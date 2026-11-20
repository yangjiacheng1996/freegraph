# 上游对照：B18F1 · Span 生产

**Feature**: `B18F1` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**上游版本**: `langgraph` **1.2.11** · `langchain-core` **1.7.6** · `langsmith` **0.14.17**
（取证于 2026-11-20 · 本仓库 `.venv` 实测）
**证据**: [research.md](../research.md) §2（E-1…E-4）

---

## §0 口径

上游**没有** freegraph 这样的「自有 `Span` 数据类 + 自有 span 生产协议」。上游的可观测挂钩是
`callbacks` / `tracers`，其 span 数据模型来自 `langsmith.RunTree`；`langchain-core` 的
`Requires-Dist` **硬依赖** `langsmith`。因此本 feature 的主体落在宪法原则 XI 的
**必须自研区 ③（上游没有的能力）** 与 **①（零账号 / 零主动出站 / 零依赖）**；
只有「默认关闭」「父子关系」「失败也成对」三类**行为面**与上游对齐。

---

## §1 逐条对照（P-01…P-11）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| **P-01** | 无 tracer / handler 时不产生观测对象 | `langgraph/pregel/_retry.py:617`（`task.proc.invoke`）· `langgraph/pregel/main.py:2919`（`has_graph_lifecycle_callbacks=bool(...)`）· 实测 **E-1** | 未绑定 tracer ⇒ span 构造数 == 0 / 回调数 == 0 | **SAME** | 默认关闭是上游同款行为面 |
| **P-02** | 每个节点执行产生一个观测单元 | `langgraph/pregel/_retry.py:617` · `langchain_core/runnables/base.py:2344`（`on_chain_start`）/ `:2369`（`on_chain_end`）· 实测 **E-2** | 每次节点任务执行一个节点 span（开始 + 结束） | **DIFF** | 上游是 LangChain callback run / LangSmith `RunTree`；freegraph 是自有 11 字段 `Span` ⇒ 自研区 ③ |
| **P-03** | 父子关系（嵌套） | `langchain_core/callbacks/manager.py:510,532,623` · `langchain_core/tracers/base.py:47,53` · 实测 **E-2** | `parent` = 父 span 的 `id` 字符串；模型 / 工具 span 的 parent = 所在节点 span id；嵌套逐层 | **DIFF** | 语义 SAME、表示不同（id 字符串 vs 对象引用）；B2F1 已冻结 |
| **P-04** | 模型调用 span | `langchain_core/tracers/base.py:61`（`on_chat_model_start`）· `:108`（`on_llm_start`） | `invoke_model` ⇒ 模型 span（`gen_ai.operation.name=chat`） | **DIFF** | 上游依赖 `langchain-core` + tracer handler；freegraph 零 LangChain、零依赖 ⇒ 自研区 ①③ |
| **P-05** | 工具调用 span | `langchain_core/tracers/base.py:363`（`on_tool_start`）· `:408`（`on_tool_end`） | `invoke_tool` ⇒ 工具 span（`gen_ai.operation.name=execute_tool`） | **DIFF** | 同上 |
| **P-06** | span 字段面 | `langsmith/run_trees.py:403-409`（`RunTree`）· `:689`（`end_time`） | **11 字段逐字冻结**（B2F1）；无 `run_type` / `events` / `status` | **DIFF** | 字段面归 B2F1；`run_type` 的语义由 `name` + `attributes` 表达 |
| **P-07** | 默认关闭是否受环境变量影响 | `langchain_core/tracers/context.py:141-144` · `langsmith/utils.py:119-140` | **只认显式注入的 `SpanProducer` / receiver**；MUST NOT 读 env；`LANGSMITH_TRACING=true` 不改变行为 | **STRICTER** | 宪法原则 I / 配置层黑名单 |
| **P-08** | 运行时依赖闭包 | `langchain-core 1.7.6` 的 `Requires-Dist` 含 `langsmith<1.0.0,>=0.14.9`（+ `certifi` / `httpx` / `pydantic` 等）· 实测 **E-4** | 基础安装闭包**为空集**；无 `opentelemetry-*` / `langchain*` / `langsmith` | **STRICTER** | 宪法原则 I / II / IX |
| **P-09** | 失败路径仍观测到耗时 | `langchain_core/runnables/base.py:2366` · `langchain_core/tracers/base.py:335` / `:428` · 实测 **E-3** | 异常时仍产出同 id、已填 `end_time` 的结束 span，然后原样重抛 | **SAME**（语义）· **DIFF**（表示） | 「失败也成对」；表示差异随 P-02 / P-06 |
| **P-10** | 节点 span 的属性面 | 上游无「节点 span」概念；chain run 的 `extra` / `metadata` 是自由字典（`langchain_core/tracers/base.py:61-105`） | 节点 span 属性为**空映射** | **DIFF** | Q6 允许自定义命名空间；B18F1 取更小的空映射（Q11）⇒ **X-3** |
| **P-11** | 输入 / 输出内容采集 | `langsmith/schemas.py:284-285` · `langsmith/run_trees.py:498-500` | v1 默认不采集内容属性 | **DIFF** | semconv 内容属性为 Opt-In；v1 取隐私 / 体积最小面 ⇒ **X-4** |

---

## §2 实测基线（E-1…E-4）

| # | 实验 | 结果 |
|---|---|---|
| **E-1** | 两节点线性图 `a → b`，不传 `callbacks` | 正常返回；**无任何** callback 事件 |
| **E-2** | 同图，传自定义 `BaseCallbackHandler` | 6 条事件；节点 run 的 `parent_run_id` == 图 run 的 `run_id` |
| **E-3** | 两节点图 `a → boom`（抛 `RuntimeError`），传 handler | 异常原样抛出；`start`（图）→ `start`（a）→ `end`（a）→ `start`（boom）→ `error`（boom）→ `error`（图） |
| **E-4** | `importlib.metadata.requires("langchain-core")` | 含 `langsmith<1.0.0,>=0.14.9`；`langsmith` 实测 `0.14.17` |

---

## §3 差分场景组（D-201…D-208）

| # | 场景 | 断言 | 判词 |
|---|---|---|---|
| **D-201** | 无 tracer / 无 handler | freegraph：span 构造数 == 0；上游：callback 事件数 == 0；两侧图都正常完成 | SAME（P-01） |
| **D-202** | 两节点线性图 | freegraph：2 个节点 span；上游：2 组节点 callback；两侧最终状态逐字相等 | SAME（行为面）· DIFF（表示，P-02） |
| **D-203** | 节点 → 工具 → 模型嵌套 | freegraph：模型 span 的 parent == 工具 span id，工具 span 的 parent == 节点 span id；上游：对应 run 的 `parent_run_id` 逐层正确 | SAME（父链语义）· DIFF（表示，P-03） |
| **D-204** | 模型 / 工具属性键 | freegraph：模型 / 工具属性键**除失败时的 `error.type` 外** 100% 命中 `gen_ai.*` 允许清单；上游：属性由 LangSmith run 的 inputs / outputs / extra 表达 | DIFF（P-04 / P-05） |
| **D-205** | 环境变量 | 设置 `LANGSMITH_TRACING=true` 且不传 tracer：freegraph span 数 == 0；上游可能自动开启 tracer | STRICTER（P-07） |
| **D-206** | 异常节点 | freegraph：结束 span 仍产生、异常原样重抛；上游：`on_chain_error` 仍触发、异常原样重抛 | SAME（P-09） |
| **D-207** | 依赖闭包 | freegraph 基础安装闭包为空；上游 `langchain-core` 闭包含 `langsmith` | STRICTER（P-08） |
| **D-208** | 并发 3 节点 | freegraph：3 个独立节点 span、无跨任务父子；上游：3 组节点 run、`parent_run_id` 均相同 | SAME（并发独立）· DIFF（表示） |

⇒ **判词分布**：SAME 行为面 5（D-201 / D-202 / D-203 / D-206 / D-208；其中 **D-202 / D-203 / D-208 同时含表示层 DIFF**）+ 纯 DIFF 1（D-204）+ STRICTER 2（D-205 / D-207）。

---

## §4 偏离登记（仅限三类）

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **DIFF**（自研区 ③） | 上游无自有 `Span` / 无自有三级 span 生产协议（对应 P-02 / P-03 / P-04 / P-05 / P-06 / P-09） | freegraph 的可观测协议必须自研（C23 / C24）；字段面已由 B2F1 冻结；引入上游方案即破零依赖红线 | B2F1（字段面）· 本 feature（生产） |
| **X-2** | **STRICTER**（自研区 ①） | 上游 tracing 由 `langchain-core` + `langsmith` 承载，且可由 env 自动开启（对应 P-07 / P-08） | freegraph 零第三方依赖、零 env、零主动出站；只认显式 tracer | 宪法原则 I / II / IX |
| **X-3** | **DIFF**（自研区 ③） | 节点 span 的属性面（对应 P-10） | 节点执行不是 GenAI 模型 / 工具操作；Q6 允许自定义命名空间，B18F1 取更小的空映射（Q11） | 本 feature |
| **X-4** | **DIFF**（自研区 ③） | 默认不采集输入 / 输出内容（对应 P-11） | semconv 内容属性为 Opt-In；v1 只采结构化元数据 | 本 feature |

---

## §5 破冻结面

**无**。本 feature 不修改 `Span` 11 字段 / `TraceSink` / `RunConfig` / `SuperStepResult` /
`PregelTask` / `stream()` 信封 / 节点签名 / 公开门面符号。新增的 `bind_run_ids` 是 **L2 私有助手**
（不进 `__all__` / 兼容矩阵），与 `StreamSession` 的 `bind_stream` 使用同一对 contextvar，不新增第二套载体。
