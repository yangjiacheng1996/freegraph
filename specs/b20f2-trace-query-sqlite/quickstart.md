# Quickstart / Validation Guide: B20F2

**Feature**: B20F2 · **Date**: 2026-11-22 · **Spec**: [spec.md](./spec.md)
**Contracts**: [query-api](./contracts/query-api-contract.md) · [sqlite-store](./contracts/sqlite-store-contract.md) · [upstream-parity](./contracts/upstream-parity.md)

> 本文件是可执行的**验收 / 验证指南**，不是实现清单。所有片段只 import
> `freegraph` 与标准库，不需要任何 SaaS 账号 / API key / 网络。

---

## 0. 前提

- Python **3.11+**；仓库根已安装开发依赖（`.venv`）。
- **零出站**：验证前清空 `LANGSMITH_*` / `LANGCHAIN_*` / `OTEL_*` / `FREEGRAPH_*`。
- 基线（2026-11-22 实跑）：`1991 passed, 7 skipped`。

```bash
cd /path/to/freegraph
unset LANGSMITH_API_KEY LANGSMITH_TRACING LANGCHAIN_TRACING_V2 FREEGRAPH_TRACE_DIR
```

---

## 1. 最小验证：写入 + 按 run 查询（A1 / SC-001）

```python
import json
import tempfile
from pathlib import Path
from typing import TypedDict

from freegraph.graph import END, START, RunConfig, StateGraph
from freegraph.contracts import TraceQuery
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

# 从写入结果或 stream 事件里拿到 run_id
run_id = next(json.loads(line)["run_id"] for line in
              next(tmp.glob("trace-*.jsonl")).read_text(encoding="utf-8").splitlines())

result = store.query(TraceQuery(run_id=run_id))
assert result, result
assert all(row["run_id"] == run_id for row in result)
assert {row["kind"] for row in result} == {"span", "trace_record"}
assert len([r for r in result if r["kind"] == "span" and r["node"] == "a"]) == 1
json.dumps(result)  # 必须成功
```

**预期**：

- `store.query(TraceQuery(run_id=...))` 返回该次运行的全部 span / record；
- 每行 `kind` 只有两种；节点 `a` / `b` 都有 span + record；
- 结果可直接 `json.dumps`。

---

## 2. 按 thread 查询（A2 / SC-002）

```python
# 同一 store 再跑一次，换 thread_id
g.compile(tracer=store).invoke({"x": 0}, config=RunConfig(thread_id="t-2"))

t1 = store.query(TraceQuery(thread_id="t-1"))
t2 = store.query(TraceQuery(thread_id="t-2"))
assert t1 and t2
assert all(row["thread_id"] == "t-1" for row in t1)
assert all(row["thread_id"] == "t-2" for row in t2)
assert {row["run_id"] for row in t1}.isdisjoint({row["run_id"] for row in t2})
```

**预期**：两个 thread 的结果互不混入；每次运行一个 `run_id`。

---

## 3. 按时间窗查询（A3 / SC-003）

```python
spans = [r for r in store.query() if r["kind"] == "span"]
times = sorted(r["start_time"] for r in spans)
lo, hi = times[0], times[-1]

window = store.query(TraceQuery(start_time=lo, end_time=hi))
assert {r["kind"] for r in window} <= {"span", "trace_record"}

# 边界包含
edge = store.query(TraceQuery(start_time=lo, end_time=lo))
assert edge, edge
assert all(row.get("start_time") == lo or row["kind"] == "trace_record" for row in edge)

# 倒置 ⇒ []
assert store.query(TraceQuery(start_time=hi, end_time=lo)) == []
```

**预期**：窗内条目返回、窗外排除；边界包含；倒置返回 `[]`。

---

## 4. 按节点名查询（A4 / SC-004）

```python
node_a = store.query(TraceQuery(node="a"))
assert node_a
assert all(row["node"] == "a" for row in node_a)
assert any(row["kind"] == "span" for row in node_a)
assert any(row["kind"] == "trace_record" for row in node_a)

# 模型 / 工具子 span：其 node 也等于所属节点名，应一并返回
node_b = store.query(TraceQuery(node="b"))
assert all(row["node"] == "b" for row in node_b)
```

**预期**：该节点的节点 span、内部模型 / 工具 span、record 全部返回；其它节点 0 条。

---

## 5. 组合过滤 + 稳定排序 + 副本（A5 / SC-005 / SC-009）

```python
combo = store.query(TraceQuery(run_id=run_id, thread_id="t-1", node="a"))
assert all(r["run_id"] == run_id and r["thread_id"] == "t-1" and r["node"] == "a"
           for r in combo)

first = store.query(TraceQuery(run_id=run_id))
second = store.query(TraceQuery(run_id=run_id))
assert first == second                 # 稳定排序

first[0]["node"] = "mutated"
assert store.query(TraceQuery(run_id=run_id)) == second   # 独立副本
```

**预期**：AND 组合；同一查询两次结果逐条相等；调用方修改结果不影响存储。

---

## 6. SQLite 后端 + 两后端等价（A6 / SC-006）

```python
from freegraph.observability import SqliteTraceStore

db = tmp / "traces.sqlite3"
sqlite_store = SqliteTraceStore(database=db)
app_sqlite = g.compile(tracer=sqlite_store)

run_sql = app_sqlite.invoke({"x": 0}, config=RunConfig(thread_id="t-1"))["x"]
assert run_sql == 2

# 用同一 run_id 分别查两个后端（先各写一次，再比较空过滤器 / 四类过滤）
q = TraceQuery(thread_id="t-1")
jsonl_rows = store.query(q)
sqlite_rows = sqlite_store.query(q)
assert jsonl_rows == sqlite_rows, (len(jsonl_rows), len(sqlite_rows))

assert sqlite_store.query()  # 空过滤器取全部
assert json.dumps(sqlite_store.query())  # 可序列化
```

**预期**：同一事件流 / 同一查询在两个后端逐条相等；空过滤器合法；结果可序列化。

> 注意：`store` 与 `sqlite_store` 应各自写入**同一组**事件（同一图、同一 thread），
> 比较的是查询语义，不是跨后端的 run_id 相同。

---

## 7. 容错 / 只读 / 校验（SC-013 / SC-017）

```python
import os

# 1) 缺失存储 ⇒ []
assert FileTraceStore(tmp / "missing").query() == []
assert SqliteTraceStore(tmp / "missing.sqlite3").query() == []

# 2) 坏行跳过
bad = tmp / "trace-bad.jsonl"
bad.write_text('{"kind": "span", "id": "x"}\nnot-json\n', encoding="utf-8")
rows = FileTraceStore(tmp).query()
# 坏行 / 残缺行被跳过；不会抛错

# 3) 未知 kind 跳过
unknown_dir = tmp / "unknown-kind"
unknown_dir.mkdir()
(unknown_dir / "trace-unknown.jsonl").write_text(
    '{"kind": "event", "run_id": "r"}\n', encoding="utf-8"
)
assert FileTraceStore(unknown_dir).query() == []  # 不返回未知 kind

# 4) 非白名单文件名跳过
(tmp / "trace-a.b.jsonl").write_text('{"kind": "span"}\n', encoding="utf-8")
FileTraceStore(tmp).query()   # 跳过 + WARNING，不读取

# 5) 类型错误
try:
    store.query(TraceQuery(run_id=123))  # type: ignore[arg-type]
except TypeError:
    pass
else:
    raise AssertionError("expected TypeError")

# 6) 非法时间
try:
    store.query(TraceQuery(start_time="not-a-time"))
except ValueError:
    pass
else:
    raise AssertionError("expected ValueError")

# 7) 查询只读：查询前后文件哈希不变
import hashlib
before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp.glob("trace-*.jsonl")}
store.query()
after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp.glob("trace-*.jsonl")}
assert before == after
```

**预期**：坏行 / 未知 kind / 非白名单 / 符号链接跳过并告警；缺失存储 `[]`；
类型错误 `TypeError`；坏时间 `ValueError`；查询不改文件。

---

## 8. 并发写 + 查询（SC-011 / Windows）

```python
from concurrent.futures import ThreadPoolExecutor
from freegraph.observability import TraceRecord

sqlite_store = SqliteTraceStore(database=tmp / "concurrent.sqlite3")
records = [ ... ]  # 同一 run 的多条 TraceRecord

with ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(sqlite_store.on_trace_record, records))
    list(pool.map(lambda _: sqlite_store.query(), range(8)))

rows = sqlite_store.query()
assert len(rows) == len(records)
assert all(isinstance(row, dict) for row in rows)
```

**预期**：无数据库损坏、无半行 / 未提交条目；查询结果可序列化；排序合法。
**Windows CI**：同一用例 MUST 通过；`busy_timeout` 超时按写入失败隔离 / 查询异常交调用方。

---

## 9. 命令

```bash
# 定向：查询 API / SQLite / 后端等价
.venv/bin/python -m pytest tests/observability/test_b20f2_query_api.py -q
.venv/bin/python -m pytest tests/observability/test_b20f2_query_time.py -q
.venv/bin/python -m pytest tests/observability/test_b20f2_query_node.py -q
.venv/bin/python -m pytest tests/observability/test_b20f2_query_result.py -q
.venv/bin/python -m pytest tests/observability/test_b20f2_query_validation.py -q
.venv/bin/python -m pytest tests/observability/test_b20f2_query_tolerance.py -q
.venv/bin/python -m pytest tests/observability/test_b20f2_query_read_only.py -q
.venv/bin/python -m pytest tests/observability/test_b20f2_sqlite_write.py -q
.venv/bin/python -m pytest tests/observability/test_b20f2_sqlite_lifecycle.py -q
.venv/bin/python -m pytest tests/observability/test_b20f2_sqlite_concurrency.py -q
.venv/bin/python -m pytest tests/observability/test_b20f2_backend_parity.py -q

# 契约 / 门禁
.venv/bin/python -m pytest tests/contracts/test_b20f2_contracts.py -q
.venv/bin/python -m pytest tests/contracts/test_b20f2_gates.py -q

# 差分（上游缺席即 skip）
.venv/bin/python -m pytest tests/differential/test_b20f2_trace_query_parity.py -q

# 一键验收
.venv/bin/python harness/verification/B20F2/acceptance.py
# 预期最后一行：B20F2 acceptance: PASS

# 全量回归（实施前后各跑一次）
.venv/bin/python -m pytest -q --tb=no
```

**预期**：定向全绿；差分 D-501…D-508 在上游可用时全绿（缺席 skip）；
全量回归在基线 `1991 passed, 7 skipped` 上**只增不减**（新测试计入）。

### 9.1 门禁

```bash
.venv/bin/python -m pytest tests/gates -q
.venv/bin/python -m pytest tests/contracts/test_architecture.py -q
```

**预期**：G21 / G24 / G26 / G27 全绿；L5 只 import 标准库 + L1 + 同层；
`import freegraph` 不加载 L5；无 env / 网络；`_file_store.py` 仍不 import `sqlite3`。

---

## 10. 人工验收记录

- 路径：`harness/verification/B20F2/manual-verification.md`
- 必含：
  - 环境、步骤、实际输出、结论、遗留问题；
  - 四类过滤（run / thread / 时间 / 节点）+ 组合的实测输出；
  - JSONL / SQLite 同一查询逐条等价的结果；
  - 空过滤器 / 稳定排序 / `json.dumps` 证据；
  - 容错证据（坏行 / 未知 kind / 字段残缺 / 非白名单 / 符号链接 / 不兼容旧表）；
  - 并发写 + 查询证据（含 Windows 说明）；
  - 零出站证据（socket 监测夹具「框架出站 == 0」）；
  - `observability.__all__` 精确集合更新 + B20F1「无查询方法」断言拆分的追认
    （确认人 + 日期）；
  - **质量门禁 5 偏离声明**（fake / 本地轮；真实模型轮由 B25F1 承接）与
    **发起者追认文字**（确认人 + 日期，由发起者本人签署）；
  - `harness/demo/README.md` / `harness/verification/README.md` 更新证据。
- 自动守卫：`tests/runtime/test_b20f2_manual_record_guard.py`（在记录写就后执行）。
