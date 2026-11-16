# Quickstart · B7F2 · `compile()` → `CompiledGraph`

**Feature**: `specs/b7f2-compile/` · **Date**: 2026-11-16
**用途**：**可运行**的验证指南 —— 每一节都是「复制即可跑」的判据演示，不是实现教程。
**契约细节**见 `contracts/compile-contract.md`；**数据形状**见 `data-model.md`；**判据编号**见 `spec.md`。

---

## 1. 前置条件

```bash
cd /path/to/freegraph

# ① 依赖自证：零第三方运行时依赖
.venv/bin/python -c "import freegraph, sys; print(freegraph.__version__)"

# ② 本 feature 的入口（compile 已接线；invoke 仍属 B7F3）
.venv/bin/python - <<'PY'
from freegraph.graph import StateGraph
print("compile 可调用：", callable(StateGraph.compile))
print("非法 schema 预期：", end=" ")
try:
    StateGraph(dict).compile()
except Exception as exc:
    print(type(exc).__name__)   # 期望 InvalidSchemaError（dict 不是合法 schema）
PY
```

**期望**：`compile` 可调用；非法 schema 在**编译期**失败（`InvalidSchemaError`）。

---

## 2. 场景 A · 一行拿到可执行图（SC-001 / SC-004）

```python
from typing import Annotated, TypedDict
import operator

from freegraph.graph import START, END, StateGraph


class State(TypedDict):
    messages: Annotated[list, operator.add]
    calls: int


def node_a(state: State) -> dict:
    return {"messages": ["a"], "calls": 1}


def node_b(state: State) -> dict:
    return {"messages": ["b"]}


graph = StateGraph(State)
graph.add_node("a", node_a).add_node("b", node_b)
graph.add_edge(START, "a").add_edge("a", "b").add_edge("b", END)

compiled = graph.compile()          # ← A2：无参可调用

assert compiled is not None         # ← A1：产物非空
for name in (
    "invoke", "stream", "get_graph",
    "get_state", "get_state_history", "update_state",
):
    assert hasattr(compiled, name), name            # ← SC-004：6/6

try:
    compiled.invoke({"messages": [], "calls": 0})
except NotImplementedError as exc:
    assert "B7F3" in str(exc)       # ← 未就绪 ⇒ 点名归属 feature
print("A 通过")
```

> ⚠️ **本 feature 不执行图**：`invoke` 抛 `NotImplementedError`（B7F3）。
> 若你期望它跑通，那属于 **B7F3** 的验收。

---

## 3. 场景 B · 注入可插拔能力（SC-002 / SC-015）

```python
import warnings
from freegraph.graph import START, END, StateGraph
from tests.facade._builder_support import State   # 或自定义 TypedDict

def make():
    g = StateGraph(State)
    g.add_node("a", lambda s: {})
    g.add_edge(START, "a").add_edge("a", END)
    return g

# ① None / None ⇒ 不抛 TypeError（A3）
make().compile(checkpointer=None, store=None)

# ② 任意对象被接受 + 可从公开属性读到（身份保留）
sentinel_ckpt, sentinel_store = object(), object()
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    compiled = make().compile(checkpointer=sentinel_ckpt, store=sentinel_store)

assert compiled.checkpointer is sentinel_ckpt
assert compiled.store is sentinel_store
assert len(caught) == 1 and "Store" in str(caught[0].message)   # ← 裁定 14：恰好 1 条

# ③ 不传 store ⇒ 零警告
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    safe = make().compile()
assert caught == []                    # ← checkpointer / cache 等不发警告
assert safe.store is None
print("B 通过")
```

**顺带可观察（上游同款 · E-31 / E-33）**：
`compiled.debug is False` · `compiled.name is None` · `compiled.interrupt_before_nodes == ()`
· `compiled.cache is None` · `compiled.transformers is None`。

---

## 4. 场景 C · 编译期发现图定义的问题（SC-003）

```python
from freegraph.graph import START, END, StateGraph
from tests.facade._builder_support import State

# 错误 1 · 边指向不存在的节点（先建立有效入口，隔离出唯一错误）
g = StateGraph(State)
g.add_node("a", lambda s: {})
g.add_edge(START, "a")
g.add_edge("a", "missing")
try:
    g.compile()
except ValueError as exc:
    assert "missing" in str(exc)

# 错误 2 · 条件边源不存在
g = StateGraph(State)
g.add_node("a", lambda s: {})
g.add_edge(START, "a").add_edge("a", END)
g.add_conditional_edges("nope", lambda s: "a", ["a", END])
try:
    g.compile()
except ValueError as exc:
    assert "nope" in str(exc)

# 错误 3 · path_map 目标不存在
g = StateGraph(State)
g.add_node("a", lambda s: {})
g.add_edge(START, "a").add_edge("a", END)
g.add_conditional_edges("a", lambda s: "x", {"x": "missing"})
try:
    g.compile()
except ValueError as exc:
    assert "missing" in str(exc)
print("C 通过")
```

> **失败点 MUST 是 `compile()` 那一行**（不是 `invoke()`）—— 这就是「编译期是最后的机会」。

---

## 5. 场景 D · 静态断点的 6 种形态（SC-005 / SC-007）

```python
from freegraph.graph import START, END, StateGraph
from freegraph.runtime._static import normalize_static_points
from tests.facade._builder_support import State

def make():
    g = StateGraph(State)
    g.add_node("a", lambda s: {}).add_node("b", lambda s: {})
    g.add_edge(START, "a").add_edge("a", "b").add_edge("b", END)
    return g

# ① None ⇒ ()
assert make().compile(interrupt_before=None).interrupt_before_nodes == ()

# ② 裸 "*" ⇒ 全部可执行节点
assert make().compile(interrupt_before="*").interrupt_before_nodes == ("a", "b")

# ③ list[str] ⇒ 保序去重
assert make().compile(interrupt_before=["b", "a", "b"]).interrupt_before_nodes == ("b", "a")

# ④ 元组 ⇒ 入口层 TypeError（B13F1 D-1：tuple 只在 compile 入口拒绝）
for bad in (("a",), {"a"}, 1, 1.5):
    try:
        make().compile(interrupt_before=bad)
    except TypeError:
        pass
    else:
        raise AssertionError(bad)

# ⑤ 裸非 "*" 字符串 ⇒ TypeError（消息与 GraphSpec 构造期**逐字**一致）
try:
    make().compile(interrupt_before="a")
except TypeError as exc:
    expected = None
    try:
        normalize_static_points("a", {"a": None, "b": None}, "interrupt_before")
    except TypeError as ref:
        expected = str(ref)
    assert expected == str(exc), (expected, str(exc))

# ⑥ 未知节点 ⇒ 编译期 ValueError（点名该节点）
try:
    make().compile(interrupt_before=["nope"])
except ValueError as exc:
    assert "nope" in str(exc)
print("D 通过")
```

**另外两条（元素级）**：`["*"]` ⇒ `ValueError`（`"*"` 不能作元素）；
`[""]` ⇒ `ValueError`（空串元素）。两者消息与 `GraphSpec` 构造期一致。

---

## 6. 场景 E · 一次编译、多次安全使用（SC-011 / SC-012）

```python
from dataclasses import fields
from freegraph.graph import START, END, StateGraph
from tests.facade._builder_support import State

def make():
    g = StateGraph(State)
    g.add_node("a", lambda s: {})
    g.add_edge(START, "a").add_edge("a", END)
    return g

# ① 编译后改图 ⇒ 已编译产物不变
g = make()
first = g.compile()
before = list(first._spec.nodes)
g.add_node("late", lambda s: {})
assert list(first._spec.nodes) == before            # 快照隔离

# ② 两次编译 ⇒ 两个独立产物
second = g.compile()
assert first is not second
assert "late" in second._spec.nodes and "late" not in first._spec.nodes

# ③ 通道是**未写入的模板**（零残留）+ 两个映射对象独立
assert first._spec.channels is not first._builder_spec.channels
fresh = make().compile()                          # 另一次编译，同样从未执行
for key, template in first._spec.channels.items():
    assert template.checkpoint() == fresh._spec.channels[key].checkpoint(), key
assert first._spec.conditional_edges == {}    # ← 恒空（B8F1 之前）

# ④ 冻结的私有字段名（下游按名读）
for name in ("_spec", "_builder_spec", "_conditional_edges"):
    assert hasattr(first, name), name
print("E 通过")
```

---

## 7. 场景 F · 编译期零副作用（SC-005）

```python
from freegraph.graph import START, END, StateGraph
from tests.facade._builder_support import CallCounter, State

counter = CallCounter()

g = StateGraph(State)
g.add_node("a", counter.node("a"))
g.add_edge(START, "a").add_edge("a", END)
g.add_conditional_edges("a", counter.router("r", target="a"), ["a", END])

g.compile()
assert counter.counts == {}, counter.counts    # 节点 / 路由一次都没被调用
print("F 通过")
```

**零出站**由门禁 **G27**（只观测不阻断的 socket 夹具）在**全量测试套件**上断言；
本场景只需证明「编译不调用用户函数」。

---

## 8. 运行测试与验收

```bash
# 只跑本 feature 的 facade 测试
.venv/bin/python -m pytest tests/facade/test_compiled_graph.py \
    tests/facade/test_compile_validation.py \
    tests/facade/test_compile_interrupt.py -q

# 既有门面 / 构建器回归（含 TestNotWired 的拆分结果）
.venv/bin/python -m pytest tests/facade/test_facade.py -q

# 差分（上游缺席 ⇒ skip）
.venv/bin/python tests/differential/parity_probe.py -k compile

# 一键验收
.venv/bin/python harness/verification/B7F2/acceptance.py

# 全量回归
.venv/bin/python -m pytest -q

# 关键门禁
.venv/bin/python harness/scripts/gates/gate_G25_import_graph.py     # 层方向（L3 单文件）
.venv/bin/python harness/scripts/gates/gate_G27_zero_egress.py      # 零出站
.venv/bin/python harness/scripts/gates/gate_G29_contract_carrier.py # 只读基准 diff + 验收脚本
.venv/bin/python harness/scripts/gates/gate_G30_attribution.py      # 署名头 100%
```

**期望**：全绿；`graph_core.py` 的 **A3 组（`case_build_and_compile`）先通过**，随后因
`invoke` 未就绪（B7F3）以**退出码 2** 结束（并打印 `[环境未就绪]`）—— 这是
`harness/demo/graph_core.py` 的 `main()`「先跑 A3、再探 `invoke`」口径的结果，
**不是失败**。

---

## 9. 明确不应期（MUST NOT expect）

| # | 不存在的行为 | 归属 |
|---|---|---|
| 1 | `compiled.invoke(...)` 跑通图 | **B7F3** |
| 2 | `compiled.stream(...)` / `get_graph()` / 状态查询 | **B8F2** / **B22F1** / **B15F1** / **B16F1** |
| 3 | `checkpointer=` 真的保存检查点 | **B14F1** |
| 4 | `store=` 真的读写长期记忆 | **v1 无实现**（v2） |
| 5 | 条件边求值 / fresh 读 | **B8F1** |
| 6 | 节点别名寻址 | **B8F3** |
| 7 | `compile()` 检查「路由返回值是否在 `path_map` 中」 | 运行期（B8F1）失败 |
| 8 | `compile()` 检查节点可达性 / 环 | **不做**（上游同款） |
| 9 | `compile()` 校验 `checkpointer` / `store` 的类型 | **不做**（B14F1 补 checkpointer 校验） |
| 10 | `CompiledGraph` 出现在 `freegraph.graph` 的导出面 | **不会**（B2F2 冻结 7 符号） |

---

## 10. 相关文件

| 路径 | 作用 |
|---|---|
| `specs/b7f2-compile/spec.md` | 需求 / 判据 / 上游对照 / 偏离登记（**唯一权威**） |
| `specs/b7f2-compile/contracts/compile-contract.md` | 编译契约（形状 · 校验 · 接口 · 禁止事项） |
| `specs/b7f2-compile/contracts/upstream-parity.md` | 上游锚点 / 差分口径 / X 取证底稿 |
| `specs/b7f2-compile/data-model.md` | 实体 / 不变量 / CV / NV / 状态机 |
| `specs/b7f2-compile/research.md` | E-25…E-55 实测 + DR-1…DR-16 |
| `src/freegraph/_stategraph.py` | 实现体（`StateGraph.compile` + `CompiledGraph`） |
| `harness/verification/B7F2/` | 一键验收 + 人工验证记录 |
