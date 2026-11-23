# Quickstart · B15F1 · `SqliteSaver` + `get_state` / `get_state_history`

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) ·
**Contracts**: [sqlite-saver-contract.md](./contracts/sqlite-saver-contract.md) /
[state-read-contract.md](./contracts/state-read-contract.md) /
[checkpoints-stream-contract.md](./contracts/checkpoints-stream-contract.md)

> 本文件是**验收 / 跑通指南**（可执行）⇒ **不含**实现代码；实现细节归 `tasks.md`。
> 所有命令从仓库根目录执行。上游 SQLite 源码只作行为参照；运行时不可导入 ⇒ `SKIP`。

---

## 0. 前置条件

```bash
# ① Python 3.11+（本机 .venv）
.venv/bin/python --version

# ② 开发期依赖（pytest）
.venv/bin/python -m pytest --version

# ③ 本 feature 包（editable）
.venv/bin/python -m pip install -e . 2>/dev/null || true

# ④ （差分可选）上游 langgraph 已装；langgraph-checkpoint-sqlite 未装 ⇒ skip
```

**基线**（2026-11-22 实跑）：

```bash
.venv/bin/python -m pytest -q --tb=no
# ⇒ 2191 passed, 8 skipped
```

---

## 1. 跨实例 / 跨进程持久化（SC-003 / SC-019 / A3）

```bash
.venv/bin/python -m pytest tests/persistence/test_b15f1_cross_process.py -v
```

| 项 | 期望 |
|---|---|
| 步骤 | `with SqliteSaver.from_conn_string(path) as saver:` 跑 `a → b`；退出后新进程用同一 `path` 读 |
| 断言 | `get_tuple` / `get_state` 的 8 字段与写入时逐字段一致 |
| 判据 | SC-003 / SC-019 · FR-028 · A3 |

> 补充：`SqliteSaver(conn)` 与 `from_conn_string` 均可；`:memory:` 只要求同连接生命周期内可读。
> `from_conn_string` 退出后继续调用 ⇒ `sqlite3.ProgrammingError`。

---

## 2. `get_state` 字段完整（SC-002 / A2）

```bash
.venv/bin/python -m pytest tests/facade/test_b15f1_state_read.py -v -k "get_state_fields"
```

| 项 | 期望 |
|---|---|
| 图 | `a → b` 顺序图，挂 `SqliteSaver` + `RunConfig(thread_id="t")` |
| 断言 | 返回 `StateSnapshot`；`values` / `next` / `config` / `metadata` / `created_at` / `parent_config` / `tasks` / `interrupts` 全部可读；`config.configurable["checkpoint_id"]` 非空；`config.context is None` |
| 判据 | SC-002 · FR-013 / FR-015 · A2 |

---

## 3. 历史快照可枚举（SC-001 / A1）

```bash
.venv/bin/python -m pytest tests/facade/test_b15f1_state_read.py -v -k "history"
```

| 项 | 期望 |
|---|---|
| 步骤 | `list(compiled.get_state_history({"thread_id": "t"}))` |
| 断言 | 长度 == 成功 `put` 次数；`checkpoint_id` 严格递减；首元素最新、末元素初始 |
| 判据 | SC-001 · FR-016 / FR-017 · 裁定 9 · A1 |

> 补充：`limit=2` / `before=<id>` / `filter={"source": ...}` 与 `SqliteSaver.list` 同参数逐条一致；
> `limit <= 0` ⇒ 空；未知 id ⇒ `None` / 空。

---

## 4. pending writes 合并进 `values`（SC-025）

```bash
.venv/bin/python -m pytest tests/facade/test_b15f1_state_read.py -v -k "pending_values"
```

| 项 | 期望 |
|---|---|
| 步骤 | 写入快照后 `put_writes` 若干普通通道写入；调用 `get_state` |
| 断言 | 无 `checkpoint_id` ⇒ `values` 含按 C6 合并后的写入；带 `checkpoint_id` ⇒ 不合并；历史 ⇒ 不合并 |
| 判据 | SC-025 · FR-015 · 裁定 8 |

> 补充：合并只操作副本；存储快照 / 写入零变化；保留通道不进入 `values`。

---

## 5. 中断 `tasks` / `interrupts`（SC-008 / SC-027 / A2）

```bash
.venv/bin/python -m pytest tests/facade/test_b15f1_state_read.py -v -k "interrupt"
```

| 项 | 期望 |
|---|---|
| 步骤 | 节点 `interrupt("approve?")` 挂起；`get_state` / 历史 |
| 断言 | `interrupts` 与 `invoke` 结果 `__interrupt__` 逐项一致；`tasks` 为**上游 next-tasks**（`next` + `.scheduler["fanout"]`，**两源 id 域不同、互斥、不跨源去重**）：标准任务 `id=name=节点名`；`next` 来源 fan-out `id=运行时 task_key=f"{node}:{全局TaskId}"`；账本来源 fan-out `id=f"{node}:{本地index}"` 且 `interrupts==()`；pending 中断按运行时 `task_key` 附着；`Interrupt` 字段数 == 2 |
| 判据 | SC-008 / SC-027 · FR-018 / FR-037 · 裁定 13 · A2 |

> 补充：真异常 + 中断同现 ⇒ round-start 快照的 `next` / `fanout` + pending 中断重建；
> 即使 `snapshot.interrupts` 非空也不忽略新 pending 中断；不会混入上一轮完成态任务；
> 抛出的异常类型 / 消息 / identity 不变。

---

## 6. 静态挂起（SC-009）

```bash
.venv/bin/python -m pytest tests/facade/test_b15f1_state_read.py -v -k "static"
```

| 项 | 期望 |
|---|---|
| 步骤 | `interrupt_before` / `interrupt_after` 挂起 |
| 断言 | `interrupts == ()`；`suspension_kind` / `static_ack` 原样；`next` 可为空；`tasks` 为 next-tasks 投影（`interrupts==()`），**不是** `snapshot.tasks`，不伪造审批任务 |
| 判据 | SC-009 · FR-019 · 裁定 8 / 9 |

---

## 7. 删除会话（SC-012）

```bash
.venv/bin/python -m pytest tests/persistence/test_sqlite_saver.py -v -k "delete"
```

| 项 | 期望 |
|---|---|
| 步骤 | 两个线程各有快照；`delete_thread("t-1")` |
| 断言 | `get_tuple == None`、`get_state == None`、历史为空；`t-2` 不变；重复删除不抛；重建 id 从 1 开始 |
| 判据 | SC-012 · FR-010 |

---

## 8. 并发 / Windows（SC-004 / A4）

```bash
# Linux / macOS 本机
.venv/bin/python -m pytest tests/persistence/test_sqlite_saver_concurrency.py -v
```

| 项 | 期望 |
|---|---|
| 步骤 | 同一 `SqliteSaver` 实例 8 个线程并发 `put` / `get_tuple` |
| 断言 | 无异常、无数据串扰、id 唯一且单调；无 `database is locked` 泄漏 |
| 判据 | SC-004 · FR-011 / FR-027 · A4 |

> Windows：现有 `.github/workflows/ci.yml` 的 `windows-2025` × 3.11 / 3.14 作业真跑；
> 测试**不得**标 `linux_only`。跨进程只断言不损坏，不承诺严格串行。

---

## 9. `checkpoints` 流式事件（SC-014）

```bash
.venv/bin/python -m pytest tests/runtime/test_b15f1_stream_checkpoints.py -v
```

| 项 | 期望 |
|---|---|
| 步骤 | 挂 `SqliteSaver` / `MemorySaver`，`stream(..., stream_mode="checkpoints")` |
| 断言 | 事件数 == 本次运行成功 `put` 次数；每条四键完整；`payload` 是 `StateSnapshot`；无 saver / 无 `thread_id` ⇒ 0 条；不伪造历史 |
| 判据 | SC-014 · FR-022 · 裁定 10 |

> 其它六档（values / updates / tasks / debug / messages / custom）行为逐字不变；
> **只有 `checkpoints` mode 写 saver**；`stream + saver` **不恢复历史**，只追加本次运行快照。
> `payload` 的「同形」= 8 字段同构；`values` 为存储快照值，不保证等于 pending 合并结果；
> `tasks` / `interrupts` 为 **next-tasks 投影**，与 `get_state()` 对该 id 一致（不使用存储的
> 完成态 `snapshot.tasks`）。

---

## 10. 失败信号 / 序列化（SC-013 / SC-007）

```bash
.venv/bin/python -m pytest tests/persistence/test_sqlite_saver_failures.py tests/persistence/test_sqlite_saver_json.py -v -k "failure or json"
```

| 项 | 期望 |
|---|---|
| 不可 JSON 序列化 | `TypeError`；该次调用零写入 |
| pending `__interrupt__` | channel-aware 编码 `Interrupt→{value,id}`，读回为 `Interrupt`；不直接 `json.dumps` |
| `PregelTask.error` / `state` 非 `None` | `TypeError` |
| 磁盘满 / 权限 / 损坏 / 锁 | `sqlite3.Error` 子类原样传播；不吞 |
| 单次写失败 | 事务回滚；零残留 |
| `filter` 非法 key | `ValueError` |
| 判据 | SC-013 / SC-007 · FR-005 / FR-012 / FR-031 |

---

## 11. 差分（SC-018）

```bash
.venv/bin/python -m pytest tests/differential/test_b15f1_state_parity.py -v
```

| 项 | 期望 |
|---|---|
| 场景 | D-01…D-21 |
| 上游 SQLite 缺席 | `SKIP (source-aligned)`（不是 fail） |
| 上游在场 | 通过率 100% |
| 判据 | SC-018 · FR-026 |

---

## 12. 人工验收 + 全量回归（SC-020 / 门禁）

```bash
# 人工记录（五段式）必须存在且非空
test -s harness/verification/B15F1/manual-verification.md && echo OK

# 全量回归
.venv/bin/python -m pytest -q --tb=no

# Linux 门禁套件（至少这些；G27 为独立入口）
.venv/bin/python harness/scripts/gates/gate_G21_dependencies.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml
.venv/bin/python harness/scripts/gates/gate_G22_isolated_env.py
.venv/bin/python harness/scripts/gates/gate_G23_licenses.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml
.venv/bin/python harness/scripts/gates/gate_G24_config_layer.py
.venv/bin/python harness/scripts/gates/gate_G25_import_graph.py
.venv/bin/python harness/scripts/gates/gate_G26_network_static.py
.venv/bin/python harness/scripts/gates/gate_G27_zero_egress.py
.venv/bin/python harness/scripts/gates/gate_G30_attribution.py
```

| 项 | 期望 |
|---|---|
| 人工记录 | 环境 / 步骤 / 实际输出 / 结论 / 遗留问题；含持久化往返 + 并发实测 |
| 质量门禁 5 | **合规**：B15F1 自跑 fake 轮 + 真实模型轮；记录含模型端点 / 调用次数 / 零出站归因；B25F1 只做复验 |
| 全量回归 | 回到基线（除上游缺席 / 平台 skip） |
| 门禁 | G3 / G7 / G8 / G16 / G18 / G19 / G21 / **G22** / G23 / G24 / G25 / G26 / **G27** / G30 判绿 |
| 判据 | SC-020 / SC-005 / SC-023 · FR-029 |

---

## 附录 A · 一键跑本轮新增测试

```bash
.venv/bin/python -m pytest \
  tests/persistence/test_sqlite_saver.py \
  tests/persistence/test_sqlite_saver_failures.py \
  tests/persistence/test_sqlite_saver_json.py \
  tests/persistence/test_sqlite_saver_concurrency.py \
  tests/persistence/test_b15f1_cross_process.py \
  tests/facade/test_b15f1_state_read.py \
  tests/runtime/test_b15f1_stream_checkpoints.py \
  tests/contracts/test_b15f1_contracts.py \
  tests/differential/test_b15f1_state_parity.py \
  -q --tb=short
```

## 附录 B · 已知边界

| 边界 | 说明 |
|---|---|
| `stream` 只 `checkpoints` mode 写 saver | 其它六档保持 B8F2 v1 |
| `stream` 不恢复历史 | 只追加本次运行快照；恢复走 `invoke` |
| 跨进程并发写 | 只要求不损坏；不承诺严格串行 |
| `filter` dotted key | `SqliteSaver` 按上游 `json_extract`；`MemorySaver` 保持 B14F1 |
| `values` 中 tuple | JSON 往返变 list（X-05）；冻结字段仍重建 tuple |
| `delete_for_runs` / `copy_thread` | v1 `NotImplementedError` |
