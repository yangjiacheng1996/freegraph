# B14F1 · Checkpointer 协议 + `MemorySaver`（快照 + pending writes 双层持久化）

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B14F1` |
> | 所属 功能块 | B14（Checkpointer 协议 + MemorySaver） |
> | 架构层 | L4 持久化层 |
> | 里程碑 | M3 可诊断（第 26 个） |
> | 前置依赖 | **B7F3** |
> | 规模 | 1,200 行（实现 560 / 测试 640）· 3 人日 |
> | 建议 short-name | `b14f1-checkpointer-memory-saver` |
> | MVP 必需（★） | 否（**位于关键路径上**） |

---

## 提示词正文

### 1. 目标

交付**检查点（checkpoint）能力的第一段**：把 C19 协议落成第一个可用实现
`MemorySaver`——在每个 super-step 结束时把**状态快照**与**待写入（pending writes）**
分别持久化，并提供按 `thread_id` 取回的能力。本 feature 的判定是：
**快照 + pending writes 双层持久化**。

### 2. 背景与上下文

- **C19（检查点接口）**：`checkpointer` 提供 `get_tuple` / `list` / `put` /
  `put_writes` / `delete_thread` / `get_next_version` 等方法（快照 + 历史）。
  协议已在 B2F1 冻结；本 feature 交付**实现**。
- **为什么是「双层」**：快照（state snapshot）与 pending writes（单个任务的写入）
  是**两种不同的数据**——快照用于「回到某一步看状态」，pending writes 用于
  「崩溃后重放未落地的写入」。LangGraph 同样区分这两层
  （`langgraph/checkpoint/base` + `memory` 1558 行）。
- **版本号语义**：`get_next_version` 递增 checkpoint 版本——版本号是「谁更新了哪个
  channel」的依据（触发判定依赖它，见 B7F1）。
- **形态待锁定**：`harness/demo/README.md` 列出「`MemorySaver` 的**模块路径**」是
  **未锁定的形态**，随 M3 各 feature 一同锁定。本 feature 正是锁定它的时点。
- ✅ **「interrupt 恢复必须依赖 checkpointer」已由发起者拍板（2026-11-05）**——不再是待锁定
  形态。**理由**（发起者原话要点）：① **内存态恢复不可靠**——LangGraph 的 MemorySaver
  仅限**开发 / 调试**，不可用于生产；而 `interrupt` 的主场景是 **time travel**（可能隔了
  很长时间、甚至**电脑重启之后**，图状态仍须可恢复）；② **SQLite 是智能体开发的事实标准**
  ——智能体是低并发应用，用户需要**开箱即用**（不配置额外中间件 / 数据库），故各大智能体
  都采用 SQLite；面对 SQLite 就**必须**像 LangGraph 那样采用 checkpointer；
  ③ 「用户第一次用 HITL 就得先建 saver」**不是负担，而是选择持久化中间件的过程，不能省略**
  ——LangGraph 有多种 Saver，若开发者连 Saver 都不愿创建，那这套图运行时也就无从谈起。
  → **对本 feature 的直接影响**：`MemorySaver` 从「可选项」变为**恢复路径的必需品**，
  定位明确为**开发 / 调试**（生产 / 长期场景由 B15F1 的 `SqliteSaver` 承担）。

- **承接条款（B12F1 → B14F1 · M2 / M3 · 跨进程 / 跨重启的多会话隔离）**：B12F1 已交付**并发执行
  内核**并**冻结**了跨 feature 的接口口径 ⇒ **本 feature MUST** 照它写：
  - **⚠️ 2026-11-12 修订（承 B12F1 · D-5 / V-7）**：**进程内**的隔离**已由 2026-11-12 P2-b
    在 L2 落地**（**每次运行从规格新建通道实例**）⇒ **实测**：同一份规格**连续两次** ⇒
    **不累积**；**并发两次** ⇒ **不串扰** ⇒ ⇒ **B12F1 已 NOT 把这条列为限制**（初版的
    「X-6 已知限制」**作废**）⇒ ⇒ 下面这条**跨进程 / 跨重启**的隔离**仍然归本 feature**
    （进程内的**门面级**验收归 **B7F2 / B7F3** · 下游承接 **D-4**）；
  - **进程内**的隔离由 **B7F2 / B7F3** 承担（编译产物持**规格**、每次 `invoke` **新建实例** ·
    下游承接 **D-4**）⇒ **跨进程 / 跨重启**的隔离 MUST 由**本 feature** 承担；
  - **本 feature 的义务**：MUST 保证「**同一 `thread_id`** 的连续调用」与「**不同 `thread_id`** 的
    并行调用」**状态互不干扰** ⇒ 会话状态按 `thread_id` 落在 checkpointer 上 ⇒ 与 **D-4** **互补**
    （一个管进程内、一个管跨进程）；
  - **B12F1 MUST NOT** 越界实现本条。
  该口径由 B12F1 的 `specs/b12f1-concurrency-errors/spec.md`（**FR-024** · **裁定 23（已作废）** ·
  下游承接 **D-5** · 回溯修订 **T-7**）落成。

- **承接条款（B12F1 → B14F1 · M3 · 「真异常 + 中断同现」时的中断留痕 · 2026-11-12 澄清轮 Q17）**：
  B12F1 已交付「同一 super-step 内**多个节点同时中断** ⇒ **完整收集** ⇒ **合并抛出**一个
  `GraphInterrupt`（载荷 = **元组**）」的**运行期语义**，并**冻结**了跨 feature 的接口口径 ⇒
  **本 feature MUST** 照它写：
  - **上游同款**：上游把中断元组写进 checkpoint 的 **pending writes**
    （`langgraph/pregel/_runner.py:588-591`）⇒ 即便**真异常**优先抛出（`_runner.py:687`），
    那批**待审批项也留了痕**（用户 `get_state()` 看得到）；
  - **freegraph v1 的现状**：**B12F1 在 M1**、checkpoint 的**实现**（`Checkpointer` 协议 +
    `MemorySaver`）在 **B14F1 / M3** ⇒ ⇒ B12F1 交付时内核**无处写 checkpoint** ⇒ 那批元组
    **丢弃** ⇒ ⇒ 这是**阶段性**差异（**不是**取舍），B12F1 已**如实登记**为 **DIFF**；
  - **本 feature 的义务**：**让中断元组随 pending writes 留痕** ⇒ ⇒ **该差异自动消解 ·
    回归上游同款** ⇒ ⇒ 本条**不是**「新增功能」，只是**上游本来就这样**；
  - **本 feature MUST NOT** 把这件事当成「新能力」来宣传；
  - **B12F1 MUST NOT** 为此**自创**留痕形态（在真异常上加**附注** / 落**调度状态字段**）⇒
    原则 XI ③「自研必须论证」⇒ 而此处**无理由**自创。
  该口径由 B12F1 的 `specs/b12f1-concurrency-errors/spec.md`（**FR-014** · **裁定 10** ·
  **SC-013** · 偏离登记 **X-4** 的**消解条件** · 下游承接 **D-6**）落成。

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

- **FR-001**：系统 MUST 实现 `MemorySaver`，满足 B2F1 冻结的 `Checkpointer` 协议
  （方法集：`get_tuple` / `list` / `put` / `put_writes` / `delete_thread` /
  `get_next_version`）。
- **FR-002**：系统 MUST 在每个 super-step 结束时写入**状态快照**（含 `values` /
  `next` / `config` / `metadata` / `created_at` / `tasks` / `interrupts` —
  `StateSnapshot` 字段，B1F1 冻结）。
- **FR-003**：系统 MUST 支持把**单个任务的写入**（pending writes）单独持久化，
  与快照分层存储。
- **FR-004**：系统 MUST 按 `thread_id` 隔离快照与写入。
- **FR-005**：系统 MUST 维护 checkpoint **版本号**（`get_next_version` 单调递增），
  且版本号语义 MUST 与触发判定所用的版本语义一致。
- **FR-006**：系统 MUST 支持 `delete_thread`（删除某会话的全部快照与写入）。
- **FR-007**：checkpointer MUST 可通过 `compile(checkpointer=...)` 注入
  （B7F2 已支持该关键字）；未注入时行为 MUST 与注入时**语义一致**（不落盘）。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量；
  MUST NOT 有任何出站。

### 5. 成功标准

- **SC-001**：快照数量 == super-step 轮数 + 1（可判定）。
- **SC-002**：pending writes 写入后可取回（内容一致）。
- **SC-003**：`thread-1` / `thread-2` 的数据完全隔离。
- **SC-004**：版本号单调递增，且与触发判定使用的版本一致（跨 feature 一致性断言）。
- **SC-005**：注入 checkpointer 前后，图的**执行结果**一致（只影响持久化，不影响语义）。

### 6. 验收判据（= 立项书 §5.2 B14F1 小目标，逐条可判定）

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
| `MemorySaver` | 内存实现（本 feature） | C19 |
| `StateSnapshot` | 快照载体（B1F1 冻结） | C19 / DF3 |
| `RunConfig.thread_id` | 会话标识 | C22 |

> **口径提醒**：`StateSnapshot` 的字段（`values` / `next` / `config` / `metadata` /
> `created_at` / `tasks` / `interrupts`）在 B1F1 冻结；`get_state` / `get_state_history`
> 的**对外方法**属 B15F1。

### 8. 边界（本 feature 明确不做）

- 不实现 `SqliteSaver`（属 B15F1）——本 feature 只做内存实现。
- 不实现 `get_state` / `get_state_history` 的对外方法（属 B15F1）。
- 不实现 `update_state` 与时间旅行回放（属 B16F1）。
- 不实现 `Store` / `MemoryStore`（**B17 已砍，2026-11-05**——`Store` 是**跨会话 / 跨图**
  能力，而 freegraph 的定位是**通用图框架**（智能体 / RPA 自动化 / 脚本编排 / 在一定程度
  上替代 `main` 函数 / 可视化工作流编排），共同前提是「**图 = 一个进程**」→ 复杂且违背
  初衷。契约 **C20 仍冻结**（freechain 的设计输入不受影响），实现后补（v2））。
- 不实现 Postgres 后端（v2 范围，未排 feature）。
- 不实现跨进程 / 跨机共享 thread（v2 范围——这是 Postgres 的存在理由）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`；零第三方依赖。
- **零出站 / 零环境变量**。
- **ARCH-1 / ARCH-3**：L4 只依赖 L1（**不得** import L5 可观测层——L2–L5 之间不横向依赖）。
- **契约门禁**：MUST NOT 改变图执行的语义（注入 checkpointer 只影响持久化）。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：与 LangGraph checkpoint 语义的对应须标注源码行号
  （`langgraph/checkpoint/base` + `langgraph/checkpoint/memory`）。

### 10. 交付物与后续

- **交付物**：`MemorySaver` 实现（快照 + pending writes + 版本号 + thread 隔离 +
  `delete_thread`）、单元测试 + 人工验证记录。
- **形态锁定（本 feature 必办）**：锁定 `MemorySaver` 的**模块路径**与
  `compile(checkpointer=...)` 的注入用法，并更新 `harness/demo/README.md` 的
  「待锁定形态」清单（移除对应条目）。
- ✅ **「interrupt 恢复必须依赖 checkpointer」已由发起者拍板（2026-11-05）** → 本 feature 的
  `MemorySaver` 从「可选项」升级为**恢复路径的必需品**：
  - `MemorySaver` 的定位明确为**开发 / 调试**（与 LangGraph 一致）：它不适用于生产，
    但**足以支撑本地开发与单测**；生产 / 长期场景由 **B15F1 的 `SqliteSaver`** 承担；
  - **理由**（发起者原话要点）：① **内存态恢复不可靠**——LangGraph 的 MemorySaver 仅限
    开发 / 调试，而 `interrupt` 的主场景是 time travel（跨长时间、跨重启仍须可恢复）；
    ② **SQLite 是智能体开发的事实标准**（低并发 + 开箱即用），故必须采用 checkpointer；
    ③ 「用户第一次用 HITL 就得先建 saver」是**选择持久化中间件的过程，不能省略**；
  - **本 feature 的义务**：`MemorySaver` MUST 满足 C19 协议，**并能被恢复路径直接消费**
    （`get_tuple` 取回快照 + `put_writes` 取回 pending writes）。
- **⚠️ 软断言升级（本 feature 的强制动作）**：`harness/demo/README.md` 的
  「`interrupt` 恢复是否依赖 checkpointer」软断言**形态已由 2026-11-05 的决策锁定**，
  **本 feature MUST 把它升级为硬断言**——即在 `harness/demo/graph_core.py` 的
  `case_interrupt_resume` 中**挂上真实的 `MemorySaver`**（模块路径由本 feature 锁定），
  并把 `soft(...)` 改为 `check(...)`：断言「从节点起点重跑并拿到 resume 值」**失败即 FAIL**。
- **本 feature 必须锁定的第二个形态**：`MemorySaver` 的**模块路径**
  （`harness/demo/README.md` 的待锁定清单之一）——它同时是「`graph_core.py` 升级硬断言」
  的前置。
- **后续解锁**：**B15F1**（`SqliteSaver` + `get_state` / `get_state_history`）→
  **B16F1**（`update_state` + 时间旅行）→ **B21F1**（OTLP 导出）。
- **关键路径**：本 feature 位于**关键路径**上（15 个 feature / 45 天），
  紧接其后的 B15F1 / B16F1 / B24F1 / B25F1 构成到交付终点的尾链。

---

## 依据

- 立项书 §5.2（B14F1 行）、§5.3（C19 / C22）、§5.4（P2 `Checkpointer` 协议 +
  DF3 `StateSnapshot`）、§6.3（关键路径）、§9.1（门禁）。
- 源码参照：`langgraph/checkpoint/base` + `langgraph/checkpoint/memory`（1558 行）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C19）。
- 验收脚本约定：`harness/demo/README.md`（M3 待锁定形态清单 + 软断言清单）。
- 架构纪律：`harness/prompts/guide.md` §2.3 / §3.5（L4 只依赖 L1）。
