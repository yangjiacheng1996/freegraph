# B13F1 人工验证记录 · 静态中断点 + `recursion_limit`

**日期**：2026-11-15 · **环境**：CPython **3.11.16** · Linux · 仓库 `.venv`  
**基线**：B13F1 之前 **1203 passed / 4 skipped**；本 feature 完成后 **1281 passed / 4 skipped**。

---

## 1. 验证环境

| 项 | 值 |
|---|---|
| Python | 3.11.16（隔离环境 `.venv`） |
| 上游取证 | `langgraph 1.2.11`（开发 / 测试侧 `differential` 组） |
| 运行命令 | `.venv/bin/python -m pytest -q` |
| 覆盖率 | `.venv/bin/coverage run --branch -m pytest -q` |
| 验收脚本 | `.venv/bin/python harness/demo/graph_core.py` |

---

## 2. 验证步骤

1. 全量回归：`.venv/bin/python -m pytest -q`；
2. 分支覆盖率：`.venv/bin/coverage run --branch -m pytest -q`，并检查
   `_static.py` / `_recursion.py` / `_fanout.py` 与 `superstep.py` 的**新增行**；
3. 一键验收：`.venv/bin/python harness/verification/B13F1/acceptance.py`；
4. 验收脚本：`.venv/bin/python harness/demo/graph_core.py`（M1 门面未就绪 ⇒ 退出码 2）；
5. 差分对跑：`.venv/bin/python harness/scripts/diff_parity.py -k D-`（含 D-38…D-49）；
6. 门禁：`gate_G21_dependencies.py` / `gate_G25_import_graph.py` /
   `gate_G29_contract_carrier.py` / `gate_G30_attribution.py`；
7. quickstart §1–§10 的等价场景由 `tests/runtime/test_static_interrupt.py` ·
   `test_static_interrupt_fanout.py` · `test_recursion_limit.py` ·
   `test_graph_spec_static.py` · `test_acceptance_script.py` 覆盖。

---

## 3. 实际输出

```text
$ .venv/bin/python -m pytest -q
1281 passed, 4 skipped

$ .venv/bin/coverage report --include="src/freegraph/runtime/_static.py,src/freegraph/runtime/_recursion.py,src/freegraph/runtime/_fanout.py"
_fanout.py      100%
_recursion.py   100%
_static.py      100%

# superstep.py：新增/变更行在 diff 覆盖率中缺失数 == 0
# （全文件 99% 的未覆盖分支均为 B13F1 之前的既有路径）

$ .venv/bin/python harness/verification/B13F1/acceptance.py
共 37 条断言 · 失败 0 条
B13F1 acceptance: PASS
exit=0

$ .venv/bin/python harness/demo/graph_core.py
[环境未就绪] compile() / invoke() 仍为桩（构建器 / 编译属 M2）
exit=2

$ .venv/bin/python harness/scripts/diff_parity.py -k D-
场景数 51 · 符合判词 51 · 失败 0
# D-38…D-49 全部符合判词

$ gate_G21_dependencies.py   → PASS
$ gate_G25_import_graph.py   → PASS
$ gate_G26_network_static.py → PASS
$ gate_G27_zero_egress.py    → PASS
$ gate_G29_contract_carrier.py → PASS（graph_core = ENV_NOT_READY）
$ gate_G30_attribution.py    → PASS（另有 8 条既有 spec 文案警告，非本 feature 源码）
```

---

## 4. 结论

- **A1（递归超限抛明确异常）**：通过；`GraphRecursionError` 原样传播，
  `.recursion_limit` / `.current_step` 如实。
- **A2（interrupt_before / interrupt_after）**：通过；before 目标执行 0 次、
  after 目标执行 1 次（fan-out N 次）；空载荷 / 恢复 / 最终节点 / 优先级均通过。
- **A3（软断言升级）**：`graph_core.py` 已升级为 `check(...)` + `GraphRecursionError`；
  L2 等价硬测试通过；端到端真跑按 **EV-1** 延至 B7F3。
- **SC-001…SC-024**：逐条由任务与测试承载（见 tasks.md 文末追溯表）；
  新增模块行 / 分支覆盖率 **100%**；`superstep.py` 新增行 diff 覆盖率 **100%**。
- **差分**：D-38…D-49 全部符合判词；上游缺失时 skip 的既有纪律未改变。

---

## 5. 遗留问题

| # | 事项 | 承接方 | 状态 |
|---|---|---|---|
| **EV-1** | `graph_core.py` 的 `case_recursion_limit` 端到端真跑依赖 `compile()` / `invoke()`；M1 以退出码 2 结束 | **B7F3**（D-3 · M2） | 已具名延期 |
| **T114** | F-1…F-10 与 X-1 / X-2 / X-6 / X-8 的**发起者追认** | 发起者 | ✅ **已追认（2026-11-15）** |
| **DIF-1** | 纯 fan-out × 静态断点的上游 `snapshot.next` / 任务保留未差分比对 | B13F1 本地 T076 | 已登记限制 |
| **G30** | 8 条既有 spec 文案警告（非本 feature 源码） | 既有文档 | 不阻塞本 feature |

---

## 6. 来源覆盖表

| 判据 / 需求 | 覆盖载体 |
|---|---|
| **V1–V10 · 一键验收** | `harness/verification/B13F1/acceptance.py`（37 条断言 · PASS） |
| A1 / SC-003 / SC-004 / SC-008 / SC-013 | `test_recursion_limit.py` · T053–T060 |
| A2 / SC-001 / SC-002 / SC-006 / SC-007 / SC-009 / SC-010 | `test_static_interrupt.py` · `test_static_interrupt_fanout.py` · T031–T048 · T073–T082 |
| A3 / SC-005 | `test_acceptance_script.py` · T098 · T100 · T102 |
| SC-011 / SC-012 | `test_interrupt_checkpoint.py` · `test_static_interrupt.py` · T018–T022 · T049–T052 |
| SC-014 / SC-015 / SC-016 / SC-017 | `test_graph_spec_static.py` · T002–T013 · T023–T029 · T090–T097 · T111 |
| SC-018 / SC-019 / SC-020 | 门禁 G21 / G25 / G26 / G27 / G29 + T030 · T095 · T110 · T113 |
| SC-021 | 本记录 + T008 · T103 · T112 · T114 |
| SC-022 | `parity_probe.py` D-38…D-49 + T101 · T102 · T115 |
| SC-023 / SC-024 | 覆盖率报告 + T109 · T001 · T030 · T102 · T106 · T108 · T110 |
| **FR-001…FR-032** | 逐条见 `tasks.md` 的「需求 ↔ 成功标准」与文末「任务 ↔ spec 追溯表」（32/32 有任务） |

---

## 7. 追认文字（已签字 · 2026-11-15）

### F-1…F-10（破冻结面 · 只增不删）

B13F1 按宪法 v1.8.0 的「破冻结面三条」登记并实施以下**兼容扩展**：

- **F-1**：`GraphSpec` 只增两个 keyword-only 字段，既有构造零改动；
- **F-2**：`_validate_graph_spec` 只增 V-22…V-25 的**调用点**（单一入口），
  B7F1 / B7F4 / B11F1 既有校验规则一条不改；
- **F-3**：`SchedulerState.to_checkpoint` / `from_checkpoint` **只增** `fanout` 键，
  缺键宽容；B11F1 的「不落盘」历史断言按「拆分而不删」保留；
- **F-4**：`run_graph` 的 `config` 注解放宽为 `RunConfig | Mapping | None`，
  不新增 `recursion_limit=` 关键字；
- **F-5**：`no_pending_interrupt` 拆分——静态 `suspension_kind` 合法，非静态仍抛；
- **F-6**：`graph_core.py` 的 `soft(...)` → `check(...)` + `GraphRecursionError`；
- **F-7**：README 软断言清单移除 `recursion_limit` 行，保留 C25 与规则文字；
- **F-8**：B7F1 低层入口只增 V-26（显式拒绝静态字段），签名 / 返回类型不变；
- **F-9**：挂起 metadata 只增 `suspension_kind` / `static_ack`（并镜像进 scheduler）；
- **F-10**：静态恢复完成时只写一次完成快照，不是每轮末快照。

### X-1 / X-2 / X-6 / X-8（结构性偏离）

- **X-1**：静态挂起在结果里补 `"__interrupt__": ()`（上游无该键）；
  承接方 **B7F3**（D-4）；理由：明确挂起信号 + 复用 `InterruptResult`；
- **X-2**：静态断点由 `GraphSpec` 字段承载（上游是 `compile()` 关键字）；
  承接方 **B7F2**（D-1 / D-2）；理由：M1 的 L2 图定义侧；
- **X-6**：低层 `run_super_step` / `run_super_steps` 收到非空静态字段时**显式拒绝**；
  理由：上游无此入口，低层返回类型冻结；
- **X-8**：检查点 metadata 增 `suspension_kind` / `static_ack`；
  承接方 **B14F1 / B15F1 / B16F1**（D-5 / D-6）；理由：空 `next` 的静态挂起必须可恢复。

**发起者签字 / 日期**：杨家成 · **2026-11-15**（T114 已确认）

---

## 8. B11F1 冻结面同步

F-3 已同步更新 B11F1 的 `contracts/send-contract.md` §5.1 · `data-model.md` I-12 ·
`tasks.md` T019 · `plan.md` PR-8 · `research.md` DR-02 / D-08 · `quickstart.md` DR-02 ·
`spec.md` D-3；「拆分而不删」的历史断言保留。**B11F1 追认**与上表一并于 **2026-11-15** 确认。
