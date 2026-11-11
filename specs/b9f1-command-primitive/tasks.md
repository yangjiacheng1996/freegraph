---
description: "Task list for B9F1 · Command 原语（goto / update + Command.PARENT）"
---

# Tasks: B9F1 · `Command` 原语（`goto` / `update` + `Command.PARENT`）

**Input**: Design documents from `/specs/b9f1-command-primitive/`
**Prerequisites**: plan.md（required）· spec.md（required · 用户故事）· research.md · data-model.md ·
contracts/（`command-contract.md` + `upstream-parity.md`）· quickstart.md

**Tests**: **包含**测试任务 —— spec FR-020 / SC-016 要求「纯单元可测 + 行/分支覆盖率 == 100%」
⇒ **MUST 先写 · MUST 先失败**（入口此时抛 `NotImplementedError` ⇒ Phase 2 只出骨架桩）。

**Organization**: 按用户故事分组（**6** 个 · P1–P6）⇒ 每个故事可**独立实现、独立测试**。

---

## 格式：`[ID] [P?] [Story] 描述`

- **[P]**：可并行（不同文件 / 无未完成依赖）
- **[Story]**：所属用户故事（US1…US6）—— 仅**用户故事阶段**的任务带
- **每条任务 MUST 带确切文件路径**（本仓库约定）

## 路径约定

- 源码：`src/freegraph/runtime/`（L2 · 层注册表**目录条目** ⇒ **零改动**）
- 测试：`tests/runtime/`（⚠️ **MUST NOT** 放 `tests/contracts/` —— 门禁 **G2** 禁该目录 import `freegraph.*`）
- 人工验证：`harness/verification/B9F1/`
- 本 feature **只改** `src/freegraph/runtime/superstep.py`（**既有文件** ⇒ 不新建模块 ⇒ 层注册表零改动）

---

**本 feature 的可测判据总表**（**23 FR + 25 SC ↔ 39 条任务**）：
追溯见文末「**附录 · 任务 ↔ spec 追溯表」** —— **每个 FR 与每个 SC 均至少被一条任务映射**
（**FR 23/23 · SC 25/25**）· **反向**：**每条任务**携带的义务 MUST 挂上**至少一条 FR**
⇒ 追溯表**双向**齐全（宪法原则 VI）。
> ⚠️ **本表 = 摘要**：**权威映射 = 文末「任务 ↔ spec 追溯表」** ⇒ 修改判据归属时 MUST **同步**两处。
其中 **SC-001 / SC-002**（跳转 + 更新**同时生效**）由 **T013 / T014 / T015** 承载；
**SC-003 / SC-004 / SC-023**（三形态**共用同一条合并路径** · 未知 key · 覆盖型冲突）由 **T017 / T018** 承载；
**SC-005**（`Command.PARENT` **可判定**）由 **T020 / T021** 承载；
**SC-006 / SC-012**（空操作 · `resume` 只被接受）由 **T026 / T027** 承载；
**SC-007 / SC-010 / SC-011 / SC-023**（叠加 · 生命周期 · 多目标 · 触发与入参）由 **T024 / T025** 承载；
**SC-008**（`END` 不跳转 + **更新照常生效** + **门面 `END` == L2 字面量**）由 **T013 / T016 / T030** 承载；**SC-009**（非法目标 ⇒ 显式失败）由 **T022 / T023** 承载；
**SC-013**（原子性）由 **T028** 承载；**SC-014 / SC-015 / SC-016**（纯净性 · 结构纪律〔含**门面 `END` == L2 字面量**与**两个构造签名逐字不变**〕· 覆盖率）
由 **T002 / T030 / T032 / T033 / T041** 承载；**SC-017**（人工验证记录）由 **T004 / T036 / T037 / T038 / T042** 承载；
**SC-018**（偏离登记 + 追认）由 **T039** 承载；**SC-019**（确定性 + 不串扰）由 **T029** 承载；
**SC-020**（上游引用纪律）由 **T001 / T034 / T040 / T042** 承载；**SC-021**（命令列表）由 **T018** 承载；
**SC-022**（写入归源节点）由 **T014** 承载；**SC-024**（跳转的可观察出口）由 **T030** 承载；
**SC-025**（可观测层不越界 + B19F1 已接线）由 **T035** 承载。
**T039**（**发起者追认** · 登记项 **R-1…R-5**）与 **T035**（下游承接接线复核）是**阻断合入**的任务。

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 取证工件核对 + 依赖面基线 + 测试/验收工件骨架（本 feature **不新建项目**）

- [X] T001 核对 Phase 0 的上游取证工件已落盘且与 spec 逐条一致：`specs/b9f1-command-primitive/research.md` §1 的 **D-01…D-10**（每条含**实测方法 + 真实输出**）· `specs/b9f1-command-primitive/contracts/upstream-parity.md` 的 **P-01…P-12** + **8 组**实测基线（E-01…E-08）· 全部上游引用 MUST 带**核实版本 `langgraph 1.2.11` + `路径:行号`**，凭记忆沿用的引用数 == **0**
  ⚠️ 取证环境是**用户 site-packages**（`~/.local/lib/python3.12/site-packages`）⇒ **不在**仓库 venv ⇒ 依赖声明零改动
- [X] T002 核对**依赖面零新增**：`pyproject.toml` **零改动**（`dependencies = []` · 无新增 extras）· `langgraph` **不在**任何依赖组 ⇒ 门禁 **G3 / G21 / G22 / G23** 的基线实跑结果记入 `harness/verification/B9F1/manual-verification.md` 的「实际输出」段
  ⚠️ **零新增门禁编号**（G1–G30 的连续性是不变量）⇒ 本 feature **只改既有文件**、**不新增门禁脚本**
- [X] T003 建 **11** 个测试模块骨架（空文件 + 模块 docstring 声明其对应的 SC）：`tests/runtime/test_command_goto_update.py` · `tests/runtime/test_command_merge_parity.py` · `tests/runtime/test_command_parent.py` · `tests/runtime/test_command_goto_errors.py` · `tests/runtime/test_command_goto_semantics.py` · `tests/runtime/test_command_list.py` · `tests/runtime/test_command_noop.py` · `tests/runtime/test_command_atomicity.py` · `tests/runtime/test_command_determinism.py` · `tests/runtime/test_command_purity.py` · `tests/runtime/test_command_contract.py`
  ⚠️ **必须住 `tests/runtime/`**（门禁 **G2** 禁 `tests/contracts/**` import `freegraph.*`）⇒ **G2 恒绿**
- [X] T004 建 `harness/verification/B9F1/manual-verification.md` 的**五段式骨架**（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）+ **来源覆盖表**三张（判据 **A1–A3** · **SC-001…SC-025** · **FR-001…FR-023**）+ **追认栏（只标「待发起者」· MUST NOT 代签）**
- [X] T005 [P] 建 `harness/verification/B9F1/acceptance.py` 的骨架（**单文件** · **只依赖 Python 标准库** + 被验收的 `freegraph` ⇒ **零第三方依赖** · **一条命令跑完全部闸口** · 退出码 **0 = PASS / 1 = FAIL / 2 = 环境未就绪** · **两态运行**：已安装 ⇒ 测发行产物 / 未安装 ⇒ 注入 `<repo>/src` 测源码树）
  ⚠️ **MUST NOT** 代发起者追认（追认栏只标「待发起者」）⇒ **未追认前 MUST NOT 合入**（宪法 v1.6.0）
  ⚠️ **零新增门禁编号**（验收脚本**不是**门禁 ⇒ G1–G30 不变）· 覆盖率工具缺席 ⇒ 标「◌ 环境未就绪」（skip ≠ fail）

---

## Phase 2: Foundational（阻塞性前置）

**Purpose**: `Command` 的**类型面 + 归一骨架 + 失败信号分类 + 动态边字段** —— 所有用户故事都依赖

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

> **📌 本 Phase 只出「字段 + 骨架桩 + 注解放宽 + 两条核对」**（沿用 **B7F1** 的 Q13 教训：实现逻辑分摊到各用户故事）
> ⇒ 每个故事的测试 MUST **先写 · 先失败**（此时入口抛 `NotImplementedError`）⇒
> 「每个故事独立可实现、独立测试」的承诺成立。
> ⚠️ **本 Phase MUST NOT** 引入第三种内置异常之外的新失败语义、**MUST NOT** 动 `SuperStepResult` 的四字段、**MUST NOT** 新增导出符号。

- [X] T006 在 `src/freegraph/runtime/superstep.py` 给 `SchedulerState` **增一个带缺省值的字段** `dynamic_edges: dict[str, tuple[str, ...]]`（源节点名 → 跳转目标序列 · **保序** · 缺省 MUST 用**工厂语义** `field(default_factory=dict)` ⇒ **MUST NOT** 用字面可变默认值 `= {}` —— dataclass 会抛 `ValueError: mutable default <class 'dict'>`（**实测**））
  ⚠️ **字段名 `dynamic_edges` 由 plan 冻结**（登记项 **R-3 ①** · 裁定 12 · 澄清轮第 2 次 **Q5** 发起者拍板）
  ⚠️ `SchedulerState()` 的**构造签名与名字逐字不变** ⇒ **B7F2 / B7F3 / B8F1 / B12F1 零改动**（FR-016 · SC-015）
- [X] T007 在 `src/freegraph/runtime/superstep.py` 实现**归一函数骨架** `_normalize_node_result(result)`：把三种返回值形态（`dict` / `Command` / `list[Command | dict]`）归一为**同一种内部形状** `{"writes": dict[str, tuple[Any, ...]], "gotos": tuple[str, ...]}` —— **本条只出签名 + 文档字符串 + 骨架**，函数体 `raise NotImplementedError`
  ⚠️ **`writes` MUST 是「每 key 一个**值序列**」**（**不是** `dict[str, Any]`）—— 命令列表里**两条命令写同一个 key** 时，单值形态会**后者覆盖前者** ⇒ 与 FR-004 / 裁定 15 的「**MUST NOT** 让后一条命令覆盖前一条」**直接冲突** ⇒ SC-021① 不可实现；**值序列**形态 ⇒ 与 B7F1 的 `node_writes`（节点 → 通道 key → **值序列**）**天然同构** ⇒ **合并路径零改动**、**FR / SC 零变动**（**2026-11-11 分析轮 · 发起者拍板 · Q1**）
  ⚠️ 归一是**唯一的新增概念** ⇒ 三形态归一后**只有一种内部表示** ⇒ 「未知 key 报错」「归约器语义」「批量合并」「原子性」**全部复用 B7F1 的同一条路径**（裁定 4）
  ⚠️ `Command` MUST 取自 **L1**（`freegraph.contracts.types.Command`）⇒ **MUST NOT** import 门面（L3 · ARCH-1）
- [X] T008 在 `src/freegraph/runtime/superstep.py` 实现**`goto` 形态解析骨架** `_parse_goto_targets(goto)`：**先判 `isinstance(x, str)`**（`str` 本身也是 `Sequence[str]` ⇒ 顺序判断会把它拆成字符序列 —— L1 docstring 逐字点名）· 序列 ⇒ 多目标（**保序去重**）· 空序列 ⇒ 无跳转 · 终止标记 `"__end__"` ⇒ **无跳转**（该位不产生动作）· `Command.PARENT` ⇒ 失败 · 目标不在节点表 ⇒ 失败 —— **本条只出骨架**，函数体 `raise NotImplementedError`
  ⚠️ **终止标记 MUST 以字面量判定**（L2 **MUST NOT** import 门面 ⇒ ARCH-1）⇒ 门面的 `END` 值 MUST 与该字面量**逐字相等**（可自动核对 · 裁定 6 · SC-008）
- [X] T009 在 `src/freegraph/runtime/superstep.py` 实现**失败信号分类**的骨架（**V-9…V-14** · data-model §6）：**V-9** 返回值形态非法 ⇒ 内置 `TypeError` · **V-10** 列表元素非法 ⇒ `TypeError` · **V-11** `update` 非 `dict` ⇒ `TypeError` · **V-12** `goto` 形态非法 ⇒ `TypeError` · **V-13** 目标不在节点表 / 空串 / `START` ⇒ 内置 `ValueError`（**点名目标**）· **V-14** `goto == Command.PARENT` ⇒ 内置 **`NotImplementedError`**（**点名 `__parent__` + 「子图属 v2 能力」**）
  ⚠️ **V-13 与 V-14 MUST NOT 合并** ⇒ 「**写错了**」与「**合法但未实现**」**可区分**（SC-005 · 裁定 7 · 澄清轮第 2 次 **Q2**）
  ⚠️ **零新增错误类型**：只用**内置**异常 + B5F1 既有的 `InvalidChannelUpdateError` + L1 已冻结的 `InvalidUpdateError` ⇒ L1 **18** 符号面**零改动**（登记项 **R-4**）
- [X] T010 在 `src/freegraph/runtime/superstep.py` **放宽** `NodeSpec.run` 的**返回类型注解**为「`dict[str, Any]` 或 `Command` 或 `list[Command | dict]`」（**协变放宽** · 裁定 11 / 15）⇒ `NodeSpec(subscribes, run)` 的**构造签名与名字逐字不变**
  ⚠️ 注解 MUST 与实际行为**一致**（否则下游 B7F2 / B7F3 / B12F1 的类型检查会说谎）
  ⚠️ **骨架期**（Phase 2 → US2 落地前）该形态**一律**抛 `NotImplementedError`（T007 / T008 的骨架桩）⇒ 注解**暂宽于**行为，**US2 闸口 A4 之后**两者一致（**判据只收紧、不放宽**）
- [X] T011 核对 **B7F1 契约措辞未走样**（登记项 **R-3 ②**）：`specs/b7f1-superstep-loop/contracts/superstep-contract.md` **§2.1.1** 的 **V-4** 行（「节点返回值**不是 `dict`**，含 `None` ⇒ 内置 `TypeError`」）—— **MUST NOT 改动**该文件（本 feature 只是**多接收** `Command` / `list` 两种形态 ⇒ 旧口径**仍然成立**）⇒ 只核对 + 把结论记入人工验证记录
  ⚠️ **MUST NOT** 回头改 B7F1 的契约 / spec / 追溯表（本 feature 只**放宽接受面**）
- [X] T012 核对**导出面零新增**（裁定 13）：`src/freegraph/runtime/__init__.py` 的 `__all__` **仍 20** ⇒ `tests/runtime/test_read_contract.py` 的符号数断言**不需要再动** ⇒ 兼容矩阵**零新增行**；**既有 `Command` / `NodeFunc` 两行的「措辞更新」**（**已在 plan 阶段落地** · `README.md:94` / `:101` · **零新增行** · **等价程度不变**）⇒ **本条为核对**（确认两行未被改回 / 未新增行）· 其余行 MUST **一字不动** · `THIRD_PARTY_NOTICES` **零改动**
  ⚠️ **口径收敛（2026-11-11 分析轮 · 发起者拍板 · Q2）**：FR-016 原写「API 兼容矩阵 **MUST NOT** 触碰」，与宪法原则 X 的「MUST 在**扩展 API 兼容面**的特性中**更新**清单」**字面互斥** ⇒ 收敛为「**零新增行** + 既有两行**措辞更新** MAY」⇒ **只消除字面冲突 · 不放宽判据**

**Checkpoint**: 类型面 + 骨架桩就位 ⇒ **各故事的测试此时 MUST 先失败**（`NotImplementedError`）⇒ 可进 Phase 3

---

## Phase 3: User Story 1 - 节点同时跳转与更新状态（Priority: P1）🎯 MVP

**Goal**: 节点返回 `Command` 时，**跳转**与**更新**同时生效（一个都不能少）
**Independent Test**: 一个节点返回 `Command(goto=END, update={"messages": [...]})` ⇒ 断言「状态含该更新」**且**「流程按 `goto` 终止」**同时**成立 ⇒ 用**手写图规格**驱动（不经 `StateGraph` / `compile()` / `invoke()`）

### Tests for User Story 1（MUST 先写 · MUST 先失败）

- [X] T013 [P] [US1] 在 `tests/runtime/test_command_goto_update.py` 写用例：`Command(goto=END, update={"messages": ["via-command"]})` ⇒ 最终状态**含**该更新（**按归约器合并**）**且** `goto` 之后**没有**任何节点被执行 · `Command(goto="next", update={"count": 1})` ⇒ `"next"` **被执行**（跳转生效）**且** 状态含 `count`（更新生效）—— 两条断言**同时**成立 · 「只生效其一」的现象 == **0**
  ⚠️ MUST **先失败**（Phase 2 的骨架桩抛 `NotImplementedError`）⇒ 先跑一次确认红
  ⚠️ 用例 MUST **不经由** `StateGraph` / `compile()` / `invoke()`（FR-020 · SC-016）⇒ 用**手写图规格**驱动

### Implementation for User Story 1

- [X] T014 [US1] 在 `src/freegraph/runtime/superstep.py` 把**归一**接进节点执行路径：`_execute_node` 的返回值 ⇒ 经 `_normalize_node_result` ⇒ 待写入交给**既有的** `_collect_writes` / `_merge_writes`（**MUST NOT** 另写合并路径）⇒ 写入归到**源节点**名下（`node_writes` 的按节点分组 ⇒ **B8F1** 的 fresh 读**读得到** · 裁定 16）
  ⚠️ 「三形态共用同一条合并路径」是**结构性**的（归一 ⇒ 一种内部形状）⇒ MUST NOT 出现「未知 key 只对 `dict` 报错」这类分叉
- [X] T015 [US1] 在 `src/freegraph/runtime/superstep.py` 实现**跳转登记与触发**：节点执行后 `dynamic_edges[源节点] = 跳转目标`（**整体替换** ⇒ 裁定 2 / FR-009）⇒ 触发判定枚举某节点的边触发源时，MUST 纳入「动态边表里指向它的源节点」（标识 `("e", 源节点名)` · **边空间** ⇒ 与 `("c", 通道 key)` **分离**）⇒ 目标在**下一轮**被触发（**本轮不产生新触发**）
  ⚠️ `goto` MUST 落在**边触发源**空间 ⇒ **MUST NOT** 另造第三种跳转语义（承接 **H-1** · 裁定 1）
  ⚠️ 边触发源**无「有值」门槛**（只比版本号）⇒ 目标**订阅的通道都没值也照跑**（裁定 17）
- [X] T016 [US1] 在 `src/freegraph/runtime/superstep.py` 实现**终止标记**的语义：`goto == "__end__"` ⇒ **不产生跳转**（该位不产生动作）⇒ **MUST NOT** 终止整张图（其它触发源照常推进）⇒ **终止是「收敛」的结果**（裁定 5）

**Checkpoint**: US1 可独立验收（**MVP**）⇒ 两项断言同时成立 ⇒ 进 Phase 4

---

## Phase 4: User Story 2 - `Command` 的更新走归约器 / 三形态共用同一条合并路径（Priority: P2）

**Goal**: `Command.update`（与命令列表里的每条命令）与普通 `dict` 返回**走同一条合并路径**，归约行为**逐项一致**
**Independent Test**: 同一 key 分别以「返回 `dict`」「返回 `Command(update=)`」「返回命令列表」写入 ⇒ 合并结果**逐项相等**；未知 key ⇒ 三者**都**抛 `InvalidUpdateError`

### Tests for User Story 2（MUST 先写 · MUST 先失败）

- [X] T017 [P] [US2] 在 `tests/runtime/test_command_merge_parity.py` 写用例：同一 key 分别以三种形态写入 ⇒ 合并结果**逐项相等**（含**归约型**通道的**按序拼接** —— 与 `operator.add` 的逐元素拼接相等）· 未知 key ⇒ 三者**都**抛 `InvalidUpdateError` 且 `invalid_keys` **一致** · 覆盖型通道同轮多写 ⇒ 抛 `InvalidChannelUpdateError`（B5F1 既有类型）· 「行为分叉」的现象 == **0**
  ⚠️ **MUST 先失败** ⇒ 先跑一次确认红

### Implementation for User Story 2

- [X] T018 [US2] 在 `src/freegraph/runtime/superstep.py` 实现**命令列表**的归一与合并顺序：列表元素**按列表顺序**归入同一份待写入（⇒ 归约型通道按该顺序归约 ⇒ 与上游 `_get_updates` 的 `updates.extend(...)` 顺序**逐字一致**）· 列表里**混入的 `dict`** 按其**所在位置**生效 · 列表里**每条**命令的 `goto` **各自成边**（全部目标在下一轮被触发）· **空列表 ⇒ 明确无操作**（零写入 + 零跳转 + 节点仍计入执行记录）
  ⚠️ **MUST NOT** 按 key 聚合后打乱顺序、**MUST NOT** 让「后一条命令覆盖前一条」（裁定 15 · 澄清轮第 2 次 **Q1** 发起者拍板）
  ⚠️ **「不覆盖」的可实现性依赖 T007 的形状**：归一后的 `writes` MUST 是**每 key 一个值序列** ⇒ 列表内同 key 的多个值**按列表顺序**依次入列 ⇒ 归约型通道按该顺序归约（与上游 `updates.extend(...)` **逐字一致**）⇒ **MUST NOT** 把同 key 的多个值压成一个（那会让「后一条覆盖前一条」）

**Checkpoint**: US1 与 US2 均可独立验收 ⇒ 进 Phase 5

---

## Phase 5: User Story 3 - `Command.PARENT` 被识别但不越界（Priority: P3）

**Goal**: `Command.PARENT` 在 v1（**无子图**）的��为**可判定**：**显式失败**且**点名原因**；`__parent__` 是**保留节点名**
**Independent Test**: `goto=Command.PARENT` ⇒ 断言抛 `NotImplementedError` 且消息点名 `__parent__` 与「子图属 v2 能力」；图规格含名为 `__parent__` 的节点 ⇒ 断言**构造期**抛 `ValueError`

### Tests for User Story 3（MUST 先写 · MUST 先失败）

- [X] T019 [P] [US3] 在 `tests/runtime/test_command_parent.py` 写用例：`goto=Command.PARENT` ⇒ 抛 **`NotImplementedError`**（消息点名 `__parent__` 与「子图属 v2 能力」）· 图规格含名为 `__parent__` 的节点 ⇒ **构造期**抛 **`ValueError`**（保留名）· 「静默失效」的现象 == **0** · `NotImplementedError` 与 `ValueError` **可区分**（两条用例的异常类型**不同**）
  ⚠️ **MUST 先失败** ⇒ 先跑一次确认红
  ⚠️ ⚠️ **上游对照**：上游对 `goto="__parent__"` 只是 **warning + 忽略** ⇒ freegraph **刻意分叉**（parity **P-08 / X-2**）

### Implementation for User Story 3

- [X] T020 [US3] 在 `src/freegraph/runtime/superstep.py` 实现 **V-14**：`goto == Command.PARENT` ⇒ 抛 **`NotImplementedError`**（消息 MUST 点名 `__parent__` 与「子图属 v2 能力」）⇒ **MUST NOT** 静默忽略、**MUST NOT** 抛 `ValueError`（那是「写错了」）
  ⚠️ **零新增错误类型**（内置）⇒ L1 冻结面不动（登记项 **R-4**）
- [X] T021 [US3] 在 `src/freegraph/runtime/superstep.py` 的**图规格构造期校验**里加**保留名**检查：节点名（及通道 key）MUST NOT 为 `__parent__` ⇒ 否则抛内置 **`ValueError`**（构造期 ⇒ 即刻显式失败 · MUST NOT 推迟到运行期）
  ⚠️ 目的：杜绝「用户自建一个叫 `__parent__` 的节点 ⇒ `Command.PARENT` 跳到它」的**语义歧义**（L1 docstring 逐字把该校验指派给 B7F2 / **B9F1**）

**Checkpoint**: US1–US3 均可独立验收 ⇒ 进 Phase 6

---

## Phase 6: User Story 4 - 跳转目标写错时立刻报错（Priority: P4）

**Goal**: 非法跳转目标**当场显式失败**（不静默忽略）
**Independent Test**: `goto="no-such-node"` ⇒ 断言抛 `ValueError` 且消息**点名**该目标；`goto=123` ⇒ 断言抛 `TypeError`

### Tests for User Story 4（MUST 先写 · MUST 先失败）

- [X] T022 [P] [US4] 在 `tests/runtime/test_command_goto_errors.py` 写用例：`goto` 指向**不在节点表**的名字 ⇒ 内置 **`ValueError`**（消息**点名该目标**）· `goto=""`（空串）⇒ `ValueError` · `goto="__start__"` ⇒ `ValueError` · `goto=123` / `goto=("a", 1)`（非 `str` / 序列含非 `str`）⇒ 内置 **`TypeError`** · `update` 非 `dict`（如 `Command(update=["a"])`）⇒ `TypeError` · 「静默忽略 / warning 后继续」的现象 == **0**
  ⚠️ **MUST 先失败** ⇒ 先跑一次确认红
  ⚠️ ⚠️ **上游对照**：上游对未知目标是 **warning + 忽略** ⇒ freegraph **刻意分叉**（parity **P-07 / X-1**）

### Implementation for User Story 4

- [X] T023 [US4] 在 `src/freegraph/runtime/superstep.py` 实现 **V-12 / V-13**（复用 T008 / T009 的骨架 ⇒ **MUST NOT** 另写一套解析）：目标**不在节点表** / 空串 / `START` ⇒ 内置 **`ValueError`**（点名目标）· 形态非法 ⇒ 内置 **`TypeError`**
  ⚠️ 与 B7F1 的 V-2（边的端点不在节点表 ⇒ `ValueError`）**同款**

**Checkpoint**: US1–US4 均可独立验收 ⇒ 进 Phase 7

---

## Phase 7: User Story 5 - 跳转与既有边并存时两边都不丢（Priority: P5）

**Goal**: `goto` 与静态边**叠加**（不互相取消）；`goto` 目标由源节点的**最近一次执行**决定
**Independent Test**: X 有静态边 X→Y 且返回 `Command(goto="Z")` ⇒ 断言 **Y 与 Z** 都被执行；X 再次执行且不给 `goto` ⇒ 断言 **Z 不再**被触发

### Tests for User Story 5（MUST 先写 · MUST 先失败）

- [X] T024 [P] [US5] 在 `tests/runtime/test_command_goto_semantics.py` 写用例：X 有静态边 X→Y 且返回 `Command(goto="Z")` ⇒ **Y 与 Z** 在**下一轮****都**被执行（叠加 · 同一对 (源, 目标) 在一轮内被触发**恰好 1** 次）· X 再次执行且**不**返回 `goto` ⇒ 旧目标**不再**被触发（残留触发 == **0**）· 目标**订阅的通道都没值** ⇒ 目标**照跑**（入参为空 `dict`）· 目标入参 == `read_channels(子映射)` 的结果（**逐字相等** · 子映射按**通道映射顺序**构造）· 源节点 `goto` + `update` ⇒ 目标**读得到**这次 `update` 的内容 · 多目标 `goto` ⇒ **全部**目标在下一轮被执行 · `goto` 目标在**同一轮**内被执行的现象 == **0**
  ⚠️ **MUST 先失败** ⇒ 先跑一次确认红
  ⚠️ **上游对照**：上游实测**同款**（叠加 + 目标照跑 + 读得到本次 update）⇒ research **D-02 / D-09**

### Implementation for User Story 5

- [X] T025 [US5] 在 `src/freegraph/runtime/superstep.py` 实现**叠加**与**生命周期**：静态边与动态边在触发源枚举中**并存**（MUST NOT 互相取消）· `dynamic_edges[X]` 在 X **每次执行**时**整体替换**（含空集）⇒ 旧的 `goto` 目标被清空（裁定 2 / FR-009）
  ⚠️ 目标节点的**触发与入参** MUST 与静态边**同款**（无「有值」门槛 + 正常稀疏读）

**Checkpoint**: US1–US5 均可独立验收 ⇒ 进 Phase 8

---

## Phase 8: User Story 6 - 空命令是「无操作」（Priority: P6）

**Goal**: 槽位为空 / 空列表 ⇒ **明确无操作**（零写入 + 零跳转 + 节点仍计入执行记录）；`resume` **被接受但无效果**
**Independent Test**: 返回「`goto` 与 `update` 均为空」的 `Command` ⇒ 断言零写入 + 零跳转 + 节点计入执行记录

### Tests for User Story 6（MUST 先写 · MUST 先失败）

- [X] T026 [P] [US6] 在 `tests/runtime/test_command_noop.py` 写用例：`Command(update={})` ⇒ 状态**无任何新增写入** + 节点**计入执行记录** · `Command(goto=())` ⇒ **无跳转** · `Command(goto=(), update={})` ⇒ 零写入 + 零跳转 · **空列表** `[]` ⇒ 零写入 + 零跳转 + 节点仍计入执行记录 · `Command(resume="x")` ⇒ **被接受**（不抛错）+ 产生写入 **0** 次 + 产生跳转 **0** 次 · 「因空命令而报错」的现象 == **0**
  ⚠️ **MUST 先失败** ⇒ 先跑一次确认红
  ⚠️ **L1 契约层**逐字：「某位**显式给了但内容为空**（`update={}` / `goto=()`）亦合法，语义为「该位不产生动作**」⇒ 运行期 MUST 照此执行 ⇒ MUST NOT 造成「契约层说合法、运行期抛错」的**分层分叉**（裁定 10）
  ⚠️ `Command()`（三槽全空）⇒ **L1 构造期**即抛 `FreegraphError` ⇒ 运行期**不可达** ⇒ 用例 MUST NOT 断言运行期行为

### Implementation for User Story 6

- [X] T027 [US6] 在 `src/freegraph/runtime/superstep.py` 实现**空操作**的归一：槽位为空（`None` / `{}` / `()`）与**空列表** ⇒ 待写入为空 + 跳转目标为空 ⇒ **不产生写入**、**不产生跳转**（节点**仍**计入执行记录、其**执行版本**照常 +1）· `Command(resume=...)` ⇒ **被接受**且**不产生任何效果**（不写入 · 不跳转 · 不改变流程）
  ⚠️ `resume` 的**恢复效果**归 **B10F1**（下游承接 **D-2**）⇒ 本 feature **MUST NOT** 实现

**Checkpoint**: 六个故事**全部**可独立验收 ⇒ 进 Phase 9

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 原子性 · 确定性 · 纯净性 · 契约守卫 · 覆盖率 · 门禁 · 证据 · 接线复核 · 追认

- [X] T028 [P] 在 `tests/runtime/test_command_atomicity.py` 写用例：`Command.update` 引发的四类错误（未知 key · 覆盖型多写 · 归约器抛错 · 与同轮其它节点的冲突）⇒ 出错后**全部**通道的值与**本轮开始前**逐字相等 + 通道的**写入版本未推进** + 「一部分通道已更新、一部分没更新」的用例数 == **0**
  ⚠️ **MUST NOT** 改 B7F1 的回滚机制（快照 + 逐通道回滚 + 版本延后推进）⇒ 本 feature 只**复用**它
- [X] T029 [P] 在 `tests/runtime/test_command_determinism.py` 写用例：同一份规格重复执行 **≥ 3** 次 ⇒ 合并后状态与执行序列**逐项相等**（差异 == **0**）· 两次**独立**运行（各自新建调度状态）⇒ **互不影响**（比率 == **100%**）· 多轮入口**省略**调度状态 ⇒ 内部自洽（**不**继承此前任何调用的消费记录）
- [X] T030 [P] 在 `tests/runtime/test_command_purity.py` 写**子进程**断言（复用 `tests/runtime/conftest.py` 的 `run_in_subprocess` 夹具 · **既有 conftest 零改动**）：内核路径 `src/freegraph/**` 对 `langgraph` / `langchain*` / `langsmith` 的导入次数 == **0** · 环境变量读取 == **0** 次 · 出站 == **0** 次 · 导入无副作用；**AST 级**静态扫描用例中 `freegraph.graph` / `freegraph._stategraph` 的**导入**次数 == **0**（⚠️ **AST 级**扫描 ⇒ 排除字符串 / 注释 / docstring ⇒ 不被用例自身陈述不变量的**文字**误伤）· `SuperStepResult` 的字段数 == **4**（**MUST NOT** 为记录跳转而扩字段 · 裁定 18）· **静态断言** L1 的 `StateSnapshot.next` 字段**存在**且其语义与上游 `types.py:688-689` **逐字同款**（⚠️ **运行期**产出快照归 **B7F3 / B14F1** ⇒ 本 feature 只断言**字段面**）· `freegraph.runtime.__all__` 的符号数 == **20** · **门面 `END` 的值 == L2 终止标记字面量 `"__end__"`**（**逐字相等** · SC-008 第三子句）· **`NodeSpec.run` 的构造签名与名字**与 B7F1 契约 §1 **逐字相同**（只允许返回类型**注解**放宽）· **`SchedulerState()` 的构造签名**与 B7F1 契约 §1 **逐字相同**（SC-015 后两句）
- [X] T031 [P] 在 `tests/runtime/test_command_contract.py` 写**契约守卫**：**解析** `specs/b9f1-command-primitive/contracts/command-contract.md` §9 的 **I-1…I-14** 并**逐条**断言（⚠️ **MUST NOT** 只测行为而不校验契约文本 ⇒ 否则「契约与实现**同源即自证**」）⇒ 契约若与 spec 冲突 ⇒ 该守卫**失败**（提示「以 spec 为准」）
- [X] T032 跑**覆盖率取证**（**差分口径** · `git diff -U0` 取 `src/freegraph/runtime/superstep.py` 的新增行号 ∩ `coverage json` 的 `executed_lines` / `executed_branches`；⚠️ 文件级 `coverage report` **无法区分**既有行与新增行 ⇒ **仅作参考**）⇒ **行覆盖 == 100%** 且 **分支覆盖 == 100%**
  ⚠️ 「新增代码」的范围 = `src/freegraph/runtime/superstep.py` 中本 feature **新增 / 修改**的代码（**测试代码本身不计入**）⇒ 差分口径沿用 **B5F1** 已确立的做法
  ⚠️ 覆盖率工具 MUST **NOT** 进依赖声明（v1.0 依赖面为零）⇒ 开发期临时安装
- [X] T033 跑**全量门禁**核对（`pytest tests/ -q` + `python harness/scripts/gates/gate_G25_import_graph.py --registry specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` + `gate_G30_attribution.py` + `gate_G24_config_layer.py` + `gate_G26_network_static.py`）：门禁编号总数仍 == **30** 且**连续无跳号** · L1 **18** / 门面 **7** 符号面 / 兼容矩阵 / `THIRD_PARTY_NOTICES` 的差异 == **0** · L2 → L3/L4/L5 的依赖边数 == **0** · **越界实现数 == 0**（⚠️ **AST 标识符扫描** `src/freegraph/runtime/` ⇒ MUST NOT 出现 `invoke` / `stream` / `compile` / `StateGraph` / `Send` / `interrupt` / `async` / checkpoint 相关标识符 —— **排除**字符串 / 注释 / docstring）· 新源文件的**署名头覆盖率 == 100%**
  ⚠️ **层注册表零改动**（`runtime/` 已是**目录条目** ⇒ MUST NOT 为新模块单独立条目）
- [X] T034 复核**上游引用纪律**：spec / plan / 契约 / research 中的每条上游引用 MUST 带**核实版本**（`langgraph 1.2.11`）+ **`路径:行号`**；凭记忆沿用的引用数 == **0** ⇒ 逐条对照 `specs/b9f1-command-primitive/research.md` §1 的 **D-01…D-10** 与 `contracts/upstream-parity.md` 的 **P-01…P-12**
- [X] T035 **下游承接 D-1 / D-3 的接线复核**（登记项 **R-5** · 宪法 **v1.8.0** · **只复核 · MUST NOT 重写**）：核对 `harness/features/B12F1_并发执行与错误传播.md` **§2** 与 `harness/features/B19F1_TraceSink与current_span.md` **§2** 中已追加的「**B9F1 → B12F1**」「**B9F1 → B19F1**」两条承接条款措辞与 FR-004 / FR-008 / FR-022 / 裁定 19 **一致**；并核对 `harness/features/B10F1_interrupt与resume.md` **§7** 的「`goto`/`update` 语义在 **B9F1**」仍在位（**D-2** · 既有）⇒ **MUST NOT** 改动这三个文件的**其余**内容
  ⚠️ **MUST NOT** 越界实现 B12F1 的并发合并 / B19F1 的触发源暴露 / B10F1 的恢复效果
  ⚠️ 核对口径 = 「措辞**不得弱于** spec」⇒ 判据以 **spec 裁定**为准（宪法 v1.8.0）
- [X] T036 回填 `harness/verification/B9F1/manual-verification.md`：**五段式**（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）+ **来源覆盖表**三张（判据 **A1–A3** · **SC-001…SC-025** · **FR-001…FR-023** · 覆盖率 == **100%** · 无来源项数 == **0**）—— ⚠️ **未实跑的项 MUST 显式记入「遗留问题」**（MUST NOT 伪造输出）
- [X] T037 执行 `specs/b9f1-command-primitive/quickstart.md` 的**验收闸口 V1–V12**（§1 ~ §12 的**可照抄命令**）⇒ 每道闸口的**真实输出** MUST 记入 `harness/verification/B9F1/manual-verification.md` 的「实际输出」段（MUST NOT 伪造输出）
- [X] T038 完成 `harness/verification/B9F1/acceptance.py`（**一条命令跑完全部闸口 V1–V12** + 覆盖率取证 + **10 条门禁**的实跑结果）⇒ **不必**手工逐节执行 `quickstart.md` 的 15 节手册
  ⚠️ **退出码 MUST 逐条唯一**（`0` = PASS · `1` = FAIL · `2` = **环境未就绪** ⇒ 与「判失败」**区分**）· **MUST NOT** 代发起者追认（追认栏只标「待发起者」）· **零新增门禁编号**

- [X] T039 **发起者追认**（登记项 **R-1 / R-2 / R-3 / R-4 / R-5 / R-7 / R-8 / R-9** · 宪法 **v1.6.0 / v1.8.0** · **阻断合入**）：把**追认文字 + 发起者确认 + 日期**落在 `harness/verification/B9F1/manual-verification.md` —— ⚠️ **MUST 由发起者本人作出**（**MUST NOT** 由实现者代签）· ⚠️ **未追认前 MUST NOT 合入** · MUST **NOT** 改宪法正文 · MUST **NOT** 写一条永久红的 CI · 四条红线（依赖 / 许可证 / 商标 / 零出站）**照常执行**
  ⚠️ **追认清单 MUST 含八项**：① **R-1**（门禁 3 / 4 / 5 的偏离登记）· ② **R-2**（**裁定 1 / 2 / 4 / 6 / 8 / 10 / 11 / 13 / 14** 由 spec 阶段 agent 拍板 ⇒ 跨 feature 接口**缺发起者背书**）· ③ **R-3**（两处**跨 feature 冻结面扩展**：`SchedulerState` 增字段 + V-4 接受面放宽）· ④ **R-4**（**第三种内置异常** `NotImplementedError`）· ⑤ **R-5**（下游承接 **D-1 / D-3** 的接线复核）· ⑥ **R-7**（**破 L1 冻结面** —— `NodeFunc.__call__` 增补「命令列表」· **发起者特批** · 含回溯修订清单）· ⑦ **R-8**（**已落地 feature 的验收闭环** —— 三个验收脚本的复跑结论 + **发起者签字**；**含子项 ⑤**：B7F1 的两处「内核零越界标识符」断言因本 feature 落地而**过期** ⇒ 已按「**补齐过期**」修订（**仅移除** `Command` 一项 · 其余**逐字保留**）⇒ **B7F1 的验收脚本内容已变** ⇒ MUST 由发起者**复跑并签字**）· ⑧ **R-9**（**破冻结面对 19 个后续 feature 的影响面** —— **7** 个已接线 · **12** 个零影响）⇒ 追认文字 MUST **逐项**点名
  ⚠️ **裁定 3 / 5 / 7 / 9 / 12 / 15 / 16 / 17 / 18 / 19** 由**澄清轮的发起者本人**拍板 ⇒ **不在**追认清单内；**R-6**（分析轮的三处收敛）同属**发起者本人拍板** ⇒ **不在**追认清单内

- [X] T040 登记 `specs/b9f1-command-primitive/research.md` §4 的**遗留取证动作**（换上游版本时 MUST 重做：重新核实全部行号 + 重跑 8 组实测 + 把实现放到 CI 最低档 **3.11** 上跑）⇒ 记入人工验证记录的「遗留问题」段（MUST NOT 伪造成已闭合）
- [X] T043 [P] **下游接线的复核**（登记项 **R-9** · 宪法 **v1.8.0** · **只复核 · MUST NOT 重写**）：核对 `harness/features/` 下**七个**提示词初稿的承接条款与 spec 的**下游承接 D-4…D-9 / D-1 扩充****逐条一致** —— **B6F1**（节点函数的返回形态）· **B8F1**（`node_writes` 的归属口径）· **B10F1**（`Command` 两条路径的边界）· **B11F1**（`Send` 的落点与「命令列表」的关系）· **B12F1**（D-1 的「命令列表的并发维度」扩充）· **B22F1**（`goto` 序列 ⇒ 多条边 · 非泛型 ⇒ 来源自设计）· **B24F1**（兼容矩阵的定稿口径）⇒ **MUST NOT** 改动这些文件的**其余**内容；并核对**其余 12 个**后续 feature **零影响**（不碰节点返回值形态 / `node_writes` / `Command` 的类型面 / 兼容矩阵）⇒ **MUST NOT** 无谓接线
  ⚠️ **落地状态**：七条**已在 plan 阶段落地**（**只接线 · 逐条最小改动**）⇒ 本条为**复核**任务。
- [X] T041 [P] **破 L1 冻结面的返工**（登记项 **R-7** · **裁定 21** · **发起者特批**）：
  ① 在 `src/freegraph/contracts/protocols.py` 把 `NodeFunc.__call__` 的返回联合**放宽**为
  `StateDict | Command | list[Command | StateDict] | None`（**含注解 + docstring 的表格行与「返回」段**）
  ⇒ **L1 的符号集合与数量不变**（**18** 个 ⇒ **G7 恒绿**）· **MUST NOT** 改动其余任何 L1 符号；
  ② **回溯修订** `specs/b2f1-contracts-protocols/contracts/public-api.md`（**5** 处：符号清单注释 /
  逐符号表 / 上游对照行（补「上游 `ToolNode` **自身即返回命令列表**」）/ C5 行 / C6 行）·
  `specs/b2f1-contracts-protocols/spec.md`（FR-001 的冻结口径 + **理由留痕**）·
  `specs/b7f1-superstep-loop/contracts/superstep-contract.md`（**V-4** 行 · 改为「不在三形态之内」⇒
  **与 B9F1 不再矛盾**）· `specs/b7f1-superstep-loop/spec.md`（**FR-009** 措辞）
  ⇒ **MUST NOT** 改动其余任何 L1 符号 / B7F1 契约的其余部分 ⇒ **MUST NOT** 改 Q8 / 立项书 §5.3
  （**C5 / C6 的条目本身一字不动**）；
  ③ **登记**（不修）：L1 的协议允许 `None`（= 不写状态 · **忠实镜像上游**）而 **B7F1 的运行时 V-4 拒绝它**
  ⇒ 登记为**遗留** ⇒ **MUST NOT** 顺带放宽 B7F1 的 V-4 判据（改它 = 放宽判据 ⇒ 违宪）。
  ⚠️ **为什么必须改**：L1 的三形态**从未讨论**「一个节点发出多条命令」（B1F1 / B2F1 / Q8 **零命中**）⇒
  只改运行时 ⇒ **协议与运行时分歧**（用 `NodeFunc` 标注的节点**类型层**无法表达列表返回）⇒
  且上游 `ToolNode` **自身即返回命令列表** ⇒ **协议 MUST 与运行时一致**（裁定 21）。
  ⚠️ **判据只收紧、不放宽**：本条**只**改**注解与文档**（**零新增符号** ⇒ G7 / G8 恒绿）⇒
  **FR / SC 的编号与总数零变动**（FR 23 · SC 25）。
- [X] T042 [P] **跨 feature 返工的「执行记录 + 接线 + 验收」闭环**（登记项 **R-8** · 宪法 **v1.8.0**）：
  ① 在 `specs/b2f1-contracts-protocols/tasks.md` 与 `specs/b2f1-contracts-protocols/research.md` 追加
  **回溯修订注记**（**只加注记 · 不改历史执行记录**）⇒ 指向 B9F1 的 **裁定 21**；
  ② 在 `specs/b7f1-superstep-loop/plan.md` 与 `specs/b7f1-superstep-loop/tasks.md` 追加**回溯修订注记**
  （V-4 / FR-009 的口径已被上游改写；**`None` 的显式失败口径未放宽**）；
  ③ 在 `harness/features/B2F1_四类协议与图数据类.md` 与
  `harness/features/B7F1_任务准备与super-step循环.md` 各**追加一条承接条款**
  （宪法 v1.8.0 的**接线动作** · **只接线 · 逐条最小改动** · MUST NOT 改动其余内容）；
  ④ **补齐过期**（已在 plan 阶段落地）：`harness/verification/B2F1/acceptance.py` 的 **SC021 断言**
  「兼容矩阵逐符号覆盖公开符号面（**18** 个）」**已过期**（B2F2 交付时矩阵**合法地增补了门面的
  **5** 个符号 ⇒ 矩阵共 **23** 行 ⇒ 该脚本未同步）⇒ **与本次返工无关**（矩阵的**符号集合**返工前后
  **完全相同**）⇒ 期望值**补为**「契约层 18 ∪ 门面新增 5 = **23**」⇒ 断言**恢复为真**、**非放宽**
  （与 B7F1 的 R-3「事实性订正」同款）⇒ **B2F1 124/124 PASS**；
  ⑤ **人工验收记录的复跑与签字**：L1 的公开签名已变 ⇒ `harness/verification/B2F1/manual-verification.md`
  与 `harness/verification/B2F2/manual-verification.md` 中**记载旧签名**的部分**已失效** ⇒
  **MUST 由发起者复跑** `harness/verification/<feature>/acceptance.py` 并**签字**（原则 V ·
  **MUST NOT** 由实现者代签）⇒ **本 feature 的 A10 追认 MUST 把此项列入**。
  ⚠️ **机械层已复跑并留证**：**B2F1 124/124 PASS** · **B2F2 76/76 PASS** · **B7F1 104/104 PASS**
  ⇒ 结论记录入人工验证记录（**签字仍由发起者作出**）。
  ✅ **已闭合（2026-11-11）**：发起者**亲自复跑**三个验收脚本并**全部 PASS** ⇒ 三份记录的「**补充验收**」段已**如实转录**输出并标注「**发起者验收**」（**实施者未代签**）⇒ **T042 整体完成**。

**Checkpoint**: 全部故事完成 · 门禁全绿 · 覆盖率 == 100% · 人工记录齐全 · **追认已落** ⇒ 可合入

---

## Dependencies & Execution Order

### 执行闸口（Phase 闸口 · 每道 MUST 全绿才进下一 Phase）

| 闸口 | 内容 | 对应任务 |
|---|---|---|
| **A1** | Setup 完成（取证工件核对 · 依赖面基线 · 测试/验收工件骨架） | T001 / T002 / T003 / T004 / T005 |
| **A2** | Foundational 完成（**字段 + 骨架桩 + 注解放宽 + 两条核对** · **不含实现逻辑**） | T006 / T007 / T008 / T009 / T010 / T011 / T012 |
| **A3** | **US1 完成**（跳转 + 更新**同时生效** · **MVP** · 独立可验收） | T013 / T014 / T015 / T016 |
| **A4** | **US2 完成**（三形态**共用同一条合并路径** + 命令列表） | T017 / T018 |
| **A5** | **US3 完成**（`Command.PARENT` 可判定 + 保留名） | T019 / T020 / T021 |
| **A6** | **US4 完成**（非法目标 ⇒ 显式失败） | T022 / T023 |
| **A7** | **US5 完成**（叠加 + 生命周期 + 触发与入参） | T024 / T025 |
| **A8** | **US6 完成**（空操作 + `resume` 只被接受） | T026 / T027 |
| **A9** | Polish 完成（原子性 / 确定性 / 纯净性 / 守卫 / 覆盖率 / 门禁 / 证据 / 接线复核 / 一键验收入口 / **破 L1 冻结面的返工** / **跨 feature 返工闭环** / **下游接线的复核**） | T028 ~ T038 / T040 / **T041 / T042 / T043** |
| **A10** | **发起者追认已落**（**R-1…R-5**）⇒ **可合入** | T039 |

### Phase Dependencies

- **Setup（Phase 1）**：无依赖 —— 可立即开始
- **Foundational（Phase 2）**：依赖 Setup —— **阻断**全部用户故事
- **用户故事（Phase 3–8）**：全部依赖 Foundational 完成 ⇒ 之后可**并行**推进（或按 P1 → P6 顺序）
- **Polish（Phase 9）**：依赖全部目标故事完成
- **追认（A10）**：依赖 Polish 完成 ⇒ **合入前置**

### User Story Dependencies

- **US1（P1）**：Foundational 之后即可开始 —— **不依赖**其它故事 ⇒ **MVP**
- **US2（P2）**：Foundational 之后即可开始 —— 依赖 US1 的**归一**已接线（同一实现单元）但**判据独立**
- **US3（P3）**：Foundational 之后即可开始 —— 只依赖 T009 的失败信号骨架
- **US4（P4）**：Foundational 之后即可开始 —— 只依赖 T008 / T009 的骨架
- **US5（P5）**：依赖 US1 的跳转登记（同一实现单元）但**判据独立**
- **US6（P6）**：Foundational 之后即可开始 —— 只依赖 T007 的归一骨架

### Within Each User Story

- **测试 MUST 先写 · MUST 先失败**（Phase 2 的骨架桩抛 `NotImplementedError` ⇒ 先红后绿）
- 归一骨架 → 形态解析 → 失败信号 ⇒ 接线 → 行为断言
- 一个故事完成后再进下一个优先级

### Parallel Opportunities

- Phase 1 的 **T005**（验收脚本骨架）可与 T003（测试骨架）并行
- Phase 2 的 **T011 / T012**（两条**核对**）互不依赖 ⇒ 可并行
- **六个故事的「测试起草」层可并行**（不同文件：T013 / T017 / T019 / T022 / T024 / T026）
- Phase 9 的 **T028 / T029 / T030 / T031**（四个不同测试文件）可并行
- ⚠️ **同一文件内的任务 MUST 串行**（`src/freegraph/runtime/superstep.py` 的实现任务 **T014 / T015 / T016 / T018 / T020 / T021 / T023 / T025 / T027** ⇒ 逐条追加，**MUST NOT** 并行改同一文件）

---

## Parallel Example: User Story 1

```bash
# 测试起草层（先红）
Task: "T013 [US1] 在 tests/runtime/test_command_goto_update.py 写用例：跳转 + 更新同时生效"

# 实现 MUST 等测试先红（同一文件 ⇒ 串行追加）
Task: "T014 [US1] 在 src/freegraph/runtime/superstep.py 把归一接进节点执行路径"
Task: "T015 [US1] 在 src/freegraph/runtime/superstep.py 实现跳转登记与触发"
Task: "T016 [US1] 在 src/freegraph/runtime/superstep.py 实现终止标记的语义"
```

---

## Parallel Example: User Story 5 与 User Story 2（判据独立 · 文件不同）

```bash
# 两条故事可由不同人同时推进（**测试文件不同** ⇒ 可并行）
Task: "T024 [US5] 在 tests/runtime/test_command_goto_semantics.py 写用例：叠加 + 生命周期 + 触发与入参"
Task: "T017 [US2] 在 tests/runtime/test_command_merge_parity.py 写用例：三形态逐项一致"
# ⚠️ 两者的**实现**都落在 src/freegraph/runtime/superstep.py ⇒ 实现层 MUST 串行合并
```

---

## Implementation Strategy

### MVP First（仅 User Story 1）

1. Phase 1 Setup（取证核对 + 骨架）
2. Phase 2 Foundational（字段 + 骨架桩 ⇒ 测试先红）
3. Phase 3 User Story 1（跳转 + 更新同时生效）
4. **停下来验证**：US1 独立验收（**A1 / A2** 两条断言同时成立）
5. 演示 / 合入（**追认未落 ⇒ 不可合入**）

### Incremental Delivery

1. Setup + Foundational → 地基就位
2. **US1** → 独立验收 → 演示（MVP）
3. **US2**（合并路径的逐项一致）→ 独立验收 → 演示
4. **US3 / US4**（失败信号的可判定性）→ 独立验收
5. **US5 / US6**（叠加 / 空操作）→ 独立验收
6. Polish（原子性 / 确定性 / 纯净性 / 守卫 / 覆盖率 / 门禁 / 证据 / 接线 / **追认**）→ 合入

### Parallel Team Strategy

1. 团队共做 Setup + Foundational
2. 之后：开发者 A 做 US1（**MVP**）· B 做 US2 / US5 的**测试起草**· C 做 US3 / US4 的**测试起草**
3. ⚠️ **实现层**（`src/freegraph/runtime/superstep.py`）**必须串行合并** ⇒ 同一时刻只允许一人改该文件

---

## Notes

- **[P]** = 不同文件 · 无未完成依赖；⚠️ **同一文件内的任务 MUST 串行**
- **[Story]** 标签映射到 spec 的用户故事（US1…US6）⇒ 追溯见文末
- **测试 MUST 先写 · 先失败**（Phase 2 只出骨架桩 ⇒ 入口抛 `NotImplementedError`）
- 每个故事完成后**停下来独立验证**
- 提交粒度 = 一个任务或一组逻辑相关任务
- 避免：含糊的任务、同一文件的并行冲突、破坏故事独立性的跨故事依赖

---

## 附录 · 任务 ↔ spec 追溯表

> **反向覆盖**：**FR 23/23 · SC 25/25** —— 每个 FR 与每个 SC **至少**被一条任务映射；
> **反向亦然**：每条任务携带的义务 MUST 挂上**至少一条 FR**（⇒ 追溯表**双向**齐全 · 宪法原则 VI）。
> ⚠️ **编号连续无跳号**（T001…T040）⇒ **ID ↔ 义务的权威映射 = 本表**（每个 T-ID 恰好一条义务）。

| T-ID | FR | SC | 义务摘要 |
|---|---|---|---|
| T001 | FR-017 · FR-021 | SC-020 | Phase 0 取证工件核对（**D-01…D-10** · **P-01…P-12** · 8 组实测基线） |
| T002 | FR-014 · FR-016 | SC-014 · SC-015 | **依赖面零新增**核对（`pyproject.toml` 零改动 · 门禁基线） |
| T003 | FR-020 | SC-016 | **10** 个测试模块骨架（住 `tests/runtime/` · G2 恒绿） |
| T004 | FR-018 | SC-017 | 人工验证记录骨架（五段式 + 来源覆盖表 + 追认栏「待发起者」） |
| T005 | FR-018 | SC-017 | **一键验收入口**骨架（`acceptance.py` · 退出码 0/1/2 · 两态运行） |
| T006 | FR-002 · FR-013 · FR-016 | SC-015 · SC-019 | `SchedulerState.dynamic_edges`（**字段名冻结** · 工厂语义 · 构造签名不变） |
| T007 | FR-001 · FR-004 | SC-003 | **归一函数骨架**（三形态 → 一种内部形状） |
| T008 | FR-005 · FR-007 | SC-008 · SC-009 | **`goto` 形态解析骨架**（先判 `str` · 多目标 · 空序列 · 终止标记 · PARENT） |
| T009 | FR-001 · FR-005 · FR-007 · FR-010 | SC-005 · SC-009 | **失败信号分类**（**V-9…V-14** · `TypeError` / `ValueError` / `NotImplementedError`） |
| T010 | FR-001 | SC-003 · SC-015 | `NodeSpec.run` 返回类型注解放宽（**协变** · 构造签名不变） |
| T011 | FR-013 · FR-016 | SC-015 | **B7F1 契约措辞未走样**核对（**R-3 ②** · MUST NOT 改动该文件） |
| T012 | FR-016 | SC-015 | **导出面零新增**核对（`__all__` 仍 20 · 兼容矩阵**零新增行** + 既有两行**措辞已更新**（plan 阶段落地）） |
| T013 | FR-001 · FR-002 · FR-003 | SC-001 · SC-002 | US1：跳转 + 更新**同时生效**的用例（**先红**） |
| T014 | FR-003 · FR-004 | SC-002 · SC-022 | US1：归一接线 + 写入归**源节点**（共用 B7F1 的合并路径） |
| T015 | FR-002 · FR-009 | SC-001 · SC-007 | US1：跳转登记 + 下一轮触发（**边触发源空间** · 整体替换） |
| T016 | FR-007 | SC-008 | US1：终止标记 **不跳转、不终止** |
| T017 | FR-004 · FR-010 | SC-003 · SC-004 · SC-023 | US2：三形态**逐项一致** + 未知 key + 覆盖型冲突（**先红**） |
| T018 | FR-001 · FR-004 | SC-003 · SC-021 | US2：**命令列表**（按列表顺序合并 · 每条 `goto` 各自成边 · 空列表无操作） |
| T019 | FR-005 | SC-005 | US3：`Command.PARENT` + 保留名的用例（**先红** · 可区分性） |
| T020 | FR-005 | SC-005 | US3：**V-14** `NotImplementedError`（点名「子图属 v2 能力」） |
| T021 | FR-005 | SC-005 | US3：**`__parent__` 保留名**的构造期校验（`ValueError`） |
| T022 | FR-007 · FR-010 | SC-009 | US4：非法目标 / 非法形态的用例（**先红** · 点名目标） |
| T023 | FR-007 | SC-009 | US4：**V-12 / V-13** 的实现（复用 T008 / T009 的骨架） |
| T024 | FR-002 · FR-007 · FR-008 · FR-009 | SC-007 · SC-010 · SC-011 · SC-023 | US5：叠加 + 生命周期 + 触发门槛 + 入参 + 多目标（**先红**） |
| T025 | FR-002 · FR-008 · FR-009 | SC-007 · SC-010 | US5：**叠加** + **整体替换**的生命周期实现 |
| T026 | FR-006 · FR-011 | SC-006 · SC-012 | US6：空操作 + `resume` 只被接受（**先红**） |
| T027 | FR-006 · FR-011 | SC-006 · SC-012 | US6：**空操作**的归一实现（零写入 + 零跳转 + 计入执行记录） |
| T028 | FR-012 | SC-013 | **原子性**覆盖 `Command` 路径（整轮不合并 · 版本不推进） |
| T029 | FR-013 | SC-019 | **确定性** + 调度状态**不串扰** |
| T030 | FR-014 · FR-016 · FR-022 | SC-014 · SC-015 · SC-016 · SC-024 | **纯净性**（子进程）· **四字段**不动 · `StateSnapshot.next` 字段面 · 导出面 20 · **门面 `END` == L2 字面量** · **`NodeSpec.run` / `SchedulerState()` 构造签名逐字不变** |
| T031 | FR-020 | SC-016 | **契约守卫**（解析契约 §9 的 **I-1…I-14**） |
| T032 | FR-020 | SC-016 | **覆盖率取证**（差分口径 · 行 / 分支 == 100%） |
| T033 | FR-015 · FR-022 · FR-023 | SC-015 | **全量门禁**核对 + 越界 **AST 标识符扫描** + 门禁编号连续性 |
| T034 | FR-017 · FR-021 | SC-020 | **上游引用纪律**复核（版本 + `路径:行号`） |
| T035 | FR-004 · FR-008 · FR-011 · FR-022 | SC-025 | **下游承接 D-1 / D-3 接线复核**（**R-5** · 只复核） |
| T036 | FR-018 | SC-017 | **人工验证记录**回填（五段式 + 来源覆盖表 == 100%） |
| T037 | FR-018 | SC-017 | 执行 **quickstart 闸口 V1–V12** ⇒ 真实输出入记录 |
| T038 | FR-018 | SC-017 | **一键验收入口**完成（一条命令跑完全部闸口 + 覆盖率 + 10 条门禁） |
| T043 | FR-002 · FR-004 · FR-011 · FR-016 | SC-001 · SC-012 · SC-015 · SC-022 | **下游接线的复核**（**七个**后续 feature 的提示词初稿 · **只复核 · MUST NOT 重写** · 其余 12 个**零影响**） |
| T042 | FR-016 · FR-017 | SC-017 · SC-020 | **跨 feature 返工的闭环**（B2F1 / B7F1 的执行记录注记 + 提示词初稿**接线** + 验收脚本遗留登记 + **人工验收复跑由发起者签字**） |
| T041 | FR-001 · FR-016 | SC-015 | **破 L1 冻结面的返工**（`NodeFunc.__call__` 增补「命令列表」· **符号集合与数量不变** ⇒ G7 恒绿 · 回溯修订 B2F1 / B7F1 文档） |
| T039 | FR-001 · FR-002 · FR-005 · FR-007 · FR-008 · FR-011 · FR-013 · FR-016 · FR-019 · FR-022 | SC-005 · SC-015 · SC-018 · SC-025 | **发起者追认**（**R-1…R-5 / R-7** · **阻断合入**） |
| T040 | FR-017 | SC-020 | research §4 的**遗留取证动作**登记（换版本重核 · 3.11 复核） |
