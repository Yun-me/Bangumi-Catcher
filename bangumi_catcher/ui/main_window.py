"""Desktop shell: navigation, dataset lifecycle and user actions."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from .. import __version__
from ..core.config import AppConfig, load_config
from ..core.models import AnalysisReport, UserCollection
from ..services.export_service import export_dataset
from ..services.fetch_service import analyze_user_collection, fetch_and_analyze
from ..services.library_service import SUBJECT_TYPES, load_collection, normalize_username
from ..services.task_service import check_cancelled, run_cancellable
from .chart_page import ChartPage
from .dialogs import LogDialog, SettingsDialog
from .icons import icon
from .library_page import LibraryPage
from .overview_page import OverviewPage
from .report_page import ReportPage
from .theme import Palette, build_stylesheet
from .widgets import Card, label
from .workers import TaskRunner

APP_NAME = "Bangumi Catcher"
APP_VERSION = __version__
PAGES = [("收藏概览", "OVERVIEW", "home"), ("我的收藏", "LIBRARY", "library"),
         ("数据洞察", "INSIGHTS", "chart"), ("高分排行", "FAVORITES", "star"),
         ("年度回顾", "TIMELINE", "calendar")]


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config: AppConfig | None = None, settings: QtCore.QSettings | None = None):
        super().__init__()
        self.config = config if config is not None else load_config()
        self.settings = settings if settings is not None else QtCore.QSettings(APP_NAME, APP_NAME)
        self.theme_preference = self.settings.value("theme", self.config.ui.theme, type=str)
        if not self.settings.contains("theme") and self.settings.contains("dark") and self.config.ui.theme == "system":
            self.theme_preference = "dark" if self.settings.value("dark", False, type=bool) else "light"
        self.collection: UserCollection | None = None
        self.report: AnalysisReport | None = None
        self.last_output: Path | None = None
        self._closing = False
        self.task = TaskRunner(self)
        self.task.succeeded.connect(self._task_result)
        self.task.failed.connect(self._show_error)
        self.task.cancelled.connect(lambda: self.status_label.setText("任务已取消；保留此前的数据。"))
        self.task.progress.connect(self._on_progress)
        self.task.busy_changed.connect(self._busy_changed)
        self.setWindowTitle(APP_NAME)
        self.resize(1380, 940)
        self.setMinimumSize(900, 600)
        self._build_menu()
        self._build_ui()
        self._restore_state()
        self._apply_theme()
        self._busy_changed(False)
        QtWidgets.QApplication.instance().styleHints().colorSchemeChanged.connect(self._system_theme_changed)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        self.import_action = file_menu.addAction("导入收藏 JSON…", self._import_collection)
        self.import_action.setShortcut("Ctrl+O")
        self.export_actions = {}
        self.export_menu = file_menu.addMenu("导出")
        for format_name, title in [("csv", "CSV 表格"), ("json", "JSON 收藏快照"),
                                   ("report-json", "JSON 分析报告"), ("html", "HTML 可视化报告")]:
            action = self.export_menu.addAction(title + "…")
            action.triggered.connect(lambda checked=False, kind=format_name: self._export(kind))
            self.export_actions[format_name] = action
        self.export_actions["csv"].setShortcut("Ctrl+S")
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close).setShortcut("Ctrl+Q")
        tools = self.menuBar().addMenu("工具")
        tools.addAction("同步收藏", self._on_fetch).setShortcut("F5")
        tools.addAction("搜索收藏", self._focus_search).setShortcut("Ctrl+F")
        tools.addAction("切换亮 / 暗主题", self._toggle_theme).setShortcut("Ctrl+D")
        self.settings_action = tools.addAction("设置…", self._open_settings)
        self.settings_action.setShortcut("Ctrl+,")
        self.cache_action = tools.addAction("清空请求缓存…", self._clear_cache)
        tools.addAction("运行日志…", self._open_logs)
        self.menuBar().addMenu("帮助").addAction("关于", self._about)

    def _build_ui(self) -> None:
        root = QtWidgets.QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        shell = QtWidgets.QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setMinimumWidth(180)
        side = QtWidgets.QVBoxLayout(sidebar)
        side.setContentsMargins(18, 30, 18, 22)
        side.setSpacing(8)
        side.addWidget(label("BANGUMI", "Brand"))
        side.addWidget(label("C A T C H E R", "SideMuted"))
        side.addSpacing(34)
        side.addWidget(label("个人工作台", "SideMuted"))
        side.addSpacing(4)
        self.nav_buttons = []
        self.nav_group = QtWidgets.QButtonGroup(self)
        for index, (title, _name, glyph) in enumerate(PAGES):
            button = QtWidgets.QPushButton(f"  {title}")
            button.setCheckable(True)
            button.setIconSize(QtCore.QSize(19, 19))
            button.setIcon(icon(glyph, "#C3D8CD"))
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
            side.addWidget(button)
        self.nav_group.idClicked.connect(self._navigate)
        side.addStretch()
        self.side_user = label("你的收藏，你的节奏。", "SideMuted", True)
        side.addWidget(self.side_user)
        side.addSpacing(18)
        self.settings_button = QtWidgets.QPushButton("  偏好设置")
        self.settings_button.setIcon(icon("settings", "#C3D8CD"))
        self.settings_button.clicked.connect(self._open_settings)
        side.addWidget(self.settings_button)
        logs_button = QtWidgets.QPushButton("  运行日志")
        logs_button.setIcon(icon("log", "#C3D8CD"))
        logs_button.clicked.connect(self._open_logs)
        side.addWidget(logs_button)
        side.addSpacing(10)
        side.addWidget(label(f"v{APP_VERSION}  ·  本地优先 / 只读分析", "SideMuted"))
        sidebar_scroll = QtWidgets.QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFixedWidth(204)
        sidebar_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        sidebar_scroll.setWidget(sidebar)
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
        self.import_button.clicked.connect(self._import_collection)
        heading.addWidget(self.import_button)
        self.export_button = QtWidgets.QPushButton("导出报告")
        self.export_button.setMenu(self.export_menu)
        heading.addWidget(self.export_button)
        self.theme_button = QtWidgets.QPushButton()
        self.theme_button.setFixedSize(40, 40)
        self.theme_button.setToolTip("切换亮 / 暗主题  Ctrl+D")
        self.theme_button.setAccessibleName("切换亮暗主题")
        self.theme_button.clicked.connect(self._toggle_theme)
        heading.addWidget(self.theme_button)
        body.addLayout(heading)

        fetch_card = Card()
        fetch_card.body.setContentsMargins(14, 12, 14, 12)
        fetch_row = QtWidgets.QHBoxLayout()
        fetch_row.setSpacing(10)
        self.user_input = QtWidgets.QLineEdit()
        self.user_input.setPlaceholderText("用户名 / UID / Bangumi 用户主页链接")
        self.user_input.setAccessibleName("Bangumi 用户")
        self.user_input.setClearButtonEnabled(True)
        self.user_input.returnPressed.connect(self._on_fetch)
        fetch_row.addWidget(self.user_input, 1)
        self.history_button = QtWidgets.QPushButton("最近")
        self.history_menu = QtWidgets.QMenu(self.history_button)
        self.history_button.setMenu(self.history_menu)
        fetch_row.addWidget(self.history_button)
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.setAccessibleName("收藏分类")
        for value, title in SUBJECT_TYPES.items():
            self.type_combo.addItem(title, value)
        fetch_row.addWidget(self.type_combo)
        self.refresh_check = QtWidgets.QCheckBox("跳过缓存")
        self.refresh_check.setToolTip("忽略收藏缓存，重新从 Bangumi 同步。")
        fetch_row.addWidget(self.refresh_check)
        self.fetch_button = QtWidgets.QPushButton("同步收藏")
        self.fetch_button.setObjectName("Primary")
        self.fetch_button.clicked.connect(self._on_fetch)
        fetch_row.addWidget(self.fetch_button)
        self.cancel_button = QtWidgets.QPushButton("取消任务")
        self.cancel_button.clicked.connect(self._cancel)
        fetch_row.addWidget(self.cancel_button)
        fetch_card.body.addLayout(fetch_row)
        body.addWidget(fetch_card)
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
        self.overview.library_requested.connect(self._open_library)
        self.overview.import_requested.connect(self._import_collection)
        self.overview.fetch_requested.connect(self.user_input.setFocus)
        self.library.export_requested.connect(lambda kind: self._export(kind, filtered=True))
        self.library.message.connect(self._message)
        self.charts.message.connect(self._message)
        self.charts.runner.busy_changed.connect(self._finish_close_if_idle)
        body.addWidget(self.pages, 1)
        shell.addWidget(workspace, 1)

        self.status_label = label("准备就绪 · 输入用户名同步，或导入 JSON 离线使用。", "Muted")
        self.status_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.statusBar().addWidget(self.status_label, 1)
        self.open_output_button = QtWidgets.QPushButton("打开文件 ↗")
        self.open_output_button.setObjectName("Link")
        self.open_output_button.hide()
        self.open_output_button.clicked.connect(self._open_output)
        self.statusBar().addPermanentWidget(self.open_output_button)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedWidth(160)
        self.progress.setTextVisible(False)
        self.statusBar().addPermanentWidget(self.progress)
        self._navigate(0)

    def _navigate(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        self.page_title.setText(PAGES[index][0])
        self.breadcrumb.setText(f"WORKSPACE / {PAGES[index][1]}")
        for position, button in enumerate(self.nav_buttons):
            button.setIcon(icon(PAGES[position][2], "#173C31" if position == index else "#C3D8CD"))

    def _open_library(self, status=None, text: str = "") -> None:
        self._navigate(1)
        self.library.filter_by(status, text)

    def _focus_search(self) -> None:
        self._navigate(1)
        self.library.search.setFocus()
        self.library.search.selectAll()

    def _apply_theme(self) -> None:
        app = QtWidgets.QApplication.instance()
        self.dark = self.theme_preference == "dark" or (
            self.theme_preference == "system" and app.styleHints().colorScheme() == QtCore.Qt.ColorScheme.Dark)
        colors = Palette(self.dark)
        palette = app.palette()
        for role, color in [(QtGui.QPalette.Window, colors.bg), (QtGui.QPalette.Base, colors.surface),
                            (QtGui.QPalette.Text, colors.text), (QtGui.QPalette.WindowText, colors.text),
                            (QtGui.QPalette.Button, colors.surface), (QtGui.QPalette.ButtonText, colors.text),
                            (QtGui.QPalette.Highlight, colors.accent), (QtGui.QPalette.HighlightedText, colors.on_accent)]:
            palette.setColor(role, QtGui.QColor(color))
        app.setPalette(palette)
        app.setStyleSheet(build_stylesheet(colors))
        self.theme_button.setIcon(icon("moon", colors.accent))
        self.import_button.setIcon(icon("import", colors.muted))
        self.export_button.setIcon(icon("export", colors.muted))
        self.charts.set_dark(self.dark)

    def _toggle_theme(self) -> None:
        self.theme_preference = "light" if self.dark else "dark"
        self.settings.setValue("theme", self.theme_preference)
        self._apply_theme()

    def _system_theme_changed(self, _scheme) -> None:
        if self.theme_preference == "system":
            self._apply_theme()

    def _on_fetch(self) -> None:
        if self.task.busy or self._closing:
            return
        try:
            username = normalize_username(self.user_input.text())
        except ValueError as exc:
            self._show_error(str(exc))
            self.user_input.setFocus()
            return
        self.user_input.setText(username)
        config = self.config.model_copy(deep=True)
        subject_type = self.type_combo.currentData()
        force_refresh = self.refresh_check.isChecked()

        def fetch(cancel, progress):
            collection, report = run_cancellable(fetch_and_analyze(
                config, username, subject_type=subject_type, force_refresh=force_refresh,
                progress=lambda fraction, message: progress(fraction * 0.94, message),
                cancel_check=cancel.is_set,
            ), cancel)
            progress(1.0, "分析完成")
            return "data", (collection, report, "同步完成")

        self.task.start(fetch)

    def _import_collection(self) -> None:
        if self.task.busy or self._closing:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "导入收藏快照", self.settings.value("import_dir", "", type=str), "收藏 JSON (*.json)")
        if path:
            self.import_path(path)

    def import_path(self, path: str) -> bool:
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

    def _set_data(self, collection: UserCollection, report: AnalysisReport, source: str) -> None:
        self.collection, self.report = collection, report
        self.user_input.setText(collection.username)
        if collection.subject_type in SUBJECT_TYPES:
            self.type_combo.setCurrentIndex(self.type_combo.findData(collection.subject_type))
        self.overview.set_data(collection, report)
        self.library.set_collection(collection)
        self.charts.set_report(report)
        self.ranking.set_report(report)
        self.years.set_report(report)
        self.side_user.setText(f"{collection.username}\n{len(collection.items):,} 部作品 · {SUBJECT_TYPES.get(collection.subject_type, '未标注分类')}")
        self.setWindowTitle(f"{collection.username} — {APP_NAME}")
        self._message(f"{source} · {len(collection.items):,} 部作品 · 快照时间 {collection.fetched_at[:16].replace('T', ' ')}")
        self._remember_user(collection.username)

    def _export(self, format_name: str, filtered: bool = False) -> None:
        if self.collection is None or self.task.busy or self._closing:
            return
        collection = self.library.filtered_collection() if filtered else self.collection
        report = self.report
        extension = "json" if format_name == "report-json" else format_name
        stem = "filtered" if filtered else "report" if format_name in {"html", "report-json"} else "collection"
        folder = self.settings.value("export_dir", self.config.export.output_dir, type=str)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出筛选结果" if filtered else "导出数据", str(Path(folder) / f"{stem}.{extension}"),
            f"{extension.upper()} (*.{extension})")
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

    @QtCore.Slot(object)
    def _task_result(self, result) -> None:
        if self._closing:
            return
        kind, payload = result
        if kind == "data":
            self._set_data(*payload)
        elif kind == "export":
            self.last_output = payload
            self.open_output_button.show()
            self._message(f"导出完成：{payload}")
        else:
            self._message(str(payload))

    def _on_progress(self, fraction: float, message: str) -> None:
        self.progress.setValue(max(0, min(100, round(fraction * 100))))
        self.status_label.setText(message)

    def _busy_changed(self, busy: bool) -> None:
        for widget in (self.fetch_button, self.user_input, self.history_button, self.type_combo,
                       self.refresh_check, self.import_button, self.settings_button):
            widget.setEnabled(not busy)
        for action in (self.import_action, self.settings_action, self.cache_action):
            action.setEnabled(not busy)
        can_export = self.collection is not None and not busy
        self.export_button.setEnabled(can_export)
        self.library.export_button.setEnabled(can_export and self.library.proxy.rowCount() > 0)
        for action in self.export_actions.values():
            action.setEnabled(can_export)
        self.cancel_button.setVisible(busy)
        self.fetch_button.setVisible(not busy)
        self.cancel_button.setEnabled(True)
        self.progress.setVisible(busy)
        if busy:
            self.feedback.hide()
            self.progress.setValue(0)
            self.status_label.setText("正在准备任务 …")
        self._finish_close_if_idle()

    def _cancel(self) -> None:
        self.task.cancel()
        self.cancel_button.setEnabled(False)
        self.status_label.setText("正在取消任务 …")

    def _show_error(self, message: str) -> None:
        self.feedback.setText(f"未能完成操作：{message}")
        self.feedback.show()
        self.status_label.setText("操作未完成；已有收藏数据不受影响。")

    def _message(self, message: str) -> None:
        self.status_label.setText(message)
        self.status_label.setToolTip(message)

    def _open_output(self) -> None:
        if self.last_output:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.last_output.resolve())))

    def _open_settings(self) -> None:
        if self.task.busy:
            return
        dialog = SettingsDialog(self, config=self.config, theme=self.theme_preference)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self.config = dialog.result_config
            self.theme_preference = self.config.ui.theme
            self.settings.setValue("theme", self.theme_preference)
            self._apply_theme()
            if self.collection is not None:
                collection, config = self.collection, self.config.model_copy(deep=True)
                self.task.start(lambda cancel, progress: (
                    "data", (collection, analyze_user_collection(collection, config), "设置已应用")))

    def _open_logs(self) -> None:
        LogDialog(self).exec()

    def _clear_cache(self) -> None:
        if self.task.busy:
            return
        if QtWidgets.QMessageBox.question(self, "清空缓存", "清空所有请求缓存？当前收藏和已导出的文件不会删除。") != QtWidgets.QMessageBox.Yes:
            return
        directory = self.config.cache.dir or None

        def clear(cancel, progress):
            from ..core.cache import Cache

            cache = Cache(directory=directory)
            try:
                count = cache.size
                check_cancelled(cancel)
                cache.clear()
                return "message", f"已清空 {count} 条缓存"
            finally:
                cache.close()

        self.task.start(clear)

    def _about(self) -> None:
        QtWidgets.QMessageBox.about(self, APP_NAME, f"{APP_NAME} v{APP_VERSION}\n\n"
                                   "本地优先的 Bangumi 收藏工作台\n"
                                   "支持只读同步、离线快照、组合筛选与数据分析。\n\n"
                                   "本应用不会修改你的 Bangumi 收藏。")

    def _remember_user(self, username: str) -> None:
        history = self.settings.value("recent_users", self.config.ui.recent_users, type=list)
        history = list(dict.fromkeys([username, *history]))[:self.config.ui.max_recent_users]
        self.settings.setValue("recent_users", history)
        self.settings.setValue("last_user", username)
        self._update_history(history)

    def _update_history(self, history: list[str]) -> None:
        self.history_menu.clear()
        for username in history:
            self.history_menu.addAction(username, lambda value=username: self.user_input.setText(value))
        if not history:
            self.history_menu.addAction("还没有历史用户").setEnabled(False)
        completer = QtWidgets.QCompleter(history, self.user_input)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.user_input.setCompleter(completer)

    def _restore_state(self) -> None:
        self.user_input.setText(self.settings.value("last_user", "", type=str))
        self._update_history(self.settings.value("recent_users", self.config.ui.recent_users, type=list))
        subject_type = self.settings.value("subject_type", self.config.collection.subject_type, type=int)
        self.type_combo.setCurrentIndex(max(0, self.type_combo.findData(subject_type)))
        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    def _finish_close_if_idle(self, *_args) -> None:
        if self._closing and not self.task.busy and not self.charts.runner.busy:
            QtCore.QTimer.singleShot(0, self.close)

    def closeEvent(self, event) -> None:
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("subject_type", self.type_combo.currentData())
        if self.task.busy or self.charts.runner.busy:
            self._closing = True
            self.charts.suspended = True
            self.task.cancel()
            self.charts.runner.cancel()
            self.status_label.setText("正在安全结束后台任务 …")
            event.ignore()
            return
        super().closeEvent(event)
