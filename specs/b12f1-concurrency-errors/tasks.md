---
description: "Task list for B12F1 · 节点执行 + 并发执行 + 错误传播 + GraphInterrupt 合并"
---

# Tasks: B12F1 · 节点执行 + 并发执行 + 错误传播 + `GraphInterrupt` 合并

**Input**: Design documents from `/specs/b12f1-concurrency-errors/`
**Prerequisites**: plan.md（required）· spec.md（required · 用户故事）· research.md · data-model.md ·
contracts/（`concurrency-contract.md` + `upstream-parity.md`）· quickstart.md

**Tests**: **包含**测试任务 —— spec FR-022 / SC-020 要求「纯单元可测 + 行/分支覆盖率 == 100%」
⇒ **MUST 先写 · MUST 先失败**（入口此时仍是**串行** ⇒ 并发断言**必然失败** ⇒ Phase 2 只出骨架桩）。

**Organization**: 按用户故事分组（**5** 个 · P1–P5）⇒ 每个故事可**独立实现、独立测试**。

> ⚠️ **本文件是**重写**：初版（377 行 / 60 条任务）建立在**旧口径**上（节点表顺序 · 并发度不限 ·
> 失败**不**取消其余任务 · 中断集合落**调度状态字段**）⇒ spec / plan / research / data-model /
> quickstart / contracts 已于 2026-11-12 全部重出 ⇒ ⇒ 本 tasks MUST 与新口径**逐条一致**。

---

## 格式：`[ID] [P?] [Story] 描述`

- **[P]**：可并行（不同文件 / 无未完成依赖）
- **[Story]**：所属用户故事（US1…US5）—— 仅**用户故事阶段**的任务带
- **每条任务 MUST 带确切文件路径**（本仓库约定）

## 路径约定

- 源码：`src/freegraph/runtime/`（L2 · 层注册表**目录条目** ⇒ **零改动**）
- ⚠️ **新增内部模块**：`src/freegraph/runtime/_concurrency.py`（**不进 `__all__`** ⇒ 导出面仍 **20**）
- 测试：`tests/runtime/`（⚠️ **MUST NOT** 放 `tests/contracts/` —— 门禁 **G2** 禁该目录 import `freegraph.*`）
- 差分：`tests/differential/`（**已存在** · 追加场景组）
- 人工验证：`harness/verification/B12F1/`
- 契约 / 规格：`specs/b12f1-concurrency-errors/` · `specs/b7f1-superstep-loop/`
- 下游提示词：`harness/features/`（**只接线 · 逐条最小改动**）

---

**本 feature 的可测判据总表**（**26 FR + 29 SC ↔ 83 条任务**）—— **逐 SC 一行**：
追溯见文末「**附录 · 任务 ↔ spec 追溯表**」—— **每个 FR 与每个 SC 均至少被一条任务映射**
（**FR 26/26 · SC 29/29**）· **反向**：**每条任务**携带的义务 MUST 挂上**至少一条 FR**
⇒ 追溯表**双向**齐全（宪法原则 VI）。
> ⚠️ **本表 = 摘要**：**权威映射 = 文末「任务 ↔ spec 追溯表」** ⇒ 修改判据归属时 MUST **同步**两处
> ⇒ 本表已**逐行**由附录生成 ⇒ **两处 MUST NOT 漂移**。

**SC-001**（并行节点不串行化（**A1**））由 **T018 · T019** 承载；
**SC-002**（首个异常正确抛出（**A2**））由 **T027 · T028** 承载；
**SC-003**（后续 super-step 不执行（**A3**））由 **T032** 承载；
**SC-004**（并发 == 串行（同一规格））由 **T048** 承载；
**SC-005**（确定性 · 可复现）由 **T049 · T050** 承载；
**SC-006**（写入收集语义）由 **T055** 承载；
**SC-007**（原子性）由 **T031** 承载；
**SC-008**（调度状态不落回（无幽灵触发））由 **T033** 承载；
**SC-009**（多个中断合并抛出（元组 · 顺序确定））由 **T038 · T040** 承载；
**SC-010**（中断元素的 `.value` / `.id`）由 **T039** 承载；
**SC-011**（中断与写入的关系（中断轮合并 / 出错轮不合并））由 **T041** 承载；
**SC-012**（中断后暂停）由 **T045** 承载；
**SC-013**（异常优先于中断）由 **T044** 承载；
**SC-014**（其余并发失败不被静默吞掉（附注三样））由 **T029** 承载；
**SC-015**（`goto` 不互相吞并）由 **T051** 承载；
**SC-016**（多节点 × 多命令的归并顺序）由 **T053** 承载；
**SC-017**（节点入参口径）由 **T054** 承载；
**SC-018**（依赖隔离 · 零出站）由 **T002 · T075** 承载；
**SC-019**（结构纪律（导出面 / 四字段 / 层 / 门禁编号））由 **T072 · T082** 承载；
**SC-020**（可测性 · 覆盖率）由 **T073** 承载；
**SC-021**（人工验证记录）由 **T004 · T078 · T083** 承载；
**SC-022**（偏离登记 + 发起者追认）由 **T080** 承载；
**SC-023**（不越界）由 **T075 · T079 · T083** 承载；
**SC-024**（文档纪律（署名头 / 上游引用 / 冻结面文案））由 **T001 · T074 · T076 · T082** 承载；
**SC-025**（零悬挂线程）由 **T021** 承载；
**SC-026**（确定性 · 调度状态不串扰）由 **T021 · T049** 承载；
**SC-027**（并发度缺省与上限（`min(32, cpu+4)`））由 **T009 · T022 · T023** 承载；
**SC-028**（取消语义（排队未启动者被取消 · 运行中者被等待））由 **T011 · T030 · T035** 承载；
**SC-029**（差分探针场景组全绿（**A4**））由 **T058 · T059 · T060 · T061 · T062 · T063 · T064 · T065 · T066 · T067 · T068** 承载；

**T077**（验收脚本跑全量 **14** 道闸口）、**T080**（**发起者追认** · plan 登记项 **PR-1…PR-11**）、
**T081**（**追溯表双向齐全**）与 **T082**（**L1 冻结面文档的失准文案订正**）是**阻断合入**的任务。
**T083**（**验收契约 A7 的判据差距核对 + 登记**）**非阻断**，但 MUST 在 feature 收尾前完成
（其产出并入 **PR-11** 的「遗留问题」面 ⇒ 否则 A7 现状会被误当作 A1 已通过）。

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 核对上游取证工件 · 依赖面 · 判定归属，并建立人工验证与验收入口的骨架。

- [X] T001 核对 Phase 0 的上游取证工件已落盘且与 spec 逐条一致：`specs/b12f1-concurrency-errors/research.md` §1 的 **E-1…E-6**（每条含**实测方法 + 真实输出**）· `specs/b12f1-concurrency-errors/contracts/upstream-parity.md` 的 **P-01…P-19** + **X-1…X-7** 分叉汇总 ⇒ 全部上游引用 MUST 带**核实版本 `langgraph 1.2.11` + `路径:行号`**，凭记忆沿用的引用数 == **0**
- [X] T002 核对**依赖面零新增**：`pyproject.toml` **零改动**（`dependencies = []` · 无新增 extras）· `langgraph` **不在**任何依赖组 ⇒ 门禁 **G3 / G21 / G22 / G23** 的基线实跑结果记入 `harness/verification/B12F1/manual-verification.md` 的「实际输出」段
- [X] T003 核对 `specs/b12f1-concurrency-errors/spec.md` 的 **25 条裁定**（裁定 1–24 + **裁定 25**「结果对象该承载几个字段」· 依宪法 **v1.10.0 原则 XII**）与**澄清 25 问**（**Q1–Q18** + **Q-A…Q-G**）已落盘且**来源标注齐全** ⇒ 逐条核对 · 缺一即判失败（spec 的「澄清与裁定」表 + `## Clarifications` 下**四节**「Session 2026-11-12（澄清轮 · 发起者拍板）/（第 2 次 · 发起者拍板）/（第 3 次 · 发起者拍板）」+ 「Session 2026-11-13（对账补记 · V-8 · 发起者预先裁定）」⇒ 其中 **Q-G** 即**裁定 25** 的**来源补录**）
- [X] T004 [P] 建立人工验证记录骨架 `harness/verification/B12F1/manual-verification.md`：**五段式**（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）+ 「来源覆盖表」骨架（**A1–A4** + **SC-001…SC-029** + **FR-001…FR-026**）
- [X] T005 [P] 建立一键验收入口骨架 `harness/verification/B12F1/acceptance.py`：**一条命令跑完全部闸口**（**14** 道 · 对应 quickstart 的 V1–V14）· 退出码 **0/1/2**（沿用 **B9F1** 的同款先例）· 文件头 MUST 带**署名头**（宪法原则 X）
- [X] T006 [P] 把既有 **7 处**顺序敏感用例（⚠️ **2026-11-13 · T007 实跑据实**：初版口径 **10** 处 ⇒ 实跑 **7** 处 / **5** 个文件）的**基线清单**记入 `harness/verification/B12F1/manual-verification.md`（research **§2 C-01** 的精确清单 · 5 个文件 / 10 个测试函数）⇒ 供 **US4** 阶段的拆分任务逐处核对

- [X] T007 [P] **重跑**既有测试的**回归面探测**（research **§2 C-01**）以确认「**10 处**顺序敏感断言」的清单**未扩大**：① 用「**并发版** `_run_round`」的原型**替换**既有实现（**临时脚本 · 不进仓库**）· **不加抖动**跑一遍既有套件 ⇒ 记录**当次基线**（⚠️ research 记载初版基线 = **626** ⇒ P2-a / P2-b / P2-c 落地后为 **1067** ⇒ **MUST 以当次实跑为准**）② 再给**同轮内靠后的任务**注入 **4 ms 递增延迟** ⇒ 暴露对「完成顺序」敏感的断言 ③ 把**实跑**得到的**精确清单**（文件 / 测试函数 / **条数**）记入 `harness/verification/B12F1/manual-verification.md` 的「**验证步骤**」段 ⇒ ⚠️ **若条数 ≠ 10** ⇒ MUST **据实修订**「10 处」的表述（spec **FR-006** / 裁定 19 / R-6 · plan **PR-8**）并**同步** US4 阶段拆分任务的清单 ⇒ ⇒ **判据本身不变**（仍 MUST **逐处拆分** · 一条不删）⇒ ★ **实跑结论（2026-11-13）**：条数 == **7**（原型 + **真实实现**双证 · **3/3 次一致**）⇒ spec / plan 已**据实订正为 7** ⇒ 实跑清单见 `harness/verification/B12F1/manual-verification.md` §2.3⇒ ⚠️ research §2 已明确「**本轮 MUST 重跑**该探测」⇒ 本任务即其落点

**Checkpoint**: 取证与判定归属核对完毕 · 人工验证与验收骨架就位

---

## Phase 2: Foundational（阻塞性前置 · 骨架）

**Purpose**: 并发执行器与调度内核改造的骨架 —— **所有用户故事都依赖它**。

**⚠️ CRITICAL**: 本 Phase 未完成前，**任何用户故事**都不可开工。

- [X] T008 在 `src/freegraph/runtime/_concurrency.py` 定义**任务结果槽** `_TaskOutcome`（`frozen=True, slots=True` 的 dataclass · 字段 `writes: dict[str, tuple[Any, ...]]` / `gotos: tuple[str, ...]` / `error: BaseException | None` / `interrupts: tuple[Interrupt, ...]`）⇒ ⚠️ **`interrupts` 的元素 = 该节点 `GraphInterrupt.args[0]`（≡ `payload`）的**元素**（`Interrupt` 对象）**（裁定 7）⇒ MUST **NOT** 是 `payload` 本身（那是元组 ⇒ 嵌套元组 ⇒ 元素**没有** `.value` / `.id`）** ⇒ **不导出**（`freegraph.runtime.__all__` 仍 **20**）⇒ 文件头 MUST 带**署名头**（宪法原则 X）
- [X] T009 在 `src/freegraph/runtime/_concurrency.py` 实现**并发度计算** `_resolve_cap(task_count: int, max_concurrency: int | None) -> int`：返回 `min(task_count, max_concurrency or min(32, (os.cpu_count() or 1) + 4))` ⇒ ⚠️ `os.cpu_count()` 是**系统调用**（**非**环境变量）⇒ **MUST NOT** 读 `os.environ` ⇒ 显式 `N` 时 **N MUST NOT 被 32 再夹**（`max_concurrency=100` ⇒ 上限 **100**，不是 32）
- [X] T010 在 `src/freegraph/runtime/_concurrency.py` 实现 `run_tasks_concurrently(tasks, *, cap) -> list[_TaskOutcome]`：用 `concurrent.futures.ThreadPoolExecutor(max_workers=cap, thread_name_prefix="freegraph-node")` ⇒ **每轮新建 + 每轮关闭**（`with` ⇒ **零悬挂线程**）⇒ **零节点 MUST NOT 建池**（直接返回 `[]`）⇒ 逐任务产出一个 `_TaskOutcome` ⇒ 工作线程**只**捕获 `Exception` ⇒ `KeyboardInterrupt` / `SystemExit` **不进** `_TaskOutcome`（**上游同款**）⇒ ⚠️ **「穿出」的实现落点（契约 §4）**：线程池会把 `BaseException` **存进 future** ⇒ 轮末 MUST 对**每个** future 调 `result()`（**重抛**）⇒ 该 `BaseException` 即**中止整轮**（**MUST NOT** 被吞成普通失败）<br>⚠️ **捕获顺序（MUST · 2026-11-13 分析轮补记）**：`GraphInterrupt` **是** `Exception` 的子类（`src/freegraph/contracts/errors.py:102` · `FreegraphError(Exception)` 在 `:24`）⇒ ⇒ **`except GraphInterrupt` MUST 写在 `except Exception` 之前** ⇒ ⇒ **`_TaskOutcome.error` MUST 只装「真异常」**（`GraphInterrupt` 走 `interrupts` 通道）⇒ ⇒ 否则 T034 的「取第一个非空 `error`」会把**中断误判为首个异常** ⇒ 直接冲击 FR-014（真异常优先）<br>⚠️ **中途感知失败（取消语义的前提 · MUST · 2026-11-13 分析轮补记）**：主线程 MUST 用 `concurrent.futures.wait(..., return_when=FIRST_EXCEPTION)`（或等价手段）**在轮末之前**感知到「**墙钟时刻第一个**失败」⇒ 立即调用 `_cancel_pending`（T011）⇒ ⇒ **MUST NOT** 等到轮末统一收 future 时才取消 ⇒ 否则排队任务**早已被启动** ⇒ T030 的**机制级**夹具（排队任务 `cancel()` → `True`）**必红** ⇒ ⇒ 轮末再统一收全部 future 并产出 `_TaskOutcome` 列表（顺序 = **节点名序**）
- [X] T011 在 `src/freegraph/runtime/_concurrency.py` 实现**取消语义** `_cancel_pending(futures) -> None`：**墙钟时刻第一个**真实异常出现时（⚠️ **2026-11-13 分析轮补记**：= **中途**感知到的那一个 ⇒ **MUST NOT** 等轮末的「节点名序选取」之后才取消 —— 二者是**两个独立口径**，见 spec FR-003 的「口径分离」段）⇒ 遍历**未完成**的 future 调 `.cancel()`（**排队未启动**者返回 `True` ⇒ 不执行；**运行中**者返回 `False` ⇒ **不中断**、但**被等待**）⇒ MUST **NOT** 取消运行中的任务 ⇒ MUST **NOT** 等待未启动者
- [X] T012 在 `src/freegraph/runtime/superstep.py` 的两个入口加 **keyword-only** 参数 `max_concurrency: int | None = None`：`run_super_step(spec, state, *, max_concurrency=None)` · `run_super_steps(spec, state=None, *, max_steps=10007, max_concurrency=None)`；既有参数的名字 / 顺序 / 语义**一字不动**；加**入口即校验**（非 `int`/`None` ⇒ 内置 `TypeError`；`< 1` ⇒ 内置 `ValueError`；两者均**点名该参数**）⇒ ⚠️ **哪怕本轮没有节点要跑也 MUST 报错** ⇒ `bool` 按 `int` 收（**上游同款**）
- [X] T013 在 `src/freegraph/runtime/superstep.py` 把 `_execute_node`（`:712`）拆成两半：`_execute_node_pure(spec, node, node_input)`（**只**调 `node.run` + `_normalize_node_result(result, spec.nodes)` 归一 ⇒ **零共享状态写**）与 `_commit_outcome(state, node_name, outcome)`（**轮末**落回 `state.node_versions` **+1** 与 `state.dynamic_edges` 整体替换）⇒ 执行期 MUST **NOT** 改写 `SchedulerState` ⇒ ⚠️ **`spec`（或节点名集合）MUST 随参传入**：归一需要**节点名集合**才能解析 `Command.goto`（`Command.PARENT` / 终止标记 / 非法目标 ⇒ `superstep.py:476-479`）⇒ **MUST NOT** 丢掉 `spec` ⇒ 否则破 FR-012 / 裁定 15 / 承接 H-2
- [X] T014 在 `src/freegraph/runtime/superstep.py` 改 `_run_round`（`:903`）—— ⚠️ **阶段编号与职责 MUST 与 `contracts/concurrency-contract.md` **§3**（**「一个 super-step 的七个阶段」· 2026-11-13 拍板的**唯一权威**）· spec 的 T-10 · B7F1 契约 §4 的阶段表**四方一致**：**阶段 ① / ② / ④ / ⑤ 的语义与编号逐字不变**；**阶段 ③**（**任务执行**）改为调用 `run_tasks_concurrently`（提交顺序 = **节点名序**）⇒ **并发执行**；**阶段 ③′**（**判定与落回**）：**只做判定与落回 · 不抛任何异常** —— 判「有真实异常」⇒ **不合并任何写入** + **调度状态不落回**（**整轮原子**）；否则 ⇒ **成功节点照常落回** · **被中断节点不落回**（**没完成** ⇒ 恢复时重跑）⇒ 收集中断载荷；**阶段 ⑥**（**收尾** · **唯一的「抛出」点**）：有真实异常 ⇒ **抛出**（原对象）⇒ 中断元组**随之丢弃**；否则若有中断 ⇒ **合并抛出**一个 `GraphInterrupt`（载荷 = **元组** · **节点名序**）⇒ ⇒ 原「按节点表顺序串行执行」一条**拆分而不删**
- [X] T015 在 `src/freegraph/runtime/superstep.py` **只订正 docstring 的残留措辞**（**逻辑零改动**）⇒ 三处：① `_group_writes`（`:759`）的「值按**节点表顺序**排列（契约 §5.1）」→「值按**节点名序**排列（**上游同款** · P2-c 已落地）」② `_determine_triggers`（`:417`）的「按**节点表顺序**」→ 节点名序 ③ `_execute_node`（`:712`）的「按**节点表顺序**串行执行」→「**并发**执行（顺序 = **节点名序** · **上游同款**）」⇒ ⚠️ `_group_writes` 的既有实现**已是** `for node_name in sorted(spec.nodes)` ⇒ **不是**「由节点表顺序改为节点名序」⇒ **MUST NOT** 改逻辑、**MUST NOT** 另写一条合并路径（**T-10 / T-11** 的**源码侧**对应项）
- [X] T016 [P] 产出 **B7F1 契约与规格**的**回溯修订清单**（**本任务不改任何文件** · 只落一份逐条清单到 `harness/verification/B12F1/manual-verification.md` 的「**验证步骤**」段（⚠️ 清单属**待办步骤** ⇒ **MUST NOT** 落「遗留问题」段 · 遗留问题段只放**已知限制**））：**T-1**（`specs/b7f1-superstep-loop/contracts/superstep-contract.md` **§5.3** 的 `executed` 措辞 ⇒「本轮**被启动过**的节点 · 按**节点名序**」· 含被中断的节点 · 不含被取消的节点）**T-2**（同文件 **§1** 两行入口签名各**追加** `*, max_concurrency: int | None = None`）**T-3**（`specs/b7f1-superstep-loop/spec.md` **FR-013** ⇒「**节点名序**」）**T-4**（同契约 **§4** 阶段 ①/③ 与 **§5.1** 批量行里**残留**的「节点表顺序」措辞）**T-5**（同契约 **§5.3** 的 `steps` 追加「挂起时如实计」分支 · 载体归 B10F1）**T-7**（同契约 **§7** 的 **I-13** 加注记「P2-b 之后首次成立」）**T-8**（同契约 **§7** 的 **I-12** ⇒「**节点名序 == 报告顺序**」+ `tests/runtime/test_superstep_contract.py` 的 `test_i12` 的 docstring / 命名）**T-10**（同契约 **§4** 的**标题**「五阶段」+ 阶段 ③ 行「按**节点表顺序串行**执行」⇒ 阶段 ③ **细分**为 ③（**并发执行**）/ ③′（**判定与落回**）+ **追加**阶段 ⑥（**收尾**）⇒ ① / ② / ④ / ⑤ 的语义与编号**逐字不变**）**T-11**（`specs/b7f1-superstep-loop/spec.md` **FR-013** 的「**执行**」承诺 ⇒ 拆分为「合并 / 报告顺序 = **节点名序**」+「执行的**时间**先后**不确定**」⇒ **顺序承诺本身不撤销** + 其 Out of Scope 那句「FR-013 的顺序承诺届时失效」的**对账**）⇒ ⚠️ **T-6** 的落笔在 **T069**（**7** 处顺序敏感断言的拆分 · ⚠️ T007 实跑据实）· **T-9** 的落笔在 **T071**（B10F1 结果键接线）⇒ 本清单**不含**这两项

- [X] T017 [P] **扩展差分探针框架**以承载 **D-01…D-15**（⚠️ **FR-026 的前置** · 现有 `Scenario`（`:51-72`）**无** `max_concurrency` / **无**时间窗 / **无**异常对象 identity / **无** `GraphInterrupt` 载荷 ⇒ ⇒ **D-01…D-15 在现有模型下不可实现**）：`tests/differential/parity_probe.py` ⇒ ① `Scenario` 增**可选**钩子：`max_concurrency: int | None = None` · **屏障 / 时间窗**记录 · **节点抛异常 / 抛 `GraphInterrupt`（1-元组写法）**的声明 ② `run_freegraph`（`:81`）⇒ 把 `max_concurrency` 透传给 `run_super_steps` · **捕获异常对象**（供 `is` 比对）· **捕获 `GraphInterrupt.args[0]`** ③ `run_upstream`（`:142`）⇒ 提取结果的 **`__interrupt__`** 键（上游**根图抑制**）④ 比较器扩展 ⇒ 支持「**集合比较**（判 `SAME`）」与「**顺序比较**（判 `STRICTER`）」两态 ⇒ ⚠️ **MUST NOT** 改动既有 **15** 个场景的行为与判词（只**加**能力）⇒ 既有差分门禁**恒绿** ⇒ ⚠️ **上游缺席即 skip** 的既有纪律**不变**

**Checkpoint**: 骨架就位（**并发尚未正确** ⇒ US1 的测试此时 MUST 失败）

---

## Phase 3: User Story 1 - 同一轮的两个节点都真的并行跑（Priority: P1）🎯 MVP

**Goal**: 同一 super-step 内的多个节点**真的同时**在跑（不串行化）· 并发度**有上限**且与上游同款。

**Independent Test**: 给两个节点各装一个**屏障夹具**（两边都到齐才放行）⇒ 串行执行会**死锁**、
并发执行会**放行** ⇒ 单独实现本故事即可得到一个可验收的垂直切片。

### Tests for User Story 1（MUST 先写 · MUST 先失败）

- [X] T018 [P] [US1] 屏障夹具测试写入 `tests/runtime/test_superstep_concurrency.py`：两个节点各等一个 `threading.Barrier(2, timeout=…)` ⇒ 断言**屏障被放行**（串行下**超时** ⇒ 测试先失败）+ 断言两者**执行时间窗重叠时长 > 0** + 断言「后一个的开始 ≥ 前一个的结束」的次数 == **0**
- [X] T019 [P] [US1] 副作用计数测试写入 `tests/runtime/test_superstep_concurrency.py`：两个节点各把一个计数器 **+1** ⇒ 断言各自计数 **== 1**（不是 0 · 也不是 2）
- [X] T020 [P] [US1] 节点名序测试写入 `tests/runtime/test_superstep_concurrency.py`：两节点的**声明顺序**与**名字顺序相反** ⇒ 断言 `SuperStepResult.executed` **按节点名序**排列（**上游同款** · `_algo.py:482`）⇒ 声明顺序**打乱**时执行序列**不变**
- [X] T021 [P] [US1] 零悬挂线程测试写入 `tests/runtime/test_superstep_concurrency.py`：断言一轮结束后 `threading.active_count()` 回到**轮前**的值 ⇒ 且连续运行 **≥ 10** 轮后进程内线程数**不增长**
- [X] T022 [P] [US1] 并发度上限测试写入 `tests/runtime/test_superstep_concurrency.py`：缺省（`max_concurrency=None`）⇒ 断言**同时在跑**的任务数 **≤ `min(32, cpu+4)`**；显式 `max_concurrency=N` ⇒ 断言实际并发度 == `min(本轮任务数, N)`（⚠️ **N 不被 32 再夹** · 用 `N=100` + 大量节点验证）
- [X] T023 [P] [US1] 取值校验测试写入 `tests/runtime/test_superstep_concurrency.py`：传 `"x"` ⇒ 断言抛内置 `TypeError` 且**消息点名该参数**；传 `0` ⇒ 内置 `ValueError` 且**点名**；⚠️ **零节点的一轮**传非法值 ⇒ **同样抛**
- [X] T024 [P] [US1] 串行基线测试写入 `tests/runtime/test_superstep_concurrency.py`：`max_concurrency=1` ⇒ 断言逐个执行（**无重叠**）且**副作用计数仍各 == 1**

### Implementation for User Story 1

- [X] T025 [US1] 实现**并发度上限**与**入口校验**：`src/freegraph/runtime/_concurrency.py` 的 `_resolve_cap`（T009）+ `src/freegraph/runtime/superstep.py` 两入口的校验（T012）⇒ **零节点不建池**
- [X] T026 [US1] 实现**阶段 ③ 的并发执行**：`src/freegraph/runtime/superstep.py` 的 `_run_round`（T014）调用 `run_tasks_concurrently`（T010）⇒ 每轮新建 + 关闭线程池 ⇒ **零悬挂线程**

**Checkpoint**: User Story 1 可独立验收（**A1**）⇒ 屏障放行 + 计数各 1 + 节点名序 + 并发度上限

---

## Phase 4: User Story 2 - 节点抛异常时拿到的是原始异常（Priority: P2）

**Goal**: 首个异常以**原始类型与消息**抛出（**对象 identity 相同**）· 其余失败**可见** · 失败时**取消**排队未启动者。

**Independent Test**: 让节点抛一个自定义异常 ⇒ 断言捕获到的**异常类型**、**消息**与**异常对象 identity**
与节点内抛出的一致；再断言**下游节点一次都没跑**。

### Tests for User Story 2（MUST 先写 · MUST 先失败）

- [X] T027 [P] [US2] 异常 identity 测试写入 `tests/runtime/test_superstep_errors.py`：节点抛 `ValueError("boom")` ⇒ 断言 `type(caught) is ValueError` · `str(caught) == "boom"` · **`caught is raised_by_node`**（对象 identity）· 被包装次数 == **0**
- [X] T028 [P] [US2] 首个异常选取测试写入 `tests/runtime/test_superstep_errors.py`：两个节点分别抛 `ValueError` / `KeyError`（**名字顺序与声明顺序相反**）⇒ 断言抛出的是**节点名序最靠前**的那个 ⇒ 且**重复运行 ≥ 3 次恒定**（**确定性** · **X-1**）
- [X] T029 [P] [US2] 附注格式测试写入 `tests/runtime/test_superstep_errors.py`：一轮内两个节点失败 ⇒ 断言抛出异常的 `__notes__` **恰好 1 条**且**三样齐全**（**节点名** · **异常类型名** · **消息逐字**）⇒ 格式为 `其它并发失败 · 节点 <节点名>：<异常类型名>: <异常消息>` ⇒ 附注**未改变**类型 / 消息 / identity（**X-2**）
- [X] T030 [P] [US2] 取消语义测试写入 `tests/runtime/test_superstep_errors.py`：**机制级**夹具（占住唯一 worker 的慢任务 + 一个排队任务 + 一个立即失败的任务）⇒ 断言排队任务的 `cancelled() == True`（**不执行**）且运行中任务**跑完并被等待**（未被中断）；⚠️ **端到端** MUST **NOT** 断言「排队者一定没跑」⇒ 只断言「本轮最后被启动了哪些节点」与上游**逐项相等**（**X-1** 同款 · research **E-2f/E-2g**）
- [X] T031 [P] [US2] 整轮原子测试写入 `tests/runtime/test_superstep_errors.py`：一轮内一个节点抛异常、另一个**跑成功并写入** ⇒ 断言**全部**通道值 == **轮初**（逐字）· **写入版本不推进** · 「跑成功者的写入生效」次数 == **0**（**X-3** ⇒ 比上游更严）
- [X] T032 [P] [US2] 后续轮不执行测试写入 `tests/runtime/test_superstep_errors.py`：断言**下游节点**的执行计数 == **0**
- [X] T033 [P] [US2] 调度状态不落回测试写入 `tests/runtime/test_superstep_errors.py`：出错轮后断言**全部**节点的 `node_versions` 与 `dynamic_edges` == **轮初**（⇒ 无**幽灵触发**）

### Implementation for User Story 2

- [X] T034 [US2] 实现**结果槽的异常采集**与**首个异常选取**：`src/freegraph/runtime/_concurrency.py`（工作线程捕获 `Exception` ⇒ 存入 `_TaskOutcome.error` ⇒ ⚠️ **MUST 只装真异常** —— `GraphInterrupt` 走 `interrupts` 通道 · 捕获顺序见 T010）⇒ 按**节点名序**取第一个非空 `error`（⚠️ 这是**抛出**口径 · **确定** · **X-1**）⇒ ⚠️ **MUST NOT** 与「**取消**的口径」（= **墙钟**第一个失败 · T011）混为一谈 ⇒ 二者**可能不是同一个异常**（见 spec FR-003 的「口径分离」段）
- [X] T035 [US2] 实现**取消**与**等待**：`src/freegraph/runtime/_concurrency.py` 的 `_cancel_pending`（T011）⇒ 在首个真实异常出现时取消**未完成**的 future ⇒ **运行中者不中断**、但**被等待**（线程池 `shutdown(wait=True)`）
- [X] T036 [US2] 实现**其余失败的附注**：`src/freegraph/runtime/_concurrency.py` ⇒ 按**节点名序**遍历其余失败 ⇒ 对抛出的那个异常调 `add_note(...)`（固定格式 · 三样齐全）⇒ ⚠️ **已取消任务**的异常**不收集**
- [X] T037 [US2] 实现**出错轮的原子落回**：`src/freegraph/runtime/superstep.py` 的阶段 ⑥（T014）⇒ 有真实异常 ⇒ **不合并任何写入**（含跑成功者）· **不落回**调度状态 ⇒ 通道值保持轮初（**整轮原子**）

**Checkpoint**: User Story 2 可独立验收（**A2**）⇒ 异常原样 + 附注可见 + 取消语义 + 整轮原子

---

## Phase 5: User Story 3 - 多个中断被完整收集（Priority: P3）

**Goal**: 多个节点同时中断 ⇒ **合并抛出**一个 `GraphInterrupt`（载荷 = **元组** · **节点名序**）· 中断**不是**「出错」。

**Independent Test**: 两个节点各抛一个 `GraphInterrupt`（载荷不同）⇒ 断言捕获到的**载荷是长度 == 2 的元组**
且各元素的 `.value` **逐字正确**。

### Tests for User Story 3（MUST 先写 · MUST 先失败）

- [X] T038 [P] [US3] 中断合并测试写入 `tests/runtime/test_superstep_errors.py`：两个节点各 `raise GraphInterrupt((Interrupt(value="approve-A", id="a"),))` —— ⚠️ **1-元组**（**上游同款** · `langgraph/types.py:967`；传**单个** `Interrupt` 会抛 `TypeError`）⇒ ⚠️ 本 feature **不**接线 `interrupt()` · 归 B10F1）⇒ 断言捕获到**一个** `GraphInterrupt`（**不是**两个）且 `exc.args[0]` 是 **元组** · **长度 == 2** ⇒ ⚠️ 且 `exc.args[0][0]` 是 **`Interrupt` 对象**（带 `.value` / `.id`）⇒ **不是**嵌套元组
- [X] T039 [P] [US3] 中断元素测试写入 `tests/runtime/test_superstep_errors.py`：断言每个元素的 **`.value`** 与 **`.id`** 与节点内传入的**逐字**相同（内核**原样收集** · 不生成 / 改写 / 校验）⇒ 元素被包装或改写次数 == **0**；⚠️ **补充（澄清轮 Q-E · 裁定 20 · SC-010 的断言范围）**：另加一个**载荷缺 `.id`** 的节点 ⇒ 断言内核**原样收集**（**不生成 `.id`** · **不包装** · **不校验**）⇒ **MUST NOT** 报错、**MUST NOT** 中断流程（该情形**不在** SC-010 的断言范围内）⇒ 且元组**长度仍 == 本轮中断的节点数**（**FR-004**「一个节点**至多**贡献一个中断」）
- [X] T040 [P] [US3] 中断元组顺序测试写入 `tests/runtime/test_superstep_errors.py`：断言元组内顺序 == **节点名序** ⇒ 且**重复运行 ≥ 3 次逐项相同**（**X-7** ⇒ 比上游更严）
- [X] T041 [P] [US3] 中断与写入测试写入 `tests/runtime/test_superstep_errors.py`：一个节点中断、另一个**跑成功并写入** ⇒ 断言**中断节点的写入不生效** · **其它节点的写入照常合并**（**中断轮合并**）⇒ 且**出错轮**（真异常）时**一个都不合并** ⇒ 两条**分界清晰**
- [X] T042 [P] [US3] 中断轮落回测试写入 `tests/runtime/test_superstep_errors.py`：断言**成功节点**的 `node_versions` **照常落回**（**+1**）· **被中断节点不落回**（**没完成** ⇒ 恢复时重跑 · **上游同款**）
- [X] T043 [P] [US3] 中断轮不产出结果对象测试写入 `tests/runtime/test_superstep_errors.py`：断言入口在抛出中断时**不返回** `SuperStepResult`（四字段一个都不给）⇒ 且调用方从**自己持有的 `SchedulerState`** 读到的通道值**已是合并后**的
- [X] T044 [P] [US3] 异常优先测试写入 `tests/runtime/test_superstep_errors.py`：一轮内既有真异常又有中断 ⇒ 断言抛出的是**真实异常**（原对象）· 中断元组**随之丢弃**（**上游同款** · **E-2e**）⇒ 中断**不掩盖**失败
- [X] T045 [P] [US3] 中断后暂停测试写入 `tests/runtime/test_superstep_errors.py`：断言中断轮之后**不进入下一轮**（下游节点执行计数 == **0**）⇒ ⚠️ **2026-11-13 分析轮补记（对齐 SC-012 的口径订正）**：**MUST NOT** 断言「被中断的节点在下一轮不被触发」——本 feature 中断轮**不进入下一轮** ⇒ **不存在「下一轮」** ⇒ 该断言是**空转**；⇒ 改断言「**被中断的节点确实被启动过**」（其节点函数确实执行了 ⇒ 间接判定 · spec SC-009 同款口径）⇒ 且「被中断节点在**恢复**时会被**重跑**」的义务归 **B10F1**（**下游承接 D-1**）⇒ 本 feature **MUST NOT** 把它写成硬判据（会与 FR-010 矛盾）

### Implementation for User Story 3

- [X] T046 [US3] 实现**中断的收集**：`src/freegraph/runtime/_concurrency.py` ⇒ 工作线程捕获 `GraphInterrupt` ⇒ 把其 **`args[0]`（≡ `payload`）的**元素**（`Interrupt` 对象 · 原样）**存入 `_TaskOutcome.interrupts` ⇒ ⚠️ **MUST NOT** 把 `payload` **本身**（元组）塞进去（⇒ 嵌套元组 ⇒ 元素**没有** `.value` / `.id`）⇒ 该节点的 `writes` 恒空（**未完成**）
- [X] T047 [US3] 实现**中断的合并抛出**：`src/freegraph/runtime/superstep.py` 的阶段 ⑥（T014）⇒ 按**节点名序**收集全部中断载荷 ⇒ 合并成**一个** `GraphInterrupt`（载荷 = **元组**）⇒ **抛出** ⇒ ⚠️ **MUST NOT** 落进 `SchedulerState` 的字段 ⇒ ⚠️ **MUST NOT** 给 `SuperStepResult` 加第 5 个字段（**裁定 25**）

**Checkpoint**: User Story 3 可独立验收 ⇒ 中断合并为元组 · 顺序确定 · 中断轮合并其它节点写入

---

## Phase 6: User Story 4 - 并发不改变状态的语义（Priority: P4）

**Goal**: 并发与串行（`max_concurrency=1`）的**最终状态**与**待写入序列****逐项相等** · 结果**可复现**。

**Independent Test**: 同一份规格（带**非交换归约器**）分别以并发 / 串行 / 重复 **≥ 3** 次运行 ⇒
逐项比对最终状态与待写入序列。

### Tests for User Story 4（MUST 先写 · MUST 先失败）

- [X] T048 [P] [US4] 并发 == 串行测试写入 `tests/runtime/test_superstep_concurrency.py`：同一份规格分别以**缺省**与 `max_concurrency=1` 运行 ⇒ 断言**最终状态逐项相等**（含每个通道的值的**元素顺序**）· **待写入序列逐项相等** ⇒ 差异项数 == **0**
- [X] T049 [P] [US4] 可复现测试写入 `tests/runtime/test_superstep_concurrency.py`：同一份规格（带**非交换归约器**）重复运行 **≥ 3** 次 ⇒ 断言最终状态与执行节点序列**逐项相等**（差异 == **0**）
- [X] T050 [P] [US4] 归并顺序测试写入 `tests/runtime/test_superstep_concurrency.py`：同轮两个节点写**同一个归约通道** ⇒ 断言该通道的元素顺序 == **节点名序**（**非交换归约器**的结果**可复现**）
- [X] T051 [P] [US4] `goto` 不吞并测试写入 `tests/runtime/test_superstep_concurrency.py`：同轮多个节点各自返回 `Command(goto=…)` ⇒ 断言每个节点各自的跳转目标在下一轮**全部被触发** ⇒ 吞并次数 == **0**
- [X] T052 [P] [US4] `Command.update` 路径测试写入 `tests/runtime/test_superstep_concurrency.py`：断言 `Command.update` 的写入与普通返回值走**同一条**批量合并路径 ⇒ 未知 key 仍抛 `InvalidUpdateError`
- [X] T053 [P] [US4] 多节点 × 多命令顺序测试写入 `tests/runtime/test_superstep_concurrency.py`：断言归并顺序 ==「**节点名序 × 命令列表顺序**」
- [X] T054 [P] [US4] 节点入参口径测试写入 `tests/runtime/test_superstep_concurrency.py`：断言节点收到的入参 == `read_channels(子映射)` 的结果（**逐字** · 含 **key 顺序**）⇒ 且入参**不受**同轮其它节点产出的影响
- [X] T055 [P] [US4] 执行期不改正式值测试写入 `tests/runtime/test_superstep_concurrency.py`：断言节点执行期间从外部观察到的通道值 == **本轮开始前**的值

### Implementation for User Story 4

- [X] T056 [US4] 实现**节点名序**的合并顺序：`src/freegraph/runtime/superstep.py` 的 `_group_writes`（T015）⇒ 同一通道上多个写入的归并顺序 == **节点名序** ⇒ **MUST NOT** 依赖完成时刻
- [X] T057 [US4] 实现**结果槽按节点名序的收集**：`src/freegraph/runtime/superstep.py` 的阶段 ④（T014）⇒ 待写入的分组与顺序**恒定** ⇒ 与串行**逐项相等**

**Checkpoint**: User Story 4 可独立验收 ⇒ 并发 == 串行 · 顺序可复现

---

## Phase 7: User Story 5 - 与上游同款（差分可判定）（Priority: P5）

**Goal**: 交付**一组**「上游 ↔ freegraph 同场景对跑」的**差分探针场景** ⇒ 任何 feature 让地基与上游分叉 ⇒ **差分用例立刻红**。

**Independent Test**: 跑 `tests/differential/parity_probe.py` 的**本 feature 场景组** ⇒ 逐条判词（`SAME` / `STRICTER` / `DIFF`）**全部成立**。

### Tests for User Story 5（MUST 先写 · MUST 先失败）

> ⚠️ **判词纪律**：上游**自身不确定**的场景（**D-13 / D-15**）MUST **NOT** 逐字比对两侧 ⇒
> MUST 拆成「freegraph 一侧**重复跑 ≥ 3 次恒定**」+「上游一侧**只断言也在同一批里**」⇒ ⇒ 差分门禁**偶发红次数 == 0**。

- [X] T058 [P] [US5] 差分场景 **D-01**（并发重叠）追加进 `tests/differential/parity_probe.py`：断言两侧的执行时间窗**重叠 > 0**（或屏障夹具放行）· 副作用计数各 == 1 ⇒ 判词 `SAME`
- [X] T059 [P] [US5] 差分场景 **D-02**（首个异常的对象 identity 与消息）追加进 `tests/differential/parity_probe.py`：断言两侧捕获到的异常**类型 / 消息**逐字一致 ⇒ 判词 `SAME`
- [X] T060 [P] [US5] 差分场景 **D-03**（取消语义）追加进 `tests/differential/parity_probe.py`：断言**端到端**「本轮最后实际被启动了哪些节点」两侧**逐项相等**（⚠️ **不**比「取消与否」⇒ 上游端到端 **15/15** 次排队者照跑）⇒ 判词 `SAME` ⇒ ⚠️ **机制层**（「尚未启动的任务 `cancel()` → `True`」· 契约 §11 的 **I-17**）由**单元夹具**承担（`tests/runtime/test_superstep_errors.py`）⇒ **MUST NOT** 在差分探针内做机制级断言
- [X] T061 [P] [US5] 差分场景 **D-04**（中断合并成一个异常且载荷为元组）追加进 `tests/differential/parity_probe.py`：上游从**结果键 `__interrupt__`** 取、freegraph 从**异常的 `args[0]`** 取 ⇒ 比**集合**（**不**比顺序）⇒ 判词 `SAME`
- [X] T062 [P] [US5] 差分场景 **D-05**（中断节点的写入被丢弃 / 其它节点照常合并）追加进 `tests/differential/parity_probe.py` ⇒ 判词 `SAME`
- [X] T063 [P] [US5] 差分场景 **D-06**（并发 == 串行）追加进 `tests/differential/parity_probe.py` ⇒ 判词 `SAME`
- [X] T064 [P] [US5] 差分场景 **D-07…D-12** 追加进 `tests/differential/parity_probe.py`：节点名序 / 归约顺序 / 异常优先 / 多会话隔离 / 并发度上限 / `goto` 不吞并 ⇒ 判词均 `SAME`
- [X] T065 [P] [US5] 差分场景 **D-13**（首个异常的选取）追加进 `tests/differential/parity_probe.py`：freegraph 一侧**重复跑 ≥ 3 次每次同一个异常**；上游一侧**只断言**也在同几个失败节点之中 ⇒ 判词 `STRICTER` + **理由**（上游自身不确定）
- [X] T066 [P] [US5] 差分场景 **D-14**（其余失败的可见性）追加进 `tests/differential/parity_probe.py`：上游**丢弃**其余异常 · freegraph **附注**记录 ⇒ 判词 `STRICTER` + **理由**
- [X] T067 [P] [US5] 差分场景 **D-15**（中断元组内元素顺序）追加进 `tests/differential/parity_probe.py`：freegraph 一侧**重复跑 ≥ 3 次顺序逐项相同**；上游一侧**只断言元素集合相同** ⇒ 判词 `STRICTER` + **理由**

### Implementation for User Story 5

- [X] T068 [US5] 把场景组接入 `tests/differential/test_parity_probe.py` 的 pytest 包装 ⇒ **CI 的 Linux 全量档真跑**（装了上游差分组的作业）⇒ 上游**缺席即 skip**（非失败 · **B5F2 纪律**）⇒ ⇒ **不新增门禁编号**（既有档位内加跑）

**Checkpoint**: User Story 5 可独立验收（**A4**）⇒ 差分场景组全绿 · 偶发红次数 == **0**

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 跨故事的回溯修订 · 结构纪律 · 覆盖率 · 人工验证 · 追认。

- [X] T069 [P] **拆分**既有 **7 处**顺序敏感断言（**T-6** · ⚠️ **T007 实跑据实**：初版 **10** 处 ⇒ **7** 处）：`tests/runtime/test_command_contract.py` · `tests/runtime/test_command_goto_semantics.py` · `tests/runtime/test_command_list.py` · `tests/runtime/test_command_merge_parity.py` · `tests/runtime/test_superstep_trigger.py` ⇒ 每处**拆成两条** —— ① **串行模式**（`max_concurrency=1`）**保留原逐字顺序断言**（**一条不删**）② **并发模式**（缺省）断言**顺序无关但有力**的性质（**元素多重集相等** + **次数相等**）⇒ MUST **NOT** 写成「跑过了就行」的弱断言
- [X] T070 [P] 落笔**回溯修订 T-1 / T-2 / T-3 / T-4 / T-5 / T-7 / T-8 / T-10 / T-11**：`specs/b7f1-superstep-loop/contracts/superstep-contract.md`（§1 / §4 / §5.1 / §5.3 / §7）· `specs/b7f1-superstep-loop/spec.md`（FR-013）· `tests/runtime/test_superstep_contract.py`（`test_i12` 的 docstring / 命名）⇒ **拆分而不删** ⇒ 逐条记录改前 / 改后 ⇒ ⚠️ **T-10 / T-11**（2026-11-13 对账补记）：契约 §4 的**标题**「五阶段」+ 阶段 ③「按**节点表顺序串行**执行」⇒ ③（**并发执行**）/ ③′（**判定与落回**）+ **追加**阶段 ⑥（**收尾**）· B7F1 spec FR-013 的「**执行**」承诺 ⇒ 拆分为「合并 / 报告顺序 = **节点名序**」+「执行时序**不确定**」⇒ **顺序承诺本身不撤销**
- [X] T071 [P] **逐条核对并补齐**下游承接 **D-1…D-7** 的**跨 feature 文档改动**（**只接线 · 逐条最小改动** · **MUST NOT** 重写已落地的段落）⇒ ⚠️ **前六条（D-1…D-6）已于 2026-11-12 全部写入目标提示词初稿**（`harness/features/B10F1_interrupt与resume.md` 两段（D-1 / T-9）· `harness/features/B19F1_TraceSink与current_span.md`（D-3）· `harness/features/B7F2_compile编译.md`（D-4）· `harness/features/B7F3_invoke返回完整状态.md`（D-2 / D-4）· `harness/features/B14F1_Checkpointer协议与MemorySaver.md` 两段（D-5 / D-6））⇒ ⚠️ **第七条（D-7 · B15F1）亦已接线**（**2026-11-13 对账复核** · 宪法 **v1.8.0**）：`harness/features/B15F1_SqliteSaver与状态历史.md` **已含**「承接条款（B12F1 → B15F1 · M3 · `StateSnapshot.interrupts` 的生产者口径 · 2026-11-13 补记）」一段（落盘 **2026-11-13 02:42:45** ⇒ **早于**本 tasks 的对账补记）⇒ ⇒ **本任务 MUST NOT 重复追加**（重复追加会违反宪法 v1.8.0「只接线 · MUST NOT 改动目标提示词初稿的其余内容」）⇒ ⇒ **D-1…D-7 全部转为「只核对」**（**T071 目标清单 = 6 个文件**）⇒ 本任务**只做核对 + 补缺口**（缺口 = **零**；若核对中发现偏差 ⇒ **只做最小追加**）⇒ ⚠️ **2026-11-13 实施期补记**：核对 FR-017 时发现「**并发度旋钮 `max_concurrency` 原样搬进 `RunConfig`**」这条**指名 B7F3 的跨 feature 义务**尚未落进 B7F3 的提示词初稿 ⇒ ⇒ 依宪法 v1.8.0 的承接通则**追加**了一个承接段落（**同文件** · B7F3 的 `RunConfig` 形态 + 并发度缺省 / 取值口径）⇒ ⇒ **仍未改动** B7F3 提示词初稿的**其余**内容：① 逐条比对 spec「下游承接」表与目标提示词初稿的**逐字口径**（`__interrupt__` 元素 = **元组**（元素 = `Interrupt`）· **B10F1 负责把异常转成结果键** · 挂起时 `steps` 如实计的**载体**归 B10F1 · 并发分组由 **B19F1** 自行在调度层取得 · 报告顺序 = **节点名序** · 真异常同现时中断元组随 pending writes 留痕 · `StateSnapshot.interrupts` 由 **B15F1** 生产）② 仅对**缺口**做最小追加 ③ 差异逐条记入 `harness/verification/B12F1/manual-verification.md` 的「实际输出」段 ⇒ **MUST NOT** 改动目标提示词初稿的**其余**内容
- [X] T072 [P] 结构纪律的核验测试写入 `tests/runtime/test_superstep_concurrency.py`：`freegraph.runtime.__all__` 的符号数 == **20** · L1 **20** / 门面 **7** 符号面**一字不动**（⚠️ **2026-11-13 订正 · X1 / R-10**：L1 基线由 **18** 改为 **20** —— **上游对齐批次 P3**（发起者已批准）已扩了 L1 的公开符号面（新增 `Interrupt` / `PregelTask`）⇒ ⇒ **本 feature 对 L1 零新增** ⇒ 断言 MUST 为「与 `specs/b2f1-contracts-protocols/contracts/public-api.md` §0 的清单**集合相等**」⇒ **不硬编码 18**） · `SuperStepResult` 的**字段数 == 4**（⚠️ **无** `interrupts` 字段 · **裁定 25**）· `SchedulerState()` 的**构造签名逐字不变**（**零新增字段**）· 两个入口的**既有参数**名字 / 顺序 / 语义**一字不动**（只**增** keyword-only 的 `max_concurrency`）· L2 → L3/L4/L5 的依赖边数 == **0** · 既有门禁编号 **G1–G30** 连续无跳号（总数 **30**）
- [X] T073 [P] 取覆盖率：`coverage run --branch -m pytest tests/runtime tests/differential -q` ⇒ 本 feature **新增**代码的**行 / 分支覆盖率 == 100%**（**SC-020**）⇒ 实测输出记入 `harness/verification/B12F1/manual-verification.md`
- [X] T074 [P] 核验**署名头**（宪法原则 X）：本 feature 的**每个**新 `.py`（`src/freegraph/runtime/_concurrency.py` · `tests/runtime/test_superstep_concurrency.py` · `tests/runtime/test_superstep_errors.py` · `harness/verification/B12F1/acceptance.py`）MUST 带署名头且 docstring 是首个语句 ⇒ 由既有 **G30** 全仓扫描覆盖
- [X] T075 [P] 核验**不越界**（**SC-023**）：`src/freegraph/runtime/` 内 MUST **NOT** 出现 `interrupt()` 的接线 · `__interrupt__` 结果键 · async 构件 · `Send` · `recursion_limit` · checkpoint · 重试 / 超时 · 多源汇合边 ⇒ `src/freegraph/runtime/channel.py` **零改动** ⇒ `src/freegraph/contracts/**` **零改动** ⇒ ⚠️ **同时核验 SC-018 的「零环境变量 / 零出站」**：新增模块 `src/freegraph/runtime/_concurrency.py` 内 MUST **NOT** 出现 `os.environ` / `os.getenv` / `socket` / `urllib` / `requests` / `httpx` / 任何文件 I/O 调用（`os.cpu_count()` 是**系统调用**·**非**环境变量 ⇒ **允许**）⇒ 断言：命中数 == **0**
- [X] T076 [P] 核验**上游引用纪律**（**SC-024**）：`src/freegraph/runtime/_concurrency.py` · `src/freegraph/runtime/superstep.py` · `tests/runtime/test_superstep_concurrency.py` · `tests/runtime/test_superstep_errors.py` · `tests/differential/parity_probe.py` · `harness/verification/B12F1/acceptance.py` 里的上游引用 MUST 带**版本 + `路径:行号`** ⇒ 凭记忆沿用的引用数 == **0**
- [X] T077 跑 `harness/verification/B12F1/acceptance.py` 跑完全部 **14** 道闸口 ⇒ 退出码 == **0** ⇒ 输出记入 `harness/verification/B12F1/manual-verification.md` 的「实际输出」段
- [X] T078 填写 `harness/verification/B12F1/manual-verification.md` 的**五段式**内容（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）· 「来源覆盖表」对 **A1–A4** + **SC-001…SC-029** + **FR-001…FR-026** 的覆盖率 == **100%**（**无来源项数 == 0**）
- [X] T079 在 `harness/verification/B12F1/manual-verification.md` 的「**遗留问题**」段**如实登记**本 feature 的**已知限制**（MUST **NOT** 隐瞒）：① 一个**不返回**的节点会**阻塞**本轮（**DR-3**）② **节点函数会被并发调用** ⇒ **线程安全是用户的责任**（裁定 16）③ 取消**只**对「排队未启动」者生效 ⇒ 用户节点函数**已产生**的外部副作用**取消不掉**（**DR-3**）④ 「真异常 + 中断同现」时那批中断元组**被丢弃**且 v1 **无处留痕**（**X-4** · 临时 · 消解条件 = **B10F1 / B14F1**）⑤ ⚠️ **多会话隔离**（同一份规格连续 / 并发跑两次）**已由 P2-b 落地** ⇒ **MUST NOT** 再列为本 feature 的限制（**V-7**）⑥ ⚠️ **宪法「质量门禁 3 / 4 / 5」的三部分在本 feature 物理不可达成**（门禁 3 的 **C8** 独立回归 · 门禁 4 的「fake 模型跑通验收基线的一轮」· 门禁 5 的「真实模型一轮」）⇒ **如实登记**（**登记项 PR-11**）⇒ **MUST NOT** 伪装成「已通过」⇒ **MUST NOT** 写一条**永久红**的 CI ⑦ ⚠️ **验收契约 A7 的判据差距**（`harness/demo/graph_core.py` 的 **A7** 用例只断言「两个节点都跑了」⇒ **不构成 A1「真并发」判据**）⇒ 由 **T083** 核对并登记 ⇒ **MUST NOT** 把 A7 现状误当作 A1 已通过 ⑧ ⚠️ **立项书 §5.2 的规模数字**（「1,080 行 / 3 人日」）**已被本轮修订超越**（实际以 `tasks.md` 的任务清单为准）⇒ **MUST** 由**发起者**在 feature 收尾时**重估并回写** `立项书.md`（⚠️ 本 feature **MUST NOT** 单方面改动上位文档 ⇒ **只登记**，不代改）
- [X] T080 **【阻断合入】发起者追认**：把 **plan 登记项 PR-1…PR-11** 的**追认文字**写进 `harness/verification/B12F1/manual-verification.md`（**MUST NOT** 由实现者代签 · 宪法原则 V / v1.6.0）⇒ 含 **PR-1**（首个异常的确定性 · **X-1**）· **PR-2**（其余失败的附注 · **X-2**）· **PR-3**（整轮原子含「节点抛真异常」· **X-3**）· **PR-4**（中断元组顺序 · **X-7**）· **PR-5**（根图处置 · **X-4** · 临时）· **PR-6**（多源汇合边不实现 · **X-5**）· **PR-7**（**T-1…T-11** 回溯修订 —— ⚠️ **含 T-10 / T-11**：契约 §4 阶段 ③「串行」→ 并发 + 追加阶段 ③′ / ⑥ · B7F1 spec FR-013「执行」承诺拆分）· **PR-8**（**7** 处断言拆分 · ⚠️ T007 实跑据实）· **PR-9**（落回时机收紧）· **PR-10**（下游承接 **D-1…D-7**）· **PR-11**（⚠️ **宪法「质量门禁 3 / 4 / 5」在本 feature 物理不可达成**：门禁 3 的 **C8** 独立回归（owner = B8F1 / M2）· 门禁 4 的「fake 模型跑通验收基线的一轮」（需 B7F2 / B7F3 / M2）· 门禁 5 + 原则 V 的「真实模型一轮」（需 B25F1 / M4）⇒ **判据一字未改** · **红线照常执行** · **MUST NOT** 写永久红的 CI）⇒ ⚠️ **追认次数 ≤ 1 次** ⇒ **十一条**打包成**一次** ⇒ ✅ **已由发起者于 2026-11-13 追认**（签署栏：`harness/verification/B12F1/manual-verification.md` §5.1.3）
- [X] T081 **【阻断合入】** 确认 `specs/b12f1-concurrency-errors/tasks.md` 的**追溯表**（文末附录）双向齐全：每个 **FR**（26）与每个 **SC**（29）**至少**被一条任务映射 · 每条任务**至少**挂一条 FR ⇒ **plan 登记项 PR-1…PR-11** 的「追认」得以成立
- [X] T082 **【阻断合入】** 订正 **L1 冻结面**的「**18 个**」失准文案（**2026-11-13 对账补记 · X1 / R-10**）：`tests/contracts/test_architecture.py` 的 **G7** docstring / 注释（「公开符号面**恰为 18 个**」⇒ 改为「**清单驱动**（期望值从 `specs/b2f1-contracts-protocols/contracts/public-api.md` §0 解析）· **当前 20 个**」）⇒ ⇒ **MUST NOT** 改动 G7 的**任何断言逻辑**（清单驱动 ⇒ **判据零改动**）⇒ 同时**核对**两处**已落**的订正（`specs/b2f1-contracts-protocols/contracts/public-api.md` §0 的「**恰好 20 个**」+ P3 批次注记 · `specs/b2f1-contracts-protocols/spec.md` FR-012 / SC-017 的**回溯注记**）⇒ ⇒ **核对结果**记入 `harness/verification/B12F1/manual-verification.md` 的「实际输出」段
- [X] T083 **核对**验收契约侧的 **A7** 用例并**登记差距**（⚠️ **2026-11-13 分析轮补记**）：`harness/demo/graph_core.py` 的 **A7** 用例（`:403-441` · 并发与错误传播）现状只断言「两个节点都跑了」（`sorted(out.get("messages") or []) == ["left","right"]`）⇒ ⇒ **不构成 A1「真并发」判据**（**无**执行时间窗 · **无**屏障夹具）⇒ 且它依赖 `StateGraph` / `compile()` / `invoke()` ⇒ 本 feature **无图可跑**（登记项 **PR-11**）⇒ ⇒ **本任务 MUST NOT 改动该文件的逻辑**（**只核对**）⇒ 产出：① 逐条列出 A7 的现有断言与 **A1 / A2** 的差距（**A1** 缺时间窗 / 屏障 · **A2** 缺对象 identity 与「节点名序最靠前」的判定）② 把差距**如实登记**进 `harness/verification/B12F1/manual-verification.md` 的「**遗留问题**」段（并入 **PR-11** 的遗留问题面）③ **MUST NOT** 把 A7 现状误当作 **A1 / A2** 已通过 ⇒ ⇒ **A1 / A2 的真判据**仍由本 feature 的单元用例（`tests/runtime/test_superstep_concurrency.py`）与 `harness/verification/B12F1/acceptance.py` 承担 ⇒ ⇒ **A7 的收紧**归 **B7F2 / B7F3**（门面级）

---

## Dependencies & Execution Order

### 执行闸口（Phase 闸口 · 每道 MUST 全绿才进下一 Phase）

| 闸口 | 位置 | 判据 |
|---|---|---|
| **G-a** | Phase 1 末 | 上游取证工件 · 依赖面 · 判定归属核对完成（**T001–T007** 全绿 · 含 **C-01 探测重跑**）⇒ ⚠️ **2026-11-13 订正**：原写「T001–**T008**」⇒ **T008 属 Phase 2**（Foundational）⇒ 闸口**不得**要求 Phase 2 的任务先行完成 |
| **G-b** | Phase 2 末 | 并发执行器骨架就位 · **差分探针框架就位** · **US1 的测试此时 MUST 失败**（证明测试有效） |
| **G-c** | Phase 3 末 | **A1** 可判定 ⇒ 屏障放行 · 计数各 1 · 节点名序 · 并发度上限 |
| **G-d** | Phase 4 末 | **A2** 可判定 ⇒ 异常原样 · 附注可见 · 取消语义 · 整轮原子 |
| **G-e** | Phase 5 末 | 中断合并为元组 · 顺序确定 · 中断轮合并其它写入 |
| **G-f** | Phase 6 末 | 并发 == 串行 · 顺序可复现 |
| **G-g** | Phase 7 末 | **A4** 可判定 ⇒ 差分场景组全绿 · **偶发红 == 0** |
| **G-h** | Phase 8 末 | **14** 道闸口全绿 + 覆盖率 == 100% + 追溯表双向齐全 + **追认已签** + **L1 冻结面文案已订正（T082）** + ⚠️ **A7 判据差距已核对并登记（T083** · 非阻断合入 · 但 MUST 于 feature 收尾前完成**）** |

### Phase Dependencies

- **Setup (Phase 1)**：无依赖 —— 可立即开始（**T007** 的探测重跑**不阻塞**其余 Setup 任务 ⇒ 但**阻塞** G-a 闸口）
- **Foundational (Phase 2)**：依赖 Setup —— **阻塞**所有用户故事（**T017** 的探针框架扩展 ⇒ **阻塞** US5 的全部 **D-xx** 场景任务）
- **User Stories (Phase 3–7)**：全部依赖 Phase 2 完成 ⇒ 之后**可并行**（若人手允许）
- **Polish (Phase 8)**：依赖所有目标用户故事完成（⚠️ **例外**：**T083** 只**读**既有文件 ⇒
  **可提前**开工，但 MUST **排在 T079 之前** —— 它的产出并入 T079 的「遗留问题」段）

### User Story Dependencies

- **User Story 1 (P1)**：Phase 2 完成后可开工 —— 无其它故事依赖
- **User Story 2 (P2)**：Phase 2 完成后可开工 —— 依赖 **US1** 的并发执行器（同一实现），但**可独立测试**
- **User Story 3 (P3)**：Phase 2 完成后可开工 —— 依赖 **US1** 的并发执行器 + **US2** 的异常采集（同一 `_TaskOutcome`），但**可独立测试**
- **User Story 4 (P4)**：Phase 2 完成后可开工 —— 依赖 **US1**（并发）+ **US2**（错误路径），但**可独立测试**
- **User Story 5 (P5)**：依赖 **US1–US4** 全部完成（差分场景要对比的是**已实现**的行为）⇒ ⇒ **最后一个**

### Within Each User Story

- 测试 **MUST** 先写并 **MUST** 先**失败**（Phase 2 末的 G-b 闸口验证这一点）
- 实现骨架 → 实现语义 → 跑该故事的测试
- 故事完成后再进入下一个优先级

### Parallel Opportunities

- Phase 1 的 **T004 / T005 / T006** 可并行（不同文件）
- Phase 2 的 **T016**（只产出一份清单 · 不改文件）与 **T017**（只扩探针框架 · 不改既有场景）可与 **T008–T015** 并行
- 每个故事的**测试任务**全部标 **[P]** ⇒ 可并行开写
- **T069 / T070 / T071 / T072 / T073 / T074 / T075 / T076 / T082** 可并行（不同文件）
- ⚠️ **T083** 与 **T069 / T070 / T071 / T072 / T073 / T074 / T075 / T076 / T082** 可并行
  （它**只读** `harness/demo/graph_core.py`）⇒ **但 MUST NOT** 与 **T077 / T078 / T079 / T080**
  并行（**同改** `harness/verification/B12F1/manual-verification.md` ⇒ 同文件冲突）⇒
  ⇒ **T083 MUST 排在 T079 之前**（它的产出并入 T079 的「遗留问题」段）
- 不同用户故事可由不同成员并行推进（**US5 除外** ⇒ 它依赖 US1–US4）

---

## Parallel Example: User Story 1

```bash
# 一次性并行启动 US1 的 7 个测试任务（此时它们 MUST 失败 —— 入口仍是串行 ⇒ 屏障超时）：
Task: "屏障夹具测试写入 tests/runtime/test_superstep_concurrency.py"
Task: "副作用计数测试写入 tests/runtime/test_superstep_concurrency.py"
Task: "节点名序测试写入 tests/runtime/test_superstep_concurrency.py"
Task: "零悬挂线程测试写入 tests/runtime/test_superstep_concurrency.py"
Task: "并发度上限测试写入 tests/runtime/test_superstep_concurrency.py"
Task: "取值校验测试写入 tests/runtime/test_superstep_concurrency.py"
Task: "串行基线测试写入 tests/runtime/test_superstep_concurrency.py"
```

---

## Parallel Example: User Story 2 与 User Story 3（判据独立 · 文件不同）

```bash
# US1 完成后 ⇒ 两者的测试任务可同时开工（文件不同 ⇒ 无冲突）：
Task: "异常 identity / 首个异常选取 / 附注格式 / 取消语义 / 整轮原子 / 后续轮不执行 / 调度状态不落回 —— 写入 tests/runtime/test_superstep_errors.py"
Task: "中断合并 / 元素 / 顺序 / 与写入关系 / 落回 / 不产出结果对象 / 异常优先 / 暂停 —— 写入 tests/runtime/test_superstep_errors.py"
```

---

## Implementation Strategy

### MVP First（仅 User Story 1）

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational（**CRITICAL** · 阻塞所有故事）
3. 完成 Phase 3: User Story 1
4. **STOP and VALIDATE**：独立验收 **A1**（屏障放行 + 计数各 1）
5. 可演示 / 可合并

### Incremental Delivery

1. Setup + Foundational ⇒ 地基就位
2. **US1** ⇒ 独立测试 ⇒ 交付（**MVP**）
3. **US2** ⇒ 独立测试 ⇒ 交付（**A2**）
4. **US3** ⇒ 独立测试 ⇒ 交付
5. **US4** ⇒ 独立测试 ⇒ 交付
6. **US5** ⇒ 独立测试 ⇒ 交付（**A4** · 差分门禁**常驻**）
7. Polish ⇒ 回溯修订 + 覆盖率 + 人工验证 + **追认**

### Parallel Team Strategy

1. 全员完成 Setup + Foundational
2. 之后：
   - 成员 A：US2（错误传播）
   - 成员 B：US3（中断合并）
   - 成员 C：US4（语义一致性）
3. **US5** 在 US1–US4 全部完成后由单人推进（差分场景**互相耦合** ⇒ 单人更稳）

---

## Notes

- **[P]** = 不同文件 / 无未完成依赖
- **[Story]** 标签映射到 spec 的用户故事（US1–US5）⇒ 可追溯
- 每个用户故事 MUST **可独立完成、独立测试**
- **先写测试 · 确认失败 · 再实现**
- 每个任务或逻辑组完成后提交
- 任一闸口可停下 ⇒ **独立验证该故事**
- 避免：含糊的任务、同文件冲突、破坏独立性的跨故事依赖
- ⚠️ **禁止**：`git checkout` / `git restore` / `git reset --hard` 覆盖工作区（会**抹除**未提交改动）⇒ 回退**只用**精确的 Edit

---

## 附录 · 任务 ↔ spec 追溯表

> **权威映射**（本表与文首「判据总表」**同步维护**）⇒ **FR 26/26 · SC 29/29 · 任务 83 条**
> ⇒ 追溯表**双向**齐全（宪法原则 VI）。
> ⚠️ **每条任务 MUST 至少挂一条 FR**；每条 FR / SC MUST 至少被一条任务映射。

### FR → 任务

| FR | 主题 | 承载任务 |
|---|---|---|
| **FR-001** | 同轮任务并发执行（线程 · 缺省上限 · 零节点不建池） | T009 · T010 · T018 · T019 · T022 · T025 · T026 · **T083** |
| **FR-002** | 写入收集 = 待写入 → 轮末统一合并 | T013 · T014 · T055 · T057 |
| **FR-003** | 首个异常原样传播 + 确定性 + 取消语义 + 附注 | T011 · T012 · T027 · T028 · T029 · T030 · T034 · T035 · T036 · **T083** |
| **FR-004** | 收集全部 `GraphInterrupt` 并合并抛出（元组） | T038 · T039 · T040 · T041 · T042 · T044 · T045 · T046 · T047 |
| **FR-005** | 异常时停止后续 super-step | T032 · T037 |
| **FR-006** | 并发不改变合并语义 | T006 · **T007** · T015 · T048 · T049 · T050 · T069 · T070 |
| **FR-007** | 依赖隔离 · 零出站 · 零环境变量 | T002 · T075 |
| **FR-008** | 不引入 async | T010 · T075 |
| **FR-009** | 合并 / 报告顺序 = **节点名序** | T013 · T014 · T015 · T016 · T020 · T042 · T050 · T053 · T056 · T057 · T070 |
| **FR-010** | 原子性（含调度状态不落回） | T013 · T021 · T031 · T033 · T037 |
| **FR-011** | 节点入参口径照写 | T014 · T054 |
| **FR-012** | `Command` 的并发语义 | T051 · T052 · T053 |
| **FR-013** | 中断的载体与落点（元组 · 抛出 · 四字段零改动） | T016 · T038 · T039 · T040 · T042 · T043 · T045 · T047 · T070 · T071 · T072 |
| **FR-014** | 异常优先于中断 | T037 · T044 · T047 |
| **FR-015** | 层纪律（ARCH-1） | T072 |
| **FR-016** | 导出面与可观测面零改动 | T008 · T072 · **T082** |
| **FR-017** | 并发旋钮 + 缺省上限 + 入口即校验 | T009 · T012 · T016 · T022 · T023 · T024 · T025 · T070 |
| **FR-018** | 线程生命周期（零悬挂线程） | T010 · T021 · T026 |
| **FR-019** | 上游行号纪律 | T001 · T003 · T076 |
| **FR-020** | 人工验证记录 | T004 · T005 · T077 · T078 · **T083** |
| **FR-021** | 偏离登记 + 发起者追认 | T003 · T080 · T081 |
| **FR-022** | 纯单元可测 · 覆盖率 | T073 · T077 |
| **FR-023** | 署名头与文档纪律 | T008 · T074 · **T082** |
| **FR-024** | 不越界 | T049 · T075 · T079 · **T083** |
| **FR-025** | 零新增门禁编号 | T068 · T071 · T072 |
| **FR-026** | 差分探针场景组 | **T017** · T058 · T059 · T060 · T061 · T062 · T063 · T064 · T065 · T066 · T067 · T068 |

### SC → 任务

| SC | 主题 | 承载任务 |
|---|---|---|
| **SC-001** | 并行节点不串行化（**A1**） | T018 · T019 |
| **SC-002** | 首个异常正确抛出（**A2**） | T027 · T028 |
| **SC-003** | 后续 super-step 不执行（**A3**） | T032 |
| **SC-004** | 并发 == 串行（同一规格） | T048 |
| **SC-005** | 确定性 · 可复现 | T049 · T050 |
| **SC-006** | 写入收集语义 | T055 |
| **SC-007** | 原子性 | T031 |
| **SC-008** | 调度状态不落回（无幽灵触发） | T033 |
| **SC-009** | 多个中断合并抛出（元组 · 顺序确定） | T038 · T040 |
| **SC-010** | 中断元素的 `.value` / `.id` | T039 |
| **SC-011** | 中断与写入的关系（中断轮合并 / 出错轮不合并） | T041 |
| **SC-012** | 中断后暂停 | T045 |
| **SC-013** | 异常优先于中断 | T044 |
| **SC-014** | 其余并发失败不被静默吞掉（附注三样） | T029 |
| **SC-015** | `goto` 不互相吞并 | T051 |
| **SC-016** | 多节点 × 多命令的归并顺序 | T053 |
| **SC-017** | 节点入参口径 | T054 |
| **SC-018** | 依赖隔离 · 零出站 | T002 · T075 |
| **SC-019** | 结构纪律（导出面 / 四字段 / 层 / 门禁编号） | T072 · **T082** |
| **SC-020** | 可测性 · 覆盖率 | T073 |
| **SC-021** | 人工验证记录 | T004 · T078 · **T083** |
| **SC-022** | 偏离登记 + 发起者追认 | T080 |
| **SC-023** | 不越界 | T075 · T079 · **T083** |
| **SC-024** | 文档纪律（署名头 / 上游引用 / 冻结面文案） | T001 · T074 · T076 · **T082** |
| **SC-025** | 零悬挂线程 | T021 |
| **SC-026** | 确定性 · 调度状态不串扰 | T021 · T049 |
| **SC-027** | 并发度缺省与上限（`min(32, cpu+4)`） | T009 · T022 · T023 |
| **SC-028** | 取消语义（排队未启动者被取消 · 运行中者被等待） | T011 · T030 · T035 |
| **SC-029** | 差分探针场景组全绿（**A4**） | T058 · T059 · T060 · T061 · T062 · T063 · T064 · T065 · T066 · T067 · T068 |

### 任务 → FR（反向覆盖 · 每条任务至少挂一条 FR）

| 任务区间 | 主题 | 挂载 FR |
|---|---|---|
| T001–T003 | 上游取证 · 依赖面 · 判定归属核对 | FR-019 · FR-007 · FR-021 |
| T004–T006 · **T007** | 人工验证 / 验收 / 基线清单骨架 · **C-01 探测重跑** | FR-020 · FR-006 |
| T008–T011 | 并发执行器骨架（结果槽 · 并发度 · 线程池 · 取消） | FR-001 · FR-016 · FR-018 · FR-003 · FR-023 |
| T012 | 入口的 `max_concurrency` + 入口即校验 | FR-017 · FR-003 |
| T013–T016 · **T017** | 阶段 ③/③′/④/⑥ 改造 · 节点名序 · 回溯清单 · **差分探针框架扩展** | FR-001 · FR-002 · FR-003 · FR-004 · FR-006 · FR-009 · FR-010 · FR-011 · FR-013 · FR-017 · FR-026 |
| T018–T026 | **US1** 并发执行 | FR-001 · FR-017 · FR-018 |
| T027–T037 | **US2** 错误传播 | FR-003 · FR-005 · FR-010 |
| T038–T047 | **US3** 中断合并 | FR-004 · FR-013 · FR-014 |
| T048–T057 | **US4** 语义一致性 | FR-002 · FR-006 · FR-009 · FR-012 |
| T058–T068 | **US5** 差分探针 | FR-026 · FR-025 |
| T069 | **7 处**顺序敏感断言的拆分（⚠️ **T007** 实跑据实：初版 **10** 处 ⇒ **7** 处 / **5** 个文件） | FR-006 |
| T070 | 回溯修订 T-1…T-11（不含 T-6 / T-9）落笔 | FR-006 · FR-009 · FR-013 · FR-017 |
| T071 | 下游承接 **D-1…D-7** **核对 + 补缺口**（含 **D-7 → B15F1** 的接线追加） | FR-013 · FR-025 |
| T072–T076 | 结构纪律 · 覆盖率 · 署名头 · 不越界 · 引用纪律 | FR-007 · FR-008 · FR-015 · FR-016 · FR-019 · FR-022 · FR-023 · FR-024 · FR-025 |
| T077–T079 | 验收脚本 · 五段式填写 · 遗留登记 | FR-020 · FR-022 · FR-024 |
| T080 | **【阻断合入】** 发起者追认 | FR-021 |
| T081 | **【阻断合入】** 追溯表双向齐全 | FR-021 |
| **T082** | **【阻断合入】** L1 冻结面文档与门禁 docstring 的「18 个」失准文案订正 | FR-016 · FR-023 |
| **T083** | 验收契约 **A7** 用例的判据差距核对 + 差距登记（**只核对 · 不改逻辑**） | FR-001 · FR-003 · FR-020 · FR-024 |

---

## Notes（续）

- ⚠️ **本 feature 的**四条**「比上游更严」（**X-1 / X-2 / X-3 / X-7**）MUST 在人工验证记录里**各有一段**
  **追认文字**：**X-1**（首个异常的确定性 · T028）· **X-2**（其余失败的附注 · T029）·
  **X-3**（整轮原子含「节点抛真异常」· T031）· **X-7**（中断元组顺序 · T040）
  ⇒ ⇒ 四条**打包**进 **T080** 的**一次**追认（宪法「追认次数每 feature MUST ≤ 1 次」）
  ⇒ ⇒ ⚠️ **R-10**（上游对齐批次 P3 对 L1 的改动 · **发起者已批准**）**不在**追认范围内
  （**不重复追认**）⇒ ⇒ 追认范围仍为 **PR-1…PR-11**。
- ⚠️ **T070 与 T071** 是**跨 feature** 的**文档**改动 ⇒ **只接线 · 逐条最小改动** ⇒
  **MUST NOT** 改动下游 feature 提示词初稿的**其余**内容。
