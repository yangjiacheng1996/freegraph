# Data Model: B20F1 · 本地 Trace 存储：JSONL 文件后端（零依赖）

**Date**: 2026-11-21 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

> 本文件描述**写入侧的数据形态与生命周期**。`Span` 的字段权威仍是 B2F1；`TraceRecord`
> 的字段权威仍是 B19F1；本 feature **只消费**，不重定义、不扩字段。
>
> **不变量**：`Span`（11 字段 · B2F1）、`TraceSink`（3 方法 · B2F1）、
> `TraceRecord`（13 字段 · B19F1）、`RunConfig`（9 字段 · B1F1）、
> `SuperStepResult` / `PregelTask`（B7F1 / B12F1）**逐字不改**。

---

## 1. 实体总览

| 实体 | 层 | 归属 | 说明 |
|---|---|---|---|
| `FileTraceStore` | L5 | **本 feature** | JSONL 文件后端 / sink 实现；写侧唯一入口 |
| `Span` | L1 | B2F1（冻结） | 11 字段；本 feature **原样消费** |
| `TraceRecord` | L5 | B19F1（交付） | 13 字段；本 feature **原样消费** `to_jsonable()` |
| JSONL 行 | 内部持久化形态 | **本 feature** | `kind="span"` / `kind="trace_record"` 的单个 JSON 对象 |
| Run 文件 | 内部 | **本 feature** | `<directory>/trace-<run_id>.jsonl`，每次运行一个 |
| 诊断面 | L5 | **本 feature** | `write_errors` / `last_error` / 可选 `on_error` / 日志 |

---

## 2. `FileTraceStore`（L5 · 新实体）

**形态**：普通类（**不是** dataclass；持有锁 / 可变诊断 / 无对象引用字段进 L1）。
`__slots__` 固定内部字段；公开面只有构造、3 个 sink 回调 + `current_span`、
两个只读诊断属性。

### 2.1 构造

```python
FileTraceStore(
    directory: str | os.PathLike[str],
    *,
    on_error: Callable[[BaseException], None] | None = None,
) -> None
```

| 参数 | 类型 | 必填 | 语义 |
|---|---|---|---|
| `directory` | `str \| os.PathLike[str]` | ✅ | 存储目录；按传入值构造 `pathlib.Path`；**不做** `expanduser` / `expandvars` / env 解析 |
| `on_error` | `Callable[[BaseException], None] \| None` | ❌ | 每次持久化失败时调用一次（锁外）；自身异常被吞并记日志 |

**构造期零副作用**：只保存 `directory` / `on_error`、创建锁 / thread-local、初始化
诊断；**MUST NOT** 访问文件系统 / 创建目录 / 读环境变量。

### 2.2 内部字段（`__slots__`）

| 字段 | 类型 | 语义 |
|---|---|---|
| `_directory` | `Path` | 存储目录（未解析 / 未创建） |
| `_on_error` | `Callable[[BaseException], None] \| None` | 可选诊断回调 |
| `_lock` | `threading.Lock` | **实例级**写入 / 诊断锁 |
| `_local` | `threading.local` | `on_error` 重入标记（`in_on_error`） |
| `_write_errors` | `int` | 持久化失败计数（初值 0，单调递增） |
| `_last_error` | `str \| None` | 最后一次持久化失败的 `Type: message` |

### 2.3 公开面

| 成员 | 类型 | 语义 |
|---|---|---|
| `write_errors` | `int`（只读属性） | 持久化失败次数；读时持锁 |
| `last_error` | `str \| None`（只读属性） | 最后一次失败；格式 `f"{type(exc).__name__}: {exc}"` |
| `on_span_start(span)` | `None` | **no-op**；不写盘 / 不建目录 |
| `on_span_end(span)` | `None` | 写一条 `kind="span"` 行 |
| `on_trace_record(record)` | `None` | 写一条 `kind="trace_record"` 行 |
| `current_span()` | `Span \| None` | 恒 `None`（它是 sink，不是 producer） |

**MUST NOT** 提供：`close()` / `__enter__` / `__exit__` / 任意上下文管理器 /
查询方法（`query` / `search` / `read` 等；归 B20F2）。

> **span-only 说明**：`FileTraceStore` 始终实现 `on_trace_record`，因此它本身**不**是
> span-only sink。需要「只落 span」时 MUST 用**仅转发 `on_span_start` / `on_span_end`
> 并补 `current_span_id()` 的适配器**绑定 B18F1；`FileTraceStore` 的公开面不新增
> `current_span_id()`。

### 2.4 与 B19F1 的关系

- `FileTraceStore` 通过 `getattr(receiver, "on_trace_record", None)` 被 B19F1 识别为
  「想要 record」的接收端；收到的是 `TraceRecord` 实例。
- `on_span_start` / `on_span_end` 收到的是 B18F1 / B19F1 的 `Span` 快照。
- `current_span()` 只是为满足静态 `TraceSink` 形态；运行期最小面仍是 start / end。
- **不**改变 `TraceSink` 三方法协议；**不**把 record 塞进 `Span`。

---

## 3. JSONL 行（内部持久化形态）

### 3.1 span 行

```json
{"kind": "span", "id": "<span-id>", "name": "<name>", "attributes": {}, "parent": null, "start_time": "<ISO-8601>", "end_time": "<ISO-8601>", "context": {}, "thread_id": "<tid>", "run_id": "<rid>", "node": "<node>", "checkpoint_id": null}
```

| 字段 | 类型 | 来源 | 规则 |
|---|---|---|---|
| `kind` | `str` | 本 feature | 恒 `"span"`（唯一新增字段） |
| `id` | `str` | `Span.id` | 逐字 |
| `name` | `str` | `Span.name` | 逐字 |
| `attributes` | `dict` | `dict(Span.attributes)` | 浅拷贝为 dict |
| `parent` | `str \| None` | `Span.parent` | 逐字 |
| `start_time` | `str` | `Span.start_time` | 逐字 |
| `end_time` | `str` | `Span.end_time` | 结束回调时非空 |
| `context` | `dict` | `dict(Span.context)` | 浅拷贝为 dict |
| `thread_id` | `str \| None` | `Span.thread_id` | 可空 |
| `run_id` | `str` | `Span.run_id` | 非空；用于文件名 |
| `node` | `str` | `Span.node` | 逐字 |
| `checkpoint_id` | `str \| None` | `Span.checkpoint_id` | 可空 |

**写入时机**：只在 `on_span_end` 写一次；开始快照（`end_time is None`）**不写**。

### 3.2 trace 记录行

```json
{"kind": "trace_record", "span_id": "<span-id>", "task_id": "<task-id>", "run_id": "<rid>", "thread_id": "<tid>", "checkpoint_id": null, "node": "<node>", "superstep": 0, "triggers": [["e", "a"]], "concurrency_group": ["b"], "barrier_groups": [], "input_state": {}, "output_state": {}, "error": null}
```

| 字段 | 类型 | 来源 | 规则 |
|---|---|---|---|
| `kind` | `str` | 本 feature | 恒 `"trace_record"`（唯一新增字段） |
| `span_id` | `str` | `TraceRecord.span_id` | == 节点 span 的 `id` |
| `task_id` | `str` | `TraceRecord.task_id` | 标准 = 节点名；fan-out = `节点名:TaskId` |
| `run_id` | `str` | `TraceRecord.run_id` | 非空；用于文件名 |
| `thread_id` | `str \| None` | `TraceRecord.thread_id` | 可空 |
| `checkpoint_id` | `str \| None` | `TraceRecord.checkpoint_id` | 可空 |
| `node` | `str` | `TraceRecord.node` | 逐字 |
| `superstep` | `int` | `TraceRecord.superstep` | 0 起 |
| `triggers` | `list[list]` | `to_jsonable()` | 原样；确定性顺序由 B19F1 保证 |
| `concurrency_group` | `list[str]` | `to_jsonable()` | 原样 |
| `barrier_groups` | `list[list[str]]` | `to_jsonable()` | 原样；无则 `[]` |
| `input_state` | `Any` | `to_jsonable()` | 已 `json_safe` |
| `output_state` | `Any` | `to_jsonable()` | 已 `json_safe`；节点原始返回值 |
| `error` | `dict \| None` | `to_jsonable()` | `{"type": 类名, "message": str(exc)}` 或 `null` |

**写入时机**：只在 `on_trace_record` 写一次；`kind` 是唯一新增字段，其余字段名
**MUST NOT** 改名 / 重新定义。

### 3.3 行序 / 关联

| 规则 | 内容 |
|---|---|
| 行序 | B19F1 回调到达顺序；**不排序 / 不聚合 / 不重写** |
| 同节点顺序 | `on_span_start`（不写）→ `on_trace_record`（record 行）→ `on_span_end`（span 行） |
| 关联 | `trace_record.span_id` == 同文件 span 行的 `id` |
| 计数 | **当经 B19F1 注入且 `on_trace_record` 可用时**：`trace_record` 行数 == 节点任务数；`span` 行数 == 全部已结束 span 数（节点 + 模型 + 工具）。**接收端不含 `on_trace_record`**（span-only 适配器 / 纯 span sink）时允许 span-only（`trace_record` 行数 == 0）；`FileTraceStore` 本身始终写 record |
| 并发 | 到达顺序可不稳定；确定性由 `triggers` / `concurrency_group` **字段内**顺序承载 |
| 无事件 | store 未收到任何回调（v1 `StateGraph` 不允许无节点的图）⇒ 不写文件、不报错 |

---

## 4. Run 文件命名与路径安全

| 项 | 规则 |
|---|---|
| 文件名 | `trace-<run_id>.jsonl` |
| `run_id` 安全 | MUST 匹配 `^[A-Za-z0-9][A-Za-z0-9_-]*$`（**无点号**）；含任意 `.`（含 `..`）或路径分隔符 ⇒ 记诊断、跳过该行 |
| 空 `run_id` | 拒绝；不写文件；不伪造新 id |
| 目录 | `<directory>`；相对路径按传入值在写入时解析；不展开 `~` / `$HOME` |
| 目录创建 | 惰性：第一次真正写行时 `mkdir(parents=True, exist_ok=True)` |
| 写入模式 | 追加（`append`）；同名文件续写，不截断 |
| 文件权限 | POSIX 新建 `0o600`；`umask` 只能收紧；已存在文件不放宽 |
| 编码 | UTF-8（无 BOM）；`\n`（LF）；`json.dumps(..., ensure_ascii=False)` |
| 头部 | 无头部 / 尾部 / 注释 / 空行 |

**目录权限**：spec 未锁定；本 plan 使用 `Path.mkdir` 的默认权限（受 `umask` 约束），
**不**额外 `chmod` 目录。文件权限仍由 `os.open(..., 0o600)` 保证。

---

## 5. 写盘状态机

### 5.1 正常路径

```text
on_span_end(span) / on_trace_record(record)
  ├─ 构造 payload dict（kind + 字段）
  │    ├─ span：手工 11 字段；attributes/context = dict(...)
  │    └─ record：record.to_jsonable()
  ├─ 校验 run_id（非空 + 安全 allowlist）
  ├─ json.dumps(payload, ensure_ascii=False) + "\n"   # 锁外
  ├─ acquire(instance lock)
  │    ├─ path = directory / f"trace-{run_id}.jsonl"
  │    ├─ path.parent.mkdir(parents=True, exist_ok=True)
  │    ├─ before = path.stat().st_size if path.exists() else 0
  │    ├─ fd = os.open(path, O_WRONLY|O_APPEND|O_CREAT, 0o600)
  │    ├─ handle = os.fdopen(fd, "a", encoding="utf-8", newline="\n")
  │    ├─ handle.write(line); handle.flush()
  │    └─ handle.close()
  └─ release(instance lock)
```

### 5.2 失败路径

| 失败点 | 处置 |
|---|---|
| payload 构造 / `to_jsonable()` / `json.dumps` | `Exception` 捕获 ⇒ 不写文件 ⇒ `_report(exc)` |
| `run_id` 空 / 不安全 | 抛 `ValueError` ⇒ 捕获 ⇒ `_report`；不建目录 / 不写 |
| `mkdir` 失败 | 捕获 ⇒ `_report`；不写 |
| `path.stat` / `os.open` 失败 | 捕获 ⇒ `_report`；不写 |
| `write` / `flush` / `close` 失败 | 捕获 ⇒ 锁内 `os.truncate(path, before)`（best-effort）⇒ `_report` |
| 截断失败 | 记日志（`logging.WARNING`）；不重试；运行继续 |
| `on_error` 抛 `Exception` | 捕获 ⇒ `logging.WARNING`；不递归 |
| `on_error` 抛 `BaseException` | **不吞**（`KeyboardInterrupt` / `SystemExit` 传播） |
| 写入 `BaseException` | **不吞**；只有 `Exception` 被隔离 |

> **不重试**：同一行失败后**不再尝试**；失败行丢弃；后续行继续尝试。
> **不留半行**：`before` 是写前偏移；失败时截断回该偏移；已存在的完整行不受影响。

### 5.3 诊断更新

```text
_report(exc):
  message = f"{type(exc).__name__}: {exc}"
  with lock:
      _write_errors += 1
      _last_error = message
  logger.warning("trace write failed: %s", message, exc_info=exc)
  if on_error is None or local.in_on_error:
      return
  local.in_on_error = True
  try:
      on_error(exc)          # 锁外
  except Exception:
      logger.warning("trace on_error failed", exc_info=True)
  finally:
      local.in_on_error = False
```

**不变量**：

- `write_errors` 单调递增；初值 0；跨 run 累计（实例级，不按 run 重置）。
- `last_error` 只保留最后一次；失败后非空。
- `on_error` 每次失败最多调用一次；锁外；重入时不再调用（防递归）。
- `write_errors` 只统计**持久化失败**；`on_error` 自身异常不增加计数。
- `BaseException` 不被吞。

---

## 6. 并发 / 锁 / 生命周期

| 项 | 规则 |
|---|---|
| 锁粒度 | **每个 `FileTraceStore` 实例一把 `threading.Lock`** |
| 不共享 | 不同实例 MUST NOT 共享锁；MUST NOT 使用模块级 / 进程级全局锁 |
| 不建锁表 | MUST NOT 使用「每个 run 文件一把锁」的锁表 |
| 锁内 | 单行写入临界区（记偏移 → 追加 → `flush` → 关闭）+ 诊断更新 |
| 锁外 | JSON 序列化、`on_error` 回调 |
| 同实例多线程 | MUST 串行；每行完整、字节不交错 |
| 跨实例 | 互不阻塞；各自锁计数独立 |
| 跨进程 | v1 不承诺事务性；B20F2 SQLite 场景另议 |
| 句柄生命周期 | 每行独立 `open → append → flush → close`；无持久句柄 / `close()` / 上下文管理器 |
| 回调返回后 | MUST 不留下打开的 trace 文件句柄；Windows 上可立即 rename / delete |

---

## 7. 权限（POSIX）

| 场景 | 规则 |
|---|---|
| 新建文件 | `os.open(..., 0o600)`；实测 `mode & 0o077 == 0`；`umask` 只能收紧 |
| 已存在文件 | MUST NOT 主动放宽；v1 **不**额外 `chmod`（spec 的 MAY 不实现） |
| 权限配置 | v1 **无**参数 / 无 env / 无配置文件 |
| Windows | 由平台 ACL 解释；MUST NOT 因无法设置 POSIX 权限而阻断写入 |
| 目录 | 默认 `mkdir` 权限（受 umask）；不额外 `chmod` |

---

## 8. 与 `Span` / `TraceRecord` 的字段映射

### 8.1 `Span`（L1 · 11 字段）

```
id, name, attributes, parent, start_time, end_time, context,
thread_id, run_id, node, checkpoint_id
```

- span 行 = `{kind: "span", **手工 11 字段}`。
- **不**用 `dataclasses.asdict`（避免深拷贝 / 额外失败面）。
- `attributes` / `context` = `dict(...)` 浅拷贝。
- 开始快照（`end_time=None`）不落盘；结束快照落盘。

### 8.2 `TraceRecord`（L5 · 13 字段）

```
span_id, task_id, run_id, thread_id, checkpoint_id, node, superstep,
triggers, concurrency_group, barrier_groups, input_state, output_state, error
```

- record 行 = `{kind: "trace_record", **record.to_jsonable()}`。
- `to_jsonable()` 已把 `error` 转成 `{"type", "message"}` / `None`；
  `input_state` / `output_state` 已是 `json_safe` 视图。
- **不**重新降级 / **不**改名 / **不**从 `PregelTask` / `SuperStepResult` 重新猜。

---

## 9. 不变量汇总（用于测试）

- **I-01**：每个 `run_id` 一个 `trace-<run_id>.jsonl`；文件内 `run_id` 一致。
- **I-02**：每行一个 JSON 对象；`json.loads` 成功；无空行 / 多行对象 / 尾随垃圾。
- **I-03**：`kind` 只允许 `"span"` / `"trace_record"`。
- **I-04**：span 行 11/11 字段；record 行 13/13 字段；字段名逐字一致。
- **I-05**：每行含 `run_id` / `thread_id` / `node` / `checkpoint_id`（C23）。
- **I-06**：span 行只在 `on_span_end` 出现；开始回调不写盘。
- **I-07**：同节点 record 行在 span 行之前；行序 = 回调到达顺序。
- **I-08**：**当经 B19F1 注入且 `on_trace_record` 可用时**，`trace_record.span_id` 在同文件有 `id` 相等的 span 行；接收端不含 `on_trace_record`（span-only 适配器 / 纯 span sink）时允许 span-only；`FileTraceStore` 本身始终写 record。
- **I-09**：失败不阻断；`write_errors > 0` / `last_error` 非空 / `on_error` / WARNING。
- **I-10**：失败不重试；失败行丢弃；不留半行（截断）。
- **I-11**：每行 `flush` 即成功；逐行 `fsync` 调用数 == 0。
- **I-12**：POSIX 新建文件 `mode & 0o077 == 0`。
- **I-13**：无 `close` / `__enter__` / `__exit__`；回调返回后无残留句柄。
- **I-14**：每实例一把锁；不同实例不共享；`on_error` 锁外 / 重入不死锁。
- **I-15**：未注入 / 只构造 / env 变量 ⇒ 零文件 / 零目录 / 零副作用。

---

## 10. 明确不做（数据模型边界）

- 查询 API / `TraceQuery` 过滤 / 结果集合 —— B20F2。
- SQLite 表 / `sqlite3` —— B20F2。
- OTLP 导出 / 远端后端 —— B21F1。
- 前端 / UI / Studio —— v2 / B26；Studio 不直连 JSONL。
- 保留期 / 清理 / 轮转 / 压缩 —— v1 不做。
- 跨进程并发事务性 —— v1 不承诺。
- 评测 / 数据集 —— 永不做。
