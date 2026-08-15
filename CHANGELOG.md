# 更新日志

本文件记录本项目所有值得注意的变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循[语义化版本（SemVer）](https://semver.org/lang/zh-CN/)。

<!-- 下一个版本的变更请记录在此处。 -->

## [2.0.0] - 2026-06-20

> **大版本更新：源头性重构。** 从“单体脚本式”架构升级为分层、可测试、可脚本化的现代 Python 项目。

### 新增 (Added)

- **命令行模式**：新增 `bangumi_catcher/cli.py`，支持 `fetch` / `clear-cache` / `version` 子命令，可无 GUI 抓取并导出 CSV/JSON/HTML。
- **服务层**：新增 `bangumi_catcher/services`，GUI 与 CLI 共用同一套抓取/分析编排逻辑，消除重复实现。
- **类型化配置**：`config.py` 从裸 dict 升级为 Pydantic 模型（`AppConfig`），提供字段校验、环境变量覆盖、`save_config` 写回能力。
- **设置对话框**：GUI 新增「工具 → 设置…」，可编辑 API 地址、超时、代理、并发、缓存 TTL、排行数量与默认主题。
- **日志对话框**：GUI 新增「工具 → 运行日志…」入口。
- **代理支持**：`api.proxy` 配置真实生效，可直连或走本地代理访问 Bangumi。
- **GitHub Actions CI**：新增 `.github/workflows/ci.yml`，Python 3.9 / 3.12 矩阵自动执行 ruff、pytest、CLI smoke。
- **工程化文件**：新增 `.editorconfig`，`pyproject.toml` 增加 CLI script 与模板打包配置。

### 架构重构 (Architecture)

- 主窗口从 700+ 行 `gui.py` 拆分为：
  - `ui/main_window.py`：主窗口
  - `ui/workers.py`：QThread 后台任务
  - `ui/widgets.py`：可复用组件（卡片、搜索代理）
  - `ui/dialogs.py`：设置/日志对话框
  - `ui/gui.py`：薄入口
- 核心层、服务层、UI 层职责分离，模块边界清晰。

### 修复 (Fixed)

- **matplotlib 后端被覆盖**：`visualizer.py` 不再无条件调用 `matplotlib.use("Agg")`，避免覆盖 GUI 的 Qt 后端。
- **HTML 报告图表缓存串数据**：每次新报告都会清空旧图表缓存。
- **取消响应不及时**：抓取过程新增 `cancel_check` 快速中断，并正确取消并发任务。
- **模板路径失效**：重构后模板路径同步更新。
- **配置年份硬编码**：`analysis.year_end` 默认改为当前年份。
- **配置无法写回**：新增 `save_config`，设置对话框可持久化修改。

### 变更 (Changed)

- 顶部栏改为自适应布局，小窗口不再挤压。
- `APP_VERSION` 统一从包版本读取。
- 收藏总表新增状态筛选、右键菜单。
- 图表新增「热门标签 Top 15」，总数由 8 增至 9。

### 性能 (Performance)

- 分析引擎使用 `heapq.nlargest` 取 Top N，避免全量排序。
- 抓取/分析通过服务层复用，减少重复计算路径。

### 测试 (Tests)

- 测试总数提升至 58 个。
- 新增 CLI 测试、类型化配置测试、标签统计断言，并同步图表数量断言。

## [1.2.2] - 2026-06-20

> **首个正式发布版本。** 1.2.2 之前的条目为公开发布前的开发迭代记录，一并保留以便追溯。

### 修复 (Fixed)

- **全站评分无法获取（导致相关图表空白）**：收藏列表内联的 `SlimSubject` 将评分存放在扁平的 `score` / `rank` 字段，而旧版 `_build_subject` 仅读取嵌套的 `rating` 对象，致使所有内联条目的全站评分恒为 0；又因这些条目自带 `date`，补全逻辑被跳过，评分始终无法拉取。现 `_build_subject` 同时兼容「扁平 `score`」与「嵌套 `rating`」两种结构，全站评分、「评分对比」图表及最爱排行中的全站分均恢复正常。
- **完成度计算错误**：由两处原因叠加——其一，`SlimSubject` 只有 `eps` 而无 `total_episodes`，旧版以 `total_episodes` 作分母致其恒为 0；其二，「看过」条目在 Bangumi 上常为 `ep_status=0`，旧版会将其误算为 0%。现新增 `episodes_total`（优先取 `total_episodes`，回退 `eps`），并修正语义：看过 = 100%，在看 / 搁置 / 抛弃按「已看 / 总集数」计算，想看 = 0。
- **「我的进度」展示不当**：`ep_status` 此前已能获取，但界面仅显示一个恒为 0 的完成百分比，无法反映实际进度。现「进度」列改为直接展示「已看 / 总集数」「看到第 N 话」或「看完 · 全 N 话」，进度一目了然。

### 变更 (Changed)

- 「进度」列加宽，以容纳更丰富的进度文案。

### 性能 (Performance)

- **抓取提速**：内联 `SlimSubject` 已包含名称、年份、全站评分、集数与封面，足以支撑完整展示；因此仅在条目详情确实缺失时才触发补全请求，省去了旧版「每条收藏额外发起一次请求」的开销。

### 测试 (Tests)

- 新增 `tests/test_subject_build.py`（覆盖扁平 / 嵌套评分映射、`eps` 回退、`short_summary` 回退）与 `tests/test_completion.py`（覆盖看过 = 100%、在看回退、想看 = 0 等完成率语义）。

## [1.2.1] - 2026-06-19

承接 v1.2.0，修复一批「配置项形同虚设」与缓存相关的缺陷，并完善收藏搜索。

### 修复 (Fixed)

- **`cache.ttl` 与缓存目录此前被忽略**：客户端从不读取 `cache` 配置段，收藏缓存恒用硬编码的 1 小时有效期，自定义目录也不生效。现 `cache.enabled` / `cache.ttl` / `cache.dir` 均真实生效；「清除缓存」也改为清理配置指定的目录。
- **`rate_limit_delay` 此前为无效配置**：v1.2.0 分页并发化后，该字段不再被任何代码使用。现接入真正的异步限速器以约束请求的最小发起间隔。默认值为 `0.0`（不额外限速，仅受 `max_concurrent` 约束，不改变 v1.2.0 的默认抓取速度）；遇到 429 限流时可调至 0.2~0.5 主动放慢。
- **缓存键未区分收藏类型**：`collection_key` 此前仅含用户名与 `subject_type`，直接调用 API 按不同 `collection_type`（如「全部」与「仅想看」）抓取时会相互覆盖。现已将收藏类型并入缓存键。
- **注入的缓存被误关闭**：`async with` 退出时无条件关闭缓存；若缓存由外部传入，会影响调用方复用。现仅关闭客户端自行创建的缓存。

### 变更 (Changed)

- **收藏搜索覆盖短评**：搜索框提示为「作品名 / 标签 / 评价」，但旧版仅匹配可见列，搜不到未单独成列的短评。新增 `_SearchProxy`，将「名称 + 标签 + 短评」预拼为统一的可搜索文本，使提示与实际行为一致。

### 测试 (Tests)

- 新增 `tests/test_ratelimit_cache.py`：覆盖限速器（0 不等待、>0 真实间隔、负值收敛）与「缓存键含收藏类型」。

## [1.2.0] - 2026-06-19

面向稳定性与体验的重构，**不改变核心功能与对外接口**，已抓取的数据与缓存保持兼容。

### 修复 (Fixed)

- **修复脏数据导致整次抓取崩溃**：当接口对某条收藏返回 `"rate": null` 或越界评分时，旧版数据层的硬约束（`ge=0, le=10`）会直接抛错并中断整次抓取。现改用 `mode="before"` 的宽松校验器，单条脏数据就地收敛（`null` / 非数字归零、评分收敛至 `[0, 10]`），不再影响整体。`type` / `ep_status` / `vol_status` / `tags`（兼容 `null`、字符串列表及 `{"name": ...}` 对象列表）以及 `Subject` 的 `eps` / `total_episodes` / `rank` 同步加固。
- **消除翻页死循环风险**：抓取逻辑由 `while True` 改为按 `offset` 计算页码，待抓取页数由 `total` 唯一确定，即便接口返回异常 `total` 也不会无限翻页。
- **精确的错误归类**：用户不存在 / 主页隐私 → `NotFoundError`（404）；空收藏 → `EmptyCollectionError`；限流 → `RateLimitError`（429，读取 `Retry-After`）；其余 4xx / 5xx、网络异常与非 JSON 响应均有明确的中文提示与解决指引。
- **修复 Qt 线程生命周期**：抓取线程结束后正确调用 `deleteLater` 并清理引用，避免重复抓取时出现「destroyed while running」及对象堆积。

### 变更 (Changed)

- 移除蓝色渐变头部横幅，改为带 1px 底边的扁平表面头部；收敛圆角（卡片 14 → 8px、控件 8 → 6px）。
- 统计卡片去除彩虹色块，改以字号 / 字重搭配浅阴影建立层级；图表配色随亮 / 暗主题自动重着色（修复旧版暗色模式下图表仍为浅色的不一致问题）。
- 全量移除界面与 HTML 报告中的装饰性 emoji，文案与配色趋于克制。

### 性能 (Performance)

- **并发分页**：先获取首页拿到 `total`，再按 `offset` 并发抓取其余页（以信号量限制并发，配合 `asyncio.as_completed`），取代旧版「逐页串行 + 每页 sleep」。
- **合并去重**：多页结果按 `offset` 升序合并并按 `subject_id` 去重，规避抓取过程中 `total` 抖动造成的重叠。
- 并发数（`max_concurrent`，默认 8）与请求最小间隔（`rate_limit_delay`，默认下调至 0.5s）均可配置。

### 内部 (Internal)

- 抽出 `compute_remaining_offsets` / `merge_pages` 两个纯函数，使分页核心逻辑可独立单测。
- 新增 `tests/test_pagination.py` 与 `tests/test_models_coercion.py`，锁定上述两处关键修复。
- `pyproject.toml` 补全 `[tool.ruff]` 与 `[tool.pytest.ini_options]` 配置。
- 修正 `User-Agent` 与仓库占位信息，统一为真实仓库地址。

## [1.1.0] - 2026-06-18

框架级重构：**GUI 与图表引擎全量替换**，并修复 v1.0.0 上线后反馈的多个数据正确性缺陷。

### 新增 (Added)

- **缓存层**：基于 diskcache，收藏 1 小时 / 条目详情 7 天 TTL，API 请求优先命中缓存。
- **多格式导出**：CSV、JSON 及自包含 HTML（Jinja2 模板 + matplotlib base64 内嵌图表，单文件即可离线分享）。
- **分析维度**：评分分布、收藏状态饼图、年度趋势、年度均分、Top 15 排行、季度分布、「我的评分 vs 全站均分」散点图、收藏状态年度堆叠。
- **双色主题**：亮 / 暗一键切换，QSS 与 matplotlib 图表配色同步。
- **一键打包**：`python build.py` 输出 82MB 单文件 exe，双击即用。

### 变更 (Changed)

- **GUI 框架**：Tkinter → **PySide6 / Qt**。引入 `FlowLayout`（响应式换行布局）、Signal/Slot 线程模型与 QSS 双色主题（亮 / 暗）。
- **图表引擎**：plotly + kaleido → **matplotlib**（Agg + QtAgg）。体积缩减约 100MB，不再依赖 headless Chromium 子进程；图表以 `FigureCanvasQTAgg` 嵌入界面，随窗口实时缩放重绘，不再是固定 PNG。

### 修复 (Fixed)

- **环境变量嵌套覆盖失效**：`config.py` 加载逻辑中 `target = target` 未推进指针，导致 `BANGUMI_*` 环境变量无法覆写嵌套键。现改为 `target = target[k]`。
- **年度均分分母包含未评分条目**：`analyzer.py` 的年度评分计算改为先收集有效评分列表再统一求均值，未评分条目不再拉低分母。
- **分页跳页丢数据**：`api.py` 中 `offset += limit` 在「`limit` > 页面实际返回数」时会跳过条目。现改为 `offset += len(data_list)`。
- **Pydantic 拒绝 API `null`**：API 返回 `comment` / `name` 等字段为 `null` 时，Pydantic v2 直接抛错。现为相关字段添加 `@field_validator(mode="before")`，将 `None` 转为空串。
- **完成率图非法属性**：plotly 的 `alpha` 参数移植到 matplotlib 时报错，现改用 RGBA 色值。
- **配置在 exe 中失效**：冻结后找不到外部 `config.yaml`。现改为代码内嵌 `DEFAULT_CONFIG`，外部文件降级为可选覆盖；`build.py` 同步打包 `config.yaml`。
- **PyInstaller 构建问题**：修复 `.spec` 绝对路径、UPX 误报及打包产物残留 Tkinter 的问题。统一改用 `build.py`，添加 `--noupx`，并排除 `tkinter` 与未引用的 Qt 子模块以瘦身。

## [1.0.0] - 2026-06-14

项目初始化，建立基本骨架与核心数据流。

### 新增 (Added)

- **GUI 框架**：Tkinter（后于 v1.1.0 替换为 PySide6）。
- **图表引擎**：plotly + kaleido（后于 v1.1.0 替换为 matplotlib）。
- **HTTP 客户端**：基于 httpx 的异步请求，支持分页抓取 Bangumi v0 API 用户收藏。
- **数据模型**：基于 Pydantic 的 `Subject` / `CollectionItem` / `UserCollection` 模型。
- **分析引擎**：基本统计维度（评分分布、类型分布、年度趋势、完成率）。
- **HTML 报告**：Jinja2 模板，图表以 base64 data-URI 内嵌。
- **数据导出**：CSV 格式导出收藏列表。
- **打包**：PyInstaller 生成独立 exe（初始方案，多处配置问题于 v1.1.0 修复）。