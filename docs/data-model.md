# 数据模型与统计口径

## Bangumi API

本项目只使用 v0 的两个只读端点：

| 端点 | 用途 |
|---|---|
| `GET /v0/users/{username}/collections` | 用户收藏分页，参数 `subject_type`、`type`、`limit`（≤50）、`offset` |
| `GET /v0/subjects/{id}` | 单条目详情（补全缺失的内联条目） |

响应中的 `total` 是收藏总数，`data` 是当前页条目。代码按 `total` 计算所有
offset（见 `api/pagination.py`），不依赖“下一页是否存在”。

## 两种 subject 形态

| 字段 | slim（收藏列表内联） | full（`/v0/subjects/{id}`） |
|---|---|---|
| 评分 | 扁平 `score` | 嵌套 `rating.score` |
| 排名 | 扁平 `rank` | `rating.rank`（也有顶层 `rank`） |
| 集数 | `eps` | `eps` + `total_episodes` |
| 简介 | `short_summary` | `summary` |
| 封面 | `images.*` | `images.*` |

`api/mapping.build_subject` 同时兼容两者；`Subject.episodes_total` 优先
`total_episodes`，回退 `eps`。**删掉这个回退会让所有完成率变成 0。**

## 收藏状态

`CollectionItem.type` 与中文标签（`core/models/collection.py`）：

| id | 含义 |
|---|---|
| 1 | 想看 |
| 2 | 看过 |
| 3 | 在看 |
| 4 | 搁置 |
| 5 | 抛弃 |
| 其他 | `未知(n)` |

`rate` 为 0–10，0 表示未评分。API 返回 `null`/越界/非数字时在模型层收敛，
不会让整次同步失败。

## 完成率

```text
看过(type=2)            -> 1.0
想看(type=1)            -> 0.0
在看/搁置/抛弃           -> min(ep_status / episodes_total, 1.0)
episodes_total 缺失      -> 用 eps 回退；两者皆无 -> 0.0
```

`AnalysisReport.avg_completion` 只统计 `type in (2, 3)`，乘以 100 保留 1 位小数。

## 平均分

- `overall_avg_rating`：只统计 `type == 2` 且 `rate > 0` 的条目。
- `by_year[year].avg_rating`：同一年内 `type == 2` 且 `rate > 0`。
- **未评分不等于 0 分**，不参与分母。这是 3.0 之前的历史 bug，测试已锁定。

## 年度统计

- 按**作品发行年份**（`Subject.date[:4]`），不是用户收藏时间。
- 范围由 `analysis.year_start` / `analysis.year_end` 控制（默认 2000–今年）。
- 无日期的条目不计入年度统计，也不进入 `season_stats`（季度为空时跳过）。

## 榜单

- `top_rated`：`type == 2`、`rate >= 5`、有 subject；按 `(rate, 全站均分)` 取 Top N。
- `rating_compare`：有个人评分与全站均分的前 50 条，用于散点图。
- `top_tags`：按出现次数取 Top N；`tag_counts` 保留全部。
- 以上都使用 `heapq.nlargest`，避免对万级收藏全量排序。

## 收藏快照 JSON

`services.export` 的 `json` 格式与 `UserCollection` 一致（`model_dump(mode="json")`）：

```json
{
  "username": "alice",
  "subject_type": 2,
  "total": 123,
  "fetched_at": "2026-01-01T00:00:00",
  "items": [
    {
      "subject_id": 101,
      "subject": {"id": 101, "name": "...", "name_cn": "...", "date": "2023-09-29", "...": "..."},
      "type": 2,
      "rate": 9,
      "comment": "短评",
      "tags": ["奇幻"],
      "ep_status": 28,
      "vol_status": 0,
      "updated_at": "2024-03-31T12:00:00+08:00",
      "private": false
    }
  ]
}
```

导入规则（`services/library.load_collection`）：

- 最大 64 MB；支持 UTF-8 BOM；
- 必须是含 `username` 与 `items` 列表的对象；
- 报告 JSON（`total_items` 等）会被拒绝；
- 导入后 `total` 重置为实际条目数；
- 旧快照缺少 `subject_type` 时保持 `None`，UI 显示「未标注分类」，不猜测。

## 报告 JSON

`report-json` 是 `AnalysisReport` 的序列化，字段包括 `by_year`、`type_counts`、
`rating_distribution`、`top_rated`、`year_trend`、`type_trend`、`season_stats`、
`rating_compare`、`tag_counts`、`top_tags`、`avg_completion`、
`overall_avg_rating`、`generated_at`。它**不能**作为收藏快照导入。

## HTTP 错误映射

| 情况 | 异常 | UI/CLI 表现 |
|---|---|---|
| 404 | `NotFoundError` | 「用户不存在或收藏未公开」/「条目不存在」 |
| 429 | `RateLimitError`（重试后） | 提示等待 `Retry-After` |
| 其他 4xx | `APIError` | 「请求被拒绝，检查参数/权限」 |
| 5xx | 重试后 `APIError` | 「Bangumi 暂时不可用」 |
| 网络错误 | 重试后 `APIError(status_code=0)` | 「网络请求失败」 |
| 取消 | `OperationCancelled` | 状态栏「任务已取消」，保留旧数据 |

## 分页与去重

- 首页取 `total`，其余 offset 由 `compute_remaining_offsets` 计算。
- 最多 `collection.max_concurrent` 个消费者协程并发抓取。
- `merge_pages` 按 offset 升序合并，并按 `subject_id` 去重（防止 total 抖动导致
  相邻页重叠）；`subject_id` 缺失的条目保留且不参与去重。
- 任一页失败会取消其余同批任务并等待它们结束，不会把半份数据写入缓存。

## 缓存

| 键 | 内容 | TTL |
|---|---|---|
| `collection:{user}:st{subject_type}:{all|ctN}` | 完整收藏快照 | `cache.ttl`（默认 3600s） |
| `subject:{id}` | 条目详情 | 7 天 |

关闭缓存（`cache.enabled: false`）时既不读也不写。`--force-refresh` 跳过收藏缓存
但仍会读取条目详情缓存。
