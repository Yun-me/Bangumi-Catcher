"""Regression tests for the analysis engine.

The central historical bug was counting unrated entries as ``0`` in average
ratings; these tests pin the documented semantics.
"""

from __future__ import annotations

from datetime import datetime

from bangumi_catcher.core.analysis import analyze
from bangumi_catcher.core.models import AnalysisReport
from tests.factories import make_collection, make_item


def test_overall_avg_excludes_unrated(sample_collection):
    report = analyze(sample_collection)
    # finished scores: 8, 0 (unrated), 6 -> only 8 and 6 count => 7.0
    assert report.overall_avg_rating == 7.0


def test_year_avg_only_rated(sample_collection):
    report = analyze(sample_collection)
    year_2020 = report.by_year[2020]
    # two finished entries in 2020, one unrated -> average stays 8.0
    assert year_2020.avg_rating == 8.0
    assert year_2020.finished == 2


def test_type_counts(sample_collection):
    report = analyze(sample_collection)
    assert report.type_counts["看过"] == 3
    assert report.type_counts["想看"] == 1
    assert report.type_counts["在看"] == 1


def test_completion_rate(sample_collection):
    report = analyze(sample_collection)
    assert 0 < report.avg_completion <= 100


def test_tag_stats(sample_collection):
    report = analyze(sample_collection)
    assert report.tag_counts.get("原创") == 5
    assert report.top_tags and report.top_tags[0].name == "原创"
    assert report.top_tags[0].count == 5


def test_default_year_range_includes_current_year(sample_collection):
    current_year = datetime.now().year
    sample_collection.items[0].subject.date = f"{current_year}-01-01"
    assert current_year in analyze(sample_collection).by_year


def test_top_rated_requires_finished_and_five_plus():
    items = [
        make_item(1, 2, 9, year=2020),
        make_item(2, 2, 4, year=2020),  # rated below 5
        make_item(3, 3, 9, year=2020),  # still watching
        make_item(4, 1, 9, year=2020),  # wish
    ]
    report = analyze(make_collection(items))
    assert [entry.subject_id for entry in report.top_rated] == [1]


def test_top_n_limits_ranking_and_tags():
    items = [make_item(index, 2, 8, year=2020, tags=("tag", f"tag{index}")) for index in range(1, 8)]
    report = analyze(make_collection(items), top_n=3)
    assert len(report.top_rated) == 3
    assert len(report.top_tags) == 3


def test_season_stats_skip_entries_without_dates():
    items = [
        make_item(1, 2, 8, year=None),
        make_item(2, 2, 8, year=2021),
    ]
    report = analyze(make_collection(items))
    assert [entry.season for entry in report.season_stats] == ["Q2"]


def test_empty_collection_produces_empty_report():
    report = analyze(make_collection([]))
    assert isinstance(report, AnalysisReport)
    assert report.total_items == 0
    assert report.top_rated == []
    assert report.overall_avg_rating == 0.0
    assert report.avg_completion == 0.0


def test_year_window_excludes_out_of_range_years():
    items = [make_item(1, 2, 8, year=1990), make_item(2, 2, 8, year=2024)]
    report = analyze(make_collection(items), year_start=2000, year_end=2024)
    assert list(report.by_year) == [2024]


def test_type_trend_and_rating_compare_are_consistent(sample_collection):
    report = analyze(sample_collection)
    by_year = {entry.year: entry for entry in report.type_trend}
    assert by_year[2020].finished == 2
    assert report.rating_compare
    assert report.rating_compare[0].my_rate >= report.rating_compare[-1].my_rate
