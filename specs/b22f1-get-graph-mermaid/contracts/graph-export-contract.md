<!-- authority: yes -->

# 图导出 / mermaid 契约（graph-export-contract.md）· B22F1

**Feature**: `specs/b22f1-get-graph-mermaid/` · **Date**: 2026-11-20
**契约性质**: **冻结面 · 唯一权威** —— `get_graph()` / `draw_mermaid()` / `Command` 泛型 /
`destinations` 的形状与机械判据
**上位权威**: [spec.md](../spec.md) · 本文件只把形状与判据**落细**，**不得**放宽 spec
**上游**: `langgraph 1.2.11`（锚点与实测见 [upstream-parity.md](./upstream-parity.md)）

> **机器标记**：`<!-- authority: yes -->`。下游 **B23F1** MUST 以本文件 §5 的文本口径为准。

---

## 0. 作用域

覆盖：

1. `CompiledGraph.get_graph(*, xray=False)` 的签名、返回类型与只读语义；
2. 节点表 / 边表的形状与顺序；
3. 条件边、节点声明边、join 边、终结 `END` 边的导出规则；
4. 可达性 / 去重 / metadata 的规则；
5. `Graph.draw_mermaid()` 的文本格式、安全 id、标签转义；
6. `Command` 泛型化与 `destinations` 的登记 / 推断 / 校验口径；
7. 上述面的失败信号与不变量。

**不覆盖**：`draw_mermaid_png()`（B23F1）· 子图（C26）· 别名（B8F3）·
checkpointer / store（B14F1 / v2）· trace（B18F1 / B19F1）。

---

## 1. `get_graph` 入口（**签名冻结**）

```python
def get_graph(self, *, xray: bool = False) -> Graph: ...
```

| # | 要求 |
|---|---|
| 1.1 | `xray` **仅关键字**、缺省 `False`；位置传参 ⇒ Python 自身 `TypeError` |
| 1.2 | 返回 `freegraph.contracts.graph.Graph`（**自有类型**） |
| 1.3 | `get_graph(xray=True)` 与 `get_graph(xray=False)` 在无子图时**逐项相等** |
| 1.4 | v1 对任意真值 / 假值 **不改变结果、不抛 `TypeError`**（签名兼容） |
| 1.5 | MUST NOT 增加 `config` 参数；MUST NOT 返回 `langchain_core` 类型 |
| 1.6 | MUST NOT 执行图 / 调用节点 / 调用 `invoke()` / `stream()` |
| 1.7 | MUST NOT 修改 `_spec` / `_builder_spec` / `_conditional_edges` |
| 1.8 | 每次返回**新** `Graph`（`Graph` 不可变；不得共享可变内部状态） |

---

## 2. 节点表

### 2.1 形状与顺序

```text
nodes = (
    Node(id="__start__", name="__start__"),
    Node(id=<业务节点 1>, name=<同名>, metadata=<按 §2.2>),
    ...
    Node(id=<业务节点 N>, name=<同名>, metadata=<按 §2.2>),
    Node(id="__end__", name="__end__"),
)
```

| # | 要求 |
|---|---|
| 2.1.1 | `__start__` 恒在首位；`__end__` 恒在末位 |
| 2.1.2 | 业务节点顺序 = `_spec.nodes` 的**声明顺序** |
| 2.1.3 | 业务节点 `name == id`（v1 不解析 B8F3 别名；`_NodeRecord.alias` 不参与） |
| 2.1.4 | **全部**业务节点都在表中（含不可达节点） |
| 2.1.5 | 不含路由通道（`branch:to:<target>`） |
| 2.1.6 | 不含 `_spec.channels` 中的非节点 key |

### 2.2 `metadata` 的填充（上游 `_draw.py:221-229` 同款）

对业务节点 `name`：

```python
meta = dict(builder_spec.node_records[name].metadata or {})
if builder_spec.node_records[name].defer:
    meta["defer"] = True
if name in interrupt_before and name in interrupt_after:
    meta["__interrupt"] = "before,after"
elif name in interrupt_before:
    meta["__interrupt"] = "before"
elif name in interrupt_after:
    meta["__interrupt"] = "after"
```

- `metadata` MUST 为**浅拷贝**（不得把用户映射原样交给 `Node`）。
- `__start__` / `__end__` 的 `metadata` = 空映射。
- `defer` 仅在 `True` 时出现；`__interrupt` 仅在命中时出现。

---

## 3. 边表

### 3.1 边的定义

每条边是 `Edge(source, target, conditional, condition)`：

| 来源 | `source` | `target` | `conditional` | `condition` |
|---|---|---|---|---|
| START 入口（`_spec.edges` 的 `"__start__"` 键） | `"__start__"` | 目标 | `False` | `None` |
| 静态单源边（`_spec.edges`） | 源节点 | 目标 | `False` | `None` |
| 静态 `END` 边（从 `_builder_spec.edges` 恢复） | 源节点 | `"__end__"` | `False` | `None` |
| join 边（`_spec.edges` 的 tuple 键） | 每个源各一条 | 目标 | `False` | `None` |
| `add_conditional_edges` | 源节点 | `targets` 每个目标 | `True` | `branch` |
| 节点声明（`destinations` / 推断） | 源节点 | 每个目标 | `True` | 标签或 `None` |
| 终结补边（§3.3） | 可达无出边节点 | `"__end__"` | `False` | `None` |

### 3.2 顺序

```text
START 入口 → 静态单源边（含 END）→ join 边 → 条件边 → 节点声明边 → 终结补边
```

- 组内目标按声明顺序 / `targets` 顺序 / 元组顺序。
- 最终边表必须**确定性**：同图同输入 ⇒ 同顺序。

### 3.3 终结补边

对每个 **可达**业务节点 `n`：

- 若已导出边中**没有** `source == n` 的边 ⇒ 补 `Edge(n, "__end__", False, None)`。
- 若 `n` 只有不可满足的 join 出边 ⇒ 视为无出边 ⇒ 补 `END`。
- **不补**上游「末步单源」条件 `END` 边（X-08）。

### 3.4 可达性

- `reachable = {"__start__"}`。
- 每条边先归一为 `_EdgeGroup(sources, target, ...)`：
  - 单源 / 条件 / 声明 = `sources` 为 1 元组；
  - join = `sources` 为元组键的**全部源**。
- 迭代至不动点：`∀ s ∈ sources: s ∈ reachable` ⇒ `target ∈ reachable`。
- **只导出可满足组**；不可达节点的出边不出现。
- `END` 是汇点；`__end__` 不再作为源（终结补边除外）。

### 3.5 去重

- 键 = `(source, target)`。
- 若重复：`conditional=True` 优先；同为普通 / 同为条件 ⇒ **先出现者**优先。
- `condition` 不参与判重。
- 同一端点不得同时出现实线与虚线（上游 `add_edge` 同款）。

### 3.6 `END` 的写法

- 图内统一写 `"__end__"`（不是 `END` 常量以外的字符串）。
- `END` 只在以下位置出现：`target`、终结补边、`nodes` 的合成 `__end__`。
- 多源 join 的 `END` 目标被 B7F4 构造期拒绝（本 feature 不重复校验）。

---

## 4. `Command` 泛型 + `destinations`（T-1 / T-2 / T-3）

### 4.1 `Command[N]`

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

| # | 要求 |
|---|---|
| 4.1.1 | 字段名 / 顺序 / 类型 / 缺省 / 构造校验**逐字不变** |
| 4.1.2 | `Command.PARENT == "__parent__"`；不在 `__slots__` / `fields()` |
| 4.1.3 | `Command[Literal["b"]]` **可构造**（下标不抛） |
| 4.1.4 | `Command(goto=...)` 的运行期语义**不变**（B9F1 零改动） |
| 4.1.5 | `__all__` 不变；不新增顶层符号 |

### 4.2 `add_node(destinations=)`

```python
def add_node(
    self,
    node: str | Callable[..., Any],
    action: Callable[..., Any] | None = None,
    *,
    alias: str | None = None,
    defer: bool = False,
    metadata: Mapping[str, Any] | None = None,
    destinations: dict[str, str] | tuple[str, ...] | None = None,
) -> Self: ...
```

| # | 要求 |
|---|---|
| 4.2.1 | 新关键字**仅** `destinations`；既有参数名 / 顺序 / 缺省不变 |
| 4.2.2 | 运行期接受任何**非 `str`** 的 `Sequence[str]`（含 list） |
| 4.2.3 | 运行期接受 `dict[str, str]`（键 = 目标，值 = 标签） |
| 4.2.4 | 运行期接受 `None`（= 使用返回注解推断） |
| 4.2.5 | `add_node` MUST 先判 `destinations is None`：`None` ⇒ 使用 §4.3 推断；**其余（含空序列 / 空 dict）** ⇒ 显式覆盖（不再用推断） |
| 4.2.6 | **仅影响图渲染**，MUST NOT 改变执行 / 触发 / 写入 |
| 4.2.7 | 声明目标 MUST 是已登记节点或 `END`；否则编译期 `ValueError` |
| 4.2.8 | 形态非法 ⇒ 登记期 `TypeError` |

### 4.3 类型推断（登记期）

| # | 要求 |
|---|---|
| 4.3.1 | 在 `add_node` 内对 `action` 做上游同款 guard：`isfunction(action)` / `ismethod(action)` / `ismethod(action.__call__)`；先取 `get_type_hints(action.__call__)`，再回退 `get_type_hints(action)` |
| 4.3.2 | 返回注解为 `Union` ⇒ 在其中找 `Command` 分支 |
| 4.3.3 | `get_origin(Command[...]) is Command` 且首参 origin 为 `Literal` ⇒ 取 `get_args` 值 |
| 4.3.4 | `NameError` / `TypeError` / `StopIteration` ⇒ **静默**（无声明） |
| 4.3.5 | 推断结果随 `_NodeRecord` 冻结；MUST NOT 在 `compile()` 重算 |
| 4.3.6 | 结果目标保留顺序；`END` 原样保留（导出时归一为 `__end__`） |

### 4.4 `_NodeRecord.destinations`

```python
destinations: tuple[tuple[str, str | None], ...] = ()
```

- 空元组 = 无声明（不是 `None`）。
- 归一后保序；`dict` 值 = 标签；序列 / 推断 = `None` 标签。
- 该字段是**图渲染声明**，**不**进入 `GraphSpec.edges`、**不**影响调度。

---

## 5. `draw_mermaid()`（**下游 B23F1 的唯一文本口径**）

### 5.1 入口

```python
def draw_mermaid(self) -> str: ...
```

| # | 要求 |
|---|---|
| 5.1.1 | 无参数；仅用 `self.nodes` / `self.edges` |
| 5.1.2 | 纯本地：零网络、零子进程、零环境变量、零第三方 |
| 5.1.3 | 对任何 `Graph`（含空图、`condition=None`）**返回 `str`**，永不抛 |
| 5.1.4 | 确定性：同图同文本（逐字相等） |
| 5.1.5 | 输出 MUST 以 `graph TD;` 开头；**不含** YAML frontmatter |
| 5.1.6 | 输出 MUST 非空（空图 = 至少头部 + 换行） |

### 5.2 节点行

```text
\t{_safe_id(node.id)}["{_escape_label(node.name)}"];
```

- 顺序 = `Graph.nodes` 顺序。
- `_safe_id`：`[A-Za-z0-9_-]` 原样；其它 → `\` + 小写十六进制码点。
- `_escape_label`：见 §5.4。
- 普通名（`a` / `b`）字面出现 ⇒ SC-002。

### 5.3 边行

| 类型 | 格式 |
|---|---|
| 普通边 | `\t{src} --> {tgt};` |
| 条件边（`condition` 非 `None`） | `\t{src} -. &nbsp;{escaped_condition}&nbsp; .-> {tgt};` |
| 条件边（`condition is None`） | `\t{src} -.-> {tgt};` |

- `src` / `tgt` = `_safe_id(source)` / `_safe_id(target)`。
- 条件边 MUST 为**虚线**；普通边 MUST 为**实线**。
- 标签文本 MUST 与节点标签同款转义（§5.4）。
- 顺序 = `Graph.edges` 顺序。

### 5.4 `_escape_label`（**顺序敏感**）

```text
1. "#" -> "#35;"
2. '"' -> "#quot;"
3. "\n" / "\r" -> "<br/>"
4. "<" -> "#lt;"
5. ">" -> "#gt;"
6. "&" -> "#amp;"
7. "|" -> "#124;"
8. "\\" -> "#92;"
9. 其它字符原样
```

> 必须先处理 `#`，否则后续生成的 `#quot;` 等实体会被二次转义。

### 5.5 合法性判据

| # | 判据 |
|---|---|
| 5.5.1 | 首行 == `graph TD;` |
| 5.5.2 | 每条节点 / 边行以 `;` 结尾 |
| 5.5.3 | 节点 id 只含 `[A-Za-z0-9_\\-]`（编码后） |
| 5.5.4 | 引号成对；无裸换行（换行已转 `<br/>`） |
| 5.5.5 | 条件边使用 `-.` / `.->`；普通边使用 `-->` |
| 5.5.6 | `condition is None` 的条件边无 `&nbsp;` 标签段 |
| 5.5.7 | 无 `mermaid.ink` / `http://` / `https://` 字样 |

---

## 6. 失败信号

| # | 场景 | 时机 | 信号 |
|---|---|---|---|
| 6.1 | `destinations` 非序列 / 非映射 / 元素非 `str` | `add_node` | 内置 `TypeError` |
| 6.2 | 声明目标不在节点表且非 `END` | `validate()` / `compile()` | 内置 `ValueError`（点名） |
| 6.3 | 注解无法解析 | `add_node` | **静默**（无声明） |
| 6.4 | `get_graph` 对合法编译产物 | 任意 | **不抛** |
| 6.5 | `draw_mermaid` 对任何 `Graph` | 任意 | **不抛** |
| 6.6 | 未知 `xray` 值 | 任意 | **不抛**（v1 忽略） |

---

## 7. 不变量（I-01…I-12）

| # | 不变量 | 判据 |
|---|---|---|
| I-01 | 返回类型 | `type(g).__module__ == "freegraph.contracts.graph"` 且 `type(g).__name__ == "Graph"` |
| I-02 | 节点集合 | == `{"__start__"} ∪ spec.nodes ∪ {"__end__"}` |
| I-03 | 伪节点名 | `__start__` / `__end__` 的 `id == name` |
| I-04 | 业务节点名 | `name == id`（无别名解析） |
| I-05 | 边端点 | 所有 `source` / `target` 都在节点 id 集合 |
| I-06 | 条件标记 | 分支边 `conditional=True` 且 `condition` 非空 |
| I-07 | 去重 | 无重复 `(source,target)`；条件优先 |
| I-08 | 不可达 | 不可达节点无出边 |
| I-09 | 终结 | 可达无出边节点有 `→__end__` |
| I-10 | mermaid | 含全部 `node.name`；§5.5 全过 |
| I-11 | 只读 | 导出前后快照相等 |
| I-12 | xray | `True` / `False` 的 `nodes` / `edges` 逐项相等 |

---

## 8. 下游接口（B23F1）

B23F1 `draw_mermaid_png()` MUST：

1. 以 `graph.draw_mermaid()` 的返回值为**唯一** mermaid 输入；
2. 复用本契约 §5 的格式 / 转义（MUST NOT 另写生成器）；
3. 保留全部条件边 / 节点声明边 / join 边；
4. **MUST NOT** 访问 `mermaid.ink` 或任何外部域名；
5. 不改变本契约的文本格式（若必须改，走契约修订）。
