# Tasks: B7F3 · `invoke()` 返回完整状态 + `InvalidUpdateError`

**Input**: Design documents from `specs/b7f3-invoke-full-state/`

**Prerequisites**: plan.md · spec.md · research.md · data-model.md · contracts/ (`invoke-contract.md` / `upstream-parity.md`) · quickstart.md · checklists/requirements.md

**Tests**: 本任务列表**包含测试任务**。理由：spec 的 SC-001…SC-020 要求**可执行判据**；宪法原则 VI 要求每条 SC 至少挂一条**能判定它**的测试任务；仓库既有 feature（B7F2 等）均以 pytest 为实现门禁。⇒ ⇒ **每个用户故事一个测试文件**（6 个）⇒ 故事之间**零文件冲突**、可独立并行。

**Organization**: 按 spec 的 **7** 个用户故事组织（US1…US7），每个故事可独立验证。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 不同文件、无未完成依赖，可并行
- **[Story]**: `[US1]`…`[US7]`，仅用户故事阶段使用
- 每个任务均带明确文件路径

## Path Conventions

- 实现：`src/freegraph/_stategraph.py`（L3 **单文件** · 层注册表冻结 ⇒ **MUST NOT 新建源文件**）
- L1 协议：`src/freegraph/contracts/protocols.py`（**唯一**破面 · 两处注解放宽）
- 测试：`tests/facade/`（**每故事一个文件**）· `tests/differential/` · `tests/runtime/`
- 验收：`harness/verification/B7F3/` · `harness/demo/`
- 门禁：`harness/scripts/gates/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 确认绿基线与「invoke 未就绪」的冻结断言清单；建立共享夹具与测试骨架

- [X] T001 Confirm the current baseline: run `.venv/bin/python -m pytest tests/ -q` and **record the pass/skip/fail counts**（**三个数**）**in this task's own checklist note** ⇒ ⇒ ⚠️ **MUST NOT** write into `harness/verification/B7F3/manual-verification.md` at this stage —— that file is **created by T044** ⇒ ⇒ ⇒ ⇒ writing to it here would be a write to a **not-yet-existing** file ⇒ ⇒ ⇒ ⇒ ⇒ **T044 MUST transcribe these counts into its §1 环境段**；then **list**（**not** finalize）the **four** candidate frozen "invoke is not wired" assertions: `tests/facade/test_compiled_graph.py:73-86`（`calls` 映射里的 `"invoke": (({},), "B7F3")` 条目）· `tests/facade/test_facade.py:195-200`（`test_compile_reports_invoke_b7f3`）· `tests/facade/test_facade.py:217-234`（`calls` 元组里的 `("invoke", ({},))` 条目）· `tests/runtime/test_acceptance_script.py:15-34`（`graph_core` 退出码 == 2 的断言）⇒ ⇒ ⚠️ **本条只立「候选」清单** —— 宪法 v1.12.0 的「**冻结断言清单 MUST 实测化**」要求在**实现之后**才能完成（改动源码 ⇒ 跑套件 ⇒ **变红**者才入清单）⇒ ⇒ ⇒ ⇒ ⇒ **实测归 T011**（T010 之后）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 只凭推理登记（SC-019 · 宪法 v1.12.0「基线义务」· **FND-H5**）
- [X] T002 [P] Create shared invoke-test support in `tests/facade/_invoke_support.py` **with the repository copyright/license header**（G30）：`State` schema（`messages: Annotated[list, operator.add]` + `llm_calls: int`，与 `harness/demo/graph_core.py:124-128` **逐字同款**）· node stubs returning partial dicts · a `CallCounter` · ✅ **a self-contained stub checkpointer**（⚠️ **2026-11-16 analyse 轮 · 第三轮回修（**FND-A4**）· 恢复路径的载体**）：**MUST** 逐字按契约 §4 **F-05** 冻结的清单实现（**3 个**方法：`get_tuple` / `put` / `put_writes` + `get_tuple` 返回值的**三个具名属性** `.snapshot` / `.pending_writes` / `.scheduler` ⇒ ⇒ **MUST NOT** 多实现 `list` / `delete_thread` / `delete_for_runs` / `copy_thread` / `get_next_version` 这 5 个 **L2 恢复路径不调用**的协议方法 ⇒ ⇒ **MUST NOT** 以「等最小集」这类**开放表述**自行取舍）⇒ ⇒ ⇒ 只存**最小**载荷、**自足**（不依赖仓库其它模块）⇒ ⇒ ⇒ ⇒ **形态参照** `tests/differential/parity_probe.py:251-255`（B10F1 的**桩** checkpointer · 探针自足）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **用途**：**仅供测试**（`compile(checkpointer=...)`）⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · M1 回修**（**与上句同款 · 本条为唯一权威表述**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 判据：桩「够不够」由契约 F-05 的方法集判定⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 在 `src/freegraph/**` 内实现任何 saver（`MemorySaver` / `SqliteSaver` 归 **B14F1** · 宪法原则 IV「MUST NOT 提供『不挂 checkpointer 也能恢复』的内存态旁路」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **T029① MUST 挂本桩**（否则「恢复后拿到 resume 值」无载体 ⇒ SC-010 不可判定 ⇒ 仓库既有验收脚本 `graph_core.py:392-393` / `agent_loop.py:275-280` 已把该路径定为 soft 且注「载体待 B14F1 锁定」（⚠️ **2026-11-16 analyse 轮第五轮行号订正** · **FND-F1**：`graph_core.py` 的 soft() 调用与注记实际在 **:392-393**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 写进 `src/`（那里**零** saver 实现）· **MUST NOT** 进发行包 · `build_two_node_graph()`（`START→a→b→END`）· `build_loop_graph()`（自环 ⇒ 供 `recursion_limit` 用例）⇒ ⇒ ✅ `build_conditional_graph()`（含 `add_conditional_edges(src, path_fn, path_map)`）**本 feature 用**（**路由通道排除**的判据载体 · 契约 **I-03** / FR-012 / 裁定 4）⇒ ⇒ ⚠️ **MUST 带 `path_map`**（**只有 `path_map` 非空时** `_stategraph.py:530-540` 才会建 `branch:to:<target>` 的 `EphemeralValue` 通道 ⇒ ⇒ ⇒ 否则**无路由通道可排除** ⇒ ⇒ ⇒ ⇒ 该断言将**恒真** ⇒ ⇒ ⇒ ⇒ ⇒ **空洞**）⇒ ⇒ ⇒ ⚠️ **MUST NOT** 断言「路由求值生效」（**路由求值归 B8F1** · FR-026）⇒ ⇒ ⇒ ⇒ ⇒ 本图**只**用于断言「路由通道**不进**返回键集」⇒ ⇒ ⇒ ⇒ ⇒ 若 B8F1 另建夹具 ⇒ 本条可作废（**MUST NOT** 留两处）⇒ ⇒ ✅ **`build_fanout_graph()`**（`START→a` / `START→b` ⇒ **两个节点落在同一 super-step** ⇒ **并发**；⚠️ **2026-11-16 analyse 轮 · 第三轮回修（**FND-B4** · 夹具形态消歧）**：该夹具**不含** join 边 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **T017⑦ MUST 自行追加** `add_edge(["a", "b"], "c")`（屏障半边）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 另造第二个 fan-out 夹具（零漂移）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第五轮补齐**：该夹具 **MUST 含一个名为 `c` 的节点**（**注册但暂不被任何边引用**）⇒ ⇒ 否则 T017⑦ 的 `add_edge(["a", "b"], "c")` 会指向**未注册节点**⇒ ⇒ ⇒ ⇒ 编译期即失败 ⇒ ⇒ ⇒ ⇒ ⇒ **判据载体不完整** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST** 显式写明这一点 · **FND-E2**）**本 feature 用**（**SC-006 的「可观测并发度」判据载体** —— ⚠️ **必须同 super-step** ⇒ 串行图（`build_two_node_graph()`）**恒不重叠** ⇒ 该断言将**恒假**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **T017⑦ 与 T027 MUST 复用本夹具**（**MUST NOT** 另建 ⇒ 零漂移）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 复用 `tests/facade/_builder_support.py` 的既有替身 ⇒ **MUST NOT** 重复造（SC-001 · SC-002 · SC-006 · SC-007（夹具）· **FND-H4**）
- [X] T003 [P] Create the **six** test module skeletons **with headers and module docstrings** in `tests/facade/`: `test_invoke_full_state.py`（US1 + US2 ⇒ **两者共用这一份** ⇒ 两者**串行**）· `test_invoke_errors.py`（US3）· `test_invoke_config.py`（US4）· `test_invoke_interrupt.py`（US5）· `test_invoke_isolation.py`（US6）· `test_invoke_purity.py`（US7）⇒ ⇒ **六个文件互不重叠** ⇒ 除 US1/US2 外，其余故事**互不依赖、可并行**（SC-001…SC-020（测试骨架）） ⚠️ **2026-11-16 analyse 轮第五轮 · FND-B10 补注**：本条**只建空骨架**（署名头 + 模块 docstring） ⇒ 与后续**填充**同一批文件的 T017 / T020 / T022 / T025 / T028 / T029 / T031 / T033 **按阶段天然串行**（本条在 **Phase 1** · 填充任务在 **Phase 3+**）
- [X] T004 [P] Create `harness/verification/B7F3/` with an `acceptance.py` skeleton **with header**（退出码约定：`0` = PASS · `1` = FAIL · `2` = 环境未就绪；`check(cond, label)` 助手；`from freegraph.graph import ...` 失败 ⇒ `raise SystemExit(2)`）（SC-001…SC-010（验收承载））

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: L1 协议放宽 + `invoke` 的**机械主链**（驱动 L2 + 完整状态归一）+ **验收脚本的实测化与分级** + **冻结断言的拆分替换**（**所有用户故事共享**）

**CRITICAL**: 本阶段完成前，任何用户故事都不得开始；**T014 MUST 在本阶段内完成**，否则基线变红。
⚠️ **T011（本阶段新增 · 2026-11-16 analyse 轮）** MUST 在 **T010** 之后执行（`invoke` 接通 ⇒ 验收脚本才首次真正跑到用例组）⇒ ⇒ 它的产出（**实测红点**）是 **T040 / T042**（降级范围）的**事实依据**。
⚠️ **2026-11-16 analyse 轮 · 第三轮回修（**FND-A3 · CRITICAL**）· 阶段编排**：原编排把 **T040 / T041 / T042**（验收脚本分级 + 修陈旧断言）排在 **Phase 10** ⇒ ⇒ 但 **T010 接通 `invoke`** 后 `graph_core.py` 必以 `rc == 1` 结束（既有陈旧断言 `graph_core.py:509-512` + 依赖 **B8F1 / B8F3** 的 A5 / A6(C16) / A9(context) / A10 组）⇒ ⇒ ⇒ ⇒ ⇒ T014④ 的 `rc == 0` 断言在 Phase 2 **自身必红** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **Phase 2 的「pytest 全绿」门禁不可达成** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **违反宪法 v1.6.0 红线「MUST NOT 写永久红的 CI」** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **处置（发起者 2026-11-16 拍板）**：**T040 / T041 / T042 前移到本阶段**（置于 **T011** 之后 ⇒ **先登记实测红点 · 再据实分级**）⇒ ⇒ **T014 移至本阶段末尾**（**脚本先修绿 · 再替换冻结断言**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **红窗收敛为阶段内的「T010 → T014」窗口**（宪法 v1.12.0「冻结断言清单 MUST 实测化」**强制要求**在实现落地之后才完成 ⇒ 该窗口**必然存在**且**有界**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **Phase 10 只留 T051 / T052**（全量回归 + 一致性复核）。
⚠️ **任务号保持不变**：**T040 / T041 / T042 仅换阶段、不换 ID** ⇒ ⇒ ⇒ 所有跨工件的引用（spec / plan / contracts / 本文件的追溯表）**无需改动**。

- [X] T005 Widen the L1 protocol `invoke` signature in `src/freegraph/contracts/protocols.py:270-272` to `invoke(self, input: StateDict | Command | None, config: RunConfig | Mapping[str, Any] | None = None) -> StateDict`（**上游同款** · `langgraph/pregel/main.py:3836-3838`；`config` 的放宽与 L2 的 `run_graph` **逐字同款** · `superstep.py:1924`）⇒ update the docstring table rows at `:240` / `:263` to say「**自 B7F3 起已交付 / 放宽**」⇒ ⇒ ⚠️ **必要伴随改动（C1 · CRITICAL · MUST 与本条同批）**：`src/freegraph/contracts/protocols.py:22` 的 `from collections.abc import Iterator, Sequence` **MUST** 改为 `from collections.abc import Iterator, Mapping, Sequence`（⚠️ **2026-11-16 analyse 轮 · 第三轮回修 · 行号订正**：原写「`:26` 的 import」⇒ **`:26` 实为 `from .trace import Span`**（内部模块导入）⇒ **改它会误伤 import** ⇒ ⇒ **正确目标是 `:22`**）—— ⚠️ 该模块**无** `from __future__ import annotations` ⇒ ⇒ ⇒ ⇒ 注解在**类体求值期**解析 ⇒ ⇒ ⇒ ⇒ 缺 `Mapping` ⇒ `NameError: name 'Mapping' is not defined` ⇒ ⇒ ⇒ ⇒ ⇒ **在 `import freegraph` 时抛出**（已实测复现）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 全仓不可导入 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 本条**不得**在补该 import 之前合入（否则 G1–G30 与全量 pytest 一起红）⇒ ⇒ ⚠️ **MUST NOT** 改 `protocols.py:26` 的 `from .trace import Span`（那是**内部模块导入** · 与本条无关）⇒ ⇒ ⚠️ **MUST NOT** touch `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`（that snapshot renders the **facade export surface only** ⇒ contains **no** `invoke` line ⇒ editing it turns **G16** red）（FR-001 · 裁定 1 · SC-019 · **C1**）
- [X] T006 Back-revise the frozen public-API doc in `specs/b2f1-contracts-protocols/contracts/public-api.md`: row `:82`（the `CompiledGraph` row）and row `:195`（the **C11** row）⇒ **拆分而不删**（keep the original text, append a **pointer** note）⇒ ⇒ ⚠️ **这两行不含 `input`/`config` 的注解原文**（`:82` 写的是「返回类别已冻结；参数名按 `data-model.md` §2.5 冻结为占位名」）⇒ ⇒ ⇒ ⇒ 「标注放宽」**无字面锚点** ⇒ ⇒ ⇒ ⇒ ⇒ 故 MUST 写成**指向性**注记：「**协议注解自 B7F3 起放宽**（`input: StateDict | Command | None` + `config: RunConfig | Mapping[str, Any] | None` ⇒ 详见 `src/freegraph/contracts/protocols.py`）」⇒ ⇒ ⇒ ⇒ ⇒ **字面锚点**在 `protocols.py:240` 的 docstring 表格行（**由 T005 标注**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** add / remove / reorder any other row (G19 byte-compare)（FR-001 · 裁定 1 · SC-019 · G19 · **L1**）
- [X] T007 Replace the stub in `src/freegraph/_stategraph.py:259-261` with the real signature `def invoke(self, input: StateDict | Command | None, config: RunConfig | Mapping[str, Any] | None = None) -> StateDict`（**`input` 必填位置参数** · 上游同款）and a docstring that MUST contain 「**返回值是只读快照 · 不要原样回喂给下一次 `invoke`**」**and its reason**（回喂会把补齐的 `None` 真的写进通道 ⇒ 节点里 `state.get("llm_calls", 0) + 1` 会 `TypeError`）⇒ ⇒ body stays a `NotImplementedError` placeholder until T010 lands (keeps the suite green between T007 and T010)⇒ ⇒ ⚠️ **MUST** 保留现桩上的 `# noqa: A002`（`input` 遮蔽内置名 · 去掉 ⇒ lint 红）（FR-001 · FR-009 · 裁定 1 / 3 · SC-020）
- [X] T008 Extend the imports in `src/freegraph/_stategraph.py`: ① add `run_graph` **+** `InterruptResult` **+** `SuperStepResult` into the existing `from .runtime import (...)` block（**三者已在 `freegraph.runtime.__all__` ⇒ 导出面仍 23** ⇒ 不扩导出面）② add `Command` **+** `RunConfig` **+** `StateDict` into the existing `from .contracts import (...)` block（T007 的注解 `StateDict | Command | None` / `RunConfig | Mapping[str, Any] | None` **MUST** 可解析 —— 该模块有 `from __future__ import annotations` ⇒ 注解是**惰性字符串** ⇒ 漏导入**不会**在 import 期炸，但 `get_type_hints()` 会抛 `NameError`）③ ⚠️ **MUST NOT** 再导入 `collections.abc.Mapping`（**`_stategraph.py:34` 已导入** ⇒ 重复导入 ⇒ lint 红）⇒ ⇒ ⚠️ **MUST NOT** add any symbol to `freegraph.runtime.__all__`（it stays at **23**）⇒ ⇒ ⚠️ **MUST NOT** create a new source file (层注册表冻结 · G25 禁 L3→L3)（FR-002 · 裁定 4 · SC-016 · **FND-H2 / FND-H3 / FND-M3**）
- [X] T009 Add the module-level private helper `_full_state(spec, sparse) -> dict` in `src/freegraph/_stategraph.py`（**单一实现点** · downstream **B8F2** MUST reuse it · 下游承接 D-1）: key set = `[k for k, ch in spec.channels.items() if not isinstance(ch, EphemeralValue)]`（**保序** · 路由通道判定 MUST use the B7F1 frozen criterion `isinstance(channel, EphemeralValue)` · **MUST NOT** use a `branch:to:` name-prefix heuristic）⇒ value = `sparse.get(k, None)`（⚠️ **MUST NOT** treat「值为 `None`」as「无值」）⇒ ⇒ if `"__interrupt__"` is present in `sparse`, **keep** it (append at the end; never overwrite, never reorder)⇒ ⇒ **MUST NOT** add a 4th private field to `CompiledGraph`（B7F2 冻结面 · `vars()` stays exactly **11** keys）（FR-008 · FR-009 · FR-012 · 裁定 2 / 3 / 4 · SC-001 / SC-003）
- [X] T010 Implement the execution body of `invoke` in `src/freegraph/_stategraph.py`: ① pass `config` **verbatim** to `run_graph(config=...)`（**MUST NOT** translate a mapping into a `RunConfig`）② call `run_graph(self._spec, input, checkpointer=self.checkpointer, config=config)` ⇒ **MUST NOT** pass `state=`（⇒ L2 builds a fresh `SchedulerState()` and fresh channel instances per call · `superstep.py:1965` / `:575-591`）③ normalize the result: `InterruptResult` ⇒ **first** `as_result_dict()`（the **only** conversion path）⇒ **then** `_full_state`; `SuperStepResult` ⇒ `.state` ⇒ `_full_state` ④ **zero `try`/`except`** ⇒ every failure signal propagates with its **original type and message**（`InvalidUpdateError` / `GraphRecursionError` / `InterruptError` / user exceptions）⑤ **MUST NOT** re-implement input writes, resume decisions or routing（all owned by L2）（FR-002 · FR-004 · FR-005 · FR-013 · FR-014 · 裁定 3 / 8 / 10 · SC-002 / SC-010）
- [X] T011 **首次执行两个验收脚本并据实登记红点**（宪法 v1.12.0「冻结断言清单 MUST 实测化」· **MUST NOT** 只凭推理登记）: `invoke` 接通后（**T010 之后**）先跑 `harness/demo/graph_core.py` 与 `harness/demo/agent_loop.py` ⇒ ⇒ 把**首次变为可达**的用例组的真实结果逐条记录（红的写**红点** + 原因 + 是否依赖未交付 feature）⇒ ⇒ ⚠️ **A1 / A2 / A4 / A7 / A8 此前从未执行过**（长期被就绪探针 `_invoke_ready()` 挡住 ⇒ `graph_core.py` 以退出码 2 结束）⇒ ⇒ ⇒ **本条的产出落「本任务自带的 checklist note」**（**不写** `manual-verification.md` —— 该文件由 **T044** 创建 ⇒ 提前写 ⇒ 撞 T001 的禁令 + 产生半成品文档）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **T044 MUST 转录本条的实测结果**（与 T001 的绿基线计数一并）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 记录结果 MUST 作为 **T040 / T042**（降级范围）的**事实依据**（⇒ ⇒ 「降级」只针对**依赖未交付 feature** 的红点 ⇒ ⇒ ⇒ 与本 feature 无关的红点 MUST 单独登记并据实处理，**MUST NOT** 顺手降级）⇒ ⇒ ⇒ **同时**完成宪法 v1.12.0 的「**冻结断言清单 MUST 实测化**」（**T001 只立候选清单 · 实测在本条** · 2026-11-16 analyse 轮 · **FND-H5**）：按本 feature 的落地形态改动源码 ⇒ 跑既有 pytest 套件 ⇒ ⇒ ⇒ **变红**的断言即入清单 ⇒ ⇒ ⇒ **MUST** 逐条带 `文件:行号` + 变红原因 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 只凭推理登记（SC-015 · SC-018 · G29 · EV-1 / EV-2 · **FND-H5**）
- [X] T012 Implement the **L2 compatible extension** in `src/freegraph/runtime/superstep.py`: in `run_graph` (`:1964-1967`) the `max_concurrency` **reading point** MUST fall back to `config.max_concurrency` when the **keyword is absent** (**keyword takes precedence**) ⇒ ⇒ the keyword's validation MUST stay **before** `resolve_config` (the existing failure order stays **verbatim**) ⇒ ⇒ the `config`-sourced value MUST be validated by the **same** `_validate_max_concurrency` ⇒ ⇒ ⚠️ **校验点 MUST 写准（2026-11-16 analyse 轮第四轮 · M2 回修）**：**config 兜底值的校验点 = `resolve_config` **之后**、`_first_graph` **之前****（它只能在 resolve 之后才读到 `run_config.max_concurrency`） ⇒ ⇒ ⇒ ⇒ ⇒ **失败信号与关键字形态同款**（类型不符 ⇒ 内置 `TypeError` · `< 1` ⇒ 内置 `ValueError` · 均**点名该参数**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **关键字形态的失败先后逐字不变** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 把该校验点放在 `resolve_config` **之前**（读不到 `run_config`） ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 放在 `_first_graph` **之后**（失败信号晚于图首轮） ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 逐字口径见 **spec FR-023** 与 **契约 ES-08** ⇒ ⇒ **MUST NOT** change `run_graph`'s **signature** ⇒ ⇒ **MUST NOT** add any symbol to `freegraph.runtime.__all__`（still **23**）⇒ ⇒ ⇒ the effective value MUST flow down the existing `_first_graph` → `_run_graph_loop` → `_run_round` → `_resolve_cap` chain ⇒ ⇒ ⇒ ⚠️ **`None` ≡ 未指定**（2026-11-16 analyse 轮 · **D-B 决策** · 本 feature 的唯一口径）：关键字为 `None`（**未传**或**显式 `None`** · 二者**不可区分** ⇒ 门面的 `invoke` **恒不传**该关键字）⇒ ⇒ ⇒ ⇒ **一律回落到 `config.max_concurrency`** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **不存在**「显式 `None` 覆盖 config」的第三种语义（FR-023 · 裁定 13 · SC-006 · 破冻结面 T-3 · **D-B**）
- [X] T013 Back-revise the **frozen L2 contracts** (**split without deleting**) in `specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md` §2's `run_graph` parameter row and `specs/b12f1-concurrency-errors/spec.md`'s **FR-017 / 裁定 18** rows ⇒ annotate「自 B7F3 起：关键字优先 · config 兜底」⇒ ⇒ **MUST NOT** delete or reorder any existing row ⇒ ⇒ ⇒ the change is a **compatible extension**（existing callers unchanged）⇒ ⇒ ⇒ **实测化义务**：MUST run the existing suite and **back-fill** any assertion that turns red（宪法 v1.12.0「冻结断言清单 MUST 实测化」· **拆分而不删**）⇒ ⇒ ⇒ folded into the **one** ratification（FR-023 · 裁定 13 · 破冻结面 T-3）⇒ ⇒ ⇒ ⚠️ **承接编号订正**（2026-11-16 analyse 轮）：`src/freegraph/runtime/superstep.py:1947`'s docstring says「门面层再归一成 dict（B7F3 · 承接 **D-3**）」⇒ 那是 **B10F1 的 D-3**（与本 feature 的 D-3 / D-4 **不同源**）⇒ ⇒ ⇒ ⇒ MUST 一并订正为正确编号（**文档性改动 · 零行为变化**）
- [X] T040 Re-grade the acceptance-script groups in `harness/demo/graph_core.py`: A5（条件边 ⇒ **B8F1**）· the C16 part of A6（⇒ **B8F1**）· the context part of A9（⇒ **B8F3**）· A10（节点别名 ⇒ **B8F3**）⇒ **downgrade from `check()` to `soft()`** and annotate each with its owning feature（沿用 C17 恢复项「载体待 B14F1 锁定」的既有写法）⇒ ⇒ ⚠️ **降级范围 MUST 以 T011 的实测红点为依据**（**MUST NOT** 只凭推理 ⇒ 宪法 v1.12.0「冻结断言清单 MUST 实测化」）⇒ ⇒ ⇒ ⚠️ **A1 / A2 / A4 / A7 / A8 此前从未执行过**（长期被就绪探针挡住）⇒ ⇒ ⇒ 它们**默认保持硬断言**（依赖已交付：B5F1/B5F2/B12F1/B13F1）⇒ ⇒ ⇒ ⇒ 但若 T011 实测出红点 ⇒ ⇒ ⇒ MUST **据实登记**并**单独处置**（**MUST NOT** 顺手降级掩盖）⇒ ⇒ ⇒ ⚠️ ⚠️ **2026-11-16 analyse 轮 · 第三轮回修（FND-B2 · 清单补全）**：原清单**漏**了 **A6 的 C17 段（中断与恢复 · `graph_core.py:357-405`）** ⇒ ⇒ ⇒ ⇒ **该段 MUST 保持硬断言**（**挂起半边**：C17 中断后结果含 `__interrupt__` / 元素有 `.value` / `.id` / 载荷原样透出 ⇒ 依赖已交付 ⇒ 必绿）⇒ ⇒ ⇒ ⇒ ⇒ 其**恢复半边**（`Command(resume=)`）沿用**仓库既有写法** = `soft()`（「恢复需 checkpointer 支持 —— 载体待 **B14F1** 锁定」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 把该段**整体**降级（挂起半边必绿）⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** touch the readiness probe `_invoke_ready()`（`:555-571` · it keys on `NotImplementedError` and switches by itself）⇒ ⇒ ⚠️ **MUST NOT** change `harness/demo/target.py`（read-only baseline · G29 ①）⇒ ⇒ ⚠️ **阶段（2026-11-16 analyse 轮 · A3）**：本条**由 Phase 10 前移到 Phase 2**（置于 **T011** 之后）⇒ ⇒ ⇒ ⇒ **MUST** 在 **T014** 之前完成（否则 `graph_core.py` 仍以 `rc == 1` 结束 ⇒ T014④ 的 `rc == 0` 断言必红）⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **与 T041 同文件**（`graph_core.py`）⇒ ⇒ ⇒ ⇒ **两者 MUST 串行**（**MUST NOT** 同时并行）（SC-015 · EV-1 · EV-2 · G29）
- [X] T041 Fix the stale assertion in `harness/demo/graph_core.py:509-512`: `not hasattr(cfg, "configurable")` contradicts the **frozen** `RunConfig`（which **does** have `configurable` · `src/freegraph/contracts/types.py:215`）and is therefore **already red**（it only becomes reachable once `invoke` works）⇒ replace the condition with `cfg.configurable == {}` while **keeping** the original label「C21 context 未被塞进 configurable」⇒ ⇒ ⚠️ **阶段（2026-11-16 analyse 轮 · A3）**：本条**由 Phase 10 前移到 Phase 2**（置于 **T011** 之后）⇒ ⇒ ⇒ ⇒ **MUST** 在 **T014** 之前完成（脚本先修绿 · 再替换冻结断言）⇒ ⇒ ⇒ ⇒ ⚠️ **与 T040 同文件**（`graph_core.py`）⇒ ⇒ ⇒ ⇒ **两者 MUST 串行**（SC-015 · G29 · R-3）
- [X] T042 [P] Re-grade `harness/demo/agent_loop.py`: ⚠️ **降级范围 MUST 覆盖三个用例组**（2026-11-16 analyse 轮 · C2 修复 —— 原先只列 B1，遗漏 B2 / B3）——**B1**（工具循环：`llm_calls == 2` / `len(messages) == 4` / 工具结果 = 7）· **B2**（tool_call 形状：断言直接取 `msgs[1]` ⇒ **路由未交付时 `msgs` 长度为 1 ⇒ `IndexError`** ⇒ 被 `main()` 的兜底捕获成「用例组未抛异常即完成」的失败）· **B3**（人工审批插入工具循环：`tools` 节点依赖路由才可达 ⇒ 断言「工具执行前触发中断」必红）⇒ ⇒ 三者**均依赖 B8F1 的条件边路由** ⇒ ⇒ 全部 **downgrade to `soft()`** + 标注归属 feature（**B8F1**）⇒ ⇒ ⇒ **B4**（`Command(update=)` · **静态边** ⇒ 依赖已交付）⇒ ⇒ ⇒ **保持硬断言** ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 把「与本 feature 无关」的失败一并降级 ⇒ ⇒ ⇒ ⇒ 降级范围 MUST 以 **T011 的实测红点**为依据 ⇒ ⇒ ⇒ ⚠️ **阶段（2026-11-16 analyse 轮 · A3）**：本条**由 Phase 10 前移到 Phase 2**（置于 **T011** 之后）⇒ ⇒ ⇒ ⇒ **MUST** 在 **T014** 之前完成（脚本先修绿 · 再替换冻结断言）⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ 与 T040 / T041 **不同文件**（`agent_loop.py`）⇒ ⇒ ⇒ ⇒ ⇒ **可与 T040 / T041 并行**（SC-002 · EV-2 · G29）
- [X] T014 [Foundational] **Split/replace without deleting** the **four** frozen "invoke is not wired" assertions **in this phase, after T040 / T041 / T042 have turned the acceptance scripts green**（the baseline must stay green at the end of this phase）: ① `tests/facade/test_compiled_graph.py:73-86` ⇒ **从参数化列表中提出**（split，**不删**语义）：把 `"invoke": (({},), "B7F3")` 这一条从 `calls` 映射里提出 ⇒ 改为**独立断言**（`invoke` on a legal path MUST **not** raise `NotImplementedError`）⇒ 其余 **five** 条目**逐字不动**② `tests/facade/test_facade.py:195-200` ⇒ **replace** `test_compile_reports_invoke_b7f3` with its inverse（`invoke` is delivered ⇒ no `NotImplementedError`）③ `tests/facade/test_facade.py:217-234` ⇒ **从参数化列表中提出**（split，**不删**语义）：把 `("invoke", ({},))` 这一条从 `calls` 元组里提出 ⇒ 改为**独立断言**（`invoke` 已交付 ⇒ **不**抛 `NotImplementedError`）⇒ 其余 **five** 条目**逐字不动**；keep `assert not hasattr(graph, "invoke")` — that is the **builder** side④ `tests/runtime/test_acceptance_script.py:15-34` ⇒ **replace** the `returncode == 2` assertion with「the script **succeeds**」= `returncode == 0`（⇒ 期望**绿**）while keeping the subprocess **mechanism** assertion（still spawn the script and assert on its exit code）⇒ ⇒ ⚠️ **判据**（2026-11-16 analyse 轮 · **FND-H5**）：**MUST** 断言 `returncode == 0`（**不是**「不再是 2」）⇒ ⇒ ⇒ ⇒ ⇒ **理由**：G29 判定 2 与 T051 均要求验收脚本 **rc == 0**；「`rc ∉ {2}`」会让**真失败（rc == 1）**仍然判绿 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据只可更严 · MUST NOT 放宽**（与 T040 / T041 / T042 的降级口径一致：降级后的脚本 MUST 仍全绿）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** keep the `[环境未就绪]` text check（that text is printed **only** on the not-ready branch · `graph_core.py:585/596` ⇒ once `invoke` ships it **never** appears ⇒ the two assertions are **mutually exclusive**）⇒ ⇒ Phase 2 MUST end with `.venv/bin/python -m pytest tests/ -q` green（FR-001 · FR-026 · FR-028 · SC-015 · 破冻结面）
- [X] T015 [P] Add the differential scenario model to `tests/differential/parity_probe.py`: `@dataclass InvokeScenario`（`name` / `verdict` / `note` / `fg: Callable[[], Any]` / `up: Callable[[], Any]`）· a `_invoke_scenarios()` registry function（**initially empty** — the scenarios land in T036）· append `_run_invoke_scenarios(keyword)` at the end of `run_all()` ⇒ ⇒ mirror the existing `CompileScenario` shape (`parity_probe.py:3594-3603`) ⇒ ⇒ **MUST NOT** touch the existing runtime / builder / compile scenario families（SC-017 · DD-11）
- [X] T016 Add the new model to the closed-vocabulary check in `tests/differential/test_parity_probe.py::test_the_verdict_vocabulary_is_closed`: loop over `parity_probe._invoke_scenarios()` asserting `verdict ∈ {SAME, STRICTER, DIFF}` and that `STRICTER` / `DIFF` **MUST** carry a non-empty `note` ⇒ ⇒ without this the new scenarios **escape** the check（SC-017）

**Checkpoint**: `invoke` drives L2 end-to-end and returns the full state; the L1 protocol is widened; the acceptance scripts have been **measured, re-graded and turned green**（T011 实测 → T040 / T041 / T042 分级与修复）; the frozen assertions are split (not deleted); **the baseline is green at the end of this phase**（`pytest tests/ -q` 全绿）. User stories now add their own judgments.

---

## Phase 3: User Story 1 - 一次调用跑完整张图，拿到完整状态 (Priority: P1) 🎯 MVP

**Goal**: `compiled.invoke({"messages": [...]})` 跑完整张图并返回**完整状态**（键集 == schema 全部 key · `messages` 含初始 + 全部新增）。

**Independent Test**: 建 2 节点图（`START→a→b→END`）⇒ `invoke({"messages": ["seed"]})` ⇒ 断言 `type(out) is dict`、`list(out) == ["messages", "llm_calls"]`、`out["messages"] == ["seed", "a", "b"]`。

### Tests for User Story 1

- [X] T017 [P] [US1] Add the full-state tests in `tests/facade/test_invoke_full_state.py`: ① the result is a **plain `dict`**（`type(out) is dict`）② the **key set equals the schema's full key set** and the **order matches**（`list(out) == ["messages", "llm_calls"]`）③ `messages` == **initial + all new**（`["seed", "a", "b"]`）④ the result is **not a delta**（the initial message is still present）⑤ the graph runs to **termination**（the node sequence covers every reachable node）⑥ the returned value is **not** the input object（no aliasing of the caller's dict）⑦ ⚠️ **多源汇合（屏障）**（**SC-013 的屏障半边** · **H-8 的落点**）：⚠️ **MUST** 用 **T002 的 `build_fanout_graph()`**（`START→a` / `START→b` ⇒ 两个源节点）+ `add_edge(["a", "b"], "c")` ⇒ ⇒ 屏障目标 `c` 的写入出现在**所有**源之后（执行序 `a`/`b` → `c`）⇒ ⇒ 完整状态含 `c` 的写入（**静态多源边** · B7F4 已交付于 L2 ⇒ **不依赖 B8F1 的条件边路由** ⇒ ⇒ **EV-3 已撤销** ⇒ 本 feature **必须**判定）⑧ ⚠️ **路由通道排除**（契约 **I-03** · FR-012 · 裁定 4）：用 **T002 的条件边图**（**带 `path_map`**）跑一次 ⇒ ⇒ 断言 `"branch:to:*" not in out` **且** `list(out)` **恰为** schema 键集（顺序一致）⇒ ⇒ ⇒ ⇒ ⇒ 该断言**非空洞**（普通图无路由通道 ⇒ 恒真）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 断言路由求值生效（**B8F1**）（FR-003 · FR-007 · FR-008 · FR-010 · FR-012 · SC-001 · SC-002 · SC-013 · **FND-H4**）
- [X] T018 Add the **frozen-holding-face** test in `tests/facade/test_invoke_full_state.py`: `set(vars(compiled))` MUST be **exactly** the 11 frozen names（`_spec` / `_builder_spec` / `_conditional_edges` + the 8 public attributes）⇒ ⇒ `invoke` MUST NOT add a 4th private field nor a 7th capability method ⇒ ⇒ ⇒ also assert `freegraph.runtime.__all__` still has **23** symbols and `freegraph.graph` still has **7**（FR-028 · SC-016 · 裁定 4）

### Implementation for User Story 1

- [X] T019 [US1] Audit `src/freegraph/_stategraph.py` against `contracts/invoke-contract.md` §3.1 / §3.2 and `quickstart.md` §1 (key set · order · merge · termination) and fix any deviation — in particular confirm the result is built from the **sparse view + fill** and never from a delta（FR-008 · 裁定 2 / 3）

**Checkpoint**: US1 = MVP slice. `pytest tests/facade/test_invoke_full_state.py -q` green ⇒ the headline judgement「`invoke` 返回 `{'messages': [...], 'llm_calls': N}`」is satisfied.

---

## Phase 4: User Story 2 - 计数型 key 也在返回里 (Priority: P1)

**Goal**: 无值 schema key **也在**返回键集里（值 `None`）；有值的 key 给出**合并/覆盖**后的最终值；**节点入参仍稀疏**。

**Independent Test**: 一个节点只写 `messages` ⇒ `invoke` 后断言 `"llm_calls" in out` 且 `out["llm_calls"] is None`；另一个图里 `llm_calls` 每轮都写 ⇒ 断言 `out["llm_calls"] == 2`（**覆盖**，不是累加）。

### Tests for User Story 2

- [X] T020 [US2] Add the counting/fill tests in `tests/facade/test_invoke_full_state.py` ⇒ ⇒ ⚠️ **MUST NOT** 标 `[P]`（2026-11-16 analyse 轮第五轮 · **FND-B10**）：与 **T017 同文件**（`test_invoke_full_state.py`）⇒ ⇒ ⇒ ⇒ **两者 MUST 串行**（`[P]` 的定义 = 「不同文件、无未完成依赖」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **本条补齐 FND-B5 的第三组同文件缺口**（前三组 = `T022/T023` · `T025/T027` · `T040/T041` ⇒ 已去 `[P]`；本组 = `T017/T020` ⇒ 本条）： ① a schema key that was **never written** is still in the key set with value `None` ② a **reducer** channel's **type empty value** is preserved（a `list`-typed reducer channel that was never written yields `[]`, **not** `None`）③ a key **without** a reducer holds the **overwritten** final value（not an accumulation）④ the **node input stays sparse**（an unwritten key is absent from the node input ⇒ `state.get(k, default)` still returns `default`）⑤ writing `None` **explicitly** as an initial value is still honoured（`{"x": None}` reaches the channel）⇒ ⇒ the fill rule MUST NOT leak into the node input（FR-009 · FR-011 · FR-025 · SC-003）

### Implementation for User Story 2

- [X] T021 [US2] Audit `_full_state` in `src/freegraph/_stategraph.py`: confirm it uses `sparse.get(key, None)`（**MUST NOT** use「value is `None` ⇒ treat as absent」）and that it never rewrites a reducer channel's derived empty value（FR-009 · 裁定 3）

**Checkpoint**: US2 independently passes;「键一定在」becomes a fact users can rely on.

---

## Phase 5: User Story 3 - 未知 key 会被立刻指出 (Priority: P1)

**Goal**: 节点返回 schema 之外的 key ⇒ `InvalidUpdateError` 且消息**点名**违规 key；节点真异常 ⇒ **原类型 + 原消息**到达调用方。

**Independent Test**: 节点返回 `{"messages": [...], "typo_key": 1}` ⇒ 断言抛 `InvalidUpdateError`、`"typo_key" in str(exc)`、`exc.invalid_keys == ("typo_key",)`。

### Tests for User Story 3

- [X] T022 [P] [US3] Add the unknown-key tests in `tests/facade/test_invoke_errors.py`: ① a node returning an unknown key ⇒ `InvalidUpdateError` whose message **contains the offending key name** ② **several** unknown keys ⇒ the message contains **all** of them and `exc.invalid_keys` is the full tuple ③ the exception reaches the caller **unchanged**（`type(exc) is InvalidUpdateError`）④ an **initial input** carrying an unknown key ⇒ the same `InvalidUpdateError` ⑤ **no partial result** is returned on failure（FR-016 · SC-004 · X-2 / X-3）
- [X] T023 [US3] Add the exception-identity test in `tests/facade/test_invoke_errors.py` ⇒ ⇒ ⚠️ **MUST NOT** 标 `[P]`（2026-11-16 analyse 轮 · 第三轮回修 · **FND-B5**）：与 **T022 同文件** ⇒ ⇒ ⇒ ⇒ **两者 MUST 串行**（`[P]` 的定义 = 「不同文件、无未完成依赖」）: a node raising a custom `Boom(RuntimeError)` ⇒ the caller receives **`Boom` itself** with the **verbatim** message（`type(exc) is Boom` and `str(exc) == "原始消息 payload"`）⇒ ⇒ proves the facade does **not** wrap it into `RuntimeError`（FR-017 · SC-005）

### Implementation for User Story 3

- [X] T024 [US3] Audit the error path in `src/freegraph/_stategraph.py`: confirm there is **zero `try`/`except`** in `invoke`（every failure signal propagates with its original type and message）⇒ ⇒ confirm nothing in the facade re-raises `InvalidUpdateError` under another type（FR-017 · FR-018 · FR-020 · 裁定 9）

**Checkpoint**: US3 independently passes; a typo'd key fails loudly and names itself.

---

## Phase 6: User Story 4 - 两种 config 形态都能用 (Priority: P2)

**Goal**: `config` 同时接受 `RunConfig` 与普通映射；`recursion_limit` 以 dict 形态生效；`max_concurrency` 经 `RunConfig` 可见且生效。

**Independent Test**: 同一张自环图 ⇒ `invoke(input, {"recursion_limit": 3})` 抛 `GraphRecursionError`（`.recursion_limit == 3`）；`invoke(input, RunConfig(max_concurrency=1))` 正常跑完且结果与并发档**逐字相等**。

### Tests for User Story 4

- [X] T025 [P] [US4] Add the config tests in `tests/facade/test_invoke_config.py`: ① a `RunConfig` instance is accepted ② a plain `dict` is accepted ③ **another `Mapping` type**（not a literal `dict`）is accepted ④ **unknown keys in a mapping are ignored**（no exception）⑤ `{"recursion_limit": 3}` on a self-looping graph ⇒ `GraphRecursionError` with `.recursion_limit == 3` and the exception is **not wrapped**（`type(exc) is GraphRecursionError`）（FR-021 · FR-022 · SC-006 · SC-007）

### Implementation for User Story 4

- [X] T026 [US4] Audit `src/freegraph/_stategraph.py`: the facade MUST pass `config` **verbatim** to `run_graph(config=...)` ⇒ ⇒ the **facade MUST NOT** read `max_concurrency` itself, MUST NOT translate the mapping into a `RunConfig` (FR-021) ⇒ ⇒ the knob's **reading point is L2's**（T012）⇒ ⇒ ⇒ the invalid-value failures (`TypeError` / `ValueError`, both naming the parameter) MUST keep coming from L2 (`superstep.py:1339-1361`) ⇒ ⇒ **MUST NOT** re-implement that validation in the facade ⇒ ⇒ ⇒ ⚠️ **「关键字缺省」≡「显式传 `None`」**（**D-B 决策** · 二者**不可区分** ⇒ **一律回落** `config.max_concurrency`）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **门面的 `invoke` 恒不传该关键字** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **不存在**「显式 `None` 覆盖 config」的第三种语义（FR-023 · 裁定 13 · DD-4）
- [X] T027 [US4] Add the concurrency-knob test in `tests/facade/test_invoke_config.py` ⇒ ⇒ ⚠️ **MUST NOT** 标 `[P]`（2026-11-16 analyse 轮 · 第三轮回修 · **FND-B5**）：与 **T025 同文件** ⇒ ⇒ ⇒ ⇒ **两者 MUST 串行**（`[P]` 的定义 = 「不同文件、无未完成依赖」）: ① **可观测并发度**（the discriminating assertion）：⚠️ **MUST** 用 **T002 的 `build_fanout_graph()`**（`START→a` / `START→b` ⇒ **两个节点落在同一 super-step** ⇒ 才会真并发；⚠️ **串行图恒不重叠** ⇒ 该断言**恒假**）· two nodes that record their own **in-flight overlap count**（a shared counter incremented on entry / decremented on exit）⇒ ⇒ `RunConfig(max_concurrency=1)` ⇒ overlap count == **0**（**serial baseline**）· the default run（`None` ⇒ `min(32, cpu+4)`）⇒ overlap count **≥ 1** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ this is what **proves** the knob took effect（if the L2 reading point were missing, the default run would also be non-overlapping ⇒ the assertion goes **red**）② **supplement**（not the discriminator）：`RunConfig(max_concurrency=1)` and the default concurrent run produce **byte-identical** final states ⇒ ⇒ ⚠️ **MUST NOT** rely on ② alone（the final state is **independent** of the concurrency level ⇒ it passes even when the knob is silently ignored）（FR-023 · SC-006）⚠️ **确定性要求（2026-11-16 analyse 轮 · C3 修复）**：①② 的「重叠」**MUST NOT** 依赖**时间流逝**（⇒ ⇒ CI 慢档 / Windows 档会假红 —— 仓库已有一次「时序测量假红」的修复史）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ① MUST 用**确定性同步**构造：两个并发节点各自进入后用 `threading.Event`（或 `Barrier`）**互相等待到齐**才返回 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 缺省档 ⇒ 两节点必然同时在飞 ⇒ 重叠计数 **≥ 1**（**必成立**）· `max_concurrency=1` ⇒ 第一个节点等不到第二个 ⇒ **以超时兜底**（不得无限等待）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 断言「重叠计数 == 0」且**不得**把超时本身当失败（超时 ⇒ 串行 ⇒ 正是期望）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **超时时长 MUST 取值稳健**（远大于线程调度抖动 · 远小于 CI 超时上限）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **超时值 MUST 实测标定**（2026-11-16 analyse 轮 · **FND-L3**）：在 **CI 最低档（3.11 · Linux）** 与 **Windows 档**各跑一次 ⇒ 记录「重叠 ≥ 1」是否稳定成立 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据不放宽**（重叠计数 == 0 / ≥ 1 两条**一字不改**）（FR-023 · SC-006 · 裁定 13 · DD-4 · **D-B** · **FND-L3**）

**Checkpoint**: US4 independently passes; both config shapes work and the knob is visible.

---

## Phase 7: User Story 5 - 挂起与恢复可观察 (Priority: P2)

**Goal**: 挂起时结果含 `"__interrupt__"`（元素有 `.value` / `.id`）且键集 == schema 全集 **+** 该键；恢复用 `Command(resume=...)`。

**Independent Test**: 节点调 `interrupt("approve?")` ⇒ 断言 `out["__interrupt__"][0].value == "approve?"` 且 `.id` 非空；再以 `Command(resume="yes")` 恢复 ⇒ 节点拿到「yes」。

### Tests for User Story 5

- [X] T028 [P] [US5] Add the suspension tests in `tests/facade/test_invoke_interrupt.py`: ① a node calling `interrupt("approve?")` ⇒ the result contains the `"__interrupt__"` key and its element has `.value == "approve?"` and a non-empty `.id` ② the suspended result's **key set** == the schema key set **plus** `"__interrupt__"`（⇒ the fill happens **after** the conversion）③ a **non-suspended** run ⇒ the result does **not** contain `"__interrupt__"`（occurrence count == 0）④ a **static** suspension（`compile(interrupt_before=[...])`）goes through the **same** conversion path and yields an **empty tuple** `()`（FR-014 · SC-010 · 裁定 8）
- [X] T029 [US5] Add the resume tests in `tests/facade/test_invoke_interrupt.py` ⇒ ⇒ ⚠️ **MUST NOT** 标 `[P]`（2026-11-16 analyse 轮第五轮 · **FND-B10**）：与 **T028 同文件**（`test_invoke_interrupt.py`）⇒ ⇒ ⇒ ⇒ **两者 MUST 串行**（`[P]` 的定义 = 「不同文件、无未完成依赖」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **本条补齐 FND-B5 的第四组同文件缺口**： ① `invoke(Command(resume="yes"))` ⇒ the interrupted node **re-runs from its origin** and receives the resume value「yes」⇒ ⇒ ⇒ ⚠️ **载体（2026-11-16 analyse 轮 · 第三轮回修 · FND-A4）**：**MUST** 挂 **T002 的「自足桩 checkpointer」**（`compile(checkpointer=stub)`）⇒ ⇒ ⇒ ⇒ ⇒ **理由**：`src/freegraph/**` 内**零** saver 实现（`MemorySaver` 归 **B14F1**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 无 checkpointer ⇒ 恢复**必**抛 `InterruptError(checkpointer_required)` ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **SC-010 的「恢复取值」半边**将**物理不可达成** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 因「无载体」把 ① 降级为 soft（那是**仓库既有验收脚本** `graph_core.py:392-393` / `agent_loop.py:275-280` 的做法 —— 它们注「载体待 B14F1 锁定」；**本 feature 的 SC-010 是硬判据** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST** 用测试侧的桩 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ 两侧（挂起 / 恢复）**MUST** 使用**同一会话键**（`thread_id` · 上游同款）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ② submitting `Command(resume=...)` **without a checkpointer** ⇒ `InterruptError`（**MUST NOT** silently degrade to an in-memory resume）③ the `InterruptError`'s `reason` is one of the closed values（FR-015 · FR-019 · SC-010 · 裁定 7）

### Implementation for User Story 5

- [X] T030 [US5] Audit the normalization order in `src/freegraph/_stategraph.py`: `InterruptResult` ⇒ **first** `as_result_dict()`（the **only** conversion path · B10F1 owns it）⇒ **then** `_full_state` ⇒ ⇒ **MUST NOT** write a second conversion path（not even a static-suspension-specific one）⇒ ⇒ the static suspension MUST reuse the very same branch（FR-014 · 裁定 8）

**Checkpoint**: US5 independently passes; suspension is observable and resume works.

---

## Phase 8: User Story 6 - 一次编译，多次互不干扰的会话 (Priority: P2)

**Goal**: 同一张编译图**连续两次不累积**、**并发两次不串扰**；编译产物持有的通道**零状态残留**。

**Independent Test**: 编译一张图 ⇒ 连续两次 `invoke` ⇒ 第二次的结果不含第一次的新增；再并发两次 ⇒ 两次结果互不含对方的值。

### Tests for User Story 6

- [X] T031 [P] [US6] Add the isolation tests in `tests/facade/test_invoke_isolation.py`: ① two **consecutive** `invoke` calls on the same compiled product ⇒ the second result does **not** contain the first run's new values ② two **concurrent** `invoke` calls (`threading.Thread`) ⇒ the two results do **not** contain each other's values ③ the compiled product's channels stay **free of residue**（no channel has a value after the runs）④ ⚠️ **步末清空口径**（**2026-11-16 analyse 轮 · 第三轮回修 · FND-B7** · FR-006 / 裁定 11）：用 **T002 的条件边图**（**带 `path_map`** ⇒ 才有路由通道）**连续两次** `invoke` ⇒ ⇒ 断言第二次结果**不含**任何路由通道名（`"branch:to:*" not in out`）⇒ ⇒ ⇒ ⇒ 且两次的**键集逐字相等** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **路由通道的值 MUST NOT 残留到下一次调用**（步末清空 ⇒ 该口径此前**无专门用例** ⇒ 本条补齐）（FR-004 · FR-006 · SC-008 · SC-009 · 裁定 10 / 11）

### Implementation for User Story 6

- [X] T032 [US6] Audit the `run_graph` call site in `src/freegraph/_stategraph.py`: confirm `state=` is **never** passed（⇒ L2 builds a fresh `SchedulerState()` per call ⇒ no cross-talk of consumed versions）⇒ ⇒ confirm the facade never touches `compiled._spec.channels` in a way that would write into the shared templates（FR-002 · FR-005 · 裁定 10）

**Checkpoint**: US6 independently passes;「compile once, run many」holds at the façade level.

---

## Phase 9: User Story 7 - 执行过程零副作用 (Priority: P3)

**Goal**: 执行期**零环境变量读取**、**零出站**、**零第三方依赖**。

**Independent Test**: 用 socket 监测夹具 + `sys.modules` 快照观测 ⇒ 断言出站连接数 == 0、`langchain*` / `langgraph*` / `langsmith` 出现次数 == 0。

### Tests for User Story 7

- [X] T033 [P] [US7] Add the purity tests in `tests/facade/test_invoke_purity.py`: ① **zero environment-variable reads** during a full `invoke`（including `LANGSMITH_*`）⇒ ⇒ ⚠️ **测量机制 MUST 显式化**（2026-11-16 analyse 轮 · C4 修复）：MUST 用**可判定的**手段计数（如对 `os.environ` / `os.getenv` 做代理计数，或用「哨兵环境变量 + 读取痕迹」的夹具）⇒ ⇒ ⇒ **MUST NOT** 只断言「结果未受影响」（那不证明「未读取」）② `sys.modules` contains **no** `langchain` / `langchain_core` / `langgraph` / `langsmith` after a full `invoke` ③ **zero egress**（socket-monitoring fixture）④ the user nodes / routers / reducers are called **exactly** the expected number of times（no extra invocation introduced by the facade）（FR-024 · SC-011 · SC-012）
- [X] T034 Add the **documentation-guard** test in `tests/facade/test_invoke_purity.py`: ① the `invoke` **docstring** MUST contain the「只读快照 · 不要原样回喂」wording（**substring** assertion, not an exact match）⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · L6 去重**：SC-020 另要求的「**显式 `None` 初始值仍被写进通道**」那条用例**已由 T020⑤ 承载**（`test_invoke_full_state.py`）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **本任务只留 docstring 守卫** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ （**单一实现点** · 零漂移）② ⚠️ **README.md 的同名断言不在本任务**（README 由 **T047** 写就 ⇒ 若本任务先断言它 ⇒ **T034→T047 之间必然红** ⇒ ⇒ 撞宪法「MUST NOT 写永久红 CI」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **README 子串断言归 T047**（各守卫紧贴其产物 ⇒ 零红窗口）③ ⚠️ **SC-019 的判定守卫已移出**（2026-11-16 analyse 轮 · C1/C6 修复）：人工验证记录的守卫断言（记录存在 + 含**追认**文字 + 含**两轮实测输出**）MUST 由 **T046** 承担（Phase 10 · 在 **T044 / T045** 之后）⇒ ⇒ ⇒ ⇒ **理由**：本任务在 Phase 9，而 `manual-verification.md` 由 **T044** 创建、追认文字由 **T045** 写入 ⇒ ⇒ ⇒ 若守卫留在本任务 ⇒ **T034→T046 之间必然红**（撞宪法「MUST NOT 写永久红 CI」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **本任务只留 SC-020 的 docstring 守卫**（FR-009 · FR-020 · 裁定 3）

### Implementation for User Story 7

- [X] T035 [US7] Audit `src/freegraph/_stategraph.py` for purity: the `invoke` path MUST NOT read environment variables, MUST NOT perform I/O or egress, and MUST NOT import any third-party package ⇒ ⇒ keep using the hard-coded `10007` recursion default (B13F1 · X-5)（FR-024 · 裁定 14）

**Checkpoint**: US7 independently passes; the runtime stays clean.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: 差分场景、门禁接线（**T053** = G19 兼容矩阵行白名单 · 破冻结面 T-4）、文档、人工验证与追认、下游接线、全量回归
> ⚠️ **2026-11-16 analyse 轮 · 第三轮回修（FND-A3 · CRITICAL）· 阶段编排**：**验收脚本的分级与修复（T040 / T041 / T042）已前移到 Phase 2**（置于 T011 实测之后）⇒ ⇒ ⇒ ⇒ **理由**：`invoke` 接通（T010）后 `graph_core.py` 必以 `rc == 1` 结束 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 若脚本修复留在本阶段 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **Phase 2 → Phase 10 之间存在红窗**（撞宪法 v1.6.0 红线「MUST NOT 写永久红的 CI」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **本阶段只留 T051（全量回归 + 门禁）/ T052（一致性复核）作为收尾** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **任务号不变 · 仅换阶段**。

- [X] T036 Land the differential scenarios in `tests/differential/parity_probe.py::_invoke_scenarios()` ⇒ ⇒ ⚠️ **MUST NOT** 标 `[P]`（2026-11-16 analyse 轮第五轮 · **FND-B10**）：与 **T015 同文件**（`tests/differential/parity_probe.py`）**且** 本条**依赖** T015 落下的空注册表 ⇒ ⇒ ⇒ ⇒ **两者 MUST 串行**（`[P]` 的定义 = 「不同文件、无未完成依赖」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **本条补齐 FND-B5 的第五组同文件缺口**：**D-92…D-102**（**11 条**）verbatim from `contracts/upstream-parity.md` §3: D-92 minimal graph + `invoke({"messages": ["seed"]})` ⇒ both sides' `messages` are **byte-identical**（initial + all new · SAME）· D-93 initial input carrying **every** schema key ⇒ both sides' **key sets** are **byte-identical**（`['messages','llm_calls']` · **upstream orders by schema declaration order** · SAME）· D-94 initial input missing **one** schema key ⇒ upstream **omits** it, freegraph **keeps** it ⇒ ⇒ ⚠️ **MUST** use a **覆盖型（无归约器）** key（如 `llm_calls`）⇒ ⇒ ⇒ ⇒ **MUST NOT** use a **归约型** key（its value would be the **type empty value** `[]`, not `None` · spec D-94）（**STRICTER** · X-1）· D-95 node returns an unknown key（**STRICTER** · X-2）· D-96 initial input carries an unknown key（**STRICTER** · X-3）· D-97 node raises a real exception ⇒ both sides raise the **same type and message**（SAME）· D-98 `{"recursion_limit": 3}` on a loop ⇒ both raise `GraphRecursionError`（SAME）· D-99 two consecutive calls（**no accumulation** · SAME）· D-100 two concurrent calls（**no cross-talk** · SAME）· D-101 suspended result ⇒ both carry `"__interrupt__"`, freegraph's value is a **tuple** vs upstream's **list**（DIFF · X-4 passthrough）· D-102 **多源汇合（屏障）**：`add_edge(["a","b"], "c")` ⇒ both sides' final states are **byte-identical** and the barrier target lands **after all sources**（SAME）⇒ ⇒ **the three STRICTER scenarios MUST carry a `note`** ⇒ ⇒ wire them into `run_all()`（SC-017 · D-92…D-102）⇒ ⇒ ⚠️ the verdict distribution becomes **SAME 7 / STRICTER 3 / DIFF 1**（D-102 is the 7th SAME）
- [X] T037 Add the pytest wrapper in `tests/differential/test_parity_probe.py`: `test_invoke_parity_scenarios_meet_their_verdicts`（upstream absent ⇒ `skip`，沿用 B5F2 的「缺席即 skip」纪律）⇒ ⇒ ⚠️ **MUST NOT** 标 `[P]`（2026-11-16 analyse 轮 · 第三轮回修 · **FND-B5**）：本条**依赖 T036**（场景必须先落地）⇒ ⇒ ⇒ ⇒ **MUST** 在 T036 之后执行（SC-017）
- [X] T038 Land the **③② 运行期（最小图）** assertion in `harness/scripts/gates/gate_G22_isolated_env.py`（**wiring only · MUST NOT add a gate id**）: inside the **scenario ②** acceptance environment（`langchain-core` installed）, build → compile → invoke a minimal graph ⇒ assert `sys.modules` has **no** langchain family **and** the framework egress count == 0 ⇒ ⇒ update the module docstring's step 6（which currently says「本 feature MUST NOT 实现」）⇒ ⇒ ⇒ its **reverse case MUST fail accordingly**（inject `import langchain` into a copy ⇒ the runtime assertion MUST catch it）⇒ ⇒ ⇒ **G22 = 隔离环境门禁**；「场景 ②」= **验收环境**；**③② 运行期那一半**才是本 feature 的义务（FR-027 · SC-014 · EV-1 · 裁定 15）
- [X] T039 Update the **observation-scope declaration** in `harness/scripts/gates/gate_G27_zero_egress.py`:「当前观测面：测试套件执行期（**尚不含内核运行时 —— 运行期待 M2**）」⇒「**已含内核运行时（M2 · B7F3 起）**」⇒ ⇒ B3F1 SC-006 ① requires the zero-egress assertion to carry a **current** observation-scope declaration（a stale one lets「零出站已被证明」be misread）⇒ ⇒ ⇒ the string MUST stay **printable verbatim**（it is a MUST-declared literal）（FR-024 · SC-011 · 原则 I）
- [X] T043 Fill `harness/verification/B7F3/acceptance.py`: sections A1–A3（full state · key set · counting）+ failure signals + multi-session isolation + both config shapes ⇒ exit codes `0` / `1` / `2` per the B7F2 skeleton（SC-001…SC-010）
- [X] T053 [P] Add the **G19 兼容矩阵行白名单**（**FND-A5** · 本条即该缺口的**补齐任务**） in `tests/facade/test_facade_gates.py`（**破冻结面 T-4** · 「登记 + 回溯修订 + 发起者追认」三条 · **追认的第 ④ 项**）: 新增 `MATRIX_ROWS_UPDATABLE_BY_B7F3 = frozenset({"CompiledGraph"})`（**只放行这一行** ⇒ ⇒ 其余**契约层**行仍**逐字未改** ⇒ ⇒ 判据**只放宽一处**）⇒ ⇒ **比照 B9F1 / B11F1 / B12F1 的三处既有白名单写法**（类属性 + **两处**纳入：`test_existing_contract_rows_are_unchanged` 的「changed」判定 **AND** 「**等价程度（第三列）MUST NOT 变差**」的护栏循环）⇒ ⇒ ⇒ ⇒ ⇒ **护栏 MUST 一并接入**（`CompiledGraph` 保持 **部分等价** ⇒ ⇒ `stream` / `get_state` / `get_state_history` / `update_state` 仍**未交付** ⇒ ⇒ **不得**升为「行为等价」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 放行任何其它行 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 改动 G19 判据本身的强度（逐字节比对逻辑 **一字不动**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **本条 MUST 在 T047（README 兼容矩阵行更新）之前落地** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 改 `public-api-snapshot.txt`（G16）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 动 `harness/demo/target.py`（只读基准 · G29 ①）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **追认**：本白名单的设立由 **B7F3 的唯一一次发起者追认**（`harness/verification/B7F3/manual-verification.md` §7 · **追认项第 ④ 项**）覆盖 ⇒ ⇒ ⇒ **未追认前 MUST NOT 合入**（SC-019 · 破冻结面 **T-4** · G19 · **FND-A5**）
- [X] T044 Write `harness/verification/B7F3/manual-verification.md` in the repo's **五段式**（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）: paste the **real** outputs（not「符合预期」）of `quickstart.md` §1–§5 and of the two acceptance scripts（⚠️ **2026-11-16 analyse 轮第五轮订正**：原写 §1–§4 ⇒ **漏掉 §5「人工验证 · 两轮」**⇒ ⇒ 而 SC-018 要求的两轮实测输出正出自 §5 ⇒ ⇒ ⇒ **取证范围 MUST 含 §5** ⇒ ⇒ ⇒ **MUST NOT** 只写 §1–§4 · **FND-E2**）; ⚠️ **§1 环境段 MUST 转录 T001 记录的绿基线计数**（pass / skip / fail **三个数**）⇒ ⇒ **§3 实际输出段 MUST 转录 T011 记录的「首次执行验收脚本」的实测结果**（含红点与原因）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 写「全绿」而无计数 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 只写「符合预期」; add the **EV-1 / EV-2 / EV-4** carry-over notes（EV-2: the tool-loop round depends on **B8F1** ⇒ record it as a **named** carry-over, **not** as「未验证」· EV-4: the **fixed-script** end-to-end round needs **B8F1 + B22F1 + B23F1** ⇒ same treatment）⇒ ⇒ ⚠️ **两轮的定义（2026-11-16 analyse 轮 · C4 修复）**：**「fake 模型轮」** = 用**假模型**（猴补 `init_chat_model` · 立项书 §9.2）+ **可跑的最小图**跑一轮并记录实测输出（**静态边**部分**真跑**）· **「真实模型轮」** = 用**真实模型**（`claude-sonnet-4-6`）+ **最小真实模型图**（1 个节点调用真实模型 ⇒ **用户出站** · 不判失败 · **框架零出站**断言仍须通过）跑一轮并记录实测输出 ⇒ ⇒ ⇒ ⇒ ⚠️ 若真实轮因**环境不具备**（无模型凭据 / 无外网）而无法完成 ⇒ MUST 登记为**环境偏离**（**MUST NOT** 用「未验证」替代）⇒ ⇒ ⇒ ⇒ ⇒ **判据本身不放宽**（fake 轮仍 MUST 跑通）⇒ ⇒ ⇒ ⇒ ⚠️ **EV-3 已撤销**（屏障半边由本 feature 判 ⇒ **NOT** a carry-over）⇒ ⇒ ⚠️ **追认文字另立任务**（T045 · **阻断合入**）（SC-018 · EV-1 / EV-2 / EV-4 · 原则 V · **FND-H5**）
- [X] T045 **BLOCKING** — **备好并落笔**「**发起者追认**」文字 into `harness/verification/B7F3/manual-verification.md` §7 covering, in **one** ratification（⚠️ **2026-11-16 analyse 轮第五轮 · 追认项清单统一**：**唯一事实源 = spec.md「Assumptions」的「破面全集 5 类」** ⇒ ⇒ 本任务逐条**逐字对齐**该 5 类 ⇒ ⇒ ⇒ **MUST NOT** 另立分组 / 增减项数）：① the L1 protocol's `input` widening（`src/freegraph/contracts/protocols.py:270-272`） ② the L1 protocol's `config` widening（同上 ⇒ 与 ① **同属一次**登记 + 回溯修订 + 追认） ③ the L2 `run_graph` `max_concurrency` reading point（**compatible extension** · 关键字优先 · config 兜底） ④ ⚠️ **2026-11-16 analyse 轮第四轮 · C1 回修**：the **G19** 兼容矩阵行白名单（`tests/facade/test_facade_gates.py` 新增 `MATRIX_ROWS_UPDATABLE_BY_B7F3` · 只放行 `CompiledGraph` **一行** · 其余契约层行仍**逐字未改** · **等价程度列 MUST NOT 变差**）**＋** the **README** 兼容矩阵 `CompiledGraph` 行（「差异说明」列移除「行为细节挂起 B7F3」· **等价程度列 MUST NOT 变**） ⑤ the **four** frozen-assertion replacements（`tests/facade/test_compiled_graph.py:73-86` · `tests/facade/test_facade.py:195-200` · `tests/facade/test_facade.py:217-234` · `tests/runtime/test_acceptance_script.py:15-34`）⇒ ⇒ ⚠️ **签署主体（2026-11-16 analyse 轮 · 第三轮回修 · FND-C3）**：宪法 v1.6.0 明定「追认 **MUST 由发起者本人作出**」且「**MUST NOT** 由实现者代签」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **实现者只负责备好待签文本**（**含**追认内容 + **发起者确认** + **日期**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **签署动作 MUST 由发起者本人完成** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 以「实现者已写好」视同追认 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** be merged with any other feature's ratification ⇒ ⇒ ⇒ **未追认前 MUST NOT 合入**（SC-019 · 破冻结面 T-1 / T-2 / T-3 / **T-4** · ✅ **追认已作出**（2026-11-17 · **发起者本人**签署 · 人工验收通过后）⇒ ⇒ 追认**文本**落 `harness/verification/B7F3/manual-verification.md` §7.2 ⇒ ⇒ **追认次数 == 1**（≤ 1 次 / feature）⇒ ⇒ **合入闸口已打开**）
- [X] T046 Add the **人工验证记录守卫测试** in `tests/facade/test_invoke_purity.py`（**文档守卫** · 与 SC-020 的守卫同款 · ⚠️ **MUST** 在 **T044 / T045 之后**才转绿 ⇒ ⇒ ⇒ 本任务 MUST NOT 早于它们合入）：① `harness/verification/B7F3/manual-verification.md` MUST exist ② MUST contain the **fake 模型轮** 与 **真实模型轮** 两轮的**实测输出**（两段标题 + **非空**输出 ⇒ ⇒ **MUST NOT** 只写「符合预期」）③ MUST contain the **发起者追认**文字（substring「追认」+ **五项** —— **唯一事实源 = spec.md「Assumptions」的「破面全集 5 类」**：① L1 `input` 放宽 ② L1 `config` 放宽 ③ L2 `max_concurrency` 读取点 ④ **G19 的 `CompiledGraph` 矩阵行白名单**（含 README 矩阵行的措辞更新）⑤ **四处**「invoke 未就绪」冻结断言的拆分替换 · ⚠️ **2026-11-16 analyse 轮第五轮**：追认项由四项增为**五项** ⇒ 与 T045 逐字对齐 ⇒ ⇒ ⇒ **MUST NOT** 少于五项 ⇒ ⇒ ⇒ **MUST NOT** 多于五项 · **FND-B8**）⇒ ⇒ ⇒ ⇒ ①②③ 缺一 ⇒ ⇒ ⇒ 该断言即 **SC-018 与 SC-019 的判定覆盖**（⇒ ⇒ 「写记录」本身**不**构成判定覆盖 —— 宪法原则 VI v1.11.0 + v1.13.0 的「人工门禁类 SC」条款）（FR-019 · SC-018 · SC-019 · 契约 §6 的 **I-14** · 宪法原则 VI）
- [X] T047 [P] Update `README.md`: the compat-matrix rows for `StateGraph` and `CompiledGraph` ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · C1 回修**：两行的**现状措辞不同** ⇒ ⇒ ⇒ ⇒ `StateGraph` 行现写「**`invoke` 待 B7F3**」⇒ 改为「**已交付（B7F3）**」；`CompiledGraph` 行现写「**行为细节挂起** B7F3 / B8F2 / B15F1 / B16F1」⇒ ⇒ ⇒ ⇒ 改为「**行为细节挂起** B8F2 / B15F1 / B16F1」（**只移除 B7F3** · 其余三项**逐字不动**）⇒ ⇒ ⇒ ⇒ ⚠️ **等价程度列（第三列）MUST NOT 变**（`CompiledGraph` 保持 **部分等价**）and add the「**返回值是只读快照 · 不要原样回喂**」note ⇒ ⇒ ⚠️ **MUST NOT** touch any other matrix row ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · C1 回修（事实订正）**：G19 的逐字节比对**只覆盖「契约层」的 21 行**（清单驱动 · `public-api.md` §0 · 不硬编码个数）（`tests/facade/test_facade_gates.py::test_existing_contract_rows_are_unchanged` · 比对 `git show HEAD:README.md`）⇒ ⇒ ⇒ ⇒ ⇒ `CompiledGraph` **属契约层** ⇒ ⇒ ⇒ ⇒ ⇒ **必须**落在白名单 `MATRIX_ROWS_UPDATABLE_BY_B7F3` 内（见 spec 的破冻结面清单）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ `StateGraph` **属门面层 7 符号** ⇒ ⇒ ⇒ ⇒ ⇒ **不**参与该逐字节比对 ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 依赖「同提交内 HEAD 比对自我满足」⇒ ⇒ ⇒ ⇒ ⇒ **MUST** 以白名单方式放行 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 其余**契约层**行仍**逐字未改**（判据**只放宽一处**）⇒ ⇒ ⇒ ⚠️ **SC-020 的 README 子串断言落在本任务**（**substring** assertion · 与 T034 的 docstring 守卫**同款**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **理由**：README 由本任务写就 ⇒ 守卫紧贴其产物 ⇒ **T034→T047 之间零红窗口**（宪法「MUST NOT 写永久红 CI」）（FR-009 · FR-020 · SC-020 · G19）
- [X] T048 [P] Update `harness/demo/README.md`: refresh the soft / hard assertion lists to match T040–T042（`invoke` is now wired; the newly softened groups name their owning feature）⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第五轮 · FND-N5 补齐**：该文件 `:64` 的硬断言清单写「C22 的 `RunConfig` **四字段**」⇒ ⇒ 与**现状 9 字段**矛盾（`types.py:211-219`）⇒ ⇒ ⇒ **本条 MUST 一并订正为「九字段」**（SC-015 · 原则 X）
- [X] T049 [P] Add the B7F3 row to `harness/verification/README.md`'s「当前已有记录」table（feature / record / acceptance script / status — follow the existing row format)（SC-018 · 原则 V）
- [X] T050 [P] Downstream wiring（**只接线 · 逐条最小改动** — append one entry each, change nothing else）: `harness/features/B8F2_*.md`（D-1：`stream`'s `values` mode MUST reuse `_full_state`）· `B8F1_*.md`（D-2：routing on the **same** execution path）· `B22F1_*.md` / `B23F1_*.md`（D-3：readiness order）· `B14F1_*.md`（D-4：checkpointer persistence）· `B15F1_*.md` / `B16F1_*.md`（D-5：the `config` annotation widening of the remaining 4 L1 methods is **theirs** to ratify）⇒ ⇒ ⚠️ **D-5 归 B8F2 / B15F1 / B16F1**（B8F2 已由 D-1 触及 ⇒ 在其「下游承接」块**追加第二条**即可 ⇒ **MUST NOT** 覆盖 D-1 那条）（下游承接 D-1…D-5）
- [X] T051 Full regression + gates（⚠️ **2026-11-16 analyse 轮第五轮补齐**：本任务只列 **G21–G30** ⇒ ⇒ 而 plan 的 Constitution Check 声明「**G1–G30** 通过」⇒ ⇒ ⇒ ⇒ **G1–G20**（依赖闭包 / 配置层 / 许可证 / 导入图 / 网络静态 / 署名头等）**由既有 CI 常驻门禁覆盖** ⇒ ⇒ ⇒ ⇒ 本任务**不重复跑** ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 读成「G1–G20 未验证」 · **FND-E2**）：`.venv/bin/python -m pytest tests/ -q` then `harness/scripts/gates/gate_G21_dependencies.py --project pyproject.toml` · `gate_G23_licenses.py` · `gate_G24_config_layer.py` · `gate_G25_import_graph.py --root .` · `gate_G26_network_static.py` · `gate_G27_zero_egress.py` · `gate_G28_offline_equiv.py --root .`（⚠️ **断网等价性** · **MUST NOT** 在联网环境内跑 ⇒ 须在**已断网**的环境内跑 ⇒ `unshare --net --map-root-user .venv/bin/python harness/scripts/gates/gate_G28_offline_equiv.py --root .` ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · L7 判据写准**：**本地判据 = 跳过并在任务 note 中注明**（**MUST NOT** 判失败）⇒ ⇒ ⇒ **CI 档 MUST 跑且 MUST 绿** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **本 feature 的新增测试 MUST NOT** 依赖网络）· `gate_G22_isolated_env.py`（⚠️ **MUST** 跑 —— 本 feature **改的就是这个门禁** · T038）· `gate_G29_contract_carrier.py` · `gate_G30_attribution.py --root .` ⇒ ⇒ ⚠️ **G29 的验收脚本集是三个**（`graph_core` / `agent_loop` / `visualization`）⇒ ⇒ **`graph_core` 与 `agent_loop` MUST exit 0**（G29 judge 2 treats any non-`NotImplementedError` failure as a real failure）⇒ ⇒ ⇒ **`visualization.py` 仍为 `ENV_NOT_READY`**（其用例组归 **B22F1 / B23F1 / B8F2** · 本 feature **MUST NOT** 越界实现 ⇒ ⇒ ⇒ **MUST NOT** 被读成「三个脚本全绿」）⇒ ⇒ ⚠️ `git diff --stat HEAD -- harness/demo/target.py` MUST be empty ⇒ ⇒ ⚠️ G30 must show **no new** violations beyond the 8 pre-existing ones（SC-011 · SC-012 · SC-013 · SC-015 · G29）
- [X] T052 Final consistency review of `specs/b7f3-invoke-full-state/{spec.md, plan.md, research.md, data-model.md, contracts/invoke-contract.md, contracts/upstream-parity.md}`: the id sets 裁定 1–16 · P-01…P-14 · D-92…D-102（**11 条**）· X-1…X-6 · I-01…I-14 · ES-01…ES-11（契约 §2 · 2026-11-16 analyse 轮 · S-15）· EV-1/EV-2/EV-4 · S-1…S-45（⚠️ **2026-11-16 analyse 轮第五轮订正**：原写 `S-1…S-26`，已过期 ⇒ **MUST NOT** 漏检 S-27…S-45（**第五轮追加 S-38…S-45**）· **FND-D1**）· FR-001…FR-028 · SC-001…SC-020 must match one-to-one（⚠️ **EV-3 已撤销** ⇒ 不在集合内）, and the spec's traceability table must stay **bidirectionally gap-free** ⇒ ⇒ fix drift **only factually**（never weaken a criterion）⇒ ⇒ ⚠️ **必查项 ①**：「无值 key 填 `None` + 只读快照禁令」这条规则在 **16 处**重述 —— **已带「仅覆盖型（无归约器）」限定**的 6 处：spec **FR-009**（消歧）/ **US2**（口径注）/ **SC-003**（⚠️ 归约型 key 的例外）· 契约 **R-06** · data-model **§2.3**（表）+ **§5.5**；**原未带限定**的 **10 处**（**S-14 已回修 6 处**）：spec **裁定 3** / **FR-009**（首句）/ **Edge Cases**（首条）/ **Key Entities** · 契约 **R-03** · data-model **§2.5** ⇒ ⇒ ⇒ **＋ 2026-11-16 第三轮回修补限定的 4 处**（**FND-B1**）：spec **P-03**（上游对照表）/ spec **X-1**（偏离登记）· `contracts/upstream-parity.md` **P-03** / **X-1** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **16 处 MUST 逐字同义**（口径已一致 · 判据零放宽）⇒ ⇒ ⇒ ⚠️ **必查项 ②**：偏离登记的「类别」列 MUST 与对照表的「关系」列**逐字一致**（宪法原则 XI 末条）⇒ ⇒ X-1 / X-2 / X-3 MUST 带 `STRICTER` 令牌 ⇒ ⇒ ⇒ **必查项 ③**：**差分场景组**的判词分布（SAME 7 / STRICTER 3 / DIFF 1）**≠** **上游对照表**的分布（SAME 6 / STRICTER 3 / DIFF 5）⇒ ⇒ ⇒ 两处**不得混用**⇒ ⇒ ⇒ ⚠️ **必查项 ④（2026-11-16 第三轮回修 · **2026-11-16 analyse 轮第五轮 · FND-H7** 改写为**可执行**判据**）· 判据只可更严**：三份工件 MUST NOT 再出现「**把『不再是 2』当作判据**」的**正面表述** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **判定方式（MUST 按此判定 · 可执行）**：grep `rc ∉ {2}` / `returncode != 2` / `rc != 2` / `退出码 ≠ 2` 等**判据形态** ⇒ ⇒ ⇒ **命中数 MUST == 0** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 用「全文 grep『不再是 2』」这种**裸字符串**判据 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **理由**：该短语在三份工件里共 **7** 处命中（`spec.md` / `plan.md` / `tasks.md`），**全部**出现在「**MUST 断言 `rc == 0`（不是「不再是 2」）**」这类**禁止语境**里 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **裸字符串判据恒红** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽**（`rc == 0` 一字不动 · 弱化形态仍为 0 命中）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **必查项 ⑤ · 双份表同步**：spec 的「上游对照表 / 偏离登记」与 `contracts/upstream-parity.md` §2 / §4 是**同一份内容的两处落点** ⇒ ⇒ ⇒ MUST **逐条语义一致**（关系 / 判词 / 偏离编号 / 实测引用）⇒ ⇒ ⇒ ⇒ **发现漂移 MUST 双侧同改**（MUST NOT 只改一侧）⇒ ⇒ ⇒ ⇒ ⚠️ **必查项 ⑥ · 阶段编排**：**T040 / T041 / T042 MUST 位于 Phase 2**（T011 之后 · T014 之前）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **判定方式（可执行）**：检查**本文件**的**阶段归属**（`T040` / `T041` / `T042` 出现在 **Phase 2** 的任务列表里 ⇒ 且**不出现在** Phase 10 的任务列表里）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 用「全文 grep『Phase 10』」这种**裸字符串**判据 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **理由**：「原编排排在 Phase 10」/「已由 Phase 10 前移」等**历史陈述**共 **4** 处命中 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **裸字符串判据恒红** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽**（阶段归属这一事实本身不变）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **必查项 ⑦ · 门面的旋钮搬运**：三份工件 MUST NOT 出现「**把门面写成『传 `max_concurrency` 关键字』**」的**正面表述**（门面 **恒不传**该关键字 · 读取点在 L2 · 裁定 13 / FR-023）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **判定方式（可执行）**：grep `run_graph(..., max_concurrency=` / `run_graph(..., max_concurrency)` 等**调用形态** ⇒ ⇒ ⇒ **命中数 MUST == 0** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 用「全文 grep『门面』」这种**裸字符串**判据 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **理由**：「门面 **MUST NOT** 传」/「初版仍写门面传该关键字」等**禁止语境**共 **3** 处命中 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **裸字符串判据恒红** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽**⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **必查项 ⑧ · G19 的白名单与矩阵行（2026-11-16 analyse 轮第四轮 · C1 回修）**：① `tests/facade/test_facade_gates.py` MUST 存在 `MATRIX_ROWS_UPDATABLE_BY_B7F3` 且**恰含** `CompiledGraph` 一项 ⇒ ⇒ ② `README.md` 的 `CompiledGraph` 行 MUST 已移除「行为细节挂起 B7F3」且**等价程度列 == 「部分等价」** ⇒ ⇒ ③ spec 的破冻结面清单 MUST 收录该项、**T045** 的追认文字 MUST 含第 ④ 项 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ④ 三份工件 MUST NOT 再出现「G19 的白名单**已含** `CompiledGraph`」这类**事实错误**断言 ⇒ ⇒ ⚠️ **必查项 ⑨ · 编号域消歧（2026-11-16 analyse 轮第四轮 · H1 回修 · 第五轮订正范围）**：`spec.md` + `plan.md` + `tasks.md` 的 `FND-` 编号集 MUST 与 `research.md` §7.2 对照表的编号集**逐项相等**（⚠️ **第五轮订正**：原检查范围只列 `plan.md` + `tasks.md` ⇒ ⇒ 而 **FND-B9 / FND-C2 / FND-M6** 的处置落点在 **spec.md** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 原范围下该自检**必红** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 范围**补齐为三份工件**） ⇒ ⇒ ⇒ 且 MUST NOT 出现**无 `FND-` 前缀**的 analyse 轮发现编号 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **必查项 ⑩ · 计划阶段自洽**：plan 的 **Phase C** MUST NOT 再含 C6（人工记录守卫） ⇒ ⇒ ⇒ ⇒ ⇒ 且 plan 的 Phase C1 的 `I-01…I-14` 枚举 MUST 补出 **I-12 / I-13 / I-14** 及其承载任务（FR-001…FR-028 / SC-001…SC-020 的一致性 · **L2**）

---

## 追溯表（任务 → FR / SC）

> **宪法原则 VI（v1.11.0 补 + v1.13.0 补）**：追溯 MUST 到**判据级** ⇒ ⇒ 每条 **SC** 至少挂一条
> **能判定它**的任务 ⇒ ⇒ 「实现 / 记录 / 审计」类任务**不**构成判定覆盖 ⇒ ⇒ 本表与 spec 的
> 「追溯表（FR → SC）」**双向**齐备。
>
> **标记说明**：**※** = 该任务是**登记 / 记录 / 实现 / 审计 / 接线**类 ⇒ ⇒ **不**构成该 SC 的**判定覆盖**
>（宪法原则 VI v1.11.0 + v1.13.0）⇒ ⇒ **判定覆盖**由标**测试 / 断言**类的任务承担（见下方「判据级覆盖自检」）。

| 任务 | 覆盖的 FR | 覆盖的 SC | 归属 |
|---|---|---|---|
| **T001** | — | SC-019 | — ※（**绿基线** · 候选清单；实测归 **T011**）|
| **T002** | — | SC-001 · SC-002 · SC-006 · SC-007（**夹具**） | — ※（夹具类 · 不构成判定覆盖）|
| **T003** | — | — | — ※|
| **T004** | — | — | — ※|
| **T005** | FR-001 | SC-019 | 裁定 1 ※|
| **T006** | FR-001 | SC-019 | 裁定 1 · G19 ※|
| **T007** | FR-001 · FR-009 | SC-020 | 裁定 1 / 3 ※|
| **T008** | FR-002 | SC-016 | 裁定 1 / 3 / 8 · **FND-H2 / FND-H3 / FND-M3** ※|
| **T009** | FR-008…FR-009 · FR-012 | SC-001 · SC-003 | 裁定 2 / 3 / 4 ※|
| **T010** | FR-002 · FR-004…FR-005 · FR-013…FR-014 | SC-002 · SC-010 | 裁定 3 / 6 / 8 / 10 ※|
| **T011** | — | SC-015 · SC-018 | EV-1 / EV-2 · G29 · 首次执行红点登记 + **冻结断言实测化** ※|
| **T012** | FR-023 | SC-006 | 裁定 13 · 破冻结面 T-3 ※|
| **T013** | FR-023 | — | 裁定 13 · 破冻结面 T-3 ※|
| **T014** | FR-001 · FR-026 · FR-028 | SC-015 | 破冻结面 · I-12 |
| **T015** | — | SC-017 | DD-11 |
| **T016** | — | SC-017 | — |
| **T017** | FR-003 · FR-007…FR-008 · FR-010 · FR-012 | SC-001…SC-002 · **SC-013** | I-01 · **I-03** · **I-13** |
| **T018** | FR-028 | SC-016 | 裁定 4 · I-10 |
| **T019** | FR-008 | — | 裁定 2 / 3 ※|
| **T020** | FR-009 · FR-011 · FR-025 | SC-003 | 裁定 12 · I-02 |
| **T021** | FR-009 | — | 裁定 3 ※|
| **T022** | FR-016 | SC-004 | I-06 |
| **T023** | FR-017 | SC-005 | I-07 |
| **T024** | FR-017…FR-018 · FR-020 | — | 裁定 9（**间接**：FR-020 → SC-005 → **T023** 的断言型覆盖） ※|
| **T025** | FR-021…FR-022 | SC-006…SC-007 | 裁定 5 · I-08 |
| **T026** | FR-021 · FR-023 | — | 裁定 5 · 裁定 13 ※|
| **T027** | FR-023 | SC-006 | — |
| **T028** | FR-014 | SC-010 | 裁定 8 · I-04 · I-05 |
| **T029** | FR-015 · FR-019 | SC-010 | 裁定 7 · **FND-A4**（桩 checkpointer 载体）|
| **T030** | FR-014 | — | 裁定 8 ※|
| **T031** | FR-004 · FR-006 | SC-008…SC-009 | 裁定 10 / **11**（步末清空）· I-09 |
| **T032** | FR-002 · FR-005 | — | 裁定 10 ※|
| **T033** | FR-024 | SC-011…SC-012 | — |
| **T034** | FR-009 | SC-020 | 裁定 3 · I-11 |
| **T035** | FR-024 | — | 裁定 14 ※|
| **T036** | — | SC-017 | — ※|
| **T037** | — | SC-017 | — |
| **T038** | FR-027 | SC-014 | 裁定 15 ※|
| **T039** | FR-024 | SC-011 | 原则 I ※|
| **T040** | — | SC-015 | G29 ※（**Phase 2** · A3 前移）|
| **T041** | — | SC-015 | G29 ※（**Phase 2** · A3 前移）|
| **T042** | — | SC-002 | G29 ※（**Phase 2** · A3 前移）|
| **T043** | — | SC-001 · SC-010 | — ※|
| **T044** | — | SC-018 | 原则 V · EV-4 ※|
| **T045** | — | SC-019 | 破冻结面 T-1 / T-2 / T-3 ※|
| **T046** | FR-019 | **SC-018 · SC-019** | **I-14** · 宪法原则 VI（v1.11.0 + v1.13.0 的「人工门禁类 SC」条款） |
| **T047** | FR-009 | SC-020 | G19 ※|
| **T048** | — | SC-015 | 原则 X ※|
| **T049** | — | SC-018 | 原则 V ※|
| **T050** | — | — | 裁定 16（就绪顺序 · D-3） ※|
| **T051** | — | SC-011…SC-013 · SC-015 | G29 |
| **T053** | — | SC-019 | 破冻结面 **T-4** · G19 ※（**白名单的设立** · 与 T045 的追认第 ④ 项对齐）|
| **T052** | FR-001 · FR-028 | SC-001 · SC-020 | — ※|

> **判据级覆盖自检（2026-11-16 analyse 轮 · 复核 · 按 v1.13.0 口径）**：**判定任务**（测试 / 断言 / 跑门禁）⇒ SC-001 → **T017 / T018** · SC-002 → **T017** · SC-003 → **T020** · SC-004 → **T022** · SC-005 → **T023** · SC-006 → **T025 / T027** · SC-007 → **T025** · SC-008 → **T031** · SC-009 → **T031** · SC-010 → **T028 / T029** · SC-011 → **T033** · SC-012 → **T033** · SC-013 → **T017** · SC-014 → **T051**（跑 **G22** 门禁）· SC-015 → **T014** · SC-016 → **T018** · SC-017 → **T016 / T037** · **SC-018 → T046** · **SC-019 → T046** · SC-020 → **T034**
> ⇒ ⇒ **20 条 SC 全部至少挂一条「能判定它」的任务**（宪法原则 VI v1.11.0 + v1.13.0）⇒ ⇒ ⇒ ⇒ **SC-018 / SC-019** 的判定载体 = **人工验证记录的文档守卫断言**（**T046**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 「写记录」类任务（**T044 / T045 / T049**）与「审计」类任务**不**计入判定覆盖（标 ※）。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — **BLOCKS all user stories**
- **User Stories (Phase 3–9)**: All depend on Foundational completion
  - The **test** tasks are independent per story (six separate files) ⇒ stories can proceed **in parallel**
  - The **implementation** tasks touch `src/freegraph/_stategraph.py` ⇒ they are **sequential** (one at a time)
- **Polish (Phase 10)**: Depends on the desired user stories being complete; T051/T052 are the last two
  - ⚠️ **T053（MUST 早于 T047）**：G19 白名单 ⇒ ⇒ **MUST** 在 README 兼容矩阵行更新（T047）之前落地
    ⇒ ⇒ 否则 G19 的逐字节比对会把 `CompiledGraph` 行判红 ⇒ ⇒ ⇒ **MUST NOT** 把 T053 排到 T047 之后

### User Story Dependencies

- **User Story 1 (P1)**: after Foundational — no dependency on other stories
- **User Story 2 (P1)**: after Foundational — shares `_full_state` with US1 but is independently testable
- **User Story 3 (P1)**: after Foundational — independent
- **User Story 4 (P2)**: after Foundational — independent
- **User Story 5 (P2)**: after Foundational — independent
- **User Story 6 (P2)**: after Foundational — independent
- **User Story 7 (P3)**: after Foundational — independent

### Within Each User Story

- Tests are written **first** and MUST fail before the story's **audit** task fixes any deviation（⚠️ 本 feature 的**主体实现**在 **Phase 2**（T005–T016）已完成 ⇒ ⇒ **故事阶段的任务是「判据级审计 + 补测」**，不是「首次实现」）
- The audit task runs **after** the story's tests
- Story complete before moving to the next priority

### Parallel Opportunities

- All Setup tasks marked `[P]` can run in parallel (T002 / T003 / T004)
- In Foundational, **T015** can run in parallel with T005–T014 (different file) ⇒ ⇒ ⚠️ **T016** **NOT** `[P]`（依赖 T015）⇒ ⇒ ⇒ ⇒ ⚠️ **T015 / T036 同文件**（`tests/differential/parity_probe.py`）⇒ ⇒ ⇒ ⇒ **两者 MUST 串行**（`T036` **未**标 `[P]` · **FND-B10**）⇒ ⇒ ⇒ ⇒ ⚠️ **T040 / T041** 同文件（`graph_core.py`）⇒ ⇒ ⇒ ⇒ **两者 MUST 串行**；**T042**（`agent_loop.py`）⇒ ⇒ ⇒ ⇒ **可与 T040 / T041 并行**
- Each user's **test** tasks are parallelizable with each other (different files, one story at a time) ⇒ ⇒ ⚠️ **同文件对 MUST 串行**（**五组** · 2026-11-16 analyse 轮第五轮 · **FND-B10** 补齐）：**T017 / T020**（`test_invoke_full_state.py`）· **T028 / T029**（`test_invoke_interrupt.py`）· **T022 / T023**（`test_invoke_errors.py`）· **T025 / T027**（`test_invoke_config.py`）· **T015 / T036**（`tests/differential/parity_probe.py`）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **五组的后一条均已去 `[P]`**（`T020` / `T029` / `T023` / `T027` / `T036` · 2026-11-16 第三轮回修 **FND-B5** + 第五轮 **FND-B10**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **另**：`T040 / T041`（`harness/demo/graph_core.py`）**同文件** ⇒ ⇒ **两者 MUST 串行**（`T041` **未**标 `[P]`）；**T042**（`harness/demo/agent_loop.py`）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **可与 T040 / T041 并行** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **T003**（`[P]` · 建 6 个测试文件的**空骨架**）⇒ ⇒ **与后续填充同一批文件的任务天然串行** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 与填充任务并行
- The six story test files are mutually independent ⇒ **different stories can be tested in parallel**
- Polish tasks marked `[P]` can run in parallel (different files) ⇒ ⇒ **T053** `[P]`（`tests/facade/test_facade_gates.py` · 无其它任务碰该文件）⇒ ⇒ ⚠️ **T053 仍 MUST 早于 T047**（G19 白名单 ⇒ README 矩阵行更新）⇒ ⇒ ⇒ ⚠️ **T037** **NOT** `[P]`（依赖 T036）⇒ ⇒ ⇒ ⇒ ⚠️ **T046**（人工验证记录守卫测试）**不在**其中 ⇒ ⇒ 它 MUST 在 **T044 / T045** 之后执行（否则守卫断言必然红）

---

## Parallel Example: User Story 1

```bash
# Launch the story's test file and the shared fixture work together:
Task: "Create shared invoke-test support in tests/facade/_invoke_support.py"
Task: "Add the full-state tests in tests/facade/test_invoke_full_state.py"

# Then the story's audit (depends on the tests):
Task: "Audit src/freegraph/_stategraph.py against contracts/invoke-contract.md §3.1 / §3.2"
```

## Parallel Example: User Story 3 & 4 (different stories, different files)

```bash
Task: "Add the unknown-key tests in tests/facade/test_invoke_errors.py"
Task: "Add the config tests in tests/facade/test_invoke_config.py"
# ⇒ the implementation edits to src/freegraph/_stategraph.py are sequential
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational（**CRITICAL** — blocks every story）
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `pytest tests/facade/test_invoke_full_state.py -q` green ⇒ `invoke` returns `{'messages': [...], 'llm_calls': N}`
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → the mechanical chain works
2. US1 → full state (MVP!)
3. US2 → every schema key is present
4. US3 → unknown keys fail loudly
5. US4 → both config shapes work
6. US5 → suspension / resume observable
7. US6 → multi-session isolation
8. US7 → zero side effects
9. Polish → differential scenarios, acceptance scripts, docs, ratification, downstream wiring, full regression

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 + US2（same test file ⇒ sequential）
   - Developer B: US3 + US5
   - Developer C: US4 + US6 + US7
3. Stories complete and integrate independently; the shared implementation file is edited **one at a time**

---

## Notes

- `[P]` tasks = different files, no dependencies
- `[Story]` label maps a task to its user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing (for the behavioural tasks)
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
- ⚠️ **SC-013 整条判定**（2026-11-16 analyse 轮 · **EV-3 已撤销**）：**终止**半边 + **屏障**半边（「多源汇合」= **静态多源边** · `add_edge([a, b], c)` · **B7F4 已交付于 L2**）**都**由本 feature 判 ⇒ ⇒ **判据不放宽** ⇒ ⇒ ⚠️ **「条件边路由」（B8F1）是「能力尚未交付」，不是「物理不可达成」** ⇒ ⇒ 两者**不可**混为一条
- ⚠️ **追认次数 ≤ 1 / feature**: the single ratification covers the **5 类** of broken frozen surfaces（**唯一事实源 = spec.md「Assumptions」的「破面全集 5 类」**）：① the L1 protocol's `input` widening ② the L1 protocol's `config` widening ③ the L2 `run_graph` `max_concurrency` reading point（**compatible extension**）④ the **G19** 兼容矩阵行白名单（`MATRIX_ROWS_UPDATABLE_BY_B7F3` · 含 README 矩阵行的措辞更新）⑤ the **four** frozen-assertion replacements（`test_compiled_graph.py:73-86` · `test_facade.py:195-200` · `test_facade.py:217-234` · `test_acceptance_script.py:15-34`）⇒ **MUST NOT** break any other frozen surface (B7F2's compiled-product holding face · L2's public exports · the facade's 7 symbols · the API snapshot)
- ⚠️ **人工门禁类 SC 的判定覆盖**（2026-11-16 analyse 轮 · 宪法 v1.13.0 新条款）：**SC-018 / SC-019** 的判定由 **T046**（文档守卫断言）承担 ⇒ ⇒ ⇒ 「写记录」类任务（**T044 / T045 / T049**）**不**构成判定覆盖 ⇒ ⇒ ⇒ ⇒ 且 **T046** MUST 在 **T044 / T045** 之后 ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 把守卫断言放在 **T034**（Phase 9）⇒ ⇒ ⇒ ⇒ ⇒ 否则 **T034→T046 之间必然红**（撞「MUST NOT 写永久红 CI」）
- ⚠️ **验收脚本的降级 MUST 以实测为据**（2026-11-16 analyse 轮）：**T011** 记录**首次执行**的真实红点 ⇒ ⇒ **T040 / T042** 的降级范围 MUST 据此确定 ⇒ ⇒ ⇒ **MUST NOT** 只凭推理降级、**MUST NOT** 顺手降级与本 feature 无关的红点
- ⚠️ **阶段编排（2026-11-16 analyse 轮 · 第三轮回修 · FND-A3 · CRITICAL）**：**T040 / T041 / T042 已由 Phase 10 前移至 Phase 2**（置于 **T011** 之后 · **T014** 之前）⇒ ⇒ ⇒ **理由**：`invoke` 接通（T010）后 `graph_core.py` 必以 `rc == 1` 结束 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 脚本修复若留在 Phase 10 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **Phase 2 → Phase 10 之间存在红窗**（撞宪法 v1.6.0「MUST NOT 写永久红的 CI」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **T014 MUST 在本阶段内完成**（**脚本先修绿 · 再替换冻结断言**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **任务号不变 · 仅换阶段** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 所有跨工件引用无需改动
- ⚠️ **发现编号的消歧（2026-11-16 analyse 轮第四轮 · H1 回修）**：本文件与 `plan.md` 里的
  analyse 轮**发现编号**一律带 **`FND-`** 前缀（`FND-A1` / `FND-B7` / `FND-C4` / `FND-H5` / `FND-L3` …）
  ⇒ ⇒ ⇒ **唯一解释处 = `research.md` §7「编号域与发现编号对照表」**（⚠️ **2026-11-16 analyse 轮第五轮**：§7.1 已补 **T-4**、§7.3 已增「**跨 feature 的 `T-#` MUST 带来源 feature 前缀**」· **FND-H6**；另 spec 的跨 feature 裁定号已补来源前缀（「B10F1 的裁定 4」/「B7F1 的裁定 33」）· **FND-C9**） ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒
  ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 与 spec 的**承接条款 `H-1…H-10`**、**里程碑 `M1…M4`**、**层 `L1…L3`**、
  ⇒ ⇒ ⇒ ⇒ ⇒ **契约条目 `C1…C27`**、**验收脚本用例组 `A1–A10` / `B1–B4`** 混淆 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒
  ⇒ ⇒ ⇒ ⇒ ⇒ **T052 必查项 ⑨** 会核对 `FND-` 编号集与对照表**逐项相等** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒
- ⚠️ **No new source file**: `src/freegraph/_stategraph.py` is a **file-level L3** registry entry ⇒ a new L3 module would be an **L3 → L3** violation (G25) ⇒ **zero** new files under `src/`
- ⚠️ **New test/verification `.py` files MUST carry the verbatim signature header**（G5 / G19 / **G30** scans every tracked `.py`）⇒ ⇒ **MUST NOT** add them to `tests/facade/_gatesupport.py::SIGNED_SOURCE_FILES`（that list is frozen; G30 already covers new files)
