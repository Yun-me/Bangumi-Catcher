"""对话框：设置、日志、关于。"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from ..core.config import AppConfig, load_config, save_config


class _LogBuffer(logging.Handler):
    """把日志保留在内存中，供日志对话框展示。"""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


log_buffer = _LogBuffer()
log_buffer.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))


class SettingsDialog(QtWidgets.QDialog):
    """编辑并保存 config.yaml 的对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(460)
        self._cfg = load_config()

        form = QtWidgets.QFormLayout(self)
        self.base_url = QtWidgets.QLineEdit(self._cfg.api.base_url)
        self.timeout = QtWidgets.QDoubleSpinBox()
        self.timeout.setRange(1, 300)
        self.timeout.setValue(self._cfg.api.timeout)
        self.proxy = QtWidgets.QLineEdit(self._cfg.api.proxy or "")
        self.proxy.setPlaceholderText("例如 http://127.0.0.1:7890，留空表示直连")
        self.max_concurrent = QtWidgets.QSpinBox()
        self.max_concurrent.setRange(1, 32)
        self.max_concurrent.setValue(self._cfg.collection.max_concurrent)
        self.cache_enabled = QtWidgets.QCheckBox("启用本地缓存")
        self.cache_enabled.setChecked(self._cfg.cache.enabled)
        self.cache_ttl = QtWidgets.QSpinBox()
        self.cache_ttl.setRange(0, 86400 * 30)
        self.cache_ttl.setSuffix(" 秒")
        self.cache_ttl.setValue(self._cfg.cache.ttl)
        self.top_n = QtWidgets.QSpinBox()
        self.top_n.setRange(1, 100)
        self.top_n.setValue(self._cfg.analysis.top_n)
        self.theme = QtWidgets.QComboBox()
        self.theme.addItems(["system", "light", "dark"])
        self.theme.setCurrentText(self._cfg.ui.theme)

        form.addRow("API 地址", self.base_url)
        form.addRow("请求超时（秒）", self.timeout)
        form.addRow("HTTP 代理", self.proxy)
        form.addRow("最大并发", self.max_concurrent)
        form.addRow("", self.cache_enabled)
        form.addRow("缓存有效期", self.cache_ttl)
        form.addRow("排行数量", self.top_n)
        form.addRow("默认主题", self.theme)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self) -> None:
        cfg: AppConfig = load_config()
        cfg.api.base_url = self.base_url.text().strip() or "https://api.bgm.tv"
        cfg.api.timeout = self.timeout.value()
        cfg.api.proxy = self.proxy.text().strip() or None
        cfg.collection.max_concurrent = self.max_concurrent.value()
        cfg.cache.enabled = self.cache_enabled.isChecked()
        cfg.cache.ttl = self.cache_ttl.value()
        cfg.analysis.top_n = self.top_n.value()
        cfg.ui.theme = self.theme.currentText()
        try:
            path = save_config(cfg, Path.cwd() / "config.yaml")
        except OSError as exc:
            QtWidgets.QMessageBox.critical(self, "保存失败", f"无法写入配置文件：{exc}")
            return
        QtWidgets.QMessageBox.information(self, "已保存", f"配置已写入：{path}")
        self.accept()


class LogDialog(QtWidgets.QDialog):
    """显示运行日志的简易对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("运行日志")
        self.resize(640, 420)
        layout = QtWidgets.QVBoxLayout(self)
        self.view = QtWidgets.QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setPlainText("\n".join(log_buffer.lines[-500:]))
        layout.addWidget(self.view)
        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=QtCore.Qt.AlignRight)

    def append(self, line: str) -> None:
        self.view.appendPlainText(line)
