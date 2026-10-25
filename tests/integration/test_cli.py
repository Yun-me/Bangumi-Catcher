"""CLI surface and error handling."""

from __future__ import annotations

import json

import pytest

from bangumi_catcher import __version__
from bangumi_catcher.cli import main
from bangumi_catcher.cli.parser import build_parser
from bangumi_catcher.reporting import collection_to_json


def test_version_command(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_version_subcommand(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_parser_has_commands():
    parser = build_parser()
    sub_actions = parser._subparsers._group_actions[0].choices
    assert {"gui", "fetch", "analyze", "clear-cache", "config", "version"} <= set(sub_actions)


def test_fetch_parser_requires_username(capsys):
    with pytest.raises(SystemExit):
        main(["fetch"])
    assert "username" in capsys.readouterr().err


def test_offline_analyze_and_export(tmp_path, sample_collection, capsys):
    source = tmp_path / "collection.json"
    collection_to_json(sample_collection, source)
    output = tmp_path / "nested" / "result.csv"
    assert main(["analyze", str(source), "--format", "csv", "-o", str(output), "--quiet"]) == 0
    assert output.exists()
    assert "已导出" in capsys.readouterr().out


def test_cli_reports_errors_without_tracebacks(tmp_path, capsys):
    assert main(["analyze", str(tmp_path / "missing.json")]) == 1
    captured = capsys.readouterr()
    assert "操作失败" in captured.err
    assert "Traceback" not in captured.err


def test_config_command_json(capsys):
    assert main(["config", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["api"]["base_url"].startswith("https://")
    assert payload["collection"]["subject_type"] in (1, 2, 3, 4, 6)


def test_config_command_yaml(capsys):
    assert main(["config"]) == 0
    assert "api:" in capsys.readouterr().out


def test_clear_cache_command(tmp_path, capsys):
    cache_dir = tmp_path / "cache"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(f"cache:\n  dir: '{cache_dir.as_posix()}'\n", encoding="utf-8")
    assert main(["clear-cache", "--config", str(config_path)]) == 0
    assert "缓存已清空" in capsys.readouterr().out


def test_invalid_config_exits_non_zero(tmp_path, capsys):
    config_path = tmp_path / "bad.yaml"
    config_path.write_text("analysis:\n  year_start: 2030\n  year_end: 2020\n", encoding="utf-8")
    assert main(["analyze", "missing.json", "--config", str(config_path)]) == 1
    assert "操作失败" in capsys.readouterr().err
