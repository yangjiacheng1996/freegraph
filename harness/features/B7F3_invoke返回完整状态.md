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
- **承接条款（B7F1 → B7F3 · M2 · 调度契约的跨 feature 接口）**：B7F1 已交付**调度内核**
  并**冻结**了跨 feature 的接口口径 ⇒ **本 feature MUST** 照它写：
  - **调度状态口径**（裁定 27）：`run_super_steps(spec, state=None, *, max_steps=25)` 的
    `state` **MAY 省略**（缺省新建一个）⇒ 本 feature **MUST NOT** 依赖「调用方复用同一个
    调度状态」⇒ **每次 `invoke` 内部自洽**（否则两次 `invoke` 的「已消费版本」会串扰）；
  - **节点入参口径**（裁定 26）：入参 MUST 等于 `read_channels(子映射)` 的结果，子映射 MUST
    按「**通道映射的顺序**」构造 ⇒ **本 feature MUST NOT** 改写 key 顺序
    （同一张状态表在不同节点处的 key 顺序 MUST 一致）；
  - **返回值口径**：`invoke` MUST 返回**完整状态**（全部 schema key）⇒ **本 feature MUST**
    照 B7F1 的 `SuperStepResult.state`（**稀疏**通道状态）**取稀疏视图**后**补齐**无值 key，
    MUST NOT 因「无值」而漏 key（C11 的硬要求）；
  - **步末清空口径**（裁定 33）：单轮入口与多轮入口**都**执行步末清空 ⇒ **本 feature MUST
    NOT** 假设「路由型通道的值会残留到下一次 `invoke`」。
  该口径由 B7F1 的 `specs/b7f1-superstep-loop/spec.md`（FR-001 / FR-008 / FR-014 / 裁定 26 /
  裁定 27 / 裁定 33）落成 · 契约见
  `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §3.2 / §5.2 / §5.3。

- **承接条款（B12F1 → B7F3 · M2 · 多会话隔离的「每次调用新建实例」口径）**：B12F1 已交付**并发执行
  内核**并**冻结**了跨 feature 的接口口径 ⇒ **本 feature MUST** 照它写：
  - **⚠️ 2026-11-12 修订（承 B12F1 · D-4 / V-7）**：多会话隔离**已由 2026-11-12 P2-b 在 L2 落地**
    （**每次运行从规格新建通道实例**）⇒ **实测**：同一份规格**连续两次** ⇒ **不累积**；
    **并发两次** ⇒ **不串扰** ⇒ ⇒ **B12F1 已 NOT 把这条列为限制**（初版的「X-6 已知限制」**作废**）
    ⇒ **本 feature 的义务收窄为「对外暴露」**：**每次 `invoke` MUST 新建一份通道实例**
    ⇒ 同一张编译图可被**多个会话并发调用**而**状态互不干扰** ⇒ 与 **B7F2** 的「编译产物持规格」
    **共同**落成**门面级**验收；
  - **上游同款**：上游的编译产物只持通道**规格**、**每次运行新建实例**
    （`langgraph/channels/last_value.py:50-54`）⇒ **一次编译、多会话并行**天然成立；
  - **本 feature 的并发承诺仅覆盖「一轮之内」**（B12F1 负责）⇒ 跨运行隔离**归**本条；
  - **B12F1 MUST NOT** 越界实现本条。
  该口径由 B12F1 的 `specs/b12f1-concurrency-errors/spec.md`（**FR-024** · **裁定 23（已作废）** ·
  下游承接 **D-4** · 回溯修订 **T-7**）落成。

- **承接条款（B12F1 → B7F3 · M2 · 并发度旋钮 `max_concurrency` 的「搬进 `RunConfig`」口径）**：
  B12F1（M1）已交付**并发执行内核**并**冻结**了跨 feature 的接口口径 ⇒ **本 feature MUST** 照它写：
  - **旋钮的形态**：B12F1 在 **L2 调度入口**（`run_super_step` / `run_super_steps`）各增了**一个
    **keyword-only** 的参数 **`max_concurrency: int | None = None`**（**上游同名同义** ·
    `langchain_core/runnables/config.py:660-674` 的 `get_executor_for_config`）⇒
    ⇒ **L1 的 20 符号面零改动**（**`RunConfig` 仍为 4 个字段** · 冻结面未破）；
  - **本 feature 的义务**：若要让用户**看得见**这个旋钮 ⇒ MUST **原样**搬进 `RunConfig`
    （**同名同义** · 同样的类型与缺省）⇒ **MUST NOT** 另造一个名字或另定一套语义；
  - **缺省与取值口径**：缺省 `None` ⇒ 并发度上限 = `min(32, cpu+4)`（**上游同款**）⇒
    显式 `N` ⇒ 实际并发度 = `min(本轮任务数, N)`（**N 不被 32 再夹**）⇒ `N = 1` ⇒ **串行基线**
    ⇒ **非法取值 MUST 入口即显式失败**（类型不符 ⇒ 内置 `TypeError`；`< 1` ⇒ 内置 `ValueError`；
    两者均**点名该参数**）⇒ **上游同款**（标准库线程池在**构造时**校验 `max_workers`）；
  - **本 feature MUST NOT** 破 L1 冻结面（B12F1 **零改动** L1 ⇒ 本 feature 若扩 `RunConfig`
    ⇒ 是**本 feature 自己的**契约变更 ⇒ 走 L1 的冻结面流程）；
  - ⚠️ **B12F1 侧已冻结**：并发度缺省 = `min(32, cpu+4)`（**上游同款** · **实测** 20 节点在缺省下
    **无法全部同时到齐**）⇒ ⇒ **不得**改回「不限」或「固定上限」。
  该口径由 B12F1 的 `specs/b12f1-concurrency-errors/spec.md`（**FR-017** · **裁定 2 / 18** ·
  **V-18** · 回溯修订 **T-2**）落成。

- **承接条款（B10F1 → B7F3 · M2 · `invoke()` 的接线 + L1 入参放宽 + MVP 验收承接）**：
  B10F1（M1）已交付**中断 / 恢复**闭环并**冻结**了跨 feature 的接口口径 ⇒
  **本 feature MUST** 照它写：
  - **① L1 `CompiledGraph.invoke` 的 `input` 注解 MUST 放宽**为
    「`StateDict | Command | None`」（**上游同款** ·
    `langgraph/pregel/main.py:3836-3838`）⇒ ⇒ **B10F1 刻意不破该 L1 冻结面**
    ⇒ ⇒ **本 feature MUST** 走「登记 + 回溯修订 + 发起者追认」流程
    （**不**消耗 B10F1 的追认名额）；
  - **② `invoke` MUST 接受 `Command` 作为输入**（**上游同款**）⇒ ⇒ 恢复路径的
    **判定表**以 B10F1 的 `specs/b10f1-interrupt-resume/spec.md` **FR-013 的表**为
    **唯一事实源**（**逐字照抄**）· **判定顺序**以**裁定 4** 为准 ⇒ ⇒
    **MUST NOT** 在本 feature 的文档 / 实现里另抄一份；
  - **③ 挂起时 MUST 返回 `{**state, "__interrupt__": interrupts}`**
    （**无**挂起时**不**含该键）⇒ ⇒ **转成路径 MUST 只此一条**
    （B10F1 的 `InterruptResult.as_result_dict()`）⇒ ⇒ **MUST NOT** 另写一条转成路径；
  - **④ MUST NOT** 把「未挂 checkpointer 时提交 `Command(resume=...)`」**静默降级**
    ⇒ ⇒ MUST 抛**明确异常**；
  - **⑤ 两条补漏口径**（「按 id 的映射恢复」与「未提供恢复值」）MUST 按 **FR-013** 落成
    （**上游同款** · 实测 E-12 / E-13 / E-19 / E-20）；
  - **⑥ MVP 验收基线的人工验证承接**（**偏离登记 V-2 / V-3** · 登记档位 **A**）：
    B10F1 在 **M1** **物理不可达成**「固定脚本那一轮」（`harness/demo/target.py` 需
    `compile()` + `invoke()` = **B7F2 / B7F3 · M2**）⇒ ⇒ **本 feature 的
    `manual-verification.md` MUST** 补上这两轮的**实测输出**（**fake 模型轮** +
    **真实模型轮**）⇒ ⇒ **B10F1 MUST NOT** 把「本 feature 未跑固定脚本」写成
    「本 feature 未验证」（**已达成部分** = B10F1 自身的**挂起侧**人工验证）；
  - **B10F1 MUST NOT** 越界实现门面的 `invoke()`（**FR-024**）。
  该口径由 B10F1 的 `specs/b10f1-interrupt-resume/spec.md`（**FR-002** · **FR-013** ·
  **裁定 1 / 4 / 10** · **SC-002 / SC-011 / SC-012** · 下游承接 **D-3 / D-8**）落成。

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
  ⚠️ **2026-11-12 修订（承 B12F1 · D-2 + Q12）**：① 传播的对象 MUST 是**原始类型与原始消息**
  （MUST NOT 包装成 `RuntimeError` 之类）；② ⚠️ **中断不是「出错」**：B12F1 在中断轮
  **合并抛出**一个 `GraphInterrupt`（载荷 = 元组）且**中断轮不产出结果对象** ⇒
  ⇒ 在 **B10F1** 接手之前，`invoke` MUST **照常把这个异常抛给调用方**
  （MUST NOT 吞掉、也 MUST NOT 假装图跑完了）⇒ 待 **B10F1** 落地后，`invoke` 才把它
  **转成**结果里的 `__interrupt__` 键 ⇒ **本 feature MUST NOT** 另写一条转成路径。
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
- **承接 B3F1 的 FR-005 ③②（验收环境 · 运行期 · 「最小图」反向断言）**：B3F1 只交付
  **③①（声明级 + 导入级）**，**③② 延后至 M2**（依据：B3F1 `spec.md` **裁定 22** · 里程碑见
  立项书 §6.2）。**本 feature 承接「执行」环节** —— 最小图**闭环**（建图 → 编译 → 执行）
  在此闭合 ⇒ **G22「场景 ②」的运行期断言 MUST 在本 feature 交付并点亮**（**只接线，
  MUST NOT 新增门禁编号**）。边界：红线**不放宽**（FR-018 无豁免）—— ③② 是同一红线的
  **运行期加强**，非判据放宽。

### 10. 交付物与后续

- **交付物**：`invoke()` 实现（初始状态写入 + 调度驱动 + 完整状态返回 +
  `InvalidUpdateError`）、单元测试 + 人工验证记录。
- **后续解锁**：**B8F1**（条件边路由 + fresh 读）→ **B8F2**（`stream`）→
  **B22F1**（`get_graph`）→ **B23F1**（PNG）。
- **承接项（红线断言 · 见 §9）**：B3F1 延后的 **FR-005 ③②**（验收环境 · 运行期 ·
  最小图）—— 本 feature 交付「执行」环节，**最小图闭环在此闭合** ⇒ **G22「场景 ②」的
  运行期断言 MUST 在本 feature 交付并点亮**。
- **★ MVP 六项最小交付集**：本 feature 是其中第 3 项。六项齐备后
  `harness/demo/target.py` 的 **fake 模型轮**可跑通（M2 验收点）。
- **风险提示**：「完整状态」这一条极易被实现成「只返回本次写入的 key」。spec 阶段的
  验收判据必须写成**键集相等**断言，而不是「含 `messages` 键」。

---

## 下游承接（**B7F4** · 2026-11-13 · **只接线 · 逐条最小改动**）

- **D-2 · `invoke()` 的对外行为随之支持屏障**：门面级 `invoke` **MUST** 让「多源汇合边」
  在**完整状态**里**可观察**（屏障目标在**所有**源之后出现）⇒ ⇒ **B7F3 MUST NOT**
  为屏障另开一条执行路径（沿用 **B7F1 / B12F1** 的**同一条**）⇒ ⇒ 判据 **FR-005** / **SC-004**。
  ⇒ 落点：`specs/b7f4-multisource-join/spec.md` 的**承接条款 D-2** · 登记项 **PR-4**。

## 依据

- 立项书 §4.3（第 7 项 `invoke` 必须返回完整状态）、§5.2（B7F3 行）、§5.3（C11 / C6）、
  §6.2（M2 = MVP 验收点）、§9.2（fake 注入机制与断言点）、§9.1（门禁）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C11）。
- 验收脚本：`harness/demo/target.py:168`（`agent.invoke(...)`）、
  `harness/demo/graph_core.py`、`harness/demo/agent_loop.py`。
- 宪法 `.specify/memory/constitution.md`：原则 III（第 7 项）。
