# Research · B22F1 `get_graph(xray=)` + 自有 `Graph` + `draw_mermaid()`

**Feature**: `specs/b22f1-get-graph-mermaid/` · **Date**: 2026-11-20
**上游版本**: `langgraph 1.2.11`（用户 site-packages · 非仓库依赖）
+ 同批 `langchain-core`（`runnables/graph.py` / `runnables/graph_mermaid.py`）
**运行环境**: `.venv` · CPython **3.11.16** · pytest 9.2.0 · packaging 26.3

> 纪律：宪法原则 XI「上游有答案 ⇒ 照抄」；**行为断言 MUST 有实测支撑**。
> 本节只记录**已取证**的决定；没有 `NEEDS CLARIFICATION`。

---

## §0.1 取证环境与锚点复核（T003 的落点）

**环境**：`.venv` · CPython **3.11.16** · `pytest 9.2.0` · `packaging 26.3`；
上游 `langgraph==1.2.11` + 同批 `langchain-core`（非仓库依赖）。

**复核锚点**（2026-11-20）：

| 用途 | 路径:行号 |
|---|---|
| `get_graph` | `langgraph/pregel/main.py:845-870` |
| 图导出 / 模拟 | `langgraph/pregel/_draw.py:42,138-151,221-257,286-288` |
| 静态声明 / 推断 / `destinations` | `langgraph/graph/state.py:810-861,1150-1162,1780-1788` |
| mermaid 文本 | `langchain_core/runnables/graph_mermaid.py:45,255-266,277,422-423` |
| `Graph` / `Node` / `Edge` | `langchain_core/runnables/graph.py:65,95,255` |

换上游版本 MUST 重新核实全部行号并改写版本号（原则 XI ③）。

---

## §1 决策清单（Decision / Rationale / Alternatives）

### D-01 · 动态 `goto` 目标的来源：上游静态声明，**删除**运行期记录

- **Decision**：`get_graph` 的节点声明边来自 ① `Command[Literal[...]]` 返回注解推断；
  ② `add_node(destinations=...)`。无运行期观测字段。
- **Rationale**：上游在「图渲染」维度更优（静态、不依赖运行）；发起者 2026-11-20 裁定
  「最优设计优先」。freegraph 原 `Command` 非泛型 ⇒ 只能靠运行期记录 ⇒ 已证伪为更差。
- **Alternatives**：① 保留运行期记录（依赖 `invoke`、丢失未观测分支）② 只加
  `destinations`（无法自动支持类型标注）③ 只做泛型（无边图 / 无标注场景无解）⇒ 均拒绝。
- **证据**：E-3 / E-4 / E-5 / E-8 / E-9 / E-13 / E-15。

### D-02 · `Command` 泛型化的最小改动面

- **Decision**：`class Command(Generic[N])`；字段（`goto` / `update` / `resume` / `graph`）、
  构造签名、`PARENT` 哨兵、运行期校验**逐字不变**。
- **Rationale**：上游 `types.py:799` 为 `Generic[N]`；图渲染需要 `Command[Literal[...]]`
  可下标。运行期不需要知道 `N`。
- **Alternatives**：新增第二个类型（`CommandWithTargets`）⇒ 破坏同名同签名与用户代码。
- **锚点**：`src/freegraph/contracts/types.py:60`；上游 `langgraph/types.py:799`。

### D-03 · 类型推断：登记期 `get_type_hints` + `Union` 解包 + 静默降级

- **Decision**：`add_node` 登记时对节点函数（含 `__call__`）取 `get_type_hints`；
  返回注解若为 `Union`，找出 `Command` 分支；若首参 `Literal[...]`，取其值为目标。
  `NameError` / `TypeError` / `StopIteration` **静默忽略**（无声明）。
- **Rationale**：与上游 `graph/state.py:810-858` 逐字同款；登记期冻结避免编译期重算漂移。
- **Alternatives**：编译期重算（前向引用解析更晚、与上游不一致）；报错（上游静默）。
- **证据**：E-3（推断出 `b` / `c`）；E-5（`destinations` 覆盖推断）。

### D-04 · `destinations`：形态、归一化与覆盖

- **Decision**：签名按上游写 `dict[str,str] | tuple[str,...] | None`；运行期接受任何
  非 `str` 的 `Sequence[str]`（含列表）；`dict` 值 = 边标签；显式值**覆盖**推断。
  归一为 `tuple[tuple[target, label | None], ...]`（保序）。
- **Rationale**：上游 `state.py:404-410` / `:860-861`；列表接受为实测。
- **Alternatives**：只接受 tuple（拒绝上游用户常见的 list）；合并推断 + 显式（上游为覆盖）。
- **证据**：E-4 / E-4b / E-4c / E-5。

### D-05 · 图导出：边组 + 静态可达闭包

- **Decision**：所有边先归一为 `_EdgeGroup(sources, target, conditional, condition)`：
  - 单源静态 / 条件 / 声明边 ⇒ 组大小 1；
  - 多源 join（`_spec.edges` 的 tuple 键）⇒ **全源一组**；
  - 从 `__start__` 出发迭代：组的**全部源**可达 ⇒ 目标可达（`END` 为汇点）；
  - 只为**可满足组**导出边。
- **Rationale**：上游 `_draw.py` 的模拟只发现可达边；静态闭包是其无执行等价物。
- **Alternatives**：不做可达过滤（不可达节点的出边会多出来，与上游不符）；
  模拟执行（违反零执行 / X-08）。
- **证据**：E-7（不可达 `d`：节点在、边无）；E-9（join 一源不可达 ⇒ 组不导出 + `a→END`）。

### D-06 · 多源 join 的渲染：每源一条普通边

- **Decision**：join 组导出时**每个源各一条** `Edge(source,target)`，`conditional=False`。
  `Graph.Edge` 是单起点，**不造 n 元边**。
- **Rationale**：上游 `add_edge([a,b], c)` 实测就是 `a→c` + `b→c`。
- **Alternatives**：单条边带 `sources` 字段 ⇒ 改冻结类型；不导出（丢结构）。
- **证据**：E-8；E-9。

### D-07 · 节点 `metadata`：拷贝 + `defer` + `__interrupt`

- **Decision**：`Node.metadata` 从 `_builder_spec.node_records[name].metadata` 浅拷贝；
  `defer=True` ⇒ `metadata["defer"]=True`；中断 ⇒
  `metadata["__interrupt"] = "before" | "after" | "before,after"`。
- **Rationale**：上游 `_draw.py:221-229` 同款；图评审可看到断点/延迟节点。
- **Alternatives**：忽略 metadata（与上游不符、丢可观察性）。
- **证据**：E-11。

### D-08 · 终结节点补 `END`

- **Decision**：可达业务节点若**没有任何已导出出边**且未显式连 `END`，补一条普通
  `node→__end__`。
- **Rationale**：上游 `_draw.py:247-257` 的 `termini` 同款。
- **Alternatives**：不补（图看起来悬空；与上游不符）。
- **证据**：E-2 / E-4 / E-7 / E-8。

### D-09 · 去重：按 `(source,target)`，条件 / 声明边优先

- **Decision**：重复端点只保留一条；`conditional=True` 优先；同为普通 / 同为条件时先出现者优先。
- **Rationale**：上游 `add_edge` 按端点去重；实测条件 / 声明边覆盖同端点静态边。
- **Alternatives**：四字段全等去重（会同时出现实线与虚线，与上游不符）。
- **证据**：E-13 / E-15。

### D-10 · 不模拟执行；登记两处模拟性边界

- **Decision**：不复制上游 `_draw.py` 的 Pregel 模拟；不复制「末步单源补条件 END」
  与 `limit=250` 截断（X-08）。
- **Rationale**：B22F1 的硬约束是**零执行 / 零副作用**；模拟会把运行期语义带回来。
- **Alternatives**：逐字模拟（与 `get_graph` 的只读承诺冲突）。
- **证据**：E-10（单源自环额外 `a→END`）；E-12（两节点循环额外 `b→END`）；
  E-3（循环末步单源额外 `a→END`）。

### D-11 · mermaid：`graph TD;` + 安全 id + 标签转义

- **Decision**：
  - 头部 `graph TD;`；v1 不输出 YAML frontmatter；
  - 节点 id：`[A-Za-z0-9_-]` 原样，其它 → `\` + 小写十六进制码点（上游 `_to_safe_id` 同款）；
  - 标签包双引号；`#` 先转 `#35;`，再转 `"`→`#quot;`、换行→`<br/>`、`<`/`>`/`&`/`|`/
    `\` 为对应实体；
  - 普通边 `-->`；条件边虚线；`condition` 非 `None` 带标签，`None` 仅虚线；
  - 空图返回 `graph TD;\n`。
- **Rationale**：上游 `graph_mermaid.py:45,255`；freegraph 额外要求标签安全（X-04）。
- **Alternatives**：原样输出标签（非法 mermaid 风险）；引入 YAML 库（第三方依赖）。
- **证据**：E-14；E-16。

### D-12 · 条件边标签：分支名 vs `None`

- **Decision**：`add_conditional_edges` 的边 `condition = branch`；节点声明边
  `condition = destinations` 的标签或 `None`。
- **Rationale**：prompt 要求条件边虚线 + 标签；上游 `Edge.data` 对两类均为 `None`
  ⇒ freegraph 的 `condition` 是自有字段（X-07 / X-09）。
- **Alternatives**：全部 `None`（评审不可读）；全部固定 `"goto"`（偏离上游 `data=None`）。
- **证据**：E-2 / E-3 / E-4 / E-13。

### D-13 · 层归属

- **Decision**：`Graph.draw_mermaid` 与转义助手放 **L1** `contracts/graph.py`；
  图导出放 **L3** `_stategraph.py`。
- **Rationale**：`Graph` 是 L1 类型；方法必须同模块 ⇒ 否则 L1 反向 import L3（ARCH-1）。
  L1 实现只用标准库、无 import 副作用 ⇒ 不违反「契约层零行为（import 无副作用）」。
- **Alternatives**：新建 L3 渲染器 + monkey-patch（不可维护）；把 `Graph` 搬去 L3
  （破坏公开导入路径）。
- **锚点**：层注册表 `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md:95`
  （`_stategraph.py` = L3）；`tests/contracts/test_architecture.py:122`（`contracts/graph.py`）。

### D-14 · 失败信号

- **Decision**：`destinations` 形态非法 ⇒ 登记期 `TypeError`；声明目标不存在 ⇒
  编译期 `ValueError`（点名目标）；注解不可解析 ⇒ 静默；`draw_mermaid` 永不抛。
- **Rationale**：上游 `state.py:1150-1162` + `:857-858` 同款；导出本身零新增异常类型。
- **证据**：E-6。

### D-15 · 破冻结面：T-1…T-6 一次追认

- **Decision**：`Command` 泛型 · `add_node(destinations=)` · `_NodeRecord` 追加字段 ·
  B9F1 D-8 作废 · `Graph.draw_mermaid` · `Edge.condition=None` 放宽。
- **Rationale**：发起者 2026-11-20 明确「勇于打破冻结面，按最优设计执行」。
- **Alternatives**：保留旧冻结面（已证伪为更差设计）。
- **追认**：`harness/verification/B22F1/manual-verification.md`。

---

## §2 实测证据（E-1…E-16）

> 运行方式：`.venv` 或系统 Python 均可（仅上游包）；`graph = g.compile().get_graph()`。
> 场景图状态 schema 为 `S(TypedDict, total=False): v: int`。

### E-1 · 基本形状（线性图 + 条件边）

```text
建图：START→a；a --route--> {b, END}；b→END
NODES: __start__, a, b, __end__
EDGES: __start__→a(False,None); a→__end__(True,None); a→b(True,None); b→__end__(False,None)
```

### E-2 · 条件边标记 + 终结 `END`

```text
EDGES: ('a','__end__',True,None); ('a','b',True,None); ('b','__end__',False,None)
⇒ 条件边 conditional=True；终结节点补普通 END 边。
```

### E-3 · `Command[Literal["b","c"]]` 推断（不运行）

```text
def lit(s) -> Command[Literal["b","c"]]: ...
建图：START→a；b→a；c→a（循环）
EDGES: a→b(True,None); a→c(True,None); b→a(False,None); c→a(False,None);
       a→__end__(True,None)   ← 末步单源模拟性边（见 D-10 / X-08）
```

### E-4 / E-4b / E-4c · `destinations` 三种形态

```text
dict {"b":"to-b","c":"to-c"} ⇒ a→b(True,'to-b'); a→c(True,'to-c')
tuple ("b","c")               ⇒ a→b(True,None);  a→c(True,None)
list  ["b"]                   ⇒ a→b(True,None)    （运行期接受列表）
```

### E-5 · `destinations` 覆盖注解推断

```text
注解 Command[Literal["b","c"]] + destinations={"c":"only-c"}
EDGES: a→c(True,'only-c')   ⇒ 仅 c，且标签 only-c；b 未出现
```

### E-6 · 声明未知目标

```text
destinations=("nope",) ⇒ compile() 抛 ValueError: Found edge ending at unknown node `nope`
```

### E-7 · 不可达节点

```text
建图：START→a；d 有 destinations={"a":"x"} 但无入边
NODES: __start__, a, d, __end__   （d 在）
EDGES: __start__→a; a→__end__     （d 的出边不出现）
```

### E-8 · 多源 join（两源都可达）

```text
add_edge(["a","b"], "c")
EDGES: __start__→a; __start__→b; a→c(False); b→c(False); c→__end__(False)
```

### E-9 · 多源 join（一源不可达）

```text
建图：START→a；add_edge(["a","b"],"c")；b 无入边
EDGES: __start__→a; a→__end__   （a→c / b→c 都不出现）
```

### E-10 · 单节点自环 + 无显式 END

```text
建图：START→a；a→a
EDGES: __start__→a; a→a(False); a→__end__(True)   ← 末步单源启发式（X-08）
```

### E-11 · `metadata` / `defer` / `__interrupt`

```text
add_node("a", a, metadata={"k":"v"}, defer=True)
compile(interrupt_before=["a"], interrupt_after=["b"])
a.metadata == {'k': 'v', 'defer': True, '__interrupt': 'before'}
b.metadata == {'__interrupt': 'after'}
```

### E-12 · 两节点循环（末步单源）

```text
建图：START→a；a→b；b→a
EDGES: __start__→a; a→b(False); b→a(False); b→__end__(True)
⇒ 末步只剩 b 一个源 ⇒ 上游补 b→__end__ 条件边（X-08，freegraph 不补）
```

### E-13 · 去重：声明边覆盖静态边

```text
add_edge("a","b") + add_node("a", destinations={"b":"cond"})
EDGES: a→b(True,'cond')   ⇒ 条件 / 声明边优先
```

### E-14 · mermaid 安全 id

```text
_to_safe_id('a"b') == 'a\\22b'
_to_safe_id('x\ny') == 'x\\ay'      （换行 U+000A）
上游 draw_mermaid 默认头部含 YAML frontmatter + 'graph TD;'
```

### E-15 · 条件边覆盖静态边

```text
add_edge("a","b") + add_conditional_edges("a", ..., ["b"])
EDGES: a→b(True,None)   ⇒ 条件优先
```

### E-16 · 本 feature 目标文本形态（设计样例）

```text
graph TD;
    __start__["__start__"];
    a["a"];
    b["b"];
    __end__["__end__"];
    __start__ --> a;
    a -. &nbsp;route&nbsp; .-> b;
    a -.-> __end__;
    b --> __end__;
```

---

## §3 基线（实施前）

```text
.venv/bin/python -m pytest -q
1661 passed, 4 skipped in 108.22s (0:01:48)
```

> 系统 `python3`（3.12）基线为 `1646 passed / 10 failed / 9 skipped`：失败均为环境
> （未安装 `freegraph` + `packaging 24.0` 缺 `packaging.licenses`）。**不作为基线**。

---

## §4 未决项

**无。** 所有 spec 的 `[NEEDS CLARIFICATION]` 槽位为零；设计点均有 D-01…D-15 唯一裁定。
