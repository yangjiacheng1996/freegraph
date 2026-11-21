# Contract: `TraceSink` 接入 / run scope / `current_span()`

**Feature**: B19F1 · **Date**: 2026-11-21 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)

> 本契约**只增不改**：`Span` 11 字段、`TraceSink` 3 方法、`RunConfig` 9 字段、
> `SuperStepResult` / `PregelTask` 字段、`stream()` 事件信封一律冻结。
> 唯一新增公开关键字 = `compile(*, tracer=...)`。

---

## 1. 注入点

```python
class StateGraph:
    def compile(
        self,
        checkpointer: Checkpointer | None = None,
        *,
        cache: Any = None,
        store: Store | None = None,
        interrupt_before: Any = None,
        interrupt_after: Any = None,
        debug: bool = False,
        name: str | None = None,
        transformers: Any = None,
        tracer: TraceSink | None = None,   # 本 feature 新增（keyword-only）
    ) -> CompiledGraph: ...
```

| 规则 | 内容 |
|---|---|
| **形态** | **编译期关键字**；`tracer` keyword-only |
| **默认** | 不传 / `None` ⇒ 等价于未注入 |
| **持有** | `CompiledGraph` 只**持有** sink；不构造 producer、不绑定 |
| **无参可调用** | `compile()` 仍可无参调用（宪法原则 III） |
| **唯一形态** | MUST NOT 扩 `RunConfig`、MUST NOT 给 `invoke` / `stream` 加 `tracer=` |
| **快照** | API 签名快照因新增关键字**更新（非放宽）**；`compile()` 无参断言保持 |
| **静态注解 vs 运行期最小面** | 注解仍为 `TraceSink \| None`；运行期只要求 `on_span_start` / `on_span_end`，缺 `current_span` 的 `SpanOnlySink` 属有意的鸭子类型扩展；测试用 `typing.cast` / `# type: ignore` 表达 |

---

## 2. run scope 与双绑定

```python
# src/freegraph/observability/_inject.py (L5)
@contextmanager
def trace_run_scope(tracer: TraceSink | None) -> Iterator[SpanProducer | None]:
    ...
```

| 规则 | 内容 |
|---|---|
| **有 tracer** | `producer = SpanProducer(receiver=tracer)`；进入 `bind_tracer(producer)`（L5）**与** `bind_span_tracer(producer)`（L2）；yield producer；置 `_B19F1_SCOPE_ACTIVE = True` |
| **无 tracer** | 仅在**B19F1 作用域内嵌套屏蔽**时进入 `bind_tracer(None)` + `bind_span_tracer(None)`（**屏蔽外层**）；yield `None` |
| **作用域** | 每次 `invoke()` / `stream()` 一个；结束即解绑（contextvar reset）；`_B19F1_SCOPE_ACTIVE` 用 token 恢复 |
| **同一 producer** | L2 节点接缝与 L5 `invoke_model` / `invoke_tool` 看到**同一实例** |
| **同 run id** | 同一 scope 内所有 span 共享一个 `run_id`；嵌套注入运行**各自独立**（FR-021） |

### 2.1 invoke 路径的 id

- `_stategraph.CompiledGraph.invoke`：若 `tracer is not None`，在进入 run scope 前用
  `bind_run_ids(uuid4().hex, resolve_config(config).resolved_thread_id())` **优先**建立
  **本次运行**的 id；B18F1 的 L2 `_run_graph` 绑定为 **fallback**（仅当 `_STREAM_RUN_ID`
  为空时生效）。嵌套注入运行**新 id**（不继承外层），结束恢复外层；每次注入运行 MUST
  恰发生一次有效绑定。
- `RunConfig.run_id` **忽略**（宪法 v1.15.2）。
- 未注入**且无任何外层 tracer** ⇒ 不生成 span 专用 id。

### 2.2 stream 路径的 id

- `StreamSession` 绑定 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`（零改动）。
- `trace_run_scope` 只绑定 producer；span 读取同一对 id ⇒ 与 stream 事件**同源同 id**。
- 嵌套 stream 由 `bind_stream` 的 contextvar 栈自然独立 / 恢复。

### 2.3 嵌套屏蔽（FR-021）

| 场景 | 行为 |
|---|---|
| 外层为 **B19F1 注入作用域**，内层 `compile(tracer=None)` | 内层进入 `trace_run_scope(None)` ⇒ L2 + L5 两层 hook 都置 `None` ⇒ 无 span / 无 record；`current_span()` 返回 `None` |
| 外层为 **B19F1 注入作用域**，内层 `compile(tracer=sink2)` | 内层构造自己的 producer + 独立 `run_id`；顶层节点 span `parent=None`；不挂外层 |
| 外层为 **B18F1 直接绑定**（**当前无活动 B19F1 作用域**），内层 `compile(tracer=None)` | **不触发新的屏蔽语义**；由既有 B18F1 绑定决定 span 生产（保留 B18F1 测试语义） |
| **B19F1 作用域内**另有 B18F1 直接绑定，内层 `compile(tracer=None)` | **B19F1 作用域优先**；仍进入 `trace_run_scope(None)` 屏蔽（含该直接绑定） |
| 外层无 tracer，内层 `tracer=None` | 直接跳过 run scope（零 L5 import / 零开销） |
| 同一产物重入 `invoke()` | 每次调用一个 run scope / 独立 id；结束恢复外层 |

---

## 3. `current_span()`

```python
# src/freegraph/observability/__init__.py (L5)
def current_span() -> Span | None: ...
```

| 规则 | 内容 |
|---|---|
| **返回值** | 上下文内**最内层**活动 `Span`（栈顶）；无 ⇒ `None` |
| **不抛** | 任何上下文都不抛异常 |
| **不委托** | **不**调用 sink 的 `current_span` 方法；读 `SpanProducer` 栈顶 |
| **回调内** | `on_span_start` ⇒ 新 span；`on_trace_record` ⇒ 该节点 span；`on_span_end` ⇒ 父级 / `None` |
| **导出** | 从 `freegraph.observability` 导出；**不**经 `freegraph.graph` 门面；`import freegraph` 不加载 L5 |
| **可选 sink 方法** | 注入的 sink **只需** `on_span_start` / `on_span_end`；`current_span` 可选 |

---

## 4. 回调生命周期与顺序

对每个**已产生节点 span**的任务：

```text
on_span_start(span)          # span.end_time is None；current_span() == span
node.run(...)                # 执行
on_trace_record(record)      # 可选；current_span() == span
on_span_end(end_span)        # end_span.id == span.id；current_span() == parent / None
```

| 规则 | 内容 |
|---|---|
| **成对** | start / end 按 `id` 成对；成功 / 异常 / 中断路径均成对 |
| **顺序** | **sink 实现 `on_trace_record` 时**为 `start → record → end`；未实现时为 `start → end`；MUST NOT 让 record 晚于 end |
| **record 可选** | sink 未实现 `on_trace_record` ⇒ 跳过，不报错 |
| **span 载荷** | start = `end_time is None`；end = 同 `id`、`end_time` 非空 |
| **异常路径** | record 的 `error` = 原异常；end 后原异常**原对象 / 类型 / 消息**重抛 |
| **未产生 span** | `start_node_span` 返回 `None`（如无 `run_id`）⇒ 不产 record |

---

## 5. 可选记录回调（**不是**协议成员）

```python
class MySink:                      # 结构化满足 TraceSink + 可选扩展
    def on_span_start(self, span): ...
    def on_span_end(self, span): ...
    def current_span(self): ...    # 可选（运行时只要求 start/end）
    def on_trace_record(self, record): ...   # 可选扩展
```

| 规则 | 内容 |
|---|---|
| **协议面** | `TraceSink` 仍恰 3 方法；`on_trace_record` **不计入**协议 |
| **发现方式** | `SpanProducer` 用 `getattr(receiver, "on_trace_record", None)` |
| **返回值** | 忽略 |
| **异常** | 隔离 **`Exception`**（同 FR-017）；不传播、不改变图执行、不吞节点异常；`BaseException` 不吞 |
| **不实现** | 零影响；`record 数 == 0`、`TraceRecord` 构造数 == 0、input-output 采集数 == 0 只对「未实现」的接收端成立 |

---

## 6. 零开销 / 默认关闭

| 条件 | 必须发生 | 必须不发生 |
|---|---|---|
| 未注入 + 无 B19F1 作用域 + 无 B18F1 直接绑定 | 一次廉价 contextvar 判断 | 构造 `Span` / `SpanProducer` / payload；import L5；生成 span 专用 `run_id`；读环境变量；回调 |
| `compile(tracer=None)`（顶层 / 无外层 tracer） | 同上 | 同上 |
| `compile(tracer=None)`（B19F1 作用域内嵌套） | 仅屏蔽外层 | 构造新 producer / payload；生成新 `run_id` |
| `compile(tracer=None)`（**作用域外**的 B18F1 直接绑定外层） | 保持既有继承语义 | 新的屏蔽语义 |
| 环境变量存在（`LANGSMITH_*` / `LANGCHAIN_*` / `OTEL_*`） | 行为不变 | 启用 / 禁用 / 改变任何行为 |
| 注入但从未运行 | 仅持有 sink | 任何 span / 回调 / id |

---

## 7. 分层与登记例外

| 依赖 | 方向 | 处置 |
|---|---|---|
| `_stategraph.py`（L3）→ `observability._inject`（L5） | **反向**（L3 → L5） | **R-1** · ARCH-1 例外；**2026-11-21 已批准**；仅 tracer 接线路径；局部 import；更新 `立项书 §5.1` / `spec §5` / layer-registry + G25 |
| `observability._inject`（L5）→ `runtime._span_hook`（L2） | 向下（允许） | **R-2** · ARCH-3 例外；只允许双绑定 `bind_span_tracer`；**不读** `_stream_context`（id 由 start `Span` 继承）；不新增公开符号。**B8F2 的 R-6 已收窄**：L2 `_run_round` 读取 stream id，B19F1 不直接读取 |
| `observability` 纯模块（`_record` / `_time` / `_producer` / `_invoke`） | L5 → L1 | 保持「只 import 标准库 + L1」；B18F1 断言**拆分而不删** |
| `freegraph.graph` 门面 | — | **零改动**；不得 import L5 |
| `import freegraph` | — | 只加载 `freegraph`；不加载 L5 / `_stategraph` |

> 红线：R-1 / R-2 **只覆盖 tracer 接线**，MUST NOT 扩展为任意 L3 → L5 / L5 → L2 私有依赖。

---

## 8. 冻结面

| 冻结面 | 本 feature |
|---|---|
| `Span` 11 字段 | 零改动（原样消费） |
| `TraceSink` 3 方法 | 零改动（可选回调不计入） |
| `RunConfig` 9 字段 | 零改动（不装 tracer） |
| `SuperStepResult` / `PregelTask` | 零改动 |
| `stream()` 事件信封 | 零改动（trace 不塞入） |
| `freegraph.graph.__all__` | 仍 8 |
| `freegraph.contracts.__all__` | 仍 22 |
| `freegraph.runtime.__all__` | 不变（新 helper 私有） |
| `StateGraph.compile` | **只增** `tracer=`（keyword-only） |
