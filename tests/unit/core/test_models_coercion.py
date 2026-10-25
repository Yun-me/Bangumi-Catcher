"""Lenient field validation: one dirty API row must never abort a sync."""

from __future__ import annotations

import pytest

from bangumi_catcher.core.models import CollectionItem, Subject


def test_null_rate_becomes_zero():
    assert CollectionItem(subject_id=1, rate=None).rate == 0


def test_rate_string_coerced():
    assert CollectionItem(subject_id=1, rate="8").rate == 8


def test_rate_clamped_high_and_low():
    assert CollectionItem(subject_id=1, rate=15).rate == 10
    assert CollectionItem(subject_id=1, rate=-3).rate == 0


def test_rate_garbage_becomes_zero():
    assert CollectionItem(subject_id=1, rate="N/A").rate == 0


def test_type_and_status_null_safe():
    item = CollectionItem(subject_id=1, type=None, ep_status=None, vol_status=None)
    assert (item.type, item.ep_status, item.vol_status) == (0, 0, 0)


def test_tags_null_becomes_empty_list():
    assert CollectionItem(subject_id=1, tags=None).tags == []


def test_tags_object_form_supported():
    item = CollectionItem(subject_id=1, tags=[{"name": "原创"}, "TV", 123])
    assert item.tags == ["原创", "TV"]


def test_subject_null_ints_safe():
    subject = Subject(id=1, name="x", eps=None, total_episodes=None, rank=None)
    assert (subject.eps, subject.total_episodes, subject.rank) == (0, 0, 0)


def test_subject_numeric_string_coerced():
    assert Subject(id=1, name="x", total_episodes="24").total_episodes == 24


def test_subject_null_str_fields_safe():
    subject = Subject(id=1, name="x", date=None)
    assert subject.date == ""
    assert subject.year is None


@pytest.mark.parametrize("bad", ["", None, "oops"])
def test_subject_rank_robust(bad):
    assert Subject(id=1, name="x", rank=bad).rank == 0


def test_comment_and_name_null_safe():
    item = CollectionItem(subject_id=1, comment=None, name=None, updated_at=None)
    assert (item.comment, item.name, item.updated_at) == ("", "", "")
