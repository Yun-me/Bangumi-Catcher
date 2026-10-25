"""Small sortable summary tables for the ranking and timeline pages."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.models import AnalysisReport
from .widgets import configure_table, label

RANKING_HEADERS = ("排名", "作品", "年份", "我的评分", "全站均分")
TIMELINE_HEADERS = ("年份", "收藏", "看过", "在看", "想看", "搁置", "抛弃", "均分")


class ReportPage(QtWidgets.QWidget):
    """Either the favourite ranking (``ranking=True``) or the yearly table."""

    def __init__(self, ranking: bool, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.ranking = ranking
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.hint = label("载入收藏后查看统计。", "Muted", True)
        layout.addWidget(self.hint)
        self.table = QtWidgets.QTableView()
        configure_table(self.table)
        self.model = QtGui.QStandardItemModel(self)
        self.table.setModel(self.model)
        self.table.doubleClicked.connect(self._open)
        layout.addWidget(self.table, 1)

    def set_report(self, report: AnalysisReport) -> None:
        self.table.setSortingEnabled(False)
        self.model.clear()
        if self.ranking:
            self.model.setHorizontalHeaderLabels(list(RANKING_HEADERS))
            rows = [
                (position, item.name_cn or item.name, item.year or 0, item.rate, item.bangumi_score)
                for position, item in enumerate(report.top_rated, start=1)
            ]
            self.hint.setText("已看过、评分 ≥ 5 的作品，按个人评分与全站均分排列。双击打开作品。")
        else:
            self.model.setHorizontalHeaderLabels(list(TIMELINE_HEADERS))
            rows = [
                (
                    item.year,
                    item.total,
                    item.finished,
                    item.watching,
                    item.wish,
                    item.on_hold,
                    item.dropped,
                    item.avg_rating,
                )
                for item in report.year_trend
            ]
            self.hint.setText("按作品发行年份统计；均分仅计算已看过且已评分的作品，范围可在设置中调整。")

        for row_index, values in enumerate(rows):
            cells = []
            for value in values:
                cell = QtGui.QStandardItem()
                cell.setData(value, QtCore.Qt.DisplayRole)
                if self.ranking:
                    cell.setData(report.top_rated[row_index].subject_id, QtCore.Qt.UserRole)
                cells.append(cell)
            self.model.appendRow(cells)

        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, QtCore.Qt.AscendingOrder if self.ranking else QtCore.Qt.DescendingOrder)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        if self.ranking:
            for column in (0, 2, 3, 4):
                self.table.horizontalHeader().setSectionResizeMode(
                    column, QtWidgets.QHeaderView.ResizeToContents
                )

    def _open(self, index: QtCore.QModelIndex) -> None:
        if self.ranking and index.isValid():
            subject_id = index.data(QtCore.Qt.UserRole)
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(f"https://bgm.tv/subject/{subject_id}"))


__all__ = ["RANKING_HEADERS", "TIMELINE_HEADERS", "ReportPage"]
