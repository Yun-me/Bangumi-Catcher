"""Render report charts to PNG bytes or base64 data URIs.

Matplotlib's Agg canvas is not thread safe, so every render is serialised by a
process-wide lock. The desktop renders charts on a worker thread; the HTML
exporter renders them synchronously during an export task. Both paths go
through :func:`render_chart`.
"""

from __future__ import annotations

import base64
import io
import threading
from collections.abc import Callable

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from ..core.models import AnalysisReport
from .builders import FIGURE_BUILDERS
from .catalog import CHART_TITLES
from .theme import DARK, LIGHT

_RENDER_LOCK = threading.RLock()


def build_figures(report: AnalysisReport, dark: bool = False) -> dict[str, Figure]:
    """Build every figure for ``report`` using the requested theme."""
    theme = DARK if dark else LIGHT
    return {key: builder(report, theme) for key, builder in FIGURE_BUILDERS.items()}


def render_chart(report: AnalysisReport, key: str, dark: bool = False) -> bytes:
    """Render one chart as PNG bytes.

    Raises:
        KeyError: ``key`` is not a registered chart.
    """
    builder = FIGURE_BUILDERS.get(key)
    if builder is None:
        raise KeyError(f"未知图表维度: {key}")

    theme = DARK if dark else LIGHT
    with _RENDER_LOCK:
        figure = builder(report, theme)
        try:
            FigureCanvasAgg(figure)
            output = io.BytesIO()
            figure.savefig(output, format="png", bbox_inches="tight", facecolor=theme["surface"], dpi=160)
            return output.getvalue()
        finally:
            figure.clear()


def render_all(
    report: AnalysisReport, progress: Callable[[float, str], None] | None = None
) -> dict[str, str]:
    """Render every chart as a ``data:image/png;base64,...`` URI (light theme)."""
    charts: dict[str, str] = {}
    keys = list(FIGURE_BUILDERS)
    for index, key in enumerate(keys):
        encoded = base64.b64encode(render_chart(report, key)).decode("ascii")
        charts[key] = f"data:image/png;base64,{encoded}"
        if progress is not None:
            progress((index + 1) / len(keys), f"渲染图表 {CHART_TITLES.get(key, key)}")
    return charts


__all__ = ["build_figures", "render_all", "render_chart"]
