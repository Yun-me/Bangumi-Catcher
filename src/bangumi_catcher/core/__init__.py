"""Pure domain layer: models, configuration, errors, analysis and querying.

Nothing in this package imports HTTP, Qt, Matplotlib or Jinja2. That rule is
enforced by ``tests/architecture/test_layers.py``.
"""

from __future__ import annotations

from .analysis import analyze
from .config import (
    AnalysisConfig,
    ApiConfig,
    AppConfig,
    CacheConfig,
    CollectionConfig,
    ExportConfig,
    LoggingConfig,
    UiConfig,
    load_config,
    save_config,
    user_config_path,
    validate_config,
)
from .errors import (
    APIError,
    BangumiError,
    ConfigError,
    EmptyCollectionError,
    NotFoundError,
    OperationCancelled,
    RateLimitError,
)
from .models import (
    COLLECTION_TYPE_MAP,
    AnalysisReport,
    CollectionItem,
    RatingInfo,
    Subject,
    UserCollection,
)
from .query import CollectionQuery

__all__ = [
    "COLLECTION_TYPE_MAP",
    "APIError",
    "AnalysisConfig",
    "AnalysisReport",
    "ApiConfig",
    "AppConfig",
    "BangumiError",
    "CacheConfig",
    "CollectionConfig",
    "CollectionItem",
    "CollectionQuery",
    "ConfigError",
    "EmptyCollectionError",
    "ExportConfig",
    "LoggingConfig",
    "NotFoundError",
    "OperationCancelled",
    "RateLimitError",
    "RatingInfo",
    "Subject",
    "UiConfig",
    "UserCollection",
    "analyze",
    "load_config",
    "save_config",
    "user_config_path",
    "validate_config",
]
