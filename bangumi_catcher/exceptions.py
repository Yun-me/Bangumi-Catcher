"""自定义异常体系."""

from __future__ import annotations


class BangumiError(Exception):
    """Bangumi Catcher 基础异常."""

    def __init__(self, message: str, *, code: int | None = None):
        super().__init__(message)
        self.code = code


class APIError(BangumiError):
    """Bangumi API 请求失败.

    - 4xx: 客户端错误 (用户不存在 / 权限不足)
    - 5xx: 服务端错误
    """

    def __init__(self, message: str, status_code: int, url: str):
        super().__init__(message, code=status_code)
        self.status_code = status_code
        self.url = url


class RateLimitError(BangumiError):
    """触发 Bangumi API 速率限制 (HTTP 429)."""

    def __init__(self, retry_after: int = 5):
        super().__init__(f"速率限制, 建议等待 {retry_after}s", code=429)
        self.retry_after = retry_after


class ConfigError(BangumiError):
    """配置错误."""


class NotFoundError(BangumiError):
    """用户或资源不存在."""


class EmptyCollectionError(BangumiError):
    """用户收藏为空 (可能设置了隐私保护)."""
