# 契约：B18F1 · Span 生产（L2 节点接缝 + L5 生产者 / 接收端）

**Feature**: `B18F1` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**上游**: `langgraph` **1.2.11** / `langchain-core` **1.7.6**（取证于 2026-11-20）
**状态**: Phase 1 设计契约 · **可被 `/speckit.tasks` 追溯** · **MUST NOT** 被测试解析

---

## §0 公开面（零新增）

| 面 | 本 feature 之后 |
|---|---|
| `freegraph.graph` 门面 | **零新增**（仍 8 个符号；`invoke` / `stream` 签名不动） |
| `freegraph.runtime.__all__` | **不变**（仍 23 个符号；`_span_hook` 不进） |
| `freegraph.contracts` | **零新增**（`Span` / `TraceSink` 冻结） |
| `Span` 11 字段 | **零改动**（B2F1） |
| `RunConfig` 九字段 | **零改动**（`run_id` 仍被忽略） |
| L5 可 import 面 | `freegraph.observability` 模块（非门面）：`invoke_model` / `invoke_tool` / `SpanProducer` |
| L2 私有 hook | `freegraph.runtime._span_hook`（`__all__ = []`） |

> **禁止**：把 helpers / `SpanProducer` 加进 `freegraph.graph`；把 `_span_hook` 符号加进
> `freegraph.runtime.__all__`；新增 L1 契约符号。

---

## §1 节点 span 生命周期（L2）

### 1.1 接缝

```text
_run_round._bind._inner(task_id, task_key, target, fn):
    started.append(task_id)
    with bind_current_task(task_id), bind_task(task_key, run_table, node_name=target):
        tracer = current_span_tracer()
        if tracer is None:
            return fn()                         # 零 span / 零回调
        run_id, thread_id = current_stream_ids()
        start = start_node_span(tracer, target, run_id, thread_id, None)
        try:
            result = fn()
        except BaseException:
            end_node_span(tracer, start)        # 不写 error.type（Q12）
            raise
        end_node_span(tracer, start)
        return result
```

- `target` = 节点内部名（标准任务 = 节点名；fan-out 任务 = 目标节点名）。
- `run_id` / `thread_id` 来自 `_stream_context.current_stream_ids()`。
- `checkpoint_id` = 运行期接缝值（v1 `None` · Q5）；模型 / 工具 span 从节点 span 继承。
- `tracer is None` ⇒ **不构造** `Span`、**不调用**接收端、**不生成** id。
- `start_node_span` MUST 在构造开始 `Span` 后调用 `tracer.on_span_start(start)`；
  `end_node_span` MUST 在构造结束 `Span` 后调用 `tracer.on_span_end(end)`。
  这两个调用是**唯一**的入栈 / 出栈 + 接收端转发点；缺失会导致模型 / 工具子 span 丢失 parent。

### 1.2 开始 / 结束

| 时点 | 行为 |
|---|---|
| 调用 `fn()` 前 | 构造开始 `Span`：`id=uuid4().hex`、`name=target`、`node=target`、`attributes={}`、`context={}`、`parent=tracer.current_span_id()`、`start_time=<UTC ISO-8601>`、`end_time=None`、`checkpoint_id=<运行期值 | None>` |
| `fn()` 返回 | 构造结束 `Span`：同 `id` / 同字段；`end_time=<UTC ISO-8601>`；`end_ns > start_ns` |
| `fn()` 抛异常 | 同「返回」的结束 Span（**不写** `error.type`）→ 原对象 / 类型 / 消息重抛 |

### 1.3 不变量

1. 每个被执行的节点任务 **恰好** 一对开始 / 结束（`Send` fan-out 的每个任务也算）。
2. 结束 span 的 `id` 与开始相同；开始快照不被改写。
3. 节点 span 的 `attributes` **恒为空映射**；`context` **恒为空映射**。
4. `run_id` 非空；`thread_id` = `RunConfig.resolved_thread_id()`；`node` = 节点名；
   `checkpoint_id` = 运行期值（v1 `None`；模型 / 工具 span 继承节点值）。
5. 并发任务各自独立；节点 span 的 `parent` = 创建时栈顶 id（顶层为 `None`）。
6. **`run_id` 为空 ⇒ 不产生 span**：接缝若发现 `run_id is None`，MUST NOT 构造空 `run_id` 的 span；MAY 记录一次 warning 后直接执行 `fn()`（C23：缺 `run_id` 是缺陷）。

---

## §2 运行 id 绑定

### 2.1 stream 路径（零改动）

`StreamSession.__enter__` 通过既有 `bind_stream(run_id, thread_id, ...)` 绑定
`_STREAM_RUN_ID` / `_STREAM_THREAD_ID`（`runtime/_stream.py:110-118`）。
B18F1 **不修改**该路径。

### 2.2 invoke 路径（新增私有助手）

`runtime/_stream_context.py` 新增：

```python
@contextmanager
def bind_run_ids(run_id: str, thread_id: str | None) -> Iterator[None]:
    """只绑定 _STREAM_RUN_ID / _STREAM_THREAD_ID；不碰 writer / sink / capture。"""
```

`run_graph` 的绑定规则：

```python
tracer = current_span_tracer()
if tracer is not None and current_stream_ids()[0] is None:
    with bind_run_ids(uuid.uuid4().hex, run_config.resolved_thread_id()):
        ... existing body ...
else:
    ... existing body ...
```

- 已有 `run_id`（stream / 嵌套）⇒ **不覆盖**。
- `RunConfig.run_id` **仍被忽略**；用户不可设置 / 覆盖。
- 未绑定 tracer ⇒ **不生成** span 专用 `run_id`、不绑定。
- **spec §5 口径**：stream 路径只读；invoke 路径经 `bind_run_ids` 写入**同一对** contextvar（不新增第二套载体）。

### 2.3 不变量

1. 一次运行一个 `run_id`；同一次运行的所有 span 共享。
2. `stream()` 的事件与 span 的 `run_id` / `thread_id` **逐字相同**。
3. 不同运行 `run_id` 不同。
4. `bind_run_ids` 是 **L2 私有符号**；不进 `__all__`；`bind_stream` 行为不变。

---

## §3 L5 生产者 / 接收端

### 3.1 鸭子类型 tracer

L2 在 `src/freegraph/runtime/_span_hook.py` 定义私有 `typing.Protocol` `_SpanTracer`；
L2 只要求以下方法（结构化满足，不要求继承；L5 **MUST NOT import** 该 Protocol）：

| 方法 | 用途 |
|---|---|
| `on_span_start(span)` | 节点 span 开始 |
| `on_span_end(span)` | 节点 span 结束 |
| `current_span_id() -> str \| None` | 节点 span 的 parent |

L5 `SpanProducer` 满足以上；B19F1 的 `TraceSink` 若作为**接收端（receiver）**，只要求
`on_span_start` / `on_span_end`（`current_span` 由 B19F1 自己用）。

> **术语**：本契约的 `tracer` = `SpanProducer`；`receiver` = 接收端。B19F1 的公开注入点
> MUST 构造 `SpanProducer`（接收端 = 用户 `TraceSink`）并把**同一个 `SpanProducer`**
> 同时绑定 L2 `_span_hook` 与 L5 `_producer`（双绑定；spec D-1 / R-4）。

### 3.2 当前 span 栈

- `SpanProducer` 持有 `ContextVar[tuple[_SpanFrame, ...]]`；
- `_SpanFrame = (span, kind)`；`kind ∈ {"node", "model", "tool"}`；
- `kind` 推断：
  - `attributes` 空 ⇒ `node`；
  - `gen_ai.operation.name == "execute_tool"` ⇒ `tool`；
  - 其他含 `gen_ai.operation.name` ⇒ `model`。
- `on_span_start` 入栈 + 转发接收端；`on_span_end` 按 `id` 出栈 + 转发接收端。
- `current_span_id()` = 栈顶 `id` 或 `None`。
- `current_node_span()` = 最近的 `node` 帧（供 helpers 取 `node` / `run_id` / `thread_id`）。

### 3.3 接收端转发

- 接收端方法：`on_span_start(span)` / `on_span_end(span)`（鸭子类型）。
- 接收端异常 ⇒ **隔离**；MAY 标准库 `logging.warning`；MUST NOT 传播到节点 / 图执行；
  MUST NOT 吞掉节点异常；MUST NOT 造成永久挂起。
- 栈的入 / 出 MUST 在接收端异常时仍保持平衡（先改栈，再回调；或 try/finally）。

### 3.4 L5 依赖面（ARCH-3）

允许：

- `freegraph.contracts.trace.Span`（L1）；
- 标准库；
- **零 L2 import**：不 import `superstep` / `_span_hook` / `_stream` / `_stream_context`；
  `run_id` / `thread_id` / `node` 从当前节点 span 继承。

禁止：

- `freegraph.runtime.superstep` / `_span_hook` / `_stream` / `_concurrency`；
- `freegraph.contracts.protocols.TraceSink` **不强制**；helpers 只与 `SpanProducer` 交互；
- `langchain*` / `langgraph*` / `langsmith` / `opentelemetry-*`。

---

## §4 时间与 id

| 项 | 规则 |
|---|---|
| 时间源 | 标准库 `time.time_ns()` |
| 格式 | `YYYY-MM-DDTHH:MM:SS.<9 位纳秒>+00:00`（UTC） |
| 严格正耗时 | `end_ns > start_ns`；若相等，`end_ns = start_ns + 1`（1 ns，不伪造微秒） |
| span id | `uuid.uuid4().hex`（标准库） |
| 开始 / 结束配对 | 同 `id`；结束是**新实例** |
| 时间助手位置 | L2 `_span_hook` + L5 `observability/_time.py` 各一份（层隔离） |

> **MUST NOT** 用 `datetime.isoformat(timespec="microseconds")` 作为唯一精度来源
> （极快调用会 `end == start`，SC-005 红）。

---

## §5 零开销

| 状态 | 行为 |
|---|---|
| 未绑定 tracer · 节点执行 | 一次 `current_span_tracer()` + `is None`；直接 `fn()` |
| 未绑定 tracer · `run_graph` | 一次 `current_span_tracer()` + `is None`；不生成 **span 专用** `run_id` |
| 未绑定 tracer · helpers | 形状校验后直接 `obj.invoke(...)`；不产生 span |
| 绑定 tracer · 节点 | 2 个 `Span`（开始 / 结束）+ 2 次接收端回调 |
| 绑定 tracer · helpers | 每次 2 个 `Span` + 2 次回调 |

**可测判据**：

- 对 `runtime._span_hook.Span` 与 `observability._producer.Span` 两点做构造计数；
- 未绑定路径两处计数均为 0；
- 接收端回调计数为 0；
- `import freegraph` 后 `sys.modules` 不含 L5 / L2 hook。

---

## §6 并发

| 项 | 规则 |
|---|---|
| 线程模型 | 沿用 `run_tasks_concurrently` 的线程池 + 每任务 `copy_context()` |
| 当前 span 栈 | L5 `ContextVar`；每任务独立 |
| 节点 span parent | 创建时栈顶 id；本 feature 无 run 级 span ⇒ 顶层节点 `None` |
| 跨任务父子 | **禁止**；跨任务父子数 == 0 |
| 不新增传播机制 | **MUST NOT** 另立 thread-local / 全局栈 |

---

## §7 错误与异常

| 场景 | 行为 |
|---|---|
| 节点抛异常 | 结束节点 span（同 id、`end_time`；不写 `error.type`）→ 原样重抛 |
| 模型 / 工具抛异常 | 结束子 span（同 id、`end_time`；写 `error.type = type(exc).__name__` / `_OTHER`）→ 原样重抛 |
| 接收端抛异常 | 隔离；MAY `logging.warning`；不改变执行结果 / 不吞节点异常 |
| 对象返回 awaitable | 结束当前 span（若存在；模型 / 工具 MUST 写 `error.type = "TypeError"`）→ `TypeError` |
| 形状不匹配 | **不产生**模型 / 工具 span；直接 `TypeError` |

---

## §8 禁止项（红线）

1. L2 import `freegraph.observability`。
2. L5 import `freegraph.runtime.superstep` / `_span_hook` / `_stream` / `_concurrency`。
3. 修改 `Span` 的 11 字段 / `TraceSink` / `RunConfig` / `SuperStepResult` / `PregelTask`。
4. 把 helpers / `SpanProducer` 加入 `freegraph.graph` 或 `freegraph.runtime.__all__`。
5. 读环境变量 / 发起出站 / 引入 `opentelemetry-*` / `langchain*` / `langsmith`。
6. 用 `sys.settrace` / monkeypatch 拦截任意 `.invoke`。
7. 在节点 span 上写 `error.type` / `freegraph.*` 属性。
8. 在 `Span.context` 写入任何内容。

---

## §9 原则 IV 的字段载体（输入 / 输出 / 错误）

> 宪法原则 IV 要求每次节点执行的可观测记录含节点名、输入状态、输出状态、耗时、错误。
> 该记录是**组合载体**，不是单个 `Span`。

| 字段 | 本 feature 的载体 | 既有 / 下游载体 |
|---|---|---|
| 节点名 | 节点 span `name` / `node` | `PregelTask.name` |
| 耗时 | 节点 span `start_time` / `end_time` | — |
| 输入状态 | **不写进节点 span**（Q11） | `stream_mode="values"` step 前状态 + B19F1/B20 |
| 输出状态 | **不写进节点 span**（Q11） | `updates` / `tasks` + `PregelTask.result` + B19F1/B20 |
| 错误 | **不写进节点 span**（Q12）；模型 / 工具 span 失败时 MUST 写 `error.type` | 原样抛出的异常（+ `add_note`）/ B19F1/B20；`PregelTask.error` 仅非抛出快照可见 |

**MUST**：

1. 节点 span 的 `attributes` 保持 `{}`；**MUST NOT** 为原则 IV 把输入 / 输出 / 错误塞进节点 span。
2. `stream()` 路径的输入 / 输出 MUST 能由 `values` / `updates` / `tasks` +
   `PregelTask.result` 还原；**错误** MUST 能由**原样抛出的异常**（+ `add_note`）还原；
   `PregelTask.error` **不作为失败路径载体**（SC-016）。
3. `invoke()` 路径的逐节点输入 / 输出 / 错误 MUST 由 B19F1/B20 提供等价 trace record（D-6）；
   **B19F1/B20 的 spec MUST 落成该承接并写死捕获机制**；B18F1 不声称本 feature 已闭合该路径。
4. `error.type` MUST 写在模型 / 工具失败 span 上，不是节点 span。

