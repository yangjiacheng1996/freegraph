# Quickstart —— B18F1 · Span 生产验证指南

**Feature**: B18F1 · Span 数据类生产（节点 / 工具 / 模型三级 span）
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Data Model**: [data-model.md](./data-model.md)
**Date**: 2026-11-20

> 本文件只提供**可执行验证步骤**；实现细节在 `tasks.md` / 源码中。
> 所有命令在仓库根目录执行；使用 `.venv`。

---

## 0. 前置条件

```bash
# Python 3.11+
.venv/bin/python -V

# 基线：既有测试全绿（2026-11-20 实测 1778 passed, 6 skipped）
.venv/bin/python -m pytest -q --tb=no
```

**期望**：`1778 passed, 6 skipped`（允许环境导致的既有 skip；不应出现新的 fail）。

---

## 1. 运行本 feature 的测试

```bash
# 单元 / 集成（按 tasks 落地后的文件名为准）
.venv/bin/python -m pytest -q \
  tests/observability/ \
  tests/runtime/test_node_spans.py \
  tests/runtime/test_concurrency_spans.py \
  tests/runtime/test_span_ids.py \
  tests/observability/test_span_attributes.py

# 差分（上游缺席即 skip）
.venv/bin/python -m pytest -q tests/differential/test_b18f1_span_parity.py
```

**期望**：

- 节点 / 模型 / 工具三级 span 用例全绿；
- 父链、异常成对、并发不串父、`run_id` 同源用例全绿；
- 属性允许清单 / JSON 可序列化用例全绿；
- D-201…D-208 按判词通过（上游缺席时 skip，不判失败）。

---

## 2. 手工冒烟：三层 span + 父子关系

> 目的：用**最小**脚本证明「节点 span 自动产生；`invoke_model` / `invoke_tool` 产生子 span；
> 父子关系正确；耗时严格 > 0」。

```python
from typing import TypedDict

from freegraph.graph import StateGraph, START, END
from freegraph.observability import invoke_model, invoke_tool, SpanProducer
from freegraph.runtime._span_hook import bind_span_tracer
from freegraph.observability._producer import bind_tracer

class RecordingReceiver:
    def __init__(self):
        self.started = []
        self.ended = []
    def on_span_start(self, span):
        self.started.append(span)
    def on_span_end(self, span):
        self.ended.append(span)

class FakeModel:
    model_name = "demo-model"
    def invoke(self, _input):
        return "ok"

class FakeTool:
    name = "multiply"
    description = "Multiply two numbers"
    def invoke(self, args):
        return args["a"] * args["b"]

class S(TypedDict):
    result: int

def node(state):
    model_result = invoke_model(FakeModel(), "hello")
    tool_result = invoke_tool(FakeTool(), {"a": 3, "b": 4})
    return {"result": tool_result}

g = StateGraph(S)
g.add_node("demo_node", node)
g.add_edge(START, "demo_node")
g.add_edge("demo_node", END)
app = g.compile()

receiver = RecordingReceiver()
producer = SpanProducer(receiver)

with bind_span_tracer(producer), bind_tracer(producer):
    app.invoke({})

# 期望：1 个节点 span + 1 个模型 span + 1 个工具 span
assert len(receiver.started) == 3
assert len(receiver.ended) == 3
by_name = {s.name: s for s in receiver.started}
node_span = by_name["demo_node"]
model_span = next(s for s in receiver.started if s.attributes.get("gen_ai.operation.name") == "chat")
tool_span = next(s for s in receiver.started if s.attributes.get("gen_ai.operation.name") == "execute_tool")
assert model_span.parent == node_span.id
assert tool_span.parent == node_span.id
assert tool_span.attributes["gen_ai.tool.name"] == "multiply"
assert all(s.end_time and s.end_time > s.start_time for s in receiver.ended)
```

**期望**：

- `receiver.started` / `receiver.ended` 各 3 条；
- 模型 / 工具 span 的 `parent` == 节点 span 的 `id`；
- 工具 span 的 `name == "execute_tool multiply"`；
- 所有结束 span 的 `end_time > start_time`；
- `Span.context == {}`；节点 span 的 `attributes == {}`。

> 说明：本脚本的 **tracer = `SpanProducer`**，**receiver = `RecordingReceiver`**；`bind_tracer` 是 L5 私有绑定（测试 / B19F1 用）。B18F1 **不**提供公开注入 API；B19F1 的公开注入 MUST 构造 `SpanProducer` 并同时绑定 L2 + L5（R-4）。实际导入路径以实现后的 `__init__` 导出为准。

---

## 3. 手工冒烟：未绑定 tracer ⇒ 零开销

```python
from typing import TypedDict

from freegraph.graph import StateGraph, START, END

class S(TypedDict):
    x: int

# 没有绑定任何 tracer，直接跑图
g = StateGraph(S)
g.add_node("n", lambda s: {"x": s.get("x", 0) + 1})
g.add_edge(START, "n")
g.add_edge("n", END)
app = g.compile()
assert app.invoke({})["x"] == 1
```

**期望**：

- 图正常完成；
- 真实测试用计数夹具断言 `Span` 构造数 == 0、接收端回调数 == 0；
- 不生成 **span 专用** `run_id`（`stream()` 既有事件 `run_id` 不属 span 生产）；不读环境变量。

**环境变量仍不改变行为**：

```bash
LANGSMITH_TRACING=true LANGCHAIN_TRACING_V2=true \
  .venv/bin/python -m pytest -q tests/observability/test_zero_overhead.py
```

---

## 4. 手工冒烟：形状错配 / 节点外 / awaitable

```python
from freegraph.observability import invoke_model, invoke_tool

class ToolLike:
    name = "t"
    description = "d"
    def invoke(self, args): return args

class ModelLike:
    def invoke(self, x): return x

# 1) 工具形状传给 invoke_model ⇒ TypeError
try:
    invoke_model(ToolLike(), {})
except TypeError:
    pass
else:
    raise AssertionError("expected TypeError")

# 2) 模型形状传给 invoke_tool ⇒ TypeError
try:
    invoke_tool(ModelLike(), {})
except TypeError:
    pass
else:
    raise AssertionError("expected TypeError")

# 3) 节点外调用：形状正确 ⇒ 直接调用、不产生 span
assert invoke_model(ModelLike(), 7) == 7

# 4) awaitable ⇒ TypeError
class AsyncLike:
    def invoke(self, x):
        async def _coro(): return x
        return _coro()

try:
    invoke_model(AsyncLike(), 1)
except TypeError:
    pass
else:
    raise AssertionError("expected TypeError")
```

**期望**：4 个用例均符合 spec Q13 / Q14 / Q16；节点外调用不产生 span。

---

## 5. 手工冒烟：环境变量 / 依赖 / 惰性

```bash
# 5.1 依赖闭包（基础安装）
.venv/bin/python - <<'PY'
import importlib.metadata as m
reqs = m.requires("freegraph") or []
assert reqs == [], reqs
print("dependency closure: empty")
PY

# 5.2 import freegraph 不加载 L5 / L2 hook
.venv/bin/python - <<'PY'
import sys
import freegraph
bad = [n for n in sys.modules if n.startswith("freegraph.observability") or n.endswith("runtime._span_hook")]
assert not bad, bad
print("lazy import: ok")
PY

# 5.3 禁止依赖的 import 计数
rg -n "opentelemetry|langchain|langsmith" src/freegraph/observability src/freegraph/runtime/_span_hook.py || true
```

**期望**：依赖闭包为空；`import freegraph` 后无 L5 / hook 模块；源码无禁用 import。

---

## 6. 手工冒烟：stream 与 span 共用 id

```python
from typing import TypedDict

from freegraph.graph import StateGraph, START, END
from freegraph.observability import SpanProducer
from freegraph.runtime._span_hook import bind_span_tracer
from freegraph.observability._producer import bind_tracer

class Rec:
    def __init__(self): self.spans = []
    def on_span_start(self, s): self.spans.append(s)
    def on_span_end(self, s): pass

class S(TypedDict):
    x: int

g = StateGraph(S)
g.add_node("n", lambda s: {"x": 1})
g.add_edge(START, "n")
g.add_edge("n", END)
app = g.compile()

rec = Rec()
producer = SpanProducer(rec)
with bind_span_tracer(producer), bind_tracer(producer):
    events = list(app.stream({}, stream_mode="values"))

event_run_id = events[0]["run_id"]
event_thread_id = events[0]["thread_id"]
assert all(s.run_id == event_run_id for s in rec.spans)
assert all(s.thread_id == event_thread_id for s in rec.spans)
```

**期望**：同一次 `stream()` 的所有 span 与事件共享 `run_id` / `thread_id`。

---

## 6.1 原则 IV 载体（stream 路径）

节点 span 只承担节点名 / 耗时；输入状态 / 输出状态 / 错误由既有 `stream()` 事件承担：

```python
events = list(app.stream({}, stream_mode=["values", "updates", "tasks"]))
# 正常节点：
#   - values 事件给出 step 前 / 后的状态（输入 / 输出状态）
#   - updates / tasks 事件给出写入与 PregelTask.result（输出）
# 失败节点：
#   - 错误由原样抛出的异常给出（并发其它失败见 add_note）
#   - tasks / PregelTask.error 仅在非抛出快照 / 中断路径可见，不作为失败路径载体
# `invoke()` 路径的逐节点输入 / 输出 / 错误由 B19F1 / B20 承接（spec D-6）；
# B19F1/B20 的 spec MUST 落成该承接（目标提示词已接线）。
```

**期望**：节点 span 的 `attributes == {}`；原则 IV 的输入 / 输出 / 错误由上述事件 / `PregelTask`
还原，而不是由节点 span 属性携带。`invoke()` 路径的逐节点记录不在 B18F1 内闭合，由 B19F1/B20 明确承接。

---

## 7. 人工验证记录

先跑一键验收脚本，再完成 §1–§6：

```bash
.venv/bin/python harness/verification/B18F1/acceptance.py
```

期望：末行 `B18F1 acceptance: PASS`。随后将实测输出写入：

```text
harness/verification/B18F1/manual-verification.md
```

必须包含：

- 验证环境（Python / `langgraph` / 日期）；
- fake 轮与真实轮的**实际输出**（非「符合预期」）；
- 零出站证据（框架出站 == 0）；
- 结论 / 遗留问题；
- 若真实模型轮无法执行：按宪法 v1.6.0 登记偏离 + 发起者追认（plan R-3）。

---

## 8. 失败排查

| 现象 | 检查 |
|---|---|
| 只看到节点 span，没有模型 / 工具 span | 是否用 `invoke_model` / `invoke_tool` 调用；是否同时绑定了 L2 hook 与 L5 tracer |
| 模型 / 工具 span 的 `parent` 为 `None` | 是否在节点执行期间调用；节点 span 是否已开始 |
| `run_id` 为空 | `invoke` 路径是否在 tracer 绑定时经过 `run_graph` 的 `bind_run_ids` |
| `end_time == start_time` | 时间助手是否使用纳秒精度；是否保证 `end_ns = max(end_ns, start_ns + 1)` |
| `import freegraph` 加载了 L5 | `freegraph/__init__.py` 是否误加 import |
| 公开 API 快照红 | 是否误把 helpers 加进 `freegraph.graph` 门面 |
| 依赖门禁红 | 是否 import 了 `opentelemetry` / `langchain` / `langsmith` |
