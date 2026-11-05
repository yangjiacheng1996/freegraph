# F14P1 · Checkpointer 协议 + `MemorySaver`（快照 + pending writes 双层持久化）

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | Phase ID | `F14P1` |
> | 所属 Feature | F14（Checkpointer 协议 + MemorySaver） |
> | 架构层 | L4 持久化层 |
> | 里程碑 | M3 可诊断（第 26 个） |
> | 前置依赖 | **F7P3** |
> | 规模 | 1,200 行（实现 560 / 测试 640）· 3 人日 |
> | 建议 short-name | `p14-checkpointer-memory-saver` |
> | MVP 必需（★） | 否（**位于关键路径上**） |

---

## 提示词正文

### 1. 目标

交付**检查点（checkpoint）能力的第一段**：把 C19 协议落成第一个可用实现
`MemorySaver`——在每个 super-step 结束时把**状态快照**与**待写入（pending writes）**
分别持久化，并提供按 `thread_id` 取回的能力。本 Phase 的判定是：
**快照 + pending writes 双层持久化**。

### 2. 背景与上下文

- **C19（检查点接口）**：`checkpointer` 提供 `get_tuple` / `list` / `put` /
  `put_writes` / `delete_thread` / `get_next_version` 等方法（快照 + 历史）。
  协议已在 F2P1 冻结；本 Phase 交付**实现**。
- **为什么是「双层」**：快照（state snapshot）与 pending writes（单个任务的写入）
  是**两种不同的数据**——快照用于「回到某一步看状态」，pending writes 用于
  「崩溃后重放未落地的写入」。LangGraph 同样区分这两层
  （`langgraph/checkpoint/base` + `memory` 1558 行）。
- **版本号语义**：`get_next_version` 递增 checkpoint 版本——版本号是「谁更新了哪个
  channel」的依据（触发判定依赖它，见 F7P1）。
- **形态待锁定**：`harness/demo/README.md` 列出「`MemorySaver` 的**模块路径**」是
  **未锁定的形态**，随 M3 各 Phase 一同锁定。本 Phase 正是锁定它的时点。
- ✅ **「interrupt 恢复必须依赖 checkpointer」已由发起者拍板（2026-11-05）**——不再是待锁定
  形态。**理由**（发起者原话要点）：① **内存态恢复不可靠**——LangGraph 的 MemorySaver
  仅限**开发 / 调试**，不可用于生产；而 `interrupt` 的主场景是 **time travel**（可能隔了
  很长时间、甚至**电脑重启之后**，图状态仍须可恢复）；② **SQLite 是智能体开发的事实标准**
  ——智能体是低并发应用，用户需要**开箱即用**（不配置额外中间件 / 数据库），故各大智能体
  都采用 SQLite；面对 SQLite 就**必须**像 LangGraph 那样采用 checkpointer；
  ③ 「用户第一次用 HITL 就得先建 saver」**不是负担，而是选择持久化中间件的过程，不能省略**
  ——LangGraph 有多种 Saver，若开发者连 Saver 都不愿创建，那这套图运行时也就无从谈起。
  → **对本 Phase 的直接影响**：`MemorySaver` 从「可选项」变为**恢复路径的必需品**，
  定位明确为**开发 / 调试**（生产 / 长期场景由 F15P1 的 `SqliteSaver` 承担）。

### 3. 用户场景

**P1 — 每一步的状态都被记下来了**
作为用户，我跑完一张图后，希望能看到它在**每一步**的状态快照，从而复盘状态如何演进。

- **独立验收**：运行结束后，历史快照数量 == 执行的 super-step 轮数 + 1（含初始）。

**P2 — 未落地的写入也被记下来了**
作为实现者，我需要 pending writes 被单独保存，以便崩溃后能重放。

- **独立验收**：`put_writes` 写入的内容可被取回。

**P3 — 按 thread 隔离不同会话**
作为用户，我同时跑两个会话，希望它们的 checkpoint **互不干扰**。

- **独立验收**：`thread-1` 与 `thread-2` 的快照互不可见。

### 4. 功能需求

- **FR-001**：系统 MUST 实现 `MemorySaver`，满足 F2P1 冻结的 `Checkpointer` 协议
  （方法集：`get_tuple` / `list` / `put` / `put_writes` / `delete_thread` /
  `get_next_version`）。
- **FR-002**：系统 MUST 在每个 super-step 结束时写入**状态快照**（含 `values` /
  `next` / `config` / `metadata` / `created_at` / `tasks` / `interrupts` —
  `StateSnapshot` 字段，F1P1 冻结）。
- **FR-003**：系统 MUST 支持把**单个任务的写入**（pending writes）单独持久化，
  与快照分层存储。
- **FR-004**：系统 MUST 按 `thread_id` 隔离快照与写入。
- **FR-005**：系统 MUST 维护 checkpoint **版本号**（`get_next_version` 单调递增），
  且版本号语义 MUST 与触发判定所用的版本语义一致。
- **FR-006**：系统 MUST 支持 `delete_thread`（删除某会话的全部快照与写入）。
- **FR-007**：checkpointer MUST 可通过 `compile(checkpointer=...)` 注入
  （F7P2 已支持该关键字）；未注入时行为 MUST 与注入时**语义一致**（不落盘）。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量；
  MUST NOT 有任何出站。

### 5. 成功标准

- **SC-001**：快照数量 == super-step 轮数 + 1（可判定）。
- **SC-002**：pending writes 写入后可取回（内容一致）。
- **SC-003**：`thread-1` / `thread-2` 的数据完全隔离。
- **SC-004**：版本号单调递增，且与触发判定使用的版本一致（跨 Phase 一致性断言）。
- **SC-005**：注入 checkpointer 前后，图的**执行结果**一致（只影响持久化，不影响语义）。

### 6. 验收判据（= 立项书 §5.2 F14P1 小目标，逐条可判定）

> 小目标原文：快照 + pending writes 双层持久化

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 快照持久化 | 快照数量 == 轮数 + 1；`values` 内容可校验 |
| A2 | pending writes 持久化 | 写入后可取回（内容一致） |
| A3 | 按 thread 隔离 | 两 thread 互不可见 |
| A4 | `MemorySaver` 满足 `Checkpointer` 协议 | 结构化子类型检查 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `Checkpointer`（协议） | 快照 + 历史持久化接口 | **C19** |
| `MemorySaver` | 内存实现（本 Phase） | C19 |
| `StateSnapshot` | 快照载体（F1P1 冻结） | C19 / DF3 |
| `RunConfig.thread_id` | 会话标识 | C22 |

> **口径提醒**：`StateSnapshot` 的字段（`values` / `next` / `config` / `metadata` /
> `created_at` / `tasks` / `interrupts`）在 F1P1 冻结；`get_state` / `get_state_history`
> 的**对外方法**属 F15P1。

### 8. 边界（本 Phase 明确不做）

- 不实现 `SqliteSaver`（属 F15P1）——本 Phase 只做内存实现。
- 不实现 `get_state` / `get_state_history` 的对外方法（属 F15P1）。
- 不实现 `update_state` 与时间旅行回放（属 F16P1）。
- 不实现 `Store` / `MemoryStore`（**F17 已砍，2026-11-05**——`Store` 是**跨会话 / 跨图**
  能力，而 freegraph 的定位是**通用图框架**（智能体 / RPA 自动化 / 脚本编排 / 在一定程度
  上替代 `main` 函数 / 可视化工作流编排），共同前提是「**图 = 一个进程**」→ 复杂且违背
  初衷。契约 **C20 仍冻结**（freechain 的设计输入不受影响），实现后补（v2））。
- 不实现 Postgres 后端（v2 范围，未排 Phase）。
- 不实现跨进程 / 跨机共享 thread（v2 范围——这是 Postgres 的存在理由）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`；零第三方依赖。
- **零出站 / 零环境变量**。
- **ARCH-1 / ARCH-3**：L4 只依赖 L1（**不得** import L5 可观测层——L2–L5 之间不横向依赖）。
- **契约门禁**：MUST NOT 改变图执行的语义（注入 checkpointer 只影响持久化）。
- **人工门禁**：`harness/features/<feature>/manual-verification.md`。
- **证据门禁**：与 LangGraph checkpoint 语义的对应须标注源码行号
  （`langgraph/checkpoint/base` + `langgraph/checkpoint/memory`）。

### 10. 交付物与后续

- **交付物**：`MemorySaver` 实现（快照 + pending writes + 版本号 + thread 隔离 +
  `delete_thread`）、单元测试 + 人工验证记录。
- **形态锁定（本 Phase 必办）**：锁定 `MemorySaver` 的**模块路径**与
  `compile(checkpointer=...)` 的注入用法，并更新 `harness/demo/README.md` 的
  「待锁定形态」清单（移除对应条目）。
- ✅ **「interrupt 恢复必须依赖 checkpointer」已由发起者拍板（2026-11-05）** → 本 Phase 的
  `MemorySaver` 从「可选项」升级为**恢复路径的必需品**：
  - `MemorySaver` 的定位明确为**开发 / 调试**（与 LangGraph 一致）：它不适用于生产，
    但**足以支撑本地开发与单测**；生产 / 长期场景由 **F15P1 的 `SqliteSaver`** 承担；
  - **理由**（发起者原话要点）：① **内存态恢复不可靠**——LangGraph 的 MemorySaver 仅限
    开发 / 调试，而 `interrupt` 的主场景是 time travel（跨长时间、跨重启仍须可恢复）；
    ② **SQLite 是智能体开发的事实标准**（低并发 + 开箱即用），故必须采用 checkpointer；
    ③ 「用户第一次用 HITL 就得先建 saver」是**选择持久化中间件的过程，不能省略**；
  - **本 Phase 的义务**：`MemorySaver` MUST 满足 C19 协议，**并能被恢复路径直接消费**
    （`get_tuple` 取回快照 + `put_writes` 取回 pending writes）。
- **⚠️ 软断言升级（本 Phase 的强制动作）**：`harness/demo/README.md` 的
  「`interrupt` 恢复是否依赖 checkpointer」软断言**形态已由 2026-11-05 的决策锁定**，
  **本 Phase MUST 把它升级为硬断言**——即在 `harness/demo/graph_core.py` 的
  `case_interrupt_resume` 中**挂上真实的 `MemorySaver`**（模块路径由本 Phase 锁定），
  并把 `soft(...)` 改为 `check(...)`：断言「从节点起点重跑并拿到 resume 值」**失败即 FAIL**。
- **本 Phase 必须锁定的第二个形态**：`MemorySaver` 的**模块路径**
  （`harness/demo/README.md` 的待锁定清单之一）——它同时是「`graph_core.py` 升级硬断言」
  的前置。
- **后续解锁**：**F15P1**（`SqliteSaver` + `get_state` / `get_state_history`）→
  **F16P1**（`update_state` + 时间旅行）→ **F21P1**（OTLP 导出）。
- **关键路径**：本 Phase 位于**关键路径**上（15 个 Phase / 45 天），
  紧接其后的 F15P1 / F16P1 / F24P1 / F25P1 构成到交付终点的尾链。

---

## 依据

- 立项书 §5.2（F14P1 行）、§5.3（C19 / C22）、§5.4（P2 `Checkpointer` 协议 +
  DF3 `StateSnapshot`）、§6.3（关键路径）、§9.1（门禁）。
- 源码参照：`langgraph/checkpoint/base` + `langgraph/checkpoint/memory`（1558 行）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C19）。
- 验收脚本约定：`harness/demo/README.md`（M3 待锁定形态清单 + 软断言清单）。
- 架构纪律：`harness/prompts/guide.md` §2.3 / §3.5（L4 只依赖 L1）。
