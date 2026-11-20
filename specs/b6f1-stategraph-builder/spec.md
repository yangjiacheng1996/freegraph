# Feature Specification: B6F1 · `StateGraph` 构建器（同名同签名 · `path_map` 双形态）

**Feature Branch**: `b6f1-stategraph-builder`

**Created**: 2026-11-15

**Status**: Draft

**Input**: User description: "B6F1 · `StateGraph` 构建器 —— 交付与 LangGraph **同名同签名**的图定义 API：`StateGraph(schema)` / `add_node(name, fn)` / `add_edge(src, dst)` / `add_conditional_edges(src, path_fn, path_map)`。构建器只**记录并校验**节点、静态边、条件边与 schema 适配结果，产出可供 B7F2 `compile()` 消费的内部规格；本 feature **不执行**任何节点、**不实现** `compile()` / `invoke()` / `stream()`。判定 = `harness/demo/target.py` 第 142–155 行建图代码原样可用，且 `path_map` 的 list 与 dict 两形态各一例通过。"

> **2026-11-20 后续修订（C25 正式作废）**：B8F3 已正式作废 C25；`add_node` **不再接受 `alias`**，
> `_NodeRecord` **不再含 `alias`**。本 spec 中所有 `alias` 相关文字保留为**历史**（B6F1 当时
> 只记录、不实现），当前契约以 B8F3 spec / B2F2 facade / 本 spec 的后续修订块为准。
> 另：差分场景 **D-74**（alias）已**迁移到 B8F3 D-142**，不再由 `tests/differential/parity_probe.py`
> 承载；本 spec 的 D-74 行保留为历史墓碑，active 差分范围 = **D-50…D-73**。

---

## 承接条款（上游 feature → 本 feature）

> 宪法 v1.8.0「跨 feature 承接的接线通则」：上游 feature 指名本 feature 的跨 feature 义务
> MUST 在本 spec 落成 **FR + 裁定**；**只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽判据**。

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B4F1 → B6F1** | **M2** | **schema → 通道规格的唯一入口**：`StateGraph(schema)` 的 schema 解析 MUST 复用 `freegraph.runtime.parse_state_schema` / `build_channels`；MUST NOT 在构建器内另写一套 `TypedDict` / `Annotated` 解析 | `specs/b4f1-schema-reducer-parse/spec.md` FR-002 / FR-010 / 裁定 6 | FR-007 · 裁定 1 · SC-005 |
| **H-2** | **B7F1 → B6F1** | **M2** | **图规格形态**：构建器产出的内部规格 MUST 适配 `GraphSpec`（通道映射 + 保序节点表 + 边表 + 预留条件边字段）与 `NodeSpec`（订阅集 + 节点函数）；**校验职责**：B6F1 的 `validate()` / `_build_spec()` MUST 执行与 L2 `GraphSpec` 构造时校验**语义一致**的早失败检查；B7F2 构造 `GraphSpec` 时仍是**最终**校验门。⚠️ 「语义一致」的**范围仅限 V-1 / V-2 / V-3**；B9F1 FR-005 的 **`__parent__` 保留名检查**（`GraphSpec` 构造期，与 V-1 / V-2 / V-3 同族）与 **V-16**（多源目标为 `END` / 多源目标数 ≠ 1）**不在 B6F1 提前校验**，由 B7F2 构造 `GraphSpec` 时最终失败；构建器 MUST NOT 另造第三套图规格 | `specs/b7f1-superstep-loop/spec.md` FR-012 / FR-033 / 裁定 26 / 裁定 32 · `contracts/superstep-contract.md` §1 / §2.1 / §2.1.1 · `specs/b9f1-command-primitive/spec.md` 裁定 7 / FR-005（`__parent__` 保留名检查）· `specs/b7f4-multisource-join/spec.md` 裁定 5 / FR-017（V-16） | FR-007 · FR-016 · 裁定 2 · SC-005 |
| **H-3** | **B9F1 → B6F1** | **M2** | **节点返回形态透传**：`add_node(name, fn)` MUST 接受返回 `dict` / `Command` / `list[Command \| dict]` / `None` 的节点函数；构建器 MUST NOT 依据返回注解或运行时返回值另行拒绝 | `specs/b9f1-command-primitive/spec.md` 裁定 21 · `plan.md` R-7 | FR-009 · 裁定 7 · SC-007 |
| **H-4** | **B11F1 → B6F1** | **M2** | **`Send` 透传**：`add_node` / `add_conditional_edges` MUST 接受「返回 `Send` / `list[Send]`」的节点函数与条件边函数（透传 ⇒ 零代码改动）；MUST NOT 在构建层拒绝 | `specs/b11f1-send-fanout/spec.md` 下游承接 **D-6** · FR-001 / 裁定 12 | FR-009 · 裁定 7 · SC-007 |
| **H-5** | **B7F4 → B6F1** | **M2** | **`add_edge([a, b], c)` 接线**：`add_edge` MUST 接受列表 / 元组形态的源 ⇒ 直接记录为 `GraphSpec.edges` 的**元组键**；MUST NOT 另写屏障语义；`defer=True` 的节点专用屏障**不做**（偏离 X-03；路由通道类型差异另登记 X-7） | `specs/b7f4-multisource-join/spec.md` 下游承接 **D-1** · FR-001 / 裁定 14 / 15 | FR-003 · FR-011 · 裁定 6 · SC-005 |
| **H-6** | **B13F1 → B6F1** | **M2** | **静态断点透传**：构建器 MUST 允许用户把 `interrupt_before` / `interrupt_after` 带到 `compile()`（**构建器侧零动作**：不拦截、不新增字段、不改名、不丢弃；**正向透传由 B7F2 承担**）；对外接受形态与失败信号由 B7F2 的 `compile()` 入口层收紧 | `specs/b13f1-static-interrupt-recursion-limit/spec.md` 下游承接 **D-7** · FR-002 / 裁定 3 | FR-012 · 裁定 8 · SC-013 |
| **H-7** | **B3F1 → B6F1** | **M2** | **最小图可被构造**：承接 B3F1 延后的 FR-005 ③② 的「建图」环节 —— 本 feature MUST 让最小图**可被构造**；运行期断言在 B7F3 闭环。**只接线，MUST NOT 新增门禁编号**；红线不放宽 | `specs/b3f1-scaffold-ci-gates/spec.md` 裁定 22 | FR-015 · 裁定 11 · SC-001 / SC-015 |

---

## 下游承接条款（本 feature → 下一棒）

> 本 feature 冻结「构建器内部规格」这唯一跨 feature 接口。**只接线 · 逐条最小改动**。

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 |
|---|---|---|---|---|
| **D-1** | **B6F1 → B7F2** | **M2** | **`compile()` MUST 消费 `_build_spec()`**：B7F2 MUST 从 `StateGraph._build_spec()` 取得 `_BuilderSpec`，再适配为 L2 的 `GraphSpec` / `NodeSpec`；MUST NOT 重新解析 schema、MUST NOT 重造节点表 / 边表、MUST NOT 另立第三套图规格。`_BuilderSpec.edges` 中，**仅单源键（`str`）**指向 `END` 的边由 B7F2 在构造 `GraphSpec` 前过滤（B7F1 的 V-2 不接受 `END` 作为目标）；**多源键（`tuple[str, ...]`）**的 **V-16 形态（目标为 `END` 或目标数 ≠ 1）** MUST NOT 被过滤 / 提前拒绝，MUST 原样交给 `GraphSpec` 的 **V-16** 显式失败（B7F4 的「多源目标 MUST NOT 为 `__end__`」与「多源目标 MUST 恰为一个」）。`_BuilderSpec.nodes` / `node_records` 中的 `__parent__` 节点名同理由 B7F2 的 `GraphSpec` 构造期 **B9F1 FR-005 `__parent__` 保留名检查**最终失败。<br>**别名交接载体（D-3 · 已撤回）**：B7F2 仍保留完整 `_BuilderSpec` 供其他用途；**C25 正式作废后，B8F3 不再读取 `_NodeRecord.alias`**（该字段已由 B8F3 移除）。 | FR-007 · 裁定 2 / 6 · SC-005 |
| **D-2** | **B6F1 → B7F2 / B8F1** | **M2** | **条件边规格的跨层消费**：`_BuilderSpec.conditional_edges` 的字段（`source` / `branch` / `path` / `path_map` / `targets` / `route_channels`）逐字冻结。**B7F2（L3）MUST 保留 `_BuilderSpec.conditional_edges`（或其机械翻译出的普通映射）作为唯一 L3 交接载体**；在 B8F1 放宽 V-8 之前，B7F2 **MUST NOT** 填充 `GraphSpec.conditional_edges`。**B8F1（L2）MUST 只消费 L2 侧的 `GraphSpec.conditional_edges`，MUST NOT import `freegraph._stategraph` 或 `_ConditionalEdgeSpec`**，MUST NOT 重新归一化 `path_map`；B8F1 落地时把该映射填入 `GraphSpec.conditional_edges` 并承接 V-8 放宽。路由通道 `branch:to:<target>` 已由构建器建好，B8F1 MUST NOT 另起命名。<br>**普通映射形状（B6F1 内冻结）**：B7F2 MUST 把 `_BuilderSpec.conditional_edges` 机械翻译为**纯内建类型**的 `dict[str, tuple[dict[str, Any], ...]]`：外层 key = `source`；内层每个 dict 的 key / value 逐字为 `{"branch": str, "path": Callable[..., Any], "path_map": dict[Hashable, str] \| None, "targets": tuple[str, ...], "route_channels": tuple[str, ...]}`；顺序 = 登记顺序；`path_map` 已是归一化结果；内层 `"branch"` MUST 取自 `_ConditionalEdgeSpec.branch`（= `_branch_name(path)` 的登记结果），B7F2 MUST NOT 重新推断。B7F2 MUST 将该普通映射存放在 `CompiledGraph` 的私有字段（如 `_conditional_edges`）；B8F1 MUST 只读取该普通映射（或由 B7F2 以同形状参数传入），MUST NOT import `freegraph._stategraph` / `_ConditionalEdgeSpec` | FR-004 / FR-007 · 裁定 3 / 5 · SC-002 / SC-005 |
| **D-3** | **B6F1 → B8F3** | **M2** | **已撤回（C25 正式作废）**：B8F3 不再读取 `_NodeRecord.alias`；`add_node` 不再接受 `alias`，`_NodeRecord` 不再含 `alias`。历史 B6F1 的「只记录」语义保留为历史文字。 | FR-010（历史）· 裁定 7（历史）· SC-014（历史） |

---

## Clarifications

### Session 2026-11-15（设计裁定 · spec 阶段写死，plan 不得再翻）

- **Q1（schema 解析时机）**：`StateGraph(schema)` 构造时就解析 schema，还是等到构建期末？
  → **A：构造期只保存 `state_schema`（并初始化空的私有登记容器），不解析、不校验、
  无副作用**。理由：B2F2 的 FR-007 已冻结「`StateGraph(schema)` 构造 MUST 成功，
  MUST NOT 抛异常」；schema 的合法性属**构建期**检查，解析推迟到 `validate()` /
  `_build_spec()`。plain `dict` 等非法 schema 因此在构造时**不会**报错，只在构建期末
  报 `InvalidSchemaError`。
  ⇒ 落点：FR-001 / FR-007 · 裁定 1 · SC-005。
- **Q2（构建器 → B7F2 的内部规格形态）**：B7F2 从哪里取得构建结果？
  → **A：冻结为私有接口 `StateGraph._build_spec() -> _BuilderSpec`**，`_BuilderSpec` 是
  `freegraph._stategraph` 内的冻结数据类；**不导出、不进门面、不进 API 快照**。
  字段：`channels` / `nodes` / `node_records` / `edges` / `conditional_edges`。
  `channels` / `nodes` / `edges` 的形态与 B7F1 的 `GraphSpec` / `NodeSpec` 同构。
  ⇒ 落点：FR-007 · 裁定 2 · SC-005。
- **Q3（路由通道的落位与命名）**：条件边的路由通道由谁建、叫什么？
  → **A：构建器建；每个静态可判定目标一个 `EphemeralValue`，键名 `branch:to:<target>`**
  （与上游 `state.py:98` 的 `_CHANNEL_BRANCH_TO` 同款）。`END` **不建**通道；
  `path_map=None` 时按上游尝试从 `path` 的 `Literal[...]` 返回注解推断静态目标；
  推断不到 ⇒ **不建**路由通道（动态路由归 B8F1）。同一目标被多个
  分支引用时共享同一通道（首次出现顺序）。
  ⇒ 落点：FR-004 / FR-007 / FR-020 · 裁定 3 · SC-002 / SC-005。
- **Q4（校验时机与异常类型）**：哪些错误立即报、哪些到构建期末报？
  → **A：分两层，异常只用内置 `ValueError` / `TypeError`（schema 错误沿用 B4F1 的
  `InvalidSchemaError`）**。① **立即层**：见 `data-model.md` **BV-1…BV-9**（节点参数形态、
  保留名 / 保留字符、边类型、`path_map`、同名分支等）；② **构建期末层**：见 **BV-10…BV-12**
  与 FR-006（含 schema、源 / 入口 / 目标存在性、空节点表）；③ `validate(interrupt=...)`：
  见 **BV-13**。**MUST NOT** 在本条维护第二份逐项清单（避免与 BV 表漂移）。
  ⇒ 落点：FR-006 · 裁定 4 · SC-003 / SC-012。
- **Q5（`path_map` 归一化）**：list 与 dict 在内部如何统一？
  → **A：统一归一化为 `dict[Hashable, str] | None`**：list `["a", END]` ⇒
  `{"a": "a", END: END}`；dict 做浅拷贝；`None` ⇒ 按上游尝试从 `Literal[...]`
  返回注解推断，推断不到则保持 `None`。dict 的 key 可以是任意
  `Hashable`（路由函数返回值），value MUST 是 `str` 节点名或 `END`。
  ⇒ 落点：FR-004 · 裁定 5 · SC-002。
- **Q6（静态边的聚合口径）**：同一源多次 `add_edge` 怎么记？
  → **A：按源聚合、目标按首次出现顺序累积**。单源键保持 `str`；多源键为
  `tuple[str, ...]`（保序、去重）。完全相同的 `(源键, 目标)` 重复登记为**幂等**（只记一次）。
  ⇒ 落点：FR-003 / FR-016 · 裁定 6 · SC-011。
- **Q7（`add_node` 的单 callable 形态与附加关键字）**：是否支持 `add_node(fn)`？
  → **A：支持**（上游 `state.py:778-799` 同款：节点名取 `fn.__name__`，无 `__name__` 时取
  类型名；普通 callable 的 `.name` 不参与）。`defer` / `metadata` 接受并记录，但 `defer=True` 的
  **节点专用屏障不在本 feature 实现**（B7F4 的 X-03）。**`alias` 已于 2026-11-20 随 C25 正式作废；
  `add_node` 不再接受 `alias`。**
  ⇒ 落点：FR-002 / FR-010 / FR-011 · 裁定 7 · SC-014。
- **Q8（静态断点关键字）**：`interrupt_before` / `interrupt_after` 放构建器还是 `compile()`？
  → **A：仍是 `compile()` 的关键字**（B7F2 收紧形态并填入 `GraphSpec`）；构建器**不新增**
  同名字段、**不校验**、**不改名**、**不丢弃**。`add_node` / `add_edge` 的签名与行为不受其影响。
  ⚠️ `validate(interrupt=...)` 的**节点存在性校验**与上游同款（未知节点 ⇒ `ValueError`，
  见 FR-021 ③），与本条「compile 关键字不入构建器」不冲突。
  ⇒ 落点：FR-012 · 裁定 8 · SC-013。
- **Q9（其余上游同款构建方法）**：`add_sequence` / `set_entry_point` /
  `set_conditional_entry_point` / `set_finish_point` / `set_node_defaults` 是否在本 feature 交付？
  → **A：不在**。它们不属于宪法原则 III 的 7 项同名同签名硬要求，也不在 B6F1 的验收判据内；
  本 feature **只交付** 4 个核心方法与 `validate()`（构建期校验入口）。其余方法保持
  **显式 `NotImplementedError`**（MUST NOT 静默成功 / 返回 `None`），等待后续立项。
  ⇒ 落点：Out of Scope · 裁定 9 · SC-010。
- **Q10（接口载体的发起者确认）**：构建器把结果交给 B7F2 时，用私有 `_build_spec()` +
  `_BuilderSpec`、直接返回 `GraphSpec` + 独立分支规格，还是新增公开 `build()`？
  → **A：选项 A —— 私有 `_build_spec()` + 冻结 `_BuilderSpec`**。不新增公开 API，
  B7F2 只做一次机械适配。该选择已于 2026-11-15 澄清轮由发起者确认。
  ⇒ 落点：FR-007 · 裁定 2 · SC-005。
- **Q11（路由通道在内部规格中的位置）**：路由通道放 `_BuilderSpec.channels`、单独字段，
  还是完全不建？
  → **A：选项 A —— 放进 `_BuilderSpec.channels`，`_ConditionalEdgeSpec.route_channels`
  只引用它们**。B7F2 不再二次合并，B8F1 也不再建通道。该选择已于 2026-11-15 澄清轮
  由发起者确认。
  ⇒ 落点：FR-007 / FR-020 · 裁定 3 · SC-002 / SC-005。
- **Q12（更严失败信号的发起者确认）**：对上游静默降级/静默忽略的非法输入，freegraph
  是否统一改为显式早失败？
  → **A：选项 A —— 保持更严**：非法 `path_map` 容器 / 元素 / value ⇒ `TypeError`；
  空多源 source ⇒ `ValueError`；条件边 `source` 非 `str`、单源边 `end_key` 非 `str`
  ⇒ `TypeError`；缺 `action` / 多传 `action` ⇒ `TypeError`。该选择已于 2026-11-15
  澄清轮由发起者确认。
  ⇒ 落点：FR-003 / FR-004 / FR-002 · 偏离登记 X-2 / X-4 · 差分 D-56 / D-58 / D-59 /
  D-62 / D-63 / D-64 / D-66。

### 裁定编号映射（本 spec 的唯一裁定编号表）

| 裁定 | 内容 | 来源 |
|---|---|---|
| **裁定 1** | 构造期只保存 schema，不解析；schema 解析在 `validate()` / `_build_spec()` | Q1 · H-1 |
| **裁定 2** | 冻结私有接口 `_build_spec() -> _BuilderSpec`；字段与 `GraphSpec` / `NodeSpec` 同构 | Q2 · **Q10（发起者确认选项 A）** · H-2 · D-1 |
| **裁定 3** | 条件边路由通道 `branch:to:<target>`（`EphemeralValue`）放进 `_BuilderSpec.channels`；`END` 不建；`None` 推断不到则不建 | Q3 · **Q11（发起者确认选项 A）** · H-2 · D-2 |
| **裁定 4** | 两层校验：立即层 / 构建期末层；只用 `ValueError` / `TypeError`（schema 用 B4F1 异常） | Q4 · FR-006 |
| **裁定 5** | `path_map` 统一归一化为 `dict[Hashable, str] \| None` | Q5 · FR-004 |
| **裁定 6** | 静态边按源聚合；单源 `str`、多源 `tuple`；目标保序去重；相同边幂等 | Q6 · H-5 · D-1 |
| **裁定 7** | 支持 `add_node(fn)`；`defer` / `metadata` 记录；**`alias` 已随 C25 正式作废**；`defer` 屏障不实现；返回形态透传 | Q7 · H-3 / H-4 · D-3（已撤回） |
| **裁定 8** | 静态断点关键字仍属 `compile()`；构建器不新增 / 不改名 / 不丢弃 | Q8 · H-6 |
| **裁定 9** | 只交付 4 个核心方法与 `validate()`；其余上游同款构建方法保持显式未实现 | Q9 · Out of Scope |
| **裁定 10** | 构建期不执行任何用户函数；`path` / 节点函数 / 归约器均只在 `_build_spec()` 中被**持有**，不被调用 | FR-008 / FR-009 |
| **裁定 11** | B6F1 只交付「最小图可构造」（建图环节）；G22「场景②」的运行期断言由 B7F3 点亮；本 feature MUST NOT 新增门禁编号 | H-7 · B3F1 裁定 22 |

### 引文差异（提示词初稿 vs 本 spec）

| # | 差异 | 处置 |
|---|---|---|
| **引文差异 1** | 提示词 §4 FR-002 只写 `add_node(name, action)`，但 `_stategraph.py` 的冻结签名与上游同款还含 `defer` / `metadata`，且支持单 callable 形态 | **裁定 7 / Q7**：签名按已冻结的上游同款保留；核心验收只要求 `(str, Callable)`；`alias` 已于 2026-11-20 随 C25 正式作废 |
| **引文差异 2** | 提示词 §4 FR-006 要求「缺少起点」在构建期报错，但未指定入口方法；`target.py` 不调用 `validate()` | **裁定 4 / Q4**：`validate()` 是构建期校验入口；`_build_spec()` 复用同一校验，B7F2 调 `compile()` 时必然触发 ⇒ 错误仍早于运行期 |
| **引文差异 3** | 提示词 §7 把「路由通道」列为关键实体，但未指定通道命名 | **裁定 3 / Q3**：命名冻结为上游同款 `branch:to:<target>`；`END` 与 `None` 不建通道 |
| **引文差异 4** | 提示词 §10 写「4 个方法 + 构建期校验」，而 `_stategraph.py` 把其余上游同款方法也标注为「由 B6F1 交付」 | **裁定 9 / Q9**：本 feature 只交付 4 个核心方法与 `validate()`；其余保持显式未实现，并在 Out of Scope 登记 |
| **引文差异 5** | 提示词 FR-005 要求 `START` / `END` **可作节点名**；本 spec 反转为保留名失败 | **裁定 4 / P-03 / E-18**：按上游 `state.py:804-805` 与宪法原则 XI，`START` / `END` 仅作边哨兵；`add_node` 传入即 `ValueError` |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 原样写出验收脚本的建图代码 (Priority: P1)

作为项目发起者，我希望 `harness/demo/target.py` 的建图段落（第 142–155 行）**一字不改**
就能执行，不抛 `AttributeError` / `TypeError`。

**Why this priority**: 这是本 feature 的唯一最高判据（提示词 P1 / A3 / SC-001），也是
MVP 六项最小交付集的第 1 项。

**Independent Test**: 把 `target.py:142-155` 的建图语句原样放进测试（节点函数用本地
fake 替身、schema 用标准 `TypedDict`），断言全部调用成功、构建器记录了 2 个节点、
2 条静态边与 1 条条件边。

**Acceptance Scenarios**:

1. **Given** 标准 `TypedDict` schema 与两个用户节点函数，**When** 依次执行
   `StateGraph(schema)` / `add_node` × 2 / `add_edge(START, ...)` /
   `add_conditional_edges(..., ["tool_node", END])` / `add_edge(..., ...)`，
   **Then** 全部调用成功并返回可用于链式调用的构建器。
2. **Given** 同一段建图代码，**When** 调用 `validate()`，**Then** 成功返回构建器自身，
   且不执行任何节点函数。
3. **Given** 同一段建图代码，**When** 检查构建器内部规格，**Then** 节点名、边、条件边
   与用户声明**逐项一致**。

---

### User Story 2 - 条件边的两种 `path_map` 都能用 (Priority: P1)

作为用户，我既会用 list 形态声明分支目标（`["tool_node", END]`），也会用 dict 形态把
「返回值 → 节点名」显式映射（`{"hit": "node_a"}`）。

**Why this priority**: `path_map` 双形态是宪法原则 III 第 5 项的硬要求，也是验收脚本与
`graph_core.py` 的既有用法。

**Independent Test**: 分别用 list 与 dict 各建一张图，断言两者都构建成功；内部规格里
list 被归一化为 `{"tool_node": "tool_node", "__end__": "__end__"}`，dict 被浅拷贝且
键值保持用户声明。

**Acceptance Scenarios**:

1. **Given** `add_conditional_edges("llm_call", should_continue, ["tool_node", END])`，
   **When** 构建，**Then** 成功；分支目标集合 = `{"tool_node", END}`。
2. **Given** `add_conditional_edges("r", router, {"hit": "hit", "miss": "miss"})`，
   **When** 构建，**Then** 成功；分支映射逐字等于用户 dict（浅拷贝）。
3. **Given** 同一条件边源上有两个不同函数名的分支，**When** 构建，**Then** 两者都被记录，
   顺序 = 登记顺序。
4. **Given** 同一条件边源上有两个同名函数的分支，**When** 构建，**Then** 立即抛
   `ValueError` 并在消息中点名源节点与分支名。

---

### User Story 3 - 建图错误能被早点指出 (Priority: P2)

作为用户，我把节点名写错（边指向不存在的节点）、重复登记节点名、或忘记从 `START`
出发时，希望 freegraph 在**构建期**报错，而不是运行时才炸。

**Why this priority**: 提示词 P3 / SC-003 要求 3 类错误各有一例且消息可定位；早失败是
本 feature 相对上游的主要增量之一。

**Independent Test**: 三类错误各建一个反例，断言异常类型为 `ValueError` 且消息含问题
节点名 / 「entrypoint」等可定位信息。

**Acceptance Scenarios**:

1. **Given** 已登记节点 `a`，**When** 再次 `add_node("a", fn)`，**Then** 立即抛
   `ValueError`，消息含 `a`。
2. **Given** 已登记节点 `a` 且已 `add_edge(START, "a")`，**When**
   `add_edge("a", "missing")` 后调用 `validate()`，**Then** 抛 `ValueError`，消息含
   `missing`（先用有效入口隔离「未知目标」这一单一错误）。
3. **Given** 有节点但没有任何 `START` 入口边 / 条件入口，**When** 调用 `validate()`，
   **Then** 抛 `ValueError`，消息含 `entrypoint` 与 `START`。
4. **Given** 已建立有效 `START` 入口，且条件边 `path_map` 指向不存在的节点，
   **When** 调用 `validate()`，**Then** 抛 `ValueError`，消息点名源节点、分支与目标节点。

---

### User Story 4 - 构建器可链式调用 (Priority: P2)

作为用户，我希望能连续写 `builder.add_edge(...).add_edge(...)`，不必每步重新接收对象。

**Why this priority**: 宪法原则 III 第 4 项明确要求 `add_edge` 链式返回；提示词 SC-004
要求该形态可判定。

**Independent Test**: `add_edge(START, "a").add_edge("a", END)` 不抛异常；三个构建方法
的返回值都 `is` 同一个构建器。

**Acceptance Scenarios**:

1. **Given** 已登记节点 `a`，**When** `add_edge(START, "a").add_edge("a", END)`，
   **Then** 链式成功，两条边都被记录。
2. **Given** 任意构建方法成功返回，**When** 比较返回值与调用者，**Then** 两者是同一对象。

---

### User Story 5 - 构建器产物可被 `compile()` 消费 (Priority: P2)

作为 B7F2 的开发者，我希望构建器产出**唯一、冻结、可直接适配**的内部规格，而不是让我
重新解析 schema 或猜节点 / 边的存储形态。

**Why this priority**: 提示词 SC-005 要求本 feature 与 B7F2 的接口形态写死；否则 B7F2
会另造一套图规格，破坏分层。

**Independent Test**: 调用 `_build_spec()`，断言返回对象含 `channels` / `nodes` / `edges` /
`conditional_edges`，且 `channels` / `nodes` / `edges` 可原样用于构造 L2 的 `GraphSpec`
（`END` 目标先过滤）。

**Acceptance Scenarios**:

1. **Given** 一张含节点、静态边、条件边的图，**When** 调用 `_build_spec()`，
   **Then** 返回 `_BuilderSpec`，其中 `nodes` 的每个值是 B7F1 的 `NodeSpec`，
   `channels` 的每个值是 B5F1 的 `Channel` 子类实例。
2. **Given** 同一 `_BuilderSpec`，**When** 过滤 `END` 目标后构造 `GraphSpec`，
   **Then** 构造成功（无 V-1 / V-2 / V-3）；`conditional_edges` 字段保持空。
3. **Given** 构建器后续再添加节点 / 边，**When** 对比之前取得的 `_BuilderSpec`，
   **Then** 之前的快照**不受影响**。

---

### User Story 6 - 构建期不执行任何用户代码 (Priority: P3)

作为用户，我希望在 `add_node` / `add_edge` / `validate()` 期间，我的节点函数、路由函数
与归约器都**不**被调用，以免构建图时产生副作用。

**Why this priority**: 构建器与运行时的职责边界是本 feature 的硬边界；提前执行会让
「建图」与「跑图」不可区分。

**Independent Test**: 使用带调用计数器的节点函数 / 路由函数 / 归约器；完成全部构建与
`validate()` 后，计数器全部为 0。

**Acceptance Scenarios**:

1. **Given** 节点函数带调用计数，**When** 完成建图与 `validate()`，**Then** 计数为 0。
2. **Given** 路由函数带调用计数，**When** 完成建图与 `validate()`，**Then** 计数为 0。

---

### Edge Cases

- **构造期传入 B4F1 拒绝的 schema 形态**（如普通 `dict` / 模型实例）：构造成功
  （B2F2 冻结）；直到 `validate()` / `_build_spec()` 才由 B4F1 抛 `InvalidSchemaError`。
  **B4F1 的接受 / 拒绝面以其 spec 与 `contracts/schema-parse-contract.md` 为准**
  （含 2026-11-12 上游对齐 P3 的「是类 + 有 `__annotations__`」放宽；两者若仍有差异，
  属 B4F1 范围，本 feature 不另立第二套 schema 判定）。
- **空 `TypedDict`**：合法；通道映射为空；只要节点表非空且有入口边，构建仍可成功。
- **空节点表**：在源 / 入口 / 目标校验通过后（如 `START -> END` 空图），
  `validate()` / `_build_spec()` MUST 抛 `ValueError`（点名「节点表为空」· X-5）；
  若同时缺少入口，则按上游优先级先报入口错误。
- **重复节点名**：`add_node` 立即抛 `ValueError`，消息含该名字。
- **`START` / `END` 作节点名**：`add_node` 立即抛 `ValueError`（保留名）。
- **节点名含 `|` / `:`**：`add_node` 立即抛 `ValueError`（上游保留字符）。
- **节点名不是 `str` 且不是 callable**：抛 `TypeError`。
- **`str` 节点缺少 `action` / `action` 不可调用**：抛 `TypeError`。
- **单 callable 形态**：`add_node(fn)` 使用 `fn.__name__`；无 `__name__` 时使用类型名
  （普通 callable 的 `.name` **不参与**取名，上游同款）；两者都取不到时抛 `ValueError`；
  若同时传了非 `None` 的 `action`，抛 `TypeError`。
- **`alias`（已作废）**：C25 已于 2026-11-20 正式作废；`add_node` 不再接受 `alias`，`_NodeRecord` 不再含 `alias`。
- **`defer=True`**：接受并记录；**不实现**节点专用屏障（B7F4 的 X-03），
  MUST NOT 因此改变边 / 触发语义。B6F1 的路由通道对 defer 目标仍用 `EphemeralValue`；
  上游对 defer 目标用 `LastValueAfterFinish`，该差异登记为 **X-7**（已知不支持），
  由 B7F4 X-03 在 defer 落地时一并处理。
- **`metadata`**：接受并原样记录；本 feature 不消费。
- **单源边指向尚不存在的节点**：允许先登记边、后登记节点（上游同款）；到
  `validate()` / `_build_spec()` 才报错。
- **`start_key` 为 `int` / `None` 等非法类型**：`add_edge` 立即抛 `TypeError`
  （上游同族；差分 D-69）。
- **多源边的源不存在**：`add_edge` 立即抛 `ValueError`（上游同款）。
- **多源边的源为空列表 / 空元组**：立即抛 `ValueError`（比上游更严，见 X-2）。
- **多源边的目标为 `END`**：本 feature 接受并记录；B7F2 **只过滤单源键的 `END` 目标**，
  **多源键的 `END` 目标 MUST 原样保留**，由 L2 `GraphSpec` 的 V-16 在 B7F2 / B7F4 阶段
  显式失败（不属于本 feature 的屏障语义）。
- **多源边的目标数 ≠ 1**：本 feature 接受并记录（同一多源源键可累积多个目标）；B7F2
  构造 `GraphSpec` 时由 **V-16** 显式失败（B7F4 的「多源目标 MUST 恰为一个」）。
- **节点名为 `__parent__`**：本 feature 不校验（上游 `add_node` 同款接受）；B7F2 构造
  `GraphSpec` 时由 **B9F1 FR-005 的 `__parent__` 保留名检查**显式失败（与 V-1 / V-2 / V-3 同族）。
- **`END` 作边源**：立即抛 `ValueError`。
- **`START` 作边目标**：立即抛 `ValueError`。
- **重复登记完全相同的静态边**：幂等（只记一次）。
- **同一源登记不同目标**：按登记顺序累积。
- **自环边**（`a -> a`）：合法，构建期不判环。
- **条件边源不存在**：`validate()` / `_build_spec()` 抛 `ValueError`，消息含源节点名。
- **条件边源为 `START`**：合法，并视为入口声明。
- **条件边源为 `END`**：`validate()` / `_build_spec()` 抛 `ValueError`（`END` 不是节点）。
- **`path_map` 为 `None`**：合法；按上游尝试从 `path` 的 `Literal[...]` 返回注解推断静态
  目标；推断不到则 `targets=()`、`route_channels=()`，不建路由通道，动态路由归 B8F1。
- **`path_map` 为 list**：元素 MUST 为 `str`；归一化为 `{name: name}`。
- **`path_map` 为 dict**：key 任意 `Hashable`；value MUST 为 `str`；浅拷贝。
- **`path_map` 为其它类型**（tuple / set / str 等）：立即抛 `TypeError`（比上游更严，见 X-2）。
- **`path_map` 的 list / dict 为空**：合法；无静态目标；不建路由通道。
- **`path_map` 目标为 `END`**：允许；`END` 不建路由通道，但保留在归一化映射中。
- **`path_map` 目标为不存在的节点**：`validate()` / `_build_spec()` 抛 `ValueError`，
  消息点名源、分支与目标。
- **同一源上两个同名分支**：`add_conditional_edges` 立即抛 `ValueError`。
- **同一源上多个不同名分支**：合法，按登记顺序记录。
- **`path` 不可调用**：立即抛 `TypeError`。
- **条件边函数返回 `Send` / `list[Send]`**：构建器不检查返回注解、不拒绝（H-4）。
- **节点函数返回 `Command` / 命令列表 / `None`**：构建器不检查返回注解、不拒绝（H-3）。
- **`validate()` 成功后再添加节点 / 边**：允许；下一次 `_build_spec()` 重新计算快照。
  B6F1 无 `compiled` 状态，因此**不产生**上游 `validate()` 之后的 `compiled=True` warning
  （范围边界，见 P-09）。
- **`validate()` 失败后**：构建器状态保持不变；用户修正后可再次调用。
- **`_build_spec()` 两次调用**：返回**结构等价但彼此独立**的快照（通道按类型 / 归约器 / key
  比较；节点、边、分支逐字相等）；第二次不受第一次调用方修改影响。
- **节点函数 / 路由函数 / 归约器**：构建期 MUST NOT 被调用。
- **`interrupt_before` / `interrupt_after`**：构建器不接受、不存储、不改名；`compile()`
  关键字由 B7F2 处理。
- **`add_sequence` / `set_entry_point` / `set_conditional_entry_point` / `set_finish_point` /
  `set_node_defaults`**：本 feature 不交付；保持显式 `NotImplementedError`。
- **`compile()`**：本 feature 不交付；仍为显式 `NotImplementedError`，消息点名 B7F2。

---

## Upstream Parity *(mandatory — 宪法 v1.9.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11**（取证于 2026-11-15 ·
`/home/ctyun/workspace/github/freegraph/.venv/lib/python3.11/site-packages/langgraph`）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | `StateGraph` 类与构造参数名 | `langgraph/graph/state.py:131`（class）· `:216-225`（`state_schema` / `context_schema` / `input_schema` / `output_schema`） | 同名同签名；`state_schema` 是唯一必填位置参数；其余可选 | SAME | 宪法原则 III 第 2 项 |
| P-02 | `add_node(node, action, *, defer, metadata, ...)` 与单 callable 形态 | `langgraph/graph/state.py:667-682`（签名）· `:778-799`（单 callable 取名） | 同名同签名；支持单 callable | SAME | 宪法原则 III 第 3 项 · 实测 E-21 |
| P-02b | `add_node(..., alias=...)` | `langgraph/graph/state.py:667-682`（`add_node` 签名无 `alias`；运行时经 `**kwargs` 静默忽略） | **C25 已于 2026-11-20 正式作废**；freegraph 的 `add_node` 不再接受 `alias` ⇒ `TypeError` | STRICTER | B8F3 · 实测 E-24 · D-74 |
| P-02c | 普通 callable 的 `.name` **不参与**取名 | `langgraph/graph/state.py:778-799`（实测 E-21） | 同款：`__name__` → 类型名；`.name` 忽略 | SAME | 上游首段已把 `node` 固定为 `str` ⇒ 第二段不再取 `.name` |
| P-03 | 重复节点名 / 保留节点名 / 保留字符失败信号 | `langgraph/graph/state.py:802-811`（`Node ... already present` / `... is reserved` / 保留字符）· `langgraph/_internal/_constants.py:87-89`（`\|` / `:`）· 实测 E-18 | `add_node` 立即抛 `ValueError`，消息点名节点 | SAME | 早失败且与上游类型一致 |
| P-03b | 缺 `action` / 单 callable 形态同时传 `action` | `langgraph/graph/state.py:800-801`（上游缺 `action` 抛 `RuntimeError`）· `:782-799`（单 callable 时忽略 `action`） | 缺 `action` / 多传 `action` ⇒ 立即 `TypeError` | STRICTER | 用统一的用户输入错误类型替代上游 `RuntimeError`，且不静默忽略 `action` ⇒ X-4 |
| P-03c | `action` 不可调用 / `node` 非 `str` 非 callable | `langgraph/_internal/_runnable.py:579`（`coerce_to_runnable` 抛 `TypeError: Expected a Runnable, callable or dict`） | 立即抛 `TypeError` | SAME | 异常类型一致；消息不冻结 |
| P-04 | `add_edge(start_key, end_key) -> Self` 与多源源 | `langgraph/graph/state.py:928`（签名）· `:951-966`（单源）· `:969-979`（多源） | 同名同签名；单源 `str`、多源 `list` / `tuple`；链式返回 `Self` | SAME | 宪法原则 III 第 4 项 |
| P-04b | 空的多源 source（`[]` / `()`） | `langgraph/graph/state.py:969-979`（空循环后仍登记 waiting edge · 实测 1.2.11 接受） | 立即抛 `ValueError` | STRICTER | 空的「多源汇合」没有语义，早失败优于静默登记 ⇒ X-2 |
| P-04c | 单源边的 `end_key` 非 `str` | `langgraph/graph/state.py:958`（上游不校验 `end_key` 类型，直接登记） | 立即抛 `TypeError` | STRICTER | 非法目标值会让错误推迟到上游 `validate()` / `compile()`（`state.py:1261` 调 `validate()`） ⇒ X-2 |
| P-04d | 非法 `start_key` 类型（既非 `str` 也非 list / tuple） | `langgraph/graph/state.py:951-979`（迭代非可迭代对象 ⇒ `TypeError: 'int' object is not iterable` · 实测 E-22） | 立即抛 `TypeError` | SAME | 异常类型与上游一致；消息不冻结 · D-69 |
| P-05 | 边的 `END` 源 / `START` 目标失败信号 | `langgraph/graph/state.py:951-955` · `:969-977` · 实测 E-19 | `add_edge` 立即抛 `ValueError` | SAME | 与上游同款 |
| P-06 | `add_conditional_edges(source, path, path_map) -> Self` | `langgraph/graph/state.py:982-989`（签名）· `:1018-1027`（保存分支） | 同名同签名；`path_map` list / dict / None | SAME | 宪法原则 III 第 5 项 |
| P-06b | 条件边 `source` 非 `str` | `langgraph/graph/state.py:1008-1025`（上游把 `source` 直接作为 `branches` 键；`validate()` 才报未知源） | 立即抛 `TypeError` | STRICTER | 非法源键会让错误推迟到构建期末 ⇒ X-2 |
| P-06c | 非 callable `Runnable` 作为 `path` | `langgraph/graph/state.py:1018-1019`（`coerce_to_runnable` · 实测 E-23） | 仅接受 callable；非 callable ⇒ 立即 `TypeError` | DIFF（范围边界） | 零 langchain 约束 ⇒ X-6 |
| P-07 | `path_map` list / dict 归一化 | `langgraph/graph/_branch.py:89-120`（`from_path`）· `:98-101`（list → dict） | list 归一化为 `{name: name}`；dict 浅拷贝；None 保持 | SAME | 与上游同构 |
| P-07b | `path_map=None` 时按 `Literal[...]` 返回注解推断目标 | `langgraph/graph/_branch.py:102-114`（`get_type_hints` + `Literal` 展开） | 仅当返回注解为 `Literal[...]` 时归一化为 `{name: name}`；推断不到保持 `None`、不报错 | SAME | 与上游同款 |
| P-07c | `path_map` 的 list 元素 / dict value 非 `str` | `langgraph/graph/_branch.py:96-101`（上游只做 `{name: name}` / `dict.copy()`，不校验元素类型） | 立即抛 `TypeError` | STRICTER | 非法目标值会让错误推迟到上游 `validate()` / `compile()` ⇒ X-2 |
| P-08 | 同一源上同名分支重复 / 分支名推断 | `langgraph/graph/state.py:1022-1025`（`Branch with name ... already exists`）· `langgraph/_internal/_runnable.py:313-319`（lambda 不取 `<lambda>` · 普通 callable 的 `.name` 不参与） | `add_conditional_edges` 立即抛 `ValueError`；分支名 = `__name__`，lambda / 无名 ⇒ `condition` | SAME | 与上游同款 · 实测 E-21 |
| P-09 | 构建期末的边 / 条件边 / 入口 / `interrupt` 节点校验 | `langgraph/graph/state.py:1129-1175`（`validate`）· `:1138-1145`（源 / 入口）· `:1147-1168`（目标）· `:1168-1174`（`interrupt` 节点）· `:1175`（`compiled=True`） | `validate()` / `_build_spec()` 抛 `ValueError`，消息点名问题节点；`validate(interrupt=...)` 对未知节点抛 `ValueError`；顺序 = 源 → 入口 → 目标（空节点表见 P-14） | SAME（校验顺序 / 失败信号） | 构建器提供同名 `validate()`；顺序与上游 `validate()` 一致。⚠️ 上游 `validate()` 另设 `compiled=True`（之后 `add_node` / `add_edge` 会 warning）⇒ B6F1 无 compile 状态，不复制该副作用（范围边界，不影响校验判据） |
| P-10 | `path_map` 非法容器类型 | `langgraph/graph/_branch.py:96-116`（非 dict / list 落入 else 分支：无 `Literal` 时 `ends=None`；有 `Literal` 时反而按注解推断） | 立即抛 `TypeError` | STRICTER | 上游静默降级 / 静默推断不可接受 ⇒ X-2 |
| P-11 | 构建器内部规格 | `langgraph/graph/state.py:1242-1247` / `:1374-1399`（`compile()` 读取自身 `nodes` / `edges` / `branches`） | freegraph 冻结 `_build_spec() -> _BuilderSpec` 供 B7F2 消费 | DIFF（分层接缝） | L3 构建器与 L2 运行时物理分层 ⇒ X-3（原则 XII 形态优化） |
| P-12 | 静态断点关键字 | `langgraph/graph/state.py:1177-1188`（`compile(..., interrupt_before=, interrupt_after=)`） | 构建器不拦截；`compile()` 由 B7F2 接受 | SAME | H-6 · D-7 |
| P-13 | 条件边路由通道的类型与 guard（非 defer） | `langgraph/graph/state.py:1525-1530`（非 defer 用 `EphemeralValue(Any, guard=False)`） | `EphemeralValue(key="branch:to:<target>", value_type=Any, guard=False)` | SAME | 与上游**非 defer** 路由通道同款；`guard=False` 允许一步内多写取末值。该行为面由 B5F1 的 `EphemeralValue` 差分覆盖；B6F1 只验证构造形态 |
| P-13b | `defer=True` 目标的路由通道类型 | `langgraph/graph/state.py:1525-1530`（defer 用 `LastValueAfterFinish(Any)`） | B6F1 因不实现 defer 屏障，统一用 `EphemeralValue` | DIFF（已知不支持） | defer 屏障不在 v1 本 feature 实现 ⇒ B7F4 X-03 同源；本 feature 登记 **X-7**，B7F4 MUST 在其 defer 落地时一并处理 |
| P-14 | 空节点表 / `START -> END` 空图 | `langgraph/graph/state.py:1138-1168`（实测 E-20） | 空节点表 ⇒ `ValueError` | STRICTER | 与 L2 `GraphSpec` V-3 一致 ⇒ X-5 |

> **实测覆盖说明**：P-03 / P-05 分别由 E-18 / E-19 支撑；P-02c / P-08 的「普通 callable
> 的 `.name` 不参与取名」由 E-21 支撑；P-02b / D-74 的 alias 拒绝形态由 E-24 支撑（C25 作废后 freegraph `TypeError`）；
> P-06c 的 Runnable 行为由 E-23 支撑；P-14 由 E-20 支撑；P-13 的非 defer 行为面由 B5F1
> 覆盖，P-13b 的 defer 差异登记 X-7。换版本时 MUST 一并重跑。

### 差分场景组 *(mandatory)*

> **落点**：`tests/differential/parity_probe.py` ⇒ CI 的 Linux 全量档真跑
> （上游缺席即 `skip` · 沿用 B5F2 的「缺席即 skip」纪律）。本 feature 的差分只做
> **构建 / 校验**，不执行节点。

| # | 场景 | 断言（构建成功 / 失败 + 异常类型 / 可观察记录） | 判词 |
|---|---|---|---|
| D-50 | target 风格的建图（2 节点 + `START` 边 + list `path_map` + 回边） | 两侧 `validate()` 均成功；节点名 / 边数一致 | SAME |
| D-51 | dict 形态 `path_map` | 两侧 `validate()` 均成功；归一化映射一致 | SAME |
| D-52 | 重复节点名 | 两侧均抛 `ValueError`；消息均含重复名 | SAME |
| D-53 | 静态边指向不存在的节点（先建立有效 `START` 入口） | 两侧 `validate()` 均抛 `ValueError`；freegraph 消息含目标名 | SAME |
| D-54 | 缺少 `START` 入口 | 两侧 `validate()` 均抛 `ValueError`；消息含 `entrypoint` / `START` | SAME |
| D-55 | 链式调用 `add_edge(...).add_edge(...)` | 两侧均成功且返回同一 builder | SAME |
| D-56 | `path_map` 为 tuple（路由函数返回注解**不含** `Literal`） | 上游静默接受并保持 `ends=None`；freegraph 立即 `TypeError` | STRICTER（X-2） |
| D-57 | 多源边 `add_edge(["a", "b"], "c")` | 两侧均接受；freegraph 记录元组键 `("a", "b") -> ("c",)` | SAME |
| D-58 | `add_node("a")` 缺 `action` | 两侧均失败；上游 `RuntimeError`，freegraph `TypeError` | STRICTER（失败信号更明确 · X-4） |
| D-59 | `add_edge([], "a")` 空多源 source | 上游接受（静默登记无效汇合）· freegraph 立即 `ValueError` | STRICTER（X-2） |
| D-60 | `path_map=None` 且 `path` 返回注解为 `Literal[...]` | 两侧推断出的目标集合一致 | SAME |
| D-61 | `validate(interrupt=["nope"])` 未知节点 | 两侧均抛 `ValueError`；freegraph 消息含 `nope` | SAME |
| D-62 | `add_edge("a", 123)` 单源 `end_key` 非 `str` | 上游接受；freegraph 立即 `TypeError` | STRICTER（X-2） |
| D-63 | `add_conditional_edges(123, router, ["a"])` `source` 非 `str` | 上游接受并把错误推迟到 `validate()`；freegraph 立即 `TypeError` | STRICTER（X-2） |
| D-64 | `path_map=["a", 3]` / `{"x": 3}` 元素或 value 非 `str` | 上游接受；freegraph 立即 `TypeError` | STRICTER（X-2） |
| D-65 | 多源边 `add_edge(["a", "b"], END)` | 构建期两侧均接受并记录；freegraph 保留元组键的 `END` 目标 | SAME（构建期；下游 V-16 属 B7F4 的 STRICTER · D-1） |
| D-66 | `add_node(fn, fn2)` 单 callable + action | 上游接受并静默忽略 action；freegraph 立即 `TypeError` | STRICTER（X-4 · E-11） |
| D-67 | `add_node(START, fn)` / `add_node(END, fn)` | 两侧均 `ValueError`；消息含 `reserved` | SAME（P-03 · E-18） |
| D-68 | `add_edge(END, "a")` / `add_edge("a", START)` | 两侧均 `ValueError` | SAME（P-05 · E-19） |
| D-69 | `add_edge(123, "a")` 非法 `start_key` | 两侧均 `TypeError` | SAME（FR-003 ⑤ · E-22） |
| D-70 | 普通 callable 仅有 `.name`、无 `__name__` 时取名 | 两侧均忽略 `.name`：节点名取类型名、分支名取 `condition` | SAME（P-02c / P-08 · E-21） |
| D-71 | 缺入口 + 未知目标 | 两侧均先报入口错误（消息含 `entrypoint` / `START`） | SAME（FR-006 新顺序） |
| D-72 | 空节点 + `START -> END` | 上游通过；freegraph `ValueError` | STRICTER（X-5 · E-20） |
| D-73 | 非 callable `Runnable` 作为 `path` | 上游接受并使用 `.name`；freegraph 立即 `TypeError` | DIFF（X-6 · 范围边界 · E-23） |
| D-74 | `add_node(..., alias="model")` | **2026-11-20 起 tombstone**：C25 作废后该场景迁移到 **B8F3 D-142**，不再由 `parity_probe.py` 承载；上游仍静默忽略（E-24） | STRICTER（X-3 · E-24 · 已迁移） |

### 偏离登记 *(三类 + 已知不支持（DIFF）· 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | 必须自研区（上游没有） | `add_node(..., alias=...)` | C25 已于 2026-11-20 正式作废（编号不复用）；freegraph 不再接受 `alias`；上游签名无 `alias`、运行时静默忽略（E-24） | B8F3 · C25 tombstone · 差分 D-74 |
| **X-2** | 更严失败信号 | `path_map` 非 list / dict / None、list 元素 / dict value 非 `str` ⇒ `TypeError`；条件边 `source` 非 `str`、单源边 `end_key` 非 `str` ⇒ `TypeError`；空多源列表 ⇒ `ValueError` | 上游对非 dict/list 的 `path_map` **不报错**（无 `Literal` 时保持 `None`；有 `Literal` 时反而按注解推断），对非 `str` 的 source / end_key / path_map 元素**静默接受**并把错误推迟到 `validate()` / `compile()`，会让拼错的图「看起来建好了」；freegraph 选择显式早失败 | 本 feature 内闭合 · **Q12 发起者确认选项 A（含同类非法输入）** · 差分 D-56 / D-59 / D-62 / D-63 / D-64 |
| **X-3** | 形态优化（原则 XII） | `_build_spec() -> _BuilderSpec` 内部规格 | 上游 `compile()` 直接读自身字段（`langgraph/graph/state.py:1242-1247` / `:1374-1399`）；freegraph 的 L3 构建器与 L2 运行时物理分层 ⇒ 必须有冻结的内部规格载体，否则 B7F2 会重造第三套形态 ⇒ 这是**形态最优**而非「上游缺失能力」；Q10 发起者 2026-11-15 已确认选项 A | B7F2（B8F1 经 L2）· 本 spec D-1 / D-2 |
| **X-4** | 更严失败信号 | `add_node` 缺 `action` / 单 callable 形态同时传 `action` ⇒ `TypeError` | 上游缺 `action` 抛 `RuntimeError`，单 callable 时静默忽略 `action`；freegraph 统一用 `TypeError` 明确拒绝，避免「参数被静默忽略」 | 本 feature 内闭合 · **Q12 发起者确认选项 A** · 差分 D-58 / D-66 |
| **X-5** | 更严失败信号 | 空节点表 ⇒ `ValueError` | 上游 `START -> END` 空图可通过 `validate()`；freegraph 的 L2 `GraphSpec` V-3 要求节点表非空，且空图无可执行语义 ⇒ 提前显式失败。`validate()` 顺序已与上游一致，本项仅保留「空表更严」 | 本 feature 内闭合 · 差分 D-72 · E-20 |
| **X-6** | 必须自研区（零依赖 duck-typing 边界） | 非 callable `Runnable` / Runnable-like 对象 | freegraph MUST NOT import langchain / langchain-core；只接受**普通 callable**（`__call__`）。上游对 Runnable 的 `.get_name()` / `.name` 取值不承载；非 callable 对象不承载 | 本 feature 内登记 · 差分 D-73 |
| **X-7** | 结构差异（DIFF · 已知不支持） | `defer=True` 目标的路由通道类型：freegraph 用 `EphemeralValue`；上游用 `LastValueAfterFinish` | defer 节点屏障不在 v1 本 feature 实现（B7F4 X-03 同源）；freegraph 只接受并记录 `defer=True`，不改变路由通道类型 ⇒ 不伪装成已实现 | 本 feature 只记录 · 由 **B7F4 X-03** 在 defer 落地时一并处理 · 差分 D-50…D-74 不含该运行期行为 |

### 破冻结面的回溯修订清单

本 feature **不破**任何既有公开契约面：

- `freegraph.graph` 的 7 个导出符号不变；
- `StateGraph` 的公开方法签名不变（B2F2 快照仍成立）；
- B7F1 的 `GraphSpec` / `NodeSpec` 签名与语义不变；
- B4F1 / B5F1 的解析与通道接口不变。

**既有测试口径更新（非公开冻结面 · 按宪法 v1.11.0 记录）**：

- `tests/facade/test_facade.py::test_constructor_has_no_side_effect`：`vars(graph)` 从
  `{"_schema"}` 变为含私有登记容器（FR-001）；测试断言同步更新，公开属性仍为零。
- `tests/facade/test_facade.py::TestNotWired`：三个构建方法不再抛 `NotImplementedError`，
  测试收窄到 `compile()` / 其余未交付方法。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001（构造器）**：系统 MUST 提供 `StateGraph(state_schema, context_schema=None, *,
  input_schema=None, output_schema=None)`，**恰一个必填位置参数**（C1 / 宪法原则 III 第 2 项）。
  ① 构造期 MUST 只保存 `state_schema`（`context_schema` / `input_schema` / `output_schema`
  MUST 一律忽略，不落实例属性），并初始化空的私有登记容器
  （`_nodes` / `_edges` / `_conditional_edges` / `_branch_names`）；MUST NOT 解析 schema、
  MUST NOT 校验图结构、MUST NOT 调用任何用户函数、MUST NOT 产生任何副作用（不读环境变量、
  不做 I/O、不起线程）。`vars(graph)` 的 key 集合 MUST 恰为
  `{"_schema", "_nodes", "_edges", "_conditional_edges", "_branch_names"}`，
  MUST NOT 出现任何公开属性。
  ② **第三个**位置参数 MUST 抛 `TypeError`（B2F2 冻结面；第二个位置参数 `context_schema`
  仍合法）。
  ③ 构造期 MUST NOT 抛因 schema 内容导致的异常。

- **FR-002（节点登记）**：系统 MUST 提供
  `add_node(node, action=None, *, defer=False, metadata=None) -> Self`（`alias` 已随 C25 正式作废）。
  ① `node` 为 `str` 时，`action` MUST 可调用且不是 `None`；否则 `TypeError`。
  `node` 为 callable 时，`action` MUST 为 `None`（否则 `TypeError`），节点名取
  `node.__name__`，无 `__name__` 时取类型名；均取不到 ⇒ `ValueError`（上游
  `state.py:778-799` · 实测 E-21：普通 callable 的 `.name` 不参与取名）。
  ② 非 `str` / 非 callable 的 `node` ⇒ `TypeError`。
  ③ 重复节点名 ⇒ 立即 `ValueError`（消息含节点名）；`node == START` 或 `node == END`
  ⇒ 立即 `ValueError`（保留名）；节点名含 `|` 或 `:` ⇒ 立即 `ValueError`
  （上游保留字符 · `langgraph/_internal/_constants.py:87-89`）。
  ④ MUST 原样记录 `action` / `defer` / `metadata`（`metadata` 按 FR-018 做
  浅拷贝）；MUST NOT 调用 `action`、
  MUST NOT 检查其返回注解。本 feature **不校验** `defer` / `metadata` 的运行时
  类型（如 `defer="yes"`、非 Mapping 的 `metadata`）⇒ 只原样记录；
  `alias` 已随 C25 正式作废，不再接受。
  ⑤ 返回 `Self`（链式）。

- **FR-003（静态边）**：系统 MUST 提供
  `add_edge(start_key, end_key) -> Self`，`start_key` 可为 `str` / `list[str]` / `tuple[str, ...]`，
  `end_key` 为 `str`。公开签名注解 MUST 保持 `start_key: str | list[str]`
  （B2F2 快照）；`tuple[str, ...]` 是运行时接受形态，MUST NOT 因此改写注解。
  ① `END` 作 `start_key` ⇒ 立即 `ValueError`；`START` 作 `end_key` ⇒ 立即 `ValueError`。
  ② 单源边 MUST 允许「先登记边、后登记节点」（上游同款）；端点存在性到构建期末校验。
  ③ 多源边 MUST 接受列表 / 元组；每个源 MUST 已登记且不是 `END`，目标 MUST 已登记或为
  `END`，否则立即 `ValueError`；空列表 / 空元组 ⇒ 立即 `ValueError`。
  ④ 记录口径 MUST 按源聚合：单源键为 `str`，多源键为 `tuple[str, ...]`（保序、去重）；
  目标按首次出现顺序累积；完全相同的 `(源键, 目标)` 重复登记 MUST 幂等。多源键的目标
  MAY 累积多个（上游 `add_edge(starts, end)` 可对同一起点集合多次调用）；目标数 ≠ 1
  不在本层拒绝，由 B7F2 的 `GraphSpec` **V-16** 显式失败（B7F4）。
  ⑤ `start_key` 既非 `str` 也非 `list` / `tuple` ⇒ 立即 `TypeError`（与上游同族 ·
  SAME · E-22 / D-69）；`end_key` 非 `str` ⇒ 立即 `TypeError`（更严 · X-2 / P-04c）。
  ⑥ 返回 `Self`（链式）。

- **FR-004（条件边）**：系统 MUST 提供
  `add_conditional_edges(source, path, path_map=None) -> Self`。
  **公开签名注解 MUST 保持 `list[str] | dict[str, str] | None`（B2F2 快照）**；运行时
  dict key 可为任意 `Hashable`（见 ④），MUST NOT 因此改写公开注解（与 FR-003 的
  `tuple` 源运行时形态同款）。
  ① `source` MUST 为 `str`；`path` MUST 可调用，否则 `TypeError`。`source` 可为
  `START`；`END` 不是合法源，构建期末 `ValueError`。
  ② `path_map` MUST 支持 **list** 与 **dict** 两形态（C7 / 宪法原则 III 第 5 项），
  另接受 `None`；其它类型 ⇒ 立即 `TypeError`。
  ③ list 元素 MUST 为 `str`，否则 `TypeError`；归一化为 `{name: name}`，保序。
  ④ dict 的 key 可为任意 `Hashable`，value MUST 为 `str`，否则 `TypeError`；做浅拷贝。
  ⑤ `None` ⇒ MUST 按上游尝试从 `path` 的返回注解推断：仅当返回注解为 `Literal[...]`
  时归一化为 `{name: name}`；取不到 / 非 `Literal` / 推断异常 ⇒ 保持 `None`，MUST NOT 报错。
  ⑥ 分支名取 `path.__name__`；当无 `__name__` 或为 `<lambda>` 时取 `"condition"`
  （上游 `langgraph/_internal/_runnable.py:313-319` 同款 · 实测 E-21：普通 callable 的
  `.name` 不参与取名）；同一 `source` 上分支名重复 ⇒ 立即 `ValueError`。
  ⑦ MUST 记录 `source` / `branch` / `path` / 归一化后的 `path_map`；MUST NOT 调用 `path`。
  ⑧ 返回 `Self`（链式）。

- **FR-005（`START` / `END`）**：系统 MUST 接受 `START` 作为静态边 / 条件边的**源**，
  接受 `END` 作为静态边 / 条件边的**目标**；其值 MUST 分别为 `'__start__'` / `'__end__'`
  （C9）。二者 MUST NOT 被登记为节点（`add_node` 保留名失败）。
  `START` 作静态边目标、`END` 作静态边源 ⇒ 立即 `ValueError`（FR-003 ①）；
  `END` 作条件边源 ⇒ 构建期末 `ValueError`；`START` 作条件边目标 ⇒ 构建期末
  `ValueError`（`START` 不是节点且不是 `END`）。

- **FR-006（构建期校验与顺序）**：系统 MUST 在**构建期**（`add_*` 当时或 `validate()` /
  `_build_spec()` 时）按以下**顺序**检测并报出：
  ① schema 非法（B4F1 `InvalidSchemaError`）；
  ② **源存在性**：静态边源（单源 / 多源）与条件边源（`START` 除外）MUST 已登记，
  否则 `ValueError`；
  ③ **入口存在性**：`START` MUST 作为某条静态边或条件边的源出现，否则 `ValueError`
  （消息含 `entrypoint` / `START`）；
  ④ **目标存在性**：静态边目标（`END` 除外）与条件边目标（`END` 除外）MUST 已登记，
  否则 `ValueError`；
  ⑤ **空节点表**：`ValueError`（本项目比上游更严，登记 **X-5**；上游对
  `START -> END` 空图接受 · 实测 E-20）。
  校验顺序 MUST = ① → ② → ③ → ④ → ⑤；其中 ②③④ 与上游 `validate()` 的
  「源 → 入口 → 目标」一致（实测 E-07 / E-20）。
  错误消息 MUST 指明具体问题（节点名 / 源 / 分支 / 目标 / `entrypoint`）。
  **图结构错误**的异常类型 MUST 只用内置 `ValueError` / `TypeError`；**schema 非法** MUST
  沿用 B4F1 的 `InvalidSchemaError`。本 feature MUST NOT 新增任何异常类型。
  另：重复节点名 / `START` / `END` 作节点名 / 保留字符等**立即层**错误仍按
  `data-model.md` **BV-1…BV-9** 执行；本条只规定**构建期末层**的顺序。

- **FR-007（内部规格产物）**：系统 MUST 提供私有接口
  `StateGraph._build_spec() -> _BuilderSpec`（**2026-11-15 澄清轮发起者确认选项 A**），
  并冻结以下形态：
  ```text
  _BuilderSpec(
      channels: dict[str, Channel],
      nodes: dict[str, NodeSpec],
      node_records: dict[str, _NodeRecord],
      edges: dict[str | tuple[str, ...], tuple[str, ...]],
      conditional_edges: tuple[_ConditionalEdgeSpec, ...],
  )
  _NodeRecord(name: str, action: Callable,
              defer: bool, metadata: Mapping[str, Any] | None)
  _ConditionalEdgeSpec(source: str, branch: str, path: Callable,
                       path_map: dict[Hashable, str] | None,
                       targets: tuple[str, ...],
                       route_channels: tuple[str, ...])
  ```
  ① `channels` MUST 由 B4F1 `parse_state_schema` + B5F1 `build_channels` 产出，顺序 =
  schema 声明顺序；其后追加路由通道（见 FR-020）。
  ② `nodes` MUST 使用 B7F1 的 `NodeSpec`；`subscribes` MUST 为**状态通道** key 的元组
  （顺序 = `channels` 中状态部分的顺序），MUST NOT 含路由通道。
  ③ `edges` MUST 与 B7F1 `GraphSpec.edges` 同构；值 MAY 含 `END`（由 B7F2 过滤）；
  多源键的 **V-16 形态**（`END` / 目标数 ≠ 1）同样由 B7F2 最终失败。
  ④ `conditional_edges` MUST 按登记顺序保存，字段名 / 语义逐字冻结；`branch` MUST 为
  `_branch_name(path)` 的登记结果（同一 `source` 上唯一，与 `_branch_names` 去重口径一致）；
  `targets` MUST 为归一化 `path_map` values 的唯一目标（**含 `END`**，首次出现顺序）；
  `route_channels` MUST 仅含非 `END` 目标的 `branch:to:<target>`。`path_map=None` 且无法从
  `Literal[...]` 推断时：`targets=()`、`route_channels=()`，`path_map` 保持 `None`；
  B7F2 MUST 原样保留该 `None` 供 B8F1 动态求值，MUST NOT 把「无静态目标」等价为 `END`。
  ⑤ 每次调用 MUST 返回**新副本**：`channels` 映射与其中**通道实例**、`nodes` 映射与其中
  `NodeSpec`、`edges` / `conditional_edges` 元组、`node_records` 映射均 MUST 新建；
  调用方修改快照 MUST NOT 影响构建器或后续快照。
  ⑥ 两次调用的结果 MUST **结构等价**：通道按类型 / 归约器 / key 比较；节点、边、分支
  字段逐字相等。MUST NOT 以通道对象的身份相等作为判据。
  ⑦ `_BuilderSpec` / `_NodeRecord` / `_ConditionalEdgeSpec` MUST NOT 进 `freegraph.graph`
  的导出面，MUST NOT 出现在 API 快照的公开符号中。
  ⑧ 实现 MAY 使用私有中间草稿 `_ConditionalEdgeDraft`，但它 MUST NOT 进入
  `_BuilderSpec` 的冻结字段或 `freegraph.graph` 的导出面。

- **FR-008（不执行）**：本 feature MUST NOT 执行任何节点、路由函数、归约器或 `Send`；
  MUST NOT 实现 `compile()` / `invoke()` / `stream()` / `get_graph()`。构建期对用户函数
  只做「持有」，不做「调用」。

- **FR-009（返回形态透传）**：`add_node` 的节点函数与 `add_conditional_edges` 的条件边
  函数 MUST 接受任意可调用对象；MUST NOT 依据返回注解或运行时返回值拒绝 `dict` /
  `Command` / `list[Command | dict]` / `None` / `Send` / `list[Send]`（H-3 / H-4）。

- **FR-010（别名 · 已作废）**：C25 已于 2026-11-20 正式作废；`add_node` MUST NOT 接受 `alias`，
  `_NodeRecord` MUST NOT 含 `alias`。历史 B6F1 的「只记录」文字保留为历史。

- **FR-011（`defer` 的边界）**：`add_node(..., defer=True)` MUST 被接受并记录，但
  节点专用屏障（`NamedBarrierValueAfterFinish`）**不在本 feature 实现**；MUST NOT 因
  `defer` 改变静态边 / 触发语义（B7F4 的 X-03）。因此 B6F1 对 `defer=True` 目标仍建
  `EphemeralValue` 路由通道；上游对 defer 目标用 `LastValueAfterFinish`，该差异登记为
  **X-7**（已知不支持），由 **B7F4 X-03** 在 defer 落地时一并处理。若用户需要 `defer` 屏障，MUST 另行立项。

- **FR-012（静态断点透传）**：构建器 MUST NOT 新增 `interrupt_before` / `interrupt_after`
  字段或校验；其 `add_node` / `add_edge` / `add_conditional_edges` 方法不接收这两个配置
  ⇒ 不存在「丢弃 / 改名 / 改写」的路径。它们仍是 `compile()` 的关键字，由 B7F2 接受并
  填入 `GraphSpec`；本 feature 只做「不拦截」的静态断言，**正向透传判据归 B7F2**。

- **FR-013（依赖与红线）**：本 feature MUST NOT import `langchain` / `langchain-core` /
  `langsmith` / `langgraph*`；MUST NOT 读任何环境变量；MUST NOT 有任何 I/O / 出站；
  MUST 只依赖标准库与 L1 / L2 内部模块。L3 MUST NOT 被 L1 / L2 反向 import。

- **FR-014（公开 API 零新增）**：`freegraph.graph` 的 7 个导出符号 MUST 不变；
  `StateGraph` 的公开方法签名 MUST 不变（B2F2 快照仍逐字节成立）；
  `_build_spec` / `_BuilderSpec` 等下划线名字 MUST NOT 进入公开快照。

- **FR-015（固定脚本）**：`harness/demo/target.py` MUST NOT 被修改（只读基准）；
  其第 142–155 行的建图代码 MUST 原样可用。本 feature 只交付「建图」环节，
  **不**声称 `target.py` 已端到端跑通（`compile()` / `invoke()` 归 B7F2 / B7F3）。

- **FR-016（顺序与确定性）**：通道 key 顺序 MUST = schema 声明顺序；节点表顺序 MUST =
  `add_node` 登记顺序；静态边目标顺序 MUST = 首次出现顺序；条件边顺序 MUST = 登记顺序；
  分支目标 / 路由通道顺序 MUST = 归一化映射的首次出现顺序。相同输入的两次
  `_build_spec()` MUST 产生结构等价快照（判定口径见 FR-007 ⑥）。

- **FR-017（schema 错误传播）**：B4F1 的 `InvalidSchemaError` MUST 原样向上传播；
  构建器 MUST NOT 包装、吞掉或降级为「无归约器」的解析结果。

- **FR-018（输入不变性）**：构建器 MUST NOT 修改用户传入的 `path_map` dict / list / `metadata`
  dict；对 dict MUST 做浅拷贝，对 list MUST 新建归一化 dict。用户后续修改原对象 MUST NOT
  影响已记录的规格。**浅拷贝仅保证顶层 key 隔离**；`metadata` 的嵌套可变对象不保证隔离
  （需要深拷贝的用户 MUST 自行复制），该边界 MUST 在文档中写明。

- **FR-019（校验幂等）**：`validate()` MUST 成功返回 `Self`；失败后构建器状态 MUST 保持
  不变；同一构建器可重复调用 `validate()` / `_build_spec()`。

- **FR-020（路由通道）**：对每个条件边的**静态目标**（归一化 `path_map` 的 values，
  排除 `END`；**2026-11-15 澄清轮发起者确认选项 A**），构建器 MUST 在 `channels` 中追加一个
  `EphemeralValue(key="branch:to:<target>", value_type=Any, guard=False)`；同一目标
  MUST 只建一次。`guard=False` 与上游路由通道一致（允许一步内多写、取末值）；
  `path_map=None` 且推断不到目标 ⇒ MUST NOT 建任何路由通道；推断出目标 ⇒ 照常建。

- **FR-021（`validate()` 的范围）**：本 feature 交付上游同名的
  `validate(interrupt=None) -> Self` 作为构建期校验入口。① 它 MUST 执行 FR-006 的
  全部构建期末检查；② MUST NOT 执行节点；③ `interrupt` 参数 MUST 被接受，并 MUST
  按上游（`langgraph/graph/state.py:1168-1174`）校验：每个名字 MUST 是已登记节点，
  否则 `ValueError`（消息含该名字）；参数缺省 / `None` ⇒ 不校验。静态断点的
  **编译期可达性**仍归 B7F2 的 compile 入口层。
  ④ 其余上游同款构建方法（`add_sequence` / `set_entry_point` /
  `set_conditional_entry_point` / `set_finish_point` / `set_node_defaults`）本 feature
  MUST NOT 交付，且 MUST 保持显式 `NotImplementedError`（不得静默成功）；其 docstring /
  `NotImplementedError` 消息 MUST NOT 继续写「由 B6F1 交付」，MUST 写「本版本不交付 ·
  另行立项」。

### Key Entities

| 实体 | 语义 | 契约 |
|---|---|---|
| **`StateGraph`** | 图构建器；持有 schema、节点、边、条件边；不执行 | C1 / C9 / C10 |
| **`_BuilderSpec`** | 构建器 → B7F2 的冻结内部规格；`channels` / `nodes` / `node_records` / `edges` / `conditional_edges` | FR-007 · D-1 |
| **`_NodeRecord`** | 节点登记项：名字、函数、`defer`、`metadata`（**C25 作废后无别名**） | FR-002 / FR-010（历史） / FR-011 |
| **`_ConditionalEdgeSpec`** | 条件边登记项：源、分支名、路由函数、归一化 `path_map`、静态目标、路由通道 | FR-004 / FR-020 · D-2 |
| **节点规格 `NodeSpec`** | B7F1 的节点规格：订阅集 + 节点函数 | C5 · H-2 |
| **静态边规格** | 单源 `str` / 多源 `tuple[str, ...]` → 目标元组 | C7 / C9 · H-5 |
| **路由通道** | `EphemeralValue`，键名 `branch:to:<target>` | C7 / C8 · FR-020 |

### 需求 ↔ 成功标准 追溯表

| 需求 | 成功标准 | 验收判据 |
|---|---|---|
| FR-001 | SC-001 / SC-005 | A3 |
| FR-002 | SC-001 / SC-006 / SC-014 | A1 / A3 |
| FR-003 | SC-001 / SC-004 / SC-011 | A1 / A3 |
| FR-004 | SC-002 / SC-005 | A2 |
| FR-005 | SC-001 / SC-002 | A1 / A2 |
| FR-006 | SC-003 / SC-012 | A1 |
| FR-007 | SC-005 | A1 |
| FR-008 | SC-007 | A1 |
| FR-009 | SC-007 | A1 |
| FR-010 | SC-014 | A1 |
| FR-011 | SC-014 | A1 |
| FR-012 | SC-013 | A1 |
| FR-013 | SC-008 | A1 |
| FR-014 | SC-010 | A1 |
| FR-015 | SC-001 / SC-009 / SC-015 | A3 |
| FR-016 | SC-005 / SC-011 | A1 |
| FR-017 | SC-003 | A1 |
| FR-018 | SC-011 | A1 |
| FR-019 | SC-012 | A1 |
| FR-020 | SC-002 / SC-005 | A2 |
| FR-021 | SC-003 / SC-010 / SC-013 | A1 |

### Out of Scope

- `compile()` —— 属 **B7F2**。
- `invoke()` —— 属 **B7F3**。
- 条件边求值与 fresh 读 —— 属 **B8F1**。
- `stream()` —— 属 **B8F2**。
- `get_graph()` / `draw_mermaid()` —— 属 **B22F1** / **B23F1**。
- **C25 已正式作废** —— `add_node` 不再接受 `alias`；本 feature 不再记录 `alias`。
- `defer=True` 的节点专用屏障 —— B7F4 的 X-03；本 feature 只接受并记录，路由通道对
  defer 目标仍用 `EphemeralValue`（与上游 `LastValueAfterFinish` 的差异登记为 **X-7**，
  由 B7F4 X-03 在 defer 落地时一并处理）。
- `add_sequence` / `set_entry_point` / `set_conditional_entry_point` /
  `set_finish_point` / `set_node_defaults` —— 本 feature 不交付（裁定 9）。
- 上游 `add_node` 的可选关键字 `input_schema` / `retry_policy` / `cache_policy` /
  `error_handler` / `timeout` / `trace_policy` / `destinations` —— **不在 B2F2 冻结签名内**，
  本 feature 不交付；`NodeSpec.subscribes` 固定为**全部状态通道**，不实现上游的窄
  `input_schema` 自动推断。若未来需要窄订阅，另行立项。
- 子图 —— v2（C26）。
- 任何运行期行为 / checkpoint / trace / persistence。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：`harness/demo/target.py:142-155` 的**建图调用**原样执行成功（schema 以等价
  `TypedDict` 替身；0 个 `AttributeError` / `TypeError`），且构建器记录了 2 个节点、2 条静态边、1 条条件边。
- **SC-002**：`add_conditional_edges` 的 list 与 dict 两种 `path_map` 各有一例通过；
  归一化结果与预期逐字一致；路由通道各按目标建好。
- **SC-003**：构建期错误检测的 3 类反例（重复节点名 / 边目标不存在 / 缺少入口）
  各有一例被捕获；异常类型为 `ValueError`，消息含问题节点名 / `entrypoint`。
  「边目标不存在」用例 MUST 先建立有效 `START` 入口，使目标错误成为唯一错误
  （校验顺序见 FR-006）。
- **SC-004**：`add_edge(...).add_edge(...)` 可用；三个构建方法的返回值与调用者
  `is` 同一对象（链式语义 100%）。
- **SC-005**：`_build_spec()` 的产物可被 B7F2 消费：`channels` / `nodes` / `edges`
  可适配为 B7F1 的 `GraphSpec` / `NodeSpec`；`conditional_edges` 字段（含 `branch`）逐字可读；
  两次调用产生结构等价但彼此独立的快照（判定口径见 FR-007 ⑥）。
- **SC-006**：`StateGraph` / `add_node` / `add_edge` / `add_conditional_edges`
  的**方法名、必填位置参数 / 顺序、返回语义**三项与 `langgraph 1.2.11` 逐项一致；
  每条断言附 `路径:行号`；差分场景 D-50…D-73 的判词与 Upstream Parity 表一致
  （D-74 已迁移到 B8F3 D-142，不再由 `parity_probe.py` 承载）。
  **MUST NOT** 把「一致」解释为全部 keyword-only 参数、默认值或注解逐字相同：
  **C25 已正式作废**；freegraph 不再接受 `alias`；上游可选 `add_node` 关键字不承载；非 callable `Runnable`
  不承载（X-6）。
- **SC-007**：构建期节点函数、路由函数、归约器调用计数全部为 0；返回形态
  `dict` / `Command` / 命令列表 / `None` / `Send` 列表均不被拒绝。
- **SC-008**：依赖门禁通过：0 个 `langchain*` / `langgraph*` / `langsmith` import；
  0 次环境变量读取；0 次 I/O / 出站。
- **SC-009**：`harness/demo/target.py` 的 git diff 为空。
- **SC-010**：`freegraph.graph` 的 7 个导出符号不变；`StateGraph` 公开方法签名快照
  逐字节不变；`_BuilderSpec` / `_build_spec` 不出现在公开快照中。
- **SC-011**：通道 / 节点 / 静态边 / 条件边 / 分支目标 / 路由通道的顺序均与声明顺序
  一致；相同输入两次 `_build_spec()` 结构等价（判定口径见 FR-007 ⑥）；用户原
  `path_map` / `metadata` 的**顶层 key**后续修改 MUST NOT 影响已记录快照（嵌套可变对象
  不保证隔离，见 FR-018）。
- **SC-012**：`validate()` 成功返回 `Self`；失败后构建器状态不变；重复调用幂等；
  错误消息可定位问题。
- **SC-013**：构建器不新增 / 不丢弃 / 不改名 `interrupt_before` / `interrupt_after`；
  `compile()` 的这两个关键字仍可被 B7F2 接收；`validate(interrupt=...)` 接受并按上游
  校验节点存在性（未知节点 ⇒ `ValueError`）；本 feature 仅做静态断言 + 接口检查，
  **正向透传判据归 B7F2（D-1 / H-6）**。
- **SC-014**：`add_node(..., defer=True, metadata=...)` 的 `defer` / 元数据值出现在 `_NodeRecord`；
  `add_node(..., alias="model")` 在 C25 作废后抛 `TypeError`；不实现 `defer` 屏障（归 B7F4 X-03）。
- **SC-015**：最小图（2 节点 + `START` / `END` 边）可被构造并通过 `validate()`；
  运行期断言留给 B7F3（承接 H-7）。

---

## Assumptions

- 上游版本固定为 `langgraph 1.2.11`（核实环境：`.venv/lib/python3.11/site-packages/langgraph`）。
  换版本 MUST 重新核实 `路径:行号`，MUST NOT 凭记忆沿用。
- B4F1 的 `parse_state_schema` / `build_channels` 已交付且行为稳定；本 feature 只消费，
  不修改。**schema 的接受 / 拒绝面以 B4F1 的 spec 与 `contracts/schema-parse-contract.md`
  为准**（含 2026-11-12 上游对齐 P3 的口径）；本 feature MUST NOT 另立第二套 schema 判定。
- B5F1 的 `Channel` / `LastValue` / `BinaryOperatorAggregate` / `EphemeralValue` 已交付；
  本 feature 只实例化，不修改。
- B7F1 的 `NodeSpec` / `GraphSpec` 已交付且冻结；本 feature 的 `_BuilderSpec` 是它们的
  上游适配，不另立第三套图规格。
- B7F2 将按 D-1 调用 `_build_spec()`；若 B7F2 需要额外字段，MUST 通过正式回溯修订
  更新本 spec，MUST NOT 私自扩展 `_BuilderSpec`。
- B9F1 的 **`__parent__` 保留名检查**与 B7F4 的 **V-16** 由 B7F2 最终校验；B6F1 的 `validate()` 只覆盖
  V-1 / V-2 / V-3 对应的图结构检查（含空节点表 X-5）。
- B7F2 将按 D-2 把 `_BuilderSpec.conditional_edges` 机械翻译为纯内建类型
  `dict[str, tuple[dict[str, Any], ...]]`（形状见 D-2；内层 `branch` 取自
  `_ConditionalEdgeSpec.branch`）并存放在 `CompiledGraph` 私有字段；B8F1 只消费 L2 侧的
  `GraphSpec.conditional_edges` 与 `branch:to:<target>` 路由通道，
  MUST NOT import `freegraph._stategraph` 或 `_ConditionalEdgeSpec`。
- B7F2 仍按 D-1 在 `CompiledGraph` 私有字段保留完整 `_BuilderSpec`（至少 `node_records`）供其他用途；
  **C25 正式作废后，B8F3 不再读取 `_NodeRecord.alias`**。
- **C25 已于 2026-11-20 正式作废**：`add_node` 不再接受 `alias`，`_NodeRecord` 不再含 `alias`；
  未来若重启 alias，使用新契约编号（如 C28）并重新论证。
- `path_map=None` 的 `Literal[...]` 注释推断按上游复制；推断不到时 `targets=()`、
  `route_channels=()` 且只记录 `None`，实际求值归 B8F1。
- `defer=True` 的节点屏障不在 v1 本 feature 实现；用户需要时另行立项。`defer=True` 目标的
  路由通道类型差异登记为 **X-7**（已知不支持），由 B7F4 X-03 在 defer 落地时一并处理。
- `add_node` 的签名以 B2F2 快照为准；上游额外的 `input_schema` / `retry_policy` 等可选
  关键字不属于宪法原则 III 的「同名同签名」硬要求，本 feature 不交付，也不据此扩展
  `_BuilderSpec`。`NodeSpec.subscribes` = 全部状态通道。
- 普通 callable 取名 = `__name__` → 类型名；`.name` 不参与（上游同款）。非 callable
  `Runnable` / Runnable-like 对象不承载（X-6 · 零依赖 duck-typing 边界）。
- 空节点表保留为比上游更严的失败（X-5）；上游 `START -> END` 空图可通过 `validate()`。
- 「同名同签名」的签名比较口径 = 方法名 + **必填位置参数 / 顺序** + 返回语义；
  MUST NOT 要求完整 keyword-only 集合、默认值或注解逐字相同。
- `harness/demo/target.py` 是只读基准；本 feature 不修改任何一行。
- 本 feature 只交付「建图」环节；固定脚本端到端可跑仍需 B7F2 / B7F3 / B8F1 / B22F1 /
  B23F1 齐备。

---

## 依据

- 立项书 §4.3（18 项 API 裁定 · 7 项同名同签名）、§5.1（分层拍板）、§5.2（B6F1 行）、
  §5.3（C1 / C5 / C7 / C9 / C10；C25 已正式作废）、§6.2（M2 里程碑）、§9.1（门禁）。
- 宪法 `.specify/memory/constitution.md`：原则 III（7 项 MUST 同名同签名）· 原则 VI（可追溯性）·
  原则 IX（依赖许可证红线）· 原则 X（文档合规）· 原则 XI（上游优先）。
- 上游源码（`langgraph 1.2.11`）：`langgraph/graph/state.py:131`（`StateGraph`）·
  `:216-225`（`__init__`）· `:667-682` / `:778-799`（`add_node`）· `:802-805`（重复 / 保留名）·
  `:928-979`（`add_edge`）· `:982-1027`（`add_conditional_edges`）· `:1129-1175`（`validate`）·
  `langgraph/graph/_branch.py:89-120`（`BranchSpec.from_path`）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4。
- 调度契约：`specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §2.1 / §2.1.1。
- 上游承接：`specs/b7f4-multisource-join/spec.md` D-1 / X-03 ·
  `specs/b13f1-static-interrupt-recursion-limit/spec.md` D-7 ·
  `specs/b11f1-send-fanout/spec.md` D-6 ·
  `specs/b9f1-command-primitive/spec.md` 裁定 21 ·
  `specs/b4f1-schema-reducer-parse/spec.md` FR-002 / 裁定 6。
- 验收脚本：`harness/demo/target.py:142-155`（只读基准）·
  `harness/demo/graph_core.py`（C7 list / dict 建图用例）。
