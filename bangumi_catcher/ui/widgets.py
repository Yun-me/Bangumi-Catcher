"""可复用 UI 组件：统计卡片、图表卡片、搜索代理等。"""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6 import QtCore, QtGui, QtWidgets


def soft_shadow(widget: QtWidgets.QWidget, blur: int = 18, dy: int = 2, alpha: int = 28) -> None:
    """给卡片加一层极浅阴影，替代生硬描边来区分层级。"""
    effect = QtWidgets.QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(dy)
    effect.setColor(QtGui.QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(effect)


def progress_label(item) -> str:
    """收藏条目的「进度」展示文本。"""
    total = item.subject.episodes_total if item.subject else 0
    if item.type == 2:  # 看过
        return f"看完 · 全 {total} 话" if total else "看完"
    if item.type == 1:  # 想看
        return "—"
    if item.ep_status > 0:
        return f"{item.ep_status}/{total}" if total else f"看到第 {item.ep_status} 话"
    return f"0/{total}" if total else "—"


class StatCard(QtWidgets.QFrame):
    """概览数字卡片。"""

    def __init__(self, value, label: str):
        super().__init__()
        self.setObjectName("StatCard")
        self.setFixedSize(176, 92)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(2)
        value_label = QtWidgets.QLabel(str(value))
        value_label.setObjectName("StatValue")
        text_label = QtWidgets.QLabel(label)
        text_label.setObjectName("StatLabel")
        layout.addWidget(value_label)
        layout.addWidget(text_label)
        layout.addStretch()
        soft_shadow(self)


class ChartCard(QtWidgets.QFrame):
    """图表卡片：标题 + 随窗口重绘的 matplotlib 画布。"""

    def __init__(self, title: str, figure):
        super().__init__()
        self.setObjectName("ChartCard")
        self.setMinimumWidth(440)
        self.setMinimumHeight(340)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("ChartTitle")
        layout.addWidget(title_label)
        self.canvas = FigureCanvasQTAgg(figure)
        self.canvas.setStyleSheet("background:transparent;")
        layout.addWidget(self.canvas, 1)
        soft_shadow(self)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(520, 380)


class SearchProxy(QtCore.QSortFilterProxyModel):
    """跨作品名/标签/短评的搜索 + 收藏状态过滤。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._needle = ""
        self._status_filter = ""

    def set_needle(self, text: str) -> None:
        self._needle = (text or "").strip().lower()
        self.invalidateFilter()

    def set_status_filter(self, status: str) -> None:
        self._status_filter = status or ""
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):  # noqa: N802
        model = self.sourceModel()
        if self._status_filter:
            status_index = model.index(source_row, 2, source_parent)
            status = model.data(status_index, QtCore.Qt.UserRole) or ""
            if status != self._status_filter:
                return False
        if not self._needle:
            return True
        index = model.index(source_row, 0, source_parent)
        haystack = model.data(index, QtCore.Qt.UserRole) or ""
        return self._needle in haystack.lower()
