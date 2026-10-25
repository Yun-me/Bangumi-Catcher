"""Application services: orchestration that sits between UI/CLI and the API.

Nothing in this package imports Qt; that boundary is enforced by the
architecture tests. Import the public functions from here::

    from bangumi_catcher.services import export_dataset, fetch_and_analyze
"""

from __future__ import annotations

from .cancellation import check_cancelled, run_cancellable
from .export import (
    EXPORT_FORMATS,
    default_output_path,
    export_dataset,
    export_extension,
    export_stem,
)
from .fetch import analyze_user_collection, fetch_and_analyze, fetch_user_collection
from .library import MAX_IMPORT_BYTES, load_collection, normalize_username

__all__ = [
    "EXPORT_FORMATS",
    "MAX_IMPORT_BYTES",
    "analyze_user_collection",
    "check_cancelled",
    "default_output_path",
    "export_dataset",
    "export_extension",
    "export_stem",
    "fetch_and_analyze",
    "fetch_user_collection",
    "load_collection",
    "normalize_username",
    "run_cancellable",
]
