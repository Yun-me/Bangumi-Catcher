"""Bangumi Catcher GUI 入口（兼容旧导入路径）。"""

from __future__ import annotations

import logging

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
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
