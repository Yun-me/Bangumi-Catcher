"""Qt 主题 —— 克制、原生观感的 QSS 样式 + 亮/暗双色板.

设计原则（对应"去 AI 味 / 现代简约"）：
* 顶栏不再用蓝色渐变横幅，改为与窗体同色系的扁平表面 + 一道底部细线。
* 圆角收敛：卡片 8px、控件 6px，避免"胶囊感"。
* 信息层级靠字号/字重/留白与极浅的描边区分，不靠大色块与分割线堆叠。
* 强调色只保留一种蓝，用于主操作与选中态；数据色集中在图表里。
"""

from __future__ import annotations


class Palette:
    """一套主题色。"""

    def __init__(self, dark: bool):
        if dark:
            self.bg = "#16191F"        # 窗体背景
            self.surface = "#1E222A"   # 顶栏 / 输入 / 菜单
            self.card = "#20242C"      # 卡片
            self.card_alt = "#262B34"  # 表格交替行
            self.text = "#E6E9EF"
            self.muted = "#9AA3B2"
            self.border = "#2E343E"
            self.hover = "#272C35"
            self.accent = "#5B8DEF"
            self.accent_hover = "#4A7BE0"
        else:
            self.bg = "#F6F7F9"
            self.surface = "#FFFFFF"
            self.card = "#FFFFFF"
            self.card_alt = "#FAFBFC"
            self.text = "#1F2329"
            self.muted = "#8A929E"
            self.border = "#E8EAED"
            self.hover = "#F2F4F7"
            self.accent = "#3B7DF0"
            self.accent_hover = "#2F6BD8"
        # 跨主题统一
        self.accent2 = "#1FB6A6"
        self.danger = "#E2506B"
        self.warning = "#E8A317"
        self.on_accent = "#FFFFFF"
        self.dark = dark


def build_stylesheet(p: Palette) -> str:
    return f"""
* {{
    font-family: "Microsoft YaHei UI", "PingFang SC", "Noto Sans CJK SC", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {p.text};
    outline: none;
}}
QMainWindow, QWidget#Root {{ background: {p.bg}; }}

/* ---------- 顶栏：扁平、与窗体同色系、仅底部细线 ---------- */
QFrame#Header {{
    background: {p.surface};
    border: none;
    border-bottom: 1px solid {p.border};
}}
QLabel#AppTitle {{ color: {p.text}; font-size: 16px; font-weight: 600; }}

/* ---------- 输入控件 ---------- */
QLineEdit, QComboBox {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {p.accent};
    selection-color: {p.on_accent};
}}
QLineEdit:hover, QComboBox:hover {{ border: 1px solid {p.muted}; }}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {p.accent}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {p.surface};
    border: 1px solid {p.border};
    selection-background-color: {p.accent};
    selection-color: {p.on_accent};
    border-radius: 6px;
    padding: 4px;
}}

/* ---------- 按钮 ---------- */
QPushButton {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: 6px;
    padding: 6px 14px;
    color: {p.text};
}}
QPushButton:hover {{ background: {p.hover}; border: 1px solid {p.muted}; }}
QPushButton:disabled {{ color: {p.muted}; background: {p.surface}; }}

QPushButton#Primary {{
    background: {p.accent};
    color: {p.on_accent};
    border: 1px solid {p.accent};
    font-weight: 600;
    padding: 6px 18px;
}}
QPushButton#Primary:hover {{ background: {p.accent_hover}; border-color: {p.accent_hover}; }}
QPushButton#Primary:disabled {{ background: {p.muted}; border-color: {p.muted}; color: {p.surface}; }}

QPushButton#Ghost {{ background: transparent; color: {p.muted}; border: 1px solid {p.border}; }}
QPushButton#Ghost:hover {{ background: {p.hover}; color: {p.text}; }}

/* ---------- Tab：下划线式，克制 ---------- */
QTabWidget::pane {{ border: none; background: {p.bg}; }}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: transparent;
    color: {p.muted};
    padding: 9px 16px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {p.text}; border-bottom: 2px solid {p.accent}; }}
QTabBar::tab:hover:!selected {{ color: {p.text}; }}

/* ---------- 卡片 ---------- */
QFrame#StatCard, QFrame#ChartCard {{
    background: {p.card};
    border: 1px solid {p.border};
    border-radius: 8px;
}}
QLabel#StatValue {{ font-size: 25px; font-weight: 700; color: {p.text}; }}
QLabel#StatLabel {{ color: {p.muted}; font-size: 12px; }}
QLabel#ChartTitle {{ font-size: 13px; font-weight: 600; color: {p.text}; }}

/* ---------- 表格 ---------- */
QTableView {{
    background: {p.card};
    border: 1px solid {p.border};
    border-radius: 8px;
    gridline-color: transparent;
    selection-background-color: {p.accent};
    selection-color: {p.on_accent};
    alternate-background-color: {p.card_alt};
}}
QHeaderView::section {{
    background: {p.surface};
    color: {p.muted};
    border: none;
    border-bottom: 1px solid {p.border};
    padding: 8px 10px;
    font-weight: 600;
}}
QTableView::item {{ padding: 5px 8px; border: none; }}
QTableCornerButton::section {{ background: {p.surface}; border: none; }}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p.border}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {p.muted}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {p.border}; border-radius: 5px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {p.muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollArea {{ border: none; background: {p.bg}; }}
QWidget#FlowPage {{ background: {p.bg}; }}

/* ---------- 进度条 / 状态栏 ---------- */
QProgressBar {{
    background: {p.border};
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{ background: {p.accent}; border-radius: 4px; }}
QStatusBar {{ background: {p.surface}; color: {p.muted}; border-top: 1px solid {p.border}; }}
QStatusBar::item {{ border: none; }}

/* ---------- 菜单 ---------- */
QMenuBar {{ background: {p.surface}; border-bottom: 1px solid {p.border}; }}
QMenuBar::item {{ padding: 6px 12px; background: transparent; }}
QMenuBar::item:selected {{ background: {p.hover}; border-radius: 6px; }}
QMenu {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 7px 22px; border-radius: 6px; }}
QMenu::item:selected {{ background: {p.accent}; color: {p.on_accent}; }}
QMenu::separator {{ height: 1px; background: {p.border}; margin: 4px 8px; }}

/* ---------- 其它 ---------- */
QLabel#Muted {{ color: {p.muted}; }}
QLabel#Empty {{ color: {p.muted}; font-size: 14px; }}
QCheckBox {{ color: {p.text}; spacing: 6px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px;
    border-radius: 4px;
    border: 1px solid {p.muted};
    background: {p.surface};
}}
QCheckBox::indicator:checked {{ background: {p.accent}; border: 1px solid {p.accent}; }}
QToolTip {{
    background: {p.surface}; color: {p.text};
    border: 1px solid {p.border}; border-radius: 6px; padding: 5px 8px;
}}
"""
