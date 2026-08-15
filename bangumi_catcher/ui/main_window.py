"""Bangumi Catcher —— PySide6 (Qt) 现代化桌面主窗口.

v2.0 将主窗口从单一 gui.py 拆出：后台任务、可复用组件、对话框均独立成模块。
"""

from __future__ import annotations

import webbrowser
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from .. import __version__
from ..core.config import load_config
from ..core.export import collection_to_csv, collection_to_json, report_to_json
from ..core.models import AnalysisReport, UserCollection
from .dialogs import LogDialog, SettingsDialog
from .flowlayout import FlowLayout
from .theme import Palette, build_stylesheet
from .visualizer import CHART_TITLES, build_figures, render_all
from .widgets import ChartCard, SearchProxy, StatCard, progress_label
from .workers import FetchWorker

APP_NAME = "Bangumi Catcher"
APP_VERSION = __version__
TYPE_MAP = {"动画": 2, "书籍": 1, "音乐": 3, "游戏": 4, "三次元": 6}


# ============================================================ 主窗口
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QtCore.QSettings(APP_NAME, APP_NAME)
        theme_pref = load_config().ui.theme
        if theme_pref == "dark":
            self.dark = True
        elif theme_pref == "light":
            self.dark = False
        else:
            self.dark = self.settings.value("dark", False, type=bool)
        self.collection: UserCollection | None = None
        self.report: AnalysisReport | None = None
        self._charts_uri: dict[str, str] = {}
        self._thread: QtCore.QThread | None = None
        self._worker: FetchWorker | None = None

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1240, 840)
        self.setMinimumSize(900, 600)

        self._build_menu()
        self._build_ui()
        self._apply_theme()
        self._restore_state()

    # -------------------------------------------------- 菜单
    def _build_menu(self):
        bar = self.menuBar()
        m_file = bar.addMenu("文件")
        self.act_csv = m_file.addAction("导出 CSV…", self._export_csv)
        self.act_json = m_file.addAction("导出 JSON…", self._export_json)
        self.act_report_json = m_file.addAction("导出报告 JSON…", self._export_report_json)
        self.act_html = m_file.addAction("导出 HTML 报告…", self._export_html)
        self.act_csv.setShortcut("Ctrl+S")
        m_file.addSeparator()
        m_file.addAction("退出", self.close)

        m_tools = bar.addMenu("工具")
        m_tools.addAction("查看 / 清空缓存", self._clear_cache)
        m_tools.addAction("设置…", self._open_settings)
        m_tools.addAction("运行日志…", self._open_logs)
        self.act_theme = m_tools.addAction("切换 暗/亮 主题", self._toggle_theme)
        self.act_theme.setShortcut("Ctrl+D")

        m_help = bar.addMenu("帮助")
        m_help.addAction("关于", self._about)

        for a in (self.act_csv, self.act_json, self.act_report_json, self.act_html):
            a.setEnabled(False)

    # -------------------------------------------------- UI
    def _build_ui(self):
        root = QtWidgets.QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QtWidgets.QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- 顶部栏 ----
        header = QtWidgets.QFrame()
        header.setObjectName("Header")
        header.setMinimumHeight(64)
        hl = QtWidgets.QHBoxLayout(header)
        hl.setContentsMargins(20, 8, 20, 8)
        hl.setSpacing(10)

        title = QtWidgets.QLabel("Bangumi Catcher")
        title.setObjectName("AppTitle")
        title.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        hl.addWidget(title)
        hl.addSpacing(12)

        self.user_input = QtWidgets.QLineEdit()
        self.user_input.setPlaceholderText("输入 Bangumi 用户 ID / 用户名")
        self.user_input.setMinimumWidth(180)
        self.user_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.user_input.returnPressed.connect(self._on_fetch)
        hl.addWidget(self.user_input, 1)

        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(list(TYPE_MAP.keys()))
        self.type_combo.setMinimumWidth(86)
        hl.addWidget(self.type_combo)

        self.refresh_check = QtWidgets.QCheckBox("强制刷新")
        hl.addWidget(self.refresh_check)

        self.fetch_btn = QtWidgets.QPushButton("开始抓取")
        self.fetch_btn.setObjectName("Primary")
        self.fetch_btn.clicked.connect(self._on_fetch)
        hl.addWidget(self.fetch_btn)

        self.cancel_btn = QtWidgets.QPushButton("取消")
        self.cancel_btn.setObjectName("Ghost")
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.cancel_btn.setVisible(False)
        hl.addWidget(self.cancel_btn)

        outer.addWidget(header)

        # ---- 标签页 ----
        self.tabs = QtWidgets.QTabWidget()
        outer.addWidget(self.tabs, 1)
        self._build_tab_overview()
        self._build_tab_charts()
        self._build_tab_collection()
        self._build_tab_ranking()
        self._build_tab_years()
        self._set_empty_state(True)

        # ---- 状态栏 ----
        sb = self.statusBar()
        self.status_label = QtWidgets.QLabel("就绪")
        self.status_label.setObjectName("Muted")
        self.progress = QtWidgets.QProgressBar()
        self.progress.setFixedWidth(220)
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        sb.addWidget(self.status_label, 1)
        sb.addPermanentWidget(self.progress)

    def _scroll_with_flow(self):
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        inner.setObjectName("FlowPage")
        flow = FlowLayout(inner, margin=18, h_spacing=16, v_spacing=16)
        scroll.setWidget(inner)
        return scroll, flow

    def _build_tab_overview(self):
        self.overview_scroll, self.overview_flow = self._scroll_with_flow()
        self.tabs.addTab(self.overview_scroll, "概览")

    def _build_tab_charts(self):
        self.charts_scroll, self.charts_flow = self._scroll_with_flow()
        self.tabs.addTab(self.charts_scroll, "图表")

    def _build_tab_collection(self):
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)
        v.setContentsMargins(18, 14, 18, 14)
        v.setSpacing(10)

        bar = QtWidgets.QHBoxLayout()
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setObjectName("SearchBox")
        self.search_box.setPlaceholderText("搜索作品名 / 标签 / 评价")
        self.search_box.textChanged.connect(self._on_search)
        bar.addWidget(self.search_box, 1)
        self.status_filter = QtWidgets.QComboBox()
        self.status_filter.addItem("全部状态", "")
        for label in ("想看", "看过", "在看", "搁置", "抛弃"):
            self.status_filter.addItem(label, label)
        self.status_filter.currentIndexChanged.connect(self._on_status_filter)
        bar.addWidget(self.status_filter)
        self.count_label = QtWidgets.QLabel("")
        self.count_label.setObjectName("Muted")
        bar.addWidget(self.count_label)
        v.addLayout(bar)

        self.table = QtWidgets.QTableView()
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self._open_subject)
        self.model = QtGui.QStandardItemModel()
        self.proxy = SearchProxy(self)
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_table_menu)
        v.addWidget(self.table, 1)
        self.tabs.addTab(page, "收藏总表")

    def _build_tab_ranking(self):
        self.ranking_table = QtWidgets.QTableWidget()
        self.ranking_table.setAlternatingRowColors(True)
        self.ranking_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.ranking_table.verticalHeader().setVisible(False)
        wrap = QtWidgets.QWidget()
        wl = QtWidgets.QVBoxLayout(wrap)
        wl.setContentsMargins(18, 14, 18, 14)
        wl.addWidget(self.ranking_table)
        self.tabs.addTab(wrap, "排行")

    def _build_tab_years(self):
        self.years_table = QtWidgets.QTableWidget()
        self.years_table.setAlternatingRowColors(True)
        self.years_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.years_table.verticalHeader().setVisible(False)
        wrap = QtWidgets.QWidget()
        wl = QtWidgets.QVBoxLayout(wrap)
        wl.setContentsMargins(18, 14, 18, 14)
        wl.addWidget(self.years_table)
        self.tabs.addTab(wrap, "年度")

    # -------------------------------------------------- 主题
    def _apply_theme(self):
        self.palette_ = Palette(self.dark)
        QtWidgets.QApplication.instance().setStyleSheet(build_stylesheet(self.palette_))

    def _toggle_theme(self):
        self.dark = not self.dark
        self.settings.setValue("dark", self.dark)
        self._apply_theme()
        if self.report is not None:
            self._render_charts()   # 重建图表以适配主题

    # -------------------------------------------------- 抓取流程
    def _on_fetch(self):
        username = self.user_input.text().strip()
        if not username:
            QtWidgets.QMessageBox.warning(self, "提示", "请输入 Bangumi 用户 ID")
            return
        if self._thread and self._thread.isRunning():
            return
        self.settings.setValue("last_user", username)
        subject_type = TYPE_MAP.get(self.type_combo.currentText(), 2)

        self.fetch_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress.setVisible(True)
        self.progress.setValue(0)

        self._thread = QtCore.QThread()
        self._worker = FetchWorker(username, subject_type, self.refresh_check.isChecked())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        # 收尾链：停事件循环 → 删 worker → 删 thread → 清引用，
        # 杜绝"线程仍在运行就被销毁"以及反复抓取导致的对象堆积。
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_thread_done)
        self._thread.start()

    def _on_thread_done(self):
        self._thread = None
        self._worker = None

    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()
            self.status_label.setText("正在取消 …")

    @QtCore.Slot(float, str)
    def _on_progress(self, frac, msg):
        self.progress.setValue(int(frac * 100))
        self.status_label.setText(msg)

    @QtCore.Slot(object, object)
    def _on_finished(self, collection, report):
        self.collection = collection
        self.report = report
        self._charts_uri = {}  # 重要：新报告必须丢弃旧的 HTML 图表缓存
        self.search_box.clear()
        self.status_filter.setCurrentIndex(0)
        self._reset_controls()
        self.status_label.setText(
            f"{report.total_items} 条 · 均分 {report.overall_avg_rating} · "
            f"完成率 {report.avg_completion}%")
        for a in (self.act_csv, self.act_json, self.act_report_json, self.act_html):
            a.setEnabled(True)
        self._set_empty_state(False)
        self._render_overview()
        self._render_charts()
        self._render_collection()
        self._render_ranking()
        self._render_years()

    @QtCore.Slot(str)
    def _on_failed(self, msg):
        self._reset_controls()
        self.status_label.setText(f"失败：{msg}")
        if msg != "已取消":
            QtWidgets.QMessageBox.critical(self, "抓取失败", msg)

    def _reset_controls(self):
        self.fetch_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.progress.setVisible(False)
        self.progress.setValue(0)

    # -------------------------------------------------- 渲染
    def _clear_flow(self, flow):
        while flow.count():
            item = flow.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def _set_empty_state(self, empty: bool):
        if empty and self.overview_flow.count() == 0:
            tip = QtWidgets.QLabel("输入 Bangumi 用户 ID，点击「开始抓取」开始")
            tip.setObjectName("Empty")
            self.overview_flow.addWidget(tip)

    def _render_overview(self):
        self._clear_flow(self.overview_flow)
        r = self.report
        cards = [
            ("总收藏", r.total_items),
            ("平均评分", f"{r.overall_avg_rating:.1f}"),
            ("完成率", f"{r.avg_completion:.0f}%"),
            ("覆盖年份", len(r.by_year)),
        ]
        for tn, cnt in r.type_counts.items():
            cards.append((tn, cnt))
        for label, val in cards:
            self.overview_flow.addWidget(StatCard(val, label))

    def _render_charts(self):
        self._clear_flow(self.charts_flow)
        figs = build_figures(self.report, dark=self.dark)
        self._figs = figs  # keep refs alive
        for key, title in CHART_TITLES.items():
            if key in figs:
                self.charts_flow.addWidget(ChartCard(title, figs[key]))

    def _render_collection(self):
        self.model.clear()
        headers = ["作品", "年份", "状态", "我的评分", "全站均分", "进度", "标签"]
        self.model.setHorizontalHeaderLabels(headers)
        for it in self.collection.items:
            name = QtGui.QStandardItem(it.subject_name)
            # 预拼可搜索文本：作品名 + 标签 + 短评（短评未单独成列，借此也可被搜索到）
            name.setData(
                " ".join(filter(None, [it.subject_name, " ".join(it.tags), it.comment])),
                QtCore.Qt.UserRole,
            )
            year = QtGui.QStandardItem()
            year.setData(it.subject_year or 0, QtCore.Qt.DisplayRole)
            year.setTextAlignment(QtCore.Qt.AlignCenter)
            status = QtGui.QStandardItem(it.collection_type_name)
            status.setData(it.collection_type_name, QtCore.Qt.UserRole)
            status.setTextAlignment(QtCore.Qt.AlignCenter)
            myrate = QtGui.QStandardItem()
            myrate.setData(it.rate or 0, QtCore.Qt.DisplayRole)
            myrate.setTextAlignment(QtCore.Qt.AlignCenter)
            bgm = QtGui.QStandardItem()
            bgm.setData(round(it.subject_score, 1), QtCore.Qt.DisplayRole)
            bgm.setTextAlignment(QtCore.Qt.AlignCenter)
            prog = QtGui.QStandardItem(progress_label(it))
            prog.setTextAlignment(QtCore.Qt.AlignCenter)
            tags = QtGui.QStandardItem("、".join(it.tags[:5]))
            self.model.appendRow([name, year, status, myrate, bgm, prog, tags])
        self.table.setColumnWidth(0, 360)
        for c in range(1, 6):
            self.table.setColumnWidth(c, 90)
        self.table.setColumnWidth(5, 132)  # 进度列文本更长，单独加宽
        self.count_label.setText(f"共 {self.model.rowCount()} 条")

    def _on_search(self, text):
        self.proxy.set_needle(text)
        self._update_count()

    def _on_status_filter(self, _index):
        status = self.status_filter.currentData() or ""
        self.proxy.set_status_filter(status)
        self._update_count()

    def _update_count(self):
        self.count_label.setText(f"匹配 {self.proxy.rowCount()} / {self.model.rowCount()} 条")

    def _open_subject(self, index):
        row = self.proxy.mapToSource(index).row()
        if 0 <= row < len(self.collection.items):
            sid = self.collection.items[row].subject_id
            webbrowser.open(f"https://bgm.tv/subject/{sid}")

    def _show_table_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = self.proxy.mapToSource(index).row()
        if not (0 <= row < len(self.collection.items)):
            return
        item = self.collection.items[row]
        menu = QtWidgets.QMenu(self)
        act_open = menu.addAction("在浏览器打开条目")
        act_copy = menu.addAction("复制条目链接")
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen is act_open:
            webbrowser.open(f"https://bgm.tv/subject/{item.subject_id}")
        elif chosen is act_copy:
            QtWidgets.QApplication.clipboard().setText(f"https://bgm.tv/subject/{item.subject_id}")
            self.status_label.setText("已复制条目链接")

    def _render_ranking(self):
        r = self.report
        cols = ["#", "作品", "年份", "我的评分", "全站均分"]
        self.ranking_table.setColumnCount(len(cols))
        self.ranking_table.setHorizontalHeaderLabels(cols)
        self.ranking_table.setRowCount(len(r.top_rated))
        for i, it in enumerate(r.top_rated):
            vals = [str(i + 1), it.name_cn or it.name, str(it.year or "-"),
                    str(it.rate), f"{it.bangumi_score:.1f}" if it.bangumi_score else "-"]
            for c, val in enumerate(vals):
                cell = QtWidgets.QTableWidgetItem(val)
                if c != 1:
                    cell.setTextAlignment(QtCore.Qt.AlignCenter)
                self.ranking_table.setItem(i, c, cell)
        self.ranking_table.horizontalHeader().setStretchLastSection(True)
        self.ranking_table.setColumnWidth(1, 460)

    def _render_years(self):
        r = self.report
        cols = ["年份", "总计", "看过", "在看", "想看", "搁置", "抛弃", "均分"]
        self.years_table.setColumnCount(len(cols))
        self.years_table.setHorizontalHeaderLabels(cols)
        self.years_table.setRowCount(len(r.year_trend))
        for i, d in enumerate(r.year_trend):
            vals = [d.year, d.total, d.finished, d.watching, d.wish, d.on_hold, d.dropped,
                    f"{d.avg_rating:.1f}"]
            for c, val in enumerate(vals):
                cell = QtWidgets.QTableWidgetItem(str(val))
                cell.setTextAlignment(QtCore.Qt.AlignCenter)
                self.years_table.setItem(i, c, cell)
        self.years_table.horizontalHeader().setStretchLastSection(True)

    # -------------------------------------------------- 导出
    def _export_csv(self):
        if not self.collection:
            return
        p, _ = QtWidgets.QFileDialog.getSaveFileName(self, "导出 CSV", "collection.csv", "CSV (*.csv)")
        if p:
            collection_to_csv(self.collection, p)
            self.status_label.setText(f"已导出 CSV：{p}")

    def _export_json(self):
        if not self.collection:
            return
        p, _ = QtWidgets.QFileDialog.getSaveFileName(self, "导出 JSON", "collection.json", "JSON (*.json)")
        if p:
            collection_to_json(self.collection, p)
            self.status_label.setText(f"已导出 JSON：{p}")

    def _export_report_json(self):
        if not self.report:
            return
        p, _ = QtWidgets.QFileDialog.getSaveFileName(self, "导出报告 JSON", "report.json", "JSON (*.json)")
        if p:
            report_to_json(self.report, p)
            self.status_label.setText(f"已导出报告 JSON：{p}")

    def _export_html(self):
        if not self.report:
            return
        p, _ = QtWidgets.QFileDialog.getSaveFileName(self, "导出 HTML 报告", "report.html", "HTML (*.html)")
        if not p:
            return
        from jinja2 import Environment, FileSystemLoader
        if not self._charts_uri:
            self._charts_uri = render_all(self.report)
        env = Environment(
            loader=FileSystemLoader(str(Path(__file__).resolve().parent.parent / "templates")),
            autoescape=True)
        html = env.get_template("report.html.j2").render(report=self.report, charts=self._charts_uri)
        Path(p).write_text(html, encoding="utf-8")
        self.status_label.setText(f"已导出 HTML：{p}")
        if QtWidgets.QMessageBox.question(
                self, "导出完成", "HTML 报告已保存，是否在浏览器中打开？") == \
                QtWidgets.QMessageBox.Yes:
            webbrowser.open(Path(p).resolve().as_uri())

    def _open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def _open_logs(self):
        dialog = LogDialog(self)
        dialog.exec()

    def _clear_cache(self):
        from ..core.cache import Cache
        cache_dir = load_config().cache.dir or None
        c = Cache(directory=cache_dir)
        count = c.size
        if count and QtWidgets.QMessageBox.question(
                self, "清空缓存", f"确定清空 {count} 条本地缓存吗？") != QtWidgets.QMessageBox.Yes:
            c.close()
            return
        c.clear()
        c.close()
        self.status_label.setText(f"缓存已清空（{count} 条）")

    def _about(self):
        QtWidgets.QMessageBox.about(
            self, "关于 Bangumi Catcher",
            f"<b>{APP_NAME}</b> v{APP_VERSION}<br><br>"
            "Bangumi 用户收藏抓取与可视化分析工具<br>"
            "PySide6 · matplotlib · httpx · pydantic<br><br>"
            "数据来源：<a href='https://bgm.tv'>Bangumi 番组计划</a>")

    # -------------------------------------------------- 状态持久化
    def _restore_state(self):
        last = self.settings.value("last_user", "", type=str)
        if last:
            self.user_input.setText(last)
        geo = self.settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        if self._thread and self._thread.isRunning():
            if self._worker:
                self._worker.cancel()
            self._thread.quit()
            self._thread.wait(2000)
        super().closeEvent(event)
