"""Small native widgets; importing the desktop never imports matplotlib."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.models import CollectionItem


def label(text: str, role: str = "", wrap: bool = False) -> QtWidgets.QLabel:
    widget = QtWidgets.QLabel(text)
    widget.setTextFormat(QtCore.Qt.PlainText)
    widget.setObjectName(role)
    widget.setWordWrap(wrap)
    return widget


def progress_label(item: CollectionItem) -> str:
    total = item.subject.episodes_total if item.subject else 0
    if item.type == 2:
        return f"已完成 · {total} 集" if total else "已完成"
    if item.type == 1:
        return "尚未开始"
    if item.ep_status > 0:
        return f"{item.ep_status} / {total} 集" if total else f"已记录 {item.ep_status} 集"
    return f"0 / {total} 集" if total else "暂无进度"


class Card(QtWidgets.QFrame):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self.body = QtWidgets.QVBoxLayout(self)
        self.body.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.body.setContentsMargins(22, 20, 22, 20)
        self.body.setSpacing(14)
        if title:
            self.body.addWidget(label(title, "SectionTitle"))


class StatCard(Card):
    def __init__(self, title: str, hint: str):
        super().__init__()
        self.setMinimumWidth(155)
        self.body.setSpacing(5)
        self.body.addWidget(label(title, "Muted"))
        self.value = label("—", "StatValue")
        self.body.addWidget(self.value)
        self.body.addWidget(label(hint, "Muted"))


class ChartImage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.pixmap = QtGui.QPixmap()
        self.setMinimumSize(300, 260)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def set_image(self, data: bytes) -> None:
        self.pixmap.loadFromData(data)
        self.update()

    def clear(self) -> None:
        self.pixmap = QtGui.QPixmap()
        self.update()

    def paintEvent(self, event):
        if self.pixmap.isNull():
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        size = self.pixmap.size().scaled(self.size(), QtCore.Qt.KeepAspectRatio)
        target = QtCore.QRect(QtCore.QPoint(), size)
        target.moveCenter(self.rect().center())
        painter.drawPixmap(target, self.pixmap)


def configure_table(table: QtWidgets.QTableView) -> None:
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setSortingEnabled(True)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    table.verticalHeader().hide()
    table.verticalHeader().setDefaultSectionSize(48)
    table.horizontalHeader().setHighlightSections(False)
    table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
