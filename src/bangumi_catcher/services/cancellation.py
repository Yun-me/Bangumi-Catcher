"""Cooperative cancellation for blocking worker threads.

The desktop runs async fetches inside a ``QThread``. A ``threading.Event`` is
the only signal that can be set safely from the UI thread, so helpers here
bridge that event into asyncio and raise :class:`OperationCancelled`.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

from ..core.errors import OperationCancelled

T = TypeVar("T")

CANCEL_POLL_SECONDS = 0.05
"""How often the monitor checks the event while awaiting a coroutine."""


def check_cancelled(cancel: threading.Event) -> None:
    """Raise :class:`OperationCancelled` when ``cancel`` is set."""
    if cancel.is_set():
        raise OperationCancelled("已取消")


def run_cancellable(coroutine: Coroutine[Any, Any, T], cancel: threading.Event) -> T:
    """Run ``coroutine`` to completion, aborting when ``cancel`` is set.

    Cancellation also interrupts an in-flight ``await`` by cancelling the
    asyncio task, which lets httpx close its sockets instead of leaking them.

    Raises:
        OperationCancelled: cancellation was requested before or during the run.
    """
    if cancel.is_set():
        coroutine.close()
        check_cancelled(cancel)

    async def run() -> T:
        task = asyncio.create_task(coroutine)

        async def monitor() -> None:
            while not task.done():
                if cancel.is_set():
                    task.cancel()
                    return
                await asyncio.sleep(CANCEL_POLL_SECONDS)

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


__all__ = ["CANCEL_POLL_SECONDS", "check_cancelled", "run_cancellable"]
