# Data Model · B11F1 · `Send`：动态 fan-out / map-reduce

**Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md) · **Date**: 2026-11-14

> **纪律**：本文件只落**实体 / 形状 / 校验 / 不变量**（可自动判定的部分）⇒
> **MUST NOT** 改写 spec 的任何语义 ⇒ 一切语义以 `spec.md` 为**唯一权威**。
> ⚠️ **私有形状**（前导下划线）⇒ **不进** `freegraph.runtime.__all__`（仍 **23** 个符号）⇒
> **不进** API 兼容矩阵（沿用 B12F1 的 `_concurrency.py` **同款**先例）。

---

## §1 实体总览

| # | 实体 | 层 | 公开性 | 关系 |
|---|---|---|---|---|
| **EM-1** | **`Send`**（fan-out 载荷） | **L1** | **公开**（`freegraph.contracts.Send` ⇒ 门面再导出 `freegraph.graph.Send`） | 1 个 `Send` ⇒ **1 个** fan-out 任务 |
| **EM-2** | **fan-out 载荷**（`Send` / `list[Send]` / `tuple[Send, ...]`） | 运行期 | 内部 | 1 个载荷 ⇒ N 个 fan-out 任务 |
| **EM-3** | **fan-out 任务** | 运行期（L2） | 内部 | 目标节点 + **arg 逐字** + 产生者 + 序号 |
| **EM-4** | **任务标识（TaskId）** | 运行期（L2） | 内部 | **一轮内**任务的**唯一**标识 ⇒ 结果槽的键 |
| **EM-5** | **fan-out 表**（`SchedulerState.fanout`） | 运行期（L2） | 内部（调度状态**由调用方持有**） | 产生者任务（TaskId）⇒ 其产生的载荷 |

---

## §2 EM-1 · `Send`（**L1 的纯数据类** · 逐字冻结）

```python
# src/freegraph/contracts/types.py（**定义在 Command 之前** · 见 research D-06）
@dataclass(frozen=True, slots=True)
class Send:
    node: str
    arg: Any

    __hash__ = None
```

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `node` | `str` | — | **目标节点名**（构造期**不校验** ⇒ 运行期校验 · FR-007） |
| `arg` | `Any` | — | **逐字**传给目标节点的入参（**不校验** · FR-008）。⚠️ **H3**：经 `Send` 调用的目标节点入参可以是**非 `dict` / `None`** ⇒ **C5 / `NodeFunc` 的稀疏 `dict` 注记只适用于标准触发 / `goto`**；该例外 MUST 写进 `NodeFunc` docstring（F-11）。 |

### 2.1 三条**不可动**的属性（**既有断言 C-08 逐字保留**）

| # | 属性 | 依据 |
|---|---|---|
| ① | **不可变**（`frozen=True` ⇒ 改属性抛 `FrozenInstanceError`） | Q7（避免调度器读到旧值的时序坑）· `tests/facade/test_facade.py:288-293` |
| ② | **不可哈希**（**显式** `__hash__ = None`） | frozen dataclass 默认**仍会**生成 `__hash__` ⇒ MUST 显式关掉（`_primitives.py` 的既有说明） |
| ③ | **位置参数与关键字参数两种写法都合法**（⇒ **刻意不用** `kw_only=True`） | 上游 `Send("worker", {"n": 1})` 与 `harness/demo/graph_core.py` 的 C18 用例**逐字**采用位置参数 ⇒ `kw_only=True` 会直接 `TypeError` |

### 2.2 与上游的关系（**一处差异 + 一处已消解**）

| # | 关系 | 承接 |
|---|---|---|
| ① | 上游**可变** + **可哈希** + 带 `timeout`（`langgraph/types.py:704-792`）⇒ **差异** | 偏离登记 **X-5** ⇒ 归**上游对齐批次 P3-8** |
| ② | 上游的 `Send` 与 `Command` **同模块** ⇒ 本 feature **照抄**（`Send` 进 L1 · 同模块）⇒ **不是差异** | 上游对照 **P-11**（SAME） |

---

## §3 EM-2 / EM-3 / EM-5 · 运行期的三个内部形状

### 3.1 fan-out 载荷（**内部**）

```python
# src/freegraph/runtime/_fanout.py（**私有** · research D-11）
@dataclass(frozen=True, slots=True)
class _FanOutTask:
    """一个 fan-out 任务（**一个** `Send` ⇒ **一个**任务）。"""
    target: str              # 目标节点名
    arg: Any                 # **逐字**入参（不校验 · FR-008）
    index: int               # 该 `Send` 在载荷内的下标（0 起）⇒ 归并次序键的一维
    suppresses_static: bool  # 载体标志（**逐任务携带**）：True = 载体 B · False = 载体 A


@dataclass(frozen=True, slots=True)
class _FanOut:
    """一个**产生者任务**的 fan-out 载荷（该任务本次执行的产出 · 键 = TaskId）。"""
    producer: str             # **产生者节点名**（抑制按 (producer, target) 匹配 · 见 §4）
    tasks: tuple[_FanOutTask, ...]
    suppresses_static: bool   # True = **载体 B**（标准触发至多一次）· False = **载体 A**（叠加）
```

| 字段 | 语义 | 依据 |
|---|---|---|
| `_FanOut.producer` | **产生者节点名** ⇒ 载体 B 的静态边抑制 MUST 按 **(producer, target)** 匹配（**同一节点一轮内可执行多次 · 但静态边源只认节点名**） | FR-006 · 裁定 5 · **本节 2026-11-14 分析轮补齐** |
| `_FanOut.tasks` | 该产生者产生的全部 fan-out 任务（**保序**） | FR-001 / FR-004 |
| `_FanOutTask.suppresses_static` | 该任务携带的**载体标志**（**归一形状的信息源** · 同一执行内**全部任务同值**）⇒ **不直接参与**抑制判定 | 裁定 5 的**按载体分列表** · P-10 / P-10b |
| `_FanOut.suppresses_static` | **抑制判定的唯一聚合源**：**载体 B** ⇒ `True`（同一对（产生者, 目标）一轮内**至多一次**）· **载体 A** ⇒ `False`（**叠加** · 上游同款）⇒ MUST 由其 `tasks` 的载体标志聚合 | 裁定 5 的**按载体分列表** · P-10 / P-10b |

> ⚠️ **载体信息 MUST 穿过归一形状**：`_normalize_node_result` 在**已知载体**时逐任务写入
> `suppresses_static`（载体 A ⇒ `False` · 载体 B ⇒ `True`）⇒ 否则 `_FanOut` 无法区分两载体
> （⇒ 本表 2026-11-14 分析轮补齐 · 修复「归一形状丢失载体/产生者」的缺口）。
>
> ⚠️ **判定口径（2026-11-14 收口 · 判定源统一）**：**抑制判定只读 `_FanOut.suppresses_static`**
> （唯一聚合源）⇒ 它 MUST 由其 `tasks` 的 `_FanOutTask.suppresses_static` 聚合而来
> （同一执行内全部同值）；`_FanOutTask` 的字段只为**穿过归一形状**，**不直接参与**抑制判定。

### 3.2 归一后的**内部形状**（**增一个键** · research D-05）

```python
{"writes": dict[str, tuple[Any, ...]], "gotos": tuple[str, ...], "fanout": tuple[_FanOutTask, ...]}
```

| 键 | 语义 | 与 B9F1 的关系 |
|---|---|---|
| `writes` | 待写入（每 key 一个**值序列**） | **逐字不变** |
| `gotos` | `Command.goto` 里的**节点名**目标（保序去重） | **逐字不变** |
| `fanout` | 本次执行产生的 fan-out 任务（**载体 A 的 `goto` 里的 `Send` + 载体 B 的返回值**）⇒ 每个 `_FanOutTask` **自带载体标志** | **新增**（⇒ B9F1 契约**已回溯修订** · **F-10 / T-10**） |

### 3.3 EM-4 · 任务标识（**TaskId**）· research D-01

```python
TaskId = int   # 本轮任务的规范序号（0 起）· 排序键 = TaskId 本身
```

| 任务种类 | TaskId 分配顺序 | 说明 |
|---|---|---|
| **标准触发**（边触发源触发） | **先分配** · 按**目标节点名序** | 上游 PULL 路径 `(PULL, 节点名)` |
| **fan-out**（`Send` 派发） | **后分配** · 按**产生者 TaskId 序 · 载荷内 `Send` 序号** | 上游 PUSH 路径 `(PUSH, idx)`；`idx` 顺序 = 前一超步 `TASKS` 的写入顺序 |

**持久化 `task_id`（F-13）**：内部结果槽 / 次序键用 `TaskId`（`int`）；写入 pending writes 时，
标准任务仍用 **节点名**，fan-out 任务用 **`f"{节点名}:{TaskId}"`**（同一节点一轮内 N 个任务各自唯一）。
⚠️ 该口径**已回溯修订** B10F1 契约（`checkpoint-contract.md` / `interrupt-resume-contract.md`），
并由 B14F1 / B15F1 承接（D-3 / D-8）。

> **排序键 = TaskId 本身**（`int` 字典序）⇒ ⇒ **与 spec FR-005 的「上游任务序」逐字一致**：
> ① **标准触发任务全部在前**（按目标节点名序）· ② **fan-out 任务在后**（按产生者 TaskId 序 ·
> 载荷内 `Send` 序号）。
> ⚠️ **同一节点在一轮内执行多次** ⇒ **各次任务各有独立 TaskId**（产生者用**任务**而不是节点名标识）。
> ⚠️ **2026-11-14 分析轮已回写进 spec 的 FR-005**（分析轮补问 **Q4** · 2026-11-14）· **2026-11-14 复核更正**
> 归并顺序为**上游同款**（`pregel/_algo.py:253-256`）⇒ 三件套口径一致。

### 3.4 EM-5 · 调度状态的**新增字段**（**一个** · 带缺省值）

```python
# src/freegraph/runtime/superstep.py（SchedulerState）
fanout: dict[TaskId, _FanOut] = field(default_factory=dict)
```

| 口径 | 内容 |
|---|---|
| **构造签名** | `SchedulerState()` 的**签名与名字逐字不变**（B9F1 裁定 12 的先例）⇒ **B7F2 / B7F3 / B8F1 / B12F1 零改动** |
| **可变性** | 可变（运行期记账 · 与 `dynamic_edges` 同款） |
| **生命周期** | **一次性**：载荷在下一轮被**消费后清空**（上游 `TASKS` 的 `accumulate=False`）⇒ **MUST NOT** 重复触发；产生者任务**再次执行** ⇒ **整体替换**（含**空集** ⇒ 旧的 fan-out 被清空 · FR-002） |
| **落盘** | **不落盘**（`to_checkpoint` **不含**它）⇒ 理由 = 载荷含**用户对象**（未必可 JSON 序列化）⇒ **DR-02** |
| **键** | **产生者 TaskId** ⇒ 其产生的 `_FanOut`（同一节点在一轮内执行多次时**各次任务分别记录**） |

---

## §4 一个 super-step 内的**阶段**（**八阶段** · 相对 B12F1 只增「②′」）

> ⚠️ **相对 B12F1 的七阶段**（① 触发判定 · ② 任务准备 · ③ 并发执行 · ③′ 判定与落回 ·
> ④ 写入收集 · ⑤ 写入合并 · ⑥ 收尾）⇒ 本 feature **新增「②′ fan-out 任务准备」**，
> 并按 fan-out 语义做**最小口径调整**（③ 结果槽键 / ④ 遍历顺序 / ⑤ 分组顺序，见下表）；
> **合并器与原子性的语义本身不变**。

| 阶段 | 内容 | 本 feature 的变化 |
|---|---|---|
| **① 触发判定** | 枚举本轮被触发的节点（**节点名序**） | ⚠️ **新增一处抑制**：**载体 B** 的 fan-out 覆盖 ⇒ 当**任一** `_FanOut.suppresses_static=True` **且** `_FanOut.producer == 该静态边的源节点` **且** `target == 当前节点` ⇒ 该对（producer, target）的**单元素**边触发组 `("e", producer)` **不计入**（⇒ 该目标**不被该静态边触发**；若**全部**为标准执行 ⇒ **不抑制**）⇒ **多源屏障组（B7F4）不抑制** · **其它 producer 的静态边不抑制** |
| **② 任务准备** | 每个被触发的节点 ⇒ 入参（稀疏读）· 消费已满足的触发源版本 | **零改动**（fan-out 任务**不消费**版本 ⇒ 不是「触发」） |
| **②′ fan-out 任务准备** *(新增)* | 读调度状态的 `fanout` ⇒ 逐个 `_FanOutTask` ⇒ 构造 **fan-out 任务**（目标节点 + **arg 逐字**）⇒ **不消费**任何版本 | **新增阶段**（D-04） |
| **③ 并发执行** | 线程池跑本轮**全部**任务（标准 + fan-out）⇒ 实际并发度 = `min(本轮任务数, min(32, cpu+4))` | ⚠️ **结果槽的键由节点名改为 TaskId**（D-02）⇒ 否则同节点的多任务**互相覆盖** |
| **③′ 判定与落回** | 首个异常（**任务序**）· 成功任务的版本 +1 与跳转目标落回 | ⚠️ **按任务**落回（不是按节点）⇒ `node_versions` **+N**（D-09） |
| **④ 写入收集** | 按**节点名分组**收集待写入（供 `node_writes`）· 同时产出**按 TaskId 序**的 `ordered_writes: list[(TaskId, target, writes)]` | ⚠️ **遍历顺序改为 TaskId 序** ⇒ 同一节点的值序列 = **任务序** ⇒ `_group_writes` 用 `ordered_writes` 遍历（不再按目标节点名排序） |
| **⑤ 写入合并** | 按通道分组 ⇒ 每通道**一次** `Channel.update(values)` | ⚠️ **`_group_writes` 的遍历顺序改为 TaskId 序**（不再按目标节点名排序）⇒ 跨目标顺序 = **上游任务序**（标准任务按目标名序 → fan-out 按产生者 TaskId 序 + `Send` 序号）；`_merge_writes` 的**批量 / 未知 key / 回滚**语义**零改动** |
| **⑥ 收尾** | `executed` / `node_writes` / `steps` | ⚠️ `executed` **逐次列出**（重复可判定 · D-10） |

> ⚠️ **对 B7F1 / B12F1 契约的取代范围（F-14）**：上表的 ②′ 与 ③ / ③′ / ④ / ⑤ / ⑥ 的
> **TaskId 次序键**，在**含 fan-out 任务的轮**里**取代** B7F1 契约 **I-12** 与 B12F1 契约
> **§3 / §5 / §6 / I-3 / I-8** 的字面「节点名序」；**标准触发任务之间**仍按节点名序。
> 该取代 MUST 由 **F-14 / T-15** 的**拆分而不删**回溯修订承接。

---

## §5 校验规则（**V-15…V-21** · 本 feature 新增 · 与 B7F1 的 V-1…V-8 / B9F1 的 V-9…V-14 同族）

| # | 规则 | 失败信号 | 消息要点 | 依据 |
|---|---|---|---|---|
| **V-15** | **载体 B 的载荷形态非法**（空列表 / 空元组 / 元素非 `Send` / 与 `dict` / `Command` 混装） | 内置 **`TypeError`** | 点名**槽位**与**非法元素类型** | FR-001 / FR-008 · 裁定 9 · B9F1 **V-9 / V-10** 同族 |
| **V-16** | **`goto` 槽位里的元素非法**（非 `str` / 非 `Send`） | 内置 **`TypeError`** | 点名**槽位**与**非法元素类型** | FR-001 · B9F1 **V-12** 同族 |
| **V-17** | **`Send.node` 的类型非法**（非 `str`） | 内置 **`TypeError`** | 点名**字段**与**实际类型** | FR-007 · 裁定 10 |
| **V-18** | **`Send.node` 为空串** | 内置 **`ValueError`** | 点名**字段** | FR-007 · 裁定 10 |
| **V-19** | **`Send.node` 不在节点表** | 内置 **`ValueError`** | ⚠️ **同时点名「产生者节点」与「目标节点」**（澄清轮第 2 次 Q3 = **A**） | FR-007 · 裁定 7 · 验收判据 **A3** |
| **V-20** | **`Send.node == Command.PARENT`** | **`NotImplementedError`** | 点名 `__parent__` + 「子图属 v2 能力」 | FR-007 · 裁定 10 · B9F1 **V-14** 同款 |
| **V-21** | **`Send.node` 是 `START` / `END`** | 内置 **`ValueError`** | 点名**哨兵值** | FR-007 · 裁定 10 · B9F1 **V-13** 同族 |

> ⚠️ **校验时机**：**V-17…V-21** 一律在**产生该 `Send` 的那一轮**立即校验
> （⇒ 与 B9F1 裁定 8 的「`goto` 目标不存在 ⇒ 当轮显式失败」**同款**）⇒
> ⇒ **MUST NOT** 推迟到下一轮（那会让产生节点的本轮写入先合并 ⇒ 「一半成功」）。
> ⚠️ **`Send.arg` MUST NOT 被校验**（任意对象 · 含 `None` ⇒ **逐字**传递 · 上游 E-10 同款）。

---

## §6 不变量（**I-1…I-14** · 可自动判定）

| # | 不变量 | 判定口径 |
|---|---|---|
| **I-1** | **fan-out 任务数 == 载荷里的 `Send` 数** | 逐轮断言 |
| **I-2** | **同一目标的一轮内调用次数 == 该对 `Send` 的条数**（**载体 B**） | 逐轮断言（**验收判据 A1**） |
| **I-3** | **fan-out 任务的入参 == 其 `arg` 逐字** | 逐任务断言（**不合并** · **不过滤**） |
| **I-4** | **fan-out 任务在产生它的下一轮执行**（**本轮内 == 0**） | 逐轮断言 |
| **I-5** | **载体 B：同一对（产生者, 目标）的**标准触发**一轮内至多一次**（fan-out 调用次数仍 == `Send` 条数；**同一产生者一轮内多次执行且载体混合 ⇒ 任一载体 B 执行即抑制** · 全部标准执行则不抑制） | 逐轮断言 |
| **I-6** | **标准触发与 fan-out 触发的写入走同一条合并路径**（未知 key ⇒ `InvalidUpdateError`） | 逐轮断言 |
| **I-7** | **归并顺序 == 上游任务序**（标准触发任务按目标节点名序 → fan-out 任务按产生者 TaskId 序 · `Send` 序号；标准任务全部在前） | 重复 **≥ 3** 次 ⇒ 逐项相等 |
| **I-8** | **出错轮不合并**（全部通道的值 == 轮初 · 写入版本不推进） | 逐轮断言 |
| **I-9** | **fan-out 任务不消费触发源版本** | 断言 `versions_seen` 不因 fan-out 变化 |
| **I-10** | **`node_versions` 按成功执行次数递增**（N 次 ⇒ **+N**） | 逐轮断言 |
| **I-11** | **`executed` 逐次列出**（同节点可重复 · 顺序 = TaskId 序） | 逐轮断言 |
| **I-12** | **载荷不落盘**（`to_checkpoint` 不含 `fanout`） | 断言 checkpoint 载荷的键集合 |
| **I-13** | **fan-out 任务的并发度受 `max_concurrency` 约束** | `max_concurrency=1` ⇒ 不重叠；`= N` ⇒ 可重叠 |
| **I-14** | **失败消息同时点名产生者与目标**（**V-19**） | 断言消息含**两个**节点名 |

---

## §7 规模与性能口径

| 项 | 口径 |
|---|---|
| **单轮 fan-out 任务数** | == 载荷里的 `Send` 数 ⇒ **无上限**（**上游同款** · E-6）⇒ 由 `max_concurrency`（并发度）与 `recursion_limit`（轮数 · **B13F1**）兜底 |
| **墙钟时间** | ≈ **最慢的那个任务**（并发 ⇒ E-6：两个各 sleep 0.3s ⇒ 总 **0.308s**） |
| **入参成本** | `arg` **逐字**传递 ⇒ **零拷贝语义**（不复制 · 不序列化）⇒ ⇒ 代价 = **用户的对象** |
| **调度状态增量** | **一个**带缺省值的字段（`fanout`）⇒ 载荷规模 = 本轮产生者的 fan-out 任务数 |
| **零新增线程** | fan-out 任务复用**同一个**线程池（B12F1 的每轮新建 + 每轮关闭 ⇒ 零悬挂线程） |
