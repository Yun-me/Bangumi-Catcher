"""Virtual collection model and proxy contract (no window required)."""

from __future__ import annotations

import pytest
from PySide6 import QtCore, QtTest

from bangumi_catcher.core.query import HEADERS
from bangumi_catcher.ui.collection_model import CollectionProxy, CollectionTableModel
from tests.factories import make_collection


@pytest.fixture
def model(sample_collection):
    source = CollectionTableModel()
    source.set_collection(sample_collection)
    proxy = CollectionProxy()
    proxy.setSourceModel(source)
    return source, proxy


def test_virtual_model_and_numeric_sort(model):
    source, proxy = model
    assert source.rowCount() == 5
    assert source.columnCount() == 7
    assert source.rowCount(source.index(0, 0)) == 0
    proxy.sort(3, QtCore.Qt.DescendingOrder)
    assert proxy.index(0, 3).data() == "8"
    assert proxy.mapToSource(proxy.index(0, 0)).row() == 0
    assert source.index(1, 3).data() == "—"


def test_headers_match_core_contract(model):
    source, proxy = model
    assert tuple(source.HEADERS) == HEADERS
    assert [proxy.headerData(column, QtCore.Qt.Horizontal) for column in range(7)] == list(HEADERS)


def test_proxy_preserves_selection_and_round_trips_indexes(model):
    source, proxy = model
    persistent = QtCore.QPersistentModelIndex(proxy.index(0, 0))
    proxy.sort(3, QtCore.Qt.AscendingOrder)
    assert proxy.mapToSource(persistent).row() == 0
    for row in range(proxy.rowCount()):
        index = proxy.index(row, 1)
        assert proxy.mapFromSource(proxy.mapToSource(index)) == index
    proxy.set_filters(status=1)
    assert not persistent.isValid()
    assert proxy.rowCount() == 1
    assert not proxy.mapFromSource(source.index(0, 0)).isValid()
    source.set_collection(make_collection([]))
    assert proxy.rowCount() == 0


def test_proxy_obeys_qt_model_contract(model, sample_collection):
    source, proxy = model
    messages: list[str] = []
    previous = QtCore.qInstallMessageHandler(lambda kind, context, message: messages.append(message))
    try:
        tester = QtTest.QAbstractItemModelTester(
            proxy, QtTest.QAbstractItemModelTester.FailureReportingMode.Warning
        )
        proxy.sort(3, QtCore.Qt.DescendingOrder)
        proxy.set_filters(status=2)
        proxy.sort(1, QtCore.Qt.AscendingOrder)
        proxy.set_filters("nothing matches")
        source.set_collection(sample_collection)
        assert tester.model() is proxy
    finally:
        QtCore.qInstallMessageHandler(previous)
    assert not messages


def test_sort_and_filter_do_not_request_individual_cell_data(model, monkeypatch):
    source, proxy = model

    def unexpected(*args, **kwargs):
        pytest.fail("Sorting and filtering should use cached row indexes, not Qt cell callbacks")

    monkeypatch.setattr(source, "data", unexpected)
    proxy.sort(3, QtCore.Qt.DescendingOrder)
    proxy.set_filters("原创", status=2)
    assert proxy.rowCount() == 3


def test_combined_filters_match_original_title_tags_and_comment(model, sample_collection):
    source, proxy = model
    sample_collection.items[0].comment = "这是一次很棒的旅行"
    source.set_collection(sample_collection)
    proxy.set_filters("ANIME1 原创 旅行", status=2, year=2020, rating="8")
    assert proxy.rowCount() == 1
    proxy.set_filters(status=2, year=2020, rating="unrated")
    assert proxy.rowCount() == 1
    assert proxy.mapToSource(proxy.index(0, 0)).row() == 1
    proxy.set_filters("不存在")
    assert proxy.rowCount() == 0
