# Quickstart: B8F2 · `stream()` 多模式流式输出 + `StreamWriter`

**Feature**: `B8F2` · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**契约权威**: [contracts/stream-contract.md](./contracts/stream-contract.md)
**上游对照**: [contracts/upstream-parity.md](./contracts/upstream-parity.md)
**核实环境**: CPython **3.11.16** · `langgraph` **1.2.11** + `langchain-core` **1.7.6**
（取证于 2026-11-19）

> 本文件是**可照抄的验证手册**（闸口 **V1…V21**）—— 只写**怎么跑**与**期望看到什么**，
> **不含**实现代码。⚠️ **实施前这些闸口 MUST 为红**；期望输出是**交付后**的目标形态。
> ⚠️ 编号消歧：本手册的 `V1…V21` = 验收闸口；`data-model.md` §5 的 `VS-1…VS-11` =
> 校验规则；`stream-contract.md` §8 的 `IS-1…IS-25` = 不变量。

---

## 0. 环境与前置

| 项 | 要求 |
|---|---|
| Python | **≥ 3.11**（最低档 3.11 跑全量） |
| venv | 仓库根 `.venv` |
| 开发依赖组 | `dev`（pytest）· `differential`（上游差分 · 缺席即 skip） |
| 运行时依赖 | **零第三方**（`dependencies = []`） |

```bash
# 自检
uv run --no-project --python .venv python -c "import sys, importlib.metadata as m; \
print(sys.version.split()[0], m.version('langgraph'))"
```

**期望**：`3.11.16 1.2.11`（上游缺席时差分闸口 skip）。

```bash
# 全量
uv run --no-project --python .venv python -m pytest tests/ -ra
# 差分
uv run --no-project --python .venv python -m pytest tests/differential/ -ra
```

---

## V1 · 七种 mode 全部被接受

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END
class S(dict): pass
def a(s): return {"x": s.get("x", 0) + 1}
g = StateGraph(S); g.add_node("a", a); g.add_edge(START, "a"); g.add_edge("a", END)
app = g.compile()
for mode in ["values","updates","checkpoints","tasks","debug","messages","custom"]:
    evs = list(app.stream({"x": 0}, stream_mode=mode))
    print(mode, len(evs))
PY
```

**期望**：七行均不抛；`checkpoints` / `messages` 为 `0`；`custom` 本例也为 `0`（该节点未调用 `writer`，见 V4）；`values` / `updates` / `tasks` / `debug` 为 `> 0`（空图例外）。
**对应**：SC-001 / SC-008 / SC-009 / SC-012 · A1。

> **默认档**：`app.stream({"x": 0})`（省略 `stream_mode`）与
> `app.stream({"x": 0}, stream_mode=None)` 等价，按 **`updates`** 产出（上游同款 · E-18）。

---

## V2 · `values` 与 `invoke` 终态一致

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END
class S(dict): pass
def a(s): return {"x": s.get("x", 0) + 1}
def b(s): return {"x": s.get("x", 0) + 1}
g = StateGraph(S); g.add_node("a", a); g.add_node("b", b)
g.add_edge(START, "a"); g.add_edge("a", "b"); g.add_edge("b", END)
app = g.compile()
evs = list(app.stream({"x": 0}, stream_mode="values"))
final = app.invoke({"x": 0})
print(len(evs), evs[-1]["payload"] == final, evs[-1]["payload"])
PY
```

**期望**：`3 True {'x': 2}`（初始 + 两步；最后一条 == `invoke`）。
**对应**：SC-002 · A2。

---

## V3 · `updates` 可合并回终态

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END
class S(dict): pass
def a(s): return {"x": s.get("x", 0) + 1}
def b(s): return {"x": s.get("x", 0) + 1}
g = StateGraph(S); g.add_node("a", a); g.add_node("b", b)
g.add_edge(START, "a"); g.add_edge("a", "b"); g.add_edge("b", END)
app = g.compile()
merged = {}
for ev in app.stream({"x": 0}, stream_mode="updates"):
    for node, upd in ev["payload"].items():
        merged.update(upd)   # 本例只有覆盖型通道
print(merged, app.invoke({"x": 0}), merged == app.invoke({"x": 0}))
PY
```

**期望**：`{'x': 2} {'x': 2} True`。
**注意**：归约型通道 MUST 按通道归约合并（不能用 `dict.update` 冒充）。
**对应**：SC-003 · A3。

---

## V4 · `StreamWriter` → `custom`

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END, get_stream_writer
class S(dict): pass
def a(s):
    get_stream_writer()({"msg": "retrieving"})
    return {"x": 1}
g = StateGraph(S); g.add_node("a", a); g.add_edge(START, "a"); g.add_edge("a", END)
app = g.compile()
print([e["payload"] for e in app.stream({}, stream_mode="custom")])
PY
```

**期望**：`[{'msg': 'retrieving'}]`（原样）。
**注意**：`custom` 是**轮末批量**（每轮 L2 单轮入口结束后按 TaskId 序产出 · P-23 / X-6），
不是逐写即时；本闸口只判载荷与顺序。
**对应**：SC-004。

---

## V5 · `tasks` / `debug`

```bash
uv run --no-project --python .venv python - <<'PY'
from datetime import datetime, timedelta
from freegraph.graph import StateGraph, START, END
from freegraph.contracts import PregelTask
class S(dict): pass
def a(s): return {"x": 1}
def b(s): return {"x": 2}
g = StateGraph(S); g.add_node("a", a); g.add_node("b", b)
g.add_edge(START, "a"); g.add_edge("a", "b"); g.add_edge("b", END)
app = g.compile()
ts = [e["payload"] for e in app.stream({}, stream_mode="tasks")]
dbg = [e["payload"] for e in app.stream({}, stream_mode="debug")]
print(len(ts), all(isinstance(t, PregelTask) for t in ts))
print([set(d) for d in dbg], [d["type"] for d in dbg])
print([datetime.fromisoformat(d["timestamp"]).utcoffset() == timedelta(0) for d in dbg])
print([d["step"] for d in dbg])
PY
```

**期望**：`2 True`；debug 键集 `{'step','timestamp','type','payload'}`，`type` 全为 `task_result`；
`datetime` 解析结果全为 `True`（UTC）；`step` 为 1 起的轮次序号（同轮相同）。
**对应**：SC-006 / SC-007。

---

## V6 · 事件信封与 id

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END
class S(dict): pass
def a(s): return {"x": 1}
g = StateGraph(S); g.add_node("a", a); g.add_edge(START, "a"); g.add_edge("a", END)
app = g.compile()
evs = list(app.stream({}, stream_mode="values", config={"configurable": {"thread_id": "t-1"}}))
print([set(e) for e in evs])
print(len({e["run_id"] for e in evs}), {e["thread_id"] for e in evs})
PY
```

**期望**：每条键集 `{'stream_mode','payload','run_id','thread_id'}`；`run_id` 集合基数 `1`；
`thread_id == {'t-1'}`。
**对应**：SC-010 / SC-011。

---

## V7 · 多 mode 与固定顺序

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END
class S(dict): pass
def a(s): return {"x": 1}
g = StateGraph(S); g.add_node("a", a); g.add_edge(START, "a"); g.add_edge("a", END)
app = g.compile()
evs = list(app.stream({}, stream_mode=["values", "updates", "tasks"]))
print([e["stream_mode"] for e in evs])
PY
```

**期望**：`['values', 'updates', 'tasks', 'values']`（初始 + 轮内 `updates → tasks → values`）。
**对应**：SC-012。

---

## V8 · 非法 mode / 空序列

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END
class S(dict): pass
def a(s): return {}
g = StateGraph(S); g.add_node("a", a); g.add_edge(START, "a"); g.add_edge("a", END)
app = g.compile()
for bad in ["bogus", [], 123]:
    try:
        app.stream({}, stream_mode=bad)
        print("NO ERROR", bad)
    except Exception as exc:
        print(type(exc).__name__, str(exc)[:80])
PY
```

**期望**：`bogus` ⇒ `ValueError`（列七种合法值）；`[]` ⇒ `ValueError`；`123` ⇒ `TypeError`；
`None` **不抛异常**并按 `updates` 产出。
**对应**：SC-001。

---

## V9 · 惰性与提前停止

```bash
uv run --no-project --python .venv python - <<'PY'
import threading, time
from freegraph.graph import StateGraph, START, END
class S(dict): pass
calls = {"n": 0}
def a(s):
    calls["n"] += 1
    return {"x": 1}
g = StateGraph(S); g.add_node("a", a); g.add_edge(START, "a"); g.add_edge("a", END)
app = g.compile()
it = app.stream({}, stream_mode="values")
print("before", calls["n"])
next(it); it.close()
time.sleep(0.05)
print("after", calls["n"], [t.name for t in threading.enumerate() if t.name.startswith("freegraph-node")])
PY
```

**期望**：`before 0`；`after 0 []`（首次 `next()` 只产出初始 `values`，节点尚未执行；惰性 + 零悬挂线程）。若需观察节点执行，可在 `close()` 前再调用一次 `next()`。
**对应**：SC-013 / SC-016。

---

## V10 · 中断

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END, interrupt
class S(dict): pass
def a(s):
    interrupt("approve?")
    return {"x": 1}
g = StateGraph(S); g.add_node("a", a); g.add_edge(START, "a"); g.add_edge("a", END)
app = g.compile()
for mode in ["values", "updates", "tasks", "debug"]:
    evs = list(app.stream({}, stream_mode=mode))
    print(mode, len(evs), evs[-1])
PY
```

**期望**：四条流都不抛；`values` / `updates` 收尾含 `__interrupt__`；`tasks` / `debug` 为被中断
task 产出一条（`interrupts` 非空）。
**注意**：v1 需要 checkpointer 才能真实挂起/恢复；本闸口只判「流式收尾」。静态断点（`interrupt_before` / `interrupt_after`）不在 stream v1 支持范围：首次迭代应抛 `ValueError`（V-26 口径）。
**对应**：SC-017。

---

## V11 · 失败先 flush custom，再重抛

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END, get_stream_writer
class S(dict): pass
def a(s):
    get_stream_writer()({"m": "before-fail"})
    raise RuntimeError("boom")
g = StateGraph(S); g.add_node("a", a); g.add_edge(START, "a"); g.add_edge("a", END)
app = g.compile()
try:
    for ev in app.stream({}, stream_mode="custom"):
        print("EVENT", ev["payload"])
except Exception as exc:
    print("RAISED", type(exc).__name__, exc)
PY
```

**期望**：先 `EVENT {'m': 'before-fail'}`，再 `RAISED RuntimeError boom`。
**对应**：SC-013。

---

## V12 · `checkpoints` / `messages` 边界

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END
class S(dict): pass
def a(s): return {"x": 1}
g = StateGraph(S); g.add_node("a", a); g.add_edge(START, "a"); g.add_edge("a", END)
app = g.compile()
print(len(list(app.stream({}, stream_mode="checkpoints"))))
print(len(list(app.stream({}, stream_mode="messages"))))
PY
```

**期望**：`0` / `0`（不抛）。
**对应**：SC-008 / SC-009。

---

## V13 · 公开面与 L2 签名

```bash
uv run --no-project --python .venv python - <<'PY'
import inspect
from freegraph import graph as facade, contracts, runtime
print(len(facade.__all__), len(contracts.__all__), len(runtime.__all__))
print("stream", inspect.signature(runtime.run_super_step))
print("stream_mode" in dir(runtime) or "ok")
PY
```

**期望**：`8 22 23`；`run_super_step` 签名与 B7F1 契约逐字一致。
**对应**：SC-014 / SC-018。

---

## V14 · 差分（上游缺席即 skip）

```bash
uv run --no-project --python .venv python -m pytest tests/differential/ -q
```

**期望**：D-121…D-136 全绿；判词分布 SAME **10** / DIFF **4** / STRICTER **2**。
**对应**：SC-015。

---

## V15 · 一键验收脚本

```bash
uv run --no-project --python .venv python harness/verification/B8F2/acceptance.py
```

**期望**：退出码 `0`，末行 `B8F2 acceptance: PASS`。
**对应**：SC-019。

```bash
uv run --no-project --python .venv python -m pytest tests/runtime/test_stream_acceptance.py -q
```

**期望**：B8F2 的那条用例 PASS（脚本与实现漂移 ⇒ 立刻红）。

---

## V16 · 零依赖 / 零出站 / 零环境变量

```bash
uv run --no-project --python .venv python -m pytest tests/runtime/test_parse_contract.py \
  tests/gates -q
```

**期望**：依赖闭包为空、无 `langchain*` / `langgraph*` / `langsmith`、零环境变量读取。
**对应**：SC-005。

---

## V17 · 破冻结面回溯修订

```bash
uv run --no-project --python .venv python - <<'PY'
from pathlib import Path
checks = [
    ("specs/b7f1-superstep-loop/contracts/superstep-contract.md", "tasks"),
    ("specs/b12f1-concurrency-errors/spec.md", "B8F2"),
    ("specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md", "copy_context"),
    ("specs/b2f2-public-api-facade/contracts/facade-api.md", "get_stream_writer"),
    ("specs/b2f1-contracts-protocols/contracts/public-api.md", "StreamWriter"),
    ("specs/b8f1-conditional-edges-fresh-read/research.md", "DR-4"),
    ("harness/verification/B8F2/manual-verification.md", "追认"),
]
for path, needle in checks:
    text = Path(path).read_text()
    print(path, needle in text)
PY
```

**期望**：七条均为 `True`（原描述保留 + 注记在位 + B8F1 DR-4 关闭注记 + 追认文字在位）。
**对应**：SC-020 / SC-021。

---

## V18 · 关键字注入（参数名 `writer`）

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END
class S(dict): pass
def a(s, writer):
    writer({"via": "writer"})
    return {"x": 1}
g = StateGraph(S); g.add_node("a", a); g.add_edge(START, "a"); g.add_edge("a", END)
app = g.compile()
print([e["payload"] for e in app.stream({}, stream_mode="custom")])
print(app.invoke({}))
PY
```

**期望**：`[{'via': 'writer'}]`；`invoke` 正常完成（注入 no-op）。
**注意**：上游参数名是 **`writer`**；`def node(state, stream_writer)` **不会**被注入。
**对应**：SC-021。

---

## V19 · `stream(None)` = 无输入写入

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END
class S(dict): pass
def a(s): return {"x": 1}
g = StateGraph(S); g.add_node("a", a); g.add_edge(START, "a"); g.add_edge("a", END)
app = g.compile()
print(list(app.stream(None, stream_mode="values")))
PY
```

**期望**：图照常执行（静态入口触发）；初始状态为 schema 空值；不抛异常。
**对应**：FR-023 / FR-028。

---

## V20 · 双参路由收到原始 `config`

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END
class S(dict): pass
seen = []
def route(state, config):
    seen.append(config)
    return "b"
def a(s): return {"x": 1}
def b(s): return {"x": 2}
g = StateGraph(S); g.add_node("a", a); g.add_node("b", b)
g.add_edge(START, "a"); g.add_conditional_edges("a", route, ["b"]); g.add_edge("b", END)
app = g.compile()
cfg = {"configurable": {"thread_id": "t-1"}, "recursion_limit": 9}
list(app.stream({}, config=cfg, stream_mode="updates"))
print(seen)
PY
```

**期望**：`seen == [cfg]`（第二参与用户交给 `stream()` 的**原始映射逐字相等**；不是 `None`，
也不是被翻译后的 `RunConfig`）。**对应**：FR-024 / SC-023。

---

## V21 · 递归上限的精确边界

```bash
uv run --no-project --python .venv python - <<'PY'
from freegraph.graph import StateGraph, START, END
class S(dict): pass
def a(s): return {"x": s.get("x", 0) + 1}
g = StateGraph(S); g.add_node("a", a); g.add_edge(START, "a"); g.add_edge("a", "a")
app = g.compile()
try:
    list(app.stream({}, config={"recursion_limit": 3}, stream_mode="values"))
    print("NO ERROR")
except Exception as exc:
    print(type(exc).__name__, getattr(exc, "recursion_limit", None), getattr(exc, "current_step", None))
PY
```

**期望**：`GraphRecursionError 3 3`（**执行前**抛，不跑第 4 轮）；另用**恰好收敛于上限**的图
（如 3 步线性图 + `recursion_limit=3`）验证**不抛**。**对应**：FR-037 / SC-022。

---

## 失败排查

| 现象 | 可能原因 | 处置 |
|---|---|---|
| `facade.__all__` == 7 | `get_stream_writer` 未转出 | 检查 `graph.py` 的 import 与 `__all__` |
| `contracts.__all__` == 21 | `StreamWriter` 未导出 | 检查 `contracts/__init__.py` |
| `SuperStepResult` 仍 4 字段 | `tasks` 未追加 | 检查 `superstep.py` 与 T-1 |
| `tasks` 中断时缺失 | round capture 未接线 | 检查 `_run_round` 阶段 ⑥ |
| `custom` 顺序抖动 | sink 未按 TaskId 排序 | 检查 `_stream_context.py` |
| 双参路由收到 `None` | `_stream_tick` 未透传 `route_config` | 检查 L3 主循环是否把原始 `config` 传给 `_stream_tick` |
| 递归上限多跑一轮 / 误抛 | `_stream_tick` 未在执行前判「触发集非空」 | 检查 `_stream_tick` 是否复用 `_determine_triggers` |
| 上游差分 skip | 未装 `differential` 组 | `uv pip install --group differential` |
| 快照红 | 未更新 API 快照 | `pytest tests/facade/test_api_snapshot.py --update-api-snapshot` |
