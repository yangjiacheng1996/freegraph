# Contract: JSONL 记录格式（`span` / `trace_record`）

**Feature**: B20F1 · **Date**: 2026-11-21 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)

> 文件格式是 C27 ⑤ 的**内部实现细节**；本 contract 将其写死以保证：
> ① 每行可被 `json.loads` 独立解析；② 字段与 `Span` / `TraceRecord` 逐字对齐；
> ③ 失败时不留下半行。B20F2 查询实现 MUST 按此读取；Studio MUST NOT 直连。

---

## 1. 文件与行

| 项 | 规则 |
|---|---|
| 文件 | `<directory>/trace-<run_id>.jsonl` |
| 粒度 | 每个 `run_id` 一个文件 |
| 行 | 一行一个 JSON 对象；无头部 / 尾部 / 注释 / 空行 |
| 换行 | `\n`（LF），最后一行也以 `\n` 结束 |
| 编码 | UTF-8（无 BOM）；`json.dumps(..., ensure_ascii=False)` |
| 键序 | `kind` 第一；其余按 `Span` 字段声明序 / `to_jsonable()` 顺序 |
| `kind` | **唯一新增字段**；只允许 `"span"` / `"trace_record"` |
| 分隔符 | `json.dumps` 默认分隔符（空格可读；不缩进） |
| 非有限浮点 | 遵循 Python `json` 的 `NaN` / `Infinity`；`json.loads` 可解析（不额外改写） |

---

## 2. `kind="span"` 行

**写入时机**：`on_span_end(span)`；开始快照（`end_time is None`）**不写**。

```json
{"kind": "span", "id": "6f1c...", "name": "a", "attributes": {}, "parent": null, "start_time": "2026-11-21T12:00:00.000000000+00:00", "end_time": "2026-11-21T12:00:00.000120000+00:00", "context": {}, "thread_id": "t-1", "run_id": "9b2e...", "node": "a", "checkpoint_id": null}
```

| 字段 | 类型 | 必填 | 来源 | 规则 |
|---|---|---|---|---|
| `kind` | `str` | ✅ | 本 feature | 恒 `"span"` |
| `id` | `str` | ✅ | `Span.id` | 逐字；span 唯一标识 |
| `name` | `str` | ✅ | `Span.name` | 逐字 |
| `attributes` | `object` | ✅ | `dict(Span.attributes)` | 浅拷贝；节点 span 通常 `{}` |
| `parent` | `str \| null` | ✅ | `Span.parent` | 父 span id；顶层 `null` |
| `start_time` | `str` | ✅ | `Span.start_time` | UTC ISO-8601 |
| `end_time` | `str` | ✅ | `Span.end_time` | 结束时非空 |
| `context` | `object` | ✅ | `dict(Span.context)` | 浅拷贝；v1 通常 `{}` |
| `thread_id` | `str \| null` | ✅ | `Span.thread_id` | 可空 |
| `run_id` | `str` | ✅ | `Span.run_id` | 非空；文件名使用 |
| `node` | `str` | ✅ | `Span.node` | 节点内部名 |
| `checkpoint_id` | `str \| null` | ✅ | `Span.checkpoint_id` | 可空 |

**不变量**：

- 11 字段 **全部存在**；字段名逐字等于 `Span` 定义。
- 结束快照 `end_time` 非空；开始快照不落盘。
- 模型 / 工具 span 也落盘；`parent` 指向所在节点 span 的 `id`。
- `attributes` / `context` 不承载 `TraceRecord` 字段。

---

## 3. `kind="trace_record"` 行

**写入时机**：`on_trace_record(record)`；字段 = `record.to_jsonable()` + `kind`。

```json
{"kind": "trace_record", "span_id": "6f1c...", "task_id": "a", "run_id": "9b2e...", "thread_id": "t-1", "checkpoint_id": null, "node": "a", "superstep": 0, "triggers": [["e", "__start__"]], "concurrency_group": ["a"], "barrier_groups": [], "input_state": {"x": 0}, "output_state": {"x": 1}, "error": null}
```

| 字段 | 类型 | 必填 | 来源 | 规则 |
|---|---|---|---|---|
| `kind` | `str` | ✅ | 本 feature | 恒 `"trace_record"` |
| `span_id` | `str` | ✅ | `TraceRecord.span_id` | == 节点 span 的 `id` |
| `task_id` | `str` | ✅ | `TraceRecord.task_id` | 标准 = 节点名；fan-out = `节点名:TaskId` |
| `run_id` | `str` | ✅ | `TraceRecord.run_id` | 非空 |
| `thread_id` | `str \| null` | ✅ | `TraceRecord.thread_id` | 可空 |
| `checkpoint_id` | `str \| null` | ✅ | `TraceRecord.checkpoint_id` | 可空 |
| `node` | `str` | ✅ | `TraceRecord.node` | 逐字 |
| `superstep` | `int` | ✅ | `TraceRecord.superstep` | 0 起 |
| `triggers` | `array` | ✅ | `to_jsonable()` | 原样；元素为数组 |
| `concurrency_group` | `array[str]` | ✅ | `to_jsonable()` | 原样 |
| `barrier_groups` | `array[array[str]]` | ✅ | `to_jsonable()` | 无屏障 `[]` |
| `input_state` | `any` | ✅ | `to_jsonable()` | 已 `json_safe` |
| `output_state` | `any` | ✅ | `to_jsonable()` | 已 `json_safe`；节点原始返回值 |
| `error` | `object \| null` | ✅ | `to_jsonable()` | `{"type": 类名, "message": str(exc)}` 或 `null` |

**不变量**：

- 13 字段 **全部存在**；字段名逐字等于 `TraceRecord` / `to_jsonable()`。
- `error` **MUST NOT** 是原异常对象 / `repr` / 堆栈；只允许 `{type, message}` 或 `null`。
- `input_state` / `output_state` **MUST NOT** 被 B20 重新降级 / 改名；原样持久化。
- 记录 **MUST NOT** 塞进 `Span.attributes` / `Span.context`。

---

## 4. 行序 / 关联

```text
on_span_start(span)        # 不写
on_trace_record(record)    # 写 trace_record 行
on_span_end(span)          # 写 span 行
```

| 规则 | 内容 |
|---|---|
| 行序 | 回调到达顺序；**不排序 / 不聚合 / 不重写** |
| 同节点 | record 行在节点 span 行之前 |
| 并发 | 到达顺序可不稳定；确定性由 `triggers` / `concurrency_group` **字段内**顺序承载 |
| 关联 | `trace_record.span_id` == 同文件 span 行的 `id` |
| 计数 | **当经 B19F1 注入且 `on_trace_record` 可用时**：record 行数 == 节点任务数；span 行数 == 全部已结束 span 数（节点 + 模型 + 工具）。**接收端不含 `on_trace_record`**（span-only 适配器 / 纯 span sink）时允许 span-only（record 行数 == 0）；`FileTraceStore` 本身始终写 record |
| 模型 / 工具 | 只有 span 行；无 record 行 |
| 错误 | 节点 record 的 `error` 为 `{type, message}`；span 行仍完整 |
| 无事件 | store 未收到任何回调（v1 `StateGraph` 不允许无节点的图）⇒ 不写文件、不报错 |

---

## 5. 编码 / 转义

| 输入 | 输出 |
|---|---|
| 中文 / Unicode | 原样（`ensure_ascii=False`），UTF-8 |
| 换行 / 引号 / 控制字符 | `json.dumps` 转义；对象仍只占一行 |
| `None` / `bool` / `int` / `float` / `str` | 原样 |
| `dict` / `list` / `tuple`（record 的 input/output） | B19F1 `json_safe` 已处理（tuple → list） |
| 非有限浮点 `nan` / `inf` | Python `json` 的 `NaN` / `Infinity` 标记；`json.loads` 可解析 |
| 不可序列化对象（外部构造） | `json.dumps` 抛 `TypeError` ⇒ 写入失败（不写半行） |

---

## 6. 失败时不留半行

| 场景 | 规则 |
|---|---|
| 写前 | 记录 `path.stat().st_size`（或 0） |
| 写入失败 | `os.truncate(path, before)`；保留之前的完整行 |
| 截断失败 | 只记日志 / 诊断；不重试；运行继续 |
| 后续行 | 仍可尝试写入 |

---

## 7. 示例（最小两节点图）

```text
trace-<run_id>.jsonl
{"kind": "trace_record", "span_id": "...a", "task_id": "a", ..., "node": "a", "superstep": 0, ...}
{"kind": "span", "id": "...a", "name": "a", ..., "node": "a", ...}
{"kind": "trace_record", "span_id": "...b", "task_id": "b", ..., "node": "b", "superstep": 1, ...}
{"kind": "span", "id": "...b", "name": "b", ..., "node": "b", ...}
```

> 实际字段顺序 / 值是示例；验收以字段名 / 类型 / 关联键为准。

---

## 8. 验收判据

| 判据 | 对应 |
|---|---|
| 每行 `json.loads` 成功 | SC-001 / A3 |
| span 11 字段 / record 13 字段 | SC-002 |
| 每行含 `run_id` / `thread_id` / `node` / `checkpoint_id` | SC-002 / A3 |
| `kind` 只允许两个值 | SC-010 |
| UTF-8 / LF / 无头部 / 无空行 | SC-010 |
| record 在 span 前 / 不排序 | SC-008 / SC-009 |
| 失败无半行 | SC-004 / SC-019 |
