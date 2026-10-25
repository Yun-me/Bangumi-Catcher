"""Chart rendering built on Matplotlib.

Importing this package is cheap: :mod:`bangumi_catcher.charts.catalog` has no
third-party imports, and the Matplotlib-backed names below are loaded lazily on
first access::

    from bangumi_catcher.charts import render_chart
"""

from __future__ import annotations

from typing import Any

__all__ = ["FIGURE_BUILDERS", "build_figures", "render_all", "render_chart"]

_LAZY_ATTRS = {
    "FIGURE_BUILDERS": (".builders", "FIGURE_BUILDERS"),
    "build_figures": (".render", "build_figures"),
    "render_chart": (".render", "render_chart"),
    "render_all": (".render", "render_all"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    module_name, attribute = target
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value
