"""开发/打包统一入口：python run.py。

PyInstaller 以本文件为入口可避免"相对导入作为 __main__ 失败"的问题。
"""

from bangumi_catcher.ui.gui import main

if __name__ == "__main__":
    main()
