# F7P2 · `compile()` → `CompiledGraph` ★

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | Phase ID | `F7P2` |
> | 所属 Feature | F7（compile + 调度 + invoke） |
> | 架构层 | L3 图定义层 |
> | 里程碑 | M2 图定义与对外 API（第 15 个） |
> | 前置依赖 | **F6P1** |
> | 规模 | 1,200 行（实现 640 / 测试 560）· 3 人日 |
> | 建议 short-name | `p07-compile` |
> | MVP 必需（★） | **是**（固定脚本所需 6 项之一） |

---

## 提示词正文

### 1. 目标

把构建器产出的「节点 + 边 + schema」规格**编译成一个可执行对象** `CompiledGraph`：
节点挂载、路由通道就位、条件边分支就位、可选能力（checkpointer / store）注入。
本 Phase 的判定是：**图可编译；`compile()` 无参可调用**。

### 2. 背景与上下文

- `compile()` 是**图定义层与执行内核层的接缝**：它把 L3 的声明式规格翻译成 L2 的
  可执行结构（节点任务规格 + 触发依赖 + 路由通道 + 分支）。
- **同名同签名是硬要求**（宪法原则 III 第 6 项）：`compile()` MUST 无参可调用；
  MUST 支持 `checkpointer=` / `store=` 两个可选关键字（**即使对应实现尚未就绪**，
  关键字也必须被接受——验收脚本 `graph_core.py` 会断言这一点）。
- **编译产物即运行时实例**：LangGraph 的 `CompiledStateGraph` 的基类链是
  `CompiledGraph(Pregel)`——编译产物**就是**运行时。freegraph 采同构设计，但两者
  **分层归属不同**：freegraph 把执行内核（L2）与图定义（L3）分开，`CompiledGraph`
  持有并驱动 L2 的运行时。
- **编译期校验**：编译是「最后的机会」做静态检查的时点（如路由函数返回值不在
  `path_map` 中、节点不可达等）。

### 3. 用户场景

**P1 — 一行拿到可执行图**
作为用户，我写完建图代码后调 `agent_builder.compile()` 就得到一个能 `invoke` 的对象。

- **独立验收**：`compile()` 无参调用成功，返回对象非空且具备 `invoke` / `stream` /
  `get_graph` 能力面。

**P2 — 编译时能注入可插拔能力**
作为用户，我希望能 `compile(checkpointer=..., store=...)` 传入自己的持久化与存储实现。

- **独立验收**：`compile(checkpointer=None, store=None)` 被接受（不抛 `TypeError`）。

**P3 — 编译期发现图定义的问题**
作为用户，我希望「边指向不存在的节点」「路由目标不在 `path_map` 里」这类问题在
**编译时**被指出，而不是跑到一半才炸。

- **独立验收**：构造错误图 → `compile()` 抛出明确异常。

### 4. 功能需求

- **FR-001**：系统 MUST 提供 `compile()`，**无参可调用**（C10）。
- **FR-002**：系统 MUST 支持 `checkpointer=` / `store=` 两个可选关键字；
  本 Phase 内二者的**实现可尚未就绪**（`checkpointer` 属 F14P1；`store` 在 v1
  **无实现**——F17 已砍，2026-11-05），但关键字 MUST 被接受且被记录到编译产物中。
  > **`store=` 的 v1 语义**：关键字被接受（API 兼容，C10），但 v1 **背后无实现**——
  > 传入 `store=` **MUST NOT** 报错，也 **MUST NOT** 静默生效；文档 MUST 显式写明
  > 「v1 不支持 `Store`」。
- **FR-003**：系统 MUST 把构建器规格编译为可执行结构：节点任务规格、每节点的触发
  依赖、路由通道、分支规格（`branch:to:<node>` 机制）。
- **FR-004**：编译产物 MUST 具备对外能力面：`invoke` / `stream` / `get_graph` /
  `get_state` / `get_state_history` / `update_state`（其中未就绪者在本 Phase 可先
  抛明确「未实现」异常，**MUST NOT** 静默不存在）。
- **FR-005**：系统 MUST 在编译期做静态校验（至少：边目标节点存在、条件边源节点
  存在、`path_map` 形态合法），错误消息 MUST 指明具体问题。
- **FR-006**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量。

### 5. 成功标准

- **SC-001**：`compile()` 无参调用成功，返回 `CompiledGraph` 实例。
- **SC-002**：`compile(checkpointer=None, store=None)` 被接受（不抛异常）。
- **SC-003**：编译期校验的 3 类错误各有一例被捕获。
- **SC-004**：编译产物的能力面 6 个方法**全部存在**（未就绪者抛明确异常而非
  `AttributeError`）。
- **SC-005**：编译过程不读环境变量、不发起网络请求（零出站）。

### 6. 验收判据（= 立项书 §5.2 F7P2 小目标，逐条可判定）

> 小目标原文：图可编译；`compile()` 无参可调用

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 图可编译 | 构建器产出 → `compile()` 成功返回编译产物 |
| A2 | `compile()` 无参可调用 | 无参调用成功 |
| A3 | `checkpointer=` / `store=` 关键字被接受 | `compile(checkpointer=None, store=None)` 不抛 `TypeError` |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `CompiledGraph` | 编译产物；对外能力面协议在 F2P1 已定义 | **C10** / C11 / C12 / C13 / C19 |
| 节点任务规格 | 「订阅 channel → 读 → 写」 | C5 / C6 |
| 分支规格 | 条件边（`path_map` 双形态） | C7 |
| 路由通道 | `EphemeralValue`，每 super-step 清空 | C7 / C8 |

> **口径提醒**：`CompiledGraph` 的**协议**（方法面）在 F2P1 冻结；本 Phase 交付
> **实现**。`get_graph` 的实现属 F22P1，`invoke` 的实现属 F7P3。

### 8. 边界（本 Phase 明确不做）

- 不实现 `invoke()` 的执行语义（属 F7P3）。
- 不实现 `stream()`（属 F8P2）。
- 不实现 `get_graph` / `draw_mermaid`（属 F22P1 / F23P1）。
- 不实现条件边求值（属 F8P1）——本 Phase 只把分支规格挂好。
- 不实现 checkpointer / store 的**行为**（`checkpointer` 属 F14P1；`store` **v1 无实现**
  ——F17 已砍，2026-11-05）。
- 不实现节点别名语义（属 F8P3）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**。
- **ARCH-1 / ARCH-4**：L3 只依赖 L1 / L2；公开 API 面只经由 L1 导出。
- **契约门禁**：MUST NOT 破坏 M1 的运行时语义。
- **人工门禁**：`harness/features/<feature>/manual-verification.md`。
- **证据门禁**：编译产物结构与 LangGraph 的对应须标注源码行号
  （`langgraph/graph/state.py:1177` `compile`）。

### 10. 交付物与后续

- **交付物**：`compile()` 实现、编译产物 `CompiledGraph`、编译期静态校验、
  单元测试 + 人工验证记录。
- **后续解锁**：**F7P3**（`invoke`）→ **F22P1**（`get_graph`）。
- **★ MVP 六项最小交付集**：本 Phase 是其中第 2 项。
- **风险提示**：编译期校验的**严格程度**是本 Phase 的主要决策点——过严会误伤合法用法
  （如条件边目标由 `path_map` 动态决定），过松则把错误推迟到运行期。spec 阶段必须
  逐条列出「编译期检查清单」与「明确不检查的项」。

---

## 依据

- 立项书 §4.3（第 6 项 `compile()`）、§5.1（编译产物即运行时实例）、§5.2（F7P2 行）、
  §5.3（C10）、§6.2（M2）、§9.1（门禁）。
- 源码参照：`langgraph/graph/state.py:1177`（`compile`）、
  `langgraph/pregel/main.py:845`（`get_graph`）、`langgraph/graph/state.py:73-75`
  （图定义层 import 运行时层）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4。
- 验收脚本：`harness/demo/graph_core.py`（`case_build_and_compile`）。
- 宪法 `.specify/memory/constitution.md`：原则 III。
