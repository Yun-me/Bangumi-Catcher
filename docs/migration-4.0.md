# 从 3.x 迁移到 4.0

4.0 是**结构性重构**：用户可见功能基本不变，但内部导入路径、开发命令与目录布局
有破坏性变化。应用自身的配置与环境变量保持兼容。

## 目录布局

```text
3.x                              4.0
bangumi_catcher/                 src/bangumi_catcher/
tests/test_*.py                  tests/unit|integration|ui|architecture/...
build.py (实现)                  scripts/build.py（根 build.py 已删除）
requirements.txt                 已删除，使用 pyproject.toml
```

## 导入路径

| 3.x | 4.0 |
|---|---|
| `bangumi_catcher.core.models` | 不变（现在是包，仍从这里导入） |
| `bangumi_catcher.core.config` | 不变（现在是包，仍从这里导入） |
| `bangumi_catcher.core.analyzer` | `bangumi_catcher.core.analysis` |
| `bangumi_catcher.core.exceptions` | `bangumi_catcher.core.errors` |
| `bangumi_catcher.core.api` | `bangumi_catcher.api`（`client` / `collection` / `mapping` / `pagination`） |
| `bangumi_catcher.core.cache` | `bangumi_catcher.api.cache` |
| `bangumi_catcher.core.export` | `bangumi_catcher.reporting` |
| `bangumi_catcher.ui.visualizer` | `bangumi_catcher.charts.render` |
| `bangumi_catcher.ui.chart_catalog` | `bangumi_catcher.charts.catalog` |
| `bangumi_catcher.ui.gui` | `bangumi_catcher.ui.app` |
| `bangumi_catcher.ui.dialogs` | `bangumi_catcher.ui.settings_dialog` + `ui.log_dialog` |
| `bangumi_catcher.ui.flowlayout` | `bangumi_catcher.ui.flow_layout` |
| `bangumi_catcher.ui.dialogs._LogBuffer` | `bangumi_catcher.observability.LogBuffer` |
| `bangumi_catcher.services.fetch_service` | `bangumi_catcher.services.fetch` |
| `bangumi_catcher.services.library_service` | `bangumi_catcher.services.library` |
| `bangumi_catcher.services.export_service` | `bangumi_catcher.services.export` |
| `bangumi_catcher.services.task_service` | `bangumi_catcher.services.cancellation` |
| `bangumi_catcher.cli`（模块） | `bangumi_catcher.cli`（包，`main` 仍可导入） |

`core.models` 与 `core.config` 保留了包级 re-export，常见导入无需改。

## API 变化

| 3.x | 4.0 |
|---|---|
| `BangumiClient._request` | `BangumiClient.request`（公开） |
| `BangumiClient._fetch_page` | `BangumiClient.fetch_page` |
| `BangumiClient._cache` | `BangumiClient.cache` |
| `BangumiClient._check_cancel` | `BangumiClient.check_cancelled` |
| `_build_subject` | `api.mapping.build_subject` |
| `_RateLimiter` | `api.ratelimit.RateLimiter` |
| `BangumiClient(config)` | 增加可选 `transport=` 关键字，便于离线测试 |

`fetch_collection` 的公开参数与行为不变。

## 桌面内部方法

这些是 GUI 内部 API，3.x 的测试/脚本若直接调用需要改名：

| 3.x | 4.0 |
|---|---|
| `MainWindow._set_data` | `set_data` |
| `MainWindow._navigate` | `navigate_to` |
| `MainWindow._open_library` | `open_library` |
| `MainWindow._toggle_theme` | `toggle_theme` |
| `MainWindow._focus_search` | `focus_search` |
| `MainWindow._export` | `export_data` |
| `MainWindow.user_input` 等 | `MainWindow.fetch_bar.user_input`（`FetchBar` 封装） |
| `MainWindow.settings_button` | `MainWindow.sidebar.settings_button` |

## 配置

新增字段（旧配置无需修改）：

```yaml
api:
  trust_env: true     # 读取 HTTP(S)_PROXY / NO_PROXY
logging:
  level: INFO
  file: ""
```

新增 `BANGUMI_CONFIG` 环境变量，用于显式指定配置文件（优先级等同 `--config`）。
配置优先级不变。

## 行为变化

- 季度统计不再把“无日期”的条目计入 `season_stats`（图表本来就会过滤空季度）。
- 收藏条目缺少 `subject_id` 时回退使用内联 `subject.id`，减少 `#0` 条目。
- CLI 新增 `config` 子命令、全局 `--verbose/-v` 与 `--log-file`。
- GUI 设置新增日志级别/日志文件。
- `--format` 支持集合不变：`none|csv|json|report-json|html`。
- 单文件打包仍为 `--onefile`，但推荐 `scripts/dev.py package` 的目录版。

## 开发命令

| 3.x | 4.0 |
|---|---|
| `pytest -q` | `python scripts/dev.py test`（等价） |
| `ruff check bangumi_catcher tests` | `python scripts/dev.py lint`（范围含 scripts） |
| `python build.py` | `python scripts/dev.py package`（根目录入口已删除，避免遮蔽 `python -m build`） |
| `pip install -e ".[dev]"` | 不变 |
| `python run.py` | 不变（会优先使用 `src/`） |

## 升级检查清单

1. `python -m pip install -e ".[dev]"` 重新安装。
2. 若你从旧代码导入了上表中的内部模块，按新路径修改。
3. 删除本地的 `requirements.txt` 使用习惯，改用 `pip install -e ".[dev]"`。
4. 跑 `python scripts/dev.py check` 与 `python scripts/dev.py smoke`。
5. 用 `python -m bangumi_catcher.cli config` 核对配置合并结果。
