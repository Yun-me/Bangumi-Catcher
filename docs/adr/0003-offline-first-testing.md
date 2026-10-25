# 0003. 离线优先的测试策略

- 状态：Accepted
- 日期：2026-10-25
- 决策者：Bangumi Catcher Contributors

## 背景

3.x 的客户端测试通过替换私有属性接入 `httpx.MockTransport`：

```python
await client._client.aclose()
client._client = httpx.AsyncClient(transport=httpx.MockTransport(request))
```

这带来三个问题：

1. 测试依赖 `_client` 私有结构，重构即碎；
2. `httpx` 默认读取环境代理，本机异常的 `NO_PROXY`（例如含 `[::1]`）会让
   `AsyncClient` 在构造时崩溃，出现“只有某台机器失败”的测试；
3. 只有零散 mock，没有统一的失败/延迟/取消/并发模拟，抓取生命周期难以覆盖。

## 决策

1. **传输层注入**：`BangumiClient(config, transport=...)` 接受
   `httpx.AsyncBaseTransport`。注入 transport 时自动 `trust_env=False`，
   测试不再受环境代理影响。
2. **统一 fake API**：`tests/fakes.py` 实现收藏分页与条目详情，支持
   `delay`、`slow_offsets`、`fail_offsets`、`omit_inline_subject`、
   `missing_subjects`，并统计 `peak_in_flight`、`subject_requests`、
   `raw requests`。
3. **全局离线守卫**：`tests/conftest.py` 的 autouse 夹具替换真实
   `HTTPTransport` / `AsyncHTTPTransport` 的处理器，任何漏网的网络调用立即失败；
   需要真实网络的测试显式标记 `@pytest.mark.network`。
4. **环境隔离**：清空 `BANGUMI_*` 与代理变量，把项目/用户配置路径重定向到
   `tmp_path`，测试不读取开发者本机配置。
5. **录制夹具**：`tests/fixtures/bangumi/*.json` 保存真实形态的 slim/full subject
   与收藏页，映射测试直接消费，防止 API 形态变化被忽略。

## 后果

正面：

- 测试确定性高，可在无网络 CI、飞机上、沙箱中运行；
- 并发、取消、失败清理可以被精确模拟；
- 测试不再触碰私有属性，内部重构更安全；
- 捕获了真实的 httpx 环境代理兼容问题，并提供了用户侧开关 `api.trust_env`。

代价：

- fake 需要随 API 字段演进维护；
- 注入 transport 的代码路径与生产默认路径略有差异（例如没有真实 DNS/TLS）；
  因此保留少量手动/标记为 `network` 的冒烟测试。

## 备选方案

1. **VCR 录制回放**（vcrpy / pytest-recording）：能记录真实响应，但增加依赖，
   且对并发/取消/延迟模拟不友好。
2. **只 mock `httpx.get`**：无法测试异步并发与 transport 生命周期。
3. **允许测试联网**：慢、不稳定、可能触发 Bangumi 限流，且无法在受限环境运行。

选择“注入 transport + 统一 fake + 全局守卫”，兼顾真实度、速度与可控性。
