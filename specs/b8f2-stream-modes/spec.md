# Feature Specification: B8F2 · `stream()`：多模式流式输出 + `StreamWriter`

**Feature Branch**: `b8f2-stream-modes`

**Created**: 2026-11-19

**Status**: Draft

**Input**: User description: "B8F2 · `stream()`：多模式流式输出 + `StreamWriter` —— 交付 `stream()`：以**流式**方式产出运行过程事件，支持多种流式模式（`values` / `updates` / `checkpoints` / `tasks` / `debug` / `messages` / `custom`），让用户能在图运行过程中实时观察每一步的产出；并提供节点侧 `StreamWriter`（`custom` 模式的来源）。本 feature 的判定是：**多模式流式输出**。前置依赖 **B7F3**。"

> 注：`custom` 的「实时」按 **P-23 / X-6** 收敛为**轮末批量**（每轮结束后按 TaskId 序产出）；
> 其余 mode 的「逐轮观察」语义不变。

---

## 承接条款（上游 feature → 本 feature）

> 宪法 v1.12.0「跨 feature 承接的接线通则」：上游 feature 指名本 feature 的跨 feature 义务
> MUST 在本 spec 落成 **FR + 裁定**；**只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽判据**。

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B7F3 → B8F2** | **M2** | **「完整状态」的归一**：`stream()` 的 `values` 档 MUST 与 B7F3 的 `invoke()` **逐字同款**（同一份「稀疏视图 + 补齐无值 key」的归一 ⇒ **单一实现点**）⇒ ⇒ MUST NOT 另写一份「补齐」逻辑；`updates` 档（增量）**不受**本口径约束。<br>⚠️ **层纪律（ARCH-1）**：`_full_state` 是 **L3 模块内**的私有函数 ⇒ ⇒ `stream()` 的**门面侧**（L3 · 与 `invoke()` **同模块**）MUST **复用**它 ⇒ ⇒ **MUST NOT** 让 **L2 依赖 L3**（反向 import）⇒ ⇒ **L2 只负责产出事件**（每轮的稀疏状态），**归一**在 L3 侧完成。 | `specs/b7f3-invoke-full-state/spec.md` **下游承接 D-1** · 契约 **CF-01** | FR-012 · FR-015 · 裁定 3 |
| **H-2** | **B7F3 → B8F2** | **M2** | **`config` 注解放宽的归属**：L1 `CompiledGraph.stream` 的 `config` 注解仍写 `RunConfig \| None` ⇒ ⇒ 它的放宽归 **B8F2 自己**走「登记 + 回溯修订 + 发起者追认」⇒ ⇒ MUST 复用 B7F3 已定的**载体边界**（`RunConfig` = 会话面 + `max_concurrency`；普通映射 = 运行期参数 ⇒ **原样**交给 L2 ⇒ MUST NOT 在门面层翻译成 `RunConfig`）。 | `specs/b7f3-invoke-full-state/spec.md` **下游承接 D-5** · 契约 **CF-05** | FR-023 · 破冻结面 **T-3** |
| **H-3** | **B7F1 → B8F2** | **M2** | **「单轮驱动」的入口形态**：`stream()` MUST 以**单轮入口** **反复驱动**（**上游同款** · `PregelLoop.tick()` 注释「Execute a single iteration of the Pregel loop」· `langgraph/pregel/_loop.py:599` ⇒ `stream()` 的主循环 = `while loop.tick(): … yield` · `langgraph/pregel/main.py:2964`）⇒ 单轮入口 = 公开 `run_super_step` **或** L2 **私有** `_stream_tick`（为透传 B8F1 双参路由的原始 `config` + 精确判定递归上限而新增 · 见 Q8）⇒ ⇒ 本 feature MUST **NOT** 改动既有 L2 入口（`run_super_step` / `run_super_steps`）的**签名**（**B7F1 的冻结面** · 契约 §1）⇒ ⇒ ⇒ **零新增公开 L2 入口**（私有助手不进 `__all__`）⇒ ⇒ 该形态是**上游同款** ⇒ ⇒ **无需发起者另行裁决**。 | `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 · 本 spec FR-009 | FR-009 · 裁定 8 |
| **H-4** | **B7F1 → B8F2** | **M2** | **「结果对象」的 task 级载荷**：`tasks` 档 MUST 产出 **task 级**事件（**每个** task 完成时一条）⇒ 载荷 MUST 用 `freegraph.contracts.PregelTask`（**七字段**与上游**同名同义** · `langgraph/types.py:637-646`）⇒ ⇒ 本仓库契约层**已有**该类型（`src/freegraph/contracts/types.py:141`）⇒ ⇒ **零新增公开面**（就 `PregelTask` 本身而言）⇒ ⇒ `SuperStepResult` MUST 增 `tasks` 字段 ⇒ ⇒ **MUST NOT** 删既有 **4** 个字段（**拆分而不删**）⇒ ⇒ ⚠️ **这是破 B7F1 的冻结面**（契约 §1 的构造签名）⇒ ⇒ MUST 走「破冻结面的三条」。 | `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §5.3 · 本 spec FR-010 | FR-010 · FR-020 · 破冻结面 **T-1** / **T-2** |
| **H-5** | **B10F1 → B8F2** | **M2** | **`StreamWriter` 的跨线程可见性**：节点侧的 `StreamWriter` 写入 MUST 照抄上游的 **contextvar + 执行器 `copy_context()`** 传播机制（`langgraph/config.py:126` 的 `get_stream_writer()` + `langgraph/pregel/_executor.py:64` 的 `copy_context()` / `:71` 的 `ctx.run(fn, …)` / `:164` 的 async `copy_context()`）⇒ ⇒ 本仓库的落点 = 给 `src/freegraph/runtime/_concurrency.py` 的 `run_tasks_concurrently` 加 `copy_context()` ⇒ ⇒ **MUST NOT** 另立一套**并行**的显式传参机制（原则 XII「零重复载体」）⇒ ⇒ ⚠️ 该改动使 `_interrupt.py` docstring 的「线程池**不继承** `contextvars`（**实测**）」表述**对 freegraph 的执行器**不再为真 ⇒ ⇒ MUST **回溯修订**该表述与 B10F1 契约 §3（**只补注记** · **原描述不改写**）⇒ ⇒ B10F1 的两级 ContextVar 机制 MUST **NOT** 被移除（它照常工作）⇒ ⇒ **判据只收紧**。 | `specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md` §3 · `src/freegraph/runtime/_interrupt.py` 模块 docstring | FR-011 · 破冻结面 **T-4** |
| **H-6** | **B8F1 → B8F2** | **M2** | **`stream()` 的路由口径**：`stream()` 的每一档的**路由判定** MUST 与 **B8F1** 交付的**路由求值实现点** **逐字同款**（**同一份**实现 ⇒ **MUST NOT** 另写一份）⇒ ⇒ 路由判定 MUST 在 `stream()` 的**同一次**执行里可观察 ⇒ ⇒ 「稀疏视图 + 补齐」（B7F3 的 D-1）口径**继续**适用 ⇒ ⇒ **MUST NOT** 让 `stream()` 自己求值路由。 | `specs/b8f1-conditional-edges-fresh-read/spec.md` **下游承接 D-1** · 契约 `conditional-edge-contract.md` §2 | FR-009 · FR-012 · 裁定 8 |
| **H-7** | **B12F1 → B8F2** | **M2** | **并发执行器是 `StreamWriter` 的唯一传播载体**：`run_tasks_concurrently` 的**每任务** `copy_context()` MUST 与 B12F1 的「执行期零共享状态写 / 结果槽 / 每轮新建并关闭」**共存** ⇒ ⇒ MUST NOT 改变 `_TaskOutcome` 的五字段与「按节点名序返回」口径 ⇒ ⇒ MUST NOT 把 `StreamWriter` 的写入塞进 `_TaskOutcome`（那会把「可观测事件」混进「执行结果」· 原则 XII）⇒ ⇒ 写入 MUST 走**独立的运行级缓冲区**。 | `specs/b12f1-concurrency-errors/spec.md` **FR-010 / FR-013** · `contracts/concurrency-contract.md` §4 | FR-011 · FR-022 · 裁定 7 |
| **H-8** | **B2F1 → B8F2** | **M2** | **L1 协议的 `stream` 入口**：返回类别 = **事件迭代器**（`Iterator[dict[str, Any]]`）· 参数名 `input` / `config` / `stream_mode` **冻结为占位名** ⇒ ⇒ 本 feature MUST 沿用**参数名**与**返回类别** ⇒ ⇒ `stream_mode` 的**枚举全集与默认档**由本 feature 落成（B2F1 当时挂起；默认档按上游 = **`updates`**，签名默认 **`None`**）⇒ ⇒ `config` 注解的放宽与 `stream_mode` 默认值的落定按 **H-2 / T-3** 走破冻结面流程。 | `specs/b2f1-contracts-protocols/spec.md` · `contracts/public-api.md` · `src/freegraph/contracts/protocols.py:278-286` | FR-001 · FR-023 · FR-030 · 破冻结面 **T-3** |
| **H-9** | **B1F1 / D11 → B8F2** | **M2** | **`run_id` / `thread_id` 的标识职责**：`thread_id` = **会话**标识（由 `RunConfig` 承载）· `run_id` = **单次运行**标识（由运行时在每次 `stream` 开始时生成，**用户不设置**）⇒ ⇒ `stream()` 产出的**每一条**事件 MUST 携带 `run_id` 与 `thread_id`（形态在 **FR-013** 写死）⇒ ⇒ 与 **B19F1** 的 `TraceSink` span **共享同一 `run_id` / `thread_id`** ⇒ ⇒ **载体 = L2 私有 contextvar**（`_STREAM_RUN_ID` / `_STREAM_THREAD_ID` · 由 `StreamSession` 绑定 · 见 FR-027）⇒ ⇒ 两条通道**相互独立**、不互为前置。 | `harness/reports/Q8-图运行时最小契约.md` §3.4.1（C22 / C23）· `specs/b1f1-contracts-core/spec.md` Assumptions | FR-013 · FR-027 · SC-010 / SC-011 |
| **H-10** | **B7F2 / B6F1 → B8F2** | **M2** | **节点别名与流式过滤**：`stream_mode="updates"` 的载荷键 MUST 是**节点名**（与路由查表同一口径）⇒ ⇒ B8F3 落地别名后，事件里的节点名 MUST 与 `invoke` / 图结构**一致**⇒ ⇒ 本 feature MUST NOT 预埋别名解析（别名归 B8F3）。 | `specs/b7f2-compile/spec.md` 裁定 12 / 13 · `specs/b6f1-stategraph-builder/spec.md` | FR-004 · FR-016 · 下游承接 **D-1** |

---

## 下游承接条款（本 feature → 下一棒）

> 本 feature 冻结「流式事件信封 + 七种 mode 的 v1 语义 + `StreamWriter` 载体」这组跨 feature 接口
> （**D-1…D-4**）。**只接线 · 逐条最小改动**。

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 |
|---|---|---|---|---|
| **D-1** | **B8F2 → B8F3** | **M2** | **别名在流式事件中的可见性**：节点别名（C25）落地后，`stream_mode="updates"` 的载荷键 MUST 与 `invoke` / 图结构使用**同一套节点名口径**（沿用 B8F1 的 `path_map` 查表口径：**用节点名，不解析别名**）⇒ ⇒ B8F3 MUST NOT 为 `stream()` 另造一套命名映射。 | FR-004 · FR-016 · H-10 |
| **D-2** | **B8F2 → B14F1** | **M3** | **`checkpoints` 档的真实数据源**：本 feature 的 `checkpoints` 档在 v1 **恒为空序列**（无伪造事件）⇒ ⇒ B14F1 交付 `MemorySaver` / checkpointer 后 MUST 提供「每创建一个 checkpoint 一条事件」的数据源，并复用 `_loop.py:631-636` / `debug.py:144`（`map_debug_checkpoint`）的「checkpoint 事件 vs `get_state()` 同形」口径。 | FR-017 · 裁定 5 |
| **D-3** | **B8F2 → B18F1 / B19F1** | **M3** | **两条事件通道独立、按 id 合并**：`stream()` 的事件与 `TraceSink` 的 span **不互为前置**；二者 MUST 共享同一 `run_id` / `thread_id`（D11 已冻结）⇒ ⇒ **载体 = L2 私有 contextvar**（`_STREAM_RUN_ID` / `_STREAM_THREAD_ID` · 由 `StreamSession` 绑定；B18F1 / B19F1 MUST 读取同一对 contextvar）⇒ ⇒ B18F1 / B19F1 MUST NOT 反向要求 `stream()` 先落地，亦 MUST NOT 把 trace 数据塞进 `stream()` 的信封。 | FR-013 · FR-027 · H-9 · SC-010 |
| **D-4** | **B8F2 → B22F1 / B23F1** | **M2** | **图导出与流式互不影响**：`get_graph` / `draw_mermaid_png` MUST NOT 依赖 `stream()` 的副作用；`stream()` MUST NOT 调用图导出 ⇒ ⇒ 两者只在「同一张编译产物」上共享只读规格。 | FR-006 · SC-013 · Out of Scope |

> ⚠️ **ARCH-3 例外登记（2026-11-20 · 发起者授权）**：D-3 / H-9 的
> `_STREAM_RUN_ID` / `_STREAM_THREAD_ID` 是 **L2 私有运行期 contextvar**，由 B18F1 /
> B19F1（L5）读取。这是对 `立项书 §5.1` **ARCH-3**「跨层只经由 `Protocol` + 纯数据类」的
> **已登记例外**：其载荷是 `str | None` **运行期元数据**，不是新的公开契约载体；本 feature
> **MUST NOT** 因此新增公开符号（`runtime.__all__` 仍 23）。该例外**不改变** ARCH-1 的
> 导入方向约束（L5 → L2 合法），也**不放宽**任何跨层 Protocol 判据；若未来把该标识升级为
> 公开 API，MUST 另走契约修订（`Protocol` + 纯数据类 + 兼容矩阵）。

---

## Clarifications

### Session 2026-11-19（设计裁定 · spec 阶段写死，plan 不得再翻）

> **背景**：提示词初稿已写死「七种 mode 名 · `StreamWriter` 走 contextvar + `copy_context()` ·
> `tasks` 载荷用 `PregelTask` · `values` 复用 `_full_state`」，但若干点仍会外溢到实现口径或
> 下游 feature 的接口决策。
>
> ⚠️ **本轮未向用户提问** —— 纪律：宪法原则 XI「上游有答案 ⇒ 照抄 ⇒ 不问用户」；
> 上游 `langgraph 1.2.11` 对本 feature 的**全部**语义点**均已给出答案**（含实测），
> 故 **零** 澄清标记（`NEEDS CLARIFICATION` 槽位）。

#### Q1（事件信封的形态）

→ **A：固定四键信封** —— 每一条事件都是普通 `dict`，**恰含**：

```text
{
  "stream_mode": <str>,        # 七种 mode 之一
  "payload":     <Any>,        # 该 mode 的上游同款载荷
  "run_id":      <str>,        # 本次 stream() 调用生成的单次运行标识
  "thread_id":   <str | None>, # 会话标识（来自 config；未提供则 None）
}
```

- **理由**：D11 已冻结「每条事件 MUST 携带 `run_id` / `thread_id`」，且 L1 协议的返回类别是
  `Iterator[dict[str, Any]]` ⇒ 信封是唯一同时满足两者的载体。
- 上游 v1 的「单 mode 直接 yield 载荷 / 多 mode yield `(mode, payload)`」是**无 id** 的形态
  （`langgraph/pregel/main.py:4236-4243`；实测 **E-11**）⇒ freegraph 采用**上游 v2 风格**的
  信封（上游 v2 的形态是 `{"type", "ns", "data", "interrupts"}` · `main.py:4228`）⇒ 登记为
  **偏离 X-1（DIFF）**，理由 = D11 的硬约束（必须自研区 ③：freegraph 自创的诊断关联能力）。
- **MUST NOT** 在 `payload` 上再挂 `run_id` / `thread_id`（避免污染状态 / 自定义数据）。

落点：FR-013 · 裁定 1 · SC-010。

#### Q2（`stream_mode` 的单值与序列）

→ **A：三者都接受** —— `str` ⇒ 该 mode；`Sequence[str]` ⇒ 逐 mode 产出，**每条事件**的
`stream_mode` 标明来源；`None` ⇒ 默认档 **`"updates"`**（上游同款 · `StateGraph.compile()`
默认 `updates`）；**重复 mode MUST 去重保序**；空序列 ⇒ 显式失败。

- 上游多 mode 的形态是 `(mode, payload)` 元组（`main.py:4236-4239`；实测 **E-11**）⇒
  freegraph 用**同一信封**表达（`stream_mode` 字段）⇒ 登记为 **偏离 X-1**。
- 校验 MUST 在 `stream()` **调用时**完成（返回迭代器之前）⇒ 非法 mode / 空序列 ⇒
  内置 **`ValueError`**（点名非法值并列出七种合法值）；非 `str` / 非 `Sequence` / 非
  `None` ⇒ 内置 **`TypeError`**。
- 上游对非法 mode **静默产出空流**（实测 **E-10**）⇒ freegraph 取**显式失败** ⇒
  登记为 **偏离 X-2（STRICTER）**。
- 上游 `CompiledStateGraph` 的默认档是 **`updates`**（`langgraph/graph/state.py:1357`），
  且 `Pregel.stream` 接受 `None`（`main.py:2737-2743`；实测 **E-18**）⇒ freegraph
  **照抄**：签名默认 `None`，`None` 解析为 `"updates"`。

落点：FR-002 · FR-014 · 裁定 2 · SC-001 / SC-012。

#### Q3（`values` 档的产出节奏与归一）

→ **A：初始状态 + 每个完成的 super-step 一条**；`payload` = **完整状态**（普通 `dict`，
键集 == schema 全集、顺序 == schema 声明顺序、路由通道**不进**键集、无值键以 `None` 补齐）。

- 上游在**执行前**先产出一条输入状态，然后每个 step 一条（实测 **E-1 / E-12**）。
- 归一 MUST 复用 B7F3 的 `_full_state`（`src/freegraph/_stategraph.py:235`）⇒ ⇒
  **MUST NOT** 在 L2 复制补齐逻辑（ARCH-1 · H-1）。
- 对**同图、同输入、无静态断点、无会话历史**的运行，`stream()` 的**最后一个** `values`
  事件的 `payload` MUST 与 `invoke()` 的最终状态**逐字相等**（有中断时含
  `"__interrupt__"` 元组）。

落点：FR-003 · FR-012 · FR-015 · 裁定 3 · SC-002。

#### Q4（`updates` 档的粒度与载荷）

→ **A：每个完成的 task 一条**；`payload = {节点名: {通道 key: 值 | 值的元组}}`。

- **单次写入** ⇒ 该通道的值（标量）· **同一 task 对同一通道多次写入** ⇒ **按写入顺序的元组**
  ⇒ 合并时 MUST 按**通道归约语义**逐条应用（**MUST NOT** 简单 `dict.update`）。
- 上游同样按 task / step 产出，并在「同通道多次写入」时包成 `{"$writes": [...]}`
  （`langgraph/pregel/_io.py:142-163`；实测 **E-2**）⇒ freegraph 用**元组**表达同一语义
  ⇒ 登记为 **偏离 X-1 的载荷形态子项**（DIFF · 仅形态，归约语义不变）。
- 载荷键 MUST 是**节点名**（H-10）。

落点：FR-004 · FR-016 · 裁定 4 · SC-003。

#### Q5（`checkpoints` / `messages` 的 v1 边界）

→ **A：两档都**接受**且**恒为空序列**（零事件、零异常）。

- `checkpoints`：真实数据源属 **B14F1**（`MemorySaver` / checkpointer）⇒ 本 feature
  **MUST NOT** 伪造 checkpoint 事件、MUST NOT 把 `SuperStepResult.state` 伪装成 checkpoint
  ⇒ 下游承接 **D-2**。
- `messages`：上游的语义是「LLM token 流 + metadata」（`langgraph/types.py:132`），属
  **LangChain 特有**、归 freechain；freegraph v1 **没有 LLM 回调源** ⇒ 恒为空序列；
  未来有源时 MUST **原样透传**（不抽取、不改写、不假设 LangChain 消息类型）。
- 两档的「空序列」是**显式声明的语义边界**，不是「实现未完成」；验收断言 MUST 判
  「序列长度 == 0 且不抛异常」，**MUST NOT** 判「未实现」。
- 上游在有 checkpointer 时 `checkpoints` 会产出 3 条（实测 **E-5**）⇒ 该差异属
  **能力尚未交付**（B14F1）⇒ 走 Out of Scope / 下游承接，**MUST NOT** 记为偏离。

落点：FR-017 · FR-018 · 裁定 5 · SC-008 / SC-009。

#### Q6（`tasks` 档的载荷与 `SuperStepResult.tasks`）

→ **A：每个完成的 task 一条**；`payload` = `freegraph.contracts.PregelTask` **实例**
（七字段：`id` / `name` / `path` / `error` / `interrupts` / `state` / `result`）。

- 字段语义（逐字对齐上游 `langgraph/types.py:637-646`）：
  - `id` —— 本次运行内**唯一**的任务标识（`str`；具体生成方式**不冻结**；可与上游一样
    随机，**MUST NOT** 跨运行比较，也 MUST NOT 作为差分断言的一部分）；
  - `name` —— 执行的节点名（fan-out 任务 = 目标节点名）；
  - `path` —— 任务路径（标准任务 = `(节点名,)`；fan-out 任务 = `(目标名, TaskId)`，其中
    `TaskId` 是 L2 本轮的整数任务标识）；
  - `error` —— 该 task 捕获的真实异常对象（**原对象、不包装**）· 成功 / 挂起时为 `None`；
  - `interrupts` —— 该 task 的中断载荷元组（元素 = `Interrupt`）· 无中断时为空元组；
  - `state` —— v1 **恒为 `None`**（无子图 / 无 per-task StateSnapshot 生产 · B15F1 才有）；
  - `result` —— 该 task **本次**的更新载荷（与 `updates` 同形：`{通道 key: 值 | 元组}`；
    无写入时为空 `dict`）。
- `SuperStepResult` MUST **新增** `tasks: tuple[PregelTask, ...]` ⇒ **追加在末尾**、
  带缺省值 `()` ⇒ 既有 4 个字段**一个都不删**（拆分而不删）；单轮入口 = 本轮 ·
  多轮入口 = **累计**（按轮次先后拼接，与 `executed` / `node_writes` **同款累计口径**）。
- ⚠️ **上游的实际形态**：`tasks` 在**任务开始**与**任务完成**各产出一条，载荷是**普通 dict**
  （`TaskPayload` / `TaskResultPayload` · `_loop.py:580` / `:674` / `:1461-1466` ·
  `debug.py:41-70` / `:106-125`；实测 **E-3**）⇒ 本 spec 按**提示词 FR-010 的冻结口径**
  （每 task 完成一条 · 载荷 = `PregelTask`）⇒ 登记为 **偏离 X-3（DIFF）**，理由 =
  提示词已冻结 + 复用 L1 既有 `PregelTask`（零新增公开面）。
- `SuperStepResult` 扩字段 = 破 **B7F1** 的冻结面 ⇒ 走 **T-1**；同时破 **B12F1** 的
  「四字段零改动」裁定 ⇒ 走 **T-2**（**T-2 是本 spec 新发现的受影响面**）。

落点：FR-010 · FR-020 · 裁定 6 · SC-006 · 破冻结面 **T-1 / T-2**。

#### Q7（`StreamWriter` 的载体与作用域）

→ **A：contextvar 取写入器 + 执行器 `copy_context()` 传播**；无流时是 **no-op**。

- 公开入口：`freegraph.graph.get_stream_writer() -> StreamWriter`（门面转出）+
  `freegraph.contracts.StreamWriter`（类型别名 `Callable[[Any], None]`）⇒ 与上游的
  `get_stream_writer()` / `StreamWriter` **同名同义**（`langgraph/config.py:126` ·
  `langgraph/types.py:138`）⇒ **2026-11-19 clarify 轮拍板（选项 A）**：不新建
  `freegraph.config` 模块，也不做双入口别名。
- 运行级 contextvar 只在 `stream()` 期间设置；**`invoke()` 期间**或**完全无流**时 ⇒
  `get_stream_writer()` MUST 返回 **no-op 可调用对象**（上游同款 · `config.py:13-14`；
  实测 **E-9**）⇒ MUST NOT 抛异常。
- 跨线程可见性 MUST 由 `run_tasks_concurrently` 的**每任务** `copy_context()` 提供
  （`_executor.py:64` 的 `copy_context()` / `:71` 的 `ctx.run`；实测 **E-7**）⇒ MUST NOT 另加「显式把 writer 传给节点」的
  第二套载体（原则 XII）。
- **关键字注入也必须交付（上游同款）**：节点签名声明参数名为 **`writer`** 时
  （`POSITIONAL_OR_KEYWORD` 或 `KEYWORD_ONLY`；注解 ∈ {`StreamWriter` · 字符串
  `"StreamWriter"` · 空}）⇒ 节点调用 MUST 以**关键字**注入当前 `get_stream_writer()`
  （无流时为 no-op）；`**kwargs` / 其它参数名 / 注解不匹配 ⇒ **不注入**（按一参调用）。
  ⚠️ 上游的参数名是 **`writer`**；`stream_writer` 是 **runtime key**，不是参数名
  （`langgraph/_internal/_runnable.py:183-188` · 实测 **E-17**）。⇒ 本 feature 交付后
  **B8F1 DR-4 关闭**。
- 写入 MUST 线程安全，并按「任务标识序 + 任务内写入序」**确定排序**后产出（H-7）。
  ⚠️ **产出时机**：本轮 `custom` 写入在 L2 单轮入口（`_stream_tick`）**结束后批量产出**（不是逐写即时产出）⇒
  该时机差异登记为 **P-23 / X-6**；与 **P-11** 的「载体 SAME」分开标注。

落点：FR-005 · FR-011 · FR-021 · FR-022 · FR-036 · 裁定 7 · SC-004 / SC-021。

#### Q8（主循环、惰性与提前停止）

→ **A：L3 门面持有主循环；每轮调用 L2 单轮入口（公开 `run_super_step` 或 L2 私有 `_stream_tick`）；返回惰性迭代器。**

- 主循环 = **反复驱动** L2 单轮入口（**零新增公开 L2 入口** · H-3）：
  `while True: result = _stream_tick(...); if result is None: break; yield …`
  ⇒ 与上游 `while loop.tick(): … yield`（`main.py:2964`）**同构**。
- ⚠️ **私有单轮助手 `_stream_tick`（本 spec 新增的冻结口径）**：为同时满足
  ① **双参路由的原始 `config` 透传**（B8F1 的 `f(state, config)`；`run_super_step`
  目前内部把 `route_config` 写死为 `None`）与 ② **精确的递归上限判定**
  （「超限**且仍有任务** ⇒ `GraphRecursionError`」需要先看触发集），
  允许在 L2 新增**私有** `_stream_tick`（前导下划线 · **不进**
  `freegraph.runtime.__all__` · 不改两个既有入口签名）⇒ ⇒ 它 MUST 与
  `run_super_step` **共享同一** `_run_single_step` / `_run_round` / `_evaluate_*` /
  `_determine_triggers` 实现（**MUST NOT** 另写路由 / 触发 / 执行）⇒ ⇒
  `_stream_tick` 返回 `SuperStepResult | None`（`None` = 已收敛）⇒
  超限且仍有任务 ⇒ 抛 `GraphRecursionError`；`route_config` MUST 是用户交给
  `stream()` 的**原始** `config`（`RunConfig` / 普通映射 / `None` · **逐字**）。
- **输入写入 / `bind_run` / contextvar 绑定** MUST 复用 L2 既有的 **初始化语义**
  （`run_graph` 的 `_first_graph` 中已落地的同一套步骤；允许把这些步骤抽成
  **私有初始化助手**）⇒ **MUST NOT** 在 L3 直接 `channel.update(...)`，
  亦 **MUST NOT** 另写一套通道写入。⚠️ **`checkpointer` 与 `_resume_graph` 的恢复路径
  在本 feature 不参与**（FR-028）：`StreamSession` MUST **忽略** `checkpointer`
  （不读快照、不写快照、不触发恢复）⇒ MUST NOT 因 `checkpointer` 改变七档语义。
  **主循环本身 MUST 只调用 L2 单轮入口**
  （**MUST NOT** 复用 `_run_graph_loop` 的整图循环 · **MUST NOT** 自己求值路由 / 触发）。
  ⇒ 允许在 L2 **内部新增私有生成器 / 私有助手**（前导下划线 · **不进**
  `freegraph.runtime.__all__` · 不改两个既有入口签名）；「零新增 L2 入口」的解释 =
  **零新增公开入口**（裁定 8）。
- **惰性**：调用 `stream()` 不执行图；**首次迭代**才开始（上游同款）。
- **提前停止**：消费者停止迭代 / `close()` 时，当前轮已结束（L2 单轮入口每轮自建并关闭
  线程池）⇒ **零悬挂线程**、零脏 contextvar（`finally` 复原 token）⇒ 后续轮**不再执行**。
  ⇒ ⚠️ 提示词 §2 的「消费者不迭代时图仍应能正常跑完」**不是**上游行为（惰性生成器不启动则
  零执行）⇒ 本 spec **按上游与 FR-006 的口径**收敛为「**提前停止不泄漏、不吞异常**」，
  **MUST NOT** 为了实现「不迭代也跑完」而引入后台线程 / 预计算（那会破坏惰性且引入泄漏面）。
  ⇒ 登记**引文差异 ③**。
- **异常**：非中断异常 MUST **原类型 + 原消息**从迭代器**重抛**（不包装、不吞）；
  中断（`GraphInterrupt`）是**受控暂停** ⇒ 产出收尾事件后**正常结束迭代**（见 Q10）。

落点：FR-001 · FR-006 · FR-009 · FR-024 · FR-025 · FR-026 · FR-037 · 裁定 8 ·
SC-013 / SC-016 / SC-022 / SC-023。

#### Q9（`run_id` / `thread_id` 的生成与 `RunConfig.run_id`）

→ **A：每次 `stream()` 调用生成一个 `run_id`（`uuid4().hex`），全事件共享；
`thread_id` 取会话配置；`RunConfig.run_id` **不参与**事件标识。**

- `run_id` —— 由门面在 `stream()` 启动时生成，**用户不可指定 / 不可覆盖**；同一
  `stream()` 的**全部**事件共享**同一个** `run_id` ⇒ D11 不变式 2。
- `thread_id` —— `RunConfig` 或普通映射的**同一解析口径**：`configurable["thread_id"]` 优先于
  顶层 `thread_id`（`RunConfig.resolved_thread_id()` · `src/freegraph/contracts/types.py:234-245`）；
  未提供 ⇒ `None`。
- ⚠️ **现状冲突**：`RunConfig` 现含 `run_id: str | None`（上游对齐 P3 · `types.py:219`），
  而 D11 写「`run_id` **不进** `RunConfig`」⇒ ⇒ 本 feature **不改** `RunConfig` 的字段清单，
  但 **MUST NOT** 把用户填的 `RunConfig.run_id` 当作事件 `run_id` ⇒ 事件的 `run_id`
  **恒为运行时生成值**；该字段在 `stream()` 路径上**不生效**（登记**引文差异 ①**）。
  上游 `RunnableConfig` 的 `run_id` 可直接指定（`_config.py` 一族）⇒ freegraph 此处
  **更严**（D11 追认）⇒ 登记 **偏离 X-5（STRICTER）**。
  ⇒ **2026-11-19 clarify 轮拍板（选项 A）**：采用「**忽略**」而非「显式拒绝」
  ⇒ 上游风格配置可**原样传入**（不新增成功路径上的失败点）。
- 与 `TraceSink` 的 span 共享**同一** `run_id` / `thread_id` ⇒ 可按 id 合并时间线（H-9）。

落点：FR-013 · FR-027 · 裁定 9 · SC-010 / SC-011 · 偏离 **X-5**。

#### Q10（中断与失败时的事件）

→ **A：中断 ⇒ 收尾事件后正常结束；失败 ⇒ 已发生的 custom 先产出，再原异常重抛。**

- **中断**（`GraphInterrupt`）：**执行顺序以 FR-014 为准** =
  `custom → updates → tasks → debug → values`。
  - `custom` 档 MUST 先产出本轮已记录的写入（它们确实发生过）；
  - `updates` 档 MUST 产出一条收尾事件：`payload = {"__interrupt__": <元组>}`；
  - `tasks` 档 MUST 为**被中断的 task** 补发一条 `PregelTask`（`error=None` ·
    `interrupts` 非空 · `result` = 该 task 的已发生写入）
    ⇒ `debug` 档 MUST 为其补发一条对应包裹事件（`type="task_result"`）
    ⇒ 上游同款（实测 **E-8 / E-14**：`tasks` 在中断时仍产出 task 完成事件）；
  - `values` 档 MUST 产出一条收尾事件：`payload` = 完整状态 + `"__interrupt__"`（元组）；
  - ⚠️ 为实现这一点，L2 的**私有流式生成器** MUST 捕获本轮 task 定格（即使
    L2 单轮入口抛 `GraphInterrupt`）⇒ **MUST NOT** 为此给 `SuperStepResult` 或
    `InterruptResult` 改字段；
  - 迭代器**正常结束**（不把 `GraphInterrupt` 抛给 `stream()` 的消费者）⇒ 上游同款
    （实测 **E-8**）。
- **失败**（节点的真实异常 / `InvalidUpdateError` / `GraphRecursionError` 等）：
  - 迭代器 MUST **重抛原异常对象**（`type` / `message` / `identity` 不变）；
  - 失败轮**已发生的 custom 写入** MUST **先产出**（它们确实发生过；上游实测同样先产出再抛），
    然后重抛原异常；失败轮的 `values` / `updates` / `tasks` / `debug` **不产出**；
  - 之前**已成功**的轮次事件**已经交付**，不回撤。
- `stream()` MUST NOT 把中断或失败转成「空流」或「吞掉」。

落点：FR-025 · FR-026 · 裁定 10 · SC-013 / SC-017 · 偏离 **X-4**（仅 `debug` 载荷形态）。

#### 裁定编号映射（本 spec 的唯一裁定编号表）

| # | 裁定 | 落点 |
|---|---|---|
| **裁定 1** | 事件信封 = 固定四键 `{stream_mode, payload, run_id, thread_id}` | Q1 · FR-013 |
| **裁定 2** | `stream_mode` 接受单值与序列；非法 / 空序列 ⇒ `ValueError`；重复去重保序 | Q2 · FR-002 / FR-014 |
| **裁定 3** | `values` = 初始状态 + 每完成步一条；归一复用 `_full_state`（L3） | Q3 · FR-003 / FR-012 / FR-015 |
| **裁定 4** | `updates` = 每完成 task 一条；同通道多次写入 ⇒ 元组；合并按通道归约 | Q4 · FR-004 / FR-016 |
| **裁定 5** | `checkpoints` / `messages` v1 恒为空序列；语义边界写死 | Q5 · FR-017 / FR-018 |
| **裁定 6** | `tasks` = 每完成 task 一条 + `PregelTask`；`SuperStepResult` 追加 `tasks` | Q6 · FR-010 / FR-020 |
| **裁定 7** | `StreamWriter` = contextvar getter + 每任务 `copy_context()` + 参数名 `writer` 的关键字注入；无流 no-op | Q7 · FR-005 / FR-011 / FR-021 / FR-036 |
| **裁定 8** | L3 主循环反复驱动 L2 单轮入口（公开 `run_super_step` 或私有 `_stream_tick`）；`_stream_tick` 与 `run_super_step` 共享同一执行/路由/触发实现；惰性；提前停止零泄漏；零新增公开 L2 入口 | Q8 · FR-001 / FR-006 / FR-009 |
| **裁定 9** | 每次 `stream()` 生成 `run_id`；`thread_id` 按 `resolved_thread_id()`；`RunConfig.run_id` 不生效 | Q9 · FR-013 / FR-027 |
| **裁定 10** | 中断 ⇒ 收尾事件后正常结束；失败 ⇒ 先产出已发生的 custom，再原异常重抛 | Q10 · FR-025 / FR-026 |

### Session 2026-11-19 · clarify 轮（用户拍板）

- Q: 事件信封的字段形态应该采用哪一种？ → A: **四键** `{stream_mode, payload, run_id, thread_id}`（选项 A）。理由：七档统一、无 `ns` / `interrupts` 死字段、`values` 的 `payload` 可与 `invoke` 终态逐字比较；后期本仓要写自己的官方文档，四键信封可自洽描述，不依赖上游 v2 文档。
- Q: 当用户通过 `RunConfig.run_id` 指定了运行标识时，`stream()` 应该怎么处理？ → A: **选项 A（忽略该字段）**：事件始终用运行时生成的 `run_id`；文档写明该字段在 `stream()` 路径不生效。理由：对上游配置的兼容性伤害最小，同时满足 D11 的「运行时生成、用户不可覆盖」；不采用「显式拒绝」，因为那是在成功路径上新增失败点，不是单纯更严的失败信号。
- Q: `StreamWriter` 类型与 `get_stream_writer()` 应该放在哪个公开入口？ → A: **选项 A**：`freegraph.graph.get_stream_writer`（门面）+ `freegraph.contracts.StreamWriter`（类型）。理由：本仓的公开入口是单一门面，类型属于 L1；不新增公开模块，便于后期写自洽的官方文档。

### 引文差异（提示词初稿 vs 本 spec）

| # | 提示词写法 | 事实 / 订正 | 处置 |
|---|---|---|---|
| **①** | §7 / D11：「`run_id` … **不进 `RunConfig`**」 | `RunConfig` 现为 **9 字段**且**已含** `run_id: str \| None`（上游对齐 P3 · `src/freegraph/contracts/types.py:219`）⇒ D11 的「不进」是 **2026-11-05** 的历史口径 | **不改** `RunConfig` 字段清单；本 feature 只保证**事件**的 `run_id` 由运行时生成、`RunConfig.run_id` 不生效（Q9 · **X-5**）⇒ **宪法已订正为 v1.15.2**（字段为上游兼容保留；事件/ span 的 `run_id` 仍运行时生成）；立项书 §5.3.1 保留为历史事实 |
| **②** | §2 / FR-010：「上游的 `tasks` 档 … 载荷 = `PregelTask` 七字段」 | 上游 `tasks` 在**任务开始**与**完成**各发一条，载荷是普通 `dict`（`TaskPayload` / `TaskResultPayload`），**不是** `PregelTask`（`_loop.py:580` / `:674` / `:1461-1466` · 实测 **E-3**） | 本 spec **按提示词 FR-010 的冻结口径**（每完成一条 + `PregelTask`）⇒ 如实登记 **X-3（DIFF）**（原则 XI ②：上游自身的不确定 / 形态差异） |
| **③** | §2：「消费者不取（不迭代）时，图仍应能正常跑完」 | **惰性生成器**不启动 ⇒ **零执行**；上游 `stream()` 同样是惰性（同步、同线程驱动） | 收敛为「**提前停止不泄漏 / 不吞异常**」（FR-006 / Q8）⇒ **MUST NOT** 引入后台线程或预计算 ⇒ 本 feature 的 SC-013 按此判定 |
| **④** | §4 FR-010：「扩 `SuperStepResult` = 破 **B7F1** 的冻结面」 | 除 B7F1 外，**B12F1** 的裁定 25 ② / FR-013 明确写「`SuperStepResult` 的**四字段冻结面 MUST 零改动**」（`specs/b12f1-concurrency-errors/spec.md:792`） | **新发现的受影响面** ⇒ 一并登记 **T-2**（只补注记 · 原描述不改写） |
| **⑤** | §10：「规模 1,180 行 · 3 人日」 | FR-009…FR-012 带来额外工作量（线程池 `copy_context()` + `SuperStepResult` 扩字段 + **三处**上游契约回溯修订（B7F1 / B10F1 / B7F2）+ 一键验收脚本） | 本 feature 以**实现期实测**为准；**行数 / 工时修订属发起者职权**（与 B8F1 的 R-5 同款 · 原则 VIII）⇒ 本 spec **不单方面修改** |
| **⑥** | 立项书 §5.2 B8F2 行：「`stream()`：**5 种模式** + `StreamWriter`」 | C12 与提示词均要求 **7 种** mode（`values` / `updates` / `checkpoints` / `tasks` / `debug` / `messages` / `custom`） | 以 **C12 / 7 种**为准；本 spec **不单方面改立项书**（上位文档修订属发起者职权） |
| **⑦** | 提示词 / B8F1 DR-4 措辞：「`stream_writer` 关键字注入」 | 上游的**参数名是 `writer`**（`langgraph/_internal/_runnable.py:183-188`）；`stream_writer` 是 **runtime key**，不是参数名；实测 **E-17** | FR-036 照抄上游：注入参数名 **`writer`**；`stream_writer` 只作为 runtime key 的说明 |
| **⑧** | §1 / §3 / US3：「**实时观察**每一步」 | 上游 `custom` 是逐写即时；freegraph 为并发确定性取**轮末批量**（`P-23` / `X-6`） | US3 收敛为「**按轮观察**」；登记 **X-6（必须自研区 ②）**；MUST NOT 假称逐写实时 |
| **⑨** | 提示词 §「下游承接（B7F1 + B10F1）」D-1：「**零新增 L2 入口**」 | 本 spec 解释为「**零新增公开 L2 入口**」；允许新增 L2 **私有** `_stream_tick`（不改 `run_super_step` / `run_super_steps` 签名 · 不进 `__all__`） | 为使 B8F1 双参路由的**原始 `config`** 与**精确递归上限**可达；私有助手复用同一执行/路由/触发实现 ⇒ **判据只收紧** |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 观察每一步的状态演进 (Priority: P1)

作为用户，我在开发期想看到图跑到每一步时的完整状态，以便定位问题出在哪一步。

**Why this priority**: 这是 `values` 档的全部价值，也是「可诊断性是一等功能」的最直接体现。

**Independent Test**: 用一张两节点线性图，`list(app.stream({"x": 0}, stream_mode="values"))`
应得到「初始状态 + 每步完整状态」的序列，且最后一条的 `payload` 与 `invoke` 的最终状态相等。

**Acceptance Scenarios**:

1. **Given** 一张 `a → b` 的线性图与输入 `{"x": 0}`，**When** 以 `stream_mode="values"` 消费，
   **Then** 事件数为 `1 + 2`（初始 + 两步），且每条 `payload` 的键集 == schema 全集。
2. **Given** 同一次运行，**When** 对比最后一个 `values` 事件的 `payload` 与 `invoke` 的结果，
   **Then** 两者**逐字相等**。
3. **Given** 无值通道 `llm_calls`，**When** 消费 `values`，**Then** 最后一个 `payload` 含
   `"llm_calls": None`（补齐），而归约型通道的类型空值 `[]` / `0` **不被改写**。

---

### User Story 2 - 只看每步的增量 (Priority: P1)

作为用户，我只想看每步**改了什么**（而非全量状态），以便快速定位变化点。

**Why this priority**: `updates` 是日志 / 过滤 / 轻量消费的主路径；增量可合并回终态是核心判据。

**Independent Test**: 用同一张两节点图，`list(app.stream(..., stream_mode="updates"))`
应得到两条事件（每个 task 一条），把载荷按通道归约语义合并后 == `invoke` 的最终状态。

**Acceptance Scenarios**:

1. **Given** 线性图，**When** 消费 `updates`，**Then** 每条 `payload` 的键是**节点名**，
   值是「通道 → 值」的映射。
2. **Given** 同一 task 对同一归约通道写两次，**When** 消费 `updates`，**Then** 该通道的值是
   **按写入顺序的元组**，合并时逐条归约。
3. **Given** 所有 `updates` 事件，**When** 按通道归约语义合并，**Then** 结果 == `invoke` 终态。

---

### User Story 3 - 节点主动写自定义数据 (Priority: P1)

作为用户，我的节点想主动往流里写一条进度信息（如「正在检索…」）。

**Why this priority**: `custom` 是 `StreamWriter` 的唯一用途；它也是「按轮观察」的用户自定义通道
（每轮 L2 单轮入口结束后批量产出 · 见 P-23 / X-6）。

**Independent Test**: 图中的一个节点调用 `get_stream_writer()({"msg": "retrieving"})`；
`list(app.stream(..., stream_mode="custom"))` 应包含该对象（**原样**）。

**Acceptance Scenarios**:

1. **Given** 节点内 `writer({"msg": "retrieving"})`，**When** 消费 `custom`，
   **Then** 事件的 `payload` 逐字等于 `{"msg": "retrieving"}`。
2. **Given** 节点在**多个线程**（同轮并发）各写一条，**When** 消费 `custom`，
   **Then** 所有写入都出现，且顺序按「任务标识序 + 任务内写入序」确定。
3. **Given** 不在 `stream()` 中（如 `invoke()`），**When** 调用 `get_stream_writer()`，
   **Then** 返回 no-op，不抛异常、不产生任何事件。

---

### User Story 4 - 七种 mode 都被接受 (Priority: P2)

作为用户，我按 LangGraph 的 mode 名调用，不希望遇到自造名字或静默空流。

**Why this priority**: mode 名是 C12 的兼容面；拼错时静默空流会让用户误以为图没跑。

**Independent Test**: 对七种 mode 逐一调用 `list(app.stream(...))`；非法 mode 调用
`app.stream(..., stream_mode="bogus")` 应立刻抛 `ValueError`（点名非法值并列出合法值）。

**Acceptance Scenarios**:

1. **Given** 七种合法 mode，**When** 逐一消费，**Then** 均不抛异常（`checkpoints`/`messages`
   允许零事件）。
2. **Given** `stream_mode="bogus"`，**When** 调用 `stream()`，**Then** **调用时**即抛
   `ValueError`（不是首次迭代时）。
3. **Given** `stream_mode=["values", "updates"]`，**When** 消费，**Then** 每条事件的
   `stream_mode` 标明来源，且两类事件都出现。

---

### User Story 5 - task 级观察与调试 (Priority: P2)

作为用户，我想看到每个 task 的完成情况（成功 / 错误 / 中断），以及调试用的包裹事件。

**Why this priority**: `tasks` / `debug` 是定位「哪个 task 失败 / 挂起」的直接手段。

**Independent Test**: 用同一张线性图，`tasks` 档应得到「每个完成的 task 一条
`PregelTask`」；`debug` 档应得到同数量的包裹事件（`type="task_result"`，`payload` 是同一
`PregelTask`）。

**Acceptance Scenarios**:

1. **Given** 两节点图，**When** 消费 `tasks`，**Then** 事件数为 2，每个 `payload` 是
   `PregelTask` 实例且 `name` / `result` / `error` / `interrupts` 可读。
2. **Given** 同一图，**When** 消费 `debug`，**Then** 每条 `payload` 是
   `{"step", "timestamp", "type", "payload"}`，`type == "task_result"`，
   `payload` 是 `PregelTask`；`step` 为 1 起的轮次序号（同轮相同），`timestamp`
   可被 `datetime.fromisoformat` 解析且带 UTC 时区。
3. **Given** 节点抛真实异常，**When** 消费 `stream()`，**Then** 原异常被重抛（不包装），
   失败轮**不**产出 task 事件。

---

### User Story 6 - 流式消费不改变执行语义 (Priority: P3)

作为用户，我担心「开了流」会改变图的执行结果或留下资源。

**Why this priority**: 宪法原则 IV「可视化不阻断执行」的底线。

**Independent Test**: 对同一张图分别 `invoke()` 与「消费到一半就 `close()` 的 `stream()`」；
前者结果稳定、后者无悬挂线程 / 无 contextvar 脏状态；再跑一次 `invoke()` 结果与第一次相同。

**Acceptance Scenarios**:

1. **Given** 同一张编译图，**When** 先 `invoke()` 再 `stream()`（完整消费），**Then**
   两者的最终状态相等。
2. **Given** 消费者只取一条事件就 `close()`，**When** 等待线程退场，**Then** 无
   `freegraph-node` 线程残留，且后续运行不受影响。
3. **Given** 节点抛异常，**When** 消费 `stream()`，**Then** 异常原样出现（不被吞成 StopIteration）。

---

### Edge Cases

- `stream_mode` 是 `int` / 不可迭代对象 ⇒ **`TypeError`**（点名类型）；`None` ⇒ 默认档
  `"updates"`（合法，不抛）。
- `stream_mode=[]`（空序列）⇒ `ValueError`（未请求任何 mode）。
- `stream_mode=["values", "values"]` ⇒ 去重保序（每个 mode 只产出一族事件）。
- 图只有入口 → `END` 的直连（零节点执行）⇒ `values` 只产出初始状态一条；其余 mode 零事件。
- 节点返回 `None`（无写入）⇒ `updates` 该 task 的载荷为空 `dict`；`tasks.result` 为空 `dict`。
- 同轮多节点并发写 `custom` ⇒ 顺序按任务标识序 + 任务内写入序；不因完成时刻抖动。
- 节点挂起（`interrupt()`）⇒ `tasks` / `debug` 为被中断 task 补发一条（`interrupts` 非空；
  中断轮的 `debug.step` 是该轮自己的序号，**不沿用上一轮**）；`values` / `updates` 产出
  `"__interrupt__"` 收尾事件后正常结束。
- 节点抛异常 ⇒ 已发生的 custom 写入先产出，然后原异常重抛；失败轮的 `values` / `updates` /
  `tasks` / `debug` 不产出；之前成功的轮次事件已交付。
- 消费者不迭代 ⇒ **零执行**（惰性）；消费者提前 `close()` ⇒ 只执行到已完成的轮次。
- `input` 是 `Command` ⇒ 调用时仍返回惰性迭代器；**首次 `next()`** 抛 `TypeError`
  （不执行节点；恢复路径归 B14F1 / B15F1）。
- `checkpoints` / `messages` ⇒ 恒为空序列且不抛异常（v1 边界）。
- `values` 的最后一个 `payload` 含 `"__interrupt__"` 时，与 `invoke` 的中断结果**逐字相等**
  （元组形态）。
- `thread_id` 未提供 ⇒ 所有事件的 `thread_id == None`；提供 `configurable["thread_id"]` ⇒
  顶层 `thread_id` 被覆盖（`resolved_thread_id()` 口径）。
- 用户提供 `RunConfig(run_id="x")` ⇒ 事件 `run_id` **仍**是运行时生成值（`RunConfig.run_id`
  不生效 · **X-5**）。
- `stream_mode` 大小写 / 空白（如 `"Values"`）⇒ 非法（MUST NOT 自动纠正）。
- 同一次 `stream()` 的全部事件共享同一 `run_id`；两次 `stream()` 的 `run_id` 不同。
- L2 的 `run_super_step` / `run_super_steps` 签名、`freegraph.runtime.__all__` 的 **23** 个
  符号保持不变。

---

## Upstream Parity *(mandatory — 宪法 v1.12.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11** / `langchain-core` **1.7.6**（取证于 2026-11-19，
本仓库 `.venv` 实际安装版本 · 与 `pyproject.toml` 的差分依赖钉死值一致）

### §1 逐条对照（P-01…P-23）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | 七种 mode 名 | `langgraph/types.py:122-124`（`StreamMode` Literal） | **逐字同名**：`values` / `updates` / `checkpoints` / `tasks` / `debug` / `messages` / `custom` | SAME | 原则 XI ① 照抄命名 |
| P-02 | 单 mode 的产出形态 | `langgraph/pregel/main.py:4242-4243`（`yield payload`） | 固定四键信封（`stream_mode` / `payload` / `run_id` / `thread_id`） | DIFF | D11 要求每条事件带 id ⇒ **X-1** |
| P-03 | 多 mode 的产出形态 | `langgraph/pregel/main.py:4236-4239`（`yield (mode, payload)`） | 同一信封，`stream_mode` 字段区分 | DIFF | 同上 ⇒ **X-1** |
| P-04 | `values` 的节奏 | `langgraph/types.py:127`（each step）· `_loop.py:699-707`· 实测 **E-1 / E-12**（先初始状态，再每步一条） | 初始状态 + 每个完成的 super-step 一条 | SAME | 只比 `payload` 投影；信封差异归 **X-1** |
| P-05 | `values` 含中断 | `langgraph/pregel/_loop.py:1443-1451`· 实测 **E-8** | 收尾 `values` 含 `"__interrupt__"` | SAME | 只比 `payload` 投影；信封差异归 **X-1** |
| P-06 | `updates` 的粒度与同通道多写 | `langgraph/types.py:129-130`· `_loop.py:1452-1459`· `_io.py:118-174`· 实测 **E-2** | 每完成 task 一条；同通道多写 ⇒ **元组**（上游包成 `{"$writes": [...]}`） | DIFF | 归约语义不变、仅值形态不同 ⇒ **X-1** 的子项 |
| P-07 | `tasks` 的粒度与载荷 | `_loop.py:580` / `:674`（开始）· `:1461-1466`（完成）· `debug.py:41-70` / `:106-125`· 实测 **E-3**（每 task 两条、普通 dict） | 每完成 task 一条、载荷 = `PregelTask` | DIFF | 提示词 FR-010 冻结 ⇒ **X-3** |
| P-08 | `debug` 的包裹形态 | `_loop.py:1389-1412`· 实测 **E-4**（`{step,timestamp,type,payload}`） | 同形包裹，`type="task_result"`，`payload` = `PregelTask`；无 checkpoint 事件 | DIFF | 载荷换 `PregelTask` ⇒ **X-4** |
| P-09 | `checkpoints` 的数据源 | `_loop.py:631-636`（`_emit("checkpoints", map_debug_checkpoint, …)`）· `debug.py:144`（`map_debug_checkpoint`）· `_loop.py:1081`（`_put_checkpoint`）· 实测 **E-5**（挂 checkpointer 时 3 条） | v1 恒为空序列（真实源归 B14F1） | 能力尚未交付 | 走 Out of Scope / 下游承接 **D-2**；**不记偏离** |
| P-10 | `messages` 的数据源 | `langgraph/types.py:132`· 实测 **E-6**（无 LLM 时 0 条） | v1 恒为空序列；有源时**原样透传**，不做 LangChain 抽取 | 能力尚未交付 | LangChain 特有，归 freechain；**不记偏离** |
| P-11 | `custom` 的载体 | `langgraph/config.py:126` / `:195-196`（contextvar 取 writer）· `_executor.py:64`（`copy_context()`）/ `:71`（`ctx.run`）/ `:164`（async `copy_context()`）· 实测 **E-7** | 同款：运行级 contextvar + 每任务 `copy_context()` | SAME | 原则 XI ① 照抄机制；⚠️ **仅指载体**，产出时机另见 **P-23 / X-6** |
| P-12 | 无流时 `get_stream_writer()` | `langgraph/config.py:13-14`（`_no_op_stream_writer`）· 实测 **E-9**（`invoke` 期间返回可调用对象、不抛） | 返回 no-op 可调用对象 | SAME | 照抄 |
| P-13 | 单步 / 整轮分离 | `_loop.py:599`（tick 注释）· `main.py:2964`（`while loop.tick(): … yield`） | L3 主循环反复驱动 L2 单轮入口（公开 `run_super_step` 或私有 `_stream_tick`）；两者共享同一单轮实现 | SAME | 与上游同构（私有助手只是 `route_config` / 精确上限的实现细节） |
| P-14 | `PregelTask` 七字段 | `langgraph/types.py:637-646` | `src/freegraph/contracts/types.py:141`（已存在 · 逐字同名字段） | SAME | 零新增公开面 |
| P-15 | 非法 mode 的失败信号 | 实测 **E-10**（静默产出空流） | 调用时 `ValueError`（点名非法值 + 列出合法值） | STRICTER | 原则 XI「失败信号 MAY 更严」⇒ **X-2** |
| P-16 | 事件与 `run_id` / `thread_id` | 上游 v1 事件**不带** id；v2 信封也不带 `run_id` / `thread_id`（`main.py:4228`） | 每条事件带运行时生成的 `run_id` + 解析后的 `thread_id` | DIFF | D11 硬约束（事件带 id）⇒ **X-1** |
| P-17 | `RunConfig.run_id` 是否可指定 | 上游 `RunnableConfig` 允许传入 `run_id`（`langchain_core/runnables/config.py` 一族） | **事件**的 `run_id` 恒由运行时生成；`RunConfig.run_id` 在 `stream()` 路径**不生效** | STRICTER | D11 追认「用户不设置」⇒ **X-5** |
| P-18 | 中断时的流式收尾 | `_loop.py:1441-1451`· `:1461-1466`· 实测 **E-8**（`values` / `updates` 含 `__interrupt__`；`tasks` 仍产出 task 完成事件；流正常结束） | `values` / `updates` 同款；`tasks` 为被中断 task 补发一条（`interrupts` 非空）；`debug` 包裹同款 | SAME | `tasks` 的载荷类型差异归 **X-3**；`debug` 包裹差异归 **X-4** |
| P-19 | 提前停止 / 惰性 | 上游 `stream()` 是同步惰性生成器（同线程驱动） | 同款；提前停止不泄漏、不吞异常 | SAME | 与上游一致 |
| P-20 | `StreamWriter` 关键字注入 | `langgraph/_internal/_runnable.py:183-188`（参数名 `writer` · runtime key `stream_writer`）· 实测 **E-17** | 参数名 `writer` 的关键字注入（FR-036）· 无流 no-op | SAME | 照抄参数名与注解匹配集；`stream_writer` 是 runtime key |
| P-21 | `stream_mode` 默认档 / `None` | `langgraph/graph/state.py:1357`（`CompiledStateGraph` 默认 `updates`）· `langgraph/pregel/main.py:2737-2743`（`None` 解析为默认档）· 实测 **E-18** | 签名默认 `None`，解析为 **`updates`**；`None` 不报错 | SAME | 照抄上游默认档与 `None` 语义 |
| P-22 | `stream(Command)` 输入 | 上游 `stream(input: InputT \| Command \| None)` 接受 `Command` 作为恢复输入（`pregel/main.py:2655`） | v1 只做全新运行；`Command` ⇒ **首次迭代** `TypeError`（能力尚未交付） | 能力尚未交付 | 恢复路径归 **B14F1 / B15F1**；不记偏离（Out of Scope） |
| P-23 | `custom` 的**产出时机** | 上游 `stream_writer` 直接 `stream.put(...)`（`pregel/main.py:2841-2849` / `:3280-3287` 的 `SyncQueue`）⇒ **逐写即时入队** | 本轮 `custom` 写入在 L2 单轮入口 **结束后按 TaskId 序批量产出** | **DIFF** | 并发下保证「TaskId 序 + 任务内写入序」的确定性；与 P-11 的载体 SAME 分开标注 ⇒ **X-6** |

### §2 实测基线（E-1…E-18 · `langgraph 1.2.11` · 取证于 2026-11-19）

| # | 实验 | 结果 |
|---|---|---|
| **E-1** | 两节点线性图 `a → b`，`stream_mode="values"` | 3 条：`{"x":0,"log":[]}` → `{"x":1,"log":["a"]}` → `{"x":2,"log":["a","b"]}` |
| **E-2** | 同图，`stream_mode="updates"` | 2 条：`{"a": {...}}` / `{"b": {...}}`（按 task） |
| **E-3** | 同图，`stream_mode="tasks"` | **4 条**：每个 task 各有一条**开始**（`id/name/input/triggers`）与一条**完成**（`id/name/error/result/interrupts`） |
| **E-4** | 同图，`stream_mode="debug"` | 4 条：`{step,timestamp,type,payload}`，`type` 为 `task` / `task_result` |
| **E-5** | 挂 `MemorySaver`，`stream_mode="checkpoints"` | 3 条 checkpoint（含 `values` / `next` / `metadata` / `tasks`） |
| **E-6** | 无 LLM 调用的节点，`stream_mode="messages"` | 0 条 |
| **E-7** | 节点内 `get_stream_writer()({"msg":"hi"})`，`stream_mode="custom"` | 1 条：`{"msg":"hi"}` |
| **E-8** | 节点内 `interrupt("approve?")`；分别消费 `values` / `updates` / `tasks` | `values` = 初始 + 含 `__interrupt__` 的收尾；`updates` = `{"__interrupt__": (...)}`；`tasks` = 开始 + 完成（`interrupts` 非空）；**流均不抛** |
| **E-9** | `invoke()` 期间调用 `get_stream_writer()` | 返回可调用对象，不抛异常；图正常完成 |
| **E-10** | `stream_mode="bogus"` / `["values","bogus"]` | 静默产出空流（或仅合法 mode 的事件），**不抛** |
| **E-11** | `stream_mode=["values","updates"]` | 产出 `(mode, payload)` 元组序列：`("values", …)` / `("updates", …)` / `("values", …)` |
| **E-12** | `values` 的第一条 | 是**输入状态**（执行前），不是第一步之后的状态 |
| **E-13** | 节点写 `custom` 后 `raise RuntimeError` | `custom` 先产出，然后 `RuntimeError` |
| **E-14** | 中断节点，`stream_mode="tasks"` / `debug` | `tasks` = 开始 + 完成（`interrupts` 非空）；`debug` = `task` + `task_result` |
| **E-15** | 非法 mode | `list(app.stream(...))` 返回空 / 忽略非法项 |
| **E-16** | 多 mode | 产出 `(mode, payload)` 元组 |
| **E-17** | `def node(state, writer)` / `def node(state, stream_writer)` | `writer` 被注入并产出 custom；`stream_writer` **不被注入** ⇒ `TypeError` |
| **E-18** | 不传 `stream_mode` / 显式 `stream_mode=None`（`CompiledStateGraph`） | 均按 **`updates`** 产出（示例：两节点图 = 每 task 一条），不抛异常 |

### §3 差分场景组 *(mandatory)*

> 编号承接 B8F1 的 `D-103…D-120` ⇒ 本 feature 使用 **D-121…D-136**。

| # | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 |
|---|---|---|---|
| **D-121** | `values` 的载荷序列（投影掉信封） | freegraph 的 `payload` 序列 == 上游的 payload 序列 | SAME |
| **D-122** | `values` 最后一条 vs `invoke` 终态 | 两侧的最终状态逐字相等 | SAME |
| **D-123** | `updates` 的单 task 载荷（投影掉信封） | 单节点单步：`{node: {...}}` 逐字相等 | SAME |
| **D-124** | `custom` 的载荷 | 两侧都出现 `{"msg":"hi"}`（原样） | SAME（仅比载荷；**产出时机差异归 X-6**） |
| **D-125** | `tasks` 的条数与载荷 | freegraph：每完成 task 一条 + `PregelTask`；上游：每 task 两条 + dict | DIFF（**X-3**） |
| **D-126** | `debug` 的包裹载荷 | freegraph：`type="task_result"` + `PregelTask`；上游：`task` / `task_result` + dict | DIFF（**X-4**） |
| **D-127** | 多 mode 的形态 | freegraph：信封序列；上游：`(mode, payload)` 元组 | DIFF（**X-1**） |
| **D-128** | 每条事件的 id | freegraph：每条含 `run_id` / `thread_id`；上游 v1：不含 | DIFF（**X-1**） |
| **D-129** | 非法 mode | freegraph：`ValueError`；上游：空流 / 忽略 | STRICTER（**X-2**） |
| **D-130** | 中断的 `values` / `updates` 载荷 | 两侧都含 `__interrupt__`，元素逐字一致；流都不抛 | SAME |
| **D-131** | 提前停止（取 1 条后 `close()`） | 两侧都不产生悬挂线程 / 不吞异常 | SAME |
| **D-132** | 无流时的 `get_stream_writer()` | 两侧都返回可调用对象、不抛 | SAME |
| **D-133** | 中断时的 `tasks` | 两侧都为被中断 task 产出一条完成事件（`name` / `interrupts` 投影一致） | SAME |
| **D-134** | `RunConfig(run_id="x")` 下的事件 `run_id` | freegraph：运行时生成值（不采用 `"x"`）；上游：采用 `"x"` | STRICTER（**X-5**） |
| **D-135** | 不传 `stream_mode` / 显式 `stream_mode=None` | 两侧都按默认 `updates` 产出；不抛异常 | SAME |
| **D-136** | 条件边图的 `stream` 路由 | 两侧的执行节点序列 / 最终状态逐字相等 | SAME |

⇒ **共 16 条**（D-121…D-136）⇒ **判词分布** = **SAME 10**（D-121 / D-122 / D-123 / D-124 /
D-130 / D-131 / D-132 / D-133 / D-135 / D-136）+ **DIFF 4**（D-125 / D-126 / D-127 / D-128）+
**STRICTER 2**（D-129 / D-134）。

### §4 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | DIFF（必须自研区 ③：freegraph 自创的诊断关联能力） | 事件形态：上游单 mode 直接 yield 载荷、多 mode yield `(mode, payload)`；freegraph 统一为四键信封 | D11 已冻结「每条事件 MUST 带 `run_id` / `thread_id`」；L1 返回类别是 `Iterator[dict[str, Any]]` ⇒ 信封是唯一同时满足两者的载体 | D11（2026-11-05 已批准） |
| **X-2** | STRICTER（失败信号更严） | 非法 mode：上游静默空流 / 忽略；freegraph 调用时 `ValueError` | 「拼错名字无声地少跑」与 B7F3 的 X-2（未知 key ⇒ 显式失败）同类；原则 XI ② 允许失败信号更严 | 本 feature |
| **X-3** | DIFF（形态差异） | `tasks`：上游每 task 两条 + 普通 dict；freegraph 每完成一条 + `PregelTask` | 提示词 FR-010 已冻结粒度与载荷；`PregelTask` 是 L1 既有类型（零新增公开面） | 提示词初稿「下游承接（B7F1 + B10F1）」D-2 · `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §5.3 |
| **X-4** | DIFF（形态差异） | `debug` 的包裹载荷换 `PregelTask`（`type="task_result"`）；v1 无 checkpoint 类 debug 事件 | `debug` 以 `tasks` 为唯一 v1 源；`PregelTask` 是 L1 既有类型；checkpoint 源归 B14F1 | 本 feature |
| **X-5** | STRICTER（更严的标识纪律） | `run_id`：上游允许从 `RunnableConfig` 指定；freegraph 事件的 `run_id` 恒由运行时生成，`RunConfig.run_id` 不生效 | D11 追认「用户不可指定 / 不可覆盖」；采用**忽略**而非拒绝 ⇒ 上游风格配置可原样传入，不新增成功路径失败点；`RunConfig.run_id` 字段为上游兼容保留，不改字段清单 | D11（2026-11-05 已批准）· 2026-11-19 clarify 轮确认选项 A |
| **X-6** | DIFF（**必须自研区 ②：上游自身的缺陷 / 不确定**） | `custom`：上游逐写即时入队；freegraph 在每轮 L2 单轮入口结束后按 TaskId 序批量产出 | 上游并发 `custom` 的跨任务顺序依赖完成时刻（**不确定**）；freegraph 取轮末批量保证「TaskId 序 + 任务内写入序」的**确定性**；不把可观测事件塞进 `_TaskOutcome`（H-7）；与 P-11 的载体 SAME 分开标注 | 本 feature |

### §5 破冻结面的回溯修订清单 *(本 feature 触发)*

| # | 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|---|
| **T-1** | **B7F1** 的 `SuperStepResult(state, executed, node_writes, steps)` 构造签名（契约 §1 / §5.3） | ① `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §5.3 ② `specs/b7f1-superstep-loop/spec.md` 的相关 FR / 裁定 ③ `src/freegraph/runtime/superstep.py:348-377` 的类 docstring | **拆分而不删**：原四字段**逐字保留**；**追加** `tasks: tuple[PregelTask, ...] = ()`（末尾 · 带缺省 ⇒ 既有按关键字构造的调用方零改动） | 本 feature 的**唯一一次**追认（T-1…T-5 并入同一次） |
| **T-2** | **B12F1** 的裁定 25 ② / FR-013「`SuperStepResult` 的四字段冻结面 MUST 零改动」（`specs/b12f1-concurrency-errors/spec.md:792`） | `specs/b12f1-concurrency-errors/spec.md` 的裁定 25 ② / FR-013 行 + 其相关契约行 | **只补注记**：原「四字段零改动」文字**不改写**，追加「自 B8F2 起：**追加**第 5 字段 `tasks` · 原四字段不变」 | 并入 T-1 的同一次追认 |
| **T-3** | **L1 + L3** 的 `CompiledGraph.stream` 的 `config` 注解 + `stream_mode` 默认值（`RunConfig \| None` / `"values"` · `src/freegraph/contracts/protocols.py:278-286` 与 `src/freegraph/_stategraph.py:357-365` 的 concrete stub） | ① `src/freegraph/contracts/protocols.py:278-286`（`config` 放宽为 `RunConfig \| Mapping[str, Any] \| None`；`stream_mode` 默认改为 `None`，`None` 解析为 `"updates"`）② `src/freegraph/_stategraph.py:357-365` 的 concrete 签名同步（默认 `None` + `config` 放宽；**由 T022 落地，T064 只复核**）③ `specs/b2f1-contracts-protocols/contracts/public-api.md` 的 `stream` 行与 `specs/b2f1-contracts-protocols/data-model.md` §2.5 ④ **B7F2** 的 `specs/b7f2-compile/contracts/compile-contract.md` §2.4 + `specs/b7f2-compile/data-model.md` §2.3 + `specs/b7f2-compile/plan.md` Phase A / `specs/b7f2-compile/tasks.md` T006（只补注记：自 B8F2 起 `stream` 已交付、默认 `None ⇒ "updates"`；原 `"values"` 文字保留为历史）⑤ `README.md` 的 API 兼容矩阵 `stream` 行（由 **T068** 执行） | **拆分而不删**：原 `RunConfig \| None` 写法保留为**子集**（只传 `RunConfig` 仍合法）；显式 `stream_mode="values"` 仍合法；**默认值**改为上游同款 `None ⇒ "updates"`；B7F2 契约原描述**不改写**，只追加注记 | 并入 T-1 的同一次追认 |
| **T-4** | **B10F1** 契约 §3 的「线程池**不继承** `contextvars`（实测）」表述 + `src/freegraph/runtime/_interrupt.py` 模块 docstring | ① `specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md` §3 ② `src/freegraph/runtime/_interrupt.py:15-27` 的模块 docstring | **只补注记**：原描述**不改写**，追加「自 B8F2 起：`run_tasks_concurrently` 每任务 `copy_context()` ⇒ 线程池**继承**运行级 contextvars；两级机制照常工作，判据只收紧」 | 并入 T-1 的同一次追认 |
| **T-5** | **B2F2** 的公开面「门面恰 7 个符号」+ **B2F1** 的契约清单「恰 21 个符号」（`specs/b2f2-public-api-facade/contracts/facade-api.md` §0 · `public-api-snapshot.txt` · `specs/b2f1-contracts-protocols/contracts/public-api.md` §0） | ① `specs/b2f2-public-api-facade/contracts/facade-api.md` §0 ② `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt` ③ `specs/b2f1-contracts-protocols/contracts/public-api.md` §0 ④ `tests/contracts/test_architecture.py` 的 G7 解析器（`:389-460` · 21 → 22 · 新增分段）⑤ `README.md` 的 API 兼容矩阵（由 **T068** 执行）⑥ 源码模块 docstring：`contracts/types.py`（「五个核心类型」）· `contracts/__init__.py`（「恰为 21 个」）· `graph.py`（「7 个」/「stream 仍抛 NotImplementedError」）· `_stategraph.py`（「stream 未实现」）（只补计数/注记） | **拆分而不删**：原 7 个门面符号 / 21 个契约符号**一个不删**；**追加**门面 `get_stream_writer`（7 → **8**）与契约 `StreamWriter`（21 → **22**） | 并入 T-1 的同一次追认 |

> ⚠️ **追认次数**：本 feature 的**唯一一次**追认额度由 **T-1…T-5** **共同**使用
> （宪法 v1.8.0「每 feature ≤ 1 次」）⇒ 追认文字 MUST 落
> `harness/verification/B8F2/manual-verification.md` ⇒ **未追认前 MUST NOT 合入**。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 提供 `stream(input, config=None, *, stream_mode=None)`，返回
  **惰性可迭代对象**（生成器或等价结构）；`stream_mode=None` MUST 解析为默认档
  **`"updates"`**（上游 `CompiledStateGraph` 同款）；调用 `stream()` 本身 MUST NOT 执行图。
- **FR-002**: `stream_mode` MUST 是 `str`、`Sequence[str]` 或 `None`（`None` = 默认档
  `"updates"`）；每个值 MUST 在**闭集**
  `{values, updates, checkpoints, tasks, debug, messages, custom}` 内；非法值 / 空序列 ⇒
  **调用时**抛内置 `ValueError`（点名非法值并列出七种合法值）；`bool` / `int` / 不可迭代
  对象（`None` 除外）⇒ **调用时** `TypeError`；重复值 MUST 去重保序。
- **FR-003**: `values` 模式 MUST 产出「**初始状态** + 每个完成的 super-step 一条」的
  **完整状态**序列。
- **FR-004**: `updates` 模式 MUST 产出每个**完成 task** 的**更新增量**（载荷见 FR-016）。
- **FR-005**: 系统 MUST 提供 `StreamWriter`（类型别名 `Callable[[Any], None]`）与
  `get_stream_writer() -> StreamWriter`；节点内经它写入的数据 MUST 在 `custom` 模式中产出；
  节点签名声明参数名 `writer` 时 MUST 以关键字注入当前 writer（详见 FR-036）。
- **FR-006**: 流式消费 MUST NOT 改变图的执行语义；消费者**提前停止** MUST NOT 造成资源泄漏
  （零悬挂线程 / 零脏 contextvar）或状态不一致；MUST NOT 吞掉节点的真实异常。
- **FR-007**: MUST NOT 引入 async（`astream` 属 v2 范围）；本 feature 只做**同步**流。
- **FR-008**: 系统 MUST NOT import `langchain` / `langchain-core` / `langgraph` / `langsmith`；
  MUST NOT 读环境变量；MUST 零出站。
- **FR-009**: `stream()` MUST **逐轮**产出 ⇒ MUST 以**L2 单轮入口** **反复驱动**
  （上游同款 · `PregelLoop.tick()`）：公开 `run_super_step` **或** L2 私有 `_stream_tick`
  ⇒ `_stream_tick` MUST 与 `run_super_step` 共享同一 `_run_single_step` / `_run_round` /
  `_evaluate_*` / `_determine_triggers` 实现（MUST NOT 另写执行 / 路由 / 触发）⇒
  主循环 **MUST NOT** 复用 `_run_graph_loop` 的整图循环
  ⇒ MUST **NOT** 改动既有 L2 入口（`run_super_step` / `run_super_steps`）的**签名**
  ⇒ MUST **NOT** 新增**公开** L2 入口（`freegraph.runtime.__all__` 的 **23** 个符号不变；
  私有助手不进 `__all__`）；
  输入写入 / 会话恢复 / contextvar 绑定 MUST 复用 L2 既有的初始化语义（允许抽成私有初始化
  助手 / 私有生成器；MUST NOT 在 L3 直接写通道）。
- **FR-010**: `tasks` 档 MUST 产出 **task 级**事件（**每个** task 完成时一条）⇒ 载荷 MUST 用
  `freegraph.contracts.PregelTask`（七字段同名同义）⇒ `SuperStepResult` MUST 追加
  `tasks: tuple[PregelTask, ...]`（末尾 · 缺省 `()`）⇒ MUST **NOT** 删既有 4 个字段
  （`state` / `executed` / `node_writes` / `steps`）。
- **FR-011**: 节点侧的 `StreamWriter` 写入 MUST 照抄上游的 **contextvar + 执行器
  `copy_context()`** 传播机制 ⇒ 落点 = `run_tasks_concurrently` 的**每任务** `copy_context()`
  ⇒ MUST **NOT** 另立一套**并行**的显式传参机制 ⇒ **同一 carrier** MUST 同时服务
  `get_stream_writer()` 与节点签名 `writer` 的关键字注入（FR-036）⇒ MUST **回溯修订**
  B10F1 契约 §3 与 `_interrupt.py` docstring 的「线程池不继承 contextvars」表述（只补注记）；
  B10F1 的两级 ContextVar 机制 MUST **NOT** 被移除。
- **FR-012**: `values` 档的**完整状态**归一 MUST 在 **L3**（门面侧 · 与 `invoke()` 同模块）
  完成 ⇒ MUST 复用 B7F3 的 `_full_state`（`src/freegraph/_stategraph.py:235`）⇒ MUST NOT
  复制到 L2；**L2 只负责产出每轮的稀疏状态**。
- **FR-013**: 每一条事件 MUST 是普通 `dict`，**恰含**四键：
  `"stream_mode"`（`str`）/ `"payload"`（该 mode 的载荷）/ `"run_id"`（`str`）/
  `"thread_id"`（`str | None`）；`run_id` / `thread_id` MUST NOT 混进 `payload`。
- **FR-014**: `stream_mode` 为序列时 MUST 在同一流中产出各 mode 的事件；每条事件的
  `stream_mode` MUST 标明来源；**跨 mode 的轮内顺序** MUST 固定为
  `custom → updates → tasks → debug → values`（同一轮内）⇒ 判据可复现。
- **FR-015**: 对**同图、同输入、无静态断点、无会话历史**的运行，`values` 的最后一条
  `payload` MUST 与 `invoke()` 的最终状态**逐字相等**（中断时含 `"__interrupt__"` 元组）。
- **FR-016**: `updates` 的 `payload` MUST 是 `{节点名: {通道 key: 值 | 值的元组}}`；
  同一 task 对同一通道多次写入 ⇒ **按写入顺序的元组**；对同图、同输入、无静态断点、
  无会话历史的运行，把全部 `updates` 按**通道归约语义**逐条应用后 MUST 等于 `invoke()` 的
  最终状态（MUST NOT 用简单 `dict.update` 冒充合并）。
- **FR-017**: `checkpoints` 档 MUST 被接受且 v1 **恒为空序列**；MUST NOT 伪造 checkpoint
  事件；真实数据源归 **B14F1**（下游承接 D-2）。
- **FR-018**: `messages` 档 MUST 被接受且 v1 **恒为空序列**；MUST NOT 实现 LangChain 消息
  抽取；未来有源时 MUST **原样透传**（归 freechain）。
- **FR-019**: `debug` 档 MUST 为每个 `tasks` 事件产出一条包裹事件：
  `{"step": int, "timestamp": str(UTC ISO-8601), "type": "task_result", "payload": PregelTask}`；
  `step` = **1 起的 super-step 序号**（同轮多 task 相同）⇒ **进入每一轮时递增**（成功轮与
  中断轮使用同一规则；`_stream_tick` 返回 `None` 的收敛轮不产出事件）；
  `timestamp` MUST 是 **UTC ISO-8601** 字符串（含 `+00:00` 时区偏移 · 示例
  `2026-11-20T00:00:00+00:00`）且 MUST 可被 `datetime.fromisoformat` 解析；
  v1 MUST NOT 产出 checkpoint 类 debug 事件。
- **FR-020**: `PregelTask` 的字段语义 MUST 按裁定 6 落成（`id` 运行内唯一（生成方式不冻结）/ `name` 节点名 /
  `path` 标准或 fan-out 形态 / `error` 原对象 / `interrupts` 元组 / `state` 恒 `None` /
  `result` 与 `updates` 同形）；**被中断的 task** MUST 出现在 **`stream()` 的 `tasks` /
  `debug` 事件**中（`error=None` · `interrupts` 非空 · `result` = 已发生写入），但
  **MUST NOT** 要求它出现在 `SuperStepResult.tasks` 里（中断轮不产出 `SuperStepResult`）；
  `SuperStepResult.tasks` 的单轮 / 多轮累计口径 MUST 与 `executed` / `node_writes` 一致
  （只累计**成功返回**的轮次）。
- **FR-021**: `get_stream_writer()` MUST 在 `stream()` 期间返回当前写入器；在 `invoke()` 或
  无流时 MUST 返回 **no-op** 可调用对象（不抛异常）。
- **FR-022**: `custom` 事件的顺序 MUST 是「任务标识序 + 任务内写入序」；写入 MUST 线程安全；
  MUST NOT 把 custom 写入塞进 `_TaskOutcome`（H-7）。
- **FR-023**: `stream` 的 `config` 注解 MUST 放宽为
  `RunConfig | Mapping[str, Any] | None`（与 `invoke` 逐字同款）；MUST 按 B7F3 的载体边界
  原样交给 L2 ⇒ MUST NOT 在门面层把普通映射翻译成 `RunConfig`；`stream` 的 `input` 注解
  MUST 沿用 L1 现状 `StateDict`；运行期 MUST 允许 `None` = **无输入写入**（图照常由静态入口
  触发）；`Command`（及其他非法 `input` 类型）的拒绝 MUST 在**第一次迭代**发生（保持完全
  惰性），`TypeError` 点名「恢复路径归 B14F1 / B15F1」；`stream_mode` 的校验仍在**调用时**
  完成（两者时机不同，MUST NOT 混淆）。
- **FR-024**: `stream()` MUST 复用 B8F1 的**同一份**路由求值实现（MUST NOT 另写路由）；
  路由在 `stream()` 的**同一次执行**里可观察（由 L2 单轮入口 `_stream_tick` / `run_super_step`
  保证）⇒ **双参路由 `f(state, config)` 的第二参 MUST 是用户交给 `stream()` 的原始 `config`**
  （`RunConfig` / 普通映射 / `None` · **逐字**）⇒ MUST NOT 传 `None` 或翻译成 `RunConfig`。
- **FR-025**: `GraphInterrupt` MUST 被 `stream()` 当作**受控暂停**：为被中断 task 补发
  `tasks` / `debug` 事件（`interrupts` 非空），产出收尾 `values` / `updates`
  （含 `"__interrupt__"`）与已发生的 custom 事件后**正常结束迭代**
  （不把 `GraphInterrupt` 抛给消费者）。
- **FR-026**: 非中断异常 MUST **原类型 + 原消息**从迭代器重抛（不包装 / 不吞）；失败轮
  **已发生**的 custom 写入 MUST **先产出**（上游实测：先产出再抛）⇒ 失败轮的
  `values` / `updates` / `tasks` / `debug` MUST NOT 产出；已成功轮次的事件**不回撤**。
- **FR-027**: 每次 `stream()` MUST 生成**一个** `run_id`（`uuid4().hex`）并用于该次流的
  全部事件；`thread_id` MUST 按 `RunConfig.resolved_thread_id()` 的同一口径解析
  （`configurable["thread_id"]` 优先）；`RunConfig.run_id` MUST NOT 被用作事件 `run_id`。
  `StreamSession` MUST 把该 `run_id` / `thread_id` 绑定到 L2 私有 contextvar
  （`_STREAM_RUN_ID` / `_STREAM_THREAD_ID`），供 **B18F1 / B19F1** 的 span 读取
  （D-3 / H-9）⇒ MUST NOT 新增公开符号，MUST NOT 改 `run_super_step` / `run_super_steps` 签名。
- **FR-028**: `stream()` v1 MUST **不**提供会话连续 / checkpoint 持久化 / `Command` 恢复路径
  （这些属 B14F1 / B15F1 / B16F1）；`StreamSession` MUST **忽略** `checkpointer`
  （不读快照、不写快照、不触发恢复）；`checkpointer` 的存在 MUST NOT 改变本 feature 的七档语义。
  **静态断点**（`interrupt_before` / `interrupt_after`，B13F1）在 stream v1 **不支持**：
  MUST 复用 `_reject_static_points_for_low_level` 的 `ValueError`（V-26 口径）⇒
  在**第一次迭代**抛 `ValueError`（点名「静态断点只在图级 `run_graph` 生效」）⇒
  MUST NOT 静默忽略，MUST NOT 为此新增错误类型。
- **FR-029**: MUST NOT 新增**公开** L2 符号；`freegraph.runtime.__all__` MUST 仍恰为 **23**
  个符号；允许新增**私有**模块 / 私有生成器（前导下划线 · 不进 `__all__`）。
- **FR-030**: 公开面新增 MUST **仅**为：`freegraph.graph.get_stream_writer`（门面 7 → **8**）
  与 `freegraph.contracts.StreamWriter`（契约 21 → **22**）；MUST 同步更新 API 兼容矩阵与
  `public-api-snapshot.txt`；MUST NOT 在顶层 `freegraph` 包新增导出（顶层保持惰性 · G1）。
- **FR-031**: MUST 交付 `harness/verification/B8F2/acceptance.py`（退出码 `0` PASS / `1` FAIL /
  `2` 环境未就绪 · 打印 `B8F2 acceptance: PASS|FAIL`）并由一条 pytest **真跑**它；
  MUST 交付 `harness/verification/B8F2/manual-verification.md`（五段式 + 追认文字）。
- **FR-032**: MUST 把 E-1…E-18 的实测固化成 `tests/differential/parity_probe.py` 的
  **D-121…D-136** 场景；上游缺席即 `skip`（沿用 B5F2 纪律）；判词分布 MUST 与 §3 一致。
- **FR-033**: MUST 按「登记 + 回溯修订 + 发起者追认」三条完成 **T-1…T-5**；既有断言
  **拆分而不删**；原描述**不改写**；追认次数 == **1**。
- **FR-034**: 本 spec MUST NOT 单方面修改立项书 §5.2 的规模行；实现期实测值另记，
  修订属发起者职权（与 B8F1 的 R-5 同款）。
- **FR-035**: MUST NOT 实现 `astream` / trace span 生产 / `TraceSink` 接入 / 前端 UI /
  `checkpoints` 真实数据源 / LangChain 消息抽取（均见 Out of Scope）。
- **FR-036**: 节点签名声明参数名为 **`writer`**（`POSITIONAL_OR_KEYWORD` 或
  `KEYWORD_ONLY`；注解 ∈ {`StreamWriter` · 字符串 `"StreamWriter"` · 空}）时，节点调用
  MUST 以**关键字**注入当前 `get_stream_writer()`；`**kwargs` / 其它参数名 / 注解不匹配
  ⇒ MUST NOT 注入（按一参调用）；无流时注入的 writer MUST 是 no-op；MUST NOT 新增公开符号
  （参数名 `writer` 不是公开 API 符号）；`stream_writer` 是 **runtime key**，MUST NOT
  作为节点参数名。
- **FR-037**: `stream()` 的轮循环 MUST 复用既有 L2 的 `recursion_limit` / `max_steps`
  解析口径（`resolve_limit`；由 `StreamSession` 在首次迭代内完成，L3 MUST NOT 重复解析）；
  **精确判定**必须发生在**执行下一轮之前**：
  「触发集非空 **且** `state.step >= max_steps`」⇒ `GraphRecursionError`
  （零新增错误类型）⇒ 该判定由 L2 私有 `_stream_tick` 复用 `_determine_triggers`
  完成（MUST NOT 多跑一轮、MUST NOT 在恰好收敛于上限时误抛）；`max_concurrency`
  MUST 由流式会话从 `config`（`RunConfig.max_concurrency` 或普通映射的同名字段）解析后
  传给 L2 单轮入口。⚠️ `stream()` 签名**不新增** `max_concurrency` 关键字
  ⇒ 不存在「关键字优先」的第三态；非法取值仍由 L2 既有校验承担。

### Key Entities *(include if feature involves data)*

- **`StreamEvent`（事件信封 · 普通 `dict`）**: 四键 `stream_mode` / `payload` / `run_id` /
  `thread_id`；由 L3 门面构造，**唯一形态**。
- **`StreamWriter`（类型别名）**: `Callable[[Any], None]`；节点侧写入自定义数据的入口；
  由 `get_stream_writer()` 取得，或在节点签名声明 `writer` 时由关键字注入（FR-036）；
  无流时 no-op。
- **`PregelTask`（既有 L1 类型）**: 七字段任务定格；本 feature 只**消费**它作为 `tasks` 载荷，
  **零新增字段**。
- **`SuperStepResult.tasks`（新增字段）**: `tuple[PregelTask, ...]`；每轮完成的 task 定格；
  单轮 = 本轮 · 多轮 = 累计。
- **`run_id` / `thread_id`**: 单次运行标识（运行时生成 · 每条事件共享）/ 会话标识
  （来自 config）；与 `TraceSink` 的 span 共享（D11）⇒ **载体 = L2 私有 contextvar**
  `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`（FR-027 · 非公开符号）。
- **`custom` 的轮末缓冲**: 本轮 `StreamWriter` 写入按 TaskId 序暂存，L2 单轮入口
  结束后批量产出（P-23 / X-6）。
- **`_stream_tick`（L2 私有单轮助手）**: 与 `run_super_step` 共享同一
  `_run_single_step` / `_run_round` / `_evaluate_*` / `_determine_triggers` 实现；
  传入原始 `route_config` 并在执行前精确判定 `recursion_limit`；
  返回 `SuperStepResult | None`（`None` = 已收敛）；**不进** `runtime.__all__`。

### Out of Scope

- `astream` / 异步流（v2，未排 feature）。
- trace span 的生产（B18F1）与 `TraceSink` 接入（B19F1）；本 feature 只保证 id 对齐。
- `checkpoints` 档的真实数据源（B14F1）；本 feature 只产出**空序列**。
- `messages` 档的 LangChain 消息抽取（freechain）；freegraph 只做**原样透传**的边界声明。
- `stream(Command(...))` 的恢复路径 / 会话连续 / checkpoint 持久化（B14F1 / B15F1 / B16F1）。
- 静态断点（`interrupt_before` / `interrupt_after`）在 `stream()` 下的行为（v1 显式拒绝 · V-26 口径）。
- 节点别名解析（B8F3）；`stream()` 只消费节点名。
- 前端 / UI 消费（B26）。
- 图导出 `get_graph` / `draw_mermaid_png`（B22F1 / B23F1）。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 七种合法 mode 名**全部**被接受（7/7 不抛异常）；`stream_mode=None` 被接受
  并按 `updates` 产出（100%）；非法 mode / 空序列 ⇒ 调用时 `ValueError`（100%）；
  `bool` / `int` / 不可迭代对象（`None` 除外）⇒ 调用时 `TypeError`（100%）。
- **SC-002**: 对同图、同输入、无静态断点、无会话历史的运行，`values` 的最后一条 `payload`
  与 `invoke()` 的最终状态**逐字相等**（100% 的测试图）；事件数 == `1 + 执行步数`。
- **SC-003**: 对同图、同输入、无静态断点、无会话历史的运行，把全部 `updates` 按通道归约
  语义合并后 == `invoke()` 最终状态（100%）；同通道多写的值形态为**元组**（100%）。
- **SC-004**: `StreamWriter` 写入的对象在 `custom` 流中**原样**出现（100%）；多次写入全部出现，
  顺序确定。
- **SC-005**: 流式执行期间**零出站**、**零环境变量读取**、**零第三方 import**（100%）。
- **SC-006**: `tasks` 每条事件都是 `PregelTask` 实例，字段可读；每个完成的 task **恰一条**
  （100%）；`SuperStepResult.tasks` 类型 == `tuple[PregelTask, ...]`（100%）。
- **SC-007**: `debug` 每条事件的键集恰为 `{step, timestamp, type, payload}`，`type` ==
  `task_result`（100%）；`step` 与轮次一致、中断轮也有独立序号（100%）；`timestamp`
  可被 `datetime.fromisoformat` 解析且 `utcoffset() == timedelta(0)`（100%）。
- **SC-008**: `checkpoints` 档序列长度 == **0** 且不抛异常（100%）。
- **SC-009**: `messages` 档序列长度 == **0** 且不抛异常（100%）。
- **SC-010**: 每条事件是 `dict` 且键集恰为四键（100%）；`run_id` 非空 `str`（100%）；
  `thread_id` 与配置一致（100%）。
- **SC-011**: 同一次 `stream()` 的全部事件共享**同一** `run_id`（100%）；两次 `stream()` 的
  `run_id` **不同**（100%）；`StreamSession` 绑定的 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`
  与该流全部事件的 `run_id` / `thread_id` 一致（100%）。
- **SC-012**: 单 mode / 多 mode 的事件都带正确的 `stream_mode`（100%）；重复 mode 去重保序
  （100%）；跨 mode 轮内顺序固定（100%）。
- **SC-013**: 提前停止后 `freegraph-node` 线程数 == **0**（100%）；后续运行结果不受影响
  （100%）；真实异常被原样重抛（100%）。
- **SC-014**: `run_super_step` / `run_super_steps` 的签名**逐字不变**（100%）；
  `freegraph.runtime.__all__` == **23** 个符号（100%）。
- **SC-015**: 七种 mode 的差分场景 D-121…D-136 **全绿**（上游缺席即 `skip`）；
  判词分布 == SAME **10** / DIFF **4** / STRICTER **2**（100%）。
- **SC-016**: 惰性 —— 未迭代的 `stream()` 执行节点次数 == **0**（100%）。
- **SC-017**: 中断时 `tasks` / `debug` 为被中断 task 产出一条（`interrupts` 非空）(100%)；
  `values` / `updates` 的收尾载荷含 `"__interrupt__"`（100%），且迭代器**正常结束**
  （不抛 `GraphInterrupt`）（100%）。
- **SC-018**: 公开面新增**仅** 2 个符号（门面 8 · 契约 22）；顶层 `freegraph.__all__`
  仍 == `["__version__"]`（100%）。
- **SC-019**: `harness/verification/B8F2/acceptance.py` 退出码 `0` 且打印
  `B8F2 acceptance: PASS`；由一条 pytest 真跑（100%）。
- **SC-020**: T-1…T-5 的「原描述 + 注记」两段都在位（100%）；追认文字、**发起者确认**与
  **日期**三者都在位（100%）。
- **SC-021**: 声明 `writer` 参数的节点在 `stream_mode="custom"` 中产出其写入（100%）；
  未声明 / 注解不匹配 / `**kwargs` ⇒ 不注入（100%）；`invoke()` 中注入 no-op、不抛（100%）。
- **SC-022**: `stream()` 超 `recursion_limit` 且**仍有任务** ⇒ `GraphRecursionError`
  （100%）；**恰好收敛于上限**（无待执行任务）⇒ 不抛（100%）；错误 MUST 在**执行超限轮之前**
  发生（MUST NOT 多跑一轮）；`max_concurrency` 从 `config` 正确解析并传给 L2 单轮入口，
  并发行为与 `invoke` 一致（100%）。
- **SC-023**: 条件边图在 `stream()` 下的路由目标序列与 `invoke()` 一致（100%）；
  **双参路由 `f(state, config)` 的第二参与用户交给 `stream()` 的原始 `config` 逐字相等**
  （100%）；`stream()` MUST NOT 另写路由实现（100%）。

### 验收判据（= 立项书 §5.2 B8F2 小目标 · 逐条可判定）

> 小目标原文：**多模式流式输出**

| # | 判据 | 判定方式 | 对应 SC |
|---|---|---|---|
| **A1** | 多模式流式输出 | 七种 mode 各有一例**可判定**断言（`checkpoints` / `messages` 判「零事件且不抛」） | SC-001 / SC-008 / SC-009 / SC-012 |
| **A2** | `values` 与 `invoke` 终态一致 | 最后一个 `values` 事件的 `payload` 与 `invoke` 结果**等值断言** | SC-002 |
| **A3** | `updates` 可合并回终态 | 按通道归约语义合并全部 `updates` 后与 `invoke` 结果**等值断言** | SC-003 |

### 追溯表（FR → SC）

| SC | 覆盖的 FR |
|---|---|
| SC-001 | FR-002 · FR-014 |
| SC-002 | FR-003 · FR-012 · FR-015 |
| SC-003 | FR-004 · FR-016 |
| SC-004 | FR-005 · FR-021 · FR-022 |
| SC-005 | FR-008 |
| SC-006 | FR-010 · FR-020 |
| SC-007 | FR-019 |
| SC-008 | FR-017 |
| SC-009 | FR-018 |
| SC-010 | FR-013 · FR-027 |
| SC-011 | FR-013 · FR-027 |
| SC-012 | FR-002 · FR-014 |
| SC-013 | FR-006 · FR-026 |
| SC-014 | FR-009 · FR-029 |
| SC-015 | FR-032 |
| SC-016 | FR-001 · FR-006 |
| SC-017 | FR-025 |
| SC-018 | FR-030 · FR-035 |
| SC-019 | FR-031 |
| SC-020 | FR-033 |
| SC-021 | FR-036 |
| SC-022 | FR-037 |
| SC-023 | FR-024 |

---

## Assumptions

- 上游版本钉死为 `langgraph 1.2.11` / `langchain-core 1.7.6`；换版本 MUST 重新核实全部锚点。
- `stream_mode` 的默认档照抄上游 `CompiledStateGraph`：签名默认 `None`，`None` 与省略等价
  ⇒ 实际按 **`updates`** 产出（`langgraph/graph/state.py:1357` · 实测 E-18）。
- `values` 的「完整状态」口径**完全复用** B7F3 的 `_full_state`（含「无值 key 填 `None`」与
  「路由通道不进键集」）；本 feature **不重新定义** schema 补齐语义。
- `updates` 的「可合并」按**通道归约语义**判定，不按简单 `dict.update`；验收图 SHOULD 同时
  含覆盖型与归约型通道，以覆盖两种合并路径。
- `checkpoints` / `messages` 的 v1 空序列是**能力边界**，不是「未实现」；验收脚本 MUST 判
  「零事件且不抛」，MUST NOT 用 `NotImplementedError` 当判据。
- `stream()` v1 只支持**全新运行**（`input: StateDict`；运行期允许 `None` = 无输入写入）；
  会话连续 / `Command` 恢复 / checkpoint 持久化由 B14F1 / B15F1 / B16F1 承接；
  `checkpointer` 在 stream v1 **被忽略**，静态断点（`interrupt_before` / `interrupt_after`）
  **显式拒绝**（首次迭代 `ValueError` · V-26 口径）。
  ⚠️ **注解与运行期的口径**：L1 的 `input` 注解保持 `StateDict`（B2F1 冻结面），
  但运行期 MUST 接受 `None`（= 无输入写入）；调用方若做静态类型检查，需按
  `StateDict | None` 断言。该差异是**有意的保守注解**，不是行为缺口。
- **L2 私有单轮助手 `_stream_tick`**：允许新增（前导下划线 · 不进 `runtime.__all__` ·
  不改 `run_super_step` / `run_super_steps` 签名）；它 MUST 与 `run_super_step` 共享
  同一执行 / 路由 / 触发实现，并负责把 `route_config`（原始 `config`）传入 B8F1 的
  双参路由、在**执行前**精确判定 `recursion_limit`。
- `RunConfig.run_id` 字段为上游兼容保留；事件的 `run_id` 由运行时生成，该字段在 `stream()`
  路径**不生效**（D11 追认 · X-5 · **宪法 v1.15.2 已订正**）。事件的 `run_id` / `thread_id`
  由 `StreamSession` 绑定到 L2 私有 contextvar（FR-027），供 B18F1 / B19F1 的 span 读取。
- `StreamWriter` 的公开入口是 `get_stream_writer()`；**关键字注入**（参数名 `writer`）也由
  本 feature 交付（FR-036）⇒ B8F1 的 DR-4 关闭；不新增公开符号。
- `custom` 的 v1 产出时机是**每轮结束后批量产出**（按 TaskId 序），不是上游的逐写即时产出；
  该差异登记为 **P-23 / X-6**。
- 事件信封的**四键形态**是 v1 冻结面；未来新增信封键 MUST 走破冻结面流程。
- 流式执行使用标准库线程池（B12F1 既有）；`copy_context()` 的每任务捕获**不改变**并发度、
  失败顺序与 `_TaskOutcome` 五字段。
- `PregelTask.id` 是**运行内唯一**的 opaque 字符串；生成方式不冻结（可与上游一样随机），
  差分断言 MUST NOT 比较 `id`；该口径与上游 UUID 语义同族，不构成额外偏离。
- 规模口径以实现期实测为准；行数 / 工时修订属发起者职权（FR-034）。

---

## 交付物与验收联动

- **交付物**：
  - `stream()` 实现（七种 mode · 事件信封 · 主循环）；
  - L2 私有 `_stream_tick`（单轮驱动 · 原始 `route_config` · 精确递归上限）；
  - `StreamWriter` / `get_stream_writer()`；
  - `SuperStepResult.tasks` 字段与 `PregelTask` 载荷；
  - 单元测试 + `tests/differential/parity_probe.py` 的 D-121…D-136；
  - `harness/verification/B8F2/acceptance.py`（退出码 `0/1/2` · 打印
    `B8F2 acceptance: PASS|FAIL`）；
  - `harness/verification/B8F2/manual-verification.md`（五段式 + 追认文字）。
- **CI 常驻门禁**：一条 pytest **真跑** `acceptance.py`；脚本与实现漂移 ⇒ 立刻红。
- **验收脚本联动**：`harness/demo/visualization.py` 的 `case_stream_modes`（七种模式）
  MUST 转绿；`harness/demo/graph_core.py` 的 C25 流式别名软断言 MUST 改为读取
  `event["payload"]` 的键（信封形态适配 · **不是**放宽判据）。
- **人工门禁**：`harness/verification/B8F2/manual-verification.md` MUST 含
  「七种 mode 实测输出 + 差分结果 + T-1…T-5 追认 + R-5 / R-6 登记」。
- **证据门禁**：mode 名与语义的证据锚点 = `langgraph/types.py:122-124`（`StreamMode`
  字面量；说明 docstring 至 `:136`）·
  `langgraph/graph/state.py:1357`（默认 `updates`）· `langgraph/pregel/main.py:2737-2743`
  （`None` 解析默认档）· `langgraph/config.py:126`（`get_stream_writer`）·
  `langgraph/pregel/_executor.py:64`（`copy_context()`）/ `:71`（`ctx.run`）/
  `:164`（async `copy_context()`）·
  `langgraph/pregel/_loop.py:580` / `:674` / `:1461-1466`（`tasks`）·
  `langgraph/types.py:637-646`（`PregelTask`）。
- **规模口径登记**：立项书 §5.2 的「1,180 行 · 3 人日」**不单方面修改**；FR-009…FR-012
  带来额外工作量（线程池 `copy_context()` + `SuperStepResult` 扩字段 + **三处**上游契约回溯修订
  （B7F1 / B10F1 / B7F2）+ 一键验收脚本）⇒ 以实现期实测为准（FR-034 · 与 B8F1 的 R-5 同款）。
- **依赖边界**：B22F1（`get_graph` + `draw_mermaid`）/ B23F1（PNG）与 `stream()` **互不依赖**
  （D-4）；B8F3 只承接流式事件的节点命名口径（D-1），**不被本 feature 阻塞**。
  立项书 §5.2 的 B22F1 依赖是 B7F2、B8F3 依赖是 B7F3，均**不是** B8F2。
