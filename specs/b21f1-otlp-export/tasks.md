---

description: "Task list for B21F1 · OTLP 导出插件（可选 extra）+ 后端对接文档"
---

# Tasks: B21F1 · OTLP 导出插件（可选 extra）+ 后端对接文档

**Input**: Design documents from `/specs/b21f1-otlp-export/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: **包含**。spec 定义了 SC-001…SC-015，且项目宪法原则 VI 要求「判据级可追溯」；
每个用户故事先写失败测试，再实现，再跑定向回归；Phase 8 补契约 / 门禁 / 差分 / 验收 /
人工记录；Phase 9 补 SC-010 文档守卫与最终审计。

**Organization**: 任务按用户故事分组；US1–US5 可独立实现 / 测试 / 交付。
Phase 8（契约 / 门禁 / 差分 / 验收 / 人工）与 Phase 9（覆盖闭包 / 文档守卫 / 审计）
为跨切面。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: `US1` / `US2` / `US3` / `US4` / `US5`；Setup / Foundational / Phase 8 / Phase 9 不带故事标签
- 每个任务都带**精确文件路径**或**精确命令 / 测试文件**

---

## 追溯表（FR → 任务）

| FR | 任务 |
|---|---|
| FR-001 | T005 / T038 / T042 |
| FR-002 | T005 / T038 |
| FR-003 | T006 / T007 / T011 / T038 / T042 |
| FR-004 | T005 / T006 / T007 / T008 / T009 / T011 |
| FR-005 | T005 / T038 |
| FR-006 | T024 / T026 / T027 |
| FR-007 | T020 / T037 / T042 |
| FR-008 | T024 / T026 / T027 |
| FR-009 | T020 / T037 |
| FR-010 | T019 / T024 |
| FR-011 | T020 / T021 / T022 / T037 |
| FR-012 | T015 / T020 / T023 |
| FR-013 | T016 / T020 / T037 |
| FR-014 | T020 / T037 |
| FR-015 | T024 |
| FR-016 | T014 / T015 / T017 / T037 |
| FR-017 | T015 / T017 / T038 |
| FR-018 | T014 / T017 |
| FR-019 | T014 / T017 |
| FR-020 | T015 / T017 |
| FR-021 | T015 / T017 |
| FR-022 | T015 / T017 |
| FR-023 | T019 / T037 / T038 |
| FR-024 | T016 / T038 / T039 |
| FR-025 | T028 / T029 / T030 |
| FR-026 | T028 / T029 / T030 |
| FR-027 | T028 / T029 |
| FR-028 | T020 / T028 / T029 |
| FR-029 | T028 / T029 / T030 |
| FR-030 | T031 / T032 / T033 / T034 / T035 / T036 |
| FR-031 | T032 / T033 / T034 |
| FR-032 | T003 / T035 / T046 / T050 |
| FR-033 | T032 / T033 / T034 / T035 / T038 |
| FR-034 | T033 / T034 / T035 |
| FR-035 | T016 / T020 / T021 / T025 / T026 / T027 |
| FR-036 | T006 / T038 / T042 |
| FR-037 | T035 / T038 |
| FR-038 | T019 / T037 / T038 |
| FR-039 | T037 / T042 |
| FR-040 | T001 / T044 / T049 / T050 / T051 / T052 / T054 |
| FR-041 | T011 / T040 / T046 |

## 追溯表（SC → 任务）

| SC | 任务 |
|---|---|
| SC-001 | T018 / T019 / T023 / T044 |
| SC-002 | T024 / T026 / T027 |
| SC-003 | T028 / T029 / T030 |
| SC-004 | T031 / T032 / T033 / T034 / T035 / T036 / T051 |
| SC-005 | T005 / T006 / T007 / T011 / T038 / T042 |
| SC-006 | T024 / T027 |
| SC-007 | T014 / T015 / T017 / T023 |
| SC-008 | T038 / T039 / T042 |
| SC-009 | T003 / T035 / T046 / T050 |
| SC-010 | T001 / T050 / T052 / T054 |
| SC-011 | T020 / T037 / T042 |
| SC-012 | T016 / T020 / T028 / T029 / T030 |
| SC-013 | T019 / T037 / T038 |
| SC-014 | T043 / T055 |
| SC-015 | T035 / T044 / T051 |

## 追溯表（Task → spec）

| Task | Maps to |
|---|---|
| T001 | FR-040 / SC-010（人工记录骨架） |
| T002 | 基线 / 原则 VI |
| T003 | 原则 VIII / XI / FR-032 / SC-009（来源 + as-of） |
| T004 | 原则 III（`target.py` 只读） |
| T005 | FR-001 / FR-002 / FR-004 / FR-005 / SC-005（extra） |
| T006 | FR-003 / FR-004 / FR-036 / SC-005（G3） |
| T007 | FR-003 / FR-004 / SC-005（G23 归一） |
| T008 | FR-004 / SC-005 / SC-008（G26） |
| T009 | FR-035 / FR-036 / SC-005 / SC-008（B19F1 import 例外） |
| T010 | FR-001 / FR-004 / SC-005（CI 安装） |
| T011 | FR-003 / FR-004 / FR-041 / SC-005（归属） |
| T012 | 测试夹具（映射 / 导出） |
| T013 | FR-040 / SC-010 / SC-015（B25F1 承接） |
| T014 | FR-016 / FR-018 / FR-019 / SC-007（身份 / 时间） |
| T015 | FR-012 / FR-016 / FR-017 / FR-020…FR-022 / SC-007 |
| T016 | FR-013 / FR-024 / SC-001 / SC-008 / SC-012 |
| T017 | FR-016…FR-022 / SC-007 / US1 定向 |
| T018 | FR-010 / FR-024 / SC-001 / SC-012 / US1 传输 |
| T019 | FR-010 / FR-011 / FR-012 / FR-023 / SC-001 / US1 注入 |
| T020 | FR-007 / FR-009 / FR-011 / FR-013 / FR-014 / FR-028 / SC-011 |
| T021 | FR-011 / FR-035 / SC-002 |
| T022 | FR-011 / FR-035 / SC-002（公开面 / 惰性） |
| T023 | SC-001 / SC-007 / US1 回归 |
| T024 | FR-006 / FR-008 / FR-010 / FR-015 / SC-002 / SC-006 |
| T025 | FR-035 / SC-002（惰性 / 门禁） |
| T026 | FR-006 / FR-008 / FR-035 / SC-002 / SC-006 |
| T027 | SC-002 / SC-006 / US2 回归 |
| T028 | FR-025…FR-029 / SC-003 / SC-012 |
| T029 | FR-025…FR-029 / SC-003 / SC-012 |
| T030 | SC-003 / US3 回归 |
| T031 | FR-030 / FR-032 / FR-033 / SC-004 / SC-009 |
| T032 | FR-030 / FR-031 / FR-033 / SC-004 |
| T033 | FR-030 / FR-031 / FR-034 / SC-004 |
| T034 | FR-030 / FR-031 / FR-034 / SC-004 |
| T035 | FR-030 / FR-032…FR-034 / SC-004 / SC-009 / SC-015 |
| T036 | SC-004 / US4 回归 |
| T037 | FR-007 / FR-011 / FR-014 / FR-016 / FR-023 / FR-038 / FR-039 / SC-011 / SC-013 |
| T038 | FR-003 / FR-017 / FR-023 / FR-024 / FR-033 / FR-036…FR-038 / SC-005 / SC-008 / SC-013 |
| T039 | FR-024 / SC-008（无自研编码） |
| T040 | FR-041 / SC-009（README） |
| T041 | FR-004 / 原则 VI（spec §6 核对登记） |
| T042 | SC-005 / SC-008 / SC-011 / SC-014 |
| T043 | 原则 XI / D-601…D-608 / X-1…X-5 / SC-014 |
| T044 | FR-040 / SC-001 / SC-004 / SC-015（一键验收） |
| T045 | SC-010 / SC-014（验收守卫） |
| T046 | FR-032 / FR-041 / SC-009（记录行） |
| T047 | G3 / G21 / G23 / G24 / G26 / G27 / SC-005 |
| T048 | quickstart / SC-001…SC-015 |
| T049 | 全量回归 / 原则 VI |
| T050 | FR-040 / SC-009 / SC-010 |
| T051 | SC-004 / SC-015（真实后端冒烟） |
| T052 | FR-040 / SC-010 / 质量门禁 5 / 治理追认（finalize） |
| T053 | 原则 III / 冻结面只读 |
| T054 | SC-010（文档守卫） |
| T055 | SC-014 / 原则 VI / 最终审计 |
| T056 | 全量回归 / 基线不下降 |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 记录基线、建立人工记录骨架、完成 extra / 许可证 / 门禁 / CI / 归属的前置接线；
零行为改动。

- [X] T001 Create `harness/verification/B21F1/manual-verification.md` with the five-section skeleton（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）and a `§1.1 基线` placeholder; create the `harness/verification/B21F1/` directory. T050/T052 finalize the record; T054 is the final document guard.
- [X] T002 Run the real full baseline `.venv/bin/python -m pytest -q --tb=no` and record passed / skipped / failed / elapsed in `harness/verification/B21F1/manual-verification.md` §1.1（2026-11-24 expected: `2345 passed, 10 skipped`；elapsed 以本机为准）.
- [X] T003 [P] Re-check upstream anchors and backend sources: `langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`; Phoenix `https://arize.com/docs/phoenix`; OpenLIT `https://docs.openlit.io/latest/overview` + `https://github.com/openlit/openlit`（旧 `openlit.io/docs` 404）; Langfuse `https://langfuse.com/docs` + `https://langfuse.com/self-hosting`; update `contracts/upstream-parity.md` / `contracts/backend-examples-contract.md` only if a source or line anchor drifted. Record as-of dates.
- [X] T004 [P] Confirm `harness/demo/target.py` and the frozen contract files are untouched: run `git diff --exit-code -- harness/demo/target.py src/freegraph/contracts/trace.py src/freegraph/contracts/protocols.py`; record the result in `harness/verification/B21F1/manual-verification.md` §1.1.
- [X] T005 Add `[project.optional-dependencies].otlp` to `pyproject.toml` with **exactly** `opentelemetry-api>=1.20`, `opentelemetry-sdk>=1.20`, `opentelemetry-exporter-otlp-proto-grpc>=1.20`; keep `dependencies = []`; update the `full_install` marker description to「全部 extras（含 `otlp`）」; update the surrounding `pyproject.toml` comment（当前写「本文件不含 `[project.optional-dependencies]`」）to record the **宪法 v1.17.0 `[otlp]` 唯一具名例外**. Add the same `otlp` entry to `specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml` and extend its `closed_closure` with the 7 new package names; add a comment that `otlp` is the **v1.0 named exception**, not a fifth v2.0 extra. **MUST NOT** add the meta-package / HTTP exporter / `requests` / `certifi`.
- [X] T006 [P] Update `tests/contracts/test_architecture.py::CONSTITUTION_DEPENDENCY_WHITELIST` (12 → 19) by adding `opentelemetry-exporter-otlp-proto-grpc`, `opentelemetry-exporter-otlp-proto-common`, `opentelemetry-exporter-otlp-common`, `opentelemetry-proto`, `googleapis-common-protos`, `grpcio`, `protobuf`; keep the existing 12 names byte-for-byte.
- [X] T007 Implement the G23 named normalization in `harness/scripts/gates/_gatekit.py` + `harness/scripts/gates/gate_G23_licenses.py` + `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md`: **only** `protobuf` + identifier `3-Clause BSD License` → `BSD-3-Clause`; **MUST NOT** add a general prose→SPDX table, family heuristics, or whitelist relaxation. Record the protobuf LICENSE evidence in the gate docstring / contract.
- [X] T008 Update G26 in `harness/scripts/gates/_gatekit.py` + `harness/scripts/gates/gate_G26_network_static.py`: add `grpc` to the network-client list and `freegraph.observability._otlp_transport` to `G26_EXCEPTED_MODULES`; keep the scan domain `src/freegraph/**` unchanged; **MUST NOT** add default-path exceptions. Depends on T007 (same `_gatekit.py`).
- [X] T009 Update `tests/contracts/test_b19f1_gates.py` + `tests/contracts/test_architecture.py` for the named OTLP exception: allow `opentelemetry` / `grpc` **only** in `_otlp_mapping.py` / `_otlp_transport.py` / `_otlp_exporter.py`; keep `langchain*` / `langsmith` / `langgraph*` forbidden everywhere; add the 3 new files to `SIGNED_SOURCE_FILES` and the L5 scan paths. **MUST NOT** relax default-path zero-egress assertions. This task changes **only** the allowlist / signed-file / scan-path declarations; runtime lazy-assertion coverage is added by T025（不要在此重复）. Depends on T006.
- [X] T010 [P] Update `.github/workflows/ci.yml` step 5.5 to install `opentelemetry-exporter-otlp-proto-grpc>=1.20`（or `.[otlp]`）on all 7 jobs; update `specs/b3f1-scaffold-ci-gates/contracts/ci-matrix.md`; keep the `pyproject.toml` marker edit in T005.
- [X] T011 [P] Update `THIRD_PARTY_NOTICES`: add a separate `[otlp]` entry with the 11-package closure and licenses; annotate `protobuf` as `BSD-3-Clause` with the prose metadata normalized; explicitly state `certifi` / HTTP exporter are **not** in `[otlp]`.
- [X] T012 [P] Add reusable B21F1 helpers to `tests/observability/conftest.py`: `make_span(...)`（`Span` 11 fields with `run_id` / `thread_id` / `node` / `checkpoint_id`), `make_model_span(...)`, `make_tool_span(...)`, `RecordingSpanExporter`（captures `ReadableSpan`s; returns `SpanExportResult.SUCCESS`), `assert_readable_span(...)`; keep existing B18F1 / B19F1 / B20F1 / B20F2 fixtures unchanged.
- [X] T013 [P] Wire / verify the B21F1 downstream clause in `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B21F1）」: it MUST require OTLP export evidence in the real-model round; confirm `spec.md` / `plan.md` references resolve. **Blocking**: MUST pass before T052 sign-off.

**Checkpoint**: Baseline recorded; extra / license / gate / CI / attribution wiring done; manual skeleton exists; B25F1 clause in place; no behavioural change.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 建立纯映射 / gRPC 传输 / 官方编码边界。**⚠️ CRITICAL**：本阶段完成前，
US1 / US3 / US5 的实现不开始；US2 / US4 的测试可先写但会失败。

- [X] T014 Implement `src/freegraph/observability/_otlp_mapping.py` identity / time layer: `trace_id = sha256(b"freegraph:run:" + run_id.encode("utf-8")).digest()[:16]`, `span_id = sha256(b"freegraph:span:" + id.encode("utf-8")).digest()[:8]`, `SpanContext(..., is_remote=False, trace_flags=TraceFlags(TraceFlags.SAMPLED))`; parse `start_time` / `end_time` via `freegraph.observability._time.parse_iso_ns`; `end_time is None` ⇒ no export; invalid / empty `id` / empty `run_id` ⇒ skip + diagnostic reason; `end < start` ⇒ clamp to start + WARNING. Add source header + module docstring.
- [X] T015 Implement `src/freegraph/observability/_otlp_mapping.py` assembly layer (depends T014): build `ReadableSpan(name, context, parent, resource=Resource({"service.name": "freegraph"}), attributes, kind, status, start_time, end_time, instrumentation_scope=InstrumentationScope("freegraph", __version__))`; attributes = `Span.attributes` direct map + derived `gen_ai.conversation.id` from `thread_id` only when absent; value normalization (`str`/`bool`/`int`/`float`/`bytes`/homogeneous scalar sequences pass; `None` → `"null"`; others → `json.dumps(..., ensure_ascii=False, sort_keys=True)` then `str`); `error.type` ⇒ `Status(StatusCode.ERROR, str(value))`, else `UNSET`; `SpanKind.CLIENT` iff `gen_ai.operation.name` ∈ {`chat`, `execute_tool`} else `INTERNAL`; `context` / `checkpoint_id` / `node` / `TraceRecord` not exported; no `freegraph.*` prefix. Add source header + docstring.
- [X] T016 [P] Implement `src/freegraph/observability/_otlp_transport.py`: `encode_spans([readable])` + `TraceServiceStub`; short-lived `grpc.insecure_channel(endpoint)` when `insecure=True` else `grpc.secure_channel(endpoint, grpc.ssl_channel_credentials())`; `stub.Export(request, metadata=tuple(headers.items()), timeout=timeout or 10.0)`; `finally: channel.close()`; **no** `OTLPSpanExporter` facade, **no** env reads, **no** retry, **no** background thread. Add source header + docstring.

**Checkpoint**: Mapping and transport are frozen; official `encode_spans` + official stubs are the only encoding path.

---

## Phase 3: User Story 1 - 接进我现有的 OTel 栈 (Priority: P1) 🎯 MVP

**Goal**: 显式传入端点 / 导出器后，`compile(tracer=OtlpExporter(...))` 把节点 / 模型 / 工具 span
导出到 OTLP；最小 gRPC 接收端可解析；图结果不变。

**Independent Test**: 启动最小 gRPC 接收端；`OtlpExporter(endpoint="127.0.0.1:<port>", insecure=True)`；
运行两节点图；断言接收端收到完整 span（name / ids / times / attributes / parent / trace）；
图返回预期状态。

### Tests for User Story 1

- [X] T017 [P] [US1] Write `tests/observability/test_b21f1_mapping.py`: 11-field mapping; same `run_id` ⇒ same `trace_id`; different `run_id` ⇒ different; node / model / tool `SpanKind`; `error.type` status; `thread_id` → `gen_ai.conversation.id`（已有同名键不覆盖）; `context` / `checkpoint_id` / `node` not exported; empty id / run_id / bad time ⇒ skip; `end < start` ⇒ clamp; nested dict / list / None / non-str-key attributes; non-ASCII / newline / control characters; `parent` missing / empty ⇒ root span; duplicate `id` not deduped; empty graph ⇒ no span / no export; Resource `service.name == "freegraph"`; `InstrumentationScope("freegraph", __version__)`; `TraceFlags.SAMPLED`; no `freegraph.*` prefix; time nanosecond precision.
- [X] T018 [P] [US1] Write `tests/observability/test_b21f1_transport.py`: minimal gRPC `TraceServiceServicer` on `127.0.0.1:0`; `OtlpExporter(endpoint=..., insecure=True)`; run `a → b` graph; assert received `ExportTraceServiceRequest` span count / names / trace_id / parent / attributes; assert no env reads and no retry (one request per span). Mark `@pytest.mark.linux_only` + `@pytest.mark.full_install`.
- [X] T019 [P] [US1] Write `tests/observability/test_b21f1_export.py` basic path: `compile(tracer=OtlpExporter(exporter=RecordingSpanExporter()))`; node span + model span + tool span; `on_span_start` no-op; `on_span_end` with `end_time=None` no-op; graph result equals no-export run; `TraceRecord` is not exported; `query()` not called.

### Implementation for User Story 1

- [X] T020 [US1] Implement `src/freegraph/observability/_otlp_exporter.py` public class: add the constitution principle X source header + module docstring; constructor validation (exactly one of `endpoint` / `exporter`; `endpoint` non-empty `host:port` without `http://` / `https://`, port 1–65535, IPv6 bracket allowed; `insecure` bool; `headers` mapping of `str`→`str`; `timeout` positive; `on_error` callable or `None`; `insecure=True` / `headers` / `timeout` + `exporter=` ⇒ `ValueError`; missing extra / OTel SDK + `endpoint=` **or** `exporter=` ⇒ `ImportError` with `pip install freegraph[otlp]`); state `_endpoint` / `_exporter` / `_insecure` / `_headers` / `_timeout` / `_on_error` / `_lock` / `_export_errors` / `_last_error`; read-only properties; `on_span_start` no-op; `on_span_end` uses mapping + transport / user exporter; `current_span()` returns `None`; no `close()` / context manager. `BaseException` is never passed to `on_error`. Depends T014–T016.
- [X] T021 [US1] Update `src/freegraph/observability/__init__.py`: import `OtlpExporter` from `._otlp_exporter` and append to `__all__`; update module docstring; keep the existing 7 symbols and `trace_run_scope` non-export unchanged; **MUST NOT** export it from `freegraph.graph` / `freegraph.runtime.__all__`.
- [X] T022 [US1] Update `tests/facade/test_api_snapshot.py::test_observability_module_exports_only_its_own_symbols` exact set to add `OtlpExporter`; update `tests/contracts/test_b19f1_lazy.py` to assert `OtlpExporter` in `observability.__all__` and still absent from `freegraph.graph`. **只增不改**.
- [X] T023 [US1] Run `.venv/bin/python -m pytest tests/observability/test_b21f1_mapping.py tests/observability/test_b21f1_transport.py tests/observability/test_b21f1_export.py tests/facade/test_api_snapshot.py tests/contracts/test_b19f1_lazy.py -q`; fix US1 failures; do not weaken assertions.

**Checkpoint**: US1 is independently functional; endpoint / exporter mode both export; minimal gRPC receiver parses OTLP.

---

## Phase 4: User Story 2 - 不导出时零负担 (Priority: P1)

**Goal**: 未安装 extra / 未传 tracer 时，零 OTel import、零出站、零 env、零行为变化；
`import freegraph.observability` 也不加载 OTel / grpc。

**Independent Test**: 基础安装（无 `[otlp]`）不传 `tracer` 运行图；断言 `sys.modules` 无
`opentelemetry` / `grpc`、框架出站 == 0；设置 `OTEL_*` / `LANGSMITH_*` 行为不变。

### Tests for User Story 2

- [X] T024 [P] [US2] Write `tests/observability/test_b21f1_default_off.py`: subprocess `import freegraph.observability` ⇒ `OtlpExporter` in `__all__`, `opentelemetry` / `grpc` not in `sys.modules`; run graph without tracer ⇒ no export / no egress; `OTEL_EXPORTER_OTLP_ENDPOINT` / `OTEL_*` / `LANGSMITH_*` set ⇒ behavior unchanged; installed extra but no `OtlpExporter` construction ⇒ zero export; **simulate missing `[otlp]`**（隔离子进程 / import blocker）⇒ graph succeeds, no OTel / grpc import, zero egress; `endpoint=` or `exporter=` with missing extra / OTel SDK ⇒ `ImportError` only when explicitly constructing; `exporter=` + `headers` / `timeout` ⇒ `ValueError` with zero egress.
- [X] T025 [P] [US2] Extend `tests/contracts/test_b19f1_gates.py` + `tests/contracts/test_architecture.py` with the runtime lazy assertions required by the named exception: only the 3 OTLP modules may import `opentelemetry` / `grpc`; default path zero egress; other L5 modules unchanged. This task adds **only** runtime lazy / default-path assertions; do not duplicate T009's allowlist / signed-file edits. Depends T009.

### Implementation for User Story 2

- [X] T026 [US2] Enforce lazy imports in `src/freegraph/observability/_otlp_exporter.py`: top level imports **only** stdlib + `freegraph.contracts.trace.Span` + `._time`; `_otlp_mapping` / `_otlp_transport` are imported inside `__init__` / `on_span_end`; `import freegraph.observability` must not import `opentelemetry` / `grpc`. Validate no module-level `os.environ` / `os.getenv` anywhere.
- [X] T027 [US2] Run `.venv/bin/python -m pytest tests/observability/test_b21f1_default_off.py tests/contracts/test_b19f1_lazy.py tests/contracts/test_b19f1_gates.py -q`; fix lazy / zero-egress defects.

**Checkpoint**: US2 is independently functional; not using OTel is truly zero-burden.

---

## Phase 5: User Story 3 - 导出失败不阻断运行 (Priority: P1)

**Goal**: 端点不可达 / 编码失败 / 用户 exporter 抛错 / `on_error` 抛错都不阻断图执行；
四路诊断可感知；`BaseException` 不吞；不重试；并发安全。

**Independent Test**: 传入不可达端点，运行图；断言图成功、`export_errors > 0`、`last_error`
非空、WARNING 出现；用户 exporter / `on_error` 抛 `Exception` 同样隔离；`KeyboardInterrupt`
/ `SystemExit` 不被吞。

### Tests for User Story 3

- [X] T028 [P] [US3] Write `tests/observability/test_b21f1_failure.py`: unreachable endpoint; fake exporter raises `Exception`; fake exporter returns `SpanExportResult.FAILURE`; `on_error` raises `Exception`; `BaseException` propagates; no retry (export call count == span count); graph result equals no-export run; concurrent node completions with one shared exporter; empty graph / no span produced ⇒ no export; process exit after synchronous export ⇒ no pending thread / flush; `export_errors` / `last_error` semantics（success does not clear `last_error`）.

### Implementation for User Story 3

- [X] T029 [US3] Implement failure isolation / diagnostics in `src/freegraph/observability/_otlp_exporter.py`: per-instance `threading.Lock` around mapping + export; `export_errors +1` for every complete span not successfully exported (mapping skip / transport exception / `SpanExportResult.FAILURE`); `last_error` retains most recent failure (success does not clear); optional `on_error` called outside lock, its `Exception` caught + WARNING, original error preserved; `BaseException` not swallowed; `logging.WARNING`; no retry / no circuit breaker. Depends T020.
- [X] T030 [US3] Run `.venv/bin/python -m pytest tests/observability/test_b21f1_failure.py -q`; fix failure-isolation defects; verify graph result / node sequence / stream events unchanged.

**Checkpoint**: US3 is independently functional; export failures never block execution.

---

## Phase 6: User Story 4 - 三个后端的最小对接示例 (Priority: P2)

**Goal**: 交付 OpenLIT / Langfuse / Phoenix 三个并列示例；来源 + as-of + 分工表 +
已知风险；至少一个真实后端冒烟，其余可用桩接收端。

**Independent Test**: 三个示例文件存在且 `--help` 成功；README 含分工 / 重叠表、
来源 / as-of、旧路径 404、HTTP exporter 用户侧依赖、无默认推荐；至少一个真实后端冒烟。

### Tests for User Story 4

- [X] T031 [P] [US4] Write `tests/observability/test_b21f1_examples.py`: three files exist; each `python <script> --help` exits 0 **even when the user-side HTTP exporter is not installed**; missing HTTP exporter while running openlit / langfuse prints the install hint and exits non-zero (not silently); README contains「能力分工 / 重叠」+「无默认推荐」+「OpenLIT 旧路径 404」+「docs.openlit.io」+「as-of」+「HTTP exporter 用户侧依赖」+「Phoenix 只连不嵌」; scripts do not import `langchain` / `langsmith` / `langgraph`; scripts do not read `os.environ` / `os.getenv`; no default endpoint; the HTTP exporter import is deferred until after `argparse`.

### Implementation for User Story 4

- [X] T032 [P] [US4] Create `harness/examples/B21F1/phoenix.py`: self-contained `argparse`; `--endpoint 127.0.0.1:4317`; `OtlpExporter(endpoint=..., insecure=True)`; fake two-node graph + fake model / tool call; no env; no default endpoint; no langchain; prints exported count.
- [X] T033 [P] [US4] Create `harness/examples/B21F1/openlit.py`: self-contained `argparse`; `--endpoint http://127.0.0.1:4318/v1/traces`; user-installed `opentelemetry-exporter-otlp-proto-http` **imported lazily after `argparse`**（missing ⇒ print `pip install "opentelemetry-exporter-otlp-proto-http>=1.20"` and exit 2; `--help` never imports it）; `OtlpExporter(exporter=OTLPSpanExporter(endpoint=...))`; same fake graph; no env; no default endpoint.
- [X] T034 [P] [US4] Create `harness/examples/B21F1/langfuse.py`: self-contained `argparse`; `--endpoint http://localhost:3000/api/public/otel/v1/traces`; `--public-key` / `--secret-key` → Basic auth header; user-installed HTTP exporter **imported lazily after `argparse`**（missing ⇒ print `pip install "opentelemetry-exporter-otlp-proto-http>=1.20"` and exit 2; `--help` never imports it）; `OtlpExporter(exporter=...)`; same fake graph; no env; no default endpoint.
- [X] T035 [US4] Create `harness/examples/B21F1/README.md`: three backend sections with source + as-of; OpenLIT old 404 + current `https://docs.openlit.io/latest/overview`; Phoenix 4317 / gRPC / `insecure=True`; OpenLIT 4318 / HTTP; Langfuse HTTP + Basic auth; prerequisites; **能力分工 / 重叠表**; **三示例并列、无默认推荐**; HTTP exporter 用户侧依赖; known failure risks; Phoenix ELv2 只连不嵌.
- [X] T036 [US4] Run `.venv/bin/python -m pytest tests/observability/test_b21f1_examples.py -q` and manually `python harness/examples/B21F1/{phoenix,openlit,langfuse}.py --help`; confirm all three `--help` succeed **without** the user-side HTTP exporter installed, then install it and run a stub / real backend smoke; fix example defects.

**Checkpoint**: US4 is independently functional; examples are copy-runnable and documented.

---

## Phase 7: User Story 5 - 标准化而非私有格式 (Priority: P2)

**Goal**: freegraph 只以标准 OTLP 输出；不自研 protobuf / wire format；不内嵌
Phoenix / Langfuse / OpenLIT；基础安装闭包为空；`[otlp]` 只含白名单包。

**Independent Test**: 代码审查 + AST / 静态扫描无自研编码；依赖声明无 `langchain*` /
`langsmith` / `langgraph*` / Phoenix / Langfuse / OpenLIT；`[otlp]` 闭包无 `certifi`。

### Tests for User Story 5

- [X] T037 [P] [US5] Write `tests/contracts/test_b21f1_contracts.py`: `OtlpExporter` in `observability.__all__`, not in `freegraph.graph` / `freegraph.runtime.__all__`; no `close()` / `__enter__` / `__exit__` / public OTel object; `on_span_start` / `on_span_end` / `current_span`; `export_errors` / `last_error` read-only; constructor validation（exactly one of `endpoint` / `exporter`; `endpoint` scheme / port; `insecure` / `headers` / `timeout` + `exporter=` ⇒ `ValueError`; missing extra / OTel SDK + `endpoint=` or `exporter=` ⇒ `ImportError`）; `Span` 11 / `TraceSink` 3 / `TraceRecord` 13 / `TraceQuery` 5 / `RunConfig` 9 unchanged; no `TraceRecord` OTLP span; no B20F2 `query()` call; no schema / wire format leakage.
- [X] T038 [P] [US5] Write `tests/contracts/test_b21f1_gates.py`: `dependencies == []`; `[otlp]` closure ⊆ 19-name whitelist; no `certifi` / `requests` / `langchain*` / `langsmith` / `langgraph*`; `protobuf` normalized to `BSD-3-Clause`; G23 / G21 / G26 pass; G26 exception only `_otlp_transport.py`; `grpc` in network client list; no Phoenix / Langfuse / OpenLIT package; no env reads in `_otlp_exporter.py` / `_otlp_mapping.py` / `_otlp_transport.py`; no `freegraph.*` attributes.
- [X] T039 [US5] Add the no-self-encoding AST / static scan to `tests/contracts/test_b21f1_gates.py`: no hand-written protobuf encoder / OTLP wire format / gRPC payload encoding; only official `encode_spans` + official `TraceServiceStub`; no `OTLPSpanExporter` import in freegraph source; `TraceRecord` not referenced in mapping.

### Implementation for User Story 5

- [X] T040 [US5] Update `README.md`: add「可观测 / OTLP 导出」section with `pip install "freegraph[otlp]"`, endpoint / `insecure` / `exporter=` usage, three example links, capability division table, known risks, and「无默认推荐后端」; **MUST NOT** change unrelated API compatibility matrix rows.
- [X] T041 [US5] Verify `specs/b21f1-otlp-export/spec.md` §6 **already contains** the G23 `protobuf` named-normalization and B19F1 OTLP-module import-exception rows（本次修复已补）；如发现漂移，只补齐这两行，**不得**改 FR / SC 语义；在 `harness/verification/B21F1/manual-verification.md` 记录核对结果。
- [X] T042 [US5] Run `.venv/bin/python -m pytest tests/contracts/test_b21f1_contracts.py tests/contracts/test_b21f1_gates.py tests/contracts/test_architecture.py -q` + `python harness/scripts/gates/gate_G21_dependencies.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml` + `python harness/scripts/gates/gate_G23_licenses.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml`; fix contract / gate defects; **MUST NOT** relax assertions.

**Checkpoint**: US5 is independently functional; standard protocol only, no private encoding / embedding.

---

## Phase 8: Cross-Cutting Concerns

**Purpose**: 契约 / 门禁 / 差分 / 一键验收 / 人工记录 / 全量回归 / 真实后端冒烟。

- [X] T043 [P] Write `tests/differential/test_b21f1_otlp_parity.py`: D-601…D-608 per [contracts/upstream-parity.md](./contracts/upstream-parity.md) §4; upstream absent ⇒ `pytest.importorskip`; assert freegraph default-off / zero env / zero egress / failure isolation / no self-encoding; assert P↔X 三态一致（X-1…X-5）。
- [X] T044 [P] Create `harness/verification/B21F1/acceptance.py` for A1–A5: A1 dependency / no self-encoding; A2 three examples exist + `--help`; A3 docs markers; A4 default-off / zero egress; A5 stub exporter + minimal gRPC receiver; socket monitor; exit code `0` PASS / `1` FAIL / `2` env not ready; last line `B21F1 acceptance: PASS|FAIL`.
- [X] T045 Add `test_b21f1_one_click_acceptance_script_passes` to `tests/runtime/test_acceptance_script.py`; run `harness/verification/B21F1/acceptance.py` in a subprocess and assert exit code 0 + `B21F1 acceptance: PASS`. **Depends on T044**.
- [X] T046 [P] Update `harness/verification/README.md` with the B21F1 row linking `B21F1/manual-verification.md` / `B21F1/acceptance.py`; update `harness/demo/README.md` with the OTLP export entry / capabilities; keep existing rows verbatim.
- [X] T047 Run architecture / dependency / env / egress gates: `.venv/bin/python -m pytest tests/contracts/test_architecture.py tests/gates -q`, `python harness/scripts/gates/gate_G25_import_graph.py`, G21 / G23 / G24 / G26 / G27; record results in `harness/verification/B21F1/manual-verification.md` §1.1 / §4.
- [X] T048 Run the [quickstart.md](./quickstart.md) validation scenarios（安装 / A1 / A4 / A5 / 失败隔离 / 三示例 `--help` / 门禁）; fix only defects, do not weaken assertions.
- [X] T049 Run the full regression `.venv/bin/python -m pytest -q --tb=no`; record actual output in `harness/verification/B21F1/manual-verification.md` §1.1 / §4; compare with baseline `2345 passed, 10 skipped`（only add, never reduce）.
- [X] T050 Write the manual-verification body in `harness/verification/B21F1/manual-verification.md`: explicit endpoint export output; stub / minimal gRPC receiver evidence; default-off / zero-import / zero-egress evidence; unreachable endpoint / failure isolation evidence; three examples evidence; license normalization evidence; README / `__all__` updates.
- [X] T051 Real backend smoke（manual）: run at least one of Phoenix / OpenLIT / Langfuse per `harness/examples/B21F1/README.md`; record the actual output in `harness/verification/B21F1/manual-verification.md`; if the environment is unavailable, record the reason / stub-receiver substitute / pending verification item; **MUST NOT** silently downgrade or write stub evidence as a real backend result.
- [X] T052 Finalize `harness/verification/B21F1/manual-verification.md`（**MUST run after T049 / T050 / T051 / T013**）: add v1.17.0 named-exception ratification; G3 / G23 / G26 / B19F1 import-exception written ratifications（确认人 + 日期）; **质量门禁 5 偏离声明（真实模型轮由 B25F1 承接）**; 遗留问题（无 async / 无 UI / 无自托管后端 / `checkpoint_id` 不导出 / 无 `resource_attributes` 参数）.
- [X] T053 [P] Verify read-only / dependency files unchanged: `git diff --exit-code -- harness/demo/target.py src/freegraph/contracts/trace.py src/freegraph/contracts/protocols.py`; confirm `Span` / `TraceSink` / `TraceRecord` / `TraceQuery` / `RunConfig` / `compile()` signatures zero change; record the result in the manual record.

**Checkpoint**: Contracts / gates / differential / acceptance / manual record complete; real backend evidence or documented substitute.

---

## Phase 9: Coverage Closure & Final Document Guard

**Purpose**: 关闭 SC-010 的判定覆盖，最终审计 FR / SC、红名单与范围边界。

- [X] T054 Write `tests/runtime/test_b21f1_manual_record_guard.py` for **SC-010**: assert `harness/verification/B21F1/manual-verification.md` exists, has non-empty five-section structure, contains actual outputs for endpoint export + stub / minimal gRPC receiver + default-off / zero-import / zero-egress + failure isolation + three examples + **SC-015 real backend smoke** + license normalization + governance ratifications + **quality gate 5 deviation**; assert `harness/features/B25F1_双跑验收与迁移说明.md` contains §「下游承接（B21F1）」 with OTLP evidence; assert `README.md` / `harness/examples/B21F1/README.md` contain the required markers. **MUST run after T052 / T013**; MUST NOT be enabled before the record is written.
- [X] T055 Final audit in `harness/verification/B21F1/manual-verification.md`: map FR-001…FR-041 / SC-001…SC-015 to executing tasks/tests; re-check plan red list B-1…B-17; re-check P-01…P-07 ↔ X-1…X-5 三态一致; confirm T013 / T052 / T054 passed; confirm no unresolved clarification markers / no placeholders / no out-of-scope implementation（OTLP async / UI / Agent Server / self-hosted backend / DateTime / TraceRecord export / query API consumption / `resource_attributes`）; confirm G23 / G26 / B19F1 exceptions are named and minimal.
- [X] T056 Run the final full regression `.venv/bin/python -m pytest -q --tb=no`（含 T054 文档守卫）; record actual output in `harness/verification/B21F1/manual-verification.md` §4; confirm counts only increase and the B21F1 guard is green.

**Checkpoint**: All coverage gaps closed; SC-010 has a document guard; full regression green; manual verification signed; red list closed.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - **BLOCKS** US1 / US3 / US5 implementation;
  US2 / US4 tests may be written earlier but will fail until the public API exists.
- **US1 (Phase 3)**: Depends on Foundational (T014–T016).
- **US2 (Phase 4)**: Depends on US1 T020–T022 (public API exists); can run in parallel with US3 tests.
- **US3 (Phase 5)**: Depends on US1 T020–T022; shares `_otlp_exporter.py` with US2 (sequential implementation or coordinated edits).
- **US4 (Phase 6)**: Depends on US1 T020–T022 (examples use the public API); test T031 can be written earlier.
- **US5 (Phase 7)**: Depends on US1 T020–T022; dependency / gate tasks T005–T011 can run in Setup.
- **Phase 8**: Depends on all desired user stories.
- **Phase 9**: Depends on Phase 8 + T052 + T013.

### User Story Dependencies

- **US1 (P1)**: MVP core; no dependency on US2–US5.
- **US2 (P1)**: Needs the public symbol from US1; no dependency on US3–US5.
- **US3 (P1)**: Needs the public symbol from US1; no dependency on US2 / US4 / US5.
- **US4 (P2)**: Needs the public symbol from US1; can be developed after US1.
- **US5 (P2)**: Needs the public symbol from US1; dependency / license gates can be done in Setup.

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation.
- Mapping / transport before public API; public API before failure isolation / examples.
- Core implementation before integration / docs.
- Story complete before moving to next priority.

### Parallel Opportunities

- Setup: T003 / T004 / T006 / T010 / T011 / T012 / T013 can run in parallel after T001 / T002 / T005; T007 → T008 → T009 are sequential because they share `_gatekit.py` / `test_architecture.py`.
- Foundational: T014 → T015 sequential; T016 can run in parallel with T014 / T015.
- US1: T017 / T018 / T019 tests can run in parallel; T020 → T021 → T022 sequential; T023 after.
- US2 tests T024 / T025 can run in parallel; implementation T026 after US1 T020.
- US3 test T028 can be written in parallel with US2 tests; T029 after T020; T030 after.
- US4 T032 / T033 / T034 can run in parallel; T035 after; T031 can be written first; T036 after.
- US5 T037 / T038 can run in parallel; T039 after T038; T040 / T041 can run in parallel; T042 after.
- Phase 8 T043 / T044 / T046 / T053 can run in parallel; T045 after T044; T047–T052 sequential where evidence depends on each other; T051 manual.
- Phase 9 T054 after T052 / T013; T055 after T054; T056 after T055.

---

## Parallel Example: User Story 1

```bash
# Write the three US1 test files in parallel:
#   tests/observability/test_b21f1_mapping.py
#   tests/observability/test_b21f1_transport.py
#   tests/observability/test_b21f1_export.py

# Then implement sequentially:
#   _otlp_exporter.py → __init__.py → facade/lazy tests → targeted run
```

## Parallel Example: User Story 4

```bash
# Three example scripts can be authored in parallel:
#   harness/examples/B21F1/phoenix.py
#   harness/examples/B21F1/openlit.py
#   harness/examples/B21F1/langfuse.py

# Then write the README and run --help smoke.
```

---

## Implementation Strategy

### MVP First (P1 stories)

1. Complete Phase 1: Setup（governance / extra / gates / CI / attribution）。
2. Complete Phase 2: Foundational（mapping / transport）。
3. Complete US1（endpoint / exporter export）。
4. Complete US2（default-off / lazy import / zero env / zero egress）。
5. Complete US3（failure isolation / diagnostics / concurrency）。
6. **STOP and VALIDATE**: US1 + US2 + US3 are the non-negotiable P1 acceptance slices
   (原则 IV 的 MUST + 零出站 + 不阻断)。Only then add examples / standardization.

> 虽然模板通常把 US1 单独作为 MVP，本 feature 的 P1 包含 US1 / US2 / US3 三条；
> 砍掉 US2 或 US3 会分别弱化「零负担」与「不阻断执行」的宪法承诺，故 MVP 取三条 P1。

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → endpoint export works; validate with stub / minimal receiver.
3. US2 → default-off / lazy import green.
4. US3 → failure isolation green.
5. US4 → three backend examples + docs.
6. US5 → standardization / dependency / license gates.
7. Phase 8 → contracts / gates / differential / acceptance / manual.
8. Phase 9 → coverage closure / document guard / final regression.

### Parallel Team Strategy

- Developer A: Setup governance / gates / CI（T005–T011）。
- Developer B: Foundational mapping（T014–T015）。
- Developer C: Foundational transport（T016）。
- After T020: Developer A: US4 examples; Developer B: US3 failure; Developer C: US5 contracts/gates.
- Cross-cutting / manual: one owner for T043–T056 to keep evidence coherent.

---

## Notes

- **[P] tasks** = different files, no dependencies on incomplete tasks.
- **[Story] label** maps task to US1–US5 for traceability.
- **Tests are included** because spec SC-001…SC-015 + 宪法原则 VI require judged coverage.
- **MUST NOT** weaken assertions to make a task green; update with named exceptions only.
- **MUST NOT** add `certifi` / HTTP exporter to `[otlp]`; HTTP exporter is user-side only.
- **MUST NOT** use `OTLPSpanExporter` facade in freegraph source（env reads + internal retry）。
- **MUST NOT** use `Resource.create()`（env reads）；use `Resource({...})`.
- **MUST NOT** export `TraceRecord` / `context` / `checkpoint_id` / `node` in v1.
- **MUST NOT** consume B20F2 `query()`.
- **MUST NOT** embed Phoenix / Langfuse / OpenLIT.
- **MUST** complete governance written ratifications before T052 sign-off:
  v1.17.0 named exception; G3 whitelist expansion; G23 `protobuf` normalization;
  G26 / B19F1 import / egress exceptions; quality gate 5 deviation.
- `harness/demo/target.py` **零改动**（只读基准）。
- Full regression baseline: `2345 passed, 10 skipped`（2026-11-24）。
