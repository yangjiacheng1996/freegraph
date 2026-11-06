# B9F1 · `Command` 原语（`goto` / `update` + `Command.PARENT`）

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B9F1` |
> | 所属 功能块 | B9（`Command`） |
> | 架构层 | L2 执行内核层 |
> | 里程碑 | M1 运行时内核（第 9 个） |
> | 前置依赖 | **B7F1** |
> | 规模 | 880 行（实现 420 / 测试 460）· 3 人日 |
> | 建议 short-name | `b9f1-command-primitive` |
> | MVP 必需（★） | 否（**位于关键路径上**） |

---

## 提示词正文

### 1. 目标

交付 `Command` 原语的**运行期语义**：节点可以返回一个 `Command`，同时表达
「**跳转到哪个节点**」与「**更新哪些状态**」两件事；并支持 `Command.PARENT`
（向父图跳转）。本 feature 的判定是：**跳转与状态更新必须同时生效**。

### 2. 背景与上下文

- `Command` 是 LangGraph 首创但**语义通用**的原语（Q8 §3.4 标注为「通用语义」）：
  `Command(goto=..., update=..., resume=...)`。freegraph 提供**自有**实现，不复用任何
  LangChain 类型。
- `Command` 是 freechain 做 HITL（人工介入）的基础能力之一（宪法原则 VII 把 HITL 依赖
  交给 freechain，但原语由 freegraph 提供）。
- `resume` 字段的类型已在 B1F1 冻结（契约层），其**运行期行为**在 B10F1（中断恢复）
  才实现——本 feature 负责 `goto` / `update` 两条语义。
- `Command.PARENT` 用于**子图向父图跳转**；v1 不实现子图（C26 仅保签名兼容），
  因此本 feature 只需保证常量**存在且被正确识别**，其跨层传播语义属 v2。

### 3. 用户场景

**P1 — 节点同时跳转与更新状态**
作为用户，我的节点希望「一边跳到下一个节点，一边把状态更新写进去」——两者必须
同时生效，不能只生效其一。

- **独立验收**：节点返回 `Command(goto=END, update={"messages": [...]})` → 执行结果中
  状态包含该更新，且流程按 `goto` 终止。

**P2 — `Command` 的更新走归约器**
作为用户，`Command.update` 里写的 `messages` 应与普通节点返回一样**按归约器合并**，
而不是覆盖。

- **独立验收**：`update` 中的消息与既有消息拼接。

**P3 — `Command.PARENT` 被识别但不越界**
作为实现者，我希望 `Command.PARENT` 在 v1 无子图时被**明确处理**（要么按普通跳转
处理并给出可判定结果，要么抛明确异常），而不是静默失效。

- **独立验收**：传入 `Command.PARENT` 时行为可判定且有测试覆盖。

### 4. 功能需求

- **FR-001**：系统 MUST 支持节点函数返回 `Command`（与返回 dict 并列）。
- **FR-002**：系统 MUST 支持 `Command.goto` 指定下一节点（或 `END`）；MUST 支持
  `Command.update` 指定状态更新。
- **FR-003**：`Command.goto` 与 `Command.update` MUST **同时生效**（跳转不吞掉更新，
  更新不吞掉跳转）。
- **FR-004**：`Command.update` MUST 与普通节点返回值**走同一条合并路径**（逐 key 应用
  归约器；无归约器则覆盖；未知 key 报错）。
- **FR-005**：系统 MUST 提供 `Command.PARENT` 常量；在 v1（无子图）其行为 MUST 可判定
  且被测试覆盖。
- **FR-006**：系统 MUST 定义「节点返回了 `Command` 但 `goto` 与 `update` 均为空」时的
  行为（明确异常或明确无操作），并在 spec 中写死。
- **FR-007**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量。

### 5. 成功标准

- **SC-001**：`Command(goto=END, update={...})` 的执行结果同时满足「跳转生效」与
  「更新生效」两条断言。
- **SC-002**：`Command.update` 的归约行为与普通节点返回值的归约行为**逐项一致**。
- **SC-003**：`Command.PARENT` 的 v1 行为有明确判定与测试覆盖（100% 可判定）。
- **SC-004**：未知 key 的 `update` 抛出契约层已定义的 `InvalidUpdateError`（C6）。

### 6. 验收判据（= 立项书 §5.2 B9F1 小目标，逐条可判定）

> 小目标原文：`Command` 跳转 + 状态更新同时生效

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | `Command` 跳转生效 | 执行结果：流程到达 `goto` 指定的目标 |
| A2 | 状态更新同时生效 | 执行结果：状态包含 `update` 的内容（且按归约器合并） |
| A3 | `Command.update` 与普通节点返回**共用同一条合并路径** | 同一 key 分别用「返回 dict」与「`Command(update=)`」写入，结果**逐项一致**；未知 key 两者都抛 `InvalidUpdateError` |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `Command` | 命令原语：`goto` / `update` / `resume` | **C16** |
| `Command.PARENT` | 向父图跳转标记 | C16 / C26（v2 语义） |
| 节点返回值合并 | dict 与 `Command.update` 共用 | **C6** |

> **口径提醒**：`Command` 的**类型**在 B1F1 已冻结；本 feature 交付**运行期语义**。
> `resume` 字段的运行期行为在 B10F1。

### 8. 边界（本 feature 明确不做）

- 不实现子图（C26）——因此 `Command.PARENT` 的跨层传播不做。
- 不实现中断 / 恢复（属 B10F1）——`Command(resume=...)` 在本 feature 只是被接受，
  不产生恢复效果。
- 不实现 `Send`（属 B11F1）。
- 不实现 `invoke()` 对外 API（属 B7F3）。
- 不实现 checkpoint 中 pending writes 的持久化（属 B14F1）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**。
- **ARCH-1**：L2 只依赖 L1。
- **契约门禁**：不得破坏 B5F2 的 C4 回归与 B7F1 的合并语义。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：与 LangGraph `Command` 语义的对应须标注源码行号
  （`langgraph/types.py:799`）。

### 10. 交付物与后续

- **交付物**：`Command` 运行期语义（`goto` / `update` / `PARENT`）、与 dict 返回值
  **共用**的合并路径、单元测试 + 人工验证记录。
- **后续解锁**：**B12F1**（并发与错误传播，`Command` 是其前置）→ **B10F1**
  （`interrupt` + `resume`，用 `Command(resume=)` 完成恢复闭环）。
- **风险提示**：`Command` 与普通 dict 返回值若走**两条**合并路径，迟早出现行为分叉
  （如「未知 key 报错」只对 dict 生效）。spec 阶段应把「共用同一合并路径」写成
  一条**显式需求**。

---

## 依据

- 立项书 §5.2（B9F1 行）、§5.3（C16 / C6）、§6.3（关键路径含 B9F1）、§9.1（门禁）。
- 源码参照：`langgraph/types.py:799`（`Command` 定义）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C16 标注为「通用语义」）。
- 验收脚本：`harness/demo/graph_core.py`（`Command(update=)` 与 `Command(goto=)` 用例）。
