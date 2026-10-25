"""Small reusable widgets; importing the desktop never imports Matplotlib."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


def label(text: str, role: str = "", wrap: bool = False) -> QtWidgets.QLabel:
    """A plain-text label with an object name used as the style selector."""
    widget = QtWidgets.QLabel(text)
    widget.setTextFormat(QtCore.Qt.PlainText)
    widget.setObjectName(role)
    widget.setWordWrap(wrap)
    return widget


def clear_layout(layout: QtWidgets.QLayout) -> None:
    """Delete every child widget/layout so a container can be rebuilt in place."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.hide()
            widget.deleteLater()
            continue
        child = item.layout()
        if child is not None:
            clear_layout(child)
            child.deleteLater()


class Card(QtWidgets.QFrame):
    """A bordered surface with a vertical ``body`` layout."""

    def __init__(self, title: str = "", parent: QtWidgets.QWidget | None = None):
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
    """Metric card used by the overview dashboard."""

    def __init__(self, title: str, hint: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setMinimumWidth(155)
        self.body.setSpacing(5)
        self.body.addWidget(label(title, "Muted"))
        self.value = label("—", "StatValue")
        self.body.addWidget(self.value)
        self.body.addWidget(label(hint, "Muted"))


class ChartImage(QtWidgets.QWidget):
    """Scaled, aspect-preserving display of a rendered PNG."""

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.pixmap = QtGui.QPixmap()
        self.setMinimumSize(300, 260)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def set_image(self, data: bytes) -> None:
        self.pixmap.loadFromData(data)
        self.update()

    def clear(self) -> None:
        self.pixmap = QtGui.QPixmap()
        self.update()

    def paintEvent(self, event) -> None:
        if self.pixmap.isNull():
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        size = self.pixmap.size().scaled(self.size(), QtCore.Qt.KeepAspectRatio)
        target = QtCore.QRect(QtCore.QPoint(), size)
        target.moveCenter(self.rect().center())
        painter.drawPixmap(target, self.pixmap)


def configure_table(table: QtWidgets.QTableView) -> None:
    """Apply the shared read-only table defaults."""
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


__all__ = ["Card", "ChartImage", "StatCard", "clear_layout", "configure_table", "label"]
