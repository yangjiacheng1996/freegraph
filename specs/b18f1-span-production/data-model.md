# 数据模型（Data Model）—— B18F1 的 Span 生产

**Feature**: B18F1 · Span 数据类生产（节点 / 工具 / 模型三级 span）

**Date**: 2026-11-20 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> 本文件描述**生产侧的数据形态与生命周期**。`Span` 的字段面权威仍是 B2F1 的
> `specs/b2f1-contracts-protocols/contracts/public-api.md` §1.2 / §1.3；
> 本 feature **MUST NOT** 增删 / 改名 / 改类型 / 改缺省。

---

## 1. 实体总览

| 实体 | 语义 | 所有者 | 是否新增 |
|---|---|---|---|
| **`Span`** | 可观测事件载体（11 字段 · 不可变 · 字段经 `asdict` 后 JSON 可序列化） | B2F1（L1） | 否（只构造） |
| **节点 span** | 一次节点任务执行的定格 | L2 `_span_hook` | 生产行为新增 |
| **模型 span** | 一次 `invoke_model` 调用的定格 | L5 `SpanProducer` | 新增 |
| **工具 span** | 一次 `invoke_tool` 调用的定格 | L5 `SpanProducer` | 新增 |
| **`SpanProducer`（= tracer）** | 当前 span 栈 / 父子关系 / 接收端转发 | L5 `observability/_producer.py` | 新增 |
| **`_SpanFrame`** | 栈帧（`span` + `kind`） | L5 `_producer.py` | 新增（私有） |
| **接收端（receiver）** | 鸭子类型 `on_span_start` / `on_span_end` | 用户 / 测试 / B19F1 | 新增（协议由鸭子类型表达） |
| **运行上下文** | `run_id` / `thread_id` / `node` / `checkpoint_id` | L2 `_stream_context` + L2 hook | 复用 + 一次绑定扩展 |

---

## 2. `Span`（B2F1 冻结 · 零改动）

| 字段 | 类型 | 缺省 | 本 feature 的填法 |
|---|---|---|---|
| `id` | `str` | — | `uuid.uuid4().hex`（标准库） |
| `name` | `str` | — | 节点名 / `chat <model>` / `execute_tool <tool>` |
| `attributes` | `Mapping[str, Any]` | `{}` | 节点空映射；模型 / 工具按 Q9 最小集 |
| `parent` | `str \| None` | `None` | 当前栈顶 span 的 `id`；顶层节点 `None` |
| `start_time` | `str` | — | UTC ISO-8601（9 位小数） |
| `end_time` | `str \| None` | `None` | 开始时 `None`；结束时填值（严格 > `start_time`） |
| `context` | `Mapping[str, Any]` | `{}` | **v1 恒空映射**（Q15） |
| `thread_id` | `str \| None` | `None` | `RunConfig.resolved_thread_id()` |
| `run_id` | `str` | — | 运行时生成 · 单次运行一个 · 非空 |
| `node` | `str` | — | 所属节点内部名（模型 / 工具 span 也填所在节点） |
| `checkpoint_id` | `str \| None` | `None` | 节点 span 取运行期值（v1 `None`）；模型 / 工具 span **从节点 span 继承**；B14F1 后续补节点 span |

**不变量**（来自 B2F1 + 本 spec）：

1. `frozen=True` / `slots=True` / `kw_only=True`；构造后不可改。
2. `attributes` / `context` 浅拷贝为自身新映射。
3. 开始快照 `end_time is None`；结束快照 `end_time` 非空；二者 `id` 相同。
4. 开始快照**不被事后改写**（结束用**新实例**）。
5. `dataclasses.asdict(span)` 可被标准库 `json.dumps` 序列化；`Span` 对象本身不是 JSON 编码器直接可序列化的类型。
6. `run_id` 为空 ⇒ 实现缺陷；`checkpoint_id` 可为 `None`。

---

## 3. 三种生产形态

### 3.1 节点 span

```text
Span(
  id=<uuid>,
  name=<node>,                 # 节点内部名，与 stream()/PregelTask.name 一致
  attributes={},               # 恒空（Q11）
  parent=<当前栈顶 id | None>,
  start_time=<UTC ISO-8601>,
  end_time=None,               # 开始时
  context={},                  # 恒空（Q15）
  thread_id=<resolved_thread_id>,
  run_id=<non-empty>,
  node=<node>,
  checkpoint_id=<运行期值 | None>,  # v1 为 None
)
```

- **产生点**：`runtime/superstep.py:1361-1368` 的 `_run_round._bind._inner`。
- **开始**：调用 `fn()` 前；`parent = tracer.current_span_id()`。
- **结束**：`fn()` 返回 / 抛异常后；构造同 `id`、已填 `end_time` 的新 `Span`。
- **异常**：结束 span 不写 `error.type`（Q12），然后原样重抛。
- **并发**：每个任务线程的栈独立；顶层的 `parent` 为 `None`。

### 3.2 模型 span

```text
Span(
  id=<uuid>,
  name="chat <model>" | "chat",
  attributes={
    "gen_ai.operation.name": "chat",
    "gen_ai.request.model": <model_name or model>,   # 可读且非空时才写
  },
  parent=<当前栈顶 id>,
  start_time=<UTC ISO-8601>,
  end_time=None,               # 开始时
  context={},
  thread_id=<从当前节点 span 继承>,
  run_id=<从当前节点 span 继承>,
  node=<所属节点名>,
  checkpoint_id=<从当前节点 span 继承>,  # v1 为 None
)
```

- **产生点**：`invoke_model(obj, input, *, call_id=None)`。
- **要求**：`obj` 有 callable `invoke` 且**非工具形状**；否则 `TypeError`（Q14）。
- **结果**：`result = obj.invoke(input)`；若 `inspect.isawaitable(result)` ⇒ 结束 span +
  `TypeError`（Q16）；否则结束 span，原样返回 `result`。
- **异常**：结束 span + `error.type = type(exc).__name__`（或 `_OTHER`），原样重抛。
- **节点外**：无活动节点 span ⇒ 校验通过后直接 `obj.invoke(input)`，**不产生 span**（Q13）。

### 3.3 工具 span

```text
Span(
  id=<uuid>,
  name="execute_tool <tool.name>",
  attributes={
    "gen_ai.operation.name": "execute_tool",
    "gen_ai.tool.name": <tool.name>,
    "gen_ai.tool.call.id": <call_id>,   # 仅显式提供时
  },
  parent=<当前栈顶 id>,
  start_time=<UTC ISO-8601>,
  end_time=None,
  context={},
  thread_id=<从当前节点 span 继承>,
  run_id=<从当前节点 span 继承>,
  node=<所属节点名>,
  checkpoint_id=<从当前节点 span 继承>,  # v1 为 None
)
```

- **产生点**：`invoke_tool(obj, args, *, call_id=None)`。
- **要求**：`obj` 有 `name`（`str`）+ `description` + callable `invoke`；否则 `TypeError`（Q14）。
- **结果 / 异常 / awaitable / 节点外**：同模型 span。
- **`gen_ai.tool.call.id`**：只从显式 `call_id` 参数取；没传 / 空 ⇒ 省略，不猜。

---

## 4. `SpanProducer` 与当前 span 栈

### 4.1 结构

```text
_SpanFrame = (span: Span, kind: Literal["node", "model", "tool"])
SpanProducer:
    _receiver: <on_span_start/on_span_end> | None
    _stack: ContextVar[tuple[_SpanFrame, ...]]  # 运行内 / 每任务独立
```

### 4.2 方法

| 方法 | 语义 |
|---|---|
| `on_span_start(span)` | 推断 `kind`（按 `gen_ai.operation.name` 是否存在 / 值），入栈，转发接收端 |
| `on_span_end(span)` | 按 `id` 出栈（校验栈顶），转发接收端 |
| `current_span_id()` | 栈顶 `id` 或 `None` |
| `current_node_span()` | 最近的 `kind == "node"` 帧（供 helpers 取 `node` / `run_id` / `thread_id`） |
| `make_model_span(obj)` / `make_tool_span(obj, call_id)` | 构造开始 `Span`（L5） |
| `finish_span(start, error_type=None)` | 构造结束 `Span`（同 `id`、`end_time`） |

> **调用职责**：L2 `_span_hook.start_node_span` MUST 在构造开始 Span 后调用 `tracer.on_span_start(start)`；
> `end_node_span` MUST 在构造结束 Span 后调用 `tracer.on_span_end(end)`。`on_span_start` / `on_span_end`
> 是唯一的入栈 / 出栈 + 接收端转发点；不调用它们会导致子 span 丢失 parent。

### 4.3 `kind` 的推断

| `attributes` | `kind` |
|---|---|
| 空 | **node** |
| `gen_ai.operation.name == "execute_tool"` | **tool** |
| 其他含 `gen_ai.operation.name` | **model** |

> 这是 B18F1 生产侧的**封闭约定**；`Span` 的 11 字段不变。B19F1 的 `TraceSink`
> 只收 `Span`，不需要知道 `kind`。

### 4.4 接收端

- **鸭子类型**：`on_span_start(span)` / `on_span_end(span)`；
- B19F1 的 `TraceSink` 有这两个方法（另有 `current_span()`，本 feature 不调用）；
- 接收端抛异常 ⇒ 隔离；MAY `logging.warning`；不传播 / 不改变执行（FR-025）；
- 无接收端 ⇒ 生产者仍可维护栈，但不转发；生产语义上「未绑定 tracer」不应绑定生产者。

---

## 5. 生命周期状态机

```text
                 bind tracer (L2 + L5)
idle ─────────────────────────────────────► ready
                                              │
                    node start               │
                    (L2, tracer != None)     ▼
                                             node-active
                                              │      │
                       invoke_model/tool      │      │  node return / raise
                       (L5, node-active)      ▼      ▼
                                          child-active   finish node
                                              │             │
                       child return / raise  │             ▼
                                              └────────► node-finish
                                                             │
                                                             ▼
                                                           idle
```

**规则**：

1. `tracer is None` ⇒ 不进入 `ready`，节点直接执行；零 `Span` 分配。
2. 节点 span 是 `node-active` 的根；模型 / 工具 span 只能在 `node-active` 内产生。
3. 嵌套：模型 → 工具 → 模型；每个子 span 的 `parent` = 入栈前的栈顶。
4. 子 span 结束 ⇒ 栈恢复到父；父的 `id` 不变。
5. 异常 ⇒ 先结束当前 span（同 id、`end_time`），再原样抛出；栈仍恢复到父。
6. 未绑定 tracer 时调用 `invoke_model` / `invoke_tool` ⇒ 校验通过后直接调用，不产生 span。
7. **作用域结束** ⇒ 回到 `idle`；之后不再产生 span；再次进入作用域 ⇒ 新的一次运行 / 新 `run_id`（FR-003 / T059）。

---

## 6. 关联键与运行上下文

| 键 | 来源 | 生命周期 | 备注 |
|---|---|---|---|
| `run_id` | 运行时 `uuid4().hex` | 一次运行一个 | `stream()` 复用 `_STREAM_RUN_ID`；`invoke()` 由 `run_graph` 绑定一次；L5 从节点 span 继承 |
| `thread_id` | `RunConfig.resolved_thread_id()` | 一次运行 | 可为 `None`；L5 从节点 span 继承 |
| `node` | 当前节点帧的 `Span.node` | 每个节点 | 模型 / 工具 span 填**所属节点** |
| `checkpoint_id` | 节点 span 的 `checkpoint_id` | 一次运行 | 节点 span 接受运行期值（v1 `None`）；模型 / 工具 span 从节点 span 继承；B14F1 后续补节点 span |

**同源不变量**：

- `stream()` 的事件与 span 的 `run_id` / `thread_id` **逐字相同**；
- `RunConfig.run_id` **MUST 被忽略**；
- 不同运行 `run_id` **不同**；
- 未绑定 tracer ⇒ **不生成** span 专用 `run_id`（`stream()` 既有事件 `run_id` 不属 span 生产）。

---

## 7. 属性矩阵（v1）

### 7.1 模型 span（只写两项）

| 键 | 值 | 条件 |
|---|---|---|
| `gen_ai.operation.name` | `chat` | 总是 |
| `gen_ai.request.model` | `model_name` → `model` | 可读且非空 |

### 7.2 工具 span（只写三项）

| 键 | 值 | 条件 |
|---|---|---|
| `gen_ai.operation.name` | `execute_tool` | 总是 |
| `gen_ai.tool.name` | `obj.name` | 总是（工具形状要求 `str`；空串也写，不省略） |
| `gen_ai.tool.call.id` | 显式 `call_id` | 调用方提供时 |

### 7.3 节点 span

| 键 | 值 | 条件 |
|---|---|---|
| — | 空映射 | **总是**（Q11） |

### 7.4 通用

| 键 | 值 | 条件 |
|---|---|---|
| `error.type` | `type(exc).__name__` / `_OTHER` | **模型 / 工具 span 失败时 MUST 写**（Q12） |

**禁止**：`gen_ai.system`、`gen_ai.provider.name`、`gen_ai.usage.*`、`gen_ai.response.*`、
`gen_ai.request.temperature` / `max_tokens` / `top_p`、`gen_ai.tool.description` /
`tool.type`、`gen_ai.conversation.id`、任何无命名空间私有键。

---

## 8. 并发模型

| 机制 | 位置 | 语义 |
|---|---|---|
| 任务线程池 | `runtime/_concurrency.py:185-230` | 每任务一个 `copy_context()` |
| 当前 span 栈 | L5 `ContextVar` | 每任务独立；跨任务不可见 |
| 节点接缝 | `runtime/superstep.py:1361-1368` | 每任务一次 `bind_current_task` / `bind_task` |
| 父子关系 | L5 栈顶 | 只在本任务内生效 |

**不变量**：

- 同一 super-step N 个并发节点 ⇒ N 个节点 span，**顶层节点** `parent` 均为 `None`（本 feature 无 run 级 span）；
- 每个节点的模型 / 工具 span 的 `parent` 落在**本任务的节点 span 子树内**（直接子 span = 节点 span id；嵌套子 span = 本任务内内层 span id）；
- 跨任务父子数 == 0；
- 不新增第二套上下文传播机制（沿用 B8F2 D-3）。

---

## 9. 零开销模型

| 状态 | 节点接缝 | `run_id` | `Span` 分配 | 接收端回调 |
|---|---|---|---|---|
| 未绑定 tracer | 一次 `current_span_tracer()` + `is None` | 不生成 span 专用 id | 0 | 0 |
| 绑定 tracer（节点） | 开始 / 结束各一次 | 复用 / 绑定一次 | 2（开始 + 结束） | 2 |
| 绑定 tracer（模型 / 工具） | 辅助函数内 | 复用 | 2 / 次 | 2 / 次 |
| 未绑定 tracer + 节点外 helper | 校验后直接调用 | 不生成 | 0 | 0 |

**判定**：计数夹具对 `_span_hook.Span` / `_producer.Span` 两点计数；
未绑定路径两处都必须为 0。

---

## 10. 验证矩阵（FR / SC 落点）

| FR | 数据面 / 不变量 | SC |
|---|---|---|
| FR-001 | `Span` 11 字段不变 | SC-002 / SC-008 / SC-012 |
| FR-002 | 未绑定 ⇒ 零 span / 零回调 / 不生成 span 专用 id | SC-003 / SC-004 / SC-012 |
| FR-003 | 显式 tracer · run-scoped · 覆盖 invoke / stream | SC-003 / SC-006 |
| FR-004 | 每节点任务一个节点 span | SC-002 / SC-009 / SC-010 |
| FR-005 | helpers 产生独立子 span | SC-002 / SC-009 / SC-010 / SC-013 |
| FR-006 | 形状 / 类型 / `TypeError` | SC-001 / SC-009 / SC-013 / SC-014 |
| FR-007 | `parent` = 父 id 字符串 | SC-002 / SC-010 |
| FR-008 | `id` 唯一 | SC-002 / SC-005 |
| FR-009 | 起止时间 / 严格正耗时 | SC-005 / SC-008 |
| FR-010 | 异常成对 + 原样重抛 | SC-007 |
| FR-011 | 四项关联键 | SC-006 / SC-008 |
| FR-012 | 与 stream 同源 | SC-006 |
| FR-013 | 属性允许清单 / 最小集 | SC-001 |
| FR-014 | JSON 可序列化 | SC-008 |
| FR-015 | span 名格式 | SC-009 |
| FR-016 | operation / model 名读取 | SC-001 / SC-009 |
| FR-017 | 不采集内容 | SC-001 |
| FR-018 | `error.type` 仅模型 / 工具失败 | SC-001 / SC-007 |
| FR-019 | 依赖闭包为空 | SC-004 |
| FR-020 | 零 env / 零出站 | SC-004 |
| FR-021 | 层纪律 | SC-004 / SC-012 |
| FR-022 | 公开面零扩张 | SC-012 |
| FR-023 | `context` 恒空 | SC-011 |
| FR-024 | 并发隔离 | SC-010 |
| FR-025 | 接收端异常隔离 | SC-007 |
| FR-026 | 不实现下游能力 | SC-012 |
| FR-027 | B19F1 可消费 | SC-002 / SC-008 |
| FR-028 | 同步 / awaitable | SC-015 |
| FR-029 | 原则 IV 组合载体 / 下游承接 | SC-016 |

---

## 11. JSON 形态示例

`dataclasses.asdict(span)` 的形态：

```json
{
  "id": "9f2c...",
  "name": "execute_tool multiply",
  "attributes": {
    "gen_ai.operation.name": "execute_tool",
    "gen_ai.tool.name": "multiply"
  },
  "parent": "1a7e...",
  "start_time": "2026-11-20T12:34:56.123456789+00:00",
  "end_time": "2026-11-20T12:34:56.123457001+00:00",
  "context": {},
  "thread_id": "thread-1",
  "run_id": "b7d1...",
  "node": "tool_node",
  "checkpoint_id": null
}
```

> 结束 span 的 `id` / `parent` / `name` / `attributes` / `context` / `thread_id` /
> `run_id` / `node` / `checkpoint_id` 与开始 span 相同；仅 `end_time` 填值（失败时
> 模型 / 工具 span 的 `attributes` 多一个 `error.type`）。

---

## 12. 原则 IV 的字段载体（输入 / 输出 / 错误）

| 原则 IV 字段 | B18F1 的载体 | 既有 / 下游载体 |
|---|---|---|
| 节点名 | 节点 span `name` / `node` | `PregelTask.name` |
| 耗时 | 节点 span `start_time` / `end_time` | — |
| 输入状态 | **不写进节点 span**（Q11） | `stream_mode="values"` step 前状态 + B19F1/B20 |
| 输出状态 | **不写进节点 span**（Q11） | `updates` / `tasks` + `PregelTask.result` + B19F1/B20 |
| 错误 | **不写进节点 span**（Q12）；模型 / 工具 span 失败时 MUST 写 `error.type` | 原样抛出的异常（+ `add_note`）/ B19F1/B20；`PregelTask.error` 仅非抛出快照可见 |

**不变量**：

- 节点 span `attributes == {}`；不因原则 IV 扩属性；
- `stream()` 路径的节点名 / 耗时由 span 承担；输入 / 输出由既有事件 + `PregelTask.result` 还原；错误由**原样抛出的异常**（+ `add_note`）还原（SC-016）；`PregelTask.error` 不作为失败路径载体；
- `invoke()` 路径的逐节点三项归 B19F1/B20（D-6）；**B19F1/B20 的 spec MUST 落成该承接并写死捕获机制**；
- 节点 span 的 `context` 仍恒空（Q15）。

