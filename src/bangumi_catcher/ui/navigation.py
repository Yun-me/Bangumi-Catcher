"""Sidebar destinations and their labels/icons.

Kept separate from both the sidebar widget and the main window so tests can
assert the navigation contract without constructing the desktop.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    """One sidebar destination."""

    title: str
    section: str
    icon: str


PAGES: tuple[Page, ...] = (
    Page("收藏概览", "OVERVIEW", "home"),
    Page("我的收藏", "LIBRARY", "library"),
    Page("数据洞察", "INSIGHTS", "chart"),
    Page("高分排行", "FAVORITES", "star"),
    Page("年度回顾", "TIMELINE", "calendar"),
)

OVERVIEW_INDEX = 0
LIBRARY_INDEX = 1
CHARTS_INDEX = 2


__all__ = ["CHARTS_INDEX", "LIBRARY_INDEX", "OVERVIEW_INDEX", "PAGES", "Page"]
