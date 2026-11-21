# Data Model: B20F2 · Trace 查询 API + SQLite 后端

**Date**: 2026-11-22 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

> 本文件描述**读取侧的数据形态、查询流水线与两个后端的数据模型**。
> `Span` 的字段权威仍是 B2F1；`TraceRecord` 的字段权威仍是 B19F1；
> `TraceQuery` 的字段权威仍是 B2F1；本 feature **只消费**，不重定义。
>
> **不变量**：`Span`（11 字段）、`TraceSink`（3 方法）、`TraceRecord`（13 字段）、
> `TraceQuery`（5 字段）、`RunConfig`（9 字段）、`SuperStepResult` / `PregelTask`
> **逐字不改**。B20F1 的 JSONL 写侧行结构 / 文件命名 / `kind` / `0o600` / 锁 / 四路诊断
> **逐字不改**。

---

## 1. 实体总览

| 实体 | 层 | 归属 | 说明 |
|---|---|---|---|
| `TraceQuery` | L1 | B2F1（冻结） | 5 字段查询请求；全可空、可组合 |
| 查询结果条目 | 对外数据形态 | **本 feature** | B20F1 行视图的纯 `dict`；`kind="span"` / `"trace_record"` |
| `FileTraceStore` | L5 | B20F1（写入）/ **本 feature（读取）** | JSONL 后端；本 feature 增加 `query()` |
| `SqliteTraceStore` | L5 | **本 feature** | SQLite 写入 + 查询后端 |
| `_query` | L5 内部 | **本 feature** | 共享查询引擎：校验 / 时间 / 行校验 / 过滤 / 排序 |
| `_payloads` | L5 内部 | **本 feature** | 共享行构造：`span_to_dict` / `record_to_dict` |
| SQLite 表 `trace_entries` | 内部持久化形态 | **本 feature** | schema 不对外；`payload` 存 B20F1 行视图 |
| `Span` | L1 | B2F1（冻结） | 11 字段；查询返回其落盘视图 |
| `TraceRecord` | L5 | B19F1（交付） | 13 字段；`to_jsonable()` 是唯一稳定视图 |
| 诊断面 | L5 | B20F1（`FileTraceStore`）/ **本 feature（`SqliteTraceStore`）** | `write_errors` / `last_error` / `on_error` / 日志 |

---

## 2. `TraceQuery`（L1 · 冻结 · 原样消费）

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class TraceQuery:
    run_id: str | None = None
    thread_id: str | None = None
    node: str | None = None
    start_time: str | None = None
    end_time: str | None = None
```

| 字段 | 类型 | 匹配规则 |
|---|---|---|
| `run_id` | `str \| None` | 精确相等；`None` 不启用 |
| `thread_id` | `str \| None` | 精确相等；`None` 不启用 |
| `node` | `str \| None` | 精确相等（大小写敏感、非子串）；**全部匹配**含子 span / record |
| `start_time` | `str \| None` | 闭区间下界（含）；UTC ISO-8601；解析到纳秒 |
| `end_time` | `str \| None` | 闭区间上界（含）；UTC ISO-8601；解析到纳秒 |

**校验**：

- 5 字段运行时值 MUST 是 `str` 或 `None`；否则读取前 `TypeError`。
- 合法字符串但不可解析 ⇒ `ValueError`。
- `start_time > end_time` ⇒ 返回 `[]`（不抛错、不交换）。
- `None` 是唯一「不启用」值；空字符串 `""` 是字面值。
- **v1 不增加** `checkpoint_id` / `task_id` / `superstep` / `kind` / `name` / `parent`
  / 错误状态过滤器；这些只作返回字段。

---

## 3. 查询结果条目（对外数据形态）

### 3.1 `kind="span"`（12 键 = `kind` + 11 字段）

```json
{
  "kind": "span",
  "id": "<span-id>",
  "name": "<name>",
  "attributes": {},
  "parent": null,
  "start_time": "2026-11-22T12:00:00.000000000+00:00",
  "end_time": "2026-11-22T12:00:00.000120000+00:00",
  "context": {},
  "thread_id": "t-1",
  "run_id": "r-1",
  "node": "a",
  "checkpoint_id": null
}
```

### 3.2 `kind="trace_record"`（14 键 = `kind` + 13 字段）

```json
{
  "kind": "trace_record",
  "span_id": "<span-id>",
  "task_id": "a",
  "run_id": "r-1",
  "thread_id": "t-1",
  "checkpoint_id": null,
  "node": "a",
  "superstep": 0,
  "triggers": [["e", "__start__"]],
  "concurrency_group": ["a"],
  "barrier_groups": [],
  "input_state": {"x": 0},
  "output_state": {"x": 1},
  "error": null
}
```

### 3.3 行校验规则（`_query.normalize_row`）

| `kind` | 必需字段 | 类型规则 |
|---|---|---|
| `span` | `kind` / `id` / `name` / `attributes` / `parent` / `start_time` / `end_time` / `context` / `thread_id` / `run_id` / `node` / `checkpoint_id` | `id` / `name` / `start_time` / `run_id` / `node` = `str`；`attributes` / `context` = `dict`；`parent` / `end_time` / `thread_id` / `checkpoint_id` = `str \| None` |
| `trace_record` | `kind` / `span_id` / `task_id` / `run_id` / `thread_id` / `checkpoint_id` / `node` / `superstep` / `triggers` / `concurrency_group` / `barrier_groups` / `input_state` / `output_state` / `error` | `span_id` / `task_id` / `run_id` / `node` = `str`；`thread_id` / `checkpoint_id` = `str \| None`；`superstep` = `int`（`type(x) is int`，排除 `bool`）；`triggers` / `concurrency_group` / `barrier_groups` = `list`；`error` = `dict \| None`（`type` / `message` = `str`）；`input_state` / `output_state` = 任意 JSON 值 |

**规则**：

- 未知 `kind` / 缺必需字段 / 类型不符 ⇒ 返回 `None`（调用方跳过 + WARNING）。
- 额外未知字段 ⇒ **丢弃**；返回只含上表字段。
- 返回的 dict 是新对象；嵌套值来自 `json.loads` / 行构造，调用方修改不影响存储。
- 结果整体 MUST 可 `json.dumps`；MUST NOT 含异常 / 类 / 函数 / 句柄 / dataclass 实例。

---

## 4. `FileTraceStore` 查询扩展

### 4.1 公开面（B20F1 写侧 + 本 feature 读取）

```python
class FileTraceStore:
    def __init__(self, directory, *, on_error=None) -> None: ...
    @property
    def write_errors(self) -> int: ...
    @property
    def last_error(self) -> str | None: ...
    def on_span_start(self, span: Span) -> None: ...      # no-op
    def on_span_end(self, span: Span) -> None: ...        # 写 span 行
    def on_trace_record(self, record: TraceRecord) -> None: ...  # 写 record 行
    def current_span(self) -> Span | None: ...            # 恒 None
    def query(self, query: TraceQuery | None = None) -> list[dict[str, Any]]: ...
```

**写侧不变**：文件命名、`kind` / 字段名、`0o600`、per-instance 锁、四路诊断、
逐行短生命周期、不重试、无 `close()` / 上下文管理器 —— 全部逐字保留。

### 4.2 查询扫描规则

| 项 | 规则 |
|---|---|
| 目录不存在 | `[]` |
| 目录存在但不是目录 | 抛 `NotADirectoryError`（底层异常交调用方） |
| 候选文件名 | `^trace-([A-Za-z0-9][A-Za-z0-9_-]*)\.jsonl$`；不匹配 ⇒ 跳过 + WARNING |
| 候选符号链接 | 跳过 + WARNING；MUST NOT 跟随 |
| `run_id` 过滤 | 不安全 / 非 allowlist ⇒ `[]`；安全 ⇒ 只读对应文件（存在时） |
| 行解析 | `json.loads` 失败 ⇒ 跳过 + WARNING |
| 行校验 | `normalize_row` 返回 `None` ⇒ 跳过 + WARNING |
| 单文件 I/O 失败 | 跳过 + WARNING；全部普通候选不可读 ⇒ 抛错 |
| 写入锁 | 查询**不获取**写入锁；可能读到半行 ⇒ 按坏行跳过 |
| 副作用 | 不建文件 / 目录 / 表；不截断 / 删除 / 改写 |

### 4.3 查询流水线

```text
query(q)
  ├─ q = normalize_query(q)                    # TypeError / 时间 ValueError
  ├─ if q.run_id unsafe: return []
  ├─ if directory missing: return []
  ├─ if directory is not a dir: raise
  ├─ candidates = allowlisted regular files (no symlink)
  ├─ for file in candidates:
  │    ├─ if q.run_id set and file.run_id != q.run_id: continue
  │    ├─ read lines; json.loads; normalize_row
  │    └─ bad line / unknown kind / incomplete ⇒ WARNING + skip
  ├─ finalize(rows, q)                         # filter + effective time + sort
  └─ return list[dict]
```

---

## 5. `SqliteTraceStore`（L5 · 新实体）

### 5.1 构造

```python
SqliteTraceStore(
    database: str | os.PathLike[str],
    *,
    on_error: Callable[[BaseException], None] | None = None,
) -> None
```

| 参数 | 类型 | 必填 | 语义 |
|---|---|---|---|
| `database` | `str \| os.PathLike[str]` | ✅ | 单个 SQLite 文件路径；无默认；不展开 `~` / env；不支持 URI / `:memory:`（⇒ 构造时 `ValueError`） |
| `on_error` | `Callable[[BaseException], None] \| None` | ❌ | 每次持久化失败调用一次（锁外）；自身异常被吞并记日志 |

**构造期零副作用**：只保存 `database` / `on_error`、创建锁 / thread-local、初始化诊断。

### 5.2 公开面

| 成员 | 类型 | 语义 |
|---|---|---|
| `write_errors` | `int`（只读属性） | 持久化失败次数；读时持锁 |
| `last_error` | `str \| None`（只读属性） | 最后一次失败；`f"{type(exc).__name__}: {exc}"` |
| `on_span_start(span)` | `None` | **no-op** |
| `on_span_end(span)` | `None` | 写一条 span 行 |
| `on_trace_record(record)` | `None` | 写一条 record 行 |
| `current_span()` | `Span \| None` | 恒 `None` |
| `query(query=None)` | `list[dict]` | 同 `FileTraceStore.query` 语义 |

**MUST NOT** 提供：`close()` / `__enter__` / `__exit__` / 上下文管理器 / 公开表名 /
列名 / SQL / 连接对象。

### 5.3 写盘状态机

```text
on_span_end(span) / on_trace_record(record)
  ├─ validate run_id (allowlist) + build payload (_payloads)
  ├─ json.dumps(payload, ensure_ascii=False)             # 锁外
  ├─ acquire(instance lock)
  │    ├─ path.parent.mkdir(parents=True, exist_ok=True)
  │    ├─ if path missing: os.open(path, O_CREAT|O_EXCL, 0o600); close
  │    ├─ conn = sqlite3.connect(path, timeout=5.0)
  │    ├─ PRAGMA busy_timeout=5000
  │    ├─ CREATE TABLE IF NOT EXISTS trace_entries (...)
  │    ├─ CREATE INDEX IF NOT EXISTS ...
  │    ├─ INSERT INTO trace_entries (...) VALUES (...)
  │    ├─ conn.commit()
  │    └─ conn.close()
  └─ release(instance lock)
```

| 失败点 | 处置 |
|---|---|
| payload / `run_id` / `json.dumps` | `Exception` 捕获 ⇒ `_report`；不写 |
| `mkdir` / 预创建文件 / `connect` | 捕获 ⇒ `_report` |
| `CREATE TABLE` / `INSERT` / `commit` | 捕获 ⇒ rollback / close ⇒ `_report` |
| `on_error` 抛 `Exception` | 吞并记日志；不递归 |
| `BaseException` | **不吞**（传播） |

**不重试**：同一行失败后不再尝试；后续行继续。

### 5.4 内部 SQLite 表（不对外）

```sql
CREATE TABLE IF NOT EXISTS trace_entries (
    seq           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind          TEXT NOT NULL,
    run_id        TEXT NOT NULL,
    thread_id     TEXT,
    node          TEXT NOT NULL,
    checkpoint_id TEXT,
    span_id       TEXT NOT NULL,
    start_time    TEXT,
    payload       TEXT NOT NULL
);
```

| 列 | 语义 |
|---|---|
| `seq` | 内部插入序（仅调试 / 稳定读取；查询排序由 `_query.finalize` 决定） |
| `kind` | `"span"` / `"trace_record"` |
| `run_id` | 运行标识 |
| `thread_id` | 会话标识（可空） |
| `node` | 节点名 |
| `checkpoint_id` | 检查点标识（可空；**不是**过滤器） |
| `span_id` | span 的 `id` / record 的 `span_id` |
| `start_time` | span 的 `start_time`；record 为 `NULL` |
| `payload` | B20F1 行视图的 JSON 文本 |

**索引**：`run_id` / `thread_id` / `node` / `(run_id, span_id)` / `start_time`。
**schema 版本**：v1 不做 `user_version` / 迁移；缺必需列 / 类型冲突 ⇒ 查询 `[]` + WARNING，
写入失败隔离；额外多出的列忽略、不视为不兼容。

### 5.5 查询流水线

```text
query(q)
  ├─ q = normalize_query(q)                    # TypeError / ValueError
  ├─ if database missing: return []
  ├─ conn = sqlite3.connect(path, timeout=5.0)
  │    ├─ PRAGMA busy_timeout=5000
  │    └─ PRAGMA query_only=ON
  ├─ validate table columns via PRAGMA table_info(trace_entries)
  │    ├─ table missing ⇒ []
  │    └─ missing required column / type conflict ⇒ WARNING + []
  │       (extra columns are tolerated and ignored)
  ├─ SELECT payload FROM trace_entries
  ├─ for payload: json.loads; normalize_row
  │    └─ decode / validate failure（含嵌套 input_state / output_state / error）
  │       ⇒ WARNING + skip
  ├─ finalize(rows, q)
  ├─ close conn
  └─ return list[dict]
```

- 查询**不**创建库 / 表 / 索引；不迁移；不修改数据。
- `sqlite3.DatabaseError`（损坏 / 非 SQLite / I/O）⇒ 异常交调用方。
- 查询不持写入锁；并发写入中的未提交行不会被看到。

---

## 6. 过滤 / 有效起始时刻 / 排序（共享语义）

### 6.1 过滤

```text
row matches q  ⇔
  (q.run_id is None or row.run_id == q.run_id)
  and (q.thread_id is None or row.thread_id == q.thread_id)
  and (q.node is None or row.node == q.node)
  and (time bounds are None or effective_time(row) in [start, end])
```

- `run_id` / `thread_id` / `node` 精确相等；大小写敏感。
- `node` 过滤返回该节点自身 span、其内部 `node` 同名的模型 / 工具 span、以及 record。
- 时间过滤按**有效起始时刻**；无有效起始时刻的 record 在任何时间界存在时不匹配。

### 6.2 有效起始时刻

| 条目 | 有效起始时刻 |
|---|---|
| `kind="span"` | 该 span 的 `start_time` → `parse_instant_ns` |
| `kind="trace_record"` | 同一 `run_id` + `(span_id == id)` 的 span 的 `start_time` |
| record 找不到关联 span | **无时刻** |

- 关联 MUST 在 `(run_id, span_id)` ↔ `(run_id, id)` 内；MUST NOT 跨 run。
- 「可见」= 满足同一查询过滤、且被本次查询读取到的 span。

### 6.3 排序

```text
timed   = rows with effective_time not None
untimed = rows with effective_time None

timed.sort(key=(start_ns, run_id, kind_rank, stable_id))
  kind_rank: trace_record=0, span=1
  stable_id: record.span_id / span.id

untimed.sort(key=(run_id, superstep, task_id, span_id))

result = timed + untimed
```

- `start_ns` 是 UTC 纳秒整数；**不**用 `datetime` 微秒。
- 完全相同的重复行相对顺序 MAY 任意；不影响其它条目。
- 两后端 MUST 给出相同排序；**完全相同的重复行跨后端按多重集合比较**（不比较相对顺序）。

---

## 7. 并发 / 锁 / 生命周期

| 项 | `FileTraceStore` | `SqliteTraceStore` |
|---|---|---|
| 锁粒度 | 每实例一把 `threading.Lock`（写 + 诊断） | 每实例一把 `threading.Lock`（写 + 诊断） |
| 查询持锁 | **否** | **否** |
| 写锁内 | 单行 append / flush / close + 诊断 | connect / schema / insert / commit / close + 诊断 |
| 写锁外 | JSON 序列化、`on_error` | JSON 序列化、`on_error` |
| 跨实例 | 不共享锁 | 不共享锁 |
| 跨进程 | v1 不承诺事务性 | SQLite 文件锁 + 有限 busy timeout |
| 句柄 | 每行短生命周期；无持久句柄 | 每操作短生命周期连接；无持久连接 |
| `close()` | **不提供** | **不提供** |
| 上下文管理器 | **不提供** | **不提供** |

---

## 8. 权限

| 场景 | `FileTraceStore` | `SqliteTraceStore` |
|---|---|---|
| 新建文件 | POSIX `0o600`（B20F1） | 预创建 `0o600`；SQLite 辅助文件由 SQLite 管理 |
| 已存在文件 | 不放宽；v1 不额外 chmod | 不放宽；MAY 尝试收紧；失败不阻断 |
| 父目录 | `mkdir(parents=True, exist_ok=True)`；默认权限 | 同左 |
| 配置 | v1 无参数 / 无 env | v1 无参数 / 无 env |
| Windows | 平台 ACL；不因权限失败阻断 | 平台 ACL；不因权限失败阻断 |

---

## 9. 与 `Span` / `TraceRecord` 的映射

### 9.1 `Span`（L1 · 11 字段）

- `span_to_dict(span)` = `{"kind": "span", ...11 fields}`。
- `attributes` / `context` = `dict(...)` 浅拷贝。
- 开始快照（`end_time=None`）不落盘；查询只应看到结束快照。
- 查询返回的是落盘视图，不重建 `Span` 对象。

### 9.2 `TraceRecord`（L5 · 13 字段）

- `record_to_dict(record)` = `{"kind": "trace_record", **record.to_jsonable()}`。
- `error` 为 `{"type", "message"}` / `None`；`input_state` / `output_state` 已 `json_safe`。
- 查询返回的是落盘视图，不重建 `TraceRecord` 对象。

---

## 10. 不变量汇总（用于测试）

- **I-01**：`query(None)` ≡ `query(TraceQuery())`；返回全部匹配条目。
- **I-02**：四类过滤精确匹配；非 `None` 条件 AND 组合。
- **I-03**：`node` 过滤包含该节点自身 span、内部模型 / 工具 span、record。
- **I-04**：时间窗闭区间；按有效起始时刻；倒置 ⇒ `[]`；非法串 ⇒ `ValueError`。
- **I-05**：有效起始时刻：span 用 `start_time`；record 用同 run 关联 span 的 `start_time`；
  无关联 ⇒ 无时刻、排除出任何时间窗、排最后。
- **I-06**：排序：有时刻在前；`(start_ns, run_id, kind_rank, stable_id)`；
  无时刻 record 按 `(run_id, superstep, task_id, span_id)`。
- **I-07**：结果只含 `kind="span"` / `"trace_record"`；未知 kind 跳过。
- **I-08**：span 行 11/11 + `kind`；record 行 13/13 + `kind`；额外字段丢弃。
- **I-09**：结果纯数据；`json.dumps(result)` 成功；元素是独立副本。
- **I-10**：两后端对同一事件流、同一查询逐条相等（条目数 / 字段 / 排序）；
  **完全相同的重复行按多重集合比较**（不比较相对顺序）。
- **I-11**：查询只读：不建文件 / 目录 / 表；不截断 / 删除 / 改写；前后哈希不变。
- **I-12**：坏行 / 未知 kind / 字段残缺 / 非白名单 / 符号链接 ⇒ 跳过 + WARNING。
- **I-13**：目录是普通文件 / 全部候选不可读 / SQLite 损坏 ⇒ 抛错给调用方。
- **I-14**：请求类型错误 ⇒ `TypeError`；坏时间串 ⇒ `ValueError`；均读取前完成。
- **I-15**：SQLite 写侧同 B20F1：四路诊断 / 不重试 / `BaseException` 不吞 / 每实例锁。
- **I-16**：SQLite 惰性建父目录 / 库 / 表；构造与查询零副作用；新建库 `0o600`；
  已存在不放宽。
- **I-17**：SQLite 并发写 + 查询不损坏库；未提交事务不可见；Windows 用例通过。
- **I-18**：`FileTraceStore` 写侧行为逐字不变；只新增 `query()`。
- **I-19**：`SqliteTraceStore` 不暴露表名 / 列名 / SQL / 连接；schema 是内部细节。
- **I-20**：`import freegraph` 不加载 L5；`SqliteTraceStore` 不进 `freegraph.graph`。

---

## 11. 明确不做（数据模型边界）

- OTLP 导出 / 远端后端 —— B21F1。
- 前端 / UI / Studio —— v2 / B26；Studio 不直连 SQLite / JSONL。
- 本地 Agent Server —— v2 / D8。
- Postgres 后端 —— v2。
- 保留期 / 清理 / 轮转 / 压缩 —— v1 不做。
- `checkpoint_id` / `task_id` / `superstep` 过滤器 —— v1 不支持。
- 分页 / 上限 / `limit` / `offset` —— v1 不提供。
- schema 迁移 / `user_version` —— v1 不做。
- 评测 / 数据集 —— 永不做。
