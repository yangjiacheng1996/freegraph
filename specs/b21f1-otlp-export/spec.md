# Feature Specification: B21F1 · OTLP 导出插件（可选 extra）+ 后端对接文档

**Feature Branch**: `b21f1-otlp-export`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_specify` 钩子；既有 feature 同样在 `main` 上开发）

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: `harness/features/B21F1_OTLP导出插件与后端对接.md` —— 交付**可观测生态出口**：把 freegraph 自有的 `Span` 编码为 **OTLP** 并导出到用户**显式提供的端点**（可选 extra，**默认关闭**），同时交付**三个后端的最小对接示例**（OpenLIT / Langfuse / Phoenix）与**已知失效风险说明**。判定：**可导出到任一 OTel 后端**。

> **范围提醒**：本 feature 是 **L5 可观测层**的**导出侧**。
> 它只消费 B18F1 生产、B19F1 推送的 `Span`；**MUST NOT** 消费 B20F2 的
> `query()` 查询 API，**MUST NOT** 把 B19F1 的 `TraceRecord` 映射为 OTLP span，
> **MUST NOT** 修改 `Span` / `TraceSink` / `TraceRecord` / `TraceQuery` /
> `RunConfig` 的任何字段，**MUST NOT** 改变图执行结果。
> **不实现**本地 Agent Server / SSE（v2 / D8）、前端 UI（v2 / B26）、
> 评测 / 数据集（永不做）、自托管 trace 后端（路线 A，MUST NOT）、async 导出（v2）、
> 自研 protobuf / OTLP 编码（明确不采用）。

---

## Spec 阶段结论（立项书 §7.5 单点敏感性 · MUST）

> 提示词要求：若该 extra **无法**满足「自有 `Span` → OTLP」的映射（须自研编码），
> 则本 feature **需上浮 +2 人日**；触发信号 = spec 阶段确认**必须自研 OTLP 编码**。
> 本节是**结论**，`/speckit.plan` 与 `/speckit.implement` **MUST** 照此执行。

**结论：可行，不触发 +2 人日上浮。**

理由（按可判定事实）：

1. `Span` 的 11 个字段均有确定的 OTLP 对应物（见「形态锁定裁定 §3」）；`Span.attributes`
   的键来自 B18F1 的 `gen_ai.*` 允许清单（唯一例外是失败时的 `error.type`），可**逐键直映射**，
   **不需要**解析任何 freegraph 私有格式（B18F1 D-3）。
2. 映射由**官方 OTel SDK 数据对象 + 官方 OTLP 编码器 + 官方 gRPC stubs** 完成：
   freegraph 只组装 `ReadableSpan`，调用官方 `encode_spans` 得到
   `ExportTraceServiceRequest`，再由官方 `TraceServiceStub.Export` 发送；
   **不写 protobuf / OTLP wire format**。**MUST NOT** 使用
   `OTLPSpanExporter` 门面——它在构造期读取 `OTEL_EXPORTER_OTLP_*` 且内部最多重试
   `_MAX_RETRYS = 6`，与「零 env / 不重试」冲突（证据见 plan / research）。
3. 已知合规障碍（`opentelemetry-exporter-otlp` 元包的 `certifi` / MPL-2.0）**不影响映射可行性**：
   本 feature 改为仅声明 **gRPC 传输实现**（`opentelemetry-exporter-otlp-proto-grpc`），
   避开 `requests` / `certifi`；`protobuf` 的许可证语义是 BSD-3-Clause（散文标识经
   **权威 SPDX 归一**登记，不改白名单）。HTTP-only 后端由**用户自装官方 HTTP exporter**
   并以「显式传入导出器」模式接入，不进入 freegraph 的依赖闭包。
4. 唯一新增工作量是「额外 extra 声明 + 许可证归一 + 三个示例」，属本 feature 基准范围，
   不构成「自研编码」上浮。

**若后续实测推翻第 2 条**（官方编码器 / gRPC stubs 无法接受 freegraph 组装的 SDK 数据对象，
且必须自研 OTLP 编码）⇒ **MUST 立即按 §7.5 上浮 +2 人日并回写本结论**；
在触发前，tasks / plan **MUST NOT** 预留自研编码路径。

---

## 形态锁定裁定（spec 阶段写死 · plan 不得再翻）

> 本节把实现前必须写死的形态一次锁定。每条均给出**采用 / 不采用**与理由；
> `/speckit.plan` 与 `/speckit.implement` **MUST** 照此执行。

### 1. Extra 名称、依赖内容与许可证合规（FR-001 / A1 / SC-005 / SC-011）

**锁定形态：新增独立 extra `[otlp]`，不修改既有 `[otel]`。**

| 项 | 锁定值 | 理由 |
|---|---|---|
| extra 名 | **`[otlp]`** | 与 B3F1 的 `[otel]`（`opentelemetry-api` + `opentelemetry-sdk`，**不含 exporter**）区分；提示词的「如 `[otel]`」只是举例，不是强制名称 |
| 依赖声明 | `opentelemetry-api` · `opentelemetry-sdk` · **`opentelemetry-exporter-otlp-proto-grpc`** | 只用 **gRPC 传输实现**，避免 `opentelemetry-exporter-otlp` 元包经 `requests` 拉入 `certifi`（MPL-2.0，不在许可证白名单） |
| MUST NOT 声明 | `opentelemetry-exporter-otlp`（元包）· `opentelemetry-exporter-otlp-proto-http` · `requests` · `certifi` | 元包与 HTTP 路径的闭包含 `certifi`；为用户演示 HTTP 后端时，由**用户自行安装**，不进 freegraph 声明 |
| 基础安装 | **零变化**：`dependencies = []`；`[otlp]` 默认不安装 | FR-001 / SC-005 |
| 许可证门禁 | `[otlp]` 闭包逐包 ∈ {MIT, Apache-2.0, BSD-2/3, PSF}；`protobuf` 的散文标识 `3-Clause BSD License` 经**权威 SPDX 归一**为 `BSD-3-Clause`（依据其 LICENSE 文件）；**MUST NOT** 放宽白名单 | 宪法原则 IX（NON-NEGOTIABLE）；B3F1 裁定 21 / D14 的遗留技术债在本 feature 解决 |

> **与提示词字面的偏差（已登记）**：FR-001 / FR-004 字面写 `opentelemetry-exporter-otlp`。
> 本 spec 取**同项目官方的 gRPC 协议实现**（`opentelemetry-exporter-otlp-proto-grpc`），
> 因为它与元包使用**同一官方 OTLP 编码实现**，且是**唯一**能同时满足「复用官方 OTLP 编码实现
> + 许可证白名单」的路径。**MUST NOT** 因此自研编码；**MUST NOT** 为此放宽许可证白名单。
>
> **2026-11-24 用户确认（选项 A）**：`[otlp]` 只声明 gRPC 协议实现；HTTP-only 后端由
> 用户自装官方 HTTP exporter，以 `exporter=` 模式接入。

### 2. 公开 API 与注入形态（FR-002 / FR-004 / A4 / SC-002 / SC-015）

**锁定形态：L5 新增公开符号 `freegraph.observability.OtlpExporter`，实现 `TraceSink` 三方法；经既有 `StateGraph.compile(*, tracer=...)` 注入。**

```python
# 形态示意（非最终代码结构）
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

| 项 | 锁定值 | 理由 |
|---|---|---|
| 公开符号 | **`OtlpExporter`**，由 `freegraph.observability.__all__` 导出；**不进** `freegraph.graph` 门面 | L5 既有惯例；`import freegraph` 不加载 L5 |
| 注入点 | **`compile(tracer=OtlpExporter(...))`** | 复用 B19F1 已冻结的唯一注入点；不新增 `invoke()` / `RunConfig` 字段 |
| 模式一：端点 | **`endpoint=` 显式传入**（gRPC OTLP 端点，写成 `host:port`，如 `127.0.0.1:4317`）⇒ 用官方 `encode_spans` + 官方 `TraceServiceStub`；**不用 `OTLPSpanExporter` 门面** | FR-002 的「显式传入端点」；零 env / 不重试 |
| 模式二：导出器 | **`exporter=` 显式传入**一个官方 OTel `SpanExporter` 实例（如用户自装 HTTP exporter）；此模式不接受 `headers` / `timeout` | FR-002 的「显式传入导出器」；使 HTTP-only 后端可接入 |
| 默认值 | `endpoint` / `exporter` **都无默认值**；**恰好传一个**；都不传 ⇒ 构造时 `ValueError`；两个都传 ⇒ 构造时 `ValueError` | 默认关闭；零默认端点；MUST NOT 读环境变量 |
| TLS 默认 | **`insecure: bool = False`**（默认 TLS）；仅 `endpoint=` 模式有效；本地明文示例 MUST 显式传 `insecure=True`；远程端点 MUST 保持默认 TLS | 默认安全；与官方 gRPC 传输的参数习惯一致 |
| 既有 `[otel]` | **只依赖不改**：`[otlp]` 独立；`[otel]` 仍不含 exporter | 不回溯改写 B3F1 已发布事实 |
| `current_span()` | 恒返回 `None` | 导出器是**接收端**，不是 span 生产者；不伪造上下文 |
| `on_span_start` | **no-op**（不导出未完成 span） | 只导出有 `end_time` 的完整 span |
| `on_span_end` | 仅当 `span.end_time is not None` 时执行同步导出；否则 no-op | 与 B20F1 / B20F2 的「完整行」口径一致 |

**不采用**：新增 `invoke(tracer=...)` / `RunConfig` 字段（破冻结面）；模块级自动注册 / 全局
`TracerProvider`（隐式出站）；命令行 / 环境变量自动发现端点（FR-003）。

> **导出器模式的例外**：用户可在 `exporter=` 中传入官方 `OTLPSpanExporter`（如 HTTP），
> 它是**用户侧对象**；「MUST NOT 用门面」仅约束 freegraph 的**端点模式内部实现**，
> 不禁止用户显式传入该对象。

### 3. `Span` → OTLP 映射（FR-004 / A5 / SC-007 / D-3）

**锁定映射表**（只使用 `Span` 的 11 个字段，不解析任何私有格式）：

| `Span` 字段 | OTLP 对应物 | 规则 |
|---|---|---|
| `id` | `span_id`（8 字节） | 对 `"freegraph:span:" + id` 做 SHA-256，取前 8 字节；`id` 为空 ⇒ 跳过该 span + `WARNING`，不阻断 |
| `name` | span name | 逐字映射 |
| `attributes` | span attributes | **逐键直映射**；B18F1 的 `gen_ai.*` 与失败时的 `error.type` 原样保留，**不增删、不改名**；`error.type` 存在时**同时**把 OTel status 置为 `ERROR`（message = `error.type`），否则 `UNSET` |
| `parent` | `parent_span_id`（8 字节） | 对 `"freegraph:span:" + parent` 做同一映射；`None` / 空 ⇒ 无 parent（根 span，`parent_span_id` 为空） |
| `start_time` | `start_time_unix_nano` | 解析 UTC ISO-8601；**精度到纳秒**，MUST NOT 截断到微秒；解析失败 ⇒ 跳过该 span + `WARNING`，不阻断 |
| `end_time` | `end_time_unix_nano` | 同上；`None` ⇒ **不导出**（no-op） |
| `context` | **不导出**（v1） | 本地补充上下文，不属于 OTLP 标准语义；若要导出，MUST 在本 feature spec 单独登记映射 |
| `thread_id` | `gen_ai.conversation.id`（标准 semconv） | 仅当 `thread_id` 为 `str` 且 `Span.attributes` 中**不存在**该键时派生；已有同名键**保留原值、不覆盖**；`thread_id` 非 `str` ⇒ 不派生 + `WARNING`；不写回 `Span.attributes`；`None` ⇒ 省略 |
| `run_id` | `trace_id`（16 字节） | 对 `"freegraph:run:" + run_id` 做 SHA-256，取前 16 字节；**同一 `run_id` ⇒ 同一 trace_id**；不同 `run_id` ⇒ 不同 trace_id |
| `node` | **不新增属性** | 节点 span 的 `name` 即节点名；模型 / 工具 span 通过 `parent` 链回溯到节点 span；MUST NOT 伪造节点名 |
| `checkpoint_id` | **不导出**（v1） | 依 B14F1 D-06，本 feature **MAY** 复用但 v1 不导出；未来若导出，MUST 在本 spec 单独登记映射与偏离 |

**映射纪律**：

- **属性面**：OTLP span attributes 的键**只来自** `Span.attributes` 的逐键直映射，
  外加**唯一派生键** `gen_ai.conversation.id`（来自 `thread_id`）。**MUST NOT** 出现
  freegraph 私有前缀（如 `freegraph.*`）；**MUST NOT** 解析 `context` / `TraceRecord` /
  存储行格式。
- **值归一**：`attributes` 的值是 `str` / `bool` / `int` / `float` / `bytes` /
  同质标量序列（元素类型一致且为上述标量）时原样映射；`None` ⇒ `"null"`（JSON 字符串）；
  其它类型按 `json.dumps(value, ensure_ascii=False, sort_keys=True)` 转成字符串（失败再
  `str(value)`），**MUST NOT** 因单个值类型不支持而抛出到图执行路径。
- **身份投影**：`run_id` / `id` / `parent` 的哈希只在导出器内部用于构造 OTel 身份；
  **MUST NOT** 回写 `Span`、**MUST NOT** 要求 B18F1 增删字段。
- **`TraceRecord` 不映射**：B19F1 的 `TraceRecord` 是本地补充元数据，**不是** `Span`；
  **MUST NOT** 为其生成独立 OTLP span（B19F1 D-1）。
- **不自研编码**：freegraph 只组装官方 SDK 的 `ReadableSpan` 并交给官方
  `encode_spans` + 官方 `TraceServiceStub`；**MUST NOT** 手写 protobuf、OTLP wire
  format 或 HTTP/gRPC payload 编码；**MUST NOT** 使用 `OTLPSpanExporter` 门面
  （读 env + 内部重试）。

### 4. 默认关闭、零出站、失败隔离与同步语义（FR-002 / FR-003 / FR-005 / A4 / SC-002 / SC-003）

| 项 | 锁定值 |
|---|---|
| 默认关闭 | 不传 `tracer` ⇒ 导出路径完全不激活；不构造 `OtlpExporter` ⇒ 不 import OTel、不建连接、不产生 span |
| 零默认端点 | **无任何默认端点**；不读 `OTEL_EXPORTER_OTLP_*` / `OTEL_*` / `LANGSMITH_*` / 任何环境变量 |
| 零出站 | 只有用户显式构造 `OtlpExporter(endpoint=...)` 或传入导出器，且图实际产生完整 span 时，才向该端点出站；这是**用户显式启用**的合法出站，不计入「框架零出站」违例 |
| 同步语义 | v1 **只做同步导出**：`on_span_end` 内直接调用官方编码器 / gRPC stub 或用户 exporter；**MUST NOT** 启动后台线程 / async 任务 / batching processor；进程退出时无需额外 flush |
| 失败隔离 | 导出 / 编码 / 连接 / 超时失败 **MUST NOT** 抛出到图执行路径；失败仅被记录；**MUST NOT** 重试同一 span（v1） |
| 诊断面 | `export_errors`（计数）、`last_error`（最近一次异常对象）、可选 `on_error` 回调、`logging.WARNING` 四路可感知；`BaseException`（如 `KeyboardInterrupt` / `SystemExit`）**不被吞**，且**不调用** `on_error`（仅 `Exception` 进入诊断面） |
| 并发 | 每个 `OtlpExporter` 实例一把进程内锁串行化导出；MUST NOT 使用模块级全局锁；用户 `on_error` / 日志在锁外执行 |
| 生命周期 | 不提供 `close()` / 上下文管理器 / 公开 OTel 对象；`export_errors` / `last_error` 只读可查询 |
| 端点校验 | `endpoint` 必须是**非空 `host:port`**（MUST NOT 带 `http://` / `https://` scheme）；`insecure` 必须是 `bool` 且只能与 `endpoint=` 同用；`headers` / `timeout` 只能与 `endpoint=` 同用，与 `exporter=` 同用 ⇒ 构造时 `ValueError`；`exporter` 是官方 OTel `SpanExporter` 形状；校验在**构造时**完成，失败即 `ValueError` / `ImportError`（**显式用户错误**，不发生在图运行中） |
| 缺 extra | 传 `endpoint=` **或** `exporter=` 但未安装 `[otlp]` / OTel SDK ⇒ 构造时抛**明确 `ImportError`**（含安装提示）；**MUST NOT** 静默降级、MUST NOT 在图运行中才报错 |

### 5. 架构与依赖边界（FR-009 / SC-005 / SC-008）

| 项 | 锁定值 |
|---|---|
| 代码层 | 新增代码位于 **L5** `freegraph.observability`；只依赖标准库 + L1 `Span` + 官方 OTel（**惰性 import**） |
| import 纪律 | `import freegraph` **MUST NOT** 加载 L5 / OTel；`import freegraph.observability` **MUST NOT** 在模块导入期 import OTel；OTel 只在**显式构造 `OtlpExporter`** 时惰性 import |
| 禁止 import | `langchain` / `langchain-core` / `langsmith` / `langgraph*` 的 import 次数 **== 0**（FR-009） |
| 禁止内嵌 | Phoenix / Langfuse / OpenLIT 的代码 / 包 / 镜像 **MUST NOT** 进入 freegraph 依赖或发行包；三者只作为**外部 OTLP 后端**（FR-008 / 原则 IX） |
| 与 B20F2 解耦 | **MUST NOT** 消费 `FileTraceStore.query()` / `SqliteTraceStore.query()`；**MUST NOT** 修改 JSONL 行结构 / SQLite schema / 查询语义（B20F2 D-1） |
| 与 B14F1 解耦 | **MAY** 读取 `span.checkpoint_id`，但 v1 **不导出**；**MUST NOT** 修改 `checkpoint_id` 语义 / `MemorySaver` 存储格式（B14F1 D-06） |
| 与 B18F1 解耦 | **MUST NOT** 要求 B18F1 增删 `Span` 字段或修改属性 allowlist；映射只读 11 字段（B18F1 D-3） |
| 运行时自动性 | 运行时 **MUST NOT** 自动构造 / 调用导出器；导出器只在用户注入时存在（原则 IV「可视化不阻断执行」） |

### 6. 冻结面、依赖门禁与治理追认（MUST）

本 feature 的落地会触碰**多处既有冻结面 / 门禁规则**，MUST 按「破冻结面三条」处理
（登记 + 回溯修订 + 发起者追认），**MUST NOT** 静默改写：

| 冻结面 | 冲突 | 本 spec 的处理 | 追认 |
|---|---|---|---|
| 宪法 v1.7.0「v1.0 的 `pyproject.toml` MUST NOT 含 `[project.optional-dependencies]`」（已由 v1.17.0 修订） | 本 feature 是 **v1 / M4**，但 FR-001 要求可选 extra | **已按宪法 v1.17.0（2026-11-24 · MINOR）修订**：登记**唯一具名例外**——仅 `[otlp]` 一个 extra 进入 v1.0 发行元数据；其余四个 extra 仍归 v2.0；基础安装闭包不变；例外条件见宪法正文 | 宪法 v1.17.0 正式修订 + 发起者追认；正式文字 + 确认人 + 日期落 `harness/verification/B21F1/manual-verification.md` |
| B3F1 的 G3 extras 白名单（12 个确切包名）与 `extras-v2.toml` | `[otlp]` 闭包新增 `opentelemetry-exporter-otlp-proto-grpc` / `opentelemetry-proto` / `opentelemetry-exporter-otlp-proto-common` / `opentelemetry-exporter-otlp-common` / `googleapis-common-protos` / `protobuf` / `grpcio` 等包 | **只增不改**：更新白名单、extras 清单、G21/G23 取证对象与 `THIRD_PARTY_NOTICES`；既有 12 名逐字保留；许可证归一 `protobuf` 为 `BSD-3-Clause` | 发起者书面追认 + manual-verification |
| **B3F1 的 G23「散文式标识 MUST 失败 / MUST NOT 引入等价标识符对照表」** | `protobuf 7.36.2` 的元数据是散文式 `License: 3-Clause BSD License`（无 `License-Expression`），但其 LICENSE 文件是标准 BSD-3-Clause | **只加一条具名归一**：仅 `protobuf` + 精确字符串 `3-Clause BSD License` → `BSD-3-Clause`；**不是**通用对照表、不放开其它散文标识、不放宽白名单 | 发起者书面追认 + manual-verification |
| **B19F1 的「L5 模块禁止 import `opentelemetry`」门禁** | 可选 OTLP 导出器必须在 3 个 L5 模块中惰性 import OTel / grpc | **拆分而不删**：只允许 `_otlp_mapping.py` / `_otlp_transport.py` / `_otlp_exporter.py` 具名例外；其它 L5 模块禁令不变；新增运行时断言「`import freegraph.observability` 后 `opentelemetry` / `grpc` 不在 `sys.modules`」 | manual-verification 追认 + 门禁文档同步 |
| B3F1 的 G26 网络静态扫描例外名单（当前为空） | OTLP 传输模块是**用户显式启用**的合法出站方 | **只增** `_otlp_transport.py` 到例外名单；同时把 `grpc` 加入网络客户端扫描清单（**更严**）；MUST NOT 放宽扫描域本身；MUST NOT 把默认路径加入例外 | manual-verification 追认 |

> **不破的冻结面**：`Span` 11 字段 · `TraceSink` 3 方法 · `TraceRecord` 13 字段 ·
> `TraceQuery` 5 字段 · `RunConfig` 9 字段 · `SuperStepResult` / `PregelTask` ·
> `stream()` 事件信封 · `freegraph.graph` 门面符号面 · L1 契约 22 符号 ·
> B20F2 的查询语义 / JSONL 行结构 / SQLite schema · `compile()` 既有签名（只复用
> `tracer=` 关键字，不新增参数）。
> **唯一新增公开符号**：`freegraph.observability.OtlpExporter`。

### 7. 导出器自有常量与容错口径（FR-016 / FR-026 / SC-007 的补充）

> 本节把「不属于 `Span` 的 11 个字段、但导出器必须决定」的口径写死，避免 spec / plan /
> tasks 之间出现未登记的行为差。FR-016 的「只读取 `Span` 的 11 个字段」应理解为
> **不解析 freegraph 私有格式 / 存储行 / `TraceRecord`**；导出器使用自身常量
> （`service.name` / scope 名 / 包版本）**不构成**私有格式解析。

| 项 | 锁定值 |
|---|---|
| `Resource` | `Resource({"service.name": "freegraph"})`（**直接构造**，不用 `Resource.create`，后者读 `OTEL_RESOURCE_ATTRIBUTES` / `OTEL_SERVICE_NAME`） |
| `InstrumentationScope` | `InstrumentationScope("freegraph", freegraph.__version__)` |
| `SpanKind` | `gen_ai.operation.name` ∈ {`chat`, `execute_tool`} ⇒ `SpanKind.CLIENT`；否则 `SpanKind.INTERNAL` |
| `TraceFlags` | `TraceFlags(TraceFlags.SAMPLED)`；`is_remote=False` |
| `timeout` 默认 | `10.0` 秒；仅 `endpoint=` 模式；不读 env |
| `last_error` | 保留最近一次失败；**成功导出不清空**；无 reset API |
| `on_error` | 可选回调；在锁外调用；仅 `Exception` 触发该回调；其自身抛出的 `Exception` 被捕获并 `WARNING`，原错误保留为 `last_error`；`BaseException` 不调用 `on_error` 且继续传播 |
| `end < start` | 钳到 `start` + `WARNING`（保留 span，不丢弃） |
| 非 `str` attribute 键 | 跳过该键 + `WARNING`；span 仍导出 |
| `SpanExportResult.FAILURE` | 视为失败；合成 `RuntimeError("SpanExporter.export returned FAILURE")` 记诊断 |
| 传输 channel | 端点模式每次导出创建短生命周期 channel，`finally` 关闭；不缓存、不暴露 |
| `service.name` 自定义 | v1 **不提供** `resource_attributes` 参数；未来若需要，走新 feature |

---

## Clarifications

### Session 2026-11-24（spec 阶段写死 + clarify 轮 · plan 不得再翻）

- Q: 可选 extra 叫什么、装什么？ → A: **新增 `[otlp]`**，装 `opentelemetry-api` +
  `opentelemetry-sdk` + **`opentelemetry-exporter-otlp-proto-grpc`**；**不修改** `[otel]`，
  **不含** `opentelemetry-exporter-otlp` 元包 / HTTP exporter / `requests` / `certifi`。
  理由：只有 gRPC 协议路径能同时满足「官方 OTLP 编码器 / 协议实现复用」与许可证白名单；HTTP-only 后端
  由用户自装官方 HTTP exporter 并以 `exporter=` 模式接入。
- Q: 导出的触发方式是什么？ → A: **`compile(tracer=OtlpExporter(...))`**；不新增
  `invoke()` / `RunConfig` 字段；不自动注册全局 provider；不读环境变量。
- Q: 端点 / 导出器如何传入？ → A: **二选一且必须恰好传一个**：`endpoint=`（gRPC）或
  `exporter=`（官方 OTel `SpanExporter` 实例）；都不传或都传 ⇒ 构造时 `ValueError`；
  无默认端点。
- Q: 导出的时间语义与并发语义？ → A: **v1 同步导出**，只导出有 `end_time` 的完整 span；
  **不做** async / 后台线程 / batching；每实例一把进程内锁。
- Q: 导出失败怎么处理？ → A: **不阻断图执行**；四路诊断（`export_errors` / `last_error` /
  `on_error` / `WARNING`）；`BaseException` 不吞；不重试。
- Q: `TraceRecord` / `context` / `checkpoint_id` 是否导出？ → A: **不导出**（v1）。
  `TraceRecord` 不是 `Span`；`context` 是本地补充；`checkpoint_id` 依 B14F1 D-06 仅 MAY 复用。
  它们都不改变 `Span` 字段面。
- Q: `thread_id` / `node` / `run_id` 如何进入 OTLP？ → A: `run_id` ⇒ `trace_id`（稳定哈希）；
  `thread_id` 非空 ⇒ 派生标准 semconv 属性 `gen_ai.conversation.id`；`node` **不新增属性**
  （节点 span 的 `name` 即节点名，子 span 经 `parent` 链回溯）。MUST NOT 出现私有前缀属性。
- Q: 许可证合规怎么解决？ → A: 只用 gRPC 协议实现避开 `certifi`；`protobuf` 的散文标识
  `3-Clause BSD License` 经**权威 SPDX 归一**为 `BSD-3-Clause`；**不放宽**白名单。
- Q: 三个示例如何分工？ → A: **Phoenix** 用 `endpoint=`（gRPC 4317）；**OpenLIT / Langfuse**
  用 `exporter=`（用户自装官方 HTTP exporter）；每个示例接受显式端点参数，不内置默认端点。
- Q: 是否消费 B20F2 的查询 API？ → A: **否**。本 feature 只导出 B18F1 的 `Span`；
  查询 API 与 OTLP 导出是两个能力面（B20F2 D-1 / D-2）。
- Q: 是否需要上浮 +2 人日？ → A: **否**。映射可行，复用官方 OTLP 编码器 / gRPC stubs；无自研编码。
  若实测推翻该前提 ⇒ 按 §7.5 立即上浮并回写结论。
- Q: 是否允许为 `[otlp]` 在 v1.0 开「仅此一个 extra 进入发行元数据」的窄例外？ →
  A: **允许**。发起者 2026-11-24 选择 A：仅 `[otlp]` 进入 v1.0 发行元数据，其他 extra
  仍归 v2.0，基础安装闭包不变；正式追认文字 + 确认人 + 日期落
  `harness/verification/B21F1/manual-verification.md`。
- Q: OpenLIT 与 Langfuse 都能诊断智能体、功能重叠，怎么处理？ →
  A: **三个示例并列保留、不设默认推荐后端**（发起者 2026-11-24 选择 A）。文档 MUST
  增加「能力分工 / 重叠说明」表：freegraph 负责**本地运行时诊断**（图视图、状态快照、
  checkpoint / time-travel、交互式调试），OpenLIT / Langfuse / Phoenix 负责**外部
  trace 浏览 / 分析 / 评测 / Prompt 管理**；重叠是**分层互补**，不是替代关系。
  三个示例 MUST 导出**同一份标准 OTLP 数据**，MUST NOT 为不同后端写不同映射 / 分支；
  MUST NOT 使用「官方推荐 / 默认后端」措辞。
- Q: `[otlp]` 用官方元包还是只走 gRPC 协议实现？ →
  A: **只走 gRPC 协议实现**（发起者 2026-11-24 选择 A）：`[otlp]` 声明
  `opentelemetry-exporter-otlp-proto-grpc`，避开 `certifi`/MPL-2.0；OpenLIT / Langfuse
  等 HTTP-only 后端由用户自装官方 HTTP exporter，以 `exporter=` 接入；freegraph 依赖
  闭包保持白名单。
- Q: `endpoint=` 模式的 gRPC TLS 怎么决定？ →
  A: **显式 `insecure: bool`，默认 `False`（TLS）**（发起者 2026-11-24 选择 B）。
  `endpoint` 写成 `host:port`，不带 URL scheme；本地明文示例显式传 `insecure=True`；
  远程端点保持默认 TLS；`insecure` 与 `exporter=` 同用 ⇒ 构造时 `ValueError`；
  MUST NOT 按 URL scheme 推断、MUST NOT 读环境变量。
- Q: `thread_id` / `node` / `checkpoint_id` / `context` 这些非 `attributes` 字段怎么映射？ →
  A: **保守映射**（发起者 2026-11-24 选择 A）：`thread_id` 非空 ⇒ 派生标准 semconv
  属性 `gen_ai.conversation.id`；`node` 不新增属性（节点 span 的 `name` 即节点名，
  模型 / 工具 span 经 `parent` 链回溯）；`checkpoint_id` / `context` v1 不导出。
  MUST NOT 出现 `freegraph.*` 私有前缀；未来若要导出，MUST 在本 spec 单独登记映射与偏离。
- Q: 三个后端示例的「冒烟」验收做到什么程度？ →
  A: **至少一个真实后端冒烟 + 其余用桩接收端**（发起者 2026-11-24 选择 C）。三个示例
  MUST 都有可运行记录；至少一个 MUST 对真实后端（优先部署最轻的 Phoenix / OpenLIT）
  完成一次真实导出；其余 MAY 用最小 OTLP 接收端 / 桩接收端验证。若真实后端环境确实
  不可得，manual-verification MUST 写明原因、替代证据（桩接收端）与待补验证项，并由
  发起者追认，**MUST NOT** 静默降级。

### Session 2026-11-24（analyze 轮补 · 与上节同等效力）

- Q: 三个示例的 `--help` 与 HTTP exporter 用户侧依赖如何对齐？ → A: **延迟导入**：
  OpenLIT / Langfuse 在 `argparse` 解析完成、确认执行导出后再导入用户侧 HTTP exporter；
  `--help` MUST NOT 触发该导入；缺包时打印安装提示并以非零退出码结束。
- Q: `exporter=` 模式下 `headers` / `timeout` 与缺少 OTel SDK 如何处理？ → A:
  **构造时显式报错**：`headers` / `timeout` 仅端点模式有效，与 `exporter=` 同用 ⇒
  `ValueError`；缺 `[otlp]` / OTel SDK 且传 `endpoint=` 或 `exporter=` ⇒ 构造时
  `ImportError`（含安装提示）。
- Q: 属性值归一与 `thread_id` 优先级以谁为准？ → A: **统一为本 spec / contracts 的同一口径**：
  `bytes` 原样、`None` ⇒ `"null"`；`gen_ai.conversation.id` 仅在 `thread_id` 为 `str`
  且属性中不存在时派生，已有同名键保留原值。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 接进我现有的 OTel 栈 (Priority: P1)

作为用户，我已有 Phoenix / OpenLIT / Grafana 等 OTel 栈；我希望把 freegraph 的 span
导出到那里，与既有系统统一观测。

**Why this priority**: 这是宪法原则 IV「后端对接政策」的直接落地，也是本 feature 的
最小价值切片。没有它，feature 不成立。

**Independent Test**: 启动一个最小 OTLP 接收端（gRPC），显式传入端点构造
`OtlpExporter`，编译并运行一个两节点图；断言接收端收到该次运行的节点 span 及全部
`gen_ai.*` 属性，且图结果不受影响。

**Acceptance Scenarios**:

1. **Given** 已安装 `[otlp]` 且有一个可达的 OTLP 接收端，**When** 用户显式传入
   `endpoint=` 并把 `OtlpExporter` 作为 `tracer` 注入，运行图，**Then** 接收端收到
   每个完整 span 的 name / 时间 / attributes / 父子关系，且图返回预期的最终状态。
2. **Given** 一次运行包含节点 span 与其内部的模型 / 工具 span，**When** 导出，
   **Then** 模型 / 工具 span 的 `parent` 指向节点 span，三者的 `trace_id` 相同
   （同一 `run_id`）。
3. **Given** 模型 / 工具 span 失败（`attributes` 含 `error.type`），**When** 导出，
   **Then** 该 span 的 OTLP status 为 `ERROR`，且 `error.type` 属性原样保留。

---

### User Story 2 - 不导出时零负担 (Priority: P1)

作为用户，我不用 OTel 时，希望完全不受影响：不装 extra、不出站、不报错、不加载额外模块。

**Why this priority**: 「零依赖 / 零出站 / 零账号」是本项目的产品承诺；导出能力不得
反过来污染默认路径。

**Independent Test**: 在**未安装** `[otlp]` 的基础安装环境里，不传 `tracer` 运行图；
断言图正常完成、`sys.modules` 无 `opentelemetry.*`、socket 监测夹具「框架出站 == 0」、
无新增依赖。

**Acceptance Scenarios**:

1. **Given** 基础安装（无 `[otlp]`），**When** 运行图且不传 `tracer`，**Then** 图正常完成，
   无任何导出 / 连接 / OTel import。
2. **Given** 已安装 `[otlp]`，**When** 用户不构造 `OtlpExporter`、不传 `tracer`，
   **Then** 导出路径完全不激活，行为与基础安装一致。
3. **Given** 环境中设置了 `OTEL_EXPORTER_OTLP_ENDPOINT` / `OTEL_*` / `LANGSMITH_*`，
   **When** 运行图，**Then** freegraph 不读取这些变量、不因此出站、行为不变。

---

### User Story 3 - 导出失败不阻断运行 (Priority: P1)

作为用户，后端挂了 / 端点不可达，我的图必须照常跑完。

**Why this priority**: 宪法原则 IV：可视化层 MUST NOT 阻断执行。导出是可选增强，
不能成为运行的单点故障。

**Independent Test**: 显式传入一个不可达端点，运行图；断言图返回正确结果、无异常抛出、
`export_errors > 0`、`last_error` 非空、日志有警告。

**Acceptance Scenarios**:

1. **Given** 端点不可达，**When** 运行图，**Then** 图成功完成，导出失败只被记录。
2. **Given** 导出过程中抛出任意 `Exception`，**When** 继续运行后续节点，**Then**
   后续节点照常执行，最终状态与不导出时逐字相等。
3. **Given** 导出器收到 `KeyboardInterrupt` / `SystemExit`，**When** 发生，**Then**
   该 `BaseException` 不被吞掉（与 `Exception` 隔离口径区分）。

---

### User Story 4 - 三个后端的最小对接示例 (Priority: P2)

作为用户，我希望有可直接复制运行的 OpenLIT / Langfuse / Phoenix 示例，知道端点、
认证方式和前置安装。

**Why this priority**: FR-006 的交付物；示例是把「协议能力」变成「用户可接入」的桥梁。

**Independent Test**: 三个示例文件存在；各自在文档给出的前置条件下可运行，并至少完成
一次导出（用最小接收端或真实后端冒烟）。

**Acceptance Scenarios**:

1. **Given** 用户按示例文档启动 Phoenix，**When** 运行 Phoenix 示例，**Then** span 出现在
   Phoenix 中（或最小接收端收到等价数据）。
2. **Given** 用户按示例文档安装官方 HTTP exporter 并启动 Langfuse，**When** 运行 Langfuse 示例，
   **Then** span 被导出到 Langfuse 的 OTLP 端点。
3. **Given** 用户按示例文档启动 OpenLIT，**When** 运行 OpenLIT 示例，**Then** span 被导出；
   文档明确写明「旧路径 `openlit.io/docs` 404、现行文档 `https://docs.openlit.io/latest/overview`、
   仓库 README 可作回退」与 as-of 日期。
4. **Given** 三个示例都存在，**When** 执行验收，**Then** 至少一个示例对真实后端完成
   真实导出冒烟，其余示例至少有桩接收端 / 最小接收端的可运行记录。

---

### User Story 5 - 标准化而非私有格式 (Priority: P2)

作为用户 / 生态维护者，我希望 freegraph 只以标准 OTLP 输出，不自造私有编码，也不内嵌
任何后端。

**Why this priority**: 这是「可导出到任一 OTel 后端」的前提；私有编码会让生态对接
重新变成一对一适配。

**Independent Test**: 代码审查 + AST / 静态扫描确认无自研 protobuf / OTLP 编码；
依赖声明确认无 Phoenix / Langfuse / OpenLIT / langchain / langsmith；导出数据可被
任意符合 OTLP 的接收端解析。

**Acceptance Scenarios**:

1. **Given** 导出实现，**When** 审查源码与依赖，**Then** 无 protobuf 编码器 / 手写 wire format，
   仅有官方 SDK 数据对象组装与官方编码器 / gRPC stub 调用。
2. **Given** freegraph 发行包与依赖，**When** 检查，**Then** 无 Phoenix / Langfuse / OpenLIT
   的代码或包；三者只出现在示例文档中作为外部后端。

---

### Edge Cases

- **未安装 `[otlp]` 却显式传 `endpoint=`**：构造时抛明确 `ImportError`（含安装提示），
  不静默降级、不在图运行中才报错。
- **`endpoint` 与 `exporter` 都不传 / 都传**：构造时 `ValueError`。
- **`endpoint` 为空串 / 不是 `host:port` / 带 `http://` 或 `https://` scheme**：
  构造时 `ValueError`；不尝试连接。明文本地连接 MUST 用 `insecure=True`，不得靠 URL
  scheme 推断。
- **`insecure=True` 与 `exporter=` 同用**：构造时 `ValueError`；TLS 由用户传入的导出器
  自行负责。
- **端点不可达 / DNS 失败 / 超时**：导出失败被隔离，图成功；`export_errors` 增加，
  `last_error` 记录；不重试。
- **`on_span_start` 收到的未完成 span**：no-op，不导出。
- **`end_time` 为 `None` 的 span**：不导出，无异常。
- **`start_time` / `end_time` 无法解析**：跳过该 span + `WARNING`，不阻断其它 span 与图执行。
- **`end_time < start_time`**：钳到 `start_time` + `WARNING`（保留 span，不丢弃）。
- **`id` 为空 / `run_id` 为空**：`id` 为空 ⇒ 跳过 + `WARNING`；`run_id` 为空在 B18F1
  不应出现，导出器按「无法构造 trace_id」跳过 + `WARNING`，不回写 / 不抛到运行路径。
- **`parent` 指向不存在或为空的 span**：按根 span（全零 parent）导出，不抛错。
- **`attributes` 含嵌套 dict / list / 自定义对象**：按值归一规则转字符串，不抛错；
  图中执行不受影响。
- **`attributes` 含非 `str` 键**：跳过该键 + `WARNING`；span 仍可导出，不抛到运行路径。
- **`attributes` 含非 ASCII / 换行 / 控制字符**：原样保留，由 exporter 编码；不截断。
- **同一 `run_id` 的多个 span**：共享同一 `trace_id`；不同 `run_id` 不共享。
- **同一 `id` 被重复导出**：按调用次数导出，不去重（幂等性由用户 / 后端负责）。
- **并发节点同时结束 span**：每实例锁串行化导出；不损坏 exporter 内部状态；图结果不变。
- **导出器回调中抛 `Exception`**：被四路诊断捕获；`BaseException` 不吞。
- **用户 `SpanExporter.export` 返回 `SpanExportResult.FAILURE`**：视为失败；合成
  `RuntimeError("SpanExporter.export returned FAILURE")` 记诊断；不阻断图执行。
- **用户自装 HTTP exporter 传给 `exporter=`**：freegraph 不检查 / 不读取其内部配置；
  端点 / 认证由用户对象决定；freegraph 仍不读环境变量。
- **后端只支持 HTTP（如 Langfuse）**：用 `exporter=` 模式；文档要求用户自行安装官方
  HTTP exporter，该包不进入 freegraph 依赖闭包。
- **OpenLIT 旧文档路径 404 / 文档迁移 / OTel 后端 API 变更**：示例可能失效；文档 MUST
  写明旧路径 404、现行文档 URL、仓库 README 回退与 as-of 日期，不阻塞核心验收。
- **真实后端环境不可得（Docker / 服务启动失败 / 网络受限）**：至少一个真实后端冒烟
  无法完成 ⇒ 用最小接收端 / 桩接收端证据代替，manual-verification MUST 写明原因、
  替代证据与待补验证项，并由发起者追认；MUST NOT 静默降级或把桩接收端写成「已接真实后端」。
- **用户设置 `OTEL_EXPORTER_OTLP_*`**：freegraph 忽略；只有显式参数生效。
- **`TraceRecord` 被推送**：导出器不实现 `on_trace_record` / 不为其生成 OTLP span；
  B19F1 的可选回调行为保持不变。
- **图运行未产生任何 span**：不导出、不出站、不报错。
- **导出失败后继续运行更多节点**：后续导出仍尝试（不熔断），失败继续隔离。
- **进程提前退出**：同步导出已完成，无后台线程 / 无未 flush 数据。

---

## Upstream Parity *(mandatory — 宪法 v1.12.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11** / `langchain-core` **1.7.6** / `langsmith` **0.14.17**（取证于 2026-11-21，本仓库 `.venv` 实际安装版本；沿用 B19F1 / B20F1 / B20F2 的版本钉住口径）

> **口径说明**：上游 `langgraph` 内核**没有**内建 OTLP exporter，也**没有** freegraph
> 这样的「自有 `Span` + 可选 OTLP 导出器」。上游的可观测出口是 LangSmith SaaS
> （`langsmith` 客户端 / callback handler），默认关闭，开启后经 HTTP 上报远端；
> OTel 接入依赖外部 instrumentor / 用户自行桥接。因此本 feature 的主体落在
> 原则 XI 的**必须自研区 ③（上游没有的能力）**与**①（零账号 / 零主动出站 / 零依赖）**；
> 只有「失败隔离」「默认关闭」「成对生命周期」几类**行为面**可与上游对齐。

### §1 逐条对照（P-01…P-07）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| **P-01** | **OTLP 导出能力** | 上游内核无 OTLP exporter；可观测出口是 LangSmith `langsmith/client.py:139`（httpx 客户端）· `:619`（默认 `https://api.smith.langchain.com`）· `langsmith/_internal/_background_thread.py:377`（批量 ingest） | 可选 `[otlp]` extra + `OtlpExporter`，以标准 OTLP 导出到用户显式端点；无账号、无默认远端 | **DIFF**（自研区 ③：上游没有的能力） | 宪法原则 IV「MUST 以 OTLP 等标准协议输出」；上游对应物是私有 SaaS，引入即破零依赖 / 零账号 |
| **P-02** | **默认关闭 / 环境变量** | `langchain_core/tracers/context.py:114-120`（只有启用 tracing 才构造 tracer）· `langsmith/utils.py:119-144`（`LANGSMITH_*` 环境变量可影响开关） | 不注入 `OtlpExporter` ⇒ 零导出 / 零 import / 零连接；不读 `OTEL_*` / `LANGSMITH_*` / 任何 env | **SAME**（默认关闭）· **STRICTER**（不读 env） | 宪法原则 I / IV；「端点存在即自动开启」是上游的反面教材 |
| **P-03** | **失败隔离** | `langchain_core/callbacks/manager.py:351-354`（handler 异常被捕获并记警告） | 导出失败被四路诊断隔离；图结果不受影响；`BaseException` 不吞 | **SAME**（隔离语义）· **STRICTER**（可感知面） | 宪法原则 IV；静默吞错会让用户误以为已导出 |
| **P-04** | **标准协议 vs 私有格式** | 上游上报 LangSmith run tree（私有 schema）；OTel 需外部桥接 | 自有 `Span` 逐字段映射为官方 OTel SDK 数据对象，再由官方编码器编码为 OTLP | **DIFF** | 自研区 ①③；标准协议是可导出到任一后端的前提 |
| **P-05** | **属性命名** | 上游 run tree 的 inputs / outputs / extra；无 `gen_ai.*` 约束 | `Span.attributes` 逐键直映射（B18F1 的 `gen_ai.*` + `error.type`）；派生 `gen_ai.conversation.id`；无私有前缀 | **DIFF**（表示层）· **STRICTER**（属性面收窄到 B18F1 allowlist） | 宪法原则 IV「SHOULD 对齐 OTel GenAI semconv」；B18F1 D-3 要求 1:1 |
| **P-06** | **成对生命周期** | `langchain_core/tracers/base.py:261`（on_chain_start）/ `:306`（on_chain_end） | `on_span_start` no-op / `on_span_end` 仅导出完整 span；开始 / 结束按 `id` 成对 | **SAME**（行为面）· **DIFF**（表示） | 导出只发生在结束时；与 B18F1 / B19F1 的生命周期一致 |
| **P-07** | **运行时依赖闭包** | `langchain-core 1.7.6` 的 `Requires-Dist` 含 `langsmith<1.0.0,>=0.14.9`（+ `certifi` / `httpx` / `pydantic` 等）· B18F1 实测 **E-4** | 基础安装闭包**为空集**；`[otlp]` 只含白名单包；无 `langchain*` / `langsmith` / `langgraph*` | **STRICTER** | 宪法原则 I / II / IX；产品承诺 |

### §2 实测基线（沿用 B19F1 / B20F1 · 取证于 2026-11-21）

| # | 实验 | 结果 |
|---|---|---|
| **E-1** | 两节点线性图 `a → b`，`invoke()`，不传 callbacks / tracer，环境变量全清 | 正常返回；**无任何**回调 / span / 出站（默认关闭） |
| **E-2** | 同图，传入自定义 `BaseCallbackHandler` | 共 6 条 handler 事件；callback 驱动的图节点内 `get_current_run_tree()` 为 `None` |
| **E-3** | `boom` 节点抛 `RuntimeError`，传入自定义 handler | 异常原样抛出；run 生命周期仍完成（`on_chain_error`） |

> **实测来源**：B19F1 spec §2 的 `/tmp/b19_upstream_probe.py`（2026-11-21 实跑）。
> 本 feature **不新增**上游行为断言；P-01 / P-04 / P-05 / P-07 的「上游无内建 OTLP /
> 私有 run tree / 依赖闭包」取证于**上游源码阅读**与 `.venv` 实际安装版本，仅用于说明
> 能力缺失与表示差异，**不**作为本 feature 的差分行为断言（P-02 / P-03 / P-06 的
> 默认关闭 / 隔离 / 成对生命周期由 E-1 / E-3 与 B19F1 实测支撑）。

### §3 差分场景组 *(mandatory)*

> 编号段 **D-601…D-608**（避开 B18F1 的 D-201…D-208、B19F1 的 D-301…D-310、
> B20F1 的 D-401…D-408、B20F2 的 D-501…D-508）。

| # | 场景 | 断言（结果 / 失败与否） | 判词 |
|---|---|---|---|
| **D-601** | 标准协议导出 vs 上游私有上报 | freegraph：最小 OTLP 接收端可解析并收到 span；上游：上报 LangSmith 私有 run tree，需账号 | DIFF（P-01 / P-04） |
| **D-602** | 默认关闭 | 两侧不启用时都正常完成；freegraph 额外断言 OTel import == 0 / 出站 == 0 | SAME（默认关闭）· STRICTER（零 import） |
| **D-603** | 环境变量 | freegraph：设置 `OTEL_*` / `LANGSMITH_*` 不改变导出行为；上游：`LANGSMITH_*` 可影响开关 | STRICTER（P-02） |
| **D-604** | 失败隔离 | freegraph：端点不可达图仍成功；上游：callback handler 异常被捕获 | SAME（隔离）· STRICTER（诊断） |
| **D-605** | 成对生命周期 | freegraph：每个完整 span 一次导出；上游：成对 callback run | SAME（行为面）· DIFF（表示，P-06） |
| **D-606** | 属性映射 | freegraph：`Span.attributes` 逐键直映射；上游：run tree inputs / outputs / extra | DIFF（P-05） |
| **D-607** | 依赖闭包 | freegraph 基础闭包为空；`[otlp]` 仅白名单包；上游闭包含 `langsmith` / `httpx` / `certifi` 等 | STRICTER（P-07） |
| **D-608** | 无自研编码 | freegraph：AST / 静态扫描无 protobuf / OTLP wire encoder；只调用官方编码器 / gRPC stubs；上游：无内建 OTLP 编码 | DIFF（自研区 ③） |

⇒ **判词分布**：**SAME 行为面 3**（D-602 默认关闭段 / D-604 隔离段 / D-605 生命周期段）+
**STRICTER 4**（D-602 零 import / D-603 / D-604 诊断面 / D-607）+ **DIFF 4**
（D-601 / D-605 表示 / D-606 / D-608）。

⇒ **证据口径**：D-601 / D-605 / D-606 / D-608 的上游侧是**能力 / 表示层说明**（源码阅读），
不是需要实测的差分行为断言；差分用例只对 freegraph 侧做可执行断言
（D-602 / D-603 / D-604 / D-607 的零 import / env / 隔离 / 依赖闭包除外）。

⇒ **落点**：`tests/differential/test_b21f1_otlp_parity.py` ⇒ **CI 的 Linux 全量档真跑**
（上游缺席即 skip · 沿用 B5F2 的「缺席即 skip」纪律）。本 feature 不与上游做逐字节
结果对比，只对齐「默认关闭 / 失败隔离 / 成对生命周期 / 零出站 / 依赖闭包」五类行为面；
标准协议导出与属性映射仅作本地语义说明（上游侧未实测，不标 SAME 行为面）。

### §4 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **DIFF**（自研区 ③：上游没有的能力） | 上游无内建 OTLP exporter、无自有 `Span` 导出协议（对应 **P-01 / P-04**） | 宪法原则 IV「MUST 以 OTLP 等标准协议输出」；上游对应物是 LangSmith SaaS，引入即破零依赖 / 零账号 | 本 feature |
| **X-2** | **STRICTER**（自研区 ①：零账号 / 零主动出站 / 零依赖） | 上游 `LANGSMITH_*` 可影响 tracing 开关；freegraph 不读任何 env（对应 **P-02** 的 STRICTER 半段） | 宪法原则 I；端点只认显式参数 | 本 feature |
| **X-3** | **SAME + STRICTER**（隔离语义 SAME；可感知面更严） | 导出失败隔离；上游 handler 异常被捕获（对应 **P-03**） | 宪法原则 IV；静默吞错会让用户误以为已导出 | 本 feature |
| **X-4** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 标准 OTLP span vs 上游 LangSmith run tree（对应 **P-04 / P-05 / P-06** 的表示差异） | 标准协议是可导出到任一后端的前提；属性面收窄到 B18F1 allowlist | B18F1（属性面）· 本 feature（导出） |
| **X-5** | **STRICTER**（自研区 ①：零依赖） | 基础安装闭包为空；`[otlp]` 仅白名单包；上游闭包含 `langsmith` / `httpx` / `certifi`（对应 **P-07**） | 宪法原则 IX；产品承诺 | 本 feature |

### §5 破冻结面的回溯修订清单 *(本 feature 触发)*

> 本 feature **不改写**已发布的 B18F1 / B19F1 / B20F1 / B20F2 事实，只做**增量接线**
> 与**必要的清单扩充**。完整治理条目见「形态锁定裁定 §6」。

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| 宪法 v1.7.0「v1.0 无 `[project.optional-dependencies]`」（已由 v1.17.0 修订） | `.specify/memory/constitution.md` 相关段落 + `pyproject.toml` | **唯一具名例外**：仅 `[otlp]`；其它四个 extra 仍归 v2.0；基础安装闭包不变 | 宪法 v1.17.0 正式修订 + 发起者追认 + manual-verification |
| B3F1 的 G3 extras 白名单 / `extras-v2.toml` | `tests/contracts/test_architecture.py` 白名单 + `specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml` + 门禁取证对象 | **只增不改**：新增 `[otlp]` 闭包包名；既有 12 名逐字保留；`protobuf` 归一为 `BSD-3-Clause` | 发起者书面追认 + manual-verification |
| B3F1 的 G26 网络静态扫描例外名单 | 对应门禁脚本的显式名单 | **只增** OTLP exporter 模块路径；MUST NOT 放宽扫描域 | manual-verification |
| `freegraph.observability.__all__` 的精确集合断言 | `tests/facade/test_api_snapshot.py` / L5 快照 | **只增** `OtlpExporter`；既有符号逐字保留 | manual-verification |

---

## Requirements *(mandatory)*

### Functional Requirements

#### A. 可选 extra 与依赖 / 许可证

- **FR-001**：系统 MUST 提供可选 extra **`[otlp]`**；其依赖 MUST 为
  `opentelemetry-api` + `opentelemetry-sdk` + **`opentelemetry-exporter-otlp-proto-grpc`**
  （官方 OTLP gRPC 协议实现）；基础安装 MUST NOT 引入它，`dependencies` MUST 保持为空集。
  **MUST NOT** 修改既有 `[otel]` 的依赖内容。
- **FR-002**：`[otlp]` MUST NOT 声明 `opentelemetry-exporter-otlp` 元包、
  `opentelemetry-exporter-otlp-proto-http`、`requests` 或 `certifi`；HTTP-only 后端
  由用户自行安装官方 HTTP exporter，并以 `exporter=` 模式接入。
- **FR-003**：`[otlp]` 的依赖闭包 MUST 逐包满足许可证白名单
  {MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, PSF-2.0}；`protobuf` 的散文标识
  `3-Clause BSD License` MUST 经**权威 SPDX 归一**为 `BSD-3-Clause`（依据其 LICENSE），
  **MUST NOT** 放宽白名单或加入 MPL-2.0。
- **FR-004**：交付物 MUST 更新 `THIRD_PARTY_NOTICES` 与 extras 清单 / G3 白名单 /
  G26 例外名单；更新 MUST 为**只增不改**（既有条目逐字保留）。
- **FR-005**：`[otlp]` 的版本范围 MUST 与 `opentelemetry-api` / `opentelemetry-sdk`
  兼容；具体下限归 plan，但 MUST NOT 引入黑名单包（`langchain*` / `langsmith` /
  `langgraph*` / `deepagents` / provider 包）。

#### B. 默认关闭、显式启用与零出站

- **FR-006**：导出 MUST **默认关闭**；不注入 `OtlpExporter` / 不传 `tracer` 时，
  MUST NOT 构造导出器、MUST NOT import OTel、MUST NOT 建立连接、MUST NOT 出站。
- **FR-007**：导出 MUST 只在用户**显式传入端点或导出器**时生效；`OtlpExporter`
  的 `endpoint` 与 `exporter` **都无默认值**，且 MUST 恰好传一个；两者都不传或都传
  ⇒ 构造时 `ValueError`。`endpoint` MUST 是 **`host:port`**（不带 URL scheme）；
  `insecure: bool` MUST 默认 `False`（TLS），仅 `endpoint=` 模式有效；本地明文示例
  MUST 显式传 `insecure=True`；`insecure` 与 `exporter=` 同用 ⇒ 构造时 `ValueError`。
  `headers` / `timeout` MUST 仅与 `endpoint=` 同用；与 `exporter=` 同用 ⇒ 构造时 `ValueError`。
- **FR-008**：系统 MUST NOT 读取任何环境变量来推断端点 / 开关 / 认证
  （包括 `OTEL_EXPORTER_OTLP_*` / `OTEL_*` / `LANGSMITH_*` / `LANGCHAIN_*`）；
  freegraph 内核 MUST NOT 读任何环境变量。
- **FR-009**：未安装 `[otlp]` / OTel SDK 而传 `endpoint=` **或** `exporter=` ⇒
  构造时 MUST 抛明确 `ImportError`（含安装提示）；MUST NOT 静默降级、
  MUST NOT 等到图运行中才报错。
- **FR-010**：只有用户显式启用且图实际产生完整 span 时才出站；该出站是
  **用户显式启用的合法出站**，不计入「框架零出站」违例；默认路径的框架出站 MUST == 0。

#### C. 公开 API、注入与生命周期

- **FR-011**：系统 MUST 提供公开符号 **`freegraph.observability.OtlpExporter`**，
  实现 `TraceSink` 的 `on_span_start` / `on_span_end` / `current_span` 三方法；
  MUST 经既有 `StateGraph.compile(*, tracer=...)` 注入；MUST NOT 新增
  `invoke()` / `stream()` / `RunConfig` 字段。
- **FR-012**：`on_span_start` MUST 为 no-op；`on_span_end` MUST 仅在
  `span.end_time is not None` 时导出；`current_span()` MUST 返回 `None`。
- **FR-013**：v1 MUST 为**同步导出**：MUST NOT 启动后台线程 / async 任务 /
  batching processor；MUST NOT 依赖进程退出时的异步 flush。
- **FR-014**：`OtlpExporter` MUST NOT 提供 `close()` / `__enter__` / `__exit__` /
  上下文管理器 / 公开 OTel 对象；对外只暴露三方法 + `export_errors` / `last_error`。
- **FR-015**：`OtlpExporter` MUST NOT 被运行时自动构造或调用；是否导出完全由用户
  注入决定。

#### D. `Span` → OTLP 映射

- **FR-016**：映射 MUST 只读取 `Span` 的 11 个字段；MUST NOT 要求 B18F1 增删字段、
  MUST NOT 解析 `context` / `TraceRecord` / 存储行格式 / 任何 freegraph 私有格式。
  导出器**自有常量**（`service.name="freegraph"` / scope 名 / 包版本）不属于私有格式解析，
  其口径见「形态锁定裁定 §7」。
- **FR-017**：`Span.attributes` MUST **逐键直映射**为 OTLP span attributes；
  B18F1 的 `gen_ai.*` 与失败时的 `error.type` MUST 原样保留（不增删、不改名）；
  MUST NOT 出现 freegraph 私有前缀属性。
- **FR-018**：`Span.id` / `Span.parent` MUST 映射为 OTLP `span_id` /
  `parent_span_id`（8 字节，稳定哈希）；`Span.run_id` MUST 映射为 `trace_id`
  （16 字节，稳定哈希）；同一 `run_id` MUST 共享同一 `trace_id`；不同 `run_id`
  MUST NOT 共享。
- **FR-019**：`Span.name` / `start_time` / `end_time` MUST 映射为 OTLP name /
  start / end；时间 MUST 保留**纳秒精度**，MUST NOT 截断到微秒；解析失败 ⇒ 跳过该
  span + `WARNING`，不阻断。
- **FR-020**：`thread_id` 为 `str` 且 `Span.attributes` 中**不存在** `gen_ai.conversation.id`
  时 MUST 派生该标准 semconv 属性；已有同名键 MUST 保留原值、不覆盖；`thread_id` 非 `str`
  ⇒ 不派生 + `WARNING`；`node` MUST NOT 派生新属性（节点 span 的 `name` 即节点名，
  子 span 经 `parent` 链回溯）；`checkpoint_id` / `context` MUST NOT 导出（v1）。
- **FR-021**：`error.type` 出现在 `Span.attributes` 时，OTLP status MUST 为 `ERROR`
  （message = `error.type`）；否则 status MUST 为 `UNSET`。
- **FR-022**：`attributes` 的值类型 MUST 按值归一规则处理：`str` / `bool` / `int` /
  `float` / `bytes` / 同质标量序列原样；`None` ⇒ `"null"`；其它类型转 JSON 字符串
  （失败再 `str`）；MUST NOT 因单个值类型不支持抛到运行路径。
- **FR-023**：`TraceRecord` MUST NOT 映射为 OTLP span；导出器 MUST NOT 实现
  `on_trace_record` 依赖（B19F1 的可选回调行为不变）。
- **FR-024**：映射 MUST 复用官方 OTel SDK 数据对象（`ReadableSpan`）+ 官方 OTLP
  编码器（`encode_spans`）+ 官方 gRPC stubs（`TraceServiceStub`）；
  MUST NOT 使用 `OTLPSpanExporter` 门面（构造期读 env + 内部重试）；
  MUST NOT 自研 protobuf / OTLP wire format / 手写 gRPC / HTTP payload 编码。

#### E. 失败隔离与诊断

- **FR-025**：导出 / 编码 / 连接 / 超时 / 用户 `exporter` 抛出的 `Exception`
  MUST 被隔离：MUST NOT 传播到图执行路径，MUST NOT 改变图结果 / 节点序列 /
  `stream()` 事件。
- **FR-026**：失败 MUST 可经四路感知：`export_errors`（计数）、`last_error`
  （最近异常对象）、可选 `on_error` 回调、`logging.WARNING`；MUST NOT 重试同一 span。
  `last_error` 成功导出后**不清空**；`on_error` 自身抛出的 `Exception` 也被隔离；
  详见「形态锁定裁定 §7」。
- **FR-027**：`BaseException`（`KeyboardInterrupt` / `SystemExit` 等）MUST NOT 被吞；
  只有 `Exception` 范围被隔离。
- **FR-028**：每个 `OtlpExporter` 实例 MUST 一把进程内锁串行化导出；MUST NOT 使用
  模块级全局锁；用户 `on_error` / 日志 MUST 在锁外执行。
- **FR-029**：并发节点同时结束时，导出器 MUST NOT 损坏内部状态；图结果 MUST 与不导出
  时逐字相等。

#### F. 后端示例与文档

- **FR-030**：系统 MUST 交付**三个并列**最小对接示例：**OpenLIT** / **Langfuse** /
  **Phoenix**；每个示例 MUST 可复制运行（在文档给出的前置条件下）。三个示例 MUST
  **并列、无默认推荐后端**；文档 MUST NOT 使用「官方推荐 / 默认后端」措辞；MUST 提供
  一张「能力分工 / 重叠说明」表，明确 freegraph 的**本地运行时诊断**（图视图、状态快照、
  checkpoint / time-travel、交互式调试）与外部后端的**trace 浏览 / 分析 / 评测 /
  Prompt 管理**是分层互补关系，重叠不构成替代。三个示例 MUST 都有可运行记录；其中
  **至少一个** MUST 对真实后端（优先 Phoenix / OpenLIT）完成一次真实导出冒烟，其余
  MAY 用最小 OTLP 接收端 / 桩接收端验证；若真实后端环境不可得，MUST 按 SC-015 写明
  原因、替代证据与待补验证项，并由发起者追认。
- **FR-031**：Phoenix 示例 MUST 用 `endpoint=`（gRPC 4317；本地明文 MUST 显式传
  `insecure=True`）；OpenLIT / Langfuse 示例 MUST 用 `exporter=`（用户自装官方 HTTP
  exporter）；每个示例 MUST 接受**显式端点参数**，MUST NOT 内置默认端点、MUST NOT
  依赖 freegraph 读 env。三个示例 MUST 导出**同一份标准 OTLP 数据**；MUST NOT 为不同
  后端写不同的映射 / 字段分支。OpenLIT / Langfuse 示例 MUST 在 `argparse` 解析完成后再
  惰性导入用户侧 HTTP exporter；`--help` MUST NOT 触发该导入；缺包时 MUST 打印安装提示
  并以非零退出码结束（不得静默降级）。
- **FR-032**：每个示例的接入方式 MUST 标注**来源与 as-of 日期**；OpenLIT 的**旧路径
  `openlit.io/docs` 404**、**现行文档 `https://docs.openlit.io/latest/overview`**、
  **仓库 README 回退** MUST 写明；OTel 后端 API 变更风险 MUST 写明。
- **FR-033**：示例 MUST NOT import `langchain` / `langchain-core` / `langsmith` /
  `langgraph*`；MUST NOT 内嵌 Phoenix / Langfuse / OpenLIT 的代码或包。
- **FR-034**：示例的 HTTP exporter 前置安装 MUST 明确标注它是**用户侧依赖**，
  **不进 freegraph 的依赖闭包**；freegraph 的 `[otlp]` 仍只含白名单包。

#### G. 边界、架构与质量门禁

- **FR-035**：新增代码 MUST 位于 **L5**；`import freegraph` MUST NOT 加载 L5 / OTel；
  OTel MUST 惰性 import（仅在显式构造 `OtlpExporter` 时）。
- **FR-036**：系统 MUST NOT import `langchain` / `langchain-core` / `langsmith` /
  `langgraph*`；基础安装第三方依赖闭包 MUST 保持为空；`[otlp]` 只含白名单包。
- **FR-037**：系统 MUST NOT 内嵌 Phoenix（Elastic-2.0）；MUST NOT 内嵌 Langfuse /
  OpenLIT；三者只作为外部 OTLP 后端出现在示例文档中（原则 IX）。
- **FR-038**：本 feature MUST NOT 消费 B20F2 的 `query()`；MUST NOT 修改查询语义 /
  JSONL 行结构 / SQLite schema；MUST NOT 要求 B20F2 提供第二套序列化（B20F2 D-1）。
- **FR-039**：本 feature MUST NOT 修改 `Span` 11 字段 / `TraceSink` 3 方法 /
  `TraceRecord` 13 字段 / `TraceQuery` 5 字段 / `RunConfig` 9 字段；MUST NOT 新增
  L1 `Protocol`；唯一新增公开符号为 `OtlpExporter`。
- **FR-040**：交付物 MUST 包含 `harness/verification/B21F1/manual-verification.md`，
  记录：显式端点导出的实测输出、最小接收端证据、未启用时零出站 / 零 import 证据、
  端点不可达时运行成功证据、三个示例冒烟证据、许可证归一证据、治理追认文字、
  **质量门禁 5 偏离声明**与发起者追认文字。
- **FR-041**：交付物 MUST 更新 README 的「可观测 / OTLP 导出」章节与
  `THIRD_PARTY_NOTICES`；MUST NOT 改动 API 兼容矩阵中与本 feature 无关的条目。

### Key Entities *(include if feature involves data)*

- **`Span`**（L1，B2F1 冻结）：11 字段的可观测事件载体；本 feature 只读，不改字段。
- **`TraceSink`**（L1，B2F1 冻结）：3 方法接收端协议；`OtlpExporter` 结构化实现它。
- **`OtlpExporter`**（L5，本 feature 新增）：可选 OTLP 导出器；实现
  `on_span_start` / `on_span_end` / `current_span`；持有官方编码器 / gRPC stub 或用户
  `SpanExporter`；暴露 `export_errors` / `last_error`。
- **`[otlp]` extra**（本 feature 新增）：可选依赖单元；gRPC 协议实现 + OTel SDK；
  基础安装不引入。
- **OTLP 接收端 / 后端**（外部，不属于 freegraph）：最小测试接收端、Phoenix、
  OpenLIT、Langfuse；只通过标准 OTLP 协议接收。
- **三个后端示例**（仓库交付物，非运行时依赖）：OpenLIT / Langfuse / Phoenix 的最小
  可运行对接示例与已知失效风险说明。
- **`TraceRecord`**（L5，B19F1）：本地补充元数据；**不是** `Span`，本 feature 不导出。
- **`TraceQuery` / `FileTraceStore.query()` / `SqliteTraceStore.query()`**（B20F2）：
  本地查询能力；本 feature **不消费**、不修改。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001（显式端点导出 · A5）**：显式传入端点并把 `OtlpExporter` 注入后，最小 OTLP
  接收端收到该次运行的**全部完整 span**；span 数 == 图产生的完整 span 数；name /
  时间 / attributes / 父子关系可校验；图最终状态与不导出时逐字相等。
- **SC-002（默认关闭 · A4）**：未安装 `[otlp]` / 未传 `tracer` 时，OTel import 次数
  **== 0**、导出调用次数 **== 0**、框架出站 **== 0**、图正常完成；设置
  `OTEL_*` / `LANGSMITH_*` 不改变行为。
- **SC-003（失败不阻断）**：端点不可达时图成功完成，异常传播次数 **== 0**，
  `export_errors > 0`、`last_error` 非空、至少一条 `WARNING`；后续节点照常执行。
- **SC-004（三个后端示例 · A2）**：三个示例文件存在且**并列、无默认推荐**；每个示例在
  文档前置条件下可运行，并至少完成一次导出；**至少一个**示例对真实后端（优先
  Phoenix / OpenLIT）完成真实导出冒烟，其余可用最小接收端 / 桩接收端；三个示例都有
  可运行记录；每个示例标注来源与 as-of 日期；文档含「能力分工 / 重叠说明」表；三个
  示例导出同一份标准 OTLP 数据，后端专属映射分支出现次数 **== 0**。
- **SC-005（依赖闭包 / 许可证 · A1）**：基础安装依赖闭包仍为空集；
  `[otlp]` 闭包逐包 ∈ 白名单；`certifi` / `requests` / `langchain*` / `langsmith` /
  `langgraph*` 出现次数 **== 0**；`protobuf` 归一为 `BSD-3-Clause`。
- **SC-006（零 env / 零默认端点）**：`OTEL_EXPORTER_OTLP_*` / `OTEL_*` /
  `LANGSMITH_*` 被读取次数 **== 0**；无显式参数时无默认端点、无连接尝试。
- **SC-007（映射正确 · A5）**：11 个 `Span` 字段按锁定映射表处理；`Span.attributes`
  逐键直映射（键集合相等）；同一 `run_id` 的 span 共享 `trace_id`；不同 `run_id`
  不共享；时间纳秒精度误差 **== 0**；`error.type` ⇒ status `ERROR`；私有前缀属性
  出现次数 **== 0**；`service.name == "freegraph"`、scope name / version 与 §7 一致；
  `SpanKind` 按 §7 的 `CLIENT` / `INTERNAL` 规则。
- **SC-008（不自研编码 · A1）**：源码 / AST / 静态扫描中 protobuf 编码器、OTLP wire
  encoder、手写 gRPC / HTTP payload 编码的出现次数 **== 0**；只调用官方编码器 / gRPC stubs。
- **SC-009（文档与风险 · A3）**：已知失效风险说明存在；OpenLIT 旧路径 404、现行
  `docs.openlit.io` URL、仓库 README 回退均写明；三个后端的来源与 as-of 日期齐全；
  无 Phoenix 内嵌；无 langchain import。
- **SC-010（人工门禁）**：`harness/verification/B21F1/manual-verification.md` 存在，
  且含**非空**的导出实测输出、零出站 / 零 import 证据、失败隔离证据、三示例冒烟证据、
  许可证归一证据、治理追认文字；由自动文档守卫核验。
- **SC-011（端点 / 导出器 / TLS 校验）**：`endpoint` / `exporter` 都不传或都传 ⇒
  `ValueError`，出站 **== 0**；`endpoint` 为空 / 非 `host:port` / 带 URL scheme ⇒
  构造时 `ValueError`；`insecure` 非 `bool` 或与 `exporter=` 同用 ⇒ 构造时 `ValueError`；
  `insecure` 默认 `False`（TLS）；未装 extra 而传 `endpoint` ⇒ 构造时明确 `ImportError`；
  合法 `exporter` 对象可正常导出。
- **SC-012（同步 / 并发）**：导出无后台线程 / async 任务；并发节点同时结束时导出器
  状态不损坏，图结果与不导出时逐字相等；进程退出无未 flush 数据。
- **SC-013（不消费查询 API / 不改记录）**：`FileTraceStore.query` /
  `SqliteTraceStore.query` 调用次数 **== 0**；JSONL 行结构 / SQLite schema /
  `TraceRecord` 字段面在改动前后逐条一致；`TraceRecord` 生成的 OTLP span 数 **== 0**。
- **SC-014（验收映射）**：A1–A5 每条都有至少一个可判定用例（见 §验收判据）。
- **SC-015（真实后端冒烟）**：在至少一个真实 OTel 后端（优先 Phoenix / OpenLIT，
  Langfuse 亦可）上完成一次人工冒烟；若真实后端环境确实不可得 ⇒ 以最小接收端 / 桩
  接收端证据代替，并在 manual-verification 中写明未验证项、原因、替代证据与待补验证项，
  由发起者追认（**MUST NOT** 静默降级）。

### 验收判据（= 立项书 §5.2 B21F1 小目标，逐条可判定）

> 小目标原文：交付物清单：① OTLP exporter（**可选 extra，基于
> `opentelemetry-exporter-otlp`，不自研 protobuf/OTLP 编码**）② **三个后端的最小对接
> 示例**（OpenLIT / Langfuse / Phoenix）③ **已知失效风险说明**（OpenLIT 文档站 404）
> ④ 默认关闭，仅用户显式传入端点时生效；可选导出到任一 OTel 后端
>
> **2026-11-24 事实更新**：提示词记录的「文档站 404」指旧路径 `openlit.io/docs`；
> 现行文档已迁至 `https://docs.openlit.io/latest/overview`（用户已核实可访问）。
> 交付物 MUST 同时写旧路径 404、现行 URL、仓库 README 回退与 as-of 日期。

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 可选 extra + 不自研 OTLP 编码 | 依赖声明核对 + 代码审查 / AST 扫描（无自研 protobuf / wire encoder）；`[otlp]` 闭包白名单 |
| A2 | 三个后端最小对接示例 | 三个示例文件存在且各有一例冒烟 |
| A3 | 已知失效风险说明 | 文档条目存在（OpenLIT 旧路径 404 + 现行文档 URL + 来源 + as-of） |
| A4 | 默认关闭，仅显式传入端点时生效 | 未传端点时零出站 / 零 import 断言通过 |
| A5 | 可导出到任一 OTel 后端 | 导出用例（最小接收端判定）+ 至少一个真实后端可选冒烟 |

---

## Dependencies & Out of Scope

### Dependencies

- **B18F1**（已交付）：`Span` 生产、`gen_ai.*` 属性 allowlist、失败时 `error.type`；
  本 feature 只读其 `Span`，逐键直映射（D-3）。
- **B19F1**（已交付）：`TraceSink` 注入点 `compile(tracer=...)`、`current_span()`、
  生命周期与失败隔离；本 feature 复用注入点，不新增字段（D-1 / D-2）。
- **B20F1 / B20F2**（已交付）：本地 trace 存储 / 查询；本 feature **不消费**查询 API，
  不改 JSONL 行结构 / SQLite schema（B20F2 D-1 / D-2）。
- **B14F1**（已交付）：`span.checkpoint_id`；本 feature **MAY** 复用但 v1 不导出，
  不改其语义 / `MemorySaver` 格式（D-06）。
- **B2F1 / C23 / C24 / DF4**：`Span` / `TraceSink` 字段面与可观测契约。
- **B3F1**：extras 划分、G3 / G21 / G23 / G26 门禁；本 feature 扩充其白名单 / 例外
  名单（需追认）。
- **官方 OTel 生态**：`opentelemetry-api` / `opentelemetry-sdk` /
  `opentelemetry-exporter-otlp-proto-grpc`；只在 `[otlp]` 中，不进基础安装。

### Out of Scope

- **本地 Agent Server / SSE 推送** —— v2 / D8。
- **前端 UI / Studio** —— v2 / B26。
- **评测 / 数据集 / Prompt Hub** —— 永不做。
- **自研 protobuf / OTLP 编码** —— 明确不采用。
- **内嵌 Phoenix / Langfuse / OpenLIT** —— 红线；只做外部后端示例。
- **自托管 trace 后端（路线 A）** —— MUST NOT 采用。
- **async / 后台线程 / batching 导出** —— v2 范围；v1 只做同步。
- **HTTP exporter 进入 freegraph 依赖** —— 由用户自装；freegraph 只提供 `exporter=`
  接入模式。
- **`TraceRecord` / `context` / `checkpoint_id` 的 OTLP 映射** —— v1 不做；未来需
  在本 spec 单独登记。
- **消费 B20F2 查询 API** —— 明确不做；OTLP 导出与本地查询是两个能力面。
- **在 v1.0 引入 `[otlp]` 之外的其它 extra** —— 仍归 v2.0。

---

## 质量门禁偏离（2026-11-24 · 沿用 B20F1 / B20F2 先例 · 已追认）

### 质量门禁 5 · 真实模型轮

| 项 | 内容 |
|---|---|
| 被偏离门禁 | 质量门禁 5「人工验证记录，含真实模型一轮」 |
| 根因 | B21F1 是 **L5 OTLP 导出层**；验收对象是映射正确性、默认关闭、失败隔离、许可证合规与后端示例可用性。真实模型轮不产生本 feature 的新判据，反而引入 provider 依赖。**沿用 B20F1 / B20F2 的同一偏离口径**；判据未放宽。 |
| 判据未放宽 | 本地图 + fake 模型 + 最小 OTLP 接收端的轮次照常执行；导出、默认关闭、零出站、失败隔离、三示例、许可证、治理追认等判据**一字未改**；人工记录五段式照常。 |
| 承接方 / 机制 | **B25F1（M4 · 双跑验收）**：在 B25F1 的人工验收中补真实模型轮（含 OTLP 导出证据）；承接条款 MUST 写入 `harness/features/B25F1_双跑验收与迁移说明.md` 的「下游承接（B21F1）」，并由 B21F1 tasks 的守卫断言核验。B21F1 只交付 fake / 最小接收端轮证据；真实后端冒烟按 SC-015 可选。 |
| 追认 | **已由发起者于 2026-11-24 书面追认**（确认人：发起者本人；见 `harness/verification/B21F1/manual-verification.md` §4.2）。真实模型轮由 **B25F1** 承接。 |

> **先例**：B19F1 / B20F1 / B20F2 已按同一口径登记「fake / 本地轮 + 真实模型轮由
> 后续 feature 承接」；本偏离**不降低**任何红线判据，也不改变 B21F1 的 A1–A5 验收。
> **未完成 B25F1 接线守卫前，本偏离不得视为已有效承接。**

---

## Assumptions

- **权威顺序**：宪法 > 立项书 > feature 提示词初稿 > 仓库现状。本 spec 在提示词与
  B3F1 既有决定冲突处，取**不违反宪法白名单**的解法（gRPC-only + SPDX 归一），并登记偏差。
- **`Span` 字段面已冻结**：11 字段由 B2F1 冻结；本 feature 不增删、不改语义。
- **属性面已收窄**：B18F1 v1 只写 `gen_ai.operation.name` / `gen_ai.request.model` /
  `gen_ai.tool.name` / `gen_ai.tool.call.id` + 失败时的 `error.type`；导出器逐键直映射，
  不补全未采集的属性。
- **`run_id` 是 trace 分组键**：同一 `run_id` 视为同一 trace；哈希只用于构造 OTel 身份，
  不回写字段。
- **同步导出可接受**：v1 面向本地诊断与示例；单次运行 span 数有限；同步导出使失败
  隔离与 CI 断言可确定。async / batching 留待 v2。
- **HTTP-only 后端由用户自装 exporter**：freegraph 的合规 extra 只含 gRPC 路径；
  Langfuse / OpenLIT 的 HTTP 接入以 `exporter=` 模式完成，前置安装由文档说明。
- **许可证归一可接受**：`protobuf` 的 LICENSE 是 BSD-3-Clause；把散文标识归一为
  SPDX `BSD-3-Clause` 是**证据规范化**，不是放宽白名单。
- **治理追认是合入前提**：v1.0 的 `[otlp]` 具名例外已按**宪法 v1.17.0（2026-11-24 ·
  MINOR）**正式修订；G3 白名单扩充、G23 `protobuf` 归一、G26 / B19F1 import 例外仍 MUST
  获发起者书面追认；未追认前不得合入，也不得改走自研编码。
- **三个示例的环境**：用户已有对应后端（Phoenix / OpenLIT / Langfuse）或可启动
  最小接收端；示例只承诺「在文档前置条件下可运行」，不承诺后端版本长期兼容。
- **OpenLIT 文档路径迁移**：据 Q6 报告（取证于 2026-11-03），旧路径 `openlit.io/docs`
  返回 404；**2026-11-24 用户核实现行文档 `https://docs.openlit.io/latest/overview` 可访问**。
  本 feature 示例 MUST 标注旧路径 404、现行文档 URL、仓库 README 回退与 as-of 日期，
  并在实现 / 文档阶段再次复核。
- **不新增契约**：本 feature 落的是宪法原则 IV 的 MUST（标准协议输出），不新增
  C23 / C24 之外的契约条目；若要调整原则 IV 措辞，MUST 走 Governance 修订。
- **文档联动**：实现阶段 MUST 更新 README 的可观测 / OTLP 章节、`THIRD_PARTY_NOTICES`、
  B3F1 的 extras / 门禁清单，并生成 `harness/verification/B21F1/manual-verification.md`；
  该记录 MUST 由自动文档守卫核验。
