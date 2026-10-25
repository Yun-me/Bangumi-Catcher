# Bangumi Catcher

**本地优先的 Bangumi 收藏工作台。同步、整理、回顾，让收藏不止于列表。**

PySide6 桌面界面 + 可脚本化 CLI，兼容 Python 3.9+。无需账号密码，不修改远程收藏。

## 3.0 带来了什么

- **重新设计的桌面**：固定侧栏、森绿浅色 / 夜间主题、跟随系统外观，以及真正可用的空状态。
- **收藏概览**：收藏与评分指标、状态分布、高分作品、最近更新和兴趣标签；点击状态或标签即可继续筛选。
- **高效收藏库**：虚拟表格不再逐格创建 Qt 对象，批量排序行索引而非逐次跨 Qt 比较；搜索带 160 ms 防抖，支持原名、中文名、ID、标签、短评及多个关键词的交集。
- **组合筛选与详情**：状态、发行年份、已评分 / 未评分、最低分组合过滤；数值排序、作品详情、进度、标签和短评；可单独导出筛选结果。
- **离线快照**：导入旧版 / 新版收藏 JSON，不联网即可查看和重新分析。报告 JSON 不作为收藏快照导入。
- **按需分析**：9 个图表维度只在查看时后台生成，同一数据与主题内缓存复用；支持 PNG 保存。启动和浏览收藏不加载 Matplotlib。
- **可靠后台任务**：抓取、分析、导入、导出均放到工作线程；取消可中断正在等待的 HTTP / 重试；退出等待任务安全结束，不强杀线程。
- **统一导出**：CSV、收藏 JSON、报告 JSON、自包含 HTML；GUI / CLI 共用实现。临时文件成功生成后才替换目标，失败不覆盖旧文件。
- **便捷入口**：主页链接识别、最近用户、自动补全、常用快捷键、实时日志、可写用户目录中的偏好设置。

原来的分页并发、持久缓存、代理、年度统计、高分排行和命令行功能仍然保留，没有引入浏览器壳或新的运行时依赖。

## 安装与运行

在项目目录执行：

```bash
pip install -e ".[dev]"
python -m bangumi_catcher
# 也可以使用 python run.py
```

Windows 上如果 `python` 不在 PATH，可以使用已安装的 Python 完整路径，或可用的 `py -3` 启动器。

### 第一次使用

1. 输入 **用户名 / 数字 UID / 用户主页链接**，例如 `https://bgm.tv/user/yourname`。显示昵称不是用户名。
2. 选择动画、书籍、音乐、游戏或三次元，然后点击「同步收藏」。
3. 从侧栏进入收藏、洞察、排行或年度；使用「作品详情」展开详情面板。
4. 「导出报告」导出完整数据；收藏页的「导出筛选结果」只导出当前匹配的行，保持当前排序。
5. 以后使用「导入」打开收藏 JSON，即可离线回顾。旧快照未包含分类时显示“未标注分类”，不会猜测分类。

### 快捷键

| 按键 | 操作 |
|---|---|
| `F5` / 用户输入框中的 `Enter` | 同步收藏 |
| `Ctrl+F` | 进入收藏并聚焦搜索 |
| `Ctrl+O` | 导入收藏 JSON |
| `Ctrl+S` | 导出完整收藏 CSV |
| `Ctrl+D` | 切换亮 / 暗主题 |
| `Ctrl+,` | 偏好设置 |
| `Ctrl+Q` | 安全退出 |

## 命令行

```bash
python -m bangumi_catcher.cli --help
python -m bangumi_catcher.cli version

# 在线同步；用户名也可以替换为用户主页 URL
python -m bangumi_catcher.cli fetch yourname --subject-type 2
python -m bangumi_catcher.cli fetch yourname --force-refresh
python -m bangumi_catcher.cli fetch yourname --format json -o collection.json
python -m bangumi_catcher.cli fetch yourname --format html -o reports/bangumi.html

# 完全离线：读取快照并重新分析 / 转换格式
python -m bangumi_catcher.cli analyze collection.json
python -m bangumi_catcher.cli analyze collection.json --format csv -o collection.csv
python -m bangumi_catcher.cli analyze collection.json --format html -o report.html

python -m bangumi_catcher.cli clear-cache
```

`fetch` / `analyze` 都支持 `--format none|csv|json|report-json|html`、`--output`、`--config`、`--quiet`。
未指定输出路径时保存到配置的 `export.output_dir`，例如 `output/yourname_collection.json`。
出错返回非零退出码并打印错误说明；不会把已有文件覆盖成半份报告。

## 设置与网络

偏好设置分为外观、网络、数据与分析三个页面。网络不可达时可配置 HTTP 代理：

```yaml
api:
  proxy: "http://127.0.0.1:7890"
collection:
  max_concurrent: 8
  rate_limit_delay: 0.2
```

代理留空时由 HTTPX 使用环境代理设置。遇到限流时可降低并发、增加最小请求间隔。

配置合并顺序：内置默认 → 项目 `config.yaml` → 用户偏好 → 程序化覆盖 → 环境变量。
显式提供 `--config` 时仅加载该文件与内置默认，再应用环境变量；路径不存在会报错。

GUI 保存设置不再覆写源码 / 安装目录下的配置，而是写入：

- Windows：`%APPDATA%/bangumi-catcher/config.yaml`
- macOS：`~/Library/Application Support/bangumi-catcher/config.yaml`
- Linux：`${XDG_CONFIG_HOME:-~/.config}/bangumi-catcher/config.yaml`

示例环境变量：

```bash
export BANGUMI_API__TIMEOUT=60
export BANGUMI_COLLECTION__MAX_CONCURRENT=4
export BANGUMI_ANALYSIS__TOP_N=30
```

窗口大小、最近用户、最后分类和手动主题选择仍使用 Qt 的本地应用设置。设置里的主题选择会同步更新手动选择；环境变量配置在下次启动时重新读取。
缓存目录保持兼容：默认 `~/.cache/bangumi-catcher`，可在设置中修改。清缓存不会删除当前收藏、快照或导出文件。

## 数据口径与边界

- 总均分 / 年度均分只统计“看过”且评分大于 0 的作品，未评分不视为 0 分。
- 平均完成率统计“看过”和“在看”；看过为 100%，在看按已记录集数计算。
- 年度统计按作品发行年份，不是用户收藏日期。统计范围在设置中调整，保存后后台重新分析。
- 图表展示完整载入数据；收藏页的筛选不会偷偷改变完整报告的统计口径。
- 收藏 JSON 支持最大 64 MB，保留作品、评分、标签、短评、进度和时间；CSV 额外保留标签、卷数，并将疑似公式文本转为普通文本。
- 本应用是只读工具；不会修改远程收藏，也不会绕过未授权的私有收藏访问限制。网络失败 / 导入失败 / 取消任务会保留上一份已载入数据。
- HTML 报告内嵌全部图表，没有外部脚本或字体依赖，可离线浏览与打印。

## 项目结构

```text
bangumi_catcher/
  core/                  数据模型、配置、缓存、API、分析与序列化
  services/
    fetch_service.py     在线同步与分析编排
    library_service.py   用户输入规范化、离线快照读取
    export_service.py    GUI / CLI 共用的原子导出
    task_service.py      异步任务取消
  ui/
    main_window.py       工作台外壳、导航与数据生命周期
    overview_page.py     轻量原生概览
    library_page.py      收藏浏览与详情
    collection_model.py 虚拟表格与组合筛选
    chart_page.py        按需图表调度与缓存
    report_page.py       排行与年度表格
    workers.py           统一后台任务及线程生命周期
    dialogs.py           偏好设置和实时日志
    theme.py / icons.py  样式令牌与矢量图标
    visualizer.py        线程串行化的 Agg 绘图入口
  templates/             自包含 HTML 报告
  cli.py                 在线 / 离线命令行
tests/                   领域、网络生命周期、导出和无显示器 GUI 回归
```

## 测试与打包

```bash
pytest -q
ruff check bangumi_catcher tests
python build.py
```

测试默认使用 Qt `offscreen`，不要求显示器，也不依赖 `pytest-qt`。网络测试使用 HTTPX 模拟传输，不调用真实 Bangumi。
CI 覆盖 Windows / Linux、Python 3.9 / 3.12。

默认目录打包，避免单文件版本每次启动解压 Qt 与绘图库：

```text
dist/BangumiCatcher/BangumiCatcher.exe   # Windows
dist/BangumiCatcher/BangumiCatcher       # Linux / macOS
```

需要单文件分发时使用 `python build.py --onefile`，输出到 `dist/`；目录版分发时请保留整个文件夹。

## 致谢与许可

数据来源于 [Bangumi 番组计划](https://bgm.tv)。请合理设置请求频率，遵守其 API 使用约定。

MIT，详见 [LICENSE](LICENSE)。
