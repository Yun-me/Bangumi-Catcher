"""YAML 配置管理 —— 加载、合并、验证."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml


DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.yaml"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """递归合并字典, override 覆盖 base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)  # type: ignore[arg-type]
        else:
            result[key] = value
    return result


def load_config(
    config_path: Optional[str] = None,
    overrides: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """加载配置: 默认 config.yaml → 用户指定路径 (可选) → CLI 覆盖.

    Args:
        config_path: 用户指定的配置文件路径.
        overrides: 命令行覆盖项, 使用点号键 (如 "api.timeout": 60).

    Returns:
        合并后的配置字典.
    """
    # 1. 加载默认配置
    cfg: dict[str, Any]
    if DEFAULT_CONFIG.exists():
        with open(DEFAULT_CONFIG, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    else:
        cfg = {}

    # 2. 加载用户指定配置 (可选)
    if config_path:
        user_path = Path(config_path).expanduser()
        if user_path.exists():
            with open(user_path, "r", encoding="utf-8") as f:
                user_cfg: dict[str, Any] = yaml.safe_load(f) or {}
            cfg = _deep_merge(cfg, user_cfg)

    # 3. 应用 CLI 点号键覆盖
    if overrides:
        for key_path, value in overrides.items():
            keys = key_path.split(".")
            target: dict[str, Any] = cfg
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            target[keys[-1]] = value

    # 4. 处理环境变量覆盖: BANGUMI_ 前缀
    for env_key, env_val in os.environ.items():
        if env_key.startswith("BANGUMI_") and env_val:
            config_key = env_key[len("BANGUMI_"):].lower()
            keys = config_key.split("__")  # 双下划线 = 点号
            target = cfg
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target
            # 类型转换
            try:
                target[keys[-1]] = int(env_val)
            except ValueError:
                try:
                    target[keys[-1]] = float(env_val)
                except ValueError:
                    target[keys[-1]] = env_val

    return cfg


def validate_config(cfg: dict[str, Any]) -> list[str]:
    """验证必填项, 返回问题列表."""
    issues: list[str] = []

    if not cfg.get("api", {}).get("base_url"):
        issues.append("api.base_url 为空")
    if not cfg.get("collection", {}).get("subject_type"):
        issues.append("collection.subject_type 未设置")

    st = cfg.get("collection", {}).get("subject_type")
    if st and st not in (1, 2, 3, 4, 6):
        issues.append(f"collection.subject_type 无效: {st} (期望 1/2/3/4/6)")

    return issues
