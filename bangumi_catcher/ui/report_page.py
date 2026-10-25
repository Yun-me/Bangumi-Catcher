"""Small sortable summary tables, separate from the large collection model."""

from PySide6 import QtCore, QtGui, QtWidgets

from .widgets import configure_table, label


class ReportPage(QtWidgets.QWidget):
    def __init__(self, ranking: bool):
        super().__init__()
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

    def set_report(self, report) -> None:
        self.table.setSortingEnabled(False)
        self.model.clear()
        if self.ranking:
            self.model.setHorizontalHeaderLabels(["排名", "作品", "年份", "我的评分", "全站均分"])
            rows = [(position, item.name_cn or item.name, item.year or 0, item.rate, item.bangumi_score)
                    for position, item in enumerate(report.top_rated, start=1)]
            self.hint.setText("已看过、评分 ≥ 5 的作品，按个人评分与全站均分排列。双击打开作品。")
        else:
            self.model.setHorizontalHeaderLabels(["年份", "收藏", "看过", "在看", "想看", "搁置", "抛弃", "均分"])
            rows = [(item.year, item.total, item.finished, item.watching, item.wish,
                     item.on_hold, item.dropped, item.avg_rating) for item in report.year_trend]
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
                self.table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)

    def _open(self, index) -> None:
        if self.ranking and index.isValid():
            subject_id = index.data(QtCore.Qt.UserRole)
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(f"https://bgm.tv/subject/{subject_id}"))
