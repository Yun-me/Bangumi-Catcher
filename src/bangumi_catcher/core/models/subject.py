"""Bangumi subject value objects and the date-derived helpers.

Bangumi returns two different subject shapes:

* the *slim* subject embedded in collection pages — flat ``score`` / ``rank``
  fields, ``eps`` but no ``total_episodes`` and ``short_summary`` instead of
  ``summary``;
* the full subject returned by ``/v0/subjects/{id}`` — a nested ``rating``
  object and both ``eps`` / ``total_episodes``.

The models below normalise both shapes so the rest of the application never
has to care which endpoint produced the data.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, computed_field, field_validator

SUBJECT_TYPE_MAP: dict[int, str] = {1: "书籍", 2: "动画", 3: "音乐", 4: "游戏", 6: "三次元"}
"""Subject categories supported by the Bangumi API (``subject_type`` query)."""

SUBJECT_TYPE_NAMES: dict[str, int] = {name: value for value, name in SUBJECT_TYPE_MAP.items()}


def subject_type_name(type_id: int | None) -> str:
    """Label for a subject type id, or ``未标注分类`` when unknown."""
    return SUBJECT_TYPE_MAP.get(type_id or 0, "未标注分类")


def parse_year(date: str) -> int | None:
    """Return the four-digit air year of an ISO-ish date string, else ``None``."""
    if len(date) >= 4:
        try:
            return int(date[:4])
        except ValueError:
            return None
    return None


def parse_season(date: str) -> str:
    """Return ``Q1``..``Q4`` for a date string, or an empty string."""
    if len(date) >= 7:
        try:
            month = int(date[5:7])
        except ValueError:
            return ""
        if 1 <= month <= 12:
            return f"Q{(month - 1) // 3 + 1}"
    return ""


class RatingInfo(BaseModel):
    """Community rating block (``rating`` object of a full subject)."""

    score: float = 0.0
    total: int = 0
    rank: int = 0


class ImageInfo(BaseModel):
    """Cover image URLs in the four sizes Bangumi exposes."""

    large: str = ""
    common: str = ""
    medium: str = ""
    small: str = ""


class Subject(BaseModel):
    """A Bangumi subject (anime, book, music, game or live action)."""

    id: int
    name: str = ""
    name_cn: str = ""
    summary: str = ""
    date: str = ""
    platform: str = ""
    eps: int = 0
    total_episodes: int = 0
    rating: RatingInfo | None = None
    rank: int = 0
    images: ImageInfo | None = None

    @field_validator("name", "name_cn", "summary", "date", "platform", mode="before")
    @classmethod
    def _none_str(cls, value: Any) -> str:
        # The API occasionally returns null for string fields; collapse to "" so
        # downstream ``.strip()`` / slicing never sees ``None``.
        return value or ""

    @field_validator("eps", "total_episodes", "rank", mode="before")
    @classmethod
    def _none_int(cls, value: Any) -> int:
        # null / missing / non-numeric -> 0. One dirty row must not abort a sync.
        if value in (None, ""):
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def year(self) -> int | None:
        """Air year derived from ``date``."""
        return parse_year(self.date)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def season(self) -> str:
        """Air quarter derived from ``date`` (``Q1``..``Q4``)."""
        return parse_season(self.date)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def episodes_total(self) -> int:
        """Total episode count, preferring ``total_episodes`` and falling back to ``eps``.

        Collection pages embed *slim* subjects that only carry ``eps``; using
        ``total_episodes`` alone would make every completion rate zero.
        """
        return self.total_episodes or self.eps

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cover_url(self) -> str:
        if self.images:
            return self.images.large or self.images.common or self.images.medium or ""
        return ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score(self) -> float:
        return self.rating.score if self.rating else 0.0


__all__ = [
    "SUBJECT_TYPE_MAP",
    "SUBJECT_TYPE_NAMES",
    "ImageInfo",
    "RatingInfo",
    "Subject",
    "parse_season",
    "parse_year",
    "subject_type_name",
]
