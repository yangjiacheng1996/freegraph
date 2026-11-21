---

description: "Task list for B20F2 · Trace 查询 API + SQLite 后端"
---

# Tasks: B20F2 · Trace 查询 API + SQLite 后端

**Input**: Design documents from `/specs/b20f2-trace-query-sqlite/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: **包含**。spec 定义了 SC-001…SC-018，且项目宪法原则 VI 要求「判据级可追溯」；
每个用户故事先写失败测试，再实现，再跑定向回归；Phase 8 补容错 / 只读 / 类型校验 /
SQLite 生命周期 / 并发；Phase 10 补 SC-015 文档守卫与最终审计。

**Organization**: 任务按用户故事分组；US1–US5 可独立实现 / 测试 / 交付。
Phase 8（容错 / 只读 / 校验 / SQLite 生命周期 / 并发）、Phase 9（契约 / 差分 / 文档 /
验收 / 全量回归）与 Phase 10（覆盖闭包 / 文档守卫 / 审计）为跨切面。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: `US1` / `US2` / `US3` / `US4` / `US5`；Setup / Foundational / Phase 8 / Phase 9 / Phase 10 不带故事标签
- 每个任务都带**精确文件路径**或**精确命令 / 测试文件**

---

## 追溯表（FR → 任务）

| FR | 任务 |
|---|---|
| FR-001 | T005 / T006 / T009 / T010 / T014 / T015 / T017 / T022 / T024 / T041 |
| FR-002 | T006 / T008 / T014 / T018–T020 / T021–T025 / T026–T028 / T029–T031 |
| FR-003 | T005 / T006–T008 / T014 / T022 / T024 / T029–T031 / T041 / T043 |
| FR-004 | T005 / T007 / T008 / T014 / T022 / T024 / T029 / T032 / T033 / T041 |
| FR-005 | T008 / T014 / T029–T031 / T033 |
| FR-006 | T006 / T018 / T019 / T029–T031 / T043 |
| FR-007 | T006 / T018–T020 / T034 |
| FR-008 | T026–T028 |
| FR-009 | T008 / T014 / T024 / T029–T031 |
| FR-010 | T015 / T023–T025 / T032 / T033 / T035 |
| FR-011 | T007 / T015 / T024 / T032 / T033 / T035 / T037 / T039 |
| FR-012 | T015 / T024 / T036 / T039 |
| FR-013 | T006 / T007 / T034 / T038 |
| FR-014 | T009 / T021 / T023–T025 / T039 / T042 |
| FR-015 | T009 / T023–T025 / T035 |
| FR-016 | T005 / T009 / T021 / T023 / T039 |
| FR-017 | T009 / T021 / T023 / T039 |
| FR-018 | T009 / T023 / T036 / T039 |
| FR-019 | T009 / T023 / T035 / T039 |
| FR-020 | T023 / T036 / T039 |
| FR-021 | T009 / T024 / T039 / T041 / T042 |
| FR-022 | T021–T025 / T043 |
| FR-023 | T005 / T015 / T016 / T037 |
| FR-024 | T015 / T032 / T037 |
| FR-025 | T015 / T032 / T033 / T037 |
| FR-026 | T042 / T049 |
| FR-027 | T042 / T049 |
| FR-028 | T009 / T010 / T041 / T048 |
| FR-029 | T015 / T024 / T033 / T037 / T039 |
| FR-030 | T009 / T010 / T011 / T012 / T041 |
| FR-031 | T042 / T056 |
| FR-032 | T011 / T012 / T016 / T052 |
| FR-033 | T001 / T045 / T046 / T051 / T052 / T055 / T058 |
| FR-034 | T044 / T047 / T055 |

## 追溯表（SC → 任务）

| SC | 任务 |
|---|---|
| SC-001 | T014 / T015 / T017 |
| SC-002 | T014 / T015 / T017 |
| SC-003 | T018 / T019 / T020 |
| SC-004 | T026 / T027 / T028 |
| SC-005 | T014 / T018 / T022 / T026 / T029 |
| SC-006 | T021–T025 / T043 |
| SC-007 | T008 / T014 / T015 / T029 |
| SC-008 | T005 / T014 / T022 / T029–T031 / T041 |
| SC-009 | T019 / T029–T031 |
| SC-010 | T016 / T017 / T021 / T023 / T025 / T050 |
| SC-011 | T021–T025 / T036 / T039 / T040 |
| SC-012 | T042 / T049 |
| SC-013 | T032 / T033 / T035 / T037 / T039 / T040 |
| SC-014 | T007 / T032 / T041 / T042 |
| SC-015 | T001 / T051 / T052 / T055 / T058 |
| SC-016 | T017 / T020 / T028 / T031 / T025 / T045（T056 审计） |
| SC-017 | T029 / T034 / T038 / T040 |
| SC-018 | T023 / T035 / T039 / T040 |

## 追溯表（Task → spec · 反向追溯）

| Task | Maps to |
|---|---|
| T001 | FR-033 / SC-015（骨架） |
| T002 | —（基线） |
| T003 | 原则 XI / P-01…P-07 / X-1…X-8 三态一致 |
| T004 | 门禁 3 / 原则 III |
| T005 | FR-001 / FR-003 / FR-004 / FR-016 / FR-023 / SC-008 |
| T006 | FR-001 / FR-002 / FR-003 / FR-006 / FR-007 / FR-013 |
| T007 | FR-003 / FR-004 / FR-011 / FR-013 / SC-014 |
| T008 | FR-002 / FR-003 / FR-004 / FR-005 / FR-009 / SC-007 |
| T009 | FR-001 / FR-014 / FR-015 / FR-016 / FR-017 / FR-018 / FR-019 / FR-021 / FR-028 / FR-030 |
| T010 | FR-001 / FR-028 / FR-030 |
| T011 | FR-030 / FR-032 |
| T012 | FR-030 / FR-032 |
| T013 | —（测试夹具） |
| T014 | FR-001 / FR-002 / FR-003 / FR-004 / FR-005 / FR-009 / SC-001 / SC-002 / SC-005 / SC-007 / SC-008 |
| T015 | FR-001 / FR-010 / FR-011 / FR-012 / FR-023 / FR-024 / FR-025 / FR-029 / SC-001 / SC-002 / SC-007 |
| T016 | FR-023 / FR-032 / SC-010 |
| T017 | FR-001 / SC-001 / SC-002 / SC-010 / SC-016 / US1 定向回归 |
| T018 | FR-002 / FR-006 / FR-007 / SC-003 / SC-005 |
| T019 | FR-002 / FR-006 / FR-007 / SC-003 / SC-009 |
| T020 | FR-002 / FR-007 / SC-003 / SC-016 / US2 定向回归 |
| T021 | FR-002 / FR-014 / FR-016 / FR-017 / FR-022 / SC-006 / SC-010 / SC-011 |
| T022 | FR-001 / FR-002 / FR-003 / FR-004 / FR-022 / SC-005 / SC-006 / SC-008 / SC-011 |
| T023 | FR-002 / FR-010 / FR-014 / FR-015 / FR-016 / FR-017 / FR-018 / FR-019 / FR-020 / FR-022 / SC-006 / SC-010 / SC-011 / SC-018 |
| T024 | FR-001 / FR-002 / FR-003 / FR-004 / FR-009 / FR-010 / FR-011 / FR-012 / FR-014 / FR-015 / FR-021 / FR-022 / FR-029 / SC-006 / SC-011 |
| T025 | FR-002 / FR-010 / FR-014 / FR-015 / FR-022 / SC-006 / SC-010 / SC-011 / SC-016 / US5 定向回归 |
| T026 | FR-002 / FR-008 / SC-004 / SC-005 |
| T027 | FR-002 / FR-008 / SC-004 |
| T028 | FR-002 / FR-008 / SC-004 / SC-016 / US3 定向回归 |
| T029 | FR-002 / FR-003 / FR-004 / FR-005 / FR-006 / FR-009 / SC-005 / SC-007 / SC-008 / SC-009 / SC-017 |
| T030 | FR-002 / FR-003 / FR-005 / FR-006 / FR-009 / SC-008 / SC-009 |
| T031 | FR-002 / FR-003 / FR-005 / FR-006 / FR-009 / SC-008 / SC-009 / SC-016 / US4 定向回归 |
| T032 | FR-004 / FR-010 / FR-011 / FR-024 / FR-025 / SC-013 / SC-014 |
| T033 | FR-004 / FR-005 / FR-010 / FR-011 / FR-025 / FR-029 / SC-013 |
| T034 | FR-007 / FR-013 / SC-017 |
| T035 | FR-010 / FR-011 / FR-015 / FR-019 / SC-013 / SC-018 |
| T036 | FR-012 / FR-018 / FR-020 / SC-011 |
| T037 | FR-011 / FR-023 / FR-024 / FR-025 / FR-029 / SC-013 |
| T038 | FR-013 / SC-017 |
| T039 | FR-011 / FR-012 / FR-014 / FR-016 / FR-017 / FR-018 / FR-019 / FR-020 / FR-021 / FR-029 / SC-011 / SC-013 / SC-018 |
| T040 | SC-011 / SC-013 / SC-017 / SC-018 / 跨切面回归 |
| T041 | FR-001 / FR-003 / FR-004 / FR-021 / FR-028 / FR-030 / SC-008 / SC-014 |
| T042 | FR-014 / FR-021 / FR-026 / FR-027 / FR-031 / SC-012 / SC-014 |
| T043 | FR-003 / FR-006 / FR-022 / SC-006 / D-501…D-508 / X-1…X-8 三态一致 |
| T044 | FR-034 |
| T045 | FR-033 / SC-016 / A1–A6 |
| T046 | FR-033 / A1–A6 |
| T047 | FR-034 |
| T048 | FR-028 / 门禁 / ARCH |
| T049 | FR-026 / FR-027 / SC-012 / 门禁 |
| T050 | SC-010 / 全量回归 / 基线 |
| T051 | FR-033 / SC-015（支撑） |
| T052 | FR-032 / FR-033 / SC-015 / 质量门禁 5 |
| T053 | 只读检查 / 原则 III |
| T054 | quickstart / A1–A6 |
| T055 | FR-033 / FR-034 / SC-015（判定） |
| T056 | FR-031 / SC-016 / 审计 / 全 FR / SC / X-1…X-8 三态一致 |
| T057 | 最终回归 / 基线 |
| T058 | FR-033 / SC-015 / 宪法 v1.8.0 跨 feature 承接 / 质量门禁 5（B25F1 接线守卫） |

> **T002 / T003 / T004 / T013 / T053 / T054 / T057** 主要为基线 / 上游取证 / 门禁 /
> 夹具 / 只读检查 / quickstart / 最终回归（不单挂某条 FR/SC）。
> **T051** 写人工记录主体；**T052** 写最终追认（含质量门禁 5）；**T055** 是文档守卫，
> MUST 在 T052 / T047 / T058 之后执行；**T056 / T057** 是最终审计与回归。
> **T058** 是 B25F1「下游承接（B20F2）」的接线 / 守卫，**MUST 在 T052 之前通过**。

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 记录基线、确认上游锚点、建立人工记录骨架；零行为改动。

- [X] T001 Create `harness/verification/B20F2/manual-verification.md` with the five-section skeleton（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）and a `§1.1 基线` placeholder; create the `harness/verification/B20F2/` directory. T051/T052 finalize the record; T055 is the final document guard.
- [X] T002 Run the real full baseline `.venv/bin/python -m pytest -q --tb=no` and record passed / skipped / failed / elapsed in `harness/verification/B20F2/manual-verification.md` §1.1（2026-11-22 expected: `1991 passed, 7 skipped`；elapsed 以本机为准）.
- [X] T003 [P] Re-check upstream versions and anchors (`langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`) against `specs/b20f2-trace-query-sqlite/contracts/upstream-parity.md` §1/§2; update line numbers only if they drifted. Also verify the **X-1…X-8** deviation rows are one-to-one with P-01…P-07's `DIFF` / `STRICTER` aspects（宪法原则 XI v1.12.0 三态一致）；add or repair any missing row.
- [X] T004 [P] Confirm zero read-only / dependency changes: run `git diff --exit-code -- harness/demo/target.py pyproject.toml THIRD_PARTY_NOTICES specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`; report the result to T001 / T056.
- [X] T058 Wire / verify the B20F2 downstream clause in `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B20F2）」; confirm it requires both `FileTraceStore` and `SqliteTraceStore` query evidence for the real-model round; confirm `spec.md` / `plan.md` references resolve. **Blocking**: MUST pass before T052 sign-off（编号按追加分配；执行顺序在 T052 之前）. 宪法 v1.8.0 跨 feature 承接 / 质量门禁 5.

**Checkpoint**: Baseline recorded; upstream anchors confirmed; manual skeleton exists; B25F1 downstream clause in place; no behavioural change.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 建立共享行构造 / 共享查询引擎 / SQLite 骨架 / 导出面 / 冻结面更新 / 测试夹具。
**⚠️ CRITICAL**: 本阶段完成前，US1 / US2 / US3 / US4 / US5 不开始。

- [X] T005 Implement `src/freegraph/observability/_payloads.py` with `span_to_dict(span)`（`kind="span"` + 11 fields，`attributes` / `context` 用 `dict(...)`）and `record_to_dict(record)`（`kind="trace_record"` + `to_jsonable()`）；带署名头 + 模块 docstring。Update `src/freegraph/observability/_file_store.py` to import these helpers and delete its local `_span_to_dict` / `_record_to_dict`; **write-side behaviour MUST stay byte-for-byte equivalent**（only pure-function move）.
- [X] T006 [P] Implement `src/freegraph/observability/_query.py` request validation: `normalize_query(query) -> TraceQuery`（`None → TraceQuery()`；`query` 非 `TraceQuery` / 非 `None` ⇒ `TypeError`；5 字段非 `str` / `None` ⇒ `TypeError`）and `parse_instant_ns(text) -> int`（`Z` / 偏移 / 无时区按 UTC；小数右补到 9 位；非法 ⇒ `ValueError`）；模块只 import 标准库 + L1 `TraceQuery`，**不 import `sqlite3` / 文件 API**；带署名头。
- [X] T007 Implement `src/freegraph/observability/_query.py` row validation: `normalize_row(row) -> dict | None`；`span` 必需 12 键（含 `kind`）、`trace_record` 必需 14 键（含 `kind`）；类型规则严格（`superstep` 用 `type(x) is int` 排除 `bool`；`attributes` / `context` dict；`triggers` / `concurrency_group` / `barrier_groups` list；`error` dict / None 且 `type` / `message` str）；未知 kind / 缺字段 / 类型不符 ⇒ `None`；额外字段丢弃；只返回冻结字段。
- [X] T008 Implement `src/freegraph/observability/_query.py` `finalize(rows, query) -> list[dict]` **skeleton**：仅 `run_id` / `thread_id` 精确匹配（AND）+ 确定性直通顺序；**暂不实现**时间过滤 / `node` 过滤 / 最终平局排序（分别归 T019 / T027 / T030）；返回新列表（元素已是新 dict）。
- [X] T009 [P] Create `src/freegraph/observability/_sqlite_store.py` with signature header + module docstring + `SqliteTraceStore` skeleton: `__slots__`（`_database` / `_on_error` / `_lock` / `_local` / `_write_errors` / `_last_error`）；constructor `SqliteTraceStore(database, *, on_error=None)` only stores params / initializes lock / thread-local / diagnostics; `write_errors` / `last_error` properties; sink callbacks stubs (`on_span_start` no-op, `current_span` returns `None`); `query()` stub returns `[]`; **no filesystem / sqlite access yet**.
- [X] T010 Export `SqliteTraceStore` from `src/freegraph/observability/__init__.py`: import it and append to `__all__`; update the module docstring to list `SqliteTraceStore`; keep the existing 6 symbols and `trace_run_scope` non-export unchanged; MUST NOT add it to `freegraph.graph` or `freegraph.runtime.__all__`.
- [X] T011 Update `tests/facade/test_api_snapshot.py`'s `test_observability_module_exports_only_its_own_symbols` exact set to add `SqliteTraceStore`; update `tests/contracts/test_b19f1_lazy.py` to assert `SqliteTraceStore` is in `observability.__all__` and still absent from `freegraph.graph`. **只增不改**.
- [X] T012 Update `tests/contracts/test_architecture.py` `SIGNED_SOURCE_FILES` to append `src/freegraph/observability/_payloads.py` / `_query.py` / `_sqlite_store.py`; update `tests/contracts/test_b19f1_gates.py` `paths` and `test_no_network_client_is_used_by_new_modules` to include the 3 new modules. **只增不改**.
- [X] T013 [P] Add reusable B20F2 helpers to `tests/observability/conftest.py`: `seed_events(store, *, spans=(), records=())`（按事件类型调用 `on_span_end` / `on_trace_record`）、`assert_rows_equal(left, right)`（逐条 dict 比较并给出可读差异）、`query_by_kind(rows, kind)`；keep existing B18F1 / B19F1 / B20F1 fixtures unchanged.

**Checkpoint**: Shared `_payloads` / `_query` frozen; `SqliteTraceStore` skeleton exported; frozen-surface tests updated; fixtures ready.

---

## Phase 3: User Story 1 - 按 run / thread 精确回查一次运行 (Priority: P1) 🎯 MVP

**Goal**: `FileTraceStore.query()` 支持 `run_id` / `thread_id` / 空过滤器；返回 span + record 两类行；字段 11/13 逐字；`json.dumps` 成功。

**Independent Test**: 写入 2 次运行（不同 `run_id`，分属 2 个 `thread_id`）；按 `run_id` 查询只返回该次运行的全部条目；按 `thread_id` 查询只返回该 thread；空过滤器返回全部；结果可 `json.dumps`。

### Tests for User Story 1

- [X] T014 [P] [US1] Write `tests/observability/test_b20f2_query_api.py`: empty filter / `query=None` returns all（只含合法 B20F1 行）; `run_id` exact filter; `thread_id` exact filter; both `kind`s present; span 12-key / record 14-key field sets; `record.span_id` ↔ span `id`; result is a new list / dicts; `json.dumps` succeeds; `None` ≠ `""`（空字符串是字面值）; **unsafe `run_id` filter values**（`""` / `a.b` / `a/b` / `../x`）⇒ `[]`（不拼路径、不目录穿越）; **span-only storage**（只调用 `on_span_end` 构造）returns span rows with 0 records; `thread_id=None` entries only match when the filter is `None`; non-ASCII / newline / control characters round-trip and `json.dumps` succeeds.
- [X] T015 [US1] Implement `FileTraceStore.query()` in `src/freegraph/observability/_file_store.py`: `normalize_query`; unsafe / non-allowlist `run_id` filter ⇒ `[]`; missing directory ⇒ `[]`; directory-is-file ⇒ `NotADirectoryError`; enumerate regular files matching `^trace-([A-Za-z0-9][A-Za-z0-9_-]*)\.jsonl$`; skip symlinks / non-allowlist names + WARNING; parse lines (`json.loads`), `normalize_row`, skip bad rows + WARNING; call `_query.finalize`; no write lock; no filesystem side effects. **Update the module docstring** so it no longer claims the module has no query API. **Write side unchanged**.
- [X] T016 [US1] Update `tests/contracts/test_b20f1_contracts.py::test_public_face_is_write_only_and_has_diagnostics`（**拆分而不删**）：keep the write-side 4 methods + 2 diagnostics + no lifecycle assertion; change `queries` expectation from `[]` to `["query"]`; keep `search` / `read` / `read_all` forbidden. **Verify (do not duplicate) the supersession note** already present in `specs/b20f1-local-trace-jsonl/spec.md`（Clarifications / SC-006）and `specs/b20f1-local-trace-jsonl/contracts/file-trace-store-contract.md` §1 / §8: `query()` 由 B20F2 新增；B20F1 交付时无查询方法；写侧 / 生命周期 / 四路诊断断言不变；**不删除**原事实.
- [X] T017 [US1] Run `.venv/bin/python -m pytest tests/observability/test_b20f2_query_api.py tests/contracts/test_b20f1_contracts.py -q`; fix US1 failures; do not weaken assertions.

**Checkpoint**: US1 is independently functional; run / thread / empty-filter queries return the full B20F1 row view.

---

## Phase 4: User Story 2 - 按时间范围定位一次运行 (Priority: P2)

**Goal**: 时间窗闭区间、按有效起始时刻、纳秒精度；record 用同 run 关联 span 的 `start_time`；倒置 ⇒ `[]`；非法串 ⇒ `ValueError`。

**Independent Test**: 写入 `T0 < T1 < T2` 的 trace；查询 `[T1, T1]` 只返回 `T1`；只给 `start_time=T1` 返回 `T1` 及之后；`start_time > end_time` ⇒ `[]`；`Z` / 偏移 / 无时区 / 9 位小数被正确处理。

### Tests for User Story 2

- [X] T018 [P] [US2] Write `tests/observability/test_b20f2_query_time.py`: closed interval / boundary inclusion; **one-sided bounds（only `start_time` ⇒ items with effective time `>= start`; only `end_time` ⇒ items with effective time `<= end`; the unspecified side is unbounded）**; inverted range ⇒ `[]`; `Z` / `+08:00` / `+0800` / naive UTC; 9-digit fractional seconds（不得截断到微秒）; invalid string ⇒ `ValueError`; record effective time uses the linked span's `start_time`; record without linked span is excluded by any time bound; other run's same `span_id` is not used.
- [X] T019 [US2] Implement time filtering in `_query.finalize` + `parse_instant_ns` in `src/freegraph/observability/_query.py`: build `(run_id, span_id) -> start_ns` index (same run only); inclusive bounds; one-sided; inverted `[]`; ns precision; no `datetime.microsecond` truncation; no cross-run record link.
- [X] T020 [US2] Run `.venv/bin/python -m pytest tests/observability/test_b20f2_query_time.py -q`; fix time defects.

**Checkpoint**: US2 is independently functional; time windows are precise and deterministic.

---

## Phase 5: User Story 5 - 两个后端可替换 (Priority: P2)

**Goal**: `SqliteTraceStore` 写侧与 `FileTraceStore` 同语义；查询结果逐条等价（A6 / SC-006）。

**Independent Test**: 同一组 B19F1 事件分别写入 JSONL / SQLite；对同一空过滤器 / 四类过滤 / 组合查询，两个结果列表逐条相等。

### Tests for User Story 5

- [X] T021 [P] [US5] Write `tests/observability/test_b20f2_sqlite_write.py`: constructor zero side effect; `on_span_start` no-op; **`on_span_end` with a start snapshot (`end_time=None`) writes nothing and creates no DB / directory / table**; span / record rows with 11/13 fields; run_id safety; append across runs; `write_errors` / `last_error` / `on_error` / WARNING on failure; `BaseException` not swallowed; no retry; same store across runs; per-instance lock identity (`store_a._lock is not store_b._lock`).
- [X] T022 [P] [US5] Write `tests/observability/test_b20f2_backend_parity.py`: seed the same spans / records into `FileTraceStore` and `SqliteTraceStore`（**include one start snapshot with `end_time=None` and assert both backends ignore it**）; compare empty filter, `run_id`, `thread_id`, `node`, time window, and combination; assert row counts / field values / ordering are identical（**完全相同的重复行只比较多重集合，不比较相对顺序**）; `json.dumps` both; assert `input_state` / `output_state` / `error` round-trip equal.
- [X] T023 [US5] Implement `SqliteTraceStore` write side in `src/freegraph/observability/_sqlite_store.py`: constructor / diagnostics（constructor rejects `:memory:` / SQLite URI with `ValueError`）; **`on_span_end` no-op when `span.end_time is None`**; `on_span_end` / `on_trace_record` build rows via `_payloads`; run_id allowlist; per-instance lock; lazy `mkdir(parents=True, exist_ok=True)`; pre-create DB file `0o600` if absent; `sqlite3.connect(timeout=5.0)` + `PRAGMA busy_timeout=5000`; `CREATE TABLE IF NOT EXISTS trace_entries` + indexes; `INSERT` + `commit` + close; `Exception` isolation / 4-way diagnostics / no retry; `BaseException` not swallowed; no `close()` / context manager.
- [X] T024 [US5] Implement `SqliteTraceStore.query()` in `src/freegraph/observability/_sqlite_store.py`: `normalize_query`; missing DB ⇒ `[]`; read-only connection (`PRAGMA query_only=ON`); `PRAGMA table_info(trace_entries)` validation（missing table ⇒ `[]`；**missing required column / type conflict ⇒ `[]` + WARNING；extra columns tolerated and ignored**）；`SELECT payload`；`json.loads` + `normalize_row`（bad row ⇒ skip + WARNING）；`_query.finalize`；corrupt / non-SQLite / I/O ⇒ raise; no migration / creation / modification.
- [X] T025 [US5] Run `.venv/bin/python -m pytest tests/observability/test_b20f2_sqlite_write.py tests/observability/test_b20f2_backend_parity.py -q`; fix SQLite / parity defects.

**Checkpoint**: US5 is independently functional; JSONL and SQLite are interchangeable for the same query.

---

## Phase 6: User Story 3 - 按节点名查最慢的那一步 (Priority: P3)

**Goal**: `node` 精确匹配；返回该节点自身 span、内部模型 / 工具 span、record；其它节点 0 条；`task_id` 不是过滤器。

**Independent Test**: 写入含 `a` / `b` / `c` 节点且 `b` 内部调用模型 / 工具的 trace；查询 `node="b"` 返回节点 `b` 的 span + 模型 / 工具 span + record；不返回 `a` / `c`；fan-out record 的 `task_id="b:TaskId"` 仍因 `node == "b"` 返回。

### Tests for User Story 3

- [X] T026 [P] [US3] Write `tests/observability/test_b20f2_query_node.py`: node exact match（大小写敏感、非子串）；`b` 的模型 / 工具 span 一并返回；`b` 的 record 返回；其它节点 0 条；`task_id` / `superstep` / `checkpoint_id` 过滤不存在（传这些关键字应 `TypeError`）；fan-out `task_id="b:TaskId"` 仍命中 `node="b"`；两个后端结果一致。
- [X] T027 [US3] Implement `node` filtering in `src/freegraph/observability/_query.py` so that all rows with the same `node` (node span, model / tool child spans, record) match; ensure no `kind` / `name` exclusion; keep `task_id` / `superstep` / `checkpoint_id` as return-only fields.
- [X] T028 [US3] Run `.venv/bin/python -m pytest tests/observability/test_b20f2_query_node.py -q`; fix node-filter defects.

**Checkpoint**: US3 is independently functional; node queries return the whole "step".

---

## Phase 7: User Story 4 - 在 CI 里写断言 (Priority: P4)

**Goal**: 返回结果稳定、可 JSON 序列化、可断言；排序确定；结果独立副本。

**Independent Test**: 一次运行含 2 次模型 span；按 `run_id` 查询计数 == 2；连续两次查询逐条相等；调用方原地排序 / 修改不影响再次查询；`json.dumps` 成功。

### Tests for User Story 4

- [X] T029 [P] [US4] Write `tests/observability/test_b20f2_query_result.py`: `json.dumps(result)` success for both backends; only pure data types; count model spans == 2; repeated query equality; caller mutation does not affect store / next query; sorting keys (`start_ns`, `run_id`, `kind_rank`, `stable_id`); record-before-span at the same effective time; untimed record ordering; extra fields dropped; unknown kind skipped.
- [X] T030 [US4] Implement full result ordering / purity in `src/freegraph/observability/_query.py`: timed `(start_ns, run_id, kind_rank, stable_id)` + untimed `(run_id, superstep, task_id, span_id)`; record-before-span at the same effective time; each returned dict is a new object; list is new; no store references; deterministic tie-breaks; no `datetime` microsecond truncation.
- [X] T031 [US4] Run `.venv/bin/python -m pytest tests/observability/test_b20f2_query_result.py -q`; fix result / sorting defects.

**Checkpoint**: US4 is independently functional; query results are CI-ready.

---

## Phase 8: Cross-Cutting Query Tolerance / Read-Only / Validation / SQLite Lifecycle

**Purpose**: 容错 / 只读 / 类型校验 / SQLite 生命周期 / 并发写 + 查询；覆盖 SC-011 / SC-013 / SC-017 / SC-018。

- [X] T032 [P] Write `tests/observability/test_b20f2_query_tolerance.py`: JSONL bad line / truncated last line; unknown `kind`; known kind missing field / wrong type / `superstep=True`; extra field dropped; non-allowlist `trace-a.b.jsonl`; symlink candidate skipped; single file unreadable skipped; all candidates unreadable ⇒ raise; SQLite incompatible table ⇒ `[]` + WARNING; SQLite single-row `payload` JSON decode failure（含嵌套 `input_state` / `output_state` / `error`）⇒ skip; SQLite corrupt / non-SQLite ⇒ raise; **duplicate identical rows are returned twice（no dedupe）**.
- [X] T033 [P] Write `tests/observability/test_b20f2_query_read_only.py`: missing directory / DB ⇒ `[]`; directory path is a regular file ⇒ raise; query does not create files / dirs / tables; query before/after SHA-256 of every store file unchanged; corrupt JSONL / incompatible SQLite table not modified; query does not follow symlinks out of the store.
- [X] T034 [P] Write `tests/observability/test_b20f2_query_validation.py`: `query` non-`TraceQuery` / non-`None` ⇒ `TypeError`; each of 5 fields non-`str` / non-`None` ⇒ `TypeError`（含 `run_id=123` / `node=["b"]` / `start_time=123`）；合法字符串但坏时间 ⇒ `ValueError`；inverted range ⇒ `[]`; validation happens before any file / DB read (use a directory with a poisoned file to prove).
- [X] T035 [P] Write `tests/observability/test_b20f2_sqlite_lifecycle.py`: constructor creates nothing; first write creates parent dirs / DB file / table / indexes; query does not create; POSIX new DB `mode & 0o077 == 0`; existing wider file not loosened; `not hasattr(store, "close")` / `__enter__` / `__exit__`; unsupported `:memory:` / URI ⇒ **构造时 `ValueError`**（assert this behavior）; no persistent handle; **parent dir unwritable ⇒ write failure isolated + four-way diagnostics, graph/run not blocked**.
- [X] T036 [P] Write `tests/observability/test_b20f2_sqlite_concurrency.py`: `ThreadPoolExecutor` writes N records + concurrent queries; all rows readable; no DB corruption; no half / uncommitted row; two instances have distinct locks and do not block each other; cross-process writer/query via `multiprocessing` / subprocess; `busy_timeout` finite; Windows marker / branch.
- [X] T037 [P] Implement JSONL tolerance / read-only fixes in `src/freegraph/observability/_file_store.py`: per-file I/O skip + WARNING; all-candidates-unreadable raise; symlink / non-allowlist skip; no writes; no lock; no side effects.
- [X] T038 [P] Implement validation / time-error fixes in `src/freegraph/observability/_query.py`: `TypeError` for query / fields; `ValueError` for bad time; inverted `[]`; validation before any backend read; no accidental `bool` as `int`.
- [X] T039 [P] Implement SQLite tolerance / read-only / lifecycle / concurrency fixes in `src/freegraph/observability/_sqlite_store.py`: table/column validation; row decode skip; corrupt DB raise; lazy parent / DB / table; `0o600`; existing not loosened; busy timeout; per-instance lock; no migration / creation on query; no `close()`.
- [X] T040 Run `.venv/bin/python -m pytest tests/observability/test_b20f2_query_tolerance.py tests/observability/test_b20f2_query_read_only.py tests/observability/test_b20f2_query_validation.py tests/observability/test_b20f2_sqlite_lifecycle.py tests/observability/test_b20f2_sqlite_concurrency.py -q`; fix cross-cutting defects.

**Checkpoint**: Cross-cutting semantics complete: tolerance, read-only, validation, SQLite lifecycle / concurrency.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 契约 / 门禁 / 差分 / README / 一键验收 / 人工验证 / 全量回归。

- [X] T041 [P] Write `tests/contracts/test_b20f2_contracts.py`: `FileTraceStore` / `SqliteTraceStore` in `freegraph.observability.__all__`; not in `freegraph.graph` / `freegraph.runtime.__all__`; `FileTraceStore.query` present; `search` / `read` / `read_all` absent; `SqliteTraceStore` has sink callbacks + `query` + diagnostics, no `close` / context manager; `Span` 11 / `TraceRecord` 13 / `TraceQuery` 5 / `TraceSink` 3 / `RunConfig` 9 / `SuperStepResult` / `PregelTask` unchanged; L5 modules import only stdlib + L1 + same layer; no public table / column / SQL / connection.
- [X] T042 [P] Write `tests/contracts/test_b20f2_gates.py`: no `langchain*` / `langgraph*` / `langsmith` / `opentelemetry*`; `sqlite3` only in `_sqlite_store.py`（`_file_store.py` / `_query.py` / `_payloads.py` MUST NOT import it）；no env reads; no `socket` / `http` / `urllib` / `requests` / `httpx`; signature headers + module docstrings; dependency closure still empty; **FR-031 scope guard**：the 3 new modules MUST NOT import / contain OTLP、UI、Agent Server、Postgres driver、retention / eval code（`psycopg` / `asyncpg` / `opentelemetry` / `server` / `ui` 等均为禁止项）.
- [X] T043 [P] Write `tests/differential/test_b20f2_trace_query_parity.py`: D-501…D-508 per [contracts/upstream-parity.md](./contracts/upstream-parity.md) §3; upstream absent ⇒ `pytest.importorskip`; assert local query shape / zero egress / env no-op / backend parity. Also assert the P ↔ X mapping（X-1…X-8）in `contracts/upstream-parity.md` §4 covers every `DIFF` / `STRICTER` aspect（宪法原则 XI v1.12.0）：X-5 只映射 P-01、P-03 由 X-2 承接、**P-04 / D-503 不标 SAME 行为面**.
- [X] T044 [P] Update `harness/demo/README.md`: add the B20F2 row / note for `query()` stable interface + `SqliteTraceStore(database=...)` + "schema / file format internal; Studio only via query()"; keep the existing B20F1 `已锁定（B20F1）` row verbatim.
- [X] T045 [P] Create `harness/verification/B20F2/acceptance.py` (A1–A6): A1 run / A2 thread / A3 time / A4 node / A5 combination / A6 backend parity; socket monitor for zero egress; JSON-serialisable results; exit code `0` PASS / `1` FAIL / `2` env not ready; last line `B20F2 acceptance: PASS|FAIL`.
- [X] T046 Add `test_b20f2_one_click_acceptance_script_passes` to `tests/runtime/test_acceptance_script.py`; run `harness/verification/B20F2/acceptance.py` in a subprocess and assert exit code 0 + `B20F2 acceptance: PASS`. **Depends on T045**（脚本必须先存在）.
- [X] T047 [P] Update `harness/verification/README.md`: add the **B20F2** row in the「当前已有记录」table, linking `B20F2/manual-verification.md` and `B20F2/acceptance.py`; mirror the B20F1 row style (status / pytest count / A1–A6 / gate 5 deviation).
- [X] T048 Run architecture / layer gates: `.venv/bin/python -m pytest tests/contracts/test_architecture.py tests/gates -q` and `.venv/bin/python harness/scripts/gates/gate_G25_import_graph.py`; confirm no new L3 → L5 / L5 → L2 edges; `_file_store.py` remains L5 + no `sqlite3`.
- [X] T049 Run dependency / env / egress gates: G21 / G24 / G26 / G27 via `.venv/bin/python -m pytest tests/gates -q` and the relevant scripts; record results in `harness/verification/B20F2/manual-verification.md` §1.1 / §4.
- [X] T050 Run the full regression `.venv/bin/python -m pytest -q --tb=no`; record actual output in `harness/verification/B20F2/manual-verification.md` §1.1 / §4; compare with baseline `1991 passed, 7 skipped`（only add, never reduce）.
- [X] T051 Update `harness/verification/B20F2/manual-verification.md` with: four filters + combination actual outputs; JSONL / SQLite parity evidence; empty filter / sorting / `json.dumps` evidence; tolerance evidence（bad line / unknown kind / field mismatch / non-allowlist / symlink / incompatible table）；concurrency write + query（含 Windows note）；zero-egress evidence；README / `__all__` updates.
- [X] T052 Finalize `harness/verification/B20F2/manual-verification.md`（**final manual record · MUST run after T050 / T051 / T058**）：add `observability.__all__` exact-set follow-up（只增 `SqliteTraceStore`）and B20F1「无查询方法」assertion **split-not-delete** follow-up；**质量门禁 5 偏离声明（真实模型轮由 B25F1 承接；沿用 B20F1 先例；引用 B25F1 §「下游承接（B20F2）」并由 T058 守卫）**；**发起者追认文字（确认人 + 日期，由发起者本人签署）**；遗留问题（无 UI / 无 OTLP / 无分页 / schema 无迁移）。
- [X] T053 [P] Verify read-only / dependency files unchanged: `git diff --exit-code -- harness/demo/target.py pyproject.toml THIRD_PARTY_NOTICES specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`; record the result.
- [X] T054 [P] Run the [quickstart.md](./quickstart.md) validation scenarios against `src/freegraph/observability/_file_store.py` / `_sqlite_store.py`; fix only defects, do not weaken assertions.

---

## Phase 10: Coverage Closure & Final Document Guard

**Purpose**: 关闭 SC-015 的判定覆盖，最终审计 FR/SC、红名单与范围边界。

- [X] T055 Write `tests/runtime/test_b20f2_manual_record_guard.py` for **SC-015**: assert `harness/verification/B20F2/manual-verification.md` exists, has non-empty five-section structure, contains code blocks / actual outputs for four filters + combination + JSONL / SQLite parity + empty filter / sorting + **`json.dumps` output** + tolerance + concurrency (**including Windows note**) + zero-egress + `observability.__all__` / B20F1 assertion follow-up + **质量门禁 5 偏离** + **发起者追认（确认人 + 日期）**; assert `harness/features/B25F1_双跑验收与迁移说明.md` contains §「下游承接（B20F2）」 with both `FileTraceStore` / `SqliteTraceStore` query evidence; assert `harness/demo/README.md` contains the B20F2 row and keeps `已锁定（B20F1）`; assert `harness/verification/README.md` contains a **B20F2** row. **MUST run after T047 / T052 / T058**; MUST NOT be enabled before the record is written.
- [X] T056 Final audit in `harness/verification/B20F2/manual-verification.md`: map FR-001…FR-034 / SC-001…SC-018 to executing tasks/tests; re-check plan red list B-1…B-13; re-check **X-1…X-8** P↔X 三态一致（宪法原则 XI v1.12.0，含 X-5 只映射 P-01、X-2 承接 P-03、P-04 / D-503 不标 SAME 行为面）；confirm T058 已通过且 B25F1 §「下游承接（B20F2）」存在；confirm no 未决澄清标记、no 未完成占位、no out-of-scope implementation（OTLP / UI / Agent Server / Postgres / retention / eval / `checkpoint_id` filter / pagination）；confirm schema / file format internal；confirm quality gate 5 deviation registered.
- [X] T057 Run the final full regression `.venv/bin/python -m pytest -q --tb=no`（含 T055 文档守卫）；record actual output in `harness/verification/B20F2/manual-verification.md` §4; confirm counts only increase and the B20F2 guard is green.

**Checkpoint**: All coverage gaps closed; SC-015 has a document guard; full regression green; manual verification signed; red list closed.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖，可立即开始。
- **Foundational (Phase 2)**: 依赖 Setup；**阻塞** US1 / US2 / US3 / US4 / US5。
- **US1 (Phase 3)**: 依赖 Foundational（T005–T008 / T010 / T013）；可独立测试。
- **US2 (Phase 4)**: 依赖 Foundational + US1 的 `query()`（T015）；可独立测试。
- **US5 (Phase 5)**: 依赖 Foundational（T005–T010 / T013）+ US1 的查询语义；可独立测试。
- **US3 (Phase 6)**: 依赖 Foundational + US1 的 `query()`；可独立测试。
- **US4 (Phase 7)**: 依赖 Foundational + US1 的 `query()`；可独立测试。
- **Phase 8 (跨切面)**: 依赖 US1 / US5 的查询 / 写入路径；可独立测试。
- **Phase 9 (Polish)**: 依赖所有目标阶段完成。
- **Phase 10 (Coverage Closure)**: 依赖 Phase 9 的 T052；T055 MUST 在 T047 / T052 / T058 之后；T056 / T057 最后执行。
- **T058（跨 feature 接线守卫）**：Setup 阶段执行；**阻塞 T052**。

### User Story Dependencies

- **US1 (P1 · MVP)**：T014 → T015 → T016 → T017；是 US2 / US3 / US4 / US5 的查询前提。
- **US2 (P2)**：T018 → T019 → T020；依赖 T015；不依赖 US3 / US4 / US5。
- **US5 (P2)**：T021 / T022 → T023 → T024 → T025；依赖 T005–T010 / T013；提供 SQLite 后端。
- **US3 (P3)**：T026 → T027 → T028；依赖 T015；不依赖 US2 / US4 / US5。
- **US4 (P4)**：T029 → T030 → T031；依赖 T015；不依赖 US2 / US3 / US5。

### Within Each Phase

- 测试先写并**先失败**；再实现；测试通过后进入下一任务。
- Foundational：T005 / T006 可并行；T007 依赖 T006（同文件）；T008 依赖 T006 / T007；
  T009 独立；T010 依赖 T009；T011 依赖 T010；T012 依赖 T005 / T006 / T009；T013 可并行。
- US1：T014 先写；T015 依赖 T008 / T014；T016 依赖 T015；T017 最后。
- US2：T018 先写；T019 依赖 T008 / T018；T020 最后。
- US5：T021 / T022 先写（可并行）；T023 依赖 T009 / T021；T024 依赖 T023 / T022；T025 最后。
- US3：T026 先写；T027 依赖 T008 / T026；T028 最后。
- US4：T029 先写；T030 依赖 T008 / T029；T031 最后。
- Phase 8：T032–T036 可并行写测试；T037 / T038 / T039 可并行实现（不同文件）；T040 最后。
- Phase 9：T041–T045 / T047 / T053 / T054 可并行；**T045 → T046**；**T048 → T049 → T050 → T051 → T052 串行**（门禁 / 回归 / 同一 manual 文件）。
- Phase 10：T055 在 T047 / T052 / T058 之后；T056 → T057 串行。
- Setup：T058 可在 Setup 内完成，但 **MUST 早于 T052**。

---

## Parallel Opportunities

- **Setup**: T003 / T004 / T058 可并行（只读检查 / 跨 feature 接线）；T058 仍 MUST 早于 T052。
- **Foundational**: T005 / T006 可并行；T009 / T013 可并行；T010 → T011 串行。
- **US1**: T014 可先写；T015 → T016 → T017 串行。
- **US2**: T018 可先写；T019 → T020 串行。
- **US5**: T021 / T022 可并行写测试；T023 → T024 → T025 串行。
- **US3**: T026 可先写；T027 → T028 串行。
- **US4**: T029 可先写；T030 → T031 串行。
- **Phase 8**: T032–T036 可并行写测试；T037 / T038 / T039 可并行实现；T040 最后。
- **Phase 9**: T041–T045 / T047 / T053 / T054 可并行；T045 → T046；T048 → T049 → T050 → T051 → T052 串行；T058 必须先于 T052。
- **Phase 10**: T055 依赖 T047 / T052 / T058；T056 → T057 串行。

### Parallel Example: US5

```bash
Task: "Write SQLite write tests in tests/observability/test_b20f2_sqlite_write.py"
Task: "Write backend parity tests in tests/observability/test_b20f2_backend_parity.py"
```

### Parallel Example: Phase 8

```bash
Task: "Write tolerance tests in tests/observability/test_b20f2_query_tolerance.py"
Task: "Write read-only tests in tests/observability/test_b20f2_query_read_only.py"
Task: "Write validation tests in tests/observability/test_b20f2_query_validation.py"
Task: "Write SQLite lifecycle tests in tests/observability/test_b20f2_sqlite_lifecycle.py"
Task: "Write SQLite concurrency tests in tests/observability/test_b20f2_sqlite_concurrency.py"
```

### Parallel Example: Phase 9

```bash
Task: "Write contract tests in tests/contracts/test_b20f2_contracts.py"
Task: "Write gate tests in tests/contracts/test_b20f2_gates.py"
Task: "Write differential tests in tests/differential/test_b20f2_trace_query_parity.py"
Task: "Update harness/demo/README.md"
Task: "Create harness/verification/B20F2/acceptance.py"
```

---

## Implementation Strategy

### MVP First（US1 Only）

1. 完成 Phase 1 Setup。
2. 完成 Phase 2 Foundational。
3. 完成 Phase 3 US1（T014–T017）。
4. **STOP and VALIDATE**：运行 US1 定向测试 + `quickstart.md` §1/§2；
   `run_id` / `thread_id` / 空过滤器返回完整 B20F1 行视图。
5. US1 是 MVP；US2 / US5 / US3 / US4 是后续增量。

### Incremental Delivery

1. Setup + Foundational → 共享 `_payloads` / `_query` / `SqliteTraceStore` 骨架 / 导出 / 夹具。
2. US1 → JSONL 查询 + 四类过滤基础 + 空过滤器。
3. US2 → 时间窗 / 纳秒 / 倒置 / 有效起始时刻。
4. US5 → SQLite 写侧 + 查询 + 两后端等价。
5. US3 → 节点过滤（含模型 / 工具子 span）。
6. US4 → 稳定排序 / JSON 断言 / 独立副本。
7. Phase 8 → 容错 / 只读 / 类型校验 / SQLite 生命周期 / 并发。
8. Phase 9 → 契约 / 门禁 / 差分 / README / 一键验收 / 人工记录 / 全量回归。
9. Phase 10 → SC-015 文档守卫 / 最终审计 / 最终回归。

### Parallel Team Strategy

- **Foundational**: A 做 `_payloads` / `_file_store` 接线；B 做 `_query` 校验 / 时间 / 行 / 排序；C 做 `_sqlite_store` 骨架 + 导出 + 夹具。
- **US1**: A 做 `FileTraceStore.query`；B 写 US1 测试；C 更新 B20F1 契约断言。
- **After US1**:
  - A：US2 时间（`_query` 同文件，串行）。
  - B：US5 SQLite 写 + 查询（`_sqlite_store`）。
  - C：US3 节点 / US4 结果 / Phase 8 测试（不同文件）。
- **Phase 9**: 并行做契约 / 门禁 / 差分 / README / 验收 / 人工记录；T058 必须在 T052 之前完成；最后 T052。
- **Phase 10**: 文档守卫 T055 在 T052 之后；T056 / T057 最后。

---

## Notes

- [P] = 不同文件、无未完成依赖。
- [Story] 标签映射到 spec 的 US1–US5；Setup / Foundational / Phase 8 / Phase 9 / Phase 10 为跨切面，不带故事标签。
- 每个任务都必须有精确文件路径；测试任务先写并先失败。
- 冻结面：`Span` 11 字段 / `TraceSink` 3 方法 / `TraceRecord` 13 字段 / `TraceQuery` 5 字段 /
  `RunConfig` 9 字段 / `SuperStepResult` / `PregelTask` / `stream()` 信封 / 门面 8 符号 /
  L1 22 符号 / `runtime.__all__` **零改动**；唯一新增公开符号 = L5 `SqliteTraceStore`；
  `FileTraceStore.query` 是既有类的新方法。
- 不新增运行时依赖；`harness/demo/target.py` / `pyproject.toml` / `THIRD_PARTY_NOTICES` 零改动；
  `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt` 零改动（新符号不进
  `freegraph.graph`）。
- `_file_store.py` 写侧（文件命名 / `kind` / `0o600` / per-instance 锁 / 四路诊断 / 逐行
  短生命周期 / 不重试）**逐字不变**；只新增 `query()` + 改用 `_payloads` 纯函数。
- schema / 表名 / 列名 / SQL / JSONL 文件格式是 C27 ⑤ 的内部实现细节；Studio / 测试 /
  用户只能经 `query()` 取数。
- 人工验证：`harness/verification/B20F2/manual-verification.md`（四类过滤 + 组合 +
  两后端等价 + 空过滤器 / 排序 + 容错 + 并发 + 零出站 + `__all__` / B20F1 断言追认 +
  **质量门禁 5 偏离** + **发起者追认**）；由 T055 自动守卫。
- **T051** 写人工记录主体；**T052** 写最终追认；**T055** 是最终文档守卫
  （MUST 在 T047 / T052 / T058 之后）；T056 / T057 是最终审计与回归。
- **T058** 守卫 B25F1 §「下游承接（B20F2）」与真实模型轮承接条款；**MUST 早于 T052**。
