# Contract · 状态读取（`get_state` / `get_state_history`）

**Feature**: B15F1 · **Date**: 2026-11-22 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)
**Upstream**: `langgraph 1.2.11` · `pregel/main.py:1145-1210` / `:1392-1435` / `:1480-1530`

> 本 contract 冻结 **L1 `CompiledGraph`** 的对外状态读取面。
> `SqliteSaver` 只提供 `Checkpointer` 的 8 方法；状态组装在 **L2 私有**
> （`src/freegraph/runtime/_state_read.py`，与 `superstep.py` / `_recursion.py` **同一层注册条目**），
> 由 **L3 `_stategraph.py`** 调用。通过鸭子类型读取 saver，**MUST NOT** import `freegraph.persistence`。
> ⇒ G25：`_stategraph`(L3) → `runtime`(L2) 为合法方向；`_state_read` 的内部 import 不产生层边。

---

## 1. 调用形态

```python
get_state(
    config: RunConfig | Mapping[str, Any] | None,
) -> StateSnapshot | None

get_state_history(
    config: RunConfig | Mapping[str, Any] | None,
    *,
    filter: Mapping[str, Any] | None = None,
    before: RunConfig | Mapping[str, Any] | None = None,
    limit: int | None = None,
) -> Iterator[StateSnapshot]
```

| 项 | 锁定值 |
|---|---|
| 方法位置 | `freegraph.graph` 门面返回的编译产物（L3 `CompiledGraph`） |
| `config` | `RunConfig` / 普通映射 / `None`；**MUST NOT** 接受裸 `thread_id: str`。**`None` 仅在类型层接受**：解析后缺 `thread_id` ⇒ `ValueError`（不构成成功读取路径）。 |
| 会话标识 | `configurable["thread_id"]` 优先于顶层；缺失 / 空串 ⇒ `ValueError` |
| `checkpoint_ns` | 非空 ⇒ `ValueError`（v1 无子图）；空串 / 缺失视为 `""` |
| saver 来源 | 只用 `compile(checkpointer=...)` 注入的 saver；不支持 config 级 checkpointer |
| 无 saver | `checkpointer` 为 `None` / `True` / `False` ⇒ `ValueError("No checkpointer set")` |
| 未找到 | `get_state` ⇒ `None`；`get_state_history` ⇒ 空迭代器 |
| 返回 | `StateSnapshot` 8 字段；不是裸 dict |

### 1.1 L1 注解放宽（R-3）

`src/freegraph/contracts/protocols.py:288-290` 的两处 `config` 注解：

```python
# 旧
def get_state(self, config: RunConfig) -> StateSnapshot | None: ...
def get_state_history(self, config: RunConfig) -> Iterator[StateSnapshot]: ...

# 新（只改 config 注解；返回类别不变）
def get_state(
    self, config: RunConfig | Mapping[str, Any] | None
) -> StateSnapshot | None: ...
def get_state_history(
    self, config: RunConfig | Mapping[str, Any] | None
) -> Iterator[StateSnapshot]: ...
```

- 只改 **2 处**注解；**不**新增 L1 符号；**不**新增 L1 异常。
- 走「登记 + 回溯修订 + 发起者追认」；追认落 `harness/verification/B15F1/manual-verification.md`。
- 实现体可额外接受 `filter` / `before` / `limit` 关键字；L1 协议签名保持（SC-023）。

---

## 2. `get_state` 组装

输入：`config`、`spec`、`checkpointer`。

1. `cfg = resolve_read_config(config)`；校验 `thread_id` / `checkpoint_ns`（`None` ⇒ 缺
   `thread_id` ⇒ `ValueError`）。
2. `checkpointer` 必须满足 L1 `Checkpointer`；否则 `ValueError`。
3. `t = checkpointer.get_tuple(cfg)`；`None` ⇒ `None`。
4. `values`：
   - 无 `configurable["checkpoint_id"]` ⇒ `merge_pending_writes(spec, t.snapshot.values,
     t.pending_writes)`（只读副本；C6 归约）；
   - 有 `checkpoint_id` ⇒ `t.snapshot.values`。
5. `tasks = assemble_tasks(t.snapshot.next, t.scheduler, t.pending_writes)`（§4；**上游
   next-tasks 语义，不读取 `t.snapshot.tasks`**）。
6. `interrupts = assemble_interrupts(tasks)`（§5；任务顺序展平；无任务中断时回退
   `t.snapshot.interrupts`）。
7. `next` / `config` / `metadata` / `created_at` / `parent_config` 原样取自 `t.snapshot`。
8. 返回新的 `StateSnapshot`；存储零变化。

### 2.1 `values` 合并

| 条件 | `values` |
|---|---|
| 无 `checkpoint_id` + 有 pending writes | 以快照为底，按 `.pending_writes` 顺序合并**非保留通道**（C6） |
| 无 `checkpoint_id` + 无 pending writes | 快照 `values` |
| 有 `checkpoint_id` | 快照 `values`（**不**合并） |

- 合并只操作副本；MUST NOT 修改存储。
- 归约失败 ⇒ 原异常传播；存储零变化。
- 保留通道（`__error__` / `__scheduled__` / `__interrupt__` / `__resume__`）不进入 `values`。
- 未知通道 ⇒ `InvalidUpdateError`（与运行期同款）。
- **`configurable["checkpoint_id"]` 存在但为 `None` / 空串** ⇒ 视为**未指定**（取最新并合并）；
  只有**非空字符串**才视为「指定 id」。

---

## 3. `get_state_history` 组装

1. 同 §2 的 config / saver 校验。
2. 校验 `filter` / `before` / `limit` 类型：
   - `filter` ∈ `Mapping | None`；
   - `before` ∈ `RunConfig | Mapping | None`；
   - `limit` ∈ `int | None`（排除 `bool`）。
3. `items = list(checkpointer.list(cfg, filter=..., before=..., limit=...))`（急切消费）。
4. 对每个 `t`：
   - `values = t.snapshot.values`（**不**合并 pending）；
   - `tasks` / `interrupts` 按 §4 / §5 的 **next-tasks** 算法组装（**不读取**
     `t.snapshot.tasks`）；
   - 其它字段原样。
5. 返回 `iter(snapshots)`；顺序 = `list` 的 `checkpoint_id` 降序（最新在前）。

> **后端语义边界**：`filter` / `before` / `limit` 委托给 `checkpointer.list`。
> `SqliteSaver` 后端按上游 key 校验 + `json_extract`；`MemorySaver` 后端保持 B14F1
> 顶层精确匹配（不校验 key）。`MemorySaver` **不改**；跨后端差异属已知行为。

| 判据 | 规则 |
|---|---|
| 数量 | 无过滤时 == 该线程成功 `put` 次数 |
| 顺序 | `checkpoint_id` 严格递减 |
| `limit <= 0` | 空 |
| 未知线程 | 空 |
| 未知 `checkpoint_id` | `None` / 空 |
| `before` 指向不存在 id | 按字符串比较，不抛 |

---

## 4. `tasks` 重建（**上游 next-tasks**）

输入：`snapshot.next`、`scheduler`、`pending_writes`。

1. 建 pending 中断索引：`channel == "__interrupt__"` 的写入按 `(task_path, task_id, idx)`
   顺序归组；值 MUST 是 `Interrupt` / 序列，否则 `TypeError`；重建为 `Interrupt`。
2. **fan-out 账本来源任务（已调度、尚未执行）**：`scheduler["fanout"]` 的每个 `tasks[]` 项 ⇒
   `id = f"{target}:{index}"`（**本地枚举 id · 非运行时 `task_key`**）、`name = target`、
   `path = (target, index)`、`interrupts = ()`（尚未执行 ⇒ 无 pending；MUST NOT 读 pending）。
3. **`next` 中的任务项（已调度 / 挂起现场 · 以运行时 `task_key` 为准）**：
   - 含 `:`（`节点名:TaskId`，挂起现场）⇒ `id = next_node`（**= 运行时 `task_key`**）、
     `name = split(":", 1)[0]`、`path = (name, TaskId)`（TaskId 为冒号后全局值）、
     `interrupts = pending[id]`；
   - 否则标准 ⇒ `id = name = next_node`、`path = (next_node,)`、`interrupts = pending[next_node]`；
   - ⚠️ **MUST NOT** 跨源按 `id` 去重 / 相等合并：账本来源（步骤 2）与 `next` 来源（步骤 3）的
     `id` 域不同（本地 `index` vs 运行时全局 `task_key`），且两源互斥（运行时 `_determine_triggers`
     不把 pending fan-out 写入 `next`）；同一 checkpoint 同时出现 ⇒ 视为两条独立任务并断言不变量。
4. **兜底**：无 `next` 且无 fan-out ⇒ `()`；未关联的 pending `__interrupt__` 按 pending
   顺序追加（`id = task_id`、`name = task_id.split(":", 1)[0]`、`path = (name,)`），
   MUST NOT 静默丢弃。
5. `error` / `state` / `result` = `None`。
6. 顺序：按 `name` 升序；同名 fan-out 任务按 `TaskId`（`next` 来源 = 运行时全局 TaskId；
   账本来源 = 本地 `index`）升序。
7. **MUST NOT** 读取 / 合并 `snapshot.tasks`（B14F1 存储的「本轮完成态」字段）。
8. `next`/pending 来源任务的 `id` MUST 与 `.pending_writes` 的 `task_id` 同款；账本来源任务的
   `id` 是本地 `index`、MUST NOT 与之做相等 / 去重假设（同一 checkpoint 内唯一；生成方式不冻结）。
9. `Interrupt` **不**增加 `name` / 节点名字段。

| 字段 | 标准任务 | fan-out（`next` 来源 · 权威） | fan-out（账本来源 · 未执行） |
|---|---|---|---|
| `id` | 节点名 | `next_node`（= 运行时 `task_key`） | `f"{节点名}:{本地index}"`（非 `task_key`） |
| `name` | 节点名 | 节点名 | 节点名（`target`） |
| `path` | `(节点名,)` | `(节点名, 运行时全局 TaskId)` | `(节点名, 本地index)` |
| `interrupts` | pending 中断元组 / `()` | pending 中断元组 / `()` | 恒 `()` |
| `error` / `state` / `result` | `None` | `None` | `None` |

---

## 5. `interrupts` 投影

1. 若任一 `task.interrupts` 非空 ⇒ 按 §4 的 `tasks` 顺序展平各任务载荷元组。
2. 否则回退 `snapshot.interrupts`（兼容 B10F1 历史快照）。
3. 否则 `()`。
4. `interrupts == flatten(tasks.interrupts)`（同序）。
5. MUST NOT 因 `snapshot.interrupts` 非空而忽略 pending 新中断（真异常 + 中断同现）。

- `get_state` 与 `get_state_history` **同款**。
- `get_state` 的 `interrupts` MUST 与 `invoke` 结果的 `__interrupt__` 元组逐项一致。
- `Interrupt` 元素只有 `value` / `id`（上游同款）。

---

## 6. 静态挂起 / `context`

- 静态挂起：`interrupts == ()` 合法；`suspension_kind` / `static_ack` 原样；
  `next` 允许为空；不要求动态中断载荷。
- `context`：不出现在快照 / metadata / scheduler / pending writes；
  `snapshot.config.context is None`；不从快照还原 `context`。
- 节点别名：不重新引入。

---

## 7. 失败信号

| 场景 | 异常 |
|---|---|
| 裸 `str` / 数字作为 `config` | `TypeError`（`resolve_config`） |
| `config is None`（类型层接受） | 解析为空配置 ⇒ 缺 `thread_id` ⇒ `ValueError`（不是成功读取路径） |
| 缺 / 空 `thread_id` | `ValueError`（点名 `thread_id`） |
| 非空 `checkpoint_ns` | `ValueError`（v1 无子图） |
| 无 saver / `True` / `False` | `ValueError`（含 `No checkpointer set`） |
| `filter` 非 `Mapping` | `TypeError` |
| `SqliteSaver` 的 `filter` key 不匹配 `^[a-zA-Z0-9_.-]+$` | `ValueError`（`MemorySaver` 不校验 key） |
| `before` 非 `RunConfig` / `Mapping` / `None` | `TypeError` |
| `limit` 非 `int` / `None`（`bool` 拒绝） | `TypeError` |
| 未知线程 / id | `None` / 空（不抛） |
| pending 载荷不是 `Interrupt` / 序列 | `TypeError` |
| 归约失败 | 原异常传播；存储零变化 |

---

## 8. 不变量

| # | 不变量 |
|---|---|
| **SR-1** | `get_state` 无 id（含 `None` / 空串）⇒ pending 合并；有非空 id ⇒ 不合并；历史 ⇒ 不合并。 |
| **SR-2** | `tasks` 为上游 next-tasks（`next` + `.scheduler["fanout"]`）；`interrupts` 按任务顺序展平、无任务中断时 snapshot 回退；**不使用** `snapshot.tasks`。 |
| **SR-3** | 历史按 `checkpoint_id` 降序；数量 == `put` 次数。 |
| **SR-4** | `get_state(id)` 与历史同 id 元素逐字段相等（两者都不合并 `values`）。 |
| **SR-5** | 无快照 ⇒ `None` / 空；不伪造。 |
| **SR-6** | `context` 零出现；`snapshot.config.context is None`。 |
| **SR-7** | 只改 L1 的 2 处 `config` 注解；L1 方法签名参数个数不变；无新 L1 符号 / 异常。 |
