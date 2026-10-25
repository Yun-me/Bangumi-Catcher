"""Chart keys and human readable titles — safe to import without Matplotlib.

The desktop shell imports this module to populate its chart selector; the
plotting runtime is only imported when a chart is actually rendered.
"""

from __future__ import annotations

CHART_TITLES: dict[str, str] = {
    "rating_distribution": "评分分布",
    "type_distribution": "收藏状态",
    "yearly_trend": "年度趋势",
    "yearly_rating": "年度均分",
    "type_trend": "状态构成",
    "season_distribution": "季度分布",
    "top_tags": "热门标签",
    "rating_compare": "评分对比",
    "top_rated": "最爱排行",
}

DEFAULT_CHART_KEY = next(iter(CHART_TITLES))

__all__ = ["CHART_TITLES", "DEFAULT_CHART_KEY"]
