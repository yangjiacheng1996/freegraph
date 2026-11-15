# Data Model · B6F1 · `StateGraph` 构建器

**Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md) · **Date**: 2026-11-15

> 本文件只落实体 / 形状 / 校验 / 不变量（可自动判定的部分）；**MUST NOT** 改写 spec 的任何语义。
> 一切语义以 `spec.md` 为唯一权威。所有新增类型均为 **私有**（下划线开头），不进门面、
> 不进 API 快照。

---

## 1. 实体总览

| # | 实体 | 层 | 公开性 | 关系 |
|---|---|---|---|---|
| **EM-1** | `StateGraph` 构建器 | L3 | 公开（门面导出） | 持有 schema / 节点 / 边 / 条件边 |
| **EM-2** | `_NodeRecord` | L3 | 私有 | 一个节点登记项 |
| **EM-3** | 静态边表 | L3 | 私有（构建期） | 源键 → 目标序列 |
| **EM-4** | `_ConditionalEdgeDraft` | L3 | 私有（构建期） | 一条条件边草稿 |
| **EM-5** | `_ConditionalEdgeSpec` | L3 | 私有（快照） | 冻结的条件边规格 |
| **EM-6** | `_BuilderSpec` | L3 | 私有（快照） | 构建器 → B7F2 的唯一内部规格 |
| **EM-7** | 状态通道 | L2 | L2 内部 API | B4F1 / B5F1 产出 |
| **EM-8** | 路由通道 | L2 | L2 内部 API | `branch:to:<target>` · `EphemeralValue` |
| **EM-9** | `NodeSpec` | L2 | L2 内部 API | 订阅集 + 节点函数 |

---

## 2. `StateGraph` 内部状态

```python
class StateGraph:
    _schema: Any
    _nodes: dict[str, _NodeRecord]
    _edges: dict[str | tuple[str, ...], list[str]]
    _conditional_edges: list[_ConditionalEdgeDraft]
    _branch_names: dict[str, set[str]]
```

| 字段 | 类型 | 语义 | 不变量 |
|---|---|---|---|
| `_schema` | `Any` | 用户传入的 state schema；构造期不解析 | 构造后不被构建器改写 |
| `_nodes` | `dict[str, _NodeRecord]` | 节点名 → 登记项；**保序** | key 唯一；顺序 = `add_node` 顺序 |
| `_edges` | `dict[str \| tuple[str, ...], list[str]]` | 源键 → 目标列表（构建期可变） | 目标列表无重复；单源键为 `str`，多源键为 `tuple` |
| `_conditional_edges` | `list[_ConditionalEdgeDraft]` | 条件边草稿；**保序** | 顺序 = `add_conditional_edges` 顺序 |
| `_branch_names` | `dict[str, set[str]]` | 源节点 → 已用分支名 | 同一源的分支名不重复 |

> 构造期只初始化空容器，MUST NOT 解析 schema、MUST NOT 调用任何用户函数、MUST NOT 做 I/O。

---

## 3. 登记实体

### 3.1 `_NodeRecord`

```python
@dataclass(frozen=True)
class _NodeRecord:
    name: str
    action: Callable[..., Any]
    alias: str | None = None
    defer: bool = False
    metadata: Mapping[str, Any] | None = None
```

| 字段 | 语义 | 校验 / 备注 |
|---|---|---|
| `name` | 节点内部名 | `str`；非 `START` / `END`；不含 `\|` / `:`；唯一；单 callable 形态取 `__name__` → 类型名（普通 callable 的 `.name` 不参与） |
| `action` | 节点函数 | 可调用；构建期不调用、不检查返回注解 |
| `alias` | 对外别名 | 接受 `str \| None` 并记录；冲突 / 寻址语义归 B8F3 |
| `defer` | 上游同款关键字 | 接受并记录；`defer=True` 屏障不在本 feature 实现（B7F4 X-03） |
| `metadata` | 上游同款元数据 | 接受并浅拷贝记录；本 feature 不消费 |

> **类型校验边界**：本 feature **不校验** `alias` / `defer` / `metadata` 的运行时类型
> （如 `alias=123`、`defer="yes"`、`metadata` 非 Mapping）；只按上述规则原样记录，
> 类型收紧留给后续 feature 或另行立项。

### 3.2 静态边表

| 形态 | 示例 | 语义 |
|---|---|---|
| 单源 | `"a": ["b", "c"]` | `a` 执行后触发 `b` / `c` |
| 多源 | `("a", "b"): ["c"]` | `a` / `b` 共同汇合到 `c`（屏障语义由 L2 实现） |

不变量：

1. 目标列表**无重复**（相同 `(source, target)` 幂等）；
2. 目标顺序 = **首次登记顺序**；
3. 单源键保持 `str`，多源键保持 `tuple[str, ...]`（保序、去重）；
4. `_BuilderSpec.edges` 中值 MAY 含 `END`；B7F2 在构造 `GraphSpec` 前**仅过滤单源键的
   `END`**；多源键的 **V-16 形态**（`END` / 目标数 ≠ 1）MUST 原样保留给 `GraphSpec`
   的 V-16 显式失败。

### 3.3 `_ConditionalEdgeDraft`

```python
@dataclass(frozen=True)
class _ConditionalEdgeDraft:
    source: str
    path: Callable[..., Any]
    path_map: dict[Hashable, str] | None
    branch_name: str
```

| 字段 | 语义 | 备注 |
|---|---|---|
| `source` | 条件边源节点 | 可为 `START`；构建期末校验存在性 |
| `path` | 路由函数 | 可调用；构建期不调用 |
| `path_map` | 归一化映射 | list → dict；dict 浅拷贝；`None` 可能由 `Literal` 推断 |
| `branch_name` | 同一源上的分支名 | `path.__name__`；普通 callable 的 `.name` 不参与；lambda / 无名 ⇒ `condition`（上游 `_runnable.py:313-319`）；同源唯一 |

---

## 4. 快照实体

### 4.1 `_BuilderSpec`

> 字段列表以 `spec.md` **FR-007** 为唯一权威；本节只描述形状与消费者，不独立定义语义。

```python
@dataclass(frozen=True)
class _BuilderSpec:
    channels: dict[str, Channel]
    nodes: dict[str, NodeSpec]
    node_records: dict[str, _NodeRecord]
    edges: dict[str | tuple[str, ...], tuple[str, ...]]
    conditional_edges: tuple[_ConditionalEdgeSpec, ...]
```

| 字段 | 形态 | 语义 | 消费者 |
|---|---|---|---|
| `channels` | `dict[str, Channel]` | 状态通道（schema 顺序）+ 路由通道（目标首次出现顺序） | B7F2 → `GraphSpec.channels` |
| `nodes` | `dict[str, NodeSpec]` | 节点规格；`subscribes` = 全部状态通道 | B7F2 → `GraphSpec.nodes` |
| `node_records` | `dict[str, _NodeRecord]` | 原始节点登记（含 alias / defer / metadata） | B7F2 按 D-1 在 `CompiledGraph` 私有字段保留；B8F3 读取 alias |
| `edges` | `dict[str \| tuple[str, ...], tuple[str, ...]]` | 静态边；值 MAY 含 `END` | B7F2（仅过滤**单源** `END` 后 → `GraphSpec.edges`；多源 **V-16 形态**（`END` / 目标数 ≠ 1）保留给 V-16） |
| `conditional_edges` | `tuple[_ConditionalEdgeSpec, ...]` | 条件边规格；登记顺序 | B7F2 机械翻译为纯内建类型 `dict[str, tuple[dict[str, Any], ...]]`（内层 `{"branch": str, "path": Callable, "path_map": dict[Hashable, str] \| None, "targets": tuple[str, ...], "route_channels": tuple[str, ...]}`，`branch` 取自 `_ConditionalEdgeSpec.branch`，形状以 spec D-2 为准）并存放于 `CompiledGraph` 私有字段；B8F1 经 L2 `GraphSpec.conditional_edges` 消费 |

### 4.2 `_ConditionalEdgeSpec`

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

| 字段 | 语义 | 不变量 |
|---|---|---|
| `source` | 条件边源节点 | 在节点表里，或为 `START` |
| `branch` | 同一源上的分支名 | `_branch_name(path)` 的登记结果；同一 `source` 上唯一 |
| `path` | 路由函数 | 原对象，不复制、不调用 |
| `path_map` | 归一化映射 | `dict[Hashable, str] \| None`；与用户原对象解耦（浅拷贝）；`None` 且推断不到时保持 `None` |
| `targets` | 唯一目标集合 | 归一化 values 的首次出现顺序；**含 `END`**；`path_map=None` 且推断不到 ⇒ `()` |
| `route_channels` | 路由通道名 | `branch:to:<target>`；仅非 `END` 目标；顺序与 `targets` 中的非 `END` 一致；`path_map=None` 且推断不到 ⇒ `()` |

> **消费者边界**：`_ConditionalEdgeSpec` 属 L3。B7F2（L3）负责把它翻译为 L2 可消费的
> 普通映射；B8F1（L2）只消费 `GraphSpec.conditional_edges`，MUST NOT import 本类型。

### 4.3 快照不变量

1. **新副本**：每次 `_build_spec()` 返回新对象、新通道实例、新元组；
2. **结构等价**：两次快照按「通道类型 / 归约器 / key + 节点 / 边 / 分支字段」比较，不按通道对象身份；
3. **调用方不修改**：`_BuilderSpec` 的 dict 字段约定由调用方只读；构建器不再持有已返回快照的引用；
4. **零用户代码执行**：快照过程不调用节点函数、路由函数、归约器；
5. **失败不改状态**：`_build_spec()` / `validate()` 失败后，`StateGraph` 的登记状态不变。

---

## 5. 校验规则（BV-1…BV-13）

> 编号 `BV-n` = Builder Validation；**MUST NOT** 与 B7F1 的 V-n / B7F4 的 V-16 混淆。
> 图结构错误只用内置 `ValueError` / `TypeError`；schema 错误沿用 B4F1 `InvalidSchemaError`。

| # | 规则 | 时机 | 失败信号 | 消息要点 |
|---|---|---|---|---|
| **BV-1** | `node` 非 `str` 且非 callable；或 `str` 节点缺 `action` / `action` 不可调用；或 callable 形态同时传 `action` | `add_node` 立即 | `TypeError` | 点名参数形态 |
| **BV-2** | 节点名为 `START` / `END`；含 `\|` / `:`；重复 | `add_node` 立即 | `ValueError` | 点名节点名 / 保留名 / 保留字符 |
| **BV-3** | 单 callable 形态取不到名字 | `add_node` 立即 | `ValueError` | 说明无法推断节点名 |
| **BV-4** | `start_key` 既非 `str` 也非 `list` / `tuple`；`end_key` 非 `str` | `add_edge` 立即 | `TypeError` | 点名参数 |
| **BV-5** | `END` 作边源；`START` 作边目标 | `add_edge` 立即 | `ValueError` | 点名哨兵 |
| **BV-6** | 多源边为空；多源边的源不存在 / 为 `END`；多源目标不存在且非 `END` | `add_edge` 立即 | `ValueError` | 点名源 / 目标 |
| **BV-7** | `source` 非 `str`；`path` 不可调用 | `add_conditional_edges` 立即 | `TypeError` | 点名参数 |
| **BV-8** | `path_map` 非 list / dict / None；list 元素非 `str`；dict value 非 `str` | `add_conditional_edges` 立即 | `TypeError` | 点名 `path_map` 与非法值 |
| **BV-9** | 同一 `source` 上分支名重复 | `add_conditional_edges` 立即 | `ValueError` | 点名源与分支名 |
| **BV-10** | schema 非法 | `validate()` / `_build_spec()` | B4F1 `InvalidSchemaError` | 由 B4F1 提供 |
| **BV-11** | 节点表为空（源 / 入口 / 目标校验通过后，如 `START -> END`） | `validate()` / `_build_spec()` | `ValueError` | 点名「节点表为空」；**在 BV-12c 之后执行**（X-5） |
| **BV-12a** | 源存在性：静态边源（单源 / 多源）与条件边源（`START` 除外）不存在 | `validate()` / `_build_spec()` | `ValueError` | 点名源 |
| **BV-12b** | 缺少 `START` 入口（静态边或条件边 source == `START`） | `validate()` / `_build_spec()` | `ValueError` | `entrypoint` / `START` |
| **BV-12c** | 目标存在性：静态边目标或条件边目标不存在且非 `END` | `validate()` / `_build_spec()` | `ValueError` | 点名源 / 分支 / 目标 |
| **BV-13** | `validate(interrupt=...)` 含未知节点 | `validate()` | `ValueError` | 点名该节点（与上游 `state.py:1168-1174` 同款） |

> **校验顺序**（`_build_spec`）：schema → **BV-12a 源** → **BV-12b 入口** → **BV-12c 目标**
> → **BV-11 空节点表（X-5）** → 建路由通道 → 组装快照。该顺序与上游 `validate()` 的
> 「源 → 入口 → 目标」一致；空节点表是本项目更严项，放在最后。
> ⚠️ **校验范围**：B6F1 的「与 L2 `GraphSpec` 构造语义一致」**仅限 V-1 / V-2 / V-3**；
> B9F1 FR-005 的 **`__parent__` 保留名检查**（`GraphSpec` 构造期，与 V-1 / V-2 / V-3 同族）
> 与 **V-16**（多源目标为 `END` / 目标数 ≠ 1）**不在本层提前校验**，由 **B7F2** 构造
> `GraphSpec` 时最终失败。
> `validate(interrupt=...)` 在 `_build_spec` 成功后校验 `interrupt` 节点存在性（BV-13）。
> 任何一步失败即停止；构建器状态不被修改。

---

## 6. 顺序与确定性

| 维度 | 顺序来源 |
|---|---|
| 状态通道 key | schema 声明顺序（B4F1 `SchemaSpec.keys`） |
| 路由通道 key | 条件边登记顺序 + 归一化 values 首次出现顺序 |
| 节点表 | `add_node` 登记顺序 |
| 静态边目标 | 首次登记顺序 |
| 静态边 key | 首次登记顺序（单源 / 多源各自保序） |
| 条件边 | `add_conditional_edges` 登记顺序 |
| 分支目标 / 路由通道 | `path_map` 归一化后的首次出现顺序 |

> 相同输入的两次 `_build_spec()` MUST 结构等价；不得引入哈希序或不稳定集合迭代。

---

## 7. 状态机（构建期）

```text
CONSTRUCTED
  │  只保存 schema；空容器
  ▼
REGISTERING
  │  add_node / add_edge / add_conditional_edges
  │  立即层校验（BV-1…BV-9）
  ▼
VALIDATING
  │  validate() / _build_spec()
  │  schema → 源（BV-12a）→ 入口（BV-12b）→ 目标（BV-12c）→ 空节点表（BV-11 / X-5）
  │  validate(interrupt=...) 节点存在性（BV-13）
  ├─ 失败 ──▶ REGISTERING（状态不变，可修正后重试）
  ▼
SNAPSHOT_READY
  │  _BuilderSpec（新副本）
  ▼
（B7F2 消费）
```

- **没有运行期状态**：本 feature 不执行节点，不存在 RUNNING / SUSPENDED 等状态。
- **没有 compile 状态**：`compile()` 仍抛 `NotImplementedError`（B7F2）。

---

## 8. 边界

- 不实现 `compile()` / `invoke()` / `stream()` / `get_graph()` / `draw_mermaid()`。
- 不实现条件边求值 / fresh 读（B8F1）。
- 不实现别名寻址 / 冲突（B8F3）；B8F3 只从 B7F2 保留的 `_BuilderSpec.node_records` 读取 alias。
- 路由通道 `branch:to:<target>` 与用户 schema key 同名时，复制上游覆盖行为
  （`state.py:1525-1530`）；登记为已知边界，不新增 spec 判据（research **O-1**）。
- 不实现 `defer=True` 的节点专用屏障（B7F4 X-03）。路由通道对 `defer=True` 目标仍用
  `EphemeralValue`；上游对 defer 目标用 `LastValueAfterFinish`，该差异登记为 **X-7**（已知不支持），由 B7F4 X-03 在 defer 落地时一并处理。
- 不实现上游窄 `input_schema` 自动推断；`NodeSpec.subscribes` = 全部状态通道。
- 不承载非 callable `Runnable` / Runnable-like 对象（X-6）；只接受普通 callable。
- 不实现 `add_sequence` / `set_entry_point` / `set_conditional_entry_point` /
  `set_finish_point` / `set_node_defaults`。
- 不实现静态断点关键字；`compile()` 的 `interrupt_before` / `interrupt_after` 归 B7F2。
- 空节点表保留为比上游更严的失败（X-5）；上游 `START -> END` 空图接受。
- 多源边的 **V-16 形态**（目标为 `END` / 目标数 ≠ 1）不在本层失败；由 B7F2 的
  `GraphSpec` 最终失败（B7F4）。
- 节点名 `__parent__` 不在本层失败；由 B7F2 的 `GraphSpec` 构造期 **B9F1 FR-005 的 `__parent__` 保留名检查**最终失败。
