# Quickstart / Validation Guide: B20F1

**Feature**: B20F1 · **Date**: 2026-11-21 · **Spec**: [spec.md](./spec.md)
**Contracts**: [file-trace-store](./contracts/file-trace-store-contract.md) · [jsonl-record](./contracts/jsonl-record-contract.md) · [upstream-parity](./contracts/upstream-parity.md)

> 本文件是可执行的**验收 / 验证指南**，不是实现清单。所有片段只 import
> `freegraph` 与标准库，不需要任何 SaaS 账号 / API key / 网络。

---

## 0. 前提

- Python **3.11+**；仓库根已安装开发依赖（`.venv`）。
- **零出站**：验证前清空 `LANGSMITH_*` / `LANGCHAIN_*` / `OTEL_*` / `FREEGRAPH_*`。
- 基线（2026-11-21 实跑）：`1917 passed, 6 skipped`。

```bash
cd /path/to/freegraph
unset LANGSMITH_API_KEY LANGSMITH_TRACING LANGCHAIN_TRACING_V2 FREEGRAPH_TRACE_DIR
```

---

## 1. 最小验证：落盘 + 双行（US1 / A1 / SC-001 / SC-002）

```python
import json
import tempfile
from pathlib import Path
from typing import TypedDict

from freegraph.graph import END, START, RunConfig, StateGraph
from freegraph.observability import FileTraceStore

class S(TypedDict, total=False):
    x: int

def a(state): return {"x": state.get("x", 0) + 1}
def b(state): return {"x": state.get("x", 0) + 1}

tmp = Path(tempfile.mkdtemp())
store = FileTraceStore(directory=tmp)

g = StateGraph(S)
g.add_node("a", a)
g.add_node("b", b)
g.add_edge(START, "a")
g.add_edge("a", "b")
g.add_edge("b", END)
app = g.compile(tracer=store)

out = app.invoke({"x": 0}, config=RunConfig(thread_id="t-1"))
assert out["x"] == 2

files = list(tmp.glob("trace-*.jsonl"))
assert len(files) == 1, files
lines = files[0].read_text(encoding="utf-8").splitlines()
objs = [json.loads(line) for line in lines]
assert {o["kind"] for o in objs} == {"span", "trace_record"}
assert len([o for o in objs if o["kind"] == "span"]) == 2
assert len([o for o in objs if o["kind"] == "trace_record"]) == 2
```

**预期**：

- `tmp` 下**恰好一个** `trace-<run_id>.jsonl`；
- 两个节点各有 1 条 span 行 + 1 条 record 行；
- 每行 `json.loads` 成功；`kind` 只有两个值。

### 1.1 用 `jq` 读

```bash
jq -c 'select(.kind == "span")' trace-*.jsonl
jq -c 'select(.kind == "trace_record")' trace-*.jsonl
jq -r 'select(.kind == "trace_record") | [.run_id, .thread_id, .node, (.checkpoint_id // "null")] | @tsv' trace-*.jsonl
```

**预期**：每个节点一行；`run_id` 非空；`thread_id == "t-1"`；`node` 为 `a` / `b`；
`checkpoint_id` 字段可读（v1 通常 `null`）。

---

## 2. 字段逐项断言（SC-002 / A3）

```python
SPAN_FIELDS = {
    "kind", "id", "name", "attributes", "parent", "start_time", "end_time",
    "context", "thread_id", "run_id", "node", "checkpoint_id",
}
RECORD_FIELDS = {
    "kind", "span_id", "task_id", "run_id", "thread_id", "checkpoint_id",
    "node", "superstep", "triggers", "concurrency_group", "barrier_groups",
    "input_state", "output_state", "error",
}
for obj in objs:
    if obj["kind"] == "span":
        assert set(obj) == SPAN_FIELDS
        assert obj["end_time"] is not None
    else:
        assert set(obj) == RECORD_FIELDS
    assert {"run_id", "thread_id", "node", "checkpoint_id"} <= set(obj)
```

**预期**：span 行 11/11 + `kind`；record 行 13/13 + `kind`；C23 四项每行都有。

### 2.1 关联

```python
span_ids = {o["id"] for o in objs if o["kind"] == "span"}
record_ids = {o["span_id"] for o in objs if o["kind"] == "trace_record"}
assert record_ids <= span_ids
```

**预期**：每个节点 record 的 `span_id` 都能在同文件找到 `id` 相等的 span 行。

---

## 3. 默认关闭 / 零副作用（US4 / A5 / SC-003）

```python
# 不注入
app_no = g.compile()
assert app_no.invoke({"x": 0})["x"] == 2
assert list(tmp.glob("trace-*.jsonl")) == []

# 显式 None
app_none = g.compile(tracer=None)
assert app_none.invoke({"x": 0})["x"] == 2
assert list(tmp.glob("trace-*.jsonl")) == []

# 只构造不运行
store_only = FileTraceStore(directory=tmp / "never")
assert not (tmp / "never").exists()
```

**预期**：未注入 / `tracer=None` ⇒ 零文件 / 零目录；只构造 ⇒ 不创建目录。

### 3.1 环境变量不改变行为

```bash
FREEGRAPH_TRACE_DIR=/tmp/ignored LANGSMITH_TRACING=true \
  .venv/bin/python -c "from freegraph.graph import StateGraph; ..."
```

**预期**：仍零文件；注入 `FileTraceStore(directory=...)` 时只认显式目录，env 不覆盖。

---

## 4. 失败感知（US3 / A4 / SC-004 / SC-019）

### 4.1 只读目录（POSIX）

```python
import os
import stat

readonly = tmp / "readonly"
readonly.mkdir()
os.chmod(readonly, 0o500)

errors = []
store = FileTraceStore(directory=readonly, on_error=errors.append)
app = g.compile(tracer=store)
out = app.invoke({"x": 0})            # 不抛
assert out["x"] == 2
assert store.write_errors > 0
assert store.last_error
assert errors
os.chmod(readonly, 0o700)            # 清理
```

**预期**：图正常返回；`write_errors > 0`；`last_error` 非空；`on_error` 被调用；
日志有 WARNING；文件中无半行（或没有文件）。

> Windows 上跳过 `chmod` 只读断言；用「路径是普通文件」模拟失败。

### 4.2 路径是文件

```python
not_a_dir = tmp / "not-a-dir"
not_a_dir.write_text("x", encoding="utf-8")
store = FileTraceStore(directory=not_a_dir)
assert g.compile(tracer=store).invoke({"x": 0})["x"] == 2
assert store.write_errors > 0
```

**预期**：运行成功；诊断可见。

### 4.3 不重试

用 monkeypatch 让第一次 `os.open` / `os.fdopen` 失败、第二次成功；调用一次
`on_span_end` 后断言 `write_errors == 1`、文件中没有该行；再调用一次成功追加。

---

## 5. 并发 / 锁（SC-008 / SC-018）

```python
from concurrent.futures import ThreadPoolExecutor

store = FileTraceStore(directory=tmp)
# 构造同一 run_id 的多条 record / span（可用 B19F1 的 TraceRecord 或直接 run 图）
with ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(lambda i: store.on_trace_record(record_i), range(32)))

lines = next(tmp.glob("trace-*.jsonl")).read_text(encoding="utf-8").splitlines()
assert len(lines) == 32
assert all(isinstance(json.loads(line), dict) for line in lines)
```

**预期**：每行完整；无字节交错 / 半行；同一实例内串行。

### 5.1 `on_error` 重入

构造「第一行序列化失败 + `on_error` 内再写一行合法事件」；断言不死锁、合法行落盘、
`write_errors == 1`。

---

## 6. 权限 / 生命周期（SC-016 / SC-017）

```python
import stat

path = next(tmp.glob("trace-*.jsonl"))
mode = stat.S_IMODE(path.stat().st_mode)
assert mode & 0o077 == 0          # POSIX：仅本人
assert not hasattr(store, "close")
assert not hasattr(store, "__enter__")
assert not hasattr(store, "__exit__")

# 回调返回后无残留句柄：Windows 上 rename / delete 会失败；POSIX 也执行
renamed = path.with_name(path.name + ".renamed")
path.rename(renamed)
renamed.unlink()
```

**预期**：POSIX 新建文件 `0o600`（或更紧）；无 `close` / 上下文管理器；
回调返回后可立即 rename / delete。

---

## 7. 图形 / 模型 / 工具 span（US1 场景 3）

```python
from freegraph.observability import invoke_model, invoke_tool

class Model:
    model_name = "demo"
    def invoke(self, value): return value

class Tool:
    name = "demo-tool"
    description = "demo"
    def invoke(self, value): return value

def node(state):
    invoke_model(Model(), 1)
    invoke_tool(Tool(), 2)
    return {"x": 1}
```

**预期**：文件中额外含 `chat demo` / `execute_tool demo-tool` 的 span 行；
`parent` 指向节点 span 的 `id`；这两个 span 没有 record 行。

---

## 8. 异常节点（US1 场景 4）

```python
def boom(state):
    raise RuntimeError("boom")

# 运行；捕获 RuntimeError
```

**预期**：节点 span 行仍落盘（`end_time` 非空）；record 行 `error` 为
`{"type": "RuntimeError", "message": "boom"}`；原异常仍抛给调用方。

---

## 9. 多 run（SC-007）

```python
store = FileTraceStore(directory=tmp)
app = g.compile(tracer=store)
app.invoke({"x": 0})
app.invoke({"x": 0})

files = sorted(tmp.glob("trace-*.jsonl"))
assert len(files) == 2
for path in files:
    objs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len({o["run_id"] for o in objs}) == 1
    assert path.stem == f"trace-{objs[0]['run_id']}"
```

**预期**：两个 `run_id` 两个文件；文件内 `run_id` 唯一；不混写。

---

## 10. 命令

```bash
# 定向
.venv/bin/python -m pytest tests/observability -q
.venv/bin/python -m pytest tests/contracts -q
.venv/bin/python -m pytest tests/facade -q

# 差分（上游缺席即 skip）
.venv/bin/python -m pytest tests/differential/test_b20f1_local_trace_parity.py -q

# 一键验收
.venv/bin/python harness/verification/B20F1/acceptance.py
# 预期最后一行：B20F1 acceptance: PASS

# 全量回归（实施前后各跑一次）
.venv/bin/python -m pytest -q --tb=no
```

**预期**：定向全绿；差分 D-401…D-408 在上游可用时全绿（缺席 skip）；
全量回归在基线 `1917 passed, 6 skipped` 上**只增不减**（新测试计入）。

### 10.1 门禁

```bash
.venv/bin/python -m pytest tests/gates -q
.venv/bin/python -m pytest tests/contracts/test_architecture.py -q
```

**预期**：G21 / G24 / G26 / G27 全绿；L5 只 import 标准库 + L1 + 同层；
`import freegraph` 不加载 L5；无 env / 网络。

---

## 11. 人工验收记录

- 路径：`harness/verification/B20F1/manual-verification.md`
- 必含：
  - 环境、步骤、实际输出、结论、遗留问题；
  - JSONL 样例行 + `jq` / `json.loads` 读回证据；
  - 写入失败感知证据（`write_errors` / `last_error` / `on_error` / WARNING）；
  - 零出站证据（socket 监测夹具「框架出站 == 0」）；
  - `observability.__all__` 精确集合更新的追认（确认人 + 日期）；
  - **质量门禁 5 偏离声明**（fake / 本地轮；真实模型轮由 B25F1 承接）与
    **发起者追认文字**（确认人 + 日期，由发起者本人签署）；
  - `harness/demo/README.md` 行改为「已锁定」的证据；
  - `harness/verification/README.md` 的 B20F1 记录行已更新。
- 自动守卫：`tests/runtime/test_b20f1_manual_record_guard.py`（T053；在记录写就后执行）。
