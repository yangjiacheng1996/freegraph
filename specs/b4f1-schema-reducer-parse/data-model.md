# Phase 1 · Data Model: B4F1 · 状态 schema 解析 + 归约器提取（`TypedDict` + `Annotated` → 通道规格）

**Date**: 2026-11-08 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) |
**Research**: [research.md](./research.md)

> 本文件描述**解析产物**的实体模型 —— 即 **B5F1**（通道实现）与 **B6F1**（构建器）将要消费的输入。
> 字段名与取值域由 spec FR-020 **逐字冻结**（澄清 Q8）；实现形态由 research D-01 / D-02 落定。
> **判据的权威载体** = [contracts/binary-criterion.md](./contracts/binary-criterion.md)
> （`<!-- authority: yes -->`）—— 本文件只**引用**它，不复制表格（避免双份权威 · research D-03）。

---

## 1. 实体总览

```text
状态 schema（用户提供的 TypedDict）
        │  parse_state_schema(schema)  ← 唯一的解析入口（L2 内部 API · research D-07）
        ▼
   SchemaSpec ──────────────► 规格集（不可变 · 保序）
        │  channels: Mapping[str, ChannelSpec]
        │  keys: tuple[str, ...]
        ▼
   ChannelSpec（每个 key 一条 · 不可变纯数据）
        │  key / value_type / reducer / has_reducer / semantics / required
        │
        ├── reducer: Callable | None   ← 按引用持有（SC-001 身份判定）
        ├── semantics: "overwrite" | "reduce"   ← C3 的「无归约器 ⇒ 覆盖」事实
        └── required: bool             ← 必填性（只记录不执行 · FR-021）

   （解析失败时）
   InvalidSchemaError(key: str | None, reason: str)   ← 结构化字段 + 英文摘要
```

**关系**：`状态 schema` 1 —— N `ChannelSpec`（**每个 key 恰一条** · SC-008）；
`SchemaSpec` 是它们的**保序集合**；`ChannelSpec` 对 `归约器` 是 **0..1** 的引用关系
（无归约器时为**空**）；`ChannelSpec` 对 `语义标记` 是 **1..1**（由「有无归约器」**推导**）。

---

## 2. 状态 schema（输入 · C1）

| 项 | 内容 |
|---|---|
| **形态** | 标准 `TypedDict`（**stdlib** `typing` 或 `typing_extensions` —— 后者由**鸭子判定**兼容） |
| **判定口径** | `typing.is_typeddict(x)` 为真，**或** `x` 同时满足「是类」+「是 `dict` 子类」+「有 `__annotations__`」+「有 `__total__`」（FR-001 ① · 裁定 3） |
| **正面路径判据** | `typing_extensions.TypedDict`（验收基准同构形态）MUST 被**接受** ⇒ 被误判为「非 `TypedDict`」的次数 == **0**（**SC-018**） |
| **示例** | `class MessagesState(TypedDict): messages: Annotated[list[AnyMessage], operator.add]; llm_calls: int` |
| **MUST NOT** | 继承任何 freegraph 基类（FR-001）· 引入第三方依赖（FR-001） |

**不接受的输入**（⇒ `InvalidSchemaError(reason="not_a_typed_dict")`）：普通 `dict` ·
`dict[str, int]` · 模型实例 · Pydantic 模型（v1.0 不支持 · 裁定 7）。

---

## 3. 通道规格（`ChannelSpec`）—— 逐 key 一条

| 字段 | 类型 | 取值域 | 语义 | 冻结依据 |
|---|---|---|---|---|
| `key` | `str` | schema 中的 key 名 | 该通道的**状态键** | FR-020 ① · Q8 |
| `value_type` | 类型对象 | **归约前的基类型 `T`**（`Annotated[T, …]` 的 `T`；无 `Annotated` 时即该 key 的类型） | 「这个 key 到底存什么」 | FR-002 · **Q1** |
| `reducer` | 可调用对象 \| **空** | `Annotated` 元数据**末位**的二元 callable（**按引用**持有）；无归约器时为**空** | 追加语义的执行者 | FR-012 · **Q1** |
| `has_reducer` | `bool` | `True` / `False` | 「是否带归约器」的显式标记 | FR-002 · FR-020 ① |
| `semantics` | `str` | **恰为** `{"overwrite", "reduce"}` | `overwrite` = 无归约器 ⇒ **默认覆盖**（C3）；`reduce` = 有归约器 | FR-006 · FR-020 ① |
| `required` | `bool` | `True` / `False` | **必选 / 可选**（取自 `__required_keys__` / `__optional_keys__`；**只记录不执行**） | FR-021 · **Q2** |

**实现形态**（research D-01）：`@dataclass(frozen=True, slots=True, kw_only=True)` + `__hash__ = None`
（**显式不可哈希**）⇒ **不可变**（改属性抛 `FrozenInstanceError`）、**值相等可比较**、**不可哈希**。

**取值域封闭性**：`semantics` 的取值域**恰为 2 个**；`has_reducer` 与 `semantics` **恒一致**
（`has_reducer == (semantics == "reduce")`）—— 见 §8 不变量 I-3。

---

## 4. 规格集（`SchemaSpec`）—— 整份 schema 一条

| 字段 | 类型 | 取值域 | 语义 |
|---|---|---|---|
| `channels` | **只读**映射（`types.MappingProxyType`） | `str` → `ChannelSpec` | **保序**的「key → 通道规格」映射（research D-02） |
| `keys` | `tuple[str, ...]` | schema 的全部 key | **有序**的 key 序列；顺序 = `get_type_hints` 的**插入序**（父类在前 · 同名覆盖保持原位 · research D-10） |

**实现形态**：`@dataclass(frozen=True, slots=True, kw_only=True)` + `__hash__ = None`；
`__post_init__` 用 `object.__setattr__` 把 `channels` 包成 `MappingProxyType` ⇒ **结构性不可变**
（写操作抛 `TypeError`）。

**「零条规格」是合法形态**：空 TypedDict ⇒ `channels` 为空映射、`keys` 为空元组（**不是**错误）。

---

## 5. 语义标记（`semantics`）—— C3 的「事实」而非「执行」

| 取值 | 触发条件 | 对应上游通道（**B5F1 交付**） | 本 feature 的职责 |
|---|---|---|---|
| `overwrite` | 该 key **无**归约器 | `LastValue`（丢弃左值 · 保留右值） | **只标记**，MUST NOT 执行覆盖 |
| `reduce` | 该 key **有**二元归约器 | `BinaryOperatorAggregate`（`operator(current, new)`） | **只标记**，MUST NOT 调用归约器 |

> **口径提醒**（spec §7）：C3 的**执行**在 **B5F1**；本 feature 只负责把「无归约器」这一事实解析出来。
> 归约器的**调用时机**（super-step 内多次写入如何合并）属 **B5F1 / B7F1**。

---

## 6. 归约器（reducer）—— 按引用持有的二元 callable

| 项 | 内容 |
|---|---|
| **判定** | `Annotated` 元数据**末位**元素是 callable（FR-003）**且**其签名恰有 **2 个位置参数**（FR-004） |
| **计数口径** | 位置专用（positional-only）**+** 位置或关键字（positional-or-keyword）**== 2**；`*args` / `**kwargs` / keyword-only **一律不计入** |
| **候选范围** | **任何 callable** —— **类**与**可调用对象实例**都**不**特殊排除（澄清 Q6 · 裁定 9） |
| **签名取不到** | `inspect.signature` 抛 `ValueError`（如内置 `str` / `max`）⇒ 判为**非二元** ⇒ **拒绝** |
| **持有方式** | **按引用**（MUST NOT 包装 / 复制 / 部分应用）⇒ `spec.reducer is operator.add` 成立（SC-001 · SC-009） |
| **副作用** | 解析期**永不调用**归约器（只读签名）⇒ 解析是**纯函数**（SC-009） |

**权威判据表**（**16 类**二元性形态 + **2 类**提取形态，每条带上游 `路径:行号`）
⇒ [contracts/binary-criterion.md](./contracts/binary-criterion.md)。

---

## 7. 解析错误（`InvalidSchemaError`）—— 非法 schema 的显式失败信号

| 项 | 内容 |
|---|---|
| **落点** | `src/freegraph/runtime/errors.py`（**L2**）· **不进**契约层 18 符号面、**不进**门面 7 符号面（裁定 2 · Q4 · research D-08） |
| **继承** | `FreegraphError`（内核异常基类）+ `ValueError`（与上游同族）⇒ 用户侧**两种**捕获都有效 |
| **结构化字段** | `key: str \| None`（出错的 key；schema 级错误时为**空**）· `reason: str`（原因码） |
| **消息** | **英文摘要** + 点名 key（沿用仓库既有约定 `contracts/errors.py`：「缺省摘要为**英文**」）—— **只是给人看的**，上层 MUST NOT 需要解析它 |

**原因码（取值域封闭 · FR-007 ⑥）**

| 原因码 | 触发条件 | `key` |
|---|---|---|
| `not_a_typed_dict` | schema 不是 `TypedDict`（含 Pydantic 模型 / 普通 dict / 实例） | **空** |
| `reducer_not_binary` | 末位元素是 callable 但位置参数数 ≠ 2（含类 / 实例 / 签名不可取） | 有 |
| `annotation_unresolvable` | 注解解析失败（如不可解析的前向引用） | 有 |

**失败策略**：**快速失败** —— 按 key 的解析顺序逐个检查，发现**第一个**问题即抛出
（MUST NOT 汇总多个问题 · 澄清 Q3 · FR-007 ④）。

---

## 8. 可序列化投影（JSON 友好）

| 投影 | 结构 |
|---|---|
| `ChannelSpec` 的投影 | `{"key": str, "value_type": str（可读文本 · research D-05）, "has_reducer": bool, "semantics": str, "required": bool, "reducer": str \| None（可读标识 · research D-06）}` |
| `SchemaSpec` 的投影 | `{"keys": list[str], "channels": list[上述 dict]}`（**按 `keys` 顺序**） |

**硬约束**：MUST NOT 含**内存地址**形态（`0x…`）⇒ 快照测试不假红（SC-005 · FR-011 ④）；
两次投影**逐字一致**（确定性）。

---

## 9. 不变量（跨实体 · MUST 恒成立）

| # | 不变量 | 判据 |
|---|---|---|
| **I-1** | 每个 schema key **恰一条** `ChannelSpec`；不多不少 | SC-008 |
| **I-2** | `SchemaSpec.keys` 与 `SchemaSpec.channels` 的键集合**恒等**，且 `channels` 的迭代序 **==** `keys` | SC-008 · research D-02 |
| **I-3** | `has_reducer == (semantics == "reduce")`；`reducer` 为**空** ⇔ `has_reducer is False` | FR-002 / FR-006 |
| **I-4** | `reducer` 为**非空**时，其签名恰有 2 个位置参数（FR-004 计数口径） | SC-001 · 判定表 |
| **I-5** | `reducer` 为**非空**时，`spec.reducer is` 用户在 `Annotated` 中放入的那个对象（**身份**，非相等） | SC-001 · SC-009 |
| **I-6** | `value_type` **不含** `Annotated` 包装（= 基类型 `T`） | FR-002 · **Q1** |
| **I-7** | 两个产物类型均**不可变**（改属性抛 `FrozenInstanceError`；`channels` 写操作抛 `TypeError`） | FR-010 · SC-005 |
| **I-8** | 两个产物类型均**不可哈希**（`hash()` 抛 `TypeError`） | research D-01 / D-02（**刻意**，非 spec 要求） |
| **I-9** | 投影**不含**内存地址；两次投影**逐字一致** | SC-005 · FR-011 ④ |
| **I-10** | 解析**不调用**用户的归约器（调用次数 == 0） | SC-009 · FR-013 |
| **I-11** | 解析**不读**环境变量、**不**出站、**不**写文件 | FR-013 · SC-007 |
| **I-12** | 必填性标记**照抄** `__required_keys__` / `__optional_keys__`；未来注解下**一律**为「必选」 | FR-021 ③ |
| **I-13** | 错误对象必带 `key` + `reason`；`reason` ∈ 封闭集合 | SC-017 · FR-007 ⑥ |
| **I-14** | 本 feature **零新增公开 API**：契约层 `__all__` 仍 **18** 个、门面仍 **7** 个 | SC-015 · FR-015 |

---

## 10. 与后续 feature 的交接

| 承接方 | 消费什么 | 本 feature 提供什么 |
|---|---|---|
| **B5F1**（通道实现） | `SchemaSpec` / `ChannelSpec` ⇒ 推导 `LastValue` / `BinaryOperatorAggregate` / `EphemeralValue` | 解析产物 + `semantics` 标记 |
| **B6F1**（`StateGraph` 构建器） | `StateGraph(schema)` 内部调用解析入口 | 解析入口 `parse_state_schema`（L2 内部 API） |
| **B5F2**（稀疏读取 · C4） | 无（只消费通道的运行期语义） | — |
| **B7F3**（调用入参校验） | `required` 标记（**本 feature 只记录，执行在 B7F3**） | 必填性事实 |
