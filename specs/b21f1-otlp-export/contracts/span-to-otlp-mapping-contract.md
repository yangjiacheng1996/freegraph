# Contract: `Span` → OTLP 映射

**Feature**: B21F1 · **Date**: 2026-11-24 · **Spec**: [../spec.md](../spec.md)

> 本契约锁定 **11 字段 → OTel SDK 数据对象 → OTLP 请求** 的逐字段规则、身份哈希、
> 时间 / 属性 / status / kind / Resource / Scope，以及「不自研编码」的边界。

---

## 1. 输入 / 输出

| 项 | 类型 | 说明 |
|---|---|---|
| 输入 | `freegraph.contracts.trace.Span` | 11 字段；只读 |
| 中间 | `opentelemetry.sdk.trace.ReadableSpan` | 官方 SDK 数据对象 |
| wire | `opentelemetry.proto.collector.trace.v1.trace_service_pb2.ExportTraceServiceRequest` | 官方 `encode_spans` 生成 |
| 输出 | gRPC `TraceServiceStub.Export` / 用户 `SpanExporter.export` | 官方 stubs / 用户 exporter 接口 |

---

## 2. 字段映射表（11/11）

| # | `Span` 字段 | OTel 对应物 | 规则 | 非法 / 缺失 |
|---|---|---|---|---|
| 1 | `id` | `SpanContext.span_id`（8 字节） | `sha256(b"freegraph:span:" + id)[:8]` → `int.from_bytes(..., "big")` | 空 ⇒ 跳过 span + 诊断 |
| 2 | `name` | `ReadableSpan.name` | 逐字 | 空串仍导出（不伪造） |
| 3 | `attributes` | `ReadableSpan.attributes` | 逐键直映射 + 值归一 + 派生 `gen_ai.conversation.id` | 非 `str` 键 ⇒ 跳过该键 + 诊断 |
| 4 | `parent` | `SpanContext`（parent） | 对 `parent` 用同一 `span` 哈希；`None` / 空 ⇒ 无 parent | 无效父 ⇒ 根 span，不抛 |
| 5 | `start_time` | `ReadableSpan.start_time`（int ns） | `parse_iso_ns` | 非法 ⇒ 跳过 span + 诊断 |
| 6 | `end_time` | `ReadableSpan.end_time`（int ns） | `parse_iso_ns`；`None` ⇒ 不导出 | 非法 ⇒ 跳过 span + 诊断 |
| 7 | `context` | **不导出**（v1） | — | — |
| 8 | `thread_id` | `gen_ai.conversation.id`（派生） | 非 `None` 且属性中不存在时写入 | 非 `str` ⇒ 不派生 + 诊断 |
| 9 | `run_id` | `SpanContext.trace_id`（16 字节） | `sha256(b"freegraph:run:" + run_id)[:16]` → `int.from_bytes(..., "big")` | 空 ⇒ 跳过 span + 诊断 |
| 10 | `node` | **不新增属性** | 节点 span 的 `name` 即节点名；子 span 经 parent 链回溯 | — |
| 11 | `checkpoint_id` | **不导出**（v1） | — | — |

---

## 3. 身份哈希

| 输出 | 规则 | 不变量 |
|---|---|---|
| `trace_id` | `sha256(b"freegraph:run:" + run_id.encode("utf-8")).digest()[:16]` | 同 `run_id` ⇒ 同 `trace_id`；不同 `run_id` ⇒ 不同 |
| `span_id` | `sha256(b"freegraph:span:" + id.encode("utf-8")).digest()[:8]` | 同 `id` ⇒ 同 `span_id`；跨进程稳定 |
| `parent_span_id` | 对 `parent` 用同一 `span` 规则 | `None` / 空 ⇒ 无 parent |
| `trace_flags` | `TraceFlags(TraceFlags.SAMPLED)` | 采样标志置位 |
| `is_remote` | `False` | 本地产生 |

**OTel 构造**：

```python
context = SpanContext(
    trace_id=int.from_bytes(trace_bytes, "big"),
    span_id=int.from_bytes(span_bytes, "big"),
    is_remote=False,
    trace_flags=TraceFlags(TraceFlags.SAMPLED),
)
```

**碰撞**：SHA-256 截断的碰撞概率可忽略；v1 **不做**碰撞检测 / 重映射。若将来需要
更严格唯一性，走新 feature（不得改本契约的确定性）。

---

## 4. 时间

| 项 | 规则 |
|---|---|
| 解析 | `freegraph.observability._time.parse_iso_ns`（同层复用；9 位 UTC 纳秒） |
| `start_time` | 必须可解析；否则跳过 span + 诊断 |
| `end_time` | `None` ⇒ 不导出；可解析 ⇒ 使用 |
| `end < start` | 钳到 `start` + `WARNING`（保留 span） |
| 精度 | **纳秒**；MUST NOT 截断到微秒 |
| 时区 | B18F1 产出 `+00:00`；按 UTC |

**OTel 字段**：`ReadableSpan.start_time` / `end_time`（int ns）；OTLP 编码为
`start_time_unix_nano` / `end_time_unix_nano`。

---

## 5. 属性

### 5.1 键面

- **只来自** `Span.attributes` 的逐键直映射。
- **唯一派生键**：`gen_ai.conversation.id`（来自 `thread_id`）。
- **MUST NOT** 出现 `freegraph.*` 私有前缀。
- **MUST NOT** 解析 `context` / `TraceRecord` / 存储行格式。
- 非 `str` 键 ⇒ 跳过该键 + `WARNING`；不影响其它属性 / span 导出。

### 5.2 值归一

| 输入 | 输出 |
|---|---|
| `str` / `bool` / `int` / `float` / `bytes` | 原样 |
| 同质标量序列（`list` / `tuple`，元素类型一致且为上述标量） | 原样序列 |
| `None` | `"null"`（JSON 字符串） |
| `dict` / 混合序列 / 自定义对象 | `json.dumps(value, ensure_ascii=False, sort_keys=True)`；失败 ⇒ `str(value)` |

- `json` 失败 / 循环引用 ⇒ `str(value)`，**MUST NOT** 抛到运行路径。
- 非 ASCII / 换行 / 控制字符原样保留；不截断。

### 5.3 `thread_id` 派生

| 条件 | 行为 |
|---|---|
| `thread_id is None` | 不写 `gen_ai.conversation.id` |
| `thread_id` 是 `str` 且 `Span.attributes` 无该键 | 写 `gen_ai.conversation.id = thread_id` |
| `Span.attributes` 已有该键 | **保留原值**，不覆盖 |
| `thread_id` 非 `str` | 不派生 + `WARNING` |

### 5.4 不导出的字段

| 字段 | 原因 |
|---|---|
| `context` | 本地补充上下文；不属于 OTLP 标准语义；未来需单独登记 |
| `checkpoint_id` | B14F1 D-06 仅 MAY 复用；v1 不导出 |
| `node` | 节点 span 的 `name` 已表达；子 span 经 parent 回溯 |
| `TraceRecord` | 不是 `Span`；MUST NOT 生成独立 OTLP span |

---

## 6. 传输与「不自研编码」边界

### 6.1 端点模式

```python
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import TraceServiceStub

request = encode_spans([readable])                 # 官方编码器
channel = grpc.insecure_channel(endpoint) if insecure else grpc.secure_channel(
    endpoint, grpc.ssl_channel_credentials()
)
try:
    TraceServiceStub(channel).Export(request, metadata=headers, timeout=timeout)
finally:
    channel.close()
```

| 项 | 规则 |
|---|---|
| 编码 | **必须**用官方 `encode_spans`；MUST NOT 手写 protobuf / wire format |
| stubs | **必须**用官方 `TraceServiceStub`；MUST NOT 手写 gRPC payload |
| 门面 | **MUST NOT** 用 `OTLPSpanExporter`（读 env + 内部重试） |
| 重试 | `stub.Export` 只调用一次；失败即诊断 |
| channel | 每次导出短生命周期；`finally` 关闭；不缓存 |
| TLS | `insecure=False` ⇒ `secure_channel` + `ssl_channel_credentials()`；`True` ⇒ `insecure_channel` |
| headers | `tuple(headers.items())`；不读 env |
| timeout | 默认 `10.0` 秒；不读 env |

### 6.2 导出器模式

```python
result = exporter.export([readable])
```

| 返回值 | 处理 |
|---|---|
| `SpanExportResult.SUCCESS` / `None` | 成功 |
| `SpanExportResult.FAILURE` | 失败（合成 `RuntimeError`） |
| 其它 | 忽略（按成功处理） |
| 抛 `Exception` | 隔离并诊断 |
| 抛 `BaseException` | 传播 |

---

## 7. Status / SpanKind / Resource / Scope

| 输出 | 规则 |
|---|---|
| `status` | `error.type` 存在 ⇒ `Status(StatusCode.ERROR, str(error.type))`；否则 `Status(StatusCode.UNSET)` |
| `kind` | `gen_ai.operation.name` ∈ {`chat`, `execute_tool`} ⇒ `SpanKind.CLIENT`；否则 `SpanKind.INTERNAL` |
| `resource` | `Resource({"service.name": "freegraph"})`（**直接构造**，不用 `Resource.create`） |
| `instrumentation_scope` | `InstrumentationScope("freegraph", freegraph.__version__)` |
| `events` / `links` | 空序列 |
| `schema_url` | 空 |

> **Resource 纪律**：`Resource.create()` 会读 `OTEL_RESOURCE_ATTRIBUTES` /
> `OTEL_SERVICE_NAME`（`sdk/resources/__init__.py:199,333,350`）⇒ **MUST NOT** 使用。
> v1 固定 `service.name="freegraph"`；不提供 `resource_attributes` 参数。

---

## 8. 可测试不变量

1. 同一 `Span` ⇒ 同一 `trace_id` / `span_id`（确定性）。
2. 同一 `run_id` 的节点 / 模型 / 工具 span 共享 `trace_id`；不同 `run_id` 不共享。
3. `Span.attributes` 的键集合 ⊆ OTLP 属性键集合；额外仅 `gen_ai.conversation.id`。
4. OTLP 属性中 `freegraph.*` 出现次数 **== 0**。
5. 时间纳秒误差 **== 0**；`end_time is None` ⇒ 不导出。
6. `error.type` ⇒ status `ERROR`（message == 字符串化值）；否则 `UNSET`。
7. `gen_ai.operation.name` ∈ {`chat`, `execute_tool`} ⇒ `CLIENT`；否则 `INTERNAL`。
8. `Resource` 的 `service.name == "freegraph"`。
9. 源码 / AST 中无手写 protobuf encoder / OTLP wire format。
10. `TraceRecord` 生成的 OTLP span 数 **== 0**。

---

## 9. 测试矩阵

| # | 用例 | 断言 |
|---|---|---|
| M-01 | 节点 span | name / ids / times / INTERNAL / 空属性 |
| M-02 | 模型 span（`gen_ai.operation.name=chat`） | CLIENT；属性逐键 |
| M-03 | 工具 span（`gen_ai.operation.name=execute_tool`） | CLIENT；属性逐键 |
| M-04 | 失败 span（`error.type`） | status ERROR；message 正确 |
| M-05 | `thread_id` 非空 | 派生 `gen_ai.conversation.id` |
| M-06 | `thread_id` 已有同名属性 | 保留原值，不覆盖 |
| M-07 | `context` / `checkpoint_id` / `node` | 不导出 |
| M-08 | 同 run 多 span | 同 `trace_id`；不同 run 不同 |
| M-09 | 空 id / run_id / 坏时间 | 跳过 + 诊断 |
| M-10 | 嵌套 dict / list / None 属性 | JSON 字符串 / `"null"`；不抛 |
| M-11 | 纳秒时间 | `start_time` / `end_time` 精确 |
| M-12 | `end < start` | 钳到 start + WARNING |
| M-13 | Resource / Scope | `service.name=freegraph`；scope name/version 正确 |
| M-14 | 无自研编码 | AST / 静态扫描无 protobuf encoder / wire format |
