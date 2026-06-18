"""分析引擎 —— 多维度统计."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict

from .models import (
    AnalysisReport,
    RatingCompareItem,
    SeasonStats,
    TopRatedItem,
    TypeTrendItem,
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
    report = AnalysisReport(username=collection.username, total_items=len(collection.items))
    type_counter: Counter[str] = Counter()
    rating_counter: Counter[int] = Counter()
    season_counter: Counter[str] = Counter()
    by_year: dict[int, YearStats] = defaultdict(lambda: YearStats(year=0))
    type_by_year: dict[int, Counter[str]] = defaultdict(Counter)
    rating_pairs: list[tuple[str, int, float]] = []

    year_rates: dict[int, list[int]] = defaultdict(list)

    for item in collection.items:
        type_counter[item.collection_type_name] += 1
        if item.rate > 0:
            rating_counter[item.rate] += 1

        year = item.subject_year
        if item.subject:
            season_counter[item.subject.season] += 1
            if item.rate > 0 and item.subject_score > 0:
                rating_pairs.append((item.subject_name, item.rate, item.subject_score))

        if year is None:
            continue
        if year_start <= year <= year_end:
            ys = by_year[year]
            ys.year = year
            ys.total += 1
            type_by_year[year][item.collection_type_name] += 1

            if item.type == 1:
                ys.wish += 1
            elif item.type == 2:
                ys.finished += 1
                if item.rate > 0:
                    year_rates[year].append(item.rate)
            elif item.type == 3:
                ys.watching += 1
            elif item.type == 4:
                ys.on_hold += 1
            elif item.type == 5:
                ys.dropped += 1

    # 统一计算年度平均分 (避免增量公式因未评分条目导致的误差)
    for y, rates in year_rates.items():
        by_year[y].avg_rating = round(sum(rates) / len(rates), 2) if rates else 0.0

    report.type_counts = dict(type_counter)
    report.rating_distribution = dict(sorted(rating_counter.items()))
    report.by_year = dict(sorted(by_year.items()))
    report.season_stats = [SeasonStats(season=k, count=v) for k, v in sorted(season_counter.items())]

    # 年度趋势
    report.year_trend = [
        YearTrendItem(year=y, total=s.total, finished=s.finished, watching=s.watching,
                       wish=s.wish, on_hold=s.on_hold, dropped=s.dropped,
                       avg_rating=round(s.avg_rating, 2))
        for y, s in sorted(by_year.items())
    ]

    # 类型年度趋势
    report.type_trend = [
        TypeTrendItem(year=y,
                       wish=c.get("想看", 0), watching=c.get("在看", 0),
                       finished=c.get("看过", 0), on_hold=c.get("搁置", 0),
                       dropped=c.get("抛弃", 0))
        for y, c in sorted(type_by_year.items())
    ]

    # 高分排行
    rated = [it for it in collection.items if it.type == 2 and it.rate >= 5 and it.subject]
    rated.sort(key=lambda x: x.rate, reverse=True)
    report.top_rated = [
        TopRatedItem(subject_id=it.subject_id, name=it.subject.name if it.subject else it.name,
                      name_cn=it.subject.name_cn if it.subject else "", rate=it.rate,
                      year=it.subject_year, cover_url=it.subject_cover, bangumi_score=it.subject_score)
        for it in rated[:top_n]
    ]

    # 评分对比
    rating_pairs.sort(key=lambda x: x[1], reverse=True)
    report.rating_compare = [
        RatingCompareItem(name=n, my_rate=mr, bgm_score=bs)
        for n, mr, bs in rating_pairs[:50]
    ]

    # 平均完成率
    completions = [it.completion_rate for it in collection.items if it.type in (2, 3)]
    report.avg_completion = round(sum(completions) / len(completions) * 100, 1) if completions else 0.0

    # 整体平均分
    all_rated = [it.rate for it in collection.items if it.type == 2 and it.rate > 0]
    report.overall_avg_rating = round(sum(all_rated) / len(all_rated), 2) if all_rated else 0.0

    logger.info("分析完成: %d 条, %d 年, 均分 %.2f", report.total_items, len(report.by_year), report.overall_avg_rating)
    return report
