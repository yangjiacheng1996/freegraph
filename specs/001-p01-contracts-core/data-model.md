# Phase 1 · 数据模型（data-model.md）

**Feature**: F1P1 · 契约层骨架（四个核心类型 + 异常体系）
**输入**: [spec.md](./spec.md) · [research.md](./research.md)
**Date**: 2026-11-05

> 本层**不含任何运行时行为**——无调度、无 channel、无状态读写。
> 下列「实体」全部是**类型定义**（值对象 / 记录），不是有生命周期的领域对象。
> 唯一带「状态迁移」的是 `Command`：它由「三个语义位全空（非法）」迁移到「至少一位有效」。

---

## 实体总览

```text
                    ┌──────────────────────────┐
                    │  StateDict (= dict[str, Any]) │  ← 别名，非新造类型
                    │  稀疏状态字典              │
                    └──────────────────────────┘
                             ▲          ▲
              values: StateDict        update: StateDict | None
                             │          │
                    ┌────────┴──────────┴────────┐        ┌──────────────────────┐
                    │     StateSnapshot            │◄───────┤       RunConfig      │
                    │  （某一时刻的定格，不可变）    │ config │  （单次运行的配置）    │
                    └──────────────────────────────┘        └──────────────────────┘
                                                                │ from_dict(裸 dict)
                                                                ▼
                                                          dict[str, Any]

                    ┌──────────────────────────┐
                    │         Command            │  goto: str | Sequence[str] | None
                    │  （节点返回的命令，不可变）   │  update: StateDict | None
                    │  PARENT = "__parent__"     │  resume: Any
                    └──────────────────────────┘
                             │ 构造期校验
                             ▼
                    ┌──────────────────────────┐
                    │      FreegraphError        │  ← 统一基类
                    │  ├ InvalidUpdateError      │     .invalid_keys
                    │  ├ GraphRecursionError     │     .recursion_limit / .current_step
                    │  └ GraphInterrupt          │     .payload
                    └──────────────────────────┘
```

---

## 实体 1 · 状态字典（`StateDict`）

| 项 | 内容 |
|---|---|
| **形态** | **类型别名**，非新造类型：`StateDict: TypeAlias = dict[str, Any]` |
| **语义** | 图状态的**稀疏**映射 —— 只含「当前有值」的 key |
| **与 `dict[str, Any]` 的关系** | **完全等价**（同一个类型，不是子类型）。`isinstance(x, StateDict)` 恒等于 `isinstance(x, dict)` |
| **必填 / 可选** | 不适用（映射类型本身无「字段」） |
| **校验规则** | 无。freegraph **不校验**键名是否在状态 schema 中——那是运行时的事（归 F5P1 / F4P1） |

**关键语义（C4 · 稀疏状态）**：空 channel 的 key **不得**出现在节点入参里。但「值为 `None` 的 key」**算**有值，必须出现。二者不可混淆。

**与用户 schema 的关系**：用户的状态 schema 由**用户自己**的 `TypedDict`（或 Pydantic）表达；freegraph **不要求**用户继承任何基类，也**不校验**节点注解与 schema 是否一致（鸭子类型）。用户想让编辑器补全具体字段，直接用自己的 `TypedDict` 标注节点签名即可。

> **来源**：spec FR-002 / FR-014；澄清第 2 条；宪法原则 II。

---

## 实体 2 · 命令原语（`Command`）

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `goto` | `str \| Sequence[str] \| None` | `None` | 跳转目标：单个节点名（字符串）或一组节点名（任意序列，元组/列表都收）。本 Phase 不导出 `Send`，故目标**只能是节点名** |
| `update` | `StateDict \| None` | `None` | 要写入图状态的部分更新 |
| `resume` | `Any \| None` | `None` | 恢复值（与 `interrupt` 配对使用；`interrupt` 实体属 F2P1） |

| 类属性 | 值 | 语义 |
|---|---|---|
| `PARENT` | `"__parent__"`（`ClassVar[Literal["__parent__"]]`） | 「跳向最近的父图」的哨兵值。**节点名 `__parent__` 视为保留名** |

**校验规则（构造期，fail fast）**

| 情形 | 结果 |
|---|---|
| `goto` / `update` / `resume` **三者全为 `None`** | **抛 `FreegraphError`** —— 非法输入，不静默退化成空操作 |
| 三者中至少一位**不是 `None`** | 合法。三者可**任意组合**（「跳转+写入」同填、「恢复+跳转」同填），各语义位互不排斥 |
| 某位**显式给了但内容为空**（`update={}` / `goto=()`） | 合法 —— 语义为「该位不产生动作」。**与「未提供」（`None`）严格区分** |
| `goto` 传字符串 | 是**单个目标**，不是「字符串的字符序列」—— 归一化检查须先判 `isinstance(x, str)` |

**状态迁移**

```text
                 ┌───────────────────────────┐
   Command(...)  │  三个语义位全为 None        │ ──构造──► 抛 FreegraphError
   （未校验）    │  （非法态，不存在）          │            （对象不返回给调用方）
                 └───────────────────────────┘

                 ┌───────────────────────────┐
                 │  至少一位语义位有效          │  ← 唯一合法态
                 │  （不可变，此后不再变化）     │
                 └───────────────────────────┘
```

**不变式**

- 浅不可变：对象本身不可改，但 `update` 装的是 `dict`、`goto` 装列表时**其内容仍可变**（与 `RunConfig.metadata` 同理）。已在 docstring 中写明。
- `goto` **不归一化**：传元组存元组、传列表存列表（保持与冻结注解逐字一致，见 D-06）。
- 无参构造 `Command()` **必然**抛 `FreegraphError`（三全空）。

> **来源**：spec FR-003；澄清第 1 条与第 2 轮第 1、2 题；research D-05 / D-06 / D-07。

---

## 实体 3 · 状态快照（`StateSnapshot`）

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `values` | `StateDict` | — | 该时刻的**完整**状态（稀疏映射） |
| `next` | `tuple[str, ...]` | — | 本步之后要执行的节点名。**空元组** = 无后续节点（运行已结束 / 等待外部输入） |
| `config` | `RunConfig` | — | 取回该快照所用的运行配置 |
| `metadata` | `Mapping[str, Any]` | — | 与该快照相关的附加信息（可为空映射） |
| `created_at` | `str` | — | 创建时刻，**UTC 的 ISO-8601 字符串**（例 `2026-11-05T10:20:30.123456+00:00`），**必填** |
| `tasks` | `tuple[Any, ...]` | — | 本步的任务列表（元素类型由 **F2P1** 细化） |
| `interrupts` | `tuple[Any, ...]` | — | 本步发生的中断（元素类型由 **F2P1** 细化） |

**校验规则**

- 七个字段**全部必填**（无缺省值）—— 快照是「某一时刻的完整定格」，不存在「字段缺失的快照」。
- `created_at` 格式 MUST 一律为 UTC ISO-8601 —— **各持久化后端不得各写各的**（否则时间线排序与对比出错）。
- 本 Phase **不提供**「生成快照」的功能（那是运行时的活）；只定义形状与格式。

**不变式**

- 不可变类（`frozen=True`）；`values` / `metadata` 装的是可变容器 ⇒ **浅不可变**。
- `values` 是**稀疏**的：空 channel 的 key 不出现。

> **来源**：spec FR-004；澄清第 4 题；research D-10。

---

## 实体 4 · 运行配置（`RunConfig`）

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `thread_id` | `str \| None` | `None` | **会话**标识（由 checkpointer 挂载时使用） |
| `context` | `Any` | `None` | **运行时上下文** —— 独立通道（C21），**不塞进 `configurable`** |
| `metadata` | `Mapping[str, Any]` | 空映射 | 附加信息，**不参与标识** |
| `tags` | `Sequence[str]` | 空序列 | 附加标签，**不参与标识** |

**校验规则**

- 四个字段**全部可选**，均有缺省值 ⇒ 构造无前置条件。
- **`from_dict` 默认严格**：裸 dict 中出现四字段之外的键 ⇒ 抛 `FreegraphError`（消息点名该键）。当场暴露 `threadId` 这类拼写错误，而不是静默吞掉（否则表现为「会话没记住」——极难查的 bug）。
- **`from_dict(..., ignore_unknown=True)`** 走宽松：忽略未知键。供运行入口将来容忍「HTTP 请求体整包透传」用（该运行时行为归 F7P3）。

**标识职责划分（立项书 §5.3.1 / C22）**

| 标识 | 由谁产生 | 用户能否指定 |
|---|---|---|
| `thread_id` = **会话**标识 | 用户经 `RunConfig` 传入 | ✅ 可以 |
| `run_id` = **单次运行**标识 | freegraph 在每次 `invoke` / `stream` 开始时生成 | ❌ **不可指定、不可覆盖**；且**不进** `RunConfig` 字段清单 |

**关系**

- `StateSnapshot.config` 的类型就是 `RunConfig`。
- `RunConfig` 是 `StateSnapshot` 的**组成部分**（组合，非继承）。
- **容器防御性拷贝**：两个类型在构造时都把 `metadata` / `tags` **拷贝**为自身持有的新容器，
  不与调用方传入的容器共用同一对象（否则调用方事后改原 dict 会静默改到已构造的「不可变记录」）。

> **来源**：spec FR-005 / FR-014；澄清第 3 条；立项书 §5.3.1；research D-04。

---

## 实体 5 · 异常体系

### 5.1 `FreegraphError`（基类）

| 项 | 内容 |
|---|---|
| **基类** | `Exception` |
| **职责** | 统一锚点。上层 `except FreegraphError` 即可兜住**全部**内核错误 |
| **自定义 `__init__`** | **无** —— 刻意不定义，让它只做「类型锚点 + 统一捕获点」 |
| **稳定性** | 基类名一旦冻结**不得再改**；后续版本可**新增**子类，但上层只捕获基类即可继续工作 |

### 5.2 三个子异常

| 类 | 触发场景 | 结构化属性（**属性名即冻结面**） | 属性类型 |
|---|---|---|---|
| `InvalidUpdateError` | 节点返回了状态 schema 中**不存在的 key** | `invalid_keys` | `tuple[str, ...]` |
| `GraphRecursionError` | 递归**超限** | `recursion_limit`（递归上限）<br>`current_step`（已达步数） | `int`<br>`int` |
| `GraphInterrupt` | 节点**主动中断** | `payload`（中断载荷**对象**） | 本 Phase `Any`；结构约定：载荷须带 `.value` 与 `.id`（C17） |

**构造签名**

```text
InvalidUpdateError(invalid_keys: Iterable[str], *, message: str | None = None)
GraphRecursionError(recursion_limit: int, current_step: int, *, message: str | None = None)
GraphInterrupt(payload: Any, *, message: str | None = None)
```

- 结构化属性作**位置参数**（主要信息，不该藏在 kwargs 里）；`message` 为**可选关键字**，缺省时由属性自动生成一句摘要消息。
- 错误消息**只是给人看的摘要** —— 上层 MUST NOT 需解析消息才能取到细节。

**不变式**

- 三者 MUST 全部派生自 `FreegraphError`，且 `FreegraphError` 派生自 `Exception`。
- 构造「三个语义位全缺省」的 `Command` 时抛出的错误同样 MUST 可被基类捕获（⇒ 该错误必须是 `FreegraphError` 或其子类）。

> **来源**：spec FR-006；澄清第 5 题与第 2 轮第 3 题；research D-08 / D-09。

---

## 实体间关系汇总

| 关系 | 类型 | 说明 |
|---|---|---|
| `StateSnapshot.values` → `StateDict` | 组合 | 快照持有稀疏状态字典 |
| `StateSnapshot.config` → `RunConfig` | 组合 | 快照持有产生它的运行配置 |
| `Command.update` → `StateDict` | 组合 | 命令携带的部分更新 |
| `RunConfig` ← `dict[str, Any]` | **工厂**（非继承） | `from_dict` 构造；**不**继承 dict，**不**是 dict 的子类型 |
| `StateDict` ≡ `dict[str, Any]` | **别名**（同一类型） | 不是继承关系 |
| `InvalidUpdateError` / `GraphRecursionError` / `GraphInterrupt` → `FreegraphError` → `Exception` | 继承 | 单一异常族 |

---

## 不变式清单（供 tasks 与实现逐条对照）

| # | 不变式 | 判定方式 |
|---|---|---|
| I-01 | `StateDict` 与 `dict[str, Any]` 完全等价（别名） | `typing.get_origin(StateDict) is dict` **且** `StateDict == dict[str, Any]`（**不得**用 `is` 判定 —— 实测 `dict[str, Any] is dict[str, Any]` 为 `False`；**不得**用 `isinstance(x, StateDict)` —— 参数化泛型不是合法的 `isinstance` 第二参数） |
| I-02 | `Command()`（三全空）必然抛 `FreegraphError` | 直接构造 + 断言异常类型 |
| I-03 | `Command` 三语义位可任意组合，互不排斥 | 逐一构造组合并断言成功 |
| I-04 | `Command.PARENT == "__parent__"` | 直接断言常量值 |
| I-05 | `Command` / `StateSnapshot` / `RunConfig` 构造后字段不可改 | 赋值 ⇒ 抛 `FrozenInstanceError` |
| I-06 | 三个记录类的字段注解可被 `typing.get_type_hints` 完整解析 | 全量解析无异常、无残留字符串注解 |
| I-07 | `StateSnapshot` 七字段齐全且全部必填 | 逐字段构造 + 缺字段构造失败 |
| I-08 | `created_at` 必填且为 UTC ISO-8601 字符串 | 构造缺省失败 + 格式正则断言 |
| I-09 | `RunConfig.from_dict` 默认对未知键抛 `FreegraphError` 并点名该键 | 传入 `{"threadId": "x"}` 断言异常与消息 |
| I-10 | `RunConfig.from_dict(..., ignore_unknown=True)` 忽略未知键 | 传入多余键断言成功且字段值为期望值 |
| I-11 | `RunConfig` 四字段均有缺省、可全空构造 | `RunConfig()` 成功 |
| I-12 | 三个子异常都派生自 `FreegraphError`，基类派生自 `Exception` | `issubclass` 断言 + `except` 基类捕获三例 |
| I-13 | 三个子异常的结构化属性可直接读取 | 构造后 `getattr` 断言 |
| I-14 | `Command` 的空语义位与未提供语义位**严格区分** | `update={}` 合法、`update=None` 单独存在时也合法、但三全空非法 |
| I-15 | 公开符号面恰为 8 个符号 | `__all__` 集合相等断言 |
| I-16 | 构造后本对象持有的 `metadata` / `tags` 容器与调用方传入的**不是同一个对象** | `cfg.metadata is not passed_dict` 断言 |
