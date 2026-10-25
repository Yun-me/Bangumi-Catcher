# 测试

## 原则

1. **默认离线**：任何测试都不得访问真实网络。`tests/conftest.py` 的
   `block_real_http` 会把 `httpx` 的真实 transport 替换成抛错的实现。
2. **确定性**：不依赖当前年份以外的系统状态；时间用固定值或动态取当前年。
3. **快**：单元测试毫秒级；UI/图表测试几秒。CI 全量应在数分钟内完成。
4. **行为而非实现**：断言公开行为与数据口径，避免绑定私有细节。
5. **失败可读**：断言信息说明“期望的语义”，例如完成率为什么是 100%。

## 命令

```bash
python scripts/dev.py test                 # 全部
python scripts/dev.py test -- tests/unit   # 只跑单元
python scripts/dev.py test -- -k "chart and not slow"
python scripts/dev.py cov                  # 覆盖率
```

## 分层

```text
tests/
  conftest.py                 全局隔离、离线守卫、qapp、sample_collection
  factories.py                模型工厂（make_subject/make_item/make_collection）
  fakes.py                    FakeBangumiAPI（async transport）
  helpers.py                  run_python（子进程导入）、read_fixture
  fixtures/bangumi/*.json     录制的 API 响应
  unit/core/                  模型、分析、配置、查询
  unit/api/                   分页、映射、缓存/限速
  unit/charts/                注册表与 PNG
  unit/reporting/             CSV/JSON/HTML/原子写
  integration/                客户端生命周期、fetch/export/library/CLI/取消
  ui/                         模型契约、TaskRunner、窗口流程
  architecture/               分层与 import 方向
  test_docs.py                文档链接与存在性
  test_packaging.py           pyproject/入口点/包数据
```

## 全局夹具

`tests/conftest.py` 的 autouse 夹具负责：

- 清除 `HTTP(S)_PROXY`、`ALL_PROXY`、`NO_PROXY`（大小写两种）与所有 `BANGUMI_*`；
- 把项目/用户配置路径重定向到 `tmp_path`，避免读到开发者本机配置；
- 拦截真实 HTTP transport；
- 提供 `sample_collection`（5 条覆盖看过/想看/在看/未评分）与 session 级 `qapp`。

需要网络的测试：

```python
@pytest.mark.network
def test_real_api(): ...
```

默认 CI 不运行 `-m network`。

## 造数据

优先用工厂，不要复制大段字典：

```python
from tests.factories import make_collection, make_item

items = [make_item(1, 2, 8, year=2020), make_item(2, 1, 0, year=2021)]
collection = make_collection(items)
```

API 响应放 `tests/fixtures/bangumi/`，用 `read_fixture()` 读取；新增抓取字段时
同时补 fixture 和映射测试。

## 网络替身

`FakeBangumiAPI` 实现 `/v0/users/{user}/collections` 与 `/v0/subjects/{id}`，
支持：

```python
api = FakeBangumiAPI(
    total=100,
    delay=0.001,                 # 模拟网络延迟
    fail_offsets=(1,),           # 指定 offset 返回 403
    slow_offsets=(2, 3, 4),      # 指定 offset 长时间挂起（测取消）
    omit_inline_subject=True,    # 强制走详情补全
    missing_subjects=(2,),       # 详情 404
)
client = BangumiClient(config, transport=api.transport())
```

它可以统计 `requests`、`subject_requests`、`peak_in_flight`，用于断言并发上限与
取消清理。

## 写集成测试

```python
def test_fetch(tmp_path):
    api = FakeBangumiAPI(total=5)
    config = AppConfig()
    config.cache.dir = str(tmp_path / "cache")
    config.api.trust_env = False
    collection = asyncio.run(fetch_user_collection(
        config, "tester", client_factory=lambda cfg: BangumiClient(cfg, transport=api.transport()),
    ))
    assert [item.subject_id for item in collection.items] == [1, 2, 3, 4, 5]
```

## 写 UI 测试

- 使用 `tests/ui/conftest.py` 的 `window` 夹具（自动设置主题、隔离 `QSettings`、
  关闭时等待任务结束）。
- 用 `wait_until(lambda: ...)` 驱动事件循环，**不要** `time.sleep`。
- 断言用户可见状态（按钮可用性、页面切换、表格行数、状态栏文本），不要直接改
  私有字段来“制造”状态。
- 后台任务通过 `TaskRunner` 的 signal 完成；测试中可调用 `window.task.start(...)`
  并等待 `not window.task.busy`。
- 图表测试 monkeypatch `bangumi_catcher.charts.render.render_chart` 返回固定 PNG，
  避免真实渲染；真实渲染只保留一个 `@pytest.mark.slow` 测试。

## 架构与文档测试

- 新增模块时，`tests/architecture/test_layers.py` 会自动把它纳入分层检查。
- 如果确实需要打破依赖方向，先写 ADR 并更新该测试，不要静默放宽。
- `tests/test_docs.py` 会检查 README/AGENTS/docs 中的相对链接；移动文件后记得
  更新链接，否则 CI 失败。
- `tests/test_packaging.py` 校验版本、入口点、`package-data`、src 布局。

## 覆盖率

`python scripts/dev.py cov` 生成终端摘要与 `coverage.xml`。不要为覆盖率数字写
无意义断言；优先覆盖边界条件：空集合、未知类型、脏数据、取消、失败回滚。

## 稳定性和超时

- 不写依赖执行顺序的测试；每个测试自己构造状态。
- 异步代码用 `asyncio.run(...)` 包装，避免引入 `pytest-asyncio`。
- 涉及线程的测试用 `threading.Event` 同步，最长等待 5–8 秒；超时应给出明确
  断言信息。
- 如果测试偶发失败，先找竞态（通常是 Qt 事件未处理或线程未 join），不要用更长
  的 sleep 掩盖。
