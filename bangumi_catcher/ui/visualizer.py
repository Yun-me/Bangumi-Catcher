"""Agg 图表引擎：GUI 与 HTML 共用构建器，渲染入口以锁串行化。

桌面后台按需生成 PNG；主线程仅显示与缩放图像，不访问 Matplotlib 对象。
HTML 导出固定使用浅色主题，不依赖 Qt 或浏览器。
"""

from __future__ import annotations

import base64
import io
import threading
from typing import Callable

import matplotlib.font_manager as fm
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from ..core.models import AnalysisReport
from .chart_catalog import CHART_TITLES as CHART_TITLES

_RENDER_LOCK = threading.RLock()

# 分类色板（亮/暗通用，均经过对比度校验）
PALETTE = ["#219D83", "#6291D5", "#E7B35C", "#D87988", "#9482C3", "#52ABB9", "#CE8654"]
ACCENT, ACCENT2 = "#219D83", "#6291D5"

# 主题相关：仅文字/网格/分隔线随主题切换，数据色保持一致便于跨主题对照
LIGHT = {"text": "#2C2E33", "muted": "#8A929E", "grid": "#E6E8EB",
         "edge": "#FFFFFF", "empty": "#B7BDC6"}
DARK = {"text": "#E7EAF0", "muted": "#9AA3B2", "grid": "#3A414D",
        "edge": "#252A34", "empty": "#5B6472"}

_CJK = ["Microsoft YaHei", "PingFang SC", "SimHei", "Noto Sans CJK SC",
        "Noto Sans CJK JP", "WenQuanYi Zen Hei"]
_CJK_FONT = next((n for n in _CJK if n in {f.name for f in fm.fontManager.ttflist}), None)
_FONT = _CJK_FONT or "DejaVu Sans"


def _fig(th: dict, w: float = 6.4, h: float = 4.0, constrained: bool = True):
    fg = Figure(figsize=(w, h), dpi=100, layout="constrained" if constrained else None)
    fg.patch.set_facecolor("none")          # 透明底，融入卡片背景
    ax = fg.add_subplot(111)
    ax.set_facecolor("none")
    for o in (ax.title, ax.xaxis.label, ax.yaxis.label):
        o.set_fontfamily(_FONT)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(th["grid"])
    ax.spines["bottom"].set_color(th["grid"])
    ax.tick_params(colors=th["muted"], labelsize=9)
    ax.grid(axis="y", color=th["grid"], linewidth=0.8, alpha=0.7)
    ax.set_axisbelow(True)
    return fg, ax


def _cjk(ax):
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontfamily(_FONT)


def _title(ax, t: str, th: dict):
    ax.set_title(t, color=th["text"], fontsize=13, pad=12, fontfamily=_FONT, fontweight="bold")


def _empty(t: str, th: dict) -> Figure:
    fg, ax = _fig(th)
    ax.axis("off")
    ax.text(0.5, 0.5, "暂无数据", ha="center", va="center", fontsize=14,
            color=th["empty"], fontfamily=_FONT, transform=ax.transAxes)
    _title(ax, t, th)
    return fg


# ============================================================ 单图构建器

def make_rating_distribution(report: AnalysisReport, th: dict = LIGHT) -> Figure:
    counts = report.rating_distribution
    if not counts or sum(counts.values()) == 0:
        return _empty("评分分布", th)
    fg, ax = _fig(th)
    scores = list(range(1, 11))
    vals = [counts.get(s, 0) for s in scores]
    bars = ax.bar(scores, vals, color=ACCENT, width=0.72, zorder=3)
    for b, v in zip(bars, vals):
        if v:
            ax.text(b.get_x() + b.get_width() / 2, v, str(v), ha="center", va="bottom",
                    fontsize=8, color=th["muted"])
    _title(ax, "我的评分分布", th)
    ax.set_xticks(scores)
    ax.set_xlabel("评分", color=th["muted"])
    ax.set_ylabel("数量", color=th["muted"])
    _cjk(ax)
    return fg


def make_type_distribution(report: AnalysisReport, th: dict = LIGHT) -> Figure:
    by_type = report.type_counts
    if not by_type:
        return _empty("收藏状态分布", th)
    fg, ax = _fig(th, 5.6, 4.0, constrained=False)
    fg.subplots_adjust(left=0.0, right=0.66, top=0.88, bottom=0.04)
    labels, sizes = list(by_type), list(by_type.values())
    w, _, at = ax.pie(sizes, labels=None, colors=PALETTE[:len(labels)],
                      autopct=lambda p: f"{p:.0f}%" if p >= 4 else "",
                      startangle=90, pctdistance=0.78,
                      wedgeprops={"width": 0.42, "edgecolor": th["edge"], "linewidth": 2})
    for t in at:
        t.set_color("white")
        t.set_fontsize(9)
    ax.legend(w, labels, loc="center left", bbox_to_anchor=(1.0, 0.5),
              frameon=False, fontsize=9, labelcolor=th["text"],
              prop=fm.FontProperties(family=_FONT))
    _title(ax, "收藏状态分布", th)
    ax.axis("equal")
    return fg


def make_yearly_trend(report: AnalysisReport, th: dict = LIGHT) -> Figure:
    by_year = {d.year: d.total for d in report.year_trend if d.total > 0}
    if not by_year:
        return _empty("年度收藏趋势", th)
    fg, ax = _fig(th, 7.0, 3.6)
    years = sorted(by_year)
    vals = [by_year[y] for y in years]
    ax.plot(years, vals, color=ACCENT, linewidth=2.4, marker="o", markersize=5,
            markerfacecolor=th["edge"], markeredgecolor=ACCENT, zorder=3)
    ax.fill_between(years, vals, color=ACCENT, alpha=0.12, zorder=2)
    _title(ax, "年度收藏趋势", th)
    ax.set_xlabel("年份", color=th["muted"])
    ax.set_ylabel("数量", color=th["muted"])
    _cjk(ax)
    return fg


def make_yearly_rating(report: AnalysisReport, th: dict = LIGHT) -> Figure:
    avg = {d.year: d.avg_rating for d in report.year_trend if d.avg_rating > 0}
    if not avg:
        return _empty("年度平均评分", th)
    fg, ax = _fig(th, 7.0, 3.6)
    years = sorted(avg)
    vals = [avg[y] for y in years]
    ax.plot(years, vals, color=ACCENT2, linewidth=2.4, marker="o", markersize=5,
            markerfacecolor=th["edge"], markeredgecolor=ACCENT2, zorder=3)
    ax.set_ylim(0, 10)
    _title(ax, "年度平均评分", th)
    ax.set_xlabel("年份", color=th["muted"])
    ax.set_ylabel("平均分", color=th["muted"])
    _cjk(ax)
    return fg


def make_top_rated(report: AnalysisReport, th: dict = LIGHT) -> Figure:
    items = report.top_rated
    if not items:
        return _empty("最爱排行", th)
    items = list(reversed(items[:15]))
    fg, ax = _fig(th, 6.4, max(3.0, len(items) * 0.36))
    labels = [(it.name_cn or it.name)[:18] for it in items]
    rates = [it.rate for it in items]
    ax.barh(range(len(labels)), rates, color=ACCENT, zorder=3, height=0.7)
    for i, v in enumerate(rates):
        ax.text(v - 0.15, i, str(v), ha="right", va="center", fontsize=8,
                color="white", fontweight="bold")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 10)
    ax.grid(axis="x", color=th["grid"], linewidth=0.8, alpha=0.7)
    ax.grid(axis="y", visible=False)
    _title(ax, "我的最爱 Top 15", th)
    _cjk(ax)
    return fg


def make_season_distribution(report: AnalysisReport, th: dict = LIGHT) -> Figure:
    seasons = [s for s in report.season_stats if s.season]
    if not seasons:
        return _empty("追番季度分布", th)
    fg, ax = _fig(th, 5.0, 3.6)
    labels = [s.season for s in seasons]
    vals = [s.count for s in seasons]
    ax.bar(labels, vals, color=PALETTE[:len(labels)], width=0.6, zorder=3)
    for i, v in enumerate(vals):
        ax.text(i, v, str(v), ha="center", va="bottom", fontsize=9, color=th["muted"])
    _title(ax, "追番季度分布", th)
    ax.set_ylabel("数量", color=th["muted"])
    _cjk(ax)
    return fg


def make_top_tags(report: AnalysisReport, th: dict = LIGHT) -> Figure:
    tags = report.top_tags[:15]
    if not tags:
        return _empty("热门标签", th)
    fg, ax = _fig(th, 6.4, max(3.0, len(tags) * 0.36))
    labels = [t.name[:16] for t in reversed(tags)]
    counts = [t.count for t in reversed(tags)]
    ax.barh(range(len(labels)), counts, color=ACCENT2, zorder=3, height=0.7)
    for i, v in enumerate(counts):
        ax.text(v + 0.1, i, str(v), ha="left", va="center", fontsize=8, color=th["muted"])
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlabel("出现次数", color=th["muted"])
    ax.grid(axis="x", color=th["grid"], linewidth=0.8, alpha=0.7)
    ax.grid(axis="y", visible=False)
    _title(ax, "热门标签 Top 15", th)
    _cjk(ax)
    return fg


def make_rating_compare(report: AnalysisReport, th: dict = LIGHT) -> Figure:
    pairs = report.rating_compare
    if not pairs:
        return _empty("我的评分 vs 全站均分", th)
    fg, ax = _fig(th, 5.6, 4.4)
    xs = [p.bgm_score for p in pairs]
    ys = [p.my_rate for p in pairs]
    ax.scatter(xs, ys, s=42, color=ACCENT, alpha=0.6, edgecolors=th["edge"],
               linewidths=0.6, zorder=3)
    lim = [0, 10]
    ax.plot(lim, lim, color=th["muted"], linewidth=1, linestyle="--", alpha=0.7, zorder=2)
    ax.set_xlim(4, 10)
    ax.set_ylim(0, 10)
    _title(ax, "我的评分 vs 全站均分", th)
    ax.set_xlabel("全站均分", color=th["muted"])
    ax.set_ylabel("我的评分", color=th["muted"])
    ax.grid(True, color=th["grid"], linewidth=0.8, alpha=0.6)
    _cjk(ax)
    return fg


def make_type_trend(report: AnalysisReport, th: dict = LIGHT) -> Figure:
    tt = [t for t in report.type_trend if (t.finished + t.watching + t.wish + t.on_hold + t.dropped) > 0]
    if not tt:
        return _empty("收藏状态年度堆叠", th)
    fg, ax = _fig(th, 7.0, 3.8)
    years = [t.year for t in tt]
    series = [("看过", [t.finished for t in tt]), ("在看", [t.watching for t in tt]),
              ("想看", [t.wish for t in tt]), ("搁置", [t.on_hold for t in tt]),
              ("抛弃", [t.dropped for t in tt])]
    bottom = [0] * len(years)
    for (label, vals), color in zip(series, PALETTE):
        ax.bar(years, vals, bottom=bottom, label=label, color=color, width=0.8, zorder=3)
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.legend(loc="upper left", frameon=False, fontsize=8, ncol=5, labelcolor=th["text"],
              prop=fm.FontProperties(family=_FONT))
    _title(ax, "收藏状态年度构成", th)
    ax.set_xlabel("年份", color=th["muted"])
    ax.set_ylabel("数量", color=th["muted"])
    _cjk(ax)
    return fg


# 注册表：key 必须与 HTML 模板里的 {{ charts.<key> }} 对应
FIGURE_BUILDERS: dict[str, Callable[..., Figure]] = {
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

# GUI 标签页展示顺序与标题（无装饰性 emoji，保持克制）
def build_figures(report: AnalysisReport, dark: bool = False) -> dict[str, Figure]:
    """为 GUI 构建全部 Figure（按当前主题着色，可直接塞进 FigureCanvasQTAgg）。"""
    th = DARK if dark else LIGHT
    return {key: builder(report, th) for key, builder in FIGURE_BUILDERS.items()}


def render_chart(report: AnalysisReport, key: str, dark: bool = False) -> bytes:
    with _RENDER_LOCK:
        figure = FIGURE_BUILDERS[key](report, DARK if dark else LIGHT)
        try:
            FigureCanvasAgg(figure)
            output = io.BytesIO()
            figure.savefig(output, format="png", bbox_inches="tight",
                           facecolor="#1C2425" if dark else "#FFFFFF", dpi=160)
            return output.getvalue()
        finally:
            figure.clear()


def render_all(report: AnalysisReport,
               progress: Callable[[float, str], None] | None = None) -> dict[str, str]:
    """为 HTML 导出生成全部图表 base64 data-URI（固定浅色），返回 {模板key: uri}。"""
    out: dict[str, str] = {}
    items = list(FIGURE_BUILDERS)
    n = len(items)
    for i, key in enumerate(items):
        out[key] = "data:image/png;base64," + base64.b64encode(render_chart(report, key)).decode()
        if progress:
            progress((i + 1) / n, f"渲染图表 {key}")
    return out
