# F22P1 · `get_graph(xray=)` + 自有 `Graph` 类型 + `draw_mermaid()` ★

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | Phase ID | `F22P1` |
> | 所属 Feature | F22（Graph 类型 + `get_graph` + `draw_mermaid`） |
> | 架构层 | L3 图定义层 |
> | 里程碑 | M2 图定义与对外 API（第 19 个） |
> | 前置依赖 | **F7P2** |
> | 规模 | 1,140 行（实现 620 / 测试 520）· 3 人日 |
> | 建议 short-name | `p22-get-graph-mermaid` |
> | MVP 必需（★） | **是**（固定脚本所需 6 项之一；且**必须先于** `invoke` 就绪） |

---

## 提示词正文

### 1. 目标

交付**图结构导出**能力：编译产物能通过 `get_graph(xray=...)` 返回一个**自有类型**的
图结构对象（含节点与边），该对象能通过 `draw_mermaid()` 输出 **mermaid 文本**——
**纯本地、离线必然成功、零出站**。

### 2. 背景与上下文

- **C13（图结构导出）**：`get_graph(xray=False) -> Graph`，含 `nodes` / `edges`；
  C14（mermaid 导出）：`draw_mermaid() -> str`，**纯本地**、离线必然成功。
- **必须重写，不得复用**：LangGraph 的 `get_graph()` 返回
  `langchain_core.runnables.graph.Graph`——**复用即把 `langchain-core` → `langsmith`
  拖回依赖树**，直接破红线。freegraph 必须有自己的 `Graph` / `Node` / `Edge` 类型
  （类型已在 F2P1 冻结）。
- **`xray` 参数的 v1 义务**：C26（子图）在 v1 **不实现**，因此
  `get_graph(xray=True)` 只需**签名兼容 + 无子图时无副作用**（与 LangGraph 一致）。
  但 `target.py:163` 正是用 `get_graph(xray=True)`，因此该参数**必须存在**。
- **零出站是硬要求**：`draw_mermaid()` MUST 完全本地生成，**MUST NOT** 访问
  `mermaid.ink`（LangGraph 的默认行为每次调用必外呼，Q3 已实测）。
- **时间顺序的硬约束**：`target.py:163` 的 `draw_mermaid_png()` 位于
  `target.py:168` 的 `invoke()` **之前**——因此 F22P1 / F23P1 MUST 早于 F7P3 对用户
  可用（否则脚本在到达验收点前就中断）。

### 3. 用户场景

**P1 — 导出图结构做断言**
作为用户，我想拿到节点与边的清单，从而对图结构做自动化断言（CI 里断言「有 3 个
节点、2 条边」）。

- **独立验收**：图对象的 `nodes` / `edges` 可枚举，元素含名称信息。

**P2 — 生成 mermaid 文本用于评审**
作为用户，我想把图导出成 mermaid 文本，贴到评审文档里（无需任何联网服务）。

- **独立验收**：`draw_mermaid()` 返回字符串，且内容含节点名。

**P3 — 断网也能出图**
作为内网环境的用户，我希望生成 mermaid 文本**不需要任何外网**。

- **独立验收**：断网环境下 `draw_mermaid()` 依然成功（零出站断言同时通过）。

### 4. 功能需求

- **FR-001**：系统 MUST 提供 `get_graph(xray=False)`，返回**自有 `Graph` 对象**
  （不得是 `langchain_core` 的类型）（C13）。
- **FR-002**：`Graph` 对象 MUST 暴露 `nodes` 与 `edges`（可枚举集合），元素为本层定义的
  纯数据类，含节点名 / 边起止 / 边类型（普通边 / 条件边）等信息。
- **FR-003**：`get_graph(xray=True)` MUST 可调用；在无子图时其结果与 `xray=False`
  **一致**（C26 的 v1 义务：签名兼容 + 无副作用）。
- **FR-004**：`Graph` 对象 MUST 提供 `draw_mermaid() -> str`，**纯本地生成**，
  离线必然成功，**MUST NOT** 发起任何网络请求（C14）。
- **FR-005**：mermaid 文本 MUST 含**全部节点名**（可判定），且 MUST 能表达条件边
  （用虚线 + 标签的常规 mermaid 表达）。
- **FR-006**：mermaid 文本 MUST 对**非法字符**（节点名含引号 / 换行 / mermaid 特殊字符）
  做转义，保证输出始终是**合法 mermaid**。
- **FR-007**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量；
  MUST NOT 访问 `mermaid.ink` 或任何外部域名。

### 5. 成功标准

- **SC-001**：`draw_mermaid()` 在**断网环境**下必然成功（零出站断言同时通过）。
- **SC-002**：mermaid 文本包含全部节点名（逐名断言）。
- **SC-003**：`get_graph(xray=True)` 与 `get_graph(xray=False)` 在无子图时结果一致。
- **SC-004**：`Graph` / `Node` / `Edge` 为 freegraph **自有类型**（类型名与导入路径
  可判定；CI 的依赖门禁确认无 `langchain_core`）。
- **SC-005**：含特殊字符的节点名产出的 mermaid 文本仍合法（转义用例通过）。

### 6. 验收判据（= 立项书 §5.2 F22P1 小目标，逐条可判定）

> 小目标原文：`draw_mermaid()` 离线必然成功、零出站

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | `draw_mermaid()` 离线必然成功 | 断网任务中调用成功（退出码 0） |
| A2 | 零出站 | socket 监测夹具「框架出站 = 0」 |
| A3 | `get_graph(xray=)` 可用 | `xray=True` / `xray=False` 各一例 |
| A4 | 自有 `Graph` 类型 | 类型断言 + 依赖门禁 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `Graph` | 图结构（自有类型） | **C13** |
| `Node` / `Edge` | 图结构元素（自有类型，F2P1 冻结） | C13 / C25 |
| `draw_mermaid()` | mermaid 文本导出（纯本地） | **C14** |
| `xray` 参数 | 子图穿透开关（v1 仅签名兼容） | C26 |

> **口径提醒**：C15（PNG 渲染）属 **F23P1**——本 Phase 只交付 mermaid **文本**。
> 本 Phase MUST NOT 让 `draw_mermaid_png()` 依赖任何网络。

### 8. 边界（本 Phase 明确不做）

- 不实现 `draw_mermaid_png()`（属 F23P1）。
- 不实现子图渲染（v2 / C26）——v1 只保 `xray` 签名兼容。
- 不实现前端 / UI（v2 / F26）。
- 不实现 `get_state` / `get_state_history` / `update_state`（属 F14P1 / F15P1 / F16P1）。
- 不实现 trace / span（属 F18P1 / F19P1 / F20P1）。
- 不引入 mermaid 渲染工具链（`mermaid-cli` 等）——v1 零依赖。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`；
  **MUST NOT** 引入 `mermaid-cli`（Node 工具链）等破坏「零第三方运行时依赖」的依赖。
- **零出站**：`draw_mermaid()` MUST NOT 访问 `mermaid.ink`（该域名在网络层黑名单）。
- **零环境变量**。
- **ARCH-1**：L3 只依赖 L1 / L2。
- **人工门禁**：`harness/features/<feature>/manual-verification.md`。
- **证据门禁**：与 LangGraph 的图结构语义对应须标注源码行号
  （`langgraph/pregel/main.py:845`；`langchain_core/runnables/graph_mermaid.py:45,277`）。

### 10. 交付物与后续

- **交付物**：`get_graph(xray=)`、自有 `Graph` / `Node` / `Edge` 实现、
  `draw_mermaid()`（含转义）、单元测试 + 人工验证记录。
- **后续解锁**：**F23P1**（`draw_mermaid_png()`）。
- **★ MVP 六项最小交付集**：本 Phase 是其中第 5 项，且**必须先于 F7P3 对用户可用**
  （`target.py` 的调用顺序）。
- **风险提示**：mermaid 文本的**合法性**容易被忽略——节点名含特殊字符时产出的非法
  mermaid 会让下游渲染工具报错。转义用例必须进 spec 的验收判据，而不是「实现时顺手」。

---

## 依据

- 立项书 §4.3（第 13 项 `get_graph` / `draw_mermaid_png`）、§5.2（F22P1 行）、
  §5.3（C13 / C14 / C15 / C26）、§5.5（PNG 渲染方案 A/B 不采用的理由）、
  §5.7（可视化代码归属与替代品）、§6.2（M2）、§9.2（约束 6）。
- 源码参照：`langgraph/pregel/main.py:845-870`（`get_graph`）、
  `langchain_core/runnables/graph_mermaid.py:45,277,422-423,461`。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C13 / C14 / C26）。
- 验收脚本：`harness/demo/visualization.py`（`case_get_graph` / `case_xray_signature` /
  `case_draw_mermaid`）、`harness/demo/target.py:163`。
- 宪法 `.specify/memory/constitution.md`：原则 I（零出站）、原则 III（PNG 硬约束）。
