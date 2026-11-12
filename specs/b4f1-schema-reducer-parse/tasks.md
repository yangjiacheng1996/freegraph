---

description: "B4F1 · 状态 schema 解析 + 归约器提取（TypedDict + Annotated → 通道规格）—— 任务清单"
---

# Tasks: B4F1 · 状态 schema 解析 + 归约器提取（`TypedDict` + `Annotated` → 通道规格）

**Input**: Design documents from `/specs/b4f1-schema-reducer-parse/`

**Prerequisites**:
- `plan.md`（必读 · 含 **Constitution Check** 与 **登记项 R-1**（宪法门禁 3/4/5 的偏离登记）·
  **Structure Decision**（模块切分与落位理由））
- `spec.md`（必读 · 含 **14 条裁定** + **10 条澄清问答 Q1–Q10** · FR-001 ~ FR-021 · SC-001 ~ SC-018）
- `research.md`（必读 · **13 条决策 D-01…D-13** · 全部附**实测证据** · 9 条遗留登记 DR-1…DR-9）
- `data-model.md`（必读 · 7 类实体 · **字段名逐字冻结** · 不变量 I-1…I-14）
- `contracts/binary-criterion.md`（**判据的唯一权威** · `<!-- authority: yes -->` · 16 类二元性形态 + 2 类提取形态 + 逐条上游 `路径:行号`）
- `contracts/schema-parse-contract.md`（解析契约 · 输入 / 输出 / 错误 / 不变量 / 边界）
- `quickstart.md`（**可照抄**的验证手册 · 10 节 · 9 个验收闸口）

**Tests**: **含**测试任务 —— 本 feature 的成功标准**全部**以断言形式给出（SC-001…SC-018），
且 spec **强制**要求：① A2 的**自包含判定表**（FR-016 ①-a·①-b · **16 + 2 类形态**）；
② 「非二元 callable 被拒绝」的**负向用例**（FR-017 · SC-014）；
③ 错误契约的**结构化字段**用例（SC-017）；
④ **`typing_extensions.TypedDict` 的正面接受路径**（SC-018 · 裁定 3 —— 否则验收基准的 schema 不可用）
⇒ 测试是**交付面的一部分**，不是可选项。

**Organization**: 任务按用户故事分组，每个故事可**独立实现、独立测试、独立交付**。

**本 feature 的可测判据总表**（**21 FR + 18 SC ↔ 57 条任务**）：
追溯见文末「**附录 · 任务 ↔ spec 追溯表**」——
**每个 FR 与每个 SC 均至少被一条任务映射**（**FR 21/21 · SC 18/18**）。
其中 **SC-004**（A2 判据一致）由 **T046**（判定表逐条比对）承载，
**SC-014**（负向用例）由 **T037** 承载，
**SC-017**（错误契约）由 **T006 + T040** 承载，
**SC-018**（`typing_extensions.TypedDict` 正面路径）由 **T057** 承载，
**T053**（**发起者追认** · plan 登记项 R-1）是**阻断合入**的任务。

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可并行（**不同文件**且无未完成依赖）——同一文件内的后续任务**不标** `[P]`
- **[Story]**：所属用户故事（US1…US4）；Setup / Foundational / Polish 阶段**不标**
- 每条任务都带**确切文件路径**；冻结面的**逐字内容**在 `contracts/` 与 `data-model.md` 中，
  本文件**只引用不复制**
- **逐条追溯**：每条任务对应的 **FR / SC** 见文末「**附录 · 任务 ↔ spec 追溯表**」
  （宪法原则 VI：「tasks MUST 逐条勾选、**可追溯到 spec 条目**」）

## Path Conventions

- 内核实现：`src/freegraph/runtime/`（**L2 执行内核层** · 层注册表**已登记** · 本 feature 首次创建该目录）
  - `__init__.py`（包声明 + L2 内部 API 的导出 · **不是**公开门面）
  - `errors.py`（`InvalidSchemaError`）
  - `reducer.py`（二元性判定 + 归约器提取）
  - `schema.py`（`ChannelSpec` / `SchemaSpec` / 解析主流程 / 类型解析 / 投影）
- 测试：`tests/runtime/`（与既有 `tests/contracts/` · `tests/facade/` · `tests/gates/` **平级** ·
  **自带** `__init__.py` ⇒ 模块名带包前缀 ⇒ 不会触发 pytest 的 `import file mismatch`）——
  **五个测试模块**：`test_schema_parse.py`（US1–US4 主断言）· `test_future_annotations.py`
  （**未来注解形态的隔离模块** · T016 / T024 的未来注解子用例）· `test_binary_criterion.py`（判定表比对）·
  `test_parse_contract.py`（契约守卫 + 零副作用）· `test_typed_dict_variants.py`
  （**`typing_extensions.TypedDict` 正面路径** · 独立文件以免污染 `sys.modules` 断言）
- 判据权威表：`specs/b4f1-schema-reducer-parse/contracts/binary-criterion.md`（**只读** · 测试解析它）
- 人工验证记录：`harness/verification/B4F1/manual-verification.md`
- **零改动清单**（本 feature **MUST NOT** 触碰）：`src/freegraph/__init__.py` ·
  `src/freegraph/graph.py` · `src/freegraph/contracts/**`（含 `errors.py` 的「唯一定义处」措辞
  —— **裁定 2** / research D-08）·
  `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` ·
  `tests/contracts/test_contract_regressions.py`（⚠️ **C4 / C8 的 `GATE-MOUNT:` 标记 MUST NOT 改成
  `landed`** —— C4 / C8 **未**由本 feature 落地 · 归属 B5F2 / B8F1）·
  `pyproject.toml`（三处依赖声明零新增）· `.github/workflows/ci.yml`（`testpaths = ["tests"]` ⇒ **零改动**即被收集）

> **⚠️ 落地顺序提示**：本 feature 的**红线**是「**不误判、不静默降级**」——
> 二元性判据写错的代价**只在运行期暴露**（提示词 §10）⇒
> 判定表（`contracts/binary-criterion.md`）是**判据的唯一权威**，实现 MUST 与它**逐条一致**
> （T046 在 Polish 阶段逐条比对 ⇒ 判据与实现不一致会**当场变红**）。

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 建立 L2 包骨架与测试骨架，并取「实现前」的绿基线

- [X] T001 建 `src/freegraph/runtime/` 包骨架：`src/freegraph/runtime/__init__.py`（**署名头** + 模块 docstring 为首个语句 + 包 docstring 写明「L2 执行内核层 · 状态 schema 解析 · 属 B4F1」） —— ⚠️ **MUST NOT** 在 `src/freegraph/__init__.py` 里 import 它（顶层包惰性 · 门禁 G1 / L-1）
- [X] T002 建测试包骨架：`tests/runtime/__init__.py`（**空文件即可** · 自带 `__init__.py` ⇒ 模块名带包前缀）
- [X] T003 建子进程夹具：`tests/runtime/conftest.py`（提供「在**子进程**里执行一段 Python 并回传 JSON」的夹具—— 用于测 `sys.modules` 增量 / 环境变量读取次数 / socket 连接次数；⚠️ **MUST 在子进程**执行，测试进程自身已导入 pytest ⇒ 同进程 `sys.modules` 不可用 · 沿用 B1F1 / B3F1 的既有口径）—— **计数口径 MUST 写死**（否则「次数 == 0」不可判定）：① **环境变量**：MUST 同时覆盖 `os.environ.__getitem__` / `os.environ.get` / `os.getenv` **三条**读取路径；② **出站**：MUST 同时覆盖 `socket.socket.connect` / `socket.create_connection` **两个**入口；③ **`sys.modules`**：「非标准库」判定 = 名字**不在** `sys.stdlib_module_names` 中**且**不是 `freegraph` 自身模块（SC-007 的字面口径）
- [X] T004 建判定表夹具：`tests/runtime/conftest.py`（提供「解析 `specs/b4f1-schema-reducer-parse/contracts/binary-criterion.md` 的 Markdown 表格 ⇒ 返回 `[(序号, 形态, 输入表达式, 期望, 上游来源)]`」的夹具 · research D-03 —— 与既有门禁 G25 解析 `layer-registry.md` **同构**；⚠️ **MUST NOT** 在测试里另抄一份表）—— **并提供「按名字求值」能力**：把「输入」列的表达式映射到 `contracts/binary-criterion.md` §4 **夹具清单**里的实际对象（求值命名空间 MUST 与该清单**逐名一致**）—— ⚠️ §2（16 类二元性形态）与 §3（2 类提取形态）的「输入」列**一律是 §4 里的名字**（§3 的两个是**元数据元组** `meta_non_callable` / `meta_multi_entry`）⇒ 求值路径**只有一套**
- [X] T005 **创建人工验证记录骨架**并取**实现前**绿基线：新建 `harness/verification/B4F1/manual-verification.md`（五段式小节标题 + **来源覆盖表**空表 —— ⚠️ T021 / T029 / T036 / T045 / T054 都要往该文件写 ⇒ 文件 MUST **最先**存在）⇒ 再跑 `uv run --no-project --python .venv python -m pytest tests/ -ra` （期望 **405 passed / 4 skipped**）⇒ 把**真实输出**记入该文件第 3 节

---

## Phase 2: Foundational（阻塞性前置）

**Purpose**: 全部用户故事共用的**底座**（数据契约 · 错误契约 · 二元性判据 · 类型解析 · 投影）
—— **不含**解析主流程（主流程属 US1）

**⚠️ CRITICAL**: 本 Phase 未完成前，**任何用户故事**都不得开工

- [X] T006 建 `src/freegraph/runtime/errors.py`：定义 `InvalidSchemaError(FreegraphError, ValueError)` （**双重继承** · 裁定 2 / 澄清 Q4）—— 结构化字段 `key: str | None`（出错的 key；schema 级错误为**空**）+ `reason: str`（**封闭取值域**：`not_a_typed_dict` / `reducer_not_binary` / `annotation_unresolvable`）；消息为**英文摘要** + 点名 key（沿用仓库既有约定 `src/freegraph/contracts/errors.py`）· ⚠️ **MUST NOT** 把该类型加进 `src/freegraph/contracts/__init__.py` 的 `__all__`（18 符号面是冻结面 · 门禁 G7）
- [X] T007 实现二元性判定：`src/freegraph/runtime/reducer.py` 的 `_is_binary_operator(candidate) -> bool` —— `inspect.signature(candidate)`；计数 = **位置专用 + 位置或关键字** **== 2**；`*args` / `**kwargs` / keyword-only **一律不计入**；签名取不到（`ValueError` / `TypeError`）⇒ **False**（research D-01 · 判据见 `contracts/binary-criterion.md` §1）
- [X] T008 实现归约器提取：`src/freegraph/runtime/reducer.py` 的 `_extract_reducer(annotation)` —— 取 `annotation.__metadata__[-1]`；末位**非** callable ⇒ 返回**空**；末位是 callable 但非二元 ⇒ 交由调用方按 **FR-007 ②** 报错；⚠️ **类**与**可调用对象实例**都**不**特殊排除（澄清 **Q6** · 裁定 9）
- [X] T009 定义 `src/freegraph/runtime/schema.py` 的 `ChannelSpec`：`@dataclass(frozen=True, slots=True, kw_only=True)` + **显式** `__hash__ = None`（research D-01）；6 个字段**逐字照** `data-model.md` §3：`key` / `value_type`（**基类型 `T`**）/ `reducer`（无则**空**）/ `has_reducer` / `semantics` / `required`；字段注释 MUST 引用 FR-020 ① 与澄清 **Q1** / **Q2**
- [X] T010 定义 `src/freegraph/runtime/schema.py` 的 `SchemaSpec`：同上的 dataclass 形态 + **显式** `__hash__ = None`；字段 `channels`（保序映射）+ `keys`（有序元组）；`__post_init__` 用 `object.__setattr__` 把 `channels` 包成 `types.MappingProxyType` ⇒ **结构性不可变**（research D-02 · data-model §4）
- [X] T011 实现类型解析辅助：`src/freegraph/runtime/schema.py` 的 `_resolve_annotations(schema)` —— `typing.get_type_hints(schema, include_extras=True)`（**保留 PEP 593 元数据**）；顶层 `Required[...]` / `NotRequired[...]` **先剥离**再取元数据（裁定 4 · FR-008）；解析失败时**逐 key 探针**以**指名出错 key**（research D-04）—— **探针形态 MUST 写死**：① 用**函数式** `TypedDict("_Probe", {key: ann})`，`ann` MUST 取自 `schema.__annotations__`（TypedDict 的 `__annotations__` **已合并继承链** · CPython `_TypedDictMeta` 的既有行为 ⇒ **父类上的坏注解同样能被指名**）；② MUST NOT 手工 `eval` 注解字符串（命名空间解析必须与 `get_type_hints` 一致）
- [X] T012 实现投影方法：`src/freegraph/runtime/schema.py` 的 `ChannelSpec.to_dict()` 与 `SchemaSpec.to_dict()` —— JSON 友好；「类型可读文本」口径 = 类取 `__name__`、其余 `str()` 去 `typing.` 前缀（research D-05）；**归约器标识** = 4 级规则（`__module__`+`__qualname__` → 其**类型**的 → `__name__` → `repr` 抹除 `0x…`） （research D-06 · FR-011）
- [X] T013 导出 L2 内部 API：`src/freegraph/runtime/__init__.py` 导出 `ChannelSpec` / `SchemaSpec` / `InvalidSchemaError`（⚠️ **此时不含** `parse_state_schema` —— 属 US1 的 T018）· docstring MUST 写明「**L2 内部 API · 不是公开门面**」（公开门面仍是 7 个符号 · 门禁 G15 / G19）

**Checkpoint**: 底座就位（数据契约 + 错误契约 + 判据 + 类型解析 + 投影）—— 用户故事可开工

---

## Phase 3: User Story 1 - 追加语义被正确识别（Priority: P1）🎯 MVP

**Goal**: `Annotated[list[AnyMessage], operator.add]` 的归约器被**正确识别**并**按引用**持有；
解析**不调用**它

**Independent Test**: 解析一份只含 `messages: Annotated[list, operator.add]` 的 schema ⇒
断言 `spec.channels["messages"].reducer is operator.add`（**身份**判定）+ `has_reducer is True` +
`semantics == "reduce"`

### Tests for User Story 1（MUST 先写 · MUST 先失败）

- [X] T014 [P] [US1] 写测试：`tests/runtime/test_schema_parse.py` —— 断言 `Annotated[list, operator.add]` 的通道规格满足**四项**（与 spec SC-001 逐项对应）：① `reducer is operator.add`（**身份**）· ② `has_reducer is True` · ③ `semantics == "reduce"` · ④ `value_type is list`（**归约前的基类型 `T`** · 无 `Annotated` 包装）—— ⚠️ 「二元性」**不落字段**（FR-020 ①）⇒ 本条**不**断言「二元性标记」，其可判定形式见 T046（判定表逐条比对）；验收基准同构形态（`typing_extensions` + `list[AnyMessage]`）由 **T057** 承载
- [X] T015 [P] [US1] 写测试：`tests/runtime/test_schema_parse.py` —— 断言归约器**引用保持**（`spec.reducer is operator.add`）+ 解析期**调用次数 == 0**（用一个会记账的 reducer 验证它没被调用）—— 另含两条 Edge Case：① **同一个 callable 被两个 key 共用** ⇒ 两条规格持**同一引用**（不复制）；② **有状态的归约器**（闭包 / 可变默认参数）⇒ 按引用持有、**不重置**其状态（状态归用户负责）
- [X] T016 [P] [US1] 写测试：`tests/runtime/test_schema_parse.py` —— 断言 `Required[Annotated[list, operator.add]]` 与 `NotRequired[Annotated[list, operator.add]]` 的归约器**不被漏掉**（裁定 4 · FR-008）—— 另含一条 Edge Case：**未来注解**（`from __future__ import annotations`）下**仍能解析出归约器**（该形态下 `__annotations__` 的值是 `ForwardRef` ⇒ 解析路径须能求值）—— ⚠️ **隔离要求**：该形态 MUST 放在**独立测试模块** `tests/runtime/test_future_annotations.py` 内（**模块名逐字固定**），**MUST NOT** 在 `tests/runtime/test_schema_parse.py` 里整体开启 `from __future__ import annotations`（否则该文件内**所有** schema 的注解都变成字符串，须模块级 import `operator` / `Annotated` / `Required` / `NotRequired` 才能求值，且会与 T039 的「注解不可解析」用例**相互干扰** ⇒ 无法区分「真不可解析」与「作用域没解析到」）；⚠️ **T024 的「未来注解 ⇒ 必选」用例亦落在该独立模块**（见 T024）

### Implementation for User Story 1

- [X] T017 [US1] 实现解析主流程：`src/freegraph/runtime/schema.py` 的 `parse_state_schema(schema) -> SchemaSpec` —— 校验 schema 是 `TypedDict`（FR-001 ① 的鸭子判定）→ `_resolve_annotations` → 按 key 顺序遍历 → 剥离 `Required` / `NotRequired` → 取**基类型**与**末位元数据** → `_extract_reducer` → 落位 `reducer` / `has_reducer` / `semantics` / `required` → 组装 `SchemaSpec`（保序）
- [X] T018 [US1] 导出解析入口：`src/freegraph/runtime/__init__.py` 增补 `parse_state_schema` （research D-07 · 落点 `freegraph.runtime`；⚠️ **MUST NOT** 进 `src/freegraph/graph.py` 门面）
- [X] T019 [US1] 接入投影中的归约器标识：`src/freegraph/runtime/schema.py` —— 已带归约器的通道，其 `to_dict()` 的 `reducer` 字段 MUST 是**可读标识**（research D-06 4 级规则），**不是** `repr` 原文
- [X] T020 [US1] 跑 US1 用例：`uv run --no-project --python .venv python -m pytest tests/runtime/ -ra` ⇒ T014–T016 **全绿**
- [X] T021 [US1] 跑 quickstart **§1**（`quickstart.md`）⇒ 把**真实输出**贴进 `harness/verification/B4F1/manual-verification.md` 第 3 节（⚠️ MUST NOT 写「符合预期」）

**Checkpoint**: US1 独立可验收（**A1 验收判据**成立）—— MVP 达成

---

## Phase 4: User Story 2 - 计数型 key 走默认覆盖（Priority: P2）

**Goal**: 无归约器的 key 被标记为**默认覆盖**（C3）；每个 key 恰一条规格；必填性**只记录不执行**

**Independent Test**: 解析一份含 `llm_calls: int`（无 `Annotated`）的 schema ⇒
断言该键 `reducer is None` + `has_reducer is False` + `semantics == "overwrite"`；
且规格条数 == key 数

### Tests for User Story 2（MUST 先写 · MUST 先失败）

- [X] T022 [P] [US2] 写测试：`tests/runtime/test_schema_parse.py` —— 断言无 `Annotated` 的 key ⇒ `reducer is None` · `has_reducer is False` · `semantics == "overwrite"`
- [X] T023 [P] [US2] 写测试：`tests/runtime/test_schema_parse.py` —— 断言**规格条数 == schema 的 key 数**（含继承链上的 key）· **保序**（父类 key 在前 · 子类新 key 在后 · 同名覆盖**保持原位**）· 名为 `__slots__` 的伪 key **不计入**条数 —— 另含一条 Edge Case：**空 TypedDict（零个 key）** ⇒ **零条规格**（**合法**，**不报错**）
- [X] T024 [P] [US2] 写测试：`tests/runtime/test_schema_parse.py` —— 断言**必填性标记**：`total=False` 与 `NotRequired[...]` ⇒ `required is False`；`Required[...]` 与默认全必选 ⇒ `required is True`；未来注解（`from __future__ import annotations`）下的 key ⇒ **一律** `required is True`（FR-021 ③）—— ⚠️ **该「未来注解」子用例 MUST 落在 T016 的独立模块** `tests/runtime/test_future_annotations.py` 内（**MUST NOT** 在 `test_schema_parse.py` 里引入未来注解 · T016 的隔离要求）—— 另加一条**否定断言**：**缺必填 key 的 schema 仍解析成功** ⇒ 证明本 feature **不执行任何必填性校验**（FR-021 ② · 校验归 B7F3）

### Implementation for User Story 2

- [X] T025 [US2] 实现「无归约器 ⇒ 覆盖语义」的落位：`src/freegraph/runtime/schema.py` —— 无归约器的 key MUST 标记 `semantics = "overwrite"`（FR-006 ① · C3）；⚠️ 本 feature **只标记**，MUST NOT 执行覆盖（执行属 **B5F1**）
- [X] T026 [US2] 实现必填性标记：`src/freegraph/runtime/schema.py` —— 取值来源 MUST 是 `__required_keys__` / `__optional_keys__`（**照抄** · MUST NOT 自造判定逻辑 · FR-021 ③）；⚠️ **MUST NOT** 在本 feature 执行任何必填性校验（校验属 **B7F3**）
- [X] T027 [US2] 实现保序与伪 key 跳过：`src/freegraph/runtime/schema.py` —— `keys` 序列 MUST 是 `get_type_hints` 的**插入序**（research D-10）；名为 `__slots__` 的 key MUST 被跳过（裁定 12）
- [X] T028 [US2] 跑 US2 用例：`uv run --no-project --python .venv python -m pytest tests/runtime/ -ra`
- [X] T029 [US2] 跑 quickstart **§2** 与 **§7** ⇒ 把**真实输出**贴进 `harness/verification/B4F1/manual-verification.md` 第 3 节

**Checkpoint**: US2 独立可验收（**A3 验收判据**成立）

---

## Phase 5: User Story 3 - 别的 `Annotated` 用法不被误判（Priority: P3）

**Goal**: 末位**非** callable 的元数据**不**被当成归约器、**不**报错；多条目只认末位；
类与可调用实例按**机械判定**处理

**Independent Test**: 解析一份含 `note: Annotated[int, "说明文字"]` 的 schema ⇒
断言该键 `has_reducer is False` + `semantics == "overwrite"` 且**解析成功**

### Tests for User Story 3（MUST 先写 · MUST 先失败）

- [X] T030 [P] [US3] 写测试：`tests/runtime/test_schema_parse.py` —— 断言末位**非** callable （字符串元数据）⇒ **无归约器**且**解析成功**（**不报错**）
- [X] T031 [P] [US3] 写测试：`tests/runtime/test_schema_parse.py` —— 断言多条目元数据 （`Annotated[list, "描述", operator.add]`）⇒ **只认末位**（`reducer is operator.add`）
- [X] T032 [P] [US3] 写测试：`tests/runtime/test_schema_parse.py` —— 断言**类 / 可调用实例**按 **机械判定**（澄清 **Q6** · 裁定 9）：`ClassTwoArgInit`（`__init__(self, a, b)`）⇒ **被接受**为归约器；`ClassNoInit` / `ClassOneArgInit` / `CallableKwOnlyInstance` ⇒ **被拒绝**（抛 schema 错误）

### Implementation for User Story 3

- [X] T033 [US3] 实现「末位非 callable ⇒ 不视为归约器」的分支：`src/freegraph/runtime/schema.py` —— 与「无 `Annotated`」共用同一落位，但 MUST **不报错**（FR-003 ① · P3）；⚠️ 代码注释 MUST 标明裁定 9 / 澄清 **Q6**（类与实例**不**特殊排除）
- [X] T034 [US3] 实现多条目只认末位的分支：`src/freegraph/runtime/schema.py` —— 前面的元数据条目 MUST **不**影响判定、也 MUST **不**进入 `value_type`（FR-005）
- [X] T035 [US3] 跑 US3 用例：`uv run --no-project --python .venv python -m pytest tests/runtime/ -ra`
- [X] T036 [US3] 跑 quickstart **§3** ⇒ 把**真实输出**贴进 `harness/verification/B4F1/manual-verification.md` 第 3 节

**Checkpoint**: US3 独立可验收（误判方向被堵死）

---

## Phase 6: User Story 4 - 写错的 schema 在解析期就报错（Priority: P4）

**Goal**: 三类非法输入**显式失败**（**绝不**静默降级为「覆盖」），错误**快速失败**且带**结构化字段**

**Independent Test**: 解析一份含 3 参函数的 schema ⇒ 断言抛出 schema 错误、
`e.key` 指名该 key、`e.reason == "reducer_not_binary"`，且 `except FreegraphError` / `except ValueError` 均可捕获

### Tests for User Story 4（MUST 先写 · MUST 先失败）

- [X] T037 [P] [US4] 写**负向用例**：`tests/runtime/test_schema_parse.py` —— 断言**五类**非二元候选 **被拒绝**并抛 schema 错误：**3 参函数 / 1 参函数 / 类（`__init__` 非 2 位置参者）/ 内置类型（签名不可取）/ `*args` 形态**（FR-017 · SC-014；⚠️ 每例 MUST 断言「抛错」而非「静默降级」）
- [X] T038 [P] [US4] 写测试：`tests/runtime/test_schema_parse.py` —— 断言**非 `TypedDict`** 输入 （普通 `dict` / `dict[str, int]` / **模型实例** / **Pydantic 形态的替身**）⇒ `reason == "not_a_typed_dict"` 且 `e.key is None`；⚠️ MUST NOT 抛裸 `TypeError` —— **「Pydantic 形态」的替身口径**（v1.0 **零依赖** · 宪法 v1.7.0 + FR-019「开发期依赖组三处零新增」⇒ **MUST NOT** 把 `pydantic` 写进 `pyproject.toml` 任何一处、**MUST NOT** 依赖本机是否装了它）：用**零依赖替身类**代替（`class _FakeModel:` + `__annotations__` + **不是** `dict` 子类 —— 与 Pydantic `BaseModel` 的结构特征一致 ⇒ 鸭子判定同样拒绝）；若测试环境**恰好**装了 `pydantic`，可**额外**用真身 `BaseModel` 子类断言一次，但该例 MUST 用 `pytest.importorskip("pydantic")` 兜底（**不许**因此新增依赖声明）—— ⚠️ **`importorskip` MUST 置于**测试函数内**（MUST NOT 置于模块级：模块级 skip 会连带跳过本文件内**其余全部**用例 ⇒ 闸口 A4 的 SC-006 / SC-017 在未装 `pydantic` 的环境里**静默不被执行**）
- [X] T039 [P] [US4] 写测试：`tests/runtime/test_schema_parse.py` —— 断言**注解不可解析**（未来注解下的 未定义名）⇒ `reason == "annotation_unresolvable"` 且 `e.key` **指名出错 key** —— ⚠️ 该用例 MUST 用**显式字符串注解**（`bad: "Annotated[list[Missing], operator.add]"` 或独立模块的未来注解）构造（**非**未来注解下 `Annotated[...]` 是立即求值的表达式 ⇒ 会在**类定义时**就抛 `NameError`，构造不出该分支 · research D-04）—— 另含一条**继承链变体**：坏注解放在**父类**上（`class P(TypedDict): bad: …` + `class C(P): …`）⇒ 仍 MUST 指名 `bad`（TypedDict 的 `__annotations__` **已合并继承链** · research D-04）
- [X] T040 [P] [US4] 写测试：`tests/runtime/test_schema_parse.py` —— 断言**快速失败**（一份含多个问题的 schema **只报第一个**）· 结构化字段**齐备**（`key` + `reason`）· `reason` ∈ 封闭集合 · `except FreegraphError` 与 `except ValueError` **均**能捕获（SC-006 / SC-017）

### Implementation for User Story 4

- [X] T041 [US4] 实现三处错误抛出点：`src/freegraph/runtime/schema.py` —— ① 非 `TypedDict` ⇒ `InvalidSchemaError(key=None, reason="not_a_typed_dict")`；② 末位 callable 但非二元 ⇒ `InvalidSchemaError(key=该 key, reason="reducer_not_binary")`；③ 注解解析失败 ⇒ `InvalidSchemaError(key=该 key, reason="annotation_unresolvable")` （⚠️ **MUST NOT** 抛裸 `TypeError` / `NameError` / `AttributeError` · FR-007）
- [X] T042 [US4] 实现「快速失败」：`src/freegraph/runtime/schema.py` —— 按 key 的解析顺序逐个检查，命中**第一个**问题即抛出（MUST NOT 汇总多个问题 · 澄清 **Q3**）
- [X] T043 [US4] 复核错误消息：`src/freegraph/runtime/errors.py` —— 消息 MUST 是**英文摘要**且**点名 key**（沿用仓库既有约定）；⚠️ 上层 MUST **无须**解析消息即可取到全部细节（结构化字段承载）
- [X] T044 [US4] 跑 US4 用例：`uv run --no-project --python .venv python -m pytest tests/runtime/ -ra`
- [X] T045 [US4] 跑 quickstart **§4** ⇒ 把**真实输出**贴进 `harness/verification/B4F1/manual-verification.md` 第 3 节

**Checkpoint**: US4 独立可验收（错误在**解析期**暴露，而不是运行期）

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 判定表逐条比对、契约守卫、零副作用断言、纪律复核与人工门禁

- [X] T046 [P] 写判定表比对测试：`tests/runtime/test_binary_criterion.py` —— 解析 `specs/b4f1-schema-reducer-parse/contracts/binary-criterion.md` 的 §2（16 类二元性形态）与 §3（2 类提取形态）⇒ **逐条**比对解析判定结果；每条 MUST 带**非空**的上游 `路径:行号` ⇒ **缺失条数 == 0** · **无来源项数 == 0**（SC-004 · FR-016 ①-a·①-b）—— ⚠️ **覆盖面下限 MUST 有独立断言**（否则删表行仍绿）：断言 §2 行数 **== 16**（FR-016 ①-a 的覆盖面 · SC-004「缺失条数 == 0」）· §3 行数 **== 2**；并断言 §2 / §3 的「输入」列的**每个名字**都能在 §4 夹具清单中**找到**（求值命名空间逐名一致）
- [X] T047 [P] 写契约守卫测试：`tests/runtime/test_parse_contract.py` —— 断言 **不可变**（改属性抛 `FrozenInstanceError` · `channels` 写操作抛 `TypeError`）· **可比较**（同一 schema 两次解析相等 · ⚠️ 「不等」的差异源 MUST 取自**产物内容**（键集合 / `value_type` / `reducer` 任一不同）—— **MUST NOT** 用「类名不同」当差异源：两个**内容相同、仅类名不同**的 `TypedDict` 解析结果**必然相等** ⇒ 会假红 · SC-005 的字面口径）· 投影**可 JSON 序列化**且 **不含内存地址形态**（`0x…`）· 两个产物类型**显式不可哈希**（SC-005 · I-7…I-8·I-9）
- [X] T048 [P] 写零副作用断言：`tests/runtime/test_parse_contract.py` —— 用 T003 的**子进程**夹具断言 解析前后 `sys.modules` 增量的**非标准库**条目数 == 0 · **环境变量读取次数 == 0** · **出站连接次数 == 0** · 归约器**调用次数 == 0**（SC-007 · FR-013）—— 另加一条 **import 期**断言（⚠️ **MUST 在子进程内执行** —— 测试进程已被 T038 / T057 导入 `pydantic` / `typing_extensions`，进程内 `sys.modules` 必然含之 ⇒ **进程内断言必假红**）：`import freegraph.runtime` **之后** `sys.modules` 中 `pydantic` / `typing_extensions` / `langchain*` / `langgraph*` / `langsmith` 的**条目数 == 0**（SC-011 的字面口径 · 只查「解析前后增量」会漏掉**导入期**引入）
- [X] T049 复核**零新增依赖声明与零公开面变化**：`pyproject.toml`（`dependencies` / `[project.optional-dependencies]` / `[dependency-groups]` **三处零改动** · ⚠️ **MUST NOT** 把 `langchain*` 写进任何一处 · 澄清 **Q5**）· `.github/workflows/ci.yml` 的安装步骤**不含** `langgraph`（**第 4 处**声明位 · FR-016 ③）—— 且 MUST 有**可机读断言**：扫描 `.github/workflows/ci.yml` 全文，`langgraph` 出现次数 == **0**（SC-004 的「CI 作业内安装次数 == 0」· 不止于人工复核）· `src/freegraph/contracts/__init__.py` 的 `__all__` **仍为 18 个** · `src/freegraph/graph.py` 的 `__all__` **仍为 7 个**（SC-011 / SC-015 · FR-015 / FR-019）
- [X] T050 复核**层纪律**：`specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` **零改动**（`src/freegraph/runtime/` 已在其中登记为 **L2**）· 新增代码的 import 图**无 L2 → L3/L4/L5 的边** · 既有门禁 **G25 / G30** 仍全绿 · **门禁编号总数仍为 30**（SC-012 · research D-09）
- [X] T051 复核**署名头与 docstring**：`src/freegraph/runtime/*.py` 与 `tests/runtime/*.py` 每个文件 MUST 带署名头且模块 docstring 为首个语句（既有门禁 **G30** 全仓扫描自动覆盖 · FR-019）
- [X] T052 **回填**人工验证记录：`harness/verification/B4F1/manual-verification.md`（**骨架已由 T005 创建**）—— **五段式**各小节填齐（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）+ **来源覆盖表**（每条判据 → 上游 `路径:行号` / Q8 条号 / 宪法条款号）；**A1–A3 逐条给出结论**（SC-013 · FR-018）；⚠️ 未实跑的项 MUST 显式记入「遗留问题」，MUST NOT 伪造输出
- [X] T053 **发起者追认**（**阻断合入**）：把 plan 的**登记项 R-1**（宪法「质量门禁 3 / 4 / 5」在本 feature 物理不可达成：门禁 3 的 C4 / C8 两条独立回归 · 门禁 4 的 fake 模型轮 · 门禁 5 的真实模型一轮） 的**偏离登记**交发起者追认，追认文字 MUST 落在 `harness/verification/B4F1/manual-verification.md` （含追认文字 + 发起者确认 + 日期）⇒ ⚠️ **未追认前 MUST NOT 合入** · MUST NOT 代签 · MUST NOT 改宪法正文 · MUST NOT 把 `tests/contracts/test_contract_regressions.py` 的 `GATE-MOUNT:` 标记改成 `landed`（C4 / C8 未由本 feature 落地）
  > **📌 已完成（2026-11-08 · 发起者）**：追认栏已填（追认人 **杨家成** · 结论 **追认** ·
  > 日期 2026-11-08）⇒ 落 `harness/verification/B4F1/manual-verification.md` **§4.3** ⇒
  > 执行闸口 **A5** 通过。追认由**发起者本人**作出（明示「验收通过了」），实现者
  > **未代签** · **未**改宪法正文 · **未**把 `GATE-MOUNT: C4 / C8` 改成 `landed`
  > （仍是 `status=not-landed` · owner=B5F2/B8F1）⇒ **C4 / C8 未由本 feature 落地**。
- [X] T054 跑 quickstart **全文**（§0 – §10）⇒ 把**真实输出**逐节贴进 `harness/verification/B4F1/manual-verification.md` 第 3 节 （⚠️ §1 起的命令在实现完成后才可执行）
- [X] T055 复核**兼容矩阵零新增行**：`README.md` 的「API 兼容矩阵」**不新增**本 feature 的行 （零新增公开 API · 判定口径 = 契约层 **18** + 门面 **7**；`freegraph.runtime` 的 4 个导出属 **L2 内部 API**（可 import，但不承诺稳定）⇒ **不进兼容矩阵** · SC-015）⇒ 并在人工验证记录中**显式记「无新增」**（以区别于「漏更新」· FR-018）—— ⚠️ MUST 有**可机读断言**：解析 README 的兼容矩阵表 ⇒ 其 freegraph 符号集合与**变更前**集合**恒等**（行数不变 ⇒ 防「漏更新」与「误新增」双向漂移）
- [X] T056 复核 `THIRD_PARTY_NOTICES` **无需新增登记**（本 feature 零新增第三方依赖 · FR-019 · 原则 X）
- [X] T057 写 **`typing_extensions.TypedDict` 正面路径**守卫测试：`tests/runtime/test_typed_dict_variants.py`（★ **独立文件** —— MUST NOT 写进 `tests/runtime/test_parse_contract.py`：pytest 的**收集期**会 import 本模块 ⇒ 同进程内 `sys.modules` 必含 `typing_extensions` ⇒ T048 的「导入后无 `typing_extensions`」断言**必假红**）—— 用 **`typing_extensions`** 构造一份与 `harness/demo/target.py:59-61` **同构**的 schema（`messages: Annotated[list[AnyMessage], operator.add]` + `llm_calls: int`）⇒ 断言**解析成功**（**不得**被判成「非 `TypedDict`」）· `messages` 的 `reducer is operator.add`（**身份**）· `has_reducer is True` · `semantics == "reduce"` · `llm_calls` 的 `reducer is None` + `semantics == "overwrite"`（SC-018 · 裁定 3 · FR-001 ①）—— ⚠️ **依赖纪律**：被测 schema 由**测试代码**用 `typing_extensions` 构造；freegraph 侧 **MUST NOT** import 它（FR-001 ② · FR-013 · SC-011）⇒ **MUST NOT** 把 `typing_extensions` 写进 `pyproject.toml` 的任何一处（FR-016 ② · FR-019）—— ⚠️ 若测试环境**未装** `typing_extensions`，该例 MUST 用 `pytest.importorskip("typing_extensions")` 兜底（**MUST NOT** 因此新增依赖声明）—— ⚠️ **`importorskip` MUST 置于**测试函数内**（MUST NOT 置于模块级）—— ⚠️ **本例是「环境依赖型」判据**（`typing_extensions` **不是声明依赖**；CI 的可得性来自步骤 5.5 的 v2.0 预验证包的**传递带入**）⇒ **skip ≠ pass**：若被 skip，MUST 记入 `harness/verification/B4F1/manual-verification.md` 的「遗留问题」节
- [X] T058 **补人工验收脚本**（**发起者追加 · 2026-11-08**）：落 `harness/verification/B4F1/acceptance.py`（**单文件 · 零第三方依赖 · 可独立运行**）⇒ 把 A1–A3 与 SC-001…SC-018 逐条落成**可判定的断言**（**89 条**），**一条命令**即可完成人工验收 ⇒ 落点沿用 **B1F1 / B2F1 / B2F2** 的既有形态（`harness/verification/README.md` 的「验收脚本」约定）—— ⚠️ **判定表不另抄一份**：脚本**解析** `contracts/binary-criterion.md`（**唯一权威** · research D-03）⇒ 判据与用例天然分离 —— ⚠️ **两态运行**（已安装 ⇒ 测发行产物；未安装 ⇒ 注入 `<repo>/src` 测源码树 + 标「◌ 环境未就绪」）—— ⚠️ `--record out.md` 产出**五段式**记录片段（可直接并入人工验证记录）—— ⚠️ **零新增依赖声明**（只用标准库 + 被验的 freegraph 本身）—— ⚠️ **`typing_extensions` 判据是「环境依赖型」**：未装时**不判失败**但标「◌」（**skip ≠ pass**）
  > **📌 追加理由与口径变更**：本 feature 原按 `harness/verification/README.md` 的
  > 「`acceptance.py` **可选**」判定为**不落**（B3F1 同款）⇒ **发起者于人工验收环节要求**
  > 「一条命令跑完全部验收」⇒ **补落**本脚本 ⇒ 该 README 的判定依据（「判据能否脱离
  > `pytest` 单独跑成一段脚本」）对本 feature **成立**（判据是纯计算 · 零依赖）⇒
  > README 的「无此类脚本的 feature」举例（B3F1 / B4F1）**随之更新**（见 T059）。
- [X] T059 **同步** `harness/verification/README.md`（文档合规 · 原则 X）：① 「验收脚本」索引表的 **B4F1** 行补上 `acceptance.py` 链接与「**89 条断言全绿**」的实测结论；② 「`acceptance.py` 可选」一节的举例**去掉 B4F1**（本 feature **已落**该脚本）⇒ 判定依据（判据能否脱离 `pytest` 单独跑成一段脚本）对 B4F1 **成立** ⇒ 仍保留 **B3F1** 作为「无此类脚本」的举例 —— ⚠️ **零改动**该 README 的**目录约定**与**五段式**定义（宪法原则 V 的落点）
- [X] T060 **修订 quickstart §6 的演示手段**（**实现者实测发现 · 发起者确认后执行 · 2026-11-08**）：该节原用 `dataclasses.replace(a.channels['n'], key='zzz')` 演示「字段不可改」，但 `dataclasses.replace` 的语义是「**基于现有实例构造一个新实例**」⇒ 它**不**（也**不应当**）抛异常 ⇒ 该段**没有任何输出**，与该节的「期望输出」**不一致** ⇒ **会让正确的实现看起来是坏的** ⇒ 改为**直接赋值**（`a.channels['n'].key = 'zzz'` · frozen dataclass ⇒ `FrozenInstanceError`）—— ⚠️ **判据一字未改**（SC-005 · FR-010 · I-7），本次修订**只换演示手段** ⇒ 并在该节留**修订记**（含原写法的问题与实测结论）—— ⚠️ `quickstart.md` **不是**跨 feature 的**冻结契约**（无 `<!-- authority: yes -->` 标记）⇒ 改它**不触碰**任何冻结面 ⇒ 人工验证记录 §3.7 同步贴出修订后的**真实输出**（与「期望输出」逐行一致）· §5 遗留 #2 **关闭**

---

## Dependencies & Execution Order

> **⚠️ 执行策略**：**不逐任务人工确认**，改为「**批量执行 + Phase 闸口**」——
> 每个 Phase 结束 MUST 跑一次可机读的闸口验证，闸口全绿才进下一 Phase。
> **折中**：**Phase 3–6 批量执行**、**Phase 1 / 2 / 7 逐任务过**
> （Phase 1–2 是底座，写错了后面全错；Phase 7 是人工验证记录与合规同步，本质是人工活）。

### 执行闸口（Phase 闸口 · 每道 MUST 全绿才进下一 Phase）

| 闸口 | 触发点 | MUST 验证 | 关联判据 |
|---|---|---|---|
| **A1** | Phase 1–2 结束 | `ChannelSpec` / `SchemaSpec` / `InvalidSchemaError` 三个类型就位且**不可变** · 二元性判定与 `contracts/binary-criterion.md` **§2 判定表**逐条一致 · `pytest tests/ -ra` **仍全绿**（既有门禁零破坏）· 层注册表**零改动** | FR-004 · FR-009 · FR-010 · FR-014 · FR-020 |
| **A2** | Phase 3 结束（US1） | `Annotated[list, operator.add]` 的归约器**身份**判定成立（`is operator.add`）· 引用保持率 100% · 调用次数 == 0 · `Required[...]` 包裹的归约器**不漏** | FR-003 · FR-008 · FR-012 · SC-001 · SC-009 · SC-010（**A1 验收判据**） |
| **A3** | Phase 4–6 结束（US2–US4） | 无归约器 key ⇒ `overwrite`（**A3 验收判据**）· 末位非 callable **不误判** · 五类负向用例**全绿** · 错误契约字段齐备且原因码 ∈ 封闭集合 · 快速失败（只报第一个） | FR-005 · FR-006 · FR-007 · FR-017 · FR-021 · SC-002 · SC-003 · SC-006 · SC-014 · SC-016 · SC-017（**A2 / A3 验收判据**） |
| **A4** | Phase 7 结束（**最关键**） | 判定表**逐条**比对一致（缺失 == 0 · 无来源 == 0 · **行数 16 / 2 达标**）· 零副作用三断言全绿（`sys.modules` / 环境变量 / 出站）+ **import 期无第三方模块** · 依赖**三处声明 + `ci.yml` 安装步骤**零新增 `langchain*` · 公开面 18 / 7 未变 · 层纪律与署名头复核通过 · **`typing_extensions.TypedDict` 被接受**（SC-018 · **未 skip 时**须 pass；被 skip 须记入人工验证记录 ⇒ **skip ≠ pass**）⇒ 满足 PR-4「每个 feature 必须能独立通过门禁」 | FR-001 · FR-011 · FR-013 · FR-016 · FR-019 · SC-004 · SC-005 · SC-007 · SC-011 · SC-012 · SC-015 · SC-018 |
| **A5** | 收官 | **T053 发起者追认**（登记项 R-1 · **阻断合入**）· 人工验证记录五段式 + 来源覆盖表齐全 · **A1–A3 逐条有结论** · quickstart 全文绿 | FR-018 · SC-013（**A4**） |

> **📌 编号说明（**四套**编号 · 同名不同义）**：本表的 **A1–A5 是「执行闸口」**（Phase 闸口）——
> 而 spec 的「**验收判据 A1–A3**」是**引文 §6 / 立项书 §5.2** 的编号
> （A1 二元归约器识别 · A2 与上游判据一致 · A3 无归约器走覆盖）；
> `quickstart.md` §10 的**验收闸口**原编号 A1–A9 已**改名为 V1–V9**（Verification gates · 2026-11-08 分析轮）⇒
> **四套编号互不撞名**（验收判据 A1–A3 · 执行闸口 A1–A5 · quickstart 闸口 V1–V9 · 宪法门禁 G1–G30）⇒
> 引用时 MUST 带限定语（「验收判据 A1（引文 §6）」/「执行闸口 A1」/「quickstart 闸口 V1」）。

### MUST 由发起者亲自出面的闸口（实现阶段只能「备料」，不得代劳）

- **T053 —— 宪法质量门禁 3 / 4 / 5 的偏离登记追认**（plan 登记项 R-1）：三条**共享同一根因**
  （验收基线跑通需要**内核运行时**，而内核运行时按 立项书 §6.2 属 M1 尾 / M2；本 feature 属
  **M1 的解析侧**、**不交付通道与运行时**）⇒ 依宪法 **v1.6.0** 的窄口径通则处置
  ⇒ 实现 MUST **停下来等追认**，MUST NOT 代签（**MUST NOT** 改宪法正文、**MUST NOT** 写一条永久红的 CI、
  **MUST NOT** 把 C4 / C8 的 `GATE-MOUNT:` 标记改成 `landed`）。
  > **📌 承接方已具名且未变**：**B5F2**（C4 · M1）· **B8F1**（C8 · M2）· **B7F2 / B7F3**（fake 轮）·
  > **B25F1**（真实模型轮）⇒ **不悬空**（宪法 v1.6.0 的红线之一）。

### Phase Dependencies

- **Setup（Phase 1）**：无依赖 —— 可立即开始
- **Foundational（Phase 2）**：依赖 Setup —— **阻塞全部用户故事**
- **用户故事（Phase 3–6）**：全部依赖 Phase 2 完成 ⇒ 之后可**并行**（若人手够）或按 **P1 → P2 → P3 → P4** 顺序
- **Polish（Phase 7）**：依赖全部目标用户故事完成

### User Story Dependencies

- **US1（P1）**：Phase 2 后可开始 —— **不依赖**其他故事（**MVP**）
- **US2（P2）**：Phase 2 后可开始 —— 与 US1 共用底座，但**独立可测**
- **US3（P3）**：Phase 2 后可开始 —— 与 US1 共用归约器提取，**独立可测**
- **US4（P4）**：Phase 2 后可开始 —— 与 US1/US3 共用错误契约，**独立可测**

### Within Each User Story

- **测试 MUST 先写且 MUST 先失败**（本 feature 的测试即判据）
- 数据类型与判据（Foundational）→ 主流程（US1）→ 各分支（US2–US4）→ 守卫与纪律（Polish）
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**：T002 · T003 · T004 三条可并行（不同文件 / 同一 conftest 的**不同函数** ⇒ 落盘同文件须串行）
- **Phase 2**：T007 · T008 可并行（`reducer.py` 的两个函数，落盘同文件须串行）；
  T009 · T010 · T012 可并行（`schema.py` 的**不同**类型 ⇒ 落盘同文件须串行）
- **Phase 3–6**：每个故事的**测试任务**（`[P]`）可并行；跨故事的测试文件**同一文件** ⇒ 落盘须串行
- **Phase 7**：T046 · T047 · T048 · T057 四条可并行（**四个不同测试文件**：T046 `test_binary_criterion.py` ·
  T047 / T048 `test_parse_contract.py`（**同文件 ⇒ 二者落盘须串行**）· T057 `test_typed_dict_variants.py`）
- 不同用户故事可由不同成员并行推进（底座 Phase 2 完成后）

---

## Parallel Example: User Story 1

```bash
# 三条测试任务（不同断言组 · 同一文件 ⇒ 编写可并行，落盘须串行）
Task: "T014 [P] [US1] 写测试：Annotated[list, operator.add] 的四项断言 in tests/runtime/test_schema_parse.py"
Task: "T015 [P] [US1] 写测试：归约器引用保持 + 调用次数 == 0 in tests/runtime/test_schema_parse.py"
Task: "T016 [P] [US1] 写测试：Required/NotRequired 包裹的归约器不漏 in tests/runtime/test_schema_parse.py"

# 实现（依赖上面的测试已写好且已失败）
Task: "T017 [US1] 实现 parse_state_schema 主流程 in src/freegraph/runtime/schema.py"
Task: "T018 [US1] 导出 parse_state_schema in src/freegraph/runtime/__init__.py"
Task: "T019 [US1] 接入投影中的归约器标识 in src/freegraph/runtime/schema.py"
```

---

## Implementation Strategy

### MVP First（User Story 1 Only）

1. 完成 Phase 1：Setup（骨架 + 子进程夹具 + 绿基线）
2. 完成 Phase 2：Foundational（**CRITICAL** —— 阻塞全部故事）
3. 完成 Phase 3：User Story 1（归约器识别 · **A1 验收判据**）
4. **STOP and VALIDATE**：跑 `pytest tests/runtime/ -ra` + quickstart §1 ⇒ 独立验收 US1
5. 提交（**不**合入 —— 尚有闸口 A3/A4/A5 未完成）

### Incremental Delivery

1. Setup + Foundational ⇒ 底座就位
2. US1 ⇒ 独立测试 ⇒ 提交（**MVP**：核心判定成立）
3. US2 ⇒ 独立测试 ⇒ 提交（覆盖语义 + 必填性事实）
4. US3 ⇒ 独立测试 ⇒ 提交（误判方向堵死）
5. US4 ⇒ 独立测试 ⇒ 提交（错误在解析期暴露）
6. Polish ⇒ 判定表比对 / 零副作用 / 纪律复核 / 人工记录 / 追认 ⇒ 合入

### Parallel Team Strategy

With multiple developers:

1. 团队共同完成 Setup + Foundational（底座是**共享前置** ⇒ MUST 先合）
2. 底座完成后：
   - 开发 A：US1（主流程 + 归约器分支）· **优先**（P1 是 MVP）
   - 开发 B：US2（覆盖语义 + 必填性）
   - 开发 C：US3 + US4（误判分支 + 错误契约）
   - ⚠️ 三人**同时**改 `src/freegraph/runtime/schema.py` ⇒ MUST 用「**按分支分函数 + 串行合并**」的策略
     （建议：各自把分支逻辑写进**独立函数**，合并时只调函数、不改他人代码）
3. Polish 由**一人**统一收口（判定表比对 + 人工记录 + 追认）

---

## 附录 · 任务 ↔ spec 追溯表

| 任务 | FR | SC | 落点 |
|---|---|---|---|
| T001 | FR-014 | SC-012 | `src/freegraph/runtime/` 包骨架（**L2** · 层注册表已登记）· ⚠️ **MUST NOT** 被 `src/freegraph/__init__.py` import（顶层包惰性 · G1 / L-1） |
| T002 | — | — | 测试包骨架（`tests/runtime/__init__.py` · 自带 `__init__.py` ⇒ 不触发 pytest `import file mismatch`） |
| T003 | FR-013 | SC-007 | 子进程夹具（`sys.modules` 增量 / 环境变量读取 / socket 连接）—— 同进程不可用 ⇒ **必须子进程** |
| T004 | FR-016 | SC-004 | 判定表夹具（解析 `contracts/binary-criterion.md` + **按名字求值** §4 夹具清单 —— §4 是 **全部 18 个输入名**的唯一命名空间）· research D-03 · **MUST NOT** 另抄一份表 |
| T005 | FR-018 | SC-013 | **创建人工验证记录骨架**（五段式 + 来源覆盖表空表 · 后续 5 条任务都往这里写 ⇒ 文件 MUST 最先存在）+ 实现前绿基线（**真实输出**贴进该文件第 3 节） |
| T006 | FR-007 ⑤⑥ | SC-017 | `InvalidSchemaError`（双重继承 + `key` / `reason` 结构化字段 + 英文摘要）· 裁定 2 / Q4 / Q7 |
| T007 | FR-004 | SC-001 / SC-004 | 二元性判定（位置专用 + 位置或关键字 == 2 · `*args` / `**kwargs` / keyword-only 不计 · 签名不可取 ⇒ False）· research D-01 |
| T008 | FR-003 | SC-001 / SC-003 | 归约器提取（**末位** · callable 判定 · 类与实例**不**例外）· 裁定 9 / Q6 |
| T009 | FR-002 / FR-010 / FR-020 | SC-005 / SC-008 | `ChannelSpec`（6 字段**逐字冻结** · frozen + slots + kw_only · **显式** `__hash__ = None`）· data-model §3 · Q8 |
| T010 | FR-010 / FR-020 | SC-005 / SC-008 | `SchemaSpec`（`channels` + `keys` · `MappingProxyType` ⇒ **结构性不可变**）· research D-02 · data-model §4 |
| T011 | FR-008 / FR-009 | SC-010 | 类型解析辅助（`include_extras=True` · `Required` / `NotRequired` **先剥离** · 逐 key 探针指名出错 key）· 裁定 4 / 5 · research D-04 |
| T012 | FR-011 | SC-005 | 投影方法（类型可读文本 D-05 · 归约器标识 4 级规则 D-06 · 抹除内存地址） |
| T013 | FR-015 | SC-015 | 导出 L2 内部 API（**不是**公开门面 · 门面仍 7 符号面）· research D-07 |
| T014 | FR-002 / FR-003 | SC-001 | US1 主断言（身份判定 + `has_reducer` + `reduce` + 基类型 `value_type is list`） |
| T015 | FR-012 / FR-013 | SC-009 | 引用保持 + 调用次数 == 0 + **同一 callable 两 key 共用**（持同一引用）+ **有状态归约器**（不重置状态） |
| T016 | FR-008 / FR-021 ③ | SC-010 / SC-016 | `Required` / `NotRequired` 包裹的归约器**不漏** + **未来注解**下仍能解析出归约器（落 `tests/runtime/test_future_annotations.py`）+ **未来注解 ⇒ 必选**（FR-021 ③） |
| T017 | FR-001 / FR-002 / FR-003 / FR-012 | SC-001 / SC-008 | 解析主流程 `parse_state_schema`（鸭子判定 + 剥离 + 末位 + 落位 + 保序组装） |
| T018 | FR-015 | SC-015 | 导出解析入口（**MUST NOT** 进门面） |
| T019 | FR-011 | SC-005 | 投影中的归约器**可读标识**（research D-06） |
| T020 | — | SC-001 / SC-009 / SC-010 | US1 用例跑绿 |
| T021 | FR-018 | SC-001 | quickstart §1 真实输出 |
| T022 | FR-006 | SC-002 | 无归约器 key ⇒ `overwrite`（C3 事实） |
| T023 | FR-002 / FR-009 | SC-008 | 条数 == key 数 · 保序 · `__slots__` 跳过 + **空 TypedDict ⇒ 零条规格**（合法） |
| T024 | FR-021 | SC-016 | 必填性标记（照抄 `__required_keys__` / `__optional_keys__`）+ **缺必填 key 仍解析成功**（证明**不执行**必填性校验 · FR-021 ②）· **未来注解 ⇒ 一律必选**的子用例归 **T016** 的隔离模块 |
| T025 | FR-006 | SC-002 | 「无归约器 ⇒ 覆盖语义」的落位（**只标记** · 执行属 B5F1） |
| T026 | FR-021 | SC-016 | 必填性标记实现（**只记录不执行** · 校验属 B7F3） |
| T027 | FR-002 / FR-009 | SC-008 | 保序（`get_type_hints` 插入序 · research D-10）+ `__slots__` 跳过（裁定 12） |
| T028 | — | SC-002 / SC-008 / SC-016 | US2 用例跑绿 |
| T029 | FR-018 | SC-002 / SC-016 | quickstart §2 / §7 真实输出 |
| T030 | FR-003 ① | SC-003 | 末位非 callable ⇒ 无归约器且**不报错** |
| T031 | FR-005 | SC-003 | 多条目元数据 ⇒ 只认末位 |
| T032 | FR-003 ③ | SC-003 / SC-004 | 类 / 可调用实例的**机械判定**（澄清 **Q6** · 裁定 9） |
| T033 | FR-003 ① | SC-003 | 「末位非 callable」分支（不报错）· 注释标明 Q6 |
| T034 | FR-005 | SC-003 | 多条目只认末位的分支 |
| T035 | — | SC-003 | US3 用例跑绿 |
| T036 | FR-018 | SC-003 | quickstart §3 真实输出 |
| T037 | FR-004 / FR-017 | SC-003 / SC-014 | **五类**非二元负向用例（3 参 / 1 参 / 类 / 内置类型 / `*args`）· FR-017 · 提示词 §10 |
| T038 | FR-001 / FR-007 ① | SC-006 / SC-017 | 非 `TypedDict` ⇒ `not_a_typed_dict` + `key is None`（「Pydantic 形态」用**零依赖替身** · MUST NOT 新增依赖声明） |
| T039 | FR-007 ③ | SC-006 / SC-017 | 注解不可解析 ⇒ `annotation_unresolvable` + 指名 key（**含继承链变体** · 父类上的坏注解同样可指名） |
| T040 | FR-007 ④⑤⑥ | SC-006 / SC-017 | 快速失败（只报第一个）· 结构化字段齐备 · 两种捕获路径 |
| T041 | FR-007 | SC-006 / SC-017 | 三处错误抛出点（**MUST NOT** 抛裸 `TypeError` / `NameError`） |
| T042 | FR-007 ④ | SC-006 | 快速失败实现（按 key 顺序 · 澄清 **Q3**） |
| T043 | FR-007 | SC-017 | 错误消息复核（**英文摘要** + 点名 key · 上层**无须**解析消息） |
| T044 | — | SC-006 / SC-014 / SC-017 | US4 用例跑绿 |
| T045 | FR-018 | SC-006 | quickstart §4 真实输出 |
| T046 | FR-016 ①-a·①-b | SC-004 | **判定表逐条比对**（16 + 2 行 · 缺失 == 0 · 无来源 == 0 · **行数 == 16 断言**）· research D-03 |
| T047 | FR-010 / FR-011 | SC-005 | 契约守卫（不可变 · 可比较（差异源取自**产物内容**）· 投影可序列化且无地址 · 显式不可哈希）· I-7…I-8·I-9 |
| T048 | FR-013 | SC-007 | 零副作用三断言（`sys.modules` 增量 / 环境变量 / 出站）· 子进程 + **import 期** `sys.modules` 无 `pydantic`/`typing_extensions`/`langchain*`（SC-011 字面口径 · **import 期断言 MUST 在子进程内执行**） |
| T049 | FR-013 / FR-015 / FR-019 | SC-004 / SC-011 / SC-015 | 依赖三处零新增（含 **MUST NOT** 写 `langchain*`）+ **`ci.yml` 全文 `langgraph` 出现次数 == 0**（第 4 处声明位 · 可机读断言）· 公开面 18 / 7 未变 |
| T050 | FR-014 | SC-012 | 层纪律（层注册表零改动 · 无 L2 → L3/L4/L5 边 · G25 / G30 绿 · 门禁总数仍 30）· research D-09 |
| T051 | FR-019 | SC-012 | 署名头与 docstring 复核（既有 G30 覆盖） |
| T052 | FR-018 | SC-013 | **回填**人工验证记录（骨架由 T005 建）· 五段式 + 来源覆盖表 + A1–A3 逐条结论 |
| T053 | FR-018 | SC-013 | **发起者追认**（plan 登记项 R-1 · **阻断合入** · MUST NOT 代签） |
| T054 | FR-018 | SC-013 | quickstart 全文（§0 – §10）真实输出 |
| T055 | FR-015 / FR-018 | SC-015 | 兼容矩阵**零新增行** + 人工记录显式记「无新增」 |
| T056 | FR-019 | SC-011 | `THIRD_PARTY_NOTICES` 无需新增登记（零新增依赖 · 原则 X） |
| T057 | FR-001 | SC-018 | **`typing_extensions.TypedDict` 正面路径**守卫（验收基准同构形态 · 裁定 3）· 被测 schema 由测试代码构造 ⇒ 内核仍 MUST NOT import 它 · 落 `tests/runtime/test_typed_dict_variants.py`（**独立文件**）· **环境依赖型** ⇒ skip ≠ pass |

> **覆盖核对**：**FR 21/21**（FR-001…FR-021 全部命中）· **SC 18/18**（SC-001…SC-018 全部命中）·
> **任务 57 条**（Setup 5 + Foundational 8 + US1 8 + US2 8 + US3 7 + US4 9 + Polish 12）。

---

> ⚠️ **2026-11-12 · 上游对齐 P3 回溯修订注记**（**只加注记 · 不改历史记录**）：
> 本 feature 的 T006 / T038 / T041 等条目记录的「原因码 `not_a_typed_dict`」与
> 「只接受 `TypedDict` / 拒绝 Pydantic 模型」两条口径，已在
> **2026-11-12 · 上游对齐 P3**（见 `specs/b12f1-concurrency-errors/` 与
> `harness/proposals/上游对齐审计.md`）**改为上游同款**：
> ① 原因码**改名** `not_a_state_schema`（判定口径已从「是不是 `TypedDict`」放宽）；
> ② **Pydantic 模型 / dataclass / 普通类**（是类 + 有 `__annotations__`）**一律接受**
> （上游 `langgraph/graph/state.py:1818`）；
> ③ `value_type` **保留 `Annotated` 原样**（上游 `:1862-1872`）；
> ④ **空 schema** 仍合法（零条通道）。
> ⇒ 上面的**执行记录**保持原样（历史事实），**判据面**见 `spec.md` / `contracts/` / `data-model.md`。
