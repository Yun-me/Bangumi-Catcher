"""Snapshot import and username normalisation (no network)."""

from __future__ import annotations

import json

import pytest

from bangumi_catcher.reporting import collection_to_json
from bangumi_catcher.services.library import load_collection, normalize_username


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("  alice_123-4 ", "alice_123-4"),
        ("12345", "12345"),
        ("https://bgm.tv/user/alice?ref=nav#collections", "alice"),
        ("https://bangumi.tv/user/12345/", "12345"),
        ("chii.in/user/alice", "alice"),
        ("https://bgm.tv/user/%61lice", "alice"),
        ("https://www.bgm.tv/user/alice", "alice"),
    ],
)
def test_normalize_username(value, expected):
    assert normalize_username(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "显示昵称",
        "../alice",
        "alice/bob",
        "alice\\bob",
        "alice?x=1",
        "https://evil.example/user/alice",
        "https://bgm.tv/subject/1",
        "https://bgm.tv/user/alice%2fbob",
        "file:///user/alice",
    ],
)
def test_reject_invalid_user_inputs(value):
    with pytest.raises(ValueError):
        normalize_username(value)


def test_snapshot_round_trip(tmp_path, sample_collection):
    sample_collection.subject_type = 2
    path = tmp_path / "snapshot.json"
    collection_to_json(sample_collection, path)
    assert load_collection(path) == sample_collection


def test_legacy_snapshot_and_bom(tmp_path, sample_collection):
    data = sample_collection.model_dump(mode="json")
    data.pop("subject_type")
    data["total"] = 999
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(data), encoding="utf-8-sig")
    restored = load_collection(path)
    assert restored.subject_type is None
    assert restored.total == len(sample_collection.items)


@pytest.mark.parametrize("data", [{"username": "alice", "total_items": 2}, [], {"items": []}])
def test_reject_reports_and_wrong_shapes(tmp_path, data):
    path = tmp_path / "not-a-collection.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="收藏 JSON"):
        load_collection(path)


def test_reject_oversize_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr("bangumi_catcher.services.library.MAX_IMPORT_BYTES", 10)
    path = tmp_path / "large.json"
    path.write_bytes(b" " * 11)
    with pytest.raises(ValueError, match="64 MB"):
        load_collection(path)


def test_missing_file_raises_oserror(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_collection(tmp_path / "missing.json")
