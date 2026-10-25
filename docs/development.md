# 开发

## 前置条件

- Python 3.9–3.13（CI 覆盖 3.9 与 3.13）
- Windows / macOS / Linux
- 可选：`git`、GNU Make（没有也能用 `python scripts/dev.py`）

## 安装

```bash
git clone https://github.com/Yun-me/Bangumi-Catcher.git
cd Bangumi-Catcher
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`-e` 可编辑安装让 `src/` 的改动立即生效。`[dev]` 包含 pytest、pytest-cov、ruff、
mypy、build；PyInstaller 在 `[packaging]` 中按需安装。

不安装也能工作：`python scripts/dev.py` 会把 `src/` 放进子进程的 `PYTHONPATH`。

## 运行

```bash
python -m bangumi_catcher                 # GUI
python run.py                             # 等价的开发入口
python -m bangumi_catcher.cli --help       # CLI
python -m bangumi_catcher.cli config --json
```

无显示器环境（CI、服务器）设置 `QT_QPA_PLATFORM=offscreen`；`scripts/dev.py`
和测试夹具会自动设置。

## 日常任务

所有任务都有两个等价入口：`python scripts/dev.py <task>` 与 `make <task>`。

```bash
python scripts/dev.py fmt            # 格式化 + 自动修复
python scripts/dev.py lint
python scripts/dev.py type
python scripts/dev.py test           # 全部测试
python scripts/dev.py test -- -k chart -x
python scripts/dev.py cov            # 覆盖率（生成 coverage.xml）
python scripts/dev.py check          # lint + type + test，提交前必须绿
python scripts/dev.py smoke          # 导入 + CLI 冒烟
python scripts/dev.py build          # sdist + wheel
python scripts/dev.py package        # PyInstaller 目录版
python scripts/dev.py clean          # 清理构建产物（不动 output/）
```

## 开发循环

1. 在 `docs/playbooks/` 找到对应改动清单。
2. 先写失败测试：单元 → 集成 → UI（按需）。
3. 从内层向外改：`core` → `api`/`charts`/`reporting` → `services` → `ui`/`cli`。
4. `python scripts/dev.py check`。
5. 手动跑一次 GUI / CLI，确认用户可见行为。
6. 更新文档与 `CHANGELOG.md` 的 `Unreleased`。

## 调试

- 日志：`logging` 输出到 stderr；GUI 的「工具 → 运行日志」显示最近 1,000 行。
  可在设置或 `config.yaml` 中改 `logging.level` / `logging.file`。
- CLI：`python -m bangumi_catcher.cli -v fetch alice` 输出 DEBUG 日志。
- 配置排查：`python -m bangumi_catcher.cli config` 打印合并后的最终配置。
- 缓存：默认 `~/.cache/bangumi-catcher`；`clear-cache` 只删缓存，不动收藏/导出。
- 代理问题：设置 `api.proxy` 或 `api.trust_env: false`；测试中 fake transport 会自动
  关闭 `trust_env`。
- Qt 启动失败：确认 `QT_QPA_PLATFORM` 未指向错误插件；Linux 需 `libegl1 libgl1
  libxkbcommon0` 与 CJK 字体。
- Matplotlib 中文方框：安装 `Noto Sans CJK` / `Microsoft YaHei` / `PingFang SC`
  之一；`charts/theme.py` 会按顺序探测。

## 环境变量

用于临时覆盖配置（下次启动生效），详见 [configuration.md](configuration.md)：

```bash
export BANGUMI_API__TIMEOUT=60
export BANGUMI_COLLECTION__MAX_CONCURRENT=4
export BANGUMI_ANALYSIS__TOP_N=30
export BANGUMI_LOGGING__LEVEL=DEBUG
export BANGUMI_CONFIG=/path/to/config.yaml   # 显式配置文件
```

## 发布

见 [packaging.md](packaging.md) 与 [AGENTS.md](../AGENTS.md) 第 8 节。

## 常见问题

| 现象 | 处理 |
|---|---|
| `ModuleNotFoundError: bangumi_catcher` | 运行 `pip install -e .`，或用 `scripts/dev.py` |
| pytest 报 Qt platform plugin 错误 | 设置 `QT_QPA_PLATFORM=offscreen`，Linux 安装 Qt 运行库 |
| `httpx` 初始化时报 URL/端口错误 | 检查 `NO_PROXY` 是否含 `[::1]` 等异常值，或设 `api.trust_env: false` |
| 图表很慢/内存高 | 只在需要时渲染；图表按数据+主题缓存；不要预渲染全部 |
| 打包后找不到模板 | 确认 `[tool.setuptools.package-data]` 与 PyInstaller `--add-data` 均包含 `templates/*.j2` |
