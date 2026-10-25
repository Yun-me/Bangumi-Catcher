"""Pagination arithmetic and page merging.

These algorithms replaced a ``while True`` paging loop: offsets are derived from
the declared total, so a bogus total can never loop forever.
"""

from __future__ import annotations

from bangumi_catcher.api.pagination import compute_remaining_offsets, merge_pages


def test_offsets_multi_page():
    assert compute_remaining_offsets(50, 120, 50) == [50, 100]


def test_offsets_single_page_no_extra():
    assert compute_remaining_offsets(25, 25, 50) == []


def test_offsets_exact_multiple():
    assert compute_remaining_offsets(50, 100, 50) == [50]


def test_offsets_bogus_small_total():
    assert compute_remaining_offsets(50, 3, 50) == []


def test_offsets_zero_limit_safe():
    assert compute_remaining_offsets(50, 120, 0) == []


def test_offsets_negative_total_safe():
    assert compute_remaining_offsets(10, -1, 50) == []


def test_merge_orders_by_offset():
    pages = {
        100: [{"subject_id": 5}, {"subject_id": 6}],
        0: [{"subject_id": 1}, {"subject_id": 2}],
        50: [{"subject_id": 3}, {"subject_id": 4}],
    }
    assert [entry["subject_id"] for entry in merge_pages(pages)] == [1, 2, 3, 4, 5, 6]


def test_merge_dedupes_overlap():
    pages = {
        0: [{"subject_id": 1}, {"subject_id": 2}, {"subject_id": 3}],
        50: [{"subject_id": 3}, {"subject_id": 4}],
    }
    assert [entry["subject_id"] for entry in merge_pages(pages)] == [1, 2, 3, 4]


def test_merge_keeps_entries_without_id():
    pages = {0: [{"subject_id": 0}, {"foo": "bar"}, {"subject_id": 7}]}
    assert len(merge_pages(pages)) == 3


def test_merge_empty():
    assert merge_pages({}) == []


def test_merge_does_not_mutate_input():
    entry = {"subject_id": 1, "subject": {"id": 1}}
    pages = {0: [entry]}
    merged = merge_pages(pages)
    merged[0]["subject"] = None
    assert entry["subject"] == {"id": 1}
