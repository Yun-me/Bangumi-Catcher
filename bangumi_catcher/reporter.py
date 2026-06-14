"""Jinja2 静态 HTML 报告生成."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .models import AnalysisReport

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def generate_html(
    report: AnalysisReport,
    charts: dict[str, str],
    output_path: str,
    template_name: str = "report.html.j2",
) -> str:
    """用 Jinja2 渲染完整 HTML 报告.

    Args:
        report: 分析报告.
        charts: {name: file_path} 图表路径映射.
        output_path: 输出 HTML 文件路径.
        template_name: 模板文件名.

    Returns:
        输出文件路径.
    """
    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)
    template = env.get_template(template_name)

    # 图片相对路径
    html_dir = Path(output_path).resolve().parent
    rel_charts: dict[str, str] = {}
    for name, chart_path in charts.items():
        try:
            rel_charts[name] = os.path.relpath(chart_path, html_dir)
        except ValueError:
            rel_charts[name] = chart_path

    html = template.render(report=report, charts=rel_charts)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    logger.info("HTML 报告已生成: %s", output_path)
    return output_path
