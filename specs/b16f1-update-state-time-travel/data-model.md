# Data Model · B16F1 · `update_state` + 时间旅行回放

**Spec**: [spec.md](./spec.md)（**唯一权威**）· **Plan**: [plan.md](./plan.md) ·
**Contracts**: [update-state-contract.md](./contracts/update-state-contract.md) /
[time-travel-contract.md](./contracts/time-travel-contract.md) /
[put-parent-contract.md](./contracts/put-parent-contract.md) /
[upstream-parity.md](./contracts/upstream-parity.md)

> 本文件只描述**数据**与**不变量**；行为归 contracts。
> **不变量**：`StateSnapshot` 8 字段、`Checkpointer` 8 方法、`RunConfig` 9 字段、
> `Interrupt` / `PregelTask` 字段面、调度账本既有键**逐字不改**；
> 本 feature **只新增 L2 私有时间旅行助手**，不新增公开数据类 / 异常 / 存储格式。

---

## 1. 实体总览

| # | 实体 | 层 | 归属 | 新增？ | 说明 |
|---|---|---|---|---|---|
| **EM-01** | `CompiledGraph.update_state` | L1 / L3 | 本 feature | ✅ 实现 | 锁定签名 `(config, values, as_node=None) -> RunConfig` |
| **EM-02** | 基准快照（base snapshot） | L4 | B14F1 / B15F1 | ❌ 复用 | 显式 `checkpoint_id` 或 thread 最新 `StateSnapshot` |
| **EM-03** | 分支快照（branch snapshot） | L4 | 本 feature | ✅ 新增数据 | 由 `update_state` 写入的 `StateSnapshot`；**兼任本分支 anchor** |
| **EM-04** | branch anchor（replay 锚点） | L4 | 本 feature | ✅ 新增数据 | 非 no-op replay / 历史续跑的首条分支快照；`update_state` 分支快照兼任（spec 裁定 10 / FR-026） |
| **EM-05** | `StateSnapshot` | L1 | B1F1（冻结） | ❌ 复用 | 8 字段快照 |
| **EM-06** | `RunConfig` | L1 | B1F1（冻结） | ❌ 复用 | 9 字段；`config` 双形态 |
| **EM-07** | `CheckpointTuple` | L4 | B14F1（冻结） | ❌ 复用 | `.snapshot` / `.pending_writes` / `.scheduler` |
| **EM-08** | 调度账本（`SchedulerState`） | L2 | B7F1 / B10F1 / B11F1 / B13F1 | ❌ 复用 | `versions_seen` / `channel_versions` / `node_versions` / `dynamic_edges` / `fanout` |
| **EM-09** | pending writes | L1 协议载荷 | B10F1（形状） | ❌ 只读 / 不复制 | `(task_id, channel, value)` 三元组 |
| **EM-10** | `_time_travel` 私有助手 | L2 | 本 feature | ✅ 新增 | 基准 / 推断 / 合并 / 后继 / put |
| **EM-11** | 静态挂起现场 | L2 / L4 | B13F1（冻结） | ❌ 复用 | `suspension_kind` / `static_ack` |
| **EM-12** | checkpoint 顺位 id | L4 | B14F1（冻结） | ❌ 复用 | `f"{n:032d}"`；`MAX+1` |

---

## 2. `CompiledGraph.update_state`（L1 / L3 对外面）

```python
def update_state(
    self,
    config: RunConfig | Mapping[str, Any] | None,
    values: StateDict,
    as_node: str | None = None,
) -> RunConfig: ...
```

| 项 | 约束 |
|---|---|
| 方法位置 | `freegraph.graph` 门面返回的编译产物（L3） |
| `config` | `RunConfig` / 普通映射 / `None`；**MUST NOT** 裸 `str` / 数字；`None` 解析后缺 `thread_id` ⇒ `ValueError` |
| `values` | `Mapping`（任意 Mapping 运行时复制）；非 Mapping / `None` ⇒ `TypeError` |
| `as_node` | `str \| None`；非 `str` / `None` ⇒ `TypeError`；不存在 / 歧义 ⇒ `InvalidUpdateError` |
| 返回 | `RunConfig`（`thread_id` + 新 `checkpoint_id`；`context is None`）；**不是** `StateSnapshot` / 裸 dict |
| saver | 只用 `compile(checkpointer=...)`；未挂 / `True` / `False` ⇒ `ValueError`（含 `No checkpointer set`） |
| 导出 | 不新增模块级导出；门面符号面零改动 |

### 2.1 L1 注解（R-1）

- `config`：由 `RunConfig` 放宽为 `RunConfig | Mapping[str, Any] | None`。
- 返回：由 `StateSnapshot` 改为 `RunConfig`。
- 其余五方法 / 字段面 / 异常类型**零改动**。

---

## 3. 基准快照与分支快照

### 3.1 基准快照选择

| 输入 | 基准 | 不存在时 |
|---|---|---|
| `configurable["checkpoint_id"]` 非空 `str` | 该 id 的 `StateSnapshot` | `ValueError`（点名 `checkpoint_id`） |
| 缺失 / `None` / 空串 | 该 `thread_id` 最新快照 | `ValueError`（点名 `thread_id` / 无基准） |
| `checkpoint_ns` 非空 | — | `ValueError`（v1 无子图） |

### 3.2 分支快照（`update_state` 产出）

| 字段 | 值 | 约束 |
|---|---|---|
| `values` | 基准 `values` 经 C6 合并 `values` 后的稀疏状态 | 深拷贝；不修改基准 |
| `next` | `as_node` 后继集合（出边 + 条件边 + fan-out 求值后的标准触发目标） | `tuple[str, ...]`；可为 `()` |
| `config` | `RunConfig(thread_id=..., configurable={"checkpoint_id": <新 id>})` | `context is None` |
| `metadata` | 内部调度账本投影：`next` / `interrupts=()` / `tasks=()` / `suspension_kind=None` / `static_ack=None` / `scheduler` | 不承诺上游 `source` |
| `created_at` | UTC ISO-8601 | 新值 |
| `parent_config` | **基准快照的 config** | 不是 thread 最新 / 上一分支 tip |
| `tasks` | `()` | 读取层按 next-tasks 重建 |
| `interrupts` | `()` | 不复制基准 pending `__interrupt__` |
| pending writes | **初始空** | 不复制基准 pending；**该分支快照兼任本分支 anchor**，可承载本分支首轮 pending 留痕，但 MUST NOT 回写原历史快照 |

> **anchor 兼任**：`update_state` 产出的分支快照就是本分支首条快照 / anchor；
> 从该分支快照 `invoke(None, fork_config)` **MUST NOT** 再追加 anchor。

### 3.3 branch anchor（非 no-op replay / 历史续跑产出）

> **规范来源**：spec **裁定 10 / FR-026**（本表是其数据面投影，不另立规则）。

| 字段 | 值 |
|---|---|
| `values` | 基准 `values`（原样） |
| `next` | 基准 `next` |
| `config` | 新 id |
| `metadata.next` | 基准 `next` |
| `metadata.interrupts` | `()`（anchor 本身不携带 pending 中断） |
| `metadata.tasks` | `()` |
| `metadata.suspension_kind` / `static_ack` | 基准值（静态快照 replay 必须保留 ack） |
| `metadata.scheduler` | 基准 scheduler |
| `created_at` | 新值 |
| `parent_config` | 基准快照 config |
| pending writes | **初始空**（基准的动态 pending 不复制；执行时从基准 history 读） |

> **anchor 的作用**：给非 no-op replay / 历史续跑一个明确的父链起点；保证首轮中断 / 真异常 /
> `__resume__` 的 pending writes 只落新快照（SC-014），不写原快照。
> **正常终态 no-op**（`next==()` 且无 fanout / 静态 / pending；`input` 为 None / 空 dict）**不写 anchor**；
> `static_after` 的 `next==()` 不是正常终态（按 FR-011 继续并写完成快照）。
> **计数**：非 no-op replay（从**既有历史快照**起）= 1 anchor + 执行快照；
> `update_state` 分叉 = 1 分支快照（**兼任 anchor**）+ 执行快照，**不另写 anchor**；
> 正常终态 replay = 0（SC-008 / SC-016）。

---

## 4. 合并语义（C6）

输入 `values: Mapping[str, Any]`；输出新分支快照的 `values`。

| 通道类型 | 合并规则 |
|---|---|
| 覆盖型 | 新值覆盖旧值 |
| 归约型 | `Channel.update([value])`（如 `operator.add` ⇒ `old + value`） |
| 未知 key | `InvalidUpdateError`（`invalid_keys` = 未知 key 元组） |
| 单 key 多值 | 不可能（`Mapping` 单键单值）；不绕过 `InvalidChannelUpdateError` |

- 合并 MUST 在**副本**上完成；基准快照 / pending writes 零变化。
- 合并失败（未知 key / 归约器异常 / 深拷贝失败）⇒ 原异常传播；存储零变化（原子性）。
- 成功后由 `_clear_step_end` 清理本轮未写的路由型通道（与普通执行同款）。
- `context` 不参与合并 / 不持久化。

---

## 5. `as_node` 与后继

### 5.1 `as_node` 推断

| 情形 | 结果 |
|---|---|
| 显式且存在 | 使用 |
| 显式但不存在 | `InvalidUpdateError`（消息点名节点） |
| 省略，图恰 **1 个节点** | 使用该节点（上游兜底） |
| 省略，基准 `versions_seen` 有唯一最后更新者 | 使用该节点 |
| 省略，最后更新者并列 | `InvalidUpdateError`（`Ambiguous update, specify as_node`） |
| 省略，无版本历史 | `InvalidUpdateError`（同款；MUST NOT 回退 `node_versions` / 入口节点） |
| 非 `str` / `None` | `TypeError` |

> 推断镜像上游「单节点兜底 + `versions_seen`」；v1 无 `input_channels`，上游该兜底
> 列能力边界（spec 裁定 9）。

### 5.2 后继

- **标准目标**：`_determine_triggers(spec, state)`（节点名序）⇒ `metadata.next`。
- **条件边 / `Command.goto`**：`_evaluate_source_routes` 结果写入
  `state.dynamic_edges[as_node]`；目标进入 `next`（标准触发）或 fan-out 账本。
- **fan-out（`Send`）**：`state.fanout[as_node]`；`.scheduler["fanout"]` 编码；
  `next` 可为 `()`；B15F1 读取层据此重建 `PregelTask`。
- **无后继**：`next == ()`；`invoke(None, fork_config)` 为 no-op。
- **不执行** `as_node` 节点函数；只跑 writers / 路由。

---

## 6. 父链与 id

```
基准快照 B (id=b)
  └── 分支快照 U (id=MAX+1, parent=B)          # update_state 产出；兼任本分支 anchor
        ├── 执行快照 E1 (parent=U 或首轮新快照)
        └── 执行快照 E2 (parent=E1)

基准快照 B (id=b)
  └── branch anchor A (id=MAX+1, parent=B)     # 非 no-op replay 产出（既有历史快照起）
        ├── 执行快照 R1 (parent=A)
        └── 执行快照 R2 (parent=R1)
```

> `update_state` 分叉**不**再写 `A`；`U` 本身即 anchor（首轮 pending 可落 `U`，不落 `B`）。

| 规则 | 约束 |
|---|---|
| 新 id | 该 thread `MAX(checkpoint_id)+1`；`f"{n:032d}"`；**不覆盖**已有 id |
| `parent_config` | 分支首条快照 = 基准 / anchor；后续 = 本分支上一条 |
| 原父链 | MUST NOT 重排 / 修改 / 删除 |
| `get_state_history` | 扁平倒序列表；原快照 + 新分支；分支结构由 `parent_config` 读取 |
| 多次分叉 | 每次新分支首条都指向各自分叉点；历史可出现多个同父分支 |

---

## 7. 重放 / 恢复的数据边界

| 操作 | 读取 | 写入 | 历史影响 |
|---|---|---|---|
| `invoke(None, snapshot.config)`（非 no-op，**既有历史快照**起） | 指定快照 `values` / scheduler / next | branch anchor + 后续执行快照 | 只追加；原快照零变化 |
| `invoke(None, fork_config)`（`update_state` 分支起） | 分支快照 `values` / scheduler / next | 后续执行快照（**不写 anchor**；分支快照兼任 anchor） | 只追加；原历史零变化 |
| `invoke(None, final.config)` | 指定**正常终态**快照 | **无**（no-op） | 零新快照（spec SC-016 · STRICTER）；`static_after` 不适用 |
| `invoke(None, static_snapshot.config)` | 指定静态快照 + `static_ack` | anchor（保留 ack）+ 后续 / 完成快照 | 越过已确认断点；断点前 replay 再次暂停 |
| `invoke(state_dict, historical.config)` | 历史快照 + dict 叠加 | anchor + 后续执行快照（若基准是 `update_state` 分支快照则**不写** anchor） | 属 B7F3 续跑，不是 replay 入口；只追加 |
| `Command(resume=...)` | **最新**快照 + pending writes | 最新快照的 `__resume__` + 后续 | 原历史 pending 零变化 |
| `update_state(...)` | 基准快照 | 分支快照（兼任 anchor） | 原历史零变化 |

---

## 8. 静态挂起数据

| 字段 | replay 保留？ | `update_state` 新分支 | 说明 |
|---|---|---|---|
| `suspension_kind` | ✅ 保留（`static_before` / `static_after`） | ❌ 清空（`None`） | 静态快照本身是已确认断点；`update_state` 是新执行起点 |
| `static_ack` | ✅ 保留 | ❌ 清空（`None`） | 水位同构上游 `versions_seen[INTERRUPT]` |
| `next` | 原样（可空） | `as_node` 后继（可空） | 静态 `next` 为空合法 |
| `interrupts` | `()` | `()` | 不要求动态载荷；不假设 `next` 非空 ⇒ 有中断 |

---

## 9. 失败信号映射

| 场景 | 异常 | 存储 |
|---|---|---|
| 未挂 saver（`update_state` / **显式 `checkpoint_id` 重放**） | `ValueError`（含 `No checkpointer set`） | 零变化 |
| 未挂 saver（无显式 id 的普通 `invoke` / 续跑） | 保持 B15F1 / B7F3 行为，不抛本 feature 的 `No checkpointer set` | — |
| 缺 / 空 `thread_id` | `ValueError`（点名） | 零变化 |
| 裸 `str` / 数字 config | `TypeError` | 零变化 |
| 显式 `checkpoint_id` 不存在 | `ValueError`（点名） | 零变化 |
| thread 不存在 / 无基准 | `ValueError`（点名） | 零变化 |
| `checkpoint_ns` 非空 | `ValueError` | 零变化 |
| `values` 非 Mapping | `TypeError` | 零变化 |
| 未知 state key | `InvalidUpdateError` | 零变化 |
| `as_node` 非 `str` / `None` | `TypeError` | 零变化 |
| `as_node` 不存在 | `InvalidUpdateError`（点名） | 零变化 |
| `as_node` 歧义 / 无历史 | `InvalidUpdateError`（`Ambiguous update...`） | 零变化 |
| 合并 / 深拷贝失败 | 原异常 | 零变化 |

---

## 10. 不变量清单

1. **只追加**：原快照 8 字段与 pending writes 逐项不变。
2. **id 唯一**：新 id = `MAX+1`；同一 thread 内严格递增；不覆盖。
3. **父链正确**：分支首条 = 基准 / anchor；`update_state` 分支快照兼任 anchor；
   本分支后续逐条接续；原父链不重排；分叉后 `invoke(None, fork_config)` 不再写 anchor。
4. **读取唯一**：`get_state` / `get_state_history` 的组装路径零改动；
   `tasks` / `interrupts` 由 B15F1 的 next-tasks 投影。
5. **C6 唯一**：`update_state` 不另写归约 / 覆盖规则。
6. **静态分流**：replay 保留 ack；`update_state` 清空 ack。
7. **恢复最新**：`Command(resume)` 只读最新快照；旧 pending 不被改写。
8. **context 不持久化**：快照 / metadata / scheduler / pending 中出现次数 == 0。
9. **纯数据**：`SqliteSaver` 的 JSON 约束继续适用（B15F1 X-05）。
10. **零改动面**：L1 只改 `update_state`；L4 只改 `put` 父链；门面符号面零改动。
