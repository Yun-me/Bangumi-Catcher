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
