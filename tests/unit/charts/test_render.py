"""Chart registry and PNG rendering (Agg backend, no display required)."""

from __future__ import annotations

import pytest

from bangumi_catcher.charts.builders import FIGURE_BUILDERS
from bangumi_catcher.charts.catalog import CHART_TITLES
from bangumi_catcher.charts.render import build_figures, render_all, render_chart
from bangumi_catcher.core.analysis import analyze
from tests.factories import make_empty_report


def test_registry_matches_catalog_titles():
    assert set(FIGURE_BUILDERS) == set(CHART_TITLES)
    assert len(FIGURE_BUILDERS) == 9


def test_build_figures_keys(sample_collection):
    report = analyze(sample_collection)
    figures = build_figures(report)
    assert set(figures) == set(FIGURE_BUILDERS)
    assert len(figures) == 9


def test_render_all_returns_data_uris(sample_collection):
    report = analyze(sample_collection)
    uris = render_all(report)
    assert set(uris) == set(CHART_TITLES)
    assert all(value.startswith("data:image/png;base64,") for value in uris.values())


def test_rendered_chart_is_a_png(sample_collection):
    report = analyze(sample_collection)
    data = render_chart(report, "rating_distribution")
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(data) > 1000


def test_empty_report_renders_placeholder():
    data = render_chart(make_empty_report(), "yearly_trend")
    assert data.startswith(b"\x89PNG")


def test_unknown_chart_key_raises():
    with pytest.raises(KeyError, match="未知图表维度"):
        render_chart(make_empty_report(), "not-a-chart")


def test_dark_and_light_renders_differ(sample_collection):
    report = analyze(sample_collection)
    light = render_chart(report, "yearly_trend", dark=False)
    dark = render_chart(report, "yearly_trend", dark=True)
    assert light != dark
