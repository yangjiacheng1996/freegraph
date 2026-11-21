---

description: "Task list for B19F1 · TraceSink 接入 + current_span() + 默认关闭"
---

# Tasks: B19F1 · `TraceSink` 接入 + `current_span()` + 默认关闭

**Input**: Design documents from `/specs/b19f1-tracesink-current-span/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: **包含**。spec 定义了 SC-001…SC-017，且项目宪法原则 VI 要求「判据级可追溯」；
每个用户故事先写失败测试，Phase 6（下游记录）同样先写测试。

**Organization**: 任务按用户故事分组；每个故事可独立实现 / 测试 / 交付。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: `US1` / `US2` / `US3`；Setup / Foundational / Phase 6 / Polish 不带故事标签
- 每个任务都带**精确文件路径**

---

## 追溯表（FR → 任务）

| FR | 任务 |
|---|---|
| FR-001 | T018 / T019 / T021 |
| FR-002 | T015 / T016 / T019 / T039 |
| FR-003 | T023 / T026 |
| FR-004 | T023 / T025 |
| FR-005 | T029 / T031 |
| FR-006 | T015 / T045 |
| FR-007 | T030 / T032 |
| FR-008 | T030 / T032 |
| FR-009 | T009 / T019 |
| FR-010 | T015 / T019 / T020 / T030 |
| FR-011 | T036 / T040 |
| FR-012 | T037 / T041 |
| FR-013 | T037 / T043 |
| FR-014 | T037 / T041 |
| FR-015 | T033 / T035 / T038 / T039 |
| FR-016 | T045 |
| FR-017 | T016 / T025 / T035 |
| FR-018 | T026 / T028 / T045 |
| FR-019 | T045 |
| FR-020 | T052 |
| FR-021 | T024 / T027 |

## 追溯表（SC → 任务）

| SC | 任务 |
|---|---|
| SC-001 | T023 |
| SC-002 | T029 / T031 |
| SC-003 | T015 / T016 |
| SC-004 | T023 / T025 |
| SC-005 | T030 / T032 |
| SC-006 | T015 |
| SC-007 | T017 / T020 |
| SC-008 | T036 / T043 |
| SC-009 | T037 |
| SC-010 | T016 / T025 / T035 |
| SC-011 | T033 / T038 |
| SC-012 | T015 / T033 / T035 |
| SC-013 | T034 / T043 |
| SC-014 | T033 / T035 / T036 |
| SC-015 | T025 / T035 |
| SC-016 | T024 / T027 |
| SC-017 | T035 / T042 |

> **T044 / T045 / T046 / T052** 是差分 / 冻结面 / 层门禁 / 最终审计（不单挂某条 FR/SC）。
> **T013 / T014** 是 R-1 / R-2 / R-3 的登记与测试拆分（跨 feature 门禁准备；三者已获发起者一次性追认 2026-11-21）。
> **SC-010** 的判定必须使用 T012 的 `FailingSink` 做**图级**注入（见 T016）；仅 producer 级异常隔离不足。
> **FR-006 / SC-012** 的判定必须使用 `SpanOnlySink`（只有 start/end）做**图级**注入（见 T015）。

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 记录基线、确认上游锚点、建立 L5 新模块骨架；零行为改动。

- [X] T001 Create `harness/verification/B19F1/manual-verification.md` with the five-section skeleton（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）and a `§1.1 基线` placeholder; create the `harness/verification/B19F1/` directory. Other tasks append their own subsections; T048 is the final consolidator/owner.
- [X] T002 Run the real full baseline `.venv/bin/python -m pytest -q --tb=no` and record passed / skipped / failed / elapsed in `harness/verification/B19F1/manual-verification.md` §1.1 (2026-11-21 expected: `1863 passed, 6 skipped`; elapsed 以本机为准).
- [X] T003 [P] Re-check upstream versions and anchors (`langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`) against `specs/b19f1-tracesink-current-span/contracts/upstream-parity.md` §1/§2; update line numbers only if they drifted.
- [X] T004 [P] Confirm zero read-only / dependency changes: run `git diff --exit-code -- harness/demo/target.py pyproject.toml`; report the result to T001 / T032.
- [X] T005 [P] Create L5 module skeletons `src/freegraph/observability/_record.py` and `src/freegraph/observability/_inject.py` with signature headers, module docstrings first, and planned exports as comments only; no behavior.

**Checkpoint**: Baseline recorded; upstream anchors confirmed; L5 skeletons exist; no behavioural change.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 建立记录类型、producer 扩展、run scope、L2 采集形状、测试夹具与 R-1/R-2/R-3 门禁。
**⚠️ CRITICAL**: 本阶段完成前，US1 / US2 / US3 / Phase 6 不开始。

- [X] T006 Implement `TraceRecord` + `json_safe()` + `to_jsonable()` in `src/freegraph/observability/_record.py` per [data-model.md](./data-model.md) §2/§6: frozen/slots/kw_only; fields `span_id` / `task_id` / `run_id` / `thread_id` / `checkpoint_id` / `node` / `superstep` / `triggers` / `concurrency_group` / `barrier_groups` / `input_state` / `output_state` / `error`; `json_safe` deterministic, never raises, never introspects object contents; `to_jsonable()` converts `error` to `{"type": ..., "message": ...}` or `None`.
- [X] T007 [P] Add `SpanProducer.current_span() -> Span | None` to `src/freegraph/observability/_producer.py`: return the top `_SpanFrame.span`; empty stack ⇒ `None`; do not change `current_span_id()` / `current_node_span()`.
- [X] T008 Add `SpanProducer.wants_trace_records`（构造期缓存 `getattr(receiver, "on_trace_record", None) is not None`）+ `SpanProducer.on_trace_record(payload)` to `src/freegraph/observability/_producer.py` (same file as T007 ⇒ MUST run after T007; **not** parallel): build `TraceRecord` from the L2 pure-data payload, forward to the receiver's **optional** `on_trace_record` via `getattr`, isolate receiver **`Exception`** (`logging.warning`) while **not swallowing `BaseException`**, never propagate `Exception`.
- [X] T009 Implement `trace_run_scope(tracer: TraceSink | None)` in `src/freegraph/observability/_inject.py`: non-`None` ⇒ one `SpanProducer(receiver=tracer)` bound to both `bind_tracer` (L5) and `bind_span_tracer` (L2); `None` ⇒ both hooks set to `None`（**仅用于 B19F1 作用域内的嵌套屏蔽**）; yield producer or `None`; reset on exit. Also add private `_B19F1_SCOPE_ACTIVE: ContextVar[bool]` + `b19f1_scope_active()`; set True on enter（token 恢复）. This is the R-2 exception point; MUST NOT bind / read anything else from L2.
- [X] T010 [P] Add private `TaskTraceMeta` + `build_trace_payload(...)` to `src/freegraph/runtime/_span_hook.py`: pure-data only (no L5 import); payload keys per [data-model.md](./data-model.md) §8.2; `span_id` / `run_id` / `thread_id` / `checkpoint_id` come from the start `Span`.
- [X] T011 Extend `src/freegraph/runtime/superstep.py` `_run_round` **only** to carry a private `TaskTraceMeta` slot per dispatched task（形状见 T010）；**MUST NOT** 在本任务计算最终 triggers / concurrency / barrier（归 T039–T041）；Keep `SuperStepResult` / `PregelTask` fields unchanged.
- [X] T012 [P] Extend `tests/observability/conftest.py` and `tests/runtime/conftest.py` with reusable fixtures: `RecordingSink`（start/end + records）、`FailingSink`（start/end/record 均抛异常；**必须被 T016 使用**）、`FailingRecordSink`（仅 `on_trace_record` 抛异常；**必须被 T035 使用**）、`RecordSink`（仅实现 `on_trace_record`，用于 Phase 6 记录断言）、`SpanOnlySink`（只有 `on_span_start` / `on_span_end`；**无** `current_span` / `on_trace_record`；供 T015 的 FR-006 / SC-012 判定）、`SpanConstructionCounter`、`SpanProducerConstructionCounter`、`RunIdBindingCounter`（**必须 patch `_stategraph.bind_run_ids`（T019 要求 module-level import）以及 `_stream_context.bind_run_ids` / `superstep.bind_run_ids`**）、`TraceRecordConstructionCounter`（patch `_record.TraceRecord`）、`InputOutputCaptureCounter`（patch `_execute_node_pure_with_raw` / `build_trace_payload` 等等价采集点）、B18F1-style `direct_bind_producer` fixture（`bind_span_tracer` + `bind_tracer` 直接绑定；供 T024 回归）、graph builders (`linear_two_node`, `nested_model_tool`, `fanout_graph`, `barrier_graph`, `interrupt_graph`).
- [X] T013 [P] Split the B18F1 assertion in `tests/contracts/test_architecture.py`: keep a pure-module check for `observability/_record.py` / `_time.py` / `_producer.py` / `_invoke.py`; add an explicit exception check allowing `observability/_inject.py` → `runtime._span_hook` **only**（R-3 · 拆分而不删）；**MUST NOT** 放行 `_stream_context`.
- [X] T014 R-1/R-2/R-3 一次性追认（**R-1 主体已在分析轮落地**：立项书 §5.1 / layer-registry `trace-wiring-L3-L5` / G25 `allow` / `tests/gates/test_gates.py` 自检）：核对 R-1 四处，并把 **R-1+R-2+R-3 的追认文字（确认人 + 日期 2026-11-21）** append 到 T001's manual-verification file；R-2 仅 `_inject.py` → `_span_hook.bind_span_tracer`，**不读 `_stream_context`**；R-3 仅拆分断言；**B8F2 的 R-6 同步收窄为「L2 读取 stream id，B19F1 从节点 span 继承」**。**R-2 / R-3 不进 layer-registry / G25**（它们是 ARCH-3 / 测试拆分例外，由 T013 的 architecture test 覆盖）。

**Checkpoint**: `TraceRecord` / `current_span` / `on_trace_record` / run scope / L2 payload / fixtures / R-1-R-3 gates are ready; no user-visible behavior yet.

---

## Phase 3: User Story 1 - 把运行轨迹接到我自己的系统 (Priority: P1) 🎯 MVP

**Goal**: 注入 `TraceSink` 后，节点执行触发**成对**的 `on_span_start` / `on_span_end`；
span 带 `run_id` / `thread_id` / 节点名 / `checkpoint_id`；异常路径也成对；`stream()` 同样生效。

**Independent Test**: `RecordingSink` + `compile(tracer=sink)` + `a → b` 图：断言 2 对 start/end、
`id` 配对、`run_id` 非空、`thread_id == "t-1"`、异常节点仍成对且原异常重抛。

### Tests for User Story 1

- [X] T015 [P] [US1] Write `tests/observability/test_b19f1_push.py`: one node + `a → b`; assert start/end counts, same `id`, `end_time` non-null, `name` / `node`, `run_id` non-empty, `thread_id` from `RunConfig`, `checkpoint_id is None`; **inject `SpanOnlySink`（无 `current_span` / 无 `on_trace_record`）并断言可正常注入、结果不变、无 `AttributeError`、`TraceRecordConstructionCounter` == 0、`InputOutputCaptureCounter` == 0**（FR-006 / SC-012；用 `typing.cast` 表达静态类型与运行期鸭子类型的有意差异）；**传 `RunConfig(run_id="user-supplied")` 并断言所有 span 的 `run_id != "user-supplied"` 且非空**（FR-010 / 宪法 v1.15.2）；**另测 `RunConfig(thread_id=None)` ⇒ span 的 `thread_id is None` 且不报错**（Edge Cases）。
- [X] T016 [P] [US1] Write `tests/observability/test_b19f1_exception.py`: node raises `RuntimeError`; assert start/end same `id`, end `end_time` non-null, original exception object/type/message unchanged. **另用 `FailingSink`（start/end 回调抛异常）跑同一张图，断言 `invoke()` 输出与正常 sink 逐字相同、sink 异常不传播、节点自身的 `RuntimeError` 仍按原对象/类型/消息抛出**（SC-010 / FR-017）。`on_trace_record` 的顺序断言归 T035。
- [X] T017 [P] [US1] Write `tests/observability/test_b19f1_stream.py`: `stream()` path emits span pairs; event and span `(run_id, thread_id)` are identical; no trace field in the stream envelope; `stream()` works without a tracer. **不在此任务断言 record**（归 T038）。

### Implementation for User Story 1

- [X] T018 [US1] Implement `StateGraph.compile(*, tracer: TraceSink | None = None)` in `src/freegraph/_stategraph.py`; store on `CompiledGraph._tracer`; keep `compile()` no-arg callable and all existing keywords unchanged.
- [X] T031 [US1] Add the **single shared** cheap guard helper in `src/freegraph/_stategraph.py`（**先于 T019 / T020** 落地；区分 `OWN` / `MASK` / `LEGACY_DIRECT` / `NONE`：`_tracer is not None` ⇒ OWN；`_tracer is None` + 外层 tracer + `b19f1_scope_active()` ⇒ MASK（**B19F1 作用域优先**；即使外层另有 B18F1 直接绑定也屏蔽）；`_tracer is None` + 外层 tracer + 非 B19F1 作用域 ⇒ LEGACY_DIRECT；`_tracer is None` + 无外层 tracer ⇒ NONE）；**NONE 分支 MUST NOT import L5**；L5 `_inject` 只在 `_tracer is not None` 或 `current_span_tracer() is not None` 时局部 import。让 T019 / T020 / T027 调用它，**MUST NOT** 另写第二个 scope 判断 / 第二个「是否需要 trace」分支。
- [X] T019 [US1] Implement `CompiledGraph.invoke` run scope in `src/freegraph/_stategraph.py`: `bind_run_ids` MUST be imported at module level（from `.runtime._stream_context`，便于 T012 的 counter patch `_stategraph.bind_run_ids`）；if `_tracer` is not `None`, bind a fresh `uuid4().hex` run id via `bind_run_ids` with `resolve_config(config).resolved_thread_id()`（**忽略 `RunConfig.run_id`**）, then enter the L5 `trace_run_scope`; wrap `run_graph`; ensure no second id carrier. **B18F1 的 L2 `_run_graph` 绑定是 fallback**（仅当 `_STREAM_RUN_ID` 为空时生效）；本任务 MUST 保证**每次注入运行恰发生一次有效绑定**（L3 已绑定时 L2 不覆盖），且与 B18F1 共用同一 `bind_run_ids` 载体。
- [X] T020 [US1] Implement `CompiledGraph._stream_events` run scope in `src/freegraph/_stategraph.py`: **when `_tracer is not None`**, enter `trace_run_scope(self._tracer)` around `StreamSession`; nested masking for `_tracer is None` is owned by T027; let `StreamSession` bind `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`; do not bind an invoke-style run id on the stream path.
- [X] T021 [US1] Update `tests/facade/test_api_snapshot.py` via `--update-api-snapshot` and the committed snapshot `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`: accept the new keyword-only `tracer` in `StateGraph.compile`; keep the `compile()` no-arg assertion; update the snapshot (update, not relax).
- [X] T022 [US1] Update `harness/demo/README.md`: change the `compile(tracer=...)` row from「待锁定」to「已锁定」and cite `specs/b19f1-tracesink-current-span/spec.md` §「注入点形态裁定」.

**Checkpoint**: US1 is independently functional; T031 shared guard is in place before T019/T020; span push works for `invoke()` and `stream()`; exception path paired.

---

## Phase 4: User Story 2 - 嵌套调用能还原调用树 (Priority: P2)

**Goal**: `current_span()` 返回上下文内最内层 span；模型 / 工具子 span 的 `parent` 正确；
离开内层恢复外层；空上下文返回 `None`；跨 compiled graph 嵌套按 FR-021 独立 / 屏蔽。

**Independent Test**: 节点内 `invoke_model` / `invoke_tool` 产生子 span；断言 `parent ==` 直接父级
`id`；`current_span()` 内层 → 外层 → `None`；内层 compiled graph 未注入 ⇒ 0 span。

### Tests for User Story 2

- [X] T023 [P] [US2] Write `tests/observability/test_b19f1_current_span.py`: nested model → tool → model; assert `parent` chain, `current_span()` inner / outer / `None`, no exception outside any span.
- [X] T024 [P] [US2] Write `tests/runtime/test_b19f1_nested_scope.py`: outer **B19F1** tracer + inner `compile()` / `compile(tracer=None)` ⇒ inner span 0 / record 0（不隐式继承）；outer + inner `compile(tracer=sink2)` ⇒ inner run_id differs, inner top-level `parent is None`; reentrant `invoke()` restores the outer scope on exit; **每次注入运行的 `RunIdBindingCounter` 恰为 1**（L3 优先、L2 fallback 不重复）. **回归 1：B18F1 直接绑定（`direct_bind_producer`）在 B19F1 作用域外 + `compile()`（无 tracer）⇒ 既有 span 仍产生（不触发屏蔽）**. **回归 2：B19F1 作用域内再做 B18F1 直接绑定 + `compile()`（无 tracer）⇒ 按 FR-021 被屏蔽（B19F1 作用域优先）**。
- [X] T025 [P] [US2] Write `tests/observability/test_b19f1_callback_span.py`: inside `on_span_start` ⇒ new span; inside `on_trace_record` ⇒ node span; inside `on_span_end` ⇒ parent / `None`; event order `start → record → end`.

### Implementation for User Story 2

- [X] T026 [US2] Export `current_span()` **and `TraceRecord`** from `src/freegraph/observability/__init__.py`; `current_span()` reads `current_tracer()` and returns `producer.current_span()` or `None`; add both to `__all__`; do not export via `freegraph.graph`.
- [X] T027 [US2] Implement **only nested masking** in `src/freegraph/_stategraph.py`: if `_tracer is None` and `current_span_tracer()` is not `None`, **局部 import L5 `_inject`** and read `b19f1_scope_active()`; if true, enter `trace_run_scope(None)`（**B19F1 作用域优先**：即使外层另有 B18F1 直接绑定也屏蔽）；if false（作用域外的 B18F1 direct binding），**do not mask**. If `_tracer is None` and `current_span_tracer()` is `None`, **skip the L5 import entirely**. **MUST NOT** re-enter scope for `_tracer is not None`（T019 / T020 own that）；cover both `invoke()` and `stream()`；MUST 调用 T031 的共享守卫，不得另写判断。
- [X] T028 [US2] Add `tests/contracts/test_b19f1_lazy.py`: `import freegraph` loads only `freegraph`; `freegraph.graph` does not export `current_span`; `current_span` is importable from `freegraph.observability`; L5 import is lazy when no tracer / no outer tracer; **`trace_run_scope` 不出现在 `freegraph.observability.__all__`（内部入口）**.

**Checkpoint**: US2 is independently testable; nested parent chain + `current_span()` + cross-graph independence work.

---

## Phase 5: User Story 3 - 不注入就完全没这回事 (Priority: P1)

**Goal**: 未注入（或 `tracer=None`）⇒ 零 span / 零 producer / 零记录 / 零 id / 零回调；
环境变量存在也不改变行为；依赖闭包仍为空；`import freegraph` 仍惰性。

**Independent Test**: 不传 `tracer`，运行同一张图；断言 `Span` / `SpanProducer` 构造数 == 0、
回调数 == 0、`bind_run_ids` 调用数 == 0；设 `LANGSMITH_TRACING=true` 后不变；
`import freegraph` 的 `sys.modules` 不含 L5 / `opentelemetry` / `langchain*` / `langsmith`。

### Tests for User Story 3

- [X] T029 [P] [US3] Write `tests/observability/test_b19f1_default_off.py`: no tracer / explicit `None`，**且无任何外层 tracer**；assert span construction 0, **producer construction 0（用 `SpanProducerConstructionCounter`）**, record count 0, callback count 0, `bind_run_ids` 0（**counter 必须覆盖 `_stategraph.bind_run_ids` 新调用点；本任务用 `invoke()` 断言，不把 `stream()` 既有 `_STREAM_RUN_ID` 计入**）; `compile()` and `compile(tracer=None)` are byte-for-byte equivalent in observable behavior; **另测 `compile(tracer=sink)` 但从不运行 ⇒ 0 span / 0 回调 / 0 `run_id` 绑定**.
- [X] T030 [P] [US3] Write `tests/contracts/test_b19f1_gates.py`: `LANGSMITH_TRACING=true` / `LANGCHAIN_TRACING_V2=true` / arbitrary `LANGSMITH_*` do not change behavior; dependency closure still empty; no `opentelemetry` / `langchain*` / `langsmith` imports; no env reads; no egress in the new modules.

### Implementation for User Story 3

- [X] T032 [US3] Verify signature headers, module docstrings, and forbidden-import hygiene in `src/freegraph/observability/_record.py`, `_inject.py`, `_producer.py`, `__init__.py`, `src/freegraph/runtime/_span_hook.py`; run G4 / G24 / G26 / G27 and record the result in T001.

**Checkpoint**: US3 is independently functional; default-off is measurable and includes nested masking.

---

## Phase 6: Downstream Trace Records (Cross-Cutting · FR-011…FR-015)

**Goal**: 每节点任务一条补充记录，经可选 `on_trace_record` 推送；含触发源（静态边 / goto /
fan-out）、并发组、屏障组、输入 / 输出 / 错误；JSON 安全降级；与 span 一一对齐；确定性顺序。

**Independent Test**: 混合图（静态边 + `goto` + `Send` + 多源汇合）注入 `RecordSink`；
断言 `record 数 == 节点 span 数`、三类触发源都出现、并发组 / 屏障组正确、
`json.dumps(record.to_jsonable())` 不抛、中断 / 取消对齐。

### Tests for Phase 6

- [X] T033 [P] Write `tests/observability/test_b19f1_record.py`: all `TraceRecord` fields; `span_id` / `task_id`（standard = node; fan-out = `node:TaskId`）; `run_id` / `thread_id` / `checkpoint_id` match the span; `input_state` complete; **`output_state` == 节点原始返回值（raw return）**（归一 `writes` / `gotos` / `fanout` 不作为 `output_state`）; `json.dumps(record.to_jsonable())` serializes; `error` remains the original exception object（若原异常有 `add_note`，notes 仍可读）。
- [X] T034 [P] Write `tests/observability/test_b19f1_json_safe.py`: plain scalars / dict / list / tuple preserved; **dict 非 `str` key 先确定字符串化**；set sorted; bytes / object / cycle → deterministic placeholders; same input ⇒ same output; no object content leaks.
- [X] T035 [P] Write `tests/runtime/test_b19f1_alignment.py`: `record 数 == 节点 span 数`; **sink 实现 `on_trace_record` 时** event order `start → record → end`; interrupt ⇒ `error` is the original `GraphInterrupt`; **node-raised cancellation (`CancelledError`) ⇒ record with the original cancellation/exception**; never-started cancelled task ⇒ no span / no record; `on_trace_record` exception is isolated（使用 `FailingRecordSink`，只让 record 回调抛异常）。
- [X] T036 [P] Write `tests/runtime/test_b19f1_triggers.py`: static edge + `Command.goto` + `Send` fan-out all appear; no goto-only / static-only case; trigger identifiers `("e", source)` / `("send", producer, index)`; **断言 `triggers` 字段按统一键 `(kind, source, index)` 排序（标准项 `index = -1`）、重复运行逐字一致；不断言 sink 到达顺序**。
- [X] T037 [P] Write `tests/runtime/test_b19f1_concurrency_barrier.py`: same super-step ⇒ same `concurrency_group`; standard tasks by node-name order, fan-out by **numeric** TaskId order; **dispatched-but-never-started cancelled tasks are in the group but have no record**; multi-source `[a, b] → c` ⇒ `barrier_groups == (("a","b"),)`; cross-round grouping == 0; **cross-task span parent count == 0**（复用 B18F1 的每任务 ContextVar 隔离）；**不断言记录到达顺序**。
- [X] T038 [P] Write `tests/runtime/test_b19f1_invoke_records.py`: `invoke()` **and `stream()`** per-node `(node, input_state, output_state, error)`; input keys preserved; **`output_state` == 节点原始返回值（raw return）**; normalized `writes` / `gotos` / `fanout` only as a scheduler-side assertion; no `Span` field / attribute changes. **`stream()` 同样断言 `record 数 == 节点 span 数`，每条记录的 `span_id` == 对应节点 span 的 `id`；不要求到达顺序**。

### Implementation for Phase 6

- [X] T039 Implement L2 payload capture in `src/freegraph/runtime/superstep.py` `_run_round._bind._inner`: add **`_execute_node_pure_with_raw(...) -> tuple[dict[str, Any], Any]`**（`normalized, raw`）；`_bind._inner` 解包后把 `normalized` 返回给 `_worker`，把 `raw` 用于 `output_state`. After execution returns / raises and **before** `end_node_span`, only when **`start is not None` AND `getattr(tracer, "wants_trace_records", False)` is true**, build the payload via `build_trace_payload(...)` and call `getattr(tracer, "on_trace_record", None)`; **do not** build payload / capture input-output when the receiver lacks `on_trace_record`（该情形 MUST 走原 `_execute_node_pure` 路径）; do not touch `node_input` / scheduler return value / `SuperStepResult`.
- [X] T040 Implement standard trigger extraction in `src/freegraph/runtime/superstep.py`: reuse `_satisfied_groups(...)` from `_run_round`; union group members ⇒ `("e", source)`; deduplicate; sort by unified key `(kind, source, index)` with standard edge / `goto` using `index = -1`. Do not re-run trigger determination. **与 T041 同文件：MUST 串行，不得并行。**
- [X] T041 Implement fan-out trigger + concurrency/barrier metadata in `src/freegraph/runtime/superstep.py`: keep `producer` / `index` in `fanout_pending`; build `("send", producer, index)`; `superstep = state.step`; `concurrency_group` in dispatch order（标准节点名序 + fan-out **数值** TaskId 序）；`barrier_groups` from satisfied multi-source groups. **与 T040 同文件：MUST 串行，不得并行。**
- [X] T042 Implement interrupt / cancellation alignment in `src/freegraph/runtime/superstep.py` + `src/freegraph/runtime/_span_hook.py`: `GraphInterrupt` and **node-raised cancellation (`CancelledError`)** keep the original object in `error`; never-started（运行期取消只发生在这里）tasks produce no record; `record 数 == 节点 span 数`。
- [X] T043 Integrate JSON-safe degradation + deterministic ordering in `src/freegraph/observability/_record.py` / `_producer.py`: `input_state` / `output_state` go through `json_safe`; `triggers` / `concurrency_group` / `barrier_groups` are deterministic; `error` bypasses `json_safe`.

**Checkpoint**: Phase 6 records are complete; all downstream obligations FR-011…FR-015 / SC-008…SC-017 are testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 差分、冻结面、层门禁、快照、文档、人工验收、全量回归。

- [X] T044 [P] Write `tests/differential/test_b19f1_trace_access_parity.py`: D-301…D-310 per [contracts/upstream-parity.md](./contracts/upstream-parity.md) §3; upstream absent ⇒ skip (use the existing differential fixture / skip discipline).
- [X] T045 [P] Write `tests/contracts/test_b19f1_contracts.py`: `Span` 11 fields / `TraceSink` 3 methods / `RunConfig` 9 fields / `SuperStepResult` / `PregelTask` unchanged; `freegraph.graph.__all__ == 8`; `freegraph.contracts.__all__` == 22; `freegraph.runtime.__all__` unchanged; **`vars(compiled)` == 12（含 `_tracer`）**; `Span.context` stays empty and does not carry C21 `context`; **`SpanOnlySink` 不静态满足 `TraceSink` 但运行期可注入**（FR-001/FR-006 的有意差异）；**接收端隔离仅覆盖 `Exception`**（FR-017）。
- [X] T046 [P] Run the architecture / layer gates **as the final recheck**: `tests/contracts/test_architecture.py`, `harness/scripts/gates/gate_G25_import_graph.py`; confirm **R-1 is the only new G25/layer-registry allowance**（`_stategraph.py` → `observability/_inject.py` only）；R-2 / R-3 are covered by the architecture-test exception split（`_inject.py` → `_span_hook` only）；no other L3 → L5 / L5 → L2 private edges.
- [X] T047 [P] **Final recheck** of the API snapshot after T021: `tests/facade/test_api_snapshot.py` + `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt` against `src/freegraph/_stategraph.py`; confirm `compile()` no-arg still works and the only signature delta is keyword-only `tracer`.
- [X] T049 [P] Run the full regression `.venv/bin/python -m pytest -q --tb=no`; record the actual output in `harness/verification/B19F1/manual-verification.md` §1.1 / §4; compare with baseline `1863 passed, 6 skipped`.
- [X] T050 [P] Re-check the plan's red list **B-1…B-9** one by one in `harness/verification/B19F1/manual-verification.md` §5; fix or register any deviation. Also re-check the 2026-11-21 analysis fixes **I1 / I2 / I3 / A1 / G1 / T1 / T2**（定义见 `spec.md` 的「分析修复记录」与 `plan.md` 的 Post-Design Re-check）、second-round fixes **P-10 / D-309 · R-2 收窄 · SC-010 / SC-012 / FR-010 测试 · 取消语义 · 可选 payload · baseline 1863 · 序号 24**、third-round fixes **I1 直接绑定保留 / K1 一次性追认 / K2 门禁5偏离 / S1 A6+A7 / D1 T017 / A1 字段顺序 / P1 D-310+X-5 / G1 计数器 / A4 stream 计数**、fourth-round fixes **X1 R-6 收窄 / X2 run-id fallback / T1 T031 前移 / A1 排序键 / U1 raw 承载 / T2 命名 / A2 Exception 隔离 / A3 类型差异 / A4 作用域优先 / G1–G3**; do not leave a red gate unexplained.
- [X] T051 [P] Verify `THIRD_PARTY_NOTICES` / `pyproject.toml` / `harness/demo/target.py` are unchanged; record `git diff --exit-code` output.
- [X] T052 [P] Final acceptance audit in `harness/verification/B19F1/manual-verification.md`: map SC-001…SC-017 to executing tests; confirm no `[NEEDS CLARIFICATION]`, no TODO, no out-of-scope implementation (B20 / B21 / UI); confirm **质量门禁 5 偏离已登记**；write the audit into the same file. **T048 finalizes after this task.**
- [X] T048 Finalize `harness/verification/B19F1/manual-verification.md` (**final consolidator · MUST run after T049 / T050 / T052**): fake round（本地真实 `Sink` / `Model` / `Tool`）、local real sink round、零出站证据（socket 监测夹具，框架出站 == 0）、**R-1/R-2/R-3 一次性追认文字（确认人 + 日期）**、**B8F2 R-6 已收窄为「L2 读取 stream id，B19F1 从节点 span 继承」**、**质量门禁 5 偏离登记（确认人 + 日期）**、遗留问题（`checkpoint_id` 仍 `None`、跨图统一树留 v2）。

**Checkpoint**: All tasks complete; full regression green; manual verification signed; R-1/R-2/R-3 approved; gate 5 deviation registered.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖，可立即开始。
- **Foundational (Phase 2)**: 依赖 Setup；**阻塞** US1 / US2 / US3 / Phase 6。
- **US1 (Phase 3)**: 依赖 Foundational（T006–T011）；内部顺序 **T018 → T031 → T019/T020**；可独立测试。
- **US2 (Phase 4)**: 依赖 Foundational + US1（run scope / `_tracer`）；可独立测试。
- **US3 (Phase 5)**: 依赖 Foundational + US1（需要 `compile(tracer=None)` 路径）；可独立测试。
- **Phase 6 (CC)**: 依赖 Foundational + US1（记录经同一 sink 推送）；可独立测试。
- **Polish (Phase 7)**: 依赖所有目标阶段完成。

### User Story Dependencies

- **US1 (P1 · MVP)**：含 T018 / T031 / T019 / T020；是 US2 / US3 / Phase 6 的接线前提。
- **US2 (P2)**：依赖 US1 的 `_tracer` / run scope；但 `current_span()` 的单测可用合成栈独立验证。
- **US3 (P1)**：与 US1 的 `compile(tracer=None)` 路径共用；但零开销 / env / 依赖门禁可独立验证。
- **Phase 6 (CC)**：依赖 US1 的 sink 推送；触发源 / 并发组 / 屏障组可用 L2 夹具独立验证。

### Within Each Phase

- 测试先写并**先失败**；再实现；测试通过后进入下一任务。
- Foundational 的模型 / 类型（T006 / T010）先于 producer / L2 采集（T007 → T008 / T011）；
  T007 与 T008 **同文件**（`_producer.py`），MUST 顺序执行。
- US1 的 `compile()`（T018）先于共享守卫（T031），T031 再先于 invoke / stream scope（T019 / T020）。
- Phase 6 的 L2 payload（T039）先于 trigger / concurrency / barrier（T040 / T041 / T042）。
- Polish 的差分 / 契约 / 门禁 / 审计可并行；T049（全量回归）/ T050（红名单）/ T052（审计）
  先于 T048（最终 consolidator）。

---

## Parallel Opportunities

- **Setup**：T003 / T004 / T005 可并行（不同文件 / 只读检查）。
- **Foundational**：T006 / T007 / T010 / T012 / T013 可并行（不同文件 / 不同测试）；
  **T008 依赖 T007（同文件 `_producer.py`）**；T009 依赖 T006 / T008；T011 依赖 T010；
  T014 依赖 T013。
- **US1**：T015 / T016 / T017 可并行（不同测试文件）；T018 → T031 → T019 / T020。
- **US2**：T023 / T024 / T025 可并行；T026 先于 T027 / T028。
- **US3**：T029 / T030 / T032 可并行；**T031 已在 US1 阶段完成**。
- **Phase 6**：T033…T038 可并行（不同测试文件）；T039…T043 按 T039 → **T040 → T041（同文件，必须串行）** → T042/T043 顺序。
- **Polish**：T044…T047 / T051 / T052 可并行；T049 / T050 / T052 先于 T048（最终 consolidator）。

### Parallel Example: US1

```bash
Task: "Write basic push tests in tests/observability/test_b19f1_push.py"
Task: "Write exception push tests in tests/observability/test_b19f1_exception.py"
Task: "Write stream push tests in tests/observability/test_b19f1_stream.py"
```

### Parallel Example: Phase 6

```bash
Task: "Write TraceRecord field tests in tests/observability/test_b19f1_record.py"
Task: "Write json_safe tests in tests/observability/test_b19f1_json_safe.py"
Task: "Write trigger-source tests in tests/runtime/test_b19f1_triggers.py"
Task: "Write concurrency/barrier tests in tests/runtime/test_b19f1_concurrency_barrier.py"
```

---

## Implementation Strategy

### MVP First（US1 + US3 · 两个 P1）

1. 完成 Phase 1 Setup。
2. 完成 Phase 2 Foundational。
3. 完成 Phase 3 US1（T031 共享守卫 + 推送 + 成对 + 流式 id）。
4. 完成 Phase 5 US3（默认关闭 + 环境变量 + 依赖门禁）。
5. **STOP and VALIDATE**：US1 + US3 独立可测 ⇒ 这是最小可交付切片。

> US2（嵌套 / `current_span()`）与 Phase 6（补充记录）是第二个增量；它们不阻塞 MVP。

### Full Acceptance（US1 + US2 + US3；US2 为 P2）

1. Setup + Foundational。
2. US1 → T031 共享守卫 / 推送 / 成对 / 异常 / 流式。
3. US2 → `current_span()` / 嵌套父链 / 跨图屏蔽。
4. US3 → 默认关闭 / env / 依赖门禁。
5. Phase 6 → 记录 / 触发源 / 并发组 / 屏障组 / 中断取消。
6. **STOP and VALIDATE**：三层能力 + 默认关闭 + 记录全绿。

### Incremental Delivery

1. Setup + Foundational → 记录类型 / run scope / L2 payload / fixtures / 门禁 ready。
2. US1 → 共享守卫 + 最小推送（MVP 的一半）。
3. US3 → 默认关闭（MVP 的另一半）。
4. US2 → 嵌套 / `current_span()`。
5. Phase 6 → 下游补充记录。
6. Polish → 差分 / 冻结面 / 快照 / 文档 / 人工验收 / 全量回归。

### Parallel Team Strategy

- **Foundational**：A 做 `_record.py`；B 做 `_producer.py`；C 做 `_inject.py` / L2 payload；
  D 做 fixtures / architecture test / layer registry。
- **After Foundational**：
  - A：US1（`compile` / T031 共享守卫 / invoke / stream）。
  - T018 + T031 完成后，B 与 C 可并行：
    - B：US3（默认关闭 / env / 依赖门禁）。
    - C：US2（`current_span` / 嵌套屏蔽）。
- **After US1**：D 做 Phase 6（记录 / 触发源 / 并发组 / 屏障组）。
- **Polish**：E 做差分 / 契约 / 快照；F 做人工验证 / 全量回归。

---

## Notes

- [P] = 不同文件、无未完成依赖。
- [Story] 标签映射到 spec 的 US1 / US2 / US3；Phase 6 / Polish 为跨切面，不带故事标签。
- 每个任务都必须有精确文件路径；测试任务先写并先失败。
- 冻结面：`Span` 11 字段 / `TraceSink` 3 方法 / `RunConfig` 9 字段 / `SuperStepResult` /
  `PregelTask` / `stream()` 信封 / 门面 8 符号 / L1 22 符号 / `runtime.__all__` **零改动**。
- R-1（L3 → L5）/ R-2（L5 → L2 `_span_hook` 双绑定）/ R-3（B18F1 断言拆分）
  **已获发起者一次性追认（2026-11-21）**；由 T014 / T046 落地；T048 记录追认文字（确认人 + 日期）；
  **MUST NOT** 扩展为例外通行证，**MUST NOT** 把 `_stream_context` 纳入 R-2。
- 不新增运行时依赖；`harness/demo/target.py` 零改动；`THIRD_PARTY_NOTICES` 零变更。
- **T048 编号虽小，但它是最终 consolidator**：执行顺序以「T048 MUST run after T049 / T050 / T052」为准。
- 人工验证：`harness/verification/B19F1/manual-verification.md`（fake + 本地真实 sink + 零出站证据 + R-1/R-2/R-3 追认 + 门禁 5 偏离登记）。
