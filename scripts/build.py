"""PyInstaller packaging script.

Usage::

    pip install -e ".[dev,packaging]"
    python scripts/dev.py package            # onedir (recommended)
    python scripts/dev.py package --onefile  # single file (slower start)

The onedir build avoids re-extracting Qt and Matplotlib on every launch.
Templates and ``config.yaml`` are bundled as data; unused Qt modules and
Tkinter are excluded to keep the bundle smaller.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SEP = os.pathsep


def build(onefile: bool = False) -> Path:
    import PyInstaller.__main__ as pyinstaller

    arguments = [
        str(ROOT / "scripts" / "launch_gui.py"),
        "--name",
        "BangumiCatcher",
        "--onefile" if onefile else "--onedir",
        "--windowed",
        "--noupx",
        "--noconfirm",
        "--paths",
        str(SRC),
        # resources
        "--add-data",
        f"{SRC / 'bangumi_catcher' / 'templates'}{SEP}bangumi_catcher/templates",
        "--add-data",
        f"{ROOT / 'config.yaml'}{SEP}.",
        # implicit dependencies
        "--hidden-import",
        "eval_type_backport",
        "--collect-data",
        "matplotlib",
        # keep the bundle lean
        "--exclude-module",
        "tkinter",
        "--exclude-module",
        "PySide6.QtQml",
        "--exclude-module",
        "PySide6.QtQuick",
        "--exclude-module",
        "PySide6.Qt3DCore",
        "--exclude-module",
        "PySide6.QtWebEngineCore",
        "--exclude-module",
        "PySide6.QtMultimedia",
        "--exclude-module",
        "PySide6.QtNetworkAuth",
        "--exclude-module",
        "PyQt5",
        "--exclude-module",
        "PyQt6",
    ]
    icon = ROOT / "assets" / "icon.ico"
    if icon.exists():
        arguments += ["--icon", str(icon)]

    print("Building BangumiCatcher ...")
    pyinstaller.run(arguments)

    distribution = ROOT / "dist" if onefile else ROOT / "dist" / "BangumiCatcher"
    executable = distribution / ("BangumiCatcher.exe" if sys.platform == "win32" else "BangumiCatcher")
    print(f"\nDone -> {executable}")
    return executable


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="默认目录打包；避免每次启动解压依赖。")
    parser.add_argument("--onefile", action="store_true", help="生成单文件版本（启动时需要解压）")
    build(onefile=parser.parse_args(argv).onefile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
