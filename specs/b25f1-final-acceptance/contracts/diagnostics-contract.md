# Contract: `harness/demo/diagnostics.py`

**Feature**: B25F1 · **Date**: 2026-11-25
**Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)

> 锁定 FR-006 / SC-003：trace / checkpoint / 时间旅行的可诊断性验收脚本。
> 依赖：**只 import `freegraph` + Python 标准库**；不引入第三方依赖。

---

## 1. 入口与退出码

```bash
python harness/demo/diagnostics.py
```

| 码 | 含义 |
|---|---|
| `0` | 三组全部 PASS |
| `1` | 断言失败 |
| `2` | 环境未就绪（缺 `freegraph` / 必要 API） |

最后一行 MUST 打印 `diagnostics: PASS|FAIL`。
断言框架沿用 demo 的内联 `check` / `eq` / `section` / `finish`（单文件独立运行）。

---

## 2. trace 组

### 2.1 JSONL 后端

```python
store = FileTraceStore(directory=tmp)
graph = build_graph().compile(tracer=store)
graph.invoke({"value": 0}, RunConfig(thread_id="t-trace"))
```

断言：

- `tmp/trace-<run_id>.jsonl` 至少 1 个；
- 存在 `kind="span"` 行；
- 存在 `kind="trace_record"` 行；
- 模型 / 工具 span（若图含）与节点 span 的 `parent` 关系正确；
- C23 四项关联键存在（`run_id` / `thread_id` / `node` / `span_id` 等，按 B19F1 契约）。

### 2.2 SQLite 后端

```python
store = SqliteTraceStore(database=tmp / "traces.sqlite3")
graph = build_graph().compile(tracer=store)
graph.invoke({"value": 0}, RunConfig(thread_id="t-trace"))
rows = store.query(TraceQuery(thread_id="t-trace"))
```

断言：

- 四类过滤：`run_id` / `thread_id` / `node` / 时间窗（`start_time` / `end_time`）各至少 1 条；
- 组合过滤（如 `thread_id + node`）条数正确；
- 空过滤器 `TraceQuery()` 返回全部；
- `json.dumps(rows)` 成功。

### 2.3 两后端等价

- 同一 `TraceQuery` 在 `FileTraceStore` 与 `SqliteTraceStore` 上**逐条相等**（按 B20F2 口径）。

---

## 3. checkpoint 组

### 3.1 `MemorySaver`

```python
saver = MemorySaver()
graph = build_graph().compile(checkpointer=saver)
cfg = RunConfig(thread_id="t-cp")
graph.invoke({"value": 0}, cfg)
```

断言：

- `graph.get_state(cfg)` 返回快照；
- `graph.get_state_history(cfg)` 至少 1 条；
- `graph.get_tuple(cfg)`（或等价）往返正确。

### 3.2 `SqliteSaver`

```python
saver = SqliteSaver.from_conn_string(str(tmp / "cp.sqlite3"))
graph = build_graph().compile(checkpointer=saver)
```

断言：

- 持久化往返（写后读回）；
- `get_state` / `get_state_history`（倒序）正确；
- `stream(stream_mode="checkpoints")` 的事件数与 payload（`StateSnapshot`）正确；
- `tasks` / `interrupts` 形状符合 B15F1 口径。

---

## 4. 时间旅行组

| 用例 | 断言 |
|---|---|
| 历史点重放 | `invoke(None, snapshot.config)` 从历史快照继续执行，结果正确 |
| `update_state` 覆盖 | 新值覆盖旧值；返回 `RunConfig` |
| `update_state` 归约 | 有 reducer 的字段按归约器合并 |
| 分叉后原历史不变 | 新分支写入后，原历史快照数量 / 内容不变 |
| 中断组合 | `interrupt` / `resume` + 历史快照；`interrupts` 关联正确 |

**MUST NOT**：

- 通过猴补 `compile` / `invoke` 把组件塞进固定脚本；
- 使用未锁定的 API 形态；
- 在 diagnostics 中访问网络（trace / checkpoint 全部本地）。

---

## 5. 与 `harness/demo/acceptance.py` 的接线

`harness/demo/acceptance.py` 的 `SUITES` MUST 包含：

```python
("diagnostics", "diagnostics.py", "trace / checkpoint / 时间旅行（M3 可诊断性）")
```

执行顺序：

```text
acceptance(自检+零出站) → graph_core → agent_loop → visualization → diagnostics → target(fake)
```

`diagnostics.py` 缺失 ⇒ `harness/demo/acceptance.py` **判失败**（不得跳过）。

---

## 6. 失败示例

```text
[FAIL] trace · FileTraceStore 未产出 trace-*.jsonl
[FAIL] trace · SQLite query(thread_id=...) 期望 1 条，实际 0
[FAIL] checkpoint · 历史不是倒序
[FAIL] time travel · 分叉后原历史被改写
[FAIL] diagnostics 环境未就绪：freegraph.persistence.SqliteSaver 不可用
```
