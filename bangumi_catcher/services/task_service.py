"""Cooperative cancellation, including in-flight HTTP requests and retry sleeps."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine

from ..core.exceptions import OperationCancelled


def check_cancelled(cancel: threading.Event) -> None:
    if cancel.is_set():
        raise OperationCancelled("已取消")


def run_cancellable(coroutine: Coroutine, cancel: threading.Event):
    if cancel.is_set():
        coroutine.close()
        check_cancelled(cancel)

    async def run():
        task = asyncio.create_task(coroutine)

        async def monitor():
            while not task.done():
                if cancel.is_set():
                    task.cancel()
                    return
                await asyncio.sleep(0.05)

        monitor_task = asyncio.create_task(monitor())
        try:
            result = await task
            check_cancelled(cancel)
            return result
        except asyncio.CancelledError as exc:
            raise OperationCancelled("已取消") from exc
        finally:
            monitor_task.cancel()
            await asyncio.gather(monitor_task, return_exceptions=True)

    return asyncio.run(run())
