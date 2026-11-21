# Quickstart / Validation Guide: B19F1

**Feature**: B19F1 · **Date**: 2026-11-21 · **Spec**: [spec.md](./spec.md)
**Contracts**: [trace-sink](./contracts/trace-sink-contract.md) · [trace-record](./contracts/trace-record-contract.md) · [upstream-parity](./contracts/upstream-parity.md)

> 本文件是可执行的**验收 / 验证指南**，不是实现清单。所有片段只 import
> `freegraph` 与标准库，不需要任何 SaaS 账号 / API key / 网络。

---

## 0. 前提

- Python **3.11+**；仓库根已安装开发依赖（`.venv`）。
- **零出站**：验证前清空 `LANGSMITH_*` / `LANGCHAIN_*` / `OTEL_*`。
- 基线（2026-11-21 实跑）：`1863 passed, 6 skipped`。

```bash
cd /path/to/freegraph
unset LANGSMITH_API_KEY LANGSMITH_TRACING LANGCHAIN_TRACING_V2
```

---

## 1. 最小验证：注入即推送（US1 / SC-003）

```python
from typing import TypedDict
from freegraph.graph import StateGraph, START, END, RunConfig

class S(TypedDict, total=False):
    x: int

class Sink:
    def __init__(self):
        self.events, self.records = [], []
    def on_span_start(self, span):
        self.events.append(("start", span))
    def on_span_end(self, span):
        self.events.append(("end", span))
    # current_span 可选；不实现也不影响注入
    def on_trace_record(self, record):
        self.records.append(record)

def a(state): return {"x": state.get("x", 0) + 1}
def b(state): return {"x": state.get("x", 0) + 1}

sink = Sink()
g = StateGraph(S)
g.add_node("a", a); g.add_node("b", b)
g.add_edge(START, "a"); g.add_edge("a", "b"); g.add_edge("b", END)
app = g.compile(tracer=sink)

out = app.invoke({"x": 0}, config=RunConfig(thread_id="t-1"))

assert out["x"] == 2
starts = [s for kind, s in sink.events if kind == "start"]
ends   = [s for kind, s in sink.events if kind == "end"]
assert len(starts) == len(ends) == 2
assert {s.id for s in starts} == {s.id for s in ends}
assert all(s.run_id and s.thread_id == "t-1" for s in starts + ends)
assert len(sink.records) == 2
```

**预期**：无异常；每节点 1 对 `start` / `end`；`run_id` 非空、`thread_id == "t-1"`。

---

## 2. 嵌套 + `current_span()`（US2 / SC-001 / SC-004）

```python
from freegraph.observability import current_span, invoke_model, invoke_tool

class Model:
    model_name = "fake-model"
    def invoke(self, value): return f"<{value}>"

class Tool:
    name = "fake-tool"
    description = "fake"
    def invoke(self, value): return f"[{value}]"

seen = []
def node(state):
    outer = current_span()
    seen.append(("outer", outer))
    invoke_model(Model(), "hi")
    invoke_tool(Tool(), "hi")
    return {"x": state.get("x", 0) + 1}
```

**断言**：

- 每个模型 / 工具 span 的 `parent` == 所在节点 span 的 `id`；
- 在节点内 `current_span()` 返回**该节点 span**（不是 `None`）；
- 内层调用结束后 `current_span()` 恢复为节点 span；
- 离开节点后 `current_span()` 为 `None`，且不抛异常。

---

## 3. 默认关闭 / 零副作用（US3 / SC-002 / SC-005）

```python
app_no = g.compile()                 # 不传 tracer
out = app_no.invoke({"x": 0})
assert out["x"] == 2

# 显式 None 与不传等价
app_none = g.compile(tracer=None)
assert app_none.invoke({"x": 0})["x"] == 2
```

**断言**：

- 不注入（或 `tracer=None`）**且无任何外层 tracer** ⇒ `on_span_start` / `on_span_end`
  调用数 == 0，`Span` / `SpanProducer` 构造数 == 0，span 专用 `run_id` 绑定数 == 0；
- 设置 `LANGSMITH_TRACING=true` / `LANGCHAIN_TRACING_V2=true` 后行为不变；
- `import freegraph` 的 `sys.modules` 不含 `freegraph.observability` /
  `opentelemetry` / `langchain*` / `langsmith`；⚠️ **该检查必须在全新子进程 / 新进程执行**
  （§2 已导入 `freegraph.observability`，同进程会污染结果）；
- 基础安装依赖闭包仍为空集。

---

## 4. 异常路径仍成对（SC-003 / SC-010）

```python
def boom(state):
    raise RuntimeError("boom")

g2 = StateGraph(S); g2.add_node("boom", boom)
g2.add_edge(START, "boom"); g2.add_edge("boom", END)
app2 = g2.compile(tracer=Sink())

try:
    app2.invoke({"x": 0})
except RuntimeError as exc:
    assert str(exc) == "boom"
else:
    raise AssertionError("expected RuntimeError")
```

**断言**：`start` / `end` 仍成对（end 的 `end_time` 非空）；异常**原对象 / 类型 / 消息**
不变；record 的 `error` 是该异常对象。

---

## 5. 补充记录：触发源 / 并发组 / 屏障组（SC-008 / SC-009 / SC-014 / SC-015）

```python
import json

sink = Sink()
# 静态边 + Command.goto + Send fan-out 混合图（见 tests/runtime 的夹具）
app = build_mixed_graph().compile(tracer=sink)
app.invoke({"x": 0})

for rec in sink.records:
    assert rec.span_id and rec.task_id and rec.run_id
    assert isinstance(rec.superstep, int)
    assert rec.triggers                      # 至少一个触发源
    assert rec.concurrency_group             # 同轮任务集
    assert rec.barrier_groups == rec.barrier_groups  # tuple of tuples / ()
    assert json.dumps(rec.to_jsonable())     # B20 落盘视图
    # output_state = 节点原始返回值（node.run raw return）；
    # 不是归一后的 writes / gotos / fanout
```

**断言**：

- 三类触发源都出现（静态边 / `goto` / fan-out）；不出现「只有 goto」或「只有静态边」；
- 同一 super-step 的记录 `concurrency_group` 相同；标准任务按节点名序、fan-out 按 TaskId 序；
- 多源汇合（`[a, b] → c`）的 `barrier_groups` 含 `("a", "b")`；
- `record 数 == 节点 span 数`；事件顺序 `start → record → end`。

---

## 6. 流式通道与 span 同源同 id（SC-007）

```python
sink = Sink()
app = g.compile(tracer=sink)
events = list(app.stream({"x": 0}, config=RunConfig(thread_id="t-1"),
                         stream_mode="updates"))

event_ids = {(e["run_id"], e["thread_id"]) for e in events}
span_ids  = {(s.run_id, s.thread_id) for _, s in sink.events}
assert event_ids == span_ids
assert len(sink.records) == 2          # stream() 也产逐节点 record（与 invoke 同款）
```

**断言**：事件与 span 的 `(run_id, thread_id)` 逐字相同；`stream()` 信封中 trace 字段数 == 0；
不注入 tracer 也能 `stream()`；不 `stream()` 也能 `invoke()` 产出 span。

---

## 7. 中断 / 取消对齐（SC-017）

```python
from freegraph.graph import interrupt

def gate(state):
    interrupt({"need": "approval"})
    return {"x": state.get("x", 0) + 1}
```

**断言**：`record 数 == 节点 span 数`；中断 record 的 `error` 是**原 `GraphInterrupt` 对象**；
节点自身抛 `CancelledError` 等取消异常时有 record（`error` = 原取消 / 异常）；运行期只取消排队未启动任务（已启动任务跑完，不取消）；从未启动的取消任务无 span / record。

> 恢复（`Command(resume=...)`）挂 checkpointer（B14F1）；本 feature 只验证「中断轮」的记录对齐。

---

## 8. 跨 compiled graph 嵌套（FR-021 / SC-016）

```python
inner_no = inner_graph.compile()              # 未注入
inner_yes = inner_graph.compile(tracer=Sink())
outer = outer_graph.compile(tracer=Sink())
```

**断言**：

- 外层注入、内层未注入 ⇒ 内层 span 数 == 0、record 数 == 0（**不隐式继承**）；
- 内层注入 ⇒ 内层 `run_id` 与外层**不同**，内层顶层节点 span 的 `parent is None`；
- 跨图父子串线数 == 0。

---

## 9. 命令

```bash
# 定向
.venv/bin/python -m pytest tests/observability -q
.venv/bin/python -m pytest tests/runtime -q
.venv/bin/python -m pytest tests/contracts -q

# 差分（上游缺席即 skip）
.venv/bin/python -m pytest tests/differential/test_b19f1_trace_access_parity.py -q

# 全量回归（实施前后各跑一次）
.venv/bin/python -m pytest -q --tb=no
```

**预期**：定向全绿；差分：上游可用时 D-301…D-310 全绿（上游不可用则对应项 skip）；
全量回归在基线 `1863 passed, 6 skipped` 上**只增不减**（新测试计入）。

---

## 10. 人工验收记录

- 路径：`harness/verification/B19F1/manual-verification.md`
- 必含：环境、步骤、实际输出、结论、遗留问题；
- fake 轮：本地真实 `Sink` / `Model` / `Tool` 对象；
- 真实轮：本地真实 sink 实现（无需外部模型 provider）；
- 零出站证据：socket 监测夹具（只观测、不阻断）⇒ 框架出站 == 0；
- **R-1/R-2/R-3 一次性追认文字（确认人 + 日期）**：L3 → L5 / L5 → L2 `_span_hook`（不读 `_stream_context`）/ B18F1 断言拆分；
- **B8F2 R-6 已收窄**：L2 读取 stream id，B19F1 从节点 span 继承；
- **质量门禁 5 偏离登记（确认人 + 日期）**：fake 轮 + 本地真实 sink 轮；真实模型轮由 B21F1 承接。
