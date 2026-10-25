"""Pagination arithmetic and page merging.

The offsets are derived from the API's declared ``total`` instead of looping
``while True`` — a bogus total can therefore never cause an infinite loop.
Merging sorts by offset and de-duplicates by ``subject_id`` because ``total``
may drift while pages are being fetched.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def compute_remaining_offsets(first_count: int, total: int, limit: int) -> list[int]:
    """Offsets of the pages that still need fetching (excluding the first page).

    Args:
        first_count: Number of entries returned by the first page.
        total: Collection size declared by the API.
        limit: Page size (``<= 0`` yields no pages).
    """
    if limit <= 0 or total <= first_count:
        return []
    return list(range(first_count, total, limit))


def merge_pages(raw_pages: Mapping[int, Sequence[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    """Merge pages in offset order, de-duplicating entries that carry an id.

    Entries with a missing/zero ``subject_id`` are kept as-is and never
    de-duplicated, so malformed rows are still visible to the caller.
    """
    merged: list[dict[str, Any]] = []
    seen: set[int] = set()
    for offset in sorted(raw_pages):
        for entry in raw_pages[offset]:
            subject_id = entry.get("subject_id", 0)
            if subject_id and subject_id in seen:
                continue
            if subject_id:
                seen.add(subject_id)
            merged.append(dict(entry))
    return merged


__all__ = ["compute_remaining_offsets", "merge_pages"]
