# B15F1 · `SqliteSaver` + `get_state` / `get_state_history`

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B15F1` |
> | 所属 功能块 | B15（`SqliteSaver` + `get_state_history`） |
> | 架构层 | L4 持久化层 |
> | 里程碑 | M3 可诊断（第 27 个） |
> | 前置依赖 | **B14F1** |
> | 规模 | 1,240 行（实现 620 / 测试 620）· 3 人日 |
> | 建议 short-name | `b15f1-sqlite-saver-state-history` |
> | MVP 必需（★） | 否（**位于关键路径上**） |

---

## 提示词正文

### 1. 目标

交付**磁盘持久化**与**状态查询**：把 B14F1 的 `MemorySaver` 换成可落盘的
`SqliteSaver`（标准库 `sqlite3`，零第三方依赖），并实现对外的
`get_state()` 与 `get_state_history()`——让用户能「看当前状态」与「枚举历史快照」。
本 feature 的判定是：**历史快照可枚举**。

### 2. 背景与上下文

- **三件套之第 ③ 件**（立项书 §5.6）：③ **状态快照 + checkpoint 历史 + 回放入口**。
  本 feature 交付「快照 + 历史」的对外读取面，「回放入口」属 B16F1。
- **为什么用 SQLite**：**唯一免第三方依赖的持久化选项**（`sqlite3` 属标准库）。
  Postgres 后端属 v2（且驱动 `psycopg` 是 LGPL-3.0，不在许可证白名单内）。
- **SQLite 是智能体开发的事实标准**（发起者 2026-11-05 决策的配套理由）：智能体是
  **低并发**应用，用户需要**开箱即用**（不配置额外中间件 / 数据库），故各大智能体都
  采用 SQLite。→ 因此 `SqliteSaver` 是 freegraph **面向真实使用的默认推荐后端**，
  而 B14F1 的 `MemorySaver` 定位为**开发 / 调试**（与 LangGraph 一致：memory saver
  仅限开发调试，不可用于生产）。
- **与「恢复必须挂 checkpointer」的决策配套**（2026-11-05）：`interrupt` 恢复与
  time travel **必须**经由 checkpointer（内存态恢复不可靠；time travel 须跨长时间 /
  跨重启可恢复）→ 用户「第一次用 HITL 就得先建 saver」，而**开箱即用的 saver 就是
  `SqliteSaver`**（零第三方依赖、零配置）。**这一条是本 feature 存在意义的一部分**：
  它让「挂 saver」这一步的成本接近于零，同时保留生产级语义。
- **与 LangGraph 行为对齐**：LangGraph 的 `get_state_history()` 返回按
  `checkpoint_id` 倒序的快照序列（实测 `HISTORY: 6`）；freegraph 的排序语义 MUST
  在 spec 中写死并与之一致。
- **Windows 文件锁差异**（立项书 §3.5）：SQLite 后端在 Windows 上存在文件锁差异
  → **本 feature 必须在 Windows CI 上跑并发写用例**。
- **`StateSnapshot` 组装**：`get_state` / `get_state_history` 返回的是
  `StateSnapshot`（B1F1 冻结的字段集），不是裸 dict。

### 3. 用户场景

**P1 — 进程重启后状态还在**
作为用户，我的应用重启后，希望上次的运行状态**能从磁盘取回**（而不是丢失）。

- **独立验收**：写入 → 新建 saver 实例 → 快照仍可取回。

**P2 — 看当前状态**
作为用户，我希望随时查看某会话「现在停在哪一步、下一步要干什么」。

- **独立验收**：`get_state` 返回的 `StateSnapshot` 含 `values` / `next` / `config` 等。

**P3 — 枚举历史快照做时间旅行**
作为用户，我希望能列出这次会话的全部历史快照，从而挑一个点回放。

- **独立验收**：`get_state_history` 返回数量与写入轮数一致，且顺序可判定。

**P4 — 删除会话数据**
作为用户，我希望能删掉某个会话的全部持久化数据。

- **独立验收**：`delete_thread` 后该 thread 的快照不可见。

### 4. 功能需求

- **FR-001**：系统 MUST 实现 `SqliteSaver`，满足 B14F1 / B2F1 的 `Checkpointer` 协议。
- **FR-002**：`SqliteSaver` MUST 只使用**标准库 `sqlite3`**，MUST NOT 引入第三方依赖。
- **FR-003**：系统 MUST 提供 `get_state(...)`（当前状态）与 `get_state_history(...)`
  （历史快照序列）两个对外方法，返回 `StateSnapshot` 对象。
- **FR-004**：历史快照的**排序语义 MUST 写死**（默认按时间倒序 / 或按 checkpoint
  版本倒序；二者择一，与 LangGraph 行为对齐）。
- **FR-005**：`SqliteSaver` MUST 支持 `delete_thread` 语义（来自协议）。
- **FR-006**：系统 MUST 处理 SQLite 的**并发访问**（同进程多线程；Windows 文件锁差异
  MUST 有专门用例）。
- **FR-007**：持久化失败（磁盘满 / 权限不足）MUST 有明确行为（抛明确异常），
  且 MUST 在 spec 中写死。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量；
  MUST NOT 有任何出站。

### 5. 成功标准

- **SC-001**：历史快照**可枚举**（数量与轮数一致、顺序可判定）。
- **SC-002**：`get_state` 返回 `StateSnapshot`，字段完整（`values` / `next` / `config` /
  `metadata` / `created_at` / `tasks` / `interrupts`）。
- **SC-003**：跨进程 / 跨实例持久化生效（新实例可取回旧快照）。
- **SC-004**：Windows CI 上的并发写用例通过（无 `database is locked` 异常泄漏）。
- **SC-005**：freegraph 运行时依赖闭包**仍为空集**（零第三方运行时依赖）。

### 6. 验收判据（= 立项书 §5.2 B15F1 小目标，逐条可判定）

> 小目标原文：历史快照可枚举

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 历史快照可枚举 | `get_state_history` 数量与顺序断言 |
| A2 | `get_state` 可用 | 返回 `StateSnapshot` 且字段完整 |
| A3 | 磁盘持久化生效 | 跨实例取回用例 |
| A4 | Windows 并发写通过 | Windows CI 任务 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `SqliteSaver` | 磁盘持久化实现 | **C19** |
| `get_state()` / `get_state_history()` | 对外状态读取 | C19 |
| `StateSnapshot` | 快照载体 | C19 / DF3 |
| `RunConfig.thread_id` | 会话标识 | C22 |

> **口径提醒**：C19 的协议方法集在 B2F1 冻结；`get_state` / `get_state_history` 的
> **对外调用形态**（参数是 `thread_id` 字符串还是 `RunConfig`）MUST 在本 feature 锁定
> 并写死。

### 8. 边界（本 feature 明确不做）

- 不实现 `update_state` 与时间旅行回放（属 B16F1）。
- 不实现 `Store` / `MemoryStore`（**B17 已砍，2026-11-05**——跨会话 / 跨图能力，
  与「图 = 一个进程」的定位不符；契约 C20 仍冻结，实现后补 v2）。
- 不实现 Postgres 后端（v2 范围）。
- 不实现「进程崩溃后自动恢复」的完整语义（属 B16F1 的组合能力）。
- 不实现 trace 存储（属 B20F1 / B20F2）——**checkpoint 与 trace 是两套东西**
  （前者管状态，后者管观测）。
- 不实现 async（v2 范围）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：零第三方依赖（`sqlite3` 属标准库）。
- **零出站 / 零环境变量**。
- **ARCH-1**：L4 只依赖 L1；MUST NOT import L5。
- **契约门禁**：MUST NOT 改变图执行语义。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：排序语义与 LangGraph 的对应须标注实测依据（`HISTORY: 6`）。

### 10. 交付物与后续

- **交付物**：`SqliteSaver`（含 schema、并发处理）、`get_state` /
  `get_state_history`（含 `StateSnapshot` 组装）、跨平台测试（含 Windows 并发写）
  + 人工验证记录。
- **后续解锁**：**B16F1**（`update_state` + 时间旅行回放）→ **B24F1**（打包分发）。
- **风险提示**：SQLite 的 **Windows 文件锁**与**写事务**语义是本 feature 最可能返工
  的点（立项书 §3.5 已点名）。spec 阶段应把「并发写 + 查询」的用例写成**跨平台**
  验收项，而不是只在 Linux 上跑。

---

## 依据

- 立项书 §3.5（支持矩阵 · Windows 文件锁差异）、§5.2（B15F1 行）、§5.3（C19）、
  §5.4（DF3 `StateSnapshot`）、§5.6（三件套之 ③）、§6.3（关键路径）、§9.1（门禁）。
- 源码参照：`langgraph/checkpoint/sqlite`（645 行）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C19）。
- 架构纪律：`harness/prompts/guide.md` §3.5（L4 只依赖 L1 · 持久化层不得 import
  可观测层）。
