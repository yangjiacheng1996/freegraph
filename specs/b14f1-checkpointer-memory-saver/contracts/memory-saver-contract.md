# Contract · `MemorySaver` / `CheckpointTuple`（L4 公开面）

**Feature**: B14F1 · **Date**: 2026-11-22 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)
**Upstream**: `langgraph` 1.2.11 · `langgraph/checkpoint/base` + `checkpoint/memory`

> 本 contract 冻结 **L4 `freegraph.persistence`** 的公开面与存储语义。
> 运行期写盘时机见 [checkpoint-persistence-contract.md](./checkpoint-persistence-contract.md)。
> **不新增 L1 符号**；`Checkpointer` / `StateSnapshot` / `RunConfig` 的字段面**一字不改**。

---

## 1. 模块与导出面

```python
from freegraph.persistence import MemorySaver, InMemorySaver, CheckpointTuple
```

| 项 | 锁定值 |
|---|---|
| 包 | `src/freegraph/persistence/`（**L4** · 层注册表已登记） |
| 实现 | `memory.py`（`MemorySaver`）· `_types.py`（`CheckpointTuple`） |
| `__all__` | `["MemorySaver", "InMemorySaver", "CheckpointTuple"]` |
| 别名 | `InMemorySaver is MemorySaver`（**同一对象**） |
| 门面 | `freegraph.graph` **MUST NOT** 转出 `MemorySaver`（G18 · `facade-L1-L3` 不覆盖 L4） |
| 依赖 | 只 import `freegraph.contracts`（L1）+ 标准库；**MUST NOT** import L2 / L3 / L5 |
| 零出站 | 无网络 / 文件 / 环境变量 / 第三方包 |

---

## 2. 构造与协议

```python
class MemorySaver:
    def __init__(
        self,
        *,
        on_checkpoint: Callable[[StateSnapshot], None] | None = None,
    ) -> None: ...
```

| 规则 | 内容 |
|---|---|
| 必填参数 | **无** |
| `on_checkpoint` | 可调用或 `None`；非法 ⇒ `TypeError` |
| 锁 | 每实例一把 `threading.RLock`；公开方法串行化 |
| 定位 | 开发 / 调试；不保证跨进程 / 跨重启 |
| 协议 | 结构化满足 `freegraph.contracts.Checkpointer` 的 **8** 个方法 |

**8 方法存在性**（`runtime_checkable` 的 `isinstance` 判定）：

```text
get_tuple · list · put · put_writes · delete_thread
delete_for_runs · copy_thread · get_next_version
```

`delete_for_runs` / `copy_thread` 在 v1 **抛 `NotImplementedError`**（上游 `InMemorySaver`
未覆写、由基类抛出 · `base/__init__.py:355,374`）；存在性仍然满足协议。

---

## 3. 读侧载体 `CheckpointTuple`

```python
@dataclass(frozen=True, slots=True)
class CheckpointTuple:
    snapshot: StateSnapshot
    pending_writes: tuple[tuple[str, str, Any], ...]
    scheduler: dict[str, Any]
```

| 字段 | 约束 |
|---|---|
| `snapshot` | L1 `StateSnapshot` · **8 字段全部可读**；`config.configurable["checkpoint_id"]` 有值；`config.context is None`；`values` 稀疏；`next` / `tasks` / `interrupts` 是 `tuple` |
| `pending_writes` | `(task_id, channel, value)` 三元组 · 按 `(task_path, task_id, idx)` 升序（上游 `writes_sort_key`）· 只含该 checkpoint 的写入 |
| `scheduler` | `metadata["scheduler"]` 的深拷贝 · 纯数据 · JSON 可序列化 |

- **恰好 3 个公开字段**；不加上游 `.config` / `.checkpoint` / `.metadata` 别名。
- `get_tuple` 查不到 ⇒ **`None`**（不抛）。
- 返回的 `snapshot` / `pending_writes` / `scheduler` 都是**深拷贝**；调用方修改不影响存储。

---

## 4. `put` · 写快照

```python
def put(
    self,
    config: RunConfig,
    *,
    values: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> RunConfig: ...
```

| 规则 | 内容 |
|---|---|
| `values` | MUST 是 `Mapping` ⇒ 存**深拷贝**；否则 `TypeError` |
| `metadata` | MUST 是 `Mapping` ⇒ 存**深拷贝**；否则 `TypeError` |
| `thread_id` | 取 `config.resolved_thread_id()`；缺失 / 空串 ⇒ `ValueError` |
| 新 id | 每线程单调递增 32 位零填充十进制字符串 |
| 父链 | `parent_config` = 上一快照的 `config`；首个为 `None` |
| 返回 | `RunConfig(thread_id=生效 id, configurable={"checkpoint_id": 新 id})`；`context=None`；不复制调用方的 `metadata` / `tags` / 其它 `configurable` 键 |
| 快照组装 | 见 [checkpoint-persistence-contract.md](./checkpoint-persistence-contract.md) §3 |
| 原子性 | 一次 `put` 要么完整提交，要么存储完全不变 |
| 回调 | 提交并释放锁后调用 `on_checkpoint(深拷贝 snapshot)`；异常吞掉、不回滚 |
| 失败 | 深拷贝失败 ⇒ 原异常传播；无 I/O |

---

## 5. `put_writes` · 写待写入

```python
def put_writes(
    self,
    config: RunConfig,
    *,
    writes: Sequence[tuple[str, Any]],
    task_id: str,
    task_path: str = "",
) -> None: ...
```

| 规则 | 内容 |
|---|---|
| `writes` | `(channel, value)` 对的序列；`channel` MUST 是 `str`；否则 `TypeError` |
| `task_id` | MUST 是非空 `str`；否则 `TypeError` / `ValueError` |
| `task_path` | 缺省 `""`；内部保存；**不**出现在 `.pending_writes` 三元组 |
| 目标快照 | `config.configurable["checkpoint_id"]` 指定的（**上游同款**）；缺 key ⇒ `KeyError` |
| 无目标 | 指定 id 在本线程不存在 ⇒ `ValueError`（X-07）；**MUST NOT** 回退最新 |
| 去重 | 键 `(task_id, WRITES_IDX_MAP.get(channel, idx))`；普通通道跨调用同 `(task_id, idx)` **首次生效**；`__error__` / `__scheduled__` / `__interrupt__` / `__resume__` **最后一次生效**（覆盖） |
| 同调用内 | 保留通道重复 ⇒ **最后一次生效**；普通通道不同 `idx` ⇒ 全保留 |
| 顺序 | `.pending_writes` 按 `(task_path, task_id, idx)` 升序（上游 `writes_sort_key`） |
| 值 | 深拷贝 |
| 分层 | **MUST NOT** 修改任何快照的 `values` |

---

## 6. 查询 / 列表 / 删除

### 6.1 `get_tuple`

```python
def get_tuple(self, config: RunConfig) -> CheckpointTuple | None: ...
```

- `config.configurable["checkpoint_id"]` 有值 ⇒ 取该快照（不存在 ⇒ `None`）。
- 否则取该线程**最新**快照。
- 缺失 `thread_id` ⇒ `ValueError`。
- 未知线程 ⇒ `None`。

### 6.2 `list`

```python
def list(
    self,
    config: RunConfig | None = None,
    *,
    filter: Mapping[str, Any] | None = None,
    before: RunConfig | None = None,
    limit: int | None = None,
) -> Iterator[CheckpointTuple]: ...
```

| 参数 | 规则 |
|---|---|
| `config=None` | 全部线程；`thread_id` 按存储**插入序**（上游同款、不排序），同线程 checkpoint id **降序** |
| `config` 有 `thread_id` | 只列该线程 |
| `config.configurable["checkpoint_id"]` | 只列该 id |
| `filter` | 按 `metadata` 顶层 key 精确匹配（AND） |
| `before` | 排除 id **>= `before` 的 id**（同线程） |
| `limit` | `<= 0` ⇒ 空；否则最多 `limit` 条 |
| 返回 | **迭代器**；每项为深拷贝 `CheckpointTuple` |

### 6.3 `delete_thread`

```python
def delete_thread(self, thread_id: str) -> None: ...
```

- 删除该线程的**全部**快照 + 写入 + 内部状态（含计数器）。
- 幂等；未知线程 ⇒ 无操作。
- 不影响其它线程。
- `thread_id` 非 `str` ⇒ `TypeError`。

### 6.4 `delete_for_runs` / `copy_thread`

```python
def delete_for_runs(self, run_ids: Sequence[str]) -> None: ...
def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None: ...
```

- **存在**（协议结构面）。
- v1 **抛 `NotImplementedError`**（上游内存 saver 同款）。
- 运行级删除 / 线程复制属 B15F1 / B16F1 的存储后端职责。

---

## 7. 版本号

```python
def get_next_version(self, current: int | None, channel: None = None) -> int: ...
```

| 输入 | 输出 |
|---|---|
| `None` | `1` |
| `int` 且非 `bool` | `current + 1` |
| `bool` / `str` / 其它 | `TypeError` |

- `channel` 参数保留（上游兼容）；本 feature 忽略。
- **MUST NOT** 返回上游 `InMemorySaver` 的字符串形式。
- `put` **MUST NOT** 调用 `get_next_version` 改写 `metadata["scheduler"]` 的
  `channel_versions` / `node_versions` / `versions_seen`。
- checkpoint **顺位 id** 与 `get_next_version` 是**两个命名空间**：
  顺位 id = 每线程递增字符串；`get_next_version` = 调度版本 `int+1`。

---

## 8. `on_checkpoint` 数据源

```python
MemorySaver(on_checkpoint=callback)
```

| 规则 | 内容 |
|---|---|
| 时机 | 每次**成功** `put` 后，**恰一次** |
| 载荷 | `StateSnapshot` 的**深拷贝**；与 `get_tuple().snapshot` 同形（8 字段 · 同 id · 同 values / next / tasks / interrupts） |
| 锁 | 在释放 `RLock` 之后调用 |
| 异常 | 吞掉；不传播；不回滚已提交快照；不递归 |
| 与 `list()` | 同源；`list()` 是历史枚举 |
| 边界 | **不**接线 `stream(checkpoints)`；消费端归 B8F2 / B15F1；**MUST NOT** 伪造 stream 事件 |

---

## 9. 线程隔离 / 深拷贝 / 并发

| 项 | 规则 |
|---|---|
| 隔离 | `thread_id` 为一级键；不同线程的快照 / 写入 / 计数器互不可见 |
| 存入 | `put` / `put_writes` 深拷贝 |
| 取出 | `get_tuple` / `list` 返回深拷贝；`on_checkpoint` 收到深拷贝 |
| 深拷贝失败 | 原异常传播；不留下半成品；**MUST NOT** 退化为共享引用 |
| 并发 | 每实例 `RLock`；`put` / `get_tuple` / `list` / `delete_thread` 串行化；无数据串扰 |
| 回调重入 | `on_checkpoint` 在锁外 ⇒ 可安全再调用 saver；不死锁 |

---

## 10. 失败信号

| 场景 | 信号 |
|---|---|
| `values` / `metadata` 非 `Mapping` | `TypeError`（点名参数） |
| `writes` 元素 / `channel` 非法 | `TypeError` |
| `task_id` 非 `str` / 空 | `TypeError` / `ValueError` |
| `config` 缺 `thread_id` | `ValueError`（点名 `thread_id`） |
| `put_writes` 缺 `checkpoint_id` | `KeyError`（上游同款） |
| `put_writes` 指定 id 不存在 | `ValueError`（X-07） |
| `get_next_version` 非法 `current` | `TypeError`（比上游 base 对 `str` 的 `NotImplementedError` 更明确 · STRICTER） |
| `delete_thread` 非 `str` | `TypeError` |
| 深拷贝失败 | 原异常传播 |
| `delete_for_runs` / `copy_thread` | `NotImplementedError` |

- **MUST NOT** 新增 L1 异常类型。
- **MUST NOT** 做 I/O ⇒ 无 `OSError` / 超时 / 权限类失败。

---

## 11. 编译期注入（L3 · 与本 contract 相邻）

```python
g.compile(checkpointer=MemorySaver())
```

| 传入值 | 编译期 | 运行期落盘 |
|---|---|---|
| `None` | 接受 | 不落盘 |
| `True` / `False` | 接受并原样记录 | 不落盘（v1 无子图 · X-06） |
| 满足 L1 `Checkpointer` 协议的对象 | 接受 | 落盘 |
| 其它 | **`TypeError`** | —— |

- 校验在 **L3 `compile()`** 边界、用 **L1 的 `runtime_checkable` 协议**；
  **MUST NOT** 让 L3 import L4。
- 布尔判定 MUST 用 `isinstance(x, bool)`；**MUST NOT** 用 `x in (None, True, False)`
  （否则 `0 == False` / `1 == True` 会把数字误当合法值）。
- **接受面比上游更宽松**（X-08）：上游要求 `BaseCheckpointSaver` 子类，freegraph 接受任意
  满足 8 方法的鸭子类型对象（零依赖的必然取舍）。
- **运行期不再判 `isinstance`**：`effective_checkpointer` 只归一 `None` / `True` / `False` /
  `thread_id`（见 checkpoint-persistence-contract §1）。
- `CompiledGraph.checkpointer` 的记录方式零改动（B7F2 冻结面）。
- 该行为是 B7F2 偏离登记 X-4 的消解；差分 D-77 由 `DIFF` 改为 `SAME`。

---

## 12. 验收清单（与 spec FR / SC 对齐）

| # | 项 | 判定 | spec |
|---|---|---|---|
| 1 | `isinstance(MemorySaver(), Checkpointer)` | `True` | FR-001 · SC-006 |
| 2 | `InMemorySaver is MemorySaver` | `True` | FR-001 · SC-012 |
| 3 | `get_tuple` 三属性 | 存在 + 类型 | FR-011 · SC-007 |
| 4 | `snapshot` 8 字段 | 逐字段可读 | FR-012 · SC-008 |
| 5 | `put` / `put_writes` 关键字 | 逐字 | FR-013 · SC-002 |
| 6 | `__interrupt__` / `__resume__` | 逐字 | FR-014 · SC-009 |
| 7 | 指定 id 取回 | 命中 | FR-015 · SC-010 |
| 8 | `list` 过滤 / 排序 / 上限 | 逐项相等 | FR-016 · SC-010 |
| 9 | 深拷贝 / 线程隔离 | 修改返回值不污染 | FR-017 · SC-003 |
| 10 | 版本 | `int+1` + 调度版本不变 | FR-005 · SC-004 |
| 11 | `delete_thread` | 零残留 | FR-006 · SC-011 |
| 12 | `on_checkpoint` | 每次 `put` 一次 + 深拷贝 | FR-023 · SC-020 |
| 13 | 失败信号 | 内置异常 + 点名 | FR-031 / FR-032 |
| 14 | 编译期校验 | 非法 ⇒ `TypeError` | FR-010 · SC-013 |
| 15 | L4 依赖 | 只 L1 + stdlib | FR-008 · SC-024 |
