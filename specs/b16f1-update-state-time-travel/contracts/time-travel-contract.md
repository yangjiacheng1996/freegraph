# Contract · 时间旅行（replay / fork / 中断 / 静态）

**Feature**: B16F1 · **Date**: 2026-11-23 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)
**Upstream**: `use-time-travel.md:18-170` · `pregel/main.py:1392-1435` / `:2515-2526` ·
`pregel/_loop.py:946-965` · `pregel/_algo.py:155-185`

> 本 contract 冻结 **重放入口**、**branch anchor**、**只追加**、**中断 / 静态组合**、
> **`Command(resume)` 最新定位**。`update_state` 的签名与合并见
> [update-state-contract.md](./update-state-contract.md)。

---

## 1. 重放入口

| 项 | 锁定值 |
|---|---|
| 唯一入口 | `CompiledGraph.invoke(None, snapshot.config)`；`snapshot` 来自 `get_state` / `get_state_history` |
| `snapshot.config` | 必须携带非空 `thread_id` + `checkpoint_id` |
| 非入口 | `stream()` v1 **不是**回放入口（B8F2 冻结面）；`Command(resume=...)` 走恢复路径 |
| `invoke(state_dict, historical.config)` | 沿用 B7F3「会话连续 + 状态字典输入」；**不是** replay；仍只追加新分支 |
| **正常终态** | `next==()` 且无 fanout / 静态挂起 / pending 中断、且 `input` 为 `None` / 空 dict ⇒ **no-op**（不执行节点、零新快照）；`static_after` 的 `next==()` 不是正常终态（按 FR-011 继续并写完成快照） |

---

## 2. 起点校验

```text
explicit_id = checkpoint_id_of(run_config)
history = checkpointer.get_tuple(run_config)
if explicit_id and history is None:
    raise ValueError(... checkpoint_id ...)      # MUST NOT 回退 latest / fresh
```

| 情况 | 行为 |
|---|---|
| 显式 id 存在 | 从该快照重放 |
| 显式 id 不存在 | `ValueError`（点名 `checkpoint_id`） |
| 无显式 id，thread 有历史 | 会话连续（B10F1 既有语义） |
| 无显式 id，thread 无历史 | 全新运行（既有语义） |

---

## 3. branch anchor（非 no-op replay / 历史续跑）

> **规范来源**：spec **裁定 10 / FR-026**（本 contract 是其行为面投影）。

**触发条件**：显式历史 id **且** 以下任一：

- `snapshot.next` 非空；
- `.scheduler["fanout"]` 非空；
- 静态挂起（`suspension_kind` ∈ `static_before` / `static_after`）；
- 有 pending 动态中断；
- `input` 是**非空** `dict`（叠加输入；`invoke(dict, historical.config)` 属 B7F3 续跑、不是 replay，但同受 anchor 保护）。

**不触发（已是分支 anchor）**：显式 id 指向 `update_state` 产出的**分支快照**
（`invoke(None, fork_config)`）⇒ 该分支快照**兼任**本分支 anchor，**MUST NOT** 再追加 anchor；
分支快照初始 pending 为空，可承载首轮 pending 留痕，但 MUST NOT 回写原历史快照。

**anchor 字段**：

| 字段 | 值 |
|---|---|
| `parent_config` | 基准快照 config |
| `values` | 基准 `values` |
| `next` | 基准 `next` |
| `metadata.next` | 基准 `next` |
| `metadata.interrupts` | `()` |
| `metadata.tasks` | `()` |
| `metadata.suspension_kind` / `static_ack` | 基准值（保留静态 ack） |
| `metadata.scheduler` | 基准 scheduler |
| pending writes | **初始空**（基准 pending 不复制；执行时从基准 history 读取） |

- 写 anchor 后，`current_checkpoint_id` = anchor id；后续执行快照 parent = anchor，
  再逐条接续。
- **`update_state` 分叉**：分支快照即 anchor；`current_checkpoint_id` = 分支快照 id，
  不再写额外 anchor；首轮 pending 可落该分支快照或后续新快照。
- 恢复状态 / pending / 静态 ack **仍从基准 history 读取**，不从 anchor 重建。
- **正常终态 no-op 不写 anchor**（SC-016 · STRICTER（X-06））；`static_after` 的 `next==()` 仍写 anchor 并按 FR-011 继续。

**理由**：上游 `_loop.py:952-965` 在 time travel 首轮写 `source="fork"` 快照；
保证首轮中断 / 真异常 / `__resume__` 不写原快照（SC-014）。

---

## 4. 只追加与历史完整性

| 规则 | 约束 |
|---|---|
| 原快照 | 8 字段 + pending writes 逐项不变（MUST NOT 修改 / 删除 / 重排） |
| 新快照 | 只通过同一 `put` 渠道追加；id = `MAX+1` |
| 父链 | 分支首条 = 基准 / anchor；本分支后续逐条接续；原父链不变 |
| 历史枚举 | `get_state_history` 扁平倒序；原快照 + 新分支全部可见 |
| 分支结构 | 仅由 `parent_config` 读取；v1 无分支树 / 按分支枚举 API |
| 多次分叉 | 每次新分支首条指向各自分叉点；允许同父多分支 |
| 旧 pending | 若最新快照挂起而用户从更早历史点分叉，旧 pending 仍留在旧快照；不再是最新 |
| 恢复旧 pending | 先对旧快照 `invoke(None, old.config)` 重新触发中断，再对新的暂停点 `Command(resume=...)` |

---

## 5. 中断组合

### 5.1 动态中断重放

```text
invoke(None, historical.config)   # 节点重跑 → 再次 interrupt() → 追加新暂停快照
invoke(Command(resume=...), thread_config)  # 恢复最新暂停点
```

- 被中断节点**重跑**（不是读缓存）；LLM / API / 中断会再次触发。
- 原快照 pending `__interrupt__` 不改；`__resume__` 只写最新快照。
- 若用户从更早历史点分叉，旧中断需按 §4「恢复旧 pending」处理。

### 5.2 静态挂起重放

| 场景 | 行为 |
|---|---|
| 从**静态快照** `invoke(None, static_snapshot.config)` | **保留 `static_ack`** ⇒ 越过已确认的静态断点继续；不要求动态载荷 |
| 从断点**之前**重放 | 基准无 ack / ack 旧；重放节点产生新写入 ⇒ `static_allowed` 为真 ⇒ 断点**再次触发** |
| `next == ()` 的静态 `static_after` | 不是正常终态；写 anchor 后按静态恢复完成路径清理 `suspension_kind` / `static_ack` |
| `update_state` 新分支 | 清空 `suspension_kind` / `static_ack`；后继命中静态断点则再次暂停 |

- MUST NOT 假设「`next` 非空 ⇒ 必有中断」。
- 静态 `interrupts == ()` 合法；不要求动态载荷。

---

## 6. `Command(resume=...)` 最新定位

| 项 | 锁定值 |
|---|---|
| 读取 | 该 `thread_id` 的**最新**快照 + pending writes |
| 旧 `checkpoint_id` | **忽略**（不参与恢复定位） |
| `__resume__` 写入 | 最新快照 config；MUST NOT 写历史快照 |
| 无挂起 | `InterruptError(reason="no_pending_interrupt")` |
| 未挂 saver | `InterruptError(reason="checkpointer_required")`（B10F1 冻结） |
| 与 replay 的边界 | replay 不调用恢复逻辑；恢复不调用 `update_state`；两者只共享 `put` / `put_writes` |

**理由**：B10F1 FR-010 / 裁定 9「恢复读最新快照」；防旧 id 误写历史；与上游
`invoke(Command(resume="Bob"), fork_config)` 形态兼容（旧 id 不误导定位）。

---

## 7. 失败信号

| 场景 | 异常 |
|---|---|
| 显式 `checkpoint_id` 不存在 | `ValueError`（点名 `checkpoint_id`） |
| 缺 / 空 `thread_id` | `ValueError`（点名 `thread_id`） |
| `checkpoint_ns` 非空 | `ValueError`（v1 无子图） |
| 未挂 saver（**显式 `checkpoint_id` 的 replay** / `update_state`） | `ValueError`（含 `No checkpointer set`） |
| 无显式 `checkpoint_id` 的普通 `invoke` / 续跑 | 保持 B15F1 / B7F3 行为，不因本 feature 抛 `No checkpointer set` |
| 裸 `str` / 数字 config | `TypeError` |
| 动态中断恢复无挂起 | `InterruptError`（`no_pending_interrupt`） |

- replay 的失败 MUST NOT 产生新快照 / 改写原快照。

---

## 8. 差分与证据

| 场景 | 断言 | 判词 |
|---|---|---|
| D-01 | 中间 checkpoint replay 重新执行后续节点，终态一致 | SAME |
| D-02 | **正常终态** replay 不执行节点、终态一致；**不比较快照数**（上游写 fork checkpoint · X-06） | STRICTER |
| D-03 | 中断点 replay 再次触发中断；恢复后跑完；原 pending 不变 | SAME |
| D-15 | 静态挂起重放：`interrupts==()` + 静态标记；不要求动态载荷 | SAME |
| D-17 | 静态快照 replay 保留 ack；断点前 replay 再次暂停；`update_state` 清空 ack | SAME（载体差异属 B13F1 X-8） |

> 上游证据见 [upstream-parity.md](./upstream-parity.md) 与
> `harness/docs/oss/python/langgraph/use-time-travel.md`。
