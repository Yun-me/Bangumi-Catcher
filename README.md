<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

<h1 align="center">🔍 Bangumi Catcher</h1>

<p align="center"><strong>Bangumi 动画收藏分析桌面工具 —— 输入用户 ID，一键生成报告</strong></p>

---

## 使用方式

### ⚡ 下载 .exe 直接运行 (推荐)

从 [Releases](https://github.com/your-username/bangumi-catcher/releases) 下载 `BangumiCatcher.exe`，双击运行。

> 无需安装 Python，无需联网配置，一个文件搞定。

### 🐍 从源码运行

```bash
git clone https://github.com/your-username/bangumi-catcher.git
cd bangumi-catcher
pip install -r requirements.txt
python -m bangumi_catcher
```

### 📦 自己打包 .exe

```bash
pip install pyinstaller
python build.py
# 输出: dist/BangumiCatcher.exe
```

---

## 功能

| 功能 | 说明 |
|---|---|
| 🔍 输入 ID 抓取 | 支持 Bangumi 用户名或数字 UID |
| 📊 四维分析 | 年份趋势 / 评分分布 / 收藏类型 / 高分排行 |
| 📈 交互图表 | Plotly 生成的高清 PNG 图表 |
| 📋 数据表格 | 高分排行 + 年度明细 |
| 💾 多格式导出 | CSV / JSON / 静态 HTML 报告 |
| 💾 本地缓存 | 同一用户 1 小时内不重复请求 |

---

## 文件结构

```
bangumi-catcher/
├── bangumi_catcher/
│   ├── gui.py            # Tkinter 桌面 GUI
│   ├── api.py            # httpx 异步 API 客户端
│   ├── models.py         # Pydantic v2 数据模型
│   ├── analyzer.py       # 分析引擎
│   ├── export.py         # CSV / JSON 导出
│   ├── visualizer.py     # Plotly 图表
│   ├── reporter.py       # HTML 报告
│   ├── config.py         # YAML 配置
│   ├── cache.py          # 缓存层
│   ├── exceptions.py     # 异常体系
│   └── templates/        # HTML 模板
├── build.py              # PyInstaller 打包脚本
├── config.yaml           # 默认配置
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## License

MIT © 2025 Bangumi Catcher Contributors
