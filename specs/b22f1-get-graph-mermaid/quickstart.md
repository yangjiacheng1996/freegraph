# Quickstart · B22F1 `get_graph(xray=)` + 自有 `Graph` + `draw_mermaid()`

**Feature**: `specs/b22f1-get-graph-mermaid/` · **Date**: 2026-11-20
**目的**: 用**可运行**的场景验证图导出与 mermaid 文本导出；不含实现细节。

---

## §0 前置

```bash
cd /home/ctyun/workspace/github/freegraph
.venv/bin/python --version          # 期望 Python 3.11.x
.venv/bin/python -m pytest -q       # 基线：1661 passed, 4 skipped
```

> ⚠️ 必须用 `.venv`：系统 `python3`（3.12）未安装 `freegraph` 且 `packaging 24.0`
> 缺 `packaging.licenses` ⇒ 环境性失败，不代表代码红。

---

## §1 最小验收（P1 / P2）

```python
from typing import TypedDict

from freegraph.graph import END, START, StateGraph

class State(TypedDict, total=False):
    v: int

def a(state):   return {"v": 1}
def b(state):   return {"v": 2}
def route(s):   return "b"

g = StateGraph(State)
g.add_node("a", a)
g.add_node("b", b)
g.add_edge(START, "a")
g.add_conditional_edges("a", route, ["b", END])
g.add_edge("b", END)
app = g.compile()

graph = app.get_graph()
print(type(graph).__module__, type(graph).__name__)
print([n.id for n in graph.nodes])
print([(e.source, e.target, e.conditional, e.condition) for e in graph.edges])
print(graph.draw_mermaid())
```

**期望**

- `type(graph).__module__ == "freegraph.contracts.graph"`，`type(graph).__name__ == "Graph"`；
- 节点含 `a` / `b`（以及 `__start__` / `__end__`）；
- 边含 `__start__→a`、`a→b`（`conditional=True`）、`b→__end__`；
- mermaid 首行 `graph TD;`，含 `a` / `b`，条件边为虚线。

---

## §2 `xray` 签名兼容（C26 v1）

```python
g1 = app.get_graph(xray=True)
g0 = app.get_graph(xray=False)
assert g1.nodes == g0.nodes
assert g1.edges == g0.edges
```

**期望**：无子图时两者逐项相等；不抛 `TypeError`。

---

## §3 节点声明的动态目标（C13 / B9F1）

### 3.1 返回注解推断

```python
from typing import Literal
from freegraph.graph import Command  # 门面再导出

def a(state) -> Command[Literal["b", "c"]]:
    return Command(goto="b")

def b(state): return {}
def c(state): return {}

g = StateGraph(State)
g.add_node("a", a)
g.add_node("b", b)
g.add_node("c", c)
g.add_edge(START, "a")
app = g.compile()

edges = {(e.source, e.target): e for e in app.get_graph().edges}
assert ("a", "b") in edges and ("a", "c") in edges
assert edges[("a", "b")].conditional is True
assert edges[("a", "b")].condition is None
```

**期望**：**不运行**即可看到 `a→b` 与 `a→c` 两条边（MUST NOT 只有一条）。

### 3.2 显式 `destinations`

```python
g = StateGraph(State)
g.add_node("a", a, destinations={"b": "to-b", "c": "to-c"})
g.add_node("b", b)
g.add_node("c", c)
g.add_edge(START, "a")
edges = {(e.source, e.target): e for e in g.compile().get_graph().edges}
assert edges[("a", "b")].condition == "to-b"
assert edges[("a", "c")].condition == "to-c"
```

**期望**：`destinations` 的标签成为 `condition`；显式声明**覆盖**返回注解推断。

---

## §4 不可达节点与 join 边

```python
g = StateGraph(State)
g.add_node("a", a)
g.add_node("b", b)
g.add_node("d", a, destinations={"b": "x"})   # 无入边 ⇒ 不可达
g.add_edge(START, "a")
g.add_edge(START, "b")
g.add_edge(["a", "b"], "a")                   # join（多源）
graph = g.compile().get_graph()
```

**期望**

- `d` 在 `graph.nodes` 中，但没有任何 `source == "d"` 的边；
- join `["a","b"]→a` 导出为 `a→a` 与 `b→a` 两条普通边（不是一条 n 元边）；
- 不可达 / 无出边节点按 §3.3 补 `→__end__`（若适用）。

---

## §5 断网 / 零出站（P3）

```python
import socket

class _Guard:
    def __init__(self): self.calls = 0
    def __call__(self, *a, **k):
        self.calls += 1
        raise AssertionError("框架尝试出站")

guard = _Guard()
_orig = socket.socket
socket.socket = guard
try:
    text = app.get_graph().draw_mermaid()
finally:
    socket.socket = _orig

assert isinstance(text, str) and text.strip()
assert guard.calls == 0
```

**期望**：`draw_mermaid()` 成功，且 **框架出站 = 0**（不访问 `mermaid.ink`）。

---

## §6 特殊字符 / 合法性

```python
g = StateGraph(State)
g.add_node('a"b', a)
g.add_node("x\ny", b)
g.add_edge(START, 'a"b')
g.add_edge('a"b', "x\ny")
text = g.compile().get_graph().draw_mermaid()
print(text)
```

**期望**

- 首行 `graph TD;`；每行以 `;` 结尾；
- 节点 id 已安全编码（`a\22b` / `x\ay` 形态）；
- 标签中的 `"` / 换行已转义（`#quot;` / `<br/>`）；
- 文本可通过 §5.5 的合法性判据；不出现裸反斜杠 / 裸引号 / 裸换行。

---

## §7 差分（可选 · 有上游时）

```bash
.venv/bin/python -m pytest -q tests/differential/parity_probe.py -k "B22F1 or D_0" 
```

**期望**：上游缺席 ⇒ skip；在场 ⇒ D-01…D-15 按 `contracts/upstream-parity.md` 的判词通过。
**MUST NOT** 断言 mermaid 文本逐字等于上游。

---

## §8 一键验收

```bash
.venv/bin/python harness/verification/B22F1/acceptance.py
```

**期望输出**

```text
B22F1 acceptance: PASS
```

**退出码**：`0` = PASS · `1` = FAIL · `2` = 环境未就绪（如缺依赖 / 未安装）。
脚本 MUST 覆盖 A1–A4：

| # | 判据 | 脚本覆盖 |
|---|---|---|
| A1 | `draw_mermaid()` 离线必然成功 | §5 的 socket 守卫 + 文本合法性 |
| A2 | 零出站 | §5 的出站计数 == 0 |
| A3 | `get_graph(xray=)` 可用 | §2 |
| A4 | 自有 `Graph` 类型 | §1 的类型断言 + 依赖门禁 |

---

## §9 人工验证（门禁）

完成后 MUST 在 `harness/verification/B22F1/manual-verification.md` 记录**五段式**：

1. 环境（`.venv` / Python / 上游版本）；
2. 步骤（§1–§8 的命令）；
3. **实际输出**（真实粘贴，MUST NOT 伪造）；
4. 结论（A1–A4 逐条）；
5. 遗留问题（含 T-1…T-6 的追认文字：发起者 2026-11-20 · 承接方 B22F1）。
