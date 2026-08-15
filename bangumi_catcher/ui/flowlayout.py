"""FlowLayout —— 像 CSS flex-wrap 一样自动换行的布局.

让卡片/图表随窗口宽度自动重排：窄窗一列，宽窗多列。
这是解决"全屏图标挤在一角 / 不全屏内容被裁剪"的核心。
改编自 Qt 官方 FlowLayout 示例。
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, margin=0, h_spacing=16, v_spacing=16):
        super().__init__(parent)
        self._items: list[QtWidgets.QLayoutItem] = []
        self._h = h_spacing
        self._v = v_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        while self._items:
            self.takeAt(0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return QtCore.Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QtCore.QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QtCore.QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        eff = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y = eff.x(), eff.y()
        line_height = 0
        for item in self._items:
            w = item.sizeHint().width()
            h = item.sizeHint().height()
            next_x = x + w + self._h
            if next_x - self._h > eff.right() and line_height > 0:
                x = eff.x()
                y = y + line_height + self._v
                next_x = x + w + self._h
                line_height = 0
            if not test_only:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, h)
        return y + line_height - rect.y() + m.bottom()
