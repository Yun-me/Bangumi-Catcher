"""CLI 基础测试：版本、帮助、缓存清理命令可解析。"""
import pytest

from bangumi_catcher import __version__
from bangumi_catcher.cli import _build_parser, main


def test_version_command(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_parser_has_commands():
    parser = _build_parser()
    sub_actions = parser._subparsers._group_actions[0].choices  # noqa: SLF001
    assert {"gui", "fetch", "clear-cache", "version"} <= set(sub_actions)


def test_fetch_parser_requires_username(capsys):
    with pytest.raises(SystemExit):
        main(["fetch"])
    assert "username" in capsys.readouterr().err


def test_offline_analyze_and_export(tmp_path, sample_collection, capsys):
    from bangumi_catcher.core.export import collection_to_json

    source = tmp_path / "collection.json"
    collection_to_json(sample_collection, str(source))
    output = tmp_path / "nested" / "result.csv"
    assert main(["analyze", str(source), "--format", "csv", "-o", str(output), "--quiet"]) == 0
    assert output.exists()
    assert "已导出" in capsys.readouterr().out


def test_cli_reports_errors_without_tracebacks(tmp_path, capsys):
    assert main(["analyze", str(tmp_path / "missing.json")]) == 1
    captured = capsys.readouterr()
    assert "操作失败" in captured.err
    assert "Traceback" not in captured.err
