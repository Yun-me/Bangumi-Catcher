# 打包与发布

## Python 包

```bash
python scripts/dev.py build
# 或
python -m build
```

产物在 `dist/`：

- `bangumi_catcher-4.0.0-py3-none-any.whl`
- `bangumi_catcher-4.0.0.tar.gz`

包内容由 `src/` 布局决定；模板与 `py.typed` 通过
`[tool.setuptools.package-data]` 打入 wheel：

```toml
[tool.setuptools.package-data]
bangumi_catcher = ["templates/*.j2", "py.typed"]
```

安装后可用三个入口：

```bash
bangumi-catcher        # GUI
bangumi-catcher-gui    # GUI 别名
bangumi-catcher-cli    # CLI
```

## PyInstaller 桌面包

需要 `[packaging]` extra：

```bash
python -m pip install -e ".[dev,packaging]"
python scripts/dev.py package            # dist/BangumiCatcher/
python scripts/dev.py package --onefile  # 单文件，启动较慢
```

要点：

- 入口是 `scripts/launch_gui.py`，构建时传 `--paths src`，冻结后不依赖仓库路径。
- 打包 `templates/` 与 `config.yaml`；排除 Tkinter、QtQml/Quick/WebEngine 等未用模块。
- 默认 onedir，避免每次启动解压 Qt/Matplotlib；分发时保留整个目录。
- 关闭 UPX，减少杀软误报。
- Windows 产物为 `dist/BangumiCatcher/BangumiCatcher.exe`。

为避免遮蔽 Python 的 `build` 模块（`python -m build`），仓库根目录**不放**
`build.py`；PyInstaller 入口固定为 `scripts/build.py`。

## 版本一致性

版本号出现在两处，必须一致：

- `pyproject.toml` 的 `[project].version`
- `src/bangumi_catcher/__init__.py` 的 `__version__`

`tests/test_packaging.py` 会校验；发布前先跑 `python scripts/dev.py check`。

## CI

`.github/workflows/ci.yml`：

- `quality`：ruff + mypy（Linux，Python 3.12）
- `test`：Windows/Linux × Python 3.9/3.13，`QT_QPA_PLATFORM=offscreen`
- `package`：`python -m build` + 检查 wheel 内含模板/`py.typed` + CLI 冒烟

Linux 的 Qt 依赖：`libegl1 libgl1 libxkbcommon0 fonts-noto-cjk`。

## 发布流程

1. 更新 `CHANGELOG.md`，把 `Unreleased` 改为版本号与日期。
2. 同步两处版本号，跑 `python scripts/dev.py check`。
3. 提交：`git commit -m "chore: release v4.0.0"`。
4. 打标签并推送：`git tag -a v4.0.0 -m "v4.0.0" && git push origin main --follow-tags`。
5. `.github/workflows/release.yml` 自动构建 sdist/wheel 并创建 GitHub Release。
   如需同时附带 Windows 桌面包，在仓库变量中设置 `BUILD_DESKTOP_BUNDLE=true`，
   `bundle` job 会构建并上传 zip。

## 常见打包问题

| 问题 | 原因/处理 |
|---|---|
| 冻结后 `FileNotFoundError: report.html.j2` | 忘记 `--add-data` 或 wheel 的 package-data |
| `ImportError: eval_type_backport` | 添加 `--hidden-import eval_type_backport` |
| 体积过大 | 检查是否卷入 QtWebEngine/QtQuick；确认 `--exclude-module` 生效 |
| 启动白屏/崩溃 | 先用控制台版（去掉 `--windowed`）看 traceback |
| 中文变方框 | 目标机器缺 CJK 字体；安装 Noto Sans CJK / 微软雅黑 |
| macOS 无法打开 | 未签名应用需右键“打开”，或自行签名/公证 |
