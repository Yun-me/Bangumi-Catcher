"""透明缓存层 —— 基于 diskcache, 自动管理 API 响应与条目详情的持久化."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import diskcache

logger = logging.getLogger(__name__)

# 缓存目录: ~/.cache/bangumi-catcher/
_CACHE_ROOT = Path.home() / ".cache" / "bangumi-catcher"

# 默认过期时间 (秒)
DEFAULT_TTL = 3600  # 1 小时
SUBJECT_TTL = 86400 * 7  # 条目详情 7 天


class Cache:
    """透明缓存封装.

    用法::

        cache = Cache()
        data = cache.get("user_123_collection")
        if data is None:
            data = await fetch_from_api()
            cache.set("user_123_collection", data)
    """

    def __init__(self, directory: str | None = None):
        cache_dir = Path(directory) if directory else _CACHE_ROOT
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._store = diskcache.Cache(str(cache_dir))
        logger.debug("缓存目录: %s", cache_dir)

    # ---- key 生成 ----

    @staticmethod
    def _hash_key(key: str) -> str:
        """对长 key 做 sha256 缩短, 避免文件系统路径过长."""
        if len(key) <= 80:
            return key
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        return f"{key[:60]}_{digest}"

    # ---- 基础操作 ----

    def get(self, key: str) -> Any | None:
        """读取缓存, 过期返回 None."""
        value = self._store.get(self._hash_key(key), default=None)
        if value is not None:
            logger.debug("缓存命中: %s", key)
        return value

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        """写入缓存."""
        self._store.set(self._hash_key(key), value, expire=ttl)
        logger.debug("缓存写入: %s (TTL=%ds)", key, ttl)

    def delete(self, key: str) -> bool:
        """删除缓存项."""
        return bool(self._store.delete(self._hash_key(key)))

    def clear(self) -> None:
        """清空全部缓存."""
        self._store.clear()

    def close(self) -> None:
        """关闭缓存连接."""
        self._store.close()

    @property
    def size(self) -> int:
        """缓存条目数量."""
        return len(self._store)

    # ---- 领域方法 ----

    @staticmethod
    def collection_key(username: str, subject_type: int) -> str:
        """用户收藏缓存键."""
        return f"collection:{username}:st{subject_type}"

    @staticmethod
    def subject_key(subject_id: int) -> str:
        """条目详情缓存键."""
        return f"subject:{subject_id}"

    def get_collection(self, username: str, subject_type: int) -> Any | None:
        """读取用户收藏缓存."""
        return self.get(self.collection_key(username, subject_type))

    def set_collection(self, username: str, subject_type: int, data: Any, ttl: int = DEFAULT_TTL) -> None:
        """写入用户收藏缓存."""
        self.set(self.collection_key(username, subject_type), data, ttl=ttl)

    def get_subject(self, subject_id: int) -> Any | None:
        """读取条目详情缓存."""
        return self.get(self.subject_key(subject_id))

    def set_subject(self, subject_id: int, data: Any) -> None:
        """写入条目详情缓存."""
        self.set(self.subject_key(subject_id), data, ttl=SUBJECT_TTL)
