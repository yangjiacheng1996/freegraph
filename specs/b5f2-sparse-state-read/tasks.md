---

description: "B5F2 · 稀疏状态读取（C4 独立回归测试）+ 差分测试夹具建立 —— 任务清单"
---

# Tasks: B5F2 · 稀疏状态读取（C4 独立回归测试）+ 差分测试夹具建立

**Input**: Design documents from `/specs/b5f2-sparse-state-read/`

**Prerequisites**:
- `plan.md`（必读 · 含 **Constitution Check** 与**三个登记项**（**R-1** 宪法门禁 3/4/5 的偏离登记 ·
  **R-2** CI 矩阵契约的修订需求 · 选定「**方案 α′** = 既有作业内的**新增独立步骤 5.6**」·
  **R-3** **既有 B4F1 依赖判据的取样范围拆分**（定性 = 取样范围 bug 修复 · **无需宪法修订**）· 需发起者追认）·
  **Structure Decision**（`read.py` 与 `channel.py`
  分离的理由 · C4 断言住 `tests/runtime/` 的理由 · `tests/runtime/` 既有文件的**零改动例外**）·
  **设计后复核**）
- `spec.md`（必读 · 含 **33 条裁定** + **28 条澄清问答 Q1–Q28** · FR-001 ~ FR-038 · SC-001 ~ SC-033 ·
  需求 ↔ SC **追溯表 38 行** · ⚠️ 其中 **裁定 22 / 裁定 3 / 裁定 14 / SC-027** 已在 Phase 0 被**上游实测更正**（research §3 的 C-1…C-5）·
  ⚠️ **裁定 32**（2026-11-10 分析轮）= **新增 `SC-032`** + **扩写 `FR-027`** + **`FR-037` ④ 可判定化**）
- `research.md`（必读 · **18 条决策 D-01…D-18**（全部附**实测输出**）· **5 条遗留登记 DR-1…DR-5** ·
  **5 条事实更正 C-1…C-5**）
- `data-model.md`（必读 · 5 类实体 · **fresh 读的 8 格状态机** · 8 条校验规则 · **不变量 I-1…I-11 的唯一权威
  在 `contracts/read-contract.md` §4**）
- `contracts/read-contract.md`（**读取契约的唯一权威** · `<!-- authority: yes -->` · §4 的 **I-1…I-11**
  MUST 逐条被解析并断言）
- `contracts/differential-fixture.md`（**差分夹具契约的唯一权威** · 图规格形态 / 三项投影 / 归一化 /
  判定 / **不进入比对的范围**）
- `contracts/upstream-parity.md`（与上游 LangGraph 的**逐条对照** · **12 条**〔**10 条**带 `路径:行号` +
  **2 条**带实测编号 · 其中 **P-12** 的上游侧**待实测** · tasks T044〕+ §2 的**实测基线**）
- `quickstart.md`（**可照抄**的验证手册 · 12 节 · 验收闸口 **V1–V12**）

**Tests**: **含**测试任务 —— 本 feature 的成功标准**全部**以断言形式给出（SC-001…SC-033），
且 spec **强制**要求：① **否定式**的 C4 回归（FR-012 · SC-001 / SC-002）；
② 行 / 分支覆盖 **100%**（FR-027 · SC-018）；③ **契约守卫**解析 `read-contract.md` 的 **I-1…I-11** 并
**逐条**断言（FR-027 · 裁定 32 ② · **MUST NOT** 只测行为而不校验契约文本）；
④ **差分夹具**（FR-014 ~ FR-017）；⑤ **零副作用**的子进程断言（FR-020 / FR-023）
⇒ 测试是**交付面的一部分**，不是可选项。

**Organization**: 任务按用户故事分组，每个故事可**独立实现、独立测试、独立交付**。

**本 feature 的可测判据总表**（**38 FR + 33 SC ↔ 50 条任务**）：
追溯见文末「**附录 · 任务 ↔ spec 追溯表」——
**每个 FR 与每个 SC 均至少被一条任务映射**（**FR 38/38 · SC 33/33**）·
**反向**：**每条任务**携带的义务 MUST 挂上**至少一条 FR**（⇒ 任务级追溯表**双向**齐全 · 裁定 32 ②）。
其中 **SC-001 / SC-002**（C4 的两条否定式断言）由 **T011** 承载，
**SC-006 / SC-007 / SC-032**（差分的输出状态 / 事件序列 / **节点入参**）由 **T020 / T021 / T046** 承载，
**SC-008**（A5 · `Requires-Dist` 为空）由 **T001 / T030** 承载，
**SC-014**（差分夹具的**真实执行**次数 ≥ 1）由 **T035** 承载，
**SC-017**（差分夹具的**纯本地节点**）由 **T009** 承载（前置校验），
**SC-028**（事件口径的实测与冻结）由 **T020 / T021** 承载，
**SC-030**（模型工厂钩子 · 恒空 ⇒ 非空即显式失败 + B25F1 承接条款）由 **T009 / T019 / T039** 承载，
**SC-031**（既有依赖判据的**取样范围拆分** · 红线未放宽）由 **T041 / T042** 承载（**④** 由 **A7** 闸口验收 · 裁定 28），
**SC-033**（两个稀疏入口 MUST 逐字相等 · 裁定 33 ④）由 **T013 / T028** 承载，
**T037 / T038 / T043 / T049**（**发起者追认** · 登记项 R-1 / R-2 / R-3 / **R-4**）是**阻断合入**的任务。

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可并行（**不同文件**且无未完成依赖）——同一文件内的后续任务**不标** `[P]`
- **[Story]**：所属用户故事（US1…US5）；Setup / Foundational / Polish 阶段**不标**
- 每条任务都带**确切文件路径**；冻结面的**逐字内容**在 `contracts/` 与 `data-model.md` 中，
  本文件**只引用不复制**
- **逐条追溯**：每条任务对应的 **FR / SC** 见文末「**附录 · 任务 ↔ spec 追溯表**」
  （宪法原则 VI：「tasks MUST 逐条勾选、**可追溯到 spec 条目**」）

## Path Conventions

- 内核实现：`src/freegraph/runtime/`（**L2 执行内核层** · 层注册表**已登记**）
  - `read.py`（★ 新建 · `read_channels` + `local_read` —— **状态读取的唯一实现点**）
  - `__init__.py`（★ 追加导出 · L2 内部 API **12 → 14** 个符号 · **不是**公开门面）
  - `channel.py` / `mapping.py` / `errors.py` / `schema.py` / `reducer.py`（既有 · **零改动**）
- 测试：
  - `tests/runtime/`（与既有 `tests/contracts/` · `tests/facade/` · `tests/gates/` **平级** ·
    **自带** `__init__.py`）—— **五个**新测试模块：
    `test_read_c4_sparse_state.py`（**C4 独立回归** · 否定式断言）·
    `test_read_semantics.py`（稀疏语义 · 结果形态 · 顺序）·
    `test_read_fresh.py`（fresh 读 · 副本 · **绑定与可用性判定的零污染**）·
    `test_read_purity.py`（零副作用 · 副本纯净）·
    `test_read_contract.py`（**契约守卫** · 解析 `read-contract.md`）
    ⚠️ **既有文件的唯一例外**：`tests/runtime/test_parse_contract.py` 的**两条依赖判据**
    MUST 按登记项 **R-3** **拆分取样范围**（**T041 / T042** · FR-037 · 裁定 27）—— **原断言一条未放宽**。
  - `tests/differential/`（★ 新建包 · **测试侧** · **MUST NOT** 进 `src/`）——
    `__init__.py` · `conftest.py`（`langgraph` 缺席 ⇒ skip）· `spec_builder.py`（图规格 ⇒ `TypedDict`）·
    `driver.py`（freegraph 侧的**规格驱动器**）· `runner.py`（两侧执行 + 三项投影 + 判定）·
    `test_differential.py`
  - `tests/contracts/test_contract_regressions.py`（既有 · **仅**改 C4 标记与元测试 · ⚠️ **MUST NOT**
    import `freegraph.*` ⇒ 门禁 **G2**）
- 人工记录：`harness/verification/B5F2/manual-verification.md`（★ 新建 · 五段式 + 来源覆盖表）
- 配置：`pyproject.toml`（★ `[dependency-groups] differential`）· `.github/workflows/ci.yml`（★ 步骤 **5.6** · **既有作业内的专门步骤**）
- **冻结面 / 上位文档的最小修订**（**四处** · 只接线 · 逐条最小改动）：
  - `specs/b3f1-scaffold-ci-gates/contracts/ci-matrix.md`（★ 步骤 5.6 行 + 位置约束 + §2.1 修订记录 · **T036** · 登记项 **R-2**）
  - `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md`（★ **G29 判定 3** 的**两态**口径 + `landed` 语义 · **T048** · 登记项 **R-4** · **判定代码零改动**）
  - `harness/scripts/gates/gate_G29_contract_carrier.py`（★ **docstring 第 3 点** 与契约文本同步 · **T048** · **判定代码零改动**）
  - `harness/proposals/立项书.md`（★ §4.2 S5 / §5.2 B5F2 行 / §9.2 落点 · **T047** · 裁定 33 ③ · **只接线**）

> **📌 两条全局口径（2026-11-10 · 分析轮补登记 · 写在最前以免被漏）**：
> ① **跑测试的命令 MUST 与 CI 逐字同款** —— `uv run --no-project --python .venv python -m pytest …`
>   （`--no-project` **不可省** ⇒ 避免 uv **同步环境**把手工装入的 `differential` 组**卸掉**
>   ⇒ 否则差分用例**全 skip** ⇒ **假绿** · plan R-2 风险 ⑤）。
> ② **「零污染」口径（= 绑定与可用性判定）的唯一表述源** = `contracts/read-contract.md` §3.3 / §4（**I-5**）
>   ⇒ 本文件**只引用编号、不重述全文**（防措辞漂移 · 裁定 29 的成因）。

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 项目初始化与共享骨架

- [X] T001 [P] 在 `pyproject.toml` 新增 `[dependency-groups] differential = ["langgraph==1.2.11"]`（PEP 735 · **钉版本**与 `contracts/upstream-parity.md` 的核实版本一致 ⇒ 换版本 MUST 重新核实全部行号）—— **MUST NOT** 写进 `[project].dependencies` / `[project.optional-dependencies]`（宪法 v1.7.0 禁止 v1.0 含 extra）⇒ `Requires-Dist` 保持为空集
  · ⚠️ **依赖顺序（2026-11-10 · 分析轮第二轮）**：本任务 MUST **在 `T006` 之后执行**（`T006` 要取
  **实现前绿基线** ⇒ 本任务一落地，既有判据
  `test_dependency_declarations_contain_no_upstream_package`（取样范围含 `[dependency-groups]`）
  **立刻变红** ⇒ 基线将**不是绿**）⇒ 两个任务**仍可并行起草**、但**执行有先后**
- [X] T002 [P] 新建 `src/freegraph/runtime/read.py` 骨架：署名头（`# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph`）+ 模块 docstring 为**首个语句** + `__all__ = ["read_channels", "local_read"]`；**只依赖标准库**（`collections.abc` / `copy`）⇒ MUST NOT import `langchain*` / `langgraph*` / `langsmith` / `pydantic` / `typing_extensions`
- [X] T003 [P] 在 `src/freegraph/runtime/__init__.py` 追加导出 `read_channels` 与 `local_read`（**12 → 14** 个符号）—— `freegraph.runtime` 仍是 **L2 内部 API**，MUST NOT 进 `freegraph.contracts`（18 符号）或 `freegraph.graph`（7 符号）⇒ 顶层包惰性（G1）恒成立
- [X] T004 [P] 新建五个测试模块骨架：`tests/runtime/test_read_c4_sparse_state.py` · `tests/runtime/test_read_semantics.py` · `tests/runtime/test_read_fresh.py` · `tests/runtime/test_read_purity.py` · `tests/runtime/test_read_contract.py`（各带署名头 + docstring 首个语句 + 既有 `tests/runtime/__init__.py` **零改动**）
- [X] T005 [P] 新建 `tests/differential/` 包：`__init__.py` · `conftest.py` · `spec_builder.py` · `driver.py` · `runner.py` · `test_differential.py`（各带署名头 + docstring 首个语句）
- [X] T006 新建 `harness/verification/B5F2/manual-verification.md` 骨架（五段式：① 验证环境 · ② 逐条判据的实测输出 · ③ 与上游的逐条对照 · ④ 未实跑项 · ⑤ 来源覆盖表）+ 取**实现前绿基线**：`uv run --no-project --python .venv python -m pytest tests/ -ra` 的输出 + `python -c "import importlib.metadata as m; print(m.requires('freegraph') or [])"` 的输出（⇒ 基线 = `[]`）—— ⚠️ **MUST** 用 `--no-project` 口径（与 CI 逐字同款 · 见 Path Conventions 的全局口径 ①）
  · ⚠️ **依赖顺序（2026-11-10 · 分析轮第二轮）**：本任务 MUST **先于 `T001` 执行**（取**绿**基线）⇒
  `T001` 依赖本任务（`T001` 一落地 `differential` 组，既有判据
  `test_dependency_declarations_contain_no_upstream_package` 的取样范围含 `[dependency-groups]`
  ⇒ **立刻变红** ⇒ 若 `T001` 先跑，本任务采到的**不是绿基线**）⇒ 两个任务**仍可并行起草**、但**执行有先后**

---

## Phase 2: Foundational（阻塞性前置）

**Purpose**: 阻塞全部用户故事的共同底座

**⚠️ CRITICAL**: 任何用户故事的工作 MUST 在本 Phase 完成前开始

- [X] T007 在 `src/freegraph/runtime/read.py` 实现两个入口的**签名与入参形态校验**（`read_channels(channels: Mapping[str, Channel], *, skip_empty: bool = True)` · `local_read(channels: Mapping[str, Channel], writes: Mapping[str, Sequence[Any]], *, fresh: bool = False)`；入参非映射 ⇒ 抛 `TypeError`）—— **行为**留待各故事实现（US1 填稀疏读 · US4 填 fresh 读）
- [X] T008 [P] 在 `tests/differential/conftest.py` 实现「`langgraph` **缺席 ⇒ skip**」的夹具（`pytest.importorskip("langgraph")`）—— MUST **标记跳过**而非失败（FR-019 · 裁定 11）
  · ⚠️ **导入 MUST 在夹具函数体内**（延迟到用例实际运行时才 import）· MUST **NOT** 置于 conftest **模块级** —— 否则上游及其传递依赖（`langchain-core` → `langsmith`）会被导入**共享 pytest 进程** ⇒ 污染同进程的 `sys.modules` 观测（仓库既有教训：`tests/contracts/test_architecture.py:29`「同进程 `sys.modules` 不可作依据」）
- [X] T009 [P] 在 `tests/differential/spec_builder.py` 实现**图规格的前置校验**（**只做不依赖 schema 的那部分** · 2026-11-10 分析轮拆分）：`conditional_edges` **必须为空** ⇒ 非空即显式失败 · `model_factory`（模型工厂钩子）**必须为空** ⇒ 非空即显式失败（**判定方**归本任务 · **字段的定义**归 **T019** · FR-036 · SC-030 · 裁定 26）· 节点名**唯一** · 节点函数**确定性**且零网络的提示 —— 依据 `contracts/differential-fixture.md` §2 / §5（FR-036 · SC-030 · 裁定 26）
  · ⚠️ **职责边界（2026-11-10 · 分析轮）**：**依赖 schema 的校验**（节点返回的 key 必须在 schema 里 · 初始输入含 schema 外的 key ⇒ 显式失败 · 字段描述的值类型不可解析 / 缺值类型 ⇒ 显式失败）**MUST NOT** 在本任务实现 ⇒ 它们**随 schema 的构造**落在 **T019**（schema 由 `T019` 构造 ⇒ 本任务 Phase 2 **无** schema 可依 ⇒ 避免 Phase 倒置）
- [X] T010 [P] 核对**冻结面**并把结论记入 `harness/verification/B5F2/manual-verification.md`：`freegraph.runtime.__all__` == **14** · `freegraph.contracts.__all__` == **18** · `freegraph.graph.__all__` == **7** · API 兼容矩阵**零新增行** · `THIRD_PARTY_NOTICES` **零改动** · 层注册表 `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` **零改动**
- [X] T041 **拆分取样范围**（`tests/runtime/test_parse_contract.py::test_dependency_declarations_contain_no_upstream_package`）：**发行面部分逐字保留** —— `[project].dependencies` 的**零上游**断言**一字不动**（MUST NOT 删 / 弱化）；`[project].optional-dependencies]`（extra）本仓库 v1.0 **不存在**（宪法 v1.7.0）⇒ 天然为零；对 **`[dependency-groups]`** 改**正向枚举** —— 含上游包名的组 == **恰好 1 个**且为 `differential`，且该组 MUST **NOT** 进 `Requires-Dist`（判据 **A5**）⇒ **MUST NOT** 以「删断言 / 放宽断言」的方式消除红灯（裁定 27 · FR-037 · 登记项 **R-3** · **取样范围 bug 修复** · **无需宪法修订**）
- [X] T042 **保留原断言 + 新增正向断言**（`tests/runtime/test_parse_contract.py::test_ci_workflow_never_installs_langgraph`）：原断言（**`ci.yml` 文本中 `langgraph` 字样 == 0**）**一字不动**（MUST NOT 删 / 弱化）**并新增**一条**正向断言** —— **可判定形式（裁定 32 ③）**：① `ci.yml` 中出现的**全部** `--group <X>` 的 `X` MUST ∈ {`dev`, `differential`}；② `pyproject.toml` 的 `differential` 组的内容 MUST == **恰好 1 个**上游包声明 ⇒ 上游**只许**经 `--group differential` 安装、**不得**出现在**发行依赖声明**与**基础安装步骤**中 ⇒ 判据**未放宽**、且**新增**一条可判定的正向约束（裁定 27 · 裁定 28 · FR-037 · 登记项 **R-3**）
  · ⚠️ **与原断言的相容性（2026-11-10 · 分析轮）**：① 与 ② 必须在「`ci.yml` 文本中 `langgraph` 字样 == 0」的**前提下**成立 ⇒ 新增步骤的**标题 / 注释**亦不得出现该字样（见 `T035`）⇒ 否则原断言变红 ⇒ **MUST NOT** 以「删 / 放宽断言」消除红灯

**Checkpoint**: 底座就位 —— 读取层可被 import、夹具骨架可被收集、图规格**前置校验（不依赖 schema 的那部分）**就位、冻结面已核对、**既有依赖判据已按 R-3 拆分取样范围** ⇒ 用户故事可开始

---

## Phase 3: User Story 1 - 空 key 不出现在节点入参里（Priority: P1）🎯 MVP

**Goal**: 节点收到的那个 `dict` **只含当前有值的 channel** —— 无值 channel 的 key **MUST NOT** 出现；
`.get(key, default)` 返回 **default** 而非 `None`。

**Independent Test**: 手写通道状态（一个已写入 + 一个从未写入）⇒ 走读取入口 ⇒
断言 `"llm_calls" not in node_input` 且 `node_input.get("llm_calls", 0) == 0` —— **不经由图执行**。

### Tests for User Story 1（MUST 先写 · MUST 先失败）

> **NOTE**: 先写这些测试，确认它们**先失败**，再实现

- [X] T011 [P] [US1] 在 `tests/runtime/test_read_c4_sparse_state.py` 写 **C4 独立回归测试**（**否定式**断言）：schema 用 `messages`（`Annotated[list, operator.add]`）+ `llm_calls`（无归约器）+ 一个从未写入的 key；断言 `type(node_input) is dict` 且 `"llm_calls" not in node_input` 且 `node_input.get("llm_calls", 0) == 0` —— **MUST NOT** 写成「节点入参包含所有 schema key」的宽松断言

### Implementation for User Story 1

- [X] T012 [US1] 在 `src/freegraph/runtime/read.py` 实现 `read_channels` 的**稀疏读**：按入参映射顺序遍历 · 以 `is_available()` 判定（**MUST NOT** 以捕获异常驱动控制流）· 无值通道的 key **MUST NOT** 出现在结果中 · 结果为**新建**的普通 `dict` · 值**按引用**（不深拷贝）
- [X] T013 [P] [US1] 在 `tests/runtime/test_read_semantics.py` 写稀疏语义用例：结果 key 集合 == 「`is_available()` 为真」的通道集合（I-1）· 「值为 `None`」的通道**出现**（I-10）· `skip_empty=False` 读到无值 ⇒ 抛 `EmptyChannelError`（其 `key` 指向该 key）· 省略 `skip_empty` 与显式 `skip_empty=True` 的结果**逐字相等**
  · **Edge Cases 补落（2026-11-10 · 分析轮）**：① **通道 key 为空串** ⇒ MUST 照常作为 `dict` 的一个 key 出现；② 映射里有**不在 schema 里**的 key ⇒ 读取层 MUST **照常读取**（读取层不做 schema 校验 —— 那是 B4F1 的职责）⇒ 该 key 若「无值」则在 `skip_empty=True` 下被跳过；③ `read_channels({})`（**空映射**）⇒ MUST 返回**空 `dict`**（**不是** `None`、**不**抛错）
- [X] T014 [US1] 在 `tests/contracts/test_contract_regressions.py` 把 `# GATE-MOUNT: C4 · status=not-landed` 改为 `status=landed`，并写一条**元测试**：以**路径扫描**确认 `tests/runtime/test_read_c4_sparse_state.py` 在位且被 pytest 收集 —— 该元测试 **MUST NOT** import `freegraph.*`（门禁 **G2** 扫描 `tests/contracts/**`）⇒ **MUST NOT** 改动 `GATE-MOUNT: C8`（仍属 B8F1）

**Checkpoint**: US1 可独立验证 —— C4 的两条否定式断言成立、稀疏语义成立、G29 显示「挂载点 C4：**已落地**」、G2 仍绿

---

## Phase 4: User Story 2 - 节点入参是普通 dict（Priority: P2）

**Goal**: 节点收到的第一个参数是**普通 `dict`** —— 不是自定义映射、不是属性对象。

**Independent Test**: 读取一次状态 ⇒ 断言 `type(result) is dict`；再断言结果里每个值与通道里的值**同一对象**。

### Tests for User Story 2（MUST 先写 · MUST 先失败）

- [X] T015 [US2] 在 `tests/runtime/test_read_semantics.py` 写**形态**用例：`type(result) is dict` **逐字**（MUST NOT 降级为「是 `dict` 的实例」）· 结果里的值与通道当前值**同一对象**（`is`）· 修改结果 `dict` 的**键集合****不影响**通道状态 · 结果 `dict` 的 key **顺序** == 入参映射顺序（过滤后 · I-2）—— ⚠️ **依赖顺序（2026-11-10 · 分析轮）**：本任务**写** `tests/runtime/test_read_semantics.py` ⇒ MUST **等 `T013`（同文件 · US1）完成后**再动 ⇒ **不标 `[P]`**

### Implementation for User Story 2

- [X] T016 [US2] 在 `src/freegraph/runtime/read.py` 固化三条口径（对照 `contracts/read-contract.md` §2.1）：结果 `dict` **必须新建**（MUST NOT 把内部映射交出去）· 值**按引用**（MUST NOT 深拷贝 —— 深拷贝会破坏对象身份且对不可拷贝对象会失败）· 结果 key **顺序** == 入参映射顺序
- [X] T017 [US2] 在 `tests/runtime/test_read_semantics.py` 追加**浅引用的已知面**用例：就地修改结果里的**值对象**（如 `result["messages"].append(x)`）**会**影响通道的当前值 —— 与上游**同构**（上游 `checkpoint()` 亦返回同一对象）⇒ **断言写明该行为**，MUST NOT 去修它（research **D-08** / **D-10** / **DR-4**）

**Checkpoint**: US1 与 US2 均可独立验证 —— 稀疏语义 + 结果形态同时成立

---

## Phase 5: User Story 3 - 与 LangGraph 的行为可逐项比对（Priority: P3）

**Goal**: 一套**可复用的差分夹具** —— 同一份图规格分别在 `langgraph` 与 `freegraph` 上执行，
比对**节点入参**、**输出状态**、**事件序列**三项投影。

**Independent Test**: 准备一份「有归约器 + 无归约器 + 空 key」混合的图规格 ⇒ 跑差分夹具 ⇒
三项投影的差异 == **0**；`langgraph` 缺席时该用例被**标记跳过**而非失败。

### Tests for User Story 3（MUST 先写 · MUST 先失败）

- [X] T018 [P] [US3] 在 `tests/differential/test_differential.py` 写差分用例：一份**混合** schema 的图规格（**有归约器** + **无归约器** + **空 key** 三者同时出现）⇒ 断言三项投影**逐项相等**；`langgraph` 缺席 ⇒ **skip**（不是 fail）

### Implementation for User Story 3

- [X] T019 [P] [US3] 在 `tests/differential/spec_builder.py` 实现**图规格 ⇒ 动态构造 `TypedDict`**：用 `typing.TypedDict("名称", {...})` 的**函数式**写法从**字段描述**构造出**一个**真的 `TypedDict`（MUST NOT 用 `exec` / 动态求值）⇒ 两侧**消费同一个对象**（MUST NOT 各自构造）· 并让 B4F1 的 `parse_state_schema` 能**成功解析**它 ⇒ 初始输入按「**一次写入**」进通道（走通道自身的写入语义）· **定义并预留「模型工厂」钩子**（`model_factory` · 本 feature **恒空** ⇒ 非空即**显式失败**的**判定**由 **T009** 承担 · MUST NOT 自行实现 fake 注入 · FR-036 · SC-030）
  · **依赖 schema 的校验（2026-11-10 · 分析轮 · 自 `T009` 拆来）**：① 节点返回的 key **必须全在** schema 里 ⇒ 否则**显式失败**（**非** schema 之外的 key 被静默接受）；② **初始输入**含 schema 之外的 key ⇒ **显式失败**（SC-021 的子情形一 · MUST NOT 静默丢弃、也 MUST NOT 塞进「未知通道」）；③ **初始值**与归约器不兼容 ⇒ 错误**向上传播**且通道保持「无值」（SC-021 的子情形二）；④ 字段描述里的**值类型无法被 B4F1 解析**（如 `Annotated` 里的归约器不是二元）⇒ **显式失败**（MUST NOT 静默跳过该字段）；⑤ 字段描述里某个 key **缺少值类型** ⇒ **显式失败**（构造不出 `TypedDict` ⇒ 两边都拼不出图）
- [X] T020 [P] [US3] 在 `tests/differential/driver.py` 实现 freegraph 侧的**规格驱动器**：线性单链（按 `nodes` 顺序串行）· 只用 **B5F1 通道层 + B5F2 读取层** ⇒ MUST **NOT** 含触发判定 / 分支路由 / 版本号 / 并发（调度循环属 **B7F1**）· 节点的入参按**读取层**产出（稀疏）· **节点入参的观测方式**：在**节点函数内部**把收到的字典**复制一份**留存，且该副本 MUST 取自**节点执行前**（节点就地改写入参时观测到的仍是原始入参）
- [X] T046 [US3] 在 `tests/differential/driver.py` 补齐「**节点返回值 → 通道写入**」的**测试侧最小合并**：节点函数返回的部分状态 MUST 按通道**自身的写入语义**写入通道（覆盖型 = 覆盖 · 归约型 = 首次写**直存**（不调归约器 · B5F1 裁定 4）+ 其余按序归约 · 路由型 = 同覆盖型）⇒ 产出「**输出状态**」与「**事件序列**」两项投影所需的通道终值；MUST **NOT** 含触发判定 / 版本号 / 分支路由 / 并发 ⇒ 该「最小合并」= **一次写入**的模拟，MUST **NOT** 长成第二个调度器（FR-024 · 裁定 6 · SC-006 / SC-007）—— ⚠️ **依赖顺序（2026-11-10 · 分析轮）**：本任务**写** `tests/differential/driver.py` ⇒ MUST **等 `T020`（同文件）完成后**再动 ⇒ **不标 `[P]`**
- [X] T045 [US3] **复核**「**写入**」投影的**语义**在**全部引用点**上一致：`contracts/differential-fixture.md` §3.3（已钉死）· `contracts/upstream-parity.md` §2（已补）· `data-model.md` §4（已补）· spec `FR-034` + `裁定 23`（已回写）⇒ 该投影 MUST 取「**节点函数返回的部分状态（原样 · 未归约）**」⇒ **无更新 ⇒ `None`**；MUST **NOT** 取「通道**归约后**的累计值」（二者在归约型通道上不同 ⇒ 取法不同即**稳定假差异**）⇒ **本任务的实质 = 一致性复核 + 补齐任何遗漏的同步点**（四处措辞已在 plan 阶段落定，实现期只做复核）—— ⚠️ **判据口径（2026-11-10 · 分析轮）**：MUST 核的是**语义一致**（同一口径），**不是**「逐字相同」（各文档的措辞可不同）；**引用点清单** = 上列 **3 份文档 + spec 的 `FR-034` / `裁定 23`**（共 **5 处**）—— ⚠️ **依赖顺序**：本任务**写** `contracts/upstream-parity.md` ⇒ MUST **等 `T022`（同文件）完成后**再动 ⇒ **不标 `[P]`**
- [X] T021 [US3] 在 `tests/differential/runner.py` 实现**两侧执行 + 三项投影归一化 + 逐字段判定**：① **节点入参**（两侧的 key 集合 + 逐 key 值；两侧 MUST 以**同一方式**观测 —— 在**节点函数内部**复制留存且副本取自**节点执行前**）—— ⚠️ 该投影的**差异 == 0** 是 **`SC-032`**（裁定 32 ① · **节点入参是 C4 的载荷** ⇒ MUST 被**逐字段**计入判定记录）② **输出状态**（两侧的 key 集合 + 逐 key 值 · `SC-006`）③ **事件序列**（归一化为 `(步序, 节点名, 写入)` 三元组；**「无更新 ⇒ 写入为 `None`**」· `SC-007`）—— 判定 MUST **逐字段**报告（哪个 key / 哪个步序 / 期望值 vs 实际值），MUST NOT 只写「一致」；并把**上游版本**（`langgraph 1.2.11`）记入判定记录
- [X] T022 [US3] 在 `tests/differential/runner.py` 与 `contracts/upstream-parity.md` §2 的**实测基线**逐项对齐（节点入参 `keys == ['messages']` · 归约结果 `['a','b']` · 空更新 `{'<node>': None}` · fresh 视图 `['old','new']`）—— MUST NOT 凭记忆写期望值；上游版本升级时 MUST **重新实测**该基线 —— ⚠️ **依赖顺序（2026-11-10 · 分析轮）**：本任务**写** `runner.py` ⇒ MUST **等 `T021`（同文件）完成后**再动 ⇒ **不标 `[P]`**

**Checkpoint**: US1–US3 均可独立验证 —— 差分夹具在混合规格上三项投影一致，且**缺席即 skip**

---

## Phase 6: User Story 4 - fresh 读视图不污染通道正式值（Priority: P4）

**Goal**: 「**当前值 + 本任务本次写入**」的视图，且**不污染**通道的**绑定与可用性判定**。

**Independent Test**: 手写通道状态 + 一组待写入值 ⇒ 走 fresh 读入口 ⇒ 断言视图**含**本次写入、
且通道的**绑定与可用性判定**（`is_available()` 的**结果** + `get()` 的**取值**）在读取**前后不变**
（**零污染判据的作用域** · 已知面见 spec Edge Cases · 裁定 29）。

### Tests for User Story 4（MUST 先写 · MUST 先失败）

- [X] T023 [P] [US4] 在 `tests/runtime/test_read_fresh.py` 写 fresh 读用例：`fresh=True` 的视图**含**本次写入 · 读取**前后**通道的**绑定与可用性判定**（`is_available()` 的**结果** + `get()` 的**取值**）**不变**（零污染 · 作用域见 FR-009 / SC-005 · 裁定 29）· 归约型通道的 fresh 视图 == 归约后的结果 · `fresh=False` 的视图**不含**本次写入 · 待写入的**未知 key** ⇒ 抛 `InvalidChannelUpdateError`（其 `key` 指向该 key）· 归约器在合并中抛错 ⇒ **向上传播**且通道正式值**不变**
  · ⚠️ **两个稀疏入口 MUST 逐字相等（2026-11-10 · 分析轮第二轮 · FR-038 / SC-033 · 裁定 33 ④）**：追加一条用例 ——
    `read_channels(channels)` 与 `local_read(channels, {}, fresh=False)` 的结果 **MUST 逐字相等**
    （key 集合**相同** + key **顺序相同** + 逐 key 值**同一对象**）⇒ 「**稀疏**读」只有一处实现
    （契约 `read-contract.md` §1 / §3.1 / §4 **I-11**）⇒ 若二者出现差异 ⇒ 判为**语义分叉缺陷**
    （**不是**「口径相近」）⇒ ⚠️ **本用例 MUST 住在本任务（US4）**：它依赖 `local_read` 的
    **非 fresh 分支**（T024）⇒ 放在 US1（T013）会**永远红**（`local_read` 尚未实现）
  · ⚠️ **已知面用例（就地修改型归约器）**：一个**就地修改型**归约器（就地 `extend` 值对象）⇒ 副本与原通道**浅共享值对象** ⇒ 原通道的**值对象会被改写** ⇒ **断言写明该行为**（与上游**同构** · research **D-10** / **DR-4**）⇒ MUST **NOT** 由读取层修复（**不深拷贝**）⇒ MUST **NOT** 计入零污染判据 ⇒ MUST 在人工验证记录中**显式登记**（裁定 29 · Q26）
  · **Edge Cases 补落（2026-11-10 · 分析轮）**：④ `local_read` 的**待写入映射为空** ⇒ MUST 返回与「**非** fresh 读」**逐字相等**的视图；⑤ **同一通道**在**同一次** fresh 读里**既被读取又被写入** ⇒ 视图按「先合并本次写入、再取值」计算 ⇒ 视图 == 「写入生效后的状态」· 而**通道正式值**仍为写入前的值；⑥ **第三方自定义 `Channel` 子类** ⇒ 读取层 MUST 只依赖 B5F1 冻结的四个操作 ⇒ 自定义通道可被读取；但 fresh 读的**复制**要求该子类**可复制**（MUST 在文档里写明这一约束）

### Implementation for User Story 4

- [X] T024 [US4] 在 `src/freegraph/runtime/read.py` 实现 `local_read` 的**非 fresh 分支**（`fresh=False` ⇒ 只读当前值 · 稀疏口径与 `read_channels` 一致 · ⚠️ **且二者结果 MUST 逐字相等** · FR-038 / SC-033 / `read-contract.md` §4 **I-11** ⇒ **MUST 共享同一处稀疏读实现**、MUST NOT 各写一份）
- [X] T025 [US4] 在 `src/freegraph/runtime/read.py` 实现 `local_read` 的 **fresh 副本法**与**合并语义**：`copy.copy(channel)` 复制通道 ⇒ 在**副本**上 `update(writes[key])` ⇒ 从**副本**读 ⇒ **丢弃**副本 ⇒ 原通道的**绑定与可用性判定零污染**（作用域见 FR-009 · 裁定 29）；合并 MUST **复用** `Channel.update()`（MUST NOT 在读取层另写一份归约逻辑）；待写入的未知 key ⇒ 抛**既有**的 `InvalidChannelUpdateError`（MUST **NOT** 新增错误类型）
- [X] T026 [P] [US4] 在 `tests/runtime/test_read_purity.py` 写**副本**的纯净用例：副本**无** `__dict__`（B5F1 的 `__slots__` 纪律不被破坏）· 副本的**归约器与原通道同一引用** · 原通道的**绑定与可用性判定**（`is_available()` 的**结果** + `get()` 的**取值**）在 fresh 读**前后不变**（零污染判据的作用域 · FR-009 / 裁定 29）—— ⚠️ **MUST NOT** 断言「值对象逐字相等」：「**就地修改型**归约器改写值对象」属**已知面**（MUST **NOT** 计入该判据 · MUST **NOT** 修 · 登记见 T023）

**Checkpoint**: US1–US4 均可独立验证 —— fresh 读的视图与**绑定与可用性判定**的零污染同时成立

---

## Phase 7: User Story 5 - 状态读取只有一处实现点（Priority: P5）

**Goal**: 「稀疏读」与「fresh 读」两条语义**收敛**到同一个模块的两个入口；
内核路径**零**上游导入；发行依赖**零**新增。

**Independent Test**: 全仓扫描 —— 状态读取入口的**实现点数 == 1**；内核路径对上游的导入次数 == **0**；
`Requires-Dist` **整体为空**。

### Tests for User Story 5（MUST 先写 · MUST 先失败）

- [X] T027 [P] [US5] 在 `tests/runtime/test_read_purity.py` 写**零副作用**用例（**必须在子进程中执行** ⇒ 复用既有 `tests/runtime/conftest.py` 的 `run_in_subprocess` 夹具 · **既有 conftest 零改动**）：导入 `freegraph.runtime.read` 后 `sys.modules` 增量中非标准库条目数 == **0** · 环境变量读取次数 == **0** · 出站连接次数 == **0**
- [X] T028 [P] [US5] 在 `tests/runtime/test_read_contract.py` 写**契约守卫**：**解析** `contracts/read-contract.md` 并逐条断言 §4 的 **I-1…I-11**（key 集合 / key 顺序 / `type is dict` / 值同一对象 / **绑定与可用性判定前后不变**（I-5 · 作用域见 FR-009 · 裁定 29 · ⚠️ **MUST NOT** 断言「值对象逐字相等」）/ 副本无 `__dict__` / 归约器同一引用 / 零出站 / 零新增错误类型 / 「值为 `None`」出现 / **两个稀疏入口的结果逐字相等（I-11 · FR-038 / SC-033）**）⇒ 并断言两个入口的**名字 + 签名**逐字一致（`read_channels` · `local_read`）
- [X] T029 [US5] 在 `tests/runtime/test_read_contract.py` 追加**收敛守卫**与**依赖隔离**断言：全仓「状态读取入口」的实现点 == **1**（一个模块 · 两个函数）· `src/freegraph/**` 对 `langgraph` / `langchain*` / `langsmith` 的导入次数 == **0** · `freegraph.runtime.errors` 的符号集合**未变**（**零新增错误类型**）· `metadata.requires("freegraph")` **整体为空**（判据 **A5**）· `pyproject.toml` MUST **NOT** 含 `[project].optional-dependencies]` —— ⚠️ **依赖顺序（2026-11-10 · 分析轮）**：本任务**写** `tests/runtime/test_read_contract.py` ⇒ MUST **等 `T028`（同文件）完成后**再动 ⇒ **不标 `[P]`**
- [X] T030 [US5] 在 `tests/runtime/test_read_contract.py` 追加**冻结面**断言：`freegraph.runtime.__all__` == **14** 且含两个读取入口 · `freegraph.contracts.__all__` == **18** · `freegraph.graph.__all__` == **7**（依据 `contracts/read-contract.md` §1）

**Checkpoint**: 全部 5 个用户故事均可独立验证

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 跨故事的守卫、取证与合入前自检

- [X] T031 回填 `harness/verification/B5F2/manual-verification.md`：五段式齐全 · **来源覆盖表** · 差分夹具的判定**记录比对的具体字段**（字段名 + 逐项结果）· **SC-014 的「真实执行」取证**（CI 日志中 `tests/differential` 段 `passed ≥ 1` 且 `skipped == 0`）· **SC-017 的「纯本地节点」审查结论**（人工审查 · 无发起网络调用的节点）· **档位实测结论**（`langgraph==1.2.11` 在 3.14 / Windows / arm64 的安装与可导入性 ⇒ 装不上的档**登记**）· 未实跑的项**显式**记入「遗留问题」（MUST NOT 伪造输出）· 登记 **DR-1…DR-5** 的处置与触发重新评估的信号 · 登记**就地修改型归约器**的**已知面**（FR-009 / 裁定 29）
  · ⚠️ **依赖顺序（2026-11-10 · 分析轮第二轮）**：本任务 MUST **等 `T035` 完成且 CI 实际跑过至少一次**后再回填 ⇒ **不标 `[P]`**
  （`SC-014` 的取证来自 **CI 日志** ⇒ `T035` 未落地步骤 5.6、或 CI 未跑过时，**该证据不存在** ⇒ 回填即伪造）
- [X] T032 覆盖率取证：临时安装覆盖率工具（**MUST NOT** 写进依赖声明 —— v1.0 依赖面为零）⇒ 对 `src/freegraph/runtime/read.py` **全文** + `src/freegraph/runtime/__init__.py` 的**新增部分**取**行 / 分支**覆盖率 ⇒ **== 100%**；**整包**覆盖率**记录但不阻断**；实测输出记入人工验证记录
- [X] T033 执行 `quickstart.md` **全文**（**V1–V12** 逐条有结论）并把结论回填人工验证记录
- [X] T034 全量门禁核对：`uv run --no-project --python .venv python -m pytest tests/ -ra` **全绿**（含 **G2 / G3 / G24 / G27** 等**随套件执行**的门禁 · ⚠️ **MUST** 用 `--no-project` 口径 · 与 CI 逐字同款 · 否则 uv 会同步环境并**卸载**手工装入的 `differential` 组 ⇒ 差分用例全 skip ⇒ **假绿** · 见 Path Conventions 的全局口径 ①）· `gate_G21_dependencies.py`（**基础安装闭包为空集**）· `gate_G23_licenses.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml` · `gate_G24_config_layer.py` · `gate_G25_import_graph.py` · `gate_G26_network_static.py` · `gate_G27_zero_egress.py` · `gate_G29_contract_carrier.py` · `gate_G30_attribution.py` 逐条**退出码 0**（G29 输出含「挂载点 C4：**已落地**」）· 门禁编号**仍为 30**（`gate_G22_isolated_env.py` 与 **G28** 的**隔离 / 断网**实测由 CI 的 **Linux** 作业承担 ⇒ 见 T035）
- [X] T035 在 `.github/workflows/ci.yml` 的**既有作业内新增一个独立步骤**（**步骤 5.6** · `uv pip install --python .venv --group differential`）（**登记项 R-2 · 方案 α′** · 落地形态 = 既有作业内的专门**步骤** · spec **裁定 25**）⇒ **步骤 5.5 一字不动**（仍只做 v2.0 extras 预验证）· §1 的 **7 个作业形状**与 §4.1 的 **7 个 required check 名零变更**（分支保护零变更）· ⚠️ **位置约束（裁定 30）**：**步骤 5.6 MUST 位于步骤 6（全量测试套件）之前** —— 否则差分用例在步骤 6 执行时**尚未装上游** ⇒ **永远 skip** ⇒ `SC-014`「真实执行次数 ≥ 1」**不可达** ⇒ **假绿** · 并**实测** **G28 断网等价性**下差分用例可跑通（`langgraph` 在断网下 MUST 可 import 且可跑）—— 若失败 ⇒ 该用例 MUST 纳入 G28 的**可机读排除清单**（**确切路径 = `tests/gates/data/offline_exclusions.txt`** · G28 脚本固定读该文件 · `harness/scripts/gates/gate_G28_offline_equiv.py:53`）⇒ MUST **NOT** 新建第二份清单（**单一事实源** · 宪法原则 VIII）（MUST NOT 删断言）
  · ⚠️ **步骤 5.6 的标题 / 注释 MUST NOT 出现 `langgraph` 字样（2026-11-10 · 分析轮 · 裁定 32 ③ 的实施约束）** —— 既有判据 `test_ci_workflow_never_installs_langgraph` 断言的是 **`ci.yml` 全文** `count("langgraph") == 0` ⇒ 步骤名 / 注释里出现该字样 ⇒ 该判据**变红** ⇒ 而 **MUST NOT** 以「删 / 放宽断言」消除红灯 ⇒ 步骤名只写 **`differential`**（如 `Install differential group`）· 注释亦然（**只写依赖组名**）
  · ⚠️ **G27 的实测项（2026-11-10 · 分析轮 · plan R-2 风险 ④）**：**G27（零出站动态 · Linux 档）**与 G28 同在**步骤 9**、**同一个 venv**（已装上游 ⇒ 带 `langchain-core` / `langsmith`）里跑 `pytest tests/` 全量套件 + socket 监测 ⇒ MUST 实测「上游在 socket 监测下被 import」的归因结论（**框架出站 == 0** · 只观测不阻断 · 按发起方归因）⇒ 结论 MUST 落入人工验证记录（**MUST NOT** 把上游自身的出站记到 freegraph 头上）
  · ⚠️ **档位实测（2026-11-09 · clarify 第四轮 · 裁定 30 增补）**：MUST 实测 `langgraph==1.2.11` 在 **3.14 / Windows / arm64** 三档的**安装与可导入性** ⇒ 过 ⇒ 该档**也**装该组；不过 ⇒ 该档**不装**并**登记**（写入人工验证记录）⇒ 该档差分用例 **skip**（**非失败**）· **MUST NOT** 静默不跑 ⇒ **至少 1 个作业 MUST 装**（实测通过的那档 · Linux 全量档优先）
- [X] T036 在 `specs/b3f1-scaffold-ci-gates/contracts/ci-matrix.md` 做**契约修订的复核与补齐**（⚠️ **2026-11-10 · 分析轮的状态订正**）：该契约的**工作区版本已含**「步骤 **5.6**」行（§2 步骤表）与「步骤 6 MUST 在步骤 5.6 之后」的**位置约束**与 **§2.1 修订记录** ⇒ 本任务 MUST **先复核**这三处是否**逐字合规**（位置约束是否写明「在步骤 6 之前」· 修订记录是否带日期与发起者追认落点）⇒ **仅在缺项时补齐** ⇒ **MUST NOT** 追加**第二条** 5.6 行（冻结面 · 重复行 ⇒ 契约自相矛盾）· 修订 MUST 走该契约自身的冻结面处置流程并**留发起者追认的落点**（MUST NOT 改 §1 的作业形状 · MUST NOT 改 §4.1 的 required check 名 ⇒ **零新增 job 名**）
- [X] T037 **发起者追认 R-1**（宪法「质量门禁 3 / 4 / 5」的偏离登记 · **阻断合入**）：追认文字 + 发起者确认 + 日期 MUST 落在 `harness/verification/B5F2/manual-verification.md` —— 实现 MUST **停下来等追认**，MUST **NOT** 代签；MUST NOT 改宪法正文 · MUST NOT 写一条永久红的 CI · MUST NOT 把 `GATE-MOUNT: C8` 改成 `landed`
- [X] T038 **发起者追认 R-2**（`ci-matrix` 契约修订 · **阻断合入**）：追认文字 + 发起者确认 + 日期 MUST 落在 `harness/verification/B5F2/manual-verification.md` ⇒ MUST NOT 代签
- [X] T043 **发起者追认 R-3**（既有 **B4F1** 依赖判据的**取样范围拆分** · **阻断合入**）：追认文字 + 发起者确认 + 日期 MUST 落在 `harness/verification/B5F2/manual-verification.md` —— MUST **NOT** 代签；MUST NOT 以「删断言 / 放宽断言」的方式消除红灯 ⇒ **发行面断言一字未弱化** + **新增**等效正向约束 ⇒ 拆分后的五条断言 MUST **全部**成立（FR-037 · SC-031 · 裁定 27）。
  ⚠️ **定性（裁定 27 · 第四轮改写）**：本项 = 「**取样范围 bug 修复** + **发起者追认**」⇒ **不属**宪法 v1.6.0
  的门禁偏离（其窄口径根因 = 「该 feature 按里程碑**不交付其前置能力**」）· **不属**宪法 v1.8.0 的跨 feature
  承接（其触发条件 = 「指名**下一棒** feature」· **B4F1 是上一棒**）⇒ **无需宪法修订**（宪法正文与门禁编号
  **G1–G30** 一字不动）。
  ⚠️ **闸口归属（裁定 28）**：**SC-031** 的 **① ② ③ ⑤** 在**执行闸口 A1** 验收 · **④**（`ci.yml` 的上游安装
  路径 == 仅 `--group differential`）在**执行闸口 A7** 验收（④ 的对象要到 **T035** 才进入 `ci.yml`）。
- [X] T039 复核**跨 feature 接线**（宪法 **v1.8.0**「跨 feature 承接的接线通则」· 本 feature 的**首次适用**）：`harness/features/B7F1_任务准备与super-step循环.md:41`（承接条款：MUST 把 C4 用例改为断言真实节点入参）· `harness/features/B8F1_条件边路由与fresh读.md:42`（夹具接口口径：条件边字段已预留）· `harness/features/B25F1_双跑验收与迁移说明.md`（承接条款：B25F1 MUST 提供 fake 模型工厂 ⇒ 让差分夹具能跑**模型形状**的图规格 · FR-036 / 裁定 26）—— 三处**在位**且措辞未走样；MUST NOT 改动这三份提示词初稿的**其余**内容（宪法 v1.8.0 的「只接线 · 逐条最小改动」红线）
  · ⚠️ **第五处接线（2026-11-10 · 分析轮第二轮 · FR-031 ② / SC-023 · 裁定 33 ③）**：`harness/features/B8F1_条件边路由与fresh读.md` 的**既有**承接条款（`:42`）MUST **补入**一句 ——「**B8F1 MUST 在使用 `local_read` 时显式传 `fresh=True`**（`fresh` 的缺省是 `False`）· MUST NOT 依赖缺省 · MUST NOT 假设上游的 `managed` 语义（research **DR-3**）」（原义务只写在 `contracts/read-contract.md` §1.1 ⇒ **无 FR / 无任务承载** ⇒ 违反宪法原则 VI 的可追溯性要求）⇒ **只接线 · 逐条最小改动**（MUST NOT 改动该文件的**其余**内容）
  · ⚠️ **第四处接线（2026-11-09 clarify 第四轮 · 裁定 27 / R-3）**：`harness/features/B4F1_schema解析与归约器提取.md`（**承接条款：B5F2 → B4F1 · 既有依赖判据的**取样范围拆分**」）—— **B4F1 是上一棒 ⇒ 非 v1.8.0 通则的触发条件** ⇒ 按**同款形态**做「**只接线**」记录 ⇒ MUST **校正**其措辞与 **裁定 27** 一致（「**拆分取样范围**」·「**发行面断言逐字保留**」·「**取样范围 bug 修复 + 发起者追认**」·「**无需宪法修订**」· **MUST NOT** 出现「判据收窄」或援引宪法 v1.6.0 作为依据）⇒ **MUST NOT** 改动该文件的**其余**内容（只接线 · 逐条最小改动）
- [X] T040 提交前自检：逐条核对**零改动清单**（`src/freegraph/contracts/` · `src/freegraph/graph.py` · `src/freegraph/runtime/{channel,mapping,errors,schema,reducer}.py` · `tests/{contracts/test_architecture,facade,gates}/` · `pyproject.toml` 的 `[project]` 段 · 兼容矩阵 · `THIRD_PARTY_NOTICES` · **`harness/demo/target.py`**〔**G29-01 的只读基准 diff 保护对象** · 宪法原则 III〕· **`.specify/memory/constitution.md`**〔**原则 I–X + 门禁编号 G1–G30** · 本 feature 明定**无需宪法修订**〕）—— ⚠️ **例外共四处**（其余**一字不动**）：
  ① `tests/runtime/test_parse_contract.py` 的**两条依赖判据**按登记项 **R-3** **拆分取样范围**（**T041 / T042**）；
  ② `specs/b3f1-scaffold-ci-gates/contracts/ci-matrix.md` 按登记项 **R-2** **复核与补齐**步骤 5.6 行（**T036**）；
  ③ `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 的 **G29 判定 3** + `harness/scripts/gates/gate_G29_contract_carrier.py` 的 **docstring** 按登记项 **R-4** **最小修订**（**T048** · **判定代码零改动**）；
  ④ `harness/proposals/立项书.md` 的 §4.2 S5 / §5.2 B5F2 行 / §9.2 落点按裁定 33 ③ **回改**（**T047** · **只接线**）
  · 核对附录追溯表**逐条有任务**（FR **38/38** · SC **33/33**）· 核对**反向**：每条任务携带的义务**都挂上了至少一条 FR**（⇒ 追溯表**双向**齐全 · 裁定 32 ②）· 核对**无占位符**（`TODO` / `TBD` / `[FEATURE NAME]` / `NEEDS CLARIFICATION` 计数 == 0）
- [X] T044 [P] 补**上游实测**并登记 parity 条目：在**钉住的上游版本**（`langgraph 1.2.11`）上实测 `local_read` 对「**待写入映射里存在、但通道映射里没有**的 key」的可观察行为 ⇒ 结论 MUST 落成**可机读**记录并作为 **P-12** 写入 `contracts/upstream-parity.md`（freegraph 抛 `InvalidChannelUpdateError` · FR-011 / 裁定 19 vs 上游的实际行为）⇒ MUST NOT 凭记忆写期望值（宪法原则 VIII）
  · 📌 **归位理由**：本任务是**纯取证 / 文档回填**，**不阻塞任何用户故事** ⇒ 从 Foundational（原 Phase 2）移至本 Phase ⇒ 避免把「需联网的上游实测」压在**阻塞全部用户故事**的底座上（⇒ 关键路径不被一个文档性测量卡住）
- [X] T047 [P] **回改立项书**（**上位文档** · 只接线 · 逐条最小改动 · 裁定 33 ③）：`harness/proposals/立项书.md` 三处 ——
  ① **§4.2 S5** 行尾：「差分夹具与 fake 轮共用同一套注入机制」⇒ 补「**分棒交付**：**接口与钩子**归 B5F2（该 feature 内 `model_factory` **恒空** ⇒ 非空即**显式失败**）/ **注入实现**归 B25F1（M4）」；
  ② **§4.2 S5** 的「落点」注 ⇒ 补「B5F2 的差分夹具由**两项**投影**扩展为三项**（+ 节点入参 · 属**加强**）」；
  ③ **§5.2** 的 **B5F2 行**小目标 ⇒ 补「**（2026-11-10 修订）B5F2 的差分夹具扩展为三项投影**」；
  ④ **§9.2**「fake 模型的注入机制」的**落点**行 ⇒ 把「§5.2 **B25F1** 小目标（CI 轮）与 §5.2 **B5F2 / B8F1**（差分夹具）」改为「§5.2 **B25F1** 小目标（CI 轮）与 §5.2 **B8F1**（路由形状）；**B5F2** 交付差分夹具**接口**与**预留的「模型工厂」钩子** ⇒ fake 注入的**实现**归 **B25F1**（M4）· **分棒交付**」
  ⇒ MUST **只接线**：MUST NOT 改动立项书的**其余**内容 · MUST NOT 删条目 · MUST NOT 改 §5.2 的**规模 / 人日 / 成本**数字
  ⇒ 回改后的口径 MUST 与 `spec.md` **裁定 26 / FR-036** 与 `research.md` **DR-5** **逐字一致**（宪法原则 VIII）
- [X] T048 [P] **最小修订 G29 的冻结契约**（登记项 **R-4** · 裁定 33 ②）—— **两处**、**判定代码零改动**：
  ① `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 的 **G29 判定 3** ⇒ 改为**两态口径**
     （`status` ∈ {`not-landed`, `landed`}）+ **定义 `landed` 的语义**（该契约的独立回归测试**已存在且常驻 CI**；
     **断言对象的边界**由该 feature 的 `spec` 承担 —— B5F2 的 C4 = **读取层口径**、节点边界归 **B7F1**）
     + 保留「MUST NOT 伪装成『已通过』」这一**红线原样**；
  ② `harness/scripts/gates/gate_G29_contract_carrier.py` 的 **docstring 第 3 点**（`:19-24`）⇒ 与 ① **逐字同义**
  ⇒ **MUST NOT** 改动 G29 的**判定代码**（`:232` 早已接受两态）· MUST NOT 改动**门禁编号 G1–G30** · MUST NOT 新增门禁编号
  ⇒ 修订 MUST 走该契约自身的**冻结面处置流程**并**留发起者追认的落点**（**T049**）
  ⇒ **实测项**：修订后 `gate_G29_contract_carrier.py` 的退出码仍为 **0** 且输出含「挂载点 C4：**已落地**」
- [X] T049 **发起者追认 R-4**（**G29 冻结契约**的最小修订 · **阻断合入**）：追认文字 + 发起者确认 + 日期 MUST 落在
  `harness/verification/B5F2/manual-verification.md` —— MUST **NOT** 代签 · MUST NOT 改门禁**判定代码** · MUST NOT 改门禁编号
  ⚠️ **定性（裁定 33 ②）**：本项 = 「**冻结面最小修订 + 发起者追认**」⇒ **不属**宪法 v1.6.0 的门禁偏离
  （其窄口径根因 = 「该 feature 按里程碑**不交付其前置能力**」）· **不属** v1.8.0 的跨 feature 承接
  （无「指名下一棒」的跨 feature 义务）⇒ **无需宪法修订**（宪法正文与门禁编号 **G1–G30** 一字不动）
  ⚠️ **闸口归属**：**T048** 在**执行闸口 A7** 验收 · 本追认任务是**阻断合入**的
- [X] T050 [P] **取证 SC-009 的「缺席即跳过」**（裁定 32 配套 · **未安装 `differential` 组的环境**）：在
  **G22 的隔离 venv**（或开发者**未装该组**的 venv）里跑一次差分用例 ⇒ MUST 记录「**跳过标记数 ≥ 1** 且
  **失败数 == 0**」的实测输出 ⇒ 写入 `harness/verification/B5F2/manual-verification.md`
  ⇒ ⚠️ **CI 主测试档不适用本取证**（步骤 5.6 已装上游 ⇒ 差分用例**真实执行**）⇒ 二者**互不替代**（SC-009 / SC-014）
  ⇒ MUST NOT 凭「CI 里没红」冒充本取证（**MUST NOT** 伪造输出）
- [X] T051 **独立验收脚本**（**裁定 34** · FR-039 / SC-034 · **2026-11-10 · 发起者提出**）：
  新建 `harness/verification/B5F2/acceptance.py`（★ **单文件** · **只依赖标准库**
  （+ 被验收的 `freegraph` 本身 + 仓库自带的 `tests/differential` 包）⇒ **零第三方依赖** ·
  **署名头** + docstring 为首个语句 ⇒ 过既有门禁 **G30**）——
  **一条命令跑完全部验收闸口 V1–V12** + 覆盖率取证 + 10 条门禁的实跑结果：
  ① **V1** C4 稀疏读（**否定式**断言）· ② **V2** 挂载点（C4 = `landed` / C8 = `not-landed`）·
  ③ **V3** G2（挂载点文件零 `freegraph.*` 导入）· ④ **V4 / V5** 稀疏读语义（普通 `dict` ·
  key 集合 / 顺序 · `None` 值 · `skip_empty` 两分支 · Edge Cases）· ⑤ **V6** fresh 读
  （视图 · **零污染** · 未知 key ⇒ 显式失败 · 归约器抛错 ⇒ 向上传播且正式值不变 ·
  **两个稀疏入口逐字相等**）· ⑥ **契约守卫**（**解析** `read-contract.md` 的 §4 ⇒ I-1…I-11
  **逐条**绑定 + §1 的**签名逐字一致**）· ⑦ **V7 / V8** 差分夹具（三项投影**逐字段**相等 ·
  上游实测基线对齐）· ⑧ **V9** 依赖红线（`Requires-Dist` 整体为空 · 内核零上游导入 ·
  依赖组**正向枚举** · `ci.yml` 的 `--group` 白名单 · 步骤 5.6 位于步骤 6 之前）·
  ⑨ **V10** 10 条门禁实跑（7 条**本地硬断言** + 3 条 **Linux only 只观测**）·
  ⑩ **V11** 覆盖率（`read.py` / `__init__.py` 行 / 分支 **100%**）· ⑪ **V12** 冻结面
  （**18 / 7 / 14** · 兼容矩阵零新增行 · 层注册表 · 门禁编号 **30**）+ 跨 feature 接线（**五处**）——
  MUST 支持**两态运行**（已安装 ⇒ 测**发行产物** / 未安装 ⇒ 测**源码树**）·
  `--record <file>`（产**五段式**记录片段）· `--skip-coverage` / `--skip-gates` ·
  退出码 **0 = PASS · 1 = FAIL · 2 = 环境未就绪** ⇒ ⚠️ **上游 / `coverage` 缺席 ⇒ 对应分组标
  「◌ 环境未就绪」（skip ≠ fail · FR-019）⇒ MUST NOT 判失败**

---

## Dependencies & Execution Order

### 执行闸口（Phase 闸口 · 每道 MUST 全绿才进下一 Phase）

| 闸口 | 触发点 | MUST 验证 | 关联判据 |
|---|---|---|---|
| **A1** | Phase 1–2 结束 | `read.py` 骨架就位（署名头 · docstring 首个语句 · **只依赖标准库**）· `freegraph.runtime.__all__` == **14** · L1 == **18** / 门面 == **7** · 图规格前置校验就位 · 夹具的 skip 夹具就位 · **既有 B4F1 两条依赖判据已按 R-3 拆分取样范围**（**SC-031 的 ① ② ③ ⑤ 在 A1 成立** —— **④** 由 **A7** 验收 · 裁定 28）· `pytest tests/ -ra` **仍全绿**（既有门禁零破坏）
  · ⚠️ **SC-009 已从本闸口移出**（2026-11-10 · 分析轮第二轮）：SC-009 要求「**跳过标记数 ≥ 1**」⇒ 需**真实差分用例**被收集并 skip（用例在 **T018** · Phase 5）⇒ A1 时刻 skip 数 == 0 ⇒ **不可判定** ⇒ **SC-009 归 A4 / T050** | FR-021 · FR-022 · FR-028 · FR-035 · FR-037 · SC-011 · SC-029 · SC-031 |
| **A2** | Phase 3 结束（US1） | **C4 的两条否定式断言**成立（`"llm_calls" not in node_input` · `.get("llm_calls", 0) == 0`）· 空 key **缺席** · 「值为 `None`」**出现** · `skip_empty=False` **抛错** · 挂载点 C4 == `landed` · C8 **未被改动** · **G2 仍绿** | FR-003 · FR-006 · FR-007 · FR-012 · FR-013 · FR-032 · SC-001 · SC-002 · SC-003 · SC-015 · SC-025（**验收判据 A1 / A2**） |
| **A3** | Phase 4 结束（US2） | `type(result) is dict` **逐字**成立 · 值与通道当前值**同一对象** · 改结果 `dict` 的键集合**不影响**通道 · key **顺序** == 入参顺序 · 浅引用的已知面**被断言写明** | FR-004 · FR-005 · SC-004（**验收判据** — 引文 §6 的 P2） |
| **A4** | Phase 5 结束（US3） | 混合规格上**三项投影**逐项相等（节点入参 / 输出状态 / 事件序列）—— ⚠️ **节点入参投影**的差异 == 0 是 **`SC-032`**（裁定 32 ① · 节点入参是 **C4** 的载荷）· **空更新 ⇒ 写入为 `None`** · 判定记录含**比对的具体字段** · `langgraph` 缺席 ⇒ **skip 而非 fail**（**SC-009** 在本闸口验收 · 含 **T050** 的「未装 `differential` 组」取证）· 上游版本**已记录** · 期望值与上游实测基线**对齐** · **模型工厂钩子恒空 ⇒ 非空即显式失败**（含「模型形状的图规格」不进入比对） | FR-014 · FR-015 · FR-016 · FR-017 · FR-019 · FR-029 · FR-033 · FR-034 · FR-036 · SC-006 · SC-007 · **SC-032** · SC-009 · SC-013 · SC-019 · SC-021 · SC-022 · SC-026 · SC-028 · SC-030（**验收判据 A3 / A4**） |
| **A5** | Phase 6 结束（US4） | fresh 视图**含**本次写入 · 读取**前后**通道的**绑定与可用性判定**（`is_available()` 的结果 + `get()` 的取值）**不变** · 归约型视图 == 归约结果 · `fresh=False` 不含写入 · 未知 key ⇒ `InvalidChannelUpdateError`（`key` 指向该 key）· 归约器抛错 ⇒ 向上传播且正式值不变 · **就地修改型归约器的已知面已被断言写明**（MUST **NOT** 计入零污染判据 · MUST **NOT** 修 · 已登记）· 副本**无** `__dict__` · 归约器**同一引用** · **两个稀疏入口的结果逐字相等**（FR-038 / SC-033 · `read-contract.md` **I-11**） | FR-008 · FR-009 · FR-010 · FR-011 · **FR-038** · SC-005 · SC-024 · **SC-033** |
| **A6** | Phase 7 结束（US5） | 契约守卫逐条断言 **I-1…I-11**（含 **I-11** 两个稀疏入口逐字相等）· 读取入口的实现点 == **1** · 内核路径对上游的导入次数 == **0** · `errors` 的符号集合**未变** · `Requires-Dist` **整体为空** · `pyproject.toml` **无** `[project.optional-dependencies]` · 零副作用三断言全绿 | FR-001 · FR-002 · FR-018 · FR-020 · FR-021 · FR-022 · FR-023 · FR-027 · FR-035 · **FR-038** · SC-008 · SC-010 · SC-012 · SC-016 · SC-018 · SC-029 · **SC-033**（**验收判据 A5**） |
| **A7** | 收官 | **T037 / T038 / T043 / T049 发起者追认**（R-1 / R-2 / R-3 / **R-4** · **阻断合入**）· 覆盖率**行 / 分支 100%** · quickstart 全文绿（**V1–V12**）· 全量门禁**全绿**且门禁编号仍为 **30** · CI **新增步骤 5.6** 已含 `--group differential` **且位于步骤 6（全量测试套件）之前**（裁定 30）· **G28 断网**下差分用例已实测（**零新增 job 名 ⇒ 分支保护零变更**）· **T039 接线复核**通过（**含 B25F1 的承接条款**：fake 模型工厂 · 模型形状的图规格 · **含 B8F1 的第五处接线**：显式传 `fresh=True`） · **T047 立项书回改**完成（§4.2 S5 / §5.2 B5F2 行 / §9.2 落点 · 裁定 33 ③） · **T048 G29 冻结契约最小修订**完成（**判定代码零改动** · 退出码仍 0 · 登记项 R-4） · **T050 SC-009 的「未装 differential 组」取证**已落人工记录· **SC-030 复核**（模型工厂钩子恒空 ⇒ 非空即显式失败 · 承接条款已在位）· **SC-031 复核**（既有依赖判据**拆分取样范围**后五条断言全成立〔**① ② ③ ⑤** 在 A1 · **④**（CI 安装路径 == 仅 `--group differential`）**在本闸口 A7** 验收 · 裁定 28〕· **原断言一条未放宽**）· 提交前自检（零改动清单〔**含 R-2 / R-3 / R-4 三处例外 + 立项书回改**〕+ 追溯表逐条有任务） | FR-024 · FR-025 · FR-026 · FR-027 · FR-028 · FR-031 · FR-036 · FR-037 · SC-009 · SC-014 · SC-017 · SC-018 · SC-020 · SC-023 · SC-030 · SC-031 |

> **📌 编号说明（**四套**编号 · 同名不同义）**：本表的 **A1–A7 是「执行闸口」**（Phase 闸口）——
> 而 spec 的「**验收判据 A1–A5**」是**引文 §6 / 立项书 §5.2** 的编号
> （A1 `"llm_calls" not in node_input` · A2 `.get("llm_calls", 0) == 0` · A3 输出状态一致 ·
> A4 事件序列一致 · A5 `langgraph` 不入 `Requires-Dist`）；
> `quickstart.md` 的**验收闸口**用 **V1–V12**（Verification gates）；
> 宪法门禁是 **G1–G30** ⇒ **四套编号互不撞名** ⇒ 引用时 MUST 带限定语
> （「验收判据 A1（引文 §6）」/「执行闸口 A1」/「quickstart 闸口 V1」/「门禁 G21」）。

### MUST 由发起者亲自出面的闸口（实现阶段只能「备料」，不得代劳）

- **T037 —— 宪法质量门禁 3 / 4 / 5 的偏离登记追认**（plan 登记项 **R-1**）：三部分**共享同一根因**
  （C4 的**节点边界**断言需要**调度循环**、C8 需要**路由语义**、fake 轮 / 真实模型轮需要**完整内核运行时**，
  而本 feature 按立项书 §5.2 只交付**读取层**）⇒ 依宪法 **v1.6.0** 的窄口径通则处置
  ⇒ 实现 MUST **停下来等追认**，MUST **NOT** 代签（**MUST NOT** 改宪法正文 · **MUST NOT** 写一条永久红的 CI ·
  **MUST NOT** 把 `GATE-MOUNT: C8` 改成 `landed`）。
  > **📌 承接方已具名且未变**：**B7F1**（C4 的节点边界 · M1）· **B8F1**（C8 · M2）·
  > **B7F2 / B7F3**（fake 轮）· **B25F1**（真实模型轮）⇒ **不悬空**（宪法 v1.6.0 的红线之一）。
  > **📌 承接条款已接线**：B7F1 / B8F1 / **B25F1** 的提示词初稿**已写入**（宪法 **v1.8.0** 通则）⇒ 由 T039 **复核**；
  > **第四处（B4F1）** = **上一棒** ⇒ **非**通则触发条件 ⇒ 按**同款形态**「**只接线**」⇒ 同样由 **T039** 复核并校正措辞。
- **T038 —— `ci-matrix` 契约修订的追认**（plan 登记项 **R-2**）：差分夹具若在 CI **永远 skip** ⇒
  差分证据退化为「主张」⇒ SC-014 不可达 ⇒ 属**冻结面**（`ci-matrix.md`）的修订 ⇒ **MUST** 由发起者追认
  （MUST NOT 代签 · MUST NOT 改 §1 的作业形状 · MUST NOT 改 §4.1 的 required check 名）。
- **T043 —— 既有 B4F1 依赖判据的**取样范围拆分**的追认**（plan 登记项 **R-3**）：本 feature 引入**第一个**上游
  dev / test 依赖 ⇒ B4F1 的两条依赖判据（「三处声明中零上游」+「`ci.yml` 中 `langgraph` 字样 == 0」）
  MUST **拆分取样范围**（**发行面部分逐字保留** + 对 `[dependency-groups]` 改**正向枚举**：「上游只许出现在
  `differential` 组」）**并新增**一条 CI 正向断言（上游安装**只许**经 `--group differential`）
  ⇒ **原断言一条未放宽、且新增一条正向约束** ⇒ 属「**取样范围 bug 修复**」⇒ **MUST** 由发起者追认
  （MUST NOT 代签 · **MUST NOT** 以「删断言 / 放宽断言」的方式消除红灯）。
  ⚠️ **通道**：**不属**宪法 v1.6.0 的门禁偏离（窄口径根因不同）· **不属**宪法 v1.8.0 的跨 feature 承接
  （**B4F1 是上一棒**）⇒ **无需宪法修订**（宪法正文与门禁编号 **G1–G30** 一字不动）。

### Phase Dependencies

- **Setup（Phase 1）**：无依赖 —— 可立即开始
- **Foundational（Phase 2）**：依赖 Setup —— **阻塞全部用户故事**
- **用户故事（Phase 3–7）**：全部依赖 Phase 2 完成 ⇒ 之后可**并行**（若人手够）或按 **P1 → P2 → P3 → P4 → P5** 顺序
- **Polish（Phase 8）**：依赖全部目标用户故事完成

### User Story Dependencies

- **US1（P1）**：Phase 2 后可开始 —— **不依赖**其他故事（**MVP**）
- **US2（P2）**：Phase 2 后可开始 —— 与 US1 共用 `read_channels`，但**独立可测**（形态断言组可单独跑）
- **US3（P3）**：Phase 2 后可开始 —— 需要 US1 的稀疏读（夹具的 freegraph 侧要读通道状态）⇒ **实现**依赖 US1，
  但**夹具骨架与图规格构造**（T009 / T019）可与 US1 并行
- **US4（P4）**：Phase 2 后可开始 —— 需要 US1 的 `read_channels`（非 fresh 分支复用它）⇒ **实现**依赖 US1；
  **测试**（T023）可与 US1 并行
- **US5（P5）**：Phase 2 后可开始 —— 需要 US1 + US4 都在位（收敛守卫要看到**两个**入口）⇒ 其**测试**可并行

### Within Each User Story

- **测试 MUST 先写且 MUST 先失败**（本 feature 的测试即判据）—— 实现任务**不标** `[P]` ⇒
  实现**不得**与同阶段的测试任务并行起草（实现须等测试先红）；**合入顺序**：测试先红 → 实现 → 转绿
- 底座（Phase 1–2）→ 稀疏读（US1）→ 结果形态（US2）→ 差分夹具（US3）→ fresh 读（US4）→ 收敛与纪律（US5）→ 取证与自检（Phase 8）
- Story complete before moving to next priority

### Parallel Opportunities

> **📌 纪律（沿用 B5F1 的澄清轮 Q15 修复）**：**实现任务一律不标 `[P]`** ⇒ 实现 MUST 等同阶段的测试
> **先红**；**合入顺序**：测试先红 → 实现 → 转绿。下列「并行」指**起草**层面的并行（不同文件）。

- **Phase 1**：T001 · T002 · T003 · T004 · T005 · T006 六条可并行（**六个不同文件**）；T007 依赖 T002（同一文件）
  · ⚠️ **执行先后（2026-11-10 · 分析轮第二轮）**：**T006 MUST 先于 T001 执行**（`T006` 取**实现前绿基线** ⇒ `T001` 一落地，既有依赖判据即变红 ⇒ 基线将不是绿）⇒ 两者**可并行起草**、**执行有先后**
- **Phase 2**：T008 · T009 · T010 · T041 · T042 可并行（**五个不同文件** · T041 / T042 同文件
  `tests/runtime/test_parse_contract.py` ⇒ **T041 与 T042 串行**）；T007 与它们可并行（`read.py` 不与它们冲突）
  · ⚠️ **T009 的范围已收窄**（分析轮）：T009 只做**不依赖 schema** 的前置校验 ⇒ 与 T019 的**职责**不重叠（**仍**同文件 ⇒ 但 Phase 2 先于 Phase 5 ⇒ 串行成立）
- **US1**：T011 与 T013 可并行（两个不同测试文件）；T012 须等 T011 先红；T014 须等 T011 在位
- **US2**：T015 **须等 T013**（同文件 `test_read_semantics.py` ⇒ **串行**）· T016 须等 T015 先红；T017 须等 T015（同一文件）
- **US3**：T019 · T020 可并行（两个不同文件）· **T046 须等 T020**（同文件 `driver.py` ⇒ **串行**）· **T022 须等 T021**（同文件 `runner.py` ⇒ **串行**）· **T045 须等 T022**（同文件 `upstream-parity.md` ⇒ **串行**）· T021 须等 T020；T018 须等 T021
  · ⇒ **可并行的起草层** = **T019 · T020**（**两个**不同文件）+ T018（`test_differential.py`）
- **US4**：T023 · T026 可并行（两个不同测试文件）；T024 · T025 须等 T023 先红（同一文件）
- **US5**：T027 · T028 · T029 · T030 —— T029 / T030 与 T028 **同一文件** ⇒ **串行**（T029 须等 T028）；T027 可与它们并行
- **Phase 8**：T035 · T036 · T039 · T044 · T047 · T048 · T050 可并行（**七个不同文件**）；
  ⚠️ **T031 不在上列**：MUST 等 **T035** 完成**且 CI 实际跑过至少一次**（`SC-014` 的取证来自 **CI 日志**）⇒ 再回填人工记录；
  ⚠️ **2026-11-10 · 实现期登记**：**T035 已落地**（步骤 5.6 已进 `ci.yml` 且位于步骤 6 之前），
    人工记录**已回填**（五段式 + 来源覆盖表 + 判定记录的具体字段 + DR-1…DR-5 + 已知面）；
    ⚠️ **但 CI 尚未在本会话实际跑过** ⇒ **SC-014 的「CI 日志」侧证据不存在**
    ⇒ **未伪造** ⇒ 已**显式**登记为人工记录的「未实跑项 #4」（连同 macOS / Windows /
    arm64 三档的**档位实测缺口**）⇒ **该证据待下一次 CI 实跑后补录**（⇒ **A7 的
    SC-014 复核**在 CI 实跑后才算闭合）。
  ⚠️ **T037 / T038 / T043 / T049**（**四条**追认）**必须**等 T031（追认文字落在人工记录里）

> **📌 并行纪律的补充（2026-11-10 · 分析轮 + 第二轮）**：**同文件的多条任务一律串行**（`[P]` 只在
> **不同文件**且**无未完成依赖**时标注）⇒ 本轮已去掉 `T015` / `T022` / `T029` / `T045` / `T046` 的 `[P]`
> （分别与 `T013` / `T021` / `T028` / `T022` / `T020` 同文件）⇒ 后续若再新增任务，MUST 复核本条。

---

## Parallel Example: User Story 1

```bash
# 起草层并行（不同文件）
Task: "在 tests/runtime/test_read_c4_sparse_state.py 写 C4 独立回归测试（否定式断言）"
Task: "在 tests/runtime/test_read_semantics.py 写稀疏语义用例"

# 实现 MUST 等测试先红
Task: "在 src/freegraph/runtime/read.py 实现 read_channels 的稀疏读"
```

---

## Parallel Example: User Story 3

```bash
# 起草层并行（不同文件）
Task: "在 tests/differential/spec_builder.py 实现图规格 ⇒ 动态构造 TypedDict"
Task: "在 tests/differential/driver.py 实现 freegraph 侧的规格驱动器"
Task: "在 tests/differential/test_differential.py 写差分用例"

# 判定层依赖 driver（须串行）
Task: "在 tests/differential/runner.py 实现两侧执行 + 三项投影归一化 + 逐字段判定"
```

---

## Implementation Strategy

### MVP First（User Story 1 Only）

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational（CRITICAL - blocks all stories）
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: 跑 `pytest -q tests/runtime/test_read_c4_sparse_state.py`
   ⇒ C4 的两条否定式断言成立 ⇒ **MVP 达成**（差分夹具与 fresh 读可延后）
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **C4 契约门禁解锁**（G29 挂载点翻 `landed`）
3. Add User Story 2 → Test independently → 结果形态可判定
4. Add User Story 3 → Test independently → **等价证据**产出（需 CI 的步骤 **5.6** 已含 `--group differential`）
5. Add User Story 4 → Test independently → **C8 的读取原语**就位（供 B8F1）
6. Add User Story 5 → Test independently → 收敛与纪律守住
7. 每个故事增量交付，**不破坏**前面的故事

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 → User Story 2
   - Developer B: User Story 3（夹具骨架与图规格先行）
   - Developer C: User Story 5 的契约守卫骨架
3. Stories complete and integrate independently
   ⚠️ **US3 / US4 / US5 的实现**依赖 US1 ⇒ Developer A 的进度**是**关键路径

---

## 附录 · 任务 ↔ spec 追溯表

> **反向覆盖**：**FR 38/38 · SC 33/33** —— 每个 FR 与每个 SC **至少**被一条任务映射；
> **反向亦然**：每条任务携带的义务 MUST 挂上**至少一条 FR**（⇒ 追溯表**双向**齐全 · 裁定 32 ②）。
> （宪法原则 VI：「tasks MUST 逐条勾选、**可追溯到 spec 条目**」）

| 任务 | FR | SC | 说明 |
|---|---|---|---|
| T001 | FR-018 | SC-008 | **PEP 735** `differential` 依赖组（**钉版本** · 不进发行元数据） |
| T002 | FR-022 · FR-028 | — | `read.py` 骨架（署名头 · docstring · 只依赖标准库） |
| T003 | FR-021 · FR-035 | SC-029 | 导出面 **12 → 14**（L2 内部 API） |
| T004 | FR-027 | — | 五个测试模块骨架 |
| T005 | FR-014 · FR-015 | — | `tests/differential/` 包骨架（**测试侧**） |
| T006 | FR-023 | — | 人工记录骨架 + **实现前绿基线** |
| T007 | FR-002 | — | 两个入口的**签名 + 入参形态校验** |
| T008 | FR-019 | SC-009 | `langgraph` 缺席 ⇒ **skip** 夹具 |
| T009 | FR-014 · FR-015 · FR-023 · FR-024 · **FR-036** | SC-013 · **SC-017** · **SC-030** | 图规格**前置校验**（**只做不依赖 schema 的那部分**：条件边必须空 · **模型工厂钩子必须空** · 节点名唯一 · **节点确定性 / 零网络**） |
| T010 | FR-026 | SC-011 | 冻结面核对（14 / 18 / 7 · 零新增行） |
| T011 | **FR-012** | **SC-001** · **SC-002** | **C4 独立回归测试**（**否定式**断言 · 验收判据 **A1 / A2**） |
| T012 | FR-003 | SC-003 | `read_channels` 的**稀疏读**（`is_available()` 判定） |
| T013 | FR-003 · FR-006 · FR-007 | SC-003 · SC-027 | 稀疏语义用例（key 集合 / `None` 值 / `skip_empty` 两分支） |
| T014 | FR-013 · FR-032 | SC-015 · SC-025 | C4 挂载点翻 `landed` + **元测试**（**只做路径扫描** · G2） |
| T015 | FR-004 · FR-005 | SC-004 | 结果**形态**用例（`type is dict` · 同一对象 · 顺序） |
| T016 | FR-004 · FR-005 | SC-004 | 固化「新建 dict + 按引用 + 保序」 |
| T017 | FR-005 | SC-004 | **浅引用的已知面**（与上游同构 · DR-4） |
| T018 | FR-014 | SC-013 | 差分用例（混合 schema · 三项投影） |
| T019 | FR-014 · FR-029 · FR-033 · **FR-036** | SC-013 · SC-021 · SC-026 · **SC-030** | 图规格 ⇒ **动态构造 `TypedDict`**（一个对象）· 初始输入 = 一次写入 · **预留模型工厂钩子（恒空 ⇒ 非空即失败）** · **依赖 schema 的校验**（节点返回 key / 初始输入 / 字段描述负例） |
| T020 | FR-014 · FR-024 · FR-030 | SC-013 · SC-022 | freegraph 侧的**规格驱动器**（**无调度逻辑**）+ **节点入参的观测方式**（函数内部复制 · 执行前的副本） |
| T021 | FR-016 · FR-017 · FR-030 · FR-034 | SC-006 · SC-007 · **SC-032** · SC-019 · SC-022 · SC-028 | 三项投影归一化 + **逐字段**判定（**空更新 ⇒ `None`** · **节点入参投影差异 == 0 = SC-032**）+ 两侧**同法观测**节点入参 |
| T022 | FR-028 | SC-020 | 期望值与**上游实测基线**对齐（不凭记忆） |
| T023 | FR-008 · FR-009 · FR-010 · FR-011 · **FR-038** | SC-005 · SC-024 · **SC-033** | fresh 读用例（视图含写入 · **绑定与可用性判定零污染** · 未知 key · **就地修改型归约器的已知面** · **两个稀疏入口逐字相等**） |
| T024 | FR-008 · **FR-038** | SC-005 · **SC-033** | `local_read` 的**非 fresh 分支**（**MUST 与 `read_channels` 共享同一处稀疏读实现** · I-11） |
| T025 | FR-008 · FR-009 · FR-010 · FR-011 | SC-005 · SC-024 | **fresh 副本法** + 合并语义 + 未知 key |
| T026 | FR-009 | SC-005 | 副本纯净（**无** `__dict__` · 归约器同一引用 · **绑定与可用性判定前后不变**） |
| T027 | FR-020 · FR-022 · FR-023 | SC-010 · SC-016 | 零副作用三断言（子进程） |
| T028 | FR-001 · FR-002 · FR-027 | SC-012 · SC-018 | **契约守卫**（解析 `read-contract.md` · I-1…I-11） |
| T029 | FR-001 · FR-018 · FR-020 | SC-008 · SC-010 · SC-012 | 收敛守卫 + 依赖隔离（`Requires-Dist` 为空） |
| T030 | FR-021 · FR-026 · FR-035 | SC-011 · SC-029 | 冻结面断言（14 / 18 / 7） |
| T031 | FR-017 | SC-019 | 人工记录回填（五段式 · 来源覆盖表 · **具体字段**） |
| T032 | FR-027 | SC-018 | 覆盖率**行 / 分支 100%** 取证（不进依赖声明） |
| T033 | FR-028 | — | 执行 quickstart（**V1–V12**） |
| T034 | FR-025 · FR-026 | SC-011 · SC-015 | 全量门禁核对（pytest · G21–G30 · 编号仍 30） |
| T035 | FR-025 | SC-014 | CI **新增步骤 5.6** 安装 `--group differential`（**MUST 位于步骤 6 之前**· 步骤名/注释**不得**含 `langgraph` 字样）+ **G28 断网实测** + **G27 零出站归因实测** |
| T036 | FR-025 | SC-014 | `ci-matrix` **契约修订的复核与补齐**（既有 5.6 行 + 位置约束 + §2.1 修订记录 · **MUST NOT** 追加第二条 5.6 行） |
| T037 | FR-024 · FR-031 | SC-013 · SC-023 | **发起者追认 R-1**（**阻断合入**） |
| T038 | FR-025 | SC-014 | **发起者追认 R-2**（**阻断合入**） |
| T039 | FR-031 · **FR-036** · **FR-037** | SC-023 · **SC-030** · **SC-031** | 复核 B7F1 / B8F1 / **B25F1** 的**承接条款接线**（宪法 v1.8.0）+ **第四处 B4F1**（上一棒 · 同款形态只接线 · 措辞校正） |
| T040 | FR-024 · FR-026 · FR-028 | SC-011 · SC-020 | 提交前自检（零改动清单〔含 **R-3 的唯一例外**〕· 追溯表 · 无占位符） |
| **T041** | **FR-037** | **SC-031** | **拆分取样范围**：发行面零上游断言**逐字保留** + `[dependency-groups]` 改**正向枚举**（上游只许出现在 `differential` 组）（**R-3**） |
| **T042** | **FR-037** | **SC-031** | **保留原断言**（`ci.yml` 文本中 `langgraph` 字样 == 0）+ **新增**正向断言（上游安装**只许**经 `--group differential`） |
| **T043** | **FR-037** | SC-013 · SC-031 | **发起者追认 R-3**（**阻断合入** · 取样范围 bug 修复 · **无需宪法修订**） |
| **T044** | FR-011 · FR-028 | SC-024 · SC-020 | 补**上游实测**（`local_read` 的未知 key 行为）⇒ 登记 **P-12** |
| **T045** | FR-016 · FR-034 | SC-006 · SC-007 · **SC-032** · SC-028 | **复核**「**写入**」投影在 **5 处引用点**上的**语义**一致 = 节点返回的部分状态（**未归约**） |
| **T046** | FR-014 · FR-015 · FR-024 | SC-006 · SC-007 · **SC-032** | 驱动器的「**节点返回值 → 通道写入**」**测试侧最小合并** |
| **T047** | **FR-036** | **SC-030** | **回改立项书**（§4.2 S5 / §5.2 B5F2 行 / §9.2 落点 · 裁定 33 ③ · **只接线**） |
| **T048** | **FR-013** · **FR-026** | **SC-015** · **SC-011** | **G29 冻结契约最小修订**（两态 + `landed` 语义 · **判定代码零改动** · 登记项 R-4） |
| **T049** | **FR-013** · **FR-026** | **SC-015** · **SC-011** | **发起者追认 R-4**（**阻断合入**） |
| **T050** | **FR-019** | **SC-009** | **SC-009 的「未装 `differential` 组」取证**（G22 隔离 venv / 未装该组的 venv） |
| **T051** | **FR-039** | **SC-034** | **独立验收脚本**（一条命令跑完全部验收闸口 V1–V12 · 裁定 34） |

> **SC 反向覆盖核对**（由上方正向表**逐条派生** · 保持两者一致）：
> SC-001 → T011 · SC-002 → T011 · SC-003 → T012/T013 · SC-004 → T015/T016/T017 ·
> SC-005 → T023/T024/T025/T026 · SC-006 → T021/T045/T046 · SC-007 → T021/T045/T046 ·
> SC-008 → T001/T029 · SC-009 → T008/T050 · SC-010 → T027/T029 · SC-011 → T010/T030/T034/T040/T048/T049 ·
> SC-012 → T028/T029 · SC-013 → T009/T018/T020/T037/T043 · SC-014 → T035/T036/T038 ·
> SC-015 → T014/T034/T048/T049 · SC-016 → T027 · SC-017 → T009 · SC-018 → T028/T032 ·
> SC-019 → T021/T031 · SC-020 → T022/T040/T044 · SC-021 → T019 · SC-022 → T020/T021 ·
> SC-023 → T037/T039 · SC-024 → T023/T025/T044 · SC-025 → T014 · SC-026 → T019 ·
> SC-027 → T013 · SC-028 → T021/T045 · SC-029 → T003/T030 · SC-030 → T009/T019/T039/T047 ·
> SC-031 → T041/T042/T043 · **SC-032 → T021/T045/T046**（**节点入参投影** · 裁定 32 ①）
> **SC-033 → T023/T024/T028**（**两个稀疏入口逐字相等** · 裁定 33 ④）
> **SC-034 → T051**（**独立验收脚本** · 裁定 34）
> ⇒ **33/33 全覆盖**（每条 SC 至少被一条任务映射 · 与上方正向表**逐条一致**）。
