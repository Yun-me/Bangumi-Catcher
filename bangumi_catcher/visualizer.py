"""Plotly 可视化 —— 返回 Plotly Figure 对象 (供 CLI 和 GUI 复用)."""

from __future__ import annotations

import logging
from pathlib import Path

import plotly.graph_objects as go

from .models import AnalysisReport

logger = logging.getLogger(__name__)

# 配色方案
COLORS = {
    "finished":  "#4CAF50",
    "watching":  "#2196F3",
    "wish":      "#FF9800",
    "on_hold":   "#9E9E9E",
    "dropped":   "#f44336",
    "rating":    "#E91E63",
    "top":       "#673AB7",
}


def _ensure_dir(path: str) -> Path:
    p = Path(path).parent
    p.mkdir(parents=True, exist_ok=True)
    return p


def fig_yearly_trend(report: AnalysisReport) -> go.Figure:
    """年度收藏趋势 —— 堆叠柱状图."""
    years = [d.year for d in report.year_trend]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="看过", x=years, y=[d.finished for d in report.year_trend], marker_color=COLORS["finished"]))
    fig.add_trace(go.Bar(name="在看", x=years, y=[d.watching for d in report.year_trend], marker_color=COLORS["watching"]))
    fig.add_trace(go.Bar(name="想看", x=years, y=[d.wish for d in report.year_trend], marker_color=COLORS["wish"]))
    fig.update_layout(
        title=f"{report.username} 年度收藏趋势",
        xaxis_title="年份", yaxis_title="数量",
        barmode="stack", template="plotly_white",
        height=500, width=900,
    )
    return fig


def fig_rating_distribution(report: AnalysisReport) -> go.Figure:
    """评分分布 —— 柱状图."""
    scores = sorted(report.rating_distribution.keys())
    counts = [report.rating_distribution[s] for s in scores]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[str(s) for s in scores], y=counts,
        marker_color=COLORS["rating"],
        text=counts, textposition="outside",
    ))
    fig.update_layout(
        title=f"{report.username} 评分分布",
        xaxis_title="评分", yaxis_title="数量",
        template="plotly_white", height=500, width=900,
    )
    return fig


def fig_collection_pie(report: AnalysisReport) -> go.Figure:
    """收藏类型饼图."""
    labels = list(report.type_counts.keys())
    values = list(report.type_counts.values())
    type_colors = {
        "看过": COLORS["finished"], "在看": COLORS["watching"],
        "想看": COLORS["wish"], "搁置": COLORS["on_hold"], "抛弃": COLORS["dropped"],
    }
    marker_colors = [type_colors.get(l, "#607D8B") for l in labels]
    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=labels, values=values,
        marker=dict(colors=marker_colors),
        textinfo="label+percent+value", hole=0.3,
    ))
    fig.update_layout(
        title=f"{report.username} 收藏分布",
        template="plotly_white", height=500, width=700,
    )
    return fig


def fig_top_rated(report: AnalysisReport) -> go.Figure:
    """高评分 Top N —— 横向柱状图."""
    items = list(reversed(report.top_rated))
    names = [it.name_cn or it.name for it in items]
    rates = [it.rate for it in items]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=rates, y=names, orientation="h",
        marker_color=COLORS["top"],
        text=rates, textposition="outside",
    ))
    fig.update_layout(
        title=f"{report.username} 最爱 Top {len(report.top_rated)}",
        xaxis_title="评分", template="plotly_white",
        height=max(400, len(names) * 25), width=900,
        margin=dict(l=200),
    )
    return fig


# --- 生成图片文件 (CLI 用) ---

def save_chart(fig: go.Figure, output_path: str, scale: int = 2) -> str:
    """保存图表为 PNG."""
    _ensure_dir(output_path)
    fig.write_image(output_path, format="png", scale=scale)
    logger.info("图表已保存: %s", output_path)
    return output_path


def generate_all_charts(report: AnalysisReport, output_dir: str) -> dict[str, str]:
    """生成全部四张图表并保存, 返回 {名称: 路径}."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    charts = {
        "yearly_trend":        (fig_yearly_trend, "yearly_trend.png"),
        "rating_distribution":  (fig_rating_distribution, "rating_distribution.png"),
        "collection_pie":      (fig_collection_pie, "collection_pie.png"),
        "top_rated":           (fig_top_rated, "top_rated.png"),
    }

    result: dict[str, str] = {}
    for name, (fig_fn, filename) in charts.items():
        fig = fig_fn(report)
        result[name] = save_chart(fig, str(out / filename))

    return result
