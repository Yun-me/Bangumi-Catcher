"""Typed configuration models.

Every setting has an in-code default; YAML files, ``BANGUMI_*`` environment
variables and programmatic overrides are merged on top (see ``loading.py``).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .paths import default_cache_dir


class ApiConfig(BaseModel):
    """HTTP client behaviour."""

    base_url: str = "https://api.bgm.tv"
    user_agent: str = "bangumi-catcher (https://github.com/Yun-me/Bangumi-Catcher)"
    timeout: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_delay: float = Field(default=1.0, ge=0)
    proxy: str | None = None
    trust_env: bool = True
    """Honour ``HTTP(S)_PROXY`` / ``NO_PROXY``. Disable when a proxy environment
    variable is malformed and should not affect requests."""

    @field_validator("base_url", mode="before")
    @classmethod
    def _strip_base_url(cls, value: Any) -> str:
        return str(value or "https://api.bgm.tv").rstrip("/")

    @field_validator("proxy", mode="before")
    @classmethod
    def _empty_proxy_to_none(cls, value: Any) -> str | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return str(value)


class CollectionConfig(BaseModel):
    """Which collection to sync and how aggressively."""

    subject_type: int = 2
    limit: int = 50
    max_concurrent: int = 8
    rate_limit_delay: float = Field(default=0.0, ge=0)

    @field_validator("subject_type", mode="before")
    @classmethod
    def _valid_subject_type(cls, value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 2
        if number not in (1, 2, 3, 4, 6):
            raise ValueError(f"collection.subject_type 无效: {number} (期望 1/2/3/4/6)")
        return number

    @field_validator("limit", "max_concurrent", mode="before")
    @classmethod
    def _positive_int(cls, value: Any) -> int:
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return 50


class CacheConfig(BaseModel):
    """Persistent disk cache for API responses."""

    enabled: bool = True
    ttl: int = Field(default=3600, ge=0)
    dir: str = ""

    @field_validator("enabled", mode="before")
    @classmethod
    def _coerce_bool(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def resolved_dir(self) -> Path:
        """Configured directory, or the platform default when empty."""
        return Path(self.dir).expanduser() if self.dir.strip() else default_cache_dir()


class AnalysisConfig(BaseModel):
    """Analysis window and ranking size."""

    year_start: int = 2000
    year_end: int = Field(default_factory=lambda: datetime.now().year)
    top_n: int = Field(default=20, ge=1, le=1000)


class ExportConfig(BaseModel):
    """Exporter defaults."""

    output_dir: str = "output"
    csv_encoding: str = "utf-8-sig"
    json_indent: int = 2


class UiConfig(BaseModel):
    """Desktop preferences persisted outside Qt's own settings store."""

    theme: Literal["system", "light", "dark"] = "system"
    recent_users: list[str] = Field(default_factory=list)
    max_recent_users: int = Field(default=8, ge=1, le=50)


class LoggingConfig(BaseModel):
    """Process logging."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    file: str = ""
    """Optional log file; an empty string only logs to stderr."""


class AppConfig(BaseModel):
    """Root configuration object passed explicitly through every layer."""

    api: ApiConfig = Field(default_factory=ApiConfig)
    collection: CollectionConfig = Field(default_factory=CollectionConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    ui: UiConfig = Field(default_factory=UiConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    def resolved_output_dir(self) -> Path:
        return Path(self.export.output_dir).expanduser()


__all__ = [
    "AnalysisConfig",
    "ApiConfig",
    "AppConfig",
    "CacheConfig",
    "CollectionConfig",
    "ExportConfig",
    "LoggingConfig",
    "UiConfig",
]
