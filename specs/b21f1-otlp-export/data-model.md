# Data Model: B21F1 · OTLP 导出插件（可选 extra）+ 后端对接文档

**Date**: 2026-11-24 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

> 本文件定义 **导出侧的公开 / 内部数据形态**。`Span` / `TraceSink` / `TraceRecord` /
> `TraceQuery` / `RunConfig` 均为**既有冻结面**，本 feature **不新增 / 不修改**其字段；
> 这里只描述导出器如何读取它们、如何组装官方 OTel 数据对象。

---

## 1. 实体关系

```text
TraceSink (L1, frozen)
   ▲ implements
   │
OtlpExporter (L5, new) ──reads──> Span (L1, frozen, 11 fields)
   │
   ├── endpoint mode ──> _otlp_mapping ──> ReadableSpan ──> encode_spans ──> ExportTraceServiceRequest
   │                                                                             │
   │                                                                        TraceServiceStub.Export
   │                                                                             │
   └── exporter mode ──> ReadableSpan ──> user SpanExporter.export([...])       ▼
                                                                          external OTLP backend
```

| 实体 | 层 | 语义 | 本 feature 的关系 |
|---|---|---|---|
| `Span` | L1 | 11 字段可观测事件 | **只读**；不增删字段 |
| `TraceSink` | L1 | 3 方法接收端协议 | `OtlpExporter` 结构化实现 |
| `OtlpExporter` | L5 | 可选 OTLP 导出器 | **新增公开符号** |
| `ReadableSpan` | OTel SDK | 官方只读 span 数据对象 | 由 `_otlp_mapping` 组装 |
| `SpanContext` | OTel API | trace_id / span_id / flags | 由身份哈希构造 |
| `Resource` | OTel SDK | 服务资源 | 固定 `service.name="freegraph"` |
| `InstrumentationScope` | OTel SDK | 仪表范围 | 固定 `freegraph` + 版本 |
| `ExportTraceServiceRequest` | OTel proto | OTLP wire 请求 | 由官方 `encode_spans` 生成 |
| `TraceRecord` | L5 | 本地补充元数据 | **不导出**（不是 `Span`） |
| `TraceQuery` / stores | L5 | 本地查询 | **不消费** |

---

## 2. `OtlpExporter`（公开符号）

### 2.1 构造参数

| 参数 | 类型 | 默认 | 语义 | 校验 |
|---|---|---|---|---|
| `endpoint` | `str \| None` | `None` | gRPC OTLP 端点，`host:port` | 非空；不含 `://`；端口 1–65535；允许 IPv6 `[::1]:4317` |
| `exporter` | `object \| None` | `None` | 官方 OTel `SpanExporter` 形状 | `callable(getattr(obj, "export", None))` |
| `insecure` | `bool` | `False` | `True` ⇒ 明文 gRPC；`False` ⇒ TLS | 必须是 `bool`；仅 `endpoint=` 模式；与 `exporter=` 同用 ⇒ `ValueError` |
| `headers` | `Mapping[str, str] \| None` | `None` | gRPC metadata（**仅端点模式**） | 键 / 值必须是 `str`；复制为 tuple；不读 env；与 `exporter=` 同用 ⇒ `ValueError` |
| `timeout` | `float \| None` | `None`（内部 `10.0`） | 单次导出的秒数（**仅端点模式**） | 非 `None` 时正数；不读 env；与 `exporter=` 同用 ⇒ `ValueError` |
| `on_error` | `Callable[[BaseException], None] \| None` | `None` | 失败回调 | callable 或 `None`；在锁外调用；仅 `Exception` 触发；`BaseException` 不调用 |

**恰好一个**：`endpoint` 与 `exporter` 必须二选一；都不传 / 都传 ⇒ 构造时 `ValueError`。
**缺 extra**：`endpoint=` 但 OTel 不可导入 ⇒ 构造时 `ImportError`，消息含
`pip install freegraph[otlp]`。

### 2.2 实例状态

| 字段 | 类型 | 初始值 | 说明 |
|---|---|---|---|
| `_endpoint` | `str \| None` | 校验后的值 | 端点模式 |
| `_exporter` | `object \| None` | 用户对象 | 导出器模式 |
| `_insecure` | `bool` | `False` | 仅端点模式 |
| `_headers` | `tuple[tuple[str, str], ...]` | `()` | 复制后的 metadata |
| `_timeout` | `float` | `10.0` | 秒 |
| `_on_error` | `Callable \| None` | `None` | 失败回调 |
| `_lock` | `threading.Lock` | 新锁 | 每实例一把 |
| `_export_errors` | `int` | `0` | 每失败 / 跳过一个完整 span +1 |
| `_last_error` | `BaseException \| None` | `None` | 最近一次失败；成功不清空 |

**公开只读面**：`export_errors` / `last_error` 以 `@property` 暴露；无 setter / reset API。
**不提供**：`close()` / `__enter__` / `__exit__` / 上下文管理器 / 公开 OTel 对象。

### 2.3 方法语义

| 方法 | 行为 |
|---|---|
| `on_span_start(span)` | **no-op**；不导出未完成 span |
| `on_span_end(span)` | `span.end_time is None` ⇒ return；否则在锁内组装 `ReadableSpan` 并导出；失败记诊断，不抛出 `Exception` |
| `current_span()` | 恒返回 `None` |

### 2.4 状态机（单次 `on_span_end`）

```text
[received span]
   │ end_time is None? ──yes──> return (no diagnostic)
   │ no
   ▼
[validate / map]
   │ invalid id / run_id / time / attribute key? ──yes──> record diagnostic (WARNING + export_errors+1 + last_error)
   │ no
   ▼
[export]
   │ endpoint mode: short-lived channel → encode_spans → stub.Export
   │ exporter mode: exporter.export([ReadableSpan])
   │ Exception / FAILURE? ──yes──> record diagnostic
   │ no
   ▼
[done]
```

**注意**：`on_error` / `logging.WARNING` 在锁外调用；`BaseException` 不被捕获，且**不调用** `on_error`。

### 2.5 失败 / 跳过规则

| 场景 | `export_errors` | `last_error` | `on_error` | 日志 | 图执行 |
|---|---|---|---|---|---|
| `end_time is None` | 不变 | 不变 | 不调用 | 无 | 正常 |
| `id` 为空 | +1 | `ValueError("empty span id")` | 调用 | WARNING | 正常 |
| `run_id` 为空 | +1 | `ValueError("empty run_id")` | 调用 | WARNING | 正常 |
| `start_time` / `end_time` 无法解析 | +1 | `ValueError("invalid ... time")` | 调用 | WARNING | 正常 |
| `end < start` | 不变（钳到 start） | 不变 | 不调用 | WARNING | 正常 |
| 非 `str` attribute 键 | +1（该 span 仍可导出，跳过该键） | `TypeError("non-str attribute key")` | 调用 | WARNING | 正常 |
| 传输 / 编码异常 | +1 | 原异常 | 调用 | WARNING | 正常 |
| 用户 exporter 返回 `SpanExportResult.FAILURE` | +1 | `RuntimeError("SpanExporter.export returned FAILURE")` | 调用 | WARNING | 正常 |
| 用户 `on_error` 抛 `Exception` | 不变（原错误保留） | 原错误 | 已调用 | WARNING（secondary） | 正常 |
| `BaseException` | 不变 | 不设置 | 不调用 | 无 | **传播** |

---

## 3. `Span` → OTel 映射

### 3.1 字段映射表

| `Span` 字段 | OTel 目标 | 规则 | 缺失 / 非法 |
|---|---|---|---|
| `id` | `SpanContext.span_id`（8 字节） | `sha256(b"freegraph:span:"+id)[:8]` → `int.from_bytes` | 空 ⇒ 跳过 span + 诊断 |
| `name` | `ReadableSpan.name` | 逐字 | 空串仍导出（不伪造） |
| `attributes` | `ReadableSpan.attributes` | 逐键直映射 + 值归一 + 派生 `gen_ai.conversation.id` | 非 str 键 ⇒ 跳过该键 + 诊断 |
| `parent` | `SpanContext`（parent） | 同一 span 哈希；`None` / 空 ⇒ 无 parent | 非法不抛；无效父 ⇒ 根 span |
| `start_time` | `ReadableSpan.start_time`（int ns） | `parse_iso_ns` | 非法 ⇒ 跳过 span + 诊断 |
| `end_time` | `ReadableSpan.end_time`（int ns） | `parse_iso_ns`；`None` ⇒ 不导出 | 非法 ⇒ 跳过 span + 诊断 |
| `context` | **不导出**（v1） | — | — |
| `thread_id` | `gen_ai.conversation.id`（派生） | 为 `str` 且属性中不存在时写入；已有同名键保留原值 | 非 str ⇒ 不派生 + 诊断 |
| `run_id` | `SpanContext.trace_id`（16 字节） | `sha256(b"freegraph:run:"+run_id)[:16]` | 空 ⇒ 跳过 span + 诊断 |
| `node` | **不新增属性** | 节点 span 的 `name` 即节点名；子 span 经 parent 回溯 | — |
| `checkpoint_id` | **不导出**（v1） | — | — |

### 3.2 身份与 trace 聚合

| 输出 | 规则 |
|---|---|
| `trace_id` | `sha256(b"freegraph:run:" + run_id.encode("utf-8")).digest()[:16]` |
| `span_id` | `sha256(b"freegraph:span:" + id.encode("utf-8")).digest()[:8]` |
| `parent_span_id` | 对 `parent` 使用同一 `span` 规则；`None` ⇒ 无 parent |
| `trace_flags` | `TraceFlags(TraceFlags.SAMPLED)` |
| `is_remote` | `False` |

**不变量**：同一 `run_id` 的所有 span 共享同一 `trace_id`；不同 `run_id` 不共享；
同一 `id` 多次导出得到相同 `span_id`（确定性）；不同 `id` 碰撞概率可忽略，v1 不做碰撞处理。

### 3.3 属性归一

| 输入类型 | 输出 |
|---|---|
| `str` / `bool` / `int` / `float` / `bytes` | 原样 |
| 同质标量序列（`list` / `tuple`，元素类型一致且为上述标量） | 原样序列 |
| `None` | `"null"`（JSON 字符串） |
| `dict` / 混合序列 / 自定义对象 | `json.dumps(value, ensure_ascii=False, sort_keys=True)`；失败 ⇒ `str(value)` |
| 非 `str` 键 | 跳过该键 + 诊断 |
| 嵌套 dict / list | 按 JSON 字符串 |

**派生键**：`thread_id` 非 `None` 且 `"gen_ai.conversation.id"` 不在 `Span.attributes` 中
⇒ 写入 `gen_ai.conversation.id = thread_id`；若已存在，保留原值。**MUST NOT** 出现
`freegraph.*` 前缀。

### 3.4 Status / SpanKind / Resource / Scope

| 输出 | 规则 |
|---|---|
| `Status` | `error.type` 存在 ⇒ `Status(StatusCode.ERROR, str(error.type))`；否则 `Status(StatusCode.UNSET)` |
| `SpanKind` | `gen_ai.operation.name` ∈ {`chat`, `execute_tool`} ⇒ `SpanKind.CLIENT`；否则 `SpanKind.INTERNAL` |
| `Resource` | `Resource({"service.name": "freegraph"})`（**直接构造**，不用 `Resource.create`） |
| `InstrumentationScope` | `InstrumentationScope("freegraph", freegraph.__version__)` |
| `events` / `links` | 空序列 |
| `schema_url` | 空 |

### 3.5 不导出字段

| 字段 / 实体 | 原因 |
|---|---|
| `context` | 本地补充上下文；不属于 OTLP 标准语义；未来若要导出需单独登记 |
| `checkpoint_id` | 依 B14F1 D-06 仅 MAY 复用；v1 不导出 |
| `node` | 节点 span 的 `name` 已表达；子 span 经 parent 链回溯；不伪造属性 |
| `TraceRecord` | 不是 `Span`；MUST NOT 生成独立 OTLP span |
| B20F2 查询结果 | 本 feature 不消费查询 API |

---

## 4. OTLP 传输数据

### 4.1 端点模式

```text
ReadableSpan
  └── encode_spans([readable]) ──> ExportTraceServiceRequest
        └── grpc.insecure_channel(endpoint) / grpc.secure_channel(endpoint, ssl_channel_credentials())
              └── TraceServiceStub(channel).Export(request, metadata=headers, timeout=timeout)
                    └── finally: channel.close()
```

- **官方编码器**：`opentelemetry.exporter.otlp.proto.common.trace_encoder.encode_spans`。
- **官方 stubs**：`opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc.TraceServiceStub`。
- **不自研**：不手写 protobuf / OTLP wire format / 手写 gRPC payload。
- **不读 env**：不 import `OTLPSpanExporter` 门面；不调用 `Resource.create()`。
- **不重试**：`stub.Export` 只调用一次；失败即记录。
- **channel 生命周期**：每次导出创建、`finally` 关闭；不缓存、不暴露。

### 4.2 导出器模式

```text
ReadableSpan
  └── user_exporter.export([readable]) -> SpanExportResult | None
```

- `user_exporter` 形状：`callable(getattr(obj, "export", None))`。
- `SpanExportResult.FAILURE` ⇒ 失败（合成 `RuntimeError`）；`None` / `SUCCESS` ⇒ 成功；
  其它返回值忽略。
- **不调用** `shutdown()` / `force_flush()`；TLS / 认证 / 重试由用户对象负责。

### 4.3 `Resource` / `InstrumentationScope`

| 项 | 值 | 说明 |
|---|---|---|
| `service.name` | `"freegraph"` | 固定；避免 `unknown_service`；不读 `OTEL_SERVICE_NAME` |
| scope name | `"freegraph"` | 固定 |
| scope version | `freegraph.__version__` | 当前 `0.0.3`（实现时读取 `freegraph.__version__`） |

> **v1 不提供** `resource_attributes` 参数；用户若需自定义 resource，可在未来 feature
> 或 `exporter=` 模式中自行处理。本 feature 的固定值是可判定的最小面。

---

## 5. 不变量（可测试）

1. **默认关闭**：不构造 `OtlpExporter` / 不传 `tracer` ⇒ 无 OTel import、无连接、无导出。
2. **零 env**：构造 / 导出 / 映射 / 传输路径 **不读取任何环境变量**。
3. **零默认端点**：无 `endpoint` / `exporter` ⇒ `ValueError`；无隐式默认。
4. **恰好一个**：`endpoint` 与 `exporter` 互斥。
5. **TLS 默认**：`insecure=False` 默认；本地明文需显式 `insecure=True`。
6. **同 run 同 trace**：同一 `run_id` ⇒ 同一 `trace_id`；不同 `run_id` ⇒ 不同。
7. **确定性**：同一 `Span` ⇒ 同一 `span_id` / `trace_id`（跨进程 / 重启稳定）。
8. **无私有前缀**：OTLP attributes 不含 `freegraph.*`；只有 `Span.attributes` 的键 +
   `gen_ai.conversation.id`。
9. **无重复载体**：不新增私有 span 类型 / 私有编码；复用 `Span` + 官方 SDK 数据对象。
10. **失败不阻断**：`Exception` 不进入图执行路径；`BaseException` 不被吞。
11. **不重试**：每个完整 span 最多一次导出尝试（用户 exporter 内部行为除外）。
12. **不重复导出**：同一 `on_span_end` 不因失败重放；后续 span 继续尝试。
13. **无后台线程**：无 async / batching / 后台 flush。
14. **只读字段面**：`Span` / `TraceSink` / `TraceRecord` / `TraceQuery` / `RunConfig` 零改动。
15. **不消费查询 API**：`FileTraceStore.query` / `SqliteTraceStore.query` 调用次数 == 0。

---

## 6. 验收数据 / 证据形态

| 证据 | 形态 | 落点 |
|---|---|---|
| 映射证据 | `ReadableSpan` 快照（name / ids / times / attributes / kind / status / resource / scope） | `test_b21f1_mapping.py` |
| wire 证据 | 最小 gRPC 接收端捕获的 `ExportTraceServiceRequest` | `test_b21f1_transport.py` |
| 默认关闭证据 | 子进程 `sys.modules` 无 `opentelemetry` / `grpc`；socket 监测「框架出站 == 0」 | `test_b21f1_default_off.py` |
| 失败隔离证据 | `export_errors` / `last_error` / WARNING；图结果不变 | `test_b21f1_export.py` |
| 示例证据 | 三个 `--help` / 真实后端冒烟 / 桩接收端记录 | `test_b21f1_examples.py` + manual-verification |
| 许可证证据 | wheel METADATA / `protobuf` LICENSE / G23 归一记录 | `contracts/dependency-and-gate-contract.md` |
| 不自研编码证据 | AST / 静态扫描无 protobuf encoder / wire format | `test_b21f1_gates.py` |

---

## 7. 与既有冻结面的关系

| 冻结面 | 本 feature 的处置 |
|---|---|
| `Span` 11 字段 | **零改动**；只读 |
| `TraceSink` 3 方法 | **零改动**；`OtlpExporter` 实现 |
| `TraceRecord` 13 字段 | **零改动**；不导出 |
| `TraceQuery` 5 字段 | **零改动**；不消费 |
| `RunConfig` 9 字段 | **零改动**；不新增 tracer 字段 |
| `freegraph.graph` 门面 | **零改动**；`OtlpExporter` 不进 |
| `compile()` 签名 | **零改动**；复用 `tracer=` |
| `observability.__all__` | **只增** `OtlpExporter` |
| B20F2 JSONL / SQLite / 查询语义 | **零改动**；不消费 |

---

## 8. 术语

| 术语 | 含义 |
|---|---|
| **端点模式** | `OtlpExporter(endpoint="host:port", ...)`；内部用官方编码器 + gRPC stubs |
| **导出器模式** | `OtlpExporter(exporter=<官方 SpanExporter>, ...)`；把 `ReadableSpan` 交给用户对象 |
| **完整 span** | `end_time is not None` 的 `Span` |
| **导出失败** | 映射跳过 / 传输异常 / 用户 exporter 返回 `FAILURE` |
| **跳过** | 因非法字段（空 id / run_id / 坏时间）不导出该 span，但仍记录诊断 |
| **框架出站** | 调用栈归因到 `freegraph/` 包路径的出站；用户显式启用的 OTLP exporter 是合法例外 |
| **私有前缀** | `freegraph.*` 等非标准属性前缀；本 feature 的 OTLP attributes **MUST NOT** 出现 |
