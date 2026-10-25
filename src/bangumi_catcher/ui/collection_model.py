"""Virtual collection rows and composable filters.

No Qt objects are created per cell: search text, display strings and sort keys
are computed once per collection by :mod:`bangumi_catcher.core.query`, and the
proxy sorts integer row indexes. This keeps sorting/filtering fast for tens of
thousands of entries and moves the actual rules into a Qt-free module.
"""

from __future__ import annotations

from PySide6 import QtCore

from ..core.models import UserCollection
from ..core.query import (
    HEADERS,
    CollectionQuery,
    display_row,
    search_haystack,
    sort_row,
)


class CollectionTableModel(QtCore.QAbstractTableModel):
    """Source model exposing one row per collection item."""

    HEADERS = HEADERS

    def __init__(self, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self.items: list = []
        self.search_text: list[str] = []
        self.display_values: list[tuple[str, ...]] = []
        self.sort_values: list[tuple[object, ...]] = []

    def set_collection(self, collection: UserCollection) -> None:
        self.beginResetModel()
        self.items = list(collection.items)
        self.search_text = [search_haystack(item) for item in self.items]
        self.display_values = [display_row(item) for item in self.items]
        self.sort_values = [sort_row(item) for item in self.items]
        self.endResetModel()

    # -- QAbstractTableModel --------------------------------------------

    def rowCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self.items)

    def columnCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self.HEADERS)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.DisplayRole):
        if (
            role == QtCore.Qt.DisplayRole
            and orientation == QtCore.Qt.Horizontal
            and 0 <= section < len(self.HEADERS)
        ):
            return self.HEADERS[section]
        return None

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.items):
            return None
        if role == QtCore.Qt.DisplayRole:
            return self.display_values[index.row()][index.column()]
        if role == QtCore.Qt.ToolTipRole:
            item = self.items[index.row()]
            return f"{item.subject_name}\n{' / '.join(item.tags)}\n{item.comment}".strip()
        if role == QtCore.Qt.TextAlignmentRole:
            alignment = QtCore.Qt.AlignLeft if index.column() == 0 else QtCore.Qt.AlignHCenter
            return int(QtCore.Qt.AlignVCenter | alignment)
        return None


class CollectionProxy(QtCore.QAbstractProxyModel):
    """Filtering + sorting proxy driven by a pure :class:`CollectionQuery`."""

    def __init__(self, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self.query = CollectionQuery()
        self._model: CollectionTableModel | None = None
        self._source_rows: list[int] = []
        self._proxy_rows: dict[int, int] = {}
        self._sort_column = -1
        self._sort_order = QtCore.Qt.AscendingOrder

    # -- source model plumbing ------------------------------------------

    def setSourceModel(self, model: CollectionTableModel | None) -> None:
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

    # -- proxy contract --------------------------------------------------

    def rowCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._source_rows)

    def columnCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        if self._model is None or (parent is not None and parent.isValid()):
            return 0
        return self._model.columnCount()

    def index(self, row: int, column: int, parent: QtCore.QModelIndex | None = None) -> QtCore.QModelIndex:
        valid_parent = parent is None or not parent.isValid()
        if valid_parent and 0 <= row < self.rowCount() and 0 <= column < self.columnCount():
            return self.createIndex(row, column)
        return QtCore.QModelIndex()

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        return QtCore.QModelIndex()

    def mapToSource(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if (
            not index.isValid()
            or index.model() is not self
            or self._model is None
            or not 0 <= index.row() < len(self._source_rows)
        ):
            return QtCore.QModelIndex()
        return self._model.index(self._source_rows[index.row()], index.column())

    def mapFromSource(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        is_source = index.isValid() and index.model() is self._model
        row = self._proxy_rows.get(index.row()) if is_source else None
        return self.index(row, index.column()) if row is not None else QtCore.QModelIndex()

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        if self._model is None:
            return None
        return self._model.data(self.mapToSource(index), role)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.DisplayRole):
        if self._model is None:
            return None
        return self._model.headerData(section, orientation, role)

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        return QtCore.Qt.NoItemFlags

    # -- filtering and sorting ------------------------------------------

    def set_filters(
        self, text: str = "", status: int | None = None, year: int | None = None, rating: str = "all"
    ) -> None:
        query = CollectionQuery(text=text, status=status, year=year, rating=rating)
        if query == self.query:
            return
        self.beginResetModel()
        self.query = query
        self._rebuild()
        self.endResetModel()

    def _matches(self, source_row: int) -> bool:
        if self._model is None:
            return False
        return self.query.matches(self._model.items[source_row], self._model.search_text[source_row])

    def _rebuild(self) -> None:
        self._source_rows = (
            [row for row in range(len(self._model.items)) if self._matches(row)]
            if self._model is not None
            else []
        )
        self._sort_rows()

    def _sort_rows(self) -> None:
        if self._model is not None and self._sort_column >= 0:
            values, column = self._model.sort_values, self._sort_column
            self._source_rows.sort(
                key=lambda row: values[row][column], reverse=self._sort_order == QtCore.Qt.DescendingOrder
            )
        else:
            self._source_rows.sort()
        self._proxy_rows = {source: row for row, source in enumerate(self._source_rows)}

    def sort(self, column: int, order: QtCore.Qt.SortOrder = QtCore.Qt.AscendingOrder) -> None:
        if not -1 <= column < self.columnCount() or (column, order) == (self._sort_column, self._sort_order):
            return
        self.layoutAboutToBeChanged.emit()
        persistent = self.persistentIndexList()
        source_rows = [self.mapToSource(index).row() for index in persistent]
        self._sort_column, self._sort_order = column, order
        self._sort_rows()
        self.changePersistentIndexList(
            persistent,
            [
                self.index(self._proxy_rows[source], index.column())
                for source, index in zip(source_rows, persistent)
            ],
        )
        self.layoutChanged.emit()


__all__ = ["CollectionProxy", "CollectionTableModel"]
