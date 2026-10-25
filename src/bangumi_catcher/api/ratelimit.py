"""Minimum interval between request starts.

Concurrency is bounded separately by the client's semaphores; this limiter
controls *spacing*. With ``min_interval == 0`` (the default) it is a no-op.
"""

from __future__ import annotations

import asyncio


class RateLimiter:
    """Serialise request starts with a configurable minimum interval."""

    def __init__(self, min_interval: float):
        self.min_interval = max(0.0, float(min_interval))
        self._lock: asyncio.Lock | None = None  # created lazily to bind the right loop
        self._next_at = 0.0

    async def acquire(self) -> None:
        if self.min_interval <= 0:
            return
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            wait = self._next_at - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = loop.time()
            self._next_at = max(now, self._next_at) + self.min_interval


__all__ = ["RateLimiter"]
