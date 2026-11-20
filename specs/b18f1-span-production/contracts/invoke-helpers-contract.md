# 契约：B18F1 · `invoke_model` / `invoke_tool` 调用辅助

**Feature**: `B18F1` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**状态**: Phase 1 设计契约 · **可被 `/speckit.tasks` 追溯** · **MUST NOT** 被测试解析

---

## §0 位置与公开面

| 项 | 值 |
|---|---|
| 模块 | `freegraph.observability`（L5 · 非 `freegraph.graph` 门面） |
| 符号 | `invoke_model` / `invoke_tool`（可 import；**不进** API 快照） |
| 依赖 | 标准库 + `freegraph.contracts.trace.Span`；**零 L2 import**（id 从当前节点 span 继承） |
| 公开门面 | **零新增** |
| L2 hook | `runtime._span_hook`（L2 私有；helpers **不 import**） |

> **定位**：freegraph 是**通用图框架**；模型 / 工具 span 是**可选**的可观测能力，
> 由用户**显式**调用 helpers 启用。框架**不**隐式拦截节点里的任意 `.invoke`。

---

## §1 签名（逐字冻结）

```python
def invoke_model(obj: Any, input: Any, *, call_id: str | None = None) -> Any: ...
def invoke_tool(obj: Any, args: Any, *, call_id: str | None = None) -> Any: ...
```

| 参数 | 语义 |
|---|---|
| `obj` | 鸭子类型对象；**不强制转换** |
| `input` / `args` | 原样传给 `obj.invoke(...)`；框架不解释 |
| `call_id` | **仅**工具 span 的 `gen_ai.tool.call.id`；不传给 `obj.invoke` |
| 返回 | `obj.invoke(...)` 的**原对象**结果（不包装） |
| 异常 | 原对象 / 类型 / 消息重抛（不包装） |

> **MUST NOT** 新增 `context` / `span` / `attributes` 等关键字（Q15 已定 `Span.context` 恒空；
> 额外元数据入口留给后续 feature）。

---

## §2 形状判定（Q14）

### 2.1 工具形状

```text
hasattr(obj, "name") and isinstance(obj.name, str)
and hasattr(obj, "description")
and callable(getattr(obj, "invoke", None))
```

- `description` **存在即可**；值可为任意（可为 `None` / 空串）。
- `name` **必须是 `str`**（空串仍是 `str`；空串仍视为合法工具）。
- **不** import / isinstance 检查 `langchain*` 类型。

### 2.2 模型形状

```text
callable(getattr(obj, "invoke", None)) and not <工具形状>
```

### 2.3 辅助函数名即期望层级

| 调用 | 要求 | 不满足 |
|---|---|---|
| `invoke_model(obj, ...)` | **模型形状**（callable `invoke` 且非工具形状） | `TypeError` |
| `invoke_tool(obj, ...)` | **工具形状** | `TypeError` |

- **MUST NOT** 静默把工具当模型 / 把模型当工具。
- 形状校验**与生产开关无关**：即使未绑定 tracer，也照常校验。
- `TypeError` 消息 MUST 点名辅助函数与缺失 / 冲突的形状（可读、可测试）。

### 2.4 错配用例（SC-014）

| # | 输入 | 调用 | 期望 |
|---|---|---|---|
| 1 | 工具形状对象 | `invoke_model` | `TypeError` · 模型 span 数 == 0 |
| 2 | 模型形状对象 | `invoke_tool` | `TypeError` · 工具 span 数 == 0 |
| 3 | 无 `invoke` 对象 | `invoke_model` | `TypeError` |
| 4 | 无工具形状对象 | `invoke_tool` | `TypeError` |

> 节点 span 不受影响：若错配发生在节点内，节点 span 照常存在。

---

## §3 执行流程

> **术语**：本契约的 `tracer` = `SpanProducer`（L5）；`receiver` = 接收端（`on_span_start` / `on_span_end`）。

```text
invoke_model / invoke_tool:
    1. 形状校验（§2）                      # 失败 ⇒ TypeError，零子 span
    2. tracer = current_tracer()           # L5 contextvar
    3. node_span = tracer.current_node_span() if tracer else None
    4. if tracer is None or node_span is None:
           result = obj.invoke(...)
           if isawaitable(result): raise TypeError   # Q16
           return result                    # Q13：节点外 / 未绑定 ⇒ 零 span
    5. start = tracer.make_*_span(obj, call_id)      # parent = 栈顶 id
    6. tracer.on_span_start(start)
    7. try:
           result = obj.invoke(...)
           if isawaitable(result):
               raise TypeError("v1 只支持同步 invoke")
       except BaseException as exc:
           end = tracer.finish_span(start, error_type=_error_type(exc))
           tracer.on_span_end(end)
           raise
       end = tracer.finish_span(start)
       tracer.on_span_end(end)
       return result
```

---

## §4 属性（Q9 · v1 最小集）

### 4.1 模型 span

| 键 | 值 | 条件 |
|---|---|---|
| `gen_ai.operation.name` | `"chat"` | **总是** |
| `gen_ai.request.model` | `obj.model_name` → `obj.model` | 可读且为非空 `str` |

- 读取顺序：`model_name` → `model`；只读**文档化、非私有**属性。
- 都不存在 / 非 `str` / 空串 ⇒ **省略**该键，不猜测。
- **不读**：`provider` / `_llm_type` / `usage` / `response_metadata` / `temperature` / `max_tokens` / `top_p`。

### 4.2 工具 span

| 键 | 值 | 条件 |
|---|---|---|
| `gen_ai.operation.name` | `"execute_tool"` | **总是** |
| `gen_ai.tool.name` | `obj.name` | **总是**（工具形状要求 `str`；空串也写，不省略） |
| `gen_ai.tool.call.id` | `call_id` | 显式提供且非空 |

- **不写**：`gen_ai.tool.description` / `tool.type` / `tool.call.arguments` / `tool.call.result`。

### 4.3 名称

| span | `name` |
|---|---|
| 模型 | `"chat <model>"`（有模型名）/ `"chat"`（无） |
| 工具 | `"execute_tool <tool.name>"`（空串时为 `"execute_tool "`） |

### 4.4 值类型

- 所有属性值 MUST 可被 `json.dumps` 序列化；
- 不写对象 / 异常 / `datetime` / `bytes` / 模型 / 工具实例。

---

## §5 节点外行为（Q13）

- 无活动节点 span（未在节点执行期间，或未绑定 tracer）⇒ **直接** `obj.invoke(...)`；
- **不产生** span、**不伪造** `node`、**不生成** span 专用 `run_id`；
- 形状校验与 awaitable 拒绝**仍然执行**（Q14 / Q16）。

---

## §6 异步（Q16）

- v1 **只支持同步** `invoke`；
- 调用后 `inspect.isawaitable(result)` 为真 ⇒
  1. 若存在活动 span：结束当前 span（同 id、`end_time`；MUST 写 `error.type = "TypeError"`）；
  2. 抛内置 `TypeError`；
  3. **MUST NOT** 返回 awaitable；
- **MUST NOT** 提供 `ainvoke_model` / `ainvoke_tool`；
- 异步 span 生命周期属后续 feature。

---

## §7 异常（Q12 / FR-025）

| 场景 | 行为 |
|---|---|
| `obj.invoke` 抛异常 | 模型 / 工具 span 结束 + `error.type = type(exc).__name__`（空则 `_OTHER`）；原样重抛 |
| 接收端抛异常 | 隔离；MAY `logging.warning`；不改变 helper 的返回值 / 异常 |
| 形状错配 | `TypeError`；**不产生**模型 / 工具 span |
| awaitable | `TypeError`；若已产生 span 则成对结束 |

> 节点 span 永远不写 `error.type`；节点失败通过异常本身体现。

---

## §8 返回值与对象身份

- 返回 `obj.invoke(...)` 的**原结果**（不包装、不复制、不改类型）；
- 传给 `invoke_model` / `invoke_tool` 的 `obj` **不被**替换 / 代理 / monkeypatch；
- 节点外 / 未绑定 tracer 时，返回值与直接调用 `obj.invoke(...)` **逐字相等**（SC-013）。

---

## §9 禁止项（红线）

1. 不 import `langchain*` / `langgraph*` / `langsmith` / `opentelemetry-*`。
2. 不读环境变量 / 不做网络。
3. 不隐式拦截任意 `.invoke`；只处理显式传入的对象。
4. 不修改 `Span` 字段 / `context` / 节点属性。
5. 不把 helpers 加进 `freegraph.graph` 门面。
6. 不为异步提供半成品（不返回 awaitable）。
7. 不把 `call_id` 传给 `obj.invoke`（它只用于 span 属性）。
8. 不读取 `description` / provider / usage 等未列入 Q9 的元数据。
