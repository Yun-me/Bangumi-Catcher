"""Scriptable online fetch, offline analysis and dataset export."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import yaml

from . import __version__
from .core.config import load_config, validate_config
from .core.exceptions import BangumiError
from .services.export_service import export_dataset
from .services.fetch_service import analyze_user_collection, fetch_and_analyze
from .services.library_service import load_collection, normalize_username


def _print_progress(fraction: float, message: str) -> None:
    print(f"\r[{int(fraction * 100):3d}%] {message}", end="", flush=True)
    if fraction >= 1.0:
        print()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bangumi-catcher", description="Bangumi 收藏工作台：在线同步、离线分析与导出")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("gui", help="启动图形界面")
    fetch = commands.add_parser("fetch", help="同步并分析用户收藏")
    fetch.add_argument("username", help="Bangumi 用户名、UID 或用户主页链接")
    fetch.add_argument("--subject-type", type=int, default=None, choices=[1, 2, 3, 4, 6],
                       help="1=书籍 2=动画 3=音乐 4=游戏 6=三次元")
    fetch.add_argument("--force-refresh", action="store_true", help="跳过收藏缓存")
    analyze = commands.add_parser("analyze", help="离线分析收藏 JSON，不连接 Bangumi")
    analyze.add_argument("input", help="本应用导出的收藏 JSON 路径")
    for command in (fetch, analyze):
        command.add_argument("--format", choices=["none", "csv", "json", "report-json", "html"],
                             default="none", help="导出格式；默认只打印摘要")
        command.add_argument("--output", "-o", help="输出文件路径")
        command.add_argument("--config", help="显式配置文件路径")
        command.add_argument("--quiet", action="store_true", help="隐藏进度")
    clear = commands.add_parser("clear-cache", help="清空请求缓存")
    clear.add_argument("--config", help="显式配置文件路径")
    commands.add_parser("version", help="显示版本号")
    return parser


def _config(args):
    config = load_config(config_path=args.config)
    issues = validate_config(config)
    if issues:
        raise ValueError("；".join(issues))
    return config


def _output(args, config, collection, report) -> int:
    if args.format == "none":
        print(f"用户 {report.username}: {report.total_items} 条收藏, "
              f"平均评分 {report.overall_avg_rating}, 完成率 {report.avg_completion}%")
        return 0
    extension = "json" if args.format == "report-json" else args.format
    stem = "report" if args.format in {"report-json", "html"} else "collection"
    try:
        username = normalize_username(collection.username)
    except ValueError:
        username = "snapshot"
    output = Path(args.output) if args.output else Path(config.export.output_dir) / f"{username}_{stem}.{extension}"
    export_dataset(collection, report, output, args.format, config,
                   progress=None if args.quiet else _print_progress)
    print(f"已导出: {output}")
    return 0


async def _run_fetch(args) -> int:
    config = _config(args)
    collection, report = await fetch_and_analyze(
        config, args.username, subject_type=args.subject_type,
        force_refresh=args.force_refresh, progress=None if args.quiet else _print_progress,
    )
    return _output(args, config, collection, report)


def _run_clear_cache(args) -> int:
    from .core.cache import Cache

    cache = Cache(directory=_config(args).cache.dir or None)
    try:
        count = cache.size
        cache.clear()
    finally:
        cache.close()
    print(f"缓存已清空（{count} 条）")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    try:
        if args.command == "gui":
            from .ui.gui import main as gui_main

            gui_main()
            return 0
        if args.command == "fetch":
            return asyncio.run(_run_fetch(args))
        if args.command == "analyze":
            config = _config(args)
            collection = load_collection(args.input)
            return _output(args, config, collection, analyze_user_collection(collection, config))
        if args.command == "clear-cache":
            return _run_clear_cache(args)
        print(__version__)
        return 0
    except (BangumiError, ValueError, OSError, yaml.YAMLError) as exc:
        print(f"操作失败：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("操作已取消。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
