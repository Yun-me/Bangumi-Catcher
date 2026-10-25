"""Pure, deterministic collection analytics.

The analysis is a single pass over the collection: counters for types,
ratings, seasons and tags, per-air-year accumulators, and two bounded heaps for
the "top rated" and "rating compare" lists (``heapq.nlargest`` avoids a full
sort when a user has tens of thousands of entries).

No I/O, no Qt and no plotting happens here — see ``docs/data-model.md`` for the
statistical conventions this module implements.
"""

from __future__ import annotations

import heapq
import logging
from collections import Counter, defaultdict
from datetime import datetime

from .models import (
    AnalysisReport,
    RatingCompareItem,
    SeasonStats,
    TagItem,
    TopRatedItem,
    TypeTrendItem,
    UserCollection,
    YearStats,
    YearTrendItem,
)

logger = logging.getLogger(__name__)

RATING_COMPARE_LIMIT = 50
"""Number of rating-comparison points kept for the scatter chart."""


def analyze(
    collection: UserCollection,
    year_start: int = 2000,
    year_end: int | None = None,
    top_n: int = 20,
) -> AnalysisReport:
    """Build the complete :class:`AnalysisReport` for ``collection``.

    Args:
        collection: Snapshotted user collection.
        year_start: First air year included in the yearly statistics.
        year_end: Last air year; defaults to the current year.
        top_n: Maximum number of favourite and tag entries to keep.
    """
    if year_end is None:
        year_end = datetime.now().year

    report = AnalysisReport(username=collection.username, total_items=len(collection.items))
    type_counter: Counter[str] = Counter()
    rating_counter: Counter[int] = Counter()
    season_counter: Counter[str] = Counter()
    tag_counter: Counter[str] = Counter()
    years: dict[int, YearStats] = {}
    type_by_year: dict[int, Counter[str]] = defaultdict(Counter)
    rating_pairs: list[tuple[str, int, float]] = []
    year_rates: dict[int, list[int]] = defaultdict(list)

    for item in collection.items:
        type_counter[item.collection_type_name] += 1
        if item.rate > 0:
            rating_counter[item.rate] += 1
        for tag in item.tags:
            tag_counter[tag] += 1

        subject = item.subject
        if subject is not None:
            if subject.season:
                season_counter[subject.season] += 1
            if item.rate > 0 and item.subject_score > 0:
                rating_pairs.append((item.subject_name, item.rate, item.subject_score))

        year = item.subject_year
        if year is None or not year_start <= year <= year_end:
            continue

        stats = years.get(year)
        if stats is None:
            stats = years[year] = YearStats(year=year)
        stats.total += 1
        type_by_year[year][item.collection_type_name] += 1

        if item.type == 1:
            stats.wish += 1
        elif item.type == 2:
            stats.finished += 1
            if item.rate > 0:
                year_rates[year].append(item.rate)
        elif item.type == 3:
            stats.watching += 1
        elif item.type == 4:
            stats.on_hold += 1
        elif item.type == 5:
            stats.dropped += 1

    for year, rates in year_rates.items():
        years[year].avg_rating = round(sum(rates) / len(rates), 2)

    report.type_counts = dict(type_counter)
    report.rating_distribution = dict(sorted(rating_counter.items()))
    report.by_year = dict(sorted(years.items()))
    report.season_stats = [
        SeasonStats(season=season, count=count) for season, count in sorted(season_counter.items())
    ]
    report.tag_counts = dict(tag_counter.most_common())
    report.top_tags = [TagItem(name=name, count=count) for name, count in tag_counter.most_common(top_n)]

    report.year_trend = [
        YearTrendItem(
            year=year,
            total=stats.total,
            finished=stats.finished,
            watching=stats.watching,
            wish=stats.wish,
            on_hold=stats.on_hold,
            dropped=stats.dropped,
            avg_rating=round(stats.avg_rating, 2),
        )
        for year, stats in sorted(years.items())
    ]

    report.type_trend = [
        TypeTrendItem(
            year=year,
            wish=counts.get("想看", 0),
            watching=counts.get("在看", 0),
            finished=counts.get("看过", 0),
            on_hold=counts.get("搁置", 0),
            dropped=counts.get("抛弃", 0),
        )
        for year, counts in sorted(type_by_year.items())
    ]

    rated = [
        item for item in collection.items if item.type == 2 and item.rate >= 5 and item.subject is not None
    ]
    report.top_rated = [
        TopRatedItem(
            subject_id=item.subject_id,
            name=item.subject.name if item.subject else item.name,
            name_cn=item.subject.name_cn if item.subject else "",
            rate=item.rate,
            year=item.subject_year,
            cover_url=item.subject_cover,
            bangumi_score=item.subject_score,
        )
        for item in heapq.nlargest(top_n, rated, key=lambda item: (item.rate, item.subject_score))
    ]

    report.rating_compare = [
        RatingCompareItem(name=name, my_rate=my_rate, bgm_score=bgm_score)
        for name, my_rate, bgm_score in heapq.nlargest(
            RATING_COMPARE_LIMIT, rating_pairs, key=lambda pair: (pair[1], pair[2])
        )
    ]

    completions = [item.completion_rate for item in collection.items if item.type in (2, 3)]
    report.avg_completion = round(sum(completions) / len(completions) * 100, 1) if completions else 0.0

    rated_scores = [item.rate for item in collection.items if item.type == 2 and item.rate > 0]
    report.overall_avg_rating = round(sum(rated_scores) / len(rated_scores), 2) if rated_scores else 0.0

    logger.info(
        "分析完成: %d 条, %d 年, 均分 %.2f",
        report.total_items,
        len(report.by_year),
        report.overall_avg_rating,
    )
    return report


__all__ = ["RATING_COMPARE_LIMIT", "analyze"]
