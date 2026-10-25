"""Logging buffer used by the desktop log viewer."""

from __future__ import annotations

import logging

from bangumi_catcher.observability import LogBuffer, attach_log_buffer, log_buffer


def _record(message: str) -> logging.LogRecord:
    return logging.LogRecord("test", logging.INFO, "", 0, message, (), None)


def test_log_buffer_is_bounded():
    buffer = LogBuffer(capacity=1000)
    for number in range(1100):
        buffer.handle(_record(str(number)))
    assert len(buffer.lines) == 1000
    assert buffer.lines[0] == "100"


def test_log_buffer_custom_capacity():
    buffer = LogBuffer(capacity=3)
    for number in range(5):
        buffer.handle(_record(str(number)))
    assert buffer.lines == ["2", "3", "4"]


def test_attach_log_buffer_is_idempotent():
    root = logging.getLogger()
    try:
        attach_log_buffer()
        attach_log_buffer()
        assert root.handlers.count(log_buffer) == 1
    finally:
        root.removeHandler(log_buffer)
