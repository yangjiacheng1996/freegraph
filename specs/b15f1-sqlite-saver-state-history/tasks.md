---

description: "Task list for B15F1 · SqliteSaver + get_state / get_state_history"
---

# Tasks: B15F1 · `SqliteSaver` + `get_state` / `get_state_history`

**Input**: Design documents from `/specs/b15f1-sqlite-saver-state-history/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) ·
[data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: **包含**。spec 的 FR-026 / FR-027 / FR-028 / FR-029 与宪法原则 VI「判据级可追溯」要求
每条 SC 有可判定测试；每个用户故事先写失败测试，再实现，再跑定向回归；差分 D-01…D-21 落
`tests/differential/`。

**Organization**: 按 `spec.md` 的 **6** 个用户故事分组；US1–US3 为 P1，US4–US5 为 P2，US6 为 P3。
Setup / Foundational / Polish 为跨切面，不带故事标签。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（**不同文件** / 无未完成依赖）
- **[Story]**: `US1`…`US6` —— 仅**用户故事阶段**的任务带
- 每条任务 MUST 带**精确文件路径**；行尾用 `⇒ FR-xxx · SC-xxx` 标注追溯（纯登记项可标 `⇒ R-x`）
- ⚠️ 同一文件的多项修改 MUST 串行；测试文件之间可并行

## 路径约定

- L4（新增 / 修改）：`src/freegraph/persistence/{__init__.py,_json.py,sqlite.py}` · `_types.py` / `memory.py` 零改动
- L3（修改）：`src/freegraph/_stategraph.py`
- L2（新增 / 修改）：`src/freegraph/runtime/{_state_read.py,_stream_checkpoint.py,_stream.py,superstep.py}`
- L1（只改 2 处注解）：`src/freegraph/contracts/protocols.py`
- 测试：`tests/persistence/` · `tests/facade/` · `tests/runtime/` · `tests/contracts/` · `tests/differential/`
- 验收：`harness/verification/B15F1/`
- 文档：`README.md` · `THIRD_PARTY_NOTICES` · 上游承接状态：`specs/b2f1-contracts-protocols/{spec.md,data-model.md,contracts/public-api.md}` · `specs/b8f2-stream-modes/{spec,plan,tasks}.md` 与 `contracts/{stream-contract,upstream-parity}.md` · `specs/b14f1-checkpointer-memory-saver/{spec,plan}.md` · `specs/b7f3-invoke-full-state/spec.md` 与 `contracts/invoke-contract.md`

---

## 基线 / 预登记红点（实施前先读）

**基线**（2026-11-22 实跑）：`.venv/bin/python -m pytest -q --tb=no` ⇒ **2191 passed, 8 skipped**。

| # | 预登记红点 | 处置任务 |
|---|---|---|
| **RED-1** | `tests/facade/test_compiled_graph.py::test_each_unready_method_raises_not_implemented_naming_owner`（`get_state` / `get_state_history` 已实现） | T017 |
| **RED-2** | `tests/runtime/test_conditional_edge_surface.py::test_the_unimplemented_protocol_methods_still_name_their_owner` | T017 |
| **RED-3** | `tests/facade/test_facade.py::test_compile_returns_a_product_but_capability_methods_are_not_implemented` | T017 |
| **RED-4** | `tests/contracts/test_b14f1_contracts.py` 的 `persistence.__all__` / 门面否定断言 | T018 |
| **KEEP-1** | `tests/facade/test_stream_modes.py::test_checkpoints_and_messages_are_empty`（无 saver 仍 0 条） | T046 |
| **KEEP-2** | `tests/contracts/test_protocols.py::test_get_state_returns_none_when_not_found`（返回注解不变） | T019 |
| **KEEP-3** | `tests/differential/parity_probe.py` 的能力面列表（仅检查存在性） | T061 |
| **KEEP-4** | `tests/runtime/test_interrupt_checkpoint.py::test_the_runtime_never_imports_a_saver_implementation`（只扫描 `runtime/**`） | T018 |

> **纪律**：RED-1…RED-4 MUST 按「**拆分而不删** + 判据只可更严」处置；
> KEEP-1…KEEP-4 MUST 保持绿；其余测试 MUST 保持绿；**MUST NOT** 写永久红的 CI。

---

<!-- TRACE_TABLES_START -->

## 追溯表（FR → 任务）

> 由任务行尾 `⇒ FR/SC` **机械生成**；与正文逐项一致。

| FR | 任务 |
|---|---|
| FR-001 | T002 / T003 / T013 / T020 |
| FR-002 | T019 / T061 / T064 |
| FR-003 | T008 / T024 / T025 |
| FR-004 | T008 / T024 / T025 |
| FR-005 | T002 / T007 / T021 |
| FR-006 | T011 / T020 |
| FR-007 | T009 / T010 |
| FR-008 | T010 |
| FR-009 | T009 / T011 |
| FR-010 | T013 / T020 / T039 / T040 / T041 |
| FR-011 | T008 / T042 / T043 / T044 / T045 |
| FR-012 | T010 / T022 / T044 |
| FR-013 | T004 / T016 / T027 / T031 / T033 |
| FR-014 | T016 / T027 |
| FR-015 | T015 / T027 / T028 / T031 / T033 |
| FR-016 | T034 / T036 / T038 |
| FR-017 | T012 / T034 / T035 / T036 / T038 |
| FR-018 | T016 / T029 / T068 / T031 / T033 |
| FR-019 | T030 / T033 |
| FR-020 | T029 |
| FR-021 | T016 / T027 |
| FR-022 | T004 / T046 / T047 / T048 / T049 / T050 / T051 |
| FR-023 | T019 / T032 / T037 / T069 |
| FR-024 | T026 / T061 |
| FR-025 | T014 / T018 / T056 |
| FR-026 | T003 / T006 / T052 / T053 / T054 / T055 / T063 |
| FR-027 | T042 / T043 / T045 |
| FR-028 | T023 / T027 |
| FR-029 | T001 / T058 / T059 / T066 / T067 |
| FR-030 | T007 / T009 / T021 |
| FR-031 | T012 / T020 / T022 / T035 / T038 |
| FR-032 | T011 / T012 |
| FR-033 | T008 / T024 / T025 |
| FR-034 | T008 / T020 |
| FR-035 | T009 / T020 |
| FR-036 | T019 / T032 / T037 / T064 / T069 |
| FR-037 | T016 / T029 / T068 / T033 |

## 追溯表（SC → 任务）

> 由任务行尾 `⇒ FR/SC` **机械生成**；与正文逐项一致。

| SC | 任务 |
|---|---|
| SC-001 | T034 / T036 / T038 |
| SC-002 | T027 / T031 / T033 |
| SC-003 | T023 / T025 / T026 / T027 / T060 |
| SC-004 | T042 / T043 / T044 / T045 |
| SC-005 | T019 / T020 / T061 / T064 |
| SC-006 | T013 / T020 / T040 |
| SC-007 | T007 / T010 / T011 / T020 / T021 |
| SC-008 | T016 / T029 / T068 / T031 / T033 |
| SC-009 | T030 / T033 |
| SC-010 | T029 |
| SC-011 | T027 |
| SC-012 | T013 / T039 / T040 / T041 |
| SC-013 | T022 / T044 |
| SC-014 | T046 / T047 / T048 / T049 / T050 / T051 / T060 |
| SC-015 | T020 / T027 |
| SC-016 | T012 / T035 / T038 |
| SC-017 | T020 |
| SC-018 | T006 / T052 / T053 / T054 / T055 / T063 |
| SC-019 | T023 / T026 / T060 |
| SC-020 | T001 / T058 / T059 / T060 / T066 / T067 |
| SC-021 | T014 / T018 / T056 |
| SC-022 | T008 / T024 / T025 |
| SC-023 | T019 / T032 / T037 / T064 / T069 |
| SC-024 | T009 / T020 |
| SC-025 | T015 / T028 / T031 / T033 |
| SC-026 | T012 / T022 / T035 / T038 |
| SC-027 | T016 / T029 / T068 / T033 |

> **反向追溯**：每条任务行尾的 `⇒ FR/SC` 即「任务 → spec」的映射；上两表为「spec → 任务」。

<!-- TRACE_TABLES_END -->

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 基线 / 骨架 / 人工记录 / 差分骨架 / 归属登记

- [x] T001 跑既有测试套件 `.venv/bin/python -m pytest -q --tb=no`，把 **2191 passed / 8 skipped** 写入 `harness/verification/B15F1/manual-verification.md` 的「环境」段（先建最小五段式骨架）；**并按宪法 v1.11.0 实测复核冻结断言**：在临时副本按本 feature 落地形态（`get_state` / `get_state_history` 不再抛 `NotImplementedError`）改动源码 ⇒ 跑既有套件 ⇒ 实测采集变红断言，逐条核对 plan 的 RED-1…RED-4 是否完整（缺失 ⇒ 补登记，带 `文件:行号` + 变红原因）⇒ FR-029 · SC-020 · R-1 / R-2
- [x] T002 创建 `src/freegraph/persistence/_json.py` / `src/freegraph/persistence/sqlite.py` 两个**骨架文件**（署名头逐字 + 模块 docstring 为首个语句；`__all__` 先留空）⇒ FR-001 / FR-005
- [x] T003 [P] 创建测试骨架：`tests/persistence/test_sqlite_saver.py` · `test_sqlite_saver_json.py` · `test_sqlite_saver_failures.py` · `test_b15f1_cross_process.py` · `test_sqlite_saver_concurrency.py` · `tests/facade/test_b15f1_state_read.py` · `tests/runtime/test_b15f1_stream_checkpoints.py` · `tests/runtime/test_b15f1_manual_record_guard.py` · `tests/contracts/test_b15f1_contracts.py` ⇒ FR-001 / FR-026
- [x] T004 创建 `src/freegraph/runtime/_state_read.py`（**L2 私有**，与 `superstep.py` 同条目）与 `src/freegraph/runtime/_stream_checkpoint.py`（L2 私有）骨架（署名头 + 模块 docstring + 空函数签名）⇒ FR-013 / FR-022
- [x] T005 在 `THIRD_PARTY_NOTICES` §1 增加上游 SQLite 同步 saver 的 **MIT 改编**草稿行（项目 / 来源 / `MIT` / 改编 / 修改说明 / 原始版权声明）⇒ R-11
- [x] T006 [P] 创建 `tests/differential/test_b15f1_state_parity.py` 骨架：通用 `pytest.importorskip("langgraph")`；**SQLite 专属场景必须单独 `pytest.importorskip("langgraph.checkpoint.sqlite")`**（当前该子包未安装，必须 skip 而非 collection 失败）；D-01…D-21 占位 ⇒ FR-026 · SC-018

**Checkpoint**: 骨架与基线就绪，可进入 Foundational。

---

## Phase 2: Foundational（阻塞性前置 · 所有故事共享）

**Purpose**: L4 JSON / `SqliteSaver` 核心 / L2 pending 合并 / L3 组装助手 / 冻结测试预修。
**⚠️ CRITICAL**: 未完成本 Phase 前，任何用户故事都不能开工。

### L4 · JSON / SqliteSaver 核心

- [x] T007 [P] 在 `src/freegraph/persistence/_json.py` 实现 JSON 编解码：`values` / `metadata` / `writes` / `Interrupt` / `PregelTask`；`next` / `tasks` / `interrupts` / `path` 读回重建 tuple / 对象；**pending `__interrupt__` 值 channel-aware 投影为 `{"value","id"}` 并读回 `Interrupt`**；不可序列化 ⇒ `TypeError`；`PregelTask.error` / `state` 必须 `None` ⇒ FR-005 / FR-030 · SC-007
- [x] T008 [P] 在 `src/freegraph/persistence/sqlite.py` 实现 `SqliteSaver.__init__(conn, *, on_checkpoint=None)` / `from_conn_string(...)`（`closing` + `check_same_thread=False`）/ `setup()`（WAL + `checkpoints` / `writes` 表）/ `cursor()`（每实例 `threading.Lock`；异常 rollback、成功 commit；首次操作建表）；支持 `:memory:`；不提供 `serde` / 额外 `close()` ⇒ FR-003 / FR-004 / FR-011 / FR-033 / FR-034 · SC-022
- [x] T009 在 `src/freegraph/persistence/sqlite.py` 实现 `put(config, *, values, metadata) -> RunConfig`：`Mapping` 校验；JSON 编码；`MAX(checkpoint_id)+1` 每线程 32 位 id；`parent_checkpoint_id`；`created_at` UTC ISO-8601；8 字段快照；返回新 `RunConfig`；成功 `put` 后锁外 `on_checkpoint`（异常吞掉）⇒ FR-007 / FR-009 / FR-030 / FR-035 · SC-024
- [x] T010 在 `src/freegraph/persistence/sqlite.py` 实现 `put_writes(config, *, writes, task_id, task_path="")`：目标 `configurable["checkpoint_id"]`（缺 key ⇒ `KeyError`；不存在 ⇒ `ValueError`）；**`__interrupt__` 值按 `Interrupt→{value,id}` 编码，其余通道按纯 JSON**；去重键 `(task_id, WRITES_IDX_MAP.get(channel, idx))`（`WRITES_IDX_MAP` 为上游名；freegraph 复用私有 `_WRITES_IDX_MAP`）；普通通道 `INSERT OR IGNORE`、保留通道 `INSERT OR REPLACE`（逐写判定）；事务失败零残留 ⇒ FR-007 / FR-008 / FR-012 · SC-007 · 裁定 5 / 6
- [x] T011 在 `src/freegraph/persistence/sqlite.py` 实现 `get_tuple(config) -> CheckpointTuple | None`：按 id / 最新；读 `writes` 按 `(task_path, task_id, idx)` 升序；`snapshot` 8 字段；`.scheduler` 副本；返回独立副本 ⇒ FR-006 / FR-009 / FR-032 · SC-007
- [x] T012 在 `src/freegraph/persistence/sqlite.py` 实现 `list(config=None, *, filter=None, before=None, limit=None)`：`config=None` 线程按首次写入（`MIN(rowid)`）+ 同线程 id 降序；`filter` 上游 key 校验 + `json_extract`；`filter` 非 `Mapping` ⇒ `TypeError`；`before` 排除 `id >= before_id`；`limit <= 0` ⇒ 空；全局 limit；返回迭代器 ⇒ FR-017 / FR-031 / FR-032 · SC-016 / SC-026
- [x] T013 在 `src/freegraph/persistence/sqlite.py` 实现 `delete_thread(thread_id)`（幂等；非 `str` ⇒ `TypeError`；不影响其它线程）/ `delete_for_runs` / `copy_thread`（v1 `NotImplementedError`）/ `get_next_version`（`int+1`，非 `int` / `bool` ⇒ `TypeError`）⇒ FR-010 / FR-001 · SC-006 / SC-012
- [x] T014 在 `src/freegraph/persistence/__init__.py` 导出 `SqliteSaver`（`__all__` 只增；`freegraph.graph` 不转出）；更新模块 docstring 为“四个公开符号”⇒ FR-025 · SC-021

### L2 / L3 共享助手

- [x] T015 [P] 在 `src/freegraph/runtime/superstep.py` 新增 `merge_pending_writes(spec, values, pending_writes) -> dict`：`_restore_channels` → 按 `.pending_writes` 顺序收集非保留通道 → `_reject_unknown_keys` → `Channel.update` → `_sparse_state`；只读副本；不推进版本；不写存储；未知 key ⇒ `InvalidUpdateError` ⇒ FR-015 · SC-025
- [x] T016 在 `src/freegraph/runtime/_state_read.py`（L2 私有）实现：`resolve_read_config(config)`（`resolve_config` + `thread_id` / 非空 `checkpoint_ns` 校验；`None` ⇒ 缺 `thread_id` ⇒ `ValueError`）、`require_saver(checkpointer)`（`ValueError("No checkpointer set")`）、`assemble_tasks(next_nodes, scheduler, pending_writes)`（**上游 next-tasks**：`next` + `.scheduler["fanout"]` + pending `__interrupt__`；**两类来源 id 域不同、互斥**：`next` 来源（含 `节点名:TaskId`）的 `id` = 运行时 `task_key`（权威）、interrupts 按 `task_key` 附着；`fanout` 账本来源的 `id` = 本地 `index`（非 `task_key`）、`interrupts` 恒 `()`；**MUST NOT** 跨源按 `id` 去重 / 相等合并；标准 / fan-out 的 id/name/path 按裁定 13；**不读取 `snapshot.tasks`**）、`assemble_interrupts(tasks, snapshot_interrupts)`（任务顺序展平 / snapshot 回退）、`assemble_snapshot(..., *, apply_values: bool)`（`apply_values=True` ⇒ 无 id 合并 pending；`False` ⇒ 带 id / 历史不合并；tasks / interrupts 始终按 next-tasks 投影）⇒ FR-013 / FR-014 / FR-018 / FR-021 / FR-037 · SC-008 / SC-027

### 冻结测试预修 + 契约 / 单测

- [x] T017 拆分 `tests/facade/test_compiled_graph.py::test_each_unready_method_raises_not_implemented_naming_owner`、`tests/runtime/test_conditional_edge_surface.py::test_the_unimplemented_protocol_methods_still_name_their_owner`、`tests/facade/test_facade.py::test_compile_returns_a_product_but_capability_methods_are_not_implemented`：保留 `update_state` → B16F1；`get_state` / `get_state_history` 改为正面断言（无 saver ⇒ `ValueError`；有 saver ⇒ `StateSnapshot`）。⚠️ 预修后**暂红**，由 T031 / T036 收口 ⇒ R-1
- [x] T018 更新 `tests/contracts/test_b14f1_contracts.py`：`persistence.__all__` 加 `SqliteSaver`；门面同时断言无 `SqliteSaver`；保留 `MemorySaver` / `InMemorySaver` / `CheckpointTuple` 逐字；保持 `tests/runtime/test_interrupt_checkpoint.py` 的 `runtime/**` 扫描通过 ⇒ R-2 / FR-025 · SC-021
- [x] T019 [P] 在 `tests/contracts/test_b15f1_contracts.py` 写契约 / 门禁用例：导出面、门面否定、L4 不 import L2/L3/L5（同层内部 `._types` / `._json` 允许）、零 env / 零出站、`get_state` 返回注解仍含 `None`；**L1 `config` 注解放宽与 SC-023 的判定断言见 T069（在 T032 / T037 之后运行，避免 Foundational 红）** ⇒ FR-002 / FR-023 / FR-036 · SC-005 / SC-023
- [x] T020 [P] 在 `tests/persistence/test_sqlite_saver.py` 写核心单测：`isinstance(..., Checkpointer)`、8 方法、`put` / `get_tuple` / `list` / `delete_thread` / `get_next_version`、id 单调 / 父链、`.pending_writes` 排序、返回副本、`list(None)` 线程序、`filter` / `before` / `limit`、`.scheduler` 的 JSON 往返、`conn_string` 原样传给 `sqlite3.connect`（`~` / `$VAR` 不展开）⇒ FR-001 / FR-006 / FR-010 / FR-031 / FR-034 / FR-035 · SC-005 / SC-006 / SC-007 / SC-015 / SC-017 / SC-024
- [x] T021 [P] 在 `tests/persistence/test_sqlite_saver_json.py` 写 JSON 往返用例：`values` tuple→list（X-05）、`next` / `tasks` / `interrupts` / `path` 重建、`Interrupt` / `PregelTask` 对象、**pending `__interrupt__` 值 round-trip 为 `Interrupt`/元组（channel-aware）**、`PregelTask.error` / `state` 非 None ⇒ `TypeError`、不可序列化 ⇒ `TypeError` + 零写入 ⇒ FR-005 / FR-030 · SC-007
- [x] T022 [P] 在 `tests/persistence/test_sqlite_saver_failures.py` 写失败 / 原子性用例：磁盘满 / 权限 / 损坏 / `database is locked` 原样传播、单次 `put` / `put_writes` 失败零残留、`from_conn_string` 退出后 `sqlite3.ProgrammingError`、`filter` 非法 key `ValueError` ⇒ FR-012 / FR-031 · SC-013 / SC-026

**Checkpoint**: L4 核心 + L2/L3 助手 + 冻结测试预修就绪；用户故事可开工。

---

## Phase 3: User Story 1 - 进程重启后状态还在（Priority: P1）🎯 MVP

**Goal**: `from_conn_string(path)` 写入后，新实例 / 新进程用同一路径能取回旧快照（8 字段一致）。

**Independent Test**: `with SqliteSaver.from_conn_string(path) as saver:` 跑 `a → b`；退出后用同一
`path` 新建 saver，`get_tuple(...).snapshot` 的 8 字段与写入时一致；子进程同样可读。

### Tests for User Story 1（MUST 先写 · MUST 先失败）

- [x] T023 [P] [US1] 在 `tests/persistence/test_b15f1_cross_process.py` 写跨实例 / 跨进程用例：`from_conn_string(path)` 写入 → 新实例 / 新 Python 子进程读取；`get_tuple().snapshot` 的 `values` / `next` / `config` / `metadata` / `tasks` / `interrupts` 逐字段一致；子进程退出码 0 ⇒ FR-028 · SC-003 / SC-019
- [x] T024 [US1] 在 `tests/persistence/test_sqlite_saver.py` 写生命周期用例：`:memory:` 可用、`from_conn_string` 打开 / 创建 DB、首次操作 `setup()`（WAL + 两表）、`from_conn_string` 退出后调用 `sqlite3.ProgrammingError`、`SqliteSaver(conn)` 不关闭调用方连接 ⇒ FR-003 / FR-004 / FR-033 · SC-022

### Implementation for User Story 1

- [x] T025 [US1] 在 `src/freegraph/persistence/sqlite.py` 收口 `from_conn_string` / `setup()` / 事务提交与关闭：确保只在首次操作建表、WAL 生效、异常回滚、正常退出提交并关闭；父路径 / 权限错误原样传播 ⇒ FR-003 / FR-004 / FR-033 · SC-003 / SC-022
- [x] T026 [US1] 跑 US1 定向回归：`.venv/bin/python -m pytest tests/persistence/test_b15f1_cross_process.py tests/persistence/test_sqlite_saver.py -q -k "cross_process or lifecycle or memory or from_conn"`；确认无 saver / 无 `thread_id` 时执行语义不变 ⇒ FR-024 · SC-003 / SC-019

**Checkpoint**: US1 独立可测（重启后取回 / 生命周期 / 跨进程）。

---

## Phase 4: User Story 2 - 看当前状态（Priority: P1）

**Goal**: `get_state(config)` 返回 8 字段 `StateSnapshot`；无 id 合并 pending；有 id 不合并；
`tasks` 按上游 **next-tasks**（`next` + `.scheduler["fanout"]` + pending `__interrupt__`）重建；
`interrupts` 按任务顺序展平；静态挂起合法。

**Independent Test**: 挂 `SqliteSaver` 跑图后 `get_state({"thread_id": "t"})` 返回 8 字段；
动态中断时 `interrupts` 与 `invoke` 的 `__interrupt__` 逐项一致；`tasks` 含审批节点名。

### Tests for User Story 2（MUST 先写 · MUST 先失败）

- [x] T027 [US2] 在 `tests/facade/test_b15f1_state_read.py` 写 `get_state` 字段 / config 用例：8 字段、`config.configurable["checkpoint_id"]` 非空、`config.context is None`、`RunConfig` / `Mapping` / `None` 双形态、裸 `str` / 数字 ⇒ `TypeError`、缺 `thread_id` / 非空 `checkpoint_ns` / 无 saver ⇒ `ValueError`；**并补一条跨进程 `get_state`（新 Python 子进程读同一 DB；依赖 T031）** ⇒ FR-013 / FR-014 / FR-015 / FR-021 / FR-028 · SC-002 / SC-003 / SC-011 / SC-015
- [x] T028 [US2] 在 `tests/facade/test_b15f1_state_read.py` 写 pending values 合并用例：无 `checkpoint_id` ⇒ C6 合并；`checkpoint_id=None` / 空串 ⇒ 视为未指定并合并；带非空 id ⇒ 不合并；`get_state_history` ⇒ 不合并；合并只改副本、存储零变化；保留通道不进入 `values` ⇒ FR-015 · SC-025
- [x] T029 [US2] 在 `tests/facade/test_b15f1_state_read.py` 写 `tasks` / `interrupts` 用例：**next-tasks 语义**（收敛快照 `tasks==()`；`next` 非空 ⇒ 每个目标一个 `PregelTask`；标准任务 `id=name=节点名`、`path=(节点名,)`；fan-out `id=f"{node}:{TaskId}"`、`path=(node,TaskId)`）；pending 中断按 `task_id` 附着；`interrupts` 与 `flatten(task.interrupts)` 同序；`Interrupt` 字段数 == 2；**确认不使用 `snapshot.tasks`** ⇒ FR-018 / FR-020 / FR-037 · SC-008 / SC-010 / SC-027
- [x] T068 [US2] 在 `tests/facade/test_b15f1_state_read.py` 补 **next-tasks 全场景**用例：普通 `next` / 收敛 / 静态挂起 / fan-out（调度账本与挂起现场两类来源）/ 真异常 + 中断同现 五类；断言 fan-out 任务来自 `.scheduler["fanout"]`（`id`=本地 `index`、`interrupts==()`）或 `next` 的 `节点名:TaskId` 项（`id`=运行时 `task_key`、interrupts 按 `task_key` 附着）、**两源 id 域不同且不跨源去重**、**新增「标准任务与 fan-out 同轮」用例**（令 `index != 全局 task_id`，断言不误合并）、真异常时不会混入上一轮完成态任务、fan-out 轮不比较 `next` ⇒ FR-018 / FR-037 · SC-008 / SC-027
- [x] T030 [US2] 在 `tests/facade/test_b15f1_state_read.py` 写静态挂起用例：`interrupts == ()`、`suspension_kind` / `static_ack` 原样、`next` 可为空、`tasks` 为 next-tasks 投影且 `interrupts==()`（**不是** `snapshot.tasks`；不伪造审批任务）⇒ FR-019 · SC-009

### Implementation for User Story 2

- [x] T031 [US2] 在 `src/freegraph/_stategraph.py` 实现 `CompiledGraph.get_state(config)`：先 `cfg = runtime._state_read.resolve_read_config(config)`（L3→L2 合法方向；`None` ⇒ 缺 `thread_id` ⇒ `ValueError`），再调用 `require_saver` / `get_tuple` / `assemble_snapshot`（`apply_values = not cfg.configurable.get("checkpoint_id")`；`None` / 空串视为未指定）；无快照 ⇒ `None`；`tasks` 由 `assemble_tasks(next, scheduler, pending)` 重建；类型注解 `RunConfig | Mapping | None` ⇒ FR-013 / FR-015 / FR-018 · SC-002 / SC-008 / SC-025
- [x] T032 [US2] 在 `src/freegraph/contracts/protocols.py` 放宽 `get_state` 的 `config` 注解为 `RunConfig | Mapping[str, Any] | None`（R-3；返回类别不变）；同步 `_stategraph.py` 的方法注解 ⇒ FR-023 / FR-036 · SC-023
- [x] T033 [US2] 跑 US2 定向回归：`.venv/bin/python -m pytest tests/facade/test_b15f1_state_read.py -q -k "get_state or pending or interrupt or static"`；确认 B12F1 D-7 / B13F1 D-6 / B10F1 F-3 断言通过 ⇒ FR-013 / FR-015 / FR-018 / FR-019 / FR-037 · SC-002 / SC-008 / SC-009 / SC-025 / SC-027

**Checkpoint**: US2 独立可测（当前状态 / pending / tasks / interrupts / 静态挂起）。

---

## Phase 5: User Story 3 - 枚举历史快照做时间旅行（Priority: P1）

**Goal**: `get_state_history(config)` 按 `checkpoint_id` 倒序返回全部快照；数量 == `put` 次数；
`filter` / `before` / `limit` 与 `SqliteSaver.list` 一致。

**Independent Test**: `list(compiled.get_state_history({"thread_id": "t"}))` 长度 == `put` 次数；
首元素最新、末元素初始；同 id 的元素与 `get_state(id)` 逐字段相等。

### Tests for User Story 3（MUST 先写 · MUST 先失败）

- [x] T034 [US3] 在 `tests/facade/test_b15f1_state_read.py` 写历史数量 / 顺序用例：长度 == `put` 次数；`checkpoint_id` 严格递减；首元素最新、末元素初始；`get_state(id)` 与历史同 id 逐字段相等（含 `tasks` / `interrupts`）⇒ FR-016 / FR-017 · SC-001
- [x] T035 [US3] 在 `tests/facade/test_b15f1_state_read.py` 写历史过滤用例：`filter` / `before` / `limit` 与 `SqliteSaver.list` 逐条一致；`limit <= 0` ⇒ 空；未知线程 ⇒ 空；未知 id ⇒ `None` / 空；`filter` 非 `Mapping` / `before` 非 `RunConfig` / `Mapping` / `None` / `limit` 非 `int` / `None` ⇒ `TypeError`；`SqliteSaver` 的 `filter` 的 `None` / `bool` / `dict` / `list` 值编码与上游一致、非法 key ⇒ `ValueError`；`MemorySaver` 保持 B14F1 顶层精确匹配（不校验 key；**不改 `MemorySaver`**）；`SqliteSaver` 的 dotted key 与 `MemorySaver` 的差异有断言 ⇒ FR-017 / FR-031 · SC-016 / SC-026

### Implementation for User Story 3

- [x] T036 [US3] 在 `src/freegraph/_stategraph.py` 实现 `CompiledGraph.get_state_history(config, *, filter=None, before=None, limit=None) -> Iterator[StateSnapshot]`：校验类型 → `list(checkpointer.list(...))` 急切消费 → 对每项 `assemble_snapshot(apply_values=False)` → `iter(...)` ⇒ FR-016 / FR-017 · SC-001
- [x] T037 [US3] 在 `src/freegraph/contracts/protocols.py` 放宽 `get_state_history` 的 `config` 注解为 `RunConfig | Mapping[str, Any] | None`（R-3；返回类别不变；**L1 方法签名参数个数不变**，`filter` / `before` / `limit` 只是 `_stategraph` 实现体的 keyword-only 扩展）；同步 `_stategraph.py` 的方法注解 ⇒ FR-023 / FR-036 · SC-023
- [x] T038 [US3] 跑 US3 定向回归：`.venv/bin/python -m pytest tests/facade/test_b15f1_state_read.py -q -k "history"`；确认与 `saver.list` 同参数逐条一致 ⇒ FR-016 / FR-017 / FR-031 · SC-001 / SC-016 / SC-026

**Checkpoint**: US3 独立可测（历史枚举 / 倒序 / 过滤）。

---

## Phase 6: User Story 4 - 删除会话数据（Priority: P2）

**Goal**: `delete_thread` 清空该会话快照 + pending writes；幂等；其它线程不变；重建从 id 1 开始。

**Independent Test**: 两个线程各有快照；`delete_thread("t-1")` 后 `get_tuple == None`、
历史为空；`t-2` 逐项不变；重复删除不抛；同 id 重建 id 从 1 开始。

### Tests for User Story 4（MUST 先写 · MUST 先失败）

- [x] T039 [US4] 在 `tests/persistence/test_sqlite_saver.py` 写 `delete_thread` 用例：删除后 `get_tuple == None`、`list` 空、`pending_writes` 无残留；另一线程逐项不变；重复删除不抛；重建 id 从 1 开始；非 `str` ⇒ `TypeError` ⇒ FR-010 · SC-012

### Implementation for User Story 4

- [x] T040 [US4] 在 `src/freegraph/persistence/sqlite.py` 复核 `delete_thread` / `delete_for_runs` / `copy_thread`：删除两表行、幂等、不影响其它线程；两方法 v1 `NotImplementedError`；**MUST NOT** 回改 `MemorySaver` ⇒ FR-010 · SC-006 / SC-012
- [x] T041 [US4] 跑 US4 定向回归：`.venv/bin/python -m pytest tests/persistence/test_sqlite_saver.py -q -k "delete"` ⇒ FR-010 · SC-012

**Checkpoint**: US4 独立可测（删除 / 幂等 / 隔离 / 重建）。

---

## Phase 7: User Story 5 - 并发写不互相破坏（Priority: P2）

**Goal**: 同一 `SqliteSaver` 实例 8 线程并发 `put` / `get_tuple` 无异常 / 无串扰 / id 唯一单调；
Windows CI 通过；跨实例只要求不损坏。

**Independent Test**: 同实例 8 线程各写若干快照与 pending writes；结束后每个线程快照数 /
pending writes 正确；无 `database is locked` 泄漏；测试不带 `linux_only`。

### Tests for User Story 5（MUST 先写 · MUST 先失败）

- [x] T042 [P] [US5] 在 `tests/persistence/test_sqlite_saver_concurrency.py` 写同实例多线程用例：8 线程并发 `put` / `get_tuple`；无异常、无数据串扰、checkpoint id 唯一单调；无 `database is locked` 泄漏；不加 `linux_only` ⇒ FR-011 / FR-027 · SC-004
- [x] T043 [US5] 在 `tests/persistence/test_sqlite_saver_concurrency.py` 写跨实例用例：两个 `from_conn_string` 实例写不同线程；结束后数据完整、无半事务；跨进程只断言不损坏 ⇒ FR-011 / FR-027 · SC-004

### Implementation for User Story 5

- [x] T044 [US5] 在 `src/freegraph/persistence/sqlite.py` 复核并收口并发：单连接 + 每实例 `threading.Lock` + `check_same_thread=False` + WAL；`setup()` / `cursor()` / 读写 / `on_checkpoint` 均在锁内 / 锁外按契约；`put` 的 `MAX+1` 在事务内；**不额外重试**（`database is locked` 原样传播）；异常 rollback ⇒ FR-011 / FR-012 · SC-004 / SC-013
- [x] T045 [US5] 跑 US5 定向回归：`.venv/bin/python -m pytest tests/persistence/test_sqlite_saver_concurrency.py -q`；确认 Windows 分支由现有 `windows-2025` CI 覆盖；记录跨进程边界 ⇒ FR-011 / FR-027 · SC-004

**Checkpoint**: US5 独立可测（并发 / Windows / 不损坏）。

---

## Phase 8: User Story 6 - `checkpoints` 流式事件（Priority: P3）

**Goal**: `stream(..., stream_mode="checkpoints")` 在挂 saver + `thread_id` 时，本次运行每次成功
`put` 产出 1 条四键事件，`payload` = `StateSnapshot`；无 saver / 无 `thread_id` ⇒ 0 条；
其它六档行为不变；不恢复历史。

**Independent Test**: 挂 `SqliteSaver` / `MemorySaver` 跑 `a → b` 并消费 `checkpoints`；
事件数 == `put` 次数；每条 `payload` 是 `StateSnapshot`；无 saver / 无 `thread_id` ⇒ 0 条。

### Tests for User Story 6（MUST 先写 · MUST 先失败）

- [x] T046 [US6] 在 `tests/runtime/test_b15f1_stream_checkpoints.py` 写事件用例：有 saver + `thread_id` ⇒ 事件数 == 本次 `put` 次数；四键完整；`payload` 是 `StateSnapshot`（**同形 = 8 字段；`values` 为存储快照值；`tasks` / `interrupts` 为 next-tasks 投影，与 `get_state()` 对该 id 一致**）；无 saver / 无 `thread_id` ⇒ 0 条；其它六档（values / updates / tasks / debug / messages / custom）序列不变；**只有 `checkpoints` mode 写 saver** ⇒ FR-022 · SC-014
- [x] T047 [US6] 在 `tests/runtime/test_b15f1_stream_checkpoints.py` 写历史 / 顺序用例：线程已有历史时只含本次新增快照；事件按创建顺序（旧 → 新）；初始快照事件（无历史时）在首轮之前；不伪造历史事件 ⇒ FR-022 · SC-014

### Implementation for User Story 6

- [x] T048 [US6] 在 `src/freegraph/runtime/_stream_checkpoint.py` 实现 `StreamCheckpointWriter`：`prepare()`（`get_tuple` 判历史；无历史 ⇒ `put_initial`）、`after_result()`（`put_step`）、`on_interrupt()`（`_suspend` + `_write_suspend`）、`on_error(collector)`（`put_error_interrupts`）、`snapshot_of()`（`get_tuple(written)` + **next-tasks 组装**返回 `StateSnapshot`；不可读 ⇒ 明确异常）。**spec H-7 / FR-022 已允许** `get_tuple(written)` 等价读回与私有 writer 复用 B14F1 写盘助手 ⇒ FR-022 · SC-014
- [x] T049 [US6] 在 `src/freegraph/runtime/_stream.py` 给 `StreamSession` 增可选 `checkpointer` / `persist_checkpoints` / `run_table` 暴露；在 `__enter__` 初始化 writer；在 `__exit__` 重置错误中断收集器；**不**改变其它 mode / 静态断点 / `Command` 边界 ⇒ FR-022 · SC-014
- [x] T050 [US6] 在 `src/freegraph/_stategraph.py` 接线：`CompiledGraph.stream` 把 `self.checkpointer` 传给 `_stream_events`；`_stream_events` 在 `"checkpoints" in modes` 时调用 `prepare` / `after_result` / `on_interrupt` / `on_error(collector)` 并产出 `checkpoints` 事件；其它 mode 走原路径；**不恢复历史**；**spec H-7 / FR-022 已允许私有 writer** ⇒ FR-022 · SC-014
- [x] T051 [US6] 跑 US6 定向回归：`.venv/bin/python -m pytest tests/runtime/test_b15f1_stream_checkpoints.py tests/facade/test_stream_modes.py -q`；确认无伪造事件、无回归 ⇒ FR-022 · SC-014

**Checkpoint**: US6 独立可测（流式 checkpoint 事件 / 其它档不变）。

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 差分 D-01…D-21、文档 / 上游规格、人工验收、全量回归、行数与审计

- [x] T052 在 `tests/differential/test_b15f1_state_parity.py` 落 **D-01…D-05**（`get_state` 最新 / 按 id / 历史数量 / 顺序 / 过滤；**比较投影只含 `values` / `next`（非 fan-out）/ `tasks`（next-tasks）/ `interrupts`，排除 `metadata` / `created_at` / `config`**；上游缺席 `SKIP (source-aligned)`）⇒ FR-026 · SC-018
- [x] T053 在 `tests/differential/test_b15f1_state_parity.py` 落 **D-06…D-10**（动态中断 / 真异常 + 中断 / `context` / 无 checkpointer / 缺 `thread_id`）⇒ FR-026 · SC-018
- [x] T054 在 `tests/differential/test_b15f1_state_parity.py` 落 **D-11…D-15**（`checkpoints` 事件 / `delete_thread` / 双后端 / 跨实例 / 并发）⇒ FR-026 · SC-018
- [x] T055 在 `tests/differential/test_b15f1_state_parity.py` 落 **D-16…D-21**（不可序列化 / pending 合并 / 带 id / `from_conn_string` / filter key / **next-tasks 重建：普通 / 收敛 / 静态 / fan-out（含账本来源与 next 来源、以及标准任务与 fan-out 同轮的混合轮）/ 真异常**）⇒ FR-026 · SC-018

> ⚠️ **D-19 / 直接使用上游 `SqliteSaver` 的场景** MUST 额外 `pytest.importorskip("langgraph.checkpoint.sqlite")`；
> D-01…D-18 的 state 读取对照可用已安装的 `MemorySaver`，不因 SQLite 子包缺席而 fail。
- [x] T056 更新 `README.md` 的 `CompiledGraph` / `Checkpointer` 行：写明 `get_state` / `get_state_history`（**上游 next-tasks 语义**）已由 B15F1 交付、`SqliteSaver` 已可用；**不新增**兼容矩阵行（B24F1 定稿）⇒ FR-025 · SC-021 / 文档纪律
- [x] T057 更新上游规格的下游承接状态：`specs/b2f1-contracts-protocols/spec.md`（2 处 `config` 注解拆分而不删）、`specs/b8f2-stream-modes/spec.md`（`checkpoints` 档有 saver 时由 B15F1 产出；**其「`StreamSession` 忽略 `checkpointer`」冻结条款（原 028 号 FR）的 carve-out 已在 spec 层登记为「承接中」**：非 `checkpoints` 六档仍忽略 `checkpointer`，`checkpoints` 档由本 feature 的 `StreamCheckpointWriter` 写盘；**补充：`stream(tasks)` 仍为「每完成一条」，与 `StateSnapshot.tasks` 的 next-tasks 语义分界**）、`specs/b14f1-checkpointer-memory-saver/spec.md`（关闭 D-02；**H-8 同款 carve-out 已在 spec 层登记为「承接中」；新增 `tasks` 语义 carve-out：存储的「本轮完成态」不再是读取权威，`get_state` / `get_state_history` / `stream(checkpoints)` 由 B15F1 读取层重建 next-tasks**）。**当前上游规格已登记为「B15F1 承接中（计划交付）」**（另含 `specs/b8f2-stream-modes/{plan,tasks}.md` 与 `contracts/{stream-contract,upstream-parity}.md`、`specs/b14f1-checkpointer-memory-saver/plan.md`、`specs/b7f3-invoke-full-state/spec.md` 与 `contracts/invoke-contract.md` 中的同款标记）；本任务在 B15F1 实现合入后把它们统一置为「✅ 已交付」，并复核措辞与实现一致（**MUST NOT** 提前把「承接中」写成「已交付」）⇒ R-3 / R-4 / R-13
- [x] T058 完成 `harness/verification/B15F1/manual-verification.md`：环境 / 步骤 / 实际输出 / 结论 / 遗留问题；贴跨实例 / 跨进程取回、历史枚举、中断 tasks / interrupts、并发实测的非空输出；**写入本 feature 唯一一次追认文字**（L1 `config` 注解放宽 R-3 + B14F1 `tasks` 语义回溯 R-13，同一次）；**并完成质量门禁 5 合规**：跑 **fake 轮 + 真实模型轮**，记录模型端点 / 调用次数 / 零出站归因；不得伪造 / 代签 ⇒ FR-029 · SC-020 · R-3 / R-13
- [x] T059 [Blocked by T058 / T067] 完成 / 补充 `tests/runtime/test_b15f1_manual_record_guard.py`（T003 已建骨架）：断言 `harness/verification/B15F1/manual-verification.md` 存在、五段齐全、含非空实测输出、**含 fake 轮 + 真实模型轮证据（模型端点 / 调用次数 / 零出站归因）**、**含唯一一次追认文字（R-3 / R-13）**；并断言 `harness/features/B25F1_双跑验收与迁移说明.md` 含「下游承接（B15F1）」且为**复验**口径；**必须在 T058 / T067 之后运行** ⇒ FR-029 · SC-020
- [x] T060 跑 `quickstart.md` 的 12 组验证命令（§1–§12 的 pytest / 差分入口）；把不适用项显式记入人工验证的「遗留问题」⇒ SC-003 / SC-014 / SC-019 / SC-020
- [x] T069 [P] 在 `tests/contracts/test_b15f1_contracts.py` 增加 **SC-023 判定用例**（在 T032 / T037 之后运行）：断言 `CompiledGraph.get_state` / `get_state_history` 的 `config` 注解均为 `RunConfig | Mapping[str, Any] | None`（用 `typing.get_type_hints` 精确比对）、`freegraph.contracts` 未新增 `Exception` / `BaseException` 子类（对比快照）、门禁编号集合仍为 G1–G30（无新增）；断言失败时点名具体差异 ⇒ FR-023 / FR-036 · SC-023
- [x] T061 跑全量回归 + Linux 门禁套件：`.venv/bin/python -m pytest -q --tb=no`（**隐式覆盖** G3 / G7 / G16 / G18 / G19 等既有契约 / 门禁用例）；并运行 `gate_G21` / **`gate_G22`（隔离环境依赖闭包 + `sys.modules` 无 langchain 家族）** / `G23` / `G24` / `G25` / `G26` / **`G27` 零出站独立入口** / `G30`；确认除上游缺席 / 平台 skip 外全绿；记录最终 passed / skipped 与每条门禁退出码；G22 若本地无法起隔离 venv ⇒ 由 CI 运行并在 manual-verification 记录（**MUST NOT** 静默跳过）⇒ FR-002 / FR-024 · SC-005
- [x] T062 在 `specs/b15f1-sqlite-saver-state-history/tasks.md` 的「行数预算」表填入实施期实测（实现 / 测试 / 合计）；若超 1,240 行 ⇒ 按 plan **R-9** 如实登记，**MUST NOT** 削减 FR / SC ⇒ R-9
- [x] T063 做最终追溯审计（`specs/b15f1-sqlite-saver-state-history/tasks.md`）：**37 FR / 27 SC** 全部至少挂 1 条任务；从任务行尾 `⇒ FR/SC` 机械核对「表中有、正文无」与「正文有、表中无」均为 0；核对 FR / SC 编号连续、无跳号；核对 P-01…P-25 上游断言带版本 + `路径:行号`；核对 `tasks` 全部为 next-tasks 语义、无残留 `snapshot.tasks` 权威表述 ⇒ FR-026 · SC-018
- [x] T064 做最终零扩张审计（`src/freegraph/contracts/protocols.py` / `src/freegraph/persistence/` / `src/freegraph/graph.py`）：L1 符号面只 2 处注解；`Span` / `StateSnapshot` / `RunConfig` / `Interrupt` / `PregelTask` 字段面零改动；`runtime.__all__` / `superstep.__all__` / 门面符号面零改动；零新增第三方依赖 / 零 env / 零出站；零新增门禁编号；G25 对 `persistence` 判绿 ⇒ FR-002 / FR-036 · SC-005 / SC-023
- [x] T065 核对 `THIRD_PARTY_NOTICES` §1 的上游 SQLite MIT 改编行已落地；`README.md` / 来源路径 / 版权声明齐全；G8 / G30 判绿 ⇒ R-11
- [x] T066 收尾：清理临时脚本 / `__pycache__` 不入库；确认 `git status` 只含本 feature 的预期文件；把最终结论写入 `harness/verification/B15F1/manual-verification.md` 的「结论」段 ⇒ FR-029 · SC-020
- [x] T067 在 `harness/features/B25F1_双跑验收与迁移说明.md` 的「下游承接（B15F1）」中写明：B15F1 **自跑** fake + 真实模型轮；B25F1 对 `SqliteSaver` 持久化往返 / `get_state` / `get_state_history` / `checkpoints` 证据做**跨 feature 复验**（**不是替代**）；引用 plan 的「质量门禁 5 合规执行」；由 T059 守卫 ⇒ FR-029 · SC-020
- [x] T070 把 spec 的下游承接写入目标 feature 提示词初稿：`harness/features/B16F1_update_state与时间旅行.md` 增「下游承接（B15F1）」节（D-01 / D-02 / D-03：复用 checkpoint 顺位 id 与父链、同一组装口径、静态快照可作重放起点）；`harness/features/B24F1_打包分发与兼容矩阵.md` 增「下游承接（B15F1）」（D-04：兼容矩阵增 `SqliteSaver` / `get_state` / `get_state_history` 三行）；`harness/features/B20F2_Trace查询API与SQLite后端.md` 增「下游承接（B15F1）」（D-06：trace SQLite 与 checkpoint SQLite 两套存储不共用表/文件/连接）。**只接线 · 逐条最小改动 · 不新增门禁编号**；与 T057 / T067 同批 ⇒ R-14

---

## 行数预算（**约束** · 立项书 §5.2）

| 项 | 立项书 | 本 tasks 的计划拆分（基线） | 预计增量 | 实施期实测 |
|---|---|---|---|---|
| 实现 | 620 | L4 `sqlite.py` + `_json.py` ~260 · L2 helper / stream / `_state_read` ~120 · L3 `_stategraph` ~160 · 文档 / 验收 ~80 | next-tasks 读取层 + 回溯 ~80–160 | **~1,270**（新增 4 文件 1,114 行 + 既有文件改动 ~158 行） |
| 测试 | 620 | persistence ~220 · facade / runtime ~220 · contracts ~60 · differential ~120 | 含 fan-out / 真异常 / 混合轮 ~120–240 | **~1,070**（10 个新增测试文件） |
| **合计** | **1,240** | **基线 ~1,240** | **预计 +200~400** | **~2,340**（实测；按 plan R-9 / R-13 如实登记，未削减 FR / SC） |

> ⚠️ **2026-11-23 范围上调**：next-tasks 读取层重建（含 fan-out / 真异常同现）与 B14F1 回溯修订
> 预计 **+200~400 行**（实现 + 测试）；超支 MUST 按 plan **R-9 / R-13** 如实登记；
> **MUST NOT** 通过削减 FR / SC 来压行数。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**：无依赖，可立即开始。
- **Phase 2 Foundational**：依赖 Setup；**阻塞所有用户故事**。
- **Phase 3 US1 / Phase 4 US2 / Phase 5 US3**：依赖 Foundational；均 P1，可按顺序做，也可并行（注意共享文件）。
- **Phase 6 US4**：依赖 Foundational（`delete_thread` 已实现）；独立可测。
- **Phase 7 US5**：依赖 Foundational（连接 / 锁 / WAL）；独立可测。
- **Phase 8 US6**：依赖 Foundational + US2/US3 的 `get_tuple` / snapshot 组装语义；独立可测。
- **Phase 9 Polish**：依赖 US1–US6 完成；差分可提前写骨架，最终断言依赖实现。

### User Story Dependencies

| Story | 依赖 | 说明 |
|---|---|---|
| **US1** | Foundational | 跨实例 / 跨进程持久化 |
| **US2** | Foundational | 当前状态 / pending / tasks / interrupts |
| **US3** | Foundational + US2 的 snapshot 组装 | 历史枚举；若 US2 未完成，可独立用 `runtime._state_read.assemble_snapshot` |
| **US4** | Foundational | 删除 / 幂等 / 隔离 |
| **US5** | Foundational | 并发 / Windows |
| **US6** | Foundational + US2/US3 | `checkpoints` 事件 / 快照读回 |

### Within Each User Story

- Tests MUST 先写、先失败，再实现。
- L4 数据载体 / 存储 → 读侧 / 写侧 → L3 组装 → 定向回归。
- 同一文件的多项修改 MUST 串行（`sqlite.py` / `_stategraph.py` / `runtime/_state_read.py`）。

---

## Parallel Opportunities

- **Setup**：T003 / T006 可并行；T001 / T002 / T004 / T005 因不同文件也可并行（注意 T002 / T004 是骨架）。
- **Foundational**：T007（`_json.py`）与 T008（`sqlite.py`）不同文件 ⇒ 可并行；T009–T013 同写 `sqlite.py` ⇒ **串行**。T015（`superstep.py`）可与 T007–T013 并行。T017 / T018 / T019 / T020 / T021 / T022 不同测试文件 ⇒ 可并行（T020 / T021 / T022 同属 `tests/persistence` 但不同文件）。
- **US1**：T023（跨进程）与 T024（生命周期）不同文件 ⇒ 可并行；T025 同写 `sqlite.py` ⇒ 与 T009–T013 串行。
- **US2 / US3**：T027–T030 / T068 同写 `tests/facade/test_b15f1_state_read.py` ⇒ **串行**；T031 / T036 同写 `_stategraph.py` ⇒ **串行**；T032 / T037 同写 `contracts/protocols.py` ⇒ **串行**。
- **US4 / US5**：T039 / T042 / T043 不同测试文件 ⇒ 可并行；T040 / T044 同写 `sqlite.py` ⇒ **串行**。
- **US6**：T046 / T047 同写 `tests/runtime/test_b15f1_stream_checkpoints.py` ⇒ **串行**；T048 / T049 / T050 分别改 `_stream_checkpoint.py` / `_stream.py` / `_stategraph.py` ⇒ 可并行，但 T050 依赖 T048/T049。
- **Polish**：T052–T055 同写差分文件 ⇒ **串行**；T056 / T057 / T058 / T059 / T065 不同文件 ⇒ 可并行（T059 依赖 T058）。

---

## Parallel Example: US1 + US2 + US3

```bash
# 测试骨架 / 不同文件可并行
Task: "T023 [US1] tests/persistence/test_b15f1_cross_process.py"
Task: "T027 [US2] tests/facade/test_b15f1_state_read.py"
Task: "T034 [US3] tests/facade/test_b15f1_state_read.py"  # 同一文件 ⇒ 串行执行

# 实现侧：_stategraph.py 的 get_state / get_state_history 串行
Task: "T031 [US2] src/freegraph/_stategraph.py get_state"
Task: "T036 [US3] src/freegraph/_stategraph.py get_state_history"
```

---

## Implementation Strategy

### MVP First（US1 + US2 + US3 · 三个 P1）

1. 完成 Phase 1 Setup + Phase 2 Foundational。
2. 完成 US1（跨实例 / 跨进程持久化）→ 验证 `get_tuple` 8 字段。
3. 完成 US2（`get_state` / pending / tasks / interrupts）→ 验证当前状态。
4. 完成 US3（历史枚举）→ 验证数量 / 倒序 / 过滤。
5. **STOP and VALIDATE**：US1–US3 独立测试通过 ⇒ MVP（磁盘持久化 + 状态读取 + 历史可枚举）。

### Incremental Delivery

1. Setup + Foundational → L4 核心 / 助手 / 冻结预修就绪。
2. US1 → 跨重启持久化。
3. US2 → 当前状态读取。
4. US3 → 历史枚举。
5. US4 → 删除会话。
6. US5 → 并发 / Windows。
7. US6 → `checkpoints` 流式事件。
8. Polish → 差分 / 文档 / 人工验收 / 全量回归。

### Parallel Team Strategy

1. 团队共同完成 Setup + Foundational。
2. Foundational 后：
   - A：US1 + US4（持久化 / 删除）
   - B：US2 + US3（状态读取 / 历史；共享 `_stategraph.py` ⇒ 串行或同一人）
   - C：US5 + US6（并发 / 流式；共享 `sqlite.py` / `_stream.py` ⇒ 串行或同一人）
3. US1–US3 完成后收口 Polish。

---

## Notes

- [P] tasks = 不同文件、无未完成依赖。
- [Story] label 仅用于用户故事阶段；Setup / Foundational / Polish 不带。
- 每个用户故事必须能独立测试；US1 用 `get_tuple().snapshot`，US2 用 `get_state`，避免故事间硬依赖。
- 测试 MUST 先失败再实现；同一文件的多项修改 MUST 串行。
- 不伪造：`get_state` / 历史只从真实 saver 读；`stream` 只对真实 `put` 发事件。
- 不越界：不实现 `update_state` / 时间旅行 / `Store` / Postgres / async / 子图 / 运行级删除 / 线程复制。
- 文档纪律：README 只做事实订正；兼容矩阵行由 B24F1 纳入。
- 人工记录 MUST 由执行者如实转录，禁止代签。
