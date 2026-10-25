"""Self-contained HTML report.

All charts are inlined as base64 PNG data URIs, so the file can be opened
offline, emailed or printed without any external asset. The template lives in
``bangumi_catcher/templates/report.html.j2`` and is shipped as package data.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..core.models import AnalysisReport

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
TEMPLATE_NAME = "report.html.j2"


@lru_cache(maxsize=1)
def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(enabled_extensions=("html", "j2")),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def build_html_report(report: AnalysisReport, progress: Callable[[float, str], None] | None = None) -> str:
    """Render the full report HTML, importing the plotting stack lazily."""
    # Imported here so ``import bangumi_catcher.reporting`` stays light and the
    # desktop can show the export menu before Matplotlib is ever loaded.
    from ..charts.render import render_all

    charts = render_all(report, progress=progress)
    template = _environment().get_template(TEMPLATE_NAME)
    return template.render(report=report, charts=charts)


__all__ = ["TEMPLATE_DIR", "TEMPLATE_NAME", "build_html_report"]
