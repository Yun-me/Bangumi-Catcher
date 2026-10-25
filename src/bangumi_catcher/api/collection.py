"""Collection pagination, enrichment and caching.

This module contains the orchestration that used to live inside
``BangumiClient.fetch_collection``. It depends only on the small client
primitives, which makes the concurrency behaviour easy to test with a fake
transport.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from ..core.errors import APIError, EmptyCollectionError, NotFoundError, OperationCancelled
from ..core.models import CollectionItem, UserCollection
from .mapping import build_collection_item
from .pagination import compute_remaining_offsets, merge_pages

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .client import BangumiClient, CancelCheck, ProgressCb

logger = logging.getLogger(__name__)


async def fetch_collection(
    client: BangumiClient,
    username: str,
    subject_type: int = 2,
    collection_type: int | None = None,
    limit: int | None = None,
    enrich_subjects: bool = True,
    force_refresh: bool = False,
    progress: ProgressCb | None = None,
    cancel_check: CancelCheck | None = None,
) -> UserCollection:
    """Fetch every page of a user's collection and build a snapshot.

    The first page provides ``total``; the remaining offsets are fetched by at
    most ``client.max_concurrent`` consumer coroutines. Progress is reported in
    the 0-1 range and the callback may raise to cancel the whole operation.
    """
    client.set_cancel_check(cancel_check)
    username = username.strip()
    if not username:
        raise APIError("用户名不能为空。", status_code=0, url="")

    def report(fraction: float, message: str) -> None:
        if progress is not None:
            progress(max(0.0, min(1.0, fraction)), message)

    # -- cached snapshot -------------------------------------------------
    if client.cache_enabled and not force_refresh:
        cached = client.cache.get_collection(username, subject_type, collection_type)
        if cached is not None:
            try:
                result = UserCollection(**cached)
                result.subject_type = subject_type
            except Exception:
                client.cache.delete(client.cache.collection_key(username, subject_type, collection_type))
            else:
                client.check_cancelled()
                logger.info("使用缓存数据 (用户=%s, type=%d)", username, subject_type)
                report(1.0, "已从本地缓存载入")
                return result

    page_limit = max(1, min(int(limit if limit is not None else client.page_limit), 50))

    # -- first page ------------------------------------------------------
    report(0.05, "连接 Bangumi …")
    client.check_cancelled()
    first_entries, total = await client.fetch_page(username, subject_type, 0, page_limit, collection_type)
    if not first_entries:
        raise EmptyCollectionError(f"用户「{username}」在该分类下没有收藏，或其收藏未公开。")

    page_count = max(1, -(-total // page_limit))
    logger.info("用户 %s 共 %d 条 / %d 页", username, total, page_count)
    report(0.15, f"已获取 1/{page_count} 页")

    raw_pages: dict[int, list[dict]] = {0: first_entries}

    # -- remaining pages, bounded concurrency ----------------------------
    remaining_offsets = compute_remaining_offsets(len(first_entries), total, page_limit)
    if remaining_offsets:
        semaphore = asyncio.Semaphore(client.max_concurrent)
        done = 0

        async def grab(offset: int) -> tuple[int, list[dict]]:
            async with semaphore:
                client.check_cancelled()
                entries, _ = await client.fetch_page(
                    username, subject_type, offset, page_limit, collection_type
                )
                return offset, entries

        offsets = iter(remaining_offsets)

        async def consume_pages() -> None:
            nonlocal done
            for offset in offsets:
                page_offset, page_entries = await grab(offset)
                raw_pages[page_offset] = page_entries
                done += 1
                client.check_cancelled()
                report(0.15 + 0.40 * done / len(remaining_offsets), f"已获取 {done + 1}/{page_count} 页")

        tasks = [
            asyncio.create_task(consume_pages())
            for _ in range(min(client.max_concurrent, len(remaining_offsets)))
        ]
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    # -- build items -----------------------------------------------------
    report(0.58, "整理收藏条目 …")
    items: list[CollectionItem] = []
    for entry in merge_pages(raw_pages):
        client.check_cancelled()
        items.append(build_collection_item(entry))

    # -- enrich entries without an inline subject ------------------------
    if enrich_subjects:
        await _enrich_missing_subjects(client, items, report)

    client.check_cancelled()
    result = UserCollection(username=username, subject_type=subject_type, total=len(items), items=items)
    if client.cache_enabled:
        client.cache.set_collection(
            username,
            subject_type,
            result.model_dump(),
            collection_type=collection_type,
            ttl=client.cache_ttl,
        )
    report(1.0, "抓取完成")
    logger.info("抓取完成: %d 条收藏", len(result.items))
    return result


async def _enrich_missing_subjects(
    client: BangumiClient,
    items: list[CollectionItem],
    report,
) -> None:
    """Fetch full subject details for entries that arrived without one."""
    missing = [item for item in items if item.subject is None]
    if not missing:
        return

    logger.info("并发补全 %d 个条目详情 (concurrency=%d)", len(missing), client.max_concurrent)
    semaphore = asyncio.Semaphore(client.max_concurrent)
    done = 0
    step = max(1, len(missing) // 50)  # limit progress callback frequency

    async def enrich_one(item: CollectionItem) -> None:
        nonlocal done
        async with semaphore:
            client.check_cancelled()
            try:
                item.subject = await client.get_subject(item.subject_id)
            except OperationCancelled:
                raise
            except NotFoundError:
                pass  # deleted or no longer visible — keep the row as-is
            except Exception as exc:
                logger.warning("补全条目 %d 失败: %s", item.subject_id, exc)
            finally:
                done += 1
                if done % step == 0 or done == len(missing):
                    report(0.62 + 0.36 * done / len(missing), f"补全详情 {done}/{len(missing)} …")

    pending = iter(missing)

    async def consume_subjects() -> None:
        for item in pending:
            await enrich_one(item)

    tasks = [asyncio.create_task(consume_subjects()) for _ in range(min(client.max_concurrent, len(missing)))]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    client.check_cancelled()


__all__ = ["fetch_collection"]
