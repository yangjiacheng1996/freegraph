# Tasks: B18F1 · Span 数据类生产（节点 / 工具 / 模型三级 span）

**Input**: Design documents from `/specs/b18f1-span-production/`

**Prerequisites**: `plan.md`（required）· `spec.md`（required）· `research.md` ·
`data-model.md` · `contracts/span-production-contract.md` ·
`contracts/invoke-helpers-contract.md` · `contracts/upstream-parity.md` · `quickstart.md`

**Tests**: **必做** —— 本 feature 的 SC-001…SC-016、D-201…D-208、零开销计数、
属性允许清单、依赖 / 环境变量守卫均为判据级要求。每个 user story **先写测试、先失败**，
再实现。

**Organization**: 按 user story 分组。US1（P1）是 MVP 的最小切片；US2（P1）补模型 / 工具 span；
US3（P1）验证零开销；US4（P2）验证关联键；US5（P2）验证并发隔离。
> US2 的单元测试可用**合成的节点 span** 独立验证；端到端父子链在 US1 完成后补跑。
> US3 依赖 US1；US5 依赖 US1 + US2。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、不依赖未完成任务）
- **[Story]**: `US1` / `US2` / `US3` / `US4` / `US5`（仅 user story 阶段）
- 每个任务都含**精确文件路径**

## Path Conventions

- 单项目：`src/freegraph/` + `tests/` + `harness/`（仓库根）
- 设计 / 契约：`specs/b18f1-span-production/`
- 人工验证：`harness/verification/B18F1/`

---

## 追溯表（FR → 任务）

| FR | 任务 |
|---|---|
| FR-001 | T008 / T017 / T047 |
| FR-002 | T030 / T032 / T053 |
| FR-003 | T008 / T010 / T032 / T039 / T059 |
| FR-004 | T013 / T015 / T016 / T017 |
| FR-005 | T019 / T021 / T024 / T025 |
| FR-006 | T019 / T023 / T024 / T025 |
| FR-007 | T017 / T024 / T028 / T042 |
| FR-008 | T008 / T013 / T023 |
| FR-009 | T009 / T013 / T017 |
| FR-010 | T014 / T016 / T018 |
| FR-011 | T008 / T024 / T035 / T036 |
| FR-012 | T007 / T036 / T037 / T038 / T039 |
| FR-013 | T022 / T024 / T047 |
| FR-014 | T009 / T024 / T047 |
| FR-015 | T022 / T024 |
| FR-016 | T022 / T024 |
| FR-017 | T022 / T047 |
| FR-018 | T014 / T020 / T026 |
| FR-019 | T004 / T031 / T034 |
| FR-020 | T031 / T034 |
| FR-021 | T031 / T033 / T048 |
| FR-022 | T011 / T027 / T048 |
| FR-023 | T022 / T047 |
| FR-024 | T041 / T042 / T043 / T044 |
| FR-025 | T023 / T028 |
| FR-026 | T048 / T050 |
| FR-027 | T011 / T023 / T028 |
| FR-028 | T020 / T026 |
| FR-029 | T055 / T056 |

**SC 追溯表**

| SC | 任务 |
|---|---|
| SC-001 | T022 / T024 / T047 |
| SC-002 | T013 / T017 / T023 / T024 / T042 |
| SC-003 | T030 / T032 / T059 |
| SC-004 | T031 / T033 / T034 |
| SC-005 | T013 / T014 / T017 |
| SC-006 | T035 / T036 / T038 |
| SC-007 | T014 / T018 / T020 / T023 / T028 / T053 |
| SC-008 | T017 / T024 / T047 |
| SC-009 | T013 / T022 / T024 |
| SC-010 | T041 / T042 / T043 / T044 |
| SC-011 | T022 / T047 / T053 |
| SC-012 | T033 / T048 / T050 |
| SC-013 | T021 / T025 |
| SC-014 | T019 / T025 |
| SC-015 | T020 / T026 |
| SC-016 | T055 / T056 |

> **T057 / T058** 是跨 feature 接线 / 文档守卫（不单挂某条 FR/SC）；**T059** 挂在 FR-003 / SC-003（run-scoped 生命周期）。

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 记录基线、确认上游锚点、建立 L2 / L5 新模块骨架。

- [x] T001 Create `harness/verification/B18F1/manual-verification.md` with the five-section skeleton（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）and a `§1.1 基线` placeholder; create the `harness/verification/B18F1/` directory. Other tasks append their own subsections; T049 is the final consolidator/owner.
- [x] T002 Run the real full baseline `.venv/bin/python -m pytest -q --tb=no` and record passed / skipped / failed / elapsed in `harness/verification/B18F1/manual-verification.md` §1.1 (2026-11-20 expected: `1778 passed, 6 skipped in 121.56s`).
- [x] T003 [P] Re-check upstream versions and anchors `langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17` against `specs/b18f1-span-production/research.md` §2; update line numbers only if they drifted.
- [x] T004 [P] Confirm zero read-only / dependency changes: run `git diff --exit-code -- harness/demo/target.py pyproject.toml`; report the result to T001 / T033.
- [x] T005 Create the L5 package skeleton `src/freegraph/observability/__init__.py`, `src/freegraph/observability/_time.py`, `src/freegraph/observability/_producer.py`, `src/freegraph/observability/_invoke.py` with signature headers, module docstrings first, and `__all__: list[str] = []` / planned exports as comments only.
- [x] T006 [P] Create the L2 private hook skeleton `src/freegraph/runtime/_span_hook.py` with signature header, module docstring first, and `__all__: list[str] = []`.

**Checkpoint**: Baseline recorded; upstream anchors confirmed; empty skeletons exist; no behavioural change.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 建立 L2 运行 id 绑定、L2 私有 hook、L5 生产者栈与测试夹具。US1 / US2 依赖本阶段。

**⚠️ CRITICAL**: 本阶段完成前，US1 / US2 不开始。

- [x] T007 Add private `bind_run_ids(run_id, thread_id)` context manager to `src/freegraph/runtime/_stream_context.py`; it MUST set only `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`, MUST NOT touch writer / custom sink / round capture, and MUST keep `bind_stream` behaviour unchanged; update the module docstring note that `bind_stream` remains `StreamSession`'s only entry. This is the spec §5-approved invoke-path binding; it MUST NOT introduce a second id carrier.
- [x] T008 Implement `src/freegraph/runtime/_span_hook.py` core: `bind_span_tracer(tracer)`, `current_span_tracer()`, `start_node_span(tracer, node, run_id, thread_id, checkpoint_id=None)`, `end_node_span(tracer, start_span)`, UTC ISO-8601 nanosecond helper, strict-positive duration helper, `uuid4().hex`; define a private `typing.Protocol` `_SpanTracer` in the same module (`on_span_start` / `on_span_end` / `current_span_id`); L5 `SpanProducer` structurally satisfies it but MUST NOT import it; `start_node_span` MUST call `tracer.on_span_start(start)` after constructing the start span, and `end_node_span` MUST call `tracer.on_span_end(end)` after constructing the end span; if `run_id is None` the hook MUST NOT construct a span.
- [x] T009 [P] Implement `src/freegraph/observability/_time.py`: `utc_now_iso_ns()` returning `(iso_text, ns)` in `YYYY-MM-DDTHH:MM:SS.<9 digits>+00:00` and `end_ns > start_ns` enforcement (`end_ns = max(end_ns, start_ns + 1)`).
- [x] T010 Implement `src/freegraph/observability/_producer.py` `SpanProducer`: `_SpanFrame(span, kind)`, `ContextVar[tuple[_SpanFrame, ...]]`, `on_span_start` / `on_span_end` / `current_span_id` / `current_node_span`, kind inference (empty attrs ⇒ node; `execute_tool` ⇒ tool; other `gen_ai.operation.name` ⇒ model), receiver forwarding, and receiver-exception isolation; add private `bind_tracer(tracer)`.
- [x] T011 Implement `src/freegraph/observability/__init__.py` initial exports: `SpanProducer` only; keep `invoke_model` / `invoke_tool` for US2; MUST NOT import L2.
- [x] T012 Create `tests/observability/conftest.py` with reusable fixtures: `RecordingReceiver` (records start/end spans), `FailingReceiver` (raises on callback), `SpanConstructionCounter` (monkeypatches both `runtime._span_hook.Span` and `observability._producer.Span` construction points), `RunIdBindingCounter` (monkeypatches `runtime._stream_context.bind_run_ids`, records calls, reset per test), and a `bound_tracer` fixture that binds the same producer into L2 + L5 for tests.

**Checkpoint**: L2 id binding + hook + L5 producer + fixtures are ready; no node span is produced yet.

---

## Phase 3: User Story 1 - 知道每一步跑了多久 (Priority: P1) 🎯 MVP

**Goal**: 每个被执行的节点任务产生一个节点 span，含节点名、起止时间、空属性 / 空 context、正确 parent。

**Independent Test**: 注入计数 / 捕获夹具，跑两节点线性图，断言 2 个节点 span，`name == node`、`start_time < end_time`；节点抛异常时仍有成对结束 span 且原样重抛。

### Tests for User Story 1

- [x] T013 [P] [US1] Write basic node-span tests in `tests/runtime/test_node_spans.py`: one node + `a → b`; assert span count, `name == node`, `node == node`, `attributes == {}`, `context == {}`, `checkpoint_id is None`, `start_time < end_time`, top-level `parent is None`.
- [x] T014 [US1] Write node-span exception tests in `tests/runtime/test_node_spans.py`: node raises `RuntimeError`; assert start/end same `id`, `end_time` non-null, node span `attributes == {}` (no `error.type`), exception object/type/message unchanged.
- [x] T015 [US1] Write node-span fan-out + skip tests in `tests/runtime/test_node_spans.py`: `Send` fan-out tasks each produce a node span; nodes not triggered produce no span.

### Implementation for User Story 1

- [x] T016 [US1] Integrate node span production into `src/freegraph/runtime/superstep.py` `_run_round._bind._inner` (`:1361-1368`): read `current_span_tracer()` once; `None` ⇒ call `fn()` unchanged; otherwise start before `fn()` and end after return / exception; do not touch `node_input` / state.
- [x] T017 [US1] Ensure node span fields in `src/freegraph/runtime/_span_hook.py`: `name == node`, `node == node`, `attributes={}`, `context={}`, `parent = tracer.current_span_id()`, `thread_id` / `run_id` from `current_stream_ids()`, `checkpoint_id` from the run-time seam (v1 `None`).
- [x] T018 [US1] Add the exception path in `src/freegraph/runtime/superstep.py` / `_span_hook.py`: end the same-id span with `end_time` then re-raise the original exception; do not write `error.type` on node spans.

**Checkpoint**: US1 is independently testable; node spans work with a bound tracer; no tracer ⇒ no node span.

---

## Phase 4: User Story 2 - 模型与工具调用各自有 span (Priority: P1)

**Goal**: `invoke_model` / `invoke_tool` 产生独立的模型 / 工具子 span；父链、名称、最小属性集、形状校验、awaitable、节点外透传全部正确。

**Independent Test**: 在节点内用 `invoke_model(FakeModel(), ...)` 与 `invoke_tool(FakeTool(), ...)` 调用；断言模型 / 工具 span 的 `parent` == 节点 span `id`，名称 / `gen_ai.*` 属性符合 Q9；工具内再调模型时父链逐层正确。

### Tests for User Story 2

- [x] T019 [P] [US2] Write shape tests in `tests/observability/test_invoke_helpers.py`: 4 mismatch cases（工具→`invoke_model`、模型→`invoke_tool`、无 `invoke`→`invoke_model`、无工具形状→`invoke_tool`）⇒ `TypeError`，模型 / 工具 span 构造数 == 0。**必须同时覆盖「未绑定 tracer」与「已绑定 tracer」两种状态**（Q14：形状校验与生产开关无关）。
- [x] T020 [US2] Write failure / awaitable tests in `tests/observability/test_invoke_helpers.py`: ① `invoke` returns awaitable ⇒ `TypeError`, helper MUST NOT return awaitable; with production enabled, span start/end are paired and `error.type == "TypeError"`; ② model / tool `obj.invoke` raises `RuntimeError` ⇒ span ends paired and `error.type == "RuntimeError"`（工具同样）；③ success ⇒ no `error.type`.
- [x] T021 [US2] Write outside-node / no-tracer tests in `tests/observability/test_invoke_helpers.py`: no active node span ⇒ direct `obj.invoke(...)`, zero span, return value identity equal to direct call; shape validation still runs; **outside-node awaitable ⇒ `TypeError`（Q16 在节点外同样生效）**.
- [x] T022 [P] [US2] Write attribute / name tests in `tests/observability/test_span_attributes.py`: model span only `gen_ai.operation.name` + `gen_ai.request.model`（`model_name` → `model` precedence）; tool span only `gen_ai.operation.name` + `gen_ai.tool.name` + `gen_ai.tool.call.id`（explicit only）; no `gen_ai.system` / provider / usage / description / conversation id; node attrs empty; `context == {}`.
- [x] T023 [P] [US2] Write producer tests in `tests/observability/test_producer.py`: nested model → tool → model parent chain; stack returns to parent after child end; `FailingReceiver` does not break the call; stack remains balanced.

### Implementation for User Story 2

- [x] T024 [US2] Add model / tool span constructors to `src/freegraph/observability/_producer.py`: `make_model_span(obj)`, `make_tool_span(obj, call_id)`, `finish_span(start, error_type=None)`; attributes from Q9; names `chat <model>` / `execute_tool <tool>`; parent = current stack top; `node` from current node frame; `run_id` / `thread_id` / `checkpoint_id` inherited from the node span.
- [x] T025 [US2] Implement `src/freegraph/observability/_invoke.py`: `invoke_model(obj, input, *, call_id=None)` / `invoke_tool(obj, args, *, call_id=None)`; shape validation per Q14, awaitable rejection per Q16, outside-node passthrough per Q13, return result identity unchanged.
- [x] T026 [US2] Add failure / awaitable handling in `src/freegraph/observability/_invoke.py`: model / tool span `error.type = type(exc).__name__` or `_OTHER`; awaitable rejection ends the span; original exceptions re-raised unchanged.
- [x] T027 [US2] Export `invoke_model` / `invoke_tool` from `src/freegraph/observability/__init__.py`; keep them out of `freegraph.graph` and `freegraph.runtime.__all__`.
- [x] T028 [US2] Verify / harden receiver-exception isolation implemented by T010: add regression tests in `tests/observability/test_producer.py`; catch receiver exceptions, MAY `logging.warning`, never propagate; stack push/pop remains balanced. (No duplicate implementation.)

**Checkpoint**: US2 is independently testable with a synthetic node span / producer stack; full end-to-end passes after US1.

---

## Phase 5: User Story 3 - 不诊断时零负担 (Priority: P1)

**Goal**: 未绑定 tracer 时零 span、零回调、不生成 span 专用 `run_id`（`stream()` 既有事件 `run_id` 不属 span 生产）、不读环境变量、不引入依赖。

**Independent Test**: 不绑定任何接收端跑图；计数夹具断言两处 `Span` 构造数 == 0、回调数 == 0；依赖闭包仍空；`import freegraph` 不加载 L5 / hook；设置 `LANGSMITH_TRACING=true` 不改变行为。

### Tests for User Story 3

- [x] T029 [P] [US3] Write zero-overhead tests in `tests/observability/test_zero_overhead.py`: no tracer + node / exception / node-outside helper ⇒ `Span` construction count == 0 and receiver callbacks == 0; no **span-specific** `run_id` generated / bound (`stream()` event `run_id` is out of scope), asserted with `RunIdBindingCounter` == 0.
- [x] T030 [P] [US3] Write environment / laziness tests in `tests/runtime/test_no_env_reads.py`: set `LANGSMITH_TRACING=true` / `LANGCHAIN_TRACING_V2=true`, run a graph, assert zero spans; assert `import freegraph` does not load `freegraph.observability` or `freegraph.runtime._span_hook`.
- [x] T031 [P] [US3] Extend `tests/contracts/test_architecture.py` assertions (reuse G3 / G7): dependency closure empty; no `opentelemetry` / `langchain` / `langsmith` imports; L2 must not import L5; L5 must not import L2; public API snapshot unchanged. Env-read coverage stays in T030 / existing G24.

### Implementation for User Story 3

- [x] T032 [US3] Audit the zero-overhead guard implemented by T016: confirm exactly one `current_span_tracer()` read per task / run, `None` ⇒ no span / no id, no eager import or module-level side effect; add a regression assertion/comment only if missing; record the audit in `harness/verification/B18F1/manual-verification.md` §1.2.
- [x] T033 [US3] Ensure `src/freegraph/__init__.py` remains a lazy shell and no L5 import leaks; if a new module import is needed for tests, use explicit `freegraph.observability` imports only.
- [x] T034 [US3] Run the US3 targeted tests + gates (`tests/observability/test_zero_overhead.py`, `tests/runtime/test_no_env_reads.py`, `tests/contracts/test_architecture.py`) and record pass/fail + counts in `harness/verification/B18F1/manual-verification.md` §1.2.

**Checkpoint**: US3 proves the default path is inert; the zero-overhead claim is measurable, not qualitative.

---

## Phase 6: User Story 4 - 每条 span 都能回连到运行与会话 (Priority: P2)

**Goal**: 每个 span 带非空 `run_id`、生效 `thread_id`、所属节点名、可读 `checkpoint_id`；`stream()` 事件与 span 同 id；`RunConfig.run_id` 被忽略。

**Independent Test**: 在 `stream()` / `invoke()` 下启用生产，收集事件与 span；断言同一次运行的 `run_id` / `thread_id` 逐字相同；`RunConfig(run_id=...)` 不生效；invoke 路径只有一个 `run_id`。

### Tests for User Story 4

- [x] T035 [P] [US4] Write span key tests in `tests/runtime/test_span_ids.py`: every span has non-empty `run_id`; `thread_id == RunConfig.resolved_thread_id()`; `node` equals enclosing node name; `checkpoint_id` is readable (`None` allowed).
- [x] T036 [US4] Write stream / span id equality tests in `tests/runtime/test_span_ids.py`: `stream()` events and spans share the exact same `run_id` / `thread_id`.
- [x] T037 [US4] Write `RunConfig(run_id=...)` ignored + invoke one-run-id tests in `tests/runtime/test_span_ids.py`: user value never becomes span `run_id`; all spans in one invoke share one generated id.

### Implementation for User Story 4

- [x] T038 [US4] Implement `run_graph` id binding in `src/freegraph/runtime/superstep.py`: when a tracer is bound and `current_stream_ids()[0] is None`, enter `bind_run_ids(uuid4().hex, run_config.resolved_thread_id())`; do not override an existing id; no id generation when no tracer.
- [x] T039 [US4] Verify / harden L5 producer / helpers: they inherit `run_id` / `thread_id` / `checkpoint_id` / `node` from the current node span in `src/freegraph/observability/_producer.py`; MUST NOT import L2. (No duplicate implementation.)
- [x] T040 [US4] Verify `src/freegraph/runtime/_stream.py` / `bind_stream` is unchanged and stream events keep their existing ids.

**Checkpoint**: US4 links spans to runs / threads / nodes without introducing a second id carrier.

---

## Phase 7: User Story 5 - 并发节点不串父 (Priority: P2)

**Goal**: 同一 super-step 并发执行的多个节点各自产生独立 span；模型 / 工具 span 只挂在本任务的节点下。

**Independent Test**: 构造同一 super-step 内并发 3 个节点的图，每个节点调用一个工具；断言 3 个节点 span id 互不相同，工具 span 的 parent 与节点 id 一一对应，跨任务父子数 == 0。

### Tests for User Story 5

- [x] T041 [P] [US5] Write concurrent node tests in `tests/runtime/test_concurrency_spans.py`: N ≥ 3 concurrent nodes ⇒ N node spans, top-level `parent is None`; no cross-task parent.
- [x] T042 [US5] Write per-task nested tests in `tests/observability/test_producer.py`: each node calls `invoke_tool` / `invoke_model`; direct child parent == its node span id; nested child parent == its own enclosing span id; no cross-task parent; child span count per node is correct.
- [x] T043 [US5] Write stack-isolation tests in `tests/observability/test_producer.py`: two `copy_context()` tasks have independent stacks; one task's end does not pop another task's frame.

### Implementation for User Story 5

- [x] T044 [US5] Verify `src/freegraph/runtime/_concurrency.py` `copy_context()` propagation is sufficient; do not add a second thread-local / global stack; adjust only `src/freegraph/observability/_producer.py` if needed.
- [x] T045 [US5] Run the concurrency tests with the real thread pool and assert no cross-task parent; record the result in `harness/verification/B18F1/manual-verification.md`.

**Checkpoint**: US5 proves trace trees are task-local under concurrency.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 差分、契约守卫、文档、人工门禁、全量回归。

- [x] T046 [P] Add differential scenarios D-201…D-208 to `tests/differential/test_b18f1_span_parity.py` (B18F1-specific differential suite; upstream absent ⇒ skip); assert the SAME / DIFF / STRICTER verdicts from `contracts/upstream-parity.md`.
- [x] T047 Complete the JSON / C21-isolation contract cases in `tests/observability/test_span_attributes.py` (building on T022): `dataclasses.asdict(span)` is `json.dumps`-serializable; `context == {}` (C21 isolation); node attrs empty; `error.type` MUST be present on model / tool failure and absent on success. Do not duplicate T022's key allow-list cases. Receiver-exception isolation stays in T028.
- [x] T048 [P] Add public-face guard in `tests/facade/test_api_snapshot.py`: no new `freegraph.graph` / `freegraph.runtime.__all__` / L1 symbols. Import-graph / laziness coverage stays in T031 and T030.
- [x] T049 As the manual-record owner, consolidate and complete `harness/verification/B18F1/manual-verification.md`: append fake round + real round（or R-3 deviation + approval）, zero-outbound evidence, actual outputs (not “符合预期”), conclusion, remaining issues; execution order: T002 → T034 → T045 → T052 → T049; do not overwrite the sections appended by T002 / T034 / T045 / T052. Also record the D-1 / D-4 / D-6 / R-4 cross-feature wiring evidence.
- [x] T050 Add a **separate** `README.md` section「可观测属性」with the `gen_ai.*` attribute mapping (D-5 is **MUST**); **MUST NOT** modify the「API 兼容矩阵」section (G8: symbol rows / 4 columns / manifest only). Public symbols stay zero-change.
- [x] T051 Optional: add a span-production acceptance scenario to `harness/demo/graph_core.py` / `harness/demo/acceptance.py`; **MUST NOT** modify `harness/demo/target.py`.
- [x] T052 Run `specs/b18f1-span-production/quickstart.md` §1–§6.1 and record the actual outputs in `harness/verification/B18F1/manual-verification.md`.
- [x] T053 Run the full suite `.venv/bin/python -m pytest -q --tb=no` and record passed / skipped / failed; confirm the baseline count only increased by the new tests and no existing test regressed.
- [x] T054 Final red-list review (`plan.md` Pre-registered Red List): confirm no L2 → L5 import, no L5 → L2 import, no public API expansion, no env reads, no dependency changes, no `Span` field changes, no `stream()` / `RunConfig` / `SuperStepResult` / `PregelTask` changes.
- [x] T055 [P] Add `tests/runtime/test_node_record_carriers.py`: verify `stream_mode="values"/"updates"/"tasks"` + `PregelTask.result` can reconstruct principle IV input / output; error is carried by the raised exception（并发其它失败见 `add_note`）, and `PregelTask.error` MUST NOT be asserted as a failure-path carrier; assert node span `attributes == {}` and `context == {}`; document that `invoke()` per-node carriers are explicitly B19F1/B20 downstream (D-6) with a written capture mechanism.
- [x] T056 [P] Add a doc guard `tests/contracts/test_trace_carrier_contract.py` asserting `specs/b18f1-span-production/spec.md` contains the principle IV carrier mapping (D-6 / FR-029 / SC-016), including that errors are carried by the raised exception and `PregelTask.error` is not a failure-path carrier; assert the explicit B19F1/B20 downstream clause and capture mechanism; assert node span attribute rule remains `{}`; assert the D-4 / D-6 target prompt wiring exists (B14F1/B19F1/B20F1/B20F2). Full D-1 / D-2 / D-3 / D-4 / D-6 / R-4 wiring including B21F1 stays in T058.
- [x] T057 Wire B18F1's downstream clauses into the target prompts: B14F1 (`checkpoint_id`), B19F1 (D-1 `SpanProducer` dual-binding + D-6 `invoke()` per-node carriers + capture mechanism), B20F1/B20F2 (D-2 JSON records + C27 query dimensions + D-6 capture mechanism), B21F1 (D-3 OTLP 1:1). The prompt edits are complete; the manual record is appended by T001/T049 during implementation. **Completed 2026-11-21 in the analysis remediation round.**
- [x] T058 [P] Add `tests/contracts/test_downstream_wiring.py`: assert **across** the B14F1 / B19F1 / B20F1 / B20F2 / B21F1 prompts the key B18F1 downstream clauses are present (D-1 / D-2 / D-3 / D-4 / D-6 / R-4): D-1 dual binding (`SpanProducer` / `bind_span_tracer` / `bind_tracer`); D-2 JSON records (`dataclasses.asdict`) and C27 query dimensions (`run_id` / `thread_id` / 时间范围 / 节点名, no `checkpoint_id` filter); D-3 OTLP 1:1; D-4 `checkpoint_id`; D-6 per-node capture mechanism + error = raised exception; R-4 run-scoped lifetime. Assert `spec.md` D-1/D-2/D-3/D-4/D-6 match these key clauses. Do not require exact paraphrases or every clause in every prompt.
- [x] T059 [P] Add run-scoped lifetime tests in `tests/runtime/test_span_lifetime.py`: after the tracer binding scope exits, no further span is produced; within one run all spans share exactly one `run_id`; re-entering the scope produces a new `run_id`; use `RunIdBindingCounter` to assert binding count 0 without a tracer and exactly 1 per invoke with a tracer. (FR-003 / U1)
- [x] T060 Add one-click acceptance script `harness/verification/B18F1/acceptance.py`（A1–A7）与 pytest 包装 `tests/runtime/test_acceptance_script.py::test_b18f1_one_click_acceptance_script_passes`。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; can start immediately.
- **Foundational (Phase 2)**: depends on Setup; blocks US1 / US2.
- **US1 (Phase 3)**: depends on Foundational.
- **US2 (Phase 4)**: depends on Foundational; unit tests can run in parallel with US1 using a synthetic node span; end-to-end parent chain validates after US1.
- **US3 (Phase 5)**: depends on US1 (node integration exists).
- **US4 (Phase 6)**: depends on US1; independent of US2.
- **US5 (Phase 7)**: depends on US1 + US2 (nested model / tool spans).
- **Polish (Phase 8)**: depends on all desired stories (at least US1 + US3 for MVP; all stories for full acceptance). **T057** (cross-feature wiring) is done in the 2026-11-21 remediation round; **T058** guards it; **T059** depends on US4's id binding.

### User Story Dependencies

| Story | Depends on | Independent Test |
|---|---|---|
| **US1** | Foundational | Node span count / name / duration / exception pairing |
| **US2** | Foundational（单元）/ US1（端到端父链） | Helpers produce child spans; parent == node; attribute allow-list |
| **US3** | US1 | No tracer ⇒ zero span / zero callback / no id / no env |
| **US4** | US1 | Span keys + stream event id equality + `RunConfig.run_id` ignored |
| **US5** | US1 + US2 | Concurrent nodes / per-task nested spans / no cross-task parent |

### Within Each User Story

- Tests first → implement → run targeted tests → checkpoint.
- Models / span constructors before helpers / wiring.
- Parent chain before concurrency.
- Keep `Span` fields / `TraceSink` / `RunConfig` / `SuperStepResult` / `PregelTask` frozen.

---

## Parallel Execution Examples

### Setup + Foundational

```bash
# T003 / T004 / T006 can run in parallel:
Task: "T003 Re-check upstream anchors"
Task: "T004 Confirm target.py / pyproject.toml zero changes"
Task: "T006 Create runtime/_span_hook.py skeleton"

# After T005 / T006:
Task: "T007 bind_run_ids"
Task: "T009 observability/_time.py"
Task: "T012 test fixtures"
```

### User Story 1

```bash
# T013 can start first; T014 / T015 extend the same file sequentially:
Task: "T013 [US1] basic node-span tests"
Task: "T014 [US1] exception tests (after T013)"
Task: "T015 [US1] fan-out / skip tests (after T014)"

# Then sequential integration:
Task: "T016 [US1] integrate _run_round._bind"
Task: "T017 [US1] node span fields"
Task: "T018 [US1] exception path"
```

### User Story 2

```bash
# Different files can run in parallel; same-file cases are sequential:
Task: "T019 [US2] shape tests"
Task: "T020 [US2] awaitable tests (after T019)"
Task: "T021 [US2] outside-node tests (after T020)"
Task: "T022 [US2] attribute / name tests"
Task: "T023 [US2] producer nested / receiver tests"

# Then sequential implementation:
Task: "T024 [US2] producer span constructors"
Task: "T025 [US2] _invoke.py helpers"
Task: "T026 [US2] failure / awaitable handling"
Task: "T027 [US2] exports"
Task: "T028 [US2] receiver isolation"
```

### User Story 3 / 4 / 5

```bash
# After US1:
Task: "T029 [US3] zero-overhead tests"
Task: "T035 [US4] span key tests"

# After US1 + US2:
Task: "T041 [US5] concurrent node tests"
Task: "T042 [US5] per-task nested tests"
```

---

## Implementation Strategy

### MVP First (US1 + US3)

1. Complete Setup.
2. Complete Foundational.
3. Complete US1 (node spans).
4. Complete US3 (zero-overhead proof).
5. **STOP and VALIDATE**: node spans + zero-overhead are independently demonstrable.
6. This is the minimum shippable slice; the feature's headline “三级 span” needs US2.

### Full P1 (US1 + US2 + US3)

1. Complete Setup + Foundational.
2. US1 → node spans.
3. US2 → model / tool child spans + parent chain.
4. US3 → zero-overhead + dependency guards.
5. **STOP and VALIDATE**: three-level spans + measurable zero overhead.

### Incremental Delivery

1. Setup + Foundational → hook / producer / fixtures ready.
2. US1 → node spans (MVP slice).
3. US2 → model / tool spans (full three-level promise).
4. US3 → zero-overhead proof (P1).
5. US4 → run / thread / node correlation (P2).
6. US5 → concurrency isolation (P2).
7. Polish → differential / contract guards / manual gate / full regression.

### Parallel Team Strategy

- After Foundational:
  - Developer A: US1 node spans.
  - Developer B: US2 helpers + producer tests (synthetic node span; ends with US1 integration).
- After US1:
  - Developer C: US3 zero-overhead + dependency guards.
  - Developer D: US4 correlation keys.
- After US1 + US2:
  - Developer E: US5 concurrency.
- Polish: differential / contract guards can be parallel; manual verification is single-owner and serial.

---

## Notes

- [P] = different files, no dependency on incomplete tasks.
- [Story] label maps each task to `spec.md` US1…US5.
- Every task includes an exact file path (or an exact command with file paths).
- Tests are mandatory for this feature: each story starts with failing tests.
- Do not modify `harness/demo/target.py` (read-only baseline).
- Do not add runtime dependencies, public L2 symbols, or a second `run_id` carrier.
- L2 MUST NOT import L5; L5 MUST NOT import L2 (use node-span inheritance for ids).
- Node span `attributes` / `Span.context` MUST remain empty mappings.
- `error.type` MUST be written on model / tool failure spans and MUST NOT appear on success; node spans never write it.
- Manual verification is serially edited: T001 creates; T002/T034/T045/T052 append their own subsections; **T049 runs after T052** and is the final consolidator/owner.
- **Cross-feature wiring**: T057 (done 2026-11-21) writes the B14F1 / B19F1 / B20F1 / B20F2 / B21F1 downstream clauses; T058 is the doc guard. Do NOT duplicate the production logic in target features.
- **Run-scoped lifetime**: T059 verifies FR-003's "scope exit ⇒ no span" and "one run ⇒ one run_id".
- After T053 / T054 / T055 / T056 / T058 / T059 / T060, the feature is ready for manual review and `/speckit.implement` completion.
