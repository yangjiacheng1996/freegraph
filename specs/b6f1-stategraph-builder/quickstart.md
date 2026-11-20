# Quickstart · B6F1 · `StateGraph` 构建器

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contract**: [contracts/builder-contract.md](./contracts/builder-contract.md)

> **2026-11-20 后续修订（C25 正式作废）**：差分场景 **D-74** 已迁移到 **B8F3 D-142**；
> 本文件的 `D-50…D-74` 为历史范围，`parity_probe.py` 不再承载 D-74。

> 本文件是**验证指南**，不是实现教程。所有验证只做「建图 / 校验 / 读取私有快照」；
> **不调用** `compile()` / `invoke()`。`compile()` 仍属 B7F2。

---

## 1. 前置条件

```bash
cd /home/ctyun/workspace/github/freegraph
.venv/bin/python -V          # 期望 3.11.x
.venv/bin/python -m pytest -q
```

基线要求：既有测试全绿；`harness/demo/target.py` 的 git diff 为空。

---

## 2. 场景 A · target 风格建图原样执行

> 「原样」指 `target.py:142-155` 的**建图调用**原样；schema 用等价的本地 `TypedDict`
> 替身（`MessagesState` 是脚本自带的 langchain 类型，freegraph 不需要它）。

```python
from typing import TypedDict
from freegraph.graph import StateGraph, START, END

class State(TypedDict):
    count: int

def llm_call(state: State) -> dict:
    return {}

def tool_node(state: State) -> dict:
    return {}

def should_continue(state: State) -> str:
    return "tool_node"

agent_builder = StateGraph(State)
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
agent_builder.add_edge("tool_node", "llm_call")

agent_builder.validate()
spec = agent_builder._build_spec()

assert list(spec.nodes) == ["llm_call", "tool_node"]
assert spec.edges["__start__"] == ("llm_call",)
assert spec.edges["tool_node"] == ("llm_call",)
assert len(spec.conditional_edges) == 1
```

**期望**：无异常；`_build_spec()` 的节点 / 边 / 条件边与声明一致；`validate()` 返回同一 builder。
**不得**调用 `compile()`。

---

## 3. 场景 B · `path_map` 的 list 与 dict

```python
# list 形态
g1 = StateGraph(State)
g1.add_node("r", llm_call)
g1.add_node("a", tool_node)
g1.add_edge(START, "r")
g1.add_conditional_edges("r", should_continue, ["a", END])
g1.validate()
ce1 = g1._build_spec().conditional_edges[0]
assert ce1.branch == "should_continue"
assert ce1.targets == ("a", END)
assert ce1.route_channels == ("branch:to:a",)

# dict 形态
g2 = StateGraph(State)
g2.add_node("r", llm_call)
g2.add_node("hit", tool_node)
g2.add_node("miss", tool_node)
g2.add_edge(START, "r")
g2.add_conditional_edges("r", should_continue, {"hit": "hit", "miss": "miss"})
g2.validate()
ce2 = g2._build_spec().conditional_edges[0]
assert ce2.branch == "should_continue"
assert ce2.path_map == {"hit": "hit", "miss": "miss"}
assert ce2.targets == ("hit", "miss")
assert ce2.route_channels == ("branch:to:hit", "branch:to:miss")
```

**期望**：两形态都成功；list 被归一化为 `{name: name}`；dict 保持用户映射；`END` 不建路由通道。

---

## 4. 场景 C · 构建期错误

```python
from freegraph.graph import StateGraph

# 1) 重复节点名
g = StateGraph(State)
g.add_node("a", llm_call)
try:
    g.add_node("a", llm_call)
except ValueError as exc:
    assert "a" in str(exc)

# 2) 边指向不存在节点（构建期末；先建立有效入口以隔离该错误）
g = StateGraph(State)
g.add_node("a", llm_call)
g.add_edge(START, "a")
g.add_edge("a", "missing")
try:
    g.validate()
except ValueError as exc:
    assert "missing" in str(exc)

# 3) 缺少入口
g = StateGraph(State)
g.add_node("a", llm_call)
g.add_edge("a", END)
try:
    g.validate()
except ValueError as exc:
    assert "entrypoint" in str(exc).lower() or "START" in str(exc)

# 4) validate(interrupt=...) 未知节点（与上游同款）
g = StateGraph(State)
g.add_node("a", llm_call)
g.add_edge(START, "a")
g.add_edge("a", END)
try:
    g.validate(interrupt=["missing"])
except ValueError as exc:
    assert "missing" in str(exc)

# 5) 非法 start_key（立即层）
g = StateGraph(State)
g.add_node("a", llm_call)
try:
    g.add_edge(123, "a")
except TypeError:
    pass
```

**期望**：前四类错误均在构建期抛出 `ValueError`，消息可定位问题；非法 `start_key`
立即抛 `TypeError`。

---

## 5. 场景 D · 链式与不执行用户函数

```python
calls = {"node": 0, "router": 0}

def node(state: State) -> dict:
    calls["node"] += 1
    return {}

def router(state: State) -> str:
    calls["router"] += 1
    return "b"

g = StateGraph(State)
assert g.add_node("a", node).add_edge(START, "a").add_edge("a", "b") is g
g.add_node("b", node)
g.add_conditional_edges("a", router, ["b", END])
g.validate()

assert calls == {"node": 0, "router": 0}
```

**期望**：链式返回同一对象；构建期节点 / 路由函数调用计数为 0。

---

## 6. 运行测试与验收

```bash
# 只跑构建器相关测试
.venv/bin/python -m pytest -q tests/facade/test_stategraph_builder.py \
  tests/facade/test_stategraph_validation.py tests/facade/test_facade.py

# 全量回归
.venv/bin/python -m pytest -q

# 差分（上游缺席即 skip）
.venv/bin/python harness/scripts/diff_parity.py -k builder

# 一键验收
.venv/bin/python harness/verification/B6F1/acceptance.py

# public API 快照（必须不变）
.venv/bin/python -m pytest -q tests/facade/test_api_snapshot.py
```

**期望**：

- 构建器相关测试全绿；
- `tests/facade/test_facade.py` 只保留 `compile()` / 其余未交付方法的未接线断言；
- 差分 D-50…D-73 符合各自判词（D-74 已迁移到 B8F3 D-142）；
- acceptance 脚本输出 `B6F1 acceptance: PASS`；
- API 快照零差异。

---

## 7. 明确不应期

- `compile()` 仍抛 `NotImplementedError`（B7F2）。
- `invoke()` / `stream()` / `get_graph()` / `draw_mermaid()` 不存在或仍为桩。
- `harness/demo/graph_core.py` 仍以退出码 2 表示「环境未就绪」；
  **不是**本 feature 的失败。
- `target.py` 端到端跑通仍需 B7F2 / B7F3 / B8F1 / B22F1 / B23F1 齐备。

---

## 8. 相关文件

- 需求：`spec.md`（21 FR / 15 SC）
- 设计：`plan.md` · `research.md`
- 形状 / 校验：`data-model.md` · `contracts/builder-contract.md`
- 上游证据 / 差分：`contracts/upstream-parity.md`
- 验收：`harness/verification/B6F1/acceptance.py` · `manual-verification.md`
