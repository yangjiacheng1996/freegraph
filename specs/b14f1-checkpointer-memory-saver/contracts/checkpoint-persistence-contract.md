# Contract · 运行期检查点持久化接缝（L2 / L3 ⇄ L4）

**Feature**: B14F1 · **Date**: 2026-11-22 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)
**Public L4 contract**: [memory-saver-contract.md](./memory-saver-contract.md)

> 本 contract 冻结**运行期写盘时机**、**快照 8 字段组装**、**pending writes 接线**、
> **静态挂起 / fan-out / 屏障**、**真异常 + 中断留痕**、**节点 span 的 `checkpoint_id`**、
> **`context` 不持久化**与**无 `thread_id` 的跳过**。
> 它只描述**接缝行为**；`MemorySaver` 的存储细节归 [memory-saver-contract.md](./memory-saver-contract.md)。

---

## 1. 入口归一化（`run_graph`）

```python
run_graph(spec, input=None, *, state=None, checkpointer=None, config=None, ...)
```

`run_graph` MUST 在进入 `_first_graph` / `_resume_graph` 之前计算：

```text
effective_checkpointer = checkpointer
    if checkpointer 不是 None / True / False
    且 run_config.resolved_thread_id() 非 None / 非空串
    else None
```

| 输入 | 归一化 | 结果 |
|---|---|---|
| `None` | `None` | 不落盘 |
| `True` / `False` | `None` | 不落盘（v1 无子图 · X-06） |
| 非协议对象 | **原样使用**（运行期鸭子类型；**不判 `isinstance`**） | 直接调用 `run_graph` 时不因归一化而丢 saver |
| 协议对象 + 无 `thread_id` | `None` | 不落盘（SC-005） |
| 协议对象 + 有 `thread_id` | 原对象 | 落盘 |

- 下游 `get_tuple` / `put` / `put_writes` **只看** `effective_checkpointer`。
- **MUST NOT** 在每个调用点重复判 `bool` / `thread_id`。
- **MUST NOT** 在运行期判 `isinstance(checkpointer, Checkpointer)`：协议校验只在 **L3 `compile()`**
  边界（FR-010）；L2 的既有测试桩（`StubCheckpointer` / `_ProbeCheckpointer`）只实现
  恢复路径用到的 3 个方法（B7F3 的 F-05）。
- `Command(resume=...)` 在 `effective_checkpointer is None` 时，**沿用 B10F1 的**
  `InterruptError(reason="checkpointer_required")`（FR-028）。

---

## 2. 写盘时机总表

| 时机 | 写什么 | `next` | `interrupts` | `tasks` | 备注 |
|---|---|---|---|---|---|
| **全新会话 · 初始（round 0）** | `put_initial` | 第一轮触发集 | `()` | `()` | **惰性**：在第一个 `_run_round` **之前**写；若先命中 `interrupt_before`，挂起写**兼任**初始快照 |
| **每轮执行完成 · 合并成功后** | `put_step` | 下一轮触发集；收敛 ⇒ `()` | `()` | 本轮 `PregelTask` | 失败轮**不写** |
| **动态中断挂起** | `_write_suspend` 的 `put` + `put_writes` | 挂起快照的 `next`（可空） | 本轮中断 | `()` | 该写**就是**本轮快照；不再写 `put_step`；挂起快照**不产任务** |
| **静态 `interrupt_before` 挂起** | `_write_suspend` | 待执行节点名 | `()` | `()` | 若此前无快照 ⇒ **兼任初始快照** |
| **静态 `interrupt_after` 挂起** | `_write_suspend` | 下一轮触发集 | `()` | `()` | **代替**该轮 `put_step`；挂起快照**不产任务** |
| **`static_resume` 完成（F-10）** | `_clear_static_suspension` | `()` | `()` | `()` | 只写**一次**；最后一轮**跳过** `put_step` |
| **真异常 + 中断** | 仅 `put_writes(__interrupt__)`（显式 round-start checkpoint id） | —— | —— | —— | **不**写新快照；附着该轮起点快照 |
| **收敛空轮** | 不写 | —— | —— | —— | 空轮不产生快照 |

> **`tasks` 口径**：只有「每轮执行完成」的 `put_step` 填本轮 `PregelTask`；所有
> **挂起快照**（动态中断 / `interrupt_before` / `interrupt_after` / F-10）的
> `tasks` **恒为 `()`** —— 与 B10F1 的冻结挂起写及 `_suspend_metadata` 一致。

### 2.1 快照计数

- **正常跑完**：`快照数 == 实际执行过的 super-step 轮数 + 1`（初始）。
- **动态中断挂起**：`快照数 == 含挂起轮的已执行轮数 + 1`。
- **静态 `interrupt_before` 首轮前命中**：`快照数 == 1`（挂起写兼任初始）。
- **`static_resume` 完成**：F-10 完成快照**只写一次**，与 `put_step` 重复次数 == 0。
- 上述计数 MUST NOT 改变图的**状态 / 节点执行次数 / 返回 dict**（SC-005）。

---

## 3. 快照 8 字段组装（`put`）

`put(config, *, values, metadata)` 的新 `StateSnapshot`：

| 字段 | 取值 |
|---|---|
| `values` | `values` 的深拷贝（稀疏状态） |
| `next` | `metadata["next"]`，缺省 `()`；归一为 `tuple` |
| `config` | `RunConfig(thread_id=生效 id, configurable={"checkpoint_id": 新 id})`；`context=None` |
| `metadata` | `metadata` 的深拷贝（含 `scheduler`） |
| `created_at` | `datetime.now(timezone.utc).isoformat()` |
| `parent_config` | 上一快照的 `config`；首个为 `None` |
| `tasks` | `metadata["tasks"]`，缺省 `()`；归一为 `tuple` |
| `interrupts` | `metadata["interrupts"]`，缺省 `()`；归一为 `tuple` |

**MUST NOT**：

- 把 `context` 写进 `config` / `configurable` / `metadata`；
- 把 pending writes 合并进 `values`；
- 复制调用方的 `metadata` / `tags` 到 `config`；
- 改写 `metadata["scheduler"]` 的 `channel_versions` / `node_versions` / `versions_seen`。

---

## 4. 初始 / 每轮 / 静态 / F-10 的接线

### 4.1 初始快照

- 仅 **全新会话**（`_first_graph` 的 `history is None`）写初始快照。
- **惰性**：在 `interrupt_before` 检查之后、第一个 `_run_round` 之前写。
- `next` = `_determine_triggers(...)` 的第一轮触发集（含 `__start__` 条件边求值后的结果）。
- 初始 `put` 返回的 `config.configurable["checkpoint_id"]` 成为 `current_checkpoint_id`。
- 若 `interrupt_before` 首轮前命中，`_write_suspend` 写挂起快照后直接返回；**不**再写初始。

### 4.2 每轮快照

- 在 `_run_round` 成功、写入合并成功、`state.step += 1` 之后写。
- `next` = `_determine_triggers(spec, state)` 的结果（含 fan-out 目标）；收敛 ⇒ `()`。
- `tasks` = 本轮 `PregelTask`；`interrupts=()`。
- 若 `interrupt_after` 命中，改用 `_write_suspend`（**代替** `put_step`）。
- 每轮 `put` 返回的 id 更新 `current_checkpoint_id`，供**下一轮**节点 span 使用。
- **失败轮**（`_run_round` 抛真异常）**不**写 `put_step`。

### 4.3 静态挂起

- `interrupt_before`：`_write_suspend(..., suspension_kind="static_before",
  static_ack=..., next_nodes=触发集)`。
- `interrupt_after`：`_write_suspend(..., suspension_kind="static_after",
  static_ack=..., next_nodes=下一轮触发集)`。
- 静态挂起的 `interrupts == ()` **合法**；MUST NOT 要求动态中断载荷。
- `.scheduler` 原样保存 `suspension_kind` / `static_ack` / `fanout` / `versions_seen`。

### 4.4 F-10 完成快照

- `static_resume=True` 且运行**收敛**时：
  - 最后一轮**跳过** `put_step`；
  - `_run_graph_loop` 返回后由 `_clear_static_suspension(...)` 写一次完成快照：
    `next=()` / `interrupts=()` / `tasks=()` / `suspension_kind=None` / `static_ack=None` / `fanout={}`；
  - 与 `put_step` 重复次数 MUST == 0。
- `static_resume=True` 但**再次挂起** ⇒ 走 `_write_suspend`；**不**写 F-10 完成快照。

### 4.5 会话连续 / 恢复

- `_first_graph` 有历史 / `_resume_graph` **不写新的初始快照**。
- `current_checkpoint_id` 初值 = `history.snapshot.config.configurable["checkpoint_id"]`。
- 恢复值写 `__resume__` pending write（B10F1 既有路径）⇒ **必须**用带该 checkpoint id 的
  config（直接复用 `history.snapshot.config`；`put_writes` 不再回退最新）⇒ 本 feature 不重复写恢复值。
- 挂起写 / 错误轮留痕同样**必须**把「该轮起点所用的 checkpoint id」显式放进传给 `put_writes` 的 config。
- 后续每轮 / 挂起写按 §2 执行。

---

## 5. 真异常 + 中断留痕

### 5.1 上游同款

上游 `_runner.py:588-591` 在真异常抛出前把中断写进 checkpoint；`:687` 真异常优先；
`:690` 合并中断。freegraph 需要同样的**留痕**，但**不**改变异常的可见面。

### 5.2 机制

- `_run_graph_loop` 在调用 `_run_round` 前设置 L2 私有 `ContextVar` 收集器。
- `_run_round` 在 ⑥ 收尾发现 `error is not None 且 interrupts` 时：
  - 把 `[(task_key, (payload,)), ...]` 写入收集器；
  - `raise error`（**原对象** · 类型 / 消息 / identity 不变）。
- `_run_graph_loop` 捕获后：
  1. 对每个 `(task_key, payload)` 调
     `put_writes(round_start_config, writes=[("__interrupt__", (payload,))], task_id=task_key, task_path=task_key)`
     —— `round_start_config.configurable["checkpoint_id"]` = **该轮起点所用的** checkpoint id
     （`put_writes` 不再回退最新）；
  2. `raise error`（**同一个对象**）。
- 目标快照 = **该轮起点所用的** checkpoint（该线程上一快照 / 初始）；**不**为失败轮写新快照。
- 若无 `effective_checkpointer` ⇒ 跳过 `put_writes`，照常抛错。

### 5.3 MUST NOT

- 在异常上 `add_note` / 挂私有属性 / 改消息；
- 把中断写进 `SchedulerState` / 快照 `metadata` 的私有字段；
- 把该行为宣传为「新能力」（它是上游本来就这样）。

---

## 6. pending writes 的接缝

| 项 | 规则 |
|---|---|
| 保留通道 | `__interrupt__`（中断留痕）· `__resume__`（恢复值）· `__error__` / `__scheduled__`（上游同款保留名，接受但不解释） |
| `task_id` | 标准任务 = 节点名；fan-out = `f"{节点名}:{TaskId}"` |
| 多任务 | 同一轮同一节点可有多个 `task_id`；MUST NOT 假设「一轮一个节点一个任务」 |
| fan-out 载荷 | 目标 + 原样入参 + TaskId 随调度账本一起保存 / 还原；`MemorySaver` **不**解释 |
| 屏障 | `versions_seen` 的 `seen` 原样存取；恢复后目标**不**重复触发 |
| 分层 | `put_writes` **不**修改快照 `values` |

---

## 7. 无 `thread_id` / 无 checkpointer

| 场景 | 行为 |
|---|---|
| `checkpointer=None` | 零 saver 调用；执行结果与注入真实 saver 一致（SC-005） |
| `checkpointer=True` / `False` | 归一化为 `None`；零 saver 调用；不抛 `AttributeError` |
| 有 saver、`thread_id` 缺失 / 空串 | 归一化为 `None`；零 saver 调用；执行结果不变（SC-005） |
| `Command(resume=...)` 且无 effective saver | `InterruptError(reason="checkpointer_required")`（B10F1 既有信号） |

---

## 8. 节点 span 的 `checkpoint_id`

```python
start_node_span(tracer, node, run_id, thread_id, checkpoint_id)
```

| 时点 | `checkpoint_id` |
|---|---|
| 全新会话第一轮 | 初始快照的 id |
| 恢复 / 会话连续第一轮 | `history.snapshot.config.configurable["checkpoint_id"]` |
| 后续轮 | 上一轮 `put_step` / 挂起写返回的 id |
| 无 saver / 无 `thread_id` | `None` |
| 失败轮 | 该轮起点所用的 id（初始 / 上一轮） |

- `_run_round` 增 **keyword-only** `checkpoint_id: str | None = None`；缺省不改既有调用。
- `_bind` 把它传给 `start_node_span`；模型 / 工具 span 继续从节点 span 继承。
- `Span` 的 11 字段**零改动**；**MUST NOT** 新增字段 / 改类型 / 改缺省。

---

## 9. `context` 不持久化

- `MemorySaver` MUST NOT 读取 / 保存 / 还原 / 透出 `RunConfig.context`。
- `snapshot.config.context` MUST 为 `None`。
- `metadata` / `configurable` / `.scheduler` / pending writes 中 `context` 出现次数 == 0。
- 恢复路径的 `context` 由调用方**本次**传入的 `RunConfig` 决定；**不**从快照还原。
- MUST NOT 回退到 `configurable` 承载 `context`；MUST NOT 重新引入节点别名。

---

## 10. `checkpoints` 事件数据源

- `MemorySaver(on_checkpoint=...)`：每次成功 `put` 恰一次，载荷 = 深拷贝 `StateSnapshot`。
- `list()`：历史枚举，返回同形 `CheckpointTuple`。
- **不**接线 `stream(..., stream_mode="checkpoints")`；消费端归 B8F2 / B15F1。
- **MUST NOT** 在 `StreamSession` 里另立 checkpoint 路径；**MUST NOT** 伪造事件。

---

## 11. 与 spec / data-model 的对应

| 接缝 | spec | data-model |
|---|---|---|
| 入口归一化 / 无 `thread_id` | FR-007 / FR-018 | I-13 |
| 初始 / 每轮 / 静态 / F-10 | FR-002 / FR-019 · 裁定 5 | §6.2 |
| 快照 8 字段 | FR-012 | §4 · EM-02 |
| 真异常 + 中断 | FR-021 | I-07 · §6.3 |
| pending writes / fan-out / 屏障 | FR-003 / FR-020 | EM-13 |
| span `checkpoint_id` | FR-022 | I-04 |
| `context` 不持久化 | FR-024 | I-11 |
| 事件数据源 | FR-023 | I-12 |
| 执行语义不变 | FR-034 | I-08 / I-09 |
