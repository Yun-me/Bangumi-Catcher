<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PySide6-41CD52" alt="PySide6">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

<h1 align="center">Bangumi Catcher</h1>

<p align="center"><strong>Bangumi 用户收藏抓取与可视化分析桌面工具 —— 输入用户 ID，一键生成分析报告</strong></p>

---

## 特性

| 功能 | 说明 |
|---|---|
| 桌面界面 | 基于 **PySide6 (Qt)**，响应式布局，窗口缩放/全屏自动重排，亮/暗双主题 |
| 实时图表 | matplotlib 画布随窗口实时重绘，且随主题切换自动重着色；评分分布、状态分布、年度趋势、年度均分、季度分布、最爱排行等 |
| 收藏总表 | 全部收藏的可搜索、可排序数据表；双击跳转 Bangumi 条目页 |
| 后台执行 | 抓取/分析在后台线程执行，进度条全程平滑反馈，可随时取消 |
| 并发抓取 | httpx 异步并发拉取条目详情，按页偏移并发分页 + 自动重试 + 速率限制 |
| 本地缓存 | diskcache 持久化，同一用户默认 1 小时内不重复请求；支持「强制刷新」 |
| 多格式导出 | CSV / JSON / 自包含 HTML 报告（可一键在浏览器打开） |
| 状态记忆 | 自动记住上次用户名、窗口大小与主题偏好 |

---

## ⚠️ 网络要求

Bangumi（bgm.tv）在中国大陆境内已被 DNS 污染 / SNI 封锁，直接访问会超时或无法连接。**请务必开启系统代理或 VPN 后再使用本工具**，否则抓取会失败。

推荐方式：
- 开启全局代理（如 Clash Verge、v2rayN、sing-box 等），确保 `bgm.tv` 和 `api.bgm.tv` 可访问
- 或在 `config.yaml` 中配置 `api.base_url` 指向可用的反代地址

验证方法：浏览器打开 https://bgm.tv 确认能正常加载。

---

## 使用方式

### 下载可执行文件（推荐）

从 [Releases](https://github.com/Yun-me/Bangumi-Catcher/releases) 下载并双击运行，无需安装 Python。

### 从源码运行

```bash
git clone https://github.com/Yun-me/Bangumi-Catcher.git
cd Bangumi-Catcher
pip install -r requirements.txt
python -m bangumi_catcher        # 或 python run.py
```

### 自行打包

```bash
pip install pyinstaller
python build.py                  # 输出 dist/BangumiCatcher
```

---

## 开发

```bash
pip install -e ".[dev]"
pytest -q                        # 运行测试（Qt 用 offscreen，无需显示器）
ruff check bangumi_catcher       # 代码检查（规则见 pyproject.toml）
```

---

## 项目结构

```
Bangumi-Catcher/
├── bangumi_catcher/
│   ├── gui.py            # PySide6 主窗口（响应式布局 + 后台线程）
│   ├── theme.py          # Qt QSS 主题（亮/暗）
│   ├── flowlayout.py     # 自动换行布局（响应式核心）
│   ├── visualizer.py     # matplotlib 图表（GUI 实时 + HTML 导出共用，主题感知）
│   ├── api.py            # httpx 异步 API 客户端（并发分页 + 重试 + 缓存 + 进度回调）
│   ├── models.py         # Pydantic v2 数据模型（带宽松字段校验）
│   ├── analyzer.py       # 多维统计分析引擎（单遍 O(n)）
│   ├── export.py         # CSV / JSON 导出
│   ├── config.py         # 配置（内嵌默认 + YAML + 环境变量覆盖）
│   ├── cache.py          # diskcache 缓存层
│   ├── exceptions.py     # 异常体系
│   └── templates/        # HTML 报告模板
├── tests/                # pytest 测试套件
├── run.py                # 打包入口
├── build.py              # PyInstaller 脚本
├── config.yaml           # 可选外部配置
├── pyproject.toml
└── requirements.txt
```

---

## 配置

默认配置已内嵌，开箱即用。如需自定义，在工作目录放置 `config.yaml`，或用环境变量覆盖（嵌套用 `__`）：

```bash
export BANGUMI_API__TIMEOUT=60
export BANGUMI_COLLECTION__MAX_CONCURRENT=4
export BANGUMI_ANALYSIS__TOP_N=30
```

常用项：

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `api.timeout` | 30 | 单次请求超时（秒） |
| `api.max_retries` | 3 | 失败重试次数 |
| `api.max_concurrent` | 8 | 最大并发请求数，调小可进一步降低被限流风险 |
| `collection.rate_limit_delay` | 0.0 | 请求最小发起间隔（秒）。0=不额外限速，仅受 `max_concurrent` 约束；遇到 429 限流时可调到 0.2~0.5 |
| `cache.enabled` | true | 是否启用本地缓存（关闭则每次重新抓取） |
| `cache.ttl` | 3600 | 收藏数据缓存有效期（秒） |
| `cache.dir` | "" | 缓存目录，留空 = `~/.cache/bangumi-catcher` |
| `analysis.top_n` | 20 | 「最爱排行」展示数量 |

---

## 致谢

数据来源：[Bangumi 番组计划](https://bgm.tv) · 请遵守其 API 使用条款与频率限制。

## License

MIT © Bangumi Catcher Contributors
