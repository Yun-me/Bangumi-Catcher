"""End-to-end window tests running with the offscreen Qt platform."""

from __future__ import annotations

import threading

import pytest
from PySide6 import QtCore, QtTest, QtWidgets

from bangumi_catcher.core.config import AppConfig, load_config
from bangumi_catcher.reporting import collection_to_json
from bangumi_catcher.services.fetch import analyze_user_collection
from bangumi_catcher.ui.settings_dialog import SettingsDialog
from tests.helpers import run_python
from tests.ui.conftest import wait_until


def test_desktop_import_does_not_load_plotting_runtime():
    result = run_python(
        "import sys; import bangumi_catcher.ui.main_window; "
        "assert 'matplotlib' not in sys.modules, sorted(sys.modules)"
    )
    assert result.returncode == 0, result.stderr


def test_offline_import_repeated_load_and_filtered_export(window, tmp_path, sample_collection):
    source = tmp_path / "collection.json"
    collection_to_json(sample_collection, source)
    for _ in range(2):
        assert window.import_path(str(source))
        wait_until(lambda: not window.task.busy)
        assert window.collection is not None
    assert window.report.total_items == 5
    assert window.settings.value("recent_users", type=list) == ["tester"]
    assert window.export_button.isEnabled()

    window.open_library(2)
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
    window.set_data(sample_collection, analyze_user_collection(sample_collection, AppConfig()), "测试")
    source = tmp_path / "broken.json"
    source.write_text("not JSON", encoding="utf-8")
    window.import_path(str(source))
    wait_until(lambda: not window.task.busy)
    assert window.collection is sample_collection
    assert window.feedback.isVisible()
    assert window.fetch_bar.fetch_button.isEnabled()


def test_charts_are_lazy_and_cached(window, sample_collection, monkeypatch, png):
    calls: list[tuple[str, bool]] = []

    def render(report, key, dark=False):
        calls.append((key, dark))
        return png

    monkeypatch.setattr("bangumi_catcher.charts.render.render_chart", render)
    window.set_data(sample_collection, analyze_user_collection(sample_collection, AppConfig()), "测试")
    QtTest.QTest.qWait(30)
    assert not calls

    window.navigate_to(2)
    wait_until(lambda: window.charts.key in window.charts.cache and not window.charts.runner.busy)
    assert not window.charts.image.pixmap.isNull()
    assert len(calls) == 1

    window.navigate_to(0)
    window.navigate_to(2)
    QtTest.QTest.qWait(20)
    assert len(calls) == 1

    window.toggle_theme()
    wait_until(lambda: window.charts.key in window.charts.cache and not window.charts.runner.busy)
    assert calls[-1][1] is True
    assert len(calls) == 2


@pytest.mark.slow
def test_real_background_chart_is_displayed(window, sample_collection):
    window.set_data(sample_collection, analyze_user_collection(sample_collection, AppConfig()), "测试")
    loop = QtCore.QEventLoop()
    poll = QtCore.QTimer()
    deadline = QtCore.QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(loop.quit)
    ticks: list[bool] = []

    def check() -> None:
        ticks.append(True)
        if window.charts.key in window.charts.cache and not window.charts.runner.busy:
            loop.quit()

    poll.timeout.connect(check)
    poll.start(20)
    deadline.start(20000)
    window.navigate_to(2)
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
    window.focus_search()
    assert window.pages.currentWidget() is window.library
    assert window.library.search.hasFocus()


def test_navigation_updates_sidebar_and_breadcrumb(window):
    window.navigate_to(1)
    assert window.pages.currentWidget() is window.library
    assert window.sidebar.nav_buttons[1].isChecked()
    assert window.breadcrumb.text() == "WORKSPACE / LIBRARY"
    assert window.page_title.text() == "我的收藏"


def test_fetch_bar_history_and_subject_type(window):
    window.remember_user("alice")
    assert window.settings.value("last_user", type=str) == "alice"
    actions = [action.text() for action in window.fetch_bar.history_menu.actions()]
    assert actions == ["alice"]

    window.fetch_bar.set_username("alice")
    assert window.fetch_bar.username() == "alice"

    window.fetch_bar.set_subject_type(1)
    assert window.fetch_bar.subject_type() == 1
    window.fetch_bar.set_username("bob")
    assert window.fetch_bar.username() == "bob"


def test_theme_toggle_persists(window):
    assert window.dark is False
    window.toggle_theme()
    assert window.dark is True
    assert window.settings.value("theme", type=str) == "dark"
    window.toggle_theme()
    assert window.dark is False
    assert window.settings.value("theme", type=str) == "light"


def test_stale_chart_failure_does_not_poison_new_selection(window, sample_collection, monkeypatch, png):
    entered, release = threading.Event(), threading.Event()

    def render(report, key, dark=False):
        if key == "rating_distribution":
            entered.set()
            release.wait(3)
            raise ValueError("first chart failed")
        return png

    monkeypatch.setattr("bangumi_catcher.charts.render.render_chart", render)
    window.set_data(sample_collection, analyze_user_collection(sample_collection, AppConfig()), "测试")
    window.navigate_to(2)
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


def test_settings_save_to_user_directory(window, tmp_path, monkeypatch):
    path = tmp_path / "preferences.yaml"
    monkeypatch.setattr("bangumi_catcher.ui.settings_dialog.user_config_path", lambda: path)
    dialog = SettingsDialog(window, config=AppConfig())
    dialog.top_n.setValue(42)
    dialog.theme.setCurrentIndex(dialog.theme.findData("dark"))
    dialog.log_level.setCurrentIndex(dialog.log_level.findData("DEBUG"))
    dialog._save()
    assert dialog.result() == QtWidgets.QDialog.Accepted

    restored = load_config()
    assert restored.analysis.top_n == 42
    assert restored.ui.theme == "dark"
    assert restored.logging.level == "DEBUG"
