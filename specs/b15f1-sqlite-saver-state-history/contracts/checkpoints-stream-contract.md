# Contract · `stream(..., stream_mode="checkpoints")` 消费端

**Feature**: B15F1 · **Date**: 2026-11-22 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)
**Upstream**: `langgraph` 1.2.11 · `_loop.py:631-636` / `debug.py:144-185` · B8F2 四键信封

> 本 contract 冻结 **`stream_mode="checkpoints"`** 的消费端行为。
> 它**只**在 `"checkpoints" in stream_mode` 时启用；其它六档保持 B8F2 v1 的
> 「忽略 checkpointer」语义。允许 L2 私有 `StreamCheckpointWriter` 复用 B14F1 写盘助手；
> MUST NOT 伪造事件或另立事件路径。

---

## 1. 启用条件

| 条件 | 行为 |
|---|---|
| `"checkpoints" in modes` + 真实 saver + `thread_id` 非空 | 启用 `StreamCheckpointWriter`；本次运行每成功 `put` 一条事件 |
| `"checkpoints" in modes` + 无 saver / `True` / `False` | 0 条事件；不写 saver；不抛 |
| `"checkpoints" in modes` + `thread_id` 缺失 / 空串 | 0 条事件；不写 saver；不抛 |
| `"checkpoints" not in modes` | **不**写 saver；B8F2 v1 的其它 mode 行为逐字不变 |
| 静态断点 / `Command` 输入 | B8F2 v1 的既有拒绝边界不变 |

> **不恢复历史**：stream MUST NOT 从历史快照恢复执行、MUST NOT 把历史快照并入本次事件；
> 只把本次运行的新快照追加到该 thread。`prepare()` **允许**读取最新 `checkpoint_id`
> 以设置首条快照的父链（不构成恢复）。
> 若 thread 已有历史，不写初始快照；首个每轮快照的父链指向最新历史快照。

---

## 2. 事件信封（B8F2 零改动）

```python
{
    "stream_mode": "checkpoints",
    "payload": <StateSnapshot>,
    "run_id": <str>,
    "thread_id": <str | None>,
}
```

| 键 | 规则 |
|---|---|
| `stream_mode` | 逐字 `"checkpoints"` |
| `payload` | L1 `StateSnapshot` 8 字段（与 `get_state()` 同形：8 字段同构；`values` 为存储快照值，不保证等于 pending 合并结果；**`tasks` / `interrupts` 为 next-tasks 投影**，与 `get_state()` 对该 id 的结果一致；**不使用**存储的完成态 `snapshot.tasks`） |
| `run_id` | 本次 `stream()` 运行时生成；用户不可指定 |
| `thread_id` | `resolved_thread_id()`；启用时非空 |

- MUST NOT 在 `payload` 上再挂 `run_id` / `thread_id`（避免污染快照）。
- MUST NOT 把历史快照塞进本次运行事件。

---

## 3. 写盘与事件顺序

| 时机 | 写盘 | 事件 |
|---|---|---|
| 会话开始 + thread 无历史 | `put_initial`（`next` = 首轮触发集） | 1 条（初始快照） |
| 每轮成功完成 | `put_step`（`values` = 本轮稀疏状态；`tasks` = 本轮 `PregelTask`） | 1 条 |
| 动态中断挂起 | `put` + `put_writes`（`_write_suspend`） | 1 条（挂起快照） |
| 真异常 + 中断同现 | `put_writes`（round-start checkpoint） | **0 条**（无新快照） |
| 无 saver / 无 `thread_id` | 不写 | 0 条 |

- 事件顺序 = checkpoint 创建顺序（旧 → 新）。
- 初始快照事件在首轮之前；每轮事件在该轮其它 mode 事件之后。
- 事件 payload 由 `get_tuple(written)` + **next-tasks 组装**（`values` 取存储快照；
  `tasks` / `interrupts` 与 `get_state()` 同款）等价读回（spec H-7 / FR-022 已允许）；**不**伪造。
- 数据源允许 `on_checkpoint` / `list()`，或 `get_tuple(written)` 等价读回。
- `on_checkpoint` 用户回调**不是**事件产生的必要条件；writer 用 `get_tuple` + next-tasks 组装读回。

---

## 4. `StreamCheckpointWriter`（L2 私有）

```python
class StreamCheckpointWriter:
    def __init__(self, spec, state, run_config, checkpointer, table) -> None: ...

    def prepare(self) -> RunConfig | None: ...
    def after_result(self, result) -> RunConfig | None: ...
    def on_interrupt(self, exc, *, steps: int) -> tuple[InterruptResult, RunConfig] | None: ...
    def on_error(self, collector: list[tuple[str, Interrupt]]) -> None: ...
    def snapshot_of(self, written: RunConfig) -> StateSnapshot: ...
```

| 方法 | 规则 |
|---|---|
| `prepare` | 读 `get_tuple`；无历史 ⇒ `put_initial`；写回 `current_checkpoint_id`；返回 written / `None` |
| `after_result` | `_determine_triggers(spec, state)` → `put_step`；更新 id；返回 written |
| `on_interrupt` | `_suspend` → `_produced_interrupts` → `_write_suspend`；更新 id；返回 `InterruptResult` + written |
| `on_error` | 有 round-start id ⇒ `put_error_interrupts(collector)`；无 id ⇒ no-op |
| `snapshot_of` | 读 `get_tuple(written)`，用 **next-tasks 组装**返回 `StateSnapshot`（`values` 取存储快照；`tasks` / `interrupts` 与 `get_state()` 一致）；不可读 ⇒ 明确异常（不伪造） |

- 事件产生只依赖 `put` 的真实返回 config；不依赖用户是否传 `on_checkpoint`。
- 写盘失败 ⇒ 底层 `sqlite3.Error` / `TypeError` 原样传播；**不**吞掉。
- `StreamCheckpointWriter` 不改变 `_stream_tick` 的签名；由 `StreamSession` 持有 / 调用。

---

## 5. 与 B8F2 / B14F1 的边界

| 项 | 规则 |
|---|---|
| B8F2 七档语义 | 除 `checkpoints` 外零改动 |
| B8F2 四键信封 | 逐字沿用（裁定 1） |
| B8F2 静态断点 / `Command` | 仍按 B8F2 v1 拒绝；本 feature 不扩张 |
| B14F1 `on_checkpoint` / `list()` | 只作为数据源语义参照；事件从 `get_tuple(written)` 读回 |
| B14F1 快照策略 | 复用 `put_initial` / `put_step` / `_write_suspend` / `put_error_interrupts` |
| 历史枚举 | 归 `get_state_history`；stream 事件只含本次运行 |
| 恢复 / 会话连续 | 不在 stream v1 实现；仍走 `invoke` |

---

## 6. 失败信号

| 场景 | 行为 |
|---|---|
| 无 saver / 无 `thread_id` | 0 条；不抛 |
| saver 写盘失败 | 底层异常原样传播（不降级为 0 条） |
| `get_tuple(written)` 返回 `None` | `RuntimeError`（明确失败；不伪造事件） |
| 静态断点 / `Command` | B8F2 v1 的既有 `ValueError` / `TypeError` |
| 非 `checkpoints` mode | 不启用 writer；既有行为不变 |

---

## 7. 不变量

| # | 不变量 |
|---|---|
| **CS-1** | 事件数 == 本次运行成功 `put` 次数（thread 无历史时含初始）。 |
| **CS-2** | 每条 `payload` 是 `StateSnapshot`；四键信封齐全。 |
| **CS-3** | 无 saver / 无 `thread_id` / 非 `checkpoints` mode ⇒ 事件数 0。 |
| **CS-4** | 不伪造历史事件；不把旧快照塞进本次运行。 |
| **CS-5** | 其它六档事件序列零改动。 |
| **CS-6** | stream 不恢复历史；只追加本次运行快照。 |
| **CS-7** | payload 的 `tasks` / `interrupts` 与 `get_state()` 对该 id 的结果一致（上游 next-tasks 语义）；不使用存储的完成态 `snapshot.tasks`。 |
