"""One builder per chart dimension.

Every builder accepts ``(report, theme)`` and returns a Matplotlib
:class:`~matplotlib.figure.Figure`. Builders never touch Qt, files or global
state, so they can be exercised from tests and the HTML exporter alike.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from matplotlib.figure import Figure

from ..core.models import AnalysisReport
from .theme import (
    ACCENT,
    ACCENT2,
    DARK,
    LIGHT,
    PALETTE,
    apply_cjk_font,
    create_figure,
    empty_figure,
    font_properties,
    set_title,
)

logger = logging.getLogger(__name__)

Theme = dict[str, str]
Builder = Callable[[AnalysisReport, Theme], Figure]


def make_rating_distribution(report: AnalysisReport, theme: Theme = LIGHT) -> Figure:
    counts = report.rating_distribution
    if not counts or sum(counts.values()) == 0:
        return empty_figure("评分分布", theme)
    figure, axes = create_figure(theme)
    scores = list(range(1, 11))
    values = [counts.get(score, 0) for score in scores]
    bars = axes.bar(scores, values, color=ACCENT, width=0.72, zorder=3)
    for bar, value in zip(bars, values):
        if value:
            axes.text(
                bar.get_x() + bar.get_width() / 2,
                value,
                str(value),
                ha="center",
                va="bottom",
                fontsize=8,
                color=theme["muted"],
            )
    set_title(axes, "我的评分分布", theme)
    axes.set_xticks(scores)
    axes.set_xlabel("评分", color=theme["muted"])
    axes.set_ylabel("数量", color=theme["muted"])
    apply_cjk_font(axes)
    return figure


def make_type_distribution(report: AnalysisReport, theme: Theme = LIGHT) -> Figure:
    by_type = report.type_counts
    if not by_type:
        return empty_figure("收藏状态分布", theme)
    figure, axes = create_figure(theme, 5.6, 4.0, constrained=False)
    figure.subplots_adjust(left=0.0, right=0.66, top=0.88, bottom=0.04)
    labels, sizes = list(by_type), list(by_type.values())
    wedges, _, autotexts = axes.pie(
        sizes,
        labels=None,
        colors=PALETTE[: len(labels)],
        autopct=lambda percent: f"{percent:.0f}%" if percent >= 4 else "",
        startangle=90,
        pctdistance=0.78,
        wedgeprops={"width": 0.42, "edgecolor": theme["edge"], "linewidth": 2},
    )
    for text in autotexts:
        text.set_color("white")
        text.set_fontsize(9)
    axes.legend(
        wedges,
        labels,
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        frameon=False,
        fontsize=9,
        labelcolor=theme["text"],
        prop=font_properties(),
    )
    set_title(axes, "收藏状态分布", theme)
    axes.axis("equal")
    return figure


def make_yearly_trend(report: AnalysisReport, theme: Theme = LIGHT) -> Figure:
    by_year = {item.year: item.total for item in report.year_trend if item.total > 0}
    if not by_year:
        return empty_figure("年度收藏趋势", theme)
    figure, axes = create_figure(theme, 7.0, 3.6)
    years = sorted(by_year)
    values = [by_year[year] for year in years]
    axes.plot(
        years,
        values,
        color=ACCENT,
        linewidth=2.4,
        marker="o",
        markersize=5,
        markerfacecolor=theme["edge"],
        markeredgecolor=ACCENT,
        zorder=3,
    )
    axes.fill_between(years, values, color=ACCENT, alpha=0.12, zorder=2)
    set_title(axes, "年度收藏趋势", theme)
    axes.set_xlabel("年份", color=theme["muted"])
    axes.set_ylabel("数量", color=theme["muted"])
    apply_cjk_font(axes)
    return figure


def make_yearly_rating(report: AnalysisReport, theme: Theme = LIGHT) -> Figure:
    averages = {item.year: item.avg_rating for item in report.year_trend if item.avg_rating > 0}
    if not averages:
        return empty_figure("年度平均评分", theme)
    figure, axes = create_figure(theme, 7.0, 3.6)
    years = sorted(averages)
    values = [averages[year] for year in years]
    axes.plot(
        years,
        values,
        color=ACCENT2,
        linewidth=2.4,
        marker="o",
        markersize=5,
        markerfacecolor=theme["edge"],
        markeredgecolor=ACCENT2,
        zorder=3,
    )
    axes.set_ylim(0, 10)
    set_title(axes, "年度平均评分", theme)
    axes.set_xlabel("年份", color=theme["muted"])
    axes.set_ylabel("平均分", color=theme["muted"])
    apply_cjk_font(axes)
    return figure


def make_top_rated(report: AnalysisReport, theme: Theme = LIGHT) -> Figure:
    items = report.top_rated
    if not items:
        return empty_figure("最爱排行", theme)
    items = list(reversed(items[:15]))
    figure, axes = create_figure(theme, 6.4, max(3.0, len(items) * 0.36))
    labels = [(item.name_cn or item.name)[:18] for item in items]
    rates = [item.rate for item in items]
    axes.barh(range(len(labels)), rates, color=ACCENT, zorder=3, height=0.7)
    for position, rate in enumerate(rates):
        axes.text(
            rate - 0.15,
            position,
            str(rate),
            ha="right",
            va="center",
            fontsize=8,
            color="white",
            fontweight="bold",
        )
    axes.set_yticks(range(len(labels)))
    axes.set_yticklabels(labels)
    axes.set_xlim(0, 10)
    axes.grid(axis="x", color=theme["grid"], linewidth=0.8, alpha=0.7)
    axes.grid(axis="y", visible=False)
    set_title(axes, "我的最爱 Top 15", theme)
    apply_cjk_font(axes)
    return figure


def make_season_distribution(report: AnalysisReport, theme: Theme = LIGHT) -> Figure:
    seasons = [item for item in report.season_stats if item.season]
    if not seasons:
        return empty_figure("追番季度分布", theme)
    figure, axes = create_figure(theme, 5.0, 3.6)
    labels = [item.season for item in seasons]
    values = [item.count for item in seasons]
    axes.bar(labels, values, color=PALETTE[: len(labels)], width=0.6, zorder=3)
    for position, value in enumerate(values):
        axes.text(position, value, str(value), ha="center", va="bottom", fontsize=9, color=theme["muted"])
    set_title(axes, "追番季度分布", theme)
    axes.set_ylabel("数量", color=theme["muted"])
    apply_cjk_font(axes)
    return figure


def make_top_tags(report: AnalysisReport, theme: Theme = LIGHT) -> Figure:
    tags = report.top_tags[:15]
    if not tags:
        return empty_figure("热门标签", theme)
    figure, axes = create_figure(theme, 6.4, max(3.0, len(tags) * 0.36))
    labels = [tag.name[:16] for tag in reversed(tags)]
    counts = [tag.count for tag in reversed(tags)]
    axes.barh(range(len(labels)), counts, color=ACCENT2, zorder=3, height=0.7)
    for position, count in enumerate(counts):
        axes.text(count + 0.1, position, str(count), ha="left", va="center", fontsize=8, color=theme["muted"])
    axes.set_yticks(range(len(labels)))
    axes.set_yticklabels(labels)
    axes.set_xlabel("出现次数", color=theme["muted"])
    axes.grid(axis="x", color=theme["grid"], linewidth=0.8, alpha=0.7)
    axes.grid(axis="y", visible=False)
    set_title(axes, "热门标签 Top 15", theme)
    apply_cjk_font(axes)
    return figure


def make_rating_compare(report: AnalysisReport, theme: Theme = LIGHT) -> Figure:
    pairs = report.rating_compare
    if not pairs:
        return empty_figure("我的评分 vs 全站均分", theme)
    figure, axes = create_figure(theme, 5.6, 4.4)
    x_values = [pair.bgm_score for pair in pairs]
    y_values = [pair.my_rate for pair in pairs]
    axes.scatter(
        x_values, y_values, s=42, color=ACCENT, alpha=0.6, edgecolors=theme["edge"], linewidths=0.6, zorder=3
    )
    limits = [0, 10]
    axes.plot(limits, limits, color=theme["muted"], linewidth=1, linestyle="--", alpha=0.7, zorder=2)
    axes.set_xlim(4, 10)
    axes.set_ylim(0, 10)
    set_title(axes, "我的评分 vs 全站均分", theme)
    axes.set_xlabel("全站均分", color=theme["muted"])
    axes.set_ylabel("我的评分", color=theme["muted"])
    axes.grid(True, color=theme["grid"], linewidth=0.8, alpha=0.6)
    apply_cjk_font(axes)
    return figure


def make_type_trend(report: AnalysisReport, theme: Theme = LIGHT) -> Figure:
    trend = [
        item
        for item in report.type_trend
        if item.finished + item.watching + item.wish + item.on_hold + item.dropped > 0
    ]
    if not trend:
        return empty_figure("收藏状态年度堆叠", theme)
    figure, axes = create_figure(theme, 7.0, 3.8)
    years = [item.year for item in trend]
    series = [
        ("看过", [item.finished for item in trend]),
        ("在看", [item.watching for item in trend]),
        ("想看", [item.wish for item in trend]),
        ("搁置", [item.on_hold for item in trend]),
        ("抛弃", [item.dropped for item in trend]),
    ]
    bottom = [0] * len(years)
    for (label, values), color in zip(series, PALETTE):
        axes.bar(years, values, bottom=bottom, label=label, color=color, width=0.8, zorder=3)
        bottom = [base + value for base, value in zip(bottom, values)]
    axes.legend(
        loc="upper left", frameon=False, fontsize=8, ncol=5, labelcolor=theme["text"], prop=font_properties()
    )
    set_title(axes, "收藏状态年度构成", theme)
    axes.set_xlabel("年份", color=theme["muted"])
    axes.set_ylabel("数量", color=theme["muted"])
    apply_cjk_font(axes)
    return figure


FIGURE_BUILDERS: dict[str, Builder] = {
    "rating_distribution": make_rating_distribution,
    "type_distribution": make_type_distribution,
    "yearly_trend": make_yearly_trend,
    "yearly_rating": make_yearly_rating,
    "top_rated": make_top_rated,
    "season_distribution": make_season_distribution,
    "top_tags": make_top_tags,
    "rating_compare": make_rating_compare,
    "type_trend": make_type_trend,
}

# ``DARK`` is re-exported for callers that build figures directly.
__all__ = ["DARK", "FIGURE_BUILDERS", "Theme"]
