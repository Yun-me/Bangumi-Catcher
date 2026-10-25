"""Translate Bangumi JSON payloads into domain models.

Two subject shapes exist in the API and both are normalised here:

* collection pages embed a *slim* subject: flat ``score`` / ``rank`` fields,
  ``eps`` (no ``total_episodes``) and ``short_summary``;
* ``/v0/subjects/{id}`` returns a full subject with a nested ``rating`` object.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from ..core.models import CollectionItem, ImageInfo, RatingInfo, Subject

logger = logging.getLogger(__name__)


def build_subject(data: Mapping[str, Any]) -> Subject:
    """Build a :class:`Subject` from either API shape."""
    rating: RatingInfo | None = None
    nested_rating = data.get("rating")
    if isinstance(nested_rating, Mapping):
        rating = RatingInfo(**nested_rating)
    elif "score" in data or "rank" in data:
        rating = RatingInfo(score=data.get("score") or 0.0, rank=data.get("rank") or 0)

    images = data.get("images")
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
        images=ImageInfo(**images) if isinstance(images, Mapping) else None,
    )


def safe_build_subject(data: Any) -> Subject | None:
    """Best-effort subject build; a single dirty row never aborts a sync."""
    if not isinstance(data, Mapping) or not data:
        return None
    try:
        return build_subject(data)
    except Exception as exc:  # pragma: no cover - defensive, exercised by fuzzed rows
        logger.warning("忽略无法解析的条目详情: %s", exc)
        return None


def build_collection_item(entry: Mapping[str, Any]) -> CollectionItem:
    """Build a :class:`CollectionItem` from one collection API entry."""
    subject = safe_build_subject(entry.get("subject"))
    subject_id = entry.get("subject_id") or (subject.id if subject else 0)
    return CollectionItem(
        subject_id=subject_id,
        subject=subject,
        type=entry.get("type", 0),
        rate=entry.get("rate", 0),
        comment=entry.get("comment", ""),
        tags=entry.get("tags", []),
        ep_status=entry.get("ep_status", 0),
        vol_status=entry.get("vol_status", 0),
        updated_at=entry.get("updated_at", ""),
        private=entry.get("private", False),
    )


__all__ = ["build_collection_item", "build_subject", "safe_build_subject"]
