"""One atomic export path for the GUI and CLI."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable

from ..core.config import AppConfig
from ..core.export import collection_to_csv, collection_to_json, report_to_json
from ..core.models import AnalysisReport, UserCollection


def export_dataset(
    collection: UserCollection,
    report: AnalysisReport,
    output: str | Path,
    format_name: str,
    config: AppConfig,
    progress: Callable[[float, str], None] | None = None,
) -> Path:
    target = Path(output).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(descriptor)
    try:
        if progress:
            progress(0.02, "准备导出 …")
        if format_name == "csv":
            collection_to_csv(collection, temporary, encoding=config.export.csv_encoding)
        elif format_name == "json":
            collection_to_json(collection, temporary, indent=config.export.json_indent)
        elif format_name == "report-json":
            report_to_json(report, temporary, indent=config.export.json_indent)
        elif format_name == "html":
            from jinja2 import Environment, FileSystemLoader

            from ..ui.visualizer import render_all

            charts = render_all(report, progress=progress)
            environment = Environment(
                loader=FileSystemLoader(str(Path(__file__).resolve().parent.parent / "templates")),
                autoescape=True,
            )
            html = environment.get_template("report.html.j2").render(report=report, charts=charts)
            Path(temporary).write_text(html, encoding="utf-8")
        else:
            raise ValueError(f"不支持的导出格式：{format_name}")
        if progress:
            progress(1.0, "保存文件 …")
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target
