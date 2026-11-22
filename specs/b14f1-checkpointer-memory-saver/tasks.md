---

description: "Task list for B14F1 · Checkpointer 协议 + MemorySaver"
---

# Tasks: B14F1 · Checkpointer 协议 + `MemorySaver`（快照 + pending writes 双层持久化）

**Input**: Design documents from `/specs/b14f1-checkpointer-memory-saver/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) ·
[data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: **包含**。spec 的 SC-001…SC-025 与宪法原则 VI「判据级可追溯」要求每条判据有可判定测试；
每个用户故事先写失败测试，再实现，再跑定向回归；差分场景 D-01…D-15 落 `tests/differential/`。

**Organization**: 按 `spec.md` 的 **6** 个用户故事分组；US1–US3 为 P1，US4–US5 为 P2，US6 为 P3。
Setup / Foundational / Polish 为跨切面，不带故事标签。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（**不同文件** / 无未完成依赖）
- **[Story]**: `US1`…`US6` —— 仅**用户故事阶段**的任务带
- 每条任务 MUST 带**精确文件路径**；行尾用 `⇒ FR-xxx · SC-xxx` 标注追溯（纯登记项任务可标 `⇒ R-x`）
- ⚠️ 任务顺序以**依赖**为准：同一文件的多项修改 MUST 串行；测试文件之间可并行

## 路径约定

- L4（新增）：`src/freegraph/persistence/{__init__.py,_types.py,memory.py}`
- L2（修改）：`src/freegraph/runtime/{_checkpoint.py,superstep.py,_span_hook.py}`
- L3（修改）：`src/freegraph/_stategraph.py`
- L1 / 门面（**零改动**）：`src/freegraph/contracts/**` · `src/freegraph/graph.py`
- 测试：`tests/persistence/` · `tests/runtime/` · `tests/facade/` · `tests/contracts/` · `tests/differential/`
- 验收：`harness/demo/{graph_core.py,README.md}` · `harness/verification/B14F1/`
- 文档：`README.md`（只改 `Checkpointer` 行与边界段；**不新增**兼容矩阵行）

---

## 基线 / 预登记红点（实施前先读）

**基线**（2026-11-22 实跑）：`.venv/bin/python -m pytest -q --tb=no` ⇒ **2111 passed, 8 skipped**。

| # | 预登记红点（实施前 MUST 用沙箱实测补全） | 处置任务 |
|---|---|---|
| RED-1 | `tests/facade/test_compile_validation.py::test_nv5_non_conforming_checkpointer_and_store_compile` | T031 |
| RED-2 | `tests/facade/test_compiled_graph.py::test_non_store_objects_are_accepted` | T031 |
| RED-3 | `tests/facade/test_compiled_graph.py::test_readme_states_store_and_checkpointer_boundaries` | T033 / T078 |
| RED-4 | `tests/differential/parity_probe.py` 的 D-77 | T077 |
| RED-5 | `tests/runtime/test_interrupt_checkpoint.py::test_the_runtime_never_imports_a_saver_implementation` | T032 |
| RED-6 | `tests/runtime/test_acceptance_script.py` 依赖 demo README / `graph_core.py` 的文本断言 | T033 / T081 |
| RED-7 | `tests/facade/test_invoke_interrupt.py` 的过期 docstring（可选同步） | T033 |
| RED-8 | `tests/facade/test_compiled_graph.py::test_injection_identities_are_preserved`（`SENTINEL_CHECKPOINTER=object()` 被编译期拒绝） | T031 |
| RED-9 | `tests/facade/test_compiled_graph.py::test_all_six_keywords_are_readable`（同上） | T031 |
| RED-10 | `tests/facade/test_compiled_graph.py::test_non_store_injections_emit_zero_warnings[checkpointer]`（`object()` 被拒） | T031 |
| RED-11 | `tests/facade/test_invoke_interrupt.py::test_resume_re_runs_the_interrupted_node`（3 方法 facade 桩被编译期拒绝） | T032 |
| RED-12 | `tests/runtime/test_static_interrupt.py::test_ordinary_completion_does_not_write_a_static_completion_snapshot`（新增每轮 `put` 后 `"put" not in calls` 必红） | T033 |
| RED-13 | `tests/facade/test_invoke_interrupt.py::test_resume_re_runs_the_interrupted_node`（原用例未传 `thread_id`） | T032 |

> **纪律**：RED-1…RED-13 MUST 按「**拆分而不删** + 判据只可更严」处置；
> 实施前 MUST **实测**（改源码 → 跑全量）补全本表（宪法 v1.11.0），
> 其余测试 MUST 保持绿；**MUST NOT** 写永久红的 CI。

---

## 追溯表（FR → 任务）

> 由任务行尾 `⇒ FR/SC` **机械生成**（T087）；与正文逐项一致。

| FR | 任务 |
|---|---|
| FR-001 | T003 / T015 / T026 / T034 |
| FR-002 | T005 / T017 / T030 / T035 / T038 / T039 / T040 / T041 / T042 / T054 / T056 |
| FR-003 | T020 / T027 / T043 / T045 / T046 |
| FR-004 | T028 / T049 / T050 / T052 / T053 |
| FR-005 | T022 / T026 / T036 |
| FR-006 | T021 / T026 / T050 |
| FR-007 | T004 / T029 / T037 / T051 |
| FR-008 | T002 / T011 / T032 / T034 / T085 |
| FR-009 | T002 / T015 / T024 / T034 |
| FR-010 | T010 / T031 / T068 / T071 / T073 / T077 |
| FR-011 | T014 / T018 / T025 |
| FR-012 | T017 / T024 / T025 / T027 / T036 |
| FR-013 | T016 / T017 / T020 / T027 / T045 |
| FR-014 | T020 / T044 / T047 / T057 |
| FR-015 | T018 / T026 |
| FR-016 | T019 / T026 |
| FR-017 | T018 / T019 / T023 / T025 / T027 / T028 |
| FR-018 | T004 / T017 / T019 / T020 / T026 / T027 / T029 / T037 / T051 / T052 / T055 |
| FR-019 | T007 / T032 / T039 / T060 / T062 / T063 / T064 / T065 / T066 |
| FR-020 | T007 / T020 / T061 / T065 / T066 |
| FR-021 | T008 / T030 / T046 / T048 |
| FR-022 | T009 / T041 / T056 / T067 / T070 / T072 / T073 |
| FR-023 | T023 / T026 / T069 / T073 |
| FR-024 | T017 / T036 / T055 |
| FR-025 | T011 / T032 / T034 / T088 |
| FR-026 | T013 / T058 / T082 / T083 / T084 / T090 |
| FR-027 | T033 / T079 / T080 / T081 |
| FR-028 | T006 / T054 / T055 / T057 / T059 |
| FR-029 | T021 / T026 |
| FR-030 | T023 / T028 |
| FR-031 | T016 / T017 / T027 |
| FR-032 | T002 / T034 / T088 |
| FR-033 | T012 / T074 / T075 / T076 |
| FR-034 | T042 / T048 / T053 / T059 / T066 / T085 |
| FR-035 | T012 / T074 / T075 / T076 / T085 / T087 |

## 追溯表（SC → 任务）

> 由任务行尾 `⇒ FR/SC` **机械生成**（T087）；与正文逐项一致。

| SC | 任务 |
|---|---|
| SC-001 | T030 / T035 / T038 / T039 / T040 / T041 / T042 / T054 / T056 / T060 |
| SC-002 | T020 / T027 / T043 / T045 / T046 / T048 |
| SC-003 | T028 / T049 / T050 / T052 / T053 |
| SC-004 | T022 / T026 / T036 |
| SC-005 | T037 / T042 / T051 / T053 |
| SC-006 | T015 / T021 / T024 / T026 / T034 |
| SC-007 | T014 / T018 / T025 / T026 |
| SC-008 | T017 / T025 / T027 / T036 |
| SC-009 | T020 / T044 / T047 / T057 |
| SC-010 | T018 / T019 / T026 |
| SC-011 | T021 / T026 / T050 |
| SC-012 | T015 / T024 / T034 |
| SC-013 | T031 / T068 / T071 / T073 / T077 |
| SC-014 | T017 / T019 / T020 / T026 / T027 / T029 / T037 / T051 / T052 / T054 / T055 / T057 / T059 |
| SC-015 | T039 / T060 / T063 / T064 / T066 |
| SC-016 | T020 / T061 / T065 / T066 |
| SC-017 | T062 / T065 / T066 |
| SC-018 | T030 / T046 / T048 |
| SC-019 | T041 / T067 / T070 / T072 / T073 |
| SC-020 | T023 / T026 / T028 / T069 / T073 |
| SC-021 | T017 / T036 / T055 |
| SC-022 | T013 / T058 / T082 / T083 / T090 |
| SC-023 | T033 / T079 / T080 / T081 / T089 |
| SC-024 | T001 / T034 / T085 / T086 / T088 |
| SC-025 | T074 / T075 / T076 / T085 / T087 / T089 |

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 基线 / 包骨架 / 测试骨架 / 人工记录骨架 / 差分骨架

- [x] T001 跑既有测试套件 `.venv/bin/python -m pytest -q --tb=no`，把 **2111 passed / 8 skipped** 写入 `harness/verification/B14F1/manual-verification.md` 的「环境」段（文件未建 ⇒ 先建最小骨架；T013 再补齐）⇒ 基线（SC-024 的环境证据）
- [x] T002 创建 `src/freegraph/persistence/__init__.py` / `_types.py` / `memory.py` 三个**骨架文件**（署名头逐字 + 模块 docstring 为首个语句；`__all__` 先留空，T024 再填）⇒ FR-008 / FR-009 / FR-032
- [x] T003 [P] 创建 `tests/persistence/__init__.py` · `tests/persistence/test_memory_saver.py` · `tests/persistence/test_checkpoint_tuple.py` 骨架（署名头 + 模块 docstring + 空用例组）⇒ FR-001
- [x] T004 创建 `src/freegraph/runtime/_checkpoint.py` **私有骨架**（署名头 + 模块 docstring + 空函数：`effective_checkpointer` / `put_initial` / `put_step` / `put_error_interrupts` / `checkpoint_id_of`）⇒ FR-007 / FR-018
- [x] T005 [P] 创建 `tests/runtime/test_b14f1_step_snapshots.py` 骨架（US1 定向）⇒ FR-002
- [x] T006 [P] 创建 `tests/runtime/test_b14f1_resume.py` 骨架（US4 定向）⇒ FR-028
- [x] T007 [P] 创建 `tests/runtime/test_b14f1_fanout_barrier.py` 骨架（US5 定向）⇒ FR-019 / FR-020
- [x] T008 [P] 创建 `tests/runtime/test_b14f1_error_interrupts.py` 骨架（US2 / 真异常 + 中断）⇒ FR-021
- [x] T009 [P] 创建 `tests/runtime/test_b14f1_spans.py` 骨架（US6 定向）⇒ FR-022
- [x] T010 [P] 创建 `tests/facade/test_b14f1_compile_validation.py` 骨架（US6 编译期校验）⇒ FR-010
- [x] T011 [P] 创建 `tests/contracts/test_b14f1_contracts.py` 骨架（L4 导出 / 依赖方向 / 零 env / 零出站）⇒ FR-008 / FR-025
- [x] T012 [P] 创建 `tests/differential/test_b14f1_checkpoint_parity.py` 骨架（D-01…D-15 · `pytest.importorskip("langgraph")`）⇒ FR-033 / FR-035
- [x] T013 创建 `harness/verification/B14F1/manual-verification.md` 五段式骨架（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）⇒ FR-026 / SC-022

**Checkpoint**: 骨架与基线就绪，可进入 Foundational。

---

## Phase 2: Foundational（阻塞性前置 · 所有故事共享）

**Purpose**: L4 `MemorySaver` / `CheckpointTuple` 的完整实现 + L2 归一化 / 写盘助手 + 冻结测试预修。
**⚠️ CRITICAL**: 未完成本 Phase 前，任何用户故事都不能开工。

### L4 公开载体与内存实现

- [x] T014 在 `src/freegraph/persistence/_types.py` 实现 `CheckpointTuple`：`@dataclass(frozen=True, slots=True)` · **恰好 3 字段** `snapshot: StateSnapshot` / `pending_writes: tuple[tuple[str, str, Any], ...]` / `scheduler: dict[str, Any]`；docstring 写明「不加上游 `.config` / `.checkpoint` / `.metadata` 别名」⇒ FR-011 · SC-007
- [x] T015 在 `src/freegraph/persistence/memory.py` 实现 `MemorySaver.__init__(*, on_checkpoint=None)`：校验可调用 / `None`；初始化每实例 `threading.RLock`；定义 `InMemorySaver = MemorySaver` 别名（`__all__` 由 T024 导出）⇒ FR-001 / FR-009 · SC-006 / SC-012
- [x] T016 在 `src/freegraph/persistence/memory.py` 实现内部存储结构 `_ThreadStore` / `_StoredCheckpoint` / `_StoredWrite`（字段逐字按 `data-model.md` §3：`snapshots` / `order` / `writes: dict[cp_id, dict[(task_id, idx), _StoredWrite]]` / `next_seq` / `latest_id`；`_StoredWrite.task_id` / `channel` / `value` / `task_path` / `idx`）⇒ FR-013 / FR-031 · data-model EM-08…EM-10
- [x] T017 在 `src/freegraph/persistence/memory.py` 实现 `put(config, *, values, metadata) -> RunConfig`：
  - `values` / `metadata` 非 `Mapping` ⇒ `TypeError`；**先深拷贝、再落锁提交**；
  - 缺失 / 空 `thread_id` ⇒ `ValueError`（与 `get_tuple` / `put_writes` / `list(config)` 同一口径）；
  - 生成每线程 32 位零填充顺位 id；`parent_config` = 上一快照 `config`（首个 `None`）；
  - 组装 `StateSnapshot` 8 字段：`values` / `next`（`metadata["next"]`，缺省 `()`）/ `config`（`thread_id` + `configurable={"checkpoint_id": id}`，`context=None`）/ `metadata` 深拷贝 / `created_at`（UTC ISO-8601）/ `parent_config` / `tasks`（缺省 `()`）/ `interrupts`（缺省 `()`）；
  - 返回 `RunConfig(thread_id=生效 id, configurable={"checkpoint_id": id})`；释放锁后调 `on_checkpoint(深拷贝 snapshot)`，回调异常吞掉 ⇒ FR-002 / FR-012 / FR-013 / FR-018 / FR-024 / FR-031 · SC-008 / SC-014 / SC-021
- [x] T018 在 `src/freegraph/persistence/memory.py` 实现 `get_tuple(config) -> CheckpointTuple | None`：`configurable["checkpoint_id"]` 有值 ⇒ 取指定（不存在 ⇒ `None`）；否则最新；缺失 `thread_id` ⇒ `ValueError`；返回 `snapshot` / `pending_writes`（按 `(task_path, task_id, idx)` 升序）/ `scheduler` 的**深拷贝** ⇒ FR-011 / FR-015 / FR-017 · SC-007 / SC-010
- [x] T019 在 `src/freegraph/persistence/memory.py` 实现 `list(config=None, *, filter=None, before=None, limit=None)`：`config=None` 全线程（`thread_id` 按存储**插入序** · 上游同款、不排序；同线程 id 降序）；`config` 缺失 / 空 `thread_id` ⇒ `ValueError`；`filter` 按 `metadata` 顶层 key 精确匹配；`before` 排除 `id >= before_id`；`limit<=0` 空；返回**迭代器**；每项深拷贝 ⇒ FR-016 / FR-017 / FR-018 · SC-010 / SC-014
- [x] T020 在 `src/freegraph/persistence/memory.py` 实现 `put_writes(config, *, writes, task_id, task_path="")`：
  - `(channel, value)` 序列校验；`task_id` 非空 `str`；缺失 / 空 `thread_id` ⇒ `ValueError`；
  - 目标 = `configurable["checkpoint_id"]` 指定（**缺 key ⇒ `KeyError`**；同线程内不存在 ⇒ `ValueError` · X-07）；**MUST NOT** 回退最新；
  - 去重键 = `(task_id, WRITES_IDX_MAP.get(channel, idx))`：普通通道跨调用同 `(task_id, idx)` 首次生效；`__error__` / `__scheduled__` / `__interrupt__` / `__resume__` 最后生效（**同调用内也覆盖**）；普通通道不同 `idx` 全保留；
  - 值深拷贝；`.pending_writes` 按 `(task_path, task_id, idx)` 升序（上游 `writes_sort_key`）；**MUST NOT** 改快照 `values` ⇒ FR-003 / FR-013 / FR-014 / FR-018 / FR-020 · SC-002 / SC-009 / SC-014 / SC-016
- [x] T021 在 `src/freegraph/persistence/memory.py` 实现 `delete_thread(thread_id)`（删快照 + 写入 + 计数器；幂等；非 `str` ⇒ `TypeError`）与 `delete_for_runs` / `copy_thread`（存在；v1 `NotImplementedError`）⇒ FR-006 / FR-029 · SC-011 / SC-006
- [x] T022 在 `src/freegraph/persistence/memory.py` 实现 `get_next_version(current, channel=None) -> int`：`None ⇒ 1`；`int` 且非 `bool` ⇒ `current+1`；其它 ⇒ `TypeError`；**MUST NOT** 返回字符串；`put` 不改写调度版本 ⇒ FR-005 · SC-004
- [x] T023 在 `src/freegraph/persistence/memory.py` 完成 `on_checkpoint` 接线：每次成功 `put` **恰一次**、锁外、深拷贝 `StateSnapshot`；异常吞掉、不回滚、不递归；并确保所有存入 / 取出路径使用 `copy.deepcopy` ⇒ FR-017 / FR-023 / FR-030 · SC-020
- [x] T024 在 `src/freegraph/persistence/__init__.py` 导出 `__all__ = ["MemorySaver", "InMemorySaver", "CheckpointTuple"]`；补模块 docstring（L4 只 import L1 + stdlib）⇒ FR-009 / FR-012 · SC-006 / SC-012

### L4 单元测试

- [x] T025 [P] 在 `tests/persistence/test_checkpoint_tuple.py` 写 `CheckpointTuple` 用例：3 字段、`snapshot` 是 L1 `StateSnapshot`、`pending_writes` 元组、`scheduler` 深拷贝、无上游别名 ⇒ FR-011 / FR-012 / FR-017 · SC-007 / SC-008
- [x] T026 在 `tests/persistence/test_memory_saver.py` 写协议 / 版本 / 列表 / 删除 / 直接失败面用例：`isinstance(..., Checkpointer)`、8 方法存在、`InMemorySaver is MemorySaver`、`get_next_version`、`list` 过滤 / 排序 / `before` / `limit`、`delete_thread` 零残留、两方法 `NotImplementedError`；**`get_tuple` 三态**（指定 id 命中 / 未知 id ⇒ `None` / 未给 id ⇒ 最新）；**直接调用 `get_tuple` / `list(config)` 缺失 / 空 `thread_id` ⇒ `ValueError` 且 `list(None)` 合法**；**`list()` 项与 `get_tuple()` 同形**；**`.scheduler` `json.dumps` 往返** ⇒ FR-001 / FR-005 / FR-006 / FR-015 / FR-016 / FR-018 / FR-023 / FR-029 · SC-004 / SC-006 / SC-007 / SC-010 / SC-011 / SC-014 / SC-020
- [x] T027 在 `tests/persistence/test_memory_saver.py` 写 `put` / `put_writes` 用例：8 字段组装、父链、返回 config、pending writes 分层、普通 / 保留通道去重（**同调用内保留通道也最后生效**）、普通通道不同 `idx` 全保留、缺 `checkpoint_id` ⇒ `KeyError`、指定 id 不存在 ⇒ `ValueError`、`.pending_writes` 按 `(task_path, task_id, idx)` 排序、**`put` / `put_writes` 缺失 / 空 `thread_id` ⇒ `ValueError`**、深拷贝 / 原子性（失败不改存储）⇒ FR-003 / FR-012 / FR-013 / FR-017 / FR-018 / FR-031 · SC-002 / SC-008 / SC-014
- [x] T028 在 `tests/persistence/test_memory_saver.py` 写隔离 / 并发用例：两 `thread_id` 互不可见、`delete_thread` 只清一个、并发 `put` / `get_tuple` 无串扰、`on_checkpoint` 深拷贝 / 异常隔离 / 重入不死锁 ⇒ FR-004 / FR-017 / FR-030 · SC-003 / SC-020

### L2 归一化 / 写盘助手

- [x] T029 在 `src/freegraph/runtime/_checkpoint.py` 实现 `effective_checkpointer(checkpointer, run_config)`：`None` / `True` / `False` / 缺失 / 空 `thread_id` ⇒ `None`；否则**原对象原样返回**（**不判 `isinstance`** · 协议校验只在编译期）；**MUST NOT** 因「非协议对象」而归一为 `None` ⇒ FR-007 / FR-018 · SC-014
- [x] T030 在 `src/freegraph/runtime/_checkpoint.py` 实现写盘助手：
  - `put_initial(config, checkpointer, state, values, next_nodes)`（初始快照，返回新 config）；
  - `put_step(config, checkpointer, state, values, next_nodes, tasks)`（每轮快照，返回新 config）；
  - `put_error_interrupts(round_start_config, checkpointer, task_payloads)`（只写 `__interrupt__`；
    `round_start_config.configurable["checkpoint_id"]` = 该轮起点 checkpoint id）；
  - `checkpoint_id_of(config)`（从 `configurable["checkpoint_id"]` 取）
  ⇒ FR-002 / FR-021 · SC-001 / SC-018

### 冻结测试预修（R-1 / R-2 / R-5）

- [x] T031 拆分 `tests/facade/test_compile_validation.py::test_nv5_non_conforming_checkpointer_and_store_compile`、`tests/facade/test_compiled_graph.py::test_non_store_objects_are_accepted`、`::test_injection_identities_are_preserved`、`::test_all_six_keywords_are_readable`、`::test_non_store_injections_emit_zero_warnings[checkpointer]`：
  - 非法 **checkpointer**（`object()` / `SENTINEL_CHECKPOINTER`）⇒ `TypeError`；
  - 合法 checkpointer 用 dummy 8 方法 saver；非法 **store** ⇒ 仍接受（1 条 warning 不变）；
  - 保留与 checkpointer 无关的 identity / warning 断言（**拆分而不删**）⇒ FR-010 · SC-013（RED-1 / RED-2 / RED-8 / RED-9 / RED-10）
- [x] T032 拆分 `tests/runtime/test_interrupt_checkpoint.py::test_the_runtime_never_imports_a_saver_implementation`，并扩展 `tests/facade/_invoke_support.py::StubCheckpointer` 到 8 方法（其余 5 个 no-op / `NotImplementedError`）：
  - 保留「`src/freegraph/runtime/**` 零 saver + MUST NOT import `freegraph.persistence`」；
  - 新增「`src/freegraph/persistence/memory.py` 有 `MemorySaver`」；
  - `tests/runtime` 的 3 方法桩**保持不变**（运行期不判 `isinstance`）；
  - 更新 `tests/facade/test_invoke_interrupt.py::test_resume_re_runs_the_interrupted_node`：两次 `invoke` 使用同一 `RunConfig(thread_id=...)`（**保留原恢复断言**）；
  - 同步 docstring（B10F1 的 FR-019 仍成立）⇒ FR-008 / FR-025（RED-5 / RED-11 / RED-13）
- [x] T033 更新 `tests/facade/test_compiled_graph.py::test_readme_states_store_and_checkpointer_boundaries` 的断言文本、`tests/runtime/test_acceptance_script.py` 中依赖 demo README / `graph_core.py` 的文本断言，以及 `tests/runtime/test_static_interrupt.py::test_ordinary_completion_does_not_write_a_static_completion_snapshot`：
  - README 新文本：「checkpointer 的行为已由 B14F1 的 `MemorySaver` 落地；编译期校验已交付」；
  - demo README：移除 `MemorySaver` 待锁定条目；
  - `graph_core.py` 的软断言升级后仍退出码 0；
  - 普通完成改为断言「`put` 次数 == 执行轮数 + 1」+「无 F-10 完成快照标记」（**不是**放宽）；
  - **拆分而不删**，不是放宽 ⇒ FR-027 · SC-023（RED-3 / RED-6 / RED-7 / RED-12）
- [x] T034 [P] 在 `tests/contracts/test_b14f1_contracts.py` 写 L4 契约用例：`freegraph.persistence.__all__ == {MemorySaver, InMemorySaver, CheckpointTuple}`、`persistence` 零第三方 / 零 L2-L5 import、`InMemorySaver is MemorySaver`、`CheckpointTuple` 3 字段、L1 符号面零改动、`runtime.__all__` / `superstep.__all__` 零改动 ⇒ FR-001 / FR-008 / FR-009 / FR-025 / FR-032 · SC-006 / SC-012 / SC-024

**Checkpoint**: L4 实现 + L2 助手 + 冻结测试预修就绪；用户故事可开工。

---

## Phase 3: User Story 1 - 每一步的状态都被记下来了（Priority: P1）🎯 MVP

**Goal**: 全新会话写惰性初始快照；每个实际执行过的 super-step 写一条每轮快照；收敛空轮不写；
`a → b` 的快照数 == 3；最后一条 `next == ()`。

**Independent Test**: `compile(checkpointer=MemorySaver())` + `RunConfig(thread_id="t")` 跑 `a → b`；
`len(list(saver.list(cfg))) == 3`；`values` 与轮次稀疏状态一致。

### Tests for User Story 1（MUST 先写 · MUST 先失败）

- [x] T035 [P] [US1] 在 `tests/runtime/test_b14f1_step_snapshots.py` 写快照计数用例：单节点 == 2；`a → b` == 3；收敛空轮不增加；`next` 逐轮正确（首轮 `("a",)`、`b` 后 `()`）⇒ FR-002 · SC-001
- [x] T036 [US1] 在 `tests/runtime/test_b14f1_step_snapshots.py` 写快照 8 字段 + `context` 不持久化用例：`values` 稀疏 / `metadata` / `created_at` / `parent_config` 链 / `tasks` / `interrupts`；`snapshot.config.context is None`；`context` 出现次数 0；**`.scheduler["channel_versions"]` 与调度器当前版本逐 key 相等** ⇒ FR-005 / FR-012 / FR-024 · SC-004 / SC-008 / SC-021

### Implementation for User Story 1

- [x] T037 [US1] 在 `src/freegraph/runtime/superstep.py` 的 `run_graph` 入口调用 `_checkpoint.effective_checkpointer(...)`，把归一化后的值传给 `_first_graph` / `_resume_graph`；`Command` 恢复路径在无 effective saver 时仍走 B10F1 的 `checkpointer_required` ⇒ FR-007 / FR-018 · SC-005 / SC-014
- [x] T038 [US1] 在 `src/freegraph/runtime/superstep.py` 的 `_run_graph_loop` 增 `is_fresh: bool` 与 `current_checkpoint_id: str | None` 参数；在 `interrupt_before` 检查之后、第一个 `_run_round` 之前**惰性**写初始快照（`put_initial`）；若先命中静态 before，`_write_suspend` 兼任初始快照、**不再**写初始 ⇒ FR-002 · SC-001
- [x] T039 [US1] 在 `src/freegraph/runtime/superstep.py` 的 `_run_graph_loop` 每轮合并成功后写 `put_step`：`next` = `_determine_triggers(...)`（含 fan-out 目标），收敛 ⇒ `()`；`tasks` = 本轮 `PregelTask`；`interrupts=()`；`interrupt_after` 命中时改用 `_write_suspend`（代替该轮 `put_step`）；失败轮不写 ⇒ FR-002 / FR-019 · SC-001 / SC-015
- [x] T040 [US1] 在 `src/freegraph/runtime/superstep.py` 的 `_first_graph` 调用 `_run_graph_loop` 时传 `is_fresh=True`（`history is None`）或 `False`（有历史）；有历史时把 `history.snapshot.config.configurable["checkpoint_id"]` 作为 `current_checkpoint_id` ⇒ FR-002 · SC-001
- [x] T041 [US1] 在 `src/freegraph/runtime/superstep.py` 的 `_run_graph_loop` 用 `put_initial` / `put_step` / `_write_suspend` 的返回值更新 `current_checkpoint_id`（供下一轮 span 与后续写盘使用）⇒ FR-002 / FR-022 · SC-001 / SC-019
- [x] T042 [US1] 跑 US1 定向回归：`.venv/bin/python -m pytest tests/runtime/test_b14f1_step_snapshots.py -q`；断言无 checkpointer / 无 `thread_id` 时零 saver 调用且执行结果与注入时一致 ⇒ FR-002 / FR-034 · SC-001 / SC-005

**Checkpoint**: US1 独立可测（快照数量 / 8 字段 / 执行语义不变）。

---

## Phase 4: User Story 2 - 未落地的写入也被记下来了（Priority: P1）

**Goal**: `put_writes` 写入可被 `get_tuple().pending_writes` 取回；与快照 `values` 分层；
普通 / 保留通道去重按上游；缺 `checkpoint_id` 的写入 ⇒ `KeyError`；指定 id 不存在 ⇒ `ValueError`。

**Independent Test**: `put(values={"x":1})` → `put_writes(writes=[("x",2)], task_id="n")`；
`get_tuple().pending_writes == (("n","x",2),)`；`values` 仍 `{"x":1}`。

### Tests for User Story 2（MUST 先写 · MUST 先失败）

- [x] T043 [P] [US2] 在 `tests/persistence/test_memory_saver.py` 写 pending writes 往返 / 分层用例：写入后逐三元组相等；快照 `values` 不变；`list` 每项的 `pending_writes` 只含该 checkpoint；**排序 = `(task_path, task_id, idx)` 升序** ⇒ FR-003 · SC-002
- [x] T044 [US2] 在 `tests/persistence/test_memory_saver.py` 写保留通道去重用例：普通通道跨调用同 `(task_id, idx)` 首次生效；`__interrupt__` / `__resume__` / `__error__` / `__scheduled__` 最后生效（**同调用内也覆盖**）；普通通道不同 `idx` 全保留 ⇒ FR-014 · SC-009
- [x] T045 [US2] 在 `tests/persistence/test_memory_saver.py` 写目标选择 / 失败用例：`configurable["checkpoint_id"]` 指定；**缺 `checkpoint_id` ⇒ `KeyError`**；未知 id ⇒ `ValueError`；不回退最新 ⇒ FR-003 / FR-013 · SC-002

### Implementation for User Story 2

- [x] T046 [US2] 在 `src/freegraph/runtime/_checkpoint.py` 增加 **L2 私有 contextvar 收集器**；在 `src/freegraph/runtime/superstep.py` 的 `_run_round` ⑥ 收尾处，当 `error is not None 且 interrupts` 时把 `[(task_key, (payload,)), ...]` 写入收集器（**收集器未设置** ⇒ 低层入口 no-op）；`_run_graph_loop` 捕获后先 `put_error_interrupts(round_start_config, ...)` 再**原样** `raise error`；**不**改异常对象 / 返回类型 / 不写新快照。同时**必须**把 `put_writes` 改为显式目标：`_write_suspend` 捕获 `put` 返回的新 config 并传给 `put_writes`；`_resume_graph` 复用 `history.snapshot.config`；关键字（`writes=` / `task_id=` / `task_path=`；`__interrupt__` 载荷元组；`__resume__` 累积列表）与 `MemorySaver` 逐字对齐 ⇒ FR-003 / FR-021 · SC-002 / SC-018
- [x] T047 [US2] 在 `src/freegraph/runtime/superstep.py` 复核 `_pending_interrupts` / `_pending_resume_values` 对已按上游排序的 `.pending_writes` 的读取（`__interrupt__` 取首个；`__resume__` 同 task 最后一条胜）；如假设不成立则按契约修正 ⇒ FR-014 · SC-009
- [x] T048 [US2] **先写测试**（TDD · 此时应失败）在 `tests/runtime/test_b14f1_error_interrupts.py`：同一轮一节点抛真异常、一节点 `interrupt` ⇒ pending writes 含 `__interrupt__`（命中率 100%）；抛出的异常 **identity / 类型 / 消息**与未挂 saver 时逐项相等；**为中断留痕新增的附注数 == 0**（B12F1 既有的其余并发失败 `attach_failure_notes` 保留）；调度状态中新增留痕字段数 == 0。再跑 US2 定向回归：`.venv/bin/python -m pytest tests/persistence/test_memory_saver.py tests/runtime/test_b14f1_error_interrupts.py -q -k "pending or interrupt"` ⇒ FR-021 / FR-034 · SC-002 / SC-018

**Checkpoint**: US2 独立可测（写入取回 / 分层 / 去重）。

---

## Phase 5: User Story 3 - 按 thread 隔离不同会话（Priority: P1）

**Goal**: 两个 `thread_id` 的快照 / 写入 / 计数器互不可见；`delete_thread` 只清一个；
运行期无 `thread_id` 时跳过全部落盘且执行结果不变。

**Independent Test**: `thread-1` / `thread-2` 各写两条；交叉读取命中数 == 0；
`delete_thread("thread-1")` 后 `thread-2` 逐项不变。

### Tests for User Story 3（MUST 先写 · MUST 先失败）

- [x] T049 [US3] 在 `tests/persistence/test_memory_saver.py` 写两线程隔离用例：快照 / pending writes / 计数器互不可见；`get_tuple` / `list` 不交叉 ⇒ FR-004 · SC-003
- [x] T050 [US3] 在 `tests/persistence/test_memory_saver.py` 写 `delete_thread` 隔离用例：只清目标线程；另一线程逐项不变；重复删除幂等；删除后重建从 id 1 开始 ⇒ FR-004 / FR-006 · SC-003 / SC-011
- [x] T051 [US3] 在 `tests/runtime/test_b14f1_step_snapshots.py` 写无 `thread_id` / 无 checkpointer 用例：零 saver 调用；执行结果与注入时逐项相等；`checkpointer=True` / `False` 不抛 `AttributeError`；**直接调用 saver 的失败面由 T026 / T027 覆盖** ⇒ FR-007 / FR-018 · SC-005 / SC-014

### Implementation for User Story 3

- [x] T052 [US3] 在 `src/freegraph/runtime/superstep.py` 的 `_first_graph` / `_resume_graph` / `_run_graph_loop` 的所有 saver 调用点使用 `effective_checkpointer`（**不在**每个点重复判 bool / `thread_id`）；`_write_suspend` / `get_tuple` / `put_writes` 全部受同一归一化结果守卫 ⇒ FR-004 / FR-018 · SC-003 / SC-014
- [x] T053 [US3] 跑 US3 定向回归：`.venv/bin/python -m pytest tests/persistence/test_memory_saver.py tests/runtime/test_b14f1_step_snapshots.py -q -k "isolation or thread"` ⇒ FR-004 / FR-034 · SC-003 / SC-005

**Checkpoint**: US1 + US2 + US3 均独立可测（MVP 三件套）。

---

## Phase 6: User Story 4 - 挂起后用真实的 `MemorySaver` 恢复（Priority: P2）

**Goal**: `interrupt("approve?")` 挂起后，`Command(resume="yes")` 用真实 `MemorySaver`
**只重跑被中断节点（从该节点起点）**并跑完；未挂 saver 时抛 `checkpointer_required`；历史继续追加。

**Independent Test**: `app = g.compile(checkpointer=MemorySaver())`；第一次 `invoke` 挂起；
第二次 `invoke(Command(resume="yes"), cfg)` 跑完，结果含 `answer=yes`；只重跑被中断节点、
已完成节点不重复，`interrupt()` 之后代码执行一次。

### Tests for User Story 4（MUST 先写 · MUST 先失败）

- [x] T054 [P] [US4] 在 `tests/runtime/test_b14f1_resume.py` 写动态中断 / 恢复用例：挂起写 + pending writes；挂起时**快照数 == 含挂起轮的已执行轮数 + 1**（SC-001 动态分支）；恢复跑完；历史快照继续追加；**只重跑被中断节点（从该节点起点）**、已完成节点不重复 ⇒ FR-002 / FR-028 · SC-001 / SC-014
- [x] T055 [US4] 在 `tests/runtime/test_b14f1_resume.py` 写无 saver / 会话连续 / 恢复 context 用例：未挂 saver ⇒ `InterruptError(reason="checkpointer_required")`；`invoke(None)` 续跑语义不变；**恢复后节点看到的 `context` 来自本次 `RunConfig`，不是快照；从快照还原 `context` 次数 == 0** ⇒ FR-018 / FR-024 / FR-028 · SC-014 / SC-021

### Implementation for User Story 4

- [x] T056 [US4] 在 `src/freegraph/runtime/superstep.py` 的 `_resume_graph` / `_first_graph` 把历史快照的 checkpoint id 传给 `_run_graph_loop` 的 `current_checkpoint_id`；恢复轮 / 会话连续轮不再写新的初始快照 ⇒ FR-002 / FR-022 · SC-001
- [x] T057 [US4] 在 `src/freegraph/runtime/superstep.py` 复核 `_resume_graph` 的 `__resume__` 写入：用 `history.snapshot.config`（含 checkpoint_id）作为 `config` 传给 `put_writes`；先 `put_writes` 再执行目标节点；`MemorySaver` 的普通 / 保留通道去重不吞掉累积列表 ⇒ FR-014 / FR-028 · SC-009 / SC-014
- [x] T058 [US4] 在 `harness/verification/B14F1/manual-verification.md` 写入**真实 `MemorySaver` 恢复轮**的实测输出草稿（`interrupt` → `Command(resume=...)` → 跑完；贴原始输出，不写「符合预期」）⇒ FR-026 · SC-022
- [x] T059 [US4] 跑 US4 定向回归：`.venv/bin/python -m pytest tests/runtime/test_b14f1_resume.py -q`；确认未挂 saver 的失败信号原样传播 ⇒ FR-028 / FR-034 · SC-014

**Checkpoint**: US4 独立可测（真实 saver 的恢复闭环）。

---

## Phase 7: User Story 5 - 静态挂起 / fan-out / 屏障跨 checkpoint 存活（Priority: P2）

**Goal**: 静态挂起（`interrupts=()`）可恢复；F-10 完成快照只写一次；fan-out 多任务
`task_id` 唯一；屏障 `seen` 保留、目标不重复触发。

**Independent Test**: `interrupt_before=["b"]` 挂起后 `.scheduler["suspension_kind"] == "static_before"`；
恢复后完成快照只写一次；fan-out 两任务 `task_id` 为 `f"{node}:{id}"`；屏障暂停恢复后目标执行一次。

### Tests for User Story 5（MUST 先写 · MUST 先失败）

- [x] T060 [US5] 在 `tests/runtime/test_b14f1_resume.py` 写静态挂起 / F-10 用例：`interrupt_before` / `interrupt_after` 的 `suspension_kind` / `static_ack` / `next`；`interrupts=()`；**挂起快照 `tasks == ()`**；**首轮前 `interrupt_before` 命中时快照数 == 1**；**`interrupt_after` 代替该轮快照（不重复）**；完成快照只写 1 次、与每轮重复 0 次 ⇒ FR-019 · SC-001 / SC-015
- [x] T061 [P] [US5] 在 `tests/runtime/test_b14f1_fanout_barrier.py` 写 fan-out 用例：两个 `Send` 任务 `task_id` 唯一（`f"{node}:{id}"`）；pending writes 不互相覆盖；普通任务 `task_id` == 节点名 ⇒ FR-020 · SC-016
- [x] T062 [US5] 在 `tests/runtime/test_b14f1_fanout_barrier.py` 写屏障用例：暂停 → 恢复后 `seen` 保留；目标重复触发次数 == 0 ⇒ FR-019 · SC-017

### Implementation for User Story 5

- [x] T063 [US5] 在 `src/freegraph/runtime/superstep.py` 的 `_run_graph_loop` 把静态 before / after 与 US1 的每轮策略衔接：静态 before 挂起写兼任初始（首轮前）；静态 after 挂起写代替 `put_step`；`next_nodes` 传 `_determine_triggers(...)` 结果 ⇒ FR-019 · SC-015
- [x] T064 [US5] 在 `src/freegraph/runtime/superstep.py` 的 `_run_graph_loop` 处理 `static_resume=True` 的收敛：最后一轮**跳过** `put_step`，由 `_clear_static_suspension` 写一次 F-10 完成快照；再次挂起时**不**写完成快照 ⇒ FR-019 · SC-015
- [x] T065 [US5] 在 `src/freegraph/runtime/superstep.py` 复核 fan-out / 屏障的调度账本原样存取：`versions_seen` / `fanout` / `dynamic_edges` 不被 `MemorySaver` 解释或改写；fan-out `task_id` 与任务数无关地全部落盘 ⇒ FR-019 / FR-020 · SC-016 / SC-017
- [x] T066 [US5] 跑 US5 定向回归：`.venv/bin/python -m pytest tests/runtime/test_b14f1_resume.py tests/runtime/test_b14f1_fanout_barrier.py tests/runtime/test_static_interrupt.py tests/runtime/test_static_interrupt_fanout.py -q` ⇒ FR-019 / FR-020 / FR-034 · SC-015 / SC-016 / SC-017

**Checkpoint**: US5 独立可测（静态 / fan-out / 屏障）。

---

## Phase 8: User Story 6 - `checkpoint_id` 可关联到 span 与事件（Priority: P3）

**Goal**: 节点 span 的 `checkpoint_id` 非空且等于该轮起点快照 id；模型 / 工具 span 继承；
`on_checkpoint` 事件与 `get_tuple().snapshot` 同形；编译期非法 checkpointer ⇒ `TypeError`。

**Independent Test**: 挂 `MemorySaver` + tracer 跑单节点图，节点 span `checkpoint_id` ==
最新快照 config 的 id；`compile(checkpointer=object())` ⇒ `TypeError`；
`on_checkpoint` 次数 == `put` 次数。

### Tests for User Story 6（MUST 先写 · MUST 先失败）

- [x] T067 [P] [US6] 在 `tests/runtime/test_b14f1_spans.py` 写节点 span 用例：挂 saver + tracer ⇒ 非空且等于该轮起点快照 id；子 span 继承；不挂 saver ⇒ `None`；`Span` 11 字段不变 ⇒ FR-022 · SC-019
- [x] T068 [P] [US6] 在 `tests/facade/test_b14f1_compile_validation.py` 写编译期校验用例：`None` / `True` / `False` / `MemorySaver()` 接受；`object()` / `"saver"` / `[]` / **`0` / `1` / `0.0`** ⇒ `TypeError`（**数字不得因 `0 == False` / `1 == True` 被误接受**）；`CompiledGraph.checkpointer` 记录方式不变 ⇒ FR-010 · SC-013
- [x] T069 [US6] 在 `tests/persistence/test_memory_saver.py` 写 `on_checkpoint` 运行时集成用例：回调次数 == `put` 次数；载荷与 `get_tuple().snapshot` 同形；**`list()` 项也与 `get_tuple().snapshot` 同形**；回调抛错不影响落盘；`stream(checkpoints)` 伪造事件数 == 0 ⇒ FR-023 · SC-020

### Implementation for User Story 6

- [x] T070 [US6] 在 `src/freegraph/runtime/superstep.py` 的 `_run_round` 增 **keyword-only** `checkpoint_id: str | None = None`；`_bind` 调 `start_node_span(..., checkpoint_id=checkpoint_id)`；既有三个调用点缺省不传 ⇒ `None`，零行为变化 ⇒ FR-022 · SC-019
- [x] T071 [US6] 在 `src/freegraph/_stategraph.py` 新增私有 `_validate_checkpointer(checkpointer)`：`checkpointer is None` / `isinstance(checkpointer, bool)` / `isinstance(..., Checkpointer)` 接受（**MUST NOT 用 `in (None, True, False)`** —— 否则 `0` / `1` 会被 `==` 误接受）；其它 ⇒ `TypeError`；在 `compile()` 构造 `CompiledGraph` 前调用；不改 `CompiledGraph.checkpointer` 记录方式；L3 **MUST NOT** import L4 ⇒ FR-010 · SC-013
- [x] T072 [US6] 在 `src/freegraph/runtime/superstep.py` 的 `_run_graph_loop` 把 `current_checkpoint_id` 传给 `_run_round`（每轮起点 id；恢复 / 会话连续用历史 id；无 saver ⇒ `None`）⇒ FR-022 · SC-019
- [x] T073 [US6] 跑 US6 定向回归：`.venv/bin/python -m pytest tests/runtime/test_b14f1_spans.py tests/facade/test_b14f1_compile_validation.py -q` ⇒ FR-010 / FR-022 / FR-023 · SC-013 / SC-019 / SC-020

**Checkpoint**: US6 独立可测（span / 编译期 / 事件数据源）。

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 差分 D-01…D-15、冻结断言收尾、demo / 文档、人工验收、全量回归、行数与审计

- [x] T074 [P] 在 `tests/differential/test_b14f1_checkpoint_parity.py` 落 **D-01…D-05**（单节点 / 两节点 / `get_tuple` / `put_writes` 去重（含同调用内保留通道覆盖、跨调用同 idx 不同 channel 跳过）/ 两线程隔离）；`pytest.importorskip("langgraph")`；上游缺席 skip ⇒ FR-033 / FR-035 · SC-025
- [x] T075 在 `tests/differential/test_b14f1_checkpoint_parity.py` 落 **D-06…D-10**（`list` 过滤 / 动态恢复 / 静态挂起 / fan-out / 屏障；**`list(None)` 线程插入序、pending writes 按 `(task_path,task_id,idx)`**）⇒ FR-033 / FR-035 · SC-025
- [x] T076 在 `tests/differential/test_b14f1_checkpoint_parity.py` 落 **D-11…D-15**（真异常 + 中断 / 编译期 / `True` / `False` / 无 `thread_id` / `context`）⇒ FR-033 / FR-035 · SC-025
- [x] T077 更新 `tests/differential/parity_probe.py` 的 D-77：判词由 `DIFF` 改为 **`SAME`**，理由改为「两侧都 `TypeError`（B7F2 X-4 消解）」；保留其余场景逐字不变 ⇒ FR-010 · SC-013（RED-4）
- [x] T078 更新 `README.md` 的 `Checkpointer` 行与边界段：移除「返回类型与载荷形状挂起 B14F1」「本阶段只接受并记录，编译期不做类型校验」；写明 `MemorySaver` 已落地、编译期校验已交付；**不新增**兼容矩阵行（按 spec **D-07**，`MemorySaver` / `InMemorySaver` / `CheckpointTuple` 的 3 行由 B24F1 / B25F1 定稿；本任务只更新 `Checkpointer` 行）⇒ R-5（文档事实订正）
- [x] T079 更新 `harness/demo/README.md`：移除「`MemorySaver` 的模块路径 → B14F1 未定」条目；在验收脚本清单写「已锁定：`freegraph.persistence.MemorySaver`」；把 C17 恢复段从「待 B14F1」改为「已由 B14F1 升级为硬断言」⇒ FR-027 · SC-023
- [x] T080 更新 `harness/demo/graph_core.py::case_interrupt_resume`：`g.compile(checkpointer=MemorySaver())`；两次 `invoke` 传同一 `RunConfig(thread_id=...)`；把对应 `soft(...)` 改为 `check(...)`；断言「从节点起点重跑并拿到 resume 值」失败即 FAIL；**同步把 `len(calls)==1` 的标签改为「只重跑被中断节点，interrupt 之后代码执行一次」** ⇒ FR-027 · SC-023
- [x] T081 更新 `tests/runtime/test_acceptance_script.py`：新增 `case_interrupt_resume` 的硬断言守卫（无 `soft(`、含 `check(`、使用 `MemorySaver`）；保留 `graph_core.py` 退出码 0 的 subprocess 断言 ⇒ FR-027 · SC-023（RED-6）
- [x] T082 [Blocked by T083] 新增 `tests/runtime/test_b14f1_manual_record_guard.py`：断言 `harness/verification/B14F1/manual-verification.md` 存在、五段齐全、含恢复侧非空实测输出（文档守卫）⇒ FR-026 · SC-022。⚠️ **执行顺序：必须在 T083 完成记录之后运行**（守卫不得造成永久红 CI · 宪法 v1.13.0）
- [x] T083 完成 `harness/verification/B14F1/manual-verification.md`：环境 / 步骤 / 实际输出 / 结论 / 遗留问题；贴 `interrupt → Command(resume=…) → 跑完` 的**真实**输出；不得伪造 / 代签 ⇒ FR-026 · SC-022
- [x] T084 新增 `harness/verification/B14F1/acceptance.py`：一键跑关键场景（MemorySaver / 快照计数 / 恢复 / 静态 / span / 编译期），退出码 0 / 1 / 2 三态；只 import freegraph + 标准库 ⇒ FR-026
- [x] T085 跑全量回归：`.venv/bin/python -m pytest -q --tb=no`；确认除上游缺席 skip 外全绿；记录最终 passed / skipped 计数 ⇒ FR-008 / FR-034 / FR-035 · SC-024 / SC-025
- [x] T086 在 `specs/b14f1-checkpointer-memory-saver/tasks.md` 的「行数预算」表填入**实施期实测**（实现 / 测试 / 合计）；若超 1,200 行 ⇒ 按 plan **R-7** 如实登记，**MUST NOT** 削减 FR / SC ⇒ R-7（SC-024 的审计证据）
- [x] T087 做最终追溯审计：35 FR / 25 SC 全部至少挂 1 条任务；用解析脚本从**任务行尾** `⇒ FR/SC` 重新生成两张追溯表，机械核对「表中有、正文无」与「正文有、表中无」均为 0；同时核对 FR / SC 编号连续、无跳号；**并审计 spec 的 P-01…P-21 上游断言全部带 `langgraph 1.2.11 + 路径:行号`（缺失数 == 0）** ⇒ FR-035 / SC-025
- [x] T088 做最终零扩张审计：L1 符号面 / `runtime.__all__` / `superstep.__all__` / `Span` 11 字段 / 门面符号面**零改动**；零新增第三方依赖 / 零 env / 零出站；零新增门禁编号；G25 对 `persistence` 判绿 ⇒ FR-025 / FR-032 · SC-024
- [x] T089 跑 `quickstart.md` 的 15 组验证命令（至少 §1–§15 的 pytest / demo / 差分入口），把不适用项显式记入人工验证的「遗留问题」；确认 `graph_core.py` 退出码 0 ⇒ SC-023 / SC-025
- [x] T090 收尾：清理临时脚本 / `__pycache__` 不入库；确认 `git status` 只含本 feature 的预期文件；把最终结论写入 `harness/verification/B14F1/manual-verification.md` 的「结论」段 ⇒ FR-026 · SC-022

---

## 行数预算（**约束** · 立项书 §5.2）

| 项 | 立项书 | 本 tasks 的计划拆分 | 实施期实测 |
|---|---|---|---|
| 实现 | 560 | L4 包 ~260 · 运行期接线 ~180 · 编译期校验 ~30 · demo / 文档 ~90 | **986**（实测；含 L4 新增 434 · `_checkpoint.py` 148 · `superstep.py` / `_stategraph.py` / `protocols.py` 改动 147 · 验收脚本 257） |
| 测试 | 640 | L4 单测 ~220 · 运行期 ~260 · 差分 ~120 · 守卫 / 契约 ~40 | **1,767**（实测；新增测试 1,597 + 既有测试适配 / 验收守卫 170） |
| **合计** | **1,200** | **~1,200** | **2,753**（超预算；按 plan **R-7** 如实登记，**未削减任何 FR / SC**） |

> ⚠️ 超支 MUST 按 plan **R-7** 如实登记；**MUST NOT** 通过削减 FR / SC 来压行数。
> 新增 `harness/verification/B14F1/acceptance.py` 属可选；若落地，行数计入「实现 / 验收」并在 T086 登记。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**：无依赖，可立即开始。
- **Phase 2 Foundational**：依赖 Setup；**阻塞所有用户故事**。
- **Phase 3 US1 / Phase 4 US2 / Phase 5 US3**：依赖 Foundational；三者可并行（不同文件为主）。
- **Phase 6 US4**：依赖 US1（每轮 / 初始快照）+ US2（pending writes 取回）+ US3（隔离）。
- **Phase 7 US5**：依赖 US1（每轮策略）+ US2（pending writes）+ US3（隔离）。
- **Phase 8 US6**：依赖 US1（当前 checkpoint id）+ US3（无 saver / 无 thread_id 路径）。
- **Phase 9 Polish**：依赖 US1–US6 完成；差分可提前写骨架，但最终断言依赖实现。

### User Story Dependencies

| Story | 依赖 | 说明 |
|---|---|---|
| **US1** | Foundational | 快照计数 / 8 字段 / 执行语义不变 |
| **US2** | Foundational | pending writes 往返 / 分层 / 去重 |
| **US3** | Foundational | 两线程隔离 / 无 `thread_id` 跳过 |
| **US4** | US1 / US2 / US3 | 真实 saver 的恢复闭环 |
| **US5** | US1 / US2 / US3 | 静态 / fan-out / 屏障 |
| **US6** | US1 / US3 | span id / 编译期 / 事件数据源 |

### Within Each User Story

- Tests MUST 先写、先失败，再实现。
- L4 数据载体 → 存储实现 → 读侧 / 写侧 → 运行期接线 → 定向回归。
- 同一文件的多项修改 MUST 串行（如 `memory.py` 的 T015–T023）。

---

## Parallel Opportunities

- **Setup**：T003 / T005–T012 的测试骨架可并行（不同文件）。
- **Foundational**：T025（`test_checkpoint_tuple.py`）可与 T026 并行；T026–T028 同写 `tests/persistence/test_memory_saver.py` ⇒ **MUST 串行**。T031 / T032 可并行；T033 与 T031 同写 `test_compiled_graph.py` ⇒ **MUST 串行**。
- **US1 / US2 / US3**：T035（US1）与 T043（US2）不同文件 ⇒ 可并行；T049 与 T043 同写 `tests/persistence/test_memory_saver.py` ⇒ **串行**；T051 与 T035 同写 `tests/runtime/test_b14f1_step_snapshots.py` ⇒ **串行**；实现任务都改 `src/freegraph/runtime/superstep.py` ⇒ **MUST 串行**或由同一人合并。
- **US4 / US5**：T054（US4）与 T061（US5）不同文件 ⇒ 可并行；T060 与 T054 同写 `tests/runtime/test_b14f1_resume.py` ⇒ **串行**；实现共享 `_run_graph_loop`，**MUST 串行**或由同一人合并。
- **US6**：`_run_round` / `_stategraph` 与 US4/US5 的 `_run_graph_loop` 改动需协调；建议 US4/US5 完成后再合。
- **Polish**：T074–T076 同写 `tests/differential/test_b14f1_checkpoint_parity.py` ⇒ **MUST 串行**；T078–T084 文档 / demo / 人工记录可并行（注意 T080 / T081 同源）。

### Parallel Example: US1 + US2 + US3

```bash
# 在 Foundational 完成后，可并行启动「不同文件」的测试编写：
Task: "US1 快照计数测试" in tests/runtime/test_b14f1_step_snapshots.py
Task: "US2 pending writes 往返测试" in tests/persistence/test_memory_saver.py
```

> ⚠️ US1 / US2 / US3 的**实现**都改 `src/freegraph/runtime/superstep.py`
> ⇒ **同一文件 MUST NOT 并行写**；请按 US1 → US2 → US3 串行或由同一人合并。
> ⚠️ T043–T045 与 T049–T050 都可能落 `tests/persistence/test_memory_saver.py`
> ⇒ 该文件的测试用例也 **MUST 串行**；不同测试文件之间才可并行。
> ⚠️ T051 与 T035/T036 同写 `tests/runtime/test_b14f1_step_snapshots.py`；T060 与 T054
> 同写 `tests/runtime/test_b14f1_resume.py` ⇒ 这两组也 **MUST 串行**。

---

## Implementation Strategy

### MVP First（US1 + US2 + US3 · 三个 P1）

1. 完成 Phase 1 Setup。
2. 完成 Phase 2 Foundational（**阻塞所有故事**）。
3. 完成 US1（快照）+ US2（pending writes）+ US3（隔离）。
4. **STOP and VALIDATE**：跑 US1–US3 定向回归 + `quickstart.md` §1–§3。
5. 此时已满足验收判据 **A1 / A2 / A3 / A4**。

### Incremental Delivery

1. Foundational → L4 saver 可用。
2. US1 → 每步快照可复盘。
3. US2 → pending writes 可重放。
4. US3 → 多会话隔离。
5. US4 → 真实 saver 的恢复闭环（人工 V-1 补齐）。
6. US5 → 静态 / fan-out / 屏障。
7. US6 → span / 编译期 / 事件数据源。
8. Polish → 差分 / demo / 文档 / 全量回归。

### Parallel Team Strategy

- 1 人：Foundational → US1 → US2 → US3 → US4 → US5 → US6 → Polish（严格串行）。
- 2 人：A 做 L4（T014–T028）+ US2/US3；B 做运行期（T029–T030 / US1 / US4 / US5）；US6 合流。
- 3 人：A 做 L4 + 单测；B 做运行期快照 / 恢复；C 做差分 + demo + 文档；US6 由 B 收尾。

---

## Notes

- **唯一权威**：`spec.md`；本 tasks 只承接；若冲突以 spec 为准并回修本文件。
- **Tests**：spec 的 SC 全部可测；测试 MUST 先写、先失败；**MUST NOT** 用实现代替判据。
- **冻结面**：L1 / 门面 / `runtime.__all__` / `superstep.__all__` / `Span` 11 字段 / `StateSnapshot` 8 字段**零改动**。
- **L4 边界**：`persistence` 只 import L1 + stdlib；`runtime/**` 通过鸭子类型调用 saver，**MUST NOT** import `freegraph.persistence`。
- **不伪造**：`stream(checkpoints)` 消费端未接线前，MUST NOT 产生伪造事件。
- **不越界**：不实现 `SqliteSaver` / `get_state` / `Time Travel` / `Store` / Postgres / async。
- **文档纪律**：`README.md` 只改 `Checkpointer` 行与边界段，**不新增**兼容矩阵行。
- **人工验证**：`harness/verification/B14F1/manual-verification.md` 五段齐全 + 真实输出；禁止代签。
- **红点纪律**：RED-1…RED-7 按「拆分而不删 + 判据只可更严」处置；其余测试保持绿。
