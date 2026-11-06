# B8F3 · 节点重命名别名 + `context` 独立通道

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B8F3` |
> | 所属 功能块 | B8（路由语义 + stream + 别名/context） |
> | 架构层 | L3 图定义层 |
> | 里程碑 | M2 图定义与对外 API（第 21 个） |
> | 前置依赖 | **B7F3** |
> | 规模 | 580 行（实现 280 / 测试 300）· 3 人日 |
> | 建议 short-name | `b8f3-node-alias-context` |
> | MVP 必需（★） | 否 |

---

## 提示词正文

### 1. 目标

交付两项「可演进性」能力：
① **节点别名**——允许把节点的**对外可见名**与**内部名**分开（如内部叫 `agent`、
对外叫 `model`），使 freechain 升级时不必破坏用户的 `stream` 过滤器；
② **`context` 独立通道**——运行期上下文通过**独立通道**传递，**不塞进
`configurable`**。本 feature 的判定是：**C21 / C22 / C25 三条契约落地**。

### 2. 背景与上下文

- **C25（节点命名）**：节点名唯一；允许别名（把 `"agent"` 改成 `"model"`）。
  用途：freechain 升级内部节点命名时，用户按节点名写的 `stream` 过滤器不失效。
- **C21（运行时上下文）**：**独立的 `context` 通道**，不塞进 `configurable`。
  `context` 与 `RunConfig` 职责不同：
  - **C21 `context`** = 状态/运行时上下文的**传递通道**（给节点用的只读上下文）；
  - **C22 `RunConfig`** = **每次运行的配置载体**（`thread_id` / `context` /
    `metadata` / `tags`）。
  二者在本 feature 之外的所有引用都按此口径。
- **为什么 `context` 不塞进 `configurable`**：`configurable` 是 `RunnableConfig` 的
  约定（LangChain 特有）——复用即把 `langchain-core` 拖回依赖树。freegraph 自有
  `RunConfig`，因此 `context` 天然有独立位置。
- **调用形态**：`harness/demo/graph_core.py` 已锁定两处形态——
  `add_node("agent", node, alias="model")` 与 `RunConfig(thread_id=..., context=...,
  metadata=..., tags=...)`，且节点读 context 的形态是 `getattr(state, "context", None)`
  （即**节点能读到 context**）。该断言目前是**软断言**（形态待 B8F3 拍板），
  本 feature 拍板后 MUST 升级为**硬断言**。

### 3. 用户场景

**P1 — 换名不破坏用户的过滤器**
作为 freechain 用户，我的 `stream` 过滤器写的是节点名 `model`；freechain 内部把节点
改名成 `agent` 后，我的过滤器仍然有效。

- **独立验收**：以别名寻址节点可执行；`stream` / 图导出中的节点名呈现**对外别名**。

**P2 — 运行时上下文独立传递**
作为用户，我有一份「本次运行的上下文」（如当前用户 ID），希望节点能读到它，
且**不污染状态**（不进 `messages`、不参与归约）。

- **独立验收**：节点能读到 context 值；状态字典中**不出现** context 键。

**P3 — context 不被塞进 configurable**
作为维护者，我希望 `context` 的位置是**固定的**（`RunConfig.context`），避免将来
与 LangChain 的 `configurable` 语义混淆。

- **独立验收**：`RunConfig.context` 可读；节点侧的 context 视图里**没有**
  `configurable` 键。

### 4. 功能需求

- **FR-001**：系统 MUST 支持 `add_node(name, action, alias=...)`：节点**内部名**唯一，
  **对外别名**可与内部名不同（C25）。
- **FR-002**：系统 MUST 允许以**别名**寻址节点（执行、图导出、流式事件的呈现）。
- **FR-003**：系统 MUST 明确「别名冲突」「别名与已有节点内部名冲突」时的行为
  （构建期明确异常），并在 spec 中写死。
- **FR-004**：系统 MUST 提供 `context` **独立通道**（C21）：其值**不进入状态字典**、
  不参与归约、不出现在 `invoke` 的返回状态中。
- **FR-005**：节点 MUST 能读到本次运行的 context（形态按
  `harness/demo/graph_core.py` 锁定的 `getattr(state, "context", None)` 兼容）。
- **FR-006**：`RunConfig` MUST 提供 `thread_id` / `context` / `metadata` / `tags`
  四个字段（C22，类型已在 B1F1 冻结）。
- **FR-007**：context MUST NOT 被塞进 `configurable`（freegraph 不提供
  `configurable` 概念）。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量。

### 5. 成功标准

- **SC-001**：以别名寻址节点成功执行；图导出与流式事件呈现别名。
- **SC-002**：节点读到 context 值；`invoke` 返回的状态**不含** context 键。
- **SC-003**：`RunConfig` 四字段均可读写且语义清晰（`thread_id` / `context` /
  `metadata` / `tags`）。
- **SC-004**：节点侧上下文中**不存在** `configurable` 键。
- **SC-005**：`harness/demo/graph_core.py` 的 C25 软断言**升级为硬断言**并通过。

### 6. 验收判据（= 立项书 §5.2 B8F3 小目标，逐条可判定）

> 小目标原文：契约 **C21**（`context` 通道）/ **C22**（`RunConfig` 标识）/
> **C25**（节点别名）落地

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | C21 落地 | 节点读到 context；状态中无 context 键 |
| A2 | C22 落地 | `RunConfig` 四字段可读（`thread_id` / `context` / `metadata` / `tags`） |
| A3 | C25 落地 | 别名寻址可执行；`harness/demo/graph_core.py` 的 C25 软断言升级为硬断言并通过 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| 节点别名 | 对外可见名 vs 内部名 | **C25** |
| `context` 通道 | 运行期上下文（独立、不入状态） | **C21** |
| `RunConfig` | 运行配置载体 | **C22** |

> **口径提醒**：C21 与 C22 **职责不同**——`context` 是**通道**，`RunConfig` 是**配置载体**。
> 本 feature 交付二者的**运行期接线**（类型已在 B1F1 / B2F1 冻结）。

### 8. 边界（本 feature 明确不做）

- 不实现 `context_schema`（声明式 context schema）——若纳入，须写明支持范围。
- 不实现 checkpoint 中 context 的持久化（属 B14F1 及以后）。
- 不实现子图（v2 / C26）——别名在跨图层级的语义属 v2。
- 不实现 async（v2 范围）。
- 不实现 `Send`（属 B11F1，已在 M1 完成）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**（特别地：**不得**从环境变量读 context 之类）。
- **ARCH-1**：L3 只依赖 L1 / L2。
- **契约门禁**：MUST NOT 破坏 C4 / C6 / C8 / C11。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：与 LangGraph 的对应关系须标注来源（节点别名 / `context` 在 LangGraph
  v1 中的形态），并标注**差异**（freegraph 自有 `RunConfig`，无 `configurable`）。

### 10. 交付物与后续

- **交付物**：节点别名（构建 + 寻址 + 呈现）、`context` 独立通道接线、`RunConfig`
  运行期接线、单元测试 + 人工验证记录。
- **软断言升级**：`harness/demo/graph_core.py` 的 C25 节点别名软断言升级为硬断言。
- **后续解锁**：**M3 全部 8 个 feature**（B18F1 → B19F1 → B20F1 → B20F2 →
  B14F1 → B15F1 → B16F1）。
- **里程碑达成**：本 feature 完成 = **M2（图定义与对外 API）整体结束**——
  达成状态「构建器 + compile + invoke + 路由 + stream + 图导出；**固定脚本跑通
  （fake 模型）—— MVP 验收点**」。M2 在串行口径下位于**第 21 个 feature / 第 63 天**。

---

## 依据

- 立项书 §5.2（B8F3 行）、§5.3（C21 / C22 / C25 与口径说明）、§6.2（M2 里程碑定义）、
  §9.2（验收脚本集的软/硬断言约定）、§9.1（门禁）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C21 / C22 / C25）。
- 验收脚本：`harness/demo/graph_core.py`（`case_run_config_and_context` /
  `case_node_alias`）、`harness/demo/README.md`（软断言清单）。
