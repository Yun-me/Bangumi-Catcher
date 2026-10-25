"""Aggregated analytics produced by :mod:`bangumi_catcher.core.analysis`."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class YearStats(BaseModel):
    """Per-year totals and the average rating of finished, rated entries."""

    year: int
    total: int = 0
    watching: int = 0
    finished: int = 0
    wish: int = 0
    on_hold: int = 0
    dropped: int = 0
    avg_rating: float = 0.0


class YearTrendItem(BaseModel):
    """Flat per-year row used by the timeline table and the trend charts."""

    year: int
    total: int
    finished: int
    watching: int
    wish: int
    on_hold: int = 0
    dropped: int = 0
    avg_rating: float = 0.0


class TopRatedItem(BaseModel):
    """One row of the "favourite" ranking."""

    subject_id: int
    name: str
    name_cn: str = ""
    rate: int
    year: int | None = None
    cover_url: str = ""
    bangumi_score: float = 0.0


class SeasonStats(BaseModel):
    """Number of collected subjects aired in a given quarter."""

    season: str
    count: int


class TypeTrendItem(BaseModel):
    """Collection status counts for one air year."""

    year: int
    wish: int = 0
    watching: int = 0
    finished: int = 0
    on_hold: int = 0
    dropped: int = 0


class RatingCompareItem(BaseModel):
    """User rating vs. the Bangumi community score for one subject."""

    name: str
    my_rate: int
    bgm_score: float


class TagItem(BaseModel):
    """One tag and how many collected subjects carry it."""

    name: str
    count: int


class AnalysisReport(BaseModel):
    """Everything the UI, the CLI and the HTML report need to render analytics.

    The report is deliberately self-contained: it never references the source
    collection, so it can be exported and consumed on its own.
    """

    username: str
    total_items: int
    by_year: dict[int, YearStats] = Field(default_factory=dict)
    type_counts: dict[str, int] = Field(default_factory=dict)
    rating_distribution: dict[int, int] = Field(default_factory=dict)
    top_rated: list[TopRatedItem] = Field(default_factory=list)
    year_trend: list[YearTrendItem] = Field(default_factory=list)
    type_trend: list[TypeTrendItem] = Field(default_factory=list)
    season_stats: list[SeasonStats] = Field(default_factory=list)
    rating_compare: list[RatingCompareItem] = Field(default_factory=list)
    tag_counts: dict[str, int] = Field(default_factory=dict)
    top_tags: list[TagItem] = Field(default_factory=list)
    avg_completion: float = 0.0
    overall_avg_rating: float = 0.0
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


__all__ = [
    "AnalysisReport",
    "RatingCompareItem",
    "SeasonStats",
    "TagItem",
    "TopRatedItem",
    "TypeTrendItem",
    "YearStats",
    "YearTrendItem",
]
