"""Collection entries and the user collection snapshot."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field, field_validator

from .subject import Subject

COLLECTION_TYPE_MAP: dict[int, str] = {1: "想看", 2: "看过", 3: "在看", 4: "搁置", 5: "抛弃"}
"""Bangumi collection type ids, as returned by the ``type`` field."""

COLLECTION_TYPE_NAMES: dict[str, int] = {
    "想看": 1,
    "看过": 2,
    "在看": 3,
    "搁置": 4,
    "抛弃": 5,
}
"""Reverse lookup used by the CLI and the analysis layer."""


def collection_type_name(type_id: int) -> str:
    """Human readable label for a collection type id."""
    return COLLECTION_TYPE_MAP.get(type_id, f"未知({type_id})")


class CollectionItem(BaseModel):
    """One subject inside a user's collection, plus the user's own metadata."""

    subject_id: int
    subject: Subject | None = None
    name: str = ""
    type: int = 0
    rate: int = 0  # 0-10; out-of-range values are clamped instead of raising
    comment: str = ""
    tags: list[str] = Field(default_factory=list)
    ep_status: int = 0
    vol_status: int = 0
    updated_at: str = ""
    private: bool = False

    @field_validator("comment", "name", "updated_at", mode="before")
    @classmethod
    def _none_empty(cls, value: Any) -> str:
        return value or ""

    @field_validator("type", "rate", "ep_status", "vol_status", mode="before")
    @classmethod
    def _coerce_int(cls, value: Any, info) -> int:
        # null / non-numeric -> 0; ``rate`` is additionally clamped to [0, 10] so a
        # single bad row can never fail validation of the whole collection.
        if value in (None, ""):
            return 0
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 0
        if info.field_name == "rate":
            return max(0, min(10, number))
        return number

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value: Any) -> list[str]:
        # Support all three historical shapes: null, ``["tag"]`` and ``[{"name": "tag"}]``.
        if not value:
            return []
        tags: list[str] = []
        for tag in value:
            if isinstance(tag, str):
                tags.append(tag)
            elif isinstance(tag, dict) and tag.get("name"):
                tags.append(str(tag["name"]))
        return tags

    @computed_field  # type: ignore[prop-decorator]
    @property
    def collection_type_name(self) -> str:
        return collection_type_name(self.type)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def subject_name(self) -> str:
        if self.subject:
            return self.subject.name_cn or self.subject.name or self.name
        return self.name or f"#{self.subject_id}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def subject_year(self) -> int | None:
        return self.subject.year if self.subject else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def subject_score(self) -> float:
        return self.subject.score if self.subject else 0.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def subject_cover(self) -> str:
        return self.subject.cover_url if self.subject else ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completion_rate(self) -> float:
        """Completion ratio in ``[0, 1]`` with the documented Bangumi semantics.

        * ``看过`` (type 2) is always 100%: the entry is finished regardless of
          whether every episode was recorded individually.
        * ``在看`` / ``搁置`` / ``抛弃`` use ``ep_status / episodes_total``.
        * ``想看`` (type 1) and missing progress are 0.
        """
        if self.type == 2:
            return 1.0
        if self.type == 1:
            return 0.0
        total = self.subject.episodes_total if self.subject else 0
        if total > 0 and self.ep_status > 0:
            return min(self.ep_status / total, 1.0)
        return 0.0


class UserCollection(BaseModel):
    """A complete, self-contained snapshot of one user's collection."""

    username: str
    subject_type: int | None = None
    total: int = 0
    items: list[CollectionItem] = Field(default_factory=list)
    fetched_at: str = Field(default_factory=lambda: datetime.now().isoformat())


__all__ = [
    "COLLECTION_TYPE_MAP",
    "COLLECTION_TYPE_NAMES",
    "CollectionItem",
    "UserCollection",
    "collection_type_name",
]
