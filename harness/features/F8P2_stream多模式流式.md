# F8P2 · `stream()`：多模式流式输出 + `StreamWriter`

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | Phase ID | `F8P2` |
> | 所属 Feature | F8（路由语义 + stream + 别名/context） |
> | 架构层 | L2 执行内核层 |
> | 里程碑 | M2 图定义与对外 API（第 18 个） |
> | 前置依赖 | **F7P3** |
> | 规模 | 1,180 行（实现 620 / 测试 560）· 3 人日 |
> | 建议 short-name | `p02-stream-modes` |
> | MVP 必需（★） | 否（但**是「可诊断性」三件套的运行侧基础**） |

---

## 提示词正文

### 1. 目标

交付 `stream()`：以**流式**方式产出运行过程事件，支持多种流式模式，让用户能在图
运行过程中**实时观察**每一步的产出。本 Phase 的判定是：**多模式流式输出**。

### 2. 背景与上下文

- **C12（流式）**：`stream(input, stream_mode=...)`，mode 名称是 **LangGraph 特有**
  （须同名），取值至少覆盖 `values` / `updates` / `checkpoints` / `tasks` / `debug` /
  `messages` / `custom`。
- **「可诊断性是一等功能」（宪法原则 IV）**：流式是用户「实时观察运行」的手段
  （立项书 §5.8.2 第 7 项）。
- **`StreamWriter`**：节点内部主动向流写自定义数据的能力（`custom` 模式的来源）。
- **可视化不阻断执行（宪法原则 IV）**：流式消费 MUST NOT 影响图的执行语义；
  消费者不取（不迭代）时，图仍应能正常跑完。
- 本 Phase 与 F19P1（`TraceSink`）是**两条独立的事件通道**——D11 尚未批准前，
  二者的关联性未规定；spec 中 MUST 标注这一未冻结项（见 §7）。

### 3. 用户场景

**P1 — 观察每一步的状态演进**
作为用户，我在开发期想看到图跑到每一步时的完整状态，以便定位问题出在哪一步。

- **独立验收**：`stream_mode="values"` 产出随执行推进的状态序列。

**P2 — 只看每步的增量**
作为用户，我只想看每步**改了什么**（而非全量状态），以便快速定位变化点。

- **独立验收**：`stream_mode="updates"` 产出每步的更新增量。

**P3 — 节点主动写自定义数据**
作为用户，我的节点想主动往流里写一条进度信息（如「正在检索…」）。

- **独立验收**：节点内经 `StreamWriter` 写入的内容出现在 `custom` 模式的流中。

### 4. 功能需求

- **FR-001**：系统 MUST 提供 `stream(input, stream_mode=...)`，返回**可迭代对象**
  （生成器或等价可迭代结构）。
- **FR-002**：系统 MUST 支持的 mode 名 MUST 与 LangGraph 一致，至少覆盖：
  `values` / `updates` / `checkpoints` / `tasks` / `debug` / `messages` / `custom`
  （C12）。
- **FR-003**：`values` 模式 MUST 产出每步之后的**完整状态**。
- **FR-004**：`updates` 模式 MUST 产出每步的**更新增量**。
- **FR-005**：系统 MUST 提供 `StreamWriter`（节点侧写入自定义数据的入口），
  其数据 MUST 在 `custom` 模式中产出。
- **FR-006**：流式消费 MUST NOT 改变图的执行语义；消费者提前停止迭代时，MUST NOT
  造成资源泄漏或状态不一致（至少：不吞异常）。
- **FR-007**：MUST NOT 引入 async（`astream` 属 v2 范围，未排 Phase）——
  本 Phase 只做同步流。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量。

### 5. 成功标准

- **SC-001**：7 种 mode 名全部被接受（非法 mode 名抛明确异常）。
- **SC-002**：`values` 模式产出的状态序列 == 对应 `invoke` 的最终状态（最后一个元素）。
- **SC-003**：`updates` 模式产出每步增量，且增量可合并回最终状态（合并结果 ==
  `invoke` 的最终状态）。
- **SC-004**：`StreamWriter` 写入的数据出现在 `custom` 流中。
- **SC-005**：流式执行过程中不产生额外出站、不读环境变量。

### 6. 验收判据（= 立项书 §5.2 F8P2 小目标，逐条可判定）

> 小目标原文：多模式流式输出

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 多模式流式输出 | 7 种 mode 各有一例产出断言 |
| A2 | `values` 与 `invoke` 终态一致 | 等值断言 |
| A3 | `updates` 可合并回终态 | 合并断言 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `stream(input, stream_mode)` | 流式执行入口 | **C12** |
| `StreamWriter` | 节点侧自定义数据写入 | C12 |
| 事件通道 | `stream()` 与 `TraceSink` 为**两条独立通道**，共享 `run_id` / `thread_id` | **✅ 已冻结（D11 2026-11-05）** |

> ✅ **口径（已冻结 · D11 批准 2026-11-05）**：立项书 §5.8.3 的**缺口 3** 已关闭——
> `stream()` 产出的事件与 `TraceSink` 收到的 span **共享同一 `run_id` / `thread_id`**
> （Q8 §3.4.1 / 立项书 §5.3.1 / 宪法原则 VII）。
> - `thread_id` = **会话**标识（由 `RunConfig` 承载，字段清单不变）；
> - `run_id` = **单次运行**标识（由运行时在每次 `invoke` / `stream` 开始时生成，
>   **用户不设置**，**不进 `RunConfig`**）；
> - **本 Phase 的义务**：`stream()` 产出的每一条事件 MUST 携带 `run_id` 与 `thread_id`
>   （可作为事件载荷的字段或事件信封的字段，**形态在 spec 中写死**），以便与 span 树
>   按 id 合并为一条时间线。

### 8. 边界（本 Phase 明确不做）

- 不实现 `astream`（v2 范围，未排 Phase）。
- 不实现 trace span 的生产（属 F18P1）与 `TraceSink` 接入（属 F19P1）。
- 不实现 checkpoint 事件（`checkpoints` mode 的真实数据源属 F14P1——本 Phase 可先
  产出占位或空序列，但 MUST 明确其语义边界）。
- 不实现 `messages` mode 的 LangChain 消息抽取语义（**LangChain 特有**，属 freechain；
  freegraph 只做**原样透传**）。
- 不实现前端 / UI 消费（v2，F26）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**。
- **ARCH-1**：L2 只依赖 L1。
- **可视化不阻断执行**（宪法原则 IV）：流式消费不得改变执行语义。
- **人工门禁**：`harness/features/<feature>/manual-verification.md`。
- **证据门禁**：mode 名与语义须附 LangGraph 源码 / 文档来源
  （`langgraph/types.py:122-130` `StreamMode`）。

### 10. 交付物与后续

- **交付物**：`stream()` 实现（7 种 mode）、`StreamWriter`、单元测试 +
  人工验证记录。
- **后续解锁**：**F22P1**（`get_graph` + `draw_mermaid`）→ **F23P1**（PNG）。
- **验收脚本联动**：`harness/demo/visualization.py` 覆盖 C12–C15 / C26，
  其中「七种流式模式」一项由本 Phase 交付——该脚本在 M2 阶段应转绿。
- **风险提示**：mode 名是 LangGraph **特有**约定——若实现时「顺手」改成自造名字，
  验收脚本会直接失败。spec 阶段把 mode 名**逐个列出**并作为 FR。

---

## 依据

- 立项书 §5.2（F8P2 行）、§5.3（C12）、§5.8.1（可视化 12 项接口之「运行 · 流式事件」）、
  §5.8.2（第 7 项）、§5.8.3（缺口 3 / D11）、§9.1（门禁）。
- 源码参照：`langgraph/types.py:122-130`（`StreamMode`）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C12）。
- 验收脚本：`harness/demo/visualization.py`（七种流式模式用例）、
  `harness/demo/graph_core.py`（`stream_mode="updates"` 用例）。
- 宪法 `.specify/memory/constitution.md`：原则 IV（可视化不阻断执行）。
