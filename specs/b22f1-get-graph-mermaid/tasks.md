# Tasks: B22F1 · `get_graph(xray=)` + 自有 `Graph` 类型 + `draw_mermaid()`

**Input**: Design documents from `/specs/b22f1-get-graph-mermaid/`

**Prerequisites**: `plan.md`（required）· `spec.md`（required）· `research.md` ·
`data-model.md` · `contracts/graph-export-contract.md` · `contracts/upstream-parity.md` ·
`quickstart.md`

**Tests**: **必做** —— 本 feature 的 SC-001…SC-018、D-01…D-15、acceptance.py 均为
判据级要求；每个 user story 先写测试、先失败，再实现。

**Organization**: 按 user story 分组（US1 P1 → US2 P2 → US3 P3）。US2 依赖 US1 的
`Graph` 实例；US3 只增加断网 / 零出站判据，不改变 US1 / US2 的实现。

> ⚠️ **红色基线**：`.venv/bin/python -m pytest -q` = `1661 passed / 4 skipped / 0 failed`
> （2026-11-20 · 108.22s）。系统 `python3`（3.12）的环境性失败**不得**作为基线。

---

## 追溯表（FR → 任务）

| FR | 任务 |
|---|---|
| FR-001 / FR-007 / FR-019 / FR-021 | T021 / T029 |
| FR-002 / FR-004 | T017 / T024 |
| FR-003 / FR-005 / FR-023 | T017 / T019 / T022 / T024 / T027 |
| FR-006 / FR-025 | T019 / T020 / T027 / T028 |
| FR-008 / FR-009 / FR-012 / FR-024 | T021 / T024 / T028 / T029 |
| FR-010 / FR-011 / FR-026 / FR-027 | T005 / T006 / T007 / T009 / T010 / T011 / T012 |
| FR-013 / FR-014 / FR-015 / FR-016 / FR-018 / FR-020 | T032 / T033 / T034 / T035 / T036 / T037 |
| FR-017 | T004 / T040 |
| FR-022 | T022 / T024 |
| FR-028 / FR-029 | T019 / T024 / T026 |

**SC 追溯表**

| SC | 任务 |
|---|---|
| SC-001 | T039 / T041 / T043 |
| SC-002 / SC-005 | T032 / T033 / T036 / T037 / T038 |
| SC-003 / SC-008 / SC-010 | T021 / T029 |
| SC-004 | T021 / T040 / T043 |
| SC-006 | T022 / T034 / T037 |
| SC-007 / SC-013 | T006 / T018 / T025 |
| SC-009 | T021 / T043 / T049 |
| SC-011 / SC-012 | T021 / T029 / T032 / T037 |
| SC-014 | T006 / T012 |
| SC-015 | T006 / T010 / T034 |
| SC-016 / SC-017 / SC-018 | T019 / T024 / T026 / T027 |
| 全部 SC | T042 / T044 / T045 / T046 / T048 |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 记录基线、确认取证环境、建立验收目录。

- [X] T001 Create `harness/verification/B22F1/manual-verification.md` with the five-section skeleton（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）and record the baseline `1661 passed / 4 skipped / 0 failed`（2026-11-20 · `.venv`）
- [X] T002 [P] Verify `.venv/bin/python --version` (3.11.16) / `pytest --version` (9.2.0) and re-run `.venv/bin/python -m pytest -q`; record the exact output in `harness/verification/B22F1/manual-verification.md` §1
- [X] T003 [P] Verify the upstream pin and anchors `langgraph==1.2.11` · `pregel/main.py:845-870` · `pregel/_draw.py:42,138-151,221-257,286-288` · `graph/state.py:810-861,1150-1162,1780-1788` · `runnables/graph_mermaid.py:45,255-266,277,422-423`; record in `specs/b22f1-get-graph-mermaid/research.md` §0.1
- [X] T004 Confirm `pyproject.toml` is unchanged（零新增运行时 / 差分依赖）；record in `harness/verification/B22F1/manual-verification.md` §1

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `Command` 泛型 · `destinations` · `_NodeRecord` 快照 —— 所有 user story 的前置。

**⚠️ CRITICAL**: 本 phase 完成前，任何 user story 不开始。

### 测试先行（先写、先失败）

- [X] T005 [P] Write `tests/contracts/test_types.py` additions: `Command[Literal["b"]]` is subscriptable and does not change fields / `PARENT` / `__slots__` / runtime construction; add a test that `Command(goto="a")` still behaves identically
- [X] T006 [P] Write `tests/facade/test_stategraph_builder.py` additions (先写、先失败): `destinations=("b","c")` / `["b","c"]` / `{"b":"to-b"}` / `None`；`destinations` 覆盖返回注解；未知目标 ⇒ `ValueError`（编译期）；非法形态 ⇒ `TypeError`（登记期）；列表被接受；`Command[Literal["b","c"]]` 推断；注解不可解析 ⇒ 静默；**`destinations` 不进入 `_spec.edges` / `GraphSpec.edges`，且不改变 `invoke()` 的行为/结果**（FR-011）

### 实现

- [X] T007 Implement `Command` generics in `src/freegraph/contracts/types.py`: `N = TypeVar("N", bound=str)`; `class Command(Generic[N])`; import `Generic` / `TypeVar`; 字段 / 构造 / `PARENT` / `__slots__` **逐字不变**; update module docstring（T-1）
- [X] T008 Add `destinations: tuple[tuple[str, str | None], ...] = ()` to `_NodeRecord` in `src/freegraph/_stategraph.py`（按符号定位）; update its docstring; existing positional construction sites keep working（T-3）
- [X] T009 Implement private `_infer_command_destinations(action)` in `src/freegraph/_stategraph.py` **照抄上游 guard**：仅当 `isfunction(action)` / `ismethod(action)` / `ismethod(getattr(action,"__call__",None))` 时取 hints；先 `get_type_hints(action.__call__)` 再回退 `get_type_hints(action)` → unwrap `Union` → `Command` → `Literal` → tuple；`NameError` / `TypeError` / `StopIteration` 静默；登记期调用一次并冻结
- [X] T010 Implement private `_normalize_destinations(value) -> tuple[tuple[str, str | None], ...]` in `src/freegraph/_stategraph.py` for **explicit** values only: 非 `str` 的 `Sequence[str]` → `(target, None)`；`dict[str,str]` → `(target, label)`；空序列 / 空 dict → `()`；非法形态 / 元素非 `str` → 内置 `TypeError`。**MUST NOT** 把 `None` 当作「未提供」信号；`None` 的语义由 T011 在调用前判定
- [X] T011 Extend `StateGraph.add_node` in `src/freegraph/_stategraph.py`（按符号定位） with `destinations: dict[str, str] | tuple[str, ...] | None = None`; **先判 `destinations is None`**：`None` ⇒ `_infer_command_destinations(action)`；否则 ⇒ `_normalize_destinations(destinations)`（空序列 / 空 dict 也覆盖推断）；仅记录到 `_NodeRecord.destinations`，**不得**写入 `_edges` / `GraphSpec.edges` / 调度（T-2）
- [X] T012 Extend `StateGraph._validate_targets` in `src/freegraph/_stategraph.py`（按符号定位）: `node_records[name].destinations` 的每个目标必须是已登记节点或 `END`；否则 `ValueError` 点名目标（编译期）
- [X] T013 Update B2F2 facade snapshot + facade contract: `.venv/bin/python -m pytest tests/facade/test_api_snapshot.py --update-api-snapshot` 后提交 `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt` 的 `add_node(...destinations...)` 行；同步 `specs/b2f2-public-api-facade/contracts/facade-api.md`（若含签名示例）
- [X] T014 Update **exact** B6F1 docs: `specs/b6f1-stategraph-builder/contracts/builder-contract.md` §1（`add_node` 签名行）· §1.2（语义）· §2（失败信号表）；`specs/b6f1-stategraph-builder/contracts/upstream-parity.md` 的 P-02 / X-1 附近**追加** `destinations` 行与 T-2 追认；只追加，既有断言不改写
- [X] T015 Update **exact** B1F1 / B2F1 docs: `specs/b1f1-contracts-core/spec.md`（`Command` 泛型注记 T-1）· `specs/b2f1-contracts-protocols/contracts/public-api.md` 与 `research.md`（`Edge.condition=None` 注记 T-6 · `Graph.draw_mermaid` 注记 T-5）；`README.md` 的 API 兼容矩阵统一由 T047 负责，本任务不重复改 README
- [X] T016 Run `.venv/bin/python -m pytest -q tests/contracts/test_types.py tests/facade/test_stategraph_builder.py tests/facade/test_api_snapshot.py`; record the exact output in `harness/verification/B22F1/manual-verification.md` §2.0

**Checkpoint**: `Command` 泛型可用、`destinations` 可登记 / 推断 / 校验、快照与文档更新、既有测试不弱化。

---

## Phase 3: User Story 1 - 导出图结构做断言 (Priority: P1) MVP

**Goal**: `get_graph()` 从编译快照导出完整的自有 `Graph`（节点 / 静态边 / 条件边 /
节点声明边 / join / 终结 `END` / metadata），且**零执行、运行前后一致**。

**Independent Test**: 编译一张含条件边 + `Command[Literal]` + `destinations` + join 的图；
不调用 `invoke()`，断言节点集合、边端点、`conditional` / `condition`、`xray` 等价、
不可达节点无出边、join 每源一条边。

### Tests for User Story 1（先写、先失败）

- [X] T017 [P] [US1] Write `tests/runtime/test_graph_export.py`（新文件 · 署名头）: 节点集合含 `__start__` + 业务 + `__end__`；`__start__` / `__end__` 的 `id == name`；静态边 / 条件边 / `END` 边 / 终结补边的形状；`conditional=True` 的 `condition`
- [X] T018 [US1] Write `tests/runtime/test_graph_export.py` declaration cases: `Command[Literal["b","c"]]` → 两条边；`destinations` → 标签；`destinations` 覆盖推断；多目标不合并；未知目标在 `compile()` 前失败
- [X] T019 [US1] Write `tests/runtime/test_graph_export.py` topology cases: 不可达节点只在 `nodes`；不可满足 join 不导出组边；两源可达 join → 每源一条普通边；同端点静态 + 条件 → 只一条且条件优先；循环 / 自环按 X-08 不补模拟性 END
- [X] T020 [US1] Write `tests/runtime/test_graph_export.py` metadata cases: `metadata` 浅拷贝；`defer=True` → `defer: True`；`interrupt_before` / `after` → `__interrupt` = `before` / `after` / `before,after`
- [X] T021 [P] [US1] Write `tests/facade/test_get_graph.py`（新文件 · 署名头）: `get_graph` 关键字 `xray`；`xray=True` vs `False` 逐项相等；**`xray=1` / `xray=0` 等真值/假值不抛 `TypeError` 且结果同 `True`/`False`（FR-021）**；运行前 / 运行后逐项相等；`stream()` 前后逐项相等；返回类型 `freegraph.contracts.graph.Graph`；`get_graph` 不调用节点 / 不抛
- [X] T022 [P] [US1] Write `tests/runtime/test_conditional_edge_surface.py` additions: `add_conditional_edges` 的每个目标各一条边、`condition == branch`、路由通道不出现在 `nodes`
- [X] T023 [P] [US1] Add **graph-export** differential support to `tests/differential/parity_probe.py` per `contracts/upstream-parity.md` §3: 新增 `GraphScenario`（`name` / `verdict` / `note` / `fg` / `up`）+ `_run_graph_scenarios()`（比较节点 id 集合与 `(source,target,conditional,condition)` 边集合）；D-04 的 `STRICTER` 断言 freegraph mermaid 合法性（不比较上游文本）；D-12 显式断言「上游多一条末步 `→__end__`、freegraph 无」（覆盖自环 + 循环）；在 `tests/differential/test_parity_probe.py` 增加调用；上游缺席即 skip

### Implementation for User Story 1

- [X] T024 [US1] Implement `_EdgeGroup` (frozen dataclass) + private `_export_graph(...)` in `src/freegraph/_stategraph.py`: build nodes（`__start__` + `spec.nodes` + `__end__`）; static single-source groups from `_spec.edges`; recover `END` groups from `_builder_spec.edges`; join groups from tuple keys; conditional groups from `_conditional_edges`
- [X] T025 [US1] Implement declaration groups in `_export_graph` in `src/freegraph/_stategraph.py`: iterate `builder_spec.node_records` in `spec.nodes` order; each `(target,label)` → `_EdgeGroup((name,), target, True, label)`; `END` → `__end__`
- [X] T026 [US1] Implement static reachability in `_export_graph` in `src/freegraph/_stategraph.py`: `reachable={"__start__"}`; iterate groups until fixpoint (`all(src in reachable)` ⇒ add target); only emit satisfiable groups; `__end__` is a sink
- [X] T027 [US1] Implement terminal `END` edges + dedupe in `_export_graph` in `src/freegraph/_stategraph.py`: reachable node with no emitted outgoing edge ⇒ `Edge(node,"__end__",False,None)`; dedupe by `(source,target)` with `conditional=True` winning, else first-wins; preserve deterministic order
- [X] T028 [US1] Implement node metadata + `__interrupt` in `_export_graph` in `src/freegraph/_stategraph.py` per `contracts/graph-export-contract.md` §2.2; MUST shallow-copy user metadata and MUST NOT mutate `_builder_spec` / `_spec`
- [X] T029 [US1] Replace the `CompiledGraph.get_graph` stub in `src/freegraph/_stategraph.py`（按符号定位；当前约 `:572`）: validate keyword-only `xray`; return `_export_graph(self._spec, self._builder_spec, self._conditional_edges, self.interrupt_before_nodes, self.interrupt_after_nodes)`; v1 ignores truthiness; MUST NOT execute / call `stream()`
- [X] T030 [US1] Update R-01 / R-02 old assertions: `tests/runtime/test_conditional_edge_surface.py` 与 `tests/facade/test_compiled_graph.py`（按 `get_graph` 未实现列表定位；当前约 `:101` / `:76`）— remove `get_graph` from the "unimplemented" lists, add positive assertions; **split-don't-delete**
- [X] T031 [US1] Run `.venv/bin/python -m pytest -q tests/runtime/test_graph_export.py tests/facade/test_get_graph.py tests/runtime/test_conditional_edge_surface.py tests/facade/test_compiled_graph.py`; record exact output in `harness/verification/B22F1/manual-verification.md` §2.1

**Checkpoint**: US1 独立可验收 —— 无运行即可拿到完整图结构，MVP 成立。

---

## Phase 4: User Story 2 - 生成 mermaid 文本用于评审 (Priority: P2)

**Goal**: `Graph.draw_mermaid()` 返回合法、确定、含全部节点名的 mermaid 文本；
条件边虚线 + 标签（无标签仅虚线）。

**Independent Test**: 对 US1 的 `Graph` 调用 `draw_mermaid()`；断言首行 `graph TD;`、
含全部节点名、普通边 `-->`、条件边 `-.` / `.->`、特殊字符转义、重复调用逐字相同。

### Tests for User Story 2（先写、先失败）

- [X] T032 [P] [US2] Write `tests/contracts/test_graph.py` additions: `Graph.draw_mermaid` exists; empty graph returns non-empty `str`; header / 每条行以 `;` 结尾；`nodes` 全部出现；determinism（两次逐字相等）；`Edge(conditional=True, condition=None)` 合法且 `draw_mermaid` 不抛（T-6）；no `mermaid.ink` / `http` / `https`
- [X] T033 [US2] Write `tests/contracts/test_graph.py` escaping cases: `a"b` / `x\ny` / `p|q` / `#` / `\` / `&` / `<` / `>` / `{p}` / **中文节点名** / **emoji 节点名**; `_safe_id` 形态（`a\22b` / `x\ay`；非 ASCII 转为 `\` + hex）；标签实体（`#quot;` / `<br/>` / `#124;` / `#92;` / `#35;`）；不同节点名不碰撞
- [X] T034 [US2] Write `tests/runtime/test_graph_export.py` mermaid integration: conditional edge label（`route` / `destinations` 标签）；`condition is None` 仅虚线；join / 终结 `END` 边；空图；特殊字符节点
- [X] T035 [US2] Implement private `_safe_id(label)` in `src/freegraph/contracts/graph.py`: `[A-Za-z0-9_-]` 原样，其它 `\` + lowercase hex codepoint（上游 `_to_safe_id` 同款）
- [X] T036 [US2] Implement private `_escape_label(text)` in `src/freegraph/contracts/graph.py`: 先 `#` → `#35;`，再 `"` / 换行 / `<` / `>` / `&` / `\|` / `\` 的实体映射；MUST be deterministic and idempotent-safe（不二次转义）
- [X] T037 [US2] Implement `Graph.draw_mermaid()` in `src/freegraph/contracts/graph.py`: header `graph TD;`; node lines `\t{id}["{label}"];`; plain `-->`; conditional `-. &nbsp;{label}&nbsp; .->` or `-.->`; empty graph `graph TD;\n`; 零 import 副作用 / 零网络 / 零环境变量（T-5）
- [X] T038 [US2] Run `.venv/bin/python -m pytest -q tests/contracts/test_graph.py tests/runtime/test_graph_export.py`; record exact output in `harness/verification/B22F1/manual-verification.md` §2.2

**Checkpoint**: US2 独立可验收 —— mermaid 文本合法、确定、可读。

---

## Phase 5: User Story 3 - 断网也能出图 (Priority: P3)

**Goal**: `draw_mermaid()` 在断网 / 零出站环境下必然成功；框架出站计数 == 0。

**Independent Test**: socket 监测夹具下调用 `draw_mermaid()`；断言成功、返回非空 `str`、
出站计数为 0；同时扫描图导出模块无 `socket` / `urllib` / `http` / `subprocess` import。

### Tests & Verification for User Story 3

- [X] T039 [P] [US3] Write `tests/runtime/test_graph_offline.py`（新文件 · 署名头）: monkeypatch `socket.socket` → 计数并抛错；`draw_mermaid()` 仍成功；计数 == 0；`get_graph()` 同样零出站
- [X] T040 [US3] Write `tests/runtime/test_graph_offline.py` static checks: `src/freegraph/contracts/graph.py` / `src/freegraph/_stategraph.py` 的**代码体**不含 `mermaid.ink`；不含 `os.environ` / `os.getenv`；不 import `socket` / `http` / `urllib` / `subprocess`。**MUST NOT** 对 `http://` / `https://` 做 blanket 扫描——署名头含项目 GitHub URL（原则 X），扫描口径 MUST 排除首行版权头
- [X] T041 [US3] Run `.venv/bin/python -m pytest -q tests/runtime/test_graph_offline.py tests/contracts/test_graph.py`; record exact output in `harness/verification/B22F1/manual-verification.md` §2.3

**Checkpoint**: US3 独立可验收 —— 断网必然成功、零出站。

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 差分、一键验收、人工记录、基线回归。

- [X] T042 Run differential probe `.venv/bin/python -m pytest -q tests/differential/test_parity_probe.py`（图导出场景随 `_run_graph_scenarios()` 收集；上游缺席即 skip）; record pass/skip/output in `harness/verification/B22F1/manual-verification.md` §3
- [X] T043 [P] Create `harness/verification/B22F1/acceptance.py`（署名头；退出码 0/1/2；打印 `B22F1 acceptance: PASS|FAIL`）：覆盖 A1（断网 `draw_mermaid`）、A2（出站 0）、A3（`xray` 两例）、A4（自有类型 + 依赖门禁）
- [X] T044 Create `tests/runtime/test_graph_acceptance.py`（署名头）: subprocess 真跑 `harness/verification/B22F1/acceptance.py`；断言退出码 0 且 stdout 含 `B22F1 acceptance: PASS`
- [X] T045 Update `harness/verification/B22F1/manual-verification.md`: 五段式实际输出（MUST NOT 伪造）；A1–A4 逐条结论；T-1…T-6 追认文字（发起者 2026-11-20 · 承接方 B22F1）
- [X] T046 **必做**：新增/扩展 `tests/runtime/test_graph_manual_record_guard.py`（署名头；参考既有 `test_manual_record_guard.py` 模式）：断言 `harness/verification/B22F1/manual-verification.md` 存在、五个必需段落非空、A1–A4 与 T-1…T-6 追认文字非空、实测输出段非占位；安排在 T045 之后，MUST NOT 造成永久红 CI
- [X] T047 Update `README.md` 的 API 兼容矩阵：`Command` 泛型 · `add_node(destinations=)` · `Graph.draw_mermaid` · `Edge.condition=None`（节点声明边）；MUST NOT 漏记（原则 X）
- [X] T048 Re-run the full baseline `.venv/bin/python -m pytest -q`; 逐条核对 plan.md「变红清单」R-01…R-08；确认无新增红；把最终计数写入 `harness/verification/B22F1/manual-verification.md` §5
- [X] T049 Run `quickstart.md` §1–§8 的手工命令；核对 §1 / §2 / §3 / §4 / §5 / §6 的期望输出；§9 为人工记录说明，其结果由 T045 写入 `harness/verification/B22F1/manual-verification.md`
- [X] T050 [P] Update `specs/b9f1-command-primitive/spec.md` 下游承接 D-8：**只补注记**「已被 B22F1 的静态声明取代（T-4，发起者 2026-11-20）」；运行期 `goto` 语义/断言全部保留

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: 无依赖，立即开始。
- **Phase 2 Foundational**: 依赖 Setup；**阻塞所有 user story**。
- **Phase 3 US1**: 依赖 Phase 2；产出 `Graph`。
- **Phase 4 US2**: 依赖 US1（需要真实 `Graph`）；可与 US3 并行。
- **Phase 5 US3**: 依赖 US2（`draw_mermaid` 已存在）；可与 US2 的测试并行准备。
- **Phase 6 Polish**: 依赖 US1 / US2 / US3 完成。

### User Story Dependencies

- **US1（P1）**：无其它 story 依赖；MVP。
- **US2（P2）**：需要 US1 的 `get_graph` 产出。
- **US3（P3）**：需要 US2 的 `draw_mermaid`。

### Within Each User Story

- 测试先写并失败 → 实现 → 回归。
- 数据类 / 归一化先于导出算法；导出算法先于门面。
- 文档与快照更新在实现之后、Polish 之前。

### Parallel Opportunities

- Phase 1：T002 / T003 可并行；T004 在 T002 之后（同一 `manual-verification.md`，串行）。
- Phase 2：T005 / T006 并行；T008 / T009 / T010 串行（同文件）；T013 / T014 / T015 可并行（不同文档）。
- US1：T017 先创建 `test_graph_export.py`；T018 → T019 → T020 紧随其后追加（同文件，串行）；T021 / T022 / T023 可与 T017 并行（不同文件）。T024 → T025 → T026 → T027 → T028 → T029 串行（同文件）。
- US2：T032 先改 `test_graph.py`；T033 紧随其后追加（同文件，串行）；T034 在 T032/T033 之后（追加 `test_graph_export.py`）；T035 → T036 → T037 串行。
- US3：T039 先创建 `test_graph_offline.py`；T040 紧随其后追加（同文件，串行）。
- Polish：T043 / T047 / T050 可并行；T042 → T049 → T044 → T045 → T046 → T048 串行（`manual-verification.md` / 验收 / 记录守卫依赖）。

---

## Parallel Example: User Story 1

```bash
# 先并行写不同文件
Task: "Create tests/runtime/test_graph_export.py node/edge cases"
Task: "Write tests/facade/test_get_graph.py"
Task: "Add GraphScenario + D-01…D-15 to tests/differential/parity_probe.py"

# test_graph_export.py 的后续追加（同文件，串行）
Task: "Append declaration cases"
Task: "Append topology cases"
Task: "Append metadata cases"

# 再串行实现导出算法（同一文件）
Task: "_EdgeGroup + static/conditional/join groups"
Task: "declaration groups"
Task: "reachability"
Task: "terminal END + dedupe"
Task: "metadata + __interrupt"
Task: "replace get_graph stub"
```

---

## Implementation Strategy

### MVP First（仅 US1）

1. 完成 Phase 1 / Phase 2。
2. 完成 US1（T017–T031）。
3. **STOP & VALIDATE**：不运行图即可得到完整 `Graph`；`xray=True ≡ False`。
4. 再进入 US2（mermaid）与 US3（断网）。

### Incremental Delivery

- **增量 1（US1）**：图结构断言可用（C13）。
- **增量 2（US2）**：mermaid 文本可贴评审（C14）。
- **增量 3（US3）**：断网 / 零出站判据闭环（原则 I）。
- **收尾**：差分 + 一键验收 + 人工记录 + 全量回归。

### 关键风险与处置

| 风险 | 处置 |
|---|---|
| `Command` 泛型破坏既有运行期测试 | T005 先锁字段 / `PARENT` / `__slots__`；T007 后只加 `Generic` |
| `destinations` 误入执行路径 | T011 只写 `_NodeRecord`；T016 断言 `_edges` / `GraphSpec` 不变 |
| 图导出多出 / 少边 | T019 / T023 锁 D-11…D-15 与 X-08；T026 静态闭包 |
| mermaid 特殊字符非法 | T033 覆盖 `"` / 换行 / `\|` / `\` / `#`；T036 先转义 `#` |
| 断网测试假绿 | T039 monkeypatch `socket.socket` 并断言计数 == 0 |
| 破冻结面漏记 | T013 / T014 / T015 / T047 / T050 逐项更新快照、契约、矩阵、追认 |
| 环境性红 | 全程使用 `.venv`；T002 / T048 记录真实输出 |

---

## 完成判据（DoD）

- [X] `.venv/bin/python -m pytest -q` 全绿（≥ 基线 1661 passed，0 failed）。
- [X] `harness/verification/B22F1/acceptance.py` 退出码 0，打印 `B22F1 acceptance: PASS`。
- [X] A1–A4 全部通过（离线 / 零出站 / `xray` / 自有 `Graph`）。
- [X] D-01…D-15 全部按判词通过（上游缺席时 skip）。
- [X] T-1…T-6 的回溯修订、兼容矩阵、人工追认全部落库。
- [X] `harness/verification/B22F1/manual-verification.md` 五段式完整、实测输出非空、无伪造。
