"""JSON export for collection snapshots and analysis reports."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..core.models import AnalysisReport, UserCollection

logger = logging.getLogger(__name__)


def _write_json(data: dict[str, Any], output_path: str | Path, indent: int) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=indent)
    return str(path)


def collection_to_json(collection: UserCollection, output_path: str | Path, indent: int = 2) -> str:
    """Write a collection snapshot that :func:`services.library.load_collection` reads."""
    path = _write_json(collection.model_dump(mode="json"), output_path, indent)
    logger.info("JSON 已导出: %s", path)
    return path


def report_to_json(report: AnalysisReport, output_path: str | Path, indent: int = 2) -> str:
    """Write the analysis report (not importable as a collection snapshot)."""
    path = _write_json(report.model_dump(mode="json"), output_path, indent)
    logger.info("报告 JSON 已导出: %s", path)
    return path


__all__ = ["collection_to_json", "report_to_json"]
