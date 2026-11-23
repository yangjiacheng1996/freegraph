# Quickstart · B16F1 · `update_state` + 时间旅行回放

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) ·
**Contracts**: [update-state-contract.md](./contracts/update-state-contract.md) /
[time-travel-contract.md](./contracts/time-travel-contract.md) /
[put-parent-contract.md](./contracts/put-parent-contract.md) /
[upstream-parity.md](./contracts/upstream-parity.md)

> 本文件是**验收 / 跑通指南**（可执行）⇒ **不含**实现代码；实现细节归 `tasks.md`。
> 所有命令从仓库根目录执行。上游 `langgraph` 只作差分参照；缺席 ⇒ `SKIP`。
> 测试函数名以实现为准；下列命令按**整个测试文件**执行，避免 `-k` 未命中导致 0 用例。

---

## 0. 前置条件

```bash
# ① Python 3.11+（本机 .venv）
.venv/bin/python --version

# ② 开发期依赖（pytest）
.venv/bin/python -m pytest --version

# ③ 本 feature 包（editable）
.venv/bin/python -m pip install -e . 2>/dev/null || true

# ④ （差分）上游 langgraph 已装；缺席时差分 skip
.venv/bin/python -c "import langgraph; print('langgraph ok')"
```

**基线**（2026-11-23 实跑）：

```bash
.venv/bin/python -m pytest -q --tb=no
# ⇒ 2266 passed, 10 skipped
```

---

## 1. 从任意历史 checkpoint 重放（A1 · SC-001）

```bash
.venv/bin/python -m pytest tests/facade/test_b16f1_time_travel.py -v
```

| 项 | 期望 |
|---|---|
| 图 | 线性 `a → b → c`，挂 `MemorySaver` 或 `SqliteSaver`，`thread_id="t"` |
| 步骤 | 跑完 → `history = list(get_state_history(...))` → 对每个 `next` 非空的快照 `invoke(None, s.config)` |
| 断言 | 每次从该快照的 `next` 重新执行；终态一致；原快照 8 字段不变 |
| 判据 | SC-001 · FR-009 / FR-010 · 裁定 5 |

---

## 2. 正常终态重放为 no-op（SC-016）

```bash
.venv/bin/python -m pytest tests/facade/test_b16f1_time_travel.py -v
```

| 项 | 期望 |
|---|---|
| 步骤 | `final = [s for s in history if not s.next and (s.metadata or {}).get("suspension_kind") is None][0]` → `invoke(None, final.config)`（**正常终态**） |
| 断言 | 不执行节点；**freegraph 零新快照**（spec SC-016）；终态一致；`static_after` 的 `next==()` 不适用（按 FR-011 继续） |
| 判据 | SC-016 · FR-015 |

> ⚠️ 上游实测 final replay 会写一条 `source="fork"` 快照（不重跑节点）；
> freegraph 按 SC-016 为 **STRICTER**；差分 D-02 只比较执行 / 终态，不比较快照数
> （X-06 · 自研区 ②：上游文档/实现不一致 · spec 已订正）。

---

## 3. 分叉：覆盖型 + 归约型（A3 · SC-003）

```bash
.venv/bin/python -m pytest tests/facade/test_b16f1_update_state.py -v
```

| 项 | 期望 |
|---|---|
| schema | `x: int`（覆盖）+ `messages: Annotated[list, operator.add]`（归约） |
| 步骤 | `fork = update_state(cp.config, {"x": 9, "messages": ["new"]})` |
| 断言 | 新快照 `x == 9`；`messages == 旧 + ["new"]`；返回 `RunConfig`；`parent_config == cp.config` |
| 判据 | SC-003 · FR-001 / FR-006 · 裁定 1 / 4 |

---

## 4. 分叉不污染原历史（A2 · SC-002 / SC-008）

```bash
.venv/bin/python -m pytest tests/facade/test_b16f1_time_travel.py -v
```

| 项 | 期望 |
|---|---|
| 步骤 | 记录原 N 条快照的 8 字段 + pending writes → 重放 / 分叉多次 |
| 断言 | 原 N 条逐项不变；`get_state_history` = 原数量 + 新分支；倒序；原父链不变；**`update_state` 分叉后 `invoke(None, fork_config)` 不再写 anchor（分支快照兼任 anchor）** |
| 判据 | SC-002 / SC-008 / SC-014 · FR-014 / FR-026 · 裁定 3 / 10 |

---

## 5. 父链：分支首条指向分叉点（SC-007）

```bash
.venv/bin/python -m pytest tests/persistence/test_b16f1_put_parent.py -v
```

| 项 | 期望 |
|---|---|
| 步骤 | 同一操作序列分别在 `MemorySaver` / `SqliteSaver` 上：`put` 带显式 `checkpoint_id` |
| 断言 | 新快照 `parent_config` = 显式 id；无显式 id ⇒ 最新；新 id = MAX+1；两后端一致 |
| 判据 | SC-007 · FR-017 · 裁定 3 · put-parent-contract |

---

## 6. `as_node`：显式 / 推断 / 条件边 / fan-out（SC-009）

```bash
.venv/bin/python -m pytest tests/runtime/test_b16f1_update_state_runtime.py -v
```

| 项 | 期望 |
|---|---|
| 显式 | `next` = 该节点后继（出边 / 条件边 / fan-out）；`invoke(None)` 从后继继续 |
| 省略 | 从 `versions_seen` 推断最后更新者；歧义 ⇒ `InvalidUpdateError` |
| 不存在 | `InvalidUpdateError`（点名节点） |
| 判据 | SC-009 · FR-007 · 裁定 4 · D-06 / D-07 |

---

## 7. 静态挂起：replay 保留 ack / 分叉清空 ack（SC-011）

```bash
.venv/bin/python -m pytest tests/runtime/test_b16f1_static_replay.py -v
```

| 场景 | 期望 |
|---|---|
| 从静态快照 `invoke(None, static.config)` | 保留 `static_ack`，越过已确认断点继续；不要求动态载荷 |
| 从断点**之前** replay | 重放节点产生新写入 ⇒ 静态断点**再次暂停** |
| `update_state` 从静态快照分叉 | 新快照 `suspension_kind=None` / `static_ack=None`；后继命中断点则再次暂停 |
| 判据 | SC-011 · FR-011 · 裁定 4 / 6 · D-15 / D-17 |

---

## 8. 中断 + `Command(resume)` 最新定位（SC-011 / SC-014）

```bash
.venv/bin/python -m pytest tests/runtime/test_b16f1_resume_latest.py -v
```

| 项 | 期望 |
|---|---|
| 步骤 | 跑到 `interrupt()` 挂起 → 从历史中断点 replay → 再次暂停 → `invoke(Command(resume="x"), 同一 thread config)` |
| 断言 | 恢复**最新**暂停点；旧 `checkpoint_id` 被忽略；原快照 pending writes 零变化 |
| 判据 | SC-011 / SC-014 · FR-013 · 裁定 6 · X-04 |

---

## 9. 失败信号（SC-004 / SC-015）

```bash
.venv/bin/python -m pytest tests/facade/test_b16f1_update_state.py -v
```

| 场景 | 期望 |
|---|---|
| 未挂 saver（`update_state` / **显式 `checkpoint_id` 重放**） | `ValueError`（含 `No checkpointer set`） |
| 未挂 saver（无显式 id 的普通 `invoke` / 续跑） | 保持 B15F1 / B7F3 行为，**不**抛 `No checkpointer set` |
| 缺 `thread_id` | `ValueError`（点名） |
| 坏 `checkpoint_id` | `ValueError`（点名）；不回退 latest / fresh |
| 重放非空 `checkpoint_ns` | `ValueError`（v1 无子图） |
| 未知 key / 坏 `as_node` | `InvalidUpdateError` |
| 任意失败 | 存储零变化 |
| 判据 | SC-004 / SC-015 / SC-017 · FR-003 / FR-010 / FR-025 · 裁定 5 / 8 |

---

## 10. `context` 不持久化（SC-010）

```bash
.venv/bin/python -m pytest tests/facade/test_b16f1_update_state.py -v
```

| 断言 | 判据 |
|---|---|
| 新快照 / metadata / scheduler / pending writes 中 `context` 次数 == 0；`snapshot.config.context is None` | SC-010 · FR-012 · 裁定 7 |

---

## 11. 差分（D-01…D-17）

```bash
.venv/bin/python -m pytest tests/differential/test_b16f1_time_travel_parity.py -v
```

| 项 | 期望 |
|---|---|
| 上游在场 | 真跑；节点序列 / 终态 / `next` / `values` / `tasks` / `interrupts` 一致 |
| 上游缺席 | skip（不是 fail） |
| D-02 | 只比较「不执行节点 / **正常终态**」；**不比较快照数**（X-06 · 自研区 ② · spec 已订正） |
| 判据 | SC-012 · FR-023 |

---

## 12. 契约 / 门禁 / 全量

```bash
.venv/bin/python -m pytest tests/contracts/test_b16f1_contracts.py -q
.venv/bin/python -m pytest tests/facade/test_compiled_graph.py tests/facade/test_facade.py \
  tests/runtime/test_conditional_edge_surface.py -q
.venv/bin/python -m pytest -q --tb=no
```

| 项 | 期望 |
|---|---|
| L1 | `update_state` 返回 `RunConfig`；`config` 双形态；其余五方法零改动 |
| 依赖 / 环境 | `dependencies == []`；零 env；零出站；L4 只依赖 L1；L3 → L2 合法 |
| 全量 | 2266+ 基线 → 全绿（除上游 / Windows skip） |
| 判据 | SC-005 / SC-006 / SC-017 · R-9 |

---

## 13. 人工验收（SC-013）

```bash
# 按 harness/verification/B16F1/manual-verification.md 执行
.venv/bin/python -m pytest tests/runtime/test_b16f1_manual_record_guard.py -q
```

| 项 | 期望 |
|---|---|
| 五段式 | 环境 / 步骤 / 实际输出 / 结论 / 遗留问题 |
| 实测输出 | 非空：重放 → 状态一致；分叉 → 原历史不变；归约 / 覆盖合并 |
| 门禁 5 | fake 轮 + 真实模型轮（端点 / 调用次数 / 零出站归因） |
| 追认 | R-1 文字（`update_state` 返回类别 + config 注解放宽） |
| 判据 | SC-013 · FR-024 · R-1 / R-8 |

---

## 14. 文档守卫（SC-018）

```bash
.venv/bin/python -m pytest tests/runtime/test_b16f1_doc_guard.py -q
```

| 项 | 期望 |
|---|---|
| demo README | 不再含「`update_state(...)` 的签名」待锁定条目；新增锁定说明指向 spec 裁定 1 |
| `target.py` | 相对基线零改动（哈希 / 内容不变） |
| 判据 | SC-018 · FR-022 |

---

## 15. 手工最小示例（概念形态）

```python
from freegraph.graph import StateGraph, START, END
from freegraph.persistence import MemorySaver

# 1) 跑一张线性图
graph = (
    StateGraph(State)
    .add_node("a", a)
    .add_node("b", b)
    .add_edge(START, "a")
    .add_edge("a", "b")
    .add_edge("b", END)
    .compile(checkpointer=MemorySaver())
)
cfg = {"thread_id": "t"}
graph.invoke({"messages": []}, cfg)

# 2) 找第 2 步前的快照并重放
history = list(graph.get_state_history(cfg))
cp = next(s for s in history if s.next == ("b",))
graph.invoke(None, cp.config)

# 3) 分叉：改状态后继续
fork = graph.update_state(cp.config, {"messages": ["forked"]})
graph.invoke(None, fork)

# 4) 原历史仍完整；新分支首条 parent_config == cp.config
assert any(s.config == cp.config for s in graph.get_state_history(cfg))
```

> 以上只示调用形态；真实 schema / 节点 / 断言见对应测试。
