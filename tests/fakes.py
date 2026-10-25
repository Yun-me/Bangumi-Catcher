"""A deterministic, in-process fake of the Bangumi v0 API.

The fake implements just enough of ``/v0/users/{user}/collections`` and
``/v0/subjects/{id}`` to exercise pagination, enrichment, caching, retries and
cancellation without touching the network. It is an async transport so tests can
observe real concurrency (``peak_in_flight``).
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

SLIM_TEMPLATE: dict[str, Any] = {
    "id": 1,
    "name": "Slim Subject",
    "name_cn": "精简条目",
    "date": "2020-04-05",
    "score": 7.5,
    "rank": 120,
    "eps": 12,
    "images": {"large": "https://example.invalid/large.jpg"},
    "short_summary": "列表内联简介",
}

FULL_TEMPLATE: dict[str, Any] = {
    "id": 1,
    "name": "Full Subject",
    "name_cn": "完整条目",
    "date": "2020-04-05",
    "summary": "完整简介",
    "platform": "TV",
    "eps": 12,
    "total_episodes": 12,
    "rating": {"score": 7.5, "total": 5000, "rank": 120},
    "images": {"large": "https://example.invalid/large.jpg"},
}


def slim_subject(subject_id: int) -> dict[str, Any]:
    return {**SLIM_TEMPLATE, "id": subject_id, "name": f"作品{subject_id}", "name_cn": f"动画{subject_id}"}


def full_subject(subject_id: int) -> dict[str, Any]:
    return {**FULL_TEMPLATE, "id": subject_id, "name": f"作品{subject_id}", "name_cn": f"动画{subject_id}"}


class _FakeTransport(httpx.AsyncBaseTransport):
    def __init__(self, api: FakeBangumiAPI):
        self.api = api

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return await self.api.handle(request)


class FakeBangumiAPI:
    """Configurable fake API used by integration tests."""

    def __init__(
        self,
        *,
        total: int = 5,
        page_size: int = 2,
        user: str = "tester",
        delay: float = 0.0,
        slow_offsets: tuple[int, ...] = (),
        slow_delay: float = 30.0,
        fail_offsets: tuple[int, ...] = (),
        omit_inline_subject: bool = False,
        missing_subjects: tuple[int, ...] = (),
    ):
        self.total = total
        self.page_size = page_size
        self.user = user
        self.delay = delay
        self.slow_offsets = set(slow_offsets)
        self.slow_delay = slow_delay
        self.fail_offsets = set(fail_offsets)
        self.omit_inline_subject = omit_inline_subject
        self.missing_subjects = set(missing_subjects)

        self.requests: list[httpx.Request] = []
        self.subject_requests: list[int] = []
        self.in_flight = 0
        self.peak_in_flight = 0

    # -- transport -------------------------------------------------------

    def transport(self) -> httpx.AsyncBaseTransport:
        return _FakeTransport(self)

    # -- routing ---------------------------------------------------------

    async def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path

        if path.startswith("/v0/users/") and path.endswith("/collections"):
            return await self._collection_page(request)
        if path.startswith("/v0/subjects/"):
            return await self._subject(request)
        return httpx.Response(404, json={"message": "not found"})

    async def _collection_page(self, request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", 0))
        limit = int(request.url.params.get("limit", self.page_size))
        if offset in self.fail_offsets:
            return httpx.Response(403, json={"message": "forbidden"})

        self.in_flight += 1
        self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
        try:
            if offset in self.slow_offsets:
                await asyncio.sleep(self.slow_delay)
            elif self.delay:
                await asyncio.sleep(self.delay)
            end = min(offset + limit, self.total)
            entries = []
            for index in range(offset, end):
                subject_id = index + 1
                entry: dict[str, Any] = {
                    "subject_id": subject_id,
                    "type": 2,
                    "rate": 8 if subject_id % 2 else 0,
                    "comment": "",
                    "tags": [{"name": "原创"}],
                    "ep_status": 12,
                    "updated_at": "2026-01-01T00:00:00+08:00",
                }
                if not self.omit_inline_subject:
                    entry["subject"] = slim_subject(subject_id)
                entries.append(entry)
        finally:
            self.in_flight -= 1

        return httpx.Response(200, json={"total": self.total, "data": entries})

    async def _subject(self, request: httpx.Request) -> httpx.Response:
        subject_id = int(request.url.path.rsplit("/", 1)[-1])
        self.subject_requests.append(subject_id)
        if subject_id in self.missing_subjects:
            return httpx.Response(404, json={"message": "gone"})
        return httpx.Response(200, json=full_subject(subject_id))


def page_offsets(api: FakeBangumiAPI) -> list[int]:
    """Offsets requested against the collection endpoint, in call order."""
    return [
        int(request.url.params.get("offset", 0))
        for request in api.requests
        if request.url.path.endswith("/collections")
    ]


__all__ = ["FULL_TEMPLATE", "SLIM_TEMPLATE", "FakeBangumiAPI", "full_subject", "page_offsets", "slim_subject"]
