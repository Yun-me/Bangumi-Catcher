"""Async Bangumi v0 client.

Responsibilities are intentionally narrow: build one ``httpx.AsyncClient``,
retry transient failures, translate HTTP status codes into the project's
exception types, and expose small primitives (``request`` / ``fetch_page`` /
``get_subject``). Collection pagination lives in :mod:`.collection` so this
module stays easy to reason about.

Every method accepts an explicit cancellation check. Progress callbacks receive
``(fraction, message)`` and may raise to abort the operation.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import httpx

from ..core.config import AppConfig
from ..core.errors import APIError, NotFoundError, OperationCancelled, RateLimitError
from ..core.models import Subject
from .cache import Cache
from .mapping import build_subject
from .ratelimit import RateLimiter

logger = logging.getLogger(__name__)

ProgressCb = Callable[[float, str], None]
CancelCheck = Callable[[], bool]

NOT_FOUND_USER = "用户不存在，或其收藏未公开（隐私设置）。请核对用户 ID。"
NOT_FOUND_SUBJECT = "条目不存在或已被删除。"


class BangumiClient:
    """Bangumi v0 API client.

    Example::

        async with BangumiClient(config) as client:
            collection = await client.fetch_collection("username")
    """

    def __init__(
        self,
        config: AppConfig,
        cache: Cache | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        api_cfg = config.api
        collection_cfg = config.collection
        cache_cfg = config.cache

        self.base_url = api_cfg.base_url.rstrip("/")
        self.timeout = api_cfg.timeout
        self.max_retries = api_cfg.max_retries
        self.retry_delay = api_cfg.retry_delay
        self.proxy = api_cfg.proxy
        self.trust_env = api_cfg.trust_env
        self.user_agent = api_cfg.user_agent
        self.rate_limit_delay = collection_cfg.rate_limit_delay
        self.page_limit = max(1, min(collection_cfg.limit, 50))
        self.max_concurrent = max(1, collection_cfg.max_concurrent)

        self.cache_enabled = cache_cfg.enabled
        self.cache_ttl = cache_cfg.ttl
        self._owns_cache = cache is None
        self.cache = cache if cache is not None else Cache(cache_cfg.resolved_dir())

        self._rate_limiter = RateLimiter(self.rate_limit_delay)
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        self._cancel_check: CancelCheck | None = None

    # -- lifecycle -------------------------------------------------------

    async def __aenter__(self) -> BangumiClient:
        # When a transport is injected (tests, fakes) environment proxies are
        # irrelevant and some malformed ``NO_PROXY`` values would make httpx fail
        # while building its mounts, so trust_env is disabled in that case.
        trust_env = self.trust_env and self._transport is None
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            follow_redirects=True,
            proxy=None if self._transport is not None else self.proxy,
            trust_env=trust_env,
            transport=self._transport,
            limits=httpx.Limits(
                max_connections=self.max_concurrent,
                max_keepalive_connections=self.max_concurrent,
            ),
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._owns_cache:
            self.cache.close()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("BangumiClient not initialised — use `async with`")
        return self._client

    # -- cancellation ----------------------------------------------------

    def set_cancel_check(self, check: CancelCheck | None) -> None:
        self._cancel_check = check

    def check_cancelled(self) -> None:
        if self._cancel_check is not None and self._cancel_check():
            raise OperationCancelled("操作已取消")

    # -- HTTP ------------------------------------------------------------

    async def request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        not_found: str = NOT_FOUND_USER,
    ) -> dict[str, Any]:
        """GET ``path`` with retries, mapping status codes to exceptions."""
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            self.check_cancelled()
            try:
                await self._rate_limiter.acquire()
                response = await self.client.get(url, params=params)
            except httpx.RequestError as exc:
                # transport-level failures (timeout, DNS, reset) -> back off and retry
                logger.warning("请求异常 %s (重试 %d/%d): %s", url, attempt, self.max_retries, exc)
                last_error = APIError(f"网络请求失败：{exc}", status_code=0, url=url)
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                self.check_cancelled()
                continue

            if response.status_code == 429:
                retry_after = self._parse_retry_after(response, default=self.retry_delay * 5)
                logger.warning("速率限制 429, 等待 %ss (重试 %d/%d)", retry_after, attempt, self.max_retries)
                last_error = RateLimitError(int(retry_after))
                if attempt < self.max_retries:
                    await asyncio.sleep(retry_after)
                continue

            if response.status_code == 404:
                raise NotFoundError(not_found)

            if 400 <= response.status_code < 500:
                raise APIError(
                    f"请求被拒绝（HTTP {response.status_code}）。可能是参数有误或访问受限。",
                    status_code=response.status_code,
                    url=url,
                )

            if response.status_code >= 500:
                logger.warning("服务端错误 %d (重试 %d/%d)", response.status_code, attempt, self.max_retries)
                last_error = APIError(
                    f"Bangumi 服务暂时不可用（HTTP {response.status_code}），请稍后重试。",
                    status_code=response.status_code,
                    url=url,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                continue

            try:
                return response.json()
            except ValueError as exc:
                raise APIError(
                    f"响应不是合法 JSON：{exc}", status_code=response.status_code, url=url
                ) from exc

        raise last_error or APIError("请求多次重试后仍失败。", status_code=0, url=url)

    @staticmethod
    def _parse_retry_after(response: httpx.Response, default: float) -> float:
        try:
            return float(response.headers.get("Retry-After", default))
        except (TypeError, ValueError):
            return default

    # -- endpoints -------------------------------------------------------

    async def get_subject(self, subject_id: int) -> Subject:
        """Fetch subject details, honouring the subject cache when enabled."""
        if self.cache_enabled:
            cached = self.cache.get_subject(subject_id)
            if cached is not None:
                try:
                    return Subject(**cached)
                except Exception:  # stale cache shape -> drop and refetch
                    self.cache.delete(self.cache.subject_key(subject_id))

        data = await self.request(f"/v0/subjects/{subject_id}", not_found=NOT_FOUND_SUBJECT)
        subject = build_subject(data)
        if self.cache_enabled:
            self.cache.set_subject(subject_id, subject.model_dump())
        return subject

    async def fetch_page(
        self,
        username: str,
        subject_type: int,
        offset: int,
        limit: int,
        collection_type: int | None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch one collection page, returning ``(entries, total)``."""
        params: dict[str, Any] = {
            "subject_type": subject_type,
            "limit": min(limit, 50),
            "offset": offset,
        }
        if collection_type is not None:
            params["type"] = collection_type
        page = await self.request(
            f"/v0/users/{quote(username, safe='')}/collections",
            params,
        )
        entries = page.get("data") or []
        return entries, int(page.get("total") or 0)

    async def fetch_collection(
        self,
        username: str,
        subject_type: int = 2,
        collection_type: int | None = None,
        limit: int | None = None,
        enrich_subjects: bool = True,
        force_refresh: bool = False,
        progress: ProgressCb | None = None,
        cancel_check: CancelCheck | None = None,
    ):
        """Fetch a complete collection; see :func:`.collection.fetch_collection`."""
        from .collection import fetch_collection

        return await fetch_collection(
            self,
            username,
            subject_type=subject_type,
            collection_type=collection_type,
            limit=limit,
            enrich_subjects=enrich_subjects,
            force_refresh=force_refresh,
            progress=progress,
            cancel_check=cancel_check,
        )


__all__ = [
    "NOT_FOUND_SUBJECT",
    "NOT_FOUND_USER",
    "BangumiClient",
    "CancelCheck",
    "ProgressCb",
]
