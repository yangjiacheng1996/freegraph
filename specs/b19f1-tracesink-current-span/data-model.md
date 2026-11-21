# Data Model: B19F1 · `TraceSink` 接入 + `current_span()` + 默认关闭

**Date**: 2026-11-21 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

> **2026-11-21 分析修复**：`output_state` = **节点原始返回值**（`node.run` raw return）；
> `concurrency_group` = 本轮**派发集**（含未启动取消任务）；SC-011 以
> `json.dumps(record.to_jsonable())` 判定。
>
> **不变量**：`Span`（11 字段 · B2F1）、`TraceSink`（3 方法 · B2F1）、`RunConfig`（9 字段 ·
> B1F1）、`SuperStepResult` / `PregelTask`（B7F1 / B12F1）**逐字不改**。本 feature 只新增
> **L5 自有**的 `TraceRecord` 与 `SpanProducer` 的扩展方法，并复用 B18F1 的 `SpanProducer`。

---

## 1. 实体总览

| 实体 | 层 | 归属 | 说明 |
|---|---|---|---|
| `Span` | L1 | B2F1（冻结） | 11 字段；本 feature **原样消费** |
| `TraceSink` | L1 | B2F1（冻结） | `on_span_start` / `on_span_end` / `current_span`（3 方法） |
| `SpanProducer` | L5 | B18F1（复用 + 扩展） | run-scoped 当前 span 栈 / 父子 / 转发 / 隔离 |
| `current_span()` | L5 | **本 feature** | 模块函数；返回上下文内最内层 `Span` |
| `TraceRecord` | L5 | **本 feature** | 每节点任务一条补充 trace 记录 |
| `trace_run_scope()` | L5 | **本 feature** | run-scoped 双绑定 + 嵌套屏蔽 |
| `TaskTraceMeta` | L2 | **本 feature**（私有） | 纯数据；触发源 / 并发组 / 屏障组 / 轮次 |
| `TaskTracePayload` | L2 → L5 | **本 feature**（私有） | 纯数据 dict；`_bind` → `SpanProducer.on_trace_record` |

---

## 2. `TraceRecord`（L5 · 新实体）

**形态**：`@dataclass(frozen=True, slots=True, kw_only=True)`（与 L1 数据类同风格；
不放 L1 ⇒ 不扩 22 符号面）。

| 字段 | 类型 | 必填 | 语义 | 来源 |
|---|---|---|---|---|
| `span_id` | `str` | ✅ | 对应节点 span 的 `id` | `start_node_span` 返回的 `Span.id` |
| `task_id` | `str` | ✅ | 任务标识：标准 = 节点名；fan-out = `节点名:TaskId`（B11F1 F-13） | `_run_round` 的 `task_key` |
| `run_id` | `str` | ✅ | 单次运行标识（非空） | 节点 span 的 `run_id` |
| `thread_id` | `str \| None` | ✅（可空） | 会话标识 | 节点 span 的 `thread_id` |
| `checkpoint_id` | `str \| None` | ✅（可空） | 检查点标识（v1 通常 `None`） | 节点 span 的 `checkpoint_id` |
| `node` | `str` | ✅ | 节点内部名 | `_run_round` 的 `target` |
| `superstep` | `int` | ✅ | 当前轮 **0 起**索引 = `state.step` | `_run_round` |
| `triggers` | `tuple[TriggerId, ...]` | ✅ | 触发源标识（见 §4） | `_satisfied_groups` / fan-out 载荷 |
| `concurrency_group` | `tuple[str, ...]` | ✅ | 本轮**派发集**的 `task_id`（见 §4.2） | `_run_round` |
| `barrier_groups` | `tuple[tuple[str, ...], ...]` | ✅（可空元组） | 已满足的多源组（见 §4.3） | `_satisfied_groups` |
| `input_state` | `Any` | ✅ | 节点实际入参（JSON 安全降级后） | `node_input` |
| `output_state` | `Any` | ✅ | **节点原始返回值**（`node.run` raw return；JSON 安全降级后） | `node.run` 的 raw return（归一结果仅用于调度） |
| `error` | `BaseException \| None` | ✅（可空） | **原异常对象**（+ `add_note`） | `_bind` 捕获 |

**不变量**：

- `run_id` **非空**；`thread_id` / `checkpoint_id` 可为 `None`（不伪造）。
- `span_id` == 对应节点 span 的 `id`；`record 数 == 节点 span 数`（FR-015 / SC-017）。
- `input_state` / `output_state` 已经过 `json_safe`（可直接 `json.dumps`）；
  `error` **不**降级（保留原对象）。
- `triggers` / `concurrency_group` / `barrier_groups` 均为**确定性**顺序。
- 记录与节点 span **一一对应**；不另发轮记录。

**方法**：

| 方法 | 返回 | 语义 |
|---|---|---|
| `to_jsonable()` | `dict[str, Any]` | B20 落盘视图：`error` → `{"type": ..., "message": ...}` 或 `None`；其余字段已 JSON 安全 |

> **SC-011 口径**：`json.dumps(record.to_jsonable())` 不抛；**不**要求
> `json.dumps(record)`（`error` 是异常对象）。

---

## 3. `TriggerId`（L5 类型别名）

```python
TriggerId = tuple[Any, ...]
```

| 形态 | 语义 | 来源 |
|---|---|---|
| `("e", 源节点名)` | 边触发源（静态边 **或** `Command.goto` · 同源口径） | `_trigger_groups` 的 `_EDGE_SOURCE = "e"` |
| `("send", 产生者节点名, Send 序号)` | fan-out 派发任务的 trace 标识（**不是**第三类调度触发源） | `state.fanout[producer_id]` + `task.index` |

> `("send", ...)` 只作**展示标识**；B7F1 的调度触发源空间仍只有 `("e", ...)`。B9F1 的
> 「不另造第三类触发源」不被违反。

---

## 4. 触发源 / 并发组 / 屏障组

### 4.1 触发源（`triggers`）

- **标准任务**：`satisfied = _satisfied_groups(...)` ⇒ 取所有已满足组的成员并集
  （去重）⇒ `tuple(("e", source), ...)`。
- **fan-out 任务**：`(("send", producer, index),)`。
- **顺序**：按**统一排序键** `(kind, source, index)` 升序（`kind` 为 `"e"` / `"send"`）；
  标准边 / `goto` 的 `("e", source)` **没有 `index`** ⇒ 实现 MUST 使用 `index = -1`
  （`"e"` < `"send"`），MUST NOT 直接比较二元组 / 三元组的自然序。
- **不区分 goto / 静态边**：二者同属 `("e", source)`（B9F1 裁定 1）。

### 4.2 并发组（`concurrency_group`）

- 本轮**全部派发任务**的 `task_id` 元组（标准 + fan-out）。
- **顺序**：标准任务按**节点名序**；fan-out 任务按**数值** TaskId 序（B11F1 F-14）。
- 例：`("a", "b", "worker:2", "worker:3")`。
- **包含自身**；同一轮所有记录的该字段**相同**。
- 未启动的取消任务仍属「派发集」（它们被派发但未执行）；其自身无 record。
- **到达顺序 ≠ 执行次序**：`on_trace_record` 由并发任务完成时推送，到达顺序不稳定；
  确定性只由 `triggers` / `concurrency_group` 的字段内顺序承载。

### 4.3 屏障组（`barrier_groups`）

- 取 `satisfied` 中**成员数 > 1** 的组 ⇒ 每组转成**源节点名元组**。
- **顺序**：按组元组排序。
- 单源组只进 `triggers`，不进 `barrier_groups`。
- 无屏障 ⇒ `()`。
- 例：静态边 `[a, b] → c` 满足 ⇒ `barrier_groups = (("a", "b"),)`。

---

## 5. `superstep`

- `superstep = state.step`（**0 起** · 当前轮索引）。
- 与 `PregelTask.id` 的 `f"{state.step}:{task_id}"` 前缀**一致**（避免 off-by-one）。
- 空轮不产记录（没有任务执行）。

---

## 6. `json_safe`（L5 私有纯函数）

**输入**：任意 Python 值。**输出**：可直接 `json.dumps` 的值。

| 输入 | 输出 |
|---|---|
| `None` / `bool` / `int` / `float` / `str` | 原样 |
| `dict` | `{str_key: json_safe(v)}`；`str_key` = `k`（`str` 原样 · 标量 `str(k)` · 其它对象 `f"<{type.__module__}.{type.__qualname__}>"`），value 递归 |
| `list` | `[json_safe(v)]` |
| `tuple` | `[json_safe(v)]` |
| `set` / `frozenset` | 排序后的 `[json_safe(v)]`（元素不可排序 ⇒ 降级后的字符串排序） |
| 循环引用 | `"<cycle>"` |
| 其它对象 / bytes / 异常 | `f"<{type.__module__}.{type.__qualname__}>"` |

**不变量**：

- **确定**：同输入重复调用结果逐字相同。
- **不抛**：任何输入都返回一个 JSON 安全值。
- **不泄漏**：绝不内省对象属性 / `repr` / `__dict__`；只给类型名。
- **深度**：循环检测用 `id()` 的 `set`（不跨分支复用 ⇒ 只防环，不误伤共享子树）。

> **例外**：`TraceRecord.error` **不走** `json_safe`（保留原异常对象）；`to_jsonable()`
> 单独把 `error` 转成 `{"type": type(exc).__name__, "message": str(exc)}`。

---

## 7. `SpanProducer` 扩展（L5 · 复用 B18F1）

| 成员 | 类型 | 语义 |
|---|---|---|
| `current_span()` | `Span \| None` | 栈顶 span（空栈 ⇒ `None`）；供 L5 `current_span()` 使用 |
| `wants_trace_records` | `bool` | 构造期用 `getattr(receiver, "on_trace_record", None) is not None` 缓存；供 L2 `_bind` **廉价判断是否构造 payload** |
| `on_trace_record(payload)` | `None` | 由 L2 `_bind` 调用；构造 `TraceRecord` 并转发给接收端的**可选** `on_trace_record`；隔离 **`Exception`**（`BaseException` 不吞，与 B18F1 一致） |

**不变量**：

- `on_trace_record` **不是** `TraceSink` 协议成员；`SpanProducer` 通过 `getattr` 调用接收端。
- **接收端未实现 `on_trace_record` ⇒ `wants_trace_records == False` ⇒ L2 MUST NOT 构造 payload /
  MUST NOT 采集 `input_state` / `output_state`。**
- 记录推送在 `on_span_end` **之前**；此时 `current_span()` = 该节点 span。
- 记录构造 / 转发失败不得传播到图执行。

---

## 8. L2 私有形状（`TaskTraceMeta` / payload）

### 8.1 `TaskTraceMeta`（L2 · 纯数据）

| 字段 | 类型 | 说明 |
|---|---|---|
| `node` | `str` | 节点名 |
| `task_key` | `str` | 任务标识（标准 = 节点名；fan-out = `节点名:TaskId`） |
| `superstep` | `int` | `state.step` |
| `triggers` | `tuple[tuple[Any, ...], ...]` | 见 §3 |
| `concurrency_group` | `tuple[str, ...]` | 见 §4.2 |
| `barrier_groups` | `tuple[tuple[str, ...], ...]` | 见 §4.3 |

### 8.2 `TaskTracePayload`（L2 → L5 · 纯数据 dict）

```python
{
  "span_id": start.id,
  "task_id": meta.task_key,
  "run_id": start.run_id,
  "thread_id": start.thread_id,
  "checkpoint_id": start.checkpoint_id,
  "node": meta.node,
  "superstep": meta.superstep,
  "triggers": meta.triggers,
  "concurrency_group": meta.concurrency_group,
  "barrier_groups": meta.barrier_groups,
  "input_state": node_input,
  "output_state": raw_result,  # node.run 的原始返回值；失败路径为 None
  "error": exc_or_none,        # 失败路径；成功路径为 None
}
```

**`raw_result`** = `node.run(node_input)` 的**原始返回值**；`_execute_node_pure` 的归一结果
（`writes` / `gotos` / `fanout`）仅用于调度，**不**进入 `output_state`。

**私有承载形状（写死）**：新增 `_execute_node_pure_with_raw(...) -> tuple[dict[str, Any], Any]`
（`normalized, raw`）。`_run_round._bind._inner` 调用它后**解包**：把 `normalized` 返回给
`_worker`（调度器看到的仍是归一结果），把 `raw` 用于 `output_state`。当接收端未实现
`on_trace_record` 时，MUST 走原 `_execute_node_pure` 路径，MUST NOT 采集 raw / input-output。
**MUST NOT** 改 `SuperStepResult` / `PregelTask` / 节点签名。

**采集点**：`_run_round._bind._inner`；**仅当** `start is not None`（节点 span 已产生）
**且 `tracer.wants_trace_records` 为真（接收端实现了 `on_trace_record`）**，才构造 payload；
成功 / 异常 / 中断路径都构造；**在 `end_node_span` 之前**推送。

---

## 9. 生命周期与顺序

```text
compile(tracer=sink)
  └─ CompiledGraph._tracer = sink（仅持有）

invoke() / stream()
  └─ if tracer or outer B19F1 scope:
       ├─ invoke + tracer: bind_run_ids(new)   # L3→L2: 本次运行独立 id
       └─ trace_run_scope(tracer)              # L5: bind_tracer + bind_span_tracer
            ├─ invoke / StreamSession
            └─ 每个节点任务:
                 on_span_start(span)          # current_span = 新 span
                 node.run(...)                # 执行
                 on_trace_record(record)      # current_span = 该节点 span
                 on_span_end(end_span)        # current_span = 父级 / None
```

> **B18F1 直接绑定**不是 B19F1 作用域：当前无活动 B19F1 作用域时保持既有 L2/L5 绑定语义；
> 若本产物无 tracer **且** `_B19F1_SCOPE_ACTIVE` 为真，则 **B19F1 作用域优先**（作用域内的直接
> 绑定也被屏蔽）。
> **嵌套屏蔽**：仅当本产物无 tracer **且** `_B19F1_SCOPE_ACTIVE` 为真时进入
> `trace_run_scope(None)`；**作用域外**的 B18F1 直接绑定不触发屏蔽。

**异常 / 中断路径**：`on_span_start` → 抛异常 → `on_trace_record(error=exc)` →
`on_span_end` → 原异常重抛。**从未启动**的取消任务：无 span / 无 record。

---

## 10. 关系与边界

| 关系 | 规则 |
|---|---|
| `TraceRecord` ↔ `Span` | 通过 `span_id` 关联；记录**不**复制 / 不改写 `Span` 字段 |
| `TraceRecord` ↔ `TraceSink` | 经**可选** `on_trace_record` 推送；协议三方法不变 |
| `TraceRecord` ↔ `stream()` | 共享 `run_id` / `thread_id`；记录**不**进 `stream()` 信封 |
| `TraceRecord` ↔ B20 | B20 用 `to_jsonable()` 落 JSONL；B19F1 不落盘 |
| `Span.context` ↔ C21 `context` | **分离**；`Span.context` 恒空（B18F1 Q15） |
| 跨 compiled graph | 各自独立树；内层未注入 ⇒ 屏蔽外层；子图统一树 v2 / C26 |

---

## 11. 验证映射（spec → data model）

| Spec | 数据模型落点 |
|---|---|
| SC-001 / SC-004 | `Span.parent` / `SpanProducer.current_span()` |
| SC-002 / SC-005 | run scope 跳过 + 无 payload |
| SC-006 / SC-007 | `Span.run_id` / `thread_id` |
| SC-008 / SC-013 / SC-014 | `TraceRecord.triggers` / `json_safe` / 字段 |
| SC-009 / SC-014 / SC-015 | `concurrency_group` / 事件顺序 |
| SC-010 / SC-017 | `error` 原对象 / 对齐规则 |
| SC-011 / SC-012 | `input_state` / `output_state` / `to_jsonable` |
| SC-016 | 嵌套屏蔽 / 独立 run scope |
