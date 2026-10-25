"""Pure collection-table semantics: rows, search text, sorting and filters.

Keeping this logic out of the Qt model has two benefits:

* the desktop table and any future CLI/query surface share one definition of
  "matches" and "sort order";
* the rules are tested without starting a Qt application.

Column indexes match :data:`HEADERS` and are part of the model contract used by
``bangumi_catcher.ui.collection_model``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import CollectionItem

HEADERS: tuple[str, ...] = (
    "作品",
    "年份",
    "收藏状态",
    "我的评分",
    "全站均分",
    "进度",
    "最近更新",
)

NAME_COLUMN = 0
YEAR_COLUMN = 1
STATUS_COLUMN = 2
RATE_COLUMN = 3
SCORE_COLUMN = 4
PROGRESS_COLUMN = 5
UPDATED_COLUMN = 6

RATING_FILTERS = ("all", "rated", "unrated", "9", "8", "7")


def progress_label(item: CollectionItem) -> str:
    """Human readable progress for the library table and detail pane."""
    total = item.subject.episodes_total if item.subject else 0
    if item.type == 2:
        return f"已完成 · {total} 集" if total else "已完成"
    if item.type == 1:
        return "尚未开始"
    if item.ep_status > 0:
        return f"{item.ep_status} / {total} 集" if total else f"已记录 {item.ep_status} 集"
    return f"0 / {total} 集" if total else "暂无进度"


def search_haystack(item: CollectionItem) -> str:
    """Case-folded text searched by the library filter.

    Matches id, display name, original/Chinese names, tags and comment; every
    whitespace-separated token must be present somewhere in this string.
    """
    subject = item.subject
    return " ".join(
        [
            str(item.subject_id),
            item.subject_name,
            subject.name if subject else "",
            subject.name_cn if subject else "",
            " ".join(item.tags),
            item.comment,
        ]
    ).casefold()


def display_row(item: CollectionItem) -> tuple[str, ...]:
    """Pre-rendered cell text, aligned with :data:`HEADERS`."""
    return (
        item.subject_name,
        str(item.subject_year or "—"),
        item.collection_type_name,
        str(item.rate) if item.rate else "—",
        f"{item.subject_score:.1f}" if item.subject_score else "—",
        progress_label(item),
        item.updated_at[:10] or "—",
    )


def sort_row(item: CollectionItem) -> tuple[object, ...]:
    """Comparable values aligned with :data:`HEADERS`.

    Qt sorts by asking the model for a column value; pre-computing a tuple per
    row keeps sorting and filtering O(rows) without per-cell Qt callbacks.
    """
    return (
        item.subject_name.casefold(),
        item.subject_year or 0,
        item.type,
        item.rate,
        item.subject_score,
        item.completion_rate,
        item.updated_at,
    )


@dataclass(frozen=True)
class CollectionQuery:
    """A search text plus the three dropdown filters of the library page."""

    text: str = ""
    status: int | None = None
    year: int | None = None
    rating: str = "all"
    tokens: tuple[str, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tokens", tuple(self.text.casefold().split()))
        if self.rating not in RATING_FILTERS and not self.rating.isdigit():
            object.__setattr__(self, "rating", "all")

    def matches(self, item: CollectionItem, haystack: str) -> bool:
        """Return ``True`` when ``item`` passes every active filter.

        ``haystack`` is passed in (rather than recomputed) because the table
        model caches one per row.
        """
        if self.status is not None and item.type != self.status:
            return False
        if self.year is not None and (item.subject_year or 0) != self.year:
            return False
        if self.rating == "rated" and item.rate == 0:
            return False
        if self.rating == "unrated" and item.rate != 0:
            return False
        if self.rating.isdigit() and item.rate < int(self.rating):
            return False
        return all(token in haystack for token in self.tokens)


__all__ = [
    "HEADERS",
    "NAME_COLUMN",
    "PROGRESS_COLUMN",
    "RATE_COLUMN",
    "RATING_FILTERS",
    "SCORE_COLUMN",
    "STATUS_COLUMN",
    "UPDATED_COLUMN",
    "YEAR_COLUMN",
    "CollectionQuery",
    "display_row",
    "progress_label",
    "search_haystack",
    "sort_row",
]
