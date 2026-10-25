# 配置

## 优先级

从低到高：

```text
内置默认
< 项目 config.yaml（当前目录，其次仓库根目录，其次打包内置）
< 用户偏好（平台配置目录）
< 程序化覆盖（load_config(overrides=...)）
< BANGUMI_* 环境变量
```

显式 `--config PATH` 或 `BANGUMI_CONFIG=PATH` **替代**项目搜索（只读该文件），
环境变量仍然最后覆盖。路径不存在会直接报错。

## 文件位置

| 用途 | 位置 |
|---|---|
| 项目示例 | `<repo>/config.yaml`（从仓库运行时的默认项目配置） |
| 打包内置 | PyInstaller 包内的 `config.yaml`（仅作项目默认，可被用户偏好覆盖） |
| 用户偏好（GUI 保存） | Windows `%APPDATA%/bangumi-catcher/config.yaml`；macOS `~/Library/Application Support/bangumi-catcher/config.yaml`；Linux `${XDG_CONFIG_HOME:-~/.config}/bangumi-catcher/config.yaml` |
| 缓存 | 默认 `~/.cache/bangumi-catcher`，可用 `cache.dir` 覆盖 |

配置文件必须是 YAML 对象；`null` 表示使用默认值。未知键会被 Pydantic 忽略
（便于向后兼容），但拼错键不会报错，建议用 `cli config` 检查最终结果。

## 字段

### `api`

| 字段 | 默认 | 说明 |
|---|---|---|
| `base_url` | `https://api.bgm.tv` | 末尾斜杠会自动去掉 |
| `user_agent` | 项目 UA | 建议保留项目标识 |
| `timeout` | `30` | 单请求超时（秒） |
| `max_retries` | `3` | 网络/5xx/429 最大尝试次数 |
| `retry_delay` | `1.0` | 退避基数（秒），第 n 次等待 `n * retry_delay` |
| `proxy` | `null` | HTTP(S) 代理；留空走环境/直连 |
| `trust_env` | `true` | 是否读取 `HTTP(S)_PROXY` / `NO_PROXY`。遇到异常的 `NO_PROXY` 可设为 `false` |

### `collection`

| 字段 | 默认 | 说明 |
|---|---|---|
| `subject_type` | `2` | 1=书籍 2=动画 3=音乐 4=游戏 6=三次元 |
| `limit` | `50` | 每页条数，代码会 clamp 到 1–50 |
| `max_concurrent` | `8` | 同时抓取的页数/详情数 |
| `rate_limit_delay` | `0.0` | 请求最小间隔；429 时可调到 0.2–0.5 |

### `cache`

| 字段 | 默认 | 说明 |
|---|---|---|
| `enabled` | `true` | 关闭后每次都重新抓取 |
| `ttl` | `3600` | 收藏缓存秒数；条目详情固定 7 天 |
| `dir` | `""` | 留空用 `~/.cache/bangumi-catcher` |

### `analysis`

| 字段 | 默认 | 说明 |
|---|---|---|
| `year_start` | `2000` | 年度统计起始年（含） |
| `year_end` | 当前年 | 年度统计结束年（含） |
| `top_n` | `20` | 高分排行与热门标签数量 |

### `export`

| 字段 | 默认 | 说明 |
|---|---|---|
| `output_dir` | `output` | CLI 未指定 `-o` 时的目录 |
| `csv_encoding` | `utf-8-sig` | 带 BOM，Excel 直接打开不乱码 |
| `json_indent` | `2` | JSON 缩进 |

### `ui`

| 字段 | 默认 | 说明 |
|---|---|---|
| `theme` | `system` | `system` / `light` / `dark` |
| `recent_users` | `[]` | 首次运行的最近用户（之后由 QSettings 维护） |
| `max_recent_users` | `8` | 历史用户上限 |

### `logging`

| 字段 | 默认 | 说明 |
|---|---|---|
| `level` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `file` | `""` | 追加写入的日志文件；留空只输出到 stderr |

## 环境变量

规则：`BANGUMI_` 前缀，层级用双下划线，键名小写。

```bash
export BANGUMI_API__TIMEOUT=60
export BANGUMI_API__TRUST_ENV=false
export BANGUMI_COLLECTION__MAX_CONCURRENT=4
export BANGUMI_COLLECTION__RATE_LIMIT_DELAY=0.3
export BANGUMI_ANALYSIS__TOP_N=30
export BANGUMI_LOGGING__LEVEL=DEBUG
```

值会转换为 bool / int / float / `null` / 字符串。`BANGUMI_CONFIG` 是保留变量，
用于指定配置文件，不作为配置键。

## 示例

```yaml
api:
  proxy: "http://127.0.0.1:7890"
  trust_env: true
collection:
  max_concurrent: 4
  rate_limit_delay: 0.3
analysis:
  year_start: 2010
logging:
  level: DEBUG
```

## 检查最终配置

```bash
python -m bangumi_catcher.cli config          # YAML
python -m bangumi_catcher.cli config --json   # JSON
```

有校验问题时命令返回非零并把问题写到 stderr（`api.base_url` 非 HTTP、
`collection.limit` 越界、年份倒置等）。

## GUI 设置

「工具 → 设置…」修改的字段会写入**用户偏好**文件，不会覆盖仓库/安装目录里的
`config.yaml`。保存后会立即重新分析当前收藏；日志设置会即时重建日志 handler。
窗口几何、主题、最近用户仍保存在 Qt 的 `QSettings` 中。
