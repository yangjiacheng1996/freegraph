# Tasks: B6F1 · `StateGraph` 构建器

> **2026-11-20 后续修订（C25 正式作废）**：B8F3 已移除 `alias`；本文件 T008/T014/T027/T041/T046 中的 alias 记录文字保留为历史，当前契约以 B8F3 为准。
> 另：差分场景 **D-74** 已**迁移到 B8F3 D-142**，`tests/differential/parity_probe.py` 不再承载；本文件的 D-74 引用保留为历史墓碑。


**Input**: Design documents from `specs/b6f1-stategraph-builder/`

**Prerequisites**: `plan.md` · `spec.md` · `research.md` · `data-model.md` · `contracts/` · `quickstart.md`

**Tests**: 本任务列表**包含测试任务**。理由：spec 的 SC-001…SC-015 要求可执行判据；宪法原则 VI 要求每条 SC 至少挂一条能判定它的测试任务；仓库既有 feature 均以 pytest 为实现门禁。

**Organization**: 按 spec 的 6 个用户故事组织，每个故事可独立实现与验证。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 不同文件、无未完成依赖，可并行
- **[Story]**: `[US1]`…`[US6]`，对应 spec 的用户故事
- 每个任务均带明确文件路径

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 建立共享测试夹具、确认基线、创建测试模块骨架

- [X] T001 Confirm baseline and current facade expectations in `tests/facade/test_facade.py` (run `.venv/bin/python -m pytest -q`; record current `TestNotWired` / constructor assertions before changes)
- [X] T002 [P] Create shared builder test support in `tests/facade/_builder_support.py` **with the repository copyright/license header** (schema fixtures, node/router stubs, call counters, `builder_summary`, `specs_equivalent`, `build_graph_spec_from_snapshot`)
- [X] T003 Create new test module skeletons with copyright headers and module docstrings in `tests/facade/test_stategraph_builder.py`, `tests/facade/test_stategraph_validation.py`, `tests/facade/test_stategraph_spec.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有用户故事共享的构建器核心：私有类型、容器、注册方法、快照骨架

**CRITICAL**: 本阶段完成前，任何用户故事都不得开始实现。

- [X] T004 Add private dataclasses `_NodeRecord`, `_ConditionalEdgeDraft`, `_ConditionalEdgeSpec`, `_BuilderSpec` with exact fields from `data-model.md` in `src/freegraph/_stategraph.py`
- [X] T005 Initialize private containers `_nodes`, `_edges`, `_conditional_edges`, `_branch_names` in `StateGraph.__init__` in `src/freegraph/_stategraph.py`; keep schema parse deferred, ignore the other constructor params, and keep the constructor side-effect free; `vars(graph)` key set MUST be exactly `{"_schema", "_nodes", "_edges", "_conditional_edges", "_branch_names"}`
- [X] T032a [Foundational] Update `tests/facade/test_facade.py` **in the same phase as T008–T010**: narrow `TestNotWired` to `compile()` and remaining unshipped methods; remove the three builder methods from **both** `test_not_wired_method_raises_not_implemented` (its parametrization) and `test_not_wired_methods_produce_no_real_semantics`; update `test_constructor_has_no_side_effect` to the exact `vars(graph)` key set. Phase 2 MUST end with `pytest -q` green.
- [X] T006 Implement `_branch_name(path)` in `src/freegraph/_stategraph.py` (`path.__name__`; missing or `<lambda>` ⇒ `"condition"`; plain callable `.name` NOT used) and per-source duplicate tracking
- [X] T007 Implement `_normalize_path_map(path, path_map)` in `src/freegraph/_stategraph.py` (list → dict, dict shallow copy, `None` → `Literal[...]` return-annotation inference, other types ⇒ `TypeError`; BV-8)
- [X] T008 Implement `add_node` in `src/freegraph/_stategraph.py` (str / single callable forms; `__name__` → type-name naming; plain callable `.name` NOT used; `TypeError` / `ValueError` rules BV-1…BV-3; record `alias` / `defer` / `metadata`; no user call)
- [X] T009 Implement `add_edge` and private edge aggregation helpers in `src/freegraph/_stategraph.py` (str / list / tuple source; BV-4…BV-6; target order first-seen; duplicate edge idempotent; return `Self`)
- [X] T010 Implement `add_conditional_edges` in `src/freegraph/_stategraph.py` (source / path checks; `path_map` normalization; `__name__` branch name; plain callable `.name` NOT used; duplicate branch name; record `_ConditionalEdgeDraft`; return `Self`)
- [X] T011 Implement `_build_spec()` base in `src/freegraph/_stategraph.py`: `parse_state_schema` → `build_channels` → `NodeSpec` table → static edges → `_ConditionalEdgeSpec` tuple (including `branch`); preserve schema / node / edge / conditional-edge branch order
- [X] T012 Implement `validate(interrupt=None) -> Self` in `src/freegraph/_stategraph.py` by calling `_build_spec()`; if `interrupt` is not `None`, validate each name is a registered node (unknown ⇒ `ValueError`, matching upstream `state.py:1168-1174`); failure must not mutate builder state

**Checkpoint**: Foundation ready. `StateGraph` can register nodes / edges / conditionals and produce a basic `_BuilderSpec`; snapshot-level endpoint / entry validation and route channels are added in user stories.

---

## Phase 3: User Story 1 - 原样写出验收脚本的建图代码 (Priority: P1) MVP

**Goal**: `harness/demo/target.py:142-155` 的建图段原样执行成功，构建器记录 2 节点 / 2 静态边 / 1 条件边。

**Independent Test**: 在 `tests/facade/test_stategraph_builder.py` 中复制 target 建图段（本地 fake 节点），断言 `validate()` 成功且 `_build_spec()` 内容一致。

### Tests for User Story 1

- [X] T013 [P] [US1] Add target-style build test in `tests/facade/test_stategraph_builder.py` (2 nodes, `START` edge, list `path_map`, return edge; assert nodes / edges / conditional edge)
- [X] T014 [US1] Add `alias` / `defer` / single-callable / `metadata` recording test in `tests/facade/test_stategraph_builder.py` (assert `_NodeRecord.alias`, `defer`, metadata copy, inferred node name; `defer` MUST NOT change edge semantics)

### Implementation for User Story 1

- [X] T015 [US1] Audit and fix the target-style flow in `src/freegraph/_stategraph.py` so `add_node` / `add_edge` / `add_conditional_edges` / `_build_spec` satisfy `target.py:142-155` exactly

**Checkpoint**: US1 independently passes; this is the MVP slice.

---

## Phase 4: User Story 2 - 条件边的两种 `path_map` 都能用 (Priority: P1)

**Goal**: list 与 dict 两形态都成功；`END` 不建路由通道；`path_map=None` 按上游 `Literal[...]` 推断。

**Independent Test**: list / dict / None+Literal 各一例；断言归一化映射、`targets`、`route_channels` 与通道顺序。

### Tests for User Story 2

- [X] T016 [US2] Add list / dict / None+Literal / None+non-Literal `path_map` tests in `tests/facade/test_stategraph_builder.py` (normalized map, `branch` recorded from `_branch_name(path)`, `targets` includes `END`, `route_channels` excludes `END`, order preservation; dict with a non-`str` `Hashable` key such as `1` is accepted and copied; None + non-Literal ⇒ `targets == ()` / `route_channels == ()` / `path_map is None`)
- [X] T017 [P] [US2] Add invalid `path_map` container / element type tests and duplicate branch-name tests in `tests/facade/test_stategraph_validation.py` (BV-8 / BV-9; lambda / function branch names)

### Implementation for User Story 2

- [X] T018 [US2] Add route-channel helper `_route_channel_names` and integrate into `_build_spec()` in `src/freegraph/_stategraph.py` (`branch:to:<target>`, `EphemeralValue(Any, guard=False)`, non-`END`, dedupe, after state channels). `defer=True` targets also use `EphemeralValue`; the upstream `LastValueAfterFinish` difference is registered as **X-7** (known unsupported) and owned by B7F4 X-03 when defer lands
- [X] T019 [US2] Audit `_normalize_path_map` against upstream E-02 / E-03 / E-04 / E-17 / E-21 / E-23 in `src/freegraph/_stategraph.py`; ensure tuple / set / str `path_map` ⇒ `TypeError`, list elements / dict values non-`str` ⇒ `TypeError`, `__name__` branch naming (plain callable `.name` NOT used), and lambda / unnamed branch name ⇒ `condition`; non-callable Runnable ⇒ `TypeError` (X-6)

**Checkpoint**: US2 independently passes; US1 remains green.

---

## Phase 5: User Story 3 - 建图错误能被早点指出 (Priority: P2)

**Goal**: 重复节点名、边指向不存在节点、缺少入口等在构建期抛 `ValueError`，消息可定位问题。

**Independent Test**: 3 类核心错误各一例；schema 非法 / 空节点表 / 条件边源与目标 / 保留字符 / action 形态等 BV 矩阵全覆盖。

### Tests for User Story 3

- [X] T020 [US3] Add 3 core error tests in `tests/facade/test_stategraph_validation.py` (duplicate node, unknown single-source edge target via `validate()` **with a valid `START` entry so the target error is the only failure**, missing `START` entrypoint; plus conditional-edge source `START` counts as entrypoint)
- [X] T021 [US3] Add BV matrix + validate-invariance tests in `tests/facade/test_stategraph_validation.py` (BV-1…BV-13; schema `InvalidSchemaError`, empty node table (with `START -> END` to reach BV-11), conditional source/target, `START`/`END` misuse, reserved chars, invalid action forms / invalid `action` or `node` type ⇒ `TypeError` (P-03c), invalid `start_key` type ⇒ `TypeError` (P-04d), plain callable `.name` NOT used, multi-source errors, multi-source `END` / multi-target retained in snapshot, `__parent__` retained in snapshot, empty-node graph `START -> END` ⇒ `ValueError` (X-5), `validate(interrupt=["missing"])` ⇒ `ValueError`; target-existence cases first establish a valid `START` entry; failure leaves `vars(graph)` unchanged; repeated `validate()` is idempotent. BV-8 / BV-9 由 T017 覆盖)

### Implementation for User Story 3

- [X] T022 [US3] Implement snapshot-level validation helpers in `src/freegraph/_stategraph.py` (`_validate_sources`, `_validate_entrypoint`, `_validate_targets`, `_validate_nodes`, `_validate_interrupt`; messages name node / source / branch / target / `entrypoint`; entrypoint = static edge source `START` OR conditional edge source `START`; `_validate_interrupt` checks names against `_nodes`)
- [X] T023 [US3] Integrate validation order into `_build_spec()` in `src/freegraph/_stategraph.py`: schema → **source existence** → **entrypoint** → **target existence** → **empty node table (X-5)** → route channels → snapshot; `validate(interrupt=...)` checks `_validate_interrupt` after `_build_spec()` succeeds; failure leaves builder state unchanged. **Do not enforce the B9F1 `__parent__` reserved-name check / `GraphSpec` V-16 in B6F1**: `__parent__`, multi-source `END`, and multi-source target-count ≠ 1 are retained in the snapshot and left to B7F2's `GraphSpec` final gate

**Checkpoint**: US3 independently passes; all build-time errors are explicit and localized.

---

## Phase 6: User Story 4 - 构建器可链式调用 (Priority: P2)

**Goal**: `add_node` / `add_edge` / `add_conditional_edges` / `validate` 均返回同一 builder，可连续调用。

**Independent Test**: `add_edge(...).add_edge(...)` 与 `add_node(...).add_edge(...).add_conditional_edges(...)` 返回 `is` 同一对象。

### Tests for User Story 4

- [X] T024 [US4] Add chainability identity tests in `tests/facade/test_stategraph_builder.py` (all four methods return the same builder; `add_edge(...).add_edge(...)` works)

### Implementation for User Story 4

- [X] T025 [US4] Audit all builder methods in `src/freegraph/_stategraph.py` for `return self` on success; fix any missing chain return without changing signatures

**Checkpoint**: US4 independently passes.

---

## Phase 7: User Story 5 - 构建器产物可被 `compile()` 消费 (Priority: P2)

**Goal**: `_build_spec()` 的 `channels` / `nodes` / `edges` 可适配 B7F1 的 `GraphSpec` / `NodeSpec`；快照独立、结构等价、顺序稳定。

**Independent Test**: 过滤 `END` 后构造 `GraphSpec` 成功；两次 `_build_spec()` 结构等价但彼此独立；顺序与声明一致。

### Tests for User Story 5

- [X] T026 [P] [US5] Add `GraphSpec` compatibility test in `tests/facade/test_stategraph_spec.py` (construct `GraphSpec` after filtering **single-source** `END`; assert no V-1 / V-2 / V-3 and `conditional_edges == {}`; assert multi-source `("a","b") -> END` is retained in `_BuilderSpec.edges` and rejected by `GraphSpec` V-16, not silently filtered; assert a multi-source key with two targets is retained in `_BuilderSpec.edges` and rejected by `GraphSpec` V-16; assert a `__parent__` node is retained in `_BuilderSpec.nodes` / `node_records` and rejected by the B9F1 `__parent__` reserved-name check on `GraphSpec` construction)
- [X] T027 [US5] Add snapshot independence / structural equivalence / ordering / input-invariance tests in `tests/facade/test_stategraph_spec.py` (two calls; mutate first snapshot; mutate user `path_map` / `metadata` after registration; channel / node / edge / condition order; `node_records` alias preserved; `_ConditionalEdgeSpec.branch` preserved)

### Implementation for User Story 5

- [X] T028 [US5] Finalize `_BuilderSpec` copy semantics in `src/freegraph/_stategraph.py` (new channel instances, `NodeSpec` per call, tuple-copied edges / conditional edges, `node_records` copy)
- [X] T029 [US5] Audit `_build_spec()` output against `contracts/builder-contract.md` §2 in `src/freegraph/_stategraph.py` (field names, types, `targets` includes `END`, `route_channels` excludes `END`, no public symbols)

**Checkpoint**: US5 independently passes; B7F2 can consume the snapshot mechanically.

---

## Phase 8: User Story 6 - 构建期不执行任何用户代码 (Priority: P3)

**Goal**: `add_node` / `add_edge` / `add_conditional_edges` / `validate()` / `_build_spec()` 均不调用节点函数、路由函数或归约器。

**Independent Test**: 使用带调用计数器的节点 / 路由 / 归约器；完成建图与校验后计数全部为 0。

### Tests for User Story 6

- [X] T030 [US6] Add purity + return-form acceptance test in `tests/facade/test_stategraph_builder.py` (node / router / reducer counters remain 0 after all build and validate operations; declare nodes / routers annotated `-> Command`, `-> list[Command | dict]`, `-> None`, `-> Send`, `-> list[Send]` and assert they are accepted without being called)

### Implementation for User Story 6

- [X] T031 [US6] Audit `src/freegraph/_stategraph.py` for accidental user-code calls or return-annotation execution; ensure only type-hint inspection for `Literal` inference and no function invocation

**Checkpoint**: US6 independently passes; build is side-effect free w.r.t. user functions.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 更新既有门面测试、文档、差分、验收脚本、下游接线与全量验证

- [X] T032b [P] Add static interrupt passthrough assertions to `tests/facade/test_facade.py`: `inspect.signature(StateGraph.compile)` contains `interrupt_before` / `interrupt_after`; builder has no public same-named fields; `validate(interrupt=["nope"])` on a valid graph raises `ValueError` with `nope` in the message, matching upstream. (`TestNotWired` narrowing / `vars(graph)` exact set are already done by T032a.)
- [X] T033 [P] Update `src/freegraph/_stategraph.py` **module / class / method-level** docstrings and `src/freegraph/graph.py` docstring to reflect B6F1 wired / compile still B7F2; update the `NotImplementedError` messages of `add_sequence` / `set_entry_point` / `set_conditional_entry_point` / `set_finish_point` / `set_node_defaults` to “本版本不交付 · 另行立项” (MUST NOT keep “由 B6F1 交付”)
- [X] T034 [P] Update `README.md` `StateGraph` row factual wording: builder delivered by B6F1; `compile` still B7F2
- [X] T035 [P] Extend `tests/differential/parity_probe.py` with builder-only scenario model and D-50…D-74 (scenario names include `builder`; wire into `run_all()` so `diff_parity.py -k builder` works; do not change existing runtime scenarios); verify and reuse the already-recorded E-18…E-24 measured evidence in `research.md` (do not add duplicate rows)
- [X] T036 [P] Extend `tests/differential/test_parity_probe.py` with a builder-scenario pytest wrapper (upstream absent ⇒ skip)
- [X] T037 [P] Add one-click acceptance script `harness/verification/B6F1/acceptance.py` **with the repository copyright/license header**, covering target build, list/dict/None path_map (including `None` + non-Literal ⇒ empty targets), `branch` in the conditional-edge snapshot, non-`str` `Hashable` path_map key, errors, invalid `start_key`, empty-node graph (X-5), plain callable `.name` not used, non-callable Runnable rejection (X-6), chain, snapshot, no user execution, signature parity, minimal graph, conditional START entrypoint, multi-source END / multi-target retention, `__parent__` retention, `validate(interrupt=["missing"])`
- [X] T038 Add `harness/verification/B6F1/manual-verification.md` with five sections and EV-1a / EV-1b / EV-1c acknowledgement
- [X] T039 [P] Append B6F1 → B7F2 downstream wiring entry in `harness/features/B7F2_compile编译.md` (B7F2 consumes `_build_spec()`; filters only **single-source** `END`; retains multi-source **V-16 形态**（`END` / 目标数 ≠ 1）and `__parent__` so `GraphSpec` V-16 / **B9F1 保留名检查** can fail; translates `_BuilderSpec.conditional_edges` to the frozen plain mapping `dict[str, tuple[dict[str, Any], ...]]` (inner `{"branch": str, "path": Callable, "path_map": dict[Hashable, str] | None, "targets": tuple[str, ...], "route_channels": tuple[str, ...]}`; `branch` comes from `_ConditionalEdgeSpec.branch`, MUST NOT re-infer) and stores it on the `CompiledGraph` private field (e.g. `_conditional_edges`); also retains the full `_BuilderSpec` (at least `node_records`) on `CompiledGraph` for B8F3; does not fill `GraphSpec.conditional_edges` until B8F1; only wiring; do not implement compile)
- [X] T040 [P] Append B6F1 → B8F1 downstream wiring entry in `harness/features/B8F1_条件边路由与fresh读.md` (B8F1 is L2: reads the B7F2-retained **plain mapping** and fills `GraphSpec.conditional_edges`, relaxing V-8; MUST NOT import `_stategraph` / `_ConditionalEdgeSpec`; MUST NOT re-normalize `path_map`; only wiring; do not implement routing)
- [X] T041 [P] Append B6F1 → B8F3 downstream wiring entry in `harness/features/B8F3_节点别名与context通道.md` (B8F3 reads `_NodeRecord.alias` from the B7F2-retained full `_BuilderSpec` / `node_records`; MUST NOT require re-declaration; only wiring; do not implement alias semantics)
- [X] T045 Update `specs/b6f1-stategraph-builder/checklists/requirements.md` validation notes if any task-level clarification changes spec coverage (otherwise leave unchanged)
- [X] T046 Add **constitutional signature compatibility** test in `tests/facade/test_stategraph_builder.py`: compare against `langgraph 1.2.11` (upstream absent ⇒ skip) **only** the frozen public surface required by SC-006 — ① method names exist; ② `__init__` / `add_node` / `add_edge` / `add_conditional_edges` / `validate` 的**必填位置参数名与顺序**一致; ③ `add_edge` / `add_conditional_edges` / `validate` 的必填参数个数一致; ④ 返回语义一致（成功调用返回同一 builder / `Self`，与 D-55 / T024 的断言相互印证）. **MUST NOT** compare complete keyword-only sets, defaults, or annotations; freegraph-only `alias` and missing upstream `input_schema` / `retry_policy` / `**kwargs` MUST be explicitly whitelisted; attach `state.py` line references
- [X] T047 [US1] Add minimal graph test in `tests/facade/test_stategraph_builder.py`: `StateGraph(State)` + `add_node("a", node_a)` + `add_node("b", node_b)` + `add_edge(START,"a")` + `add_edge("a","b")` + `add_edge("b",END)`; assert `validate()` succeeds and `_build_spec()` has 2 nodes / 3 static edges; no user function (`node_a` / `node_b`) is called
- [X] T048 [P] Append B6F1 → B7F3 downstream wiring entry in `harness/features/B7F3_invoke返回完整状态.md`: minimal graph runtime assertion for G22 scenario② (only wiring; do not implement `invoke`)
- [X] T049 [P] Update `harness/verification/README.md` "当前已有记录" table with B6F1 row after T037–T038 complete
- [X] T042 Run full regression `.venv/bin/python -m pytest -q`, coverage on `src/freegraph/_stategraph.py`, and gates G17 / G18 / G19 / G21 / G24 / G25 / G26 / G27 / G29 / G30; record actual outputs in `harness/verification/B6F1/manual-verification.md`; record that G22 scenario② is deferred to B7F3 (H-7 · 裁定 11). **MUST run after T046 / T047** so the new tests are included
- [X] T043 Run `harness/verification/B6F1/acceptance.py` and the quickstart scenarios; record outputs in `harness/verification/B6F1/manual-verification.md`. **MUST run after T042**
- [X] T044 Verify `harness/demo/target.py` diff is empty, public API snapshot is unchanged, and `harness/demo/graph_core.py` still exits 2 (compile / invoke not ready); record in manual verification; record G22 scenario② deferred to B7F3. **MUST run after T042**
- [X] T050 **【阻断合入】** Verify bidirectional traceability: every FR / SC has at least one task; every task maps to at least one FR / SC or an explicit process obligation (原则 V / D-1…D-3 / H-7). Fill the reverse appendix below; missing entries MUST be fixed before merge.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: starts immediately.
- **Foundational (Phase 2)**: depends on Setup; blocks all user stories.
- **US1–US6 (Phases 3–8)**: depend on Foundational. US1 and US2 share the builder test file, so run US1 then US2 if single-threaded; US3 uses a separate validation test file and can run in parallel with US2 after Foundational.
- **Polish (Phase 9)**: depends on all desired user stories; T032b–T041 / T045–T049 may run after their target files exist (T046/T047 after US1 tests; T048/T049 after T037–T038); **T042–T044 are final verification and MUST run after T032b–T041 and T046–T049**; T050 MUST run after all tasks are written and before merge.

### User Story Dependencies

- **US1 (P1)**: after Foundational; no dependency on other stories.
- **US2 (P1)**: after Foundational; independent test surface, but shares `test_stategraph_builder.py` with US1 (sequence those two files).
- **US3 (P2)**: after Foundational; independent via `test_stategraph_validation.py`.
- **US4 (P2)**: after Foundational; independent via chainability assertions.
- **US5 (P2)**: after US1 + US2 (needs registration + base snapshot + route channels for T027/T029); independent via `test_stategraph_spec.py`.
- **US6 (P3)**: after US1 / US2 (needs all build paths); independent via call counters.

### Within Each User Story

- Tests first, then implementation.
- Registration / snapshot implementation before downstream assertions.
- Story complete and green before moving to the next priority in single-threaded mode.

### Parallel Opportunities

- T002 / T003 in Setup.
- T017 (validation tests) can run in parallel with `test_stategraph_builder.py` work because it uses `test_stategraph_validation.py`; T020 / T021 share that file and follow T017 if editing simultaneously.
- T026 / T027 in `test_stategraph_spec.py` can run in parallel with builder test tasks.
- T032b–T041 / T048 / T049 in Polish touch different files and can run in parallel; T046 / T047 share `test_stategraph_builder.py` with T013 / T014 / T016 / T030, so sequence them; T050 is a final blocking traceability check.
- T042–T044 are sequential final verification and MUST run after T046–T049.

---

## Parallel Example: US2 / US3 / US5

```bash
# After Foundational:
Task: "T016 [US2] list/dict/None path_map tests in tests/facade/test_stategraph_builder.py"
Task: "T017 [US2] invalid path_map / branch-name tests in tests/facade/test_stategraph_validation.py"
Task: "T026 [US5] GraphSpec compatibility test in tests/facade/test_stategraph_spec.py"
```

> T016 / T017 / T026 are in different files and can run in parallel. T020 / T021 share
> `test_stategraph_validation.py` with T017, so sequence them if editing simultaneously.

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Setup + Foundational.
2. Complete US1: target.py build segment + basic `_build_spec`.
3. Stop and validate US1 independently.
4. This is the smallest demoable slice: the target build code runs unchanged.

### Incremental Delivery

1. Setup + Foundational（含 T032a：与 T008–T010 同批收窄 facade 测试，Phase 2 结束必须绿）。
2. US1 → target build works.
3. US2 → path_map list/dict works.
4. US3 → build-time errors are localized.
5. US4 → chaining works.
6. US5 → snapshot is B7F2-consumable.
7. US6 → build purity is proven.
8. Polish → facade tests / docs / differential / acceptance / manual verification / signature parity / minimal graph / G22 wiring / verification README.

### Parallel Team Strategy

- Team completes Setup + Foundational together.
- After Foundational:
  - Developer A: US1 then US2 (`test_stategraph_builder.py`).
  - Developer B: US3 (`test_stategraph_validation.py`).
  - Developer C: US5 (`test_stategraph_spec.py`).
- US4 / US6 can follow once US1 / US2 are stable.
- Polish tasks T032b–T041 / T046 / T048 / T049 can be split by file; T047 follows the builder test file.

---

## SC → Tasks 追溯（判据级）

| SC | 判定任务 | 说明 |
|---|---|---|
| SC-001 | T013 · T037 | target 建图段原样执行 + acceptance 覆盖 |
| SC-002 | T016 · T037 · T035 | list / dict `path_map` + 差分 D-50 / D-51 / D-56 / D-60 |
| SC-003 | T020 · T021 · T017 · T037 | 3 类核心错误 + BV 矩阵（T017 负责 BV-8/9）+ acceptance |
| SC-004 | T024 | 链式同一对象 |
| SC-005 | T011 · T028 · T029 · T026 · T027 | `_BuilderSpec` 形状 / 副本 / GraphSpec 适配 |
| SC-006 | T035 · T036 · T046 | 差分 D-50…D-73 + 宪法签名 parity（T046 只比较必填位置参数 / 顺序 / 返回语义）；D-74 已迁移到 B8F3 D-142 |
| SC-007 | T030 · T037 | 用户函数调用计数 0 + 返回形态接受 + acceptance |
| SC-008 | T042 | 依赖 / env / I-O 门禁 |
| SC-009 | T044 | `target.py` diff 为空 |
| SC-010 | T032a · T032b · T033 · T044 | 公开 API 快照 / 未接线测试收窄 / docstring |
| SC-011 | T027 | 顺序 / 结构等价 / 用户输入变更隔离 |
| SC-012 | T020 · T021 · T037 | 校验幂等 / 失败不改状态 / 消息可定位 |
| SC-013 | T012 · T021 · T032b · T033 · T044 | 静态断点透传（不新增 / 不丢弃；`validate(interrupt=...)` 按上游校验；compile 签名快照由 T044 复核） |
| SC-014 | T014 | `defer` / `metadata` 记录（`alias` 已随 C25 正式作废，不再作为 SC-014 判据） |
| SC-015 | T013 · T047 · T037 | 最小图可构造 + acceptance |

> 每条 SC 至少挂一条**测试 / 可执行判定**任务；实现任务不单独充当判据覆盖。

---

## 附录 · 任务 → FR / SC 反向追溯

> 宪法 v1.11.0 原则 VI：追溯表 MUST 双向（spec → tasks 与 tasks → spec 各自齐备）。
> 本表与上方「SC → Tasks」表共同构成双向追溯；T050 负责校验本表完整性。

| 任务 | 对应 FR / SC | 任务 | 对应 FR / SC |
|---|---|---|---|
| T001 | 过程义务：基线确认（不构成 SC-008 / SC-009 判据） | T002 | 过程义务：测试夹具（判据由 T013 / T016 / T020 / T026 / T027 承担） |
| T003 | 过程义务：测试骨架 | T004 | FR-007 |
| T005 | FR-001 | T006 | FR-004 |
| T007 | FR-004 / FR-018 | T008 | FR-002 / FR-005 / FR-009 / FR-010 / FR-011 / FR-018 |
| T009 | FR-003 / FR-005 / FR-016 | T010 | FR-004 / FR-005 / FR-009 / FR-018 |
| T011 | FR-007 / FR-016 / FR-017 | T012 | FR-019 / FR-021 |
| T013 | FR-015 / SC-001 / SC-015 | T014 | FR-010 / FR-011 / SC-014 |
| T015 | SC-001 / SC-015 | T016 | FR-004 / FR-007 / FR-020 / SC-002 |
| T017 | FR-004 / SC-003 | T018 | FR-007 / FR-020 |
| T019 | FR-004 | T020 | FR-006 / SC-003 |
| T021 | FR-006 / FR-017 / FR-019 / FR-021 / SC-012 | T022 | FR-006 |
| T023 | FR-006 / FR-017 / FR-019 | T024 | SC-004 |
| T025 | FR-002 / FR-003 / FR-004 / FR-019 | T026 | FR-007 / SC-005 |
| T027 | FR-007 / FR-016 / FR-018 / SC-011 | T028 | FR-007 |
| T029 | FR-007 | T030 | FR-008 / FR-009 / SC-007 |
| T031 | FR-008 | T032a | FR-001 / FR-014 / SC-010 |
| T032b | FR-012 / FR-021 / SC-010 / SC-013 | T033 | FR-014 / SC-010 |
| T034 | FR-014 / SC-010 | T035 | SC-006 |
| T036 | SC-006 | T037 | SC-001…SC-015 |
| T038 | 原则 V / EV-1 | T039 | D-1 |
| T040 | D-2 | T041 | D-3 / FR-010 |
| T042 | FR-013 / SC-008 / SC-010 / SC-013 | T043 | SC-001…SC-015 |
| T044 | FR-015 / SC-009 / SC-010 / SC-013 | T045 | 规格维护 |
| T046 | SC-006 | T047 | SC-015 / FR-005 |
| T048 | H-7 | T049 | 原则 V |
| T050 | 原则 VI（双向追溯） | — | — |

---

## Notes

- `[P]` 仅用于不同文件且无未完成依赖的任务；同一文件的任务必须顺序执行。
- 本 feature **不实现** `compile()` / `invoke()` / `stream()` / `get_graph()` / `draw_mermaid()`。
- `harness/demo/target.py` 是只读基准；任何任务都不得修改它。
- `graph_core.py` 在本 feature 后仍退出码 2（compile / invoke 未就绪）；**不是**失败。
- 门禁 3 / 4 / 5 的端到端部分按 plan 的 EV-1a / EV-1b / EV-1c 承接 B7F2 / B7F3 / B8F1 / B22F1 / B23F1 / B25F1；本 feature 不写永久红 CI。
- G22「场景②」的运行期断言不在本 feature 执行；由 B7F3 点亮（H-7 · 裁定 11）。T042 / T044 须记录「未点亮，承接 B7F3」。
- 差分场景编号为 **D-50…D-73**（D-74 已迁移到 B8F3 D-142）；plan 的设计决策编号为 **DD-01…DD-15**，两者 MUST NOT 混用。
- 提交前必须完成 **T046–T049 → T042–T044** 的顺序，并把实际输出写入人工验证记录；T050 最后完成。
- T032a 属 Foundational（与 T008–T010 同批完成，Phase 2 结束必须绿）；T032b 属 Polish。
