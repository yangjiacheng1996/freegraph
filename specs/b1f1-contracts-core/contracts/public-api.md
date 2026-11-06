# 公开 API 冻结契约（public-api.md）

**功能块**: B1F1 · 契约层骨架 · **Date**: 2026-11-05
**权威来源**: [spec.md](../spec.md) 的 FR-002…FR-006 / FR-014 / FR-015 + 15 条澄清记录
**契约性质**: **冻结面** —— 本文件列出的符号名、字段名、属性名、常量值一经落地，后续 30 个 feature 全部引用；改名成本极高

---

## 0. 公开符号面

```python
from freegraph.contracts import (
    StateDict,          # 状态字典（类型别名）
    Command,            # 命令原语
    StateSnapshot,      # 状态快照
    RunConfig,          # 运行配置
    FreegraphError,     # 内核异常基类
    InvalidUpdateError,   # ├ 节点返回了 schema 中不存在的 key
    GraphRecursionError,  # ├ 递归超限
    GraphInterrupt,        # └ 节点主动中断
)
```

**恰好 8 个**。不多、不少：

> 本节是**公开符号面的唯一手工维护点** —— spec / plan / tasks / `README.md` 兼容矩阵中的同款
> 清单均以本节为准（spec FR-015）。

- `__all__` **集合相等**断言为这 8 个名字（集合断言才能抓住「偷偷多导出一个」）。
- 契约层**不得**出现名为 `Send` / `interrupt` 的公开符号（它们归 B2F1）。
- `import freegraph.contracts` **不得**连带加载任何 freegraph 内部层模块。

---

## 1. `StateDict` —— 状态字典

```python
StateDict: TypeAlias = dict[str, Any]
```

| 契约点 | 内容 |
|---|---|
| **形态** | **类型别名**，与 `dict[str, Any]` **完全等价**（同一类型，不是子类型） |
| **语义** | 图状态的**稀疏**字典：只含「当前有值」的 key |
| **空 channel 的 key** | **不得**出现在节点入参中 |
| **值为 `None` 的 key** | **算**有值，**必须**出现在节点入参中（与上一条不可混淆） |
| **参数化** | **不支持** `StateDict[MySchema]` 写法 |
| **用户 schema** | 由用户自己的 `TypedDict`（或 Pydantic）表达；freegraph **不要求**继承任何基类，**不校验**节点注解与 schema 的一致性 |

**想要字段补全怎么办**：直接用自己的 `TypedDict` 标注节点签名 ——

```python
from typing import TypedDict
from freegraph.contracts import StateDict

class MyState(TypedDict):
    messages: list[str]
    llm_calls: int

def node(state: MyState) -> MyState:      # 编辑器在这里补全 messages / llm_calls
    ...

def loose(state: StateDict) -> StateDict:  # 宽松写法，同样被接受
    ...
```

---

## 2. `Command` —— 命令原语

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class Command:
    goto: str | Sequence[str] | None = None
    update: StateDict | None = None
    resume: Any | None = None

    PARENT: ClassVar[Literal["__parent__"]] = "__parent__"
```

### 2.1 三个语义位

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `goto` | `str \| Sequence[str] \| None` | `None` | 跳转目标。**单个** = 节点名字符串；**一组** = 任意序列（元组、列表都收）。目标**只能是节点名**（`Send` 归 B2F1） |
| `update` | `StateDict \| None` | `None` | 要写入图状态的部分更新 |
| `resume` | `Any \| None` | `None` | 恢复值（配对 `interrupt`，后者归 B2F1） |

### 2.2 填写规则（**冻结**）

| 情形 | 结果 |
|---|---|
| 三者**全为 `None`** | **抛 `FreegraphError`**（构造期 fail fast，对象不返回） |
| 至少一位**不是 `None`** | 合法 |
| 三者组合 | **任意组合**，互不排斥（「跳转+写入」、「恢复+跳转」均可） |
| 某位**显式给了但内容为空**（`update={}` / `goto=()`） | 合法 —— 语义为「该位不产生动作」；与「未提供」（`None`）**严格区分** |

### 2.3 `Command.PARENT`

| 项 | 内容 |
|---|---|
| 值 | `"__parent__"` |
| 形态 | `ClassVar[Literal["__parent__"]]` —— 类属性，**非**实例字段 |
| 语义 | 「跳向最近的父图」 |
| 连带约定 | 节点名 `__parent__` 视为**保留名**，运行时不得与「跳向父图」产生歧义（校验归 B7F2 / B9F1） |

### 2.4 用法

```python
Command(goto="review")                          # 跳到一个节点
Command(goto=("a", "b"))                         # 跳到一组节点（并行）
Command(update={"llm_calls": 1})                # 只写状态
Command(goto=Command.PARENT)                    # 跳向最近的父图
Command(goto="x", update={"n": 1})              # 跳转 + 写入（合法组合）
Command(update={})                              # 合法：该位不产生动作
Command()                                       # 非法 → FreegraphError
```

### 2.5 不变式

- 浅不可变：对象本身不可改（`frozen=True`），但 `update` 装的是 `dict`、`goto` 装列表时**其内容仍可变**。
- `goto` **不归一化**：传元组存元组、传列表存列表（与冻结注解逐字一致）。
- `Command()` **必然**抛 `FreegraphError`。

---

## 3. `StateSnapshot` —— 状态快照

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class StateSnapshot:
    values: StateDict
    next: tuple[str, ...]
    config: RunConfig
    metadata: Mapping[str, Any]
    created_at: str
    tasks: tuple[Any, ...]
    interrupts: tuple[Any, ...]
```

| 字段 | 类型 | 语义 |
|---|---|---|
| `values` | `StateDict` | 该时刻的**完整**状态（稀疏映射） |
| `next` | `tuple[str, ...]` | 本步之后要执行的节点名。**空元组** = 无后续节点 |
| `config` | `RunConfig` | 取回该快照所用的运行配置 |
| `metadata` | `Mapping[str, Any]` | 附加信息（可为空映射，只读） |
| `created_at` | `str` | 创建时刻 —— **UTC 的 ISO-8601 字符串**，例 `2026-11-05T10:20:30.123456+00:00`；**必填** |
| `tasks` | `tuple[Any, ...]` | 本步任务列表（元素类型归 **B2F1**） |
| `interrupts` | `tuple[Any, ...]` | 本步发生的中断（元素类型归 **B2F1**） |

**校验规则**

- 七字段**全部必填**（无缺省值）—— 不存在「字段缺失的快照」。
- `created_at` MUST 一律为 UTC ISO-8601 —— **各持久化后端不得各写各的**。
- 本 feature **不提供**「生成快照」的功能（那是运行时的活），只定义形状与格式。

**构造期的行为边界**

- **容器防御性拷贝**：构造时把 `metadata` 拷为自身持有的新容器（`dict(metadata)`）——不与调用方传入的对象共用；拷贝为**浅拷贝**（嵌套容器仍与调用方共享）。
- **只拷 `metadata`**：快照**没有** `tags` 字段（`tags` 属 `RunConfig`）。
- **构造期只执行两条冻结校验**（`Command()` 三语义位全空、`RunConfig.from_dict` 未知键）——**不在构造期校验值**：`created_at` 格式不符**不抛错**（格式由生产者保证），`thread_id` 的实际类型、`tags` 的元素类型同样不校验。
- 快照的 `metadata` 与配置的 `metadata` **一律声明为 `Mapping[str, Any]`**（只读映射）；实现时持有 `dict` 实例——注解与实现容器分离。

---

## 4. `RunConfig` —— 运行配置

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class RunConfig:
    thread_id: str | None = None
    context: Any = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    tags: Sequence[str] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any], *, ignore_unknown: bool = False) -> "RunConfig": ...
```

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `thread_id` | `str \| None` | `None` | **会话**标识 |
| `context` | `Any` | `None` | **运行时上下文** —— 独立通道（C21），**不塞进 `configurable`** |
| `metadata` | `Mapping[str, Any]` | 空映射 | 附加信息，**不参与标识** |
| `tags` | `Sequence[str]` | 空序列 | 附加标签，**不参与标识** |

**构造期的行为边界**

- 四个字段**全部可选**，均有缺省值 ⇒ 构造无前置条件。
- **容器防御性拷贝**：构造时把 `metadata` / `tags` 拷为自身持有的新容器（`dict(...)` / `tuple(...)`）——不与调用方传入的对象共用；拷贝为**浅拷贝**（嵌套容器仍与调用方共享）。
- **构造期只执行两条冻结校验**——`from_dict` 的未知键判定是其中之一；`thread_id` 的实际类型、`tags` 的元素类型等**不在构造期校验**（只做类型注解）。
- `metadata` 声明为 `Mapping[str, Any]`（只读映射），实现时持有 `dict` 实例；需要新增键时由调用方**重建整个配置**，而非就地修改。

### 4.1 `from_dict` —— 裸 dict 构造路径

| 情形 | 结果 |
|---|---|
| 键全部在四字段内 | 正常构造 |
| 出现四字段之外的键，**默认** | **抛 `FreegraphError`**，消息**点名该键**（当场暴露 `threadId` 这类拼写错误） |
| 出现四字段之外的键，`ignore_unknown=True` | **忽略**未知键，正常构造 |

**为什么要这条路**：智能体上下文多为 JSON，用户手上天然是**裸 dict**。有了它，运行入口将来（归 B7F3）就能容忍裸 dict 传入，调用方不必逐字段搬运。

```python
RunConfig.from_dict({"thread_id": "t-1", "tags": ["a"]})           # ✅
RunConfig.from_dict({"threadId": "t-1"})                            # ❌ FreegraphError（点名 threadId）
RunConfig.from_dict({"thread_id": "t-1", "extra": 1}, ignore_unknown=True)  # ✅（extra 被忽略）
```

### 4.2 标识职责（C22 · 立项书 §5.3.1）

| 标识 | 产生方 | 用户可指定？ |
|---|---|---|
| `thread_id` = **会话**标识 | 用户经 `RunConfig` 传入 | ✅ |
| `run_id` = **单次运行**标识 | freegraph 每次 `invoke` / `stream` 开始时生成 | ❌ 不可指定、不可覆盖，**且不进** `RunConfig` 字段清单 |

---

## 5. 异常体系

```text
Exception
└── FreegraphError            ← 统一基类（上层只捕获它即可兜住全部内核错误）
    ├── InvalidUpdateError    .invalid_keys
    ├── GraphRecursionError   .recursion_limit / .current_step
    └── GraphInterrupt        .payload
```

### 5.1 构造签名

```text
InvalidUpdateError(invalid_keys: Iterable[str], *, message: str | None = None)
GraphRecursionError(recursion_limit: int, current_step: int, *, message: str | None = None)
GraphInterrupt(payload: Any, *, message: str | None = None)
```

- 结构化属性作**位置参数**；`message` 为**可选关键字**，缺省时由属性自动生成一句摘要。
- 错误消息**只是给人看的摘要** —— 上层 MUST NOT 需解析消息才能取到细节。
- **自动生成的摘要 MUST 为英文**（面向下游消费者与上游报错的逐条对照）；三个异常类的 docstring 沿用项目现有的中文文档惯例。
- 默认摘要 MUST **点名结构化属性里的关键值**（如 `InvalidUpdateError` 的未知 key）——用户不该为了知道「哪个 key 出错」而去找消息以外的渠道。

### 5.2 结构化属性（**属性名即冻结面**）

| 类 | 属性 | 类型 | 含义 |
|---|---|---|---|
| `InvalidUpdateError` | `invalid_keys` | `tuple[str, ...]` | 状态 schema 中**不存在**的 key 列表 |
| `GraphRecursionError` | `recursion_limit` | `int` | 递归上限 |
| `GraphRecursionError` | `current_step` | `int` | 已达步数 |
| `GraphInterrupt` | `payload` | 本 feature `Any`；结构约定：载荷带 `.value` 与 `.id`（C17） | 中断载荷**对象** |

**为什么 `payload` 保持对象形态**：将来载荷加字段**不必**改动异常的 API（只需加载荷类的字段）。
`payload` 的**具体类型**归 B2F1 —— 本 feature 收紧**注解**不构成契约破坏。

### 5.3 用法

```python
try:
    result = agent.invoke({"messages": [...]})
except FreegraphError as e:                     # 一次兜住全部内核错误
    if isinstance(e, InvalidUpdateError):
        print(e.invalid_keys)                   # 结构化取用，无须解析消息
    elif isinstance(e, GraphRecursionError):
        print(e.recursion_limit, e.current_step)
    elif isinstance(e, GraphInterrupt):
        print(e.payload.value, e.payload.id)     # 载荷对象带 .value / .id
```

---

## 6. 冻结面速查（改动即破坏契约）

| 类别 | 冻结项 |
|---|---|
| **符号名** | `StateDict` / `Command` / `StateSnapshot` / `RunConfig` / `FreegraphError` / `InvalidUpdateError` / `GraphRecursionError` / `GraphInterrupt`（恰好 8 个） |
| **字段名** | `Command`: `goto` / `update` / `resume`；`StateSnapshot`: 七字段；`RunConfig`: 四字段 |
| **字段类型** | 见第 2 / 3 / 4 节（逐个冻结） |
| **属性名** | `invalid_keys` / `recursion_limit` / `current_step` / `payload` |
| **常量值** | `Command.PARENT == "__parent__"` |
| **基类名** | `FreegraphError`（后续可**新增**子类，但基类名不得改） |
| **行为** | `Command()` 必抛 `FreegraphError`；`from_dict` 默认对未知键抛错；自动生成的摘要为**英文**且点名关键值 |
| **容器拷贝** | `StateSnapshot.metadata` 拷贝；`RunConfig.metadata` + `RunConfig.tags` 拷贝（均为**浅拷贝**） |

**不属于冻结面（可在后续 feature 无痛调整）**：`tasks` / `interrupts` / `payload` 的**元素类型**
（归 B2F1；细化时不改动字段注解本身）、额外的便利方法（如 `to_dict()`）。

> **字段的注解本身已冻结**：`RunConfig` 四字段与 `StateSnapshot` 七字段的注解（`Mapping[str, Any]` /
> `Sequence[str]` / `tuple[str, ...]` 等）自本 feature 起一并冻结 —— B4F1 / B8F3 只能**新增字段**、
> 不得改动已有字段的注解（依据：spec Assumptions「`RunConfig` 四个字段的具体注解」条）。
