"""Bangumi Catcher GUI 入口（兼容旧导入路径）。"""

from __future__ import annotations

import logging

import yaml
from PySide6 import QtCore, QtWidgets

from .. import __version__
from .dialogs import log_buffer
from .main_window import APP_NAME, MainWindow


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger().addHandler(log_buffer)
    QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    try:
        window = MainWindow()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        QtWidgets.QMessageBox.critical(None, "无法启动", f"请检查配置文件：{exc}")
        return
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
