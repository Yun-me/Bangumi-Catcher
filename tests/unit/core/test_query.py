"""Pure table semantics: search, filters and sort keys."""

from __future__ import annotations

from bangumi_catcher.core.query import (
    HEADERS,
    CollectionQuery,
    display_row,
    progress_label,
    search_haystack,
    sort_row,
)
from tests.factories import make_item


def test_query_requires_every_token():
    item = make_item(1, 2, 8, year=2020, tags=("原创",), comment="很棒的旅行")
    haystack = search_haystack(item)
    assert CollectionQuery(text="ANIME1 原创 旅行").matches(item, haystack)
    assert not CollectionQuery(text="ANIME1 不存在").matches(item, haystack)


def test_status_and_year_filters():
    item = make_item(1, 2, 8, year=2020)
    haystack = search_haystack(item)
    assert CollectionQuery(status=2).matches(item, haystack)
    assert not CollectionQuery(status=1).matches(item, haystack)
    assert CollectionQuery(year=2020).matches(item, haystack)
    assert not CollectionQuery(year=2021).matches(item, haystack)


def test_rating_filters():
    rated = make_item(1, 2, 8)
    unrated = make_item(2, 2, 0)
    rated_haystack, unrated_haystack = search_haystack(rated), search_haystack(unrated)
    assert CollectionQuery(rating="rated").matches(rated, rated_haystack)
    assert not CollectionQuery(rating="rated").matches(unrated, unrated_haystack)
    assert CollectionQuery(rating="unrated").matches(unrated, unrated_haystack)
    assert CollectionQuery(rating="7").matches(rated, rated_haystack)
    assert not CollectionQuery(rating="9").matches(rated, rated_haystack)


def test_invalid_rating_filter_falls_back_to_all():
    item = make_item(1, 2, 8)
    assert CollectionQuery(rating="bogus").matches(item, search_haystack(item))


def test_search_haystack_includes_id_names_tags_and_comment():
    item = make_item(42, 1, 0, year=2021, tags=("科幻", "日常"), comment="好看")
    haystack = search_haystack(item)
    for token in ("42", "anime42", "动画42", "科幻", "日常", "好看"):
        assert token.casefold() in haystack


def test_display_and_sort_rows_align_with_headers():
    item = make_item(1, 2, 8, year=2020, score=7.5, ep_status=12)
    assert len(HEADERS) == 7
    assert display_row(item) == ("动画1", "2020", "看过", "8", "7.5", "已完成 · 12 集", "2026-01-01")
    sort_row_values = sort_row(item)
    assert len(sort_row_values) == len(HEADERS)
    assert sort_row_values[0] == "动画1"
    assert sort_row_values[1] == 2020
    assert sort_row_values[3] == 8


def test_progress_label_variants():
    assert progress_label(make_item(1, 2, 8, eps=12)) == "已完成 · 12 集"
    assert progress_label(make_item(2, 1, 0, eps=12)) == "尚未开始"
    assert progress_label(make_item(3, 3, 0, eps=12, ep_status=4)) == "4 / 12 集"
    assert progress_label(make_item(4, 3, 0, eps=0, ep_status=4)) == "已记录 4 集"
    assert progress_label(make_item(5, 3, 0, eps=0, ep_status=0)) == "暂无进度"
    assert progress_label(make_item(6, 2, 8, eps=0)) == "已完成"


def test_query_is_hashable_and_comparable():
    first = CollectionQuery(text="A  B", status=2, rating="8")
    second = CollectionQuery(text="A  B", status=2, rating="8")
    assert first == second
    assert first.tokens == ("a", "b")
