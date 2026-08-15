"""分析引擎回归测试 —— 锁住"年度均分只统计已评分条目"这一历史 Bug。"""
from bangumi_catcher.core.analyzer import analyze


def test_overall_avg_excludes_unrated(sample_collection):
    rep = analyze(sample_collection)
    # 看过条目评分为 8、0(未评)、6 → 只对 8 和 6 求均值 = 7.0
    assert rep.overall_avg_rating == 7.0


def test_year_avg_only_rated(sample_collection):
    rep = analyze(sample_collection)
    y2020 = rep.by_year[2020]
    # 2020 看过两条(8 和未评分) → 均分应为 8.0，而非 (8+0)/2=4.0
    assert y2020.avg_rating == 8.0
    assert y2020.finished == 2


def test_type_counts(sample_collection):
    rep = analyze(sample_collection)
    assert rep.type_counts["看过"] == 3
    assert rep.type_counts["想看"] == 1
    assert rep.type_counts["在看"] == 1


def test_completion_rate(sample_collection):
    rep = analyze(sample_collection)
    # 4 部看过(100%) + 1 部在看(4/12) 取 type in (2,3)
    assert 0 < rep.avg_completion <= 100


def test_tag_stats(sample_collection):
    rep = analyze(sample_collection)
    assert rep.tag_counts.get("原创") == 5
    assert rep.top_tags and rep.top_tags[0].name == "原创"
    assert rep.top_tags[0].count == 5
