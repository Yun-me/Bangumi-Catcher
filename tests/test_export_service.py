import csv

import pytest

from bangumi_catcher.core.config import AppConfig
from bangumi_catcher.core.exceptions import OperationCancelled
from bangumi_catcher.services.export_service import export_dataset
from bangumi_catcher.services.fetch_service import analyze_user_collection
from bangumi_catcher.services.library_service import load_collection


@pytest.mark.parametrize("format_name", ["csv", "json", "report-json", "html"])
def test_export_creates_parent_directories(tmp_path, sample_collection, format_name):
    config = AppConfig()
    report = analyze_user_collection(sample_collection, config)
    output = tmp_path / "nested" / f"report.{format_name}"
    assert export_dataset(sample_collection, report, output, format_name, config) == output
    assert output.stat().st_size > 0
    assert list(output.parent.iterdir()) == [output]
    if format_name == "json":
        assert load_collection(output) == sample_collection
    elif format_name == "html":
        html = output.read_text(encoding="utf-8")
        assert "data:image/png;base64," in html
        assert "tester" in html


def test_cancelled_export_preserves_existing_file(tmp_path, sample_collection):
    config = AppConfig()
    report = analyze_user_collection(sample_collection, config)
    output = tmp_path / "collection.json"
    output.write_text("previous export", encoding="utf-8")

    def cancel_before_commit(fraction, message):
        if fraction == 1.0:
            raise OperationCancelled("cancelled")

    with pytest.raises(OperationCancelled):
        export_dataset(sample_collection, report, output, "json", config, cancel_before_commit)
    assert output.read_text(encoding="utf-8") == "previous export"
    assert list(tmp_path.iterdir()) == [output]


def test_export_failure_removes_temporary_file(tmp_path, sample_collection, monkeypatch):
    config = AppConfig()
    report = analyze_user_collection(sample_collection, config)

    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("bangumi_catcher.services.export_service.collection_to_json", fail)
    with pytest.raises(OSError, match="disk full"):
        export_dataset(sample_collection, report, tmp_path / "result.json", "json", config)
    assert not list(tmp_path.iterdir())


def test_csv_keeps_tags_and_neutralizes_formulas(tmp_path, sample_collection):
    sample_collection.items[0].comment = "=HYPERLINK(\"bad\")"
    sample_collection.items[0].tags = ["原创", "日常"]
    config = AppConfig()
    report = analyze_user_collection(sample_collection, config)
    output = tmp_path / "collection.csv"
    export_dataset(sample_collection, report, output, "csv", config)
    with output.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["comment"].startswith("'=")
    assert rows[0]["tags"] == "原创 / 日常"
