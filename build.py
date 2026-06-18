"""PyInstaller 打包脚本。

用法:
    pip install pyinstaller
    python build.py

要点:
* 入口用 run.py（绝对导入，避免相对导入作为 __main__ 失败）。
* 把 templates/ 与 config.yaml 一并打包，确保冻结后可用。
* 排除 tkinter 及未用到的 Qt 模块，显著减小体积。
* 关闭 UPX（避免被杀软误报）。
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEP = os.pathsep


def build():
    import PyInstaller.__main__ as pyi

    args = [
        str(ROOT / "run.py"),
        "--name", "BangumiCatcher",
        "--onefile",
        "--windowed",
        "--noupx",
        "--noconfirm",
        # 资源
        "--add-data", f"{ROOT / 'bangumi_catcher' / 'templates'}{SEP}bangumi_catcher/templates",
        "--add-data", f"{ROOT / 'config.yaml'}{SEP}.",
        # 隐式依赖
        "--hidden-import", "eval_type_backport",
        "--collect-data", "matplotlib",
        # 瘦身：排除不用的库与 Qt 模块
        "--exclude-module", "tkinter",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.Qt3DCore",
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtMultimedia",
        "--exclude-module", "PySide6.QtNetworkAuth",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PyQt6",
    ]
    icon = ROOT / "assets" / "icon.ico"
    if icon.exists():
        args += ["--icon", str(icon)]

    print("Building BangumiCatcher ...")
    pyi.run(args)
    out = ROOT / "dist" / ("BangumiCatcher.exe" if sys.platform == "win32" else "BangumiCatcher")
    print(f"\nDone -> {out}")


if __name__ == "__main__":
    build()
