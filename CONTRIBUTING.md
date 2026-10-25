# 贡献指南

感谢你愿意改进 Bangumi Catcher。这个项目同时面向人类与 AI agent，因此我们把
“如何改”写成了可执行的规则，而不是靠口口相传。

## 开始之前

1. 阅读 [AGENTS.md](AGENTS.md)（唯一权威开发说明）。
2. 按需阅读：
   - [docs/architecture.md](docs/architecture.md)：分层与依赖方向；
   - [docs/testing.md](docs/testing.md)：测试分层与离线替身；
   - [docs/conventions.md](docs/conventions.md)：代码与提交约定；
   - [docs/playbooks/](docs/playbooks/README.md)：常见改动的分步清单。
3. 使用 Python 3.9+；建议虚拟环境：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## 提交前检查

```bash
python scripts/dev.py check      # ruff + mypy + pytest
python scripts/dev.py smoke      # 导入与 CLI 冒烟
```

要求：

- 所有测试离线、可重复；新增网络行为请用 `tests/fakes.py` 的 `FakeBangumiAPI`；
- 分层规则（`tests/architecture/test_layers.py`）保持通过；
- 移动/重命名文件后更新文档链接（`tests/test_docs.py` 会检查）；
- 用户可见变化更新 `CHANGELOG.md` 的 `Unreleased`；
- UI 变化附截图（可放在 PR 描述中，不必提交到仓库）。

## 提交信息

使用 Conventional Commits：

```text
feat: 支持按标签最小值筛选
fix: 修复取消后仍写入缓存的问题
refactor: 拆分 reporting 层的 HTML 渲染
docs: 补充 CLI config 命令说明
test: 覆盖空收藏的年度统计
chore: 升级 ruff 配置
build: 打包时包含 py.typed
```

一次提交只做一件事；重构与行为变更分开，方便 review 与回滚。

## Pull Request

PR 描述请包含：

1. **动机**：解决什么问题，关联 issue；
2. **行为变化**：用户可见差异、兼容性/迁移说明；
3. **测试方式**：新增/修改了哪些测试，手动验证了什么；
4. **截图**：UI 改动前后对比（可选但推荐）。

小而聚焦的 PR 更容易合并。涉及架构、依赖或数据口径的改动，请先开 issue 或
在 PR 中说明，并考虑新增 [ADR](docs/adr/README.md)。

## 报告问题

请使用 issue 模板，并提供：

- 操作系统、Python 版本、安装方式（`pip` / 源码 / 打包版）；
- 复现步骤与期望/实际结果；
- 相关日志（`-v` 或「工具 → 运行日志」），注意隐去隐私信息；
- 如果是网络问题，说明代理/限流/错误码情况。

## 代码风格

- 格式化与 lint 交给 `ruff`；类型检查交给 `mypy`。
- 公共 docstring 用英文，用户可见文本用中文。
- 不引入新运行时依赖除非有充分理由（先写 ADR）。
- 不提交 `output/`、`reports/`、`dist/`、缓存或本机配置。

## 行为准则

保持友善、就事论事。数据来源于 Bangumi，请尊重其 API 使用约定与社区规则。
