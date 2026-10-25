"""配置回归测试 —— 锁住类型化配置与环境变量嵌套覆盖。"""
from bangumi_catcher.core.config import load_config, validate_config


def test_user_preferences_override_project_defaults(tmp_path):
    from bangumi_catcher.core.config import AppConfig, save_config

    preferences = AppConfig()
    preferences.analysis.top_n = 37
    save_config(preferences, tmp_path / "preferences.yaml")
    assert load_config().analysis.top_n == 37


def test_explicit_missing_config_is_an_error(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        load_config(config_path=str(tmp_path / "missing.yaml"))


def test_invalid_year_range():
    from bangumi_catcher.core.config import AppConfig

    config = AppConfig()
    config.analysis.year_start = 2030
    config.analysis.year_end = 2020
    assert any("年份" in issue for issue in validate_config(config))


def test_defaults_load():
    cfg = load_config()
    assert cfg.api.base_url.startswith("https://")
    assert cfg.collection.subject_type in (1, 2, 3, 4, 6)


def test_env_nested_override(monkeypatch):
    monkeypatch.setenv("BANGUMI_API__TIMEOUT", "55")
    cfg = load_config()
    assert cfg.api.timeout == 55  # 必须改到 api.timeout，而非顶层游离键


def test_validate_config_ok():
    assert validate_config(load_config()) == []


def test_proxy_optional():
    cfg = load_config(overrides={"api.proxy": "http://127.0.0.1:7890"})
    assert cfg.api.proxy == "http://127.0.0.1:7890"
