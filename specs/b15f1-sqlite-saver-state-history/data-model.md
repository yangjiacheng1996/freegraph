# Data Model · B15F1 · `SqliteSaver` + `get_state` / `get_state_history`

**Spec**: [spec.md](./spec.md)（**唯一权威**）· **Plan**: [plan.md](./plan.md) ·
**Contracts**: [sqlite-saver-contract.md](./contracts/sqlite-saver-contract.md) /
[state-read-contract.md](./contracts/state-read-contract.md) /
[checkpoints-stream-contract.md](./contracts/checkpoints-stream-contract.md)

> 本文件只描述**数据**，不描述行为（行为归 contracts）。
> **不变量**：`StateSnapshot` 8 字段、`Checkpointer` 8 方法、`RunConfig` 9 字段、
> `Interrupt` / `PregelTask` 字段面、`Span` 11 字段**逐字不改**；
> 本 feature **只新增 L4 的 `SqliteSaver` / JSON 编解码与 L2/L3 私有载体**。

---

## 1. 实体总览

| # | 实体 | 层 | 归属 | 新增？ | 说明 |
|---|---|---|---|---|---|
| **EM-01** | `SqliteSaver` | L4 | **本 feature** | ✅ 新增 | 磁盘 checkpointer |
| **EM-02** | `CheckpointTuple` | L4 | B14F1（冻结） | ❌ 复用 | `.snapshot` / `.pending_writes` / `.scheduler` |
| **EM-03** | `StateSnapshot` | L1 | B1F1（冻结） | ❌ 复用 | 8 字段快照 |
| **EM-04** | `RunConfig` | L1 | B1F1（冻结） | ❌ 复用 | 9 字段；`config` 双形态 |
| **EM-05** | `Interrupt` / `PregelTask` | L1 | B1F1（冻结） | ❌ 复用 | 中断 / 任务载体 |
| **EM-06** | `checkpoints` 表 | L4 内部 | **本 feature** | ✅ 新增 | 快照行 |
| **EM-07** | `writes` 表 | L4 内部 | **本 feature** | ✅ 新增 | pending writes 行 |
| **EM-08** | `_json` | L4 内部 | **本 feature** | ✅ 新增 | JSON 编码 / 解码 |
| **EM-09** | `merge_pending_writes` | L2 私有 | **本 feature** | ✅ 新增 | 只读合并助手 |
| **EM-10** | `StreamCheckpointWriter` | L2 私有 | **本 feature** | ✅ 新增 | stream 写盘适配器 |
| **EM-11** | `_state_read` 组装助手 | **L2 私有**（`runtime/_state_read.py`，与 `superstep.py` 同条目） | **本 feature** | ✅ 新增 | config / saver / snapshot / tasks / interrupts |
| **EM-12** | 调度账本 | L2 既有 | B7F1 / B10F1 / B13F1 | ❌ 只存取 | `metadata["scheduler"]` / `.scheduler` |
| **EM-13** | pending write 三元组 | L1 / 协议载荷 | B10F1（形状） | ❌ 只存取 | `(task_id, channel, value)` |
| **EM-14** | checkpoint 顺位 id | L4 私有 | B14F1（冻结） | ❌ 复用 | 32 位零填充十进制字符串 |

---

## 2. `SqliteSaver`（L4 公开面）

```python
class SqliteSaver:
    conn: sqlite3.Connection
    is_setup: bool

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

    # Checkpointer · 8 方法
    def get_tuple(self, config: RunConfig) -> CheckpointTuple | None: ...
    def list(self, config: RunConfig | None = None, *, filter=None,
             before: RunConfig | Mapping[str, Any] | None = None,
             limit: int | None = None
             ) -> Iterator[CheckpointTuple]: ...
    def put(self, config: RunConfig, *, values: Mapping[str, Any],
            metadata: Mapping[str, Any]) -> RunConfig: ...
    def put_writes(self, config: RunConfig, *, writes: Sequence[tuple[str, Any]],
                   task_id: str, task_path: str = "") -> None: ...
    def delete_thread(self, thread_id: str) -> None: ...
    def delete_for_runs(self, run_ids: Sequence[str]) -> None: ...      # v1 NotImplementedError
    def copy_thread(self, source: str, target: str) -> None: ...        # v1 NotImplementedError
    def get_next_version(self, current: int | None, channel: None = None) -> int: ...
```

| 项 | 约束 |
|---|---|
| 模块路径 | `freegraph.persistence.SqliteSaver` |
| 公开导出 | `freegraph.persistence.__all__` **只增** `SqliteSaver` |
| 门面 | `freegraph.graph` **MUST NOT** 转出（G18） |
| 构造 | `conn` 由调用方持有；`on_checkpoint` 可调用或 `None` |
| `from_conn_string` | `sqlite3.connect(conn_string, check_same_thread=False)`；退出关闭 |
| 支持 | `:memory:` / 本地文件 |
| 不支持 | `serde` 参数 / 额外 `close()` / URI / 网络数据库 / 连接池 |
| 锁 | 每实例一把 `threading.Lock` |
| 事务 | `cursor()`：异常 rollback；成功 commit |
| 建表 | 首次操作 `setup()`：WAL + `checkpoints` / `writes` |
| 定位 | 面向真实使用的默认推荐后端；`MemorySaver` 为开发 / 调试 |
| 依赖 | 只 import L1 + 标准库；零 env / 零出站 / 零第三方 |

---

## 3. 内部 SQLite schema（不对外）

> **表名 / 列名 / SQL / 索引 / 事务参数 MUST NOT 作为公开 API。**
> 以下仅为本 feature 的实现契约，供 tests / contracts 对齐；schema 变化 MUST NOT 改变对外语义。

### 3.1 `checkpoints`

```sql
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id             TEXT NOT NULL,
    checkpoint_ns         TEXT NOT NULL DEFAULT '',
    checkpoint_id         TEXT NOT NULL,
    parent_checkpoint_id  TEXT,
    created_at            TEXT NOT NULL,
    values                TEXT NOT NULL,   -- JSON object
    metadata              TEXT NOT NULL,   -- JSON object
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
```

| 列 | 语义 |
|---|---|
| `thread_id` | 会话标识（`resolved_thread_id()`） |
| `checkpoint_ns` | v1 恒 `""`（内部；get_state 拒绝非空） |
| `checkpoint_id` | `f"{n:032d}"`；每线程单调 |
| `parent_checkpoint_id` | 上一快照 id；首条 `NULL` |
| `created_at` | UTC ISO-8601 |
| `values` | JSON object（稀疏状态） |
| `metadata` | JSON object（`next` / `interrupts` / `tasks` / `scheduler` / 其它） |

### 3.2 `writes`

```sql
CREATE TABLE IF NOT EXISTS writes (
    thread_id      TEXT NOT NULL,
    checkpoint_ns  TEXT NOT NULL DEFAULT '',
    checkpoint_id  TEXT NOT NULL,
    task_id        TEXT NOT NULL,
    task_path      TEXT NOT NULL DEFAULT '',   -- freegraph 内部额外列
    idx            INTEGER NOT NULL,
    channel        TEXT NOT NULL,
    value          TEXT NOT NULL,              -- JSON
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

| 列 | 语义 |
|---|---|
| `task_id` | 标准任务 = 节点名；fan-out = `f"{节点名}:{TaskId}"` |
| `task_path` | B14F1 的 `.pending_writes` 排序 `(task_path, task_id, idx)` |
| `idx` | 普通通道 = 本次调用内位置；保留通道 = `WRITES_IDX_MAP` 负值 |
| `channel` | 通道名（含 `__interrupt__` / `__resume__` 等保留通道） |
| `value` | JSON 载荷 |

### 3.3 线程顺序

- `list(config=None)` 的线程顺序 = **该线程首次写入的顺序**；
  实现用 `SELECT thread_id, MIN(rowid) ... GROUP BY thread_id ORDER BY MIN(rowid)`。
- 同线程 checkpoint id **降序**。
- `delete_thread` 清空该线程后，重建视为新线程（首次写入顺序从头开始）。

### 3.4 索引（内部）

- 主键已覆盖 `(thread_id, checkpoint_id)` 查找。
- `writes` 主键覆盖 `(thread_id, checkpoint_id, task_id, idx)` 查找。
- `filter` 用 `json_extract(CAST(metadata AS TEXT), '$.<key>')`；是否加表达式索引由 plan / tasks
  决定（v1 不承诺）。

---

## 4. JSON 编解码（`_json.py`）

### 4.1 写侧

| 数据 | 编码 |
|---|---|
| `values` | `json.dumps(dict(values), ensure_ascii=False)`；tuple → list |
| `metadata` | 递归转换；`next` / `interrupts` / `tasks` / `scheduler` 已知形状；`Interrupt` / `PregelTask` → dict |
| `Interrupt` | `{"value": <json>, "id": <str>}` |
| `PregelTask` | `{"id","name","path","error","interrupts","state","result"}`；`error` / `state` 必须 `None`；`result` JSON |
| pending write value（普通通道） | `json.dumps(value)`；不可序列化 ⇒ `TypeError` |
| pending write value（`channel == "__interrupt__"`） | **channel-aware**：每个 `Interrupt` 投影为 `{"value": <json>, "id": <str>}`（序列保持顺序）；**MUST NOT** 对 `(Interrupt,)` 直接 `json.dumps` |

### 4.2 读侧

| 数据 | 解码 |
|---|---|
| `values` | `json.loads` → `dict`（用户 tuple 变 list · X-05） |
| `next` | list → `tuple[str, ...]` |
| `interrupts` | list → `tuple[Interrupt, ...]` |
| `tasks` | list → `tuple[PregelTask, ...]`；`path` / `interrupts` 重建 tuple（**仅供 B14F1 历史/流数据源；读取 API 的权威 tasks 由 §5.3 重建**） |
| pending `__interrupt__` | list → `tuple[Interrupt, ...]`；每个元素按 `Interrupt(value=..., id=...)` 重建 |
| `scheduler` | `dict` 原样（缺省 `{}`；含 `fanout` 编码，供 §5.3 枚举 fan-out 任务） |
| `parent_config` | 由 `parent_checkpoint_id` 构造 `RunConfig(thread_id=..., configurable={"checkpoint_id": ...})` |
| `snapshot.config` | `RunConfig(thread_id=..., configurable={"checkpoint_id": ...})`；`context=None` |

### 4.3 失败

- `json.dumps` 失败（不可序列化）⇒ `TypeError`；该次 `put` / `put_writes` **零写入**。
- `json.loads` 失败 / 行损坏 ⇒ 传播明确异常；MUST NOT 静默返回半快照。
- `PregelTask.error` 非 `None` / `state` 非 `None` ⇒ `TypeError`（v1 不持久化异常 / 子图快照）。

---

## 5. 读侧组装（L2 `runtime/_state_read`，由 L3 `_stategraph` 调用）

### 5.1 `get_state`

输入：`config`、`spec`、`checkpointer`。

1. `cfg = resolve_read_config(config)`；校验 `thread_id` / `checkpoint_ns`（`config=None` ⇒
   空配置 ⇒ 缺 `thread_id` ⇒ `ValueError`）。
2. `checkpointer` 必须满足 L1 `Checkpointer`；否则 `ValueError("No checkpointer set")`。
3. `t = checkpointer.get_tuple(cfg)`；`None` ⇒ `None`。
4. `values`：无 `checkpoint_id`（**含 `None` / 空串**）⇒ `merge_pending_writes(spec, t.snapshot.values, t.pending_writes)`；
   有非空 `checkpoint_id` ⇒ `t.snapshot.values`。
5. `tasks`：`assemble_tasks(t.snapshot.next, t.scheduler, t.pending_writes)`（见 §5.3；**上游
   next-tasks 语义，不读取 `t.snapshot.tasks`**）。
6. `interrupts`：`assemble_interrupts(tasks, snapshot_interrupts)`（任务顺序展平；无任务中断时回退
   `t.snapshot.interrupts`，见 §5.4）。
7. `next` / `config` / `metadata` / `created_at` / `parent_config` 原样取自 `t.snapshot`。
8. 返回新的 `StateSnapshot`；不修改 `t`。

### 5.2 `get_state_history`

1. 同 §5.1 的 config / saver 校验。
2. `filter` / `before` / `limit` 类型校验。
3. `items = list(checkpointer.list(cfg, filter=..., before=..., limit=...))`（急切消费）。
4. 对每个 `t` 组装：`values = t.snapshot.values`（**不合并**）；`tasks` / `interrupts` 同 §5.3 / §5.4。
5. 返回 `iter(snapshots)`；顺序即 `list` 的 `checkpoint_id` 降序。

### 5.3 `tasks` 重建（**上游 next-tasks**）

输入：`snapshot.next`、`scheduler`（`CheckpointTuple.scheduler`）、`pending_writes`。

```python
def assemble_tasks(
    next_nodes: Sequence[str],
    scheduler: Mapping[str, Any],
    pending_writes: Sequence[tuple[str, str, Any]],
) -> tuple[PregelTask, ...]: ...
```

**步骤**：

1. 建 pending 中断索引：遍历 `channel == "__interrupt__"` 的 pending writes（按既有
   `(task_path, task_id, idx)` 顺序），按 `task_id` 归组；值 MUST 是 `Interrupt` / 序列，
   否则 `TypeError`；重建为 `Interrupt` 对象。
2. 枚举 **fan-out 账本来源任务**（已调度、尚未执行）：`scheduler["fanout"]` = `{producer_task_key:
   {"tasks": [{"target", "arg", "index", ...}]}}`；按 producer key 升序、再按 `index` 升序：
   `id = f"{target}:{index}"`（**本地枚举 id · 非运行时 `task_key`**）、`name = target`、
   `path = (target, index)`、`interrupts = ()`（尚未执行 ⇒ 无 pending；**MUST NOT** 用 `pending.get`）。
3. 枚举 **`next` 中的任务项**（已调度 / 挂起现场 · 以运行时 `task_key` 为准）：
   - 含 `:`（形如 `节点名:TaskId`，fan-out 挂起现场）⇒ `id = next_node`（**= 运行时 `task_key`**）、
     `name = next_node.split(":", 1)[0]`、`path = (name, TaskId)`（`TaskId` 为冒号后全局值，
     能转 `int` 时转 `int`）、`interrupts = pending.get(id, ())`；
   - 否则（标准任务）⇒ `id = name = next_node`、`path = (next_node,)`、
     `interrupts = pending.get(next_node, ())`；
   - ⚠️ **MUST NOT** 对账本来源（步骤 2）与 `next` 来源（步骤 3）做跨源 `id` 去重 / 相等合并：
     两源 id 域不同（本地 `index` vs 运行时全局 `task_key`），且运行时 `_determine_triggers`
     不把 pending fan-out 写入 `next` ⇒ 两源互斥；若同一 checkpoint 同时出现，视为两条独立任务
     并断言不变量。
4. **兜底**：`next_nodes` 为空且无 fan-out ⇒ `tasks = ()`；未关联的 pending `__interrupt__`
   按 pending 顺序追加（`id = task_id`、`name = split(":",1)[0]`、`path = (name,)`），
   MUST NOT 静默丢弃。
5. `error` / `state` / `result` = `None`。
6. 排序：按 `name` 升序；同名 fan-out 任务按 `TaskId`（`next` 来源 = 运行时全局 TaskId；
   账本来源 = 本地 `index`）升序。
7. **MUST NOT** 读取 / 合并 `snapshot.tasks`（B14F1 存储的「本轮完成态」字段）。
8. `next`/pending 来源任务的 `id` MUST 与 `.pending_writes` 的 `task_id` 同款；账本来源任务的
   `id` 是本地 `index`、**MUST NOT** 与之做相等 / 去重假设（同一 checkpoint 内唯一；生成方式不冻结）。

| 字段 | 标准任务 | fan-out（`next` 来源 · 权威） | fan-out（`fanout` 账本来源 · 未执行） |
|---|---|---|---|
| `id` | 节点名 | `next_node`（= 运行时 `task_key`） | `f"{节点名}:{本地index}"`（非 `task_key`） |
| `name` | 节点名 | 节点名 | 节点名（`target`） |
| `path` | `(节点名,)` | `(节点名, 运行时全局 TaskId)` | `(节点名, 本地index)` |
| `interrupts` | pending 中断元组 / `()` | pending 中断元组 / `()` | 恒 `()` |
| `error` / `state` / `result` | `None` | `None` | `None` |

### 5.4 `interrupts` 投影

- 若任一 `task.interrupts` 非空 ⇒ 按 `tasks` 顺序展平各任务载荷元组。
- 否则回退 `snapshot.interrupts`（兼容 B10F1 历史快照）。
- 否则 `()`。
- `interrupts == flatten(tasks.interrupts)`（同序）。
- MUST NOT 因 `snapshot.interrupts` 非空而忽略 pending 新中断。

### 5.5 `merge_pending_writes`（L2 私有）

```python
def merge_pending_writes(
    spec: GraphSpec,
    values: Mapping[str, Any],
    pending_writes: Sequence[tuple[str, str, Any]],
) -> dict[str, Any]: ...
```

1. 新建 `SchedulerState`；`_restore_channels(spec, state, values)`。
2. 按 `pending_writes` 顺序收集**非保留通道**写入。
3. `_reject_unknown_keys`（未知 key ⇒ `InvalidUpdateError`）。
4. 每通道 `Channel.update(values)`。
5. 返回 `_sparse_state(spec, state)` 的新 dict。

- **不**推进 `channel_versions` / `node_versions`。
- **不**修改 `values` 入参 / 存储。
- 保留通道（`__error__` / `__scheduled__` / `__interrupt__` / `__resume__`）跳过。

---

## 6. `StreamCheckpointWriter`（L2 私有）

| 字段 | 类型 | 语义 |
|---|---|---|
| `spec` | `GraphSpec` | 图规格 |
| `state` | `SchedulerState` | stream 会话的调度状态 |
| `run_config` | `RunConfig` | 生效 thread_id |
| `checkpointer` | `Checkpointer` | 真实 saver |
| `table` | `Mapping[str, Any]` | 运行级任务现场（中断映射） |
| `current_checkpoint_id` | `str \| None` | 本轮起点 / 最新 id |
| `is_fresh` | `bool` | 该 thread 是否无历史快照 |

| 方法 | 行为 |
|---|---|
| `prepare()` | `is_fresh` ⇒ `put_initial`；返回本次写出的 `RunConfig \| None` |
| `after_result(result)` | `_determine_triggers` → `put_step`；返回 written |
| `on_interrupt(exc, *, steps)` | `_suspend` → `_produced_interrupts` → `_write_suspend`；返回 `InterruptResult` + written |
| `on_error(collector)` | 若有 round-start id ⇒ `put_error_interrupts` |
| `snapshot_of(written)` | 读取 `get_tuple(written)`，用 §5.1 的 `assemble_snapshot(apply_values=False)` 返回 next-tasks 投影；不可读 ⇒ 明确异常（不伪造） |

- 只在 `"checkpoints" in stream_mode` + saver + `thread_id` 时创建。
- 不恢复历史；`is_fresh` 只决定是否写初始快照。
- 不改变 `stream` 的输入 / 静态断点 / `Command` 边界。

---

## 7. 状态转换

### 7.1 `put`

```text
无该线程 ──► 首个快照（id = 1，parent = None）
有该线程 ──► 追加快照（id = MAX + 1，parent = 上一 id）
delete_thread ──► 清空 ──► 再次 put ⇒ id = 1（新线程）
```

### 7.2 `get_tuple`

```text
有 checkpoint_id ──► 精确命中 ⇒ CheckpointTuple
                     不存在 ⇒ None
无 checkpoint_id ──► 最新 id ⇒ CheckpointTuple
                     无快照 ⇒ None
```

### 7.3 `delete_thread`

```text
thread_id 非 str ⇒ TypeError
存在 ⇒ 删除 checkpoints + writes ⇒ 幂等
不存在 ⇒ no-op
```

---

## 8. 不变量

| # | 不变量 |
|---|---|
| **I-01** | 同一线程 checkpoint id 唯一且严格递增（32 位字符串序 == 数值序）。 |
| **I-02** | 快照与 pending writes 分层：`put_writes` 不改变快照 `values`。 |
| **I-03** | `.pending_writes` 按 `(task_path, task_id, idx)` 升序；普通通道首次生效、保留通道最后生效。 |
| **I-04** | `get_state` 的 pending 合并只操作副本；存储零变化。 |
| **I-05** | `tasks` 为上游 next-tasks（`next` + `.scheduler["fanout"]`）；`interrupts` 与 `tasks` 同序；无任务中断时 snapshot 回退；不使用存储的 `snapshot.tasks`。 |
| **I-06** | `context` 不出现在快照 / metadata / scheduler / pending writes。 |
| **I-07** | `snapshot.config` 只含 `thread_id` + `checkpoint_id`；`context=None`。 |
| **I-08** | 单次 `put` / `put_writes` 失败 ⇒ 事务回滚，零残留。 |
| **I-09** | `from_conn_string` 退出后调用 ⇒ `sqlite3.ProgrammingError`。 |
| **I-10** | `SqliteSaver` 不 import L2 / L3 / L5；L2 / L3 不 import L4。 |
| **I-11** | `freegraph.graph` 不转出 `SqliteSaver`。 |
| **I-12** | `stream(checkpoints)` 只对真实 `put` 发事件；无 saver / 无 `thread_id` ⇒ 0 条；payload 的 `tasks` / `interrupts` 与 `get_state()` 一致。 |
| **I-13** | pending `__interrupt__` 值 channel-aware 编码，读回为 `Interrupt`；其它通道按纯 JSON。 |
