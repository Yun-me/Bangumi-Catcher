"""CSV / JSON 导出模块 (Pydantic 模型适配)."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from .models import AnalysisReport, UserCollection

logger = logging.getLogger(__name__)


def _ensure_dir(path: str) -> Path:
    p = Path(path).parent
    p.mkdir(parents=True, exist_ok=True)
    return p


# ================================================================
# Collection → CSV
# ================================================================

def collection_to_csv(
    collection: UserCollection,
    output_path: str,
    encoding: str = "utf-8-sig",
) -> str:
    """用户收藏 → CSV 文件."""
    _ensure_dir(output_path)

    fieldnames = [
        "subject_id", "name", "name_cn", "year", "collection_type",
        "rate", "ep_status", "comment", "bangumi_score", "rank", "updated_at",
    ]

    with open(output_path, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for item in collection.items:
            writer.writerow({
                "subject_id": item.subject_id,
                "name": item.subject.name if item.subject else item.name,
                "name_cn": item.subject.name_cn if item.subject else "",
                "year": item.subject_year or "",
                "collection_type": item.collection_type_name,
                "rate": item.rate,
                "ep_status": item.ep_status,
                "comment": item.comment,
                "bangumi_score": item.subject_score,
                "rank": item.subject.rank if item.subject else "",
                "updated_at": item.updated_at,
            })

    logger.info("CSV 已导出: %s (%d 条)", output_path, len(collection.items))
    return output_path


# ================================================================
# Collection → JSON
# ================================================================

def collection_to_json(
    collection: UserCollection,
    output_path: str,
    indent: int = 2,
) -> str:
    """用户收藏 → JSON 文件."""
    _ensure_dir(output_path)
    # 直接用 model_dump 然后微调 key 名
    data = collection.model_dump(mode="json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
    logger.info("JSON 已导出: %s", output_path)
    return output_path


# ================================================================
# Report → JSON
# ================================================================

def report_to_json(report: AnalysisReport, output_path: str, indent: int = 2) -> str:
    """分析报告 → JSON 文件."""
    _ensure_dir(output_path)
    data = report.model_dump(mode="json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
    logger.info("报告 JSON 已导出: %s", output_path)
    return output_path
