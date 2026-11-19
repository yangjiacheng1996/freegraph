# Tasks: B8F2 · `stream()`：多模式流式输出 + `StreamWriter`

**Input**: Design documents from `/specs/b8f2-stream-modes/`

**Prerequisites**: `plan.md`（required）· `spec.md`（required）· `research.md` ·
`data-model.md` · `contracts/stream-contract.md` · `contracts/upstream-parity.md` · `quickstart.md`

**Tests**: **必做** —— 本 feature 的 SC-001…SC-023、D-121…D-136、acceptance.py 均为
判据级要求；每个 user story 先写测试、先失败，再实现。

**Organization**: 按 user story 分组；同优先级 P2 内按依赖序 **US5 → US4**
（US4 的「七种 mode 全接受」需要 US5 的 `tasks` / `debug` 已存在）。
> ⚠️ **T071–T075** 是追加编号（T071/T072 = US3 关键字注入；T073/T074 = US6 执行语义；
> T075 = Foundational 的 L2 私有单轮助手 `_stream_tick` / `_run_single_step`），
> 执行顺序按 phase 内位置，不按 ID 数值。

---

## 追溯表（FR → 任务）

| FR | 任务 |
|---|---|
| FR-001 / FR-002 / FR-009 | T021 / T022 / T023 / T024 / T044 / T047 / T075 |
| FR-003 / FR-012 / FR-015 | T021 / T022 / T023 |
| FR-004 / FR-016 | T028 / T029 / T030 |
| FR-005 / FR-021 / FR-022 / FR-036 | T004 / T005 / T006 / T013 / T015 / T033 / T034 / T035 / T071 / T072 |
| FR-006 / FR-025 / FR-026 | T049 / T050 / T051 / T052 / T053 |
| FR-007 / FR-008 / FR-035 | T002 / T003 / T070 |
| FR-010 / FR-019 / FR-020 | T009 / T010 / T011 / T012 / T014 / T038 / T039 / T040 / T041 |
| FR-011 | T006 / T008 / T012 / T015 |
| FR-013 / FR-014 / FR-027 | T007 / T021 / T022 / T024 / T044 / T045 / T046 / T049 |
| FR-017 / FR-018 | T044 / T045 |
| FR-023 / FR-028 | T007 / T022 / T049 / T055 |
| FR-024 | T022 / T074 / T075 |
| FR-029 / FR-030 | T004 / T005 / T013 / T016 / T017 / T018 / T019 / T020 |
| FR-031 / FR-032 / FR-033 / FR-034 | T056 / T057 / T058 / T059 / T060 / T061 / T062 / T063 / T064 / T065 / T066 / T067 / T068 / T069 / T070 |
| FR-037 | T022 / T073 / T075 |

**SC 追溯表**

| SC | 任务 |
|---|---|
| SC-001 | T044 / T047 |
| SC-002 | T021 / T022 / T023 / T026 |
| SC-003 | T028 / T029 / T030 / T031 |
| SC-004 | T033 / T034 / T035 / T036 |
| SC-005 | T002 / T003 / T070 / `tests/gates` G24 / G26 / G27 |
| SC-006 | T009 / T010 / T014 / T038 / T039 |
| SC-007 | T038 / T040 / T042 |
| SC-008 / SC-009 | T044 / T045 / T048 |
| SC-010 / SC-011 | T007 / T021 / T022 / T049 |
| SC-012 | T044 / T046 / T048 |
| SC-013 | T049 / T051 / T053 / T054 |
| SC-014 | T008 / T009 / T020 / T075 / T070 |
| SC-015 | T056 / T057 |
| SC-016 | T049 / T050 |
| SC-017 | T041 / T049 / T052 / T054 |
| SC-018 | T004 / T005 / T013 / T020 / T068 / T070 |
| SC-019 | T058 / T059 |
| SC-020 | T060 / T061 / T062 / T063 / T064 / T065 / T066 / T069 |
| SC-021 | T060 / T061 / T071 / T072 |
| SC-022 | T073 / T075 |
| SC-023 | T074 / T075 |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 记录基线、确认取证环境、建立验收目录。

- [X] T001 Create `harness/verification/B8F2/` directory and `harness/verification/B8F2/manual-verification.md` with the five-section skeleton + §1.1 green baseline `1607 passed / 4 skipped / 0 failed` (2026-11-19) in `harness/verification/B8F2/manual-verification.md`
- [X] T002 [P] Verify upstream pin `langgraph==1.2.11` / `langchain-core==1.7.6` in `.venv`, and re-check the anchors `langgraph/types.py:122-124,637-646` · `config.py:126` · `pregel/_executor.py:64,71` · `pregel/_loop.py:580,674,1461-1466` · `pregel/main.py:2964,4228,4236-4243`; record the check in `specs/b8f2-stream-modes/research.md` §0.1
- [X] T003 [P] Confirm `pyproject.toml` is unchanged (zero new runtime/differential dependencies) and record `Requires-Dist` remains empty in `harness/verification/B8F2/manual-verification.md` §1

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 共享载体 / contextvar / `SuperStepResult.tasks` / 公开面 —— 所有 user story 的前置。

**⚠️ CRITICAL**: 本 phase 完成前，任何 user story 不开始。

- [X] T004 Add `StreamWriter: TypeAlias = Callable[[Any], None]` to `src/freegraph/contracts/types.py` (import `Callable` from `collections.abc`; add a docstring: upstream-same `Callable[[Any], None]`; no class; no runtime body); update the module docstring's「五个核心类型」列表以纳入 `StreamWriter`（类型别名）
- [X] T005 Export `StreamWriter` from `src/freegraph/contracts/__init__.py` (append to `__all__`, contracts 21 → 22; keep the existing 21 names unchanged); update the module docstring's「恰为 21 个」为 22
- [X] T006 Create `src/freegraph/runtime/_stream_context.py` (L2 private · `__all__: list[str] = []` · 署名头 · module docstring is first statement): define `_STREAM_WRITER: ContextVar[StreamWriter | None]`, `_CUSTOM_SINK: ContextVar[_CustomSink | None]`, `_CURRENT_TASK: ContextVar[int | None]`, `_ROUND_CAPTURE: ContextVar[_RoundCapture | None]`, **`_STREAM_RUN_ID: ContextVar[str | None]`**, **`_STREAM_THREAD_ID: ContextVar[str | None]`**; implement `get_stream_writer()` (return current writer or a module-level no-op), `bind_stream(...)`, `bind_current_task(task_id)`, `record_round_tasks(tasks)`, `take_custom()`, `take_round_tasks()`, plus private accessors for the two run-id contextvars (供 B18F1 / B19F1 读取); `bind_stream(...)` MUST 是 `_STREAM_WRITER` / `_CUSTOM_SINK` / `_ROUND_CAPTURE` / `_STREAM_RUN_ID` / `_STREAM_THREAD_ID` 的**唯一绑定入口**（由 `StreamSession` 调用）; `_CustomSink` MUST be thread-safe (`threading.Lock`) and store `dict[int, list[Any]]`; `take_custom()` MUST return values in **TaskId ascending** then **insertion order**
- [X] T007 Create `src/freegraph/runtime/_stream.py` (L2 private · `__all__: list[str] = []` · 署名头): implement `StreamSession` context manager; it MUST accept the facade-generated `run_id` and the **raw** `config`; at **first iteration** it MUST call `resolve_config(config)`（非法 `config` ⇒ `TypeError`）并解析 `thread_id`，再绑定 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`；it MUST call `_apply_input_writes(spec, state, input)`, `bind_run(new_run_table())`, 并通过 `_stream_context.bind_stream(...)` 设置 `_STREAM_WRITER` / `_CUSTOM_SINK` / `_ROUND_CAPTURE` / `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`, expose `state` (`SchedulerState`), `initial_sparse` (`_sparse_state`), `max_concurrency`, `max_steps`, `take_custom()`, `take_round_tasks()`, `sparse_state()`, `run_id`, `thread_id`; reset all contextvar tokens in `finally`; accept `input` = `dict` or `None`（`None` = 无输入写入）； `Command` / 其他非法 input 类型 ⇒ built-in `TypeError` naming B14F1 / B15F1 **at first iteration**（这是 input 的唯一校验点；公共 `stream()` MUST NOT 提前拒绝；`config` 的归一 / `thread_id` 解析也 MUST 延迟到首次迭代）；**ignore** `RunConfig.run_id` and `checkpointer`（不读/写快照、不触发恢复）；MUST NOT 调用 `_resume_graph`；可复用 `_first_graph` 的输入写入 / 绑定步骤（抽成私有初始化助手），但 MUST NOT 复用整图循环；**含静态断点（`interrupt_before` / `interrupt_after`）⇒ 首次迭代调用 `_reject_static_points_for_low_level(spec)`（V-26 的 `ValueError`）**
- [X] T008 [P] Add per-task `copy_context()` to `src/freegraph/runtime/_concurrency.py` (`run_tasks_concurrently`: `ctx = copy_context()` per submitted task; `executor.submit(ctx.run, _worker, task_id, fn)`); MUST NOT change `_TaskOutcome` (5 fields), cap, failure order, or cancellation semantics
- [X] T009 Add `tasks: tuple[PregelTask, ...] = ()` at the **end** of `SuperStepResult` in `src/freegraph/runtime/superstep.py`; import `PregelTask` from L1; update the class docstring's construction signature; MUST NOT delete/rename/reorder the existing 4 fields
- [X] T010 In `src/freegraph/runtime/superstep.py` `_run_round` (around `:1282-1445`), build `tuple[PregelTask, ...]` for each outcome: `id`（**运行内唯一**；生成方式不冻结；**建议** `f"{state.step}:{task_id}"`，其中 `task_id` = 本轮整数 TaskId；MUST NOT 跨运行比较 / MUST NOT 进差分断言 / 测试只判唯一性）, `name=target`, `path=(target,)` for standard tasks / `(target, task_id)` for fan-out, `error=outcome.error`, `interrupts=outcome.interrupts`, `state=None`, `result={chan: values[0] if len(values)==1 else tuple(values)}`; return it as a third value; update `run_super_step`, `run_super_steps`, and `_run_graph_loop` to pass/accumulate it into `SuperStepResult.tasks` (single-round = this round; multi-round = accumulated in round order)
- [X] T011 In `src/freegraph/runtime/superstep.py` `_run_round._bind` (around `:1330-1344`), wrap the task call with `bind_current_task(task_id)` from `_stream_context.py` so `StreamWriter` writes can be ordered by TaskId
- [X] T012 In `src/freegraph/runtime/superstep.py` `_run_round` phase ⑥, before `raise GraphInterrupt(interrupts)`, call `record_round_tasks(<the same PregelTask tuple>)` from `_stream_context.py`; MUST NOT add fields to `SchedulerState` / `SuperStepResult` / `InterruptResult`; `RoundCapture` stays `None` for non-stream runs
- [X] T075 In `src/freegraph/runtime/superstep.py`, extract a private `_run_single_step(spec, state, *, max_concurrency=None, route_config=None, max_steps=None)` shared by `run_super_step` and the new private `_stream_tick`: it MUST reuse the existing `_evaluate_start_routes` / `_determine_triggers` / `_run_round` / `_sparse_state`; `run_super_step` delegates with `route_config=None, max_steps=None` and keeps its signature/behavior; `_stream_tick` passes the **raw** `route_config` and `max_steps`, returns `SuperStepResult | None` (`None` = no triggered tasks), and raises `GraphRecursionError` **before executing** when `triggered/fanout` is non-empty and `state.step >= max_steps`; MUST NOT duplicate route/trigger logic; MUST NOT add public L2 symbols (`runtime.__all__` remains 23)
- [X] T013 Add `get_stream_writer` to `src/freegraph/graph.py` (`from .runtime._stream_context import get_stream_writer`; append to `__all__`, facade 7 → 8); facade MUST remain implementation-free (no `def` / `class` / `async def`); update the module docstring's「共 7 个」/「公开名恰 7 个」为 8
- [X] T014 [P] Write `tests/runtime/test_superstep_tasks.py` (先写、先失败): assert `fields(SuperStepResult)` names == `["state","executed","node_writes","steps","tasks"]`; `tasks` default `()`; success round produces one `PregelTask` per task with 7 fields; fan-out `path == (target, task_id)` **and `id` 在 fan-out 同目标多任务间唯一**; `run_super_steps` accumulates; interrupt round does **not** produce `SuperStepResult` (still `GraphInterrupt`)
- [X] T015 [P] Write `tests/runtime/test_stream_writer.py` (先写、先失败): `get_stream_writer()` outside a stream is no-op (no raise); inside a stream it returns the current writer; writes from multiple threads all appear; order is TaskId ascending + insertion order; `get_stream_writer()` and the `writer` keyword injection share the same contextvar carrier; no separate `stream_writer` explicit parameter mechanism
- [X] T016 Update `specs/b2f1-contracts-protocols/contracts/public-api.md` §0: add `StreamWriter` under a new `# ── B8F2 新增的 1 个 ──` comment; **订正既有分组注释** `# ── B2F1 新增的 10 个（本 feature 的交付面）──` 为 `# ── B2F1 / B11F1 新增的 11 个（含 Send）──`（保留原 10 个 B2F1 符号与 `Send` 的顺序）；update the "恰好 21" prose to 22; keep the existing 21 names and ordering
- [X] T017 Update `tests/contracts/test_architecture.py` G7 parser (`parse_public_api_symbols` around `:389-460` and asserts around `:450` / `:1508`): 21 → 22; recognize the new `# ── B8F2 新增的 1 个 ──` comment bucket and the corrected `# ── B2F1 / B11F1 新增的 11 个（含 Send）──` bucket (map them into the parser's `new` segment, or extend the return shape consistently); update the parser docstring; **精确计数口径** = **8 existing + 11 B2F1（含 `Send`）+ 1 B8F2（`StreamWriter`）+ 2 aligned（`Interrupt` / `PregelTask`）**；若解析器保持返回 `(existing, new+aligned)`，则第二段 = **14**（12+2）；若改为显式四段 `(existing, b2f1, b8f2, aligned)`，则 = **8 / 11 / 1 / 2**；**`FR012_NEW_SYMBOLS` 保持 B2F1 的 10 个不变**，`Send` 与 `StreamWriter` 以显式并集加入断言（MUST NOT 把 `StreamWriter` 塞进 `FR012_NEW_SYMBOLS`）；同步把 `test_manifest_splits_into_eight_existing_ten_new_and_two_aligned` 的**名称/注释**改为反映「B2F1 段实为 11（含 `Send`）+ B8F2 1 个」的精确名称，并保持断言强度；不得弱化原有 8 / 11 / 2 与新增 1 个的分段判据
- [X] T018 Update `specs/b2f2-public-api-facade/contracts/facade-api.md` §0 and `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`: facade 7 → 8 with `get_stream_writer`; run `pytest tests/facade/test_api_snapshot.py --update-api-snapshot` **after implementation (T013)** and commit the generated snapshot; 同步清理 `facade-api.md` 顶部「契约层 18 个」及 `tests/facade/test_facade.py` 中「7 个」的过时 docstring（只改文案，不改断言强度）
- [X] T019 Update the field-count asserts R-01…R-04 in `tests/runtime/test_command_purity.py` (`:236-243`), `tests/runtime/test_command_contract.py` (`:565-567`), `tests/runtime/test_interrupt_contract.py` (`:29-39` **and** the hardcoded L1 set at `:72-95`), `tests/runtime/test_superstep_concurrency.py` (`:608-616`): `SuperStepResult` 4 → 5 with `tasks` named; `InterruptResult` stays 4; L1 set + `StreamWriter` (22); split-don't-delete
- [X] T020 Update the count asserts R-05/R-07/R-08/R-09/R-10/R-11/R-14/R-15/R-17 in `tests/runtime/test_conditional_edge_surface.py` (`:50,65,70`), `tests/runtime/test_channel_contract.py` (`:355-356`), `tests/runtime/test_conditional_edge_contract.py` (`:424-426`), `tests/runtime/test_read_contract.py` (`:561-562` + constants `:63,66`), `tests/facade/test_invoke_full_state.py` (`:212-219`), `tests/runtime/test_command_purity.py` (`:287-288`), `tests/runtime/test_superstep_concurrency.py` (`:596`), `tests/runtime/test_parse_contract.py` (`:443-444`): 契约 22 / 门面 8 / runtime 23。⚠️ **T019 与 T020 均改 `test_command_purity.py` / `test_superstep_concurrency.py` ⇒ MUST 串行（T019 → T020），不得并行**

**Checkpoint**: 共享载体就绪 —— `StreamWriter` 可取、`SuperStepResult.tasks` 可读、公开面 8/22/23、G7 清单一致、L2 单轮助手 `_stream_tick` 可用（路由 / 上限由 T075 保证）。

---

## Phase 3: User Story 1 - 观察每一步的状态演进 (Priority: P1) 🎯 MVP

**Goal**: `stream_mode="values"` 产出「初始状态 + 每完成步完整状态」，最后一条 == `invoke` 终态。

**Independent Test**: 两节点线性图 `list(app.stream({"x":0}, stream_mode="values"))` 得到
`1 + 2` 条；最后一条 `payload` == `app.invoke({"x":0})`；每条事件四键。

### Tests & Implementation for User Story 1

- [X] T021 [US1] Write `tests/facade/test_stream_modes.py` `TestValuesStream` (先写、先失败): initial state event first; one values event per completed super-step; full key set == schema; missing overwrite keys are `None`; reducer empty values `[]` / `0` preserved; last `payload` == `invoke` final (no static points / no session history); every event is a dict with exactly `{"stream_mode","payload","run_id","thread_id"}`; same `run_id` across events; `thread_id` from `configurable["thread_id"]`; `RunConfig.run_id` ignored
- [X] T022 [US1] Implement `CompiledGraph.stream` in `src/freegraph/_stategraph.py` (replace the `:357-365` stub): resolve `stream_mode` at call time (`None` ⇒ `"updates"`; str or `Sequence[str]`; closed set; dedupe preserving order; empty sequence / unknown ⇒ `ValueError`; non-str/non-sequence/non-None ⇒ `TypeError`), generate `run_id = uuid4().hex`, and return a **lazy** generator；**`config` 的归一 / `thread_id` 解析 / `input` 校验（`None` 允许 / `Command` 及非法类型 ⇒ `TypeError`）均 MUST 延迟到 `StreamSession` 首次迭代**（与 data-model VS-7 一致）；the generator opens `StreamSession(run_id=..., input=..., config=...)`（`thread_id` 由 session 在首次迭代内解析），emits the initial `values` event (if requested), then loops **L2 单轮入口** `_stream_tick(spec, session.state, max_steps=effective_limit, max_concurrency=session.max_concurrency, route_config=raw_config)` until it returns `None`；`effective_limit` 取 `session.max_steps`（由 `StreamSession` 在首次迭代内按既有 `resolve_limit` 口径解析；L3 MUST NOT 重复解析 `config`）；**MUST NOT** call `_run_graph_loop`；**MUST NOT** 自己求值路由或触发；`stream_mode` 的签名默认改为 `None`、`config` 注解放宽为 `RunConfig | Mapping[str, Any] | None`（T-3）；同步更新 `_stategraph.py` 模块 docstring 中「stream 仍抛 NotImplementedError / 未实现 stream」的过时表述
- [X] T023 [US1] In `src/freegraph/_stategraph.py`, add private helpers for envelope creation (`{"stream_mode","payload","run_id","thread_id"}`) and `values` payload normalization; `values` MUST reuse `_full_state` (`:235-267`) and MUST NOT copy the normalization logic into L2
- [X] T024 [US1] In `src/freegraph/_stategraph.py` `CompiledGraph.stream`, implement the **single-mode** path for `values` only (str mode / default resolution already done in T022); leave `Sequence[str]` normalization and the cross-mode per-round order to **T046**; other modes are added in their phases
- [X] T025 [US1] Update the now-false "stream not delivered" assertions: `tests/facade/test_compiled_graph.py:76` (R-12), `tests/runtime/test_conditional_edge_surface.py:100` (R-06), `tests/facade/test_facade.py:219-235` (R-18) — split-don't-delete: remove `stream` from the NotImplemented loop, add a positive "stream is callable / yields events" assertion
- [X] T026 [US1] Run `pytest tests/facade/test_stream_modes.py -k Values -q` and `pytest tests/facade/test_compiled_graph.py -q`; record the real output in `harness/verification/B8F2/manual-verification.md` §2.1
- [X] T027 [US1] Run `pytest tests/runtime/test_superstep_tasks.py tests/runtime/test_stream_writer.py -q` and confirm the Foundational tests stay green after the L3 stream implementation

**Checkpoint**: US1 独立可验收 —— `values` 序列与 `invoke` 终态一致，MVP 成立。

---

## Phase 4: User Story 2 - 只看每步的增量 (Priority: P1)

**Goal**: `stream_mode="updates"` 产出每个完成 task 的增量；全部增量按通道归约合并 == `invoke` 终态。

**Independent Test**: 线性图 `list(app.stream(..., stream_mode="updates"))` 得到 2 条；
`{node: {channel: value|tuple}}`；合并后 == `invoke`。

### Tests & Implementation for User Story 2

- [X] T028 [US2] Write `tests/facade/test_stream_modes.py` `TestUpdatesStream` (先写、先失败): one event per completed task; payload key is the node name; single write is a scalar; same task same channel multi-write is a tuple in write order; merge all updates with channel reducer semantics == `invoke` final; interrupt closing event is `{"__interrupt__": tuple}` (may be added in US6, keep the test ready)
- [X] T029 [US2] Implement `updates` event building in `src/freegraph/_stategraph.py` from `SuperStepResult.tasks` (each `PregelTask.result` is already `{channel: value|tuple}`); emit one event per completed task in task order; MUST NOT use simple `dict.update` as the merge implementation
- [X] T030 [US2] Add a merge-back helper test in `tests/facade/test_stream_modes.py` (or a private test helper) that applies every update via the channel reducer (`channel.update([...])`) and compares with `invoke`; cover overwrite and reducer channels
- [X] T031 [US2] Run `pytest tests/facade/test_stream_modes.py -k Updates -q`; record the real output in `harness/verification/B8F2/manual-verification.md` §2.2
- [X] T032 [US2] Verify US1 `values` tests still pass (`pytest tests/facade/test_stream_modes.py -k Values -q`)

**Checkpoint**: US2 独立可验收 —— `updates` 可合并回终态。

---

## Phase 5: User Story 3 - 节点主动写自定义数据 (Priority: P1)

**Goal**: 节点内 `get_stream_writer()({"msg": ...})` 或签名的 `writer({"msg": ...})` 的数据
在 `custom` 流中**原样**出现。

**Independent Test**: 节点写 `{"msg":"retrieving"}`；`list(app.stream({}, stream_mode="custom"))`
的 `payload` == `{"msg":"retrieving"}`；声明 `writer` 参数的节点同样生效。

### Tests & Implementation for User Story 3

- [X] T033 [US3] Write `tests/facade/test_stream_modes.py` `TestCustomStream` (先写、先失败): single write appears verbatim; multiple writes all appear; order is TaskId ascending + insertion order; `get_stream_writer()` outside `stream()` is no-op; failed node still flushes its prior custom writes before the exception (detailed behavior in US6); no `_TaskOutcome` field is added
- [X] T034 [US3] Wire `custom` in `src/freegraph/_stategraph.py`: after each L2 单轮入口（`_stream_tick` / `run_super_step`）, call `session.take_custom()`, wrap each value in the four-key envelope with `stream_mode="custom"`, and emit them before `updates`/`tasks`/`debug`/`values` in the fixed per-round order；**这是轮末批量产出（P-23 / X-6），不是逐写即时产出**；不得把 custom 塞进 `_TaskOutcome`
- [X] T035 [US3] Verify `src/freegraph/runtime/_stream_context.py` writer closure reads `_CUSTOM_SINK` + `_CURRENT_TASK`, and `_stream.py` resets the sink per round; ensure `get_stream_writer()` returns a no-op when `_STREAM_WRITER` is `None`；**轮末批量**与 X-6 的口径一致
- [X] T071 [US3] Implement keyword injection in `src/freegraph/_stategraph.py` via a private `_wrap_node_action(action)` helper **applied once at node registration / compile time** (so `invoke` and `stream` share the same wrapper): inspect `inspect.signature(action)`; if parameter name **`writer`** exists with kind `POSITIONAL_OR_KEYWORD` or `KEYWORD_ONLY` and annotation ∈ {`StreamWriter`, `"StreamWriter"`, empty}, return a wrapper calling `action(node_input, writer=get_stream_writer())`; otherwise return `action` unchanged; `**kwargs` / other parameter names / mismatched annotations MUST NOT inject; use `get_stream_writer()` (no-op outside `stream()`); MUST NOT add public symbols; close B8F1 DR-4
- [X] T072 [US3] Write `tests/facade/test_stream_writer_injection.py` (先写、先失败): `def node(state, writer)` receives the writer and emits `custom`; `def node(state, writer: StreamWriter)` works; `def node(state, *, writer)` works; `def node(state, stream_writer)` is **not** injected (upstream parameter name is `writer`); `def node(state, **kwargs)` is not injected; `invoke()` injects a no-op and does not raise
- [X] T036 [US3] Run `pytest tests/facade/test_stream_modes.py -k Custom tests/runtime/test_stream_writer.py tests/facade/test_stream_writer_injection.py -q`; record the real output in `harness/verification/B8F2/manual-verification.md` §2.3
- [X] T037 [US3] Verify US1/US2 tests still pass (`pytest tests/facade/test_stream_modes.py -q`)

**Checkpoint**: US3 独立可验收 —— custom 原样出现、顺序确定、无流 no-op、`writer` 关键字注入生效。

---

## Phase 6: User Story 5 - task 级观察与调试 (Priority: P2)

**Goal**: `tasks` 每个完成 task 一条 `PregelTask`（含被中断 task）；`debug` 产出对应的
`{step,timestamp,type:"task_result",payload}` 包裹。

**Independent Test**: 两节点图 `tasks` 得到 2 条 `PregelTask`；`debug` 得到 2 条同数量包裹；
被中断 task 也各有一条。

### Tests & Implementation for User Story 5

- [X] T038 [US5] Write `tests/facade/test_stream_modes.py` `TestTasksDebugStream` (先写、先失败): `tasks` payload is `PregelTask`; one per completed task; `name` / `result` / `error` / `interrupts` readable; interrupted task gets one event with `interrupts` non-empty; `debug` keys == `{"step","timestamp","type","payload"}`; `type == "task_result"`; `step` is 1-based and same for tasks in one round, **including the interrupted round**; `timestamp` is UTC ISO-8601, parseable by `datetime.fromisoformat`, and `utcoffset() == timedelta(0)`
- [X] T039 [US5] Implement `tasks` event emission in `src/freegraph/_stategraph.py` from `result.tasks`; `payload` is the `PregelTask` instance **as-is**; emit one event per task in task order
- [X] T040 [US5] Implement `debug` event emission in `src/freegraph/_stategraph.py`: for each `tasks` event, build `{"step": round_index, "timestamp": datetime.now(timezone.utc).isoformat(), "type": "task_result", "payload": <same PregelTask>}` where `round_index` is a local counter in the stream generator (starts at 1, **increments before each L2 单轮入口 invocation** so a successful round and an interrupted round both get their own index; if `_stream_tick` returns `None`/converged, no events are emitted; same value for tasks in one round); no checkpoint class debug events in v1
- [X] T041 [US5] Implement interrupt task/debug emission in `src/freegraph/_stategraph.py`: on `GraphInterrupt`, follow **FR-014** exactly: `custom → updates(__interrupt__) → tasks → debug → values`; read `session.take_round_tasks()` and emit the interrupted task's `tasks` + `debug` events between `updates` and `values`; use the **same `round_index` rule as T040**（进入该轮前已递增的序号；中断轮 MUST NOT 沿用上一轮）; MUST NOT add fields to `SuperStepResult` / `InterruptResult`
- [X] T042 [US5] Run `pytest tests/facade/test_stream_modes.py -k "Tasks or Debug" tests/runtime/test_superstep_tasks.py -q`; record the real output in `harness/verification/B8F2/manual-verification.md` §2.4
- [X] T043 [US5] Verify US1/US2/US3 tests still pass (`pytest tests/facade/test_stream_modes.py -q`)

**Checkpoint**: US5 独立可验收 —— `tasks` / `debug` 事件、被中断 task 补发、`SuperStepResult.tasks` 一致。

---

## Phase 7: User Story 4 - 七种 mode 都被接受 (Priority: P2)

**Goal**: 七种合法 mode 全部接受；非法 / 空 / 重复 / 多 mode 行为可判定；
`checkpoints` / `messages` 恒空序列。

**Independent Test**: 七种 mode 逐一消费均不抛；`bogus` ⇒ 调用时 `ValueError`；`[]` ⇒
`ValueError`；`123` ⇒ `TypeError`；多 mode 每条的 `stream_mode` 正确。

### Tests & Implementation for User Story 4

- [X] T044 [US4] Write `tests/facade/test_stream_modes.py` `TestModeSurface` (先写、先失败): seven modes accepted; `stream_mode=None` accepted and produces `updates`-shaped events; `checkpoints` / `messages` length == 0 and no raise; `bogus` / `[]` ⇒ `ValueError` at call time (not at first iteration); `123` ⇒ `TypeError`; duplicate modes deduped preserving order; multi-mode events each carry the correct `stream_mode`; per-round order is `custom → updates → tasks → debug → values`
- [X] T045 [US4] Implement `checkpoints` / `messages` in `src/freegraph/_stategraph.py`: accepted, but emit zero events and never raise; MUST NOT fabricate checkpoint events; MUST NOT attempt LangChain message extraction
- [X] T046 [US4] Implement multi-mode normalization and ordering in `src/freegraph/_stategraph.py`: `Sequence[str]` dedupe preserving first occurrence; emit only requested modes; keep the fixed per-round order `custom → updates → tasks → debug → values`; single-mode and multi-mode share the same four-key envelope
- [X] T047 [US4] Verify (do **not** reimplement) that invalid-mode validation from **T022** is call-time (not generator-time) in `src/freegraph/_stategraph.py`: `ValueError` message MUST name the offending value and list the seven legal values; `TypeError` message MUST name the type; if a gap is found, fix the single T022 implementation point
- [X] T048 [US4] Run `pytest tests/facade/test_stream_modes.py -k "Mode or Surface or Checkpoints or Messages" -q`; record the real output in `harness/verification/B8F2/manual-verification.md` §2.5

**Checkpoint**: US4 独立可验收 —— 七种 mode / 非法 mode / 多 mode / 空序列边界。

---

## Phase 8: User Story 6 - 流式消费不改变执行语义 (Priority: P3)

**Goal**: 惰性、提前停止零泄漏、中断收尾、失败原样重抛；`invoke` 终态不受流式消费影响；
递归上限 / `max_concurrency` 与 `invoke` 同款；条件边路由与 `invoke` 一致。

**Independent Test**: 未迭代的 `stream()` 执行节点 0 次；取 1 条后 `close()` 无
`freegraph-node` 线程；中断流正常结束且含 `__interrupt__`；失败流先出 custom 再重抛原异常；
超 `recursion_limit` 抛 `GraphRecursionError`；条件边图流式路由与 `invoke` 一致。

### Tests & Implementation for User Story 6

- [X] T049 [US6] Write `tests/facade/test_stream_lifecycle.py` (先写、先失败): lazy (no iteration ⇒ 0 node calls); `stream(None)` = no input writes and the graph still runs from the static entry; `stream(Command(...))` does **not** raise at call time but raises `TypeError` on the **first** `next()`; **非法 `config` 也在首次 `next()` 抛 `TypeError`（调用时不抛）**; `config` as a plain mapping resolves `thread_id` / `max_concurrency` like `RunConfig`; **含 `interrupt_before` / `interrupt_after` 的图在首次 `next()` 抛 `ValueError`（复用 V-26 口径，调用时不抛）**; `next(it)` then `it.close()` ⇒ no `freegraph-node` threads; `interrupt()` ⇒ `tasks`/`debug`补发 + `values`/`updates` 含 `__interrupt__` + normal stop; failing node ⇒ prior custom flushed, original `RuntimeError` re-raised, no failing-round values/updates/tasks/debug; `invoke` after a partial stream still gives the same final state; **节点内读到的 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID` 与本流事件一致**
- [X] T050 [US6] Implement lazy semantics in `src/freegraph/_stategraph.py`: the public `stream()` validates mode and returns a generator; no session / no L2 单轮入口（`_stream_tick` / `run_super_step`）until first `next()`; a never-iterated generator executes zero nodes
- [X] T051 [US6] Implement early-stop cleanup in `src/freegraph/_stream.py` / `src/freegraph/_stategraph.py`: `StreamSession` resets all contextvar tokens in `finally`; each L2 单轮入口 closes its thread pool before returning; no `freegraph-node` threads remain after `close()`
- [X] T052 [US6] Implement `GraphInterrupt` handling in `src/freegraph/_stategraph.py`: emit custom (already recorded) → `updates(__interrupt__)` → `tasks`/`debug` for the interrupted task → `values` (full state + `__interrupt__`) → stop normally (do not raise `GraphInterrupt`)
- [X] T053 [US6] Implement failure handling in `src/freegraph/_stategraph.py`: on non-interrupt exceptions, drain and emit the failing round's already-recorded custom events, then re-raise the **original** exception object/type/message; do not emit failing-round values/updates/tasks/debug; do not roll back already-delivered successful rounds
- [X] T073 [US6] Write execution-semantics tests for **FR-037 / SC-022** in `tests/facade/test_stream_lifecycle.py`: `recursion_limit` exceeded **with pending tasks** ⇒ `GraphRecursionError`; **exactly converged at the limit** (no pending tasks) ⇒ no raise; the error occurs **before** executing the over-limit round (node-call counter proves no extra round); `max_concurrency` from `config`（`RunConfig.max_concurrency` 或普通映射同名字段）is passed to the L2 单轮入口 and behaves like `invoke`；`stream()` 不新增该关键字
- [X] T074 [US6] Write `tests/facade/test_stream_modes.py` `TestRoutingStream` for **FR-024 / SC-023**: a conditional-edge graph under `stream(..., stream_mode="updates")` produces the same executed-node sequence and final state as `invoke()`; a **dual-param route `f(state, config)`** receives the **raw** `config` passed to `stream()` (RunConfig / mapping / None, verbatim); assert `stream()` does not evaluate routes itself
- [X] T054 [US6] Run `pytest tests/facade/test_stream_lifecycle.py tests/facade/test_stream_modes.py -q`; record the real output in `harness/verification/B8F2/manual-verification.md` §2.6

**Checkpoint**: US6 独立可验收 —— 惰性 / 提前停止 / 中断 / 失败 / 不改变执行语义。

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 差分、验收脚本、人工记录、回溯修订、下游接线、全量验证。

- [X] T055 [P] Update `harness/demo/visualization.py` `case_stream_modes` to expect the seven modes green (no code change to the script's mode list; only adjust the assertions/notes if needed) and update `harness/demo/graph_core.py` C25 stream soft assertion to read `event["payload"]` keys (envelope shape adaptation; not a gate relaxation)
- [X] T056 [P] Write `tests/differential/parity_probe.py` D-121…D-136 (16 scenarios) exactly per `contracts/upstream-parity.md` §4; non-`SAME` rows MUST carry a non-empty `note`; upstream absent ⇒ `skip`
- [X] T057 Run `pytest tests/differential/test_parity_probe.py -q` and record the judgment distribution `SAME 10 / DIFF 4 / STRICTER 2`（**D-124 只比载荷；custom 时机归 X-6**）in `harness/verification/B8F2/manual-verification.md` §3
- [X] T058 [P] Create `harness/verification/B8F2/acceptance.py` (A1…A3 / V1…V21): exit codes `0` PASS / `1` FAIL / `2` environment not ready; last line MUST print `B8F2 acceptance: PASS|FAIL`; cover seven modes, default `None ⇒ updates`, values==invoke, updates merge, custom (getter + `writer` injection + **轮末批量 X-6**), `stream(None)`, tasks/debug, envelope ids (+ **`_STREAM_RUN_ID` / `_STREAM_THREAD_ID` 与事件一致**), invalid modes / `None`, checkpoints/messages zero, **checkpointer ignored / static interrupt `ValueError`（V-26）**, lazy/early stop, interrupt/failure, recursion limit / `max_concurrency`（含**恰好收敛于上限**与**超限前抛**）, **双参路由的原始 `config` 透传**, conditional-edge route parity, public surface, differential skip, zero deps
- [X] T059 Create `tests/runtime/test_stream_acceptance.py` to run `harness/verification/B8F2/acceptance.py` in a subprocess and assert exit code `0` / `B8F2 acceptance: PASS`（**after T058**）
- [X] T061 Write `harness/verification/B8F2/manual-verification.md` §4 / §5: five-section record, environment, green baseline, real outputs per mode, differential results, interrupt/failure observations, **R-5 门禁 3/4/5 偏离登记**, **R-6 ARCH-3 例外登记**, T-1…T-5 acknowledgment text + initiator confirmation + date
- [X] T062 [P] Retro-revise T-1: `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §5.3 + `specs/b7f1-superstep-loop/spec.md` — keep the original 4 fields, append `tasks` note；`src/freegraph/runtime/superstep.py:348-377` 的 docstring 由 **T009** 负责（本任务只复核其注记在位，不重复改写）
- [X] T063 [P] Retro-revise T-2: `specs/b12f1-concurrency-errors/spec.md` 裁定 25 ② / FR-013 — **only add a note**, do not rewrite the original "four fields zero change" text
- [X] T064 Retro-revise T-3: `src/freegraph/contracts/protocols.py:278-286`（**concrete 签名由 T022 落地，本任务只复核**）+ `specs/b2f1-contracts-protocols/contracts/public-api.md` 的 `stream` 行 + `specs/b2f1-contracts-protocols/data-model.md` §2.5 + **`specs/b7f2-compile/contracts/compile-contract.md` §2.4 + `specs/b7f2-compile/data-model.md` §2.3 + `specs/b7f2-compile/plan.md` Phase A / `specs/b7f2-compile/tasks.md` T006（只补注记，原 `"values"` 文字保留为历史）** — widen `config` to `RunConfig | Mapping[str, Any] | None`; change `stream_mode` default to `None` with `None ⇒ "updates"`; keep the original `RunConfig | None` as a subset and explicit `"values"` as valid；同步检查 `protocols.py` 模块 docstring 是否有旧默认值说明并补注记。⚠️ `README.md` 归 **T068**，本任务不写
- [X] T065 [P] Retro-revise T-4: `specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md` §3 + `src/freegraph/runtime/_interrupt.py:15-27` docstring — only add the "since B8F2, per-task copy_context ⇒ thread pool inherits contextvars" note; keep the original text
- [X] T066 [P] Retro-revise T-5 + close B8F1 DR-4: **先复核** `specs/b8f1-conditional-edges-fresh-read/research.md` 的 DR-4 关闭注记（`writer` / `"StreamWriter"` / 空注解 · 工作区已含 2026-11-19 注记）**已在位**；若缺失才补，**MUST NOT** 重复追加。`public-api.md` §0 / G7 / `facade-api.md` / snapshot 的清单改动已分别由 T016 / T017 / T018 完成，本任务只复核，不重复改写
- [X] T069 Register the scale actuals in `harness/verification/B8F2/manual-verification.md` §5 (measured lines/hours; do not modify the 立项书 §5.2 scale row; the revision is the initiator's authority)。⚠️ **与 T057 / T061 串行**（同一文件）
- [X] T060 Create `tests/runtime/test_stream_manual_record_guard.py`: assert `harness/verification/B8F2/manual-verification.md` exists, has the five sections, contains non-empty outputs for the seven modes + `writer` 注入 + D-121…D-136 + **P-23 / X-6（custom 轮末批量）**, and contains acknowledgment text for T-1…T-5 + **R-5 + R-6** **plus 发起者确认与日期**（SC-020 / SC-021）。⚠️ **物理位置在 T061/T062–T066/T069 之后**：守卫 MUST 在记录写就之后启用，MUST NOT 造成永久红 CI
- [X] T067 [P] Wire downstream D-1…D-4 into `harness/features/B8F3_节点别名与context通道.md`, `B14F1_Checkpointer协议与MemorySaver.md`, `B18F1_Span数据类生产.md`, `B19F1_TraceSink与current_span.md`, `B22F1_get_graph与draw_mermaid.md`, `B23F1_draw_mermaid_png离线不阻断.md` — only wire, do not implement the next feature；D-3 的载体明确为 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`，并注明 **ARCH-3 已登记例外（plan R-6）**：只读取运行期 `str | None` 元数据，不得扩展为任意 L5 → L2 私有依赖
- [X] T068 [P] Update `README.md` API compatibility matrix: add `StreamWriter` / `get_stream_writer` rows, update the `CompiledGraph.stream` row (delivered / seven modes / four-key envelope / custom 轮末批量 X-6 / run-id contextvar), record zero new dependencies and zero `THIRD_PARTY_NOTICES` changes。⚠️ `StreamWriter` 是 `public-api.md` §0 的 `new` 符号 ⇒ G8 要求该行含上游 `路径:行号`（写 `langgraph/types.py:138`）或「无上游对应」；`get_stream_writer` 是门面符号，不受 G8 的 contract-new 段约束。⚠️ `README.md` 的**唯一 owner = 本任务**
- [X] T070 Run the final gate: `pytest tests/ -q` (all green), `pytest tests/runtime/test_stream_acceptance.py -q`, `pytest tests/runtime/test_stream_manual_record_guard.py -q`, and `harness/verification/B8F2/acceptance.py` (exit 0, `B8F2 acceptance: PASS`); also run the negative-scope scan (no `async def` / `astream` / new trace / UI / checkpoint-source / messages-extraction code in `src/freegraph/**`); assert top-level `freegraph.__all__ == ["__version__"]`（顶层惰性 · SC-018）; record the final counts in `harness/verification/B8F2/manual-verification.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: 可立即开始；T001 先做（记录基线），T002/T003 可并行。
- **Phase 2 Foundational**: 依赖 Setup；**阻塞所有 user story**。
  - T004 → T005 → T006 → T007 → T013（公开面/会话链）
  - T009 → T010 → T011/T012（任务定格链）→ **T075**（`_run_single_step` / `_stream_tick`）
  - T008 与 T006 可并行（不同文件）
  - T014/T015 测试可在 T006/T010 后写
  - **T016 → T017 串行**（T017 依赖 T016 写定的最终分组注释字符串）；**T018 在 T013 之后**（快照由实现生成）；**T019 → T020 MUST 串行**（二者都改 `test_command_purity.py` / `test_superstep_concurrency.py`）
- **Phase 3 US1**: 依赖 Foundational；MVP。
- **Phase 4 US2**: 依赖 US1（需要 `stream()` 主循环）。
- **Phase 5 US3**: 依赖 US1 + Foundational 的 writer；T071/T072 交付 `writer` 关键字注入，T036 同时验证 custom 与注入。
- **Phase 6 US5**: 依赖 US1（主循环） + Foundational 的 `tasks` 字段。
- **Phase 7 US4**: 依赖 US1（校验/多 mode 骨架） + US5（tasks/debug 已存在） + US2/US3（七 mode 全接受）。
- **Phase 8 US6**: 依赖 US1（惰性） + US5（中断 task） + US3（失败 custom flush）；
  T073（FR-037）依赖 T007 / T022 / **T075**，T074（FR-024）依赖 T022 / T029 / **T075**。
- **Phase 9 Polish**: 依赖所有 user stories + Foundational。
  - **T057 → T061 → T069 MUST 串行**（同一 `manual-verification.md`）。
  - **T061 写记录 → T062–T066 回溯修订 → T069 规模实测 → T060 守卫**（守卫 MUST 在记录写就之后）。
  - `README.md` 的唯一 owner = **T068**；T064 / T066 不写 README。
  - T019 → T020 串行（见 Phase 2）。

### User Story Dependencies

- **US1 (P1)**: 无其它 story 依赖；是 MVP。
- **US2 (P1)**: 依赖 US1；不依赖 US3/US5。
- **US3 (P1)**: 依赖 US1；writer 载体在 Foundational。
- **US5 (P2)**: 依赖 US1；`tasks` 字段在 Foundational。
- **US4 (P2)**: 依赖 US1 + US2 + US3 + US5（七 mode 全接受）。
- **US6 (P3)**: 依赖 US1 + US3 + US5（中断/失败路径）。

### Within Each User Story

- 测试先行：每个 story 的第一个任务是写测试并确认**先失败**。
- 实现顺序：主循环/载荷 → 事件组装 → 边界行为 → 验证。
- 同一文件的测试/实现任务**不标 [P]**；不同文件才可并行。

---

## Parallel Execution Examples

### Foundational（Phase 2）

```bash
# T006 / T008 不同文件，可并行
Task: "T006 Create src/freegraph/runtime/_stream_context.py"
Task: "T008 Add per-task copy_context in src/freegraph/runtime/_concurrency.py"

# T014 / T015 不同测试文件，可并行
Task: "T014 Write tests/runtime/test_superstep_tasks.py"
Task: "T015 Write tests/runtime/test_stream_writer.py"
```

### US1 + US2 + US3（P1 stories，Foundational 完成后）

```bash
# US1 先落地主循环；US2/US3 在其后按文件分工
Task: "T021-T027 US1 values + stream skeleton"
Task: "T028-T032 US2 updates"
Task: "T033-T037 + T071-T072 US3 custom / writer injection"
```

### Polish（Phase 9）

```bash
# 差分 / 验收 / 回溯修订 / 下游接线 / README 可并行（有同文件约束的除外）
Task: "T055 visualization + graph_core adaptation"
Task: "T056 differential D-121…D-136（T057 与其串行；记录写人工记录 §3）"
Task: "T058-T059 acceptance.py + pytest"
Task: "T062-T066 T-1…T-5 retro revisions"
Task: "T067 downstream wiring"
Task: "T068 README API matrix"
# 串行链：T057 → T061（写记录）→ T069（规模实测）；T060（守卫）在 T061/T062–T066/T069 之后
```

---

## Implementation Strategy

### MVP First（US1 Only）

1. 完成 Phase 1 Setup。
2. 完成 Phase 2 Foundational（**阻塞所有 story**）。
3. 完成 Phase 3 US1：`stream()` 骨架 + `values`。
4. **STOP and VALIDATE**：`values` 最后一条 == `invoke` 终态；四键信封；惰性。
5. 可交付 MVP。

### Incremental Delivery

1. Setup + Foundational → 共享载体就绪。
2. US1 → `values` MVP → 验证。
3. US2 → `updates`（可合并回终态）→ 验证。
4. US3 → `custom`（getter + `writer` 注入 + 顺序）→ 验证。
5. US5 → `tasks` / `debug` → 验证。
6. US4 → 七种 mode / 非法 mode / 空序列 / 多 mode → 验证。
7. US6 → 惰性 / 提前停止 / 中断 / 失败 / 递归上限 / 路由一致性 → 验证。
8. Polish → 差分 / acceptance / 人工记录 / 回溯修订 → 全量绿。

### Parallel Team Strategy

1. 全员完成 Setup + Foundational。
2. Foundational 完成后：
   - Developer A：US1（MVP，先落主循环）
   - Developer B：US3 的 writer 测试（先写、先失败，等 US1 主循环）
   - Developer C：US5 的 `SuperStepResult.tasks` 测试（Foundational 已落字段）
3. US1 完成后：US2 / US3 / US5 可并行（不同测试类/文件）。
4. US4 在 US2/US3/US5 后收口；US6 在 US1/US3/US5 后收口。
5. Polish 最后统一做差分 / 验收 / 回溯修订。

---

## Notes

- **测试先行**：每个 story 的第一条测试任务 MUST 先失败；实现任务 MUST 使其转绿。
- **[P]** = 不同文件、无未完成依赖；同一文件的任务 MUST 串行。
- **文件路径**：全部为仓库相对路径（`src/...` / `tests/...` / `harness/...` / `specs/...`）。
- **破冻结面**：T-1…T-5 的追认文字 MUST 落 `harness/verification/B8F2/manual-verification.md`；
  **未追认前 MUST NOT 合入**。
- **零新增**：运行时依赖 · 错误类型 · async · 公开 L2 符号 · 门禁编号。
- **绿基线**：实施前 `1607 passed / 4 skipped / 0 failed`；改动后 MUST 重跑并按
  `plan.md` 的 R-01…R-18 逐条归因。
- **禁止**：把 `checkpoints` / `messages` 判成 `NotImplementedError`；把 `tasks` /
  `debug` 的失败轮补发；把 custom 塞进 `_TaskOutcome`；在 L2 复制 `_full_state`。
- **偏离登记**：custom 为**轮末批量**（P-23 / **X-6**，DIFF）；它不是逐写即时产出，验收断言
  MUST 按「每轮结束后 TaskId 序」判定。
- **运行标识载体**：`_STREAM_RUN_ID` / `_STREAM_THREAD_ID` 是 L2 私有 contextvar；B18F1 / B19F1
  MUST 读取同一对值，MUST NOT 新增公开符号。
- **追溯**：文末「附录 · 任务 ↔ spec 追溯表（反向）」是 tasks → spec 的权威；FR 37/37 ·
  SC 23/23 双向无空缺。

---

## 附录 · 任务 ↔ spec 追溯表（反向）

> **反向覆盖**：**FR 37/37 · SC 23/23** —— 每个 FR 与每个 SC **至少**被一条任务映射；
> **反向亦然**：每条任务携带的义务 MUST 挂上**至少一条 FR/SC**（⇒ 追溯表**双向**齐全 · 宪法原则 VI）。
>
> ⚠️ **两张追溯表的关系不同**：正文的 FR→任务 / SC→任务 = **spec → tasks**；
> 本附录 = **tasks → (FR, SC)**（每条任务承载哪些 FR 与 SC）⇒ 覆盖判定以本附录为准。
> 本附录可包含正文 SC 表未列的 SC 组合（任务 → SC 的细化），**不构成矛盾**。
>
> ⚠️ **※ 标记**：标 ※ 的任务是「写记录 / 追认 / 文档回溯修订 / 审计」类；按宪法 v1.11.0 + v1.13.0，
> 它们产出产物但**不构成判定覆盖** ⇒ 判定载体见对应 SC 的测试任务。

| 任务 | FR | SC | 说明 |
|---|---|---|---|
| T001 | FR-034 | SC-020 | 绿基线 + 人工记录骨架（流程义务） |
| T002 | FR-007 · FR-008 · FR-035 | SC-005 | 见正文 |
| T003 | FR-007 · FR-008 · FR-035 | SC-005 | 见正文 |
| T004 | FR-005 · FR-021 · FR-022 · FR-036 · FR-029 · FR-030 | SC-018 | 见正文 |
| T005 | FR-005 · FR-021 · FR-022 · FR-036 · FR-029 · FR-030 | SC-018 | 见正文 |
| T006 | FR-005 · FR-021 · FR-022 · FR-036 · FR-011 | — | 见正文 |
| T007 | FR-023 · FR-027 · FR-028 | SC-011 | 见正文 |
| T008 | FR-011 | SC-014 | 见正文 |
| T009 | FR-010 · FR-019 · FR-020 | SC-006 · SC-014 | 见正文 |
| T010 | FR-010 · FR-019 · FR-020 | SC-006 | 见正文 |
| T011 | FR-010 · FR-019 · FR-020 | — | 见正文 |
| T012 | FR-010 · FR-019 · FR-020 · FR-011 | — | 见正文 |
| T075 | FR-009 · FR-024 · FR-037 | SC-014 · SC-022 · SC-023 | L2 私有 `_run_single_step` / `_stream_tick`（与 `run_super_step` 共用 · `route_config` 透传 · 执行前判上限） |
| T013 | FR-005 · FR-021 · FR-022 · FR-036 · FR-029 · FR-030 | SC-018 | 见正文 |
| T014 | FR-010 · FR-019 · FR-020 | SC-006 | 见正文 |
| T015 | FR-005 · FR-021 · FR-022 · FR-036 · FR-011 | — | 见正文 |
| T016 | FR-029 · FR-030 | — | 见正文 |
| T017 | FR-029 · FR-030 | — | 见正文 |
| T018 | FR-029 · FR-030 | — | 见正文 |
| T019 | FR-029 · FR-030 | — | 见正文 |
| T020 | FR-029 · FR-030 | SC-014 · SC-018 | 见正文 |
| T021 | FR-001 · FR-002 · FR-009 · FR-003 · FR-012 · FR-015 · FR-013 · FR-014 · FR-027 | SC-002 · SC-010 · SC-011 | 见正文 |
| T022 | FR-001 · FR-002 · FR-009 · FR-003 · FR-012 · FR-015 · FR-013 · FR-014 · FR-027 · FR-023 · FR-028 · FR-024 · FR-037 | SC-002 · SC-010 · SC-011 | 见正文 |
| T023 | FR-001 · FR-002 · FR-009 · FR-003 · FR-012 · FR-015 | SC-002 | 见正文 |
| T024 | FR-001 · FR-002 · FR-009 · FR-013 · FR-014 · FR-027 | — | 见正文 |
| T025 | FR-035 | SC-018 | 移除 stream 未就绪断言，改正面断言 |
| T026 | FR-003 | SC-002 | US1 values 回归 |
| T027 | FR-010 | SC-006 | Foundational 测试回归 |
| T028 | FR-004 · FR-016 | SC-003 | 见正文 |
| T029 | FR-004 · FR-016 | SC-003 | 见正文 |
| T030 | FR-004 · FR-016 | SC-003 | 见正文 |
| T031 | FR-004 | SC-003 | US2 updates 回归 |
| T032 | FR-003 | SC-002 | US1 values 回归 |
| T033 | FR-005 · FR-021 · FR-022 · FR-036 | SC-004 | 见正文 |
| T034 | FR-005 · FR-021 · FR-022 · FR-036 | SC-004 | 见正文 |
| T035 | FR-005 · FR-021 · FR-022 · FR-036 | SC-004 | 见正文 |
| T036 | FR-005 | SC-004 | US3 custom 回归 |
| T037 | FR-004 | SC-003 | US1/US2 回归 |
| T038 | FR-010 · FR-019 · FR-020 | SC-006 · SC-007 | 见正文 |
| T039 | FR-010 · FR-019 · FR-020 | SC-006 | 见正文 |
| T040 | FR-010 · FR-019 · FR-020 | SC-007 | 见正文 |
| T041 | FR-010 · FR-019 · FR-020 | SC-017 | 见正文 |
| T042 | FR-010 | SC-007 | US5 tasks/debug 回归 |
| T043 | FR-006 | SC-013 | US1/US2/US3 回归 |
| T044 | FR-001 · FR-002 · FR-009 · FR-013 · FR-014 · FR-027 · FR-017 · FR-018 | SC-001 · SC-008 · SC-009 · SC-012 | 见正文 |
| T045 | FR-013 · FR-014 · FR-027 · FR-017 · FR-018 | SC-008 · SC-009 | 见正文 |
| T046 | FR-013 · FR-014 · FR-027 | SC-012 | 见正文 |
| T047 | FR-001 · FR-002 · FR-009 | SC-001 | 见正文 |
| T048 | FR-002 | SC-008 · SC-009 · SC-012 | US4 边界回归 |
| T049 | FR-006 · FR-025 · FR-026 · FR-023 · FR-027 · FR-028 | SC-011 · SC-013 · SC-016 · SC-017 | 见正文 |
| T050 | FR-006 · FR-025 · FR-026 | SC-016 | 见正文 |
| T051 | FR-006 · FR-025 · FR-026 | SC-013 | 见正文 |
| T052 | FR-006 · FR-025 · FR-026 | SC-017 | 见正文 |
| T053 | FR-006 · FR-025 · FR-026 | SC-013 | 见正文 |
| T054 | FR-006 | SC-013 · SC-017 | US6 生命周期回归 |
| T055 | FR-023 · FR-028 · FR-035 | SC-018 | visualization / graph_core 适配 |
| T056 | FR-031 · FR-032 · FR-033 · FR-034 | SC-015 | 见正文 |
| T057 | FR-031 · FR-032 · FR-033 · FR-034 | SC-015 | 见正文 |
| T058 | FR-031 · FR-032 · FR-033 · FR-034 | SC-019 | 见正文 |
| T059 | FR-031 · FR-032 · FR-033 · FR-034 | SC-019 | 见正文 |
| T060 | FR-031 · FR-032 · FR-033 · FR-034 | SC-020 · SC-021 | 见正文（守卫 = 判定载体） |
| T061 | FR-031 · FR-032 · FR-033 · FR-034 | SC-020 · SC-021 | 见正文 ※ |
| T062 | FR-031 · FR-032 · FR-033 · FR-034 | SC-020 | 见正文 ※ |
| T063 | FR-031 · FR-032 · FR-033 · FR-034 | SC-020 | 见正文 ※ |
| T064 | FR-031 · FR-032 · FR-033 · FR-034 | SC-020 | 见正文 ※ |
| T065 | FR-031 · FR-032 · FR-033 · FR-034 | SC-020 | 见正文 ※ |
| T066 | FR-031 · FR-032 · FR-033 · FR-034 | SC-020 | 见正文 ※ |
| T067 | FR-031 · FR-032 · FR-033 · FR-034 | — | D-1…D-4 下游接线（记录/口径交接） |
| T068 | FR-031 · FR-032 · FR-033 · FR-034 | SC-018 | README API 矩阵 |
| T069 | FR-031 · FR-032 · FR-033 · FR-034 | SC-020 | 规模实测登记（写人工记录 §5）※ |
| T070 | FR-007 · FR-008 · FR-035 · FR-031 · FR-032 · FR-033 · FR-034 | SC-005 · SC-014 · SC-018 | 见正文 |
| T071 | FR-005 · FR-021 · FR-022 · FR-036 | SC-021 | 见正文 |
| T072 | FR-005 · FR-021 · FR-022 · FR-036 | SC-021 | 见正文 |
| T073 | FR-037 | SC-022 | 见正文 |
| T074 | FR-024 | SC-023 | 见正文 |

> **SC 反向覆盖核对（与上方 SC 表一致）**
> SC-001 → T044 / T047
> SC-002 → T021 / T022 / T023 / T026
> SC-003 → T028 / T029 / T030 / T031
> SC-004 → T033 / T034 / T035 / T036
> SC-005 → T002 / T003 / T070 / `tests/gates` G24 / G26 / G27
> SC-006 → T009 / T010 / T014 / T038 / T039
> SC-007 → T038 / T040 / T042
> SC-008 / SC-009 → T044 / T045 / T048
> SC-010 / SC-011 → T007 / T021 / T022 / T049
> SC-012 → T044 / T046 / T048
> SC-013 → T049 / T051 / T053 / T054
> SC-014 → T008 / T009 / T020 / **T075** / T070
> SC-015 → T056 / T057
> SC-016 → T049 / T050
> SC-017 → T041 / T049 / T052 / T054
> SC-018 → T004 / T005 / T013 / T020 / T068 / T070
> SC-019 → T058 / T059
> SC-020 → T060 / T061 / T062 / T063 / T064 / T065 / T066 / T069
> SC-021 → T060 / T061 / T071 / T072
> SC-022 → T073 / **T075**
> SC-023 → T074 / **T075**
