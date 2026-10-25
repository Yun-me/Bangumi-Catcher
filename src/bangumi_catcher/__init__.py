"""Bangumi Catcher — a local-first Bangumi collection workbench.

The package is organised in layers (see ``docs/architecture.md``):

``core``        pure domain models, configuration, analysis and querying
``api``         Bangumi HTTP client, pagination and cache
``charts``      Matplotlib figure builders and PNG rendering
``reporting``   CSV / JSON / HTML exporters
``services``    orchestration shared by the desktop app and the CLI
``ui``          PySide6 desktop application
``cli``         command line interface

The desktop shell needs only the standard library and PySide6; the plotting
stack is imported lazily when a chart or an HTML report is requested.
"""

from __future__ import annotations

__version__ = "4.0.0"
__author__ = "Bangumi Catcher Contributors"
__license__ = "MIT"

__all__ = ["__author__", "__license__", "__version__"]
