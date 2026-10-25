"""Bangumi API access: HTTP client, pagination, mapping and cache.

Public entry points::

    from bangumi_catcher.api import BangumiClient, Cache
"""

from __future__ import annotations

from .cache import Cache
from .client import BangumiClient
from .mapping import build_collection_item, build_subject
from .pagination import compute_remaining_offsets, merge_pages
from .ratelimit import RateLimiter

__all__ = [
    "BangumiClient",
    "Cache",
    "RateLimiter",
    "build_collection_item",
    "build_subject",
    "compute_remaining_offsets",
    "merge_pages",
]
