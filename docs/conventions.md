# 代码与协作约定

## 格式化与静态检查

- 格式化与 lint：`ruff`，line-length 110，target py39。不要手工对齐或调整空行。
- 类型：新增/修改的公共代码必须有注解；`mypy` 覆盖 `core`、`api`、`charts`、
  `reporting`、`services`、`observability`。UI 层允许 Qt 的动态性，但不要滥用 `Any`。
- import：绝对导入优先；同包内用相对导入。`ruff` 的 isort 规则负责排序。

```bash
python scripts/dev.py fmt
python scripts/dev.py lint
python scripts/dev.py type
```

## 命名

- 模块/函数/变量：`snake_case`；类：`PascalCase`；常量：`UPPER_SNAKE_CASE`。
- 布尔值用 `is_` / `has_` / `should_` 前缀；回调以 `on_` 命名参数、以动词命名函数。
- 私有实现用单下划线；测试不依赖私有成员，除非在测生命周期且没有公开替代。
- Qt 重写方法保留 Qt 的驼峰名，并加 `# noqa: N802`（若启用 N 规则）。

## 文档字符串与注释

- 公共模块、类、函数写英文 docstring，说明**契约**（参数、返回值、异常、副作用）。
- 面向用户的字符串用中文；错误信息要能指导用户下一步做什么。
- 注释解释“为什么”，尤其是历史 bug 与 API 怪癖；不要复述代码。
- 复杂算法在 docstring 给出不变量，例如“offset 由 total 唯一确定，不会死循环”。

## 错误处理

- 可预期失败抛 `core.errors.BangumiError` 子类；库代码不要 `print` 或 `sys.exit`。
- 重试只用于网络/5xx/429；4xx（除 429）立即失败并给出可理解消息。
- CLI 在 `cli/main.py` 统一捕获 `BangumiError`、`ValueError`、`OSError`、
  `yaml.YAMLError`，返回 1；`KeyboardInterrupt` 返回 130。
- UI 把异常显示为状态栏/反馈条，不弹 traceback；后台任务异常由 `TaskRunner.failed` 上报。
- 单条脏数据不应中断整次抓取：在模型校验器中收敛，或在映射层跳过并 `logger.warning`。

## 日志

- 模块级 `logger = logging.getLogger(__name__)`。
- INFO 记录用户可理解的阶段（缓存命中、页数、导出路径）；WARNING 记录可恢复异常；
  ERROR 留给失败；DEBUG 记录请求/缓存键等诊断细节。
- 不要记录用户短评全文或代理凭据；URL 可以记录，但避免带查询参数的隐私内容。

## Qt / UI

- 后台工作放 `TaskRunner`；worker 线程不碰 QWidget，只用 Signal 回传。
- 关闭窗口：先 `cancel()`，等 `busy_changed(False)`/`finished`，再 `close()`；
  禁止 `QThread.terminate()`。
- 图表渲染在 worker 内延迟导入 `charts.render`；UI 顶层不得 import matplotlib。
- 表格排序/筛选规则放 `core.query`，Qt 模型只负责缓存与映射。
- 新增页面在 `ui/navigation.py` 注册，保持 `main_window` 只做组合与生命周期。
- 可访问性：输入框、按钮设置 `setAccessibleName` / tooltip；快捷键在菜单中声明。

## 配置

新增字段时同时更新：

1. `core/config/models.py`（默认值 + 校验）；
2. `config.yaml`（示例与注释）；
3. `docs/configuration.md`（字段表）与本仓库相关 playbook；
4. `ui/settings_dialog.py`（如果用户应该能改）；
5. 测试（默认值、env 覆盖、校验）。

配置对象通过参数显式传递，不用模块级全局单例。

## 文件与路径

- 一律 `pathlib.Path`；用户目录用 `core/config/paths.py`。
- 写入用户数据必须原子化（`reporting.atomic_output`）或至少临时文件 + replace。
- 不把机器绝对路径写进仓库、测试或文档示例。

## 文档

- 用户向：`README.md`；贡献者/agent：`AGENTS.md`；深入说明：`docs/`。
- 改动行为、命令、目录结构时同步更新文档；`tests/test_docs.py` 会检查链接。
- 架构级决策写 ADR（`docs/adr/NNNN-*.md`），并在 `docs/adr/README.md` 建索引。

## 提交与 PR

- Conventional Commits：`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `build:`。
- 一个提交只做一件事；重构与行为变更分开，便于 review 与回滚。
- PR 描述包含：动机、行为变化、测试方式、截图（UI）、兼容性/迁移说明。
- 合并前必须：`python scripts/dev.py check` 通过，CI 绿，文档与 CHANGELOG 已更新。
