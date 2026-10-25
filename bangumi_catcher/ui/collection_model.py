"""Virtual collection rows and composable filters, without per-cell Qt objects."""

from __future__ import annotations

from PySide6 import QtCore

from ..core.models import UserCollection
from .widgets import progress_label


class CollectionTableModel(QtCore.QAbstractTableModel):
    HEADERS = ("作品", "年份", "收藏状态", "我的评分", "全站均分", "进度", "最近更新")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.search_text: list[str] = []
        self.display_values: list[tuple] = []
        self.sort_values: list[tuple] = []

    def set_collection(self, collection: UserCollection) -> None:
        self.beginResetModel()
        self.items = collection.items
        self.search_text = []
        self.display_values = []
        self.sort_values = []
        for item in self.items:
            subject = item.subject
            self.search_text.append(" ".join([
                str(item.subject_id), item.subject_name, subject.name if subject else "",
                subject.name_cn if subject else "", " ".join(item.tags), item.comment,
            ]).casefold())
            self.display_values.append((
                item.subject_name, str(item.subject_year or "—"), item.collection_type_name,
                str(item.rate) if item.rate else "—",
                f"{item.subject_score:.1f}" if item.subject_score else "—",
                progress_label(item), item.updated_at[:10] or "—",
            ))
            self.sort_values.append((
                item.subject_name.casefold(), item.subject_year or 0, item.type, item.rate,
                item.subject_score, item.completion_rate, item.updated_at,
            ))
        self.endResetModel()

    def rowCount(self, parent=None):
        return 0 if parent is not None and parent.isValid() else len(self.items)

    def columnCount(self, parent=None):
        return 0 if parent is not None and parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal and 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        return None

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.items):
            return None
        if role == QtCore.Qt.DisplayRole:
            return self.display_values[index.row()][index.column()]
        if role == QtCore.Qt.ToolTipRole:
            item = self.items[index.row()]
            return f"{item.subject_name}\n{' / '.join(item.tags)}\n{item.comment}".strip()
        if role == QtCore.Qt.TextAlignmentRole:
            return int(QtCore.Qt.AlignVCenter | (QtCore.Qt.AlignLeft if index.column() == 0 else QtCore.Qt.AlignHCenter))
        return None


class CollectionProxy(QtCore.QAbstractProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tokens: list[str] = []
        self.status: int | None = None
        self.year: int | None = None
        self.rating = "all"
        self._model: CollectionTableModel | None = None
        self._source_rows: list[int] = []
        self._proxy_rows: dict[int, int] = {}
        self._sort_column = -1
        self._sort_order = QtCore.Qt.AscendingOrder

    def setSourceModel(self, model):
        self.beginResetModel()
        if self._model is not None:
            self._model.modelAboutToBeReset.disconnect(self._source_resetting)
            self._model.modelReset.disconnect(self._source_reset)
        super().setSourceModel(model)
        self._model = model
        if model is not None:
            model.modelAboutToBeReset.connect(self._source_resetting)
            model.modelReset.connect(self._source_reset)
        self._rebuild()
        self.endResetModel()

    def _source_resetting(self) -> None:
        self.beginResetModel()

    def _source_reset(self) -> None:
        self._rebuild()
        self.endResetModel()

    def rowCount(self, parent=None):
        return 0 if parent is not None and parent.isValid() else len(self._source_rows)

    def columnCount(self, parent=None):
        if self._model is None or (parent is not None and parent.isValid()):
            return 0
        return self._model.columnCount()

    def index(self, row, column, parent=None):
        if (parent is None or not parent.isValid()) and 0 <= row < self.rowCount() and 0 <= column < self.columnCount():
            return self.createIndex(row, column)
        return QtCore.QModelIndex()

    def parent(self, index):
        return QtCore.QModelIndex()

    def mapToSource(self, index):
        if (not index.isValid() or index.model() != self or self._model is None
                or not 0 <= index.row() < len(self._source_rows)):
            return QtCore.QModelIndex()
        return self._model.index(self._source_rows[index.row()], index.column())

    def mapFromSource(self, index):
        row = self._proxy_rows.get(index.row()) if index.isValid() and index.model() == self._model else None
        return self.index(row, index.column()) if row is not None else QtCore.QModelIndex()

    def data(self, index, role=QtCore.Qt.DisplayRole):
        return self._model.data(self.mapToSource(index), role) if self._model is not None else None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        return self._model.headerData(section, orientation, role) if self._model is not None else None

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        return QtCore.Qt.NoItemFlags

    def set_filters(self, text: str = "", status: int | None = None,
                    year: int | None = None, rating: str = "all") -> None:
        tokens = text.casefold().split()
        if (tokens, status, year, rating) == (self.tokens, self.status, self.year, self.rating):
            return
        self.beginResetModel()
        self.tokens = tokens
        self.status, self.year, self.rating = status, year, rating
        self._rebuild()
        self.endResetModel()

    def _matches(self, source_row):
        model = self._model
        item = model.items[source_row]
        if self.status is not None and item.type != self.status:
            return False
        if self.year is not None and (item.subject_year or 0) != self.year:
            return False
        if self.rating == "rated" and item.rate == 0:
            return False
        if self.rating == "unrated" and item.rate != 0:
            return False
        if self.rating.isdigit() and item.rate < int(self.rating):
            return False
        return all(token in model.search_text[source_row] for token in self.tokens)

    def _rebuild(self) -> None:
        self._source_rows = ([row for row in range(len(self._model.items)) if self._matches(row)]
                             if self._model is not None else [])
        self._sort_rows()

    def _sort_rows(self) -> None:
        if self._model is not None and self._sort_column >= 0:
            values, column = self._model.sort_values, self._sort_column
            self._source_rows.sort(key=lambda row: values[row][column],
                                   reverse=self._sort_order == QtCore.Qt.DescendingOrder)
        else:
            self._source_rows.sort()
        self._proxy_rows = {source: row for row, source in enumerate(self._source_rows)}

    def sort(self, column, order=QtCore.Qt.AscendingOrder):
        if not -1 <= column < self.columnCount() or (column, order) == (self._sort_column, self._sort_order):
            return
        self.layoutAboutToBeChanged.emit()
        persistent = self.persistentIndexList()
        source_rows = [self.mapToSource(index).row() for index in persistent]
        self._sort_column, self._sort_order = column, order
        self._sort_rows()
        self.changePersistentIndexList(persistent, [self.index(self._proxy_rows[source], index.column())
                                                   for source, index in zip(source_rows, persistent)])
        self.layoutChanged.emit()
