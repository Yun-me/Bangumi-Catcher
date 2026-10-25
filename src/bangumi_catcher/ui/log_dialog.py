"""Live log viewer backed by the in-memory :data:`~bangumi_catcher.observability.log_buffer`."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ..observability import log_buffer
from .widgets import label


class LogDialog(QtWidgets.QDialog):
    """Shows the last 1,000 log lines and follows the tail while open."""

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("运行日志")
        self.resize(780, 520)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label("实时更新 · 仅保留最近 1,000 行 · 关闭窗口不会中断任务", "Muted"))
        self.view = QtWidgets.QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(1000)
        layout.addWidget(self.view)

        buttons = QtWidgets.QHBoxLayout()
        copy_button = QtWidgets.QPushButton("复制日志")
        copy_button.clicked.connect(
            lambda: QtWidgets.QApplication.clipboard().setText(self.view.toPlainText())
        )
        buttons.addWidget(copy_button)
        buttons.addStretch()
        close_button = QtWidgets.QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self._previous: list[str] = []
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self._refresh)
        self.timer.start()
        self._refresh()

    def _refresh(self) -> None:
        lines = log_buffer.lines
        if lines == self._previous:
            return
        scrollbar = self.view.verticalScrollBar()
        previous_value = scrollbar.value()
        follow = previous_value == scrollbar.maximum()
        self.view.setPlainText("\n".join(lines))
        scrollbar.setValue(scrollbar.maximum() if follow else previous_value)
        self._previous = lines


__all__ = ["LogDialog"]
