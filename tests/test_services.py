"""服务层测试：分析编排与配置对象配合。"""
from bangumi_catcher.core.config import AppConfig
from bangumi_catcher.services.fetch_service import analyze_user_collection


def test_analyze_user_collection(sample_collection):
    cfg = AppConfig()
    report = analyze_user_collection(sample_collection, cfg)
    assert report.username == sample_collection.username
    assert report.total_items == len(sample_collection.items)
    assert report.tag_counts.get("原创") == 5
