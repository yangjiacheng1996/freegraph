---

description: "Task list for B25F1 · 双跑验收（fake CI + 真实模型人工）+ 迁移说明 + README 收口"
---

# Tasks: B25F1 · 双跑验收（fake CI + 真实模型人工）+ 迁移说明 + README 收口

**Input**: Design documents from `/specs/b25f1-final-acceptance/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: **包含**。spec 定义了 SC-001…SC-006、A1–A5，且宪法原则 VI 要求「判据级可追溯」；
每个用户故事 MUST 有**可执行验收 / 测试**任务。本 feature 的测试 / 验收脚本本身就是交付物：
`harness/demo/diagnostics.py`、`tests/runtime/test_b25f1_*.py`、`tests/differential/test_b25f1_*.py`、
`harness/verification/B25F1/acceptance.py`。

**Organization**: 任务按用户故事分组；US1–US3（P1）在 Foundational 完成后可独立实现 / 测试；
US4（P2）在文档基线就绪后可独立实现 / 测试；Phase 7 为一键验收跨切面；Phase 8 收口。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: `US1` / `US2` / `US3` / `US4`；Setup / Foundational / Phase 7 / Phase 8 不带故事标签
- 每个任务都带**精确文件路径**或**精确命令**；末尾 `→ FR-xxx / SC-xxx / A-x` 是**反向追溯**。

---

## 追溯表（FR → 任务）

| FR | 任务 |
|---|---|
| FR-001 | T001 / T006 / T007 / T008 / T012 / T017 |
| FR-002 | T007 / T008 / T012 / T017 |
| FR-003 | T008 / T012 / T016 / T017 / T042 / T046 |
| FR-004 | T003 / T030 / T033 / T035 / T042 |
| FR-005 | T031 / T034 / T035 / T049 |
| FR-006 | T009 / T011 / T032 / T039 / T044 / T046 / T049 |
| FR-007 | T042 / T044 / T045 / T046 / T047 |
| FR-008 | T004 / T005 / T019 / T025 / T026 / T027 / T028 / T029 / T035 / T041 / T044 / T051 / T052 |
| FR-009 | T036 / T037 / T039 / T040 / T041 / T049 |
| FR-010 | T036 / T038 / T040 / T041 |
| FR-011 | T002 / T010 / T018 / T050 |
| FR-012 | T019 / T020 / T025 / T026 / T027 / T028 / T044 |
| FR-013 | T021 / T028 / T042 / T044 |
| FR-014 | T022 / T028 / T042 / T044 |
| FR-015 | T023 / T028 / T042 / T044 |
| FR-016 | T008 / T012 / T020 / T027 / T044 |
| FR-017 | T027 / T028 / T041 / T043 / T044 / T050 |
| FR-018 | T013 / T014 / T015 / T017 |
| FR-019 | T019 / T024 / T028 / T051 |
| FR-020 | T043 / T048 / T050 |
| FR-021 | T004 / T025 / T051 |
| FR-022 | T001 / T018 / T050 / T053 |

## 追溯表（SC → 任务）

| SC | 任务 |
|---|---|
| SC-001 | T012 / T017 / T042 / T046 / T049 |
| SC-002 | T003 / T030 / T033 / T035 / T046 / T048 |
| SC-003 | T009 / T011 / T031 / T032 / T034 / T035 / T044 / T045 / T046 / T048 / T049 |
| SC-004 | T004 / T005 / T019 / T025 / T026 / T027 / T028 / T029 / T035 / T041 / T044 / T046 / T051 / T052 |
| SC-005 | T027 / T036 / T037 / T038 / T040 / T041 / T049 / T050 |
| SC-006 | T013 / T014 / T015 / T017 |

## 追溯表（A1–A5 → 任务）

| 判据 | 任务 |
|---|---|
| A1 fake 轮 | T007 / T008 / T012 / T016 / T017 / T042 / T046 |
| A2 真实模型轮 | T019 / T020 / T021 / T022 / T023 / T025 / T026 / T027 / T028 / T029 / T042 / T046 / T051 / T052 |
| A3 框架零出站 | T003 / T030 / T033 / T035 / T046 |
| A4 验收脚本集全绿 | T009 / T011 / T032 / T042 / T044 / T045 / T046 / T048 |
| A5 `target.py` 未改 | T002 / T010 / T018 / T050 |

> **双向追溯**：上三表是 FR/SC/A → 任务的**代表性映射（不要求穷举）**；每条任务末尾的 `→ FR-xxx / SC-xxx / A-x` 是任务 → 判据，二者合起来构成双向追溯。
> **FR-036** 属 B5F2 的外部引用，不计入本 feature 的 FR 覆盖表。

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 建立验收基座（测试依赖组、固定脚本哈希、出站归因、记录骨架）。

- [X] T001 Add the **`acceptance`** PEP 735 dependency group to `pyproject.toml`（`langchain>=1.0,<2` + `IPython>=8`）；**MUST NOT** 进入 `[project].dependencies` / `[project.optional-dependencies]`；注释写明「测试 / 验收侧 · 不进发行包」；**验证 `langchain` / `langchain-core` 解析为兼容组合**（本机曾出现版本不匹配；不兼容则调整版本并记录）→ FR-001 / FR-022 / SC-001
- [X] T002 [P] Create `tests/runtime/data/b25f1_target_py.sha256`（目录不存在则先 `mkdir -p tests/runtime/data`；单行 `<64 hex>  harness/demo/target.py`，由当前 `target.py` 生成；小写 hex）；**MUST NOT** 修改 `harness/demo/target.py` → FR-011 / A5
- [X] T003 [P] In `harness/demo/acceptance.py`，把 `EgressProbe._classify` 对齐 G27 的「**第一个非标准库帧**」规则（标准库 `traceback` / `sys` 即可，**不得** import `_gatekit`）；保持**只观测不阻断** → FR-004 / SC-002 / A3
- [X] T004 Update `harness/demo/acceptance.py`：`collect_env()` 记录 `LANGSMITH_*` 清空方式；`run_suite()` 的子进程 env **剔除** 全部 `LANGSMITH_*`；`build_record()` 更新为「用户出站逐条记录、不判失败、不设目标白名单」+ 两段式真实轮占位 + 三附件占位（同一文件，T003 之后执行）→ FR-008 / FR-021 / SC-004
- [X] T005 [P] Create `harness/verification/B25F1/manual-verification.md` 骨架：五段式标题（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）+ 三附件标题；**正文可暂空**，但在 T051 完成前不得宣布完成 → FR-008

**Checkpoint**: 依赖组 / 哈希 / 出站归因 / 记录骨架就绪。

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: fake 注入、诊断脚本、固定脚本防御与诊断测试。**所有用户故事都依赖本阶段。**

**⚠️ CRITICAL**: 本阶段完成前，US1 的 fake 轮与 Phase 7 的一键验收不得开始。

- [X] T006 Add a **non-autouse** B25F1 fixture to `tests/runtime/conftest.py`：在 fixture 内 `pytest.importorskip("langchain")` / `pytest.importorskip("IPython")`，提供 `install_fake_init_chat_model()`（**在 `target.py` 导入前**猴补）；**MUST NOT** 影响其它测试 → FR-001
- [X] T007 [P] Create `harness/verification/B25F1/fake_model.py`：`FakeModel`（`bind_tools()` 返回自身；`invoke()` 2 轮序列：第 1 轮 `tool_calls=[{name:"add", args:{"a":3,"b":4}, id:"call_1", type:"tool_call"}]`，第 2 轮非空文本）；`install()` 猴补 `langchain.chat_models.init_chat_model`；第 3 次调用显式失败；带署名头 → FR-001 / FR-002
- [X] T008 Create `harness/verification/B25F1/fake_round.py`：同进程 `runpy.run_path(str(REPO_ROOT / "harness/demo/target.py"), run_name="__main__")`（**MUST 用绝对路径**，`REPO_ROOT = Path(__file__).resolve().parents[3]`）+ `--subprocess`（临时 `sitecustomize.py` + `PYTHONPATH`）；捕获 `IPython.display.display` / `Image` 得到 PNG 字节；复用 G27 归因 / `_gatekit` 监测出站；断言 A1（`messages==4` / `llm_calls==2` / `int(ToolMessage.content)==7` / 两键）与 PNG 结构；退出码 0/1/2；末行 `B25F1 fake round: PASS|FAIL`；带署名头 → FR-001 / FR-002 / FR-003 / FR-016 / A1 / A3
- [X] T009 [P] Create `harness/demo/diagnostics.py`：trace（`FileTraceStore` / `SqliteTraceStore` + `query()` 四类过滤 / 组合 / 空过滤 + `json.dumps`）/ checkpoint（`MemorySaver` / `SqliteSaver` + `get_state` / `get_state_history` / `stream(checkpoints)`）/ 时间旅行（重放 / `update_state` 覆盖与归约 / 分叉后原历史不变 / 中断组合）；只 import `freegraph` + 标准库；退出码 0/1/2；末行 `diagnostics: PASS|FAIL`；带署名头 → FR-006 / SC-003
- [X] T010 [P] Create `tests/runtime/test_b25f1_target_guard.py`：`test_target_py_matches_recorded_sha256`（读取 `tests/runtime/data/b25f1_target_py.sha256`）；`test_target_py_matches_baseline_ref`（`baseline = os.environ.get("B25F1_BASELINE_REF", "origin/main")`；`git diff --exit-code <baseline> -- harness/demo/target.py`；不可用 ⇒ `pytest.skip` 且理由明确）；**MUST NOT** 只比 `git diff HEAD`；带署名头 → FR-011 / A5
- [X] T011 Create `tests/runtime/test_b25f1_diagnostics.py`：subprocess 跑 `harness/demo/diagnostics.py`，`rc==2` ⇒ skip；`rc==0` 断言输出含 trace / checkpoint / time_travel 三组标记与末行 PASS；带署名头（依赖 T009）→ FR-006 / SC-003

**Checkpoint**: fake 注入、diagnostics、双重基线、诊断测试就绪；US1–US4 可开始。

---

## Phase 3: User Story 1 - CI 自动跑通验收基线 (Priority: P1) 🎯 MVP

**Goal**: fake 轮原样跑通 `harness/demo/target.py`；四条断言点全成立；`target.py` 零改动；
同一 fake 输入在 freegraph 与 LangGraph 上可比对；B5F2 模型工厂可跑模型形状规格。

**Independent Test**: 在干净环境跑 `harness/verification/B25F1/fake_round.py`（同进程 +
`--subprocess`）与 `tests/runtime/test_b25f1_target_fake.py`；断言 `messages==4` /
`llm_calls==2` / 工具结果归一为 `7` / 状态含两键；`target.py` SHA 与基线 ref 均通过。

### Tests for User Story 1

- [X] T012 [P] [US1] Create `tests/runtime/test_b25f1_target_fake.py`：使用 T006 fixture（或 subprocess 调 T008）；断言四条固定断言点（**`messages==4` 为最终口径；立项书已更正为 4**）、`tool_call.id == "call_1"`、`ToolMessage.tool_call_id == "call_1"`、PNG 签名 / IHDR、框架出站 `0`、用户出站逐条记录、路由函数仍读 `tool_calls`（正交）；缺 `langchain` / `IPython` ⇒ skip；带署名头 → FR-001 / FR-002 / FR-003 / FR-016 / A1 / A3
- [X] T013 [P] [US1] Create `tests/differential/test_b25f1_final_acceptance.py`：`B25F1-D-01`（同一 fake 输入在 freegraph / LangGraph 上跑固定脚本，节点序列 / `messages` 长度 == **4** / `llm_calls` / 工具结果 / 最终状态键集一致）、`B25F1-D-02`（C4 / C8 回归）、`B25F1-D-03`（target 双重基线；可直接复用 T010 的守卫断言，不要求在 differential 文件内重复实现）；`B25F1-D-04` 的模型工厂断言落在 T015 的 `test_b25f1_model_factory.py`；上游缺席 ⇒ `pytest.skip`；LangGraph 侧用临时副本替换包名或模块别名（记录方式）；带署名头 → FR-018 / SC-006 / A5

### Implementation for User Story 1

- [X] T014 [US1] Modify `tests/differential/spec_builder.py`：**新增** `build_model_graph_spec(*, name, schema, nodes, initial_input, model_factory, conditional_edges=())`（显式要求非空 `model_factory`；实现为「先以空 factory 走 `validate_graph_spec`，再 `dataclasses.replace` 回填」）；**MUST NOT** 放宽 `build_graph_spec` 的纯本地 `model_factory` 非空 ⇒ `GraphSpecError` 语义；同步 B8F1 A10 零改动清单（`spec_builder.py` 只增入口，`test_differential.py` 仍零改动）→ FR-018 / SC-006
- [X] T015 [P] [US1] Create `tests/differential/_b25f1_model_factory.py`（FakeModelFactory / make_fake_model）与 `tests/differential/test_b25f1_model_factory.py`：**B25F1-D-04**（`build_model_graph_spec` 的模型形状规格可执行）；纯本地规格非空 `model_factory` 仍 `GraphSpecError`；B5F2 的 `test_a_non_empty_model_factory_is_an_explicit_failure` 保持绿；带署名头（依赖 T014）→ FR-018 / SC-006
- [X] T016 [US1] Update `harness/demo/acceptance.py`：把 `harness/verification/B25F1/fake_round.py` 作为 **target fake 验收步**运行（子进程；记录实际输出；不计入「四组」）；`--suite` 可选跳过；同一文件（T004 之后）→ FR-003 / A1
- [X] T017 [US1] Run `harness/verification/B25F1/fake_round.py`（默认 + `--subprocess`）、`tests/runtime/test_b25f1_target_fake.py`、`tests/differential/test_b25f1_final_acceptance.py`、`tests/differential/test_b25f1_model_factory.py`；把**实际输出**写入 `harness/verification/B25F1/manual-verification.md` 的「实际输出」段 → FR-001 / FR-002 / FR-003 / FR-018 / SC-001 / SC-006 / A1
- [X] T018 [US1] Audit A5 / 零运行时改动：`git diff -- src/freegraph harness/demo/target.py` 为空；无新增门禁编号；记录命令与退出码 → FR-011 / FR-022 / A5

**Checkpoint**: fake 轮可独立通过；A1 / A5 有实测证据；模型工厂不破坏 B5F2。

---

## Phase 4: User Story 2 - 人工用真实模型跑一遍 (Priority: P1)

**Goal**: 真实模型轮两段式跑通（固定脚本段 + 专用探针段）；五要素记录 + 三附件；
B14F1 / B15F1 / B16F1 / B20F1 / B20F2 / B21F1 / B23F1 / B24F1 承接证据非空。

**Independent Test**: 配置真实模型凭据 → 跑 `harness/verification/B25F1/real_round.py` →
记录实际输出；无凭据时登记环境偏离（不宣布完成）；`manual-verification.md` 五段式 + 三附件齐备，
`tests/runtime/test_b25f1_manual_record_guard.py` 绿。

### Tests for User Story 2

- [X] T019 [P] [US2] Create `tests/runtime/test_b25f1_manual_record_guard.py`（**先写；记录缺失 / 含占位 / 无真实轮证据时 `pytest.skip`，避免永久红 CI；严格断言由 T052 在发布 / 人工门禁启用**）：断言记录存在、五段式、正文非空、三附件齐备且各含实际输出、含 B15/B16/B20/B21/B23/B24 实测证据关键词、**含 B14F1 `harness/verification/B14F1/manual-verification.md` + `harness/verification/B14F1/acceptance.py` 引用**、含 **Y-01**、**含接入路径（官方直连 / 兼容网关；gateway 不得写成官方直连）**、遗留问题非空；**「实际输出」与「结论」段 MUST NOT 以整句「符合预期」/「未验证」替代实测**（允许出现在否定 / 引用语境）；占位符检测针对 `待填` / `TODO` / `⬜` / 空表格；带署名头 → FR-008 / FR-012 / FR-019 / SC-004 / A2

### Implementation for User Story 2

- [X] T020 [US2] Create `harness/verification/B25F1/real_round.py` **段 1（固定脚本）**：真实模型执行 `target.py`；可选兼容网关时**外部包装** `init_chat_model`（只接线、不伪造输出、记录路径与原因）；捕获 PNG 字节；监测框架出站 / 用户出站；输出实际最终消息 / 工具结果 / 接入路径；带署名头 → FR-012 / FR-016 / A2
- [X] T021 [US2] Extend `real_round.py` **段 2 trace（真实模型）**：用**真实模型**（同一接入，官方直连优先 / 兼容网关记录）跑同一 agent 循环图；**分别两次独立运行**：一次 `FileTraceStore(directory=...)`、一次 `SqliteTraceStore(database=...)`；统一 `RunConfig(thread_id="b25f1-real")` 并捕获 `run_id` / 起止时间；记录 JSONL 文件数 / `kind="span"` / `kind="trace_record"` / 模型 span `parent` / C23 关联键；两后端 `query()` 四类过滤（`run_id` / `thread_id` / `node` / 时间窗）+ 组合 + 空过滤器（条数 + `json.dumps`），并逐条比对 → FR-013
- [X] T022 [US2] Extend `real_round.py` **段 2 OTLP（真实模型）**：在 `real_round.py` 内定义 `RecordingSpanExporter`（实现官方 `SpanExporter.export` / `shutdown`，把 spans 记录到内存；**无网络**）；显式构造 `OtlpExporter(exporter=RecordingSpanExporter())`（默认）或可选 `OtlpExporter(endpoint=local_grpc)`（本地接收端；不可用 ⇒ 环境偏离，不判失败）；记录 span 数 / `name` / `trace_id` / `parent` / `gen_ai.*`；用户显式 OTLP 端点不计入框架出站 → FR-014
- [X] T023 [US2] Extend `real_round.py` **段 2 checkpoint / 时间旅行（真实模型）**：`SqliteSaver.from_conn_string(path)` + `RunConfig(thread_id="b25f1-real")`；记录 `get_tuple` / `get_state` / `get_state_history` / `stream(checkpoints)` 实际输出（事件数 / payload）；`update_state` 覆盖 / 归约、历史重放、分叉后原历史不变、中断组合 → FR-015
- [X] T024 [US2] Extend `real_round.py` 输出 / 记录段：把 **B14F1 的 `harness/verification/B14F1/manual-verification.md` 与 `harness/verification/B14F1/acceptance.py`** 纳入发布前人工验收清单（只引用、不回改）；输出清单 → FR-019
- [X] T025 [US2] Fill `harness/verification/B25F1/manual-verification.md`：五要素（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）+ 三附件（依赖断言 / 出站监测 / 反向断言）；写明 `LANGSMITH_*` 清空方式；遗漏即不完整 → FR-008 / FR-012 / SC-004
- [X] T026 [US2] Run real round (`real_round.py`) 并记录**实际输出**；无凭据 / 网络受限 ⇒ 登记**环境偏离**（已完成 / 未完成 / 原因），**MUST NOT** 写「未验证」或「符合预期」；**完全无法执行 ⇒ 不得宣布 v1.0 收口** → FR-012 / SC-004 / A2
- [X] T027 [US2] Record B23F1 PNG 实测（字节数 / PNG 结构 / 框架出站 0）与 B24F1 发行产物 + `COMPAT.md` 声明的实测 / 引用；**Y-01**（`Command.goto` 缺省 `()` vs `None`）写入迁移说明与记录的遗留问题 → FR-016 / FR-017 / SC-005
- [X] T028 [US2] Record cross-feature 证据引用：B15F1 / B16F1 / B20F1 / B20F2 / B21F1 的真实轮证据（文件 / 行数 / 条数 / span 数 / 历史条目）逐条写入记录并注明来源 → FR-013 / FR-014 / FR-015 / FR-019 / SC-004
- [X] T029 [US2] Run `tests/runtime/test_b25f1_manual_record_guard.py` after T025–T028；记录未最终收口时 T019 守卫 `skip`（不判失败）；T052 在发布 / 人工门禁（T051 之后）启用严格断言（无真实轮时**不得**用空记录冒充绿）→ FR-008 / SC-004 / A2

**Checkpoint**: 真实轮两段式证据 + 人工记录完整；A2 可判定。

---

## Phase 5: User Story 3 - 能证明 freegraph 自己没有偷偷联网 (Priority: P1)

**Goal**: 框架出站 = 0；用户出站逐条记录、不判失败、不设目标白名单；断网等价性可判定。

**Independent Test**: 跑 `tests/runtime/test_b25f1_zero_egress.py`（框架 0 + 用户出站任意目标）与
`tests/runtime/test_b25f1_offline_equivalence.py`（进程内断网核心用例全绿）；Linux 上跑 G28。

### Tests for User Story 3

- [X] T030 [P] [US3] Create `tests/runtime/test_b25f1_zero_egress.py`：使用 `_gatekit.record_egress` 或 `fake_round`；断言框架出站 `0`；注入一次用户出站（任意目标）⇒ 记为 user、**不判失败**、**不做目标白名单**、**不被阻断**；带署名头 → FR-004 / SC-002 / A3
- [X] T031 [P] [US3] Create `tests/runtime/test_b25f1_offline_equivalence.py`：进程内禁用 `socket.socket.connect` / `socket.create_connection`（抛异常）后，以**同进程 `runpy.run_path`**（捕获 `SystemExit`）依次执行并断言退出码 0：① `harness/verification/B25F1/fake_round.py`（fake 轮）；② `harness/demo/graph_core.py`；③ `harness/demo/agent_loop.py`；④ `harness/demo/visualization.py`；⑤ `harness/demo/diagnostics.py`。每项同时断言「核心用例全绿 + 框架出站 0」；OS 级 G28 仅作增强证据，不替代本进程内层；带署名头 → FR-005 / SC-003

### Implementation for User Story 3

- [X] T032 [US3] Update `harness/demo/acceptance.py` `SUITES`：新增 `("diagnostics", "diagnostics.py", ...)`；执行顺序 `acceptance → graph_core → agent_loop → visualization → diagnostics → target(fake)`；缺失 diagnostics ⇒ **失败而非跳过**（同一文件，T016 之后）→ FR-006 / SC-003
- [X] T033 [US3] Update `harness/demo/acceptance.py` 零出站记录：框架出站 `0`、用户出站逐条（目标 + 归因）、观测面声明；子进程同样剔除 `LANGSMITH_*`（同一文件，T032 之后）→ FR-004 / SC-002 / A3
- [X] T034 [US3] Run OS 级断网（Linux）：`unshare --net --map-root-user uv run --no-project --python .venv python harness/scripts/gates/gate_G28_offline_equiv.py`；确认新测试在断网下可跑（无需新增排除项；记录守卫按 T019 的 skip 规则不判失败）；不具备 `unshare` ⇒ 记录环境偏离，不判失败 → FR-005 / SC-003
- [X] T035 [US3] Record zero-egress + offline actual outputs（框架 0 / 用户出站条数 / G28 退出码 / 环境偏离）in `manual-verification.md` → FR-004 / FR-005 / SC-002 / SC-003 / A3

**Checkpoint**: A3 可判定；断网等价性有进程内 + OS 级证据。

---

## Phase 6: User Story 4 - 从 LangGraph 迁过来的人知道要改什么 (Priority: P2)

**Goal**: 迁移说明三类 + Y-01；最终 README 快速上手 / 三条承诺 / 能力表 / 独立实现声明 /
`COMPAT.md` 绝对链接且不复制矩阵。

**Independent Test**: 打开 `harness/proposals/更名与迁移说明.md` 的 v1 章节与 `README.md`；
断言三类、Y-01、绝对链接、无完整矩阵；跑 docs guard。

### Tests for User Story 4

- [X] T036 [P] [US4] Create `tests/runtime/test_b25f1_docs_guard.py`：断言迁移说明含「同名直接可用 / 同名但行为有差异 / 需改写」三类 + **Y-01** + `COMPAT.md` 指针；README 含**快速上手章节**、**能力处置表（或等价标题「能力 → freegraph 处置」）**、**绝对** `COMPAT.md` 链接、三条承诺、独立实现声明、**无完整逐符号矩阵**；带署名头 → FR-009 / FR-010 / SC-005

### Implementation for User Story 4

- [X] T037 [P] [US4] Update `harness/proposals/更名与迁移说明.md`：新增 v1 迁移章节（三类清单 + Y-01 的 v1 行为提示 + 逐符号细节指向 `COMPAT.md`）；**MUST NOT** 复制完整矩阵 → FR-009 / SC-005
- [X] T038 [P] [US4] Finalize `README.md`：快速上手（安装 / 最小图 / `[otlp]` / fake / 真实轮入口）+ 三条承诺 + 能力处置表 + 独立实现声明 + **绝对链接** `https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md`；**MUST NOT** 重新引入完整矩阵 → FR-010 / SC-005
- [X] T039 [P] [US4] Update `harness/demo/README.md`：标记 `diagnostics.py` 已交付；更新执行顺序与双跑 / 上游差分跑说明；保留 `target.py` 只读基准描述 → FR-006 / FR-009
- [X] T040 [US4] Run `tests/runtime/test_b25f1_docs_guard.py` + B24F1 的 `tests/contracts/test_b24f1_docs.py` + G8 / G19 / G29 兼容矩阵检查；记录实际输出 → FR-009 / FR-010 / SC-005
- [X] T041 [US4] Record migration / README actual evidence（三类标题 / Y-01 / 绝对链接 / 无完整矩阵）in `manual-verification.md` → FR-009 / FR-010 / SC-005 / SC-004
- [X] T055 [US4] 更新 `harness/proposals/立项书.md` 的「验收脚本集」口径：把「四组 + diagnostics」统一为「四组（含 diagnostics）」（§4.2 S4 / §5.2 A8 / §9.2 / §5.8 相关行）；**不改判据** → FR-006 / FR-009 / SC-003 / SC-005

**Checkpoint**: 迁移说明与 README 收口；SC-005 可判定。

---

## Phase 7: Cross-Cutting - 一键验收与记录

**Purpose**: `harness/verification/B25F1/acceptance.py` 汇总 A1–A5；`--skip-real` 供 CI；
`--real` 供人工；`--record` 生成记录草稿。

- [X] T042 Create `harness/verification/B25F1/acceptance.py`：步骤 `DEP` / `A1` / `A3` / `A4` / `A5`；
  `--real` 额外跑 A2；`--skip-real` 显式跳过 A2；`--record <path>` 生成五要素 + 三附件草稿；
  退出码 `0/1/2`（缺 `freegraph` / `langchain` / `IPython` / `--real` 凭据 ⇒ 2）；
  末行 `B25F1 acceptance: PASS|FAIL`；带署名头 → FR-003 / FR-006 / FR-007 / FR-008 / FR-012 / A4
- [X] T043 Extend `harness/verification/B25F1/acceptance.py` `DEP`：断言 `Requires-Dist` 基础为空 /
  唯一 extra `otlp`；运行时 `sys.modules` **反向断言**无 `langchain` / `langchain_core`（干净子进程）；
  输出实际值（同一文件，T042 之后）→ FR-017 / FR-020
- [X] T044 Extend `harness/verification/B25F1/acceptance.py`：接入 `diagnostics` 组（A4）与
  `real_round.py`（A2）；`--record` 写入各步骤实际输出 / 三附件 / 环境偏离（同一文件，T043 之后）
  → FR-006 / FR-007 / FR-008 / FR-012 / FR-013 / FR-014 / FR-015 / FR-016 / FR-017 / SC-004 / A4
- [X] T045 Create `tests/runtime/test_b25f1_acceptance.py`：subprocess 跑
  `harness/verification/B25F1/acceptance.py --skip-real`；`rc==2` ⇒ `pytest.skip`（环境未就绪）；
  `rc==0` 断言末行 `B25F1 acceptance: PASS`；带署名头（依赖 T042）→ FR-007 / SC-003 / A4
- [X] T046 Run `harness/verification/B25F1/acceptance.py --skip-real --record /tmp/opencode/b25f1-acceptance-draft.md`；
  把草稿中的实际输出 / 三附件 / 环境偏离**合并**进 `harness/verification/B25F1/manual-verification.md`
  （**MUST NOT** 覆盖 T026–T028 已记录的真实轮证据）；`--real` 仅人工执行；记录 exit code
  → FR-007 / FR-008 / SC-003 / SC-004 / A4

**Checkpoint**: 一键验收可独立运行；CI 与人工入口分离。

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: CI 接线、全量门禁、quickstart、零改动审计、人工记录收口、追溯闭合。

- [X] T047 Update `.github/workflows/ci.yml`：`actions/checkout@v7` 加 `with: fetch-depth: 0`；
  在 **Linux x86 全量档**（`matrix.runner == 'ubuntu-24.04' && (matrix.python == '3.11' || matrix.python == '3.14')`）
  于「Run test suite」前安装 `--group acceptance`；新增 B25F1 验收步
  `uv run --no-project --python .venv python harness/verification/B25F1/acceptance.py --skip-real`，
  **使用与安装步相同的 `if:` 条件**；其余平台不安装、不运行该步（相关用例 `importorskip` ⇒ skip，非失败）；
  **MUST NOT** 改 job 名 / 分支保护检查名 → FR-007 / SC-003 / A4
- [X] T048 [P] Run full `pytest tests/ -ra` + `python harness/scripts/gates/gate_G21_dependencies.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml` + `python harness/scripts/gates/gate_G23_licenses.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml` + `python harness/scripts/gates/gate_G24_config_layer.py` + `python harness/scripts/gates/gate_G25_import_graph.py` + `python harness/scripts/gates/gate_G26_network_static.py` + `python harness/scripts/gates/gate_G29_contract_carrier.py` + `python harness/scripts/gates/gate_G30_attribution.py` + Linux `python harness/scripts/gates/gate_G22_isolated_env.py` / `python harness/scripts/gates/gate_G27_zero_egress.py` / `unshare --net --map-root-user uv run --no-project --python .venv python harness/scripts/gates/gate_G28_offline_equiv.py`；记录命令 / 输出（记录守卫按 T019 的 skip 规则，不因记录未收口假红）→ FR-020 / SC-002 / SC-003
- [X] T049 [P] Run [quickstart.md](./quickstart.md) end-to-end（fake 轮 / A5 / 四组（含 diagnostics）/ 一键验收 / 断网 / 依赖断言 / 文档核对）并记录实际输出；真实轮按人工环境执行或登记环境偏离 → FR-005 / FR-006 / FR-009 / SC-001…SC-006
- [X] T050 [P] Audit `git diff -- src/freegraph harness/demo/target.py` 为空；无新增门禁编号；
  `COMPAT.md` 的 `Command` / `get_state` / `Send` 行仍含 **Y-01 / Y-02 / Y-03**；
  所有新 `.py` 带署名头（G30）→ FR-011 / FR-017 / FR-020 / FR-022 / A5
- [X] T051 Finalize `harness/verification/B25F1/manual-verification.md`：移除全部占位符 / 「待填」；
  五要素 + 三附件 + 各承接证据实际输出；**真实轮未完成 ⇒ 保留环境偏离并不得宣布完成** → FR-008 / FR-012 / SC-004 / A2
- [X] T052 Run `tests/runtime/test_b25f1_manual_record_guard.py` after T051，**仅在发布 / 人工门禁**启用严格断言（常驻 CI 保持 T019 的 skip 规则，避免永久红）；严格模式要求记录含**真实轮实测证据**；无真实轮时发布门禁失败 / 阻断，**MUST NOT** 用空记录冒充绿 → FR-008 / SC-004 / A2
- [X] T053 Final traceability audit in `specs/b25f1-final-acceptance/tasks.md`：每个 FR / SC / A
  至少挂一条代表性任务；核对每条任务末尾的 `→ FR/SC/A` 与其职责一致（正向表为代表性映射，
  不要求穷举）；复核 `T001–T055` 全部在位；标记复选框；核对
  `specs/b25f1-final-acceptance/spec.md` / `plan.md` 状态 → FR-022 / SC-001…SC-006
- [X] T054 Final gate report in `harness/verification/B25F1/manual-verification.md`：把 T048 / T049 /
  T052 的命令 / 退出码 / 结论写入记录；确认 `harness/verification/B25F1/acceptance.py --skip-real`
  退出码 0、`target.py` 零改动、框架出站 0；**真实模型轮未通过 ⇒ 不得宣布 v1.0 收口**
  → FR-007 / FR-008 / SC-001…SC-006

**Checkpoint**: 全部门禁绿；人工记录含实测输出；双跑 / 零出站 / 文档收口完成（或明确登记环境偏离）。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖，可立即开始。
- **Foundational (Phase 2)**: 依赖 Setup；**阻塞 US1–US4** 与 Phase 7。
- **US1 / US2 / US3（P1）**: 依赖 Foundational；三者可并行（US2 的真实轮需凭据，可在 US1/US3 之后或并行）。
- **US4（P2）**: 依赖 Foundational；可与 US2 并行。
- **Phase 7（Cross-Cutting）**: 依赖 US1（fake）/ US3（diagnostics / egress）/ US2（真实轮探针）。
- **Phase 8（Polish）**: 依赖全部目标故事与 Phase 7。

### User Story Dependencies

- **US1**: 依赖 T006–T008 / T010 / T014；不依赖 US2/US3/US4。
- **US2**: 依赖 T006–T008 / T019；真实轮依赖凭据；不依赖 US1 的差分测试。
- **US3**: 依赖 T008 / T009 / T030 / T031；不依赖 US1/US2。
- **US4**: 依赖 T036–T039；不依赖 US1/US2/US3。
- **Phase 7**: 依赖 T008（fake）/ T009（diagnostics）/ T020–T023（real）/ T030–T031（egress/offline）。

### Within Each Story

- **US1**: T014 → T015；T012 / T013 [P] after T008；T016 after T004/T008；T017 → T018。
- **US2**: T020 → T021 → T022 → T023 → T024（同一文件，顺序）→ T025 → T026 → T027 → T028 → T029。
  **T019 守卫在记录未收口时 `skip`；T029 只确认 skip 状态，严格判定留给 T052（发布 / 人工门禁）。**
- **US3**: T030 / T031 [P] → T032 → T033 → T034 → T035。
- **US4**: T036 / T037 / T038 / T039 [P] → T040 → T041。
- **Phase 7**: T042 → T043 → T044 → T045 / T046；T045 依赖 T042。
- **Phase 8（必须遵守）**: T047 → T048 / T049 / T050 [P] → T051 → T052 → T053 → T054；
  **T051 / T052 必须在真实轮证据（T026–T028）之后**；**T019 在记录未收口时 `skip`，
  T034 / T048 可在 skip 状态下先跑；T052 仅在发布 / 人工门禁启用严格模式**（宪法 v1.13.0）。

### Critical Path

```text
T001 → T002 / T003 / T004 / T005 →
T006 → T007 → T008 → T009 / T010 / T011 →
T012 / T013 / T014 / T015 / T016 → T017 → T018 →
T019 / T020 → T021 → T022 → T023 → T024 → T025 → T026 → T027 → T028 → T029 →
T030 / T031 → T032 → T033 → T034 → T035 →
T036 / T037 / T038 / T039 → T040 → T041 →
T042 → T043 → T044 → T045 / T046 →
T047 → T048 / T049 / T050 → T051 → T052 → T053 → T054
```

---

## Parallel Opportunities

| 组 | 可并行任务 | 说明 |
|---|---|---|
| Setup | T002 / T003 / T005 | 不同文件；T004 依赖 T003（同文件） |
| Foundational | T007 / T009 / T010 | 不同文件；T008 依赖 T007；T011 依赖 T009 |
| US1 tests | T012 / T013 | 不同测试文件；均在 T008 之后 |
| US1 model factory | T014 → T015 | T015 依赖 T014 的新入口 |
| US2 independence | T020（段 1）与 US1 / US3 可并行 | 真实轮凭据独立 |
| US3 tests | T030 / T031 | 不同测试文件 |
| US4 docs | T036 / T037 / T038 / T039 | 不同文件；T040 依赖它们 |
| Phase 8 | T048 / T049 / T050 | 不同验证面 |

**Parallel Example: Foundational**

```bash
# T006 first (conftest fixture), then:
#   T007 harness/verification/B25F1/fake_model.py
#   T009 harness/demo/diagnostics.py
#   T010 tests/runtime/test_b25f1_target_guard.py
```

**Parallel Example: P1 stories after Foundational**

```bash
# Developer A: US1 (T012–T018) fake 轮 + 差分 + 模型工厂
# Developer B: US2 (T019–T029) 真实轮两段式 + 记录
# Developer C: US3 (T030–T035) 零出站 + 断网 + diagnostics 编排
```

---

## Implementation Strategy

### MVP First (US1 + US3 + diagnostics)

本 feature 的**CI 自动化 MVP** = fake 轮（US1）+ 零出站 / 断网（US3）+ `diagnostics.py`：
它能在没有真实模型凭据的环境中独立验证 A1 / A3 / A4 / A5。

1. 完成 Phase 1 + Phase 2。
2. 完成 US1 → `fake_round.py` 可独立通过（A1 / A5）。
3. 完成 US3 → 框架出站 0 + 断网 + diagnostics（A3 / A4）。
4. **STOP and VALIDATE**：`harness/verification/B25F1/acceptance.py --skip-real` 退出码 0。

### v1.0 最终完成（P1 + P2）

本 feature 的**最终判定**要求：

- **US1**（fake 轮）+ **US2**（真实模型轮）+ **US3**（零出站 / 断网）+ **US4**（迁移说明 / README）
  全部完成；
- **真实模型轮未完成 ⇒ 不得宣布 v1.0 收口**（原则 V）；
- 人工记录五要素 + 三附件；`target.py` 零改动；框架出站 0；四组（含 diagnostics）全绿。

### Incremental Delivery

1. Setup + Foundational → 验收基座。
2. US1 → fake 轮 + A1/A5。
3. US3 → 零出站 + 断网 + diagnostics。
4. US2 → 真实轮 + 记录。
5. US4 → 迁移说明 + README。
6. Phase 7 → 一键验收。
7. Phase 8 → CI / 全量门禁 / 记录收口 / 追溯。

### Parallel Team Strategy

1. 全员完成 Setup + Foundational。
2. Foundational 后：
   - Developer A：US1（fake / 差分 / 模型工厂）。
   - Developer B：US2（真实轮 / 记录）。
   - Developer C：US3（零出站 / 断网 / diagnostics）。
   - Developer D：US4（迁移 / README）。
3. Phase 7 / 8 由一人统一收口（保证证据一致）。

---

## Notes

- **[P] tasks** = 不同文件、无未完成依赖。
- **[Story] label** = US1–US4，保证每段可独立实现 / 测试。
- **Tests are included** because SC-001…SC-006 + A1–A5 + 宪法原则 VI require judged coverage.
- **MUST NOT** 修改 `harness/demo/target.py`；A5 用 SHA-256 + 基线 ref 双重基线。
- **MUST NOT** 修改 `src/freegraph/**`；本 feature 零运行时改动。
- **MUST NOT** 让用户出站判失败或做目标白名单；freegraph 是**通用型图框架**。
- **MUST NOT** 把真实轮放进 `tests/`（避免 G27 / G28 误伤）；真实轮 = `real_round.py` 人工脚本。
- **MUST NOT** 用「符合预期」「未验证」替代实际输出；环境偏离须写明完成 / 未完成范围。
- **MUST** 在 `manual-verification.md` 保留 **Y-01**（`Command.goto` 缺省 `()` vs `None`）的 v1 行为提示；
  运行时对齐归 **v2 独立契约修订**。
- **MUST** 以 **`messages == 4`** 为最终口径；**立项书 §4.2 S4 / §9.2 已同步更正为 4**
  （「3」只是 System + AI + Tool 的三点投影）。
- **MUST** 用全路径区分两个 `acceptance.py`：`harness/demo/acceptance.py` = 四组（`graph_core` / `agent_loop` / `visualization` / `diagnostics`）；
  `harness/verification/B25F1/acceptance.py` = B25F1 一键验收。
- **MUST** 用户出站逐条记录、不判失败、不设目标白名单；**立项书 §9.2 / D12 已同步为 C 口径**。
- **MUST** 让所有新 `.py` 带署名头（G30 扫描全部 tracked `.py`）；T006 / T007 / T008 / T009 /
  T010 / T011 / T012 / T013 / T015 / T019 / T030 / T031 / T036 / T042 / T045 均须逐文件添加。
- **MUST** 保持 `acceptance` 依赖组只在 `dependency-groups`，不进 `Requires-Dist`。
- **MUST** 保持 Phase 7 的 `harness/verification/B25F1/acceptance.py --skip-real` 退出码 0 作为 CI 判据；`--real` 是人工门禁。
- **MUST NOT** 在真实轮未完成时宣布 v1.0 收口（A2 是硬判据）。
