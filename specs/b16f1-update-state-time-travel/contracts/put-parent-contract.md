# Contract · L4 `put` 的显式父链扩展

**Feature**: B16F1 · **Date**: 2026-11-23 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)
**Upstream**: `langgraph/checkpoint/memory/__init__.py:430-473`（parent `:459`）·
`langgraph-checkpoint-sqlite 3.1.1` 的 `put` 形态

> 本 contract 冻结 **L4 `put` 的向后兼容扩展**：显式 `configurable["checkpoint_id"]`
> ⇒ parent = 该 id；缺失 / 空串 ⇒ 保持 B14F1「最新快照」语义。**不新增公开符号 /
> 不新增方法 / 不改变写侧关键字**。
>
> **运行期常规写盘**：MUST 以「当前 checkpoint id」作为 `configurable["checkpoint_id"]`
> 传给 `put`（首次写入为空）；故父链仍逐条接续、可观察行为不变（spec 裁定 3 / FR-017）。

---

## 1. 现状与目标

| 项 | B14F1 / B15F1 现状 | 本 feature 目标 |
|---|---|---|
| `put` 的 parent | 固定 = 该 thread **最新**快照 | 显式 id 非空 ⇒ 该 id；否则最新 |
| 新 id | `MAX(checkpoint_id)+1` | **不变** |
| `put` 关键字 | `values` / `metadata` | **不变** |
| 返回 | `RunConfig`（thread + 新 id） | **不变** |
| 既有调用 | 运行期 `put` 不携带 checkpoint id | **零变化** |

---

## 2. 行为表

| `config.configurable["checkpoint_id"]` | parent | 显式 id 不存在 |
|---|---|---|
| 非空 `str` | 该 id 对应的快照 config | `ValueError`（点名 `checkpoint_id`） |
| 缺失 / `None` / 空串 | 该 thread 最新快照（首个为 `None`） | — |

- 新 id MUST = 该 thread `MAX(checkpoint_id)+1`；MUST NOT 覆盖已有 id。
- `parent_config` 字段 = 实际 parent（不是「最新」的固定值）。
- `metadata` 原样深拷贝 / 存储；`scheduler` 原样。
- 写入 MUST 原子：失败时零残留。
- `on_checkpoint` 回调收到的快照 `parent_config` MUST = 实际 parent。
- `context` 不参与。

---

## 3. 双后端一致性

| 项 | `MemorySaver` | `SqliteSaver` |
|---|---|---|
| parent 来源 | 显式 id 的 `snapshot.config` | `parent_checkpoint_id` 列 = 显式 id |
| 显式 id 校验 | `store.snapshots` 存在性 | 事务内 `SELECT 1` / 外键式校验 |
| 新 id | `store.next_seq`（其语义 = MAX+1） | `MAX(checkpoint_id)+1` |
| 并发 | 每实例 `RLock` | 每实例 `Lock` + 事务 |
| 回调 | 锁外调用 | 锁外调用 |
| 既有行为 | 无 id ⇒ 最新 | 无 id ⇒ 最新 |

- 两后端在同操作序列下的 8 字段 / 父链 / 历史顺序 MUST 一致
  （`created_at` 只比格式；JSON 纯数据差异归 B15F1 X-05）。

---

## 4. 调用方改造（L2）

| 调用点 | 改造 |
|---|---|
| `_run_graph_loop` 的 `put_step` | 传 `config_for_checkpoint(run_config, current_checkpoint_id)`（current 为空则原 `run_config`） |
| `_run_graph_loop` 的 `_write_suspend` | 同上；`put_writes` 仍用 `put` 返回的新 config |
| `_run_graph_loop` 的 `_clear_static_suspension` | 同上 |
| `_run_graph_loop` 的 error interrupts | 已用 `config_for_checkpoint(run_config, current_id)`；不变 |
| `_time_travel.update_state` | 用 `config_for_checkpoint(cfg, base_id)` 作 `put` 的 config |
| `_first_graph` 的 replay anchor | 用 `config_for_checkpoint(run_config, base_id)` |
| `StreamCheckpointWriter` | 每次 `put` 用 `config_for_checkpoint(_run_config, current_id)`；`prepare` 用**仅 thread_id** 的 config 读最新（stream 不恢复历史） |

> **MUST NOT** 在 L2 / L3 手工改写已存快照的 `parent_config`；父链只由 `put` 生成。

---

## 5. 兼容性证据

| 回归 | 期望 |
|---|---|
| B14F1 `put` / `put_writes` 既有测试 | 全绿（无 id ⇒ 最新，不变） |
| B15F1 `SqliteSaver` 既有测试 | 全绿（无 id ⇒ 最新，不变） |
| 普通 `invoke` / `stream` 的父链 | 与原行为逐项一致 |
| 分叉 / 重放父链 | 分支首条 = 基准 / anchor；本分支逐条接续 |
| 历史完整性 | 原快照 8 字段 / pending 零变化 |

---

## 6. 失败信号

| 场景 | 异常 | 存储 |
|---|---|---|
| 显式 id 不存在 | `ValueError`（点名 `checkpoint_id`） | 零变化 |
| 缺 / 空 `thread_id` | `ValueError`（点名 `thread_id`） | 零变化 |
| `values` / `metadata` 非 Mapping | `TypeError` | 零变化 |
| 不可序列化（`SqliteSaver`） | `TypeError` | 零变化（B15F1 X-05） |
| 磁盘 / SQLite 失败 | `sqlite3.Error` 子类原样 | 事务回滚（零残留） |

- MUST NOT 在失败时删除 / 重建 / 迁移用户数据库。
