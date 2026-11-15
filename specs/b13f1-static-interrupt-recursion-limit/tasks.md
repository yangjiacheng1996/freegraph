---
description: "Task list for B13F1 · 静态中断点 + recursion_limit"
---

# Tasks: B13F1 · 静态中断点（`interrupt_before` / `interrupt_after`）+ `recursion_limit`

**Input**: Design documents from `/specs/b13f1-static-interrupt-recursion-limit/`
**Prerequisites**: plan.md（required）· spec.md（required · 用户故事）· research.md · data-model.md ·
contracts/（`static-interrupt-contract.md` / `recursion-limit-contract.md` / `upstream-parity.md`）· quickstart.md

**Tests**: **包含**测试任务 —— spec **FR-031 / SC-023** 要求「纯 L2 单元可测 + 行/分支覆盖率 == 100%」
⇒ 测试 MUST 先写 · MUST 先失败（此时静态断点 / 上限语义尚未接线）。

**Organization**: 按用户故事分组（**8** 个 · P1–P3）⇒ 每个故事可**独立实现、独立测试**。

---

## 格式：`[ID] [P?] [Story] 描述`

- **[P]**：可并行（**不同文件** / 无未完成依赖）
- **[Story]**：所属用户故事（US1…US8）—— 仅**用户故事阶段**的任务带
- **每条任务 MUST 带确切文件路径**（本仓库约定）
- 每条任务末尾用 `⇒ FR-xxx · SC-xxx` 标注**追溯**

## 路径约定

- 源码：`src/freegraph/runtime/`（L2 · 层注册表**目录条目** ⇒ **零注册表改动**）
- ⚠️ 新增**私有**模块：`src/freegraph/runtime/_static.py` · `_recursion.py`（**不进 `__all__`** ⇒ 导出面仍 **23**）
- 既有源码：`src/freegraph/runtime/superstep.py` · `_fanout.py` · `_interrupt.py`（只增不改语义）
- L1 契约层：`src/freegraph/contracts/`（**零改动**；`GraphRecursionError` / `RunConfig.recursion_limit` 已存在）
- 门面：`src/freegraph/graph.py`（**零改动**）· 构建器 / `compile()` / `invoke()`（**零改动** · M2）
- 测试：`tests/runtime/`（L2）· `tests/differential/`（差分）
- 人工验证：`harness/verification/B13F1/`
- 验收脚本：`harness/demo/graph_core.py` · `harness/demo/README.md`
- 契约 / 规格：`specs/b13f1-static-interrupt-recursion-limit/` · `specs/b7f1-superstep-loop/` ·
  `specs/b10f1-interrupt-resume/` · `specs/b11f1-send-fanout/`
- 下游提示词：`harness/features/`（**只接线 · 逐条最小改动**）
- ⚠️ **设计决策的权威落点**：`research.md` §3（**D-01…D-14**；与下游承接 **D-1…D-8** 分开编号）· `data-model.md`（实体 / 校验 / 不变量）·
  `contracts/`（运行期口径）⇒ 实施前**先读**它们

---

**本 feature 的可测判据总表**（**32 FR + 24 SC ↔ 115 条任务**）—— **逐 SC 一行**：

**SC-001** 由 **T006 · T031 · T032 · T034 · T036 · T037 · T040** 承载；
**SC-002** 由 **T006 · T042 · T043 · T044 · T045 · T047 · T048** 承载；
**SC-003** 由 **T053 · T054 · T058** 承载；
**SC-004** 由 **T003 · T005 · T014 · T026 · T067 · T068 · T069 · T070 · T072** 承载；
**SC-005** 由 **T098 · T099 · T100 · T102 · T103 · T114** 承载；
**SC-006** 由 **T011 · T015 · T035 · T046 · T061 · T062 · T063 · T064 · T065 · T066** 承载；
**SC-007** 由 **T036 · T037 · T040 · T041 · T055 · T056 · T058 · T060** 承载；
**SC-008** 由 **T057** 承载；
**SC-009** 由 **T007 · T016 · T017 · T027 · T073 · T074 · T075 · T076 · T077 · T078 · T079 · T080 · T081 · T082** 承载；
**SC-010** 由 **T083 · T084 · T085 · T086 · T087 · T088 · T089** 承载；
**SC-011** 由 **T010 · T018 · T019 · T020 · T022 · T028 · T033 · T038 · T039 · T043 · T044 · T047 · T048 · T049 · T051 · T075 · T104** 承载；
**SC-012** 由 **T019 · T021 · T028 · T050 · T051 · T052 · T076** 承载；
**SC-013** 由 **T015 · T054 · T059** 承载；
**SC-014** 由 **T002 · T004 · T009 · T012 · T023 · T024 · T026 · T069 · T105** 承载；
**SC-015** 由 **T013 · T024 · T025 · T029 · T090 · T091 · T092 · T093 · T094 · T097 · T108** 承载；
**SC-016** 由 **T011 · T094 · T096 · T107 · T113** 承载；
**SC-017** 由 **T111** 承载；
**SC-018** 由 **T071 · T110** 承载；
**SC-019** 由 **T030 · T096 · T110** 承载；
**SC-020** 由 **T095 · T106 · T113** 承载；
**SC-021** 由 **T008 · T103 · T112 · T114** 承载；
**SC-022** 由 **T101 · T102 · T115** 承载；
**SC-023** 由 **T004 · T005 · T006 · T007 · T109** 承载；
**SC-024** 由 **T001 · T030 · T102 · T106 · T108 · T110 · T114** 承载。

> **权威映射 = 文末「任务 ↔ spec 追溯表」** ⇒ 修改判据归属时 MUST **同步**两处
> ⇒ 两处 MUST NOT 漂移。**本表与附录均由任务行尾标签机械生成**（同一事实源）；
> 改任务行标签后 MUST 重新生成两表。

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 工程准备 + 测试骨架 + **绿基线** + 人工验证骨架

- [X] T001 跑既有测试套件（`.venv/bin/python -m pytest -q`）并把**绿基线**计数（**1203 passed / 4 skipped**）写进 `harness/verification/B13F1/manual-verification.md` 的「环境」段（文件未建 ⇒ 先建最小骨架；T008 再补齐五段式）⇒ FR-025 · SC-024
- [X] T002 [P] 创建 `src/freegraph/runtime/_static.py`：**私有**模块骨架（署名头逐字 + 模块 docstring 为首个语句 + 常量与空函数）⇒ FR-002 / FR-008 · SC-014
- [X] T003 [P] 创建 `src/freegraph/runtime/_recursion.py`：**私有**模块骨架（署名头 + 模块 docstring + `DEFAULT_RECURSION_LIMIT` 与空函数）⇒ FR-010 / FR-011 / FR-012 · SC-004
- [X] T004 [P] 创建 `tests/runtime/test_graph_spec_static.py`：署名头 + 模块 docstring + 手写 `GraphSpec` 夹具骨架 ⇒ FR-003 / FR-031 · SC-014 / SC-023
- [X] T005 [P] 创建 `tests/runtime/test_recursion_limit.py`：署名头 + 模块 docstring + 自环图夹具骨架 ⇒ FR-010 / FR-031 · SC-004 / SC-023
- [X] T006 [P] 创建 `tests/runtime/test_static_interrupt.py`：署名头 + 模块 docstring + before / after 图夹具骨架 ⇒ FR-001 / FR-031 · SC-001 / SC-002 / SC-023
- [X] T007 [P] 创建 `tests/runtime/test_static_interrupt_fanout.py`：署名头 + 模块 docstring + `Command(goto=[Send...])` 夹具骨架 ⇒ FR-015 / FR-016 / FR-031 · SC-009 / SC-023
- [X] T008 创建 `harness/verification/B13F1/manual-verification.md`（**五段式**：验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题 + 来源覆盖表骨架；若 T001 已建最小文件则在其上补齐）⇒ FR-025 · SC-021

**Checkpoint**: 骨架与基线就绪

---

## Phase 2: Foundational（阻塞性前置 · 所有故事共享）

**Purpose**: 静态断点的**形状 / 校验 / 纯函数** + `recursion_limit` 的**解析 / 校验** +
检查点 metadata / fanout 账本的**共享接缝** —— 所有用户故事都依赖它

**⚠️ CRITICAL**: 未完成本 Phase 前，任何用户故事都不能开工

- [X] T009 [P] 在 `src/freegraph/runtime/_static.py` 实现常量 `STATIC_BEFORE` / `STATIC_AFTER` 与 `normalize_static_points(value, nodes, field_name) -> tuple[str, ...]`：裸 `"*"` ⇒ **可执行节点**（排除 `__start__` / `__end__`）；**裸非 `"*"` 字符串（含空串 / 裸哨兵）⇒ `TypeError`**；**序列元素**空串 ⇒ `ValueError`，哨兵 / 序列中的 `"*"` / 未知节点 ⇒ `ValueError`；非 `str` 元素 / `Mapping` / `set` / 非 `Sequence` ⇒ `TypeError`；重复去重；`None` ⇒ `TypeError`。⚠️ 本函数是 V-22…V-25 的**唯一抛出点** ⇒ FR-002 / FR-003 · SC-014 · data-model §1.2
- [X] T010 在 `src/freegraph/runtime/_static.py` 实现 `static_hit(targets, configured)`、`static_allowed(ack, state)` 与 `build_static_ack(state)`（ack = `{"channel_versions": dict}`；**对 ack 键与当前键的并集**比较版本 ⇒ 新通道视为 0 → >0，无任何推进 ⇒ 抑制）⇒ FR-008 · SC-011 · data-model §2.5
- [X] T011 在 `src/freegraph/runtime/superstep.py` 的 `GraphSpec` 增两个 **keyword-only** 字段 `interrupt_before: str | Sequence[str] = ()` / `interrupt_after: str | Sequence[str] = ()`；归一 / 校验由 T012 的 `_validate_graph_spec` → `normalize_static_points` **单一入口**完成（**不在 `__post_init__` 重复第二套**）；构造后字段为 `tuple`（**防御性拷贝**）；⚠️ `GraphSpec` 是 `@dataclass(frozen=True)` ⇒ MUST 用 **`object.__setattr__`** 写回归一后的 `tuple`，且**先校验节点表、再展开 `"*"` / 做 V-25** ⇒ FR-002 / FR-029 · SC-006 / SC-016
- [X] T012 在 `src/freegraph/runtime/superstep.py` 的 `_validate_graph_spec` **调用** `normalize_static_points`，落地 V-22…V-25 并用 **`object.__setattr__`** 写回归一后的 `tuple`（构造期单一入口；**B7F1 契约既有 V-1…V-9 与 B7F4 的 V-16 形态族一字不改；B11F1 的 V-15…V-21 段不动**；**不重复第二套校验**）⇒ FR-003 / FR-027 · SC-014
- [X] T013 在 `src/freegraph/runtime/superstep.py` 的 `run_super_step` 与 `run_super_steps` 入口加 **V-26**：`spec.interrupt_before` 或 `.interrupt_after` 非空 ⇒ `ValueError`（消息说明「静态断点只在图级 `run_graph` 生效」）；签名 / 返回类型不变 ⇒ FR-017 · SC-015
- [X] T014 [P] 在 `src/freegraph/runtime/_recursion.py` 实现 `DEFAULT_RECURSION_LIMIT = 10007`、`resolve_config(config)`（`None` / `Mapping` / `RunConfig`；未知键 `ignore_unknown=True`）、`resolve_limit(config_limit, max_steps)`（`config_limit is None` ⇒ 落回 `max_steps`，**不进入校验**）、`validate_limit(value)`（**非 `None`**：`type is int` 且非 `bool`；`>= 1`）⇒ FR-010 / FR-011 / FR-012 · SC-004
- [X] T015 在 `src/freegraph/runtime/superstep.py` 的 `run_graph` 把 `config` 注解放宽为 `RunConfig | Mapping[str, Any] | None`，调用 `resolve_config` / `resolve_limit`，把 **effective limit** 传给 `_first_graph` / `_resume_graph` / `_run_graph_loop`；**不新增** `recursion_limit=` 关键字 ⇒ FR-010 / FR-014 · SC-006 / SC-013
- [X] T016 [P] 在 `src/freegraph/runtime/_fanout.py` 新增 `encode_fanout(fanout) -> dict` / `decode_fanout(data) -> dict[int, _FanOut]`（外层 key = `str(TaskId)`；`producer` / `suppresses_static` / `tasks[]{target,arg,index,suppresses_static}`；缺键 ⇒ `{}`；`arg` 原样）⇒ FR-016 · SC-009
- [X] T017 在 `src/freegraph/runtime/superstep.py` 的 `SchedulerState.to_checkpoint` 增 `"fanout"` 键、`from_checkpoint` 缺键宽容还原（外层 key 能转 `int` 则转）⇒ **并让 `_restore_scheduler` 把 `restored.fanout` 回填到 `state.fanout`**（否则纯 fan-out 现场在恢复时丢失）⇒ FR-016 · SC-009 · F-3
- [X] T018 在 `src/freegraph/runtime/superstep.py` 的 `_suspend_metadata` 增 `"suspension_kind": str | None` 与 `"static_ack": {"channel_versions": dict} | None`；动态挂起传 `None`；既有 `next` / `interrupts` / `tasks` 不变、`scheduler` 的**既有键**不变（镜像见 T019）⇒ FR-007 · SC-011 · F-9
- [X] T019 在 `src/freegraph/runtime/superstep.py` 的 `_write_suspend` 增 `suspension_kind` / `static_ack` / `next_nodes` 参数（默认 `None` / 既有 produced 口径），把 kind/ack **镜像进** `scheduler` 子字典；静态挂起 **MUST NOT** 调 `put_writes("__interrupt__")` ⇒ FR-004 / FR-007 · SC-011 / SC-012 · F-9
- [X] T020 在 `src/freegraph/runtime/superstep.py` 的 `_first_graph` / `_resume_graph` 从 `history.scheduler` 读取 `suspension_kind` / `static_ack`；缺键 ⇒ `None`（旧快照宽容）⇒ FR-007 · SC-011
- [X] T021 在 `src/freegraph/runtime/superstep.py` 的 `_resume_graph` 加**早于 `per_node` 映射**的静态分支：`interrupts == ()` 且 kind 为静态值 ⇒ 不抛 `no_pending_interrupt`、忽略 resume 值、按 `snapshot.next` 继续，并**把 `history.scheduler` 的 `static_ack` 传给 `_run_graph_loop`**（否则静态 before 恢复首轮立即重挂）；非静态且无中断 ⇒ 既有 `no_pending_interrupt` 不变 ⇒ FR-007 · SC-012 · F-5
- [X] T022 在 `src/freegraph/runtime/superstep.py` 新增 `_clear_static_suspension(run_config, checkpointer, spec, state)`：**仅当本次运行为静态恢复**且返回 `SuperStepResult` ⇒ `checkpointer.put` 写完成快照（`next=()` / `interrupts=()` / `tasks=()` / `suspension_kind=None` / `static_ack=None` / `fanout={}`）⇒ **一次性完成写（F-10）**，**不是**每轮末快照；**普通（非静态）完成 MUST NOT 调用** ⇒ FR-007 · SC-011 · F-10 · data-model §2.4
- [X] T023 在 `tests/runtime/test_graph_spec_static.py` 写 `_static.py` 的纯函数用例：`"*"` 展开为**可执行节点** / 去重 / `["*"]` / 裸非 `"*"` 字符串（含空串 / 裸哨兵）/ `Mapping` / `set` / 非 `Sequence` / 空串元素 / 哨兵元素 / 未知节点 / `None` ⇒ FR-002 / FR-003 · SC-014
- [X] T024 在 `tests/runtime/test_graph_spec_static.py` 写 `GraphSpec` 构造期 V-22…V-25 用例（含 `"*"` All **可执行节点**展开断言；**裸空串 / 裸哨兵 ⇒ TypeError**；序列元素空串 ⇒ ValueError；`Mapping` / `set` ⇒ TypeError）+ **防御性拷贝**用例（构造后修改传入 list/tuple ⇒ `interrupt_before` / `interrupt_after` 逐字不变）⇒ FR-002 / FR-003 / FR-027 / FR-029 · SC-014 / SC-015
- [X] T025 在 `tests/runtime/test_graph_spec_static.py` 写 V-26 用例：`run_super_step` / `run_super_steps` 收到非空静态字段 ⇒ `ValueError`；签名 / 返回类型不变 ⇒ FR-017 · SC-015
- [X] T026 在 `tests/runtime/test_recursion_limit.py` 写 `_recursion.py` 的纯函数用例：默认 10007 / `resolve_config` 三形态 / 优先级 / `validate_limit` 的 `TypeError` / `ValueError` ⇒ FR-010 / FR-011 / FR-012 · SC-004 / SC-014
- [X] T027 在 `tests/runtime/test_interrupt_checkpoint.py` 增 `fanout` 账本 JSON 往返用例（空 `{}` / N=2 任务 / 缺键宽容 / TaskId 键还原）⇒ FR-016 · SC-009 · F-3
- [X] T028 在 `tests/runtime/test_interrupt_checkpoint.py` **直接调用** `_suspend_metadata` / `_write_suspend`（不经 `run_graph`）测 `suspension_kind` / `static_ack` 的 metadata 形状与 `scheduler` 镜像；静态 kind 时**无** `__interrupt__` put_writes（不依赖 US1/US2 行为）⇒ FR-007 · SC-011 / SC-012 · F-9
- [X] T029 在 `tests/runtime/test_graph_spec_static.py` 写 `run_super_step` / `run_super_steps` 的**签名与返回类型不变**断言（`inspect.signature`）⇒ FR-017 · SC-015
- [X] T030 跑门禁 `harness/scripts/gates/gate_G21_dependencies.py` / `gate_G25_import_graph.py` / `gate_G30_attribution.py`，确认零新依赖 / L2 目录条目内 / 署名头 ⇒ FR-019 · SC-019 / SC-024

**Checkpoint**: 共享接缝就绪 —— 用户故事可开工

---

## Phase 3: User Story 1 - 在指定节点前挂起（Priority: P1）

**Goal**: `interrupt_before` 命中 ⇒ **整轮不执行**、目标 0 次、状态不含本轮写入、挂起空载荷；
恢复后目标恰好执行一次且不立即重挂。

**Independent Test**: 一张 `__start__ → prepare → review → __end__` 的图 + `interrupt_before=("review",)`
⇒ `review` 执行 **0** 次；`paused.state` 只含 `prepare` 写入；`as_result_dict()["__interrupt__"] == ()`；
`run_graph(spec, None, ...)` 后 `review` 执行 **1** 次。

### Tests for User Story 1（MUST 先写 · MUST 先失败）

- [X] T031 [US1] 在 `tests/runtime/test_static_interrupt.py` 写 before 基本用例：目标执行 **0** 次、`InterruptResult`、状态不含目标写入 ⇒ FR-001 / FR-005 · SC-001
- [X] T032 [US1] 在 `tests/runtime/test_static_interrupt.py` 写 before + 前置节点用例：`prepare` 执行、`review` 未执行、`state` 只含 `prepare` 写入 ⇒ FR-005 · SC-001
- [X] T033 [US1] 在 `tests/runtime/test_static_interrupt.py` 写 before 恢复用例：`input=None` ⇒ 目标执行 **1** 次；立即恢复不重复挂起 ⇒ FR-007 / FR-008 · SC-011
- [X] T034 [US1] 在 `tests/runtime/test_static_interrupt.py` 写 before 目标是入口节点的用例：首轮挂起、`state` 只含输入写入 ⇒ FR-005 · SC-001
- [X] T035 [US1] 在 `tests/runtime/test_static_interrupt.py` 写结果键用例：`interrupts == ()`、`as_result_dict()["__interrupt__"] == ()`、`executed` 不含目标、`steps` 不含本轮 ⇒ FR-004 · SC-006
- [X] T036 [US1] 在 `src/freegraph/runtime/superstep.py` 的 `_run_graph_loop` 接入 before 检查：**递归检查之后、`_run_round` 之前**；**保持循环顶部 `steps += 1` 与空终轮口径不变**（B7F1 冻结面）；本轮任一标准 / fan-out 目标命中 ⇒ 整轮不执行 ⇒ FR-005 · SC-001 / SC-007
- [X] T037 [US1] 在 `src/freegraph/runtime/superstep.py` 构造 before 的 `InterruptResult`：`state=_sparse_state` / `interrupts=()` / `executed=累计` / `steps=已执行轮（= 循环 steps - 1；不含本轮）`；写 metadata（`suspension_kind="static_before"` / `next=标准待执行目标` / `static_ack=当前版本`）；**不消费触发源 / 不合并写入 / 不推进 `state.step`** ⇒ FR-004 / FR-005 · SC-001 / SC-007
- [X] T038 [US1] 在 `src/freegraph/runtime/superstep.py` 接入 before 的 ack 检查（`static_allowed`）：恢复后无新写入 ⇒ 同一断点不立即重挂；恢复后写入**新通道** ⇒ 允许再次触发（并集比较，不得只遍历旧 ack 键）⇒ FR-008 · SC-011
- [X] T039 [US1] 在 `src/freegraph/runtime/superstep.py` 的 `_first_graph` 接**静态 before / after** 的 `input=None` 恢复：`first_round = snapshot.next`（标准目标；fan-out 由账本另存），**两类静态挂起都传 `static_ack`** 继续（after 若下一轮命中同一目标且无新写入，ack 必须抑制重挂）；**空 StateDict `input={}` 同款视为无新输入并传 `static_ack`** ⇒ FR-007 / FR-008 · SC-011
- [X] T040 [US1] 在 `tests/runtime/test_static_interrupt.py` 写「before 不消费触发源版本 / 不合并写入」的副作用断言（通道版本与状态逐字不变）⇒ FR-005 · SC-001 / SC-007
- [X] T041 [US1] 在 `tests/runtime/test_static_interrupt.py` 写口径断言：**before 轮不计入 `InterruptResult.steps`**；**空终轮不计入 `recursion_limit`**；**`SuperStepResult.steps` 口径不变**（仍含空终轮，B7F1 冻结）⇒ FR-013 · SC-007

**Checkpoint**: US1 可独立验收（静态 before）

---

## Phase 4: User Story 2 - 在指定节点后挂起（Priority: P1）

**Goal**: `interrupt_after` 命中 ⇒ 目标执行一次、写入已合并、随后挂起；恢复不重跑；
最后节点 `next==()` 仍可恢复。

**Independent Test**: 同一张图 + `interrupt_after=("review",)` ⇒ `review` 执行 **1** 次；
`paused.state` 含 `review` 写入；恢复后不重跑；`review` 为最后节点时恢复直接完成。

### Tests for User Story 2（MUST 先写 · MUST 先失败）

- [X] T042 [US2] 在 `tests/runtime/test_static_interrupt.py` 写 after 基本用例：目标执行 **1** 次、状态含写入、`InterruptResult` ⇒ FR-001 / FR-006 · SC-002
- [X] T043 [US2] 在 `tests/runtime/test_static_interrupt.py` 写 after + 最后节点用例：`next==()` 仍返回挂起态；恢复后完成、不重跑 ⇒ FR-006 / FR-007 · SC-002 / SC-011
- [X] T044 [US2] 在 `tests/runtime/test_static_interrupt.py` 写 after 恢复用例：`input=None` ⇒ 不重跑目标、后续节点照常；**恢复后下一轮无新写入时不得再次命中 after**（验证 ack 已传入）；补**空 StateDict `input={}` 与 `input=None` 同款不重挂**用例 ⇒ FR-006 / FR-007 / FR-008 · SC-002 / SC-011
- [X] T045 [US2] 在 `tests/runtime/test_static_interrupt.py` 写 after 的 `executed` / `steps` 口径：目标出现、本轮计入；**fan-out N 次时目标名出现 N 次**且顺序符合「标准任务按节点名序 · fan-out 按 TaskId 序」⇒ FR-004 / FR-006 · SC-002
- [X] T046 [US2] 在 `tests/runtime/test_static_interrupt.py` 写 after 结果键：`interrupts == ()`、`as_result_dict()["__interrupt__"] == ()` ⇒ FR-004 · SC-006
- [X] T047 [US2] 在 `src/freegraph/runtime/superstep.py` 接入 after 检查：`_run_round` 成功 + `state.step += 1` 之后；本轮 `round_executed` 命中 ⇒ 挂起；**并接入 `static_allowed(ack, state)`（after 的 ack；与 T038 的 before 同款，MUST NOT 只接 before）** ⇒ FR-006 / FR-008 · SC-002 / SC-011
- [X] T048 [US2] 在 `src/freegraph/runtime/superstep.py` 计算 after 的 `next = _determine_triggers(spec, state)`（标准下一轮；可空），写 metadata `suspension_kind="static_after"` / `static_ack=当前版本`；不把刚执行目标列入 `next` ⇒ FR-006 / FR-007 · SC-002 / SC-011
- [X] T049 [US2] 在 `src/freegraph/runtime/superstep.py` 接入完成清标记（`_clear_static_suspension`）：**仅静态恢复完成** ⇒ 清 `suspension_kind` / `static_ack` / `next`（一次性完成写 · F-10）；**普通完成 MUST NOT 调用** ⇒ FR-007 · SC-011 · F-10
- [X] T050 [US2] 在 `src/freegraph/runtime/superstep.py` 的 `_resume_graph` 接静态 after 的 `Command(resume=...)` 分支：值不投递、继续执行；**并把 `history.scheduler` 的 `static_ack` 传给 `_run_graph_loop`**（`interrupt_before` 同样适用，MUST NOT 只在 after 生效）；**`Command(resume=...)` 路径未挂 checkpointer 时必须抛 `checkpointer_required`**；补 `input=None` 且无 checkpointer ⇒ **不**声称恢复（视为新运行）的用例 ⇒ FR-007 · SC-012
- [X] T051 [US2] 在 `tests/runtime/test_static_interrupt.py` 写「恢复完成后再次 `input=None` ⇒ 不重跑」用例（验证 marker 已清；覆盖 F-10 完成快照）；**并写反向用例：普通（非静态）完成 MUST NOT 写静态完成快照 / 不调用 `_clear_static_suspension`** ⇒ FR-007 · SC-011 / SC-012 · F-10
- [X] T052 [US2] 在 `tests/runtime/test_static_interrupt.py` 写静态 after 的 `next` 为空 / 非空的 metadata 形状断言；**非自环场景断言 `next` 不含刚执行的 after 目标**，自环场景另立对照；**并写 F-5 的反向边界用例**：非静态 + `next` 非空 + 无动态中断 ⇒ 仍抛 `no_pending_interrupt`（不得因 `next` 非空而放行）；**并写「静态 `interrupt_before` + `Command(resume=...)` 恢复首轮不立即重挂」用例（验证 `_resume_graph` 已传 `static_ack`）** ⇒ FR-007 / FR-008 · SC-012

**Checkpoint**: US1 + US2 可独立验收

---

## Phase 5: User Story 3 - 死循环被明确拦住（Priority: P1）

**Goal**: 自环图 + `recursion_limit=3` ⇒ `GraphRecursionError`；按 super-step 轮次计；
fan-out 轮计入；错误结构化且不被包装。

**Independent Test**: 自环图 + `{"recursion_limit": 3}` ⇒ `GraphRecursionError`；
`.recursion_limit == 3`；消息含超限语义；每轮 2 节点的图只执行 3 轮。

### Tests for User Story 3（MUST 先写 · MUST 先失败）

- [X] T053 [US3] 在 `tests/runtime/test_recursion_limit.py` 写自环 + `limit=3` 用例：抛 `GraphRecursionError`（不是 `RecursionError` / 挂起 / 静默）⇒ FR-014 · SC-003
- [X] T054 [US3] 在 `tests/runtime/test_recursion_limit.py` 写错误结构化用例：`.recursion_limit == 3`、`.current_step` 如实、消息含两个数值 ⇒ FR-014 / FR-027 · SC-003 / SC-013
- [X] T055 [US3] 在 `tests/runtime/test_recursion_limit.py` 写「每轮 2 节点 + 上限 3 ⇒ 只执行 3 轮（不是 3 次节点调用）」用例 ⇒ FR-013 · SC-007
- [X] T056 [US3] 在 `tests/runtime/test_recursion_limit.py` 写「空终轮不计 / before 未执行轮不计 / after 轮计入 / **静态挂起恢复后从新预算开始（每次 `run_graph` 独立计数）**」用例 ⇒ FR-013 · SC-007
- [X] T057 [US3] 在 `tests/runtime/test_recursion_limit.py` 写「fan-out 轮计入上限、不绕过」用例（**B11F1 的** D-2）⇒ FR-013 / FR-015 · SC-008
- [X] T058 [US3] 在 `src/freegraph/runtime/superstep.py` 的 `_run_graph_loop` 使用 `effective_limit`（`state.step >= effective_limit` ⇒ `GraphRecursionError(recursion_limit=effective_limit, current_step=state.step)`）⇒ FR-013 / FR-014 · SC-003 / SC-007
- [X] T059 [US3] 在 `tests/runtime/test_recursion_limit.py` 写「`GraphRecursionError` 原样传播（不被包装）」用例 ⇒ FR-014 · SC-013
- [X] T060 [US3] 在 `tests/runtime/test_recursion_limit.py` 写边界用例：`limit=1` 恰好执行 1 轮后超限；`limit=2` 等 ⇒ FR-013 · SC-007

**Checkpoint**: US3 可独立验收（A1）

---

## Phase 6: User Story 4 - 载体形态锁定为普通 dict（Priority: P2）

**Goal**: **L2 `run_graph`** 的 dict 载体生效；`RunConfig` 是**互斥替代载体**；dict 与
`max_steps` 同时给时 dict 优先；未知键忽略；**不存在** `recursion_limit=` 关键字。
⚠️ 对外 `invoke(input, config)` 的同款载体透传由 **B7F3（M2）· D-3** 收口，不在本故事范围。

**Independent Test**: dict / `RunConfig` 各跑一次自环图 ⇒ 都抛 `GraphRecursionError`；
二者是互斥载体（不同时提供）；dict 与 `max_steps` 同时给 ⇒ dict 优先。

### Tests for User Story 4

- [X] T061 [US4] 在 `tests/runtime/test_recursion_limit.py` 写 dict 载体用例：`config={"recursion_limit": 3}` ⇒ 生效 ⇒ FR-010 · SC-006
- [X] T062 [US4] 在 `tests/runtime/test_recursion_limit.py` 写 `RunConfig(recursion_limit=3)` 用例 ⇒ 生效；并带 `max_steps=100` 断言 `.recursion_limit == 3`（`RunConfig` 优先于 `max_steps`）⇒ FR-010 · SC-006
- [X] T063 [US4] 在 `tests/runtime/test_recursion_limit.py` 写优先级用例：dict 的 3 vs `max_steps=100` ⇒ 以 3 为准 ⇒ FR-010 · SC-006
- [X] T064 [US4] 在 `tests/runtime/test_recursion_limit.py` 写未知键忽略 + `configurable.thread_id` 保留用例（checkpointer 仍取到会话）⇒ FR-010 / FR-028 · SC-006
- [X] T065 [US4] 在 `tests/runtime/test_recursion_limit.py` 写 `inspect.signature(run_graph)` **不含** `recursion_limit` 关键字；`config` 注解接受 `Mapping`；并断言 dict / `RunConfig` 是**互斥**载体（不存在同时提供两者的入口）；**`invoke` 的同款载体透传由 B7F3（D-3）收口**，本任务只判 `run_graph` ⇒ FR-010 · SC-006
- [X] T066 [US4] 在 `src/freegraph/runtime/superstep.py` 核验 / 补齐 `run_graph` 的 config 归一与优先级（若 T015 已落地 ⇒ 只核验 + 补注释）⇒ FR-010 · SC-006

**Checkpoint**: US4 可独立验收

---

## Phase 7: User Story 5 - 默认上限有明确取值（Priority: P2）

**Goal**: 未设置上限 ⇒ **10007**；零环境变量；非法值入口失败。

**Independent Test**: 断言 `DEFAULT_RECURSION_LIMIT == 10007`；设置
`LANGGRAPH_DEFAULT_RECURSION_LIMIT=1` 行为不变；`0` / 负数 / 非 int / bool / 浮点失败。

### Tests for User Story 5

- [X] T067 [US5] 在 `tests/runtime/test_recursion_limit.py` 写默认值用例：未设置 ⇒ 有效上限 **10007**（直接断言常量 + 跑 >25 轮不误报）⇒ FR-011 · SC-004
- [X] T068 [US5] 在 `tests/runtime/test_recursion_limit.py` 写零 env 用例：`monkeypatch.setenv("LANGGRAPH_DEFAULT_RECURSION_LIMIT", "1")` ⇒ 行为逐字不变 ⇒ FR-011 · SC-004
- [X] T069 [US5] 在 `tests/runtime/test_recursion_limit.py` 写非法值用例：`0` / `-1` ⇒ `ValueError`；`True` / `1.5` / `"3"` ⇒ `TypeError` ⇒ FR-012 · SC-004 / SC-014
- [X] T070 [US5] 在 `tests/runtime/test_recursion_limit.py` 写 `recursion_limit=None` 落回 `max_steps` / 默认值用例；**明确 `None` 不进入 `TypeError` 校验**（FR-012 的 `None` 例外）⇒ FR-010 / FR-012 · SC-004
- [X] T071 [US5] 在 `tests/runtime/test_recursion_limit.py` 写静态扫描：`_recursion.py` / `superstep.py` 不出现 `os.environ` / `getenv` / `LANGGRAPH_DEFAULT_RECURSION_LIMIT` 读取 ⇒ FR-019 · SC-018
- [X] T072 [US5] 在 `src/freegraph/runtime/_recursion.py` / `run_graph` docstring 写死默认 **10007** 与「零环境变量」说明 ⇒ FR-011 · SC-004

**Checkpoint**: US5 可独立验收

---

## Phase 8: User Story 6 - 静态断点与 fan-out 的交互可判定（Priority: P2）

**Goal**: fan-out 的 N 个任务各自独立命中 before / after；before 全保留、after 各一次；
`next==()` 仍可恢复；不合并、不伪造载荷。

**Independent Test**: `Command(goto=[Send("w",{"n":1}), Send("w",{"n":2})])` +
`interrupt_before=("w",)` ⇒ `w` 0 次、两个任务保留；`interrupt_after` ⇒ 2 次；
恢复后恰好两个任务、入参逐字不变。

### Tests for User Story 6

- [X] T073 [US6] 在 `tests/runtime/test_static_interrupt_fanout.py` 写 before N=2 用例：`w` 执行 **0** 次、两个任务都保留 ⇒ FR-015 · SC-009
- [X] T074 [US6] 在 `tests/runtime/test_static_interrupt_fanout.py` 写 after N=2 用例：`w` 执行 **2** 次（各一次）、随后挂起；**`paused.executed.count("w") == 2`** 且顺序按 TaskId ⇒ FR-015 · SC-009
- [X] T075 [US6] 在 `tests/runtime/test_static_interrupt_fanout.py` 写恢复用例：恰好两个任务、TaskId 序、入参逐字不变 ⇒ FR-016 · SC-009 / SC-011
- [X] T076 [US6] 在 `tests/runtime/test_static_interrupt_fanout.py` 写 `next==()` 子场景：纯 fan-out before / 最后节点 after 都能恢复 ⇒ FR-007 · SC-009 / SC-012
- [X] T077 [US6] 在 `tests/runtime/test_static_interrupt_fanout.py` 写「静态挂起不伪造 N 个 `Interrupt`」：`interrupts == ()` ⇒ FR-004 / FR-015 · SC-009
- [X] T078 [US6] 在 `src/freegraph/runtime/superstep.py` 的 **before** 命中判定中纳入 `state.fanout` 的任务目标；**after 只使用本轮 `round_executed`**（MUST NOT 纳入 `state.fanout`）⇒ FR-006 / FR-015 · SC-009
- [X] T079 [US6] 在 `src/freegraph/runtime/superstep.py` / `_fanout.py` 接入 fan-out 账本跨静态挂起保留（编码 / 解码 / **`_restore_scheduler` 回填 `state.fanout`** / 恢复后重试）；用 T076 的纯 fan-out before 用例验证账本未丢失 ⇒ FR-016 · SC-009
- [X] T080 [US6] 在 `src/freegraph/runtime/superstep.py` 确保静态 after 的 `next` 只放标准下一轮触发节点；fan-out 任务由账本单独恢复（不混入 `first_round`）⇒ FR-007 / FR-016 · SC-009
- [X] T081 [US6] 在 `tests/runtime/test_static_interrupt_fanout.py` 写「同轮标准任务 + fan-out 任务，before ⇒ 整轮不执行」用例 ⇒ FR-005 / FR-015 · SC-009
- [X] T082 [US6] 在 `tests/runtime/test_static_interrupt_fanout.py` 写「after + fan-out 产出下一轮任务」用例（写合并后挂起，恢复先跑 fan-out）⇒ FR-006 / FR-016 · SC-009

**Checkpoint**: US6 可独立验收（**B11F1 的** D-2 / D-7）

---

## Phase 9: User Story 7 - 动态与静态中断可共存且优先级确定（Priority: P2）

**Goal**: 真异常 > 动态中断 > 静态 after > 完成；递归超限 > 静态 before；before > after。

**Independent Test**: 节点抛真异常 + `interrupt_after` ⇒ 原异常；节点 `interrupt()` + after ⇒
动态载荷；同节点 before+after ⇒ before 先挂起、恢复后 after。

### Tests for User Story 7

- [X] T083 [US7] 在 `tests/runtime/test_static_interrupt.py` 写「真异常 > 静态 after」用例 ⇒ FR-009 · SC-010
- [X] T084 [US7] 在 `tests/runtime/test_static_interrupt.py` 写「动态中断 > 静态 after」用例（载荷 = 动态元组，不是空元组）⇒ FR-009 · SC-010
- [X] T085 [US7] 在 `tests/runtime/test_static_interrupt.py` 写「同一节点 before + after ⇒ before → 恢复 → 执行 → after」用例 ⇒ FR-009 · SC-010
- [X] T086 [US7] 在 `tests/runtime/test_static_interrupt.py` 写「递归超限 > 静态 before」用例 ⇒ FR-009 · SC-010
- [X] T087 [US7] 在 `src/freegraph/runtime/superstep.py` 核验优先级实现：after 只在 `_run_round` 成功（无真异常 / 无动态中断）后判定；before 在递归检查之后 ⇒ FR-009 · SC-010
- [X] T088 [US7] 在 `tests/runtime/test_static_interrupt.py` 写「静态 after 不吞掉动态载荷」断言（动态 `interrupts` 逐字保留）⇒ FR-009 · SC-010
- [X] T089 [US7] 在 `tests/runtime/test_static_interrupt.py` 写「真异常不被静态 after 包装」断言（类型 / 消息逐字）⇒ FR-009 · SC-010

**Checkpoint**: US7 可独立验收

---

## Phase 10: User Story 8 - 未配置静态断点时行为完全不变（Priority: P3）

**Goal**: 既有 B7F1 / B9F1 / B10F1 / B11F1 / B12F1 零回归；`GraphSpec` 旧写法零改动；
低层入口显式拒绝；签名 / 返回类型 / 字段数不变。

**Independent Test**: 既有套件一条不改全绿；旧 `GraphSpec(...)` 构造 / 运行逐字相同；
`run_super_step` / `run_super_steps` 签名不变；低层入口非空静态字段 ⇒ `ValueError`。

### Tests for User Story 8

- [X] T090 [US8] 跑既有套件（`tests/` 全量 · `.venv/bin/python -m pytest -q`）确认**一条不改**全绿（基线 1203 + 新增）⇒ FR-017 · SC-015
- [X] T091 [US8] 在 `tests/runtime/test_graph_spec_static.py` 写旧 `GraphSpec(channels, nodes, edges)` 构造 / 运行逐字不变用例 ⇒ FR-017 / FR-029 · SC-015
- [X] T092 [US8] 核验 T025 的 V-26 用例覆盖 `run_super_step` / `run_super_steps` **两个入口** + 消息说明；缺项则补齐 `tests/runtime/test_graph_spec_static.py` ⇒ FR-017 · SC-015
- [X] T093 [US8] 核验 T029 的 `run_super_step` / `run_super_steps` 签名 / 返回类型断言 + 既有 `tests/runtime/test_superstep_concurrency.py` 的入口签名断言仍绿 ⇒ FR-017 · SC-015
- [X] T094 [US8] 核验 `tests/runtime/test_interrupt_contract.py` 的 `InterruptResult` 4 字段 / `SuperStepResult` 4 字段既有断言仍绿（不新增重复用例）⇒ FR-004 / FR-018 · SC-015 / SC-016
- [X] T095 [US8] 核验 `harness/demo/target.py` 与入库基准逐字相同（`git diff` 空）⇒ FR-026 · SC-020
- [X] T096 [US8] 核验 `src/freegraph/contracts/__init__.py` 的 L1 符号面仍 **21** / `src/freegraph/graph.py` 门面仍 **7** / `src/freegraph/runtime/__init__.py` 的 `__all__` 仍 **23**（零新增导出）⇒ FR-018 / FR-030 · SC-016 / SC-019
- [X] T097 [US8] 更新 `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §5 与 `spec.md`：只增 **V-26** + 「低层入口收到非空静态字段 ⇒ 显式拒绝」说明（F-8）⇒ FR-017 · SC-015

**Checkpoint**: 全部用户故事可独立验收

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: 验收脚本 / 差分 / 回溯修订 / 下游接线 / 人工验证 / 全量回归

### 验收脚本与差分

- [X] T098 [P] 在 `harness/demo/graph_core.py` 的 `case_recursion_limit` 把 `soft(...)` 改为 `check(...)`，从 **`freegraph.contracts`** 导入 `GraphRecursionError`（门面 `freegraph.graph` 保持 **7** 符号，MUST NOT 从门面导入），精确捕获该类型（其它异常 ⇒ `check(False)`）；保留既有自环图形态（F-6）；**M1 的「门面未就绪」由 T102 的守卫负责以退出码 2 结束，不计入硬断言失败** ⇒ FR-021 / FR-023 · SC-005
- [X] T099 [P] 在 `harness/demo/README.md` 的软断言清单删除 `recursion_limit` 一行（保留 C25 一行与规则文字；「当前两处」→「当前一处」）（F-7）⇒ FR-032 · SC-005
- [X] T100 在 `tests/runtime/test_recursion_limit.py` 写与 `graph_core` **同调用形态**的 L2 硬测试：`run_graph(..., config={"recursion_limit": 3})` ⇒ `GraphRecursionError`（当下真跑通过）⇒ FR-022 · SC-005
- [X] T101 [P] 在 `tests/differential/parity_probe.py` 追加 **D-38…D-49**（逐条带判词；复用既有 Scenario 形状）⇒ FR-024 · SC-022
- [X] T102 在 `tests/differential/` 核验上游缺席 ⇒ **skip**（不判失败）；在 `harness/demo/graph_core.py` 的 `main()` **进入用例循环之前**增加**门面未就绪守卫**：`compile()` / `invoke()` 为桩（`NotImplementedError` / 未实现）时打印 `[环境未就绪]` 并以**退出码 2** 结束，**不进入硬断言失败统计**（退出码 1 仅留给真实 FAIL）；**实跑 `graph_core.py` 断言退出码 == 2**；不写永久红 ⇒ FR-023 / FR-024 · SC-005 / SC-022 / SC-024

### 回溯修订 / 下游接线 / 人工验证

- [X] T103 [P] 补齐 `harness/verification/B13F1/manual-verification.md`：五段式 + **来源覆盖表**（A1–A3 + SC + FR + X-1 / X-2 / X-6 / X-8）+ **EV-1** 延期（graph_core 端到端 → B7F3）+ **追认文字**（**F-1…F-10 + X-1 / X-2 / X-6 / X-8**）⇒ FR-023 / FR-025 · SC-005 / SC-021
- [X] T104 [P] 更新 **B10F1 的两个契约文件与 spec**（**拆分而不删**）：`checkpoint-contract.md` §3 / §4 只增 `fanout` / `suspension_kind` / `static_ack` / scheduler 镜像 + **静态恢复完成快照**（F-3 / F-9 / F-10）；`interrupt-resume-contract.md` **§2 放宽 `run_graph.config` 注解为 `RunConfig | Mapping[str, Any] | None`（F-4）**、§6.2 只增静态恢复分支（F-5）；`spec.md` 的 **裁定 4 / 9 / 10** 同步（F-3 / F-4 / F-5 / F-9 / F-10）；**并更新 B11F1 的冻结面**：`contracts/send-contract.md` §5.1、`data-model.md` I-12、`tasks.md` T019、`plan.md` PR-8、`research.md` DR-02 / D-08、`quickstart.md` DR-02、`spec.md` D-3（「`fanout` 不落盘」⇒ 自 B13F1 起落盘；**拆分而不删**；`spec.md` F-14 仅顺序口径说明，不属落盘修订）⇒ FR-007 / FR-016 · SC-011 · F-3 / F-10
- [X] T105 更新 `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §2 / §2.1.1 与 `spec.md`：只增 `GraphSpec` 字段 / V-22…V-25（F-1 / F-2；拆分而不删；V-26/F-8 由 T097 负责）；⚠️ 与 T097 共用同一对文件 ⇒ **MUST 串行（T097 → T105）** ⇒ FR-002 / FR-003 · SC-014
- [X] T106 按 plan「Downstream Wiring」逐条接线 **D-1…D-8**（`harness/features/B7F2_compile编译.md` · `harness/features/B7F3_invoke返回完整状态.md` · `harness/features/B14F1_Checkpointer协议与MemorySaver.md` · `harness/features/B15F1_SqliteSaver与状态历史.md` · `harness/features/B16F1_update_state与时间旅行.md` · `harness/features/B6F1_StateGraph构建器.md` · `harness/features/B24F1_打包分发与兼容矩阵.md`）⇒ 只接线 · 逐条最小改动 ⇒ FR-023 / FR-026 · SC-020 / SC-024
- [X] T107 逐条核验 **F-1…F-10** 的落地与「只增不删」：`src/freegraph/runtime/superstep.py` 的 `GraphSpec` 字段 / V-22…V-25 / `fanout` 键 / `run_graph` 注解 / 静态恢复 / **完成快照** · `harness/demo/graph_core.py` / `harness/demo/README.md` · `specs/b7f1-superstep-loop/contracts/superstep-contract.md` · `specs/b10f1-interrupt-resume/{spec.md,contracts/}` · metadata ⇒ FR-018 · SC-016
- [X] T108 全量回归：`tests/` 全量 `.venv/bin/python -m pytest -q`（既有 1203 + 新增全绿）⇒ FR-017 / FR-019 · SC-015 / SC-024
- [X] T109 覆盖率：`coverage run -m pytest -q` + `coverage report --fail-under=100 --include="src/freegraph/runtime/_static.py,src/freegraph/runtime/_recursion.py,src/freegraph/runtime/_fanout.py"`；`superstep.py` 的新增/变更行 MUST 纳入 **diff 覆盖率**（`coverage json` 与 `git diff -U0` 行号交集）⇒ FR-031 · SC-023
- [X] T110 跑门禁：`gate_G21_dependencies.py` / `gate_G25_import_graph.py` / `gate_G29_contract_carrier.py` / `gate_G30_attribution.py`；确认 G1–G30 连续、依赖 / 导入 / 署名头 / 零出站恒绿 ⇒ FR-019 · SC-018 / SC-019 / SC-024
- [X] T111 在 `tests/runtime/test_recursion_limit.py` / `test_static_interrupt.py` 写确定性用例：同一规格重复 **≥3** 次 ⇒ 最终状态 / 执行序列 / 挂起 / 超限判定逐项相等 ⇒ FR-020 · SC-017
- [X] T112 按 `quickstart.md` 逐场景跑一遍（§1–§10）并把实际输出填入人工验证记录；**一键验收入口** = `harness/verification/B13F1/acceptance.py`（V1–V10 · 37 条断言 PASS）⇒ FR-025 · SC-021
- [X] T113 核验 `README.md` 的 API 兼容矩阵**零新增行** / `THIRD_PARTY_NOTICES` 差异 == 0 / `harness/reports/Q8-图运行时最小契约.md` §3.4 契约条目仍 **C1–C27（27 条）** / `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 门禁编号仍 G1–G30；并用 `git diff --name-only` 断言变更仅限预期文件（`src/freegraph/runtime/{superstep.py,_static.py,_recursion.py,_fanout.py}` · `tests/` · `harness/demo/graph_core.py` · `harness/demo/README.md` · `harness/verification/B13F1/` · `harness/features/` · `harness/prompts/` · `harness/proposals/立项书.md` · `specs/b13f1-static-interrupt-recursion-limit/` · `specs/b10f1-interrupt-resume/spec.md` · `specs/b10f1-interrupt-resume/contracts/` · `specs/b7f1-superstep-loop/contracts/` · `specs/b7f1-superstep-loop/spec.md` · **`specs/b11f1-send-fanout/contracts/send-contract.md`** · **`specs/b11f1-send-fanout/data-model.md`** · **`specs/b11f1-send-fanout/tasks.md`** · **`specs/b11f1-send-fanout/plan.md`** · **`specs/b11f1-send-fanout/research.md`** · **`specs/b11f1-send-fanout/quickstart.md`** · **`specs/b11f1-send-fanout/spec.md`**；**`harness/demo/target.py` 必须在预期集之外且零 diff**；**越界实现数 == 0**）⇒ FR-018 / FR-026 / FR-030 · SC-016 / SC-020
- [X] T114 发起者追认（2026-11-15）：在 `harness/verification/B13F1/manual-verification.md` 落 **F-1…F-10** 与 **X-1 / X-2 / X-6 / X-8** 的追认文字 + **EV-1** 的具名延期确认（已追认）⇒ FR-023 / FR-025 · SC-005 / SC-021 / SC-024
- [X] T115 最终一致性复核：`spec.md` / `plan.md` / `research.md` / `data-model.md` / `contracts/` 的裁定编号（已为 **1–14**）/ P 编号（**P-01…P-20**）/ F 编号 / **下游承接 D-1…D-8** / **设计决策 D-01…D-14** / **差分场景 D-38…D-49** / **EV-1** / 外部编号限定词（**B11F1 的 D-2 / D-7**）/ 行号逐项一致；**F-3 的 B11F1 冻结面拆分（`send-contract.md` §5.1 / `data-model.md` I-12 / `tasks.md` T019 / `plan.md` PR-8 / `research.md` DR-02 / D-08 / `quickstart.md` DR-02 / `spec.md` D-3）逐条核对**；如发现漂移只做**事实性**修正 ⇒ FR-024 · SC-022

---

## Dependencies & Execution Order

### 执行闸口（每道 MUST 全绿才进下一 Phase）

| 闸口 | 条件 |
|---|---|
| **G-A** | Phase 1 完成：基线 1203/4 + 骨架文件可导入 |
| **G-B** | Phase 2 完成：`_static.py` / `_recursion.py` 纯函数 + `GraphSpec` V-22…V-26 + metadata / fanout 接缝 + 单测全绿 |
| **G-C** | US1 / US2 完成：before / after 独立可验收 |
| **G-D** | US3 / US4 / US5 完成：递归上限 / 载体 / 默认值可验收 |
| **G-E** | US6 / US7 完成：fan-out × 静态断点 / 优先级可验收 |
| **G-F** | US8 完成：零回归 + 低层拒绝 |
| **G-G** | Phase 11 完成：验收脚本 / 差分 / 人工验证 / 全量回归 / 覆盖率全绿 |

### Phase Dependencies

- **Phase 1**：无依赖，立即开始。
- **Phase 2**：依赖 Phase 1；**阻塞所有用户故事**。
- **Phase 3–10**：依赖 Phase 2；按优先级 P1 → P2 → P3 推进。
- **Phase 11**：依赖全部用户故事完成；但 T098 / T099 可在 US3 完成后提前起草（**MUST 在 Phase 11 收口**）。

### User Story Dependencies

| 故事 | 依赖 | 说明 |
|---|---|---|
| **US1 (P1)** | Phase 2 | 独立可验收（静态 before） |
| **US2 (P1)** | Phase 2 | 与 US1 共用 `superstep.py` ⇒ 实现 MUST 串行；测试可独立 |
| **US3 (P1)** | Phase 2 | 独立可验收（A1） |
| **US4 (P2)** | US3 | 载体测试需要递归超限行为 |
| **US5 (P2)** | US3 | 默认 / 校验测试需要有效上限 |
| **US6 (P2)** | US1 / US2 | 静态断点行为 + fanout 账本 |
| **US7 (P2)** | US1 / US2 / US3 | 优先级覆盖静态 / 动态 / 递归 |
| **US8 (P3)** | 全部前置 | 零回归 + 低层拒绝 |

### Within Each User Story

- 测试 MUST 先写并确认**失败**；
- 纯函数 / 模型 → 运行期接线 → 集成；
- 同一文件（`superstep.py` / `test_static_interrupt.py` / `test_recursion_limit.py`）的任务 **MUST 串行**；
- 故事完成后再进入下一优先级（除非明确并行）。

### Parallel Opportunities

- **Phase 1**：T002 / T003 / T004 / T005 / T006 / T007 可分头起草（不同文件）。
- **Phase 2**：T009 / T014 / T016 可并行（不同文件，已标 `[P]`）；T023 / T026 **在 T009 / T014 之后**起草（测试文件不同，但依赖被测接口）；T009 → T010（`_static.py` 同文件）串行；`superstep.py` 的任务串行。
- **Phase 3–10**：
  - `test_static_interrupt.py` 与 `test_static_interrupt_fanout.py` 可分头起草（不同文件），但后者依赖前者行为；
  - `test_recursion_limit.py` 与 `test_graph_spec_static.py` 可并行（不同文件）；
  - `superstep.py` 的实现任务 **MUST 串行**。
- **Phase 11**：T101（差分）/ T103（人工记录）/ T104 / T105（契约文档；**T105 必须在 T097 之后**）可并行；`T098` / `T099` 可与 T101 并行。

---

## Parallel Example: Phase 2（纯函数 / 测试骨架）

```bash
# 可并行（不同文件，已标 [P]）：
Task: "T009 _static.py 常量 + normalize_static_points"
Task: "T014 _recursion.py 默认值 / 解析 / 校验"
Task: "T016 _fanout.py fanout 账本编解码"

# 在 T009 / T014 之后起草（测试文件不同，但依赖被测接口）：
Task: "T023 test_graph_spec_static.py 的 _static.py 纯函数用例"
Task: "T026 test_recursion_limit.py 的 _recursion.py 纯函数用例"

# 必须串行（同一文件 _static.py）：
Task: "T009 normalize → T010 static_hit / static_allowed / build_static_ack"

# 必须串行（同一文件 superstep.py）：
Task: "T011 GraphSpec 字段 → T012 V-22…V-25 → T013 V-26 → T015 run_graph 解析 → T017 fanout 账本 → T018/T019 metadata → T020/T021 恢复 → T022 清标记"
```

## Parallel Example: Phase 8（fan-out × 静态断点）

```bash
# 先写测试（同一文件 ⇒ 串行起草；合入前 MUST 串行跑）：
Task: "T073 before N=2 → T074 after N=2 → T075 恢复 → T076 next==() → T077 空载荷"

# 实现（superstep.py ⇒ 串行）：
Task: "T078 before 纳入 fanout / after 用 round_executed → T079 账本保留 → T080 next 口径"
```

---

## Implementation Strategy

### MVP First（US1 + US2 + US3）

本 feature 的「最小可用」= **静态 before / after + 递归超限**：
1. Phase 1 + Phase 2；
2. US1（before）→ US2（after）→ US3（递归超限）；
3. **STOP & VALIDATE**：两条判据 A1 / A2 独立通过（`quickstart.md` §1–§3）；A3 的端到端真跑按 **EV-1** 由 B7F3 收口。

> 虽然 spec 的 MVP 判据是 **A1**（递归超限），但 US1 / US2 是同一「静态断点」功能的
> 两个 P1 面；建议一起收口，再做 US4 / US5。

### Incremental Delivery

1. Phase 1 + 2 → 骨架 / 校验 / 纯函数就绪；
2. US1 + US2 → 静态中断点可演示；
3. US3 → 递归超限可演示；
4. US4 + US5 → 载体 / 默认值可演示；
5. US6 + US7 → fan-out / 优先级可演示；
6. US8 → 零回归；
7. Phase 11 → 验收 / 差分 / 人工 / 全量回归收口。

### Parallel Team Strategy

- 1 人：严格按 Phase / Task 顺序；`superstep.py` 的任务串行。
- 2 人：
  - A：Phase 2 的 `_static.py` / `GraphSpec` / before / after；
  - B：Phase 2 的 `_recursion.py` / 递归上限 / 载体 / 默认值；
  - 合并点：`superstep.py` 的 `_run_graph_loop` 改动 MUST 由一人收口。
- 3 人：
  - A：静态 before / after + 恢复；
  - B：递归上限 + 载体 + 默认值；
  - C：fan-out × 静态 / 优先级 / 差分 / 人工验证。
  - 合并前 MUST 跑 G-G 全量闸口。

---

## Notes

- `[P]` = 不同文件、无未完成依赖；**同一文件的任务一律不标 `[P]`**（避免冲突）。
- 每个用户故事 MUST 可独立验收；测试 MUST 先写并确认失败。
- `superstep.py` 是本 feature 的**单点写入面** ⇒ 实现任务 MUST 串行。
- 不修改 `harness/demo/target.py` / L1 / 门面 / 构建器 / `compile()` / `invoke()`。
- 差分上游缺席 ⇒ **skip**；`graph_core` 端到端延期 ⇒ **EV-1**（B7F3）。
- 未追认 **F-1…F-10** 与 **X-1 / X-2 / X-6 / X-8** 前 MUST NOT 合入。

---

## 附录 · 任务 ↔ spec 追溯表

### FR → 任务

| FR | 任务 |
|---|---|
| FR-001 | T006 · T031 · T042 |
| FR-002 | T002 · T009 · T011 · T023 · T024 · T105 |
| FR-003 | T004 · T009 · T012 · T023 · T024 · T105 |
| FR-004 | T019 · T035 · T037 · T045 · T046 · T077 · T094 |
| FR-005 | T031 · T032 · T034 · T036 · T037 · T040 · T081 |
| FR-006 | T042 · T043 · T044 · T045 · T047 · T048 · T078 · T082 |
| FR-007 | T018 · T019 · T020 · T021 · T022 · T028 · T033 · T039 · T043 · T044 · T048 · T049 · T050 · T051 · T052 · T076 · T080 · T104 |
| FR-008 | T002 · T010 · T033 · T038 · T039 · T044 · T047 · T052 |
| FR-009 | T083 · T084 · T085 · T086 · T087 · T088 · T089 |
| FR-010 | T003 · T005 · T014 · T015 · T026 · T061 · T062 · T063 · T064 · T065 · T066 · T070 |
| FR-011 | T003 · T014 · T026 · T067 · T068 · T072 |
| FR-012 | T003 · T014 · T026 · T069 · T070 |
| FR-013 | T041 · T055 · T056 · T057 · T058 · T060 |
| FR-014 | T015 · T053 · T054 · T058 · T059 |
| FR-015 | T007 · T057 · T073 · T074 · T077 · T078 · T081 |
| FR-016 | T007 · T016 · T017 · T027 · T075 · T079 · T080 · T082 · T104 |
| FR-017 | T013 · T025 · T029 · T090 · T091 · T092 · T093 · T097 · T108 |
| FR-018 | T094 · T096 · T107 · T113 |
| FR-019 | T030 · T071 · T108 · T110 |
| FR-020 | T111 |
| FR-021 | T098 |
| FR-022 | T100 |
| FR-023 | T098 · T102 · T103 · T106 · T114 |
| FR-024 | T101 · T102 · T115 |
| FR-025 | T001 · T008 · T103 · T112 · T114 |
| FR-026 | T095 · T106 · T113 |
| FR-027 | T012 · T024 · T054 |
| FR-028 | T064 |
| FR-029 | T011 · T024 · T091 |
| FR-030 | T096 · T113 |
| FR-031 | T004 · T005 · T006 · T007 · T109 |
| FR-032 | T099 |

### SC → 任务

| SC | 任务 |
|---|---|
| SC-001 | T006 · T031 · T032 · T034 · T036 · T037 · T040 |
| SC-002 | T006 · T042 · T043 · T044 · T045 · T047 · T048 |
| SC-003 | T053 · T054 · T058 |
| SC-004 | T003 · T005 · T014 · T026 · T067 · T068 · T069 · T070 · T072 |
| SC-005 | T098 · T099 · T100 · T102 · T103 · T114 |
| SC-006 | T011 · T015 · T035 · T046 · T061 · T062 · T063 · T064 · T065 · T066 |
| SC-007 | T036 · T037 · T040 · T041 · T055 · T056 · T058 · T060 |
| SC-008 | T057 |
| SC-009 | T007 · T016 · T017 · T027 · T073 · T074 · T075 · T076 · T077 · T078 · T079 · T080 · T081 · T082 |
| SC-010 | T083 · T084 · T085 · T086 · T087 · T088 · T089 |
| SC-011 | T010 · T018 · T019 · T020 · T022 · T028 · T033 · T038 · T039 · T043 · T044 · T047 · T048 · T049 · T051 · T075 · T104 |
| SC-012 | T019 · T021 · T028 · T050 · T051 · T052 · T076 |
| SC-013 | T015 · T054 · T059 |
| SC-014 | T002 · T004 · T009 · T012 · T023 · T024 · T026 · T069 · T105 |
| SC-015 | T013 · T024 · T025 · T029 · T090 · T091 · T092 · T093 · T094 · T097 · T108 |
| SC-016 | T011 · T094 · T096 · T107 · T113 |
| SC-017 | T111 |
| SC-018 | T071 · T110 |
| SC-019 | T030 · T096 · T110 |
| SC-020 | T095 · T106 · T113 |
| SC-021 | T008 · T103 · T112 · T114 |
| SC-022 | T101 · T102 · T115 |
| SC-023 | T004 · T005 · T006 · T007 · T109 |
| SC-024 | T001 · T030 · T102 · T106 · T108 · T110 · T114 |

### 裁定 / 承接 / 登记项 → 任务

| 项 | 任务 |
|---|---|
| **H-1 / 裁定 4 / 裁定 8** | T035 · T037 · T046 · T048 · T077 |
| **H-2 / 裁定 9** | T018 · T019 · T020 · T021 · T033 · T039 · T049 · T050 |
| **H-3 / B11F1 的 D-2 / 裁定 5** | T057 |
| **H-4 / B11F1 的 D-7 / 裁定 8** | T073 · T074 · T075 · T076 · T077 · T079 |
| **H-5 / 裁定 13** | T013 · T025 · T029 · T092 · T093 |
| **H-6 / 裁定 6** | T015 · T053 · T054 · T058 · T059 |
| **H-7 / 裁定 7** | T083 · T084 · T085 · T086 · T087 · T088 · T089 |
| **H-8 / 裁定 2 / 裁定 12** | T061 · T062 · T063 · T098 · T099 · T100 |
| **F-1** | T011 · T105 |
| **F-2** | T012 · T105 |
| **F-3** | T016 · T017 · T027 · T104 |
| **F-4** | T015 · T066 · T104 |
| **F-5** | T020 · T021 · T104 |
| **F-6** | T098 |
| **F-7** | T099 |
| **F-8** | T013 · T025 · T092 · T097 |
| **F-9** | T018 · T019 · T028 · T104 |
| **F-10** | T022 · T049 · T051 · T104 · T114 |
| **D-1 / D-2** | T106 |
| **D-3 / D-4** | T098 · T100 · T106 |
| **D-5 / D-6** | T104 · T106 |
| **D-7** | T106 |
| **D-8** | T106 · T113 |
| **P-01…P-19** | T101 · T102 |
| **P-20** | T013 · T025 · T092 |
| **X-1…X-8** | T101 · T103 · T104 · T113 · T114 |
| **EV-1** | T103 · T114 |

### 任务 → FR（反向覆盖 · 每任务至少一条 FR）

> 任务描述末尾已带 `⇒ FR-xxx · SC-xxx`；本表给出**分组**核对（**无任务漏挂 FR**）。
> 详细逐条可在 tasks 正文中机械提取。

| 任务区间 | 主要 FR |
|---|---|
| T001–T008 | FR-025 / FR-031 / FR-001 / FR-010 / FR-015 |
| T009–T030 | FR-002 / FR-003 / FR-007 / FR-010 / FR-011 / FR-012 / FR-016 / FR-017 / FR-019 |
| T031–T041 | FR-001 / FR-004 / FR-005 / FR-007 / FR-008 / FR-013 |
| T042–T052 | FR-001 / FR-004 / FR-006 / FR-007 |
| T053–T060 | FR-013 / FR-014 / FR-015 |
| T061–T066 | FR-010 / FR-028 |
| T067–T072 | FR-010 / FR-011 / FR-012 / FR-019 |
| T073–T082 | FR-004 / FR-005 / FR-006 / FR-007 / FR-015 / FR-016 |
| T083–T089 | FR-009 |
| T090–T097 | FR-017 / FR-018 / FR-026 / FR-029 / FR-030 |
| T098–T115 | FR-018 / FR-019 / FR-020 / FR-021 / FR-022 / FR-023 / FR-024 / FR-025 / FR-026 / FR-031 / FR-032 |

---

## 完成判据

- [ ] 115 条任务全部勾选；
- [ ] 每条 SC 至少挂 1 条**测试 / 判定**任务（见 SC → 任务）；
- [ ] **A1 / A2 / A3** 分别由 US3 / US1+US2 / T098+T100+T102+T103+T114 判定；
- [ ] 全量 `pytest -q` 全绿（既有 1203 + 新增）；
- [ ] 新增模块行 / 分支覆盖率 **100%**；
- [ ] 人工验证记录五段式 + 来源覆盖 + F-1…F-10 与 X-1/X-2/X-6/X-8 追认 + EV-1；
- [ ] 差分 D-38…D-49 落盘（上游缺席 skip）；
- [ ] 无永久红 CI。
