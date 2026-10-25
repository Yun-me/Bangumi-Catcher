"""应用配置 —— 类型化配置模型 + YAML/环境变量/CLI 覆盖.

v2.0 起配置从裸 dict 升级为 Pydantic 模型，所有调用方获得类型提示与校验。
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field, field_validator

# 外部 config.yaml 的搜索路径
_EXTERNAL_PATHS = [
    Path.cwd() / "config.yaml",
    Path(__file__).resolve().parent.parent.parent / "config.yaml",
]

_ENV_PREFIX = "BANGUMI_"


def user_config_path() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return root / "bangumi-catcher" / "config.yaml"


class ApiConfig(BaseModel):
    base_url: str = "https://api.bgm.tv"
    user_agent: str = "bangumi-catcher (https://github.com/Yun-me/Bangumi-Catcher)"
    timeout: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_delay: float = Field(default=1.0, ge=0)
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
    rate_limit_delay: float = Field(default=0.0, ge=0)

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
    ttl: int = Field(default=3600, ge=0)
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
    top_n: int = Field(default=20, ge=1, le=1000)


class ExportConfig(BaseModel):
    output_dir: str = "output"
    csv_encoding: str = "utf-8-sig"
    json_indent: int = 2


class UiConfig(BaseModel):
    theme: Literal["system", "light", "dark"] = "system"
    recent_users: list[str] = Field(default_factory=list)
    max_recent_users: int = Field(default=8, ge=1, le=50)


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
    """加载默认、项目与用户配置；显式路径替代默认搜索，环境变量最后覆盖。"""
    cfg = _default_dict()

    external_files: list[Path] = []
    if config_path:
        external_files.append(Path(config_path).expanduser())
    else:
        for path in _EXTERNAL_PATHS:
            if path.exists():
                external_files.append(path)
                break
        personal = user_config_path()
        if personal.exists():
            external_files.append(personal)

    for external_file in external_files:
        with open(external_file, encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        if not isinstance(user_cfg, dict):
            raise ValueError(f"配置文件必须是 YAML 对象：{external_file}")
        cfg = _deep_merge(cfg, user_cfg)

    _apply_overrides(cfg, overrides)
    _apply_env(cfg)
    return AppConfig.model_validate(cfg)


def save_config(cfg: AppConfig, config_path: str | Path) -> Path:
    """将配置写回 YAML 文件（用于 GUI 设置对话框）。"""
    path = Path(config_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = cfg.model_dump(mode="json")
    descriptor, temporary = tempfile.mkstemp(prefix=".config-", suffix=".yaml", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            yaml.safe_dump(data, stream, allow_unicode=True, sort_keys=False)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path


def validate_config(cfg: AppConfig) -> list[str]:
    """返回配置问题列表；空列表表示配置可用。"""
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
    return issues
