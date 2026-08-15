"""v1.2.2 完成率 / 总集数语义测试。

锁住两处真实修复：
  * SlimSubject 只有 eps 没有 total_episodes 时，总集数走 eps 回退（旧版分母为 0）；
  * 「看过」一律 100%，「在看」按 已看/总集 计（旧版看过条目 ep_status=0 会误算成 0%）。
"""
from bangumi_catcher.core.models import CollectionItem, Subject


def _subj(eps=0, total_episodes=0):
    return Subject(id=1, name="x", eps=eps, total_episodes=total_episodes)


# ---------------- episodes_total 回退 ----------------

def test_episodes_total_prefers_total_episodes():
    assert _subj(eps=12, total_episodes=24).episodes_total == 24


def test_episodes_total_falls_back_to_eps():
    # SlimSubject 形态：只有 eps
    assert _subj(eps=24, total_episodes=0).episodes_total == 24


def test_episodes_total_zero_when_both_missing():
    assert _subj().episodes_total == 0


# ---------------- completion_rate 语义 ----------------

def test_finished_is_complete_even_without_ep_status():
    # 核心回归：看过条目即便 ep_status=0 也应是 100%
    it = CollectionItem(subject_id=1, type=2, ep_status=0, subject=_subj(eps=24))
    assert it.completion_rate == 1.0


def test_watching_uses_eps_fallback():
    # 在看 12/24，total_episodes 缺失 → 用 eps 作分母 = 0.5（旧版会得 0）
    it = CollectionItem(subject_id=1, type=3, ep_status=12, subject=_subj(eps=24))
    assert it.completion_rate == 0.5


def test_watching_caps_at_one():
    it = CollectionItem(subject_id=1, type=3, ep_status=30, subject=_subj(eps=24))
    assert it.completion_rate == 1.0


def test_wish_is_zero():
    it = CollectionItem(subject_id=1, type=1, ep_status=0, subject=_subj(eps=24))
    assert it.completion_rate == 0.0


def test_watching_zero_progress_is_zero():
    it = CollectionItem(subject_id=1, type=3, ep_status=0, subject=_subj(eps=24))
    assert it.completion_rate == 0.0


def test_completion_without_subject_safe():
    it = CollectionItem(subject_id=1, type=3, ep_status=5, subject=None)
    assert it.completion_rate == 0.0
