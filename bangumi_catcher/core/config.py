"""应用配置 —— 类型化配置模型 + YAML/环境变量/CLI 覆盖.

v2.0 起配置从裸 dict 升级为 Pydantic 模型，所有调用方获得类型提示与校验。
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

# 外部 config.yaml 的搜索路径
_EXTERNAL_PATHS = [
    Path.cwd() / "config.yaml",
    Path(__file__).resolve().parent.parent.parent / "config.yaml",
]

_ENV_PREFIX = "BANGUMI_"


class ApiConfig(BaseModel):
    base_url: str = "https://api.bgm.tv"
    user_agent: str = "bangumi-catcher (https://github.com/Yun-me/Bangumi-Catcher)"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    proxy: str | None = None

    @field_validator("base_url", mode="before")
    @classmethod
    def _strip_base_url(cls, v: Any) -> str:
        return str(v or "https://api.bgm.tv").rstrip("/")

    @field_validator("proxy", mode="before")
    @classmethod
    def _empty_proxy_to_none(cls, v: Any) -> str | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return str(v)


class CollectionConfig(BaseModel):
    subject_type: int = 2
    limit: int = 50
    max_concurrent: int = 8
    rate_limit_delay: float = 0.0

    @field_validator("subject_type", mode="before")
    @classmethod
    def _valid_subject_type(cls, v: Any) -> int:
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 2
        if n not in (1, 2, 3, 4, 6):
            raise ValueError(f"collection.subject_type 无效: {n} (期望 1/2/3/4/6)")
        return n

    @field_validator("limit", "max_concurrent", mode="before")
    @classmethod
    def _positive_int(cls, v: Any) -> int:
        try:
            return max(1, int(v))
        except (TypeError, ValueError):
            return 50


class CacheConfig(BaseModel):
    enabled: bool = True
    ttl: int = 3600
    dir: str = ""

    @field_validator("enabled", mode="before")
    @classmethod
    def _coerce_bool(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "on"}
        return bool(v)


class AnalysisConfig(BaseModel):
    year_start: int = 2000
    year_end: int = Field(default_factory=lambda: datetime.now().year)
    top_n: int = 20


class ExportConfig(BaseModel):
    output_dir: str = "output"
    csv_encoding: str = "utf-8-sig"
    json_indent: int = 2


class UiConfig(BaseModel):
    theme: str = "system"  # light / dark / system
    recent_users: list[str] = Field(default_factory=list)
    max_recent_users: int = 8


class AppConfig(BaseModel):
    api: ApiConfig = Field(default_factory=ApiConfig)
    collection: CollectionConfig = Field(default_factory=CollectionConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    ui: UiConfig = Field(default_factory=UiConfig)


def _default_dict() -> dict[str, Any]:
    return AppConfig().model_dump()


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_overrides(cfg: dict[str, Any], overrides: dict[str, Any] | None) -> None:
    if not overrides:
        return
    for key_path, value in overrides.items():
        keys = key_path.split(".")
        target = cfg
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value


def _apply_env(cfg: dict[str, Any]) -> None:
    for env_key, env_val in os.environ.items():
        if not env_key.startswith(_ENV_PREFIX) or not env_val:
            continue
        config_key = env_key[len(_ENV_PREFIX):].lower()
        keys = config_key.split("__")
        target = cfg
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        raw = env_val
        lowered = raw.strip().lower()
        if lowered in {"true", "false"}:
            value: Any = lowered == "true"
        else:
            try:
                value = int(raw)
            except ValueError:
                try:
                    value = float(raw)
                except ValueError:
                    value = raw
        target[keys[-1]] = value


def load_config(
    config_path: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> AppConfig:
    """加载配置：内嵌默认 → 外部 YAML（可选）→ CLI 覆盖 → 环境变量。"""
    cfg = _default_dict()

    external_file: Path | None = None
    if config_path:
        p = Path(config_path).expanduser()
        if p.exists():
            external_file = p
    else:
        for p in _EXTERNAL_PATHS:
            if p.exists():
                external_file = p
                break

    if external_file is not None:
        with open(external_file, encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, user_cfg)

    _apply_overrides(cfg, overrides)
    _apply_env(cfg)
    return AppConfig.model_validate(cfg)


def save_config(cfg: AppConfig, config_path: str | Path) -> Path:
    """将配置写回 YAML 文件（用于 GUI 设置对话框）。"""
    path = Path(config_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = cfg.model_dump(mode="json")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return path


def validate_config(cfg: AppConfig) -> list[str]:
    """返回配置问题列表；空列表表示配置可用。"""
    issues: list[str] = []
    if not cfg.api.base_url:
        issues.append("api.base_url 为空")
    if cfg.collection.subject_type not in (1, 2, 3, 4, 6):
        issues.append(f"collection.subject_type 无效: {cfg.collection.subject_type}")
    if cfg.collection.limit < 1 or cfg.collection.limit > 50:
        issues.append(f"collection.limit 应在 1~50 之间: {cfg.collection.limit}")
    if cfg.analysis.top_n < 1:
        issues.append(f"analysis.top_n 必须为正数: {cfg.analysis.top_n}")
    return issues
