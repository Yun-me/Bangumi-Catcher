"""Bangumi API 异步客户端 —— httpx + 并发分页 + 缓存 + 重试.

相比上一版的关键改动：
* 分页并发化：先取首页拿到 total，其余页用有界并发一次性抓取，不再逐页 sleep。
* 友好错误：404 抛 NotFoundError（"用户不存在/隐私保护"），与限流/服务端错误区分开。
* 进度回调：fetch_collection 接受 progress(frac, msg)，GUI 据此实时刷新进度条；
  回调可抛异常以实现"取消"（见 gui.FetchWorker）。
* 去除 while-True 翻页，改为按 offset 计算页码，从根本上消除翻页死循环风险。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

import httpx

from .cache import Cache
from .exceptions import APIError, EmptyCollectionError, NotFoundError, RateLimitError
from .models import (
    CollectionItem,
    ImageInfo,
    RatingInfo,
    Subject,
    UserCollection,
)

logger = logging.getLogger(__name__)

# 进度回调签名：fraction(0-1), message
ProgressCb = Callable[[float, str], None]


def _build_subject(data: dict) -> Subject:
    """从 API 响应安全构建 Subject（字段缺失/类型异常已在模型层兜底）。

    兼容两种来源，这正是「全站评分抓不到」的根因所在：
      * 收藏列表内联的 SlimSubject —— 评分是**扁平**的 ``score`` / ``rank`` 字段，
        集数字段为 ``eps``，且没有 ``total_episodes``、简介字段名为 ``short_summary``；
      * 条目详情接口的完整 Subject —— 评分在嵌套的 ``rating`` 对象里，集数有 ``total_episodes``。
    旧实现只读嵌套 ``rating``，导致列表内联条目的全站评分恒为 0。
    """
    rating: RatingInfo | None = None
    if isinstance(data.get("rating"), dict):
        rating = RatingInfo(**data["rating"])
    elif "score" in data or "rank" in data:  # SlimSubject 的扁平评分
        rating = RatingInfo(score=data.get("score") or 0.0, rank=data.get("rank") or 0)

    return Subject(
        id=data.get("id", 0),
        name=data.get("name", ""),
        name_cn=data.get("name_cn", ""),
        summary=data.get("summary") or data.get("short_summary", ""),
        date=data.get("date", ""),
        platform=data.get("platform", ""),
        eps=data.get("eps", 0),
        total_episodes=data.get("total_episodes", 0),
        rating=rating,
        rank=data.get("rank", 0),
        images=ImageInfo(**data["images"]) if isinstance(data.get("images"), dict) else None,
    )


def compute_remaining_offsets(first_count: int, total: int, limit: int) -> list[int]:
    """根据首页条数与总数，计算其余页的 offset 列表。

    采用按 offset 计算页码的方式取代 while-True 翻页，从根本上消除翻页死循环：
    offset 列表由 ``total`` 唯一确定，即便接口返回异常 total 也不会无限翻页。

    Args:
        first_count: 首页实际返回的条数。
        total: 接口声明的收藏总数。
        limit: 每页条数。
    Returns:
        需要额外抓取的 offset 升序列表（不含首页 0）。
    """
    if limit <= 0 or total <= first_count:
        return []
    return list(range(first_count, total, limit))


def merge_pages(raw_pages: dict[int, list[dict]]) -> list[dict]:
    """按 offset 升序合并各页原始条目，并按 subject_id 去重。

    去重可防止 total 在抓取过程中抖动、导致相邻页 offset 重叠时出现重复条目。
    subject_id 缺失（0/None）的条目一律保留，不参与去重。
    """
    merged: list[dict] = []
    seen: set[int] = set()
    for off in sorted(raw_pages):
        for entry in raw_pages[off]:
            sid = entry.get("subject_id", 0)
            if sid and sid in seen:
                continue
            if sid:
                seen.add(sid)
            merged.append(entry)
    return merged


class _RateLimiter:
    """限制连续请求的最小发起间隔（令牌桶式最简实现）。

    并发由信号量约束「同时在飞的请求数」，本限速器约束「请求发起的疏密」：
    当 ``min_interval`` 为 0 时完全不介入（默认即如此），仅当用户为规避 429
    限流而调大该值时才会在请求之间插入等待。
    """

    def __init__(self, min_interval: float):
        self.min_interval = max(0.0, float(min_interval))
        self._lock: asyncio.Lock | None = None  # 延迟创建，兼容 Python<3.10
        self._next_at = 0.0

    async def acquire(self) -> None:
        if self.min_interval <= 0:
            return
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            loop = asyncio.get_event_loop()
            now = loop.time()
            wait = self._next_at - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = loop.time()
            self._next_at = max(now, self._next_at) + self.min_interval


class BangumiClient:
    """Bangumi v0 异步 API 客户端.

    用法::

        async with BangumiClient(config) as client:
            collection = await client.fetch_collection("用户名")
    """

    def __init__(self, config: dict, cache: Cache | None = None):
        api_cfg = config.get("api", {})
        col_cfg = config.get("collection", {})
        cache_cfg = config.get("cache", {})

        self.base_url: str = api_cfg.get("base_url", "https://api.bgm.tv").rstrip("/")
        self.timeout: float = float(api_cfg.get("timeout", 30))
        self.max_retries: int = int(api_cfg.get("max_retries", 3))
        self.retry_delay: float = float(api_cfg.get("retry_delay", 1.0))
        self.rate_limit_delay: float = float(col_cfg.get("rate_limit_delay", 0.0))
        # 并发上限：同时最多 N 个请求；可经 config 调整以适配不同网络/限流策略。
        self.max_concurrent: int = max(1, int(col_cfg.get("max_concurrent", 8)))

        self.user_agent: str = api_cfg.get(
            "user_agent",
            "bangumi-catcher (https://github.com/Yun-me/Bangumi-Catcher)",
        )

        # 缓存：目录 / 有效期 / 开关均可由 config 控制（此前被忽略）。
        self.cache_enabled: bool = bool(cache_cfg.get("enabled", True))
        self.cache_ttl: int = int(cache_cfg.get("ttl", 3600))
        self._owns_cache = cache is None
        if cache is not None:
            self._cache = cache
        else:
            cache_dir = cache_cfg.get("dir") or None
            self._cache = Cache(directory=cache_dir)

        self._rate_limiter = _RateLimiter(self.rate_limit_delay)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BangumiClient":
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
        if self._owns_cache:
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
        """带重试的 GET 请求；按状态码分流到对应异常类型。"""
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                await self._rate_limiter.acquire()
                resp = await self.client.get(url, params=params)
            except httpx.RequestError as e:
                # 网络层错误（超时/DNS/连接重置）→ 退避重试
                logger.warning("请求异常 %s (重试 %d/%d): %s", url, attempt, self.max_retries, e)
                last_error = APIError(f"网络请求失败：{e}", status_code=0, url=url)
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                continue

            # 429 — 速率限制：尊重 Retry-After
            if resp.status_code == 429:
                retry_after = self._parse_retry_after(resp, default=self.retry_delay * 5)
                logger.warning("速率限制 429, 等待 %ss (重试 %d/%d)", retry_after, attempt, self.max_retries)
                last_error = RateLimitError(int(retry_after))
                if attempt < self.max_retries:
                    await asyncio.sleep(retry_after)
                continue

            # 404 — 资源/用户不存在（不重试，立即给出可理解的错误）
            if resp.status_code == 404:
                raise NotFoundError("用户不存在，或其收藏未公开（隐私设置）。请核对用户 ID。")

            # 其他 4xx — 客户端错误（不重试）
            if 400 <= resp.status_code < 500:
                raise APIError(
                    f"请求被拒绝（HTTP {resp.status_code}）。可能是参数有误或访问受限。",
                    status_code=resp.status_code,
                    url=url,
                )

            # 5xx — 服务端错误（重试）
            if resp.status_code >= 500:
                logger.warning("服务端错误 %d (重试 %d/%d)", resp.status_code, attempt, self.max_retries)
                last_error = APIError(
                    f"Bangumi 服务暂时不可用（HTTP {resp.status_code}），请稍后重试。",
                    status_code=resp.status_code, url=url,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                continue

            # 2xx — 解析 JSON（防御非法 JSON）
            try:
                return resp.json()
            except ValueError as e:
                raise APIError(f"响应不是合法 JSON：{e}", status_code=resp.status_code, url=url)

        raise last_error or APIError("请求多次重试后仍失败。", status_code=0, url=url)

    @staticmethod
    def _parse_retry_after(resp: httpx.Response, default: float) -> float:
        try:
            return float(resp.headers.get("Retry-After", default))
        except (TypeError, ValueError):
            return default

    # ----------------------------------------------------------------
    # 公开 API
    # ----------------------------------------------------------------

    async def get_subject(self, subject_id: int) -> Subject:
        """获取单条目详情（优先缓存）。"""
        cached = self._cache.get_subject(subject_id)
        if cached is not None:
            try:
                return Subject(**cached)
            except Exception:  # 缓存结构过期 → 丢弃后重新拉取
                self._cache.delete(self._cache.subject_key(subject_id))

        data = await self._request(f"/v0/subjects/{subject_id}")
        subject = _build_subject(data)
        self._cache.set_subject(subject_id, subject.model_dump())
        return subject

    async def _fetch_page(
        self, username: str, subject_type: int, offset: int, limit: int, coll_type: int | None,
    ) -> tuple[list[dict], int]:
        """抓取单页，返回 (data, total)。"""
        params: dict[str, Any] = {
            "subject_type": subject_type,
            "limit": min(limit, 50),
            "offset": offset,
        }
        if coll_type is not None:
            params["type"] = coll_type

        page = await self._request(f"/v0/users/{username}/collections", params)
        data = page.get("data") or []
        total = page.get("total") or 0
        return data, int(total)

    async def fetch_collection(
        self,
        username: str,
        subject_type: int = 2,
        collection_type: int | None = None,
        limit: int = 50,
        enrich_subjects: bool = True,
        force_refresh: bool = False,
        progress: ProgressCb | None = None,
    ) -> UserCollection:
        """分页抓取用户全部收藏，并发获取条目详情。

        Args:
            username: Bangumi 用户名或 UID。
            subject_type: 1=书籍 2=动画 3=音乐 4=游戏 6=三次元。
            collection_type: None=全部，1-5 按收藏类型过滤。
            limit: 每页条数（上限 50）。
            enrich_subjects: 是否逐条补全详情（年份/评分/封面）。
            force_refresh: 跳过缓存，强制重新抓取。
            progress: 进度回调 progress(fraction, message)，可抛异常以中断（取消）。
        """
        username = username.strip()
        if not username:
            raise APIError("用户名不能为空。", status_code=0, url="")

        def _p(frac: float, msg: str) -> None:
            if progress:
                progress(max(0.0, min(1.0, frac)), msg)

        # ---------- 尝试缓存 ----------
        if self.cache_enabled and not force_refresh:
            cached = self._cache.get_collection(username, subject_type, collection_type)
            if cached is not None:
                try:
                    logger.info("使用缓存数据 (用户=%s, type=%d)", username, subject_type)
                    _p(1.0, "已从本地缓存载入")
                    return UserCollection(**cached)
                except Exception:
                    self._cache.delete(
                        self._cache.collection_key(username, subject_type, collection_type)
                    )

        # ---------- 首页（拿到 total）----------
        limit = max(1, min(int(limit), 50))
        _p(0.05, "连接 Bangumi …")
        first_data, total = await self._fetch_page(username, subject_type, 0, limit, collection_type)

        if not first_data:
            raise EmptyCollectionError(
                f"用户「{username}」在该分类下没有收藏，或其收藏未公开。"
            )

        pages_total = max(1, -(-total // limit))  # ceil
        logger.info("用户 %s 共 %d 条 / %d 页", username, total, pages_total)
        _p(0.15, f"已获取 1/{pages_total} 页")

        raw_pages: dict[int, list[dict]] = {0: first_data}

        # ---------- 其余页并发抓取 ----------
        remaining_offsets = compute_remaining_offsets(len(first_data), total, limit)
        if remaining_offsets:
            sem = asyncio.Semaphore(self.max_concurrent)
            done = 0

            async def grab(off: int) -> tuple[int, list[dict]]:
                async with sem:
                    data, _ = await self._fetch_page(username, subject_type, off, limit, collection_type)
                    return off, data

            for coro in asyncio.as_completed([grab(o) for o in remaining_offsets]):
                off, data = await coro
                raw_pages[off] = data
                done += 1
                _p(0.15 + 0.40 * done / len(remaining_offsets),
                   f"已获取 {done + 1}/{pages_total} 页")

        # 按 offset 顺序合并 + 去重（防止 total 抖动造成的重叠）
        raw_items = merge_pages(raw_pages)

        # ---------- 构建 CollectionItem ----------
        _p(0.58, "整理收藏条目 …")
        items: list[CollectionItem] = []
        for entry in raw_items:
            subject_data = entry.get("subject")
            inline_subject = None
            if isinstance(subject_data, dict) and subject_data:
                try:
                    inline_subject = _build_subject(subject_data)
                except Exception:  # 单条目脏数据不影响整体
                    inline_subject = None

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

        # ---------- 补全缺失的条目详情 ----------
        # 列表内联的 SlimSubject 已含名称/年份/全站评分/集数/封面，足够所有展示，
        # 因此仅在极少数「未内联条目详情」时才逐条补全，避免无谓的逐条请求拖慢抓取。
        if enrich_subjects:
            need_enrich = [it for it in items if it.subject is None]
            if need_enrich:
                logger.info("并发补全 %d 个条目详情 (concurrency=%d)", len(need_enrich), self.max_concurrent)
                sem = asyncio.Semaphore(self.max_concurrent)
                done = 0
                step = max(1, len(need_enrich) // 50)  # 限制进度回调频率

                async def enrich_one(item: CollectionItem) -> None:
                    nonlocal done
                    async with sem:
                        try:
                            item.subject = await self.get_subject(item.subject_id)
                        except NotFoundError:
                            pass  # 个别条目被删除/不可见，跳过即可
                        except Exception as e:
                            logger.warning("补全条目 %d 失败: %s", item.subject_id, e)
                        finally:
                            done += 1
                            if done % step == 0 or done == len(need_enrich):
                                _p(0.62 + 0.36 * done / len(need_enrich),
                                   f"补全详情 {done}/{len(need_enrich)} …")

                await asyncio.gather(*[enrich_one(it) for it in need_enrich])

        result = UserCollection(username=username, total=len(items), items=items)
        if self.cache_enabled:
            self._cache.set_collection(
                username, subject_type, result.model_dump(),
                collection_type=collection_type, ttl=self.cache_ttl,
            )
        _p(1.0, "抓取完成")
        logger.info("抓取完成: %d 条收藏", len(result.items))
        return result
