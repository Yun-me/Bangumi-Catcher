# CLAUDE.md

本仓库的开发说明统一维护在 [AGENTS.md](AGENTS.md)，请先完整阅读它。

最短路径：

```bash
python -m pip install -e ".[dev]"
python scripts/dev.py check
```

关键约束：测试必须离线；`ui/` 顶层不得导入 Matplotlib；导出必须原子化；
任何结构改动先看 [docs/architecture.md](docs/architecture.md) 与 [docs/adr/](docs/adr/)。
