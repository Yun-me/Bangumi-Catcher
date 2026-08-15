"""Bangumi Catcher 命令行入口.

用法示例::

    python -m bangumi_catcher.cli gui
    python -m bangumi_catcher.cli fetch alice --format html --output report.html
    python -m bangumi_catcher.cli fetch alice --format csv --output collection.csv
    python -m bangumi_catcher.cli clear-cache
    python -m bangumi_catcher.cli version
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from . import __version__
from .core.config import load_config, validate_config
from .core.export import collection_to_csv, collection_to_json, report_to_json
from .services.fetch_service import fetch_and_analyze


def _print_progress(frac: float, msg: str) -> None:
    print(f"\r[{int(frac * 100):3d}%] {msg}", end="", flush=True)
    if frac >= 1.0:
        print()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bangumi-catcher",
        description="Bangumi 用户收藏抓取与可视化分析工具",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("gui", help="启动图形界面")

    fetch = sub.add_parser("fetch", help="抓取并分析用户收藏")
    fetch.add_argument("username", help="Bangumi 用户名或 UID")
    fetch.add_argument("--subject-type", type=int, default=None, choices=[1, 2, 3, 4, 6],
                       help="条目类型：1=书籍 2=动画 3=音乐 4=游戏 6=三次元")
    fetch.add_argument("--force-refresh", action="store_true", help="跳过缓存强制刷新")
    fetch.add_argument("--format", choices=["none", "csv", "json", "report-json", "html"],
                       default="none", help="导出格式（默认只打印摘要）")
    fetch.add_argument("--output", "-o", default=None, help="输出文件路径")
    fetch.add_argument("--config", default=None, help="配置文件路径")
    fetch.add_argument("--quiet", action="store_true", help="不打印进度")

    clear = sub.add_parser("clear-cache", help="清空本地缓存")
    clear.add_argument("--config", default=None, help="配置文件路径")

    sub.add_parser("version", help="显示版本号")

    return parser


def _run_gui() -> int:
    from .ui.gui import main as gui_main
    gui_main()
    return 0


async def _run_fetch(args: argparse.Namespace) -> int:
    cfg = load_config(config_path=args.config)
    issues = validate_config(cfg)
    if issues:
        for issue in issues:
            print(f"配置错误：{issue}", file=sys.stderr)
        return 2

    progress = None if args.quiet else _print_progress
    collection, report = await fetch_and_analyze(
        cfg,
        args.username,
        subject_type=args.subject_type,
        force_refresh=args.force_refresh,
        progress=progress,
    )

    if args.format == "none":
        print(f"\n用户 {report.username}: {report.total_items} 条收藏, "
              f"平均评分 {report.overall_avg_rating}, 完成率 {report.avg_completion}%")
        return 0

    output = Path(args.output) if args.output else None
    if args.format == "csv":
        output = output or Path(cfg.export.output_dir) / f"{args.username}_collection.csv"
        collection_to_csv(collection, str(output), encoding=cfg.export.csv_encoding)
    elif args.format == "json":
        output = output or Path(cfg.export.output_dir) / f"{args.username}_collection.json"
        collection_to_json(collection, str(output), indent=cfg.export.json_indent)
    elif args.format == "report-json":
        output = output or Path(cfg.export.output_dir) / f"{args.username}_report.json"
        report_to_json(report, str(output), indent=cfg.export.json_indent)
    elif args.format == "html":
        output = output or Path(cfg.export.output_dir) / f"{args.username}_report.html"
        from jinja2 import Environment, FileSystemLoader

        from .ui.visualizer import render_all
        charts = render_all(report, progress=progress)
        env = Environment(
            loader=FileSystemLoader(str(Path(__file__).resolve().parent / "templates")),
            autoescape=True,
        )
        html = env.get_template("report.html.j2").render(report=report, charts=charts)
        output.write_text(html, encoding="utf-8")
    else:  # pragma: no cover - argparse already restricts
        raise AssertionError("unreachable")

    print(f"\n已导出: {output}")
    return 0


def _run_clear_cache(args: argparse.Namespace) -> int:
    from .core.cache import Cache
    cfg = load_config(config_path=args.config)
    cache = Cache(directory=cfg.cache.dir or None)
    count = cache.size
    cache.clear()
    cache.close()
    print(f"缓存已清空（{count} 条）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.command == "gui":
        return _run_gui()
    if args.command == "fetch":
        return asyncio.run(_run_fetch(args))
    if args.command == "clear-cache":
        return _run_clear_cache(args)
    if args.command == "version":
        print(__version__)
        return 0
    parser.error(f"未知命令: {args.command}")  # pragma: no cover
    return 2  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
