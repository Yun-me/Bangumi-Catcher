"""分页逻辑单元测试 —— 锁住"按 offset 计算页码 + 合并去重"两段核心算法。

这两段逻辑是 v1.2 抓取重构的关键，从根本上消除了旧版 while-True 翻页可能
出现的死循环，并保证 total 抖动时不产生重复条目。
"""
from bangumi_catcher.api import compute_remaining_offsets, merge_pages


# ---------------- compute_remaining_offsets ----------------

def test_offsets_multi_page():
    # 首页 50 条，共 120 条，每页 50 → 还需抓 offset 50、100
    assert compute_remaining_offsets(50, 120, 50) == [50, 100]


def test_offsets_single_page_no_extra():
    # 首页已取完全部（25 条共 25 条）→ 无需额外翻页
    assert compute_remaining_offsets(25, 25, 50) == []


def test_offsets_exact_multiple():
    # 100 条、每页 50，首页 50 → 仅需再抓 offset 50（不越界到 100）
    assert compute_remaining_offsets(50, 100, 50) == [50]


def test_offsets_bogus_small_total():
    # 接口返回的 total 比首页还小（脏数据）→ 不产生任何额外页，绝不死循环
    assert compute_remaining_offsets(50, 3, 50) == []


def test_offsets_zero_limit_safe():
    # limit 异常为 0 时不抛 ZeroDivision/不无限循环
    assert compute_remaining_offsets(50, 120, 0) == []


# ---------------- merge_pages ----------------

def test_merge_orders_by_offset():
    pages = {
        100: [{"subject_id": 5}, {"subject_id": 6}],
        0: [{"subject_id": 1}, {"subject_id": 2}],
        50: [{"subject_id": 3}, {"subject_id": 4}],
    }
    ids = [e["subject_id"] for e in merge_pages(pages)]
    assert ids == [1, 2, 3, 4, 5, 6]


def test_merge_dedupes_overlap():
    # 相邻页因 total 抖动出现重叠 subject_id=3 → 仅保留一次
    pages = {
        0: [{"subject_id": 1}, {"subject_id": 2}, {"subject_id": 3}],
        50: [{"subject_id": 3}, {"subject_id": 4}],
    }
    ids = [e["subject_id"] for e in merge_pages(pages)]
    assert ids == [1, 2, 3, 4]


def test_merge_keeps_entries_without_id():
    # subject_id 缺失的条目不参与去重、全部保留
    pages = {0: [{"subject_id": 0}, {"foo": "bar"}, {"subject_id": 7}]}
    out = merge_pages(pages)
    assert len(out) == 3


def test_merge_empty():
    assert merge_pages({}) == []
