"""Client lifecycle: bounded concurrency, failure cleanup, cache and retries.

All requests go through the in-process fake transport from ``tests.fakes``.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from bangumi_catcher.api import BangumiClient
from bangumi_catcher.core.config import AppConfig
from bangumi_catcher.core.errors import APIError, EmptyCollectionError, NotFoundError, OperationCancelled
from tests.fakes import FakeBangumiAPI, page_offsets


def make_config(tmp_path, *, limit: int = 1, max_concurrent: int = 3) -> AppConfig:
    config = AppConfig()
    config.cache.dir = str(tmp_path / "cache")
    config.api.trust_env = False
    config.collection.limit = limit
    config.collection.max_concurrent = max_concurrent
    return config


def test_pages_use_bounded_workers_and_preserve_order(tmp_path):
    api = FakeBangumiAPI(total=100, delay=0.001)
    config = make_config(tmp_path)

    async def run():
        async with BangumiClient(config, transport=api.transport()) as client:
            collection = await client.fetch_collection("tester")
            assert [item.subject_id for item in collection.items] == list(range(1, 101))
            assert collection.subject_type == 2
            assert collection.total == 100

    asyncio.run(run())
    assert api.peak_in_flight <= config.collection.max_concurrent
    assert api.peak_in_flight >= 2
    assert page_offsets(api)[0] == 0


def test_page_failure_awaits_cancelled_siblings(tmp_path):
    api = FakeBangumiAPI(total=5, fail_offsets=(1,), slow_offsets=(2, 3, 4))
    config = make_config(tmp_path)

    async def run():
        async with BangumiClient(config, transport=api.transport()) as client:
            with pytest.raises(APIError):
                await client.fetch_collection("tester")
            assert api.in_flight == 0
            assert client.cache.size == 0

    asyncio.run(run())


def test_disabled_cache_does_not_read_or_write_subjects(tmp_path):
    api = FakeBangumiAPI(total=1)
    config = make_config(tmp_path)
    config.cache.enabled = False

    async def run():
        async with BangumiClient(config, transport=api.transport()) as client:
            client.cache.set_subject(1, {"id": 1, "name": "old"})
            subject = await client.get_subject(1)
            assert subject.name == "作品1"
            assert client.cache.get_subject(1)["name"] == "old"

    asyncio.run(run())


def test_collection_is_served_from_cache_on_second_client(tmp_path):
    api = FakeBangumiAPI(total=5)
    config = make_config(tmp_path, limit=2)

    async def run():
        async with BangumiClient(config, transport=api.transport()) as first_client:
            first = await first_client.fetch_collection("tester")
        requests_before = len(page_offsets(api))
        async with BangumiClient(config, transport=api.transport()) as second_client:
            second = await second_client.fetch_collection("tester")
        assert second == first
        assert len(page_offsets(api)) == requests_before

    asyncio.run(run())


def test_force_refresh_bypasses_collection_cache(tmp_path):
    api = FakeBangumiAPI(total=2)
    config = make_config(tmp_path, limit=2)

    async def run():
        async with BangumiClient(config, transport=api.transport()) as client:
            await client.fetch_collection("tester")
            requests_before = len(page_offsets(api))
            await client.fetch_collection("tester", force_refresh=True)
            assert len(page_offsets(api)) > requests_before

    asyncio.run(run())


def test_missing_subject_details_are_skipped(tmp_path):
    api = FakeBangumiAPI(total=3, omit_inline_subject=True, missing_subjects=(2,))
    config = make_config(tmp_path, limit=3)

    async def run():
        async with BangumiClient(config, transport=api.transport()) as client:
            collection = await client.fetch_collection("tester")
            assert [item.subject_id for item in collection.items] == [1, 2, 3]
            assert collection.items[0].subject is not None
            assert collection.items[1].subject is None
            assert sorted(api.subject_requests) == [1, 2, 3]

    asyncio.run(run())


def test_empty_collection_raises(tmp_path):
    api = FakeBangumiAPI(total=0)
    config = make_config(tmp_path)

    async def run():
        async with BangumiClient(config, transport=api.transport()) as client:
            with pytest.raises(EmptyCollectionError):
                await client.fetch_collection("tester")

    asyncio.run(run())


def test_cancel_check_aborts_before_any_request(tmp_path):
    api = FakeBangumiAPI(total=5)
    config = make_config(tmp_path)

    async def run():
        async with BangumiClient(config, transport=api.transport()) as client:
            with pytest.raises(OperationCancelled):
                await client.fetch_collection("tester", cancel_check=lambda: True)

    asyncio.run(run())
    assert page_offsets(api) == []


def test_server_errors_are_retried(tmp_path):
    class FlakyTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.calls = 0

        async def handle_async_request(self, request):
            self.calls += 1
            if self.calls < 3:
                return httpx.Response(500)
            return httpx.Response(200, json={"id": 1, "name": "ok"})

    config = make_config(tmp_path)
    config.api.max_retries = 3
    config.api.retry_delay = 0
    transport = FlakyTransport()

    async def run():
        async with BangumiClient(config, transport=transport) as client:
            assert (await client.get_subject(1)).name == "ok"

    asyncio.run(run())
    assert transport.calls == 3


def test_404_is_not_retried(tmp_path):
    class MissingTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.calls = 0

        async def handle_async_request(self, request):
            self.calls += 1
            return httpx.Response(404)

    config = make_config(tmp_path)
    transport = MissingTransport()

    async def run():
        async with BangumiClient(config, transport=transport) as client:
            with pytest.raises(NotFoundError, match="条目不存在"):
                await client.get_subject(42)

    asyncio.run(run())
    assert transport.calls == 1
