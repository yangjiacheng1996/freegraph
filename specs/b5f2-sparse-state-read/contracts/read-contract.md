<!-- authority: yes -->

# 读取契约（Read Contract）—— B5F2 的**唯一权威**

**Feature**: `B5F2` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**核实环境**: CPython **3.11.16** · 上游 `langgraph` **1.2.11**（核实于 2026-11-09）

> **本文件是「状态读取长什么样、怎么用」的**唯一权威**（沿用 B3F1 的层注册表先例：
> 机器可读 Markdown + `<!-- authority: yes -->` 标记；与 B5F1 的 `channel-contract.md` **同款形态**）。
> **spec** 讲「**要什么**」（需求与判据）· 本文件讲「**是什么**」（**逐字冻结的数据契约**）。
> ⚠️ 两者冲突时以 **spec** 为准（spec 是上位文档），并 MUST 回修本文件。
>
> **落位**：**L2**（`src/freegraph/runtime/read.py`）· 导出到 `freegraph.runtime.__all__`
> （**12 → 14** 个符号 · **L2 内部 API** · 不进兼容矩阵 · 裁定 24）。

---

## 1. 读取抽象（两个入口 · 名字逐字冻结）

| 项 | 契约 |
|---|---|
| 宿主模块 | `freegraph.runtime.read`（L2 · 独立文件 · 裁定 24） |
| 导出 | `freegraph.runtime.__all__` **新增 2 个**：`read_channels` · `local_read`（12 → **14**） |
| 入口 1 | `read_channels(channels: Mapping[str, Channel], *, skip_empty: bool = True) -> dict[str, Any]` |
| 入口 2 | `local_read(channels: Mapping[str, Channel], writes: Mapping[str, Sequence[Any]], *, fresh: bool = False) -> dict[str, Any]` |
| 返回类型 | **恒为 `dict`**（上游的返回类型依 `select` 而变 ⇒ 形状差异 · parity **P-05**） |
| **两入口关系** | `read_channels(channels)` 与 `local_read(channels, {}, fresh=False)` 的结果 **MUST 逐字相等**（§3.1 · §4 **I-11** · spec **FR-038** / **SC-033**） |
| key 顺序 | 结果 `dict` 的 key 顺序 == **入参映射的顺序**（B5F1 的 `build_channels` 是**保序**映射） |
| 依赖 | **只依赖标准库**（`collections.abc` · `copy`）· MUST NOT import 第三方（L2 · FR-022） |

### 1.1 入参形态（**冻结**）

| 入参 | 形态 | 说明 |
|---|---|---|
| `channels` | `Mapping[str, Channel]`（**key → 通道**） | 直接消费 B5F1 的 `build_channels` 返回值（**可变** · 保序）⇒ **零转换** |
| `writes` | `Mapping[str, Sequence[Any]]`（**key → 写入值序列**） | 与 B5F1 冻结的 `update(values: Sequence[Any])` **同形** |
| `skip_empty` | `bool`，**缺省 `True`** | `False` ⇒ 读到无值**抛 `EmptyChannelError`**（§2.3） |
| `fresh` | `bool`，**缺省 `False`** | 与上游 `local_read` 的缺省**一致**（research **D-06**）⇒ **B8F1 MUST 显式传 `fresh=True`** |

> **入参形态校验**：两个入口的 `channels` / `writes` 入参 MUST 是**映射**（`Mapping`）⇒ 入参**非映射**时
> MUST 抛 **`TypeError`**（**显式失败** · 不静默降级）。

> ⚠️ `channels` 里的 key 与通道自身的 `key` 属性**不一致**时，以**映射的 key** 为准
> （读取层 MUST NOT 改写通道的 `key`）。

---

## 2. `read_channels` 的语义（**逐字冻结**）

### 2.1 稀疏读（`skip_empty=True` · **缺省**）

- 结果 MUST **只含「当前有值」的通道**的 key；
- **无值通道的 key MUST NOT 出现在结果中**（**C4**）；
- 稀疏判据 MUST 是 `Channel.is_available()`（**恒不抛错**）⇒ **MUST NOT** 以捕获异常驱动控制流
  （机制差异 · parity **P-01**）；
- 结果 MUST 是**新建**的**普通 `dict`**（`type(result) is dict` ⇒ MUST NOT 是 `dict` 的子类）⇒
  调用方改结果 `dict` 的键集合**不影响**通道状态；
- 结果里的**值按引用**（与通道当前值**同一对象**）⇒ MUST **NOT** 深拷贝。

### 2.2 「空」的**精确定义**（**冻结**）

| 通道状态 | 是否出现在结果里 | 结果里的值 |
|---|---|---|
| 「有值」且值非 `None` | ✅ 出现 | 该值 |
| 「有值」且值**为 `None`** | ✅ **出现** | `None`（**「值为 `None`」≠「无值」** · 裁定 9 · parity P-09） |
| 「无值」（从未写入 / 已清空） | ❌ **缺席** | —— |

> ⚠️ 稀疏判据 MUST **NOT** 是「值是否为假值」—— `0` / `""` / `[]` / `False` 都是**有值**，MUST 出现。

### 2.3 不过滤模式（`skip_empty=False`）

- 读到**无值**通道 ⇒ MUST 抛 `EmptyChannelError`（其 `key` 字段指向那个 key）；
- MUST **NOT** 以 `None` 冒充「有值」（否则「无值」与「值为 `None`」混判 ⇒ 违反 B5F1 裁定 5）；
- ⚠️ **与上游分叉但不可观察**：上游的同名分支**以 `None` 填充**，且**全包从未显式使用**
  ⇒ 登记为「**不可观察**的语义差异」（research **D-04** / **DR-1** / parity **P-04**）。

---

## 3. `local_read` 的语义（**逐字冻结**）

### 3.1 两种模式

| 模式 | 视图内容 |
|---|---|
| `fresh=False`（**缺省**） | **只含通道当前值**（稀疏口径同 §2） |
| `fresh=True` | **当前值 + 本任务本次写入**（合并后的视图） |

> ⚠️ **两个稀疏入口 MUST 逐字相等**（spec **FR-038** / **SC-033** · 裁定 33 ④ · §4 **I-11**）：
> `read_channels(channels)` 与 `local_read(channels, {}, fresh=False)` 的结果 **MUST 逐字相等**
> （key 集合**相同** + key **顺序相同** + 逐 key 值**同一对象**）⇒ 二者是**同一稀疏语义的两个入口**、
> **MUST NOT** 分叉（实现上 MUST 共享同一处稀疏读逻辑 ⇒ 全仓仍只有**一个**实现点 · FR-001 / SC-012）。
> ⚠️ 本条**只**约束「**稀疏**读」；**fresh 读**（`fresh=True`）的差异**不受**本条约束
> （那是 §3.2 的合并语义）。

### 3.2 合并语义（**必须复用通道自身的写入语义**）

- 本次写入 MUST 按通道**自身的**写入规则合并（**MUST NOT** 在读取层另写一份归约逻辑）：
  - **覆盖型**（`LastValue`）⇒ 一次写入即覆盖；**多值 ⇒ `InvalidChannelUpdateError`**；
  - **归约型**（`BinaryOperatorAggregate`）⇒ `reducer(current, *writes)`；**通道无值 ⇒ 直存首值**
    （**不调**归约器 · B5F1 裁定 4）；
  - **路由型**（`EphemeralValue`）⇒ 同覆盖型；
- 待写入的 key **不在** `channels` 里 ⇒ MUST 抛 `InvalidChannelUpdateError`（`key` 指向那个未知 key）⇒
  **MUST NOT** 新增错误类型（裁定 19）；
- 归约器在合并中抛错 ⇒ 错误**向上传播**，且通道正式值**不变**。

### 3.3 零污染（**可判定** · 作用域 = **绑定与可用性判定**）

> **📌 本节是「零污染」判据**作用域**的唯一权威**（spec FR-009 / SC-005 · 裁定 29 引用本节）⇒
> spec / plan / tasks / data-model 的同款表述均**以本节为准**（本节与它们**冲突**时以本节为准，
> 并 MUST 回修那些文件）。

- `local_read` MUST **NOT** 改变任何通道的**绑定与可用性判定** —— 读取前后每个通道的
  `is_available()` 的**结果**与 `get()` 的**取值** MUST **不变**（spec FR-009 / SC-005 · 裁定 29）；
- 实现口径 = **副本法**（research **D-07** / **D-09**）：
  ① `copy.copy(channel)` 复制通道 ⇒ ② 在**副本**上 `update(writes[key])` ⇒
  ③ 从**副本**读 ⇒ ④ **丢弃**副本；
- ⚠️ **已知面（**MUST NOT** 计入本节判据 · **MUST NOT** 由读取层修复 · **MUST** 登记）**：
  副本与原通道**浅共享值对象** ⇒ **就地修改型**归约器（如 `a.extend(b)` 一类）会让**原通道的值对象被改写**
  ⇒ ① MUST **NOT** 计入本节的零污染判据（作用域只覆盖**绑定与可用性判定**）⇒
  ② MUST **NOT** 由读取层修复（**深拷贝**会破坏 spec FR-005 的**对象身份语义**、对不可拷贝对象**会失败**、
  且与**上游分叉**）⇒ ③ MUST 在本节与**人工验证记录**中**显式登记**
  ⇒ ⚠️ **上游同样如此**（`checkpoint()` 返回同一对象）⇒ **两侧同构**（research **D-08** / **D-10** / **DR-4**）。

---

## 4. 状态与规模的不变量（**逐条可断言**）

| # | 不变量 | 断言方式 |
|---|---|---|
| I-1 | 结果 `dict` 的 key 集合 == 「`is_available()` 为真的通道」的 key 集合 | 集合相等 |
| I-2 | 结果 `dict` 的 key 顺序 == 入参映射的顺序 | `list(result) == list(channels)`（过滤后） |
| I-3 | `type(result) is dict` | 类型恒等 |
| I-4 | 结果里的每个值与通道当前值**同一对象** | `result[k] is channels[k].get()` |
| I-5 | 读取**前后**每个通道的**绑定与可用性判定不变**（`is_available()` 的结果 + `get()` 的取值） | 前后快照相等（`local_read` 尤其）· ⚠️ **作用域**：「**就地修改型**归约器改写值对象」属**已知面**（§3.3）⇒ **MUST NOT** 计入本条 |
| I-6 | 副本**无** `__dict__`（B5F1 的 `__slots__` 纪律不被破坏） | `not hasattr(copy, "__dict__")` |
| I-7 | 副本的归约器与原通道**同一引用** | `copy.reducer is original.reducer` |
| I-8 | 读取层的出站次数 == 0 · 环境变量读取次数 == 0 | 既有 **G26 / G27** 门禁 + 子进程断言 |
| I-9 | 读取层**不新增**错误类型 | `freegraph.runtime.errors` 的符号集合不变 |
| I-10 | 「值为 `None`」的通道**出现**在结果里 | `result["k"] is None` |
| **I-11** | **两个稀疏入口的结果逐字相等**：`read_channels(channels)` 与 `local_read(channels, {}, fresh=False)` 的结果 **MUST 逐字相等**（key 集合**相同** + key **顺序相同** + 逐 key 值**同一对象**）⇒ 「**稀疏**读」只有一处实现（spec **FR-038** / **SC-033** · 裁定 33 ④） | 两入口结果 `==` 且 `list(result)` 相同且逐 key `is` |

---

## 5. 边界（本契约**不**规定的事）

- **调度循环**（super-step · 触发判定 · 版本号）—— 属 **B7F1**；
- **路由语义**（谁在什么时机读 fresh 视图 · 路由判定）—— 属 **B8F1**；
- **节点返回值的合并**（部分状态 → 通道写入）—— 属 **B7F1**；
- **`managed` 值**（上游 `local_read` 的第四类入参）—— freegraph **不实现**（research **D-18** / **DR-3**）；
- **只读指定 key**（上游 `read_channels` 的 `select` 参数）—— freegraph **恒读全部**（parity **P-05**）；
- **checkpoint 级通道复制**（`from_checkpoint` / `checkpoint()` 语义 · **B14F1**）—— 属 **B14F1**；
  ⚠️ **勿与本契约 §3.3 的「读侧副本」（`copy.copy`）混淆** —— 后者是本 feature 的 fresh 读实现手段。
