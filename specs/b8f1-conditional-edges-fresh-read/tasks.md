---

description: "B8F1 · 条件边路由求值 + `END` 终止 + fresh 读（C8 独立回归测试）—— 任务清单"
---

# Tasks: B8F1 · 条件边路由求值 + `END` 终止 + fresh 读（C8 独立回归测试）

**Input**: Design documents from `/specs/b8f1-conditional-edges-fresh-read/`

**Prerequisites**:
- `plan.md`（必读 · 含 **Constitution Check** 与**六个登记项**（**R-1** 破冻结面 **7 类** ·
  **R-2** 门禁 3 的 `target.py` 部分 + **门禁 4 的验收基线 fake 轮** + 门禁 5 的真实模型轮**分阶段延后** ·
  **R-3** 下游承接 **D-1…D-5** 的跨 feature 接线 · **R-4** Phase 0 的 **9** 处事实性更正 · **R-5** 上位文档过期口径 · **R-6** `Send` 失败信号的偏离正式化）·
  **绿基线记录** + **变红清单**（**6 项变红断言** · **预登记** ⇒ **MUST NOT** 只凭推理登记 ⇒ ⚠️ **本表 ≠ 破面全集**（**7 类**）·
  **门禁编号纪律**（仍为 **G1–G30**）· **Project Structure**（★ 改动锚点逐条列出）·
  **设计后复核**）
- `spec.md`（必读 · **19 条裁定** · **FR-001…FR-042**（**42** 条）· **SC-001…SC-026**（**26** 条）·
  **引文差异 16 条** · 需求 ↔ SC **追溯表 42 行** · 上游承接 **H-1…H-11** ·
  下游承接 **D-1…D-5** · 破冻结面回溯修订清单 **7 类** · 偏离登记 **X-1…X-7**）
- `research.md`（必读 · **D-n** 决策（全部附**实测方法 + 真实输出** · 上游 `langgraph 1.2.11`）·
  **DR-n** 遗留登记 · 事实更正 **C-1…C-9**（**只更正事实 · 判据零放宽**））
- `data-model.md`（必读 · 实体模型 · 载荷形态（**恰 5 键**）· 求值状态机 **M-1…M-10** ·
  `__start__` 的**特殊相位** · 校验规则 **V-8**（已放宽）+ **V-27…V-31** · 不变量 **I-1…I-14**）
- `contracts/conditional-edge-contract.md`（**条件边契约的唯一权威** · `<!-- authority: yes -->` ·
  §1 签名与载体 · §1.1 **双参判别矩阵** · §2 求值语义 · §3 **fresh 读（C8）** ·
  §4 目标解析 · §5 投递（动态边）· §6 失败信号与校验 · §7 **I-1…I-14** MUST 逐条被解析并断言 ·
  §9 **零新增面声明**）
- `contracts/upstream-parity.md`（与上游 LangGraph 的**逐条对照** · **P-01…P-23**（**23** 条）·
  §3 差分场景索引 **D-103…D-120**（**18** 条）· §4 偏离登记 **X-1…X-7** ·
  §1.1 **取证环境**（版本钉死的落点））
- `quickstart.md`（**可照抄**的验证手册 · §0 环境与前置 · 验收闸口 **V1…V16** ·
  §18 人工验证记录模板）

**Tests**: **含**测试任务 —— 本 feature 的成功标准**全部**以断言形式给出（**SC-001…SC-026**），
且宪法原则 VI **v1.11.0** 要求：**每条 SC 至少挂一条能判定它的任务**⇒ ⇒ ⇒
「**实现任务**」**不**构成判定覆盖 ⇒ ⇒ ⇒ 测试任务 MUST 与实现任务**分列**且**先写 · 先失败**。
spec 另**强制**要求：① **否定式**的 C8 回归（FR-034 · SC-001 / SC-014）；
② **契约守卫**解析 `conditional-edge-contract.md` §7 的 **I-1…I-14** 并**逐条**断言
（FR-014 · SC-013）⇒ MUST NOT 只测行为而不校验契约文本；
③ **差分场景组** **D-103…D-120**（**18** 条 · 双真实实现对跑 · 上游缺席即 `skip`）；
④ **零副作用**的子进程断言（FR-033 · SC-017 / SC-018）；
⑤ **零新增面**的清点断言（FR-037 · SC-016）⇒ ⇒ ⇒
⑥ **文档守卫断言**（FR-042 · SC-019 / SC-020 / SC-026）—— 宪法原则 VI **v1.11.0 + v1.13.0**：
  「**写记录**」与「**追认**」类任务**不**构成判定覆盖 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒
测试是**交付面的一部分**，**不是**可选项。

**Organization**: 任务按用户故事分组，每个故事可**独立实现、独立测试、独立交付**。

**本 feature 的可测判据总表**（**42 FR + 26 SC ↔ 76 条任务**）：
追溯见文末「**附录 · 任务 ↔ spec 追溯表」——
**每个 FR 与每个 SC 均至少被一条任务映射**（**FR 42/42 · SC 26/26**）·
**反向**：**每条任务**携带的义务 MUST 挂上**至少一条 FR**（⇒ 追溯表**双向**齐全 · 宪法原则 VI）。
> ⚠️ **判定覆盖的两处新增**（2026-11-17 analyse 轮的修复）：
> **SC-019 / SC-020**（人工门禁类）⇒ 由 **T068**（**文档守卫断言**）承担 ⇒ ⇒ ⇒ 「写记录 / 追认」
> 类任务（T058 / T059 / T060 / T061）**不**计入判定覆盖（宪法原则 VI v1.13.0）⇒ ⇒ ⇒
> **SC-025 / SC-026**（`agent_loop.py` 硬断言 / fake 轮实测输出）⇒ 分别由 **T067** / **T068** 承担。
其中 **SC-001**（C8 的**否定式**断言 · 本 feature 的**最高判据**）由 **T024 / T029 / T054** 承载，
**SC-003**（返回 `END` ⇒ 后续目标执行 **0** 次）由 **T035…T039** 承载，
**SC-005**（`path_map` 的 list / dict 两形态）由 **T030…T034** 承载，
**SC-006 / SC-007**（失败信号**两态**）由 **T032 / T033 / T040 / T041 / T043** 承载，
**SC-010 / SC-011**（路由通道缺席 / 零写入）由 **T026 / T047 / T053** 承载，
**SC-021**（双参形态）由 **T008 / T015** 承载，
**SC-022 / SC-023**（`__start__` 的三种情形）由 **T014 / T016** 承载，
**SC-024**（branch 名唯一）由 **T017** 承载，
**SC-013**（差分组全绿）由 **T022 / T056** 承载，
**SC-019 / SC-020**（追认 / 人工记录）由 **T068**（**文档守卫断言**）承载（**T058…T061** 是**被断言的产物**，**不**构成判定覆盖），
**T059**（**发起者追认** · 登记项 **R-1** · 破冻结面 **7 类** · **唯一一次**）是**阻断合入**的
**发起者确认**任务；**T060**（登记项 **R-2** · 门禁分阶段延后）与 **T061**（登记项 **R-3** ·
跨 feature 文档接线）**只备料**追认段落 ⇒ ⇒ ⇒ 确认动作**并入 T059 的同一次**
⇒ ⇒ ⇒ **不另计次**（宪法 v1.8.0「追认次数每 feature MUST ≤ 1 次」）⇒ ⇒ ⇒ 三者**都是**
**阻断合入**的任务（**MUST NOT** 在追认落地前合入）。
**T066**（变红清单**实测化** · 宪法 v1.11.0 的基线义务）· **T067**（`agent_loop.py` 的 B1 / B2 硬断言 ·
破冻结面 **T-7** · **EV-2 承接**）· **T068**（**文档守卫断言**）为 analyse 轮新增的三条任务。

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可并行（**不同文件**且无未完成依赖）—— ⚠️ **同文件**内的多条任务
  **起草可并行**、**合入 MUST 串行**（一次提交）⇒ 否则并行编辑会互相覆盖
- ⚠️ **本 feature 的 `[P]` 纪律**：多个任务**共用**同一文件（`tests/runtime/test_conditional_edges.py` 等）
  ⇒ ⇒ ⇒ `[P]` 表示「**起草**可并行（不同用例 · 不同函数）」
  ⇒ ⇒ ⇒ **合入 MUST 串行**（一次提交 · 避免同文件冲突）
  ⇒ ⇒ ⇒ 与 B5F2 的 tasks.md **同款**处置
- **[Story]**：所属用户故事（US1…US6）—— **Phase 1 / Phase 2 与 Polish 阶段不标**
- 每条任务都带**确切文件路径**；契约的**逐字内容**在 `contracts/` 与 `data-model.md` 中，
  本文件**只引用不复制**
- **逐条追溯**：每条任务对应的 **FR / SC** 见文末「**附录 · 任务 ↔ spec 追溯表**」
  （宪法原则 VI：「tasks MUST 逐条勾选、**可追溯到 spec 条目**」）
- ⚠️ **任务 ID 与排版顺序解耦**（**analyse 轮补登记**）：**T066 / T067 / T068 / T069 / T070**
  是分析轮新增的任务 ⇒ 按**执行依赖**插入所在 Phase（**T066 / T069 / T070** 属 Phase 2 ·
  **T067 / T068** 属 Phase 9）⇒ ⇒ ⇒ **ID 不单调是刻意为之**（既有编号**零变动** ⇒
  追溯关系不断裂）⇒ ⇒ ⇒ **执行顺序 MUST 以「Dependencies & Execution Order」为准**
- ⚠️ **2026-11-18 · analyse 轮第二轮新增任务**：**T071…T075**（**5** 条 · 全部是
  **补覆盖的用例任务** · 见下方各 Phase）⇒ ⇒ ⇒ 编号续在 **T070** 之后（**既有编号零变动**）·
  **T074** 属 Phase 2（双参形态的**附带信号**判定）· **T072** 属 Phase 6（US4）·
  **T073** 属 Phase 4（US2）· **T071 / T075** 属 Phase 7（US5）⇒ ⇒ ⇒ **ID 不单调是刻意为之**
- ⚠️ **2026-11-18 · 实施轮补登记任务**：**T076**（**逐 feature 的一键验收脚本**
  · `harness/verification/B8F1/acceptance.py`）⇒ ⇒ ⇒ **实施期发现**：`tasks.md` 原先
  **未列**该工件 ⇒ ⇒ ⇒ 但仓库的**既有范式**是「**每个 feature 都有** `acceptance.py`」
  （**16** 个 feature · 仅 **B3F1**（CI 门禁 feature · 按设计）例外）⇒ ⇒ ⇒
  ⇒ ⇒ ⇒ **补登记为 T076**（编号续在 **T075** 之后 ⇒ **既有编号零变动**）⇒ ⇒ ⇒
  ⇒ ⇒ ⇒ **零新增破面**（新增工件 ⇒ 追认次数仍 == **1**）

## Path Conventions

- **内核实现**：`src/freegraph/runtime/`
  - `_routing.py`（★ **新建** · **L2 私有** · 路由求值 / 目标解析 / 失败信号
    ⇒ MUST **NOT** 进 `freegraph.runtime.__all__`）
  - `superstep.py`（★ **改** · 移除 V-8 守卫 + 阶段 ③′ 与阶段 ① 之前的两处求值落点）
  - `read.py`（既有 · **零改动** —— fresh 读**复用** `local_read`）
- **L3 接线**：`src/freegraph/_stategraph.py`（★ **改** · `_graph_spec_from()` 填入载荷）
- **测试**：`tests/runtime/`（门禁 **G2** 禁 `tests/contracts/**` import `freegraph.*`）
  - `test_conditional_edges.py`（★ **新建** · 条件边的**全部**回归用例）
  - `test_conditional_edge_contract.py`（★ **新建** · **契约守卫** · 解析 **I-1…I-14**）
  - `test_conditional_edge_surface.py`（★ **新建** · **零新增面**清点 · 7 / 23 / 21 / 11 键）
  - `test_manual_record_guard.py`（★ **新建** · **文档守卫断言** · SC-019 / SC-020 的判定覆盖）
  - `test_read_fresh.py`（★ **改** · fresh 读在**路由场景**下的断言补充）
  - `test_superstep_basic.py`（★ **改** · 冻结断言 ①）
  - `test_superstep_contract.py`（★ **改** · 冻结断言 ②）
  - `tests/facade/test_compiled_graph.py`（★ **改** · 冻结断言 ④）·
    `tests/differential/parity_probe.py`（★ **改** · 差分 **D-103…D-120**）·
    `tests/contracts/test_contract_regressions.py`（★ **改** · C8 挂载点 + 元测试）
- **人工记录**：`harness/verification/B8F1/manual-verification.md`（★ **新建** · 五段式）
- **验收脚本**：`harness/demo/graph_core.py`（★ **改** · A5 组）·
  `harness/demo/agent_loop.py`（★ **改** · B1 / B2 组 · 破冻结面 **T-7** · **EV-2 承接**）·
  `harness/demo/target.py`（**MUST NOT** 改动 · 只读基准 · **T-4** 不破）
- **跨 feature 接线**：`harness/features/` 下 **6** 份提示词初稿（★ **改** · **只接线**）
- **文档**：`README.md`（★ **改** · API 兼容矩阵章节）· `THIRD_PARTY_NOTICES`（**零新增**）
- **上游已交付文档的回溯修订**（破冻结面 **T-1** 的 ②③④ · **T069** · 宪法 v1.9.0 ① 的
  「契约 + spec」两面 ⇒ **拆分而不删**）：
  - `specs/b7f1-superstep-loop/contracts/superstep-contract.md`（§2.1 的「条件边」行 +
    §2.1.1 的 **V-8** 行）
  - `specs/b7f1-superstep-loop/spec.md`（**FR-033** / **裁定 25** 行）
  - `specs/b7f1-superstep-loop/data-model.md`（**V-8** 行）

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 绿基线（宪法 v1.11.0）· 取证环境 · 测试骨架 ⇒ ⇒ ⇒ ⚠️ **实测化**（冻结断言清单）归 **T066**（Phase 2 末）

- [X] T001 跑 `uv run --no-project --python .venv python -m pytest tests/ -ra`，把**绿基线**（用例计数 / 跳过数 / 失败数 / 跑测时刻）写回 `specs/b8f1-conditional-edges-fresh-read/plan.md` 的「绿基线记录」表（**阻断后续全部实现任务**）⇒ ⇒ ⇒ ⚠️ **本条只做「绿基线」**；「变红清单」的**实测化**归 **T066**（Phase 2 末）
- [X] T002 [P] 确认上游取证环境：`.venv` 的 `differential` 组内 `langgraph 1.2.11` / `langchain-core 1.7.6`，并把版本钉进 `specs/b8f1-conditional-edges-fresh-read/contracts/upstream-parity.md` §1.1
- [X] T003 [P] 按「变红清单」的**候选**逐条定位 `文件:行号`（**推理级**）⇒ ⇒ ⇒ ⚠️ **本条只立「候选清单」** —— 宪法 v1.11.0 的「**冻结断言清单 MUST 实测化**」要求在**改动源码之后**才能完成（源码未动 ⇒ 一切绿 ⇒ **实测不出「变红」**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **实测化归 T066**（Phase 2 末 · MUST 在 T005 / T006 / T019 / T020 / T021 / T022 之后）
- [X] T004 [P] 新建 `tests/runtime/test_conditional_edges.py` 骨架（**MUST 先写 · MUST 先失败**；承载全部条件边回归用例 —— 因门禁 G2 禁止 `tests/contracts/**` import `freegraph.*`）

**Checkpoint**: 绿基线已记录 · 变红清单的**候选**已定位（T003）⇒ 方可动源码 ⇒ ⇒ ⇒ ⚠️ 变红清单的**实测化**归 **T066**（Phase 2 末）

---

## Phase 2: Foundational（阻塞性前置）

**Purpose**: 路由求值内核 + 破冻结面的回溯修订 —— **阻塞全部用户故事**

**⚠️ CRITICAL**: 任何用户故事的工作 MUST 在本 Phase 完成前开始

- [X] T005 移除 V-8 守卫（`src/freegraph/runtime/superstep.py:484-487`）⇒ `GraphSpec.conditional_edges` 非空**不再**是构造期失败（破冻结面 **T-1**） （裁定 14）
- [X] T006 在 `src/freegraph/_stategraph.py` 把 `_conditional_mapping()`（`:205-225`）的结果填入 `GraphSpec.conditional_edges` ⇒ **零新增编译产物私有字段**（`vars(compiled)` 仍 == **11** 键） ⇒ ⇒ ⇒ ⚠️ **接线方式 MUST 钉死**（2026-11-18 · analyse 轮修复）：`GraphSpec` 是 **`@dataclass(frozen=True)`** ⇒ **MUST NOT** 构造后赋值 ⇒ ⇒ ⇒ 推荐形态 = **给 `_graph_spec_from()`（`:175-202`）增加 `conditional_edges` 形参** · 由 `compile()`（`:667-714` · `_graph_spec_from` 调用在 `:692`）把 `_conditional_mapping()` 的结果**传入** ⇒ **一次求值 · 零重复调用** ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 在 `_graph_spec_from()` **内部**再调一次 `_conditional_mapping()`（⇒ 同一载荷**两处派生** ⇒ 漂移风险）⇒ ⇒ ⇒ docstring `:186` 的「**不传**」口径同步订正 （裁定 1 · 裁定 14）
- [X] T007 新建 `src/freegraph/runtime/_routing.py`（**L2 私有** · **MUST NOT** 进 `freegraph.runtime.__all__` ⇒ 公开面零变更）—— 承载载荷解析 / 目标解析 / 路由函数调用 / 失败信号 （裁定 1）
- [X] T008 在 `src/freegraph/runtime/_routing.py` 实现路由函数的**调用形态**：单参 `f(fresh_view)` 与双参 `f(fresh_view, config)`；双参**判别依据 = 第二参的**参数名**是 `config`**（**不是**位置参数个数）⇒ 永远只传**一个**位置实参 ⇒ `config` 以**关键字**注入 ⇒ 第二参名字不叫 `config` ⇒ 按**一参**调用 ⇒ `**kwargs` 形态**不注入** ⇒ 注解**不在匹配集**内 ⇒ **跳过注入**；第二参**内容** = 用户交给 `invoke` 的**原始 `config`**（`RunConfig` / mapping / `None` · **逐字**） （**裁定 12 · 裁定 16**）
- [X] T009 在 `src/freegraph/runtime/_routing.py` 实现**目标解析**：`path_map` 为 dict ⇒ 返回值作 **key** 查表；`path_map` 为 list ⇒ 用 L3 已归一化的 `{name: name}`；无 `path_map` ⇒ 返回值直接作节点名；返回序列 ⇒ **多目标**（去重保序）；**单独返回** `END` ⇒ **无条件终止**（**先于**查表）⇒ ⇒ **序列内**的 `END` ⇒ **剔除**（其余目标照常执行 · 照抄上游 E-13） （裁定 5 · 裁定 9）
- [X] T010 在 `src/freegraph/runtime/_routing.py` 实现**失败信号两态**：**有** `path_map` ⇒ 内置 `KeyError`；**无** `path_map` ⇒ 内置 `ValueError`；两态**消息**均**指明返回值与可选目标**（**零新增错误类型**） （裁定 6）
- [X] T011 在 `src/freegraph/runtime/_routing.py` 实现 **fresh 读**调用：`local_read(state.channels, outcome.writes, fresh=True)`（`src/freegraph/runtime/read.py:163-197`）⇒ MUST **显式传** `fresh=True` ⇒ 覆盖**整张通道表** ⇒ **路由型通道缺席** ⇒ **零污染** （裁定 2 · 裁定 3）
- [X] T012 把路由求值接进 `src/freegraph/runtime/superstep.py` 的**阶段 ③′**（`:1253-1267`）：源节点任务**成功落回**后求值 ⇒ 路由目标与该节点同轮的 `Command.goto` 目标**取并集**（去重保序）⇒ 并入 `outcome.gotos` ⇒ ⇒ ⇒ ⚠️ **投递代码零新增**：`_commit_outcome()` 的既有写入 `state.dynamic_edges[target] = outcome.gotos`（`superstep.py:987`）**无条件生效** ⇒ ⇒ ⇒ MUST NOT 另写一套投递路径 （裁定 1 · 裁定 13）
- [X] T013 **核对并断言**动态边投递的语义（**不写新的投递代码** —— 投递由 T012 并入 `outcome.gotos` 后由 `_commit_outcome()` 的既有写入 `state.dynamic_edges[target] = outcome.gotos`（`superstep.py:987`）自动生效）⇒ ⇒ ⇒ 在 `tests/runtime/test_conditional_edges.py` 断言：① `state.dynamic_edges` 的**键 == 源节点名**（契约 **I-4**）② 路由目标在**下一轮**被触发且执行次数 == **1** ③ `_trigger_groups()`（`:613-657`）把动态边编成**单元素组** ⇒ ⇒ ⇒ **零新增触发机制** （裁定 1 · 裁定 8）
- [X] T014 实现 `__start__` 条件边的求值：在 `src/freegraph/runtime/superstep.py` 的**阶段 ① 之前**求值一次 ⇒ 结果写进 `state.dynamic_edges["__start__"]` ⇒ 目标在**第 1 轮**被触发 ⇒ 与静态入口边**同轮并行** ⇒ 允许**纯条件边入口**（无静态入口点） ⇒ ⇒ ⇒ ⚠️ **幂等标记 MUST 钉死**（2026-11-18 · analyse 轮修复 · 发起者 2026-11-18 拍板 · 与 spec FR-038 / data-model M-7 注一致）= **`"__start__" in state.dynamic_edges`（键存在性）** ⇒ ⇒ ⇒ **MUST NOT** 用「值非空」当判据（返回 `END` ⇒ 空 tuple ⇒ **同样**表示已求值）⇒ ⇒ ⇒ **MUST NOT** 给 `SchedulerState` 新增字段（其「构造签名与名字逐字不变」是 B7F1 / B9F1 / **B8F1** 的冻结面 · `superstep.py:285-287`）⇒ ⇒ ⇒ **MUST NOT** 用 `state.step == 0` （裁定 17）
- [X] T015 [P] 在 `tests/runtime/test_conditional_edges.py` 写**双参形态**的判定用例：第二参 == 用户交给 `invoke` 的**原始 `config`**（`RunConfig` / mapping / `None` · 逐字）；第二参名字**不叫** `config` ⇒ 按**一参**调用（上游同款 `TypeError`）；`**kwargs` 形态 ⇒ **不注入**；注解不在匹配集内 ⇒ **跳过注入**（**SC-021**） ⇒ ⇒ ⇒ ⚠️ **「不发 `UserWarning`」的判定归 T074**（2026-11-18 · analyse 轮新增 · 归偏离 **X-5**） （**裁定 12 · 裁定 16**）
- [X] T016 [P] 在 `tests/runtime/test_conditional_edges.py` 写**`__start__` 条件边**的判定用例：被求值（**不是**静默空跑）· **纯条件边入口** · 与静态入口**并存**时两目标**同轮并行** · 返回 `END` ⇒ 该分支终止（**SC-022 / SC-023**） · **幂等**：在**含 ≥ 2 轮**的图上（条件边回到上游节点）`__start__` 的路由函数**被调用次数仍 == 1**（裁定 17 · 契约 I-11） （裁定 17）
- [X] T017 [P] 在 `tests/runtime/test_conditional_edges.py` 写**branch 名唯一**的判定用例：同源重名 ⇒ 内置 `ValueError`（消息**点名**分支名与源节点）（**SC-024**） （裁定 18）
- [X] T074 [P] 在 `tests/runtime/test_conditional_edges.py` 写「**注入被跳过时的附带信号**」的判定用例（2026-11-18 · analyse 轮新增 · 归偏离 **X-5**）：注解**不在**匹配集内（如 `config: dict`）⇒ MUST **跳过注入** ⇒ 按**一参**调用 ⇒ 内置 `TypeError` ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 发 `UserWarning`（上游在 `langgraph/_internal/_runnable.py:352-359` **发** ⇒ freegraph **不发** ⇒ 零新增可观察输出 · 失败信号 `TypeError` **逐字同款**）⇒ ⇒ ⇒ ⚠️ 该差异**MUST NOT** 用差分场景锁（差分的**三投影** = 输出状态 / 事件序列 / 节点入参 ⇒ **不含** Python 警告）⇒ ⇒ ⇒ 由**本条**单元测试锁定（**SC-021 ④**）
- [X] T018 [P] 新建 `tests/runtime/test_conditional_edge_contract.py`：**契约守卫** —— 解析 `specs/b8f1-conditional-edges-fresh-read/contracts/conditional-edge-contract.md` §7 的 **I-1…I-14** 并**逐条**断言（仿 `tests/runtime/test_superstep_contract.py:122-159` 的形状：声明数 == 期望数 · 每条有绑定 · 每个绑定指向真实测试函数） （裁定 4）
- [X] T019 [P] 回溯修订冻结断言 ①：`tests/runtime/test_superstep_basic.py:557-576` —— **拆分**（原「非空 ⇒ 显式失败」改为「**非空 ⇒ 接受且原样承载**」）⇒ ⇒ ⇒ ⚠️ 该区间含**两条**用例（`:557-565` 与 `:568-576`）⇒ **= plan 变红清单 ① + ②** ⇒ ⇒ ⇒ ⚠️ **既有 docstring 的 `SC-025` 属 B7F1 的编号域**（B7F1 语义 = 「条件边」字段恒空）⇒ 回溯修订时 MUST 加 feature 限定语（如 `SC-025（B7F1）`）⇒ ⇒ ⇒ **MUST NOT** 让它与 B8F1 的 SC-025（`agent_loop.py` 硬断言）混为一谈
- [X] T020 [P] 回溯修订冻结断言 ②：`tests/runtime/test_superstep_contract.py:77` 的不变式映射 **I-14** + `:609-617` 的用例体 —— **拆分**（语义由「恒空即失败」改为「**填值即被路由求值消费**」；**编号与槽位不变** ⇒ 契约守卫的解析范围**零改动**）⇒ ⇒ ⇒ ⚠️ **= plan 变红清单 ③** ⇒ ⇒ ⇒ ⚠️ 该文件的不变式编号 **I-1…I-16** 属 **B7F1 的编号域**（本 feature 契约的 I-1…I-14 属 **B8F1 自有编号域** · `data-model.md` §6 注）⇒ ⇒ ⇒ 引用时 MUST 写全文件前缀（勿混用）
- [X] T021 [P] 回溯修订冻结断言 ④：`tests/facade/test_compiled_graph.py:263-265` —— **替换为反面断言**（`GraphSpec.conditional_edges` **非空**且与 `compiled._conditional_edges` 一致）⇒ ⇒ ⇒ ⚠️ **= plan 变红清单 ④** ⇒ ⇒ ⇒ `:111-114` 的 **11 键持有面断言 MUST 逐字不动**（**T-3 不破**）
- [X] T022 [P] 把差分场景 **D-103…D-120**（**18** 条）落进 `tests/differential/parity_probe.py` ⇒ **MUST NOT** 填 B5F2 夹具的 `conditional_edges` 字段（其 freegraph 侧驱动器是**线性替身** ⇒ **V-4 不破** ⇒ `tests/differential/spec_builder.py:122-126` 与 `tests/differential/test_differential.py:123-132` **逐字不动**）⇒ ⇒ ⇒ ⚠️ **场景组落点 MUST 钉死**（2026-11-18 · analyse 轮修复）：落进**既有**的 `_scenarios()`（⇒ `tests/differential/test_parity_probe.py:95-120` 的 `test_the_verdict_vocabulary_is_closed` 的「判词取值域 + `note` 非空」守卫**自动覆盖** ⇒ 变红清单 ⑥ 的前提成立）⇒ ⇒ ⇒ ⚠️ **MUST NOT** 新建第 5 个场景组函数而**不**同步扩展该守卫 ⇒ ⇒ ⇒ ⚠️ **差分侧的载荷派生口径 MUST 与 L3 逐字一致**（`targets` / `route_channels` 的派生见 `_stategraph.py:643-646`）⇒ ⇒ ⇒ **MUST NOT** 在差分侧**另写一份** ⇒ ⇒ ⇒ **MUST** 有一条断言锁住「差分侧载荷 == L3 载荷」 · ⚠️ **载体扩展（属「扩展」非「重造」· 裁定 15 · FR-032）**：`Scenario` dataclass 新增**条件边字段**（外层 key = 源节点名 · 内层 = `branch` / `path` / `path_map` / `targets` / `route_channels` **五键** · 顺序 = 登记顺序）+ `run_freegraph()` 把该载荷**传入** `GraphSpec.conditional_edges` ⇒ ⇒ ⇒ **MUST NOT** 新建第二套差分夹具 / 第二条差分执行路径 · ⚠️ **判词非 `SAME` 的 6 条**（STRICTER 2 + DIFF 4）**MUST** 带**非空** `note`（与既有守卫 `tests/differential/test_parity_probe.py:106-108` 对齐 ⇒ 判据**只收紧**） （裁定 15）
- [X] T023 [P] **新建** `tests/runtime/test_conditional_edge_surface.py` 并写**零新增面**断言：`freegraph.graph` 仍 **7** 符号 · `freegraph.runtime` 仍 **23** 符号（清单单一事实源 = `tests/runtime/_runtime_export_manifest.py`）· 契约层仍 **21** 符号 · `vars(compiled)` 仍 == **11** 键（对照 `tests/facade/test_compiled_graph.py:111-114` 的既有断言）· `freegraph.runtime.errors` 的符号集合**不变**（零新增错误类型）· **未实现**的 L1 协议方法（**恰 5 个**：`stream()` / `get_graph()` / `get_state()` / `get_state_history()` / `update_state()`）仍抛内置 `NotImplementedError` 且消息**点名归属 feature**（⚠️ `draw_mermaid_png()` **尚未存在** ⇒ **MUST NOT** 计入本项） （裁定 1）


- [X] T069 **回溯修订上游已交付文档**（宪法 v1.9.0「破冻结面的三条」① 的「**契约 + spec**」两面 —— 破冻结面 **T-1** 的 ②③④ 三处）⇒ ⇒ ⇒ **拆分而不删**（原「恒空即失败」行**保留**并标注「**自 B8F1 起放宽**：允许非空 · 由路由求值消费」）⇒ ⇒ ⇒ 逐处落点：① `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §2.1 的「条件边」行 + §2.1.1 的 **V-8** 行 ② `specs/b7f1-superstep-loop/spec.md` 的 **FR-033** / **B7F1 的**裁定 25 行 ③ `specs/b7f1-superstep-loop/data-model.md` 的 **V-8** 行 ⇒ ⇒ ⇒ ⚠️ **T-5**（C8 挂载点）的**原第 ③ 处**（`specs/b3f1-scaffold-ci-gates/` 的门禁契约行）**已撤除** —— 经复核该契约的挂载点 `status` 已是「`not-landed` / `landed` **两态**口径」（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md:372-374`）⇒ ⇒ ⇒ **本次无需改动** ⇒ ⇒ ⇒ **破面全集仍为 7 类** ⇒ ⇒ ⇒ **MUST NOT** 改其余 **V-1…V-3**（逐字不动）· **MUST NOT** 改宪法正文 · **MUST NOT** 新增门禁编号 （裁定 14 · 破冻结面 **T-1**）


- [X] T070 在 `src/freegraph/runtime/_routing.py` **实现**路由函数返回 `Send` / `list[Send]` 时**复用** B11F1 的既有构造器 `validate_send()` / `make_fanout()`（`src/freegraph/runtime/_fanout.py:56-104`）⇒ ⇒ ⇒ **零新增** fan-out 机制 ⇒ ⇒ ⇒ **MUST NOT** 改 B11F1 的冻结面（V-19 / V-21）⇒ ⇒ ⇒ 失败信号的分叉已登记（**X-6 / X-7**） （裁定 10）


- [X] T066 **实测化**「变红清单」（宪法 v1.11.0 的**基线义务** · MUST NOT 只凭推理登记）：在 **T005 / T006 / T019 / T020 / T021 / T022** 落地后（⚠️ **2026-11-18 · analyse 轮修复**：**T022 MUST 在本条之前** —— 它是 plan 变红清单 ⑥（差分侧守卫）的变红源）⇒ ⇒ ⇒ 重跑基线命令 `uv run --no-project --python .venv python -m pytest tests/ -ra` ⇒ ⇒ ⇒ 把**实测变红**的断言逐条（`文件:行号` + **变红原因**）写回 `specs/b8f1-conditional-edges-fresh-read/plan.md` 的「变红清单」表 ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 只凭推理登记 ⇒ ⇒ ⇒ 若实测发现**更多**变红断言 ⇒ MUST **追加登记**（并先判「是否由本 feature 的落地形态导致」）⇒ ⇒ ⇒ ⚠️ **时序**：本条 MUST 在上述**六条**落地**之后**（否则实测不到任何变红 ⇒ 清单**未实测化**）⇒ ⇒ ⇒ ⚠️ 本条**实测化**的对象 = plan 的「变红清单」**6 项**（①…⑥）⇒ ⇒ ⇒ **spec 的 T-6 / T-7 属「时序风险」** ⇒ ⇒ ⇒ **不在**本条的实测化范围（⇒ 见 plan 的「时序风险」段）

**Checkpoint**: 路由求值内核就位 · **7 类**破面已回溯修订 · 变红清单已**实测化** ⇒ 各 story 可并行开工

---

## Phase 3: User Story 1 - 路由基于本节点的最新产出（Priority: P1）🎯 MVP

**Goal**: 路由函数看到「当前值 + 本节点本次写入」。

**Independent Test**: 2 节点图（`writer` 写 `{"messages": ["fresh"], "llm_calls": 7}` ·
`router` 记录收到的状态后返回 `"after"`）⇒ `invoke` ⇒ 断言 `messages == ["fresh"]` 且
`llm_calls == 7`（**否定式断言**）。

### Tests for User Story 1（MUST 先写 · MUST 先失败）

- [X] T024 [P] [US1] 写 C8 fresh 读的**否定式**回归用例（`tests/runtime/test_conditional_edges.py`）：断言路由函数**看到了**新写入的值（**不是**「跑通了」）
- [X] T025 [P] [US1] 写**归约型**通道的 fresh 读用例（`tests/runtime/test_read_fresh.py`）：初始 `["seed"]` ⇒ 路由函数看到 `["seed", "fresh"]`
- [X] T026 [P] [US1] 写**无值覆盖型通道缺席**于路由入参的用例（`tests/runtime/test_read_fresh.py` · 稀疏口径 · 与节点入参同款）
- [X] T027 [P] [US1] 写「同轮**另一**节点的写入**不可见**」的用例（`tests/runtime/test_conditional_edges.py` · fresh 读 = **本节点本次**写入 · 不是全轮）
- [X] T028 [P] [US1] 写**门面可观察**用例（`tests/runtime/test_conditional_edges.py`）：条件边路由在 `invoke`（B7F3 门面）上可观察（**SC-002**）

### 实现收尾断言（User Story 1 · 实现见 Phase 2）

- [X] T029 [US1] 在 `tests/runtime/test_conditional_edges.py` 断言路由函数**每次源节点执行只被求值一次**（**MUST NOT** 因多轮重跑而重复求值）· 且 fresh 读**零污染**（通道正式值与绑定前后不变）· 且**路由形成环**（条件边回到上游节点）⇒ MUST 受既有 `recursion_limit` 约束 ⇒ 超限抛 `GraphRecursionError`（**不包装** · B13F1 的既有口径）

**Checkpoint**: User Story 1 可**独立**实现 / 独立测试 / 独立交付

---

## Phase 4: User Story 2 - 两种 path_map 都能用（Priority: P1）

**Goal**: list 与 dict 两种 `path_map` 都能跑通。

**Independent Test**: 同一张图分别以 list / dict 登记 ⇒ 两次 `invoke` ⇒ 断言都路由到**预期节点**
（该节点执行 1 次 · 另一目标执行 0 次）。

### Tests for User Story 2（MUST 先写 · MUST 先失败）

- [X] T030 [P] [US2] 写 list 形态 `path_map` 的路由用例（`tests/runtime/test_conditional_edges.py` · `["a", END]` ⇒ `a` 执行 1 次 · `END` 之后无节点执行）
- [X] T031 [P] [US2] 写 dict 形态 `path_map` 的路由用例（`tests/runtime/test_conditional_edges.py` · `{"hit": "a", "miss": "b"}` ⇒ `a` 1 次 · `b` 0 次）
- [X] T032 [P] [US2] 写 dict 形态返回值**不在** `path_map` 内 ⇒ 内置 `KeyError` 且消息**指明返回值与可选目标**的用例（`tests/runtime/test_conditional_edges.py`） （裁定 6）
- [X] T033 [P] [US2] 写 list 形态返回值**不在** list 内 ⇒ 内置 `KeyError`（与 dict 形态**同款**）的用例（`tests/runtime/test_conditional_edges.py`） （裁定 6）
- [X] T073 [P] [US2] 写「路由函数返回**非 `str` 的可哈希值**（如 `int`）⇒ 作为 `path_map` 的 **key** **正常查表**」的用例（`tests/runtime/test_conditional_edges.py` · **FR-020** · 实测 **E-14 / E-15**）⇒ ⇒ ⇒ MUST **NOT** 先做类型收窄 ⇒ ⇒ ⇒ 命中时路由到该 key 对应的目标（**SC-005**）

### 实现收尾断言（User Story 2 · 实现见 Phase 2）

- [X] T034 [US2] 在 `tests/runtime/test_conditional_edges.py` 断言 L3 的 list→`{name:name}` 归一化**不被** L2 重做（载荷里的 `path_map` **逐字**来自 L3 · **零**重新归一化） （裁定 4）

**Checkpoint**: User Story 2 可**独立**实现 / 独立测试 / 独立交付

---

## Phase 5: User Story 3 - 返回 END 真的终止（Priority: P1）

**Goal**: 返回 `END` ⇒ 整张图停止。

**Independent Test**: 「`r` →（条件边）→ `after`」的图，路由返回 `END` ⇒ `invoke` ⇒
断言 `after` 的**执行次数 == 0**。

### Tests for User Story 3（MUST 先写 · MUST 先失败）

- [X] T035 [P] [US3] 写「返回 `END` ⇒ 目标节点执行 0 次」的用例（`tests/runtime/test_conditional_edges.py`） （裁定 5）
- [X] T036 [P] [US3] 写「`path_map = {"stop": END, "go": "a"}` ⇒ 同样终止」的用例（`tests/runtime/test_conditional_edges.py` · `END` 作 **value**） （裁定 5）
- [X] T037 [P] [US3] 写「`path_map` **不含** `END` 键 ⇒ **仍然终止**（不抛错）」的用例（`tests/runtime/test_conditional_edges.py` · **单独返回** `END` ⇒ **无条件终止** · 偏离 **X-2**） （裁定 5）
- [X] T038 [P] [US3] 写「返回序列 `[END, "a"]` ⇒ `a` 执行 1 次（`END` 被剔除）且不终止」的用例（`tests/runtime/test_conditional_edges.py`） （裁定 5）

### 实现收尾断言（User Story 3 · 实现见 Phase 2）

- [X] T039 [US3] 在 `tests/runtime/test_conditional_edges.py` 写「`path_map = {END: "b"}` ⇒ freegraph **单独返回** `END` ⇒ **无条件终止**」的用例（上游**解析后目的地 == "b"` ⇒ **不终止** ⇒ 差分 **D-118** 锁住的分叉） （裁定 5）

**Checkpoint**: User Story 3 可**独立**实现 / 独立测试 / 独立交付

---

## Phase 6: User Story 4 - 路由判错时立刻指出（Priority: P2）

**Goal**: 立刻拿到说清「返回了什么 / 可以返回什么」的异常。

**Independent Test**: 路由返回不存在的节点名 ⇒ `invoke` ⇒ 断言抛**内置异常**且消息**含**返回值与
**可选目标清单**（无 `path_map` ⇒ `ValueError` · 有 `path_map` ⇒ `KeyError`）。

### Tests for User Story 4（MUST 先写 · MUST 先失败）

- [X] T040 [P] [US4] 写「有 `path_map` + 非法返回值 ⇒ 内置 `KeyError` + 消息含返回值与可选目标」的用例（`tests/runtime/test_conditional_edges.py`） （裁定 6）
- [X] T041 [P] [US4] 写「**无** `path_map` + 返回未注册节点名 ⇒ 内置 `ValueError`（**不是**静默结束）」的用例（`tests/runtime/test_conditional_edges.py` · 偏离 **X-3** · 上游同场景**静默忽略**） （裁定 6） （**裁定 7**）
- [X] T042 [P] [US4] 写「路由函数**自己**抛异常 ⇒ **原始类型 + 原始消息**到达调用方（不被包装）」的用例（`tests/runtime/test_conditional_edges.py`） （裁定 11）
- [X] T072 [P] [US4] 写「路由函数返回 `None` / `START`（`'__start__'`）⇒ **显式失败**（**查表优先** · **FR-025** · 校验规则 **V-31**）」的用例（`tests/runtime/test_conditional_edges.py`）：**有** `path_map` ⇒ 内置 `KeyError`；**无** `path_map` ⇒ 内置 `ValueError` ⇒ ⇒ ⇒ ⚠️ 且「`path_map` 恰含 `__start__` **键**且其 **value** 合法 ⇒ **照上游路由到该 value**（**不**失败 ⇒ `START` **不是**独立的失败条件）⇒ ⇒ ⇒ 差分 **D-113** 锁「**无** `path_map`」那一侧（**SC-006 / SC-007**）

### 实现收尾断言（User Story 4 · 实现见 Phase 2）

- [X] T043 [US4] 在 `tests/runtime/test_conditional_edges.py` 断言失败信号**两态**与 spec 的 FR-021 / FR-022 **逐字一致** · **零新增错误类型**（只新增内置 `KeyError` / `ValueError` 的抛出点） （**裁定 6**）

**Checkpoint**: User Story 4 可**独立**实现 / 独立测试 / 独立交付

---

## Phase 7: User Story 5 - 一次路由到多个目标（Priority: P2）

**Goal**: 返回序列 ⇒ **并行**跑到那几个目标，各拿**同一份**共享状态。

**Independent Test**: 「`r` →（条件边）→ `b` / `c`」，返回 `["b", "c"]` ⇒ `invoke` ⇒
断言 `b` 与 `c` **各执行 1 次**且**同轮**。

### Tests for User Story 5（MUST 先写 · MUST 先失败）

- [X] T044 [P] [US5] 写「返回 `["b", "c"]` ⇒ `b` 与 `c` **各执行 1 次**（并行 fan-out）」的用例（`tests/runtime/test_conditional_edges.py`） （裁定 9）
- [X] T045 [P] [US5] 写「两个目标收到的入参**逐字相等**（**共享状态** · **无**逐目标载荷）」的用例（`tests/runtime/test_conditional_edges.py`） （裁定 9）
- [X] T046 [P] [US5] 写「返回 `[Send("b", payload)]` ⇒ `b` 收到**载荷**（**不是**共享状态）」的用例（`tests/runtime/test_conditional_edges.py` · 与上一条**语义相异** · 裁定 9） （裁定 10）
- [X] T047 [P] [US5] 写「**同轮两个源**节点路由到**同一目标** ⇒ **正常执行**（不得触发 V-6）」的用例（`tests/runtime/test_conditional_edges.py` · 路由通道**不被写入**的可判定证据 · 偏离 **X-4**） （裁定 8）
- [X] T048 [P] [US5] 写「条件边的目标集合与**屏障组**（多源汇合）**不混用**」的用例（`tests/runtime/test_conditional_edges.py` · 条件边**不受**屏障的「所有源齐备」判定影响）· **同一源节点登记多条条件边（不同 `branch`）⇒ 各求值一次 ⇒ 目标取并集（去重保序）** （裁定 4 · 裁定 13）
- [X] T071 [P] [US5] 写「路由函数返回**空序列** `[]`」的用例（`tests/runtime/test_conditional_edges.py` · 2026-11-18 · analyse 轮新增）：⇒ **MUST NOT** 报错（空序列**不是**非法返回值）⇒ ⇒ ⇒ 该源节点**不触发**任何目标 ⇒ ⇒ ⇒ 图**自然收敛**（**非** `END` 终止路径）⇒ ⇒ ⇒ MUST **NOT** 与「非法返回值 ⇒ 失败」混淆（spec Edge Cases + 契约 §4.1 · 实测 **M-A / M-A2** · **FR-018 / FR-024**） （裁定 9）
- [X] T075 [P] [US5] 写「路由函数返回**序列**且序列中含**重复目标** ⇒ **去重保序**（同一目标**只**触发一次）」的用例（`tests/runtime/test_conditional_edges.py` · 2026-11-18 · analyse 轮新增 · spec Edge Cases · 实测 **E-26** · **FR-018**） （裁定 9）

### 实现收尾断言（User Story 5 · 实现见 Phase 2）

- [X] T049 [US5] 在 `tests/runtime/test_conditional_edges.py` **断言**路由函数返回 `Send` / `list[Send]` 时走的是 **B11F1 的既有构造器** `validate_send()` / `make_fanout()`（`src/freegraph/runtime/_fanout.py:56-104`）⇒ ⇒ ⇒ **零新增** fan-out 机制（**实现见 T070**） （裁定 10）

**Checkpoint**: User Story 5 可**独立**实现 / 独立测试 / 独立交付

---

## Phase 8: User Story 6 - 执行过程零副作用（Priority: P3）

**Goal**: 路由一次**不**联网 / **不**读环境变量 / **不**引入第三方依赖。

**Independent Test**: socket 监测夹具 + `sys.modules` 快照 ⇒ 断言出站连接数 == 0、
`langchain*` / `langgraph*` / `langsmith` 出现次数 == 0。

### Tests for User Story 6（MUST 先写 · MUST 先失败）

- [X] T050 [P] [US6] 写子进程断言：`sys.modules` 中 `langchain` / `langchain_core` / `langgraph` / `langsmith` 出现次数 == **0**（`tests/runtime/test_conditional_edges.py`）
- [X] T051 [P] [US6] 写**零出站**断言（`tests/runtime/test_conditional_edges.py` · socket 监测夹具 · **只观测不阻断** · 按发起方归因 · 断言「**框架出站 == 0**」）
- [X] T052 [P] [US6] 写**零环境变量**断言（`tests/runtime/test_conditional_edges.py` · `LANGSMITH_*` / `LANGCHAIN_*` / `LANGGRAPH_CLOUD_LICENSE_KEY` / `LANGGRAPH_AUTH*` **不被读取** · 执行行为**不因环境变量而改变**）

### 实现收尾断言（User Story 6 · 实现见 Phase 2）

- [X] T053 [US6] 在 `tests/runtime/test_conditional_edges.py` 断言路由函数入参**不含** `context` 通道（**B8F3 的 C21** 机制）· **不含**路由通道（`branch:to:*`）· **`invoke` 的返回键集**同样**不含**任何 `branch:to:*`（路由通道**不进**返回键集 · FR-029）

**Checkpoint**: User Story 6 可**独立**实现 / 独立测试 / 独立交付

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 门禁落地 · 差分取证 · 人工记录 · 追认 · 跨 feature 接线

- [X] T054 把 C8 挂载点由 `not-landed` 翻为 `landed`（`tests/contracts/test_contract_regressions.py:36`）并**新增** C8 的**元测试**（**路径扫描** · 仿同文件 `:49-82` 的 C4 元测试 · **MUST NOT** import `freegraph.*` ⇒ 门禁 G2 恒绿）⇒ ⚠️ **既有占位用例的处置**（`:85-91` 的 `@pytest.mark.skip` + `raise NotImplementedError`）：MUST **改名保留**（如 `test_c8_placeholder_not_landed` · **语义留存**）或按「**拆分而不删**」并入元测试 ⇒ ⇒ ⇒ **MUST NOT** 直接删（宪法 v1.14.0）⇒ ⇒ ⇒ 新增的元测试 **MUST NOT** 与既有占位**同名**（同名 ⇒ 后者被**静默遮蔽** ⇒ 断言**失效**）
- [X] T055 把 `harness/demo/graph_core.py:254-321` 的 A5 组**软断言**（`soft(...)`）全部改成**硬断言**（`check(...)` / `eq(...)`）⇒ ⚠️ **时序**：MUST 在 **T012**（阶段 ③′ 接入）与 **T013**（动态边投递）就位**之后**落地 ⇒ 否则 CI 必红（宪法 v1.11.0「MUST NOT 写永久红的 CI」）⇒ ⇒ ⇒ （**不**依赖 T022 —— 差分场景与本条无因果关系）⇒ ⇒ ⇒ ⚠️ **归类**（2026-11-18 · analyse 轮修复）：本条是 plan 的「**时序风险 ①**（= spec 的 **T-6**）」⇒ ⇒ ⇒ **plan 变红清单中对应 `graph_core.py` A5 组的那一行已移出变红清单**（该行在移出前是**第 6 行** · 旧编号 ⑥ ⇒ **现行** ⑥ 是**差分侧守卫**）⇒ ⇒ ⇒ 移出的理由：其变红源是**本条** ⇒ 在 T066 的实测化时点必然是绿的 ⇒ 「待实测确认」永远关不掉 ⇒ ⇒ ⇒ **破面全集仍为 7 类**（T-6 仍在其中）
- [X] T056 取证差分场景组 **D-103…D-120**（**18** 条）全绿（上游缺席即 `skip`）⇒ 判词分布与 spec **逐条一致**（**SAME 12 / DIFF 4 / STRICTER 2**）⇒ 记入 `harness/verification/B8F1/manual-verification.md`
- [X] T057 执行 `specs/b8f1-conditional-edges-fresh-read/quickstart.md` 的验收闸口 **V1…V16** 并把**实测输出**回填到该文件对应闸口
- [X] T058 写 `harness/verification/B8F1/manual-verification.md`（**五段式**：验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）⇒ ⚠️ **MUST 含「fake 模型轮」的**实测输出** —— 「fake 模型轮」= 猴补（monkey-patch）`init_chat_model` + **含条件边的最小图** / `agent_loop.py` 的**工具循环轮**（**本 feature 可达** ⇒ **MUST 真跑** ⇒ **非空** ⇒ **MUST NOT** 只写「符合预期」）⇒ ⇒ ⇒ §3 实际输出 MUST 含**条件边路由**的**可观察结果**（路由目标 · 目标节点执行次数 · fresh 视图）⇒ ⇒ ⇒ MUST 显式声明「**真实模型一轮未落地**」+ 承接方 **B25F1（M4）**（登记项 R-2）⇒ ⇒ ⇒ ⚠️ **本条不构成 SC-020 的判定覆盖**（判定由 **T068** 的文档守卫断言承担 · 宪法原则 VI v1.13.0）
- [X] T059 **发起者追认 R-1（并入 R-3）**（破冻结面 **7 类**：T-1 · 冻结断言 ①②④ · T-5 · T-6 · **T-7** · **唯一一次**追认 · **MUST NOT** 由实现者代签 · **阻断合入**）⇒ 追认文字 MUST 落 `harness/verification/B8F1/manual-verification.md` ⇒ ⇒ ⇒ ⚠️ **本条是本 feature 唯一的发起者确认动作**（**R-1 / R-2 / R-3 三段落列于同一份记录** · **一次确认 + 一个日期** · 宪法 v1.8.0「追认次数每 feature MUST ≤ 1 次」⇒ 跨 feature 文档改动属「破冻结面」类 ⇒ **R-3 不另计次**） ⇒ ⇒ ⇒ ✅ **已由发起者签署**（2026-11-18 · 追认次数 == **1** · 宪法 v1.6.0 / v1.8.0）⇒ ⇒ ⇒ **合入闸口 G5 已打开**
- [X] T060 **备料 R-2 的追认段落**（门禁 3 的 `harness/demo/target.py` 部分 + **门禁 4 的验收基线 fake 轮** + 门禁 5 的真实模型轮 ⇒ 分阶段延后 · 承接方 **B22F1 + B23F1（M2）** / **B25F1（M4）** · **阻断合入**）⇒ 追认文字 MUST 落 `harness/verification/B8F1/manual-verification.md` ⇒ ⇒ ⇒ ⚠️ R-2 属「门禁偏离」类（宪法 v1.6.0）⇒ **不**计入破冻结面追认额度 ⇒ ⇒ ⇒ **确认动作并入 T059 的同一次**（**不另开一次确认**）⇒ ⇒ ⇒ ✅ **备料已完成**（追认段落已落 `harness/verification/B8F1/manual-verification.md` §7.0 / §7.1 / §7.2）⇒ ⇒ ⇒ **签署**仍归 **T059**
- [X] T061 **备料 R-3 的追认段落**（下游承接 **D-1…D-5** 的跨 feature 文档接线 · **阻断合入**）⇒ 追认文字 MUST 落 `harness/verification/B8F1/manual-verification.md` ⇒ ⇒ ⇒ ⚠️ **本条不构成一次新的追认** ⇒ ⇒ ⇒ 追认确认**并入 T059 的同一次发起者确认**（宪法 v1.8.0「追认次数每 feature MUST ≤ 1 次」⇒ 跨 feature 文档改动属「破冻结面」类 ⇒ **不另计次**）
- [X] T062 写入下游承接条款（宪法 v1.8.0 接线通则 · **只接线 · 逐条最小改动** · MUST NOT 改动目标文件的其余内容）：`harness/features/B8F2_stream多模式流式.md` · `harness/features/B8F3_节点别名与context通道.md` · `harness/features/B11F1_Send动态fan-out.md` · `harness/features/B22F1_get_graph与draw_mermaid.md` · `harness/features/B23F1_draw_mermaid_png离线不阻断.md` · `harness/features/B25F1_双跑验收与迁移说明.md`
- [X] T067 把 `harness/demo/agent_loop.py` 的 **B1「工具循环」**与 **B2「tool_calls 形状」**两组 `soft(...)`（`:214-262` · `_B8F1_NOTE = "条件边路由求值未交付 —— 归 B8F1"`）改成**硬断言**（`eq(...)` / 断言形态）⇒ ⇒ ⇒ **删除** `_B8F1_NOTE` 的「未交付」措辞 ⇒ ⇒ ⇒ **拆分而不删**（保留「模型被调用 2 次」「`llm_calls == 2`」「`messages` 长度 == 4」「最终答案是 '7'」「`tool_calls` 结构」五条断言的**语义**）⇒ ⇒ ⇒ ⚠️ **时序**：MUST 在 **T012 / T013** 就位**之后**落地 ⇒ ⇒ ⇒ 该脚本 MUST 仍以退出码 **0** 结束 ⇒ ⇒ ⇒ **破冻结面 T-7**（并入**同一次**追认 · 追认次数仍 == **1**）
- [X] T068 **文档守卫断言**（**SC-019 / SC-020 / SC-026** 的**判定级覆盖** · 宪法原则 VI **v1.11.0 + v1.13.0**）：新建 `tests/runtime/test_manual_record_guard.py` ⇒ ⇒ ⇒ 断言 ① `harness/verification/B8F1/manual-verification.md` **存在**且正文**非空** ② 含「**fake 模型轮**」与「**真实模型轮**」两轮的**非空实测输出**（两段标题 + **非空**输出 ⇒ **MUST NOT** 只写「符合预期」）③ 含「**追认**」文字且**逐条**列出**破面全集 7 类**（**唯一事实源 = spec.md「Assumptions」的「破面全集 7 类」**：T-1 · 冻结断言 ①②④ · T-5 · T-6 · **T-7**）⇒ ⇒ ⇒ ⚠️ **MUST** 在 **T058…T061** 之后才转绿（⇒ **MUST NOT** 造成「永久红的 CI」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 「**写记录**」类任务（T058）与「**追认**」类任务（T059 / T060 / T061）**均不**构成判定覆盖 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ 守卫断言**MUST NOT** 与 **T018** 的契约守卫（§7 的 I-1…I-14）混在同一处（**T018** 在 Phase 2 ⇒ 其判据在本条之前不可绿）
- [X] T076 新建 `harness/verification/B8F1/acceptance.py`（**逐 feature 的一键验收脚本** · **A1…A10** · **零第三方依赖** · 退出码 `0` PASS / `1` FAIL / `2` 环境未就绪）⇒ ⇒ ⇒ 覆盖 **C8 fresh 读**（否定式）· **`path_map` 双形态 + 动态目标** · **`END` 终止**（含 **X-2** 的两处分叉）· **失败信号两态** · **多目标并行 / 去重 / 空序列 / `Send`** · **`__start__` 三情形 + 幂等** · **双参形态 + 不发 `UserWarning`** · **零新增面** · **差分组全绿** · **破面全集 7 类的回溯验证** ⇒ ⇒ ⇒ **MUST** 打印 `B8F1 acceptance: PASS|FAIL`（同 B13F1 的标记口径）⇒ ⇒ ⇒ 并在 `tests/runtime/test_conditional_edges.py` 加一条用例把它**真跑**（**`--skip-differential`** ⇒ 差分证据仍由 `tests/differential/test_parity_probe.py` 独立承担）⇒ ⇒ ⇒ **纳入 CI 的常驻门禁**（脚本与实现漂移 ⇒ 用例**立刻红**）
- [X] T063 [P] 在 `README.md` 的「**API 兼容矩阵**」章节显式记录「本 feature **零新增**公开 API 行」· 并复核 `THIRD_PARTY_NOTICES` **零新增**（原则 X）
- [X] T064 提交前自检：**零改动清单**（MUST NOT 改动 `harness/demo/target.py` · `tests/differential/spec_builder.py` · `tests/differential/test_differential.py` 的 V-4 与冻结断言 ③）· 追溯表**双向**无空缺 · 无占位符 · 门禁编号仍 **30** · `vars(compiled)` 仍 **11** 键
- [X] T065 复核 `specs/b8f1-conditional-edges-fresh-read/plan.md` 的**登记项 R-4**（Phase 0 的 **9** 处事实性更正已回写 spec · **判据零放宽** · FR / SC / 裁定 / 引文差异 / P / X 的编号与总数**零变动**）

**Checkpoint**: 全部门禁落地 · 追认完成 ⇒ 可合入

---

## Dependencies & Execution Order

### 执行闸口（Phase 闸口 · 每道 MUST 全绿才进下一 Phase）

| 闸口 | 触发点 | MUST 验证 | 关联判据 |
|---|---|---|---|
| **G0** | Phase 1 结束（**T001** 落地后） | 绿基线**已记录**（用例计数 / 跳过数 / 失败数 / 跑测时刻）⇒ **MUST NOT** 在此之前改任何源码 | FR-026 · FR-037 · SC-002 · SC-016 |
| **G1** | Phase 2 结束 | `pytest tests/runtime/ tests/facade/ -ra` **全绿**（路由求值内核就位 · **7 类**破面已回溯修订（含 **T069** 的上游文档回溯修订）· 变红清单已**实测化**） | FR-002 · FR-026 · FR-037 · SC-002 · SC-016 |
| **G2** | Phase 3–8 结束 | `pytest tests/ -ra` **全绿**（**含差分组** · 上游缺席即 `skip`） | SC-001 … SC-026（除 SC-015 / SC-019 / SC-020 / SC-025 / SC-026） |
| **G3** | Phase 9 中段 | 既有门禁脚本 **G21–G30** 逐条**退出码 0**（命令形态见 `quickstart.md` §0）⇒ 门禁编号**仍为 30** | FR-037 · SC-016 · SC-018 |
| **G4** | Phase 9 末段 | **文档守卫断言**（**T068**）**全绿** ⇒ ⇒ ⇒ `harness/verification/B8F1/manual-verification.md` **存在且正文非空**（五段式 + 来源覆盖表 + 两轮**非空**实测输出 + 追认文字含破面全集 **7** 类） | FR-034 · FR-042 · SC-019 · SC-020 · SC-026 |
| **G5** | 合入前 | **一次**发起者追认**全部完成**（**R-1 / R-2 / R-3** 三段落列于同一份记录 · **确认动作 == 1 次** · 破面 **7** 类 ⇒ **同一次**追认）⇒ 追认次数 == **1** | FR-034 · FR-037 · SC-019 |

> **📌 编号消歧**（四套编号 · 同名不同义）：本表的 **G0–G5** 是「**执行闸口**」；
> `quickstart.md` 的 **V1…V16** 是「**验收闸口**」（无连字符）；
> `data-model.md` §5 与契约 §6.2 的 **V-8** / **V-27…V-31** 是「**校验规则**」（连字符）；
> 宪法门禁是 **G1–G30** ⇒ **四套编号互不撞名** ⇒ 引用时 MUST 带限定语。

### MUST 由发起者亲自出面的闸口（实现阶段只能「备料」，不得代劳）

- **T059 —— 登记项 R-1（破冻结面 7 类 · 唯一一次追认）**：破面全集 = **T-1**（V-8 守卫）·
  冻结断言 **① ② ④** · **T-5**（C8 挂载点）· **T-6**（A5 组软断言）· **T-7**（`agent_loop.py` 的 B1 / B2 组软断言）
  ⇒ ⇒ ⇒ 实现 MUST **停下来等追认**，**MUST NOT** 代签
  ⇒ ⇒ ⇒ 追认文字 + 发起者确认 + 日期 MUST 落
  `harness/verification/B8F1/manual-verification.md`
  ⇒ ⇒ ⇒ **未追认前 MUST NOT 合入** ⇒ 追认次数 MUST == **1**。
- **T060 —— 登记项 R-2（门禁的分阶段延后）**：门禁 3 的「`harness/demo/target.py` 原样可跑」
  ⇒ 承接方 **B22F1 + B23F1（M2）**；门禁 5 + 原则 V 的「**真实模型一轮**」
  ⇒ 承接方 **B25F1（M4）** ⇒ ⇒ ⇒ 追认文字 MUST 落同一份手工验证记录
  ⇒ ⇒ ⇒ **MUST NOT** 用「未验证」替代「**已登记的环境偏离**」⇒ **MUST NOT** 代签。
- **T061 —— 登记项 R-3（跨 feature 文档接线）**：下游承接 **D-1…D-5** 的**只接线 · 逐条最小改动**
  落在 **6** 份提示词初稿上 ⇒ ⇒ ⇒ 属「破冻结面」类 ⇒ **MUST** 由发起者追认
  ⇒ ⇒ ⇒ **MUST NOT** 代签 ⇒ ⇒ ⇒ **MUST NOT** 改动目标初稿的其余内容
  ⇒ ⇒ ⇒ ⚠️ **本条只备料 · 不另开确认** ⇒ ⇒ ⇒ 追认确认**并入 T059 的同一次**（**不另计次**）。

> **📌 三项追认的共同落点**：`harness/verification/B8F1/manual-verification.md`
> ⇒ ⇒ ⇒ **MUST NOT** 由实现者代签 ⇒ ⇒ ⇒ **未追认前 MUST NOT 合入**。
> ⇒ ⇒ ⇒ ⚠️ **全 feature 的发起者确认动作 == 1 次**（三段落列 · 一次确认 · 一个日期）——
> ⇒ ⇒ ⇒ 宪法 v1.8.0「追认次数每 feature MUST ≤ 1 次」⇒ 跨 feature 文档改动属「破冻结面」类
> ⇒ ⇒ ⇒ ⇒ **R-3 不另计次**；R-2 属「门禁偏离」类（宪法 v1.6.0 · 未设次数上限）⇒ **不**计入破冻结面额度。

### Phase Dependencies

- **Setup（Phase 1）**：无依赖 —— 可立即开始；**T001 阻断其余全部任务**
- **Foundational（Phase 2）**：依赖 Setup —— **阻塞全部用户故事**（**T069** 的上游文档回溯修订与 **T070** 的 `Send` 复用实现**同属**本 Phase）
- **用户故事（Phase 3–8）**：全部依赖 Phase 2 完成 ⇒ 之后可**并行**（若人手够）
  或按 **P1 → P1 → P1 → P2 → P2 → P3** 顺序
- **Polish（Phase 9）**：依赖全部目标用户故事完成 ⇒ ⇒ ⇒ **T055 / T067**（软 ⇒ 硬）另依赖 **T012 / T013** ⇒ ⇒ ⇒ **T068**（文档守卫断言）另依赖 **T058 / T059 / T060 / T061**
- **T066（实测化）属 Phase 2 末**（依赖 **T005 / T006 / T019 / T020 / T021** · 全部在 Phase 2）⇒ ⇒ ⇒ **MUST NOT** 排在 Phase 9
- **T069（上游文档回溯修订）属 Phase 2**（破冻结面 **T-1** 的 ②③④ 三处）⇒ ⇒ ⇒ **MUST** 在 **T059**（唯一一次追认）之前落地
- **T070（`Send` 复用实现）属 Phase 2** ⇒ ⇒ ⇒ **T049**（其断言）须等它
- **T074（`UserWarning` 不发的判定）属 Phase 2**（与 T015 同族 · 同文件 ⇒ 合入串行）⇒ ⇒ ⇒
  **T015** 只覆盖「跳过注入」的**行为** ⇒ ⇒ ⇒ 「**不发** `UserWarning`」的判定**独立成条**（归偏离 **X-5**）
- **T072（`None` / `START` 查表优先）属 Phase 6（US4）** ⇒ ⇒ ⇒ **T073**（非 `str` 可哈希值）属
  Phase 4（US2）⇒ ⇒ ⇒ **T071 / T075**（空序列 / 重复目标去重）属 Phase 7（US5）
  ⇒ ⇒ ⇒ **五条**均为 analyse 轮新增的**补覆盖**用例任务 ⇒ ⇒ ⇒ **零新增破面**（追认次数仍 == **1**）

### User Story Dependencies

- **US1（P1 · MVP）**：Phase 2 后可开始 —— **不依赖**其他故事
- **US2（P1）**：Phase 2 后可开始 —— 与 US1 **无依赖**（list / dict 两形态各自独立可测）
- **US3（P1）**：Phase 2 后可开始 —— 与 US1 **无依赖**（`END` 终止独立可测）
- **US4（P2）**：Phase 2 后可开始 —— **依赖 US1 的 fresh 读口径**（失败信号在 fresh 读之后抛出）
  ⇒ 但**仍可独立测试**（自带最小图）
- **US5（P2）**：Phase 2 后可开始 —— **依赖 US1 的 fresh 读口径**（多目标共享同一份 fresh 视图）
  ⇒ 但**仍可独立测试**
- **US6（P3）**：Phase 2 后可开始 —— **独立**（零副作用断言不依赖任何故事的行为面）

### Within Each User Story

- **测试 MUST 先写且 MUST 先失败**（本 feature 的测试即判据）—— 实现任务**不标** `[P]`
  ⇒ 实现**不得**与同阶段的测试任务并行起草（实现须等测试先红）；**合入顺序**：测试先红 → 实现 → 转绿
- 底座（Phase 1–2）→ fresh 读（US1）→ 两形态（US2）→ `END`（US3）→ 失败信号（US4）
  → 多目标（US5）→ 零副作用（US6）→ 取证与自检（Phase 9）
- Story complete before moving to next priority

### Parallel Opportunities

> **📌 并行纪律**：**同文件**的多条任务 **起草可并行**、**合入 MUST 串行**（一次提交）
> ⇒ 否则并行编辑会互相覆盖（沿用 B5F2 的「同文件一律串行」纪律 · 2026-11-10 补登记）。

- **Phase 1**：**T002 · T003 · T004** 可并行（**三个不同文件**）；**T001 不在上列**
  —— 它**阻断**全部后续任务（绿基线必须先取）
- **Phase 2**：**T015 / T016 / T017 / T074**（`tests/runtime/test_conditional_edges.py`）·
  **T018**（`test_conditional_edge_contract.py`）· **T019**（`test_superstep_basic.py`）·
  **T020**（`test_superstep_contract.py`）· **T021**（`test_compiled_graph.py`）·
  **T022**（`parity_probe.py`）· **T023**（`test_conditional_edge_surface.py`）
  ⇒ **八个不同文件** ⇒ 可并行**起草**；⚠️ **T015 / T016 / T017 / T074 同文件** ⇒ **合入串行**
  ⇒ **T005…T014 / T070**（实现层）**不标** `[P]`（同属内核 ⇒ 依赖未完成的前序任务）
  ⇒ **T069**（**上游文档**回溯修订 · 3 份 `specs/b7f1-*` 文档）⇒ 可与上述**并行起草**
  ⇒ ⇒ ⇒ 但**合入 MUST 在 T059（追认）之前**
- **US1**：**T024 / T025 / T026 / T027 / T028** 可并行起草；⚠️ **T024 / T027 / T028 同文件**
  ⇒ 合入串行；**T029 不在上列**（须等同阶段的测试先红）
- **US2**：**T030 / T031 / T032 / T033 / T073** 可并行起草（**同文件** ⇒ 合入串行）；**T034** 须等它们
- **US3**：**T035 / T036 / T037 / T038** 可并行起草（**同文件** ⇒ 合入串行）；**T039** 须等它们
- **US4**：**T040 / T041 / T042 / T072** 可并行起草（**同文件** ⇒ 合入串行）；**T043** 须等它们
- **US5**：**T044…T048 / T071 / T075** 可并行起草（**同文件** ⇒ 合入串行）；**T049** 须等它们
- **US6**：**T050 / T051 / T052** 可并行起草（**同文件** ⇒ 合入串行）；**T053** 须等它们
- **Phase 9**：**T063** 可并行（`README.md`）；**T054…T062 / T064 / T065 / T067 / T068** 依**时序**串行
  （**T055 / T067** 须等 **T012 / T013**；**T058** 须等 **T056 / T057 / T067**；
  **T059…T061** 须等 **T058** 的记录骨架就位；**T068** 须等 **T058…T061** 全部就位）

---

## Parallel Example: User Story 1

```bash
# 起草层并行（不同文件）
Task: "在 tests/runtime/test_conditional_edges.py 写 C8 fresh 读的否定式回归用例"
Task: "在 tests/runtime/test_read_fresh.py 写归约型通道与无值覆盖型通道缺席的 fresh 读用例"

# 实现 MUST 等测试先红
Task: "在 src/freegraph/runtime/_routing.py 实现 fresh 读调用（显式传 fresh=True）"
```

---

## Parallel Example: User Story 5

```bash
# 起草层并行（同文件的**不同用例段** · 合入 MUST 一次提交）
Task: "在 tests/runtime/test_conditional_edges.py 写返回序列的多目标并行用例"
Task: "在 tests/runtime/test_conditional_edges.py 写 Send 的逐目标载荷用例与同轮双源用例"

# 判定层依赖既有构造器（须串行）
Task: "在 src/freegraph/runtime/_routing.py 复用 B11F1 的 validate_send() / make_fanout()"
```

---

## Implementation Strategy

### MVP First（User Story 1 Only）

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational（CRITICAL - blocks all stories）
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: 跑 `pytest -q tests/runtime/test_conditional_edges.py`
   ⇒ 路由函数**看到了**本节点刚写入的值 ⇒ **MVP 达成**
   （`path_map` 双形态 / `END` / 失败信号 / 多目标可延后）
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **C8 独立回归测试**可判定（SC-001）
3. Add User Story 2 → Test independently → `path_map` 双形态可判定（SC-005）
4. Add User Story 3 → Test independently → `END` 终止可判定（SC-003 · 偏离 **X-2**）
5. Add User Story 4 → Test independently → 失败信号**两态**可判定（SC-006 / SC-007）
6. Add User Story 5 → Test independently → 多目标 fan-out 可判定（SC-008）
7. Add User Story 6 → Test independently → 零副作用守住（SC-017 / SC-018）
8. 每个故事增量交付，**不破坏**前面的故事

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 → User Story 2
   - Developer B: User Story 3（`END` 终止 · 偏离 **X-2**）
   - Developer C: User Story 4（失败信号两态）→ User Story 5
3. Stories complete and integrate independently
   ⚠️ US4 / US5 的断言**依赖 US1 的 fresh 读口径** ⇒ Developer A 的进度**是**关键路径

---

## 附录 · 任务 ↔ spec 追溯表

> **反向覆盖**：**FR 42/42 · SC 26/26** —— 每个 FR 与每个 SC **至少**被一条任务映射；
> **反向亦然**：每条任务携带的义务 MUST 挂上**至少一条 FR**（⇒ 追溯表**双向**齐全 · 宪法原则 VI）。
> ⚠️ **两张追溯表的关系不同**（2026-11-18 · analyse 轮补登记 · 消歧）：
> **spec 的「追溯表（FR → SC）」= 需求 → 判据**（每条 FR 由哪些 SC 判定）
> ⇒ **tasks 的本附录 = 任务 → (FR, SC)**（每条任务承载哪些 FR 与 SC）
> ⇒ ⇒ ⇒ 二者**不是同一关系** ⇒ ⇒ ⇒ 本附录里出现「spec 追溯表未列」的 SC 组合**不构成矛盾**
> ⇒ ⇒ ⇒ 但**覆盖判定以本附录为准**（FR 42/42 · SC 26/26 · 双向无空缺）。
> （宪法原则 VI：「tasks MUST 逐条勾选、**可追溯到 spec 条目**」）
> ⚠️ **※ 标记**（2026-11-17 analyse 轮）：标 ※ 的任务是「**写记录**」/「**追认**」/「**审计**」类 ——
> 按宪法原则 VI **v1.11.0 + v1.13.0**，它们**产出产物**但**不**构成**判定覆盖** ⇒ ⇒ ⇒ 判定载体见 ※ 行内的「判定」列。

| 任务 | FR | SC | 说明 |
|---|---|---|---|
| T001 | FR-026 · FR-037 | SC-002 · SC-016 | **绿基线**实测（写回 plan 的「绿基线记录」表）⇒ ⚠️ 「变红清单」的**实测化归 T066**（本条**不含**实测化） |
| T002 | FR-032 · FR-033 | SC-013 · SC-014 · SC-017 · SC-018 | 上游取证环境与版本钉死（`upstream-parity.md` §1.1） |
| T003 | FR-026 · FR-037 | SC-002 · SC-016 | 变红清单的**候选**定位（**推理级**）⇒ ⇒ ⇒ **实测化归 T066**（本条在源码未动时**实测不出变红**） |
| T004 | FR-034 | SC-001 · SC-014 | C8 回归用例的**骨架**（住 `tests/runtime/` · 门禁 G2） |
| T005 | FR-002 · FR-026 | SC-002 · SC-013 · SC-016 | 移除 V-8 守卫（破冻结面 **T-1**） |
| T006 | FR-026 · FR-027 · FR-037 | SC-002 · SC-016 | L3 接线 ⇒ `GraphSpec.conditional_edges` 填值（**11** 键不破）⇒ ⚠️ 接线方式 = **给 `_graph_spec_from()` 加形参**（`GraphSpec` 是 frozen dataclass ⇒ **MUST NOT** 构造后赋值） |
| T007 | FR-002 · FR-014 · FR-033 | SC-002 · SC-013 · SC-016 · SC-017 · SC-018 | 新建 L2 私有模块 `_routing.py`（**零公开面**） |
| T008 | FR-003 · FR-023 | SC-001 · SC-012 · SC-020 · SC-021 | 路由函数的**调用形态**（按参数名 `config` 判别） |
| T009 | FR-015 · FR-016 · FR-017 · FR-018 · FR-019 · FR-020 · FR-024 · FR-025 | SC-003 · SC-005 · SC-006 · SC-007 · SC-008 · SC-013 | **目标解析**（dict / `None` / 序列 / `END`） |
| T010 | FR-021 · FR-022 · FR-025 | SC-006 · SC-007 · SC-013 | 失败信号**两态**（`KeyError` / `ValueError` · 零新增错误类型） |
| T011 | FR-007 · FR-008 · FR-009 · FR-010 · FR-011 · FR-012 · FR-013 | SC-004 · SC-010 | **fresh 读**（唯一实现点 · 显式 `fresh=True` · 零污染） |
| T012 | FR-001 · FR-002 · FR-004 · FR-005 · FR-031 | SC-001 · SC-002 · SC-009 · SC-012 · SC-013 · SC-016 | 接入**阶段 ③′**（每源每条各求值一次 · 与 `Command.goto` 取并集） |
| T013 | FR-005 · FR-028 | SC-002 · SC-011 · SC-016 | 用**既有的动态边载体**投递（路由通道零写入） |
| T014 | FR-038 · FR-039 | SC-022 · SC-023 | `__start__` 条件边求值（**阶段 ① 之前**）⇒ ⚠️ 幂等标记 = **`"__start__" in state.dynamic_edges`**（键存在性 · **MUST NOT** 新增 `SchedulerState` 字段） |
| T015 | FR-003 | SC-001 · SC-020 · SC-021 | 双参形态的判定用例（**原始 `config`** 逐字）⇒ ⚠️ 「**不发** `UserWarning`」的判定归 **T074** |
| T016 | FR-038 · FR-039 | SC-022 · SC-023 | `__start__` 条件边的判定用例（三情形） |
| T017 | FR-040 | SC-024 | **branch 名唯一**的判定用例（消息点名分支名与源节点） |
| T018 | FR-014 · FR-034 | SC-001 · SC-013 · SC-014 · SC-016 | **契约守卫**（解析契约 §7 的 **I-1…I-14** 并逐条断言） |
| T019 | FR-026 · FR-037 | SC-002 · SC-016 | 回溯修订**冻结断言 ①**（拆分而不删 · = plan 变红清单 ① + ②）⇒ ⚠️ 既有 docstring 的 `SC-025` 属 **B7F1 编号域** ⇒ MUST 加 feature 限定语 |
| T020 | FR-026 · FR-037 | SC-002 · SC-016 | 回溯修订**冻结断言 ②**（**I-14** 拆分 · 编号与槽位不变 · = plan 变红清单 ③）⇒ ⚠️ 不变式编号 **I-1…I-16** 属 **B7F1 编号域** ⇒ 引用 MUST 写全文件前缀 |
| T021 | FR-026 · FR-037 | SC-002 · SC-016 | 回溯修订**冻结断言 ④**（替换为反面断言 · = plan 变红清单 ④）⇒ `:111-114` 的 **11 键**断言 MUST 逐字不动 |
| T022 | FR-032 | SC-013 · SC-014 | 差分场景 **D-103…D-120**（**18** 条）落 `parity_probe.py`（**V-4 不破**）⇒ ⚠️ 落点 = **既有** `_scenarios()`（⇒ 判词 / `note` 守卫**自动覆盖**）⇒ ⚠️ 差分侧载荷派生 MUST 与 L3 **逐字一致** |
| T023 | FR-036 · FR-037 | SC-015 · SC-016 | **零新增面**断言（**7** / **23** / **21** / **11** 键 + `runtime.errors` 符号集合不变 + 未实现的 L1 协议方法仍抛 `NotImplementedError`） |
| T024 | FR-001 · FR-007 · FR-008 · FR-009 · FR-010 · FR-011 · FR-012 · FR-013 · FR-034 | SC-001 · SC-004 · SC-010 · SC-014 | C8 fresh 读的**否定式**回归用例 |
| T025 | FR-009 | SC-004 | **归约型**通道的 fresh 读用例（`["seed", "fresh"]`） |
| T026 | FR-011 · FR-013 | SC-004 · SC-010 | **无值覆盖型通道缺席**于路由入参（稀疏口径） |
| T027 | FR-008 · FR-010 | SC-004 | 同轮**另一**节点的写入**不可见** |
| T028 | FR-001 · FR-002 | SC-002 | **门面可观察**（`invoke` 上路由可见） |
| T029 | FR-001 · FR-002 · FR-003 · FR-007 · FR-008 · FR-009 · FR-010 · FR-011 · FR-012 · FR-013 · FR-034 | SC-001 · SC-002 · SC-004 · SC-010 · SC-014 · SC-020 · SC-021 | 每源每次**只求值一次** + fresh 读**零污染** + **路由成环** ⇒ `recursion_limit` ⇒ `GraphRecursionError`（不包装） |
| T030 | FR-016 | SC-005 | **list 形态** `path_map` 的路由用例 |
| T031 | FR-015 | SC-005 | **dict 形态** `path_map` 的路由用例 |
| T032 | FR-021 | SC-006 | dict 形态查表失败 ⇒ 内置 `KeyError` + 消息更详细 |
| T033 | FR-016 · FR-021 | SC-006 | list 形态查表失败 ⇒ 内置 `KeyError`（与 dict **同款**） |
| T034 | FR-014 · FR-016 | SC-005 · SC-013 | L3 的 list→`{name:name}` 归一化**不被** L2 重做 |
| T035 | FR-019 | SC-003 · SC-013 | 返回 `END` ⇒ 目标节点执行 **0** 次 |
| T036 | FR-019 | SC-003 · SC-013 | `path_map` 的 **value** 为 `END` ⇒ 同样终止 |
| T037 | FR-019 | SC-003 · SC-013 | `path_map` **不含** `END` 键 ⇒ **仍然终止**（偏离 **X-2**） |
| T038 | FR-019 | SC-003 · SC-013 | 返回序列 `[END, "a"]` ⇒ `END` 被**剔除** · 其余照常执行 |
| T039 | FR-019 | SC-003 · SC-013 | `path_map = {END: "b"}` ⇒ freegraph **单独返回** `END` ⇒ **无条件终止**（**D-118**） |
| T040 | FR-021 | SC-006 | 有 `path_map` + 非法返回值 ⇒ 内置 `KeyError`（**X-1**） |
| T041 | FR-017 · FR-022 | SC-007 | 无 `path_map` + 未注册节点名 ⇒ 内置 `ValueError`（**X-3**） |
| T042 | FR-023 | SC-012 | 路由函数**自身**异常 ⇒ 原始类型 + 原始消息 |
| T043 | FR-021 · FR-022 · FR-025 | SC-006 · SC-007 · SC-016 | 失败信号**两态**逐字一致 · **零新增错误类型** |
| T044 | FR-018 · FR-024 | SC-008 | 返回序列 ⇒ **多目标并行** fan-out |
| T045 | FR-018 | SC-008 | 两个目标收到的入参**逐字相等**（共享状态） |
| T046 | FR-030 | SC-008 | 返回 `[Send("b", payload)]` ⇒ 目标收到**载荷**（语义相异） |
| T047 | FR-028 | SC-011 | 同轮**两个源**路由到**同一目标** ⇒ 正常执行（不触发 V-6） |
| T048 | FR-004 · FR-006 | SC-009 | 条件边目标与**屏障组**不混用 · **同一源节点的多条条件边各求值一次 ⇒ 目标取并集（去重保序）** |
| T049 | FR-030 | SC-008 | 断言走 B11F1 的既有 `validate_send()` / `make_fanout()`（零新增 · **实现见 T070**） |
| T050 | FR-011 · FR-029 · FR-033 | SC-002 · SC-010 · SC-017 · SC-018 | 子进程断言 `sys.modules` 中**零上游** |
| T051 | FR-011 · FR-029 · FR-033 | SC-002 · SC-010 · SC-017 · SC-018 | **零出站**断言（socket 监测 · 只观测不阻断） |
| T052 | FR-011 · FR-029 · FR-033 | SC-002 · SC-010 · SC-017 · SC-018 | **零环境变量**断言（执行行为不因环境变量而改变） |
| T053 | FR-011 · FR-029 · FR-033 | SC-002 · SC-010 · SC-017 · SC-018 | 路由入参**不含** `context` 通道 · **不含**路由通道 · **`invoke` 的返回键集不含任何 `branch:to:*`** |
| T054 | FR-034 | SC-001 · SC-014 | C8 挂载点翻 `landed` + **新增** C8 元测试（路径扫描 · 零 import） |
| T055 | FR-035 · FR-036 | SC-015 | A5 组**软断言 ⇒ 硬断言**（⚠️ 有时序 · 不写永久红的 CI）⇒ ⚠️ 归 plan 的「**时序风险 ①**」（= spec 的 **T-6**）⇒ 对应行已**移出**变红清单（移出前为**第 6 行** · 现行 ⑥ = 差分侧守卫） |
| T056 | FR-032 | SC-013 · SC-014 | 取证 **D-103…D-120** 全绿 + 判词分布逐条一致 |
| T057 | FR-032 · FR-034 | SC-001 · SC-013 · SC-014 | 执行 quickstart 的 **V1…V16** 并回填实测输出 |
| T058 ※ | FR-003 · FR-034 | SC-026 | 人工验证记录（五段式 + **fake 轮实测输出** + **真实轮未落地**声明 + 来源覆盖表）⇒ **判定 = T068** |
| T059 ※ | FR-034 · FR-037 | —— | **发起者追认 R-1**（破冻结面 **7** 类 · 唯一一次 · 阻断合入）⇒ **判定 = T068** |
| T060 ※ | FR-034 · FR-037 | —— | **发起者追认 R-2**（门禁分阶段延后 · 阻断合入）⇒ **判定 = T068** |
| T061 ※ | FR-034 · FR-037 | —— | **发起者追认 R-3**（跨 feature 接线 · 阻断合入）⇒ **判定 = T068** |
| T062 | FR-002 · FR-003 · FR-007 · FR-009 · FR-011 · FR-013 · FR-025 | SC-002 · SC-010 · SC-014 | 写入下游承接条款（**D-1…D-5** · 六份提示词初稿 · 只接线）⇒ 落点 = spec「下游承接条款」表各行的 FR 列（D-1 → FR-002 · D-2 → FR-007/FR-009 · D-3 → FR-011 · D-4 → FR-013/FR-025 · D-5 → FR-003） |
| T063 | FR-037 | SC-016 · SC-018 | README 兼容矩阵「**零新增**公开 API 行」+ `THIRD_PARTY_NOTICES` 零新增 |
| T064 | FR-037 | SC-016 | 提交前自检（零改动清单 · 追溯表双向 · 门禁仍 **30** · **11** 键） |
| T065 | FR-030 · FR-032 | SC-013 | 复核**登记项 R-4**（Phase 0 的 **9** 处事实性更正已回写 spec）与 **R-6**（`Send` 失败信号的偏离正式化 · X-6 / X-7 · D-119 / D-120 ⇒ 落点 = FR-030 · FR-032） |
| T066 | FR-026 · FR-037 | SC-002 · SC-016 | **实测化**「变红清单」（宪法 v1.11.0 的基线义务 · MUST NOT 只凭推理登记）⇒ ⚠️ **MUST** 在 T005 / T006 / T019 / T020 / T021 / **T022** 之后（对象 = plan 变红清单的 **6 项**） |
| T067 | FR-041 | SC-025 | `harness/demo/agent_loop.py` 的 B1 / B2 组软断言 ⇒ **硬断言**（破冻结面 **T-7** · **EV-2 承接**）⇒ ⚠️ **MUST** 在 T012 / T013 之后 |
| T068 | FR-042 | SC-019 · SC-020 · SC-026 | **文档守卫断言**（记录存在 + 两轮**非空**实测输出 + 追认文字含破面全集 **7** 类）⇒ ⚠️ **MUST** 在 T058…T061 之后 |
| T069 | FR-026 · FR-034 | SC-016 | 回溯修订**上游已交付文档**（破冻结面 **T-1** 的 ②③④ 三处 · 宪法 v1.9.0 ① 的「契约 + spec」两面）⇒ ⚠️ **T-5** 的原第 ③ 处已**撤除**（b3f1 契约已是两态口径）⇒ ⇒ ⇒ **破面全集仍为 7 类** ⇒ ⇒ ⇒ ⚠️ SC-019 的**判定载体 = T068** |
| T070 | FR-030 | —— | 在 `_routing.py` **实现**路由返回 `Send` 时**复用** B11F1 的既有构造器（零新增 fan-out 机制）⇒ ⇒ ⇒ ⚠️ SC-008 的**判定载体 = T046 / T049** |
| T071 | FR-018 · FR-024 | SC-008 | 「返回**空序列** `[]` ⇒ **不报错** · 不触发任何目标 · 图自然收敛」（2026-11-18 · analyse 轮新增的补覆盖用例） |
| T072 | FR-025 | SC-006 · SC-007 | 「返回 `None` / `START` ⇒ **查表优先**的显式失败（两态）」+「`path_map` 含 `__start__` **键** ⇒ **不**失败」（2026-11-18 · analyse 轮新增的补覆盖用例） |
| T073 | FR-020 | SC-005 | 「返回**非 `str` 的可哈希值**（如 `int`）⇒ 作为 `path_map` 的 key **正常查表**」（2026-11-18 · analyse 轮新增的补覆盖用例） |
| T074 | FR-003 | SC-021 | 「注入被跳过时**不发** `UserWarning` ⇒ 按**一参**调用 ⇒ 内置 `TypeError`」（归偏离 **X-5** · 差分**三投影**不含 Python 警告 ⇒ 由**单元测试**锁定） |
| T076 | FR-034 | SC-001 · SC-013 · SC-016 | **逐 feature 的一键验收脚本**（`harness/verification/B8F1/acceptance.py` · **A1…A10**）⇒ ⇒ ⇒ 并在 `tests/runtime/test_conditional_edges.py` 加一条用例把它**真跑** ⇒ ⇒ ⇒ **纳入 CI 的常驻门禁** |
| T075 | FR-018 | SC-008 | 「返回**序列**且含**重复目标** ⇒ **去重保序**（同一目标**只**触发一次）」（2026-11-18 · analyse 轮新增的补覆盖用例） |

> **SC 反向覆盖核对**
> SC-001 → T004 / T008 / T012 / T015 / T018 / T024 / T029 / T054 / T057 / T076
> SC-002 → T001 / T003 / T005 / T006 / T007 / T012 / T013 / T019 / T020 / T021 / T028 / T029 / T050 / T051 / T052
>   T053 / T062 / T066
> SC-003 → T009 / T035 / T036 / T037 / T038 / T039
> SC-004 → T011 / T024 / T025 / T026 / T027 / T029
> SC-005 → T009 / T030 / T031 / T034 / T073
> SC-006 → T009 / T010 / T032 / T033 / T040 / T043 / T072
> SC-007 → T009 / T010 / T041 / T043 / T072
> SC-008 → T009 / T044 / T045 / T046 / T049 / T071 / T075
> SC-009 → T012 / T048
> SC-010 → T011 / T024 / T026 / T029 / T050 / T051 / T052 / T053 / T062
> SC-011 → T013 / T047
> SC-012 → T008 / T012 / T042
> SC-013 → T002 / T005 / T007 / T009 / T010 / T012 / T018 / T022 / T034 / T035 / T036 / T037 / T038 / T039 / T056
>   T057 / T065 / T076
> SC-014 → T002 / T004 / T018 / T022 / T024 / T029 / T054 / T056 / T057 / T062
> SC-015 → T023 / T055
> SC-016 → T001 / T003 / T005 / T006 / T007 / T012 / T013 / T018 / T019 / T020 / T021 / T023 / T043 / T063 / T064
>   T066 / T069 / T076
> SC-017 → T002 / T007 / T050 / T051 / T052 / T053
> SC-018 → T002 / T007 / T050 / T051 / T052 / T053 / T063
> SC-019 → T068
> SC-020 → T008 / T015 / T029 / T068
> SC-021 → T008 / T015 / T029 / T074
> SC-022 → T014 / T016
> SC-023 → T014 / T016
> SC-024 → T017
> SC-025 → T067
> SC-026 → T058 / T068

> ⇒ ⇒ ⇒ **判定载体**（**人工门禁类 SC**）：SC-019 / SC-020 / SC-026 ⇒ **T068**（文档守卫断言）·
> SC-025 ⇒ **T067**（`agent_loop.py` 硬断言）⇒ ⇒ ⇒ 「**写记录**」/「**追认**」类任务（T058 / T059 / T060 / T061）**不**构成判定覆盖（宪法原则 VI v1.11.0 + v1.13.0）。
