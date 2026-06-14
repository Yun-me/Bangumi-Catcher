"""分析引擎 —— 年份过滤、评分分布、趋势统计 (Pydantic 模型)."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict

from .models import (
    AnalysisReport,
    CollectionItem,
    TopRatedItem,
    UserCollection,
    YearStats,
    YearTrendItem,
)

logger = logging.getLogger(__name__)


def analyze(
    collection: UserCollection,
    year_start: int = 2000,
    year_end: int = 2025,
    top_n: int = 20,
) -> AnalysisReport:
    """对用户收藏执行全量分析.

    Args:
        collection: 用户收藏数据.
        year_start: 年份过滤起点 (含).
        year_end: 年份过滤终点 (含).
        top_n: 高分排名数量.

    Returns:
        AnalysisReport.
    """
    report = AnalysisReport(
        username=collection.username,
        total_items=len(collection.items),
    )

    type_counter: Counter[str] = Counter()
    rating_counter: Counter[int] = Counter()
    by_year: dict[int, YearStats] = defaultdict(lambda: YearStats(year=0))

    for item in collection.items:
        type_counter[item.collection_type_name] += 1

        if item.rate > 0:
            rating_counter[item.rate] += 1

        year = item.subject_year
        if year is None:
            continue

        if year_start <= year <= year_end:
            ys = by_year[year]
            ys.year = year
            ys.total += 1

            if item.type == 1:
                ys.wish += 1
            elif item.type == 2:
                ys.finished += 1
                if item.rate > 0:
                    ys.avg_rating = (
                        (ys.avg_rating * (ys.finished - 1) + item.rate) / ys.finished
                        if ys.finished > 1
                        else item.rate
                    )
            elif item.type == 3:
                ys.watching += 1
            elif item.type == 4:
                ys.on_hold += 1
            elif item.type == 5:
                ys.dropped += 1

    report.type_counts = dict(type_counter)
    report.rating_distribution = dict(sorted(rating_counter.items()))
    report.by_year = dict(sorted(by_year.items()))

    # 年度趋势
    report.year_trend = [
        YearTrendItem(
            year=y,
            total=s.total,
            finished=s.finished,
            watching=s.watching,
            wish=s.wish,
            on_hold=s.on_hold,
            dropped=s.dropped,
            avg_rating=round(s.avg_rating, 2),
        )
        for y, s in sorted(by_year.items())
    ]

    # 高分排名
    rated_items = [
        item for item in collection.items
        if item.type == 2 and item.rate >= 5 and item.subject is not None
    ]
    rated_items.sort(key=lambda x: x.rate, reverse=True)
    report.top_rated = [
        TopRatedItem(
            subject_id=it.subject_id,
            name=it.subject.name if it.subject else it.name,
            name_cn=it.subject.name_cn if it.subject else "",
            rate=it.rate,
            year=it.subject_year,
            cover_url=it.subject_cover,
            bangumi_score=it.subject_score,
        )
        for it in rated_items[:top_n]
    ]

    # 整体平均分
    all_rated = [item.rate for item in collection.items if item.type == 2 and item.rate > 0]
    report.overall_avg_rating = round(sum(all_rated) / len(all_rated), 2) if all_rated else 0.0

    logger.info("分析完成: %d 条 → %d 个年份, 平均分 %.2f",
                 report.total_items, len(report.by_year), report.overall_avg_rating)
    return report
