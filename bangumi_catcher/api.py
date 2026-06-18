"""Bangumi API 异步客户端 —— httpx + 并发 + 缓存 + 重试."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .cache import Cache
from .exceptions import APIError, EmptyCollectionError, RateLimitError
from .models import (
    CollectionItem,
    ImageInfo,
    RatingInfo,
    Subject,
    UserCollection,
)

logger = logging.getLogger(__name__)

# 并发限制: 同时最多 N 个请求
MAX_CONCURRENT = 8


def _build_subject(data: dict) -> Subject:
    """从 API 响应构建 Subject."""
    return Subject(
        id=data.get("id", 0),
        name=data.get("name", ""),
        name_cn=data.get("name_cn", ""),
        summary=data.get("summary", ""),
        date=data.get("date", ""),
        platform=data.get("platform", ""),
        eps=data.get("eps", 0),
        total_episodes=data.get("total_episodes", 0),
        rating=RatingInfo(**data["rating"]) if data.get("rating") else None,
        rank=data.get("rank", 0),
        images=ImageInfo(**data["images"]) if data.get("images") else None,
    )


class BangumiClient:
    """Bangumi v0 异步 API 客户端.

    用法::

        async with BangumiClient(config) as client:
            collection = await client.fetch_collection("用户名")
    """

    def __init__(self, config: dict, cache: Cache | None = None):
        api_cfg = config.get("api", {})
        col_cfg = config.get("collection", {})

        self.base_url: str = api_cfg.get("base_url", "https://api.bgm.tv").rstrip("/")
        self.timeout: float = float(api_cfg.get("timeout", 30))
        self.max_retries: int = api_cfg.get("max_retries", 3)
        self.retry_delay: float = float(api_cfg.get("retry_delay", 1.0))
        self.rate_limit_delay: float = float(col_cfg.get("rate_limit_delay", 1.0))

        self.user_agent: str = api_cfg.get(
            "user_agent",
            "bangumi-catcher/2.0 (https://github.com/your-username/bangumi-catcher)",
        )
        self._cache = cache or Cache()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BangumiClient":
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
        self._cache.close()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized — use `async with`")
        return self._client

    # ----------------------------------------------------------------
    # 底层 HTTP
    # ----------------------------------------------------------------

    async def _request(self, path: str, params: dict | None = None) -> dict:
        """带重试的 GET 请求."""
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await self.client.get(url, params=params)
            except httpx.RequestError as e:
                logger.warning("请求异常 %s (重试 %d/%d): %s", url, attempt, self.max_retries, e)
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                continue

            # HTTP 429 — 速率限制
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", self.retry_delay * 5))
                logger.warning("速率限制 429, 等待 %ds (重试 %d/%d)", retry_after, attempt, self.max_retries)
                if attempt < self.max_retries:
                    await asyncio.sleep(retry_after)
                last_error = RateLimitError(retry_after)
                continue

            # HTTP 4xx
            if 400 <= resp.status_code < 500:
                raise APIError(
                    f"客户端错误 {resp.status_code}: {resp.text[:200]}",
                    status_code=resp.status_code,
                    url=url,
                )

            # HTTP 5xx
            if resp.status_code >= 500:
                logger.warning("服务端错误 %d (重试 %d/%d)", resp.status_code, attempt, self.max_retries)
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                last_error = APIError(f"服务端错误 {resp.status_code}", status_code=resp.status_code, url=url)
                continue

            return resp.json()

        raise last_error or APIError("请求彻底失败", status_code=0, url=url)

    # ----------------------------------------------------------------
    # 公开 API
    # ----------------------------------------------------------------

    async def get_subject(self, subject_id: int) -> Subject:
        """获取单条目详情 (优先缓存)."""
        cached = self._cache.get_subject(subject_id)
        if cached is not None:
            # cached 是 dict, 需要重建为 Subject
            try:
                return Subject(**cached)
            except Exception:
                self._cache.delete(self._cache.subject_key(subject_id))

        data = await self._request(f"/v0/subjects/{subject_id}")
        subject = _build_subject(data)
        # 缓存原始 dict (Pydantic model 不能直接 pickle)
        self._cache.set_subject(subject_id, subject.model_dump())
        return subject

    async def _fetch_page(
        self, username: str, subject_type: int, offset: int, limit: int, coll_type: int | None,
    ) -> tuple[list[dict], int]:
        """抓取单页."""
        params: dict[str, Any] = {
            "subject_type": subject_type,
            "limit": min(limit, 50),
            "offset": offset,
        }
        if coll_type is not None:
            params["type"] = coll_type

        page = await self._request(f"/v0/users/{username}/collections", params)
        return page.get("data", []), page.get("total", 0)

    async def fetch_collection(
        self,
        username: str,
        subject_type: int = 2,
        collection_type: int | None = None,
        limit: int = 50,
        enrich_subjects: bool = True,
        force_refresh: bool = False,
    ) -> UserCollection:
        """分页抓取用户全部收藏, 并发获取条目详情.

        Args:
            username: Bangumi 用户名或 UID.
            subject_type: 1=书籍 2=动画 3=音乐 4=游戏 6=三次元.
            collection_type: None=全部, 1-5 按收藏类型过滤.
            limit: 每页条数.
            enrich_subjects: 是否逐条获取详情 (含年份/评分/封面).
            force_refresh: 跳过缓存, 强制重新抓取.

        Returns:
            UserCollection.
        """
        # ---------- 尝试缓存 ----------
        if not force_refresh:
            cached = self._cache.get_collection(username, subject_type)
            if cached is not None:
                try:
                    logger.info("使用缓存数据 (用户=%s, type=%d)", username, subject_type)
                    return UserCollection(**cached)
                except Exception:
                    self._cache.delete(self._cache.collection_key(username, subject_type))

        # ---------- 分页抓取 ----------
        logger.info("开始抓取用户 %s (subject_type=%d)", username, subject_type)
        raw_items: list[dict] = []
        offset = 0

        while True:
            data_list, total = await self._fetch_page(username, subject_type, offset, limit, collection_type)
            raw_items.extend(data_list)
            logger.info("  第 %d 页: +%d 条, 累计 %d/%d", offset // limit + 1, len(data_list), len(raw_items), total)

            if not data_list or len(raw_items) >= total:
                break
            offset += len(data_list)
            await asyncio.sleep(self.rate_limit_delay)

        if not raw_items:
            raise EmptyCollectionError(
                f"用户 {username} 的收藏为空 (可能设置了隐私保护或 subject_type 不匹配)"
            )

        # ---------- 构建 CollectionItem ----------
        items: list[CollectionItem] = []
        for entry in raw_items:
            subject_data = entry.get("subject", {})
            # 内联 subject (API 在列表里可能返回精简版)
            inline_subject = None
            if subject_data:
                try:
                    inline_subject = _build_subject(subject_data)
                except Exception:
                    pass

            items.append(CollectionItem(
                subject_id=entry.get("subject_id", 0),
                subject=inline_subject,
                type=entry.get("type", 0),
                rate=entry.get("rate", 0),
                comment=entry.get("comment", ""),
                tags=entry.get("tags", []),
                ep_status=entry.get("ep_status", 0),
                vol_status=entry.get("vol_status", 0),
                updated_at=entry.get("updated_at", ""),
                private=entry.get("private", False),
            ))

        # ---------- 并发获取条目详情 ----------
        if enrich_subjects:
            # 筛选需要补充详情的条目 (没有 date 的)
            need_enrich = [item for item in items if item.subject is None or not item.subject.date]
            if need_enrich:
                logger.info("并发获取 %d 个条目详情 (max_concurrent=%d)", len(need_enrich), MAX_CONCURRENT)
                semaphore = asyncio.Semaphore(MAX_CONCURRENT)

                async def enrich_one(item: CollectionItem) -> None:
                    async with semaphore:
                        try:
                            item.subject = await self.get_subject(item.subject_id)
                            await asyncio.sleep(self.rate_limit_delay * 0.2)
                        except Exception as e:
                            logger.warning("获取条目 %d 详情失败: %s", item.subject_id, e)

                await asyncio.gather(*[enrich_one(it) for it in need_enrich])
                logger.info("详情获取完成")

        result = UserCollection(username=username, total=len(items), items=items)

        # ---------- 写入缓存 ----------
        self._cache.set_collection(username, subject_type, result.model_dump())

        logger.info("抓取完成: %d 条收藏", len(result.items))
        return result
