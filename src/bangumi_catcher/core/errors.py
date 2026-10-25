"""Exception hierarchy shared by every layer.

All application errors derive from :class:`BangumiError`; the CLI catches that
base class to print a readable message and a non-zero exit code instead of a
traceback. The desktop app connects worker failures to the same base class.
"""

from __future__ import annotations


class BangumiError(Exception):
    """Base class for all expected, user-facing failures."""

    def __init__(self, message: str, *, code: int | None = None):
        super().__init__(message)
        self.code = code


class APIError(BangumiError):
    """A Bangumi API request failed.

    ``status_code`` is 0 for transport-level errors (timeouts, DNS, resets).
    """

    def __init__(self, message: str, status_code: int, url: str):
        super().__init__(message, code=status_code)
        self.status_code = status_code
        self.url = url


class RateLimitError(BangumiError):
    """HTTP 429 from the API; ``retry_after`` is the suggested delay in seconds."""

    def __init__(self, retry_after: int = 5):
        super().__init__(f"速率限制, 建议等待 {retry_after}s", code=429)
        self.retry_after = retry_after


class NotFoundError(BangumiError):
    """The user or subject does not exist (or is not publicly visible)."""


class EmptyCollectionError(BangumiError):
    """The API returned no entries for the requested collection type."""


class ConfigError(BangumiError):
    """Invalid configuration value or file."""


class OperationCancelled(BangumiError):
    """A task was cancelled cooperatively by the user."""


__all__ = [
    "APIError",
    "BangumiError",
    "ConfigError",
    "EmptyCollectionError",
    "NotFoundError",
    "OperationCancelled",
    "RateLimitError",
]
