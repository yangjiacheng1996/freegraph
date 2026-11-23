# Contract · 上游对照（Upstream Parity）

**Feature**: B16F1 · **Date**: 2026-11-23 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md)

> 本文件是 **spec 的 P-01…P-23 / D-01…D-17 / X-01…X-06 的索引与取证清单**；
> 语义权威仍是 [spec.md](../spec.md)。本文件不新增判据，只把「上游怎么说 /
> freegraph 怎么做 / 为什么」集中到一处，供 plan / tasks / 实现 / 复核使用。

---

## 1. 取证环境

| 项 | 值 |
|---|---|
| `langgraph` | **1.2.11** · `.venv` 已安装（2026-11-23） |
| `update_state` | `langgraph/pregel/main.py:2515-2526` |
| `bulk_update_state` | `langgraph/pregel/main.py:1590-2054` |
| `MemorySaver.put` | `langgraph/checkpoint/memory/__init__.py:430-473`（parent `:459`） |
| `StateUpdate` | `langgraph/types.py:631` |
| 文档 | `harness/docs/oss/python/langgraph/use-time-travel.md` · `checkpointers.md` |
| 静态断点 | `langgraph/pregel/_algo.py:155-185` · `_loop.py:946-965` |
| Python | `.venv` 3.11.16 |
| 基线 | **2266 passed / 10 skipped**（2026-11-23 实跑） |

> 上游 `langgraph` 只在差分测试侧使用；生产依赖声明 MUST 保持 `dependencies = []`。
> freegraph **不复制上游代码**；只按行为语义自研。

---

## 2. 语义点索引（P-01…P-23）

| # | 语义点 | 上游锚点 | freegraph 口径 | 关系 |
|---|---|---|---|---|
| P-01 | `update_state` 返回载体 | `main.py:2515-2526` | `(config, values, as_node=None) -> RunConfig`；无 `task_id` | SAME（返回载体）；`task_id` 能力边界 |
| P-01b | `update_state` 的 `config` 载体 | 上游 `RunnableConfig` | `RunConfig \| Mapping \| None` | DIFF（X-01） |
| P-02 | 未挂 checkpointer | `main.py:1617` | `ValueError("No checkpointer set")` | SAME |
| P-03 | 基准快照定位 | `main.py:1650-1666` | 显式 id 优先；缺省最新 | SAME（基准定位） |
| P-03b | 显式 id 不存在 | 上游部分入口 `ValueError` / `KeyError` / 空结果 | 明确 `ValueError` | STRICTER（X-05） |
| P-04 | 只追加 / 原历史完整 | `use-time-travel.md:84` | 新 id = MAX+1；原 8 字段 / pending 不变 | SAME |
| P-05 | `parent_config` = 被分叉点 | `memory/__init__.py:459` | 显式 id ⇒ parent = 该 id；否则最新 | SAME（R-2 扩展） |
| P-06 | `values` 走归约器 / 覆盖 | `use-time-travel.md:104` · `checkpointers.md:255` · `main.py:1950-2008` | 同一 `Channel.update([value])` 路径（C6） | SAME |
| P-07 | `as_node` 省略推断 | `main.py:1875-1935`（单节点兜底 + `versions_seen` 最后更新者） | 同款；MUST NOT 回退 `node_versions`；歧义 ⇒ `InvalidUpdateError`；`input_channels` 兜底列能力边界 | SAME |
| P-08 | `as_node` 不存在 | `main.py:1937` / `:1946` | 同款异常类型；点名节点 | SAME |
| P-09 | 继续执行起点 = `as_node` 后继 | `use-time-travel.md:104` · `main.py:1957-2008` | 出边 + 条件边 + fan-out 按运行期同款求值 | SAME |
| P-10 | 重放入口 = `invoke(None, prior_config)` | `use-time-travel.md:18-72` | 同款 | SAME |
| P-11 | 重放重新执行节点 | `use-time-travel.md:24` | 从 `snapshot.next` 重新执行；不读缓存 | SAME |
| P-12 | **正常终态**重放为 no-op | `use-time-travel.md:24` · **实测：仍写 fork checkpoint** | 不执行节点、**零新快照**（SC-016）；`static_after` 不在本行 | **STRICTER（X-06）** |
| P-13 | 中断在时间旅行中再次触发 | `use-time-travel.md:128-170` | 节点重跑、再次暂停；恢复最新暂停点 | SAME |
| P-14 | 恢复路径定位 | B10F1 FR-010 / 裁定 9 | `Command(resume)` 只读最新快照；忽略旧 id | STRICTER（X-04） |
| P-15 | 重放 / 分叉 pending 归属 | `main.py:2014-2050` | 只写新追加 checkpoint；不写原快照 | SAME（行为不变量；不占 X） |
| P-16 | `context` 不持久化 | 上游 `RunnableConfig.configurable` | 不持久化 / 不恢复；`config.context is None` | DIFF（X-03） |
| P-17 | `task_id` / `values=None + END` / fresh-thread | `main.py:2515-2526` · `:1668-1730` · `:1650-1666` | v1 不支持（`None` ⇒ `TypeError`；须有基准） | 能力边界 |
| P-18 | `stream` 与时间旅行 | 上游 `stream` 不专门定义恢复 | v1 `stream` 不是回放入口；B8F2 冻结 | 能力边界 |
| P-19 | `metadata.source` | `checkpointers.md:163,235-236` | 内部调度账本；不承诺 `source` | DIFF（继承 B14F1/B15F1；不新增 X） |
| P-20 | 额外 `__start__` 快照 | 上游 `metadata["step"] == -1` | freegraph 不存在 | DIFF（继承 B14F1；不新增 X） |
| P-21 | 配置级 checkpointer / 子图 | `main.py:1612` | v1 只用编译期 saver；无子图 | 能力边界 |
| P-22 | 并发 / 多分支 | `bulk_update_state` 多 superstep | v1 每次单 superstep；同 thread 可多次分叉 | 能力边界 |
| P-23 | 静态断点 replay / recovery | `_algo.py:155-185` · `_loop.py:946-951` | `static_ack` 水位同构；replay 保留 ack；断点前 replay 再次触发；`update_state` 清空 ack | SAME（载体差异属 B13F1 X-8） |

---

## 3. 差分场景组（D-01…D-17）

| # | 场景 | 断言 | 判词 |
|---|---|---|---|
| D-01 | 中间 checkpoint 重放 | 两侧重新执行后续节点，终态一致；原快照数量 / 内容不变 | SAME |
| D-02 | **正常终态** checkpoint 重放 | 两侧都**不执行节点**、终态一致；**不比较快照数**（上游写 fork checkpoint） | STRICTER（X-06） |
| D-03 | 重放中断点 | 两侧都重新触发中断；恢复后跑完；原 pending 不变 | SAME |
| D-04 | `update_state` 覆盖型 | 新快照 `values` = 基准 + 覆盖；parent = 基准；原快照不变 | SAME |
| D-05 | `update_state` 归约型 | 归约器追加（如 messages） | SAME |
| D-06 | `update_state` + `as_node` | `next` = 后继（含条件边 / fan-out）；`invoke(None)` 从后继继续；节点序列一致 | SAME |
| D-07 | `as_node` 歧义 / 不存在 | 两侧均 `InvalidUpdateError`；消息要点一致 | SAME |
| D-08 | 未挂 saver / 缺 `thread_id` | 两侧均 `ValueError`（含 `No checkpointer set` / 点名） | SAME（缺 thread STRICTER · X-05 同源） |
| D-09 | 显式 `checkpoint_id` 不存在 | freegraph `ValueError`；上游按版本可能空 / 抛 | STRICTER（X-05） |
| D-10 | `update_state` 返回载体 | freegraph `RunConfig`；上游 `RunnableConfig` | SAME（返回载体形态 · R-1；`config` 载体见 X-01） |
| D-11 | `context` 不持久化 | 快照 / metadata / scheduler / pending 中 `context` 次数 == 0 | DIFF（X-03） |
| D-12 | 历史枚举 / 顺序 | 原快照 + 新分支；倒序；原父链不变；`__start__` 排除 | SAME |
| D-13 | 多次重放 | 每次追加新分支；原快照逐项不变；parent 均指向同一分叉点 | SAME（freegraph-only 部分始终运行） |
| D-14 | `SqliteSaver` ↔ `MemorySaver` | 同一序列的 8 字段 / 父链 / 历史顺序一致 | SAME（双后端） |
| D-15 | 静态挂起重放 | `interrupts==()` + 静态标记；直接重放不要求动态载荷 | SAME |
| D-16 | 重放 / 分叉期间真异常 + 中断 | 中断留痕只写新 checkpoint；原 pending 零变化；异常 identity 不变 | SAME（更严不变量） |
| D-17 | 静态断点的重放 / 分叉 | replay 保留 ack；断点前 replay 再次暂停；`update_state` 清空 ack | SAME（B13F1 X-8） |

> **D-02 的证据**：实测上游线性图 history `4 → 5`，新增 `((), 'fork', 3)`；
> 但**没有节点重跑**。freegraph 按 SC-016 零新快照 ⇒ 这是 **STRICTER**，
> 不是 SAME。spec 的 P-12 / D-02 已改标 **STRICTER（X-06）**。
>
> **branch anchor 的口径**：非 no-op replay / 历史续跑先写一条 anchor（spec 裁定 10 / FR-026），
> 其在父链上的作用对应上游的 `source="fork"` 快照；D-01 / D-13 只比较节点序列 / 终态 /
> 父链 / 原快照完整性，**不把 anchor 与上游 fork 的快照数当判据**。

---

## 4. 偏离登记（X-01…X-06）

| # | 类别 | 被偏离的判据 | 理由 | 承接 / 追认 |
|---|---|---|---|---|
| X-01 | 自研区 ④（下游兼容适配层） | P-01b / D-10：`config` 双形态 | B7F3 CF-05 已冻结 | B7F3 · 本 feature |
| X-02 | 破已冻结契约面（B2F1） | `update_state` 返回 `RunConfig`（B2F1 冻结面；上游对照 P-01 为 SAME） | 上游 `RunnableConfig` + 时间旅行用法；R-1 | B2F1 知情 · 本 feature（唯一一次追认） |
| X-03 | 破已冻结契约面（B8F3） | P-16：`context` 不持久化 | B8F3 D-1 / D-3 已拍板 | B8F3 · 本 feature |
| X-04 | 自研区 ②（更严的恢复定位 · 上游静默污染 / 不确定） | P-14 | 上游可能按 config 的 checkpoint 树把 pending 写回旧快照；freegraph 取更确定的「最新快照」口径，防旧 id 误写历史 / 静默回退 | 本 feature · B10F1 知情 |
| X-05 | 更明确的失败信号 | P-03b / D-08 / D-09 | 与 B14F1 / B15F1 同源 | 本 feature |
| X-06 | **自研区 ②（上游自身缺陷 / 不确定）** | P-12 / D-02：**正常终态** replay 零新快照（不写 fork checkpoint） | 上游文档称 no-op，实测写 fork checkpoint（不重跑节点）⇒ 文档/实现不一致；freegraph 取文档口径 | 本 feature · 上游自身缺陷/不确定（②） |

> **已订正**：P-12 / D-02 已改 **STRICTER（X-06）**（**正常终态** replay 不写 fork checkpoint ·
> 零新快照 · SC-016）。X-06 归入自研区 **②（上游文档/实现不一致）**，只改标注，**不放松**任何判据。

---

## 5. 差分执行

```bash
.venv/bin/python -m pytest tests/differential/test_b16f1_time_travel_parity.py -q
```

- 上游 `langgraph` 在场 ⇒ 真跑；缺席 ⇒ skip（不是 fail）。
- 每条上游断言带版本 + `路径:行号`。
- 比较投影：节点序列 / 最终状态 / `next` / `values` / `tasks` / `interrupts` /
  异常类型 + 消息要点；`metadata` / `created_at` / config 载体按 B15F1 投影排除。
- 上游额外 `__start__` 快照排除（P-20）。
- **D-02 不比较快照数**（X-06）。
