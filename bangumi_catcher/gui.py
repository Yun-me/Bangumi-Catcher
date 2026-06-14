"""Tkinter 桌面 GUI —— 一键抓取 · 分析 · 导出."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# 确保 bangumi_catcher 包可被导入 (PyInstaller / 直接运行均兼容)
_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from PIL import Image, ImageTk

from bangumi_catcher.analyzer import analyze
from bangumi_catcher.api import BangumiClient
from bangumi_catcher.config import load_config
from bangumi_catcher.exceptions import BangumiError, EmptyCollectionError
from bangumi_catcher.export import collection_to_csv, collection_to_json, report_to_json
from bangumi_catcher.models import UserCollection, AnalysisReport
from bangumi_catcher.reporter import generate_html
from bangumi_catcher.visualizer import (
    fig_yearly_trend,
    fig_rating_distribution,
    fig_collection_pie,
    fig_top_rated,
)

logger = logging.getLogger(__name__)


# ================================================================
# 异步在线程中运行
# ================================================================

def _run_async(coro):
    """在新线程中运行 asyncio，返回结果或抛出异常."""
    result: list = []
    error: list = []

    def _target():
        try:
            result.append(asyncio.run(coro))
        except Exception as e:
            error.append(e)

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join()

    if error:
        raise error[0]
    return result[0]


# ================================================================
# 主窗口
# ================================================================

class BangumiApp:
    """Bangumi Catcher Tkinter 应用."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Bangumi Catcher")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)

        # 数据
        self.collection: UserCollection | None = None
        self.report: AnalysisReport | None = None
        self.chart_images: dict[str, ImageTk.PhotoImage] = {}

        # 样式
        self._setup_style()

        # 布局
        self._build_top_bar()
        self._build_notebook()

    # ------------------------------------------------------------
    # 样式
    # ------------------------------------------------------------

    def _setup_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        bg = "#f0f0f0"
        fg = "#333333"
        accent = "#4CAF50"

        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg, font=("Microsoft YaHei", 10))
        style.configure("TButton", font=("Microsoft YaHei", 10), padding=6)
        style.configure("Accent.TButton", background=accent, foreground="white")
        style.configure("TLabelframe", background=bg, foreground=fg)
        style.configure("TLabelframe.Label", background=bg, foreground=fg, font=("Microsoft YaHei", 10, "bold"))
        style.configure("TNotebook", background=bg)
        style.configure("TNotebook.Tab", font=("Microsoft YaHei", 10), padding=[12, 4])
        style.configure("TProgressbar", thickness=20)

        self.root.configure(background=bg)

    # ------------------------------------------------------------
    # 顶栏
    # ------------------------------------------------------------

    def _build_top_bar(self) -> None:
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.X)

        ttk.Label(frame, text="Bangumi 用户 ID:", font=("Microsoft YaHei", 11)).pack(side=tk.LEFT, padx=(0, 8))

        self.user_entry = ttk.Entry(frame, width=24, font=("Microsoft YaHei", 11))
        self.user_entry.pack(side=tk.LEFT, padx=(0, 8))
        self.user_entry.bind("<Return>", lambda e: self._on_fetch())

        self.fetch_btn = ttk.Button(frame, text="开始抓取", command=self._on_fetch)
        self.fetch_btn.pack(side=tk.LEFT, padx=(0, 16))

        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=200)
        self.status_label = ttk.Label(frame, text="就绪", foreground="#888")

    # ------------------------------------------------------------
    # Notebook (Tab 页)
    # ------------------------------------------------------------

    def _build_notebook(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Tab 1: 概览
        self.tab_overview = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_overview, text="📋 概览")

        # Tab 2: 图表
        self.tab_charts = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_charts, text="📈 图表")

        # Tab 3: 排行
        self.tab_ranking = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ranking, text="🏆 排行")

        # Tab 4: 年份
        self.tab_years = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_years, text="📅 年度明细")

        # 导出按钮 (底部)
        btn_frame = ttk.Frame(self.root, padding=(10, 0, 10, 6))
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="导出 CSV", command=self._export_csv).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="导出 JSON", command=self._export_json).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="导出 HTML 报告", command=self._export_html).pack(side=tk.LEFT, padx=4)

    # ------------------------------------------------------------
    # 抓取逻辑
    # ------------------------------------------------------------

    def _on_fetch(self) -> None:
        username = self.user_entry.get().strip()
        if not username:
            messagebox.showwarning("提示", "请输入 Bangumi 用户 ID")
            return

        self.fetch_btn.config(state=tk.DISABLED)
        self.progress.pack(side=tk.LEFT, padx=(8, 8))
        self.progress.start()
        self.status_label.config(text="正在抓取...")
        self.status_label.pack(side=tk.LEFT)

        # 在后台线程运行
        threading.Thread(target=self._fetch_thread, args=(username,), daemon=True).start()

    def _fetch_thread(self, username: str) -> None:
        try:
            cfg = load_config()
            collection, report = _run_async(self._do_fetch(cfg, username))
            self.root.after(0, self._on_fetch_done, collection, report, None)
        except Exception as e:
            self.root.after(0, self._on_fetch_done, None, None, str(e))

    async def _do_fetch(self, cfg: dict, username: str):
        async with BangumiClient(cfg) as client:
            collection = await client.fetch_collection(username)
        report = analyze(collection)
        return collection, report

    def _on_fetch_done(
        self, collection: UserCollection | None, report: AnalysisReport | None, error: str | None,
    ) -> None:
        self.progress.stop()
        self.progress.pack_forget()
        self.status_label.pack_forget()
        self.fetch_btn.config(state=tk.NORMAL)

        if error:
            if "ConnectError" in error or "connect" in error.lower():
                msg = f"网络连接失败，无法访问 Bangumi API。\n\n{error}\n\n请检查网络或尝试使用代理。"
            elif "validation error" in error.lower():
                msg = f"数据解析错误，可能是 API 返回格式变化。\n\n{error}"
            elif "EmptyCollection" in error or "为空" in error:
                msg = f"该用户收藏为空或设置了隐私保护。\n\n{error}"
            else:
                msg = error
            messagebox.showerror("抓取失败", msg)
            return

        self.collection = collection
        self.report = report
        self._render_overview()
        self._render_charts()
        self._render_ranking()
        self._render_years()
        self.status_label.config(text=f"完成! {report.total_items} 条收藏", foreground="#4CAF50")
        self.status_label.pack(side=tk.LEFT)

    # ------------------------------------------------------------
    # Tab 1: 概览
    # ------------------------------------------------------------

    def _render_overview(self) -> None:
        for w in self.tab_overview.winfo_children():
            w.destroy()

        r = self.report
        if r is None:
            return

        cards = ttk.Frame(self.tab_overview, padding=20)
        cards.pack(fill=tk.X)

        stats = [
            ("总收藏", r.total_items),
            ("平均评分", f"{r.overall_avg_rating:.1f}"),
            ("覆盖年份", len(r.by_year)),
        ]
        for type_name, count in r.type_counts.items():
            stats.append((type_name, count))

        for i, (label, value) in enumerate(stats):
            card = ttk.LabelFrame(cards, text=label)
            card.grid(row=i // 4, column=i % 4, padx=8, pady=8, sticky="nsew")
            val = ttk.Label(card, text=str(value), font=("Microsoft YaHei", 24, "bold"), foreground="#4CAF50")
            val.pack(padx=24, pady=16)

        for col in range(4):
            cards.columnconfigure(col, weight=1)

        # 评分分布
        if r.rating_distribution:
            dist_frame = ttk.LabelFrame(self.tab_overview, text="评分分布", padding=10)
            dist_frame.pack(fill=tk.X, padx=20, pady=10)
            text = "  ".join(f"{k}分×{v}" for k, v in sorted(r.rating_distribution.items()))
            ttk.Label(dist_frame, text=text, font=("Consolas", 10)).pack()

    # ------------------------------------------------------------
    # Tab 2: 图表
    # ------------------------------------------------------------

    def _render_charts(self) -> None:
        for w in self.tab_charts.winfo_children():
            w.destroy()

        r = self.report
        if r is None:
            return

        self.chart_images.clear()

        # 外框 — 填满 tab
        outer = ttk.Frame(self.tab_charts)
        outer.pack(fill=tk.BOTH, expand=True)

        # Canvas + 双向滚动条
        canvas = tk.Canvas(outer, bg="#f0f0f0", highlightthickness=0)
        v_scroll = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        h_scroll = ttk.Scrollbar(outer, orient=tk.HORIZONTAL, command=canvas.xview)

        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        win_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # 布局: canvas 填满, 滚动条贴边
        canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        # 鼠标滚轮 — 仅作用于 canvas 区域
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_shift_mousewheel(event):
            canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        canvas.bind("<Shift-MouseWheel>", _on_shift_mousewheel, add="+")

        # 让内框宽度跟随 canvas 可见宽度
        def _sync_width(event):
            canvas.itemconfig(win_id, width=event.width)
        canvas.bind("<Configure>", _sync_width, add="+")

        # 生成图表 — 宽度自适应
        canvas.update_idletasks()
        chart_width = max(canvas.winfo_width() - 40, 400)

        charts = [
            ("年度收藏趋势", fig_yearly_trend),
            ("评分分布", fig_rating_distribution),
            ("收藏类型分布", fig_collection_pie),
            ("最爱排行", fig_top_rated),
        ]

        for title, fig_fn in charts:
            try:
                fig = fig_fn(r)
                fig.update_layout(width=chart_width, height=chart_width * 9 // 16)
                buf = io.BytesIO()
                fig.write_image(buf, format="png", scale=1.5)
                buf.seek(0)

                img = Image.open(buf)
                photo = ImageTk.PhotoImage(img)
                self.chart_images[title] = photo

                section = ttk.LabelFrame(scroll_frame, text=title, padding=8)
                section.pack(fill=tk.X, padx=12, pady=6)
                ttk.Label(section, image=photo).pack()
            except Exception as e:
                section = ttk.LabelFrame(scroll_frame, text=title, padding=8)
                section.pack(fill=tk.X, padx=12, pady=6)
                ttk.Label(section, text=f"图表生成失败: {e}", foreground="red").pack()

    # ------------------------------------------------------------
    # Tab 3: 排行
    # ------------------------------------------------------------

    def _render_ranking(self) -> None:
        for w in self.tab_ranking.winfo_children():
            w.destroy()

        r = self.report
        if r is None or not r.top_rated:
            ttk.Label(self.tab_ranking, text="暂无排行数据", padding=30).pack()
            return

        tree = ttk.Treeview(
            self.tab_ranking,
            columns=("rank", "name", "year", "rate", "bgm"),
            show="headings",
            height=20,
        )
        tree.heading("rank", text="#")
        tree.heading("name", text="作品")
        tree.heading("year", text="年份")
        tree.heading("rate", text="评分")
        tree.heading("bgm", text="Bangumi 均分")

        tree.column("rank", width=40, anchor=tk.CENTER)
        tree.column("name", width=400)
        tree.column("year", width=60, anchor=tk.CENTER)
        tree.column("rate", width=60, anchor=tk.CENTER)
        tree.column("bgm", width=100, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(self.tab_ranking, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        for i, item in enumerate(r.top_rated, 1):
            tree.insert("", tk.END, values=(
                i,
                item.name_cn or item.name,
                item.year or "-",
                item.rate,
                f"{item.bangumi_score:.1f}" if item.bangumi_score > 0 else "-",
            ))

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

    # ------------------------------------------------------------
    # Tab 4: 年度明细
    # ------------------------------------------------------------

    def _render_years(self) -> None:
        for w in self.tab_years.winfo_children():
            w.destroy()

        r = self.report
        if r is None or not r.year_trend:
            ttk.Label(self.tab_years, text="暂无年度数据", padding=30).pack()
            return

        tree = ttk.Treeview(
            self.tab_years,
            columns=("year", "total", "finished", "watching", "wish", "hold", "drop", "avg"),
            show="headings",
            height=20,
        )

        for col, text, width in [
            ("year", "年份", 60), ("total", "总计", 60),
            ("finished", "看过", 60), ("watching", "在看", 60),
            ("wish", "想看", 60), ("hold", "搁置", 60),
            ("drop", "抛弃", 60), ("avg", "均分", 60),
        ]:
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(self.tab_years, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        for d in r.year_trend:
            tree.insert("", tk.END, values=(
                d.year, d.total, d.finished, d.watching,
                d.wish, d.on_hold, d.dropped, f"{d.avg_rating:.1f}",
            ))

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

    # ------------------------------------------------------------
    # 导出
    # ------------------------------------------------------------

    def _export_csv(self) -> None:
        if self.collection is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            collection_to_csv(self.collection, path)
            messagebox.showinfo("导出完成", f"已保存到:\n{path}")

    def _export_json(self) -> None:
        if self.collection is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            collection_to_json(self.collection, path)
            messagebox.showinfo("导出完成", f"已保存到:\n{path}")

    def _export_html(self) -> None:
        if self.collection is None or self.report is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML", "*.html")])
        if not path:
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            charts_dir = Path(tmpdir) / "charts"
            charts_dir.mkdir()
            chart_paths: dict[str, str] = {}
            for name, fig_fn in [
                ("yearly_trend", fig_yearly_trend),
                ("rating_distribution", fig_rating_distribution),
                ("collection_pie", fig_collection_pie),
                ("top_rated", fig_top_rated),
            ]:
                fig = fig_fn(self.report)
                p = str(charts_dir / f"{name}.png")
                fig.write_image(p, format="png", scale=2)
                chart_paths[name] = p
            generate_html(self.report, chart_paths, path)
        messagebox.showinfo("导出完成", f"HTML 报告已保存到:\n{path}")


# ================================================================
# 入口
# ================================================================

def main() -> None:
    """启动 Tkinter GUI."""
    root = tk.Tk()
    BangumiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
