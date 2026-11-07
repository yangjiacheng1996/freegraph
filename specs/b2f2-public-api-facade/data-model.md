# Data Model · B2F2 门面导出面的冻结规格

**feature**: `B2F2`（公开 API 门面 `freegraph/graph.py` + API 签名快照）
**规格来源**: [`spec.md`](./spec.md)（FR-001…FR-019 · SC-001…SC-018 · 12 条裁定 + 12 条澄清问答）
**决策来源**: [`research.md`](./research.md)（D-01…D-23）
**本文件性质**: `/speckit.plan` 的 **Phase 1 输出** —— 本 feature 的「数据」不是业务数据，
而是**对外形状本身**：7 个导出符号的**签名 / 字段 / 行为边界**与**快照文本的格式**。
**规范性来源优先级**：**spec 的 FR / SC 正文** > 本文件 > `research.md`；
冲突时以 spec 为准并**回头修正**本文件。

---

## 1. 通用规则

### 1.1 门面模块的规则（`src/freegraph/graph.py`）

> **层归属 = 跨层单元（层 =「—」，2026-11-07 发起者裁定）**：门面的导出面横跨 **L1–L3**，
> 故它是 **ARCH-1 的唯一例外**（可 import L1–L3，仍**不得** import L4 / L5）——
> 例外条款见立项书 §5.1 的 ARCH-1 条目与 §5.2 的 B2F2 行。

| # | 规则 | 判据（门禁 G14 / G15） |
|---|---|---|
| R-1 | 门面模块**零实现体**：`class` / `def` / `async def` 语句数 **== 0** | AST 扫描，报行号 |
| R-2 | 门面只允许：`import` 语句、**常量赋值**（`START` / `END`）、`__all__` 赋值、文档字符串 | AST 白名单 |
| R-3 | 门面**不得**使用 `from __future__ import annotations`（该 future import 会留下名为 `annotations` 的**公开绑定**，破坏 R-6） | R-6 的公开名判据 |
| R-4 | 门面**不得**定义（`def` / `class`）任何公开名——**导入绑定不受此限**（门面**必须** import 那 7 个导出符号），但**不得**以「下划线开头」为由藏入新的公开能力；一切公开名 MUST 受 R-6 的**集合相等**约束 | G15 |
| R-5 | 门面的 `__all__` **恰为** 7 个名字，**集合相等** | G15 |
| R-6 | 门面模块内**所有不以下划线开头的名字**恰为这 7 个（`dir()` 口径） | G15 |
| R-7 | 门面**零**环境变量读取、**零**出站 / 文件 I/O、**零** `langchain*` / `langgraph*` / `langsmith` import（**第三方档**；**内部档**只禁 **L4 / L5**（与 FR-014 ④ 同口径）—— `freegraph.contracts` 的 import **合法**；**L2 / L3 合法**，因门面是 **ARCH-1 的唯一例外** · 裁定 9） | G17（**两档**） |
| R-8 | 门面**不得**横向依赖 L4（持久化）/ L5（可观测） | G18 |

### 1.2 快照的记录规则（**ID 索引**）

> **规范性来源 = [`contracts/snapshot-format.md`](./contracts/snapshot-format.md)**（格式契约）。
> 本节**只列 ID 索引**，便于 spec / plan / tasks / 门禁交叉引用；**规则正文一律不在此复写**
> （避免同一套规则两处抄写导致漂移 —— E1）。

| ID | 规则摘要 | 权威位置 |
|---|---|---|
| R-9 | 记录：导出符号名 + 类别 + 完整调用签名（参数名 / 缺省值 / `*` 关键字-only 标记 / 参数注解 / 返回注解）；常量含**字面值**；类含其**公开方法**与**公开属性 / property** | `snapshot-format.md` §1 |
| R-10 | 「公开」= 名字不以下划线开头 **∪** `__init__`；其余 dunder **不记** | `snapshot-format.md` §1 |
| R-11 | 「公开属性」= 名字不以下划线开头；dataclass 字段 / `property` / `ClassVar` 均算（**取数规则见 D-21-1…D-21-4**） | `snapshot-format.md` §1 · §1.1 |
| R-12 | **参数顺序是冻结面的一部分**（逐字保留，不排序）；类内成员按名排序 | `snapshot-format.md` §1 · §3（T-5 / T-6） |
| R-13 | 顶层条目按名排序；编码 UTF-8 / 换行 LF / 末行带换行 | `snapshot-format.md` §3（T-1…T-4） |
| R-14 | 快照**不得**含：内存地址 / `id()` / 哈希序 / 时间戳 / 绝对路径 / Python 版本号 | `snapshot-format.md` §5 |
| R-15 | 同一份代码**两次生成 MUST 逐字节相同** | `snapshot-format.md` §4 |
| R-16 | 快照由**代码生成**（纯函数）；入库文件 = `contracts/public-api-snapshot.txt`；期望的导出面清单来自**手写**的 `contracts/facade-api.md` §0（判定**非循环**） | `snapshot-format.md` §4 · `facade-api.md` §0 |
| N-1…N-6 | 注解规范化的 6 条（去引号 / 去限定前缀 / `Optional[X]`→`X \| None` / `NoneType`→`None` / 空白归一 / 缺省 `-> None`） | `snapshot-format.md` §2 |

### 1.3 注解规范化规则（D-04 · 逐字冻结）

| # | 规则 | 示例 |
|---|---|---|
| N-1 | 去掉字符串注解的**外层引号** | `'RunConfig'` → `RunConfig` |
| N-2 | 去掉 `typing.` / `collections.abc.` **限定前缀** | `typing.Any` → `Any`；`collections.abc.Sequence[str]` → `Sequence[str]` |
| N-3 | `Optional[X]` → `X \| None`；`Union[X, Y]` → `X \| Y`（**保持原成员顺序**） | `Optional[str]` → `str \| None` |
| N-4 | `NoneType` → `None` | `type(None)` → `None` |
| N-5 | 参数注解与缺省值两侧空白归一为单空格；缺省值用 `repr` 形态 | `ignore_unknown=False` |
| N-6 | 返回注解写成 `-> <注解>`；无返回注解记 `-> None` | — |

> **⚠️ 与 research D-04 的关系（2026-11-07 分析轮澄清）**：research D-04 列的 6 条里，
> ⑤「参数顺序逐字保留」与 ⑥「类内成员按名排序」**不是注解规范化规则** —— 它们属
> **文本层规则** `snapshot-format.md` §3 的 **T-6 / T-5**。
> **「注解规范化 6 条（N-1…N-6）」这一标签只指本表的 N-1…N-6**（`tasks.md` T019 只实现本表这 6 条）。
>
> **跨版本稳定性**：N-2 / N-3 吸收了 `typing` 渲染在 Python 小版本间的主要差异源；
> 快照文本**不依赖**具体 Python 版本（SC-006 的「两次生成逐字节相同」在**同一环境**判定，
> 跨版本由「CI 最低档 3.11 + 上述规范化」共同保证）。

---

## 2. 七个导出符号的冻结规格

> **类别**：`class` = 类 · `function` = 函数 · `constant` = 常量。
> **归属**：该符号的**行为**由哪个 feature 交付。
> **转出**：该符号**原样**来自契约层（`freegraph.contracts`），门面不复制、不子类化。

### 2.1 `StateGraph`（class · 门面自有 · 行为归 B6F1 / B7F2）

| 项 | 内容 |
|---|---|
| 定义位置 | `src/freegraph/_stategraph.py`（**不在**门面文件内 · 裁定 3） |
| 构造签名 | `__init__(self, schema: Any) -> None` —— **恰一个必填位置参数**，参数名 `schema`（裁定 4） |
| 公开属性 | **无**（`schema` 私有存放 · D-11）⇒ M0 快照无 `[attribute]` 条目 |
| 公开方法 | `add_node` / `add_edge` / `add_conditional_edges` / `compile`（签名见下） |
| 构造期行为 | **成功构造、不抛异常**；**零**校验、**零**副作用（不读环境变量、不 I/O） |
| 多传一个位置参数 | **失败**（`TypeError`） |
| 未接线行为 | 四个方法**均**抛 `NotImplementedError`（FR-009 · D-15） |

**四个方法的冻结签名**：

| 方法 | 签名 | 形态要点 |
|---|---|---|
| `add_node` | `(self, name: str, fn: NodeFunc, *, alias: str \| None = None) -> Self` | 位置参数 `(str, Callable)`（宪法 III 第 3 项）；`alias` **keyword-only**（C25 · B8F3）；`fn` 用契约层已有的 `NodeFunc` 协议 |
| `add_edge` | `(self, src: str \| list[str], dst: str) -> Self` | 返回注解 `Self`（链式语义 · 宪法 III 第 4 项） |
| `add_conditional_edges` | `(self, src: str, path_fn: Callable[..., str \| list[str]], path_map: list[str] \| dict[str, str]) -> Self` | `path_map` **同时支持 list 与 dict**（宪法 III 第 5 项）；**无缺省值**；路由契约 C7 归 B8F1 |
| `compile` | `(self, *, checkpointer: Checkpointer \| None = None, store: Store \| None = None) -> CompiledGraph` | **无参可调用** + 两个 **keyword-only** 可选关键字（裁定 6） |

> `Self` = `typing.Self`（**3.11+** ⇒ 合规 typing 构件上限 G9）；上游同形
> （`langgraph/graph/state.py:667` / `:928` / `:982`）。
> `NodeFunc` / `Checkpointer` / `Store` / `CompiledGraph` 均取自**契约层既有协议**
> （B2F1 冻结）——本 feature **不新增**任何类型，也**不导出**它们。

### 2.2 `START` / `END`（constant · 门面自有）

| 符号 | 值 | 类型 | 契约 |
|---|---|---|---|
| `START` | `'__start__'` | `str` | C9 |
| `END` | `'__end__'` | `str` | C9 |

- **定义位置**：门面模块内（常量赋值是 R-2 允许的唯一「非 import」语句）；
- **不得**是枚举成员或自定义对象（FR-003）；
- **不得**在 `freegraph.contracts` 中重复定义（避免两处取值漂移）。

### 2.3 `Command`（class · **契约层转出**）

| 项 | 内容 |
|---|---|
| 定义位置 | `freegraph.contracts.types`（B1F1 冻结）——门面**原样转出** |
| 同一性 | `freegraph.graph.Command is freegraph.contracts.Command` ⇒ **True**（FR-004 · SC-003） |
| 字段 | `goto: str \| Sequence[str] \| None = None` / `update: StateDict \| None = None` / `resume: Any \| None = None` |
| 类属性 | `PARENT: ClassVar[Literal["__parent__"]] = "__parent__"` |
| 方法 | `__init__(self, goto=None, update=None, resume=None) -> None`（契约层是 `kw_only=True` ⇒ 快照里呈 `*` 标记） |
| 构造期行为 | 三语义位全空即抛 `FreegraphError`（**既有**行为，本 feature 不改） |
| 运行时语义 | 归 **B9F1** |

> **快照里为什么含它**：门面是用户唯一入口 ⇒ 用户经门面用到的调用面都应被冻结
> （D-06）。`Command` 的**字段语义权威**仍是 B2F1 的 `contracts/public-api.md`，
> 快照只是**机器镜像**（分工见 D-06 表）。

### 2.4 `RunConfig`（class · **契约层转出**）

| 项 | 内容 |
|---|---|
| 定义位置 | `freegraph.contracts.types`（B1F1 冻结）——门面**原样转出** |
| 同一性 | `freegraph.graph.RunConfig is freegraph.contracts.RunConfig` ⇒ **True** |
| 字段 | `thread_id: str \| None = None` / `context: Any = None` / `metadata: Mapping[str, Any] = {}` / `tags: Sequence[str] = ()` |
| 方法 | `__init__(...)` / `from_dict(cls, d: Mapping[str, Any], *, ignore_unknown: bool = False) -> RunConfig`（classmethod） |
| 构造期行为 | 四字段全可选；`metadata` / `tags` 浅拷贝（**既有**行为） |
| 标识约定 | `thread_id` = **会话标识**（在运行配置内）；**`run_id` NOT in** 字段清单（C22 · D11）——本 feature **不增删字段** |

### 2.5 `Send`（class · 门面自有 · 行为归 B11F1）

| 项 | 内容 |
|---|---|
| 定义位置 | `src/freegraph/_primitives.py` |
| 形状 | `@dataclass(frozen=True, slots=True)`，字段 `node: str` / `arg: Any` |
| 参数形态 | **位置或关键字皆可**（**不用** `kw_only=True` · D-13）⇒ `Send("w", {...})` 与 `Send(node="w", arg={...})` 均合法 |
| 不可变性 | **不可变记录**（改属性抛 `FrozenInstanceError` · Q7） |
| 哈希 | **不可哈希**（显式 `__hash__ = None`；与 `Node` / `Edge` / `Graph` / `Span` 同构） |
| 与上游的差异 | 上游 `Send` **可变** ⇒ 差异入兼容矩阵（D-17） |
| 运行时语义 | 动态 fan-out 归 **B11F1** |

> **为何不用 `kw_only=True`**：契约层的五个数据类一律 `kw_only=True`，
> 但 `harness/demo/graph_core.py` 与上游都用**位置参数** `Send("worker", {"n": 1})`
> ⇒ `kw_only=True` 会直接 `TypeError`。这是本 feature 中**唯一**与契约层 dataclass 惯例
> 不同处，**显式登记**在此与快照中。

### 2.6 `interrupt`（function · 门面自有 · 行为归 B10F1）

| 项 | 内容 |
|---|---|
| 定义位置 | `src/freegraph/_primitives.py`（模块级函数） |
| 签名 | `interrupt(value: Any) -> Any` —— **位置或关键字皆可**（上游 `langgraph/types.py:851` 同形） |
| 当前行为 | **无条件抛 `NotImplementedError`**（消息点名 B10F1 · D-15）⇒ 零副作用 |
| 返回值语义 | 运行期返回**恢复值**（`Any`）；恢复闭环归 **B10F1** |

---

## 3. 快照文本格式（契约 · `contracts/snapshot-format.md` 同步）

### 3.1 语法

```
<kind> <name><payload>
```

- 顶级条目（导出面成员）**无缩进**；类内条目**缩进 2 空格**；
- `kind ∈ {constant, function, class, method, attribute}`；
- 顶级条目与类内条目**均按名字排序**（R-12 / R-13）；
- `class` 条目只给类名，其成员以下一级缩进列出。

### 3.2 示例（本 feature 落地后的快照**形态示意**）

> **注意**：这是**形态示意**，不是入库快照的逐字内容——入库文件由实现阶段的
> `pytest --update-api-snapshot` 生成并**经人工 review diff 后提交**（FR-011 ①）。
> 示例中 `[attribute]` 的**缺省值**与**只读 / 可写**标注遵循
> `contracts/snapshot-format.md` §1.1 的 **D-21-1…D-21-4**（dataclass 属性的取数规则）。

```
# freegraph 公开 API 快照 —— 门面 `freegraph.graph`
# 本文件由 `pytest tests/facade/test_api_snapshot.py --update-api-snapshot` 生成，请勿手工编辑。
# 格式契约：specs/b2f2-public-api-facade/contracts/snapshot-format.md
# 导出面清单（哪些符号算公开）的权威是 contracts/facade-api.md §0；本文件只记录签名。
#
[constant] END = '__end__'
[constant] START = '__start__'
[class] Command
    [attribute] PARENT: ClassVar[Literal['__parent__']] = '__parent__' (readonly)
    [attribute] goto: str | Sequence[str] | None = None (readonly)
    [attribute] resume: Any | None = None (readonly)
    [attribute] update: StateDict | None = None (readonly)
    [method] __init__(self, *, goto: str | Sequence[str] | None = None, update: StateDict | None = None, resume: Any | None = None) -> None
[class] RunConfig
    [attribute] context: Any = None (readonly)
    [attribute] metadata: Mapping[str, Any] = {} (readonly)
    [attribute] tags: Sequence[str] = () (readonly)
    [attribute] thread_id: str | None = None (readonly)
    [method] __init__(self, *, thread_id: str | None = None, context: Any = None, metadata: Mapping[str, Any] = {}, tags: Sequence[str] = ()) -> None
    [method] from_dict(cls, d: Mapping[str, Any], *, ignore_unknown: bool = False) -> RunConfig
[class] Send
    [attribute] arg: Any = <required> (readonly)
    [attribute] node: str = <required> (readonly)
    [method] __init__(self, node: str, arg: Any) -> None
[class] StateGraph
    [method] __init__(self, schema: Any) -> None
    [method] add_conditional_edges(self, src: str, path_fn: Callable[..., str | list[str]], path_map: list[str] | dict[str, str]) -> Self
    [method] add_edge(self, src: str | list[str], dst: str) -> Self
    [method] add_node(self, name: str, fn: NodeFunc, *, alias: str | None = None) -> Self
    [method] compile(self, *, checkpointer: Checkpointer | None = None, store: Store | None = None) -> CompiledGraph
[function] interrupt(value: Any) -> Any
```

### 3.3 缺省值的表示

| 形态 | 记法 |
|---|---|
| 字符串缺省 | `= '__end__'`（`repr` 形态） |
| `None` 缺省 | `= None` |
| 空容器缺省 | `= {}` / `= ()`（**`repr` 形态**，不是空文本） |
| **无缺省**（必填） | `= <required>`（占位符，**逐字固定**） |

> `<required>` 是本 feature 新引入的**占位记法**：必填参数在快照里必须与「有缺省值」可区分
> （否则 `Send(node, arg)` 与 `Send(node=None, arg=None)` 的快照会长得一样）。

### 3.4 快照的**非目标**

- **不记录**函数体 / 实现细节 / 内部实现模块路径；
- **不记录** dunder（语言协议）；
- **不记录**门面**未导出**的内部模块（如 `_stategraph`）——它们不是 API 面。

---

## 4. 未接线语义表（FR-009 · D-15）

| 调用 | 抛出的异常 | 消息形态 | 行为归属 |
|---|---|---|---|
| `StateGraph.add_node(...)` | `NotImplementedError` | `add_node 尚未接线（由 B6F1 交付）` | **B6F1** |
| `StateGraph.add_edge(...)` | `NotImplementedError` | `add_edge 尚未接线（由 B6F1 交付）` | **B6F1** |
| `StateGraph.add_conditional_edges(...)` | `NotImplementedError` | `add_conditional_edges 尚未接线（由 B6F1 交付）` | **B6F1** |
| `StateGraph.compile(...)` | `NotImplementedError` | `compile 尚未接线（由 B7F2 交付）` | **B7F2** |
| `interrupt(...)` | `NotImplementedError` | `interrupt 尚未接线（由 B10F1 交付）` | **B10F1** |

**统一约束**：

- 异常类型 **MUST** 是内置 `NotImplementedError`（Q2）——**不新增**任何公开错误类型；
- 消息 **MUST** 点明「尚未接线」+ **归属 feature**；
- **MUST NOT** 抛 `NameError` / `AttributeError` 之类的意外异常；
- **MUST NOT** 静默成功（返回 `None` 或空对象）——静默成功会让用户的图「看起来建好了」
  却永不执行，比报错更坏；
- 门禁 G14–G20 **不**判异常消息，但 `test_facade.py` **MUST** 断言消息形态（正则）。

---

## 5. 校验规则（构造期 vs 运行期）

| 规则 | 落点 | 说明 |
|---|---|---|
| **零**构造期值校验 | `StateGraph(schema)` | `schema` **不校验**类型 / 非空 / 唯一——契约层的数据类也一律「零值校验」（生产者负责） |
| **零**构造期副作用 | `StateGraph(schema)` | 不读环境变量、不 I/O、不起线程 |
| `Send` **零**构造期校验 | `Send(node, arg)` | `node` 是否为合法节点名、是否可达，归 **B6F1 / B11F1** 的运行期 |
| `Command` 的**既有**校验**不动** | `Command(...)` | 三语义位全空即抛 `FreegraphError`（B1F1 冻结，本 feature 不改） |
| `RunConfig.from_dict` 的**既有**校验**不动** | `RunConfig.from_dict(...)` | 未知键默认抛 `FreegraphError`（B1F1 冻结，本 feature 不改） |

> **口径**：本 feature **只新增**「未接线」这一种失败模式（§4），
> **不新增**任何新的校验规则 ⇒ 契约层既有的两条构造期校验（B1F1）保持原样。

---

## 6. 状态与生命周期

| 实体 | 生命周期 | 状态转换 |
|---|---|---|
| `StateGraph` 实例 | 由 `StateGraph(schema)` 创建 | **无状态机**——构造后即「未接线」终态；四个方法在任何状态下都抛 `NotImplementedError`（无「已接线」状态，因为 B6F1 之前无实现） |
| `Send` 实例 | 由 `Send(node, arg)` 创建 | **不可变值对象**——创建后无任何状态变化 |
| `interrupt(...)` 调用 | 每次调用即抛 | 无状态（运行期语义归 B10F1） |
| `Command` / `RunConfig` 实例 | 契约层既有语义 | **不变**（B1F1 冻结） |

> **无「部分接线」状态**：M0 阶段门面**要么**整体未接线、**要么**（B6F1 之后）整体接线；
> 允许「`add_node` 能用、`compile` 不能用」的半接线状态会产生难以诊断的行为 ⇒ 明确禁止。
> 该约束由 §4 的统一异常表 + `test_facade.py` 的逐方法断言共同保证。
