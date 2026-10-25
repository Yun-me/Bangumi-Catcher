"""Computed model fields and small domain helpers."""

from __future__ import annotations

from bangumi_catcher.core.models import (
    COLLECTION_TYPE_MAP,
    CollectionItem,
    Subject,
    collection_type_name,
    parse_season,
    parse_year,
    subject_type_name,
)


def test_subject_year_and_season():
    subject = Subject(id=1, name="x", date="2021-07-08")
    assert subject.year == 2021
    assert subject.season == "Q3"


def test_collection_type_name():
    assert CollectionItem(subject_id=1, type=2).collection_type_name == "看过"
    assert collection_type_name(2) == "看过"
    assert collection_type_name(99) == "未知(99)"
    assert COLLECTION_TYPE_MAP[5] == "抛弃"


def test_subject_type_names():
    assert subject_type_name(2) == "动画"
    assert subject_type_name(None) == "未标注分类"
    assert subject_type_name(99) == "未标注分类"


def test_parse_helpers_are_defensive():
    assert parse_year("") is None
    assert parse_year("abcd-01-01") is None
    assert parse_year("2024") == 2024
    assert parse_season("2024-01") == "Q1"
    assert parse_season("2024-12") == "Q4"
    assert parse_season("2024-13") == ""
    assert parse_season("2024") == ""


def test_display_name_prefers_chinese_title_then_original_then_id():
    item = CollectionItem(subject_id=7, name="fallback")
    assert item.subject_name == "fallback"
    item.subject = Subject(id=7, name="Original")
    assert item.subject_name == "Original"
    item.subject.name_cn = "中文名"
    assert item.subject_name == "中文名"
    assert CollectionItem(subject_id=8).subject_name == "#8"
