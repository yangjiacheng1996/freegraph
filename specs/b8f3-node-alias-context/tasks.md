# Tasks: B8F3 · `context` 独立通道 + `RunConfig` 运行期接线（C25 已正式作废）

**Input**: Design documents from `/specs/b8f3-node-alias-context/`

**Prerequisites**: `plan.md`（required）· `spec.md`（required）· `research.md` ·
`data-model.md` · `contracts/context-channel-contract.md` ·
`contracts/alias-removal-contract.md` · `contracts/upstream-parity.md` · `quickstart.md`

**Tests**: **必做** —— 本 feature 的 SC-001…SC-012、D-137…D-144、`graph_core.py` C21 硬断言、
C25 正式作废判据均为判据级要求。每个 user story 先写测试、先失败，再实现。

**Organization**: 按 user story 分组。US1（P1）是 MVP；US2（P2）依赖 US1；
US3（P2，C25 移除）**不依赖** context 载体，可在 Setup 后与 US1 并行；US4（P3）依赖 US1。
> ⚠️ `graph_core.py` / `harness/demo/README.md` 同时被 US1（C21 硬断言）与 US3（C25 清理）修改
> ⇒ **US1 的 T015 必须在 US3 的 T022 之前完成**（同一文件串行）。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、不依赖未完成任务）
- **[Story]**: `US1` / `US2` / `US3` / `US4`（仅 user story 阶段）
- 每个任务都含**精确文件路径**

## Path Conventions

- 单项目：`src/freegraph/` + `tests/` + `harness/`（仓库根）
- 文档 / 契约：`specs/b8f3-node-alias-context/` · `harness/reports/` · `harness/proposals/`

---

## 追溯表（FR → 任务）

| FR | 任务 |
|---|---|
| FR-001 / FR-002 | T008 / T011 / T012 / T013 / T014 / T017 / T018 |
| FR-003 | T011 / T012 / T013 / T014 / T017 / T018 |
| FR-004 / FR-005 | T011 / T012 / T013 / T014 / T016 |
| FR-006 | T026 / T027 |
| FR-007 | T017 / T018 |
| FR-008 | T009 / T010 / T011 / T012 / T018 |
| FR-009 | T011 / T012 / T017 / T018 / T040 |
| FR-010 | T008 / T009 / T010 / T040 |
| FR-011 / FR-012 | T019 / T020 |
| FR-013 / FR-014 | T019 / T020 / T021 / T022 / T023 / T024 / T031 / T032 / T033 / T034 |
| FR-015 | T022 / T023 |
| FR-016 | T020 / T022 / T023 / T025 / T027 / T040 |
| FR-017 | T004 / T040 |
| FR-018 | T008 / T009 / T010 / T040 |
| FR-019 | T012 / T013 / T014 / T016 / T026 / T040 |
| FR-020 | T015 / T023 / T036 |
| FR-021 | T011 / T017 / T018 |
| FR-022 | T005 / T006 / T007 / T030 / T031 / T032 / T033 / T034 / T039 / T040 |

**SC 追溯表**

| SC | 任务 |
|---|---|
| SC-001 | T011 / T012 / T013 / T014 / T016 |
| SC-002 | T017 / T018 |
| SC-003 | T017 / T018 |
| SC-004 | T019 / T020 / T021 / T022 / T023 / T024 / T025 |
| SC-005 | T026 / T027 |
| SC-006 | T012 / T013 / T016 / T040 |
| SC-007 | T028 / T029 |
| SC-008 | T004 / T040 |
| SC-009 | T022 / T023 / T036 / T037 |
| SC-010 | T015 / T023 / T036 |
| SC-011 | T037 / T039 |
| SC-012 | T005 / T006 / T007 / T024 / T030 / T031 / T032 / T033 / T034 / T039 / T040 |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 记录基线、确认上游锚点、**先完成 C25 正式作废的治理层修订**，再进入代码。

- [X] T001 Create `harness/verification/B8F3/` directory and `harness/verification/B8F3/manual-verification.md` with the five-section skeleton (环境 / 步骤 / 实际输出 / 结论 / 遗留问题) and a `§1.1 基线` placeholder.
- [X] T002 Run the real full baseline `.venv/bin/python -m pytest -q tests/` and record passed / skipped / failed / elapsed in `harness/verification/B8F3/manual-verification.md` §1.1 (2026-11-20 collect-only = 1742; do not substitute the collect count for the real run).
- [X] T003 [P] Re-check upstream anchors and versions `langgraph 1.2.11` / `langchain-core 1.7.6`: `langgraph/graph/state.py:667-682` · `pregel/main.py:3783-3843` · `runtime.py:198` · `pregel/_io.py:118` · `types.py:637-646`; update `specs/b8f3-node-alias-context/research.md` §0.1 only if a line number drifted.
- [X] T004 [P] Confirm zero dependency and zero read-only-baseline changes: run `git diff --exit-code -- harness/demo/target.py pyproject.toml`; report the result to T002 / T037 (no manual-file edit in this task).
- [X] T005 Formal C25 retirement: update `.specify/memory/constitution.md` principle VII to the active list **C1–C24 + C26–C27** (C25 retired, number not reused; C26/C27 not renumbered), bump the header revision summary + footer to **1.16.0 (MINOR)**, append the v1.16.0 entry to `.specify/memory/constitution-changelog.md` (what / why / affected principles & features / migration), and sync the same principle-VII text + version in `harness/prompts/init_constitution.md`.
- [X] T006 [P] Update `harness/reports/Q8-图运行时最小契约.md`: mark the C25 row as **officially retired** (tombstone, number not reused), change the active-list references to **C1–C24 + C26–C27**, and add the 2026-11-20 status note; keep the historical C25 text.
- [X] T007 [P] Update `harness/proposals/立项书.md`: §5.2 B8F3 row to **C21/C22 only** (C25 retired; 580/3 is a historical estimate and does not include the C25 removal rework), §5.3 C25 row to retired, §9.2 `graph_core.py` coverage **C1–C24** and remove C25 from the soft-assertion list, §4 architecture `B8(别名)` → `B8(context)`, and fix the §6.3 M2 timing sentence to「fixed script at 21st/63 days; M2 overall at 22nd/66 days」.

**Checkpoint**: C25 is formally retired in the constitution / Q8 / 立项书 before any code change; active contract list is C1–C24 + C26–C27. **治理层修订（T005–T007、T031–T034）已落地但尚未追认**：按宪法 v1.8.0「未追认前 MUST NOT 合入」，追认文字由 T037 落 `harness/verification/B8F3/manual-verification.md`，T039 守卫；在 T037 完成前保持「已完成待追认」状态。

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: context 的**单一运行期载体**与两条运行入口的绑定。US1 / US2 / US4 依赖本阶段；
US3 不依赖本阶段，可在 Setup 后并行开始。

**⚠️ CRITICAL**: 本阶段完成前，US1 / US2 / US4 不开始。

- [X] T008 [P] Create `src/freegraph/runtime/_context.py` (L2 private · `__all__: list[str] = []` · 署名头 · module docstring is first statement): define `_CONTEXT: ContextVar[Any]` (default `None`), `bind_context(context)` (contextmanager with token reset in `finally`), `get_context()`, `_ContextState(dict)` with a **read-only `.context` property** and no `"context"` key, `with_context(view)` (returns the exact input `dict` when context is `None`), and `with_context_arg(arg)` (wraps only `dict` args when context is non-`None`; non-`dict` unchanged). The mapping content remains mutable; only `.context` is read-only.
- [X] T009 [P] Bind context in `src/freegraph/runtime/superstep.py` `run_graph` (around `:2178-2260` / `with bind_run(table):` at `:2244`): enter `bind_context(run_config.context)` for both `_first_graph` and `_resume_graph`; reset in `finally`; MUST NOT change any `run_graph` / `run_super_step` / `run_super_steps` signature.
- [X] T010 [P] Bind context in `src/freegraph/runtime/_stream.py` `StreamSession` (`__enter__` around `:74-118`, `__exit__` around `:119-133`): after `resolve_config(self._raw_config)`, enter `bind_context(run_config.context)` and reset the token in `finally`; MUST NOT mix C21 `context` into `_stream_context.py`'s stream writer / run-id contextvars.

**Checkpoint**: context 载体已绑定；节点视图由 US1 的 T013/T014 接线（本阶段不承诺节点已能读到 `.context`）。

---

## Phase 3: User Story 1 - 运行时上下文独立传递 (Priority: P1) MVP

**Goal**: 节点通过 `getattr(state, "context", None)` 读到 `RunConfig.context`；`invoke` /
`values` 不含 context；`context is None` 时节点入参仍是精确 `dict`。

**Independent Test**: `RunConfig(context={"user":"u1"})` + 单节点图；节点读到值；
`invoke` 终态与 `values` payload 均无 `"context"`；`context=None` 时 `type(state) is dict`。

### Tests for User Story 1

- [X] T011 [P] [US1] Write `tests/facade/test_context_channel.py` (先写、先失败): `invoke` node reads context; `invoke` final key set == schema and has no `"context"`; `stream(..., stream_mode="values")` payloads have no `"context"`; `context=None` ⇒ `getattr(state, "context", None) is None`; `context={}` / `0` / `""` ⇒ non-None path; `RunConfig` mapping form `{"context": ...}` works; `invoke(..., context=...)` / `stream(..., context=...)` raise `TypeError`; context object identity is preserved.
- [X] T012 [P] [US1] Write `tests/runtime/test_context_channel.py` (先写、先失败): no context ⇒ `type(state) is dict`; context non-None ⇒ `isinstance(state, dict)` and `type(state) is not dict`; `dict(state)` equals the sparse state; no `"context"` key; `.context` is read-only but the mapping remains mutable; unknown attrs raise `AttributeError`; `"context" not in spec.channels` / `state.channels`; `Send.arg` dict is wrapped, non-dict is unchanged; `Command.goto` target gets a standard context-bearing input; two consecutive `run_graph` / `StreamSession` runs do not leak context; `bind_context(None)` restores `None`.

### Implementation for User Story 1

- [X] T013 [US1] Modify `src/freegraph/runtime/superstep.py` `_node_input` (`:784-800`) to return `with_context(read_channels(subset))`; keep the sparse key set / order / values and C4 semantics unchanged; MUST NOT wrap the route view.
- [X] T014 [US1] Modify `src/freegraph/runtime/superstep.py` `_run_round` fan-out preparation (`:1328-1340`) to use `with_context_arg(task.arg)` for fan-out records; `Send.arg` non-`dict` MUST remain unchanged; standard tasks continue through `_node_input`.
- [X] T015 [US1] In `harness/demo/graph_core.py` upgrade the C21 `context` soft assertion to a hard assertion (`soft(...)` ⇒ `check(...)` / `eq(...)`) and update the C21 row in `harness/demo/README.md` so C21 is no longer listed as a soft assertion. ⚠️ Must finish before T022 (same files).
- [X] T016 [US1] Run `.venv/bin/python -m pytest tests/facade/test_context_channel.py tests/runtime/test_context_channel.py tests/runtime/test_superstep_contract.py tests/runtime/test_conditional_edges.py -q`; record the real output in `harness/verification/B8F3/manual-verification.md` §2.1. Confirm C4 / I-1 and route-view-no-context stay green.

**Checkpoint**: US1 独立可验收 —— context 可读、状态无污染、无 context 时精确 `dict`、fan-out 边界明确。

---

## Phase 4: User Story 2 - `context` 不被塞进 `configurable` (Priority: P2)

**Goal**: `RunConfig` 四核心字段与九字段面不变；`configurable` 独立；节点侧 context view 没有
freegraph 注入的 `"configurable"` 键；只传 `configurable={"context": ...}` 不会被当作 context。

**Independent Test**: 构造 `RunConfig(thread_id=..., context=..., metadata=..., tags=...)`；
四字段值正确；九字段名/顺序不变；`configurable` 不包含 `context`；节点 view 无注入的
`configurable`；`configurable={"context": ...}` 时 `context` 仍为 `None`。

### Tests & Verification for User Story 2

- [X] T017 [US2] Append US2 cases to `tests/facade/test_context_channel.py` (先写、先失败): the exact `RunConfig` field set is still nine fields with the same names/order (`thread_id` / `context` / `metadata` / `tags` / `configurable` / `max_concurrency` / `recursion_limit` / `run_name` / `run_id`); four core fields readable and `tags` is `tuple`; `configurable` is an independent mapping and does not contain `context`; node-side context view has no injected `"configurable"` key; `thread_id` / `metadata` / `tags` are not injected into state or context; only `configurable={"context": ...}` ⇒ `context is None`; `StateGraph(context_schema=...)` remains accepted but unused. Checkpoint persistence is a B14F1 boundary: assert no `context` key in the existing snapshot fixture if one is available, otherwise record「checkpoint 持久化归 B14F1」in the manual record.
- [X] T018 [US2] Run `.venv/bin/python -m pytest tests/facade/test_context_channel.py -k "RunConfig or configurable or Configurable" -q`; record the real output in `harness/verification/B8F3/manual-verification.md` §2.2. If a failure is in the view construction, adjust only `src/freegraph/runtime/_context.py` (no second carrier).

**Checkpoint**: US2 独立可验收 —— C21 / C22 职责分离；九字段面不变；`configurable` 不承载 context。

---

## Phase 5: User Story 3 - C25 正式作废与 alias 彻底移除 (Priority: P2)

**Goal**: `add_node` 无 `alias`；`_NodeRecord` / `_BuilderSpec` 无 `alias`；`add_node(alias=...)`
抛 `TypeError`；C25 用例 / 软断言 / active 契约承诺全部移除（历史文字保留 + 墓碑）。

**Independent Test**: `add_node("agent", fn, alias="model")` ⇒ `TypeError`；`_NodeRecord` 无
`alias`；`stream()` / `get_graph()` / `PregelTask.name` 只用内部名；demo / README / 测试无 C25
active 引用。

**Note**: 本 story 不依赖 Phase 2；可在 Setup 后直接开始，与 US1 并行（但 T015 必须先于 T022）。

### Tests & Implementation for User Story 3

- [X] T019 [US3] Update `tests/facade/test_stategraph_builder.py` (`:61-77`) **first** (先写、先失败): `pytest.raises(TypeError, match="alias")` for `add_node(..., alias="model")`; `_NodeRecord` has no `alias` field (`dataclasses.fields` / `hasattr` false); `_BuilderSpec` has no `alias` field; keep `defer` / `metadata` / single-callable assertions.
- [X] T020 [US3] Remove the `alias` field from `_NodeRecord` and the keyword-only `alias` parameter from `StateGraph.add_node` in `src/freegraph/_stategraph.py` (`:83-89` / `:834-890`); remove the `alias=alias` constructor argument; keep `defer` / `metadata` / `destinations` / single-callable behavior unchanged.
- [X] T021 [P] [US3] Remove the D-74 alias scenario and its `_fg_alias` / `_up_alias` helpers from `tests/differential/parity_probe.py` (`:4139-4162` / `:4220`); do not leave a dangling `BuilderScenario` entry.
- [X] T022 [US3] Remove the alias header bullet at `harness/demo/graph_core.py:31`, `case_node_alias`, and its `main` registration from `harness/demo/graph_core.py`; delete the C25 soft-assertion rows / A10 row and update the `当前一处` wording in `harness/demo/README.md`; change the core coverage description `C1–C25` to `C1–C24` in `harness/demo/README.md` and `harness/demo/acceptance.py:70`. ⚠️ Depends on T015 (same files).
- [X] T023 [US3] Update `tests/runtime/test_acceptance_script.py` (`:59-65`): replace the "README keeps C25" assertion with "README no longer contains C25"; update/remove the `"当前一处"` assertion to match the new README; add an assertion that `harness/demo/graph_core.py`'s C21 `case_run_config_and_context` contains no `soft(` and uses `check(` / `eq(`. ⚠️ Depends on T015 / T022.
- [X] T024 [US3] Update `src/freegraph/contracts/graph.py:152` `Node` docstring from `C13 / C25` to `C13` and note that `Node.name` is a **display name**, not the retired C25 alias; update `README.md:114` `StateGraph` row to remove `alias=None` and the C25 mention while keeping the rest of the compatibility matrix intact.
- [X] T025 [US3] Run `.venv/bin/python -m pytest tests/facade/test_stategraph_builder.py tests/runtime/test_acceptance_script.py -q`; record the real output in `harness/verification/B8F3/manual-verification.md` §2.3. Confirm no C25 active references remain with `rg -n "case_node_alias|C25 节点别名|alias=None" src tests harness/demo README.md`.

**Checkpoint**: US3 独立可验收 —— alias 签名 / 字段 / demo / README / 测试全部移除；C25 仅保留历史墓碑。

---

## Phase 6: User Story 4 - 路由与流式消费不受影响 (Priority: P3)

**Goal**: context 接线不改变条件边 fresh 视图、`path_map` 查表、`stream()` 节点名口径、
`get_graph()` 节点名；路由第二参原始 config 可携带 context。

**Independent Test**: 条件边路由 fresh 视图无 `context` 键 / `.context`；路由第二参
`RunConfig(context=...)` 可读；`stream_mode="updates"` 键 = 内部节点名；`get_graph()` 节点
`id` / `name` = 内部节点名。

### Tests & Verification for User Story 4

- [X] T026 [US4] Append US4 cases to `tests/runtime/test_context_channel.py` (先写、先失败): route fresh view is a plain `dict` with no `context` / no `.context`; a dual-param route `f(state, config)` can read `config.context` when the raw config is `RunConfig`; `path_map` lookup still uses internal node names; `stream(..., stream_mode="updates")` payload keys are internal names; `get_graph()` node `id` / `name` are internal names; `PregelTask.name` is internal.
- [X] T027 [US4] Run `.venv/bin/python -m pytest tests/runtime/test_context_channel.py -k "route or Route or stream or graph" tests/runtime/test_conditional_edges.py -q`; record the real output in `harness/verification/B8F3/manual-verification.md` §2.4.

**Checkpoint**: US4 独立可验收 —— context 不进入路由 fresh 视图；stream / graph export 命名口径不变。

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 差分、其余契约修订、下游接线、验收 / 人工记录、守卫测试、全量门禁。

- [X] T028 [P] Add D-137…D-144 to `tests/differential/parity_probe.py` as a new context group (after the existing stream group): D-137 context not in final state; D-138 node reads context (DIFF X-1); D-139 context vs configurable; D-140 RunConfig four fields (DIFF X-2); D-141 no-alias graph naming / route; D-142 `add_node(alias=...)` ⇒ `TypeError` vs upstream silent ignore (STRICTER X-3); D-143 stream / graph export internal names; D-144 route view no context. Upstream absent ⇒ skip; non-SAME rows MUST have a non-empty note.
- [X] T029 Run `.venv/bin/python harness/scripts/diff_parity.py -k "context D-"` and `.venv/bin/python -m pytest tests/differential/test_parity_probe.py -q -k "context"`; record the judgment distribution `SAME 5 / DIFF 2 / STRICTER 1` in `harness/verification/B8F3/manual-verification.md` §3.
- [X] T030 [P] Retro-revise T-1: add the C4 note to `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §I-1 and the relevant docstring in `tests/runtime/test_superstep_contract.py`: no context ⇒ exact `dict`; context non-None ⇒ **带只读 `.context` 的 `dict` 子类，映射内容仍可变**; original C4 text unchanged.
- [X] T031 [P] Retro-revise T-3 / R-2: update `specs/b6f1-stategraph-builder/spec.md`, `plan.md`, `research.md`, `quickstart.md`, `contracts/builder-contract.md`, `contracts/upstream-parity.md`, `checklists/requirements.md`, and `data-model.md` to remove `alias` from `add_node` / `_NodeRecord`, withdraw B6F1 D-3, and update FR-010 / 裁定 7 / SC-014 / P-02b / D-74 / X-1 notes; mark D-74 as migrated to B8F3 D-142 and adjust the active differential range to D-50…D-73.
- [X] T032 [P] Retro-revise T-4 / R-3: update `specs/b2f2-public-api-facade/spec.md`, `contracts/facade-api.md`, `contracts/public-api-snapshot.txt`, `data-model.md`, `research.md`, and `checklists/requirements.md` to remove `alias` from the facade `add_node` signature and compatibility matrix.
- [X] T033 [P] Retro-revise T-5 / R-4: update `specs/b22f1-get-graph-mermaid/spec.md`, `contracts/graph-export-contract.md`, and `data-model.md` to remove the「别名归 B8F3 / 待解析」notes while keeping `name == id` (internal name) unchanged.
- [X] T034 [P] Retro-revise T-7 / R-5: update the alias handover notes in `specs/b7f2-compile/spec.md` (D-3), `specs/b7f2-compile/plan.md` (D-3), `specs/b7f2-compile/contracts/compile-contract.md` (B8F3 read row), and `specs/b8f2-stream-modes/spec.md` (D-1) — withdraw / shrink to「stream 只用内部节点名」; add a B8F1 D-2 note in `specs/b8f1-conditional-edges-fresh-read/spec.md` that alias is retired and `path_map` still uses internal names. B6F1 D-3 is already covered by T031.
- [X] T035 [P] Wire downstream D-1…D-4 into `harness/features/B14F1_Checkpointer协议与MemorySaver.md`, `harness/features/B15F1_SqliteSaver与状态历史.md`, `harness/features/B16F1_update_state与时间旅行.md`, `harness/features/B18F1_Span数据类生产.md`, and `harness/features/B19F1_TraceSink与current_span.md`: context is not persisted / not restored (B14F1 / B15F1 / B16F1); C21 context is not the trace span `context` field (B18F1 / B19F1); M3 features MUST NOT fall back to `configurable` or reintroduce alias. Only wire, do not implement next features.
- [X] T036 Run `.venv/bin/python harness/demo/graph_core.py` and `.venv/bin/python harness/demo/acceptance.py`; record exit codes and the C21 hard-assertion result in `harness/verification/B8F3/manual-verification.md` §4. Confirm no C25 active reference / `case_node_alias` remains.
- [X] T037 Write the final `harness/verification/B8F3/manual-verification.md`: five sections; `context` real output; `RunConfig` four core + nine-field check; C25 formal retirement (`TypeError` / no alias field / no C25 active reference / constitution 1.16.0 + changelog evidence); differential D-137…D-144; zero-outbound evidence (framework outbound = 0); T-1…T-7 acknowledgment text + initiator confirmation + date.
- [X] T038 Create `tests/contracts/test_c25_retirement.py`: assert `add_node` has no `alias` parameter; `_NodeRecord` / `_BuilderSpec` have no `alias`; `harness/reports/Q8-图运行时最小契约.md` and `harness/proposals/立项书.md` mark C25 as retired (not active); `harness/demo/README.md` / `harness/demo/acceptance.py` use `C1–C24`; `tests/differential/parity_probe.py` has no D-74 alias scenario. This is the formal C25-retirement guard.
- [X] T039 Create `tests/runtime/test_context_manual_record_guard.py`: assert `harness/verification/B8F3/manual-verification.md` exists, has the five sections, contains non-empty real outputs for context / RunConfig / C25 retirement / D-137…D-144, contains constitution 1.16.0 + changelog evidence, and contains T-1…T-7 acknowledgment + initiator confirmation + date. ⚠️ Must run after T037 so it does not create a permanently red CI.
- [X] T040 Run the final gate: `.venv/bin/python -m pytest -q tests/`; `.venv/bin/python harness/demo/acceptance.py`; verify `freegraph.runtime.__all__` is still 23 symbols; verify no `langchain*` / `langgraph*` / `langsmith*` imports and no environment-variable reads; verify `git diff --exit-code -- harness/demo/target.py pyproject.toml`; run `rg -n "C25 节点别名|case_node_alias|alias=None" src tests harness/demo README.md` and require zero active hits; record final counts in `harness/verification/B8F3/manual-verification.md` §5.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: starts immediately; T001 → T002 (same manual file); T003 / T004 can run in parallel; **T005 → T006 / T007** must complete before code.
- **Phase 2 Foundational**: T008 → T009 / T010; T009 and T010 are different files and may run in parallel after T008. Blocks US1 / US2 / US4. **US3 is independent of Phase 2** and may start after Setup.
- **Phase 3 US1**: depends on Phase 2; T011 / T012 can run in parallel; T013 → T014 (same `superstep.py`); T015 depends on T013/T014; T016 depends on T013/T014 (demo hardening T015 is not a prerequisite for the runtime test run).
- **Phase 4 US2**: depends on US1 (node view); T017 → T018 (same file as T011, so not parallel with T011).
- **Phase 5 US3**: depends on Setup only; T019 → T020 (test-first); T021 is parallel (different file); T022 depends on T015 (same demo files); T023 depends on T022; T024 is independent; T025 depends on T019 / T020 / T022 / T023 / T024.
- **Phase 6 US4**: depends on US1; T026 → T027 (same runtime test file as T012, so not parallel with T012).
- **Phase 7 Polish**: depends on all stories. T028 → T029; T030–T035 are parallel (different files); T036 depends on T022 / T023; T037 depends on T029 / T036 / T030–T035 (T-1…T-7 追认须先完成); T038–T039 depend on T037 (guards after docs/code); T040 runs last.

### User Story Dependencies

- **US1 (P1)**: no other story dependency; MVP.
- **US2 (P2)**: depends on US1 (node context view).
- **US3 (P2)**: independent of context stories; depends only on Setup.
- **US4 (P3)**: depends on US1 (context carrier + node view) and existing B8F1 / B8F2 behavior.

### Within Each User Story

- Tests first; confirm they fail before implementation.
- Same-file tasks MUST NOT be marked [P].
- `graph_core.py` / `harness/demo/README.md` are shared by T015 (US1) and T022 (US3) ⇒ serialize
  **T015 → T022**.
- `tests/facade/test_context_channel.py` is shared by T011 (US1) and T017 (US2) ⇒ serialize.
- `tests/runtime/test_context_channel.py` is shared by T012 (US1) and T026 (US4) ⇒ serialize.
- `tests/differential/parity_probe.py` is shared by T021 (US3) and T028 (Polish) ⇒ serialize.
- `harness/verification/B8F3/manual-verification.md` is shared by T001/T002/T016/T018/T025/T027/T029/T036/T037/T040 ⇒ strictly serial.

---

## Parallel Execution Examples

### Setup + Foundational

```bash
# After T001/T002/T005:
Task: "T003 re-check upstream anchors in specs/b8f3-node-alias-context/research.md"
Task: "T004 confirm target.py / pyproject.toml unchanged"
Task: "T006 update Q8 active list / C25 tombstone"
Task: "T007 update 立项书 §5.2 / §5.3 / §9.2 / §6.3"

# After T008:
Task: "T009 bind context in src/freegraph/runtime/superstep.py"
Task: "T010 bind context in src/freegraph/runtime/_stream.py"
```

### User Story 1

```bash
# Tests in parallel (different files):
Task: "T011 write tests/facade/test_context_channel.py"
Task: "T012 write tests/runtime/test_context_channel.py"

# Then sequentially:
T013 → T014 → T015 → T016
```

### User Story 3 (independent of context carrier)

```bash
# After Setup; can run in parallel with US1:
Task: "T019 write/update tests/facade/test_stategraph_builder.py (test-first)"
Task: "T020 remove alias from src/freegraph/_stategraph.py"
Task: "T021 remove D-74 alias from tests/differential/parity_probe.py"
# T022 must wait for US1 T015 (shared demo files)
```

### Polish contract revisions

```bash
# Different files, after all stories:
Task: "T030 T-1 C4 note"
Task: "T031 T-3 B6F1 docs"
Task: "T032 T-4 B2F2 docs"
Task: "T033 T-5 B22F1 docs"
Task: "T034 T-7 B7F2 / B8F2 / B8F1 notes"
Task: "T035 downstream D-1…D-4 wiring"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 Setup (including formal C25 retirement).
2. Complete Phase 2 Foundational (context carrier + bindings).
3. Complete Phase 3 US1.
4. **STOP and VALIDATE**: context readable; state clean; `context=None` exact `dict`.
5. Demo the C21 hard assertion.

### Incremental Delivery

1. Setup + Foundational → carrier ready.
2. US1 → context independent (MVP).
3. US3 → C25 formally retired / alias removed (can be delivered in parallel with US1).
4. US2 → C21 / C22 boundary verified.
5. US4 → route / stream / graph regression verified.
6. Polish → differential / contract revisions / manual gate / full tests.

### Parallel Team Strategy

- After Setup:
  - Developer A: US1 context node view + graph_core C21.
  - Developer B: US3 C25 retirement / alias removal + builder tests + demo cleanup.
- After US1:
  - Developer C: US2 configurable / RunConfig tests.
  - Developer D: US4 route / stream / graph tests.
- Polish contract revisions can be split across developers (different specs), but
  `manual-verification.md` and `parity_probe.py` remain single-owner.

---

## Notes

- [P] = different files, no dependency on incomplete tasks.
- [Story] label maps each story task to `spec.md` US1 / US2 / US3 / US4.
- Every task includes an exact file path or an exact command with file paths.
- Tests are mandatory for this feature: each story starts with failing tests.
- Do not modify `harness/demo/target.py` (read-only baseline).
- Do not add runtime dependencies, public L2 symbols, or a second context carrier.
- C25 is **formally retired**: number not reused, C26/C27 not renumbered; future alias requires a new contract number (e.g. C28).
- `manual-verification.md` is single-owner and strictly serial.
- After T037, T038/T039 guards must pass; after T040, the feature is ready for manual review.
