"""Subject detail pane shown next to the collection table."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.models import CollectionItem
from ..core.query import progress_label
from .widgets import Card, label


class DetailPanel(Card):
    """Read-only details for the selected collection item."""

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
        self.setObjectName("DetailPanel")
        self.setMinimumWidth(230)
        self.item: CollectionItem | None = None

        self.body.addWidget(label("SUBJECT DETAILS", "Eyebrow"))
        self.title = label("选择一部作品", "DetailTitle", True)
        self.body.addWidget(self.title)
        self.subtitle = label("在列表中单击查看详细信息。", "Muted", True)
        self.body.addWidget(self.subtitle)
        self.score = label("", "SectionTitle", True)
        self.body.addWidget(self.score)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.body.addWidget(self.progress)

        self.metadata = label("", "Muted", True)
        self.body.addWidget(self.metadata)
        self.body.addWidget(label("我的短评 / 标签", "Eyebrow"))

        self.comment = QtWidgets.QPlainTextEdit()
        self.comment.setReadOnly(True)
        self.comment.setMinimumHeight(100)
        self.comment.setMaximumHeight(170)
        self.comment.setPlaceholderText("选择作品后显示短评")
        self.body.addWidget(self.comment)

        self.body.addWidget(label("作品简介", "Eyebrow"))
        self.summary = QtWidgets.QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMinimumHeight(120)
        self.summary.setPlaceholderText("暂无简介")
        self.body.addWidget(self.summary, 1)

        self.open_button = QtWidgets.QPushButton("在 Bangumi 中打开  ↗")
        self.open_button.setObjectName("Primary")
        self.open_button.clicked.connect(self.open_subject)
        self.body.insertWidget(5, self.open_button)

        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.set_item(None)

    def set_item(self, item: CollectionItem | None) -> None:
        self.item = item
        self.open_button.setEnabled(item is not None and item.subject_id > 0)
        self.progress.setVisible(item is not None)
        if item is None:
            self.title.setText("选择一部作品")
            self.subtitle.setText("在列表中单击查看详细信息。")
            self.score.clear()
            self.metadata.clear()
            self.comment.clear()
            self.summary.clear()
            return

        subject = item.subject
        self.title.setText(item.subject_name)
        original = subject.name if subject and subject.name != item.subject_name else ""
        self.subtitle.setText(original or f"Bangumi #{item.subject_id}")
        own_score = str(item.rate) if item.rate else "未评分"
        site_score = f"{item.subject_score:.1f}" if item.subject_score else "暂无"
        self.score.setText(f"我的评分  {own_score}   /   全站  {site_score}")
        self.progress.setValue(round(item.completion_rate * 100))

        rank = (subject.rating.rank if subject and subject.rating else subject.rank) if subject else 0
        self.metadata.setText(
            "\n".join(
                [
                    f"{item.collection_type_name} · {progress_label(item)}",
                    f"发行：{subject.date if subject and subject.date else '未知'}  ·  排名：{rank or '—'}",
                    f"更新：{item.updated_at[:16].replace('T', ' ') or '未记录'}",
                ]
            )
        )
        self.comment.setPlainText(
            f"{item.comment or '还没有写短评。'}\n\n{'  /  '.join(item.tags) or '暂无标签'}"
        )
        self.summary.setPlainText(subject.summary if subject else "")

    def open_subject(self) -> None:
        if self.item and self.item.subject_id > 0:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(f"https://bgm.tv/subject/{self.item.subject_id}"))


__all__ = ["DetailPanel"]
