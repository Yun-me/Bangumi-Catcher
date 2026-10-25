"""Mapping between Bangumi's two subject payload shapes and domain models."""

from __future__ import annotations

import json

from bangumi_catcher.api.mapping import (
    build_collection_item,
    build_subject,
    safe_build_subject,
)
from tests.helpers import read_fixture


def test_slim_subject_flat_score_maps():
    # slim shape: flat score/rank, eps only, no total_episodes
    slim = {"id": 1, "name": "x", "date": "2021-04-01", "score": 8.4, "rank": 120, "eps": 24}
    subject = build_subject(slim)
    assert subject.score == 8.4
    assert subject.rank == 120
    assert subject.episodes_total == 24


def test_full_subject_nested_rating_maps():
    full = {
        "id": 1,
        "name": "x",
        "rating": {"score": 8.4, "rank": 120, "total": 5000},
        "total_episodes": 24,
        "eps": 24,
    }
    subject = build_subject(full)
    assert subject.score == 8.4
    assert subject.episodes_total == 24


def test_unrated_slim_stays_zero():
    assert build_subject({"id": 2, "name": "y", "score": 0, "eps": 12}).score == 0.0


def test_short_summary_fallback():
    assert build_subject({"id": 3, "name": "z", "short_summary": "简介", "eps": 1}).summary == "简介"


def test_recorded_payload_fixtures_still_parse():
    slim = json.loads(read_fixture("bangumi/slim_subject.json"))
    full = json.loads(read_fixture("bangumi/full_subject.json"))
    assert build_subject(slim).score == 8.8
    assert build_subject(full).summary == "勇者一行击败魔王之后的故事。"
    assert build_subject(full).episodes_total == 28


def test_recorded_collection_page_builds_items():
    page = json.loads(read_fixture("bangumi/collection_page.json"))
    items = [build_collection_item(entry) for entry in page["data"]]
    assert [item.subject_id for item in items] == [101, 102]
    assert items[0].tags == ["奇幻", "治愈"]
    assert items[0].subject_name == "葬送的芙莉莲"
    assert items[1].completion_rate == 4 / 24


def test_collection_item_falls_back_to_subject_id():
    item = build_collection_item({"subject": {"id": 9, "name": "x"}})
    assert item.subject_id == 9
    assert item.subject is not None


def test_dirty_subject_is_dropped_not_fatal():
    item = build_collection_item({"subject_id": 5, "subject": {"id": "oops", "eps": []}})
    assert item.subject_id == 5
    assert item.subject is None


def test_safe_build_subject_handles_non_mapping():
    assert safe_build_subject(None) is None
    assert safe_build_subject("nope") is None
    assert safe_build_subject({}) is None
