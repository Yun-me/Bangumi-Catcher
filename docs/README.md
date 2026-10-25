# 文档索引

仓库的开发说明以 [AGENTS.md](../AGENTS.md) 为唯一权威入口。本目录提供更细的背景资料。

| 文档 | 内容 | 适合谁 |
|---|---|---|
| [architecture.md](architecture.md) | 分层、依赖方向、数据流、扩展点 | 改结构前必读 |
| [development.md](development.md) | 环境、任务、调试、发布 | 新贡献者 |
| [testing.md](testing.md) | 测试分层、夹具、离线替身、UI 测试 | 写测试时 |
| [conventions.md](conventions.md) | 命名、类型、错误、日志、提交 | 所有改动 |
| [data-model.md](data-model.md) | Bangumi API 形态、统计口径、快照 schema | 改抓取/统计时 |
| [configuration.md](configuration.md) | 配置优先级、字段、环境变量 | 改配置/部署时 |
| [packaging.md](packaging.md) | wheel、PyInstaller、发布流程 | 发布时 |
| [migration-4.0.md](migration-4.0.md) | 3.x → 4.0 的路径与行为变化 | 从旧版本升级 |
| [playbooks/](playbooks/README.md) | 常见改动的分步清单 | 动手前 |
| [adr/](adr/README.md) | 架构决策记录（为什么这样做） | 质疑设计时 |

约定：文档里的命令都应在仓库根目录执行；路径使用 `/` 表示，Windows 下等价。
