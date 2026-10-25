# 0001. 分层架构与单向依赖

- 状态：Accepted
- 日期：2026-10-25
- 决策者：Bangumi Catcher Contributors

## 背景

3.x 的代码已经按 `core` / `services` / `ui` 分目录，但边界是约定而非约束：

- `core` 同时承担模型、配置、HTTP、缓存与导出，依赖面很宽；
- `services/export_service` 为了渲染 HTML 图表直接导入 `ui.visualizer`，
  形成 `services -> ui` 的反向依赖；
- UI 的表格筛选/排序规则嵌在 Qt 模型里，无法脱离 Qt 测试；
- 新贡献者（或 agent）需要读多个大文件才能确定“这段逻辑该放哪”。

目录存在不等于架构存在。我们需要可执行的边界。

## 决策

把运行时包分为七层，并规定单向依赖：

```text
core  ←  api  ←  services  →  reporting  →  charts
                    ↑
                   ui / cli
```

- `core`：模型、配置、异常、分析、查询语义。只依赖标准库 + pydantic + yaml。
- `api`：HTTP、分页、缓存、限速。依赖 `core` + httpx + diskcache。
- `charts`：Matplotlib 构建与渲染。依赖 `core` + matplotlib。
- `reporting`：CSV/JSON/HTML 与原子写。依赖 `core` + `charts` + jinja2。
- `services`：编排与取消。依赖 `core` + `api` + `reporting`，**不依赖 UI**。
- `ui` / `cli`：组合根，可依赖内部任意层；CLI 只在 `gui` 命令懒加载 Qt。

边界由 `tests/architecture/test_layers.py` 解析 AST 强制执行。新增模块自动纳入
检查；要打破规则必须先写 ADR 并修改测试，而不是悄悄 import。

同时把纯规则下沉：

- 表格搜索/排序/筛选 → `core/query.py`（无 Qt，可直接单测）；
- 图表构建 → `charts/`（GUI 与 HTML 共用）；
- 导出格式 → `reporting/`（writer） + `services/export.py`（编排）。

## 后果

正面：

- 依赖方向可机器验证，重构时不会悄悄产生环；
- `core` 的测试不需要安装 Qt/httpx；
- HTML 导出可以在无 GUI 的 CLI/CI 中运行；
- 新代码的归属一目了然，agent 不需要跨层猜。

代价：

- 文件数量增加（`models/`、`config/`、`api/` 都是包），需要维护 `__init__` re-export；
- 小的功能可能要在 2–3 个文件里各加一点；
- 分层测试对“移动文件”很敏感，必须同步修改 import。

## 备选方案

1. **保持三目录，仅靠 review**：成本低，但已经出现过反向依赖；不可执行。
2. **事件总线/插件架构**：解耦更强，但当前没有第三方扩展需求，会增加启动与调试成本。
3. **把所有逻辑放进 services**：会让 services 变成新的上帝模块，且 UI 仍需 Qt 特定逻辑。

选择分层 + 自动守卫，是在当前规模下收益/成本最平衡的方案。
