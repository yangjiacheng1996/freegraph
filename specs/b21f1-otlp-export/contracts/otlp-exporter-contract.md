# Contract: `OtlpExporter` 公开面

**Feature**: B21F1 · **Date**: 2026-11-24 · **Spec**: [../spec.md](../spec.md)

> 本契约锁定 **公开符号、构造签名、两种模式、校验、TLS、诊断、失败隔离、惰性 import
> 与生命周期**。实现 / 测试 / 文档 MUST 照此执行；plan 不得再翻。

---

## 1. 公开符号与位置

| 项 | 值 |
|---|---|
| 符号 | `freegraph.observability.OtlpExporter` |
| 层 | **L5** |
| 导出 | `freegraph.observability.__all__` **只增** `OtlpExporter` |
| 门面 | **不进** `freegraph.graph`；`import freegraph` 不加载 L5 |
| 协议 | 结构化实现 L1 `TraceSink`：`on_span_start` / `on_span_end` / `current_span` |
| 注入点 | `StateGraph.compile(*, tracer=OtlpExporter(...))`；**不新增** `invoke()` / `RunConfig` 字段 |

---

## 2. 构造签名

```python
OtlpExporter(
    *,
    endpoint: str | None = None,
    exporter: object | None = None,
    insecure: bool = False,
    headers: Mapping[str, str] | None = None,
    timeout: float | None = None,
    on_error: Callable[[BaseException], None] | None = None,
)
```

| 参数 | 类型 | 默认 | 规则 |
|---|---|---|---|
| `endpoint` | `str \| None` | `None` | 非空 `host:port`；不带 `http://` / `https://`；端口 1–65535；允许 IPv6 `[::1]:4317` |
| `exporter` | `object \| None` | `None` | 鸭子类型：`callable(getattr(obj, "export", None))` |
| `insecure` | `bool` | `False` | 仅端点模式；`True` ⇒ 明文 gRPC；与 `exporter=` 同用 ⇒ `ValueError` |
| `headers` | `Mapping[str, str] \| None` | `None` | **仅端点模式**；键 / 值必须 `str`；复制为 tuple；不读 env；与 `exporter=` 同用 ⇒ `ValueError` |
| `timeout` | `float \| None` | `None`（内部 `10.0`） | **仅端点模式**；正数；不读 env；与 `exporter=` 同用 ⇒ `ValueError` |
| `on_error` | `Callable[[BaseException], None] \| None` | `None` | 在锁外调用；仅 `Exception` 触发；`BaseException` 不调用 |

**恰好一个**：`endpoint` 与 `exporter` 必须二选一；都不传 / 都传 ⇒ `ValueError`。

---

## 3. 两种模式

### 3.1 端点模式（gRPC）

```python
OtlpExporter(endpoint="127.0.0.1:4317", insecure=True)
```

- 内部使用官方 `encode_spans` + 官方 `TraceServiceStub`；详见
  [span-to-otlp-mapping-contract.md](./span-to-otlp-mapping-contract.md) §6。
- `insecure=False`（默认）⇒ `grpc.secure_channel(endpoint, grpc.ssl_channel_credentials())`。
- `insecure=True` ⇒ `grpc.insecure_channel(endpoint)`。
- 每次导出创建短生命周期 channel；`finally` 关闭。
- **MUST NOT** 使用 `OTLPSpanExporter` 门面（读 env + 内部重试）。
- 缺 `[otlp]` ⇒ 构造时 `ImportError`，消息含 `pip install freegraph[otlp]`。

### 3.2 导出器模式

```python
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
OtlpExporter(exporter=OTLPSpanExporter(endpoint="http://.../v1/traces", headers={...}))
```

- 把 `ReadableSpan` 交给 `exporter.export([readable])`。
- 该模式**允许**用户传入官方 `OTLPSpanExporter`（HTTP）作为**用户侧对象**；它不是
  freegraph 的端点模式实现，故不受「端点模式 MUST NOT 用门面」的约束。
- `SpanExportResult.FAILURE` ⇒ 失败（合成 `RuntimeError`）；`None` / `SUCCESS` ⇒ 成功；
  其它返回值忽略。
- **不调用** `shutdown()` / `force_flush()`；TLS / 认证 / 重试由用户对象负责。
- `insecure=True` / `headers` / `timeout` 与 `exporter=` 同用 ⇒ 构造时 `ValueError`（仅端点模式有效）。
- 该模式使 HTTP-only 后端（OpenLIT / Langfuse）可接入；HTTP exporter 是**用户侧依赖**。

---

## 4. 校验与失败语义

| 场景 | 结果 |
|---|---|
| `endpoint` 与 `exporter` 都不传 | 构造时 `ValueError` |
| 两个都传 | 构造时 `ValueError` |
| `endpoint` 空 / 带 scheme / 无端口 / 端口越界 | 构造时 `ValueError`；不连接 |
| `insecure` 非 `bool` | 构造时 `ValueError` |
| `insecure=True` + `exporter=` | 构造时 `ValueError` |
| `headers` 非 mapping / 键或值非 `str` | 构造时 `ValueError` |
| `headers` / `timeout` + `exporter=` | 构造时 `ValueError`（仅端点模式有效） |
| `timeout` 非 `None` 且非正数 | 构造时 `ValueError` |
| `on_error` 非 `None` 且非 callable | 构造时 `ValueError` |
| `exporter` 无 `export` 可调用 | 构造时 `ValueError` |
| 缺 `[otlp]` + `endpoint=` | 构造时 `ImportError`（含安装提示） |
| 缺 `[otlp]` / OTel SDK + `exporter=` | 构造时 `ImportError`（含安装提示） |

> 校验全部在**构造时**完成；失败是显式用户错误，不发生在图运行中。

---

## 5. 生命周期与并发

| 项 | 规则 |
|---|---|
| 默认关闭 | 不构造 `OtlpExporter` / 不传 `tracer` ⇒ 零导出、零 OTel import、零连接 |
| `on_span_start` | **no-op** |
| `on_span_end` | 仅 `span.end_time is not None` 时导出；否则 return |
| `current_span` | 恒 `None` |
| 同步 | v1 **同步导出**；无后台线程 / async / batching |
| 锁 | 每实例一把 `threading.Lock`；锁内「映射 + 导出」；锁外 `on_error` / 日志 |
| 诊断读取 | `export_errors` / `last_error` 只读 property；无 setter / reset |
| 生命周期 | **不提供** `close()` / `__enter__` / `__exit__` / 上下文管理器 / 公开 OTel 对象 |
| channel | 端点模式每次导出短生命周期；`finally` 关闭；不缓存 |
| exporter 对象 | 不调用 `shutdown()` / `force_flush()`；不持有公开引用 |

---

## 6. 诊断与失败隔离

| 项 | 规则 |
|---|---|
| `export_errors` | 每个「有 `end_time` 但未成功导出」的 span +1（映射跳过 / 传输异常 / exporter `FAILURE`） |
| `last_error` | 最近一次失败对象；成功导出**不**清空；无 reset API |
| `on_error` | 可选回调；在锁外调用；仅 `Exception` 触发；其自身抛出的 `Exception` 被捕获并 WARNING，原错误保留；`BaseException` 不调用 `on_error` 且继续传播 |
| `logging` | 失败 / 跳过 ⇒ `logging.WARNING` |
| 隔离 | `Exception` **MUST NOT** 传播到图执行路径；图结果 / 节点序列 / `stream()` 不变 |
| `BaseException` | `KeyboardInterrupt` / `SystemExit` 等 **不被吞** |
| 重试 | **不重试**同一 span；`exporter=` 对象内部重试不受 freegraph 控制（文档说明） |
| 熔断 | **不熔断**；后续 span 继续尝试 |

**跳过规则**：空 `id` / 空 `run_id` / 非法时间 ⇒ 跳过该 span + 诊断；非 `str` attribute
键 ⇒ 跳过该键 + 诊断（span 仍可导出）；`end < start` ⇒ 钳到 `start` + WARNING（不跳过）。

---

## 7. 惰性 import

| 断言 | 规则 |
|---|---|
| `import freegraph` | 不加载 `freegraph.observability` / `opentelemetry` / `grpc` |
| `import freegraph.observability` | 不加载 `opentelemetry` / `grpc`（`_otlp_exporter.py` 顶层不 import 它们） |
| `OtlpExporter(...)` | 首次构造时才 import OTel / grpc |
| `_otlp_mapping.py` | 顶层 import OTel SDK / proto；只在 `OtlpExporter.__init__` 内惰性 import |
| `_otlp_transport.py` | 顶层 import `grpc` / `encode_spans` / `TraceServiceStub`；只在 `OtlpExporter.__init__` / `on_span_end` 内惰性 import |

---

## 8. 公开面边界

**只暴露**：

- 构造签名（§2）
- `on_span_start` / `on_span_end` / `current_span`
- `export_errors` / `last_error`

**MUST NOT 暴露**：

- `close()` / `__enter__` / `__exit__` / 上下文管理器
- 底层 OTel exporter / channel / stub / Resource / Scope
- 表结构 / wire format / protobuf 类型
- `_lock` / `_endpoint` 等私有字段的公开属性

---

## 9. 测试矩阵

| # | 用例 | 断言 |
|---|---|---|
| E-01 | 端点模式 + 最小 gRPC 接收端 | 收到完整 span；图结果不变（Linux 全量） |
| E-02 | 导出器模式 + 桩 `SpanExporter` | 收到 `ReadableSpan`；映射正确 |
| E-03 | 端点不可达 | 图成功；`export_errors > 0`；`last_error` 非空；WARNING |
| E-04 | 用户 exporter 抛 `Exception` | 隔离；图成功；诊断可感知 |
| E-05 | 用户 exporter 返回 `FAILURE` | 计失败；`last_error` 为合成 `RuntimeError` |
| E-06 | `on_error` 抛 `Exception` | 被捕获；原错误保留；图成功 |
| E-07 | `KeyboardInterrupt` / `SystemExit` | 不被吞（传播） |
| E-08 | 并发节点同时结束 | 导出器状态不损坏；图结果不变 |
| E-09 | 不传 tracer / 不构造 | 零 OTel import / 零出站 / 零导出 |
| E-10 | `endpoint` / `insecure` / `headers` / `timeout` 非法，或 `headers` / `timeout` + `exporter=` | 构造时 `ValueError`；零出站 |
| E-11 | 缺 extra / OTel SDK + `endpoint=` 或 `exporter=` | 构造时 `ImportError` |
| E-12 | `import freegraph.observability` | `opentelemetry` / `grpc` 不在 `sys.modules` |
| E-13 | `on_span_start` / `end_time=None` | no-op；不导出 |
| E-14 | 空 `id` / `run_id` / 坏时间 | 跳过 + 诊断；图成功 |
| E-15 | `end < start` | 钳到 start + WARNING；仍导出 |

---

## 10. 冻结面

- `Span` 11 字段 / `TraceSink` 3 方法 / `TraceRecord` 13 字段 / `TraceQuery` 5 字段 /
  `RunConfig` 9 字段 / `freegraph.graph` 门面 / `compile()` 签名：**零改动**。
- `observability.__all__`：**只增** `OtlpExporter`。
- 不新增 L1 `Protocol`；不新增 `invoke()` / `stream()` 关键字。
