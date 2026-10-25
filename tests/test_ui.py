import subprocess
import sys
import threading
import time

import pytest
from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from bangumi_catcher.core.config import AppConfig
from bangumi_catcher.core.export import collection_to_json
from bangumi_catcher.services.fetch_service import analyze_user_collection
from bangumi_catcher.ui.collection_model import CollectionProxy, CollectionTableModel
from bangumi_catcher.ui.main_window import MainWindow
from bangumi_catcher.ui.workers import TaskRunner


@pytest.fixture
def png(qapp):
    image = QtGui.QImage(8, 8, QtGui.QImage.Format_ARGB32)
    image.fill(QtCore.Qt.white)
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(buffer.data())


def wait_until(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QtTest.QTest.qWait(10)
    assert predicate(), "Qt operation did not finish before the timeout"


@pytest.fixture
def window(qapp, tmp_path):
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


def test_desktop_import_does_not_load_plotting_runtime():
    result = subprocess.run([sys.executable, "-c", "import sys; import bangumi_catcher.ui.main_window; "
                             "assert 'matplotlib' not in sys.modules"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_virtual_model_and_numeric_sort(qapp, sample_collection):
    model = CollectionTableModel()
    model.set_collection(sample_collection)
    proxy = CollectionProxy()
    proxy.setSourceModel(model)
    assert model.rowCount() == 5
    assert model.columnCount() == 7
    assert model.rowCount(model.index(0, 0)) == 0
    proxy.sort(3, QtCore.Qt.DescendingOrder)
    assert proxy.index(0, 3).data() == "8"
    assert proxy.mapToSource(proxy.index(0, 0)).row() == 0
    assert model.index(1, 3).data() == "—"


def test_proxy_preserves_selection_and_round_trips_indexes(qapp, sample_collection):
    model = CollectionTableModel()
    model.set_collection(sample_collection)
    proxy = CollectionProxy()
    proxy.setSourceModel(model)
    persistent = QtCore.QPersistentModelIndex(proxy.index(0, 0))
    proxy.sort(3, QtCore.Qt.AscendingOrder)
    assert proxy.mapToSource(persistent).row() == 0
    for row in range(proxy.rowCount()):
        index = proxy.index(row, 1)
        assert proxy.mapFromSource(proxy.mapToSource(index)) == index
    proxy.set_filters(status=1)
    assert not persistent.isValid()
    assert proxy.rowCount() == 1
    assert not proxy.mapFromSource(model.index(0, 0)).isValid()
    model.set_collection(sample_collection.model_copy(update={"items": [], "total": 0}))
    assert proxy.rowCount() == 0


def test_proxy_obeys_qt_model_contract(qapp, sample_collection):
    model = CollectionTableModel()
    proxy = CollectionProxy()
    proxy.setSourceModel(model)
    messages = []
    previous = QtCore.qInstallMessageHandler(lambda kind, context, message: messages.append(message))
    try:
        tester = QtTest.QAbstractItemModelTester(proxy, QtTest.QAbstractItemModelTester.FailureReportingMode.Warning)
        model.set_collection(sample_collection)
        proxy.sort(3, QtCore.Qt.DescendingOrder)
        proxy.set_filters(status=2)
        proxy.sort(1, QtCore.Qt.AscendingOrder)
        proxy.set_filters("nothing matches")
        model.set_collection(sample_collection)
        assert tester.model() is proxy
    finally:
        QtCore.qInstallMessageHandler(previous)
    assert not messages


def test_sort_and_filter_do_not_request_individual_cell_data(qapp, sample_collection, monkeypatch):
    model = CollectionTableModel()
    model.set_collection(sample_collection)
    proxy = CollectionProxy()
    proxy.setSourceModel(model)

    def unexpected(*args, **kwargs):
        pytest.fail("Sorting and filtering should use cached row indexes, not Qt cell callbacks")

    monkeypatch.setattr(model, "data", unexpected)
    proxy.sort(3, QtCore.Qt.DescendingOrder)
    proxy.set_filters("原创", status=2)
    assert proxy.rowCount() == 3


def test_combined_filters_match_original_title_tags_and_comment(qapp, sample_collection):
    sample_collection.items[0].comment = "这是一次很棒的旅行"
    model = CollectionTableModel()
    model.set_collection(sample_collection)
    proxy = CollectionProxy()
    proxy.setSourceModel(model)
    proxy.set_filters("ANIME1 原创 旅行", status=2, year=2020, rating="8")
    assert proxy.rowCount() == 1
    proxy.set_filters(status=2, year=2020, rating="unrated")
    assert proxy.rowCount() == 1
    assert proxy.mapToSource(proxy.index(0, 0)).row() == 1
    proxy.set_filters("不存在")
    assert proxy.rowCount() == 0


def test_offline_import_repeated_load_and_filtered_export(window, tmp_path, sample_collection):
    source = tmp_path / "collection.json"
    collection_to_json(sample_collection, str(source))
    for _ in range(2):
        assert window.import_path(str(source))
        wait_until(lambda: not window.task.busy)
        assert window.collection is not None
    assert window.report.total_items == 5
    assert window.settings.value("recent_users", type=list) == ["tester"]
    assert window.export_button.isEnabled()
    window._open_library(2)
    assert window.library.proxy.rowCount() == 3
    window.library.table.sortByColumn(3, QtCore.Qt.DescendingOrder)
    window.library.table.selectRow(0)
    assert window.library.detail.item.subject_id == 1
    filtered = window.library.filtered_collection()
    assert filtered.total == 3
    assert [item.subject_id for item in filtered.items] == [1, 3, 2]
    window.library.search.setText("Anime2")
    wait_until(lambda: window.library.proxy.rowCount() == 1)
    assert window.library.filtered_collection().items[0].subject_id == 2


def test_failed_import_retains_existing_data(window, tmp_path, sample_collection):
    window._set_data(sample_collection, analyze_user_collection(sample_collection, AppConfig()), "测试")
    source = tmp_path / "broken.json"
    source.write_text("not JSON", encoding="utf-8")
    window.import_path(str(source))
    wait_until(lambda: not window.task.busy)
    assert window.collection is sample_collection
    assert window.feedback.isVisible()
    assert window.fetch_button.isEnabled()


def test_charts_are_lazy_and_cached(window, sample_collection, monkeypatch, png):
    calls = []

    def render(report, key, dark=False):
        calls.append((key, dark))
        return png

    monkeypatch.setattr("bangumi_catcher.ui.visualizer.render_chart", render)
    window._set_data(sample_collection, analyze_user_collection(sample_collection, AppConfig()), "测试")
    QtTest.QTest.qWait(30)
    assert not calls
    window._navigate(2)
    wait_until(lambda: window.charts.key in window.charts.cache and not window.charts.runner.busy)
    assert not window.charts.image.pixmap.isNull()
    assert len(calls) == 1
    window._navigate(0)
    window._navigate(2)
    QtTest.QTest.qWait(20)
    assert len(calls) == 1
    window._toggle_theme()
    wait_until(lambda: window.charts.key in window.charts.cache and not window.charts.runner.busy)
    assert calls[-1][1] is True
    assert len(calls) == 2


def test_real_background_chart_is_displayed(window, sample_collection):
    window._set_data(sample_collection, analyze_user_collection(sample_collection, AppConfig()), "测试")
    loop = QtCore.QEventLoop()
    poll = QtCore.QTimer()
    deadline = QtCore.QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(loop.quit)
    ticks = []

    def check():
        ticks.append(True)
        if window.charts.key in window.charts.cache and not window.charts.runner.busy:
            loop.quit()

    poll.timeout.connect(check)
    poll.start(20)
    deadline.start(20000)
    window._navigate(2)
    loop.exec()
    poll.stop()
    deadline.stop()
    assert ticks
    assert window.charts.key in window.charts.cache
    assert window.charts.image.pixmap.width() > 500


def test_empty_and_minimum_window_layout(window):
    window.resize(900, 600)
    QtTest.QTest.qWait(40)
    assert window.overview.explore_button.height() >= 32
    assert window.overview.hero_title.height() >= 35
    assert window.width() == 900
    assert window.height() == 600
    assert window.overview.stat_columns == 2
    assert not window.export_button.isEnabled()
    window._focus_search()
    assert window.pages.currentWidget() is window.library
    assert window.library.search.hasFocus()


def test_stale_chart_failure_does_not_poison_new_selection(window, sample_collection, monkeypatch, png):
    entered, release = threading.Event(), threading.Event()

    def render(report, key, dark=False):
        if key == "rating_distribution":
            entered.set()
            release.wait(3)
            raise ValueError("first chart failed")
        return png

    monkeypatch.setattr("bangumi_catcher.ui.visualizer.render_chart", render)
    window._set_data(sample_collection, analyze_user_collection(sample_collection, AppConfig()), "测试")
    window._navigate(2)
    try:
        wait_until(entered.is_set)
        window.charts.selector.setCurrentIndex(1)
    finally:
        release.set()
    wait_until(lambda: window.charts.key in window.charts.cache and not window.charts.runner.busy)
    assert window.charts.key not in window.charts.errors
    assert not window.charts.image.pixmap.isNull()


def test_close_cancels_and_waits_without_destroying_running_thread(window):
    entered = threading.Event()

    def pending(cancel, progress):
        entered.set()
        cancel.wait(5)
        return "message", "done"

    window.task.start(pending)
    wait_until(entered.is_set)
    window.close()
    wait_until(lambda: not window.isVisible() and not window.task.busy)


def test_task_runner_rejects_overlapping_jobs(qapp):
    runner = TaskRunner()
    release = threading.Event()
    assert runner.start(lambda cancel, progress: release.wait(2))
    assert not runner.start(lambda cancel, progress: None)
    release.set()
    wait_until(lambda: not runner.busy)
    assert runner.start(lambda cancel, progress: 42)
    wait_until(lambda: not runner.busy)


def test_log_buffer_is_bounded():
    import logging

    from bangumi_catcher.ui.dialogs import _LogBuffer

    buffer = _LogBuffer()
    for number in range(1100):
        buffer.handle(logging.LogRecord("test", logging.INFO, "", 0, str(number), (), None))
    assert len(buffer.lines) == 1000
    assert buffer.lines[0] == "100"


def test_settings_save_to_user_directory(window, tmp_path, monkeypatch):
    from bangumi_catcher.core.config import load_config
    from bangumi_catcher.ui.dialogs import SettingsDialog

    path = tmp_path / "preferences.yaml"
    monkeypatch.setattr("bangumi_catcher.ui.dialogs.user_config_path", lambda: path)
    dialog = SettingsDialog(window, config=AppConfig())
    dialog.top_n.setValue(42)
    dialog.theme.setCurrentIndex(dialog.theme.findData("dark"))
    dialog._save()
    assert dialog.result() == QtWidgets.QDialog.Accepted
    restored = load_config()
    assert restored.analysis.top_n == 42
    assert restored.ui.theme == "dark"
