"""Command dispatch for the ``bangumi-catcher`` CLI.

The CLI never imports Qt unless the ``gui`` command is used, so it stays usable
on headless machines and in CI smoke tests.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import yaml

from .. import __version__
from ..core.config import AppConfig, dump_config, load_config, validate_config
from ..core.errors import BangumiError
from ..observability import configure_logging
from ..services import (
    analyze_user_collection,
    default_output_path,
    export_dataset,
    fetch_and_analyze,
    load_collection,
    normalize_username,
)
from .parser import build_parser


def _print_progress(fraction: float, message: str) -> None:
    print(f"\r[{int(fraction * 100):3d}%] {message}", end="", flush=True)
    if fraction >= 1.0:
        print()


def _effective_config(args: Any) -> AppConfig:
    """Load and validate the configuration for a command."""
    config = load_config(config_path=getattr(args, "config", None))
    issues = validate_config(config)
    if issues:
        raise ValueError("；".join(issues))
    return config


def _configure_logging(args: Any, config: AppConfig) -> None:
    level = "DEBUG" if getattr(args, "verbose", False) else config.logging.level
    logfile = getattr(args, "log_file", None) or config.logging.file or None
    configure_logging(level, logfile)


def _emit(args: Any, config: AppConfig, collection, report) -> int:
    """Print the summary or write the requested export."""
    if args.format == "none":
        print(
            f"用户 {report.username}: {report.total_items} 条收藏, "
            f"平均评分 {report.overall_avg_rating}, 完成率 {report.avg_completion}%"
        )
        return 0

    if args.output:
        output = Path(args.output).expanduser()
    else:
        try:
            username = normalize_username(collection.username)
        except ValueError:
            username = "snapshot"
        output = default_output_path(config, username, args.format)

    export_dataset(
        collection,
        report,
        output,
        args.format,
        config,
        progress=None if args.quiet else _print_progress,
    )
    print(f"已导出: {output}")
    return 0


async def _run_fetch(args: Any, config: AppConfig) -> int:
    collection, report = await fetch_and_analyze(
        config,
        args.username,
        subject_type=args.subject_type,
        force_refresh=args.force_refresh,
        progress=None if args.quiet else _print_progress,
    )
    return _emit(args, config, collection, report)


def _run_analyze(args: Any, config: AppConfig) -> int:
    collection = load_collection(args.input)
    return _emit(args, config, collection, analyze_user_collection(collection, config))


def _run_clear_cache(args: Any, config: AppConfig) -> int:
    from ..api import Cache

    with Cache(config.cache.resolved_dir()) as cache:
        count = cache.size
        cache.clear()
    print(f"缓存已清空（{count} 条）")
    return 0


def _run_config(args: Any) -> int:
    config = load_config(config_path=args.config)
    if args.json:
        print(config.model_dump_json(indent=2))
    else:
        print(dump_config(config), end="")
    issues = validate_config(config)
    if issues:
        print("配置问题：" + "；".join(issues), file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and run one command, returning a process exit code."""
    args = build_parser().parse_args(argv)

    if args.command == "version":
        print(__version__)
        return 0

    if args.command == "gui":
        from ..ui.app import main as gui_main

        return gui_main()

    try:
        if args.command == "config":
            return _run_config(args)

        config = _effective_config(args)
        _configure_logging(args, config)

        if args.command == "fetch":
            return asyncio.run(_run_fetch(args, config))
        if args.command == "analyze":
            return _run_analyze(args, config)
        if args.command == "clear-cache":
            return _run_clear_cache(args, config)
        return 0
    except (BangumiError, ValueError, OSError, yaml.YAMLError) as exc:
        print(f"操作失败：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("操作已取消。", file=sys.stderr)
        return 130


__all__ = ["main"]
