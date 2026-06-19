"""v1.2.2 全站评分映射测试 —— 锁住「列表内联条目评分抓不到」的根因修复。

收藏列表内联的 SlimSubject 评分是扁平 ``score`` 字段；条目详情接口是嵌套
``rating.score``。``_build_subject`` 需同时兼容两者。
"""
from bangumi_catcher.api import _build_subject


def test_slim_subject_flat_score_maps():
    # 收藏列表内联形态：扁平 score / rank，集数为 eps，无 total_episodes
    slim = {"id": 1, "name": "x", "date": "2021-04-01", "score": 8.4, "rank": 120, "eps": 24}
    s = _build_subject(slim)
    assert s.score == 8.4          # 此前恒为 0
    assert s.rank == 120
    assert s.episodes_total == 24  # eps 回退


def test_full_subject_nested_rating_maps():
    full = {"id": 1, "name": "x", "rating": {"score": 8.4, "rank": 120, "total": 5000},
            "total_episodes": 24, "eps": 24}
    s = _build_subject(full)
    assert s.score == 8.4
    assert s.episodes_total == 24


def test_unrated_slim_stays_zero():
    # score 为 0 是「暂无评分」的合法值，不应被当成缺失
    s = _build_subject({"id": 2, "name": "y", "score": 0, "eps": 12})
    assert s.score == 0.0


def test_short_summary_fallback():
    s = _build_subject({"id": 3, "name": "z", "short_summary": "简介", "eps": 1})
    assert s.summary == "简介"
