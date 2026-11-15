# Quickstart: B13F1 · 静态中断点 + `recursion_limit`

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-11-15

> **本文件是验证指南（可运行场景）** ⇒ **不含**实现代码、不含完整测试套件。
> ⚠️ 全部场景用「手写图规格」（`GraphSpec` + `NodeSpec` + `run_graph`）⇒
> **不经由** `StateGraph` / `compile()` / `invoke()` ⇒ 本 feature 可在 **M1 独立验收**
> （构建器 / `invoke` 属 M2 · 见 §8）。

---

## 0. 前置条件

### 0.1 环境

```bash
# 仓库既有口径（B3F1）
uv venv .venv
uv pip install --python .venv --group dev
uv pip install --python .venv --no-deps -e .
```

### 0.2 绿基线

```bash
.venv/bin/python -m pytest -q
# 期望：1203 passed / 4 skipped（2026-11-15 基线；本 feature 后应 ≥ 1203 + 新增）
```

### 0.3 checkpointer 桩

静态挂起的恢复需要 `Checkpointer` 协议。本 feature **不实现** saver；
验证场景复用 B10F1 的测试桩：

```python
# tests/runtime/test_interrupt_checkpoint.py（既有 · B10F1）
from tests.runtime.test_interrupt_checkpoint import StubCheckpointer
from freegraph.contracts import RunConfig
```

> ⚠️ 生产级 `MemorySaver` 属 **B14F1**（M3）；本 feature 只消费协议。

---

## 1. ★ `interrupt_before`（判据 A2 · SC-001）

```python
import operator

from freegraph.runtime import GraphSpec, NodeSpec, InterruptResult, run_graph
from freegraph.runtime.channel import BinaryOperatorAggregate

calls = {"review": 0}

def prepare(state):
    return {"log": ["prepare"]}

def review(state):
    calls["review"] += 1
    return {"log": ["review"]}

spec = GraphSpec(
    channels={"log": BinaryOperatorAggregate("log", list, operator.add)},
    nodes={
        "__start__": NodeSpec(subscribes=(), run=lambda s: {}),
        "prepare": NodeSpec(subscribes=(), run=prepare),
        "review": NodeSpec(subscribes=(), run=review),
    },
    edges={
        "__start__": ("prepare",),
        "prepare": ("review",),
    },
    interrupt_before=("review",),
)

stub = StubCheckpointer()
config = RunConfig(thread_id="t-before")

paused = run_graph(spec, checkpointer=stub, config=config)
assert isinstance(paused, InterruptResult)
assert calls["review"] == 0                       # 目标未执行
assert paused.interrupts == ()                    # 空载荷
assert paused.as_result_dict()["__interrupt__"] == ()
assert paused.state["log"] == ["prepare"]        # 只含 prepare 的写入

# 恢复（规范形态 input=None）
finished = run_graph(spec, None, checkpointer=stub, config=config)
assert calls["review"] == 1
assert finished.state["log"] == ["prepare", "review"]
```

**期望**：目标执行 **0** 次 → 挂起（空元组）→ 恢复后执行 **1** 次；同一断点不立即重挂。

---

## 2. ★ `interrupt_after`（判据 A2 · SC-002 · 含最后节点）

```python
import operator

calls = {"review": 0}

def review(state):
    calls["review"] += 1
    return {"log": ["review"]}

spec = GraphSpec(
    channels={"log": BinaryOperatorAggregate("log", list, operator.add)},
    nodes={
        "__start__": NodeSpec(subscribes=(), run=lambda s: {}),
        "review": NodeSpec(subscribes=(), run=review),
    },
    edges={"__start__": ("review",)},
    interrupt_after=("review",),
)

stub = StubCheckpointer()
config = RunConfig(thread_id="t-after")

paused = run_graph(spec, checkpointer=stub, config=config)
assert isinstance(paused, InterruptResult)
assert calls["review"] == 1                       # 已执行恰好一次
assert paused.interrupts == ()
assert paused.state["log"] == ["review"]         # 写入已合并

# 最后节点 after ⇒ next 为空；仍可恢复并完成
finished = run_graph(spec, None, checkpointer=stub, config=config)
assert calls["review"] == 1                       # 不重跑
assert finished.state["log"] == ["review"]
```

**期望**：目标执行 **1** 次 → 挂起 → 恢复后直接完成，不重跑。

---

## 3. ★ 递归上限（判据 A1 · SC-003 / SC-004）

```python
import pytest
from freegraph.contracts import GraphRecursionError
from freegraph.runtime import GraphSpec, NodeSpec, run_graph
from freegraph.runtime.channel import LastValue

def loop(state):
    return {"n": state.get("n", 0) + 1}

spec = GraphSpec(
    channels={"n": LastValue("n", int)},
    nodes={
        "__start__": NodeSpec(subscribes=(), run=lambda s: {}),
        "loop": NodeSpec(subscribes=(), run=loop),
    },
    edges={"__start__": ("loop",), "loop": ("loop",)},
)

with pytest.raises(GraphRecursionError) as caught:
    run_graph(spec, {"n": 0}, config={"recursion_limit": 3})

assert caught.value.recursion_limit == 3
assert "recursion limit" in str(caught.value).lower()

# 默认 10007（不在 25 步误报）
# ⇒ 专项断言见 tests/runtime/test_recursion_limit.py::test_default_is_10007

# 非法值：入口即失败
with pytest.raises(ValueError):
    run_graph(spec, {"n": 0}, config={"recursion_limit": 0})
with pytest.raises(TypeError):
    run_graph(spec, {"n": 0}, config={"recursion_limit": True})
with pytest.raises(TypeError):
    run_graph(spec, {"n": 0}, config={"recursion_limit": 1.5})
```

**期望**：`GraphRecursionError`（结构化属性 + 消息）；默认 10007；非法值入口失败。

---

## 4. 载体与优先级（SC-006）

```python
from freegraph.contracts import RunConfig

# dict（规范载体）
with pytest.raises(GraphRecursionError):
    run_graph(spec, {"n": 0}, config={"recursion_limit": 3})

# RunConfig（等价载体）
with pytest.raises(GraphRecursionError):
    run_graph(spec, {"n": 0}, config=RunConfig(recursion_limit=3))

# dict > max_steps
with pytest.raises(GraphRecursionError) as caught:
    run_graph(spec, {"n": 0}, config={"recursion_limit": 3}, max_steps=100)
assert caught.value.recursion_limit == 3

# RunConfig > max_steps（等价载体同样优先）
with pytest.raises(GraphRecursionError) as caught:
    run_graph(spec, {"n": 0}, config=RunConfig(recursion_limit=3), max_steps=100)
assert caught.value.recursion_limit == 3

# 未知键忽略（仍按 3 抛超限，而不是 TypeError）
try:
    run_graph(spec, {"n": 0}, config={"recursion_limit": 3, "unknown": 1})
except GraphRecursionError:
    pass
```

**期望**：dict / `RunConfig` 都生效（二者**互斥**，不同时提供）；dict 优先于 `max_steps`；
未知键不失败；**不存在** `recursion_limit=` 关键字。

---

## 5. ★ fan-out × 静态断点（SC-009 · **B11F1 的** D-7）

```python
import operator

from freegraph.contracts import Command, Send
from freegraph.runtime import GraphSpec, NodeSpec, InterruptResult, run_graph
from freegraph.runtime.channel import BinaryOperatorAggregate

seen = []

def fan(state):
    return Command(
        goto=[Send("worker", {"n": 1}), Send("worker", {"n": 2})],
    )

def worker(state):
    seen.append(dict(state))
    return {"log": [f"w{state['n']}"]}

def _spec(before=(), after=()):
    return GraphSpec(
        channels={"log": BinaryOperatorAggregate("log", list, operator.add)},
        nodes={
            "__start__": NodeSpec(subscribes=(), run=lambda s: {}),
            "fan": NodeSpec(subscribes=(), run=fan),
            "worker": NodeSpec(subscribes=(), run=worker),
        },
        edges={"__start__": ("fan",)},
        interrupt_before=before,
        interrupt_after=after,
    )

# before：N=2 个任务都保留、一个都不执行
stub = StubCheckpointer()
cfg = RunConfig(thread_id="t-fan-before")
paused = run_graph(_spec(before=("worker",)), checkpointer=stub, config=cfg)
assert isinstance(paused, InterruptResult)
assert seen == []
# 恢复：恰好两个任务，各自入参逐字不变
run_graph(_spec(before=("worker",)), None, checkpointer=stub, config=cfg)
assert [s["n"] for s in seen] == [1, 2]

# after：N=2 个任务各执行一次
seen.clear()
stub = StubCheckpointer()
cfg = RunConfig(thread_id="t-fan-after")
paused = run_graph(_spec(after=("worker",)), checkpointer=stub, config=cfg)
assert isinstance(paused, InterruptResult)
assert [s["n"] for s in seen] == [1, 2]
```

**期望**：before 0 次 / after 2 次；`__interrupt__ == ()`；**不**合并任务、**不**伪造载荷。

---

## 6. 优先级（SC-010）

```python
# 真异常 > 静态 after
def boom(state):
    raise RuntimeError("boom")

spec = GraphSpec(..., interrupt_after=("boom",))
with pytest.raises(RuntimeError):
    run_graph(spec, ...)

# 动态中断 > 静态 after
def ask(state):
    from freegraph.graph import interrupt
    interrupt("approve?")

# before 先于 after
spec = GraphSpec(..., interrupt_before=("review",), interrupt_after=("review",))
paused = run_graph(spec, ...)          # before
finished = run_graph(spec, None, ...)  # 执行后 after
```

**期望**：真异常原样抛出；动态中断载荷不是空元组；before 先挂起。

---

## 7. 低层入口拒绝（SC-015）

```python
from freegraph.runtime import run_super_step, run_super_steps, SchedulerState

spec = GraphSpec(..., interrupt_before=("review",))

with pytest.raises(ValueError, match="run_graph"):
    run_super_step(spec, SchedulerState())

with pytest.raises(ValueError, match="run_graph"):
    run_super_steps(spec)
```

**期望**：显式拒绝；`run_super_step` / `run_super_steps` 签名 / 返回类型不变。

---

## 8. `graph_core.py` 的软断言升级（A3 · SC-005 · EV-1）

```bash
grep -n "soft(False, \"recursion_limit" harness/demo/graph_core.py   # 期望：无输出
grep -n "GraphRecursionError" harness/demo/graph_core.py             # 期望：命中
```

- `soft(...)` → `check(...)`；异常判定收紧为 `GraphRecursionError`；
- `harness/demo/README.md` 的软断言清单删除 `recursion_limit` 一行；
- ⚠️ `graph_core.py` 的**端到端真跑**依赖 `compile()` / `invoke()`（B7F2 / B7F3 · M2）⇒
  M1 只验证「升级 + L2 等价硬测试」；端到端由 **B7F3** 收口（**EV-1**）。
- ⚠️ **M1 退出语义**：门面未就绪时 `graph_core.py` MUST 打印 `[环境未就绪]` 并以
  **退出码 2** 结束（不是 1）；退出码 1 仅表示真实硬断言失败。

---

## 9. 差分场景（SC-022）

```bash
.venv/bin/python -m pytest -q tests/differential
# 上游缺席 ⇒ skip；D-38…D-49 存在且判词齐备
```

---

## 10. 回归 / 覆盖

```bash
.venv/bin/python -m pytest -q
# 期望：既有 1203 + 新增 全绿；既有断言一条不删

.venv/bin/python -m coverage run -m pytest -q
.venv/bin/python -m coverage report --fail-under=100 \
  --include="src/freegraph/runtime/_static.py,src/freegraph/runtime/_recursion.py,src/freegraph/runtime/_fanout.py"
# superstep.py 的新增 / 变更行另按 T109 的 diff 覆盖率口径核对
```

**期望**：全绿；新增私有模块行 / 分支覆盖率 **100%**；`superstep.py` 的变更行按 diff 覆盖率核对。
