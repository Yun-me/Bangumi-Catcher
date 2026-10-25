"""Configuration merging, environment overrides and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from bangumi_catcher.core.config import (
    AppConfig,
    CacheConfig,
    load_config,
    save_config,
    validate_config,
)
from bangumi_catcher.core.config.loading import coerce_env_value


def test_user_preferences_override_project_defaults(tmp_path):
    preferences = AppConfig()
    preferences.analysis.top_n = 37
    save_config(preferences, tmp_path / "preferences.yaml")
    assert load_config().analysis.top_n == 37


def test_explicit_missing_config_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(config_path=str(tmp_path / "missing.yaml"))


def test_invalid_year_range():
    config = AppConfig()
    config.analysis.year_start = 2030
    config.analysis.year_end = 2020
    assert any("年份" in issue for issue in validate_config(config))


def test_defaults_load():
    config = load_config()
    assert config.api.base_url.startswith("https://")
    assert config.collection.subject_type in (1, 2, 3, 4, 6)
    assert config.logging.level == "INFO"


def test_env_nested_override(monkeypatch):
    monkeypatch.setenv("BANGUMI_API__TIMEOUT", "55")
    assert load_config().api.timeout == 55


def test_validate_config_ok():
    assert validate_config(load_config()) == []


def test_proxy_optional():
    config = load_config(overrides={"api.proxy": "http://127.0.0.1:7890"})
    assert config.api.proxy == "http://127.0.0.1:7890"


def test_empty_proxy_becomes_none():
    config = load_config(overrides={"api.proxy": "   "})
    assert config.api.proxy is None


def test_bangumi_config_env_selects_explicit_file(tmp_path, monkeypatch):
    custom = tmp_path / "custom.yaml"
    custom.write_text("analysis:\n  top_n: 11\n", encoding="utf-8")
    monkeypatch.setenv("BANGUMI_CONFIG", str(custom))
    assert load_config().analysis.top_n == 11


def test_environment_wins_over_programmatic_override():
    config = load_config(
        overrides={"api.timeout": 5},
        environ={"BANGUMI_API__TIMEOUT": "9"},
    )
    assert config.api.timeout == 9


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("true", True),
        ("FALSE", False),
        ("42", 42),
        ("1.5", 1.5),
        ("none", None),
        ("null", None),
        ("http://127.0.0.1:7890", "http://127.0.0.1:7890"),
    ],
)
def test_environment_value_coercion(raw, expected):
    assert coerce_env_value(raw) == expected


def test_non_mapping_config_file_rejected(tmp_path):
    path = tmp_path / "list.yaml"
    path.write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="YAML 对象"):
        load_config(config_path=str(path))


def test_cache_directory_resolution(tmp_path):
    assert CacheConfig(dir="").resolved_dir() == Path.home() / ".cache" / "bangumi-catcher"
    assert CacheConfig(dir=str(tmp_path)).resolved_dir() == tmp_path


def test_output_directory_resolution():
    assert AppConfig(export={"output_dir": "build/out"}).resolved_output_dir() == Path("build/out")


def test_invalid_base_url_is_reported():
    config = AppConfig(api={"base_url": "ftp://example.com"})
    assert any("base_url" in issue for issue in validate_config(config))
