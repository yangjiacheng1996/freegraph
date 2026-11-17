<!-- authority: yes -->

# 条件边契约（Conditional-Edge Contract）—— B8F1 的**唯一权威**

**Feature**: `B8F1` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**数据模型**: [../data-model.md](../data-model.md)
**核实环境**: CPython **3.11.16** · 上游 `langgraph` **1.2.11** + `langchain-core` **1.7.6**
（取证于 2026-11-17）

> **本文件是「条件边路由求值长什么样、怎么用」的**唯一权威**（沿用 B3F1 的层注册表先例：
> 机器可读 Markdown + `<!-- authority: yes -->` 标记；与 B7F1 的 `superstep-contract.md` /
> B5F2 的 `read-contract.md` **同款形态**）。
> **spec** 讲「**要什么**」（需求与判据）· 本文件讲「**是什么**」（**逐字冻结的数据契约**）。
> ⚠ 两者冲突时以 **spec** 为准（spec 是上位文档），并 MUST 回修本文件。
> ⚠ **本契约 MUST NOT** 被测试**解析**其 Markdown 文本以外的「同源事实」——
> 测试**断言行为**（可观察语义）· 本文件是**判据**· `upstream-parity.md` 是**证据**。
>
> **落位**：求值落 **L2**（`src/freegraph/runtime/`）· 接线落 **L3**（`src/freegraph/_stategraph.py`）
> ⇒ 新模块 `src/freegraph/runtime/_routing.py` 是 **L2 私有** ⇒ **不进** `freegraph.runtime.__all__`
> ⇒ **零新增公开面**（§9）。

---

## 1. 签名与载体

| 项 | 契约 |
|---|---|
| 宿主模块 | `freegraph.runtime._routing`（L2 · **私有** · **不进** `__all__`）· ⚠ **MUST NOT** 为它**单独立**层注册表条目（层纪律 · G25 · ARCH-1） |
| 求值落点 | **L2** `run_super_step` / `run_super_steps` 内部的**阶段 ③′「判定与落回」**（`src/freegraph/runtime/superstep.py:1253-1267`）⇒ MUST **NOT** 另开一条「条件边专用」的调度路径（FR-002 · 裁定 1） |
| 载荷载体 | `GraphSpec.conditional_edges`（`superstep.py:219`）· 外层 key = **源节点名** · 内层 = **tuple**（顺序 = **登记顺序**）· 每项 = **恰 5 键** plain mapping |
| 分支项的五键 | `branch`（`str`）· `path`（`Callable[..., Any]`）· `path_map`（`dict[Hashable, str] \| None`）· `targets`（`tuple[str, ...]`）· `route_channels`（`tuple[str, ...]`） |
| 载荷产出 | **L3** 的 `_conditional_mapping()`（`src/freegraph/_stategraph.py:205-225`）⇒ L2 MUST **只**消费本字段（FR-014）⇒ MUST **NOT** import `freegraph._stategraph` / `_ConditionalEdgeSpec` |
| 归一化 | `path_map` 在 L2 **只有** **dict**（已归一化）与 **`None`** 两形态 ⇒ MUST **NOT** 重新归一化（FR-014 / FR-016 · 裁定 4）· list ⇒ `{name: name}` 已在 L3 完成（实测 **E-18**） |
| 路由函数形态 | **单参** `f(fresh_view)` 或 **双参** `f(fresh_view, config)` ⇒ MUST 支持两形态（FR-003 · 裁定 12） |
| 双参判别 | **第二参的参数名是 `config`**（**不是**位置参数个数）⇒ 永远只传**一个**位置实参（fresh 视图）⇒ `config` 以**关键字**注入（裁定 16） |
| 依赖 | **只依赖标准库**（`inspect` · `collections.abc` · `typing`）· MUST NOT import 第三方（FR-033） |

### 1.1 双参判别矩阵（**照抄上游** · 上游 `langgraph/_internal/_runnable.py:299` / `:341-365`）

| 路由函数形态 | freegraph 的调用 | 上游的观察 | 依据 |
|---|---|---|---|
| `f(state)` | **一参**调用 | OK | 上游同款 · 实测 **P-A01** |
| `f(state, cfg)`（第二参**不叫** `config`） | **一参**调用 ⇒ `TypeError` | `TypeError`（**不**凭位置补传） | 实测 **P-A02** · 上游同款 |
| `f(state, config)`（**无注解**） | 一参 + `config=` **关键字**注入 | OK | 实测 **P-A03** |
| `f(state, config: RunConfig)` / `config: Mapping[str, Any]`（**类对象**） | 同上（**注入**） | OK（上游的对应类对象是 `RunnableConfig`） | 实测 **P-A12** · 匹配集**同形**（裁定 16） |
| `f(state, config: "RunConfig")` / `"Optional[RunConfig]"` / `"Mapping[str, Any]"` / `"Optional[Mapping[str, Any]]"`（**字符串**） | 同上（**注入**） | OK（上游的字符串槽只含 `"RunnableConfig"` / `"Optional[RunnableConfig]"`） | 实测 **P-A13 / P-A15** · 字符串槽**每种载体两个字面量** |
| `f(state, config: Optional[RunConfig])` / `Union[..., None]` / **PEP-604** 等价形式 | 同上（**注入**） | OK | 实测 **P-A14 / P-A16** |
| `f(state, config: "RunConfig \| None")`（**字符串**的 PEP-604 写法） | **跳过注入** ⇒ 按**一参**调用 ⇒ `TypeError`（⚠️ **MUST NOT** 发 `UserWarning`） | `UserWarning` + `TypeError` | 实测 **P-A17** · 上游同款（字符串槽**不含**该字面量） |
| `f(state, config: dict)` / `config: int)` / `Optional[str]`（**匹配集外**） | **跳过注入** ⇒ 按**一参**调用 ⇒ `TypeError`（⚠️ **MUST NOT** 发 `UserWarning`） | 同款 | 实测 **P-A04 / P-A05 / P-A19** |
| `f(state, *, config)`（**keyword-only**） | 同上（**注入**） | OK | 实测 **P-A06** |
| `f(state, **kwargs)` | **不注入**（kwargs 为空） | OK 且 kwargs 为空 | 实测 **P-A07** · 上游同款 |
| `f(state, *args)` | 按**一参**调用 | OK 且 `args == ()` | 实测 **P-A08** |
| `f(state, config, /)`（**仅位置**） | 按**一参**调用 ⇒ `TypeError` | `TypeError`（上游的 `VALID_KINDS` 不含 `POSITIONAL_ONLY`） | 实测 **P-A18** |
| 可调用对象 `__call__(self, state, config)` | 同上（**注入**） | OK | 实测 **P-A11** |
| `f()` / `f(a, b, c)` | 按**一参**调用 ⇒ `TypeError` | `TypeError` | 实测 **P-A09 / P-A10** |

> ⚠ **第二参的内容** = 用户交给 `invoke` 的**原始 `config`**（`RunConfig` / mapping / `None`
> · **逐字传入**）⇒ MUST **NOT** 归一化它 · MUST **NOT** 用 `context` 通道顶替（FR-003 · 裁定 12）
> （B8F3 的 **C21** 是**另一套**机制）⇒ 属偏离 **X-5**（§8）。

---

## 2. 求值语义（时机 · 落点 · 顺序 · 次数）

### 2.1 时机（**when**）

| 规则 | 内容 | 依据 |
|---|---|---|
| **求值时机** | 路由函数 MUST 在**源节点执行完毕**（任务**成功落回**）后被求值 ⇒ MUST **NOT** 在源节点执行**前**、或在**节点入参构造**时被求值 | FR-001 · 裁定 1 · 上游同款（上游的分支是**源节点的 writer** · `langgraph/graph/state.py:1624`） |
| **与写入合并的关系** | 求值 MUST 落在**阶段 ③′**（判定与落回）⇒ 早于**阶段 ⑤**（写入合并）⇒ 路由函数读到「**轮次开始前的通道值 + 本节点本次写入**」 | FR-001 / FR-008 · 裁定 1 |
| **节点挂起** | 节点挂起（`interrupt()`）⇒ 该任务**不成功落回** ⇒ 路由函数 MUST **NOT** 被求值 ⇒ 中断路径与路由路径**互斥** | FR-003 / FR-018 · 裁定 1 · 承接条款 **H-10** · 实测 **E-24**（上游 `router called = 0`） |
| **路由函数内部挂起** | 路由函数内部调 `interrupt()` ⇒ 归 **B10F1** 的既有口径 ⇒ 本 feature **零新增** | research **D-22** · 实测 **E-25** |

### 2.2 落点（**where**）

| 规则 | 内容 | 依据 |
|---|---|---|
| **落点** | **L2** 的 super-step 循环**内部**（`run_super_step` / `run_super_steps` 的阶段 **③′** · `superstep.py:1253-1267`）⇒ MUST **NOT** 另开一条「条件边专用」的调度路径 | FR-002 · 裁定 1 · 裁定 2 |
| **同一份状态** | 路由求值 MUST 与节点求值**同处一条**执行路径 ⇒ 路由**触发的目标节点**的写入 MUST 进入**同一份**完整状态 ⇒ ⇒ ⇒ ⚠️ **路由本身不产生状态写入**（路由通道**不被写入** · 裁定 8） | FR-002 · 承接 **H-5** · SC-002 · 裁定 8 |
| **零新增字段** | MUST **NOT** 增删编译产物的私有字段（`vars(compiled)` 仍 == **11** 键）⇒ 触发 MUST 走**既有的**「动态边」载体 | FR-005 / FR-037 · 裁定 1 · 裁定 10 |

### 2.3 顺序（**order**）

| 规则 | 内容 | 依据 |
|---|---|---|
| **同源多条条件边** | 同一源节点的多条条件边 ⇒ **各求值一次** ⇒ 顺序 = **登记顺序**（`GraphSpec.conditional_edges` 的内层 tuple 顺序） | FR-004 · 实测 **E-29**（上游：顺序 = 登记顺序） |
| **同轮多源** | 同轮**多个源节点**的求值顺序 = **节点名序**（B7F1 的阶段 ③′ 口径） | B7F1 契约 §4 · **I-12**（`superstep-contract.md`） |
| **目标在轮内的顺序** | 目标序列的**内部顺序** = 路由返回值的顺序（**去重保序**）⇒ 但目标在轮内的**执行顺序** = **节点名序** ⇒ 顺序**不可观察** | FR-018 · 裁定 13 |
| **与屏障组的关系** | 条件边的目标集合与「**屏障组**」是**两套**语义 ⇒ MUST **NOT** 把「多源边」当作「条件边」求值 ⇒ MUST **NOT** 受屏障组的「所有源齐备」判定影响 | FR-004 / FR-006 · 裁定 1 · 承接 **H-6** · 实测（research **D-24**） |

### 2.4 次数（**how many**）

| 规则 | 内容 | 依据 |
|---|---|---|
| **每源每次一次** | 每个源节点的**每次执行** MUST 只求值一次路由函数 ⇒ MUST **NOT** 因多轮重跑而对**同一次执行**重复求值 | FR-003 |
| **每条条件边各一次** | 同一源节点登记**多条**条件边（不同 `branch`）⇒ 每条的路由函数**各求值一次** ⇒ 目标取**并集**（去重保序） | FR-004 · 实测 **E-29** / **N-A6** |
| **总量口径** | 单图单次 `invoke` 的**求值次数** == Σ（各源节点各次成功落回 × 该源节点的条件边条数） | plan「Scale/Scope」 · **结构口径**（不设墙钟预算） |
| **`__start__` 相位** | 挂在**入口哨兵**上的条件边 MUST **求值** ⇒ 其结果 MUST 成为**入口目标** ⇒ MUST **NOT** 静默跳过（当前的「空跑」是**缺陷** · 实测 **E-34**）⇒ 求值落点 = **阶段 ① 之前**（**仅在第 1 轮**的触发判定前求值一次 ⇒ **幂等** ⇒ 后续轮次 MUST **NOT** 再求值）⇒ 结果写进 `state.dynamic_edges["__start__"]` ⇒ 目标在**第 1 轮**被触发 ⇒ ⇒ ⇒ ⚠️ **入参口径**：`__start__` **无本次写入**（哨兵不执行节点）⇒ 其路由函数看到的 fresh 视图 = **轮次开始前的通道值**（fresh 读**退化为「当前值」**）⇒ ⇒ ⇒ 入口目标的**校验口径**与**普通目标**同款 | FR-038 / FR-039 · 裁定 17 · 上游同款（上游的 `__start__` 是**真实伪节点** · `langgraph/graph/state.py:1373` / `:1508-1514`）· 实测 **N-A1 … N-A8** |

---

## 3. fresh 读（**C8**）

| 规则 | 内容 | 依据 |
|---|---|---|
| **唯一实现点** | 路由函数 MUST 通过 **fresh 读**获取状态 ⇒ MUST 使用 `local_read(channels, writes, fresh=True)` ⇒ MUST **显式**传 `fresh=True`（**缺省是 `False`**）⇒ MUST **NOT** 依赖缺省 | FR-007 · 裁定 2 · B5F2 `read-contract.md` §1.1 |
| **零第二份实现** | MUST **NOT** 在调度层另写一份 fresh 合并逻辑 | FR-007 · 裁定 2 |
| **`managed` 语义** | MUST **NOT** 假设上游 `local_read` 的 `managed` 入参语义（freegraph **不实现**该入参） | FR-007 · 裁定 2 · research **DR-1** · 上游 `langgraph/pregel/_algo.py:188-201`（六参签名） |
| **视图内容** | 「**当前值 + 本节点本次写入**」的合并视图 ⇒ MUST **NOT** 含**同轮其它节点**的写入 ⇒ MUST 含 `Command.update` 的写入（B9F1 的归源节点口径） | FR-008 / FR-010 · 裁定 13 · 承接 **H-7** |
| **覆盖整张通道表** | 路由函数的入参 MUST 是**覆盖整张通道表**的 fresh 视图 ⇒ MUST **NOT** 收窄为「源节点的订阅集」 | FR-013 · 裁定 3 · 上游 `langgraph/graph/state.py:1615`（`select=channels`）· 实测 **E-10** |
| **路由型通道缺席** | **路由型通道**（`EphemeralValue`）MUST 在 fresh 视图里**缺席** ⇒ MUST **NOT** 用「`branch:to:` 名称前缀」之类启发式判定 ⇒ MUST **NOT** 把路由通道的值**注入**路由函数的入参 | FR-011 · 裁定 3 · 上游 `langgraph/channels/ephemeral_value.py:56-61`（`update([])` 清空副本）· B5F2 `read-contract.md` §3.1 |
| **无值覆盖型通道缺席** | **无值**的**覆盖型**通道 MUST **缺席**（稀疏口径）⇒ 与节点入参**同款** | FR-013 · 裁定 3 |
| **归约器已生效** | 写入 MUST 按通道**自身**的写入规则合并（**归约型 MUST 走归约器**）⇒ MUST **NOT** 在路由层另写一份归约逻辑 | FR-009 · 实测 **E-16**（归约型通道看到 `['seed', 'n1']`） |
| **零污染** | fresh 读 MUST **零污染** ⇒ 每个通道的「绑定与可用性判定」在读取前后 MUST **不变** | FR-012 · B5F2 `read-contract.md` §3.3（**唯一权威**） |
| **一次合并** | 路由函数 MUST **只**看到本节点**本次**写入**一次**的结果 ⇒ MUST **NOT** 把同一批写入**重复**合并进视图 | FR-010 |

---

## 4. 目标解析（`path_map` 双形态 · 序列 · `END`）

### 4.1 返回值的形态判定

| 返回值 | 解释 | 依据 |
|---|---|---|
| `Send` 实例 | **fan-out 载荷** ⇒ MUST 复用 **B11F1** 的 `validate_send` / `make_fanout`（`src/freegraph/runtime/_fanout.py:56-104`）⇒ MUST **NOT** 另写条件边专属路径 | FR-030 · 裁定 10 · 上游 `langgraph/graph/_branch.py:203`（`Send` 实例**不**查表）· 实测 **E-11 / E-23** |
| `list` / `tuple` | **多目标**（**逐元素**查表）⇒ MUST **NOT** 当作「一个不可哈希的 key」 | FR-024 · 裁定 9 · 上游 `langgraph/graph/_branch.py:199-200` · 实测 **M-F / M-G / E-15b** |
| 其它**可哈希**值（含 `int`） | 作为 `path_map` 的 **key** 正常查表 ⇒ MUST **NOT** 先做类型收窄 | FR-020 · 实测 **E-14 / E-30** · 上游 `langgraph/graph/_branch.py:199-200` |
| `set` 等**非** `list`/`tuple` 容器 | **不是**多目标（按**单个**值处理）⇒ 无 `path_map` ⇒ 目标不存在 ⇒ 内置 `ValueError`；有 `path_map` ⇒ 查表失败 | research **D-19** · 实测 **M-H / E-27** |
| **空序列** `[]` | **无目标**（**不是**非法返回值）⇒ 该源节点**不再触发**任何目标 ⇒ MUST **NOT** 报错 | FR-018 / FR-024 · 裁定 9 · 实测 **M-A / M-A2** · spec Edge Cases |
| `None` / `START` | **显式失败** ⇒ 失败信号 = **查表优先**（**照抄上游**的判定顺序）：**有** `path_map` ⇒ 先查表 ⇒ 不在表内 ⇒ **`KeyError`**；**无** `path_map` ⇒ 直接作目标 ⇒ 非合法目标 ⇒ **`ValueError`** ⇒ ⇒ ⇒ ⚠️ `START` **不**是独立的失败条件（若 `path_map` 恰含 `__start__` **键**且其 **value** 合法 ⇒ 照上游路由到该 value） | FR-025 · 实测 **M-B / M-C / M-D / M-E** |

### 4.2 `path_map` 的两形态

| 形态 | 解析规则 | 依据 |
|---|---|---|
| **dict**（已归一化） | 路由函数的返回值 MUST 作为 **key** 查表 ⇒ 其 **value** 为目标节点名 ⇒ 取值不在表内 ⇒ **显式失败** | FR-015 · 裁定 4 · 上游 `langgraph/graph/_branch.py:202-204` · 实测 **E-6 / E-7 / M-C / M-E** |
| **`None`**（动态目标） | 路由函数的返回值 MUST **直接**作为目标节点名 ⇒ MUST 校验其为**已注册节点名**或 `END` ⇒ 否则**显式失败** | FR-017 / FR-022 · 裁定 7 · 上游 `langgraph/graph/_branch.py:205-206`（**静默忽略** · 实测 **E-8**）⇒ freegraph **更严**（**X-3**） |
| **list**（L3 归一化后） | L3 MUST 在**构建期**归一化为 `{name: name}` ⇒ 归一化后「返回值即目标节点名」⇒ 取值不在该集合内 ⇒ **显式失败** | FR-016 · 裁定 4 · 实测 **E-18** · 上游 `langgraph/graph/_branch.py:96-101` |
| **`Literal` 推断**（`path_map is None` + 返回注解） | 推断 MUST 在 **L3（构建期）**完成 ⇒ L2 **零**推断、**零**归一化 | FR-014 / FR-016 · 裁定 4 · research **D-23** · 上游 `langgraph/graph/_branch.py:102-114` · 实测 **E-33** |

### 4.3 序列与 `END`

| 规则 | 内容 | 依据 |
|---|---|---|
| **多目标并行** | 路由函数返回**序列** ⇒ MUST 解析为**多个目标** ⇒ 多个目标 MUST 在**同一轮**并行执行 ⇒ 各目标 MUST 收到**同一份**共享状态 ⇒ **无**逐目标载荷 | FR-018 · 裁定 9 · 实测 **E-9 / E-9b**（上游同款） |
| **与 `Send` 相异** | **序列**（共享状态 · 无逐目标载荷）⇒ 与 `Send`（**逐目标载荷**）**语义相异** ⇒ MUST 可区分 | 裁定 9 · 实测 **E-11**（对照） |
| **去重保序** | 目标序列 MUST **去重保序**（同一目标**只**触发一次） | FR-018 · 实测 **E-26**（上游同款） |
| **`END` 无条件终止**（**单独返回**时） | 路由函数**单独返回** `END`（`"__end__"` · **非**序列）⇒ MUST **终止整张图**（判定**先于** `path_map` 查表）⇒ ⇒ ⇒ **标量**（**非序列**）返回值经 `path_map` **解析后**的目标是 `END` ⇒ **该分支**终止（上游同款）⇒ ⇒ ⇒ **序列**返回值内的 `END`（**无论以何种形式出现**：元素**恰为** `END`，**或**元素经 `path_map` **解析后**为 `END`）⇒ **被剔除**（其余目标**照常执行** · 照抄上游 E-13 · 上游 `state.py:1592` 的过滤对**标量与序列同款**）⇒ ⇒ ⇒ 三处判定的**完整**口径见 spec 的 FR-019 ⇒ 后续目标节点的执行次数 MUST == **0** | FR-019 · 裁定 5 · **X-2** · 上游 docstring `langgraph/graph/state.py:999` |
| **序列含 `END`** | 序列中**同时**含 `END` 与其它目标 ⇒ `END` 被**剔除**、其余目标**照常执行**（**不**终止整张图）⇒ ⇒ ⇒ ⚠️ **② 只适用于「非序列」返回值** ⇒ ⇒ ⇒ 序列**不**按 ② 终止 ⇒ ⇒ ⇒ 二者**不互斥** | FR-019 · 实测 **E-13** |
| **`END` 的值** | `"__end__"`（`src/freegraph/graph.py:45`）⇒ 与上游 `langgraph/constants.py:28` 逐字同款 | P-15 · 实测 **E-3b / E-4 / M-J** |

> ⚠ **`END` 的判定与「有无 `path_map`」正交**（上游在**无** `path_map` 时返回 `END` ⇒ **正常终止** ·
> 实测 **E-19 / Q-7**）⇒ freegraph 的「**单独返回** `END` ⇒ **无条件终止**」亦然。

---

## 5. 投递（动态边 · 与 `Command.goto` 的并集）

| 规则 | 内容 | 依据 |
|---|---|---|
| **唯一触发源** | 路由目标 MUST 通过**既有的「动态边」载体**投递触发 ⇒ MUST **NOT** 另写一套「条件边触发」机制 | FR-005 · 裁定 1 · 裁定 10 |
| **载体** | `SchedulerState.dynamic_edges`（`superstep.py:264`）· 键 = **源节点名** · 值 = **目标名 tuple** | FR-005 · B7F1 契约 §3 |
| **落盘** | 由 `_commit_outcome`（`superstep.py:979-1014` · `:987`）**一次性**写入 ⇒ 出错轮一个都不落回（整轮原子） | 裁定 1 · B7F1 契约 §5.4 |
| **编组** | `_trigger_groups`（`superstep.py:613-657`）把动态边编成**单元素组** `((_EDGE_SOURCE, source),)` | B7F1 契约 §3.1 / §3.2 |
| **路由通道不写** | 路由通道（`branch:to:<target>`）MUST **不被写入** ⇒ 它**只作声明载体** ⇒ MUST **NOT** 触发 **V-6**（单值语义通道一轮收到多于一个值）⇒ 同轮**两个源**路由到**同一目标**时 MUST **正常执行** | FR-028 · 裁定 8 · **X-4** · SC-011 |
| **与 `Command.goto` 取并集** | 同一源节点同轮既返回 `Command(goto=...)` 又有条件边 ⇒ 两个来源的目标 MUST 取**并集**（去重保序）⇒ 合并进 `outcome.gotos` ⇒ 再由 `_commit_outcome` 一次性写入 | FR-031 · 裁定 13 · 承接 **H-7** |
| **入口目标的投递** | `__start__` 的条件边结果写进 `state.dynamic_edges["__start__"]` ⇒ 目标在**第 1 轮**被触发 ⇒ 与静态入口边**同轮并行**（两者的触发组版本都是 **1**）⇒ **纯条件边入口**（**无**静态入口点）也成立 | FR-038 / FR-039 · 裁定 17 · 实测 **N-A1 / N-A2** |
| **不重复触发** | 同一版本 MUST NOT 重复触发同一节点（动态边**恒为单元素组**） | FR-005 · 裁定 1 · B7F1 契约 §3.3 · **I-3** |

---

## 6. 失败信号与校验

### 6.1 失败信号（**两态** · 照抄上游）

| 场景 | 异常类型 | 消息要求 | 依据 |
|---|---|---|---|
| **有** `path_map` ⇒ 返回值不在表内 | 内置 **`KeyError`**（**类型逐字同款**） | MUST **指明返回值**与**可选目标** | FR-021 · 裁定 6 · 上游 `langgraph/graph/_branch.py:203`（消息只有 key 本身）· 实测 **E-6 / E-7 / M-C / M-E** |
| **无** `path_map` ⇒ 返回值不是已注册节点名 / `END` | 内置 **`ValueError`**（**类型逐字同款**） | MUST **指明返回值**与**已注册节点名** | FR-022 · 裁定 7 · 上游 `langgraph/graph/_branch.py:207-209`（`ValueError("Branch did not return a valid destination")` · 实测 **M-B / M-D**）⇒ 上游对**非法节点名**是**静默忽略**（实测 **E-8**）⇒ freegraph **更严**（**X-3**） |
| 返回 `None` / `START` | **查表优先**（**照抄上游**）：**有** `path_map` ⇒ **先查表** ⇒ 不在表内 ⇒ 内置 **`KeyError`**；**无** `path_map` ⇒ 直接作目标 ⇒ 非合法目标 ⇒ 内置 **`ValueError`** | MUST **指明返回值** | FR-025 · 实测 **M-B / M-C / M-D / M-E** |
| 路由函数**自身**抛出 | **原始类型 + 原始消息** | MUST **NOT** 包装 / 吞掉 / 返回部分结果 | FR-023 · 裁定 11 · 实测 **E-12** |
| 消息口径 | —— | 两态的消息均**比上游更详细** ⇒ **STRICTER**（**X-1**）⇒ 差分场景 MUST **只比对异常类型** | FR-021 / FR-025 · 裁定 6 · **X-1** · 差分 **D-107 / D-113** |
| 错误类型面 | —— | MUST **NOT** 新增异常类型 ⇒ 本 feature 只引入**内置** `KeyError` / `ValueError` 两种失败信号 | FR-033 · 契约 §9 的延续 · **I-14** |

### 6.2 校验规则（**V-8 已放宽** · 新增自 **V-27**）

> ⚠ **全局编号连续性**：既有空间 = **V-1…V-26** ⇒ 本 feature 的**新增**规则自 **V-27** 起续号
> ⇒ **零新增门禁编号**（门禁仍为 **G1–G30**）。

| # | 场景 | 时机 | 失败信号 | 依据 | 状态 |
|---|---|---|---|---|---|
| **V-8** | `GraphSpec.conditional_edges` **非空** | —— | —— | FR-026 · 裁定 14 · 破冻结面 **T-1** | ⚠ **已放宽 / 已移除** —— 守卫本体（`superstep.py:484-487`）MUST 移除 ⇒ 非空**不再**是构造期失败 ⇒ 既有断言**拆分而不删**（`tests/runtime/test_superstep_basic.py:557-576` · `tests/runtime/test_superstep_contract.py:609-617`） |
| **V-27** | 条件边载荷的**五键**形态不符（缺键 / 多键 / 键名不符） | **构造期**（L2 消费 L3 产物时逐项核对） | 内置 **`ValueError`** | FR-026 · 裁定 14 | **新增**（防御性核对 · MUST **NOT** 静默跳过） |
| **V-28** | `path_map` 的 **value** 不是已注册节点名 / `END` | **构造期**（L3 构建期） | 内置 **`ValueError`** | FR-014 · 裁定 4 · 承接 **H-4** | **引用既有**（L3 已实现）⇒ **零新增** |
| **V-29** | 路由返回值的目标**不存在**（**无** `path_map`） | **运行期**（路由求值时） | 内置 **`ValueError`** | FR-017 / FR-022 · 裁定 7 | **新增** ⇒ **X-3** ⇒ 差分 **D-111** |
| **V-30** | 同一源节点（含 `__start__`）的 **branch 名重名** | **构造期**（L3 登记时） | 内置 **`ValueError`**（消息**点名**分支名与源节点） | FR-040 · 裁定 18 | **引用既有**（L3 已实现 · `_stategraph.py:509-512`）⇒ **零新增** |
| **V-31** | 路由目标为 **`__start__`**（入口哨兵） | **运行期**（路由求值时） | **查表优先**（**照抄上游**）：**有** `path_map` ⇒ 查表失败 ⇒ 内置 **`KeyError`**；**无** `path_map` ⇒ 非合法目标 ⇒ 内置 **`ValueError`** | FR-025 · 实测 **M-D / M-E** | **新增**（`__start__` **不是**合法目标）· ⚠️ 附注：`path_map` 的 **value** 为 `__start__` 的形态**不可构造**（**V-28** 已在**构造期**拦住）⇒ ⇒ ⇒ **零新增**（引用上游的判定顺序） |

> ⚠ **V-1…V-3 等既有规则逐字不动**（FR-026 · 裁定 14）⇒ 本 feature **只放宽 V-8** 这一条
> **构造期守卫** ⇒ **零条既有判据被删** ⇒ 判据**只收紧不放宽**。

---

## 7. 不变量表（**逐条可判定**）

> ⚠ **编号空间**：本表的 **I-1…I-14** 是**本契约自有**的编号域（沿用 B7F1 / B5F2 的
> 「每份契约自有 I 编号」同款纪律）⇒ 与 `superstep-contract.md` 的 **I-1…I-16**、
> `read-contract.md` 的 **I-1…I-11** **并存但不相通** ⇒ 引用时 MUST 写全文件前缀。
> ⚠️ **本表只收「行为面」不变量** ⇒ ⇒ ⇒ **人工验证记录的文档守卫断言**（SC-019 / SC-020 ·
> FR-042）与 **`agent_loop.py` 的硬断言**（SC-025 · FR-041）**MUST NOT** 进本表
> ⇒ ⇒ ⇒ **理由**：二者的判据依赖 **Phase 9** 的产物（记录 / 追认 / 脚本硬化）⇒ ⇒ ⇒ 若进本表
> ⇒ ⇒ ⇒ 则 Phase 2 的契约守卫（tasks **T018**）在 Phase 9 之前**必然红**（撞宪法 v1.6.0 的
> 「MUST NOT 写永久红的 CI」红线 · B7F3 的 **S-29** 同款）⇒ ⇒ ⇒ 二者由 **tasks** 的
> **T067 / T068** 承担（守卫断言落在**记录写就之后**）。

| # | 不变量 | 判定方式 | 绑定测试 |
|---|---|---|---|
| **I-1** | 条件边载荷的**五键**形态**逐字不变**（`branch` / `path` / `path_map` / `targets` / `route_channels`） | `GraphSpec.conditional_edges` 与 `CompiledGraph._conditional_edges` **逐字相等** + 每项 key 集合 == 那 **5** 个 | SC-016 · FR-026 · 裁定 4 |
| **I-2** | `path_map` **不被重新归一化**（L2 只消费 L3 的 dict / `None` 两形态） | list 形态在 L3 已是 `{name: name}`（实测 **E-18**）· L2 的取值路径**只**读 `path_map` | SC-005 · SC-013 · FR-014 / FR-016 |
| **I-3** | 路由通道**零写入**（`branch:to:<target>` 从不被写）⇒ MUST NOT 触发 **V-6** | 同轮**两个源**路由到**同一目标** ⇒ **不**抛 `InvalidChannelUpdateError` | SC-011 · FR-028 · 裁定 8 |
| **I-4** | 路由目标**以动态边投递**（`state.dynamic_edges[source]`）⇒ 零新增触发机制 | 目标节点**被触发**且执行次数 == 1 + `dynamic_edges` 的键 == 源节点名 | SC-002 · SC-016 · FR-005 |
| **I-5** | fresh 视图**零污染**（每个通道的绑定与可用性判定在读取前后**不变**） | 读取前后逐通道 `is_available()` 与 `get()` 的**快照相等** | SC-004 · FR-012 |
| **I-6** | 路由通道**缺席**于 fresh 视图（且 MUST NOT 用名称前缀启发式） | 路由函数收到的 key 集合 **不含**任何 `branch:to:*` | SC-010 · FR-011 / FR-029 |
| **I-7** | 失败信号**两态**：**有** `path_map` ⇒ 内置 `KeyError`；**无** ⇒ 内置 `ValueError` | 两种场景分别断言**异常类型**（消息**不**逐字比对） | SC-006 · SC-007 · FR-021 / FR-022 |
| **I-8** | **单独返回** `END` ⇒ **无条件终止**（判定**先于** `path_map` 查表）⇒ 后续目标执行次数 == **0** ⇒ ⇒ ⇒ **标量**（**非序列**）返回值经 `path_map` **解析后**为 `END` ⇒ **该分支**终止 ⇒ ⇒ ⇒ **序列**返回值内的 `END`（**无论以何种形式出现**）⇒ **剔除**（其余目标照常执行 · 照抄上游 E-13）⇒ ⇒ ⇒ **② 只适用于非序列** ⇒ 二者**不互斥** | 目标节点执行计数 == 0（**不**抛错）+ 序列内的 `END` 被剔除而其余目标**照常执行** | SC-003 · FR-019 · **X-2** |
| **I-9** | 路由函数**自身**的异常**原样**传播（**不**包装 / 不吞掉） | 异常**类型**与**消息**逐字一致（`is` 同一对象） | SC-012 · FR-023 · 裁定 11 |
| **I-10** | 双参判别**按参数名 `config`**（**不是**位置参数个数）⇒ 永远只传一个位置实参 | 第二参不叫 `config` ⇒ 按**一参**调用 ⇒ `TypeError`（上游同款） | SC-021 · FR-003 · 裁定 16 |
| **I-11** | `__start__` 上的条件边**被求值**（**不**静默空跑）⇒ 入口目标在**第 1 轮**被触发 ⇒ ⇒ ⇒ **求值次数 == 1**（**仅在第 1 轮**求值 ⇒ **幂等** ⇒ 后续轮次 MUST **NOT** 再求值） | 路由函数**被调用次数** == 1（**含 ≥ 2 轮的图上仍 == 1**）+ 入口目标执行次数 == 1 | SC-022 · SC-023 · FR-038 / FR-039 · 裁定 17 |
| **I-12** | **branch 名唯一**（同一源节点含 `__start__`）⇒ 重名 ⇒ 内置 `ValueError` | 登记第二条同名条件边 ⇒ 抛错且消息**点名**分支名与源节点 | SC-024 · FR-040 · 裁定 18 |
| **I-13** | **零新增公开面**：`vars(compiled)` 的键数仍 == **11**；`freegraph.runtime.__all__` 仍 **23**；`freegraph.graph` 仍 **7**；契约层仍 **21** | 键数 / 符号集合**逐一**相等（单一事实源 = `tests/runtime/_runtime_export_manifest.py`） | SC-016 · FR-037 |
| **I-14** | **零新增错误类型**（只用内置 `KeyError` / `ValueError` 两种新失败信号） | `freegraph.runtime.errors` 的符号集合**不变** + 异常类型断言 | **SC-006 · SC-007 · SC-016** · **FR-021 · FR-022 · FR-033** |

---

## 8. 与上游的差异登记（**X-1 … X-7**）

> ⚠ **三态标注一致性**（宪法 v1.12.0 原则 XI 末条）：本表的 **STRICTER / DIFF** 标注与
> `contracts/upstream-parity.md` §2 的**对应行逐字一致**⇒ 每条偏离都有对照表的**对应行**
（**X-1↔P-07** · **X-2↔P-08** · **X-3↔P-09** · **X-4↔P-14** · **X-5↔P-19** ·
> **X-6↔P-22** · **X-7↔P-23**）⇒ **判据零放宽**。

| # | 类别 | 被偏离的判据 | freegraph 口径 | 对照行 | 差分场景 |
|---|---|---|---|---|---|
| **X-1** | **STRICTER** | **非法路由返回值的失败信号**：① **有** `path_map` ⇒ 上游抛**裸 `KeyError`**（消息只有 key 本身 · `langgraph/graph/_branch.py:203` · 实测 **E-6 / E-7 / M-C / M-E**）② **无** `path_map` ⇒ 上游抛 `ValueError("Branch did not return a valid destination")`（实测 **M-B / M-D**）⇒ ⇒ freegraph 抛**同型**的 `KeyError` / `ValueError` ⇒ ⇒ ⇒ 两态的**消息均 MUST 指明返回值与可选目标** | **类型逐字同款** + **消息更严** ⇒ **零新增错误类型** | **P-07** | **D-107 / D-113**（**只比对类型**） |
| **X-2** | **DIFF** | **返回 `END` 的终止条件**：上游**不**在 `_branch.py` 里过滤 `END` ⇒ 终止的充要条件是「**解析后的目的地**恰为 `'__end__'`」⇒ ⇒ 「`END` 是 `path_map` 的 key」**不**等于终止（实测 **E-17 / E-35**：`{END: "b"}` ⇒ 路由到 `b` · **不终止**）⇒ ⇒ 上游抛 `KeyError: '__end__'` 的场景是「`path_map` **不含** `END` 键」（实测 **E-5 / E-20**） | freegraph 对「**单独返回** `END`」**无条件**终止（序列内的 `END` ⇒ **剔除** · 不终止）⇒ 判定**先于**查表 ⇒ 取上游**自己的 docstring** 口径（`langgraph/graph/state.py:999`）⇒ **更确定** · **非更严** | **P-08** | **D-110 / D-118** |
| **X-3** | **STRICTER** | **无 `path_map` 时的非法目标**：上游**静默忽略**（只打一条 warning · `langgraph/graph/_branch.py:205-206` · 实测 **E-8**）⇒ 图**静默结束** | **显式失败**（内置 `ValueError` · **V-29**）⇒ 与 B7F3 的 **X-2**（未知 key ⇒ 显式失败）**同类** | **P-09** | **D-111**（⚠ MUST 带 `note`） |
| **X-4** | **DIFF** | **路由通道的写入**：上游**写** `branch:to:<target>` 并以该通道写入**触发**目标（`langgraph/graph/state.py:1583-1592` · `:1524-1530` 的 `EphemeralValue(Any, guard=False)`）⇒ freegraph **不写**该通道（只作声明载体）· 触发由**动态边**投递 | 触发源恒为**边**（B7F1 契约 §3.0）⇒ 上游的「`branch:to:` 通道触发」≡ freegraph 的**边触发**（**同款语义**）⇒ ⇒ 而路由通道是**单值语义**⇒ 同轮**两个源**路由到**同一目标**时写两次 ⇒ 触发 **V-6** ⇒ ⇒ ⇒ **不写**是唯一正确选择（裁定 8）⇒ **不构成**行为面分叉 | **P-14** | ——（**D-108 / D-111** 的**间接**锁） |
| **X-5** | **DIFF** | **双参形态的第二参内容**：上游传**增广后**的 `RunnableConfig`（dict 形态 · 实测 **P-B**）⇒ freegraph 传用户交给 `invoke` 的**原始 `config`**（`RunConfig` / mapping / `None`）· **逐字传入** ⇒ 上游的**注解匹配集**是 `RunnableConfig` 的 5 元组（`langgraph/_internal/_runnable.py:170-176`）⇒ freegraph 的对应集合是 `RunConfig \| Mapping[str, Any]` 的**同形**集合 ⇒ ⇒ ⇒ ⚠️ **附带诊断信号**：上游在注解不匹配时**发** `UserWarning`（`langgraph/_internal/_runnable.py:352-359`）⇒ freegraph **不发**（零新增可观察输出） | 调用**形态**与**判别规则**与上游**逐字相同**（**P-13 = SAME**）⇒ **仅载体类型**不同 ⇒ **非更严** ⇒ ⇒ ⇒ **附带诊断信号**的差异**同属**本条（失败信号 `TypeError` **逐字同款** · freegraph 只是**更安静**）⇒ ⇒ ⇒ 差分**三投影**不含 Python 警告 ⇒ ⇒ ⇒ 由**单元测试**锁定（tasks **T074**） | **P-19** | **D-114**（比对**形态**而非内容）· **T074**（`UserWarning` 不发） |
| **X-6** | **STRICTER** | **路由函数返回 `Send` → 未注册节点**：上游**静默忽略**（只打一条 warning · `langgraph/graph/_branch.py:205-206` · 实测 **E-22**）⇒ freegraph **显式失败**（内置 `ValueError` · B11F1 的 **V-19** · `src/freegraph/runtime/_fanout.py:56-82`） | 原则 XI ② 类（上游自身的**静默忽略**）+ 与 B7F3 的 **X-2** 同类 ⇒ 「拼错的 `Send` 目标无声地少跑一条分支」会让图「看起来成功」却结果不对 ⇒ ⇒ **零新增错误类型** ⇒ ⇒ MUST **NOT** 改 B11F1 的冻结面（V-19） | **P-22** | **D-119**（比对「失败与否」· ⚠ MUST 带 `note`） |
| **X-7** | **DIFF** | **路由函数返回 `Send` → `END`** 的**失败信号类型**：上游抛 **`InvalidUpdateError`**（`langgraph/graph/_branch.py:209-210` · 实测 **E-21**）⇒ freegraph 抛**内置 `ValueError`**（B11F1 的 **V-21** · `validate_send`）⇒ **异常类型不同型** | freegraph **零新增错误类型**（只用**内置**异常）⇒ 与上游的**异常类型家族**不同 ⇒ **非更严**（上游更宽）⇒ ⇒ MUST **NOT** 改 B11F1 的冻结面（V-21） | **P-23** | **D-120**（比对「异常类型」） |

> ⚠ **其余上游语义点一律照抄**（**P-01 … P-23** 中标 `SAME` 的行）⇒ 本契约**不**另立口径。
> ⚠ **差分场景组 = D-103…D-120（18 条）** · 判词分布 = **SAME 12 / DIFF 4 / STRICTER 2**
> ⇒ 落 `tests/differential/parity_probe.py`（**双真实实现**对跑 · 裁定 15 · FR-032）。
> ⚠ **P-11 的 `SAME` 仅指「任务形态 / 载荷语义」** ⇒ ⇒ ⇒ **失败信号**的类型分叉
> ⇒ ⇒ ⇒ 归 **P-22 / P-23**（**X-6 / X-7**）⇒ ⇒ ⇒ **零漏行**。

---

## 9. 零新增面声明

| 面 | 数量 | 本 feature 的处置 |
|---|---|---|
| 门面 `freegraph.graph` 的 `__all__` | **7** 个符号 | **一字不动** |
| 导出面 `freegraph.runtime` 的 `__all__` | **23** 个符号 | **一字不动**（FR-037）⇒ 新模块 `src/freegraph/runtime/_routing.py` MUST 是**私有**（**不进** `__all__`） |
| 契约层 `freegraph.contracts` 的 `__all__` | **21** 个符号 | **一字不动** |
| 编译产物持有面 `vars(compiled)` | **11** 个键（3 私有 + 8 公开） | **零新增私有字段** ⇒ 路由求值复用既有的 `_conditional_edges` 与 `_spec` ⇒ **T-3 不破**（FR-037） |
| 兼容矩阵 | —— | **零新增行**（无新增公开符号） |
| 错误类型 | —— | **零新增**（只用内置 `KeyError` / `ValueError` 两种新失败信号 · FR-033） |
| 依赖 | —— | **零新增**（运行时零第三方依赖 · `pyproject.toml` 零改动） |
| 门禁编号 | **G1–G30** | **零新增**（新模块由 **G25** 的目录条目与 **G30** 的署名头扫描**自动**覆盖） |
| 路由通道命名 | —— | **沿用** `branch:to:<target>` ⇒ MUST **NOT** 另起命名（FR-014） |
| 层注册表 | —— | **零改动**（`src/freegraph/runtime/` 已是**目录条目**）⇒ MUST **NOT** 为新模块**单独立**条目（层纪律 · G25 · ARCH-1） |

> ⚠ **零新增公开面**是本 feature 的**冻结面**（**I-13** · FR-037）⇒ MUST 在人工验证记录里**显式记「零新增」**。

---

## 10. 边界（本契约**不**规定的事）

| 项 | 归属 |
|---|---|
| 调度循环（super-step · 触发判定 · 版本号 · 整轮原子） | **B7F1**（`superstep-contract.md`） |
| **稀疏读 / fresh 读的合并语义**与**零污染**的作用域 | **B5F2**（`read-contract.md` §3 / §3.3） |
| `path_map` 的**构建期归一化**与 `Literal` 推断 | **B6F1 / L3** |
| `Command` / `Command.goto` 的**语义** | **B9F1**（本契约只取**并集**） |
| `Send` fan-out 的**调度**与 `Send` 的**校验规则**（V-19 / V-21） | **B11F1**（本契约只**复用**构造器 · research **DR-6**）⇒ ⚠ 其与上游的**失败信号**差异见 **X-6 / X-7**（本 feature **MUST NOT** 改 B11F1 的判据） |
| 节点别名 / `context` 通道（**C21**） | **B8F3**（下游承接 **D-2**） |
| `stream()` 的每一档 | **B8F2**（下游承接 **D-1**）⇒ MUST 与本 feature 的 `invoke` **逐字同款**（FR-002 · 裁定 1） |
| 图导出里的条件边表达 | **B22F1 / B23F1**（下游承接 **D-4**） |
| 路由函数**内部**的 `interrupt()` 语义 | **B10F1**（实测 **E-25**） |
| checkpoint / 状态历史 / `update_state` | **B14F1 / B15F1 / B16F1** |
| async 路由求值 | **v2**（research **DR-10**） |
