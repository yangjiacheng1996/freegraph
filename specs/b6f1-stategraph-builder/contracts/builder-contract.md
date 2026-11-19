<!-- authority: yes -->

# 构建器契约（StateGraph Builder Contract）—— B6F1 的唯一权威

**Feature**: `B6F1` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**上游版本**: `langgraph` **1.2.11**（核实于 2026-11-15）
**宿主**: `src/freegraph/_stategraph.py`（L3 图定义层）

> 本文件是「构建器长什么样、怎么用、给 B7F2 / B8F1 / B8F3 交什么」的唯一权威。
> **spec 讲「要什么」**，本文件讲「是什么」；两者冲突时以 spec 为准并回修本文件。
> 本契约的公开签名部分 **MUST NOT** 改动 B2F2 已冻结的签名快照；新增的内部类型全部私有。

---

## 1. 公开 API（签名逐字冻结 · B2F2 快照）

| 项 | 契约 |
|---|---|
| 构造 | `StateGraph(state_schema: Any, context_schema: Any = None, *, input_schema: Any = None, output_schema: Any = None) -> None` |
| 节点 | `add_node(node: str \| Callable[..., Any], action: Callable[..., Any] \| None = None, *, alias: str \| None = None, defer: bool = False, metadata: Mapping[str, Any] \| None = None, destinations: dict[str, str] \| tuple[str, ...] \| None = None) -> Self` |
| 静态边 | `add_edge(start_key: str \| list[str], end_key: str) -> Self`（运行时也接受 `tuple[str, ...]` 源） |
| 条件边 | `add_conditional_edges(source: str, path: Callable[..., str \| list[str]], path_map: list[str] \| dict[str, str] \| None = None) -> Self` |
| 校验 | `validate(interrupt: Sequence[str] \| None = None) -> Self` |
| 编译 | `compile(...) -> CompiledGraph` —— **仍为桩**，归 B7F2 |

> **`path_map` 注解口径**：公开签名保持 `list[str] | dict[str, str] | None`（B2F2 快照）；
> 运行时 dict key 可为任意 `Hashable`（与 spec FR-004 ④ 一致），MUST NOT 因此改写公开注解。

公开属性：**无**。所有构建状态以下划线开头的私有属性保存。

### 1.1 构造语义

- 恰一个必填位置参数 `state_schema`；第二个位置参数 `context_schema` 可选；第三个位置参数
  ⇒ `TypeError`。
- 构造期只保存 `_schema` 并初始化空容器；**不解析 schema、不校验、无 I/O、无环境变量**。
- 构造期 MUST NOT 因 schema 内容抛异常。

### 1.2 `add_node` 语义

- `node` 为 `str`：`action` MUST 可调用且不是 `None`；否则 `TypeError`。
- `node` 为 callable：`action` MUST 为 `None`；节点名取 `node.__name__`，无 `__name__` 时取
  类型名（普通 callable 的 `.name` **不参与**）；均取不到 ⇒ `ValueError`。非 callable
  `Runnable` / Runnable-like 对象不承载（X-6）。
- 重复节点名、`START` / `END` 作节点名、节点名含 `\|` / `:` ⇒ 立即 `ValueError`。
- 节点名 `__parent__` 在本层**不拒绝**（上游 `add_node` 同款接受）；由 B7F2 的
  `GraphSpec` 构造期 **B9F1 FR-005 `__parent__` 保留名检查**最终失败（与 V-1 / V-2 / V-3 同族）。
- `alias` / `defer` / `metadata` 原样记录；`metadata` 浅拷贝。本 feature **不校验**其运行时类型。
- **B22F1 追加**：`destinations` 仅用于图渲染（`get_graph`），不影响执行；`None` = 使用返回注解推断，显式序列 / dict = 覆盖推断（含空）。形态非法 ⇒ `TypeError`；目标存在性由编译期校验（`ValueError`）。
- MUST NOT 调用 `action`、MUST NOT 检查其返回注解（`destinations=None` 时仅做 `get_type_hints` 只读推断）。

### 1.3 `add_edge` 语义

- `start_key` 为 `str`：`END` 作源 ⇒ 立即 `ValueError`；`START` 作目标 ⇒ 立即 `ValueError`；
  `end_key` 非 `str` ⇒ 立即 `TypeError`；不检查端点是否存在（允许先边后节点）。
- `start_key` 既非 `str` 也非 `list` / `tuple` ⇒ 立即 `TypeError`。
- `start_key` 为 `list` / `tuple`：空 ⇒ 立即 `ValueError`；每个源 MUST 已登记且不是 `END`；
  目标 MUST 已登记或为 `END`；否则立即 `ValueError`。
- **公开签名注解**保持 `start_key: str | list[str]`（B2F2 快照）；`tuple[str, ...]`
  是运行时接受形态，MUST NOT 因此改写注解。
- 单源键保持 `str`；多源键为保序去重的 `tuple[str, ...]`。
- 目标按首次出现顺序累积；完全相同的 `(source, target)` 幂等。多源键的目标 MAY 累积
  多个（上游同款）；目标数 ≠ 1 不在本层拒绝，由 B7F2 的 `GraphSpec` **V-16** 最终失败。
- 返回 `Self`。

### 1.4 `add_conditional_edges` 语义

- `source` MUST 为 `str`；`path` MUST 可调用；否则 `TypeError`。
- `path_map` 支持：
  - `list[str]` ⇒ `{name: name}`（保序）；
  - `dict[Hashable, str]` ⇒ 浅拷贝（**运行时接受面**；公开注解仍见 §1 表注）；
  - `None` ⇒ 尝试从 `path` 的 `Literal[...]` 返回注解推断；推断不到保持 `None`，
    此时 `targets=()` / `route_channels=()`；
  - 其它类型 ⇒ 立即 `TypeError`。
- 同一 `source` 上同名分支 ⇒ 立即 `ValueError`。分支名 = `path.__name__`（普通 callable
  的 `.name` **不参与**）；无 `__name__` 或为 `<lambda>` 时取 `"condition"`
  （上游 `_runnable.py:313-319` 同款）。
- MUST NOT 调用 `path`。
- 返回 `Self`。

### 1.5 `validate` 语义

- 调用 `_build_spec()`，执行全部构建期末校验；成功返回 `self`。
- `interrupt` 参数被接受，并 MUST 按上游（`state.py:1168-1174`）校验：每个名字 MUST
  是已登记节点，否则 `ValueError`（消息含该名字）；缺省 / `None` ⇒ 不校验。
  静态断点的**编译期可达性**仍归 B7F2 的 compile 入口层。
- MUST NOT 执行节点。
- 失败后构建器登记状态不变；可重复调用。

---

## 2. 内部快照接口（B6F1 → B7F2 / B8F1 / B8F3）

> **私有**：以下名字全部以下划线开头，MUST NOT 进门面导出面、MUST NOT 进 API 快照。
> **B7F2 / B8F3 在 L3**，可直接 import `freegraph._stategraph`；**B8F1 在 L2**，
> **MUST NOT** import `freegraph._stategraph` 或 `_ConditionalEdgeSpec`，只消费 L2 侧结构。

### 2.1 `StateGraph._build_spec() -> _BuilderSpec`

> 字段列表以 `spec.md` **FR-007** 为唯一权威；本节只描述形状与消费者。

```python
@dataclass(frozen=True)
class _BuilderSpec:
    channels: dict[str, Channel]
    nodes: dict[str, NodeSpec]
    node_records: dict[str, _NodeRecord]
    edges: dict[str | tuple[str, ...], tuple[str, ...]]
    conditional_edges: tuple[_ConditionalEdgeSpec, ...]
```

| 字段 | 语义 | 消费者 |
|---|---|---|
| `channels` | 状态通道（schema 顺序）+ 路由通道（目标首次出现顺序） | B7F2 → `GraphSpec.channels` |
| `nodes` | 节点名 → `NodeSpec(subscribes=全部状态通道, run=action)`；保序 | B7F2 → `GraphSpec.nodes` |
| `node_records` | 节点名 → `_NodeRecord`（含 alias / defer / metadata） | B7F2 按 D-1 在 `CompiledGraph` 私有字段保留；B8F3 读取 alias |
| `edges` | 静态边；单源 `str` / 多源 `tuple`；值 MAY 含 `END` | B7F2（仅过滤**单源** `END` 后 → `GraphSpec.edges`；多源 **V-16 形态**（`END` / 目标数 ≠ 1）原样保留给 V-16） |
| `conditional_edges` | 条件边规格；登记顺序 | B7F2 机械翻译为纯内建类型 `dict[str, tuple[dict[str, Any], ...]]`（内层 `{"branch": str, "path": Callable, "path_map": dict[Hashable, str] \| None, "targets": tuple[str, ...], "route_channels": tuple[str, ...]}`，`branch` 取自 `_ConditionalEdgeSpec.branch`，形状以 spec D-2 为准）并存放于 `CompiledGraph` 私有字段；B8F1 经 L2 `GraphSpec.conditional_edges` 消费 |

### 2.2 `_NodeRecord`

```python
@dataclass(frozen=True)
class _NodeRecord:
    name: str
    action: Callable[..., Any]
    alias: str | None = None
    defer: bool = False
    metadata: Mapping[str, Any] | None = None
```

### 2.3 `_ConditionalEdgeSpec`

```python
@dataclass(frozen=True)
class _ConditionalEdgeSpec:
    source: str
    branch: str
    path: Callable[..., Any]
    path_map: dict[Hashable, str] | None
    targets: tuple[str, ...]
    route_channels: tuple[str, ...]
```

| 字段 | 语义 |
|---|---|
| `source` | 条件边源节点（可为 `START`） |
| `branch` | 同一源上的分支名；`_branch_name(path)` 的登记结果，同一 `source` 上唯一 |
| `path` | 路由函数原对象（不调用） |
| `path_map` | 归一化映射；与用户原对象解耦；`None` 且推断不到时保持 `None` |
| `targets` | 归一化 values 的唯一目标，**含 `END`**，首次出现顺序；`None` 推断不到 ⇒ `()` |
| `route_channels` | 非 `END` 目标的 `branch:to:<target>`，同序、去重；`None` 推断不到 ⇒ `()` |

### 2.4 快照不变量

1. 每次 `_build_spec()` 返回**新副本**（新通道实例、新 `NodeSpec`、新映射 / 元组）；
2. 两次快照**结构等价**（通道按类型 / 归约器 / key；节点、边、分支字段逐字相等）；
3. 调用方 MUST NOT 修改快照（约定只读）；
4. 构建期 MUST NOT 调用节点函数 / 路由函数 / 归约器；
5. 失败后构建器状态不变。

---

## 3. 路由通道

| 项 | 契约 |
|---|---|
| 键名 | `branch:to:<target>`（与上游 `state.py:98` 同款） |
| 类型 | `EphemeralValue(key, value_type=Any, guard=False)` |
| 创建时机 | `_build_spec()` 内，所有校验通过之后 |
| 创建范围 | 归一化 `path_map` 的非 `END` 唯一目标；同一目标只建一次 |
| `path_map=None` | 推断不到目标 ⇒ `targets=()` / `route_channels=()`、不建；推断出目标 ⇒ 照常建；B7F2 原样保留 `None` 供 B8F1 动态求值 |
| `END` | 不建路由通道（但保留在 `_ConditionalEdgeSpec.targets`） |
| `defer=True` 目标 | B6F1 仍建 `EphemeralValue`；上游用 `LastValueAfterFinish`，该差异登记为 **X-7**（已知不支持），由 B7F4 X-03 在 defer 落地时一并处理 |
| 位置 | 直接放入 `_BuilderSpec.channels`（spec Q11 选项 A） |
| 同名 key 冲突 | 复制上游覆盖行为（`state.py:1525-1530`）；登记为已知边界 |

---

## 4. 校验矩阵（BV-1…BV-13）

| # | 规则 | 时机 | 失败信号 |
|---|---|---|---|
| BV-1 | 节点参数形态非法 | `add_node` | `TypeError` |
| BV-2 | 节点保留名 / 保留字符 / 重复 | `add_node` | `ValueError` |
| BV-3 | 单 callable 取不到名字 | `add_node` | `ValueError` |
| BV-4 | 边参数类型非法 | `add_edge` | `TypeError` |
| BV-5 | `END` 作源 / `START` 作目标 | `add_edge` | `ValueError` |
| BV-6 | 多源边空源 / 源不存在 / 目标不存在 | `add_edge` | `ValueError` |
| BV-7 | 条件边 source / path 形态非法 | `add_conditional_edges` | `TypeError` |
| BV-8 | `path_map` 类型 / 元素类型非法 | `add_conditional_edges` | `TypeError` |
| BV-9 | 同源分支名重复 | `add_conditional_edges` | `ValueError` |
| BV-14 | `destinations` 形态非法（非 `Sequence[str]` / 非 `dict[str, str]`） | `add_node` | `TypeError` |
| BV-15 | `destinations` 目标不存在（非 `END`） | `validate` / `compile` | `ValueError`（点名目标） |
| BV-10 | schema 非法 | `validate` / `_build_spec` | B4F1 `InvalidSchemaError` |
| BV-11 | 节点表为空（源 / 入口 / 目标校验通过后，如 `START -> END`；在 BV-12c 之后执行 · X-5） | `validate` / `_build_spec` | `ValueError` |
| BV-12a | 源存在性：静态边源 / 条件边源（`START` 除外）不存在 | `validate` / `_build_spec` | `ValueError` |
| BV-12b | 缺少 `START` 入口（静态边或条件边 source == `START`） | `validate` / `_build_spec` | `ValueError` |
| BV-12c | 目标存在性：静态边目标 / 条件边目标不存在且非 `END` | `validate` / `_build_spec` | `ValueError` |
| BV-13 | `validate(interrupt=...)` 含未知节点 | `validate` | `ValueError` |

> 构建期末顺序：schema → **BV-12a 源** → **BV-12b 入口** → **BV-12c 目标** → **BV-11 空节点表**（X-5）。
> ⚠️ **校验范围**：B6F1 与 L2 `GraphSpec` 构造语义一致的部分**仅限 V-1 / V-2 / V-3**；
> B9F1 FR-005 的 **`__parent__` 保留名检查**（与 V-1 / V-2 / V-3 同族）与
> **V-16**（多源目标为 `END` / 目标数 ≠ 1）**不在本层校验**，由 **B7F2** 构造
> `GraphSpec` 时最终失败。
> 图结构错误只用内置 `ValueError` / `TypeError`；MUST NOT 新增异常类型。
> schema 非法沿用 B4F1 `InvalidSchemaError`。

---

## 5. 错误消息要求

消息 MUST 含可定位信息：

- 重复节点：节点名；
- 保留名 / 保留字符：该名字与字符；
- 边端点：源 / 目标节点名；
- 条件边源：源节点名；
- 条件边目标：源、分支名、目标节点名；
- 缺少入口：`entrypoint` 与 `START`；
- `path_map`：非法类型 / 非法元素。

错误消息语言沿用仓库既有风格（英文或中英混合均可；测试只断言关键标识符，不断言整句）。

---

## 6. 下游消费口径

### 6.1 B7F2

- MUST 调用 `_build_spec()`，MUST NOT 重新解析 schema / 重造节点边。
- 构造 `GraphSpec` 前 MUST **仅过滤单源键（`str`）的 `END` 目标**（B7F1 的 V-2 不接受
  `END` 作为目标）；**多源键（`tuple`）的 V-16 形态（目标为 `END` / 目标数 ≠ 1）MUST
  原样保留**，交给 `GraphSpec` 的 **V-16** 显式失败（B7F4 的「多源目标 MUST NOT 为
  `__end__`」与「多源目标 MUST 恰为一个」）。
- `_BuilderSpec.nodes` / `node_records` 中的 `__parent__` 节点名 MUST NOT 在 B6F1 过滤；
  由 `GraphSpec` 构造期 **B9F1 FR-005 `__parent__` 保留名检查**最终失败。
- MUST 保留 `_BuilderSpec.conditional_edges`，并机械翻译为纯内建类型
  `dict[str, tuple[dict[str, Any], ...]]`（内层 `{"branch": str, "path": Callable,
  "path_map": dict[Hashable, str] | None, "targets": tuple[str, ...],
  "route_channels": tuple[str, ...]}`，`branch` 取自 `_ConditionalEdgeSpec.branch`，
  形状以 spec D-2 为准）存放在 `CompiledGraph`
  私有字段（如 `_conditional_edges`）；在 B8F1 放宽 V-8 之前，MUST NOT 填充
  `GraphSpec.conditional_edges`。
- MUST 在 `CompiledGraph` 私有字段保留**完整 `_BuilderSpec`**（至少 `node_records`），
  供 B8F3 读取 alias；该保留 MUST NOT 改写快照内容。
- 条件边字段在 B7F2 阶段仍保持 `GraphSpec.conditional_edges` 为空（B7F1 的 V-8）；
  B8F1 落地时把该映射填入 `GraphSpec.conditional_edges` 并承接 V-8 放宽。
- MUST NOT 修改快照字段；如需变换，先复制。

### 6.2 B8F1（L2）

- MUST 把 B7F2 保留的 **plain mapping**（`dict[str, tuple[dict[str, Any], ...]]`）填入
  `GraphSpec.conditional_edges`，并承接 V-8 放宽；之后只消费 L2 的
  `GraphSpec.conditional_edges` 与 `branch:to:<target>` 路由通道。
- MUST NOT import `freegraph._stategraph` 或 `_ConditionalEdgeSpec`。
- MUST NOT 重新归一化 `path_map`。
- MUST NOT 另起路由通道命名；使用 `branch:to:<target>`。

### 6.3 B8F3

- MUST 从 B7F2 按 D-1 保留的 `_BuilderSpec.node_records` 中读取 `_NodeRecord.alias`。
- MUST NOT 要求用户重新声明别名。

---

## 7. 不变量与边界

- `freegraph.graph` 仍恰 7 个导出符号；`StateGraph` 公开签名快照逐字节不变。
- B4F1 / B5F1 / B7F1 的公开签名与语义零改动。
- 本 feature 不执行任何节点 / 路由函数 / 归约器。
- 本 feature 不实现 `compile()` / `invoke()` / `stream()` / `get_graph()` /
  `draw_mermaid()`。
- 本 feature 不实现别名寻址（B8F3）、`defer` 屏障（B7F4 X-03）、条件边求值（B8F1）、
  静态断点关键字（B7F2）。`defer=True` 目标的路由通道类型差异登记为 **X-7**（已知不支持）。
- 本 feature 不实现上游窄 `input_schema` 推断；`NodeSpec.subscribes` = 全部状态通道。
