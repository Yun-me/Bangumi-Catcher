<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PySide6-41CD52" alt="PySide6">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

<h1 align="center">🔍 Bangumi Catcher</h1>

<p align="center"><strong>Bangumi 用户收藏抓取与可视化分析桌面工具 —— 输入用户 ID，一键生成分析报告</strong></p>

---

## ✨ 特性

| 功能 | 说明 |
|---|---|
| 🖥 现代界面 | 基于 **PySide6 (Qt)**，响应式布局，窗口缩放/全屏自动重排，亮/暗双主题 |
| 📈 实时图表 | matplotlib 画布随窗口实时重绘；8 张图表（评分分布、状态分布、年度趋势、年度均分、状态构成、季度分布、评分对比、最爱排行） |
| 📚 收藏总表 | 全部收藏的可搜索、可排序数据表；双击跳转 Bangumi 条目页 |
| ⚡ 不卡死 | 抓取/分析在后台线程执行，进度条实时反馈，可随时取消 |
| 🚀 高速抓取 | httpx 异步并发拉取条目详情 + 自动重试 + 速率限制 |
| 💾 本地缓存 | diskcache 持久化，同一用户默认 1 小时内不重复请求；支持「强制刷新」 |
| 📤 多格式导出 | CSV / JSON / 自包含 HTML 报告（可一键在浏览器打开） |
| 🧠 状态记忆 | 自动记住上次用户名、窗口大小与主题偏好 |

---

## 🚀 使用方式

### ⚡ 下载可执行文件（推荐）

从 [Releases](https://github.com/your-username/bangumi-catcher/releases) 下载并双击运行，无需安装 Python。

### 🐍 从源码运行

```bash
git clone https://github.com/your-username/bangumi-catcher.git
cd bangumi-catcher
pip install -r requirements.txt
python -m bangumi_catcher        # 或 python run.py
```

### 📦 自行打包

```bash
pip install pyinstaller
python build.py                  # 输出 dist/BangumiCatcher
```

---

## 🧑‍💻 开发

```bash
pip install -e ".[dev]"
pytest -q                        # 运行测试（Qt 用 offscreen，无需显示器）
ruff check bangumi_catcher       # 代码检查
```

---

## 📂 项目结构

```
bangumi-catcher/
├── bangumi_catcher/
│   ├── gui.py            # PySide6 主窗口（响应式布局 + 后台线程）
│   ├── theme.py          # Qt QSS 主题（亮/暗）
│   ├── flowlayout.py     # 自动换行布局（响应式核心）
│   ├── visualizer.py     # matplotlib 图表（GUI 实时 + HTML 导出共用）
│   ├── api.py            # httpx 异步 API 客户端（并发 + 重试 + 缓存）
│   ├── models.py         # Pydantic v2 数据模型
│   ├── analyzer.py       # 多维统计分析引擎
│   ├── export.py         # CSV / JSON 导出
│   ├── config.py         # YAML 配置（内嵌默认 + 环境变量覆盖）
│   ├── cache.py          # diskcache 缓存层
│   ├── exceptions.py     # 异常体系
│   └── templates/        # HTML 报告模板
├── tests/                # pytest 测试套件
├── .github/workflows/    # CI
├── run.py                # 打包入口
├── build.py              # PyInstaller 脚本
├── config.yaml           # 可选外部配置
├── pyproject.toml
└── requirements.txt
```

---

## ⚙️ 配置

默认配置已内嵌，开箱即用。如需自定义，在工作目录放置 `config.yaml`，或用环境变量覆盖（嵌套用 `__`）：

```bash
export BANGUMI_API__TIMEOUT=60
export BANGUMI_ANALYSIS__TOP_N=30
```

---

## 🙏 致谢

数据来源：[Bangumi 番组计划](https://bgm.tv) · 请遵守其 API 使用条款与频率限制。

## License

MIT © Bangumi Catcher Contributors
