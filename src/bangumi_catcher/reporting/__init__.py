"""Dataset exporters.

Writers are pure functions that take an output path; :func:`atomic_output`
wraps them so a crash or cancellation never damages an existing file. The
orchestration with progress reporting lives in
:mod:`bangumi_catcher.services.export`.
"""

from __future__ import annotations

from .atomic import atomic_output
from .csv_export import collection_to_csv
from .html import build_html_report
from .json_export import collection_to_json, report_to_json

__all__ = [
    "atomic_output",
    "build_html_report",
    "collection_to_csv",
    "collection_to_json",
    "report_to_json",
]
