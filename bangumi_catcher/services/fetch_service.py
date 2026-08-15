"""抓取与分析服务 —— GUI 与 CLI 共用的高层编排层。"""

from __future__ import annotations

from typing import Callable

from ..core.analyzer import analyze
from ..core.api import BangumiClient
from ..core.config import AppConfig
from ..core.models import AnalysisReport, UserCollection

ProgressCb = Callable[[float, str], None]
CancelCheck = Callable[[], bool]


async def fetch_user_collection(
    config: AppConfig,
    username: str,
    subject_type: int | None = None,
    force_refresh: bool = False,
    progress: ProgressCb | None = None,
    cancel_check: CancelCheck | None = None,
) -> UserCollection:
    """抓取单个用户的收藏列表（可选进度与取消回调）。"""
    st = subject_type or config.collection.subject_type
    async with BangumiClient(config) as client:
        return await client.fetch_collection(
            username,
            subject_type=st,
            limit=config.collection.limit,
            force_refresh=force_refresh,
            progress=progress,
            cancel_check=cancel_check,
        )


def analyze_user_collection(collection: UserCollection, config: AppConfig) -> AnalysisReport:
    """对收藏数据执行完整分析。"""
    return analyze(
        collection,
        year_start=config.analysis.year_start,
        year_end=config.analysis.year_end,
        top_n=config.analysis.top_n,
    )


async def fetch_and_analyze(
    config: AppConfig,
    username: str,
    subject_type: int | None = None,
    force_refresh: bool = False,
    progress: ProgressCb | None = None,
    cancel_check: CancelCheck | None = None,
) -> tuple[UserCollection, AnalysisReport]:
    """抓取并分析，返回 (collection, report)。"""
    collection = await fetch_user_collection(
        config,
        username,
        subject_type=subject_type,
        force_refresh=force_refresh,
        progress=progress,
        cancel_check=cancel_check,
    )
    report = analyze_user_collection(collection, config)
    return collection, report
