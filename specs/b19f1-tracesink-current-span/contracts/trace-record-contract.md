# Contract: 补充 trace 记录（`TraceRecord`）

**Feature**: B19F1 · **Date**: 2026-11-21 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)

> 记录是 **L5 自有**、与 `Span` **分离**的补充元数据。它**不是** `Span` 的字段，
> **不**写进 `Span.attributes` / `Span.context`，**不是** `TraceSink` 协议成员。

---

## 1. 形态与推送

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class TraceRecord:
    span_id: str
    task_id: str
    run_id: str
    thread_id: str | None
    checkpoint_id: str | None
    node: str
    superstep: int
    triggers: tuple[TriggerId, ...]
    concurrency_group: tuple[str, ...]
    barrier_groups: tuple[tuple[str, ...], ...]
    input_state: Any
    output_state: Any
    error: BaseException | None
```

| 规则 | 内容 |
|---|---|
| **粒度** | **每个节点任务一条**；不另发轮记录 |
| **对齐** | 与节点 span 一一对应：`record 数 == 节点 span 数` |
| **推送** | `sink.on_trace_record(record)`（**可选**鸭子类型方法） |
| **时序** | **sink 实现 `on_trace_record` 时** `on_span_start → on_trace_record → on_span_end`；未实现时 `start → end` |
| **到达顺序** | `on_trace_record` 由并发任务完成时推送，**到达顺序不保证**；确定性由字段内顺序承载 |
| **异常** | 记录回调异常被隔离（FR-017） |
| **不实现** | sink 无 `on_trace_record` ⇒ 跳过，零影响；**MUST NOT 构造 `TraceRecord` / MUST NOT 采集 input-output** |
| **不落盘** | B19F1 不存储；B20 用 `to_jsonable()` 落 JSONL |

---

## 2. 字段契约

| 字段 | 规则 |
|---|---|
| `span_id` | == 对应节点 span 的 `id`（B2F1） |
| `task_id` | 标准任务 = 节点名；fan-out = `f"{节点名}:{TaskId}"`（B11F1 F-13） |
| `run_id` | **非空**；== 对应 span 的 `run_id` |
| `thread_id` | == 对应 span 的 `thread_id`；可为 `None` |
| `checkpoint_id` | == 对应 span 的 `checkpoint_id`；v1 通常 `None` |
| `node` | 节点内部名（alias 已移除） |
| `superstep` | **0 起**当前轮索引 = `state.step`；与 `PregelTask.id` 前缀一致 |
| `triggers` | 见 §3；确定性排序 |
| `concurrency_group` | 见 §4；确定性排序 |
| `barrier_groups` | 见 §5；确定性排序；无则 `()` |
| `input_state` | 节点实际入参；`json_safe` 后 |
| `output_state` | **节点原始返回值**（`node.run` raw return）；`json_safe` 后 |
| `error` | **原异常对象**（+ `add_note`）；成功时 `None`；**不**降级 |

**不变量**：`run_id` 非空；`span_id` 与 span 对应；记录不复制 / 不改写 `Span` 字段；
`input_state` / `output_state` 可直接 `json.dumps`；`error` 保留原对象。

---

## 3. 触发源 `triggers`

```python
TriggerId = tuple[Any, ...]
```

| 形态 | 含义 | 来源 |
|---|---|---|
| `("e", 源节点名)` | **边触发源**：静态边 **或** `Command.goto`（同源口径 · B9F1） | `_trigger_groups` / `_satisfied_groups` |
| `("send", 产生者节点名, Send 序号)` | **fan-out 派发任务**的 trace 标识（非第三类调度触发源） | `state.fanout[producer_id]` + `task.index` |

| 规则 | 内容 |
|---|---|
| **覆盖** | 静态边 + `goto` + fan-out **一起给**；MUST NOT 只给 `goto` 或只给静态边 |
| **顺序** | 按统一键 `(kind, source, index)` 升序；标准边 / `goto` 的 `("e", source)` 令 `index = -1`，MUST NOT 直接混排二元组 / 三元组；同一输入重复运行逐字一致 |
| **去重** | 同一组内的同一 source 只出现一次 |
| **不伪造** | MUST NOT 期待 B9F1 / B11F1 预供跳转 / 派发记录 |

示例（同一轮）：`(("e", "a"), ("e", "b"))`；fan-out：`(("send", "fan", 0),)`。

---

## 4. 并发组 `concurrency_group`

| 规则 | 内容 |
|---|---|
| **内容** | 本轮**全部派发任务**的 `task_id` |
| **顺序** | 标准任务按**节点名序** → fan-out 任务按**数值** TaskId 序（B11F1 F-14） |
| **包含自身** | 是；同一轮所有记录的该字段**相同** |
| **未启动任务** | 仍在派发集内（它被派发但未执行）；其自身无 record |
| **确定性** | MUST NOT 用完成时刻 / 声明顺序 / 记录到达顺序 |

示例：`("a", "b", "worker:2", "worker:3")`。

---

## 5. 屏障组 `barrier_groups`

| 规则 | 内容 |
|---|---|
| **内容** | `satisfied` 中**成员数 > 1** 的触发组，每组 = **源节点名元组** |
| **顺序** | 按组元组升序 |
| **单源** | 不进入 `barrier_groups`（只进 `triggers`） |
| **无屏障** | `()` |
| **不写结果对象** | MUST NOT 写进 `SuperStepResult` / `Span.attributes` |

示例：`[a, b] → c` 满足 ⇒ `(("a", "b"),)`。

---

## 6. 输入 / 输出 / 错误

| 字段 | 采集规则 |
|---|---|
| `input_state` | 节点实际入参（标准 = 稀疏状态 dict；fan-out = 自定义入参经 `with_context_arg`） |
| `output_state` | **节点原始返回值**（`node.run` raw return）；内部对象降级为占位符。归一结果（`writes` / `gotos` / `fanout`）仅用于调度，**不**进入本字段。私有承载：`_execute_node_pure_with_raw` 返回 `(normalized, raw)`，`_bind` 解包后只把 `normalized` 交回调度 |
| `error` | 原异常对象（`BaseException`）；成功 = `None` |

> **2026-11-21 分析修复**：`output_state` = 节点 `node.run` 的 **raw return**；
> `concurrency_group` = 本轮**派发集**（含未启动取消任务）；SC-011 以
> `json.dumps(record.to_jsonable())` 判定。

**JSON 安全降级**（L5 `json_safe`）：

| 输入 | 输出 |
|---|---|
| `None` / `bool` / `int` / `float` / `str` | 原样 |
| `dict` / `list` / `tuple` | 递归（tuple → list）；dict key 非 `str` 时先按 `str` / 类型名降级为字符串，再递归 value |
| `set` / `frozenset` | 排序后的 list |
| 循环引用 | `"<cycle>"` |
| 其它对象 / bytes / 异常 | `f"<{module}.{qualname}>"` |

**不变量**：确定、不抛、不内省对象属性、不泄漏内容。

---

## 7. JSONL 视图（B20 使用）

```python
def to_jsonable(self) -> dict[str, Any]: ...
```

- 返回一个可直接 `json.dumps` 的 dict；
- `error` → `{"type": type(exc).__name__, "message": str(exc)}` 或 `None`；
- 其余字段已 JSON 安全。

> **SC-011**：`json.dumps(record.to_jsonable())` 不抛。**不**要求 `json.dumps(record)`
> （`error` 是异常对象）。

---

## 8. 中断 / 取消对齐

| 场景 | span | record | `error` |
|---|---|---|---|
| 正常完成 | 开始 + 结束 | 1 条 | `None` |
| 节点抛真实异常 | 开始 + 结束 | 1 条 | 原异常对象 |
| `GraphInterrupt` | 开始 + 结束 | 1 条 | 原 `GraphInterrupt` 对象 |
| 节点自身抛取消异常（如 `CancelledError`） | 开始 + 结束 | 1 条 | 原取消 / 异常对象 |
| 并发取消（从未启动） | 无 | 无 | — |

**判据**：`record 数 == 节点 span 数`（SC-017）。

---

## 9. 与 `stream()` / B20 的关系

| 关系 | 规则 |
|---|---|
| `stream()` | 共享 `run_id` / `thread_id`；记录**不**进 stream 信封；两条通道不互为前置 |
| B20 | 用 `to_jsonable()` 落 JSONL；B19F1 不落盘、不查询 |
| `Span` | 通过 `span_id` 关联；记录不复制 `Span` 字段 |
| C21 `context` | 不进入 `Span.context`，也不作为记录的替代载体 |

---

## 10. 可选回调与协议面

```python
class TraceSink(Protocol):        # B2F1 冻结（3 方法）
    def on_span_start(self, span: Span) -> None: ...
    def on_span_end(self, span: Span) -> None: ...
    def current_span(self) -> Span | None: ...

# 可选扩展：真正的鸭子类型示例（不是 Protocol、不是 TraceSink 成员）
class MySink:
    def on_span_start(self, span): ...
    def on_span_end(self, span): ...
    def on_trace_record(self, record): ...   # 可选
```

- `on_trace_record` **不计入** `TraceSink` 三方法，**不定义**独立的 `TraceRecordSink` Protocol；
- 运行时只要求 `on_span_start` / `on_span_end`；`current_span` 可选；
- 记录回调异常隔离。
