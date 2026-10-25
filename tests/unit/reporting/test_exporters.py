"""Exporter primitives: CSV safety, JSON round-trip, atomic replace, HTML.

The HTML test stubs the chart renderer, so this module never imports Matplotlib.
"""

from __future__ import annotations

import csv
import json

import pytest

from bangumi_catcher.charts.catalog import CHART_TITLES
from bangumi_catcher.core.analysis import analyze
from bangumi_catcher.core.models import AnalysisReport
from bangumi_catcher.reporting import (
    atomic_output,
    build_html_report,
    collection_to_csv,
    collection_to_json,
    report_to_json,
)
from bangumi_catcher.reporting.csv_export import spreadsheet_safe_text
from bangumi_catcher.services.library import load_collection
from tests.factories import make_empty_report


def test_spreadsheet_safe_text():
    assert spreadsheet_safe_text("=1+1") == "'=1+1"
    assert spreadsheet_safe_text("+SUM(A1)") == "'+SUM(A1)"
    assert spreadsheet_safe_text("-1") == "'-1"
    assert spreadsheet_safe_text("@cmd") == "'@cmd"
    assert spreadsheet_safe_text("normal") == "normal"
    assert spreadsheet_safe_text("\tleading tab") == "'\tleading tab"


def test_csv_writes_header_and_rows(tmp_path, sample_collection):
    output = tmp_path / "collection.csv"
    collection_to_csv(sample_collection, output)
    with output.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 5
    assert rows[0]["tags"] == "原创"
    assert rows[0]["name"] == "Anime1"
    assert rows[0]["name_cn"] == "动画1"


def test_json_collection_round_trip(tmp_path, sample_collection):
    output = tmp_path / "collection.json"
    collection_to_json(sample_collection, output)
    assert load_collection(output) == sample_collection


def test_report_json_is_not_a_collection_snapshot(tmp_path, sample_collection):
    output = tmp_path / "report.json"
    report_to_json(analyze(sample_collection), output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "total_items" in data
    with pytest.raises(ValueError, match="收藏 JSON"):
        load_collection(output)


def test_atomic_output_replaces_target(tmp_path):
    target = tmp_path / "result.txt"
    target.write_text("old", encoding="utf-8")
    with atomic_output(target) as temporary:
        temporary.write_text("new", encoding="utf-8")
    assert target.read_text(encoding="utf-8") == "new"
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_output_preserves_target_on_failure(tmp_path):
    target = tmp_path / "result.txt"
    target.write_text("old", encoding="utf-8")
    with pytest.raises(RuntimeError), atomic_output(target) as temporary:
        temporary.write_text("partial", encoding="utf-8")
        raise RuntimeError("boom")
    assert target.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.iterdir()) == [target]


def test_html_report_renders_template(monkeypatch, sample_collection):
    charts = dict.fromkeys(CHART_TITLES, "data:image/png;base64,AAAA")
    monkeypatch.setattr("bangumi_catcher.charts.render.render_all", lambda report, progress=None: charts)
    html = build_html_report(analyze(sample_collection))
    assert "tester" in html
    assert "data:image/png;base64,AAAA" in html
    assert "评分分布" in html


def test_html_report_escapes_user_content(monkeypatch):
    monkeypatch.setattr(
        "bangumi_catcher.charts.render.render_all",
        lambda report, progress=None: dict.fromkeys(CHART_TITLES, ""),
    )
    report = AnalysisReport(username="<script>alert(1)</script>", total_items=0)
    html = build_html_report(report)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_empty_report_html_omits_chart_cards(monkeypatch):
    monkeypatch.setattr("bangumi_catcher.charts.render.render_all", lambda report, progress=None: {})
    html = build_html_report(make_empty_report())
    assert "<img" not in html
