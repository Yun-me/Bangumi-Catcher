"""The "sync a collection" bar above the page stack.

Keeping this widget self-contained means the main window only reacts to two
signals (``fetch_requested`` / ``cancel_requested``) instead of wiring half a
dozen child widgets.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6 import QtCore, QtWidgets

from .widgets import Card


class FetchBar(Card):
    """Username input, subject-type selector, cache toggle and action buttons."""

    fetch_requested = QtCore.Signal()
    cancel_requested = QtCore.Signal()

    def __init__(self, subject_types: Mapping[int, str], parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.body.setContentsMargins(14, 12, 14, 12)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(10)

        self.user_input = QtWidgets.QLineEdit()
        self.user_input.setPlaceholderText("用户名 / UID / Bangumi 用户主页链接")
        self.user_input.setAccessibleName("Bangumi 用户")
        self.user_input.setClearButtonEnabled(True)
        self.user_input.returnPressed.connect(self.fetch_requested)
        row.addWidget(self.user_input, 1)

        self.history_button = QtWidgets.QPushButton("最近")
        self.history_menu = QtWidgets.QMenu(self.history_button)
        self.history_button.setMenu(self.history_menu)
        row.addWidget(self.history_button)

        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.setAccessibleName("收藏分类")
        for value, title in subject_types.items():
            self.type_combo.addItem(title, value)
        row.addWidget(self.type_combo)

        self.refresh_check = QtWidgets.QCheckBox("跳过缓存")
        self.refresh_check.setToolTip("忽略收藏缓存，重新从 Bangumi 同步。")
        row.addWidget(self.refresh_check)

        self.fetch_button = QtWidgets.QPushButton("同步收藏")
        self.fetch_button.setObjectName("Primary")
        self.fetch_button.clicked.connect(self.fetch_requested)
        row.addWidget(self.fetch_button)

        self.cancel_button = QtWidgets.QPushButton("取消任务")
        self.cancel_button.clicked.connect(self.cancel_requested)
        row.addWidget(self.cancel_button)

        self.body.addLayout(row)

    # -- state -----------------------------------------------------------

    def username(self) -> str:
        return self.user_input.text()

    def set_username(self, value: str) -> None:
        self.user_input.setText(value)

    def subject_type(self) -> int:
        return int(self.type_combo.currentData())

    def set_subject_type(self, value: int) -> None:
        index = self.type_combo.findData(value)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)

    def force_refresh(self) -> bool:
        return self.refresh_check.isChecked()

    def set_history(self, usernames: Sequence[str]) -> None:
        """Rebuild the recent-users menu and the input completer."""
        self.history_menu.clear()
        for username in usernames:
            self.history_menu.addAction(username, lambda value=username: self.set_username(value))
        if not usernames:
            self.history_menu.addAction("还没有历史用户").setEnabled(False)
        completer = QtWidgets.QCompleter(list(usernames), self.user_input)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.user_input.setCompleter(completer)

    def set_busy(self, busy: bool) -> None:
        for widget in (
            self.fetch_button,
            self.user_input,
            self.history_button,
            self.type_combo,
            self.refresh_check,
        ):
            widget.setEnabled(not busy)
        self.cancel_button.setVisible(busy)
        self.fetch_button.setVisible(not busy)
        self.cancel_button.setEnabled(True)


__all__ = ["FetchBar"]
