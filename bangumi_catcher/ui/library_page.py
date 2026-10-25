"""Searchable library with a selection-driven detail pane."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.models import COLLECTION_TYPE_MAP, CollectionItem, UserCollection
from .collection_model import CollectionProxy, CollectionTableModel
from .widgets import Card, configure_table, label, progress_label


class DetailPanel(Card):
    def __init__(self):
        super().__init__()
        self.setObjectName("DetailPanel")
        self.setMinimumWidth(230)
        self.item: CollectionItem | None = None
        self.body.addWidget(label("SUBJECT DETAILS", "Eyebrow"))
        self.title = label("选择一部作品", "DetailTitle", True)
        self.body.addWidget(self.title)
        self.subtitle = label("在列表中单击查看详细信息。", "Muted", True)
        self.body.addWidget(self.subtitle)
        self.score = label("", "SectionTitle", True)
        self.body.addWidget(self.score)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.body.addWidget(self.progress)
        self.metadata = label("", "Muted", True)
        self.body.addWidget(self.metadata)
        self.body.addWidget(label("我的短评 / 标签", "Eyebrow"))
        self.comment = QtWidgets.QPlainTextEdit()
        self.comment.setReadOnly(True)
        self.comment.setMinimumHeight(100)
        self.comment.setMaximumHeight(170)
        self.comment.setPlaceholderText("选择作品后显示短评")
        self.body.addWidget(self.comment)
        self.body.addWidget(label("作品简介", "Eyebrow"))
        self.summary = QtWidgets.QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMinimumHeight(120)
        self.summary.setPlaceholderText("暂无简介")
        self.body.addWidget(self.summary, 1)
        self.open_button = QtWidgets.QPushButton("在 Bangumi 中打开  ↗")
        self.open_button.setObjectName("Primary")
        self.open_button.clicked.connect(self.open_subject)
        self.body.insertWidget(5, self.open_button)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.set_item(None)

    def set_item(self, item: CollectionItem | None) -> None:
        self.item = item
        self.open_button.setEnabled(item is not None and item.subject_id > 0)
        self.progress.setVisible(item is not None)
        if item is None:
            self.title.setText("选择一部作品")
            self.subtitle.setText("在列表中单击查看详细信息。")
            self.score.clear()
            self.metadata.clear()
            self.comment.clear()
            self.summary.clear()
            return
        self.title.setText(item.subject_name)
        subject = item.subject
        original = subject.name if subject and subject.name != item.subject_name else ""
        self.subtitle.setText(original or f"Bangumi #{item.subject_id}")
        own_score = str(item.rate) if item.rate else "未评分"
        site_score = f"{item.subject_score:.1f}" if item.subject_score else "暂无"
        self.score.setText(f"我的评分  {own_score}   /   全站  {site_score}")
        self.progress.setValue(round(item.completion_rate * 100))
        rank = (subject.rating.rank if subject.rating else subject.rank) if subject else 0
        self.metadata.setText("\n".join([
            f"{item.collection_type_name} · {progress_label(item)}",
            f"发行：{subject.date if subject and subject.date else '未知'}  ·  排名：{rank or '—'}",
            f"更新：{item.updated_at[:16].replace('T', ' ') or '未记录'}",
        ]))
        self.comment.setPlainText(f"{item.comment or '还没有写短评。'}\n\n{'  /  '.join(item.tags) or '暂无标签'}")
        self.summary.setPlainText(subject.summary if subject else "")

    def open_subject(self) -> None:
        if self.item and self.item.subject_id > 0:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(f"https://bgm.tv/subject/{self.item.subject_id}"))


class LibraryPage(QtWidgets.QWidget):
    export_requested = QtCore.Signal(str)
    message = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        self.collection: UserCollection | None = None
        self.setObjectName("Page")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        tools = QtWidgets.QHBoxLayout()
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("搜索作品、原名、标签、短评或 ID …    Ctrl+F")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(220)
        tools.addWidget(self.search, 1)
        self.details_toggle = QtWidgets.QPushButton("作品详情")
        self.details_toggle.setCheckable(True)
        tools.addWidget(self.details_toggle)
        self.export_button = QtWidgets.QPushButton("导出筛选结果")
        export_menu = QtWidgets.QMenu(self.export_button)
        export_menu.addAction("CSV 表格", lambda: self.export_requested.emit("csv"))
        export_menu.addAction("JSON 快照", lambda: self.export_requested.emit("json"))
        self.export_button.setMenu(export_menu)
        self.export_button.setEnabled(False)
        tools.addWidget(self.export_button)
        layout.addLayout(tools)

        filters = QtWidgets.QHBoxLayout()
        self.status_filter = QtWidgets.QComboBox()
        self.status_filter.addItem("全部状态", None)
        for value, name in COLLECTION_TYPE_MAP.items():
            self.status_filter.addItem(name, value)
        self.year_filter = QtWidgets.QComboBox()
        self.year_filter.addItem("全部年份", None)
        self.rating_filter = QtWidgets.QComboBox()
        for title, value in [("全部评分", "all"), ("已评分", "rated"), ("未评分", "unrated"),
                             ("9 分及以上", "9"), ("8 分及以上", "8"), ("7 分及以上", "7")]:
            self.rating_filter.addItem(title, value)
        for combo in (self.status_filter, self.year_filter, self.rating_filter):
            combo.currentIndexChanged.connect(self.apply_filters)
            filters.addWidget(combo)
        reset = QtWidgets.QPushButton("重置筛选")
        reset.setObjectName("Link")
        reset.clicked.connect(self.reset_filters)
        filters.addWidget(reset)
        filters.addStretch()
        self.count_label = label("尚未载入收藏", "Muted")
        filters.addWidget(self.count_label)
        layout.addLayout(filters)

        self.splitter = QtWidgets.QSplitter()
        self.table = QtWidgets.QTableView()
        configure_table(self.table)
        self.model = CollectionTableModel(self)
        self.proxy = CollectionProxy(self)
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setMinimumSectionSize(70)
        for column, width in enumerate((300, 72, 90, 80, 80, 135, 116)):
            self.table.setColumnWidth(column, width)
        self.table.sortByColumn(6, QtCore.Qt.DescendingOrder)
        self.table.selectionModel().currentRowChanged.connect(self._selection_changed)
        self.table.doubleClicked.connect(lambda _: self.detail.open_subject())
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.splitter.addWidget(self.table)
        self.detail = DetailPanel()
        self.detail_scroll = QtWidgets.QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setMinimumWidth(280)
        self.detail_scroll.setWidget(self.detail)
        self.splitter.addWidget(self.detail_scroll)
        self.splitter.setSizes([780, 300])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.detail_scroll.hide()
        self.details_toggle.toggled.connect(self.detail_scroll.setVisible)
        layout.addWidget(self.splitter, 1)
        self.empty_label = label("输入用户并同步收藏，或导入本地 JSON，开始探索你的收藏。", "Muted", True)
        layout.addWidget(self.empty_label)
        self.search_timer = QtCore.QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(160)
        self.search_timer.timeout.connect(self.apply_filters)
        self.search.textChanged.connect(lambda _: self.search_timer.start())

    def set_collection(self, collection: UserCollection) -> None:
        self.collection = collection
        self.model.set_collection(collection)
        blocker = QtCore.QSignalBlocker(self.year_filter)
        self.year_filter.clear()
        self.year_filter.addItem("全部年份", None)
        years = sorted({item.subject_year for item in collection.items if item.subject_year}, reverse=True)
        for year in years:
            self.year_filter.addItem(str(year), year)
        if any(item.subject_year is None for item in collection.items):
            self.year_filter.addItem("年份未知", 0)
        del blocker
        self.reset_filters()
        self.detail.set_item(None)

    def reset_filters(self) -> None:
        blockers = [QtCore.QSignalBlocker(widget) for widget in
                    (self.search, self.status_filter, self.year_filter, self.rating_filter)]
        self.search.clear()
        self.status_filter.setCurrentIndex(0)
        self.year_filter.setCurrentIndex(0)
        self.rating_filter.setCurrentIndex(0)
        blockers.clear()
        self.apply_filters()

    def filter_by(self, status: int | None = None, text: str = "") -> None:
        self.reset_filters()
        self.status_filter.setCurrentIndex(max(0, self.status_filter.findData(status)))
        self.search.setText(text)
        self.apply_filters()

    def apply_filters(self, *_args) -> None:
        self.search_timer.stop()
        self.proxy.set_filters(self.search.text(), self.status_filter.currentData(),
                               self.year_filter.currentData(), self.rating_filter.currentData())
        count = self.proxy.rowCount()
        self.count_label.setText(f"{count:,} / {self.model.rowCount():,} 部作品")
        self.export_button.setEnabled(count > 0)
        self.empty_label.setVisible(count == 0)
        self.empty_label.setText("没有匹配的作品。试试其他关键词，或重置筛选。" if self.collection else
                                "输入用户并同步收藏，或导入本地 JSON，开始探索你的收藏。")
        self._selection_changed(self.table.currentIndex())

    def filtered_collection(self) -> UserCollection | None:
        if self.collection is None:
            return None
        self.apply_filters()
        items = [self.model.items[self.proxy.mapToSource(self.proxy.index(row, 0)).row()]
                 for row in range(self.proxy.rowCount())]
        return self.collection.model_copy(update={"items": items, "total": len(items)})

    def _selection_changed(self, current, previous=None) -> None:
        source = self.proxy.mapToSource(current)
        self.detail.set_item(self.model.items[source.row()] if source.isValid() else None)

    def _context_menu(self, position) -> None:
        index = self.table.indexAt(position)
        if not index.isValid():
            return
        self.table.setCurrentIndex(index)
        item = self.detail.item
        menu = QtWidgets.QMenu(self)
        menu.addAction("查看作品详情", lambda: self.details_toggle.setChecked(True))
        menu.addAction("在 Bangumi 中打开", self.detail.open_subject)
        copy_action = menu.addAction("复制条目链接")
        if menu.exec(self.table.viewport().mapToGlobal(position)) is copy_action:
            QtWidgets.QApplication.clipboard().setText(f"https://bgm.tv/subject/{item.subject_id}")
            self.message.emit("已复制条目链接")
