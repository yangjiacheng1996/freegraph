> **2026-11-20 后续修订（C25 正式作废）**：节点别名不再属于 v1；图导出继续使用内部节点名（`name == id`）。本 spec 中 alias 相关文字保留为历史。

# Feature Specification: B22F1 · `get_graph(xray=)` + 自有 `Graph` 类型 + `draw_mermaid()`

**Feature Branch**: `b22f1-get-graph-mermaid`

**Created**: 2026-11-20

**Status**: Draft

**Input**: User description: "B22F1 · `get_graph(xray=)` + 自有 `Graph` 类型 + `draw_mermaid()` —— 交付**图结构导出**能力：编译产物能通过 `get_graph(xray=...)` 返回一个**自有类型**的图结构对象（含节点与边），该对象能通过 `draw_mermaid()` 输出 **mermaid 文本**——**纯本地、离线必然成功、零出站**。前置依赖 **B7F2**。"

> **MVP 定位**：本 feature 是固定脚本 `harness/demo/target.py` 所需 6 项之一，且 `target.py:163`
> 的 `get_graph(xray=True).draw_mermaid_png()` 在 `target.py:168` 的 `invoke()` **之前**
> ⇒ 本 feature（与 B23F1）MUST 先于固定脚本端到端轮（登记项 **EV-4**）落地。
> **本 feature 只交付 mermaid 文本**；`draw_mermaid_png()` 归 **B23F1**。

> **设计更新（2026-11-20 · 发起者裁定 · 优先于本文件旧版与 B9F1 D-8）**：
> 原方案「运行期跳转记录（DR-1）」**作废**。经核实上游 `langgraph 1.2.11` 在「图渲染」维度
> **更优**（静态声明、不依赖运行），发起者决定**勇于打破冻结面、按最优设计执行**：
> 采用上游的**完整静态声明机制**——① `Command` 泛型化 + 返回注解 `Command[Literal[...]]`
> 的**类型推断**；② `add_node(..., destinations=...)` 的**显式声明**。二者并存，
> `destinations` 优先。图导出 MUST NOT 依赖任何运行期跳转记录。
> 该决定按宪法「破冻结面的三条」登记：**偏离登记 + 发起者追认 + 具名承接方 B22F1**。

---

## 承接条款（上游 feature → 本 feature）

> 宪法「跨 feature 承接的接线通则」：上游 feature 指名本 feature 的跨 feature 义务
> MUST 在本 spec 落成 **FR + 裁定**。本 feature 经发起者 2026-11-20 授权，
> **破冻结面**改为上游最优设计（见下 **H-2** 与「破冻结面的回溯修订清单」）。

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B7F2 → B22F1** | **M2** | **图结构导出的数据来源**：`CompiledGraph.get_graph(*, xray=False)` MUST 从 B7F2 交付的 `_spec`（`GraphSpec`：节点表 / 边表 / 通道表）、`_conditional_edges`（plain mapping）与 `_builder_spec`（**冻结快照**：`node_records` 的 `metadata` / `defer` / `destinations`，以及含 `END` 目标的完整边表）导出；MUST NOT 重新解析构建器状态、MUST NOT 重跑 `_build_spec()`；公开属性面**不包含** `nodes` / `channels` / `builder`（X-10）。 | `specs/b7f2-compile/spec.md` **下游承接 D-5** · `contracts/compile-contract.md` §2.1 / §8 | FR-008 · FR-009 · FR-025 · 裁定 6 |
| **H-2** | **B9F1 → B22F1** | **M3** | **`goto` 可为序列 ⇒ 渲染须画多条边**：B9F1 已冻结 `Command.goto` 可为**节点名序列**（多目标 ⇒ 各自成边）⇒ 本 feature MUST 画出**多条**边（MUST NOT 只画一条）。⚠️ **2026-11-20 发起者裁定**：原「目标只能来自运行期跳转记录（DR-1）」**作废**；改为**上游同款静态声明**——`Command[Literal[...]]` 类型推断 + `add_node(destinations=...)`。**本 feature 承接破冻结面**：`Command` 泛型化（B1F1）· `add_node` 增 `destinations`（B6F1）· 编译快照携带声明（B7F2）。 | `specs/b9f1-command-primitive/spec.md` **裁定 1** / **裁定 9** / **引文差异 ⑩** · **下游承接 D-8（已被本裁定取代）** · `contracts/command-contract.md` | FR-010 · FR-011 · FR-026 · 裁定 2 |
| **H-3** | **B8F1 → B22F1** | **M2** | **图导出里的条件边**：`get_graph()` MUST 能表达**条件边**（源节点 → 可能的多个目标）⇒ MUST **复用** B8F1 的 `targets` / `route_channels` 口径（条件边载荷的**恰 5 键**）⇒ **MUST NOT** 另算一份目标集合；条件边的**路由通道**（`branch:to:<target>`）**只作声明载体**（**从不被写入**）⇒ 图导出 MUST NOT 把它当成「已写入的通道」。 | `specs/b8f1-conditional-edges-fresh-read/spec.md` **下游承接 D-4** · `contracts/conditional-edge-contract.md` §2.1 / §5（I-1） | FR-005 · FR-024 · 裁定 4 |
| **H-4** | **B8F2 → B22F1** | **M2** | **图导出与流式互不影响**：`get_graph` / `draw_mermaid` MUST NOT 依赖 `stream()` 的副作用；`stream()` MUST NOT 调用图导出。二者只在「同一张编译产物」上共享**只读静态规格**。 | `specs/b8f2-stream-modes/spec.md` **下游承接 D-4** | FR-009 · FR-012 · 裁定 3 |
| **H-5** | **B7F3 → B22F1** | **M3** | **就绪顺序**：只读基准脚本的调用顺序是「先 `get_graph(...).draw_mermaid_png()`，后 `invoke(...)`」⇒ B22F1 / B23F1 MUST 先于固定脚本端到端轮（EV-4）就绪；B7F3 MUST NOT 越界实现 `get_graph` / `draw_mermaid_png`。本 feature MUST 做到**任何运行之前** `get_graph()` 即可用（静态声明天然满足）。 | `specs/b7f3-invoke-full-state/spec.md` **下游承接 D-3** · 契约 **CF-03** | FR-019 · SC-009 |
| **H-6** | **B7F1 → B22F1** | **M2** | **门禁 3 的固定脚本**：宪法质量门禁 3「`harness/demo/target.py` 原样可跑」在本 feature 与 B23F1 齐备前物理不可达成 ⇒ 本 feature MUST 交付其中的「图导出」环节（`get_graph()` / `draw_mermaid()`），**MUST NOT** 改动固定脚本的**任何一行**（`target.py` 是**只读基准**）。 | `specs/b3f1-scaffold-ci-gates/spec.md` **裁定 22** · `harness/proposals/立项书.md` §6.2 | Assumptions · SC-009 |
| **H-7** | **B2F1 / B2F2 / B8F2 → B22F1** | **M1** | **自有类型与门面冻结**：`Graph` / `Node` / `Edge` 的类型名与导入路径已在 B2F1 冻结（`freegraph.contracts.graph`）；`freegraph.graph` 的 **8** 个公开符号是 B2F2 + B8F2 冻结面（`StateGraph` / `START` / `END` / `Send` / `interrupt` / `Command` / `RunConfig` / `get_stream_writer`）⇒ 本 feature MUST NOT 改名 / 迁移 / 新增公开顶层导出；B2F1 的 research 已指认「mermaid 文本导出」由本 feature 交付。⚠️ **本 feature 经发起者追认，修订 B2F1 的 `Edge` 不变式**：节点声明的动态边在无显式标签时 `condition` 可为 `None`（见 X-07）。 | `specs/b2f1-contracts-protocols/spec.md` · `research.md`（`B22F1 只碰 graph.py`）· `contracts/public-api.md` §6 / §8 | FR-001 · FR-016 · FR-017 · SC-004 · 破冻结面 **T-6** |
| **H-8** | **B6F1 → B22F1** | **M2** | **节点名口径**：图结构里的节点名 MUST 与构建器 / `invoke` / `stream` 使用**同一套节点名口径**（业务节点名；**C25 已正式作废**）⇒ MUST NOT 为图导出自造命名映射。 | `specs/b6f1-stategraph-builder/spec.md` · `specs/b7f2-compile/spec.md` 裁定 12 / 13 | FR-002 · FR-012 |
| **H-9** | **B1F1 / B6F1 / B7F2 → B22F1** | **M2** | **上游最优设计的破冻结面承接**：`Command` MUST 泛型化以支持 `Command[Literal[...]]`；`add_node` MUST 接受 `destinations`（`tuple[str, ...]` 或 `dict[str, str]`，仅用于图渲染、不影响执行）；B7F2 的 `_NodeRecord` / 编译快照 MUST 携带该声明。三者 MUST 按上游 `langgraph/graph/state.py:810-861` 同款实现。发起者已追认（2026-11-20）；承接方 = **B22F1**。 | `langgraph/graph/state.py:810-861` · `:1780-1788`（`_control_static`）· 本 spec 裁定 2 | FR-010 · FR-011 · FR-026 · 破冻结面 **T-1 / T-2 / T-3** |

---

## 下游承接条款（本 feature → 下一棒）

> 本 feature 冻结「图结构对象 + mermaid 文本导出」这组跨 feature 接口。**只接线 · 逐条最小改动**。

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 |
|---|---|---|---|---|
| **D-1** | **B22F1 → B23F1** | **M2** | **PNG 的文本前置**：`Graph.draw_mermaid()` 返回的**合法 mermaid 文本**是 B23F1 `draw_mermaid_png()` 的**唯一输入**；B23F1 MUST 复用本 feature 的转义口径与确定性输出，MUST NOT 另写一套 mermaid 生成器。**PNG 渲染 MUST NOT 访问 `mermaid.ink` 或任何外部域名**（宪法原则 I / III）。 | FR-013 · FR-016 · SC-001 / SC-005 · 裁定 5 |
| **D-2** | **B22F1 → B23F1** | **M2** | **条件边与节点声明边的可见性**：B23F1 渲染 PNG 时 MUST 保留本 feature 已画出的**全部条件边**（`add_conditional_edges` 的分支）与**节点声明的动态目标边**（`Command[Literal[...]]` / `destinations`，可多目标）⇒ MUST NOT 只渲染静态边。 | FR-005 · FR-010 · 裁定 2 / 4 |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 导出图结构做断言 (Priority: P1)

作为用户，我想在 CI 里拿到节点与边的清单，从而对图结构做自动化断言（例如「有 3 个节点、2 条边」），
并且这个导出**不执行图、不产生副作用**。

**Why this priority**: 这是 C13 的最小价值面——没有可枚举的节点 / 边，后续断言、可视化与
人工评审都无从谈起；它也是 P2 / P3 的数据前提。

**Independent Test**: 编译一张含业务节点、静态边、条件边与节点声明动态目标的图；调用
`get_graph()`；逐项断言节点名集合、边起止、条件边标记与非空性；全程不调用 `invoke()`。

**Acceptance Scenarios**:

1. **Given** 一张已编译的图（含 2 个业务节点 `a` / `b`、入口边、静态边与 1 条条件边），
   **When** 调用 `get_graph()`，**Then** 返回自有 `Graph`，其 `nodes` / `edges` 均可枚举，
   含全部业务节点名，且 `edges` 非空。
2. **Given** 同一张已编译的图，**When** 在**任何运行之前**调用 `get_graph()`，
   **Then** 调用成功且图结构与运行后**完全一致**（静态声明，不随运行变化）。
3. **Given** 一张含条件边的图，**When** 枚举 `edges`，**Then** 条件边以
   `conditional=True`（且带条件名）出现，每个可能目标各成一条边。
4. **Given** 节点 `a` 的返回注解为 `Command[Literal["b","c"]]`（或 `add_node(..., destinations=...)`），
   **When** 调用 `get_graph()`，**Then** `a→b` 与 `a→c` **各成一条**边，MUST NOT 只画一条，
   且**无需运行**即可见。

---

### User Story 2 - 生成 mermaid 文本用于评审 (Priority: P2)

作为用户，我想把图导出成 mermaid 文本，贴到评审文档里，且文本包含全部节点名与边的方向。

**Why this priority**: C14 是可视化与人工评审的交付面；它是 B23F1 PNG 的文本前置。

**Independent Test**: 对 `get_graph()` 的返回值调用 `draw_mermaid()`，断言返回 `str`、
非空、包含全部节点名、普通边与条件边使用不同箭头。

**Acceptance Scenarios**:

1. **Given** 一张已编译的图，**When** 调用 `graph.draw_mermaid()`，**Then** 返回非空 `str`，
   含全部业务节点名。
2. **Given** 含条件边 / 节点声明边的图，**When** 调用 `draw_mermaid()`，**Then** 它们以
   **虚线**表达；有标签时带标签，无标签时仅虚线（与上游 `data=None` 同款）。
3. **Given** 同一张图重复调用 `draw_mermaid()`，**Then** 两次输出**逐字相同**（确定性）。

---

### User Story 3 - 断网也能出图 (Priority: P3)

作为内网 / 断网环境的用户，我希望生成 mermaid 文本**不需要任何外网**，且框架自身零出站。

**Why this priority**: 宪法原则 I 的硬约束；LangGraph 的默认 PNG 路径会外呼 `mermaid.ink`，
本 feature MUST 完全本地化文本导出。

**Independent Test**: 在禁止出站的 socket 监测夹具下调用 `draw_mermaid()`，断言成功且
框架出站计数为 0。

**Acceptance Scenarios**:

1. **Given** 网络被监测 / 阻断，**When** 调用 `draw_mermaid()`，**Then** 调用成功（退出码 0）。
2. **Given** 同一断网环境，**When** 观测 socket 活动，**Then** 「框架出站 = 0」。

---

### Edge Cases

- **节点名含引号 / 换行 / 反斜杠 / 花括号 / 中文 / emoji**：mermaid 文本仍 MUST 是合法语法；
  节点 id 使用**确定性安全编码**，标签使用**转义**（裁定 5）。
- **节点名重复**：由生产者保证唯一（B2F1 契约）；本 feature MUST NOT 静默去重成「一个节点」。
- **节点名含 `|` / `:`**：构建器已拒绝（B6F1）；本 feature 不改变该行为。
- **空图**：`Graph()` 无节点无边时 `draw_mermaid()` MUST 仍返回合法（非空）文本。
- **`get_graph(xray=True)` 无子图**：结果 MUST 与 `xray=False` **一致**，无副作用。
- **`get_graph(xray=True)` 在子图场景（v1 不存在）**：不实现穿透；MUST NOT 抛异常。
- **条件边的目标为 `END`**：MUST 以指向 `__end__` 的条件边表达。
- **条件边目标集合为空**：不产生边，MUST NOT 抛异常。
- **静态边目标被编译期过滤（`END`）**：图导出仍 MUST 能表达该边（裁定 6）。
- **节点声明目标为序列**（`Command[Literal["b","c"]]` 或 `destinations=("b","c")`）：
  每个目标各一条边；`END` 落 `__end__`；MUST NOT 合并成一条。
- **`destinations` 与返回注解同时存在**：**`destinations` 优先**，MUST NOT 叠加两份。
- **`destinations` 为 `dict`**：键 = 目标，值 = 边标签；MUST 原样成为 `Edge.condition`。
- **`destinations` 为 `tuple`**：目标无标签 ⇒ `Edge.condition is None`（与上游 `data=None` 同款）。
- **返回注解不可解析**（前向引用 / `NameError` / 非函数对象）：MUST **静默降级为「无声明」**
  （上游 `state.py:857-858` 同款），MUST NOT 让 `add_node` / `compile()` 失败。
- **声明了未登记目标**（既不是节点也不是 `END`）：**编译期**显式失败（内置 `ValueError`），
  消息点名该目标（上游 `state.py:1155-1160` 同款）。
- **`destinations` 形态**：签名按上游写 `dict[str, str] | tuple[str, ...] | None`；
  **运行期接受任何非 `str` 的 `Sequence[str]`**（列表亦接受 · 上游实测同款）；
  非 `Sequence[str]` / 非 `dict[str, str]` ⇒ **登记期**显式失败（内置 `TypeError`）。
- **多次 `invoke()` / `stream()` 后导出**：图结构 MUST **不随运行变化**（静态声明；无运行期记录）。
- **`stream()` 之后调用 `get_graph()`**：结果 MUST 与调用 `stream()` 之前**逐项相等**（H-4）。
- **终结点**（无任何出边的**可达**业务节点）：MUST 自动补一条普通边到 `__end__`（上游同款）。
- **不可达节点**：节点 MUST 仍出现在 `Graph.nodes`，但其出边 MUST **不导出**（上游模拟只发现
  可达边 · FR-028）。
- **多源汇合边**（`add_edge(["a","b"], "c")`）：拆成 `a→c` 与 `b→c` 两条普通边；
  若 `b` 不可达 ⇒ 该组不可满足 ⇒ **两条都不导出**，且可达的 `a` 因无出边补 `a→__end__`
  （上游实测同款 · FR-029）。
- **多源边源元组顺序**：不影响可观察图结构；导出顺序按元组顺序（确定性）。
- **「末步单源」场景（含单节点自环）且无显式 `END`**：上游会补一条 `源→__end__` 条件边；
  freegraph **不补**（登记 **X-08**，理由：不模拟执行）。
- **节点 `metadata`**：MUST 从登记项拷贝；`defer=True` 追加 `defer: True`；
  `interrupt_before` / `interrupt_after` 追加 `__interrupt` 标记（上游同款）。

---

## Upstream Parity *(mandatory — 宪法原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11**（取证于 2026-11-20 · 用户 site-packages · 非仓库依赖）
· 参照 `langchain-core` 的 `runnables/graph_mermaid.py` 与 `runnables/graph.py`
（同批取证）。换上游版本后 MUST 重新核实全部行号。

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | `get_graph` 入口 | `langgraph/pregel/main.py:845-870`：`get_graph(config=None, *, xray=False)`；`xray` 为真时收集子图（本仓库 v1 无子图）；返回 `draw_graph(...)` | `get_graph(*, xray=False)`；v1 无子图 ⇒ `xray=True` 与 `False` 同结果；返回自有 `Graph` | **DIFF** | freegraph 无子图（C26 v1）；`config` 参数 v1 不暴露（裁定 7） |
| P-02 | 图结构的节点集合 | `_draw.py:225-236`：业务节点 + 合成 `START`（`__start__`）；`:292-293` 在需要时补 `END`（`__end__`） | 业务节点 + 合成 `__start__` / `__end__`；节点顺序 = `__start__` → 业务节点声明序 → `__end__` | **SAME** | 语义同款；ID 沿用 `__start__` / `__end__`（`langgraph/constants.py:28-30`）；顺序差异不影响集合语义 |
| P-03 | 静态边的表达 | `_draw.py:236`（START → 入口）、`:247-256`（终结节点 → END）；普通边实线 | 静态边逐条表达；含 START → 入口、业务边、终结边 → END；普通边实线 | **SAME** | 语义同款 |
| P-04 | `add_conditional_edges` 条件边 | `_draw.py:138-151` 静态写 → 边；`:256` `conditional=True`；渲染侧虚线（`graph_mermaid.py:159-164`） | 条件边**逐目标**成边、`conditional=True`、带条件名（`branch`）；渲染为虚线 + 标签 | **SAME（结构）/ DIFF（标签）** | 复用 B8F1 的 `targets`（H-3）；上游 `data` 为 `None`，freegraph 用 `branch` 作 `condition`（X-09） |
| P-05 | `draw_mermaid` 入口 | `langchain_core/runnables/graph_mermaid.py:45`：`draw_mermaid(nodes, edges, …) -> str` | `Graph.draw_mermaid() -> str`（无参数） | **DIFF** | 自有 `Graph` 已持有节点 / 边（C13）；MUST NOT 引入上游样式参数族 |
| P-06 | mermaid 节点 id 安全化 | `graph_mermaid.py:255-266`：保留 `[A-Za-z0-9_-]`，其余字符 → `\` + 小写十六进制码点 | **逐字同款**的安全编码 | **SAME** | 保证特殊字符节点名仍产合法 id，且不同名字不碰撞 |
| P-07 | mermaid 默认头部 / 样式 | `graph_mermaid.py` 的 `draw_mermaid` 默认 `with_styles=True` ⇒ YAML frontmatter + `graph TD;` | v1 输出**不含** YAML frontmatter，仅合法 `graph TD;` 文本 | **DIFF** | 零依赖 / 确定性 / 最小文本；不影响「合法 mermaid」判据（裁定 5） |
| P-08 | 标签转义 | 上游仅安全化 id；标签内的引号 / 换行未被系统转义 | **STRICTER**：标签额外转义引号、换行、`<` / `>` / `&` / `|` / `\` / `#` | **STRICTER** | 宪法原则 XI 允许更严；产出 MUST 始终合法（FR-016） |
| P-09 | 动态 `goto` 目标的图渲染来源 | `graph/state.py:810-861`：`Command[Literal[...]]` 返回注解推断；`destinations=` 显式声明（`:860-861` 覆盖推断）；`_control_static`（`:1780-1788`）转为条件写 | **逐字同款**：`Command` 泛型 + 类型推断 + `add_node(destinations=...)`；`destinations` 优先；无运行期记录 | **SAME** | 2026-11-20 发起者裁定按最优设计改回上游（旧 DR-1 作废） |
| P-10 | 图导出是否执行图 | 上游 `_draw.py:42` 以受限轮次**模拟** Pregel 循环来发现边（不执行节点函数） | freegraph MUST NOT 模拟执行 / MUST NOT 调用节点；从编译期**静态声明**导出 | **DIFF** | 上游的模拟会带入大量运行时语义；freegraph 只读快照、零执行、零副作用（H-1 / H-4） |
| P-11 | PNG 外呼 | `graph_mermaid.py:277`（`draw_mermaid_png`）；`:422-423` 默认 `https://mermaid.ink` | **本 feature 不交付 PNG**；文本导出 MUST NOT 访问任何域名 | **STRICTER** | 宪法原则 I：`mermaid.ink` 网络层黑名单；C15 归 B23F1 |
| P-12 | 节点 / 边类型 | `langchain_core/runnables/graph.py:65`（`Edge`）/ `:95`（`Node`）/ `:255`（`Graph`） | **同名自有实现**（`freegraph.contracts.graph`）；不复用、不复制上游代码 | **DIFF** | 原则 I / IX；复用即拖回 `langchain-core` → `langsmith` |
| P-13 | 节点 `metadata` 的图渲染 | `_draw.py:221-229`：拷贝节点 metadata；`defer` → `defer: True`；断点 → `__interrupt` = `before` / `after` / `before,after` | **逐字同款** | **SAME** | 上游同款；可观察性一致 |
| P-14 | 终结节点自动连 `END` | `_draw.py:247-257`：`termini`（只入不出）→ 普通 `END` 边；无边且**末步单源**时补条件 `END` 边 | 可达业务节点无任何出边 ⇒ 自动补普通边到 `__end__`；**不**复制「末步单源」启发式 | **SAME（常规）/ DIFF（末步单源：自环 / 循环）** | 静态导出不模拟执行；边界登记 **X-08** |
| P-15 | 边去重 | `_draw.py:286-288`：`add_edge` 按 `(source, target)` 去重；实测**条件 / 声明边优先于普通静态边**（E-13 / E-15） | **逐字同款**：按 `(source, target)` 去重；`conditional=True` 优先，其余先出现者优先 | **SAME** | 避免同一端点的静态边与声明边重复渲染 |
| P-16 | `destinations` 的标签与执行影响 | `state.py:404-410`：`dict` 键 = 目标、值 = 标签；`tuple` = 目标（运行期亦接受列表）；**仅影响图渲染，不影响执行** | **逐字同款**；`dict` 的标签 → `Edge.condition`；`tuple` / 列表 → `condition=None` | **SAME** | 上游同款（`:1780-1788`；列表接受为实测） |
| P-17 | 声明目标的存在性校验 | `state.py:1150-1162`：`destinations` / 推断目标不在 `nodes` 且非 `END` ⇒ `ValueError` 点名目标 | **逐字同款**（编译期） | **SAME** | 早失败且异常类型一致 |
| P-18 | 边的可达性 | `_draw.py:42-214`：从 START 的模拟只发现**可达**边；不可达节点只进节点表、不产生边 | 从 `__start__` 按**边组**做**静态可达闭包**，只导出可满足组的边；节点表含全部业务节点 | **SAME** | 静态闭包等价于上游的「只发现可达边」；无需执行模拟（X-08） |
| P-19 | 多源汇合边的渲染 | `graph/state.py:1551-1561` 建 join 屏障；`_draw.py` 的模拟为每个可达源各发现一条 `源→目标` 普通边（实测：`a→c` / `b→c`，`conditional=False`） | **逐字同款**：每个源各一条普通 `Edge`；组内全部源可达才导出 | **SAME** | 上游同款；`Edge` 是单起点，不造 n 元边 |

### 差分场景组 *(mandatory)*

> **落点**：`tests/differential/parity_probe.py` ⇒ **CI 的 Linux 全量档真跑**
> （上游缺席即 skip · 沿用 B5F2 的「缺席即 skip」纪律）。
> 上游对照只断言**结构语义**（节点名集合 / 边端点 / 条件标记）；MUST NOT 断言 mermaid 文本逐字相等。

| # | 场景 | 断言（可判定） | 判词 |
|---|---|---|---|
| D-01 | 线性图 `START→a→b→END` | 业务节点集合 == `{a,b}`；存在 `__start__→a`、`a→b`、`b→__end__` | SAME |
| D-02 | 条件边 `a --route--> {b, END}` | `a→b` 与 `a→__end__` 两条边均 `conditional=True`；freegraph 的条件名 == `route`（上游 `data` 不参与对照） | SAME |
| D-03 | 同一源多条条件边（不同 branch） | 每条分支的每个目标各自成边；条件名分别正确 | SAME |
| D-04 | 特殊字符节点名 `a"b` / `x\ny` / `{p}` | 所有节点都可判定地出现在图中；`draw_mermaid()` 返回合法结构（id 安全编码 + 标签转义） | STRICTER |
| D-05 | `Command[Literal["b","c"]]`（**不运行**即导出） | 存在 `a→b` 与 `a→c` 两条 `conditional=True` 边；`condition is None` | SAME |
| D-06 | `add_node(a, destinations={"b":"to-b","c":"to-c"})` | `a→b` / `a→c` 两条边；`condition` 分别为 `to-b` / `to-c`；`destinations` 覆盖返回注解 | SAME |
| D-07 | 声明未知目标 `destinations=("nope",)` | 两侧均在编译期失败（`ValueError`，消息含目标名） | SAME |
| D-08 | 运行前导出 vs 运行后导出 | `nodes` / `edges` **逐项相等**（无运行期记录） | SAME |
| D-09 | `get_graph(xray=True)` vs `xray=False`（无子图） | `nodes` / `edges` 逐项相等 | SAME |
| D-10 | `stream()` 后导出 | 与 `stream()` 前逐项相等（H-4） | SAME |
| D-11 | 不可达节点 `d`（登记但无入边） | 两侧节点表都含 `d`；`d` 的出边两侧都不出现 | SAME |
| D-12 | 「末步单源」场景（**单节点自环** `START→a→a` **或**两节点循环 `START→a→b→a`）且无显式 `END` | 上游多一条末步源 `→__end__` 条件边（自环 = `a`；循环 = `b`）；freegraph 无此边 | DIFF（X-08） |
| D-13 | 多源汇合边 `add_edge(["a","b"], "c")`（两源均可达） | 两侧都有 `a→c` 与 `b→c` 两条普通边 | SAME |
| D-14 | 多源汇合边其一源不可达 | 两侧都不出现该组的边；可达源 `a` 补 `a→__end__` | SAME |
| D-15 | 同一端点同时有静态边与条件 / 声明边（`a→b` 两种） | 两侧只出现一条，且为**条件 / 声明边**（`conditional=True`） | SAME |

### 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-01** | 破冻结面 | B1F1「`Command` 非泛型」 | 上游最优设计需要 `Command[Literal[...]]` 类型推断；发起者 2026-11-20 追认 | B22F1 · M2 |
| **X-02** | 破冻结面 | B6F1 `add_node` 签名（无 `destinations`） | 上游最优设计需要显式声明（`tuple` / `dict`）；发起者 2026-11-20 追认 | B22F1 · M2 |
| **X-03** | 自研区 / 破冻结面 | 图导出的数据来源 | B7F2 的 `_spec` 不含 `END` 边、`metadata`、`defer`、`destinations`；这些只在 `_builder_spec`（冻结快照）中。读取它**不构成**重跑 `_build_spec()`；B7F2 的 `_NodeRecord` 需追加 `destinations` 字段 | B22F1 · M2 |
| **X-04** | 更严的失败信号 / 输出约束（STRICTER） | mermaid 标签转义（P-08） | 上游未系统转义标签；freegraph 要求「任何节点名 ⇒ 始终合法 mermaid」 | B22F1 · M2 |
| **X-05** | 自研区 | mermaid 头部与样式参数（P-07） | v1 零依赖、确定性、最小文本；不实现上游 frontmatter / 样式参数族 | B22F1 · M2 |
| **X-06** | 自研区 | 子图穿透（C26 / `xray`） | v1 不实现子图；`xray` 只保签名兼容与无副作用 | B22F1 · M2（v2 / C26） |
| **X-07** | 破冻结面 | B2F1 `Edge` 不变式「条件边 `condition` MUST 非空」 | 节点声明的动态边在无标签时 MUST 与上游 `data=None` 同款 ⇒ `condition=None`；发起者 2026-11-20 追认 | B22F1 · M2 |
| **X-08** | 自研区 / DIFF | 图导出不模拟执行（P-10 / P-14 边界） | 上游 `_draw.py` 的受限模拟会带入运行时语义，并带有「末步单源补条件 END」与 `limit=250` 截断；freegraph 只读静态声明快照 + 静态可达闭包，保证零执行 / 零副作用 ⇒ **不复制**该两处模拟性行为 | B22F1 · M2 |
| **X-09** | 自研区 / DIFF（标签） | `add_conditional_edges` 边的标签（P-04） | 上游 `Edge.data` 为 `None`；freegraph 的 `Edge.condition` 用分支名（B8F1 的 `branch`），与 prompt 的「条件边虚线 + 标签」一致 | B22F1 · M2 |
| **X-10** | 自研区（DIFF） | `get_graph` 的 `config` 参数 / 子图入口（P-01） | v1 不暴露 `config`；C26 子图不实现 ⇒ 仅保 `xray` 签名与无副作用 | B22F1 · M2（C26 → v2） |
| **X-11** | 自研区（DIFF） | `draw_mermaid` 的入口形态（P-05） | 自有 `Graph` 已持有节点 / 边（C13）⇒ `Graph.draw_mermaid()` 无参；不引入上游样式参数族 | B22F1 · M2 |
| **X-12** | 自研区（DIFF · C13 强制重写） | 节点 / 边类型（P-12） | 原则 I 要求不得复用 `langchain_core.runnables.graph`；自有类型是 C13 的硬约束，不是可选优化 | B22F1 · M2 |
| **X-13** | 更严的失败信号 / 输出约束（STRICTER） | PNG 外呼（P-11） | 本 feature 不交付 PNG；文本导出 MUST NOT 访问 `mermaid.ink` 或任何域名；PNG 归 B23F1 且同样零出站 | B22F1 · M2（B23F1） |

**X ↔ P 对应（三表一致的可判定锚点）**：X-01↔P-09 · X-02↔P-16 · X-03↔P-10/P-13 ·
X-04↔P-08 · X-05↔P-07 · X-06↔P-01 · X-07↔P-04/P-16 · X-08↔P-10/P-14 ·
X-09↔P-04 · X-10↔P-01 · X-11↔P-05 · X-12↔P-12 · X-13↔P-11。

### 破冻结面的回溯修订清单 *(发起者 2026-11-20 追认)*

| # | 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 / 承接方 |
|---|---|---|---|---|
| **T-1** | B1F1：`Command` 非泛型（`contracts/types.py`） | `Command` 改为泛型（`Generic[N]`，运行期语义不变）；同步 API 兼容矩阵与公开快照 | **拆分而不删**：`goto` / `update` / `resume` / `graph` / `PARENT` 的既有断言逐条保留；新增 `Command[...]` 下标与推断断言 | 发起者 2026-11-20 · B22F1 |
| **T-2** | B6F1：`add_node` 签名（`_stategraph.py`） | 增加关键字 `destinations: dict[str, str] \| tuple[str, ...] \| None = None` | **拆分而不删**：既有参数 / 失败信号断言保留；新增 `destinations` 形态与校验断言 | 发起者 2026-11-20 · B22F1 |
| **T-3** | B7F2：`_NodeRecord` / 编译快照 | `_NodeRecord` 追加 `destinations` 字段；`_BuilderSpec` / 编译产物沿用 | **拆分而不删**：既有字段与快照断言保留；新增字段为追加 | 发起者 2026-11-20 · B22F1 |
| **T-4** | B9F1：下游承接 D-8「目标只能来自运行期跳转记录」 | 本 spec 裁定 2 取代；B9F1 的 `goto` 运行期语义**不变** | **拆分而不删**：运行期 `goto` / `update` 断言全部保留；仅图渲染来源改变 | 发起者 2026-11-20 · B22F1 |
| **T-5** | B2F1：`Graph`（2 字段 · 不可哈希） | `Graph` 追加 `draw_mermaid()` 方法（**不改字段 / 构造签名 / `__all__`**） | **拆分而不删**：字段形态 / 不可哈希 / 浅不可变断言保留；新增方法断言为追加 | B2F1 `research.md` 已指认 mermaid 归 B22F1 · 发起者 2026-11-20 |
| **T-6** | B2F1：`Edge` 不变式（条件边 `condition` 非空） | 放宽为「`add_conditional_edges` 分支边 MUST 非空；节点声明的无标签动态边 MAY 为 `None`」 | **拆分而不删**：既有分支边断言保留；新增 `None` 用例 | 发起者 2026-11-20 · B22F1 |

> **不新增公开顶层符号**：`draw_mermaid` 是 `Graph` 的实例方法；`destinations` 是 `add_node`
> 的关键字；`Command` 仍是原符号（仅泛型化）。`freegraph.__all__` /
> `freegraph.graph.__all__` / `freegraph.contracts.graph.__all__` 均不变。

---

## Clarifications

### Session 2026-11-20（设计裁定 · spec 阶段写死，plan 不得再翻）

> **背景**：提示词初稿已写死「自有 `Graph` / `Node` / `Edge` · `get_graph(xray=)` 签名 ·
> `draw_mermaid()` 零出站 · 条件边可表达 · 转义必须进判据」，并经 **2026-11-20 发起者裁定**
> 改为上游最优的**静态声明**机制。本节给出唯一口径。
>
> 纪律：宪法原则 XI「上游有答案 ⇒ 照抄」；上游无答案处（自有类型 / 零出站文本）由本节裁定。

#### Q1（`get_graph` 的签名与返回类型）

→ **A：`get_graph(self, *, xray: bool = False) -> Graph`**，`xray` **仅关键字**、缺省 `False`；
返回 `freegraph.contracts.graph.Graph`（自有类型）。MUST NOT 增加 `config` 参数；
MUST NOT 返回 `langchain_core` 的类型。签名以 `contracts/protocols.py` 的 `CompiledGraph` 冻结面为准。

#### Q2（`Command[Literal[...]]` + `destinations`：上游静态声明）

→ **A：逐字照抄上游**。

- `Command` MUST 泛型化：`class Command(Generic[N])`；运行期字段 / 校验 / `PARENT` 不变。
- **类型推断**：MUST 在**登记期**（`add_node` 被调用时）对节点函数（含 `__call__`）取 `get_type_hints`；
  推断结果随登记项冻结（上游 `state.py:822-858` 同款；**MUST NOT** 推迟到编译期重算）；
  返回注解若为 `Union`，在其中寻找 `Command`；若 `get_origin(Command[...])` 的首参为
  `Literal[...]`，其值为目标集合。异常（`NameError` / `TypeError` / `StopIteration`）
  MUST **静默忽略**（上游 `state.py:810-858` 同款）。
- **显式声明**：`add_node(..., destinations=...)`：
  - 签名按上游写 `tuple[str, ...]`，但**运行期接受任何非 `str` 的 `Sequence[str]`**（含列表，
    上游实测同款）⇒ 目标集合，标签为 `None`；
  - `dict[str, str]` ⇒ 键 = 目标、值 = 标签；
  - 显式 `destinations` **覆盖**类型推断结果（上游 `:860-861` 同款）；
  - **仅影响图渲染，不影响执行**（上游 `state.py:412-414` 同款）。
- **目标存在性**：声明目标必须是已登记节点或 `END`；否则**编译期** `ValueError` 点名目标。
- **MUST NOT** 引入运行期跳转记录 / 观测字段；**MUST NOT** 从 `invoke()` / `stream()` 捕获动态边。
- 多目标 ⇒ **每个目标各一条** `conditional=True` 边；MUST NOT 只画一条。

#### Q3（导出与执行 / 流式的隔离）

→ **A：`get_graph()` / `draw_mermaid()` 是纯只读静态导出**。

- `get_graph()` MUST NOT 调用 `invoke()` / `stream()` / 节点函数，MUST NOT 运行图；
- 图结构 MUST NOT 依赖任何运行副作用；运行前后**逐项相等**；
- `stream()` MUST NOT 调用 `get_graph()` / `draw_mermaid()`；
- 两扇门只在同一张编译产物上共享**只读静态规格**。

#### Q4（`add_conditional_edges` 条件边的导出口径）

→ **A：逐分支、逐目标**。对 `_conditional_edges[source]` 的每一项：

- 目标集合 = 该项的 `targets`（**逐字复用** B8F1 的五键载荷，MUST NOT 重算 / 重排）；
- 每个目标生成一条 `Edge(source, target, conditional=True, condition=branch)`；
- `targets` 为空 ⇒ 不生成边；`END` ⇒ 目标写 `__end__`；
- `route_channels` MUST NOT 被当成「已写入的通道」，也 MUST NOT 成为图节点。

#### Q5（mermaid 的合法性与转义口径）

→ **A：确定性安全 id + 确定性标签转义 + 最小头部**。

- 头部：输出 MUST 以 `graph TD;` 开头（可含换行 / 缩进）；v1 MUST NOT 输出 YAML frontmatter；
- 节点 id：`[A-Za-z0-9_-]` 原样保留，其余字符 → `\` + 小写十六进制 Unicode 码点
  （**逐字同款**上游 `_to_safe_id` · P-06）⇒ 不同节点名 ⇒ 不同 id；
- 标签：包在双引号内；`"` → `#quot;`、换行 / 回车 → `<br/>`、`<` → `#lt;`、`>` → `#gt;`、
  `&` → `#amp;`、`|` → `#124;`、`\` → `#92;`、`#` → `#35;`；其余字符原样
  （`#` 先于其它实体处理，避免二次转义）；
- 边：普通边 `-->`；条件 / 声明边**虚线**；`condition` 非 `None` 时带标签，
  `condition is None` 时**仅虚线不画标签**（上游 `data=None` 同款）；
  **边标签与节点标签使用同款转义**（`condition` 可来自用户 `destinations` 标签）；
- 输出 MUST NOT 依赖随机数 / 时间 / 环境变量 ⇒ 同图同文本；
- 空图 MUST 返回非空合法文本（至少含头部）。

#### Q6（`END` 边、节点 metadata 与声明快照的数据来源）

→ **A：只读 `_builder_spec`（B7F2 保留的完整冻结快照）**。

B7F2 的 `_spec.edges` 在编译期过滤了单源 `END` 目标（H-1 的裁定 5），故以下信息只在
`_builder_spec` 中，读取它**不构成**「重新解析构建器状态 / 重跑 `_build_spec()`」：

- `_builder_spec.edges` ⇒ 恢复 `END` 目标边；
- `_builder_spec.node_records[name].metadata` / `.defer` ⇒ 节点 `metadata` 与 `defer: True`；
- `_builder_spec.node_records[name].destinations` ⇒ 节点声明的动态目标；
- 编译产物的 `interrupt_before_nodes` / `interrupt_after_nodes` ⇒ `__interrupt` 标记。

其余结构 MUST 取自 `_spec` 与 `_conditional_edges`（登记为 **X-03**，属自研区 / 破冻结面）。

#### Q7（节点集合、伪节点、顺序与去重）

→ **A：**

- 节点 = 合成 `__start__` + `spec.nodes` 的**声明顺序** + 合成 `__end__`；
- 边顺序固定为：`START` 入口边 → `_spec.edges` 静态边（声明顺序）→ `_conditional_edges` 条件边
  （登记顺序 × `targets` 顺序）→ 节点声明边（节点声明顺序 × 目标顺序）→ 终结 `END` 边；
- **可达性过滤**：从 `__start__` 出发按**边组**做**静态可达闭包**——单源边 / 条件边目标 /
  节点声明目标各成**大小 1 的组**；多源汇合边的源元组是**一个组**，仅当**组内全部源可达**时
  目标才可达；**只导出可满足组**内的边；节点表仍含**全部**业务节点（上游 `_draw` 的模拟
  只发现可达边，但节点集合含全部登记节点）；
- **去重按 `(source, target)`**（上游 `_draw.py:286-288` 同款）：`conditional=True` 的边
  **优先**保留；同为普通边或同为条件边时**先出现者优先**；忽略 `condition` 参与判重；
- `__start__` / `__end__` 的 `Node.id == name`；
- **边界（DIFF · X-08）**：任何「末步单源」场景（含单节点自环）且无显式 `END` 时，上游的模拟
  会补一条 `源→__end__` 条件边；freegraph 的静态导出**不补**。上游 `limit=250` 的模拟截断亦不复现。
- 本 feature MUST NOT 引入业务节点别名解析（**C25 已正式作废**）。

#### Q8（失败信号）

→ **A：上游同款 + 导出本身零新增异常类型**。

- `destinations` 形态非法（既非非 `str` 的 `Sequence[str]`，也非 `dict[str, str]`）⇒ **登记期**
  内置 `TypeError`（上游签名写 `tuple`，但运行期接受列表 · 实测同款）；
- 声明目标不在节点表且非 `END` ⇒ **编译期**内置 `ValueError`，消息点名目标；
- 返回注解不可解析 ⇒ **静默忽略**（无声明，不报错）；
- `get_graph()` 对合法编译产物 MUST 成功；
- `draw_mermaid()` 对任何 `Graph`（含空图、`condition=None`）MUST 返回 `str`。

---

### Session 2026-11-20（clarify 轮 · 用户参与）

- Q: 同一张编译产物被多次 `invoke()` 后，`get_graph()` 里的动态 `goto` 边应该保留哪些？
  → A: **原「累积并集」裁定作废**。发起者裁定改回上游最优设计（静态声明）⇒ 图结构
  **与运行次数无关**；运行前后逐项相等。
- Q: 为达成上游最优设计，本 feature 应采用哪一套动态目标声明机制？
  → A: **两者都做（完整上游）**——`Command[Literal[...]]` 类型推断 + `add_node(destinations=...)`，
  `destinations` 优先；并据此破 B1F1 / B6F1 / B7F2 快照的冻结面。
- Q: 节点声明的动态目标没有显式标签时，`Edge.condition` 应该填什么？
  → A: **填 `None`（完全照抄上游 `data=None`）**；同步修订 B2F1 的 `Edge` 不变式（T-6），
  mermaid 对 `None` 只画虚线不画标签。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 提供 `CompiledGraph.get_graph(*, xray: bool = False) -> Graph`，
  返回 **freegraph 自有** `freegraph.contracts.graph.Graph`（**不得**是 `langchain_core` 的类型）。
- **FR-002**: `Graph.nodes` MUST 是可枚举的 `tuple[Node, ...]`，每个 `Node` MUST 含节点名信息
  （`id` / `name`），并 MUST 覆盖**全部**业务节点。
- **FR-003**: `Graph.edges` MUST 是可枚举的 `tuple[Edge, ...]`，每条边 MUST 含起止节点名与
  **边类型**（普通边 / 条件边 / 节点声明边）。
- **FR-004**: 图结构 MUST 表达 `START` 入口与 `END` 终结：含合成节点 `__start__` / `__end__`
  及相应边（当图存在入口 / 终结语义时）。
- **FR-005**: `add_conditional_edges` 的条件边 MUST 逐分支、逐目标表达；目标集合 MUST
  **逐字复用** B8F1 的 `targets`（MUST NOT 另算一份）；每条条件边 MUST `conditional=True`
  且 `condition == branch`。
- **FR-006**: `END` 目标的静态边 MUST 可被表达（数据来源见裁定 6）；`END` 在图中 MUST 统一记为
  `__end__`；**可达的终结点**（无任何出边的业务节点）MUST 自动补一条普通边到 `__end__`；
  「末步单源」边界按 **X-08**（不补上游的模拟性条件 `END` 边）。
- **FR-007**: `get_graph(xray=True)` MUST 可调用；在**无子图**时其结果 MUST 与 `xray=False`
  **一致**，且 MUST NOT 产生副作用（C26 的 v1 义务）。
- **FR-008**: 图结构 MUST 从编译期冻结快照导出：`_spec`（节点表 / 边表）、`_conditional_edges`
  （条件边）、`_builder_spec`（`END` 边 / `metadata` / `defer` / `destinations`）。
  MUST NOT 重新解析构建器状态，MUST NOT 重跑 `_build_spec()`，MUST NOT 暴露
  `nodes` / `channels` / `builder` 等公开属性。
- **FR-009**: `get_graph()` MUST 是**纯只读、零执行**导出：MUST NOT 调用 `invoke()` /
  `stream()` / 任何节点函数；`stream()` MUST NOT 调用图导出（H-4）。
- **FR-010**: 节点声明的动态目标 MUST 来自**上游同款静态声明**：
  ① 返回注解 `Command[Literal[...]]` 的**类型推断**；② `add_node(..., destinations=...)`。
  二者并存、`destinations` **覆盖**推断；每个目标 MUST 各成一条 `conditional=True` 边。
- **FR-011**: `Command` MUST 泛型化（`Generic[N]`），运行期字段 / 构造校验 / `PARENT` 语义
  MUST 保持不变；`add_node` MUST 接受 `destinations`（`tuple[str, ...]` / `dict[str, str]` /
  `None`）；`destinations` MUST **仅影响图渲染、不影响执行**。
- **FR-012**: 图导出 MUST NOT 引入运行期跳转记录 / 观测字段，MUST NOT 依赖
  `invoke()` / `stream()` 的任何副作用；运行前后图结构 MUST 逐项相等。
- **FR-013**: `Graph` MUST 提供 `draw_mermaid() -> str`，**纯本地**生成，离线必然成功，
  MUST NOT 发起任何网络请求（尤其 MUST NOT 访问 `mermaid.ink` 或任何外部域名）。
- **FR-014**: mermaid 文本 MUST 含**全部节点名**（普通名字面出现；特殊名以确定性安全形式出现），
  并 MUST 表达每条边的方向。
- **FR-015**: mermaid 文本 MUST 区分普通边与条件边：普通边实线；条件边 / 节点声明边**虚线**；
  `condition` 非 `None` 时带标签，`None` 时仅虚线。
- **FR-016**: mermaid 文本 MUST 对非法 / 特殊字符做**确定性转义**（引号 / 换行 / `<` / `>` /
  `&` / `|` / 反斜杠 / `#` / 非 ASCII 等），保证输出始终是**合法 mermaid**；节点 id 的编码
  MUST 保证不同节点名不碰撞。
- **FR-017**: 系统 MUST NOT import `langchain` / `langchain-core` / `langgraph` / `langsmith`；
  MUST NOT 读环境变量；MUST NOT 引入 `mermaid-cli` 或任何第三方运行时依赖；
  MUST NOT 新增公开顶层导出符号。
- **FR-018**: `draw_mermaid()` MUST 对**任何** `Graph`（含空图、`condition=None`）返回非空 `str`；
  `get_graph()` 对合法编译产物 MUST 不抛异常。
- **FR-019**: `get_graph()` MUST 在**任何运行之前**可用（H-5 / 固定脚本调用顺序）。
- **FR-020**: 重复调用 MUST 幂等：同图多次 `get_graph()` 返回**相等**结构（新对象，不共享可变状态）；
  同图多次 `draw_mermaid()` 返回**逐字相同**文本。
- **FR-021**: `xray` MUST 仅作签名兼容：v1 对任何真值 / 假值均 MUST NOT 改变结果或触发额外行为；
  MUST NOT 抛 `TypeError`。
- **FR-022**: 条件边的路由通道（`branch:to:<target>`）MUST NOT 成为图节点、MUST NOT 被当成
  「已写入的通道」、MUST NOT 出现在 `Graph.nodes`。
- **FR-023**: 边集合 MUST 按 `(source, target)` 去重（上游同款）；同一端点的普通边与条件边
  MUST 只保留一条，且 **`conditional=True` 优先**；同为普通 / 同为条件时先出现者优先。
- **FR-024**: 图导出 MUST NOT 修改 `_spec` / `_builder_spec` / `_conditional_edges`。
- **FR-025**: 业务节点的 `Node.metadata` MUST 从 `_builder_spec.node_records[name].metadata` 拷贝；
  `defer=True` 追加 `defer: True`；`interrupt_before` / `interrupt_after` 追加
  `__interrupt` 标记（`before` / `after` / `before,after`）。
- **FR-026**: 声明目标（推断或显式）MUST 在**编译期**校验存在性：不在节点表且非 `END`
  ⇒ 内置 `ValueError` 点名目标；`destinations` 形态非法 ⇒ 登记期内置 `TypeError`。
- **FR-027**: 返回注解不可解析（前向引用 / `NameError` / `TypeError` / `StopIteration`）
  MUST **静默降级为无声明**（上游同款），MUST NOT 让 `add_node` / `compile()` 失败。
- **FR-028**: 图导出 MUST 做**静态可达性过滤**：从 `__start__` 沿**边组**求可达闭包；
  只导出**可满足组**内的边（静态 / 条件 / 节点声明 / `END`）；节点表 MUST 仍含全部业务节点。
  MUST NOT 用运行期信息求可达性。
- **FR-029**: **多源汇合边**（`_spec.edges` 的 `tuple[str, ...]` 键）MUST 拆成
  **每个源各一条** `Edge(source, target)`（`conditional=False`），按元组顺序导出；
  MUST NOT 造「多起点单条边」；仅当**组内全部源可达**时才导出该组的边
  （上游 `add_edge([a,b], c)` 的渲染同款）。

---

### Key Entities

- **`Graph`**: 图结构（自有类型，C13）。字段：`nodes: tuple[Node, ...]`、`edges: tuple[Edge, ...]`；
  提供 `draw_mermaid() -> str`（C14）。不可变、不可哈希。
- **`Node`**: 图节点元素（自有类型）。字段：`id` / `name` / `metadata`；`name` 缺省归一为 `id`；
  `metadata` 可含 `defer` / `__interrupt`。
- **`Edge`**: 图边元素（自有类型）。字段：`source` / `target` / `conditional` / `condition`；
  `add_conditional_edges` 分支边 `condition == branch`；节点声明边可 `condition=None`。
- **`Command[N]`**: 泛型命令原语。`Command[Literal["b","c"]]` 的返回注解用于图渲染的静态目标推断；
  运行期语义不变。
- **`destinations`**: `add_node` 的图渲染声明——`tuple[str, ...]`（无标签）或
  `dict[str, str]`（目标 → 标签）；覆盖返回注解推断；不影响执行。
- **条件边载荷**: `CompiledGraph._conditional_edges`（B8F1 五键：`branch` / `path` / `path_map` /
  `targets` / `route_channels`）；图导出只读 `branch` 与 `targets`。
- **伪节点**: `__start__` / `__end__`（与上游 `langgraph/constants.py:28-30` 同 ID）。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 在禁止出站的监测夹具下，调用 `draw_mermaid()` **必然成功**，且「框架出站 = 0」。
- **SC-002**: `draw_mermaid()` 返回的文本对**每一个**节点名都可判定地包含（逐名断言）。
- **SC-003**: `get_graph(xray=True)` 与 `get_graph(xray=False)` 在无子图时，
  `nodes` 与 `edges` **逐项相等**。
- **SC-004**: `get_graph()` 返回值的类型模块路径为 `freegraph.contracts.graph`，
  类型名为 `Graph`；`Graph` / `Node` / `Edge` 均为自有类型；CI 依赖门禁确认无
  `langchain_core` / `langchain` / `langgraph` / `langsmith`。
- **SC-005**: 节点名含引号 / 换行 / 反斜杠 / `#` / mermaid 特殊字符时，`draw_mermaid()` 输出
  仍通过**合法性结构断言**（安全 id 编码 + 标签转义 + 箭头语法可解析）。
- **SC-006**: `add_conditional_edges` 条件边在 `Graph.edges` 中逐目标出现
  （`conditional=True`、条件名正确），并在 mermaid 文本中以虚线表达。
- **SC-007**: 节点声明目标为序列（`Command[Literal["b","c"]]` 或 `destinations=("b","c")`）时，
  **不运行**图即可导出 `a→b` 与 `a→c` **两条**边，MUST NOT 只有一条。
- **SC-008**: `get_graph()` 在从未运行过的编译产物上可用，且运行前后 `nodes` / `edges`
  **逐项相等**（静态声明，无运行期记录）。
- **SC-009**: 固定脚本所需环节可达成：`compile()` 后、`invoke()` 前，
  `get_graph(xray=True)` 与 `draw_mermaid()` 均成功（不要求本 feature 交付 PNG）。
- **SC-010**: `stream()` 调用前后，同一编译产物的图结构**逐项相等**；`stream()` MUST NOT 调用图导出。
- **SC-011**: 重复调用 `get_graph()` / `draw_mermaid()` 输出稳定（结构相等 / 文本逐字相等）。
- **SC-012**: 图导出不修改任何编译期快照（前后快照比较相等）。
- **SC-013**: `Command[Literal[...]]` 与 `destinations` **各自**都能产生声明边；
  两者同时存在时以 `destinations` 为准（不叠加）。
- **SC-014**: 声明未知目标时，`compile()`/`validate()` 抛 `ValueError` 且消息含目标名。
- **SC-015**: `destinations={"b":"to-b"}` 的边 `condition == "to-b"`；`destinations=("b",)`
  或类型推断的边 `condition is None`；mermaid 对 `None` 仅画虚线。
- **SC-016**: 不可达节点只出现在 `Graph.nodes`、不产生任何出边（静态可达闭包）。
- **SC-017**: 多源汇合边 `["a","b"]→c` 在两侧都是 `a→c` + `b→c` 两条普通边；
  若一源不可达，则该组两条边都不出现（FR-029）。
- **SC-018**: 同一端点同时有静态边与条件 / 声明边时，只保留一条且 `conditional=True`
  （上游 E-13 / E-15 同款）。

### 验收判据（= 立项书 §5.2 B22F1 小目标，逐条可判定）

> 小目标原文：`draw_mermaid()` 离线必然成功、零出站

| # | 判据 | 判定方式 | 覆盖 |
|---|---|---|---|
| A1 | `draw_mermaid()` 离线必然成功 | 断网任务中调用成功（退出码 0） | SC-001 / SC-009 |
| A2 | 零出站 | socket 监测夹具「框架出站 = 0」 | SC-001 |
| A3 | `get_graph(xray=)` 可用 | `xray=True` / `xray=False` 各一例 | SC-003 / SC-008 |
| A4 | 自有 `Graph` 类型 | 类型断言 + 依赖门禁 | SC-004 |

---

## Out of Scope

- **`draw_mermaid_png()`**（C15 · 属 **B23F1**）——本 feature MUST NOT 实现，也 MUST NOT 让
  文本导出依赖任何网络。
- **子图渲染 / `xray` 穿透**（C26 · v2）——v1 只保签名兼容与无副作用。
- **前端 / UI**（v2 / B26）。
- **`get_state` / `get_state_history` / `update_state`**（B14F1 / B15F1 / B16F1）。
- **trace / span**（B18F1 / B19F1 / B20F1）。
- **mermaid 渲染工具链**（`mermaid-cli` / Playwright 等）——v1 零依赖、零出站。
- ~~节点别名解析~~（**C25 已正式作废**）——图导出只用构建期 / 运行期同一套内部节点名。
- **上游 `draw_mermaid` 的样式参数族**（`with_styles` / `curve_style` / `node_styles` /
  `frontmatter_config` 等）——v1 只交付确定性文本。
- **运行期跳转记录（原 DR-1）**——已由 2026-11-20 发起者裁定作废，改为上游静态声明。

---

## Assumptions

- **上游版本**：以 `langgraph 1.2.11` + 对应 `langchain-core` 为唯一对照；换版本 MUST 重新核实
  全部行号与差分断言（宪法原则 XI）。
- **图结构的冻结面**：`Node` / `Edge` / `Graph` 的字段、构造签名、不可哈希、元组容器保持不变；
  本 feature 仅**追加** `Graph.draw_mermaid()` 方法，并**经发起者追认**放宽 `Edge.condition`
  对节点声明边的非空要求（T-6）。
- **mermaid 消费方**：文本输出不需要上游的样式 / 主题参数；只要合法、确定、含节点名，
  即可被评审工具与 B23F1 消费。
- **动态目标的可见性**：完全由**静态声明**决定；运行 `invoke()` / `stream()` 不改变图。
  无声明 ⇒ 无节点声明边（与上游一致）。
- **零第三方运行时依赖**：mermaid 文本生成只用标准库；类型推断只用标准库
  `typing.get_type_hints` / `typing.get_origin` / `typing.get_args`。
- **固定脚本只读**：`harness/demo/target.py` MUST NOT 被本 feature 改动；本 feature 只保证其
  「图导出」环节可用；PNG 环节由 B23F1 闭环。
- **证据门禁**：与上游的每条语义对应 MUST 在 `research.md` / `contracts/upstream-parity.md` 标注
  版本 + `路径:行号`；行为断言 MUST 有实测支撑（禁止只读源码下断言）。
