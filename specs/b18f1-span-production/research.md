# B18F1 · Phase 0 研究记录（架构决策 + 上游实测 + 代码锚点）

**Feature**: B18F1 · Span 数据类生产（节点 / 工具 / 模型三级 span）

**Date**: 2026-11-20

**Spec**: [spec.md](./spec.md)

> **范围**：本文件只记录 **Phase 0 研究** 的结论与证据；不修改源码。
> 设计决策编号 **D-01…D-15** 与 spec 的 Clarifications Q1–Q16 对应（**多对一映射**；不新增产品决策）。

---

## §0 方法与取证环境

### 0.1 环境

| 项 | 值 |
|---|---|
| Python | `.venv` · CPython **3.11.16** |
| `langgraph` | **1.2.11** |
| `langchain-core` | **1.7.6** |
| `langsmith` | **0.14.17** |
| 基线测试 | `1778 passed, 6 skipped in 121.56s`（2026-11-20 · `.venv/bin/python -m pytest -q --tb=no`） |
| 零仓库改动 | 本阶段只读源码 / 跑既有测试；不写 `src/` / `tests/` |

### 0.2 证据分级

- **E-xx**：上游 / 依赖的**实测**（脚本为临时文件，不进仓库）；
- **A-xx**：freegraph 既有代码锚点（`路径:行号`，本轮实际核对）；
- **D-xx**：设计决策（来自 spec 的 Q1–Q16 + 现有架构约束）。

---

## §1 设计决策（D-01…D-15）

### D-01 节点 span 的产生点 = L2 单一节点执行接缝

- **决策**：在 `src/freegraph/runtime/superstep.py:1361-1368` 的 `_run_round._bind._inner`
  包住 `fn()`：开始时构造节点 `Span`，结束时构造同 `id` 的结束 `Span`；异常时先结束再原样重抛。
- **理由**：节点执行在 L2；`_run_round` 是**唯一**并发任务入口（标准任务 + fan-out 任务共用）；
  在这里包一次即可覆盖所有节点任务，且**不改** `NodeSpec.run` 签名 / `node_input` / 状态。
- **替代被拒**：在 `_stategraph.add_node` 包用户函数 ⇒ 改构建期语义、可能改变用户函数身份；
  在 `_execute_node_pure` 内包 ⇒ 只覆盖纯执行，无法与并发任务上下文对齐（仍可，但 `_bind` 已提供
  `bind_current_task` / `bind_task`，更自然）。

### D-02 L2 与 L5 解耦 = L2 私有 hook + 鸭子类型 tracer

- **决策**：
  - L2 新增 `runtime/_span_hook.py`（私有）：
    `bind_span_tracer()` / `current_span_tracer()` / `start_node_span()` / `end_node_span()`；
  - tracer 是**鸭子类型对象**（`on_span_start` / `on_span_end` / `current_span_id`），
    **不要求**继承基类；L2 **不 import** `freegraph.observability`；
  - L5 新增 `observability/_producer.py` 提供 `SpanProducer` 实现；
  - L2 `_span_hook.py` 定义私有 `typing.Protocol` `_SpanTracer`（三个方法）；
    L5 `SpanProducer` 结构化满足它，但 **MUST NOT import** 它（保持 L5 零 L2 import）；
  - L5 **零 L2 import**：`run_id` / `thread_id` / `node` 从当前节点 span 继承，不直接读 `_stream_context`。
- **理由**：ARCH-1 禁止 L2 → L5 反向 import；ARCH-3 要求跨层经 Protocol + 纯数据。
  鸭子类型 + `Span`（L1）满足两者；L2 只需要「能回调、能问当前 id」的最小面；
  L5 不读 L2，连 B8F2 的 id 例外都不需要（由节点 span 继承）。
- **替代被拒**：L2 import L5 ⇒ 反向依赖；把 tracer 放进 `RunConfig` ⇒ 改冻结类型 + 配置面污染；
  全局单例 ⇒ 不可并发 / 不可测试。

### D-03 当前 span 栈 = L5 `SpanProducer` 的 ContextVar

- **决策**：`SpanProducer` 持有
  `ContextVar[tuple[_SpanFrame, ...]]`；`_SpanFrame(span, kind)`；
  `on_span_start` 入栈、`on_span_end` 出栈；`current_span_id()` 读栈顶。
- **理由**：父子 / 嵌套 / 并发隔离都是**生产者语义**；L2 只报「节点边界」。
  B8F2 已证明线程池每任务 `copy_context()`（`runtime/_concurrency.py:223`）⇒ ContextVar 天然隔离。
- **替代被拒**：把栈放 L2 ⇒ L5 辅助函数需 import L2 业务模块（违反 FR-021）；
  把栈放 L1 ⇒ 契约层带行为。

### D-04 invoke 路径 `run_id` = `run_graph` 一次绑定

- **决策**：
  - `stream()`：`StreamSession.__enter__` 已通过 `bind_stream` 绑定
    `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`（`runtime/_stream.py:110-118`）⇒ **零改动**；
  - `invoke()`：`run_graph`（`runtime/superstep.py:2239-2255`）在
    **tracer 已绑定 且 `current_stream_ids()[0] is None`** 时，用
    `bind_run_ids(uuid4().hex, run_config.resolved_thread_id())` 绑定一次；
  - 已有 id（嵌套 / stream 内调用）⇒ **不覆盖**。
- **理由**：spec Q4 / FR-012；`RunConfig.run_id` 仍被忽略；不新增第二套载体。
- **替代被拒**：每个 span 各生成 id ⇒ trace 树散架；用 `bind_stream` 绑定 invoke ⇒
  会意外绑定 stream writer / custom sink，改变节点内 `get_stream_writer()` 行为。

### D-05 `checkpoint_id` = v1 恒 `None`

- **决策**：节点 span 的 `checkpoint_id` 取运行期接缝值（v1 为 `None`）；模型 / 工具 span **从当前节点 span 继承**同一值。字段仍可读。
- **理由**：当前运行时没有 checkpoint 标识来源；spec Q5 / D-4；B14F1 后续只需通过既有接缝补**节点 span**，不改字段面。**MUST NOT** 伪造。

### D-06 时间源 = 标准库 + UTC ISO-8601（9 位小数）+ 严格正耗时

- **决策**：
  - 取 `time.time_ns()`；
  - 格式：`YYYY-MM-DDTHH:MM:SS.<9 位纳秒>+00:00`（标准库 `datetime` + 手写小数位）；
  - 结束时间保证 `end_ns > start_ns`；若相等，`end_ns = start_ns + 1`（1ns，不伪造微秒级）；
  - L2 与 L5 各有一份**等价的小助手**（层隔离，不能共享业务模块）。
- **理由**：spec FR-009 / SC-005；不引入 `opentelemetry-*`；ISO-8601 允许任意小数位。
- **替代被拒**：`datetime.isoformat(timespec="microseconds")` 可能在极快调用下相等 ⇒ SC-005 红；
  用 `perf_counter` 做展示时间 ⇒ 不是 UTC 墙钟。

### D-07 模型 / 工具属性 = Q9 极简集

- **决策**：
  - 模型：`gen_ai.operation.name`（v1 **恒为 `chat`**）+ `gen_ai.request.model`（`model_name` → `model`）；
  - 工具：`gen_ai.operation.name`（`execute_tool`）+ `gen_ai.tool.name`（`obj.name`）+
    `gen_ai.tool.call.id`（仅显式 `call_id` 参数）；
  - 其余 semconv 属性（provider / usage / response / finish_reasons / temperature /
    tool.description / conversation.id）**不写**。
- **理由**：spec Q9；通用图框架 + 隐私最小面；避免读第三方私有属性。
- **替代被拒**：尽力读取 `_llm_type` / `usage_metadata` ⇒ 脆弱、跨 provider 不一致、隐私风险。

### D-08 节点属性 / `Span.context` = 恒空映射

- **决策**：节点 span `attributes={}`；所有 span `context={}`。
- **理由**：spec Q11 / Q15；Q6 允许自定义命名空间，B18F1 取更小面；C21 的 `context` 与
  `Span.context` 严格分离（B8F3 D-2 / D-3）。
- **替代被拒**：节点加 `freegraph.superstep` / task id ⇒ 提前扩面，归 B19F1；
  `Span.context` 承载 C21 ⇒ 违反 B8F3。

### D-09 `error.type` = 仅模型 / 工具失败

- **决策**：模型 / 工具 span 失败时写 `error.type = type(exc).__name__`（空则 `_OTHER`）；
  节点 span 不写；成功时任何 span 不写。
- **理由**：spec Q12 / FR-018；GenAI semconv 的 `error.type` 条件必填；节点 span 保持空映射。
- **替代被拒**：节点也写 ⇒ 与 Q11 冲突；完全不写 ⇒ 失败 span 无可分类信息。

### D-10 辅助函数行为 = 显式意图 + 快速失败

- **决策**：
  - `invoke_model(obj, input, *, call_id=None)`：要求 callable `invoke` **且非工具形状**；
  - `invoke_tool(obj, args, *, call_id=None)`：要求 `name`（str）+ `description` + callable `invoke`；
  - 形状不匹配 ⇒ `TypeError`；
  - 结果 awaitable ⇒ 结束当前 span（若存在）后 `TypeError`；
  - 无活动节点 span ⇒ 校验通过后直接 `obj.invoke(...)`，不产生 span。
- **理由**：spec Q13 / Q14 / Q16；显式、可预测、通用。
- **替代被拒**：自动按形状改判 ⇒ 函数名与层级不一致；静默返回 awaitable ⇒ span 耗时不覆盖真实执行。

### D-11 零开销守卫 = 一次 contextvar 读取

- **决策**：
  - `_run_round._bind._inner` 每任务一次 `current_span_tracer()`；`None` ⇒ 直接 `fn()`；
  - `run_graph` 每 run 一次 `current_span_tracer()`；`None` ⇒ 不绑定 id；
  - 未绑定 ⇒ 不构造 `Span` / 不生成 **span 专用** `run_id` / 不调用接收端 / 不读 env；
  - `freegraph/__init__.py` 不 import L5。
- **理由**：spec FR-002 / SC-003 / SC-004 / SC-012；原则 IV。
- **替代被拒**：全局开关 / 环境变量 ⇒ 违反零环境变量；每次节点构造一个 no-op 对象 ⇒ 非零分配。

### D-12 并发隔离 = 每任务 `copy_context()`

- **决策**：沿用 B8F2 / B12F1 的 `run_tasks_concurrently` 每任务 `copy_context()`；
  L5 `SpanProducer` 栈为 ContextVar；不新增第二套传播。
- **理由**：`runtime/_concurrency.py:223` 已实现；spec FR-024 / SC-010。
- **替代被拒**：全局锁保护共享栈 ⇒ 串行化 / 跨任务串父；线程局部 `threading.local` ⇒
  与 `copy_context` 体系重复。

### D-13 接收端异常 = 隔离 + 可选 warning

- **决策**：接收端 `on_span_start` / `on_span_end` 抛出的异常 MUST 被隔离；MAY 通过标准库
  `logging` 记录一次 warning；不传播、不改变图执行结果、不吞节点异常。
- **理由**：spec FR-025；上游 `langchain_core/callbacks/manager.py:351-354` 同款
  （catch + `logger.warning`）。
- **替代被拒**：让接收端异常传播 ⇒ 观测故障改变业务结果；完全静默 ⇒ 用户难以发现坏 tracer。

### D-14 公开面 = 零扩张

- **决策**：`freegraph.graph` 门面 / `freegraph.runtime.__all__` / L1 契约符号 **零新增**；
  helpers + `SpanProducer` 只在 `freegraph.observability` 模块；B19F1 决定是否再导出。
- **理由**：spec FR-022 / Q8；B2F2 / B2F1 的冻结面。
- **替代被拒**：加进门面 ⇒ API 快照红；加进 L1 ⇒ 契约膨胀。

### D-15 原则 IV 的字段载体 = 组合载体

- **决策**：B18F1 的节点 span 只承担节点名 / 耗时；输入状态 / 输出状态由
  `stream()` 的 `values` / `updates` / `tasks` + `PregelTask.result` 承担；错误由**原样抛出的异常**（+ `add_note`）承担，`PregelTask.error` 不作为失败路径载体；
  `invoke()` 路径的逐节点三项由 B19F1/B20 承接（spec D-6 / FR-029 / SC-016），且承接机制 MUST 写死；B19F1/B20 的 spec MUST 落成该承接（目标提示词已接线）。
- **理由**：宪法原则 IV 的「可观测记录」可由多个产物组合，不要求塞进单个 `Span`；
  Q11/Q12 的极简属性面保持不变；避免把大对象 / 敏感内容塞进 span 属性。
- **替代被拒**：把输入 / 输出 / 错误写进节点 span ⇒ 破 Q11、隐私 / 体积 / JSON 风险；
  不映射载体 ⇒ 原则 IV 缺口被隐藏。

---

## §2 上游实测基线（E-1…E-4）

> 版本：`langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`（2026-11-20）。

| # | 实验 | 结果 |
|---|---|---|
| **E-1** | 两节点线性图 `a → b`，不传 `callbacks`，`app.invoke({"x":0})` | 正常返回 `{"x":2}`；**无任何** callback 事件 ⇒ 默认关闭是上游同款行为面 |
| **E-2** | 同图，传入自定义 `BaseCallbackHandler` | 6 条事件：图 run 开始 → a 开始 / 结束 → b 开始 / 结束 → 图 run 结束；节点 run 的 `parent_run_id` == 图 run 的 `run_id` |
| **E-3** | 两节点图 `a → boom`（`boom` 抛 `RuntimeError("boom")`），传 handler | 异常原样抛出；事件序列 = `start`（图）→ `start`（a）→ `end`（a）→ `start`（boom）→ `error`（boom）→ `error`（图）⇒ 异常路径仍完成 run 生命周期 |
| **E-4** | `importlib.metadata.requires("langchain-core")` | 包含 `langsmith<1.0.0,>=0.14.9`（+ `certifi` / `httpx` / `pydantic` / `pyyaml` 等）；`langsmith` 实测 `0.14.17` |

**上游源码锚点**：

- `langgraph/pregel/_retry.py:617`（节点任务 `task.proc.invoke`）
- `langgraph/pregel/main.py:2919`（`has_graph_lifecycle_callbacks=bool(...)`）
- `langchain_core/runnables/base.py:2344`（`on_chain_start`）/ `:2366`（`on_chain_error`）/ `:2369`（`on_chain_end`）
- `langchain_core/callbacks/manager.py:351-354`（回调异常 catch + `logger.warning`）
- `langchain_core/callbacks/manager.py:510,532,623`（`parent_run_id` 构建 / 传递）
- `langchain_core/tracers/base.py:47,53`（父 id 解析）/ `:61`（`on_chat_model_start`）/
  `:108`（`on_llm_start`）/ `:335`（`on_chain_error`）/ `:363`（`on_tool_start`）/
  `:408`（`on_tool_end`）/ `:428`（`on_tool_error`）
- `langchain_core/tracers/context.py:141-144`（tracing 开关回落）
- `langsmith/utils.py:119-140`（最终读取 `TRACING_V2` / `TRACING` env）
- `langsmith/run_trees.py:403-409`（`RunTree` 字段）/ `:498-500`（自动补 `outputs`）/ `:689`（`end_time`）
- `langsmith/schemas.py:284-285`（RunBase 的 `inputs` / `outputs`）

---

## §3 freegraph 代码锚点（A-01…A-12）

| # | 锚点 | 与本 feature 的关系 |
|---|---|---|
| **A-01** | `src/freegraph/contracts/trace.py:27-92` | `Span` 11 字段（B2F1 冻结）· 只构造，不改 |
| **A-02** | `src/freegraph/contracts/types.py:180-260` | `RunConfig` 九字段 · `resolved_thread_id()` · 零改动 |
| **A-03** | `src/freegraph/runtime/_stream_context.py:91-122` | `_STREAM_RUN_ID` / `_STREAM_THREAD_ID` / `current_stream_ids()` |
| **A-04** | `src/freegraph/runtime/_stream_context.py:126-160` | `bind_stream()` 生命周期 · 本 feature 不改 |
| **A-05** | `src/freegraph/runtime/_stream.py:50-118` | `StreamSession.__enter__` 已绑定 id / writer / sink |
| **A-06** | `src/freegraph/runtime/superstep.py:991-999` | `_execute_node_pure`（纯执行） |
| **A-07** | `src/freegraph/runtime/superstep.py:1295-1368` | `_run_round` / `_bind._inner`（节点接缝） |
| **A-08** | `src/freegraph/runtime/superstep.py:2187-2255` | `run_graph` 图级入口 / `resolve_config` |
| **A-09** | `src/freegraph/runtime/_concurrency.py:185-230` | `run_tasks_concurrently` / 每任务 `copy_context()` |
| **A-10** | `src/freegraph/_stategraph.py:631-677` | `invoke()` 门面（零改动） |
| **A-11** | `src/freegraph/_stategraph.py:678-699` | `stream()` / `run_id = uuid4().hex` / `StreamSession` |
| **A-12** | `src/freegraph/runtime/__init__.py:111` | `__all__`（零新增符号） |

---

## §4 受影响面与预登记红点

| 面 | 是否改 | 说明 |
|---|---|---|
| `contracts/trace.py` | ❌ | `Span` / `TraceQuery` 冻结 |
| `contracts/types.py` | ❌ | `RunConfig` 冻结 |
| `contracts/protocols.py` | ❌ | `TraceSink` 冻结；B19F1 接入 |
| `runtime/_stream_context.py` | ✅（私有扩展） | 新增 `bind_run_ids()`；`bind_stream` 不动 |
| `runtime/_span_hook.py` | ✅（新增） | L2 私有 hook |
| `runtime/superstep.py` | ✅（小改） | `_run_round._bind` 包节点；`run_graph` 绑 id |
| `runtime/_stream.py` | ❌ | `StreamSession` 已绑定 |
| `runtime/_concurrency.py` | ❌ | 既有 `copy_context` |
| `observability/*` | ✅（新增） | L5 生产引擎 + helpers |
| `freegraph/__init__.py` | ❌ | 保持惰性 |
| `freegraph/graph.py` | ❌ | 门面零扩张 |
| 公开 API 快照 | ❌ | 零新增符号 |

**预登记红点**：见 `plan.md` 的「绿基线记录 / 变红清单」B-1…B-6。

---

## §5 遗留登记（DR-1…DR-4）

| # | 遗留 | 处置 |
|---|---|---|
| **DR-1** | `checkpoint_id` 在 v1 恒 `None` | 节点 span 取运行期值、子 span 继承；B14F1 后续通过既有接缝补**节点 span**（D-4）；本 feature 不伪造 |
| **DR-2** | 真实外部模型轮不可达 | fake 轮必跑；真实轮优先本地真实对象；若审查要求 provider 轮 ⇒ 偏离登记 + 追认（R-3） |
| **DR-3** | 模型名 / provider 的鸭子类型属性 | v1 只读 `model_name` / `model`；provider / usage 等不读（Q9） |
| **DR-4** | B19F1 的双绑定接缝 | L2 hook + L5 `SpanProducer` 都要绑定；B19F1 的公开注入 MUST 构造 `SpanProducer` 并同时绑两处（R-4）；目标提示词已接线 |

---

## §6 Phase 0 结论

1. **架构可行**：L2 单一节点接缝 + L2 私有 hook + L5 生产者 / helpers 的组合满足
   ARCH-1 / ARCH-2 / ARCH-3，且不需要 L2 → L5 或 L2 → L4 的反向 import。
2. **零开销可测**：未绑定 tracer 时，节点接缝只做一次 contextvar 读取 + `is None`；
   不构造 `Span`、不生成 **span 专用** `run_id`、不读 env。
3. **关联键可闭合**：`stream()` 复用 B8F2 的两个 id；`invoke()` 由 `run_graph` 一次绑定；
   `checkpoint_id` 可为 `None`（B14F1 后续补值）。
4. **属性面可判定**：模型 / 工具只写 Q9 最小集；节点 / `context` 恒空；
   `error.type` 仅模型 / 工具失败。全部有 semconv 出处。
5. **无 NEEDS CLARIFICATION**：spec Q1–Q16 已收敛；剩余为 `/speckit.tasks` 的任务拆解，
   不是产品决策。
