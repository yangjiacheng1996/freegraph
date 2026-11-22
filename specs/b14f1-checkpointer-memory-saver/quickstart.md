# Quickstart · B14F1 · Checkpointer 协议 + `MemorySaver`

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) ·
**Contracts**: [memory-saver-contract.md](./contracts/memory-saver-contract.md) /
[checkpoint-persistence-contract.md](./contracts/checkpoint-persistence-contract.md)

> 本文件是**验收 / 跑通指南**（可执行）⇒ **不含**实现代码；实现细节归 `tasks.md`。
> 所有命令从仓库根目录执行。上游 `langgraph` **仅差分测试侧**使用；缺席即 skip。

---

## 0. 前置条件

```bash
# ① Python 3.11+（本机 .venv）
.venv/bin/python --version

# ② 开发期依赖（pytest）
.venv/bin/python -m pytest --version

# ③ 本 feature 包（editable）
.venv/bin/python -m pip install -e . 2>/dev/null || true

# ④ （差分可选）上游钉版本
.venv/bin/python -m pip install langgraph==1.2.11 2>/dev/null || true
```

**基线**（2026-11-22）：

```bash
.venv/bin/python -m pytest -q --tb=no
# ⇒ 2111 passed, 8 skipped
```

---

## 1. 每一步的状态都被记下来（SC-001 / A1）

```bash
.venv/bin/python -m pytest tests/runtime/test_b14f1_step_snapshots.py -v -k "count"
```

| 项 | 期望 |
|---|---|
| 图 | `a → b` 两节点顺序图 |
| 注入 | `compile(checkpointer=MemorySaver())` + `RunConfig(thread_id="t")` |
| 断言 | `len(list(saver.list(cfg))) == 3`（初始 + `a` 后 + `b` 后）；最后一条 `next == ()` |
| 判据 | SC-001 · 裁定 5 · A1 |

> 补充断言：同一用例断言 `.scheduler["channel_versions"]` 与调度器当前版本**逐 key 相等**（SC-004 / FR-005）。

---

## 2. pending writes 写入后可取回（SC-002 / A2）

```bash
.venv/bin/python -m pytest tests/persistence/test_memory_saver.py -v -k "put_writes"
```

| 项 | 期望 |
|---|---|
| 步骤 | `cfg2 = saver.put(cfg, values={"x": 1}, metadata={...})` → `saver.put_writes(cfg2, writes=[("x", 2)], task_id="n")`（目标由 `cfg2.configurable["checkpoint_id"]` 指定） |
| 断言 | `saver.get_tuple(cfg2).pending_writes == (("n", "x", 2),)`；快照 `values` 仍为 `{"x": 1}` |
| 判据 | SC-002 · FR-003 · A2 |

> 补充断言：`put_writes` 缺 `checkpoint_id` ⇒ `KeyError`；指定 id 不存在 ⇒ `ValueError`；
> 普通通道跨调用同 `(task_id, idx)` 首次生效；保留通道最后生效（同调用内也覆盖）；
> `.pending_writes` 按 `(task_path, task_id, idx)` 升序（上游 `writes_sort_key`）。

> 补充断言：`get_tuple` 三态（指定 id 命中 / 未知 id ⇒ `None` / 未给 id ⇒ 最新）；直接调用 `get_tuple` / `put` / `put_writes` / `list(config)` 缺失 / 空 `thread_id` ⇒ `ValueError`，且 `list(None)` 合法（FR-015 / FR-018 / SC-010 / SC-014）。

---

## 3. 两个 thread 互不干扰（SC-003 / A3）

```bash
.venv/bin/python -m pytest tests/persistence/test_memory_saver.py -v -k "thread"
```

| 项 | 期望 |
|---|---|
| 步骤 | `thread-1` / `thread-2` 各写两条 |
| 断言 | 交叉读取命中数 == 0；`delete_thread("thread-1")` 后 `thread-2` 逐项不变 |
| 判据 | SC-003 · FR-004 · A3 |

---

## 4. `MemorySaver` 满足 `Checkpointer`（SC-006 / A4）

```bash
.venv/bin/python -m pytest tests/persistence/test_memory_saver.py -v -k "checkpointer"
```

| 项 | 期望 |
|---|---|
| 断言 | `isinstance(MemorySaver(), freegraph.contracts.Checkpointer) is True`；8 方法存在 |
| 别名 | `InMemorySaver is MemorySaver` |
| 边界 | `delete_for_runs` / `copy_thread` 抛 `NotImplementedError` |
| 判据 | SC-006 · FR-001 / FR-029 · A4 |

---

## 5. 挂起后用真实 `MemorySaver` 恢复（SC-014 / 人工 V-1）

```bash
.venv/bin/python -m pytest tests/runtime/test_b14f1_resume.py -v -k "dynamic"
```

| 项 | 期望 |
|---|---|
| 步骤 | `interrupt("approve?")` → 挂起 → `Command(resume="yes")` |
| 断言 | 第二次跑完；结果含 `answer=yes`；**只重跑被中断节点（从节点起点）**、已完成节点不重复；`interrupt()` 之后代码执行一次；历史继续追加 |
| 未挂 saver | `InterruptError(reason="checkpointer_required")` |
| 判据 | SC-014 · FR-028 · B10F1 V-1 |

---

## 6. 静态挂起 / F-10 不重复（SC-015）

```bash
.venv/bin/python -m pytest tests/runtime/test_b14f1_resume.py -v -k "static"
```

| 项 | 期望 |
|---|---|
| 步骤 | `interrupt_before=["b"]` 挂起 → 恢复 |
| 断言 | `.scheduler["suspension_kind"] == "static_before"`；`.snapshot.interrupts == ()`；恢复后完成快照只写一次 |
| 判据 | SC-015 · FR-019 · 裁定 5 |

---

## 7. fan-out / 屏障（SC-016 / SC-017）

```bash
.venv/bin/python -m pytest tests/runtime/test_b14f1_fanout_barrier.py -v
```

| 项 | 期望 |
|---|---|
| fan-out | 每个任务 `task_id == f"{node}:{id}"`；同节点多任务互不覆盖 |
| 屏障 | 暂停 → 恢复后目标不重复触发；`seen` 保留 |
| 判据 | SC-016 / SC-017 · FR-019 / FR-020 |

---

## 8. 真异常 + 中断留痕（SC-018）

```bash
.venv/bin/python -m pytest tests/runtime/test_b14f1_error_interrupts.py -v
```

| 项 | 期望 |
|---|---|
| 步骤 | 同一轮一个节点抛真异常、一个节点 `interrupt` |
| 断言 | 抛真异常；`get_tuple().pending_writes` 含 `__interrupt__`；异常 identity / 类型 / 消息与未挂 saver 一致 |
| 判据 | SC-018 · FR-021 · B10F1 X-5 / B12F1 X-4 消解 |

---

## 9. 节点 span 的 `checkpoint_id`（SC-019）

```bash
.venv/bin/python -m pytest tests/runtime/test_b14f1_spans.py -v
```

| 项 | 期望 |
|---|---|
| 挂 saver + tracer | 节点 span 的 `checkpoint_id` 非空，等于该轮起点快照 id；子 span 继承 |
| 不挂 saver | `checkpoint_id is None` |
| 判据 | SC-019 · FR-022 · `Span` 11 字段不变 |

---

## 10. 编译期校验（SC-013）

```bash
.venv/bin/python -m pytest tests/facade/test_b14f1_compile_validation.py -v
```

| 传入 | 期望 |
|---|---|
| `None` / `True` / `False` / `MemorySaver()` | 接受；`CompiledGraph.checkpointer` 记录原值 |
| `object()` / `"saver"` / `[]` | `TypeError`（点名期望类型） |
| 判据 | SC-013 · FR-010 · B7F2 X-4 消解 |

---

## 11. `on_checkpoint` 数据源（SC-020）

```bash
.venv/bin/python -m pytest tests/persistence/test_memory_saver.py -v -k "on_checkpoint"
```

| 项 | 期望 |
|---|---|
| 步骤 | `MemorySaver(on_checkpoint=cb)` 跑 `a → b` |
| 断言 | 回调次数 == 成功 `put` 次数；载荷与 `get_tuple().snapshot` 同形；回调抛错不回滚 |
| 边界 | `stream(checkpoints)` 伪造事件数 == 0（消费端归 B8F2 / B15F1） |
| 判据 | SC-020 · FR-023 |

---

## 12. `context` 不持久化（SC-021）

```bash
.venv/bin/python -m pytest tests/runtime/test_b14f1_step_snapshots.py -v -k "context"
```

| 项 | 期望 |
|---|---|
| 步骤 | `RunConfig(thread_id="t", context={"user": "a"})` 跑图 |
| 断言 | `snapshot.config.context is None`；`context` 在 metadata / scheduler / pending writes 中出现 0 次 |
| 判据 | SC-021 · FR-024 · B8F3 D-1 / D-3 |

> 补充断言：恢复轮节点看到的 `context` 来自**本次** `RunConfig`，不是快照；从快照还原 `context` 的次数 == 0（SC-021）。

---

## 13. 差分（SC-025）

```bash
# 上游在场
.venv/bin/python -m pytest tests/differential/test_b14f1_checkpoint_parity.py -v

# 上游缺席 ⇒ skip（不是 fail）
.venv/bin/python -m pytest tests/differential/test_b14f1_checkpoint_parity.py -v -k "not upstream"
```

| 项 | 期望 |
|---|---|
| 上游在场 | D-01…D-12 通过率 100%；D-13…D-15 按判词接受差异 |
| 上游缺席 | 全部 skip |
| 判据 | SC-025 · FR-033 / FR-035 |

---

## 14. Demo 硬断言 / 人工验收（SC-022 / SC-023）

```bash
# ① graph_core 硬断言（真实 MemorySaver + Command(resume=...)）
python harness/demo/graph_core.py
# ⇒ 退出码 0；case_interrupt_resume 无 soft(...)

# ② 一键验收（可选脚本，已交付）
.venv/bin/python harness/verification/B14F1/acceptance.py

# ③ 文档守卫
.venv/bin/python -m pytest tests/runtime/test_b14f1_manual_record_guard.py -v

# ④ 人工验证记录
# harness/verification/B14F1/manual-verification.md
# 必须含：环境 / 步骤 / 实际输出 / 结论 / 遗留问题
# 且含「interrupt → Command(resume=...) → 跑完」的真实输出
```

| 项 | 期望 |
|---|---|
| `harness/demo/README.md` | 待锁定清单中「`MemorySaver` 的模块路径」条目数 == 0 |
| `graph_core.py` | `case_interrupt_resume` 中 `soft(` 数 == 0；`check(` 覆盖断言 |
| 人工记录 | 五段齐全 + 恢复侧实测非空 |
| 判据 | SC-022 / SC-023 · FR-026 / FR-027 |

---

## 15. 全量回归 / 门禁

```bash
.venv/bin/python -m pytest -q --tb=no
# ⇒ 全绿（上游缺席的 skip 保留）

# 架构 / 门禁
.venv/bin/python -m pytest tests/contracts/test_architecture.py tests/facade/test_facade_gates.py -q
```

| 项 | 期望 |
|---|---|
| L4 依赖 | `freegraph.persistence` 只 import L1 + stdlib；L2 → L4 边数 0 |
| 门面 | `freegraph.graph` 不转出 `MemorySaver`；符号面零改动 |
| 冻结面 | L1 / `runtime.__all__` / `superstep.__all__` / `Span` 11 字段零改动 |
| 零出站 / 零 env | 依赖树新增第三方 == 0；env 读取点 == 0；出站调用 == 0 |
