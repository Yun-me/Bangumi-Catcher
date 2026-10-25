import asyncio

import httpx
import pytest

from bangumi_catcher.core.api import BangumiClient
from bangumi_catcher.core.config import AppConfig
from bangumi_catcher.core.exceptions import APIError


def _entry(subject_id):
    return {"subject_id": subject_id, "type": 2, "subject": {"id": subject_id, "name": f"作品{subject_id}"}}


def test_pages_use_bounded_workers_and_preserve_order(tmp_path):
    config = AppConfig()
    config.cache.dir = str(tmp_path)
    config.collection.limit = 1
    config.collection.max_concurrent = 3
    peak_tasks = 0

    async def request(req):
        nonlocal peak_tasks
        peak_tasks = max(peak_tasks, len(asyncio.all_tasks()))
        offset = int(req.url.params["offset"])
        await asyncio.sleep(0.001)
        return httpx.Response(200, json={"total": 100, "data": [_entry(offset + 1)]})

    async def run():
        async with BangumiClient(config) as client:
            await client._client.aclose()
            client._client = httpx.AsyncClient(transport=httpx.MockTransport(request))
            collection = await client.fetch_collection("tester")
            assert [item.subject_id for item in collection.items] == list(range(1, 101))
            assert collection.subject_type == 2

    asyncio.run(run())
    assert peak_tasks <= config.collection.max_concurrent + 1


def test_page_failure_awaits_cancelled_siblings(tmp_path):
    config = AppConfig()
    config.cache.dir = str(tmp_path)
    config.collection.limit = 1
    config.collection.max_concurrent = 3
    pending = 0

    async def request(req):
        nonlocal pending
        offset = int(req.url.params["offset"])
        if offset == 0:
            return httpx.Response(200, json={"total": 10, "data": [_entry(1)]})
        if offset == 1:
            await asyncio.sleep(0.01)
            return httpx.Response(403)
        pending += 1
        try:
            await asyncio.sleep(30)
        finally:
            pending -= 1

    async def run():
        async with BangumiClient(config) as client:
            await client._client.aclose()
            client._client = httpx.AsyncClient(transport=httpx.MockTransport(request))
            with pytest.raises(APIError):
                await client.fetch_collection("tester")
            assert pending == 0
            assert client._cache.size == 0

    asyncio.run(run())


def test_disabled_cache_does_not_read_or_write_subjects(tmp_path):
    config = AppConfig()
    config.cache.dir = str(tmp_path)
    config.cache.enabled = False

    async def run():
        async with BangumiClient(config) as client:
            client._cache.set_subject(1, {"id": 1, "name": "old"})
            await client._client.aclose()
            client._client = httpx.AsyncClient(transport=httpx.MockTransport(
                lambda req: httpx.Response(200, json={"id": 1, "name": "fresh"})))
            assert (await client.get_subject(1)).name == "fresh"
            assert client._cache.get_subject(1)["name"] == "old"

    asyncio.run(run())
