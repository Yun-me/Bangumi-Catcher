"""Configuration loading, merging and validation.

Precedence, lowest first::

    built-in defaults
    < project config.yaml (working directory, then checkout)
    < user preferences (~/.config/bangumi-catcher/config.yaml)
    < programmatic overrides (dotted keys)
    < BANGUMI_* environment variables

An explicit ``--config`` path (or ``BANGUMI_CONFIG``) replaces the project
search and is not combined with user preferences. Environment variables are
always applied last and take effect on the next start.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from .models import AppConfig
from .paths import CONFIG_ENV_VAR, ENV_PREFIX, config_search_paths

# Backwards-compatible re-export: several callers import user_config_path from here.
from .paths import user_config_path as user_config_path


def _default_dict() -> dict[str, Any]:
    return AppConfig().model_dump()


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into a copy of ``base``."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _target_for(cfg: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    target = cfg
    for key in keys[:-1]:
        child = target.get(key)
        if not isinstance(child, dict):
            child = target[key] = {}
        target = child
    return target


def apply_overrides(cfg: dict[str, Any], overrides: Mapping[str, Any] | None) -> None:
    """Apply dotted-key overrides such as ``{"api.timeout": 60}`` in place."""
    if not overrides:
        return
    for key_path, value in overrides.items():
        keys = key_path.split(".")
        _target_for(cfg, keys)[keys[-1]] = value


def coerce_env_value(raw: str) -> Any:
    """Convert an environment string to the most specific scalar type."""
    lowered = raw.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"none", "null"}:
        return None
    try:
        return int(raw)
    except ValueError:
        try:
            return float(raw)
        except ValueError:
            return raw


def apply_env(cfg: dict[str, Any], environ: Mapping[str, str] | None = None) -> None:
    """Apply ``BANGUMI_API__TIMEOUT=60`` style variables in place."""
    source = os.environ if environ is None else environ
    for env_key, env_value in source.items():
        if not env_key.startswith(ENV_PREFIX) or not env_value or env_key == CONFIG_ENV_VAR:
            continue
        keys = env_key[len(ENV_PREFIX) :].lower().split("__")
        _target_for(cfg, keys)[keys[-1]] = coerce_env_value(env_value)


def load_config(
    config_path: str | None = None,
    overrides: dict[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    """Load, merge and validate the effective configuration.

    Raises:
        FileNotFoundError: an explicitly requested file does not exist.
        ValueError: a file is not a YAML mapping, or a value fails validation.
        yaml.YAMLError: a file contains invalid YAML.
    """
    cfg = _default_dict()
    for external_file in config_search_paths(config_path):
        with open(external_file, encoding="utf-8") as stream:
            user_cfg = yaml.safe_load(stream) or {}
        if not isinstance(user_cfg, dict):
            raise ValueError(f"配置文件必须是 YAML 对象：{external_file}")
        cfg = deep_merge(cfg, user_cfg)

    apply_overrides(cfg, overrides)
    apply_env(cfg, environ)
    return AppConfig.model_validate(cfg)


def dump_config(cfg: AppConfig) -> str:
    """Serialise the effective configuration as YAML (used by ``cli config``)."""
    return yaml.safe_dump(cfg.model_dump(mode="json"), allow_unicode=True, sort_keys=False)


def save_config(cfg: AppConfig, config_path: str | Path) -> Path:
    """Atomically write ``cfg`` to ``config_path`` and return the path."""
    path = Path(config_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".config-", suffix=".yaml", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            yaml.safe_dump(cfg.model_dump(mode="json"), stream, allow_unicode=True, sort_keys=False)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path


def validate_config(cfg: AppConfig) -> list[str]:
    """Return a list of human-readable problems; empty means the config is usable."""
    issues: list[str] = []
    parsed_url = urlparse(cfg.api.base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        issues.append("api.base_url 必须是有效的 HTTP / HTTPS 地址")
    if cfg.api.proxy:
        proxy = urlparse(cfg.api.proxy)
        if proxy.scheme not in {"http", "https"} or not proxy.hostname:
            issues.append("api.proxy 必须是 HTTP / HTTPS 代理地址")
    if cfg.collection.subject_type not in (1, 2, 3, 4, 6):
        issues.append(f"collection.subject_type 无效: {cfg.collection.subject_type}")
    if cfg.collection.limit < 1 or cfg.collection.limit > 50:
        issues.append(f"collection.limit 应在 1~50 之间: {cfg.collection.limit}")
    if cfg.analysis.top_n < 1:
        issues.append(f"analysis.top_n 必须为正数: {cfg.analysis.top_n}")
    if cfg.analysis.year_start > cfg.analysis.year_end:
        issues.append("统计起始年份不能晚于结束年份")
    if cfg.export.json_indent < 0:
        issues.append(f"export.json_indent 不能为负数: {cfg.export.json_indent}")
    return issues


__all__ = [
    "apply_env",
    "apply_overrides",
    "coerce_env_value",
    "deep_merge",
    "dump_config",
    "load_config",
    "save_config",
    "user_config_path",
    "validate_config",
]
