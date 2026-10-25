"""Preferences in a writable user location and a bounded, live log viewer."""

from __future__ import annotations

import logging
from collections import deque

from PySide6 import QtCore, QtWidgets

from ..core.config import AppConfig, load_config, save_config, user_config_path, validate_config
from .widgets import label


class _LogBuffer(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self._lines = deque(maxlen=1000)

    def emit(self, record: logging.LogRecord) -> None:
        self._lines.append(self.format(record))

    @property
    def lines(self) -> list[str]:
        self.acquire()
        try:
            return list(self._lines)
        finally:
            self.release()


log_buffer = _LogBuffer()
log_buffer.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, config: AppConfig | None = None, theme: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("偏好设置")
        self.setMinimumWidth(600)
        self.resize(640, 580)
        self._cfg = (config if config is not None else load_config()).model_copy(deep=True)
        self.result_config = self._cfg
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)
        layout.addWidget(label("让工作台适合你的习惯", "SectionTitle"))
        tabs = QtWidgets.QTabWidget()
        layout.addWidget(tabs)

        def form_page(title):
            page = QtWidgets.QWidget()
            form = QtWidgets.QFormLayout(page)
            form.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
            form.setContentsMargins(8, 18, 8, 14)
            form.setSpacing(14)
            scroll = QtWidgets.QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            tabs.addTab(scroll, title)
            return form

        appearance = form_page("外观")
        self.theme = QtWidgets.QComboBox()
        for title, value in [("跟随系统", "system"), ("浅色 · 森绿", "light"), ("深色 · 夜间", "dark")]:
            self.theme.addItem(title, value)
        self.theme.setCurrentIndex(self.theme.findData(theme or self._cfg.ui.theme))
        appearance.addRow("界面主题", self.theme)
        self.recent_limit = self._spin(1, 50, self._cfg.ui.max_recent_users)
        appearance.addRow("历史用户数量", self.recent_limit)
        appearance.addRow(label("快捷键：Ctrl+O 导入 · Ctrl+F 搜索 · Ctrl+D 切换主题 · F5 同步", "Muted", True))

        network = form_page("网络")
        self.base_url = QtWidgets.QLineEdit(self._cfg.api.base_url)
        self.timeout = QtWidgets.QDoubleSpinBox()
        self.timeout.setRange(1, 300)
        self.timeout.setValue(self._cfg.api.timeout)
        self.timeout.setSuffix(" 秒")
        self.proxy = QtWidgets.QLineEdit(self._cfg.api.proxy or "")
        self.proxy.setPlaceholderText("http://127.0.0.1:7890；留空遵循系统环境代理")
        self.max_concurrent = self._spin(1, 32, self._cfg.collection.max_concurrent)
        self.max_retries = self._spin(1, 10, self._cfg.api.max_retries)
        self.request_interval = QtWidgets.QDoubleSpinBox()
        self.request_interval.setRange(0, 30)
        self.request_interval.setSingleStep(0.1)
        self.request_interval.setValue(self._cfg.collection.rate_limit_delay)
        self.request_interval.setSuffix(" 秒")
        for title, widget in [("API 地址", self.base_url), ("HTTP 代理", self.proxy), ("请求超时", self.timeout),
                              ("最大并发", self.max_concurrent), ("最大尝试次数", self.max_retries),
                              ("请求最小间隔", self.request_interval)]:
            network.addRow(title, widget)

        data = form_page("数据与分析")
        self.cache_enabled = QtWidgets.QCheckBox("启用本地请求缓存")
        self.cache_enabled.setChecked(self._cfg.cache.enabled)
        self.cache_ttl = self._spin(0, 86400 * 30, self._cfg.cache.ttl)
        self.cache_ttl.setSuffix(" 秒")
        self.cache_dir = QtWidgets.QLineEdit(self._cfg.cache.dir)
        self.cache_dir.setPlaceholderText("留空使用默认缓存目录")
        self.output_dir = QtWidgets.QLineEdit(self._cfg.export.output_dir)
        self.top_n = self._spin(1, 1000, self._cfg.analysis.top_n)
        self.year_start = self._spin(1, 9999, self._cfg.analysis.year_start)
        self.year_end = self._spin(1, 9999, self._cfg.analysis.year_end)
        data.addRow(self.cache_enabled)
        for title, widget in [("缓存有效期", self.cache_ttl), ("缓存目录", self.cache_dir),
                              ("默认导出目录", self.output_dir), ("排行 / 标签数量", self.top_n),
                              ("统计起始年份", self.year_start), ("统计结束年份", self.year_end)]:
            data.addRow(title, widget)
        path_label = label(f"设置保存到：{user_config_path()}\n环境变量覆盖仍在重启后生效。", "Muted", True)
        path_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(path_label)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttons.button(QtWidgets.QDialogButtonBox.Save).setText("保存设置")
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _spin(minimum: int, maximum: int, value: int):
        widget = QtWidgets.QSpinBox()
        widget.setRange(minimum, maximum)
        widget.setValue(value)
        return widget

    def _save(self) -> None:
        config = self._cfg.model_copy(deep=True)
        config.api.base_url = self.base_url.text().strip()
        config.api.proxy = self.proxy.text().strip() or None
        config.api.timeout = self.timeout.value()
        config.api.max_retries = self.max_retries.value()
        config.collection.max_concurrent = self.max_concurrent.value()
        config.collection.rate_limit_delay = self.request_interval.value()
        config.cache.enabled = self.cache_enabled.isChecked()
        config.cache.ttl = self.cache_ttl.value()
        config.cache.dir = self.cache_dir.text().strip()
        config.export.output_dir = self.output_dir.text().strip() or "output"
        config.analysis.top_n = self.top_n.value()
        config.analysis.year_start = self.year_start.value()
        config.analysis.year_end = self.year_end.value()
        config.ui.theme = self.theme.currentData()
        config.ui.max_recent_users = self.recent_limit.value()
        try:
            config = AppConfig.model_validate(config.model_dump())
            issues = validate_config(config)
            if issues:
                raise ValueError("\n".join(issues))
            save_config(config, user_config_path())
        except (ValueError, OSError) as exc:
            QtWidgets.QMessageBox.warning(self, "无法保存设置", str(exc))
            return
        self.result_config = config
        self.accept()


class LogDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
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
        copy_button.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(self.view.toPlainText()))
        buttons.addWidget(copy_button)
        buttons.addStretch()
        close_button = QtWidgets.QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        self._previous = []
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
        old_value = scrollbar.value()
        follow = old_value == scrollbar.maximum()
        self.view.setPlainText("\n".join(lines))
        scrollbar.setValue(scrollbar.maximum() if follow else old_value)
        self._previous = lines
