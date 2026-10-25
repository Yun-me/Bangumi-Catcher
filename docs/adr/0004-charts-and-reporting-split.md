# 0004. 拆分 charts / reporting，移除 services→ui 依赖

- 状态：Accepted
- 日期：2026-10-25
- 决策者：Bangumi Catcher Contributors

## 背景

3.x 的导出链路：

```text
services/export_service.py
    -> from ui.visualizer import render_all
    -> Jinja2 模板
```

`ui/visualizer.py` 本身不依赖 Qt（只依赖 Matplotlib），但它位于 UI 包中，导致：

- `services` 反向依赖 `ui`，与分层约定冲突；
- CLI 导出 HTML 时必须导入 UI 包，概念上不干净；
- 图表构建器无法在“无桌面”的上下文中被明确视为可复用资产；
- 模板路径依赖 `ui` 包的位置，移动文件容易断。

同时 `ui/chart_page.py` 需要延迟导入 visualizer 以避免启动加载 Matplotlib，
但延迟导入掩盖了包归属问题。

## 决策

1. 新建 `charts/`：
   - `catalog.py`：key + 标题，**无 Matplotlib**，UI 可安全导入；
   - `theme.py`：色板、字体、Figure 工厂；
   - `builders.py`：9 个纯函数构建器；
   - `render.py`：`render_chart` / `render_all`，进程级锁串行化 Agg。
2. 新建 `reporting/`：
   - `csv_export.py`、`json_export.py`、`html.py`、`atomic.py`；
   - HTML 模板仍在 `bangumi_catcher/templates/`，路径相对包根。
3. `services/export.py` 只负责格式注册、默认文件名、进度与原子替换；
   `services` 不再导入 `ui`。
4. UI 的 `ChartPage` 顶层只导入 `charts.catalog`，在 worker 函数内延迟导入
   `charts.render`。
5. 架构测试禁止 `services -> ui`，并禁止 UI 顶层导入 Matplotlib。

## 后果

正面：

- 依赖图变成单向：`services -> reporting -> charts -> core`；
- HTML 导出可在 CLI/测试中无 Qt 运行；
- 图表构建器可直接单元测试（Figure 级别，无需 QApplication）；
- 启动仍然不加载 Matplotlib（有子进程守卫测试）。

代价：

- 多了一个包层级，查找图表代码需要知道 `charts/`；
- 模板路径与包数据配置需要同步（有打包测试）；
- `charts/__init__.py` 必须保持惰性导入，否则 `import bangumi_catcher.charts.catalog`
  会触发 Matplotlib。

## 备选方案

1. **保留 `ui/visualizer.py`，通过回调注入 renderer**：能解依赖，但调用方仍需
   知道 UI 模块，且 HTML 导出的默认路径变得绕。
2. **把导出整体放进 `ui`**：CLI 将被迫依赖 Qt，违背无头可用目标。
3. **把图表放进 `core`**：会让核心层引入 Matplotlib，破坏纯领域层的可测试性。

拆分到 `charts` / `reporting` 是最符合现有依赖方向、且对用户行为无影响的方案。
