"""Completion-rate semantics.

Two real fixes are pinned here:

* slim subjects only carry ``eps``; the denominator must fall back to it;
* ``看过`` is always 100% even when ``ep_status`` is 0.
"""

from __future__ import annotations

from bangumi_catcher.core.models import CollectionItem, Subject


def _subject(eps: int = 0, total_episodes: int = 0) -> Subject:
    return Subject(id=1, name="x", eps=eps, total_episodes=total_episodes)


def test_episodes_total_prefers_total_episodes():
    assert _subject(eps=12, total_episodes=24).episodes_total == 24


def test_episodes_total_falls_back_to_eps():
    assert _subject(eps=24).episodes_total == 24


def test_episodes_total_zero_when_both_missing():
    assert _subject().episodes_total == 0


def test_finished_is_complete_even_without_ep_status():
    item = CollectionItem(subject_id=1, type=2, ep_status=0, subject=_subject(eps=24))
    assert item.completion_rate == 1.0


def test_watching_uses_eps_fallback():
    item = CollectionItem(subject_id=1, type=3, ep_status=12, subject=_subject(eps=24))
    assert item.completion_rate == 0.5


def test_watching_caps_at_one():
    item = CollectionItem(subject_id=1, type=3, ep_status=30, subject=_subject(eps=24))
    assert item.completion_rate == 1.0


def test_wish_is_zero():
    item = CollectionItem(subject_id=1, type=1, ep_status=0, subject=_subject(eps=24))
    assert item.completion_rate == 0.0


def test_watching_zero_progress_is_zero():
    item = CollectionItem(subject_id=1, type=3, ep_status=0, subject=_subject(eps=24))
    assert item.completion_rate == 0.0


def test_completion_without_subject_safe():
    item = CollectionItem(subject_id=1, type=3, ep_status=5, subject=None)
    assert item.completion_rate == 0.0


def test_wish_with_old_episode_progress_is_still_unstarted():
    item = CollectionItem(subject_id=1, subject=Subject(id=1, eps=12), type=1, ep_status=6)
    assert item.completion_rate == 0.0
