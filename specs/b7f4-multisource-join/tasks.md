---
description: "Task list for B7F4 · 多源汇合边（AND / 屏障）"
---

# Tasks: B7F4 · 多源汇合边（AND / 屏障）

**Input**: Design documents from `/specs/b7f4-multisource-join/`
**Prerequisites**: plan.md（required）· spec.md（required · 用户故事）· research.md · data-model.md ·
contracts/（`superstep-multisource-contract.md` + `upstream-parity.md`）· quickstart.md

**Tests**: **包含**测试任务 —— spec FR-005 / SC-004 / SC-011 要求「**差分可判定**」且
「**屏障语义 MUST 有自动化装置证明**」⇒ **MUST 先写 · MUST 先失败**（Phase 2 只出骨架 ⇒
多源边在运行期**仍被拒** ⇒ US1/US2/US3 的用例**必然失败** ⇒ 逐故事转绿）。

**Organization**: 按用户故事分组（**3** 个 · P1–P3）⇒ 每个故事可**独立实现、独立测试**；
另设 **Phase 6「回溯修订与追认」**（**破冻结面的代价** ⇒ **阻断合入**）与 **Phase 7「Polish」**。

> ⚠️ **本 feature 破 B7F1 的冻结面**（**发起者 2026-11-12 已同意**）⇒ ⇒
> **Phase 6 MUST 全绿 + 追认 MUST 落盘** ⇒ **未追认前 MUST NOT 合入**（宪法 v1.8.0「破冻结面的三条」）。
> ⚠️ **追认打包**（**8 项 · 1 次** · 澄清轮 **C-Q13** · **零新增登记项**）：**PR-1**（回溯修订 **R-1…R-10**）· **PR-2**（**X-02** 更严失败信号）·
> **PR-3**（判定式改写）· **PR-4**（下游承接 **D-1…D-7** · **含 D-7 → B19F1** 的可观测出口接线）· **PR-5**（**门禁 3/4/5 物理不可达成** · 宪法 v1.6.0）·
> **PR-6**（**立项书 §4.2 S5 ③ 的最小增量** = **D-24**）· **PR-7**（**X-04**：`__end__` 目标的更严失败信号）·
> **PR-8**（**FR-021**：`TypeError` · 上游同族）⇒ ⇒ 全部落进 **T065** 的**同一次**追认。
>
> ⚠️ **编号消歧（本 feature 的十套编号 · 互不撞名）**：**R-1…R-10**（回溯修订清单）·
> **D-16…D-28**（差分场景 · **全局序列**）· **X-01…X-04**（偏离登记）· **T001…T087**（**任务号**）·
> **P-01…P-16**（上游对照语义点）· **E-1…E-11**（上游实测）· **M-1…M-16**（不变量）·
> **DR-1…DR-13**（research 决策）· **裁定 1…18**（spec 裁定）
> ⇒ ⇒ ⚠️ 本文件的**任务号**是 `T0xx`（**三位**）· 而回溯修订清单是 `R-n`（**一位数**）
> ⇒ ⇒ ⚠️ **差分场景编号 = 全局序列**（**B12F1 已占用 `D-01…D-15`** ⇒ 本 feature 从 `D-16` 续编）
> ⇒ ⇒ 引用时 MUST 写全（`R-3` ≠ `T030` ≠ `D-18` ≠ `D-07` ≠ `X-03`）。

---

## 格式：`[ID] [P?] [Story] 描述`

- **[P]**：可并行（不同文件 / 无未完成依赖）
- **[Story]**：所属用户故事（US1…US3）—— 仅**用户故事阶段**的任务带
- **每条任务 MUST 带确切文件路径**（本仓库约定）

## 路径约定

- 源码：`src/freegraph/runtime/superstep.py`（L2 · **唯一**改动文件 · **不新增模块** ⇒ 层注册表**零改动**）
- 测试：`tests/runtime/test_superstep_multisource.py`（**新增** · 多源口径）· `tests/runtime/` 的 **10 个**冻结断言文件（**核对 · 零改动** ⇒ **MUST NOT** 改一个字 · 清单见 **T007**）
- 差分：`tests/differential/parity_probe.py`（**既有 30 个场景 MUST 逐字不变** ⇒ 只增）· `tests/differential/test_parity_probe.py`
- 人工验证：`harness/verification/B7F4/`（`acceptance.py` + `manual-verification.md`）
- 契约 / 规格：`specs/b7f4-multisource-join/`（本 feature）· `specs/b7f1-superstep-loop/`（**回溯修订**）
- 下游提示词：`harness/features/`（**只接线 · 逐条最小改动**）
- ⚠️ **上位文档**：`harness/proposals/立项书.md`（**MUST NOT** 由本 feature 代改 ⇒ **只登记不代改**）

---

**本 feature 的可测判据总表**（**22 FR + 13 SC + A1…A10 验收判据 ↔ 78 条任务**）—— **逐 FR / SC 一行**：

| # | 判据 | 出处 | 主责任务 |
|---|---|---|---|
| FR-001 | `edges` 键类型放宽 | spec FR-001 | T010 · T020 · T024 |
| FR-002 | 多源的每个源都在节点表里（**含多源边的目标** · C-Q18） | spec FR-002 | T025 · T037 |
| FR-003 | 判定式 = **∃ 组 g：∀ s∈g** | spec FR-003 | T023 · T026 · T027 · T033 |
| FR-004 | `seen` 逐源各记一条 + 只消费已满足的组 | spec FR-004 | T028 · T032 · T035 |
| FR-005 | 与上游同款（差分可判定） | spec FR-005 | T041 … T051 · T053 · T054 · **T081** · **T084** |
| FR-006 | 不新增通道类型 · 导出面零新增 | spec FR-006 | T076（+ T012 的「不新增类型」纪律） |
| FR-007 | 动态边不受影响 | spec FR-007 | T036 |
| FR-008 | `Command` / 稀疏读不受影响 | spec FR-008 | T036 |
| FR-009 | 层纪律（ARCH-1） | spec FR-009 | T077 |
| FR-010 | 依赖隔离 · 零出站 · 零环境变量 | spec FR-010 | T077 |
| FR-011 | 零新增门禁编号 | spec FR-011 | T077 |
| FR-012 | 破冻结面登记 + 追认 | spec FR-012 | T064 · T065 |
| FR-013 | 回溯修订清单逐条落全 | spec FR-013 | T055 … T063 |
| FR-014 | 上游行号纪律 | spec FR-014 | T052 |
| FR-015 | 人工验证记录（五段式） | spec FR-015 | T064 · T078 |
| FR-016 | 不越界 | spec FR-016 | T069 |
| FR-017 | 多源边的形态校验（V-16 · 含 `__end__` 目标） | spec FR-017 | T024 · T037 |
| FR-018 | 差分夹具支持多源边 + **期望构造期失败**（**三元组快照判据** · C-Q17） | spec FR-018 | T040 · T041 · T048 · T003 · **T083** |
| FR-019 | **门禁项偏离 MUST 登记**（宪法 v1.6.0 · **含门禁 7** · C-Q19） | spec FR-019 | T008 · T070 · T080 |
| FR-020 | **S5 ③ 的最小增量**（参数化场景 **D-24**） | spec FR-020 | T050 |
| FR-021 | **边键类型非法** ⇒ 内置 `TypeError`（上游同族） | spec FR-021 | T024 · T037 · **T084** |
| FR-022 | **可观测面零新增**（屏障触发的出口归 **B19F1**） | spec FR-022 | T069 · **T082** |
| SC-001 | 屏障目标的时序 | spec SC-001 | T021 · T022 · T023 · T029 |
| SC-002 | 屏障不齐 ⇒ 静默等待 | spec SC-002 | T030 · T031 · T038 |
| SC-003 | 屏障只触发一次 / 后齐再触发 | spec SC-003 | T032 · T035 · T039 |
| SC-004 | 差分逐字一致（**SAME 11 条** + **STRICTER 2 条**） | spec SC-004 | T041 … T051 · T053 · T054 · **T081** · **T084** |
| SC-005 | 既有判据零削弱 | spec SC-005 | T001 · T007 · T015 · T036 · T062 · **T085** |
| SC-006 | 导出面零新增 | spec SC-006 | T076 |
| SC-007 | 零新增门禁编号 | spec SC-007 | T077 |
| SC-008 | 回溯修订 + 形态校验落全（**含 14 条 Edge Case 逐条有断言** · C-Q20） | spec SC-008 | T027 · T037 · **T086** · **T087** · T055 … T063 · **T085** |
| SC-009 | 追认落盘 | spec SC-009 | T064 · T065 · T070 |
| SC-010 | 契约零影响 | spec SC-010 | T036 · T076 |
| SC-011 | 差分门禁全绿（**D-16…D-28**） | spec SC-011 | T050 · T051 · T053 · T054 · **T081** · **T083** · **T084** · T075 · T076 |
| SC-012 | 上游行号纪律 | spec SC-012 | T052 |
| SC-013 | **参数化场景组全绿**（S5 ③ 最小增量） | spec SC-013 | T050 · T075 |

**验收判据 A1…A10 的落点**（**逐条 · 可机读**）：

| 判据 | 任务 |
|---|---|
| **A1** 多源边可表达 | T020 |
| **A2** 屏障语义正确 | T021 · T023 · T030 |
| **A3** 与上游同款 | T051 · T053 · T054 · **T081** · **T084** |
| **A4** 既有断言零削弱 | T015 · T036 · T062 |
| **A5** 冻结面追认 | T064 · T065 · T070 |
| **A6** 导出面零新增 | T076 |
| **A7** 回溯修订落全 | T055 … T063 · **T085** |
| **A8** 形态校验生效（含 **源重复** · **环图** · **多源边目标不存在**） | T024 · T037 · **T086** · **T087** |
| **A9** 参数化场景全绿 | T050 |
| **A10** 门禁偏离已登记（**含门禁 7**） | T070 · T080 |

**承接条款 / 偏离登记的落点**：

| 项 | 任务 |
|---|---|
| **H-1**（B7F1 → B7F4 · 触发层口径） | T012 · T014 · T026 · T027 · T055 … T061 |
| **H-2**（B12F1 → B7F4 · 并发无关） | T023 · T027 · T046 |
| **H-3**（B9F1 → B7F4 · 动态边恒为单源） | T014 · T036 |
| **H-4**（B5F1 → B7F4 · 零新增通道类型） | T012 · T076 |
| **H-5**（B5F2 → B7F4 · 稀疏读零改动） | T014 · T036 |
| **H-6**（立项书 S5 ③ → B7F4） | T050 |
| **X-01**（破已冻结的契约面） | T055 … T063 · T065 |
| **X-02**（更严失败信号 · 空元组） | T037 · T054 · T065 |
| **X-04**（更严失败信号 · `__end__` 目标） | T024 · T037 · T053 · T065 |
| **D-7**（→ **B19F1** · 可观测出口） | **T082** · T065（**PR-4** 内 · 澄清轮 **C-Q13**） |
| **E-11**（上游实测 · 同成员不同序） | research §1（**已取证**）· **T081** |
| **D-28**（差分 · 边键类型非法 ⇒ `TypeError`） | **T084**（+ T040 的夹具能力）· T052（行号纪律） |
| **C-10**（research §4 · 既有 30 场景逐字不变 · **三元组快照比对** · C-Q17） | **T003** · **T083** |
| **X-03**（`defer` 专用屏障 · 已知不支持） | T069 |

---

## Phase 1: Setup（共享基础设施 · 取证基线）

**Purpose**: 把**基线**固定下来（后面「一条不删」「零新增」「门禁不可达成」全靠它判定）

- [X] T001 取 **SC-005 的基线**：统计 `tests/runtime/test_superstep_trigger.py` 的**断言条数**与**测试函数数**（用 `grep -c "assert "` 与 `grep -c "^def test_"`），记进 `specs/b7f4-multisource-join/research.md` §4 的 **C-01** 行（**只增一行** ⇒ 不改既有内容）
  ⚠️ **与 C-Q5 判据的关系**：澄清轮 **C-Q5** 已把 SC-005 的判定口径定为「**原文件内容逐字未变**」（⇒ 可机械核对）⇒ 本任务**只作取证留痕**（成本低 · 有助于人工复核）⇒ **不以条数**作为验收口径。
- [X] T002 取**导出面基线**：跑 `.venv/bin/python -c "import sys;sys.path.insert(0,'src');import freegraph.runtime as r, freegraph.contracts as c;print(len(r.__all__),len(c.__all__))"` ⇒ 期望 **20 / 20**，记进 `specs/b7f4-multisource-join/research.md` §4 的 **C-03** 行
- [X] T003 [P] 取**差分场景基线**：跑 `.venv/bin/python -c "import sys;sys.path.insert(0,'tests/differential');import parity_probe as p;print(len(p._scenarios()))"` ⇒ 期望 **30**，记进 `specs/b7f4-multisource-join/research.md` §4 的 **C-02** 行
  ⇒ ⇒ ⚠️ **追加（澄清轮 C-Q17 · 发起者 2026-11-13 拍板）**：同时把既有 **30** 个场景的
  **`(name, 判词, note)` 三元组**逐条导出成**快照**（⇒ 一并落进 **C-02** 行）⇒ ⇒
  供 **T083** 做「改动前后**逐条相等**」的机械比对 ⇒ ⇒ **MUST NOT** 用**文件级 `git diff`**
  作该判据（**同文件必被 T040 / T041 改动** ⇒ 文件级 diff **必然含删除行** ⇒ **必然假红**）
- [X] T004 [P] 核对**下游承接 D-1…D-7** 的目标提示词初稿现状：对 `harness/features/B6F1_StateGraph构建器.md` · `harness/features/B7F3_invoke返回完整状态.md` · `harness/features/B8F1_条件边路由与fresh读.md` · `harness/features/B14F1_Checkpointer协议与MemorySaver.md` · `harness/features/B7F2_compile编译.md` · `harness/features/B24F1_打包分发与兼容矩阵.md` · `harness/features/B19F1_TraceSink与current_span.md` 逐个 `grep` 关键字「屏障 / 多源 / add_edge / 兼容矩阵 / trace」，把「已落 / 未落」记进 `specs/b7f4-multisource-join/research.md` §4 的 **C-06** 行
  ⇒ ⇒ ⚠️ **追加（澄清轮 C-Q21 ⑤）**：范围由 **D-1…D-4** 扩到 **D-1…D-7** ⇒ ⇒ **D-5 / D-6 / D-7**
  也需「现状核对」基线（**T067 / T082** 要改这三份）⇒ ⇒ **零新增**下游承接条款
- [X] T005 [P] 建 `harness/verification/B7F4/` 目录（放 `acceptance.py` 与 `manual-verification.md`）⇒ **只建目录 + 一个 `.gitkeep`**，不写内容 ⇒ ⇒ 判据落点：**SC-009**（人工验证记录的**落盘位置**）
- [X] T006 核对 B7F1 契约的**逐条落点**：打开 `specs/b7f1-superstep-loop/contracts/superstep-contract.md`，定位 §1 边表行 · §2.1 边表行 · §3.1 · §3.2 判定式 · §4 阶段 ① 行 · §5 版本口径 · §7 的 **I-12** ⇒ 记下行号到 `specs/b7f4-multisource-join/research.md` §4 的 **C-04** 行（**Phase 6 照此改**）
- [X] T007 取 **冻结断言的完整核对面基线**（澄清轮 **C-Q5** 的机械判据 · SC-005）：逐个列出 **B7F1 / B9F1 / B12F1** 的**触发相关冻结断言**所在文件（**10 个**：`tests/runtime/test_superstep_trigger.py` · `test_superstep_contract.py` · `test_command_contract.py` · `test_command_goto_semantics.py` · `test_command_noop.py` · `test_command_purity.py` · `test_superstep_concurrency.py` · `test_command_list.py` · `test_command_merge_parity.py` · `test_read_c4_sparse_state.py`）⇒ 对**每个**文件跑 **`git diff HEAD --stat`** 取「**基线为空**」的证据 ⇒ 记进 `specs/b7f4-multisource-join/research.md` §4 的 **C-09** 行（**只增一行**）⇒ ⇒ **R-9 的核对面 = 这 10 个文件**（MUST NOT 只查其中一个）
  ⚠️ **MUST 用 `git diff HEAD --stat`**（**不是** `git diff --stat`）—— 后者**不比对已暂存的改动** ⇒ 可假通过
- [X] T008 取 **门禁 3 / 4 / 5「物理不可达成」的事实取证**（宪法 **v1.6.0** · 登记项 **PR-5** · FR-019）：确认 `harness/demo/target.py` 依赖 `StateGraph` / `compile()` / `invoke()`（**B6F1 / B7F2 / B7F3** 尚未落地）⇒ ⇒ 门禁 **3** 的「固定脚本原样可跑」· 门禁 **4** 的「fake 模型跑通验收基线一轮」· 门禁 **5** 的「人工记录含真实模型一轮」三部分在本 feature **物理不可达成** ⇒ ⇒ 取证（缺失依赖的报错输出）记进 `specs/b7f4-multisource-join/research.md` §4 的 **C-07** 行 ⇒ ⇒ 供 **T070** 的偏离登记引用
  ⇒ ⇒ ⚠️ **追加（澄清轮 C-Q19 · 发起者 2026-11-13 拍板）**：**另取门禁 7 的取证** —— 确认
  **API 兼容矩阵尚未落库**（全仓无兼容矩阵文件 ⇒ 首次落库属 **B24F1 / M4** ⇒ 本 feature
  按里程碑**不交付其前置能力**）⇒ ⇒ 门禁 **7** 的「**兼容矩阵已更新**」这一部分在本 feature
  **物理不可达成** ⇒ ⇒ 一并落进 **C-07** 行 ⇒ ⇒ 供 **T070** 的偏离登记引用

**Checkpoint**: 四条基线（断言条数 / **10 个冻结断言文件** / 导出面 / 差分场景数）+ 门禁不可达成取证 + 下游提示词现状**已落盘** ⇒ 可判定「一条不删」「零新增」。

---

## Phase 2: Foundational（阻塞性前置 · **骨架 · 行为逐字不变**）

**Purpose**: 把触发层改造成「**按组**记账」的**形状**，但**行为逐字不变**

> ⚠️ **本 Phase 只出骨架** ⇒ **多源边在运行期仍被拒**（既有 V-2 逻辑按「源不在节点表」报错）
> ⇒ ⇒ **US1 / US2 / US3 的用例在本 Phase 必然失败** ⇒ ⇒ **先红后绿**成立。

- [X] T010 放宽 `GraphSpec.edges` 的**类型注解**为 `dict[str \| tuple[str, ...], tuple[str, ...]]` 并更新 `GraphSpec` 的 docstring（边表行）—— **仅注解与文档 · 运行期行为不变**（`src/freegraph/runtime/superstep.py`）
- [X] T011 [P] 新增内部辅助函数 `_edge_sources(source: str \| tuple[str, ...]) -> tuple[str, ...]`：单源 ⇒ `(source,)`；元组 ⇒ **去重保序**（research **DR-4**）⇒ **只加函数 · 不接线**（`src/freegraph/runtime/superstep.py`）
- [X] T012 把 `_trigger_sources` 改名为 `_trigger_groups` ⇒ 承接 **H-1**（B7F1 → B7F4）· 承接 **H-4**（B5F1 → B7F4 · **零新增通道类型**） 并返回**组**的列表（`list[tuple[tuple[str, str], ...]]`）：静态边 + 动态边各成一组；按**成员集合**去重保序（research **DR-1 / DR-3**）—— **本 Phase 每组仍是单元素** ⇒ 行为不变（`src/freegraph/runtime/superstep.py`）
  ⚠️ **零新增类型 / 零新增导出符号**（裁定 9 / FR-006）⇒ **不进** `freegraph.runtime.__all__`
- [X] T013 新增内部辅助函数 `_satisfied_groups(state, node_name, groups) -> list[组]` 的**签名与调用点**（**判定逻辑的「组内全」语义由 T027 落地** ⇒ 本任务**只**落函数骨架与接线 ⇒ 避免与 T027 双实现）（`src/freegraph/runtime/superstep.py`）
- [X] T014 把 `_is_triggered` / `_determine_triggers` / `_run_round` 阶段 ② / `_consume_versions` 接到**组**接口上 ⇒ 承接 **H-1** · **H-3**（B9F1 → B7F4 · 动态边恒为单源）· **H-5**（B5F2 → B7F4 · 稀疏读零改动）（`_consume_versions` 改为接收**已满足的组**）—— **单元素组 ⇒ 与旧行为逐字等价**（research **DR-2 / DR-11**）（`src/freegraph/runtime/superstep.py`）
- [X] T015 回归核对：跑 `.venv/bin/python -m pytest tests/runtime/ tests/contracts/ -v` ⇒ **全绿**；并对 **T007 列出的 10 个冻结断言文件**逐个跑 **`git diff HEAD --stat`** ⇒ **必须全为空**（**R-9 的机械判据** · SC-005）

**Checkpoint**: 触发层已「按组」运转，但**可观察行为逐字不变** ⇒ **既有断言一条不删**成立（SC-005）。

---

## Phase 3: User Story 1 - 两个并行分支汇合到一个下游（Priority: P1）🎯 MVP

**Goal**: 多源边**可表达**（`edges={("a","b"): ("c",)}` 构造成功）⇒ 目标节点**严格晚于**所有源执行。

**Independent Test**: 构造含多源汇合边的图跑到底 ⇒ 断言「`c` 的执行**严格晚于** `a` 与 `b`」⇒ **不依赖**其他 story。

### Tests for User Story 1（MUST 先写 · MUST 先失败）

- [X] T020 [P] [US1] 在 `tests/runtime/test_superstep_multisource.py` 写**多源边可表达**用例 ⇒ **A1** · FR-001 · **M-1**：`edges={("a","b"): ("c",)}` ⇒ 构造**成功**（不抛错）⇒ **M-1**
- [X] T021 [P] [US1] 在 `tests/runtime/test_superstep_multisource.py` 写「屏障目标**严格晚于**所有源」用例 ⇒ **A2** · FR-003 · **M-2**（`c` 在执行序列里的位置晚于 `a` 与 `b`）⇒ **M-2**（**断言 MUST 用位置比较 · 不得断言 `a` 与 `b` 的先后** ⇒ 并发下二者顺序不确定 · 裁定 13）
- [X] T022 [P] [US1] 在 `tests/runtime/test_superstep_multisource.py` 写「两源**同一轮**被触发 ⇒ `c` 在**下一轮**才被触发」用例（research **DR-8**）⇒ **M-2**
- [X] T023 [P] [US1] 在 `tests/runtime/test_superstep_multisource.py` 写「**组内全**」用例 ⇒ **A2** · FR-003 · **M-2**：屏障只满足**一个**源时，`c` **不**执行 ⇒ **M-2**（这条是 US1 的**先红**核心）

### Implementation for User Story 1

- [X] T024 [US1] 在 `_validate_graph_spec` 里**分流边键**：`tuple` 键 ⇒ 走**多源**校验分支（**V-16** **四条**：元组**非空** / **不含** `__start__` / 目标**恰为一个** / 目标 **MUST NOT** 为 `__end__` ⇒ 内置 `ValueError` 并点名 · 澄清轮 **C-Q9** · **X-04**）；**类型**非法（既非 `str` 亦非 `tuple`）⇒ 内置 `TypeError`（**FR-021** · 裁定 17 · 语义点 **P-16** · 上游同族 · 实测 **E-10** · research **DR-5**）（`src/freegraph/runtime/superstep.py`）
  ⚠️ **校验的**优先级**（澄清轮 **C-Q15** · 发起者 2026-11-13 拍板）**：**形态校验（`V-16`）MUST 先于缺源校验（`V-2`）** ⇒ ⇒ 本任务**先于 T025** 落地 ⇒ ⇒ 元组同时命中两者时（典型 = 元组含 `__start__`）⇒ **归 `V-16`** ⇒ ⇒ 失败信号仍是内置 `ValueError` ⇒ ⇒ 测试断言 MUST 只断言**异常类型**与**点名**（**MUST NOT** 断言消息的逐字文本）
- [X] T025 [US1] 在 `_validate_graph_spec` 的**多源分支**里**逐个查源**：每个源 MUST 在节点表里 ⇒ 否则内置 `ValueError`（**V-2** 同族）并**点名全部**缺失的源名（FR-002 · 裁定 8 · 上游 **E-8** 同族）（`src/freegraph/runtime/superstep.py`）
  ⇒ ⇒ ⚠️ **追加（澄清轮 C-Q18 · 发起者 2026-11-13 拍板）**：**并校验多源边的目标在节点表里**
  ⇒ 否则内置 `ValueError`（**V-2** 同族）并**点名该目标** ⇒ ⇒ **归 `V-2`**（语义校验族）
  ⇒ **NOT** `V-16`（形态校验族）⇒ ⇒ 校验顺序不变：**形态 `V-16` 先于** 缺源 / 缺目标 `V-2`
  ⇒ ⇒ **零新增**错误类型
  ⚠️ **本任务 MUST 在 T024 之后落地**（澄清轮 **C-Q15**）⇒ ⇒ **形态校验（`V-16`）先于缺源校验（`V-2`）** ⇒ ⇒ 元组含 `__start__` ⇒ 归 **V-16**（**不是** V-2）
- [X] T026 [US1] 让 `_trigger_groups` 支持**多源组**：元组键 ⇒ 该组含**全部**源的边触发源（`("e", 源名)` · 逐字见 `specs/b7f4-multisource-join/contracts/superstep-multisource-contract.md` §3.1）（`src/freegraph/runtime/superstep.py`）
- [X] T027 [US1] 实现 `_satisfied_groups` 的**组内合取**（`∀ s ∈ g: version(s) > seen(N)[s]`）⇒ 承接 **H-2**（B12F1 → B7F4 · 并发无关）· 裁定 3 / 裁定 4：多源组只在**全部**成员越过各自的 `seen` 时才算满足 ⇒ **M-2**（`src/freegraph/runtime/superstep.py`）
- [X] T028 [US1] 让 `_consume_versions` 对**多源组****逐源各记一条** `seen[(kind, ident)] = version(ident)`（FR-004 · 裁定 10 ⇒ `versions_seen` **结构零改动** ⇒ `SchedulerState` 的**签名冻结断言**（`tests/runtime/test_command_purity.py`）**不受影响**）（`src/freegraph/runtime/superstep.py`）
- [X] T029 [US1] 跑 `.venv/bin/python -m pytest tests/runtime/test_superstep_multisource.py -v` ⇒ **US1 的四条用例全绿**；并重跑 `tests/runtime/` 全量 ⇒ 仍**全绿**（**单源口径零变化**）

**Checkpoint**: US1 可**独立**验收（多源边可表达 + 屏障目标严格晚于所有源）。

---

## Phase 4: User Story 2 - 屏障没齐时下游静默等待（Priority: P2）

**Goal**: 屏障**不齐** ⇒ 目标**不执行** + 图**正常收敛**（不抛错）；屏障**后齐** ⇒ 目标**再执行一次**（不被吞掉）。

**Independent Test**: 造一张「屏障某个源**永不可达**」的图 ⇒ 断言「目标执行计数 == 0」且「整张图正常收敛、不抛错」。

> ⚠️ **前置限定**（澄清轮 **C-Q1**）：该目标 MUST **只有**这一条多源入边 ⇒ 若另有单源入边 ⇒ 按「**组间任一**」它**仍会被触发**（那是 US2 的第三条用例）。

### Tests for User Story 2（MUST 先写 · MUST 先失败）

- [X] T030 [P] [US2] 在 `tests/runtime/test_superstep_multisource.py` 写「**屏障不齐**」用例 ⇒ **A2** · FR-004 · **M-3**：一个源**永不可达** ⇒ 屏障目标**执行计数 == 0** ⇒ **M-3**（上游 **E-2** 同款）
- [X] T031 [P] [US2] 在 `tests/runtime/test_superstep_multisource.py` 写「同一张图**正常收敛**」用例（**不抛错** · 无「屏障未齐」类错误）⇒ **M-3**
- [X] T032 [P] [US2] 在 `tests/runtime/test_superstep_multisource.py` 写「屏障**后齐** ⇒ 目标**再执行一次**」用例（先因单源边、后因屏障齐 ⇒ **两次**）⇒ **M-5**（上游 **E-5** 同款）—— ⚠️ 这是 US2 的**先红**核心（未改消费口径前只会跑**一次**）
- [X] T033 [P] [US2] 在 `tests/runtime/test_superstep_multisource.py` 写「**组间任一**」用例：单源边 + 不齐的屏障边并存 ⇒ 目标**仍被触发**（上游 **E-3** 同款）⇒ **M-8**
- [X] T034 [P] [US2] 在 `tests/runtime/test_superstep_multisource.py` 写「源**不订阅任何通道**」用例（入参为空 `dict`）⇒ 它**照样算「跑过」** ⇒ 屏障仍满足（FR-003 · 「源跑过」与「源写了什么」无关）
- [X] T086 [P] [US2] 在 `tests/runtime/test_superstep_multisource.py` 写「**元组内重复源**」用例：`edges={("a","a"): ("c",)}` ⇒ **构造成功**（**MUST NOT** 报错）⇒ **去重保序**后只剩一个源 ⇒ 行为与**单源口径** `edges={"a": ("c",)}` **逐字一致** ⇒ ⇒ 补齐 spec Edge Case「**源重复**」（裁定 2 · research **DR-4** · 契约 §2.3 的规范化表）（`tests/runtime/test_superstep_multisource.py`）
  ⚠️ **追加（澄清轮 C-Q20 · 发起者 2026-11-13 拍板）**：本条为**分析轮第四轮新增**（编号**追加**在末尾 ⇒ 非笔误）⇒ ⇒ 补齐 spec 的 **14** 条 Edge Case 中原零覆盖的一条
- [X] T087 [P] [US2] 在 `tests/runtime/test_superstep_multisource.py` 写「**环图**」用例：`("a","b") → c` 且 `c → a` ⇒ 屏障**照常判定**（**逐轮**判定 · **不做**环检测）⇒ 收敛由**既有步数上限**兜底 ⇒ ⇒ **MUST NOT** 抛「环检测」类异常（research **DR-9** · 契约 §6）⇒ ⇒ 补齐 spec Edge Case「**屏障目标自己也是某个源的祖先**」（`tests/runtime/test_superstep_multisource.py`）
  ⚠️ **追加（澄清轮 C-Q20 · 发起者 2026-11-13 拍板）**：本条为**分析轮第四轮新增**（编号**追加**在末尾 ⇒ 非笔误）⇒ ⇒ 补齐 spec 的 **14** 条 Edge Case 中原零覆盖的一条

### Implementation for User Story 2

- [X] T035 [US2] 把 `_consume_versions` 在**多源组**上的记账范围收窄为「**只消费已满足的组**的源」⇒ **未满足的组不记账** ⇒ 屏障后来齐了**仍能再触发**（FR-004 · 裁定 4 · 上游 **E-5** 同款）（`src/freegraph/runtime/superstep.py`）
  ⚠️ **与 T014 的边界（分析轮第三轮）**：**T014** 已把 `_consume_versions` 的**入参**改为「**已满足的组**」（Phase 2 · 每组仍是单元素 ⇒ **行为逐字不变**）⇒ ⇒ **本任务只做「多源组」侧的可观察变化**（多源组未满足 ⇒ **不记账** ⇒ 屏障后来齐了仍能再触发）⇒ ⇒ **单源组 MUST 零变化**（未满足 ⇒ `version ≤ seen` ⇒ 同值记账 · research **DR-11**）⇒ ⇒ **MUST NOT** 重复改写 T014 的接口
- [X] T036 [US2] 核对「**单源口径逐字不变**」：跑 `.venv/bin/python -m pytest tests/runtime/ -v` ⇒ **全绿**；对 **T007 的 10 个文件**逐个跑 **`git diff HEAD --stat`** ⇒ **全为空**；并在 `specs/b7f4-multisource-join/research.md` 补记「**未满足 ⇒ 同值记账**」的等价性论证（research **DR-11**）⇒ ⇒ **SC-005**
  ⚠️ **动态边（FR-007）与稀疏读（FR-008）**随本任务的全量回归**一并守住**（`tests/runtime/test_command_goto_semantics.py` · `test_read_c4_sparse_state.py`）
- [X] T037 [US2] 在 `tests/runtime/test_superstep_multisource.py` 补「**多源边的形态校验**」用例 ⇒ **A8** · **X-02 / X-04**（两条「比上游更严」的失败信号）：空元组（上游 **E-6** ⇒ freegraph **更严** · **X-02**）· 含 `__start__`（上游 **E-7** 同族）· 目标数 ≠ 1 · **目标为 `__end__`**（上游 **E-9** 静默 no-op ⇒ freegraph **更严** · **X-04** · 澄清轮 **C-Q9**）⇒ 构造期内置 `ValueError`（**V-16**）；缺源 ⇒ 内置 `ValueError` 且**点名缺失源**（**V-2** 同族 · 上游 **E-8**）；**边键类型非法**（如 `123`）⇒ 内置 **`TypeError`**（**FR-021** · 上游 **E-10** 同族）⇒ **A8**
  ⇒ ⇒ ⚠️ **追加（澄清轮 C-Q18 / C-Q20）**：**多源边的目标不在节点表** ⇒ 内置 `ValueError` 且
  **点名该目标**（**V-2** 同族 ⇒ **NOT** `V-16`）⇒ ⇒ 补齐 spec Edge Case
  「**多源边指向不存在的目标**」⇒ ⇒ **MUST NOT** 断言错误消息的**逐字文本**（只断言**异常类型**与**点名**）
- [X] T039 [P] [US2] 在 `tests/runtime/test_superstep_multisource.py` 写「**同一轮内至多触发一次**」用例：屏障目标在**单轮** `executed` 里**至多出现一次**（⇒ **M-4**）⇒ **SC-003** 的前半句
- [X] T038 [US2] 跑 `.venv/bin/python -m pytest tests/runtime/test_superstep_multisource.py -v` ⇒ **US2 的九条用例全绿**（T030 / T031 / T032 / T033 / T034 / **T037** / T039 / **T086** / **T087**）；并确认 `tests/runtime/` 其余用例仍全绿
  ⇒ ⇒ ⚠️ **追加（澄清轮 C-Q21 ⑧）**：原写「**六条**」⇒ **漏算 T037** ⇒ ⇒ 实际 **9** 条（US2 的
  **7** 条测试任务 + **T037** + **T086** + **T087** ⇒ 计数以本行列出的 **9** 个任务号为准）

**Checkpoint**: US1 + US2 均可**独立**验收（不齐 ⇒ 静默等待；后齐 ⇒ 再触发一次）。

---

## Phase 5: User Story 3 - 与上游同款（差分可判定）（Priority: P3）

**Goal**: 差分探针新增**屏障场景组** ⇒ 两侧**节点序列 + 最终状态**逐字一致（判词 **SAME**）
⇒ ⇒ **失败面**的**两条刻意更严**（**D-25 / D-26**）判词 = **STRICTER**（须带 `note`）。

**Independent Test**: `pytest tests/differential/` ⇒ 屏障场景组**全绿**（上游缺席即 **skip**）。

### Tests for User Story 3（MUST 先写 · MUST 先失败）

- [X] T040 [P] [US3] 放宽差分夹具的**边表键类型**为 `dict[str \| tuple[str, ...], tuple[str, ...]]`（`Scenario.edges`）⇒ **既有 30 个场景 MUST 逐字不变**（`tests/differential/parity_probe.py`）
  ⇒ **另**：为 `Scenario` **新增可选字段**「**期望构造期失败**」（**两侧各自期望** ⇒ 可表达「两侧都失败」与「一侧失败一侧不失败」两种形态）⇒ 供 **D-22 / D-25 / D-26 / D-28** 使用 ⇒ ⇒ ⚠️ **新增字段必须全部可选**（缺省 ⇒ **既有 30 个场景的行为与判词逐字不变** · 沿用 **B12F1** 的「全部可选」先例 · **FR-018**）
  ⇒ ⇒ ⚠️ **键类型另须能表达「既非 `str` 亦非 `tuple`」**（**仅为 `D-28`** · 澄清轮 **C-Q14** · **测试侧夹具** · 非产品面 ⇒ **零新增导出符号**）
  ⇒ ⇒ ⚠️ **`__end__` 归一化的**分流**（分析轮第三轮 · HIGH 项 · 缺此则 **D-25 落空**）**：`run_freegraph` 现有实现把**所有**边的 `__end__` 目标**剥除**（`edges = {src: tuple(t for t in targets if t != "__end__") ...}`）⇒ ⇒ 若**多源键**的 `__end__` 目标也被剥除 ⇒ **D-25** 会退化成「目标数 ≠ 1」而非「目标为 `__end__`」⇒ ⇒ **V-16 的 `__end__` 分支经夹具永远不可达**（⇒ M-14 的「消息点名该边」落空）⇒ ⇒ **本任务 MUST 让「多源键」的 `__end__` 目标**穿透**到 `GraphSpec` 构造期**（**单源键照旧剥除** ⇒ **「边到 `__end__` 即终止」的既有语义逐字不变**）
- [X] T041 [P] [US3] 在 `run_upstream` 里让**元组键**走上游**真实形态** `graph.add_edge(list(starts), target)`；**字符串键**的写法**逐字不变** ⇒ ⇒ 既有场景**零变化**（research **DR-7**）（`tests/differential/parity_probe.py`）
- [X] T042 [P] [US3] 落**差分场景 D-16**（标准屏障 ⇒ 上游基线 `{'msgs': ['a','b','c']}` · 判词 **SAME** · 上游 **E-1**）（`tests/differential/parity_probe.py`）
- [X] T043 [P] [US3] 落**差分场景 D-17**（屏障不齐 ⇒ 两侧 `c` 都不执行 · **SAME** · 上游 **E-2**）（`tests/differential/parity_probe.py`）
- [X] T044 [P] [US3] 落**差分场景 D-18**（单源边 + 不齐的屏障边并存 ⇒ 两侧 `c` **都执行一次** · **SAME** · 上游 **E-3**）（`tests/differential/parity_probe.py`）
- [X] T045 [P] [US3] 落**差分场景 D-19**（屏障**后齐** ⇒ 两侧 `c` **都执行两次** · **SAME** · 上游 **E-5**）（`tests/differential/parity_probe.py`）
- [X] T046 [P] [US3] 落**差分场景 D-20**（屏障的**并发无关性**：并发档 vs 串行档 `max_concurrency=1` ⇒ freegraph 自身两侧的**最终状态 + 待写入序列**逐字相等 ⇒ **SAME** · 裁定 13）（`tests/differential/parity_probe.py`）
- [X] T047 [P] [US3] 落**差分场景 D-21**（**两条屏障并存**（其中一条不齐）⇒ 两侧的 `c` **都执行一次** ⇒ 先齐的那条生效 ⇒ **SAME** · 上游 **E-4**）（`tests/differential/parity_probe.py`）
- [X] T048 [P] [US3] 落**差分场景 D-22**（**缺源**的多源边 ⇒ 两侧都**构造期失败**（**失败与否**一致）⇒ **SAME** · 上游 **E-8** 同族）（`tests/differential/parity_probe.py`）
  ⇒ ⚠️ 依赖 **T040** 新增的「**期望构造期失败**」夹具能力 ⇒ ⇒ **判词 = SAME**（失败与否一致）
- [X] T049 [P] [US3] 落**差分场景 D-23**（**元组顺序无关**：`("a","b")` vs `("b","a")` ⇒ 两侧的**节点序列 + 最终状态**逐字相等 ⇒ **SAME** · 语义点 **P-14**）（`tests/differential/parity_probe.py`）
- [X] T050 [P] [US3] 落**差分场景 D-24** ⇒ **A9** · 承接 **H-6** · 裁定 12（**参数化**增量 · 兑现**承接条款 H-6** / 立项书 **§4.2 S5 ③** 的「**B7F4 起逐个补**」）：用 `pytest.mark.parametrize` 枚举 **屏障形态**（单源 / 多源）× **通道类型**（`last` / `binop` / `ephemeral`）× **源可达性**（全可达 / 缺一源）⇒ 断言两侧的**节点序列 + 最终状态**逐字一致（判词 = **SAME**）⇒ ⇒ **只铺「屏障维度」的最小增量** ⇒ ⇒ **MUST NOT** 一次性铺开 S5 ③ 的**全量**枚举（归后续 feature）⇒ ⇒ **M-13** ⇒ ⇒ ⚠️ **认领 research §4 的 C-08**（立项书 §5.9 的「**B7F4 起逐个补**」口径核对）⇒ ⇒ **SC-013**（`tests/differential/parity_probe.py`）
- [X] T053 [P] [US3] 落**差分场景 D-25**（**多源边指向 `__end__`** ⇒ 上游 = **被接受但静默 no-op**（**E-9**）· freegraph = **构造期显式失败**（内置 `ValueError`）⇒ ⇒ **判词 = `STRICTER`** ⇒ ⚠️ **MUST 带 `note`**（说明「上游静默 no-op · freegraph 构造期显式失败」· **X-04**）⇒ ⇒ 依赖 **T040** 的「**期望构造期失败**」夹具能力（**两侧各自期望**）（`tests/differential/parity_probe.py`）
- [X] T054 [P] [US3] 落**差分场景 D-26**（**空的多源边 `()`** ⇒ 上游 = **被接受但静默**（**E-6**）· freegraph = **构造期显式失败**（内置 `ValueError`）⇒ ⇒ **判词 = `STRICTER`** ⇒ ⚠️ **MUST 带 `note`**（说明「上游静默 · freegraph 构造期显式失败」· **X-02**）⇒ ⇒ 依赖 **T040** 的「**期望构造期失败**」夹具能力）（`tests/differential/parity_probe.py`）
- [X] T081 [P] [US3] 落**差分场景 D-27**（**两条同成员不同序的多源边并存**：`("a","b") → c` **且** `("b","a") → c` ⇒ **两侧的屏障目标都只执行 1 次** ⇒ 节点序列与最终状态逐字一致 ⇒ **判词 = `SAME`** · 上游基线 = `{'msgs': ['a','b','c']}` · **实测 E-11**）⇒ ⇒ **锁定 P-14 的「按成员集合去重」行为 · 防回归**（⚠️ 上游的触发汇总是 `triggered_nodes: set[str]` ⇒ **按节点去重** · `_algo.py:476-482` ⇒ ⇒ **freegraph 与上游同款** ⇒ ⇒ **无需偏离登记**）（`tests/differential/parity_probe.py`）
- [X] T084 [P] [US3] 落**差分场景 D-28**（**边键类型非法**：`123 → ("a",)` ⇒ 两侧**均抛内置 `TypeError`** ⇒ **失败与否**一致 ⇒ **判词 = `SAME`** · 上游 **E-10**：`TypeError: 'int' object is not iterable` · 锚点 `state.py:969` ⇒ ⇒ **上游同族**）⇒ ⇒ 兑现 **C-Q10** 的「**类型族**」承诺（澄清轮 **C-Q14**）⇒ ⇒ **依赖 T040** 新增的「**期望构造期失败**」夹具能力（**两侧各自期望**）⇒ ⇒ **FR-021** · **裁定 17** · 语义点 **P-16** · **SC-004** · **SC-011**（`tests/differential/parity_probe.py`）

### Implementation for User Story 3

- [X] T051 [US3] 跑 `.venv/bin/python -m pytest tests/differential/ -v` ⇒ **A3** · SC-004 / SC-011 / SC-013 ⇒ **D-16…D-28 全绿**（上游缺席 ⇒ **skip** 而非失败）⇒ ⇒ 判词分布 = **SAME 11 条**（D-16…D-24 / **D-27 / D-28**）+ **STRICTER 2 条**（**D-25 / D-26** · 各带 `note`）⇒ **SC-004 / SC-011 / SC-013**
- [X] T083 [US3] **认领 research §4 的 C-10**（FR-018 / SC-011 的「**既有 30 个场景逐字不变**」的**机械证据**）：把既有 **30** 个场景的 **`(name, 判词, note)` 三元组**逐条导出成**改动后快照** ⇒ ⇒ 与 **T003** 落在 **C-02** 行的**基线快照**做**逐条比对** ⇒ ⇒ **必须逐条相等** ⇒ ⇒ **既有 30 个场景的 `name` / 判词 / `note` 逐字不变** ⇒ ⇒ 把该证据记进 `specs/b7f4-multisource-join/research.md` §4 的 **C-10** 行（**只增一行**）⇒ ⇒ **FR-018** · **SC-011**
  ⚠️ **追加（澄清轮 C-Q17 · 发起者 2026-11-13 拍板）**：原判据「跑 `git diff HEAD --stat -- parity_probe.py`
  ⇒ diff MUST **只显示新增行**」**不可满足** ⇒ ⇒ ① `--stat` 只给**统计**、**不显示行**；
  ② **T040 / T041 必改同一文件**（夹具**类型注解放宽** · **`__end__` 分流** · **`run_upstream` 接线**）
  ⇒ ⇒ 该文件 diff **必然含删除行** ⇒ ⇒ 用它判定「只增不改」**必然假红** ⇒ ⇒ **判据改为三元组快照比对**
  ⇒ ⇒ **文件级 `git diff` 降级为辅助证据**（**MUST NOT** 作为判据；若要看 diff 仍**MUST 用
  `git diff HEAD --stat`** —— **不是** `git diff --stat` —— 后者**不比对已暂存的改动** ⇒ 可假通过）
  ⚠️ **与 T003 的区别**：**T003** 取的是**改动前**的**场景数**基线（30）+ **三元组快照**（**C-02**）
  ⇒ ⇒ **本任务**证的是「**逐字未改**」（**数**不变**不等于**文本未变**）⇒ ⇒ 与 **SC-005** 对
  10 个冻结文件所用的 `git diff HEAD --stat` 判据**同族**（但**对象**不同：前者比**文件**，
  后者比**场景三元组** ⇒ ⇒ **MUST NOT** 混用）
- [X] T052 [US3] 核对**上游行号纪律**：确认 `specs/b7f4-multisource-join/contracts/upstream-parity.md` 的 **P-01…P-16** 每条都带**版本 + `路径:行号`** 且每条**行为**断言都指向 **E-1…E-11** 之一 ⇒ **凭记忆沿用的引用数 == 0**（FR-014 · SC-012）⇒ ⇒ ⚠️ 特别核对 **P-15 / P-16** 各自带 **E-9 / E-10** 的**实测**支撑 · **P-14** 带 **E-11** 的**实测**支撑（⚠️ **E-11 已把旧附注的「上游可触发两次」证伪** ⇒ P-14 的附注 MUST 写「**按节点去重 · 只触发 1 次**」）
  ⇒ ⇒ ⚠️ **核对范围 MUST 覆盖 P-14 的三处附注**（分析轮第三轮 · CRITICAL 项的**防回归**）：`contracts/upstream-parity.md` · `contracts/superstep-multisource-contract.md` §3.1「去重」行 · `data-model.md` §3.1「组的去重」行 ⇒ ⇒ 三处 MUST **逐字同款**（「上游同样只触发 1 次」· 按**节点**去重 · `_algo.py:476-482`）⇒ ⇒ **MUST NOT** 残留「上游可触发两次」的旧表述 ⇒ ⇒ **FR-014** · **SC-012**
  ⇒ ⇒ ⚠️ **追加（澄清轮 C-Q21 · 发起者 2026-11-13 拍板）**：**证据表 MUST 含 `D-28`** ⇒ ⇒
  `contracts/upstream-parity.md` 的 **E-10** 行原写「差分 **—**（类型面由单元用例覆盖）」⇒ ⇒
  **MUST NOT** 残留「差分 —」⇒ ⇒ **必须**写「差分 **D-28**（判词 **SAME** · 两侧均抛内置 `TypeError`）」
  ⇒ ⇒ **C-Q10 / C-Q14 的「类型族」承诺**在证据表侧亦须**可核** ⇒ ⇒ **FR-014** · **SC-012**

**Checkpoint**: 三个故事均**独立**可用；屏障语义与上游**逐字同款**且**可自动判定**。

---

## Phase 6: 回溯修订与追认（**破冻结面的代价** ⇒ **阻断合入**）

**Purpose**: 把 B7F1 被破的**冻结面**逐条**回溯修订**（**拆分而不删**）⇒ 并落**发起者追认**

> ⚠️ 本 Phase **MUST** 在合入前**全绿**；追认**未落盘 ⇒ MUST NOT 合入**（宪法 v1.8.0）。
> ⚠️ **「拆分而不删」**：既有断言**一条不删** ⇒ 每处修订 MUST **只增不改**。
> ⚠️ **追认打包 8 项 1 次**（澄清轮 **C-Q13**）：**PR-1**（**R-1…R-10**）· **PR-2**（**X-02**）· **PR-3**（判定式）·
> **PR-4**（**D-1…D-7** · **含 D-7 → B19F1**）· **PR-5**（门禁 3/4/5 不可达成）· **PR-6**（**D-24**）· **PR-7**（**X-04**）·
> **PR-8**（**FR-021**）⇒ **T065** 一处写全（⇒ **零新增登记项**）。

- [X] T055 [P] 回溯修订 **R-1** ⇒ **A7** · **X-01**（破已冻结的契约面）· 登记项 **PR-1**：在 `specs/b7f1-superstep-loop/contracts/superstep-contract.md` 的 **§1**（`GraphSpec` 的边表行）与 **§2.1**（边表行）把键类型由 `str` 放宽为 `str \| tuple[str, ...]` ⇒ **既有行逐字保留**（只增多源分支的说明）
- [X] T056 [P] 回溯修订 **R-2**：在 `specs/b7f1-superstep-loop/contracts/superstep-contract.md` 的 **§3.1** —— 引入「**触发源组**（每条入边一个组）」⇒ **既有触发源定义逐字保留**
- [X] T057 [P] 回溯修订 **R-3**：在 `specs/b7f1-superstep-loop/contracts/superstep-contract.md` 的 **§3.2** —— 判定式由「∃ 触发源」增补为「**∃** 组 g：**∀** s ∈ g」⇒ **原判定式逐字保留**（并注明**单源组逐字退化**）
- [X] T058 [P] 回溯修订 **R-4 / R-5**：在 `specs/b7f1-superstep-loop/contracts/superstep-contract.md` 的 **§4**（阶段 ① 行）与 **§5**（版本口径 / `seen`）—— 补「逐源各记一条」+「只消费已满足的组」⇒ **既有行逐字保留**
- [X] T059 [P] 回溯修订 **R-6**：在 `specs/b7f1-superstep-loop/contracts/superstep-contract.md` 的 **§7** 的 **I-12** —— 补「屏障两源的**执行先后不确定** ⇒ 屏障的**触发**顺序亦然 ⇒ MUST NOT 作任何可观察顺序的判据」⇒ **I-12 原文逐字保留**
- [X] T085 回溯修订 **R-1…R-6 后的**契约守卫回归**（分析轮第三轮 · **顺序缺口**）：`tests/runtime/test_superstep_contract.py` 会**解析** `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §7 的**不变量编号表**（首格 `fullmatch(r"I-\d+")` ⇒ 断言 == **I-1…I-16**）⇒ ⇒ **T055…T059 改契约后 MUST 立刻跑** `.venv/bin/python -m pytest tests/runtime/test_superstep_contract.py -v` ⇒ ⇒ **必须全绿** ⇒ ⇒ ⚠️ 若新增的表格行首格形如 `I-13` ⇒ 该守卫测试会红 ⇒ ⇒ **R-6 的补注 MUST NOT 写成新的不变量行**（⇒ 只在 **I-12 行内**追加说明）⇒ ⇒ **SC-005** · **SC-008**
- [X] T060 [P] 回溯修订 **R-7**：在 `specs/b7f1-superstep-loop/spec.md` 的 **FR-002 / FR-013 / Edge Cases** 增补「**多源口径**」的分支 ⇒ **既有 FR 与既有 Edge Case 一条不删**
- [X] T061 [P] 回溯修订 **R-8**：在 `specs/b7f1-superstep-loop/data-model.md` 的 **§6 校验表**（**V-2** 适用范围扩到「多源边的每个源」+ **追加 V-16**）与 **§3.2 / §4.2**（`seen` 口径）⇒ **既有校验表一条不删** ⇒ ⇒ ⚠️ **认领 research §4 的 C-05**（§6 校验表与 §3.2 判定式的逐字落点核对）
- [X] T062 回溯修订 **R-9** 的核对：对 **T007 列出的 10 个冻结断言文件**逐个跑 **`git diff HEAD --stat`** ⇒ **必须全为空**；并把该证据（**10 个空 diff**）记进 `harness/verification/B7F4/manual-verification.md` 的「验证步骤」段 ⇒ **SC-005**
- [X] T063 [P] 回溯修订 **R-10**：在 `specs/b7f1-superstep-loop/tasks.md` 与 `specs/b7f1-superstep-loop/research.md` 各**追加一行**注记「⚠️ **2026-11-13 · B7F4 回溯修订**：R-1…R-10 已落……」⇒ **既有任务与既有决策的原文逐字保留**
- [X] T064 [P] 写 `harness/verification/B7F4/manual-verification.md` 的**五段式**（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）⇒ **FR-015 / SC-009**
- [X] T065 **【阻断合入】发起者追认** ⇒ **A5** · **X-01 / X-02 / X-04** · 登记项 **PR-1…PR-8**（**8 项** · 澄清轮 **C-Q13** ⇒ **PR-9 并入 PR-4** ⇒ **零新增登记项**）：把 **PR-1 … PR-8** **八项打包成一次**的**追认文字**写进 `harness/verification/B7F4/manual-verification.md`（**MUST NOT** 由实现者代签 · 宪法原则 V / v1.6.0 / v1.8.0）⇒ 含 **PR-1**（回溯修订 **R-1…R-10**）· **PR-2**（**X-02** 空元组更严失败信号）· **PR-3**（判定式改写为「∃ 组 g：∀ s∈g」）· **PR-4**（下游承接 **D-1…D-7** · **含 D-7 → B19F1** 的可观测出口接线 · **FR-022** · 裁定 18 · 澄清轮 **C-Q12**）· **PR-5**（**门禁 3 / 4 / 5 物理不可达成** · 承接方 **B6F1 / B7F3 / B25F1**）· **PR-6**（**D-24** 参数化最小增量）· **PR-7**（**X-04** `__end__` 目标的更严失败信号 · 澄清轮 **C-Q9**）· **PR-8**（**FR-021** `TypeError` · 上游同族 · 裁定 17 · 澄清轮 **C-Q10**）⇒ ⇒ **追认次数 == 1**
  ⇒ ⇒ ✅ **追认已落盘**（**发起者签字 · 2026-11-13** · `harness/verification/B7F4/manual-verification.md` §4.1）⇒ ⇒ **合入闸口（G-f）已开** ⇒ ⇒ **追认次数 == 1** ✓
- [X] T066 下游接线 **D-1**：在 `harness/features/B6F1_StateGraph构建器.md` 追加承接条款（构建器的 `add_edge([a,b], c)` **直接透传**元组键 · `defer=True` 专用屏障**已知不支持**）⇒ **只接线 · 逐条最小改动**（**MUST NOT** 改动该文件的其余内容）⇒ ⚠️ **权威出处** = 立项书 **§4.3 #4**（`add_edge` **同名同签名** · 签名 `(start_key: str \| list[str], end_key: str) -> Self`）
- [X] T067 [P] 下游接线 **D-2 / D-3 / D-4 / D-5 / D-6**：分别在 `harness/features/B7F3_invoke返回完整状态.md`（`invoke` 随之支持屏障）· `harness/features/B8F1_条件边路由与fresh读.md`（条件边与屏障**两套语义** · MUST NOT 混用）· `harness/features/B14F1_Checkpointer协议与MemorySaver.md`（跨 checkpoint 的屏障状态**归 B14F1**）· `harness/features/B7F2_compile编译.md`（**D-5** · 边表键类型放宽 ⇒ `compile()` **照原样透传** ⇒ MUST NOT 重建屏障语义）· `harness/features/B24F1_打包分发与兼容矩阵.md`（**D-6** · API 兼容矩阵 MUST 新增「**多源汇合边**」条目 ⇒ 宪法原则 X）各追加一条承接条款 ⇒ **只接线 · 逐条最小改动**
- [X] T082 [P] 下游接线 **D-7**：在 `harness/features/B19F1_TraceSink与current_span.md` 追加承接条款（「**屏障的触发**」这一可观察事实由 **B19F1** 在 trace 层**统一暴露** ⇒ 本 feature **零新增** span / trace / 结果字段 ⇒ **B19F1 MUST NOT** 期待本 feature 预先提供屏障分组信息）⇒ **只接线 · 逐条最小改动**（**FR-022** · 裁定 18 · **M3**）
- [X] T068 [P] 口径对账：**最小改动**补注记（**不改写**原描述）于 ① `harness/features/README.md` 的 B7F4 行 ② `harness/features/B7F4_多源汇合边与屏障.md` —— 二者现写着「**所有**源跑完后才被触发」，比澄清轮 **C-Q1** 的口径（**组内全 · 组间任一**）**更窄** ⇒ ⇒ 补一行**注记**说明拍板后的口径 ⇒ ⚠️ **上位文档 `harness/proposals/立项书.md` §5.2 的同一处 MUST NOT 由本 feature 代改** ⇒ 由 **T080** 登记（**只登记不代改**）
- [X] T069 核对**不越界** ⇒ **X-03**（`defer=True` 专用屏障 · **已知不支持** · 承接方 **B6F1**）：确认**未**实现 `defer=True` 专用屏障 · **未**实现跨 checkpoint 持久化 · **未**实现条件边路由 · **未**实现构建器接线 · **未**实现编译层屏障语义（**D-5**）· **未**改兼容矩阵（**D-6**）（FR-016）⇒ 逐条核对 `src/freegraph/runtime/superstep.py` 与 `src/freegraph/runtime/__init__.py`
  ⇒ ⇒ **另**核对：**多源边的 `__end__` 目标 ⇒ 显式失败**（**V-16** · **X-04**）与**边键类型非法 ⇒ `TypeError`**（**FR-021**）**均已落地且只落地这两条**（⇒ 无**额外**失败信号）
  ⇒ ⇒ **另**核对：**可观测面零新增**（**FR-022** · 裁定 18）⇒ 未新增 span / trace / 结果字段 ⇒ 「屏障的触发」的可观察出口**未**在本 feature 自造 ⇒ ⇒ **只**由 **B19F1** 承接（**D-7** · **T082**）
- [X] T070 **【阻断合入】门禁项偏离登记** ⇒ **A10** · 登记项 **PR-5**（宪法 **v1.6.0** · 登记项 **PR-5** · FR-019 · SC-009）：把「门禁 **3**（固定脚本原样可跑）/ **4**（fake 模型跑通验收基线一轮）/ **5**（人工记录含真实模型一轮）在本 feature **物理不可达成**」**如实登记**进 `harness/verification/B7F4/manual-verification.md` 的「**遗留问题**」段 ⇒ ① **被偏离的门禁项**逐条点名 ② **根因**（本 feature 按里程碑**只交付 L2** ⇒ `StateGraph` / `compile()` / `invoke()` 未落地 ⇒ **无图可跑** · 取证见 **T008**）③ **判据未被放宽**的论证（三条门禁的判据**一字未改** ⇒ **MUST NOT** 伪装成「已通过」⇒ **MUST NOT** 写一条**永久红**的 CI）④ **承接方** = **B6F1 / B7F3**（构建器 + invoke · M2）· **B25F1**（双跑验收 · M4）⑤ 落点 = 本 task + 人工验证记录 ⇒ ⇒ **并入 T065 的同一次追认**（追认次数仍 == **1**）
  ⇒ ⇒ ⚠️ **追加（澄清轮 C-Q19 · 发起者 2026-11-13 拍板）**：**另须登记门禁 7**（文档合规门禁）的
  「**API 兼容矩阵已更新**」这一部分 ⇒ **物理不可达成**（**根因**：兼容矩阵**尚未落库** ⇒ 首次落库属
  **B24F1 / M4** ⇒ 本 feature 按里程碑**不交付其前置能力** · 取证见 **T008**）⇒ ⑥ **承接方** =
  **B24F1 / M4**（已有下游承接 **D-6**）⇒ ⇒ 该门禁判据**一字不改** ⇒ ⇒ **MUST NOT** 写**永久红**的 CI
  ⇒ ⇒ **并入 T065 的同一次追认**（**追认次数仍 == 1** · **零新增登记项** · **零新增**门禁编号）

**Checkpoint**: **R-1…R-10 逐条落全** + **追认文字已落盘**（含 **PR-5** 的门禁偏离登记）⇒ **破冻结面的代价已付** ⇒ 可进入 Phase 7。

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 机械层一键验收 + 全量回归 + 门禁核对 + 遗留问题登记

- [X] T075 [P] 写 `harness/verification/B7F4/acceptance.py`：**机械层**一键跑完 **A1**（多源边可表达）· **A2**（屏障语义正确）· **A3**（差分场景全绿）· **A4**（既有断言零削弱）· **A5**（追认文字在位）· **A6**（导出面 == 20）· **A7**（回溯修订逐条命中）· **A8**（形态校验生效）· **A9**（参数化场景 **D-24** 全绿）· **A10**（门禁偏离已登记）⇒ 每条断言**复用既有判据的同一口径** ⇒ **零新增门禁编号**（research **DR-12** · `harness/verification/README.md` 的「判据能否脱离 pytest 单独跑成一段脚本」判据）
- [X] T076 [P] 跑 `.venv/bin/python -m pytest tests/ -v` ⇒ **A6** · SC-006 / SC-010 · **M-9** ⇒ **全绿**；并核对 `freegraph.runtime.__all__` == **20** · `freegraph.contracts.__all__` == **20** ⇒ **零新增导出符号 / 零新增通道类型**（SC-006 / SC-010 · **M-9**）
- [X] T077 门禁核对 ⇒ SC-007 · **M-10** / **M-11**：① **门禁编号守卫** ⇒ 跑既有守卫测试 `.venv/bin/python -m pytest tests/runtime/test_superstep_concurrency.py tests/runtime/test_parse_contract.py -v`（**G1–G30 连续无跳号 · 总数 == 30** 的断言在这两个文件里）⇒ **零新增** · **M-10**；② 门禁脚本 ⇒ `.venv/bin/python -m pytest tests/gates/ -v`（⚠️ `harness/scripts/gates/` 是**目录** ⇒ **不可**用 `python <目录>` 直接执行；该目录**只含 G21–G30**）⇒ **G1–G30** 的连续性由 ① 的守卫测试判定；③ 层注册表零改动 · 零出站 · 零环境变量（SC-007 · FR-009…FR-011 · **M-11**）
- [X] T078 跑 `specs/b7f4-multisource-join/quickstart.md` 的**全部场景**（§1 冒烟 + §2 的 **A1…A10**）⇒ **逐条命中** ⇒ 把实际输出贴进 `harness/verification/B7F4/manual-verification.md` 的「实际输出」段
- [X] T079 [P] 跑 `.venv/bin/python harness/verification/B7F4/acceptance.py` ⇒ **全绿**（机械层一键验收的首次实跑证据 ⇒ 贴进人工验证记录）
- [X] T080 登记**遗留问题**：在 `harness/verification/B7F4/manual-verification.md` 的「遗留问题」段逐条登记（如「立项书 §5.2 的 **620 行 / 3 人日** 与本 feature 的**实际规模**（**78** 条任务）**体量口径不同** ⇒ **MUST 由发起者**在 feature 收尾时重估回写」·「**立项书 §5.2** 与 `harness/features/README.md` 的 B7F4 描述仍写「所有源跑完后才被触发」（比澄清轮 **C-Q1** 的口径窄）⇒ **只登记不代改** · **MUST** 由**发起者**回写」·「**API 兼容矩阵**尚未落库 ⇒ 「多源汇合边」条目归 **B24F1**（**D-6**）⇒ 本 feature **未**代改 ⇒ ⇒ **门禁 7** 的「**兼容矩阵已更新**」在本 feature **物理不可达成** ⇒ 已按 **PR-5** 如实登记（澄清轮 **C-Q19**）」⇒ **可审计**）

**Checkpoint**: 全部门禁与判据**全绿** + 人工验证记录**五段式齐全且含追认** ⇒ **可合入**。

---

## Dependencies & Execution Order

### 执行闸口（Phase 闸口 · 每道 MUST 全绿才进下一 Phase）

| 闸口 | 判据 | 任务 |
|---|---|---|
| **G-a** | 四条基线已落盘（断言条数 / **10 个冻结断言文件** / 导出面 / 差分场景数）+ 门禁不可达成取证已落盘（**含门禁 7**）+ **下游承接 D-1…D-7 的现状**已落盘 | T001 · T002 · T003 · **T004** · T007 · T008 |
| **G-b** | 骨架后**既有** `tests/runtime/` **全绿** 且 **10 个**冻结断言文件的 **diff 全为空**（`git diff HEAD --stat`） | T015 |
| **G-c** | US1 用例**全绿**（多源边可表达 + 屏障目标晚于所有源） | T029 |
| **G-d** | US2 用例**全绿**（不齐 ⇒ 静默等待 · 后齐 ⇒ 再触发一次 · 同一轮至多一次 · **形态校验** · **源重复** · **环图**） | T038 · T039 · **T037** · **T086** · **T087** |
| **G-e** | 差分场景 **D-16…D-28 全绿**（上游缺席即 skip）· 判词分布 = **SAME 11 条 + STRICTER 2 条**（**D-25 / D-26** 各带 `note`）· 既有 **30** 场景**逐字未变**（**三元组快照逐条相等** · C-02 基线 vs C-10 改动后） | T042…T054 · **T081** · **T083** · **T084** |
| **G-f** | **R-1…R-10 逐条落全**（含**契约守卫回归绿**：T085）+ **追认文字已落盘**（含 **PR-5** 的门禁偏离登记）+ **D-7 接线**落盘 ⇒ **未追认 MUST NOT 合入** | T055…T070 · **T082** · **T085** |
| **G-g** | 全量回归 + 门禁 + 一键验收**全绿** + 人工验证记录**五段式齐全** + 遗留问题已登记 | T075…T080 |

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 ⇒ 可立即开始
- **Foundational (Phase 2)**: 依赖 Phase 1 ⇒ **BLOCKS** 所有故事
- **User Stories (Phase 3–5)**: 全部依赖 Phase 2 ⇒ ⇒ 可**并行**（若人手允许）或按 **P1 → P2 → P3** 顺序
- **回溯修订与追认 (Phase 6)**: 依赖 **US1 + US2 + US3**（口径已定型 ⇒ ⇒ **PR-6** = **D-24** = **T050** · **PR-7** = **D-25** = **T053** ⇒ 二者均在 **US3 / Phase 5**）⇒ ⇒ **必须**在合入前完成
- **Polish (Phase 7)**: 依赖 Phase 3–6 全部完成

### User Story Dependencies

- **User Story 1 (P1)**: Phase 2 之后即可开始 ⇒ **不依赖**其它故事 ⇒ **MVP**
- **User Story 2 (P2)**: Phase 2 之后即可开始 ⇒ 依赖 US1 的**判定式**（组内全 · **T027**）但**不依赖** US1 的其它产出 ⇒ ⇒ **测试任务**（T030…T034 / T037 / T039 / T086 / T087）可与 US1 **并行** ⇒ ⇒ **实现任务**（**T035**）MUST 等 **T027** 落地 ⇒ ⇒ 与「MVP First」第 4 步（**不得**在 US1 绿之前进入 Phase 4）与「Parallel Team Strategy」第 3 条**同口径**
- **User Story 3 (P3)**: Phase 2 之后即可开始（夹具改动与场景落点**独立**）⇒ ⇒ **可与 US1 / US2 并行**（但**断言**依赖前两者的行为 ⇒ 跑时需前两者已绿）

### Within Each User Story

- **测试 MUST 先写 · MUST 先失败**（Phase 2 的骨架保证多源用例**必然红**）
- **判定式**（US1）→ **记账口径**（US2）→ **差分对跑**（US3）
- 故事完成后再进下一个优先级

### Parallel Opportunities

- Phase 1 的 **T003 / T004 / T005** 可并行；Phase 2 的 **T010 / T011** 可并行
- 同一故事内的**多条用例**可并行（**同一文件** ⇒ 建议**串行**写、并行跑）
- **T055…T061**（六处契约回溯修订 · **不同小节 / 不同文件**）可并行 ⇒ ⇒ **但 MUST 各自只增不改**（避免同文件并发写冲突 ⇒ 建议**同文件串行**、跨文件并行）
- **T066 / T067 / T068 / T082**（**四条**任务 · **七个**下游提示词初稿 · **不同文件**）可并行
- Phase 6 完成后，Phase 7 的 **T075 / T076** 可并行 ⇒ ⇒ ⚠️ **T079** 跑的是 **T075** 的产物 `acceptance.py` ⇒ ⇒ **T079 MUST 等 T075 落地**（**MUST NOT** 与 T075 并行）

---

## Parallel Example: User Story 1

```bash
# 用例先写（同一文件 ⇒ 建议串行写、并行跑）
Task: "在 tests/runtime/test_superstep_multisource.py 写「多源边可表达」用例"
Task: "在 tests/runtime/test_superstep_multisource.py 写「屏障目标严格晚于所有源」用例"
Task: "在 tests/runtime/test_superstep_multisource.py 写「屏障只满足一个源时不触发」用例"

# 实现（同一文件 ⇒ 严格按依赖串行）
Task: "T026 让 _trigger_groups 支持多源组（src/freegraph/runtime/superstep.py）"
Task: "T027 让 _satisfied_groups 的组内合取生效（src/freegraph/runtime/superstep.py）"
Task: "T028 让 _consume_versions 对多源组逐源各记一条（src/freegraph/runtime/superstep.py）"
```

## Parallel Example: Phase 6（回溯修订 · 跨文件）

```bash
# 不同文件 ⇒ 真并行
Task: "T055 回溯修订 B7F1 契约 §1 / §2.1（specs/b7f1-superstep-loop/contracts/superstep-contract.md）"
Task: "T060 回溯修订 B7F1 的 spec.md（specs/b7f1-superstep-loop/spec.md）"
Task: "T061 回溯修订 B7F1 的 data-model.md（specs/b7f1-superstep-loop/data-model.md）"
Task: "T066 下游接线 D-1（harness/features/B6F1_StateGraph构建器.md）"
Task: "T067 下游接线 D-2 / D-3 / D-4 / D-5 / D-6（harness/features/B7F3_*.md · B8F1_*.md · B14F1_*.md · B7F2_*.md · B24F1_*.md）"
```

---

## Implementation Strategy

### MVP First（仅 User Story 1）

1. 完成 Phase 1: Setup（基线取证）
2. 完成 Phase 2: Foundational（骨架 · 行为逐字不变）—— **G-b**
3. 完成 Phase 3: User Story 1 —— **G-c** ⇒ **STOP and VALIDATE**：独立跑 `tests/runtime/test_superstep_multisource.py` 的 US1 四条用例
4. **不得**在 US1 绿之前进入 Phase 4（消费口径的改动**依赖**判定式已定型）

### Incremental Delivery

1. Phase 1 + 2 ⇒ 骨架就位（**行为零变化** ⇒ **零风险**）
2. US1 ⇒ 多源边**可表达** + 屏障**基本语义** ⇒ **MVP**
3. US2 ⇒ **静默等待** + **消费口径**（后齐再触发）
4. US3 ⇒ **差分可判定**（与上游同款）+ **D-24 参数化增量**
5. Phase 6 ⇒ **回溯修订 + 追认（含 PR-5 的门禁偏离登记）** ⇒ **合入闸口**
6. Phase 7 ⇒ 一键验收 + 全量回归 + 门禁 + 遗留登记

### Parallel Team Strategy

1. 团队一起完成 Phase 1 + 2（骨架 ⇒ 行为零变化 ⇒ 零风险）
2. Phase 2 之后：
   - 开发甲：**US1**（`superstep.py` 的判定式）
   - 乙：**US3**（`tests/differential/parity_probe.py` 的夹具 + 场景 ⇒ **不同文件**）
   - 丙：**Phase 6 的跨文件回溯修订**（`specs/b7f1-superstep-loop/spec.md` · `data-model.md` · `harness/features/*`）
3. ⚠️ **US2 的实现**（`superstep.py` 的 `_consume_versions`）MUST 等 **US1** 的判定式落地 ⇒ ⇒ **US2 由同一人接手**（或串行）
4. 汇合 ⇒ Phase 6 的追认（含 PR-5）+ Phase 7 的验收

---

## Notes

- ⚠️ **编号消歧（十套编号 · 互不撞名）**：**R-1…R-10**（回溯修订清单）· **D-16…D-28**（差分场景 · **全局序列**）·
  **X-01…X-04**（偏离登记）· **PR-1…PR-8**（plan 登记项 · **8 项** · 澄清轮 **C-Q13**）· **T001…T087**（**本文件的任务号**）·
  **P-01…P-16**（上游对照语义点）· **E-1…E-11**（上游实测）· **M-1…M-16**（不变量）·
  **DR-1…DR-13**（research 决策）· **裁定 1…18**（spec 裁定）
  ⇒ ⇒ ⚠️ **回溯修订清单的 `R-n` ≠ B12F1 在 B7F1 文件里留下的「B12F1 回溯修订 T-n」标记**
  ⇒ ⇒ ⚠️ **差分场景编号 = 全局序列**：**B12F1 已占用 `D-01…D-15`** ⇒ ⇒ 本 feature 的场景编号 =
  ⇒ ⇒ **`D-16…D-28`** ⇒ ⇒ **新 feature MUST 继续沿全局序列续编**（MUST NOT 从 `D-01` 重新起编）
  ⇒ ⇒ 引用时 MUST 写全。
- ⚠️ **任务号 = 稳定标识符**（**不是行序**）⇒ ⇒ **T053 / T054**（新增的 **D-25 / D-26** 两个
  差分场景）排在 **Tests 段内**（编号在 **T051 / T052** 之后是**追加**所致 · 非笔误）⇒ ⇒
  ⇒ **T081**（新增的 **D-27** 场景）同理 ⇒ ⇒ **T084**（新增的 **D-28** 场景 · 澄清轮 **C-Q14**）同理
  ⇒ ⇒ **T039**（「同一轮内至多触发一次」的用例）与 **T037**（「多源边的形态校验」用例）
  排在 Phase 4 的 **Implementation 段内**（**编号在 T038 之后** ⇒ 是**追加**所致 · 非笔误
  ⇒ 但二者**仍是**一条**测试任务** ⇒ **MUST 在 T038 之前完成**）
  ⇒ ⇒ **行序 ≈ 执行顺序**（测试 MUST 先写 ⇒ 测试任务**原则上**在实现任务之前；
  ⚠️ **T037 / T039** 两条按「追加」排在 Implementation 段内 ⇒ ⇒ 二者 MUST 在其依赖的实现任务之前完成）
  ⇒ ⇒ **T083 / T084 / T085** 是**分析轮第三轮**新增的三条（**C-10** 核对 · **D-28** 场景 · **契约守卫回归**）⇒ ⇒ 同样按「追加」排位。
  ⇒ ⇒ **T086 / T087** 是**分析轮第四轮**新增的两条（**源重复**去重 · **环图** ⇒ **C-Q20**）⇒ ⇒
  同样按「追加」排在**末尾编号**（但**位置**在 Phase 4 的 **Tests 段**内 ⇒ 属**测试任务**
  ⇒ ⇒ **MUST 在 T038 之前完成**）⇒ ⇒ **任务总数 76 → 78**。
- [P] 任务 = 不同文件 / 无未完成依赖（**同一文件的改动一律串行** ⇒ 避免合并冲突）
- [Story] 标签映射到 spec 的用户故事（US1–US3）⇒ 可追溯
- **每条任务的判据出处 MUST 写进任务描述**（FR / SC / 不变量 M-n / 裁定 / 实测 E-n）⇒ 避免实现期自由发挥
- **「先红后绿」**由 Phase 2 的骨架保证（多源边在运行期**仍被拒**）
- **「拆分而不删」**：回溯修订**只增不改** ⇒ 每处改完 MUST 核对「既有内容逐字保留」
- **追认未落盘 ⇒ MUST NOT 合入**（Phase 6 的 **G-f** 闸口）⇒ **八项打包成一次**（PR-1…PR-8 · 澄清轮 **C-Q13**）
- **上位文档（立项书）MUST NOT 由本 feature 代改** ⇒ **只登记不代改**（T080）
- 提交粒度：**每条任务或每个逻辑组**一次提交 ⇒ 每条提交都 MUST 通过 `pytest tests/`
- 遇到与 spec 冲突 ⇒ **以 spec 为准** ⇒ 回修实现 + 在 `research.md` 记一行

---

## 附录 · 任务 ↔ spec 追溯表

### FR → 任务

| FR | 任务 |
|---|---|
| FR-001 | T010 · T020 · T024 |
| FR-002 | T025 · T037 |
| FR-003 | T023 · T026 · T027 · T033 |
| FR-004 | T028 · T032 · T035 |
| FR-005 | T041 … T051 · T053 · T054 · **T081** · **T084** |
| FR-006 | T076（+ T012 的「不新增类型」纪律） |
| FR-007 | T036 |
| FR-008 | T036 |
| FR-009 | T077 |
| FR-010 | T077 |
| FR-011 | T077 |
| FR-012 | T064 · T065 |
| FR-013 | T055 … T063 |
| FR-014 | T052 |
| FR-015 | T064 · T078 |
| FR-016 | T069 |
| FR-017 | T024 · T037 |
| FR-018 | T040 · T041 · T048 · T003 · **T083** |
| FR-019 | T008 · T070 · T080 |
| FR-020 | T050 |
| FR-021 | T024 · T037 · **T084** |
| FR-022 | T069 · **T082** |

### SC → 任务

| SC | 任务 |
|---|---|
| SC-001 | T021 · T022 · T023 · T029 |
| SC-002 | T030 · T031 · T038 |
| SC-003 | T032 · T035 · T039 |
| SC-004 | T041 … T051 · T053 · T054 · **T081** · **T084** |
| SC-005 | T001 · T007 · T015 · T036 · T062 · **T085** |
| SC-006 | T076 |
| SC-007 | T077 |
| SC-008 | T027 · T037 · **T086** · **T087** · T055 … T063 · **T085** |
| SC-009 | T064 · T065 · T070 |
| SC-010 | T036 · T076 |
| SC-011 | T050 · T051 · T053 · T054 · T081 · **T083** · **T084** · T075 · T076 |
| SC-012 | T052 |
| SC-013 | T050 · T075 |

### 承接条款 / 偏离登记 → 任务

| 项 | 任务 |
|---|---|
| **H-1** · **H-2** · **H-3** · **H-4** · **H-5** · **H-6** | T012 · T014 · T020 … T030 · T036 · T046 · T050 · T055 … T061 |
| **D-7**（→ **B19F1**） | **T082** |
| **X-01** · **X-02** · **X-03** · **X-04** | T024 · T037 · T053 · T054 · T055 … T063 · T065 · T069 |
| **PR-1** … **PR-8** | T065（**八项打包成一次**的追认）· T070（**PR-5** 的登记 · **含门禁 7** · C-Q19）· T050（**PR-6** 的增量）· T053 / T054（**PR-7** 的 D-25）· T024 / T037 / **T084**（**PR-8** 的 `TypeError` · 差分 **D-28**）· **T082**（**PR-4** 的 D-7 接线） |

### 任务 → FR（反向覆盖 · 每条任务至少挂一条判据）

| 任务 | 挂靠 |
|---|---|
| T001–T008 | SC-005 · SC-006 · SC-007 · FR-019（**基线取证** + **门禁不可达成**取证）<br>⚠️ 逐条细化：**T004** → **PR-4**（下游承接 **D-1…D-7** 的现状核对）· **T006** → **FR-013 / R-1…R-6**（B7F1 契约的逐条落点）· 其余 → 基线取证 |
| T010–T015 | FR-001 · SC-005（**骨架 · 行为逐字不变**） |
| T020–T029 | FR-001 · FR-002 · FR-003 · FR-017 · SC-001 · SC-008（**US1**） |
| T030–T039 · **T086–T087** | FR-003 · FR-004 · FR-007 · FR-008 · SC-002 · SC-003 · SC-008 · SC-010（**US2**） |
| T040–T054 · **T081** | FR-005 · FR-014 · FR-018 · FR-020 · SC-004 · SC-011 · SC-012 · SC-013（**US3**） |
| T055–T070 · **T082** | FR-012 · FR-013 · FR-015 · FR-016 · FR-019 · **FR-022** · SC-008 · SC-009 · SC-011（**回溯修订与追认** + **D-7 接线**） |
| **T083–T085** | FR-018 · FR-021 · SC-004 · SC-005 · SC-008 · SC-011（**分析轮第三轮**新增：**C-10** 核对 + **D-28** + 契约守卫回归） |
| T075–T080 | FR-005 · FR-006 · FR-009 · FR-010 · FR-011 · FR-019 · SC-006 · SC-007 · SC-011（**Polish**） |
