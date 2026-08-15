"""v1.2.1 修复回归测试：请求限速器 + 缓存键含收藏类型。

均用 asyncio.run 跑协程，避免引入 pytest-asyncio 依赖。
"""
import asyncio
import time

from bangumi_catcher.core.api import _RateLimiter
from bangumi_catcher.core.cache import Cache

# ---------------- _RateLimiter ----------------

def test_rate_limiter_zero_is_noop():
    """min_interval=0（默认）时不应产生任何等待。"""
    limiter = _RateLimiter(0.0)

    async def run():
        for _ in range(5):
            await limiter.acquire()

    t0 = time.perf_counter()
    asyncio.run(run())
    assert time.perf_counter() - t0 < 0.05


def test_rate_limiter_spaces_requests():
    """min_interval>0 时连续请求之间至少间隔该时长。"""
    interval = 0.05
    limiter = _RateLimiter(interval)

    async def run():
        for _ in range(3):          # 首次免等，其后两次各等 ~interval
            await limiter.acquire()

    t0 = time.perf_counter()
    asyncio.run(run())
    elapsed = time.perf_counter() - t0
    assert elapsed >= interval * 2 * 0.8   # 留出调度余量，仍能证明确实等待过


def test_rate_limiter_negative_clamped():
    assert _RateLimiter(-1.0).min_interval == 0.0


# ---------------- Cache key 含 collection_type ----------------

def test_collection_key_includes_type():
    # 「全部」与「仅想看(1)」必须落到不同缓存键，避免互相覆盖
    k_all = Cache.collection_key("alice", 2)
    k_wish = Cache.collection_key("alice", 2, 1)
    assert k_all.endswith(":all")
    assert k_wish.endswith(":ct1")
    assert k_all != k_wish


def test_collection_key_stable_for_same_args():
    assert Cache.collection_key("bob", 2, None) == Cache.collection_key("bob", 2, None)
