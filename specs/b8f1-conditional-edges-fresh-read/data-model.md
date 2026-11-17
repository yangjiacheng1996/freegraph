# 数据模型（Data Model）—— B8F1 的条件边路由求值

**Feature**: `B8F1` · **Spec**: [spec.md](./spec.md)
**契约**: [contracts/conditional-edge-contract.md](./contracts/conditional-edge-contract.md)
**核实环境**: CPython **3.11.16** · 上游 `langgraph` **1.2.11**（取证于 2026-11-17）

> **落位**：路由**求值**落 **L2**（`src/freegraph/runtime/`）· 载荷**接线**落 **L3**
> （`src/freegraph/_stategraph.py`）⇒ 方向仍是 **L3 → L2**（既有方向 · 无新增反向依赖）。
> ⇒ **零新增**编译产物私有字段（`vars(compiled)` 仍 == **11** 键 · FR-037 · T-3 不破）。
> ⇒ 新模块 `src/freegraph/runtime/_routing.py` 是 **L2 私有** ⇒ **不进** `__all__`。
> ⇒ ⚠ **MUST NOT** 为它**单独立**层注册表条目（层纪律 · G25 · ARCH-1）。
>
> **判据与证据的分工**：本文件讲「**是什么**」（实体 · 状态机 · 校验 · 不变量）·
> `contracts/conditional-edge-contract.md` 讲「**怎么用**」且是**唯一权威** ·
> `contracts/upstream-parity.md` 讲「**证据**」（上游锚点 + 差分场景 + 偏离登记）。
> ⇒ ⚠ 本文件 **MUST NOT** 被测试**解析**（测试**直接断言行为** · B7F1 契约 §1 的同款纪律）。

---

## 1. 实体总览

| 实体 | 角色 | 生命周期 | 可变性 |
|---|---|---|---|
| **条件边载荷** `GraphSpec.conditional_edges` | **静态**的路由声明（plain mapping） | 跨轮次 | **不可变**（随 `GraphSpec`） |
| **路由函数** `path` | 用户注册的**普通可调用对象** | 跨轮次（每次落回被调用一次） | 由用户持有 |
| **fresh 视图** | 路由函数的**唯一**位置入参 | **单次调用** | 一次性 `dict` |
| **目标解析结果** | 有序去重的目标名序列 | **单次求值** | 一次性 `tuple` |
| **动态边** `SchedulerState.dynamic_edges` | 触发投递的**唯一**载体 | 跨轮次（由调用方持有的调度状态） | 每轮整体替换 |
| **路由通道** `branch:to:<target>` | **声明载体**（`EphemeralValue`） | 跨轮次 | **从不被写入** |
| **失败信号** | 路由判错的**两态**异常 | 一次性 | —— |

---

## 2. 实体表

### 2.1 条件边载荷（`GraphSpec.conditional_edges`）

| 项 | 契约 |
|---|---|
| 载体 | `GraphSpec.conditional_edges`（`src/freegraph/runtime/superstep.py:219`）· 类型 `dict[str, Any]`（**缺省 = 空映射** · 工厂语义） |
| 产出 | **L3** 的 `_conditional_mapping()`（`src/freegraph/_stategraph.py:205-225`）· 外层 key = **源节点名**（首次出现顺序）· 内层 = **tuple**（顺序 = **登记顺序**） |
| 分支项 | **恰 5 键**的 plain mapping · 顺序固定：`branch` / `path` / `path_map` / `targets` / `route_channels` |
| 消费方 | **L2** 路由求值 · MUST **只**消费本字段（FR-014）⇒ MUST NOT import `freegraph._stategraph` / `_ConditionalEdgeSpec`（层纪律 · G25） |
| 归一化 | **零归一化**（FR-014 / FR-016 · 裁定 4）⇒ L2 MUST NOT 重新归一化 `path_map` · MUST NOT 另起路由通道命名（沿用 `branch:to:<target>`） |

| 分支项字段 | 类型 | 语义 | 不变量 | 校验 |
|---|---|---|---|---|
| `branch` | `str` | 分支名 | 取自 L3 的 `_branch_name`（`src/freegraph/_stategraph.py:110-115`）· **MUST NOT** 重新推断 | 同源重名 ⇒ 内置 `ValueError`（**V-30** · 裁定 18 · FR-040） |
| `path` | `Callable[..., Any]` | 路由函数 | 用户注册的**普通可调用对象** · MUST 可调用 | 非可调用 ⇒ 内置 `TypeError`（L3 构建期已实现 · `_stategraph.py:503-505` · FR-014） |
| `path_map` | `dict[Hashable, str] \| None` | 归一化后的「返回值 → 目标节点名」映射 | L2 只有 **dict** 与 **`None`** 两形态（FR-014 / FR-016 · 裁定 4）· **MUST NOT** 重新归一化（list ⇒ `{name: name}` 已在 L3 完成） | **value** 必须是已注册节点名或 `END`（**V-28**） |
| `targets` | `tuple[str, ...]` | 该条件边**可能**的目标节点名 | L3 产出（`_stategraph.py:643`）· `path_map is None` ⇒ **空** tuple | ——（**声明面** · 非运行期目标） |
| `route_channels` | `tuple[str, ...]` | `branch:to:<target>` 通道名 | L3 产出（`_stategraph.py:644-646`）· 排除 `END` · `path_map is None` ⇒ **空** tuple | ——（**声明面** · 从不被写入） |

> ⚠ **载荷形态的**五键**校验**（缺键 / 多键 / 键名不符）⇒ 内置 **`ValueError`**（**V-27**）·
> 这是 **L2** 侧的**防御性**校验（消费 L3 的产物时逐项核对）⇒ L3 的产出形态**逐字**已满足它。
> ⇒ **不得**因为形态不符而**静默**跳过该条件边。

### 2.2 路由函数（path function）

| 项 | 契约 |
|---|---|
| 类型 | `Callable[[dict[str, Any]], Hashable \| Sequence[Hashable]]`（**单参**）· 或 `Callable[[dict[str, Any], RunConfig \| Mapping[str, Any] \| None], ...]`（**双参**） |
| 双参判别 | **第二参的参数名是 `config`**（**不是**位置参数个数）· 永远只传**一个**位置实参 · `config` 以**关键字**注入（裁定 16 · FR-003） |
| 注解匹配集 | 无注解 ∨ 类对象 `RunConfig` / `Mapping[str, Any]` ∨ 字符串（每种载体**两个字面量**：`"RunConfig"` / `"Optional[RunConfig]"` · `"Mapping[str, Any]"` / `"Optional[Mapping[str, Any]]"`）∨ `Optional[...]` / `Union[..., None]` ∨ **PEP-604** 等价形式 ⇒ 字符串 `"RunConfig \| None"` **不被接受**（上游同款 · 实测 **P-A17**） |
| 注解不匹配 | **跳过注入** ⇒ 按**一参**调用 ⇒ `TypeError`（上游同款）· ⚠️ **MUST NOT** 发 `UserWarning`（上游的附带诊断信号 · 归偏离 **X-5**）· 实测 **P-A04 / P-A05 / P-A19** |
| `**kwargs` 形态 | **不注入**（上游同款 · kwargs 为空 · 实测 **P-A07**） |
| 第二参内容 | 用户交给 `invoke` 的**原始 `config`**（`RunConfig` / mapping / `None` · **逐字**）⇒ MUST NOT 归一化 · MUST NOT 用 `context` 通道顶替（裁定 12 · X-5） |
| 异常 | 路由函数**自身**抛出的异常 ⇒ **原始类型 + 原始消息**传播 · MUST NOT 包装 / 吞掉（裁定 11 · FR-023 · 实测 **E-12**） |

### 2.3 fresh 视图（路由函数的唯一位置入参）

| 项 | 契约 |
|---|---|
| 类型 | `dict[str, Any]`（**普通 `dict`**） |
| 内容 | 「**当前值 + 本节点本次写入**」的合并视图（**C8**）· 覆盖**整张通道表**（裁定 3 · 实测 **E-10**） |
| 缺席项 | ① **路由型通道**（`EphemeralValue`）· ② **无值**的**覆盖型**通道（稀疏口径） |
| 归约器 | 归约型通道的值**已**按通道自身的写入规则合并（实测 **E-16** · FR-009） |
| 唯一实现点 | `local_read(channels, writes, *, fresh=True)`（`src/freegraph/runtime/read.py:163-197`）⇒ MUST **显式**传 `fresh=True`（**缺省是 `False`** · FR-007 · 裁定 2）· 内部实现 = `_fresh_read`（`read.py:101-133` · 逐通道 copy ⇒ **零污染**） |
| 禁止 | MUST NOT 在调度层另写一份合并逻辑 · MUST NOT 依赖缺省 · MUST NOT 假设上游的 `managed` 语义（FR-007 · 裁定 2 · research **DR-1**） |

### 2.4 目标解析结果（目标节点名序列）

| 项 | 契约 |
|---|---|
| 类型 | `tuple[str, ...]` —— **有序去重**（保序 · 去重） |
| 元素 | 每项是**已注册节点名**或 `END`（`"__end__"` · `src/freegraph/graph.py:45` · 上游同款 `langgraph/constants.py:28`） |
| 产出时机 | 路由函数返回后 ⇒ 形态判定（标量 / `list` / `tuple` / `Send`）⇒ `END` 剔除 ⇒ `path_map` 查表 ⇒ 目标存在性校验 ⇒ 去重保序 |
| 序列语义 | **多目标并行 fan-out**（共享同一份状态 · **无**逐目标载荷）⇒ 与 `Send` 的**逐目标载荷**语义**相异**（裁定 9 · 实测 **E-9 / E-9b** vs **E-11**） |

### 2.5 动态边（触发投递的载体）

| 项 | 契约 |
|---|---|
| 载体 | `SchedulerState.dynamic_edges`（`src/freegraph/runtime/superstep.py:264`）· 类型 `dict[str, tuple[str, ...]]` |
| 键 / 值 | 键 = **源节点名** · 值 = **目标名 tuple** |
| 落盘 | `_commit_outcome`（`superstep.py:979-1014` · `:987` 写 `state.dynamic_edges[target] = outcome.gotos`）⇒ **整轮原子**（出错轮一个都不落回） |
| 编组 | `_trigger_groups`（`superstep.py:613-657`）⇒ 动态边编成**单元素组** `((_EDGE_SOURCE, source),)` ⇒ 动态边**恒为单元素组**（同 B7F4 的 H-3 口径） |
| 语义 | freegraph 的**边触发** ≡ 上游的「`branch:to:` **通道**触发」（**同款语义** · 不同载体）⇒ 偏离登记 **X-4** |

### 2.6 路由通道（`branch:to:<target>`）

| 项 | 契约 |
|---|---|
| 名称 | `branch:to:<target>`（L3 产出 · `src/freegraph/_stategraph.py:617-627`） |
| 类型 | `EphemeralValue(key, Any, guard=False)`（路由型 · 单值语义） |
| 角色 | **只作声明载体**（供 `targets` / `route_channels` 口径与未来的图导出用） |
| 写入 | **不被写入**（FR-028 · 裁定 8）⇒ MUST NOT 触发 **V-6**（单值语义通道一轮收到多于一个值）⇒ 同轮**两个源**路由到**同一目标**时**正常执行**（实测 **E-8** 对照 · SC-011） |
| 可见性 | ① MUST **不**出现在 fresh 视图里（FR-011）② MUST **不**出现在 `invoke` 的返回键集里（FR-029 · L3 `_full_state` 已按 `isinstance(channel, EphemeralValue)` 排除 · `_stategraph.py:252-259`） |
| 判定方式 | MUST 以 `isinstance(channel, EphemeralValue)` 判定 · MUST NOT 用「`branch:to:` 名称前缀」启发式（裁定 3 · FR-011 / FR-029） |

### 2.7 失败信号

| 场景 | 异常类型 | 消息要求 | 依据 |
|---|---|---|---|
| **有** `path_map` ⇒ 返回值不在表内 | 内置 **`KeyError`** | MUST **指明返回值**与**可选目标** | FR-021 · 裁定 6 · 上游 `langgraph/graph/_branch.py:203` · 实测 **E-6 / E-7 / M-C / M-E** |
| **无** `path_map` ⇒ 返回值不是已注册节点名 / `END` | 内置 **`ValueError`** | MUST **指明返回值**与**已注册节点名** | FR-022 · 裁定 7 · 上游 `langgraph/graph/_branch.py:207-209` · 实测 **M-B / M-D** · 偏离 **X-3** |
| 返回 **`None`** / **`START`** | 随 `path_map` 形态**两态** | MUST **指明返回值** | FR-025 · 实测 **M-B / M-C / M-D / M-E** |
| 路由函数**自身**抛出 | **原类型 + 原消息** | **不包装** | FR-023 · 裁定 11 · 实测 **E-12** |
| 消息口径 | —— | 两态的消息均**比上游更详细** ⇒ 属「失败信号 MAY 更严」⇒ **STRICTER**（**X-1**） | 偏离登记 **X-1** · 差分 **D-107 / D-113** 只比对**类型** |

> ⚠ **零新增错误类型**（FR-033 · 契约 §9 的延续）⇒ 本 feature 只用**内置** `KeyError` /
> `ValueError` 两种新失败信号 ⇒ MUST NOT 引入 freegraph 自有的新异常类（FR-021 / FR-022 · 裁定 6）。

---

## 3. 关系（ER 式文字图）

```
CompiledGraph._conditional_edges          （plain mapping · 每项恰 5 键）
            │  L3 接线（_graph_spec_from · _stategraph.py:175-202）
            ▼
GraphSpec.conditional_edges                （外层：源节点名 → tuple(分支项)）
            │
            │ 分支项.path
            ▼
        路由函数  ──调用（fresh 视图 ＋ 原始 config）──►  目标解析
            │                                              │
            │ 读                                            │ 产出目标序列
            ▼                                              ▼
      fresh 视图  ◄── local_read(fresh=True) ── 通道表      ▼
            │                              （GraphSpec.channels）  动态边
            ▼                                                    ▲
    Channel（整张表 · 路由型缺席）                                │ 写入
                                                                 │
                              SchedulerState.dynamic_edges ◄─────┘
                              （键：源节点名 → tuple(目标名)）
                                        │
                                        │ _trigger_groups 编成单元素组
                                        ▼
                              下一轮的目标节点被触发
```

| 关系 | 基数 | 说明 |
|---|---|---|
| `CompiledGraph` ⇒ `GraphSpec` | 1 : 1 | 载荷**逐字**搬运（FR-027）⇒ `GraphSpec.conditional_edges` **非空**且与 `_conditional_edges` **逐字相等** |
| `GraphSpec.conditional_edges` ⇒ 路由函数 | 1 : N（每源节点 N 条条件边） | 分支项的 `path` 字段 |
| 路由函数 ⇒ fresh 视图 | 1 : 1（每次落回一次） | 视图由 `local_read(..., fresh=True)` 产出（FR-007） |
| fresh 视图 ⇒ `Channel` | N : 1 | 覆盖**整张**通道表 · 路由型缺席 · 无值覆盖型缺席（FR-011 / FR-013） |
| 路由函数 ⇒ 目标解析结果 | 1 : 1（每次落回一次） | 返回值 ⇒ 形态判定 ⇒ 查表 ⇒ 目标序列 |
| 目标解析结果 ⇒ 动态边 | N : 1（源节点 → 目标 tuple） | 与同轮 `Command.goto` 目标取**并集**（去重保序 · 裁定 13）⇒ 一次性写入（`_commit_outcome` `:987`） |
| 路由通道 ⇒ 目标解析结果 | 1 : N | **声明关系**（`route_channels` / `targets`）⇒ **不参与**触发（裁定 8） |

---

## 4. 状态机（条件边在每个源节点的每次成功落回上的生命周期）

### 4.1 文字图

```
        （源节点任务成功落回）
                  │
                  ▼
          ┌───────────────┐
          │   未求值       │  ← 每个源节点的每次成功落回都从这里开始
          └───────────────┘
                  │  阶段 ③′（判定与落回）· 该源节点名下有条件边
                  ▼
          ┌───────────────┐   路由函数抛异常 / 返回值非法
          │   求值中       │ ──────────────────────────────► （失败 · 本轮终止）
          └───────────────┘
                  │  返回值解析成功（形态判定 → END 剔除 → 查表 → 目标校验 → 去重保序）
                  ▼
          ┌───────────────┐
          │   已求值       │  持有：有序去重的目标名 tuple
          └───────────────┘
                  │  并入 outcome.gotos（与 Command.goto 目标取并集）
                  ▼
          ┌───────────────┐
          │   已投递       │  落点：state.dynamic_edges[source] = 目标 tuple
          └───────────────┘
                  │  该源节点下次成功落回 ⇒ 回到「未求值」
                  ▼
             （未求值）
```

### 4.2 迁移表

| # | 起始态 | 事件 | 终止态 | 条件 / 载荷 | 落点 |
|---|---|---|---|---|---|
| **M-1** | 未求值 | 源节点任务**成功落回** | 求值中 | 该源节点名下**存在**条件边 · 路由函数**各求值一次**（FR-003 / FR-004） | 阶段 ③′（`superstep.py:1253-1267`） |
| **M-2** | 求值中 | 路由函数**返回**（合法） | 已求值 | 产出**有序去重**的目标名 tuple（FR-018 / FR-019） | 目标解析（§2.4） |
| **M-3** | 求值中 | 路由函数**抛异常** | **失败**（本轮终止） | **原始类型 + 原始消息**（FR-023 · 裁定 11） | 原样传播（实测 **E-12**） |
| **M-4** | 求值中 | 返回值**非法** | **失败**（本轮终止） | 两态失败信号（FR-021 / FR-022 · 裁定 6） | §2.7 |
| **M-5** | 已求值 | 并入 `outcome.gotos` | 已投递 | 与同轮 `Command.goto` 目标取**并集**（去重保序 · 裁定 13） | `_commit_outcome`（`superstep.py:987`） |
| **M-6** | 已投递 | 该源节点**下次**成功落回 | 未求值 | 每轮重新走 **M-1**（不缓存） | —— |

> ⚠ **节点挂起**（`interrupt()`）⇒ 该任务**不成功落回** ⇒ **M-1 不发生** ⇒ 路由函数
> **不被求值**（承接条款 **H-10** · 实测 **E-24**：上游 `router called = 0`）⇒ 中断路径与
> 路由路径**互斥**。
> ⚠ **出错轮一个都不落回**（B7F1 的整轮原子）⇒ **M-5** 随该轮一起回退。

### 4.3 `__start__` 的**特殊相位**（入口哨兵）

> freegraph 的 `__start__` 是**哨兵**（`superstep.py:123` 的 `_START_MARKER`）· **永不**作为
> 节点执行 ⇒ 挂在它上面的条件边**今天永不**被求值（**缺陷** · 实测 **E-34**）⇒ 本 feature
> 照抄上游的「**求值**」这件事（裁定 17 · 上游的 `__start__` 是**真实伪节点** ·
> `langgraph/graph/state.py:1373` / `:1508-1514`）⇒ 而**不是**把它变成可执行节点。

```
        （图启动 · 阶段 ① 之前）
                  │
                  ▼
          ┌───────────────┐
          │ 未求值（入口） │  ← 每轮开始时求值**一次**（若尚未求值）
          └───────────────┘
                  │  求值 __start__ 名下的条件边（每条各一次）
                  ▼
          ┌───────────────┐
          │ 已求值（入口） │  持有：入口目标名 tuple
          └───────────────┘
                  │  写进 state.dynamic_edges["__start__"]
                  ▼
          ┌───────────────┐
          │ 已投递（入口） │  ⇒ 目标在**第 1 轮**被触发
          └───────────────┘
```

| # | 事件 | 条件 / 载荷 | 落点 | 依据 |
|---|---|---|---|---|
| **M-7** | 阶段 ① **之前**求值入口哨兵的条件边 | 每轮开始时**一次**（若尚未求值）· 每条条件边**各求值一次** | 结果写进 `state.dynamic_edges["__start__"]` | 裁定 17 · FR-038 |
| **M-8** | 入口目标在**第 1 轮**被触发 | 动态边编成单元素组 `((_EDGE_SOURCE, "__start__"),)` · 版本恒为 **1**（`_source_version` · `superstep.py:562-572`） | 与静态入口边 `edges["__start__"]` **同轮并行**（两者版本都是 1） | FR-039 · 实测 **N-A2** |
| **M-9** | **纯条件边入口**（**无**静态入口点） | 图从**路由结果**起步 ⇒ 目标在第 1 轮被触发 | L3 的 `_validate_entrypoint` **已**接受条件入口（`_stategraph.py:570-583`）⇒ **零新增** | FR-039 · 实测 **N-A1** |
| **M-10** | 入口条件边返回 `END` | 该分支**终止**（纯条件边入口 ⇒ 图**直接结束**） | —— | 裁定 17 · 实测 **N-A3 / N-A3b** |

> ⚠ **幂等标记（M-7 的判据 · MUST 钉死）**：「**已求值**」的判据 MUST 覆盖**返回 `END` 时的
> 空目标情形**（⇒ **MUST NOT** 用「`state.dynamic_edges["__start__"]` **非空**」当判据
> —— 空 tuple 同样表示「已求值」）⇒ ⇒ ⇒ ⇒ ⚠️ **载体 MUST 钉死**（2026-11-18 · analyse 轮修复
> · 发起者 2026-11-18 拍板）= **键存在性** `"__start__" in state.dynamic_edges`
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 用「值非空」当判据
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 给 `SchedulerState` 新增字段（其「构造签名与名字逐字不变」
> 是 B7F1 / B9F1 / **B8F1** 的冻结面 · `superstep.py:285-287`）
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 用 `state.step == 0`（`step` 是「执行轮计数（不含空轮）」
> ⇒ 空轮场景下的「第 1 轮」与触发时点**未对齐**）
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 落在 `CompiledGraph`（**T-3 不破** ⇒ `vars(compiled)` 仍 == **11** 键）
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 触碰 SC-016 的**零新增面**六条判据
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ （⑤ `freegraph.runtime.errors` 的符号集合**不变** · ⑥ 未实现的
> L1 协议方法仍抛内置 `NotImplementedError`）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **SC-022 的「求值次数 == 1」**
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 由本判据判定（载体 = **T014 + T016**）。

---

## 5. 校验规则表

> ⚠ **编号空间**（沿用 B7F1 data-model §6 的同款纪律）：本节的 **V-n** = **校验规则**
> （连字符）· `quickstart.md` 的 **Vn** = **验收闸口**（无连字符）⇒ 两个空间**并存但不相通**。
> ⚠ **全局编号连续性**：既有空间 = **V-1…V-26**（B7F1 · B11F1 · B13F1 · B5F2）⇒ 本 feature
> 的**新增**规则自 **V-27** 起续号 ⇒ **零新增门禁编号**（门禁仍为 **G1–G30**）。

| # | 场景 | 时机 | 失败信号 | 依据 | 现状 |
|---|---|---|---|---|---|
| **V-8** | `GraphSpec.conditional_edges` **非空** | —— | —— | FR-026 · 裁定 14 · 破冻结面 **T-1** | ⚠ **已放宽 / 已移除** —— 守卫本体（`superstep.py:484-487`）MUST 移除（FR-026 · 裁定 14）⇒ 非空**不再**是构造期失败 ⇒ 既有断言**拆分而不删** |
| **V-27** | 条件边载荷的**五键**形态不符（缺键 / 多键 / 键名不符） | **构造期**（L2 消费 L3 产物时逐项核对） | 内置 **`ValueError`** | FR-026 · 裁定 14 | **新增**（L2 侧防御性核对 · MUST NOT 静默跳过 · FR-026 · 裁定 14） |
| **V-28** | `path_map` 的 **value** 不是已注册节点名 / `END` | **构造期**（L3 构建期已校验） | 内置 **`ValueError`** | FR-014 · 裁定 4 · H-4 | **引用既有**（L3 已实现 · `_stategraph.py:585` 的 `_validate_targets` 一族）⇒ **零新增** |
| **V-29** | 路由返回值的目标**不存在**（**无** `path_map` 的动态目标） | **运行期**（路由求值时） | 内置 **`ValueError`** | FR-017 / FR-022 · 裁定 7 | **新增** ⇒ 偏离 **X-3**（上游**静默忽略** · 实测 **E-8**）⇒ 差分 **D-111** |
| **V-30** | 同一源节点（含 `__start__`）的 **branch 名重名** | **构造期**（L3 登记时） | 内置 **`ValueError`**（消息**点名**分支名与源节点） | FR-040 · 裁定 18 | **引用既有**（L3 已实现 · `_stategraph.py:509-512`）⇒ **零新增** |
| **V-31** | 路由目标为 **`__start__`**（入口哨兵） | **运行期**（路由求值时） | **查表优先**（**照抄上游**）：**有** `path_map` ⇒ 查表失败 ⇒ 内置 **`KeyError`**；**无** `path_map` ⇒ 非合法目标 ⇒ 内置 **`ValueError`** | FR-025 · 实测 **M-D / M-E** | **新增**（`__start__` **不是**合法目标）· ⚠️ 附注：`path_map` 的 **value** 为 `__start__` 的形态**不可构造**（**V-28** 已在**构造期**拦住）⇒ ⇒ ⇒ **零新增** |

> ⚠ **V-1…V-3 等既有规则逐字不动**（FR-026 · 裁定 14）⇒ 本 feature **只放宽 V-8** 这一条
> **构造期守卫** ⇒ **零条既有判据被删** ⇒ 判据**只收紧不放宽**。
> ⚠ **V-28 / V-30 是「引用既有」** ⇒ freegraph 侧**零新增实现**（L3 已交付 · B6F1）。

---

## 6. 不变量表（**逐条可判定**）

> ⚠ **编号空间**：本表的 **I-1…I-14** 是**本契约自有**的编号域（沿用 B7F1 / B5F2 的
> 「每份契约自有 I 编号」同款纪律）⇒ 与 `superstep-contract.md` 的 **I-1…I-16**、
> `read-contract.md` 的 **I-1…I-11** **并存但不相通** ⇒ 引用时 MUST 写全文件前缀。

| # | 不变量 | 判定方式 | 绑定测试 |
|---|---|---|---|
| **I-1** | 条件边载荷的**五键**形态**逐字不变**（`branch` / `path` / `path_map` / `targets` / `route_channels`） | `GraphSpec.conditional_edges` 与 `CompiledGraph._conditional_edges` **逐字相等** + 每项 key 集合 == 那 **5** 个 | SC-016 · FR-026 |
| **I-2** | `path_map` **不被重新归一化**（L2 只消费 L3 的 dict / `None` 两形态） | L2 的取值路径**只**读 `path_map`；list 形态在 L3 已是 `{name: name}`（实测 **E-18**） | SC-005 · SC-013 · FR-014 / FR-016 |
| **I-3** | 路由通道**零写入**（`branch:to:<target>` 从不被写）⇒ MUST NOT 触发 **V-6** | 同轮**两个源**路由到**同一目标** ⇒ **不**抛 `InvalidChannelUpdateError` | SC-011 · FR-028 |
| **I-4** | 路由目标**以动态边投递**（`state.dynamic_edges[source]`）⇒ 零新增触发机制 | 目标节点**被触发**且执行次数 == 1 + `dynamic_edges` 的键 == 源节点名 | SC-002 · SC-016 · FR-005 |
| **I-5** | fresh 视图**零污染**（每个通道的绑定与可用性判定在读取前后**不变**） | 读取前后逐通道 `is_available()` 与 `get()` 的**快照相等** | SC-004 · FR-012 |
| **I-6** | 路由通道**缺席**于 fresh 视图（且 MUST NOT 用名称前缀启发式） | 路由函数收到的 key 集合 **不含**任何 `branch:to:*` | SC-010 · FR-011 / FR-029 |
| **I-7** | 失败信号**两态**：**有** `path_map` ⇒ 内置 `KeyError`；**无** ⇒ 内置 `ValueError` | 两种场景分别断言**异常类型**（消息**不**逐字比对） | SC-006 · SC-007 · FR-021 / FR-022 |
| **I-8** | **单独返回** `END` ⇒ **无条件终止**（判定**先于** `path_map` 查表）⇒ 后续目标执行次数 == **0** ⇒ ⇒ ⇒ **标量**（**非序列**）返回值经 `path_map` **解析后**为 `END` ⇒ **该分支**终止 ⇒ ⇒ ⇒ **序列**返回值内的 `END`（**无论以何种形式出现**）⇒ **剔除**（其余目标照常执行 · 照抄上游 E-13）⇒ ⇒ ⇒ **② 只适用于非序列** | 目标节点执行计数 == 0（**不**抛错）+ 序列内的 `END` 被剔除而其余目标**照常执行** | SC-003 · FR-019 · 偏离 **X-2** |
| **I-9** | 路由函数**自身**的异常**原样**传播（**不**包装 / 不吞掉） | 异常**类型**与**消息**逐字一致（⚠️ 2026-11-18 · analyse 轮修复：与 spec 的 FR-023 / SC-012 对齐 ⇒ **去掉**「`is` 同一对象」⇒ 判据强度 = **类型逐字相同 + 消息逐字相等**） | SC-012 · FR-023 |
| **I-10** | 双参判别**按参数名 `config`**（**不是**位置参数个数）⇒ 永远只传一个位置实参 | 第二参不叫 `config` ⇒ 按**一参**调用 ⇒ `TypeError`（上游同款） | SC-021 · FR-003 |
| **I-11** | `__start__` 上的条件边**被求值**（**不**静默空跑）⇒ 入口目标在**第 1 轮**被触发 ⇒ ⇒ ⇒ **求值次数 == 1**（**仅在第 1 轮**求值 ⇒ **幂等**） | 路由函数**被调用次数** == 1（**含 ≥ 2 轮的图上仍 == 1**）+ 入口目标执行次数 == 1 | SC-022 · SC-023 · FR-038 / FR-039 · 裁定 17 |
| **I-12** | **branch 名唯一**（同一源节点含 `__start__`）⇒ 重名 ⇒ 内置 `ValueError` | 登记第二条同名条件边 ⇒ 抛错且消息**点名**分支名与源节点 | SC-024 · FR-040 |
| **I-13** | **零新增公开面**：`vars(compiled)` 的键数仍 == **11**；`freegraph.runtime.__all__` 仍 **23**；`freegraph.graph` 仍 **7**；契约层仍 **21** | 键数 / 符号集合**逐一**相等（单一事实源 = `tests/runtime/_runtime_export_manifest.py`） | SC-016 · FR-037 |
| **I-14** | **零新增错误类型**（只用内置 `KeyError` / `ValueError` 两种新失败信号） | `freegraph.runtime.errors` 的符号集合**不变** + 异常类型断言 | **SC-006 · SC-007 · SC-016** · **FR-021 · FR-022 · FR-033** |

> **规模口径**：**不设**墙钟耗时预算（CI 假红）⇒ 全部判据用**结构口径**
> （执行次数 / 调用次数 / 逐元素相等 / 集合相等）—— 沿用 B5F1 / B5F2 / B7F1 的同款口径。

---

## 7. 与既有实体的**持有面影响**

| 既有实体 | 字段 / 面 | 本 feature 的影响 | 判定 |
|---|---|---|---|
| **`GraphSpec`**（L2） | `conditional_edges: dict[str, Any]`（`superstep.py:219`） | **由恒空改为可承载**（V-8 放宽）· 形态**不变**（仍是 plain mapping） | FR-026 · 裁定 14 |
| **`GraphSpec`** | `channels` / `nodes` / `edges` / `interrupt_before` / `interrupt_after` | **零改动** | FR-026 · 裁定 14 |
| **`SchedulerState`**（L2） | `dynamic_edges: dict[str, tuple[str, ...]]`（`superstep.py:264`） | **复用**（不新增字段）⇒ 条件边目标与 `Command.goto` 目标**同款**落盘 | FR-005 · 裁定 1 / 裁定 13 |
| **`SchedulerState`** | 其余字段（`versions_seen` / `step` / `channel_versions` / `node_versions` / `channels` / `fanout`） | **零改动**（⇒ ⚠️ **MUST NOT** 为 `__start__` 的幂等标记新增字段 —— 其「构造签名与名字逐字不变」是 B7F1 / B9F1 / **B8F1** 的冻结面 · `superstep.py:285-287` ⇒ 幂等标记 MUST 走 `dynamic_edges` 的**键存在性** · 见 §4.3 M-7 注） | FR-005 |
| **`Channel`**（L1） | 路由型（`EphemeralValue`）通道 | **不被写入** · 不进 fresh 视图 · 不进返回键集 ⇒ **通道语义零改动** | FR-028 / FR-029 · 裁定 8 |
| **`NodeSpec`**（L2） | `subscribes` / `run` | **零改动**（路由函数**不是** `NodeSpec.run`） | FR-001 |
| **`CompiledGraph`**（L3） | **持有面**：`vars(compiled)` 的键数 MUST 仍 == **11**（3 私有 + 8 公开） | **零新增私有字段** ⇒ 路由求值复用既有的 `_conditional_edges` 与 `_spec` ⇒ **T-3 不破** | FR-037 · 裁定 1 |
| **`CompiledGraph`** | `_conditional_edges`（既有私有字段） | **由恒空改为**承载 `_conditional_mapping()` 的结果（**零新增**字段） | FR-027 · 裁定 4 |
| **门面 `freegraph.graph`** | `__all__` **7** 个符号 | **一字不动** | I-13 |
| **导出面 `freegraph.runtime`** | `__all__` **23** 个符号 | **一字不动**（FR-037）⇒ 新模块 `src/freegraph/runtime/_routing.py` MUST 是**私有**（**不进** `__all__`） | I-13 |
| **契约层 `freegraph.contracts`** | `__all__` **21** 个符号 | **一字不动** | I-13 |
| **兼容矩阵** | —— | **零新增行**（无新增公开符号） | I-13 |
| **门禁编号** | **G1–G30** | **零新增**（新模块由 **G25** 的目录条目与 **G30** 的署名头扫描**自动**覆盖） | 门禁编号纪律 |

> ⚠ **零新增编译产物私有字段**是 B7F2 的**冻结面**（T-3）⇒ 本 feature MUST NOT 为路由目标
> 新增任何 `CompiledGraph` 字段（FR-005 / FR-037 · 裁定 1）⇒ 触发一律走**既有的** `dynamic_edges` 载体。

---

## 8. 边界（本模型**不**规定的事）

| 项 | 归属 |
|---|---|
| 调度循环（super-step · 触发判定 · 版本号） | **B7F1**（`superstep-contract.md`） |
| **稀疏读 / fresh 读的合并语义** | **B5F2**（`read-contract.md` §3 · §3.3 的**零污染**口径） |
| `path_map` 的**构建期归一化**（list ⇒ `{name: name}` · `Literal` 推断） | **B6F1 / L3**（`_normalize_path_map` · `_stategraph.py:118-159`） |
| `Command` / `Command.goto` 的**语义** | **B9F1**（本 feature 只取**并集**） |
| `Send` fan-out 的**调度** | **B11F1**（本 feature 只**复用** `validate_send` / `make_fanout` · `_fanout.py:56-104`） |
| 节点别名 / `context` 通道（**C21**） | **B8F3**（下游承接 **D-2**）⇒ `context` **不进** fresh 视图 · `path_map` 查表用**节点名** |
| `stream()` 的路由口径 | **B8F2**（下游承接 **D-1**）⇒ MUST 与本 feature 的 `invoke` **逐字同款**（FR-002 · 裁定 1） |
| 图导出里的条件边表达 | **B22F1 / B23F1**（下游承接 **D-4**）⇒ 复用 `targets` / `route_channels` 口径 |
| 路由函数**内部**的 `interrupt()` 语义 | **B10F1**（实测 **E-25** · 本 feature 零新增） |
| checkpoint 落盘 / 状态历史 | **B14F1 / B15F1 / B16F1** |
| async 路由求值 | **v2**（research **DR-10**） |
