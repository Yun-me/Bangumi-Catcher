"""One chart at a time, rendered off the UI thread and cached per dataset/theme.

The plotting runtime is imported inside the worker function, so starting the
desktop or browsing the collection never loads Matplotlib.
"""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtWidgets

from ..charts.catalog import CHART_TITLES
from ..core.models import AnalysisReport
from ..services.cancellation import check_cancelled
from .widgets import Card, ChartImage, label


class ChartPage(QtWidgets.QWidget):
    message = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        # Imported here to avoid a module-level Qt <-> worker cycle.
        from .workers import TaskRunner

        self.report: AnalysisReport | None = None
        self.dark = False
        self.generation = 0
        self.cache: dict[tuple[int, str, bool], bytes] = {}
        self.errors: dict[tuple[int, str, bool], str] = {}
        self.active_key: tuple[int, str, bool] | None = None
        self.suspended = False

        self.runner = TaskRunner(self)
        self.runner.succeeded.connect(self._ready)
        self.runner.failed.connect(self._failed)
        self.runner.busy_changed.connect(lambda busy: None if busy else self.ensure_chart())

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        toolbar = QtWidgets.QHBoxLayout()
        toolbar.addWidget(label("分析维度", "Muted"))
        self.selector = QtWidgets.QComboBox()
        for key, title in CHART_TITLES.items():
            self.selector.addItem(title, key)
        self.selector.setMinimumWidth(180)
        self.selector.currentIndexChanged.connect(self.ensure_chart)
        toolbar.addWidget(self.selector)
        toolbar.addStretch()
        self.save_button = QtWidgets.QPushButton("保存图表 PNG")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save)
        toolbar.addWidget(self.save_button)
        layout.addLayout(toolbar)

        card = Card()
        self.hint = label("载入收藏后，选择一个维度开始分析。", "Muted", True)
        card.body.addWidget(self.hint)
        self.image = ChartImage()
        card.body.addWidget(self.image, 1)
        self.retry_button = QtWidgets.QPushButton("重新生成")
        self.retry_button.clicked.connect(self._retry)
        self.retry_button.hide()
        card.body.addWidget(self.retry_button, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(card, 1)
        layout.addWidget(
            label("按需生成 · 后台渲染 · 切换维度复用缓存；年度统计范围可在设置中调整。", "Muted", True)
        )

    @property
    def key(self) -> tuple[int, str, bool]:
        return self.generation, self.selector.currentData(), self.dark

    def set_report(self, report: AnalysisReport) -> None:
        self.report = report
        self.invalidate()

    def set_dark(self, dark: bool) -> None:
        if self.dark != dark:
            self.dark = dark
            self.invalidate()

    def invalidate(self) -> None:
        self.generation += 1
        self.cache.clear()
        self.errors.clear()
        self.runner.cancel()
        self.image.clear()
        self.save_button.setEnabled(False)
        self.ensure_chart()

    def ensure_chart(self, *_args: object) -> None:
        if self.suspended or not self.isVisible() or self.report is None:
            return
        key = self.key
        self.retry_button.hide()
        if key in self.cache:
            self.image.set_image(self.cache[key])
            self.save_button.setEnabled(True)
            self.hint.setText(f"{self.selector.currentText()} · {self.report.total_items:,} 部作品")
            return

        self.image.clear()
        self.save_button.setEnabled(False)
        if key in self.errors:
            self.hint.setText(f"图表生成失败：{self.errors[key]}")
            self.retry_button.show()
            return

        self.hint.setText("正在后台生成图表，你可以继续浏览其他页面 …")
        if self.runner.busy:
            return
        report = self.report

        def render(cancel, progress):
            from ..charts.render import render_chart

            check_cancelled(cancel)
            return key, render_chart(report, key[1], dark=key[2])

        self.active_key = key
        self.runner.start(render)

    def _ready(self, result) -> None:
        key, image = result
        if key[0] == self.generation:
            self.cache[key] = image
        self.ensure_chart()

    def _failed(self, text: str) -> None:
        if self.active_key is not None and self.active_key[0] == self.generation:
            self.errors[self.active_key] = text
        self.ensure_chart()

    def _retry(self) -> None:
        self.errors.pop(self.key, None)
        self.ensure_chart()

    def _save(self) -> None:
        image = self.cache.get(self.key)
        if image is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存图表", f"{self.key[1]}.png", "PNG (*.png)")
        if path:
            try:
                Path(path).write_bytes(image)
            except OSError as exc:
                QtWidgets.QMessageBox.warning(self, "保存失败", str(exc))
            else:
                self.message.emit(f"图表已保存：{path}")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self.ensure_chart)


__all__ = ["ChartPage"]
