# Data Model · B22F1 `get_graph(xray=)` + 自有 `Graph` + `draw_mermaid()`

**Feature**: `specs/b22f1-get-graph-mermaid/` · **Date**: 2026-11-20
**权威口径**: [spec.md](./spec.md) · [contracts/graph-export-contract.md](./contracts/graph-export-contract.md)

> 本文件只描述**数据形状与不变量**；算法细节见 plan.md §「关键算法」与契约 §3。

---

## §1 公开数据类（L1 · 冻结字段不变）

### 1.1 `Node`（`freegraph.contracts.graph.Node`）

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `id` | `str` | — | 图中唯一的节点标识（含 `__start__` / `__end__`） |
| `name` | `str \| None` | `None` → 归一为 `id` | 展示名 / 别名（本 feature 不解析 B8F3 别名） |
| `metadata` | `Mapping[str, Any]` | 空映射 | 由图导出填入（见 §3.2） |

- `frozen=True, slots=True, kw_only=True`；**不可哈希**。
- `__post_init__`：`name is None ⇒ id`；`metadata` 浅拷贝（**既有行为不变**）。
- 生产规则：`__start__` / `__end__` 的 `id == name`；业务节点 `name == id`（v1 无别名）。

### 1.2 `Edge`（`freegraph.contracts.graph.Edge`）

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `source` | `str` | — | 起点节点名 |
| `target` | `str` | — | 终点节点名（`END` 统一写 `__end__`） |
| `conditional` | `bool` | `False` | 是否条件 / 节点声明 / 条件终结边 |
| `condition` | `str \| None` | `None` | 分支名或 `destinations` 标签；无标签声明边为 `None` |

- `frozen=True, slots=True, kw_only=True`；`__hash__ = None`（不可哈希）。
- **不变式（本 feature 放宽 · T-6）**：
  - `add_conditional_edges` 的分支边：`conditional=True ⇒ condition` **非空**（`branch`）；
  - 节点声明的无标签边（`destinations` 序列 / `Command[Literal]` 推断）：
    `conditional=True` 且 `condition is None` **合法**（上游 `Edge.data=None` 同款）。

### 1.3 `Graph`（`freegraph.contracts.graph.Graph`）

| 字段 / 成员 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `nodes` | `tuple[Node, ...]` | `()` | 节点表（保序） |
| `edges` | `tuple[Edge, ...]` | `()` | 边表（保序，已去重） |
| `draw_mermaid()` | `() -> str` | — | **本 feature 追加**（T-5）；纯本地、确定性、永不抛 |

- `frozen=True, slots=True`；`__hash__ = None`。
- **不改**字段 / 构造签名 / `__all__`；只追加方法。
- `draw_mermaid` 的实现不读环境变量、不发起网络、不依赖时间 / 随机数。

---

## §2 `Command`（L1 · T-1）

### 2.1 形状

```python
N = TypeVar("N", bound=str)

@dataclass(frozen=True, slots=True, kw_only=True)
class Command(Generic[N]):
    goto: str | Send | Sequence[str | Send] | None = None
    update: Any | None = None
    resume: Any | None = None
    graph: str | None = None

    PARENT: ClassVar[Literal["__parent__"]] = "__parent__"
```

- **字段 / 缺省 / 校验 / `PARENT` / `__slots__` 语义逐字不变**。
- 新增：`Command[Literal["b","c"]]` 可下标；运行期 `Command(goto=...)` 行为不变。
- `N` **不参与**运行期校验；只用于图渲染的返回注解解析。

### 2.2 图渲染推断结果

| 输入（节点函数返回注解） | 结果 |
|---|---|
| `Command[Literal["b","c"]]` | `(("b", None), ("c", None))` |
| `Command[Literal["b","c"]] \| None` | 同上（`Union` 内找 `Command`） |
| `Command[Literal["b","__end__"]]` | `(("b", None), ("__end__", None))` |
| 无注解 / 非 `Command` / 非 `Literal` | 空元组（无声明） |
| 解析异常（`NameError` / `TypeError` / `StopIteration`） | 空元组（静默） |

### 2.3 `destinations` 归一化

| 输入 | 归一结果 |
|---|---|
| `None` 且无推断 | `()` |
| `None` 且有推断 | 推断结果 |
| `("b","c")` / `["b","c"]` / 任何非 `str` 的 `Sequence[str]` | `(("b", None), ("c", None))` |
| `{"b":"to-b","c":"to-c"}` | `(("b","to-b"), ("c","to-c"))`（保序） |
| `()` / `{}` | `()`（**显式覆盖为空**，不再使用推断） |
| 其它类型 / 元素非 `str` | 登记期 `TypeError` |

**优先级**：显式 `destinations` **覆盖**推断（即使为空）；`None` 才使用推断。

**实现分支（唯一）**：`add_node` MUST 先判 `destinations is None`：

```text
if destinations is None:
    effective = _infer_command_destinations(action)   # 可能是 ()
else:
    effective = _normalize_destinations(destinations) # 空序列 / 空 dict 也覆盖
```

`_normalize_destinations(None)` **不得**作为「未提供」的信号；它只用于已判定为显式值的调用路径。

---

## §3 编译期快照（L3 内部 · 只读）

### 3.1 `_NodeRecord`（扩展 · T-3）

| 字段 | 类型 | 语义 |
|---|---|---|
| `name` | `str` | 节点名 |
| `action` | `Callable[..., Any]` | 节点函数（**get_graph 不调用**） |
| `alias` | `str \| None` | B8F3 保留（本 feature 不解析） |
| `defer` | `bool` | 延迟节点标记 |
| `metadata` | `Mapping[str, Any] \| None` | 用户 metadata |
| **`destinations`** | `tuple[tuple[str, str \| None], ...]` | **追加**：归一后的图渲染目标；空元组 = 无声明 |

- `_NodeRecord` 仍为 `frozen=True`；新增字段有缺省，既有构造调用零改动。

### 3.2 导出所用的快照字段

| 快照 | 字段 | 用途 |
|---|---|---|
| `CompiledGraph._spec`（`GraphSpec`） | `nodes` | 业务节点名 + 顺序 |
| `_spec.edges` | `dict[str \| tuple[str,...], tuple[str,...]]` | 静态单源 / join 边（**单源 `END` 已被过滤**） |
| `CompiledGraph._conditional_edges` | 5 键 plain mapping | `branch` / `targets` / `route_channels` |
| `CompiledGraph._builder_spec` | `edges` | 恢复被过滤的 `END` 目标边 |
| `_builder_spec.node_records[name]` | `metadata` / `defer` / `destinations` | 节点 metadata / 延迟 / 声明边 |
| `CompiledGraph.interrupt_before_nodes` / `interrupt_after_nodes` | `tuple[str,...]` | `__interrupt` 标记 |

**只读约束**：导出 MUST NOT 修改上述任何映射 / 元组 / 记录（FR-024）。
**禁止**：调用 `_build_spec()` / 解析 `StateGraph` 活状态 / 执行节点。

---

## §4 导出中间体（L3 私有 · 不进公开面）

### 4.1 `_EdgeGroup`（不可变 · 仅实现用）

| 字段 | 类型 | 语义 |
|---|---|---|
| `sources` | `tuple[str, ...]` | 边长起点集合；单源 = 1 元组；join = 多源元组 |
| `target` | `str` | 终点（`END` 已归一为 `__end__`） |
| `conditional` | `bool` | 条件 / 声明 / 终结标记 |
| `condition` | `str \| None` | 分支名 / `destinations` 标签 |

- `sources == ("__start__",)` 表示入口组。
- 组只存在于导出函数内部；**不**成为公开类型。

### 4.2 组的来源与顺序

| # | 来源 | `sources` | `conditional` | `condition` |
|---|---|---|---|---|
| 1 | `_spec.edges` 单源键 | `(key,)` | `False` | `None` |
| 2 | `_builder_spec.edges` 中 `END` 目标（被过滤部分） | `(key,)` | `False` | `None` |
| 3 | `_spec.edges` 多源键（join） | `key` | `False` | `None` |
| 4 | `_conditional_edges[source][i].targets` | `(source,)` | `True` | `branch` |
| 5 | `node_records[name].destinations` | `(name,)` | `True` | `label`（可为 `None`） |
| 6 | 终结补边（§5.3） | `(name,)` | `False` | `None` |

顺序 = 上表 1→6；同组内目标按声明顺序。

### 4.3 可达性 / 可满足性

- `reachable` 初值 = `{"__start__"}`。
- 迭代至不动点：若组 `g` 满足 `∀ s ∈ g.sources: s ∈ reachable` ⇒ `reachable.add(g.target)`。
- `END` 是汇点：加入 `reachable` 后不再有出边。
- **只导出满足上述条件的组**。
- 不可达业务节点仍出现在 `nodes`，但不产生任何出边（匹配上游 E-7）。

### 4.4 终结补边

对每个 **可达**业务节点 `n`：

- 若已导出边中**没有** `source == n` 的边，且没有 `n→__end__` 的显式边 ⇒
  补 `Edge(n, "__end__", conditional=False)`。
- 若 `n` 只有**不可满足**的 join 出边 ⇒ 视为无出边 ⇒ 补 `END`（匹配上游 E-9）。
- **不复制**上游「末步单源补条件 END」的模拟启发式（X-08）。

### 4.5 去重

- 键 = `(source, target)`。
- 保留优先级：`conditional=True` > `conditional=False`；同级先出现者优先。
- `condition` **不参与**去重键；同端点两条条件边只保留一条（上游同款）。

---

## §5 mermaid 数据映射

### 5.1 节点 id（`_safe_id`）

```text
allowed = ASCII letters + digits + "_" + "-"
id = "".join(ch if ch in allowed else "\\" + format(ord(ch), "x") for ch in label)
```

- 与上游 `_to_safe_id`（`graph_mermaid.py:255-266`）逐字同款。
- 性质：不同输入 ⇒ 不同输出（前缀码式编码）。

### 5.2 标签（`_escape_label`）

处理顺序（**先 `#`，避免二次转义**）：

| 字符 | 替换 |
|---|---|
| `#` | `#35;` |
| `"` | `#quot;` |
| `\n` / `\r` | `<br/>` |
| `<` | `#lt;` |
| `>` | `#gt;` |
| `&` | `#amp;` |
| `\|` | `#124;` |
| `\` | `#92;` |
| 其它 | 原样 |

- 节点标签与边标签（`condition`）使用**同一个** `_escape_label`。
- 普通名（`a` / `b` / `__start__`）字面出现 ⇒ 满足 SC-002。

### 5.3 行格式

| 元素 | 格式 |
|---|---|
| 头部 | `graph TD;` |
| 节点 | `\t{id}["{escaped_name}"];` |
| 普通边 | `\t{src} --> {tgt};` |
| 条件边（有标签） | `\t{src} -. &nbsp;{escaped_condition}&nbsp; .-> {tgt};` |
| 条件边（无标签） | `\t{src} -.-> {tgt};` |
| 空图 | `graph TD;\n`（非空） |

- 无 YAML frontmatter；无样式参数族（X-05）。
- 同图同输出：不含时间 / 随机 / 环境信息。

---

## §6 不变量与失败信号

| # | 不变量 | 判定 |
|---|---|---|
| I-01 | `get_graph` 返回 `freegraph.contracts.graph.Graph` | `isinstance` / `type.__module__` |
| I-02 | `nodes` 含全部业务节点 + `__start__` + `__end__` | 集合相等 |
| I-03 | `__start__` / `__end__` 的 `id == name` | 逐项 |
| I-04 | 业务节点 `name == id`（不解析别名） | 逐项 |
| I-05 | 边端点都在 `nodes` | 逐项 |
| I-06 | 条件边 `conditional=True`；分支边 `condition` 非空 | 逐项 |
| I-07 | 同端点只一条边；条件优先 | 逐项 |
| I-08 | 不可达节点无出边 | 逐项 |
| I-09 | 可达无出边节点有 `→__end__` | 逐项 |
| I-10 | `draw_mermaid` 含全部节点名 / 合法结构 / 同图同文本 | 文本断言 |
| I-11 | 导出不修改任一快照 | 前后相等 |
| I-12 | `xray=True` 与 `False` 逐项相等 | 相等 |

| 失败信号 | 时机 | 类型 |
|---|---|---|
| `destinations` 非 `Sequence[str]` / 非 `dict[str,str]` | `add_node` 登记期 | 内置 `TypeError` |
| 声明目标不在节点表且非 `END` | `validate()` / `compile()` | 内置 `ValueError`（点名目标） |
| 注解不可解析 | `add_node` 登记期 | **静默**（无声明） |
| `get_graph` 合法产物 | 任意 | **不抛** |
| `draw_mermaid` 任意 `Graph` | 任意 | **不抛** |
