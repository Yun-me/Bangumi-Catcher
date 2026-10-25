"""Desktop application shell: navigation, dataset lifecycle and user actions.

The window owns exactly one :class:`~bangumi_catcher.ui.workers.TaskRunner` for
fetch/import/export work and lets :class:`~bangumi_catcher.ui.chart_page.ChartPage`
own a second one for chart rendering. Both are cancelled and awaited before the
window closes.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from .. import __version__
from ..core.config import AppConfig, load_config
from ..core.models import SUBJECT_TYPE_MAP, AnalysisReport, UserCollection, subject_type_name
from ..observability import attach_log_buffer, configure_logging
from ..services import (
    analyze_user_collection,
    default_output_path,
    export_dataset,
    export_extension,
    export_stem,
    fetch_and_analyze,
    load_collection,
    normalize_username,
    run_cancellable,
)
from ..services.cancellation import check_cancelled
from .chart_page import ChartPage
from .fetch_bar import FetchBar
from .library_page import LibraryPage
from .log_dialog import LogDialog
from .navigation import LIBRARY_INDEX, OVERVIEW_INDEX, PAGES
from .overview_page import OverviewPage
from .report_page import ReportPage
from .settings_dialog import SettingsDialog
from .sidebar import Sidebar
from .theme import Palette, build_stylesheet
from .widgets import label
from .workers import TaskRunner

logger = logging.getLogger(__name__)

APP_NAME = "Bangumi Catcher"
APP_VERSION = __version__

EXPORT_MENU: tuple[tuple[str, str], ...] = (
    ("csv", "CSV 表格"),
    ("json", "JSON 收藏快照"),
    ("report-json", "JSON 分析报告"),
    ("html", "HTML 可视化报告"),
)


class MainWindow(QtWidgets.QMainWindow):
    """The single application window."""

    def __init__(self, config: AppConfig | None = None, settings: QtCore.QSettings | None = None):
        super().__init__()
        self.config = config if config is not None else load_config()
        self.settings = settings if settings is not None else QtCore.QSettings(APP_NAME, APP_NAME)
        self.theme_preference = self._initial_theme()
        self.collection: UserCollection | None = None
        self.report: AnalysisReport | None = None
        self.last_output: Path | None = None
        self._closing = False

        self.task = TaskRunner(self)
        self.task.succeeded.connect(self._task_result)
        self.task.failed.connect(self.show_error)
        self.task.cancelled.connect(lambda: self.status_label.setText("任务已取消；保留此前的数据。"))
        self.task.progress.connect(self._on_progress)
        self.task.busy_changed.connect(self._busy_changed)

        self.setWindowTitle(APP_NAME)
        self.resize(1380, 940)
        self.setMinimumSize(900, 600)

        self._build_menu()
        self._build_ui()
        self.restore_state()
        self.apply_theme()
        self._busy_changed(False)

        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.styleHints().colorSchemeChanged.connect(self._system_theme_changed)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _initial_theme(self) -> str:
        theme = self.settings.value("theme", self.config.ui.theme, type=str)
        legacy_dark = (
            not self.settings.contains("theme")
            and self.settings.contains("dark")
            and self.config.ui.theme == "system"
        )
        if legacy_dark:
            theme = "dark" if self.settings.value("dark", False, type=bool) else "light"
        return theme

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        self.import_action = file_menu.addAction("导入收藏 JSON…", self.import_collection)
        self.import_action.setShortcut("Ctrl+O")

        self.export_actions: dict[str, QtGui.QAction] = {}
        self.export_menu = file_menu.addMenu("导出")
        for format_name, title in EXPORT_MENU:
            action = self.export_menu.addAction(title + "…")
            action.triggered.connect(lambda checked=False, kind=format_name: self.export_data(kind))
            self.export_actions[format_name] = action
        self.export_actions["csv"].setShortcut("Ctrl+S")

        file_menu.addSeparator()
        file_menu.addAction("退出", self.close).setShortcut("Ctrl+Q")

        tools = self.menuBar().addMenu("工具")
        tools.addAction("同步收藏", self.on_fetch).setShortcut("F5")
        tools.addAction("搜索收藏", self.focus_search).setShortcut("Ctrl+F")
        tools.addAction("切换亮 / 暗主题", self.toggle_theme).setShortcut("Ctrl+D")
        self.settings_action = tools.addAction("设置…", self.open_settings)
        self.settings_action.setShortcut("Ctrl+,")
        self.cache_action = tools.addAction("清空请求缓存…", self.clear_cache)
        tools.addAction("运行日志…", self.open_logs)

        self.menuBar().addMenu("帮助").addAction("关于", self.about)

    def _build_ui(self) -> None:
        root = QtWidgets.QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        shell = QtWidgets.QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.sidebar = Sidebar(PAGES)
        self.sidebar.navigate_requested.connect(self.navigate_to)
        self.sidebar.settings_requested.connect(self.open_settings)
        self.sidebar.logs_requested.connect(self.open_logs)
        sidebar_scroll = QtWidgets.QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFixedWidth(204)
        sidebar_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        sidebar_scroll.setWidget(self.sidebar)
        shell.addWidget(sidebar_scroll)

        workspace = QtWidgets.QWidget()
        body = QtWidgets.QVBoxLayout(workspace)
        body.setContentsMargins(28, 24, 28, 18)
        body.setSpacing(20)

        heading = QtWidgets.QHBoxLayout()
        titles = QtWidgets.QVBoxLayout()
        titles.setSpacing(4)
        self.breadcrumb = label("WORKSPACE / OVERVIEW", "Eyebrow")
        self.page_title = label("收藏概览", "PageTitle")
        titles.addWidget(self.breadcrumb)
        titles.addWidget(self.page_title)
        heading.addLayout(titles, 1)

        self.import_button = QtWidgets.QPushButton("导入")
        self.import_button.clicked.connect(self.import_collection)
        heading.addWidget(self.import_button)

        self.export_button = QtWidgets.QPushButton("导出报告")
        self.export_button.setMenu(self.export_menu)
        heading.addWidget(self.export_button)

        self.theme_button = QtWidgets.QPushButton()
        self.theme_button.setFixedSize(40, 40)
        self.theme_button.setToolTip("切换亮 / 暗主题  Ctrl+D")
        self.theme_button.setAccessibleName("切换亮暗主题")
        self.theme_button.clicked.connect(self.toggle_theme)
        heading.addWidget(self.theme_button)
        body.addLayout(heading)

        self.fetch_bar = FetchBar(SUBJECT_TYPE_MAP)
        self.fetch_bar.fetch_requested.connect(self.on_fetch)
        self.fetch_bar.cancel_requested.connect(self.cancel_task)
        body.addWidget(self.fetch_bar)

        self.feedback = label("", "Muted", True)
        self.feedback.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.feedback.hide()
        body.addWidget(self.feedback)

        self.pages = QtWidgets.QStackedWidget()
        self.overview = OverviewPage()
        self.library = LibraryPage()
        self.charts = ChartPage()
        self.ranking = ReportPage(ranking=True)
        self.years = ReportPage(ranking=False)
        for page in (self.overview, self.library, self.charts, self.ranking, self.years):
            self.pages.addWidget(page)

        self.overview.library_requested.connect(self.open_library)
        self.overview.import_requested.connect(self.import_collection)
        self.overview.fetch_requested.connect(self.fetch_bar.user_input.setFocus)
        self.library.export_requested.connect(lambda kind: self.export_data(kind, filtered=True))
        self.library.message.connect(self.show_message)
        self.charts.message.connect(self.show_message)
        self.charts.runner.busy_changed.connect(self._close_when_idle)
        body.addWidget(self.pages, 1)
        shell.addWidget(workspace, 1)

        self.status_label = label("准备就绪 · 输入用户名同步，或导入 JSON 离线使用。", "Muted")
        self.status_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.statusBar().addWidget(self.status_label, 1)

        self.open_output_button = QtWidgets.QPushButton("打开文件 ↗")
        self.open_output_button.setObjectName("Link")
        self.open_output_button.hide()
        self.open_output_button.clicked.connect(self.open_output)
        self.statusBar().addPermanentWidget(self.open_output_button)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedWidth(160)
        self.progress.setTextVisible(False)
        self.statusBar().addPermanentWidget(self.progress)

        self.navigate_to(OVERVIEW_INDEX)

    # ------------------------------------------------------------------
    # Navigation and theme
    # ------------------------------------------------------------------

    def navigate_to(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.sidebar.set_active(index)
        self.page_title.setText(PAGES[index].title)
        self.breadcrumb.setText(f"WORKSPACE / {PAGES[index].section}")

    def open_library(self, status: int | None = None, text: str = "") -> None:
        self.navigate_to(LIBRARY_INDEX)
        self.library.filter_by(status, text)

    def focus_search(self) -> None:
        self.navigate_to(LIBRARY_INDEX)
        self.library.search.setFocus()
        self.library.search.selectAll()

    def apply_theme(self) -> None:
        app = QtWidgets.QApplication.instance()
        self.dark = self.theme_preference == "dark" or (
            self.theme_preference == "system" and app.styleHints().colorScheme() == QtCore.Qt.ColorScheme.Dark
        )
        colors = Palette(self.dark)
        palette = app.palette()
        for role, color in [
            (QtGui.QPalette.Window, colors.bg),
            (QtGui.QPalette.Base, colors.surface),
            (QtGui.QPalette.Text, colors.text),
            (QtGui.QPalette.WindowText, colors.text),
            (QtGui.QPalette.Button, colors.surface),
            (QtGui.QPalette.ButtonText, colors.text),
            (QtGui.QPalette.Highlight, colors.accent),
            (QtGui.QPalette.HighlightedText, colors.on_accent),
        ]:
            palette.setColor(role, QtGui.QColor(color))
        app.setPalette(palette)
        app.setStyleSheet(build_stylesheet(colors))

        from .icons import icon

        self.theme_button.setIcon(icon("moon", colors.accent))
        self.import_button.setIcon(icon("import", colors.muted))
        self.export_button.setIcon(icon("export", colors.muted))
        self.sidebar.set_active(self.pages.currentIndex())
        self.charts.set_dark(self.dark)

    def toggle_theme(self) -> None:
        self.theme_preference = "light" if self.dark else "dark"
        self.settings.setValue("theme", self.theme_preference)
        self.apply_theme()

    def _system_theme_changed(self, _scheme) -> None:
        if self.theme_preference == "system":
            self.apply_theme()

    # ------------------------------------------------------------------
    # Data actions
    # ------------------------------------------------------------------

    def on_fetch(self) -> None:
        if self.task.busy or self._closing:
            return
        try:
            username = normalize_username(self.fetch_bar.username())
        except ValueError as exc:
            self.show_error(str(exc))
            self.fetch_bar.user_input.setFocus()
            return

        self.fetch_bar.set_username(username)
        config = self.config.model_copy(deep=True)
        subject_type = self.fetch_bar.subject_type()
        force_refresh = self.fetch_bar.force_refresh()

        def fetch(cancel, progress):
            collection, report = run_cancellable(
                fetch_and_analyze(
                    config,
                    username,
                    subject_type=subject_type,
                    force_refresh=force_refresh,
                    progress=lambda fraction, message: progress(fraction * 0.94, message),
                    cancel_check=cancel.is_set,
                ),
                cancel,
            )
            progress(1.0, "分析完成")
            return "data", (collection, report, "同步完成")

        self.task.start(fetch)

    def import_collection(self) -> None:
        if self.task.busy or self._closing:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "导入收藏快照",
            self.settings.value("import_dir", "", type=str),
            "收藏 JSON (*.json)",
        )
        if path:
            self.import_path(path)

    def import_path(self, path: str) -> bool:
        """Load a local snapshot in the background; returns ``False`` when busy."""
        if self.task.busy or self._closing:
            return False
        config = self.config.model_copy(deep=True)
        self.settings.setValue("import_dir", str(Path(path).parent))

        def load(cancel, progress):
            progress(0.1, "读取本地收藏快照 …")
            collection = load_collection(path)
            check_cancelled(cancel)
            progress(0.65, "分析本地收藏 …")
            report = analyze_user_collection(collection, config)
            return "data", (collection, report, "离线快照")

        return self.task.start(load)

    def set_data(self, collection: UserCollection, report: AnalysisReport, source: str) -> None:
        self.collection, self.report = collection, report
        self.fetch_bar.set_username(collection.username)
        self.fetch_bar.set_subject_type(collection.subject_type or self.config.collection.subject_type)

        self.overview.set_data(collection, report)
        self.library.set_collection(collection)
        self.charts.set_report(report)
        self.ranking.set_report(report)
        self.years.set_report(report)

        summary = (
            f"{collection.username}\n{len(collection.items):,} 部作品 · "
            f"{subject_type_name(collection.subject_type)}"
        )
        self.sidebar.set_user_summary(summary)
        self.setWindowTitle(f"{collection.username} — {APP_NAME}")
        self.show_message(
            f"{source} · {len(collection.items):,} 部作品 · "
            f"快照时间 {collection.fetched_at[:16].replace('T', ' ')}"
        )
        self.remember_user(collection.username)
        if not self.task.busy:
            self._busy_changed(False)

    def export_data(self, format_name: str, filtered: bool = False) -> None:
        if self.collection is None or self.task.busy or self._closing:
            return
        collection = self.library.filtered_collection() if filtered else self.collection
        if collection is None:
            return
        report = self.report
        extension = export_extension(format_name)
        stem = export_stem(format_name, filtered=filtered)
        folder = self.settings.value(
            "export_dir",
            str(default_output_path(self.config, collection.username, format_name).parent),
            type=str,
        )
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出筛选结果" if filtered else "导出数据",
            str(Path(folder) / f"{stem}.{extension}"),
            f"{extension.upper()} (*.{extension})",
        )
        if not path:
            return
        self.settings.setValue("export_dir", str(Path(path).parent))
        config = self.config.model_copy(deep=True)

        def export(cancel, progress):
            def update(fraction, message):
                check_cancelled(cancel)
                progress(fraction, message)

            return "export", export_dataset(collection, report, path, format_name, config, progress=update)

        self.task.start(export)

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    @QtCore.Slot(object)
    def _task_result(self, result) -> None:
        if self._closing:
            return
        kind, payload = result
        if kind == "data":
            self.set_data(*payload)
        elif kind == "export":
            self.last_output = payload
            self.open_output_button.show()
            self.show_message(f"导出完成：{payload}")
        else:
            self.show_message(str(payload))

    def _on_progress(self, fraction: float, message: str) -> None:
        self.progress.setValue(max(0, min(100, round(fraction * 100))))
        self.status_label.setText(message)

    def _busy_changed(self, busy: bool) -> None:
        self.fetch_bar.set_busy(busy)
        for widget in (self.import_button, self.sidebar.settings_button):
            widget.setEnabled(not busy)
        for action in (self.import_action, self.settings_action, self.cache_action):
            action.setEnabled(not busy)

        can_export = self.collection is not None and not busy
        self.export_button.setEnabled(can_export)
        self.library.export_button.setEnabled(can_export and self.library.proxy.rowCount() > 0)
        for action in self.export_actions.values():
            action.setEnabled(can_export)

        self.progress.setVisible(busy)
        if busy:
            self.feedback.hide()
            self.progress.setValue(0)
            self.status_label.setText("正在准备任务 …")
        self._close_when_idle()

    def cancel_task(self) -> None:
        self.task.cancel()
        self.fetch_bar.cancel_button.setEnabled(False)
        self.status_label.setText("正在取消任务 …")

    def show_error(self, message: str) -> None:
        self.feedback.setText(f"未能完成操作：{message}")
        self.feedback.show()
        self.status_label.setText("操作未完成；已有收藏数据不受影响。")

    def show_message(self, message: str) -> None:
        self.status_label.setText(message)
        self.status_label.setToolTip(message)

    def open_output(self) -> None:
        if self.last_output:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.last_output.resolve())))

    # ------------------------------------------------------------------
    # Secondary dialogs
    # ------------------------------------------------------------------

    def open_settings(self) -> None:
        if self.task.busy:
            return
        dialog = SettingsDialog(self, config=self.config, theme=self.theme_preference)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        self.config = dialog.result_config
        self.theme_preference = self.config.ui.theme
        self.settings.setValue("theme", self.theme_preference)
        configure_logging(self.config.logging.level, self.config.logging.file)
        attach_log_buffer()
        self.apply_theme()
        if self.collection is not None:
            collection, config = self.collection, self.config.model_copy(deep=True)
            self.task.start(
                lambda cancel, progress: (
                    "data",
                    (collection, analyze_user_collection(collection, config), "设置已应用"),
                )
            )

    def open_logs(self) -> None:
        LogDialog(self).exec()

    def clear_cache(self) -> None:
        if self.task.busy:
            return
        answer = QtWidgets.QMessageBox.question(
            self, "清空缓存", "清空所有请求缓存？当前收藏和已导出的文件不会删除。"
        )
        if answer != QtWidgets.QMessageBox.Yes:
            return
        directory = self.config.cache.resolved_dir()

        def clear(cancel, progress):
            from ..api import Cache

            cache = Cache(directory=directory)
            try:
                count = cache.size
                check_cancelled(cancel)
                cache.clear()
                return "message", f"已清空 {count} 条缓存"
            finally:
                cache.close()

        self.task.start(clear)

    def about(self) -> None:
        QtWidgets.QMessageBox.about(
            self,
            APP_NAME,
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "本地优先的 Bangumi 收藏工作台\n"
            "支持只读同步、离线快照、组合筛选与数据分析。\n\n"
            "本应用不会修改你的 Bangumi 收藏。",
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def remember_user(self, username: str) -> None:
        history = self.settings.value("recent_users", self.config.ui.recent_users, type=list)
        history = list(dict.fromkeys([username, *history]))[: self.config.ui.max_recent_users]
        self.settings.setValue("recent_users", history)
        self.settings.setValue("last_user", username)
        self._update_history(history)

    def _update_history(self, history: list[str]) -> None:
        self.fetch_bar.set_history(history)

    def restore_state(self) -> None:
        self.fetch_bar.set_username(self.settings.value("last_user", "", type=str))
        self._update_history(self.settings.value("recent_users", self.config.ui.recent_users, type=list))
        subject_type = self.settings.value("subject_type", self.config.collection.subject_type, type=int)
        self.fetch_bar.set_subject_type(subject_type)
        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def _close_when_idle(self, *_args: object) -> None:
        if self._closing and not self.task.busy and not self.charts.runner.busy:
            QtCore.QTimer.singleShot(0, self.close)

    def closeEvent(self, event) -> None:
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("subject_type", self.fetch_bar.subject_type())
        if self.task.busy or self.charts.runner.busy:
            self._closing = True
            self.charts.suspended = True
            self.task.cancel()
            self.charts.runner.cancel()
            self.status_label.setText("正在安全结束后台任务 …")
            event.ignore()
            return
        super().closeEvent(event)


__all__ = ["APP_NAME", "APP_VERSION", "EXPORT_MENU", "MainWindow"]
