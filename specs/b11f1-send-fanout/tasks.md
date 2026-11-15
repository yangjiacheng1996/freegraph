---
description: "Task list for B11F1 · Send 的动态 fan-out / map-reduce"
---

# Tasks: B11F1 · `Send`：动态 fan-out / map-reduce

**Input**: Design documents from `/specs/b11f1-send-fanout/`
**Prerequisites**: plan.md（required）· spec.md（required · 用户故事）· research.md · data-model.md ·
contracts/（`send-contract.md` + `upstream-parity.md`）· quickstart.md

**Tests**: **包含**测试任务 —— spec FR-017 / SC-016 要求「纯单元可测 + 行/分支覆盖率 == 100%」
⇒ **MUST 先写 · MUST 先失败**（此时 fan-out 语义**尚未接线** ⇒ 断言**必然失败** ⇒ Phase 2 只出**骨架桩**）。

**Organization**: 按用户故事分组（**6** 个 · P1–P6）⇒ 每个故事可**独立实现、独立测试**。

---

## 格式：`[ID] [P?] [Story] 描述`

- **[P]**：可并行（不同文件 / 无未完成依赖）
- **[Story]**：所属用户故事（US1…US6）—— 仅**用户故事阶段**的任务带
- **每条任务 MUST 带确切文件路径**（本仓库约定）

## 路径约定

- 源码：`src/freegraph/runtime/`（L2 · 层注册表**目录条目** ⇒ **零注册表改动**）
- ⚠️ **新增内部模块**：`src/freegraph/runtime/_fanout.py`（**不进 `__all__`** ⇒ 导出面仍 **23**）
- 契约层：`src/freegraph/contracts/`（L1）· 门面：`src/freegraph/graph.py`
- ⚠️ **删除**：`src/freegraph/_primitives.py`（`Send` 迁入 L1 ⇒ 文件整体删除）
- 测试：`tests/runtime/`（运行期用例）· L1 契约用例可放 `tests/runtime/test_send_contract.py` **或** `tests/contracts/`（⚠️ **G2 只扫描 `src/freegraph/contracts/**`**，**不**限制 `tests/contracts/` 的 import）
- 差分：`tests/differential/`（**已存在** · 追加场景组）
- 人工验证：`harness/verification/B11F1/`
- 契约 / 规格：`specs/b11f1-send-fanout/` · `specs/b9f1-command-primitive/` · `specs/b12f1-concurrency-errors/` ·
  `specs/b1f1-contracts-core/` · `specs/b2f1-contracts-protocols/` · `specs/b2f2-public-api-facade/` ·
  `specs/b3f1-scaffold-ci-gates/`
- 上位文档：`harness/proposals/立项书.md` · `harness/proposals/上游对齐审计.md`
- 下游提示词：`harness/features/`（**只接线 · 逐条最小改动**）
- ⚠️ **设计决策的权威落点**：`specs/b11f1-send-fanout/research.md` **§3**（**D-01…D-11** · 内部形状与次序键的冻结）⇒ ⇒ 实施前**先读**它；
  实体与校验规则见 `data-model.md` · 运行期口径见 `contracts/send-contract.md`

---

**本 feature 的可测判据总表**（**24 FR + 22 SC ↔ 95 条任务**）—— **逐 SC 一行**：
追溯见文末「**附录 · 任务 ↔ spec 追溯表**」—— **每个 FR 与每个 SC 均至少被一条任务映射**
（**FR 24/24 · SC 22/22**）· **反向**：**每条任务**携带的义务 MUST 挂上**至少一条 FR**
⇒ 追溯表**双向**齐全（宪法原则 VI）。
> ⚠️ **本表 = 摘要**：**权威映射 = 文末「任务 ↔ spec 追溯表」** ⇒ 修改判据归属时 MUST **同步**两处
> ⇒ 本表已**逐行**由附录生成 ⇒ **两处 MUST NOT 漂移**。

**SC-001**（fan-out 次数 == `Send` 条数 · 各次入参正确（**A1**））由 **T021 · T022 · T056 · T057 · T091** 承载；
**SC-002**（产出按归约器汇合（**A2**））由 **T030 · T036 · T055** 承载；
**SC-003**（目标不存在 ⇒ 明确报错（**A3**））由 **T038 · T043 · T044** 承载；
**SC-004**（无 `Send` 时行为一字不变）由 **T045 · T046 · T047 · T048** 承载；
**SC-005**（混合调度可判定）由 **T049 · T050 · T052 · T053 · T054 · T056 · T059** 承载；
**SC-006**（入参形态 = arg 逐字）由 **T022 · T028** 承载；
**SC-007**（落点 = 下一轮）由 **T023 · T027 · T051** 承载；
**SC-008**（写入路径共用 + 派发与写入同时生效）由 **T030 · T033 · T035 · T036 · T055 · T058 · T074 · T094** 承载；
**SC-009**（确定性 · 可复现）由 **T031 · T032** 承载；
**SC-010**（并发语义同 B12F1）由 **T025** 承载；
**SC-011**（失败传播与原子性）由 **T034 · T037 · T074 · T093 · T094 · T095** 承载；
**SC-012**（载荷形态非法 ⇒ 显式失败）由 **T024 · T026 · T041 · T042** 承载；
**SC-013**（保留名与哨兵目标）由 **T039 · T040 · T091** 承载；
**SC-014**（层纪律）由 **T002 · T004 · T006 · T009 · T010 · T011 · T020** 承载；
**SC-015**（结构纪律 · 导出面 / 门禁编号）由 **T007 · T010 · T067 · T086** 承载；
**SC-016**（可测性 · 覆盖率 == 100%）由 **T003 · T004 · T085** 承载；
**SC-017**（人工验证记录）由 **T005 · T082 · T083 · T090** 承载；
**SC-018**（文档纪律 · 署名头 + 行号）由 **T088 · T089** 承载；
**SC-019**（差分场景组落地）由 **T060 · T061 · T062** 承载；
**SC-020**（破冻结面 + 发起者追认）由 **T063–T074 · T093–T095 · T084** 承载；
**SC-021**（依赖隔离 · 零出站）由 **T020 · T087** 承载；
**SC-022**（执行记录口径）由 **T029 · T033 · T046 · T074 · T094 · T095** 承载。

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 工程准备 + 骨架 + **绿基线**（FR-022 的**基线义务**）

- [X] T001 跑既有测试套件（`.venv/bin/python -m pytest -q`）并把**绿基线**计数（**1184 passed / 4 skipped**）写进 `harness/verification/B11F1/manual-verification.md` 的「环境」段（**若文件尚未创建 ⇒ 先建最小骨架**；T005 再补齐五段式）⇒ FR-022 · plan §Technical Context
- [X] T002 [P] 创建 `src/freegraph/runtime/_fanout.py`：**私有**模块骨架（署名头逐字 + 模块 docstring 为首个语句 + 空实现）⇒ FR-012 · SC-014
- [X] T003 [P] 创建 `tests/runtime/test_send_fanout.py`：署名头 + 模块 docstring + **手写图规格**夹具（构造 `GraphSpec` / `NodeSpec` / `run_super_steps` 的辅助函数）⇒ FR-017 · SC-016
- [X] T004 [P] 创建 `tests/runtime/test_send_contract.py`：署名头 + 模块 docstring + L1 侧断言骨架 **+ 门面转出同一性断言（`freegraph.graph.Send is freegraph.contracts.Send` · 导出名不变 · 字段/构造/哈希形态逐字不变）** ⇒ FR-012 / FR-017 · SC-014 / SC-016
- [X] T005 创建 `harness/verification/B11F1/acceptance.py`（机械层一键验收骨架）与 `harness/verification/B11F1/manual-verification.md`（**五段式**骨架：环境 / 步骤 / 实际输出 / 结论 / 遗留问题；**若 T001 已建最小文件则在其上补齐**）⇒ FR-016 · SC-017

---

## Phase 2: Foundational（阻塞性前置 · 骨架）

**Purpose**: **L1 的类型落位** + **运行期的内部形状与任务标识** —— 所有故事都依赖它

**⚠️ CRITICAL**: 未完成本 Phase 前，**任何用户故事**都不能开工

- [X] T006 把 `Send` 的类型定义迁入 `src/freegraph/contracts/types.py`（**裁定 11** · **H-3** · **PR-1**）（`@dataclass(frozen=True, slots=True)` · 字段 `node: str` / `arg: Any` · **显式** `__hash__ = None` · **刻意不用** `kw_only=True`（位置参数合法）⇒ **定义在 `Command` 之前**）并更新该模块 docstring（「四个核心类型」→ 五个）⇒ FR-012 · SC-014 · data-model §2
- [X] T007 在 `src/freegraph/contracts/__init__.py` 导出 `Send`（`__all__` **20 → 21**）**并更新模块 docstring**（「本层不导出 Send」已过时 ⇒ 改为导出 `Send`）⇒ FR-014 · SC-015
- [X] T008 放宽 `src/freegraph/contracts/types.py` 的 `Command.goto` 注解为 `str | Send | Sequence[str | Send] | None`（**保留 `None` 缺省**）**并同步 `Command` docstring 的 `goto` 字段表** ⇒ FR-012 / FR-014 · contracts §6.2
- [X] T009 放宽 `src/freegraph/contracts/protocols.py` 的 `NodeFunc.__call__` 返回联合（**增补** `Send` / `list[Send]` / `tuple[Send, ...]` ⇒ 七形态）并更新其 docstring **+ 增补「经 `Send` 调用的节点入参 = `arg` 原样（可为非 `dict` / `None`）；C5 的稀疏 `dict` 注记只适用于标准触发 / `goto`」**（F-11 · H3）⇒ FR-003 / FR-012 / FR-014 · SC-014 · contracts §6.3
- [X] T010 在 `src/freegraph/graph.py` 改为从 **L1** 转出 `Send`（`from .contracts import Command, RunConfig, Send` · 删除 `from ._primitives import Send`）并更新模块 docstring（`_primitives` 的引用）⇒ FR-012 · SC-014 / SC-015
- [X] T011 删除 `src/freegraph/_primitives.py`（`Send` 已迁出 ⇒ 文件整体删除）⇒ FR-012 · SC-014
- [X] T012 在 `src/freegraph/runtime/_fanout.py` 定义内部形状 `_FanOutTask`（**裁定 6** · **PR-6**）（`target` / `arg` / `index` / **`suppresses_static`**）与 `_FanOut`（**`producer`** / `tasks` / **`suppresses_static`**）⇒ ⚠️ **判定口径**：`_FanOutTask.suppresses_static` = **归一形状的载体信息源**（逐任务携带 · 同一执行内全部同值）；`_FanOut.suppresses_static` = **抑制判定的唯一聚合源**（MUST 由其 `tasks` 的载体标志聚合而来）⇒ **载体 B 抑制按 `(producer, target)` 匹配** ⇒ FR-005 / FR-006 · data-model §3.1
- [X] T014 在 `src/freegraph/runtime/_fanout.py` 定义 **TaskId**（**裁定 6** · **PR-4** · 分析轮补问 **Q4**（2026-11-14）· 2026-11-14 复核更正）：**`int` = 本轮任务的规范序号（0 起）**，按 **FR-005 的上游任务序**分配（标准触发任务按目标节点名序 → fan-out 任务按产生者 TaskId 序 · `Send` 序号）⇒ 排序键 = TaskId 本身 ⇒ FR-005 / FR-010 · research D-01
- [X] T013 在 `src/freegraph/runtime/superstep.py` 把归一形状扩为（**裁定 1 / 6** · **PR-5 / PR-6**） `{"writes", "gotos", "fanout"}`（`_FanOutTask` **逐任务携带 `suppresses_static`**）并给 `SchedulerState` **新增一个**带缺省值的字段 `fanout: dict[TaskId, _FanOut] = field(default_factory=dict)`（**按产生者任务**记录 · 不是按节点名 · `_FanOut` **带 `producer`** ⇒ `SchedulerState()` 的**构造签名逐字不变**）⇒ ⚠️ **依赖 T012 / T014**（先 T012、T014，再 T013）⇒ FR-002 / FR-005 / FR-006 · research D-03 / D-05
- [X] T015 在 `src/freegraph/runtime/_concurrency.py` 把结果槽的**键**由节点名改为 **TaskId**（**裁定 4 / 8** · **H-4** · **PR-4 / PR-6**）（`outcomes: dict[TaskId, _TaskOutcome]`；`TaskId` 从 `_fanout.py` import ⇒ **避免 `_concurrency ↔ superstep` 循环依赖**）并给 `_TaskOutcome` **增一个** `fanout` 字段 ⇒ FR-004 / FR-009 / FR-010 · research D-02 / D-05
- [X] T016 在 `src/freegraph/runtime/superstep.py` 的 `_run_round` 里把本轮任务集合改为（**裁定 2** · **H-1**）「标准任务 + fan-out 任务」并按 **TaskId** 排序（阶段 **②′** 骨架）⇒ FR-002 / FR-004
- [X] T017 在 `src/freegraph/runtime/_fanout.py` 实现 fan-out 任务的构造（**裁定 2 / 3**）（目标节点 + **arg 逐字**）⇒ FR-003 / FR-004
- [X] T018 在 `src/freegraph/runtime/superstep.py` 的**触发组枚举层**加「载体 B 抑制」的骨架（**裁定 5**）（**单元素**边触发组才抑制 · **按 `(producer, target)` 精确匹配** ⇒ 其它 producer 的静态边不抑制 · 多源屏障组不抑制）⇒ FR-006 · research D-04
- [X] T019 核验 `src/freegraph/runtime/superstep.py` 的 `SchedulerState.to_checkpoint` **不含** `fanout`（载荷含用户对象 ⇒ 不落盘）⇒ FR-020 · research D-08 · I-12
- [X] T020 跑门禁 `harness/scripts/gates/gate_G21_dependencies.py`（依赖）/ `gate_G25_import_graph.py`（导入图）/ `gate_G30_attribution.py`（署名头）确认层纪律与纯净性**未破** ⇒ FR-013 · SC-014 / SC-021

**Checkpoint**: 骨架就绪 —— 用户故事可开工

---

## Phase 3: User Story 1 - 同一个节点被多次调用，每次拿到不同的任务（Priority: P1）🎯 MVP

**Goal**: 节点返回 `Send` / `list[Send]` ⇒ 目标节点**被调用 N 次**，每次入参**逐字**等于各自的 `arg`

**Independent Test**: 一个节点返回 `[Send("worker", {"n": 1}), Send("worker", {"n": 2})]` ⇒ 断言
① `worker` 被调用 **2** 次；② 两次入参分别是 `{"n": 1}` 与 `{"n": 2}`（**手写图规格** · 未经构建器）

### Tests for User Story 1（MUST 先写 · MUST 先失败）

- [X] T021 [US1] 在 `tests/runtime/test_send_fanout.py` 写「fan-out 执行次数 == `Send` 条数」用例（载体 B · 同目标两个 `Send`）**+「`Send` 指向**产生者自己**（自投）⇒ 下一轮以 arg 再跑一次（**用例 MUST 传小 `max_steps` 或构造终止图**，不得依赖无限跑）」** ⇒ FR-002 / FR-004 · SC-001
- [X] T022 [US1] 在 `tests/runtime/test_send_fanout.py` 写「各次入参**逐字**等于各自 `arg`」用例 **+「`arg` 为**任意对象**（含 `None` / 非 dict）⇒ **逐字**传递 · **不校验**」** ⇒ FR-003 / FR-008 · SC-001 / SC-006
- [X] T023 [US1] 在 `tests/runtime/test_send_fanout.py` 写「fan-out 任务在**下一轮**执行（产生它的同一轮执行次数 == 0）」用例 **+「载荷**一次性**：执行后**再下一轮不重复触发**」+「产生者**再次执行**且不再产生 `Send` ⇒ 旧的 fan-out **被清空**（**无幽灵 fan-out**）」** ⇒ FR-002 · SC-007
- [X] T024 [US1] 在 `tests/runtime/test_send_fanout.py` 写「载体 B 的载荷归一（单个 `Send` / `list[Send]` / `tuple[Send, ...]`）」用例 ⇒ FR-001 · SC-012
- [X] T025 [US1] 在 `tests/runtime/test_send_fanout.py` 写「fan-out 任务受 `max_concurrency` 约束（=1 ⇒ 不重叠 · =N ⇒ 可重叠）」用例 **+「连续 ≥10 轮 fan-out 运行后进程内线程数不增长（复用 B12F1 线程池 · 零悬挂线程）」** ⇒ FR-009 · SC-010

### Implementation for User Story 1

- [X] T026 [US1] 在 `src/freegraph/runtime/superstep.py` 实现载体 B 的返回值归一（**裁定 1 / 9**）（`Send` / `list[Send]` ⇒ 归入 `fanout` 键；空列表 / 混合列表 / 元素非 `Send` ⇒ 内置 `TypeError`）⇒ FR-001 / FR-008 · SC-012
- [X] T027 [US1] 在 `src/freegraph/runtime/superstep.py` 实现阶段 **②′**（**裁定 2** · **H-1 / H-2**）：按**产生者 TaskId 序 + 载荷内 `Send` 序号**把 `state.fanout` 里的每个 `_FanOutTask` 变成下一轮的任务（**不消费**任何触发源版本）⇒ 构造后**清空**旧载荷（**一次性** · 上游 `TASKS` 每步清空）；**同时**把 `src/freegraph/runtime/_interrupt.py` 的**任务级现场键**由节点名改为**任务标识（TaskId）**（含 `bind_task` / `prepare_task` 与 `superstep.py` 的 `by_name` 构造；**持久化 `task_id` 的口径见 T093 / F-13**）⇒ 同节点 N 次 fan-out **各自独立** · 与 **B10F1** 的恢复口径对齐（**MUST NOT** 破坏既有 resume 语义）⇒ FR-002 / FR-004 / FR-009 · SC-007 · **PR-12 / DR-01 / F-13**
- [X] T028 [US1] 在 `src/freegraph/runtime/superstep.py` 实现 fan-out 任务的入参 = **`arg` 逐字**（**裁定 3**）（**不经稀疏读** · **不按订阅过滤**）⇒ FR-003 · SC-006
- [X] T029 [US1] 在 `src/freegraph/runtime/superstep.py` 实现落回（**裁定 13** · **PR-6**）：`node_versions[目标]` 按**成功执行次数**递增（**+N**）· `dynamic_edges` 取 **TaskId 序最后一个**任务的产出 · **新产生的 `fanout` 载荷按产生者 TaskId 记入**（`_FanOut.producer = 产生者节点名` · 供下一轮抑制匹配与消费）；`executed` **逐次列出**（同节点可重复 · 顺序 = TaskId 序）⇒ FR-010 · SC-022

**Checkpoint**: User Story 1 可独立验收（**MVP**）

---

## Phase 4: User Story 2 - fan-out 的产出按归约器汇合（Priority: P2）

**Goal**: 多个 fan-out 调用的写入按归约器**确定地**汇合到同一通道

**Independent Test**: 两个 worker 各写一条消息到同一归约型通道 ⇒ 断言最终值 == 两次产出的归约结果；
同一份规格重复跑 **≥ 3** 次 ⇒ 状态与执行序列**逐项相等**

### Tests for User Story 2（MUST 先写 · MUST 先失败）

- [X] T030 [US2] 在 `tests/runtime/test_send_fanout.py` 写「fan-out 的写入按归约器汇合」用例 **+「fan-out 写入含未知 key ⇒ `InvalidUpdateError`」「覆盖型通道同轮多写 ⇒ 显式失败」** ⇒ FR-005 · SC-002 / SC-008
- [X] T031 [US2] 在 `tests/runtime/test_send_fanout.py` 写「归并顺序 == **上游任务序**（标准触发任务按目标节点名序 → fan-out 任务按产生者 TaskId 序 · `Send` 序号；**标准任务全部在前**）」用例（含**多产生者 + 目标乱序 + 完成顺序颠倒** · 对齐 **E-11**）⇒ FR-005 · SC-009
- [X] T032 [US2] 在 `tests/runtime/test_send_fanout.py` 写「重复 **≥ 3** 次 ⇒ 状态 / 执行序列 / 归并顺序**逐项相等**」用例 ⇒ FR-023 · SC-009
- [X] T033 [US2] 在 `tests/runtime/test_send_fanout.py` 写「fan-out 的写入在 `node_writes` 里归到**目标节点名**名下」用例 **+「`executed` **逐次列出**（同节点可重复 · 顺序 = TaskId 序）」+「`node_versions` 按**成功执行次数**递增（+N）」+「同目标 N 次调用的值序列顺序 = TaskId 序」** ⇒ FR-005 / FR-010 · SC-008 / SC-022
- [X] T034 [US2] 在 `tests/runtime/test_send_fanout.py` 写「fan-out 轮里某个调用抛错 ⇒ 整轮**不合并** + 通道写入版本**不推进**」用例 **+「同一节点 N 次 fan-out 调用各自 `interrupt()` ⇒ N 条独立中断记录（id 不串扰 · 恢复值按任务匹配）」+「多个任务同时失败（标准任务 + fan-out 任务、且节点名序与 TaskId 序相反）⇒ 抛出 **TaskId 最靠前**者的原对象」** ⇒ FR-009 / FR-011 · SC-011 · **DR-01 / F-14**

### Implementation for User Story 2

- [X] T035 [US2] 在 `src/freegraph/runtime/superstep.py` 实现写入收集按 **TaskId 序**遍历本轮任务（**裁定 6** · **H-2** · **PR-6**）⇒ 同时产出 **`ordered_writes: list[(TaskId, target, writes)]`**（供 `_group_writes`）· `node_writes` 仍按目标节点名聚合 ⇒ 同节点的值序列 = 任务序 ⇒ FR-005 · SC-008
- [X] T036 [US2] 修改 `src/freegraph/runtime/superstep.py` 的 `_group_writes`（**裁定 6** · **PR-6**）：**改为遍历 `ordered_writes`（TaskId 序）**（标准任务按目标名序 → fan-out 按产生者 TaskId 序 + `Send` 序号）⇒ 跨目标顺序 == 上游任务序；`_merge_writes` 的**批量 / 未知 key / 回滚**语义零改动 ⇒ FR-005 · SC-002 / SC-008
- [X] T037 [US2] 核验 `src/freegraph/runtime/superstep.py` 的既有**整轮原子**机制覆盖 fan-out 路径（出错轮一个都不合并）⇒ 若已覆盖则**零改动**；否则**最小补齐** ⇒ FR-011 · SC-011

**Checkpoint**: User Story 1 与 2 均可独立验收

---

## Phase 5: User Story 3 - `Send` 的目标写错了要立刻报错（Priority: P3）

**Goal**: `Send` 指向不存在的节点 / 保留名 / 哨兵 / 非法形态 ⇒ **当轮显式失败**（不静默丢弃）

**Independent Test**: 节点返回 `Send("no-such-node", {...})` ⇒ 断言抛出 `ValueError` 且消息**同时点名产生者与目标**

### Tests for User Story 3（MUST 先写 · MUST 先失败）

- [X] T038 [US3] 在 `tests/runtime/test_send_fanout.py` 写「目标不在节点表 ⇒ `ValueError` + 消息**同时点名产生者与目标**」用例 ⇒ FR-007 · SC-003
- [X] T039 [US3] 在 `tests/runtime/test_send_fanout.py` 写「`node` 非 `str` ⇒ `TypeError`；`node` 为空串 ⇒ `ValueError`」用例 ⇒ FR-007 · SC-013
- [X] T040 [US3] 在 `tests/runtime/test_send_fanout.py` 写「`node == Command.PARENT` ⇒ `NotImplementedError`（点名 `__parent__` + 「子图属 v2 能力」）；`node` 是 `START` / `END` ⇒ `ValueError`」用例 ⇒ FR-007 · SC-013
- [X] T041 [US3] 在 `tests/runtime/test_send_fanout.py` 写「载荷形态非法（空列表 / 空元组 / 与 `dict` / `Command` 混装 / **命令列表里混入 `Send`** / 元素非 `Send` ⇒ `TypeError`）」用例 ⇒ FR-008 · SC-012
- [X] T042 [US3] 在 `tests/runtime/test_send_fanout.py` 写「`Command.goto` 槽位里的非法元素（非 `str` / 非 `Send` ⇒ `TypeError`）」用例 ⇒ FR-001 · SC-012

### Implementation for User Story 3

- [X] T043 [US3] 在 `src/freegraph/runtime/_fanout.py` 实现 `Send` 目标校验（**裁定 7 / 10** · **H-2**）（**V-17…V-21** · 类型 / 空串 / 不在节点表 / `__parent__` / 哨兵）⇒ **校验时机 = 产生它的那一轮**（立即）⇒ FR-007 · SC-003 · data-model §5
- [X] T044 [US3] 在 `src/freegraph/runtime/_fanout.py` 实现失败消息**同时点名「产生者节点」与「目标节点」**（**裁定 7** · 澄清轮第 2 次 **Q3 = A**）（如「节点 `'fan'` 的 `Send` 指向了不存在的节点 `'nope'`」）⇒ FR-007 · SC-003

**Checkpoint**: User Story 1–3 均可独立验收

---

## Phase 6: User Story 4 - 没有 `Send` 时行为一字不变（Priority: P4）

**Goal**: 静态边 / `Command` 的既有行为**逐字不变**（引入 `Send` 零污染）

**Independent Test**: 既有静态边 / `Command` 用例**零改动**全量回归通过

### Tests for User Story 4（MUST 先写 · MUST 先失败）

- [X] T045 [US4] 在 `tests/runtime/test_send_fanout.py` 写「静态边 / `Command` 的既有调用形态**行为不变**」回归用例 ⇒ FR-020 · SC-004
- [X] T046 [US4] 在 `tests/runtime/test_send_fanout.py` 写「纯 `goto`（不含 `Send`）的跳转 / 写入 / `node_writes` / `executed` 口径不变」用例 ⇒ FR-002 / FR-010 · SC-004 / SC-022
- [X] T047 [US4] 在 `tests/runtime/test_send_fanout.py` 写「节点返回**普通 `dict`** ⇒ 其写入路径与归约行为一字不变」用例 ⇒ FR-020 · SC-004

### Implementation for User Story 4

- [X] T048 [US4] 跑全量套件（`.venv/bin/python -m pytest -q tests/` · 重点看 `tests/runtime/test_superstep_concurrency.py`）确认既有断言**零变红**（基线 **1184 passed / 4 skipped**）⇒ FR-020 · SC-004

**Checkpoint**: User Story 1–4 均可独立验收

---

## Phase 7: User Story 5 - fan-out 与普通边混在一张图里也能判清（Priority: P5）

**Goal**: 同一 super-step 内既有静态边触发又有 fan-out 任务 ⇒ 调用次数**说得清**（**按载体分列**）

**Independent Test**: 同一节点既有静态边（指向**另一个**目标）、又返回指向第三个目标的 `Send`
⇒ 断言 ① 两个目标**都被调用**；② 同一目标**不会**既被标准入参调用、又被 `Send` 调用

### Tests for User Story 5（MUST 先写 · MUST 先失败）

- [X] T049 [US5] 在 `tests/runtime/test_send_fanout.py` 写「载体 B：同一对（产生者, 目标）一轮内**至多触发一次** · `Send` **胜出**（标准入参那次**不发生**）」用例 ⇒ FR-006 · SC-005
- [X] T050 [US5] 在 `tests/runtime/test_send_fanout.py` 写「载体 B：产生者的**其它**静态目标**照常触发**（叠加）」用例 ⇒ FR-006 · SC-005
- [X] T051 [US5] 在 `tests/runtime/test_send_fanout.py` 写「fan-out 任务**不消费**触发源版本（`versions_seen` 不变）」用例 ⇒ FR-002 · SC-007
- [X] T052 [US5] 在 `tests/runtime/test_send_fanout.py` 写「**别的产生者**的 fan-out / 节点名 `goto` / **静态边**指向同一目标 ⇒ **叠加**」+「**多源屏障组（B7F4）** 的目标同时被载体 B `Send` 指到 ⇒ **屏障标准入参那次照常发生**」+「**同一产生者一轮内多次执行且载体混合**（一次载体 B、一次普通 `dict`）⇒ **任一载体 B 执行即抑制**该 `(producer,target)` 单元素边组；若全为标准执行 ⇒ **不抑制**」用例 ⇒ FR-006 · SC-005 · 差分 **D-37**（⚠️ **载体 A 的叠加用例已移到 US6 T056** · 本任务只验证载体 B / B7F4 / 混合载体）

### Implementation for User Story 5

- [X] T053 [US5] 在 `src/freegraph/runtime/superstep.py` 实现触发组枚举层的「**载体 B 抑制**」（**裁定 5** · **PR-7**）（当**任一** `_FanOut.suppresses_static=True`、`_FanOut.producer == 静态边源节点`、`target == 当前节点` ⇒ 该 **单元素**边触发组**不计入** ⇒ 该目标**不被该静态边触发**；**全部为标准执行 ⇒ 不抑制**；**其它 producer 的静态边不抑制**；**多源屏障组不抑制**）⇒ FR-006 · SC-005
- [X] T054 [US5] 核验**载体 B** 的抑制口径（单元素边组 · 其它 producer 不抑制 · 多源屏障组不抑制 · 同一产生者多次执行且载体混合）并在 `specs/b11f1-send-fanout/quickstart.md` 的 **DR-03** 处保留显著提示（⚠️ **载体 A / 载体 B 的分列核验归 US6 T056**）⇒ FR-006 · SC-005

**Checkpoint**: User Story 1–5 均可独立验收

---

## Phase 8: User Story 6 - 一次返回里既派发又写入（Priority: P6）

**Goal**: `Command(goto=[Send(...), ...], update={...})` ⇒ **写入与派发同时生效**（上游同款）

**Independent Test**: 断言 ① 最终状态**含** `update` 的内容；② 目标**被调用两次**（各自入参正确）⇒ **两条断言同时成立**

### Tests for User Story 6（MUST 先写 · MUST 先失败）

- [X] T055 [US6] 在 `tests/runtime/test_send_fanout.py` 写「`Command(goto=[Send, Send], update={...})` ⇒ 写入生效 **且** 两次 fan-out 生效」用例 **+「同一逻辑载荷分别用载体 A / 载体 B ⇒ 汇合结果逐项相等」**用例 ⇒ FR-005 · SC-002 / SC-008
- [X] T056 [US6] 在 `tests/runtime/test_send_fanout.py` 写「`Command(goto=["a", Send("b", arg)])` **混装** ⇒ 一个边目标 + 一个 fan-out 任务」用例 **+「载体 A：同一产生者的静态边 + `Command.goto` 里的 `Send` 指向同一目标 ⇒ **叠加**（目标被调用 **2** 次：标准 + 自定义）」+「载体 A / 载体 B 的静态边口径**确实分列**（A 叠加 · B 胜出）并在 `quickstart.md` 的 **DR-03** 处保留显著提示」** ⇒ FR-001 / FR-006 · SC-001 / SC-005 · 差分 **D-33**（⚠️ **本任务从 US5 接收载体 A 的叠加 / 分列核验**）

### Implementation for User Story 6

- [X] T057 [US6] 在 `src/freegraph/runtime/superstep.py` 实现 `Command.goto` 的**逐元素分派**（**裁定 1** · **H-1**）（`str` → 边目标；`Send` → fan-out 任务；其它 ⇒ 内置 `TypeError`）⇒ FR-001 · SC-001 · contracts §2
- [X] T058 [US6] 在 `src/freegraph/runtime/superstep.py` 实现「`update` 与 `goto` 里的 `Send` **同时生效**」（**裁定 14** · 上游 **E-08**）（写入归**产生节点**名下 · 派发任务在下一轮）⇒ FR-005 · SC-008
- [X] T059 [US6] 在 `src/freegraph/runtime/superstep.py` 实现载体 A 的 fan-out 载荷落进归一形状的 `fanout` 键（**逐任务 `_FanOutTask.suppresses_static = False` 且聚合 `_FanOut.suppresses_static = False`** ⇒ **不抑制**静态边 ⇒ 叠加）⇒ FR-001 / FR-006 · SC-005

**Checkpoint**: User Story 1–6 均可独立验收 —— **功能面完成**

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 差分场景组 · 破冻结面回溯修订 · 下游接线 · 人工验证与追认

### 差分场景组（FR-019 · SC-019）

- [X] T060 [P] 在 `tests/differential/parity_probe.py` 追加 **D-29…D-32**（fan-out 次数与入参 SAME · arg = 完整状态 SAME · 归约汇合 **SAME（顺序逐项相等** · 上游 `apply_writes` 路径排序 · E-11）· 目标不存在 **STRICTER**）⇒ FR-019 · SC-019
- [X] T061 在 `tests/differential/parity_probe.py` 追加 **D-33…D-37**（载体 A 的静态边并存 **SAME** · 并发 **SAME** · 节点返回 `list[Send]` **DIFF** · 「既派发又写入」**SAME** · 载体 B 的静态边并存 **DIFF**）⇒ FR-019 · SC-019 ⇒ ⚠️ **与 T060 同文件 ⇒ 串行**（不标 `[P]`）
- [X] T062 在 `tests/differential/test_parity_probe.py` 核验新场景被打包进 CI（**Linux 全量档真跑** · 上游缺席即 skip）⇒ FR-019 · SC-019

### 破冻结面的回溯修订（plan T-1…T-15 · FR-022 · SC-020 · **拆分而不删**）

- [X] T063 [P] 回溯修订 `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` §1：删除**陈旧条目** `src/freegraph/_primitives.py`（其余 **11** 条一字不动 · **MUST NOT** 为 `runtime/_fanout.py` 新增条目）⇒ **T-1** · FR-022
- [X] T064 [P] 回溯修订 `tests/runtime/test_superstep_concurrency.py:800-808`（「`_primitives.py` 只留 `Send`」断言 ⇒ 意图保留：改为对 `runtime/_interrupt.py` 的断言 **+**「`Send` 的类型定义在 L1」）⇒ **T-2** · FR-022
- [X] T065 [P] 回溯修订 `tests/facade/_gatesupport.py`（第 **46** 与 **60** 行的清单项 · 移除已删文件 ⇒ G20 / G14 判据一字不动）⇒ **T-3** · FR-022
- [X] T066 [P] 回溯修订 `README.md` 的兼容矩阵：**`Send` 行**措辞更新 + **`Command` 行**删去「`goto` 目标只能是节点名」那句已过时措辞 + **`NodeFunc` 行**的「返回形态」增补 `Send` / `list[Send]` / `tuple[Send, ...]`（**零新增行**）⇒ **T-4** · FR-014
- [X] T067 [P] 回溯修订 G7 的冻结断言与符号面基线：`tests/contracts/test_architecture.py:450` 与 `:1511` · `tests/runtime/test_read_contract.py:63` 与 `:561` · `tests/runtime/test_command_purity.py:287` · `specs/b1f1-contracts-core/contracts/public-api.md` §0 的清单（**20 → 21** + 集合成员增 `Send`）⇒ **T-5** · FR-014 · SC-015
- [X] T068 **核验**（**2026-11-14 收口 · 目标文档已在工作区提前落地 ⇒ MUST NOT 回退**）`harness/proposals/立项书.md`：确认 **§5.1 的 4 处落点**（① L2 层描述行 `Command/interrupt/Send` ⇒ `Command/interrupt` ② L1 层描述行增补 `Send` ③ 公开 API 行 `Send` 改属 L1 ④ ARCH-1 行 `Send` 改属 L1）+ **§5.2 的 B11F1 依赖列**（已补 `B1F1,B9F1,B12F1,B10F1` · 与 spec 的承接条款 **H-1 / H-3 / H-4** 对齐）+ **§5.3 的 C18 行**（已改为 **`v1 提供（B11F1）`**）**均为修订后状态**；发现差异才最小补齐 ⇒ **T-6** · FR-012 · FR-022 ⇒ ⚠️ **须由发起者本人签字**
- [X] T069 [P] 回溯修订 `harness/proposals/上游对齐审计.md` §2.1 **P-05**（标注「✅ 已关闭」）与 §3 第 13 行（**落位**一项已消解）⇒ **T-7** · FR-015
- [X] T070 [P] 回溯修订 `specs/b2f1-contracts-protocols/contracts/public-api.md` · `specs/b2f2-public-api-facade/contracts/facade-api.md` · `specs/b2f2-public-api-facade/contracts/architecture-gates.md:143`（`Send` 的层级归属 + `Command.goto` 的注解）⇒ **T-8** · FR-012
- [X] T071 回溯修订 `specs/b1f1-contracts-core/data-model.md`（第 **70** 行）与 `specs/b1f1-contracts-core/contracts/public-api.md`（第 **103** 行）的 `goto` 字段行：「目标只能是节点名」→ 「可以是节点名或 `Send`」⇒ **T-9** · FR-012（⚠️ **与 T067 同写 `public-api.md` ⇒ 串行**，不标 `[P]`）
- [X] T072 **核验 + 补齐**（**2026-11-14 收口 · 工作区已部分落地 ⇒ MUST NOT 回退已落地部分**）`specs/b9f1-command-primitive/contracts/command-contract.md`：I-5 / I-6 的 `Send` 分支**已落地**；确认 §2 归一形状的 **`fanout` 键**与「`goto` 的形态解析」节的 **`Send` / `Sequence[str | Send]` 分支**已按本 feature 口径补入（**既有 `writes` / `gotos` 与既有断言一条不删**）⇒ **T-10 / T-15** · FR-012
- [X] T073 [P] 回溯修订 `src/freegraph/contracts/protocols.py` 的 `NodeFunc` 注解与 docstring + `tests/contracts/test_protocols.py:136` 的返回联合断言（**增补**三形态 ⇒ 四形态断言保留）⇒ **T-11** · FR-012
- [X] T074 [P] **核验 + 补齐**（**2026-11-14 收口 · §3 / §5 / §6 / I-3 / I-8 已落地 ⇒ MUST NOT 回退**）`specs/b12f1-concurrency-errors/contracts/concurrency-contract.md`：§3 阶段 **②′** 与「含 fan-out 的轮按 TaskId 序（标准任务在前）」**已落地**；确认 §4 已补 **结果槽键 = TaskId** 与 **`_TaskOutcome` 的 `fanout` 字段** ⇒ **T-12 / T-15** · FR-005 / FR-009 / FR-010 · SC-008 / SC-011 / SC-022
- [X] T075 **核对**（**不改**）`harness/demo/graph_core.py` 的 **C18** 用例（确认形态与 `specs/b11f1-send-fanout/quickstart.md` §1 一致 ⇒ 当前**不可跑** ⇒ 如实登记）⇒ **T-13** · FR-016

### 下游接线（宪法 v1.8.0 · **只接线 · 逐条最小改动**）

- [X] T076 [P] 在 `harness/features/B8F1_条件边路由与fresh读.md` **§2.1** 追加一条「B11F1 → B8F1」承接条款（条件边返回 `Send` 的运行期语义）⇒ **D-1** · FR-024
- [X] T077 [P] 在 `harness/features/B13F1_静态中断点与递归上限.md` **新建 `## 下游承接` 块**并追加**两条**（该文件**既无 §2.1、也无 `## 下游承接`**）（**D-2** 递归上限与 fan-out 轮 · **D-7** 静态中断点 × fan-out）⇒ **D-2 / D-7** · FR-020
- [X] T078 [P] 在 `harness/features/B14F1_Checkpointer协议与MemorySaver.md` 的 **`## 下游承接`** 块内追加一条（pending writes 与 fan-out 的归属 **+ 修订其「`task_id` = 节点名 · 一轮一个节点一个任务」假设为 F-13 口径**）⇒ **D-3** · FR-005 / FR-009
- [X] T079 [P] 在 `harness/features/B24F1_打包分发与兼容矩阵.md` **§2.1** 追加一条（`Send` / `Command` / `NodeFunc` 三行的措辞更新 + `Send` 类型落位）⇒ **D-4** · FR-014
- [X] T080 [P] 在 `harness/features/B19F1_TraceSink与current_span.md` 的 **`## 下游承接`** 块内追加一条（触发源的统一暴露含 fan-out 任务）⇒ **D-5** · FR-020
- [X] T081 [P] 在 `harness/features/B6F1_StateGraph构建器.md` **§2.1** 追加一条（构建器 MUST 接受返回 `Send` 列表的节点函数）⇒ **D-6** · FR-001

### 人工验证 · 追认 · 门禁

- [X] T082 在 `harness/verification/B11F1/acceptance.py` 补齐**机械层一键验收**入口（逐条 SC 的可执行断言）⇒ FR-016 · SC-017
- [X] T083 在 `harness/verification/B11F1/manual-verification.md` 填**五段式**（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）+ **来源覆盖表**（判据 A1–A3 + SC + FR 各一张 · 覆盖率 == **100%**）⇒ FR-016 · SC-017
- [X] T084 在 `harness/verification/B11F1/manual-verification.md` 写**发起者追认**文字（**PR-1 / PR-2 / PR-3 / PR-9 / PR-13 / PR-14** · **F-1…F-14**）（偏离登记 **X-1 / X-3 / X-6** + 破冻结面 **F-1…F-14** + **DR-03** 的显著说明）⇒ FR-016 / FR-022 · SC-020 ⇒ ⚠️ **阻断合入**
- [X] T085 跑**全量套件 + 覆盖率**：先 `pytest -q --cov=src/freegraph --cov-report=term-missing --cov-report=xml` 跑**全部相关测试**（至少含 `tests/runtime/` · `tests/contracts/` · `tests/facade/` · `tests/differential/`），再用 `diff-cover coverage.xml --compare-branch=<基线分支>`（若本机无 `diff-cover` ⇒ 人工核对 `term-missing` 中**本 feature 新增/修改的 hunk 行**的 missed == 0）⇒ **新增 / 修改代码的行 / 分支覆盖率 == 100%** ⇒ FR-017 / SC-016
- [X] T086 跑门禁全量（`harness/scripts/gates/gate_G21_dependencies.py` · `gate_G25_import_graph.py` · `gate_G30_attribution.py` 等 · **G1–G30** · **零新增编号** · 编号连续）⇒ FR-021 · SC-015
- [X] T087 核验依赖纯净（`src/freegraph/runtime/_fanout.py` 与 `src/freegraph/runtime/superstep.py` 对 `langchain*` / `langgraph*` / `langsmith` 的导入 == **0** · 环境变量读取 == **0** · 出站 == **0**）⇒ FR-013 · SC-021
- [X] T088 核验 `specs/b11f1-send-fanout/contracts/upstream-parity.md` 与 `specs/b11f1-send-fanout/research.md` 的上游引用**版本 + `路径:行号`**纪律（`langgraph 1.2.11` · `types.py:704-792` / `:824` · `graph/state.py:1488-1492` / `:1749-1775` · `pregel/_algo.py:253-256` / `:962-965` / `:978` · `pregel/main.py:809` · `pregel/_write.py:172-192`）⇒ FR-015 · SC-018
- [X] T089 核验每个新 / 修改源文件的**署名头**逐字（`src/freegraph/runtime/_fanout.py` · `tests/runtime/test_send_fanout.py` · `tests/runtime/test_send_contract.py` 等）⇒ FR-018 · SC-018
- [X] T090 在 `harness/verification/B11F1/manual-verification.md` 的「遗留问题」段登记 **DR-02…DR-06**（**DR-01 已由 T027/T034/T093/T095 修复**并实测）+ 验收脚本 C18 用例**未跑**的原因 ⇒ FR-016 · SC-017
- [X] T091 逐条执行 `specs/b11f1-send-fanout/quickstart.md` 的**可执行场景（§1–§9）**并把实际输出记入人工验证记录 ⇒ FR-017 · SC-001 / SC-013（**其余 SC 由各自的主承载任务判定**，本任务只作端到端交叉核对）
- [X] T092 把「**立项书 §5.2 的行数口径重估**」登记进 `harness/verification/B11F1/manual-verification.md` 的「遗留问题」段（由**发起者**在 feature 收尾时回写 ⇒ 本 feature **MUST NOT** 单方面改上位文档）⇒ FR-016 · plan §Scale/Scope
- [X] T093 **核验**（**2026-11-14 收口 · 目标文档已在工作区提前落地 ⇒ MUST NOT 回退**）`specs/b10f1-interrupt-resume/contracts/{checkpoint-contract.md, interrupt-resume-contract.md}` 与 `specs/b10f1-interrupt-resume/spec.md` 的任务现场 / `.id` 注记：确认 `task_id` 已拆为「标准任务 = 节点名 · fan-out 任务 = `f"{节点名}:{TaskId}"`」· 任务级现场表键已改为「任务标识」· `namespace` 仍 `f"{节点名}:{uuid4}"`（**F-13 / T-14 · 拆分而不删**）；发现差异才最小补齐 ⇒ FR-009 / FR-022 · SC-011 · PR-13
- [X] T094 **核验**（**2026-11-14 收口 · 目标文档已在工作区提前落地 ⇒ MUST NOT 回退**）`specs/b7f1-superstep-loop/{spec.md, contracts/superstep-contract.md}` · `specs/b9f1-command-primitive/contracts/command-contract.md` · `specs/b12f1-concurrency-errors/contracts/concurrency-contract.md` · `specs/b10f1-interrupt-resume/{spec.md, contracts/interrupt-resume-contract.md}` 的顺序 / 阶段模型 / 执行次数（§3 / §4 / §5 / §6 / I-2 / I-3 / I-8 / I-12 / V-15 / `.executed`）：确认已增补阶段 ②′ · **含 fan-out 的轮**按 TaskId 序（标准任务在前）· B7F1 I-1 / I-2 / I-4 的「dict 入参 / 无入边」只约束标准触发 · I-3 已拆为「标准 ≤1 · fan-out N」· `dynamic_edges` 取 TaskId 最后任务（**F-14 / T-15 · 拆分而不删**）；发现差异才最小补齐 ⇒ FR-005 / FR-009 / FR-010 / FR-022 · SC-008 / SC-011 / SC-022 · PR-14
- [X] T095 在 `harness/features/B15F1_SqliteSaver与状态历史.md`（该文件**既无 §2.1、也无 `## 下游承接` 块** ⇒ **新建 `## 下游承接` 块**）追加一条（`task_id` = F-13 口径 · N 个同节点任务的 `.pending_writes` / 中断记录可区分）⇒ **D-8** · FR-009 / FR-010 · SC-011 / SC-022

---

## Dependencies & Execution Order

### 执行闸口（Phase 闸口 · 每道 MUST 全绿才进下一 Phase）

| 闸口 | 位置 | 判据 |
|---|---|---|
| **G-1** | Phase 1 → 2 | 绿基线已记录（**1184 passed / 4 skipped**）· 骨架文件（署名头 + docstring）齐备 |
| **G-2** | Phase 2 → 3 | 门禁 **G21 / G25 / G30** 全绿 · `Send` 的类型落位与 L1 注解**已落地** · **Phase 2 只出**骨架**（fan-out 的**行为**归各故事阶段）** ⇒ **MUST NOT** 在 Phase 2 落地任何 fan-out 的**可观察行为** |
| **G-3** | Phase 3 → 4 | US1 的用例**全绿** · 「执行次数 == `Send` 条数」与「各次入参逐字正确」两条断言成立 |
| **G-4** | Phase 4 → 5 | US2 的用例**全绿** · 归并顺序**确定**（重复 ≥ 3 次逐项相等） |
| **G-5** | Phase 5 → 6 | US3 的用例**全绿** · 目标不存在 ⇒ 显式失败 + 消息点名两处 |
| **G-6** | Phase 6 → 7 | US4 的用例**全绿** · 既有断言**零变红** |
| **G-7** | Phase 7 → 8 | US5 的用例**全绿** · 同一对（产生者, 目标）一轮内至多一次 |
| **G-8** | Phase 8 → 9 | US6 的用例**全绿** · 「既派发又写入」两条断言**同时**成立 |
| **G-9** | Phase 9 → 合入 | 差分 **D-29…D-37** 判词**全部**符合 · 回溯修订 **T-1…T-15** **逐条**落地 · 下游接线 **D-1…D-8** **逐条**落盘 · 追认文字已写（**T084**）· 门禁全量绿 |

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - **BLOCKS all user stories**
- **User Stories (Phase 3–8)**: All depend on Foundational phase completion
  - US1（P1）先落地 ⇒ US2–US6 可在其后**并行**开工（文件不同 ⇒ 无冲突）
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: 依赖 Foundational ⇒ **无**对其它故事的依赖 ⇒ **MVP**
- **User Story 2 (P2)**: 依赖 Foundational（+ US1 的归一形状 ⇒ 实际顺序上在 US1 之后）· **独立可测**
- **User Story 3 (P3)**: 依赖 Foundational（校验作用于已归一的载荷 ⇒ 在 US1 之后）· **独立可测**
- **User Story 4 (P4)**: 依赖 Foundational（回归面）· **独立可测**
- **User Story 5 (P5)**: 依赖 Foundational（+ US1 的归一）· **独立可测**（⚠️ **只验证载体 B / B7F4 / 混合载体**；载体 A 的叠加 / 分列用例归 **US6 T056**）
- **User Story 6 (P6)**: 依赖 Foundational（+ US1 的归一 + `Command.goto` 的解析）· **独立可测**

### Within Each User Story

- Tests **MUST** 先写并**先失败**（此时 fan-out 语义未接线 ⇒ 断言必然失败）
- 归一（载体）→ 任务构造（阶段 ②′）→ 执行 → 落回 ⇒ 顺序不可颠倒
- 校验（V-17…V-21）⇒ 落在**归一之后、执行之前**（产生轮立即失败）
- Story complete before moving to next priority

### Parallel Opportunities

- Phase 1 的 T002–T004 可并行；⚠️ **T001 与 T005 共享 `manual-verification.md` ⇒ 串行**
- Phase 2 中**不同文件**的任务可并行（如 T007 / T009 / T010 / T011 / T012 / T015）· ⚠️ **T012 / T014 / T017 同写 `_fanout.py` ⇒ 串行**
- ⚠️ **同文件串行**：`src/freegraph/contracts/types.py`（T006 / T008）· `src/freegraph/runtime/superstep.py`（T013 / T016 / T018 / T026–T029 / T035 / T036 / T053 / T057–T059）· `src/freegraph/runtime/_fanout.py`（T012 / T014 / T017 / T043 / T044）⇒ **MUST NOT** 并行改同一文件
- Phase 3–8 的测试任务**都写 `tests/runtime/test_send_fanout.py`** ⇒ **不标 `[P]`**；可并行**起草**，但**合入前 MUST 串行跑一遍**
- Phase 9 的回溯修订（T063–T075 · T093–T094）与下游接线（T076–T081 · T095）按**不同文件**并行；⚠️ **同文件串行**：**T060 / T061**（`parity_probe.py`）· **T067 / T071**（`b1f1-contracts-core/contracts/public-api.md`）· **T072 / T094**（`b9f1-command-primitive/contracts/command-contract.md`）· **T074 / T094**（`b12f1-concurrency-errors/contracts/concurrency-contract.md`）· **T093 / T094**（`b10f1-interrupt-resume/spec.md` 与 `contracts/interrupt-resume-contract.md`）

---

## Parallel Example: User Story 1

```bash
# US1 的 5 个测试任务可并行起草（同一文件 ⇒ 不标 [P]；此时它们 MUST 失败 —— fan-out 语义尚未接线；
# 合入前 MUST 串行跑一遍）：
Task: "在 tests/runtime/test_send_fanout.py 写「fan-out 执行次数 == Send 条数」用例（载体 B · 同目标两个 Send）"
Task: "在 tests/runtime/test_send_fanout.py 写「各次入参逐字等于各自 arg」用例"
Task: "在 tests/runtime/test_send_fanout.py 写「fan-out 任务在下一轮执行」用例"
Task: "在 tests/runtime/test_send_fanout.py 写「载体 B 的载荷归一」用例"
Task: "在 tests/runtime/test_send_fanout.py 写「fan-out 任务受 max_concurrency 约束」用例"
```

---

## Parallel Example: User Story 3 与 User Story 5（判据独立 · **同文件**）

```bash
# US1 完成后 ⇒ 两者可并行起草（同文件 ⇒ 不标 [P]；合入前 MUST 串行跑一遍）：
Task: "在 tests/runtime/test_send_fanout.py 写「目标不在节点表 ⇒ ValueError + 消息同时点名产生者与目标」用例"
Task: "在 tests/runtime/test_send_fanout.py 写「载体 B：标准触发至多一次 · Send 胜出」用例"
```

---

## Implementation Strategy

### MVP First（仅 User Story 1）

1. Complete Phase 1: Setup（绿基线 + 骨架）
2. Complete Phase 2: Foundational（L1 落位 + 内部形状 + TaskId）—— **CRITICAL · 阻塞全部故事**
3. Complete Phase 3: User Story 1（**先红后绿**）
4. **STOP and VALIDATE**: 用 `quickstart.md` §1 的场景独立验收 US1
5. 此时的**可交付面** = 「同一节点被多次调用 · 每次不同入参」⇒ **map-reduce 模式已可运行**（立项书小目标）

### Incremental Delivery

1. Setup + Foundational → 骨架就绪
2. US1 → 验收（**MVP**）· US2 → 验收（归约汇合）· US3 → 验收（失败可判定）
3. US4 → 验收（回归不破）· US5 → 验收（混合可判定）· US6 → 验收（既派发又写入）
4. Phase 9：差分场景组 + 回溯修订 + 下游接线 + 人工验证与**追认**
5. 每一步都**独立可验收**，不破坏前一步

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 → User Story 2
   - Developer B: User Story 3 → User Story 5
   - Developer C: User Story 4（回归）+ User Story 6
3. Phase 9 的回溯修订与下游接线**按文件**并行

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- ⚠️ **本 feature 的三个「同一文件」热点**：`src/freegraph/runtime/superstep.py` ·
  `tests/runtime/test_send_fanout.py` · `tests/differential/parity_probe.py`（T060 / T061）
  ⇒ ⇒ **同文件的测试任务虽可并行起草，但 MUST 在合入前串行跑一遍；同文件的非测试任务 MUST 串行**
- ⚠️ **回溯修订任务（T063–T075 · T093–T094）与下游接线任务（T076–T081 · T095）** MUST 在**发起者追认**（T084）**之后**才算完成
  ⇒ ⇒ **T084 是**阻断合入**的任务**

---

## 附录 · 任务 ↔ spec 追溯表

### FR → 任务

| FR | 主题 | 承载任务 |
|---|---|---|
| FR-001 | fan-out 载体（**双载体**） | T024 · T026 · T042 · T056 · T057 · T059 · T081 |
| FR-002 | `Send` 的落点 = 与静态边 / `goto` 同族的下一轮任务（派发任务，不消费触发源版本） | T013 · T016 · T021 · T023 · T027 · T046 · T051 |
| FR-003 | 入参形态 = arg **逐字**替代 | T009 · T017 · T022 · T028 |
| FR-004 | N 次独立调用 | T015 · T016 · T017 · T021 · T027 |
| FR-005 | 共用合并路径 + 归属 + 归并顺序 + 派发与写入同时生效 | T012 · T013 · T014 · T030 · T031 · T033 · T035 · T036 · T055 · T058 · T074 · T078 · T094 |
| FR-006 | 混合调度语义（**按载体分列**） | T012 · T013 · T018 · T049 · T050 · T052 · T053 · T054 · T056 · T059 |
| FR-007 | 目标可判定（不存在 / 保留名 / 哨兵） | T038 · T039 · T040 · T043 · T044 |
| FR-008 | 载荷形态合法 | T022 · T026 · T041 |
| FR-009 | 并发语义同 B12F1 | T015 · T025 · T027 · T034 · T074 · T078 · T093 · T094 · T095 |
| FR-010 | 执行记录与版本口径 | T014 · T015 · T029 · T033 · T046 · T074 · T094 · T095 |
| FR-011 | 轮次原子性覆盖 fan-out | T034 · T037 |
| FR-012 | 层纪律 + `Send` 的类型落位 = **L1** | T002 · T004 · T006 · T008 · T009 · T010 · T011 · T068 · T070 · T071 · T072 · T073 |
| FR-013 | 依赖隔离 · 零出站 | T020 · T087 |
| FR-014 | 导出面（三处特批 L1 变更：符号面 / goto 注解 / NodeFunc 联合） | T007 · T008 · T009 · T066 · T067 · T079 |
| FR-015 | 上游行号纪律 | T069 · T088 |
| FR-016 | 人工验证记录（含追认文字） | T005 · T075 · T082 · T083 · T084 · T090 · T092 |
| FR-017 | 纯单元可测 · 覆盖率 | T003 · T004 · T085 · T091 |
| FR-018 | 署名头与文档纪律 | T089 |
| FR-019 | 差分场景组落地 | T060 · T061 · T062 |
| FR-020 | 不越界 | T019 · T045 · T047 · T048 · T077 · T080 |
| FR-021 | 零新增门禁编号 | T086 |
| FR-022 | 破冻结面的回溯修订（**F-1…F-14**） | T001 · T063 · T064 · T065 · T066 · T067 · T068 · T069 · T070 · T071 · T072 · T073 · T074 · T084 · T093 · T094 |
| FR-023 | 确定性 · 可复现 | T032 |
| FR-024 | 条件边形态的接线 | T076 |

### SC → 任务

| SC | 主题 | 承载任务 |
|---|---|---|
| SC-001 | fan-out 次数 == `Send` 条数 · 各次入参正确（**A1**） | T021 · T022 · T056 · T057 · T091 |
| SC-002 | 产出按归约器汇合（**A2**） | T030 · T036 · T055 |
| SC-003 | 目标不存在 ⇒ 明确报错（**A3**） | T038 · T043 · T044 |
| SC-004 | 无 `Send` 时行为一字不变 | T045 · T046 · T047 · T048 |
| SC-005 | 混合调度语义可判定 | T049 · T050 · T052 · T053 · T054 · T056 · T059 |
| SC-006 | 入参形态写死 | T022 · T028 |
| SC-007 | 落点 = 下一轮 | T023 · T027 · T051 |
| SC-008 | 写入路径共用 + 派发与写入同时生效 | T030 · T033 · T035 · T036 · T055 · T058 · T074 · T094 |
| SC-009 | 确定性 · 可复现 | T031 · T032 |
| SC-010 | 并发语义同 B12F1 | T025 |
| SC-011 | 失败传播与原子性 | T034 · T037 · T074 · T093 · T094 · T095 |
| SC-012 | 载荷形态非法 ⇒ 显式失败 | T024 · T026 · T041 · T042 |
| SC-013 | 保留名与哨兵目标 | T039 · T040 · T091 |
| SC-014 | 层纪律 | T002 · T004 · T006 · T009 · T010 · T011 · T020 |
| SC-015 | 结构纪律（导出面 / 门禁编号） | T007 · T010 · T067 · T086 |
| SC-016 | 可测性 · 覆盖率 == 100% | T003 · T004 · T085 |
| SC-017 | 人工验证记录 | T005 · T082 · T083 · T090 |
| SC-018 | 文档纪律 | T088 · T089 |
| SC-019 | 差分场景组落地 | T060 · T061 · T062 |
| SC-020 | 破冻结面 + 发起者追认 | T063–T074 · T093–T095 · T084 |
| SC-021 | 依赖隔离 · 零出站 | T020 · T087 |
| SC-022 | 执行记录口径 | T029 · T033 · T046 · T074 · T094 · T095 |

> **双向覆盖核验**：**FR 24/24**（每条 ≥ 1 条任务）· **SC 22/22**（每条 ≥ 1 条任务）·
> **任务 95/95**（每条 ≥ 1 条 FR · 见下表）⇒ **追溯表双向齐全**（宪法原则 VI）。
> ⚠️ 本附录的三张表**与任务正文逐条对齐**（脚本抽取每个任务描述里的 FR / SC 引用）⇒
> **改任务描述后 MUST 同步本表**（否则会漂移）。
> ⚠️ **唯一聚合写法**：**SC-020** 的 `T063–T074 · T093–T095 · T084` 是**按回溯修订组聚合**的区间
> （每个回溯任务正文以 **`T-x`** 引用其回溯项；逐条判定仍以任务正文为准）。

### 任务 → FR（反向覆盖 · 每条任务至少挂一条 FR）

| 任务 | FR | 任务 | FR | 任务 | FR |
|---|---|---|---|---|---|
| T001 | FR-022 | T032 | FR-023 / SC-009 | T063 | FR-022 |
| T002 | FR-012 / SC-014 | T033 | FR-005 / FR-010 / SC-008 / SC-022 | T064 | FR-022 |
| T003 | FR-017 / SC-016 | T034 | FR-009 / FR-011 / SC-011 | T065 | FR-022 |
| T004 | FR-012 / FR-017 / SC-014 / SC-016 | T035 | FR-005 / SC-008 | T066 | FR-014 |
| T005 | FR-016 / SC-017 | T036 | FR-005 / SC-002 / SC-008 | T067 | FR-014 / SC-015 |
| T006 | FR-012 / SC-014 | T037 | FR-011 / SC-011 | T068 | FR-012 / FR-022 |
| T007 | FR-014 / SC-015 | T038 | FR-007 / SC-003 | T069 | FR-015 |
| T008 | FR-012 / FR-014 | T039 | FR-007 / SC-013 | T070 | FR-012 |
| T009 | FR-003 / FR-012 / FR-014 / SC-014 | T040 | FR-007 / SC-013 | T071 | FR-012 |
| T010 | FR-012 / SC-014 / SC-015 | T041 | FR-008 / SC-012 | T072 | FR-012 |
| T011 | FR-012 / SC-014 | T042 | FR-001 / SC-012 | T073 | FR-012 |
| T012 | FR-005 / FR-006 | T043 | FR-007 / SC-003 | T074 | FR-005 / FR-009 / FR-010 / SC-008 / SC-011 / SC-022 |
| T013 | FR-002 / FR-005 / FR-006 | T044 | FR-007 / SC-003 | T075 | FR-016 |
| T014 | FR-005 / FR-010 | T045 | FR-020 / SC-004 | T076 | FR-024 |
| T015 | FR-004 / FR-009 / FR-010 | T046 | FR-002 / FR-010 / SC-004 / SC-022 | T077 | FR-020 |
| T016 | FR-002 / FR-004 | T047 | FR-020 / SC-004 | T078 | FR-005 / FR-009 |
| T017 | FR-003 / FR-004 | T048 | FR-020 / SC-004 | T079 | FR-014 |
| T018 | FR-006 | T049 | FR-006 / SC-005 | T080 | FR-020 |
| T019 | FR-020 | T050 | FR-006 / SC-005 | T081 | FR-001 |
| T020 | FR-013 / SC-014 / SC-021 | T051 | FR-002 / SC-007 | T082 | FR-016 / SC-017 |
| T021 | FR-002 / FR-004 / SC-001 | T052 | FR-006 / SC-005 | T083 | FR-016 / SC-017 |
| T022 | FR-003 / FR-008 / SC-001 / SC-006 | T053 | FR-006 / SC-005 | T084 | FR-016 / FR-022 / SC-020 |
| T023 | FR-002 / SC-007 | T054 | FR-006 / SC-005 | T085 | FR-017 / SC-016 |
| T024 | FR-001 / SC-012 | T055 | FR-005 / SC-002 / SC-008 | T086 | FR-021 / SC-015 |
| T025 | FR-009 / SC-010 | T056 | FR-001 / FR-006 / SC-001 / SC-005 | T087 | FR-013 / SC-021 |
| T026 | FR-001 / FR-008 / SC-012 | T057 | FR-001 / SC-001 | T088 | FR-015 / SC-018 |
| T027 | FR-002 / FR-004 / FR-009 / SC-007 | T058 | FR-005 / SC-008 | T089 | FR-018 / SC-018 |
| T028 | FR-003 / SC-006 | T059 | FR-001 / FR-006 / SC-005 | T090 | FR-016 / SC-017 |
| T029 | FR-010 / SC-022 | T060 | FR-019 / SC-019 | T091 | FR-017 / SC-001 / SC-013 |
| T030 | FR-005 / SC-002 / SC-008 | T061 | FR-019 / SC-019 | T092 | FR-016 |
| T031 | FR-005 / SC-009 | T062 | FR-019 / SC-019 | T093 | FR-009 / FR-022 / SC-011 |
| T094 | FR-005 / FR-009 / FR-010 / FR-022 / SC-008 / SC-011 / SC-022 | T095 | FR-009 / FR-010 / SC-011 / SC-022 |  |  |
### 裁定 / 承接条款 / 登记项 → 任务（**可机械核对**）

> **用途**：把 spec 的 **裁定 1–14**、承接条款 **H-1…H-4**、plan 的**登记项 PR-1…PR-14**
> 逐条落到**具体任务** ⇒ ⇒ 「哪条判定由谁实现」**不再**只能靠人读。
> ⚠️ 本表与 plan 的「登记项 → 任务落点」表**逐条一致**。

| 依据 | 主题 | 落点任务 |
|---|---|---|
| **裁定 1** | fan-out 载体 = **双载体** | T026 · T057 · T059 · T081 |
| **裁定 2** | `Send` 的落点 = 下一轮（与 `goto` 同族 · **派发任务**，不登记为边触发源）（**H-1**） | T016 · T017 · T027 |
| **裁定 3** | 入参形态 = arg **逐字**替代 | T017 · T028 |
| **裁定 4** | 多次调用 = N 次独立调用 | T012 · T015 · T016 · T021 · T027 |
| **裁定 5** | 普通边与 `Send` 混合 ⇒ **按载体分列** | T018 · T049 · T050 · T052 · T053 · T054 · T056 · T059 |
| **裁定 6** | 写入路径 + 归并顺序（**H-2**） | T012 · T013 · T014 · T035 · T036 |
| **裁定 7** | `Send` 目标不存在 ⇒ **显式失败**（消息点名两处） | T038 · T043 · T044 |
| **裁定 8** | 并发与错误传播同 B12F1（**H-4**） | T015 · T025 · T027 · T034 · T037 |
| **裁定 9** | 载荷形态的失败信号 | T026 · T039 · T041 · T042 |
| **裁定 10** | 保留名与哨兵目标 | T039 · T040 · T043 |
| **裁定 11** | `Send` 的类型落位 = **L1**（**H-3**） | T006 · T007 · T008 · T009 · T010 · T011 |
| **裁定 12** | 条件边形态归 B8F1 | T076 |
| **裁定 13** | 执行记录与版本口径 | T014 · T029 · T046 |
| **裁定 14** | 一次返回里「既派发又写入」 | T055 · T058 |
| **H-1** | `Send` 落点与 `goto` **同族** | T016 · T027 · T057 |
| **H-2** | 触发源体系 / 合并路径 / 原子性**照写** | T027 · T035 · T036 · T043 |
| **H-3** | `Send` 的类型已在门面冻结（**唯一例外** = 裁定 11） | T006 · T007 · T008 · T009 · T010 · T011 |
| **H-4** | 并发语义**同 B12F1** | T015 · T025 · T027 · T037 |
| **PR-1** | `Send` 归 L1（破 L1 冻结面） | T006 · T008 · T009 · T010 · T011 |
| **PR-2** | L1 符号面 20 → 21 | T007 · T067 |
| **PR-3** | 协议面放宽（`goto` 注解 / `NodeFunc` 联合） | T008 · T009 · T073 |
| **PR-4** | 结果槽的键 → **TaskId** | T014 · T015 |
| **PR-5** | `SchedulerState` 新增一个带缺省值的字段 | T013 |
| **PR-6** | 归一形状增一个键 + `_TaskOutcome` 增一个字段 + `ordered_writes` | T012 · T015 · T035 · T036 · T059 |
| **PR-7** | 两载体口径**不同**（DR-03） | T054 · T056 |
| **PR-8** | fan-out 载荷**不落盘**（DR-02） | T019 · T078 |
| **PR-9** | 立项书 §5.1 / §5.2 的修订 | T068 |
| **PR-10** | 下游接线 D-1…D-8 | T076 · T077 · T078 · T079 · T080 · T081 · T095 |
| **PR-11** | 差分场景 D-29…D-37 | T060 · T061 · T062 |
| **PR-12** | 中断 id 重复风险（DR-01 · F-13） | T027 · T034 · T093 · T095 |
| **PR-13** | B10F1 任务标识 / 中断现场（F-13） | T093 · T095 |
| **PR-14** | B7F1/B9F1/B12F1/B10F1 顺序 / 阶段 / 执行次数（F-14） | T094 |
| **F-13** | B10F1 契约回溯修订 | T093 · T095 |
| **F-14** | B7F1/B9F1/B12F1 契约回溯修订 | T094 |
| **D-8** | B15F1 `task_id` / 中断现场接线 | T095 |
