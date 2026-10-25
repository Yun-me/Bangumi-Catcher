"""Fetch service: orchestration, normalisation, caching and progress."""

from __future__ import annotations

import asyncio

import pytest

from bangumi_catcher.api import BangumiClient
from bangumi_catcher.core.config import AppConfig
from bangumi_catcher.core.errors import NotFoundError
from bangumi_catcher.services.fetch import (
    analyze_user_collection,
    fetch_and_analyze,
    fetch_user_collection,
)
from tests.fakes import FakeBangumiAPI, page_offsets


def make_config(tmp_path) -> AppConfig:
    config = AppConfig()
    config.cache.dir = str(tmp_path / "cache")
    config.api.trust_env = False
    config.collection.limit = 2
    config.collection.max_concurrent = 2
    return config


def client_factory(api: FakeBangumiAPI):
    return lambda config: BangumiClient(config, transport=api.transport())


def test_analyze_user_collection(sample_collection):
    report = analyze_user_collection(sample_collection, AppConfig())
    assert report.username == sample_collection.username
    assert report.total_items == len(sample_collection.items)
    assert report.tag_counts.get("原创") == 5


def test_fetch_returns_ordered_collection(tmp_path):
    api = FakeBangumiAPI(total=5)
    collection = asyncio.run(
        fetch_user_collection(
            make_config(tmp_path),
            "tester",
            client_factory=client_factory(api),
        )
    )
    assert [item.subject_id for item in collection.items] == [1, 2, 3, 4, 5]
    assert collection.username == "tester"
    assert api.subject_requests == []


def test_fetch_accepts_profile_url(tmp_path):
    api = FakeBangumiAPI(total=2)
    collection = asyncio.run(
        fetch_user_collection(
            make_config(tmp_path),
            "https://bgm.tv/user/tester?ref=nav",
            client_factory=client_factory(api),
        )
    )
    assert collection.username == "tester"


def test_fetch_enriches_entries_without_inline_subject(tmp_path):
    api = FakeBangumiAPI(total=4, omit_inline_subject=True)
    collection = asyncio.run(
        fetch_user_collection(
            make_config(tmp_path),
            "tester",
            client_factory=client_factory(api),
        )
    )
    assert sorted(api.subject_requests) == [1, 2, 3, 4]
    assert all(item.subject is not None for item in collection.items)
    assert collection.items[0].subject_score == 7.5


def test_second_fetch_hits_cache(tmp_path):
    api = FakeBangumiAPI(total=5)
    config = make_config(tmp_path)
    factory = client_factory(api)

    asyncio.run(fetch_user_collection(config, "tester", client_factory=factory))
    requests_before = len(page_offsets(api))
    asyncio.run(fetch_user_collection(config, "tester", client_factory=factory))
    assert len(page_offsets(api)) == requests_before


def test_force_refresh_refetches(tmp_path):
    api = FakeBangumiAPI(total=3)
    config = make_config(tmp_path)
    factory = client_factory(api)

    asyncio.run(fetch_user_collection(config, "tester", client_factory=factory))
    requests_before = len(page_offsets(api))
    asyncio.run(fetch_user_collection(config, "tester", force_refresh=True, client_factory=factory))
    assert len(page_offsets(api)) > requests_before


def test_fetch_and_analyze_returns_matching_report(tmp_path):
    api = FakeBangumiAPI(total=4)
    collection, report = asyncio.run(
        fetch_and_analyze(
            make_config(tmp_path),
            "tester",
            client_factory=client_factory(api),
        )
    )
    assert report.username == collection.username
    assert report.total_items == len(collection.items)


def test_progress_is_monotonic_and_completes(tmp_path):
    api = FakeBangumiAPI(total=6)
    fractions: list[float] = []

    def progress(fraction, message):
        fractions.append(fraction)
        assert 0.0 <= fraction <= 1.0
        assert message

    asyncio.run(
        fetch_user_collection(
            make_config(tmp_path),
            "tester",
            progress=progress,
            client_factory=client_factory(api),
        )
    )
    assert fractions == sorted(fractions)
    assert fractions[-1] == 1.0


def test_not_found_is_raised_for_private_users(tmp_path):
    import httpx

    class PrivateUserTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(404)

    def factory(config):
        return BangumiClient(config, transport=PrivateUserTransport())

    with pytest.raises(NotFoundError, match="用户不存在"):
        asyncio.run(fetch_user_collection(make_config(tmp_path), "tester", client_factory=factory))


def test_invalid_username_is_rejected_before_network(tmp_path):
    api = FakeBangumiAPI()
    with pytest.raises(ValueError):
        asyncio.run(
            fetch_user_collection(make_config(tmp_path), "显示昵称", client_factory=client_factory(api))
        )
    assert api.requests == []
