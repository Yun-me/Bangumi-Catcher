"""Argument parser for the ``bangumi-catcher`` CLI.

Kept separate from command dispatch so tests (and agents) can inspect the
surface without running anything.
"""

from __future__ import annotations

import argparse

from .. import __version__
from ..services.export import EXPORT_FORMATS

SUBJECT_TYPE_HELP = "1=书籍 2=动画 3=音乐 4=游戏 6=三次元"


def _add_export_options(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--format", choices=["none", *EXPORT_FORMATS], default="none", help="导出格式；默认只打印摘要"
    )
    command.add_argument("--output", "-o", help="输出文件路径")
    command.add_argument("--config", help="显式配置文件路径")
    command.add_argument("--quiet", action="store_true", help="隐藏进度输出")


def build_parser() -> argparse.ArgumentParser:
    """Build the full argument parser."""
    parser = argparse.ArgumentParser(
        prog="bangumi-catcher",
        description="Bangumi 收藏工作台：在线同步、离线分析与导出",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--log-file", help="同时写入日志文件")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")

    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("gui", help="启动图形界面")

    fetch = commands.add_parser("fetch", help="同步并分析用户收藏")
    fetch.add_argument("username", help="Bangumi 用户名、UID 或用户主页链接")
    fetch.add_argument(
        "--subject-type", type=int, default=None, choices=[1, 2, 3, 4, 6], help=SUBJECT_TYPE_HELP
    )
    fetch.add_argument("--force-refresh", action="store_true", help="跳过收藏缓存")
    _add_export_options(fetch)

    analyze = commands.add_parser("analyze", help="离线分析收藏 JSON，不连接 Bangumi")
    analyze.add_argument("input", help="本应用导出的收藏 JSON 路径")
    _add_export_options(analyze)

    clear = commands.add_parser("clear-cache", help="清空请求缓存")
    clear.add_argument("--config", help="显式配置文件路径")

    show_config = commands.add_parser("config", help="打印合并后的有效配置")
    show_config.add_argument("--json", action="store_true", help="以 JSON 输出")
    show_config.add_argument("--config", help="显式配置文件路径")

    commands.add_parser("version", help="显示版本号")
    return parser


__all__ = ["SUBJECT_TYPE_HELP", "build_parser"]
