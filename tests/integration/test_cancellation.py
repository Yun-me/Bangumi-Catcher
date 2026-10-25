"""Cooperative cancellation across the thread/asyncio boundary."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from bangumi_catcher.core.errors import OperationCancelled
from bangumi_catcher.services.cancellation import check_cancelled, run_cancellable


def test_cancellation_interrupts_inflight_await():
    cancel = threading.Event()
    cleanup = threading.Event()

    async def pending_request():
        try:
            await asyncio.sleep(30)
        finally:
            cleanup.set()

    timer = threading.Timer(0.1, cancel.set)
    timer.start()
    started = time.perf_counter()
    try:
        with pytest.raises(OperationCancelled):
            run_cancellable(pending_request(), cancel)
    finally:
        timer.cancel()
    assert cleanup.is_set()
    assert time.perf_counter() - started < 2


def test_cancellable_task_returns_value():
    async def operation():
        return 42

    assert run_cancellable(operation(), threading.Event()) == 42


def test_cancel_before_start():
    async def operation():
        await asyncio.sleep(30)

    cancel = threading.Event()
    cancel.set()
    with pytest.raises(OperationCancelled):
        run_cancellable(operation(), cancel)


def test_cancel_before_start_does_not_execute_operation():
    executed = []

    async def operation():
        executed.append(True)
        return "cached result"

    cancel = threading.Event()
    cancel.set()
    with pytest.raises(OperationCancelled):
        run_cancellable(operation(), cancel)
    assert not executed


def test_check_cancelled_is_a_noop_when_unset():
    check_cancelled(threading.Event())


def test_check_cancelled_raises_when_set():
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(OperationCancelled):
        check_cancelled(cancel)
