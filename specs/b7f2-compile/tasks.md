# Tasks: B7F2 · `compile()` → `CompiledGraph`

> **2026-11-20 后续修订（C25 正式作废）**：B7F2 → B8F3 的 alias 读取（D-3 / T050）已撤回；本文件相关文字保留为历史。


**Input**: Design documents from `specs/b7f2-compile/`

**Prerequisites**: `plan.md` · `spec.md` · `research.md` · `data-model.md` · `contracts/` (`compile-contract.md` / `upstream-parity.md`) · `quickstart.md` · `checklists/requirements.md`

**Tests**: 本任务列表**包含测试任务**。理由：spec 的 SC-001…SC-016 要求**可执行判据**；宪法原则 VI 要求每条 SC 至少挂一条**能判定它**的测试任务；仓库既有 feature 均以 pytest 为实现门禁。

**Organization**: 按 spec 的 6 个用户故事组织（US1…US6），每个故事可独立验证。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 不同文件、无未完成依赖，可并行
- **[Story]**: `[US1]`…`[US6]`，仅用户故事阶段使用
- 每个任务均带明确文件路径

## Path Conventions

- 实现：`src/freegraph/_stategraph.py`（L3 **单文件** · 层注册表冻结 ⇒ **MUST NOT 新建源文件**）
- 测试：`tests/facade/` · `tests/differential/` · `tests/runtime/`
- 验收：`harness/verification/B7F2/`
- 门禁：`harness/scripts/gates/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 建立共享夹具、上游取证脚本、测试骨架；确认基线

- [X] T001 Confirm the current baseline in `tests/facade/test_facade.py` and `tests/runtime/test_acceptance_script.py` (run `.venv/bin/python -m pytest -q`; record today's `TestNotWired` parametrization, `vars(graph)` key set, `NOT_WIRED_PATTERN`, and `graph_core.py` exit-code-2 assertions **before** any change)
- [X] T002 [P] Create shared compile test support in `tests/facade/_compiled_support.py` **with the repository copyright/license header** (minimal valid graph factory, sentinel injection objects, `capture_warnings()` helper, `normalized_summary(compiled)`; reuse `tests/facade/_builder_support.py`'s `State` / node stubs / `CallCounter`)
- [X] T003 [P] Create `harness/verification/B7F2/probe_upstream.py` **with header** reproducing evidence **E-25…E-55** from `research.md` §1 (skips cleanly when `langgraph` is absent; prints one line per E-id)
- [X] T004 Create the three test module skeletons **with headers and module docstrings** in `tests/facade/test_compiled_graph.py`, `tests/facade/test_compile_validation.py`, `tests/facade/test_compile_interrupt.py`; create the `harness/verification/B7F2/` directory

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 编译产物 + `compile()` 的机械主链（**所有用户故事共享**）

**CRITICAL**: 本阶段完成前，任何用户故事都不得开始；**T013 必须与 T005–T012 同批**，否则基线变红。

- [X] T005 Add the private `CompiledGraph` class in `src/freegraph/_stategraph.py`: `__init__` takes **exactly 11 parameters** and stores 3 private fields `_spec` / `_builder_spec` / `_conditional_edges` (names frozen · DD-13) + **8 public instance attributes** `checkpointer` / `store` / `cache` / `debug` / `name` / `transformers` / `interrupt_before_nodes` / `interrupt_after_nodes` (the two interrupt values are taken from `_spec.interrupt_before` / `_spec.interrupt_after`); **MUST be plain instance attributes, NOT `@property`** (otherwise `vars()` cannot see them); `vars(compiled)` key set MUST be exactly those **11** keys (I-1); **rename the L1 protocol import to an alias** in `src/freegraph/_stategraph.py` (`from .contracts import CompiledGraph as CompiledGraphProtocol`) so the new class does **not** shadow it → static-check clean, snapshot unaffected
- [X] T006 Add the 6 capability methods on `CompiledGraph` in `src/freegraph/_stategraph.py` with **signatures byte-identical to the L1 protocol** (`invoke(input, config=None)` · `stream(input, config=None, *, stream_mode="values")` · `get_graph(*, xray=False)` · `get_state(config)` · `get_state_history(config)` · `update_state(config, values, as_node=None)`), each raising builtin `NotImplementedError` whose message names its owning feature (**B7F3 / B8F2 / B22F1 / B15F1 / B15F1 / B16F1**) · zero new exception types。⚠️ **2026-11-20 · B8F2 回溯修订注记（T-3 · 只补注记 · 原描述不改写）**：自 B8F2 起 `stream` 已交付，签名默认值改为 `stream_mode=None`（解析为 `"updates"`）、`config` 放宽为 `RunConfig | Mapping[str, Any] | None`；原 `"values"` 描述保留为历史
- [X] T007 Add `_static_points(value, field_name)` in `src/freegraph/_stategraph.py`: `None` → `()`; `str` / `list` pass through **untouched**; everything else (`tuple` / `set` / `dict` / numeric) ⇒ builtin `TypeError` with the field name, the received type name and `(V-22)` (DR-5 · CV-11 — the **only** self-written check)
- [X] T008 Add `_graph_spec_from(builder_spec, interrupt_before, interrupt_after)` in `src/freegraph/_stategraph.py`: build `GraphSpec` with a **new channels mapping** (`dict(builder_spec.channels)` · same template objects), `dict(builder_spec.nodes)`, and an edges table where **only `str` (single-source) keys** lose `END` targets and a source key whose target tuple becomes empty is **dropped entirely**; `tuple` (multi-source) keys are passed through **verbatim**; `conditional_edges` MUST NOT be passed
- [X] T009 Add `_conditional_mapping(builder_spec)` in `src/freegraph/_stategraph.py`: `dict[str, tuple[dict[str, Any], ...]]` with exactly the 5 keys `branch` / `path` / `path_map` / `targets` / `route_channels`; order = registration order; `branch` copied **verbatim** from `_ConditionalEdgeSpec.branch` (never re-derived); `path_map` / `targets` / `route_channels` copied verbatim
- [X] T010 Implement `StateGraph.compile()` in `src/freegraph/_stategraph.py`: `_static_points(...)` for both interrupt keywords → `self._build_spec()` → `_graph_spec_from(...)` → `_conditional_mapping(...)` → record the 6 injections → emit the `store` warning (T011) → return a **new** `CompiledGraph`; signature **byte-identical** to the B2F2 snapshot; zero schema re-parsing
- [X] T011 Add the `store`-warning helper in `src/freegraph/_stategraph.py`: when `store is not None` call `warnings.warn(msg, stacklevel=2)` **exactly once** per `compile()` with a message containing `v1 不支持 Store`; `store is None` and all other injections (`checkpointer` / `cache` / `transformers` / `debug` / `name`) produce **zero** warnings (裁定 14 · FR-016)
- [X] T012 Update docstrings only: `src/freegraph/_stategraph.py` module docstring (compile now delivered · `invoke` → B7F3) and `src/freegraph/graph.py` module docstring (drop the "`compile()` 仍抛 `NotImplementedError`（归 B7F2）" wording); **export surface unchanged**
- [X] T013 [Foundational] **Split/replace without deleting** `tests/facade/test_facade.py` in the same batch — it contains **four** compile-stub assertions that all go red once `compile()` works: (`test_not_wired_method_raises_not_implemented[compile]` · **`test_not_wired_compile_reports_b7f2`** · `test_not_wired_methods_produce_no_real_semantics` · `test_not_wired_compile_does_not_return_an_executable`). ① replace the `compile` parametrization with a new `TestCompileIsWired` (calls `graph.compile()` on a valid graph, asserts a non-null product with 6 methods and **no** `NotImplementedError`) ② **replace** (not delete) `test_not_wired_compile_reports_b7f2` with its inverse: `compile()` returns a product whose `invoke()` raises `NotImplementedError` naming **B7F3** ③ replace `test_not_wired_compile_does_not_return_an_executable` with "compile returns a product, but every capability method still raises `NotImplementedError`" ④ keep the `vars(graph)` exact-key-set assertion (compile MUST NOT mutate the builder) and move it out of the raising block ⑤ add a test that the 5 remaining builder methods (`add_sequence` / `set_entry_point` / `set_conditional_entry_point` / `set_finish_point` / `set_node_defaults`) still raise `NotImplementedError` with the "本版本不交付" message ⑥ narrow/remove `NOT_WIRED_PATTERN` (its only use was the `compile` parametrization). Phase 2 MUST end with `pytest -q` green

**Checkpoint**: `compile()` works end-to-end for the mechanical path; the capability surface exists; the baseline is green. User stories now add their own judgments.

---

## Phase 3: User Story 1 - 一行拿到可执行图 (Priority: P1) MVP

**Goal**: `builder.compile()`（**无参**）返回一个具备 6 方法能力面的非空产物。

**Independent Test**: 对 2 节点最小图调用 `compile()`，断言返回非空、6 个方法全部存在，且每个方法抛出的 `NotImplementedError` 点名其归属 feature。

### Tests for User Story 1

- [X] T014 [P] [US1] Add A1/A2/A3 tests in `tests/facade/test_compiled_graph.py`: `compile()` with **no arguments** returns a non-null object; `hasattr` for all 6 capability methods; each method call raises `NotImplementedError` and the message contains the owning feature id (`B7F3` / `B8F2` / `B22F1` / `B15F1` / `B16F1`) · zero `AttributeError`
- [X] T015 [P] [US1] Add product-shape test in `tests/facade/test_compiled_graph.py`: `vars(compiled)` keys are **exactly** the 11 frozen names (**the 8 public ones MUST be instance attributes — a `@property` would make this assertion fail**); the 8 public attributes are readable with the expected default values (`debug is False` · `name is None` · `interrupt_before_nodes == ()` · `interrupt_after_nodes == ()` · `checkpointer is None` · `store is None`)
- [X] T016 [US1] Add builder-state test in `tests/facade/test_facade.py`: after `compile()`, `vars(graph)` is unchanged and calling `compile()` twice still leaves the builder untouched

### Implementation for User Story 1

- [X] T017 [US1] Audit `src/freegraph/_stategraph.py` against the A1–A3 flow (2 nodes + `START`/`END` edges → `compile()`), and fix any deviation from `quickstart.md` §2 so the no-argument call always succeeds for a valid graph

**Checkpoint**: US1 = MVP slice. `harness/demo/graph_core.py` 的 A3 组判据（`compile()` 无参 + `invoke`/`stream` 存在）可满足。

---

## Phase 4: User Story 2 - 编译时能注入可插拔能力 (Priority: P1)

**Goal**: `compile(checkpointer=..., store=...)` 被接受、被记录、可从公开属性读到；`store` 非 `None` 时**恰好 1 条** warning。

**Independent Test**: `compile()`、`compile(checkpointer=None, store=None)`、`compile(checkpointer=obj, store=obj)` 三次都不抛异常，且两个对象身份可读回；warning 计数精确。

### Tests for User Story 2

- [X] T018 [P] [US2] Add injection-acceptance tests in `tests/facade/test_compiled_graph.py`: `compile()` / `compile(checkpointer=None, store=None)` never raise `TypeError`; `compile(checkpointer=<obj>, store=<obj>)` succeeds and `compiled.checkpointer is <obj>` / `compiled.store is <obj>` (identity preserved); non-`Store` objects and falsy values (`False` / `0`) are accepted without error (NV-5)
- [X] T019 [P] [US2] Add warning-count tests in `tests/facade/test_compiled_graph.py`: passing a non-`None` `store` yields **exactly 1** `warnings.warn` whose message contains `v1 不支持 Store`; `store=None` yields **0**; each of `checkpointer` / `cache` / `transformers` / `debug` / `name` yields **0** (裁定 14)
- [X] T020 [US2] Add injection **behaviour** test in `tests/facade/test_compiled_graph.py`: all six keywords are recorded and readable via the public attributes (identity preserved), `store=None` produces **0** warnings, and a non-`None` `store` produces **exactly 1** (behaviour only — the README text assertions live in **T043b**, after T043)

### Implementation for User Story 2

- [X] T021 [US2] Audit `src/freegraph/_stategraph.py`'s injection recording and warning emission against `contracts/compile-contract.md` §6 (all 6 keywords accepted · zero type validation · identity preserved · exactly-one-warning rule) and fix any deviation

**Checkpoint**: US2 independently passes; keywords are API-compatible while v1 behaviour stays absent (documented + visible).

---

## Phase 5: User Story 3 - 编译期发现图定义的问题 (Priority: P1)

**Goal**: 3 类错误（边目标不存在 / 条件边源不存在 / 条件边目标不存在）在 **`compile()` 调用点**被捕获；14 项 MUST 查全部生效，7 项 MUST NOT 查全部不误报。

**Independent Test**: 三个反例各抛内置 `ValueError` 且消息点名问题节点；动态路由 / 不可达 / 自环 / 非法 checkpointer 的图**编译成功**。

### Tests for User Story 3

- [X] T022 [P] [US3] Add the 3 core error tests in `tests/facade/test_compile_validation.py`: unknown static edge target (with a **valid `START` entry** so the target error is the only one), unknown conditional-edge source, unknown `path_map` target — each asserts `pytest.raises(ValueError)` **around the `compile()` call** and that the message names the offending node(s) (SC-003)
- [X] T023 [P] [US3] Add the CV matrix tests in `tests/facade/test_compile_validation.py`: one positive or negative case for each of **CV-1…CV-14** from `data-model.md` §6 (schema · static source · entrypoint · static target · conditional source · conditional target · empty node table（实际命中 C-03/C-04）· V-1（**正向**：合法订阅通道可编译）· V-14 `__parent__` · V-16 multi-source forms · CV-14 `path_map` target), including the multi-source `→ END` and target-count ≠ 1 cases and the `__parent__` reserved name. ⚠️ **CV-7 / CV-8 是防御性检查**（compile 链路不可独立触发反例）⇒ 以正向用例覆盖. ⚠️ **CV-11 / CV-12 are only cross-referenced here** (detailed coverage belongs to US4 · T027–T029). ⚠️ **CV-13 fails EARLIER than `compile()`** — wrap the **`add_conditional_edges`** call, never assume `compile()` raises
- [X] T024 [US3] Add the NV reverse-assertion tests in `tests/facade/test_compile_validation.py`: **NV-1** (`path_map=None` dynamic routing compiles) · **NV-2** (nodes returning `Command` / `Send` / `None` compile) · **NV-3** (unreachable node compiles) · **NV-4** (self-loop compiles) · **NV-5** (non-conforming checkpointer/store compile) · **NV-6** (any valid schema compiles) · **NV-7** (arbitrary `Hashable` `path_map` keys compile)
- [X] T025 [US3] Add the exception-surface test in `tests/facade/test_compile_validation.py`: every compile-time failure type is one of builtin `ValueError` / `TypeError` / `InvalidSchemaError`; no new exception classes exist (assert the raised type is exactly one of those, never a subclass introduced by this feature)

### Implementation for User Story 3

- [X] T026 [US3] Audit `src/freegraph/_stategraph.py` for **single-source validation**: confirm CV-1…CV-10 and CV-12…CV-14 are produced by `_build_spec()` / `GraphSpec.__post_init__` and that `compile()` contains **no** duplicated structural check besides CV-11; fix any duplicate or missing check

**Checkpoint**: US3 independently passes; all failures happen at `compile()`, none at `invoke()`.

---

## Phase 6: User Story 4 - 静态断点随编译一并落地 (Priority: P2)

**Goal**: `compile(interrupt_before=...)` / `interrupt_after=` 接受 6 种形态；`"*"` 展开为全部可执行节点；未知节点在编译期点名失败；失败信号与 `GraphSpec` 构造期**逐字同款**。

**Independent Test**: 6 形态各一例；对同一非法值比较「入口层委托产生的消息」与「直接调 `normalize_static_points` 的消息」是否**字符串相等**。

### Tests for User Story 4

- [X] T027 [P] [US4] Add the 6-form tests in `tests/facade/test_compile_interrupt.py`: `None` → `()`; `"*"` → all executable nodes (excluding `START`/`END`); `["b","a","b"]` → `("b","a")`; `("a",)` / `{"a"}` / `1` / `1.5` ⇒ `TypeError`（**容器形态只断言类型，不断言消息逐字**）; `"a"` ⇒ `TypeError`（由 `GraphSpec` 归一抛出）; `["nope"]` ⇒ `ValueError` naming `nope`; `["*"]` and `[""]` ⇒ `ValueError`
- [X] T028 [P] [US4] Add the byte-equality test in `tests/facade/test_compile_interrupt.py`: for each **element-level or bare-string** illegal value (`""` / `"a"` as bare strings · `""` inside a list · `"__start__"` / `"__end__"` / `"*"` elements · `["nope"]` · a non-`str` element), `str(compile_raised)` **equals** `str` of the exception raised by calling `freegraph.runtime._static.normalize_static_points(value, nodes, field)` directly (B13F1 D-2); **container forms** (`tuple` / `set` / numeric) only assert `TypeError`
- [X] T029 [US4] Add the public-attribute test in `tests/facade/test_compile_interrupt.py`: `interrupt_before_nodes` / `interrupt_after_nodes` expose the **normalized ordered tuple** (`"*"` expanded, `None` → `()`) and the two fields are validated independently (X-11)

### Implementation for User Story 4

- [X] T030 [US4] Audit `src/freegraph/_stategraph.py`'s static-interrupt path: confirm the entry gate is **whitelist-only** and that no element-level validation is duplicated; confirm `None` is converted to `()` before `GraphSpec` construction; fix any deviation

**Checkpoint**: US4 independently passes; the compile entry is stricter only where X-2 says so.

---

## Phase 7: User Story 5 - 一次编译，多次安全使用 (Priority: P2)

**Goal**: 产物是**快照**（编译后改图不影响它；两次编译互相独立）；产物持**通道规格模板**（零状态残留）；三个私有字段名冻结。

**Independent Test**: 编译 → 改构建器 → 断言产物节点表不变；两次编译 → 改动其一不影响其二；通道 `checkpoint()` 与全新编译的一致。

### Tests for User Story 5

- [X] T031 [P] [US5] Add snapshot-isolation tests in `tests/facade/test_compiled_graph.py`: after `compile()`, `add_node("late", ...)` does **not** change the product's `_spec.nodes`; two `compile()` calls on the same builder return different objects whose node/edge tables are independent; the builder is never warned about post-compile mutation (assert zero warnings)
- [X] T032 [P] [US5] Add channel-template tests in `tests/facade/test_compiled_graph.py`: `compiled._spec.channels is not compiled._builder_spec.channels`; every channel's `checkpoint()` equals that of a freshly compiled graph's same key (zero residual state · I-5); `compiled._spec.conditional_edges == {}` (I-3)
- [X] T033 [P] [US5] Add frozen-carrier tests in `tests/facade/test_compiled_graph.py`: the three private field names exist with the expected types; `compiled._builder_spec.node_records` is present and complete (B8F3/DD-13); `_conditional_edges` has the frozen 5-key shape and registration order when the graph has conditional edges (I-7 / I-9…I-13)
- [X] T034 [US5] Add order/determinism tests in `tests/facade/test_compiled_graph.py`: channel key order = schema order then route channels by first appearance; node order = registration order; edge source/target order preserved after `END` filtering; two compiles produce **structurally equivalent** summaries (channels compared by type/reducer/key, not identity)

### Implementation for User Story 5

- [X] T035 [US5] Audit `src/freegraph/_stategraph.py`'s snapshot discipline (fresh `_build_spec()` per call, new channels mapping, no builder mutation, no post-compile flag/warning) and fix any deviation from `contracts/compile-contract.md` §7

**Checkpoint**: US5 independently passes; the "compile once, run many" façade contract holds on the compile side (the `invoke` half is B7F3).

---

## Phase 8: User Story 6 - 编译期零副作用 (Priority: P3)

**Goal**: 编译期**不调用**任何用户函数、**不读**环境变量、**不**做 I/O / 出站。

**Independent Test**: 节点 / 路由 / 归约器全部带计数器 ⇒ 编译后计数为空；`socket` 监测下编译 ⇒ freegraph 自身出站 0。

### Tests for User Story 6

- [X] T036 [P] [US6] Add the zero-user-call test in `tests/facade/test_compiled_graph.py`: with `CallCounter`-wrapped nodes and routers (including a reducer-bearing schema), `compile()` leaves `counter.counts == {}` (SC-005)
- [X] T037 [P] [US6] Add the environment/egress test in `tests/facade/test_compiled_graph.py`: monkeypatch `os.environ` with sentinel values (`LANGSMITH_TRACING` / `LANGCHAIN_DEBUG` / `LANGGRAPH_DEBUG`) and assert compile behaviour is identical (same product shape, `debug is False`); assert no socket is opened during `compile()` (observe-only fixture)
- [X] T038 [US6] Add the import-surface test in `tests/facade/test_compiled_graph.py`: parse `src/freegraph/_stategraph.py` with `ast` and assert zero imports of `langchain*` / `langgraph*` / `langsmith` / `socket` / `urllib` / `http` / `subprocess`, and zero `os.environ` / `getenv` usage

### Implementation for User Story 6

- [X] T039 [US6] Audit `src/freegraph/_stategraph.py` for side effects (no user call, no env read, no I/O, no thread) and fix any deviation; confirm `debug` is hard-coded from the keyword only (X-9)

**Checkpoint**: US6 independently passes; the red lines (zero env / zero egress) hold inside `compile()`.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 差分、验收脚本、文档、下游接线、门禁、双向追溯

- [X] T040 [P] Extend `tests/differential/parity_probe.py`: add the `CompileScenario` model + `_run_compile_scenarios()` with the discrete summary from `contracts/upstream-parity.md` §3.1, then add **D-75…D-91** and wire them into `run_all()` so `-k compile` selects them (upstream absent ⇒ empty list ⇒ skip)
- [X] T041 [P] Add pytest wrappers for the compile scenarios in `tests/differential/test_parity_probe.py` (skip when upstream is absent; report per-scenario verdict)
- [X] T042 Change `main()` / `_facade_ready()` in `harness/demo/graph_core.py` to **run A3 first, then probe `invoke`**: ① `compile()` still unavailable ⇒ exit **2** as before; ② `compile()` works and `invoke()` raises `NotImplementedError` ⇒ **after `case_build_and_compile` (A3) has run and passed**, print `[环境未就绪]` and exit **2**; ③ both work ⇒ run the whole suite. **MUST NOT** use "product has 6 methods" as the readiness test (that would make `graph_core` exit **1** and break `tests/runtime/test_acceptance_script.py`'s `rc == 2` assertion)
- [X] T043 [P] Update `README.md` factually: the `StateGraph` row's "`compile` 待 B7F2" → "`compile` 已交付（B7F2）；`invoke` 待 B7F3"; add the explicit "v1 不支持 `Store`" statement next to the `store=` keyword note, **and the checkpointer deferral "checkpointer 的行为归 B14F1"** (SC-015)
- [X] T043b Add documentation test in `tests/facade/test_compiled_graph.py` (Polish · **after T043**): `README.md` contains the explicit "v1 不支持 `Store`" statement and the checkpointer deferral to B14F1 (assert the exact substrings introduced by T043)
- [X] T044 [P] Update `harness/demo/README.md`'s soft/hard assertion list factually (`compile` no longer a stub; `invoke` still B7F3)
- [X] T045 Create `harness/verification/B7F2/acceptance.py` **with header**: one-click acceptance covering A1–A3, the 3 core errors, the 6 static-interrupt forms, injection read-back + warning count, snapshot independence, zero user calls, and the frozen private field names
- [X] T046 Create `harness/verification/B7F2/manual-verification.md`: five sections (环境 / 步骤 / 实际输出 / 结论 / 遗留问题) + source coverage (E-25…E-55 · D-75…D-91) + the EV-1a/b/c acknowledgment (承接 B7F3 / B8F1 / B22F1 / B23F1 / B25F1) + the X-9 / X-11 / X-12 acknowledgment text
- [X] T047 [P] Add B7F2 to the records table in `harness/verification/README.md`
- [X] T048 [P] Downstream wiring **D-1**: append a "B7F2 → B7F3" block to `harness/features/B7F3_invoke返回完整状态.md` (`invoke` MUST drive L2 `run_graph` with `_spec`; new channel instances per run; no second execution path)
- [X] T049 [P] Downstream wiring **D-2**: append a "B7F2 → B8F1" block to `harness/features/B8F1_条件边路由与fresh读.md` (read `compiled._conditional_edges` and fill `GraphSpec.conditional_edges`; routing consumes only the L2 field; MUST NOT import `_stategraph` / `_ConditionalEdgeSpec`; no re-normalization of `path_map`)
- [X] T050 [P] Downstream wiring **D-3**: append a "B7F2 → B8F3" block to `harness/features/B8F3_节点别名与context通道.md` (read `_builder_spec.node_records[*].alias` by field name)
- [X] T051 [P] Downstream wiring **D-4**: append a "B7F2 → B14F1" block to `harness/features/B14F1_Checkpointer协议与MemorySaver.md` (B14F1 MUST add the upstream-identical compile-time checkpointer type check)
- [X] T052 [P] Downstream wiring **D-5**: append a "B7F2 → B22F1" block to `harness/features/B22F1_get_graph与draw_mermaid.md` (export structure from `_spec` + `_conditional_edges`; no re-parsing of builder state)
- [X] T053 Run the full regression and the affected gates: `pytest -q`, `gate_G14` (facade zero implementation body), `gate_G17` (facade import/env/IO), `gate_G19` (compat matrix), `gate_G20`/`G30` (signature headers), `gate_G25` (layer direction · L3 single file), `gate_G26` (network static), `gate_G27` (zero egress), `gate_G29` (read-only baseline diff + acceptance exit codes); record every command and outcome into `harness/verification/B7F2/manual-verification.md`
- [X] T054 Verify bidirectional traceability: every SC in the two traceability tables below resolves to at least one **test/executable** task; every task resolves to at least one FR/SC or an explicitly labelled process obligation; confirm the spec's `D-75…D-91` rows match the probe implementation (flag any mismatch for a spec patch instead of silently diverging)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately
- **Foundational (Phase 2)**: depends on Setup; **T013 MUST land in the same batch as T005–T012** (otherwise `tests/facade/test_facade.py` goes red) and Phase 2 MUST end green
- **User Stories (Phases 3–8)**: all depend on Phase 2; they may run in parallel (different test files) or sequentially in priority order
- **Polish (Phase 9)**: depends on all desired user stories; **T042 MUST precede T053** (the gate/regression run asserts exit code 2) · **T043 MUST precede T043b** (the doc assertions read the README text written by T043) · **T043b MUST precede T053**

### User Story Dependencies

- **US1 (P1)**: after Phase 2 — independent
- **US2 (P1)**: after Phase 2 — independent (T020 is behaviour-only; the README text assertions moved to **T043b** right after T043)
- **US3 (P1)**: after Phase 2 — independent
- **US4 (P2)**: after Phase 2 — independent
- **US5 (P2)**: after Phase 2 — independent
- **US6 (P3)**: after Phase 2 — independent

### Within Each User Story

- Tests are written **before** the audit/fix task of that story
- Audit tasks only touch `src/freegraph/_stategraph.py` — tasks touching that file **MUST NOT** be parallelised with each other (T010 · T012 · T017 · T021 · T026 · T030 · T035 · T039)
- Each story ends with its checkpoint before the next priority starts (if sequential)

### Parallel Opportunities

- Setup: T002 / T003 (different files)
- Phase 3–8 test tasks marked `[P]` are in **different test files** except within the same file — same-file tasks are kept sequential
- Polish: T040 / T041 / T043 / T044 / T047 / T048–T052 are independent files

---

## Parallel Example: US3 + US4 (after Phase 2)

```bash
# US3 — validation matrix (one file, sequential within it)
Task: "T022 [US3] Add the 3 core error tests in tests/facade/test_compile_validation.py"
Task: "T023 [US3] Add the CV matrix tests in tests/facade/test_compile_validation.py"
Task: "T024 [US3] Add the NV reverse-assertion tests in tests/facade/test_compile_validation.py"
Task: "T025 [US3] Add the exception-surface test in tests/facade/test_compile_validation.py"

# US4 — static interrupts (a different file ⇒ parallel with US3)
Task: "T027 [P] [US4] Add the 6-form tests in tests/facade/test_compile_interrupt.py"
Task: "T028 [P] [US4] Add the byte-equality test in tests/facade/test_compile_interrupt.py"
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 (T001–T004)
2. Phase 2 (T005–T013) — **baseline MUST be green here**
3. Phase 3 (T014–T017)
4. **STOP and VALIDATE**: `compile()` 无参可调用 + 6 方法 + `graph_core.py` A3 组；这是**MVP 六项最小交付集的第 2 项**

### Incremental Delivery

1. Setup + Foundational → 机械主链可用（compile 不再抛 `NotImplementedError`）
2. US1 → 能力面判据闭环（A1 / A2 / SC-001 / SC-004）
3. US2 → 注入项 + `store` 警告（A3 / SC-002 / SC-015）
4. US3 → 编译期校验清单（SC-003 / SC-006 / SC-008）
5. US4 → 静态断点（SC-005 / SC-007）
6. US5 → 快照与规格（SC-009…SC-012）
7. US6 → 零副作用（SC-005 / 红线）
8. Polish → 差分 / 验收 / 文档 / 接线 / 门禁（SC-013 / SC-014 / SC-016）

### Parallel Team Strategy

1. 团队一起完成 Phase 1 + Phase 2（T013 必须同批）
2. 之后：开发 A = US1 + US2（`test_compiled_graph.py`）；开发 B = US3（`test_compile_validation.py`）；开发 C = US4 + US5（`test_compile_interrupt.py` / 追加到 `test_compiled_graph.py`）⚠️ 同文件任务须协调
3. 最后合并 Polish（`src/freegraph/_stategraph.py` 的审计任务需**串行**）

---

## SC → Tasks 追溯（判据级）

| SC | 判定任务 | 说明 |
|---|---|---|
| SC-001 | T014 · T017 · T042 · T045 | 无参 `compile()` 返回非空产物 + `graph_core` A3（先跑 A3、再以 rc=2 结束）+ acceptance |
| SC-002 | T018 · T019 · T042 · T045 | `checkpointer=None, store=None` 被接受 + 身份可读 + `graph_core` A3 的 `store`/`checkpointer` 关键字用例 |
| SC-003 | T022 · T025 · T045 | 3 类核心错误 + 异常类型面 |
| SC-004 | T014 · T015 | 6 方法全在 + 零 `AttributeError` |
| SC-005 | T036 · T037 · T038 | 用户函数计数 0 + 零 env / 零出站 + 导入面 |
| SC-006 | T023 · T024 · T026 | CV 14 项 + NV 7 项 + 单一真源 |
| SC-007 | T027 · T028 · T029 | 6 形态 + 逐字同款 + 归一值可见 |
| SC-008 | T022 · T023 · T014 | 单源 `END` 过滤 / 多源 V-16 / `__parent__` + 6 方法异常 |
| SC-009 | T023 · T034 | 适配正确性 + 顺序与确定性 |
| SC-010 | T033 · T032 · T015 | 冻结字段名 + 条件边映射形状 + `conditional_edges` 恒空 + 11 键 |
| SC-011 | T032 | 通道零残留 + 两映射独立 |
| SC-012 | T031 · T034 | 快照隔离 + 结构等价 |
| SC-013 | T013 · T053 | 公开快照不变 + 门禁（「11 键冻结」属 SC-010 的 I-1） |
| SC-014 | T017 · T053 | 最小图可编译 + `target.py` diff 为空 |
| SC-015 | T018 · T019 · T020 · T043b | 注入项可读 + 警告计数 + 文档写明（T043b 紧随 T043） |
| SC-016 | T040 · T041 | 差分 `D-75…D-91` 判词一致 |

> 每条 SC 至少挂一条**测试 / 可执行判定**任务；**实现任务不单独充当判据覆盖**（宪法 v1.11.0）。

---

## 附录 · 任务 → FR / SC 反向追溯

> 宪法 v1.11.0 原则 VI：追溯表 MUST **双向**。本表与上方「SC → Tasks」共同构成双向追溯；T054 校验完整性。

| 任务 | 对应 FR / SC | 任务 | 对应 FR / SC |
|---|---|---|---|
| T001 | 过程义务：基线确认 | T002 | 过程义务：测试夹具（判据由 T014–T039 承担） |
| T003 | 过程义务：证据可复现（E-25…E-55 · 原则 VIII） | T004 | 过程义务：测试骨架 |
| T005 | FR-002 / FR-010 / SC-015 | T006 | FR-011 / FR-024 / SC-004 / SC-008 |
| T007 | FR-013 / SC-007 | T008 | FR-004 / FR-007 / SC-009 |
| T009 | FR-009 / SC-010 | T010 | FR-001 / FR-003 / FR-008 / FR-019 / SC-001 |
| T011 | FR-016 / 裁定 14 / SC-015 | T012 | FR-017 / SC-013 |
| T013 | FR-011 / SC-004 / SC-013 | T014 | FR-001 / FR-002 / FR-011 / SC-001 / SC-004 |
| T015 | FR-010 / SC-010 / SC-013 | T016 | FR-019 / SC-012 / SC-013 |
| T017 | FR-001 / FR-020 / SC-001 / SC-014 | T018 | FR-016 / SC-002 / SC-015 |
| T019 | FR-016 / 裁定 14 / SC-015 | T020 | FR-016 / SC-015（行为面） |
| T021 | FR-016 / SC-015 | T022 | FR-005 / SC-003 / SC-008 |
| T023 | FR-005 / FR-007 / SC-003 / SC-006 / SC-008 / SC-009 | T024 | FR-006 / SC-006 |
| T025 | FR-018 / SC-003 | T026 | FR-005 / FR-006 / SC-006 |
| T027 | FR-013 / FR-014 / SC-005 / SC-007 | T028 | FR-014 / SC-007 |
| T029 | FR-010 / FR-014 / SC-007 | T030 | FR-013 / FR-014 / SC-005 / SC-007 |
| T031 | FR-019 / SC-012 | T032 | FR-012 / SC-011 |
| T033 | FR-008 / FR-009 / FR-010 / SC-010 | T034 | FR-021 / SC-009 / SC-012 |
| T035 | FR-012 / FR-019 / SC-011 / SC-012 | T036 | FR-015 / SC-005 |
| T037 | FR-015 / FR-023 / SC-005 | T038 | FR-023 / SC-005 |
| T039 | FR-015 / FR-023 / SC-005 | T040 | FR-005 / FR-006 / SC-016 |
| T041 | SC-016 | T042 | FR-022 / SC-014 |
| T043 | FR-016 / 原则 X / SC-015 | T044 | 原则 X / SC-001 |
| T045 | SC-001…SC-015 | T046 | 原则 V / EV-1 |
| T047 | 原则 V | T048 | D-1 |
| T049 | D-2 | T050 | D-3 |
| T051 | D-4 / FR-025 | T052 | D-5 |
| T053 | SC-013 / SC-014 / FR-022 / FR-024 | T054 | 原则 VI（双向追溯） |
| T043b | FR-016 / 原则 X / SC-015（文档面） | — | — |

---

## Notes

- `[P]` 仅用于不同文件且无未完成依赖的任务；**同一文件**（尤其 `src/freegraph/_stategraph.py`）的审计任务 MUST 串行。
- 本 feature **不实现** `invoke()` / `stream()` / `get_graph()` / 条件边求值 / checkpointer 与 store 的行为 / 别名语义。
- `harness/demo/target.py` 是**只读基准**；任何任务都不得修改它（G29 断言 diff 为空）。
- `harness/demo/graph_core.py` 在本 feature 后**仍退出码 2**（`invoke` 属 B7F3）——由 T042 的守卫改造保证；**不是失败**。
- **不新增源文件**：`src/freegraph/_stategraph.py` 是 L3 唯一的实现落点（层注册表冻结 · G25 禁 L3→L3）。
- 门禁 3 / 4 / 5 的端到端部分按 plan 的 EV-1a / EV-1b / EV-1c 承接 **B7F3 / B8F1 / B22F1 / B23F1 / B25F1**；本 feature **不写永久红 CI**。
- G22「场景②」的运行期断言不在本 feature 点亮；由 B7F3 承接（B3F1 裁定 22 · H-6）。T053 须记录「未点亮，承接 B7F3」。
- 差分编号 **D-75…D-91**；设计决策编号 **DD-01…DD-18**；偏离编号 **X-1…X-12**；裁定编号 **1…14** —— 四套编号 MUST NOT 混用。
- `store=` 的警告机制是 **`warnings.warn`**（用户裁定 A · 裁定 14），**不是** `logging`；上游的「已编译后改图」提示才是 `logging`（E-49/E-50），本 feature **不复制**它。
- 顺序要求：**T042 → T053**、**T043 → T043b → T053**（`T043b` 沿用仓库既有的「同阶段子标号」惯例，如 **B6F1 的** `T032b`）；T053 之前完成 T040 / T041（差分）；T046 在 T053 之后补入实际输出；T054 最后完成。
- **T013 是本 feature 唯一「同批必做」的既有测试改造**（4 处 compile 桩断言：含 `test_not_wired_compile_reports_b7f2`）；改造方向是**替换为反面断言**，不是删除。
- **T042 的口径**：`graph_core` **先跑 A3 再探 `invoke`**；`invoke` 未就绪 ⇒ A3 通过后以退出码 **2** 结束。**MUST NOT** 用「6 方法能力面」当就绪判据（会打红既有 `rc == 2` 硬断言）。
- **T043b** 属 Polish（紧随 **T043**）：README 的「v1 不支持 `Store`」等文本断言；US2 的 **T020** 只做**行为**断言。
- **CV-13 例外**：`path_map` 形态在 `add_conditional_edges` 时即失败（早于 `compile()`）⇒ 其用例 MUST 包裹**登记调用**（T023）。
- **plan 的 Phase A–E 与 tasks 的 Phase 1–9 的映射**：A→T005–T006 · B→T007–T011 · C→T022–T026 · **D→T014–T039 + T040–T041** · **E→T042–T054（含 T043b）**（**以 tasks 的顺序为准**）。
