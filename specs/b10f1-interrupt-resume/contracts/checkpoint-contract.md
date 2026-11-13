# 检查点契约（Checkpoint Contract）—— B10F1 ⇄ B14F1 的**接缝**

**Feature**: `B10F1`（**消费方**）· **兑现方**: `B14F1`（`MemorySaver` · M3）
**Spec**: [`../spec.md`](../spec.md) · **Research**: [`../research.md`](../research.md) §2 DR-07 / DR-08 / DR-09 / DR-10

> ⚠️ **本文件是 B10F1 对 B14F1 的**接缝契约****：**B10F1** 定义并**只消费**下列**最小读侧 / 写侧**；
> **B14F1** MUST **满足**它（承接 **D-1**）⇒ ⇒ **B10F1 MUST NOT** 越界实现 saver（FR-019）。
> ⚠️ **L1 的 `Checkpointer` 协议**（8 方法 · B2F1 冻结）的**返回结构与载荷形状挂起 B14F1**
> ⇒ ⇒ 本契约**就是**那个「挂起」的**解冻**⇒ ⇒ **L1 协议本身零改动**（G7 / G8 / G16 / G19 恒绿）。

---

## 1. 为什么需要这份契约（**问题陈述**）

| 项 | 内容 |
|---|---|
| **矛盾** | spec **H-5 ⑤** 要求「恢复 MUST 重建调度状态（已消费版本 / 通道版本 / 节点版本）」；而 spec **裁定 9 / FR-018** 冻结的**读侧契约**只列 `.snapshot` + `.pending_writes` **两个**属性 ⇒ ⇒ **调度账本无处可取** ⇒ ⇒ **两处自相矛盾** |
| **根因** | 恢复后的**后续轮**触发判定**必须**用到 `versions_seen` / `channel_versions` / `node_versions` / `dynamic_edges` ⇒ ⇒ 它们**必须被持久化** ⇒ ⇒ 必须有一个**读侧**出口 |
| **处置** | **读侧契约增**第三个具名属性 **`.scheduler`**（**调度账本**）⇒ ⇒ **不是 L1 冻结面**（是**本 feature 自己**定义的契约）⇒ ⇒ **不需要发起者追认** ⇒ ⇒ 但 MUST 在 plan 的**登记项**里**如实登记**（research **PR-1**）⇒ ⇒ **回修 spec 裁定 9 + FR-018** |
| **被排除** | ❌ 给 L1 的 `StateSnapshot` 加字段 ⇒ 与澄清轮 **Q3** 的拍板（「B10F1 **不**破 L1 冻结面」）**直接矛盾** ⇒ ❌ 把账本塞进 `StateSnapshot.metadata` ⇒ **借位**「附加信息」承载核心状态 ⇒ 违反原则 XII |

---

## 2. **读侧**最小契约（**B14F1 MUST 满足**）

`checkpointer.get_tuple(config)` 的返回值 MUST 暴露**三个具名属性**：

| 属性 | 类型 | 语义 | 上游对照 |
|---|---|---|---|
| `.snapshot` | **L1 的 `StateSnapshot`**（8 字段） | 该会话**最新**的**状态快照** ⇒ `values`（稀疏状态）· `next`（**这一步之后要执行的节点名**）· `interrupts`（本步的中断）· `tasks`（本步任务列表） | 上游的 `CheckpointTuple.checkpoint` 是 `Checkpoint` TypedDict ⇒ **形态不同**（freegraph 用 L1 已有的 `StateSnapshot` ⇒ **同类项同类承载** · 原则 XII ③）⇒ ⇒ **零新增数据类** |
| `.pending_writes` | **序列**（元素 = `(task_id, channel, value)` 三元组） | **待写入**（尚未合并进快照的写入）⇒ 含**中断留痕**与**恢复值** | **上游同款**（`PendingWrite = tuple[str, str, Any]` · `langgraph/checkpoint/base/__init__.py:32`） |
| `.scheduler` | **纯数据字典**（可 JSON 序列化） | **调度账本**（见 §3） | 上游把 `channel_versions` / `versions_seen` 放在 `Checkpoint` 的**一等字段**里 ⇒ ⇒ freegraph 同样**一等**（不塞进 `metadata`） |

⚠️ **三者缺一 ⇒ 恢复不可用** ⇒ ⇒ **B14F1** MUST 全部提供。
⚠️ **查不到该会话** ⇒ `get_tuple` 返回 **`None`** ⇒ ⇒ freegraph 视为「**没有挂起的中断**」
⇒ ⇒ 抛 `InterruptError(reason="no_pending_interrupt")`（**不**静默当作空状态从头跑 · FR-014）。

---

## 3. **调度账本**的编码（`.scheduler`）

| 账本字段 | L2 载体 | **编码**（JSON 可序列化） | 还原 |
|---|---|---|---|
| `versions_seen` | `SchedulerState.versions_seen`（`{节点名: {(kind, ident): 版本}}`） | `{节点名: [[kind, ident, 版本], ...]}` | `{(kind, ident): 版本}` |
| `channel_versions` | `SchedulerState.channel_versions`（`{通道key: 版本}`） | **原样** | 原样 |
| `node_versions` | `SchedulerState.node_versions`（`{节点名: 版本}`） | **原样** | 原样 |
| `dynamic_edges` | `SchedulerState.dynamic_edges`（`{节点名: (目标, ...)}`） | `{节点名: [目标, ...]}` | `tuple(目标, ...)` |

⚠️ **`versions_seen` 的 key 是二元组** ⇒ **JSON 不可直接序列化**（tuple → list ⇒ 键变 list ⇒ 不可哈希）
⇒ ⇒ **必须**用上面的**列表**编码 ⇒ ⇒ **纯数据**（C19 约束③）✓。
⚠️ `SchedulerState.step` **不落盘** ⇒ 恢复时**重新计数**（`steps` 是**本 feature 产出的结果**的口径，
不是持久化状态）⇒ ⇒ **无**「跨运行的步数」语义 ⇒ ⇒ 零歧义。
⚠️ `SchedulerState.channels` **不落盘** ⇒ 通道实例由 `Channel.from_checkpoint` **重建**（现成机制）。

**编码 / 解码的归属**：L2 的 `SchedulerState` **增两个方法**（**只增方法 · 不改字段** ⇒
`SchedulerState()` 的**构造签名逐字不变** ⇒ ⇒ B7F1 冻结面**零破坏**）：

```
SchedulerState.to_checkpoint() -> dict[str, Any]
SchedulerState.from_checkpoint(data: Mapping[str, Any]) -> SchedulerState
```

⚠️ 这两个方法**归 B10F1**（L2 侧）⇒ ⇒ B14F1 **只**需把 `.scheduler` 的内容**原样**存取 ⇒ ⇒
B14F1 **不需要**理解账本的内部结构（**只当不透明载荷**）⇒ ⇒ **零**耦合。

---

## 4. **写侧**最小契约（**B10F1 MUST 调用 · B14F1 MUST 实现**）

| 调用 | 时机 | 载荷 | 上游对照 |
|---|---|---|---|
| `checkpointer.put(config, values=..., metadata=...)` | **挂起时**（写**该步合并后的稀疏状态**）⇒ ⚠️ **口径订正**：初版写「每个 super-step 结束时」⇒ ⇒ 与 `tasks.md`（T041 只实现**挂起时**的写侧）**不一致** ⇒ ⇒ 本 feature 的**写侧**范围 = **挂起时**（`put` + `put_writes`）⇒ ⇒ 「每轮末写快照」**归 B14F1**（其 saver 的持久化策略）⇒ ⇒ **零行为影响**（恢复所需的快照在**挂起时**已写全） | `values` = 该步合并后的**稀疏状态** | 上游 `BaseCheckpointSaver.put(config, values, metadata, new_versions)` |
| `checkpointer.put_writes(config, writes=..., task_id=..., task_path=...)` | **挂起时**（写**中断留痕**）与**恢复时**（写**恢复值**） | `writes` = 该任务的写入序列 | 上游 `BaseCheckpointSaver.put_writes(config, writes, task_id, task_path)` |

⚠️ **关键字名逐字**：`values` / `metadata` / `writes` / `task_id` / `task_path`
⇒ ⇒ L1 协议用 `*args, **kwargs` ⇒ **不约束**关键字 ⇒ ⇒ 由本契约**冻结** ⇒ ⇒ B14F1 MUST 照此实现。
⚠️ **挂起时 MUST 写快照 + 待写入**（FR-012）⇒ ⇒ 挂起态**可被再次恢复**（闭环**可重复** · SC-013）。

---

## 5. **保留通道名**（**上游同款 · 逐字**）

| 通道名 | 载荷 | 谁写 | 谁读 |
|---|---|---|---|
| `__interrupt__` | 中断载荷**元组**（`tuple[Interrupt, ...]`） | 挂起时（`put_writes`） | 恢复时（读回 ⇒ 复用 `.id`） |
| `__resume__` | 恢复值**列表**（按**节点内顺序**） | 恢复时（`put_writes`） | 恢复执行时（scratchpad 消费） |

⚠️ 两个名字 **与上游逐字同款**（`langgraph/_internal/_constants.py:9` / `:11`）⇒ ⇒
`__interrupt__` **同时**是**结果字典的键名**（上游用**同一个**常量 ⇒ **原则 XI ②**）。
⚠️ `task_id` = **节点名**（freegraph 取舍：更可读 · 上游用任务路径哈希）⇒ ⇒ **一轮一个节点一个任务**
⇒ ⇒ 节点名**足够**唯一定位 ⇒ ⇒ **不**构成对上游**行为面**的偏离（pending writes 从不被用户看见）。

---

## 6. **B14F1** MUST 满足的**验收清单**（承接 **D-1**）

| # | 项 | 判定 |
|---|---|---|
| 1 | `get_tuple(config)` 的返回值暴露 `.snapshot` / `.pending_writes` / `.scheduler` **三个**属性 | 属性存在性断言 |
| 2 | `.snapshot` 是 **L1 的 `StateSnapshot`** | `isinstance` 断言 |
| 3 | `.scheduler` 是 **JSON 可序列化**的纯数据 | `json.dumps` 往返 |
| 4 | `put` 接受 `values=` / `metadata=` 两个关键字 | 调用断言 |
| 5 | `put_writes` 接受 `writes=` / `task_id=` / `task_path=` 三个关键字 | 调用断言 |
| 6 | 保留通道名 `__interrupt__` / `__resume__` **逐字** | 通道名断言 |
| 7 | 同一 `thread_id` 的连续调用**状态互不干扰** | 两会话隔离断言 |
| 8 | 挂起 → 恢复 → **再次挂起** ⇒ 三次调用后状态**自洽** | 闭环断言（SC-013） |
| 9 | **真异常 + 中断同现**时，中断元组**随 pending writes 留痕** | pending writes 断言（消解 **X-5**） |
| 10 | **人工验证**补上「**恢复侧真跑一轮**」的实测输出 | 人工验证记录（偏离登记 **V-1** 的承接） |

---

## 7. 边界

- **本契约不规定** checkpointer 的**存储介质** / **序列化格式** / **并发策略** ⇒ ⇒ 归 **B14F1 / B15F1**；
- **本契约不规定** `get_state()` / `get_state_history()` 的形态 ⇒ ⇒ 归 **B15F1**（承接 **D-5**）；
- **本契约不规定** `update_state()` / 时间旅行 ⇒ ⇒ 归 **B16F1**（承接 **D-7**）；
- **本契约不新增** L1 符号 ⇒ ⇒ **L1 的 20 符号面零改动**。
