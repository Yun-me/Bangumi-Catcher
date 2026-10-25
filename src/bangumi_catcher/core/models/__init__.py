"""Typed domain models.

Import from this package rather than from the individual modules so internal
splits stay invisible to callers::

    from bangumi_catcher.core.models import AnalysisReport, Subject, UserCollection
"""

from __future__ import annotations

from .collection import (
    COLLECTION_TYPE_MAP,
    COLLECTION_TYPE_NAMES,
    CollectionItem,
    UserCollection,
    collection_type_name,
)
from .report import (
    AnalysisReport,
    RatingCompareItem,
    SeasonStats,
    TagItem,
    TopRatedItem,
    TypeTrendItem,
    YearStats,
    YearTrendItem,
)
from .subject import (
    SUBJECT_TYPE_MAP,
    SUBJECT_TYPE_NAMES,
    ImageInfo,
    RatingInfo,
    Subject,
    parse_season,
    parse_year,
    subject_type_name,
)

__all__ = [
    "COLLECTION_TYPE_MAP",
    "COLLECTION_TYPE_NAMES",
    "SUBJECT_TYPE_MAP",
    "SUBJECT_TYPE_NAMES",
    "AnalysisReport",
    "CollectionItem",
    "ImageInfo",
    "RatingCompareItem",
    "RatingInfo",
    "SeasonStats",
    "Subject",
    "TagItem",
    "TopRatedItem",
    "TypeTrendItem",
    "UserCollection",
    "YearStats",
    "YearTrendItem",
    "collection_type_name",
    "parse_season",
    "parse_year",
    "subject_type_name",
]
