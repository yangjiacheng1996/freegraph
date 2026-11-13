---

description: "Task list for B10F1 · `interrupt()` + `resume`（HITL 中断与恢复闭环）"
---

# Tasks: B10F1 · `interrupt()` + `resume`（HITL 中断与恢复闭环）

**Input**: Design documents from `/specs/b10f1-interrupt-resume/`

**Prerequisites**: [`plan.md`](./plan.md) · [`spec.md`](./spec.md)（**唯一权威**）· [`research.md`](./research.md) ·
[`data-model.md`](./data-model.md) · [`contracts/interrupt-resume-contract.md`](./contracts/interrupt-resume-contract.md) ·
[`contracts/checkpoint-contract.md`](./contracts/checkpoint-contract.md) ·
[`contracts/upstream-parity.md`](./contracts/upstream-parity.md) · [`quickstart.md`](./quickstart.md)

**Tests**: **含**测试任务 —— 提示词的规模预算逐字写明「**测试 640** 行」⇒ ⇒ 本 feature 的
**测试是交付物**（不是可选）⇒ ⇒ 每个用户故事 phase **MUST 先写测试并确认其失败**。
⚠️ **测试行数 640 → 680**（**PR-6** · 范围变更 +40 行）⇒ ⇒ ⚠️ **再 680 → 740**（**PR-7** · 范围变更 +60 行 · 补 **3** 条**测试级**覆盖缺口）⇒ ⇒ ✅ **发起者已确认**（**2026-11-13 分析轮** · 并入 V-1 的那一次追认）⇒ ⇒ ⇒ **实施口径 = 1,260 行** ⇒ ⇒ 见 §行数预算。

**Organization**: 任务按用户故事组织 ⇒ 每个故事**可独立实现、独立测试**。

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件 · 无未完成依赖）
- **[Story]**: 所属用户故事（US1…US4 · 对应 spec 的 P1…P4）
- 每条任务 MUST 带**确切文件路径**

## Path Conventions

- **单包结构**：`src/` · `tests/` 在仓库根
- L1 = `src/freegraph/contracts/` · L2 = `src/freegraph/runtime/` · 门面 = `src/freegraph/graph.py`
- 差分探针 = `tests/differential/parity_probe.py`

---

## Phase 1: Setup (共享基础设施)

**Purpose**: 本 feature 的**脚手架**与**绿基线**取证（仓库已存在 ⇒ 无「初始化项目」步骤）

- [X] T001 建 `harness/verification/B10F1/manual-verification.md` 的**五段式骨架**（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）+ 在「验证环境」里记下**绿基线**：**pytest 计数**与**差分场景数（既有 43 条 · 实测 `parity_probe._scenarios()`）**（**实测** · 禁编造）⇒ ⇒ **本任务只建骨架 + 记基线**；「实际输出 / 结论 / 遗留问题」的填充归 **T047**（不重复）
- [X] T002 [P] 新建 `src/freegraph/runtime/_interrupt.py`（**私有**模块 · 前导下划线 ⇒ 不进 `runtime.__all__` ⇒ 不进 API 兼容矩阵 · ⚠️ **L2 目录条目内** ⇒ 与 `superstep.py` **同一注册表条目** ⇒ 互相 import **合法** · 门禁 **G25**）：带**署名头**（版权 + MIT + 项目地址 · 门禁 **G30**）· `docstring` 为**首个语句**（门禁 **G5**）· 模块 docstring 写明「**两级 `ContextVar`**（运行级 / 任务级）· **`interrupt()` 的实现体** · `.id` 的生成」
- [X] T003 [P] 新建 5 个测试文件骨架（**各带署名头** · `docstring` 首个语句）：`tests/runtime/test_interrupt_basic.py` · `tests/runtime/test_interrupt_resume.py` · `tests/runtime/test_interrupt_errors.py` · `tests/runtime/test_interrupt_checkpoint.py` · `tests/runtime/test_interrupt_contract.py`
- [X] T004 [P] 新建 `harness/verification/B10F1/acceptance.py`（**一键验收入口** · 逐条闸口 ⇒ 退出码 == 0 为全绿）

---

## Phase 2: Foundational (阻塞性前置)

**Purpose**: **全部四个故事都依赖**的地基（异常族 · 结果载体 · 运行期上下文 · 图级入口 · 导出面）⇒
**本 Phase MUST 全绿**，否则任何故事都开不了工。

- [X] T005 [P] 在 `src/freegraph/runtime/errors.py` 新增 `InterruptError`：继承 `FreegraphError` 且**不**继承 `ValueError` · `.reason` 为**封闭 5 码**（`checkpointer_required` / `resume_value_required` / `ambiguous_resume` / `no_pending_interrupt` / `not_in_run`）· **不**携带任何**上下文**字段（会话标识 / 中断 id 列表）· 缺省消息为**英文**摘要且**点名**失败原因 · ⚠️ **MUST** 把 `InterruptError` 写进 `runtime/errors.py` 的 `__all__`（**7 → 8**）⇒ ⇒ 与 T012-a 第 ④ 处的**期望集合**（7 + `InterruptError`）**逐字对齐**（**否则该断言不可判定**）
- [X] T006 [P] 在 `src/freegraph/runtime/superstep.py` 新增 `InterruptResult`（`@dataclass(frozen=True, slots=True)` · **4 字段** `state` / `interrupts` / `executed` / `steps`）+ 方法 `as_result_dict() -> dict[str, Any]`（= `{**state, "__interrupt__": interrupts}`）⇒ **MUST NOT** 有第 5 个字段（**不**带 `node_writes`）
- [X] T007 在 `src/freegraph/runtime/superstep.py` 给 `SchedulerState` **增两个方法** `to_checkpoint() -> dict[str, Any]` 与 `from_checkpoint(data) -> SchedulerState`（**只增方法 · MUST NOT 改任何字段** ⇒ `SchedulerState()` 的**构造签名逐字不变**）⇒ 编码：`versions_seen` ⇒ `{节点名: [[kind, ident, 版本], ...]}` · 其余三者**原样** · `step` / `channels` **不落盘**
- [X] T008 在 `src/freegraph/runtime/_interrupt.py` 实现**两级上下文**：`ContextVar` 运行级（载荷 = `{节点名: 任务现场}`）与任务级（载荷 = `_TaskScratchpad`：`resume: list[Any]` / `index: int` / `existing: Interrupt | None` / `namespace: str | None`）+ 上下文管理器 `bind_task(node_name)`（**用 `reset(token)` 复原** ⇒ 线程池复用线程时**零脏状态**）
- [X] T009 在 `src/freegraph/runtime/superstep.py` 的 `_bind._inner`（节点执行的**唯一**调用点）挂载**任务级**现场：`with bind_task(node_name):` 包住节点调用 ⇒ **一处**改动 ⇒ `superstep.py` 的**其余**部分零改动
- [X] T010 在 `src/freegraph/runtime/superstep.py` 实现 `run_graph(spec, input=None, *, state=None, checkpointer=None, config=None, max_steps=10007, max_concurrency=None) -> SuperStepResult | InterruptResult` 的**首次运行**路径（**复用**既有的 `_run_round` / `_determine_triggers` / `_merge_writes` / `_clear_step_end` / `_sparse_state`）⇒ **MUST NOT** 改 `run_super_step` / `run_super_steps` 的**签名与返回类型** ⇒ ⇒ ⚠️ **「会话连续」的叠加语义（补 · spec FR-013 末两行）**：首次运行（**非** `Command` 输入）且挂了 checkpointer 时 ⇒ ⇒ MUST **先读该快照的 `.scheduler`** 重建调度状态（**续跑** · **上游同款** · **实测 E-26**）⇒ ⇒ 再按输入形态分两支（⚠️ **上游两种形态行为不同** · **实测 E-26**）：**`input = None`** ⇒ **不**写任何通道 ⇒ **只有被中断的节点**重跑 ⇒ `.id` **逐字不变**（**上游同款** · **E-15 / E-26 ①**）· **`input = StateDict`** ⇒ 先读该会话最新快照的 `.snapshot.values`、再把 `input` **按通道写入**叠加上去（**覆盖型 ⇒ 覆盖** · **归约型 ⇒ 追加** · **与 B5F1 的 `Channel.update` 同款** · **上游同款** · `_loop.py:975-985` 的 `map_input`）⇒ ⇒ **写通道 ⇒ 通道版本推进 ⇒ 订阅节点重新触发** ⇒ 被触及的节点**重跑**（**实测 E-26 ②**）⇒ `.id` **可变** ⇒ ⇒ **MUST NOT** 另写一条叠加路径 / 一条「整图重跑」路径 ⇒ ⇒ ⚠️ 与**恢复**路径**刻意不同**（恢复 = **显式**跑 `.snapshot.next` 的节点 · **不走**触发判定）⇒ ⇒ **不**消费 `__resume__` ⇒ ⇒ **不**触发恢复
- [X] T011 更新 `src/freegraph/runtime/__init__.py` 的 `__all__`：新增 **3** 个符号（`InterruptResult` · `InterruptError` · `run_graph`）⇒ **20 → 23** ⇒ **MUST NOT** 新增其它符号 ⇒ ⇒ ⚠️ **附带订正**：该模块 docstring 里「契约层仍 **18** 个符号」⇒ **20**（**实测** `len(freegraph.contracts.__all__) == 20`）⇒ ⇒ **零**行为影响（**仅**文案）⇒ ⇒ ⚠️ **同一处**陈旧文案（**「契约层 18 个符号」**）共 **4 个文件 / 5 个物理位置**（**2026-11-13 分析轮扩容 · 第二轮修订计数口径**）：① 本文件（`runtime/__init__.py` · **1** 处）② `src/freegraph/runtime/errors.py` 的模块 docstring（**两处**：「契约层 **18** 符号面」· 本任务 T005 已改该文件 ⇒ **顺带**订正）③ `README.md:86`（「契约层 18 个符号」· **1** 处）④ `tests/facade/test_facade_gates.py:407`（「18 个符号」· **1** 处）⇒ ⇒ **③④ 归 T054**
- [X] T012-a 改**五处**会红的冻结断言（**回溯修订 T-1 · 前半** · ⚠️ 初版只登记了 **3 处** ⇒ **2026-11-13 分析轮实测**另有 **3 处** ⇒ ⇒ **六处 MUST 同改**（只改一处 ⇒ **pytest 必红**）⇒ ⇒ ⚠️ **本任务只含「T005 / T011 落地后即可判定」的 4 处** ⇒ ⇒ **Phase 2 MUST 全绿**）：
  - **①–③（`runtime.__all__` 的硬编码 20）**：① `tests/runtime/test_command_purity.py:255`（`assert len(runtime.__all__) == 20`）② `tests/runtime/test_superstep_concurrency.py:597`（`assert len(runtime.__all__) == 20`）③ `tests/runtime/test_read_contract.py:80`（`RUNTIME_SYMBOL_COUNT = 20`）+ `:547` + `:550`（`set(runtime.__all__) == {…20 个…}`）⇒ ⇒ 三处**一律**改为「与本 feature 的 `runtime.__all__` 清单**集合相等**」的断言（**不硬编码 23**）⇒ ⇒ ⚠️ **MUST NOT** 放宽为「≥ 20」⇒ ⇒ 另须**同步** `test_command_purity.py` / `test_read_contract.py` 的**函数名与 docstring**里的「twenty symbols」/「== **20**」（避免留下误导性命名）
  - **④（`runtime.errors` 的符号面 · PR-8）**：`tests/runtime/test_read_contract.py:313-338`（`test_i9_the_reading_layer_adds_no_new_error_type`）⇒ ⇒ `errors.__all__` 的**精确 7 元组**改「**集合相等**（**期望集合 = 7 + `InterruptError`** ⇒ 共 **8** 项 · 与 T005 写进 `errors.__all__` 的结果**逐字对齐**）」+ `FreegraphError` 子类**精确清单**改「**集合相等**（**允许** `InterruptError`）」⇒ ⇒ ⚠️ **实测**：**无论** `InterruptError` 是否写进 `errors.__all__` ⇒ **都必红**
  - **⑦（`superstep.__all__` 的「精确列表」 · PR-9 · **实施期实测新增**）**：`tests/runtime/test_superstep_purity.py:122-146`（`test_importing_the_kernel_has_no_side_effects`）⇒ ⇒ 断言 `superstep.__all__` == **一份内联的 6 项精确列表** ⇒ ⇒ **硬编码清单** ⇒ ⇒ 本 feature **增**了 3 个符号 ⇒ ⇒ **必红** ⇒ ⇒ 改为「**与清单集合相等**」（清单 = `tests/runtime/_runtime_export_manifest.py` 的 `SUPERSTEP_EXPORT_SYMBOLS` · **单一事实源** ⇒ ⇒ **不**硬编码数字）⇒ ⇒ **判据零放宽**（仍是「== 某份清单」⇒ **不是**「⊇」）⇒ ⇒ ⚠️ 该断言**同时**守「导入调度内核**无副作用**」（零环境变量 / 零出站）⇒ ⇒ 那两条**保留**
  - ⚠️ **三处断言共用** `tests/runtime/_runtime_export_manifest.py`（**本任务新增**）⇒ ⇒ **不**在三处各抄一份清单 ⇒ ⇒ **不会漂移** ⇒ ⇒ 清单的**权威** = `contracts/interrupt-resume-contract.md` §1（第二段断言 AST 类清单）
- [X] T012-b 改**两处**会红的冻结断言（**回溯修订 T-1 · 后半** · PR-8）⇒ ⚠️ **MUST 紧随 T019 落笔**（这两处的**期望值**只有 T019 的接线落地后才成立 ⇒ ⇒ 提前落笔 ⇒ **必红** ⇒ ⇒ 违反「Phase 2 / US1 **MUST 全绿**」与「MUST **NOT** 写**永久红**的 CI」⇒ ⇒ **MUST NOT** 排到 T019 之前）：
  - **⑤（门面 `interrupt` 的「未接线」测试 · PR-8）**：`tests/facade/test_facade.py:315-330`（`TestInterrupt::test_raises_not_implemented`）⇒ ⇒ 改为「**接线后** `interrupt()` 抛 `InterruptError(reason="not_in_run")` · **不再**抛 `NotImplementedError`」⇒ ⇒ 同步该类的 **docstring / 类名**（去掉「未接线（由 B10F1 交付）」措辞）⇒ ⇒ 判据**更具体**（**零放宽**）
  - **⑥（`_primitives.py` 的「未接线守卫」 · PR-8）**：`tests/runtime/test_superstep_concurrency.py:790-795`（`assert "NotImplementedError" in primitives`）⇒ ⇒ 改为「`_primitives.py` **只留 `Send`**」的**源码文本**断言（`"def interrupt" not in primitives`）⇒ ⇒ 同步该测试的 **docstring / 命名**⇒ ⇒ ⚠️ **实测**：当前**仅靠** `_primitives.py` docstring 里残留的字符串**侥幸通过** ⇒ ⇒ 按 **T019** 删实现体 + 清理 docstring 后**必红**
- [X] T013 扩展 `tests/differential/parity_probe.py`（⚠️ **MUST NOT** 标 `[P]` —— 它**依赖 T010** 的 `run_graph` ⇒ ⇒ 不满足「无未完成依赖」⇒ ⇒ **排在 T010 之后**）：① `Scenario` 增**可选**字段（「第二次输入」/「是否挂 saver」/「是否比较恢复后结果」）② 新增比较口径 **`"interrupt-shape"`**（比 `.value` **逐字** + 比 `.id` 的**形态**（正则 `^[0-9a-f]{32}$`）⇒ **不比**具体值）③ ⚠️ **freegraph 侧 MUST 从 `run_super_steps` 切到本 feature 的新入口 `run_graph`**（`run_super_steps` **无** `input` / `checkpointer` 参数 ⇒ **恢复类场景按旧口径不可实现**）⇒ ⇒ `run_freegraph` 支持传 `checkpointer`（**桩** · 本 feature **不实现** saver · FR-019）+ **两段式跑法**（第一次 ⇒ 挂起；第二次 ⇒ 以 `Command(resume=…)` 恢复 ⇒ 比**恢复后**的结果）+ **同一 config / thread_id** ⇒ ⇒ ④ **上游侧** `compile(checkpointer=InMemorySaver)` + **第二次 `invoke`** ⇒ ⇒ **既有 43 个场景的行为与判词逐字不变**（⚠️ **实测基线 = 43**（`parity_probe._scenarios()`）—— 初版写的「30」是 B7F4 落库前的旧数）⇒ ⇒ ⚠️ **只增能力** ⇒ ⇒ 既有场景**零改动**

**Checkpoint**: 地基就绪 —— 四个用户故事可并行开工（⚠️ **本 Phase MUST 全绿** ⇒ ⇒ **T012-b 的 ⑤⑥ 两处不在本 Phase 落笔** —— 它们的**期望值**依赖 T019 的接线 ⇒ ⇒ 本 Phase 的「全绿」判据 = **T012-a 的 4 处** + T005–T013 的其余项 ⇒ ⇒ **T012-b 归 US1**）

---

## Phase 3: User Story 1 - 节点挂起并把「要审批什么」交还调用方（Priority: P1）🎯 MVP

**Goal**: 节点调用 `interrupt("approve?")` ⇒ 图**挂起** ⇒ 结果含 `__interrupt__`（元素带 `.value` 与 `.id`）

**Independent Test**: 执行一张只有一个审批节点的图 ⇒ 断言结果含 `__interrupt__` 键 · 元素 `.value == "approve?"` · `.id` 为 32 位十六进制 ⇒ **不依赖** checkpointer · **不依赖**恢复

### Tests for User Story 1（MUST 先写 · MUST 先失败）

- [X] T014 [P] [US1] 在 `tests/runtime/test_interrupt_basic.py` 写用例：节点调 `interrupt("approve?")` ⇒ 断言结果含 `__interrupt__` 键 · `result["__interrupt__"][0].value == "approve?"` · `.id` 匹配 `^[0-9a-f]{32}$`（SC-001 / A3）
- [X] T015 [P] [US1] 在 `tests/runtime/test_interrupt_basic.py` 写用例：中断**前**的状态写入**不丢失**（挂起不是回滚）· 同轮**其它**节点的写入**照常合并**（SC-004）
- [X] T016 [P] [US1] 在 `tests/runtime/test_interrupt_basic.py` 写用例：同一 super-step 内**两个**节点同时中断 ⇒ `__interrupt__` 的**两个**元素都在且 `.value` 逐个对得上（SC-009）
- [X] T017 [P] [US1] 在 `tests/runtime/test_interrupt_basic.py` 写用例：挂起时返回类型 == `InterruptResult`（**不是** `SuperStepResult`）· `steps` **如实计**（含被中断的那轮 · 不含空轮）· `__interrupt__` **不进** `state`（SC-010） ⇒ ⇒ ⚠️ **补**（data-model **V-4** · **2026-11-13 分析轮回修**）：`InterruptResult.executed` 与 `SuperStepResult.executed` **同排序口径**（**节点名序** · 升序 · 含被中断的节点）⇒ ⇒ ⚠️ **判据形态**：中断轮**不**产出 `SuperStepResult`（FR-005 / 裁定 2）⇒ ⇒ **无对照物** ⇒ ⇒ **不**断言「两个对象逐字相等」⇒ ⇒ **改为** ① 断言 `InterruptResult.executed` **逐字等于期望的节点名序**（如 `("a", "b")` · 升序）② 断言它**是升序的**（⇒ ⇒ 与 `SuperStepResult.executed` 的排序口径**一致**）⇒ ⇒ ⚠️ **补**（data-model **V-5** · **2026-11-13 分析轮拍板 · 第二轮修订**）：`InterruptResult.steps`（**不含**空轮）与 `SuperStepResult.steps`（**含**空轮 · B7F1 冻结面）**计数口径刻意不同** ⇒ ⇒ ⚠️ **MUST NOT** 把两者做**算术比较**（**不**断言「挂起 N 轮 ⇒ 跑完 N+1 轮」—— 那依赖两套口径的巧合差值）⇒ ⇒ 改为**分别**断言：① 挂起结果的 `steps` == **实际跑过的轮数**（**含**被中断的那轮 · **不含**空轮）② 跑完结果的 `steps` == **含**空轮口径 ⇒ ⇒ **两者数值不可直接比较**（MUST NOT 把差值解读为「少跑了一轮」）

- [X] T056 [P] [US1] 在 `tests/runtime/test_interrupt_basic.py` 写用例：同一 super-step 内**一个**节点抛真异常、**另一个**节点调 `interrupt()` ⇒ ⇒ 断言抛出的是**那个真异常**（类型 + 消息原样）⇒ ⇒ **结果里读不到**那批中断元组（`__interrupt__` **不存在**）⇒ ⇒ **SC-008**（裁定 11 · 上游同款 `langgraph/pregel/_runner.py:687` 先于 `:690`）⇒ ⇒ ⚠️ **本任务补的是「测试级覆盖缺口」**（初版只有 T020 的**实现** ⇒ 判据不可测）⇒ ⇒ 落 **PR-7**

### Implementation for User Story 1

- [X] T018 [US1] 在 `src/freegraph/runtime/_interrupt.py` 实现 `interrupt(value)` 的**抛出**分支：无可用恢复值时抛 `GraphInterrupt((Interrupt(value=value, id=…),))`（**1-元组** · **上游同款**）· `.id` = `hashlib.blake2b(f"{节点名}:{uuid4().hex}".encode(), digest_size=16).hexdigest()`（**32 位十六进制** · 命名空间**含随机 uuid4** ⇒ **不可猜**）
- [X] T019 [US1] **按 PR-4 的唯一合法形态接线**（⚠️ **两个旧口径都会被门禁 G25 判红** —— **实测**）：① 在 `src/freegraph/_primitives.py` **删掉 `interrupt` 的实现体**（该文件**只留 `Send`）⇒ ⇒ **MUST NOT** import `runtime/`（**跨注册表条目的同层 import** ⇒ G25 判红）；② 在 `src/freegraph/graph.py` 把 `interrupt` 的来源改为**模块级** `from .runtime._interrupt import interrupt`（`facade-L1-L3` 例外 ⇒ 门面 → L2 合法）⇒ ⇒ 门面 **7 个导出名一字不改**（G14 零实现体 / G15 / G16 / G19 恒绿）⇒ ⇒ 门面的**模块加载面**只多出 L2（**不**含 L4 / L5 ⇒ 门禁 **G18** 恒绿）⇒ ⇒ ⚠️ **本任务落地后 MUST **立即**跑** `harness/scripts/gates/gate_G25_import_graph.py --root .`（退出码 == 0）⇒ ⇒ **MUST NOT** 等到 Phase 7 才验（**PR-4** 的落点一旦不合规 ⇒ 后续任务全白做）⇒ ⇒ ⚠️ **同时**须清理 `_primitives.py` 的**陈旧 docstring**（它仍写「本模块承载两个**原语**的外壳」+「当前**无条件抛** `NotImplementedError`」）⇒ ⇒ ⚠️ 该清理会**触发**既有冻结断言 `test_superstep_concurrency.py:795` 变红 ⇒ ⇒ ⇒ **由 T012 第 ⑥ 处一并回溯修订** ⇒ ⇒ ⚠️ **同样**须订正 `src/freegraph/graph.py` 的**模块 docstring**（它仍写「**本 feature 零行为**：`StateGraph` 的四个方法与 `interrupt` 一律抛内置 `NotImplementedError`」）⇒ ⇒ ⚠️ 门禁 **G14** 只查 AST 的 `class` / `def`（**不**查 docstring）⇒ ⇒ **不会**被门禁拦 ⇒ ⇒ ⇒ MUST **手工**同步 ⇒ ⇒ ⇒ ⚠️ **T019 落地后 MUST 立即执行 T012-b**（⑤ 门面「未接线」测试 + ⑥ `_primitives.py`「未接线守卫」）⇒ ⇒ 否则这两处**必红** ⇒ ⇒ 违反「US1 **MUST 全绿**」与「MUST **NOT** 写**永久红**的 CI」
- [X] T020 [US1] 在 `src/freegraph/runtime/superstep.py` 的 `run_graph` 里**接住** B12F1 合并抛出的 `GraphInterrupt` ⇒ 读 `exc.args[0]`（**元组**）⇒ 产出 `InterruptResult` ⇒ ⇒ **MUST NOT** 另写一条中断收集路径 ⇒ ⇒ **真异常优先**（真异常抛出时中断元组**丢弃**）
- [X] T021 [US1] 在 `tests/runtime/test_interrupt_contract.py` 写核验用例：`SuperStepResult` 的**字段数 == 4**（**不**新增第 5 个）· `InterruptResult` 的**字段数 == 4** · `__interrupt__` **不进** `state`（契约 §5.1 · data-model **V-1 / V-2**）

**Checkpoint**: US1 独立可跑 —— 中断 → `__interrupt__` → 交还调用方

---

## Phase 4: User Story 2 - 提交审批结果后图继续跑完（Priority: P2）

**Goal**: `Command(resume="yes")` ⇒ 图**跑到结束**且状态含 resume 值 · 未挂 checkpointer / 未提供恢复值 ⇒ **明确异常**

**Independent Test**: 挂**桩** checkpointer ⇒ 首次执行挂起 ⇒ 第二次以 `Command(resume="yes")` 执行 ⇒ 断言结果**无** `__interrupt__` 且状态含 resume 值

### Tests for User Story 2（MUST 先写 · MUST 先失败）

- [X] T022 [P] [US2] 在 `tests/runtime/test_interrupt_resume.py` 写用例：挂桩 ⇒ 中断 ⇒ `Command(resume="yes")` ⇒ 断言结果**无** `__interrupt__` 键且状态含 `"yes"`（SC-002 / A1）
- [X] T023 [P] [US2] 在 `tests/runtime/test_interrupt_errors.py` 写用例：`Command(resume="yes")` 且**未挂** checkpointer ⇒ 抛 `InterruptError` 且 `.reason == "checkpointer_required"` 且消息指明「恢复需要 checkpointer」（SC-011 / A4② · ⚠️ **上游同款** · **实测 E-25b**：上游的 checkpointer 检查**在 `if resume is not None` 之内** ⇒ **必须**给出一个**非 `None`** 的 `resume` 才触达该检查 ⇒ ⇒ **MUST NOT** 用 `Command(resume=None)` 来触发本用例） ⇒ ⇒ ⚠️ **消息断言（补 · contract §7）**：消息 MUST 为**英文**摘要且**点名**失败原因（要点与上游逐字同款：`Cannot resume without a checkpointer`）
- [X] T024 [P] [US2] 在 `tests/runtime/test_interrupt_errors.py` 写用例：`Command(resume=None)` 与 `Command()` ⇒ 均抛 `InterruptError(reason="resume_value_required")`（SC-012）⇒ ⇒ ⚠️ **交叠情形**也要断言：`Command(resume=None)` 且**未挂** checkpointer ⇒ **仍是** `resume_value_required`（**未提供恢复值优先** · **上游同款** · **实测 E-25a** ⇒ ⇒ **MUST NOT** 写成 `checkpointer_required`） ⇒ ⇒ ⚠️ **消息断言（补 · contract §7）**：消息 MUST 为**英文**摘要且**点名**失败原因（`resume value is required`）
- [X] T025 [P] [US2] 在 `tests/runtime/test_interrupt_errors.py` 写用例：该会话**没有**挂起中断时提交恢复 ⇒ 抛 `InterruptError(reason="no_pending_interrupt")`（FR-014） ⇒ ⇒ ⚠️ **消息断言（补 · contract §7）**：消息 MUST 为**英文**摘要且**点名**失败原因（`No pending interrupt to resume`）
- [X] T026 [P] [US2] 在 `tests/runtime/test_interrupt_errors.py` 写用例：在**图运行之外**调用 `interrupt()` ⇒ 抛 `InterruptError(reason="not_in_run")`（FR-025） ⇒ ⇒ ⚠️ **消息断言（补 · contract §7）**：消息 MUST 为**英文**摘要且**点名**失败原因（`interrupt() called outside of a graph run`）
- [X] T052 [P] [US2] 在 `tests/runtime/test_interrupt_resume.py` 写**三组**补漏用例（⚠️ **初版遗漏** ⇒ ⇒ 见 spec **FR-013** 判定表）：① **按 id 的映射恢复成功**（跨节点两个挂起中断 ⇒ 用 `{id: 值}` 恢复 ⇒ 指定的**已恢复**、未指定的**仍挂起**）—— **SC-015 的另一半**（初版只覆盖了「单值 ⇒ 失败」那一半 ⇒ ⇒ **两端都要有独立断言**）⇒ ⇒ ⚠️ **map 的「值」原样投递**（**标量即可** · **上游同款** · `_algo.py:1313-1314`）⇒ ⇒ 节点拿到的就是该**标量**本身 ⇒ ⇒ ⚠️ **兼容断言**：同一用例另以 `{id: [值]}`（列表形态）再跑一次 ⇒ ⇒ 节点拿到的**就是那个列表**（上游同款：上游把值**原样** append）⇒ ⇒ **两种形态都合法**（**不**强制列表）② **dict 非 map + 仅一个挂起中断** ⇒ 该 dict 被当作**普通恢复值**（**不是** map）⇒ **FR-013** ⑦ ③ `Command(resume=…)` 与 `Command(update=…)` **并存** ⇒ 两者**各走各的通道**（`update` 落在通道上 · `resume` 被节点拿到）—— **补记 F-2**（初版**只有实现**、**无测试**）

- [X] T057 [P] [US2] 在 `tests/runtime/test_interrupt_resume.py` 写用例：**会话连续**（FR-013 末两行 · 补记 **F-4** · 上游同款 `langgraph/pregel/_loop.py:975-985` · **实测 E-26**）：先跑一次**挂起**的会话⇒ ⇒ 随后以**普通状态字典**（**非** `Command`）对**同一 `thread_id`** 再调用 ⇒ ⇒ 断言① **先读**该会话最新快照的 `.snapshot.values`、**再**把 `input` **叠加**上去（既有状态**不丢**）⇒ ⇒ ② **不**消费 `__resume__` ⇒ ⇒ ③ **不**触发恢复（**不**抛 `InterruptError`）⇒ ⇒ ④ ⚠️ **续跑**（**2026-11-13 分析轮拍板**）：MUST 读 `.scheduler` 重建调度状态 ⇒ ⇒ 断言**写通道 ⇒ 通道版本推进 ⇒ 订阅节点重新触发**（被触及的节点**重跑** · **上游同款** · **实测 E-26 ②**）⇒ ⇒ ⑤ ⚠️ **另一支**：`input = None` 对**同一 `thread_id`** 再调用 ⇒ ⇒ 断言**只有被中断的节点**重跑（其它节点**不**重跑）⇒ ⇒ 且 `.id` 与先前交给调用方的那个**逐字相同**（**上游同款** · **实测 E-15 / E-26 ①** · 补记 **F-1**）⇒ ⇒ ⚠️ **本任务补的是「测试级覆盖缺口」**（PR-6 只补了**实现**面 ⇒ 判据不可测）⇒ ⇒ 落 **PR-7**

### Implementation for User Story 2

- [X] T027 [US2] 在 `src/freegraph/runtime/superstep.py` 实现 `run_graph` 的**恢复输入判定**（⚠️ **唯一事实源 = spec 的 FR-013 的表** —— **逐字照抄** · **MUST NOT** 在实现里另抄一份 ⇒ ⇒ 判定**顺序**照 **裁定 4** 的「判定顺序」行 ⇒ ⇒ ⚠️ **MUST NOT** 在实现里**另抄一份**判定表 / 判定顺序（**2026-11-13 分析轮回修 · 消除第三处漂移**）⇒ ⇒ **引用时 MUST 写全**：「按 **FR-013** 的表 · 依 **裁定 4** 的顺序」）⇒ ⇒ ⚠️ **② 先于 ③**（**上游同款** · 实测 E-25a/E-25b）⇒ ⇒ **MUST NOT** 静默降级为内存态恢复 ⇒ ⇒ ⚠️ **⑥ 的 map「值」原样投递**（**标量即可** · **上游同款** · `langgraph/pregel/_algo.py:1313-1314`）⇒ ⇒ 该值 = 该节点**下一个** `interrupt()` 的恢复值 ⇒ ⇒ 同一节点的**第 2 个** `interrupt()` ⇒ **再次挂起**（裁定 7 · **上游同款**）⇒ ⇒ ⚠️ **空 dict**（`{}`）归 ⑥（**真空为真**）⇒ 恢复**零个** ⇒ 全部**仍挂起**（**不**报错）⇒ ⇒ ⚠️ **① 的「会话连续」**：挂了 checkpointer 时 MUST **先读该会话最新快照的 `.scheduler`** 重建调度状态（**续跑** · **上游同款** · **实测 E-26**）⇒ ⇒ 再按输入形态分两支（**上游两种形态行为不同**）：**`input = None`** ⇒ **不**写通道 ⇒ **只有被中断的节点**重跑 ⇒ `.id` **不变**；**`input = StateDict`** ⇒ 先读 `.snapshot.values`、再把 `input` **叠加**上去 ⇒ ⇒ ⚠️ **「叠加」的确切语义（补 · spec FR-013 末两行）** = **按通道写入**（**覆盖型通道 ⇒ 覆盖** · **归约型通道 ⇒ 追加**）⇒ ⇒ **与 B5F1 的 `Channel.update` 同款**（**上游同款** · `langgraph/pregel/_loop.py:975-985`）⇒ ⇒ **MUST NOT** 另写一条叠加路径 ⇒ ⇒ **不**消费 `__resume__` ⇒ ⇒ **不**触发恢复
- [X] T028 [US2] 在 `src/freegraph/runtime/superstep.py` 实现恢复的**读侧**：`checkpointer.get_tuple(config)` ⇒ 取 `.snapshot` / `.pending_writes` / `.scheduler` ⇒ ⇒ 查不到该会话 ⇒ 视为「无挂起中断」（⇒ 走 T025 的 `no_pending_interrupt`）⇒ ⇒ **MUST NOT** 把它当作「空状态从头跑」
- [X] T029 [US2] 在 `src/freegraph/runtime/superstep.py` 实现恢复的**重建**：通道实例 = `Channel.from_checkpoint(...)`（**现成** · 零新增）· 调度账本 = `SchedulerState.from_checkpoint(...)` ⇒ ⇒ 待跑节点 = `.snapshot.next` ⇒ ⇒ **显式**跑这些节点（**不走**触发判定）⇒ ⇒ 恢复后的**后续轮**触发判定与首次运行**同款**
- [X] T030 [US2] 在 `src/freegraph/runtime/_interrupt.py` 实现 `interrupt(value)` 的**返回**分支：任务现场有 `resume[index]` ⇒ **返回**它（**不**抛中断）⇒ ⇒ 节点的 `answer = interrupt("approve?")` 在恢复执行时拿到 resume 值
- [X] T031 [US2] 在 `src/freegraph/runtime/superstep.py` 实现恢复轮之后**继续**多轮循环（复用既有的 `_determine_triggers` / `_run_round`）⇒ ⇒ 跑完返回 `SuperStepResult`（**四字段**）

**Checkpoint**: US1 与 US2 **各自**独立可跑 —— 闭环成立

---

## Phase 5: User Story 3 - 恢复时节点从头重跑（Priority: P3）

**Goal**: 恢复时节点函数**整个重新执行**（**不**保存局部变量 · **不**从中断点继续）· 同节点多 `interrupt()` 按**节点内顺序**匹配

**Independent Test**: 节点内放自增计数器与副作用 ⇒ 首次执行被中断 ⇒ 恢复执行 ⇒ 断言副作用序列 == `['enter', 'enter', 'got yes']`

### Tests for User Story 3（MUST 先写 · MUST 先失败）

- [X] T032 [P] [US3] 在 `tests/runtime/test_interrupt_resume.py` 写用例：节点 `interrupt()` **之前**的副作用在恢复时**再次出现** ⇒ 断言副作用序列 == `['enter', 'enter', 'got yes']` ⇒ 证明**从节点起点重跑**（SC-003 / A2）
- [X] T033 [P] [US3] 在 `tests/runtime/test_interrupt_resume.py` 写用例：同一节点内**两个** `interrupt()` ⇒ 第 1 个恢复值落在第 1 个、第 2 个落在第 2 个（SC-014）
- [X] T034 [P] [US3] 在 `tests/runtime/test_interrupt_resume.py` 写用例：恢复值**不足** ⇒ 节点在下一个 `interrupt()` 处**再次挂起**（**不**报错）⇒ 且第二次挂起的 `.id` 与第一次**逐字相同**（SC-013 · 补记 **F-1**）

### Implementation for User Story 3

- [X] T035 [US3] 在 `src/freegraph/runtime/_interrupt.py` 实现任务现场的 `index` **原子计数**（每个节点各自计数 · **不**跨节点）⇒ ⇒ 第 2 次调用 `interrupt()` 取 `resume[1]`
- [X] T036 [US3] 在 `src/freegraph/runtime/superstep.py` 实现恢复时把 pending writes 里那个**先前的中断载荷**注入任务的 `existing` ⇒ ⇒ 再次挂起时**复用** `existing.id` ⇒ ⇒ **`.id` 跨恢复稳定**（**结构性保证** · **零新增持久化字段**）
- [X] T037 [US3] 在 `src/freegraph/runtime/superstep.py` 实现 `Command(update=…)` 与 `resume` **并存**时的处理：`update` 走**通道写入**路径 · `resume` 走**恢复通道** ⇒ ⇒ 两者**互不排斥**（**照抄上游** `map_command` · 补记 **F-2**）

**Checkpoint**: US1…US3 各自独立可跑 —— 「从节点起点重跑」的语义**可判定**

---

## Phase 6: User Story 4 - 恢复路径确实经由 checkpointer（Priority: P4）

**Goal**: 恢复**确实**从 checkpointer 读回**快照 + 待写入 + 调度账本** ⇒ ⇒ 不是内存态旁路

**Independent Test**: 用**记录调用的桩** checkpointer ⇒ 断言恢复时它被调用且读到了**该 `thread_id`** 的三项载荷

### Tests for User Story 4（MUST 先写 · MUST 先失败）

- [X] T038 [P] [US4] 在 `tests/runtime/test_interrupt_checkpoint.py` 写**桩** checkpointer（记录 `get_tuple` / `put` / `put_writes` 的调用与参数）+ 用例：恢复时桩记录到 `get_tuple` 调用且返回的 `.snapshot` / `.pending_writes` / `.scheduler` **三项均被读取**（SC-005 / A4①）
- [X] T039 [P] [US4] 在 `tests/runtime/test_interrupt_checkpoint.py` 写用例：`.scheduler` 的 **JSON 往返**（`json.dumps` → `json.loads`）⇒ 还原后的 `SchedulerState` 与原对象**逐字段相等**（data-model **V-12**）
- [X] T040 [P] [US4] 在 `tests/runtime/test_interrupt_checkpoint.py` 写用例：挂起时桩记录到**快照写入**（`put`）与**待写入写入**（`put_writes` · 通道名 `__interrupt__`）⇒ ⇒ 挂起态**可被再次恢复**（闭环**可重复** · FR-012）
- [X] T053 [P] [US4] 在 `tests/runtime/test_interrupt_checkpoint.py` 写用例：**跨运行不得持有「待恢复现场」**（**FR-010 的核心禁令** ⇒ 初版**无直接断言**）：先跑一次挂起（`run_graph` 返回 `InterruptResult`）⇒ ⇒ 再跑**第二次** `run_graph`（**新会话 / 新 `thread_id`**）⇒ ⇒ 断言第二次运行**读不到**第一次的中断现场（**不**消费上一次的 `__resume__`）⇒ ⇒ 且**内核内**不残留上一轮的任务现场（**不**跨运行持有）

### Implementation for User Story 4

- [X] T041 [US4] 在 `src/freegraph/runtime/superstep.py` 实现**挂起时的写侧**：经 `checkpointer.put(config, values=..., metadata=...)` 写**快照** + 经 `checkpointer.put_writes(config, writes=..., task_id=..., task_path=...)` 写**中断留痕**（通道名 **`__interrupt__`** · 载荷 = 中断载荷**元组**）⇒ ⇒ 关键字名**逐字**照 [`contracts/checkpoint-contract.md`](./contracts/checkpoint-contract.md) §4
- [X] T042 [US4] 在 `src/freegraph/runtime/superstep.py` 实现**恢复时的写侧**：经 `put_writes(...)` 写**恢复值**（通道名 **`__resume__`** · 载荷 = 恢复值**列表** · 按**节点内顺序**）⇒ ⇒ 在**执行之前**写 ⇒ ⇒ 恢复与首次运行**共用同一条执行路径**
- [X] T043 [US4] 在 `src/freegraph/runtime/superstep.py` 实现 `task_id` = **节点名** 的映射（freegraph 一轮一个节点一个任务 ⇒ 节点名**足够**唯一定位 ⇒ **更可读**）⇒ ⇒ 保留通道名 `__interrupt__` / `__resume__` **与上游逐字同款**

**Checkpoint**: 四个故事**全部**独立可跑 —— 恢复路径的**架构约束**可判定

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 影响**多个**故事的收尾（差分同款 · 结构纪律 · 回溯修订 · 人工验证 · 跨 feature 接线）

- [X] T044 [P] 在 `tests/differential/parity_probe.py` 追加 **DI-01…DI-08** 八个差分场景（**`DI-` 前缀** · ⚠️ **MUST NOT** 用 `D-01…D-08` —— 探针内已有 B12F1 的 `D-01…D-15` 与 B7F4 的 `D-16…D-28` ⇒ **重号**）：`DI-01` 中断结果键 · `DI-02` 恢复跑完 · `DI-03` 从头重跑 · `DI-04` 未挂 checkpointer 失败 · `DI-05` 写入不丢 · `DI-06` 多 interrupt 顺序匹配 · `DI-07` 跨节点多挂起 · `DI-08` 单值恢复失败）⇒ ⇒ 判词照 spec §Upstream Parity §3（**SAME** 6 条 / **STRICTER** 2 条）⇒ ⇒ **既有 43 个场景逐字不变**（SC-016）
- [X] T045 [P] 在 `tests/runtime/test_interrupt_contract.py` 写**结构纪律**用例：`runtime.__all__` 的符号**集合** == **预期清单本身**（清单共 **23** 项 = 20 + `InterruptResult` / `InterruptError` / `run_graph` · ⚠️ **断言里 MUST NOT 写死数字** ⇒ ⇒ 写**清单**、不写「23」）· ⚠️ **补**（**2026-11-13 分析轮回修 · 判据级可追溯性**）：**L1 的 20 符号面零改动**（`freegraph.contracts.__all__` 的**集合相等** + **逐字相等**的清单 —— ⚠️ **断言里 MUST NOT 写死数字** ⇒ 写**清单**）⇒ ⇒ 这是 **SC-007 / FR-017** 的**可判定出口**（此前二者只挂**实现**任务或**挂错对象** ⇒ 判据不可测）· L2 → L3/L4/L5 的依赖边数 == **0**（导入图断言 · 门禁 **G25**）· 新增模块内**零** `os.environ` / `os.getenv` / `socket` / `urllib` / 网络调用（门禁 **G4 / G24 / G26**） ⇒ ⇒ ⚠️ **分工**（补）：本任务是**模块内自检**（**AST 级**）⇒ ⇒ 门禁 **G4 / G24 / G26** 本身在 **T051** 的**全量跑**里**独立**判定 ⇒ ⇒ 二者**不重复**（自检 + 门禁**双保险**）
- [X] T046 [P] 回溯修订 **T-1** 的**文档侧**：`specs/b12f1-concurrency-errors/tasks.md` 的 **T072** ⇒ 改为「与本 feature 的 `runtime.__all__` 清单**集合相等**」（**不硬编码数字**）⇒ ⇒ **拆分而不删**
- [X] T047 填 `harness/verification/B10F1/manual-verification.md` 的「**实际输出 / 结论 / 遗留问题**」三段（**实跑** · 禁编造）⇒ ⇒ 内容 MUST 覆盖五点：① §门禁项的偏离登记 **V-1 / V-2 / V-3 / V-4** 的**四要素**（被偏离门禁项 / 根因 / 判据未放宽的论证 / 承接方）② **已达成部分**：本 feature 自身的**挂起侧**人工验证（走 L2 入口 `run_graph`）的**实测输出** ③ 立项书 **§9.3** 的**三份附加材料**：**依赖断言轮**的输出（隔离 venv 的依赖闭包清单 + `sys.modules` 检查结果）·「**框架出站**」计数为 **0** 的监测记录 · **反向断言**结果（运行期未 import `langchain`） ④ **追认文字**（**发起者本人**确认 + 日期）⑤ 本 feature **新增**上游断言的**取证纪律**（每条带 **版本 + `路径:行号`** · 行为断言带**实测**编号（**E-1…E-26**）· **SC-021**）
- [X] T048 **【阻断合入】** 取得**发起者追认**（✅ **已取得** —— **发起者本人于 **2026-11-14 的收尾会话**中明确确认「**人工验收通过**……该勾选的文件就勾掉，**该签的就签**」⇒ ⇒ 追认文字**已落盘**：`harness/verification/B10F1/manual-verification.md` **§6.2**（**V-1 / V-2 / V-3 / V-4** + **T-1** 的 **7 处** + **PR-6 / PR-7 / PR-9 / PR-10** 共 **9** 项）⇒ ⇒ **追认次数 = 1**（宪法 v1.6.0 · E-6）⇒ ⇒ **阻断合入条件已解除** ⇒ ⇒ **可以合入**）

> ✅ **追认文字的「清单」**（**2026-11-13 分析轮固化** ⇒ ⇒ **实施期逐字**落盘 ⇒ ⇒
> **MUST NOT** 改动其**结论** —— 结论来自发起者的逐项决定）⇒ ⇒
> ⚠️ **落盘的 provenance**：**发起者本人于 2026-11-14 的收尾会话**中明确确认
> （「**人工验收通过**……该勾选的文件就勾掉，**该签的就签**」）⇒ ⇒ **已签**（**追认次数 = 1**）⇒ ⇒
> 落点 = `harness/verification/B10F1/manual-verification.md` **§6.2**：
> **MUST NOT** 改动其**结论** —— 结论来自发起者在本轮会话内的逐项决定）：
>
> | # | 追认项 | 四要素（**MUST 全部出现**） |
> |---|---|---|
> | **V-1** | **人工门禁**的「**恢复侧真跑一轮**」 | ① 被偏离项：人工门禁（宪法质量门禁第 5 条 + 原则 V）的「恢复侧真跑一轮」② 根因：可用的 checkpointer 实现（`MemorySaver`）属 **B14F1 / M3**，本 feature 在 **M1** **物理不可达成** ③ 判据未放宽的论证：红线判据（依赖 / 零环境变量 / 零出站 / L1 符号面 / 导入图）**全部照常**执行；恢复路径**已**用**桩**可判定 ④ 承接方：**B14F1 / M3** + 承接机制（B14F1 的 `manual-verification.md` 补上那一轮的实测输出） |
> | **V-2** | **自动门禁**（门禁 4）的「**fake 模型跑通验收基线的一轮**」 | ① 被偏离项 ② 根因：固定脚本需 `compile()` + `invoke()` = **B7F2 / B7F3 / M2** ③ 判据未放宽的论证：门禁 4 的**其余**部分（**CI 全绿** + **G1–G30**）**照常**执行 ④ 承接方：**B7F3 / M2** + 承接机制（B7F3 的 `manual-verification.md` 补上该轮的实测输出） |
> | **V-3** | **人工门禁**（门禁 5 + 原则 V 第 2 轮）的「**真实模型再跑一遍**」 | ① 被偏离项 ② 根因：同 **V-2**（本 feature **不涉及任何模型调用**）③ 判据未放宽的论证：同 **V-2** ④ 承接方：**B7F3 / M2**（与 **V-2** **同棒承接**） |
> | **V-4** | **契约门禁**（门禁 3）的「`target.py` **真跑**」 | ① 被偏离项 ② 根因：`target.py` 需 `compile()` + `invoke()` = **B7F2 / B7F3 / M2** ③ 判据未放宽的论证：**G29 ①–④** 四条判定**全部可判定且恒绿**；**C8** 挂载点**保持** `not-landed · owner=B8F1`（**MUST NOT** 伪装成 `landed`）④ 承接方：**B7F3 / M2** + 承接机制（B7F3 的 `manual-verification.md` 补上该轮的实测输出） |
> | **T-1** | **破冻结面回溯修订**（**6 处**冻结断言） | ① 被回溯的冻结面：`runtime.__all__`（3 处）· `runtime.errors` 的符号面与异常类清单 · 门面 `interrupt` 的「未接线」测试 · `_primitives.py` 的「未接线守卫」② **判据零放宽**的论证：全部改成「**集合相等** / **更具体的断言**」（**不**改成「≥ N」）③ 追认落点：`harness/verification/B10F1/manual-verification.md`（**同一次**）④ **上游对照**（宪法「破冻结面的三条」第 ② 条）：四项**均属「上游无此项 ⇒ 必须自研区 ③」⇒ 零行为面偏离** ⇒ ⇒ **不**进偏离登记表（**X-1…X-5 仍为 5 项**） |
> | **PR-6 / PR-7** | **范围变更**（**+40 行** / **+60 行**） | ① 变更内容：PR-6 = 4 条判据级覆盖缺口 + 1 条会话连续语义；PR-7 = 3 条测试级覆盖缺口（**T056 / T057 / T058**）② 合计 **1,160 → 1,260 行**（实现 520 / 测试 740）③ **已发起者确认**（2026-11-13 分析轮）④ 立项书 §5.2 的 B10F1 行**已同步**（合计 31,220 → **31,320** 行） |
>
> ⚠️ **落盘的 provenance 规则（MUST · 防止「代签」）**：落盘时 MUST 记明「**发起者于 2026-11-13 分析轮会话内逐项确认**」（**日期 + 轮次**）⇒ ⇒ **MUST NOT** 由实现者改动上表**任何结论** ⇒ ⇒ ⇒ **MUST NOT** 伪造「发起者已实跑」的输出（**实际输出 / 结论 / 遗留问题**三段 MUST 来自 **T047** 的**实跑**）⇒ ⇒ ⇒ 落盘后 **T048** 才可勾选 ⇒ ⇒ ⇒
> **未落盘前 MUST NOT 合入**（宪法 E-6）。
- [X] T049 [P] 跨 feature 接线（**只接线 · 逐条最小改动** · MUST NOT 新增门禁编号）：`harness/features/B14F1_Checkpointer协议与MemorySaver.md`（**D-1**：读侧 `.snapshot` / `.pending_writes` / `.scheduler` + 写侧 `put` / `put_writes` + 保留通道名 + **V-1** 的承接）· `harness/features/B7F3_invoke返回完整状态.md`（**D-3**：`invoke` 接线 + L1 入参放宽 + 按 id 的映射恢复 + 未提供恢复值）· `harness/features/B13F1_静态中断点与递归上限.md`（**D-4**：挂起载体一致）· `harness/features/B16F1_update_state与时间旅行.md`（**D-7**：与恢复路径的边界）· ⚠️ **D-2**（`harness/features/B14F1_Checkpointer协议与MemorySaver.md`：**补一句「X-5 的消解条件」** —— 即「B14F1 落地后中断元组随 pending writes 留痕 ⇒ X-5 自动消解」⇒ **X-5 的消解条件**必须有落点）· ⚠️ **D-8**（`harness/features/B7F3_invoke返回完整状态.md`：**承接偏离登记 V-2 / V-3** —— 「fake 模型跑通固定脚本一轮」+「真实模型再跑一遍」在 B7F3 落地 `invoke()` 后由 **B7F3** 的 `manual-verification.md` 补齐）
- [X] T050 [P] 核验 `harness/demo/graph_core.py` 的 C17 软断言**未被改动** ⇒ ⇒ **MUST NOT** 在本 feature 升级为硬断言（**会必红** —— 门面色断言须待 B7F3 的 `invoke` + B14F1 的真实 saver）⇒ ⇒ 升级动作**归 B14F1**（spec §软断言联动）

- [X] T058 [P] 在 `tests/runtime/test_interrupt_contract.py` 写**契约门禁逐条核对**用例（**SC-019**）：① 门禁 **G29** ①「只读基准零改动」⇒ 断言 `harness/demo/target.py` 与入库基准（`git show HEAD:…`）**逐字相同**⇒ ⇒ ② 门禁 **G29** ②「验收脚本集在**失败来源分级**下判为『环境未就绪 ⇒ 通过』」⇒ ⇒ ③ **C4** 的独立回归（`tests/contracts/test_contract_regressions.py` 的挂载点 `status=landed`）**恒绿** ⇒ ⇒ ④ **C8** 的挂载点**保持** `status=not-landed · owner=B8F1 · milestone=M2`（**MUST NOT** 改写成 `landed`）⇒ ⇒ ⚠️ **本任务补的是「测试级覆盖缺口」**（初版只有 T051 的**全量跑**兜底 ⇒ G29 的三条判定**无逐条落点**）⇒ ⇒ ⚠️ 偏离登记 **V-4** 已把「`target.py` **真跑**」延期到 **B7F3** ⇒ ⇒ **本任务只核对「照常执行」的那几部分**⇒ ⇒ 落 **PR-7**
- [X] T054 [P] 更新 `README.md` 的「**API 兼容矩阵**」章节中 `interrupt` **那一行**：由「**中断 / 恢复行为待 B10F1 交付**」改为「**中断 / 恢复行为已落地**（B10F1）」⇒ ⇒ **MUST NOT** 增删兼容矩阵的**行**（门面 7 个符号各恰一行）⇒ ⇒ 跑门禁 **G19 / G8** 确认**恒绿**（**FR-026 / SC-022** · 宪法原则 X · 质量门禁 7）⇒ ⇒ ⚠️ `THIRD_PARTY_NOTICES` **零新增行**（本 feature **零**新增第三方代码 ⇒ **零**新增依赖）⇒ ⇒ ⚠️ **附带订正**（**2 个文件 / 2 个物理位置** · 与 T011 的 ① / ② **同一类**陈旧文案 · **2026-11-13 分析轮扩容 · 第二轮修订计数口径**）：① 同章节「公开面的判定口径」里的「契约层 **18** 个符号」⇒ **20**（**实测** · 与 T011 同一处陈旧文案）② `tests/facade/test_facade_gates.py:407` 的 docstring 里的「**18** 个符号」⇒ **20**（**实测** · 同一处陈旧文案）⇒ ⇒ **MUST NOT** 增删**行**（**只**订正文案）
- [X] T055 [P] **Phase 7 终检复跑**门禁 **G25**（`harness/scripts/gates/gate_G25_import_graph.py --root .`）⇒ ⇒ 退出码 == **0** ⇒ ⇒ 并**逐条核对**：① `src/freegraph/_primitives.py` **不** import `runtime/`（**跨注册表条目的同层 import** ⇒ 判红）② `src/freegraph/graph.py` 的 `interrupt` 来源是**模块级** `from .runtime._interrupt import interrupt`（`facade-L1-L3` 例外）③ `runtime/` 内部的互相 import **合法**（同一注册表条目）⇒ ⇒ **PR-4** 的落点合规 ⇒ ⇒ 同时跑 `tests/facade/test_facade_gates.py` + `tests/contracts/test_architecture.py` **恒绿**（G14 / G15 / G16 / G18）⇒ ⇒ ⚠️ **本任务是终检复跑** ⇒ ⇒ **实现期的首次运行 MUST 紧跟 T019**（见 T019 的落点说明）⇒ ⇒ ⚠️ 另须复跑 **T012-a（①–④）** 与 **T012-b（⑤⑥）** 回溯修订的**六处**断言 ⇒ ⇒ **恒绿**
- [X] T051 全量验收：`.venv/bin/python -m pytest -q` **零回归** + 差分闸口 **43 + 8** 条符合判词 + 门禁 **G1–G30** 全绿（含 **G25** 导入图 · **G19 / G8** 兼容矩阵 · **G29** 契约门禁载体）+ `harness/verification/B10F1/acceptance.py` 退出码 == **0**

---

## 行数预算（**约束** · 立项书 §5.2 的 ~~1,160 行 = 实现 520 / 测试 640~~ ⇒ ⇒ **实施期实测口径 2,945 行 = 实现 1,091 / 测试 1,854**（**PR-10** · 已追认） · ⚠️ **PR-6 登记 +40 行** · ⚠️ **PR-7 再登记 +60 行** ⇒ ⇒ **实施口径 = 1,260 行 = 实现 520 / 测试 740**）

> ⚠️ 本表是**分配**（**不是**估算）⇒ ⇒ **实施期当约束用** ⇒ ⇒ 某块**超出** ⇒ ⇒
> **走范围变更**（**MUST NOT** 悄悄超支）⇒ ⇒ ⚠️ **引用订正**：初版写的「宪法 §10 **R5** · 范围膨胀」
> **不准确** —— 立项书 §10 的 **R5** 是「**范围膨胀到评测平台**」的**风险条目**，**不是**范围变更的
> **流程** ⇒ ⇒ 范围变更走**立项书 §12 的待决流程**（**发起者拍板**）⇒ ⇒ 见 **PR-6**。
>
> ⚠️ **PR-6 · 范围变更（+40 行 · +3.4% · ✅ 发起者已确认）**：2026-11-13 分析轮补齐了 **4** 条
> **判据级覆盖缺口**（**SC-015** 的「按 id 映射恢复**成功**」半边 · **FR-013** ⑦「dict 非 map」
> · 补记 **F-2**「resume 与 update 并存」· **FR-010**「跨运行不得持有现场」）**+ 1** 条语义补齐
> （**FR-013** 末行「**会话连续**」的上游同款行为）⇒ ⇒ **实现**行数**不变**（会话连续的读写并入
> **T010** 的既有预算）⇒ ⇒ **测试**行数 **640 → 680** ⇒ ⇒ **合计 1,160 → 1,200** ⇒ ⇒ ⇒
> ✅ **发起者已确认**（**2026-11-13 分析轮** · **并入 V-1 的那一次追认**）⇒ ⇒ ⇒ ✅ **立项书 §5.2 已同步**（1,160 → **1,260** · 合计 31,220 → **31,320** 行）
> （**发起者**确认后由**发起者本人**更新 ⇒ ⇒ 本 feature **MUST NOT** 自行改立项书）。
> 
> ⚠️ **PR-7 · 范围变更（+60 行 · +5.0% · ✅ 发起者已确认）**：2026-11-13 分析轮**实测**发现 **3** 条
> **测试级覆盖缺口**（**SC-008**「真异常优先」**只有实现任务 · 无测试** · **FR-013 末行**
> 「会话连续」**只有实现任务 · 无测试**（PR-6 只补了实现面）· **SC-019**「契约门禁」只由
> **T051** 兜底 · **无逐条核对**）⇒ ⇒ ⇒ 新增 **3** 条测试任务（**T056 / T057 / T058**）
> ⇒ ⇒ **实现**行数**不变**（**只加测试**）⇒ ⇒ **测试**行数 **680 → 740** ⇒ ⇒ **合计 1,200 → 1,260**
> ⇒ ⇒ ✅ **发起者已确认**（**2026-11-13 分析轮** · **并入 V-1 的那一次追认**）⇒ ⇒ ⇒ 立项书 §5.2 的
> ⇒ ⇒ ⚠️ **PR-8**（破冻结面清单扩容为 **6 处** ·
> **判据零放宽**）的追认**同一次**打包 ⇒ ⇒ **追认次数仍为 1 次**（宪法 E-6）。

| 块 | 实现（行） | 测试（行） | 覆盖的任务 | **实施期实测** |
|---|---|---|---|---|
| Phase 2 · Foundational（地基） | **200** | **60** | T005–T013 · **T012-a** | 实现 **1,091** / 测试 **≈ 700** |
| US1（P1）挂起与交还 | **120** | **125** | T014–T021 · **T056** · **T012-b** | ↑ |
| US2（P2）恢复闭环 | **110** | **190** | T022–T031 · **T052** · **T057** | ↑ |
| US3（P3）从头重跑 | **45** | **90** | T032–T037 | ↑ |
| US4（P4）经由 checkpointer | **45** | **135** | T038–T043 · **T053** | ↑ |
| Polish（差分 / 纪律 / 验证 / 接线） | — | **140** | T044–T051 · T001–T004 · **T045** · **T054** · **T055** · **T058** | ↑ |
| **合计** | **520** | **740** | **合计 1,260 行（立项书口径 1,160 + PR-6 的 +40 + PR-7 的 +60 · 发起者已确认）** | **实现 1,091 / 测试 1,854 ⇒ 合计 2,945 行** |

> ⚠️ **PR-10 · 范围变更（**实施期实测超支** · **+1,685 行 / +134%** · ⬜ **待发起者追认**）**：
> **实施期实测**（`git diff --numstat` + 新文件行数 · **不含** `harness/verification/B10F1/acceptance.py`
> 的 **398** 行「验收工件」· **不含**文档侧改动）⇒ **实现 1,091**（预算 **520** ⇒ **+571**）·
> **测试 1,854**（预算 **740** ⇒ **+1,114**）⇒ **合计 2,945**（预算 **1,260** ⇒ **+1,685** · **+134%**）。
>
> **超支的构成（逐项可核）**：① **T-1 的 7 处冻结断言回溯修订**（含**新增**的**单一事实源**
> `tests/runtime/_runtime_export_manifest.py` · **107** 行）+ **PR-9** 的第 ⑦ 处 ⇒ ⇒ **判据零放宽**
> （**只改断言形态**）；② **PR-8 / PR-9** 的**实测化**要求 ⇒ ⇒ **必须逐条**回溯修订**每一条**
> 既有断言 ⇒ ⇒ 工作量**不可压缩**（**不可省** ⇒ 省了就「必红」）；③ **差分探针**的
> **两段式**能力 + `"interrupt-shape"` 口径 + **8** 个 `DI-` 场景（**parity_probe.py` **+544**）；
> ④ **本 feature 的** 6 个测试文件（**1,288**）+ **桩** checkpointer + **会话连续**路径
> （`_reset_entry_triggers` 等）⇒ ⇒ **零**功能删减 ⇒ ⇒ **如实登记超支** ⇒ ⇒
> **MUST NOT** 悄悄超支（宪法「MUST NOT 悄悄超支」）⇒ ⇒ **由发起者在 V-1 的那一次追认中
> 一并追认**（**不**新增追认次数）⇒ ⇒ **立项书 §5.2 的 B10F1 行 MUST 同步为 2,945**
> （**由发起者拍板后**执行 · **本 feature MUST NOT** 自行改立项书）。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 —— 可立即开始
- **Foundational (Phase 2)**: 依赖 Setup —— **BLOCKS** 全部用户故事
- **User Stories (Phase 3–6)**: 全部依赖 Foundational 完成 ⇒ ⇒ **可并行**（若人手够）
  - **建议顺序**：US1 → US2 → US3 → US4（**语义依赖**：US2 的恢复需要 US1 的挂起；US3 需要 US2 的恢复；US4 需要 US2 的读侧）
- **Polish (Phase 7)**: 依赖全部目标故事完成（差分场景依赖四个故事的**可判定出口**）

### User Story Dependencies

- **US1 (P1)**: Foundational 之后即可开始 —— **不依赖**其它故事 ⇒ ⇒ **MVP**
  （**T056**「真异常优先」属 US1 的**判据级**补漏 ⇒ ⇒ 与 US1 同批交付）
- **US2 (P2)**: Foundational 之后即可开始 —— 需要 US1 的**挂起**作为前置（**实现上**依赖 · **验收上**独立）
  （**T057**「会话连续」属 US2 的**判据级**补漏 ⇒ ⇒ 与 US2 同批交付）
- **US3 (P3)**: 需要 US2 的**恢复**才能跑（实现上依赖 · 验收上独立）
- **US4 (P4)**: 需要 US2 的**读侧**才能跑（实现上依赖 · 验收上独立）

### Within Each User Story

- 测试 MUST 先写并**确认其失败**（红 ⇒ 绿）
- 异常族 / 结果载体 → 运行期上下文 → 图级入口 → 场景接线
- 故事完成后再进下一个优先级

### Parallel Opportunities

- Setup 的 T002 / T003 / T004 可并行（不同文件）
- Foundational 的 T005 / T006 可并行（不同文件）⇒ ⇒ ⚠️ **T013 MUST NOT** 与它们并行（它**依赖 T010** 的 `run_graph`）⇒ ⇒ **T013** 排在 T010 之后
- 每个故事的**测试任务**可并行（同文件内**顺序**写 ⇒ 按 T014→T017 顺序落笔 ⇒ **T052** 落在
  `test_interrupt_resume.py`（⇒ 与 T022 / T032 / T033 / T034 **同文件** ⇒ 按**编号顺序**落笔）
  · **T053** 落在 `test_interrupt_checkpoint.py`（⇒ 与 T038 / T039 / T040 **同文件** ⇒ 同上）
- 四个故事在 Foundational 之后**可并行**（不同测试文件 + 不同实现点）
- Polish 的 T044 / T045 / T046 / T049 / T050 / **T054** / **T055** / **T058** 可并行（不同文件）
- ⚠️ **同文件内**的补漏任务 MUST **按编号顺序**落笔（**T056** → `test_interrupt_basic.py` ·
  **T057** → `test_interrupt_resume.py`）

---

## Parallel Example: User Story 1

```bash
# 一次性并行启动 US1 的 5 个测试任务（此时 MUST 失败 —— `interrupt()` 尚未接线）：
Task: "在 tests/runtime/test_interrupt_basic.py 写用例：节点调 interrupt(\"approve?\") ⇒ 断言结果含 __interrupt__ 键 …"
Task: "在 tests/runtime/test_interrupt_basic.py 写用例：中断前的状态写入不丢失 …"
Task: "在 tests/runtime/test_interrupt_basic.py 写用例：同一 super-step 内两个节点同时中断 …"
Task: "在 tests/runtime/test_interrupt_basic.py 写用例：挂起时返回类型 == InterruptResult …"
Task: "在 tests/runtime/test_interrupt_basic.py 写用例：真异常优先（SC-008）…"

# 测试落笔后并行启动 US1 的实现任务：
Task: "在 src/freegraph/runtime/_interrupt.py 实现 interrupt(value) 的抛出分支 …"
Task: "按 PR-4 的唯一合法形态接线：_primitives.py 删掉 interrupt 实现体 + graph.py 改模块级 import …"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1: Setup（基线 + 骨架）
2. 完成 Phase 2: Foundational（**CRITICAL** —— 阻塞全部故事）
3. 完成 Phase 3: User Story 1
4. **STOP and VALIDATE**: 独立验证 US1（中断 → `__interrupt__` → 交还调用方）
5. 记录中间态（**不**合入 —— 追认未落 ⇒ T048 阻断合入）

### Incremental Delivery

1. Setup + Foundational ⇒ 地基就绪
2. + US1 ⇒ 中断可交还（**MVP**）
3. + US2 ⇒ 恢复闭环成立（**HITL 可用**）
4. + US3 ⇒ 「从节点起点重跑」的语义可判定
5. + US4 ⇒ 恢复**确实经由 checkpointer**（架构约束落地）
6. + Polish ⇒ 差分同款 · 结构纪律 · 人工验证 · 追认 · 跨 feature 接线 ⇒ **可合入**

### Parallel Team Strategy

1. 团队共同完成 Setup + Foundational
2. 之后：
   - 开发 A：US1 + US2（**语义链**：挂起 → 恢复）
   - 开发 B：US3（语义正确性 · 依赖 US2 的接口但可**并行写测试**）
   - 开发 C：US4（架构约束 · 依赖读侧接口）
   - 开发 D：Polish 的差分探针扩展（T013 已在 Foundational 完成 ⇒ 只需补场景）
3. 各故事**独立**验收 ⇒ 最后汇合 ⇒ **T048** 追认 ⇒ 合入

---

## Notes

- [P] = 不同文件 · 无未完成依赖
- [Story] 标签映射到 spec 的 P1…P4（US1…US4）
- **测试 MUST 先写并先失败**
- ⚠️ **本 feature **不实现**任何 checkpointer**（FR-019）⇒ 测试用**桩** ⇒ ⇒ 「恢复侧真跑一轮」的人工验证**延期到 B14F1**（**V-1**）
- ⚠️ **MUST NOT** 在本 feature 改 `harness/demo/graph_core.py` 的断言等级（T050）
- ⚠️ **MUST NOT** 改 L1 的任何文件（`src/freegraph/contracts/**`）⇒ ⇒ 门禁 **G7 / G8 / G16 / G19** 恒绿
- ⚠️ **MUST NOT** 改 `run_super_step` / `run_super_steps` 的签名与返回类型（B7F1 冻结面）
- ⚠️ **门禁 G25（导入图单向）是硬约束**（**PR-4**）⇒ ⇒ `_primitives.py`（L2 单文件条目）
  **MUST NOT** import `runtime/`（L2 目录条目）⇒ ⇒ **跨注册表条目的同层 import = 判红**
  ⇒ ⇒ `interrupt()` 的**运行期机制**必须住在 `runtime/_interrupt.py` · 门面 `graph.py` 用
  **模块级** import 转出 ⇒ ⇒ **实现期 MUST 先跑** `gate_G25_import_graph.py`（**T055**）
- ⚠️ **差分场景编号 MUST 用 `DI-01…DI-08`**（**不是** `D-01…D-08`）⇒ ⇒ 探针内已有 B12F1 的
  `D-01…D-15` 与 B7F4 的 `D-16…D-28` ⇒ ⇒ **重号** ⇒ ⇒ 既有场景名**逐字不动**
- ⚠️ **冻结断言共七处**（`test_command_purity.py`（**1** 处）· `test_superstep_concurrency.py`（**2** 处）·
  `test_read_contract.py`（**2** 处）· `test_facade/test_facade.py`（**1** 处）·
  `test_superstep_purity.py`（**1** 处 · **PR-9** **实施期实测**新增））⇒ ⇒ MUST **七处同改**
  （**只改一处 ⇒ pytest 必红**）⇒ ⇒ ⚠️ **拆成两条任务落笔**（**2026-11-13 分析轮第二轮**）：
  **T012-a**（**①–④ + ⑦** · Phase 2 · 落地后即可判定 ⇒ ⇒ **Phase 2 MUST 全绿**）+
  **T012-b**（**⑤⑥** · **MUST 紧随 T019** ⇒ ⇒ 提前落笔 ⇒ **必红**）⇒ ⇒ ⚠️ **2026-11-13 分析轮实测**：初版只登记了 **3 处** ⇒ ⇒
  **PR-8** 扩容为 **6 处** ⇒ ⇒ **实施期实测**再发现 **1 处** ⇒ ⇒ **PR-9** 扩容为 **7 处**
  ⇒ ⇒ **判据零放宽**（全部改成「集合相等 / 更具体的断言」）
- ⚠️ **`runtime/superstep.py` 内 MUST NOT 出现裸标识符 `interrupt`**（AST 纯净性断言：
  `tests/runtime/test_superstep_purity.py` 与 `tests/runtime/test_command_purity.py` 的
  `FORBIDDEN_NAMES` 含 `"interrupt"` ⇒ **只扫** `superstep.py`）⇒ ⇒ 本 feature 的 **14** 条实现任务
  （T006 / T007 / T009 / T010 / T020 / T027 / T028 / T029 / T031 / T036 / T037 / T041 / T042 / T043）
  全在 `superstep.py` 内 ⇒ ⇒
  （⚠️ **2026-11-13 分析轮回修**：初版只列 **8** 条 ⇒ ⇒ **漏** T007 / T009 / T031 ⇒ ⇒ 三条同样 MUST NOT 写裸 `interrupt`；
  ⚠️ **实施期再校**：**逐条**核对 `tasks.md` 的实现任务 ⇒ ⇒ 补上 **T020 / T028 / T043** ⇒ ⇒ **共 14** 条
  ⇒ ⇒ **实测**：**全部 14** 条实现任务**已落地** ⇒ ⇒ 既有断言**恒绿** ⇒ ⇒ **判据零放宽**）⇒ ⇒ ⇒
  **只**通过 `runtime/_interrupt.py` 的**模块名**（`_interrupt`）与 `Interrupt` / `InterruptResult`
  等**大写**名间接引用 ⇒ ⇒ **MUST NOT** 写 `interrupt(...)` 之类的裸调用
- ⚠️ **任务 ID 的编号顺序 ≠ 执行顺序**：`T052`–`T058` 是**分析轮补漏 / 收尾**任务
  （追加编号）⇒ ⇒ 执行时以 **Phase 归属 + Dependencies 段**为准 ⇒ ⇒ **T052** 落在
  `test_interrupt_resume.py` · **T053** 落在 `test_interrupt_checkpoint.py` · **T056** 落在
  `test_interrupt_basic.py` · **T057** 落在 `test_interrupt_resume.py` · **T058** 落在
  `test_interrupt_contract.py` ⇒ ⇒ **同文件内按编号顺序落笔**
- ⚠️ **T012 拆为两条**（**2026-11-13 分析轮第二轮**）：**T012-a**（①–④ · **Phase 2**）·
  **T012-b**（⑤⑥ · **US1 · 紧随 T019**）⇒ ⇒ ⚠️ **T012-b MUST NOT** 提前落笔（⇒ **必红**）⇒ ⇒
  同文件内（T012-a 与 T012-b 各改**不同**文件 ⇒ 可分别落笔）
- ⚠️ **MUST NOT** 改 `SuperStepResult` 的字段数（B12F1 裁定 25 ②）
- 每个逻辑组完成后提交；每个 Checkpoint 处可停下独立验收

---

## 附录 · 任务 ↔ spec 追溯表

### FR → 任务

| FR | 任务 |
|---|---|
| **FR-001** | T018 · T019 |
| **FR-002** | T014 · T020 · T021 |
| **FR-003** | T018 · T036 |
| **FR-004** | T016 · T020 |
| **FR-005** | T017 · T020 |
| **FR-006** | T015 · T029 |
| **FR-007** | T020 · **T056** |
| **FR-008** | T022 · T027 · T030 |
| **FR-009** | T032 · T035 · T036 |
| **FR-010** | T028 · T038 · **T053** |
| **FR-011** | T023 · T027 |
| **FR-012** | T040 · T041 |
| **FR-013** | T010 · T024 · T025 · T027 · T037 · **T052** · **T057** |
| **FR-014** | T025 · T028 |
| **FR-015** | T033 · T035 |
| **FR-016** | T045 |
| **FR-017** | T045 · T051 |
| **FR-018** | T007 · T028 · T039 · T041 · T042 |
| **FR-019** | T038 · T040 · **T045**（**结构纪律**用例：`src/freegraph/**` 内**零** saver 实现 · 测试**全**用桩）|
| **FR-020** | T010 · T027 · T029 |
| **FR-021** | T006 · T020 · T021 |
| **FR-022** | T029 · T031 |
| **FR-023** | T002 · T045 |
| **FR-024** | T051（**零**越界 ⇒ 由 T045 的不变量覆盖）· **T058** |
| **FR-025** | T026 |
| **FR-026** | T054 |

### SC → 任务

> ⚠️ **判据级覆盖口径**（宪法 **v1.11.0** 原则 VI 的「可追溯性 MUST 到判据级」）：
> 每条 **SC** MUST 至少挂**一条能判定它**的任务 ⇒ ⇒ 「**实现**任务」**不**构成判定覆盖
> ⇒ ⇒ 下表凡标 **（文档 / 验证类判据）** 者，其判定手段**不是**代码测试，而是**可执行**的
> 文档 / 验证动作（文件存在且五段齐全 · 矩阵行逐字更新 · 差分场景判词 · 上游锚点取证）
> ⇒ ⇒ ⇒ 其余各条**均**挂**测试任务**（含「写用例 / 写核验用例 / 写桩」等）。

| SC | 任务 |
|---|---|
| **SC-001** | T014 |
| **SC-002** | T022 · T050 |
| **SC-003** | T032 |
| **SC-004** | T015 |
| **SC-005** | T038 |
| **SC-006** | T045 |
| **SC-007** | T045（**L1 的 20 符号面集合相等** · 判据级）· T051 · **T054** |
| **SC-008** | T020 · **T056** |
| **SC-009** | T016 |
| **SC-010** | T017 |
| **SC-011** | T023 |
| **SC-012** | T024 |
| **SC-013** | T034 · T040 |
| **SC-014** | T033 |
| **SC-015** | T027 · T044（**DI-08**） · **T052** |
| **SC-016** | T013 · T044（**差分场景判词类判据** ⇒ T044 的 8 个场景即判定器）|
| **SC-017** | T045 |
| **SC-018** | T045 · T051 |
| **SC-019** | T051 · **T058** |
| **SC-020** | T001 · T047 · T048（**文档 / 验证类判据** ⇒ 文件存在 + 五段齐全 + 追认落盘）|
| **SC-021** | T044（差分场景**再取证**）· **T047**（人工验证记录里**逐条核对**锚点与实测编号）（**文档 / 取证类判据** ⇒ 锚点带 `版本 + 路径:行号` + 行为断言带实测编号）|
| **SC-022** | T054（**文档 / 验证类判据** ⇒ 兼容矩阵 `interrupt` 行逐字更新 + 门禁 **G19 / G8** 恒绿）|

### 下游承接覆盖（**D-1…D-8**）

| 承接 | 承接方 | 里程碑 | 任务 | 状态 |
|---|---|---|---|---|
| **D-1** | B14F1（检查点契约 + 人工验证承接） | M3 | T049 | ⬜ 待接线 |
| **D-2** | B14F1（**补一句「X-5 的消解条件」**） | M3 | T049 | ✅ **已接线**（既有）· **本 feature 补一句**（`harness/features/B14F1_*.md` §2 ⇒ 补「X-5 的消解条件」）|
| **D-3** | B7F3（`invoke` 接线 + L1 入参放宽） | M2 | T049 | ⬜ 待接线 |
| **D-4** | B13F1（静态中断点的挂起载体一致） | M1 | T049 | ⬜ 待接线 |
| **D-5** | B15F1（`StateSnapshot.interrupts` 生产者） | M3 | — | ✅ **已接线**（B12F1 的 D-7 ⇒ 无需任务） |
| **D-6** | freechain（审批 UI / 通知） | v2 | — | — （跨项目 · 非本仓库） |
| **D-7** | B16F1（时间旅行与恢复路径的边界） | M3 | T049 | ⬜ 待接线 |
| **D-8** | B7F3（**承接偏离登记 V-2 / V-3**） | M2 | T049 | ⬜ 待接线（**2026-11-13 分析轮新增**） |

### 任务 → FR / SC（反向覆盖 · 每条任务至少挂一条 **FR 或 SC**）

> ⚠️ **验证 / 门禁 / 接线类**任务（T001 · T004 · T013 · T044 · T047 · T048 · T050 · T051）**不产出 FR 行为**
> ⇒ ⇒ 它们**只挂 SC**（**核验的是判据，不是行为**）⇒ ⇒ **不**算「漏挂」⇒ ⇒ 判据口径见 **SC-020**。

| 任务 | FR |
|---|---|
| T001 | SC-020 |
| T002 | FR-023 |
| T003 | SC-020 · FR-019（**测试骨架**）|
| T004 | SC-020 |
| T005 | FR-011 · FR-013 · FR-014 · FR-025 |
| T006 | FR-002 · FR-021 |
| T007 | FR-018 |
| T008 | FR-001 · FR-009 |
| T009 | FR-009 · FR-022 |
| T010 | FR-013 · FR-020 |
| T011 | FR-021 · SC-007 |
| **T012-a** | FR-021 |
| **T012-b** | FR-021 |
| T013 | SC-016 |
| T014 | FR-002 · SC-001 |
| T015 | FR-006 |
| T016 | FR-004 |
| T017 | FR-005 |
| T018 | FR-001 · FR-003 |
| T019 | FR-001 |
| T020 | FR-002 · FR-005 · FR-007 |
| **T056** | FR-007 · SC-008 |
| T021 | FR-021 |
| T022 | FR-008 · SC-002 |
| T023 | FR-011 |
| T024 | FR-013 |
| T025 | FR-014 |
| T026 | FR-025 |
| T027 | FR-013 · FR-020 |
| T028 | FR-010 · FR-014 · FR-018 |
| T029 | FR-006 · FR-022 |
| T030 | FR-008 |
| T031 | FR-022 |
| T032 | FR-009 · SC-003 |
| T033 | FR-015 |
| T034 | FR-003 · FR-015 |
| T035 | FR-009 · FR-015 |
| T036 | FR-003 |
| T037 | FR-013 |
| T038 | FR-010 · FR-019 |
| T039 | FR-018 |
| T040 | FR-012 · FR-019 |
| T041 | FR-012 · FR-018 |
| T042 | FR-012 · FR-018 |
| T043 | FR-018 |
| T044 | SC-016 |
| T045 | FR-016 · FR-017 · FR-023 · SC-007 |
| T046 | FR-021 |
| T047 | SC-020 |
| T048 | SC-020 |
| T049 | FR-018 · FR-021 |
| T050 | SC-002 |
| T051 | FR-024 · SC-019 |
| **T052** | FR-013 · SC-015 |
| **T053** | FR-010 |
| **T054** | FR-026 · SC-022 |
| **T055** | FR-016 |
| **T057** | FR-013 · SC-002 |
| **T058** | FR-024 · SC-019 |
