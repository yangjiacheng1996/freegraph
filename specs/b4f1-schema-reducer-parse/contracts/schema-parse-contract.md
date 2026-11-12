<!-- authority: yes -->

# 契约：状态 schema 解析（B4F1 · 输入 / 输出 / 错误 / 不变量）

**功能块**: B4F1 · 状态 schema 解析 + 归约器提取 · **Date**: 2026-11-08
**权威来源**: [spec.md](../spec.md)（FR-001…FR-021 · SC-001…SC-018 · 裁定 1–14 · 澄清 Q1–Q10）·
[plan.md](../plan.md) · [research.md](../research.md) · [data-model.md](../data-model.md)
**配套契约**: [binary-criterion.md](./binary-criterion.md)（二元性判据的**权威判定表**）

> **📌 本文件是「解析契约」的**唯一权威**（`<!-- authority: yes -->`）：**字段名与取值域**由 spec FR-020
> 逐字冻结（澄清 Q8）；**实现形态**由 research D-01 / D-02 落定；
> **判据表**在 [binary-criterion.md](./binary-criterion.md)（**不在本文件复制** —— 避免双份权威）。
>
> **⚠️ 这不是面向终端用户的公开 API**：解析入口属 **L2 内部 API**，由 **B5F1**（通道实现）与
> **B6F1**（`StateGraph` 构建器）消费；**公开门面仍是 7 个符号**（B2F2 冻结 · G15 / G19 恒成立）。

---

## 1. 消费方与调用形态

```python
from freegraph.runtime import (
    ChannelSpec, SchemaSpec, InvalidSchemaError, parse_state_schema,
)

spec = parse_state_schema(MessagesState)     # -> SchemaSpec（不可变）
spec.keys                                    # ('messages', 'llm_calls')  ← 保序
spec.channels["messages"].reducer            # <built-in function add>   ← 按引用
spec.channels["llm_calls"].semantics         # 'overwrite'               ← C3 事实
```

| 项 | 约定 |
|---|---|
| **入口** | `parse_state_schema(schema) -> SchemaSpec`（**唯一** · research D-07） |
| **落点** | `freegraph.runtime`（**L2** · 层注册表已登记）· **顶层包不 import 它** ⇒ G1 惰性恒成立 |
| **公开面** | **零新增** —— 契约层仍 **18** 个符号、门面仍 **7** 个（SC-015） |
| **纯函数** | 解析**不**调用归约器、**不**读环境变量、**不**出站、**不**写文件（FR-013 · SC-007 / SC-009） |

---

## 2. 输入契约

| 项 | 约定 | 依据 |
|---|---|---|
| **接受** | **任何「是类 + 有 `__annotations__`」的对象** —— 标准 `TypedDict`（stdlib `typing` 或 `typing_extensions`）· **pydantic 模型** · **dataclass** · 普通类（**上游同款** · 上游 `langgraph/graph/state.py:1818` 的判据**只有**「有 `__annotations__`」） | FR-001 · 裁定 3 · **上游对齐 P3** |
| **判定口径** | **是类**（`isinstance(x, type)`）**且** `hasattr(x, "__annotations__")` ⇒ **上游原样**（上游只判 `hasattr`）· ⚠️ **一处刻意收紧**：**实例**被拒（上游随后 `get_type_hints(instance)` **会抛** `TypeError` ⇒ freegraph 给**可诊断的失败信号**而非崩溃）⇒ **成功路径与上游逐字同款** | FR-001 ① · **上游对齐 P3** |
| **正面路径 MUST 有断言** | **`typing_extensions.TypedDict`**（验收基准同构形态）MUST 被**接受** ⇒ 被误判为「非 `TypedDict`」的次数 == **0**（`typing.is_typeddict` 对其返回 `False` ⇒ 只用它判定会使验收基准不可用） | **SC-018** · 裁定 3 · FR-001 ① |
| **MUST NOT** | 要求继承任何 freegraph 基类 · 要求安装任何第三方包（**内核** MUST NOT import `typing_extensions`；被测 schema 由**测试代码**构造 ⇒ 不违反「零新增依赖声明」） | FR-001 · FR-016 ② · FR-019 |
| **拒绝** | 普通 `dict` · `dict[str, int]` · **模型实例**（**上游同款**：上游随后会崩）⇒ `InvalidSchemaError(reason="not_a_state_schema")`<br>⚠️ **2026-11-12 上游对齐 P3**：**Pydantic 形态的类**（零依赖替身：有 `__annotations__` 但非 `dict` 子类）**不再被拒** ⇒ **被接受**（**上游同款**）<br>⚠️ **空 schema（零个 key）仍然合法** ⇒ 产出**零条**通道（B4F1 的既有冻结口径） | FR-007 ① · 裁定 7 · **上游对齐 P3** |

**示例**（验收基准形态 · `harness/demo/target.py:59-61`）：

```python
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]   # 归约器 = operator.add（身份）
    llm_calls: int                                          # 无归约器 ⇒ overwrite
```

---

## 3. 输出契约（`SchemaSpec` / `ChannelSpec`）

### 3.1 `SchemaSpec`（规格集 · 整份 schema 一条）

| 字段 | 类型 | 约定 |
|---|---|---|
| `channels` | **只读**映射（`types.MappingProxyType`） | **保序**的「key → `ChannelSpec`」；写操作抛 `TypeError` |
| `keys` | `tuple[str, ...]` | **有序** key 序列；顺序 = `get_type_hints` 的插入序（父类在前 · 同名覆盖保持原位 · research D-10） |

### 3.2 `ChannelSpec`（单键规格 · 每个 key 恰一条）

| 字段 | 类型 | 取值域 | 约定 |
|---|---|---|---|
| `key` | `str` | schema 的 key 名 | — |
| `value_type` | 类型对象 | **基类型 `T`** | MUST **不含** `Annotated` 包装（澄清 Q1） |
| `reducer` | 可调用对象 \| **空** | 二元 callable（**按引用**） | 无归约器时为**空**；MUST NOT 被包装 / 复制 |
| `has_reducer` | `bool` | — | `== (semantics == "reduce")` |
| `semantics` | `str` | **恰为** `{"overwrite", "reduce"}` | `overwrite` = 无归约器 ⇒ **默认覆盖**（C3 · 执行在 B5F1） |
| `required` | `bool` | — | 必填性（**只记录不执行** · FR-021 · 校验在 B7F3） |

### 3.3 共同约定

| 项 | 约定 | 依据 |
|---|---|---|
| **不可变** | 两个类型均 `@dataclass(frozen=True, slots=True, kw_only=True)`；改属性抛 `FrozenInstanceError` | FR-010 · research D-01 |
| **不可哈希** | 两个类型均 `__hash__ = None`（**刻意**，非 spec 要求 —— 归约器可能是不可哈希的可调用实例） | research D-01 / D-02 |
| **可比较** | 值相等（字段逐一比较）⇒ 同一 schema 两次解析**相等** | SC-005 |
| **投影** | `to_dict()` → JSON 友好；MUST NOT 含内存地址；两次**逐字一致** | FR-011 · SC-005 · research D-05 / D-06 |

---

## 4. 错误契约（`InvalidSchemaError`）

| 项 | 约定 |
|---|---|
| **落点** | `src/freegraph/runtime/errors.py`（**L2**）· **不进**契约层 18 符号面、**不进**门面 7 符号面 |
| **继承** | `FreegraphError`（内核异常基类）+ `ValueError` ⇒ 用户侧**两种**捕获都有效 |
| **结构化字段** | `key: str \| None`（出错的 key；schema 级错误为**空**）· `reason: str`（原因码） |
| **读字段的路径** | 具体子类 MAY 从 **`freegraph.runtime`** import（**L2 子包** ⇒ 门面 / 契约层公开面**均不变**）；**捕获**用基类 `FreegraphError` 或 `ValueError` 即可（裁定 14 · FR-007 ⑤⑥） |
| **消息** | **英文摘要** + 点名 key —— **只是给人看的**；上层 MUST **无须解析**它 |
| **失败策略** | **快速失败**：按 key 的解析顺序逐个检查，发现**第一个**问题即抛出（MUST NOT 汇总） |

**原因码（封闭取值域）**

| 原因码 | 触发条件 | `key` |
|---|---|---|
| `not_a_state_schema` | schema **不是类**或**无** `__annotations__`（**原名** `not_a_typed_dict` · 2026-11-12 上游对齐 P3 随判定放宽而**改名**：判定口径已不再是「是不是 `TypedDict`」） | **空** |
| `reducer_not_binary` | 末位是 callable 但位置参数数 ≠ 2（含类 / 实例 / 签名不可取） | 有 |
| `annotation_unresolvable` | 注解解析失败（如不可解析的前向引用） | 有 |

**判据**：[binary-criterion.md](./binary-criterion.md) §2（16 类二元性形态）+ §3（2 类提取形态）。

---

## 5. 关键不变式（判据口径见 [data-model.md](../data-model.md) §9）

| # | 不变量 |
|---|---|
| I-1 | 每个 schema key **恰一条** `ChannelSpec`（不多不少） |
| I-3 | `has_reducer == (semantics == "reduce")`；`reducer` 为**空** ⇔ `has_reducer is False` |
| I-4 | `reducer` 非**空**时，其签名恰有 **2 个位置参数**（计数口径见 binary-criterion §1） |
| I-5 | `reducer` 非**空**时，`spec.reducer is` 用户放进 `Annotated` 的那个对象（**身份**判定） |
| I-6 | `value_type` **不含** `Annotated` 包装 |
| I-7 | 两个产物类型均**不可变** |
| I-9 | 投影**不含**内存地址；两次投影**逐字一致** |
| I-10 | 解析**不调用**用户的归约器 |
| I-12 | 必填性**照抄** `__required_keys__` / `__optional_keys__` |
| I-13 | 错误对象必带 `key` + `reason`；`reason` ∈ 封闭集合 |

---

## 6. 边界（本契约**不**承诺的事）

| 不承诺 | 归属 |
|---|---|
| 覆盖语义的**执行**（`LastValue`） | **B5F1** |
| 归约器的**执行**（`operator(current, new)` 的调用时机与合并规则） | **B5F1 / B7F1** |
| 稀疏状态读取（C4） | **B5F2** |
| 条件边 fresh 读（C8） | **B8F1** |
| 必填性的**执行校验** | **B7F3** |
| `StateGraph` 构建器 | **B6F1** |
| Pydantic schema 支持 | **v2.0**（v1.0 无 `[pydantic]` extra） |
| `Annotated[T, SomeChannel]` 的通道注解形态 | **v2.0**（v1.0 由「有无归约器」推导通道） |
| 上游在场时的**实时对照**差分夹具 | **B5F2 / B8F1** |
