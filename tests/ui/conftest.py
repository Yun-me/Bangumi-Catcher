"""Shared Qt fixtures for headless UI tests."""

from __future__ import annotations

import time

import pytest
from PySide6 import QtCore, QtGui, QtTest

from bangumi_catcher.core.config import AppConfig
from bangumi_catcher.ui.main_window import MainWindow


def wait_until(predicate, timeout: float = 8.0) -> None:
    """Spin the Qt event loop until ``predicate`` is true or the timeout expires."""
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QtTest.QTest.qWait(10)
    assert predicate(), "Qt operation did not finish before the timeout"


@pytest.fixture
def png() -> bytes:
    image = QtGui.QImage(8, 8, QtGui.QImage.Format_ARGB32)
    image.fill(QtCore.Qt.white)
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(buffer.data())


@pytest.fixture
def window(qapp, tmp_path):
    """A shown main window backed by an isolated INI settings file."""
    settings = QtCore.QSettings(str(tmp_path / "ui.ini"), QtCore.QSettings.IniFormat)
    settings.setValue("theme", "light")
    widget = MainWindow(AppConfig(), settings)
    widget.resize(1380, 940)
    widget.show()
    QtTest.QTest.qWait(20)
    yield widget
    widget.close()
    wait_until(lambda: not widget.task.busy and not widget.charts.runner.busy)
    widget.close()
    widget.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


__all__ = ["wait_until"]
