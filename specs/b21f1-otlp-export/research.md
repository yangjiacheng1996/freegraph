# Research: B21F1 · OTLP 导出插件（可选 extra）+ 后端对接文档

**Date**: 2026-11-24 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

> **取证口径**：本文件对 OTel 生态的依赖 / API 断言来自 **PyPI wheel 元数据 + wheel
> 源码**（`pip download --no-deps` 于 2026-11-24；版本见下）。对上游 `langgraph` 的
> 行为断言沿用 B19F1 / B20F1 / B20F2 的 2026-11-21 实测基线，本 feature 不新增
> 上游行为断言。所有结论均为 **spec 阶段可判定**；无 `[NEEDS CLARIFICATION]`。

**实测版本（as-of 2026-11-24）**：

| 包 | 版本 | 许可证证据 |
|---|---|---|
| `opentelemetry-api` | 1.45.2 | `License-Expression: Apache-2.0` |
| `opentelemetry-sdk` | 1.45.2 | `License-Expression: Apache-2.0` |
| `opentelemetry-semantic-conventions` | 0.66b2 | `License-Expression: Apache-2.0` |
| `opentelemetry-exporter-otlp-proto-grpc` | 1.45.2 | `License-Expression: Apache-2.0` |
| `opentelemetry-exporter-otlp-proto-common` | 1.45.2 | `License-Expression: Apache-2.0` |
| `opentelemetry-exporter-otlp-common` | 0.66b2 | `License-Expression: Apache-2.0` |
| `opentelemetry-proto` | 1.45.2 | `License-Expression: Apache-2.0` |
| `googleapis-common-protos` | 1.76.0 | `License-Expression: Apache-2.0` |
| `grpcio` | 1.85.3 | `License-Expression: Apache-2.0` |
| `protobuf` | 7.36.2 | `License: 3-Clause BSD License`（**散文标识**，无 `License-Expression`） |
| `typing-extensions` | 既有白名单 | `PSF-2.0` |

---

## D-01 · Extra 名称与依赖闭包：`[otlp]` = 仅 gRPC 协议实现

**Decision**：新增独立 extra **`[otlp]`**，声明：

```toml
[project.optional-dependencies]
otlp = [
  "opentelemetry-api>=1.20",
  "opentelemetry-sdk>=1.20",
  "opentelemetry-exporter-otlp-proto-grpc>=1.20",
]
```

**Exact closure（实测）**：`opentelemetry-api` · `opentelemetry-sdk` ·
`opentelemetry-semantic-conventions` · `opentelemetry-exporter-otlp-proto-grpc` ·
`opentelemetry-exporter-otlp-proto-common` · `opentelemetry-exporter-otlp-common` ·
`opentelemetry-proto` · `googleapis-common-protos` · `grpcio` · `protobuf` ·
`typing-extensions`。**无** `requests` / `certifi` / `charset-normalizer` / `idna` /
`urllib3`。

**Rationale**：`opentelemetry-exporter-otlp` 元包与 `...-proto-http` 均会经 `requests`
拉入 `certifi`（MPL-2.0，不在宪法原则 IX 白名单）；只有 `...-proto-grpc` 路径避开它。
gRPC 路径仍复用**同一官方 OTLP 编码器**（`opentelemetry-exporter-otlp-proto-common`），
满足「不自研 protobuf / OTLP 编码」。

**Alternatives considered**：
- **元包 `opentelemetry-exporter-otlp`** — 拒绝：闭包含 `certifi`/MPL-2.0，G23 必拒。
- **HTTP 协议实现 `...-proto-http`** — 拒绝：同样含 `certifi`。
- **自研 OTLP/HTTP JSON** — 拒绝：违反提示词「不自研 OTLP 编码」；触发 +2 人日。
- **只交付文档、不交付 extra** — 拒绝：违反宪法原则 IV 的 MUST 与 spec FR-001。

---

## D-02 · 许可证：`protobuf` 的具名 SPDX 归一

**Decision**：在 G23 中增加**仅 `protobuf`** 的归一规则：

```
package == "protobuf" and identifier.strip() == "3-Clause BSD License"
    ⇒ "BSD-3-Clause"
```

**Rationale**：`protobuf 7.36.2` 的 METADATA 只有 `License: 3-Clause BSD License`，
没有 PEP 639 的 `License-Expression`；G23 的 SPDX 解析器会把它判为散文式标识并失败。
`protobuf` 的 `dist-info/licenses/LICENSE` 是标准 BSD-3-Clause 文本 ⇒ 归一是**证据
规范化**，不是放宽白名单。

**Alternatives considered**：
- **通用「散文 → SPDX」对照表** — 拒绝：B3F1 裁定 18 明确禁止；会变成豁免入口。
- **放宽白名单加入 `3-Clause BSD License`** — 拒绝：破 G23 的「精确 SPDX id」口径。
- **换掉 `protobuf`** — 不可行：OTel proto 硬依赖。
- **不归一、让 G23 红** — 拒绝：违反「MUST NOT 长期红 CI」。

**Governance**：这是对 B3F1 G23「MUST NOT 引入等价标识符对照表」的**唯一具名例外**；
MUST 走「登记 + 回溯修订 + 发起者书面追认」。未追认 ⇒ **STOP**，不得改走自研编码。

---

## D-03 · 传输：官方编码器 + 官方 gRPC stubs，不用 `OTLPSpanExporter` 门面

**Decision**：端点模式使用：

```python
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import TraceServiceStub

request = encode_spans([readable_span])  # ExportTraceServiceRequest
stub.Export(request=request, metadata=headers, timeout=timeout)
```

**Rationale（实测源码）**：`OTLPSpanExporter` 门面在构造期读取大量环境变量，且内部重试：

| 行为 | 证据（`opentelemetry-exporter-otlp-proto-grpc 1.45.2`） |
|---|---|
| 读 `OTEL_EXPORTER_OTLP_TRACES_INSECURE` | `opentelemetry/exporter/otlp/proto/grpc/trace_exporter/__init__.py:94-96` |
| 读 `OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE` | 同上 `:98-105` |
| 读 `OTEL_EXPORTER_OTLP_TRACES_TIMEOUT` | 同上 `:107-108` |
| 读 `OTEL_EXPORTER_OTLP_TRACES_COMPRESSION` | 同上 `:110-114` |
| 读 `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` / `HEADERS` | 同上 `:118-122` |
| 读 `OTEL_EXPORTER_OTLP_ENDPOINT` / `INSECURE` / `HEADERS` / `TIMEOUT` / `COMPRESSION` / `RETRYABLE_ERROR_CODES` / metrics | `exporter.py:286,292,304,325,332,366` |
| 内部最多 6 次重试 | `exporter.py:121`（`_MAX_RETRYS = 6`）· `:421-463` |
| 官方编码入口 | `opentelemetry/exporter/otlp/proto/common/_internal/trace_encoder/__init__.py:41` |
| 官方 gRPC stub | `opentelemetry/proto/collector/trace/v1/trace_service_pb2_grpc.py` |

freegraph 的 spec 要求 **零环境变量**（FR-008 / SC-006）与 **不重试**（FR-026）；
门面无法在不 monkeypatch `os.environ` 的前提下满足。thin transport 只复用**官方编码器**
与**官方 proto stubs**，不手写 protobuf / wire format，符合 FR-024。

**Alternatives considered**：
- **用门面 + 显式传所有参数** — 拒绝：即使传 `insecure=False`，仍会 `environ.get(CERTIFICATE)`；
  且门面仍内部重试。
- **临时清空 `os.environ`** — 拒绝：线程不安全、会影响用户代码、破坏「不读 env」的可判定性。
- **自研 gRPC / protobuf 编码** — 拒绝：违反提示词。
- **只支持 `exporter=` 模式** — 拒绝：FR-001 / 示例需要 `endpoint=` 模式。

---

## D-04 · 官方 SDK 数据对象：直接构造，避免 `Resource.create()`

**Decision**：

```python
readable = ReadableSpan(
    name=span.name,
    context=SpanContext(trace_id, span_id, is_remote=False, trace_flags=TraceFlags(TraceFlags.SAMPLED)),
    parent=parent_context_or_none,
    resource=Resource({"service.name": "freegraph"}),
    attributes=attributes,
    kind=kind,
    status=status,
    start_time=start_ns,
    end_time=end_ns,
    instrumentation_scope=InstrumentationScope("freegraph", __version__),
)
```

**Rationale（实测源码）**：
- `ReadableSpan` 构造函数在 `opentelemetry/sdk/trace/__init__.py:396,404-427`；接受
  `start_time` / `end_time` 为整数纳秒，`resource` / `instrumentation_scope` / `kind` /
  `status` 均显式。
- `Resource.create()` 在 `opentelemetry/sdk/resources/__init__.py:199` 调用
  `_build_resource_detectors()`，后者读 `OTEL_EXPERIMENTAL_RESOURCE_DETECTORS`
  （`:680`）、`OTEL_RESOURCE_ATTRIBUTES`（`:333`）、`OTEL_SERVICE_NAME`（`:350`）。
  为严格零 env，**MUST** 用 `Resource({...})` 直接构造（`:172`），**MUST NOT** 用
  `Resource.create()`。
- `InstrumentationScope` 构造在 `opentelemetry/sdk/util/instrumentation.py`，无 env 读取。

**Alternatives considered**：
- `Resource.create({"service.name": "freegraph"})` — 拒绝：仍会走 detectors / env。
- `TracerProvider` / 全局 provider — 拒绝：全局状态、隐式出站、生命周期。
- 省略 Resource — 拒绝：三后端会显示 `unknown_service`。

---

## D-05 · 身份：稳定哈希 + `TraceFlags.SAMPLED`

**Decision**：

| 输出 | 规则 |
|---|---|
| `trace_id`（16 字节） | `sha256(b"freegraph:run:" + run_id.encode("utf-8")).digest()[:16]` |
| `span_id`（8 字节） | `sha256(b"freegraph:span:" + id.encode("utf-8")).digest()[:8]` |
| `parent_span_id`（8 字节） | 对 `parent` 用同一 `span` 规则；`None` / 空 ⇒ 无 parent |
| `trace_flags` | `TraceFlags(TraceFlags.SAMPLED)` |
| `is_remote` | `False` |

**Rationale**：同一 `run_id` 必须聚合到同一 trace；跨进程 / 跨重启稳定；不依赖随机
状态或实例内映射。OTel `SpanContext` 要求 trace_id / span_id 为整数
（`opentelemetry/trace/span.py:439-473`）；把字节串 `int.from_bytes(..., "big")` 传入。
哈希前缀避免与其它系统碰撞；同一 run 的节点 / 模型 / 工具 span 共享 trace。

**Alternatives considered**：
- 每实例随机 `run_id → trace_id` 映射 — 拒绝：跨进程不一致，无法与本地 trace 关联。
- 直接把 freegraph `id`（32 hex）当 span_id — 拒绝：OTel span_id 只有 8 字节。
- 不加命名空间前缀 — 拒绝：降低与其它系统碰撞的区分度。

---

## D-06 · 时间：复用 `_time.parse_iso_ns`；纳秒精度

**Decision**：用 L5 既有 `freegraph.observability._time.parse_iso_ns` 解析
`span.start_time` / `span.end_time`；`end_time is None` ⇒ 不导出；解析失败 ⇒ 跳过该
span + `WARNING` + `export_errors + 1`；`end_ns < start_ns` ⇒ 钳到 `start_ns` +
`WARNING`。

**Rationale**：B18F1 产出的时间是 `YYYY-MM-DDTHH:MM:SS.nnnnnnnnn+00:00`
（`_time._ISO_NS_RE`），`parse_iso_ns` 直接解析为整数纳秒；`datetime.fromisoformat`
有微秒截断风险。`ReadableSpan` / OTLP 都使用 `start_time_unix_nano` /
`end_time_unix_nano`，整数纳秒无损。

**Alternatives considered**：
- `datetime.fromisoformat` — 拒绝：纳秒可能被截断到微秒。
- 字符串直接比较 — 拒绝：只适用于规范格式，且无法得到 OTLP 整数纳秒。
- `end < start` 直接丢弃 — 拒绝：损失诊断数据；钳到 start 更稳。

---

## D-07 · 属性：逐键直映射 + 唯一派生键

**Decision**：

- `Span.attributes` 逐键直映射为 OTLP attributes；B18F1 的 `gen_ai.*` 与 `error.type`
  原样保留。
- `thread_id` 非 `None` 且 `Span.attributes` 中**尚不存在** `gen_ai.conversation.id`
  时，派生该键；若已存在，保留原值（不覆盖）。
- `node` / `checkpoint_id` / `context` 不导出。
- 值归一：`str` / `bool` / `int` / `float` / `bytes` / 同质标量序列原样；其它类型
  `json.dumps(value, ensure_ascii=False, sort_keys=True)`；失败再 `str(value)`；
  `None` → `"null"`（JSON 字符串）。
- 非 `str` 键 ⇒ 跳过该属性 + `WARNING`；不抛到运行路径。

**Rationale**：B18F1 D-3 要求逐键直映射；`gen_ai.conversation.id` 是标准 semconv；
不出现 `freegraph.*` 私有前缀（SC-007）。`node` 已由节点 span 的 `name` 表达，子 span
经 `parent` 链回溯；`checkpoint_id` 依 B14F1 D-06 仅 MAY 复用，v1 不导出。

**Alternatives considered**：
- 导出 `freegraph.node` / `freegraph.checkpoint_id` — 拒绝：破「无私有前缀」判据；
  需单独登记偏离。
- 把 `checkpoint_id` 塞进 `attributes` — 拒绝：改变 B18F1 属性面。
- 覆盖已有 `gen_ai.conversation.id` — 拒绝：不尊重用户 / 生产者已有值。

---

## D-08 · 默认关闭、无默认端点、零 env、OTel 惰性 import

**Decision**：

- `OtlpExporter` 无默认 `endpoint` / `exporter`；二者恰好传一个。
- 不读 `OTEL_*` / `LANGSMITH_*` / 任何 env；不读 `os.environ` / `os.getenv`。
- `_otlp_exporter.py` 顶层只 import 标准库 + L1 `Span` + 同层 `_time`；OTel / grpc 只在
  `__init__` / `on_span_end` 内惰性 import。
- `__init__.py` 只 import `_otlp_exporter`（该模块顶层不 import OTel），因此
  `import freegraph.observability` 不加载 `opentelemetry` / `grpc`。

**Rationale**：宪法原则 I / IV；spec FR-006…FR-008 / FR-035。`import freegraph` 仍只加载
`freegraph`；`import freegraph.observability` 仍不加载 OTel（新门禁断言）。

**Alternatives considered**：
- 模块级 `import opentelemetry` — 拒绝：破坏惰性 / 基础安装零负担。
- 自动读 `OTEL_EXPORTER_OTLP_ENDPOINT` — 拒绝：零 env / 零默认端点。
- 全局 `TracerProvider` 自动注册 — 拒绝：隐式出站 / 全局状态。

---

## D-09 · 失败隔离与诊断

**Decision**：

| 项 | 规则 |
|---|---|
| 隔离范围 | `Exception`（导出 / 编码 / 连接 / 超时 / 用户 `exporter` / 用户 `on_error`）MUST NOT 传播到图执行路径 |
| `BaseException` | `KeyboardInterrupt` / `SystemExit` 等 **不吞** |
| `export_errors` | 每个「有 `end_time` 但未成功导出」的 span +1（含映射跳过 / 传输异常 / exporter `FAILURE`） |
| `last_error` | 最近一次失败对象；成功导出**不**清空；无 reset API |
| `on_error` | 可选回调；在锁外调用；其 `Exception` 被捕获并 `WARNING`，原错误保留为 `last_error` |
| `logging` | 失败 / 跳过均 `logging.WARNING` |
| 重试 | **不重试**同一 span；`exporter=` 对象的内部重试不受 freegraph 控制（文档说明） |
| 熔断 | **不熔断**；后续 span 继续尝试 |

**Rationale**：宪法原则 IV；spec FR-025…FR-029 / SC-003。四路诊断让「后端挂了」可感知，
但不把可观测层变成执行单点故障。

**Alternatives considered**：
- 静默吞错 — 拒绝：用户会误以为已导出。
- 重试 / 熔断 — 拒绝：v1 锁定不重试；熔断增加状态与不确定性。
- `on_error` 异常继续传播 — 拒绝：会破「不阻断」。

---

## D-10 · 同步、并发与生命周期

**Decision**：

- v1 **同步导出**：`on_span_end` 内完成一次导出；无后台线程 / async / batching。
- 每个 `OtlpExporter` 实例一把 `threading.Lock`；锁只包住「构造 request + 调用导出」；
  `on_error` / 日志在锁外。
- 端点模式**每次导出一个短生命周期 gRPC channel**：在 `try/finally` 中 `channel.close()`；
  不缓存 channel、不提供 `close()` / `__enter__` / `__exit__`。
- `exporter=` 模式直接把 `ReadableSpan` 交给用户对象；不调用 `shutdown()` / `force_flush()`。

**Rationale**：spec FR-013 / FR-014 / FR-028 / SC-012。短生命周期 channel 牺牲连接复用，
换取「无生命周期 API / 无持久句柄 / 无后台线程」；v1 本地诊断规模有限，正确性优先。

**Alternatives considered**：
- 持久 channel + `close()` — 拒绝：破 FR-014 公开面。
- `BatchSpanProcessor` / 后台线程 — 拒绝：v2；违反 FR-013。
- `atexit` 关闭 — 拒绝：全局状态，测试难隔离。

---

## D-11 · 端点 / TLS / headers / timeout 校验

**Decision**：

| 参数 | 规则 |
|---|---|
| `endpoint` | 非空 `host:port`；**MUST NOT** 带 `http://` / `https://` scheme；端口 1–65535；允许 IPv6 `[::1]:4317` |
| `exporter` | 鸭子类型：`callable(getattr(obj, "export", None))`；否则 `ValueError` |
| `insecure` | `bool`；默认 `False`（TLS）；仅 `endpoint=` 模式；与 `exporter=` 同用 ⇒ `ValueError` |
| `headers` | `Mapping[str, str] \| None`；**仅 `endpoint=` 模式**；复制为 tuple；值非 str ⇒ `ValueError`；不读 env；与 `exporter=` 同用 ⇒ `ValueError` |
| `timeout` | 正数或 `None`；**仅 `endpoint=` 模式**；默认 `10.0` 秒；不读 env；与 `exporter=` 同用 ⇒ `ValueError` |
| `on_error` | callable 或 `None`；仅 `Exception` 触发；`BaseException` 不调用 |
| 缺 extra | `endpoint=` **或** `exporter=` 但 `opentelemetry` / OTel SDK 不可导入 ⇒ 构造时 `ImportError`（含 `pip install freegraph[otlp]`） |

**Rationale**：spec FR-007 / FR-009 / SC-011；用户 clarify 选择 B（显式 `insecure`，
默认 TLS）。默认安全，本地示例显式 `insecure=True`。

**Alternatives considered**：
- URL scheme 推断 — 拒绝：用户已选 B；解析歧义。
- 默认明文 — 拒绝：默认不安全。
- 接受连接对象 — 拒绝：新增公开面；用户可用 `exporter=`。

---

## D-12 · 三后端示例：并列、无默认、分工表、至少一个真实后端

**Decision**：

| 示例 | 接入 | 后端 | 前置 | 来源 / as-of |
|---|---|---|---|---|
| `phoenix.py` | `endpoint="127.0.0.1:4317"`, `insecure=True` | Phoenix | `[otlp]` | `https://arize.com/docs/phoenix`（Q6 C14）· 2026-11-24 |
| `openlit.py` | `exporter=OTLPSpanExporter(endpoint="http://127.0.0.1:4318/v1/traces")` | OpenLIT | `[otlp]` + 用户自装 `opentelemetry-exporter-otlp-proto-http` | `https://docs.openlit.io/latest/overview` + `https://github.com/openlit/openlit` · 2026-11-24 |
| `langfuse.py` | `exporter=OTLPSpanExporter(endpoint="http://localhost:3000/api/public/otel/v1/traces", headers=Basic ...)`；HTTP exporter 延迟导入 | Langfuse | `[otlp]` + 用户自装 HTTP exporter | `https://langfuse.com/docs` + `https://langfuse.com/self-hosting` · 2026-11-24 |

**Rationale**：spec FR-030…FR-034；OpenLIT / Langfuse 主要走 OTLP/HTTP，Phoenix 走 gRPC；
freegraph 的合规 extra 只含 gRPC，HTTP 由用户自装 exporter，不进依赖闭包。三示例并列、
无默认推荐，避免 affiliation / 维护风险。分工表明确 freegraph 本地运行时诊断 vs 外部
后端的 trace / 分析 / 评测 / Prompt 管理。

**Alternatives considered**：
- 把 HTTP exporter 放进 `[otlp]` — 拒绝：`certifi` / MPL-2.0。
- 只做 Phoenix — 拒绝：偏离提示词三后端。
- 选默认推荐后端 — 拒绝：affiliation / R12 文档风险。
- 真实三后端全必跑 — 拒绝：CI 不稳定；改为「至少一个真实 + 其余桩」。

---

## D-13 · 测试 / CI 落点

**Decision**：

| 层 | 测试 |
|---|---|
| 纯映射 | `tests/observability/test_b21f1_mapping.py`（身份 / 时间 / 属性 / status / kind / Resource） |
| 公开 API | `tests/observability/test_b21f1_export.py`（桩导出器 / 诊断 / 隔离 / 并发） |
| 传输 | `tests/observability/test_b21f1_transport.py`（最小 gRPC 接收端；`linux_only` + `full_install`） |
| 默认关闭 | `tests/observability/test_b21f1_default_off.py`（子进程：无 OTel / grpc / 零出站） |
| 示例 | `tests/observability/test_b21f1_examples.py`（存在 / `--help` / 分工表 / as-of） |
| 契约 / 门禁 | `tests/contracts/test_b21f1_contracts.py` / `test_b21f1_gates.py` |
| 差分 | `tests/differential/test_b21f1_otlp_parity.py`（D-601…D-608） |
| 人工 | `harness/verification/B21F1/acceptance.py` + `manual-verification.md` + 文档守卫 |

**CI**：全量作业安装 `.[otlp]`；G21 / G23 取证对象 = 含 `otlp` 的 `extras-v2.toml`；
非 Linux 作业用桩导出器；Linux 全量作业跑最小 gRPC 接收端。

**Rationale**：判据级覆盖（原则 VI）；真实 wire 验证 + 稳定 CI；不靠单一 mock。

**Alternatives considered**：
- 只做 mock — 拒绝：不能证明 OTLP wire 可被接收端解析。
- 只做真实后端 — 拒绝：CI 不稳定 / 需要 Docker。
- 不装 `[otlp]` 进 CI — 拒绝：G23 / 映射测试无法取证。

---

## D-14 · 文档 / 归属 / 风险

**Decision**：更新 `README.md` 的「可观测 / OTLP 导出」章节；新增
`harness/examples/B21F1/README.md`；更新 `THIRD_PARTY_NOTICES`；
`harness/demo/README.md` / `harness/verification/README.md` 增 B21F1 行；
`manual-verification.md` 记录证据。

**Rationale**：宪法原则 V / X；FR-032 / FR-040 / FR-041；OpenLIT 旧路径 404 与现行
`docs.openlit.io` 必须同时写；三个后端来源 + as-of；不内嵌 Phoenix / Langfuse / OpenLIT。

**Alternatives considered**：
- 只写代码注释 — 拒绝：不满足交付物 / 人工门禁。
- 把示例放进发行包 — 拒绝：增加发行面；`harness/` 不进发行包。

---

## D-15 · 治理 / 门禁变更（研究阶段新增发现）

**Decision**：除 spec §6 已列的 v1.17.0 具名例外 / G3 / G26 / `__all__` 外，研究阶段发现
**三项额外门禁冲突**，MUST 登记并追认：

| # | 冲突 | 变更 |
|---|---|---|
| **G-1** | G23「散文式标识 MUST 失败 / MUST NOT 引入等价标识符对照表」 vs `protobuf` | 仅 `protobuf` 具名归一 → `BSD-3-Clause` |
| **G-2** | B19F1「L5 模块禁止 import `opentelemetry`」 vs 可选导出器 | 仅 3 个 `_otlp_*.py` 具名例外；新增运行时惰性断言 |
| **G-3** | B19F1 third-party import / egress 扫描 + G26 网络扫描 vs `grpc` | `grpc` 加入网络客户端清单（更严）；仅 `_otlp_transport.py` 进例外名单 |

**Rationale**：这些是「不落地就无法满足 spec」的门禁冲突；MUST 按「登记 + 回溯修订 +
发起者追认」处理，**MUST NOT** 静默改门禁或放宽判据。spec §6 需补 G-1 / G-2 两行
（G-3 已部分覆盖于 G26）。

**Alternatives considered**：
- 不登记、实现时再改 — 拒绝：违反原则 VI / VIII。
- 放宽扫描域 / 加通用豁免 — 拒绝：门禁失效。
- 放弃 OTel 导入 — 拒绝：无法实现。

---

## 已决实现细节（供 tasks / implement 直接照做）

1. `_otlp_mapping.py` 顶层 import OTel SDK / proto 类型；只在 `OtlpExporter.__init__`
   内被 import。`_otlp_transport.py` 顶层 import `grpc` / `encode_spans` / `TraceServiceStub`；
   只在 `on_span_end` 或 `__init__` 内被 import。
2. `_otlp_exporter.py` 顶层**禁止** import `opentelemetry` / `grpc`；只 import 标准库 +
   `freegraph.contracts.trace.Span` + `._time`（同层）。
3. `OtlpExporter` 实例状态：`_endpoint` / `_exporter` / `_insecure` / `_headers` /
   `_timeout` / `_on_error` / `_lock` / `_export_errors` / `_last_error`。
4. `export_errors` / `last_error` 以只读 `@property` 暴露；无 setter。
5. `on_span_end` 流程：`end_time is None` ⇒ return；`with _lock:` 构造 `ReadableSpan`
   （失败 ⇒ 记诊断）→ 调用 transporter / `exporter.export`（异常 ⇒ 记诊断）→ 锁外
   `on_error` / `WARNING`。
6. `endpoint` 模式短生命周期 channel：`try/finally channel.close()`；`metadata` 用
   `tuple(headers.items())`；`timeout` 默认 `10.0`。
7. `exporter` 模式：`result = exporter.export([readable])`；`SpanExportResult.FAILURE`
   ⇒ 合成 `RuntimeError("SpanExporter.export returned FAILURE")` 记诊断；其它返回值忽略。
8. `Resource` 用 `Resource({"service.name": "freegraph"})`；**禁止** `Resource.create`。
9. `SpanKind`：`gen_ai.operation.name` ∈ {`chat`, `execute_tool`} ⇒ `CLIENT`；否则
   `INTERNAL`。
10. `Status`：`error.type` 存在 ⇒ `Status(StatusCode.ERROR, str(error.type))`；否则
    `Status(StatusCode.UNSET)`。
11. `TraceFlags`：`TraceFlags(TraceFlags.SAMPLED)`；`is_remote=False`。
12. `InstrumentationScope("freegraph", freegraph.__version__)`。
13. 三示例都支持 `--help`；至少 `phoenix.py` 在真实 Phoenix 上冒烟；OpenLIT / Langfuse
    用 HTTP exporter 对象；每个示例从 CLI 读端点，不读 env。
14. `harness/examples/B21F1/README.md` 必须有：三后端来源 + as-of、旧路径 404、现行
    OpenLIT URL、分工 / 重叠表、无默认推荐声明、HTTP exporter 用户侧依赖说明。

**无未决澄清。**
