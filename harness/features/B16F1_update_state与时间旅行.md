# B16F1 · `update_state` + 时间旅行回放

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B16F1` |
> | 所属 功能块 | B16（`update_state` + 时间旅行回放） |
> | 架构层 | L4 持久化层 |
> | 里程碑 | M3 可诊断（第 28 个） |
> | 前置依赖 | **B15F1** |
> | 规模 | 1,040 行（实现 480 / 测试 560）· 3 人日 |
> | 建议 short-name | `b16f1-update-state-time-travel` |
> | MVP 必需（★） | 否（**位于关键路径上 · 三件套之 ③ 的完成态**） |

---

## 提示词正文

### 1. 目标

交付**时间旅行**：用户可以**从任意历史 checkpoint 重放**，也可以**分叉**——
基于某个历史快照修改状态后重新继续跑。本 feature 的判定是：
**可从历史 checkpoint 重放**。

### 2. 背景与上下文

- **三件套之第 ③ 件的完成态**：③ 状态快照 + checkpoint 历史 + **回放入口**。
  前两段已在 B14F1 / B15F1 交付，本 feature 补上「回放入口」。
- **用户场景**（立项书 §5.8.2 第 5 项）：从任意 checkpoint 重放 / 分叉——
  **复现 bug、试另一条分支**。
- **与官方 Studio 的差分判定**（立项书 §4.2 S7 差分表）：
  - freegraph v1：`update_state()` → **有**；
  - Agent Chat UI（MIT）：state forking → **有**（可借鉴，但**不计入独占面**）；
  - LangSmith Studio → **有**。
  → 时间旅行**不是** freegraph 的独占面，但**必须交付**（否则 v1 的四类诊断能力
  缺一类，违反宪法原则 IV）。
- **实现参考**：LangGraph 的 `update_state` + time-travel 机制
  （`harness/docs/oss/python/langgraph/use-time-travel.md`）。
- **形态待锁定**：`harness/demo/README.md` 列出「`update_state(...)` 的**签名**」是
  **未锁定的形态**，随 M3 各 feature 一同锁定。本 feature 正是锁定它的时点。

### 3. 用户场景

**P1 — 从历史某一步重放**
作为用户，我跑到第 3 步时结果不对，希望**回到第 2 步的状态重新跑一遍**。

- **独立验收**：指定历史 checkpoint → 重新执行 → 结果与「当时的状态 + 后续逻辑」
  一致。

**P2 — 改状态再继续（分叉）**
作为用户，我回到第 2 步，把某个字段改成我想要的值再继续，得到一条**新分支**。

- **独立验收**：`update_state` 写入的值生效，且**不破坏**原历史快照。

**P3 — 重放不产生历史污染**
作为用户，我重放了很多次，希望原有 checkpoint 历史**仍然完整可枚举**。

- **独立验收**：重放后 `get_state_history` 仍包含全部原有快照。

### 4. 功能需求

- **FR-001**：系统 MUST 提供 `update_state(...)`（对外调用形态 MUST 在本 feature 锁定
  并写死），用于基于某个历史 checkpoint **修改状态**。
- **FR-002**：系统 MUST 支持**从任意历史 checkpoint 重放**（以该快照为起点继续执行）。
- **FR-003**：重放 / 分叉 MUST **不破坏**原有历史快照（原快照仍可取回）。
- **FR-004**：分叉产生的新状态 MUST 走**与普通写入相同的合并语义**（归约器 / 覆盖规则
  一致，C6）。
- **FR-005**：系统 MUST 定义「重放的起点不存在 / thread 不存在」时的明确行为
  （抛明确异常）。
- **FR-006**：系统 MUST 支持**中断恢复**与时间旅行的组合（从中断点的 checkpoint
  重放，`Command(resume=...)` 语义保持可用）。
- **FR-007**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量；
  MUST NOT 有任何出站。

### 5. 成功标准

- **SC-001**：从任意历史 checkpoint **可重放**（各历史点各一例）。
- **SC-002**：分叉后原历史快照**完整可枚举**（数量与内容不变）。
- **SC-003**：`update_state` 的写入按归约器 / 覆盖规则合并（与 C6 一致）。
- **SC-004**：起点不存在时抛出明确异常（可由异常类型判定）。
- **SC-005**：零出站、零环境变量读取。

### 6. 验收判据（= 立项书 §5.2 B16F1 小目标，逐条可判定）

> 小目标原文：可从历史 checkpoint 重放

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 可从历史 checkpoint 重放 | 历史点重放用例（多个历史点各一例） |
| A2 | 分叉不污染原历史 | 重放后历史快照数量与内容不变 |
| A3 | `update_state` 合并语义正确 | 归约器 / 覆盖两例 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `update_state()` | 基于历史 checkpoint 修改状态 | **C19** / C16 |
| 重放（time-travel） | 从历史 checkpoint 继续执行 | C19 |
| `Command(resume=...)` | 与中断恢复的组合 | C16 / C17 |

> **口径提醒**：C19 是「检查点接口」的契约条目；时间旅行的**对外方法名与签名**
> 属本 feature 锁定的形态（此前章程未逐字规定）。

### 8. 边界（本 feature 明确不做）

- 不实现 `Store` / `MemoryStore`（**B17 已砍，2026-11-05**——跨会话 / 跨图能力，
  与「图 = 一个进程」的定位不符；契约 C20 仍冻结，实现后补 v2）。
- 不实现 Postgres 后端（v2 范围）。
- 不实现前端「时间旅行」UI（v2 / B26）——但**回放 API 必须已为 UI 预留**。
- 不实现「并行分支 / 多分支树」的完整语义（v1 只保线性重放 + 单次分叉）。
- 不实现 trace 存储与查询（属 B20F1 / B20F2）——checkpoint 与 trace 是两套东西。
- 不实现 async（v2 范围）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**。
- **ARCH-1**：L4 只依赖 L1；MUST NOT import L5。
- **契约门禁**：MUST NOT 破坏 C4 / C6 / C8 / C16 / C17。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：与 LangGraph time-travel 语义的对应须标注来源
  （`harness/docs/oss/python/langgraph/use-time-travel.md`）。

### 10. 交付物与后续

- **交付物**：`update_state(...)`（签名锁定）、历史 checkpoint 重放、分叉、
  单元测试 + 人工验证记录。
- **形态锁定（本 feature 必办）**：锁定 `update_state(...)` 的签名，
  并更新 `harness/demo/README.md` 的「待锁定形态」清单（移除对应条目）。
- **后续解锁**：**B21F1**（OTLP 导出）→
  **B24F1**（打包分发，依赖 B23F1 + B16F1）。
- **三件套达成**：本 feature 完成后，v1 可视化三件套**全部交付**——
  ① 图视图（B22F1）、② trace 时间线 / 详情（B20F1 / B20F2）、
  ③ 状态快照 + checkpoint 历史 + 回放入口（B14F1 / B15F1 / **B16F1**）；
  加上中断 / 恢复（B10F1）→ **四类诊断能力（trace / state / interrupt / time-travel）
  全部具备最小可用实现**（宪法原则 IV 的 v1 交付要求）。
- **风险提示**：「重放」与「分叉」在实现上容易互相污染（分叉写回原 thread 的历史）。
  spec 阶段应把「分叉后原历史完整」写成**独立**的验收场景。

---

## 依据

- 立项书 §4.2（S7 差分表 · time-travel 一行）、§5.2（B16F1 行）、§5.3（C19 / C16 /
  C17）、§5.6（三件套）、§5.8.1（可视化 12 项之「状态 · 回放与分叉」）、
  §5.8.2（第 5 项）、§6.3（关键路径）、§9.1（门禁）。
- 官方文档镜像：`harness/docs/oss/python/langgraph/use-time-travel.md`。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C19）。
- 验收脚本约定：`harness/demo/README.md`（M3 待锁定形态清单）。
- 宪法 `.specify/memory/constitution.md`：原则 IV（trace / state / interrupt /
  time-travel 四类能力 MUST 有最小可用实现）。
