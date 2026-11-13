# B7F2 · `compile()` → `CompiledGraph` ★

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B7F2` |
> | 所属 功能块 | B7（compile + 调度 + invoke） |
> | 架构层 | L3 图定义层 |
> | 里程碑 | M2 图定义与对外 API（第 15 个） |
> | 前置依赖 | **B6F1** |
> | 规模 | 1,200 行（实现 640 / 测试 560）· 3 人日 |
> | 建议 short-name | `b7f2-compile` |
> | MVP 必需（★） | **是**（固定脚本所需 6 项之一） |

---

## 提示词正文

### 1. 目标

把构建器产出的「节点 + 边 + schema」规格**编译成一个可执行对象** `CompiledGraph`：
节点挂载、路由通道就位、条件边分支就位、可选能力（checkpointer / store）注入。
本 feature 的判定是：**图可编译；`compile()` 无参可调用**。

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
- **承接条款（B7F1 → B7F2 · M2 · 调度契约的跨 feature 接口）**：B7F1 已交付**调度内核**
  （手写图规格 + super-step 循环），并**冻结**了跨 feature 的接口口径：
  - **图规格形态**：`GraphSpec`（通道映射 + **保序**节点表 + 边表 + **预留**的条件边字段）
    · `NodeSpec`（**订阅集** · 节点函数 `f(state: dict) -> dict`）⇒ **本 feature MUST
    把 L3 的声明式规格**适配**成本 feature 的手写图规格形态（MUST NOT 另造第三套形态）；
  - **节点入参口径**（裁定 26）：入参 MUST 等于 `read_channels(子映射)` 的结果，子映射 MUST
    按「**通道映射的顺序**」构造 ⇒ **本 feature MUST NOT** 改写 key 顺序；
  - **调度状态口径**（裁定 27）：`run_super_step(spec, state)` **MUST 显式**接收调度状态 ·
    `run_super_steps(spec, state=None, *, max_steps=25)` **MAY 省略**（缺省新建一个）⇒
    **本 feature MUST NOT** 改写这两个入口的接收口径；
  - **校验时机**：图规格的校验 MUST 在**构造时**执行（非空值 ⇒ 显式失败）⇒ 本 feature
    的适配器 MUST 依赖此口径（**构造期**即暴露问题，而非跑到一半才炸）。
  该口径由 B7F1 的 `specs/b7f1-superstep-loop/spec.md`（FR-033 / 裁定 25 / 裁定 26 /
  裁定 27 / 裁定 32）落成 · 契约见
  `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §2.1 / §2.1.1。

- **承接条款（B12F1 → B7F2 · M2 · 多会话隔离的「编译产物持规格」口径）**：B12F1 已交付**并发执行
  内核**（同一 super-step 内多节点并发 · 错误传播 · `GraphInterrupt` 收集）并**冻结**了跨 feature
  的接口口径 ⇒ **本 feature MUST** 照它写：
  - **⚠️ 2026-11-12 修订（承 B12F1 · D-4 / V-7）**：多会话隔离**已由 2026-11-12 P2-b 在 L2 落地**
    （**每次运行从规格新建通道实例** · `src/freegraph/runtime/superstep.py:330-345`）⇒
    **实测**：同一份规格**连续两次** ⇒ **不累积**；**并发两次** ⇒ **不串扰** ⇒
    ⇒ **B12F1 已 NOT 把这条列为限制**（初版的「X-6 已知限制」**作废**）⇒
    **本 feature 的义务因此收窄为「对外暴露」**：**编译产物 MUST 持通道「规格」**
    （而非把活实例直接交给运行）⇒ 与 **B7F3** 的「每次 `invoke` 新建实例」**共同**落成
    「一次编译、多会话隔离」的**门面级**验收；
  - **上游同款**：上游的编译产物只持通道**规格**，**每次运行新建实例**
    （`langgraph/channels/last_value.py:50-54` · `from_checkpoint` → `self.__class__(...)`；
    `langgraph/channels/base.py:61-64` 的 docstring 逐字「Return a **new identical channel**」）
    ⇒ **一次编译、多会话并行**天然成立（实测：并发两次 A/B 完全相同）；
  - **B12F1 MUST NOT** 在其内核里改 `Channel` 的冻结面或 `GraphSpec.channels` 的语义来「修」这条
    ⇒ **MUST NOT** 越界到本 feature。
  该口径由 B12F1 的 `specs/b12f1-concurrency-errors/spec.md`（**FR-024** · **裁定 23（已作废）** ·
  下游承接 **D-4** · 回溯修订 **T-7**）落成。

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
  本 feature 内二者的**实现可尚未就绪**（`checkpointer` 属 B14F1；`store` 在 v1
  **无实现**——B17 已砍，2026-11-05），但关键字 MUST 被接受且被记录到编译产物中。
  > **`store=` 的 v1 语义**：关键字被接受（API 兼容，C10），但 v1 **背后无实现**——
  > 传入 `store=` **MUST NOT** 报错，也 **MUST NOT** 静默生效；文档 MUST 显式写明
  > 「v1 不支持 `Store`」。
- **FR-003**：系统 MUST 把构建器规格编译为可执行结构：节点任务规格、每节点的触发
  依赖、路由通道、分支规格（`branch:to:<node>` 机制）。
- **FR-004**：编译产物 MUST 具备对外能力面：`invoke` / `stream` / `get_graph` /
  `get_state` / `get_state_history` / `update_state`（其中未就绪者在本 feature 可先
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

### 6. 验收判据（= 立项书 §5.2 B7F2 小目标，逐条可判定）

> 小目标原文：图可编译；`compile()` 无参可调用

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 图可编译 | 构建器产出 → `compile()` 成功返回编译产物 |
| A2 | `compile()` 无参可调用 | 无参调用成功 |
| A3 | `checkpointer=` / `store=` 关键字被接受 | `compile(checkpointer=None, store=None)` 不抛 `TypeError` |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `CompiledGraph` | 编译产物；对外能力面协议在 B2F1 已定义 | **C10** / C11 / C12 / C13 / C19 |
| 节点任务规格 | 「订阅 channel → 读 → 写」 | C5 / C6 |
| 分支规格 | 条件边（`path_map` 双形态） | C7 |
| 路由通道 | `EphemeralValue`，每 super-step 清空 | C7 / C8 |

> **口径提醒**：`CompiledGraph` 的**协议**（方法面）在 B2F1 冻结；本 feature 交付
> **实现**。`get_graph` 的实现属 B22F1，`invoke` 的实现属 B7F3。

### 8. 边界（本 feature 明确不做）

- 不实现 `invoke()` 的执行语义（属 B7F3）。
- 不实现 `stream()`（属 B8F2）。
- 不实现 `get_graph` / `draw_mermaid`（属 B22F1 / B23F1）。
- 不实现条件边求值（属 B8F1）——本 feature 只把分支规格挂好。
- 不实现 checkpointer / store 的**行为**（`checkpointer` 属 B14F1；`store` **v1 无实现**
  ——B17 已砍，2026-11-05）。
- 不实现节点别名语义（属 B8F3）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**。
- **ARCH-1 / ARCH-4**：L3 只依赖 L1 / L2；公开 API 面只经由 L1 导出。
- **契约门禁**：MUST NOT 破坏 M1 的运行时语义。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：编译产物结构与 LangGraph 的对应须标注源码行号
  （`langgraph/graph/state.py:1177` `compile`）。
- **承接 B3F1 的 FR-005 ③②（验收环境 · 运行期 · 「最小图」反向断言）**：B3F1 只交付
  **③①（声明级 + 导入级）**，**③② 延后至 M2**（依据：B3F1 `spec.md` **裁定 22** · 里程碑见
  立项书 §6.2）。**本 feature 承接「编译」环节** —— 最小图**可被编译**。最终落点 = 门禁
  **G22「场景 ②」**的**运行期断言**（**只接线，MUST NOT 新增门禁编号**）。边界：红线
  **不放宽**（FR-018 无豁免）—— ③② 是同一红线的**运行期加强**，非判据放宽。

### 10. 交付物与后续

- **交付物**：`compile()` 实现、编译产物 `CompiledGraph`、编译期静态校验、
  单元测试 + 人工验证记录。
- **后续解锁**：**B7F3**（`invoke`）→ **B22F1**（`get_graph`）。
- **承接项（红线断言 · 见 §9）**：B3F1 延后的 **FR-005 ③②**（验收环境 · 运行期 ·
  最小图）—— 本 feature 交付「编译」环节，运行期断言在 **B7F3** 闭环点亮。
- **★ MVP 六项最小交付集**：本 feature 是其中第 2 项。
- **风险提示**：编译期校验的**严格程度**是本 feature 的主要决策点——过严会误伤合法用法
  （如条件边目标由 `path_map` 动态决定），过松则把错误推迟到运行期。spec 阶段必须
  逐条列出「编译期检查清单」与「明确不检查的项」。

---

## 下游承接（**B7F4** · 2026-11-13 · **只接线 · 逐条最小改动**）

- **D-5 · 编译侧的知情面**：`GraphSpec.edges` 的**键类型**已放宽为
  `str | tuple[str, ...]`（**兼容性扩展** · 只放宽不收紧）⇒ ⇒ **B7F2** 的 `compile()`
  **MUST 照原样透传**边表 ⇒ ⇒ **MUST NOT** 在编译层**重建屏障语义** ⇒ ⇒
  ⇒ 本 feature 的**破冻结面**（B7F1 契约 §1 / §2.1）对 `compile()` **无行为影响**
  （但 **B7F2 MUST 知情**）⇒ ⇒ 判据 **FR-001** / 裁定 1 / 裁定 14。
  ⇒ 落点：`specs/b7f4-multisource-join/spec.md` 的**承接条款 D-5** · 登记项 **PR-4**。

## 依据

- 立项书 §4.3（第 6 项 `compile()`）、§5.1（编译产物即运行时实例）、§5.2（B7F2 行）、
  §5.3（C10）、§6.2（M2）、§9.1（门禁）。
- 源码参照：`langgraph/graph/state.py:1177`（`compile`）、
  `langgraph/pregel/main.py:845`（`get_graph`）、`langgraph/graph/state.py:73-75`
  （图定义层 import 运行时层）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4。
- 验收脚本：`harness/demo/graph_core.py`（`case_build_and_compile`）。
- 宪法 `.specify/memory/constitution.md`：原则 III。
