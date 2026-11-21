# Contract: `SqliteTraceStore`（SQLite 后端）

**Feature**: B20F2 · **Date**: 2026-11-22 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)

> `SqliteTraceStore` 是 **L5** 的本地 trace 持久化 + 查询后端。它实现 B19F1 的 sink
> 鸭子类型接口，**不**改变 `TraceSink` 三方法协议；写侧语义与 B20F1 的
> `FileTraceStore` 一致；查询语义见 [query-api-contract.md](./query-api-contract.md)。
> **表结构 / 列名 / SQL 是内部实现细节**（C27 ⑤），本 contract 只写死对外行为。

---

## 1. 公开面

```python
class SqliteTraceStore:
    def __init__(
        self,
        database: str | os.PathLike[str],
        *,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> None: ...

    @property
    def write_errors(self) -> int: ...

    @property
    def last_error(self) -> str | None: ...

    def on_span_start(self, span: Span) -> None: ...
    def on_span_end(self, span: Span) -> None: ...
    def on_trace_record(self, record: TraceRecord) -> None: ...
    def current_span(self) -> Span | None: ...
    def query(self, query: TraceQuery | None = None) -> list[dict[str, Any]]: ...
```

| 规则 | 内容 |
|---|---|
| 注入 | `compile(tracer=SqliteTraceStore(database=...))`（B19F1 注入点） |
| `database` | 必填；`str` / `os.PathLike[str]`；单个本地 SQLite 文件路径；无默认；不展开 `~` / env |
| 不支持 | `:memory:` / SQLite URI / 网络数据库 / 连接对象注入（v1）；`:memory:` / URI ⇒ 构造时 `ValueError` |
| `on_error` | 可选；每次持久化失败调用一次；**锁外**；自身异常被吞并记日志 |
| 诊断 | `write_errors` / `last_error` 只读；实例级；跨 run 累计 |
| 回调 | `on_span_start` no-op；`on_span_end` 写 span 行；`on_trace_record` 写 record 行 |
| `current_span` | 恒 `None`（sink 不是 producer） |
| `query` | 与 `FileTraceStore.query` 同签名 / 同语义 |

**MUST NOT** 提供：`close()` / `__enter__` / `__exit__` / 上下文管理器 / 公开表名 /
列名 / SQL / 连接对象 / 第二套读取 API。

---

## 2. 构造与生命周期

| 项 | 规则 |
|---|---|
| 构造 | **零文件系统副作用**；只保存 `database` / `on_error`、初始化锁 / thread-local / 诊断 |
| 首次写行 | 惰性创建父目录（`parents=True, exist_ok=True`）、库文件、内部表 / 索引 |
| 查询 | 库不存在 ⇒ `[]`；**不**创建库 / 表 / 索引 |
| 句柄 | 每次写 / 查询短生命周期连接；`finally` 关闭；无持久连接 |
| `close()` | **不提供** |
| 上下文管理器 | **不提供** |
| 跨 run | 同一实例可直接写多次运行；无需额外清理 |

---

## 3. 写侧语义（与 B20F1 一致）

| 事件 | 行为 |
|---|---|
| `on_span_start(span)` | **no-op**；不建库 / 表 / 目录 |
| `on_span_end(span)` | 仅 `end_time` 非空时写 1 条 `kind="span"` 行（`Span` 11 字段 + `kind`）；开始快照（`end_time is None`）no-op，不建库 / 目录 / 表 |
| `on_trace_record(record)` | 写 1 条 `kind="trace_record"` 行（`to_jsonable()` 13 字段 + `kind`） |
| 行构造 | 复用 `_payloads.span_to_dict` / `record_to_dict`；字段名 / `kind` 逐字同 B20F1 |
| `run_id` 安全 | MUST 匹配 `^[A-Za-z0-9][A-Za-z0-9_-]*$`；空 / 不安全 ⇒ 诊断 + 跳过；不伪造 |
| 写入模式 | 追加；不覆盖已有数据 |
| 事务 | 每行 `INSERT` + `commit` 成功即成功；不额外 `fsync`；不重试 |
| 并发 | 每实例一把 `threading.Lock`；锁内 connect / schema / insert / commit / close；序列化 / `on_error` 锁外 |
| 跨进程 | SQLite 文件锁 + 有限 `busy_timeout`（v1 内部固定，不暴露参数） |

**失败隔离**：

| 失败点 | 处置 |
|---|---|
| payload 构造 / `json.dumps` | `Exception` 捕获 ⇒ `_report`；不写 |
| `run_id` 空 / 不安全 | `ValueError` 捕获 ⇒ `_report`；不写 |
| `mkdir` / 预创建文件 / `connect` | 捕获 ⇒ `_report` |
| `CREATE TABLE` / `INSERT` / `commit` | 捕获 ⇒ rollback / close ⇒ `_report` |
| `on_error` 抛 `Exception` | 吞并记日志；不递归 |
| `on_error` 抛 `BaseException` | **不吞** |
| 写入 `BaseException` | **不吞**；只有 `Exception` 被隔离 |

### 3.1 四路诊断

| 通道 | 形态 | 判定 |
|---|---|---|
| 计数 | `write_errors: int`（只读，初值 0，单调递增） | 失败一次 ⇒ +1 |
| 最后错误 | `last_error: str \| None` | `f"{type(exc).__name__}: {exc}"` |
| 回调 | `on_error(exc)`（锁外，最多一次/失败；重入不递归） | 提供时调用 |
| 日志 | `logging.getLogger(__name__).warning(..., exc_info=exc)` | 失败一次 ⇒ 一条 WARNING |

**不变量**：`write_errors` 只统计持久化失败；`on_error` 自身异常不增加计数；
`BaseException` 不被吞；失败不阻断图执行。

---

## 4. 内部 schema（不对外）

> **表名 / 列名 / SQL MUST NOT 作为公开 API。** 以下仅为本 feature 的实现契约，
> 供 tests / data-model 对齐；schema 变化 MUST NOT 改变对外查询语义。

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
CREATE INDEX IF NOT EXISTS idx_trace_run ON trace_entries(run_id);
CREATE INDEX IF NOT EXISTS idx_trace_thread ON trace_entries(thread_id);
CREATE INDEX IF NOT EXISTS idx_trace_node ON trace_entries(node);
CREATE INDEX IF NOT EXISTS idx_trace_span ON trace_entries(run_id, span_id);
CREATE INDEX IF NOT EXISTS idx_trace_start ON trace_entries(start_time);
```

| 列 | 语义 |
|---|---|
| `kind` | `"span"` / `"trace_record"` |
| `run_id` / `thread_id` / `node` / `checkpoint_id` | B20F1 行字段 |
| `span_id` | span 的 `id` / record 的 `span_id` |
| `start_time` | span 的 `start_time`；record 为 `NULL` |
| `payload` | B20F1 行视图的 `json.dumps(..., ensure_ascii=False)` |

**schema 版本**：v1 不做 `user_version` / 迁移；旧表缺必需列 / 类型冲突 ⇒ 查询 `[]` + WARNING，
写入按失败隔离（**MUST NOT** 自动改表 / 重建 / 删除）。**额外多出的列不视为不兼容**（读取时忽略）。

---

## 5. 查询

查询语义与 [query-api-contract.md](./query-api-contract.md) **逐字一致**；本后端特有：

| 项 | 规则 |
|---|---|
| 库不存在 | `[]` |
| 库路径是目录 / 损坏 / 非 SQLite | 抛底层异常给调用方 |
| 表不存在 | `[]` |
| 表存在但缺必需列 / 类型冲突 | `[]` + WARNING；不修改；额外多出的列忽略 |
| 单行 `payload` JSON 解码失败（含嵌套 `input_state` / `output_state` / `error`） | 跳过 + WARNING |
| 连接 | `timeout=5.0` + `PRAGMA busy_timeout=5000` + `PRAGMA query_only=ON` |
| 读锁 | 不持写入锁；未提交事务不可见 |
| SQL 下推 | v1 **不做**（正确性 / 两后端等价优先）；读全部 payload 后走 `_query.finalize` |
| 副作用 | 不建库 / 表 / 索引；不迁移 / 修复 / 删除 |

---

## 6. 权限

| 场景 | 规则 |
|---|---|
| 新建库文件 | POSIX 预创建 `os.open(..., 0o600)`；`mode & 0o077 == 0` |
| 已存在库文件 | MUST NOT 主动放宽；实现 MAY 尝试收紧到 `0o600`，失败不阻断写入 |
| 父目录 | `mkdir(parents=True, exist_ok=True)`；默认权限（受 umask）；不额外 chmod |
| SQLite 辅助文件 | 由 SQLite 管理；v1 不承诺其权限位 |
| 配置 | v1 无权限配置参数 / 无 env |
| Windows | 由平台 ACL 解释；MUST NOT 因无法设置 POSIX 权限而阻断写入 |

---

## 7. 并发 / Windows

| 项 | 规则 |
|---|---|
| 同实例多线程 | per-instance 锁串行化写；每行完整 |
| 不同实例 | MUST NOT 共享锁；各自独立 |
| 跨进程写 | SQLite 文件锁；有限 busy timeout；超时 ⇒ 写入失败隔离 |
| 并发写 + 查询 | MUST NOT 损坏数据库；查询 MUST NOT 看到未提交事务；条目 MAY 包含或跳过 |
| Windows CI | 并发写 + 查询 MUST 通过；不因文件锁差异假红；超时按既定语义处理 |
| 全局锁 | MUST NOT 使用模块级 / 进程级全局锁 |

---

## 8. 明确不做

- 公开 schema / 表名 / 列名 / SQL / 连接。
- `close()` / 上下文管理器 / 持久连接 / 连接池。
- `:memory:` / URI / 网络数据库 / 连接对象注入。
- schema 迁移 / 版本号 / 自动修复。
- 保留期 / 清理 / 轮转 / 压缩。
- OTLP / UI / Postgres / 评测（见 spec Out of Scope）。

---

## 9. 验收映射

| 判据 | 覆盖 |
|---|---|
| A5 / A6 | `SqliteTraceStore` 写 + 查询；两后端逐条等价 |
| SC-010 | 写侧同 B20F1（诊断 / 不重试 / 文件命名 / `kind`） |
| SC-011 | 持久化 / 并发写 + 查询 / Windows |
| SC-012 | 零出站 / 零 env / 零第三方；`sqlite3` 标准库 |
| SC-013 | 只读 / 容错 / 无副作用 |
| SC-014 | schema 内部；无直连公开面 |
| SC-018 | 惰性建父目录 / 库 / 表；`0o600`；已存在不放宽 |
