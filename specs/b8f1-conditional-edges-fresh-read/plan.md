# Implementation Plan: B8F1 · 条件边路由求值 + `END` 终止 + fresh 读（C8 独立回归测试）

**Branch**: `b8f1-conditional-edges-fresh-read`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`
⇒ 无 `before_specify` 钩子；既有 feature 同样在 `main` 上开发）
| **Date**: 2026-11-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b8f1-conditional-edges-fresh-read/spec.md`

**feature ID**: `B8F1`（**M2 图定义与对外 API**（里程碑第 4 棒 · 全局第 18 个）
· 前置（**上游承接 H-1…H-11 的来源**，共 **10** 个 · **单一事实源 = `spec.md` 的
「承接条款」表** —— 立项书 §5.2 的「前置」列是**里程碑序的简写** · 见**登记项 R-5**）：
**B3F1 + B5F2 + B6F1 + B7F1 + B7F2 + B7F3 + B7F4 + B9F1 + B10F1 + B11F1**
· 后续解锁 **B8F2 / B8F3 / B22F1 / B23F1 / B25F1**）


---

## Summary

交付 freegraph 的**条件边路由语义**——把「条件边」从 B7F1 预留的**空字段**变成**真正被求值**的
路由通道：路由函数在**正确的时机**被调用（源节点任务**成功落回**之后、写入合并**之前**）、
看到**正确的状态视图**（C8 fresh 读：「当前值 + 本节点本次写入」）、返回的目标被**正确解析**
（`path_map` 的 dict 形态 / 无 `path_map` 的动态目标 / 序列多目标 / `END` 终止）、
判错时**立刻**给出说清「返回了什么 · 可以返回什么」的失败信号。本 feature 同时**闭合 C8**
（条件边 fresh 状态读的**独立回归测试**）——它是宪法原则 II 与质量门禁第 3 项里长期挂着
`status=not-landed` 的那一条；并把 `harness/demo/graph_core.py` 的 **A5 组**从**软断言**升级为
**硬断言**（判据只可更严 ⇒ 条件边求值就位之后才落地 ⇒ MUST NOT 造成永久红的 CI）。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **条件边求值** | 路由函数在**源节点任务成功落回**后被调用 | 落 **L2** `run_super_step` 的**阶段 ③′**（判定与落回）· 写入合并（阶段 ⑤）**之前** ⇒ ⇒ 路由函数读到「轮次开始前的通道值 + 本节点本次写入」 |
| **fresh 读（C8）** | 路由函数的**唯一**入参 = 「当前值 + 本节点本次写入」的合并视图 | **唯一实现点** = `local_read(channels, writes, fresh=True)`（**显式**传参 · 缺省是 `False`）· 覆盖**整张通道表** · 路由型通道**缺席** · **零污染** |
| **目标解析** | 路由返回值 ⇒ 目标节点名序列 | `path_map` = **dict**（L3 已归一化）或 **`None`**（动态目标）· 序列 ⇒ 多目标**同轮并行**（共享状态 · 无逐目标载荷）· 去重保序 · **`END` 单独返回 ⇒ 无条件终止**（先于查表）· 序列内的 `END` ⇒ **剔除**（其余目标照常执行 · 口径见 FR-019） |
| **失败信号** | 路由判错时**立刻**说清「返回了什么 · 可以返回什么」 | **两态**（照抄上游）：**有** `path_map` ⇒ 内置 **`KeyError`**；**无** `path_map` ⇒ 内置 **`ValueError`** · 消息**指明返回值与可选目标**（比上游详细 ⇒ **STRICTER** · X-1 / X-3）· 路由函数自身异常 ⇒ **原类型 + 原消息** |
| **`__start__` 条件边** | 挂在**入口哨兵**上的条件边**被求值**（照抄上游 · 修掉当前的「静默空跑」缺陷） | 求值落点 = **阶段 ① 之前**（**仅在第 1 轮**求值一次 ⇒ **幂等** · 后续轮次 MUST NOT 再求值）· 结果写进 `state.dynamic_edges["__start__"]` ⇒ 目标在**第 1 轮**被触发 · 允许**纯条件边入口** · 与静态入口**同轮并行** |
| **触发投递** | 路由目标以**动态边**投递触发 | 复用**既有**载体 `SchedulerState.dynamic_edges`（**零新增触发机制**）· 与同轮 `Command.goto` 目标取**并集**（去重保序）· **零新增编译产物私有字段** |
| **差分场景组** | 路由判定与上游**同场景对跑**（双真实实现） | 落 `tests/differential/parity_probe.py` · **D-103…D-120**（**18** 条）· 判词 **SAME 12 / DIFF 4 / STRICTER 2** · 上游缺席即 `skip` · ⚠️ **载体扩展（属「扩展」非「重造」· 裁定 15）**：`Scenario` dataclass 新增**条件边字段** + `run_freegraph()` 把该载荷传入 `GraphSpec.conditional_edges` ⇒ ⇒ ⇒ **MUST NOT** 新建第二套差分夹具 / 第二条差分执行路径 · ⚠️ **判词非 `SAME` 的 6 条 MUST 带非空 `note`**（STRICTER 2 + DIFF 4 · 与既有守卫 `test_parity_probe.py:106-108` 对齐） |
| **工具循环轮**（**EV-2 承接**） | `harness/demo/agent_loop.py` 的 **B1 / B2** 两组由**软断言** ⇒ **硬断言** | 时序：在**条件边路由求值就位**之后落地（否则永久红 CI）⇒ 破冻结面 **T-7**（并入同一次追认）⇒ 承接 **B7F3 的 EV-2** |
| **人工门禁的判定覆盖** | **SC-019 / SC-020** 由**可自动核验的文档守卫断言**承担 | 宪法原则 VI v1.13.0：「写记录 / 追认」类任务**不**构成判定覆盖 ⇒ 守卫断言 MUST 在**记录写就之后**才转绿 ⇒ **MUST NOT** 造成永久红 CI |

技术方案（**照抄上游**为主 · 唯一的自由裁量在**载体形态**上 · 已登记 **X-5**）：

| 环节 | 落点（已核实的代码锚点） |
|---|---|
| 载荷形态 | `GraphSpec.conditional_edges`（`src/freegraph/runtime/superstep.py:219`）承载 **plain mapping**：外层 key = **源节点名**；内层 = **tuple** of 5 键 dict（`branch` / `path` / `path_map` / `targets` / `route_channels`）—— 该形态**已由 L3 产出**：`src/freegraph/_stategraph.py:205-225` 的 `_conditional_mapping()`（外层 key = 源节点名 · 内层每项**恰 5 键** · 顺序 = 登记顺序）⇒ ⇒ **L2 MUST NOT 重新归一化** |
| 接线 | `src/freegraph/_stategraph.py:175-202` 的 `_graph_spec_from()` **今天完全没传** `conditional_edges`（其 docstring `:186` 写「`conditional_edges` **不传**（恒空 ⇒ 不触发 V-8）」）⇒ 本 feature MUST 改为**填入** `_conditional_mapping()` 的结果 ⇒ ⇒ ⇒ ⚠️ **接线方式 MUST 钉死**（2026-11-18 · analyse 轮修复）：`GraphSpec` 是 **`@dataclass(frozen=True)`** ⇒ **MUST NOT** 构造后赋值 ⇒ ⇒ ⇒ 推荐形态 = **给 `_graph_spec_from()` 增加 `conditional_edges` 形参**（由 `compile()` 把 `_conditional_mapping()` 的结果**传入** ⇒ **一次求值 · 零重复调用**）⇒ ⇒ ⇒ ⚠️ **MUST NOT** 在 `_graph_spec_from()` **内部**再调一次 `_conditional_mapping()`（⇒ 同一载荷**两处派生** ⇒ 漂移风险）⇒ ⇒ ⇒ **零新增编译产物私有字段**（`CompiledGraph._conditional_edges` 已是既有字段 · `_stategraph.py:705` ⇒ ⇒ **T-3 不破** · `vars(compiled)` 仍 == **11** 键） |
| V-8 放宽 | `src/freegraph/runtime/superstep.py:484-487` 的守卫（`if spec.conditional_edges: raise ValueError("GraphSpec.conditional_edges must stay empty in this feature (V-8)")`）MUST **移除**（T-1 破面）⇒ ⇒ 该字段非空**不再是**构造期失败 |
| 求值落点 | `src/freegraph/runtime/superstep.py` 的 `run_super_step`（`:1364`）的**阶段 ③′**（判定与落回 · `_run_round:1253-1267`）—— 源节点任务**成功落回**后、阶段 ⑤ 写入合并**之前** ⇒ ⇒ 路由函数读到的是「轮次开始前的通道值 + 本节点本次写入」 |
| fresh 读 | 唯一实现点 = `src/freegraph/runtime/read.py:163-197` 的 `local_read(channels, writes, *, fresh=False)` ⇒ MUST **显式传** `fresh=True`（`fresh` 缺省是 `False`）· MUST NOT 在调度层另写一份 · `fresh=True` 的实现是 `read.py:101-133` 的 `_fresh_read`（逐通道 copy ⇒ 零污染） |
| 触发投递 | 复用**既有**「动态边」载体：`SchedulerState.dynamic_edges`（`superstep.py:264`）· 键 = **源节点名** · 值 = 目标名 tuple · 由 `_commit_outcome`（`superstep.py:979-1014`，`:987` 写 `state.dynamic_edges[target] = outcome.gotos`）落盘 · `_trigger_groups`（`superstep.py:613-657`）把动态边编成**单元素组** `((_EDGE_SOURCE, source),)` ⇒ ⇒ **零新增触发机制** |
| 与 `Command.goto` 的关系 | 同一源节点同轮既有 `Command.goto` 又有条件边 ⇒ 目标**取并集**（去重保序）⇒ ⇒ 合并进 `outcome.gotos` ⇒ ⇒ ⇒ 再由 `_commit_outcome` 一次性写入 |
| `__start__` 条件边 | `__start__` 是**哨兵**（`superstep.py:123` `_START_MARKER`）· **永不作为节点执行** ⇒ 挂在它上面的条件边**今天永不**被求值（**缺陷**）· `_source_version`（`superstep.py:562-572`）对 `__start__` **恒返回 1** ⇒ 入口边只写过一次 ⇒ ⇒ ⇒ **求值落点 = 阶段 ① 之前**（**仅在第 1 轮**求值一次 ⇒ **幂等** ⇒ 后续轮次 MUST **NOT** 再求值 · 裁定 17）⇒ ⇒ ⇒ 结果写进 `state.dynamic_edges["__start__"]` ⇒ 目标在**第 1 轮**被触发 ⇒ 与静态入口边 `edges["__start__"] = ("a",)` **同轮并行**（两者编出的触发组都是 `("e", "__start__")` · 版本 1 ⇒ 第 1 轮同时满足）⇒ ⇒ ⇒ **纯条件边入口**（无静态入口）也成立（`_validate_entrypoint` **今天就已**接受条件入口 —— `src/freegraph/_stategraph.py:570-583` 的 `conditional_entry` 分支 ⇒ ⇒ **零新增**）⇒ ⇒ ⇒ ⚠️ **「已求值」的幂等标记 MUST 钉死**（2026-11-18 · analyse 轮修复 · 与 `data-model.md` M-7 注一致）= **`"__start__" in state.dynamic_edges`（键存在性）** ⇒ ⇒ ⇒ **MUST NOT** 用「值非空」当判据（返回 `END` ⇒ 空 tuple ⇒ **同样**表示已求值）⇒ ⇒ ⇒ **MUST NOT** 给 `SchedulerState` 新增字段（其「构造签名与名字逐字不变」是 B7F1 / B9F1 / **B8F1** 的冻结面 · `superstep.py:285-287`）⇒ ⇒ ⇒ **MUST NOT** 用 `state.step == 0`（`step` 是「执行轮计数（不含空轮）」⇒ 空轮场景下的「第 1 轮」与触发时点**未对齐**） |
| 双参形态 | 判别依据 = **第二参的参数名是 `config`**（**不是**位置参数个数）· **永远只传一个位置实参**（fresh 视图）· `config` 以**关键字**注入 · 第二参名字不叫 `config` ⇒ 按**一参**调用（上游同款 `TypeError`）· `**kwargs` 形态**不注入** · 注解匹配集 = 无注解 ∨ 类对象 `RunConfig` / `Mapping[str, Any]` ∨ 字符串 ∨ `Optional[...]` / `Union[..., None]` ∨ **PEP-604** 等价形式（匹配集外的注解 ⇒ **跳过注入** ⇒ 按一参调用 ⇒ `TypeError` · ⚠️ **freegraph MUST NOT 发 `UserWarning`**（上游同款的可观察附带信号 · 归偏离 **X-5** · 详见「上游对照」P-13 / P-19 与偏离登记 X-5））· 第二参内容 = 用户交给 `invoke` 的**原始 `config`**（`RunConfig` / mapping / `None` · **逐字**） |
| 失败信号 | 有 `path_map` ⇒ 内置 `KeyError`；无 `path_map` ⇒ 内置 `ValueError`；**消息**比上游详细（点名返回值与可选目标）· 路由函数自身抛出的异常 ⇒ **原类型 + 原消息**传播 |
| `END` | **单独返回** `END` ⇒ **无条件终止**（先于 `path_map` 查表）⇒ ⇒ **序列内**的 `END` ⇒ **剔除**（其余目标照常执行 · 照抄上游 E-13）⇒ ⇒ ⇒ 三处判定的**完整口径**见 spec 的 FR-019 —— 与上游代码分叉（上游**不**过滤 `END` ⇒ 终止条件 = **解析后目的地**恰为 `'__end__'`）⇒ ⇒ 偏离 **X-2**（DIFF）· 差分 **D-110 / D-118** 锁住 |
| `Send` | 复用 `src/freegraph/runtime/_fanout.py` 的 `validate_send`（`:56-82`）/ `make_fanout`（`:85-104`）⇒ ⇒ **零新增**（`Send` 的**调度**属 B11F1 · 本 feature 只复用构造器） |
| 路由通道 | `branch:to:<target>` 通道（`_stategraph.py:617-627` 建 · `EphemeralValue`）**只作声明载体** · **不被写入** ⇒ 触发走动态边 ⇒ MUST **NOT** 触发 V-6（偏离 **X-4**）· **不**进 `invoke` 返回键集（`_full_state` · `_stategraph.py:252-259` 已排除 `EphemeralValue`） |
| branch 名 | `_branch_name`（`_stategraph.py:110-115`）取 `path.__name__`（缺省 `"condition"`）· 同源重名 ⇒ 内置 `ValueError`（`_stategraph.py:508-511`）· **今天已实现** ⇒ **零新增**（FR-040） |

**零新增公开 API、零新增错误类型、零新增门禁编号、零新增依赖**：
门面 `freegraph.graph` 仍 **7** 符号 · `freegraph.runtime` 仍 **23** 符号
（新增的 `src/freegraph/runtime/_routing.py` 是 **L2 私有** ⇒ **不进** `__all__`）·
契约层仍 **21** 符号 ⇒ 兼容矩阵**零新增行**；`langgraph` **只在 Phase 0 的仓库外临时 venv** 里用于上游取证
⇒ `pyproject.toml` **零改动** ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿。

**上游核实落在 Phase 0**（`langgraph 1.2.11` · 仓库外临时 venv · **不进仓库**）⇒ 详见
[research.md](./research.md)（**D-n** 决策 + **DR-n** 遗留登记）与
[contracts/upstream-parity.md](./contracts/upstream-parity.md)
（**P-01…P-23** + **D-103…D-120** + **X-1…X-7**）。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`pyproject.toml` 的 `requires-python = ">=3.11"`）；
**typing 构件上限 = 3.11**（宪法「运行时环境基线」）—— 本 feature 用到的构件**全部 ≤ 3.11**：
`inspect`（签名内省 · **标准库** · 用于路由函数的**参数名**判别与注解匹配）·
`collections.abc`（`Mapping` / `Sequence` / `Callable`）· `dataclasses` ·
`typing`（`Any` / `Optional`）。
**MUST NOT** 使用 `TypeAliasType`(3.12) / `override`(3.12) / `ReadOnly`(3.13) / `TypeIs`(3.13)
或 PEP 695 `type` 语句。**主判定 = CI 矩阵最低档 3.11 跑全量测试**（门禁 **G9** 的 AST 静态断言）。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []` · 沿用现状）。
**开发期**：`pytest`（既有 `[dependency-groups] dev`）—— **零新增**。
⚠️ **本 feature 不引入任何新依赖组**：`langgraph` **仅**在 Phase 0 的**仓库外临时 venv** 里用过
⇒ `pyproject.toml` **零改动** ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿（**未被触碰**）。
差分侧的 `langgraph` 是**开发期**依赖（`tests/differential/conftest.py:25-33` 的 `pytest.importorskip`
⇒ 上游缺席即 `skip`）⇒ 同样**不进**发行元数据。

**Storage**: N/A —— 本 feature 无运行时持久化（checkpoint 属 **B14F1**）。
**仓库内的权威工件** = **纯文本 Markdown 契约**（本 feature 的 `contracts/` 两份 · 见「Phase 1 的产物落点」）。

**Testing**: pytest —— `tests/runtime/`（内核与 C8 实际回归用例）· `tests/differential/`（双真实实现对跑）·
`tests/facade/`（编译产物形状）·
`tests/contracts/`（C4 / C8 的**元测试** · **零** `freegraph.*` import · 门禁 **G2**）。
CI 的 `testpaths = ["tests"]` ⇒ 新增的 `tests/runtime/test_conditional_edges*.py` **自动被收集**。

**Target Platform**: Linux / macOS / Windows（任意 CPython 3.11+ 平台）· **零出站**。

**Project Type**: **library**（图运行内核 · 发行名 = 导入名 = `freegraph` · 不拆独立发行包）。

**Performance Goals**: **N/A（不设时间预算）** —— 路由求值是调度层的一次**函数调用**（外加一次 fresh 视图构造），
无 I/O / 无网络 / 无锁。⚠️ **MUST NOT** 用墙钟耗时做断言（CI 假红）。

**Constraints**（**主要**来自 spec 的 MUST 条目；未逐条列出的 FR 见 `tasks.md` 的追溯表）：

| 约束 | spec 条目 |
|---|---|
| 只依赖**标准库**；MUST NOT import `langchain*` / `langgraph*` / `langsmith` / 任何第三方包 | FR-033 · SC-017 / SC-018 |
| MUST **NOT** 读取**任何**环境变量；零出站；零文件 I/O；导入**无副作用** | FR-033 · SC-017 |
| 路由求值 MUST 落 **L2** 的 super-step 循环内部（**不另开**「条件边专用」的调度路径） | FR-002 · SC-002 / SC-013 |
| 路由求值 MUST **NOT** 受**屏障组**的「所有源齐备」判定影响（条件边 ≠ 多源边） | FR-006 · SC-009 |
| 每个源节点的每次执行 MUST 只求值一次路由函数；同一源节点的多条条件边各求值一次 | FR-003 / FR-004 · SC-009 |
| fresh 读 MUST 走 `local_read(..., fresh=True)`（**显式**传参）· MUST NOT 在调度层另写一份 | FR-007 · SC-004 |
| fresh 视图 MUST 含「当前值 + 本节点本次写入」· MUST NOT 含同轮其它节点的写入 | FR-008 / FR-010 · SC-004 |
| 路由型通道（`EphemeralValue`）MUST 在 fresh 视图里**缺席**（MUST NOT 用名称前缀启发式） | FR-011 / FR-013 · SC-010 |
| `path_map` 在 L2 只有 **dict**（已归一化）或 **`None`** 两种形态 · MUST NOT 重新归一化 | FR-014 / FR-016 · SC-005 |
| 路由返回值 MUST 是**归一化后 dict 的 key**；取值不在表内 ⇒ 显式失败 | FR-015 / FR-016 · SC-006 |
| **单独返回** `END` ⇒ **无条件终止**（判定**先于**查表）· 序列中 `END` 被**剔除**、其余目标照常执行（**三处判定口径**见 spec 的 FR-019） | FR-019 · SC-003 |
| 失败信号**两态**（有 `path_map` ⇒ `KeyError`；无 ⇒ `ValueError`）· 消息 MUST 指明返回值与可选目标 | FR-021 / FR-022 / FR-025 · SC-006 / SC-007 |
| 路由函数自身异常 MUST 以**原始类型 + 原始消息**传播（MUST NOT 包装 / 吞掉） | FR-023 · SC-012 |
| 路由返回值形态：标量 / `list` / `tuple`（⇒ 多目标）· 非 `str` 的**可哈希**值 MUST 正常查表 | FR-020 / FR-024 · SC-005 / SC-006 |
| 路由函数 MUST 支持**单参**与**双参**两形态 · 判别依据 = **第二参的参数名是 `config`** · `config` 以**关键字**注入 · 永远只传一个位置实参 | FR-003 · SC-021 |
| 路由目标 MUST 与同轮 `Command.goto` 目标取**并集**（去重保序） | FR-031 · SC-012 |
| 路由返回 `Send` / `list[Send]` ⇒ MUST 复用 **B11F1** 的既有 fan-out 构造器（MUST NOT 另写路径）· MUST NOT 改 B11F1 的冻结面（V-19 / V-21）⇒ 失败信号的分叉已登记（**X-6 / X-7**） | FR-030 · SC-008 · SC-013 |
| 路由通道 MUST **不被写入**（只作声明载体）· MUST NOT 触发 V-6 | FR-028 · SC-011 |
| 路由通道 MUST **不**出现在 `invoke` 的返回键集里 | FR-029 · SC-002 / SC-010 |
| `__start__` 上的条件边 MUST 被求值 ⇒ 允许**纯条件边入口** · 与静态入口**同轮并行** | FR-038 / FR-039 · SC-022 / SC-023 |
| 同源**重名** branch ⇒ 内置 `ValueError`（消息点名分支名与源节点）· `__start__` **不特例化** | FR-040 · SC-024 |
| 差分的**路由判定** MUST 落 `tests/differential/parity_probe.py`（**双真实实现**对跑）· MUST NOT 重造夹具接口 | FR-032 · SC-013 / SC-014 |
| B5F2 差分夹具的 `conditional_edges` 字段 MUST **保持恒空** ⇒ **V-4 无需放宽** | FR-032 · 裁定 15 |
| **C8 独立回归测试** MUST 常驻 CI · MUST 是**否定式断言** · MUST 住 `tests/runtime/`（门禁 **G2**） | FR-034 · SC-001 / SC-014 |
| `harness/demo/graph_core.py` 的 A5 组 MUST 由**软断言**升级为**硬断言** | FR-035 · SC-015 |
| MUST **NOT** 实现 `stream()` / `Send` 的**调度** / 节点别名 / `context` 通道 / `get_graph()` / checkpoint / async | FR-036 · SC-015 |
| MUST **NOT** 破坏 B7F2 的编译产物持有面（`vars(compiled)` 的键数仍 == **11**） | FR-037 · SC-016 |
| **图规格校验** MUST 仍在**构造时**执行；**V-8 移除**后其余 V-1…V-3 等**逐字不动** | FR-026 · SC-016 |
| 新源文件 MUST 带**署名头**且 docstring 是首个语句；上游引用 MUST 标**版本 + `路径:行号`** | 宪法原则 X · 门禁 **G30** |
| 人工验证记录（五段式 + 来源覆盖表）+ **发起者追认**（唯一一次） | 宪法原则 V / v1.8.0 · SC-019 / SC-020 |
| `harness/demo/agent_loop.py` 的 **B1 / B2** 组 MUST 由**软断言**升级为**硬断言**（时序：在路由求值就位之后） | FR-041 · SC-025 · 破冻结面 **T-7** |
| **人工门禁类 SC**（**SC-019 / SC-020**）的判定 MUST 由**可自动核验的文档守卫断言**承担（断言记录存在 + 两轮非空实测输出 + 追认文字含破面全集 **7** 类）⇒ MUST 安排在记录写就之后 | FR-042 · SC-019 · SC-020 · SC-026 · 宪法原则 VI v1.13.0 |
| 「**fake 模型轮**」= 猴补（monkey-patch）`init_chat_model` + **含条件边的最小图** / `agent_loop.py` 的**工具循环轮** ⇒ **本 feature 可达** ⇒ MUST 真跑并记录；而「`target.py` 端到端轮」不可达 ⇒ 具名承接 B22F1/B23F1/B25F1 | 裁定 19 · SC-020 · SC-026 · 登记项 **R-2 ③** |

**Scale/Scope**: 单图单次 `invoke` 的**路由求值次数** == Σ（各源节点各次成功落回 × 其条件边条数）
· 单条条件边的目标数**上界** = 路由返回值序列的长度（去重保序后更小）·
fresh 视图的**规模** = 通道表大小（**整张**通道表 · 非订阅集）⇒ ⇒ 均为**结构口径** ⇒ 可自动判定。

---

## 绿基线记录 + 变红清单（宪法 v1.11.0 的基线义务）

> **依据**：宪法 **v1.8.0**「破冻结面的三条」① 的补强（**v1.11.0**）——
> 「**冻结断言清单 MUST 实测化**」+「**基线义务**」：
> 实施**开始前** MUST 先跑一遍既有测试套件并**记录绿基线**（计数）
> ⇒ ⇒ ⇒ 再按本 feature 的落地形态改动源码 ⇒ ⇒ ⇒ **变红**的断言即入冻结面清单
> ⇒ ⇒ ⇒ MUST 逐条带 **`文件:行号`** + **变红原因** ⇒ ⇒ ⇒ MUST **NOT** 只凭推理登记
> ⇒ ⇒ ⇒ **落点**：plan 阶段的「绿基线记录 + 变红清单」（本节）。

**义务（落 `tasks.md` · 一条**阻断合入**的任务）**：实施**开始前** MUST 跑下面这条命令并**记录绿基线**：

```text
uv run --no-project --python .venv python -m pytest tests/ -ra
```

⇒ ⇒ ⇒ 记录**绿基线**（用例计数 / 跳过数 / 失败数）⇒ ⇒ ⇒ 再按本 feature 的落地形态改动源码
⇒ ⇒ ⇒ 重跑同一命令 ⇒ ⇒ ⇒ **变红**的断言逐条带 `文件:行号` + 变红原因**写回本节**
⇒ ⇒ ⇒ **MUST NOT** 只凭推理登记 ⇒ ⇒ ⇒ **发起者追认开始前**本节 MUST 已被**实测填实**。

**绿基线记录**（**待实施时实测填入** —— 本 plan 阶段**未**改动任何源码 ⇒ 无实测计数可填）：

| 项 | 值 | 状态 |
|---|---|---|
| 基线命令 | `uv run --no-project --python .venv python -m pytest tests/ -ra` | 已写入 `tasks.md`（阻断合入） |
| 基线**用例计数**（passed / skipped / failed） | **1486 passed · 4 skipped · 0 failed**（耗时 100.27s） | ✅ **已实测填实**（tasks **T001** · 2026-11-18） |
| 基线**跑测时刻**（ISO 日期 + 提交号） | **2026-11-18T04:33:39+08:00** · 提交 **f60a182**（`docs(verification): 记录 B7F3 CI 实跑 7/7 作业全绿`） | ✅ **已实测填实**（tasks **T001** · 2026-11-18） |
| 基线**4 条 skip 的归属** | ① `tests/contracts/test_contract_regressions.py:85`（**C8 未落地** ⇒ 本 feature 闭合）② `tests/contracts/test_protocols.py:388`（本机未装 mypy）③ `tests/facade/test_api_snapshot.py:189`（未开 `--update-api-snapshot`）④ `tests/runtime/test_windows_clock_resolution.py:58`（仅 Windows 档） | ✅ **逐条点名** ⇒ 实施期**新增**的 skip MUST 再登记 |

> ⚠️ **T001 的实测结论**（2026-11-18）：基线**全绿** ⇒ ⇒ ⇒ 「变红清单」在本 feature 落地前
> **实测不出任何变红** ⇒ ⇒ ⇒ 故 plan 的「变红清单」为**预登记**（推理级）⇒ ⇒ ⇒
> **实测化归 T066**（Phase 2 末 · 在 T005 / T006 / T019 / T020 / T021 / T022 之后）。

### 变红清单（**预登记** · 共 **6 项** · ⚠️ **本表 ≠ spec 的「破面全集」**）

> ⚠️ **两个集合的成员不同**（**数字不同 · 成员也不同**）：
> 本表 = **变红断言**（**6** 项 · 全部是**既有测试断言**）⇒ spec 的「破面全集」= **破冻结面**
> （**7** 类 · 含 **源码改动**与**验收脚本软断言** ⇒ **多出 T-7** · 本表**无**对应的既有断言
> ⇒ ⇒ ⇒ 它是**时序风险**而非变红断言）⇒ ⇒ ⇒ 逐条映射：
> **变红清单 ① + ②** ⇒ spec 的**冻结断言 ①**（同一文件的两条用例 · 拆分而来）·
> **变红清单 ③** ⇒ spec 的**冻结断言 ②** · **变红清单 ④** ⇒ spec 的**冻结断言 ④** ·
> **变红清单 ⑤** ⇒ spec 的 **T-5**（C8 挂载点）· **变红清单 ⑥** ⇒ **差分侧的既有守卫**
> （`test_parity_probe.py` 的判词取值域 + 非空 `note` 守卫 · **T022 触碰**）
> ⇒ ⇒ ⇒ spec 的 **T-1**（V-8 守卫移除）是**源码改动**
> ⇒ ⇒ ⇒ **不**在本表（它没有对应的既有断言）⇒ ⇒ ⇒ ⚠️ spec 的 **T-6**
> （`graph_core.py` 的 A5 组软断言 ⇒ 硬）与 **T-7**
> （`agent_loop.py` 的 B1 / B2 组软断言 ⇒ 硬）**均不在**本表 ⇒ ⇒ ⇒ 二者是**时序风险**
> （提前硬化 ⇒ 永久红 CI）⇒ ⇒ ⇒ 处置见本节末的「时序风险」提示。
>
> ⚠️ **原 ⑥（`graph_core.py` 的 A5 组）已移出本表**（2026-11-18 · analyse 轮修复）：
> 它的变红源是 **T055**（Phase 9 的「软 ⇒ 硬」）⇒ ⇒ ⇒ 在 **T066**（Phase 2 末）的实测化
> 时点它**必然是绿的**（T055 尚未落地 ⇒ 条件边求值已就位 ⇒ 不红）⇒ ⇒ ⇒ 「待实测确认」
> 将**永远关不掉** ⇒ ⇒ ⇒ 故归入**时序风险**段（**判据只收紧**：它仍 MUST 在 T012 / T013
> 之后落地 ⇒ MUST NOT 写永久红的 CI）。

> ⚠️ **本表是「预登记」**（依据 = spec 的破面清单 + 已核实的代码锚点）⇒ ⇒ ⇒
> **实测确认前不得据此追认** ⇒ ⇒ ⇒ 实测若发现**更多**变红断言 ⇒ MUST **追加登记**（见下表末注）。

| # | 变红断言（`文件:行号`） | 变红原因 | 处置（**拆分而不删** · 判据只可更严） | 状态 |
|---|---|---|---|---|
| ① | `tests/runtime/test_superstep_basic.py:557-565`（`test_a_non_empty_conditional_edges_field_fails_explicitly`） | **V-8 守卫移除** ⇒ 该字段非空**不再**是构造期失败 ⇒ `pytest.raises(ValueError)` 落空 | 改为「**非空 ⇒ 接受且原样承载**」+ 保留「构造期**其它**失败路径**逐条唯一**」的断言  ✅ **实测：未变红**（V-8 守卫移除后，``pytest.raises(ValueError)`` 仍成立 ⇒ 但**异常来源**由 V-8 变为 **V-27** 的五键形态校验 ⇒ **断言仍绿** ⇒ 「拆分而不删」的**处置照执行**（破面 **T-1**） |
| ② | `tests/runtime/test_superstep_basic.py:568-576`（`test_the_delivered_specs_keep_the_conditional_edges_field_empty`） | 同 ①：断言「交付的规格该字段**恒空**」不再成立（编译产物开始**填值**） | 与 ① **同处拆分**（拆为「恒空构造成功」与「填值构造成功且原样承载」两条）  ✅ **实测：未变红**（「交付的规格该字段恒空」仍成立 ⇒ 断言仍绿）⇒ 「拆分」的**处置照执行** |
| ③ | `tests/runtime/test_superstep_contract.py:609-617`（`test_i14_a_non_empty_conditional_edges_field_fails_explicitly`）+ `:77` 的不变式映射 **I-14** | **I-14** 的语义由「恒空即失败」改为「**填值即被路由求值消费**」⇒ 用例体不再成立 | **拆分而不删**：**I-14** 的**编号与槽位不变**（⇒ 契约守卫的解析范围**零改动**）· 用例体改为「填值 ⇒ 构造**成功**且该值**原样**承载」  ✅ **实测：未变红**（``pytest.raises(ValueError)`` 仍成立 ⇒ 异常来源变为 **V-27**）⇒ 「拆分」的**处置照执行** |
| ④ | `tests/facade/test_compiled_graph.py:263-265`（`test_graphspec_conditional_edges_is_always_empty`） | 接线后 `GraphSpec.conditional_edges` **非空** ⇒ 「恒空」断言不成立 | **替换为反面断言**：**非空**且与 `compiled._conditional_edges` **逐字相等** ⇒ **判据只可更严**（恒空 ⇒ 非空且一致）  🔴 **实测：变红**（接线后该字段**非空** ⇒ 「恒空」断言不成立）⇒ **预登记命中** ⇒ 已按「**替换为反面断言**」处置 |
| ⑤ | `tests/contracts/test_contract_regressions.py:36`（`GATE-MOUNT: C8 · status=not-landed · owner=B8F1`）+ `:85-91`（`@pytest.mark.skip` + `raise NotImplementedError`） | C8 挂载点翻为 `status=landed` ⇒ 该文件的内容变化 ⇒ 门禁 **G29**（`harness/scripts/gates/gate_G29_contract_carrier.py:63` `MOUNT_POINT_RELPATH` · `:66` `MOUNT_MARKER` · `:127-144` 解析 · `:220-248` 判定）的输出变化；若既有断言逐字比对 `not-landed` 则变红 | `:36` 翻为 `status=landed` + **新增** C8 的**元测试**（**路径扫描** · 参照同文件 `:49-82` 的 C4 元测试 · **零** `freegraph.*` import）⇒ ⚠️ 若实测发现 G29 或既有断言因该行变红 ⇒ **追加登记**（**MUST NOT** 预先假定其不红）  ✅ **实测：未变红**（该文件的内容**未被**逐字断言 ⇒ 只有 G29 的**输出**变化）⇒ 破面 **T-5** 的**处置照执行**（翻挂载点 + 改名保留占位） |
| ⑥ | `tests/differential/test_parity_probe.py:106-108`（`test_the_verdict_vocabulary_is_closed` · 判词取值域 + **非空 `note`** 守卫） | T022 新增 **18** 条差分场景 ⇒ 判词非 `SAME` 的 **6** 条若未带 `note` ⇒ 该守卫变红（⇒ ⇒ ⇒ SC-013 已把口径钉为 **6 条** ⇒ 本条**预登记**以免漏记） | 新增场景**必带** `note`（STRICTER 2 + DIFF 4）⇒ ⇒ ⇒ 判词分布**零变动** ⇒ ⇒ ⇒ ⚠️ **若实测发现更多差分侧变红断言 ⇒ MUST 追加登记**  ✅ **实测：未变红**（新增的 18 条差分场景**均带** ``note`` ⇒ 「判词取值域 + ``note`` 非空」守卫**仍绿**）⇒ **预登记命中的是「若漏带 note 才红」这一情形** ⇒ 实测未触发 |

| **⑦** | `tests/facade/_invoke_support.py:122-138`（`build_conditional_graph`）⇒ 连带 `tests/facade/test_invoke_full_state.py:104-111` 与 `tests/facade/test_invoke_isolation.py:27-37` | **条件边**路由求值**已交付** ⇒ ⇒ ⇒ 该夹具的路由函数返回 `"a"`，而 ``path_map`` 是 ``["b", END]`` ⇒ ⇒ ⇒ 查表失败 ⇒ ⇒ ⇒ 抛内置 ``KeyError`` ⇒ ⇒ ⇒ **两条断言变红** | **修夹具**（``path_map`` 改为 ``{"a": "b"}`` ⇒ 路由合法 ⇒ 流程 = ``START→a→b``）⇒ ⇒ ⇒ **两条断言逐字未动** ⇒ ⇒ ⇒ **判据只收紧**（路由通道**真的被用过** ⇒ 断言**不再空洞**） | 🔴 **实测：变红**（**追加登记** · 2026-11-18） |
| **⑧** | `tests/runtime/test_interrupt_contract.py:176-179` | C8 的挂载点由 ``not-landed`` 翻为 ``landed`` ⇒ ⇒ ⇒ 该文件断言 ``GATE-MOUNT: C8 · status=not-landed`` ⇒ ⇒ ⇒ **变红** | **逐字替换**为 ``status=landed`` ⇒ ⇒ ⇒ **追加**「**MUST NOT** 退回 ``not-landed``」的反向断言 ⇒ ⇒ ⇒ **承接方 / 里程碑两条断言逐字保留** ⇒ ⇒ ⇒ **判据只收紧** | 🔴 **实测：变红**（**追加登记** · 2026-11-18） |

> ⚠️ **实测优先于预登记**：上表**六项**是本表（变红断言）的预登记项；spec 的**破面全集**为 **7 类**
> （**唯一事实源** = spec「破冻结面的回溯修订清单」⇒ **T-6 / T-7 均不在本表** ⇒ 两者**不是同一组**
> ⇒ ⇒ ⇒ 本表的 ⑥ 是**差分侧既有守卫**，spec 的 ⑥ 是 **T-6** · ⑦ 是 **T-7**）
> ⇒ ⇒ ⇒ **实测若另有变红断言** ⇒ MUST **追加**到本表并**先判**「是否由本 feature 的落地形态导致」
> ⇒ ⇒ ⇒ 再判「是否属冻结断言」⇒ ⇒ ⇒ **MUST NOT** 以「实现期再说」放过。
>
> ### ✅ 实测化结论（**T066** · 2026-11-18 · Phase 2 末）
>
> | 口径 | 结果 |
> |---|---|
> | **预登记项** | **6** 项 ⇒ **实测变红 1 项**（④）· **未变红 5 项**（① ② ③ ⑤ ⑦）⇒ ⇒ ⇒ 「**预登记**」的**推理**在 ① ② ③ 上**不准**（它们的异常来源从 V-8 变成了 **V-27**）⇒ ⇒ ⇒ 但**处置照执行**（破面 **T-1** 要求「拆分而不删」）⇒ ⇒ ⇒ **判据零放宽** |
> | **追加登记项** | **2** 项（**⑦**  facade 夹具 · **⑧**  C8 挂载点断言）⇒ ⇒ ⇒ 均**由本 feature 的落地形态导致** ⇒ ⇒ ⇒ **已按「拆分而不删 / 判据只收紧」处置** |
> | **未变红的处置** | ① ② ③ 的「拆分」**照执行**（破面 **T-1** 的**回溯修订**要求）⇒ ⇒ ⇒ **实测化**不等于「跳过」 |
> | **时序风险**（非变红断言） | **T-6**（`graph_core.py` 的 A5 组 + A6 的 C16 段）· **T-7**（`agent_loop.py` 的 B1 / B2 / B3 组）⇒ ⇒ ⇒ 二者**由软 ⇒ 硬**（**判据只收紧**）⇒ ⇒ ⇒ **归破面全集**（**T-6 / T-7**）⇒ ⇒ ⇒ **不在**本表的实测化范围（它们**从未变红** ⇒ **提前硬化才会红**） |
> | **实测化时点** | **T066** 在 **T005 / T006 / T019 / T020 / T021 / T022** 落地**之后**执行 ⇒ ⇒ ⇒ 变红清单的**每一项**都有**实测**结论（**无**「待实测确认」残留）⇒ ⇒ ⇒ **发起者追认前本节已填实**（宪法 v1.11.0 的基线义务） |
> ⇒ ⇒ ⇒ ⚠️ **实测化时点 = `tasks.md` 的 **T066**（Phase 2 末）** ⇒ ⇒ ⇒ **T066 的依赖 MUST 含
> **T022**（本表 ⑥ 的变红源）⇒ ⇒ ⇒ 否则本表 ⑥ 在 T066 时点**尚未产生**⇒ ⇒ ⇒ 「实测化」不闭合。
>
> **时序风险（非变红断言 · 但同样会撞「MUST NOT 写永久红的 CI」）**：
> ① **T-6**（`graph_core.py` 的 A5 组软断言 ⇒ 硬 · **2026-11-18 从变红清单移入本段**
> · 该项在移出前是变红清单的**第 6 行**（旧编号 ⑥）⇒ ⇒ ⇒ **现行**变红清单的 ⑥ 是**差分侧守卫**）
> ② **T-7**（`agent_loop.py` 的 B1 / B2 组软断言 ⇒ 硬）③ **文档守卫断言**
> （SC-019 / SC-020 的判定覆盖）⇒ ⇒ ⇒ 三者**都** MUST 在**被断言的能力就位之后**落地
> ⇒ ⇒ ⇒ ① ② ⇒ **条件边路由求值就位**（tasks **T012 / T013**）⇒ ⇒ ⇒ ③ ⇒ **人工验证记录与追认写就之后**
> （tasks **T058…T061**）⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 提前落地（**永久红窗口**）。

### MUST NOT 变红的既有断言（**不破面** · 4 类）

| 冻结面 | 锚点 | 本 feature 的处置（**必须**保持绿） |
|---|---|---|
| **T-2** | `tests/differential/spec_builder.py:122-126`（**V-4**：差分夹具的 `conditional_edges` 恒空 ⇒ 非空即失败） | **不破** ⇒ B5F2 的差分夹具字段**保持恒空** ⇒ 差分落 `parity_probe.py`（裁定 15）⇒ 该断言**必须**保持绿 |
| **冻结断言 ③** | `tests/differential/test_differential.py:123-132`（`test_non_empty_conditional_edges_are_an_explicit_failure`） | **逐字不动** ⇒ **必须**保持绿 |
| **T-3** | `tests/facade/test_compiled_graph.py:111-114`（3 私有 + 8 公开 = **11** 键的持有面） | **不破** ⇒ **零新增**编译产物私有字段 ⇒ `vars(compiled)` 的键数仍 == **11** ⇒ **必须**保持绿 |
| **T-4** | `harness/demo/target.py` 的只读基准 diff 断言 | **一字不改**（`harness/demo/target.py` **MUST NOT** 被改动）⇒ **必须**保持绿 |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 通过项（逐条）

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith 依赖 · 自身零出站 · 零环境变量） | FR-033 · 既有 **G24**（配置层扫描 `src/freegraph/**`）· **G26**（网络静态扫描）· **G27**（零出站动态）· **G4** | ✅ |
| 原则 II（内核纯净 · 状态语义 MUST 与 LangGraph 等价） | FR-022/FR-033（零依赖）· **G3 / G21 / G22 / G23**（依赖闭包为空集）· `contracts/upstream-parity.md`（**P-01…P-23** 逐条对照）+ `tests/differential/parity_probe.py`（**D-103…D-120** 双真实实现对跑）承载等价性 · **C8 独立回归测试**（MUST 住 `tests/runtime/`） | ✅ 本 feature **闭合 C8** |
| 原则 III（验收契约优先 · `target.py` 只读） | 本 feature **零改动** `harness/demo/target.py`（**T-4 不破**）· 验收证据落在可改的 `harness/demo/graph_core.py`（A5 组转硬断言） | ⚠️ 「`target.py` 原样可跑」**仍物理不可达成** ⇒ 见**登记项 R-2** |
| 原则 IV（可诊断性是一等功能） | N/A（本 feature **无新增**运行期可观测面；路由失败沿用既有内置异常类型 · 零新增错误类型） | ✅ 边界内 |
| 原则 V（人工验收是最终验收标准） | 人工验证记录（五段式 + 来源覆盖表 · SC-020）· ⚠️ **两个「fake 轮」MUST 消歧**：**「验收基线 fake 轮」**（门禁 4 · 跑 `harness/demo/target.py`）**本 feature 不可达**（PNG 路径属 **B23F1** · 原则 III / V ⇒ 见**登记项 R-2 ③**）⇒ ⇒ ⇒ **「fake 模型轮」**（猴补 `init_chat_model` + **含条件边的最小图** / `agent_loop.py` 的**工具循环轮**）**本 feature 可达** ⇒ ⇒ ⇒ **MUST 真跑并记录**（SC-020 / SC-026 · 裁定 19） | ⚠️ 门禁 4 的**验收基线 fake 轮**与门禁 5 的「**真实模型一轮**」**均**物理不可达成 ⇒ 见**登记项 R-2 ② ③** ⇒ ⇒ ⇒ **fake 模型轮照常落地**（**不豁免**） |
| 原则 VI（规格驱动 · tasks 可逐条勾选 · 判据级覆盖 · **v1.13.0 人工门禁类 SC**） | 本 plan + `tasks.md`（含 FR ↔ SC 追溯表）· 每条 SC MUST 挂**能判定它**的任务（**不**用「实现任务」冒充）· ⚠️ **SC-019 / SC-020**（人工门禁类）⇒ MUST 由**可自动核验的文档守卫断言**承担（tasks **T068**）⇒ ⇒ 「写记录 / 追认」类任务**不**构成判定覆盖 | ✅ |
| 原则 VII（职责边界 · 契约 C1–C27） | FR-014 / FR-027（**C7** 路由函数与 `path_map` 双形态的执行侧落地）· FR-007…FR-013（**C8** fresh 读的执行侧落地）· **MUST NOT** import L3/L4/L5 | ✅ **C4**（B5F2 / B7F1 已闭合）+ **C8**（本 feature 闭合）⇒ 门禁 3 的 C4 / C8 部分**全绿** |
| 原则 VIII（证据与术语纪律） | `research.md` 每条决策附**实测方法 + 真实输出**（上游 `langgraph 1.2.11`）· 上游引用标 `路径:行号` · 偏离登记 **X-1…X-7** 与对照表**三态标注逐字一致**（v1.12.0 末条） | ✅ |
| 原则 IX（许可证与商标红线 · NON-NEGOTIABLE） | **零新增依赖** ⇒ `THIRD_PARTY_NOTICES` **无需变更**· **零品牌资产**（重写语义，不复制上游代码） | ✅ |
| 原则 X（文档合规 + 源文件署名头） | 新增的 `src/freegraph/runtime/_routing.py` MUST 带署名头（既有 **G30** 全仓扫描自动覆盖）· 兼容矩阵**零新增行**（须在人工记录中显式记「零新增」） | ✅ |
| 运行时环境基线（Python 3.11 · typing 上限 3.11） | 本 feature 只用 ≤ 3.11 构件（Technical Context 已逐项列出）· 最低档 3.11 跑全量测试 · **G9** AST 静态断言 | ✅ |
| 依赖白名单 / 黑名单（包层 · 配置层 · 网络层） | **零新增运行时依赖** ⇒ **G3 / G21 / G23 / G24 / G26 / G27** 恒绿 | ✅ |
| **跨 feature 承接的接线通则（v1.8.0）** | 上游 **H-1…H-11** 全部指向**已交付**的 feature（B7F1 / B5F2 / B7F2 / B6F1 / B7F3 / B7F4 / B9F1 / B11F1 / B3F1 / B10F1）⇒ **无需**写入目标提示词初稿（属**已发布的事实** · 原则 VIII）⇒ 本 feature 只需**消费**；下游 **D-1…D-5** MUST **写入**目标 feature 的提示词初稿 ⇒ 见**登记项 R-3** | ⚠️ **R-3** |
| 质量门禁 1 / 2 / 6 / 7 | ① 规格 + tasks 可勾选 ② 依赖**零新增** ⑥ 证据（research + 对照表 + 差分场景组）⑦ 文档合规（署名头 + 兼容矩阵零新增） | ✅ |
| 质量门禁 3 / 4 / 5 | 门禁 3 的 **C4 / C8 两条独立回归** ⇒ **本 feature 闭合 C8**（C4 已闭合）⇒ **本 feature 全绿**；门禁 4 的「fake 模型跑通**验收基线（`target.py`）**的一轮」⇒ **物理不可达成** ⇒ ⚠️ **窄口径**：本 feature 的「fake 模型轮」（猴补 + 含条件边的最小图 / `agent_loop.py` 工具循环轮）**可达** ⇒ 照常落地（**验收基线 = `harness/demo/target.py`** · 原则 III · 原则 V ⇒ PNG 在 `invoke()` **之前** ⇒ 属 **B23F1**）⇒ ⇒ ⇒ **见登记项 R-2 ③**（窄口径） | ⚠️（C4 / C8 ✅ · 门禁 4 ⇒ **见 R-2 ③**） |
| 质量门禁 3 的 `target.py` 部分 / 门禁 4 的**验收基线 fake 轮** / 门禁 5 的真实模型轮 | ⚠️ **物理不可达成** ⇒ **登记项 R-2**（偏离登记 + 发起者追认）⇒ ⇒ ⇒ ⚠️ **「fake 模型轮」**（猴补 + 含条件边的最小图 / `agent_loop.py` 的**工具循环轮**）**本 feature 可达** ⇒ **MUST 真跑并记录** | ⚠️ **见 R-2 ② ③** |
| 发布门禁（发行产物纯度） | 本 feature **不接入**（B24F1）· 新增代码在 `src/freegraph/runtime/` 内 ⇒ **不污染**产物纯度；**零新增依赖** ⇒ sdist / wheel 零变更 | ✅ 边界内 |

### ⚠️ 登记项 R-1（**破冻结面 7 类** · 唯一一次追认）

**依据**：宪法 **v1.8.0**「跨 feature 承接的接线通则」的「破冻结面的三条」——
① **回溯修订**（契约 + spec + 冻结断言，**既有断言拆分而不删**）② 该 feature 的「上游对照」表
MUST 写明「**上游有此项 ⇒ freegraph 原先缺**」或「**上游无此项 ⇒ 属自研区**」③ **发起者追认**
（追认文字 MUST 落 `harness/verification/B8F1/manual-verification.md` ⇒ **未追认前 MUST NOT 合入**）
⇒ ⇒ ⇒ **追认次数每 feature MUST ≤ 1 次**。

**上游对照表的对应行**（条款 ② 的落实 · 逐条对应）：**P-01…P-23**（`contracts/upstream-parity.md` §2）
⇒ ⇒ 上游 `langgraph 1.2.11` **有**全部条件边语义 ⇒ ⇒ ⇒ freegraph 原先缺的是「**求值**」与「**接线**」
⇒ ⇒ ⇒ **不是**「更方便」破面 ⇒ ⇒ ⇒ **X-2**（`END` **单独返回** ⇒ 无条件终止 · FR-019）与 **X-5**（双参第二参内容）已如实登记。

| # | 被偏离的**具体项**（冻结面） | 回溯修订位置 | 承接方（feature ID + 里程碑） | 承接机制 |
|---|---|---|---|---|
| **T-1** | B7F1 的校验规则 **V-8**（`GraphSpec.conditional_edges` 非空 ⇒ 内置 `ValueError`） | ① `src/freegraph/runtime/superstep.py:484-487`（移除该守卫）② `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §2.1 的「条件边」行 + §2.1.1 的 **V-8** 行 ③ `specs/b7f1-superstep-loop/spec.md` 的 **FR-033** / **B7F1 的**裁定 25 行 ④ `specs/b7f1-superstep-loop/data-model.md` 的 V-8 行 ⇒ ⇒ ⇒ ⚠️ **②③④ 三处的**文档**回溯修订 MUST 由 `tasks.md` 的 **T069** 落地**（宪法 v1.9.0 ① 的「契约 + spec」两面）⇒ ⇒ ⇒ ① 由 **T005** 落地 | **B8F1**（M2）· 本 feature 内闭合 | **拆分而不删**：原「恒空即失败」行**保留**并标注「**自 B8F1 起放宽**：允许非空 · 由路由求值消费」⇒ 其余 **V-1…V-3** 逐字不动 |
| **冻结断言 ①** | `tests/runtime/test_superstep_basic.py:557-576` | 同一文件（**拆分**：原「非空 ⇒ 显式失败」改为「**非空 ⇒ 接受且原样承载**」+ 保留「构造期**其它**失败路径逐条唯一」） | **B8F1**（M2） | **拆分而不删** |
| **冻结断言 ②** | `tests/runtime/test_superstep_contract.py:77` 的 **I-14** + `:609-617` 的用例体 | 同一文件（**拆分**：**I-14** 的语义由「恒空即失败」改为「**填值即被路由求值消费**」⇒ **编号与槽位不变** ⇒ 契约守卫的解析范围**零改动**） | **B8F1**（M2） | **拆分而不删** |
| **冻结断言 ④** | `tests/facade/test_compiled_graph.py:263-265` | 同一文件（**替换为反面断言**：`GraphSpec.conditional_edges` **非空**且与 `compiled._conditional_edges` **逐字相等**） | **B8F1**（M2） | **拆分而不删** · ⚠️ **判据只可更严**（v1.14.0） |
| **T-5** | C8 的**挂载点**（`tests/contracts/test_contract_regressions.py:36`） | ① 同一文件（`:36` 翻为 `status=landed`）② 同一文件（**新增** C8 的**元测试**：路径扫描「C8 独立回归测试在位且被 pytest 收集」· 形态参照 `C4_REGRESSION_RELPATH` 的既有写法 · `:49-82`）⇒ ⇒ ⇒ ⚠️ **原第 ③ 处（`specs/b3f1-scaffold-ci-gates/` 的门禁契约行）已撤除** —— 经复核：该契约的挂载点 `status` 已是「`not-landed` / `landed` **两态**口径」（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md:372-374` · B5F2 轮修订）⇒ ⇒ ⇒ C8 翻为 `landed` **不违反**该契约 ⇒ ⇒ ⇒ **本次无需改动**（⇒ ⇒ ⇒ **破面全集仍为 7 类** · 仅回溯修订位置减一处） | **B8F1**（M2） | **拆分而不删**（`C4_REGRESSION_RELPATH` 的既有行**逐字不动**）· **零** `freegraph.*` import（门禁 **G2**） |
| **T-6** | `harness/demo/graph_core.py` 的 **A5 组软断言**（`soft(...)` · `_B8F1_NOTE`） | 同一文件（`case_conditional_edges()` 的 A5 组：全部 `soft(...)` ⇒ **硬断言**（`check(...)` / `eq(...)`）⇒ 删除 `_B8F1_NOTE` 的「未交付」措辞） | **B8F1**（M2） | **替换为反面断言**（条件边已交付 ⇒ **不**判失败）· **拆分而不删**（保留「C8 fresh 读」「C7 list 形态」「C7 dict 形态」三条断言的**语义**）· ⚠️ **判据只可更严**（`soft` → 硬） |
| **T-7** | `harness/demo/agent_loop.py` 的 **B1 / B2 组软断言**（`soft(...)` · `_B8F1_NOTE` · `harness/demo/agent_loop.py:214-262`） | 同一文件（**B1「工具循环」**与 **B2「tool_calls 形状」**两组的全部 `soft(...)` ⇒ **硬断言** ⇒ ⇒ ⇒ 删除 `_B8F1_NOTE` 的「未交付」措辞） | **B8F1**（M2）· 本 feature 内闭合 | **替换为反面断言**（工具循环已可跑 ⇒ **不**判失败）· **拆分而不删**（保留五条断言的**语义**）· ⚠️ **判据只可更严**（`soft` → 硬）· ⚠️ **时序**：MUST 在**条件边路由求值就位**之后落地 |

**判据未被放宽的论证**：破面**只**放宽「**该字段非空是否构造期失败**」这一条**构造期守卫**
⇒ ⇒ ⇒ **路由求值本身有更强的判据**（SC-001…SC-026 全部新增/收紧）⇒ ⇒ ⇒ **零条既有判据被删**
⇒ ⇒ ⇒ 「拆分而不删」在**语义留存**与**判据强度**两个维度上均**只增不减**（宪法 v1.14.0）
⇒ ⇒ ⇒ 唯一的**收紧**在 T-6 / T-7（软断言 ⇒ 硬断言）与冻结断言 ④（恒空 ⇒ 非空且一致）。

**落点**：`tasks.md` 的一条**阻断合入**的追认任务 + 追认文字 MUST 落
`harness/verification/B8F1/manual-verification.md`（**追认文字 + 发起者确认 + 日期**）
⇒ **未追认前 MUST NOT 合入**。

**红线**：MUST **NOT** 在**本次追认额度用尽后**再破任何其它冻结面（**追认次数 MUST == 1** ⇒ ⚠️ **「≤ 1 次」是次数的额度** ⇒ 「7 类破面 + 1 次追认」**不**违反该额度）· MUST **NOT** 以「拆分而不删」为名**弱化**任何断言
（v1.14.0）· MUST **NOT** 改宪法正文 · MUST **NOT** 新增门禁编号 · MUST **NOT** 放宽任何门禁判据。

### ⚠️ 登记项 R-2（**门禁 3 的 `target.py` 部分 + **门禁 4 的验收基线 fake 轮** + 门禁 5 的真实模型轮** ⇒ 分阶段延后）

**依据**：宪法 **v1.6.0**「质量门禁的分阶段落地与发起者追认」（**窄口径**通则）——
被延后的 MUST 是「**门禁项中的某一部分**」· MUST **NOT** 是「整条门禁」⇒ ⇒ ⇒ **判据零放宽**。

| # | 被偏离的**具体门禁项** | 不可达成的根因 | 判据未被放宽的论证 | 承接方（feature ID + 里程碑） | 承接机制 |
|---|---|---|---|---|---|
| ① | **门禁 3** 的「**`harness/demo/target.py` 原样可跑**」 | 根因 = `harness/demo/target.py:163` 的 `draw_mermaid_png()` 属 **B23F1**（**未交付**）⇒ ⇒ ⇒ 脚本在 `:168` 的 `invoke()` **之前**中断 ⇒ ⇒ ⇒ 本 feature 再怎么改路由语义都**到不了**验收点（**不是**本 feature 按里程碑不交付其前置能力，而是**下一棒的图导出能力**未就绪） | 固定脚本**一字未改**（**T-4 不破**）⇒ ⇒ ⇒ 本 feature 的验收证据落在**可改的** `harness/demo/graph_core.py`（A5 组转**硬断言** ⇒ 由 `tests/runtime/test_acceptance_script.py` 在 CI 里以子进程跑并断言退出码 **0**）⇒ ⇒ ⇒ **判据未放宽**（软 ⇒ 硬 = **更严**） | **B22F1 + B23F1**（M2 · 立项书 §5.2） | **已就位**：本 feature 的下游承接 **D-4** MUST 写入 `harness/features/B22F1_get_graph与draw_mermaid.md` / `B23F1_draw_mermaid_png离线不阻断.md`（见**登记项 R-3**）⇒ 由其 spec 落成 FR + 裁定 |
| ② | **门禁 5** + 原则 V 的「**真实模型一轮**」 | 物理不可达成：需**真实模型**（`claude-sonnet-4-6`）+ **厂商端点**（出网 + 凭据）⇒ ⇒ ⇒ 本仓库的 CI 与门禁环境**无**该条件 | 「**验收基线 fake 轮**」（门禁 4 的 `target.py` 一轮）**本 feature 亦不可达**（见**登记项 R-2 ③** · `graph_core.py` 零第三方依赖 ⇒ **图能力侧**的等价证据，**不冒充**门禁 4 的 fake 轮）⇒ ⇒ ⇒ 五段式人工验证记录 + 来源覆盖表**照常落地**（SC-020）⇒ ⇒ ⇒ ⚠️ 若真实轮因环境不具备而无法完成 ⇒ MUST 按宪法 v1.6.0 **登记为环境偏离**并写明（**MUST NOT** 用「未验证」替代「已登记的环境偏离」）⇒ ⇒ ⇒ **判据本身不放宽**（fake 轮仍 MUST 跑通） | **B25F1**（M4 · 立项书 §5.2） | **已就位**：下游承接 **D-5** MUST 写入 `harness/features/B25F1_双跑验收与迁移说明.md`（见**登记项 R-3**）⇒ 由其 spec 落成 FR + 裁定 |
| ③ | **门禁 4** 的「**fake 模型跑通验收基线（`harness/demo/target.py`）的一轮**」（原则 V 的第 ① 轮） | **MVP 验收基线 = `harness/demo/target.py`**（原则 III）⇒ 该脚本在 `:163` 调 `draw_mermaid_png()`、在 `:168` 才 `invoke()` ⇒ ⇒ ⇒ **PNG 路径未交付（属 B23F1）** ⇒ ⇒ ⇒ 脚本**在到达验收点之前**中断 ⇒ 且 target.py 用**真实** `init_chat_model`（`:26`）⇒ ⇒ ⇒ **伪模型注入机制**不属本 feature（属 B25F1 的「双跑验收」）⇒ ⇒ ⇒ 门禁 4 的**验收基线 fake 轮**与门禁 3 的「原样可跑」**同根因** ⇒ ⇒ ⇒ `harness/demo/graph_core.py` 承担的是 立项书 S4 的**后半句**（图能力由零依赖验收脚本集独立验证）⇒ **不**构成门禁 4 的**验收基线 fake 轮** | CI **MUST NOT** 写一条永久红的断言（宪法 v1.6.0 红线）⇒ ⇒ ⇒ 门禁 4 的 **验收基线 fake 轮判据一字未改** ⇒ ⇒ ⇒ 本 feature 以 `graph_core.py` 的 A5 组**硬断言**（SC-015）与 `agent_loop.py` 的 **B1 / B2** 组**硬断言**（SC-025）交付**图能力侧**的等价证据 ⇒ ⇒ ⇒ 该证据**不冒充**门禁 4 的**验收基线 fake 轮** ⇒ ⇒ ⇒ ⚠️ **口径订正（2026-11-17 · 与 spec 的 SC-020 / Assumptions 对齐）**：本 feature 的「**fake 模型轮**」= **猴补（monkey-patch）`init_chat_model` + 含条件边的最小图 / `agent_loop.py` 的**工具循环轮** ⇒ ⇒ ⇒ **本 feature 可达** ⇒ ⇒ ⇒ MUST **真跑**并记录（SC-020 / SC-026 · 裁定 19）⇒ ⇒ ⇒ 被延后的**只是**「跑 `target.py` 验收基线」这一**部分**（⇒ **窄口径**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据未被放宽** ⇒ ⇒ ⇒ ⚠️ **本登记项内的两个「轮」MUST 带限定语**（2026-11-18 · analyse 轮补登记「术语双义消歧」）：**「验收基线 fake 轮」**（门禁 4 · 跑 `target.py` ⇒ **不可达** · 见 ② ③）与 **「fake 模型轮」**（**窄口径** ⇒ **可达** · 见 ③）⇒ ⇒ ⇒ **MUST NOT** 混用 | **B22F1 + B23F1**（M2 · PNG / `get_graph`）· **B25F1**（M4 · 伪模型注入 + 双跑验收） | **已就位**：B3F1 的裁定 22 已把「fake 轮 / 真实模型轮」的承接条款写入各目标 feature 的提示词初稿；本 feature **MUST NOT** 改动那些文件（只接线 · 见**登记项 R-3**） |

**落点**：`tasks.md` 的一条**阻断合入**的追认任务 + 追认文字 MUST 落
`harness/verification/B8F1/manual-verification.md`。

⇒ ⇒ ⇒ **门禁 4 的验收基线 fake 轮**与门禁 5 的真实模型轮**同属**本登记项
⇒ ⇒ ⇒ 两者**均**在 `harness/verification/B8F1/manual-verification.md` 中
⇒ ⇒ ⇒ **显式登记为未落地**并写明承接方
⇒ ⇒ ⇒ **追认文字 MUST 与 R-1 的追认分列**（R-1 = 破冻结面 · R-2 = 门禁延后）
⇒ ⇒ ⇒ ⚠️ **追认次数**：本 feature 的**破冻结面追认 == 1 次**（**R-1 并入 R-3 的追认文字**
⇒ ⇒ ⇒ ⇒ **同一次**发起者确认）⇒ ⇒ ⇒ **R-2 属「门禁偏离」类**（宪法 v1.6.0 处置方式）
⇒ ⇒ ⇒ ⇒ 该条**未对追认次数设上限** ⇒ ⇒ ⇒ ⇒ ⇒ **不**计入破冻结面额度
⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **全 feature 的确认动作 == 1 次**（R-1 / R-2 / R-3 三段落列于同一份记录
⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ · 一次确认 · 一个日期）

**红线**：MUST **NOT** 改宪法正文 · MUST **NOT** 写一条**永久红**的 CI（⇒ ⇒ A5 组转硬断言 MUST **排在**
条件边求值**就位之后**）· MUST **NOT** 把本条当作**长期豁免**（承接项 MUST 有具名承接方与里程碑）·
MUST **NOT** 放宽依赖红线 / 许可证红线 / 商标红线 / 零出站红线（**这四条在本 feature 照常执行**）。

### ⚠️ 登记项 R-3（**下游承接 D-1…D-5** 的跨 feature 文档接线）

**依据**：宪法 **v1.8.0**「跨 feature 承接的接线通则」——
本 feature 的规格中出现了**指名下一棒 feature（ID + 里程碑）**的跨 feature 义务（**D-1…D-5**）
⇒ ⇒ ⇒ 该条款 MUST 写入**目标 feature 的提示词初稿** ⇒ ⇒ ⇒ 由目标 feature 的 spec 落成 **FR + 裁定**
⇒ ⇒ ⇒ 其 tasks 与契约同步接线 ⇒ ⇒ ⇒ 本 feature 的 `plan.md` + `tasks.md` MUST 留**可勾选**条目。

| # | 承接方（feature ID + 里程碑） | 承接内容（**只接线** · 逐条最小改动） | 目标提示词初稿（**已存在**） |
|---|---|---|---|
| **D-1** | **B8F2**（M2） | `stream()` 的每一档 MUST 与本 feature 的 `invoke` **逐字同款**（**同一份**路由求值实现点 ⇒ **MUST NOT** 另写一份） | `harness/features/B8F2_stream多模式流式.md` |
| **D-2** | **B8F3**（M2） | 路由函数入参 = **fresh 视图** ⇒ `context` 通道（**C21**）MUST **NOT** 进入该视图；节点别名 MUST **NOT** 影响 `path_map` 查表（查表用**节点名**） | `harness/features/B8F3_节点别名与context通道.md` |
| **D-3** | **B11F1**（M1） | `Send` fan-out 的**调度归 B11F1** ⇒ 本 feature **只**把路由函数返回的 `Send` / `list[Send]` **喂进**既有 fan-out 任务构造器 ⇒ 两条来源 MUST 产出**同款**任务 | `harness/features/B11F1_Send动态fan-out.md` |
| **D-4** | **B22F1 + B23F1**（M2） | 图导出 MUST 能表达**条件边**（源节点 → 可能的多个目标）⇒ MUST 复用本 feature 的 `targets` / `route_channels` 口径 ⇒ **MUST NOT** 另算一份目标集合 | `harness/features/B22F1_get_graph与draw_mermaid.md` / `B23F1_draw_mermaid_png离线不阻断.md` |
| **D-5** | **B25F1**（M4） | fake 注入机制 MUST 与路由函数**正交**（路由函数**可以是**一个读状态的**假模型**） | `harness/features/B25F1_双跑验收与迁移说明.md` |

> ⚠️ **事实性核对（原则 VIII）· 已回写（2026-11-17 · R-4 的 C-4 / C-5）**：Phase 0 曾发现
> spec 的「下游承接条款」表把 **D-4 / D-5** 的里程碑写成 **M3**，而**仓库现状**
> （`harness/features/README.md` 与立项书 §5.2 的 feature 体量表）记的是
> **B22F1 = M2 · B23F1 = M2 · B25F1 = M4** ⇒ ⇒ ⇒ **spec 已回写**为 **M2 / M4**
> （= 本 plan 与仓库现状**一致**）⇒ ⇒ ⇒ 本 note 保留为**当时发现的历史事实**（原则 VIII 的
> 「现状」与「历史」**MUST 可区分**）⇒ ⇒ ⇒ **无需**再改判据。

**落点**：`tasks.md` 的**可勾选**接线任务（**1 条** · **T062** · 覆盖 **5** 条承接义务 /
**6** 份目标初稿）+ 一条**阻断合入**的追认任务（**T061**）⇒ ⚠️ **R-3 的追认文字 MUST 与 R-1 的
追认归并为同一次追认**（宪法 v1.8.0「破冻结面追认每 feature MUST ≤ 1 次」⇒ 跨 feature 文档改动
属「破冻结面」类 ⇒ **不另计次**）⇒ ⇒ ⇒ 追认文字 MUST 落
`harness/verification/B8F1/manual-verification.md`（**与 R-1 的追认段落同处一份文档**）
⇒ ⇒ ⇒ **发起者确认 + 日期只有一次**（**MUST NOT** 拆成两次确认）。

**红线**：MUST **NOT** 越界实现下一棒的动作（B8F2 的 `stream` / B8F3 的别名与 `context` /
B11F1 的 fan-out **调度** / B22F1 · B23F1 的图导出 / B25F1 的注入）· MUST **NOT** 新增门禁编号
（**G1–G30** 的连续性是不变量）· MUST **NOT** 放宽或稀释任何门禁判据 · MUST **NOT** 改动目标 feature
提示词初稿的**其余**内容（**只接线 · 逐条最小改动**）。

### ⚠️ 登记项 R-4（**Phase 0 实测发现的 spec 事实性表述更正** · 已回写 spec · 判据只收紧不放宽）

**依据**：宪法**原则 VIII**（事实性结论 MUST 附来源标记 · 事实性表述 MUST 准确）·
**原则 XI**「上游锚点纪律」（**行为**断言 MUST 有**实测**支撑 · **只读源码不足以支撑行为断言**）·
**原则 XII** 第 2 步（既有形态**不是**理由 ⇒ **该更正的必须更正**）·
本 plan 的「**绿基线记录 + 变红清单**」**同款纪律**。

> **实测环境**：`langgraph 1.2.11` / `langchain-core 1.7.6`（Phase 0 · 仓库外临时 venv）⇒
> 逐条证据见 `research.md` **§4** 的 **C-1…C-9** + **§2** 的实测基线表。

| # | spec 的原表述 | 实测真相 | 回写位置 | 对判据的影响 |
|---|---|---|---|---|
| **C-1** | spec 有 **5 处**写「**无** `path_map` + 返回**未注册节点名** ⇒ 上游抛 `KeyError`」 | 上游在该场景是**静默忽略**（只打一条 warning · 运行**成功** · 实测 E-8 / M-I）⇒ 上游对 `None` / `START` 才是 `ValueError`（M-B / M-D） | Edge Cases · 偏离登记 **X-3**（freegraph 的异常类型由 `KeyError` 改为 `ValueError` · 与 **FR-022 / SC-007 / D-111** 一致）· **User Story 4** 的 IT 与 AS2 · **Q7** 澄清块 | freegraph 侧仍为「**显式失败**」（**更严** ⇒ 偏离 **X-3** 不变）· 上游描述被订正 ⇒ **判据不变** |
| **C-2** | spec 把 `langgraph/graph/_branch.py:207-208` 当成「`END` 过滤」并称「上游只在『`END` 是 `path_map` 的 key』时终止」 | 上游**不在** `_branch.py` 里过滤 `END`（`:207-208` 是 `None` / `START` 的 `ValueError` 判定）⇒ 终止的**充要条件**是「**解析后的目的地**恰为 `'__end__'`」⇒ `END` 包在 `langgraph/graph/state.py:1592` 被剔除 ⇒ 实测 `path_map = {END: "b"}` ⇒ 上游**路由到 b · 不终止** ⇒「**无** `path_map` + 返回 `END`」⇒ 上游**正常终止** | **X-2** · **引文差异 3** · **裁定 5**（追加「上游真相」小句）· **P-08** · 澄清轮 **Q1** 的理由段 | freegraph 的「**单独返回** `END` ⇒ **无条件终止**」**不变**（仍是 DIFF · **X-2**）⇒ 仅订正上游机制的事实前提 |
| **C-3** | spec 的 Edge Cases 说返回的 `tuple` 可作**单个** `path_map` key | `tuple` / `list` 被 `_branch.py:199-200` 包成列表 ⇒ **逐元素**解释为**多目标** ⇒ `tuple` **不是**单个 key（实测 E-15 / E-31） | Edge Cases + **FR-020** 补事实性排除（`list` / `tuple` **除外** ⇒ 按 **FR-024** 解释为多目标） | 与 **FR-024**（序列 = 多目标）**一致** · 判词不变 |
| **C-4** | spec 的下游承接 **D-4** 记 **M3** | 实测 `harness/features/README.md:47-48` + 立项书 §5.2 ⇒ **B22F1 = M2 · B23F1 = M2** | 已回写（spec 的「下游承接条款」表） | 仅里程碑事实 · 承接方与承接机制不变 |
| **C-5** | spec 的下游承接 **D-3** 记 **B11F1 = M2** | 实测 `harness/features/README.md:40` ⇒ **B11F1 = M1** | 已回写（spec 的「下游承接条款」表） | 同上（仅里程碑事实 · 承接方与承接机制不变） |
| **C-6** | spec 未记「`path_map = None` + 路由函数带 `-> Literal[...]` 返回注解 ⇒ 上游**推断** `path_map` ⇒ 返回表外值 ⇒ `KeyError`」 | 上游确实如此（实测 E-33 ⇒ `KeyError('zz')`）⇒ **不是**「无 `path_map`」的静默忽略 | 已补记（spec **P-02** · 裁定 4 · Edge Cases） | freegraph 的 L3 **已同款**推断（`_normalize_path_map` · `src/freegraph/_stategraph.py:118-151`）⇒ **SAME** · 不新增要求 |
| **C-7** | **FR-030**（`Send` 失败信号「同一」）与 **B11F1** 的冻结面 **V-19 / V-21** 冲突（上游 `InvalidUpdateError` vs freegraph `ValueError`） | 实测 E-21 / E-22：上游 `Send`→`END` 抛 `InvalidUpdateError` · `Send`→未注册节点**静默忽略** | ⚠️ **处置已升级（2026-11-17 clarify 轮 · 用户拍板 Q4 = 选项 A）**：由「只登记」升级为 **正式偏离登记 X-6（STRICTER）/ X-7（DIFF）** + **差分场景 D-119 / D-120** ⇒ ⇒ ⇒ 判据**只收紧**（新增覆盖 · 判词新增 · **既有**判据零放宽）⇒ ⇒ ⇒ 本 feature MUST **NOT** 改 B11F1 的校验 | **登记项 R-6**（见下） |
| **C-8** | `RunnableCallable` 的权威源码位置写成 `langgraph/utils/runnable.py` | 权威位置是 `langgraph/_internal/_runnable.py:299`（`langgraph/utils/runnable.py` 仅为兼容再导出） | 已补进 **P-13** 的上游锚点 | 仅锚点订正（**P-13 = SAME** 不变） |
| **C-9** | 上游 `config` 参数的**注解匹配集**未钉死字符串槽（写成「字符串注解 ∨ PEP-604 等价形式」） | 匹配集恰为 **5** 元组（无注解 ∨ 类对象 `RunnableConfig` ∨ 字符串 `"RunnableConfig"` ∨ `Optional[RunnableConfig]` ∨ 字符串 `"Optional[RunnableConfig]"`）⇒ 字符串槽**只**含这两个字面量 ⇒ `"RunnableConfig \| None"` 这样的字符串**不被接受**（实测 P-A17） | 已把 freegraph 的对应口径（**FR-003** · **裁定 16** · Edge Cases）钉死为「每种载体类型**两个字面量**」 | 判据**只收紧**（判定集合被钉死）· 判词不变 |

**新增的差分场景**（证据补强 · 判词 **DIFF**）：

| 差分编号 | 场景 | 上游实测 | freegraph 侧 | 判词 | 为什么必须新增 |
|---|---|---|---|---|---|
| **D-118** | `path_map = {END: "b"}` + 路由函数返回 `END` | **解析后目的地 == "b"** ⇒ **不终止**（实测 E-3 / E-17 / E-35）⇒ ⇒ ⇒ 序列内的 `END` ⇒ **剔除**（不终止 · 上游同款）⇒ ⇒ ⇒ 故「**无条件终止**」的**准确**口径 = 「**单独返回** `END`」⇒ ⇒ ⇒ 判词**不变** | **单独返回** `END` ⇒ **无条件终止**（不路由到 `b`） | **DIFF**（**X-2**） | **D-110** 只锁「`path_map` **不含** `END` 键 ⇒ 上游 `KeyError`」这一例 ⇒ **X-2 的另一半原先无差分场景锁定** ⇒ 新增 **D-118** 补齐 |

> ⇒ 差分场景由 **15** 条增至 **16** 条（**SAME 12 / DIFF 3 / STRICTER 1**）⇒ ⇒ ⇒ ⚠️ **2026-11-17 clarify 轮后再次增至 18 条**（**SAME 12 / DIFF 4 / STRICTER 2** · 新增 **D-119 / D-120**）⇒
> ⇒ **判据只收紧**（新增覆盖 · 判词未放宽 · FR / SC / 裁定编号**零变动**）。

> **红线**：MUST **NOT** 以本登记项放宽任何判据（**FR / SC / 裁定 / 既有差分编号与判词零变动** ·
> 仅 **FR-020** 补了一条**事实性排除**、**FR-019** 的追溯表多挂 **SC-013**、差分场景 **+1** 条 ·
> ⚠️ 「零变动」指**既有**编号与判词 ⇒ ⇒ ⇒ **新增**编号（D-118 / D-119 / D-120）属**只收紧**）
MUST **NOT** 回头改写已发布的事实（原则 VIII）· MUST **NOT** 因此改动宪法正文 ·
MUST **NOT** 新增门禁编号 · MUST **NOT** 放宽任何门禁判据。

**追认**：本登记项属「**只更正事实**」⇒ **MUST NOT** 与 **R-1**（破冻结面）**混为一次**追认
⇒ ⇒ 本项 **不需要**发起者追认（**未破任何冻结面** · **未放宽任何判据**）；**R-1** 的追认仍为**唯一一次**。

**落点**：`spec.md`（已回写）· `research.md` §4 的 **C-1…C-9** ·
`contracts/upstream-parity.md` §2.1 的锚点复核备注 · `tasks.md` 的一条**复核**任务（**非**阻断合入）。

### ⚠️ 登记项 R-5（**上位文档（立项书）的过期口径** · 只登记 · **不**单方面修改）

**依据**：宪法**原则 VIII**（事实性表述 MUST 准确 · **已发布的事实**不单方面改写）·
**原则 XII** 第 2 步（既有形态**不是**理由 ⇒ **该更正的必须更正**）·
本 plan 的「**绿基线记录 + 变红清单**」**同款纪律**（**只登记 · 不改判据**）。

| 上位文档位置 | 现行措辞 | 本 spec 的口径与处置 |
|---|---|---|
| 立项书 **§5.2** 的 B8F1 行「小目标」列 | 含「**差分测试夹具建立**」；§4.2 **S5** 的脚注写「差分夹具在 **B5F2**（稀疏状态）与 **B8F1**（fresh 读）**首次建立**」 | 本 spec 的口径 = 条件边的**路由判定**差分落 **`tests/differential/parity_probe.py`**（**双真实实现**对跑 · 同一差分体系）⇒ B5F2 夹具的 `conditional_edges` 字段**保持恒空**（其 freegraph 侧驱动器是**线性替身** · 无调度能力 · 填值**无消费者**）⇒ ⇒ ⇒ **以立项书 §5.9 的 E-5（2026-11-12 ·「每个 feature MUST 有自己的场景组」）为准** ⇒ 判据**只收紧**（证据更全）⇒ **不**单方面修改立项书（属发起者职权） |
| 立项书 **§5.2** 的 B8F1 行「前置」列 | 「**B5F2, B7F1**」 | 本 spec 的承接条款 **H-1…H-11** 另含 **B6F1 / B7F2 / B7F3 / B7F4 / B9F1 / B11F1 / B3F1 / B10F1** ⇒ ⇒ ⇒ 立项书的「前置」列是**里程碑序**的简写 ⇒ spec 的承接条款为准 ⇒ **不**单方面修改立项书 |
| 本 spec 以 **D-103…D-120**（**18** 条 · 判词 **SAME 12 / DIFF 4 / STRICTER 2**）覆盖该判据并**超出**（含 `END` 终止 / 失败信号 / 双参 / `__start__` 条件边 / `Send` 失败信号） | —— | **判据只收紧**（证据更全）· **不**单方面修改立项书 |

**落点**：`research.md`（事实登记）· `harness/verification/B8F1/manual-verification.md`（**只登记**）·
`tasks.md` 的一条**复核**任务（**非**阻断合入）。

**红线**：MUST **NOT** 单方面修改立项书（属**发起者职权**）· MUST **NOT** 以本登记项放宽任何判据 ·
MUST **NOT** 改动本 feature 的判据口径（**FR / SC / 裁定 / 差分编号与判词全部零变动**）。


### ⚠️ 登记项 R-6（**`Send` 失败信号的偏离正式化** · 只收紧 · 无追认）

> **依据**：宪法**原则 XI 末条**（三态标注 MUST 一致 · 对照表与偏离登记 MUST 闭合）·
> **原则 VIII**（事实性结论 MUST 准确）· **原则 XII** 第 2 步（既有形态不是理由 ⇒
> 该更正的必须更正）· research **DR-6** / **C-7**。

| 项 | 内容 |
|---|---|
| **被遗漏的分叉** | 路由函数返回 `Send` 时，上游的**失败信号**与 freegraph **不同型**：① 上游 `Send` → **未注册节点** ⇒ **静默忽略**（实测 **E-22**）⇒ freegraph 抛内置 `ValueError`（B11F1 的 **V-19**）② 上游 `Send` → `END` ⇒ 抛 **`InvalidUpdateError`**（实测 **E-21**）⇒ freegraph 抛内置 `ValueError`（**V-21**） |
| **原处置** | research **DR-6** 与 R-4 的 **C-7** 记「**只登记 · 不改判据**」⇒ 该分叉既**不在** spec 的「偏离登记 X-1…X-5」，也**不在** `contracts/upstream-parity.md` 的 X 表 ⇒ 三态标注的「无漏行」口径**未闭合**（宪法原则 XI 末条） |
| **新处置** | ① spec 的「偏离登记」新增 **X-6**（`STRICTER`）与 **X-7**（`DIFF`）⇒ ② `contracts/upstream-parity.md` 的 §2 新增 **P-22 / P-23**（关系标注**逐字一致**）⇒ ③ §3 新增 **D-119 / D-120** ⇒ ④ 差分判词分布由 **SAME 12 / DIFF 3 / STRICTER 1** 变为 **SAME 12 / DIFF 4 / STRICTER 2** ⇒ ⑤ spec 的 **P-11** 补「`SAME` 仅指任务形态 / 载荷语义」的限定 |
| **判据未被放宽的论证** | 本项**只增**证据（**新增**差分场景 + **新增**偏离登记行）⇒ ⇒ ⇒ **既有** FR / SC / 裁定 / 差分编号与判词**零变动** ⇒ ⇒ ⇒ **零新增错误类型**（只用**内置** `KeyError` / `ValueError`）⇒ ⇒ ⇒ MUST **NOT** 改 B11F1 的冻结面（V-19 / V-21）⇒ ⇒ ⇒ **判据只收紧** |
| **追认** | **不需要** —— 本项**未破任何冻结面**（不改 B11F1 的冻结面 · 不改既有断言）· **未放宽任何判据** ⇒ ⇒ ⇒ **R-1 的追认仍为唯一一次** |
| **落点** | `spec.md`（偏离登记 X-6 / X-7 · 上游对照 P-22 / P-23 · 差分场景 D-119 / D-120）· `contracts/upstream-parity.md` §2 / §3 / §4（**双侧同改**）· `contracts/conditional-edge-contract.md` §8 · `tasks.md` 的 **T022**（差分场景落 `parity_probe.py`）与 **T065**（复核） |

### 门禁编号纪律

**本 feature MUST NOT 新增门禁编号** —— 既有 **G1–G30** 的编号连续性是 B3F1 data-model 的不变量
（「门禁总数 == 30 · 编号连续」）⇒ ⇒ ⇒ 新能力由**既有门禁自动覆盖**：

| 既有门禁 | 对本 feature 的覆盖 |
|---|---|
| **G25**（导入图单向 · ARCH-1） | 新增的 `src/freegraph/runtime/_routing.py` 落在 **L2**（层注册表已把 `src/freegraph/runtime/` 登记为**目录条目**）⇒ **自动纳入扫描**；L2 → L3/L4/L5 的边数 == 0。⚠️ **MUST NOT** 为该模块**单独立**注册表条目 ⇒ 会造成 L2 → L2 横向依赖误判 |
| **G30**（全仓署名头） | 新建源文件 `src/freegraph/runtime/_routing.py` 的署名头覆盖率 == 100% ⇒ **无需**扩 G5 / G20 的硬编码清单 |
| **G2**（契约层零内部 import） | `tests/contracts/**` **禁止** import `freegraph.*` ⇒ C8 的**实际回归用例 MUST 住 `tests/runtime/`** ⇒ 挂载点文件里只留**路径扫描**的**元测试** ⇒ **G2 恒绿** |
| **G29**（契约门禁载体 · C4 / C8 挂载点） | 本 feature 改动 `tests/contracts/test_contract_regressions.py:36` 的 `GATE-MOUNT: C8` 行（`not-landed` → `landed`）⇒ G29 的解析（`:127-144`）与判定（`:220-248`）**零改动** ⇒ 判定结果由 `not-landed` 变 `landed`（**这正是本 feature 的目标状态**） |
| **G9**（typing 构件上限 3.11） | 新模块的 typing 构件受检（AST 扫描 `src/freegraph/**`）· `inspect` 是**标准库**且 ≤ 3.11 |
| **G3 / G21 / G22 / G23**（零新增依赖） | `pyproject.toml` **零改动** ⇒ 依赖闭包 / 隔离环境 / 许可证断言恒绿 |
| **G4 / G24 / G26 / G27** | 零环境变量 / 零出站（FR-033 · SC-017） |
| **G7 / G15 / G19**（公开面） | 契约层 **21** 个 / 门面 **7** 个 / `freegraph.runtime` **23** 个符号**一字不动** ⇒ 新的 `_routing.py` 是 **L2 内部 API**（**不进** `__all__`）⇒ 兼容矩阵**零新增行** |

> **⇒ 门禁编号总数仍为 30**（layer-registry.md 与 data-model 的不变量**零改动**）。

### 设计后复核（Phase 1 后 · 模板要求「Re-check after Phase 1 design」）

| 复核项 | 结论 |
|---|---|
| 宪法条款 | **无 MUST 冲突** —— Phase 1 产出的 **5** 份工件（`research.md` / `data-model.md` / `contracts/`×2 / `quickstart.md`）**全部**落在 `specs/` 内 ⇒ 新增源码只在 `src/freegraph/runtime/` ⇒ 依赖 / 许可证 / 商标 / 零出站**四条红线**不受影响 |
| 门禁编号 | **仍为 30**（G1–G30）—— Phase 1 **未新增**任何门禁脚本或编号；新增的 `_routing.py` 由 **G25** 与 **G30** 自动覆盖 |
| 公开面 | **零变更** —— `freegraph.graph` **7** / `freegraph.runtime` **23** / 契约层 **21** 符号**一字不动**；`_routing.py` 是 **L2 内部 API** ⇒ 兼容矩阵**零新增行**（MUST 在人工验证记录里显式记「零新增」） |
| 编译产物持有面 | **仍为 11 键**（3 私有 + 8 公开）—— 路由求值复用既有的 `_conditional_edges` 与 `_spec` ⇒ **零新增**私有字段 ⇒ **T-3 不破** |
| 破面 | **仍为 7 类**（T-1 · 冻结断言 ① · ② · ④ · T-5 · T-6 · **T-7**）⇒ **追认次数 == 1** ⇒ **MUST NOT** 在额度用尽后再破任何其它冻结面 |
| Phase 1 的 5 份工件 | **全在 `specs/` 内** —— `research.md` / `data-model.md` / `contracts/conditional-edge-contract.md` / `contracts/upstream-parity.md` / `quickstart.md` ⇒ **不进发行包**（发布门禁 1 零影响） |
| 四条红线 | **不受影响** —— 依赖红线（`langsmith` / `langchain*` / `langgraph*`）· 许可证红线 · 商标红线 · 零出站红线 ⇒ 全部**照常执行** |
| 与上游的等价性 | `contracts/upstream-parity.md` 给出 **23** 条语义点（**P-01…P-23**）+ **18** 条差分场景（**D-103…D-120** · **新增 D-118 / D-119 / D-120** · 判词 **SAME 12 / DIFF 4 / STRICTER 2**）+ **7** 条偏离（**X-1…X-7**）⇒ 三态标注在两张表间**逐字一致**（宪法 v1.12.0 末条） |
| spec 的事实性更正 | Phase 0 实测发现 **9** 处 spec 的**事实性表述**需更正（`research.md` §4 的 **C-1…C-9**）⇒ **已回写 spec**（**只更正事实 · 判据零放宽**）⇒ **FR / SC / 裁定 / 引文差异 / P / X** 的**编号与总数零变动**（**R-4 自身零变动**；当前总数 = **FR 42 · SC 26 · 裁定 19 · 引文差异 16 · P 23 · X 7**）· 仅 **FR-020** 补一条**事实性排除**、**FR-019** 的追溯表多挂 **SC-013**、差分场景 **+1** 条⇒ 见**登记项 R-4** |
| 绿基线与变红清单 | **待实测填实** —— 实施**开始前** MUST 跑基线命令并记录计数 ⇒ ⇒ ⇒ 变红断言逐条带 `文件:行号` + 原因**写回**本节 ⇒ ⇒ ⇒ **MUST NOT** 只凭推理登记 |
| 遗留登记 | **DR-n**（Phase 0 的上游实测遗留 · 如 `local_read` 的 `managed` 语义 freegraph **不实现**）—— 全部**只登记 · 不改判据** |

---

## Project Structure

### Documentation (this feature)

```text
specs/b8f1-conditional-edges-fresh-read/
├── plan.md                          # This file (/speckit.plan command output)
├── research.md                      # Phase 0 —— 上游取证 + 遗留登记（DR-n）
├── data-model.md                    # Phase 1 —— 实体模型 + 求值状态机 + 校验规则
├── quickstart.md                    # Phase 1 —— 可照抄的验证手册（闸口 V1…Vn）
├── contracts/
│   ├── conditional-edge-contract.md # Phase 1 —— 条件边求值契约（**唯一权威**）
│   └── upstream-parity.md           # Phase 1 —— 对照 P-01…P-23 + 差分 D-103…D-120
├── spec.md                          # 规格（19 条裁定 · FR-001…FR-042 · SC-001…SC-026）
├── checklists/
│   └── requirements.md              # 规格质量清单
└── tasks.md                         # Phase 2（/speckit.tasks —— 本命令**不**生成）
```

### Phase 1 的产物落点（**5 份工件已产出** · 2026-11-17 → 2026-11-18 · 本次任务**只**修订 `plan.md`）

> ⚠️ **2026-11-18 · analyse 轮事实订正**（原则 VIII）：本节原写「以下 5 份工件**由后续任务写**」
> ⇒ ⇒ ⇒ 但它们**已全部落盘**（`research.md` / `data-model.md` / `contracts/`×2 / `quickstart.md` ·
> mtime 2026-11-17 → 2026-11-18）⇒ ⇒ ⇒ 本 plan 的「Project Structure」与 `tasks.md` 的
> Prerequisites **均以「已存在」为前提** ⇒ ⇒ ⇒ **MUST NOT** 把它们当待办 ⇒ ⇒ ⇒
> 实施期若发现漂移 ⇒ MUST **回写对应工件**（双份维护 · 同步义务）。

| 工件 | 主题 | MUST 含 | 状态 |
|---|---|---|---|
| `research.md` | Phase 0 的**上游取证**（`langgraph 1.2.11` 的**仓库外临时 venv** 实测）+ **遗留登记** | 每条决策附**实测方法 + 真实输出**（上游 `路径:行号`）· **DR-n** 遗留 · 事实订正（原则 VIII） | ✅ **已产出** |

| `data-model.md` | **条件边实体模型** + **路由求值状态机** + **载荷形态** + **校验规则** + **不变量** | 5 键载荷的字段语义 · 求值落点（阶段 ③′ / 阶段 ① 之前）· `path_map` 两形态 · 目标解析规则 · 不变量编号 | ✅ **已产出** |

| `contracts/conditional-edge-contract.md` | **条件边求值契约**（**唯一权威**） | 操作面（求值时机 / fresh 读 / 目标解析 / 失败信号 / `__start__`）· 校验规则（**V-8 已放宽**）· 不变量 | ✅ **已产出** |

| `contracts/upstream-parity.md` | **上游对照表**（**P-01…P-23**）+ **差分场景索引**（**D-103…D-120**）+ **偏离登记**（**X-1…X-7**）+ **三态一致性** | 两张表的 `SAME` / `STRICTER` / `DIFF` 标注**逐字一致**（宪法 v1.12.0 末条）· ⚠️ **双份维护**（发现漂移 MUST 双侧同改） | ✅ **已产出** |

| `quickstart.md` | 可照抄的**验证手册**（闸口 **V1…Vn**） | 每条闸口的**命令** + **期望输出** + 对应 SC | ✅ **已产出**（**V1…V16**） |


### Source Code (repository root)

```text
src/freegraph/
├── __init__.py                      # 既有 · **零改动**（顶层包惰性 · G1 / L-1）
├── graph.py                         # 既有 · **零改动**（门面 **7** 符号面 · G15 / G19）
├── _stategraph.py                   # ★ **改**（L3 接线）—— 见下方「接线落点」
├── contracts/                       # L1 契约层 · **零改动**（**21** 符号面 · G7 / G8）
└── runtime/                         # L2 执行内核层（层注册表已登记为**目录条目**）
    ├── __init__.py                  # 既有 · **零改动**（导出面仍 **23** 符号）
    ├── read.py                      # 既有（B5F2）· **零改动** —— **复用** fresh 读
    ├── superstep.py                 # ★ **改** —— 移除 V-8 守卫 + 两处求值落点
    └── _routing.py                  # ★ **新增**（L2 私有 · 路由求值与目标解析）

tests/
├── runtime/                         # 内核用例（**G2**：C8 的实际回归用例 MUST 住这里）
│   ├── conftest.py                  # 既有（B4F1）· **零改动** —— 复用子进程夹具
│   ├── test_conditional_edges.py    # ★ **新增** —— 求值 / fresh 读 / 目标 / 失败信号
│   ├── test_conditional_edge_contract.py
│   │                                # ★ **新增** —— **契约守卫**（解析契约的不变量）
│   ├── test_conditional_edge_surface.py   # ★ **新增** —— 零新增面断言（导出面 7/23/21 · 持有面 11 键）
│   ├── test_manual_record_guard.py  # ★ **新增** —— **文档守卫断言**（SC-019 / SC-020 / SC-026）
│   ├── test_read_fresh.py           # ★ **改** —— fresh 读在路由场景下的断言补充
│   ├── test_superstep_basic.py      # ★ **改** —— 冻结断言 ①（:557-576 · **拆分而不删**）
│   ├── test_superstep_contract.py   # ★ **改** —— 冻结断言 ②（**I-14** · 槽位不变）
│   └── test_acceptance_script.py    # 既有（B13F1）· **零改动** —— 断言退出码 == **0**
├── differential/
│   ├── parity_probe.py              # ★ **改** —— 差分场景组 **D-103…D-120**（**18** 条）
│   ├── spec_builder.py              # 既有（B5F2）· **零改动** —— **V-4** ⇒ **T-2 不破**
│   ├── test_differential.py         # 既有（B5F2）· **零改动** —— 冻结断言 ③ **逐字不动**
│   └── driver.py                    # 既有（B5F2）· **零改动** —— **线性替身**（无调度）
├── facade/
│   └── test_compiled_graph.py       # ★ **改** —— 冻结断言 ④（**替换为反面断言**）
├── contracts/
│   └── test_contract_regressions.py # ★ **改** —— C8 挂载点 + **新增** C8 元测试
└── gates/                           # 既有（G21–G30）· **零改动**

harness/
├── demo/
│   ├── graph_core.py                # ★ **改** —— **T-6**：A5 组 ⇒ **硬断言**（有时序）
│   ├── agent_loop.py                # ★ **改** —— **T-7**：B1 / B2 组 ⇒ **硬断言**（有时序 · EV-2 承接）
│   └── target.py                    # 既有 · **一字不改**（只读基准 · **T-4** 不破）
└── verification/B8F1/
    └── manual-verification.md       # ★ **新增** —— 五段式 + **发起者追认**（**唯一一次**）

README.md                          # ★ **改** —— API 兼容矩阵章节「零新增公开 API 行」（T063）

harness/features/
├── B8F2_stream多模式流式.md           # ★ **改**（下游承接 **D-1** · 只接线 · R-3）
├── B8F3_节点别名与context通道.md       # ★ **改**（下游承接 **D-2** · 只接线 · R-3）
├── B11F1_Send动态fan-out.md           # ★ **改**（下游承接 **D-3** · 只接线 · R-3）
├── B22F1_get_graph与draw_mermaid.md   # ★ **改**（下游承接 **D-4** · 只接线 · R-3）
├── B23F1_draw_mermaid_png离线不阻断.md  # ★ **改**（下游承接 **D-4** · 只接线 · R-3）
└── B25F1_双跑验收与迁移说明.md         # ★ **改**（下游承接 **D-5** · 只接线 · R-3）

specs/b7f1-superstep-loop/            # ★ **改** —— 破冻结面 **T-1** 的「契约 + spec」回溯修订（T069）
├── contracts/superstep-contract.md   # ★ **改** —— §2.1 的「条件边」行 + §2.1.1 的 **V-8** 行
├── spec.md                           # ★ **改** —— **FR-033** / **裁定 25** 行
└── data-model.md                     # ★ **改** —— **V-8** 行
```

**改动的代码锚点**（`★` 行的逐条说明 · 与「技术方案」表同源）：

> ⚠️ **本表 = 改动**的**要点**摘录（**13** 行）⇒ ⇒ ⇒ **完整**的触及面清单以 `tasks.md`
> 的 **75** 条任务（各自带精确文件路径）为准 ⇒ ⇒ ⇒ 两者**必须**在实现期逐条对照
> （漂移 ⇒ 以 `tasks.md` 为准并回写本表）。

| 文件 | 改动锚点 | 改动内容 |
|---|---|---|
| `src/freegraph/_stategraph.py` | `_graph_spec_from()`（`:175-202`）· `_conditional_mapping()`（`:205-225`）· `compile()`（`:667-714` · `_graph_spec_from` 调用在 `:692` · `_conditional_mapping` 调用在 `:693`） | 把 `_conditional_mapping()` 的结果**填入** `GraphSpec.conditional_edges` ⇒ ⇒ **接线方式 = 给 `_graph_spec_from()` 加 `conditional_edges` 形参**（由 `compile()` 传入 ⇒ **一次求值**）⇒ ⇒ ⚠️ **MUST NOT** 构造后赋值（`GraphSpec` 是 frozen dataclass）⇒ ⇒ ⇒ docstring `:186` 的「**不传**」口径同步订正 |
| `src/freegraph/runtime/superstep.py` | V-8 守卫（`:484-487`）· `_run_round` 的**阶段 ③′**（`:1253-1267`）· `run_super_step`（`:1364`） | ① **移除** V-8 守卫 ② 阶段 ③′ 增加路由求值 ③ 阶段 ① **之前**增加入口哨兵的路由求值 |
| `src/freegraph/runtime/_routing.py` | 全新文件 | L2 私有：调用形态判别 · fresh 视图构造 · 返回值归一 · `path_map` 查表 · 目标序列解析 ⇒ ⇒ **不进** `freegraph.runtime.__all__` |
| `tests/runtime/test_conditional_edge_surface.py` | 全新文件 | 零新增面断言：`freegraph.graph` **7** 符号 · `freegraph.runtime` **23** 符号 · 契约层 **21** 符号 · `vars(compiled)` == **11** 键（单一事实源 = `tests/runtime/_runtime_export_manifest.py`） |
| `tests/runtime/test_superstep_basic.py` | `:557-576` | 冻结断言 ① · **拆分而不删** |
| `tests/runtime/test_superstep_contract.py` | `:77`（**I-14** 映射）+ `:609-617`（用例体） | 冻结断言 ② · **编号与槽位不变** ⇒ 契约守卫解析范围**零改动** |
| `tests/facade/test_compiled_graph.py` | `:263-265` | 冻结断言 ④ · **替换为反面断言**（非空且与 `_conditional_edges` 一致）⇒ `:111-114` 的 11 键持有面**零改动** |
| `tests/contracts/test_contract_regressions.py` | `:36` + `:85-91` | C8 挂载点翻为 `status=landed` + **新增** C8 元测试（**路径扫描** · **零** `freegraph.*` import） |
| `harness/demo/graph_core.py` | `case_conditional_edges()`（`:254-321`） | A5 组全部 `soft(...)` ⇒ **硬断言**（`check` / `eq` · `:79-105`）⇒ ⇒ **时序**：求值就位之后 |
| `harness/demo/agent_loop.py` | B1 / B2 两组（`:214-262` · `_B8F1_NOTE`） | **破冻结面 T-7**：全部 `soft(...)` ⇒ **硬断言**（`eq(...)`）⇒ ⇒ **时序**：求值就位之后 ⇒ ⇒ **EV-2 承接** |
| `tests/runtime/test_manual_record_guard.py` | 全新文件 | **文档守卫断言**：记录存在且正文非空 · 两轮**非空**实测输出 · 追认文字含破面全集 **7** 类（**SC-019 / SC-020 / SC-026**）⇒ ⇒ **MUST** 在 T058…T061 之后才转绿 |
| `README.md` | 「API 兼容矩阵」章节 | 显式记录「本 feature **零新增**公开 API 行」+ 复核 `THIRD_PARTY_NOTICES` **零新增**（T063 · 原则 X） |
| `specs/b7f1-superstep-loop/{contracts/superstep-contract.md, spec.md, data-model.md}` | `superstep-contract.md` §2.1「条件边」行 + §2.1.1 的 **V-8** 行 · `spec.md` **FR-033** / **裁定 25** 行 · `data-model.md` **V-8** 行 | **回溯修订**破冻结面 **T-1** 的「契约 + spec」两面（宪法 v1.9.0 ①）⇒ **拆分而不删**（原「恒空即失败」行**保留**并标注「**自 B8F1 起放宽**：允许非空 · 由路由求值消费」）⇒ 其余 **V-1…V-3** 逐字不动（T069） |

**Structure Decision**:

- **路由求值落 `src/freegraph/runtime/superstep.py` 的既有阶段**（**阶段 ③′**）——
  理由：spec 裁定 1（MUST NOT 另开「条件边专用」的调度路径）+ 宪法原则 XI「照抄上游」
  （上游的分支是**源节点的 writer** · `langgraph/graph/state.py:1624`）⇒ ⇒ 求值 MUST 与
  「源节点任务成功落回」在**同一条**执行路径上 ⇒ ⇒ ⇒ 「节点挂起（`interrupt()`）⇒ 不成功落回
  ⇒ 路由函数**不被求值**」自然成立（承接 **H-10**）⇒ ⇒ ⇒ **零新增调度路径**。
- **新增 `src/freegraph/runtime/_routing.py`（L2 私有 · 路由求值与目标解析）** ——
  理由：路由求值涉及**五件事**（调用形态判别 / fresh 视图构造 / 返回值归一 / `path_map` 查表 /
  目标序列解析）⇒ ⇒ 若全部塞进 `superstep.py` ⇒ 该文件已 **2100+ 行**且承载**七阶段**调度
  ⇒ ⇒ ⇒ 继续堆叠会**淹没**调度语义 ⇒ ⇒ ⇒ 拆出**私有模块** ⇒ ⇒ ⇒ **零公开面影响**：
  ⚠️ 它**不进** `freegraph.runtime.__all__`（导出面仍 **23** 个符号）⇒ ⇒ ⇒ **L2 内部 API**
  ⇒ ⇒ ⇒ 兼容矩阵**零新增行** ⇒ ⇒ ⇒ **G7 / G15 / G19 恒绿**。
  ⚠️ **MUST NOT** 为它**单独立**层注册表条目（会造成 L2 → L2 横向依赖误判 · 同 B7F1 的处置）。
- **接线落 `src/freegraph/_stategraph.py`（L3）** —— 理由：`GraphSpec.conditional_edges` 的**载荷形态**
  已由 L3 的 `_conditional_mapping()`（`:205-225`）产出 ⇒ ⇒ ⇒ L2 MUST **NOT** 重新归一化
  （H-3 / H-4 · 裁定 4）⇒ ⇒ ⇒ 也 MUST **NOT** import `freegraph._stategraph`
  （或 `_ConditionalEdgeSpec`）（层纪律 · **G25**）⇒ ⇒ ⇒ 方向仍是 **L3 → L2**（既有方向 · 无新增反向依赖）。
- **fresh 读复用 `read.py` 的 `local_read`（不另写一份）** —— 理由：C8 的契约边界是
  「路由函数收到的状态」⇒ ⇒ 而 fresh 合并逻辑**只有一处实现**（B5F2 的 `_fresh_read` · 逐通道 copy ⇒ 零污染）
  ⇒ ⇒ ⇒ 调度层复用它 ⇒ ⇒ ⇒ 「fresh 语义」**不可能**在调度层漂移 ⇒ ⇒ ⇒ **FR-007** 可判定。
- **触发投递复用 `SchedulerState.dynamic_edges`（不另写机制）** —— 理由：freegraph 的触发源恒为**边**
  （B7F1 契约 §3.0「上游对齐 P1-0」）⇒ ⇒ 上游的「`branch:to:` 通道触发」≡ freegraph 的**边触发**
  ⇒ ⇒ ⇒ 且**零新增编译产物私有字段** ⇒ ⇒ ⇒ **T-3 不破**（`vars(compiled)` 仍 == **11** 键）。
- **差分落 `tests/differential/parity_probe.py`（不重造夹具）** —— 理由：B5F2 的 freegraph 侧驱动器
  `tests/differential/driver.py` 是**线性替身**（无调度能力 · 其模块 docstring 明文「MUST NOT 含调度逻辑」）
  ⇒ ⇒ 给它加分支调度 = **在测试替身里重写一遍生产调度器**⇒ ⇒ ⇒ 两个调度器必然漂移 ⇒ ⇒ ⇒
  ⇒ 测到的就不再是「上游 vs freegraph」⇒ ⇒ ⇒ **不是更优秀的设计**（宪法原则 XII「最优设计优先」）
  ⇒ ⇒ ⇒ 而 `parity_probe.py` 已是「**双真实实现**对跑」的载体 ⇒ ⇒ ⇒ 条件边的路由判定**属于**那里
  ⇒ ⇒ ⇒ **V-4 无需放宽**（裁定 15）⇒ ⇒ ⇒ **T-2 与冻结断言 ③ 均不破**。
- **C8 的**实际**回归用例住 `tests/runtime/`、**元测试**住 `tests/contracts/`** —— 理由：门禁 **G2**
  扫描 `tests/contracts/**` 并禁止 `freegraph.*` import ⇒ ⇒ ⇒ C8 的断言本体 MUST 在 `tests/runtime/`
  ⇒ ⇒ ⇒ 而 `tests/contracts/` 只留**路径扫描**的**元测试**（参照 `C4_REGRESSION_RELPATH` 的既有写法）
  ⇒ ⇒ ⇒ **G2 恒绿** ⇒ ⇒ ⇒ **门禁 29** 的挂载点判定亦可判。
- **两份契约**（`conditional-edge-contract.md` / `upstream-parity.md`）—— 沿用 **B3F1 的层注册表先例** +
  **B5F1 / B5F2 / B7F1 的契约先例**（机器可读 Markdown + `<!-- authority: yes -->` 标记）：
  ① `conditional-edge-contract.md` 是**判据**（**唯一权威**）；② `upstream-parity.md` 是**证据表**
  （逐条 `路径:行号` + 差分场景索引 + 偏离登记）⇒ **MUST NOT** 被测试解析
  （测试**直接断言行为** ⇒ 避免「判据与实现同源 ⇒ 自证」）。

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**本 feature 零违反** —— 全部语义**照抄上游**（宪法原则 XI）⇒ ⇒ ⇒ 唯一的自由裁量在**载体形态**上
（双参的第二参内容 + `config` 的注解匹配集 ⇒ 已如实登记为偏离 **X-5** · DIFF · 非更严）
⇒ ⇒ ⇒ **无一条「必须自研区」之外的自创行为** ⇒ ⇒ ⇒ 因此本表**不填违反项**，
只列**登记项**（**登记项 ≠ 违反** —— 它们是宪法 v1.6.0 / v1.8.0 要求的**可审计留痕**）：

| 登记项 | 依据（宪法条款） | 被偏离的具体项 | 根因 | 判据未被放宽的论证 | 承接方（feature ID + 里程碑） | 承接机制 | 落点 | 红线 |
|---|---|---|---|---|---|---|---|---|
| **R-1** | v1.8.0「破冻结面的三条」（登记 + 回溯修订 + 发起者追认 · 追认 ≤ 1 次） | **7 类**冻结面：T-1（V-8）· 冻结断言 ① · ② · ④ · T-5（C8 挂载点）· T-6（A5 组软断言）· **T-7**（`agent_loop.py` 的 B1 / B2 组软断言 · EV-2 承接） | freegraph 原先缺的是「**条件边求值**」⇒ ⇒ 上游 `langgraph 1.2.11` **有**全部条件边语义 ⇒ ⇒ ⇒ 属「**上游有此项 ⇒ freegraph 原先缺**」 | 破面**只**放宽「该字段非空是否构造期失败」这一条**构造期守卫**⇒ ⇒ ⇒ **零条既有判据被删** ⇒ ⇒ ⇒ 「拆分而不删」在**语义留存**与**判据强度**两个维度上均**只增不减**（v1.14.0）⇒ ⇒ ⇒ 唯一**收紧**在 T-6 / T-7（软 ⇒ 硬）与冻结断言 ④（恒空 ⇒ 非空且一致） | **B8F1**（M2）· 本 feature 内闭合 | 破面清单**全部**落在**同一次**登记 + 回溯修订 + 发起者追认里 ⇒ ⇒ 追认次数 == **1** | `tasks.md` 的**阻断合入**追认任务 + `harness/verification/B8F1/manual-verification.md` | MUST **NOT** 在**额度用尽后**再破任何其它冻结面（**追认次数 == 1**）· MUST **NOT** 弱化任何断言 · MUST **NOT** 改宪法正文 |
| **R-2** | v1.6.0「质量门禁的分阶段落地与发起者追认」（窄口径 · 被延后的是**门禁项的某一部分**） | ① 门禁 3 的「`harness/demo/target.py` 原样可跑」② 门禁 5 + 原则 V 的「真实模型一轮」③ 门禁 4 + 原则 V 的「**验收基线 fake 轮**」 | ① `target.py:163` 的 `draw_mermaid_png()` 属 **B23F1**（未交付）⇒ ⇒ 脚本在 `:168` 的 `invoke()` **之前**中断 ② 需**真实模型** + 厂商端点（出网 + 凭据）⇒ ⇒ 本环境不具备 ③ 验收基线 = `target.py` ⇒ 与 ① **同根因**（PNG 路径未交付） | ① 固定脚本**一字未改** ⇒ ⇒ 验收证据落在**可改的** `graph_core.py`（A5 组转**硬断言** ⇒ 更严）⇒ ⇒ 门禁 3 的 **C4 / C8 两条独立回归**在本 feature **全绿** ⇒ ⇒ 门禁 4 的 **fake 模型轮**在本 feature **不可达**（见**登记项 R-2 ③** · `graph_core.py` 零第三方依赖 ⇒ **图能力侧**的等价证据，**不冒充** fake 轮）⇒ ⇒ ⇒ **判据未放宽** ② fake 轮**仍 MUST 跑通** ⇒ ⇒ ⇒ 五段式记录**照常落地**⇒ ⇒ ⇒ 若真实轮无法完成 ⇒ MUST 登记为**环境偏离**（MUST **NOT** 用「未验证」替代） | ① **B22F1 + B23F1**（M2）② **B25F1**（M4）③ **B22F1 + B23F1**（M2）· **B25F1**（M4） | 下游承接 **D-4 / D-5** MUST 写入目标 feature 的提示词初稿（见 **R-3**）⇒ ⇒ 由其 spec 落成 FR + 裁定 ⇒ ⇒ tasks 与契约同步接线 | `tasks.md` 的**阻断合入**追认任务 + `harness/verification/B8F1/manual-verification.md` | MUST **NOT** 改宪法正文 · MUST **NOT** 写**永久红**的 CI · MUST **NOT** 当作长期豁免 · 四条**红线**照常执行 |
| **R-3** | v1.8.0「跨 feature 承接的接线通则」（条款 MUST 写入目标 feature 的提示词初稿） | **D-1…D-5** 共 **5** 条下游承接义务（B8F2 / B8F3 / B11F1 / B22F1 + B23F1 / B25F1） | 本 feature **冻结**「路由求值 + fresh 读 + 目标解析 + 失败信号」这组**跨 feature 接口** ⇒ ⇒ 后续 feature MUST 按同款口径承接 ⇒ ⇒ 接线动作属**跨 feature 文档改动** | **只接线 · 逐条最小改动** ⇒ ⇒ ⇒ 目标 feature 的提示词初稿的**其余内容一字不动**⇒ ⇒ ⇒ **零新增门禁编号**（**G1–G30** 的连续性是不变量）⇒ ⇒ ⇒ **零放宽**任何门禁判据 ⇒ ⇒ ⇒ 本 feature **不越界**实现下一棒的动作 | **B8F2**（M2）· **B8F3**（M2）· **B11F1**（M1）· **B22F1 + B23F1**（M2）· **B25F1**（M4） | 5 条**可勾选**接线任务（`tasks.md`）⇒ ⇒ 目标 feature 的 spec 落成 **FR + 裁定** ⇒ ⇒ 其 tasks 与契约同步接线 | `tasks.md` 的**可勾选**接线任务（**T062** · 覆盖 5 条承接义务 / 6 份初稿）+ **阻断合入**追认任务（**T061** · **并入 T059 的同一次追认** · **不另计次**）+ `harness/verification/B8F1/manual-verification.md` | MUST **NOT** 越界实现 · MUST **NOT** 新增门禁编号 · MUST **NOT** 放宽判据 · MUST **NOT** 改动目标初稿的其余内容 |

> ⚠️ **上游承接（**H-1…H-11**）不需要登记项**：它们全部指向**已交付**的 feature
> （B7F1 / B5F2 / B7F2 / B6F1 / B7F3 / B7F4 / B9F1 / B11F1 / B3F1 / B10F1）⇒ ⇒ ⇒ 属**已发布的事实**
> （宪法原则 VIII）⇒ ⇒ ⇒ 本 feature 只需**消费** ⇒ ⇒ ⇒ **MUST NOT** 回头改写已发布的事实。

---

## ⚠️ 本 plan 阶段的「零实测」声明

> 本 plan 阶段**未改动任何源码** ⇒ ⇒ ⇒ **绿基线计数尚未取得** ⇒ ⇒ ⇒ 「绿基线记录 + 变红清单」
> 一节的**变红清单是「预登记」**（依据 = spec 的破面清单 + 已核实的代码锚点）
> ⇒ ⇒ ⇒ **MUST NOT** 凭它追认 ⇒ ⇒ ⇒ 实测（实施**开始前**的基线跑 + 改动后的重跑）
> MUST 在**发起者追认开始前**把本节填实（宪法 v1.11.0 的基线义务）。
