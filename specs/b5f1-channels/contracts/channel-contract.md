<!-- authority: yes -->

# 通道契约（Channel Contract）—— B5F1 的**唯一权威**

**Feature**: `B5F1` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**核实环境**: CPython **3.12.3** · 上游 `langgraph` **1.2.11**

> **本文件是「通道长什么样、怎么用」的**唯一权威**（沿用 B3F1 的层注册表先例：
> 机器可读 Markdown + `<!-- authority: yes -->` 标记）。
> **spec** 讲「**要什么**」（需求与判据）· 本文件讲「**是什么**」（**逐字冻结的数据契约**）。
> ⚠️ 两者冲突时以 **spec** 为准（spec 是上位文档），并 MUST 回修本文件
> （**裁定 17 ①** 据此把 §3.1 的 `clear()` 语义回修为「三类一律 ⇒ 无值」）。

---

## 1. 通道抽象（`Channel`）

| 项 | 契约 |
|---|---|
| 抽象基类 | `Channel`（`abc.ABC`）· 运行时**不可实例化** |
| 抽象方法 | `update(values)` · `get()` · `is_available()` |
| 默认实现 | `clear()` = **无操作**（返回假）· **本 feature 的三类通道全部覆写**它（§3） |
| 构造签名 | `Channel(key: str, value_type: Any)` |
| 属性（只读） | `key: str` · `value_type: Any` · `value: Any` · `reducer: Callable \| None` · `typ: Any` · `ValueType: Any` · `UpdateType: Any` |
| 公开属性集合 | **恰好** {`key`, `value_type`, `value`, `reducer`, `typ`, `ValueType`, `UpdateType`}（MUST NOT 更多）<br>⚠️ **2026-11-12 · 上游对齐 P2-a**：由**四项**扩为**七项**（**只增**）—— 新增 `typ` / `ValueType` / `UpdateType`（上游 `BaseChannel` 的同名成员 · `langgraph/channels/base.py:22,28-38`）⇒ 支撑「**每次运行新建通道实例**」的多会话隔离 |
| **上游同款的方法**（**2026-11-12 · P2-a**） | `copy()` · `checkpoint()` · `from_checkpoint(value)` · `consume()` · `finish()`（上游 `base.py:40-120`）⇒ 见 §2.1 |
| **路由型的 `guard`** | `EphemeralValue(key, value_type, guard=True)`（上游 `ephemeral_value.py:23-26`）⇒ `guard=False` 时**一步内多值不报错**、取**末值**（上游的路由用途） |

## 2. 四个操作的语义（**逐字冻结**）

> ⚠️ **2026-11-12 · 上游对齐 P2-a 补**：四个操作**保持不变**（冻结面**未动**）⇒ 另新增
> **§2.1 的上游同款方法**（**只增**）⇒ 目的是让「**每次运行新建通道实例**」得以实现
> （上游同款 · `langgraph/pregel/_checkpoint.py:229-277` 的 `channels_from_checkpoint`）
> ⇒ **多会话隔离**（同一份图规格可并发跑多次而互不干扰）。


| 操作 | 入参 | 返回 | 语义 | 失败行为 |
|---|---|---|---|---|
| `update` | `values: Sequence[Any]` | `bool` | 把「本步的写入序列」并入通道 | 一步内多值 ⇒ `InvalidChannelUpdateError`（**值不变**） |
| `get` | — | 当前值 | 取回通道当前值 | 无值 ⇒ `EmptyChannelError` |
| `is_available` | — | `bool` | 判定「有值 / 无值」 | **恒不抛错** |
| `clear` | — | `bool` | 把通道恢复到「无值」 | 无异常；已是「无值」⇒ 返回假 |

### 2.1 `update()` 返回值的口径（**冻结**）

- 返回「**本次调用是否写入了值**」；
- **写入序列非空 ⇒ 恒为真**（**哪怕**归约后的新值与旧值**逐字相等**）；
- **写入序列为空 ⇒ 为假**（且通道值**不变**）；
- **MUST NOT** 被解释为「通道的值是否发生了变化」；
- **MUST NOT** 被解释为「通道是否**处于**某个状态」。

> **上游对照**：`last_value.py:67` · `binop.py:144` · `ephemeral_value.py:68`（恒真）·
> `pregel/_algo.py:319-324`（调度层用它判断「本步通道是否被更新」）。

### 2.2 `clear()` 返回值的口径（**冻结**）

- 返回「**状态是否真的变化**」：从「有值」清成「无值」⇒ 真；已是「无值」⇒ 假。
- **三类通道一律**适用（裁定 17 ①）：从「有值」清成「无值」⇒ 真（覆盖型 / 归约型 / 路由型同构）。

## 3. 三类通道的语义

### 3.1 `LastValue`（覆盖型 · C3）

| 项 | 契约 |
|---|---|
| 归约器 | **无**（`reducer is None`）· **从不**调用任何归约器 |
| 初始状态 | **无值** |
| 空值推导 | **不推导** |
| 写入（1 个值） | **覆盖**（旧值丢弃）⇒ 值 == 该值 |
| 写入（多于 1 个值） | 抛 `InvalidChannelUpdateError`（**值不变**） |
| 写入（空序列） | 无操作（返回假） |
| `clear()` | **覆写** ⇒ **无值**（已是「无值」⇒ 无操作、返回假）· spec FR-009 / 裁定 17 ① |

### 3.2 `BinaryOperatorAggregate`（归约型 · C2）

| 项 | 契约 |
|---|---|
| 归约器 | **按引用**持有（`channel.reducer is operator.add`） |
| 空值推导 | ① 剥 `Annotated` / `Required` / `NotRequired`（逐层）→ ② 抽象容器映射（`Sequence`/`MutableSequence`→`list`；`Set`/`MutableSet`→`set`；`Mapping`/`MutableMapping`→`dict`）→ ③ `typ()`（成功 ⇒ 初始值为空实例；**失败 ⇒ 初始「无值」，构造不失败**） |
| 空值的**独立性** | 每次构造**新建** ⇒ 两个同类型通道的空值**不是同一对象** |
| 写入（有值） | `值 = reducer(写入前的值, 新值)`；多值**按序**逐个归约 |
| 写入（无值 · 首次） | **直存首个值**（**单值**写入时归约器调用次数 == **0**；多值写入 ⇒ 首个直存、其余按序归约 · 裁定 17 ④） |
| 归约器抛错 | 异常**向上传播**；通道值**不变** |
| 写入（空序列） | 无操作（返回假） |
| `clear()` | **覆写** ⇒ **无值**（**不回到**初始空值） |

### 3.3 `EphemeralValue`（路由型 · C7 / C8）

| 项 | 契约 |
|---|---|
| 归约器 | **无** |
| 初始状态 | **无值** |
| 空值推导 | **不推导** |
| 写入（1 个值） | 覆盖为最新值 |
| 写入（多于 1 个值） | 抛 `InvalidChannelUpdateError`（**值不变**） |
| 写入（空序列） | 无操作（返回假）—— ⚠️ **清空走 `clear()`**，不靠空序列 |
| `clear()` | **覆写** ⇒ **无值**（**清空后的终态**）；已是「无值」⇒ 返回假（幂等） |

## 4. 映射契约（B4F1 → 通道）

| 入口 | 入参 | 返回 | 语义 |
|---|---|---|---|
| `build_channel` | 一个 `ChannelSpec` | 一个 `Channel` | 有归约器 ⇒ `BinaryOperatorAggregate`（归约器**同一引用** · 值类型 = 规格的 `value_type`）；无归约器 ⇒ `LastValue` |
| `build_channels` | 一份 `SchemaSpec` | `dict[str, Channel]`（**保序** · **可变** · 下游可增补内部通道 · research D-14） | 每个 key **恰一个**通道；键序 == `SchemaSpec.keys` 序 |

**规则**

| # | 规则 |
|---|---|
| M-1 | schema → 通道的派生**只**经由上述两个入口（MUST NOT 由调用方拼装通道类） |
| M-2 | **路由通道不由 schema 派生** ⇒ `EphemeralValue` MUST 支持**直接实例化** |
| M-3 | 规格标注「有归约器」但归约器为**空** ⇒ 构造期抛**内置 `ValueError`** |
| M-4 | 映射**保序**；通道数 == key 数 |

## 5. 错误契约

| 错误类型 | 继承 | 结构化字段 | 触发 | 消息 |
|---|---|---|---|---|
| `EmptyChannelError` | `FreegraphError`（**仅**） | `key` | `get()` / `value` 读「无值」通道 | **英文摘要**（点名 key） |
| `InvalidChannelUpdateError` | `FreegraphError` **且** `ValueError` | `key` · `received_count` · `expected_count`（恒为 1） | 一次 `update` 收到多于一个值 | **英文摘要**（点名 key + 计数） |

**规则**

| # | 规则 |
|---|---|
| E-1 | 二者**定义在 L2**（`freegraph.runtime`）⇒ **不进**契约层 18 符号面 / 门面 7 符号面 |
| E-2 | 用户侧 `except FreegraphError` **均**能捕获；读字段 MAY 从 `freegraph.runtime` import 具体子类 |
| E-3 | 错误对象 **MUST NOT** 携带用户写入的**值本身**（只带 `key` 与计数） |
| E-4 | `EmptyChannelError` **MUST NOT** 继承 `ValueError`（「读到无值」是正常信号） |
| E-5 | 构造期的**编程错误**用**内置** `TypeError` / `ValueError`（MUST NOT 新增错误类型承载它） |

## 6. 状态与规模的不变量（**逐条可断言**）

| # | 不变量 |
|---|---|
| I-1 | **公开**属性（7 个 `property`）集合**恰为** {`key`, `value_type`, `value`, `reducer`, `typ`, `ValueType`, `UpdateType`} **且** **实例槽位**集合 ⊆ {`_key`, `_value_type`, `_value`, `_reducer`} ∪ {`_guard`}（澄清轮 **Q15** · MUST NOT 以 `dir()` / `vars()` 判定）· **子类 MUST NOT 引入新槽**（除 `EphemeralValue` 的 `_guard` · 上游同款）（⇒ 实例 MUST NOT 拥有 `__dict__` · 裁定 17 ①）· **公开属性的收集 MUST 沿 MRO**（`type(ch).__dict__` 只含该类自身定义的属性）<br>⚠️ **2026-11-12 · 上游对齐 P2-a**：由 4 项扩为 **7 项**（**只增** · 上游 `BaseChannel` 同名成员） |
| I-2 | 通道**不持有**其它通道 / 状态表的引用 ⇒ ① **引用类型白名单**（直接引用集合中 MUST NOT 出现 `dict` / `SchemaSpec` / 其它 `Channel` 实例 · 裁定 17 ③）；② `len(gc.get_referents(ch))` 与 schema 的 key 数**无关**（**辅助**判据 · **探针口径逐字冻结** · MUST NOT 用墙钟耗时 / 数行） |
| I-3 | 「无值」与「值为 `None`」严格可分 |
| I-4 | `is_available()` **恒不抛错**；`get()` 在无值时**必抛** `EmptyChannelError` |
| I-5 | `value` 属性与 `get()` **同义**（无值时同样抛 `EmptyChannelError`）⇒ 不存在第三种语义 |
| I-6 | `update()` 返回值 = 「本次调用是否写入了值」 |
| I-7 | 一步内多值冲突 ⇒ 值**不变** |
| I-8 | 归约器抛错 ⇒ 值**不变** |
| I-9 | 归约器**按引用**持有 |
| I-10 | 归约型通道的**首次**写入（通道无值时）**单值**写入 ⇒ 归约器调用次数 == **0**（多值写入 ⇒ 首个直存、其余按序归约 · 裁定 17 ④） |
| I-11 | 两个同类型归约型通道的空值**不是同一对象** |
| I-12 | 清空后**一律**「无值」（**三类通道同构** · 含归约型）；清空**不**回到初始状态（规范性表述见 spec **FR-022 ③**） |
| I-13 | 覆盖型 / 路由型初始「无值」；归约型初始「有值（空值）」或「无值」（类型不可实例化时） |
| I-14 | 通道**浅引用**用户对象（`channel.value is 传入对象`） |
| I-15 | 通道**不校验**写入值类型、**不重做**二元性校验 |
| I-16 | 构造期：不可调用的归约器 ⇒ `TypeError`；「有归约器但为空」⇒ `ValueError` |
| I-17 | 映射保序；通道数 == key 数 |
| I-18 | 归约型通道的 `reducer` **就是**规格里的引用 |
| I-19 | 导入无副作用（`sys.modules` 增量中非标准库条目数 == 0 · 环境变量读取 == 0 · 出站 == 0） |
| I-20 | 通道**无同步原语**；写入入口**只有** `update()`（**2026-11-12 · P2-a**：公开可调用项集合随上游同款方法扩为 {`update`, `get`, `is_available`, `clear`, `copy`, `checkpoint`, `from_checkpoint`, `consume`, `finish`} ⇒ 其中**写入**入口仍**只有** `update()`） |
| I-21 | 错误结构化字段齐备；**不携带**用户值 |
| I-22 | 二者均可被 `except FreegraphError` 捕获；`EmptyChannelError` **不是** `ValueError` |
| I-23 | 名字面逐字一致（4 操作 + 4 属性 + 4 类名 + 2 映射入口 + 2 错误名） |

> **完整不变量表**见 [../data-model.md](../data-model.md) §4（同一批条款的展开版）。

## 7. 边界（本契约**不**规定的事）

| # | 不规定 | 归属 |
|---|---|---|
| B-1 | 「读到无值的 key 时返回什么」（稀疏读出口径） | **B5F2** |
| B-2 | 何时调用 `clear()`（super-step 边界） | **B7F1**（调度层）· ⚠️ 步末 MUST **只**对**路由型**通道调用（覆盖型 / 归约型在步末**保留**其值，与上游 `update([])` 的 no-op 效果逐字同构 · 裁定 17 ②） |
| B-3 | 通道状态的 checkpoint / 复制 / 回滚 | **B14F1** |
| B-4 | 通道的**相等判定**与**可打印表示** | **B14F1**（research DR-1） |
| B-5 | `value_type` 的**类型可读文本**投影 | **B4F1** / **B14F1**（research DR-2） |
| B-6 | 上游的 `Overwrite` 旁路值 | v1.0 **不做**（spec FR-018） |
