"""Bangumi Catcher —— PySide6 (Qt) 现代化桌面 GUI.

设计要点：
* 响应式布局：FlowLayout + Qt layout manager，窗口缩放/全屏自动重排，无裁剪、无挤角。
* 实时图表：matplotlib FigureCanvasQTAgg 随窗口重绘，不再是固定尺寸 PNG。
* 不卡死：抓取/分析在 QThread 后台执行，通过 Qt 信号回主线程。
* 现代功能：亮/暗主题、可搜索可排序的收藏总表、设置持久化、一键导出 / 浏览器打开报告。
"""

from __future__ import annotations

import asyncio
import logging
import threading
import webbrowser
from pathlib import Path

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6 import QtCore, QtGui, QtWidgets

from .analyzer import analyze
from .api import BangumiClient
from .config import load_config
from .export import collection_to_csv, collection_to_json
from .flowlayout import FlowLayout
from .models import AnalysisReport, UserCollection
from .theme import Palette, build_stylesheet
from .visualizer import CHART_TITLES, build_figures, render_all

logger = logging.getLogger(__name__)

APP_NAME = "Bangumi Catcher"
APP_VERSION = "1.2.2"
TYPE_MAP = {"动画": 2, "书籍": 1, "音乐": 3, "游戏": 4, "三次元": 6}


# ============================================================ 后台 worker
class FetchWorker(QtCore.QObject):
    progress = QtCore.Signal(float, str)
    finished = QtCore.Signal(object, object)   # (UserCollection, AnalysisReport)
    failed = QtCore.Signal(str)

    def __init__(self, username: str, subject_type: int, force_refresh: bool):
        super().__init__()
        self.username = username
        self.subject_type = subject_type
        self.force_refresh = force_refresh
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    @QtCore.Slot()
    def run(self):
        try:
            cfg = load_config()
            a = cfg.get("analysis", {})

            def progress(frac, msg):
                # 取消信号在此检查：抛出异常即可中断 asyncio.run 内的抓取。
                if self._cancel.is_set():
                    raise _Cancelled()
                self.progress.emit(float(frac), str(msg))

            progress(0.02, "连接 Bangumi API …")

            # 把抓取自身的 0-1 进度映射到整体进度的 2%–70% 区间，
            # 余下 70%–100% 留给本地分析，进度条因此全程平滑推进。
            def fetch_progress(frac, msg):
                progress(0.02 + 0.68 * frac, msg)

            async def _fetch():
                async with BangumiClient(cfg) as client:
                    return await client.fetch_collection(
                        self.username, subject_type=self.subject_type,
                        force_refresh=self.force_refresh,
                        progress=fetch_progress,
                    )

            collection = asyncio.run(_fetch())
            progress(0.72, "分析数据 …")
            report = analyze(
                collection,
                year_start=a.get("year_start", 2000),
                year_end=a.get("year_end", 2025),
                top_n=a.get("top_n", 20),
            )
            progress(1.0, "完成")
            self.finished.emit(collection, report)
        except _Cancelled:
            self.failed.emit("已取消")
        except Exception as e:  # noqa: BLE001
            logger.exception("抓取失败")
            self.failed.emit(str(e))


class _Cancelled(Exception):
    pass


# ============================================================ 小组件
def _soft_shadow(widget, blur=18, dy=2, alpha=28):
    """给卡片加一层极浅阴影，替代生硬描边来区分层级。"""
    eff = QtWidgets.QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setXOffset(0)
    eff.setYOffset(dy)
    eff.setColor(QtGui.QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(eff)


def _progress_label(item) -> str:
    """收藏条目的「进度」展示文本。

    把此前只显示完成百分比（且常年为 0）改为直接呈现「已看 / 总集数」，
    让 ep_status 真正可见：
      * 看过 → 「看完 · 全 N 话」/「看完」
      * 在看 / 搁置 / 抛弃且有进度 → 「已看/总集」或「看到第 N 话」
      * 想看 / 无进度 → 「—」
    """
    total = item.subject.episodes_total if item.subject else 0
    if item.type == 2:           # 看过
        return f"看完 · 全 {total} 话" if total else "看完"
    if item.type == 1:           # 想看
        return "—"
    if item.ep_status > 0:       # 在看 / 搁置 / 抛弃，有进度
        return f"{item.ep_status}/{total}" if total else f"看到第 {item.ep_status} 话"
    return f"0/{total}" if total else "—"


class StatCard(QtWidgets.QFrame):
    """概览数字卡片：靠字号/字重而非颜色区分主次。"""

    def __init__(self, value, label):
        super().__init__()
        self.setObjectName("StatCard")
        self.setFixedSize(176, 92)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(2)
        v = QtWidgets.QLabel(str(value))
        v.setObjectName("StatValue")
        lbl = QtWidgets.QLabel(label)
        lbl.setObjectName("StatLabel")
        lay.addWidget(v)
        lay.addWidget(lbl)
        lay.addStretch()
        _soft_shadow(self)


class ChartCard(QtWidgets.QFrame):
    """图表卡片：标题 + 随窗口重绘的 matplotlib 画布。"""

    def __init__(self, title, figure):
        super().__init__()
        self.setObjectName("ChartCard")
        self.setMinimumWidth(440)
        self.setMinimumHeight(340)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        t = QtWidgets.QLabel(title)
        t.setObjectName("ChartTitle")
        lay.addWidget(t)
        self.canvas = FigureCanvasQTAgg(figure)
        self.canvas.setStyleSheet("background:transparent;")
        lay.addWidget(self.canvas, 1)
        _soft_shadow(self)

    def sizeHint(self):
        return QtCore.QSize(520, 380)


# ============================================================ 搜索过滤
class _SearchProxy(QtCore.QSortFilterProxyModel):
    """跨「作品名 / 标签 / 短评」的不区分大小写过滤。

    可搜索文本（名称 + 标签 + 短评）预先拼好存在第 0 列的 UserRole 里，
    过滤时只比对这一份：既覆盖了未显示为列的短评，也避免逐列取值。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._needle = ""

    def set_needle(self, text: str) -> None:
        self._needle = (text or "").strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):  # noqa: N802 (Qt 命名)
        if not self._needle:
            return True
        model = self.sourceModel()
        idx = model.index(source_row, 0, source_parent)
        haystack = model.data(idx, QtCore.Qt.UserRole) or ""
        return self._needle in haystack.lower()


# ============================================================ 主窗口
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QtCore.QSettings(APP_NAME, APP_NAME)
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
        self.act_html = m_file.addAction("导出 HTML 报告…", self._export_html)
        self.act_csv.setShortcut("Ctrl+S")
        m_file.addSeparator()
        m_file.addAction("退出", self.close)

        m_tools = bar.addMenu("工具")
        m_tools.addAction("清除缓存", self._clear_cache)
        self.act_theme = m_tools.addAction("切换 暗/亮 主题", self._toggle_theme)
        self.act_theme.setShortcut("Ctrl+D")

        m_help = bar.addMenu("帮助")
        m_help.addAction("关于", self._about)

        for a in (self.act_csv, self.act_json, self.act_html):
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
        header.setFixedHeight(76)
        hl = QtWidgets.QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(12)

        title = QtWidgets.QLabel("Bangumi Catcher")
        title.setObjectName("AppTitle")
        hl.addWidget(title)
        hl.addSpacing(18)

        self.user_input = QtWidgets.QLineEdit()
        self.user_input.setPlaceholderText("输入 Bangumi 用户 ID / 用户名")
        self.user_input.setFixedWidth(240)
        self.user_input.returnPressed.connect(self._on_fetch)
        hl.addWidget(self.user_input)

        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(list(TYPE_MAP.keys()))
        self.type_combo.setFixedWidth(92)
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

        hl.addStretch(1)   # 关键：把控件推向左侧，剩余空间留白而非挤压
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
        self.proxy = _SearchProxy(self)
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)
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
        self._reset_controls()
        self.status_label.setText(
            f"{report.total_items} 条 · 均分 {report.overall_avg_rating} · "
            f"完成率 {report.avg_completion}%")
        for a in (self.act_csv, self.act_json, self.act_html):
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
            status.setTextAlignment(QtCore.Qt.AlignCenter)
            myrate = QtGui.QStandardItem()
            myrate.setData(it.rate or 0, QtCore.Qt.DisplayRole)
            myrate.setTextAlignment(QtCore.Qt.AlignCenter)
            bgm = QtGui.QStandardItem()
            bgm.setData(round(it.subject_score, 1), QtCore.Qt.DisplayRole)
            bgm.setTextAlignment(QtCore.Qt.AlignCenter)
            prog = QtGui.QStandardItem(_progress_label(it))
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
        self.count_label.setText(f"匹配 {self.proxy.rowCount()} / {self.model.rowCount()} 条")

    def _open_subject(self, index):
        row = self.proxy.mapToSource(index).row()
        if 0 <= row < len(self.collection.items):
            sid = self.collection.items[row].subject_id
            webbrowser.open(f"https://bgm.tv/subject/{sid}")

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
            loader=FileSystemLoader(str(Path(__file__).resolve().parent / "templates")),
            autoescape=True)
        html = env.get_template("report.html.j2").render(report=self.report, charts=self._charts_uri)
        Path(p).write_text(html, encoding="utf-8")
        self.status_label.setText(f"已导出 HTML：{p}")
        if QtWidgets.QMessageBox.question(
                self, "导出完成", "HTML 报告已保存，是否在浏览器中打开？") == \
                QtWidgets.QMessageBox.Yes:
            webbrowser.open(Path(p).resolve().as_uri())

    def _clear_cache(self):
        from .cache import Cache
        from .config import load_config
        cache_dir = load_config().get("cache", {}).get("dir") or None
        c = Cache(directory=cache_dir)
        c.clear()
        c.close()
        self.status_label.setText("缓存已清空")

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


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setApplicationName(APP_NAME)
    win = MainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
