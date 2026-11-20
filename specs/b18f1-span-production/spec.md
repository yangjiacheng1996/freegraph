# Feature Specification: B18F1 · Span 数据类生产（节点 / 工具 / 模型三级 span，属性名对齐 `gen_ai.*`）

**Feature Branch**: `b18f1-span-production`

**Created**: 2026-11-20

**Status**: Draft

**Input**: User description: "B18F1 · Span 数据类生产：交付 freegraph 自有 Span 数据类的**生产行为**，在运行时为节点 / 工具 / 模型三级产生 span；属性命名对齐 OpenTelemetry GenAI 语义约定（`gen_ai.*`）；未注入 tracer 时零副作用、零开销。前置依赖 B7F3。字段面归 B2F1（11 字段逐字冻结），本 feature MUST NOT 增删字段。"

---

## 范围与口径（本 spec 的权威边界）

| 项 | 本 spec 的口径 |
|---|---|
| **交付什么** | **span 的生产行为**：节点级 / 工具级 / 模型级 span 的产生、父子关系、耗时、关联键、`gen_ai.*` 属性。 |
| **不交付什么** | `Span` 的字段面（**B2F1 已冻结** · 11 字段）、`TraceSink` 的公开注入点与 `current_span()`（**B19F1**）、trace 存储（**B20F1 / B20F2**）、OTLP 导出（**B21F1**）、前端 UI（v2 / B26）。 |
| **「符合 semconv」的可判定形式** | **span 属性命名**符合 OTel GenAI semconv；**不是**「产出 OTel SDK 的 span 对象」（v1 不依赖 `opentelemetry-*`）。 |
| **「tracer」/「receiver」在本 feature 中的含义** | **tracer = `SpanProducer`**（显式传入、持有当前 span 栈的内部生产接缝）；**receiver = 接收端**（`on_span_start` / `on_span_end`，可为测试计数夹具或 B19F1 注入的 `TraceSink`）。二者均**MUST NOT** 来自环境变量。公开的 `TraceSink` 注入形态与 `current_span()` 归 **B19F1**；B18F1 只建立**内部生产接缝**（见裁定 Q2）。 |
| **零开销** | 未启用 span 生产时：**span 对象构造数 == 0**、回调调用数 == 0、不生成 span 专用运行标识、不读环境变量。**`stream()` 既有的事件 `run_id` 由 B8F2 独立生成，不属于 span 生产**。允许**一次**廉价分支判断，不允许在热路径构造中间对象。 |
| **依赖** | 基础安装依赖闭包**仍为空集**；`opentelemetry-*` / `langchain*` / `langsmith` 一律**不引入**。 |
| **字段权威** | `specs/b2f1-contracts-protocols/contracts/public-api.md` §1.2 / §1.3（11 字段 + 冻结行为）。 |
| **契约编号** | **C23**（可观测挂钩 / span 必带字段）· **C24**（当前 span 上下文，归 B19F1）· active 清单 = **C1–C24 + C26–C27**（C25 已作废）。 |
| **上游权威** | `langgraph 1.2.11` / `langchain-core 1.7.6`（2026-11-20 取证于本仓库 `.venv`）；上游**无同名 `Span` 数据类、无自有 span 生产协议**，本 feature 属宪法原则 XI 的**必须自研区 ③（上游没有的能力）**。 |

---

## 原则 IV 的字段载体映射（输入 / 输出 / 错误）

> 宪法原则 IV 要求「每一次节点执行都必须产生可观测记录，MUST 包含：节点名、输入状态、输出状态、耗时、错误」。
> 该记录**不是单个 `Span` 的全部责任**；freegraph 由**多个产物组合**满足。B18F1 只负责其中的
> **span / 耗时 / 节点身份**；其余字段由既有 `stream()` 事件 / `PregelTask` / 状态快照与
> **B19F1 / B20** 承接。**MUST NOT** 因 Q11/Q12 而声称节点 span 已携带全部五项。

| 原则 IV 字段 | B18F1 的载体 | 既有 / 下游载体 | 说明 |
|---|---|---|---|
| **节点名** | 节点 span 的 `name` / `node` | `stream_mode="tasks"` 的 `PregelTask.name` | 同名（内部节点名） |
| **耗时** | 节点 span 的 `start_time` / `end_time` | — | 严格正耗时（FR-009） |
| **输入状态** | **不写进节点 span**（Q11） | `stream_mode="values"` 的 step 前状态 + B19F1/B20 | `stream()` 路径可还原；`invoke()` 逐节点输入由 B19F1/B20 承接 |
| **输出状态** | **不写进节点 span**（Q11） | `stream_mode="updates"` / `"tasks"` 的 `PregelTask.result` + `"values"` step 后状态 | `stream()` 路径可还原；`invoke()` 逐节点输出由 B19F1/B20 承接 |
| **错误** | **不写进节点 span**（Q12）；模型 / 工具 span 失败时 MUST 写 `error.type` | 原样抛出的异常（并发其它失败见 `add_note`）；`PregelTask.error` 仅在非抛出快照 / 中断路径可见 | `stream()` 路径由异常还原；`invoke()` 逐节点错误由 B19F1/B20 承接 |

**约束**：

- B18F1 的节点 span **MUST** 保持 `attributes={}`（Q11）；**MUST NOT** 为了原则 IV 把输入 / 输出 / 错误塞进节点 span；
- `stream()` 路径的输入 / 输出 MUST 能由既有 `values` / `updates` / `tasks` + `PregelTask.result` 还原；**错误** MUST 能由**原样抛出的异常**（并发其它失败见 `add_note`）还原；`PregelTask.error` **不作为失败路径载体**（SC-016）；
- `invoke()` 路径的逐节点输入 / 输出 / 错误 MUST 由 **B19F1 / B20** 提供等价 trace record（D-6）；**B19F1 / B20 的 spec MUST 落成该承接**；B18F1 **MUST NOT** 声称已在本 feature 内闭合该路径；
- 原则 IV 的「错误」不要求节点 span 写 `error.type`；`error.type` 只用于模型 / 工具失败 span（Q12）。

---

## 承接条款（上游 feature → 本 feature）

> 宪法「跨 feature 承接的接线通则」（v1.8.0；现行 1.16.0）：上游 feature 指名本 feature 的跨 feature 义务
> MUST 在本 spec 落成 **FR + 裁定**；**只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽判据**。

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B2F1 → B18F1** | **M1** | **`Span` 的字段面已冻结（11 字段）**：`id` / `name` / `attributes` / `parent` / `start_time` / `end_time` / `context` + 必带四项 `thread_id` / `run_id` / `node` / `checkpoint_id`。本 feature **只生产**，MUST NOT 增删 / 改名 / 改类型 / 改缺省；确需变更走**契约修订**流程。 | `specs/b2f1-contracts-protocols/contracts/public-api.md` §1.2 / §1.3 · `src/freegraph/contracts/trace.py:27-92` | FR-001 / 裁定 Q3（字段面不改） |
| **H-2** | **B7F3 → B18F1** | **M2** | **`invoke()` 已返回完整状态**：节点执行、稀疏状态、图级入口 `run_graph` 均已落地；B18F1 MUST 在不改 `invoke()` 签名 / 终态形状 / 节点签名的前提下接入 span 生产。 | `specs/b7f3-invoke-full-state/spec.md` · `src/freegraph/_stategraph.py:631-677` | FR-004 / FR-020 |
| **H-3** | **B8F2 → B18F1** | **M2** | **D-3：两条事件通道独立、按 id 合并**：`stream()` 事件与 `TraceSink` 的 span 不互为前置；二者 MUST 共享同一 `run_id` / `thread_id`。**载体 = L2 私有 contextvar** `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`（由 `StreamSession` 绑定）；**B18F1 MUST 读取 / 复用同一对值**（stream 路径只读；invoke 路径经 `bind_run_ids` 绑定）。 | `specs/b8f2-stream-modes/spec.md` **下游承接 D-3** · `src/freegraph/runtime/_stream_context.py:91-122` | FR-012 / 裁定 Q4 |
| **H-4** | **B8F3 → B18F1** | **M2** | **D-2 / D-3：`context` 与 trace 的关系**：C21 的 `context` 是节点只读运行期上下文，**不是** `Span.context` 字段；本 feature MUST NOT 复用 `Span.context` 承载 C21 的 `context`。MUST 以「`context` 已接线、alias 已移除」为前提；MUST NOT 回退到 `configurable`，MUST NOT 重新引入节点别名。 | `specs/b8f3-node-alias-context/spec.md` **下游承接 D-2 / D-3** | FR-021 / FR-026 |
| **H-5** | **宪法 → B18F1** | **M3** | **原则 IV**（可诊断性是一等功能 · 路线 B）· **原则 VII**（C23 / 标识与关联键约定）· **原则 I / II / IX**（零 LangSmith / 零 LangChain / 零第三方依赖 / 许可证）· **原则 XI**（上游优先；自研须登记）· **原则 XII**（形态取最优）。 | `.specify/memory/constitution.md` 原则 IV / VII / XI / XII | FR-007 / FR-018 / FR-019 / 上游对照 |
| **H-6** | **Q6 → B18F1** | **M3** | **路线 B 的 trace 采集口径**：tracing 层产出 OTel 兼容 span；**图节点 span 用自定义命名空间**（如 `freegraph.*`）但挂在同一 trace 下；模型 / 工具属性用 `gen_ai.*`。**B18F1 的节点 span 取空映射**（Q11），不提前附加结构属性。 | `harness/reports/Q6-可视化与可诊断性的规模与可行性.md` §4.2 第 1 条 | FR-013 / 裁定 Q3 |
| **H-7** | **Q8 / D11 → B18F1** | **M3** | **C23 字段约定**：每个 span MUST 带 `thread_id` / `run_id` / 节点名 / `checkpoint_id`；四项可读；**缺 `run_id` 的 span 视为实现缺陷**。`run_id` 由运行时生成、用户不可设置 / 覆盖；`thread_id` 由 `RunConfig` 承载。 | `harness/reports/Q8-图运行时最小契约.md` §3.4.1 · 宪法原则 VII | FR-011 / FR-012 |

### 引文差异（提示词初稿 vs 本 spec）

| # | 提示词初稿表述 | 本 spec 的落地口径 | 理由 |
|---|---|---|---|
| **C-1** | 「FR-001 系统 MUST 提供自有 `Span` 数据类」 | **`Span` 已由 B2F1 交付并冻结**；B18F1 **只生产**，MUST NOT 重定义 / 增删字段 | B2F1 澄清 Q2 / Q6：字段面归 B2F1，生产行为归 B18F1 |
| **C-2** | 「注入 tracer 后，节点执行产生 span」 | B18F1 的「tracer」= **内部生产接缝**（测试可注入计数夹具）；**公开 `TraceSink` 注入点 + `current_span()` 归 B19F1** | 提示词 §8 边界：B18F1 只生产，不接入 / 不推送 |
| **C-3** | 「span 的 `attributes` 属性名 100% 符合 `gen_ai.*`」 | **模型 / 工具语义**的属性名 100% `gen_ai.*`；**节点 span** 的属性为**空映射**（v1 不附加结构属性）；**唯一的非 gen_ai 通用属性** `error.type` 在**模型 / 工具 span 失败时 MUST 出现**（Q12）；节点 span 恒为空映射 | Q6 §4.2 第 1 条允许节点 span 用自定义命名空间，B18F1 取更小的空映射；本口径不放宽模型 / 工具属性判据 |
| **C-4** | 「模型调用 / 工具调用场景各产生对应层级的 span」 | 通过**鸭子类型可观测接缝**在生产边界识别并产生；**不对节点函数内部的任意 `.invoke` 做魔法拦截**（见裁定 Q1） | 无 API 注册 / 无装饰器时，任意 Python 函数体不可被框架透明拦截；v1 以显式接缝保证可判定与零开销 |
| **C-5** | 提示词列 `gen_ai.system`（Q6 旧文） | **MUST NOT** 使用已弃用的 `gen_ai.system`；使用当前 semconv 的 **`gen_ai.provider.name`** | OTel GenAI semconv 当前版本已将 provider 标识定为 `gen_ai.provider.name` |

---

## 下游承接条款（本 feature → 下一棒）

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 |
|---|---|---|---|---|
| **D-1** | **B18F1 → B19F1** | **M3** | **生产接缝可被 `TraceSink` 消费**：B18F1 产出的 span（含开始 / 结束两个生命周期快照）MUST 能原样交给 B19F1 的 `on_span_start` / `on_span_end`；B19F1 **MUST NOT** 重新实现 span 生产、MUST NOT 改 11 字段。B19F1 的公开注入点 MUST 构造 `SpanProducer`（接收端 = 用户 `TraceSink`），并把**同一个 `SpanProducer`** 绑定到 L2 `_span_hook` 与 L5 `_producer` 两处（双绑定）。B18F1 **MUST NOT** 实现公开 `TraceSink` 注入点或 `current_span()`。 | FR-027 / Out of Scope / plan R-4 |
| **D-2** | **B18F1 → B20F1 / B20F2** | **M3** | **JSON 可序列化**：每个 span 的字段经 `dataclasses.asdict(span)` 后 100% 可被标准库 `json.dumps` 序列化（C27 前提）；`run_id` / `thread_id` / **时间范围** / `node` 可直接作为查询维度（**C27 / DF6；v1 不含 `checkpoint_id` 过滤器**）。 | FR-011 / FR-014 / SC-008 |
| **D-3** | **B18F1 → B21F1** | **M4** | **OTLP 映射 1:1**：模型 / 工具 span 的 `attributes` 键**除模型 / 工具失败时的 `error.type` 外**全部来自 `gen_ai.*` 允许清单，B21F1 的 OTLP exporter 可**逐键直映射**，无需解析 freegraph 私有格式。 | FR-013 / 属性允许清单 |
| **D-4** | **B18F1 → B14F1** | **M3** | **`checkpoint_id` 的取值来源**：B18F1 只保证字段可读、不伪造；节点 span 接受来自运行期的 `checkpoint_id`（v1 为 `None`），模型 / 工具 span **从当前节点 span 继承**该值。B14F1 挂接 checkpointer 后 MUST 通过既有运行期接缝把当前 checkpoint 标识填入**节点 span**（**不回改 B18F1 的字段面**，子 span 自动继承）。 | FR-011 / Assumptions |
| **D-5** | **B18F1 → 文档面** | **M3** | **属性对照表**：本 spec 的「`gen_ai.*` 属性允许清单（含 semconv 出处）」MUST 进入用户可见文档 / 契约（README 的**独立「可观测属性」章节**；**MUST NOT** 改动 API 兼容矩阵），B21F1 与第三方面板对接时以该表为准。 | 属性允许清单 / 依据 |
| **D-6** | **B18F1 → B19F1 / B20** | **M3** | **原则 IV 的 invoke 路径载体**：B18F1 的节点 span 只承担节点名 / 耗时；`invoke()` 路径的逐节点输入状态 / 输出状态 / 错误 MUST 由 B19F1（`TraceSink` / `current_span`）或 B20（trace 存储 / 查询）提供等价记录，且**承接机制 MUST 在 B19F1/B20 的 spec 写死**（B19F1 MUST 通过 L2 既有节点接缝（或其扩展 hook）捕获 `(node, input_state, output_state, error)`，或 B20 MUST 从 `PregelTask` / `SuperStepResult` 快照取等价记录）；**错误载体 = 原样抛出的异常（+ `add_note`）**；B18F1 不把这三项塞进节点 span，也不声称在本 feature 内闭合该路径。 | FR-029 / SC-016 / 原则 IV 映射 |

---

## Clarifications

### Session 2026-11-20（spec 阶段设计裁定 · plan 不得再翻）

#### Q1（节点函数体内部的模型 / 工具调用如何被「检测」）

→ **A：节点 span 自动产生；模型 / 工具 span 通过「鸭子类型可观测调用接缝」产生。**

- **节点 span**：由运行期在**单一节点执行接缝**自动产生（`NodeSpec.run` 调用前后），**不要求**用户改节点签名、不改状态语义、不改 `SuperStepResult` 字段。
- **模型 / 工具 span**：节点通过 **`invoke_model` / `invoke_tool` 一次性调用辅助**调用鸭子类型对象时产生（Q10）。这两个辅助是 B18F1 的唯一模型 / 工具生产入口（L5 模块、非公开门面；**不是** `TraceSink`）。
- **为什么不做「魔法拦截」**：freegraph 的节点是任意 Python 可调用对象，模型 / 工具通常是节点闭包中的变量；在不注册、不装饰、不改用户代码的前提下，运行期**无法**透明拦截任意 `.invoke` 调用。若用 `sys.settrace` / monkeypatch 等手法，会破坏「零开销」「不改用户对象」「零第三方依赖」三条红线。故 v1 以**显式接缝**作为生产边界；这与 OTel 官方「工具调用常由应用代码直接执行，应用开发者被鼓励手动埋点」的口径一致（`semantic-conventions-genai/docs/gen-ai/execute-tool.md`）。
- **零开销**：未启用生产时，节点执行接缝只做一次廉价判断；接缝不被调用或生产关闭时，不构造任何 span / 中间对象。

#### Q2（B18F1 的「tracer」与 B19F1 的 `TraceSink` 如何分工）

→ **A：B18F1 建立内部生产接缝；B19F1 负责公开注入点与 `current_span()`。**

- B18F1 的「tracer」是**显式传入**的 `SpanProducer`（持有当前 span 栈、产生 / 转发 span）；它的**接收端（receiver）**是 `on_span_start` / `on_span_end` 的承载者（测试用计数夹具即属于此，B19F1 的用户 `TraceSink` 也属于此）。二者**不**从环境变量读取，**不**自动开启。
- 公开的「用户在 `compile` / `invoke` / `stream` 上传入 `TraceSink`」形态、`on_span_start` / `on_span_end` 的推送、`current_span()`，**全部归 B19F1**。
- B18F1 的生产结果（开始快照 + 结束快照）MUST 能被 B19F1 **原样消费**（D-1）；B19F1 MUST 复用同一个 `SpanProducer` 并双绑定（L2 + L5）。

#### Q3（节点 span 的属性命名空间）

→ **A：模型 / 工具 span 用 `gen_ai.*`；节点 span 的 `attributes` 为空映射。**

- 节点执行不是 OTel GenAI 语义中的模型 / 工具操作，**MUST NOT** 强行套 `gen_ai.*`。
- 节点 span 的身份由 `node` 字段 + `name`（节点名）表达；`attributes` **v1 恒为空映射**（Q11）。**MUST NOT** 附加 `freegraph.*` 结构属性（superstep / task id / 触发源等归 B19F1 的承接范围）。
- 因此 SC-001 的判据是：**模型 / 工具语义属性 100% `gen_ai.*`**；**节点属性为空**；**不得出现无命名空间的私有键**。

#### Q4（`invoke()` 路径的 `run_id` 从哪里来）

→ **A：优先复用运行期已绑定的 `_STREAM_RUN_ID`；未绑定时，仅在 span 生产启用期间建立一个 run-scoped `run_id`。**

- `stream()` 路径：`StreamSession` 已绑定 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`；B18F1 **只读同一对值**，**MUST NOT** 另生成 id（H-3）。
- `invoke()` 路径：当前无 `StreamSession`。若 span 生产启用而运行期未绑定 id，B18F1 MUST 为该次运行建立**一个** run-scoped `run_id`（与运行期同一生成规则 · 标准库），经 `bind_run_ids` 写入**同一对** contextvar，并在该次运行的整个 span 树中复用；**MUST NOT** 每个 span 各生成一个。
- `RunConfig.run_id` **MUST 被忽略**（宪法 v1.15.2：该字段为上游兼容保留，MUST NOT 用作事件 / span 的 `run_id`）；用户不可设置 / 覆盖。
- 未启用 span 生产时，**MUST NOT** 生成 / 绑定任何 **span 专用**运行标识（零开销；`stream()` 既有事件 id 不属 span 生产）。
- B18F1 **MUST NOT** 新增第二套 id 生成机制；若 plan 需要把 id 绑定推进到 `invoke` 路径，MUST 复用运行期同一载体（`_STREAM_RUN_ID` / `_STREAM_THREAD_ID` 或等价的 L2 私有载体）。本 feature 采用前者：在 `run_graph` 经 L2 私有助手 `bind_run_ids(run_id, thread_id)` 设置**同一对** contextvar（见 plan R-2 / tasks T007），不新增第二套载体。

#### Q5（`checkpoint_id` 何时有值）

→ **A：当前运行期有 checkpoint 标识时填入；没有时 `None`，MUST NOT 伪造。**

- B18F1 只负责「字段可读 + 取值正确」；checkpoint 的产生归 B14F1。
- B18F1 落地时尚无 checkpoint 标识来源 ⇒ 值为 `None` 是**合法现状**；节点 span 接受运行期值，模型 / 工具 span 从节点 span 继承；B14F1 通过既有接缝补**节点 span**（D-4），**不改字段面**。
- `checkpoint_id` 为 `None` **不构成**「缺关联键」缺陷；**`run_id` 为空才是缺陷**（C23 / D11）。

#### Q6（输入 / 输出内容是否进入 span 属性）

→ **A：v1 默认不采集内容。**

- `gen_ai.input.messages` / `gen_ai.output.messages` / `gen_ai.system_instructions` / `gen_ai.tool.call.arguments` / `gen_ai.tool.call.result` / `gen_ai.tool.definitions` 均为 semconv 的 **Opt-In** 内容属性。
- v1 **MUST NOT** 默认采集；若未来提供采集能力，MUST 由**显式配置**控制（不读环境变量），并沿用 semconv 的 `NO_CONTENT` 默认档。
- 本 feature 的 span 只携带**结构化元数据**（模型名、工具名、工具调用 id），不含用户消息 / 工具参数 / 工具结果；用量 / 结束原因等按 Q9 在 v1 不采集。

#### Q7（失败 / 异常的 span 行为）

→ **A：开始 / 结束仍成对；异常原样透传；`error.type` 仅出现在失败时的模型 / 工具 span 上。**

- 节点 / 模型 / 工具调用抛异常时，B18F1 MUST 产出**同 `id` 且已填 `end_time`** 的结束 span，然后**原对象 + 原类型 + 原消息**重新抛出（MUST NOT 包装 / 吞掉）。
- 失败时，**模型 / 工具 span** MUST 在 `attributes` 写 **`error.type`**（OTel general `recording-errors`，非 `gen_ai.*`）；这是本 feature 允许的**唯一**非 gen_ai 键。**节点 span MUST NOT 写 `error.type`**（保持空映射）；成功时任何 span 都 MUST NOT 出现。
- 开始快照 MUST NOT 被事后改写（B2F1 的冻结生命周期：开始时 `end_time` 为空的新实例，结束时同 id 的新实例）。

#### Q8（是否新增公开门面符号）

→ **A：不新增。**

- B2F2 的公开门面符号数 / B2F1 的契约符号数是**冻结面**；`invoke_model` / `invoke_tool` 是 **L5 模块符号**（**MUST NOT** 进入 `freegraph.graph` 门面，**MUST NOT** 扩大公开 API 快照）；是否由 B19F1 对外再导出，归 B19F1 决定。
- B19F1 若需要公开注入 API，由其按流程自行破冻结面并追认；B18F1 不代做。

### Session 2026-11-20 · clarify 轮（用户拍板）

#### Q9（v1 模型 / 工具元数据的采集范围）

- Q: 模型级与工具级 span 除了操作名和名称外，还应采集哪些元数据？ → A: **Option A（极简）**。只写 `gen_ai.operation.name`、`gen_ai.request.model`（来源：对象的 `model_name` 或 `model` 属性）、`gen_ai.tool.name`、`gen_ai.tool.call.id`（调用方提供时）；provider / usage / response / finish_reasons / temperature / tool.description / conversation.id 等一律省略。**用户理由**：freegraph 是**通用图框架**，不是专为 AI 智能体设计；元数据面必须保持通用、克制，避免刻意绑定大模型。

#### Q10（模型 / 工具埋点接缝的形态）

- Q: 节点调用模型 / 工具时，B18F1 应以什么形态提供「产生子 span」的接缝？ → A: **Option A（一次性调用辅助）**。提供 `invoke_model(obj, input, *, call_id=None)` / `invoke_tool(obj, args, *, call_id=None)`：只对用户主动传入的对象产生 span，不隐式拦截节点里的任意 `.invoke`；放在 L5 模块、非公开门面，可 import 使用。**理由**：显式、无代理魔法、任意对象可用，且避免把普通 `invoke` 对象误判为模型；与通用图框架定位一致。

#### Q11（节点 span 是否携带额外结构属性）

- Q: 节点级 span 是否要额外携带 `freegraph.*` 结构属性（如 superstep、task id、触发源）？ → A: **Option A（不加）**。节点 span 的 `attributes` 保持**空映射**；节点身份由 `name` / `node` 字段表达；并发分组 / 触发源归 B19F1 按承接条款处理。**理由**：与 Q9 的极简口径一致，避免 B18F1 提前扩大属性面。

#### Q12（失败时 `error.type` 的层级）

- Q: 失败时 `error.type` 应出现在哪些层级的 span 上？ → A: **Option A（仅模型 / 工具 span）**。模型 / 工具调用失败时写 `error.type`；节点 span 无论成功失败都保持**空映射**。**理由**：既保留 GenAI semconv 的失败信息，又让节点 span 严格满足 Q11 的「恒为空」。

#### Q13（调用辅助在节点执行之外的行为）

- Q: `invoke_model` / `invoke_tool` 在节点执行之外被调用时，应如何处理？ → A: **Option A（直接调用、不产生 span）**。没有活动节点 span 时，辅助函数等价于 `obj.invoke(...)`；不伪造 `node`，零 span、零副作用。**理由**：`Span.node` 必须是真实节点名，不能为了「有 span」而伪造 `__external__` 或空串；模型 / 工具 span 只发生在节点执行期间。

#### Q14（辅助函数名与对象形状不一致时的处理）

- Q: 当一个对象的实际形状与所调用的辅助函数名不一致时，应如何处理？ → A: **Option C（形状不匹配抛 `TypeError`）**。`invoke_model` 只接受「有 callable `invoke` 且**非工具形状**」的对象；`invoke_tool` 只接受「`name`（str）+ `description` + callable `invoke`」的对象；否则立即抛内置 `TypeError`。**理由**：辅助函数名是用户的显式意图，形状不匹配应快速失败，避免静默产出错误层级的 span；符合通用、显式、可预测的定位。

#### Q15（v1 `Span.context` 是否承载附加元数据）

- Q: v1 是否允许 `Span.context` 承载任何附加元数据？ → A: **Option A（恒为空映射）**。B18F1 产出的所有 span 的 `context` 都是 `{}`；谁都不填。**理由**：与节点属性恒空、元数据极简的口径一致；`Span.context` 先作为 B2F1 冻结面里的保留字段，未来需要时再由新 feature 按契约定义来源，避免现在引入没有明确所有者的扩展点。

#### Q16（是否支持返回 awaitable 的异步 `invoke`）

- Q: v1 是否要支持返回 awaitable 的异步 `invoke` 调用？ → A: **Option B（仅同步、检测到 awaitable 抛 `TypeError`）**。`invoke_model` / `invoke_tool` 调用对象后，若结果为 awaitable（`inspect.isawaitable(result)` 为真），MUST 结束当前 span（成对）并抛内置 `TypeError`；MUST NOT 返回 awaitable，MUST NOT 提供异步辅助。**理由**：v1 运行时是同步的；静默返回 awaitable 会让 span 只覆盖「创建协程」而非「真正执行」，trace 必然误导；快速失败与 Q14 的显式口径一致。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 知道每一步跑了多久 (Priority: P1)

作为用户，我注入 span 生产接收端后运行一张图，希望**每个被执行的节点**都产生一个 span，含节点名与起止时间，从而定位慢在哪一步。

**Why this priority**: 这是 B18F1 的最小价值切片；没有节点 span，后续工具 / 模型 span 与 trace 时间线都无从谈起。

**Independent Test**: 注入计数 / 捕获夹具，跑一个两节点线性图，断言产生 **2 个节点 span**，`name` == 节点名、`node` == 节点名、`start_time < end_time`。

**Acceptance Scenarios**:

1. **Given** 已启用 span 生产，**When** 执行一个节点，**Then** 产生 1 个节点 span，`name` / `node` 均为该节点名，`end_time` 非空且时间差 > 0。
2. **Given** 已启用 span 生产，**When** 执行 `a → b` 两节点图，**Then** 产生 2 个节点 span，顺序不构成判据（并发下按节点名 / 完成序均可），但**数量**与**归属**必须正确。
3. **Given** 节点抛异常，**When** 执行结束，**Then** 该节点仍有一个已结束 span，且原始异常原样抛给调用方。

---

### User Story 2 - 模型与工具调用各自有 span (Priority: P1)

作为用户，我希望模型调用与工具调用各自有**独立的子 span**（而非埋在节点 span 里），从而能单独统计模型耗时、工具耗时与调用次数。

**Why this priority**: 这是「三级 span」的核心；只有节点 span 时，用户无法区分「模型慢」还是「工具慢」。

**Independent Test**: 在一个节点内分别用 `invoke_model(model, input)` 与 `invoke_tool(tool, args)` 调用鸭子类型对象，断言产生 **模型 span 1 个 + 工具 span 1 个**，二者的 `parent` == 该节点 span 的 `id`，且 `attributes` 中 `gen_ai.operation.name` 分别为 `chat` / `execute_tool`。

**Acceptance Scenarios**:

1. **Given** 已启用 span 生产，**When** 节点调用一个具备 `invoke` 且不具备工具形状的对象，**Then** 产生模型 span，`name` 以 `chat` 开头，`gen_ai.request.model`（若可读）存在。
2. **Given** 已启用 span 生产，**When** 节点调用一个具备 `name`（str）+ `description` + `invoke` 的工具对象，**Then** 产生工具 span，`name` == `execute_tool <tool.name>`，`gen_ai.tool.name` == `tool.name`。
3. **Given** 工具内部再调用模型，**When** 生产结束，**Then** 模型 span 的 `parent` == 工具 span 的 `id`（不跳过层级）。
4. **Given** 同一节点内连续调用模型 2 次，**When** 生产结束，**Then** 产生 2 个独立模型 span（不合并）。

---

### User Story 3 - 不诊断时零负担 (Priority: P1)

作为用户，我不需要诊断时，希望 freegraph **完全不产生额外开销**：不创建 span 对象、不触发回调、不读环境变量、不引入额外依赖。

**Why this priority**: 这是原则 IV 的硬承诺；若「零开销」不可测，将来加埋点不会有任何红线提醒。

**Independent Test**: 不注入任何接收端，运行同一张图；用计数夹具 / 构造计数断言 **span 对象构造数 == 0**、接收端回调数 == 0；再断言依赖闭包仍为空集、`import freegraph` 不加载 L5 生产模块。

**Acceptance Scenarios**:

1. **Given** 未启用 span 生产，**When** 执行任意图，**Then** span 构造数 == 0，回调数 == 0。
2. **Given** 未启用 span 生产，**When** 设置 `LANGSMITH_TRACING=true` / 任意 `LANGCHAIN_*` 环境变量，**Then** 行为不变、span 构造数仍 == 0（MUST NOT 读环境变量）。
3. **Given** 未启用 span 生产，**When** 检查 `import freegraph` 后的 `sys.modules`，**Then** 不出现 L5 生产模块、`opentelemetry.*`、`langchain*`、`langsmith`。

---

### User Story 4 - 每条 span 都能回连到运行与会话 (Priority: P2)

作为用户，我希望每个 span 都带 `run_id` / `thread_id` / 节点名 / `checkpoint_id`，从而能与 `stream()` 事件按 id 合并、按会话回查、与图结构对齐。

**Why this priority**: C23 / D11 已冻结的关联键；缺 `run_id` 即实现缺陷。

**Independent Test**: 在 `stream()` 内启用生产，收集事件与 span；断言**同一次运行**的所有 span 与事件的 `run_id` 相同、`thread_id` 相同；`node` 与事件中的节点名一致。

**Acceptance Scenarios**:

1. **Given** `RunConfig(thread_id="t-1")` 且启用生产，**When** 运行，**Then** 每个 span 的 `thread_id == "t-1"`、`run_id` 非空。
2. **Given** `stream()` 同一次运行，**When** 对比事件与 span，**Then** 二者的 `run_id` / `thread_id` **逐字相同**。
3. **Given** 未挂 checkpointer 或运行期无 checkpoint 标识，**When** 产生 span，**Then** `checkpoint_id is None` 且字段可读（不视为缺陷）。
4. **Given** `RunConfig(run_id="user-supplied")`，**When** 启用生产，**Then** span 的 `run_id` **不等于** `"user-supplied"`（用户不可设置 / 覆盖）。

---

### User Story 5 - 并发节点不串父 (Priority: P2)

作为用户，我希望并发执行的多个节点的 span 各自独立，模型 / 工具 span 只挂在自己的节点下，不发生跨任务的父子串线。

**Why this priority**: B12F1 已交付并发执行；span 树在并发下若串线，trace 会误导诊断。

**Independent Test**: 构造一个 super-step 内并发 3 个节点的图，每个节点通过接缝调用一个工具；断言 3 个节点 span 的 id 互不相同，每个工具 span 的 `parent` 恰好是其所属节点的 id，且不存在「工具 span 的 parent 指向另一个节点」。

**Acceptance Scenarios**:

1. **Given** 同一 super-step 并发执行 N 个节点，**When** 启用生产，**Then** 产生 N 个节点 span，顶层节点 parent 均为空（本 feature 无 run 级 span）。
2. **Given** 每个节点调用 1 个工具，**When** 生产结束，**Then** 工具 span 的 parent 集合与节点 span 的 id 集合构成一一对应，无跨任务父子。

---

### Edge Cases

- **未启用生产时**：节点执行、异常、并发、`stream()` / `invoke()` 均不得构造 span；不得因生产接缝的存在而改变任何可观察行为。
- **在节点外调用辅助函数**：`invoke_model` / `invoke_tool` 等价于直接 `obj.invoke(...)`；不产生 span、不伪造节点名、不报错（Q13）。
- **接收端抛异常**：接收端（receiver）回调抛出的异常 MUST 被**隔离**——MUST NOT 传播到节点函数 / 图执行、MUST NOT 改变执行结果、MUST NOT 吞掉节点自身的异常；该次可观测写入 MAY 被丢弃，但 MUST NOT 造成永久挂起或改变 `invoke()` / `stream()` 的输出。
- **鸭子类型对象同时具备工具形状与 `invoke`**：传给 `invoke_model` ⇒ `TypeError`（工具形状对象不能当模型用）；传给 `invoke_tool` ⇒ 只产生一个工具 span。
- **对象既无 `invoke` 也无工具形状**：传给 `invoke_model` / `invoke_tool` 均抛内置 `TypeError`（Q14），不做静默透传。
- **形状校验与生产开关无关**：即使未启用 span 生产，辅助函数仍按 Q14 校验形状；校验通过后，未启用生产时等价于直接调用。
- **对象 `invoke` 返回 awaitable**：辅助函数 MUST 结束当前 span（成对）并抛内置 `TypeError`（Q16）；MUST NOT 返回协程 / awaitable。
- **工具名为空**：工具形状要求 `name` 为 `str`；**空字符串仍视为合法工具**。`gen_ai.tool.name` **总是写**（空串也写），**不省略、不伪造**；span 名为 `execute_tool <tool.name>`（空串时为 `execute_tool `）。
- **极端快调用**：`start_time == end_time` 不允许；MUST 保证**严格大于 0** 的耗时（实现可用纳秒级时间源或等价机制）。
- **异常路径**：开始 / 结束必须成对；结束 span 的 `id` 与开始相同；原始异常对象 / 类型 / 消息不变。节点 span 保持空属性（不写 `error.type`）；模型 / 工具 span 失败时 MUST 写 `error.type`。
- **嵌套调用**：模型 → 工具 → 模型，父链必须逐层正确；任一内层结束，外层恢复为「当前 span」。
- **并发 / 线程**：每个任务线程的当前 span 栈独立；MUST NOT 让一个线程的 span 成为另一线程的 parent。
- **重复 `run_id`**：同一次运行所有 span 共享一个 `run_id`；不同运行 MUST 不同。
- **`thread_id is None`**：合法；span 的 `thread_id` 为 `None`，不报错。
- **`checkpoint_id` 不可得**：合法；为 `None`，不伪造。
- **`Span.context` 与 C21 `context`**：二者 MUST 分离；`Span.context` 在 v1 恒为空映射（Q15），不得塞入 `RunConfig.context` / 节点 state / 任何自定义元数据。
- **内容属性**：默认不得出现 `gen_ai.input.messages` / `gen_ai.output.messages` / `gen_ai.tool.call.arguments` / `gen_ai.tool.call.result`。
- **已弃用属性**：不得出现 `gen_ai.system`；provider 标识只用 `gen_ai.provider.name`。

---

## Upstream Parity *(mandatory — 宪法 v1.12.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11** / `langchain-core` **1.7.6** / `langsmith` **0.14.17**（取证于 2026-11-20，本仓库 `.venv` 实际安装版本）

> **口径说明**：上游**没有** freegraph 这样的「自有 `Span` 数据类 + 自有 span 生产协议」。
> 上游的可观测挂钩是 `callbacks` / `tracers`，其 span 数据模型来自 `langsmith.RunTree`，且
> `langchain-core` 的 `Requires-Dist` **硬依赖** `langsmith`（原则 I 的推论）。因此本 feature 的
> 主体落在宪法原则 XI 的**必须自研区 ③（上游没有的能力）**与 **①（零账号 / 零主动出站 / 零依赖）**；
> 只有「默认关闭」「父子关系」「失败也成对」这三类**行为面**需要与上游对齐。

### §1 逐条对照（P-01…P-11）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| **P-01** | 无任何 tracer / handler 时不产生观测对象 | `langgraph/pregel/_retry.py:617`（`task.proc.invoke`）· `langgraph/pregel/main.py:2919`（`has_graph_lifecycle_callbacks=bool(...)`）· 实测 **E-1**（无 handler ⇒ 0 个回调） | 未启用生产 ⇒ span 构造数 == 0、回调数 == 0 | **SAME** | 默认关闭是上游同款行为面 |
| **P-02** | 每个节点执行产生一个观测单元 | `langgraph/pregel/_retry.py:617`（节点任务调用）· `langchain_core/runnables/base.py:2344`（`on_chain_start`）/ `:2369`（`on_chain_end`）· 实测 **E-2**（2 节点 ⇒ 2 组节点开始 / 结束） | 每个被执行的节点任务产生一个节点 span（开始 + 结束） | **DIFF** | 上游观测单元是 LangChain callback run / LangSmith `RunTree`；freegraph 是自有 11 字段 `Span` ⇒ 自研区 ③ |
| **P-03** | 父子关系（嵌套） | `langchain_core/callbacks/manager.py:510,532,623`（`parent_run_id` 的构建 / 传递）· `langchain_core/tracers/base.py:47,53`（父 id 解析）· 实测 **E-2**（节点 run 的 parent = 图 run） | `parent` 为**父 span 的 id 字符串**；模型 / 工具 span 的 parent = 所在节点 span id；嵌套逐层 | **DIFF** | 语义 SAME、**表示**不同（id 字符串 vs 对象引用）；B2F1 已冻结 `parent` 为 id |
| **P-04** | 模型调用 span | `langchain_core/tracers/base.py:61`（`on_chat_model_start`）· `:108`（`on_llm_start`） | 鸭子类型模型对象经生产接缝调用 ⇒ 模型 span（`gen_ai.operation.name=chat`） | **DIFF** | 上游依赖 `langchain-core` + tracer handler；freegraph 零 LangChain、零依赖 ⇒ 自研区 ①③ |
| **P-05** | 工具调用 span | `langchain_core/tracers/base.py:363`（`on_tool_start`）· `:408`（`on_tool_end`） | 鸭子类型工具对象经生产接缝调用 ⇒ 工具 span（`gen_ai.operation.name=execute_tool`） | **DIFF** | 同上 ⇒ 自研区 ①③ |
| **P-06** | span 字段面 | `langsmith/run_trees.py:403-409`（`RunTree`：`run_type` / `start_time` 等）· `:689`（`end_time`） | **11 字段逐字冻结**（B2F1）：`id` / `name` / `attributes` / `parent` / `start_time` / `end_time` / `context` + 四项关联键；**无** `run_type` / `events` / `status` 字段 | **DIFF** | 字段面归 B2F1（本 feature MUST NOT 增删）；`run_type` 的语义由 `name` + `attributes` 表达 |
| **P-07** | 默认关闭是否受环境变量影响 | `langchain_core/tracers/context.py:141-144`（`_tracing_v2_is_enabled` 回落 `ls_utils.tracing_is_enabled()`）· `langsmith/utils.py:119-140`（最终读取 `TRACING_V2` / `TRACING` 环境变量） | **只认显式传入的 tracer**；MUST NOT 读任何环境变量；设置 `LANGSMITH_TRACING=true` 不改变行为 | **STRICTER** | 宪法原则 I / 配置层黑名单；freegraph 反 LangChain「key 存在即自动开 tracing」 |
| **P-08** | 运行时依赖闭包 | `langchain-core 1.7.6` 的 `Requires-Dist` 实测包含 `langsmith<1.0.0,>=0.14.9`（+ `certifi` / `httpx` / `pydantic` 等）· 实测 **E-4** | 基础安装依赖闭包**为空集**；无 `opentelemetry-*` / `langchain*` / `langsmith` | **STRICTER** | 宪法原则 I / II / IX；本项目产品承诺 |
| **P-09** | 失败路径仍观测到耗时 | `langchain_core/runnables/base.py:2366`（异常路径 `on_chain_error`）· `langchain_core/tracers/base.py:335`（`on_chain_error`）/ `:428`（`on_tool_error`）；实测 **E-3**（异常原样抛出、run 生命周期仍完成） | 异常时仍产出**同 id、已填 `end_time`** 的结束 span，然后原样重抛 | **SAME**（语义）· **DIFF**（表示） | 「失败也成对」是同一行为面；表示差异随 P-02 / P-06 |
| **P-10** | 节点 span 的属性命名空间 | 上游无「节点 span」概念；LangChain chain run 的属性是自由 `extra` / `metadata`（`langchain_core/tracers/base.py:61-105` 的 run 创建不约束键名） | 节点 span 属性为**空映射** | **DIFF** | Q6 §4.2 第 1 条允许自定义命名空间；B18F1 取更小的空映射（Q11）⇒ **X-3** |
| **P-11** | 输入 / 输出内容采集 | `langsmith/schemas.py:284-285`（RunBase 的 `inputs` / `outputs`）· `langsmith/run_trees.py:498-500`（自动补 `outputs`） | v1 默认不采集内容属性；只采结构化元数据 | **DIFF** | semconv 内容属性为 Opt-In；v1 取隐私 / 体积最小面 ⇒ **X-4** |

### §2 实测基线（E-1…E-4 · `langgraph 1.2.11` / `langchain-core 1.7.6` · 取证于 2026-11-20）

| # | 实验 | 结果 |
|---|---|---|
| **E-1** | 两节点线性图 `a → b`，**不传** `callbacks`，`app.invoke({"x":0})` | 正常返回 `{"x":2}`；**无任何** callback 事件 |
| **E-2** | 同图，传入自定义 `BaseCallbackHandler` | 共 **6 条**事件：图 run 开始 → 节点 a 开始 / 结束 → 节点 b 开始 / 结束 → 图 run 结束；两个节点 run 的 `parent_run_id` 均 == 图 run 的 `run_id` |
| **E-3** | 两节点图 `a → boom`（`boom` 抛 `RuntimeError("boom")`），传入自定义 handler | 异常原样抛出（`RuntimeError: boom`）；handler 事件序列 = `start`（图）→ `start`（a）→ `end`（a）→ `start`（boom）→ `error`（boom）→ `error`（图）⇒ **异常路径仍完成 run 生命周期** |
| **E-4** | 检查 `importlib.metadata.requires("langchain-core")` | 包含 `langsmith<1.0.0,>=0.14.9`（以及 `certifi` / `httpx` / `pydantic` / `pyyaml` 等）；`langsmith` 实测版本 `0.14.17` |

> **实测脚本**：`/tmp/upstream_probe.py`（E-1 / E-2）· `/tmp/upstream_probe_exc.py`（E-3）（本轮临时脚本 · **不进仓库**）；E-4 为 `importlib.metadata` 实测。
> **上游源码参照**：`langgraph/pregel/_retry.py:617` · `langgraph/pregel/main.py:2919` ·
> `langchain_core/runnables/base.py:2344,2366,2369` · `langchain_core/callbacks/manager.py:510,532,623` · `langchain_core/tracers/base.py:47,53,61,108,335,363,408,428` ·
> `langchain_core/tracers/context.py:141-144` · `langsmith/utils.py:119-140` · `langsmith/run_trees.py:403-409,498-500,689` · `langsmith/schemas.py:284-285`。

### §3 差分场景组 *(mandatory)*

> 编号段 **D-201…D-208**（避开 B8F2 的 D-121…D-136 与更早的编号段）。

| # | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 |
|---|---|---|---|
| **D-201** | 无 tracer / 无 handler | freegraph：span 构造数 == 0；上游：callback 事件数 == 0；两侧图都正常完成 | SAME（P-01） |
| **D-202** | 两节点线性图 | freegraph：2 个节点 span；上游：2 组节点 callback；两侧最终状态逐字相等 | SAME（行为面）· DIFF（表示，P-02） |
| **D-203** | 节点 → 工具 → 模型嵌套 | freegraph：模型 span 的 parent == 工具 span id，工具 span 的 parent == 节点 span id；上游：对应 run 的 `parent_run_id` 逐层正确 | SAME（父链语义）· DIFF（表示，P-03） |
| **D-204** | 模型 / 工具属性键 | freegraph：模型 / 工具属性键**除失败时的 `error.type` 外** 100% 命中 `gen_ai.*` 允许清单；上游：属性由 LangSmith run 的 inputs / outputs / extra 表达 | DIFF（P-04 / P-05） |
| **D-205** | 环境变量 | 设置 `LANGSMITH_TRACING=true` 且不传 tracer：freegraph span 数 == 0；上游可能自动开启 tracer | STRICTER（P-07） |
| **D-206** | 异常节点 | freegraph：结束 span 仍产生、异常原样重抛；上游：`on_chain_error` 仍触发、异常原样重抛 | SAME（P-09） |
| **D-207** | 依赖闭包 | freegraph 基础安装闭包为空；上游 `langchain-core` 闭包含 `langsmith` | STRICTER（P-08） |
| **D-208** | 并发 3 节点 | freegraph：3 个独立节点 span、无跨任务父子；上游：3 组节点 run、`parent_run_id` 均相同 | SAME（并发独立）· DIFF（表示） |

⇒ **判词分布**：**SAME 行为面 5**（D-201 / D-202 / D-203 / D-206 / D-208；其中 **D-202 / D-203 / D-208 同时含表示层 DIFF**）+ **纯 DIFF 1**（D-204）+ **STRICTER 2**（D-205 / D-207）。

### §4 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **DIFF**（自研区 ③：上游没有的能力） | 上游无自有 `Span` 数据类、无自有「节点 / 工具 / 模型」三级 span 生产协议（对应 **P-02 / P-03 / P-04 / P-05 / P-06 / P-09**） | freegraph 的可观测协议必须自研（C23 / C24），且字段面已由 B2F1 冻结；上游的对应物是 LangChain callback + LangSmith `RunTree`，引入即破零依赖红线 | B2F1（字段面）· 本 feature（生产） |
| **X-2** | **STRICTER**（自研区 ①：零账号 / 零主动出站 / 零依赖） | 上游 tracing 由 `langchain-core` + `langsmith` 承载，且可由环境变量自动开启（对应 **P-07 / P-08**） | freegraph MUST 零第三方依赖、零环境变量、零主动出站；只认显式传入的 tracer | 宪法原则 I / II / IX · 本 feature |
| **X-3** | **DIFF**（自研区 ③：上游没有的能力） | 节点 span 的属性面（对应 **P-10**） | 节点执行不是 GenAI 模型 / 工具操作；Q6 §4.2 允许自定义命名空间，B18F1 按 Q11 取更小的**空映射** | 本 feature |
| **X-4** | **DIFF**（自研区 ③：上游没有的能力） | 默认不采集输入 / 输出内容（对应 **P-11**） | semconv 的 Opt-In 内容属性含敏感信息；v1 只采结构化元数据，避免隐私与体积风险 | 本 feature |

### §5 破冻结面的回溯修订清单 *(本 feature 触发)*

**本 feature 不破任何冻结面。** 具体：

- `Span` 的 11 字段 **零改动**（B2F1）；
- `TraceSink` 协议 **零改动**（B2F1；接入归 B19F1）；
- `SuperStepResult` 四字段 / `PregelTask` 七字段 / `RunConfig` 九字段 / 公开门面符号数 **零改动**；
- `stream()` 事件信封 **零改动**；`_STREAM_RUN_ID` / `_STREAM_THREAD_ID` 在 **stream 路径**由 `StreamSession` 绑定、B18F1 **只读**；**invoke 路径**由 L2 私有助手 `bind_run_ids` 绑定**同一对** contextvar（**不新增第二套载体**；`bind_stream` 仍是 `StreamSession` 的唯一绑定入口）；
- 节点签名、状态语义、别名移除成果 **零改动**。

---

## Requirements *(mandatory)*

### Functional Requirements

#### A. 数据面与生产开关

- **FR-001**：系统 MUST 以 **B2F1 冻结的 `Span`（11 字段）** 作为唯一 span 载体；该类型 MUST 是 freegraph **自有、零第三方依赖**的数据类（L1），MUST NOT 用 OTel SDK 的 span 对象替代；MUST NOT 新增 / 删除 / 改名 / 改类型 / 改缺省任何字段；MUST NOT 定义第二个 span 类型。字段面权威 = `specs/b2f1-contracts-protocols/contracts/public-api.md` §1.2。
- **FR-002**：span 生产 MUST **默认关闭**。未启用生产时：MUST NOT 构造任何 `Span` 对象、MUST NOT 构造 span 中间载体、MUST NOT 调用任何接收端回调、MUST NOT 为 span 生产分配 / 绑定 `run_id`、MUST NOT 读环境变量。**`stream()` 既有的事件 `run_id` 由 B8F2 独立生成，不属于 span 生产**。允许每次节点执行做**一次**廉价布尔判断。
- **FR-003**：span 生产 MUST 由**显式传入的 tracer（`SpanProducer`）/ receiver** 启用；MUST NOT 由任何环境变量、配置文件、API key 的存在自动启用。启用范围 MUST 是**一次运行**（run-scoped）：注入方（B19F1 / 测试）MUST 用作用域（context manager 或等价机制）绑定，作用域内所有 span 共享同一 `run_id`，作用域结束即不再产生 span；MUST 同时覆盖 `invoke()` 与 `stream()` 两条入口。
- **FR-004**：系统 MUST 在**每一次节点任务执行**时产生一个节点级 span（含 `Send` fan-out 产生的每个任务）；开始于节点函数调用前，结束于节点函数返回 / 抛异常后。MUST NOT 改变节点签名、状态入参形状、`SuperStepResult` 字段、`PregelTask` 字段。
- **FR-005**：系统 MUST 在节点通过 **`invoke_model(obj, input, *, call_id=None)` / `invoke_tool(obj, args, *, call_id=None)` 一次性调用辅助**调用模型 / 工具时，产生**独立的**模型级 / 工具级 span（不是节点 span 的别名、不是埋在节点 span 属性里）。MUST NOT 要求用户继承基类或 import LangChain；MUST NOT 隐式拦截节点里的任意 `.invoke` 调用。**在形状校验通过后**，若**没有活动节点 span**（即不在节点执行期间），辅助函数 MUST 等价于直接调用 `obj.invoke(...)`：**不产生 span、不伪造 `node`、零副作用**（Q13）。形状校验收 Q14 约束，即使生产关闭也照常执行；异步对象按 FR-028 / Q16 拒绝。
- **FR-006**：模型 / 工具的识别 MUST 基于**属性存在性**（鸭子类型），且**只对传入 `invoke_model` / `invoke_tool` 的对象**生效；辅助函数名决定期望层级，形状不匹配 MUST 抛出内置 `TypeError`（Q14）：
  1. **工具形状**：对象具备 `name`（`str`）+ callable `invoke` + `description`（存在即可，值可为任意）；
  2. **`invoke_tool(obj, ...)`**：要求工具形状；否则 `TypeError`；
  3. **`invoke_model(obj, ...)`**：要求 callable `invoke` **且非工具形状**；否则 `TypeError`；
  4. MUST NOT import / isinstance 检查 `langchain` / `langchain-core` 类型；MUST NOT 静默把工具当模型或反之。
- **FR-007**：父子关系 MUST 通过 `Span.parent`（**父 span 的 `id` 字符串**）表达：
  - 节点 span 的 `parent` = 创建它时**最内层活动 span** 的 `id`；顶层节点为 `None`；
  - 模型 / 工具 span 的 `parent` = 创建它时**最内层活动 span** 的 `id`（通常是所在节点 span；嵌套时可为工具 / 模型 span）；
  - MUST NOT 使用对象引用作为 parent（JSON 可序列化前提）。
- **FR-008**：每个 span 的 `id` MUST 在运行内唯一（标准库生成）；MUST NOT 复用 / 硬编码；MUST NOT 依赖 OTel SDK。
- **FR-009**：span MUST 记录起止时间：`start_time` / `end_time` 为 **UTC ISO-8601 字符串**；时间源 MUST 为标准库；**耗时必须严格大于 0**（含纯计算 / 极快调用）。未结束时 `end_time` 为空；结束时 MUST 填值。
- **FR-010**：异常路径下 MUST 产出**同 `id`、已填 `end_time`** 的结束 span，然后**原类型 + 原消息 + 原对象**重新抛出；MUST NOT 包装 / 吞掉 / 改变异常。开始快照 MUST NOT 被事后改写（B2F1 冻结生命周期：开始 = `end_time` 为空的新实例，结束 = 同 id、已填 `end_time` 的新实例）。

#### B. 关联键与运行标识

- **FR-011**：每个 span MUST 携带并可读四项关联键：
  - `run_id`：**非空**；单次运行内所有 span 共享同一值；
  - `thread_id`：来自 `RunConfig` 的**生效值**（`resolved_thread_id()`）；可为 `None`；
  - `node`：**所属图节点名**（内部名；alias 已移除）；模型 / 工具 span 也填所在节点名；
  - `checkpoint_id`：运行期有当前 checkpoint 标识时填值，否则 `None`；MUST NOT 伪造。**模型 / 工具 span 从当前节点 span 继承该值**。
  **缺 `run_id`（空串 / `None`）的 span 视为实现缺陷**（C23 / D11）。
- **FR-012**：`run_id` / `thread_id` MUST 与 `stream()` 事件**同源同 id**：
  - `stream()` 路径：MUST 读取 L2 私有 contextvar `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`（B8F2 D-3），MUST NOT 另生成；
  - `invoke()` 路径：优先复用运行期已绑定的同一对值；未绑定时，仅在 span 生产启用期间建立**一个** run-scoped `run_id`（经 `bind_run_ids` 写入**同一对** contextvar），并在该次运行全部 span 中复用；
  - `RunConfig.run_id` MUST 被**忽略**（宪法 v1.15.2）；用户不可设置 / 覆盖；
  - 未启用生产时 MUST NOT 生成 / 绑定任何 **span 专用**运行标识。
- **FR-013**：模型 / 工具 span 的 `attributes` 键 MUST **⊆** 下节「`gen_ai.*` 属性允许清单」中标注 **✅ 写**的子集（**唯一例外**：**模型 / 工具 span** 失败时 FR-018 的 `error.type`）；允许清单中标注 **❌ 不写**的键在 v1 MUST NOT 出现；节点 span 的 `attributes` MUST 为**空映射**（v1 不附加 `freegraph.*` 结构属性；Q11）；MUST NOT 出现无命名空间的私有键。**v1 只写「最小集」**（见裁定 Q9）：模型 span 仅 `gen_ai.operation.name` + `gen_ai.request.model`；工具 span 仅 `gen_ai.operation.name` + `gen_ai.tool.name` + `gen_ai.tool.call.id`（调用方提供时）。其余 semconv 属性在 v1 **MUST NOT** 写入。
- **FR-014**：所有属性值 MUST 可被标准库 `json.dumps` 直接序列化（`str` / `int` / `float` / `bool` / `None` / 由这些组成的 list / dict）；MUST NOT 放任意对象、异常对象、datetime、bytes、模型 / 工具实例。
- **FR-015**：span 的 `name` MUST 遵循：
  - 节点 span：**节点内部名**（与 `stream()` / `PregelTask.name` 一致）；
  - 工具 span：`execute_tool <gen_ai.tool.name>`（semconv 推荐格式）；
  - 模型 span：`<gen_ai.operation.name> <gen_ai.request.model>`（模型名可读时）；模型名不可读时仅 `<gen_ai.operation.name>`。
- **FR-016**：模型 span 的 `gen_ai.operation.name` 在 v1 **恒为 `chat`**；工具 span 恒为 `execute_tool`。**MUST NOT** 读取对象上的其它 operation 提示（`text_completion` / `embeddings` 等留待后续 feature）；MUST NOT 猜测。该值只用于**已被判定为模型**的对象，不改变「freegraph 是通用图框架」的定位。`gen_ai.request.model` 的取值顺序：`model_name` → `model`；两者都不可读 / 为空时**省略该属性**，MUST NOT 猜测。
- **FR-017**：v1 **MUST NOT** 默认采集内容类属性：`gen_ai.input.messages` / `gen_ai.output.messages` / `gen_ai.system_instructions` / `gen_ai.tool.call.arguments` / `gen_ai.tool.call.result` / `gen_ai.tool.definitions`。若未来提供采集，MUST 由显式配置控制（不读环境变量），默认档 = 不采集。
- **FR-018**：**模型 / 工具 span** 失败时 MUST 写 `error.type`（OTel general `recording-errors`，非 `gen_ai.*`）；值 MUST 为低基数异常类名（`type(exc).__name__`；为空时用 `_OTHER`）；这是允许的唯一非 gen_ai 键；**节点 span MUST NOT 写 `error.type`**（Q12）；成功时任何 span 都 MUST NOT 出现。MUST NOT 写已弃用的 `gen_ai.system`；provider 标识只用 `gen_ai.provider.name`。

#### C. 零开销、依赖与分层

- **FR-019**：MUST NOT 引入 `opentelemetry-*` / `langchain*` / `langsmith` / 任何第三方运行时依赖；基础安装依赖闭包 MUST 仍为空集。
- **FR-020**：span 生产与模块导入 MUST NOT 读取任何环境变量（含 `LANGSMITH_*` / `LANGCHAIN_*` / `OTEL_*`）；MUST NOT 发起任何出站请求。
- **FR-021**：B18F1 的 L5 模块 MUST 只 import 标准库 + L1；MUST NOT 让 L5 横向 import L2–L4 的业务模块；跨层耦合 MUST 只经由 L1 协议 + 纯数据。**唯一例外**（已在 B8F2 的 ARCH-3 R-6 登记）：只读 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID` 两个 `str | None` 元数据；**本 feature 不使用该例外**（L5 从当前节点 span 继承 id，零 L2 import）；MUST NOT 扩展为任意 L5 → L2 私有依赖，MUST NOT 把 trace 数据塞进 `stream()` 信封。
- **FR-022**：B18F1 MUST NOT 扩大公开门面符号数 / L1 契约符号数；`invoke_model` / `invoke_tool` / `SpanProducer` MUST 位于 L5 自有模块（**非公开门面**，可直接 import；是否由 B19F1 再导出由 B19F1 决定）；`import freegraph` 后 MUST NOT 加载 L5 生产模块（保持 ARCH-2 的惰性）。
- **FR-023**：`Span.context` 在 v1 MUST **恒为空映射**（Q15）；MUST NOT 承载 C21 的 `context`（`RunConfig.context` / 节点 state context），MUST NOT 被辅助函数 / 节点 / 接收端填入任何附加元数据。MUST NOT 回退到 `configurable` 承载 context，MUST NOT 重新引入节点别名（B8F3 D-2 / D-3）。
- **FR-024**：并发安全：同一 super-step 内并发执行的多个节点，各自的当前 span 栈 MUST 独立；MUST NOT 出现跨任务的父子关系；线程池传播 MUST 沿用 B8F2 的每任务 `copy_context()` 机制，MUST NOT 新立第二套上下文传播。
- **FR-025**：接收端（receiver）回调抛出的异常 MUST 被**隔离**：MUST NOT 传播到节点 / 图执行、MUST NOT 改变 `invoke()` / `stream()` 的输出、MUST NOT 吞掉节点自身的异常、MUST NOT 造成永久挂起。该次可观测写入 MAY 被丢弃；MAY 通过标准库 `logging` 记录一次警告（上游同款 · `langchain_core/callbacks/manager.py:351-354`）；MUST 有可测判据（由 SC-007 覆盖）。
- **FR-026**：B18F1 MUST NOT 实现 `TraceSink` 的公开注入与推送、`current_span()`、trace 存储、OTLP 导出、前端 UI；这些分别归 B19F1 / B20F1 / B20F2 / B21F1 / v2。
- **FR-027**：B18F1 的开始 / 结束 span（两个同 id 实例）MUST 能被 B19F1 原样消费（D-1）；B18F1 MUST NOT 要求 B19F1 重新实现生产或改字段。
- **FR-028**：v1 **只支持同步** `invoke`。`invoke_model` / `invoke_tool` 调用对象后，若结果为 awaitable（`inspect.isawaitable(result)` 为真），MUST：① 结束当前 span（同 `id`、已填 `end_time`，失败时按 FR-018 MUST 写 `error.type`）；② 抛内置 `TypeError`；③ MUST NOT 把 awaitable 返回给调用方。MUST NOT 提供 `ainvoke_model` / `ainvoke_tool` 等异步辅助（Q16）。
- **FR-029**：系统 MUST 按「原则 IV 的字段载体映射」明确：节点名 / 耗时由 B18F1 节点 span 承担；输入状态 / 输出状态 / 错误由既有 `stream()` 事件（`values` / `updates` / `tasks`）+ `PregelTask.result` + 原样抛出的异常 + B19F1/B20 承接（`PregelTask.error` 仅在非抛出快照 / 中断路径可见）；节点 span 的 `attributes` MUST 保持空映射，MUST NOT 因该原则把输入 / 输出 / 错误塞进节点 span。B19F1/B20 的承接条款 MUST 补齐 `invoke()` 路径的逐节点记录，并写死承接机制。

### `gen_ai.*` 属性允许清单（含 semconv 出处）

> **证据门禁**：本表的每个键 MUST 附 semconv 出处。来源仓库：
> `open-telemetry/semantic-conventions-genai`（Apache-2.0；2026-11-20 取 `main` 分支文档）。
> 具体文件：
> - `docs/gen-ai/gen-ai-spans.md`（GenAI spans 总览 / 内容采集 / 错误记录）
> - `docs/gen-ai/client-inference.md`（推理 span 与属性）
> - `docs/gen-ai/execute-tool.md`（工具执行 span）
> - `docs/registry/attributes/gen-ai.md`（属性注册表）
> - `docs/general/recording-errors.md`（通用 `error.type`，非 gen_ai）

#### 模型级 span（v1 恒 `gen_ai.operation.name = chat`）

| 键 | 值类型 | semconv 等级 | v1 是否写 | 何时写 | 出处 |
|---|---|---|---|---|---|
| `gen_ai.operation.name` | string | Required | ✅ **写** | **总是**（v1 **恒为 `chat`**；MUST NOT 读取对象上的其它 operation 提示） | `gen-ai-spans.md` / `registry/attributes/gen-ai.md` |
| `gen_ai.request.model` | string | Required（可读时） | ✅ **写** | 对象暴露 `model_name` 或 `model` 时 | `client-inference.md` |
| `gen_ai.provider.name` | string | Conditionally Required | ❌ 不写 | v1 不采集 | `gen-ai-spans.md` / `client-inference.md` |
| `gen_ai.response.model` | string | Recommended | ❌ 不写 | v1 不采集 | `client-inference.md` |
| `gen_ai.response.id` | string | Recommended | ❌ 不写 | v1 不采集 | `client-inference.md` |
| `gen_ai.response.finish_reasons` | string[] | Recommended | ❌ 不写 | v1 不采集 | `client-inference.md` |
| `gen_ai.usage.input_tokens` | int | Recommended | ❌ 不写 | v1 不采集 | `client-inference.md` |
| `gen_ai.usage.output_tokens` | int | Recommended | ❌ 不写 | v1 不采集 | `client-inference.md` |
| `gen_ai.request.temperature` | double | Recommended | ❌ 不写 | v1 不采集 | `client-inference.md` |
| `gen_ai.request.max_tokens` | int | Recommended | ❌ 不写 | v1 不采集 | `client-inference.md` |
| `gen_ai.request.top_p` | double | Recommended | ❌ 不写 | v1 不采集 | `client-inference.md` |
| `gen_ai.conversation.id` | string | Conditionally Required | ❌ 不写 | v1 不采集 | `client-inference.md` |

> **v1 最小集**（裁定 Q9 · 用户拍板）：模型 span 只写 `gen_ai.operation.name` 与 `gen_ai.request.model`。
> 其余 `gen_ai.*` 键虽在 semconv 中存在，但 v1 **MUST NOT** 写入；需要时由后续 feature 另行论证。
>
> **不写**：`gen_ai.system`（已弃用 ⇒ 用 `gen_ai.provider.name`）；`gen_ai.input.messages` / `gen_ai.output.messages` / `gen_ai.system_instructions`（Opt-In；v1 不采集）。

#### 工具级 span（`gen_ai.operation.name = execute_tool`）

| 键 | 值类型 | semconv 等级 | v1 是否写 | 何时写 | 出处 |
|---|---|---|---|---|---|
| `gen_ai.operation.name` | string | Required | ✅ **写** | **总是**（值 `execute_tool`） | `execute-tool.md` / `registry/attributes/gen-ai.md` |
| `gen_ai.tool.name` | string | Required | ✅ **写** | **总是**（来自工具对象的 `name`；空串也写，不省略） | `execute-tool.md` |
| `gen_ai.tool.call.id` | string | Conditionally Required | ✅ **写** | 调用方提供 tool call id 时 | `execute-tool.md` |
| `gen_ai.tool.description` | string | Recommended | ❌ 不写 | v1 不采集（隐私最小面） | `execute-tool.md` |
| `gen_ai.tool.type` | string | Recommended | ❌ 不写 | v1 不采集 | `execute-tool.md` |
| `gen_ai.conversation.id` | string | Conditionally Required | ❌ 不写 | v1 不采集 | `execute-tool.md` |

> **v1 最小集**（裁定 Q9 · 用户拍板）：工具 span 只写 `gen_ai.operation.name`、`gen_ai.tool.name`、`gen_ai.tool.call.id`（调用方提供时）。
>
> **不写**：`gen_ai.tool.call.arguments` / `gen_ai.tool.call.result`（Opt-In；v1 不采集）。

#### 节点级 span（v1 恒为空映射）

| 键 | 值类型 | v1 是否写 | 何时写 | 出处 |
|---|---|---|---|---|
| 空映射 | — | ✅ **恒为空** | v1 不附加任何节点结构属性 | Q11（用户拍板）· Q6 §4.2 第 1 条允许自定义命名空间，B18F1 取更小的空映射 |
| `freegraph.*`（superstep / task id / 触发源等） | — | ❌ 不写 | 归 B19F1 的承接范围 | Q11 |

#### 通用（模型 / 工具失败时唯一例外）

| 键 | 值类型 | semconv 等级 | v1 是否写 | 何时写 | 出处 |
|---|---|---|---|---|---|
| `error.type` | string | Conditionally Required | ✅ MUST · 仅模型 / 工具失败时 | **仅模型 / 工具 span 失败时 MUST 写**；低基数错误类名。节点 span MUST NOT 写 | `docs/general/recording-errors.md`（OTel general，非 gen_ai） |

### Key Entities *(include if feature involves data)*

- **`Span`**：B2F1 冻结的不可变数据类（`frozen=True` / `slots=True` / `kw_only=True`）；11 字段；`attributes` / `context` 浅拷贝；**字段经 `dataclasses.asdict(span)` 后 100% JSON 可序列化**。本 feature **只构造 / 填充**，不重定义；其中 `context` 在 v1 恒为空映射（Q15）。
- **节点级 span**：`name == node`、`node == 节点名`、`parent` 为当前最内层 span id 或 `None`；属性为**空映射**（v1 不附加结构属性）。
- **模型级 span**：`name = <operation> <request.model>`（或仅 operation）；`parent = 节点 / 内层 span id`；属性只含 `gen_ai.operation.name` + `gen_ai.request.model`（v1 最小集）。
- **工具级 span**：`name = execute_tool <tool.name>`；`parent = 节点 / 内层 span id`；属性只含 `gen_ai.operation.name` + `gen_ai.tool.name` + `gen_ai.tool.call.id`（调用方提供时）。
- **生产接缝（tracer / 接收端）**：显式传入、run-scoped、默认关闭；开始 / 结束两个生命周期快照；由 B19F1 对接 `TraceSink`。**不是**公开门面符号。
- **调用辅助**：`invoke_model(obj, input, *, call_id=None)` / `invoke_tool(obj, args, *, call_id=None)`（L5 非门面符号）；只对主动传入的对象产生子 span，不隐式拦截任意 `.invoke`。
- **鸭子类型对象**：模型 = callable `invoke` 且非工具形状；工具 = `name`（str）+ `description` + callable `invoke`；由 `invoke_model` / `invoke_tool` 的**函数名**决定期望层级，形状不匹配抛 `TypeError`（Q14）。
- **运行关联键**：`run_id`（运行时生成、单次运行一个）· `thread_id`（`RunConfig` 生效值）· `node`（内部节点名）· `checkpoint_id`（有则填、无则 `None`）。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：模型 / 工具 span 的 `attributes` 键 MUST **⊆** 「`gen_ai.*` 属性允许清单」中标注 **✅ 写**的子集（**模型 / 工具失败时 MUST 写** FR-018 的 `error.type`，作为唯一例外）；允许清单中标注 **❌ 不写**的键出现次数 == 0；节点 span 的 `attributes` **恒为空映射（成功与失败都一样）**；`gen_ai.system` 出现次数 == 0；无命名空间私有键出现次数 == 0。判定：对每种 span 的键集合与**✅ 写子集**做集合包含比对 + 负向键断言。
- **SC-002**：一个场景内节点 / 工具 / 模型**三级 span 各至少 1 例**；模型 / 工具 span 的 `parent` 100% 等于其所属节点 / 内层 span 的 `id`；节点 span 的 `parent` 为 `None` 或内层 span id。判定：父子断言 + 层级计数。
- **SC-003**：未启用 span 生产时，`Span` 构造数 == 0、接收端回调调用数 == 0、**span 专用 `run_id` 生成 / 绑定数 == 0**。判定：计数夹具（构造计数 / 回调计数 / id 绑定计数）。**`stream()` 既有事件 `run_id` 不计入**。
- **SC-004**：基础安装依赖闭包**为空集**；`opentelemetry` / `langchain` / `langsmith` 的 import 次数 == 0；环境变量读取次数 == 0。判定：依赖闭包断言 + AST / 运行时守卫。
- **SC-005**：每个已结束 span 的 `end_time` 非空且 `end_time > start_time`（**严格大于 0**）；同一 span 的开始 / 结束 `id` 相同。判定：逐 span 断言。
- **SC-006**：每个 span 的 `run_id` **非空**；`thread_id` == `RunConfig` 的生效 `thread_id`；`node` == 所属节点内部名；`checkpoint_id` 字段可读（有值或 `None`，模型 / 工具 span 与节点 span 一致）。`run_id` 为空的数量 == 0。
- **SC-007**：异常路径下，开始 / 结束 span **成对**（同 id、结束有 `end_time`）；抛出的异常对象与未启用生产时**类型 / 消息 / 对象一致**；异常被吞掉 / 包装的次数 == 0。**接收端（receiver）回调抛异常时**：MUST 被隔离、不改变 `invoke()` / `stream()` 输出、不吞节点异常、不永久挂起；当前 span 栈仍保持平衡（该次可观测写入 MAY 被丢弃）。
- **SC-008**：所有产出 span 的**字段**（`dataclasses.asdict(span)`）可被标准库 `json.dumps` 序列化；`attributes` / `context` / 时间 / `parent` 不含不可序列化对象。失败数 == 0。
- **SC-009**：span 名格式符合：节点 span `name == node`；工具 span `name == execute_tool {tool_name}`；模型 span `name == {operation} {request_model}` 或 `{operation}`。不符数 == 0。
- **SC-010**：并发 N 个节点（N ≥ 3）⇒ N 个节点 span；每个节点的模型 / 工具 span 的 `parent` MUST 落在**本节点 span 的子树内**（直接子 span = 节点 span id；嵌套子 span = 本任务内内层 span id）；跨任务父子数 == 0。
- **SC-011**：C21 隔离：任何 span 的 `context` **恒为空映射**（不含 `RunConfig.context` / 节点 state context / 自定义元数据）；节点别名回归用例仍抛 `TypeError`；`stream()` 的节点名不因本 feature 改变。违反数 == 0。
- **SC-012**：公开门面符号数**不变**；`import freegraph` 后 `sys.modules` 不含 L5 生产模块；新增公开符号数 == 0。
- **SC-013**：在节点执行之外调用形状匹配的 `invoke_model` / `invoke_tool`，span 构造数 == 0，返回值与直接调用 `obj.invoke(...)` 逐字相等，且不抛异常（对象本身不抛时）。判定：节点外调用夹具 + 计数断言。
- **SC-014**：形状不匹配时，`invoke_model` / `invoke_tool` MUST 抛内置 `TypeError`，且**模型 / 工具 span 构造数 == 0**（节点 span 不受影响）；不得静默产出错误层级 span。判定：4 个错配用例（工具→model、模型→tool、无 invoke→model、无工具形状→tool）。
- **SC-015**：对象的 `invoke` 返回 awaitable 时，辅助函数 MUST 抛内置 `TypeError`，MUST NOT 返回 awaitable；若生产已启用，MUST 仍产出**成对**的结束 span（同 id、已填 `end_time`）。判定：awaitable 夹具 + 返回类型断言 + span 成对断言。
- **SC-016**：原则 IV 的字段载体可判定：`stream()` 路径的节点名 / 耗时由 span 承担；输入状态 / 输出状态由 `values` / `updates` / `tasks` + `PregelTask.result` 还原；**错误由原样抛出的异常**（并发其它失败见 `add_note`）还原；`PregelTask.error` **不作为失败路径载体**。`invoke()` 路径的逐节点三项有 **B19F1/B20** 的具名承接 + 承接机制；节点 span 的 `attributes` 仍为空映射。判定：carrier 回归测试 + 承接机制存在性检查。

### 验收判据（= 立项书 §5.2 B18F1 小目标 · 逐条可判定）

> 小目标原文：span **属性命名**符合 OTel GenAI semconv；未注入 tracer 时零副作用、零开销。

| # | 判据 | 判定方式 | 对应 SC |
|---|---|---|---|
| **A1** | span 属性命名符合 OTel GenAI semconv | 属性键集合 vs 允许清单的 **✅ 写子集**逐项比对（附 semconv 出处）；模型 / 工具 100% `gen_ai.*`（失败时 MUST 写唯一例外 `error.type`），节点恒为空映射 | SC-001 / SC-009 |
| **A2** | 未注入 tracer 时零副作用、零开销 | span 构造计数 == 0；回调计数 == 0；依赖闭包无变化；无环境变量读取 | SC-003 / SC-004 / SC-012 |
| **A3** | 三级 span 可产生 | 节点 / 工具 / 模型各一例；父子关系正确 | SC-002 / SC-010 |

### 追溯表（FR → SC）

| FR | 覆盖 SC |
|---|---|
| FR-001 | SC-002 / SC-008 / SC-012 |
| FR-002 | SC-003 / SC-004 / SC-012 |
| FR-003 | SC-003 / SC-006 |
| FR-004 | SC-002 / SC-009 / SC-010 |
| FR-005 | SC-002 / SC-009 / SC-010 / SC-013 |
| FR-006 | SC-001 / SC-009 / SC-013 / SC-014 |
| FR-007 | SC-002 / SC-010 |
| FR-008 | SC-002 / SC-005 |
| FR-009 | SC-005 / SC-008 |
| FR-010 | SC-007 |
| FR-011 | SC-006 / SC-008 |
| FR-012 | SC-006 |
| FR-013 | SC-001 |
| FR-014 | SC-008 |
| FR-015 | SC-009 |
| FR-016 | SC-001 / SC-009 |
| FR-017 | SC-001 |
| FR-018 | SC-001 / SC-007 |
| FR-019 | SC-004 |
| FR-020 | SC-004 |
| FR-021 | SC-004 / SC-012 |
| FR-022 | SC-012 |
| FR-023 | SC-011 |
| FR-024 | SC-010 |
| FR-025 | SC-007 |
| FR-026 | SC-012 |
| FR-027 | SC-002 / SC-008 |
| FR-028 | SC-015 |
| FR-029 | SC-016 |

> 每条 SC 至少挂一条**能判定它的测试任务**（宪法原则 VI）；具体任务在 `/speckit.tasks` 阶段落成，MUST NOT 用实现任务冒充判据覆盖。

---

## Assumptions

- **`Span` 字段面已冻结**：11 字段、`frozen=True`、`slots=True`、`kw_only=True`、`attributes` / `context` 浅拷贝、不可哈希；**字段经 `dataclasses.asdict(span)` 后 100% JSON 可序列化**（B2F1）。本 feature 的测试以该类型为准，不另建测试替身。
- **节点执行是唯一自动生产点**：模型 / 工具调用必须发生在节点执行期间（图运行内核的语义）；若对象在节点外通过接缝调用，MUST NOT 产生 span（Q13；不在本 feature 的验收范围）。
- **「tracer」= `SpanProducer`，「receiver」= 接收端**：B18F1 的测试通过内部接缝注入 `SpanProducer` + 计数 / 捕获 receiver；其公开注入形态由 B19F1 决定。提示词中「注入 tracer 后」按此口径理解。
- **模型 / 工具调用必须显式经 `invoke_model` / `invoke_tool`**：B18F1 **不**隐式拦截节点里的任意 `.invoke`；未被辅助函数包裹的调用不产生模型 / 工具 span（这是通用图框架的刻意边界，避免误判）。
- **节点外调用辅助函数 = 直接调用**：形状校验通过且没有活动节点 span 时不产生 span（Q13）；`Span.node` 始终是真实节点名。
- **辅助函数名即意图**：`invoke_model` / `invoke_tool` 不互相自动改判；形状不匹配一律 `TypeError`（Q14），即使生产关闭也照常校验。
- **`Span.context` 是保留字段**：v1 恒为空映射（Q15）；未来若需要承载附加元数据，必须先立契约定义来源与格式，MUST NOT 偷偷塞入 C21 的 `context`。
- **v1 只支持同步调用**：`invoke_model` / `invoke_tool` 拒绝返回 awaitable 的对象（Q16）；异步辅助与异步 span 生命周期留给后续 feature。
- **原则 IV 的载体组合**：B18F1 的节点 span 只承担节点名 / 耗时；输入 / 输出 / 错误由 `stream()` 事件（`values` / `updates` / `tasks`）+ `PregelTask.result` + 原样抛出的异常 + B19F1/B20 承接（D-6 / FR-029）；`PregelTask.error` 不作为失败路径载体。节点 span 不因原则 IV 扩属性。
- **模型 / 工具的元数据可读性（裁定 Q9 · 极简）**：v1 只读 `gen_ai.request.model`（来源：对象的 `model_name` 或 `model` 属性）；provider / usage / response / finish_reasons / temperature / tool.description / conversation.id 等**一律不读、不写**。读不到模型名就**省略**，MUST NOT 猜测 / 伪造。LangChain 对象的内部属性（如 `_llm_type`）不在 v1 的承诺面内。
- **通用性优先**：freegraph 是**通用图框架**，不是专为 AI 智能体设计。模型 / 工具 span 是**可选的可观测能力**（由显式接缝启用），不得让通用图执行依赖任何 AI 语义；元数据面刻意保持最小集（裁定 Q9）。
- **节点 span 不带结构属性**：节点 span 的 `attributes` 恒为空映射（裁定 Q11）；superstep / task id / 触发源等由 B19F1 在调度层另行暴露，B18F1 不提前扩面。
- **`error.type` 只属于模型 / 工具失败**：节点 span 即使失败也保持空映射（裁定 Q12）；错误类信息只在模型 / 工具 span 上出现。
- **`checkpoint_id` 可能长期为 `None`**：B14F1 落地前没有 checkpoint 标识来源；这是合法现状，不构成缺陷。节点 span 接受运行期传入的值（v1 为 `None`），模型 / 工具 span 从当前节点 span 继承；B14F1 只需在既有接缝补**节点 span**（D-4）。
- **时间精度**：实现 MUST 保证严格正耗时；允许使用纳秒级时间源 / 高精度格式化（ISO-8601 支持任意小数位），不得伪造「+1µs」。
- **同一次运行的 `run_id`**：`stream()` 复用 B8F2 的绑定；`invoke()` 在生产启用期间建立一次。二者 MUST NOT 同时产生两个不同 id。
- **内容采集默认关闭**：v1 不提供内容属性；未来若提供，必须显式 opt-in，且不得读环境变量（与原则 I / 配置层黑名单一致）。
- **公开 API 面不扩大**：B18F1 的生产接缝私有；若 B19F1 需要公开注入 API，由其按「破冻结面三条」走流程。
- **上游版本**：`langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`；换版本 MUST 重新核实全部锚点（原则 XI）。
- **semconv 版本**：以 2026-11-20 `open-telemetry/semantic-conventions-genai` 的 `main` 文档为准；该仓库文档仍在演进（`Development` 状态），属性名若变更走契约修订 / 证据更新，不得静默漂移。

---

## Out of Scope

- `Span` 字段面的任何增删 / 改名（归 B2F1；变更走契约修订）。
- `TraceSink` 的公开注入点、`on_span_start` / `on_span_end` 推送、`current_span()`（**B19F1**）。
- 本地 trace 存储 / 查询（**B20F1 / B20F2**）。
- OTLP 导出 / `opentelemetry-*` 运行时（**B21F1**；v1 明确不采用）。
- 前端 UI / trace 浏览器（v2 / **B26**）。
- 「评测 / 数据集 / Annotation Queue / Prompt Hub」（永不做 · 立项书 §3.4）。
- 对任意 Python 函数体内部 `.invoke` 的透明拦截 / monkeypatch / `sys.settrace`。
- 异步 `invoke` / `ainvoke_model` / `ainvoke_tool` / 异步 span 生命周期（v1 只支持同步 · Q16）。
- 输入 / 输出消息内容采集（v1 默认关闭）。
- 图级 / run 级 span（本 feature 只有三级：节点 / 工具 / 模型）。
- 跨进程 / 跨会话的 trace 关联（v1 单进程定位）。

---

## 交付物与验收联动

| 交付物 | 落点 | 验收联动 |
|---|---|---|
| 节点 / 工具 / 模型三级 span 生产 | L5 可观测模块 + L2 单一节点执行接缝 | SC-002 / SC-009 / SC-010 |
| 鸭子类型识别 + `invoke_model` / `invoke_tool` 调用辅助 | L5 模块（不导出门面） | SC-001 / SC-009 |
| `gen_ai.*` 属性对照表（含 semconv 出处） | 本 spec「属性允许清单」+ README **独立「可观测属性」章节**（**MUST NOT** 改动 API 兼容矩阵） | SC-001 / A1 |
| 零开销计数夹具 | 测试夹具（构造计数 + 回调计数） | SC-003 / A2 |
| 依赖 / 环境变量守卫 | CI 静态断言 + 运行时守卫 | SC-004 / A2 |
| 关联键与 `run_id` 同源测试 | 单元 / 集成测试 | SC-006 / SC-011 |
| 并发父子关系测试 | 并发集成测试 | SC-002 / SC-010 |
| 异常成对测试 | 单元 / 集成测试 | SC-007 |
| 原则 IV 载体（stream 路径 + 承接文档守卫） | `tests/runtime/test_node_record_carriers.py` + `tests/contracts/test_trace_carrier_contract.py` | SC-016 |
| 一键验收脚本 | `harness/verification/B18F1/acceptance.py`（A1–A7） | 质量门禁 4 / A1–A3 |
| 人工验证记录 | `harness/verification/B18F1/manual-verification.md`（原则 V） | 质量门禁 5 |

> **人工门禁**：本 feature 的人工验证记录 MUST 含 fake / 真实两轮的实测输出（原则 V）；若真实轮无法跑（无模型 / 无网络），按「质量门禁的分阶段落地」登记偏离 + 发起者追认，MUST NOT 伪装成已通过。

---

## 依据

- 立项书 §5.2（B18F1 行）、§5.3（C23 / C24）、§5.4（DF4 `Span` 的口径）、§5.5（依赖白名单）、§5.6（路线 B）、§5.8.1（可视化 12 项之「Trace · span 生产」）、§5.8.3（缺口 2 / D11）、§9.1（门禁）。
- 契约权威：`specs/b2f1-contracts-protocols/contracts/public-api.md` §1.2 / §1.3（11 字段 + 冻结行为）· `harness/reports/Q8-图运行时最小契约.md` §3.4 / §3.4.1（C22 / C23 / C24）。
- 路线依据：`harness/reports/Q6-可视化与可诊断性的规模与可行性.md` §1 / §4.2（route B · 节点 span 自定义命名空间）。
- 上游锚点：`langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`（2026-11-20 实测）；文件 / 行号见「上游对照」§1 / §2。
- 语义约定：`github.com/open-telemetry/semantic-conventions-genai`（Apache-2.0）——`docs/gen-ai/gen-ai-spans.md` · `docs/gen-ai/client-inference.md` · `docs/gen-ai/execute-tool.md` · `docs/registry/attributes/gen-ai.md` · `docs/general/recording-errors.md`。
- 宪法 `.specify/memory/constitution.md`：原则 I / II / IV / V / VI / VII / VIII / IX / XI / XII。
- 承接来源：`specs/b8f2-stream-modes/spec.md` 下游承接 **D-3** · `specs/b8f3-node-alias-context/spec.md` 下游承接 **D-2 / D-3**。
