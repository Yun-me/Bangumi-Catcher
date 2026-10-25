# AGENTS.md — Bangumi Catcher 开发指南（面向人类与 AI agent）

> 本文件是仓库的唯一权威开发说明。`CLAUDE.md`、`.cursor/rules/project.mdc`、
> `.github/copilot-instructions.md` 只是指向这里的短指针；若内容冲突，以本文件为准。

## 1. 项目是什么

Bangumi Catcher 是一个**本地优先、只读**的 Bangumi 收藏工作台：

- PySide6 桌面应用（`python -m bangumi_catcher`）
- 可脚本化 CLI（`python -m bangumi_catcher.cli`）
- 在线同步 → 离线快照 → 统计分析 → CSV / JSON / HTML 导出
- 不登录、不改远程收藏、不绕过隐私限制

技术栈：Python 3.9+、Pydantic v2、httpx、diskcache、PyYAML、Matplotlib（Agg）、
Jinja2、PySide6。构建：setuptools + `src/` 布局。测试：pytest（Qt 使用 offscreen）。

## 2. 30 秒启动

```bash
python -m pip install -e ".[dev]"   # 或：python scripts/dev.py setup
python scripts/dev.py check         # ruff + mypy + pytest（提交前必须通过）
python -m bangumi_catcher           # 启动 GUI
python -m bangumi_catcher.cli --help
```

Windows 上如果没有 `python`，用 `py -3` 替换；`scripts/dev.py` 会自动把 `src/`
放进 `PYTHONPATH`，因此不安装也能跑测试与 CLI。CI/无显示器环境自动
`QT_QPA_PLATFORM=offscreen`。

常用任务（`python scripts/dev.py <task>`，`make <task>` 等价）：

| task | 作用 |
|---|---|
| `setup` | `pip install -e ".[dev]"` |
| `fmt` / `lint` | `ruff format` / `ruff check` |
| `type` | `mypy`（只检查无 Qt 的层） |
| `test` / `cov` | pytest / 带覆盖率的 pytest |
| `check` | lint + type + test，**定义完成的标准** |
| `run` / `cli` | 启动 GUI / CLI |
| `build` | 构建 sdist + wheel |
| `package` | PyInstaller 目录版（需 `.[packaging]`） |
| `smoke` | 导入与 CLI `--help` 冒烟 |
| `clean` | 清理构建产物与缓存，不动用户导出 |

## 3. 仓库地图

```text
AGENTS.md               本文件（agent 首选入口）
README.md               用户视角介绍
CONTRIBUTING.md         贡献流程
docs/                   架构、开发、测试、约定、数据口径、配置、打包、迁移、playbook
docs/adr/               架构决策记录（改结构前先读）
scripts/dev.py          唯一任务入口（跨平台，无第三方依赖）
scripts/build.py        PyInstaller 打包
src/bangumi_catcher/    唯一的运行时包（src 布局）
tests/                  unit / integration / ui / architecture / docs / packaging
```

### `src/bangumi_catcher/` 分层

| 层 | 职责 | 允许依赖 |
|---|---|---|
| `core/` | Pydantic 模型、配置、异常、分析、表格查询语义 | 标准库、pydantic、yaml |
| `api/` | Bangumi HTTP 客户端、分页、映射、缓存、限速 | `core`、httpx、diskcache |
| `charts/` | Matplotlib 图形构建与 PNG 渲染 | `core`、matplotlib |
| `reporting/` | CSV / JSON / HTML 导出与原子写入 | `core`、`charts`、jinja2 |
| `services/` | 抓取/导入/导出编排、协作式取消 | `core`、`api`、`reporting` |
| `ui/` | PySide6 桌面层 | 任意内部层、PySide6 |
| `cli/` | 命令行入口与参数解析 | 任意层（仅 `gui` 命令懒加载 Qt） |
| `observability.py` | 日志初始化与内存日志缓冲 | 标准库 |

依赖方向由 `tests/architecture/test_layers.py` 用 AST **强制执行**，不是建议：

```
core  ←  api  ←  services  →  reporting  →  charts
                    ↑
                   ui / cli
```

- `core/`、`api/`、`charts/`、`reporting/`、`services/` **禁止**导入 PySide6。
- `core/` 禁止导入 httpx / matplotlib / jinja2 / diskcache。
- `services/` 禁止导入 matplotlib。
- `ui/` 模块顶层禁止导入 matplotlib；`chart_page.py` 只在 worker 内延迟导入
  `bangumi_catcher.charts.render`。
- UI 与 CLI 只通过 `services/` 组合业务，不直接写 HTTP 或文件格式逻辑。

## 4. 不可违反的不变量

1. **只读**：任何代码都不得修改 Bangumi 远程收藏，或尝试绕过私有收藏限制。
2. **测试离线**：测试不得访问网络。`tests/conftest.py` 会拦截真实 HTTP transport；
   需要网络的测试必须显式标记 `@pytest.mark.network`，默认 CI 不跑。
3. **启动不加载绘图库**：导入 `bangumi_catcher.ui.main_window` / `ui.app` 后，
   `sys.modules` 中不得出现 `matplotlib`（有守卫测试）。
4. **导出原子化**：先写同目录临时文件，成功后 `os.replace`；失败/取消不得覆盖旧文件。
5. **取消协作式**：HTTP 在途请求与重试 sleep 必须能被 `threading.Event` 中断；
   关闭窗口要等待后台线程结束，不能销毁运行中的 `QThread`。
6. **配置优先级**：内置默认 < 项目 `config.yaml` < 用户偏好 < 程序化覆盖 < `BANGUMI_*`
   环境变量。显式 `--config` / `BANGUMI_CONFIG` 替代项目搜索。
7. **Python 3.9 兼容**：不用 `match`、运行时 `X | Y`、`zip(strict=)`、`tomllib`（测试有兼容层）。
8. **统计口径**：均分只算「看过 + 评分 > 0」；完成率「看过」=100%，其余按集数比；
   年度统计按**作品发行年份**。详见 `docs/data-model.md`。
9. **新增运行时依赖**：先写 ADR 并说明替代方案；不要让 GUI 启动多加载一个重依赖。
10. **不提交生成物**：`output/`、`reports/`、`dist/`、缓存、`.venv/` 均被忽略。

## 5. 典型改动怎么做

先读 `docs/playbooks/`：

- 新增图表维度 → `docs/playbooks/add-chart.md`
- 新增导出格式 → `docs/playbooks/add-export-format.md`
- 新增配置项 → `docs/playbooks/add-config-option.md`
- 排查抓取问题 → `docs/playbooks/debug-fetch.md`

通用步骤：

1. 先写/改测试（`tests/unit` 纯逻辑，`tests/integration` 用 `tests/fakes.py` 的
   `FakeBangumiAPI`，UI 用 `tests/ui`）。
2. 从最内层改起：`core` → `api`/`charts`/`reporting` → `services` → `ui`/`cli`。
3. 更新文档（AGENTS/README/docs）与 `CHANGELOG.md` 的 `Unreleased`。
4. 运行 `python scripts/dev.py check`，再跑 `python scripts/dev.py smoke`。

## 6. 测试策略

| 目录 | 范围 | 说明 |
|---|---|---|
| `tests/unit/core` | 模型、分析、配置、查询 | 无 I/O、无 Qt |
| `tests/unit/api` | 分页、映射、缓存键、限速 | 纯函数 / asyncio.run |
| `tests/unit/charts` | 注册表、PNG 渲染 | Agg，无显示器 |
| `tests/unit/reporting` | CSV/JSON/HTML/原子写 | HTML 用 monkeypatch 跳过 Matplotlib |
| `tests/integration` | 客户端生命周期、服务编排、CLI、导出 | 使用 `FakeBangumiAPI` |
| `tests/ui` | 模型契约、后台任务、窗口流程 | `QT_QPA_PLATFORM=offscreen` |
| `tests/architecture` | 分层与 import 方向 | AST 分析，秒级 |
| `tests/test_docs.py` | 文档存在性与相对链接 | 防止文档腐烂 |
| `tests/test_packaging.py` | pyproject / 包数据 / 入口点 | 防止打包回归 |

- 共享数据用 `tests/factories.py`，不要复制粘贴大段 fixture。
- 录制的 API 响应放在 `tests/fixtures/bangumi/`；新增抓取逻辑时优先补一个 fixture。
- Qt 测试不依赖 `pytest-qt`；使用 `tests/ui/conftest.py` 的 `window` fixture 与
  `wait_until`。不要用 `time.sleep` 等待 Qt。
- 测试必须能在 `pytest -q` 下独立、可重复、无顺序依赖地运行。

## 7. 代码约定

- 格式与 lint 全部交给 `ruff`（line-length 110，py39）；不要手工对齐。
- 公共函数/类写英文 docstring；面向用户的字符串用中文。领域怪癖注释可以中文。
- 新代码必须带类型注解；`mypy` 覆盖无 Qt 的层。避免 `Any` 扩散。
- 错误：可预期的失败抛 `core.errors.BangumiError` 子类；CLI 统一捕获并返回非零码；
  UI 把异常转成可读消息，不允许 traceback 弹窗。
- 日志：模块级 `logger = logging.getLogger(__name__)`；不要用 `print`（CLI 的用户输出除外）。
- UI：后台工作放 `TaskRunner`；跨线程只用 Signal；不要在 worker 里碰 QWidget。
- 配置：新增字段时同时更新 `config.yaml`、`docs/configuration.md`、设置对话框（如适用）。
- 注释解释「为什么」，不要复述代码。

## 8. 提交与发布

- 提交信息使用 Conventional Commits 风格：`feat:`, `fix:`, `refactor:`, `docs:`,
  `test:`, `chore:`, `build:`。一次提交只做一件事。
- 版本遵循 SemVer；破坏性结构调整升 major，并在 `docs/migration-*.md` 写迁移表。
- 发布：更新 `CHANGELOG.md` → 改 `pyproject.toml` 与 `src/bangumi_catcher/__init__.py`
  的版本（`tests/test_packaging.py` 会校验一致）→ `git tag vX.Y.Z` → push tag，
  `.github/workflows/release.yml` 负责构建与发布。

## 9. 常见陷阱

- **httpx 环境代理**：某些 `NO_PROXY`（如 `[::1]`）会让 httpx 0.28 在构造客户端时崩溃。
  注入测试 transport 时客户端会自动关闭 `trust_env`；用户可设 `api.trust_env: false`。
- **Matplotlib 线程安全**：所有渲染走 `charts.render._RENDER_LOCK`；不要在 UI 线程
  直接 `savefig`。
- **Pydantic computed_field**：`Subject.episodes_total` 必须保留 `eps` 回退；
  删除会让所有完成率归零。
- **`UserCollection.total`**：导入快照后要重置为 `len(items)`，不要相信文件里的值。
- **QThread**：窗口关闭时先 cancel 再等 `finished`，不要 `terminate()`。
- **CSV 公式注入**：任何写进 CSV 的文本都要经过 `reporting.csv_export.spreadsheet_safe_text`。
- **Windows 路径**：用 `pathlib.Path`；不要把路径拼进正则或 shell 字符串。
- **配置路径**：不要在 import 时缓存 `Path.cwd()`；`core/config/paths.py` 每次调用时计算。

## 10. 关键文件索引

- 模型与统计口径：`src/bangumi_catcher/core/models/`、`core/analysis.py`
- 配置与路径：`src/bangumi_catcher/core/config/`
- HTTP 与分页：`src/bangumi_catcher/api/client.py`、`api/collection.py`
- 表格筛选/排序语义：`src/bangumi_catcher/core/query.py`
- 导出：`src/bangumi_catcher/reporting/`、`services/export.py`
- 桌面外壳：`src/bangumi_catcher/ui/main_window.py`、`ui/fetch_bar.py`、`ui/sidebar.py`
- 图表：`src/bangumi_catcher/charts/`
- 测试替身：`tests/fakes.py`、`tests/factories.py`
- 架构规则：`tests/architecture/test_layers.py`

有疑问时：先读 `docs/architecture.md` 与相关 ADR，再读同层现有实现，最后再改。
