"""配置回归测试 —— 锁住环境变量嵌套覆盖。"""
from bangumi_catcher.core.config import load_config, validate_config


def test_defaults_load():
    cfg = load_config()
    assert cfg["api"]["base_url"].startswith("https://")
    assert cfg["collection"]["subject_type"] in (1, 2, 3, 4, 6)


def test_env_nested_override(monkeypatch):
    monkeypatch.setenv("BANGUMI_API__TIMEOUT", "55")
    cfg = load_config()
    assert cfg["api"]["timeout"] == 55  # 必须改到 api.timeout，而非顶层游离键


def test_validate_config_ok():
    assert validate_config(load_config()) == []
