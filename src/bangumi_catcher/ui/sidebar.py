"""Sidebar navigation with the product wordmark and secondary actions."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6 import QtCore, QtWidgets

from .. import __version__
from .icons import icon
from .navigation import Page
from .widgets import label

_INACTIVE_ICON = "#C3D8CD"
_ACTIVE_ICON = "#173C31"


class Sidebar(QtWidgets.QFrame):
    """Fixed navigation rail.

    Emits ``navigate_requested(index)`` for page buttons and dedicated signals
    for the secondary settings/log actions.
    """

    navigate_requested = QtCore.Signal(int)
    settings_requested = QtCore.Signal()
    logs_requested = QtCore.Signal()

    def __init__(self, pages: Sequence[Page], parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setMinimumWidth(180)
        self.pages = tuple(pages)

        column = QtWidgets.QVBoxLayout(self)
        column.setContentsMargins(18, 30, 18, 22)
        column.setSpacing(8)
        column.addWidget(label("BANGUMI", "Brand"))
        column.addWidget(label("C A T C H E R", "SideMuted"))
        column.addSpacing(34)
        column.addWidget(label("个人工作台", "SideMuted"))
        column.addSpacing(4)

        self.nav_buttons: list[QtWidgets.QPushButton] = []
        self.nav_group = QtWidgets.QButtonGroup(self)
        for index, page in enumerate(self.pages):
            button = QtWidgets.QPushButton(f"  {page.title}")
            button.setCheckable(True)
            button.setIconSize(QtCore.QSize(19, 19))
            button.setIcon(icon(page.icon, _INACTIVE_ICON))
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
            column.addWidget(button)
        self.nav_group.idClicked.connect(self.navigate_requested)

        column.addStretch()
        self.user_summary = label("你的收藏，你的节奏。", "SideMuted", True)
        column.addWidget(self.user_summary)
        column.addSpacing(18)

        self.settings_button = QtWidgets.QPushButton("  偏好设置")
        self.settings_button.setIcon(icon("settings", _INACTIVE_ICON))
        self.settings_button.clicked.connect(self.settings_requested)
        column.addWidget(self.settings_button)

        self.logs_button = QtWidgets.QPushButton("  运行日志")
        self.logs_button.setIcon(icon("log", _INACTIVE_ICON))
        self.logs_button.clicked.connect(self.logs_requested)
        column.addWidget(self.logs_button)

        column.addSpacing(10)
        column.addWidget(label(f"v{__version__}  ·  本地优先 / 只读分析", "SideMuted"))

    def set_active(self, index: int) -> None:
        """Check the button for ``index`` and recolour all navigation icons."""
        for position, button in enumerate(self.nav_buttons):
            button.setChecked(position == index)
            button.setIcon(
                icon(self.pages[position].icon, _ACTIVE_ICON if position == index else _INACTIVE_ICON)
            )

    def set_user_summary(self, text: str) -> None:
        self.user_summary.setText(text)


__all__ = ["Sidebar"]
