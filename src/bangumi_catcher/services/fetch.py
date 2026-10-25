"""High-level fetch/analysis orchestration shared by the GUI and the CLI."""

from __future__ import annotations

import logging
from collections.abc import Callable

from ..api import BangumiClient
from ..core.analysis import analyze
from ..core.config import AppConfig
from ..core.models import AnalysisReport, UserCollection
from .library import normalize_username

logger = logging.getLogger(__name__)

ProgressCb = Callable[[float, str], None]
CancelCheck = Callable[[], bool]
ClientFactory = Callable[[AppConfig], BangumiClient]


async def fetch_user_collection(
    config: AppConfig,
    username: str,
    subject_type: int | None = None,
    force_refresh: bool = False,
    progress: ProgressCb | None = None,
    cancel_check: CancelCheck | None = None,
    client_factory: ClientFactory = BangumiClient,
) -> UserCollection:
    """Fetch one user's collection.

    ``client_factory`` exists so tests can inject a client wired to a fake
    transport without monkeypatching private attributes.
    """
    subject_type_value = subject_type if subject_type is not None else config.collection.subject_type
    normalized = normalize_username(username)
    async with client_factory(config) as client:
        return await client.fetch_collection(
            normalized,
            subject_type=subject_type_value,
            limit=config.collection.limit,
            force_refresh=force_refresh,
            progress=progress,
            cancel_check=cancel_check,
        )


def analyze_user_collection(collection: UserCollection, config: AppConfig) -> AnalysisReport:
    """Run the configured analysis over an already loaded collection."""
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
    client_factory: ClientFactory = BangumiClient,
) -> tuple[UserCollection, AnalysisReport]:
    """Fetch a collection and analyse it in one call."""
    collection = await fetch_user_collection(
        config,
        username,
        subject_type=subject_type,
        force_refresh=force_refresh,
        progress=progress,
        cancel_check=cancel_check,
        client_factory=client_factory,
    )
    return collection, analyze_user_collection(collection, config)


__all__ = [
    "CancelCheck",
    "ClientFactory",
    "ProgressCb",
    "analyze_user_collection",
    "fetch_and_analyze",
    "fetch_user_collection",
]
