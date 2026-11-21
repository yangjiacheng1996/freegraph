# Feature Specification: B19F1 · `TraceSink` 接入 + `current_span()` + 默认关闭

**Feature Branch**: `b19f1-tracesink-current-span`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_specify` 钩子；既有 feature 同样在 `main` 上开发）

**Created**: 2026-11-21

**Status**: Draft

**Input**: User description: `harness/features/B19F1_TraceSink与current_span.md` —— 把 B18F1 生产的 span **推送给用户注入的接收端**：提供 `TraceSink` 协议接入点与 `current_span()` 上下文 API，使「当前 span」在嵌套调用中可被访问。判定：**嵌套 span 父子关系正确；不注入 tracer 时零副作用；补充记录与节点 span 一一对齐**。

> **范围提醒**：本 feature 是 **L5 可观测层**的**接入与推送**，不是重新生产 span。
> `Span` 的 11 字段、`TraceSink` 的 3 方法、`RunConfig` 的 9 字段、`SuperStepResult` /
> `PregelTask` / 公开门面符号面**一律不动**；span 生产、父子入栈 / 出栈、接收端异常隔离
> **复用 B18F1 的 `SpanProducer`**（D-1），**MUST NOT** 重新实现。
> 本地 trace 存储 / 查询（B20F1 / B20F2）、OTLP 导出（B21F1）、前端 UI（v2 / B26）
> 均**不在本 feature 范围**。

---

## 注入点形态裁定（FR-001 的「写死」结论）

> 提示词要求：注入点形态 MUST 在 spec 中**写死**——「编译期关键字」或「运行配置」二者择一，
> 并说明理由。本节是**锁定结论**，`/speckit.plan` 与 `/speckit.implement` **MUST** 照此执行。

**锁定形态：编译期关键字 `StateGraph.compile(*, tracer: TraceSink | None = None)`（keyword-only，与既有 `cache=` / `store=` 等一致）。**

| 备选 | 是否采用 | 理由 |
|---|---|---|
| **编译期关键字 `compile(tracer=...)`** | ✅ **采用** | ① `RunConfig` 是 **L1 配置载体**（**9 字段冻结面**）⇒ 把 `TraceSink` **实例**放进运行配置会破「9 字段冻结面」，且让配置载体承担对象生命周期；② `invoke()` / `stream()` 的签名（C11 / C12）已冻结，追加 `tracer=` 关键字会破**已交付**的方法签名 / 门面快照；③ `compile()` 已是**外部能力注入的既有落点**（`checkpointer=` / `store=`）⇒ 追加**可选**关键字保持「`compile()` 无参可调用」（宪法原则 III），且不污染每次运行的配置；④ `harness/demo/README.md` 已把 `compile(tracer=...)` 登记为**待锁定候选**，锁定它使验收脚本形态与 API 形态一并确定（立项书 §9.2）。 |
| 运行配置注入（`RunConfig.tracer` / `invoke(tracer=)`） | ❌ **不采用** | ① 扩 `RunConfig` 破坏 L1 纯数据面与 9 字段冻结；② 给 `invoke` / `stream` 加关键字破坏 C11 / C12 的已冻结签名与 API 快照；③ 收益（每轮换 sink）不足以抵消冻结面破坏。 |

**运行期语义（与编译期注入不矛盾）**：`compile()` 只**持有**用户 `TraceSink`；**真正的
`SpanProducer` 构造与双绑定是 run-scoped 的**——每次 `invoke()` / `stream()` 在其运行作用域内
构造**一个** `SpanProducer`（接收端 = 该 `TraceSink`），把**同一个** producer 同时绑定到
**L2 节点接缝**与 **L5 调用辅助**，作用域结束即解绑（见 FR-009）。`compile(tracer=None)`
在**顶层且无外层 tracer** 时**等价于未注入**（零副作用）；在 **B19F1 注入作用域内**则用于
**屏蔽外层**（FR-021）；作用域外的 B18F1 直接绑定不受影响。

**文档联动（本 feature 必办）**：形态锁定后，`harness/demo/README.md`
「尚缺的验收脚本」表中 `compile(tracer=...)` 一行 MUST 由「待锁定」改为「已锁定」，
并注明锁定依据 = 本 spec §「注入点形态裁定」。

---

## Clarifications

### Session 2026-11-21

- Q: 触发源、并发分组、屏障分组，以及逐节点输入/输出/错误这些补充信息，应该以什么方式交付给用户？ → A: 采用**可选鸭子类型回调推送**——sink 可额外实现 `on_trace_record(record)`；不实现则只用已冻结的三方法，零影响；B19F1 负责采集并推送（FR-011…FR-015）。
- Q: 逐节点 record 里的「输入状态 / 输出状态」默认要采集到什么程度？ → A: **完整状态 + B19F1 侧 JSON 安全降级**——完整采集，不可 JSON 序列化的对象替换为类型名 / 占位符，保证 B20 可直接落 JSONL（FR-015）。
- Q: 补充 trace 记录应该按什么粒度组织：每个节点一条、每轮 super-step 一条，还是两者都发？ → A: **每个节点任务一条记录**（含 `superstep`、触发源、并发组、屏障组、`input/output/error`），与节点 span 一一对应；不另发轮记录（FR-011…FR-015）。
- Q: 同一次运行里，一个节点通过 `Send` 被并发调用多次时，每条补充记录应如何区分这些任务？ → A: **同时带 `span_id` 与 `task_id`**——`span_id` 与节点 span 一一对应；`task_id` 沿用 B11F1 F-13（标准任务 = 节点名；fan-out 任务 = `节点名:TaskId`）（FR-011…FR-015）。
- Q: 节点执行成功或失败时，`on_trace_record` 与 `on_span_end` 的调用顺序应该是什么，且在各自回调内部 `current_span()` 应返回谁？ → A: **先记录、后结束**——**当 sink 实现 `on_trace_record` 时**顺序为 `on_span_start`（`current_span()` = 新 span）→ `on_trace_record`（= 该节点 span）→ `on_span_end`（= 父级 / `None`）；未实现时为 `on_span_start → on_span_end`；沿用 B18「先出栈再转发」现状，不改生产者（FR-002 / FR-003 / FR-015）。
- Q: 当一个节点内部再 `invoke()` 另一个编译产物时，内层运行应该和外层共享同一棵 trace 树吗？ → A: **v1 不统一**——每个编译产物各自独立；**外层为 B19F1 注入作用域**时内层未注入 tracer ⇒ 不产 span；**外层为 B18F1 直接绑定且当前无活动 B19F1 作用域**时保持既有继承语义；内层注入了 tracer ⇒ 独立一棵树（独立 `run_id`，不挂外层 parent）；子图统一树留 v2 / C26（FR-021）。
- Q: 被中断（`GraphInterrupt`）的节点，或因同轮其它节点失败而被取消的节点，要不要产出补充 trace 记录？`error` 字段放什么？ → A: **与 span 对齐**——有节点 span 就有 record；中断 `error` = 原 `GraphInterrupt`；**节点自身抛取消异常（如 `CancelledError`）= 原取消 / 异常**；**运行期只取消排队未启动任务，已启动任务会跑完，故 v1 不存在「运行期取消已启动任务」分支**；从未启动 = 无 record；`record 数 == 节点 span 数`（FR-015 / SC-017）。

---

## 分析修复记录（2026-11-21）

- **R-1 已批准**：`src/freegraph/_stategraph.py`（L3）**局部** import
  `src/freegraph/observability/_inject.py`（L5），仅限 tracer 注入 / 外层屏蔽；
  同步更新 `立项书 §5.1`、本 spec §5、`layer-registry.md`、`gate_G25_import_graph.py`；
  MUST NOT 扩展为任意 L3 → L5。
- **SC-011**：JSON 判据改为 `json.dumps(record.to_jsonable())`；`TraceRecord.error`
  保留原异常对象。
- **FR-015**：逐节点补充记录覆盖 `invoke()` **与** `stream()` 两条路径。
- **output_state**：存**节点原始返回值**（`node.run` 的 raw return；JSON 安全降级后）；
  `writes/gotos/fanout` 是调度器归一结果，不是 record 的 `output_state`。
- **concurrency_group**：= 本轮**派发集**（含被派发但未启动的取消任务；其自身无 record）。
- **2026-11-21 第二轮 analyze 修复**：补 **P-10 / D-309** 关闭 X-4 对照缺口；**R-2** 收窄为
  仅 `_span_hook`（不读 `_stream_context`）；补 **SC-010**（图级 `FailingSink`）、
  **SC-012 / FR-006**（`SpanOnlySink`）、**FR-010**（`RunConfig.run_id` 忽略）判定任务；
  取消语义改为「节点自身取消 / 运行期只取消未启动任务」；可选记录仅在接收端实现时构造
  payload；基线更新为 `1863 passed, 6 skipped`；B19F1 序号改为 **第 24 个**。
- **2026-11-21 第三轮 analyze 修复**：**I1** 保留 B18F1 直接绑定（仅 B19F1 作用域触发嵌套屏蔽；
  FR-005 / FR-021 / SC-002 / SC-016 / Edge Cases / Assumptions 同步限定）；**K1** R-1/R-2/R-3
  一次性追认；**K2** 质量门禁 5 偏离登记；**S1** A6 恢复为「补充记录与节点 span 对齐」并新增 A7；
  **D1** T017 移除 record 断言；**A1** 明确执行次序 = `triggers` / `concurrency_group` 字段顺序；
  **P1** 补 **D-310 / X-5**（P-09）；**A3/A5** 明确导出面与可选回调条件式；**G1/A4/L1–L6** 同步修订。
- **2026-11-21 第四轮 analyze 修复**：**X1** 保留 **R-2**（L5 不读 `_stream_context`），
  收窄 B8F2 的 R-6 为「L2 读取；B19F1 从节点 span 继承」；**X2** 明确 invoke `run_id`
  由注入点**优先**绑定、B18F1 L2 绑定为 **fallback**，并要求每次注入运行恰一次有效绑定；
  **T1** 把 **T031** 共享守卫移到 T018 之后、T019/T020 之前；**A1** 写死 `triggers`
  统一排序键（标准项 `index = -1`）；**U1** 写死 raw / normalized 的私有承载；
  **T2** 统一 `TaskTraceMeta`；**A2** 明确接收端异常隔离仅覆盖 `Exception`；
  **A3** 明确 `TraceSink` 静态注解与运行期最小面的有意差异；**A4** 写死 B19F1 作用域
  优先于作用域内的 B18F1 直接绑定；**G1/G2/G3** 补边缘测试、追溯映射与措辞。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 把运行轨迹接到我自己的系统 (Priority: P1)

作为用户，我实现一个 `TraceSink`（收 `on_span_start` / `on_span_end`）并传给 freegraph，
从而在**自己的**日志系统里看到每次运行的轨迹——不需要任何 SaaS 账号、不需要 API key。

**Why this priority**: 这是 C23 的**最小价值切片**：没有「推送」，B18F1 生产的 span 只停在
内核里，用户拿不到任何东西。

**Independent Test**: 构造一个记录型 `TraceSink`，用 `compile(tracer=sink)` 编译一个
`a → b` 线性图并 `invoke()`；断言收到**成对**的 `on_span_start` / `on_span_end`，
且每个 span 的 `name` / `node` 均为被执行的节点名、`run_id` 非空、`thread_id` 与
`RunConfig` 的生效值一致。

**Acceptance Scenarios**:

1. **Given** 注入了一个 `TraceSink`，**When** 执行一个节点，**Then** 该节点触发 1 次
   `on_span_start` 与 1 次 `on_span_end`，二者 `id` 相同且 `end_time` 非空。
2. **Given** 注入了 `TraceSink`，**When** 节点抛异常，**Then** 该节点仍触发配对的
   start / end（结束快照 `end_time` 非空），且原始异常原样抛给调用方。
3. **Given** 注入了 `TraceSink`，**When** 运行 `a → b` 两节点图，**Then** 两个节点各有
   一对 start / end，**数量与归属**正确（并发下不要求完成次序）。
4. **Given** `RunConfig(thread_id="t-1")` 且注入 sink，**When** 运行，**Then** 收到的每个
   span 的 `thread_id == "t-1"`、`run_id` 非空。

---

### User Story 2 - 嵌套调用能还原调用树 (Priority: P2)

作为用户，我的节点里调用了「子任务」（如模型 / 工具调用，或同一 trace 树内的更深层
调用），我希望 span 呈**父子结构**而非平铺；同时我在代码里能随时问「当前 span 是谁」。
（跨 compiled graph 的嵌套树统一**不在本 feature 范围**，见 FR-021。）

**Why this priority**: 这是 C24 的核心，也是多 agent 嵌套 trace 的基础；没有它，trace
只是一堆平铺的耗时记录，无法还原调用树。

**Independent Test**: 在一个节点内通过 B18F1 的 `invoke_model` / `invoke_tool` 产生子 span，
子 span 内再调用一层；断言每层子 span 的 `parent` == 其**直接父级 span 的 `id`**；
在嵌套内调用 `current_span()` 返回**内层** span，内层结束后**恢复**为外层 span。

**Acceptance Scenarios**:

1. **Given** 一个节点内产生子 span，**When** 子 span 开始，**Then** 子 span 的 `parent`
   == 所在节点 span 的 `id`（引用相等语义：**id 字符串逐字相等**）。
2. **Given** 模型 → 工具 → 模型三层嵌套，**When** 全部结束，**Then** 父链**逐层**正确
   （不跳层、不串层）。
3. **Given** 在嵌套内，**When** 调用 `current_span()`，**Then** 返回**当前最内层** span；
   内层结束后再次调用返回**外层** span；离开所有 span 后返回**空值**（不抛异常）。

---

### User Story 3 - 不注入就完全没这回事 (Priority: P1)

作为用户，我不诊断时，希望 freegraph **完全静默**：不推送、不创建 span、不生成 span
专用运行标识、不读环境变量、不引入新依赖——行为与没有可观测层时**完全一致**。

**Why this priority**: 这是宪法原则 I / IV 的硬承诺；若「默认关闭」不可测，将来任何
可观测增强都可能在用户不知情时改变行为或偷偷出站。

**Independent Test**: **不传** `tracer=`（或显式传 `None`），且**无任何外层 tracer**，
运行同一张图；用计数夹具 / 构造计数断言 `on_span_start` 调用数 == 0、span 构造数 == 0、
span 专用 `run_id` 绑定数 == 0；再设置 `LANGSMITH_TRACING=true` / 任意 `LANGCHAIN_*`
环境变量，断言行为**不变**；最后断言依赖闭包仍为空集、`import freegraph` 不加载 L5。

**Acceptance Scenarios**:

1. **Given** 未注入 `tracer` 且无任何外层 tracer，**When** 执行任意图（含异常、并发、
   `stream()`），**Then** span 构造数 == 0、接收端回调数 == 0。
2. **Given** 未注入 `tracer` 且无任何外层 tracer，**When** 环境中存在
   `LANGSMITH_TRACING=true` / `LANGCHAIN_TRACING_V2=true` / 任意 `LANGSMITH_*`，
   **Then** 行为不变、回调数仍 == 0。
3. **Given** 未注入 `tracer` 且无任何外层 tracer，**When** 检查 `import freegraph` 后的
   `sys.modules`，**Then** 不出现 L5 生产 / 接入模块、`opentelemetry.*`、`langchain*`、
   `langsmith`。
4. **Given** 顶层且无外层 tracer，**When** 运行 `compile(tracer=None)`，**Then** 与
   「完全不写关键字」**逐字等价**（零副作用）；B19F1 作用域内嵌套时按 FR-021 屏蔽外层。

---

### Edge Cases

- **接收端在回调里抛异常**：异常 MUST 被**隔离**——不传播到节点 / 图执行、不改变
  `invoke()` / `stream()` 的输出、不吞掉节点自身的异常、不造成永久挂起；该次可观测写入
  MAY 被丢弃（B18F1 已隔离，本 feature MUST NOT 削弱）。
- **无当前 span**：`current_span()` 返回空值，**MUST NOT** 抛异常。
- **嵌套的 start / end 交错**：内层结束后外层恢复；start / end 始终按 `id` 配对成对。
- **并发节点**：同一 super-step 内并发执行的多个节点，各自的当前 span 栈**独立**；
  一个线程的 span MUST NOT 成为另一线程的 parent（沿用 B8F2 的每任务 `copy_context()`）。
- **中断节点**：仍产配对 span 与一条 record；record 的 `error` = 原 `GraphInterrupt`
  （MUST NOT 替成字符串）。
- **并发取消**：**运行期只取消排队未启动任务**（已启动任务会跑完，v1 不取消运行中任务）⇒
  **从未启动**的取消任务无 span、无 record；若节点**自身**抛 `CancelledError` 等取消异常，
  则按原异常产 record（`error` = 原对象）；`record 数 == 节点 span 数`。
- **跨 compiled graph 嵌套**：**外层为 B19F1 注入作用域**时，内层未注入 ⇒ 无 span / record
  （B19F1 作用域优先，作用域内的直接绑定也被屏蔽）；**当前无活动 B19F1 作用域**且外层为
  B18F1 直接绑定 ⇒ 保持既有继承语义（不触发新的屏蔽）；内层注入 ⇒ **独立树**
  （独立 `run_id`、顶层 `parent=None`）；内层 MUST NOT 隐式继承外层 B19F1 producer。
- **嵌套 / 重入运行**：同一或不同编译产物在节点内被再次 `invoke()` 时，每次注入运行
  各自建立 **producer + `run_id`** 作用域（嵌套运行不继承外层 `run_id` · FR-021）；
  作用域结束恢复外层；不得出现「作用域结束后仍在推送」。
- **`thread_id is None`**：合法；span 的 `thread_id` 为 `None`，不报错。
- **`checkpoint_id` 不可得**：合法；为 `None`，不伪造。
- **`run_id` 缺失**：视为实现缺陷；本 feature MUST 保证注入生效时 `run_id` 非空。
- **环境变量存在**：`LANGSMITH_*` / `LANGCHAIN_*` / `OTEL_*` 存在时**不得**启用、禁用或
  改变任何行为。
- **`compile(tracer=sink)` 但从不运行**：不得产生任何 span / 回调 / id。
- **`Span.context` 与 C21 `context`**：二者 MUST 分离；不得把 `RunConfig.context`
  （节点只读运行期上下文）塞进 `Span.context`。

---

## Upstream Parity *(mandatory — 宪法 v1.12.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11** / `langchain-core` **1.7.6** / `langsmith` **0.14.17**（取证于 2026-11-21，本仓库 `.venv` 实际安装版本）

> **口径说明**：上游**没有** freegraph 这样的「自有 `TraceSink` 协议 + `current_span()` 自由函数」。
> 上游的可观测挂钩是 `callbacks` / `tracers`（`langchain-core` 类型），其「当前 run」由
> LangSmith 的 `get_current_run_tree()` 提供（`RunTree` 对象）。因此本 feature 的主体落在
> 宪法原则 XI 的**必须自研区 ③（上游没有的能力）**、**①（零账号 / 零主动出站 / 零依赖）**与
> **④（下游 langchain 兼容适配）**；只有「上下文内当前单元」「默认关闭」「失败也成对」
> 「接收端异常隔离」这几类**行为面**需要与上游对齐。

### §1 逐条对照（P-01…P-10）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| **P-01** | **当前运行单元**可被上下文内访问，无则返回空值 | `langsmith/run_helpers.py:107-113`（`get_current_run_tree()`）· `langsmith/_internal/_context.py:27`（`_PARENT_RUN_TREE_REF = ContextVar(...)`）/ `:30-37`（返回 `ref()` 或 `None`）· `langsmith/run_helpers.py:152`（父子取当前 run tree） | `current_span()` 返回上下文内**当前最内层** `Span`；无则 `None`，不抛异常 | **SAME**（语义）· **DIFF**（表示 + 可得性面） | 语义同为「context-local 当前单元 + 无则空」；差异：① 上游返回 `RunTree`，freegraph 返回自有 `Span`（B2F1 冻结）；② **实测 E-2** 显示上游 `get_current_run_tree()` 在 LangChain callback 驱动的图节点内返回 `None`（该 contextvar 由 LangSmith `traceable` / `tracing_context` 路径填充，非 callback 路径）⇒ freegraph 的 `current_span()` 在**节点执行期间**可用，属**更强**的可观测面（自研区 ③） |
| **P-02** | **注入载体** | `langchain_core/runnables/config.py:92,134,145,360-383`（`config["callbacks"]` / `callbacks=`）· `langchain_core/runnables/base.py:319-324`（`chain.invoke(..., config={"callbacks": [...]})`） | **编译期关键字** `compile(tracer=...)`；运行作用域内双绑定 | **DIFF** | 上游载体是 `RunnableConfig.callbacks`，属 `langchain-core` 类型；freegraph 复用即破零 LangChain 红线 ⇒ 自研区 ①③；改为编译期关键字（本 spec 已锁定） |
| **P-03** | **默认关闭是否受环境变量影响** | `langchain_core/tracers/context.py:120`（`if _tracing_v2_is_enabled():`）/ `:141-144`（回落 `tracing_is_enabled()`）· `langsmith/utils.py:119-144`（`TRACING_ENABLED` contextvar → run tree → 全局开关 → `TRACING_V2` / `TRACING` 环境变量） | **只认显式注入的 `compile(tracer=...)`**；MUST NOT 读任何环境变量；`LANGSMITH_TRACING=true` 不改变行为 | **STRICTER** | 宪法原则 I / 配置层黑名单；freegraph 反 LangChain「key / env 存在即自动开 tracing」 |
| **P-04** | **成功路径**开始 / 结束**成对** | `langchain_core/tracers/base.py:261`（`on_chain_start`）/ `:306`（`on_chain_end`）· `langchain_core/callbacks/base.py:386`（`on_chain_start`） | 每个 span 开始触发 `on_span_start`、结束触发 `on_span_end`，按 `id` 成对 | **SAME**（行为面）· **DIFF**（表示） | 成对生命周期同为行为面；载荷从 callback run 改为自有 `Span` |
| **P-05** | **异常路径**仍完成开始 / 结束配对，异常原样重抛 | `langchain_core/tracers/base.py:335`（`on_chain_error`）· `langchain_core/runnables/base.py:2366`（异常路径 `on_chain_error`） | 异常时仍产出**同 `id`、已填 `end_time`** 的结束 span，然后原对象 / 原类型 / 原消息重抛 | **SAME**（语义）· **DIFF**（表示） | 「失败也成对」同为行为面；表示差异随 P-01 / P-04 |
| **P-06** | **父子 / 嵌套**关系 | `langchain_core/callbacks/manager.py:510,532,623`（`parent_run_id` 的构建 / 传递）· `langsmith/run_helpers.py:152`（父子取当前 run tree） | `Span.parent` = 父 span 的 **`id` 字符串**；内层结束恢复外层 | **SAME**（语义）· **DIFF**（表示） | 父链语义同为「当前最内层为父」；freegraph 用 id 字符串（JSON 可序列化 · B2F1 冻结） |
| **P-07** | **接收端 / handler 异常隔离** | `langchain_core/callbacks/manager.py:351-354`（handler 抛异常被捕获并记录警告） | 接收端回调异常被隔离；可 `logging.warning`；不改变图执行结果 | **SAME** | 与上游同款行为面；由 B18F1 的 `SpanProducer` 实现，本 feature 不得削弱 |
| **P-08** | **运行时依赖闭包** | `langchain-core 1.7.6` 的 `Requires-Dist` 含 `langsmith<1.0.0,>=0.14.9`（+ `certifi` / `httpx` / `pydantic` 等）· B18F1 实测 **E-4** | 基础安装依赖闭包**为空集**；无 `opentelemetry-*` / `langchain*` / `langsmith` | **STRICTER** | 宪法原则 I / II / IX；本项目产品承诺 |
| **P-09** | **两条事件通道按 id 关联** | 上游 callback run 自带 `run_id` / `parent_run_id`（`langchain_core/tracers/base.py:47,53`）· 流式事件与回调共享同一 run 生命周期 | `stream()` 事件与 `TraceSink` span **共享同一 `run_id` / `thread_id`**（L2 私有 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`）；两条通道**独立** | **SAME**（id 关联语义）· **DIFF**（双通道结构） | D11 已冻结的关联约定；freegraph 用同一对 contextvar，不把 trace 塞进 stream 信封 |
| **P-10** | **触发源 / 并发组 / 屏障组的统一元数据面** | 上游**没有**等价的统一暴露：这些事实散落在调度内部与 callback / debug payload 中（`langgraph/pregel/_algo.py:482` 只体现节点名序；无 `triggers` / `concurrency_group` / `barrier_groups` 的公共结构） | freegraph 在 L5 自有补充 trace 记录中统一给出 `triggers` / `concurrency_group` / `barrier_groups`，经可选 `on_trace_record` 推送；**不写进**冻结的 `Span` 字段 | **DIFF**（自研区 ③：上游没有的能力） | B9F1 / B11F1 / B12F1 / B7F4 的下游承接要求统一暴露；上游无同款结构 ⇒ 只能自研；不改变 `Span` / `SuperStepResult` 冻结面 |

### §2 实测基线（E-1…E-3 · `langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17` · 取证于 2026-11-21）

| # | 实验 | 结果 |
|---|---|---|
| **E-1** | 两节点线性图 `a → b`，`app.invoke({"x":0})`，**不传** `callbacks`，环境变量全清 | 正常返回 `{"x": 2}`；**无任何** callback 事件（默认关闭） |
| **E-2** | 同图，传入自定义 `BaseCallbackHandler`，并在节点内调用 `get_current_run_tree()` | 共 **6 条** handler 事件：图 start → 节点 a start / end → 节点 b start / end → 图 end；节点 run 的 `parent_run_id` == 图 run id（另有 2 条节点内探针记录，不计入 handler 事件）。**节点内 `get_current_run_tree()` 返回 `None`**（LangChain callback 路径**不填充** `_PARENT_RUN_TREE_REF`；该 contextvar 由 LangSmith `traceable` / `tracing_context` 路径填充）⇒ 这正是 freegraph `current_span()` 的**可得性差异**来源（P-01） |
| **E-3** | `boom` 节点抛 `RuntimeError("boom")`，传入自定义 handler | 异常原样抛出（`RuntimeError: boom`）；事件序列 = 图 start → a start / end → boom start → `on_chain_error`（boom）→ `on_chain_error`（图）⇒ run 生命周期仍完成 |

> **实测脚本**：`/tmp/b19_upstream_probe.py`（E-1 / E-2 / E-3 · 2026-11-21 实跑 · **不进仓库**）。
> **上游源码参照**：`langsmith/run_helpers.py:107-113,152` · `langsmith/_internal/_context.py:27,30-37` ·
> `langsmith/utils.py:119-144` · `langchain_core/runnables/config.py:92,134,145,360-383` ·
> `langchain_core/runnables/base.py:319-324,2366` · `langchain_core/callbacks/manager.py:351-354,510,532,623` ·
> `langchain_core/callbacks/base.py:386` · `langchain_core/tracers/base.py:47,53,261,306,335` ·
> `langchain_core/tracers/context.py:120,141-144`。

### §3 差分场景组 *(mandatory)*

> 编号段 **D-301…D-310**（避开 B18F1 的 D-201…D-208 与更早编号段）。

| # | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 |
|---|---|---|---|
| **D-301** | 不注入任何 sink / handler | freegraph：span 构造数 == 0、回调数 == 0；上游：callback 事件数 == 0；两侧图都正常完成 | SAME（P-03） |
| **D-302** | 两节点线性图 + 注入 sink / handler | freegraph：2 对节点 start / end；上游：2 组节点 callback；两侧最终状态逐字相等 | SAME（行为面）· DIFF（表示，P-04） |
| **D-303** | 节点 → 工具 → 模型嵌套 | freegraph：子 span 的 `parent` == 直接父级 `id`；上游：对应 run 的 `parent_run_id` 逐层正确 | SAME（父链语义）· DIFF（表示，P-06） |
| **D-304** | 环境变量 + 不注入 | freegraph：设置 `LANGSMITH_TRACING=true` 后 span 数仍 == 0；上游：可能自动开启 tracing | STRICTER（P-03） |
| **D-305** | 异常节点 | freegraph：结束 span 仍产生、异常原样重抛；上游：`on_chain_error` 仍触发、异常原样重抛 | SAME（P-05） |
| **D-306** | 当前单元上下文（图节点执行期间） | freegraph：嵌套内 `current_span()` 返回内层、退出后返回外层、空上下文返回 `None`；上游：**实测 E-2** 在 callback 驱动的图节点内 `get_current_run_tree()` 返回 `None`（仅在 `traceable` / `tracing_context` 路径可得当前 run） | DIFF（可得性 / 表示 · P-01） |
| **D-307** | 依赖闭包 | freegraph 基础安装闭包为空；上游 `langchain-core` 闭包含 `langsmith` | STRICTER（P-08） |
| **D-308** | 注入载体差异 | 两侧都能在配置后产出观测事件；freegraph 用 `compile(tracer=...)`，上游用 `config["callbacks"]` | DIFF（P-02，行为等价、API 不同） |
| **D-309** | 触发源 / 并发组 / 屏障组元数据 | freegraph：注入实现 `on_trace_record` 的 sink 后，记录含 `triggers` / `concurrency_group` / `barrier_groups`，且与节点 span 一一对齐；上游：无等价统一结构（只能从 debug / callback 载荷拼凑或不可得） | DIFF（P-10，自研区③） |
| **D-310** | 两条事件通道按 id 关联 | freegraph：同一次运行的 `stream()` 事件与 `TraceSink` span 的 `run_id` / `thread_id` 逐字相同；上游：流式事件与 callback run 共享 run 生命周期 | SAME（id 语义）· DIFF（双通道结构，P-09） |

⇒ **判词分布**：**SAME 行为面 5**（D-301 / D-302 / D-303 / D-305 / D-310；其中 **D-302 / D-303 / D-310 同时含表示层 DIFF**）+ **STRICTER 2**（D-304 / D-307）+ **DIFF 4**（D-306 当前单元可得性 / 表示 · D-308 注入载体 API · D-309 统一元数据面 · D-310 双通道结构）。

### §4 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **DIFF**（自研区 ③：上游没有的能力；**行为面 SAME · 表示层 DIFF**） | 上游无自有 `TraceSink` 协议、无 `current_span()` 自由函数（对应 **P-01 / P-04 / P-05 / P-06** 的表示层差异；**P-01 另有可得性 DIFF**，见 D-306） | freegraph 的可观测协议必须自研（C23 / C24），且 `Span` / `TraceSink` 已由 B2F1 冻结；上游对应物是 LangChain callback + LangSmith `RunTree`，引入即破零依赖红线 | B2F1（协议 / 字段面）· 本 feature（接入 / 推送） |
| **X-2** | **STRICTER**（自研区 ①：零账号 / 零主动出站 / 零依赖） | 上游 tracing 由 `langchain-core` + `langsmith` 承载，且可由环境变量自动开启（对应 **P-03 / P-08**） | freegraph MUST 零第三方依赖、零环境变量、零主动出站；只认显式注入的 `compile(tracer=...)` | 宪法原则 I / II / IX · 本 feature |
| **X-3** | **DIFF**（自研区 ①③：零 LangChain + 上游没有的能力） | 注入载体 = 编译期关键字，而非上游的运行期 `RunnableConfig.callbacks`（对应 **P-02**） | `RunnableConfig` / callbacks 是 `langchain-core` 类型，复用即破红线；`RunConfig` 是 L1 纯数据，不能装对象引用 | 本 feature · spec「注入点形态裁定」 |
| **X-4** | **DIFF**（自研区 ③：上游没有的能力） | 触发源 / 并发分组 / 屏障分组的**统一 trace 元数据面**（对应 **P-10** · B9F1 / B11F1 / B12F1 / B7F4 的下游承接） | 上游把这些事实散落在调度内部与 callback payload 中，无统一暴露；freegraph 由 L5 在**调度层**统一提供（见 FR-011…FR-014），且**不**写进冻结的 `Span` 字段 | 本 feature（承接）· B20（存储） |
| **X-5** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 两条事件通道的载体结构：freegraph 的 `stream()` 事件 + 自有 `TraceSink` span（对应 **P-09**） | 上游 callback run 与流式事件共享 run 生命周期；freegraph 用 L2 私有 id 载体 + 自有 span，**不把 trace 塞进 `stream()` 信封**；两条通道独立、按 id 合并 | 本 feature（接入）· B8F2（id 载体） |

### §5 破冻结面的回溯修订清单 *(本 feature 触发)*

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| `StateGraph.compile` 签名（L3 · B7F2） | `src/freegraph/_stategraph.py` 的 `compile()`：**追加可选关键字** `tracer: TraceSink \| None = None` | **只增不改**：`compile()` **仍无参可调用**（宪法原则 III）；既有 `checkpointer=` / `cache=` / `store=` / `interrupt_before=` / `interrupt_after=` / `debug=` / `name=` / `transformers=` 逐字不变 | 若 API 签名快照门禁因**新增关键字**变红 ⇒ **更新快照**（更新**非**放宽），并在 `harness/verification/B19F1/manual-verification.md` 追认 |
| L5 依赖面（B18F1 的「L5 只 import 标准库 + L1」断言） | 双绑定接缝所在的 L5 模块（具体路径归 plan） | **拆分而不删**：原断言继续覆盖「纯生产 / 纯数据」L5 模块；**双绑定接缝**按 **ARCH-3 例外 R-2** 处理（**本例外只绑定、不读取**）⇒ **只允许** `_inject.py` → `runtime._span_hook`（`bind_span_tracer`）；**不读** `_stream_context`（id 由节点 start `Span` 继承），**不新增公开符号**、**不改变** ARCH-1 方向（L5 → L2 本就是**向下**依赖） | **R-2 / R-3 已获发起者一次性追认（2026-11-21）**；`manual-verification.md` 记录；**MUST NOT** 把例外扩展为「任意 L5 → L2 私有依赖」的通行证 |
| **立项书 ARCH-1**（L3 → L5 反向） | `src/freegraph/_stategraph.py`：**局部** import `observability._inject`（仅 tracer 注入 / 外层屏蔽） | **新增已批准例外（R-1）**：只允许 `_stategraph.py` → `observability._inject`；MUST NOT 扩展为任意 L3 → L5 | **R-1 / R-2 / R-3 已获发起者一次性追认（2026-11-21）**；同步更新 `立项书 §5.1` / `layer-registry.md` / `gate_G25_import_graph.py`；`manual-verification.md` 追认 |
| **CompiledGraph 私有持有面**（B7F2 / B7F3 冻结的 `vars(compiled)` **11 键**） | `src/freegraph/_stategraph.py`：`CompiledGraph` 新增私有字段 `_tracer` | **11 → 12（只增私有字段）**；`CompiledGraph` 仍只持有 sink，不构造 producer / 不绑定 | 更新 B7F2 / B7F3 / B8F1 / B8F2 / B23F1 的 `vars(compiled)` 断言与验收脚本（更新**非**放宽）；`manual-verification.md` 追认 |

> **不破的冻结面**：`Span` 11 字段 · `TraceSink` 3 方法 · `RunConfig` 9 字段 ·
> `SuperStepResult` 5 字段 / `PregelTask` 7 字段 · `stream()` 事件信封 ·
> `freegraph.graph` 门面 **8 符号** · L1 契约 **22 符号** · `freegraph.runtime.__all__`。
> **唯一新增私有字段**：`CompiledGraph._tracer` ⇒ `vars(compiled)` 由 **11** 变 **12**（已登记，**只增**）。

---

## Requirements *(mandatory)*

### Functional Requirements

#### A. 注入、推送与默认关闭

- **FR-001**：系统 MUST 支持把 `TraceSink` 实例注入运行时，**注入点形态锁定为编译期关键字
  `StateGraph.compile(*, tracer: TraceSink | None = None)`**（见「注入点形态裁定」）。
  `compile()` 在**不传** `tracer` 或**显式传 `None`** 时 MUST 与无该关键字**逐字等价**。
  MUST NOT 提供第二种注入形态（不扩 `RunConfig`、不给 `invoke` / `stream` 加 `tracer=`）。
  注入点的**运行时最小面** = `on_span_start` / `on_span_end`；sink 的 `current_span` 方法
  **可选**（freegraph 的 `current_span()` 不委托给它）。`TraceSink` 三方法协议**不变**，
  完整实现仍推荐；运行时 MUST NOT 因 sink 缺 `current_span` 而拒绝注入或报错。
  **类型注解口径**：`compile(tracer=...)` 的静态注解仍为 `TraceSink | None`（公开文档面）；
  运行期按鸭子类型只要求 `on_span_start` / `on_span_end`，因此静态类型检查器可能拒绝
  `SpanOnlySink`——该差异是**有意**的，测试 MUST 用 `typing.cast` / `# type: ignore` 表达，
  MUST NOT 把 `SpanOnlySink` 误写成「满足完整 `TraceSink`」。
- **FR-002**：注入生效时，每个 span 的开始 MUST 触发接收端 `on_span_start`、结束 MUST 触发
  `on_span_end`，且**按 `id` 成对**；正常路径与异常路径**均** MUST 成对。开始回调收到的实例
  `end_time` 为空、结束回调收到**同 `id`、`end_time` 已填**的新实例（B2F1 生命周期冻结）。
  **当 sink 实现 `on_trace_record` 时，回调生命周期顺序 MUST 为**（2026-11-21 澄清裁定）：
  `on_span_start`（`current_span()` = 新 span）→ 节点执行 → `on_trace_record`
  （`current_span()` = 该节点 span）→ `on_span_end`（`current_span()` = 父级，无则 `None`）；
  未实现时为 `on_span_start → on_span_end`。MUST NOT 让记录晚于结束回调；
  MUST NOT 在 `on_trace_record` 之前把节点 span 从当前上下文移除（沿用 B18 的入栈 / 出栈现状）。
- **FR-003**：系统 MUST 提供 `current_span()`：返回当前上下文中**最内层**的活动 span；
  无当前 span 时返回**空值**（`None`），MUST NOT 抛异常。在接收端回调内部 MUST 满足：
  `on_span_start` 内返回**新 span**；**当 sink 实现 `on_trace_record` 时**其内返回
  **该节点 span**；`on_span_end` 内返回**父级 span**（无则 `None`）——见 FR-002 的顺序约定。
- **FR-004**：`current_span()` MUST 支持**嵌套**语义：进入内层后返回内层；内层结束后
  **恢复**为外层；离开所有 span 后返回 `None`。
- **FR-005**：**未注入 sink 且不存在任何外层 tracer**（既无 B19F1 `trace_run_scope`，
  也无 B18F1 的直接 `bind_span_tracer` / `bind_tracer`）时 MUST 零副作用、零开销：
  MUST NOT 构造 `Span`、MUST NOT 构造 `SpanProducer`、MUST NOT 触发任何接收端回调、
  MUST NOT 为 span 生产生成 / 绑定 `run_id`、MUST NOT 读环境变量。
  允许每次节点执行 / 每次运行开始做**一次**廉价判断。
- **FR-006**：`TraceSink` MUST 保持 B2F1 冻结的 `typing.Protocol`（`on_span_start` /
  `on_span_end` / `current_span`，方法体只有 `...`，`runtime_checkable`）；用户**无需继承基类**。
  本 feature MUST NOT 增删 / 改名 / 改签名任何协议方法。补充 trace 记录的
  `on_trace_record(record)` 是**可选的鸭子类型扩展**，**不是**协议成员，MUST NOT 计入
  `TraceSink` 的三方法面。
- **FR-007**：本 feature MUST NOT 引入 OTel SDK 运行时依赖（v1 硬约束；OTLP 属 B21F1）；
  MUST NOT import `opentelemetry-*`。
- **FR-008**：本 feature MUST NOT import `langchain` / `langchain-core` / `langsmith` /
  `langgraph*`；MUST NOT 读取任何环境变量；MUST NOT 发起任何出站请求。
  `compile(tracer=...)` 的**存在**不得由环境变量、配置文件或 API key 自动启用。

#### B. 双绑定、运行作用域与 id 关联

- **FR-009**（承接 B18F1 · D-1）：注入生效时，公开注入点 MUST **构造** `SpanProducer`
  （接收端 = 用户 `TraceSink`），并把**同一个 `SpanProducer` 实例**同时绑定到：
  - L2 `runtime._span_hook.bind_span_tracer(producer)`；
  - L5 `observability._producer.bind_tracer(producer)`。
  绑定 MUST 是 **run-scoped**：在每次 `invoke()` / `stream()` 的运行作用域内建立，
  作用域结束即失效；同一作用域内所有 span 共享**一个** `run_id`。
  本 feature MUST NOT 重新实现 span 生产，MUST NOT 改变 `Span` 的 11 字段。
- **FR-010**（承接 B8F2 · D-3 / D11）：`TraceSink` 收到的每个 span MUST 携带
  `run_id` / `thread_id` / 节点名 / `checkpoint_id`，且与 `stream()` 事件**同源同 id**：
  - `stream()` 路径由 **L2 `_run_round`** 读取私有 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`
    （MUST NOT 另生成；**L5 不直接 import `_stream_context`**）；`invoke()` 路径由注入点在
    **每次注入运行**的作用域内**优先**建立 run-scoped `run_id`（沿用 B18F1 的 `bind_run_ids`
    载体，MUST NOT 新增第二套载体）。B18F1 的 L2 `_run_graph` 绑定是 **fallback**：仅当
    `_STREAM_RUN_ID` 为空时生效；注入点已绑定时 L2 MUST NOT 再覆盖。**每次注入运行 MUST
    恰发生一次有效绑定**，两条路径不得产生两个不同 `run_id`；**嵌套注入运行各自独立**
    （不继承外层 `run_id` · FR-021），作用域结束恢复外层；未注入**且无任何外层 tracer** 时
    MUST NOT 生成；
  - `RunConfig.run_id` MUST 被**忽略**（宪法 v1.15.2）；
  - 两条通道**相互独立、不互为前置**；MUST NOT 把 trace 数据塞进 `stream()` 事件信封；
  - `run_id` 为空（`None` / 空串）的 span 视为**实现缺陷**；`thread_id` / `checkpoint_id`
    可为 `None`（不伪造）。

#### C. 下游承接义务（只接线 · 逐条最小改动）

> 以下义务来自 B9F1 / B11F1 / B12F1 / B7F4 / B18F1 的**只接线**承接条款。它们 **MUST NOT**
> 通过改动冻结的 `Span` 11 字段 / 节点 `attributes` / `Span.context` 来兑现（B18F1 Q11 / Q15）；
> 承载形态由本 feature 自有的**补充 trace 记录**承担，经**可选鸭子类型回调**
> `on_trace_record(record)` **推送**给 sink（2026-11-21 澄清裁定 · 见 `## Clarifications`）。
> 该回调**不是** `TraceSink` 协议成员：sink 实现则收，**不实现则零影响**；MUST NOT 因它改变
> 已冻结的三方法协议。
> **记录粒度 = 每个节点任务一条**（2026-11-21 澄清裁定）：每条记录至少含
> `span_id` / `task_id`（标准任务 = 节点名；fan-out 任务 = `节点名:TaskId` · B11F1 F-13）/
> `run_id` / `thread_id` / `checkpoint_id` / `node` / `superstep` / 触发源 / 并发组 /
> 屏障组（有则）/ `input_state` / `output_state` / `error`；与节点 span 一一对应
> （关联键与 span **同源同值** · `run_id` 非空）。**不另发轮记录**。字段名与容器形状归
> `/speckit.plan` 写死。

- **FR-011**（承接 B9F1 · D-3 / B11F1 · D-5）：**当 sink 实现 `on_trace_record` 时**，
  trace 层 MUST 在**触发判定层统一暴露**「这个节点是被什么触发的」，覆盖 **静态边** +
  **`Command.goto`** + **`Send` fan-out 任务**三类；MUST NOT 只暴露 `goto` 一类，
  MUST NOT 只暴露静态边一类。
  MUST NOT 期待 B9F1 / B11F1 预先提供跳转 / 派发记录（它们刻意未新增观测字段）。
  触发源信息 MUST 经**补充 trace 记录** + 可选 `on_trace_record` 回调推送。
- **FR-012**（承接 B12F1 · D-3）：**当 sink 实现 `on_trace_record` 时**，trace 层 MUST
  在**调度层统一暴露**「这个节点与哪些节点**同轮并发**」——同一 super-step 内的并发分组；
  MUST NOT 只暴露「跑了多久」而漏掉「与谁并发」。MUST NOT 期待 B12F1 预先提供并发分组信息。
  并发分组信息 MUST 经同一补充 trace 记录 + 可选 `on_trace_record` 回调推送。
- **FR-013**（承接 B12F1 · 确定性口径）：trace 层的**确定性执行次序** MUST 由以下字段的
  **确定性顺序**承载：
  - `triggers` 按**统一排序键** `(kind, source, index)` 升序；标准边 / `Command.goto` 的
    `("e", source)` **没有 `index`**，实现 MUST 令其 `index = -1`（`"e"` < `"send"`），
    MUST NOT 直接用二元组 / 三元组的自然序混排；
  - `concurrency_group` 按「标准任务节点名序 + fan-out 任务**数值** TaskId 序」排列
    （B11F1 F-14）。
  **`on_trace_record` 的到达顺序**（并发完成时刻）**不**属于判据，
  MUST NOT 用「完成时刻」或「节点表（声明）顺序」断言。
- **FR-014**（承接 B7F4 · D-7）：**当 sink 实现 `on_trace_record` 时**，trace 层 MUST 统一
  暴露「**屏障的触发**」（多源汇合）的**触发分组 / 屏障来源**，与 FR-011 的触发源同源；
  MUST NOT 期待 B7F4 预先提供屏障分组信息，MUST NOT 自造**结果对象**字段（屏障信息不属于
  `SuperStepResult`）。
  屏障信息 MUST 经同一补充 trace 记录 + 可选 `on_trace_record` 回调推送。
- **FR-015**（承接 B18F1 · D-6）：`invoke()` **与 `stream()` 两条路径**的逐节点
  **输入状态 / 输出状态 / 错误** MUST 由本 feature 通过 **L2 既有节点接缝（或其扩展 hook）**
  捕获，并转换为本 feature 自有的 trace record（与 `Span` **分离**，不改 `Span` 字段）；
  该记录 MUST 经可选 `on_trace_record` 回调推送（sink 不实现 ⇒ 零影响；该回调的异常按
  FR-017 隔离）。**sink 不实现 `on_trace_record` 时 MUST NOT 构造补充 `TraceRecord` /
  MUST NOT 采集 `input_state` / `output_state`**（可选功能不得为无消费方的接收端产生采集开销）。
  记录 MUST 携带 `run_id` / `thread_id` / `checkpoint_id`，与本次运行的 span **同源同值**；
  `run_id` **非空**，`thread_id` / `checkpoint_id` 可为 `None`（不伪造）。
  **输入状态 / 输出状态 MUST 完整采集**（2026-11-21 澄清裁定）；**`output_state` MUST 取
  节点的原始返回值**（`node.run` 的 raw return；归一结果 `writes` / `gotos` / `fanout`
  仍用于调度，但不作为 record 的 `output_state`）。B19F1 MUST 在**本侧**做
  **JSON 安全降级**：不可被标准库 `json.dumps` 直接序列化的对象替换为**类型名 / 占位符**
  （降级 MUST 确定、MUST NOT 抛异常、MUST NOT 泄漏原对象内容），使 B20 可直接落 JSONL。
  **错误字段仍为原样抛出的异常对象（+ `add_note` 可读）**，MUST NOT 在 record 内替成字符串
  （JSONL 落盘时如何表达异常由 B20 决定：类型名 + 消息）。节点名 / 耗时继续由 B18F1 节点
  span 承担。承接机制即本 FR，MUST NOT 留给 B20「从 `PregelTask` / `SuperStepResult` 猜」
  作为**唯一**路径（`PregelTask` 无 input 字段，无法完整还原输入状态）。
  **记录 MUST 与节点 span 一一对齐**（2026-11-21 澄清裁定）：凡产生节点 span 的任务 MUST
  产出一条 record（`record 数 == 节点 span 数`）；中断节点的 `error` = 原 `GraphInterrupt`；
  **节点自身抛取消异常（如 `CancelledError`）时 `error` = 原取消 / 异常**；**运行期只取消
  排队未启动任务（已启动任务会跑完）** ⇒ **从未启动**的取消任务 MUST NOT 产 record。
- **FR-016**（承接 B8F3 · D-2 / D-3）：C21 的 `context`（节点只读运行期上下文）**不是**
  `TraceSink` / `Span.context` 的字段；本 feature MUST NOT 复用 `Span.context` 承载 C21 的
  `context`；MUST NOT 回退到 `configurable` 承载 `context`，MUST NOT 重新引入节点别名。

#### D. 隔离、惰性与零扩张

- **FR-017**：接收端回调（含 `on_span_start` / `on_span_end` / 可选的 `on_trace_record`）
  抛出的 **`Exception`** MUST 被隔离：不传播到节点 / 图执行、不改变 `invoke()` / `stream()`
  的输出、不吞掉节点自身的异常、不造成永久挂起；本 feature MUST NOT 削弱 B18F1 已实现的
  隔离。**`BaseException`（如 `KeyboardInterrupt` / `SystemExit`）不是本条的「异常」，MUST
  NOT 被吞**（与 B18F1 `SpanProducer._forward` 的现状一致）。
- **FR-018**：MUST 保持**顶层包惰性**：`import freegraph` MUST NOT 加载 L5 接入模块或 L2
  span hook。MUST NOT 扩大 `freegraph.graph` 门面符号面（仍 **8**）、L1 契约符号面（仍 **22**）、
  `freegraph.runtime.__all__`。`current_span()` 与补充记录类型 `TraceRecord` MUST 从
  **L5 模块**（`freegraph.observability`）导出，**MUST NOT** 经 `freegraph.graph` 门面转出；
  `trace_run_scope` 是 L5 **内部**接线入口，不对外导出。
- **FR-019**：冻结面零改动：`Span` 11 字段、`TraceSink` 3 方法、`RunConfig` 9 字段、
  `SuperStepResult` / `PregelTask` 字段、`stream()` 事件信封**一律不变**。唯一**新增**的公开
  关键字是 `compile(tracer=...)`（见 §「破冻结面的回溯修订清单」）。
- **FR-020**：本 feature MUST NOT 实现本地 trace 存储 / 查询（B20F1 / B20F2）、OTLP 导出
  （B21F1）、前端 UI（v2 / B26）、评测 / 数据集（永不做）。
- **FR-021**（跨编译产物的嵌套 · 2026-11-21 澄清裁定 · 2026-11-21 修订）：
  v1 MUST NOT 统一跨 compiled graph 的 trace 树——每个 `compile(tracer=...)` 产物**各自独立**。
  **本条的「外层 tracer」仅指 B19F1 注入作用域（`trace_run_scope`）绑定的 tracer**；
  B18F1 的直接 `bind_span_tracer` / `bind_tracer` 绑定**不是** B19F1 注入作用域。
  **优先级写死**：当前存在活动的 B19F1 注入作用域时，**B19F1 作用域优先**（即使外层另有
  B18F1 直接绑定，内层无 tracer 运行仍按本条屏蔽）；当前**没有**活动 B19F1 作用域时，
  B18F1 直接绑定 MUST 保持既有语义（内层 `compile()` MUST NOT 屏蔽它）。
  - 内层编译产物**未注入** tracer，且**当前处于 B19F1 注入作用域内** ⇒ 不产生 span
    （MUST NOT 隐式继承外层 B19F1 producer；`compile(tracer=None)` 在该嵌套下屏蔽外层，
    包括该作用域内的 B18F1 直接绑定）；
  - 内层编译产物**未注入** tracer，且**当前不在 B19F1 注入作用域内**（例如 B18F1 的
    直接绑定夹具）⇒ **不引入新的屏蔽语义**，由既有 B18F1 绑定决定 span 生产；
  - 内层编译产物**注入了** tracer ⇒ **独立一棵树**（独立 `run_id`；其顶层节点 span 的
    `parent` 为 `None`，不挂到外层 span 下）。
  子图统一 trace 树归 **C26 / v2**，本 feature MUST NOT 预留跨图共享载具。

### Key Entities *(include if feature involves data)*

- **`TraceSink`（协议 · B2F1 冻结）**：`on_span_start(span)` / `on_span_end(span)` /
  `current_span() -> Span | None`；用户结构化满足即可，无需继承。本 feature 只**消费**它，
  不重定义。注入点的**运行时最小面** = `on_span_start` / `on_span_end`；`current_span`
  **可选**（freegraph 的 `current_span()` 不委托给它）。
- **`Span`（B2F1 冻结 · 11 字段）**：`id` / `name` / `attributes` / `parent` /
  `start_time` / `end_time` / `context` / `thread_id` / `run_id` / `node` / `checkpoint_id`；
  本 feature **原样消费** B18F1 产出的开始 / 结束两个同 id 快照，不改字段、不改属性面。
- **`SpanProducer`（B18F1 · L5 内部）**：持有 run-scoped 当前 span 栈、父子关系、接收端转发、
  异常隔离；本 feature **复用**并以同一个实例**双绑定** L2 + L5。**不是**公开门面符号。
- **`current_span()`（本 feature 新增 · L5 模块函数）**：返回上下文内当前最内层 `Span`，
  无则 `None`；由 `SpanProducer` 的当前栈提供，**不**委托给 sink 的 `current_span` 方法。
- **注入点 `compile(tracer=...)`**：`StateGraph.compile` 的**可选关键字**；持有用户
  `TraceSink`，每次运行时构造 run-scoped `SpanProducer` 并双绑定。
- **运行关联键**：`run_id`（运行时生成、单次运行一个、用户不可设置）· `thread_id`
  （`RunConfig` 生效值）· `node`（节点内部名）· `checkpoint_id`（有则填、无则 `None`）。
- **补充 trace 记录（本 feature 自有 · 与 `Span` 分离 · 每节点任务一条）**：承载
  `span_id` / `task_id`（标准任务 = 节点名；fan-out 任务 = `节点名:TaskId` · B11F1 F-13）/
  `run_id` / `thread_id` / `checkpoint_id`（与 span 同源同值 · `run_id` 非空）/
  `node` / `superstep` / 触发源（`triggers`；静态边 / `goto` / fan-out / 屏障分组）/
  并发组（`concurrency_group` = 本轮派发集）/ 屏障组（`barrier_groups`，有则）/
  `input_state` / `output_state` / `error`；与节点 span 一一对应，**不另发轮记录**。
  `input_state` = 节点实际入参；`output_state` = **节点原始返回值**（`node.run` raw return；
  归一结果 `writes` / `gotos` / `fanout` 仍用于调度，**不**作为 `output_state`）；
  两者**完整采集**并做 **JSON 安全降级**（不可序列化对象 → 类型名 / 占位符），
  `error` 保留**原抛异常对象**（+ `add_note`）。MUST NOT 写入冻结的 `Span` 字段 / 节点
  `attributes` / `Span.context`。字段名已由 plan 固定为 `triggers` / `concurrency_group` /
  `barrier_groups`；其余容器形状归 plan。
- **可选回调 `on_trace_record(record)`（本 feature 自有 · **非** `TraceSink` 协议成员）**：
  sink 实现则接收补充 trace 记录，不实现则零影响；由 B19F1 在采集后推送。MUST NOT 计入
  已冻结的三方法协议，MUST NOT 要求用户继承任何基类。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：嵌套场景下，**子 span 的 `parent` == 直接父级 span 的 `id`**（逐字相等），
  父子正确率 **100%**；三层嵌套（模型 → 工具 → 模型）父链**逐层**正确、跨层串线数 **0**。
- **SC-002**：未注入 sink（或 `compile(tracer=None)`）**且无任何外层 tracer** 时：
  `on_span_start` / `on_span_end` 调用数 **== 0**、`Span` 构造数 **== 0**、
  `SpanProducer` 构造数 **== 0**、span 专用 `run_id` 绑定数 **== 0**。
  判定：计数夹具 / 构造计数。（`stream()` 既有事件 `run_id` 不计入；B18F1 直接绑定夹具
  不计入本条的「无外层 tracer」。）
- **SC-003**：注入生效时，正常路径与异常路径的 `on_span_start` 数 **==** `on_span_end` 数
  （按 `id` 逐对配对）；异常路径下原始异常对象 / 类型 / 消息**逐字不变**。
- **SC-004**：`current_span()` 在嵌套内返回**内层** span、内层结束后返回**外层** span、
  空上下文返回 `None`（**不抛异常**）；判定：嵌套断言 + 空上下文断言。
- **SC-005**：freegraph 基础安装依赖闭包**仍为空集**；`opentelemetry` / `langchain*` /
  `langsmith` 的 import 次数 **== 0**；环境变量读取次数 **== 0**；设置
  `LANGSMITH_TRACING=true` 后行为不变（回调数 / span 数仍 == 0）。判定：依赖闭包断言 +
  AST / 运行时守卫 + 环境变量差分。
- **SC-006**：注入生效时，每个 span 的 `run_id` **非空**；`thread_id` == `RunConfig` 的
  生效 `thread_id`；`node` == 所属节点内部名；`checkpoint_id` 字段可读（有值或 `None`）。
  `run_id` 为空的数量 **== 0**。
- **SC-007**：同一 `stream()` 运行中，事件与 span 的 `run_id` / `thread_id` **逐字相同**
  （100%）；两条通道不互为前置（不注入 tracer 也能 `stream()`；不 `stream()` 也能 `invoke()`
  产出 span）；`stream()` 信封中 trace 字段数 **== 0**。
- **SC-008**：**当 sink 实现 `on_trace_record` 时**，触发源暴露覆盖 **静态边 + `goto` +
  fan-out** 三类（各至少 1 例），「只暴露 `goto`」或「只暴露静态边」的用例 **0**；执行次序由
  `triggers` / `concurrency_group` **字段内**的确定性顺序判定（标准任务节点名序；含 fan-out
  的轮按**数值** TaskId 序）；同一图多次运行这些字段逐字一致；
  **不要求 `on_trace_record` 到达顺序一致**。
- **SC-009**：**当 sink 实现 `on_trace_record` 时**，同一 super-step 内并发 N 个节点时，
  并发分组（= 本轮**派发集**；含被派发但未启动的取消任务，其自身无 record）**恰好**包含这
  N 个节点、跨轮误并数 **0**；各节点 span 栈独立，跨任务父子 **0**。
- **SC-010**：接收端回调抛出 **`Exception`** 时，图执行结果与不抛时**逐字相同**，异常传播数
  **0**，节点自身异常不被吞；`BaseException` 不在此条隔离范围（MUST NOT 被吞）。
- **SC-011**：`invoke()` / `stream()` 路径的逐节点 record 含
  `(node, input_state, output_state, error)`；`input_state` / `output_state` **完整**
  （不丢 key；`output_state` = 节点原始返回值）、且 `json.dumps(record.to_jsonable())`
  **不抛**；错误载体是**原抛异常对象**（+ `add_note` 可读）；`Span` 11 字段与节点
  `attributes` / `Span.context` **零改动**。
- **SC-012**：sink **实现** `on_trace_record` 时，收到覆盖触发源 / 并发分组 / 屏障分组 /
  逐节点 record 的补充记录（数量与场景匹配）；sink **不实现**时，运行结果与实现时**逐字相同**、
  抛出的属性错误数 **== 0**（不得因缺该可选方法而失败），且 **`TraceRecord` 构造数 == 0、
  `input_state` / `output_state` 采集数 == 0**。判定：`SpanOnlySink` + 计数夹具。
- **SC-013**：输入 / 输出状态里含不可 JSON 序列化的对象时，降级**确定且不抛**：同输入重复运行
  得到同一占位符；原对象内容不出现在 record 的 JSON 文本中；可序列化的普通值**逐字保留**。
- **SC-014**：一次运行中被执行的 N 个节点任务，在 sink 实现 `on_trace_record` 时**恰收到 N 条**
  记录（一节点一条 · 不重不漏）；每条都带 `span_id` / `task_id` / `run_id` / `thread_id` /
  `checkpoint_id` / `node` / `superstep` / 触发源 / 并发组，有屏障时带屏障组；
  `run_id` 非空且 == 对应节点 span 的 `run_id`、`thread_id` == 对应 span 的 `thread_id`；
  同一节点被 `Send` 调用多次时 `task_id` **互不相同**（fan-out = `节点名:TaskId`）且
  `span_id` == 对应节点 span 的 `id`；sink 不实现时收到 **0** 条且运行结果不变。
- **SC-015**：**当 sink 实现 `on_trace_record` 时**，对每个节点任务，sink 记录到的事件序列
  MUST 为 `on_span_start → on_trace_record → on_span_end`（成功与异常路径一致；节点内部产生的
  模型 / 工具子 span 事件可**交错**，但节点自身这三条事件的相对顺序不变）；三处回调内
  `current_span()` 分别返回**新 span / 该节点 span / 父级或 `None`**；顺序错位数 **== 0**。
  未实现时为 `on_span_start → on_span_end`。
- **SC-016**：嵌套 compiled graph 场景：**外层为 B19F1 注入作用域**且内层**未注入** tracer
  ⇒ 内层 span 数 **== 0**、内层 record 数 **== 0**（不隐式继承）；内层**注入** tracer
  ⇒ 内层 span 的 `run_id` 与外层**不同**，且内层顶层节点 span 的 `parent is None`
  （不挂外层）；跨图父子串线数 **== 0**。**B18F1 直接绑定**仅在**当前无活动 B19F1 作用域**时
  不适用本条屏蔽；若外层是 B19F1 注入作用域，则即使作用域内另有直接绑定，也按本条屏蔽
  （FR-021 的优先级口径）。
- **SC-017**：中断与并发取消场景：`record 数 == 节点 span 数`；中断 record 的 `error` 是
  **原 `GraphInterrupt` 对象**（类型 / 消息不变）；**节点自身抛 `CancelledError` 等取消异常时
  record `error` 是原取消 / 异常对象**；**运行期只取消排队未启动任务（已启动任务跑完，不取消）**；
  **从未启动**的取消任务 record 数 **== 0**。

---

## Assumptions

- **注入形态**按本 spec「注入点形态裁定」锁定为 `compile(tracer=...)`；运行作用域内的
  `SpanProducer` 双绑定由本 feature 负责，`compile()` 只持有 sink。
- **`TraceSink` / `Span` / `RunConfig`** 均已由 B2F1 冻结；本 feature 只**接入 / 消费**，
  不重定义、不扩字段。
- **`SpanProducer`** 是 B18F1 的 L5 内部生产者；本 feature **复用**它完成栈 / 父子 / 转发 /
  隔离，**MUST NOT** 另写一套生产逻辑。
- **`current_span()` 的导出位置**为 L5 模块 `freegraph.observability`；不经公开门面
  `freegraph.graph`（门面不得 import L5），`import freegraph` 仍保持惰性。
- **层间例外（2026-11-21 · 发起者一次性追认）**：**R-1**（L3 `_stategraph.py` → L5
  `_inject`，仅 tracer 接线 / 屏蔽）、**R-2**（L5 → L2 私有 `_span_hook` 双绑定，**不读**
  `_stream_context`）、**R-3**（B18F1 断言拆分而不删）**已一并追认**（追认次数 = 1）。
  R-1 / R-2 MUST NOT 扩展为任意 L3 → L5 / L5 → L2 私有依赖。
- **触发源 / 并发分组 / 屏障分组 / 逐节点 record** 的载体是**本 feature 自有**、与 `Span`
  分离的补充 trace 记录；其具体结构由 plan 写死，且 MUST NOT 写入冻结的 `Span` 字段。
- **推送方式**按 2026-11-21 澄清裁定：sink **可选**实现鸭子类型方法
  `on_trace_record(record)`；不实现则只用三方法协议、零影响。该回调**不是** `TraceSink`
  协议成员，不改变三方法冻结面。
- **运行时最小面**：注入的 sink 只需 `on_span_start` / `on_span_end`；`current_span` 可选；
  可选回调 `on_trace_record` 抛出的 **`Exception`** 与 span 回调**同款隔离**（FR-017），
  不改变图执行结果；`BaseException` 不吞。
- **静态类型 vs 运行期最小面**：`compile(tracer=...)` 的静态注解仍为 `TraceSink | None`；
  `SpanOnlySink`（缺 `current_span`）是有意的运行期鸭子类型扩展，测试用 `typing.cast` /
  `# type: ignore` 表达，MUST NOT 误称其静态满足三方法协议。
- **逐节点内容**按 2026-11-21 澄清裁定：`input_state` = 节点实际入参；`output_state` =
  **节点原始返回值**（`node.run` raw return）；两者**完整采集**并做 **JSON 安全降级**
  （不可序列化对象 → 类型名 / 占位符）；`error` 保留**原抛异常对象**（+ `add_note`）。
  降级由 B19F1 负责，B20 可直接落 JSONL。
- **记录粒度**按 2026-11-21 澄清裁定：**每个节点任务一条**补充 trace 记录（含
  `span_id` / `task_id`（B11F1 F-13）/ `run_id` / `thread_id` / `checkpoint_id` /
  `superstep` / 触发源 / 并发组 / 屏障组 / `input/output/error`），**不另发轮记录**；
  与节点 span 一一对应，关联键**同源同值**。
- **回调顺序**按 2026-11-21 澄清裁定：**当 sink 实现 `on_trace_record` 时**顺序为
  `on_span_start → on_trace_record → on_span_end`；未实现时为 `on_span_start → on_span_end`。
  `current_span()` 在 `on_span_end` 内已恢复为父级（沿用 B18「先出栈再转发」，不改生产者）。
- **跨编译产物嵌套**按 2026-11-21 澄清裁定：v1 **不统一** trace 树——各编译产物独立；
  **外层为 B19F1 注入作用域**时内层未注入 ⇒ 无 span；**外层为 B18F1 直接绑定且当前无活动 B19F1 作用域**时保持既有
  继承语义；内层注入 ⇒ 独立树（独立 `run_id`、顶层 `parent=None`）；子图统一树留
  v2 / C26（FR-021）。
- **记录与 span 对齐**按 2026-11-21 澄清裁定：凡产生节点 span 的任务产**一条** record；
  中断 `error` = 原 `GraphInterrupt`；节点自身抛 `CancelledError` 等取消异常 = 原取消 / 异常；
  **运行期只取消排队未启动任务（已启动任务跑完，不取消）**；从未启动 = 无 record
  （FR-015 / SC-017）。
- **`harness/demo/README.md`** 的 `compile(tracer=...)` 条目在本 feature 实现期由「待锁定」
  更新为「已锁定」，依据 = 本 spec 的形态裁定。
- **环境基线**：Python ≥ 3.11；零第三方运行时依赖；零出站；零环境变量。
- **验收可在无真实 SaaS 账号下完成**：sink 由用户自有实现（测试用记录型 sink 即可），
  不需要 LangSmith / OTLP 端点。

---

## 发起者追认与质量门禁偏离（2026-11-21）

> **架构例外一次性追认**：**R-1**（L3 `_stategraph.py` → L5 `observability/_inject.py`）、
> **R-2**（L5 `observability/_inject.py` → L2 `runtime/_span_hook.py`，**仅**
> `bind_span_tracer`；**不读** `_stream_context`）、**R-3**（B18F1「L5 只 import 标准库 + L1」
> 断言**拆分而不删**）一并追认；**追认次数 = 1**。
> MUST NOT 扩展为任意 L3 → L5 / L5 → L2 私有依赖的通行证。
> 确认人：杨家成 · 日期：2026-11-21。

> **质量门禁 5 偏离登记**：本 feature 不依赖外部模型 provider；人工验收采用
> **fake 轮 + 本地真实 `TraceSink` 轮**。外部真实模型轮按宪法 v1.6.0
> 「质量门禁的分阶段落地」登记偏离，承接方 **B21F1**（真实 OTLP 后端）；
> **发起者确认：杨家成 · 日期：2026-11-21**。MUST NOT 伪装成已通过。

---

## Dependencies & Out of Scope

- **前置依赖**：B18F1（span 生产 · `SpanProducer` / L2 节点接缝 / `bind_run_ids`）。
- **契约 / 内核依赖**：B2F1（`Span` / `TraceSink` 冻结面）· B7F1（调度触发源 /
  `SuperStepResult` 形状）。
- **承接依赖**：B9F1（触发源同源口径）· B11F1（fan-out 派发任务）· B12F1（并发分组 /
  确定性次序）· B7F4（屏障触发）· B8F2（两条通道共享 id）· B8F3（`context` 与 trace 分离）。
- **后续解锁**：**B20F1**（本地 Trace 存储 JSONL）→ **B20F2**（查询 API + SQLite 后端）
  → **B21F1**（OTLP 导出）。
- **明确不做**：本地 trace 存储与查询（B20F1 / B20F2）· OTLP 导出（B21F1）·
  `compile(tracer=...)` 之外的注入形态 · 前端 UI（v2 / B26）· 评测 / 数据集（永不做）·
  自研 OTLP 编码（B21F1 明确不采用）· **跨 compiled graph 的 trace 树统一**（C26 / v2 · FR-021）。

---

## Acceptance Criteria（= 立项书 §5.2 B19F1 小目标，逐条可判定）

> 小目标原文：**嵌套 span 父子关系正确；不注入 tracer 时零副作用；
> 补充记录与节点 span 一一对齐**

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 嵌套 span 父子关系正确 | 父子断言（子 span `parent` == 父 span `id`；三层嵌套逐层） |
| A2 | 不注入 tracer 时零副作用 | 回调计数 == 0 且 span 构造计数 == 0 且 span 专用 `run_id` 绑定数 == 0 |
| A3 | `current_span()` 可用 | 嵌套场景断言（内层 → 外层）+ 空上下文返回 `None` |
| A4 | 注入即推送、成败皆成对 | start / end 计数相等、按 `id` 配对；异常原样重抛 |
| A5 | 与 `stream()` 同源同 id | 同一次运行的 `run_id` / `thread_id` 逐字相同 |
| A6 | 补充记录与节点 span 对齐 | `record 数 == 节点 span 数`；触发源 / 并发组 / 屏障组可判定（SC-014 / SC-017） |
| A7 | 零依赖 / 零环境变量 / 零出站 | 依赖闭包空、env 读取 0、`LANGSMITH_TRACING` 不改变行为（SC-005） |
