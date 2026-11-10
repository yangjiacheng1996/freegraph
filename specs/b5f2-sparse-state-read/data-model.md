# 数据模型（Phase 1）—— B5F2 · 稀疏状态读取 + 差分测试夹具

**Feature**: `B5F2` · **Spec**: [./spec.md](./spec.md) · **Plan**: [./plan.md](./plan.md)
**契约权威**: [contracts/read-contract.md](./contracts/read-contract.md) ·
[contracts/differential-fixture.md](./contracts/differential-fixture.md)

> **落位**：**L2**（`src/freegraph/runtime/read.py`）· 导出到 `freegraph.runtime.__all__`（12 → **14**）。
> **零新增错误类型**（复用 B5F1 的 `EmptyChannelError` / `InvalidChannelUpdateError`）。

---

## 1. 实体总览（**数据模型 = 纯数据 · 无对象引用字段** · 宪法原则 VII / G13）

```
                        ┌──────────────────────────────┐
   通道映射              │   Channel 映射（读入参）      │
   (B5F1 产出)  ───────▶│   Mapping[str, Channel]      │
                        │   · 可变 · 保序              │
                        └───────────┬──────────────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              │                                           │
              ▼                                           ▼
   ┌────────────────────────┐              ┌──────────────────────────┐
   │ 稀疏读取结果            │              │ fresh 读视图              │
   │ read_channels(...)     │              │ local_read(..., fresh)   │
   │ → dict[str, Any]       │              │ → dict[str, Any]         │
   │ · 只含有值的 key        │              │ · 当前值 + 本次写入        │
   │ · 值按引用              │              │ · 绑定与可用性判定零污染     │
   └────────────────────────┘              └────────────┬─────────────┘
                                                         │
   ┌────────────────────────┐                          │ 副本法（丢弃副本）
   │ 待写入映射              │──────────────────────────┘
   │ Mapping[str, Sequence] │
   │ · 与 update(values) 同形│
   └────────────────────────┘
```

---

## 2. 实体与字段（**逐字冻结**）

### 2.1 读取入口（**两个** · 名字逐字冻结）

| 实体 | 字段 / 签名 | 约束 |
|---|---|---|
| `read_channels` | `(channels: Mapping[str, Channel], *, skip_empty: bool = True) -> dict[str, Any]` | 返回**恒为 `dict`** · `skip_empty` **缺省 `True`** |
| `local_read` | `(channels: Mapping[str, Channel], writes: Mapping[str, Sequence[Any]], *, fresh: bool = False) -> dict[str, Any]` | `fresh` **缺省 `False`**（与上游一致 · research **D-06**） |

> **单一抽象点**：状态读取 MUST 只有这两个入口（spec FR-001 · 裁定 1）⇒ 全仓**无第三个**读取实现点。

### 2.2 通道映射（读入参）

| 字段 | 类型 | 约束 |
|---|---|---|
| key | `str` | **唯一** · 顺序 == 映射顺序（保序） |
| value | `Channel`（B5F1 冻结的抽象） | **只读**（读取层 MUST NOT 改写通道的 `key` / `value_type` / `reducer`） |

**来源**：B5F1 的 `build_channels(schema_spec)` 返回值（**可变 `dict`** · 保序 · B5F1 research **D-14**）。

### 2.3 待写入映射（`local_read` 的写入入参）

| 字段 | 类型 | 约束 |
|---|---|---|
| key | `str` | MUST 在通道映射中**存在** ⇒ 否则 **显式失败**（`InvalidChannelUpdateError`） |
| value | `Sequence[Any]` | 与 B5F1 的 `update(values: Sequence[Any])` **同形**；**空序列** ⇒ 无操作 |

### 2.4 读取结果（**普通 `dict`**）

| 项 | 约束 |
|---|---|
| 类型 | `type(result) is dict`（**MUST NOT** 是 `dict` 的子类） |
| key 集合 | == 「`is_available()` 为真」的通道集合 |
| key 顺序 | == 入参映射顺序（过滤后） |
| 值 | 与通道当前值**同一对象**（浅引用 · MUST NOT 深拷贝） |

> ⚠️ **已知面（**不计入**零污染判据 · **不修** · 裁定 29）**：结果里的值与通道的值**同一对象** ⇒
> **就地修改型**归约器（如 `a.extend(b)` 一类）会**改写原通道的值对象** ⇒ 该情形**MUST NOT** 计入
> 「零污染」判据（该判据的作用域 = **绑定与可用性判定**）· **MUST NOT** 由读取层修复（**深拷贝**会破坏
> spec FR-005 的对象身份语义 · 对不可拷贝对象会失败 · 与上游分叉）⇒ MUST 显式登记（spec Edge Cases ·
> research **D-10** / **DR-4**）。

### 2.5 图规格（差分夹具的输入 · **纯数据**）

| 字段 | 类型 | 约束 |
|---|---|---|
| `schema` | `{key: (value_type, reducer \| None)}` | **纯数据**（不携带 `TypedDict` 类） |
| `schema_typed` | `TypedDict`（**运行时动态构造 · 一个**） | `typing.TypedDict("名称", {...})` **函数式**写法 ⇒ 两侧消费**同一个对象** |
| `nodes` | `[(name, fn)]`（**有序**） | `fn(state: dict) -> dict`（返回**部分**状态）· **确定性** · 零网络 |
| `initial_input` | `dict` | 按「**一次写入**」进通道 |
| `conditional_edges` | **恒空**（本 feature） | 非空 ⇒ **显式失败** |
| `model_factory` | **恒空**（本 feature） | 「模型工厂」钩子 ⇒ 非空 ⇒ **显式失败**（MUST NOT 自行实现 fake 注入 · FR-036 · 裁定 26） |

---

## 3. fresh 读的**状态机**（合并语义的逐格判定）

> 合并 MUST 走通道**自身的**写入语义（**MUST NOT** 在读取层另写归约逻辑 · 裁定 4）。

| 通道类型 | 通道状态 | 待写入 | 视图里的值 | 原通道的**绑定与可用性判定** | 异常 |
|---|---|---|---|---|---|
| 覆盖型 | 有值 | 1 个 | 该写入值（覆盖） | **不变** | —— |
| 覆盖型 | 有值 | ≥ 2 个 | —— | **不变** | `InvalidChannelUpdateError` |
| 覆盖型 | **无值** | 1 个 | 该写入值 | **不变** | —— |
| 归约型 | 有值 | n 个 | `reducer(current, *writes)` | **不变** | 归约器抛错 ⇒ **向上传播** |
| 归约型 | **无值** | n 个 | **直存首值**（**不调**归约器 · B5F1 裁定 4），其余按序归约 | **不变** | 同上 |
| 路由型 | 任意 | 1 个 | 同覆盖型 | **不变** | —— |
| 路由型 | 任意 | ≥ 2 个 | —— | **不变** | `InvalidChannelUpdateError` |
| **任意** | 任意 | —— | —— | **不变** | 待写入的 key **不在**映射里 ⇒ `InvalidChannelUpdateError` |

> **「绑定与可用性判定」** = 通道的 `is_available()` 的**结果** + `get()` 的**取值** —— 这是**零污染**判据的
> **作用域**（spec FR-009 / SC-005 · 裁定 29）。
>
> ⚠️ **已知面（**MUST NOT** 计入上表的「不变」 · **MUST NOT** 修 · 裁定 29）**：**就地修改型**归约器
> （如 `a.extend(b)` 一类）会**改写原通道的值对象**（副本与原通道**浅共享值对象**）⇒ 上表的「不变」指
> **绑定与可用性判定**不变，**不含**「值对象逐字相等」⇒ **MUST NOT** 由读取层修复（**不深拷贝** ·
> 会破坏 spec FR-005 的对象身份语义 · 与**上游分叉**）⇒ MUST 显式登记（spec Edge Cases ·
> research **D-10** / **DR-4**）。

**状态转移**：读取是**无状态**的纯函数（除**副本**外不写任何东西）⇒
「读前判定 == 读后判定」是**恒等式**（不变量 **I-5**）。

---

## 4. 差分夹具的**三项投影**（比对单位）

> 📌 **逐项差异 == 0 的判据归属**（裁定 32 ①）：**节点入参** → `SC-032` · **输出状态** → `SC-006` ·
> **事件序列** → `SC-007`（`SC-013` 判「投影数 == 3」）⇒ **三项投影逐项**都有可数判据。

| 投影 | 形态 | 归一化 | 上游来源 |
|---|---|---|---|
| **节点入参** | `dict[str, Any]` | key 集合 + 逐 key 值 | 节点函数**内部**留存（**执行前**的副本） |
| **输出状态** | `dict[str, Any]` | key 集合 + 逐 key 值 | `invoke()` 返回值（**无值 key 缺席**） |
| **事件序列** | `[(步序, 节点名, 写入)]` | 三元组；「写入」= **节点函数返回的部分状态（原样 · 未归约）**；**无更新 ⇒ 写入为 `None`** | `stream(stream_mode="updates")` |

---

## 5. 验证规则（**来自 FR 的可判定约束**）

| # | 规则 | 触发的失败 |
|---|---|---|
| V-1 | 通道映射里的 key **唯一** | 映射本身保证（`dict`） |
| V-2 | 待写入的 key MUST 在通道映射中 | `InvalidChannelUpdateError` |
| V-3 | 图规格的 `nodes` MUST 非空且**节点名唯一** | 夹具**显式失败** |
| V-4 | 图规格的 `conditional_edges` MUST 为空 | 夹具**显式失败**（裁定 15） |
| V-4b | 图规格的 `model_factory` MUST 为空（本 feature **恒为纯本地**） | 夹具**显式失败**（FR-036 · 裁定 26） |
| V-5 | 节点返回的 key MUST 全在 schema 里 | 夹具**前置校验失败**（research **D-15** / **DR-2**） |
| V-6 | 节点函数 MUST **确定性** · 零网络 | 夹具**前置校验失败**（人工审查 + 无出站门禁） |
| V-7 | `schema` 的每个 key MUST 有值类型 | 构造 `TypedDict` 失败 ⇒ **显式失败** |

---

## 6. 规模与边界（**不变量**）

| 项 | 值 |
|---|---|
| schema 的 key 数 | 典型 **2–20**（`target.py` = 2） |
| 读取结果的 key 数 | ≤ schema 的 key 数（**稀疏** ⇒ 实际更少） |
| 时间复杂度 | `O(通道数)`（单遍遍历 · 无排序 · 无拷贝） |
| 空间复杂度 | `O(有值通道数)`（结果 `dict`）+ `O(通道数)`（副本，**瞬时**） |
| 副本的**瞬时**性 | 副本活到 `local_read` 返回即**丢弃** ⇒ 原通道的**绑定与可用性判定零污染**（⚠️ 已知面见 §3 的 ⚠ · **不计入**该判据 · **不修**） |
| ⚠️ **MUST NOT** 用墙钟耗时做断言 | CI 假红（沿用 B5F1 的同款纪律） |

---

## 7. 边界（**本 feature 不做的事**）

- **调度循环** / super-step / 触发判定 / 版本号 —— **B7F1**；
- **路由语义**（何时读 fresh 视图 · 路由判定）—— **B8F1**；
- **节点返回值 → 通道写入**的合并 —— **B7F1**；
- **managed 值**（上游 `local_read` 的第四类入参）—— **不实现**（research **D-18** / **DR-3**）；
- **只读指定 key**（上游 `select`）—— **不实现**（freegraph 恒读全部）；
- **checkpoint 级通道复制**（`from_checkpoint` / `checkpoint()` 语义）—— **B14F1**；
  ⚠️ **勿与本 feature 的「读侧副本」（`copy.copy` · fresh 读的实现手段）混淆**；
- **新增错误类型** —— **零新增**（复用 B5F1 的两个）。
