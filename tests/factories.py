"""Model factories shared by tests.

Building collections by hand keeps tests readable and makes the expected
semantics (which type maps to which completion rate) explicit.
"""

from __future__ import annotations

from datetime import datetime

from bangumi_catcher.core.models import (
    AnalysisReport,
    CollectionItem,
    RatingInfo,
    Subject,
    UserCollection,
)


def make_subject(
    subject_id: int = 1,
    *,
    year: int | None = 2020,
    date: str | None = None,
    score: float = 7.5,
    rank: int = 0,
    eps: int = 12,
    total_episodes: int | None = None,
    name: str | None = None,
    name_cn: str | None = None,
    summary: str = "",
    platform: str = "TV",
) -> Subject:
    """Create a subject; ``date`` wins over ``year`` when both are given."""
    if date is None and year is not None:
        date = f"{year}-04-05"
    return Subject(
        id=subject_id,
        name=name if name is not None else f"Anime{subject_id}",
        name_cn=name_cn if name_cn is not None else f"动画{subject_id}",
        summary=summary,
        date=date or "",
        platform=platform,
        eps=eps,
        total_episodes=eps if total_episodes is None else total_episodes,
        rating=RatingInfo(score=score, rank=rank),
    )


def make_item(
    subject_id: int = 1,
    type_: int = 2,
    rate: int = 8,
    *,
    year: int | None = 2020,
    score: float = 7.5,
    eps: int = 12,
    ep_status: int = 12,
    tags: tuple[str, ...] = ("原创",),
    comment: str = "",
    updated_at: str = "2026-01-01T00:00:00+08:00",
    subject: Subject | None = None,
) -> CollectionItem:
    return CollectionItem(
        subject_id=subject_id,
        subject=subject
        if subject is not None
        else make_subject(
            subject_id,
            year=year,
            score=score,
            eps=eps,
        ),
        type=type_,
        rate=rate,
        comment=comment,
        tags=list(tags),
        ep_status=ep_status,
        updated_at=updated_at,
    )


def make_collection(
    items: list[CollectionItem] | None = None,
    *,
    username: str = "tester",
    subject_type: int | None = None,
    fetched_at: str = "2026-01-01T00:00:00",
) -> UserCollection:
    entries = list(items) if items is not None else []
    return UserCollection(
        username=username,
        subject_type=subject_type,
        total=len(entries),
        items=entries,
        fetched_at=fetched_at,
    )


def make_sample_collection() -> UserCollection:
    """The canonical five-entry fixture used across the suite."""
    items = [
        make_item(1, 2, 8, year=2020, score=7.5),
        make_item(2, 2, 0, year=2020, score=8.0),  # finished but unrated
        make_item(3, 2, 6, year=2021, score=6.5),
        make_item(4, 1, 0, year=2021, score=7.0),  # wish
        make_item(5, 3, 0, year=2022, score=8.2, ep_status=4),  # watching 4/12
    ]
    return make_collection(items)


def make_empty_report(username: str = "x") -> AnalysisReport:
    return AnalysisReport(username=username, total_items=0, generated_at=datetime(2026, 1, 1).isoformat())


__all__ = [
    "make_collection",
    "make_empty_report",
    "make_item",
    "make_sample_collection",
    "make_subject",
]
