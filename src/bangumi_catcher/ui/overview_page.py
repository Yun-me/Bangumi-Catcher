"""Native overview dashboard; never imports the plotting runtime."""

from __future__ import annotations

import heapq

from PySide6 import QtCore, QtWidgets

from ..core.models import COLLECTION_TYPE_MAP, AnalysisReport, UserCollection
from .flow_layout import FlowLayout
from .widgets import Card, StatCard, clear_layout, label


class OverviewPage(QtWidgets.QScrollArea):
    """Metrics, status distribution, favourites, recent activity and tags."""

    library_requested = QtCore.Signal(object, str)
    import_requested = QtCore.Signal()
    fetch_requested = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        self.setWidget(content)
        layout = QtWidgets.QVBoxLayout(content)
        layout.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        layout.setContentsMargins(0, 0, 2, 0)
        layout.setSpacing(18)

        hero = Card()
        hero.setObjectName("Hero")
        hero.body.setContentsMargins(26, 24, 26, 24)
        hero.body.addWidget(label("YOUR PERSONAL BANGUMI WORKSPACE", "Eyebrow"))
        self.hero_title = label("让收藏，不止于列表。", "HeroTitle", True)
        hero.body.addWidget(self.hero_title)
        self.hero_hint = label("把喜欢的作品好好整理，在自己的节奏里，发现下一份热爱。", "Muted", True)
        hero.body.addWidget(self.hero_hint)

        actions = QtWidgets.QHBoxLayout()
        self.explore_button = QtWidgets.QPushButton("开始探索收藏  →")
        self.explore_button.setObjectName("Primary")
        self.explore_button.clicked.connect(self._explore)
        actions.addWidget(self.explore_button)
        import_button = QtWidgets.QPushButton("导入本地快照")
        import_button.clicked.connect(self.import_requested)
        actions.addWidget(import_button)
        actions.addStretch()
        hero.body.addLayout(actions)
        layout.addWidget(hero)

        self.stats_grid = QtWidgets.QGridLayout()
        self.stats_grid.setSpacing(14)
        self.stat_columns = 4
        self.stat_cards = [
            StatCard("收藏作品", "当前分类全部收藏"),
            StatCard("已完成", "已标记为看过的作品"),
            StatCard("平均评分", "已看过且已评分的作品"),
            StatCard("平均完成率", "看过与在看的平均进度"),
        ]
        for column, card in enumerate(self.stat_cards):
            self.stats_grid.addWidget(card, 0, column)
        layout.addLayout(self.stats_grid)

        middle = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight)
        self.middle_layout = middle
        middle.setSpacing(18)
        status_card = Card("收藏进度")
        self.status_body = QtWidgets.QVBoxLayout()
        self.status_body.setSpacing(12)
        status_card.body.addLayout(self.status_body)
        status_card.body.addStretch()
        middle.addWidget(status_card, 2)

        favorites = Card("值得回味的作品")
        self.favorites_body = QtWidgets.QVBoxLayout()
        self.favorites_body.setSpacing(8)
        favorites.body.addLayout(self.favorites_body)
        favorites.body.addStretch()
        middle.addWidget(favorites, 3)
        layout.addLayout(middle)

        bottom = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight)
        self.bottom_layout = bottom
        bottom.setSpacing(18)
        recent = Card("最近更新")
        self.recent_body = QtWidgets.QVBoxLayout()
        self.recent_body.setSpacing(6)
        recent.body.addLayout(self.recent_body)
        bottom.addWidget(recent, 3)

        tags = Card("你的兴趣标签")
        self.tag_container = QtWidgets.QWidget()
        self.tag_flow = FlowLayout(self.tag_container, margin=0, h_spacing=8, v_spacing=8)
        tags.body.addWidget(self.tag_container)
        tags.body.addStretch()
        bottom.addWidget(tags, 2)
        layout.addLayout(bottom)
        layout.addStretch()

        self.has_data = False
        self.status_body.addWidget(label("同步后，查看想看、在看与已完成的分布。", "Muted", True))
        self.favorites_body.addWidget(label("你的高分作品，会在这里相遇。", "Muted", True))
        self.recent_body.addWidget(label("无需登录，也可以导入 JSON 离线回顾。", "Muted", True))
        self.tag_flow.addWidget(label("从收藏中发现自己的偏好。", "Muted", True))

    def _explore(self) -> None:
        if self.has_data:
            self.library_requested.emit(None, "")
        else:
            self.fetch_requested.emit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        columns = 4 if self.viewport().width() >= 900 else 2
        if columns != self.stat_columns:
            self.stat_columns = columns
            for position, card in enumerate(self.stat_cards):
                self.stats_grid.addWidget(card, position // columns, position % columns)
        direction = (
            QtWidgets.QBoxLayout.LeftToRight
            if self.viewport().width() >= 760
            else QtWidgets.QBoxLayout.TopToBottom
        )
        self.middle_layout.setDirection(direction)
        self.bottom_layout.setDirection(direction)

    def set_data(self, collection: UserCollection, report: AnalysisReport) -> None:
        self.has_data = True
        self.hero_title.setText(f"{collection.username} 的收藏手记")
        rated = sum(report.rating_distribution.values())
        self.hero_hint.setText(
            f"{len(collection.items):,} 部作品 · {rated:,} 部已评分 · 让每一份喜欢，都有迹可循。"
        )
        self.explore_button.setText("浏览全部收藏  →")

        values = [
            f"{report.total_items:,}",
            str(report.type_counts.get("看过", 0)),
            f"{report.overall_avg_rating:.2f}",
            f"{report.avg_completion:.0f}%",
        ]
        for card, value in zip(self.stat_cards, values):
            card.value.setText(value)

        clear_layout(self.status_body)
        for status, title in COLLECTION_TYPE_MAP.items():
            count = report.type_counts.get(title, 0)
            button = QtWidgets.QPushButton(f"{title}     {count:,}")
            button.setObjectName("Link")
            button.clicked.connect(lambda checked=False, value=status: self.library_requested.emit(value, ""))
            row = QtWidgets.QHBoxLayout()
            button.setFixedWidth(92)
            row.addWidget(button)
            progress = QtWidgets.QProgressBar()
            progress.setFixedHeight(6)
            progress.setTextVisible(False)
            progress.setRange(0, max(1, report.total_items))
            progress.setValue(count)
            row.addWidget(progress, 1)
            self.status_body.addLayout(row)

        clear_layout(self.favorites_body)
        for position, item in enumerate(report.top_rated[:5], start=1):
            title = item.name_cn or item.name
            button = QtWidgets.QPushButton(f"{position:02d}    {title[:36]}     ·     {item.rate} 分")
            button.setToolTip(title)
            button.setObjectName("ListItem")
            button.clicked.connect(lambda checked=False, name=title: self.library_requested.emit(None, name))
            self.favorites_body.addWidget(button)
        if not report.top_rated:
            self.favorites_body.addWidget(label("还没有已看过且评分 ≥ 5 的作品。", "Muted", True))

        clear_layout(self.recent_body)
        recent = heapq.nlargest(
            4, (item for item in collection.items if item.updated_at), key=lambda item: item.updated_at
        )
        for item in recent:
            button = QtWidgets.QPushButton(f"{item.updated_at[:10]}    {item.subject_name[:28]}")
            button.setObjectName("ListItem")
            button.setToolTip(item.subject_name)
            button.clicked.connect(
                lambda checked=False, name=item.subject_name: self.library_requested.emit(None, name)
            )
            self.recent_body.addWidget(button)
        if not recent:
            self.recent_body.addWidget(label("这份收藏没有记录更新时间。", "Muted", True))

        clear_layout(self.tag_flow)
        for tag in report.top_tags[:12]:
            button = QtWidgets.QPushButton(f"{tag.name}  {tag.count}")
            button.setObjectName("Tag")
            button.clicked.connect(
                lambda checked=False, name=tag.name: self.library_requested.emit(None, name)
            )
            self.tag_flow.addWidget(button)
        if not report.top_tags:
            self.tag_flow.addWidget(label("暂无标签", "Muted"))


__all__ = ["OverviewPage"]
