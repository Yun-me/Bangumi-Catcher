"""One atomic export path for the GUI, the CLI and tests."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from ..core.config import AppConfig
from ..core.models import AnalysisReport, UserCollection
from ..reporting import (
    atomic_output,
    build_html_report,
    collection_to_csv,
    collection_to_json,
    report_to_json,
)

logger = logging.getLogger(__name__)

EXPORT_FORMATS: tuple[str, ...] = ("csv", "json", "report-json", "html")
"""Formats accepted by :func:`export_dataset` and the CLI ``--format`` flag."""

ProgressCb = Callable[[float, str], None]


def export_extension(format_name: str) -> str:
    """File extension for an export format."""
    return "json" if format_name == "report-json" else format_name


def export_stem(format_name: str, filtered: bool = False) -> str:
    """Default file stem: ``filtered`` for filtered exports, else per format."""
    if filtered:
        return "filtered"
    return "report" if format_name in {"report-json", "html"} else "collection"


def default_output_path(config: AppConfig, username: str, format_name: str) -> Path:
    """Configured output directory plus the conventional filename."""
    return (
        config.resolved_output_dir()
        / f"{username}_{export_stem(format_name)}.{export_extension(format_name)}"
    )


def export_dataset(
    collection: UserCollection,
    report: AnalysisReport,
    output: str | Path,
    format_name: str,
    config: AppConfig,
    progress: ProgressCb | None = None,
) -> Path:
    """Export ``collection`` / ``report`` to ``output`` atomically.

    The target is only replaced after the temporary file has been written
    completely, so a failure or a cancellation leaves the previous export
    untouched. ``progress`` receives ``(fraction, message)`` and may raise to
    cancel the export.

    Raises:
        ValueError: unsupported ``format_name``.
    """
    if format_name not in EXPORT_FORMATS:
        raise ValueError(f"不支持的导出格式：{format_name}")

    target = Path(output).expanduser()
    with atomic_output(target) as temporary:
        if progress is not None:
            progress(0.02, "准备导出 …")

        if format_name == "csv":
            collection_to_csv(collection, temporary, encoding=config.export.csv_encoding)
        elif format_name == "json":
            collection_to_json(collection, temporary, indent=config.export.json_indent)
        elif format_name == "report-json":
            report_to_json(report, temporary, indent=config.export.json_indent)
        else:  # html
            temporary.write_text(build_html_report(report, progress=progress), encoding="utf-8")

        if progress is not None:
            progress(1.0, "保存文件 …")

    logger.info("导出完成: %s (%s)", target, format_name)
    return target


__all__ = [
    "EXPORT_FORMATS",
    "ProgressCb",
    "default_output_path",
    "export_dataset",
    "export_extension",
    "export_stem",
]
