"""Desktop entry point.

``python -m bangumi_catcher`` and the ``bangumi-catcher`` console script both
land here. Configuration and logging are initialised before the window is
built, and failures are reported with a dialog instead of a traceback.
"""

from __future__ import annotations

import sys

import yaml
from PySide6 import QtCore, QtWidgets

from .. import __version__
from ..core.config import load_config, validate_config
from ..observability import attach_log_buffer, configure_logging
from .main_window import APP_NAME, MainWindow


def main() -> int:
    """Create the Qt application, show the window and run the event loop."""
    QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)

    try:
        config = load_config()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        QtWidgets.QMessageBox.critical(None, "无法启动", f"请检查配置文件：{exc}")
        return 1

    configure_logging(config.logging.level, config.logging.file)
    attach_log_buffer()

    issues = validate_config(config)
    if issues:
        QtWidgets.QMessageBox.warning(None, "配置有问题", "\n".join(issues))

    try:
        window = MainWindow(config=config)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        QtWidgets.QMessageBox.critical(None, "无法启动", f"请检查配置文件：{exc}")
        return 1

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
