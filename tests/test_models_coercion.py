"""模型宽松字段校验测试 —— 锁住 v1.2 的"脏数据不崩"修复。

旧版 ``rate`` 带 ``ge=0, le=10`` 硬约束，当接口对某条收藏返回 ``"rate": null``
或越界评分时，会让整次抓取在数据层直接抛错崩溃。改为 ``mode="before"`` 校验器
后，单条脏数据被就地收敛，不再影响整体。
"""
import pytest
from bangumi_catcher.models import CollectionItem, Subject


# ---------------- CollectionItem ----------------

def test_null_rate_becomes_zero():
    # 核心回归：曾导致整次抓取崩溃的 rate=null
    it = CollectionItem(subject_id=1, rate=None)
    assert it.rate == 0


def test_rate_string_coerced():
    it = CollectionItem(subject_id=1, rate="8")
    assert it.rate == 8


def test_rate_clamped_high_and_low():
    assert CollectionItem(subject_id=1, rate=15).rate == 10
    assert CollectionItem(subject_id=1, rate=-3).rate == 0


def test_rate_garbage_becomes_zero():
    it = CollectionItem(subject_id=1, rate="N/A")
    assert it.rate == 0


def test_type_and_status_null_safe():
    it = CollectionItem(subject_id=1, type=None, ep_status=None, vol_status=None)
    assert (it.type, it.ep_status, it.vol_status) == (0, 0, 0)


def test_tags_null_becomes_empty_list():
    it = CollectionItem(subject_id=1, tags=None)
    assert it.tags == []


def test_tags_object_form_supported():
    # 兼容 {"name": ...} 对象形态与纯字符串混排，非法元素被跳过
    it = CollectionItem(subject_id=1, tags=[{"name": "原创"}, "TV", 123])
    assert it.tags == ["原创", "TV"]


# ---------------- Subject ----------------

def test_subject_null_ints_safe():
    s = Subject(id=1, name="x", eps=None, total_episodes=None, rank=None)
    assert (s.eps, s.total_episodes, s.rank) == (0, 0, 0)


def test_subject_numeric_string_coerced():
    s = Subject(id=1, name="x", total_episodes="24")
    assert s.total_episodes == 24


def test_subject_null_str_fields_safe():
    # date=null 不应让 year 计算路径报错
    s = Subject(id=1, name="x", date=None)
    assert s.date == ""
    assert s.year is None


@pytest.mark.parametrize("bad", ["", None, "oops"])
def test_subject_rank_robust(bad):
    assert Subject(id=1, name="x", rank=bad).rank == 0
