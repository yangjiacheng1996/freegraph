# Contract: 上游对标（langgraph）与差分

**Feature**: B21F1 · **Date**: 2026-11-24 · **Spec**: [../spec.md](../spec.md)

**Upstream version**: `langgraph` **1.2.11** / `langchain-core` **1.7.6** /
`langsmith` **0.14.17**（取证于 2026-11-21，本仓库 `.venv` 实际安装版本；沿用
B19F1 / B20F1 / B20F2 的版本钉住口径）。

> **口径**：上游 `langgraph` 内核**没有**内建 OTLP exporter，也**没有** freegraph
> 这样的「自有 `Span` + 可选 OTLP 导出器」。上游可观测出口是 LangSmith SaaS；
> OTel 接入依赖外部 instrumentor / 用户自行桥接。本 feature 的主体落在原则 XI 的
> **必须自研区 ③（上游没有的能力）** 与 **①（零账号 / 零主动出站 / 零依赖）**；
> 只有「默认关闭」「失败隔离」「成对生命周期」几类行为面可与上游对齐。

---

## 1. 逐条对照（P-01…P-07）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| **P-01** | **OTLP 导出能力** | 上游内核无 OTLP exporter；可观测出口是 `langsmith/client.py:139`（httpx 客户端）· `:619`（默认 `https://api.smith.langchain.com`）· `langsmith/_internal/_background_thread.py:377`（批量 ingest） | 可选 `[otlp]` + `OtlpExporter`；标准 OTLP 导出到用户显式端点；无账号、无默认远端 | **DIFF**（自研区 ③） | 宪法原则 IV「MUST 以 OTLP 等标准协议输出」；上游对应物是私有 SaaS |
| **P-02** | **默认关闭 / 环境变量** | `langchain_core/tracers/context.py:114-120`（只有启用 tracing 才构造 tracer）· `langsmith/utils.py:119-144`（`LANGSMITH_*` 可影响开关） | 不注入 `OtlpExporter` ⇒ 零导出 / 零 import / 零连接；不读 `OTEL_*` / `LANGSMITH_*` / 任何 env | **SAME**（默认关闭）· **STRICTER**（不读 env） | 宪法原则 I / IV；「端点存在即自动开启」是反面教材 |
| **P-03** | **失败隔离** | `langchain_core/callbacks/manager.py:351-354`（handler 异常被捕获并记警告） | 导出失败被四路诊断隔离；图结果不变；`BaseException` 不吞 | **SAME**（隔离语义）· **STRICTER**（可感知面） | 宪法原则 IV；静默吞错会让用户误以为已导出 |
| **P-04** | **标准协议 vs 私有格式** | 上游上报 LangSmith run tree（私有 schema）；OTel 需外部桥接 | 自有 `Span` 逐字段映射为官方 OTel SDK 数据对象，再由官方编码器编码为 OTLP | **DIFF** | 自研区 ①③；标准协议是可导出到任一后端的前提 |
| **P-05** | **属性命名** | 上游 run tree 的 inputs / outputs / extra；无 `gen_ai.*` 约束 | `Span.attributes` 逐键直映射（B18F1 的 `gen_ai.*` + `error.type`）；派生 `gen_ai.conversation.id`；无私有前缀 | **DIFF**（表示层）· **STRICTER**（属性面收窄到 B18F1 allowlist） | 宪法原则 IV「SHOULD 对齐 OTel GenAI semconv」；B18F1 D-3 |
| **P-06** | **成对生命周期** | `langchain_core/tracers/base.py:261`（on_chain_start）/ `:306`（on_chain_end） | `on_span_start` no-op / `on_span_end` 仅导出完整 span；开始 / 结束按 `id` 成对 | **SAME**（行为面）· **DIFF**（表示） | 导出只发生在结束时；与 B18F1 / B19F1 一致 |
| **P-07** | **运行时依赖闭包** | `langchain-core 1.7.6` 的 `Requires-Dist` 含 `langsmith<1.0.0,>=0.14.9`（+ `certifi` / `httpx` / `pydantic` 等）· B18F1 实测 **E-4** | 基础安装闭包为空集；`[otlp]` 只含白名单包；无 `langchain*` / `langsmith` / `langgraph*` | **STRICTER** | 宪法原则 I / II / IX |

---

## 2. 实测基线（沿用 B19F1 / B20F1 · 取证于 2026-11-21）

| # | 实验 | 结果 |
|---|---|---|
| **E-1** | 两节点线性图 `a → b`，`invoke()`，不传 callbacks / tracer，环境变量全清 | 正常返回；**无任何**回调 / span / 出站（默认关闭） |
| **E-2** | 同图，传入自定义 `BaseCallbackHandler` | 共 6 条 handler 事件；callback 驱动的图节点内 `get_current_run_tree()` 为 `None` |
| **E-3** | `boom` 节点抛 `RuntimeError`，传入自定义 handler | 异常原样抛出；run 生命周期仍完成（`on_chain_error`） |

> **实测来源**：B19F1 spec §2 的 `/tmp/b19_upstream_probe.py`（2026-11-21 实跑）。
> 本 feature **不新增**上游行为断言；P-01 / P-04 / P-05 / P-07 的「上游无内建 OTLP /
> 私有 run tree / 依赖闭包」取证于**上游源码阅读**与 `.venv` 实际安装版本，仅用于说明
> 能力缺失与表示差异，**不**作为本 feature 的差分行为断言。

---

## 3. OTel 生态行为证据（本 feature 新增 · as-of 2026-11-24）

> 这些不是「上游 langgraph」的断言，而是**依赖实现**的实测证据，用于解释
> 为什么本 feature 不用 `OTLPSpanExporter` 门面，而用官方编码器 + 官方 stubs。

| # | 行为 | 证据（`opentelemetry-exporter-otlp-proto-grpc 1.45.2` / `opentelemetry-sdk 1.45.2`） |
|---|---|---|
| **O-1** | 门面构造期读 env | `opentelemetry/exporter/otlp/proto/grpc/trace_exporter/__init__.py:94-122`（INSECURE / CERTIFICATE / TIMEOUT / COMPRESSION / ENDPOINT / HEADERS） |
| **O-2** | mixin 也读 env | `opentelemetry/exporter/otlp/proto/grpc/exporter.py:286,292,304,325,332,366` |
| **O-3** | 门面内部重试 | `exporter.py:121`（`_MAX_RETRYS = 6`）· `:421-463` |
| **O-4** | 官方编码入口 | `opentelemetry/exporter/otlp/proto/common/_internal/trace_encoder/__init__.py:41`（`encode_spans`） |
| **O-5** | 官方 gRPC stub | `opentelemetry/proto/collector/trace/v1/trace_service_pb2_grpc.py` |
| **O-6** | `ReadableSpan` 可直接构造 | `opentelemetry/sdk/trace/__init__.py:396,404-427` |
| **O-7** | `Resource.create()` 读 env | `opentelemetry/sdk/resources/__init__.py:199,333,350,680` |

**结论**：为满足 spec 的「零 env」与「不重试」，本 feature **MUST** 使用
`encode_spans` + `TraceServiceStub`，**MUST NOT** 使用 `OTLPSpanExporter` 门面；
**MUST** 用 `Resource({...})` 直接构造，**MUST NOT** 用 `Resource.create()`。

---

## 4. 差分场景组（D-601…D-608）

> 编号段避开 B18F1 的 D-201…D-208、B19F1 的 D-301…D-310、B20F1 的 D-401…D-408、
> B20F2 的 D-501…D-508。

| # | 场景 | 断言（结果 / 失败与否） | 判词 |
|---|---|---|---|
| **D-601** | 标准协议导出 vs 上游私有上报 | freegraph：最小 OTLP 接收端可解析并收到 span；上游：上报 LangSmith 私有 run tree，需账号 | DIFF（P-01 / P-04） |
| **D-602** | 默认关闭 | 两侧不启用时都正常完成；freegraph 额外断言 OTel import == 0 / 出站 == 0 | SAME（默认关闭）· STRICTER（零 import） |
| **D-603** | 环境变量 | freegraph：设置 `OTEL_*` / `LANGSMITH_*` 不改变导出行为；上游：`LANGSMITH_*` 可影响开关 | STRICTER（P-02） |
| **D-604** | 失败隔离 | freegraph：端点不可达图仍成功；上游：callback handler 异常被捕获 | SAME（隔离）· STRICTER（诊断） |
| **D-605** | 成对生命周期 | freegraph：每个完整 span 一次导出；上游：成对 callback run | SAME（行为面）· DIFF（表示，P-06） |
| **D-606** | 属性映射 | freegraph：`Span.attributes` 逐键直映射；上游：run tree inputs / outputs / extra | DIFF（P-05） |
| **D-607** | 依赖闭包 | freegraph 基础闭包为空；`[otlp]` 仅白名单包；上游闭包含 `langsmith` / `httpx` / `certifi` 等 | STRICTER（P-07） |
| **D-608** | 无自研编码 | freegraph：AST / 静态扫描无 protobuf / OTLP wire encoder；只调用官方编码器 / stubs；上游：无内建 OTLP 编码 | DIFF（自研区 ③） |

**判词分布**：SAME 行为面 3（D-602 默认关闭段 / D-604 隔离段 / D-605 生命周期段）+
STRICTER 4（D-602 零 import / D-603 / D-604 诊断面 / D-607）+ DIFF 4
（D-601 / D-605 表示 / D-606 / D-608）。

**证据口径**：D-601 / D-605 / D-606 / D-608 的上游侧是**能力 / 表示层说明**
（源码阅读），不是需要实测的差分行为断言；差分用例只对 freegraph 侧做可执行断言
（D-602 / D-603 / D-604 / D-607 的零 import / env / 隔离 / 依赖闭包除外）。

**落点**：`tests/differential/test_b21f1_otlp_parity.py` ⇒ **CI 的 Linux 全量档真跑**
（上游缺席即 skip · 沿用 B5F2 的「缺席即 skip」纪律）。本 feature 不与上游做逐字节
结果对比，只对齐「默认关闭 / 失败隔离 / 成对生命周期 / 零出站 / 依赖闭包」五类行为面。

---

## 5. 偏离登记（仅限三类 · 其余一律照抄）

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **DIFF**（自研区 ③：上游没有的能力） | 上游无内建 OTLP exporter、无自有 `Span` 导出协议（对应 **P-01 / P-04**） | 宪法原则 IV「MUST 以 OTLP 等标准协议输出」；上游对应物是 LangSmith SaaS，引入即破零依赖 / 零账号 | 本 feature |
| **X-2** | **STRICTER**（自研区 ①：零账号 / 零主动出站 / 零依赖） | 上游 `LANGSMITH_*` 可影响 tracing 开关；freegraph 不读任何 env（对应 **P-02** 的 STRICTER 半段） | 宪法原则 I；端点只认显式参数 | 本 feature |
| **X-3** | **SAME + STRICTER**（隔离语义 SAME；可感知面更严） | 导出失败隔离；上游 handler 异常被捕获（对应 **P-03**） | 宪法原则 IV；静默吞错会让用户误以为已导出 | 本 feature |
| **X-4** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 标准 OTLP span vs 上游 LangSmith run tree（对应 **P-04 / P-05 / P-06** 的表示差异） | 标准协议是可导出到任一后端的前提；属性面收窄到 B18F1 allowlist | B18F1（属性面）· 本 feature（导出） |
| **X-5** | **STRICTER**（自研区 ①：零依赖） | 基础安装闭包为空；`[otlp]` 仅白名单包；上游闭包含 `langsmith` / `httpx` / `certifi`（对应 **P-07**） | 宪法原则 IX；产品承诺 | 本 feature |

**三态一致性**：P-01 / P-04 ↔ X-1 / X-4；P-02 ↔ X-2；P-03 ↔ X-3；P-05 / P-06 ↔ X-4；
P-07 ↔ X-5。**逐字一致**，无「对照表说 STRICTER、偏离登记说 DIFF」的冲突。

---

## 6. 破冻结面的回溯修订清单（本 feature 触发）

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| 宪法 v1.7.0「v1.0 无 `[project.optional-dependencies]`」 | `.specify/memory/constitution.md`（已改为 v1.17.0）+ `pyproject.toml` | **唯一具名例外**：仅 `[otlp]`；其它 extra 仍归 v2.0；基础安装闭包不变；条件见宪法 v1.17.0 正文 | 宪法 v1.17.0 正式修订 + 发起者追认；正式文字落 manual-verification |
| B3F1 G3 extras 白名单 | `tests/contracts/test_architecture.py` | **只增** 7 名；既有 12 名逐字保留 | 发起者书面追认 + manual-verification |
| B3F1 G23「禁止归一化」 | `_gatekit.py` / `gate_G23_licenses.py` / `architecture-gates.md` | **仅 `protobuf`** 具名归一；不放宽白名单 | 发起者书面追认 + manual-verification |
| B3F1 G26 例外名单 | `_gatekit.py::G26_EXCEPTED_MODULES` | **只增** `_otlp_transport.py`；`grpc` 加入网络清单（更严） | manual-verification |
| B19F1 `opentelemetry` import 禁令 | `test_b19f1_gates.py` / `test_architecture.py` | **拆分而不删**：仅 3 个 OTLP 模块具名例外；新增运行时惰性断言 | manual-verification |
| `observability.__all__` 精确集合 | `test_api_snapshot.py` / `test_b19f1_lazy.py` | **只增** `OtlpExporter` | manual-verification |
| **不破** | `Span` 11 字段 · `TraceSink` 3 方法 · `TraceRecord` 13 字段 · `TraceQuery` 5 字段 · `RunConfig` 9 字段 · `stream()` 信封 · 门面 8 符号 · L1 22 符号 · B20F2 查询语义 / 行结构 / schema · `compile()` 签名 | **零改动** | — |

---

## 7. 差分测试约束

- 落点：`tests/differential/test_b21f1_otlp_parity.py`。
- **上游缺席即 skip**（`langgraph` / `langchain-core` / `langsmith` 未安装）。
- 不对上游做逐字节结果对比；只对 freegraph 侧做可执行断言。
- D-601 / D-605 / D-606 / D-608 的上游侧为**能力 / 表示说明**，不要求实测。
- 差分测试 MUST NOT 引入 `langchain*` / `langsmith` 到 freegraph 运行时路径。
