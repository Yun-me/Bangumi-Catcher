"""Preferences dialog writing to the per-user configuration file.

The dialog edits a deep copy of :class:`AppConfig`; only an explicit save
persists it, so cancelling never changes the running configuration.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ..core.config import (
    AppConfig,
    load_config,
    save_config,
    user_config_path,
    validate_config,
)
from .widgets import label

LOG_LEVELS: tuple[tuple[str, str], ...] = (
    ("调试 (DEBUG)", "DEBUG"),
    ("信息 (INFO)", "INFO"),
    ("警告 (WARNING)", "WARNING"),
    ("错误 (ERROR)", "ERROR"),
)


class SettingsDialog(QtWidgets.QDialog):
    """Appearance, network, data/analysis and logging settings."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        config: AppConfig | None = None,
        theme: str | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("偏好设置")
        self.setMinimumWidth(600)
        self.resize(640, 620)
        self._cfg = (config if config is not None else load_config()).model_copy(deep=True)
        self.result_config = self._cfg

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)
        layout.addWidget(label("让工作台适合你的习惯", "SectionTitle"))

        tabs = QtWidgets.QTabWidget()
        layout.addWidget(tabs)

        def form_page(title: str) -> QtWidgets.QFormLayout:
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
        appearance.addRow(
            label("快捷键：Ctrl+O 导入 · Ctrl+F 搜索 · Ctrl+D 切换主题 · F5 同步", "Muted", True)
        )

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
        for title, widget in [
            ("API 地址", self.base_url),
            ("HTTP 代理", self.proxy),
            ("请求超时", self.timeout),
            ("最大并发", self.max_concurrent),
            ("最大尝试次数", self.max_retries),
            ("请求最小间隔", self.request_interval),
        ]:
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

        self.log_level = QtWidgets.QComboBox()
        for title, value in LOG_LEVELS:
            self.log_level.addItem(title, value)
        self.log_level.setCurrentIndex(max(0, self.log_level.findData(self._cfg.logging.level)))
        self.log_file = QtWidgets.QLineEdit(self._cfg.logging.file)
        self.log_file.setPlaceholderText("留空只输出到终端")

        data.addRow(self.cache_enabled)
        for title, widget in [
            ("缓存有效期", self.cache_ttl),
            ("缓存目录", self.cache_dir),
            ("默认导出目录", self.output_dir),
            ("排行 / 标签数量", self.top_n),
            ("统计起始年份", self.year_start),
            ("统计结束年份", self.year_end),
            ("日志级别", self.log_level),
            ("日志文件", self.log_file),
        ]:
            data.addRow(title, widget)

        path_label = label(f"设置保存到：{user_config_path()}\n环境变量覆盖仍在重启后生效。", "Muted", True)
        path_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(path_label)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.button(QtWidgets.QDialogButtonBox.Save).setText("保存设置")
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _spin(minimum: int, maximum: int, value: int) -> QtWidgets.QSpinBox:
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
        config.logging.level = self.log_level.currentData()
        config.logging.file = self.log_file.text().strip()

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


__all__ = ["LOG_LEVELS", "SettingsDialog"]
