# Contract · `SqliteSaver`（L4 公开面）

**Feature**: B15F1 · **Date**: 2026-11-22 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)
**Upstream**: `langgraph-checkpoint-sqlite 3.1.1`（MIT · uv 缓存）· `langgraph 1.2.11`

> 本 contract 冻结 **L4 `freegraph.persistence.SqliteSaver`** 的公开面与存储 / 并发 / 失败语义。
> ⚠️ 同步 saver 的存储 / 连接 / WAL / setup 代码**改编自** `langgraph-checkpoint-sqlite 3.1.1`（MIT）
> ⇒ `THIRD_PARTY_NOTICES` §1 必须登记；运行时依赖仍为零。
> 读侧 / 写侧关键字与 `CheckpointTuple` **逐字复用 B14F1**；本 contract 不另立第二套载体或 id 空间。
> **表结构 / 列名 / SQL / 索引是内部实现细节**，MUST NOT 作为公开 API。

---

## 1. 模块与导出面

```python
from freegraph.persistence import SqliteSaver
```

| 项 | 锁定值 |
|---|---|
| 包 | `src/freegraph/persistence/`（**L4** · 层注册表已登记） |
| 实现 | `sqlite.py`（`SqliteSaver`）· `_json.py`（序列化） |
| `__all__` | `["MemorySaver", "InMemorySaver", "CheckpointTuple", "SqliteSaver"]`（**只增**） |
| 门面 | `freegraph.graph` **MUST NOT** 转出 `SqliteSaver`（G18） |
| 依赖 | 只 import `freegraph.contracts`（L1）+ 标准库；**MUST NOT** import L2 / L3 / L5 |
| 零出站 | 无网络 / 环境变量 / 第三方包；文件 I/O 仅限用户给的 SQLite 连接 / 路径 |

---

## 2. 构造与生命周期

```python
class SqliteSaver:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        on_checkpoint: Callable[[StateSnapshot], None] | None = None,
    ) -> None: ...

    @classmethod
    @contextmanager
    def from_conn_string(
        cls,
        conn_string: str,
        *,
        on_checkpoint: Callable[[StateSnapshot], None] | None = None,
    ) -> Iterator["SqliteSaver"]: ...
```

| 规则 | 内容 |
|---|---|
| `conn` | 调用方持有的 `sqlite3.Connection`；`SqliteSaver` **不**关闭它 |
| `from_conn_string` | `sqlite3.connect(conn_string, check_same_thread=False)`；退出 `with` 时关闭（`closing` 同款） |
| 支持 | `:memory:` / 本地文件 |
| 不支持 | `serde` 参数 / 额外 `close()` / SQLite URI / 网络数据库 / 连接池 |
| `conn_string` 处理 | 原样交给 `sqlite3.connect`；MUST NOT `expanduser` / `expandvars` / 读环境变量 |
| 文件权限 | 跟随 OS 默认 / umask；MUST NOT 额外收紧到 `0o600` |
| 建表 | 首次操作 `setup()`：`PRAGMA journal_mode=WAL` + `CREATE TABLE IF NOT EXISTS` |
| 线程安全 | 每实例一把 `threading.Lock`；单连接；`from_conn_string` 设 `check_same_thread=False` |
| 定位 | 面向真实使用的默认推荐后端；`MemorySaver` 为开发 / 调试 |

---

## 3. 协议：`Checkpointer` 8 方法

```text
get_tuple · list · put · put_writes · delete_thread
delete_for_runs · copy_thread · get_next_version
```

`isinstance(SqliteSaver(...), freegraph.contracts.Checkpointer) is True`。

| 方法 | 签名（B14F1 冻结） |
|---|---|
| `get_tuple` | `(config: RunConfig) -> CheckpointTuple \| None` |
| `list` | `(config: RunConfig \| None = None, *, filter=None, before: RunConfig \| Mapping \| None = None, limit=None) -> Iterator[CheckpointTuple]` |
| `put` | `(config: RunConfig, *, values: Mapping, metadata: Mapping) -> RunConfig` |
| `put_writes` | `(config: RunConfig, *, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = "") -> None` |
| `delete_thread` | `(thread_id: str) -> None` |
| `delete_for_runs` | `(run_ids: Sequence[str]) -> None` · v1 `NotImplementedError` |
| `copy_thread` | `(source_thread_id: str, target_thread_id: str) -> None` · v1 `NotImplementedError` |
| `get_next_version` | `(current: int \| None, channel: None = None) -> int` |

---

## 4. 读侧 `CheckpointTuple`

```python
@dataclass(frozen=True, slots=True)
class CheckpointTuple:
    snapshot: StateSnapshot
    pending_writes: tuple[tuple[str, str, Any], ...]
    scheduler: dict[str, Any]
```

| 字段 | 规则 |
|---|---|
| `.snapshot` | L1 `StateSnapshot` · 8 字段；`config.configurable["checkpoint_id"]` 有值；`config.context is None`；`values` 稀疏；`next` / `tasks` / `interrupts` 是 tuple |
| `.pending_writes` | `(task_id, channel, value)` · 按 `(task_path, task_id, idx)` 升序 · 只含该 checkpoint |
| `.scheduler` | `metadata["scheduler"]` 的副本 · 纯数据 · JSON 可序列化 |
| 未找到 | `get_tuple` ⇒ `None`（不抛） |
| 副本 | 返回的快照 / 写入 / 调度账本都是独立副本 |

> **恰好 3 个公开字段**；不加上游 `.config` / `.checkpoint` / `.metadata` 别名（B14F1 冻结）。

---

## 5. 写侧

### 5.1 `put`

| 规则 | 内容 |
|---|---|
| 关键字 | `values=` / `metadata=`（逐字 B14F1） |
| 类型 | 两者必须 `Mapping`；否则 `TypeError` |
| 编码 | JSON；不可序列化 ⇒ `TypeError`，零写入 |
| checkpoint id | 每线程 `MAX(checkpoint_id) + 1`，格式 `f"{n:032d}"`；首条 `1` |
| parent | 写入前的最新 id；首条 `None` |
| 返回 | `RunConfig(thread_id=..., configurable={"checkpoint_id": new_id})` |
| 快照 8 字段 | `values` / `next` / `config` / `metadata` / `created_at` / `parent_config` / `tasks` / `interrupts` 按 B14F1 组装。⚠️ `tasks` 为 B14F1 的**存储 / 流数据源**（本轮完成态）；`get_state` / `get_state_history` / `stream(checkpoints)` 的 `tasks` 由读取层按上游 next-tasks 重建，**不使用**该字段 |
| `created_at` | UTC ISO-8601 |
| 回调 | 成功 `put` 后锁外调用 `on_checkpoint(deepcopy(snapshot))`；异常吞掉、不回滚 |
| 失败 | 事务回滚；零残留 |

### 5.2 `put_writes`

| 规则 | 内容 |
|---|---|
| 目标 | `config.configurable["checkpoint_id"]`；缺 key ⇒ `KeyError`；不存在 ⇒ `ValueError` |
| `task_id` | 非空 `str`；否则 `TypeError` / `ValueError` |
| `task_path` | `str`；默认 `""` |
| `writes` | `(channel, value)` 序列；`channel` 必须 `str` |
| `__interrupt__` 值 | MUST 是 `Interrupt` / `Interrupt` 序列；按 `{"value", "id"}` 投影后写盘；读回重建成 `Interrupt`；**MUST NOT** 直接 `json.dumps((Interrupt,))` |
| 其它通道值 | 标准库 `json` 纯数据；不可序列化 ⇒ `TypeError` + 零写入 |
| 去重键 | `(task_id, WRITES_IDX_MAP.get(channel, idx))` |
| 普通通道 | 跨调用同 `(task_id, idx)` **首次生效**（`INSERT OR IGNORE`） |
| 保留通道 | `__error__` / `__scheduled__` / `__interrupt__` / `__resume__` **最后生效**（`INSERT OR REPLACE`） |
| 混合写入 | **逐写**判定（不照抄上游 `all(...)` 的整批判定） |
| 失败 | 事务回滚；零残留 |

---

## 6. `list` / `delete` / 版本

### 6.1 `list`

| 参数 | 规则 |
|---|---|
| `config=None` | 全线程；线程按**首次写入顺序**（`MIN(rowid)`）；同线程 id 降序 |
| `config` 有 `thread_id` | 只列该线程 |
| `config.configurable["checkpoint_id"]` | 只列该 id |
| `filter` | key 匹配 `^[a-zA-Z0-9_.-]+$`（否则 `ValueError`）；`json_extract(CAST(metadata AS TEXT), '$.<key>')`；`None` / `bool` / `dict` / `list` 编码同上游 |
| `filter` 非 `Mapping` | `TypeError` |
| `before` | 排除 `checkpoint_id >= before_id`；`before` 指向不存在 id ⇒ 按字符串比较，不抛 |
| `limit` | 全局上限；`<= 0` ⇒ 空 |
| 返回 | 迭代器；每条 `CheckpointTuple` |

### 6.2 `delete_thread`

- `thread_id` 非 `str` ⇒ `TypeError`。
- 删除该线程全部 `checkpoints` + `writes`；幂等；不影响其它线程。
- 删除后同 id 重建：id 从 `1` 开始。

### 6.3 `delete_for_runs` / `copy_thread`

- 方法存在；v1 抛 `NotImplementedError`（上游 sync SQLite 未覆写）。
- MUST NOT 回改 `MemorySaver` 行为。

### 6.4 `get_next_version`

- `None ⇒ 1`；`int`（非 `bool`）⇒ `current + 1`；其它 ⇒ `TypeError`（B14F1 X-02）。

---

## 7. 并发 / 事务 / 失败

| 场景 | 行为 |
|---|---|
| 同实例多线程 | `threading.Lock` 串行化；无串扰 |
| 同线程并发 `put` | 唯一且严格递增 id（事务内 `MAX + 1`；**不额外重试**） |
| 跨实例 / 跨进程 | 依赖 SQLite 文件锁 + WAL；**不**承诺严格同线程串行 |
| 磁盘满 / 权限 / 损坏 | `sqlite3.Error` 子类原样传播；不吞 / 不包装 |
| `database is locked` | 不额外重试；仍失败 ⇒ 原样传播 |
| 单次写失败 | 事务回滚；零残留 |
| `from_conn_string` 退出后调用 | `sqlite3.ProgrammingError` |
| 用户数据库 | 不删除 / 不重建 / 不迁移 |

---

## 8. 回调

| 项 | 规则 |
|---|---|
| 时机 | 每次成功 `put` 后**恰一次** |
| 锁 | 锁外 |
| 载荷 | `StateSnapshot` 的独立副本 |
| 异常 | 吞掉；MUST NOT 回滚已提交快照；MUST NOT 传播给 `put` 调用方 |

---

## 9. 边界

- **不**提供 `get_state` / `get_state_history`（归 `CompiledGraph`）。
- **不**提供 `update_state` / 时间旅行（B16F1）。
- **不**实现运行级删除 / 线程复制（v1）。
- **不**持久化 `context`。
- **不**暴露 schema / SQL / 连接对象 / 额外 `close()`。
- **不**与 B20F2 的 `SqliteTraceStore` 共用表 / 文件 / 连接。
