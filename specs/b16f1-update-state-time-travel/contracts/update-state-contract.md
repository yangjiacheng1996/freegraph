# Contract · `update_state`（状态更新 + 分叉）

**Feature**: B16F1 · **Date**: 2026-11-23 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)
**Upstream**: `langgraph 1.2.11` · `pregel/main.py:1590-2054` / `:2515-2526` ·
`use-time-travel.md:78-123`

> 本 contract 冻结 **L1 `CompiledGraph.update_state`** 的对外面，以及 **L2 私有**
> `runtime/_time_travel.py` 的行为边界。实现代码落 L2；L3 只编排；L4 只提供
> `put` / `put_writes` 存储渠道（鸭子类型，不 import `freegraph.persistence`）。

---

## 1. 调用形态（锁定）

```python
update_state(
    config: RunConfig | Mapping[str, Any] | None,
    values: StateDict,
    as_node: str | None = None,
) -> RunConfig
```

| 项 | 锁定值 |
|---|---|
| 方法位置 | `freegraph.graph` 门面返回的编译产物（L3 `CompiledGraph`） |
| `config` | `RunConfig` / 普通映射 / `None`；**MUST NOT** 裸 `str` / 数字（`TypeError`）；`None` 仅在类型层接受（解析后缺 `thread_id` ⇒ `ValueError`） |
| `values` | `Mapping`（任意 Mapping 运行时复制为 dict）；非 Mapping / `None` ⇒ `TypeError` |
| `as_node` | `str \| None`；非 `str` / `None` ⇒ `TypeError`；不存在 / 歧义 ⇒ `InvalidUpdateError` |
| 返回 | `RunConfig`：`thread_id` = 生效 thread；`configurable["checkpoint_id"]` = 新 id；`context` = `None` |
| saver | 只用 `compile(checkpointer=...)`；`None` / `True` / `False` ⇒ `ValueError("No checkpointer set")` |
| 导出 | 不新增模块级导出；门面符号面零改动 |

**L1 协议改动（R-1 · 已追认）**：`contracts/protocols.py` 的 `update_state`
`config` 注解放宽、返回类别改为 `RunConfig`；其余五方法 / 字段面 / 异常类型不变。

---

## 2. 基准定位

```text
cfg = resolve_read_config(config)          # thread_id / checkpoint_ns 校验
explicit_id = checkpoint_id_of(cfg)        # configurable["checkpoint_id"] 非空 str
base = saver.get_tuple(cfg)                # 显式 id ⇒ 该快照；否则最新
```

| 情况 | 行为 |
|---|---|
| 显式 id 存在 | 以该 `StateSnapshot` 为基准 |
| 显式 id 不存在 | `ValueError`（点名 `checkpoint_id`） |
| 无显式 id，thread 有快照 | 以该 thread 最新快照为基准 |
| 无显式 id，thread 不存在 / 空 | `ValueError`（点名 `thread_id` / 无基准） |
| `checkpoint_ns` 非空 | `ValueError`（v1 无子图） |

- **MUST NOT** 静默新建 thread / 写初始快照 / 回退到 latest（显式 id 场景）。

---

## 3. 处理流水线（L2）

```text
1. state = SchedulerState.from_checkpoint(base.scheduler)
2. _restore_channels(spec, state, base.snapshot.values)   # 深拷贝语义
3. state.fanout.clear()                                   # 不继承基准 pending fan-out
4. node = resolve_as_node(state, spec, as_node)           # §4
5. writes = {key: (value,) for key, value in values.items()}
6. gotos, fanout = _evaluate_source_routes(
       spec, state, node, writes,
       channels=_run_channels(spec, state),
       route_config=raw_config)                           # C8 / 条件边
7. _commit_outcome(
       spec, state, task_id=0, target=node,
       outcome=_TaskOutcome(writes=writes, gotos=(), error=None,
                            interrupts=(), fanout=()),
       extra_gotos=gotos, extra_fanout=fanout)            # 本地 TaskId=0；node_versions / dynamic_edges / fanout
8. _merge_writes(spec, state, [(node, node, writes)])     # C6 合并 + channel_versions
9. _clear_step_end(spec, state, written)                  # 路由通道清理（同普通执行）
10. next_nodes = tuple(_determine_triggers(spec, state))  # 标准触发目标
11. new_cfg = saver.put(
       config_for_checkpoint(cfg, base_id),
       values=_sparse_state(spec, state),
       metadata=_metadata(state, next_nodes, tasks=(), interrupts=(),
                           suspension_kind=None, static_ack=None))
12. return new_cfg
```

**关键约束**：

- **不执行** `as_node` 节点函数；只跑 writers / 条件边。
- 合并 / 路由 / 触发全部复用 `superstep.py` 的正常执行路径；**MUST NOT** 另写第二套。
- 合并 / 路由 / `put` 失败 ⇒ 原异常传播；存储**零变化**（`put` 之前不写存储）。
- `context` 不参与任何步骤。

---

## 4. `as_node` 解析

| 情形 | 结果 |
|---|---|
| 显式 `str` 且存在于 `spec.nodes` | 使用 |
| 显式但不存在 | `InvalidUpdateError`（消息点名节点） |
| 非 `str` / `None` | `TypeError` |
| 省略，图恰 **1 个节点** | 使用该节点（上游兜底） |
| 省略，`versions_seen` 有唯一最后更新者 | 使用该节点 |
| 省略，最后更新者并列 | `InvalidUpdateError("Ambiguous update, specify as_node")` |
| 省略，`versions_seen` 无节点记录 | `InvalidUpdateError`（同款） |

> 推断镜像上游 `main.py:1875-1935`（单节点兜底 + `versions_seen` 最后更新者）。
> **MUST NOT** 用 `node_versions` / 「入口节点」作为回退；v1 无 `input_channels`，
> 上游该兜底列能力边界（spec 裁定 9）。

---

## 5. 合并语义（C6）

| 通道 | 结果 |
|---|---|
| 覆盖型 | 新值覆盖 |
| 归约型 | `Channel.update([value])`（如 `old + value`） |
| 未知 key | `InvalidUpdateError`（`invalid_keys` 保序） |
| 单 key 多值 | 不可能（`Mapping`） |

- 合并只操作**副本**；基准快照 / pending writes 零变化。
- 归约器异常 / 不可深拷贝 ⇒ 原异常；存储零变化。
- 合并顺序 = 通道映射顺序（与普通执行同款）。

---

## 6. 新快照（8 字段）

| 字段 | 值 |
|---|---|
| `values` | C6 合并后的完整稀疏状态 |
| `next` | `as_node` 后继（标准触发目标；`tuple[str, ...]`；可为 `()`） |
| `config` | 新 `RunConfig`（`thread_id` + 新 id；`context is None`） |
| `metadata` | `next` / `interrupts=()` / `tasks=()` / `suspension_kind=None` / `static_ack=None` / `scheduler` |
| `created_at` | UTC ISO-8601（新值） |
| `parent_config` | **基准快照 config** |
| `tasks` | `()` |
| `interrupts` | `()` |
| pending writes | **初始空**（不复制基准）；该分支快照**兼任本分支 anchor**，可承载首轮 pending 留痕，但 MUST NOT 回写原历史快照 |

- **静态标记清空**：`suspension_kind=None`、`static_ack=None`；后继再次命中静态断点
  ⇒ 正常再次暂停（与静态快照 replay 保留 ack 明确不同）。
- **anchor 兼任**：从该分支快照 `invoke(None, fork_config)` **MUST NOT** 再追加 anchor；
  历史增量 = 分支快照 + 执行快照。
- **fan-out**：目标落 `.scheduler["fanout"]`，`next` 可为 `()`；读取层按 B15F1
  next-tasks 重建任务。

---

## 7. 失败信号

| 场景 | 异常 | 消息要点 |
|---|---|---|
| 未挂 saver | `ValueError` | 含 `No checkpointer set` |
| 缺 / 空 `thread_id` | `ValueError` | 点名 `thread_id` |
| 裸 `str` / 数字 config | `TypeError` | — |
| 显式 `checkpoint_id` 不存在 | `ValueError` | 点名 `checkpoint_id` |
| thread 不存在 / 无基准 | `ValueError` | 点名 `thread_id` / 无基准 |
| `checkpoint_ns` 非空 | `ValueError` | v1 无子图 |
| `values` 非 `Mapping` | `TypeError` | — |
| 未知 state key | `InvalidUpdateError` | `invalid_keys` |
| `as_node` 非 `str` / `None` | `TypeError` | — |
| `as_node` 不存在 | `InvalidUpdateError` | 点名节点 |
| `as_node` 歧义 / 无历史 | `InvalidUpdateError` | 含 `Ambiguous update, specify as_node` |
| 合并 / 深拷贝失败 | 原异常 | — |

- MUST NOT 新增 L1 异常类型；失败时存储零变化。

---

## 8. 使用示例（契约形态）

```python
# 1) 跑完 / 中断后取历史
history = list(graph.get_state_history({"thread_id": "t"}))
before_b = next(s for s in history if s.next == ("b",))

# 2) 分叉：覆盖型 + 归约型
fork_cfg = graph.update_state(before_b.config, {"x": 99, "messages": ["try-b"]})

# 3) 继续执行
result = graph.invoke(None, fork_cfg)

# 4) 原历史仍完整；新分支首条 parent_config == before_b.config
assert list(graph.get_state_history({"thread_id": "t"}))[0].parent_config is not None
```

> 以上只示对外形态；具体节点 / schema 由 `quickstart.md` 的可执行场景给出。
