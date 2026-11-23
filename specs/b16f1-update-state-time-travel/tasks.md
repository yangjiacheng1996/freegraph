---

description: "Task list for B16F1 · update_state + 时间旅行回放"
---

# Tasks: B16F1 · `update_state` + 时间旅行回放

**Input**: Design documents from `/specs/b16f1-update-state-time-travel/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) ·
[data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: **包含**。spec 的 FR-023 / FR-024 与宪法原则 VI「判据级可追溯」要求每条 SC 有可判定测试；
每个用户故事先写失败测试，再实现，再跑定向回归；差分 D-01…D-17 落 `tests/differential/`。

**Organization**: 按 `spec.md` 的 **5** 个用户故事分组；US1–US3 为 P1，US4–US5 为 P2。
Setup / Foundational / Polish 为跨切面，不带故事标签。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（**不同文件** / 无未完成依赖）
- **[Story]**: `US1`…`US5` —— 仅**用户故事阶段**的任务带
- 每条任务 MUST 带**精确文件路径**；行尾用 `⇒ FR-xxx · SC-xxx` 标注追溯（纯登记项可标 `⇒ R-x`）
- ⚠️ 同一文件的多项修改 MUST 串行；测试文件之间可并行

## 路径约定

- L1（只改 `update_state`）：`src/freegraph/contracts/protocols.py`
- L3（修改）：`src/freegraph/_stategraph.py`
- L2（新增 / 修改）：`src/freegraph/runtime/{_time_travel.py,superstep.py,_stream_checkpoint.py}`（`_checkpoint.py` 零改动，复用 `_metadata` / `config_for_checkpoint`）
- L4（修改 `put` 父链）：`src/freegraph/persistence/{memory.py,sqlite.py}`
- 测试：`tests/facade/` · `tests/runtime/` · `tests/persistence/` · `tests/contracts/` · `tests/differential/`
- 验收：`harness/verification/B16F1/`
- 文档：`README.md` · `harness/demo/README.md` · 下游提示词 `harness/features/{B24F1,B25F1,B20F1,B20F2}*.md`

---

## 基线 / 预登记红点（实施前先读）

**基线**（2026-11-23 实跑）：`.venv/bin/python -m pytest -q --tb=no` ⇒ **2266 passed, 10 skipped**。

| # | 预登记红点 | 处置任务 |
|---|---|---|
| **RED-1** | `tests/facade/test_compiled_graph.py::test_each_unready_method_raises_not_implemented_naming_owner` 断言 `update_state` 抛 `NotImplementedError` | T013 |
| **RED-2** | `tests/facade/test_facade.py::test_compile_returns_a_product_but_capability_methods_are_not_implemented` 同上 | T013 |
| **RED-3** | `tests/runtime/test_conditional_edge_surface.py::test_the_unimplemented_protocol_methods_still_name_their_owner` 同上 | T013 |
| **RED-4** | `tests/contracts/test_protocols.py` 未断言 `update_state` 返回 `RunConfig` / 双形态 `config` | T005 / T049 |
| **RED-5** | `tests/facade/test_facade_gates.py` 注释 / README `CompiledGraph` 行仍写 `update_state` 未交付 | T047 |

| # | 必须保持绿 | 说明 |
|---|---|---|
| **KEEP-1** | `tests/persistence/test_*` 的 B14F1 / B15F1 `put` / `put_writes` 既有用例 | 无显式 id ⇒ parent = 最新，行为零变化 |
| **KEEP-2** | `tests/facade/test_b15f1_state_read.py` / `tests/runtime/test_b15f1_stream_checkpoints.py` | 读取面 / stream 语义零改动 |
| **KEEP-3** | `tests/differential/parity_probe.py` 的 `_COMPILE_CAPABILITY_METHODS` | 只检查方法存在性，不改 |
| **KEEP-4** | 普通 `invoke` / `stream`（无 `checkpoint_id`）的节点序列 / 快照数 | 父链扩展只在显式 id 时生效 |

> **纪律**：RED-1…RED-3 MUST 按「**拆分而不删** + 判据只可更严」处置；
> KEEP-1…KEEP-4 MUST 保持绿；其余测试 MUST 保持绿；**MUST NOT** 写永久红的 CI。

## 行数预算（R-10 · 实施期实测）

| 项 | 立项书基线 | 本 tasks 计划增量 | 计划合计 | 实施期实测 |
|---|---|---|---|---|
| 实现 | 480 | +120~200（父链扩展 / anchor / 静态 / 中断组合） | 600~680 | 待填 |
| 测试 | 560 | +150~300（差分 / 守卫 / 双后端 / 边界） | 710~860 | 待填 |
| **合计** | **1,040** | **+270~500** | **1,310~1,540** | **待填** |

> **纪律**：超预算 MUST 按 plan **R-10** 如实登记；**MUST NOT** 削减任何 FR / SC 换绿。

---

<!-- TRACE_TABLES_START -->

## 追溯表（FR → 任务）

| # | 任务 |
|---|---|
| FR-001 | T003 / T013 / T020 / T024 / T025 |
| FR-002 | T020 / T024 / T044 |
| FR-003 | T014 / T016 / T024 / T040 / T044 |
| FR-004 | T011 / T012 / T040 |
| FR-005 | T009 / T018 / T026 / T033 |
| FR-006 | T020 / T022 / T027 |
| FR-007 | T011 / T012 / T020 / T021 / T022 / T027 |
| FR-008 | T021 / T022 / T023 |
| FR-009 | T014 / T015 / T017 / T018 / T019 |
| FR-010 | T014 / T016 / T040 |
| FR-011 | T035 / T037 |
| FR-012 | T021 / T042 |
| FR-013 | T029 / T034 / T036 / T038 / T039 |
| FR-014 | T014 / T015 / T028 / T029 / T030 / T031 / T032 / T033 |
| FR-015 | T014 / T017 |
| FR-016 | T045 |
| FR-017 | T006 / T007 / T008 / T009 / T010 / T026 / T056 |
| FR-018 | T004 / T005 / T013 / T025 / T049 / T056 |
| FR-019 | T041 / T045 |
| FR-020 | T053 |
| FR-021 | T003 / T049 |
| FR-022 | T047 / T048 / T057 |
| FR-023 | T002 / T046 |
| FR-024 | T050 / T051 |
| FR-025 | T040 / T043 |
| FR-026 | T015 / T017 / T018 / T028 / T031 / T037 |

## 追溯表（SC → 任务）

| # | 任务 |
|---|---|
| SC-001 | T014 / T017 / T019 / T054 |
| SC-002 | T014 / T015 / T019 / T028 / T054 |
| SC-003 | T020 / T022 / T027 / T054 |
| SC-004 | T014 / T016 / T040 / T054 |
| SC-005 | T049 / T054 |
| SC-006 | T004 / T005 / T013 / T020 / T024 / T025 / T049 / T054 |
| SC-007 | T006 / T007 / T008 / T009 / T018 / T023 / T026 / T033 / T054 |
| SC-008 | T015 / T028 / T030 / T032 / T033 / T054 |
| SC-009 | T011 / T012 / T020 / T021 / T022 / T027 / T054 |
| SC-010 | T021 / T023 / T042 / T054 |
| SC-011 | T034 / T035 / T036 / T037 / T038 / T039 / T054 |
| SC-012 | T002 / T046 / T054 |
| SC-013 | T001 / T050 / T051 / T054 |
| SC-014 | T015 / T029 / T031 / T034 / T038 / T054 |
| SC-015 | T005 / T011 / T012 / T024 / T040 / T043 / T044 / T054 |
| SC-016 | T014 / T017 / T054 |
| SC-017 | T009 / T010 / T014 / T016 / T030 / T040 / T041 / T045 / T053 / T054 |
| SC-018 | T047 / T048 / T054 / T057 |

<!-- TRACE_TABLES_END -->

## Phase 1: Setup（共享基础设施）

**Purpose**: 建立基线、测试骨架与 L2 模块骨架

- [X] T001 跑既有测试套件 `.venv/bin/python -m pytest -q --tb=no`，把 **2266 passed / 10 skipped** 写入 `harness/verification/B16F1/manual-verification.md` 的「环境」段（先建最小五段式骨架）；**并按宪法 v1.11.0 实测复核冻结断言**：在临时副本按本 feature 落地形态（`update_state` 落地 + `put` 显式父链）改动源码 ⇒ 跑既有套件 ⇒ 实测采集变红断言，逐条核对 plan 的 RED-1…RED-5 是否完整（缺失 ⇒ 补登记，带 `文件:行号` + 变红原因）⇒ R-8 / R-15 · SC-013
- [X] T002 [P] 创建测试骨架：`tests/facade/test_b16f1_update_state.py` · `tests/facade/test_b16f1_time_travel.py` · `tests/runtime/test_b16f1_update_state_runtime.py` · `tests/runtime/test_b16f1_replay_anchor.py` · `tests/runtime/test_b16f1_static_replay.py` · `tests/runtime/test_b16f1_resume_latest.py` · `tests/runtime/test_b16f1_pending_protection.py` · `tests/runtime/test_b16f1_manual_record_guard.py` · `tests/runtime/test_b16f1_doc_guard.py` · `tests/persistence/test_b16f1_put_parent.py` · `tests/contracts/test_b16f1_contracts.py` · `tests/differential/test_b16f1_time_travel_parity.py` ⇒ FR-023 · SC-012 · SC-018
- [X] T003 [P] 创建 `src/freegraph/runtime/_time_travel.py` 骨架（署名头 + 模块 docstring 为首个语句 + `__all__=[]`；**不 import** L3 / L4 / 第三方）⇒ FR-001 · FR-021

**Checkpoint**: 基线 / 骨架就绪；可开始 Foundational。

---

## Phase 2: Foundational（阻塞性前置 · 所有故事共享）

**Purpose**: L1 协议、L4 父链、L2 父链推进与基准 / `as_node` 助手

**⚠️ CRITICAL**: 本阶段完成前，任何用户故事都不得开始实现。

- [X] T004 修改 `src/freegraph/contracts/protocols.py`：`CompiledGraph.update_state` 的 `config` 注解放宽为 `RunConfig | Mapping[str, Any] | None`，返回类别改为 `RunConfig`；同步 docstring 的签名表与「由 B16F1 交付」注记（**拆分而不删**）⇒ FR-018 · SC-006
- [X] T005 [P] 修改 `tests/contracts/test_protocols.py`：新增 `update_state` 返回 `RunConfig` / `config` 双形态注解断言；保留方法集恰 6 个断言 ⇒ FR-018 · SC-006 · SC-015
- [X] T006 修改 `src/freegraph/persistence/memory.py` 的 `put`：`configurable["checkpoint_id"]` 非空 ⇒ parent = 该 id（不存在 ⇒ `ValueError`，点名 `checkpoint_id`）；缺失 / 空串 ⇒ 保持最新；快照 / 回调的 `parent_config` 同步 ⇒ FR-017 · SC-007
- [X] T007 [P] 修改 `src/freegraph/persistence/sqlite.py` 的 `put`：同上；`parent_checkpoint_id` 列 = 显式 id；事务内校验存在性；`on_checkpoint` 快照的 `parent_config` 同步 ⇒ FR-017 · SC-007
- [X] T008 [P] 在 `tests/persistence/test_b16f1_put_parent.py` 写双后端失败测试：显式 id ⇒ parent = 该 id；无 id ⇒ 最新；新 id = MAX+1；不存在 ⇒ `ValueError`；先写测试并确认红 ⇒ FR-017 · SC-007
- [X] T009 修改 `src/freegraph/runtime/superstep.py` 的 `_run_graph_loop`：每次 `put_step` / `_write_suspend` / `_clear_static_suspension` 用 `config_for_checkpoint(run_config, current_checkpoint_id)`（current 为空则原 `run_config`）；每次 `put` 后推进 `current_checkpoint_id`；error interrupts 保持既有 `config_for_checkpoint` ⇒ FR-005 · FR-017 · SC-007 · SC-017
- [X] T010 [P] 修改 `src/freegraph/runtime/_stream_checkpoint.py` 的调用点（`prepare` / `after_result` / `on_interrupt`）：调用 `put_initial` / `put_step` / `_write_suspend` 时用当前 id 作 parent；`prepare` 的 `get_tuple` 用**仅 thread_id** 的 config（stream v1 不恢复历史）⇒ FR-017 · SC-017
- [X] T011 在 `src/freegraph/runtime/_time_travel.py` 实现基准定位 + `as_node` 助手：`resolve_base(cfg, saver)` · `infer_as_node(state, spec)` · `resolve_as_node(state, spec, as_node)`；镜像上游「单节点兜底 + `versions_seen`」，**MUST NOT** 回退 `node_versions` / 入口节点；错误消息按 spec 裁定 8 ⇒ FR-004 · FR-007 · SC-009 · SC-015
- [X] T012 [P] 在 `tests/runtime/test_b16f1_update_state_runtime.py` 写基准 / `as_node` 失败测试（显式 / 单节点兜底 / 推断 / 歧义 / 不存在 / 空历史），先确认红 ⇒ FR-004 · FR-007 · SC-009 · SC-015
- [X] T013 [P] 拆分三处冻结断言（**在 US2 实现 T024 / T025 之前执行**，RED-1…RED-3）：`tests/facade/test_compiled_graph.py` · `tests/facade/test_facade.py` · `tests/runtime/test_conditional_edge_surface.py`；改为「无 saver ⇒ `ValueError`；有 saver ⇒ `RunConfig`」正面断言（**拆分而不删**）⇒ FR-001 · FR-018 · SC-006

**Checkpoint**: L1 / L4 父链 / L2 助手就绪；US1–US5 可开始。

---

## Phase 3: User Story 1 - 从历史某一步重放（Priority: P1）🎯 最小可验收切片

**Goal**: 从任意历史 checkpoint 重放；显式 id 不存在即失败；**正常终态** no-op；非 no-op replay（既有历史快照起）先写 branch anchor；`update_state` 分支快照兼任 anchor，分叉后不再写额外 anchor。

**Independent Test**: 线性图 `a → b → c` 的每个 `next` 非空历史快照 `invoke(None, s.config)` 都重新执行后续节点；**正常终态** no-op；原历史不变。

### Tests for User Story 1

- [X] T014 [P] [US1] 在 `tests/facade/test_b16f1_time_travel.py` 写重放测试：每个历史点各一例、**正常终态** no-op、显式 id 不存在 ⇒ `ValueError`、**显式 `checkpoint_id` 重放无 saver / 非空 `checkpoint_ns` ⇒ `ValueError`**；并覆盖 `invoke(state_dict, historical.config)` 属 B7F3 续跑、不是 replay，但按裁定 10 写 anchor、仍只追加；另断言**无显式 id 的普通 `invoke` 未挂 saver 行为不变**；先确认红 ⇒ FR-003 · FR-009 · FR-010 · FR-014 · FR-015 · FR-026 · SC-001 · SC-002 · SC-016 · SC-017
- [X] T015 [P] [US1] 在 `tests/runtime/test_b16f1_replay_anchor.py` 写 anchor / 父链测试：非 no-op replay（既有历史快照起）先追加 anchor；后续快照 parent = anchor / 前一条；原快照不变；**正常终态**不写 anchor；`static_after` 的 `next==()` 仍写 anchor 并继续；非空 input dict（B7F3 续跑）同受 anchor 保护；**`update_state` 分叉后 `invoke(None, fork_config)` 不追加 anchor，历史增量 = 分支快照 + 执行快照** ⇒ FR-009 · FR-014 · FR-026 · SC-002 · SC-008 · SC-014

### Implementation for User Story 1

- [X] T016 [US1] 修改 `src/freegraph/runtime/superstep.py` 的 `_first_graph`：显式 `checkpoint_id` 非空且 `get_tuple` 为 `None` ⇒ `ValueError`（点名 `checkpoint_id`）；**仅该显式 id 分支**：无 saver / `True` / `False` ⇒ `ValueError`（消息含 `No checkpointer set`），非空 `checkpoint_ns` ⇒ `ValueError`；不得回退 latest / fresh；**无显式 id 的普通 `invoke` 行为不变**（FR-003 的「重放」分支）⇒ FR-003 / FR-010 · SC-004 · SC-017
- [X] T017 [US1] 在 `src/freegraph/runtime/superstep.py` 实现「no-op 判定 + branch anchor 写入」：**正常终态**（`next==()` 且无 fanout / 无静态 / 无 pending）且 `input` 为 None 或空 dict ⇒ 不写；**显式 id 指向 `update_state` 产出的分支快照（`fork_config`）⇒ 该分支快照兼任 anchor，不写额外 anchor**（分支快照识别由 `update_state` 在 L2 侧记录 id / 内部账本私有标记承担，不改公开面）；否则（`next` / fanout / 静态 / pending / 非空 input dict）`put` 一条 anchor（parent = 基准；values / next / 静态标记 / scheduler 同基准；`interrupts=()` / `tasks=()`）⇒ FR-009 · FR-015 · FR-026 · SC-001 · SC-008 · SC-016
- [X] T018 [US1] 修改 `src/freegraph/runtime/superstep.py`：写 anchor 时设 `current_checkpoint_id` = anchor id；若基准是 `update_state` 分支快照则直接设为其 id（**不写额外 anchor**）；把基准 history 的 pending / 静态 ack 继续用于执行；与 T009 的父链推进一致 ⇒ FR-005 · FR-009 · SC-007 · SC-008
- [X] T019 [US1] 运行 `tests/facade/test_b16f1_time_travel.py` + `tests/runtime/test_b16f1_replay_anchor.py`，在 `MemorySaver` / `SqliteSaver` 双后端修正到绿；覆盖正常终态 / static_after / `invoke(dict, historical.config)` ⇒ FR-009 · SC-001 · SC-002

**Checkpoint**: US1 独立可验收（A1 的重放部分）。

---

## Phase 4: User Story 2 - 改状态再继续（分叉）（Priority: P1）

**Goal**: `update_state` 按 C6 合并、`as_node` 后继、返回新分支 `RunConfig`；原历史不破坏。

**Independent Test**: `fork = graph.update_state(cp.config, values)` ⇒ 新快照合并正确、parent = cp；`invoke(None, fork)` 从后继继续；返回 `RunConfig`。

### Tests for User Story 2

- [X] T020 [P] [US2] 在 `tests/facade/test_b16f1_update_state.py` 写 facade 测试：签名 / config 三形态 / 返回 `RunConfig` / 覆盖 / 归约 / 未知 key / `as_node` 显式 / parent ⇒ FR-001 · FR-002 · FR-006 · FR-007 · SC-003 · SC-006 · SC-009
- [X] T021 [P] [US2] 在 `tests/runtime/test_b16f1_update_state_runtime.py` 写 runtime 测试：`next` = 后继（出边 / 条件边 / fan-out）、静态标记清空、pending 不复制、`context` 不透出；先确认红 ⇒ FR-007 · FR-008 · FR-012 · SC-009 · SC-010

### Implementation for User Story 2

- [X] T022 [US2] 在 `src/freegraph/runtime/_time_travel.py` 实现 `update_state` 流水线：`_restore_scheduler` / `_restore_channels` → 清空 `state.fanout` → `_evaluate_source_routes` → `_commit_outcome(task_id=0)` → `_merge_writes` → `_clear_step_end` → `_determine_triggers` ⇒ FR-006 · FR-007 · FR-008 · SC-003 · SC-009
- [X] T023 [US2] 在 `src/freegraph/runtime/_time_travel.py` 组装新快照：`values` / `next` / `metadata`（`interrupts=()` / `tasks=()` / `suspension_kind=None` / `static_ack=None` / `scheduler`）；`put` 用 `config_for_checkpoint(cfg, base_id)`；返回新 `RunConfig` ⇒ FR-008 · SC-007 · SC-010
- [X] T024 [US2] 修改 `src/freegraph/_stategraph.py` 的 `update_state`：替换 `NotImplementedError`，做 `Mapping` / `as_node` / saver / config 校验，调用 L2 `_time_travel.update_state`；不在门面层翻译 config ⇒ FR-001 · FR-002 · FR-003 · SC-006 · SC-015
- [X] T025 [US2] 同步 `src/freegraph/_stategraph.py` 的 `update_state` docstring / 注解为锁定签名与 `RunConfig` 返回；保留 L3 其它方法零改动 ⇒ FR-001 · FR-018 · SC-006
- [X] T026 [US2] 验证新 id = MAX+1、`parent_config` = 基准、双后端一致；修正 `src/freegraph/runtime/_time_travel.py` / `src/freegraph/persistence/memory.py` / `src/freegraph/persistence/sqlite.py` 的偏差 ⇒ FR-005 · FR-017 · SC-007
- [X] T027 [US2] 运行 `tests/facade/test_b16f1_update_state.py` + `tests/runtime/test_b16f1_update_state_runtime.py`，并补 reducer / 覆盖 / 条件边 / fan-out 用例，修到绿 ⇒ FR-006 · FR-007 · SC-003 · SC-009

**Checkpoint**: US2 独立可验收（A3）。

---

## Phase 5: User Story 3 - 重放不产生历史污染（Priority: P1）

**Goal**: 重放 / 分叉多次后原快照 8 字段与 pending writes 零变化；历史仍倒序可枚举；分支结构由 `parent_config` 表达。

**Independent Test**: 记录原 N 条快照的 8 字段 + pending；重放 / 分叉多次后逐项不变；`get_state_history` 数量 = 原 + 新分支；顺序倒序。

### Tests for User Story 3

- [X] T028 [P] [US3] 在 `tests/facade/test_b16f1_time_travel.py` 写历史完整性测试：原 8 字段 / pending 零变化、多次分叉、每分支首条 parent 正确、倒序可枚举；**分叉后 `invoke(None, fork_config)` 不再写 anchor，历史增量 = 分支快照 + 执行快照** ⇒ FR-014 · SC-002 · SC-008
- [X] T029 [P] [US3] 在 `tests/runtime/test_b16f1_pending_protection.py` 写 pending 保护测试：重放 / 分叉期间的 `__resume__` / 真异常中断留痕只落新 checkpoint（可落分支快照 / anchor 或后续新快照）；原历史快照 pending 零变化 ⇒ FR-013 · FR-014 · SC-014
- [X] T030 [P] [US3] 在 `tests/persistence/test_b16f1_put_parent.py` 写双后端历史一致性测试：同序列的 8 字段 / 父链 / 顺序一致（`created_at` 只比格式）⇒ FR-014 · SC-008 · SC-017

### Implementation for User Story 3

- [X] T031 [US3] 在 `src/freegraph/runtime/superstep.py` / `src/freegraph/runtime/_time_travel.py` 加「pending writes 只落新 checkpoint」的守卫 / anchor 保证；**分支快照兼任 anchor 时允许首轮 pending 落该分支快照，但 MUST NOT 回写原历史快照**；修正任何写原快照的路径 ⇒ FR-014 · SC-014
- [X] T032 [US3] 确认历史仍是**扁平倒序列表**、不提供分支树 / 按分支枚举 API；在 `tests/facade/test_b16f1_time_travel.py` 中断言（不新增 API）⇒ FR-014 · SC-008
- [X] T033 [US3] 在 `tests/facade/test_b16f1_time_travel.py` 验证同一 thread 多次分叉 / 每分支父链独立接续；修正 `src/freegraph/runtime/superstep.py` 的父链回退 latest 路径 ⇒ FR-005 · FR-014 · SC-007 · SC-008

**Checkpoint**: US3 独立可验收（A2）。

---

## Phase 6: User Story 4 - 中断 / 静态挂起与时间旅行的组合（Priority: P2）

**Goal**: 动态中断重放可再次暂停并恢复最新点；静态快照 replay 保留 ack；从断点前 replay 再次暂停；`update_state` 清空 ack。

**Independent Test**: 动态中断重放 → 新暂停点 → `Command(resume)` 跑完；静态快照 `invoke(None, ...)` 越过已确认断点；断点前 replay 再次暂停。

### Tests for User Story 4

- [X] T034 [P] [US4] 在 `tests/runtime/test_b16f1_resume_latest.py` 写动态中断组合测试：历史中断点 replay 再次暂停；`Command(resume)` 恢复最新点；旧 pending 不变 ⇒ FR-013 · SC-011 · SC-014
- [X] T035 [P] [US4] 在 `tests/runtime/test_b16f1_static_replay.py` 写静态组合测试：静态快照 replay 保留 ack；断点前 replay 再次暂停；`update_state` 清空 ack ⇒ FR-011 · SC-011

### Implementation for User Story 4

- [X] T036 [US4] 修改 `src/freegraph/runtime/superstep.py` 的 `_resume_graph`：`get_tuple` 使用仅 `thread_id` 的 config（忽略旧 `checkpoint_id`）；`snapshot_config` = 最新；`__resume__` 只写最新 ⇒ FR-013 · SC-011
- [X] T037 [US4] 在 `src/freegraph/runtime/superstep.py` / `_time_travel.py` 落实静态 ack 分流：replay 使用基准 `static_ack`、anchor 复制静态标记；`update_state` 清空 `suspension_kind` / `static_ack` ⇒ FR-011 · SC-011
- [X] T038 [US4] 在 `src/freegraph/runtime/superstep.py` / `tests/runtime/test_b16f1_resume_latest.py` 落实「旧挂起」边界：从更早历史点分叉时旧 pending 保留在旧快照、不自动复制；恢复旧中断需先 replay 旧快照；加断言 ⇒ FR-013 · SC-011 · SC-014
- [X] T039 [US4] 在 `tests/runtime/test_b16f1_resume_latest.py` 验证 `Command(resume)` 的既有失败信号（未挂 saver / 无挂起 / 歧义）不变；确认 `src/freegraph/runtime/superstep.py` 不写历史 pending ⇒ FR-013 · SC-011

**Checkpoint**: US4 独立可验收（中断 / 静态组合）。

---

## Phase 7: User Story 5 - 明确的失败与边界（Priority: P2）

**Goal**: 起点不存在 / thread 不存在 / 未挂 saver / 非法写入等立即失败；v1 能力边界明确；`context` 不持久化。

**Independent Test**: 逐项构造失败场景，断言异常类型 + 消息点名 + 存储零变化；边界能力不实现。

### Tests for User Story 5

- [X] T040 [P] [US5] 在 `tests/facade/test_b16f1_update_state.py` 写失败信号测试：未挂 saver / 缺 `thread_id` / 坏 `checkpoint_id` / 未知 key / 坏 `as_node` / 歧义；并在 `tests/facade/test_b16f1_time_travel.py` 写**显式 `checkpoint_id` 重放**无 saver / `True` / `False` / 非空 `checkpoint_ns` ⇒ `ValueError`；另断言**无显式 id 的普通 `invoke` 未挂 saver 不抛 `No checkpointer set`**；断言存储零变化 ⇒ FR-003 · FR-004 · FR-010 · FR-025 · SC-004 · SC-015 · SC-017
- [X] T041 [P] [US5] 在 `tests/facade/test_b16f1_update_state.py` 写能力边界测试：`task_id` 不存在 / `values=None` ⇒ `TypeError` / fresh-thread ⇒ `ValueError` / `stream` 不回放 / 无分支树 API ⇒ FR-019 · SC-017
- [X] T042 [P] [US5] 在 `tests/facade/test_b16f1_update_state.py` + `tests/runtime/test_b16f1_update_state_runtime.py` 写 `context` 非持久化测试：快照 / metadata / scheduler / pending 中 `context` 次数 == 0；`config.context is None` ⇒ FR-012 · SC-010

### Implementation for User Story 5

- [X] T043 [US5] 在 `src/freegraph/runtime/_time_travel.py` / `src/freegraph/_stategraph.py` 落实失败信号：复用 `ValueError` / `TypeError` / `InvalidUpdateError`；消息点名 `thread_id` / `checkpoint_id` / 节点 / key；不新增 L1 异常 ⇒ FR-025 · SC-015
- [X] T044 [US5] 在 `src/freegraph/runtime/_time_travel.py` 落实 config 校验：`RunConfig` / 映射 / `None`；裸 `str` / 数字 ⇒ `TypeError`；缺 `thread_id` / 非空 `checkpoint_ns` ⇒ `ValueError` ⇒ FR-002 · FR-003 · SC-015
- [X] T045 [US5] 在 `tests/contracts/test_b16f1_contracts.py` 确认 v1 不实现 / 不暴露：`delete_for_runs` / `copy_thread` 仍 `NotImplementedError`、无 async / `Store` / Postgres / 分支树；补 guard 断言 ⇒ FR-016 · FR-019 · SC-017

**Checkpoint**: US5 独立可验收（A3 的失败 / 边界部分）。

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 差分、文档守卫、人工验收、下游接线、上游 spec 回溯修订、全量回归（冻结断言已在 Foundational T013 处理）

- [X] T046 [P] 在 `tests/differential/test_b16f1_time_travel_parity.py` 落 D-01…D-17；上游缺席 ⇒ skip；D-02 只比较执行 / **正常终态**，**不比较快照数** ⇒ FR-023 · SC-012
- [X] T047 [P] 更新 `tests/facade/test_facade_gates.py` 的 `update_state` 注释 / 白名单（如需）+ `README.md` 的 `CompiledGraph` 行（不再写「由 B16F1 交付」）⇒ FR-022 · SC-018
- [X] T048 [P] 更新 `harness/demo/README.md`：移除「`update_state(...)` 的签名」待锁定行，补锁定说明指向 spec 裁定 1；`harness/demo/target.py` 零改动 ⇒ FR-022 · SC-018
- [X] T049 [P] 完成 `tests/contracts/test_b16f1_contracts.py`：L1 返回类别 / 双形态 config、无新增 L1 异常、`persistence.__all__` 不变、门面无 L4、零依赖 / 零 env / 零出站、ARCH-1 / L2 不 import L4 ⇒ FR-018 · FR-021 · SC-005 · SC-006
- [X] T050 [P] 完成 `harness/verification/B16F1/manual-verification.md`：五段式 + 非空重放 / 分叉 / 合并实测 + fake 轮 + 真实模型轮（端点 / 调用次数 / 零出站归因）+ R-1 追认文字 ⇒ FR-024 · SC-013
- [X] T051 完成 `tests/runtime/test_b16f1_manual_record_guard.py`：文档守卫断言（五段 / 非空输出 / fake+真实模型 / R-1），必须在 T050 之后运行 ⇒ FR-024 · SC-013
- [X] T052 [P] 下游承接接线：在 `harness/features/B24F1_打包分发与兼容矩阵.md` · `B25F1_双跑验收与迁移说明.md` · `B20F1_本地Trace存储JSONL.md` · `B20F2_Trace查询API与SQLite后端.md` 追加「下游承接（B16F1）」节（只接线 · 逐条最小改动）；B26 v2 UI / Postgres v2 无提示词文件 ⇒ 在 B24F1 矩阵 / plan 记录口径 ⇒ R-14
- [X] T053 跑全量 `tests/`：`.venv/bin/python -m pytest -q --tb=no` + 既有门禁 `harness/scripts/gates/`（G3 / G7 / G8 / G16 / G18 / G19 / G21 / G22 / G23 / G24 / G25 / G26 / G27 / G30）；修复回归到全绿（除上游 / Windows skip）⇒ FR-020 · SC-017
- [X] T054 按 `quickstart.md` 逐节跑可执行验收（重放 / **正常终态** no-op / 合并 / 历史 / 父链 / 静态 / resume / 失败 / context / 差分 / 全量）并记录结果 ⇒ SC-001 · SC-002 · SC-003 · SC-004 · SC-005 · SC-006 · SC-007 · SC-008 · SC-009 · SC-010 · SC-011 · SC-012 · SC-013 · SC-014 · SC-015 · SC-016 · SC-017 · SC-018
- [X] T055 复核 `specs/b16f1-update-state-time-travel/{spec,plan,tasks}.md` 的 FR-001…**FR-026** / SC-001…SC-018 判据级覆盖、行数预算（R-10）与 trace 表一致性；补齐遗漏任务 / 测试 ⇒ R-10
- [X] T056 [P] 上游 spec / data-model 回溯修订**核对已落 + 补齐遗漏**（**拆分而不删**，保留历史注解）：核对 `specs/b2f1-contracts-protocols/spec.md`（Q8 / FR-005⑥：自 B16F1 起 `update_state` 返回 `RunConfig`、`config` 双形态）与 `data-model.md`（§2.5 表加注记）；核对 `specs/b14f1-checkpointer-memory-saver/spec.md` 裁定 6、`specs/b15f1-sqlite-saver-state-history/spec.md` 裁定 4 / 5、`specs/b7f3-invoke-full-state/spec.md` CF-05 与 `specs/b7f3-invoke-full-state/contracts/invoke-contract.md`（显式 `checkpoint_id` ⇒ parent = 该 id；运行期携带当前 id；双形态载体沿用）；缺注记才补，已有则不重复追加 ⇒ R-16 · FR-018 / FR-017
- [X] T057 [Blocked by T047/T048] 完成 `tests/runtime/test_b16f1_doc_guard.py`：断言 `harness/demo/README.md` 不再含「`update_state(...)` 的签名」待锁定条目且新增锁定说明指向 spec 裁定 1；断言 `harness/demo/target.py` 相对基线零改动（哈希 / 内容不变）⇒ FR-022 · SC-018

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖；T001 / T002 / T003 可并行。
- **Foundational (Phase 2)**: 依赖 Setup；**阻塞所有用户故事**。
- **User Stories (Phase 3–7)**: 依赖 Foundational。
  - US1（P1）→ US2（P1）→ US3（P1）→ US4（P2）→ US5（P2）为推荐顺序；
  - US1 / US2 可并行（不同实现文件），但 US3 依赖二者落地；US4 / US5 可在 Foundational 后并行。
- **Polish (Phase 8)**: 依赖所有目标用户故事完成；T053 / T054 / T055 串行收口。

### User Story Dependencies

- **US1（P1）**: 依赖 Foundational；无其它故事依赖；本 feature 最小可验收切片。
- **US2（P1）**: 依赖 Foundational；与 US1 共享父链 / anchor，可并行；US3 的测试依赖 US1+US2。
- **US3（P1）**: 依赖 US1+US2 的实现；独立验收历史完整性。
- **US4（P2）**: 依赖 Foundational + US1 的 replay 路径；静态 / resume 可与 US2 并行。
- **US5（P2）**: 依赖 Foundational + US2 的 `update_state` 入口；失败信号可并行补。

### Within Each User Story

- 先写测试并确认红 → 再实现 → 再跑定向回归；
- 同一文件的多项修改 MUST 串行（如 `superstep.py` 的 T009 / T016 / T017 / T018 / T031 / T036 / T037 / T038）；
- 不同测试文件可并行。

### Parallel Opportunities

- Setup：T001 / T002 / T003。
- Foundational：T005 / T007 / T008 / T010 / T012 / T013（T006 与 T007 不同文件；T009 与 T010 不同文件）。
- US1：T014 / T015。
- US2：T020 / T021。
- US3：T028 / T029 / T030。
- US4：T034 / T035。
- US5：T040 / T041 / T042。
- Polish：T046 / T047 / T048 / T049 / T050 / T052 / T056（T051 依赖 T050、T057 依赖 T047/T048，串行）；T053 之后 T054 / T055 串行。

---

## Parallel Example: User Story 2

```bash
# 先并行写两类测试（不同文件）：
Task: "T020 [US2] facade update_state tests in tests/facade/test_b16f1_update_state.py"
Task: "T021 [US2] runtime update_state tests in tests/runtime/test_b16f1_update_state_runtime.py"

# 实现按文件串行（_time_travel.py 被 T022 / T023 / T026 改）：
Task: "T022 [US2] implement update_state pipeline in src/freegraph/runtime/_time_travel.py"
Task: "T024 [US2] wire _stategraph.update_state in src/freegraph/_stategraph.py"
```

## Parallel Example: User Story 3

```bash
Task: "T028 [US3] history integrity tests in tests/facade/test_b16f1_time_travel.py"
Task: "T029 [US3] pending protection tests in tests/runtime/test_b16f1_pending_protection.py"
Task: "T030 [US3] dual-backend history tests in tests/persistence/test_b16f1_put_parent.py"
```

---

## Implementation Strategy

### Feature Slice First（User Story 1 Only）

1. 完成 Setup + Foundational。
2. 完成 US1（T014–T019）。
3. **STOP & VALIDATE**：`tests/facade/test_b16f1_time_travel.py` +
   `tests/runtime/test_b16f1_replay_anchor.py` 全绿；从每个历史点重放 + **正常终态** no-op。
4. 这是本 feature 的最小可验收切片：**可从历史 checkpoint 重放**。

### Incremental Delivery

1. Setup + Foundational → 基础就绪。
2. US1 → 重放（最小切片）。
3. US2 → 分叉（`update_state`）。
4. US3 → 历史完整性（A2）。
5. US4 → 中断 / 静态组合。
6. US5 → 失败 / 边界。
7. Polish → 差分 / 文档 / 人工验收 / 全量。

### Parallel Team Strategy

- 完成 Setup + Foundational 后：
  - Dev A：US1（replay / anchor）
  - Dev B：US2（`_time_travel` / `_stategraph`）
  - Dev C：US4（static / resume）
- ⚠️ **`src/freegraph/runtime/superstep.py` 是共享热文件**：US1（T016–T018）与 US4（T036–T038）都修改它 ⇒ **串行** / 同一 owner 收口；US4 的测试可先并行写。
- US3 在 US1+US2 后由 A/B 共同收口；US5 由 C 并行补；Polish 由全员分摊。

---

## Notes

- **并行任务（`[P]`）**：不同文件 / 无未完成依赖；同一文件修改 MUST 串行。
- 每个用户故事先写失败测试，再实现；完成后跑该故事定向测试。
- 冻结断言：**拆分而不删**，判据只可更严（RED-1…RED-3）。
- 上游 final replay 的 fork checkpoint 与 SC-016 的差异已落 spec **X-06**；D-02 **不比较快照数**。
- **T001 MUST** 按宪法 v1.11.0 实测复核冻结断言（RED-1…RED-5），不得只凭推理登记。
- **branch anchor** 已由 spec **裁定 10 / FR-026** 正式化；非 no-op replay / 历史续跑一致适用。
- **上游 spec / data-model 回溯修订**由 T056 **核对已落 / 补齐遗漏**（宪法 v1.9.0 · 拆分而不删）；已落注记不得重复追加。
- 行数预算按 plan R-10 如实登记；**MUST NOT** 削减 FR / SC 换绿。
- 人工验收必须 fake + 真实模型两轮；B25F1 只复验。
