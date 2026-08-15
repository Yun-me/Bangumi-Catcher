"""图表引擎 smoke 测试 —— Agg 后端，无需显示器。"""
from bangumi_catcher.core.analyzer import analyze
from bangumi_catcher.ui import visualizer


def test_build_figures_keys(sample_collection):
    rep = analyze(sample_collection)
    figs = visualizer.build_figures(rep)
    assert set(figs) == set(visualizer.FIGURE_BUILDERS)
    assert len(figs) == 9


def test_render_all_data_uris(sample_collection):
    rep = analyze(sample_collection)
    uris = visualizer.render_all(rep)
    assert all(v.startswith("data:image/png;base64,") for v in uris.values())


def test_empty_report_no_crash():
    from bangumi_catcher.core.models import AnalysisReport
    rep = AnalysisReport(username="x", total_items=0)
    uris = visualizer.render_all(rep)
    assert all(v.startswith("data:image") for v in uris.values())
