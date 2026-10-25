# 0002. src 布局与 agent 文档体系

- 状态：Accepted
- 日期：2026-10-25
- 决策者：Bangumi Catcher Contributors

## 背景

3.x 使用扁平的 `bangumi_catcher/` 目录。测试直接从仓库根导入，因此：

- “本地能跑”不等于“安装后能跑”，打包/包数据问题要到最后才暴露；
- 顶层容易出现临时脚本或同名模块，导入优先级不确定；
- 文档只有 README + CHANGELOG，架构知识散落在代码注释里；
- 新加入的 AI agent 没有稳定的入口来了解命令、边界、完成标准与常见陷阱。

## 决策

### src 布局

运行时代码移入 `src/bangumi_catcher/`，`pyproject.toml` 配置：

```toml
[tool.setuptools]
package-dir = { "" = "src" }
```

pytest 通过 `pythonpath = ["src", "."]` 导入；CI 同时做 `pip install -e .` 与
`python -m build`，确保“源码树”和“构建产物”两条路径都被验证。

### agent 文档

- `AGENTS.md` 是**唯一权威**开发说明：启动、地图、依赖规则、不变量、测试策略、
  代码约定、完成标准、陷阱、关键文件索引。
- `CLAUDE.md`、`.cursor/rules/project.mdc`、`.github/copilot-instructions.md`
  只是短指针，避免多份规则漂移。
- `docs/` 按主题拆分：架构、开发、测试、约定、数据口径、配置、打包、迁移、
  playbooks、ADR。
- `python scripts/dev.py` 是唯一任务入口（跨平台、无第三方依赖），Makefile 只是
  薄包装；文档与 CI 使用同一组命令。

### 可执行的文档

- `tests/test_docs.py` 检查必需文档存在、相对链接可解析、CHANGELOG 版本与
  包版本一致；
- `tests/test_packaging.py` 检查 src 布局、入口点可导入、模板/`py.typed` 被打包；
- 架构规则见 ADR-0001。

文档不是装饰品：链接失效或入口点写错会让 CI 失败。

## 后果

正面：

- 测试与安装使用同一份代码路径，打包问题提前暴露；
- agent 有一个短而完整的入口，减少“读半个仓库”的上下文成本；
- 文档结构稳定，新增主题有明确位置；
- 任务命令统一，Windows 不需要 Make。

代价：

- 必须 `pip install -e .` 或让 `scripts/dev.py` 设置 `PYTHONPATH`；
- 移动文件时要同步更新文档链接（测试会提醒）；
- 多维护几个指针文件（成本很低，内容是刻意的短）。

## 备选方案

1. **保持扁平布局**：少一次迁移，但无法解决安装/导入不一致。
2. **只用 README 承载所有说明**：会变成数千行、难以维护的单文件。
3. **依赖外部 wiki**：与代码不同步，agent 也无法在仓库内检索。

选择 src + 分层文档 + 可执行守卫，让“正确做法”成为默认路径。
