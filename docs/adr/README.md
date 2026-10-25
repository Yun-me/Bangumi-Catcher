# 架构决策记录（ADR）

ADR 记录**为什么**这样设计，而不是操作步骤。改变分层、目录、依赖方向或关键
技术选型时新增一条，编号递增，永不删除旧记录（可将状态改为 `Superseded`）。

| 编号 | 标题 | 状态 |
|---|---|---|
| [0001](0001-layered-architecture.md) | 分层架构与单向依赖 | Accepted |
| [0002](0002-src-layout-and-agent-docs.md) | src 布局与 agent 文档体系 | Accepted |
| [0003](0003-offline-first-testing.md) | 离线优先的测试策略 | Accepted |
| [0004](0004-charts-and-reporting-split.md) | 拆分 charts / reporting，移除 services→ui 依赖 | Accepted |

模板：

```markdown
# NNNN. 标题

- 状态：Proposed / Accepted / Superseded by NNNN
- 日期：YYYY-MM-DD
- 决策者：...

## 背景
## 决策
## 后果
## 备选方案
```
