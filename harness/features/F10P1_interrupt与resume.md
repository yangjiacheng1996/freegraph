# F10P1 · `interrupt()` + `resume`（HITL 中断与恢复闭环）

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | Phase ID | `F10P1` |
> | 所属 Feature | F10（`interrupt` + `resume`） |
> | 架构层 | L2 执行内核层 |
> | 里程碑 | M1 运行时内核（第 11 个） |
> | 前置依赖 | **F9P1** |
> | 规模 | 1,160 行（实现 520 / 测试 640）· 3 人日 |
> | 建议 short-name | `p10-interrupt-resume` |
> | MVP 必需（★） | 否（**HITL 是 freechain 的强依赖能力**） |

---

## 提示词正文

### 1. 目标

交付**人工介入（HITL）的中断与恢复闭环**：节点在运行中调用 `interrupt(value)` 请求外部
输入 → 图挂起并把中断信息交还调用方 → 调用方用 `Command(resume=...)` 提交输入 →
**图从该节点的起点重跑**，节点在第二次执行时拿到 resume 值并继续跑完。

### 2. 背景与上下文

- **C17（中断原语）**：`interrupt(value)` 抛出可识别异常；结果含 `__interrupt__`
  （元素含 `.value` / `.id`）；用 `Command(resume=...)` 从**节点起点**重跑。
- **「从节点起点重跑」是本 Phase 最容易被实现错的语义**：常见错误实现是「从中断点
  继续」（相当于保存了局部变量），而 LangGraph 的语义是**整个节点函数从头再执行一遍**，
  节点内部靠 `interrupt()` 的返回值区分「首次执行」与「恢复执行」。
  → 因此节点函数的写法是：`answer = interrupt("approve?")`，首次执行时抛异常，
  恢复执行时 `interrupt()` 直接返回 resume 值。
- ✅ **「恢复必须依赖 checkpointer」已由发起者拍板（2026-11-05）**：恢复**必须**经由
  checkpointer 读取被中断处的状态（快照 + pending writes）并从节点起点重跑；
  **MUST NOT** 提供「不挂 checkpointer 也能恢复」的内存态旁路；未挂 checkpointer 时调用
  恢复**必须**抛明确异常。**理由**（发起者原话要点）：
  ① **内存态恢复不可靠**——LangGraph 的 MemorySaver 仅限**开发 / 调试**，不可用于生产；
     而 `interrupt` 的主场景是 **time travel**：可能隔了很长时间、甚至**电脑重启之后**，
     图状态仍须可恢复。
  ② **SQLite 是智能体开发的事实标准**——智能体是低并发应用，用户需要**开箱即用**
     （不配置额外中间件 / 数据库），故各大智能体都采用 SQLite；面对 SQLite 就**必须**
     像 LangGraph 那样采用 checkpointer。
  ③ 「用户第一次用 HITL 就得先建 saver」**不是负担，而是选择持久化中间件的过程，
     不能省略**——LangGraph 有多种 Saver；若开发者连 Saver 都不愿创建，那这套图运行时
     也就无从谈起。
  → **契约落点**：C17 已随之修订（Q8 §3.4.1 ④ / 立项书 §5.3.1 ④）；
  → **本 Phase 的依赖变化**：恢复路径依赖 L4 持久化层的 `Checkpointer` 协议——
    **ARCH-1 的方向不变**（L2 只依赖 L1 的协议，**不** import L4 实现）；
    协议已在 F2P1 冻结，本 Phase 只消费。
- freechain 的 HITL 能力依赖本原语（宪法原则 VII：freegraph 提供原语，
  freechain 提供 agent 装配）。

### 3. 用户场景

**P1 — 节点挂起并交还中断信息**
作为用户，我的审批节点调用 `interrupt("approve?")` 后，我希望图**停止执行**并把
「要审批什么」交给我，而不是抛一个看不懂的异常。

- **独立验收**：执行结果含 `__interrupt__` 键，元素有 `.value == "approve?"` 与 `.id`。

**P2 — 提交审批结果后图继续跑完**
作为用户，我拿到中断信息后用 `Command(resume="yes")` 提交审批结果，我希望图**继续执行
到结束**，且最终状态里能看到审批结果。

- **独立验收**：第二次 `invoke(Command(resume="yes"))` 后，结果为**完成态**（无
  `__interrupt__`），且状态包含 resume 值。

**P3 — 恢复时节点从头重跑**
作为实现者，我需要知道恢复时的节点是**重新执行**的，从而在节点里用 `interrupt()`
 的返回值做分支——这是 LangGraph 的既定语义。

- **独立验收**：节点内计数变量在恢复执行时可见「这是第 2 次进入节点」的证据
  （如节点写入一个自增计数）。

### 4. 功能需求

- **FR-001**：系统 MUST 提供 `interrupt(value)` 函数：被调用时抛出可识别的
  `GraphInterrupt`，携带 `value`。
- **FR-002**：中断发生时，执行结果 MUST 含 `__interrupt__` 键；其元素 MUST 具备
  `.value` 与 `.id` 两个可读属性（C17）。
- **FR-003**：系统 MUST 支持 `Command(resume=...)` 作为**恢复输入**；恢复后
  `interrupt(...)` MUST **返回** resume 值（而不是再次抛出中断）。
- **FR-004**：恢复 MUST **从中断节点起点重跑**（节点函数重新从头执行）。
- **FR-005**：恢复 MUST **依赖 checkpointer**——图被 `interrupt()` 挂起后，
  `Command(resume=...)` 的恢复**必须**经由 checkpointer 读取被中断处的状态（快照 +
  pending writes）并从节点起点重跑。**MUST NOT** 提供「不挂 checkpointer 也能恢复」的
  内存态旁路。
- **FR-005a**：编译产物**未挂** checkpointer 时，调用恢复（`invoke(Command(resume=...))`）
  **MUST** 抛**明确异常**（消息指明「恢复需要 checkpointer」），**MUST NOT** 静默降级为
  内存态恢复。
- **FR-006**：系统 MUST 定义「未提交的恢复值 / 未提供 resume 值」的明确行为
  （抛明确异常或重新挂起），并在 spec 中写死。
- **FR-007**：多个节点同时中断时，MUST 全部返回（与 F12P1 的收集语义一致）。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量。

### 5. 成功标准

- **SC-001**：中断后结果含 `__interrupt__`，元素 `.value` 与 `.id` 均可读（100%）。
- **SC-002**：`Command(resume=...)` 之后，图执行到结束态且状态含 resume 值。
- **SC-003**：恢复时节点函数**被重新完整执行**（可由节点内自增计数判定）。
- **SC-004**：中断前已产生的状态写入**不丢失**（挂起不是回滚）。
- **SC-005**：**恢复路径确实经由 checkpointer**——用「记录 checkpointer 调用」的桩可判定
  （恢复时 MUST 读到该 thread 的快照 + pending writes）；未挂 checkpointer 时恢复**抛明确异常**。
- **SC-006**：L2 **不 import** L4 的实现（只依赖 L1 冻结的 `Checkpointer` 协议）——
  导入图断言可判定。

### 6. 验收判据（= 立项书 §5.2 F10P1 小目标，逐条可判定）

> 小目标原文：HITL 中断/恢复闭环；从节点起点重跑

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | HITL 中断/恢复闭环 | 中断 → `Command(resume=)` → 跑到结束，状态含 resume 值 |
| A2 | **从节点起点重跑** | 节点内计数证明第二次进入节点是**重新执行** |
| A3 | `__interrupt__` 含 `.value` / `.id` | 断言（C17） |
| A4 | **恢复须挂 checkpointer** | ① 挂 checkpointer 的用例：恢复确实读到了快照 + pending writes；② 未挂 checkpointer 的用例：抛明确异常（非静默降级） |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `interrupt(value)` | 请求外部输入 | **C17** |
| `GraphInterrupt` | 可识别的中断异常 | C17 |
| `__interrupt__` | 执行结果中的中断集合 | C17 |
| `Command(resume=...)` | 恢复输入 | C16 / C17 |

> **口径提醒**：`Command` 的类型在 F1P1、`goto`/`update` 语义在 F9P1；
> 本 Phase 只补 `resume` 的运行期语义。

### 8. 边界（本 Phase 明确不做）

- 不实现 checkpointer 的**具体实现**（属 F14P1 `MemorySaver` / F15P1 `SqliteSaver`）——
  但**恢复路径 MUST 已经按「经由 checkpointer」实现**（消费 L1 冻结的 `Checkpointer`
  协议，见 FR-005）；本 Phase **不提供**任何内存态恢复旁路。
- 不实现静态中断点 `interrupt_before` / `interrupt_after`（属 F13P1）。
- 不实现 `recursion_limit`（属 F13P1）。
- 不实现 `Send`（属 F11P1）。
- 不实现 agent 层审批 UI / 通知（属 freechain）。
- 不实现 async（v2 范围）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**。
- **ARCH-1**：L2 只依赖 L1。
- **契约门禁**：中断/恢复 MUST NOT 破坏 C4 / C6 / C8。
- **人工门禁**：`harness/features/<feature>/manual-verification.md`。
- **证据门禁**：中断与恢复语义须标注源码行号（`langgraph/types.py:851+`）。

### 10. 交付物与后续

- **交付物**：`interrupt()` 函数、中断异常与 `__interrupt__` 结果结构、`resume` 恢复路径
  （含节点起点重跑）、单元测试 + 人工验证记录。
- **后续解锁**：**F13P1**（静态中断点 + `recursion_limit`，依赖 F10P1）→
  **F7P3**（`invoke` 对外 API）。
- **软断言联动**：`harness/demo/graph_core.py` 中「C17 `Command(resume=)` 从节点起点
  重跑并拿到 resume 值」当前是**软断言**（形态待 F14P1 拍板）；本 Phase 落地后，
  该断言**形态已定**——应在本 Phase 或 F14P1 结束时把它升级为硬断言（具体升级时机
  写进 spec 的验收判据）。

---

## 依据

- 立项书 §5.2（F10P1 行）、§5.3（C16 / C17）、§9.2（验收脚本集的软/硬断言约定）、
  §9.1（门禁）。
- 源码参照：`langgraph/types.py:851+`（`interrupt` 定义）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C17）。
- 验收脚本：`harness/demo/graph_core.py`（`case_interrupt_resume`）、
  `harness/demo/README.md`（软断言清单）。
