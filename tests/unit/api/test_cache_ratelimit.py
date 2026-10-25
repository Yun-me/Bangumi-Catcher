"""Rate limiter spacing and cache key stability."""

from __future__ import annotations

import asyncio
import time

from bangumi_catcher.api.cache import Cache
from bangumi_catcher.api.ratelimit import RateLimiter


def test_rate_limiter_zero_is_noop():
    limiter = RateLimiter(0.0)

    async def run():
        for _ in range(5):
            await limiter.acquire()

    started = time.perf_counter()
    asyncio.run(run())
    assert time.perf_counter() - started < 0.05


def test_rate_limiter_spaces_requests():
    interval = 0.05
    limiter = RateLimiter(interval)

    async def run():
        for _ in range(3):
            await limiter.acquire()

    started = time.perf_counter()
    asyncio.run(run())
    elapsed = time.perf_counter() - started
    assert elapsed >= interval * 2 * 0.8


def test_rate_limiter_negative_clamped():
    assert RateLimiter(-1.0).min_interval == 0.0


def test_collection_key_includes_type():
    all_key = Cache.collection_key("alice", 2)
    wish_key = Cache.collection_key("alice", 2, 1)
    assert all_key.endswith(":all")
    assert wish_key.endswith(":ct1")
    assert all_key != wish_key


def test_collection_key_stable_for_same_args():
    assert Cache.collection_key("bob", 2, None) == Cache.collection_key("bob", 2, None)


def test_cache_round_trip_and_clear(tmp_path):
    with Cache(tmp_path) as cache:
        cache.set_collection("alice", 2, {"items": []})
        assert cache.get_collection("alice", 2) == {"items": []}
        cache.set_subject(7, {"id": 7})
        assert cache.get_subject(7) == {"id": 7}
        assert cache.size == 2
        cache.clear()
        assert cache.size == 0


def test_long_cache_key_is_hashed():
    key = "x" * 200
    hashed = Cache._hash_key(key)
    assert len(hashed) <= 80
    assert hashed.startswith("x" * 60)
