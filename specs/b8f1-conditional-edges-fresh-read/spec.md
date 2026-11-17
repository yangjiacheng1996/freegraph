# Feature Specification: B8F1 · 条件边路由求值 + `END` 终止 + fresh 读（C8 独立回归测试）★

**Feature Branch**: `b8f1-conditional-edges-fresh-read`

**Created**: 2026-11-17

**Status**: Draft

**Input**: User description: "B8F1 · 条件边路由求值 + `END` 终止 + fresh 读（C8 独立回归测试）★ —— 交付**条件边**的路由语义：路由函数在正确的时机被调用、看到正确的状态视图、返回的目标被正确解析（含 `path_map` 的 list / dict 双形态）、`END` 能终止整张图。本 feature 的判定是：**路由函数看到本节点刚写入的值**（C8 fresh 读）。前置依赖 **B5F2, B7F1, B7F3**。"

---

## 承接条款（上游 feature → 本 feature）

> 宪法 v1.12.0「跨 feature 承接的接线通则」：上游 feature 指名本 feature 的跨 feature 义务
> MUST 在本 spec 落成 **FR + 裁定**；**只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽判据**。

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B7F1 → B8F1** | **M2** | **条件边字段口径 + V-8 放宽**：B7F1 的手写图规格 `GraphSpec` **已预留**「条件边」字段 `conditional_edges`（**名字逐字冻结**）· B7F1 阶段该字段**恒为空**、**填值即显式失败**（内置 `ValueError` · 校验规则 **V-8**）⇒ ⇒ **B8F1 只需填值**即可复用，**MUST NOT** 改造 B7F1 的调度内核 ⇒ ⇒ ⇒ **B8F1 MUST 放宽 V-8**（构造期**不再**因该字段非空而失败）⇒ ⇒ ⇒ ⇒ **V-8 是冻结面** ⇒ ⇒ ⇒ ⇒ 放宽 MUST 走「登记 + 回溯修订 + 发起者追认」 | `specs/b7f1-superstep-loop/spec.md` **FR-033** · **B7F1 的**裁定 25 · 下游承接 **D-1** · `contracts/superstep-contract.md` §1 / §2.1 / §2.1.1（V-8 行） | FR-001 · FR-025 · FR-026 · 裁定 14 · 破冻结面 **T-1** · 冻结断言 ① ② |
| **H-2** | **B5F2 → B8F1** | **M1** | **① 夹具接口口径**：B5F2 差分夹具的 `conditional_edges` 字段**保持恒空**（其 freegraph 侧驱动器是**线性替身** · 无调度能力）⇒ ⇒ 条件边的路由判定差分 MUST 落 `tests/differential/parity_probe.py`（**双真实实现**对跑 · **同一差分体系**）⇒ ⇒ ⇒ MUST **NOT** 重造夹具接口 ⇒ ⇒ ⇒ MUST **NOT** 作废 B5F2 已产出的**线性链路**差分证据 ⇒ ⇒ ⇒ **V-4 无需放宽**<br>**② `local_read` 的调用口径**：**B8F1 MUST 在使用 `local_read` 时显式传 `fresh=True`**（`fresh` 的**缺省是 `False`**）⇒ MUST **NOT** 依赖缺省 ⇒ MUST **NOT** 假设上游的 `managed` 语义（research **DR-3** · 上游 `local_read` 的第四类入参 freegraph **不实现**） | `specs/b5f2-sparse-state-read/spec.md` **FR-015** / 裁定 15 · **FR-031 ②** / **B5F2 的 SC-023** / **B5F2 的**裁定 33 ③ · `contracts/read-contract.md` §1.1 / §3.1 · `contracts/differential-fixture.md` §2 / §4 | FR-007 · FR-030 · 裁定 2 · 裁定 **15** · SC-014 |
| **H-3** | **B7F2 → B8F1** | **M2** | **条件边交接载体**：`CompiledGraph._conditional_edges` 已持有 **plain mapping**（外层 key = 源节点名；内层每项**恰 5 键** = `branch` / `path` / `path_map` / `targets` / `route_channels`；顺序 = 登记顺序；`branch` 取自 `_ConditionalEdgeSpec.branch`）⇒ ⇒ **B8F1 MUST 从该私有字段读取**并填入 `GraphSpec.conditional_edges`（落地时**承接 V-8 放宽**）⇒ ⇒ **路由求值 MUST 只消费 L2 的 `GraphSpec.conditional_edges`** ⇒ ⇒ MUST **NOT** import `freegraph._stategraph` / `_ConditionalEdgeSpec` ⇒ ⇒ MUST **NOT** 重新归一化 `path_map` ⇒ ⇒ MUST **NOT** 另起路由通道命名（沿用 `branch:to:<target>`）⇒ ⇒ B7F2 阶段 `GraphSpec.conditional_edges` **恒空** | `specs/b7f2-compile/spec.md` **FR-009 / FR-010** · 裁定 12 / 13 · 下游承接 **D-2** · `contracts/compile-contract.md` §8 | FR-013 · FR-026 · FR-027 · 裁定 4 · 裁定 13 |
| **H-4** | **B6F1 → B8F1** | **M2** | **条件边载体**：`add_conditional_edges(source, path, path_map=None)` 只**登记并立即校验**；`path_map` 的 **list / dict / None** 三形态在**构建期**归一化（list ⇒ `{name: name}`）⇒ ⇒ **B8F1 MUST 只消费已归一化的结果** ⇒ ⇒ MUST **NOT** 重新归一化 ⇒ ⇒ 路由通道 `branch:to:<target>` **已由构建器建好** ⇒ ⇒ MUST **NOT** 另起命名 ⇒ ⇒ `path_map` 的 **value** 指向的节点 MUST 是已注册节点或 `END`（构建期已校验 · 实测锚点 `src/freegraph/_stategraph.py:590-598` 的 `_validate_targets`）⇒ ⇒ ⇒ 同理**源节点名**亦在构建期校验（`src/freegraph/_stategraph.py:564-568` 的 `_validate_sources`） | `specs/b6f1-stategraph-builder/spec.md` **D-2** · 裁定 3 · `contracts/builder-contract.md`（路由通道行） | FR-014 · FR-015 · FR-016 · FR-027 · 裁定 4 |
| **H-5** | **B7F3 → B8F1** | **M2** | **条件边路由的执行落点（`D-2`）**：条件边路由求值 MUST 在本 feature 的**同一条**执行路径上生效（**MUST NOT** 另开路径）⇒ ⇒ 路由**触发的目标节点**的写入 MUST 进入**同一份**完整状态 ⇒ ⇒ 本 feature 的「稀疏视图 + 补齐」口径对**路由通道同样适用**（路由通道**不进**返回键集） | `specs/b7f3-invoke-full-state/spec.md` **FR-003 / FR-012** · 裁定 4 · SC-013 · 下游承接 **D-2** | FR-002 · FR-029 · 裁定 1 · SC-002 · SC-013 |
| **H-6** | **B7F4 → B8F1** | **M2** | **条件边路由 MUST NOT 受屏障影响**：「**条件边的目标集合**」与「**屏障组**」是**两套**语义 ⇒ ⇒ MUST **NOT** 混用 ⇒ ⇒ **B8F1 MUST NOT** 把「多源边」当作「条件边」求值 ⇒ ⇒ 条件边的**目标**由**路由函数**决定，与屏障组的「所有源齐备」判定**无关** | `specs/b7f4-multisource-join/spec.md` 下游承接 **D-3** · 登记项 **PR-4** | FR-004 · FR-017 · Edge Cases（「条件边与屏障不混用」） · SC-009 |
| **H-7** | **B9F1 → B8F1** | **M2** | **`node_writes` 的归属口径**：`Command.update` 的写入**归源节点名下**（`node_writes` 仍**按节点分组**）⇒ ⇒ 本 feature 的 fresh 读（「本节点**本次**写入」）**读得到** `Command` 的写入 ⇒ ⇒ **零改动**、**形态不变** ⇒ ⇒ ⇒ `Command.goto` 的目标与条件边目标的**并集**口径由本 feature 落成（裁定 13） | `specs/b9f1-command-primitive/spec.md` 裁定 16 · **FR-004** | FR-008 · FR-009 · FR-020 · 裁定 13 · SC-004 |
| **H-8** | **B11F1 → B8F1** | **M2** | **`Send` fan-out 的复用**：条件边函数返回 `Send` / `list[Send]` 时 MUST 产生**同款 fan-out 任务**（同一落点 · 同一入参形态 · 与**节点返回 `Send`** 产生**同款任务** ⇒ ⇒ ⇒ **失败信号与上游的类型分叉见偏离登记 X-6 / X-7**）⇒ MUST **NOT** 另写条件边专属 fan-out 路径 ⇒ ⇒ B11F1 只交付**节点返回**形态（`GraphSpec.conditional_edges` 恒空 · B7F1 的 V-8） | `specs/b11f1-send-fanout/spec.md` 下游承接（`Send` 语义） | FR-011 · FR-020 · 裁定 9 · 裁定 10 · SC-008 |
| **H-9** | **B3F1 → B8F1** | **M2** | **C8 回归测试的挂载点**：契约门禁第 3 项 MUST 包含 **C4**（稀疏状态读）与 **C8**（条件边 fresh 状态读）两条**独立回归测试** ⇒ ⇒ B5F2 / B7F3 交付时 **C8 的挂载点仍为 `not-landed`**（承接方 = **B8F1**）⇒ ⇒ **本 feature MUST 翻转该挂载点为 `landed`** 并**新增 C8 的元测试**（路径扫描 · **零** `freegraph.*` import）⇒ ⇒ 依赖门禁（无 `langsmith` / `langchain*` / `langgraph*`）**常驻** | `specs/b3f1-scaffold-ci-gates/spec.md` **FR-011 ①** · `harness/reports/Q8-图运行时最小契约.md` §3.4（C8 行） | FR-024 · 裁定 12 · 破冻结面 **T-5** · SC-015 |
| **H-10** | **B10F1 → B8F1** | **M2** | **中断路径与路由的关系**：路由求值发生在**节点任务成功落回**之后 ⇒ ⇒ 节点若在执行中请求人工审批（`interrupt()`）⇒ 该任务**不成功落回** ⇒ ⇒ **路由函数 MUST NOT** 被求值 ⇒ ⇒ 中断路径与路由路径**互斥** | `specs/b10f1-interrupt-resume/spec.md` **FR-013** 的表 · 裁定 4 | FR-003 · FR-018 · Edge Cases（「节点挂起时路由不求值」） · SC-012 |
| **H-11** | **B7F3 → B8F1** | **M2** | **MVP 验收的「工具循环轮」承接**：B7F3 的 **EV-2**（门禁 4 / 5 的「fake / 真实模型轮跑通**工具循环**」）的根因 = 「**条件边路由求值未交付**」⇒ ⇒ ⇒ 本 feature 交付后该轮**变为可达** ⇒ ⇒ ⇒ 本 feature MUST 让 `harness/demo/agent_loop.py` 的 **B1「工具循环」**与 **B2「tool_calls 形状」**两组 `soft(...)` ⇒ **硬断言** ⇒ ⇒ ⇒ MUST 在**人工验证记录**中补上**工具循环轮**的**实测输出** ⇒ ⇒ ⇒ 破冻结面 **T-7**（**并入**本 feature 的**唯一一次**追认 · 追认次数仍 == **1**）⇒ ⇒ ⇒ ⚠️ B7F3 的 **EV-4**（固定脚本 `target.py` 端到端轮）**仍不可达**（PNG 路径属 **B23F1**）⇒ ⇒ ⇒ 其承接方为 **B22F1 + B23F1（M2）**· **B25F1（M4）**（见 plan 的**登记项 R-2**）⇒ ⇒ ⇒ **本 feature MUST NOT** 越界实现它 | `specs/b7f3-invoke-full-state/spec.md` 的 **EV-2** / **EV-4** · `harness/verification/B7F3/manual-verification.md` 的 **EV-2** 行 · `harness/demo/agent_loop.py:214-262` | **FR-041** · **FR-042** · 裁定 **19** · **SC-025** · **SC-026** · 破冻结面 **T-7** |

---

## 下游承接条款（本 feature → 下一棒）

> 本 feature 冻结「路由求值 + fresh 读 + 目标解析 + 失败信号」这组跨 feature 接口（**D-1…D-5**）。**只接线 · 逐条最小改动**。

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 |
|---|---|---|---|---|
| **D-1** | **B8F1 → B8F2** | **M2** | **`stream()` 的路由口径**：`stream` 的每一档 MUST 与本 feature 的 `invoke` **逐字同款**（**同一份**路由求值实现点 ⇒ **MUST NOT** 另写一份）⇒ ⇒ 路由判定 MUST 在 `stream` 的**同一次**执行里可观察 ⇒ ⇒ 「稀疏视图 + 补齐」（B7F3 的 D-1）口径**继续**适用 | FR-002 · 裁定 1 · SC-002 |
| **D-2** | **B8F1 → B8F3** | **M2** | **节点别名与 `context` 通道**：本 feature 的路由函数入参 = **fresh 视图** ⇒ ⇒ `context` 通道（**C21**）MUST **NOT** 进入该视图（它是**运行期载体**，不是状态通道）⇒ ⇒ 节点别名（B8F3）MUST **NOT** 影响 `path_map` 的查表（查表用**节点名**，不解析别名） | FR-007 · FR-009 · Edge Cases · SC-010 |
| **D-3** | **B8F1 → B11F1** | **M1** | **`Send` fan-out 的调度归 B11F1**：本 feature **只**把路由函数返回的 `Send` / `list[Send]` **喂进** B11F1 既有的 fan-out 任务构造器 ⇒ ⇒ B11F1 MUST **NOT** 另写「路由来源」的 fan-out 路径 ⇒ ⇒ 两条来源（节点返回 / 路由返回）MUST 产出**同款**任务 | FR-011 · 裁定 10 · SC-008 |
| **D-4** | **B8F1 → B22F1 / B23F1** | **M2** | **图导出里的条件边**：`get_graph` / `draw_mermaid_png` MUST 能表达**条件边**（源节点 → 可能的多个目标）⇒ ⇒ MUST 复用本 feature 的 `targets` / `route_channels` 口径 ⇒ ⇒ **MUST NOT** 另算一份目标集合 | FR-013 · FR-025 · Edge Cases |
| **D-5** | **B8F1 → B25F1** | **M4** | **fake 模型注入**：本 feature 的路由函数是**用户函数**（非模型）⇒ ⇒ fake 注入（立项书 §9.2）**不涉及**本 feature ⇒ ⇒ 但路由函数**可以是**一个读状态的**假模型** ⇒ ⇒ B25F1 的注入机制 MUST 与路由函数**正交** | FR-003 · 裁定 12 · SC-014 |

---

## Clarifications

### Session 2026-11-17（设计裁定 · spec 阶段写死，plan 不得再翻）

> **背景**：提示词初稿已写死「条件边路由求值 · `path_map` list / dict 双形态 · `END` 终止 ·
> **fresh 读** · 非法返回值报错 · 序列返回值 fan-out」，但若干点仍会外溢到实现口径或下游
> feature 的接口决策。
>
> ⚠️ **本轮未向用户提问** —— 纪律：宪法原则 XI「上游有答案 ⇒ 照抄 ⇒ 不问用户」；
> 上游 `langgraph 1.2.11` 对本 feature 的**全部**语义点**均已给出答案**（含实测），
> 故 **零** 澄清标记（`NEEDS CLARIFICATION` 槽位）。

#### Q1（路由求值的执行落点）

→ **A：L2 的 `run_super_step` / `run_super_steps` 内部** —— 在**源节点任务成功落回**时求值。

- 与上游同款：上游的分支是**源节点的 writer**（`langgraph/graph/state.py:1624`），
  随源节点任务完成而执行。
- MUST NOT 另开一条「条件边专用」的调度路径。
- 投递触发 MUST 复用**既有的「动态边」载体**（与 B9F1 的 `Command.goto` 同款机制），
  于是编译产物的**私有字段数不变**（B7F2 的「3 私有 + 8 公开 = 11 键」冻结面**不破**）。

落点：FR-001 · FR-002 · FR-005 · 裁定 1 · SC-001 · SC-002。

#### Q2（fresh 读的唯一实现点）

→ **A：B5F2 的 `local_read(channels, writes, fresh=True)`** —— **显式**传 `fresh=True`。

- `fresh` 的**缺省是 `False`**（`read-contract.md` §1.1），故 MUST NOT 依赖缺省。
- MUST NOT 假设上游的 `managed` 语义（freegraph **不实现**该入参 · research **DR-3**）。
- MUST NOT 在调度层另写一份 fresh 合并逻辑。

落点：FR-007 … FR-012 · 裁定 2 · SC-004。

#### Q3（路由函数的入参）

→ **A：fresh 视图**（**当前值 + 本节点本次写入**），覆盖**整张通道表**。

- 与上游同款（实测 **E-10**：路由函数看到的是**全部 schema 通道**
  `['llm_calls', 'messages']`，**不是**「源节点订阅集」）。
- **路由型通道**（`EphemeralValue`）MUST 在该视图里**缺席**（上游同款 ·
  B5F2 `read-contract.md` §3.1 · `update([])` 清空副本）。
- MUST NOT 用「`branch:to:` 名称前缀」之类启发式判定路由通道。

落点：FR-007 · FR-011 · FR-012 · 裁定 3 · SC-004。

#### Q4（`path_map` 在 L2 的形态）

→ **A：只有两种** —— **dict**（已归一化）或 **`None`**（动态目标）。

- list 形态的归一化（`{name: name}`）**已在 L3 完成**（B6F1），故 L2 MUST NOT 重新归一化
  （H-3 / H-4）。
- 「list 形态 = 返回值即目标节点名」这一语义由归一化**自然保证**。
- 「返回值 MUST 是归一化后 dict 的 **key**」；取值不在表内时显式失败。

落点：FR-013 · FR-014 · FR-015 · FR-016 · 裁定 4 · SC-005。

#### Q5（`END` 的判定时机）

→ **A：查表前** —— 返回 `END`（**单独返回** · **非**序列）**无条件**终止整张图（精确范围见 **FR-019**）。

**理由（上游代码与上游自己的 docstring 相互矛盾）**：

- 上游 **docstring**（`langgraph/graph/state.py:999`）写「If it returns `'END'`, the graph
  will stop execution.」—— **无条件**。
- 上游**代码**（`langgraph/graph/_branch.py:199-211`）**不**过滤 `END` —— 终止的充要
  条件是「**解析后的目的地**恰为 `'__end__'`」（`:207-209` 是 `None` / `START` 校验 ·
  **不是** `END` 过滤）⇒ ⇒ 「`END` 是 `path_map` 的 key」**不等于**终止。
- **实测**：`path_map = {END: "b"}` + 返回 `END` ⇒ 上游路由到 `b`（**不终止**）；
  `path_map` **不含** `END` 键时返回 `END` ⇒ 上游抛 `KeyError: '__end__'`（查表失败）；
  **无** `path_map` + 返回 `END` ⇒ 上游**正常终止**。

结论：上游**不**在 `_branch.py` 里过滤 `END` ⇒ 终止的充要条件是「**解析后的目的地**恰为
`'__end__'`」⇒ ⇒ 「`END` 是 key」**不等于**终止 ⇒ ⇒ ⇒ freegraph 取「**单独返回** `END`
⇒ **无条件**终止」（精确范围见 **FR-019**）⇒ 与上游**仍有**分叉（`path_map = {END: "b"}`
这类）⇒ ⇒ ⇒ 属宪法原则 XI ② 类（**上游自身的不确定**）· freegraph 取**上游 docstring
口径** ⇒ **更确定** ⇒ 如实登记为偏离（**X-2** · DIFF · 非更严）。

落点：FR-018 · 裁定 5 · 偏离登记 **X-2** · 差分 **D-110 / D-118** · SC-006。

#### Q6（非法返回值的失败信号）

→ **A：内置 `KeyError`** —— **上游同族**（上游的 `self.ends[r]` 查表失败即 `KeyError` ·
`langgraph/graph/_branch.py:203` · 实测 **E-6 / E-7**）。
⇒ ⇒ ⚠️ **2026-11-17 clarify 轮 · 用户拍板（Q2 = 选项 B）**：本条口径**被修订**为
「**按 `path_map` 形态分两态**」（**有** ⇒ `KeyError` · **无** ⇒ `ValueError`）
⇒ ⇒ ⇒ 详见 §Clarifications 的「Session 2026-11-17 · clarify 轮」。

- **消息 MUST 更详细**：MUST **指明返回值**与**可选目标** ⇒ 上游的消息只有 key 本身
  ⇒ **STRICTER**（原则 XI「失败信号 MAY 更严」）。
- **类型逐字同款**（照抄纪律 ①）+ **消息更严**。
- MUST **NOT** 新增异常类型（零新增错误类型）。

落点：FR-021 · FR-022 · FR-025 · 裁定 6 · 偏离登记 **X-1 / X-3** · 差分 **D-107 / D-111 / D-113** · SC-006 · SC-007。

#### Q7（无 `path_map` 时的目标校验）

→ **A：显式失败**（内置 **`ValueError`** · **FR-022**）。

- **上游静默忽略**（实测 **E-8**：上游只打一条 warning「wrote to unknown channel
  `branch:to:ghost`, ignoring it」，图**静默结束**）⇒ ⇒ ⇒ 上游**同场景**是**静默忽略**
  （warning）⇒ ⇒ ⇒ freegraph 取**显式失败**（内置 **`ValueError`**）⇒ ⇒ ⇒ 记为**更严**
  （**X-3**）。
- 「拼错的名字无声地少跑」与 B7F3 的 **X-2**（未知 key ⇒ 显式失败）**同类**。
- 属原则 XI ② 类 ⇒ **STRICTER** ⇒ 如实登记（**X-3**）。

落点：FR-016 · FR-022 · 裁定 7 · 偏离登记 **X-3** · 差分 **D-111** · SC-007。

#### Q8（路由通道写不写）

→ **A：不写** —— 路由通道在 freegraph 里**只作声明载体**。

- L3 已建好 `branch:to:<target>`（供 `targets` / `route_channels` 口径与图导出用）。
- **触发**由**动态边**投递：freegraph 的触发源恒为**边**（B7F1 契约 §3.0
  「上游对齐 P1-0」）⇒ 上游的 `branch:to:` 通道触发 ≡ freegraph 的边触发（**同款语义**）。
- **理由（硬约束）**：路由通道是 `EphemeralValue`（**单值语义**）；同轮**两个源**节点
  路由到**同一目标**时，写两次同一通道会**触发 V-6**（单值语义通道一轮收到多于一个值
  ⇒ `InvalidChannelUpdateError`）。⇒ **不写**是 freegraph 触发模型下的**唯一**正确选择。

落点：FR-028 · 裁定 8 · 上游对照 **P-14** · 偏离登记 **X-4** · SC-011。

#### Q9（序列返回值与 `Send` 的边界）

→ **A：语义相异，MUST 明确区分**。

- **序列** = **多目标并行 fan-out**，**共享同一份状态**、**无逐目标载荷**
  （实测 **E-9**：两个目标同轮执行 · 各自收到同一份状态）。
- **`Send`** = **带逐目标载荷的推送**（实测 **E-11**：目标节点收到的是 `Send` 携带的载荷，
  **不是**共享状态）。
- 提示词 §8 明确要求区分这两者。

落点：FR-017 · FR-011 · 裁定 9 · SC-008 · SC-012。

#### Q10（路由函数返回 `Send` 时走哪条路径）

→ **A：不另写** —— MUST 复用 **B11F1** 的既有构造器（`make_fanout` / `validate_send`）。

- 同一落点 · 同一入参形态 · 与**节点返回 `Send`** 产生**同款任务**（**V-17…V-21** 同款
  ⇒ ⇒ ⇒ **失败信号与上游的类型分叉见 X-6 / X-7**）。
- **只接线**（H-8 / 下游承接 **D-3**）。

落点：FR-011 · FR-020 · 裁定 10 · SC-008。

#### Q11（路由函数的调用形态）

→ **A：单参 + 双参两形态均支持；双参的第二参 = 用户交给 `invoke` 的原始 `config`（逐字）**。

- 上游的 `self.path.invoke(value, config)`（`langgraph/graph/_branch.py:166`）经由
  `RunnableCallable` ⇒ 支持 1 参 / 2 参两形态（实测 **N-B**）。
- freegraph 照抄**两形态**；双参的第二参是用户交给 `invoke` 的**原始 `config`**
  （`RunConfig` / mapping / `None` · **逐字传入**）⇒ MUST NOT 用 `context` 通道顶替
  （B8F3 的 C21 是另一套机制）⇒ 判别依据 = 第二参的**参数名**是 `config`
  （**不是**位置参数个数）· **永远只传一个位置实参** · `config` 以**关键字**注入
  · 第二参名字**不叫** `config` ⇒ 按**一参**调用（上游同款 `TypeError`）
  · `**kwargs` 形态**不注入**。
- 双参形态**已交付** ⇒ 调用**形态**不记偏离（**P-13 = SAME**）；仅第二参的**内容**是
  freegraph 自有载体语义 ⇒ 登记 **X-5**（**DIFF** · 非更严）。

落点：FR-003 · 裁定 12 · 裁定 16 · 上游对照 **P-13 / P-19** · 偏离登记 **X-5** · SC-021 · clarify 轮（2026-11-17 · Q4 / Q6）。

#### Q12（条件边目标与 `Command.goto` 目标的关系）

→ **A：取并集**（去重保序）。

- 同一节点同轮既返回 `Command(goto=...)` 又有条件边时，两个来源的目标**都**被投递。
- 顺序**不可观察**（同轮执行顺序 = **节点名序** · B7F1 §4），故只需**确定性**即可。

落点：FR-020 · 裁定 13 · Edge Cases · SC-012。

### Session 2026-11-17 · clarify 轮（用户拍板）

> **纪律**（宪法原则 XI + clarify 的收窄纪律）：**上游有答案 ⇒ 照抄 ⇒ 不问用户**；
> 本轮只问了「**上游没答案**」的点（上游**自身无定论**之处 ⇒ 落在**必须自研区 ②**）。
> ⇒ ⇒ ⇒ 每个要问的点都**先查了上游**并附**实测证据**，才决定「可问」。

- **Q1（路由函数返回 `END` 时，是无条件终止，还是照抄上游代码）**：
  上游的**代码**（`langgraph/graph/_branch.py:199-211`）**不**过滤 `END` ⇒ 终止的充要
  条件是「**解析后的目的地**恰为 `'__end__'`」⇒ ⇒ 「`END` 是 `path_map` 的 key」**不等于**
  终止（实测 `path_map = {END: "b"}` ⇒ 路由到 `b`）⇒ ⇒ ⇒ 上游抛 `KeyError: '__end__'`
  的场景是「`path_map` **不含** `END` 键」（查表失败）⇒ ⇒ ⇒ 而上游**自己的 docstring**
  （`langgraph/graph/state.py:999`「If it returns `'END'`, the graph will stop execution.」）
  **相互矛盾** ⇒ 上游**自身无定论** ⇒ 可问。
  → **A：选项 A —— 无条件终止**（**用户 2026-11-17 拍板**）。
  （**精确范围**：**单独返回** `END` ⇒ 无条件终止；**序列内**的 `END` ⇒ **剔除** ·
  其余目标照常执行 · 照抄上游 **E-13** —— 与 FR-019 的三处判定**同款**）
  **理由（用户认可的口径）**：上游**不**在 `_branch.py` 里过滤 `END` ⇒ 终止的充要条件是
  「**解析后的目的地**恰为 `'__end__'`」⇒ ⇒ 「`END` 是 key」**不等于**终止（实测
  `path_map = {END: "b"}` ⇒ 路由到 `b`）⇒ ⇒ ⇒ freegraph 取**无条件**终止 ⇒ 与上游
  **仍有**分叉（`path_map = {END: "b"}` 这类）⇒ ⇒ ⇒ 记 **X-2**；取 docstring 口径
  **更确定**，也符合本项目「替代品」的定位 ⇒ ⇒ ⇒ 与上游代码的分歧**如实登记**（偏离登记
  **X-2** · DIFF），由差分 **D-110 / D-118** 锁住。
  ⇒ 落点：FR-019 · 裁定 5 · 偏离登记 **X-2** · 差分 **D-110 / D-118** · SC-003 · SC-006 ·
  引文差异 3。

- **Q2（路由函数返回 `None` / `START` 等非法值时，是统一抛一种异常，还是照抄上游两态）**：
  上游对**同一个语义失败**给出**两种**类型 —— **有** `path_map` ⇒ 查表**先**失败 ⇒ `KeyError`
  （实测 **E-6 / E-7 / M-C / M-E**）；**无** `path_map` ⇒ 走不到查表 ⇒
  `ValueError("Branch did not return a valid destination")`（实测 **M-B / M-D**）
  ⇒ ⇒ ⇒ 上游的差异源自**查表顺序**，并非刻意设计 ⇒ ⇒ ⇒ 上游**自身无定论** ⇒ 可问。
  → **B：选项 B —— 照抄上游两态**（**用户 2026-11-17 拍板**）。
  **理由（用户原话的口径）**：「**两个场景本来就应该是两种不同类型的 Error**」⇒ ⇒ ⇒
  「有 `path_map`」是**查表**场景 ⇒ ⇒ ⇒ 「无 `path_map`」是**目标非法**场景 ⇒ ⇒ ⇒
  两态各自贴场景 ⇒ ⇒ ⇒ freegraph **逐字照抄**上游的**类型** ⇒ ⇒ ⇒ **不**做统一 ⇒ ⇒ ⇒
  **但**两态的**消息**仍比上游更详细（点名返回值与可选目标）⇒ ⇒ ⇒ 该项仍是 **STRICTER**（**X-1**）。
  ⇒ 落点：FR-021 · FR-022 · FR-025 · 裁定 6 · 偏离登记 **X-1 / X-3** ·
  差分 **D-107 / D-111 / D-113** · SC-006 · SC-007 · 上游对照 **P-07 / P-09** ·
  引文差异 6 / 7。

- **Q3（条件边的路由判定差分：给 B5F2 的差分夹具加分支调度，还是落在既有的全图差分载体里）**：
  上游**无对应物**（这是 freegraph 自己的夹具体系）⇒ ⇒ ⇒ 「上游有答案 ⇒ 照抄」**不适用** ⇒ ⇒ ⇒ 可问。
  → **B：选项 B —— 落 `tests/differential/parity_probe.py`**（**用户 2026-11-17 委托判断**，
  依据「宪法原则 XII 最优设计优先 · 不破不立」）。
  **判断依据（三条实证）**：
  ① **B5F2 的 `driver.py` 是「替身」不是调度器** —— 它用**通道层 + 读取层**模拟一次**线性**执行
  （`driver.py` 模块 docstring 明文「本模块 MUST NOT 含调度逻辑」· 裁定 6 · FR-024）
  ⇒ ⇒ ⇒ 那条禁令是**B5F2 交付时的正确设计**（**调度器当时还不存在** · B7F1 才交付）
  ⇒ ⇒ ⇒ 给它加分支调度 = **在测试替身里重写一遍生产调度器**
  ⇒ ⇒ ⇒ 两个调度器必然**漂移** ⇒ ⇒ ⇒ 差分测到的就不再是「上游 vs freegraph」，
  而是「上游 vs 第二个调度器」⇒ ⇒ ⇒ **不是更优秀的设计**。
  ② **`parity_probe.py` 已是「双真实实现对跑」的载体** —— 上游侧 `StateGraph.compile().invoke()`
  （`parity_probe.py:18`）· freegraph 侧 `freegraph.runtime` 的 `GraphSpec` / `run_super_steps`
   （`:19`）⇒ ⇒ ⇒ 两边都是**真实现** ⇒ ⇒ ⇒ 且已有 **127** 个场景
   （实测：`_scenarios()` 74 + `_builder_scenarios()` 25 + `_compile_scenarios()` 17
   + `_invoke_scenarios()` 11 · 另 `d24_parameter_space()` 的 12 组参数化**另计**
   ⇒ ⇒ ⇒ 口径 = **执行场景 + 构建器场景 + 编译场景 + invoke 场景**）、
   **含 `add_conditional_edges` 的既有场景**（D-29…D-32 · `_fg_branches`）
   ⇒ ⇒ ⇒ 条件边的路由判定差分**属于**那里。
  ③ **「不破不立」的正解** —— 宪法原则 XII 反对的是「在既有次优形态上继续雕花」
  ⇒ ⇒ ⇒ 给替身加调度**正是**雕花；「用真实双跑」才是「不破不立」
  ⇒ ⇒ ⇒ **净收益**：**B5F2 的夹具与 V-4 零改动**
  ⇒ ⇒ ⇒ **破冻结面清单 8 类 → 6 类**（撤除 **T-2** 与冻结断言 **③**）⇒ ⇒ ⇒ ⚠️ **后续增补**：**T-7**（`agent_loop.py` 的 B1 / B2 组软断言 · **EV-2 承接**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **破面全集 = 7 类**（见「破冻结面的回溯修订清单」· Assumptions）⇒ ⇒ ⇒ 追认仍 **1** 次。
  ⇒ ⇒ ⇒ **口径的意图完整落地**：不重造夹具接口（沿用**同一差分体系**的同场景双跑 + 同三投影比对
  + 同「缺席即 skip」纪律）⇒ ⇒ ⇒ B5F2 已产出的**线性链路**差分证据**逐字不作废**
  ⇒ ⇒ ⇒ ⚠️ 提示词 §2「**填值即可复用同一夹具**」的**字面形式**（往 B5F2 夹具的
  `conditional_edges` 字段填值）在 freegraph 侧**不落地**⇒ ⇒ ⇒ 该事实**如实登记**
  （引文差异 **13**）⇒ ⇒ ⇒ **MUST NOT** 假称落地。
  ⇒ 落点：FR-032 · 裁定 **14** / **15** · 破冻结面 **T-2**（本轮取消）· 冻结断言 **③**（本轮取消）·
  引文差异 **13** · SC-019。

- **Q4（路由函数要不要支持 `f(state, config)` 双参形态（上游支持），若支持，第二参传什么）**：
  上游的 `self.path.invoke(value, config)`（`langgraph/graph/_branch.py:166`）经 `RunnableCallable`
  ⇒ ⇒ ⇒ **支持** 1 参 / 2 参两形态 ⇒ ⇒ ⇒ 而第二参在**上游**是 `RunnableConfig`
  ⇒ ⇒ ⇒ 上游**没有**给出「用户那份配置」这一层语义 ⇒ ⇒ ⇒ 可问。
  → **A：选项 A —— 支持双参，第二参逐字传用户交给 `invoke` 的原始 `config`**（用户没传时为 `None`）
  （**用户 2026-11-17 拍板**）。
  **理由（用户认可的口径）**：上游传的也是「**用户自己那份配置**」⇒ ⇒ ⇒ 这样迁移过来的路由函数
  **只差一个类型名** ⇒ ⇒ ⇒ B8F3 的 `context` 通道是**另一套**语义（往图里注入数据，不是运行期配置）
  ⇒ ⇒ ⇒ 两者**不该混** ⇒ ⇒ ⇒ 判别依据见 **Q6**（**第二参的参数名**是 `config`）。
  ⇒ 落点：FR-003 · 裁定 12 · 上游对照 **P-13 / P-19** · 偏离登记 **X-5** · SC-021 · 追溯表 ·
  引文差异 14。

- **Q5（条件边挂在入口哨兵 `__start__` 上时，路由函数会被求值吗）**：
  上游的 `__start__` 是**真实伪节点** ⇒ ⇒ ⇒ 挂在它上面的分支**会**被求值（实测 **N-A**）
  ⇒ ⇒ ⇒ 上游**有**答案 ⇒ ⇒ ⇒ 按纪律**照抄** ⇒ ⇒ ⇒ freegraph 的 `__start__`
  是**哨兵** ⇒ ⇒ ⇒ 故**照抄的是「求值」这件事** ⇒ ⇒ ⇒ 而**不是**把
  `__start__` 变成会执行的节点。
  → **A：会被求值**（照抄上游 · 实测 **N-A**）——freegraph 当前的「静默空跑」是**缺陷**，必须修掉。
  **理由（用户认可的口径）**：上游的 `__start__` 是**真实伪节点** ⇒ ⇒ ⇒ 挂在它上面的分支**会**被求值
  ⇒ ⇒ ⇒ freegraph 的 `__start__` 是**哨兵** ⇒ ⇒ ⇒ 须在**图启动**时求值该路由函数并以其结果
  作为入口目标（**不是**把 `__start__` 变成会执行的节点）。
  ⇒ 落点（**Q5**）：FR-038 · 裁定 17 · SC-022 · 追溯表。

- **Q6（双参路由函数的**判别依据**是「位置参数个数」还是「第二参的参数名是 `config`」）**：
  → **X：照抄上游 —— 判别依据 = 第二参的**参数名**是 `config`**（永远只传一个位置实参 ·
  `config` 以**关键字**注入）· 第二参名字不叫 `config` ⇒ 按**一参**调用 · `**kwargs` 形态不注入
  · 注解不匹配 ⇒ 跳过注入（**用户 2026-11-17 拍板**）。
  **理由**：上游 `RunnableCallable` 是按**参数名**查 `config` 再**关键字注入**的
  （实测：`f(state, cfg)` ⇒ `TypeError`；`f(state, *, config)` ⇒ 拿到 dict；`**kwargs` ⇒ 为空）;
  「位置参数个数」是**推测**而非上游行为 ⇒ 按推测实现会让 freegraph **比上游宽松**
  （`f(state, cfg)` 上游报错、freegraph 正常）⇒ ⇒ ⇒ 那是一条**未登记的偏离**;
  照抄则「调用形态」与「判别规则」**逐字相同** ⇒ **P-13 维持 SAME** ⇒ ⇒ ⇒
  仅第二参的**内容**（以及注解匹配集）不同 ⇒ 归入 **X-5**。
  实测的注解匹配集 = **无注解** ∨ **类对象** `RunnableConfig` ∨ **字符串** `"RunnableConfig"`
  ∨ `Optional[...]` ∨ **PEP-604** 等价形式（`RunnableConfig | None` 亦被接受）∨ 其余
  （`config: dict`）⇒ **跳过注入** ⇒ `TypeError`。
  ⇒ 落点（**Q6**）：FR-003 · 裁定 16 · 上游对照 **P-13 / P-19** · 偏离登记 **X-5** ·
  SC-021 · Edge Cases · Key Entities · Q11 · 差分 **D-115**。

- **Q7（`__start__` 上的条件边与「**唯一入口点**」契约的关系怎么定）**：
  （是否允许**纯条件边入口** · 静态入口与条件入口**并存**时怎么办）
  → **X：照抄上游 —— 允许纯条件边入口**（**无**静态入口点）· 静态入口与条件入口**并存**时
  两个目标**同轮并行**（取并集）· 返回 `END` ⇒ 该分支终止（**用户 2026-11-17 拍板**）。
  **理由**：上游的 `__start__` 是**真实伪节点** ⇒ 挂在它上面的分支**会**被求值（实测：纯条件边
  入口 ⇒ 节点序列 `['b']`；与静态入口并存 ⇒ 两个目标**同轮**并行；返回 `END` ⇒ 节点序列 `[]`）;
  freegraph 的 `_validate_entrypoint` **本就**接受条件入口（`conditional_entry` 分支）
  ⇒ **零新增** · **零破冻结面**; 缺陷只在 **L2**（`__start__` 是哨兵 ⇒ 条件边**永不**被求值
  ⇒ 静默空跑）⇒ MUST 在**图启动**时求值并把结果并入**首轮**目标。
  ⇒ 落点（**Q7**）：FR-038 · FR-039 · 裁定 17 · 上游对照 **P-20** · SC-022 · SC-023 ·
  Edge Cases · 差分 **D-116 / D-117**。

- **Q8（`__start__` 上登记**多条**条件边的纪律怎么定）**：
  （上游：必须给**不同 branch 名**，否则
  `ValueError: Branch with name ... already exists for node __start__`）
  → **X：与普通源节点同款 —— 须不同 branch 名 + 目标取并集**（**用户 2026-11-17 拍板**）。
  **理由**：上游按 `path.name or "condition"` 取 branch 名 ⇒ 同源重名 ⇒ 内置 `ValueError`;
  freegraph 的 `_branch_name` + `add_conditional_edges` **已**是同款口径 ⇒ **零新增**;
  `__start__` **不特例化** ⇒ 单一规则、零特例 ⇒ 上游同款 ⇒ 记 **SAME**。
  ⇒ 落点（**Q8**）：FR-040 · 裁定 18 · 上游对照 **P-21** · SC-024 · 差分 **D-115**。

### 裁定编号映射（本 spec 的唯一裁定编号表）

| 裁定 | 内容 | 来源 |
|---|---|---|
| **裁定 1** | 路由求值落在 L2 `run_super_step(s)` 内部 · **源节点任务成功落回**时求值 · 触发由**动态边**投递 · MUST NOT 另开路径 · MUST NOT 增删编译产物私有字段 | Q1 · H-5 |
| **裁定 2** | fresh 读的唯一实现点 = `local_read(..., fresh=True)` · **显式**传参 · MUST NOT 依赖缺省 · MUST NOT 假设 `managed` 语义 · MUST NOT 在调度层另写一份 | Q2 · H-2 |
| **裁定 3** | 路由函数的入参 = fresh 视图（覆盖整张通道表）· 路由型通道**缺席** · MUST NOT 用名称前缀启发式 | Q3 |
| **裁定 4** | L2 只消费 L3 已归一化的 `path_map`（**dict** 或 **`None`**）· MUST NOT 重新归一化 | Q4 · H-3 · H-4 |
| **裁定 5** | `END` 的判定分**三处**（**单独返回** `END` ⇒ **无条件终止**）：① 路由返回值**本身**是 `END`（**非**序列）⇒ **无条件终止**（判定**先于** `path_map` 查表 ⇒ 即使 `path_map` **不含** `END` 键也终止）；② 返回值经 `path_map` **解析后**的目标是 `END` ⇒ 终止；③ 返回值是**序列**时 ⇒ 序列内的 `END`（**无论以何种形式出现**）⇒ **被剔除**（照抄上游 · 实测 **E-13**）⇒ **不触发**终止 ⇒ 其余目标**照常执行**。 ⇒ ⇒ ⚠️ **上游真相**：上游**不**过滤 `END` ⇒ 终止条件 = 解析后目的地 == `'__end__'` ⇒ ⇒ ⚠️ **2026-11-17 clarify 轮 · 用户拍板（Q1 = 选项 A）** | Q1 · H-5 · clarify 轮（2026-11-17） |
| **裁定 6** | 非法路由返回值的失败信号 **按 `path_map` 形态分两态**（**照抄上游**）：**有** `path_map` ⇒ 查表失败 ⇒ 内置 **`KeyError`**；**无** `path_map` ⇒ 走不到查表 ⇒ 内置 **`ValueError`** ⇒ ⇒ ⇒ 两态的**消息**均**指明返回值与可选目标**（比上游更详细 ⇒ **STRICTER**）⇒ ⇒ ⇒ ⚠️ **2026-11-17 clarify 轮 · 用户拍板（Q2 = 选项 B）** | Q6 · clarify 轮（2026-11-17） |
| **裁定 7** | 无 `path_map` 时目标 MUST 是**已注册节点名**或 `END` ⇒ 否则显式失败 | Q7 |
| **裁定 8** | 路由通道**不被写入**（只作声明载体）· 触发走动态边 ⇒ MUST NOT 触发 V-6 | Q8 |
| **裁定 9** | **序列**返回值 = 多目标并行 fan-out（共享状态 · 无逐目标载荷）⇒ 与 `Send` **语义相异** | Q9 |
| **裁定 10** | 路由函数返回 `Send` / `list[Send]` ⇒ 复用 **B11F1** 的 fan-out 任务构造器 ⇒ MUST NOT 另写条件边专属路径 ⇒ ⇒ ⇒ 「**同款任务**」指 freegraph **内部**的「节点返回 `Send` ⇔ 路由返回 `Send` ⇒ 同款」⇒ ⇒ ⇒ **与上游**的失败信号类型分叉见 **X-6 / X-7** | Q10 · H-8 |
| **裁定 11** | 路由函数抛出的异常以**原始类型 + 原始消息**传播 · MUST NOT 包装 / 吞掉 | 实测 **E-12** · 上游同款 |
| **裁定 12** | 路由函数 MUST 支持**单参**（`f(fresh_view)`）与**双参**（`f(fresh_view, config)`）两形态（**照抄上游**）⇒ ⇒ 双参形态的第二参 = 用户交给 `invoke` 的**原始 `config`**（**逐字传入**）⇒ ⇒ ⇒ 双参形态**已交付** ⇒ **NOT 记为偏离** · C8 挂载点翻为 `landed` | Q11 · H-9 · clarify 轮（2026-11-17） |
| **裁定 13** | 条件边目标与同轮 `Command.goto` 目标**并集**（去重保序） | Q12 · H-7 |
| **裁定 14** | **V-8**（L2 `GraphSpec.conditional_edges`）**放宽** ⇒ 走「登记 + 回溯修订 + 发起者追认」**一次** ⇒ ⇒ ⇒ ⚠️ **V-4 本轮取消放宽**（裁定 15） ⇒ ⇒ ⇒ 破面全集由 **8** 类降为 **6** 类 | H-1 · H-2 · clarify 轮（2026-11-17） |
| **裁定 15** | **差分夹具的落点（最优设计裁定）**：条件边的路由判定差分 MUST 落 `tests/differential/parity_probe.py`（**双真实实现**对跑） ⇒ ⇒ ⇒ B5F2 差分夹具的 `conditional_edges` 字段**保持恒空**（其 freegraph 侧驱动器是**线性替身** · 无调度能力） ⇒ ⇒ ⇒ **V-4 无需放宽** ⇒ ⇒ ⇒ MUST **NOT** 重造夹具接口（沿用**同一差分体系**的同场景双跑 + 同三投影比对 + 同「缺席即 skip」纪律） ⇒ ⇒ ⇒ ⚠️ **「扩展 ≠ 重造」的口径**：为承载条件边载荷而**扩字段**（`Scenario` dataclass 新增条件边字段 + `run_freegraph()` 把 `conditional_edges` 传入 `GraphSpec`）属**同一差分体系内的扩展** ⇒ ⇒ ⇒ **MUST NOT** 新建第二套差分夹具 / 第二条差分执行路径 ⇒ ⇒ ⇒ MUST **NOT** 作废 B5F2 已产出的**线性链路**差分证据 | clarify 轮（2026-11-17 · Q3） |
| **裁定 16** | 路由函数 MUST 支持**单参**与**双参**两形态（**照抄上游**）⇒ ⇒ 双参形态的第二参 = 用户交给 `invoke` 的**原始 `config`**（**逐字传入**）⇒ ⇒ ⇒ 双参的**判别依据 = 第二参的参数名是 `config`**（**不是**位置参数个数）· **永远只传一个位置实参** · `config` 以**关键字**注入 · 第二参名字**不叫** `config` ⇒ 按**一参**调用（上游同款 `TypeError`）· 注解 MUST 落在**匹配集**内：匹配集 = **无注解** ∨ **类对象** `RunConfig` / `Mapping[str, Any]` ∨ **字符串**注解（**每种载体类型两个字面量**：`"RunConfig"` / `"Optional[RunConfig]"` · `"Mapping[str, Any]"` / `"Optional[Mapping[str, Any]]"`）∨ `Optional` / `Union[..., None]` ∨ **PEP-604** 等价形式 · 字符串槽**只**含该两种字面量（上游同款 ⇒ `"RunConfig \| None"` 这样的字符串**不被接受**）· 匹配集与上游 `KWARGS_CONFIG_KEYS` 的 `"config"` 项**同形**（仅载体类型不同 ⇒ **X-5**）· 注解**不在**匹配集内 ⇒ **跳过注入** ⇒ 按**一参**调用 ⇒ `TypeError`（上游同款）⇒ ⇒ ⇒ ⚠️ **freegraph MUST NOT 发 `UserWarning`**（上游的**附带诊断信号** · `langgraph/_internal/_runnable.py:352-359` ⇒ 归偏离 **X-5**）· `**kwargs` 形态**不注入** | clarify 轮（2026-11-17 · Q4）· Q6 |
| **裁定 17** | 条件边挂在 `__start__`（入口哨兵）上时 MUST **求值**该路由函数 ⇒ ⇒ 其结果 MUST 作为**入口目标**（照抄上游 · 实测 **N-A**）⇒ ⇒ ⇒ MUST **NOT** 静默跳过 ⇒ ⇒ ⇒ ⚠️ **入参口径**：`__start__` **无本次写入**（哨兵不执行节点）⇒ 其路由函数看到的 fresh 视图 = **轮次开始前的通道值**（fresh 读**退化为「当前值」**）⇒ ⇒ ⇒ **求值次数 == 1**（**仅在第 1 轮**的触发判定前求值一次 · 后续轮次 MUST **NOT** 再求值 ⇒ **幂等**）⇒ ⇒ ⇒ **允许纯条件边入口**（**无**静态入口点）· 静态入口与条件入口**并存** ⇒ 目标**同轮并行**（**并集**）· 返回 `END` ⇒ 该分支**终止** · `__start__` 上的多条条件边与普通源节点**同款**（须**不同** branch 名 + 目标**并集**） | clarify 轮（2026-11-17 · Q5 · `__start__` 条件边）· Q7 / Q8 |
| **裁定 18** | `__start__` 上的**多条条件边**与普通源节点**同款**：须**不同 branch 名**（重名 ⇒ 内置 `ValueError`）· 目标取**并集**；`__start__` **不特例化** | clarify 轮（2026-11-17 · Q8） |
| **裁定 19** | **EV-2 承接的落成**：`harness/demo/agent_loop.py` 的 **B1「工具循环」**与 **B2「tool_calls 形状」**两组 `soft(...)` MUST 转为**硬断言** ⇒ ⇒ ⇒ **时序**：MUST 在**条件边路由求值就位**之后落地 ⇒ ⇒ ⇒ 否则 CI 必红（宪法 v1.11.0「MUST NOT 写永久红的 CI」）⇒ ⇒ ⇒ 属**破冻结面 T-7** ⇒ ⇒ ⇒ **并入**本 feature 的**唯一一次**追认（追认次数仍 == **1**）⇒ ⇒ ⇒ 「**fake 模型轮**」的**定义** = 猴补（monkey-patch）`init_chat_model` + **含条件边的最小图** / `agent_loop.py` 的**工具循环轮** ⇒ ⇒ ⇒ 本 feature **可达** ⇒ ⇒ ⇒ MUST **真跑**并记录**实测输出**（SC-020 · SC-026）⇒ ⇒ ⇒ 而「`target.py` 端到端轮」**不可达** ⇒ ⇒ ⇒ 具名承接 **B22F1 + B23F1（M2）**· **B25F1（M4）** | H-11 · B7F3 的 **EV-2** |

### 引文差异（提示词初稿 vs 本 spec）

| # | 差异 | 处置 |
|---|---|---|
| **引文差异 1** | 提示词 §2 写「LangGraph 的 `local_read(fresh=True)`（`langgraph/pregel/_algo.py:188-224`）是 C8 语义的**唯一来源**」，但同段又把它称作「`_read_channels` 的 fresh 读」 | **事实订正**：上游 `langgraph 1.2.11` 在 `:188-224` 处的函数名是 **`local_read`**；`read_channels` 是**另一个**函数（`langgraph/pregel/_io.py:38-53`）⇒ ⇒ 本 spec **统一**写 `local_read`（`read_channels` 仅在描述稀疏读时出现） |
| **引文差异 2** | 提示词 §2 写「B7F3 已交付（2026-11-17）」，§头部写「前置依赖 **B5F2, B7F1, B7F3**」 | **事实核对 + 补齐**：B7F3 **确已交付**（`git log` 的 `a625458`）⇒ 成立；但**实际**承接来源还有 **B7F2 / B6F1 / B9F1 / B11F1 / B7F4 / B10F1 / B3F1** ⇒ ⇒ 全部落成 **H-1 … H-11** |
| **引文差异 3** | 提示词 §4 FR-005 写「路由函数返回 `END` 时 MUST 终止整张图」 | **细化（取上游 docstring 口径）**：上游**不**在 `_branch.py` 里过滤 `END` ⇒ 终止的充要条件是「**解析后的目的地**恰为 `'__end__'`」⇒ ⇒ 「`END` 是 `path_map` 的 key」**不**等于终止（实测 `path_map = {END: "b"}` ⇒ 路由到 `b` · **不终止**）⇒ ⇒ 上游抛 `KeyError` 的场景是「`path_map` **不含** `END` 键」（查表失败）⇒ ⇒ 「无 `path_map` + 返回 `END`」⇒ 上游**正常终止**⇒ ⇒ 本 spec 取「**单独返回** `END` ⇒ **无条件**终止」（序列内的 `END` ⇒ **剔除** · 照抄上游 **E-13**）⇒ ⇒ **偏离登记 X-2**（DIFF）⇒ ⇒ 差分 **D-110 / D-118**（`D-110` = `path_map` 不含 `END` 键 ⇒ 上游 `KeyError`；`D-118` = `path_map` 把 `END` 映射到别的节点 ⇒ 上游**不终止**） ⇒ ⇒ ⚠️ **2026-11-17 clarify 轮 · 用户拍板（Q1 = 选项 A）** |
| **引文差异 4** | 提示词 §4 FR-003 写「list：路由函数的返回值**直接**作为目标节点名（取值必须在 list 内）」 | **事实补齐**：上游把 list **归一化为 dict**（`{name: name}` · `langgraph/graph/_branch.py:100-101`）⇒ ⇒ 「返回值 MUST 是**归一化后 dict 的 key**」⇒ ⇒ list 形态下「返回值 = 目标节点名」成立 ⇔ 返回值 ∈ list（**语义等价** · 归一化位置不同） |
| **引文差异 5** | 提示词 §2 写「`path_map` dict 形态的语义是『路由函数返回值 → 目标节点名』的映射」 | **消歧**：dict 的 **key** 是「路由函数的返回值」，**value** 是「目标节点名」⇒ ⇒ 返回值 MUST 是 **key**（否则查表失败） |
| **引文差异 6** | 提示词 §4 FR-006 写「路由返回值**不在 `path_map` 内**时 MUST 抛出明确异常」 | **补齐失败信号**：上游**按 `path_map` 形态分两态**（有 ⇒ 裸 `KeyError` · 无 ⇒ `ValueError` · 实测 E-6/E-7/M-B/M-C/M-D/M-E）⇒ ⇒ 本 spec **照抄两态** + **更详细的消息**（指明返回值与可选目标）⇒ ⇒ **STRICTER**（偏离登记 **X-1**）⇒ ⇒ ⚠️ **2026-11-17 clarify 轮 · 用户拍板（Q2 = 选项 B）** |
| **引文差异 7** | 提示词 §4 FR-006 只覆盖「不在 `path_map` 内」的情形 | **补齐另一半**：**无** `path_map`（动态目标）时，返回一个**未注册**的节点名 ⇒ 上游**静默忽略**（实测 **E-8**）⇒ ⇒ 本 spec **显式失败**（内置 `ValueError` · **X-3** · STRICTER） |
| **引文差异 8** | 提示词 §8 写「不实现 `Send` fan-out 的调度（属 B11F1）」 | **消歧**：B8F1 **不实现** fan-out 调度（已由 B11F1 交付）⇒ 但路由函数返回 `Send` 时 **MUST 复用**它 ⇒ ⇒ 承接条款 **H-8** · 下游承接 **D-3** · 裁定 10 |
| **引文差异 9** | 提示词 §4 FR-004 写「路由函数返回序列 ⇒ 并行 fan-out 到多个节点」 | **补边界**：该 fan-out **共享同一份状态**、**无逐目标载荷** ⇒ ⇒ 与 `Send` **语义相异**（实测 E-9 vs E-11）⇒ ⇒ 裁定 9 |
| **引文差异 10** | 提示词 §4 FR-001 写「在条件边源节点**执行完毕后**求值路由函数」 | **细化落点**：MUST 落在 **L2 的 super-step 循环内部**、于**源节点任务成功落回**时（与上游「分支是源节点的 writer」同款）⇒ ⇒ 节点**挂起**（`interrupt()`）时该任务**不成功落回** ⇒ ⇒ **路由函数不被求值** ⇒ ⇒ 承接条款 **H-10** |
| **引文差异 11** | 提示词 §5 的 **SC-001…SC-005** 与本 spec 的 **SC-001…SC-026** **编号同形、含义不同** | **编号域隔离**：本 spec 的 SC 编号**以本 spec 为准** ⇒ ⇒ 提示词的 SC 编号**作废**（不得引用）⇒ ⇒ 本 spec 正文与「引文差异」表**均不引用**提示词的 SC 编号 |
| **引文差异 12** | 提示词 §7 的「关键实体」表把「路由通道」标为「`EphemeralValue`，每 super-step 清空 · C7 / C8」 | **补齐**：路由通道在 freegraph 里**只作声明载体**、**不被写入**（裁定 8）⇒ ⇒ 它的「每 super-step 清空」属性**对本 feature 无影响**（它从未有值）⇒ ⇒ 上游对照 **P-14** · 偏离登记 **X-4** |
| **引文差异 13** | 提示词 §2「**填值即可复用同一夹具**」（B5F2 的夹具已预留 `conditional_edges` 字段） | **字面形式不落地**：B5F2 差分夹具的 freegraph 侧驱动器是**线性替身**（无调度能力）⇒ ⇒ 填值**无消费者**⇒ ⇒ 条件边的路由判定差分改落**同一差分体系**内的 `tests/differential/parity_probe.py`（**双真实实现**对跑）⇒ ⇒ **V-4 无需放宽**（裁定 15） ⇒ ⇒ ⇒ ⚠️ **上位文档（立项书）口径**：立项书 **§5.2** 的 B8F1 行写「**差分测试夹具建立**」、**§4.2 S5** 的脚注写「差分夹具在 **B5F2** 与 **B8F1** **首次建立**」 ⇒ ⇒ ⇒ **以立项书 §5.9 的 E-5**（2026-11-12 ·「每个 feature MUST 有自己的**场景组**」）**为准** ⇒ ⇒ ⇒ 判据**只收紧**（证据更全）⇒ ⇒ ⇒ **不**单方面修改立项书（属**发起者**职权）· 登记落 `plan.md` 的**登记项 R-5** |
| **引文差异 14** | 提示词 §7 的 **C7** 写 `path_fn(state)`（**单参**形态） | **补齐**：上游**也**支持双参形态 ⇒ ⇒ freegraph 照抄**支持**两形态（关系 **SAME**）⇒ ⇒ ⇒ 但第二参的**内容**是 freegraph 自有的载体语义 ⇒ ⇒ ⇒ 登记 **X-5**（**DIFF** · 非更严） |
| **引文差异 15** | 提示词 §7 的 **C7** 只写「`path_fn(state)`（单参）」 | ⇒ ⇒ ⇒ **补齐**上游的 `config` 注入规则（**按参数名** · **关键字注入** · 永远只传一个位置实参）⇒ ⇒ ⇒ freegraph **照抄** ⇒ 关系 **SAME**（**P-13**）⇒ ⇒ ⇒ 第二参的**内容**与**注解匹配集**是 freegraph 自有载体语义 ⇒ 登记 **X-5** |
| **引文差异 16** | 提示词**未提**「条件边挂在 `__start__` 上」这一情形 | ⇒ ⇒ ⇒ **补齐**：照抄上游（`__start__` 上的条件边**会被求值** · 允许**纯条件边入口** · 与静态入口**并存**时**同轮并行**）⇒ ⇒ ⇒ 关系 **SAME**（**P-20**）⇒ ⇒ ⇒ freegraph 当前的「静默空跑」被标为**缺陷** |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 路由基于本节点的最新产出 (Priority: P1)

作为用户，我的模型节点刚写入了带 `tool_calls` 的消息，路由函数据此决定「去工具节点」
还是「结束」—— 我要求路由函数**看到**那条刚写进去的消息，而不是执行前的旧值。

**Why this priority**: 这是本 feature 的**最高判据**（提示词 P1 / A1 / SC-001），
也是全项目**最易被静默破坏**的两条契约之一（**C8**）。若路由函数读到旧消息，
`target.py` 的 `should_continue` 会判定「不调用工具」⇒ 工具循环失效（退化为单轮）或死循环。

**Independent Test**: 建一张 2 节点的图（`writer` 写 `{"messages": ["fresh"], "llm_calls": 7}`，
`router` 记录收到的状态后返回 `"after"`）⇒ 调 `invoke` ⇒ 断言路由函数收到的状态里
`messages == ["fresh"]` 且 `llm_calls == 7` ⇒ ⇒ ⇒ **否定式断言**（断言它**看到了**新值，
而不只是「跑通了」）。

**Acceptance Scenarios**:

1. **Given** 一个节点写入 `{"messages": ["fresh"], "llm_calls": 7}`，
   **When** 它的条件边被求值，**Then** 路由函数收到的状态里 `messages == ["fresh"]`
   且 `llm_calls == 7`（**C8 fresh 读**）。
2. **Given** 同一张图且 `messages` 是**归约型**通道（初始值 `["seed"]`），
   **When** 路由函数被求值，**Then** 它看到的 `messages == ["seed", "fresh"]`
   （**归约器已在 fresh 读里生效** · 实测 **E-16**）。
3. **Given** 一个**无值**的**覆盖型**通道，**When** 路由函数被求值，
   **Then** 该 key **不在**路由函数的入参里（**稀疏** · 与节点入参同款口径）。
4. **Given** 同一轮里还有**另一个**节点在写状态，**When** 源节点的条件边被求值，
   **Then** 路由函数**看不到**那另一个节点的写入（fresh 读 = **本节点本次**写入 · 不是全轮）。

---

### User Story 2 - 两种 path_map 都能用 (Priority: P1)

作为用户，我用 list 声明「可去的节点」，也用 dict 声明「返回值 → 节点」的映射——
两种写法都要能跑通，且路由结果与我的声明一致。

**Why this priority**: 提示词 P2 / A4 / SC-002 的直接判据；也是 `harness/demo/graph_core.py`
A5 组的**硬断言**内容（该组当前是**软断言**并注「归 B8F1」）。

**Independent Test**: 一张带条件边的图分别以 list 形态与 dict 形态登记 ⇒ 两次 `invoke`
⇒ 断言两次都路由到**预期节点**（节点执行次数 == 1 · 另一目标节点执行次数 == 0）。

**Acceptance Scenarios**:

1. **Given** `add_conditional_edges("r", router, ["a", END])` 且 `router` 返回 `"a"`，
   **When** 调 `invoke`，**Then** 节点 `a` **执行 1 次**，`END` 之后**无**节点执行。
2. **Given** `add_conditional_edges("r", router, {"hit": "a", "miss": "b"})` 且 `router`
   返回 `"hit"`，**When** 调 `invoke`，**Then** 节点 `a` **执行 1 次** · 节点 `b`
   **执行 0 次**。
3. **Given** dict 形态且 `router` 返回的值**不在** `path_map` 内，
   **When** 调 `invoke`，**Then** 抛内置 `KeyError`，且消息**指明返回值**与**可选目标**。
4. **Given** list 形态且 `router` 返回的值**不在** list 内，
   **When** 调 `invoke`，**Then** 抛内置 `KeyError`（与 dict 形态**同款**）。

---

### User Story 3 - 返回 END 真的终止 (Priority: P1)

作为用户，路由函数返回 `END` 时，整张图停止执行，不再进入后续节点—— 我不想看到
「`END` 被当成一个普通节点名然后报错」。

**Why this priority**: 提示词 P3 / A3 / SC-003 的直接判据；`END` 是**终止标记**
（**C9**）而不是节点名。

**Independent Test**: 一张「`r` →（条件边）→ `after`」的图，路由函数返回 `END`
⇒ 调 `invoke` ⇒ 断言节点 `after` 的**执行次数 == 0**。

**Acceptance Scenarios**:

1. **Given** 路由函数返回 `END`，**When** 调 `invoke`，**Then** 目标节点**执行 0 次**
   ⇒ ⇒ ⇒ 整张图**终止**。
2. **Given** `path_map` 为 `{"stop": END, "go": "a"}` 且路由函数返回 `"stop"`，
   **When** 调 `invoke`，**Then** 同样**终止**（`END` 作为 `path_map` 的 **value**）。
3. **Given** `path_map` **不含** `END` 键（如 `{"go": "a"}`）且路由函数返回 `END`，
   **When** 调 `invoke`，**Then** **仍然终止**（不抛错）⇒ ⇒ ⇒ 「**单独返回** `END` ⇒ **无条件终止**」是本 feature
   与上游的一处分叉（**X-2**）。
4. **Given** 路由函数返回序列 `[END, "a"]`，**When** 调 `invoke`，
   **Then** 节点 `a` **执行 1 次**（`END` 被剔除）且不终止整张图。

---

### User Story 4 - 路由判错时立刻指出 (Priority: P2)

作为用户，我的路由函数拼错了一个目标名，我希望**立刻**拿到一个说清「你返回了什么、
可以返回什么」的异常，而不是让图「看起来成功」却悄悄少跑一条分支。

**Why this priority**: 与 B7F3 的 **X-2**（未知 key ⇒ 显式失败）**同类**的诊断价值；
上游在**动态目标**（无 `path_map`）情形下是**静默忽略**（实测 **E-8**）⇒ 本 feature
**刻意更严**（**X-1 / X-3**）。

**Independent Test**: 一张带条件边的图，路由函数返回一个不存在的节点名
⇒ 调 `invoke` ⇒ 断言抛**内置异常**且消息**含**该返回值与**可选目标清单**
⇒ ⇒ ⇒ **无** `path_map` ⇒ 内置 **`ValueError`**（**FR-022**）· **有** `path_map` ⇒ 内置
**`KeyError`**（**FR-021**）。

**Acceptance Scenarios**:

1. **Given** `path_map` 为 `{"hit": "a"}` 且路由函数返回 `"nope"`，
   **When** 调 `invoke`，**Then** 抛 `KeyError`，消息**含** `"nope"` 与**可选目标**。
2. **Given** **无** `path_map` 且路由函数返回 `"ghost"`（未注册节点），
   **When** 调 `invoke`，**Then** 抛内置 **`ValueError`**（**不**是静默结束
   ⇒ ⇒ ⇒ 上游**同场景**是**静默忽略** ⇒ freegraph 更**确定** · **X-3**）。
3. **Given** 路由函数**自己**抛了一个异常，**When** 调 `invoke`，
   **Then** 该异常以**原始类型 + 原始消息**到达调用方（**不**被包装）。

---

### User Story 5 - 一次路由到多个目标 (Priority: P2)

作为用户，我的路由函数返回一个序列时，我希望**并行**跑到那几个目标节点，
且它们各自拿到**同一份**共享状态。

**Why this priority**: 提示词 FR-004；与 `Send` 的**逐目标载荷**语义**必须区分**
（裁定 9 · 提示词 §8 明确要求）。

**Independent Test**: 一张「`r` →（条件边）→ `b` / `c`」的图，路由函数返回 `["b", "c"]`
⇒ 调 `invoke` ⇒ 断言 `b` 与 `c` **各执行 1 次**且**同轮**完成。

**Acceptance Scenarios**:

1. **Given** 路由函数返回 `["b", "c"]`，**When** 调 `invoke`，
   **Then** `b` 与 `c` **各执行 1 次**（并行 fan-out）。
2. **Given** 同一张图，**When** 比较两个目标节点收到的入参，**Then** 两者**逐字相等**
   （**共享状态** · **无**逐目标载荷）。
3. **Given** 路由函数返回 `[Send("b", payload)]`，**When** 调 `invoke`，
   **Then** 节点 `b` 收到的是**载荷**（**不是**共享状态）⇒ ⇒ ⇒ 与上一条**语义相异**
   （裁定 9）。

---

### User Story 6 - 执行过程零副作用 (Priority: P3)

作为用户，我希望「路由一次」**不**偷偷联网、**不**读我的环境变量、**不**引入任何第三方
依赖 —— 以免「只是跑一次图」却触发了副作用。

**Why this priority**: 宪法原则 I（零出站 / 零环境变量）与原则 X（依赖门禁）是**红线**；
且执行期副作用会与「图逻辑本身的副作用」混淆，破坏可诊断性。

**Independent Test**: 用 socket 监测夹具 + `sys.modules` 快照观测 ⇒ 断言出站连接数 == 0、
`langchain*` / `langgraph*` / `langsmith` 出现次数 == 0。

**Acceptance Scenarios**:

1. **Given** 任意环境变量（含 `LANGSMITH_*`），**When** 调 `invoke`，
   **Then** 执行行为**不因环境变量而改变**，且 freegraph 自身发起 **0** 次出站连接。
2. **Given** 一次完整的 `invoke`（含条件边求值），**When** 检查导入面，
   **Then** `sys.modules` 中 `langchain` / `langchain_core` / `langgraph` / `langsmith`
   的出现次数 == **0**。

---

### Edge Cases

- **路由返回值不在 `path_map` 内**：MUST 抛内置 `KeyError`；消息 MUST **指明返回值**与
  **可选目标**（上游只有 key 本身 ⇒ **STRICTER** · **X-1**）。
- **无 `path_map` 且返回值不是已注册节点名 / `END`**：MUST **显式失败**（内置
  **`ValueError`** · **FR-022**）⇒ ⇒ ⇒ 上游**同场景**是**静默忽略**（只打一条 warning）
  ⇒ ⇒ ⇒ freegraph 更**确定**（偏离 **X-3**）⇒ ⇒ ⇒ MUST NOT 逐字照抄上游的静默。
- **路由函数返回 `END` 而 `path_map` 不含 `END` 键**：MUST **终止**（不抛错）
  ⇒ ⇒ ⇒ 与上游的 `KeyError` 分叉（**X-2** · DIFF）。
- **路由函数返回空序列 `[]`**：MUST 视为「**无目标**」⇒ 该源节点**不再触发**任何目标
  ⇒ ⇒ ⇒ MUST NOT 报错（空序列**不是**非法返回值）。
- **路由函数返回 `None`**：MUST 显式失败。**有** `path_map` ⇒ 内置 `KeyError`（上游同款 · 实测 **M-C**）；
  **无** `path_map` ⇒ 内置 `ValueError`（上游同款 · `ValueError("Branch did not return a valid destination")` · 实测 **M-B**）。
  ⇒ ⚠️ **两态**是 **2026-11-17 clarify 轮 · 用户拍板（Q2 = 选项 B）**的口径（照抄上游 · 两个场景本就是两种失败）。
- **路由函数返回 `START`（`'__start__'`）**：MUST 显式失败（入口哨兵不是合法目标）——
  **照抄上游的「查表优先」判定顺序**（**FR-025**）。**有** `path_map` ⇒ 内置 `KeyError`
  （上游同款 · 实测 **M-E** · 查表失败）；**无** `path_map` ⇒ 内置 `ValueError`
  （上游同款 · 实测 **M-D**）⇒ ⇒ ⇒ ⚠️ 若 `path_map` 恰含 `__start__` **键**且其 **value**
  合法 ⇒ **照上游路由到该 value**（**不**失败）⇒ ⇒ ⇒ `START` **不**是独立的失败条件。
- **路由函数返回 `list` / `tuple`**：**不是**「一个不可哈希的 key」，而是「**多目标**」（上游同款 ·
  `langgraph/graph/_branch.py:199-200` · 实测 **M-F**）⇒ 元素**逐个**查表 ⇒ 只有**元素**不可哈希时才在查表时失败。
- **路由函数返回非 `str` 的可哈希值**（如 `int`）：MUST 作为 `path_map` 的 **key**
  正常查表（实测 **E-14 / E-15**）⇒ ⇒ ⇒ 返回的 **`tuple`** **不是**一个 key ⇒ 按
  **多目标**解释（**逐元素**查表 · `langgraph/graph/_branch.py:199-200` · **FR-024**）
  ⇒ ⇒ ⇒ 返回的 **`list`** 同款 ⇒ ⇒ ⇒ 每个元素**各自**查表。
- **路由函数抛异常**：MUST 以**原始类型 + 原始消息**传播（实测 **E-12**）⇒ MUST NOT 包装。
- **源节点任务挂起（`interrupt()`）**：该任务**不成功落回** ⇒ ⇒ ⇒ **路由函数 MUST NOT**
  被求值（承接条款 **H-10**）⇒ ⇒ ⇒ 中断路径与路由路径**互斥**。
- **源节点同轮既返回 `Command(goto=...)` 又有条件边**：两个来源的目标 MUST 取**并集**
  （去重保序 · 裁定 13）⇒ ⇒ ⇒ 同轮执行顺序仍为**节点名序**（顺序**不可观察**）。
- **同轮两个源节点路由到同一目标**：MUST **正常执行**（不得触发 V-6 · 裁定 8 的
  「路由通道不被写入」是这一条能成立的前提）。
- **路由通道出现在 fresh 视图里**：MUST **缺席**（上游同款 · B5F2 `read-contract.md` §3.1）。
- **路由通道出现在 `invoke` 的返回键集里**：MUST **不出现**
  （`EphemeralValue` ⇒ 不在 schema key 集 · B7F3 的裁定 4）。
- **条件边源节点**同时有**静态入边**：静态边与条件边**并存**⇒ ⇒ ⇒ 条件边的目标集合与
  静态边的目标集合是**两套**语义（承接条款 **H-6**）⇒ ⇒ ⇒ **MUST NOT** 把「多源边」
  当作「条件边」求值。
- **同一源节点登记两条条件边**（不同 `branch`）：MUST **各求值一次** ⇒ ⇒ ⇒ 目标取
  **并集**（去重保序）。
- **路由函数返回序列且序列中含重复目标**：MUST **去重保序**（同一目标**只**触发一次）。
- **条件边的目标节点同时是另一个条件边的源节点**：MUST 正常形成**链式**路由
  ⇒ ⇒ ⇒ 每轮各求值一次。
- **路由形成环**（条件边回到上游节点）：MUST 受既有 `recursion_limit` 约束 ⇒
  超限抛 `GraphRecursionError`（**不包装** · B13F1 的既有口径）
  ⇒ ⇒ ⇒ ⚠️ **判定载体 = `tasks.md` 的 T029**（与「每源每次只求值一次」同一条用例）。
- **路由函数返回的序列里混入 `Send` 与普通目标名**：MUST 分别按**各自**语义处理
  （`Send` ⇒ fan-out 任务 · 普通目标名 ⇒ 共享状态的动态边）⇒ ⇒ ⇒ 两者**并行**投递。
- **`invoke` 被调用于**未编译**的构建器**：MUST NOT 存在这条路径（执行入口在编译产物上）。
- **`stream()` / `get_graph()` / `get_state()` / `get_state_history()` / `update_state()`**：
  本 feature **不**实现 ⇒ ⇒ ⇒ 仍抛内置 `NotImplementedError` 且消息**点名归属 feature**
  （B7F2 口径不变 · B7F3 的 FR-026 不变）。
- **路由函数写成双参 `f(state, config)`**：第二参 MUST 是用户交给 `invoke` 的**原始 `config`**
  （**逐字传入**）· MUST **NOT** 含 `context` 通道（B8F3 的 C21 机制）
  · 判别依据 = **参数名**（不是位置参数个数）。
- **路由函数的第二参名字不叫 `config`**（如 `f(state, cfg)`）：MUST 按**一参**调用
  （上游同款 ⇒ `TypeError`）· MUST **NOT** 凭位置个数补传第二参。
- **路由函数带 `**kwargs`****：MUST **NOT** 注入 `config`（上游同款 ⇒ kwargs 为空）
  · 第二参**名字**为 `config` 时，其注解 MUST 落在**匹配集**内（**无注解** / **类对象** /
  **字符串** / `Optional` / `Union[..., None]` / **PEP-604** 等价形式）
  ⇒ 字符串槽**只**含**每种载体类型两个**字面量（`"RunConfig"` / `"Optional[RunConfig]"`
  · `"Mapping[str, Any]"` / `"Optional[Mapping[str, Any]]"`）⇒ 上游同款 ⇒
  `"RunConfig | None"` 这样的**字符串****不被接受**
  ⇒ 匹配集外的注解（上游如 `config: dict`）⇒ MUST **跳过注入** ⇒ 按**一参**调用 ⇒ `TypeError`
  ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 发 `UserWarning`（上游的附带诊断信号 · 归偏离 **X-5**）。
- **条件边挂在 `__start__` 上**：MUST **求值**该路由函数并以其结果作为**入口目标**
  ⇒ ⇒ ⇒ MUST **NOT** 静默产出一场**空跑**（**缺陷**）· 纯条件边入口（**无**静态入口点）
  MUST 可行。
- **纯条件边入口**（`__start__` 上有条件边 · **无**静态入口点）：MUST 允许
  ⇒ 图从**路由结果**起步 ⇒ 返回 `END` ⇒ 图**直接结束**
- **静态入口与 `__start__` 条件边并存**：两者的目标 MUST **同轮并行**（取**并集**）
  · MUST NOT 只跑静态入口那条

---

## Upstream Parity *(mandatory — 宪法 v1.12.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11**（取证于 2026-11-17 ·
`/home/ctyun/workspace/github/freegraph/.venv/lib/python3.11/site-packages/langgraph`）
· `langchain-core` **1.7.6**（同目录取证）· 仓库钉死：`pyproject.toml:100`
（`"langgraph==1.2.11"` ⇒ 换版本 MUST **重新核实全部行号**）。

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | 条件边的**登记方法与签名** | `langgraph/graph/state.py:982-989`（`add_conditional_edges(source, path, path_map=None)`） | 同款：`add_conditional_edges(source, path, path_map=None)`（L3 · B6F1 已交付） | SAME | 原则 XI 照抄 · 门面已由 B6F1 冻结 |
| P-02 | `path_map` 的 **list / dict 双形态** | `langgraph/graph/_branch.py:96-101`（dict ⇒ `copy()` · list ⇒ `{name: name}`）· `:112-114`（`None` ⇒ 从 `Literal[...]` 注解推断） | 消费 L3 **已归一化**的结果（dict 或 `None`）⇒ ⇒ L2 **零归一化** | SAME | 归一化位置不同（L3 vs 上游的 L3 同层）⇒ 行为面**逐字同款** |
| P-03 | **路由求值的时机** | `langgraph/graph/state.py:1624`（`self.nodes[start].writers.append(branch.run(get_writes, reader))` ⇒ 分支是**源节点的 writer**）· `langgraph/graph/_branch.py:146-167` | 源节点任务**成功落回**时求值 | SAME | 上游同款 ⇒ 原则 XI 照抄（裁定 1） |
| P-04 | **fresh 读**（C8 的唯一来源） | `langgraph/pregel/_algo.py:188-224`（`local_read` · `:211-219` 的 `fresh=True` 分支：每个通道 `copy()` + `update(updated[k])`）· `langgraph/graph/state.py:1613-1617`（`ChannelRead.do_read(..., fresh=True)`）· **实测 E-1 / E-16** | `local_read(channels, writes, fresh=True)`（**显式**传参） | SAME | 上游同款 ⇒ 原则 XI 照抄（裁定 2）· C8 的**唯一来源** |
| P-05 | 路由函数的**入参** | **实测 E-10**：全部 schema 通道 `['llm_calls','messages']`（**不是**源节点订阅集）· `langgraph/graph/state.py:1615`（`select=channels`） | fresh 视图（覆盖整张通道表 · 路由型通道**缺席**） | SAME | 上游同款 ⇒ 两者**可观察等价**（裁定 3） |
| P-06 | 路由函数**返回值**的形态 | `langgraph/graph/_branch.py:199-200`（标量包成 1 元列表 · `list`/`tuple` ⇒ 多目标） | 同款 | SAME | 上游同款 ⇒ 原则 XI 照抄 |
| P-07 | `path_map` **key** 的查表 | `langgraph/graph/_branch.py:202-204`（`self.ends[r]`）· **实测 E-6 / E-7 / M-C / M-E** ⇒ `KeyError`（消息只有 key） | 查表 + 内置 `KeyError`（**类型逐字同款**）+ **消息指明返回值与可选目标** | **STRICTER** | 原则 XI「失败信号 MAY 更严」+ 原则 XI ② 类 ⇒ **X-1** |
| P-08 | 返回 `END` 的**终止** | **实测 E-3 / E-4 / E-5 / E-5b** ⇒ 上游**不**在 `_branch.py` 里过滤 `END` ⇒ 终止的充要条件是「**解析后的目的地**恰为 `'__end__'`」⇒ ⇒ 「`END` 是 `path_map` 的 key」**不**等于终止（实测 `path_map = {END: "b"}` ⇒ 路由到 `b` · **不终止**）⇒ ⇒ 上游抛 `KeyError` 的场景是「`path_map` **不含** `END` 键」（查表失败）⇒ ⇒ 「无 `path_map` + 返回 `END`」⇒ 上游**正常终止** | `END` **单独返回**（**非**序列）⇒ **无条件**终止（查表**前**判定）⇒ 序列内的 `END` ⇒ **剔除**（照抄上游 · 实测 **E-13**） | **DIFF** | 上游**代码**与上游**自己的 docstring**（`state.py:999`）矛盾 ⇒ 原则 XI ② 类（上游自身的不确定）⇒ 取 docstring 口径（**更确定**）⇒ **X-2** |
| P-09 | **无** `path_map` 时的非法目标 | **实测 E-8 / M-B / M-D** ⇒ 非法**节点名**被**静默忽略**；`None` / `START` ⇒ `ValueError` | 非法**节点名** ⇒ 显式失败（内置 `ValueError`）；`None` / `START` ⇒ 内置 `ValueError`（**类型逐字同款**）+ 更详细消息 | **STRICTER** | 原则 XI ② 类（上游的静默忽略）+ 与 B7F3 的 **X-2** 同类 ⇒ **X-3** |
| P-10 | **序列**返回 ⇒ 多目标 fan-out | **实测 E-9**（两个目标**同轮**执行 · 各自收到**同一份**状态） | 同款（动态边投递 · 共享状态） | SAME | 上游同款 ⇒ 原则 XI 照抄（裁定 9） |
| P-11 | 路由函数返回 **`Send`** | **实测 E-11**（目标节点收到的是 `Send` 携带的**载荷**）· `langgraph/graph/_branch.py:203`（`Send` 实例**不**查表） | 复用 **B11F1** 的 fan-out 任务构造器 | SAME | 上游同款 ⇒ 原则 XI 照抄（裁定 10）· ⚠️ 本行的 SAME **仅**指**任务形态 / 载荷语义** ⇒ ⇒ ⇒ **失败信号**的类型分叉见 **P-22 / P-23**（**X-6 / X-7**） |
| P-12 | 路由函数**抛异常** | **实测 E-12**（`RuntimeError: boom` **原样**传播） | 原样传播（原始类型 + 原始消息） | SAME | 上游同款 ⇒ 原则 XI 照抄（裁定 11） |
| P-13 | 路由函数的**调用形态与判别规则** | `langgraph/graph/_branch.py:166`（`self.path.invoke(value, config)`）⇒ 经 `RunnableCallable`（`langgraph/_internal/_runnable.py:299` · `langgraph/utils/runnable.py` 仅为**兼容再导出**）⇒ 判别按**参数名 `config`** ⇒ **关键字注入** ⇒ 永远只传一个位置实参（实测 **N-B** + 本轮实测 `f(state, cfg)` ⇒ `TypeError`） | **同款** —— **单参**与**双参**两形态均支持 · 判别按**参数名 `config`** · **关键字注入** | **SAME** | 调用**形态**与**判别规则**逐字相同 ⇒ 第二参的**内容**是 freegraph 自有的载体语义（见 **P-19**）⇒ ⇒ ⇒ ⚠️ **注入被跳过时的附带诊断信号**（上游发 `UserWarning` · freegraph **不发**）⇒ ⇒ ⇒ **归 P-19 / X-5**（**DIFF**）⇒ ⇒ ⇒ 调用**形态**与**判别规则**本身**逐字同款** ⇒ ⇒ ⇒ **P-13 维持 SAME** |
| P-14 | **路由通道**的写入 | `langgraph/graph/state.py:1583-1592`（`get_writes` ⇒ 写 `branch:to:<target>` ⇒ **触发**）· `:1525-1530`（通道为 `EphemeralValue(Any, guard=False)`） | 路由通道**只作声明载体** · **不被写入** · 触发走**动态边** | DIFF（结构差异 · 非更严） | freegraph 的触发源恒为**边**（B7F1 §3.0）⇒ 上游的通道触发 ≡ freegraph 的边触发；⇒ 而路由通道是**单值语义**（写两次 ⇒ V-6）⇒ **不写**是唯一正确选择（裁定 8）⇒ **X-4** |
| P-15 | `END` 常量的**值** | `langgraph/constants.py:28`（`END = sys.intern("__end__")` ⇒ 值 `"__end__"`） | `freegraph.graph.END == "__end__"`（`src/freegraph/graph.py:45`） | SAME | 上游同款 ⇒ 原则 XI 照抄 |
| P-16 | 路由通道**不进**返回键集 | 上游的 `branch:to:*` **不在** output schema（`langgraph/graph/state.py:1526-1530` 建在 `self.channels` 而非 schema） | `EphemeralValue` ⇒ 不在 schema key 集（B7F3 的裁定 4 · `isinstance(channel, EphemeralValue)`） | SAME | 上游同款 ⇒ 原则 XI 照抄 |
| P-17 | 路由函数入参是否含节点返回的**非 schema key** | `langgraph/graph/_branch.py:158-163`（passthrough：`value = {**input, **value}`） | freegraph **拒绝**未知 key（`InvalidUpdateError` · B7F3 的 **X-2**）⇒ **无** passthrough 需求 | DIFF（源自**更严**的未知 key 口径 · 非更严） | 上游的 passthrough 是它「未知 key 只告警」的上游条件下的伴生行为 ⇒ freegraph 在该处**更早失败** ⇒ 路由函数**看不到**非 schema key ⇒ **不构成**行为面的分叉 |
| P-18 | **零出站 / 零环境变量 / 零第三方依赖** | —（上游是依赖方 · 本项目是**替代方**） | 同款（零出站 · 零环境变量 · 零 `langchain*` / `langgraph*` / `langsmith`） | SAME | 宪法原则 I / X（**红线**）· 与上游**无冲突**（上游的依赖面被**主动排除**） |
| P-19 | 双参形态的**第二参内容** | 上游传的是 `RunnableConfig`（dict 形态）· 锚点：`langgraph/pregel/main.py` 的 `RunnableConfig`（dict）形态（**行号随版本变动**） | freegraph 传的是用户交给 `invoke` 的**原始 `config`**（`RunConfig` / mapping / `None`）· **逐字传入** | **DIFF** | **载体形态差异** ⇒ **非更严**（调用**形态**与上游同款 · 见 **P-13**）⇒ 已登记为偏离登记 **X-5** ⇒ ⇒ ⇒ ⚠️ **附带诊断信号**（上游在注解不匹配时发 `UserWarning` · freegraph **不发**）⇒ ⇒ ⇒ 同属**载体形态差异**族（**非更严** · 失败信号 `TypeError` **逐字同款**）⇒ ⇒ ⇒ **归 X-5** · 上游的 `config` **注解匹配集** = `RunnableConfig` · freegraph = `RunConfig \| Mapping \| None` ⇒ 注解**匹配集**亦不同（同属载体形态差异 · **非更严**）⇒ ⇒ ⇒ freegraph 的匹配集与上游 `KWARGS_CONFIG_KEYS` 的 `"config"` 项**同形**（类对象 / 字符串 / `Optional` / PEP-604 / 空）⇒ ⇒ ⇒ 仅**载体类型**不同（`RunnableConfig` ⇒ `RunConfig \| Mapping[str, Any]`） |
| P-20 | `__start__` 上的**条件边**是否被求值 | 上游的 `__start__` 是**真实伪节点**（带 `__pregel_pull` 任务 · `langgraph/pregel/_algo.py`）⇒ 挂在它上面的分支**会**被求值 ⇒ 纯条件边入口**可行** · 并存时两个目标**同轮并行** | freegraph **同款** —— `__start__` 上的条件边 MUST 被求值 · 允许纯条件边入口 · 并存时**同轮并行** | **SAME** | 照抄上游 ⇒ 当前 freegraph 的「静默空跑」是**缺陷**而非口径差异 ⇒ **FR-038 / FR-039** 修正它 |
| P-21 | 条件边的 **branch 名**纪律 | `langgraph/graph/state.py` 的 `add_conditional_edges`（`name = path.name or "condition"` ⇒ 同源**重名** ⇒ 内置 `ValueError`） | freegraph **同款** —— `_branch_name` 取 `__name__`（缺省 `"condition"`）· 重名 ⇒ 内置 `ValueError`（消息点名分支名与源节点） | **SAME** | freegraph **已实现**该校验 ⇒ 本 feature **零新增** ⇒ `__start__` 亦**不特例化** |
| P-22 | 路由函数返回 **`Send`** → **未注册节点**的**失败信号** | **实测 E-22**：上游**静默忽略**（**不**抛错 · `langgraph/graph/_branch.py:205-206` 把返回值直接当节点名） | **显式失败**（内置 `ValueError` · B11F1 的 **V-19** · `src/freegraph/runtime/_fanout.py:56-82`）⇒ ⇒ ⇒ MUST **NOT** 改 B11F1 的冻结面 | **STRICTER** | 原则 XI ② 类（上游的**静默忽略**）+ 与 B7F3 的 **X-2** 同类 ⇒ ⇒ 「拼错的 `Send` 目标无声地少跑一条分支」会让图「看起来成功」却结果不对 ⇒ ⇒ ⇒ **X-6** |
| P-23 | 路由函数返回 **`Send`** → **`END`** 的**失败信号类型** | **实测 E-21**：上游抛 **`InvalidUpdateError`**（`langgraph/graph/_branch.py:209-210`） | 内置 **`ValueError`**（B11F1 的 **V-21** · `validate_send`）⇒ ⇒ ⇒ **类型不同型** ⇒ ⇒ ⇒ MUST **NOT** 改 B11F1 的冻结面 | **DIFF** | freegraph **零新增错误类型**（只用**内置**异常）⇒ ⇒ ⇒ 与上游的**异常类型家族**不同 ⇒ ⇒ ⇒ **非更严**（上游更宽）⇒ ⇒ ⇒ **X-7** |

> ⚠️ **双份维护的同步义务（2026-11-17 · 与 B7F3 同款）**：本表与下方「偏离登记」表**同时**落成于
> `contracts/upstream-parity.md` §2 / §4（该文件带 `<!-- authority: yes -->` 标记）
> ⇒ ⇒ ⇒ ⇒ ⇒ **两处是「同一份内容的两处落点」** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **发现漂移 MUST 双侧同改**
> （MUST NOT 只改一侧）。
>
> ⚠️ **严格三态标注（宪法 v1.12.0 原则 XI 末条）**：本表「关系」列与下方「偏离登记」的「类别」列
> **逐字相等**（`SAME` / `STRICTER` / `DIFF` 三态之一）⇒ ⇒ 一行含**多处分叉**时，
> 复合关系在**理由**列**拆分说明**⇒ ⇒ ⇒ **无孤行 / 无漏行**。
>
> **实测覆盖说明**：P-04 / P-05 / P-07 / P-08 / P-09 / P-10 / P-11 / P-12 / **P-22 / P-23**
> 的**行为**断言
> MUST 有实测支撑（上游缺席即 `skip` · 沿用 B5F2 的「缺席即 skip」纪律）；
> P-01 / P-02 / P-03 / P-06 / P-14 / P-15 / P-16 / P-17 / P-18 / P-19 属**结构面**断言
> （源码锚点 + 差分场景的可观察结果）⇒ ⇒ 换版本时 MUST 一并重跑。

### 差分场景组 *(mandatory)*

> **落点**：`tests/differential/parity_probe.py` ⇒ CI 的 Linux 全量档真跑
> （上游缺席即 `skip`）。**编号从 `D-103` 起**（`D-01…D-102` 已被既有 feature 占用
> · B12F1 `D-01…D-15` / B7F4 `D-16…D-28` / B11F1 `D-29…D-37` / B13F1 `D-38…D-49` /
> B7F2 `D-50…D-91` / B7F3 `D-92…D-102`）。
> ⚠️ **复用夹具**：MUST 复用 **B5F2 的差分体系**（`tests/differential/`）·
> MUST **NOT** 填值 B5F2 夹具的 `conditional_edges` 字段（其 freegraph 侧驱动器是
> **线性替身** · 无调度能力 · 填值**无消费者**）⇒ ⇒ ⇒ 条件边的路由判定差分落
> **同一差分体系**内的 `tests/differential/parity_probe.py`（**双真实实现**对跑）
> ⇒ ⇒ ⇒ MUST **NOT** 重造夹具接口 ⇒ ⇒ ⇒ MUST **NOT** 使 B5F2 已产出的差分证据作废
> （H-2 ① · 裁定 15）。

| # | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 | `note`（**判词非 `SAME` 时 MUST 非空**） |
|---|---|---|---|---|
| D-103 | **list 形态** `path_map`（`["a", END]`）· 路由返回 `"a"` | 两侧的**执行节点序列**逐字相等（`('r','a')`）· 最终状态**逐字相等** | SAME | —— |
| D-104 | **dict 形态** `path_map`（`{"hit": "a", "miss": "b"}`）· 路由返回 `"hit"` | 两侧的**执行节点序列**逐字相等（`('r','a')` · `b` **未**执行）· 最终状态**逐字相等** | SAME | —— |
| D-105 | **fresh 读**：源节点写 `{"messages": ["fresh"], "llm_calls": 7}` 后路由 | 两侧路由函数收到的**状态逐字相等**（`messages == ['fresh']` · `llm_calls == 7`）⇒ ⇒ ⇒ **否定式断言**（断言**看到了**新值） | SAME | —— |
| D-106 | 路由返回 `END`（`path_map` = **`{END: END}`** · 即 `END` 映射到 `END`） | 两侧都**终止**（`END` 之后的目标节点**执行 0 次**）· 最终状态**逐字相等** | SAME | —— |
| D-107 | 路由返回**非法值**（不在 `path_map` 内） | 两侧都**抛异常**且**异常类型相同**（`KeyError` · **逐字同款**）⇒ ⇒ ⇒ freegraph 的**消息更详细**（含可选目标）⇒ 消息**不**逐字比对 | SAME（类型相同） | —— |
| D-108 | 路由返回**序列**（`["b", "c"]`） | 两侧的**执行节点序列**逐字相等（两个目标**同轮**执行）· 两个目标收到的**入参逐字相等** | SAME | —— |
| D-109 | **无** `path_map` 的**动态目标**（返回已注册节点名） | 两侧的**执行节点序列**逐字相等 · 最终状态**逐字相等** | SAME | —— |
| D-110 | 路由返回 `END` 而 `path_map` **不含** `END` 键 | 上游抛 `KeyError`（**失败**）；freegraph **终止**（**成功**）⇒ ⇒ ⇒ 失败与否**不等** | **DIFF**（X-2） | **X-2** · 上游**不**在 `_branch.py` 里过滤 `END` ⇒ 终止条件 = **解析后目的地** == `'__end__'` ⇒ 上游查表失败（`KeyError`）· freegraph 取「**单独返回** `END` ⇒ **无条件终止**」（上游 docstring 口径 · 原则 XI ② 类 · **非更严**） |
| D-111 | **无** `path_map` 且返回**未注册**节点名 | 上游**静默忽略**（**成功**结束 · 图停在那里）；freegraph 抛 `ValueError`（**失败**）⇒ ⇒ ⇒ 失败与否**不等** | **STRICTER**（X-3） | **X-3** · 原则 XI ② 类（上游**静默忽略** · 只打一条 warning）+ 与 B7F3 的 **X-2** 同类 ⇒ 「拼错的节点名无声地少跑一条分支」会让图「看起来成功」却结果不对 ⇒ ⇒ ⇒ **更确定** ⇒ **STRICTER** |
| D-112 | 路由函数**抛异常** | 两侧都抛**原异常**（类型与消息**逐字一致**） | SAME | —— |
| D-113 | **无** `path_map` 且路由返回 `None` / `START` | 两侧都抛**内置 `ValueError`**（类型**逐字相同**）⇒ ⇒ ⇒ freegraph 的**消息更详细**⇒ 消息**不**逐字比对 | SAME（类型相同） | —— |
| D-114 | **双参**形态的路由函数（`f(state, config)`） | 两侧的**调用形态**均成功（**无异常**）⇒ ⇒ ⇒ freegraph 的第二参 = 用户交给 `invoke` 的**原始 `config`**（与上游的 `RunnableConfig` dict **形态不同**）⇒ ⇒ ⇒ 比对**形态**而非**内容** | **DIFF**（X-5） | **X-5** · **载体形态**差异（上游传 `RunnableConfig` dict · freegraph 传用户交给 `invoke` 的**原始 `config`** · `RunConfig` / mapping / `None`）⇒ ⇒ ⇒ **调用形态与判别规则逐字相同** ⇒ ⇒ ⇒ **非更严**（上游更宽）⇒ 差分只锁「形态」不锁「内容」 |
| D-115 | **双参**形态的**判别规则**（第二参名字**不叫** `config`） | 两侧都抛 **`TypeError`**（**类型相同**）⇒ ⇒ ⇒ freegraph MUST **NOT** 凭位置个数补传第二参 | SAME | —— |
| D-116 | **条件边挂在 `__start__` 上** | 两侧的**执行节点序列**逐字相等（路由目标**同轮**执行）· 最终状态**逐字相等** | SAME | —— |
| D-117 | **纯条件边入口**（**无**静态入口点） | 两侧都从**路由结果**起步 · 执行节点序列**逐字相等** | SAME | —— |
| D-118 | 路由返回 `END` 而 `path_map` 把 `END` 映射到**别的节点**（`{END: "b"}`） | 上游**解析后目的地 == "b"** ⇒ **路由到 b · 不终止**（实测）；freegraph **无条件终止**（**单独返回** `END`）⇒ ⇒ ⇒ 终止与否**不等** | **DIFF**（X-2） | **X-2** · 与 **D-110** 同一分叉的**另一半**（`END` 是 `path_map` 的 **key** **不等于**终止）⇒ ⇒ ⇒ 上游**解析后目的地**为 `"b"` ⇒ **不终止** · freegraph **无条件终止** ⇒ ⇒ ⇒ **非更严**（上游更宽）⇒ **X-2** 的另一半由本条锁住 |
| D-119 | 路由返回 `Send("ghost", payload)`（**未注册**节点） | 上游**静默忽略**（**成功**结束 · 只打一条 warning · 实测 E-22）⇒ ⇒ ⇒ freegraph **显式失败**（内置 `ValueError` · B11F1 的 V-19）⇒ ⇒ ⇒ 失败与否**不等** | **STRICTER**（X-6） | **X-6** · 原则 XI ② 类（上游**静默忽略**）+ 与 B7F3 的 **X-2** 同类 ⇒ 「拼错的 `Send` 目标无声地少跑一条分支」⇒ ⇒ ⇒ freegraph **零新增错误类型**（只用内置 `ValueError`）· **MUST NOT** 改 B11F1 的冻结面（V-19）⇒ **STRICTER** |
| D-120 | 路由返回 `Send(END, payload)` | 上游抛 **`InvalidUpdateError`**（实测 E-21）⇒ ⇒ ⇒ freegraph 抛**内置 `ValueError`**（B11F1 的 V-21）⇒ ⇒ ⇒ **异常类型不同型** ⇒ ⇒ ⇒ 消息**不**逐字比对 | **DIFF**（X-7） | **X-7** · **异常类型家族**不同（上游 `InvalidUpdateError` ⇒ freegraph 内置 `ValueError`）⇒ ⇒ ⇒ freegraph **零新增错误类型**（只用内置异常）⇒ ⇒ ⇒ **非更严**（上游更宽）· **MUST NOT** 改 B11F1 的冻结面（V-21）⇒ 差分只锁「**异常类型**」不锁「消息」 |

⇒ **共 18 条**（D-103…D-120）⇒ ⇒ 判词分布 = **SAME 12**（D-103 / D-104 / D-105 / D-106 /
D-107 / D-108 / D-109 / **D-112 / D-113 / D-115 / D-116 / D-117**）·
**DIFF 4**（D-110 / D-114 / **D-118 / D-120**）· **STRICTER 2**（D-111 / **D-119**）
⇒ ⇒ ⚠️ **判词非 `SAME` 的 6 条 MUST 带非空 `note`**（**STRICTER 2** + **DIFF 4**）⇒ ⇒ ⇒
宪法原则 XI「失败信号更严须标注」+ 既有守卫 `tests/differential/test_parity_probe.py:106-108`
（`if scenario.verdict in {"STRICTER", "DIFF"}: assert scenario.note`）⇒ ⇒ ⇒
⚠️ **本口径只收紧不放宽**（判词分布 **零变动** · 差分编号 **零变动**）
⇒ ⇒ ⚠️ **D-107 / D-113 的断言口径**：比对「**异常类型**」而非「异常消息」
⇒ ⇒ ⇒ 因为 freegraph 的消息**刻意更详细**（**X-1**）⇒ ⇒ ⇒ 若逐字比对消息
⇒ ⇒ ⇒ 那两条**必红** ⇒ ⇒ ⇒ 故判词为 **SAME（类型相同）** ⇒ ⇒ ⇒ 而「消息更详细」
⇒ ⇒ ⇒ 这条**由单测**（FR-021 的消息内容断言）判定。
⇒ ⇒ ⚠️ **D-119 / D-120 的断言口径**：D-119 比对「**失败与否**」（上游成功 / freegraph 失败）⇒
⇒ ⇒ D-120 比对「**异常类型**」（上游 `InvalidUpdateError` / freegraph `ValueError` ⇒ **不同型**
⇒ ⇒ ⇒ ⇒ 故判词 **DIFF** · **不是** SAME）⇒ ⇒ ⇒ 两者的**消息**均**不**逐字比对。

### 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **STRICTER**（更严的失败信号） | **非法路由返回值的失败信号**：① **有** `path_map` ⇒ 上游抛**裸 `KeyError`**（消息只有 key 本身 · `langgraph/graph/_branch.py:203` · 实测 E-6 / E-7 / M-C / M-E）⇒ freegraph 抛**同型**的 `KeyError`；② **无** `path_map` ⇒ 上游抛 `ValueError("Branch did not return a valid destination")`（实测 M-B / M-D）⇒ freegraph 抛**同型**的 `ValueError` ⇒ ⇒ ⇒ 两态的**消息均 MUST 指明返回值与可选目标** | 原则 XI「失败信号 MAY 比上游更严」+ 原则 XI ② 类（上游自身的**不确定**：消息不含「可以返回什么」）⇒ ⇒ 「路由拼错」在 freegraph 里**一次就说清**⇒ ⇒ ⇒ **类型逐字同款**（照抄纪律 ①）+ **消息更严** ⇒ ⇒ ⇒ **零新增错误类型** ⇒ ⇒ ⇒ ⇒ 差分 **D-107 / D-113** 锁住（比对**类型**） ⇒ ⇒ ⇒ ⇒ ⚠️ **2026-11-17 clarify 轮 · 用户拍板（Q2 = 选项 B）** | 本 feature 内闭合 · 追认文字落 `harness/verification/B8F1/manual-verification.md` |
| **X-2** | **DIFF**（终止条件差异 · 非更严 · **更宽松**） | **返回 `END` 的终止条件**：上游**不**在 `_branch.py` 里过滤 `END` ⇒ 终止的充要条件是「**解析后的目的地**恰为 `'__end__'`」⇒ ⇒ 「`END` 是 `path_map` 的 key」**不**等于终止（实测 `path_map = {END: "b"}` ⇒ 路由到 `b` · **不终止**）⇒ ⇒ 上游抛 `KeyError: '__end__'` 的场景是「`path_map` **不含** `END` 键」（查表失败）⇒ ⇒ 「无 `path_map` + 返回 `END`」⇒ 上游**正常终止**⇒ freegraph 对「**单独返回** `END`」**无条件**终止（序列内的 `END` ⇒ **剔除** · 不终止）| 上游**自己的 docstring**（`langgraph/graph/state.py:999`）写「If it returns `'END'`, the graph will stop execution.」⇒ ⇒ ⇒ **代码与 docstring 相互矛盾** ⇒ ⇒ ⇒ 上游**不**在 `_branch.py` 里过滤 `END` ⇒ 终止的充要条件是「**解析后的目的地**恰为 `'__end__'`」⇒ ⇒ 「`END` 是 key」**不等于**终止（实测 `path_map = {END: "b"}` ⇒ 路由到 `b`）⇒ ⇒ ⇒ 属原则 XI ② 类（**上游自身的不确定**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ freegraph 取**docstring 口径** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **更确定** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 如实登记、**不掩盖** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 差分 **D-110 / D-118**（`D-110` = `path_map` 不含 `END` 键 ⇒ 上游 `KeyError`；`D-118` = `path_map` 把 `END` 映射到别的节点 ⇒ 上游**不终止**） ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **2026-11-17 clarify 轮 · 用户拍板（Q1 = 选项 A）** | 本 feature 内闭合 · 追认文字落同上手工验证记录 |
| **X-3** | **STRICTER**（更严的失败信号） | **无 `path_map` 时的非法目标**：上游**静默忽略**（只打一条 warning · 实测 E-8 · `langgraph/graph/_branch.py:205-206` 把返回值直接当节点名）⇒ freegraph **显式失败**（内置 `ValueError`） | 原则 XI ② 类（上游的**静默忽略**）+ 与 B7F3 的 **X-2**（未知 key ⇒ 显式失败）**同类**⇒ ⇒ 「拼错的节点名无声地少跑一条分支」会让图「看起来成功」却结果不对 ⇒ ⇒ ⇒ 差分 **D-111** 锁住 | 本 feature 内闭合 · 追认文字落同上手工验证记录 |
| **X-4** | **DIFF**（结构差异 · 非更严） | **路由通道的写入**：上游**写** `branch:to:<target>` 并以该通道写入**触发**目标（`langgraph/graph/state.py:1583-1592`）⇒ freegraph **不写**该通道（只作声明载体）· 触发由**动态边**投递 | freegraph 的触发源恒为**边**（B7F1 契约 §3.0「上游对齐 P1-0」⇒ 上游的 `branch:to:` 通道触发 ≡ freegraph 的边触发 · **同款语义**）⇒ ⇒ ⇒ 而路由通道是 `EphemeralValue`（**单值语义**）⇒ ⇒ ⇒ 同轮**两个源**路由到**同一目标**时写两次 ⇒ ⇒ ⇒ ⇒ ⇒ **触发 V-6**（`InvalidChannelUpdateError`）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **不写**是 freegraph 触发模型下的**唯一**正确选择（裁定 8）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **不构成**行为面分叉（目标集合与执行序列**逐字相同**） | 本 feature 内闭合 · 追认文字落同上手工验证记录 |
| **X-5** | **DIFF**（载体形态差异 · 非更严） | **双参形态的第二参内容**：上游传 `RunnableConfig`（dict）⇒ freegraph 传用户交给 `invoke` 的**原始 `config`**（`RunConfig` / mapping / `None`）· **逐字传入** · 上游要求 `config` 参数的注解匹配 `RunnableConfig`（不匹配 ⇒ 跳过注入 + `UserWarning`）⇒ freegraph 的对应集合是 `RunConfig \| Mapping \| None` ⇒ ⇒ ⇒ 上游的匹配集 = `KWARGS_CONFIG_KEYS` 的 `"config"` 项（类对象 / 字符串 / `Optional` / PEP-604 / 空）⇒ freegraph 的匹配集**同形**、仅载体类型不同 ⇒ ⇒ ⇒ ⚠️ **附带诊断信号**：上游在注解不匹配时**发** `UserWarning`（`langgraph/_internal/_runnable.py:352-359`）⇒ freegraph **不发**（零新增可观察输出） | freegraph 的运行期配置载体**形态**与上游不同 ⇒ 但调用**形态**（1 参 / 2 参）**逐字相同** ⇒ ⇒ ⇒ 已登记但**非更严** ⇒ ⇒ ⇒ 差分 **D-114** 锁住（**形态**）⇒ ⇒ ⇒ ⚠️ **附带诊断信号**（`UserWarning`）的差异**同属**本条（**非更严** · 失败信号 `TypeError` **逐字同款** · freegraph 只是**更安静**）⇒ ⇒ ⇒ ⚠️ 差分的**三投影**（输出状态 / 事件序列 / 节点入参）**不含** Python 警告 ⇒ ⇒ ⇒ **MUST NOT** 用差分场景锁它 ⇒ ⇒ ⇒ 由**单元测试**锁定（tasks **T074**） | 本 feature 内闭合 · 追认文字落 `harness/verification/B8F1/manual-verification.md` |
| **X-6** | **STRICTER**（更严的失败信号） | **路由函数返回 `Send` → 未注册节点**：上游**静默忽略**（只打一条 warning · `langgraph/graph/_branch.py:205-206` 把返回值直接当节点名 · 实测 **E-22**）⇒ ⇒ ⇒ freegraph **显式失败**（内置 `ValueError` · B11F1 的 **V-19** · `src/freegraph/runtime/_fanout.py:56-82`） | 原则 XI ② 类（上游自身的**静默忽略**）+ 与 B7F3 的 **X-2**（未知 key ⇒ 显式失败）**同类** ⇒ ⇒ 「拼错的 `Send` 目标无声地少跑一条分支」会让图「看起来成功」却结果不对 ⇒ ⇒ ⇒ ⇒ ⇒ **零新增错误类型**（只用**内置** `ValueError`）⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 改 B11F1 的冻结面（V-19）⇒ ⇒ ⇒ ⇒ ⇒ 差分 **D-119** 锁住（比对「失败与否」）⇒ ⇒ ⇒ ⚠️ **2026-11-17 clarify 轮 · 用户拍板（Q4 = 选项 A）** | 本 feature 内闭合 · 追认文字落 `harness/verification/B8F1/manual-verification.md` |
| **X-7** | **DIFF**（失败信号的**异常类型**差异 · 非更严） | **路由函数返回 `Send` → `END`**：上游抛 **`InvalidUpdateError`**（`langgraph/graph/_branch.py:209-210` · 实测 **E-21**）⇒ ⇒ ⇒ freegraph 抛**内置 `ValueError`**（B11F1 的 **V-21** · `validate_send`）⇒ ⇒ ⇒ **异常类型不同型** | freegraph **零新增错误类型**（只用**内置**异常 · 原则 IX「零新增错误类型」）⇒ ⇒ ⇒ 与上游的**异常类型家族**不同 ⇒ ⇒ ⇒ ⇒ ⇒ **非更严**（上游更宽）⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 改 B11F1 的冻结面（V-21）⇒ ⇒ ⇒ ⇒ ⇒ 差分 **D-120** 锁住（比对「异常类型」）⇒ ⇒ ⇒ ⚠️ **2026-11-17 clarify 轮 · 用户拍板（Q4 = 选项 A）** | 本 feature 内闭合 · 追认文字落 `harness/verification/B8F1/manual-verification.md` |

> ⚠️ **三态标注一致性**（宪法 v1.12.0 原则 XI 末条）：上表的 **STRICTER / DIFF** 标注与
> §Upstream Parity 表的**对应行逐字一致**；每条偏离都有对照表的对应行
> （**X-1↔P-07** · **X-2↔P-08** · **X-3↔P-09** · **X-4↔P-14** · **X-5↔P-19** ·
> **X-6↔P-22** · **X-7↔P-23**）⇒ ⇒ **判据零放宽**。
> ⚠️ **对照表的 `DIFF` 行不全都有偏离登记条目**（**P-17** = passthrough
> —— 均**非**「更严」）⇒ ⇒ ⇒ ⇒ **无孤行 / 无漏行**指的是「偏离登记的每一条都有对照表的
> 对应行」这一方向。

### 破冻结面的回溯修订清单 *(若有)*

> ⚠️ **追认额度**：宪法 v1.12.0「跨 feature 承接的接线通则」+「质量门禁的分阶段落地与
> 发起者追认」⇒ **每 feature ≤ 1 次**追认 ⇒ ⇒ ⇒ 下表的**全部**破面 **同属一次**登记 +
> 回溯修订 + 发起者追认 ⇒ ⇒ ⇒ **MUST NOT** 再破任何其它冻结面。

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| **T-1 · B7F1 的校验规则 V-8**（`GraphSpec.conditional_edges` 非空 ⇒ 内置 `ValueError` · `src/freegraph/runtime/superstep.py:484-487`） | ① `src/freegraph/runtime/superstep.py:484-487`（移除该守卫 ⇒ 构造期**不再**因该字段非空而失败）② `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §2.1 的「条件边」行 + §2.1.1 的 **V-8** 行 ③ `specs/b7f1-superstep-loop/spec.md` 的 **FR-033** / **B7F1 的**裁定 25 行 ④ `specs/b7f1-superstep-loop/data-model.md` 的 V-8 行 | **拆分而不删**（原「恒空即失败」行**保留**并标注「**自 B8F1 起放宽**：允许非空 · 由路由求值消费」）⇒ ⇒ ⇒ 既有断言（**其它** V-1…V-3 逐字不动）⇒ ⇒ ⇒ ⚠️ **②③④ 三处的文档回溯修订 MUST 由 `tasks.md` 的 **T069** 落地**（宪法 v1.9.0 ① 的「契约 + spec」两面）⇒ ⇒ ⇒ **T-5**（C8 挂载点）另由 **T054** 落地 | **并入下面那次**（**唯一一次**追认 · 第 ① 项） |
| **T-2 · B5F2 的校验规则 V-4**（差分夹具的 `conditional_edges` 恒空 ⇒ 显式失败 · `tests/differential/spec_builder.py:122-126`） | — （**本轮取消** · **不破** · 裁定 15） | **不动**：B5F2 的 **V-4** 维持「该字段恒空 ⇒ 非空即失败」⇒ ⇒ ⇒ B5F2 已产出的**线性链路**差分证据**逐字不变** | 不适用（本轮取消） |
| **冻结断言 ①**（`tests/runtime/test_superstep_basic.py:557-576` · `test_a_non_empty_conditional_edges_field_fails_explicitly`） | 同一文件（**拆分**：原「非空 ⇒ 显式失败」改为「**非空 ⇒ 接受**」+ 保留「构造期**其它**失败路径逐条唯一」的断言） | **拆分而不删** | **并入下面那次**（第 ③ 项） |
| **冻结断言 ②**（`tests/runtime/test_superstep_contract.py:77` 的不变式映射 **I-14** + `:609-617` 的用例体） | 同一文件（**拆分**：**I-14** 的语义由「恒空即失败」改为「**填值即被路由求值消费**」⇒ 断言改为「填值 ⇒ 构造**成功**且该值**原样**承载」） | **拆分而不删**（**I-14** 的**编号与槽位不变** ⇒ 不变式**范围**不变 ⇒ 契约守卫的解析范围**零改动**） | **并入下面那次**（第 ④ 项） |
| **冻结断言 ③**（`tests/differential/test_differential.py:123-132` · `test_non_empty_conditional_edges_are_an_explicit_failure`） | — （**本轮澄清轮** · **不破** · 裁定 15） | **不动**（原断言**逐字不动**） | 不适用（本轮取消） |
| **冻结断言 ④**（`tests/facade/test_compiled_graph.py:263-265` · `test_graphspec_conditional_edges_is_always_empty`） | 同一文件（**替换为反面断言**：`GraphSpec.conditional_edges` **非空**且与 `compiled._conditional_edges` **逐字相等**）⇒ ⇒ 保留「产物持有条件边」的**语义** | **拆分而不删** | **并入下面那次**（第 ⑥ 项） |
| **T-3 · B7F2 的编译产物持有面**（3 私有 + 8 公开 = 11 键 · `tests/facade/test_compiled_graph.py:111-114` 断言 `vars()` 恰为 11 键） | — （**不破**：路由求值 MUST 复用既有的 `_conditional_edges` 与 `_spec` ⇒ **不新增**私有字段） | **不动** ⇒ ⇒ `vars(compiled)` 的键数 MUST 仍 == **11** | 不适用（未破面） |
| **T-4 · `harness/demo/target.py` 的只读基准 diff 断言** | — （**不破**：MUST NOT 改动该脚本 ⇒ ⇒ ⇒ **不**在脚本里加断言） | **不动** | 不适用（未破面） |
| **T-5 · C8 的挂载点**（`tests/contracts/test_contract_regressions.py:36` · `# GATE-MOUNT: C8 · status=not-landed · owner=B8F1`） | ① 同一文件（`:36` 翻为 `status=landed`）② 同一文件（**新增** C8 的**元测试**：路径扫描「C8 独立回归测试在位且被 pytest 收集」· 形态参照 `C4_REGRESSION_RELPATH` 的既有写法） | **拆分而不删**（`C4_REGRESSION_RELPATH` 的既有行**逐字不动**）⇒ ⇒ ⇒ **零** `freegraph.*` import（门禁 **G2** 扫描 `tests/contracts/**`）⇒ ⇒ ⇒ ⚠️ **原第 ③ 处（`specs/b3f1-scaffold-ci-gates/` 的门禁契约行）已撤除** —— 经复核：该契约的挂载点 `status` 已是「`not-landed` / `landed` **两态**口径」（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md:372-374` · B5F2 轮修订）⇒ ⇒ ⇒ C8 翻为 `landed` **不违反**该契约 ⇒ ⇒ ⇒ **本次无需改动**（⇒ ⇒ ⇒ **破面全集仍为 7 类** · 仅回溯修订位置减一处） | **并入下面那次**（第 ⑦ 项） |
| **T-6 · `harness/demo/graph_core.py` 的 A5 组软断言**（`soft(...)` + `_B8F1_NOTE = "条件边路由求值未交付 —— 归 B8F1"`） | 同一文件（`case_conditional_edges()` 的 A5 组：全部 `soft(...)` ⇒ **硬断言**（`eq(...)` / 断言形态）⇒ ⇒ ⇒ 删除 `_B8F1_NOTE` 的「未交付」措辞） | **替换为反面断言**（条件边已交付 ⇒ **不**判失败）⇒ ⇒ ⇒ **拆分而不删**（保留「C8 fresh 读」「C7 list 形态」「C7 dict 形态」三条断言的**语义**）⇒ ⇒ ⇒ ⇒ ⚠️ **判据只可更严**（`soft` → 硬 ⇒ **更严** · **不**放宽） | **并入下面那次**（第 ⑧ 项） |
| **T-7 · `harness/demo/agent_loop.py` 的 B1 / B2 组软断言**（`soft(...)` + `_B8F1_NOTE = "条件边路由求值未交付 —— 归 B8F1"` · `harness/demo/agent_loop.py:214-262`） | 同一文件（**B1「工具循环」**与 **B2「tool_calls 形状」**两组的全部 `soft(...)` ⇒ **硬断言**（`eq(...)` / 断言形态）⇒ ⇒ ⇒ 删除 `_B8F1_NOTE` 的「未交付」措辞） | **替换为反面断言**（工具循环已可跑 ⇒ **不**判失败）⇒ ⇒ ⇒ **拆分而不删**（保留「模型被调用 2 次」「`llm_calls == 2`」「`messages` 长度 == 4」「最终答案是 '7'」「`tool_calls` 结构」五条断言的**语义**）⇒ ⇒ ⇒ ⇒ ⚠️ **判据只可更严**（`soft` → 硬 ⇒ **更严** · **不**放宽）⇒ ⇒ ⇒ ⇒ ⚠️ **时序**：MUST 在**条件边路由求值就位**之后落地（否则 CI 必红 · 宪法 v1.11.0） | **并入下面那次**（第 ⑨ 项） |

> ⚠️ **「冻结断言清单 MUST 实测化」**（宪法 v1.12.0）：实施**开始前** MUST 先跑一遍既有测试套件
> 并**记录绿基线**（计数）⇒ ⇒ 再按本 feature 的落地形态改动源码 ⇒ ⇒ **变红**的断言即入本清单
> ⇒ ⇒ ⇒ MUST 逐条带 **`文件:行号`** + **变红原因** ⇒ ⇒ ⇒ MUST **NOT** 只凭推理登记
> ⇒ ⇒ ⇒ **落点**：plan 阶段的「绿基线记录 + 变红清单」。
> ⚠️ **追认的唯一一次**（**唯一事实源 = Assumptions 的「破面全集 7 类」**）：本表
> T-1（B7F1 的 **V-8**）/ 冻结断言 ① / 冻结断言 ② / 冻结断言 ④ / T-5（C8 挂载点）/
> T-6（`graph_core.py` 的 A5 组软断言）/ **T-7**（`agent_loop.py` 的 B1 / B2 组软断言）
> 共 **7 项** ⇒ ⇒ ⇒ **全部**落在**同一次**登记 +
> 回溯修订 + 发起者追认里（追认次数 == **1**）⇒ ⇒ ⇒ **MUST NOT** 再破任何其它冻结面。
> ⚠️ **「追认次数 ≤ 1 次」**（宪法 v1.8.0 / v1.6.0）是**次数**的额度 ⇒ ⇒ ⇒ **7 类破面**
> （**一次**登记 + **一次**追认）**不违反**该额度 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ 额度**用尽后**
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 再破任何其它冻结面（**不**得追加第二次追认）。

---

## Requirements *(mandatory)*

### Functional Requirements

#### A · 路由求值语义（时机与执行落点）

- **FR-001**：条件边的路由函数 MUST 在**源节点执行完毕**（任务**成功落回**）后被求值
  ⇒ ⇒ MUST NOT 在源节点执行**前**、或在**节点入参构造**时被求值。
- **FR-002**：路由求值 MUST 落在 **L2 的 super-step 循环内部**
  （`run_super_step` / `run_super_steps`）⇒ ⇒ MUST **NOT** 另开一条「条件边专用」的
  调度路径 ⇒ ⇒ ⇒ 路由**触发的目标节点**的写入 MUST 进入**同一份**完整状态
  （B7F3 的 **D-2**）⇒ ⇒ ⇒ ⚠️ **路由本身不产生状态写入**（路由通道**不被写入** · 裁定 8）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 「稀疏视图 + 补齐」口径对**路由通道同样适用**（路由通道**不进**返回键集）。
- **FR-003**：每个源节点的每次执行 MUST 只求值一次路由函数 ⇒ ⇒ MUST NOT 因多轮重跑
  而对**同一次执行**重复求值 ⇒ ⇒ ⇒ 路由函数 MUST 支持**单参**与**双参**两形态
  （`f(fresh_view)` 与 `f(fresh_view, config)` · 照抄上游 `RunnableCallable` · 实测 **N-B**）
  ⇒ ⇒ ⇒ 双参的**判别依据 MUST 是「第二参的参数名是 `config`」**
  （**不是**位置参数个数 · 上游按**参数名**查 `config`）
  ⇒ ⇒ ⇒ MUST **永远只传一个位置实参**（fresh 视图）⇒ `config` MUST 以**关键字**注入
  （`config=...`）
  ⇒ ⇒ ⇒ 第二参不存在 / 名字**不叫** `config` ⇒ MUST 按**一参**调用
  （上游同款 ⇒ `f(state, cfg)` 抛 `TypeError`）
  ⇒ ⇒ ⇒ 第二参的注解 MUST 落在**匹配集**内：匹配集 = **无注解** ∨ **类对象** `RunConfig`
  / `Mapping[str, Any]` ∨ 对应的**字符串**注解 ∨ `Optional[...]` / `Union[..., None]` 形式
  ∨ 其 **PEP-604** 等价形式（`RunConfig | None`）
  ⇒ ⇒ ⇒ 字符串槽**只**含**每种载体类型两个**字面量（`"RunConfig"` / `"Optional[RunConfig]"`
  · `"Mapping[str, Any]"` / `"Optional[Mapping[str, Any]]"`）⇒ ⇒ ⇒ 上游同款（其字符串槽
  **只**含 `"RunnableConfig"` / `"Optional[RunnableConfig]"`）· ⇒ `"RunConfig | None"` 这样的
  **字符串****不被接受**
  ⇒ ⇒ ⇒ 注解**不在**匹配集内 ⇒ MUST **跳过注入** ⇒ 按**一参**调用 ⇒ `TypeError`
  （上游同款）⇒ ⇒ ⇒ ⚠️ **MUST NOT** 发 `UserWarning`（上游的**附带诊断信号** ·
  `langgraph/_internal/_runnable.py:352-359` ⇒ 归偏离 **X-5** ⇒ ⇒ ⇒ 判据**只收紧**
  （零新增可观察输出）
  ⇒ ⇒ ⇒ 匹配集 MUST 与上游 `KWARGS_CONFIG_KEYS` 的 `"config"` 项**同形**（类对象 /
  字符串 / `Optional` / PEP-604 / 空）
  ⇒ ⇒ ⇒ 仅**载体类型**与上游不同（`RunnableConfig` ⇒ `RunConfig | Mapping[str, Any]`）
  ⇒ 归入偏离 **X-5**
  ⇒ ⇒ ⇒ `**kwargs` 形态 MUST **NOT** 注入（上游同款 ⇒ kwargs 为空）
  ⇒ ⇒ ⇒ 双参形态的第二参 MUST 是用户交给 `invoke` 的**原始 `config`**
  （`RunConfig` / mapping / `None` · **逐字传入** · 用户没传时为 `None`）
  ⇒ ⇒ ⇒ MUST **NOT** 归一化它 ⇒ MUST **NOT** 用 `context` 通道顶替
  （B8F3 的 C21 是**另一套**机制）。
- **FR-004**：路由函数 MUST 在**该源节点的所有条件边**上各被求值一次（同一源节点可登记
  多条条件边 · 不同 `branch`）⇒ ⇒ ⇒ **条件边的目标集合**与「屏障组」是**两套**语义
  ⇒ ⇒ ⇒ MUST **NOT** 把「多源边」当作「条件边」求值（B7F4 的 **D-3**）。
- **FR-005**：路由目标 MUST 通过**既有的「动态边」载体**投递触发
  ⇒ ⇒ MUST **NOT** 增删编译产物的私有字段（B7F2 的持有面「3 私有 + 8 公开」是冻结面）
  ⇒ ⇒ ⇒ MUST **NOT** 另写一套「条件边触发」机制。
- **FR-006**：路由求值 MUST **NOT** 受**屏障组**的「所有源齐备」判定影响
  ⇒ ⇒ ⇒ 条件边目标在源节点**本轮成功落回**后即可被触发。

#### B · fresh 读（C8）

- **FR-007**：路由函数 MUST 通过 **fresh 读**获取状态 ⇒ ⇒ MUST 使用
  `local_read(channels, writes, fresh=True)` ⇒ ⇒ MUST **显式**传 `fresh=True`
  （**缺省是 `False`**）⇒ ⇒ ⇒ MUST **NOT** 依赖缺省
  ⇒ ⇒ ⇒ MUST **NOT** 假设上游的 `managed` 语义（freegraph **不实现**该入参）
  ⇒ ⇒ ⇒ MUST **NOT** 在调度层另写一份 fresh 合并逻辑。
- **FR-008**：fresh 视图 MUST 包含「**当前值 + 本节点本次写入**」（**C8**）
  ⇒ ⇒ MUST **NOT** 包含**同轮其它节点**的写入 ⇒ ⇒ ⇒ MUST 包含 `Command.update` 的写入
  （B9F1 的归源节点口径）。
- **FR-009**：写入 MUST 按通道**自身**的写入规则合并（**归约型 MUST 走归约器**）
  ⇒ ⇒ ⇒ MUST **NOT** 在路由层另写一份归约逻辑 ⇒ ⇒ ⇒ 「归约型通道已被写过的旧值」
  MUST 与本次写入**合并**后出现在 fresh 视图里（实测 **E-16**）。
- **FR-010**：路由函数 MUST **只**看到本节点**本次**写入一次的结果
  ⇒ ⇒ MUST NOT 把同一批写入**重复**合并进视图。
- **FR-011**：**路由型通道**（`EphemeralValue`）MUST 在 fresh 视图里**缺席**
  （上游同款 · B5F2 `read-contract.md` §3.1）⇒ ⇒ ⇒ MUST **NOT** 用「`branch:to:` 名称前缀」
  之类启发式判定路由通道 ⇒ ⇒ ⇒ MUST **NOT** 把路由通道的值**注入**路由函数的入参。
- **FR-012**：fresh 读 MUST **零污染** ⇒ ⇒ 每个通道的「绑定与可用性判定」在读取前后
  MUST **不变**（B5F2 `read-contract.md` §3.3）。
- **FR-013**：路由函数的入参 MUST 是**覆盖整张通道表**的 fresh 视图
  ⇒ ⇒ MUST **NOT** 收窄为「源节点的订阅集」（上游同款 · 实测 **E-10**）
  ⇒ ⇒ ⇒ **无值**的**覆盖型**通道 MUST **缺席**（稀疏口径）。

#### C · 目标解析（`path_map` 双形态 · 序列 · `END`）

- **FR-014**：路由求值 MUST **只**消费 L2 的 `GraphSpec.conditional_edges`
  ⇒ ⇒ MUST **NOT** import `freegraph._stategraph` / `_ConditionalEdgeSpec`
  ⇒ ⇒ ⇒ MUST **NOT** 重新归一化 `path_map` ⇒ ⇒ ⇒ MUST **NOT** 另起路由通道命名
  （沿用 `branch:to:<target>`）。
- **FR-015**：`path_map` 为 **dict** 时：路由函数的返回值 MUST 作为 **key** 查表，
  其对应的 **value** 为目标节点名 ⇒ ⇒ ⇒ 取值不在表内时 MUST 显式失败（**FR-022**）。
- **FR-016**：`path_map` 为 **list** 形态时：L3 MUST 在**构建期**归一化为 `{name: name}`
  ⇒ ⇒ ⇒ 归一化后「返回值即目标节点名」⇒ ⇒ ⇒ 取值不在该集合内时 MUST 显式失败
  ⇒ ⇒ ⇒ ⇒ ⇒ L2 MUST **NOT** 再做一次归一化。
- **FR-017**：`path_map` 为 **`None`**（动态目标）时：路由函数的返回值 MUST **直接**作为
  目标节点名 ⇒ ⇒ ⇒ MUST 校验其为**已注册节点名**或 `END` ⇒ ⇒ ⇒ 否则 MUST 显式失败。
- **FR-018**：路由函数返回**序列**（`list` / `tuple`）时 ⇒ ⇒ MUST 解析为**多个目标**
  ⇒ ⇒ ⇒ 多个目标 MUST 在**同一轮**并行执行 ⇒ ⇒ ⇒ 各目标 MUST 收到**同一份**共享状态
  ⇒ ⇒ ⇒ **无**逐目标载荷 ⇒ ⇒ ⇒ 与 `Send` **语义相异**（裁定 9）⇒ ⇒ ⇒ 目标序列 MUST
  **去重保序**。
- **FR-019**（**「三处判定」口径的单一事实源** · 2026-11-18 · analyse 轮补登记）：
  **裁定 5** / 契约 §4.3 / `data-model.md` 的 **I-8** **只引用**本条 ⇒ ⇒ ⇒ **口径改动 MUST 只在本条发生**
  ⇒ ⇒ ⇒ 其余三处 **MUST NOT** 另立口径）：
  路由函数**单独返回** `END`（值 `'__end__'` · **非**序列）时 MUST
  **终止整张图**的执行 ⇒ ⇒ ⇒ 后续目标节点的执行次数 MUST == **0**
  ⇒ ⇒ ⇒ `END` 的判定 MUST **先于** `path_map` 查表 ⇒ ⇒ ⇒
  **单独返回** `END` ⇒ **无条件终止**（裁定 5 · 偏离 **X-2**）⇒ ⇒ ⇒
  判定分**三处**（**单独返回** `END` ⇒ **无条件终止**）：① 路由返回值**本身**是 `END`
  （**非**序列）⇒ **无条件终止**（判定**先于** `path_map` 查表 ⇒ 即使 `path_map` **不含**
  `END` 键也终止）；② 返回值是**标量**（**非序列**）且经 `path_map` **解析后**的目标是 `END`
  ⇒ 终止；③ 返回值是**序列**时 ⇒ ⇒ ⇒ 序列内的 `END`（**无论以何种形式出现**：元素**恰为**
  `END`，**或**元素经 `path_map` **解析后**为 `END`）⇒ **被剔除**（照抄上游 · 实测 **E-13**
  · 上游 `langgraph/graph/state.py:1592` 的过滤对**标量与序列同款**）⇒ **不触发**终止
  ⇒ 其余目标**照常执行**。
  ⇒ ⇒ ⇒ ⚠️ **② 只适用于「非序列」返回值** ⇒ ⇒ ⇒ 标量经 `path_map` 解析后为 `END`
  ⇒ ⇒ ⇒ **该分支**终止（不触发任何后续节点 · 上游同款）；⇒ ⇒ ⇒ **序列**返回值内的 `END`
  ⇒ ⇒ ⇒ 一律按 **③** 剔除（**不**终止整张图）⇒ ⇒ ⇒ 二者**不互斥**。
  ⇒ ⇒ ⇒ **序列只含 `END`** ⇒ 剔除后**无目标** ⇒ 该源节点**不触发**任何目标
  （与空序列同款）⇒ ⇒ ⇒ 图**自然收敛**（非 `END` 终止路径）。
  ⇒ ⇒ ⇒ **理由**：「无条件终止」的**准确**范围 = 「**单独返回** `END`」
  ⇒ ⇒ ⇒ 序列内的 `END` **照抄上游**（剔除 · 不终止）⇒ ⇒ ⇒
  三者合起来覆盖全部情形 ⇒ ⇒ ⇒ **判词零变动**（**X-2** 仍 **DIFF** ·
  差分 **D-110 / D-118** 仍锁住）。
- **FR-020**：路由函数返回**非 `str` 的可哈希值**时 MUST 作为 `path_map` 的 **key**
  正常查表 ⇒ ⇒ ⇒ MUST **NOT** 先做类型收窄（`list` / `tuple` **除外** ⇒ 按 **FR-024**
  解释为「**多目标**」）。

#### D · 失败信号

- **FR-021**：**有** `path_map` 时，路由返回值**不在 `path_map` 内**时 MUST 抛内置
  **`KeyError`**（**照抄上游**的查表失败类型 · `langgraph/graph/_branch.py:203`
  · 实测 **E-6 / E-7 / M-C / M-E**）⇒ ⇒ ⇒ 异常消息 MUST **指明返回值**与**可选目标**
  ⇒ ⇒ ⇒ ⇒ ⇒ **STRICTER**（偏离 **X-1** · 上游的消息只有 key 本身） ⇒ ⇒ ⇒ ⇒ ⇒ **类型与上游同族**
  ⇒ ⇒ ⇒ ⇒ ⇒ MUST **NOT** 新增异常类型 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **STRICTER**（偏离 **X-1**）。
- **FR-022**：**无** `path_map` 且返回值**不是**已注册节点名 / `END` 时 MUST 抛内置
  **`ValueError`**（**与上游在该形态下的失败信号同型** · 上游对 `None` / `START` 抛
  `ValueError("Branch did not return a valid destination")` · 实测 **M-B / M-D**
  ⇒ ⇒ ⇒ freegraph 对**非法节点名**补上这层失败 ⇒ ⇒ ⇒ 消息 MUST **指明返回值**与
  **已注册节点名** ⇒ ⇒ ⇒ ⇒ ⇒ **STRICTER**（偏离 **X-3** · 上游**静默忽略**）。
- **FR-023**：路由函数**自身**抛出的异常 MUST 以**原始类型与原始消息**传播
  ⇒ ⇒ ⇒ MUST **NOT** 包装（如包成 `RuntimeError`）⇒ ⇒ ⇒ MUST **NOT** 吞掉
  ⇒ ⇒ ⇒ MUST **NOT** 返回部分结果。
- **FR-024**：路由函数返回 **`list` / `tuple`** 时 MUST 被解释为「**多目标**」
  （**照抄上游** · `langgraph/graph/_branch.py:199-200` 的
  `if not isinstance(result, (list, tuple)): result = [result]` ⇒ ⇒ ⇒ **不是**
  「一个不可哈希的 key」· 实测 **M-F** ⇒ ⇒ ⇒ 上游实测的 `KeyError: 'x'` 是**元素**
  `'x'` 查表失败 ⇒ ⇒ ⇒ 只有**元素**不可哈希时才在查表时失败 ⇒ ⇒ ⇒ MUST **NOT**
  把 `list` / `tuple` 当作「单个返回值」处理。
- **FR-025**：路由函数返回 `None` 或 `START`（`'__start__'`）时 MUST 显式失败
  ⇒ ⇒ ⇒ 失败信号 = **查表优先**（**照抄上游**的判定顺序 · `langgraph/graph/_branch.py:199-211`）
  ⇒ ⇒ ⇒ **两态的类型与消息**分别由 **FR-021**（**有** `path_map` ⇒ 内置 **`KeyError`**）
  与 **FR-022**（**无** `path_map` ⇒ 内置 **`ValueError`**）**规定**
  （本条**不**重复其内容 ⇒ 单一事实源）
  ⇒ ⇒ ⇒ ⚠️ **「`START`」**本身**不**是独立的失败条件（**照抄上游**）：若 `path_map` 恰含
  `__start__` **键**（其 **value** 合法 ⇒ 已在**构造期**被 **V-28** 校验）⇒ ⇒ ⇒
  **照上游路由到该 value**（**不**失败）⇒ ⇒ ⇒ 故「`START`」的失败**仅**发生在
  「查表失败」或「目标非法」两种情形 ⇒ ⇒ ⇒ **零新增偏离**（判词零变动）。

#### E · 载体、边界与门禁

- **FR-026**：`GraphSpec.conditional_edges` MUST 承载条件边的 plain mapping
  （外层 key = **源节点名**；内层每项 = `branch` / `path` / `path_map` / `targets` /
  `route_channels` **五键**）⇒ ⇒ ⇒ **V-8 放宽** ⇒ ⇒ ⇒ 该字段**非空** MUST **不再**是
  构造期失败 ⇒ ⇒ ⇒ ⇒ MUST 承接 **H-1**。
- **FR-027**：编译产物 MUST **从** `_conditional_edges` 读取并填入
  `GraphSpec.conditional_edges` ⇒ ⇒ ⇒ MUST **NOT** 增删编译产物的私有字段
  ⇒ ⇒ ⇒ ⇒ ⇒ MUST 承接 **H-3**。
- **FR-028**：路由通道（`branch:to:<target>`）MUST **不被写入**
  ⇒ ⇒ ⇒ 它**只作声明载体** ⇒ ⇒ ⇒ 触发 MUST 由**动态边**投递
  ⇒ ⇒ ⇒ ⇒ ⇒ MUST **NOT** 触发 **V-6**（单值语义通道一轮收到多于一个值）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **裁定 8** · 偏离 **X-4**。
- **FR-029**：路由通道 MUST **不**出现在 `invoke` 的返回键集里
  ⇒ ⇒ ⇒ 路由通道的判定 MUST 沿用 **B7F1 的冻结口径**
  （`isinstance(channel, EphemeralValue)`）⇒ ⇒ ⇒ MUST **NOT** 用名称前缀启发式
  ⇒ ⇒ ⇒ ⇒ ⇒ MUST 承接 **H-5**。
- **FR-030**：路由函数返回 `Send` / `list[Send]` 时 MUST 产生**同款** fan-out 任务
  （同一落点 · 同一入参形态 · 与**节点返回 `Send`** 产生**同款任务** ⇒ ⇒ ⇒ **失败信号与上游的
  类型分叉见偏离登记 X-6（STRICTER）/ X-7（DIFF）** ⇒ ⇒ ⇒ 本条只约束 freegraph **内部**的
  「两条来源 ⇒ 同款任务」⇒ ⇒ ⇒ MUST 复用 **B11F1** 的既有构造器
  ⇒ ⇒ ⇒ ⇒ ⇒ MUST **NOT** 另写条件边专属 fan-out 路径 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **裁定 10**。
- **FR-031**：条件边目标 MUST 与该节点**同轮**的 `Command.goto` 目标取**并集**
  （去重保序）⇒ ⇒ ⇒ 顺序**不可观察**（同轮执行顺序 = **节点名序**）⇒ ⇒ ⇒ ⇒ ⇒
  **裁定 13**。
- **FR-032**：条件边的**路由判定**差分 MUST 落 `tests/differential/parity_probe.py`
  ——「**双真实实现**对跑：上游 `StateGraph.compile().invoke()` vs freegraph
  `run_super_steps`」⇒ ⇒ ⇒ 该文件已有 `add_conditional_edges` 的**既有差分先例**
  ⇒ ⇒ ⇒ MUST 复用**同一差分体系**（同场景双跑 · 同三项投影比对 ·
  同「上游缺席即 skip」纪律）⇒ ⇒ ⇒ MUST **NOT** 重造夹具接口
  ⇒ ⇒ ⇒ MUST **NOT** 使 B5F2 已产出的**线性链路**差分证据作废
  ⇒ ⇒ ⇒ ⚠️ **载体扩展（属「扩展」非「重造」· 裁定 15）**：为承载条件边载荷而
  **扩字段** —— `Scenario` dataclass 新增**条件边字段**（外层 key = 源节点名 · 内层 =
  `branch` / `path` / `path_map` / `targets` / `route_channels` **五键** · 顺序 = 登记顺序）
  + `run_freegraph()` 把该载荷**传入** `GraphSpec.conditional_edges`
  ⇒ ⇒ ⇒ ⇒ ⚠️ **差分侧的载荷派生口径 MUST 与 L3 逐字一致**（2026-11-18 · analyse 轮修复）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ `targets` / `route_channels` 的派生（L3 `_stategraph.py:643-646`）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 在差分侧**另写一份**（⇒ 同一载荷**两处派生** ⇒ 漂移风险）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST** 有一条断言锁住「差分侧载荷 == L3 载荷」
  ⇒ ⇒ ⇒ MUST **NOT** 新建第二套差分夹具 / 第二条差分执行路径
  ⇒ ⇒ ⇒ MUST 承接 **H-2 ①** · **裁定 15**。

  ⚠️ **B5F2 差分夹具的 `conditional_edges` 字段 MUST 保持恒空** —— 其 freegraph 侧
  驱动器是**线性替身**（**无调度能力**）⇒ ⇒ ⇒ **填值无消费者** ⇒ ⇒ ⇒
  故 **`V-4` 无需放宽**（裁定 15）。
- **FR-033**：MUST **NOT** import `langchain` / `langchain-core` / `langgraph*` /
  `langsmith` / 任何第三方包 ⇒ ⇒ ⇒ MUST **NOT** 读任何环境变量 ⇒ ⇒ ⇒ MUST **NOT** 有任何出站。
- **FR-034**：**C8 独立回归测试** MUST 常驻 CI ⇒ ⇒ ⇒ MUST 是**否定式断言**
  （断言路由函数**看到了**本节点刚写入的值 ⇒ ⇒ ⇒ 而不只是「跑通了」）
  ⇒ ⇒ ⇒ 断言本体 MUST 住 `tests/runtime/`（门禁 **G2** 禁止 `tests/contracts/**` import
  `freegraph.*`）⇒ ⇒ ⇒ `tests/contracts/` **只留**路径扫描的**元测试**
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **C8 的挂载点 MUST 由 `not-landed` 翻为 `landed`**
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **H-9** · 破冻结面 **T-5**。
  ⇒ ⇒ ⇒ ⚠️ **判定级覆盖**（宪法原则 VI **v1.11.0 + v1.13.0**）：本 feature 的
  **人工门禁类 SC**（**SC-019** 追认留痕 · **SC-020** 人工验证记录）⇒ ⇒ ⇒ 其判据 MUST 由
  **可自动核验的文档守卫断言**承担（断言该记录**存在** + 含**必需的实测输出** + 正文**非空**
  · 「符合预期」**不算**实测输出）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 「**写记录**」类任务与「**追认**」类任务
  **均不**构成判定覆盖 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST** 安排在记录写就**之后**（⇒ ⇒ ⇒ **MUST NOT**
  造成「永久红的 CI」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **FR-042** · 裁定 **19**。
- **FR-035**：`harness/demo/graph_core.py` 的 A5 组 MUST 由**软断言**升级为**硬断言**
  ⇒ ⇒ ⇒ MUST **NOT** 改动 `harness/demo/target.py`（只读基准的 diff 断言常驻）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **破冻结面 T-6**。
- **FR-036**：本 feature MUST **NOT** 实现 —— ① `stream()`（B8F2）② `Send` fan-out 的
  **调度**（B11F1 · 本 feature **只复用**）③ 节点别名 / `context` 通道（B8F3）
  ④ `get_graph()` / `draw_mermaid_png()`（B22F1 / B23F1）⑤ checkpoint 落盘（B14F1）
  ⑥ `get_state()` / `get_state_history()`（B15F1）/ `update_state()`（B16F1）
  ⑦ async（v2）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **本条只约束「不实现」**⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 其余 5 个 L1 协议
  方法 MUST **继续**抛内置 `NotImplementedError` 且消息**点名归属 feature**。
- **FR-037**：本 feature MUST **NOT** 破坏 B7F2 的编译产物持有面
  ⇒ ⇒ ⇒ `vars(compiled)` 的键数 MUST 仍 == **11**
  ⇒ ⇒ ⇒ ⇒ ⇒ **破冻结面 T-3（不破）**。
- **FR-038**：条件边的源节点为 `__start__`（入口哨兵）时 MUST **求值**该路由函数
  ⇒ ⇒ ⇒ 其求值结果 MUST 成为**入口目标**（照抄上游 · 实测 **N-A**）
  ⇒ ⇒ ⇒ MUST **NOT** 静默跳过该路由函数（freegraph 当前的「空跑」是**缺陷**）
  ⇒ ⇒ ⇒ **求值次数 MUST == 1**（**仅在第 1 轮**的触发判定前求值一次 ⇒ **幂等**
  ⇒ 后续轮次 MUST **NOT** 再求值 · 裁定 17）
  ⇒ ⇒ ⇒ ⚠️ **「已求值」的幂等标记 MUST 钉死** = **`"__start__" in state.dynamic_edges`**
  （**键存在性** · 2026-11-18 · analyse 轮修复 · 与 `data-model.md` M-7 注一致）
  ⇒ ⇒ ⇒ ⇒ **MUST NOT** 用「值非空」当判据（返回 `END` ⇒ 空 tuple ⇒ **同样**表示已求值）
  ⇒ ⇒ ⇒ ⇒ **MUST NOT** 给 `SchedulerState` 新增字段（其「构造签名与名字逐字不变」是
  B7F1 / B9F1 / **B8F1** 的冻结面 · `src/freegraph/runtime/superstep.py:285-287`）
  ⇒ ⇒ ⇒ ⇒ **MUST NOT** 用 `state.step == 0`（`step` 是「执行轮计数（不含空轮）」
  ⇒ 空轮场景下的「第 1 轮」与触发时点**未对齐**）
  ⇒ ⇒ ⇒ 入口目标的校验口径与**普通目标**同款
  ⇒ ⇒ ⇒ ⚠️ **入参口径**：`__start__` 是**哨兵**（**不执行节点**）⇒ **无本次写入**
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 其路由函数看到的 fresh 视图 = **轮次开始前的通道值**
  （fresh 读在此处**退化为「当前值」**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **不是**「当前值 + 本节点本次写入」
- **FR-039**（入口点口径 · 照抄上游）：MUST 允许「**唯一入口 = `__start__` 条件边**」
  ⇒ ⇒ ⇒ （**无**静态入口点）⇒ ⇒ ⇒ 静态入口与 `__start__` 条件边**并存**时
  ⇒ ⇒ ⇒ 两者的目标 MUST **同轮并行**（取**并集**）⇒ ⇒ ⇒ `__start__` 条件边返回 `END`
  ⇒ ⇒ ⇒ 该分支 MUST **终止**（纯条件边入口 ⇒ 图**直接结束**）⇒ ⇒ ⇒ freegraph 的
  ⇒ ⇒ ⇒ `_validate_entrypoint` **已**允许条件入口 ⇒ **零新增** · **零破冻结面**
- **FR-040**（branch 名唯一 · 照抄上游）：同一源节点（含 `__start__`）登记多条条件边时
  ⇒ ⇒ ⇒ branch 名 MUST **唯一** ⇒ ⇒ ⇒ 重名 MUST 抛内置 `ValueError`
  ⇒ ⇒ ⇒ （消息**点名**分支名与源节点）⇒ ⇒ ⇒ freegraph 的 `add_conditional_edges`
  ⇒ ⇒ ⇒ **已实现**该校验 ⇒ **零新增** ⇒ ⇒ ⇒ `__start__` MUST **NOT** 特例化
  ⇒ ⇒ ⇒ （与普通源节点**同款**）
- **FR-041**（**零依赖镜像脚本的硬断言** · **EV-2 承接**）：`harness/demo/agent_loop.py` 的
  **B1「工具循环」**与 **B2「tool_calls 形状」**两组 `soft(...)` MUST 转为**硬断言**
  ⇒ ⇒ ⇒ MUST **NOT** 改动 `harness/demo/target.py`（只读基准的 diff 断言常驻）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **时序**：MUST 在**条件边路由求值就位**之后落地 ⇒ ⇒ ⇒ 否则 CI 必红
  （宪法 v1.11.0「MUST NOT 写永久红的 CI」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **破冻结面 T-7**
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **H-11** · 裁定 **19**。
- **FR-042**（**人工门禁类 SC 的判定级覆盖** · 宪法原则 VI **v1.13.0**）：**SC-019**（追认
  留痕）与 **SC-020**（人工验证记录）⇒ ⇒ ⇒ 其判定 MUST 由**可自动核验的文档守卫断言**承担
  ⇒ ⇒ ⇒ 断言内容 MUST **逐条**覆盖：① `harness/verification/B8F1/manual-verification.md`
  **存在**且正文**非空** ② 含「**fake 模型轮**」与「**真实模型轮**」两轮的**非空实测输出**
  （MUST **NOT** 只写「符合预期」）③ 含「**追认**」文字且**逐条**列出**破面全集 7 类**
  （唯一事实源 = Assumptions 的「破面全集 7 类」：T-1 · 冻结断言 ①②④ · T-5 · T-6 · **T-7**）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST** 安排在记录写就**之后**（⇒ ⇒ ⇒ **MUST NOT** 造成「永久红的 CI」）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 「**写记录**」类任务与「**追认**」类任务**均不**构成判定覆盖
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **H-11** · 裁定 **19** · 破冻结面 **T-5**（同一次追认内落地）。

### Key Entities

- **路由函数（path function）**：用户注册的**普通可调用对象** · 签名
  `f(fresh_view) -> str | Hashable | Sequence[Hashable]`（**双参**形态的第二参**参数名**
  MUST 为 `config`）· 在**源节点任务成功落回**后被调用一次 · 其返回值决定下一步的目标
  （**C7**）。
- **fresh 视图**：路由函数收到的**唯一入参** —— 「**当前值 + 本节点本次写入**」的合并视图
  （**C8**）· 覆盖**整张通道表** · **路由型通道缺席** · **无值**的**覆盖型**通道**缺席**。
- **`path_map`（归一化后）**：路由函数**返回值 → 目标节点名**的映射 · 在 L2 只以
  **dict** 或 **`None`** 两种形态出现 · list 形态已在 L3 归一化为 `{name: name}`。
- **目标节点名序列**：路由返回值解析后的**有序去重**目标集合 · 每项是**已注册节点名**
  或 `END` · 作为**动态边**投递触发。
- **路由通道**：`branch:to:<target>` 形态的 `EphemeralValue` 通道 · **只作声明载体**
  （**不被写入**）· **不进**返回键集 · **不出现**在 fresh 视图里。
- **动态边**：freegraph 的**边触发**载体（源节点名 → 目标节点名）· 条件边的目标与
  `Command.goto` 的目标都以它投递 · 是 freegraph 与上游「`branch:to:` 通道触发」的
  **同款语义**载体。
- **`END`**：终止标记（值 `'__end__'`）· 路由函数**单独返回**它 ⇒ **无条件**终止整张图
  （**C9**）⇒ 序列内的 `END` ⇒ **剔除**（见 **FR-019**）。

### Out of Scope

- `stream()`（B8F2）—— 本 feature 只交付**同步**执行路径上的路由求值。
- `Send` fan-out 的**调度**（B11F1）—— 本 feature **只复用**既有构造器。
- 节点别名 / `context` 通道（B8F3）—— 路由函数入参**不含** `context`；`path_map` 查表用
  **节点名**，**不**解析别名。
- `get_graph()` / `draw_mermaid_png()`（B22F1 / B23F1）—— 图导出里的条件边表达归它们
  （下游承接 **D-4**）。
- checkpoint 落盘与任何 saver 实现（B14F1）—— 本 feature **不**触碰。
- `get_state()` / `get_state_history()`（B15F1）/ `update_state()`（B16F1）。
- async（v2）—— 路由函数**只**支持**同步**调用（**单参 / 双参**两形态 · 均为同步）。
- fake 模型的注入实现（立项书 §9.2 · B25F1）—— 路由函数**可以是**一个读状态的假模型，
  但注入机制**不属**本 feature（下游承接 **D-5**）。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：**C8 独立回归测试**通过率 == **100%** —— 每个用例断言「路由函数**看到了**
  本节点本次写入的值」。⚠️ 「路由函数读到**旧值**」的用例数 == **0**。
  ⚠️ 断言 MUST 是**否定式**（断言**看到了**新值 ⇒ 而非「跑通了」）⇒ ⇒ 这是本 feature 的
  **最高判据**（提示词 A1）。
- **SC-002**：条件边路由在 **B7F3 的 `invoke` 门面**上可观察的比例 == **100%**
  ⇒ ⇒ 路由产生的写入 MUST 进入**同一份**完整状态（**不另开路径**）
  ⇒ ⇒ 路由通道**不进**返回键集。
- **SC-003**：路由返回 `END` ⇒ 后续目标节点**执行次数 == 0** 的用例比例 == **100%**
  ⇒ ⇒ 且 `END` 与其它目标并存时（序列含 `END`）其余目标**照常执行**。
  ⇒ ⇒ ⇒ ⚠️ **单独返回** `END` ⇒ **无条件终止**是 **2026-11-17 clarify 轮 · 用户拍板**的
  口径（Q1 = 选项 A）⇒ ⇒ ⇒ **序列内**的 `END` ⇒ **剔除**（其余目标照常执行 ·
  照抄上游 **E-13**）。
- **SC-004**：**fresh 读**的用例比例 == **100%** —— 路由函数收到的状态 MUST 逐字等于
  「当前值 + 本节点本次写入」的合并结果。⚠️ 断言 MUST 覆盖**三个**维度：
  ① 看到**本节点**的写入 ② **看不到**同轮**其它节点**的写入
  ③ **归约型**通道的值**已合并**（实测 **E-16** 同款）。
- **SC-005**：`path_map` 的 **list** 与 **dict** 两形态各有一例路由结果**正确**
  ⇒ ⇒ 两形态的**执行节点序列** MUST **逐字**等于预期 ⇒ ⇒ 比例 == **100%**。
- **SC-006**：路由返回值**非法** ⇒ 抛出**明确异常**的用例比例 == **100%**
  ⇒ ⇒ **有** `path_map` ⇒ 异常类型 MUST == 内置 `KeyError`（**逐字同款**）；**无** `path_map` ⇒ 内置 `ValueError`
  ⇒ ⇒ 消息 MUST **含返回值**与**可选目标** ⇒ ⇒ 被**静默忽略**的用例数 == **0**。
- **SC-007**：**无** `path_map` 且返回**未注册**节点名 ⇒ 显式失败（内置 `ValueError`）的用例比例 == **100%**
  ⇒ ⇒ ⇒ **静默结束**（上游同款）的用例数 == **0**。
- **SC-008**：路由函数返回**序列** ⇒ **多目标并行 fan-out** 的用例比例 == **100%**
  ⇒ ⇒ 各目标 MUST 收到**同一份**共享状态（**无**逐目标载荷）
  ⇒ ⇒ ⇒ 与 `Send` 的**逐目标载荷**语义 MUST 可区分（两者各有 1 例）。
- **SC-009**：**条件边的目标集合**与「**屏障组**」**不混用**的用例比例 == **100%**
  ⇒ ⇒ 「多源边」MUST **NOT** 被当作「条件边」求值（B7F4 的 **D-3**）。
- **SC-010**：路由函数的入参 MUST **不含** `context` 通道、**不含**路由通道
  ⇒ ⇒ 「路由通道出现在 fresh 视图里」的用例数 == **0**。
- **SC-011**：**同轮两个源**节点路由到**同一目标** ⇒ 正常执行（**不**抛
  `InvalidChannelUpdateError`）的用例比例 == **100%**。⇒ ⇒ 这是「路由通道
  **不被写入**」这条口径的**可判定证据**（若写了 ⇒ 触发 V-6 ⇒ 必红）。
- **SC-012**：路由函数**抛异常** ⇒ 以**原始类型 + 原始消息**到达调用方的比例 == **100%**
  ⇒ ⇒ 被**包装**成别的类型的次数 == **0**。
- **SC-013**：差分场景组 **D-103…D-120** 全绿（上游缺席即 `skip`）⇒ ⇒ 判词分布与
  §差分场景组表的**逐条一致**（**SAME 12 / DIFF 4 / STRICTER 2**）
  ⇒ ⇒ ⇒ ⚠️ **判词非 `SAME` 的 6 条**（**STRICTER 2** + **DIFF 4**）MUST 带**非空** `note`
  ⇒ ⇒ ⇒ （与既有守卫 `tests/differential/test_parity_probe.py:106-108` 逐字对齐 ⇒
  ⇒ ⇒ ⇒ **判据只收紧不放宽** · 判词分布**零变动**）。
- **SC-014**：**C8 的挂载点**由 `not-landed` 翻为 `landed`，且 C8 的**元测试**（路径扫描）
  在位并被 pytest 收集 ⇒ ⇒ ⇒ ⚠️ **零** `freegraph.*` import（门禁 **G2**）。
- **SC-015**：`harness/demo/graph_core.py` 的 A5 组**硬断言**通过率 == **100%**
  ⇒ ⇒ 该脚本 MUST 仍以退出码 **0** 结束（B7F3 的既有判据**不放宽**）
  ⇒ ⇒ ⇒ ⚠️ 该组的**软断言降级条数 == 0**（**整组**转为硬断言）。
- **SC-016**：`vars(compiled)` 的键数仍 == **11**（未新增编译产物私有字段）的比例
  == **100%** ⇒ ⇒ `harness/demo/target.py` **逐字未改**（只读基准的 diff 断言常驻）
  ⇒ ⇒ ⇒ ⚠️ **零新增面**的**完整**判据（判据**只收紧** · 不删任何既有断言）：
  ① `vars(compiled)` 键数 == **11** ② `freegraph.graph.__all__` == **7** 个符号
  ③ `freegraph.runtime.__all__` == **23** 个符号 ④ `freegraph.contracts.__all__` == **21**
  个符号 ⑤ `freegraph.runtime.errors` 的符号集合**不变**（**零新增错误类型**）
  ⑥ **未实现**的 L1 协议方法（**恰 5 个**：`stream()` / `get_graph()` / `get_state()` /
  `get_state_history()` / `update_state()`）仍抛内置 `NotImplementedError`
  且消息**点名归属 feature**（**B7F2 / B7F3 的 FR-026 口径不变** ⇒ **FR-036**）
  ⇒ ⇒ ⇒ ⚠️ **实测口径**（`src/freegraph/_stategraph.py:350-375`）：`draw_mermaid_png()`
  **尚未存在**（属 **B23F1** 的 `Graph` 侧能力）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 计入本项
  ⇒ ⇒ ⇒ **六项**的达成比例**各自** == **100%**（单一事实源 = `tests/runtime/_runtime_export_manifest.py`
  · 数字为 **2026-11-17** 实测快照 · ⑥ 的载体 = **T023** 的零新增面清点）。
- **SC-017**：路由求值全过程**出站连接数 == 0**；**环境变量读取次数 == 0**
  （含 `LANGSMITH_*`）。
- **SC-018**：路由求值全过程 `sys.modules` 中 `langchain` / `langchain_core` /
  `langgraph` / `langsmith` 的**出现次数 == 0**。
- **SC-019**：破冻结面的**唯一一次**发起者追认（本 spec 的**破面全集 7 类**）在
  `harness/verification/B8F1/manual-verification.md` 留痕 ⇒ ⇒ 合入前**追认完成率
  == 100%** ⇒ ⇒ ⇒ ⚠️ 追认次数 MUST == **1**（**不**得追加第二次）
  ⇒ ⇒ ⇒ ⚠️ **判定级覆盖**（宪法原则 VI **v1.11.0 + v1.13.0**）：本条的判定 MUST 由
  **可自动核验的文档守卫断言**承担（**FR-042**）⇒ ⇒ ⇒ 「**写记录**」类任务与「**追认**」类
  任务**均不**构成判定覆盖 ⇒ ⇒ ⇒ 守卫 MUST 在记录与追认**写就之后**才转绿
  ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 造成「永久红的 CI」。
- **SC-020**：**人工验证记录**存在且**正文非空**（宪法原则 VI v1.13.0 的「人工门禁类 SC」
  判定覆盖口径）⇒ ⇒ 该守卫 MUST 在记录写就之后才转绿
  ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 造成「永久红的 CI」⇒ ⇒ ⇒ **MUST NOT** 以「写记录」本身
  冒充判定覆盖 ⇒ ⇒ ⇒ 记录 MUST 覆盖「**fake 模型轮**」与「**真实模型轮**」两轮的
  **实测输出**（**含**条件边路由的**实测输出**）⇒ ⇒ ⇒ ⚠️ **「fake 模型轮」的定义**
  = 猴补（monkey-patch）`init_chat_model` + **含条件边的最小图** / `agent_loop.py` 的
  **工具循环轮** ⇒ ⇒ ⇒ **本 feature 可达** ⇒ ⇒ ⇒ MUST **真跑**并记录
  ⇒ ⇒ ⇒ ⚠️ **「`target.py` 端到端轮」不在本 feature 的达成范围**（PNG 路径属 **B23F1**）
  ⇒ ⇒ ⇒ 具名承接 **B22F1 + B23F1（M2）**· **B25F1（M4）**（见 plan 的**登记项 R-2**）
  ⇒ ⇒ ⇒ ⚠️ **若真实轮因环境不具备而
  无法完成** ⇒ MUST 按宪法 v1.6.0 登记为**环境偏离**并写明（**MUST NOT** 用「未验证」
  替代「已登记的环境偏离」）⇒ ⇒ ⇒ ⚠️ **判据本身不放宽**（fake 轮仍 MUST 跑通）。
- **SC-021**：**双参**形态（第二参**参数名**为 `config`）可用比例 == **100%**
  ⇒ ⇒ ⇒ 第二参 == 用户交给 `invoke` 的**原始 `config`**（**逐字**）
  ⇒ ⇒ ⇒ 第二参名字**不叫** `config` 时按**一参**调用的用例比例 == **100%**（上游同款）。
  ⇒ ⇒ ⇒ 注解在**匹配集**内 ⇒ 注入成功；注解在匹配集外 ⇒ 按**一参**调用的用例比例 == **100%**（上游同款）。
  ⇒ ⇒ ⇒ ⚠️ **覆盖维度 MUST 逐条可判定**（**FR-003** 的全部子义务 ⇒ **六维**）：
  ① **调用形态**（单参 / 双参）② **判别依据** = **第二参的参数名**是 `config`
  （**不是**位置参数个数）③ **注解匹配集**内 ⇒ 注入成功（类对象 / 字符串 / `Optional` /
  PEP-604 / 空）④ **匹配集外** ⇒ **跳过注入** ⇒ 按**一参**调用 ⇒ `TypeError`（上游同款）
  ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 发 `UserWarning`（上游的附带诊断信号 · 归偏离 **X-5**）
  ⑤ **`**kwargs`** 形态 ⇒ **不注入** ⑥ 第二参**逐字** == 用户的原始 `config`
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 归一化该 `config` ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 以 `context` 通道顶替
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **六维**的达成比例**各自** == **100%**（载体 = **T008 + T015**）。
- **SC-022**：条件边挂在 `__start__` 上 ⇒ ⇒ ⇒ 路由函数**确实被求值**的用例比例 == **100%**
  ⇒ ⇒ ⇒ 入口目标**照常执行** ⇒ ⇒ ⇒ ⚠️ **求值次数 == 1**：在**含 ≥ 2 轮**的图上
  （条件边回到上游节点）`__start__` 的路由函数**被调用次数仍 == 1**（**幂等** · 裁定 17）。
- **SC-023**：`__start__` 条件边的**三种情形**（**纯条件边入口** / **静态入口与条件入口并存取并集并行**
  / **返回 `END` 终止该分支**）通过率 == **100%**
- **SC-024**：同一源节点登记**重名** branch 的条件边 ⇒ 抛内置 `ValueError`（消息**点名**分支名
  与源节点）的用例比例 == **100%**（与上游同款）
- **SC-025**：`harness/demo/agent_loop.py` 的 **B1「工具循环」**与 **B2「tool_calls 形状」**两组
  ⇒ **硬断言**通过率 == **100%** ⇒ ⇒ ⇒ 该脚本 MUST 仍以退出码 **0** 结束
  ⇒ ⇒ ⇒ ⚠️ 该两组内的**软断言降级条数 == 0**（**整组**转为硬断言 · 破冻结面 **T-7**）。
- **SC-026**：「**fake 模型轮**」（猴补（monkey-patch）`init_chat_model` + **含条件边的最小图** /
  `agent_loop.py` 的**工具循环轮**）的**实测输出**已落 `harness/verification/B8F1/manual-verification.md`
  且**非空**（MUST **NOT** 只写「符合预期」）⇒ ⇒ ⇒ 该段实测输出 MUST **含条件边路由**的
  **可观察结果**（路由目标 · 目标节点执行次数 · fresh 视图）⇒ ⇒ ⇒ ⚠️ 该项**由文档守卫断言**
  判定（**FR-042**）⇒ ⇒ ⇒ 「写记录」本身**不**构成判定覆盖。

### 追溯表（FR → SC）

| FR | SC |
|---|---|
| FR-001 | SC-001 · SC-002 |
| FR-002 | SC-002 · SC-013 |
| FR-003 | SC-001 · SC-021 |
| FR-004 | SC-009 |
| FR-005 | SC-002 · SC-016 |
| FR-006 | SC-009 |
| FR-007 | SC-004 · SC-010 |
| FR-008 | SC-004 |
| FR-009 | SC-004 |
| FR-010 | SC-004 |
| FR-011 | SC-010 |
| FR-012 | SC-004 |
| FR-013 | SC-004 · SC-010 |
| FR-014 | SC-013 · SC-016 |
| FR-015 | SC-005 · SC-006 |
| FR-016 | SC-005 · SC-006 |
| FR-017 | SC-007 |
| FR-018 | SC-008 |
| FR-019 | SC-003 · SC-013 |
| FR-020 | SC-005 |
| FR-021 | SC-006 · SC-013 · SC-016 |
| FR-022 | SC-007 · SC-013 · SC-016 |
| FR-023 | SC-012 |
| FR-024 | SC-006 · SC-008 |
| FR-025 | SC-006 · SC-007 |
| FR-026 | SC-002 · SC-016 |
| FR-027 | SC-016 |
| FR-028 | SC-011 |
| FR-029 | SC-002 · SC-010 |
| FR-030 | SC-008 · SC-013 |
| FR-031 | SC-002 · SC-008 |
| FR-032 | SC-013 · SC-014 |
| FR-033 | SC-017 · SC-018 |
| FR-034 | SC-001 · SC-014 |
| FR-035 | SC-015 |
| FR-036 | SC-015 · SC-016 |
| FR-037 | SC-016 |
| FR-038 | SC-022 · SC-023 |
| FR-039 | SC-022 · SC-023 |
| FR-040 | SC-024 |
| FR-041 | SC-025 |
| FR-042 | SC-019 · SC-020 · SC-026 |
| （全局） | SC-013 · SC-019 · SC-020 |

---

## Assumptions

- **上游版本钉死**：`langgraph` **1.2.11** + `langchain-core` **1.7.6**
  （取证于 2026-11-17 · 本仓库 `.venv` 的实际安装版本 · `pyproject.toml:100` 钉死）
  ⇒ 换版本时 MUST 重新核实全部锚点并改写版本号（原则 XI「照抄的三条纪律」③）。
- **「上游实测」的取证方式**：本 spec 的 P-04 / P-05 / P-07 / P-08 / P-09 / P-10 / P-11 /
  P-12 的行为断言由**沙箱实测**得出（`langgraph 1.2.11` 的真实 `StateGraph` + `invoke`，
  2026-11-17 于本仓库 `.venv` 内执行）⇒ plan / tasks 阶段 MUST 把这些实测**固化成差分
  探针场景**（D-103…D-120 · **18 条**）⇒ 上游缺席即 `skip`。
- **「上游的 `local_read`」与「freegraph 的 `local_read`」是两件事**：上游的
  `local_read(scratchpad, channels, managed, task, select, fresh=False)` 有**六个**入参
  （含 freegraph **不实现**的 `managed`）⇒ freegraph 的
  `local_read(channels, writes, *, fresh=False)` 是 B5F2 的**自有**形状
  ⇒ **MUST NOT** 把上游的 `managed` / `select` 语义搬进来。
- **「条件边」与「屏障组」是两套语义**：条件边的目标由**路由函数**决定；屏障组的目标由
  **多源边的全部源齐备**决定 ⇒ 二者 MUST NOT 混用（B7F4 的 **D-3**）。
- **freegraph 的「边触发」≡ 上游的「`branch:to:` 通道触发」**：这是 B7F1 契约 §3.0
  「上游对齐 P1-0」的既定口径 ⇒ 本 feature 的「动态边投递」是**同款语义**的 freegraph
  载体 ⇒ **不是**与上游的分叉 ⇒ 只有「**是否写通道**」这一点是结构差异（**X-4**）。
- **路由通道在 freegraph 里从不被写入**：它**只作声明载体**（供 `targets` /
  `route_channels` 口径与未来的图导出用）⇒ 它的「每 super-step 清空」属性
  （B7F1 的裁定 33）**对本 feature 无影响**。
- **破面全集 = 7 类**（**唯一事实源 = 破冻结面的回溯修订清单**）：① **T-1** B7F1 的
  **V-8** ② 冻结断言 **①** ③ 冻结断言 **②** ④ 冻结断言 **④**
  ⑤ **T-5** C8 挂载点 ⑥ **T-6** `graph_core.py` 的 A5 组软断言
  ⑦ **T-7** `agent_loop.py` 的 B1 / B2 组软断言（**EV-2 承接** · H-11 · 裁定 19）
  ⇒ **全部**落在**同一次**登记 + 回溯修订 + 发起者追认里（追认次数 == **1**）
  ⇒ ⇒ ⇒ **MUST NOT** 再破任何其它冻结面。
- **层归属**：路由**求值**落 **L2**（`src/freegraph/runtime/`），
  故 **L2 只依赖 L1**（ARCH-1 / G25 **不破**）；而「把 `_conditional_edges` 填进
  `GraphSpec.conditional_edges`」落 **L3**（`src/freegraph/_stategraph.py`），
  方向是 **L3 → L2**（既有方向，无新增反向依赖）。
- **只读基准脚本**：`harness/demo/target.py` **MUST NOT** 被改动（门禁 3 的 diff 断言）。
  本 feature 的验收证据落在 `harness/demo/graph_core.py`（可改的**前置用例**脚本）
  加 `harness/demo/agent_loop.py`（零依赖镜像）加人工验证记录。
- **人工验证的两轮**：「fake 模型轮」= 猴补（monkey-patch）`init_chat_model` 注入（立项书 §9.2）
  加**含条件边**的最小图（或 `harness/demo/agent_loop.py` 的**工具循环轮**）跑一轮并记录
  **实测输出** ⇒ ⇒ ⇒ ⚠️ **本 feature 可达**（**MUST** 真跑并记录 · 裁定 19 · SC-026）；
  「真实模型轮」= `claude-sonnet-4-6`
  加最小真实模型图跑一轮并记录**实测输出**。真实轮的出网属**用户出站**，不判失败，
  但**框架零出站**断言仍须通过。固定脚本的端到端轮（`target.py` 跑通）**不属**本 feature
  的达成范围（需 **B22F1 + B23F1**），登记为**分阶段落地**（plan 的**登记项 R-2**）。
  ⇒ ⇒ ⇒ ⚠️ **两轮的定义**（B7F3 的同款纪律 · 消歧）：
  「fake 模型轮」= **猴补 `init_chat_model` + 含条件边的最小图 / `agent_loop.py` 的工具循环轮**
  ⇒ **本 feature 可达**；「真实模型轮」= **真实模型 + 最小真实模型图** ⇒ 需厂商端点
  ⇒ **本环境不具备** ⇒ MUST 登记为**环境偏离**（B7F3 的 **EV-2** 的承接方 = **B8F1**·
  **B25F1**）。
- **上位文档待修订清单**（属**发起者**职权，本 feature **不**单方面改立项书）：
  ① 立项书 §5.2 的 **B8F1 前置依赖**行（现写 `B5F2,B7F1`，实际含 **B7F2 / B6F1 /
  B9F1 / B11F1 / B7F4 / B10F1 / B3F1**）；② 立项书 §5.2 的 **B8F1 行数口径**；
  ③ 立项书 §5.2 的 **B8F1 层标注**（实际求值落 **L2**、接线落 **L3**）。
  本 feature 以**仓库现状**为准。
  ⚠️ **单一事实源 = `plan.md` 的登记项 R-5**（2026-11-18 · analyse 轮修复 · 消除重复登记）：
  本条**只**给摘要 ⇒ ⇒ ⇒ **逐条措辞与处置 MUST 以 R-5 为准**（R-5 另含「§4.2 S5 的脚注」
  与「**D-103…D-120** 超出该判据」两项）⇒ ⇒ ⇒ **MUST NOT** 在本处另立口径。
- **C8 的「静默破坏」风险**（提示词 §10）：写错时代码照样跑通，只是循环行为不对。
  这正是 **SC-001 MUST 是「否定式断言」**的原因：断言路由函数**看到了**新值，
  而非「跑通了」。

- **立项书 §5.2 的 B8F1 行「前置」列 = 「B5F2, B7F1」**（里程碑序的**简写**）
  ⇒ ⇒ ⇒ 本 spec 的承接条款 **H-1…H-11** 另含 **B6F1 / B7F2 / B7F3 / B7F4 / B9F1 /
  B11F1 / B3F1 / B10F1** ⇒ ⇒ ⇒ **以本 spec 的承接条款为准** ⇒ ⇒ ⇒ **不**单方面修改
  立项书（属发起者职权）· 登记落 `plan.md` 的**登记项 R-5**
