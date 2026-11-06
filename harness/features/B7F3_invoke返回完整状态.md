# B7F3 · `invoke()`：返回完整状态 + `InvalidUpdateError` ★

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B7F3` |
> | 所属 功能块 | B7（compile + 调度 + invoke） |
> | 架构层 | L2 执行内核层 |
> | 里程碑 | M2 图定义与对外 API（第 16 个） |
> | 前置依赖 | **B7F1, B12F1** |
> | 规模 | 980 行（实现 460 / 测试 520）· 3 人日 |
> | 建议 short-name | `b7f3-invoke-full-state` |
> | MVP 必需（★） | **是**（固定脚本所需 6 项之一） |

---

## 提示词正文

### 1. 目标

交付 freegraph 的**主对外执行入口** `invoke(input, config=None)`：驱动整张图跑完，
并**返回完整状态**（不是只返回新增消息）。本 feature 的判定是：
`invoke` 返回 `{'messages': [...], 'llm_calls': N}` 这样的**完整状态**。

### 2. 背景与上下文

- **完整状态是硬要求**（宪法原则 III 第 7 项 / C11）：LangGraph 实测
  `invoke()` 返回的键集为 `['llm_calls', 'messages']`——即**所有 schema key**。
  若只返回新增消息，`target.py:169` 的 `messages["messages"]` 就会取不到历史。
- **签名**：`invoke(input, config=None) -> dict`；`config` 同时接受 `RunConfig`
  与普通 dict（`harness/demo/graph_core.py` 已锁定该形态）。
- **输入形态**：`input` 是**初始状态**（部分 key 即可），例如
  `{"messages": [HumanMessage(...)]}`。
- **异常**：节点返回了 schema 中不存在的 key 时，抛出 `InvalidUpdateError`（C6
  「未知 key 报错」）。
- 本 feature 是**固定脚本的验收关键路径**：`invoke` 之前脚本会先执行
  `get_graph(...).draw_mermaid_png()`（B22F1 / B23F1），因此这三项必须**先于**
  `invoke` 就绪。

### 3. 用户场景

**P1 — 一次调用跑完整张图并拿到完整状态**
作为用户，我调 `agent.invoke({"messages": [...]})` 就能拿到图跑完后的**完整状态**，
其中包含初始消息与所有新增消息。

- **独立验收**：返回值的键集 == schema 的 key 集合；`messages` 长度 == 初始 + 新增。

**P2 — 计数型 key 也在返回里**
作为用户，我的 schema 有 `llm_calls`，我希望它也出现在返回状态里（值为最终计数）。

- **独立验收**：`result["llm_calls"] == 2`（两轮模型调用）。

**P3 — 未知 key 会被立刻指出**
作为用户，我的节点误写了一个 schema 里没有的 key，我希望报错指明是哪个 key。

- **独立验收**：抛出 `InvalidUpdateError`，消息含该 key 名。

### 4. 功能需求

- **FR-001**：系统 MUST 提供 `invoke(input, config=None)`，返回**完整状态**字典
  （含 schema 的**全部** key，不只是被写入过的 key）（C11）。
- **FR-002**：`config` MUST 同时接受 `RunConfig` 实例与普通 dict（后者承载
  `recursion_limit` 等运行期参数）。
- **FR-003**：`input` MUST 接受**部分**状态（只含需要初始化的 key），并按通道语义
  写入初始值（带归约器的 key 走归约，无归约器的 key 走覆盖）。
- **FR-004**：系统 MUST 在节点返回**未知 key** 时抛出 `InvalidUpdateError`
  （契约层已定义），消息 MUST 指明违规 key（C6）。
- **FR-005**：`invoke` MUST 驱动整张图执行到终止（`END` 或无待执行任务）。
- **FR-006**：`invoke` MUST 传播节点内部抛出的异常（B12F1 的错误传播语义），
  MUST NOT 吞掉。
- **FR-007**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量。

### 5. 成功标准

- **SC-001**：`invoke` 返回值的键集 == schema 全部 key 集合（100%）。
- **SC-002**：`messages` 长度 == 初始消息数 + 全部新增消息数；`llm_calls` == 实际调用轮数。
- **SC-003**：未知 key 用例抛出 `InvalidUpdateError` 且消息含违规 key 名。
- **SC-004**：`config` 的两种形态（`RunConfig` / dict）均被接受并生效。
- **SC-005**：`invoke` 在全过程中零出站、零环境变量读取。

### 6. 验收判据（= 立项书 §5.2 B7F3 小目标，逐条可判定）

> 小目标原文：`invoke` 返回 `{'messages': [...], 'llm_calls': N}` 完整状态

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 返回完整状态 | 断言返回键集 == schema key 集；`messages` 与 `llm_calls` 均在 |
| A2 | 返回的是**完整**状态而非增量 | 断言 `messages` 含初始消息 + 新增消息 |
| A3 | `InvalidUpdateError` 生效 | 未知 key 用例 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `invoke(input, config)` | 同步执行入口，返回完整状态 | **C11** |
| `InvalidUpdateError` | 未知 key 写入异常 | **C6** |
| 初始状态写入 | `input` → 通道初始值 | C1 / C4 / C6 |

> **口径提醒**：C11 的类型在 B1F1 冻结（返回 `StateDict`）；本 feature 交付**执行语义**。

### 8. 边界（本 feature 明确不做）

- 不实现 `stream()`（属 B8F2）。
- 不实现条件边求值（属 B8F1）——本 feature 先保证静态边路径可跑通；条件边路径在
  B8F1 补齐后由 `target.py` 完整验收。
- 不实现 `get_graph`（属 B22F1）/ `draw_mermaid_png`（属 B23F1）。
- 不实现 checkpoint（属 B14F1）——`invoke` 本 feature 不落盘状态。
- 不实现 async（`ainvoke` 属 v2 范围，未排 feature）。
- 不实现 `Command(resume=)` 的恢复入口对外形态（B10F1 已实现内核能力，
  对外暴露在 B7F3 的 `invoke(Command(...))` 输入形态中，属本 feature 的适配点）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**。
- **ARCH-1**：L2 只依赖 L1。
- **契约门禁第 3 项**：`harness/demo/target.py` 的 diff 断言常驻；
  C4 / C8 回归测试常驻。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：完整状态语义与 LangGraph 的对应须标注实测依据
  （LangGraph 实测返回键集 `['llm_calls','messages']`）。

### 10. 交付物与后续

- **交付物**：`invoke()` 实现（初始状态写入 + 调度驱动 + 完整状态返回 +
  `InvalidUpdateError`）、单元测试 + 人工验证记录。
- **后续解锁**：**B8F1**（条件边路由 + fresh 读）→ **B8F2**（`stream`）→
  **B22F1**（`get_graph`）→ **B23F1**（PNG）。
- **★ MVP 六项最小交付集**：本 feature 是其中第 3 项。六项齐备后
  `harness/demo/target.py` 的 **fake 模型轮**可跑通（M2 验收点）。
- **风险提示**：「完整状态」这一条极易被实现成「只返回本次写入的 key」。spec 阶段的
  验收判据必须写成**键集相等**断言，而不是「含 `messages` 键」。

---

## 依据

- 立项书 §4.3（第 7 项 `invoke` 必须返回完整状态）、§5.2（B7F3 行）、§5.3（C11 / C6）、
  §6.2（M2 = MVP 验收点）、§9.2（fake 注入机制与断言点）、§9.1（门禁）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C11）。
- 验收脚本：`harness/demo/target.py:168`（`agent.invoke(...)`）、
  `harness/demo/graph_core.py`、`harness/demo/agent_loop.py`。
- 宪法 `.specify/memory/constitution.md`：原则 III（第 7 项）。
