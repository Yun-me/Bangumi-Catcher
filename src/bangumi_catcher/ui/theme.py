"""Shared desktop design tokens and light/dark styles."""

from __future__ import annotations


class Palette:
    def __init__(self, dark: bool):
        self.dark = dark
        self.bg = "#141B1C" if dark else "#F4F7F5"
        self.surface = "#1C2425" if dark else "#FFFFFF"
        self.card = self.surface
        self.card_alt = "#222C2D" if dark else "#F8FAF9"
        self.text = "#E8F0ED" if dark else "#223B33"
        self.muted = "#9CB0A8" if dark else "#667B72"
        self.border = "#30403C" if dark else "#E0E9E4"
        self.hover = "#293C35" if dark else "#EAF3EE"
        self.accent = "#51C8A2" if dark else "#178365"
        self.accent_hover = "#71D7B6" if dark else "#116C53"
        self.on_accent = "#10251C" if dark else "#FFFFFF"
        self.accent2 = "#6291D5"
        self.danger = "#E17F89" if dark else "#B84356"
        self.warning = "#DBB568"


def build_stylesheet(palette: Palette) -> str:
    return f"""
    * {{ font-family: "Segoe UI", "Microsoft YaHei UI", "PingFang SC", "Noto Sans CJK SC";
         font-size: 13px; color: {palette.text}; }}
    QMainWindow, QDialog, QWidget#Root, QWidget#Page {{ background: {palette.bg}; }}
    QLabel {{ background: transparent; }}
    QLabel#Muted, QLabel#Eyebrow {{ color: {palette.muted}; }}
    QLabel#Eyebrow {{ font-size: 11px; font-weight: 600; }}
    QLabel#PageTitle {{ font-size: 26px; font-weight: 700; }}
    QLabel#HeroTitle {{ font-size: 30px; font-weight: 700; }}
    QLabel#SectionTitle {{ font-size: 16px; font-weight: 600; }}
    QLabel#StatValue {{ font-size: 30px; font-weight: 700; }}
    QLabel#DetailTitle {{ font-size: 19px; font-weight: 600; }}
    QFrame#Card, QFrame#StatCard, QFrame#DetailPanel {{
        background: {palette.surface}; border: 1px solid {palette.border}; border-radius: 12px;
    }}
    QFrame#Hero {{ background: {palette.hover}; border: 1px solid {palette.border}; border-radius: 14px; }}
    QFrame#Sidebar {{ background: #173C31; border: none; }}
    QFrame#Sidebar QLabel {{ color: #D4E6DD; }}
    QFrame#Sidebar QLabel#Brand {{ color: #FFFFFF; font-size: 20px; font-weight: 700; }}
    QFrame#Sidebar QLabel#SideMuted {{ color: #A1BDB0; font-size: 11px; }}
    QFrame#Sidebar QPushButton {{ background: transparent; color: #C3D8CD; border: none;
        text-align: left; padding: 12px 16px; border-radius: 8px; font-size: 13px; }}
    QFrame#Sidebar QPushButton:hover {{ background: #254C3F; color: #FFFFFF; }}
    QFrame#Sidebar QPushButton:checked {{ background: #D6EEDF; color: #173C31; font-weight: 600; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {palette.surface};
        border: 1px solid {palette.border}; border-radius: 7px; padding: 8px 10px;
        selection-background-color: {palette.accent}; selection-color: {palette.on_accent}; min-height: 20px; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {palette.accent}; }}
    QLineEdit:disabled, QComboBox:disabled {{ color: {palette.muted}; background: {palette.card_alt}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{ background: {palette.surface}; color: {palette.text};
        selection-background-color: {palette.hover}; selection-color: {palette.text}; padding: 4px; }}
    QPushButton, QToolButton {{ background: {palette.surface}; border: 1px solid {palette.border};
        border-radius: 7px; padding: 9px 14px; color: {palette.text}; min-height: 18px; }}
    QPushButton:hover, QToolButton:hover {{ background: {palette.hover}; border-color: {palette.accent}; }}
    QPushButton:focus, QToolButton:focus {{ border-color: {palette.accent}; }}
    QPushButton:disabled, QToolButton:disabled {{ color: {palette.muted}; background: {palette.card_alt}; }}
    QPushButton#Primary {{ background: {palette.accent}; color: {palette.on_accent};
        border-color: {palette.accent}; font-weight: 600; }}
    QPushButton#Primary:hover {{ background: {palette.accent_hover}; }}
    QPushButton#Primary:disabled {{ background: {palette.border}; border-color: {palette.border}; color: {palette.muted}; }}
    QPushButton#Link {{ border: none; background: transparent; color: {palette.accent}; padding: 5px 0; text-align: left; }}
    QPushButton#Tag {{ background: {palette.hover}; border: none; padding: 6px 10px; color: {palette.accent}; }}
    QPushButton#ListItem {{ text-align: left; padding: 12px; background: {palette.card_alt}; border: none; }}
    QTableView {{ background: {palette.surface}; alternate-background-color: {palette.card_alt};
        border: 1px solid {palette.border}; border-radius: 10px; gridline-color: transparent;
        selection-background-color: {palette.hover}; selection-color: {palette.text}; }}
    QTableView::item {{ padding: 6px 10px; border: none; }}
    QTableView::item:selected {{ background: {palette.hover}; color: {palette.text}; }}
    QHeaderView::section {{ background: {palette.card_alt}; color: {palette.muted}; border: none;
        border-bottom: 1px solid {palette.border}; padding: 12px 10px; font-size: 12px; font-weight: 600; }}
    QTableView QTableCornerButton::section {{ background: {palette.card_alt}; border: none; }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
    QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px; }}
    QScrollBar::handle {{ background: {palette.border}; border-radius: 3px; min-height: 28px; min-width: 28px; }}
    QScrollBar::handle:hover {{ background: {palette.muted}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
    QProgressBar {{ border: none; background: {palette.border}; border-radius: 3px; height: 6px; text-align: center; }}
    QProgressBar::chunk {{ background: {palette.accent}; border-radius: 3px; }}
    QStatusBar {{ background: {palette.bg}; border-top: 1px solid {palette.border}; padding: 4px 12px; }}
    QStatusBar::item {{ border: none; }}
    QMenuBar {{ background: {palette.bg}; padding: 3px 8px; }}
    QMenuBar::item:selected, QMenu::item:selected {{ background: {palette.hover}; }}
    QMenu {{ background: {palette.surface}; border: 1px solid {palette.border}; padding: 6px; }}
    QMenu::item {{ padding: 8px 22px; border-radius: 4px; }}
    QMenu::separator {{ height: 1px; background: {palette.border}; margin: 4px; }}
    QToolTip {{ background: {palette.surface}; color: {palette.text}; border: 1px solid {palette.border}; padding: 6px; }}
    QPlainTextEdit, QTextBrowser {{ background: {palette.surface}; border: 1px solid {palette.border};
        border-radius: 7px; padding: 8px; selection-background-color: {palette.accent}; }}
    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; }}
    QSplitter::handle {{ background: transparent; width: 10px; }}
    QTabWidget::pane {{ border: none; }}
    QTabBar::tab {{ background: transparent; padding: 10px 18px; color: {palette.muted};
        border-bottom: 2px solid transparent; }}
    QTabBar::tab:selected {{ color: {palette.accent}; border-bottom-color: {palette.accent}; }}
    """
