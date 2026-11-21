---

description: "Task list for B20F1 · 本地 Trace 存储：JSONL 文件后端（零依赖）"
---

# Tasks: B20F1 · 本地 Trace 存储：JSONL 文件后端（零依赖）

**Input**: Design documents from `/specs/b20f1-local-trace-jsonl/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: **包含**。spec 定义了 SC-001…SC-019，且项目宪法原则 VI 要求「判据级可追溯」；
每个用户故事先写失败测试，再实现，再跑定向回归；Phase 9 补 SC-012 / SC-013 / SC-014 /
SC-015 与 span-only 的判定覆盖。

**Organization**: 任务按用户故事分组；US1–US4 可独立实现 / 测试 / 交付。
Phase 7（并发 / 权限 / 生命周期）、Phase 8（契约 / 差分 / 文档 / 验收）与
Phase 9（覆盖闭包 / 文档守卫）为跨切面。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: `US1` / `US2` / `US3` / `US4`；Setup / Foundational / Phase 7 / Phase 8 不带故事标签
- 每个任务都带**精确文件路径**或**精确命令 / 测试文件**

---

## 追溯表（FR → 任务）

| FR | 任务 |
|---|---|
| FR-001 | T006 / T007 / T013 / T014 / T035 |
| FR-002 | T011 / T013 / T017 / T018 |
| FR-003 | T011 / T012 / T013 / T035 / T052 |
| FR-004 | T036 / T039 / T042 |
| FR-005 | T026 / T027 / T039 |
| FR-006 | T006 / T007 / T026 |
| FR-007 | T020 / T022 / T023 / T025 / T039 |
| FR-008 | T036 / T042 |
| FR-009 | T011 / T012 / T014 |
| FR-010 | T006 / T015 / T035 |
| FR-011 | T029 / T031 / T032 |
| FR-012 | T009 / T035 / T036 |
| FR-013 | T035 / T045 |
| FR-014 | T014 / T024 / T026 / T050 |
| FR-015 | T011 / T013 / T020 |
| FR-016 | T013 / T035 |
| FR-017 | T038 / T045 / T053 |
| FR-018 | T001 / T044 / T048 / T049 / T053 |
| FR-019 | T012 / T015 |
| FR-020 | T011 / T012 / T017 |
| FR-021 | T006 / T022 |
| FR-022 | T006 / T026 / T027 |
| FR-023 | T011 / T014 |
| FR-024 | T014 / T032 / T051 |
| FR-025 | T030 / T032 |
| FR-026 | T030 / T032 / T033 |
| FR-027 | T029 / T031 |
| FR-028 | T021 / T023 / T039 |

## 追溯表（SC → 任务）

| SC | 任务 |
|---|---|
| SC-001 | T011 / T012 / T017 / T039 |
| SC-002 | T011 / T012 / T035 |
| SC-003 | T026 / T027 |
| SC-004 | T020 / T022 / T025 / T039 |
| SC-005 | T036 / T039 / T042 |
| SC-006 | T035 / T036 / T042 |
| SC-007 | T012 / T014 |
| SC-008 | T029 / T031 |
| SC-009 | T012 / T013 / T035 / T052 |
| SC-010 | T017 / T018 |
| SC-011 | T009 / T035 / T036 |
| SC-012 | T044（支撑）/ T048（支撑）/ T049（支撑·登记）/ T053（判定） |
| SC-013 | T038 / T045 / T053 |
| SC-014 | T050 |
| SC-015 | T030 / T032 / T051 |
| SC-016 | T030 / T032 |
| SC-017 | T030 / T033 |
| SC-018 | T029 / T031 |
| SC-019 | T021 / T023 |

> **T003 / T004 / T005 / T010 / T041 / T043 / T046 / T047** 是上游取证 / 只读检查 /
> 门禁 / 回归 / 审计（不单挂某条 FR/SC）。
> **T048** 写最终人工记录；**T049** 更新 `harness/verification/README.md`；
> **T050–T052** 补 SC-014 / SC-015 / span-only 判定测试；**T053** 是最终文档守卫
> （MUST 在 T048 / T049 之后执行）。
> **T035/T036** 同时覆盖冻结面与零依赖 / 零 env / 零出站门禁。

## 追溯表（Task → spec · 反向追溯）

| Task | Maps to |
|---|---|
| T001 | FR-018 / SC-012 |
| T002 | —（基线） |
| T003 | 原则 XI / P-01…P-07 |
| T004 | 门禁 3 / 原则 III |
| T005 | FR-001 |
| T006 | FR-001 / FR-006 / FR-010 / FR-021 / FR-022 |
| T007 | FR-001 / FR-006 / FR-010 / FR-012 |
| T008 | FR-012 / SC-011（冻结面） |
| T009 | FR-012 / SC-011（署名头 / 扫描） |
| T010 | —（测试夹具） |
| T011 | FR-002 / FR-003 / FR-005 / FR-009 / FR-015 / FR-019 / FR-020 / FR-023 / SC-001 / SC-002 / SC-007 / SC-009 / COV-04 |
| T012 | FR-003 / FR-009 / FR-019 / FR-020 / SC-001 / SC-002 / SC-007 / SC-009 |
| T013 | FR-001 / FR-002 / FR-003 / FR-015 / FR-016 / SC-002 / SC-009 |
| T014 | FR-001 / FR-009 / FR-014 / FR-023 / FR-024 / SC-007 |
| T015 | FR-010 / FR-019 / SC-001 / SC-009 |
| T016 | US1 定向回归 / SC-001 / SC-002 / SC-007 / SC-009 |
| T017 | FR-002 / FR-020 / SC-001 / SC-010 |
| T018 | FR-002 / SC-010 |
| T019 | US2 定向回归 / SC-010 |
| T020 | FR-007 / FR-015 / SC-004 |
| T021 | FR-028 / SC-019 |
| T022 | FR-007 / FR-021 / SC-004 |
| T023 | FR-011 / FR-028 / SC-004 / SC-019 |
| T024 | FR-014 / SC-014 |
| T025 | US3 定向回归 / SC-004 / SC-019 |
| T026 | FR-005 / FR-022 / SC-003 |
| T027 | FR-005 / FR-022 / SC-003 |
| T028 | US4 定向回归 / SC-003 |
| T029 | FR-011 / SC-008 / SC-018 |
| T030 | FR-011 / FR-025 / FR-026 / FR-027 / SC-016 / SC-017 / SC-018（含 Windows 分支） |
| T031 | FR-011 / FR-027 / SC-008 / SC-018 |
| T032 | FR-024 / FR-025 / FR-026 / FR-027 / SC-015 / SC-016 / SC-017 |
| T033 | FR-026 / SC-017 |
| T034 | 定向回归 / SC-008 / SC-016 / SC-017 / SC-018 |
| T035 | FR-001 / FR-010 / FR-012 / FR-013 / FR-016 / SC-002 / SC-006 / SC-009 / SC-011 |
| T036 | FR-004 / FR-008 / SC-005 / SC-006 / SC-011 |
| T037 | 原则 XI / D-401…D-408 |
| T038 | FR-017 / SC-013 |
| T039 | A1–A5 / FR-004 / FR-005 / FR-007 / FR-028 / SC-001 / SC-004 / SC-005 |
| T040 | 验收脚本守卫 / A1–A5 |
| T041 | 门禁 / 原则 VI / ARCH |
| T042 | 门禁 / FR-004 / FR-008 / SC-005 / SC-006 |
| T043 | 全量回归 / 基线 |
| T044 | FR-018 / 支撑 SC-012（判定由 T053） |
| T045 | 审计 / 全 FR/SC |
| T046 | 门禁 2 / 3 / SC-005 / SC-006 |
| T047 | quickstart / 验收 |
| T048 | FR-018 / 支撑 SC-012（判定由 T053）/ 质量门禁 5 |
| T049 | 支撑 SC-012（`harness/verification/README.md` 记录登记；判定由 T053） |
| T050 | FR-014 / SC-014 |
| T051 | FR-024 / SC-015 |
| T052 | FR-003 / SC-009（span-only） |
| T053 | FR-017 / FR-018 / SC-012 / SC-013 / 质量门禁 5 |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 记录基线、确认上游锚点、建立 L5 新模块骨架；零行为改动。

- [X] T001 Create `harness/verification/B20F1/manual-verification.md` with the five-section skeleton（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）and a `§1.1 基线` placeholder; create the `harness/verification/B20F1/` directory. T048 finalizes the manual record; T053 is the final document guard.
- [X] T002 Run the real full baseline `.venv/bin/python -m pytest -q --tb=no` and record passed / skipped / failed / elapsed in `harness/verification/B20F1/manual-verification.md` §1.1（2026-11-21 expected: `1917 passed, 6 skipped`；elapsed 以本机为准）.
- [X] T003 [P] Re-check upstream versions and anchors (`langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`) against `specs/b20f1-local-trace-jsonl/contracts/upstream-parity.md` §1/§2; update line numbers only if they drifted.
- [X] T004 [P] Confirm zero read-only / dependency changes: run `git diff --exit-code -- harness/demo/target.py pyproject.toml THIRD_PARTY_NOTICES`; report the result to T001 / T046.
- [X] T005 [P] Create `src/freegraph/observability/_file_store.py` skeleton with signature header, module docstring first, `from __future__ import annotations`, planned imports, and an empty `FileTraceStore` class body; no behavior.

**Checkpoint**: Baseline recorded; upstream anchors confirmed; L5 skeleton exists; no behavioural change.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 建立 `FileTraceStore` 的公开形态、导出、冻结面更新、测试夹具。
**⚠️ CRITICAL**: 本阶段完成前，US1 / US2 / US3 / US4 不开始。

- [X] T006 Implement the `FileTraceStore` skeleton in `src/freegraph/observability/_file_store.py` per [data-model.md](./data-model.md) §2: `__slots__` = `_directory` / `_on_error` / `_lock` / `_local` / `_write_errors` / `_last_error`; constructor `FileTraceStore(directory, *, on_error=None)` only stores `Path(directory)` / callback / creates `threading.Lock` + `threading.local` + diagnostics; **no filesystem access**; `write_errors` / `last_error` read-only properties (read under the lock); `on_span_start` / `on_span_end` / `on_trace_record` / `current_span` stubs (`on_span_start` no-op; `current_span` returns `None`).
- [X] T007 [P] Export `FileTraceStore` from `src/freegraph/observability/__init__.py`: import it and add to `__all__`; keep `SpanProducer` / `TraceRecord` / `current_span` / `invoke_model` / `invoke_tool` and `trace_run_scope` non-export unchanged; MUST NOT add it to `freegraph.graph`.
- [X] T008 [P] Update `tests/facade/test_api_snapshot.py`'s `test_observability_module_exports_only_its_own_symbols` exact set to add `FileTraceStore`; update `tests/contracts/test_b19f1_lazy.py` to assert `FileTraceStore` is in `observability.__all__` and `trace_run_scope` is still absent. **只增不改**.
- [X] T009 [P] Update `tests/contracts/test_architecture.py` `SIGNED_SOURCE_FILES` to append `src/freegraph/observability/_file_store.py`; update `tests/contracts/test_b19f1_gates.py` `paths` and `test_no_network_client_is_used_by_new_modules` to include `_file_store.py`. **只增不改**.
- [X] T010 [P] Add reusable B20F1 fixtures to `tests/observability/conftest.py`: `make_span(...)` (11 fields with a valid `run_id`), `make_record(...)` (13 fields; `error` optional), `read_jsonl(path)` (returns list of parsed dicts), `file_mode(path)` (POSIX mode or `None` on Windows). Keep existing B18F1 / B19F1 fixtures unchanged.

**Checkpoint**: `FileTraceStore` public shape / export / frozen-surface updates / fixtures are ready; no user-visible write behavior yet.

---

## Phase 3: User Story 1 - 跑完一次图，本机留下完整轨迹 (Priority: P1) 🎯 MVP

**Goal**: 注入 `FileTraceStore(directory=...)` 后，图运行生成 `trace-<run_id>.jsonl`；每个节点任务有 1 条 span 行 + 1 条 record 行；模型 / 工具 span 也落盘；异常路径仍落盘；同一 store 多次运行写多个文件。

**Independent Test**: `compile(tracer=FileTraceStore(directory=tmp))` 运行 `a → b`；断言 `tmp` 下恰好一个 `trace-<run_id>.jsonl`，含 2 条 span 行 + 2 条 record 行、字段关联正确；异常节点仍落盘；两次运行产生两个文件。

### Tests for User Story 1

- [X] T011 [P] [US1] Write `tests/observability/test_b20f1_store_unit.py`: directly feed synthetic `Span` / `TraceRecord` to `on_span_end` / `on_trace_record`; assert one file `trace-<run_id>.jsonl`; span 行含 `kind` + **11/11** `Span` 字段（`id` / `name` / `attributes` / `parent` / `start_time` / `end_time` / `context` / `thread_id` / `run_id` / `node` / `checkpoint_id`）；record 行含 `kind` + **13/13** `to_jsonable()` 字段；`on_span_start` writes nothing; `current_span()` is `None`; constructor does not create the directory; append across two events; two `run_id`s ⇒ two files; `record` before `span` when callbacks are in B19F1 order; **also cover the no-event case** (store receives no callbacks; v1 `StateGraph` rejects graphs with no nodes) and assert no file / no directory / no exception.
- [X] T012 [P] [US1] Write `tests/observability/test_b20f1_graph_integration.py`: compile `a → b` with `FileTraceStore`; `invoke(..., config=RunConfig(thread_id="t-1"))`; assert one file, 2 span + 2 record lines, `record.span_id` matches span `id`, `run_id` non-empty, `thread_id == "t-1"`, `node` / `checkpoint_id` readable; node with `invoke_model` / `invoke_tool` adds model / tool span lines whose `parent` is the node span `id`; exception node still writes span + record with `error == {"type": "RuntimeError", "message": "boom"}` and re-raises the same object; `stream()` path writes the same shape; two `invoke()` calls produce two files.

### Implementation for User Story 1

- [X] T013 [US1] Implement `_span_to_dict(span)` and `_record_to_dict(record)` in `src/freegraph/observability/_file_store.py`: manual 11-field span mapping (`kind` first; `attributes` / `context` via `dict(...)`; no `dataclasses.asdict`) and `{"kind": "trace_record", **record.to_jsonable()}`; MUST NOT rename fields or re-degrade record values.
- [X] T014 [US1] Implement `_write_event(payload)` / `_write_line(run_id, line)` in `src/freegraph/observability/_file_store.py`: validate `run_id` (`^[A-Za-z0-9][A-Za-z0-9_-]*$`, non-empty; **no dot**); build `Path(directory) / f"trace-{run_id}.jsonl"`; lazy `mkdir(parents=True, exist_ok=True)`; append the full line without truncating existing content; **permission `0o600` and fd leak-safe cleanup are finalized in T032**.
- [X] T015 [US1] Implement `on_span_start`（no-op）, `on_span_end`（span 行）, `on_trace_record`（record 行）, `current_span`（`None`）in `src/freegraph/observability/_file_store.py`; preserve B19F1 callback arrival order; same node record before span; different `run_id` ⇒ different file; no sorting / aggregation.
- [X] T016 [US1] Run `.venv/bin/python -m pytest tests/observability/test_b20f1_store_unit.py tests/observability/test_b20f1_graph_integration.py -q`; fix all US1 failures; do not weaken assertions.

**Checkpoint**: US1 is independently functional; `FileTraceStore` writes complete span + record lines; exception / model / tool / multi-run / stream paths covered.

---

## Phase 4: User Story 2 - 记录可被人与机器读取 (Priority: P2)

**Goal**: 文件是 UTF-8 / LF / 无 BOM / 无头部 / 一行一对象；中文 / 换行 / 控制字符正确转义；每行可独立 `json.loads`，可按 `kind` / `node` / `run_id` 过滤。

**Independent Test**: 逐行 `json.loads`；断言 `kind` 只允许 `"span"` / `"trace_record"`；含中文 / 换行的状态值读回无损；无空行 / 多行对象；`jq` 等价过滤得到预期条数。

### Tests for User Story 2

- [X] T017 [P] [US2] Write `tests/observability/test_b20f1_format.py`: assert file starts without BOM / header; every non-empty line is one JSON object; `set(obj) == SPAN_FIELDS` / `RECORD_FIELDS`; `kind` only two values; `ensure_ascii=False` keeps Chinese readable; newline / quote / control chars escape and do not split lines; `json.loads` success rate 100%; `record` line precedes its span line; `jq`-equivalent filtering by `kind` / `node` / `run_id` returns expected counts.

### Implementation for User Story 2

- [X] T018 [US2] Ensure `src/freegraph/observability/_file_store.py` uses `json.dumps(payload, ensure_ascii=False)`（默认分隔符 / 无 indent）、`newline="\n"`、`kind` 第一、无头部 / 尾随注释；non-ASCII / 换行由 `json.dumps` 转义；no extra normalization of `NaN` / `Infinity` beyond Python json.
- [X] T019 [US2] Run `.venv/bin/python -m pytest tests/observability/test_b20f1_format.py -q`; fix format failures; do not change the locked field sets.

**Checkpoint**: US2 is independently testable; the file is human-readable and machine-parseable.

---

## Phase 5: User Story 3 - 写入失败不阻断，但我不被蒙在鼓里 (Priority: P2)

**Goal**: 目录不可写 / 路径是文件 / 序列化失败 / flush 失败时，图仍成功；`write_errors` / `last_error` / `on_error` / `logging.WARNING` 四路可感知；不重试；不留下半行。

**Independent Test**: `directory` 指向只读目录或普通文件；运行同一张图；断言运行结果与不注入时逐字相同、无异常逃逸；`write_errors > 0`、`last_error` 非空、`on_error` 被调用、日志有 WARNING；文件中半行数 == 0。

### Tests for User Story 3

- [X] T020 [P] [US3] Write `tests/observability/test_b20f1_failure.py`: readonly directory（POSIX chmod 0o500；Windows 用路径是普通文件）、directory path is a file、serialization failure（`Span.attributes` contains `object()`）; assert graph still returns, no exception escapes, `write_errors > 0`, `last_error` contains `Type: message`, `on_error` receives the original exception, `caplog` has WARNING, no partial line / previous valid line preserved.
- [X] T021 [P] [US3] Write `tests/observability/test_b20f1_no_retry.py`: monkeypatch the first write attempt to fail then succeed; call `on_span_end` once; assert attempt count == 1, `write_errors == 1`, no `sleep` / retry, subsequent line succeeds; simulate a partial write and assert `os.truncate` restores the pre-write size; assert `BaseException` (e.g. `KeyboardInterrupt`) is **not** swallowed.

### Implementation for User Story 3

- [X] T022 [US3] Implement `_report(exc)` in `src/freegraph/observability/_file_store.py`: `message = f"{type(exc).__name__}: {exc}"`; under the instance lock increment `_write_errors` and set `_last_error`; `logging.getLogger(__name__).warning("trace write failed: %s", message, exc_info=exc)`; call `on_error(exc)` **outside** the lock; use `threading.local` (`in_on_error`) to suppress recursive callback; swallow `Exception` from `on_error` with a warning; do **not** swallow `BaseException`.
- [X] T023 [US3] Implement truncation / no-retry in `src/freegraph/observability/_file_store.py`: capture `path.stat().st_size` before `os.open` (0 if missing); on any write / flush / close `Exception`, call `os.truncate(path, before)` best-effort; if truncation fails, log only; **MUST NOT** retry the same line; subsequent lines still attempt.
- [X] T024 [US3] Implement unsafe / empty `run_id` rejection in `src/freegraph/observability/_file_store.py` using the T014 allowlist (`^[A-Za-z0-9][A-Za-z0-9_-]*$`): raise a `ValueError` internally, catch in `_write_event`, call `_report`, do not create a file / directory, do not fake a new id; ensure `write_errors` increments and run continues.
- [X] T025 [US3] Run `.venv/bin/python -m pytest tests/observability/test_b20f1_failure.py tests/observability/test_b20f1_no_retry.py -q`; fix all failure-path defects.

**Checkpoint**: US3 is independently functional; failures are non-blocking and observable; no half-lines or retries.

---

## Phase 6: User Story 4 - 不启用时完全不留痕迹 (Priority: P3)

**Goal**: 未注入 / `tracer=None` / 只构造 store 不运行 / 存在环境变量 ⇒ 零文件 / 零目录 / 零副作用。

**Independent Test**: 不注入 tracer（或 `compile(tracer=None)`）运行图；断言目标目录 0 新文件 / 0 新目录；只构造 `FileTraceStore` 不运行也零新增；设置 `FREEGRAPH_TRACE_DIR` / `LANGSMITH_TRACING` 后行为不变。

### Tests for User Story 4

- [X] T026 [P] [US4] Write `tests/observability/test_b20f1_default_off.py`: no tracer / `compile(tracer=None)` / `compile(tracer=FileTraceStore(...))` without running; assert 0 files / 0 directories in the target; `monkeypatch.setenv("FREEGRAPH_TRACE_DIR", ...)` / `LANGSMITH_TRACING=true` / `LANGCHAIN_TRACING_V2=true` do not create files when not injected; injected store ignores env and uses only explicit `directory`.

### Implementation for User Story 4

- [X] T027 [US4] Verify and enforce constructor / export defaults in `src/freegraph/observability/_file_store.py` + `src/freegraph/observability/__init__.py`: constructor only stores params / lock / diagnostics; no `mkdir` / `open` / env; no module-level default store; no `freegraph.graph` export; `import freegraph` still does not load L5.
- [X] T028 [US4] Run `.venv/bin/python -m pytest tests/observability/test_b20f1_default_off.py -q`; fix default-off defects.

**Checkpoint**: US4 is independently functional; no injected store ⇒ no trace artifacts.

---

## Phase 7: Cross-Cutting Write Semantics（并发 / 权限 / 生命周期）

**Goal**: 每个 store 实例一把锁；同实例多线程串行且每行完整；不同实例互不阻塞；POSIX 新建文件 `0o600`；每行独立 `open → append → flush → close`；无 `close()` / 上下文管理器 / 持久句柄 / 句柄泄漏。

- [X] T029 [P] Write `tests/observability/test_b20f1_concurrency.py`: `ThreadPoolExecutor` writes N records to the same store; assert N lines, all `json.loads` valid, no byte interleaving / half line; different store instances have distinct locks (`store_a._lock is not store_b._lock`) and both write; `on_error` re-enters the store and writes a valid line; assert no deadlock and `write_errors` not double-counted.
- [X] T030 [P] Write `tests/observability/test_b20f1_permissions.py`: on POSIX assert new `trace-<run_id>.jsonl` has `mode & 0o077 == 0`; assert `not hasattr(store, "close")` / `not hasattr(store, "__enter__")` / `not hasattr(store, "__exit__")`; after each callback the file can be renamed / deleted (Windows catches residual handles); `os.fdopen` / close call count == line count via monkeypatch; existing file mode is not broadened; on Windows assert a path-as-file / permission failure does **not** block execution (SC-016 Windows branch).
- [X] T031 Implement per-instance locking in `src/freegraph/observability/_file_store.py`: serialize JSON outside the lock; under the lock do the write critical section + `_write_errors` / `_last_error` update; call `on_error` outside; keep `_lock` per instance (no module global / no per-run lock table); use `_local.in_on_error` for reentry suppression.
- [X] T032 Implement per-line lifecycle + permission in `src/freegraph/observability/_file_store.py`: `os.open(..., 0o600)` for new files; `os.fdopen(fd, "a", encoding="utf-8", newline="\n")`; `write` + `flush` + `close` inside the lock; fd leak-safe cleanup if `os.fdopen` raises; no persistent handle; no `fsync`; no chmod of existing files.
- [X] T033 Implement the no-lifecycle API in `src/freegraph/observability/_file_store.py`: no `close()` / `__enter__` / `__exit__`; no `__del__`; every callback returns with no open trace handle; same store can be reused across runs without cleanup.
- [X] T034 Run `.venv/bin/python -m pytest tests/observability/test_b20f1_concurrency.py tests/observability/test_b20f1_permissions.py -q`; fix concurrency / permission / fd defects.

**Checkpoint**: Cross-cutting write semantics are complete: per-instance lock, 0o600, per-line handle, no leaks.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 契约 / 门禁 / 差分 / README / 一键验收 / 人工验证 / 全量回归。

- [X] T035 [P] Write `tests/contracts/test_b20f1_contracts.py`: `FileTraceStore` in `freegraph.observability.__all__`; not in `freegraph.graph.__all__` / `freegraph.runtime.__all__`; public face has `write_errors` / `last_error` / 3 sink callbacks / `current_span` but **no** `close` / `__enter__` / `__exit__` / query methods; `Span` 11 / `TraceRecord` 13 / `TraceSink` 3 / `RunConfig` 9 / `SuperStepResult` / `PregelTask` unchanged; `_file_store.py` imports only standard library + L1 `Span` + same-layer `TraceRecord`; no L2 / L3 / L4 import.
- [X] T036 [P] Write `tests/contracts/test_b20f1_gates.py`: no `langchain*` / `langgraph*` / `langsmith` / `opentelemetry*` import; no `sqlite3`; no env reads (`os.environ` / `getenv` / `environb`); no `socket` / `http` / `urllib` / `requests` / `httpx`; signature header + module docstring; dependency closure still empty.
- [X] T037 [P] Write `tests/differential/test_b20f1_local_trace_parity.py`: D-401…D-408 per [contracts/upstream-parity.md](./contracts/upstream-parity.md) §3; upstream absent ⇒ `pytest.importorskip`.
- [X] T038 [P] Update `harness/demo/README.md`: change the 「本地 trace 存储目录的参数名」 row from「待锁定」to「已锁定（B20F1）：`FileTraceStore(directory=...)`」, cite `specs/b20f1-local-trace-jsonl/spec.md` §「形态锁定裁定」; do not add `diagnostics.py` yet.
- [X] T039 [P] Create `harness/verification/B20F1/acceptance.py` (A1–A5): A1 trace 落盘；A2 socket 监测「框架出站 == 0」；A3 逐行 `json.loads` + C23 四项；A4 只读目录运行成功 + 四路诊断 + 无半行；A5 未注入 / 只构造 / env 变量零痕迹. 退出码 `0` PASS / `1` FAIL / `2` 环境未就绪；最后一行 `B20F1 acceptance: PASS|FAIL`.
- [X] T040 [P] Add `test_b20f1_one_click_acceptance_script_passes` to `tests/runtime/test_acceptance_script.py`; run `harness/verification/B20F1/acceptance.py` in a subprocess and assert exit code 0 + `B20F1 acceptance: PASS`.
- [X] T041 [P] Run architecture / layer gates: `.venv/bin/python -m pytest tests/contracts/test_architecture.py tests/gates -q` and `.venv/bin/python harness/scripts/gates/gate_G25_import_graph.py`; confirm no new L3 → L5 / L5 → L2 edges and `_file_store.py` is L5-only.
- [X] T042 Run dependency / env / egress gates: G21 / G24 / G26 / G27 via `.venv/bin/python -m pytest tests/gates -q` and the relevant scripts; record the result in `harness/verification/B20F1/manual-verification.md` §1.1 / §4.
- [X] T043 Run the full regression `.venv/bin/python -m pytest -q --tb=no`; record actual output in `harness/verification/B20F1/manual-verification.md` §1.1 / §4; compare with baseline `1917 passed, 6 skipped`（only add, never reduce）.
- [X] T044 Update `harness/verification/B20F1/manual-verification.md` with: real JSONL sample lines; `jq` / `json.loads` read-back output; failure perception evidence（`write_errors` / `last_error` / `on_error` / WARNING）; zero-egress evidence; `observability.__all__` exact-set follow-up（只增 `FileTraceStore`）; README locked-row evidence.
- [X] T045 Final audit in `harness/verification/B20F1/manual-verification.md`: map FR-001…FR-028 / SC-001…SC-019 to executing tasks/tests; re-check plan red list B-1…B-11; confirm no 未决澄清标记、no 未完成占位、no out-of-scope implementation (query / SQLite / OTLP / UI / retention); confirm `harness/demo/README.md` row is locked, `harness/verification/README.md` has the B20F1 row, and **质量门禁 5 偏离** is registered.
- [X] T046 [P] Verify read-only / dependency files unchanged: `git diff --exit-code -- harness/demo/target.py pyproject.toml THIRD_PARTY_NOTICES specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`; record the result.
- [X] T047 [P] Run the [quickstart.md](./quickstart.md) validation scenarios against `src/freegraph/observability/_file_store.py`; fix only defects, do not weaken assertions.
- [X] T048 Finalize `harness/verification/B20F1/manual-verification.md`（**final manual record · MUST run after T043 / T044 / T045**）：确认 JSONL 样例 / 读回证据 / 失败感知 / 零出站 / `__all__` 追认 / README 锁定记录 / **质量门禁 5 偏离声明（真实模型轮由 B25F1 承接）** / **发起者追认文字（确认人 + 日期，由发起者本人签署）** / 遗留问题（`checkpoint_id` 仍可能 `None`；无查询 API；无保留期）。

---

## Phase 9: Coverage Closure & Final Document Guard

**Purpose**: 关闭 SC-012 / SC-013 / SC-014 / SC-015 的判定覆盖缺口，并补「接收端不含 `on_trace_record`」的 span-only 适配器测试。

- [X] T049 Update `harness/verification/README.md`: add the **B20F1** row in the「当前已有记录」table, linking `B20F1/manual-verification.md` and `B20F1/acceptance.py`; mirror the B19F1 row style (status / pytest count / A1–A5 / gate 5 deviation).
- [X] T050 [P] Write `tests/observability/test_b20f1_run_id_safety.py` for **SC-014**: empty `run_id`, `/`, `\`, `.`, `..`, `a.b`, `a..b`, and a path-like `run_id`; assert 0 files / 0 directories created, `write_errors` +1 per rejected line, `last_error` non-empty, no traversal; assert a safe `uuid4().hex`-style id is accepted; assert `~` / `$HOME` in `directory` are **not** expanded and env vars do not participate.
- [X] T051 [P] Write `tests/observability/test_b20f1_flush_durability.py` for **SC-015**: monkeypatch `os.fsync` and assert call count == 0; write a line in a subprocess then `os._exit(0)`; parent reads the file back and every line **`json.loads` succeeds**; assert no `fsync` / no retry.
- [X] T052 [P] Write `tests/observability/test_b20f1_span_only.py` for **INC-01**: build a minimal **span-only adapter** that forwards `on_span_start` / `on_span_end` to `FileTraceStore` and implements `current_span_id() -> None`; bind the **adapter** directly to B18F1 `bind_span_tracer` (not through B19F1 `compile(tracer=...)`), so `on_trace_record` is **not** invoked; assert span lines are written, `trace_record` lines == 0, and the file is valid (Edge Case). Also assert the B19F1 injection path with `FileTraceStore` itself still produces both line kinds (`FileTraceStore` always writes records).
- [X] T053 Write `tests/runtime/test_b20f1_manual_record_guard.py` for **SC-012 / SC-013**: assert `harness/verification/B20F1/manual-verification.md` exists, has non-empty five-section structure, contains code blocks with JSONL sample / `json.loads` output / failure evidence / zero-egress evidence / `__all__` follow-up / **质量门禁 5 偏离** / **发起者追认（确认人 + 日期）** markers; assert `harness/demo/README.md` no longer contains「B20F1 未说参数名」and contains「已锁定（B20F1）」; assert `harness/verification/README.md` contains a **B20F1** row. **MUST run after T048 / T049**; MUST NOT be enabled before the record is written.

**Checkpoint**: All coverage gaps closed; SC-012 / SC-013 / SC-014 / SC-015 have executing tests / guards; span-only edge case is covered; full regression green; manual verification signed; red list closed.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖，可立即开始。
- **Foundational (Phase 2)**: 依赖 Setup；**阻塞** US1 / US2 / US3 / US4。
- **US1 (Phase 3)**: 依赖 Foundational（T006 / T007 / T010）；可独立测试。
- **US2 (Phase 4)**: 依赖 Foundational + US1 的 `_write_event`（T014）；可独立测试。
- **US3 (Phase 5)**: 依赖 Foundational + US1 的 `_write_event`（T014）；可独立测试。
- **US4 (Phase 6)**: 依赖 Foundational（T006 / T007）；可独立测试。
- **Phase 7（跨切面）**: 依赖 US1 / US3 的写入与失败路径；可独立测试。
- **Phase 8（Polish）**: 依赖所有目标阶段完成。
- **Phase 9（Coverage Closure）**: 依赖 Phase 8 的 T048；T049 更新 README；T050–T052 可并行；T053 MUST 在 T048 / T049 之后。

### User Story Dependencies

- **US1 (P1 · MVP)**：T011 → T013 → T014 → T015 → T016；是 US2 / US3 / Phase 7 的写入前提。
- **US2 (P2)**：T017 → T018 → T019；依赖 T014 的文件写入；不依赖 US3 / US4。
- **US3 (P2)**：T020 / T021 → T022 → T023 / T024 → T025；依赖 T014；不依赖 US2 / US4。
- **US4 (P3)**：T026 → T027 → T028；依赖 T006 / T007；不依赖 US2 / US3。

### Within Each Phase

- 测试先写并**先失败**；再实现；测试通过后进入下一任务。
- Foundational 的 `FileTraceStore` 骨架（T006）先于导出 / 冻结面更新 / fixtures；
  T007 依赖 T006；T008 / T009 / T010 可在 T006 后并行。
- US1 的 `_span_to_dict` / `_record_to_dict`（T013）先于 `_write_event`（T014）与回调（T015）；
  T013 / T014 / T015 **同文件 `_file_store.py`，MUST 串行**。
- US2 / US3 的实现任务与 T013–T015 **同文件**，必须在 T015 之后串行；
  US2 的 `T018` 与 US3 的 `T022` / `T023` / `T024` 之间按任务 ID 顺序执行（同文件）。
- Phase 7 的 T031 / T032 / T033 **同文件**，MUST 串行；T029 / T030 可并行写测试。
- Polish 的测试 / 文档 / 验收任务可并行；**manual-verification.md 的写入任务
  T042 → T043 → T044 → T045 串行**；T048 写最终记录；T049 更新 registry；
  T050–T052 可并行；**T053 文档守卫最后执行（MUST 在 T048 / T049 之后）**。

---

## Parallel Opportunities

- **Setup**: T003 / T004 / T005 可并行（不同文件 / 只读检查）。
- **Foundational**: T008 / T009 / T010 可并行（不同测试文件）；T007 依赖 T006。
- **US1**: T011 / T012 可并行写测试（不同文件）；T013 → T014 → T015 → T016 串行。
- **US2 / US3**: T017 / T020 / T021 可并行写测试（不同文件）；实现任务与 US1 同文件，按 T018 → T022 → T023 → T024 顺序。
- **US4**: T026 独立写测试；T027 / T028 顺序。
- **Phase 7**: T029 / T030 可并行写测试；T031 → T032 → T033 → T034 串行。
- **Polish**: T035…T040 / T046 / T047 可并行；T041 可与它们并行；
  **T042 → T043 → T044 → T045 → T048 串行（同一 manual 文件）**。
- **Coverage Closure**: T049 / T050 / T051 / T052 可并行；**T053 在 T048 / T049 之后**。

### Parallel Example: US1

```bash
Task: "Write store unit tests in tests/observability/test_b20f1_store_unit.py"
Task: "Write graph integration tests in tests/observability/test_b20f1_graph_integration.py"
```

### Parallel Example: Phase 8

```bash
Task: "Write contract tests in tests/contracts/test_b20f1_contracts.py"
Task: "Write gate tests in tests/contracts/test_b20f1_gates.py"
Task: "Write differential tests in tests/differential/test_b20f1_local_trace_parity.py"
Task: "Create one-click acceptance script in harness/verification/B20F1/acceptance.py"
```

### Parallel Example: Phase 9

```bash
Task: "Write run_id safety tests in tests/observability/test_b20f1_run_id_safety.py"
Task: "Write flush durability tests in tests/observability/test_b20f1_flush_durability.py"
Task: "Write span-only tests in tests/observability/test_b20f1_span_only.py"
Task: "Update B20F1 row in harness/verification/README.md"
# T053 (manual record guard) runs after T048 / T049
```

---

## Implementation Strategy

### MVP First（US1 Only）

1. 完成 Phase 1 Setup。
2. 完成 Phase 2 Foundational。
3. 完成 Phase 3 US1（T011–T016）。
4. **STOP and VALIDATE**：运行 US1 定向测试 + `quickstart.md` §1/§2；
   `trace-<run_id>.jsonl` 含完整 span + record 行。
5. US1 是 MVP；US2 / US3 / US4 是后续增量。

### Incremental Delivery

1. Setup + Foundational → 骨架 / 导出 / 冻结面 / fixtures。
2. US1 → 落盘 + 双行 + 多 run / 模型工具 / 异常 / stream。
3. US2 → 可读格式 / UTF-8 / LF / Unicode / `kind` 过滤。
4. US3 → 失败不阻断 + 四路诊断 + 不重试 / 截断。
5. US4 → 默认关闭 / 零痕迹 / env no-op。
6. Phase 7 → per-instance 锁 / 0o600 / 逐行生命周期。
7. Phase 8 → 契约 / 门禁 / 差分 / README / 一键验收 / 人工记录 / 全量回归。
8. Phase 9 → `run_id` 安全 / flush 持久化 / span-only 测试 + 文档守卫（T049–T053）。

### Parallel Team Strategy

- **Foundational**: A 做 `_file_store.py` 骨架；B 做导出 + 冻结面测试；C 做 fixtures。
- **US1**: A 做字段映射 / 写入；B 写 store 单测；C 写图集成测试。
- **After US1**:
  - A：US2 格式（同文件，串行）。
  - B：US3 失败（同文件，串行）。
  - C：US4 默认关闭（独立测试）。
- **Phase 7**: A 做锁 / 生命周期；B 做并发 / 权限测试。
- **Phase 8**: 并行做契约 / 门禁 / 差分 / README / 验收 / 人工记录；最后 T048。
- **Phase 9**: A 做 `run_id` 安全 / flush 持久化；B 做 span-only；C 更新 verification README；
  T053 文档守卫最后执行。

---

## Notes

- [P] = 不同文件、无未完成依赖。
- [Story] 标签映射到 spec 的 US1 / US2 / US3 / US4；Setup / Foundational / Phase 7 / Phase 8 为跨切面，不带故事标签。
- 每个任务都必须有精确文件路径；测试任务先写并先失败。
- 冻结面：`Span` 11 字段 / `TraceSink` 3 方法 / `TraceRecord` 13 字段 / `RunConfig` 9 字段 /
  `SuperStepResult` / `PregelTask` / `stream()` 信封 / 门面 8 符号 / L1 22 符号 /
  `runtime.__all__` **零改动**；唯一新增公开符号 = L5 `FileTraceStore`。
- 不新增运行时依赖；`harness/demo/target.py` / `pyproject.toml` / `THIRD_PARTY_NOTICES` 零改动；
  `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt` 零改动（`FileTraceStore` 不进
  `freegraph.graph`）。
- 文件格式 / `kind` / 文件名 / 行序 / 编码是 C27 ⑤ 的内部实现细节，但本 feature 写死以保证
  可重复验收；B20F2 查询实现 MUST 按此读取，Studio MUST NOT 直连。
- 人工验证：`harness/verification/B20F1/manual-verification.md`（JSONL 样例 + 读回证据 +
  失败感知 + 零出站 + `__all__` 追认 + README 锁定记录 + **质量门禁 5 偏离** +
  **发起者追认**）；由 T053 自动守卫。
- **T048** 写最终人工记录；**T053** 是最终文档守卫（MUST 在 T048 / T049 之后）；
  T050–T052 补 SC-014 / SC-015 / span-only 判定覆盖。
