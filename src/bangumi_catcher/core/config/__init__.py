"""Typed configuration: models, file discovery, loading and validation.

Callers use this package's public names only::

    from bangumi_catcher.core.config import AppConfig, load_config, validate_config
"""

from __future__ import annotations

from .loading import (
    apply_env,
    apply_overrides,
    coerce_env_value,
    deep_merge,
    dump_config,
    load_config,
    save_config,
    validate_config,
)
from .models import (
    AnalysisConfig,
    ApiConfig,
    AppConfig,
    CacheConfig,
    CollectionConfig,
    ExportConfig,
    LoggingConfig,
    UiConfig,
)
from .paths import (
    APP_DIRNAME,
    CONFIG_ENV_VAR,
    CONFIG_FILENAME,
    ENV_PREFIX,
    bundled_config_path,
    config_search_paths,
    default_cache_dir,
    repository_config_path,
    user_config_path,
    working_dir_config_path,
)

__all__ = [
    "APP_DIRNAME",
    "CONFIG_ENV_VAR",
    "CONFIG_FILENAME",
    "ENV_PREFIX",
    "AnalysisConfig",
    "ApiConfig",
    "AppConfig",
    "CacheConfig",
    "CollectionConfig",
    "ExportConfig",
    "LoggingConfig",
    "UiConfig",
    "apply_env",
    "apply_overrides",
    "bundled_config_path",
    "coerce_env_value",
    "config_search_paths",
    "deep_merge",
    "default_cache_dir",
    "dump_config",
    "load_config",
    "repository_config_path",
    "save_config",
    "user_config_path",
    "validate_config",
    "working_dir_config_path",
]
