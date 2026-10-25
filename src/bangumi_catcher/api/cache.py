"""Transparent disk cache for API responses.

The cache stores plain JSON-compatible dictionaries keyed by user/collection or
subject id. Long keys are hashed so a deeply nested cache directory never hits
filesystem path limits.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import diskcache

from ..core.config import default_cache_dir

logger = logging.getLogger(__name__)

DEFAULT_TTL = 3600
"""Default collection cache lifetime in seconds (one hour)."""

SUBJECT_TTL = 86400 * 7
"""Subject details are stable; cache them for a week."""


class Cache:
    """Thin, typed wrapper around :class:`diskcache.Cache`."""

    def __init__(self, directory: str | Path | None = None):
        cache_dir = Path(directory).expanduser() if directory else default_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.directory = cache_dir
        self._store = diskcache.Cache(str(cache_dir))
        logger.debug("缓存目录: %s", cache_dir)

    # -- lifecycle -------------------------------------------------------

    def close(self) -> None:
        self._store.close()

    def __enter__(self) -> Cache:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # -- keys ------------------------------------------------------------

    @staticmethod
    def _hash_key(key: str) -> str:
        if len(key) <= 80:
            return key
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        return f"{key[:60]}_{digest}"

    @staticmethod
    def collection_key(username: str, subject_type: int, collection_type: int | None = None) -> str:
        """Collection cache key including the optional type filter."""
        suffix = "all" if collection_type is None else f"ct{collection_type}"
        return f"collection:{username}:st{subject_type}:{suffix}"

    @staticmethod
    def subject_key(subject_id: int) -> str:
        return f"subject:{subject_id}"

    # -- primitives ------------------------------------------------------

    def get(self, key: str) -> Any | None:
        value = self._store.get(self._hash_key(key), default=None)
        if value is not None:
            logger.debug("缓存命中: %s", key)
        return value

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        self._store.set(self._hash_key(key), value, expire=ttl)
        logger.debug("缓存写入: %s (TTL=%ds)", key, ttl)

    def delete(self, key: str) -> bool:
        return bool(self._store.delete(self._hash_key(key)))

    def clear(self) -> None:
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)

    # -- domain helpers --------------------------------------------------

    def get_collection(
        self, username: str, subject_type: int, collection_type: int | None = None
    ) -> Any | None:
        return self.get(self.collection_key(username, subject_type, collection_type))

    def set_collection(
        self,
        username: str,
        subject_type: int,
        data: Any,
        collection_type: int | None = None,
        ttl: int = DEFAULT_TTL,
    ) -> None:
        self.set(self.collection_key(username, subject_type, collection_type), data, ttl=ttl)

    def get_subject(self, subject_id: int) -> Any | None:
        return self.get(self.subject_key(subject_id))

    def set_subject(self, subject_id: int, data: Any) -> None:
        self.set(self.subject_key(subject_id), data, ttl=SUBJECT_TTL)


__all__ = ["DEFAULT_TTL", "SUBJECT_TTL", "Cache"]
