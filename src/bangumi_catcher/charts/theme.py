"""Shared chart tokens: colours, fonts and the figure factory.

Data colours are identical in light and dark mode so charts can be compared
across themes; only text, grids and edges switch.
"""

from __future__ import annotations

import matplotlib.font_manager as font_manager
from matplotlib.figure import Figure

PALETTE = ["#219D83", "#6291D5", "#E7B35C", "#D87988", "#9482C3", "#52ABB9", "#CE8654"]
ACCENT = "#219D83"
ACCENT2 = "#6291D5"

LIGHT: dict[str, str] = {
    "text": "#2C2E33",
    "muted": "#8A929E",
    "grid": "#E6E8EB",
    "edge": "#FFFFFF",
    "empty": "#B7BDC6",
    "surface": "#FFFFFF",
}
DARK: dict[str, str] = {
    "text": "#E7EAF0",
    "muted": "#9AA3B2",
    "grid": "#3A414D",
    "edge": "#252A34",
    "empty": "#5B6472",
    "surface": "#1C2425",
}

_CJK_CANDIDATES = (
    "Microsoft YaHei",
    "PingFang SC",
    "SimHei",
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "WenQuanYi Zen Hei",
)
_available_fonts = {font.name for font in font_manager.fontManager.ttflist}
CJK_FONT: str | None = next((name for name in _CJK_CANDIDATES if name in _available_fonts), None)
FONT = CJK_FONT or "DejaVu Sans"


def font_properties() -> font_manager.FontProperties:
    """Font properties for legend/table text."""
    return font_manager.FontProperties(family=FONT)


def create_figure(theme: dict[str, str], width: float = 6.4, height: float = 4.0, constrained: bool = True):
    """Create a transparent figure with the shared axis styling."""
    figure = Figure(figsize=(width, height), dpi=100, layout="constrained" if constrained else None)
    figure.patch.set_facecolor("none")
    axes = figure.add_subplot(111)
    axes.set_facecolor("none")
    for text in (axes.title, axes.xaxis.label, axes.yaxis.label):
        text.set_fontfamily(FONT)
    axes.spines["top"].set_visible(False)
    axes.spines["right"].set_visible(False)
    axes.spines["left"].set_color(theme["grid"])
    axes.spines["bottom"].set_color(theme["grid"])
    axes.tick_params(colors=theme["muted"], labelsize=9)
    axes.grid(axis="y", color=theme["grid"], linewidth=0.8, alpha=0.7)
    axes.set_axisbelow(True)
    return figure, axes


def apply_cjk_font(axes) -> None:
    """Apply the CJK font to the tick labels of ``axes``."""
    for label in axes.get_xticklabels() + axes.get_yticklabels():
        label.set_fontfamily(FONT)


def set_title(axes, title: str, theme: dict[str, str]) -> None:
    axes.set_title(title, color=theme["text"], fontsize=13, pad=12, fontfamily=FONT, fontweight="bold")


def empty_figure(title: str, theme: dict[str, str]) -> Figure:
    """Placeholder figure used when a report has no data for a chart."""
    figure, axes = create_figure(theme)
    axes.axis("off")
    axes.text(
        0.5,
        0.5,
        "暂无数据",
        ha="center",
        va="center",
        fontsize=14,
        color=theme["empty"],
        fontfamily=FONT,
        transform=axes.transAxes,
    )
    set_title(axes, title, theme)
    return figure


__all__ = [
    "ACCENT",
    "ACCENT2",
    "CJK_FONT",
    "DARK",
    "FONT",
    "LIGHT",
    "PALETTE",
    "apply_cjk_font",
    "create_figure",
    "empty_figure",
    "font_properties",
    "set_title",
]
