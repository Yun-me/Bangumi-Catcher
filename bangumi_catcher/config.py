"""YAML 配置管理 —— 默认内嵌，外部文件可选覆盖."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

# 内嵌默认配置（exe 冻结后无需外部文件）
DEFAULT_CONFIG: dict[str, Any] = {
    "api": {
        "base_url": "https://api.bgm.tv",
        "user_agent": "bangumi-catcher/3.0 (https://github.com/Yun-me/Bangumi-Catcher)",
        "timeout": 30,
        "max_retries": 3,
        "retry_delay": 1.0,
    },
    "collection": {
        "subject_type": 2,
        "limit": 50,
        "rate_limit_delay": 1.0,
    },
    "analysis": {
        "year_start": 2000,
        "year_end": 2025,
        "top_n": 20,
    },
    "export": {
        "output_dir": "output",
        "csv_encoding": "utf-8-sig",
        "json_indent": 2,
    },
}

# 外部 config.yaml 的搜索路径
_EXTERNAL_PATHS = [
    Path.cwd() / "config.yaml",
    Path(__file__).resolve().parent.parent / "config.yaml",
]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(
    config_path: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """加载配置：内嵌默认 → 外部 config.yaml (可选) → CLI 覆盖 → 环境变量.

    外部文件不存在时静默回退到内嵌默认，确保 exe 双击即可用。
    """
    cfg = copy.deepcopy(DEFAULT_CONFIG)

    # 1. 加载外部 config.yaml (若存在)
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

    if external_file:
        with open(external_file, "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, user_cfg)

    # 2. CLI 点号键覆盖
    if overrides:
        for key_path, value in overrides.items():
            keys = key_path.split(".")
            target: dict[str, Any] = cfg
            for k in keys[:-1]:
                if k not in target or not isinstance(target[k], dict):
                    target[k] = {}
                target = target[k]
            target[keys[-1]] = value

    # 3. 环境变量 BANGUMI_* 覆盖
    for env_key, env_val in os.environ.items():
        if env_key.startswith("BANGUMI_") and env_val:
            config_key = env_key[len("BANGUMI_"):].lower()
            keys = config_key.split("__")
            target = cfg
            for k in keys[:-1]:
                if k not in target or not isinstance(target[k], dict):
                    target[k] = {}
                target = target[k]
            try:
                target[keys[-1]] = int(env_val)
            except ValueError:
                try:
                    target[keys[-1]] = float(env_val)
                except ValueError:
                    target[keys[-1]] = env_val

    return cfg


def validate_config(cfg: dict[str, Any]) -> list[str]:
    """验证必填项."""
    issues: list[str] = []
    if not cfg.get("api", {}).get("base_url"):
        issues.append("api.base_url 为空")
    if not cfg.get("collection", {}).get("subject_type"):
        issues.append("collection.subject_type 未设置")
    st = cfg.get("collection", {}).get("subject_type")
    if st and st not in (1, 2, 3, 4, 6):
        issues.append(f"collection.subject_type 无效: {st} (期望 1/2/3/4/6)")
    return issues
