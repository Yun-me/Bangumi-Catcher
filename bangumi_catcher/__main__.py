"""python -m bangumi_catcher → 启动 GUI (绝对导入，兼容 PyInstaller)。"""

from bangumi_catcher.ui.gui import main

if __name__ == "__main__":
    main()
