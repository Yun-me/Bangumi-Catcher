"""CSV export for collection snapshots."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from ..core.models import UserCollection

logger = logging.getLogger(__name__)

FIELDNAMES = [
    "subject_id",
    "name",
    "name_cn",
    "year",
    "collection_type",
    "rate",
    "ep_status",
    "comment",
    "bangumi_score",
    "rank",
    "updated_at",
    "tags",
    "vol_status",
]


def spreadsheet_safe_text(value: str) -> str:
    """Neutralise text that a spreadsheet could interpret as a formula."""
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def collection_to_csv(
    collection: UserCollection, output_path: str | Path, encoding: str = "utf-8-sig"
) -> str:
    """Write ``collection`` to CSV and return the path as a string."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding=encoding) as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for item in collection.items:
            subject = item.subject
            writer.writerow(
                {
                    "subject_id": item.subject_id,
                    "name": spreadsheet_safe_text(subject.name if subject else item.name),
                    "name_cn": spreadsheet_safe_text(subject.name_cn if subject else ""),
                    "year": item.subject_year or "",
                    "collection_type": item.collection_type_name,
                    "rate": item.rate,
                    "ep_status": item.ep_status,
                    "comment": spreadsheet_safe_text(item.comment),
                    "bangumi_score": item.subject_score,
                    "rank": ((subject.rating.rank if subject.rating else subject.rank) if subject else ""),
                    "updated_at": spreadsheet_safe_text(item.updated_at),
                    "tags": spreadsheet_safe_text(" / ".join(item.tags)),
                    "vol_status": item.vol_status,
                }
            )

    logger.info("CSV 已导出: %s (%d 条)", path, len(collection.items))
    return str(path)


__all__ = ["FIELDNAMES", "collection_to_csv", "spreadsheet_safe_text"]
