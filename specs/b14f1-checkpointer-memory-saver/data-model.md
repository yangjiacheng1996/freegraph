# Data Model · B14F1 · Checkpointer 协议 + `MemorySaver`

**Spec**: [spec.md](./spec.md)（**唯一权威**）· **Plan**: [plan.md](./plan.md) ·
**Contracts**: [memory-saver-contract.md](./contracts/memory-saver-contract.md) /
[checkpoint-persistence-contract.md](./contracts/checkpoint-persistence-contract.md)

> 本文件只描述**数据**，不描述行为（行为归 contracts）。
> **不变量**：`StateSnapshot` 8 字段、`Checkpointer` 8 方法、`RunConfig` 9 字段、
> `Span` 11 字段、`Interrupt` / `PregelTask` 的类型面**逐字不改**；
> 本 feature **只新增 L4 的 `CheckpointTuple` 与 L2 私有的存储 / 接线载体**。

---

## 1. 实体总览

| # | 实体 | 层 | 归属 | 新增？ | 说明 |
|---|---|---|---|---|---|
| **EM-01** | `Checkpointer` | L1 | B2F1（冻结） | ❌ 只实现 | 8 方法协议 |
| **EM-02** | `StateSnapshot` | L1 | B1F1（冻结） | ❌ 只消费 | 8 字段快照 |
| **EM-03** | `RunConfig` | L1 | B1F1（冻结） | ❌ 只消费 | 9 字段运行配置 |
| **EM-04** | `Interrupt` / `PregelTask` | L1 | B1F1（冻结） | ❌ 只消费 | 中断 / 任务载体 |
| **EM-05** | `MemorySaver` | L4 | **本 feature** | ✅ 新增 | 内存实现 |
| **EM-06** | `InMemorySaver` | L4 | **本 feature** | ✅ 新增（别名） | `MemorySaver` 同一对象 |
| **EM-07** | `CheckpointTuple` | L4 | **本 feature** | ✅ 新增 | 读侧载体（恰好 3 字段） |
| **EM-08** | `_ThreadStore` | L4 私有 | **本 feature** | ✅ 新增 | 每线程的存储根 |
| **EM-09** | `_StoredCheckpoint` | L4 私有 | **本 feature** | ✅ 新增 | 内部快照记录 |
| **EM-10** | `_StoredWrite` | L4 私有 | **本 feature** | ✅ 新增 | 内部待写入记录 |
| **EM-11** | `CheckpointId` | L4 私有 | **本 feature** | ✅ 新增（值对象） | 32 位零填充十进制字符串 |
| **EM-12** | **调度账本** | L2（既有） | B7F1 / B10F1 / B13F1 | ❌ 只存取 | `metadata["scheduler"]` / `.scheduler` |
| **EM-13** | **pending write 三元组** | L1 / 协议载荷 | B10F1（形状） | ❌ 只存取 | `(task_id, channel, value)` |

---

## 2. 公开实体（**逐字冻结**）

### EM-05 · `MemorySaver`

```python
class MemorySaver:
    def __init__(
        self,
        *,
        on_checkpoint: Callable[[StateSnapshot], None] | None = None,
    ) -> None: ...

    # Checkpointer（8 方法）
    def get_tuple(self, config: RunConfig) -> CheckpointTuple | None: ...
    def list(
        self,
        config: RunConfig | None = None,
        *,
        filter: Mapping[str, Any] | None = None,
        before: RunConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]: ...
    def put(
        self,
        config: RunConfig,
        *,
        values: Mapping[str, Any],
        metadata: Mapping[str, Any],
    ) -> RunConfig: ...
    def put_writes(
        self,
        config: RunConfig,
        *,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None: ...
    def delete_thread(self, thread_id: str) -> None: ...
    def delete_for_runs(self, run_ids: Sequence[str]) -> None: ...  # v1 NotImplementedError
    def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None: ...  # v1 NotImplementedError
    def get_next_version(self, current: int | None, channel: None = None) -> int: ...
```

| 项 | 约束 |
|---|---|
| 模块路径 | `freegraph.persistence.MemorySaver` |
| 别名 | `freegraph.persistence.InMemorySaver is MemorySaver` |
| 构造 | 无必填参数；`on_checkpoint` 可调用或 `None`；非法 ⇒ `TypeError` |
| 线程安全 | 每实例一把 `threading.RLock`；公开方法串行化 |
| 回调 | `on_checkpoint` 在锁外调用；收到**深拷贝** `StateSnapshot`；异常吞掉 |
| 失败信号 | 内置 `TypeError` / `ValueError`；深拷贝失败原样传播；无 I/O |
| 定位 | 开发 / 调试；不保证跨进程 / 跨重启 |

### EM-06 · `InMemorySaver`

- **同一对象别名**（`InMemorySaver is MemorySaver`），不是第二套实现。
- 保留原因：与上游 `langgraph.checkpoint.memory.InMemorySaver` 的可读性对齐。

### EM-07 · `CheckpointTuple`

```python
@dataclass(frozen=True, slots=True)
class CheckpointTuple:
    snapshot: StateSnapshot
    pending_writes: tuple[tuple[str, str, Any], ...]
    scheduler: dict[str, Any]
```

| 字段 | 类型 | 约束 |
|---|---|---|
| `snapshot` | `StateSnapshot` | 8 字段全部可读；`values` 稀疏；`next` / `tasks` / `interrupts` 是元组；`config.configurable["checkpoint_id"]` 有值；`config.context is None` |
| `pending_writes` | 三元组元组 | `(task_id, channel, value)` · 排序 = `(task_path, task_id, idx)` 升序（上游 `writes_sort_key`）· 只含该 checkpoint 的写入 |
| `scheduler` | `dict[str, Any]` | 纯数据 · JSON 可序列化 · `metadata["scheduler"]` 的深拷贝 |

- **恰好 3 个公开字段**；不加上游 `.config` / `.checkpoint` / `.metadata` 别名。
- 返回值中的可变容器是**深拷贝**，不与内部存储共享。

---

## 3. 内部实体（L4 私有）

### EM-08 · `_ThreadStore`

```python
@dataclass
class _ThreadStore:
    snapshots: dict[str, _StoredCheckpoint] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)          # 插入序（旧 → 新）
    writes: dict[str, dict[tuple[str, int], _StoredWrite]] = field(default_factory=dict)
    next_seq: int = 1
    latest_id: str | None = None
```

| 字段 | 约束 |
|---|---|
| `snapshots` | key = `CheckpointId`；value = 完整内部记录 |
| `order` | 与 `snapshots` 的 key 集合一致；`list` 时按 id 降序 |
| `writes` | key = `CheckpointId`；桶内 key = `(task_id, idx)`（上游 `WRITES_IDX_MAP` 同款） |
| `next_seq` | 下一个顺位号；`delete_thread` 后重建从 1 开始 |
| `latest_id` | 最新快照 id；`get_tuple` 的缺省目标 |

### EM-09 · `_StoredCheckpoint`

```python
@dataclass(frozen=True, slots=True)
class _StoredCheckpoint:
    snapshot: StateSnapshot
    metadata: dict[str, Any]      # put 的 metadata 深拷贝（含 scheduler）
    created_at: str               # UTC ISO-8601
    parent_config: RunConfig | None
```

- `snapshot` 是**已组装**的 L1 `StateSnapshot`；`values` / `metadata` / `tasks` / `interrupts` 已深拷贝。
- `metadata` 保留原始键（含 `next` / `interrupts` / `tasks` / `scheduler` / `suspension_kind` / `static_ack`）。
- `created_at` 只在 `put` 时生成一次。

### EM-10 · `_StoredWrite`

```python
@dataclass(frozen=True, slots=True)
class _StoredWrite:
    task_id: str
    channel: str
    value: Any                    # 深拷贝
    task_path: str = ""
    idx: int = 0                  # 普通通道 = 本次调用内位置；保留通道 = WRITES_IDX_MAP 负值
```

| 字段 | 约束 |
|---|---|
| `idx` | 普通通道 = 本次调用内位置；保留通道 = `WRITES_IDX_MAP` 负值；决定去重键与排序 |
| `task_id` | 标准任务 = 节点名；fan-out = `f"{节点名}:{TaskId}"` |
| `channel` | 通道名；保留通道 `__interrupt__` / `__resume__` / `__error__` / `__scheduled__` |
| `value` | 任意可深拷贝对象；不并入快照的 `values` |
| `task_path` | 内部保存；**不**出现在 `.pending_writes` 三元组里；参与排序 |

### EM-11 · `CheckpointId`

- **类型**：`str`（32 位零填充十进制，如 `00000000000000000000000000000001`）。
- **生成**：每线程 `next_seq` 递增；`f"{n:032d}"`。
- **排序**：字典序 == 数值序；`list` / `before` 直接比较字符串。
- **生命周期**：`delete_thread` 后该线程的计数器重置（重新从 1 开始）。
- **用途**：`snapshot.config.configurable["checkpoint_id"]` · `span.checkpoint_id` ·
  `get_tuple` / `list` / `before` 的定位键。

---

## 4. 消费实体（零改动）

### EM-02 · `StateSnapshot`（L1 · 8 字段）

| 字段 | 来源 / 组装规则 |
|---|---|
| `values` | `put` 的 `values` 深拷贝（稀疏状态） |
| `next` | `metadata["next"]`，缺省 `()`；归一为 `tuple` |
| `config` | `RunConfig(thread_id=生效 id, configurable={"checkpoint_id": 新 id})`；`context=None` |
| `metadata` | `put` 的 `metadata` 深拷贝（含 `scheduler`） |
| `created_at` | `datetime.now(timezone.utc).isoformat()` |
| `parent_config` | 上一快照的 `config`；首个为 `None` |
| `tasks` | `metadata["tasks"]`，缺省 `()`；归一为 `tuple` |
| `interrupts` | `metadata["interrupts"]`，缺省 `()`；归一为 `tuple` |

### EM-12 · 调度账本（`metadata["scheduler"]` / `.scheduler`）

| 键 | 类型 | 来源 |
|---|---|---|
| `versions_seen` | `{节点名: [[kind, ident, 版本], ...]}` | `SchedulerState.to_checkpoint()` |
| `channel_versions` | `{通道: int}` | 同上 |
| `node_versions` | `{节点: int}` | 同上 |
| `dynamic_edges` | `{节点: [目标, ...]}` | 同上 |
| `fanout` | `{str(TaskId): {...}}` | 同上（B13F1 F-3） |
| `suspension_kind` | `str \| None` | B13F1 F-9 |
| `static_ack` | `Mapping \| None` | B13F1 F-9 |

- `MemorySaver` **只原样存取**，不解释内部结构、不改写 `channel_versions`。
- `.scheduler` = `metadata["scheduler"]` 的深拷贝；`snapshot.metadata["scheduler"]` 同时保留。

### EM-13 · pending write 三元组

- `(task_id, channel, value)`；`task_id` / `channel` 是 `str`；`value` 任意可深拷贝对象。
- 保留通道名：`__interrupt__`（中断留痕）· `__resume__`（恢复值）·
  `__error__` / `__scheduled__`（上游同款保留名，接受但不解释）。
- 去重键 = `(task_id, WRITES_IDX_MAP.get(channel, idx))`；普通通道跨调用同 `(task_id, idx)` 首次生效，
  保留通道最后生效（同调用内也覆盖）。
- `.pending_writes` 排序 = `(task_path, task_id, idx)` 升序；**不含** `task_path`（只在内部保存）。
- 写入目标 = `config.configurable["checkpoint_id"]`（缺 key ⇒ `KeyError` · X-07）。

---

## 5. 不变量（MUST 始终成立）

| # | 不变量 |
|---|---|
| **I-01** | 不同 `thread_id` 的 `_ThreadStore` 完全独立；交叉读取命中数 == 0。 |
| **I-02** | `snapshots` 的 key 集合 == `order` 的集合；`latest_id` 是其中最新加入的 id（或 `None`）。 |
| **I-03** | 每个 `CheckpointId` 在其线程内**严格单调递增**；`delete_thread` 后重置。 |
| **I-04** | `snapshot.config.configurable["checkpoint_id"]` == 该记录的 id；`snapshot.config.context is None`。 |
| **I-05** | `snapshot.parent_config` 是上一条快照的 `config`；首条为 `None`。 |
| **I-06** | `.pending_writes` 只含该 checkpoint 的写入；顺序 = `(task_path, task_id, idx)` 升序（上游 `writes_sort_key`）。 |
| **I-07** | `put_writes` **不**修改任何快照的 `values`；快照与写入分层。 |
| **I-08** | 所有存入 / 取出的可变容器都是**深拷贝**；调用方修改返回值不影响存储。 |
| **I-09** | 一次 `put` 要么完整提交，要么存储完全不变（无半成品）。 |
| **I-10** | `metadata["scheduler"]` 的 `channel_versions` / `node_versions` / `versions_seen` 与调度器写入值逐 key 相等。 |
| **I-11** | `context` 在 `snapshot.config` / `metadata` / `.scheduler` / pending writes 中出现次数 == 0。 |
| **I-12** | `on_checkpoint` 每次成功 `put` 恰调用一次，且收到深拷贝；回调异常不回滚。 |
| **I-13** | 无 `thread_id` 的运行期不调用 saver；直接调用 saver 时 `ValueError`。 |
| **I-14** | `delete_for_runs` / `copy_thread` 存在但 v1 `NotImplementedError`。 |
| **I-15** | `put_writes` 目标必须由 `config.configurable["checkpoint_id"]` 指定；缺 key ⇒ `KeyError`；指定 id 不存在 ⇒ `ValueError`（X-07）；**MUST NOT** 回退到最新快照。 |

---

## 6. 生命周期 / 状态转换

### 6.1 `MemorySaver` 的线程生命周期

```text
（无）
  │ put(thread_id="t")  ← 初始 / 每轮 / 挂起快照
  ▼
active(thread_id="t")
  │ put / put_writes / get_tuple / list
  ├─ delete_thread("t") → （无）  ← 计数器重置
  └─ delete_for_runs / copy_thread → NotImplementedError（状态不变）
```

### 6.2 一次运行的快照序列（`thread_id="t"`）

| 事件 | 写入 | 说明 |
|---|---|---|
| 全新会话开始 | `put_initial`（或静态 before 的挂起写） | `next` = 第一轮触发集 |
| 第 1 轮合并成功 | `put_step` | `next` = 第二轮触发集 / `()` |
| 第 2 轮动态中断 | `put` + `put_writes`（挂起写） | 本次写入即该轮快照；`tasks=()`（挂起快照不产任务） |
| 恢复 | 无新初始快照 | 从历史 id 继续；用 `history.snapshot.config`（含 checkpoint_id）写 `__resume__` |
| 恢复轮合并成功 | `put_step` | `next` = 后续触发集 / `()`；`tasks` = 本轮 `PregelTask` |
| 静态 after 挂起 | `put`（挂起写） | 代替该轮每轮快照；`tasks=()` |
| 静态恢复完成 | `_clear_static_suspension` 的 F-10 写 | 只写一次；跳过最后一轮每轮 `put` |
| 真异常 + 中断 | 仅 `put_writes(__interrupt__)` | **不**写新快照；附着上一快照 |

### 6.3 pending writes 的去重状态

```text
（空）
  │ put_writes(writes=[(ch, v)], task_id=T)   ← 普通通道（idx=0）
  ▼
stored[(T, 0)] = (ch, v)                       ← 跨调用同 (T, 0) 普通写入忽略
  │ put_writes(writes=[("__interrupt__", (p,))], task_id=T)
  ▼
stored[(T, -3)] = ("__interrupt__", (p,))      ← 保留通道覆盖
  │ 同一调用内同保留通道两次
  ▼
stored[(T, -3)] = 第二条                        ← 最后一次生效（同调用内也覆盖）
  │ 同一调用内普通通道两次（idx=0 / idx=1）
  ▼
两条 _StoredWrite（idx 不同）                   ← 普通通道全保留
```

---

## 7. 与 spec / contracts 的对应

| 实体 / 不变量 | spec | contract |
|---|---|---|
| `MemorySaver` 8 方法 | FR-001 · SC-006 | memory-saver-contract §2 |
| `CheckpointTuple` 3 字段 | FR-011 · SC-007 | memory-saver-contract §3 |
| `StateSnapshot` 8 字段 | FR-012 · SC-008 | checkpoint-persistence-contract §3 |
| pending writes 分层 | FR-003 · SC-002 | memory-saver-contract §4 |
| checkpoint id / 版本 | FR-005 · SC-004 | memory-saver-contract §5 |
| 线程隔离 / 深拷贝 | FR-004 / FR-017 · SC-003 | memory-saver-contract §6 |
| 无 `thread_id` | FR-018 · SC-014 | checkpoint-persistence-contract §7 |
| 静态 / F-10 / fan-out / 屏障 | FR-019 / FR-020 · SC-015 / SC-016 / SC-017 | checkpoint-persistence-contract §4 / §6 |
| 真异常 + 中断 | FR-021 · SC-018 | checkpoint-persistence-contract §5 |
| span `checkpoint_id` | FR-022 · SC-019 | checkpoint-persistence-contract §8 |
| 事件数据源 | FR-023 · SC-020 | memory-saver-contract §7 |
| `context` 不持久化 | FR-024 · SC-021 | checkpoint-persistence-contract §9 |
