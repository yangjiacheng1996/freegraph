# Feature Specification: B7F3 · `invoke()`：返回完整状态 + `InvalidUpdateError` ★

**Feature Branch**: `b7f3-invoke-full-state`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "B7F3 · `invoke()`：返回完整状态 + `InvalidUpdateError` ★ —— 交付 freegraph 的**主对外执行入口** `invoke(input, config=None)`：驱动整张图跑完，并**返回完整状态**（不是只返回新增消息）。本 feature 的判定是：`invoke` 返回 `{'messages': [...], 'llm_calls': N}` 这样的**完整状态**。本 feature 是 **MVP 六项最小交付集**的第 3 项；前置依赖 **B7F1 / B12F1**。"

---

## 承接条款（上游 feature → 本 feature）

> 宪法 v1.12.0「跨 feature 承接的接线通则」：上游 feature 指名本 feature 的跨 feature 义务
> MUST 在本 spec 落成 **FR + 裁定**；**只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽判据**。

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B7F1 → B7F3** | **M2** | **调度契约的跨 feature 接口**：① **节点入参口径** —— 入参 MUST 等于 `read_channels(子映射)` 的结果、子映射 MUST 按「**通道映射的顺序**」构造 ⇒ 本 feature **MUST NOT** 改写 key 顺序；② **调度状态口径** —— `run_super_steps(spec, state=None, *, max_steps=…)` 的 `state` **MAY 省略** ⇒ 本 feature **MUST NOT** 依赖「调用方复用同一个调度状态」⇒ **每次 `invoke` 内部自洽**；③ **返回值口径** —— `SuperStepResult.state` 是**稀疏**通道状态 ⇒ 本 feature MUST 取稀疏视图后**补齐**无值 key；④ **步末清空口径** —— 两个入口都执行步末清空 ⇒ 本 feature **MUST NOT** 假设路由型通道的值残留到下一次 `invoke` | `specs/b7f1-superstep-loop/spec.md` FR-001 / FR-008 / FR-014 · 裁定 26 / 27 / 33 · `contracts/superstep-contract.md` §1 / §3.2 / §5.2 / §5.3 | FR-002 · FR-005 · FR-006 · FR-008 · FR-025 · 裁定 3 / 4 / 12 |
| **H-2** | **B12F1 → B7F3** | **M2** | **多会话隔离的「每次调用新建实例」**：多会话隔离**已由 2026-11-12 P2-b 在 L2 落地**（每次运行从规格新建通道实例）⇒ 本 feature 的义务收窄为「**对外暴露**」：**每次 `invoke` MUST 新建一份通道实例** ⇒ 同一张编译图可被**多个会话并发调用**而状态互不干扰 ⇒ 与 **B7F2** 的「编译产物持规格」**共同**落成**门面级**验收；**MUST NOT** 复用「编译期已写入值的通道实例」 | `specs/b12f1-concurrency-errors/spec.md` **FR-024** · 裁定 23（**已作废**）· 下游承接 **D-4** · 回溯修订 **B12F1 的 T-7** | FR-002 · FR-004 · 裁定 10 · SC-008 / SC-009 |
| **H-3** | **B12F1 → B7F3** | **M2** | **并发度旋钮 `max_concurrency` 的「搬进 `RunConfig`」**：L1 的 `RunConfig` **已含** `max_concurrency: int \| None = None`（**同名同义** · `src/freegraph/contracts/types.py:216`）⇒ ⇒ **本 feature MUST NOT** 扩 `RunConfig`、MUST NOT 另造名字或另定语义 ⇒ ⇒ ⚠️ **2026-11-16 clarify 轮 · 用户拍板（Q2 = 选项 B）**：本 feature MUST 让 **L2 的 `run_graph` 也从 `config.max_concurrency` 读取**（**关键字优先** · `config` 兜底）⇒ ⇒ **兼容扩展**（既有调用方零改动 · 既有失败顺序逐字不变）⇒ ⇒ MUST **回溯修订** B10F1 的 `run_graph` 契约 + B12F1 的旋钮口径 ⇒ ⇒ ⇒ **追认额度**：与 L1 的两处放宽**同属一次**追认；缺省 `None` ⇒ 并发度上限 = `min(32, cpu+4)`（**上游同款**）⇒ 显式 `N` ⇒ 实际并发度 = `min(本轮任务数, N)`（**N 不被 32 再夹**）⇒ `N = 1` ⇒ **串行基线**⇒ 非法取值 MUST **入口即**显式失败（类型不符 ⇒ 内置 `TypeError`；`< 1` ⇒ 内置 `ValueError`；两者均**点名该参数**）⇒ ⇒ **该校验已由 L2 落地**（`superstep.py:1339-1361`）⇒ 本 feature MUST **NOT** 在门面层另写一份校验 | `specs/b12f1-concurrency-errors/spec.md` **FR-017** · 裁定 2 / 18 · **V-18** · 回溯修订 **B12F1 的 T-2** | FR-023 · 裁定 13 · SC-006 · 破冻结面 **T-3** |
| **H-4** | **B10F1 → B7F3** | **M2** | **`invoke()` 的接线 + L1 入参放宽 + MVP 验收承接**：① **L1 `CompiledGraph.invoke` 的 `input` 注解 MUST 放宽**为「`StateDict \| Command \| None`」（**上游同款** · `langgraph/pregel/main.py:3836-3838`）⇒ ⇒ ⚠️ **`config` 注解 MUST 一并放宽**为「`RunConfig \| Mapping[str, Any] \| None`」（**与 L2 的 `run_graph` 逐字同款** · 2026-11-16 clarify 轮 · 用户拍板）⇒ ⇒ ⇒ **两处同属一次**登记 + 回溯修订 + 发起者追认（追认额度仍 == **1 次**）⇒ ⇒ **B10F1 刻意不破该 L1 冻结面** ⇒ ⇒ **本 feature MUST** 走「登记 + 回溯修订 + 发起者追认」流程（**不**消耗 B10F1 的追认名额）；② **`invoke` MUST 接受 `Command` 作为输入** ⇒ ⇒ 恢复路径的**判定表**以 B10F1 的 **FR-013 的表**为**唯一事实源**（**逐字照抄**）· **判定顺序**以 **B10F1 的**裁定 4 为准 ⇒ ⇒ **MUST NOT** 在本 feature 的文档 / 实现里另抄一份；③ **挂起时 MUST 返回 `{**state, "__interrupt__": interrupts}`**（**无**挂起时**不**含该键）⇒ ⇒ **转成路径 MUST 只此一条**（`InterruptResult.as_result_dict()`）⇒ ⇒ **MUST NOT** 另写一条转成路径；④ **MUST NOT** 把「未挂 checkpointer 时提交 `Command(resume=...)`」**静默降级** ⇒ ⇒ MUST 抛**明确异常**；⑤ 两条补漏口径（「按 id 的映射恢复」与「未提供恢复值」）MUST 按 **FR-013** 落成；⑥ **MVP 验收基线的人工验证承接**：本 feature 的 `manual-verification.md` MUST 补上「**fake 模型轮 + 真实模型轮**」两轮的**实测输出** ⇒ ⇒ **B10F1 MUST NOT** 把「本 feature 未跑固定脚本」写成「本 feature 未验证」 ⇒ ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮补记**：**固定脚本的端到端轮**（`target.py` 跑通）**不属**本 feature 的达成范围（需 **B8F1 + B22F1 + B23F1**）⇒ ⇒ ⇒ ⇒ ⇒ 登记为 **EV-4**（分阶段落地 · 具名承接）⇒ ⇒ ⇒ ⇒ ⇒ 「两轮」的**定义**见 SC-018 ⇒ ⇒ ⇒ ⇒ ⇒ 且本条 MUST 挂**可自动核验的文档守卫断言**（判据级覆盖 · 宪法原则 VI v1.11.0 + v1.13.0） | `specs/b10f1-interrupt-resume/spec.md` **FR-002 / FR-013** · 裁定 1 / 4 / 10 · **SC-002 / SC-011 / SC-012** · 下游承接 **D-3 / D-8** | FR-014 · FR-015 · FR-019 · 裁定 1 / 7 / 8 · SC-010 / SC-018 · 破冻结面 **T-1** |
| **H-5** | **B13F1 → B7F3** | **M2** | **`recursion_limit` 透传 + 静态挂起结果**：① `invoke(input, config)` MUST 接受普通 dict 形态的 `config` 并把 `"recursion_limit"` **原样**交给 L2；MUST **NOT** 丢弃 / 改名 / 另写解析路径；MUST **NOT** 把 `GraphRecursionError` 包装成别的类型；`harness/demo/graph_core.py` 的硬断言 MUST 在此**棒真跑通过**；② 静态挂起时 MUST 返回 `InterruptResult.as_result_dict()`（含 `"__interrupt__": ()`）⇒ **MUST NOT** 另写一条「静态中断 → 结果键」的转成路径；③ 恢复时 MUST 接受 `input=None`（规范形态）与 `Command(resume=...)`（值**不投递给**任何节点） | `specs/b13f1-static-interrupt-recursion-limit/spec.md` **FR-010 / FR-014 / FR-021 / FR-023** · 裁定 2 / 6 / 12 · 下游承接 **D-3 / D-4** | FR-014 · FR-015 · FR-018 · FR-022 · 裁定 5 / 8 · SC-007 / SC-010 |
| **H-6** | **B6F1 → B7F3** | **M2** | **G22「场景 ②」的最小图运行期断言**：最小图**闭环**（建图 → 编译 → 执行）在本 feature 闭合 ⇒ ⇒ **MUST** 交付并点亮该运行期断言 ⇒ ⇒ **只接线，MUST NOT 新增门禁编号**；红线**不放宽**（FR-018 无豁免）—— ③② 是同一红线的**运行期加强**，非判据放宽 | `specs/b3f1-scaffold-ci-gates/spec.md` 裁定 22 · `harness/proposals/立项书.md` §6.2 | FR-027 · 裁定 15 · SC-014 |
| **H-7** | **B7F2 → B7F3** | **M2** | **`invoke()` 的执行语义**：① `CompiledGraph.invoke(input, config=None)` MUST 驱动 L2 的 `run_graph(spec, input, *, checkpointer=..., config=...)` 并把 `SuperStepResult` / `InterruptResult` 归一成**完整状态字典**；② **MUST NOT** 另写一条「编译 → 执行」的路径；③ **MUST NOT** 复用「编译期已写入值的通道实例」（B7F2 只交付通道**规格**）；④ **MUST NOT** 增删编译产物的**私有字段**（B7F2 的持有面「3 私有 + 8 公开」是冻结面）⇒ ⇒ schema key 集合 MUST 由**既有**字段推导 | `specs/b7f2-compile/spec.md` **FR-012** · 裁定 10 · 下游承接 **D-1** · `contracts/compile-contract.md` §8 | FR-002 · FR-008 · FR-012 · FR-028 · 裁定 4 / 10 · SC-016 |
| **H-8** | **B7F4 → B7F3** | **M2** | **多源汇合边在「完整状态」里可观察**：门面级 `invoke` MUST 让屏障目标在**所有**源之后出现 ⇒ ⇒ **MUST NOT** 为屏障另开一条执行路径（沿用 **B7F1 / B12F1** 的**同一条**）⇒ ⇒ ⚠️ **物理可达**（**静态多源边** · `add_edge([a, b], c)` · **B7F4 已交付于 L2** · **不依赖 B8F1 的条件边路由** ⇒ 实测 `executed == ('a','b','c')`）⇒ ⇒ ⇒ **本 feature MUST 判定**该半边（SC-013 **整条**）⇒ ⇒ ⇒ ⇒ **EV-3 已撤销**（2026-11-16 analyse 轮 · 根因判断有误） | `specs/b7f4-multisource-join/spec.md` 下游承接 **D-2** · 登记项 **PR-4** | FR-003 · FR-010 · SC-013 |
| **H-9** | **B3F1 → B7F3** | **M2** | **只读基准的 diff 断言常驻**：`harness/demo/target.py` 与入库基准**逐字相同**（改动即失败）⇒ 本 feature **MUST NOT** 改它；C4 / C8 回归测试**常驻**（⚠️ **C8 的挂载点仍为 `not-landed`** · 承接方 **B8F1** ⇒ 本 feature **MUST NOT** 改动 `tests/contracts/test_contract_regressions.py` 的 C8 行）；依赖门禁（无 `langsmith` / `langchain*` / `langgraph*`）**常驻** | `specs/b3f1-scaffold-ci-gates/spec.md` FR-011 ① · `harness/reports/Q8-图运行时最小契约.md` §3.4 | ① **FR-028**（`target.py` 只读 + 编译产物持有面不破）② **FR-025**（节点入参 = C4 稀疏读口径 · 承载 C4 的「常驻回归」）+ **EV-1**（C8 仍 `not-landed` · 承接 **B8F1**）③ **FR-024** · SC-011 / SC-012 |
| **H-10** | **B9F1 → B7F3** | **M2** | **`Command` 作为节点返回值**：该路径的内核能力**已由 L2 交付**（`run_graph` 消费节点返回的 `Command`）⇒ 本 feature **只驱动**、**MUST NOT** 另写一条「节点返回 `Command`」的处理路径；`invoke` 的**输入**形态是 `Command`（B10F1 的恢复路径）⇒ **两者 MUST NOT 混为一条** | `specs/b9f1-command-primitive/spec.md` 裁定 7 / 21 | FR-015 · 裁定 7 · FR-026 |

---

## 下游承接条款（本 feature → 下一棒）

> 本 feature 冻结「执行入口 + 完整状态口径」这组跨 feature 接口（**D-1…D-5**）。**只接线 · 逐条最小改动**。

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 |
|---|---|---|---|---|
| **D-1** | **B7F3 → B8F2** | **M2** | **`stream()` 的「完整状态」口径**：`stream` 的 `values` 档 MUST 与本 feature 的 `invoke` **逐字同款**（同一份「稀疏视图 + 补齐无值 key」的归一 ⇒ **单一实现点**）⇒ ⇒ **MUST NOT** 另写一份「补齐」逻辑；`updates` 档（增量）**不受**本口径约束 | FR-008 · FR-009 · 裁定 3 · SC-001 |
| **D-2** | **B7F3 → B8F1** | **M2** | **条件边路由的执行落点**：条件边路由求值 MUST 在本 feature 的**同一条**执行路径上生效（**MUST NOT** 另开路径）⇒ ⇒ 路由产生的写入 MUST 进入**同一份**完整状态 ⇒ ⇒ 本 feature 的「稀疏视图 + 补齐」口径对路由通道**同样**适用（路由通道**不进**返回键集） | FR-003 · FR-012 · 裁定 4 · SC-013 |
| **D-3** | **B7F3 → B22F1 / B23F1** | **M3** | **就绪顺序**：只读基准脚本的调用顺序是「**先** `get_graph(...).draw_mermaid_png()`，**后** `invoke(...)`」⇒ ⇒ **B22F1 / B23F1 MUST 先于本 feature 就绪**，否则脚本在到达验收点前中断 ⇒ ⇒ 本 feature **MUST NOT** 越界实现 `get_graph` / `draw_mermaid_png` | FR-026 · 裁定 16 · SC-015 |
| **D-4** | **B7F3 → B14F1** | **M3** | **checkpointer 的落盘职责**：本 feature **只把**编译产物持有的 `checkpointer` **透传**给 L2（**MUST NOT** 自己落盘 / 自己实现 saver）⇒ ⇒ 落盘与 `MemorySaver` 归 **B14F1** ⇒ ⇒ `invoke` 的**恢复**语义（MUST 挂 checkpointer）在 **B14F1** 落地前**由 L2 的既有失败信号**承担 | FR-002 · FR-019 · FR-026 · 裁定 7 |
| **D-5** | **B7F3 → B8F2 / B15F1 / B16F1** | **M2 / M3** | **L1 其余 4 个带 `config` 参数的方法的「`config` 注解放宽」**：本 feature 只放宽 `CompiledGraph.invoke` 的 `config` 注解（`RunConfig \| Mapping[str, Any] \| None` · 裁定 1）⇒ ⇒ L1 的 `stream` / `get_state` / `get_state_history` / `update_state` **仍**是 `RunConfig \| None` ⇒ ⇒ ⇒ **`config` 双形态与「运行期载体」的语义 MUST 在这 4 个方法上同样成立** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **归** B8F2（`stream`）/ B15F1（`get_state` / `get_state_history`）/ B16F1（`update_state`）**各自**走「**登记 + 回溯修订 + 发起者追认**」（宪法 v1.8.0 / v1.9.0）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **本 feature MUST NOT** 代为放宽这 4 处（**追认额度 ≤ 1 次 / feature** ⇒ 额度已用于裁定 1）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **下游 MUST 复用本 feature 已定的载体边界**（`RunConfig` = 会话面 + `max_concurrency`；普通映射 = 运行期参数 ⇒ **原样**交给 L2 ⇒ **MUST NOT** 在门面层翻译成 `RunConfig`）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ | FR-021 · FR-022 · 裁定 1 · 裁定 5 · 契约 CF-05 |

> **状态更新（2026-11-22）**：B15F1 已交付`get_state` / `get_state_history` 的
> `config` 注解放宽（`RunConfig | Mapping[str, Any] | None`；返回类别不变）；B8F2 已交付
> `stream` 的同类放宽；`update_state` 待 B16F1。
>
> ⚠️ **回溯修订（B16F1 · 2026-11-23 · 拆分而不删）**：B16F1 的裁定 1 已冻结
> `CompiledGraph.update_state` 的 `config` 注解放宽为 `RunConfig | Mapping[str, Any] | None`
> **且返回类别改为 `RunConfig`**；自 B16F1 实现起生效，**参数名 / 顺序不变**。
> 下游复用本 feature 的载体边界（`RunConfig` = 会话面 + `max_concurrency`；普通映射 = 运行期参数
> ⇒ 原样交给 L2）。新口径见 `specs/b16f1-update-state-time-travel/spec.md` 裁定 1 / R-1。

---

## Clarifications

### Session 2026-11-16（设计裁定 · spec 阶段写死，plan 不得再翻）

> **背景**：提示词初稿已写死「签名 `invoke(input, config=None)` · 返回**完整状态**（全部 schema key）·
> `config` 双形态 · `Command` 输入 · `InvalidUpdateError`」，但**五处**仍会外溢到用户代码或下游
> feature 的接口决策：
> ① 「完整状态」的**键集**到底等于什么（上游会**省略**从未写入的 key）；
> ② **无值 key**填什么值；
> ③ schema key 集合从**哪里**推导（编译产物的持有面是**冻结**的）；
> ④ `config` 与运行期旋钮的**载体与透传**边界；
> ⑤ **挂起 / 恢复**的**唯一**转成路径与**唯一**判定表。
> 本节逐条拍板。

- **Q1（`invoke` 的签名与 L1 入参放宽）**：L1 的 `CompiledGraph.invoke` 的 `input` 注解 MUST
  放宽为「`StateDict \| Command \| None`」（**上游同款** · `langgraph/pregel/main.py:3836-3838`）？
  → **A：是**。这**破 L1 冻结面** ⇒ MUST 走「**登记 + 回溯修订 + 发起者追认**」三条
  （宪法 v1.12.0「跨 feature 承接的接线通则」的破冻结面条款）⇒ ⇒ **本 feature 的追认额度
  （每 feature ≤ 1 次）即用在此处** ⇒ ⇒ ⇒ **MUST NOT** 再破 B7F2 的编译产物持有面
  （这直接排除了「给 `CompiledGraph` 加第 4 个私有字段」这条路，见 Q3）。
  ⇒ 落点：FR-001 · FR-015 · 裁定 1 · 破冻结面 **T-1** · SC-015。
- **Q2（「完整状态」的键集 = 什么）**：上游 `invoke` 返回的是「**有值**的 output channel」
  （`langgraph/pregel/_io.py:38-53` 的 `read_channels` 在 `skip_empty=True` 时
  `except EmptyChannelError: pass` ⇒ **省略**无值 channel）⇒ ⇒ **实测**：
  `invoke({"messages": []})` 返回键集 = `['messages']`（**`llm_calls` 被省略**）⇒
  ⇒ 提示词 §2 说的「实测键集 == `['llm_calls','messages']`」**是「输入给了全部 key」的情形**，
  **不是**「上游会补齐无值 key」。
  ⚠️ **2026-11-16 analyse 轮 · 实测订正**：该键集的**顺序**也写错了 ⇒ ⇒ **上游按「schema 声明顺序」返回**
  （实测 `langgraph 1.2.11`：schema 里 `messages` 在前 ⇒ 键集 `['messages','llm_calls']`；把 schema 顺序
  **反转**才得 `['llm_calls','messages']`）⇒ ⇒ ⇒ ⇒ 本 feature 的「**schema 声明顺序**」与上游**逐字同款**
  （**键序 = SAME** · 原则 XI 照抄）⇒ ⇒ ⇒ ⇒ 落点：差分 **D-93** · 契约 `upstream-parity.md` §3。
  → **A：freegraph 返回**全部 schema key**（含从未写入者）**⇒ ⇒ **比上游更严**
  （原则 XI ②「上游自身的不确定」+ 原则 III 第 7 项 + C11）⇒ ⇒ **必须登记为偏离**
  ⇒ ⇒ ⇒ 且 MUST 以**差分场景**锁住（判词 `STRICTER`）。
  ⇒ 落点：FR-008 · 裁定 3 · 偏离登记 **X-1** · 差分 **D-94** · SC-001。
- **Q3（无值 key 填什么值）**：类型无关的唯一可选项是 `None`？上游有没有「通道默认值」概念？
  → **A：`None`**。理由：① freegraph 的通道**没有**初值概念（B5F1 的 `LastValue` /
  `BinaryOperatorAggregate` 均无默认值 ⇒ 无从取「默认值」）；② 上游的 `MISSING` 是**内部哨兵**
  ⇒ MUST NOT 泄漏到门面；③ `None` 让「**键一定在**」成为可依赖的事实 ⇒ 用户 `out[k]` 不必写
  `.get(k, default)`；④ ⚠️ **本口径只影响 `invoke` 的**返回值**，MUST NOT 影响**节点入参**
  （C4 的稀疏入参 MUST 原样保留 ⇒ `state.get(k, default)` 仍返回 `default`）。
  ⇒ 落点：FR-009 · FR-025 · 裁定 3 · SC-001 / SC-013。
  ⚠️ **2026-11-16 clarify 轮补记（用户拍板 · 见 §Clarifications 的 Session 2026-11-16 ·
  clarify 轮）**：① 上游的 `BinaryOperatorAggregate` **确实**有「类型空值」
  （`langgraph/channels/binop.py:82-92` 的 `self.value = typ()`）⇒ 但它**只作内部初始值**、
  **从不**出现在返回字典里 ⇒ ⇒ **上游没有「往返回字典里补值」这个概念** ⇒ ⇒ 「填什么」属
  **必须自研区 ②**（可问）；② **填充值 = `None`**（维持 Q3 的结论）⇒ ③ ⚠️ **新增的约束**：
  补齐后返回字典**不可原样回喂**（上游因省略而天生安全；freegraph 补 `None` ⇒ 回喂会把
  `None` **真的写进**通道 ⇒ 节点里 `state.get("llm_calls", 0) + 1` 会 `TypeError`）⇒ ⇒ ⇒
  **返回值 MUST 被当作「只读快照」** ⇒ **MUST NOT** 原样回喂给下一次 `invoke` ⇒ ⇒ ⇒ 该禁令
  MUST 在**用户可见文档**里写明（并写明理由）⇒ ⇒ ⇒ 落点：FR-009 · 裁定 3 · Edge Cases ·
  SC-020 · 偏离登记 **X-1** 的「理由」列。
- **Q4（schema key 集合从哪推导）**：B7F2 的编译产物持有面是**冻结**的（「3 私有字段 + 8 公开属性」
  · `tests/facade/test_compiled_graph.py:111-114` 断言 `vars()` 恰为 11 键）⇒ ⇒ **MUST NOT**
  增删私有字段 ⇒ ⇒ schema key 集合 MUST 由**既有**字段推导。两个候选：
  **A** = 图规格通道表**扣除路由型通道**；**B** = 节点订阅集（`NodeSpec.subscribes`）。
  → **A**。理由：① **B 是间接口径**（节点订阅集是「触发判定 + 入参内容」的集合 · B7F1 FR-008
  ③，**不**承诺等于 schema 全集）⇒ 用它推导返回值键集是**偶然耦合**；② **A 是直接语义**
  （schema 通道 = 全部通道 − 路由通道）⇒ 路由通道的判定 MUST 沿用 **B7F1 的冻结口径**
  （`isinstance(channel, EphemeralValue)` · B7F1 FR-014 末条）⇒ ⇒ **MUST NOT** 用
  「`branch:to:` 前缀」之类**名称启发式**；③ 通道表的 key 顺序 = **schema 声明顺序 + 路由通道**
  （`tests/facade/test_compiled_graph.py:298-306` 已断言）⇒ ⇒ 扣除后**自然**得到 schema 声明顺序。
  ⇒ 落点：FR-012 · 裁定 4 · SC-001 / SC-016。
- **Q5（`config` 与运行期旋钮的载体与透传边界）**：两种 `config` 形态**各自**承载什么？
  → **A**：**`RunConfig` 实例** 承载 `max_concurrency`（+ `thread_id` / `context` / `metadata` /
  `tags` 等**会话面**参数）；**普通 dict** 承载 `recursion_limit` 等**运行期**参数
  （`harness/demo/graph_core.py:461` 的 `{"recursion_limit": 3}` 是**硬断言**）⇒ ⇒ 两者
  **MUST 原样**交给 L2（`run_graph(..., config=...)`）⇒ **MUST NOT** 丢弃 / 改名 / 另写解析路径
  ⇒ ⇒ ⇒ **MUST NOT** 在门面层把 dict **翻译**成 `RunConfig`（那会**改写**「dict 是运行期载体」
  这一已锁定形态 · B13F1 D-3）⇒ ⇒ ⇒ `RunConfig` **已含** `max_concurrency` 与 `recursion_limit`
  （`types.py:216-217`）⇒ ⇒ **本 feature 无需扩 `RunConfig`**（**L1 冻结面零改动**）。
  ⇒ 落点：FR-021 · FR-022 · FR-023 · 裁定 5 / 13 · SC-006 / SC-007。
- **Q6（`Command` 输入的判定表放哪）**：恢复路径的判定表 MUST 在本 feature 另抄一份吗？
  → **A：不抄**。**唯一事实源 = B10F1 的 FR-013 的表**（映射）· **判定顺序 = B10F1 的裁定 4**
  （先后）⇒ ⇒ 本 feature 只**引用**（「按 FR-013 的表 · 依 **B10F1 的**裁定 4 的顺序」）⇒ ⇒
  ⚠️ 且 **MUST NOT** 把「节点返回 `Command`」（B9F1 的路径）与「`Command` 作为图输入」
  （B10F1 的恢复路径）**混为一条**。
  ⇒ 落点：FR-015 · 裁定 7 · SC-010。
- **Q7（挂起结果的转成路径）**：挂起时 `invoke` 返回什么？转成逻辑写在哪？
  → **A**：MUST 走 **B10F1 的唯一转成路径**（`InterruptResult.as_result_dict()` ⇒
  `{**state, "__interrupt__": interrupts}`）⇒ ⇒ **MUST NOT** 在门面层另写一条
  「异常 → `__interrupt__` 键」的转成路径 ⇒ ⇒ **静态挂起同样走这一条**（值 = **空元组** `()` ·
  B13F1 D-4）⇒ ⇒ **无挂起时 MUST NOT 含**该键 ⇒ ⇒ ⇒ `__interrupt__` 的值是 **tuple**
  （上游是 **list** ⇒ 已由 **B10F1** 登记为形态差异 ⇒ 本 feature **只透传 · 不新增登记**）。
  ⇒ 落点：FR-014 · 裁定 8 · SC-010。
- **Q8（错误传播的对象）**：节点抛出的异常 MUST 原样传播还是包装？
  → **A：原样传播**（**原始类型 + 原始消息**）⇒ ⇒ `InvalidUpdateError` /
  `GraphRecursionError` / `InterruptError` / 用户自己的异常类型**一律**原样 ⇒ ⇒
  **MUST NOT** 包装成 `RuntimeError` ⇒ ⇒ **MUST NOT** 吞掉 ⇒ ⇒ ⚠️ **中断不是「出错」**：
  **B10F1 已落地** ⇒ `run_graph` 已把合并抛出的 `GraphInterrupt` 转成 `InterruptResult`
  ⇒ ⇒ 故 `invoke` **不**存在「照常抛 `GraphInterrupt`」这条分支（提示词初稿 §4 FR-006 的
  「在 B10F1 接手之前」那一支**已过期** ⇒ 见引文差异 ③）⇒ ⇒ 若 `run_graph` 仍以任何方式
  抛出 `GraphInterrupt`，`invoke` MUST **原样抛出**（MUST NOT 吞掉）。
  ⇒ 落点：FR-017 · FR-018 · FR-019 · 裁定 9 · SC-005 / SC-010。
- **Q9（每次 `invoke` 的通道实例）**：`invoke` MUST 复用编译产物的通道实例吗？
  → **A：不复用**。每次调用 MUST 由 L2 从**规格**新建通道实例（B12F1 的 P2-b ·
  `superstep.py:575-591` 的 `_run_channels`）⇒ ⇒ ⇒ 同一张编译图**连续两次** ⇒ 不累积；
  **并发两次** ⇒ 不串扰 ⇒ ⇒ ⇒ 且 MUST **不**依赖「调用方复用同一个调度状态」（裁定 27）
  ⇒ ⇒ ⇒ 每次 `invoke` **内部自洽**。
  ⇒ 落点：FR-002 · FR-004 · FR-005 · 裁定 10 · SC-008 / SC-009。
- **Q10（最小图运行期断言的归属）**：G22「场景 ②」的运行期断言由本 feature 交付吗？
  → **A：是**。建图 → 编译 → 执行在**本 feature**闭合 ⇒ ⇒ **只接线 · MUST NOT 新增门禁编号**
  ⇒ ⇒ ⇒ 边界：红线**不放宽**（③② 是同一红线的**运行期加强**）。
  ⇒ 落点：FR-027 · 裁定 15 · SC-014。

### 裁定编号映射（本 spec 的唯一裁定编号表）

> ⚠️ **裁定来源的两类（2026-11-16 analyse 轮 · 第三轮 · FND-C4）**：**裁定 1–10** 来自本节的
> **Q1–Q10 设计裁定**（clarify 轮的用户裁定并入对应条目 ⇒ 其中**裁定 5** 兼采 **H-5** 的口径）
> ⇒ ⇒ **裁定 11–16** 来自**承接条款的落成口径**：**H-1**（裁定 11 / 12）· **H-3**（裁定 13）·
> **H-9**（裁定 14）· **H-6**（裁定 15）· **下游承接 D-3**（裁定 16）⇒ ⇒ ⇒ ⇒ ⇒ **二者共同构成本表**
> ⇒ ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · M5 订正**：初版注把 **H-5** 列进「裁定 11–16」的来源
> ⇒ ⇒ ⇒ ⇒ **不准确**（**H-5** 落在**裁定 5** 的来源里；**裁定 16** 的来源是**下游承接 D-3**）
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 「16 条」的**计数**口径不变 = **10（设计）+ 6（承接落成）** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **计数口径与来源口径正交** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 计数不变 · 来源已订正
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **「16 条」的口径** = **10（设计）+ 6（承接落成）** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **不是 18 条**。

| 裁定 | 内容 | 来源 |
|---|---|---|
| **裁定 1** | `invoke(input, config=None)`；L1 协议的 `input` 注解放宽为 `StateDict \| Command \| None`（**破 L1 冻结面** ⇒ 走登记 + 回溯修订 + 追认三条；**本 feature 的追认额度用在此处**）⇒ ⚠️ **2026-11-16 clarify 轮（用户拍板）**：L1 协议的 **`config` 注解一并放宽**为 `RunConfig \| Mapping[str, Any] \| None`（**与 L2 的 `run_graph` 逐字同款**）⇒ ⇒ 两处放宽放在**同一次**登记 + 回溯修订 + 追认里（追认额度仍 == **1 次**） | Q1 · H-4 · clarify 轮（2026-11-16） |
| **裁定 2** | 返回值 MUST 是**普通 `dict`**；键集 = **schema 全部 key**（按 schema 声明顺序）+ 条件性的 `"__interrupt__"`；MUST NOT 出现 schema 之外的 key（路由通道等内部通道 MUST NOT 泄漏） | Q2 · H-1 / H-4 |
| **裁定 3** | 「完整状态」的构造 = 以 `SuperStepResult.state`（**稀疏**）为准按 schema key 顺序取值 + **从未写入者填 `None`**（⚠️ **仅覆盖型（无归约器）通道**适用 —— 归约型通道未写时其稀疏视图里**已有**「类型空值」（`[]` / `0`）⇒ ⇒ ⇒ **MUST NOT** 改写成 `None` · 契约 R-06 · data-model §2.3）⇒ 键集 == schema key 集（100%）⇒ **STRICTER** 偏离（上游省略）⇒ **X-1** ⇐ ⚠️ **返回值是「只读快照」**：MUST **NOT** 原样回喂给下一次 `invoke`（回喂会把 `None` 真的写进通道 ⇒ 节点里 `state.get(k, 0) + 1` 会报错）⇒ 该禁令 MUST 写进用户可见文档 | Q2 / Q3 · H-1 · clarify 轮（2026-11-16） |
| **裁定 4** | schema key 集合 MUST 由**图规格通道表扣除路由型通道**得出；路由通道判定 MUST 沿用 B7F1 冻结口径（`isinstance(channel, EphemeralValue)`）⇒ MUST NOT 用名称前缀启发式 ⇒ MUST NOT 依赖节点订阅集 ⇒ MUST NOT 新增编译产物私有字段 | Q4 · H-1 / H-7 |
| **裁定 5** | `config` 双形态的载体边界：`RunConfig` = 会话面 + `max_concurrency`；普通 dict = 运行期（`recursion_limit`）⇒ MUST 原样交给 L2 ⇒ MUST NOT 在门面层把 dict 翻译成 `RunConfig` | Q5 · H-5 |
| **裁定 6** | `input` 的初始状态写入 MUST 走 **L2 的既有输入写入路径**（带归约器 ⇒ 归约；无归约器 ⇒ 覆盖）⇒ MUST NOT 另写一条写入路径 | H-1 · H-7 |
| **裁定 7** | `Command` 作为**图输入**的判定 MUST 逐字按 **B10F1 FR-013 的表**、依 **B10F1 的**裁定 4 的顺序 ⇒ MUST NOT 另抄一份；「节点返回 `Command`」（B9F1）与「`Command` 作为输入」（B10F1）MUST NOT 混为一条 | Q6 · H-4 / H-10 |
| **裁定 8** | 挂起结果 MUST 走 **B10F1 的唯一转成路径** `InterruptResult.as_result_dict()`；静态挂起同款（`"__interrupt__": ()`）⇒ MUST NOT 另写一条转成路径；无挂起时 MUST NOT 含该键 | Q7 · H-4 / H-5 |
| **裁定 9** | 错误传播：原始类型 + 原始消息；MUST NOT 包装 / 吞掉；`GraphInterrupt` 若仍从 L2 抛出则原样抛出 | Q8 · H-4 / H-5 |
| **裁定 10** | 每次 `invoke` MUST 新建通道实例 ⇒ 连续两次不累积、并发两次不串扰 ⇒ MUST NOT 依赖调用方复用调度状态 | Q9 · H-2 / H-7 |
| **裁定 11** | 步末清空口径 ⇒ MUST NOT 假设路由型通道的值残留到下一次 `invoke`（**B7F1 的**裁定 33） | H-1 |
| **裁定 12** | 节点入参口径 MUST 原样 ⇒ MUST NOT 改写 key 顺序（入参 == `read_channels(子映射)`，子映射按通道映射顺序构造） | H-1 |
| **裁定 13** | 并发度旋钮：`RunConfig.max_concurrency` **已存在** ⇒ MUST NOT 扩 `RunConfig`、MUST NOT 另造名字或语义、非法取值的**入口即**失败由 **L2** 既有校验承担 ⇒ ⇒ ⚠️ **2026-11-16 clarify 轮 · 用户拍板（Q2 = 选项 B）**：旋钮的**读取点落在 L2** —— `run_graph` MUST 在**关键字缺省时**回落到 `config.max_concurrency`（**关键字优先**）⇒ ⇒ ⚠️ **`None` ≡ 未指定**（2026-11-16 analyse 轮 · **D-B 决策**）：关键字为 `None`（**未传**或**显式 `None`**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 一律回落 `config.max_concurrency` ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **不存在**「显式 `None` 覆盖 config」的第三种语义⇒ ⇒ **兼容扩展**（既有调用方零改动 · 既有失败顺序逐字不变：关键字的校验仍在 `resolve_config` **之前**）⇒ ⇒ ⇒ MUST **回溯修订** B10F1 / B12F1 的契约行 | Q5 · H-3 · clarify 轮（2026-11-16） |
| **裁定 14** | 零出站 / 零环境变量 / 零第三方依赖（`langchain*` / `langgraph*` / `langsmith`） | H-9 |
| **裁定 15** | G22「场景 ②」的最小图**运行期**断言在本 feature 交付并点亮 ⇒ 只接线、MUST NOT 新增门禁编号 | Q10 · H-6 |
| **裁定 16** | 就绪顺序：`get_graph` / `draw_mermaid_png`（B22F1 / B23F1）MUST 先于 `invoke` 就绪 ⇒ 本 feature MUST NOT 越界实现二者 | 下游承接 D-3 |

### Session 2026-11-16 · clarify 轮（用户拍板）

> **纪律**（宪法 v1.12.0 原则 XI + clarify 的收窄纪律）：**上游有答案 ⇒ 照抄 ⇒ 不问用户**。
> 本轮只问了「**上游没答案**」的点（上游**没有**「往返回字典里补值」这个概念 ⇒ 落
> **必须自研区 ②**）。

- **Q（未写入过的 schema key 在返回字典里怎么处理）**：`invoke` 返回的完整状态里，
  状态 schema 中那些「从头到尾没被写入过」的 key，该怎么处理？
  → **A：选项 A —— 保留这个 key，值填 `None`；并在文档里写明「返回的是只读快照，
  不要原样回喂给下一次 `invoke`」**（**用户 2026-11-16 拍板**）。
  ⇒ **上游依据**（clarify 前已自查）：上游是**省略**（`langgraph/pregel/_io.py:38-53` 的
  `read_channels` 在 `skip_empty=True` 时 `except EmptyChannelError: pass`）⇒ **实测 E-1**：
  `invoke({"messages": []})` ⇒ 键集 `['messages']`；⇒ **实测 E-5**：上游的返回值**可安全
  回喂**（省略 ⇒ 回喂不注入 `None`）⇒ ⇒ 上游**没有**「补什么值」的答案 ⇒ 故本点可问。
  ⇒ **代价与消化**：freegraph 补 `None` ⇒ 回喂会把 `None` **真的写进**通道 ⇒ 节点里
  `state.get("llm_calls", 0) + 1` 会 `TypeError` ⇒ ⇒ **以文档禁令消化**（FR-009 ·
  Edge Cases · SC-020）⇒ ⇒ ⇒ ⚠️ **只约束返回值**：用户**显式传入** `None` 作为初始值
  **仍 MUST 被写进通道**（写入语义不变 · 与上游同款）。
  ⇒ 落点：FR-009 · 裁定 3 · 引文差异 4 · Edge Cases · 偏离登记 **X-1** · SC-003 / SC-020。
- **Q（L1 协议里 `invoke` 的 `config` 参数注解要不要一并改准）**：L1 协议现在写的是
  `config: RunConfig | None`（**只收 `RunConfig`**），但实际必须也能收普通 dict
  （如 `{"recursion_limit": 3}`）⇒ 注解写不准，下游（B8F2 的 `stream`、B15F1 的
  `get_state`）就会照错的口径写 ⇒ 要不要在本次一并放宽？
  → **A：选项 A —— 一并放宽成 `RunConfig | Mapping[str, Any] | None`**（**与 L2 的
  `run_graph` 逐字同款** · `superstep.py:1924`）⇒ ⇒ 且与 `input` 的放宽放在**同一次**
  登记 + 回溯修订 + 发起者追认里（追认额度 **≤ 1 次/feature**，但**一次**登记可覆盖
  **两处**放宽）⇒ ⇒ ⇒ **用户 2026-11-16 拍板**。
  ⇒ **上游自查**：上游 `invoke(config: RunnableConfig | None)`（`langgraph/pregel/main.py:3839`）
  里的 `RunnableConfig` **本身就是 dict** ⇒ 上游的注解天然「含 dict」；freegraph 的
  `RunConfig` 是 dataclass（**不是** dict）⇒ 要写准就得**显式放宽注解** ⇒ 上游回答了
  「能收 dict」，「freegraph 的注解写成什么样」上游**没答案** ⇒ 故本点可问。
  ⇒ 落点：FR-001 · FR-021 · 裁定 1 · 破冻结面 **T-1**（含 `config` 行）· 引文差异 10 ·
  SC-019。

### 引文差异（提示词初稿 vs 本 spec）

| # | 差异 | 处置 |
|---|---|---|
| **引文差异 1** | 提示词 §2 写「`RunConfig` 仍为 4 个字段」（并据此推导「本 feature 若扩 `RunConfig` ⇒ 是本 feature 自己的契约变更」） | **事实订正**：`RunConfig` **现为 9 个字段**（`src/freegraph/contracts/types.py:169-219`）且**已含** `max_concurrency`（`:216`）与 `recursion_limit`（`:217`）⇒ ⇒ **本 feature 无需扩 `RunConfig`** ⇒ ⇒ ⇒ **L1 冻结面零改动**（除 `invoke` 的 `input` **与** `config` 两处注解放宽）⇒ ⇒ ⇒ 追认额度**全部**留给裁定 1 ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮补记**：**立项书 §5.3.1 C22** 仍写「`RunConfig` **字段清单不变**（`thread_id` / `context` / `metadata` / `tags`）」⇒ ⇒ 那是 **2026-11-05** 的口径 ⇒ 仓库已于 **2026-11-12（上游对齐 P3）** 扩为 **9 字段**（新增 `configurable` / `max_concurrency` / `recursion_limit` / `run_name` / `run_id`）⇒ ⇒ ⇒ ⇒ 本 feature 以**仓库现状**为准（裁定 5 依赖该字段清单）⇒ ⇒ ⇒ ⇒ 上位文档的修订属**发起者**职权 ⇒ 本 feature **不**单方面改立项书 |
| **引文差异 2** | 提示词 §2 写「`run_super_steps(spec, state=None, *, max_steps=25)`」 | **事实订正**：缺省是 **`max_steps=10007`**（`src/freegraph/runtime/superstep.py:1409`）⇒ ⇒ 冻结口径以**实际实现**为准（B7F1 已按上游 `DEFAULT_RECURSION_LIMIT = 10007` 校准）⇒ ⇒ 本 feature 只依赖「`state` MAY 省略」这一条（裁定 27），**不**依赖 `max_steps` 的具体缺省 |
| **引文差异 3** | 提示词 §4 FR-006 说「在 **B10F1 接手之前**，`invoke` MUST 照常把 `GraphInterrupt` 抛给调用方 ⇒ 待 B10F1 落地后才转成 `__interrupt__` 键」 | **事实订正**：**B10F1 已落地** ⇒ `run_graph` 已把中断轮合并抛出的 `GraphInterrupt` **转成 `InterruptResult`**（`superstep.py:1739-1740` 的 `except GraphInterrupt` ⇒ `_suspend`）⇒ ⇒ ⇒ 故 `invoke` **不**存在「照常抛出」这条分支 ⇒ ⇒ ⇒ 唯一路径 = `as_result_dict()`（裁定 8）；若仍从 L2 抛出 `GraphInterrupt`，则原样抛出（裁定 9） |
| **引文差异 4** | 提示词 §2 写「LangGraph 实测 `invoke()` 返回的键集为 `['llm_calls','messages']` —— 即**所有 schema key**」 | **事实订正 + 口径收紧**：那是「**输入给了全部 key**」的情形；上游对**从未写入**的 key 是**省略**的（**实测 E-1**：`invoke({"messages": []})` ⇒ 键集 `['messages']`）⇒ ⇒ ⇒ 本 feature 的「键集 == schema 全集」是**比上游更严**的口径（**STRICTER** · **X-1**），**不是**照抄 ⇒ ⇒ ⇒ 必须以差分场景 **D-94** 锁住 ⇒ ⇒ ⇒ ⚠️ **2026-11-16 clarify 轮 · 用户拍板**：**保留**这条更严口径（选项 A · 填充值 = `None`）⇒ ⇒ ⇒ 并接受随之而来的「返回值不可原样回喂」的代价（以**文档禁令**消化 · FR-009 / SC-020）⇒ ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮 · 顺序亦订正**：上游的返回**键序 = schema 声明顺序**（实测 `['messages','llm_calls']`）⇒ ⇒ ⇒ ⇒ 本 feature 的键序口径与上游**逐字同款**（**SAME**）⇒ ⇒ ⇒ ⇒ 差分 **D-93** 的期望键序同步订正 |
| **引文差异 5** | 提示词 §2 说「`B22F1` / `B23F1` 必须**先于** `invoke` 就绪」 | **保留但改为下游承接**：本 feature **MUST NOT** 越界实现 `get_graph` / `draw_mermaid_png` ⇒ 落 **下游承接 D-3** · 裁定 16 |
| **引文差异 6** | 提示词 §4 FR-004 说「节点返回**未知 key** ⇒ 抛 `InvalidUpdateError`」 | **标注为更严**：上游**静默忽略**（**实测 E-2**：不抛错、无告警）⇒ ⇒ ⇒ freegraph 的抛错是**失败信号更严** ⇒ 偏离登记 **X-2**（判词 **STRICTER**）⇒ ⇒ ⇒ MUST 以差分场景 **D-95** 锁住 |
| **引文差异 7** | 提示词 §8 边界说「不实现 checkpoint —— `invoke` 本 feature 不落盘状态」 | **澄清**：本 feature **只把**编译产物持有的 `checkpointer` **透传**给 L2（**MUST NOT** 自己落盘 / 自己实现 saver）⇒ ⇒ 与 B14F1 的落盘职责**互补而非冲突**⇒ 落 **下游承接 D-4** |
| **引文差异 8** | 提示词 §3 P2 的独立验收写「`result["llm_calls"] == 2`（两轮模型调用）」 | **保留但补边界**：该断言在「**每轮都写 `llm_calls`**」的节点形态下成立（`harness/demo/agent_loop.py:172`）⇒ ⇒ 若某 schema 的 key **从未被写**，其返回值为 **`None`**（裁定 3）⇒ ⇒ ⇒ **不是** `0` ⇒ ⇒ ⇒ 判据 MUST 写成「**该 key 被写过的**用例里 == 实际轮数」 |
| **引文差异 9** | 提示词 §9 说「本 feature 是**固定脚本的验收关键路径**」 | **澄清**：固定脚本（`harness/demo/target.py`）的**只读基准 diff 断言**归 B3F1 的门禁 3（**MUST NOT** 改它）⇒ ⇒ 本 feature 的义务是「**让脚本能跑通**」+「**人工验证记录补上两轮实测输出**」（H-4 ⑥）⇒ ⇒ **不是**「往脚本里加断言」 |
| **引文差异 10** | 提示词 §4 FR-002 说「`config` MUST 同时接受 `RunConfig` 实例与普通 dict」，但**未提** L1 协议的 `config` 注解要不要一并放宽 | **补齐（2026-11-16 clarify 轮 · 用户拍板）**：L1 协议现写 `config: RunConfig \| None`（**只收 `RunConfig`**）⇒ 与 FR-002 **冲突** ⇒ ⇒ L1 协议的 `config` 注解 MUST **一并放宽**为 `RunConfig \| Mapping[str, Any] \| None`（**与 L2 的 `run_graph` 逐字同款**）⇒ ⇒ 与 `input` 的放宽放在**同一次**登记 + 回溯修订 + 追认里（追认额度仍 == **1 次**）⇒ ⇒ 落点：FR-001 / FR-021 · 裁定 1 · 破冻结面 **T-1**（`config` 行）· SC-019 |
| **引文差异 11** | 提示词 §5 的 **SC-001…SC-005** 与本 spec 的 **SC-001…SC-020** **编号同形、含义不同**（提示词 SC-003 = 未知 key ⇒ 本 spec **SC-004**；提示词 SC-004 = config 双形态 ⇒ 本 spec **SC-006**；提示词 SC-005 = 零出站 / 零 env ⇒ 本 spec **SC-011 / SC-012**；提示词 SC-002 的「`llm_calls` == 轮数」半句 ⇒ 本 spec **SC-003**） | **事实订正 + 编号域隔离**（2026-11-16 analyse 轮 · **S-16**）：本 spec 的 SC 编号**以本 spec 为准** ⇒ ⇒ ⇒ 提示词的 SC 编号**作废**（不得引用）⇒ ⇒ ⇒ ⚠️ **不得**按提示词的 SC-003 去查本 spec 的 SC-003（后者 = `llm_calls` 的**覆盖**语义）⇒ ⇒ ⇒ ⇒ 本 spec 正文与「引文差异」表**均不引用**提示词的 SC 编号 ⇒ ⇒ ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第五轮 · FND-F2 回修**：提示词初稿**本身**已加**编号域隔离**注（其 `SC-001…SC-005` 标「**已作废**」）+ 其内部的 `SC-004` 引用已订正为「**B7F3 的 SC-013**」 |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 一次调用跑完整张图，拿到完整状态 (Priority: P1)

作为用户，我调 `agent.invoke({"messages": [...]})` 就能拿到图跑完后的**完整状态**，
其中 `messages` 包含**初始消息 + 所有新增消息**，而不是只有新增的那些。

**Why this priority**: 这是本 feature 的**最高判据**（提示词 P1 / A1 / A2 / SC-001 / SC-002），
也是 **MVP 六项最小交付集**的第 3 项；「只返回增量」会让只读基准脚本的
`messages["messages"]` 取不到历史。

**Independent Test**: 建一张 2 节点的图（节点往 `messages` 追加）⇒ 调
`invoke({"messages": ["seed"]})` ⇒ 断言返回的 `messages` **逐字**等于
`["seed", <新增>]` ⇒ 且返回的键集 == schema 键集。

**Acceptance Scenarios**:

1. **Given** 一张含 2 个节点的图（节点依次往 `messages` 追加 `["a"]` 与 `["b"]`），
   **When** 调 `invoke({"messages": ["seed"]})`，**Then** 返回的 `messages` 逐字等于
   `["seed", "a", "b"]`（**初始 + 全部新增**）。
2. **Given** 同一张图，**When** 调 `invoke(...)`，**Then** 返回值的**键集**逐字等于
   schema 的**全部** key 集合（不只是被写过的 key）⇒ ⇒ ⇒ **且键的**顺序**与
   schema 声明顺序逐字一致**（⚠️ **2026-11-16 analyse 轮第五轮 · FND-N3 回修**：
   顺序也是判据的一部分 ⇒ **只断言「集合相等」不足**）。
3. **Given** 同一张图，**When** 比较返回值的 `messages` 与「节点写入值的累积」，
   **Then** 两者**逐字相等**（返回的是**完整状态**而非增量）。
4. **Given** 一张**多源汇合（屏障）**图（`add_edge(["a", "b"], "c")` · **静态多源边** ·
   **B7F4 已交付于 L2** ⇒ **不依赖 B8F1 的条件边路由**），
   **When** 调 `invoke(...)`，**Then** 屏障目标 `c` 的写入出现在**所有**源之后
   （执行序 `a`/`b` → `c`）⇒ ⇒ ⇒ ⇒ 且**完整状态**含 `c` 的写入
   （⚠️ **2026-11-16 analyse 轮第五轮 · FND-N3 回修**：SC-013 的**屏障半边**在本故事层
   亦须有验收场景 ⇒ 此前只落在任务层）。

---

### User Story 2 - 计数型 key 也在返回里 (Priority: P1)

作为用户，我的 schema 有 `llm_calls`，我希望它也出现在返回状态里（值为最终计数），
而且**从未被写过的** schema key 也**一定在**（无值者的值明确为「无值」）。

> ⚠️ **口径注（2026-11-16 analyse 轮 · 消歧）**：「无值者填什么」**分两类**——
> ① **覆盖型（无归约器）**通道**从未被写** ⇒ 该 key **在**返回键集里 · 值 = **`None`**；
> ② **归约型**通道**从未被写** ⇒ 其稀疏视图里**已有**「**类型空值**」（`list` → `[]` · `int` → `0`）
> ⇒ ⇒ 该 key **在**返回键集里 · 值 = **类型空值**（**不是** `None`）⇒ ⇒ ⇒ **MUST NOT** 把类型空值改写成
> `None`（契约 R-06 · data-model §2.3 · 计划 R-9）⇒ ⇒ ⇒ 「键一定在」这条承诺**对两类都成立**，
> **变的是「无值」的具体取值**。

**Why this priority**: 提示词 P2 / SC-002 的直接判据；且「键一定在」是 freegraph
相对上游**更确定**的一处承诺（上游会省略从未写入的 key）。

**Independent Test**: 一个节点每轮写 `{"llm_calls": n+1}` ⇒ `invoke` 后断言
`out["llm_calls"] == 2`；另一张图里 `llm_calls` **从未被写** ⇒ 断言
`"llm_calls" in out` 且 `out["llm_calls"] is None`。

**Acceptance Scenarios**:

1. **Given** 节点每轮写 `llm_calls`（计数递增），**When** 调 `invoke`，
   **Then** 返回的 `llm_calls` == **实际轮数**（无归约器 ⇒ **覆盖**而非累加）。
2. **Given** schema 含一个**从未被写**的**覆盖型（无归约器）**key，**When** 调 `invoke`，
   **Then** 该 key **仍在返回值的键集里**（值 = `None`）⇒ ⇒ 用户**不必**写 `.get(k, default)`。
   ⚠️ **归约型 key 的例外**：**从未被写**的**归约型**key 同样**在**键集里，但值 = **类型空值**
   （`[]` / `0`）⇒ ⇒ **不是** `None`（契约 R-06）。
3. **Given** 同一张图，**When** 观察**节点入参**，**Then** 入参**仍然稀疏**
   （无值 key **不**出现在入参里 ⇒ `state.get(k, default)` 仍返回 `default`）。

---

### User Story 3 - 未知 key 会被立刻指出 (Priority: P1)

作为用户，我的节点误写了一个 schema 里没有的 key，我希望报错指明是哪个 key，
而不是让这次运行「看起来成功了」却悄悄丢掉那次写入。

**Why this priority**: 提示词 P3 / A3 / SC-004 的直接判据；也是 freegraph 相对上游
**更严**的一处失败信号（上游静默忽略）。

**Independent Test**: 节点返回 `{"messages": [...], "typo_key": 1}` ⇒ 断言抛出
`InvalidUpdateError`，且异常消息**含** `typo_key`。

**Acceptance Scenarios**:

1. **Given** 一个节点返回了 schema 之外的 key，**When** 调 `invoke`，
   **Then** 抛 `InvalidUpdateError`，且消息**含该 key 名**。
2. **Given** 一个节点返回了**多个**未知 key，**When** 调 `invoke`，
   **Then** 抛 `InvalidUpdateError`，且消息**含全部**未知 key 名。
3. **Given** 上述任一错误图，**When** 调 `invoke`，**Then** 异常**原样**到达调用方
   （类型未被包装）⇒ 且**不**返回任何部分结果。

---

### User Story 4 - 两种 config 形态都能用 (Priority: P2)

作为用户，我既能用一个现成的 `RunConfig` 对象，也能直接传一个普通字典
（带 `recursion_limit` 之类运行期参数）——两种形态都能生效。

**Why this priority**: `harness/demo/graph_core.py` 的 A9 组（`RunConfig` 实例）与
A8 组（`{"recursion_limit": 3}`）都是**硬断言**；B13F1 已把「dict 是运行期载体」锁死。

**Independent Test**: 同一张自环图 ⇒ 分别用 `{"recursion_limit": 3}` 与
`RunConfig(max_concurrency=1)` 调用 ⇒ 断言前者抛 `GraphRecursionError`、后者正常跑完
⇒ ⇒ ⇒ **另**（**SC-006 的判定性半边**）：一张 **fan-out 图**
（`START→a` / `START→b` ⇒ **两个节点落在同一 super-step**）⇒ 分别用
`RunConfig(max_concurrency=1)` 与缺省调用 ⇒ ⇒ 断言「**可观测并发度**」
（两节点的**同时在飞**重叠计数）分别为 **0** 与 **≥ 1**
⇒ ⇒ ⚠️ **自环图**（单节点 ⇒ 每轮只有一个任务）⇒ 重叠**恒为 0** ⇒ 该断言**空洞**
⇒ ⇒ ⇒ **并发度的判定 MUST 用 fan-out 图**（⚠️ **2026-11-16 analyse 轮第五轮 · FND-N3 回修**）。

**Acceptance Scenarios**:

1. **Given** 一张自环图，**When** 调 `invoke(input, {"recursion_limit": 3})`，
   **Then** 抛 `GraphRecursionError`（**类型不被包装**）且 `.recursion_limit == 3`。
2. **Given** 同一张图，**When** 调 `invoke(input, RunConfig(max_concurrency=1))`，
   **Then** 正常跑完且结果与并发档**逐字一致**（串行基线）。
3. **Given** 任一形态的 `config`，**When** 调用，**Then** **不**抛 `TypeError`
   （两种形态都被接受）。
4. **Given** 一张 **fan-out 图**（`START→a` / `START→b` ⇒ 同一 super-step）·
   **When** 调 `invoke(input, RunConfig(max_concurrency=1))`，
   **Then** 两个节点的「**同时在飞**」**重叠计数 == 0**（串行基线）⇒ ⇒ ⇒
   ⚠️ 该判定 MUST 用**确定性同步**构造（`threading.Event` / `Barrier` 互等到齐）⇒ ⇒
   ⇒ MUST NOT 依赖「时间流逝」⇒ ⇒ 「等不到对端」MUST 以**超时兜底**
   （超时**不**判失败 · 串行**正是**期望）。
5. **Given** 同一张 **fan-out 图** · **When** 调 `invoke(input)`（缺省档），
   **Then** 重叠计数 **≥ 1** ⇒ ⇒ ⇒ ⇒ **这一条才是「旋钮生效」的判定性证据**
   （缺省档仍不重叠 ⇒ 说明 `RunConfig.max_concurrency` 被静默忽略 ⇒ 必红）⇒ ⇒ ⇒ ⇒
   ⇒ ⇒ ⇒ ⇒ **AND** `RunConfig(max_concurrency=1)` 档与缺省档的**最终状态逐字相等**
   （**补充**判据 · MUST NOT 单独依赖它）。

---

### User Story 5 - 挂起与恢复可观察 (Priority: P2)

作为用户，我的节点请求人工审批时，我希望 `invoke` **返回**一个带 `__interrupt__` 的结果
（而不是抛一个我得自己解包的控制流异常），并在恢复时用 `Command(resume=...)` 继续。

**Why this priority**: 承接 H-4 ③ 与 H-5 ②；且只读基准脚本的 A6 组直接读
`result.get("__interrupt__")` 并检查元素的 `.value` / `.id`。

**Independent Test**: 一个调用 `interrupt("approve?")` 的节点 ⇒ `invoke` 后断言
`result["__interrupt__"]` 存在且其元素有 `.value == "approve?"` 与 `.id`；
再用 `Command(resume="yes")` 恢复 ⇒ 断言节点拿到恢复值。

**Acceptance Scenarios**:

1. **Given** 节点在执行中请求人工审批，**When** 调 `invoke`，
   **Then** 返回值含 `"__interrupt__"` 键，其元素具备 `.value` 与 `.id`。
2. **Given** 同一张图（**挂 checkpointer** · 测试侧的**自足桩** · tasks T002 交付 · 见 SC-010 的载体条款），
   **When** 调 `invoke(Command(resume="yes"))`，
   **Then** 被中断的节点**从头重跑**并拿到恢复值「yes」。
3. **Given** 一次**未挂起**的运行，**When** 调 `invoke`，
   **Then** 返回值**不含** `"__interrupt__"` 键。

---

### User Story 6 - 一次编译，多次互不干扰的会话 (Priority: P2)

作为用户，我希望**编译一次**就能在多个会话里反复调用，而且**互不干扰**：
连续两次调用不累积、并发两次调用不串扰。

**Why this priority**: 承接 H-2；与 B7F2 的「编译产物持规格」**共同**落成
「一次编译、多会话隔离」的**门面级**验收（这正是 B12F1 的 D-4 留给本 feature 的那半边）。

**Independent Test**: 编译一张图 ⇒ 连续调两次 `invoke` ⇒ 断言第二次的结果**不含**
第一次的新增；再并发调两次 ⇒ 断言两次结果**互不含**对方的值。

**Acceptance Scenarios**:

1. **Given** 一张已编译的图，**When** **连续**调两次 `invoke`（各自带自己的初始消息），
   **Then** 第二次的 `messages` **只含**第二次的初始消息 + 第二次的新增（**不累积**）。
2. **Given** 一张已编译的图，**When** **并发**调两次 `invoke`，
   **Then** 两次结果**互不串扰**（各自的 `messages` 只含各自的值）。
3. **Given** 同一张编译图，**When** 检查其持有的通道，**Then** 每个通道仍是
   **未被写入过值的规格模板**（零状态残留）。

---

### User Story 7 - 执行过程零副作用 (Priority: P3)

作为用户，我希望执行这一步**不**偷偷联网、**不**读我的环境变量、**不**引入任何
第三方依赖 —— 以免「只是跑一次图」却触发了副作用。

**Why this priority**: 宪法原则 I（零出站 / 零环境变量）与原则 X（依赖门禁）是**红线**；
且执行期副作用会与「图逻辑本身的副作用」混淆，破坏可诊断性。

**Independent Test**: 用 socket 监测夹具 + `sys.modules` 快照观测 ⇒ 断言出站连接数 == 0、
`langchain*` / `langgraph*` / `langsmith` 出现次数 == 0。

**Acceptance Scenarios**:

1. **Given** 任意环境变量（含 `LANGSMITH_*`），**When** 调 `invoke`，
   **Then** 执行行为**不因环境变量而改变**，且 freegraph 自身发起 **0** 次出站连接。
2. **Given** 一次完整的 `invoke`，**When** 检查导入面，
   **Then** `sys.modules` 中 `langchain` / `langchain_core` / `langgraph` / `langsmith`
   的出现次数 == **0**。

---

### Edge Cases

- **schema 的某个 key 从未被写**：MUST **仍在**返回键集里 ⇒ ⇒ ⚠️ **值分两类**（裁定 3 的消歧）——
  ① **覆盖型（无归约器）**通道 ⇒ 值 = **`None`**（该 key 在稀疏视图里**缺席** ⇒ 由 FR-009 补齐）
  ② **归约型**通道 ⇒ 值 = **类型空值**（`list` → `[]` · `int` → `0`）⇒ ⇒ ⇒ **不是** `None`
  ⇒ ⇒ ⇒ **MUST NOT** 把类型空值改写成 `None`（契约 R-06 · data-model §2.3）
  ⇒ ⇒ ⇒ **节点入参**仍**稀疏**（C4 不受影响）。
- **把返回值原样回喂给下一次 `invoke`**：**禁止**（FR-009）⇒ 回喂会把补齐的 `None`
  **真的写进**通道 ⇒ 覆盖型通道的值变成 `None` ⇒ 节点里 `state.get("llm_calls", 0) + 1`
  会 `TypeError`；归约型通道会被追加一个 `None` ⇒ ⇒ ⇒ ⚠️ **上游没有这个坑**
  （上游省略无值 key ⇒ 回喂**安全** · **实测 E-5**）⇒ ⇒ ⇒ 故本禁令 MUST 写进用户可见文档；
  ⇒ ⇒ ⇒ ⚠️ **「用户显式传入 `None` 作为初始值」不受影响**（那是**写入语义**，仍照写）。
- **schema 的某个 key 被写了 `None` 本身**：MUST 出现在返回值里、值 = `None`
  ⇒ ⇒ 与「从未被写」在**值上**不可区分（freegraph 的通道**无**「有无值」与「值为 None」的区分）
  ⇒ ⇒ 上游同款（`None` ≠ `MISSING`）。
- **`input` 为空字典 `{}`**：合法 ⇒ 不写任何通道 ⇒ 图照常从入口跑。
- **`input` 为 `None`**：合法（恢复 / 会话连续路径）⇒ MUST 走 L2 的既有分支
  （**B10F1 FR-013 的表**末两行）⇒ ⇒ **不**要求 checkpointer、**不**触发恢复。
- **`input` 为 `Command(resume=...)` 但未挂 checkpointer**：MUST 抛**明确异常**
  （`InterruptError(reason="checkpointer_required")`）⇒ ⇒ **MUST NOT** 静默降级为
  「内存态恢复」（H-4 ④）。
- **`input` 含 schema 之外的 key**：沿用 L2 的既有口径 ⇒ 抛 `InvalidUpdateError`
  （**比上游更严** · X-3）⇒ ⇒ 上游是「静默忽略 + 日志告警」。
- **`config` 为 `RunConfig` 与普通 dict 的其它映射类型**：合法映射即接受 ⇒
  **MUST NOT** 只认 `dict` 这一种具体类型。
- **`config` 含 L2 不认识的键**：MUST **原样**交给 L2 ⇒ 由 L2 既有口径决定
  （`RunConfig.from_dict` 的 `ignore_unknown` 语义）⇒ ⇒ **MUST NOT** 在门面层静默丢弃。
- **`config` 为 `None`**：等价于「不传运行期参数」⇒ 用 L2 的缺省
  （`recursion_limit` = 10007 · 硬编码 · **不读环境变量**）。
- **节点返回**未知 key**：抛 `InvalidUpdateError` 且消息点名（**更严** · X-2）。
- **节点返回**空字典 `{}`：合法（不写任何通道）⇒ 图照常推进。
- **节点返回**非字典（如 `None` / 列表）：沿用 L2 的既有口径（`InvalidChannelUpdateError`）
  ⇒ ⇒ 本 feature **只透传**、MUST NOT 包装。
- **节点内部抛异常**：**原始类型 + 原始消息**传播（不包装、不吞掉）。
- **节点请求人工审批（`interrupt()`）**：转为 `__interrupt__` 键（**唯一**转成路径）⇒
  ⇒ **不**当作「出错」。
- **图跑成死循环**：`recursion_limit` 生效 ⇒ 抛 `GraphRecursionError`（不包装）。
- **图里没有任何待执行节点**（空轮）：合法 ⇒ 返回**完整状态**（schema 全键 + 无值者 `None`）。
- **同一张编译图被**并发**调用**：互不串扰（每次调用新建通道实例）。
- **同一张编译图被**连续**调用**：不累积（每次调用新建通道实例 + 新建调度状态）。
- **路由型通道（`branch:to:*`）的值**：MUST **不**出现在返回值的键集里
  （它**不是** schema key）⇒ ⇒ 且 MUST NOT 假设其值残留到下一次 `invoke`（**B7F1 的**裁定 33）。
- **静态挂起（`interrupt_before` / `interrupt_after`）**：返回
  `{**state, "__interrupt__": ()}`（**空元组**）⇒ ⇒ 走**同一条**转成路径。
- **`invoke` 在任何合法路径上**：MUST **不**抛 `NotImplementedError`
  （就绪探针以它为判据 · `harness/demo/graph_core.py:555-571`）⇒ ⇒ 该脚本从
  「退出码 2」转为「正常跑完」。
- **`invoke` 被调用于**未编译**的构建器**：MUST NOT 存在这条路径（执行入口在编译产物上）。
- **`stream()` / `get_graph()` / `get_state()` / `get_state_history()` / `update_state()`**：本 feature **不**实现
  ⇒ ⇒ 仍抛内置 `NotImplementedError` 且消息**点名归属 feature**（B7F2 口径不变）。
  ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮 · 第三轮回修（FND-C2 · 清单补全）**：原条目只列 **4** 个（漏 `get_state_history()`）⇒ ⇒ ⇒ ⇒ 已补齐为 **5** 个（与 **FR-026** 的「其余 **5** 个能力面方法」一致）。

---

## Upstream Parity *(mandatory — 宪法 v1.12.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11**（取证于 2026-11-16 ·
`/home/ctyun/workspace/github/freegraph/.venv/lib/python3.11/site-packages/langgraph`）
· `langchain-core` **1.7.6**（同目录取证）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | `invoke` 的**方法名与入参形态** | `langgraph/pregel/main.py:3836-3838`（`input: InputT \| Command \| None`）· `:3839`（`config: RunnableConfig \| None = None`） | 同款：`input` 接受「状态字典 / `Command` / `None`」；`config` 为第二位置参数、缺省 `None` | SAME | 上游同款 ⇒ 宪法原则 III 第 6 项 · 破 L1 冻结面（裁定 1） |
| P-02 | `invoke` 返回**完整状态**而非增量 | `langgraph/pregel/main.py:3913-3944`（`stream_mode="values"` ⇒ 逐 chunk 取最后一个 `values` 载荷）· `:3946-3955`（`return latest`） | 同款：返回**最终状态**（初始值 + 全部新增） | SAME | 原则 XI 照抄 · 提示词 A2 |
| P-03 | 返回键集 = **有值**的 output channel | `langgraph/pregel/_io.py:38-53`（`read_channels`：`skip_empty=True` ⇒ `except EmptyChannelError: pass` ⇒ **省略**无值 channel）· `langgraph/graph/state.py:127-131`（`output_channels` = output schema 的 key）· **实测 E-1 / E-5 / E-8**：上游的返回值**可安全回喂**（省略 ⇒ 回喂不注入 `None`） | 返回**全部 schema key**（含从未写入者 ⇒ ⚠️ **仅覆盖型（无归约器）通道**的值 = `None`；**归约型**通道未写时其稀疏视图里**已有**「类型空值」（`[]` / `0`）⇒ ⇒ **MUST NOT** 改写成 `None` · 契约 R-06）⇒ ⇒ ⚠️ **代价**：返回值**不可**原样回喂（补的 `None` 会被写进通道）⇒ ⇒ 该禁令 MUST 写进用户可见文档（FR-009） | **STRICTER** | 原则 III 第 7 项 + C11 + 提示词 FR-001 / SC-001；上游的「省略」让「键是否存在」取决于「恰好有没有写过值」⇒ 属原则 XI ② 类 ⇒ **X-1** |
| P-04 | 节点返回**未知 key** | **实测 E-2**：上游**静默忽略**（不抛错、无告警）· `langgraph/errors.py:90-99`（`InvalidUpdateError` 存在，但**不由**该路径抛出） | 抛 `InvalidUpdateError` 且消息**点名**违规 key | **STRICTER** | 原则 XI「失败信号 MAY 更严」+ C6 红线；「拼错的 key 无声地少跑」⇒ **X-2** |
| P-05 | 初始输入含**未知 key** | `langgraph/pregel/_io.py:81-97`（`map_input`：不在 `input_channels` 的 key ⇒ **只** `logger.warning`）· **实测 E-3** | 沿用 L2 既有口径 ⇒ 抛 `InvalidUpdateError` | **STRICTER** | 同上；且属 **B7F1 FR-007** 已冻结的行为 ⇒ 本 feature **只透传** ⇒ **X-3** |
| P-06 | 节点抛出的**真异常** | 上游**原样传播**（`GraphBubbleUp` 只抑制中断）· **实测 E-4** | 同款：**原始类型 + 原始消息**；MUST NOT 包装 / 吞掉 | SAME | 原则 XI 照抄 · 裁定 9 |
| P-07 | **中断**的对外形态 | `langgraph/pregel/main.py:3949-3954`（`{**latest, INTERRUPT: interrupts}`）· `langgraph/_internal/_constants.py:9`（`INTERRUPT == "__interrupt__"`）· 值 = **list** | `{**state, "__interrupt__": interrupts}` · 值 = **tuple**（B10F1 已冻结） | DIFF（仅值形态 · 非更严） | 已由 **B10F1** 登记并追认 ⇒ 本 feature **只透传 · 不新增登记** |
| P-08 | `config` 的**载体类型** | `langgraph/pregel/main.py:3839`（`RunnableConfig`） | `RunConfig \| Mapping[str, Any] \| None`（**双形态**） | DIFF（载体面 · 非更严） | freegraph 的 `RunnableConfig` 对应物是 **L1 的 `RunConfig`**（B2F1 冻结）⇒ 双形态是本项目的**已锁定形态**（`harness/demo/graph_core.py:33-35`） |
| P-09 | `recursion_limit` | `langgraph/_internal/_config.py:32`（缺省 `10007`，**读环境变量** `LANGGRAPH_DEFAULT_RECURSION_LIMIT`）· `langgraph/pregel/main.py:2563-2564`（`< 1` ⇒ `ValueError`）· `:3002-3011`（超限 ⇒ `GraphRecursionError`） | dict 形态**原样**透传；缺省**硬编码** `10007`（**零环境变量**）；超限抛 `GraphRecursionError`（**不包装**） | DIFF（缺省来源 · 非更严） | 零环境变量红线（原则 I）⇒ 行为面 **SAME**（超限信号逐字一致）⇒ 缺省来源差异已由 **B13F1** 登记 ⇒ 本 feature **只透传** |
| P-10 | `max_concurrency` | `langchain_core/runnables/config.py:103-108`（`max_concurrency: int \| None`）· `:659-675`（`get_executor_for_config` ⇒ `ContextThreadPoolExecutor(max_workers=…)`） | `RunConfig.max_concurrency`（**同名同义** · `types.py:216`）· 缺省 `None` ⇒ `min(32, cpu+4)` ⇒ ⇒ ⚠️ **2026-11-16 clarify 轮（Q2 = B）**：旋钮的读取点**下沉到 L2**（`run_graph` 关键字优先 · `config` 兜底）⇒ ⇒ 与上游「旋钮在 **config** 里」**更同款** | SAME | 上游同款 ⇒ 裁定 13 · L1 冻结面零改动（`RunConfig` **不**扩字段）· L2 的改动属**兼容扩展**（回溯修订 **T-3**） |
| P-11 | 编译产物只持通道**规格** · 每次运行**新建实例** | `langgraph/channels/last_value.py:50-54`（`from_checkpoint` ⇒ `self.__class__(…)`）· `langgraph/channels/base.py:61-64`（docstring：「Return a **new identical channel**」） | 同款：每次 `invoke` 新建通道实例 | SAME | 上游同款 ⇒ 「一次编译、多会话隔离」天然成立（裁定 10） |
| P-12 | 能力面（6 方法） | `langgraph/pregel/main.py:845` / `:1392` / `:1480` / `:2515` / `:2616+` / `:3783+` | 6 方法**全部存在**；本 feature **只**交付 `invoke` ⇒ 其余 5 个仍抛内置 `NotImplementedError` 且消息**点名归属 feature**（B7F2 口径不变） | DIFF（未就绪者的失败信号 · 非更严） | 方法面是 B2F1 冻结的**协议**（**SAME**）；B7F2 已冻结未就绪者的失败信号 |
| P-13 | `invoke` 的**入口形态**（第二位置参数 + 关键字） | `langgraph/pregel/main.py:3836-3850`（上游的 `invoke` 另有 `context` / `stream_mode` / `print_mode` / `output_keys` / `interrupt_before` / `interrupt_after` / `durability` / `control` / `version` 等关键字） | 同款：`invoke(input, config=None)` ⇒ ⇒ **已实现面**逐字一致（两个位置参数 + 无其它关键字）⇒ ⇒ **无**上游的其它关键字（v1 不实现）⇒ ⇒ ⚠️ 其中 `interrupt_before` / `interrupt_after` 在 freegraph 走 `compile(...)` 载体（**B13F1**）· `context` 走 `RunConfig.context`（**C21**）⇒ ⇒ ⇒ 其余（`stream_mode` / `output_keys` / `durability` / `control` / …）归 **B8F2 / v2 extras** | SAME（已实现面） | 原则 XI 照抄「只抄已实现的部分」；⚠️ **「上游有、freegraph v1 没有」属「能力尚未交付」⇒ 走 Out of Scope / 下游承接的口径（与 B7F2 的 5 个未就绪方法同款）⇒ MUST NOT 记为偏离**（偏离登记的三类 —— ① 必须自研区 ② 更严的失败信号 ③ 破已冻结的契约面 —— **不覆盖**「能力尚未交付」）⇒ ⇒ 落点：FR-026 · 下游承接 **D-1 / D-3** |
| P-14 | **`input=None`（无 checkpointer 的新会话）** | **实测 E-7** ⇒ 抛 `langgraph.errors.EmptyInputError`「Received no input for `__start__`」· `langgraph/pregel/_loop.py` 的首轮入参校验 | **照常跑**（不写任何通道，图从入口起跑）⇒ ⇒ **比上游更宽松** | DIFF（阶段性差异 · 非更严 · 更宽松） | **行为源自 B10F1 FR-013 的末两行（已冻结）** ⇒ 本 feature **只透传** ⇒ ⇒ ⚠️ 「更宽松」**不属**原则 XI 的「失败信号 MAY 更严」⇒ ⇒ ⇒ **如实登记、不掩盖**；⇒ 若要向上游对齐 ⇒ 归 **B10F1** 的回溯修订 ⇒ ⇒ ⇒ **X-6** |

> ⚠️ **双份维护的同步义务（2026-11-16 analyse 轮 · 第三轮 · **FND-B9**）**：本表与下方「偏离登记」表
> **同时**落成于 `contracts/upstream-parity.md` §2 / §4（该文件带 `<!-- authority: yes -->` 标记）
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **两处是「同一份内容的两处落点」** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **发现漂移 MUST 双侧同改**（MUST NOT 只改一侧）
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **已回修的历史漂移（C7）**：本表 P-03 引「实测 E-1 / **E-5** / **E-8**」，
> `upstream-parity.md` P-03 原引「实测 E-1 / **E-8**」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **两处已统一为「E-1 / E-5 / E-8」**

> ⚠️ **严格三态标注（2026-11-16 analyse 轮 · **D-C 决策** · **FND-M6**）**：本表「关系」列与下方
> 「偏离登记」的「类别」列**逐字相等**（`SAME` / `STRICTER` / `DIFF` 三态之一）⇒ ⇒ 一行含**多处分叉**时，
> 复合关系在**理由**列**拆分说明**（哪一处 SAME、哪一处 DIFF）⇒ ⇒ ⇒ **无孤行 / 无漏行**。

> **实测覆盖说明**：P-03 / P-04 / P-05 / P-06 的**行为**断言 MUST 有实测支撑
> （上游缺席即 `skip` · 沿用 B5F2 的「缺席即 skip」纪律）；P-01 / P-02 / P-07 / P-08 / P-09 /
> P-10 / P-11 / P-12 / P-13 属**结构面**断言（源码锚点 + 差分场景的可观察结果）
> ⇒ 换版本时 MUST 一并重跑。

### 差分场景组 *(mandatory)*

> **落点**：`tests/differential/parity_probe.py` ⇒ CI 的 Linux 全量档真跑
> （上游缺席即 `skip`）。**编号从 `D-92` 起**（`D-01…D-91` 已被既有 feature 占用
> · B12F1 `D-01…D-15` / B7F4 `D-16…D-28` / B11F1 `D-29…D-37` / B13F1 `D-38…D-49` /
> B7F2 `D-50…D-91`）。

| # | 场景 | 断言（返回键集 / 值 / 失败与否） | 判词 |
|---|---|---|---|
| D-92 | 最小图 + `invoke({"messages": ["seed"]})` | 两侧返回的 `messages` **逐字相等**（初始 + 全部新增） | SAME |
| D-93 | 初始输入含**全部** schema key | 两侧返回的**键集**逐字相等（`['messages','llm_calls']` · **上游按 schema 声明顺序**） | SAME |
| D-94 | 初始输入**缺**一个**覆盖型（无归约器）** schema key（该 key 从未被写）⇒ ⚠️ **MUST** 用**覆盖型** key（如 `llm_calls`）⇒ ⇒ 若误用**归约型** key ⇒ 其值是**类型空值**（`[]`）而非 `None`（FR-009 的消歧） | 上游**省略**该 key；freegraph **保留**该 key（值 `None`）⇒ 键集**不等** | **STRICTER**（X-1） |
| D-95 | 节点返回**未知 key** | 上游**不抛错**（静默忽略）；freegraph 抛 `InvalidUpdateError` 且消息含该 key 名 | **STRICTER**（X-2） |
| D-96 | 初始输入含**未知 key** | 上游**不抛错**（静默忽略 + 日志告警）；freegraph 抛 `InvalidUpdateError` | **STRICTER**（X-3） |
| D-97 | 节点抛**真异常** | 两侧都抛**原异常**（类型与消息**逐字一致**） | SAME |
| D-98 | `config = {"recursion_limit": 3}` + 自环图 | 两侧都抛 `GraphRecursionError`；freegraph `.recursion_limit == 3` | SAME |
| D-99 | 同一张编译图**连续两次** `invoke` | 两侧**都不累积**（第二次的结果**不含**第一次的新增） | SAME |
| D-100 | 同一张编译图**并发两次** `invoke` | 两侧**都不串扰**（两次结果**互不含**对方的值） | SAME |
| D-101 | 中断后 `invoke` 的结果 | 两侧都含 `__interrupt__` 键、元素逐字一致；freegraph 的值为 **tuple**、上游为 **list** | DIFF（仅值形态 · X-4 透传） |
| D-102 | **多源汇合（屏障）**：`add_edge([a, b], c)` + 两个源 | 两侧的**最终状态**逐字相等（`messages` 含 `seed,a,b,c`）⇒ ⇒ 屏障目标 `c` 的写入出现在**所有**源之后 | SAME |

⇒ **共 11 条**（D-92…D-102）⇒ ⇒ **判词分布** = **SAME 7**（D-92 / D-93 / D-97 / D-98 / D-99 / D-100 / **D-102**）
+ **STRICTER 3**（D-94 / D-95 / D-96）+ **DIFF 1**（D-101 · 仅值形态）
⇒ ⇒ ⚠️ **STRICTER 的三条 MUST 各自带 `note`**（宪法原则 XI「失败信号更严须标注」）。
⇒ ⇒ ⚠️ **D-102 的上游依据**：上游 `langgraph 1.2.11` 的 `add_edge(["a","b"], "c")`
**同款**（实测 `messages == ['seed','a','b','c']` ⇒ 与 freegraph **逐字一致**）⇒ ⇒ ⇒ 判词 **SAME**
（原则 XI 照抄 · 非自研区 ⇒ 无需偏离登记）。

### 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **STRICTER**（更严 · 成功路径的可观察状态 · 原则 XI ② 类「上游自身的不确定」） | **返回键集**：上游只返回**有值**的 output channel（`langgraph/pregel/_io.py:38-53` · 实测 E-1 / E-8）⇒ freegraph 返回**全部 schema key**（无值者填 `None` ⇒ ⚠️ **仅覆盖型（无归约器）通道**适用；**归约型**通道未写时其稀疏视图里**已有**「类型空值」（`[]` / `0`）⇒ ⇒ **MUST NOT** 改写成 `None` · 契约 R-06） | 原则 III 第 7 项（`invoke` MUST 返回**完整状态**）+ C11 + 提示词 FR-001 / SC-001；上游的「省略」让「键是否存在」取决于「恰好有没有写过值」⇒ 用户被迫写 `.get(k, default)` ⇒ freegraph 让「**键一定在**」成为可依赖的事实 ⇒ ⇒ 属原则 XI 的 ② 类（上游自身的**不确定**）⇒ **判词 STRICTER** ⇒ **差分 D-94 锁住** ⇒ ⇒ ⚠️ **已知代价**（2026-11-16 clarify 轮 · 用户拍板）：返回值**不可原样回喂**（上游因省略而安全 · **实测 E-5**）⇒ ⇒ 该代价 MUST 以**文档禁令**消化（FR-009 · SC-020）⇒ ⇒ ⇒ **用户已确认接受**（选项 A）| 本 feature 内闭合 · 追认文字落 `harness/verification/B7F3/manual-verification.md` |
| **X-2** | **STRICTER**（更严的失败信号） | **节点返回未知 key**：上游**静默忽略**（实测 E-2）⇒ freegraph 抛 `InvalidUpdateError` 且消息点名 | 原则 XI「失败信号 MAY 比上游更严」+ C6 红线；「拼错的 key 无声地少跑」会让图「看起来成功」却结果不对 ⇒ ⇒ **差分 D-95 锁住** | 本 feature 内闭合 · 追认文字落同上手工验证记录 |
| **X-3** | **STRICTER**（更严的失败信号） | **初始输入含未知 key**：上游只 `logger.warning` 并忽略（`langgraph/pregel/_io.py:81-97` · 实测 E-3）⇒ freegraph 抛 `InvalidUpdateError` | 同上；且该行为**已由 B7F1 FR-007 冻结**（L2 既有口径）⇒ 本 feature **只透传 · 不新增实现** ⇒ ⇒ **差分 D-96 锁住** | 本 feature 内闭合（行为源自 **B7F1**）· 追认文字落同上手工验证记录 |
| **X-4** | **DIFF（仅值形态 · 非更严）** · ⚠️ **已由上游 feature 登记 · 本 feature 只透传 · 不新增追认**（2026-11-16 analyse 轮 · 措辞消歧） | `__interrupt__` 的值 = **tuple**（上游 = **list**） | 已由 **B10F1** 登记并追认 ⇒ 本 feature **只透传** ⇒ ⇒ **不新增登记项** | **B10F1**（已追认） |
| **X-5** | **DIFF（缺省来源 · 非更严）** · ⚠️ **已由上游 feature 登记 · 本 feature 只透传 · 不新增追认**（措辞消歧） | `recursion_limit` 的缺省**硬编码** `10007`（上游读环境变量 `LANGGRAPH_DEFAULT_RECURSION_LIMIT`） | 零环境变量红线（原则 I）· 已由 **B13F1** 登记 ⇒ 本 feature **只透传** ⇒ ⇒ **不新增登记项** | **B13F1**（已追认） |
| **X-6** | **DIFF（阶段性差异 · 非更严 · **更宽松**）** · ⚠️ **已由上游 feature 登记 · 本 feature 只透传 · 不新增追认**（措辞消歧） | `input=None`（无 checkpointer 的新会话）：上游抛 `EmptyInputError`（**实测 E-7**）⇒ freegraph **照常跑** | **行为源自 B10F1 FR-013 的末两行（已冻结）** ⇒ 本 feature **只透传** ⇒ ⇒ ⚠️ 「更宽松」**不属**原则 XI 的「失败信号 MAY 更严」⇒ ⇒ ⇒ **如实登记、不掩盖**；⇒ 若要向上游对齐 ⇒ 归 **B10F1** 的回溯修订（**不是**本 feature 的义务） | **B10F1**（FR-013 已冻结）· 本 feature **不追认** |

> ⚠️ **三态标注一致性**（宪法 v1.12.0 原则 XI 末条）：上表的 **STRICTER / DIFF** 标注与
> §Upstream Parity 表的**对应行逐字一致**；每条偏离都有对照表的对应行（**X-1↔P-03** ·
> **X-2↔P-04** · **X-3↔P-05** · **X-4↔P-07** · **X-5↔P-09** ·
> **X-6↔P-14**）⇒ ⇒ **判据零放宽**。
> ⚠️ **2026-11-16 analyse 轮复审回修（S-12）**：本偏离登记的「类别」列**原**写「更严（…）」/
> 「更严的失败信号」⇒ ⇒ 与对照表的 `STRICTER` **分类词不同**（正是原则 XI 末条要堵的失败模式）
> ⇒ ⇒ ⇒ **已回修为 `STRICTER` 令牌**（与仓库既有先例 **B10F1** 的偏离登记**同款**：`STRICTER（…）` /
> `DIFF（…）`）⇒ ⇒ ⇒ ⇒ **判据零放宽**（只改分类词 · 不改任何判定内容）。
> ⚠️ **对照表的 `DIFF` 行不全都有偏离登记条目**（**P-08** = `config` 载体面 · **P-12** = 未就绪者的
> 失败信号 · 均**非**「更严」⇒ 原则 XI 末条只要求「对照表标 **STRICTER** 的分叉 MUST 落在偏离登记里」）
> ⇒ ⇒ ⇒ **无孤行 / 无漏行**指的是「偏离登记的每一条都有对照表的对应行」这一方向。

### 破冻结面的回溯修订清单 *(若有)*

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| **L1 `CompiledGraph.invoke` 的 `input` 注解**（`src/freegraph/contracts/protocols.py:270-272` · 现为 `StateDict`） | ① `src/freegraph/contracts/protocols.py:270-272`（注解放宽为 `StateDict \| Command \| None`）　**＋ `protocols.py:22` 的 import（**补 `Mapping`** · ⚠️ **2026-11-16 analyse 轮 · 第三轮回修 · 行号订正**：原写「`:26`」⇒ **`:26` 实为 `from .trace import Span`**（内部模块导入）⇒ **改它会误伤 import** ⇒ ⇒ **正确目标是 `:22`**（`from collections.abc import Iterator, Sequence`））· ⚠️ **必要伴随改动（C1）**：该模块**无** `from __future__ import annotations` ⇒ 注解在**类体求值期**解析 ⇒ 缺 `Mapping` ⇒ `NameError` ⇒ **在 `import freegraph` 时抛出** ⇒ 全仓不可导入② `specs/b2f1-contracts-protocols/contracts/public-api.md` 的 **`CompiledGraph` 行（:82）** 与 **C11 行（:195）** ③ `src/freegraph/contracts/protocols.py:240` / `:263` 的 docstring 表行 | **拆分而不删**（2026-11-16 analyse 轮 · 措辞对齐 tasks **T005**（协议注解）+ **T006**（契约行注记） ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · L2 订正**：初版写「T005/T007」⇒ ⇒ ⇒ **T007** 是「桩原地替换 + docstring」⇒ ⇒ **不含**契约行注记 ⇒ ⇒ 引用已订正：**契约行**原行**保留**并标注「**自 B7F3 起放宽**」⇒ 既有断言（`StateDict` 形态仍合法）**不删**；**冻结断言行**按 tasks T014 的形态「**把该条从参数化列表中提出 ⇒ 改为独立断言**」⇒ 其余条目**逐字不动** | **发起者追认**落 `harness/verification/B7F3/manual-verification.md`（追认次数 **≤ 1** ⇒ 本 feature 的**唯一**一次） |
| **L1 `CompiledGraph.invoke` 的 `config` 注解**（`src/freegraph/contracts/protocols.py:270-272` · 现为 `RunConfig \| None`） | ① `src/freegraph/contracts/protocols.py:270-272`（注解放宽为 `RunConfig \| Mapping[str, Any] \| None` · **与 L2 的 `run_graph` 逐字同款**）② 同上 `public-api.md:82` / `:195` 两行 ③ 同上 `protocols.py:240` / `:263` 的 docstring 表行 | **拆分而不删**（措辞对齐 tasks **T005** + **T006** ⇒ ⚠️ **L2 订正**：初版写「T005/T007」⇒ ⇒ ⇒ **T007** 不含契约行注记 ⇒ ⇒ 引用已订正）：**契约行**原行**保留**并标注「**自 B7F3 起放宽**」⇒ 既有断言（只传 `RunConfig` 仍合法）**不删** | **并入上面那**唯一一次**追认（**同一次**登记覆盖两处放宽） |
| ⚠️ **`public-api-snapshot.txt`**（`specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`） | — （**MUST NOT 改**） | 该快照**只渲染门面导出面**（`freegraph.graph` 的 7 个符号）⇒ **不含** `invoke` 行（实测 `grep` 命中 **0**）⇒ ⇒ 改它 ⇒ **G16 逐字节红** ⇒ ⇒ ⇒ **MUST NOT** 列入回溯修订清单 | 不适用（未破面） |
| ⚠️ **破冻结面 T-4 · G19「既有契约层矩阵行逐字未改」的判据**（`tests/facade/test_facade_gates.py:492-535` · `test_existing_contract_rows_are_unchanged`） | ① `tests/facade/test_facade_gates.py`（新增 `MATRIX_ROWS_UPDATABLE_BY_B7F3 = frozenset({"CompiledGraph"})` · 比照 **B9F1 / B11F1 / B12F1** 的三处既有白名单写法 · **落地任务 = tasks T053** ⇒ ⇒ **MUST** 在 **T047**（README 矩阵行更新）之前落地）② `README.md` 的 **`CompiledGraph` 行**（兼容矩阵 · 「差异说明」列 ⇒ 移除「行为细节挂起 B7F3」一项） | **拆分而不删**：白名单**只放行这一行** ⇒ ⇒ 其余**契约层**行仍**逐字未改**（判据**只放宽一处**）⇒ ⇒ **等价程度（第三列）MUST NOT 变差**（`CompiledGraph` 保持 **部分等价** —— `invoke` 已交付，但 `stream` / `get_state` / `get_state_history` / `update_state` 仍**未交付** ⇒ **不得**升为「行为等价」）⇒ ⇒ ⇒ ⇒ ⚠️ **只放行「差异说明」列的措辞更新** ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮补记**：本行原**遗漏**（plan 改动面 §4 误断言「该两行**已在 G19 的可更新白名单**内」—— **事实错误**：`StateGraph` 属**门面层 7 符号**，**不**参与该字节比对；被比对且**无**白名单的恰恰是 `CompiledGraph`）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **已回修**（登记 + 白名单 + 追认三件齐备） | **并入那**唯一一次**追认**（**追认项第 ④ 项** · 与 L1 的两处放宽 ① ② + L2 读取点 ③ + 四处冻结断言 ⑤ **同属一次** ⇒ ⇒ **唯一事实源 = Assumptions 的「破面全集 5 类」**） |
| **L2 `run_graph` 的 `max_concurrency` 读取点**（`src/freegraph/runtime/superstep.py:1964-1967`） | ① `src/freegraph/runtime/superstep.py:1964-1967`（**关键字缺省时**回落到 `config.max_concurrency`）② `specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md` §2 的 `run_graph` 参数行 ③ `specs/b12f1-concurrency-errors/spec.md` 的 **FR-017 / 裁定 18** 行 | **拆分而不删**：原行**保留**并标注「**自 B7F3 起：关键字优先 · config 兜底**」⇒ ⇒ **兼容扩展**（既有调用方零改动 · 关键字的失败顺序**逐字不变**）⇒ ⇒ ⇒ **MUST NOT** 改 `run_graph` 的**签名** | **并入那**唯一一次**追认（与 L1 的两处放宽同属一次） |
| ⚠️ **冻结断言 ①**（清单第 4 行 · 「invoke 未就绪」· `tests/runtime/test_acceptance_script.py:15-34`） ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · L8 订正**：初版用「**第 4 处**」等编号 ⇒ ⇒ ⇒ ⇒ 易与「**第 4 条**冻结断言」混淆 ⇒ ⇒ ⇒ ⇒ ⇒ **改为「冻结断言 ①–④」**（清单行号另标） | `tests/runtime/test_acceptance_script.py:15-34`（`graph_core` 退出码 == 2 的断言） | **拆分而不删**：`rc == 2` 的断言**替换**为「**脚本成功**」= `rc == 0`（⇒ 期望**绿**）⇒ ⇒ **保留** subprocess **机制**断言（仍以子进程跑脚本并断言其退出码）⇒ ⇒ ⚠️ **判据只可更严 · MUST NOT 放宽**（2026-11-16 analyse 轮 · **S-17**）：**MUST** 断言 `rc == 0`（**不是**「不再是 2」⇒ **不是** `rc ∉ {2}`）—— 后者会让**真失败（rc == 1）**仍然判绿 ⇒ ⇒ ⇒ ⇒ ⇒ 而 G29 判定 2 与 T051 均要求验收脚本 **rc == 0**（且 T040 / T041 / T042 的降级只降低**断言强度**、脚本 MUST 仍全绿）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 保留「`[环境未就绪]` 文本检查」（该文本**只在未就绪分支**打印 · `graph_core.py:585/596` ⇒ invoke 交付后**永不出现** ⇒ 与「退出码不再是 2」**互斥**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **本行是「实测化清单」的候选**（plan **Phase 0′**（= tasks T011）的实测确认后回填） | 并入那**唯一一次**追认 |
| ⚠️ **冻结断言 ②**（清单第 5 行 · 「invoke 未就绪」· `tests/facade/test_facade.py:195-200`） | `tests/facade/test_facade.py:195-200`（`test_compile_reports_invoke_b7f3`：断言 `invoke` 抛 `NotImplementedError` 且消息含 `B7F3`） | **替换为反面断言**（`invoke` 已交付 ⇒ **不**抛 `NotImplementedError`）⇒ ⇒ **拆分而不删**（保留「产物具备 `invoke` 能力面」的语义）⇒ ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮补记**：本行原**遗漏**（plan 改动面 §6 / tasks T001 / T014 均按 **4 处**冻结断言计）⇒ ⇒ ⇒ 本清单**已回填为 4 处**（清单第 4 / 5 / 6 / 7 行 ⇒ **冻结断言 ① / ② / ③ / ④**） | 并入那**唯一一次**追认 |
| ⚠️ **冻结断言 ③**（清单第 6 行 · 「invoke 未就绪」· `tests/facade/test_facade.py:217-234`） | `tests/facade/test_facade.py:217-234`（`calls` 元组里的 `("invoke", ({},))` 条目） | **从参数化列表中提出**（split，**不删**语义）⇒ 改为**独立断言**（`invoke` 已交付 ⇒ **不**抛 `NotImplementedError`）⇒ ⇒ 其余 **5 个**条目**逐字不动** ⇒ ⇒ ⇒ `assert not hasattr(graph, "invoke")`（**构建器**侧）**保留** | 并入那**唯一一次**追认 |
| ⚠️ **冻结断言 ④**（清单第 7 行 · 「invoke 未就绪」· `tests/facade/test_compiled_graph.py:73-86`） | `tests/facade/test_compiled_graph.py:73-86`（`calls` 映射里的 `"invoke": (({},), "B7F3")` 条目） | **从参数化列表中提出**（split，**不删**语义）⇒ 改为**独立断言**（`invoke` 在合法路径上 MUST **不**抛 `NotImplementedError`）⇒ ⇒ 其余 **5 个**条目**逐字不动** | 并入那**唯一一次**追认 |
| **B7F2 的编译产物持有面**（3 私有字段 + 8 公开属性 · `tests/facade/test_compiled_graph.py:111-114` 断言 `vars()` 恰为 11 键） | — （**不破**） | **不动** ⇒ ⇒ 本 feature **MUST NOT** 增删编译产物私有字段 ⇒ ⇒ schema key 集合由**既有**字段推导（裁定 4） | 不适用（未破面） |

> ⚠️ **「冻结断言清单 MUST 实测化」**（宪法 v1.12.0）：实施**开始前** MUST 先跑一遍既有测试套件
> 并**记录绿基线**（计数）⇒ ⇒ 再按本 feature 的落地形态改动源码 ⇒ ⇒ **变红**的断言即入本清单
> ⇒ ⇒ MUST 逐条带 **`文件:行号`** + **变红原因** ⇒ ⇒ **MUST NOT** 只凭推理登记
> ⇒ ⇒ 落点：plan 阶段的「绿基线记录 + 变红清单」。

---

## Requirements *(mandatory)*

### Functional Requirements

#### A · 执行语义（对外入口）

- **FR-001**：编译产物 MUST 提供 `invoke(input, config=None)`；`input` MUST 接受
  「状态字典 / `Command` / `None`」，`config` MUST 接受「`RunConfig` / 普通映射 / `None`」
  ⇒ ⇒ MUST 返回**普通 `dict`**；MUST **NOT** 在任何合法路径上抛 `NotImplementedError`
  （就绪探针以它为判据）。
  ⚠️ **L1 协议同步放宽**（裁定 1 · **破 L1 冻结面**）：`src/freegraph/contracts/protocols.py`
  的 `CompiledGraph.invoke` 签名 MUST 写成
  `invoke(self, input: StateDict | Command | None, config: RunConfig | Mapping[str, Any] | None = None) -> StateDict`
  ⇒ ⇒ ⚠️ `input` **不**给缺省（保持**必填**位置参数 · 上游同款）⇒ ⇒ ⇒ 该放宽 MUST 走
  「登记 + 回溯修订 + 发起者追认」三条（**与 `config` 的放宽同属一次**）。
- **FR-002**：`invoke` MUST 驱动 L2 的 `run_graph(spec, input, *, checkpointer=..., config=...)`
  ⇒ ⇒ **MUST NOT** 另写一条「编译 → 执行」的路径；**MUST NOT** 复用「编译期已写入值的通道实例」
  ⇒ ⇒ `checkpointer` MUST 由编译产物**透传**（本 feature **MUST NOT** 自己落盘）。
- **FR-003**：`invoke` MUST 驱动整张图执行到终止（到达 `END` 或无待执行任务）
  ⇒ ⇒ 多源汇合边（屏障）MUST 在**同一条**执行路径上生效（**MUST NOT** 为屏障另开路径）
  ⇒ ⇒ 屏障目标 MUST 在**所有**源之后出现。
- **FR-004**：**每次** `invoke` MUST **新建**一份通道实例 ⇒ ⇒ 同一张编译图 MUST 可被
  **多个会话并发调用**而状态互不干扰 ⇒ ⇒ **连续**两次 MUST **不累积**。
- **FR-005**：`invoke` MUST **NOT** 依赖「调用方复用同一个调度状态」⇒ ⇒ **每次**调用
  **内部自洽**（自建调度状态）⇒ ⇒ 否则两次调用的「已消费版本」会串扰。
- **FR-006**：`invoke` MUST **NOT** 假设路由型通道的值残留到下一次调用
  （步末清空口径）⇒ ⇒ 路由通道**不**出现在返回键集里。

#### B · 状态语义（返回值）

- **FR-007**：返回值 MUST 是**普通 `dict`**（`type(out) is dict`）。
- **FR-008**：返回值的**键集** MUST **等于** schema 的**全部** key 集合（按 schema 声明顺序）
  ⇒ ⇒ MUST **NOT** 因「无值」漏 key   ⇒ ⇒ MUST **NOT** 出现 schema 之外的 key
  （路由通道等内部通道 MUST **NOT** 泄漏）
  ⇒ ⇒ ⚠️ **唯一例外** = **挂起**时的 `"__interrupt__"`（FR-014 产出 · 值为元组）
  ⇒ ⇒ ⇒ **非挂起**时该键 MUST **不**出现
  ⇒ ⇒ ⇒ ⇒ ⇒ **本条不收紧**（判据零放宽 · 2026-11-16 analyse 轮 · **D-C 决策**）。
- **FR-009**：**从未写入过**的 **覆盖型（无归约器）** schema key MUST 以 `None` 补齐 ⇒ ⇒ MUST **NOT** 省略。
  ⚠️ **「补齐」只作用于「缺席」的 key**（2026-11-16 analyse 轮 · 消歧）：**归约型**通道**从未被写**时
  其稀疏视图里**已有**「**类型空值**」（`list` → `[]` · `int` → `0` ⇒ 契约 R-06 · data-model §2.3）
  ⇒ ⇒ 该 key **不缺席** ⇒ ⇒ ⇒ **MUST NOT** 把类型空值改写成 `None` ⇒ ⇒ ⇒ **覆盖型（无归约器）**通道
  未写 ⇒ **缺席** ⇒ ⇒ ⇒ ⇒ 才是本条「填 `None`」的唯一适用面。
  ⚠️ **返回值是「只读快照」**：MUST **NOT** 把返回值**原样回喂**给下一次 `invoke`
  （回喂会把 `None` **真的写进**通道 ⇒ 节点里 `state.get("llm_calls", 0) + 1` 这类写法会
  `TypeError`）⇒ ⇒ 该禁令 MUST 在**用户可见文档**（`invoke` 的 docstring + README）里写明
  **并写明理由** ⇒ ⇒ ⚠️ 本条**只约束返回值**；MUST **NOT** 影响「用户显式传入 `None` 作为
  初始值」的写入语义（`{"x": None}` 仍 MUST 被写进通道 · 与上游同款）。
- **FR-010**：归约型 key（带二元归约器）的返回值 MUST 是「**初始值 + 全部新增值**」的合并结果
  ⇒ ⇒ MUST **NOT** 只返回增量。
- **FR-011**：**无归约器**的 key MUST 是**覆盖**后的最终值 ⇒ ⇒ MUST **NOT** 累加。
- **FR-012**：schema key 集合 MUST 由编译产物持有的**图规格通道表扣除路由型通道**得出；
  路由型通道的判定 MUST 沿用 **B7F1 的冻结口径**（`isinstance(channel, EphemeralValue)`）
  ⇒ ⇒ MUST **NOT** 用「名称前缀」之类启发式 ⇒ ⇒ MUST **NOT** 依赖「节点订阅集」
  ⇒ ⇒ MUST **NOT** 新增 / 删除编译产物的私有字段。
- **FR-013**：`input` MUST 接受**部分**状态（只含需要初始化的 key）⇒ ⇒ MUST 按**通道语义**
  写入初始值（带归约器 ⇒ **归约**；无归约器 ⇒ **覆盖**）⇒ ⇒ MUST **NOT** 另写一条写入路径
  ⇒ ⇒ 初始输入含 schema 之外的 key ⇒ 沿用 L2 既有口径（`InvalidUpdateError`）。
- **FR-014**：挂起时 MUST 走 **`InterruptResult.as_result_dict()` 这唯一转成路径**
  （即由它产出 `"__interrupt__"` 键 ⇒ `{**state, "__interrupt__": interrupts}`）
  ⇒ ⇒ **再**按 FR-008 补齐无值 key（**保留**该键 ⇒ 最终键集 == schema 全集 **+** `__interrupt__`）
  ⇒ ⇒ 静态挂起 MUST 走**同一条**路径（`"__interrupt__": ()`）⇒ ⇒ **无**挂起时
  MUST **NOT** 含该键 ⇒ ⇒ MUST **NOT** 另写一条「静态中断 → 结果键」的转成路径。
  ⚠️ **2026-11-16 plan 阶段回修（S-2）**：该方法的 `.state` 是**稀疏**（`superstep.py:406-418`
  + `:1334-1336`）⇒ 若**逐字**返回它 ⇒ 挂起路径的键集 ≠ schema 全集 ⇒ 与 FR-008 冲突 ⇒ ⇒ ⇒
  故「**转成路径只此一条**」指的是「**产出 `__interrupt__` 键的那一步**」，而「**补齐**」是其**之后**的
  **独立一步**、对两条路径**同款** ⇒ ⇒ ⇒ 「补齐」MUST 是**一个**实现点（下游承接 **D-1**）。
- **FR-015**：`input` MUST 接受 `Command` 与 `None` ⇒ ⇒ 恢复路径的判定 MUST **逐字**按
  **B10F1 的 FR-013 的表**、依 **B10F1 的裁定 4 的判定顺序** ⇒ ⇒ MUST **NOT** 在本 feature 的
  文档 / 实现里**另抄一份**判定表 ⇒ ⇒ 「节点返回 `Command`」与「`Command` 作为图输入」
  MUST **NOT** 混为一条。

#### C · 失败信号与错误传播

- **FR-016**：节点返回**未知 key** 时 MUST 抛 `InvalidUpdateError`（L1 契约层已冻结）
  ⇒ ⇒ 异常消息 MUST **指明违规 key**（MUST 含该 key 名；多个未知 key ⇒ 含**全部**）
  ⇒ ⇒ 异常 MUST **原样**到达调用方。
- **FR-017**：节点内部抛出的异常 MUST 以**原始类型与原始消息**传播 ⇒ ⇒ MUST **NOT** 包装
  （如包成 `RuntimeError`）⇒ ⇒ MUST **NOT** 吞掉 ⇒ ⇒ MUST **NOT** 返回部分结果。
- **FR-018**：`GraphRecursionError` MUST **原样**传播 ⇒ ⇒ MUST **NOT** 包装成别的类型。
- **FR-019**：`InterruptError`（恢复失败：未挂 checkpointer / 未提供恢复值 / 多挂起歧义 /
  无挂起中断）MUST **原样**传播 ⇒ ⇒ MUST **NOT** 把「未挂 checkpointer 时提交
  `Command(resume=...)`」**静默降级**为内存态恢复。
- **FR-020**：`GraphInterrupt` 若仍从 L2 抛出，MUST **原样**抛出（MUST **NOT** 吞掉、
  MUST **NOT** 假装图跑完了）。

#### D · 配置与运行期旋钮

- **FR-021**：`config` MUST 同时接受 `RunConfig` 实例与普通映射 ⇒ ⇒ 运行期参数 MUST
  **原样**交给 L2 ⇒ ⇒ MUST **NOT** 丢弃 / 改名 / 另写解析路径 ⇒ ⇒ MUST **NOT** 在门面层
  把普通映射**翻译**成 `RunConfig` ⇒ ⇒ `RunConfig` MUST **零改动**（本 feature **MUST NOT**
  扩字段）⇒ ⇒ ⚠️ L1 协议的 `config` 注解 MUST 与之一致（`RunConfig | Mapping[str, Any] | None`
  · 裁定 1 · **破 L1 冻结面**）⇒ ⇒ ⇒ ⚠️ 普通映射里的**未知键 MUST 被宽容忽略**
  （L2 的 `resolve_config` 用 `RunConfig.from_dict(..., ignore_unknown=True)` ·
  `runtime/_recursion.py:44`）⇒ ⇒ 与上游同款（上游的 `RunnableConfig` 也是「只挑认识的键」）。
- **FR-022**：`recursion_limit` MUST 能以**普通映射**形态生效（`{"recursion_limit": N}`）
  ⇒ ⇒ 超限时 MUST 抛 `GraphRecursionError` ⇒ ⇒ `harness/demo/graph_core.py` 的 A8 组
  硬断言 MUST **真跑通过**。
- **FR-023**：`max_concurrency` MUST 以 `RunConfig` 字段暴露（**同名同义**）并生效
  ⇒ ⇒ ⚠️ **`None` ≡ 未指定**（2026-11-16 analyse 轮 · **D-B 决策** · **本 feature 的唯一口径**）：
  `run_graph` 的**关键字**为 `None`（**未传**或**显式 `None`** · 二者**不可区分** ⇒
  门面的 `invoke` **恒不传**该关键字）**或** `config.max_concurrency` 为 `None`
  ⇒ ⇒ ⇒ 并发度上限 = `min(32, cpu+4)`；显式 `N` ⇒ 实际并发度 =
  `min(本轮任务数, N)`（**N 不被 32 再夹**）；`N = 1` ⇒ **串行基线**；非法取值 MUST
  **入口即**显式失败（类型不符 ⇒ 内置 `TypeError`；`< 1` ⇒ 内置 `ValueError`；
  两者均**点名该参数**）⇒ ⇒ MUST **NOT** 另写一份校验。
  ⇒ ⇒ ⚠️ **「关键字优先」的精确含义** = 「关键字**非 `None`** 时用关键字值；**为 `None`** 时
  **一律回落到 `config.max_concurrency`**」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **不存在**「显式 `None` 覆盖 config」的第三种语义。
  ⚠️ **2026-11-16 clarify 轮 · 用户拍板（Q2 = 选项 B）**：**读取点落在 L2** ——
  `run_graph` MUST 在**关键字缺省时**回落到 `config.max_concurrency`（**关键字优先**）
  ⇒ ⇒ **兼容扩展**（既有调用方零改动 · 关键字的失败顺序**逐字不变**）⇒ ⇒ ⇒ MUST
  **回溯修订** B10F1 的 `run_graph` 契约 + B12F1 的旋钮口径（见破冻结面 **T-3**）
  ⇒ ⇒ ⇒ **门面层 MUST NOT** 另写一份搬运逻辑。
  ⚠️ **校验时机与失败顺序（2026-11-16 analyse 轮 · 补齐）**：L2 的既有顺序 = **关键字**值的
  `_validate_max_concurrency` → `resolve_config(config)`（`superstep.py:1964-1967`）⇒ ⇒ ⇒ **config 兜底值**
  只能在 `resolve_config` **之后**读到 ⇒ ⇒ ⇒ ⇒ **config 兜底值的校验点 = `resolve_config` 之后、
  `_first_graph` 之前** ⇒ ⇒ ⇒ ⇒ **失败信号与关键字形态同款**（类型不符 ⇒ 内置 `TypeError`；
  `< 1` ⇒ 内置 `ValueError`；两者均**点名该参数**）⇒ ⇒ ⇒ ⇒ ⚠️ **与关键字形态的失败先后不同**
  （关键字形态在 `resolve_config` **之前**失败 ⇒ 既有顺序**逐字不变**）⇒ ⇒ ⇒ ⇒ ⚠️ `RunConfig.from_dict`
  **不校验**该字段（`types.py:248-276`）⇒ ⇒ ⇒ ⇒ 故 `{"max_concurrency": 0}` 在本 feature **之前完全静默**
  ⇒ ⇒ ⇒ ⇒ 本条是它的**唯一**失败信号。

#### E · 结构与边界

- **FR-024**：MUST **NOT** import `langchain` / `langchain-core` / `langgraph*` / `langsmith`
  / 任何第三方包 ⇒ ⇒ MUST **NOT** 读任何环境变量 ⇒ ⇒ MUST **NOT** 有任何出站。
- **FR-025**：节点入参 MUST **原样**沿用 L2 的稀疏读口径（入参 == `read_channels(子映射)`，
  子映射按**通道映射的顺序**构造）⇒ ⇒ MUST **NOT** 改写 key 顺序 ⇒ ⇒ 「无值 key 填 `None`」
  的口径 MUST **NOT** 泄漏到**节点入参**（C4：入参**仍稀疏** ⇒ `state.get(k, default)`
  仍返回 `default`）。
- **FR-026**：本 feature MUST **NOT** 实现 —— ① **L1 六方法协议里**的其余 **5** 个能力面方法：
  `stream()`（B8F2）· `get_graph()`（B22F1）· `get_state()` / `get_state_history()`（B15F1）·
  `update_state()`（B16F1）⇒ ⇒ 它们 MUST 继续抛内置 `NotImplementedError` 且消息**点名归属 feature**；
  ② **非协议面**的能力：`ainvoke()`（v2）· `draw_mermaid_png()`（B23F1 · 挂在 `Graph` 上）·
  checkpoint 落盘（B14F1）· 条件边**路由求值**（B8F1）· 节点返回 `Command` 的处理（B9F1 · L2 已交付）。
  ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · L4 措辞订正**：初版把 ①② 混列于同一句 ⇒ ⇒ ⇒ 易被读成「要从 6 方法协议里摘掉 5 个」⇒ ⇒ ⇒ ⇒ **已拆分**（① 协议面 · ② 非协议面）。
- **FR-027**：G22「场景 ②」的最小图**运行期**断言 MUST 在本 feature 交付并点亮
  （建图 → 编译 → 执行闭环）⇒ ⇒ **只接线 · MUST NOT 新增门禁编号** ⇒ ⇒ 红线**不放宽**。
  ⚠️ **消歧（2026-11-16）**：**G22 = 隔离环境门禁**（依赖闭包为空集 + `sys.modules` 无
  langchain 家族）⇒ 其「**场景 ②**」= **验收环境**（`langchain-core` 在场时 freegraph
  仍不碰它）⇒ ⇒ ⇒ **③② 运行期（最小图）那一半**才是本 feature 的义务
  （门禁契约 `architecture-gates.md:128-130` 与 `gate_G22_isolated_env.py:22-23`
  **指名 B7F3** 承接）⇒ ⇒ ⇒ 落点：**改 `harness/scripts/gates/gate_G22_isolated_env.py`
  的**步骤 6（③②）**，**MUST NOT** 新增门禁编号 ⇒ ⇒ ⇒ **其反向用例 MUST 同步能失败**。
- **FR-028**：本 feature MUST **NOT** 破 B7F2 的编译产物持有面（3 私有 + 8 公开）
  ⇒ ⇒ `vars(compiled)` 的键数 MUST 仍 == **11** ⇒ ⇒ MUST **NOT** 改 `target.py`
  （只读基准的 diff 断言常驻）。

### Key Entities

- **`invoke` 结果字典**：本 feature 的主交付物 —— 一个**普通 `dict`**，键集 == schema 全键
  （顺序 = schema 声明顺序），值为合并后的最终状态；**覆盖型（无归约器）**的**无值** key 以 `None` 补齐
  （**归约型**的**无值** key = **类型空值** · 契约 R-06）；
  **挂起**时额外含 `"__interrupt__"`（值为中断载荷**元组**）。
- **`__interrupt__` 键**：挂起态的唯一载体（**上游同名**）· 值 = `Interrupt` 序列
  （freegraph = **tuple**）· **无挂起时不出现**。
- **初始状态**：`invoke` 的第一个位置参数 —— 状态 schema 的**部分**键值对；
  按通道语义写入（归约 / 覆盖）· 亦可接受 `Command`（恢复）与 `None`（会话连续）。
- **运行期配置**：第二个位置参数 —— `RunConfig`（会话面 + `max_concurrency`）
  或普通映射（运行期参数，如 `recursion_limit`）· **原样**交给 L2。
- **完整状态**：schema 全部 key 的**合并后取值**（初始 + 全部新增）· 相对「增量」的对照概念。
- **`InvalidUpdateError`**：未知 key 写入异常（L1 已冻结）· 带 `invalid_keys` 结构化属性 ·
  消息点名违规 key。

### Out of Scope

- `stream()` 与 `ainvoke()`（B8F2 / v2）—— 本 feature 只交付**同步**执行入口。
- 条件边**路由求值**（B8F1）—— 本 feature 只保证**静态边**路径可跑通；
  条件边路径由 B8F1 在同一执行路径上补齐。
- `get_graph()`（B22F1）/ `draw_mermaid_png()`（B23F1）—— **必须先于**本 feature 就绪
  （只读基准脚本的调用顺序）· 本 feature **不**越界实现。
- checkpoint **落盘**与任何 saver 实现（B14F1 / B15F1）—— 本 feature 只**透传** `checkpointer`。
- `get_state()` / `get_state_history()`（B15F1）/ `update_state()`（B16F1）。
- 节点返回 `Command` 的处理（B9F1 · L2 已交付）· 本 feature 只驱动。
- 图结构导出（`draw_mermaid` 文本 / PNG 渲染）—— 归 B22F1 / B23F1。
- 可观测层（trace / span / 本地可视化）—— 归 L5 与 v2。
- 「**无值 key 填 `None`**」的口径**推广到 `stream()`**（B8F2 · 下游承接 D-1）。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：**键集相等**断言通过率 == **100%** —— 对每个用例，`invoke` 返回的键集
  **逐字等于** schema 的全部 key 集合（顺序一致）⇒ 出现「漏 key」或「多 key」的用例数 == **0**
  ⇒ ⇒ ⚠️ **挂起用例**的「期望键集」= schema 全集 **+** `"__interrupt__"`（**挂起键**）
  ⇒ ⇒ ⇒ ⇒ ⇒ **非挂起**用例的期望键集 == schema 全集
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 「多 key」的计数**排除**挂起键（**非挂起**用例里多出任何 key ⇒ 计数 == 0）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **不放松**（**D-C 决策** · 判据零放宽）。
- **SC-002**：`messages`（归约型）的返回长度 == **初始条数 + 全部新增条数**的比例 == **100%**
  （逐用例逐字断言）。
- **SC-003**：`llm_calls`（无归约器）的返回值 == **最后一次写入值**的比例 == **100%**
  （不是累加）⇒ 且**从未被写的覆盖型（无归约器）**key 在返回字典里的值 == `None` 的用例数 == 全部此类用例。
  ⚠️ **归约型 key 的例外（2026-11-16 analyse 轮 · 消歧）**：**从未被写**的**归约型**key 的返回值 ==
  **类型空值**（`list` → `[]` · `int` → `0`）⇒ ⇒ **不是** `None` ⇒ ⇒ ⇒ 「值 == `None`」这条只对
  **覆盖型**key 成立（契约 R-06 · data-model §2.3）⇒ ⇒ ⇒ **MUST NOT** 把类型空值改写成 `None`。
- **SC-004**：未知 key 用例中抛出 `InvalidUpdateError` 且消息**含违规 key 名**的比例 == **100%**
  ⇒ 未知 key 被**静默忽略**的用例数 == **0**。
- **SC-005**：节点抛出真异常时，以**原始类型与原始消息**到达调用方的比例 == **100%**
  ⇒ 被**包装**成别的类型的次数 == **0**。
- **SC-006**：`config` 的两种形态（`RunConfig` / 普通映射）均被接受且**生效**的比例 == **100%**
  ⇒ `max_concurrency=1`（串行档）与并发档的最终状态**逐字相等**。
  ⚠️ **并发度旋钮的「生效」判据（2026-11-16 analyse 轮 · 修订）**：**最终状态逐字相等**这条**无法**判定
  旋钮是否生效（最终状态与并发度**无关** ⇒ 旋钮被静默忽略时该断言**照样通过**）⇒ ⇒ ⇒ **MUST** 另有一条
  **可观测并发度**断言：两个并发节点各自记录「同时在飞」的重叠计数 ⇒ ⇒ `max_concurrency=1` ⇒ 重叠计数
  == **0**（**串行基线**）· 缺省档（`None` ⇒ `min(32, cpu+4)`）⇒ 重叠计数 **≥ 1** ⇒ ⇒ ⇒ ⇒ 旋钮被忽略 ⇒
  缺省档仍**不重叠** ⇒ ⇒ ⇒ ⇒ 该断言**必红** ⇒ ⇒ ⇒ ⇒ 判据 = 「**可观测并发度**」**AND** 「最终状态逐字相等」。
  ⚠️ **「可观测并发度」的测量 MUST 是确定性的（2026-11-16 analyse 轮 · 补齐）**：重叠 MUST 由
  **同步手段**（如 `threading.Event` / `Barrier` 互等到齐）构造 ⇒ ⇒ ⇒ **MUST NOT** 依赖「时间流逝」
  （⇒ ⇒ CI 慢档 / Windows 档会假红 —— 仓库已有一次「时序测量假红」的修复史）⇒ ⇒ ⇒ ⇒ `max_concurrency=1`
  档的「等不到对端」MUST 以**超时兜底**（⇒ ⇒ 超时**不**判失败 · 串行**正是**期望）⇒ ⇒ ⇒ ⇒ ⇒ 判据数值**一字不改**。
- **SC-007**：`{"recursion_limit": N}` 生效且超限抛 `GraphRecursionError`（**类型不被包装**）
  的比例 == **100%** ⇒ `harness/demo/graph_core.py` 的 A8 组**真跑通过**。
- **SC-008**：同一张编译图**连续两次**调用的结果**互不累积**的用例数 == 全部此类用例
  （第二次的结果**不含**第一次的新增）⇒ ⇒ ⇒ **且路由型通道的值 MUST NOT 残留到下一次调用**
  （**步末清空**口径 · FR-006 / 裁定 11 ⇒ ⇒ **该子句此前无专门用例** ⇒ ⇒ 2026-11-16 analyse 轮 · 第三轮回修 · **FND-B7** 补入 ⇒ ⇒ **判据只可更严**）。
- **SC-009**：同一张编译图**并发两次**调用的结果**互不串扰**的用例数 == 全部此类用例。
- **SC-010**：挂起结果的 `"__interrupt__"` 键**存在**且其元素具备 `.value` 与 `.id`；
  **无挂起**时该键出现次数 == **0**；恢复后被中断节点**从头重跑**且拿到恢复值。
  ⚠️ **恢复路径的载体（2026-11-16 analyse 轮 · 第三轮回修 · FND-A4）**：**「恢复后拿到恢复值」这一半 MUST 有 checkpointer**
  ⇒ ⇒ ⇒ 本 feature 的 `src/freegraph/**` 内**零** saver 实现（`MemorySaver` 归 **B14F1** · 宪法原则 IV「MUST NOT 提供『不挂 checkpointer 也能恢复』的内存态旁路」）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **载体 = 测试侧的「自足桩 checkpointer」**（tasks **T002** 交付 · 形态参照 `tests/differential/parity_probe.py:251-255`）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据不放宽**（硬判据 · **MUST NOT** 因「无载体」降级为 soft）
  ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ 仓库既有验收脚本（`graph_core.py:392-393` · `agent_loop.py:275-280`）把该路径定为 **soft** 且注「载体待 **B14F1** 锁定」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **那是验收脚本的既有写法 · 与本 SC 的硬判据不冲突**（脚本 = 载体级验收 · 本 SC = 单测级判据）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **两者 MUST NOT 混为一条**。
- **SC-011**：`invoke` 全过程的**出站连接数 == 0**；**环境变量读取次数 == 0**
  （含 `LANGSMITH_*`）。
- **SC-012**：`invoke` 全过程 `sys.modules` 中 `langchain` / `langchain_core` /
  `langgraph` / `langsmith` 的**出现次数 == 0**。
- **SC-013**：`invoke` 驱动整张图到**终止**（执行序列覆盖全部可达节点）的比例 == **100%**
  ⇒ ⇒ **含「多源汇合（屏障）」半边**：屏障目标 MUST 在**所有**源跑完后才出现
  （**静态多源边** · `add_edge([a, b], c)` · **B7F4 已交付于 L2** · `superstep.py:671/747/1000-1007`
  ⇒ ⚠️ **不依赖 B8F1 的条件边路由** ⇒ 实测 `executed == ('a','b','c')`）⇒ ⇒ ⇒ **物理可达**
  ⇒ ⇒ ⇒ ⇒ **由本 feature 判定**（比例 == **100%**）⇒ ⇒ ⇒ ⇒ 差分 **D-102** 锁住（判词 **SAME**）
  ⇒ ⇒ ⇒ ⇒ ⚠️ **条件边路由**（`add_conditional_edges` 的**求值**）**仍属 B8F1**（FR-026 · Out of Scope）
  ⇒ ⇒ ⇒ ⇒ 该能力**尚未交付**（**不是**推迟 · **不是**「物理不可达成」）⇒ ⇒ ⇒ ⇒
  ⇒ ⇒ ⚠️ **EV-3 已撤销**（2026-11-16 analyse 轮）—— 原 EV-3 把本半边判为「依赖 B8F1 ⇒ 物理不可达成」
  ⇒ ⇒ ⇒ ⇒ **根因判断有误**（屏障 = 静态多源边 · 非条件边路由）⇒ ⇒ ⇒ ⇒ **违反宪法 v1.6.0
  「分阶段落地」的窄口径**（适用范围两要件之「物理不可达成」不成立）⇒ ⇒ ⇒ ⇒ **判据不放宽** ⇒ 恢复整条判定。
- **SC-014**：G22「场景 ②」的最小图**运行期**断言被点亮（断言数 ≥ **1**）⇒ 且
  **零新增**门禁编号。
- **SC-015**：`invoke` 在任何合法路径上抛 `NotImplementedError` 的次数 == **0**
  ⇒ `harness/demo/graph_core.py` 的就绪探针返回「已就绪」⇒ 该脚本**不再**以退出码 2 结束。
- **SC-016**：`vars(compiled)` 的键数仍 == **11**（未新增编译产物私有字段）的比例 == **100%**。
- **SC-017**：差分场景组 **D-92…D-102** 全绿（上游缺席即 `skip`）⇒ 判词分布与
  §差分场景组表的**逐条一致**（**SAME 7 / STRICTER 3 / DIFF 1** —— ⚠️ **这是「差分场景组」的分布**，
  **不是** §Upstream Parity 对照表的分布；后者 = **SAME 6 / STRICTER 3 / DIFF 5**（P-01/P-02/P-06/
  P-10/P-11/P-13 SAME · P-07/P-08/P-09/P-12/P-14 DIFF））⇒ **STRICTER** 的三条
  各自带 `note`。
- **SC-018**：人工验证记录覆盖「**fake 模型轮** + **真实模型轮**」两轮的**实测输出**
  （覆盖比例 == **100%**）⇒ ⇒ 「本 feature 未跑固定脚本」**不得**被写成「本 feature 未验证」。
  ⚠️ **两轮的定义（2026-11-16 analyse 轮 · 消歧）**：**「fake 模型轮」** = 用**假模型**（猴补
  `init_chat_model` · 立项书 §9.2）+ **本 feature 可跑的最小图**跑一轮并记录**实测输出**
  （**静态边**部分**真跑**）· **「真实模型轮」** = 用**真实模型**（`claude-sonnet-4-6`）+
  **最小真实模型图**（1 个节点调用真实模型）跑一轮并记录**实测输出**（**用户出站** · 不判失败 ·
  **框架零出站**断言仍须通过）⇒ ⇒ ⇒ ⇒ ⚠️ **固定脚本的端到端轮**（`target.py` 跑通）**不属**本 feature 的
  达成范围 ⇒ ⇒ ⇒ ⇒ 它需 **B8F1 + B22F1 + B23F1** ⇒ ⇒ ⇒ ⇒ ⇒ **登记为 EV-4**（分阶段落地 · 具名承接）⇒ ⇒ ⇒ ⇒ ⇒
  ⇒ ⚠️ **若真实轮因环境不具备（无模型凭据 / 无外网）而无法完成** ⇒ ⇒ MUST 按宪法 v1.6.0 登记为
  **环境偏离**并在人工验证记录中写明（**MUST NOT** 用「未验证」替代「已登记的环境偏离」）
  ⇒ ⇒ ⚠️ **判据本身不放宽**（fake 模型轮仍 MUST 跑通）。
  ⚠️ **判据级覆盖（2026-11-16 analyse 轮 · 补齐）**：本 SC **MUST** 挂一条**能判定它**的任务 ⇒ ⇒
  **「写记录」本身不构成判定覆盖**（宪法原则 VI v1.11.0 + v1.13.0 的「人工门禁类 SC」条款）⇒ ⇒ ⇒ ⇒
  ⇒ 判定载体 = **可自动核验的文档守卫断言**（断言 `harness/verification/B7F3/manual-verification.md`
  存在且含**两轮实测输出**的**非空**正文）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 该守卫 MUST 在记录写就之后才转绿
  （⇒ ⇒ **MUST NOT** 造成「永久红的 CI」）。
- **SC-019**：破冻结面的**唯一一次**发起者追认（L1 协议 `invoke` 的 **`input`** 与
  **`config`** 两处注解放宽 —— **同一次**登记 / 回溯修订 / 追认）在
  `harness/verification/B7F3/manual-verification.md` 留痕 ⇒ ⇒ 合入前**追认完成率 == 100%**。
- **SC-020**：**用户可见文档**（编译产物 `invoke` 的 docstring + README）MUST 写明
  「返回值是只读快照、**不要原样回喂**给下一次 `invoke`」**及其理由**
  （回喂会把补齐的 `None` 写进通道 ⇒ 节点里 `state.get(k, 0) + 1` 会报错）⇒ ⇒
  该文字在文档中的**出现次数 ≥ 1**（可由文档断言判定）⇒ ⇒ 另 MUST 有一条**用例**断言
  「用户显式传入 `None` 作为初始值**仍被写进通道**」（证明禁令只约束返回值、不改写入语义）。

### 追溯表（FR → SC）

| FR | SC |
|---|---|
| FR-001 | SC-015 · SC-013 |
| FR-002 | SC-008 · SC-009 · SC-013 |
| FR-003 | SC-013 |
| FR-004 | SC-008 · SC-009 |
| FR-005 | SC-008 · SC-009 |
| FR-006 | SC-001 · SC-008 |
| FR-007 | SC-001 |
| FR-008 | SC-001 · SC-003 |
| FR-009 | SC-003 · SC-020 |
| FR-010 | SC-002 |
| FR-011 | SC-003 |
| FR-012 | SC-001 · SC-016 |
| FR-013 | SC-003 · SC-004（⚠️ **2026-11-16 analyse 轮第五轮补齐**：FR-013 含「**初始输入含 schema 之外的 key** ⇒ `InvalidUpdateError`」半边 ⇒ ⇒ 该半边由 **SC-004** 判定（tasks T022④）⇒ ⇒ ⇒ 原追溯行**只挂 SC-003**（覆盖语义）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **补挂 SC-004** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽**）|
| FR-014 | SC-010 |
| FR-015 | SC-010 |
| FR-016 | SC-004 |
| FR-017 | SC-005 |
| FR-018 | SC-007 |
| FR-019 | SC-010 |
| FR-020 | SC-005（**兜底分支** · 与 **FR-017** 同一判定任务 **T023** · 正常路径**不触达**（B10F1 已把中断转成 `InterruptResult`）⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · M4 订正**：SC-005 的判据是「**节点抛出真异常**」⇒ ⇒ ⇒ ⇒ **不覆盖** FR-020 的「L2 抛 `GraphInterrupt`」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **归并**到 FR-017 的判定任务 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 另立 SC（避免扩大追认面）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ |
| FR-021 | SC-006 · SC-007 |
| FR-022 | SC-007 |
| FR-023 | SC-006 |
| FR-024 | SC-011 · SC-012 |
| FR-025 | SC-002 |
| FR-026 | SC-015 |
| FR-027 | SC-014 |
| FR-028 | SC-016 |
| （全局） | SC-017 · SC-018 · SC-019 |

---

## Assumptions

- **上游版本钉死**：`langgraph` **1.2.11** + `langchain-core` **1.7.6**
  （取证于 2026-11-16 · 本仓库 `.venv` 的实际安装版本）⇒ 换版本时 MUST 重新核实全部锚点
  并改写版本号（原则 XI「照抄的三条纪律」③）。
- **「上游实测」的取证方式**：本 spec 的 P-03 / P-04 / P-05 / P-06 的行为断言由**沙箱实测**
  得出（`langgraph 1.2.11` 的真实 `StateGraph` + `invoke`）⇒ plan / tasks 阶段 MUST 把这些
  实测**固化成差分探针场景**（D-92…D-102 · **11 条**）⇒ 上游缺席即 `skip`。
- **「schema 全部 key」的含义**：状态 schema **声明**的全部 key（**不含**内核内部通道：
  路由通道 `branch:to:*`、保留通道名等）⇒ 本 feature MUST NOT 让内部通道泄漏到返回值。
- **「完整状态」≠「节点入参」**：节点入参**仍稀疏**（C4）⇒ 「无值 key 填 `None`」只作用于
  `invoke` 的**返回值**。
- **「无值」的判定**：freegraph 的通道**无**「有无值」与「值为 `None`」的区分
  ⇒ 返回值里「从未被写」与「被写成 `None`」在**值上**不可区分（上游同款：`None` ≠ `MISSING`）。
- **`RunConfig` 现状**：**9 个字段**（`types.py:169-219`）· 已含 `max_concurrency` 与
  `recursion_limit` ⇒ 本 feature **零改动** L1 的 `RunConfig` ⇒ 提示词初稿的
  「仍为 4 个字段」**已过期**（引文差异 1）。
- **L1 冻结面**：本 feature 的破面 = L1 `CompiledGraph.invoke` 的 **`input`** 与 **`config`**
  **两处**注解放宽（裁定 1 + clarify 轮）⇒ ⇒ 两处**同属一次**登记 + 回溯修订 + 发起者追认
  ⇒ ⇒ **追认额度（≤ 1 次）用尽于此** ⇒ ⇒ ⇒ B7F2 的编译产物持有面**不破**。
  ⚠️ **2026-11-16 plan 阶段回修（S-3）**：初版此处只写「唯一破面 = `input` 注解放宽」⇒ 已过期。
  ⚠️ **2026-11-16 analyse 轮补记（**破面全集**）**：**唯一一次**追认覆盖的破面共 **5 类**
  ⇒ ⇒ ① L1 `invoke` 的 **`input`** 注解 ② L1 `invoke` 的 **`config`** 注解
  ③ L2 `run_graph` 的 **`max_concurrency` 读取点**（兼容扩展）
  ④ **G19**「既有契约层矩阵行逐字未改」判据（**新增** `MATRIX_ROWS_UPDATABLE_BY_B7F3`
  白名单 · 只放行 `CompiledGraph` 一行）
  ⑤ **四处**「invoke 未就绪」冻结断言的拆分替换
  ⇒ ⇒ ⇒ ⇒ **全部落在同一次登记 + 回溯修订 + 发起者追认里**（追认次数 == **1**）
  ⇒ ⇒ ⇒ ⇒ **MUST NOT** 再破任何其它冻结面。
- ⚠️ **上位文档待修订清单**（2026-11-16 analyse 轮 · **D-D 决策** · 本 feature **不**单方面改立项书）：
  ① **立项书 §5.2** 的 **B7F3 层标注**（「L2 执行内核」⇒ 实际落 **L3**）
  ② **立项书 §5.3.1** 的 **C22 行**（`RunConfig` 字段清单「4 个」⇒ 仓库现状 **9 个**）
  ③ **立项书 §5.2** 的 **B7F3 行数口径**（980 行 ⇒ 本 feature 估 **≈1,180** · PR-1）
  ⇒ ⇒ ⇒ 三项均属**发起者职权**（沿用 B7F2 的既有惯例 · **不假托宪法**）⇒ ⇒ ⇒ 本 feature 以**仓库现状**为准。
- **`checkpointer` 的语义**：本 feature 只**透传**（B14F1 负责落盘与 saver 实现）⇒ ⇒
  「未挂 checkpointer 时提交 `Command(resume=...)`」的失败信号由 **L2 的既有口径**承担。
- **层归属的知情说明**（2026-11-16 clarify 轮 · 用户拍板 · Q1 = 选项 B）：立项书 §5.2 把
  **B7F3 标为「L2 执行内核」**，而本 feature 的实现**必须**在 **L3**
  （`CompiledGraph.invoke` 住在 `src/freegraph/_stategraph.py`）⇒ ⇒ 若下沉到 L2 ⇒
  **L2 → L3 反向依赖** ⇒ 违反 **ARCH-1 / G25** ⇒ ⇒ ⇒ **层归属以层注册表 + G25 为准**
  ⇒ ⇒ ⇒ **本 feature 不单方面修订立项书**（**依据 = 仓库既有惯例**（B7F2 的 plan 同款措辞「不单方面改上位文档数字」）＋ **立项口径属发起者批准**；⚠️ 宪法 v1.12.0 **并无**此 MUST ⇒ ⇒ 不假托宪法）、**不**登记偏离 ⇒ ⇒ ⇒ ⚠️ 与立项书 §5.2 的层标注
  **不一致**属**已知且刻意**的状态（上位文档的修订属**发起者**职权）。
- **`max_concurrency` 的归属**（2026-11-16 clarify 轮 · 用户拍板 · Q2 = 选项 B）：旋钮的
  **读取点下沉到 L2**（`run_graph` 关键字优先 · `config` 兜底）⇒ ⇒ **兼容扩展**
  （既有调用方零改动）⇒ ⇒ ⇒ 门面层**零搬运逻辑**。
- **只读基准脚本**：`harness/demo/target.py` **MUST NOT** 被改动（门禁 3 的 diff 断言）
  ⇒ ⇒ 本 feature 的验收证据落在 `harness/demo/graph_core.py`（可改的**前置用例**脚本）
  + `harness/demo/agent_loop.py`（零依赖镜像）+ 人工验证记录。
- **就绪顺序的依赖**：`get_graph` / `draw_mermaid_png`（B22F1 / B23F1）**先于**本 feature
  就绪 ⇒ 若二者未就绪，只读基准脚本会在到达 `invoke` 之前中断 ⇒ ⇒ 这是**排期约束**，
  不是本 feature 的实现义务（下游承接 D-3）。
- **人工验证的两轮**（2026-11-16 analyse 轮 · 消歧）：「fake 模型轮」= 猴补 `init_chat_model`
  注入（立项书 §9.2）+ **本 feature 可跑的最小图**（**静态边**部分**真跑**）；「真实模型轮」=
  `claude-sonnet-4-6` + **最小真实模型图**（1 个节点调用真实模型）⇒ ⇒ 本 feature MUST 在
  `harness/verification/B7F3/manual-verification.md` 补上两轮的**实测输出**
  ⇒ ⇒ 「真实模型轮」的出网属**用户出站**，不判失败，但**框架零出站**断言仍须通过
  ⇒ ⇒ ⚠️ **固定脚本的端到端轮**（`target.py` 跑通）**不属**本 feature 的达成范围
  （需 **B8F1 + B22F1 + B23F1**）⇒ ⇒ 登记为 **EV-4**（分阶段落地 · 具名承接）
  ⇒ ⇒ ⚠️ 若真实轮因**环境不具备**（无凭据 / 无外网）而无法完成 ⇒ MUST 登记为**环境偏离**
  ⇒ ⇒ ⇒ **判据本身不放宽**（fake 轮仍 MUST 跑通）
  ⇒ ⇒ ⚠️ **判据级覆盖**：本条 MUST 由**可自动核验的文档守卫断言**判定
  （宪法原则 VI v1.11.0 + v1.13.0 的「人工门禁类 SC」条款）⇒ ⇒ 「写记录」**不**构成判定覆盖。
