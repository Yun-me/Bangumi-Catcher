"""Qt 主题 —— 现代化 QSS 样式表 + 亮/暗双色板.

不再依赖 Tkinter。颜色集中管理，QSS 负责所有控件外观，
布局的响应式由 Qt 的 layout manager 负责（见 gui.py）。
"""

from __future__ import annotations


class Palette:
    """一套主题色。"""

    def __init__(self, dark: bool):
        if dark:
            self.bg = "#15181E"
            self.surface = "#1E222B"
            self.card = "#252A34"
            self.card_alt = "#2C323D"
            self.text = "#E7EAF0"
            self.muted = "#9AA3B2"
            self.border = "#333A46"
            self.header1 = "#2B4C8C"
            self.header2 = "#3A6FD8"
            self.hover = "#2E3540"
        else:
            self.bg = "#F4F6FA"
            self.surface = "#FFFFFF"
            self.card = "#FFFFFF"
            self.card_alt = "#F7F9FC"
            self.text = "#2C2E33"
            self.muted = "#8A929E"
            self.border = "#E6E8EB"
            self.header1 = "#5B8DEF"
            self.header2 = "#6AA8FF"
            self.hover = "#EEF2F9"
        # 跨主题统一强调色
        self.accent = "#5B8DEF"
        self.accent_hover = "#4A7BE0"
        self.accent2 = "#21C7A8"
        self.danger = "#FF6B6B"
        self.warning = "#F7B500"
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

/* ---------- 顶部栏 ---------- */
QFrame#Header {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {p.header1}, stop:1 {p.header2});
    border: none;
}}
QLabel#AppTitle {{ color: #FFFFFF; font-size: 18px; font-weight: 700; }}
QLabel#HeaderHint {{ color: rgba(255,255,255,0.85); font-size: 12px; }}

/* ---------- 输入控件 ---------- */
QLineEdit, QComboBox {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: 8px;
    padding: 7px 12px;
    selection-background-color: {p.accent};
}}
QLineEdit#SearchBox {{ padding-left: 12px; }}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {p.accent}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {p.surface}; border: 1px solid {p.border};
    selection-background-color: {p.accent}; selection-color: #FFFFFF;
    border-radius: 6px;
}}

/* ---------- 按钮 ---------- */
QPushButton {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: 8px;
    padding: 7px 16px;
    color: {p.text};
}}
QPushButton:hover {{ background: {p.hover}; }}
QPushButton:disabled {{ color: {p.muted}; }}

QPushButton#Primary {{
    background: {p.accent}; color: {p.on_accent};
    border: none; font-weight: 600; padding: 8px 22px;
}}
QPushButton#Primary:hover {{ background: {p.accent_hover}; }}
QPushButton#Primary:disabled {{ background: {p.muted}; }}

QPushButton#Danger {{ background: {p.danger}; color: #FFFFFF; border: none; }}
QPushButton#Ghost {{ background: transparent; color: #FFFFFF; border: 1px solid rgba(255,255,255,0.4); }}
QPushButton#Ghost:hover {{ background: rgba(255,255,255,0.12); }}

/* ---------- Tab ---------- */
QTabWidget::pane {{ border: none; background: {p.bg}; }}
QTabBar::tab {{
    background: transparent; color: {p.muted};
    padding: 9px 18px; margin-right: 4px;
    border: none; border-bottom: 2px solid transparent;
    font-size: 13px;
}}
QTabBar::tab:selected {{ color: {p.accent}; border-bottom: 2px solid {p.accent}; font-weight: 600; }}
QTabBar::tab:hover {{ color: {p.text}; }}

/* ---------- 卡片 ---------- */
QFrame#Card {{
    background: {p.card};
    border: 1px solid {p.border};
    border-radius: 14px;
}}
QFrame#StatCard {{
    background: {p.card};
    border: 1px solid {p.border};
    border-radius: 14px;
}}
QFrame#ChartCard {{
    background: #FFFFFF;            /* 图表卡片始终浅底，保证图例可读 */
    border: 1px solid {p.border};
    border-radius: 14px;
}}
QLabel#StatValue {{ font-size: 26px; font-weight: 700; }}
QLabel#StatLabel {{ color: {p.muted}; font-size: 12px; }}
QLabel#CardTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#ChartTitle {{ font-size: 13px; font-weight: 600; color: {p.text}; }}

/* ---------- 表格 ---------- */
QTableView {{
    background: {p.card};
    border: 1px solid {p.border};
    border-radius: 12px;
    gridline-color: {p.border};
    selection-background-color: {p.accent};
    selection-color: #FFFFFF;
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
QTableView::item {{ padding: 4px 8px; }}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p.border}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {p.muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {p.border}; border-radius: 5px; min-width: 30px; }}
QScrollArea {{ border: none; background: {p.bg}; }}
QWidget#FlowPage {{ background: {p.bg}; }}

/* ---------- 进度条 / 状态栏 ---------- */
QProgressBar {{
    background: {p.border}; border: none; border-radius: 4px;
    height: 8px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {p.accent}; border-radius: 4px; }}
QStatusBar {{ background: {p.surface}; color: {p.muted}; border-top: 1px solid {p.border}; }}
QStatusBar::item {{ border: none; }}

/* ---------- 菜单 ---------- */
QMenuBar {{ background: {p.surface}; border-bottom: 1px solid {p.border}; }}
QMenuBar::item {{ padding: 6px 12px; background: transparent; }}
QMenuBar::item:selected {{ background: {p.hover}; border-radius: 6px; }}
QMenu {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 7px 24px; border-radius: 6px; }}
QMenu::item:selected {{ background: {p.accent}; color: #FFFFFF; }}

QLabel#Muted {{ color: {p.muted}; }}
QLabel#Empty {{ color: {p.muted}; font-size: 15px; }}
QCheckBox {{ color: #FFFFFF; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.5); }}
QCheckBox::indicator:checked {{ background: {p.accent2}; border: 1px solid {p.accent2}; }}
"""
