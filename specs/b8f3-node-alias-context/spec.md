# Feature Specification: B8F3 · `context` 独立通道 + `RunConfig` 运行期接线（alias 已移除）

**Feature Branch**: `b8f3-node-alias-context`（目录名保留历史；本 feature 范围已收窄）

**Created**: 2026-11-20

**Status**: Draft

**Input**: User description: "B8F3 · 节点重命名别名 + `context` 独立通道。2026-11-20 clarify 拍板：**彻底移除 alias（原 C25）**，B8F3 只保留 `context` 独立通道（C21）与 `RunConfig` 运行期接线（C22）。前置依赖 B7F3。"

---

## 范围变更（2026-11-20 clarify 拍板）

> 本节是本 spec 的**权威范围声明**；提示词初稿 `harness/features/B8F3_节点别名与context通道.md`
> 中关于 C25 的段落保留为**历史事实**（原则 VIII），不再作为本 feature 的交付要求。

- **移除**：节点别名（alias）、**C25 节点命名别名（正式作废）**、`add_node(..., alias=...)`、
  `_NodeRecord.alias`、`GraphSpec` 的别名名表、`PregelTask.name` 的别名呈现、
  图导出 / `stream()` 的别名呈现。
- **契约编号**：C25 **正式作废**；编号**保留为历史墓碑、不复用**；C26 / C27 **不重编号**；
  **active 契约清单 = C1–C24 + C26–C27**；未来若重启 alias，MUST 使用**新契约编号**（如 C28）
  并重新论证。
- **保留**：`context` 独立通道（C21）与 `RunConfig` 四字段运行期接线（C22）。
- **行为**：`add_node(..., alias=...)` MUST 抛内置 `TypeError`（**不静默忽略**）；
  `_NodeRecord` / `_BuilderSpec` MUST NOT 再有 `alias` 字段。
- **理由**（用户 2026-11-20 拍板，逐字要点）：
  1. freechain 是**稳定、开箱即用的图集合**，不会频繁更改节点名；alias 的收益缺乏真实场景；
  2. alias 是之前软件设计时产生的「脂肪」，未经充分论证，导致今天返工；
  3. 没有 alias 可以与上游 `langgraph` 保持一致，并降低开发者心智负担；
  4. 「长痛不如短痛」：现在坚定移除，接受对既有 feature / 冻结面的修订成本。
- **验收判据收窄**：本 feature 只判定 **C21 / C22**；原验收判据 A3（C25）与提示词中的
  「软断言升级为硬断言」一条**作废**，改为「C25 用例与软断言一并移除」。
- **C25 的正式状态**：不是「v1 暂不实现」的注记，而是**从 active 契约清单正式移除**；
  历史文字保留在 Q8 / 立项书 / 宪法 changelog 中（原则 VIII）。
- **契约修订**：移除 alias 需要回溯修订 C25 与 B6F1 / B2F2 / B22F1 / B7F2 / B8F2 / B8F1 /
  验收脚本 / 测试；详见本 spec 的 **T-7** 与 **「契约修订：移除 alias」** 一节。

---

## 承接条款（上游 feature → 本 feature）

> 宪法「跨 feature 承接的接线通则」（v1.8.0；现行 1.16.0）：上游 feature 指名本 feature 的跨 feature 义务
> MUST 在本 spec 落成 **FR + 裁定**；**只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽判据**。

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B7F3 → B8F3** | **M2** | **`invoke` 终态与 `RunConfig` 的接线面**：`invoke` 已返回**完整状态**（schema 键集、无 `context` 键的位置）；`RunConfig` 已含 `context` 字段但运行期尚未读取。B8F3 MUST 在不改变 `invoke` 签名与终态形状的前提下完成 `context` 接线。 | `specs/b7f3-invoke-full-state/spec.md` · `src/freegraph/contracts/types.py:180-260` | FR-001 / FR-002 / FR-004 |
| **H-2** | **B8F1 → B8F3** | **M2** | **路由视图口径**：B8F1 的路由函数入参 = fresh 视图（当前值 + 本节点本次写入）⇒ `context` 通道（C21）**MUST NOT** 进入该视图；`path_map` 查表与别名无关（**alias 已移除**，查表仍用内部节点名）。 | `specs/b8f1-conditional-edges-fresh-read/spec.md` **下游承接 D-2** · `contracts/conditional-edge-contract.md` §3 | FR-006 / 裁定 4 |
| **H-3** | **B8F2 → B8F3** | **M2** | **流式事件的节点名口径**：`stream_mode="updates"` 的载荷键 = 节点名（内部名）；B8F3 **MUST NOT** 引入别名映射。alias 移除后，B8F2 的 D-1 自动满足：`stream()` 只消费内部节点名。 | `specs/b8f2-stream-modes/spec.md` **下游承接 D-1** · **H-10** · `contracts/stream-contract.md` | FR-013 / FR-014 |
| **H-4** | **B1F1 / B2F1 → B8F3** | **M1** | **`RunConfig` 类型已冻结**：`thread_id` / `context` / `metadata` / `tags` 四字段可读（C22）；另有 `configurable` / `max_concurrency` / `recursion_limit` / `run_name` / `run_id` 五个上游兼容字段。B8F3 MUST **保留全部九个字段**，MUST NOT 删除 / 改名 / 改语义。 | `src/freegraph/contracts/types.py:180-260` · `specs/b1f1-contracts-core/` · `specs/b2f1-contracts-protocols/` | FR-001 / 裁定 6 |
| **H-5** | **宪法 → B8F3** | **M2** | **C21 / C22 两条契约**：`context` 是独立通道、`RunConfig` 是运行配置载体；`context` MUST NOT 塞进 `configurable`。**C25 已正式作废，编号保留不复用；active 契约清单 = C1–C24 + C26–C27。** | 宪法原则 VII「active = C1–C24 + C26–C27」· `harness/reports/Q8-图运行时最小契约.md` §3.4 | FR-001…FR-010 / 裁定 1…6 |

### 撤回的承接（alias 相关）

| # | 原承接 | 处置 |
|---|---|---|
| **W-1** | **B6F1 → B8F3** D-3（B8F3 读取 `_NodeRecord.alias` 实现别名语义） | **撤回**；改为 **T-3**：B6F1 移除 `alias` 记录与 `add_node(alias=)` 参数 |
| **W-2** | **B7F2 → B8F3** D-3（B7F2 保留 `_BuilderSpec` 供 B8F3 读取 alias） | **撤回**；`_BuilderSpec` 保留本身继续服务其他用途，但不再承载 alias |
| **W-3** | **B8F2 → B8F3** D-1 的「别名在流式事件中的可见性」 | **收缩**为「流式事件只使用内部节点名」；alias 移除后自动成立，无需新映射 |
| **W-4** | **B22F1 → B8F3** 的「图导出别名归 B8F3」 | **撤回**；图导出继续使用内部节点名（**T-5** 移除相关注记） |

---

## 下游承接条款（本 feature → 下一棒）

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 |
|---|---|---|---|---|
| **D-1** | **B8F3 → B14F1** | **M3** | **`context` 不持久化**：本 feature **不**把 `context` 写入 checkpoint、**不**在恢复时从快照还原 `context`；恢复路径的 `context` 归属由 B14F1 按其 checkpoint 契约决定。B8F3 MUST NOT 预留「内存态 context 恢复」旁路。 | FR-009 / Out of Scope |
| **D-2** | **B8F3 → B18F1 / B19F1** | **M3** | **`context` 与 trace 的关系**：`context` 是节点只读运行期上下文，**不是** trace span 的 `context` 字段；span 的 `context` 由 B18F1 / B19F1 按 C23 定义。B8F3 MUST NOT 复用 `TraceSink` 的 `context` 字段承载 C21 的 `context`。 | FR-003 / FR-008 / 裁定 5 |
| **D-3** | **B8F3 → B14F1 / B15F1 / B16F1 / B18F1 / B19F1** | **M3** | **context 的 M3 边界**：本 feature 完成后，上述 feature MUST 以「`context` 已接线、alias 已移除」为前提；持久化侧（B14F1 / B15F1 / B16F1）MUST NOT 把 `context` 写入 checkpoint 或从快照恢复；可观测侧（B18F1 / B19F1）MUST NOT 复用 `Span.context` 承载 C21 的 `context`；任何 M3 feature MUST NOT 回退到 `configurable` 承载 context，也不得重新引入节点别名。 | FR-003 / FR-008 / FR-009 · 裁定 5 · 里程碑 |
| **D-4** | **B8F3 → 文档 / 验收面** | **M2** | **别名移除的收尾**：`harness/features/` 的历史提示词保留；但 `harness/demo/`、`README.md`、`tests/` 与已发布契约中的 alias 承诺 MUST 按 **T-2…T-7** 修订，MUST NOT 留下「可传 alias」的误导。 | 契约修订一节 |

---

## Clarifications

### Session 2026-11-20（本轮问询）

- Q: 是否保留节点别名（alias / C25）？ → A: **彻底移除 alias（原 C25）**；`add_node(..., alias=...)` 抛 `TypeError`；B8F3 只保留 `context` 独立通道 + `RunConfig` 运行期接线，并接受对 C25 / B6F1 / B2F2 / B22F1 / 验收脚本的冻结面修订。

### 既有设计裁定（2026-11-20 spec 阶段，本轮未变更）

> **纪律**：宪法原则 XI「上游有答案 ⇒ 照抄 ⇒ 不问用户」。`context` 的上游形态是
> `context=` + `Runtime.context`；freegraph 的 `RunConfig.context` 与 `state.context`
> 形态是已冻结的自研差异（X-1），不在本轮重新问询。alias 则因用户判断「无真实收益」
> 而整体移除。

#### Q1（`context` 的载体与「不塞进 `configurable`」）

→ **A：`RunConfig.context` 是唯一来源；运行期用独立的 run-scoped 私有载体传递。**

- `invoke()` / `stream()` 的 `config` 经既有 `resolve_config()` 归一为 `RunConfig`
  （`RunConfig` 原样返回；mapping ⇒ `RunConfig.from_dict(..., ignore_unknown=True)`；
  `None` ⇒ 空 `RunConfig`）⇒ 读 `run_config.context`。
- `context` **MUST NOT** 成为状态通道：不进 `GraphSpec.channels`、不进 `SchedulerState.channels`、
  不进 `_sparse_state`、不进 `_full_state`、不进 `invoke()` 返回字典、不进 `values` 流事件载荷。
- `context` **MUST NOT** 被写入 `RunConfig.configurable`；也 **MUST NOT** 从
  `configurable["context"]` 读取（freegraph 不提供 LangChain 的 `configurable` 语义）。
- 运行期载体 MUST 是**独立的 run-scoped 私有通道**（contextvar 或等价物），
  **MUST NOT** 改动 `run_super_step` / `run_super_steps` / `run_graph` 的既有签名。

落点：FR-001 / FR-002 / FR-003 / FR-007 · 裁定 1 · SC-001 / SC-003。

#### Q2（节点如何读到 `context`，同时不破坏 C4）

→ **A：`context is None` ⇒ 普通 `dict`；`context is not None` ⇒ 带只读 `.context` 的
`dict` 子类视图，映射内容仍是稀疏状态。**

- `getattr(state, "context", None)` MUST 返回本次运行的 `context`（**同一对象**）。
- 该视图 MUST 满足：
  - `isinstance(state, dict)` 为真；`dict(state)` == 原稀疏状态（键集 / 顺序 / 值不变）；
  - **不**出现 `"context"` 键；**不**参与归约；
  - `.context` 只读；其他未知属性按普通对象规则（`AttributeError`）。
- `context is None` 时节点入参 MUST 仍是**精确的 `dict`**（`type(state) is dict`）⇒
  B7F1 的 C4 / I-1 判据**逐字不变**。
- `context is not None` 时节点入参是 `dict` 子类 ⇒ **C4 的映射语义不变**（稀疏、
  `state.get(key, default)` 行为不变）；这是**新增能力**，不是放宽既有判据（见 **T-1**）。
- **路由函数**的 fresh 状态视图 MUST NOT 带 `context` 键，也 MUST NOT 带 `.context` 属性（H-2）。
- **路由函数的第二参 `config`** MAY 携带 `RunConfig.context`（它是用户交给 `invoke` / `stream` 的原始 config，不是 fresh 视图）；H-2 只禁止 `context` 进入 fresh 视图。此形态与上游「条件边可通过 Runtime 读 context」同义（P-03 / P-08）。

落点：FR-004 / FR-005 / FR-006 · 裁定 2 · SC-001 / SC-007。

#### Q3（`RunConfig` 的字段面）

→ **A：保留现有九字段，四字段（C22）语义写死；不新增 / 不删除。**

- 四字段：`thread_id`（会话标识，`str | None`）、`context`（运行期上下文，`Any`）、
  `metadata`（附加信息，`Mapping[str, Any]`）、`tags`（附加信息，`Sequence[str]` ⇒ 构造期
  冻结为 `tuple`）。
- 既有兼容字段：`configurable` / `max_concurrency` / `recursion_limit` / `run_name` /
  `run_id` 保留；本 feature 不改变其语义。
- `configurable["thread_id"]` 对 `resolved_thread_id()` 的优先级不变。
- `metadata` / `tags` / `thread_id` **MUST NOT** 被注入状态或 `context` 视图。

落点：FR-001 / FR-008 / 裁定 6 · SC-002。

#### Q4（alias 移除后的行为与失败信号）

→ **A：`add_node` 不再接受 `alias`；传入即 `TypeError`；C25 正式作废，编号保留不复用。**

- `StateGraph.add_node` 的签名 MUST NOT 含 `alias`；`_NodeRecord` / `_BuilderSpec` MUST NOT
  含 `alias` 字段。
- `add_node("agent", fn, alias="model")` MUST 抛内置 `TypeError`，消息**点名 `alias`**；
  具体措辞不冻结。**MUST NOT** 静默忽略（与上游 `**kwargs` 的静默忽略不同，见 **X-3**）。
- C25 在 Q8 / 立项书 / 宪法中的历史文字**保留**；但 MUST 追加注记：**C25 正式作废、
  编号保留不复用**；若未来重启 alias，须使用新契约编号（如 C28）并重新论证（**T-2**）。
- `harness/demo/graph_core.py` 的 `case_node_alias`、`harness/demo/README.md` 的 C25 软断言行、
  以及依赖它们的测试 MUST 移除 / 改写（**T-6**）。
- **理由**：留下「可传但没用」的关键字会让用户误以为别名有效；彻底移除比 no-op 更诚实。

落点：FR-011 / FR-012 / FR-013 / FR-014 / FR-015 · 裁定 3 · SC-004 / SC-012。

#### 裁定编号映射（本 spec 的唯一裁定编号表）

| # | 裁定 | 落点 |
|---|---|---|
| **裁定 1** | `context` 来源 = `RunConfig.context`；运行期用独立 run-scoped 私有载体；不塞 `configurable` | Q1 · FR-001 / FR-002 / FR-003 / FR-007 |
| **裁定 2** | `context is None` ⇒ 精确 `dict`；非 `None` ⇒ 带只读 `.context` 的 `dict` 子类（映射内容仍可变）；路由视图无 context | Q2 · FR-004 / FR-005 / FR-006 |
| **裁定 3** | alias 彻底移除：`add_node` 无 `alias`、`_NodeRecord` 无 `alias`、C25 正式作废且编号不复用 | Q4 · FR-011…FR-015 |
| **裁定 4** | `context` 不进入路由视图；`path_map` 查表与别名无关（alias 已移除） | H-2 · FR-006 |
| **裁定 5** | `context` 与 trace span 的 `context` 字段不是同一概念；不复用 `TraceSink.context` | D-2 · FR-003 / FR-008 |
| **裁定 6** | `RunConfig` 保留九字段；四核心字段语义写死；不新增 / 不删除 | Q3 · FR-001 / FR-008 |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 运行时上下文独立传递 (Priority: P1)

作为用户，我有一份「本次运行的上下文」（如当前用户 ID），希望节点能读到它，且不污染状态
（不进 `messages`、不参与归约）。

**Why this priority**: 这是 C21 的核心；上下文若进入状态，会破坏 schema / 归约 / checkpoint。

**Independent Test**: 用 `RunConfig(context={"user": "u1"})` 运行一张单节点图；节点内
`getattr(state, "context", None)` 读到 `{"user": "u1"}`；`invoke()` 返回的状态不含 `context` 键；
`values` 流事件的最后一个 `payload` 也不含 `context` 键。

**Acceptance Scenarios**:

1. **Given** `RunConfig(context={"user": "u1"})`，**When** 节点执行，
   **Then** 节点读到 `{"user": "u1"}`。
2. **Given** 同一次运行，**When** 查看 `invoke()` 返回字典，
   **Then** 键集 == schema 键集，**不含** `"context"`。
3. **Given** 同一次运行，**When** 消费 `stream(..., stream_mode="values")`，
   **Then** 每条 `payload` 都不含 `"context"`。
4. **Given** 节点返回状态写入，**When** 归约发生，**Then** `context` 不参与归约、不产生写入。
5. **Given** `context=None`（或未提供），**When** 节点执行，
   **Then** `getattr(state, "context", None)` 为 `None`，且节点入参是精确的 `dict`。

---

### User Story 2 - `context` 不被塞进 `configurable` (Priority: P2)

作为维护者，我希望 `context` 的位置是固定的（`RunConfig.context`），避免将来与 LangChain 的
`configurable` 语义混淆。

**Why this priority**: 这是 C21 与 C22 的职责边界；混淆会把 `langchain-core` 拖回依赖树。

**Independent Test**: 构造 `RunConfig(thread_id=..., context=..., metadata=..., tags=...)`；
四个字段均可读；`configurable` 保持独立空映射；节点侧 `context` 视图没有 freegraph 注入的
`configurable` 键。

**Acceptance Scenarios**:

1. **Given** `RunConfig(thread_id="thread-1", context={"user": "u1"}, metadata={"m": 1}, tags=["t1"])`，
   **When** 读取四字段，**Then** 值分别为 `"thread-1"` / `{"user": "u1"}` / `{"m": 1}` / `("t1",)`。
2. **Given** 同一 `RunConfig`，**When** 读取 `configurable`，**Then** 它是独立映射，
   **不**包含 `context`。
3. **Given** 节点侧 `context` 视图，**When** 检查键，**Then** 没有 freegraph 注入的
   `"configurable"` 键。
4. **Given** 用户只传 `configurable={"context": ...}`，**When** 运行，
   **Then** freegraph **不**把它当作 `context`（`context` 仍为 `None`）。

---

### User Story 3 - alias 被彻底移除 (Priority: P2)

作为维护者，我希望 `add_node` 不再有 `alias` 这个未经论证的关键字，避免用户误以为别名有效；
同时也让 freegraph 的 `add_node` 与上游保持同一套关键字口径。

**Why this priority**: 留下 no-op 关键字比移除更糟；它会误导用户并增加心智负担。

**Independent Test**: `add_node("agent", fn, alias="model")` 抛 `TypeError`；`_NodeRecord` 无
`alias` 字段；`case_node_alias` 与 README 的 C25 软断言行被移除；图导出 / `stream()` 只使用内部
节点名。

**Acceptance Scenarios**:

1. **Given** 任意构建器，**When** 调用 `add_node("agent", fn, alias="model")`，
   **Then** 抛内置 `TypeError`，消息点名 `alias`（具体措辞不冻结）。
2. **Given** 任意 `_NodeRecord`，**When** 检查字段，**Then** 不存在 `alias` 字段。
3. **Given** 一张普通图，**When** 运行 `invoke()` / `stream()` / `get_graph()`，
   **Then** 节点名始终是内部名，不出现别名映射。
4. **Given** `harness/demo/graph_core.py`，**When** 运行，
   **Then** 不再有 `case_node_alias`；README 不再有 C25 软断言行。

---

### User Story 4 - 路由与流式消费不受影响 (Priority: P3)

作为用户，我希望 `context` 接线不改变条件边路由、`path_map` 查表、`stream()` 的节点名口径。

**Why this priority**: 这是 C8 / B8F1 / B8F2 的既有语义；`context` 不能偷偷混入路由视图。

**Independent Test**: 条件边图中路由函数入参不含 `context` 键 / 属性；`stream(..., stream_mode="updates")`
的载荷键 = 内部节点名；最终状态与不带 `context` 时一致（除节点可读 context 外）。

**Acceptance Scenarios**:

1. **Given** 条件边图，**When** 路由函数执行，**Then** 其入参不含 `context`。
2. **Given** `stream(..., stream_mode="updates")`，**When** 消费事件，
   **Then** 载荷键 = 内部节点名。
3. **Given** `get_graph()`，**When** 导出，**Then** 节点 `id` / `name` = 内部节点名。

---

### Edge Cases

- `context=None` ⇒ 节点入参精确 `dict`；`context={}` / `context=0` / `context=""` ⇒ 非 `None`
  ⇒ 使用 `dict` 子类视图，`.context` 为对应对象。
- `context` 为任意对象（dict / dataclass / 自定义实例）⇒ 原样透传，不校验、不 coerce。
- `context` 中恰好有 `"context"` 键 ⇒ 仍是 `context` 的值；**不**把它写进状态字典。
- 用户修改 `context` 对象 ⇒ 节点读到的是同一对象（同一 run 内）；freegraph 不做防御性拷贝承诺。
- `stream()` 的 `values` 载荷 / `invoke()` 终态都无 `context` 键。
- 路由函数入参既无 `context` 键，也无 `.context` 属性。
- `RunConfig` mapping 形态 `{"context": {...}}` ⇒ 经 `from_dict` 落成 `RunConfig.context`。
- `configurable={"thread_id": "x"}` ⇒ `resolved_thread_id()` 仍优先取 `configurable` 值。
- `RunConfig` 的九个字段全部保留；四字段可读；`tags` 构造后为 `tuple`。
- `add_node(..., alias=...)` ⇒ `TypeError`（alias 已移除；不静默忽略）。
- `_NodeRecord` / `_BuilderSpec` 不再有 `alias` 字段；任何读取 alias 的代码 MUST 一并删除。
- `get_graph()` / `stream()` / `invoke()` 的节点名始终是内部名；无别名映射。
- 通过 `Command.goto` 触发的节点走**标准节点入参** ⇒ 读到同一 run 的 `context`。
- 通过 `Send` fan-out 触发的节点：`Send.arg` 是 `dict` 时同样包装为 context-bearing view；
  `Send.arg` 非 `dict` 时**原样传递**，不注入 `.context`（v1 边界；节点可自行从 `Send.arg` 读取）。
- 路由函数的第二参 `config` 可以是 `RunConfig(context=...)`；路由函数可从中读取 context，
  但其 fresh 状态视图仍无 `context`。
- C25 用例 / README 软断言行 / 依赖它们的测试被移除后，不得留下悬空引用。
- 无 `langchain*` / `langgraph*` / `langsmith*` import；不读环境变量；零出站。
- `harness/demo/graph_core.py` 的 C21 `context` 软断言升级为硬断言后全绿。

---

## Upstream Parity *(mandatory — 宪法 v1.12.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11** / `langchain-core` **1.7.6**（取证于 2026-11-20，
本仓库 `.venv` 实际安装版本）

### §1 逐条对照（P-01…P-11）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | `add_node` 的关键字面 | `langgraph/graph/state.py:667-682`（无 `alias`） | alias 移除后，freegraph 的 `add_node` 也**无 `alias`** | SAME | 移除 alias 后与上游一致 |
| P-02 | 传入 `alias=` 的失败信号 | 上游经 `**kwargs: Unpack[DeprecatedKwargs]` **静默忽略**（实测 **E-01**） | `add_node(alias=...)` ⇒ **`TypeError`** | STRICTER | 失败信号比上游更严；避免「可传但没用」的误导 ⇒ **X-3** |
| P-03 | 运行时 `context` 的载体 | `langgraph/pregel/main.py:3783-3843`（`invoke(..., context=...)`）· `langgraph/runtime.py:198`（`Runtime.context`）· 文档 `harness/docs/oss/python/langgraph/graph-api.md:999-1035` | `RunConfig.context`（C22）+ 节点侧 `state.context` 属性 | DIFF | 上游用 `context=` 参数 + `Runtime` 注入；freegraph 用自有 `RunConfig` + 已冻结的节点形态 ⇒ **X-1** |
| P-04 | `context` 不进入状态 | 实测 **E-02 / E-05**（`state` 键集无 `context`） | `context` 不进状态 / 归约 / `invoke` 终态 / `values` 载荷 | SAME | 只比「状态中无 context」这一可观察面 |
| P-05 | `context` 与 `configurable` 分离 | 上游 `context` 是独立参数，**不**要求塞进 `configurable`（`main.py:3783-3843`；文档 `graph-api.md:1012-1035`） | `RunConfig.context` 独立；`configurable` 不承载 context | SAME | 二者都拒绝「context 塞 configurable」 |
| P-06 | `RunConfig` vs `RunnableConfig` | 上游 `RunnableConfig` 含 `configurable` / `metadata` / `tags` 等（`langchain_core/runnables/config.py` 一族） | freegraph 自有 `RunConfig`（九字段，含四核心 C22 字段） | DIFF | C22 已冻结；freegraph 不复用 `RunnableConfig`（避免拖回 `langchain-core`）⇒ **X-2** |
| P-07 | `path_map` 查表用节点名 | `langgraph/graph/_branch.py:199-211`（按返回目的地解析；不解析别名） | `path_map` 查表用**内部节点名**；alias 已移除 | SAME | H-2；无别名解析 |
| P-08 | 路由函数看到的状态 | 实测 **E-05**（路由函数入参无 `context`） | 路由函数入参为 fresh 稀疏视图，**无** `context` 键 / 属性 | SAME | H-2；C8 fresh 读不变 |
| P-09 | `updates` 流事件的载荷键 | `langgraph/pregel/_io.py:118`· 实测 **E-03**（键 = 内部节点名） | `updates` 键 = 内部节点名 | SAME | alias 已移除；B8F2 口径不变 |
| P-10 | 图导出的节点名 | `langgraph/graph/state.py:1356-1374`· 实测 **E-04**（`Node.id` / `name` = 内部名） | `get_graph()` / `draw_mermaid` = 内部节点名 | SAME | alias 已移除；B22F1 口径不变 |
| P-11 | 零依赖 / 零环境变量 / 零出站 | 本 feature 不引入任何第三方依赖，不读环境变量 | 同宪法原则 I / II | SAME | 红线不变 |

### §2 实测基线（E-01…E-05 · `langgraph 1.2.11` · 取证于 2026-11-20）

| # | 实验 | 结果 |
|---|---|---|
| **E-01** | `StateGraph.add_node("agent", fn, alias="model")` | 上游**接受**该关键字（经 `**kwargs`），但**静默忽略**；图仍以 `agent` 登记 |
| **E-02** | `invoke({...}, context={"user":"u1"})`，节点签名 `(state, runtime: Runtime)` | 节点从 `runtime.context` 读到 `{"user":"u1"}`；`state` 键集不含 `context` |
| **E-03** | 同图 `stream(..., stream_mode="updates")` | 载荷键为 `agent`（不是 `model`）；alias 不参与 |
| **E-04** | 同图 `get_graph()` / `draw_mermaid()` | 节点 `id` / `name` 为 `agent`；mermaid 文本不出现 `model` |
| **E-05** | 条件边路由函数在 `invoke(..., context=...)` 下执行 | 路由函数入参键集不含 `context`；`context` 只能经 `Runtime` 取得 |

### §3 差分场景组 *(mandatory)*

> 编号承接 B8F2 的 `D-121…D-136` ⇒ 本 feature 使用 **D-137…D-144**。

| # | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 |
|---|---|---|---|
| **D-137** | `context` 不进入 `invoke` 终态 | 两侧最终状态的键集都**不含** `context`；状态值逐字相等 | SAME |
| **D-138** | 节点读取 `context` 的值 | 上游经 `Runtime.context`、freegraph 经 `state.context` 读到同一个 `{"user":"u1"}` | DIFF（**X-1**，仅访问形态） |
| **D-139** | `context` 不塞进 `configurable` | 两侧都不要求 / 不产生 `configurable.context`；freegraph 的 `RunConfig.configurable` 保持独立 | SAME |
| **D-140** | `RunConfig` 四字段 | freegraph 四字段可读且语义正确；上游以 `RunnableConfig` 的 `metadata` / `tags` / `configurable.thread_id` 表达 | DIFF（**X-2**，类型载体不同） |
| **D-141** | 无别名图的节点名 / 路由 | 两侧 `updates` 键 / 图节点名 / 最终状态都一致 | SAME |
| **D-142** | `add_node(..., alias=...)` | freegraph：`TypeError`；上游：静默忽略 | STRICTER（**X-3**） |
| **D-143** | `stream()` / `get_graph()` 的节点名 | 两侧都使用内部节点名；无别名映射 | SAME |
| **D-144** | 条件边路由视图 | 两侧路由函数入参都无 `context`；路由目标按内部节点名解析 | SAME |

⇒ **共 8 条**（D-137…D-144）⇒ **判词分布** = **SAME 5**（D-137 / D-139 / D-141 / D-143 / D-144）+
**DIFF 2**（D-138 / D-140）+ **STRICTER 1**（D-142）。

### §4 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | DIFF（必须自研区 ① / ③：零依赖边界 + 上游没有的形态） | `context` 的载体与访问形态 | 上游用 `invoke(..., context=...)` + `Runtime.context`（P-03）；freegraph 用自有 `RunConfig.context`（C22）并把 context 暴露为节点 `state.context` 属性（提示词已冻结该调用形态） | C21 / C22 · 本 feature |
| **X-2** | DIFF（必须自研区 ①：零依赖边界） | `RunConfig` 不复用 `RunnableConfig` | `RunnableConfig` 属 `langchain-core`，复用会把 `langsmith` 拖回依赖树；freegraph 自有 `RunConfig` 九字段 | C22 · B1F1 / B2F1 已冻结 |
| **X-3** | STRICTER（更严的失败信号） | `add_node(..., alias=...)` | 上游静默忽略（E-01）；freegraph 彻底移除 alias 后抛 `TypeError`，避免「可传但没用」的误导 | 本 feature · 用户 2026-11-20 拍板 |

### §5 破冻结面的回溯修订清单 *(本 feature 触发)*

| # | 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|---|
| **T-1** | **B5F2 / B7F1** 的 C4「节点入参是普通 `dict`」口径（`specs/b7f1-superstep-loop/contracts/superstep-contract.md` §I-1 · `tests/runtime/test_superstep_contract.py`） | ① 本 feature 的节点入参实现 ② 本 feature 的 C4 回归测试（无 `context` 时 `type(state) is dict`） ③ 相关契约注记 | **只补注记**：原 C4 判据**逐字不变**；追加「`context is not None` 时入参为带只读 `.context` 的 `dict` 子类（映射内容仍可变、映射语义不变）；`context is None` 时仍是精确 `dict`」 | 本 feature 的**唯一一次**追认（T-1…T-7 并入同一次） |
| **T-2** | **C25（节点别名）** · Q8 active 清单 · 宪法原则 VII · 立项书 §5.2 / §5.3 / §9.2 · 宪法 changelog | ① Q8 §3.4 的 C25 行与 active 清单 ② 宪法原则 VII + 版本 1.16.0 ③ `harness/proposals/立项书.md` §5.2 B8F3 行 / §5.3 C25 行 / §9.2 graph_core 描述 ④ `.specify/memory/constitution-changelog.md` v1.16.0 条目 | **正式移除**：C25 从 active 清单移除、编号保留不复用；C26/C27 不重编号；历史文字保留 + 注记；未来 alias 使用新编号（如 C28） | 并入 T-1 的同一次追认 |
| **T-3** | **B6F1** 的 `add_node(node, action=None, *, alias=None, defer=False, metadata=None)` 签名与 `_NodeRecord.alias` 记录（`specs/b6f1-stategraph-builder/spec.md` FR-010 / 裁定 7 / SC-014 · `contracts/builder-contract.md` · `data-model.md` · `tests/facade/test_stategraph_builder.py`） | ① 移除 `alias` 参数与 `_NodeRecord.alias` ② 撤回 B6F1 **D-3**（B8F3 读取 alias） ③ 更新 B6F1 的 FR-010 / 裁定 7 / SC-014 / P-02b / D-74 / X-1（D-74 迁移到本 feature D-142，B6F1 文档加墓碑注记） ④ 更新构建器测试 | **移除**：alias 不再是构建器参数 / 字段；其余签名（`defer` / `metadata` / 单 callable）不变 | 并入 T-1 的同一次追认 |
| **T-4** | **B2F2** 的 API 兼容矩阵与门面 `add_node(name, fn, *, alias=None)`（`specs/b2f2-public-api-facade/spec.md` · `contracts/facade-api.md` · `data-model.md` · `research.md`） | ① 门面签名移除 `alias` ② 兼容矩阵删除「新增 alias 关键字」行 ③ 删除「节点别名的运行时寻址 → B8F3」的行 | **移除**：`add_node` 只保留上游同名参数 + freegraph 既有 `defer` / `metadata`；不再承诺 alias | 并入 T-1 的同一次追认 |
| **T-5** | **B22F1** 的「别名归 B8F3 / v1 不解析别名」注记（`specs/b22f1-get-graph-mermaid/spec.md` H-8 / Out of Scope · `contracts/graph-export-contract.md` · `data-model.md`） | ① 删除「别名归 B8F3」的待办注记 ② 图导出继续用内部节点名（`name == id`） | **只补注记**：C25 已正式作废、编号不复用；图导出「`name == id`」的现有断言**不变** | 并入 T-1 的同一次追认 |
| **T-6** | **验收脚本 / README / 测试** 中的 C25 用例与软断言（`harness/demo/graph_core.py:31,563-602,660` · `harness/demo/README.md:25,70,83` · `tests/runtime/test_acceptance_script.py:59-64`） | ① 删除 `case_node_alias` 与 `main` 中的注册 ② 删除 README 的 C25 软断言行 / A10 行 ③ 更新 `test_acceptance_script.py` 中「保留 C25」的断言 | **移除**：C25 不再有软 / 硬断言；C21 的软断言仍按 FR-020 升级为硬断言 | 并入 T-1 的同一次追认 |
| **T-7** | **B7F2 / B6F1 / B8F2** 的 alias 交接注记（B6F1 D-3、B7F2 D-3、B8F2 D-1 的别名部分） | ① B6F1 / B7F2 / B8F2 的相关「下游承接」行 ② `CompiledGraph._builder_spec` 的 alias 用途说明 | **撤回 / 收缩**：B7F2 保留 `_BuilderSpec` 的用途不变（服务其他需求），但不再供 alias 读取；B8F2 的 D-1 收缩为「只用内部节点名」 | 并入 T-1 的同一次追认 |

> **追认次数**：本 feature 的**唯一一次**追认额度由 **T-1…T-7** **共同**使用
> （宪法 v1.8.0「每 feature ≤ 1 次」）⇒ 追认文字 MUST 落
> `harness/verification/B8F3/manual-verification.md` ⇒ **未追认前 MUST NOT 合入**。

---

## Requirements *(mandatory)*

### Functional Requirements

#### 运行期上下文（C21 / C22）

- **FR-001**: `RunConfig` MUST 保留 `thread_id` / `context` / `metadata` / `tags` 四个核心
  字段（C22）以及既有五个兼容字段；本 feature MUST NOT 删除 / 改名 / 改变其语义。
- **FR-002**: 运行期 MUST 从 `RunConfig.context` 读取上下文；mapping 形态
  `{"context": ...}` MUST 经 `RunConfig.from_dict` 落成 `RunConfig.context`。
  本 feature MUST NOT 新增 `invoke(..., context=...)` / `stream(..., context=...)` 关键字；
  `context` 只经 `RunConfig` / mapping 提供。
- **FR-003**: `context` **MUST NOT** 进入状态字典、schema 通道表、`GraphSpec.channels`、
  `SchedulerState.channels`、归约器、`invoke()` 返回字典、`values` 流事件载荷或 checkpoint。
- **FR-004**: 节点 MUST 能通过 `getattr(state, "context", None)` 读到本次运行的 `context`
  （同一对象）；`context is None` 时返回 `None`。该保证适用于**标准节点入参**；
  `Send.arg` 的边界见 Edge Cases。
- **FR-005**: `context is None` 时节点入参 MUST 是精确的 `dict`（`type(state) is dict`）；
  `context is not None` 时节点入参 MUST 是带只读 `.context` 属性的 `dict` 子类：映射内容 == 稀疏状态
  （键集 / 顺序 / 值不变），不带 `"context"` 键。
  两种情形都必须保持 C4 的 `state.get(key, default)` 语义。
- **FR-006**: 路由函数的 **fresh 状态视图** MUST NOT 含 `context` 键，也 MUST NOT 暴露
  `.context` 属性（H-2）；`context` MUST NOT 参与条件边求值。路由函数的**第二参 `config`**
  MAY 携带 `RunConfig.context`（原始 config · 与上游条件边可读 context 同义）。
- **FR-007**: `context` MUST NOT 被写入 `RunConfig.configurable`，也 MUST NOT 从
  `configurable["context"]` 读取；节点侧 `context` 视图 MUST NOT 被 freegraph 注入
  `"configurable"` 键。
- **FR-008**: `invoke()` 与 `stream()` MUST 使用同一套 `context` 解析口径；每次运行独立，
  `context` 不跨运行泄漏；`thread_id` / `metadata` / `tags` MUST NOT 被注入状态或
  `context` 视图。
- **FR-009**: 本 feature MUST NOT 实现 `context_schema`（不校验 / 不 coerce）；MUST NOT
  把 `context` 持久化到 checkpoint；恢复路径的 `context` 归属归 B14F1。
- **FR-010**: `context` 的运行期载体 MUST 是独立的 run-scoped 私有通道（contextvar 或
  等价物）；MUST NOT 改动 `run_graph` / `run_super_step` / `run_super_steps` /
  `_stream_tick` 的既有签名；MUST NOT 新增公开 L2 入口。

#### alias 移除（C25 作废）

- **FR-011**: `StateGraph.add_node` 的签名 MUST NOT 含 `alias`；传入
  `add_node(..., alias=...)` MUST 抛内置 `TypeError`，消息**点名 `alias`**（具体措辞不冻结）；
  **MUST NOT** 静默忽略。
- **FR-012**: `_NodeRecord` / `_BuilderSpec` MUST NOT 含 `alias` 字段；任何读取
  `_NodeRecord.alias` 的代码 MUST 一并删除。
- **FR-013**: C25（节点命名别名）MUST **正式作废**并从 active 契约清单移除；编号保留不复用；
  builder / compile / invoke /
  stream / 图导出 MUST NOT 实现任何别名语义。
- **FR-014**: `stream_mode="updates"` 的载荷键、`PregelTask.name`、`get_graph()` 的节点
  `id` / `name`、`draw_mermaid` 的标签 MUST 全部使用**内部节点名**；MUST NOT 出现别名映射。
- **FR-015**: `harness/demo/graph_core.py` 的 `case_node_alias`、`harness/demo/README.md` 的
  C25 软断言行、依赖它们的测试 MUST 移除 / 改写；MUST NOT 留下悬空引用。
- **FR-016**: alias 移除 MUST NOT 改变其它节点 / 边 / 路由 / 流式 / 图导出行为；既有
  「无 alias」图的全部可观察行为 MUST 逐字不变。

#### 质量与验收

- **FR-017**: 系统 MUST NOT import `langchain` / `langchain-core` / `langgraph` /
  `langsmith`；MUST NOT 读取环境变量；MUST 零出站。
- **FR-018**: L3 MUST 只依赖 L1 / L2（ARCH-1）；不新增公开 L2 入口；`freegraph.runtime.__all__`
  的符号集不变。
- **FR-019**: 本 feature MUST NOT 破坏 C4 / C6 / C8 / C11；C4 在无 `context` 时的
  `type(state) is dict` 判据逐字不变。
- **FR-020**: `harness/demo/graph_core.py` 的 C21 `context` 软断言 MUST 升级为硬断言
  （`soft(...)` ⇒ `check(...)` / `eq(...)`），并通过；`harness/demo/README.md` 的软断言清单
  MUST 同步更新（移除 C25 行，C21 不再列为软断言）。
- **FR-021**: `RunConfig` 的 mapping 形态 / `None` 形态 MUST 按既有 `resolve_config` 口径
  解析；失败信号 MUST 原类型 / 原消息直达调用方。
- **FR-022**: 契约修订 MUST 按 **T-2…T-7** 落地；C25 的历史文字 MUST 保留并追加
  「C25 正式作废、编号不复用」注记，MUST NOT 删除历史事实。

### Key Entities *(include if feature involves data)*

- **`RunConfig`**: 单次运行的配置载体（C22）；四核心字段 + 五兼容字段；`context` 是运行期
  上下文的**唯一来源**。
- **`context` 通道（C21）**: 运行期上下文的独立传递通道；不进入状态 / 归约 / 终态；
  不塞进 `configurable`；不持久化。
- **context-bearing node view**: `context is not None` 时节点收到的、带只读 `.context` 的 `dict` 子类；
  映射内容 = 稀疏状态；`.context` = 本次运行 context；不出现 `"context"` 键。
- **内部节点名（internal name）**: 唯一合法的节点名；用于构建器登记、边、条件边、
  `path_map` 查表、路由通道、`Command.goto` / `Send.node`、`PregelTask.name`、图导出。
- **已移除实体：节点别名（alias）**: v1 **不存在**；`_NodeRecord` 无 `alias` 字段；
  `add_node` 无 `alias` 关键字；C25 仅作为**历史墓碑**保留，编号不复用。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 节点通过 `getattr(state, "context", None)` 读到 `RunConfig.context` 的值；
  `invoke()` 返回的状态字典与 `values` 流事件载荷都**不含** `context` 键。
- **SC-002**: `RunConfig` 的 `thread_id` / `context` / `metadata` / `tags` 四字段可构造、
  可读，且语义分别为会话标识 / 运行期上下文 / 附加信息 / 附加信息（`tags` 为 `tuple`）。
- **SC-003**: 节点侧 `context` 视图中**不存在** freegraph 注入的 `configurable` 键；
  `RunConfig.configurable` 保持独立映射。
- **SC-004**: alias 已彻底移除：`add_node(..., alias=...)` 抛 `TypeError`；
  `_NodeRecord` / `_BuilderSpec` 无 `alias` 字段；builder / compile / invoke / stream /
  图导出均无别名语义；C25 不再作为 active 契约 / 验收项。
- **SC-005**: 条件边路由的 `path_map` 查表仍使用内部节点名；路由函数入参不含 `context`
  键 / 属性。
- **SC-006**: 无 `context` 的运行中，节点入参满足 `type(state) is dict`（C4 / I-1 逐字不变）；
  有 `context` 的运行中，节点入参满足 `isinstance(state, dict)` 且映射内容 == 稀疏状态。
- **SC-007**: 差分场景 **D-137…D-144** 全部可执行；SAME 5 / DIFF 2 / STRICTER 1 的判词与
  §3 一致。
- **SC-008**: 依赖门禁 / 零环境变量 / 零出站门禁全部通过；无 `langchain*` / `langgraph*` /
  `langsmith*` import。
- **SC-009**: `harness/demo/acceptance.py` 的 **core 套件（`graph_core.py`）在无 fake / 真实模型依赖**
  的情况下通过；C21 不再以 `soft(...)` 形式存在；C25 用例 / README 软断言行已移除。
  M2 的「固定脚本跑通（fake 模型）」由 **B25F1 / 固定脚本验收路径**负责，**不作为 B8F3 的独立判据**。
- **SC-010**: `harness/demo/graph_core.py` 的 C21 `context` 软断言升级为硬断言后通过；
  `harness/demo/README.md` 的软断言清单不再包含 C25，C21 不再列为软断言。
- **SC-011**: `harness/verification/B8F3/manual-verification.md` 存在且包含：`context` 实测输出、
  `RunConfig` 四字段实测、alias 移除实测（`TypeError` / 无 alias 字段）、零出站证据、
  T-1…T-7 追认文字；按宪法原则 V 完成人工门禁。
- **SC-012**: T-2…T-7 的契约修订全部落地：C25 历史文字有「正式作废、编号不复用」注记；B6F1 / B2F2 /
  B22F1 / 验收脚本 / 测试不再承诺 alias；仓库中不存在「可传 alias」的误导性文档。

## Assumptions

- **alias 不再属于 v1**：本 feature 的权威范围以「范围变更」一节为准；提示词初稿中的 C25
  段落只作历史保留。
- **freechain 稳定**：freechain 是开箱即用的图集合，不会频繁改节点名；未来若出现真实的
  改名兼容需求，另立 v2 feature 重新论证 alias，而不是在本 feature 里复活。
- **`context` 是任意对象**：不校验类型、不做 schema 校验、不做 coerce；`context_schema`
  参数保持「接受但本 feature 不使用」。
- **`context` 不复制**：同一 run 内节点读到的是 `RunConfig.context` 的同一对象；
  freegraph 不承诺防御性拷贝（与 `RunConfig` 的浅不可变口径一致）。
- **`context is None` 与 `context = {}` 不同**：前者是「未提供」，节点入参为精确 `dict`；
  后者是「提供了空映射」，节点入参为带 `.context` 的 `dict` 子类。
- **`RunConfig` 九字段冻结**：本 feature 只接线，不新增 / 不删除字段；`tags` 构造期转 `tuple`
  的既有行为不变。
- **`configurable` 不承载 context**：freegraph 不提供 LangChain 的 `configurable` 语义；
  用户传入的 `configurable` 只按既有 `resolved_thread_id()` 等口径使用。
- **`Send.arg` 非 `dict` 的 context 边界**：v1 只对标准节点入参与 `dict` 形态的 `Send.arg`
  注入 `.context`；非 `dict` 的 `Send.arg` 原样传递，不承诺 `getattr(state, "context", None)`。
- **上游版本锚点**：本 spec 的行为断言基于 `langgraph 1.2.11` / `langchain-core 1.7.6`；
  换版本 MUST 重新核实全部锚点。
- **契约修订需要发起者追认**：C25 / B6F1 / B2F2 / B22F1 的历史文字按「保留 + 注记」处理；
  追认文字落 `harness/verification/B8F3/manual-verification.md`。
- **C25 编号不复用**：C25 已正式作废；未来若重启 alias，MUST 使用新契约编号（如 C28）并重新论证，
  **MUST NOT** 复活 C25。

## Out of Scope

- 节点别名 / C25（**已正式作废、编号不复用**；未来若重启，使用新契约编号（如 C28）并重新论证）。
- `context_schema` 的声明式 schema、校验、coerce。
- checkpoint 中 `context` 的持久化与恢复（B14F1 及以后）。
- 子图（v2 / C26）。
- async / `astream`（v2 范围）。
- `Send` 的新语义（B11F1 已交付）。
- 前端 / UI 的 context 展示（B26）。
- 新增 `stream(filter=...)` 参数。

## 契约修订：移除 alias

> 本节是 T-2…T-7 的执行清单；具体任务拆分归 `/speckit.plan` / `/speckit.tasks`。
> 原则：**保留历史文字 + 追加注记**，不重写已发布事实；代码 / 签名 / 测试按「彻底移除」处理。

| # | 文件 / 面 | 必须的修订 |
|---|---|---|
| **R-1** | `harness/reports/Q8-图运行时最小契约.md` §3.4 · 宪法原则 VII · `.specify/memory/constitution-changelog.md` · `harness/prompts/init_constitution.md` · `harness/proposals/立项书.md` §5.2 / §5.3 / §9.2 | C25 行保留为历史墓碑；active 清单改为 C1–C24 + C26–C27；宪法升级 1.16.0 + changelog；立项书 B8F3 行改为 C21/C22、C25 作废；未来 alias 使用新编号（如 C28） |
| **R-2** | `specs/b6f1-stategraph-builder/spec.md` · `contracts/builder-contract.md` · `data-model.md` · `tests/facade/test_stategraph_builder.py` | 移除 `add_node(alias=...)` 与 `_NodeRecord.alias`；撤回 D-3；更新 FR-010 / 裁定 7 / SC-014 / P-02b / D-74 / X-1 / 别名测试；D-74 迁移到本 feature D-142，B6F1 文档加墓碑注记 |
| **R-3** | `specs/b2f2-public-api-facade/spec.md` · `contracts/facade-api.md` · `data-model.md` · `research.md` · `checklists/requirements.md` | 门面 `add_node` 移除 `alias`；兼容矩阵删除「新增 alias」与「别名寻址 → B8F3」行 |
| **R-4** | `specs/b22f1-get-graph-mermaid/spec.md` · `contracts/graph-export-contract.md` · `data-model.md` | 删除「别名归 B8F3 / 待解析」注记；图导出继续 `name == id`（内部名） |
| **R-5** | `specs/b7f2-compile/` · `specs/b8f2-stream-modes/` 的 alias 交接注记 | 撤回 B6F1/B7F2/B8F2 的 alias 下游承接；B8F2 D-1 收缩为「只用内部节点名」 |
| **R-6** | `harness/demo/graph_core.py` · `harness/demo/README.md` · `tests/runtime/test_acceptance_script.py` | 删除 `case_node_alias` / C25 软断言行 / 相关断言；C21 软断言升级为硬断言 |
| **R-7** | `harness/features/B8F3_节点别名与context通道.md` | **不改写**（历史提示词）；在 B8F3 spec 的「范围变更」中声明其 C25 部分已被本 spec 取代 |

## 交付物与验收联动

- **交付物**：
  - `context` 独立通道的运行期接线（`invoke` / `stream` / 节点只读视图）；
  - `RunConfig` 四核心字段的运行期接线（不改变九字段形状）；
  - alias 彻底移除（builder / compile / invoke / stream / 图导出 / 文档 / 测试）；
  - 单元测试 + `tests/differential/parity_probe.py` 的 **D-137…D-144**；
  - `harness/verification/B8F3/manual-verification.md`（含 T-1…T-7 追认文字）。
- **软断言升级**：`harness/demo/graph_core.py` 的 C21 context 软断言 MUST 升级为硬断言；
  C25 用例与 README 软断言行 MUST 移除。
- **人工门禁**：`harness/verification/B8F3/manual-verification.md` MUST 含 `context` /
  `RunConfig` 四字段 / alias 移除的实测输出、零出站证据、T-1…T-7 追认。
- **证据门禁**：上游锚点 = `langgraph 1.2.11` 的 `graph/state.py:667-682`（无 alias）·
  `pregel/main.py:3783-3843`（`context=`）· `runtime.py:198`（`Runtime.context`）·
  `pregel/_io.py:118`（updates 键）· `types.py:637-646`（`PregelTask`）；
  差异 MUST 标注「freegraph 自有 `RunConfig`，无 `configurable` 承载 context」。
- **里程碑**：本 feature 完成 = **M2（图定义与对外 API）整体结束**；后续解锁 **M3 全部
  feature**（B18F1 → B19F1 → B20F1 → B20F2 → B14F1 → B15F1 → B16F1）。

## 依据

- 立项书 §5.2（B8F3 行：C21/C22；C25 已正式作废）、§5.3（C21 / C22 / C25 历史状态；C25 编号保留不复用）、§6.2（M2 里程碑定义）、
  §9.2（验收脚本集的软/硬断言约定）、§9.1（门禁）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（active = C1–C24 + C26–C27；C25 正式作废、编号不复用）。
- 验收脚本：`harness/demo/graph_core.py`（`case_run_config_and_context` /
  `case_node_alias`（已移除））、`harness/demo/README.md`（软断言清单）。
- **2026-11-20 clarify 拍板**：用户明确选择「彻底移除 alias」，理由是 freechain 稳定、
  alias 缺乏真实高频改名场景、与上游对齐、降低心智负担；本 spec 的「范围变更」与
  「契约修订：移除 alias」是权威落点。
