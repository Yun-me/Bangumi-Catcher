<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PySide6-41CD52" alt="PySide6">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

<h1 align="center">Bangumi Catcher</h1>

<p align="center"><strong>Bangumi 用户收藏抓取与可视化分析工具 —— 桌面 GUI + 命令行双模式</strong></p>

---

## 特性

| 功能 | 说明 |
|---|---|
| 双模式 | 现代化 PySide6 桌面界面 + 可脚本化的 CLI 命令行 |
| 分层架构 | `core`（领域/数据）、`services`（用例编排）、`ui`（界面）三层解耦 |
| 类型化配置 | Pydantic 配置模型，支持 YAML / 环境变量 / CLI / 设置对话框 |
| 实时图表 | matplotlib 画布随窗口重绘、主题自适应；评分、状态、年度、季度、标签、排行等 9 类图表 |
| 收藏总表 | 可搜索、可排序、可按状态筛选；双击/右键打开或复制条目链接 |
| 后台执行 | QThread + 异步 HTTP，进度平滑反馈，取消响应快速 |
| 并发抓取 | httpx 异步并发分页 + 自动重试 + 限速 + 代理支持 |
| 本地缓存 | diskcache 持久化，可配置 TTL/目录，支持强制刷新与缓存管理 |
| 多格式导出 | CSV / JSON / 报告 JSON / 自包含 HTML 报告 |
| 工程化 | GitHub Actions CI、ruff、pytest、PyInstaller 打包脚本 |

---

## ⚠️ 网络要求

Bangumi（bgm.tv）在中国大陆境内可能被 DNS 污染 / SNI 封锁，请开启系统代理或 VPN。

也可以在 GUI「工具 → 设置」或 `config.yaml` 中配置 `api.proxy`：

```yaml
api:
  proxy: "http://127.0.0.1:7890"
```

---

## 安装与运行

### 从源码

```bash
git clone https://github.com/Yun-me/Bangumi-Catcher.git
cd Bangumi-Catcher
pip install -e ".[dev]"
```

启动 GUI：

```bash
python -m bangumi_catcher        # 或 python run.py
```

启动 CLI：

```bash
python -m bangumi_catcher.cli --help
```

### 自行打包

```bash
pip install pyinstaller
python build.py                  # 输出 dist/BangumiCatcher
```

---

## CLI 用法

```bash
# 查看版本
python -m bangumi_catcher.cli version

# 抓取并打印摘要
python -m bangumi_catcher.cli fetch <username>

# 导出 CSV / JSON / 报告 JSON / HTML
python -m bangumi_catcher.cli fetch <username> --format csv --output collection.csv
python -m bangumi_catcher.cli fetch <username> --format html --output report.html

# 强制刷新
python -m bangumi_catcher.cli fetch <username> --force-refresh

# 清空缓存
python -m bangumi_catcher.cli clear-cache
```

---

## 项目结构

```
Bangumi-Catcher/
├── .github/workflows/ci.yml     # GitHub Actions CI
├── bangumi_catcher/
│   ├── core/                    # 领域与数据层
│   │   ├── api.py               # httpx 异步 API 客户端
│   │   ├── analyzer.py          # 统计分析引擎
│   │   ├── cache.py             # diskcache 缓存
│   │   ├── config.py            # 类型化 Pydantic 配置
│   │   ├── exceptions.py        # 异常体系
│   │   ├── export.py            # CSV / JSON 导出
│   │   └── models.py            # Pydantic 数据模型
│   ├── services/                # 用例编排层
│   │   └── fetch_service.py     # GUI 与 CLI 共用的抓取/分析服务
│   ├── ui/                      # PySide6 界面层
│   │   ├── main_window.py       # 主窗口
│   │   ├── workers.py           # QThread 后台任务
│   │   ├── widgets.py           # 可复用组件
│   │   ├── dialogs.py           # 设置/日志对话框
│   │   ├── theme.py             # 亮/暗主题
│   │   ├── flowlayout.py        # 响应式布局
│   │   ├── visualizer.py        # matplotlib 图表
│   │   └── gui.py               # GUI 入口（兼容旧路径）
│   ├── cli.py                   # 命令行入口
│   ├── templates/               # HTML 报告模板
│   ├── __init__.py
│   └── __main__.py
├── tests/                       # pytest 测试套件
├── run.py                       # 开发/打包入口
├── build.py                     # PyInstaller 脚本
├── config.yaml                  # 可选外部配置
├── pyproject.toml
└── requirements.txt
```

---

## 配置

配置为类型化 Pydantic 模型，默认值内嵌，外部 `config.yaml` 可选覆盖，也支持环境变量（嵌套用 `__`）：

```bash
export BANGUMI_API__TIMEOUT=60
export BANGUMI_COLLECTION__MAX_CONCURRENT=4
export BANGUMI_ANALYSIS__TOP_N=30
```

常用配置：

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `api.base_url` | `https://api.bgm.tv` | API 地址 |
| `api.timeout` | 30 | 单次请求超时（秒） |
| `api.proxy` | 空 | HTTP 代理地址 |
| `api.max_retries` | 3 | 失败重试次数 |
| `collection.max_concurrent` | 8 | 最大并发请求数 |
| `collection.rate_limit_delay` | 0.0 | 请求最小发起间隔（秒） |
| `cache.enabled` | true | 是否启用本地缓存 |
| `cache.ttl` | 3600 | 收藏缓存有效期（秒） |
| `cache.dir` | "" | 缓存目录，留空 = `~/.cache/bangumi-catcher` |
| `analysis.top_n` | 20 | 最爱排行 / 热门标签数量 |
| `ui.theme` | `system` | `system` / `light` / `dark` |

---

## 开发

```bash
pip install -e ".[dev]"
pytest -q
ruff check bangumi_catcher tests
```

GitHub Actions 会在每次 push/PR 自动执行 lint + test + CLI smoke。

---

## 致谢

数据来源：[Bangumi 番组计划](https://bgm.tv) · 请遵守其 API 使用条款与频率限制。

## License

MIT © Bangumi Catcher Contributors
