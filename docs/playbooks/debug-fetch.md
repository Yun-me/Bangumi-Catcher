# 排查抓取 / 分页 / 网络问题

## 先分清是哪一层

| 现象 | 可能层 | 先看 |
|---|---|---|
| 用户不存在 / 收藏未公开 | API 404 → `NotFoundError` | 用户名规范化、隐私设置 |
| 只有第一页 | 分页/合并 | `FakeBangumiAPI(total=...)` 复现 |
| 条目顺序错乱 | `merge_pages` | offset 排序、去重 |
| 完成率全 0 | 模型 `episodes_total` | slim subject 是否只有 `eps` |
| 全站均分为 0 | 映射 | 是否用了扁平 `score` |
| 卡住/关不掉 | 取消 | `run_cancellable`、`QThread` 生命周期 |
| 429 | 限速 | `rate_limit_delay` / `max_concurrent` |
| 代理相关崩溃 | httpx env | `trust_env` / `NO_PROXY` |

## 用 fake 复现（推荐）

写一个临时脚本或测试，不联网：

```python
import asyncio
from bangumi_catcher.api import BangumiClient
from bangumi_catcher.core.config import AppConfig
from tests.fakes import FakeBangumiAPI, page_offsets

api = FakeBangumiAPI(total=10, page_size=2, delay=0.001)
config = AppConfig()
config.cache.enabled = False
config.api.trust_env = False

async def main():
    async with BangumiClient(config, transport=api.transport()) as client:
        collection = await client.fetch_collection("tester")
        print([item.subject_id for item in collection.items])
        print("offsets:", page_offsets(api))
        print("peak concurrency:", api.peak_in_flight)

asyncio.run(main())
```

需要模拟失败/取消：

- `fail_offsets=(1,)`：指定页返回 403，检查其它任务是否被取消、缓存是否为空；
- `slow_offsets=(2, 3)`：挂起指定页，配合 `cancel_check` 测试取消延迟；
- `omit_inline_subject=True`：强制走详情补全；
- `missing_subjects=(2,)`：模拟条目被删除。

## 看日志

```bash
python -m bangumi_catcher.cli -v fetch alice --format json -o out.json
```

关键日志：`用户 X 共 N 条 / M 页`、`并发补全 K 个条目详情`、`使用缓存数据`、
`请求异常 ... (重试 n/3)`、`抓取完成`。

GUI 里打开「工具 → 运行日志」，或设置 `logging.file` 写入文件。

## 检查缓存

```python
from bangumi_catcher.api import Cache
from bangumi_catcher.core.config import AppConfig

config = AppConfig()
with Cache(config.cache.resolved_dir()) as cache:
    print(cache.size)
    print(cache.get_collection("alice", 2))
```

排查时用 `--force-refresh` 或 `cache.enabled: false` 排除缓存因素。
`clear-cache` 只清缓存，不影响收藏与导出文件。

## 网络/代理

- `api.proxy` 显式代理；留空时 `trust_env` 决定是否读取环境变量。
- 某些 `NO_PROXY` 值（含 `[::1]`）会让 httpx 0.28 初始化失败：设
  `api.trust_env: false` 或修正环境变量。
- 429：降低 `max_concurrent`、提高 `rate_limit_delay`；客户端会尊重
  `Retry-After`。

## 取消与关闭

- 抓取中的取消由 `threading.Event` → monitor 取消 asyncio task 实现；
  若新增阻塞调用，记得在循环里调用 `check_cancelled` / `client.check_cancelled()`。
- 新增后台线程必须交给 `TaskRunner`，并在窗口关闭时等待 `finished`。
- 禁止在 worker 里直接操作 QWidget（会崩）。

## 定位后

1. 把复现固化成测试：单元（算法）或集成（fake transport）。
2. 如果是 API 形态变化，更新 `tests/fixtures/bangumi/` 与 `docs/data-model.md`。
3. 更新 `CHANGELOG.md`，注明影响范围与规避方式。
