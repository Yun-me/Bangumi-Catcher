"""
PyInstaller 打包脚本.

用法:
    pip install pyinstaller
    python build.py

输出:
    dist/BangumiCatcher.exe  (单文件，首次运行解压到临时目录)
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "BangumiCatcher",
        "--add-data", f"{ROOT / 'bangumi_catcher' / 'templates'}{os.pathsep}bangumi_catcher/templates",
        "--hidden-import", "pydantic",
        "--hidden-import", "pydantic.deprecated.decorator",
        "--hidden-import", "plotly",
        "--hidden-import", "plotly.validators",
        "--hidden-import", "kaleido",
        "--hidden-import", "kaleido.scopes",
        "--hidden-import", "kaleido.scopes.plotly",
        "--hidden-import", "jinja2",
        "--hidden-import", "jinja2.ext",
        "--hidden-import", "diskcache",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL._imagingtk",
        "--hidden-import", "PIL.ImageTk",
        "--hidden-import", "eval_type_backport",
        "--exclude-module", "kaleido.mocker",
        "--collect-all", "plotly",
        str(ROOT / "bangumi_catcher" / "gui.py"),
    ]

    print("Building BangumiCatcher.exe ...")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode == 0:
        exe = ROOT / "dist" / "BangumiCatcher.exe"
        print(f"\nDone! -> {exe}")
    else:
        print("\nBuild failed.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    import os
    build()
