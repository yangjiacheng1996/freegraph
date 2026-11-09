---

description: "B5F1 · Channel 抽象 + LastValue + BinaryOperatorAggregate + EphemeralValue —— 任务清单"
---

# Tasks: B5F1 · Channel 抽象 + `LastValue` + `BinaryOperatorAggregate` + `EphemeralValue`

**Input**: Design documents from `/specs/b5f1-channels/`

**Prerequisites**:
- `plan.md`（必读 · 含 **Constitution Check** 与 **登记项 R-1**（宪法门禁 3/4/5 的偏离登记）·
  **Structure Decision**（`channel.py` / `mapping.py` / `errors.py` 的切分理由）· **设计后复核**）
- `spec.md`（必读 · 含 **17 条裁定** + **15 条澄清问答 Q1–Q15** · FR-001 ~ FR-027 · SC-001 ~ SC-028）
- `research.md`（必读 · **17 条决策 D-01…D-17** · 全部附**实测证据** · 6 条遗留登记 DR-1…DR-6）
- `data-model.md`（必读 · 5 类实体 · **字段名逐字冻结** · 三张状态机 · 不变量 I-1…I-23 —— ⚠️ 契约 §6 的**全部 23 条**（含 **I-4** `is_available()` 恒不抛错 / **I-5** `value` 与 `get()` 同义）MUST 逐条被解析并断言）
- `contracts/channel-contract.md`（**通道契约的唯一权威** · `<!-- authority: yes -->` · 操作面 / 三类语义 / 映射 / 错误 / 不变量）
- `contracts/upstream-parity.md`（与上游 LangGraph 的**逐条对照** · 每条带 `路径:行号` + 核实版本 `langgraph 1.2.11`）
- `quickstart.md`（**可照抄**的验证手册 · 11 节 · 验收闸口 **V1–V9**）

**Tests**: **含**测试任务 —— 本 feature 的成功标准**全部**以断言形式给出（SC-001…SC-028），
且 spec **强制**要求：① 负向用例四类（FR-019 ① · SC-016）；
② 行 / 分支覆盖 **100%**（FR-019 ② · SC-015）；
③ 「只依赖通道抽象」的自定义通道实现用例（FR-019 ③ · SC-017）；
④ **独立验收脚本**（FR-026 · SC-027）
⇒ 测试是**交付面的一部分**，不是可选项。

**Organization**: 任务按用户故事分组，每个故事可**独立实现、独立测试、独立交付**。

**本 feature 的可测判据总表**（**27 FR + 28 SC ↔ 46 条任务**）：
追溯见文末「**附录 · 任务 ↔ spec 追溯表**」——
**每个 FR 与每个 SC 均至少被一条任务映射**（**FR 27/27 · SC 28/28**）。
其中 **SC-002 / SC-021**（归约语义 + 折叠基准）由 **T014 / T015** 承载，
**SC-003**（路由清空）由 **T021** 承载，**SC-015**（覆盖率 100%）由 **T036** 承载，
**SC-022**（规模口径）由 **T029** 承载，**SC-027**（独立验收脚本）由 **T037–T040** 承载，
**T042**（**发起者追认** · plan 登记项 R-1）是**阻断合入**的任务。

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可并行（**不同文件**且无未完成依赖）——同一文件内的后续任务**不标** `[P]`
- **[Story]**：所属用户故事（US1…US4）；Setup / Foundational / Polish 阶段**不标**
- 每条任务都带**确切文件路径**；冻结面的**逐字内容**在 `contracts/` 与 `data-model.md` 中，
  本文件**只引用不复制**
- **逐条追溯**：每条任务对应的 **FR / SC** 见文末「**附录 · 任务 ↔ spec 追溯表**」
  （宪法原则 VI：「tasks MUST 逐条勾选、**可追溯到 spec 条目**」）

## Path Conventions

- 内核实现：`src/freegraph/runtime/`（**L2 执行内核层** · 层注册表**已登记**）
  - `channel.py`（★ 新建 · `Channel` 抽象 + 三类实现 + 空值推导 + `_MISSING` 哨兵）
  - `mapping.py`（★ 新建 · `build_channel` / `build_channels` —— **唯一** import B4F1 `ChannelSpec` / `SchemaSpec` 的地方）
  - `errors.py`（★ 追加 `EmptyChannelError` / `InvalidChannelUpdateError` · **既有 `InvalidSchemaError` 一字不动**）
  - `__init__.py`（★ 追加导出 · L2 内部 API **4 → 12** 个符号 · **不是**公开门面）
  - `schema.py` / `reducer.py`（既有（B4F1）· **零改动**）
- 测试：`tests/runtime/`（与既有 `tests/contracts/` · `tests/facade/` · `tests/gates/` **平级** ·
  **自带** `__init__.py` ⇒ 模块名带包前缀 ⇒ 不会触发 pytest 的 `import file mismatch`）——
  **五个新测试模块**：`test_channel_semantics.py`（三类语义 · 初始状态 · 返回值口径 · 名字面）·
  `test_channel_errors.py`（错误契约 · 构造期校验）·
  `test_channel_mapping.py`（映射入口）·
  `test_channel_purity.py`（纯净性 · 规模口径 · import 副作用）·
  `test_channel_contract.py`（**契约守卫** · 解析 `contracts/channel-contract.md` 逐条比对 · T035）
  —— ⚠️ **既有 6 个测试模块与 `conftest.py` 零改动**（复用 `run_in_subprocess` 夹具）
- 契约权威：`specs/b5f1-channels/contracts/channel-contract.md`（**只读**）
- 上游对照表：`specs/b5f1-channels/contracts/upstream-parity.md`（**只读** · 证据表 · **MUST NOT** 被测试解析）
- 人工验证记录：`harness/verification/B5F1/manual-verification.md`（★ 新建）
- 独立验收脚本：`harness/verification/B5F1/acceptance.py`（★ 新建 · 零第三方依赖）
- **零改动清单**（本 feature **MUST NOT** 触碰）：`src/freegraph/__init__.py` ·
  `src/freegraph/graph.py` · `src/freegraph/contracts/**`（含 `errors.py` 的「唯一定义处」措辞）·
  `src/freegraph/runtime/schema.py` · `src/freegraph/runtime/reducer.py` ·
  `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`（⚠️ 其 `:98` 的「尚未存在」措辞已过时 ⇒ **只登记不修改** · research DR-5）·
  `tests/contracts/test_contract_regressions.py`（⚠️ **C4 / C8 的 `GATE-MOUNT:` 标记 MUST NOT 改成
  `landed`** —— C4 / C8 **未**由本 feature 落地 · 归属 B5F2 / B8F1）·
  `tests/runtime/conftest.py` · `tests/runtime/test_schema_parse.py` ·
  `tests/runtime/test_future_annotations.py` · `tests/runtime/test_binary_criterion.py` ·
  `tests/runtime/test_parse_contract.py` · `tests/runtime/test_typed_dict_variants.py` ·
  `pyproject.toml`（三处依赖声明零新增 · 覆盖率工具**不进**依赖 · research D-13）·
  `.github/workflows/ci.yml`（`testpaths = ["tests"]` ⇒ **零改动**即被收集）· `README.md`（兼容矩阵零新增行）

> **⚠️ 落地顺序提示**：本 feature 的**红线**是「**覆盖 vs 归约只有一处实现点**」——
> 归约型通道的「首次写入 `current` 取什么」选错，会让 `operator.add` 的结果与上游**差一个前缀元素**
> （提示词 §10）⇒ **空值推导（T018）与首次写入的两分支（T019）MUST 与
> `contracts/upstream-parity.md` 的 P-05 / P-07 逐条一致**（T015 逐条比对）。

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 建立新文件骨架（通道核心 / 映射 / **五个测试模块** / 验收脚本）与**人工验证记录骨架**，并取「实现前」的绿基线

- [X] T001 [P] 建 `src/freegraph/runtime/channel.py` 骨架：文件头 `# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph` + **模块 docstring 为首个语句**（写明「L2 执行内核层 · 通道实现 · 属 B5F1」）+ `__all__` 占位（`Channel` / `LastValue` / `BinaryOperatorAggregate` / `EphemeralValue`）—— ⚠️ **MUST NOT** 在 `src/freegraph/__init__.py` 里 import 它（顶层包惰性 · 门禁 G1 / L-1）
- [X] T002 [P] 建 `src/freegraph/runtime/mapping.py` 骨架：署名头 + 模块 docstring 为首个语句（写明「schema → 通道的映射入口 · 属 B5F1」）+ `__all__` 占位（`build_channel` / `build_channels`）
- [X] T003 [P] 建**五个**测试模块骨架：`tests/runtime/test_channel_semantics.py` · `tests/runtime/test_channel_errors.py` · `tests/runtime/test_channel_mapping.py` · `tests/runtime/test_channel_purity.py` · `tests/runtime/test_channel_contract.py`（⚠️ **五个** —— 第五个是 T035 的**契约守卫**模块 · 与 plan 结构段一致）（每个：署名头 + 模块 docstring 为首个语句 + 文档字符串写明其承载的 SC 范围）—— ⚠️ **MUST NOT** 修改既有的 `tests/runtime/conftest.py` 与 6 个既有测试模块（复用 `run_in_subprocess` 夹具）
- [X] T004 [P] 建 `harness/verification/B5F1/acceptance.py` 骨架：署名头 + docstring（定位 / 覆盖分组 / 两态运行 / 用法 / 退出码）+ 辅助函数 `section(title)` / `check(cond, label, detail="")` / `soft(cond, label, note="")` / `eq(actual, expected, label)` / `_load_runtime()`（返回 `freegraph.runtime` 模块与来源说明）/ `_installed()`（探测发行包是否已安装）+ `argparse`（`--record <file>` / `--require-installed`）+ **退出码 `0` = PASS · `1` = FAIL · `2` = 环境未就绪**（research D-11 · spec FR-026 ③）—— ⚠️ 只 import **标准库** + 被验收的 `freegraph` 本身
- [X] T005 创建人工验证记录骨架并取**实现前**绿基线：新建 `harness/verification/B5F1/manual-verification.md`（**五段式**小节标题：环境 / 步骤 / 实际输出 / 结论 / 遗留问题 + **来源覆盖表**空表 —— ⚠️ T041 / T044 都要往该文件写 ⇒ 文件 MUST **最先**存在）⇒ 再跑 `python -m pytest tests/ -ra` 取**实现前**的绿基线 ⇒ 把**真实输出**记入该文件第 3 节（**MUST NOT** 伪造）

---

## Phase 2: Foundational（阻塞性前置）

**Purpose**: 全部用户故事共用的**底座**（**通道抽象** + **错误契约**）—— **不含**三类通道的具体语义（属 US1–US3）

**⚠️ CRITICAL**: 本 Phase 未完成前，**任何用户故事**都不得开工

- [X] T006 [P] 追加两个错误类型到 `src/freegraph/runtime/errors.py`：`EmptyChannelError(FreegraphError)`（**仅**继承 `FreegraphError` · **MUST NOT** 继承 `ValueError` · FR-017 ⑦）+ `InvalidChannelUpdateError(FreegraphError, ValueError)`（**双重继承** · 与 B4F1 的 `InvalidSchemaError` 同款）；结构化字段**逐字冻结**：`EmptyChannelError.key` · `InvalidChannelUpdateError.key` / `.received_count` / `.expected_count`（**恒为 1**）；消息为**英文摘要** + 点名 key；⚠️ **MUST NOT** 携带用户写入的**值本身**（FR-017 ⑥）—— ⚠️ **既有 `InvalidSchemaError` 一字不动**；⚠️ **MUST NOT** 把这两个类型加进 `src/freegraph/contracts/__init__.py` 的 `__all__`（18 符号面是冻结面 · 门禁 G7）
- [X] T007 实现 `src/freegraph/runtime/channel.py` 的 `Channel` 抽象基类：`abc.ABC` + `@abstractmethod` 的 `update(values)` / `get()` / `is_available()` + **默认实现** `clear()`（**无操作** · 返回假 —— ⚠️ 本 feature 的**三类通道全部覆写**它 · 裁定 17 ①）；`__slots__` = `("_key", "_value_type", "_value", "_reducer")`；**4 个只读 property** `key` / `value_type` / `value` / `reducer`（`value` **无 setter**；无值时**抛 `EmptyChannelError`** · 与 `get()` 同义 · research D-04）；模块级哨兵 `_MISSING = object()`（**MUST NOT** 用 `None` · research D-03）—— 构造签名 `Channel(key: str, value_type: Any)`；构造 MUST **无副作用**（FR-002 ①）
  > **📌 属性定义的落点**：4 个 `property` MUST 定义在**本基类**上（子类**继承**）⇒
  > 测试断言 MUST 沿 **MRO** 收集（`type(ch).__dict__` **只**含该类自身定义的属性 ⇒ 取基类属性时会得到
  > **空集** · 裁定 17 ① · research D-17 实测）
- [X] T008 导出 L2 内部 API 的**底座部分**：`src/freegraph/runtime/__init__.py` 追加 `Channel` / `EmptyChannelError` / `InvalidChannelUpdateError`（**4 → 7** 个符号；⚠️ 此时**不含**三类通道与映射入口 —— 随各故事追加）· docstring MUST 写明「**L2 内部 API · 不是公开门面**」，且其**交付物清单** MUST 随本 feature **同步更新**（列出 `Channel` / `LastValue` / `BinaryOperatorAggregate` / `EphemeralValue` / `build_channel` / `build_channels` —— ⚠️ 否则门面描述会停留在 B4F1 的四项）（公开门面仍是 7 个符号 · 门禁 G15 / G19）

**Checkpoint**: 底座就位（抽象 + 错误契约）—— 用户故事可开工

---

## Phase 3: User Story 1 - 计数型 key 每次被覆盖（Priority: P1）🎯 MVP

**Goal**: `LastValue` 通道 —— **无归约器 ⇒ 覆盖**（C3）；一步内多值 ⇒ **显式失败**

**Independent Test**: 拿一个「无归约器」通道连续写入两个不同值（**两次独立的写入调用**），断言读取结果是**后者**；再断言该通道**从未调用过任何归约器**（`reducer is None`）

### Tests for User Story 1（MUST 先写 · MUST 先失败）

- [X] T009 [P] [US1] 在 `tests/runtime/test_channel_semantics.py` 写**覆盖语义**用例：`LastValue("llm_calls", int)` 连续两次 `update([1])` / `update([2])` ⇒ `get() == 2`（**不是** 3 / 不是 1）· `reducer is None` · 归约器调用次数 == 0（**验收判据 A2** · SC-001）
- [X] T010 [US1] 在 `tests/runtime/test_channel_semantics.py` 写**初始状态与只读性**用例：构造后 `is_available() is False`（覆盖型初始「无值」）· `get()` 抛 `EmptyChannelError` · `update([])` **无操作**且返回值假、值不变 · 写 `None` 后 `is_available() is True`（「值为 `None`」≠「无值」）· `ch.value = x` 抛 `AttributeError`（只读）· **清空语义**：写入后 `clear()` ⇒ `is_available() is False` 且 `get()` 抛 `EmptyChannelError`（**三类一律 ⇒ 无值** · FR-009 / SC-023 ④）· 连续 `clear()` 两次 ⇒ 第二次返回**假**（幂等）· 公开属性集合 **⊆** {`key`,`value_type`,`value`,`reducer`}（SC-004 · SC-009 · SC-020 · SC-023）
- [X] T011 [US1] 在 `tests/runtime/test_channel_errors.py` 写**空通道读取的错误契约**用例：读「无值」通道 ⇒ 抛 `EmptyChannelError` 且 `.key` == 通道 key · `except FreegraphError` **能**捕获 · **不是** `ValueError` 的子类 · 错误对象**不携带**用户写入的值（SC-018）

### Implementation for User Story 1

- [X] T012 [US1] 实现 `src/freegraph/runtime/channel.py` 的 `LastValue(key, value_type)`：继承 `Channel`；**MUST 声明 `__slots__ = ()`**（不引入新槽 ⇒ 实例**无 `__dict__`** · 裁定 17 ① —— 否则可写入 4 项之外的数据，FR-013 / SC-009② 失守）；`reducer` 恒为**空**；`update(values)`：空序列 ⇒ **无操作**返回假；**多于一个值 ⇒ 抛 `InvalidChannelUpdateError`（先检测后写入 ⇒ 值不变）**；恰好一个 ⇒ **覆盖**（丢弃旧值）· 返回**真**（本次写了值 · SC-020）；**覆写 `clear()`** ⇒ 清空后为「**无值**」（从「有值」清成「无值」⇒ 返回**真**；已是「无值」⇒ 无操作、返回**假** · FR-009 / 裁定 17 ① —— ⚠️ **不是**「撤销最后一次写入」）
  > **📌 步末调用范围**：覆盖型在步末**保留**其值（与上游 `update([])` 的 no-op 同构）⇒
  > 调度层**不**对覆盖型调 `clear()`（**B7F1** · contract §7 `B-2` · upstream-parity P-12 / S-05）
- [X] T013 [US1] 导出 `LastValue`：`src/freegraph/runtime/__init__.py` 追加 `LastValue`（**7 → 8** 个符号）

**Checkpoint**: US1 独立可测（覆盖语义 + 冲突显式失败 + 初始状态）—— **MVP 到此成立**

---

## Phase 4: User Story 2 - 消息型 key 累积追加（Priority: P2）

**Goal**: `BinaryOperatorAggregate` 通道 —— **有归约器 ⇒ `reducer(current, new)`**（C2）；空值按**类型**推导；首次写入分「有值 / 无值」两分支

**Independent Test**: 拿一个带 `operator.add` 归约器的通道写入两次，断言读取结果**逐元素等于**「**从通道初始值（空值）起**」的逐次归约结果（**验收判据 A1**）

### Tests for User Story 2（MUST 先写 · MUST 先失败）

- [X] T014 [P] [US2] 在 `tests/runtime/test_channel_semantics.py` 写**归约语义**用例：`BinaryOperatorAggregate("messages", list, operator.add)` 写入 `[["m1"]]` 再写入 `[["m2"]]` ⇒ `get() == ["m1","m2"]`（**逐元素相等**）· 基准 = **从初始空值起折叠** `reducer(reducer([], ["m1"]), ["m2"])`（**不是**从首值起折 · SC-021）· `ch.reducer is operator.add`（**身份**判定 · SC-010）· 初始 `is_available() is True` 且值为 `[]`（**验收判据 A1** · SC-002）
- [X] T015 [US2] 在 `tests/runtime/test_channel_semantics.py` 写**空值推导与首次写入**用例：空值推导覆盖 **6 类** —— `list→[]` · `int→0` · `str→""` · `dict→{}` · `collections.abc.Sequence→[]`（**抽象容器映射**）· **不可实例化类型**（如 `typing.Any`）⇒ **初始「无值」**；不可实例化类型的**首次写入直存新值**且**单值**写入时**归约器调用次数 == 0**（FR-007 ②）· **多值**首写 ⇒ 首个直存、其余按序归约（调用次数 == **值数 − 1** · 裁定 17 ④）· 两个同类型通道的**空值不是同一对象**（共享次数 == 0 · FR-006 ④）（SC-007 · SC-021）
- [X] T016 [US2] 在 `tests/runtime/test_channel_errors.py` 写**归约失败与构造期校验**用例：归约器抛错 ⇒ 异常**向上传播**且通道**值不变**（FR-008）· 构造期传入**不可调用**的归约器 ⇒ 抛**内置 `TypeError`**（MUST NOT 拖到写入时）· 「标注有归约器但归约器为空」⇒ 抛**内置 `ValueError`** · 通道层**不重做**二元性校验（传非二元归约器**不**在构造期报错）（SC-006 · SC-016 · SC-026）
- [X] T017 [US2] 在 `tests/runtime/test_channel_semantics.py` 写**归约型初始状态**用例：可实例化类型 ⇒ 初始「有值」且值 == 空值；不可实例化类型 ⇒ 初始「无值」；`clear()` 后 ⇒ **一律**「无值」且**不回到**初始空值（**从「有值」清成「无值」⇒ `clear()` 返回真**；已是「无值」⇒ 返回**假** · FR-022 ③ · SC-023 ④ · 裁定 17 ①）

### Implementation for User Story 2

- [X] T018 [US2] 实现 `src/freegraph/runtime/channel.py` 的空值推导 `_derive_empty_value(value_type)`：① **逐层剥离** `Annotated` / `Required` / `NotRequired`（**窄口径** · 保留泛型别名 · research D-05）→ ② 抽象容器映射（`Sequence`/`MutableSequence`→`list`；`Set`/`MutableSet`→`set`；`Mapping`/`MutableMapping`→`dict`）→ ③ `try: value_type()`（成功 ⇒ 该**新实例**；**失败（`except Exception`）⇒ `_MISSING`**）；⚠️ 每次调用 MUST **新建**实例（MUST NOT 跨通道共享可变对象 · FR-006 ④）
- [X] T019 [US2] 实现 `src/freegraph/runtime/channel.py` 的 `BinaryOperatorAggregate(key, value_type, reducer)`：**MUST 声明 `__slots__ = ()`**（不引入新槽 ⇒ 实例**无 `__dict__`** · 裁定 17 ①）；构造期校验（归约器**不可调用** ⇒ 内置 `TypeError` · FR-025 ①）· 初始值 = `_derive_empty_value(value_type)`；`update(values)`：空序列 ⇒ 无操作返回假 · 通道**无值** ⇒ **直存首个值** `values[0]`（**单值**写入时**不调**归约器 · 归约器调用次数 == **0**；**多值**写入 ⇒ 首个直存、**其余按序** `值 = reducer(写入前的值, 新值)`，调用次数 == **值数 − 1** · 裁定 17 ④ —— 与上游 `binop.py:126-128` + `:143` 逐字同构）· 多值**按序**逐个归约 · 赋值只在 reducer 返回后发生（⇒ 归约失败**不污染**状态 · FR-008）；**覆写 `clear()`** ⇒ 清空后为「**无值**」且**不回到**初始空值（从「有值」清成「无值」⇒ 返回**真**；已是「无值」⇒ 返回**假** · FR-009 / FR-022 ③ / 裁定 17 ①）
  > **📌 步末调用范围**：归约型在步末**保留**其值（上游 `update([])` 对 BinOp 是 no-op）⇒
  > 调度层**不**对归约型调 `clear()`（**B7F1** · contract §7 `B-2` · upstream-parity P-12 / S-05）
- [X] T020 [US2] 导出 `BinaryOperatorAggregate`：`src/freegraph/runtime/__init__.py` 追加（**8 → 9** 个符号）

**Checkpoint**: US1 + US2 独立可测（覆盖 + 归约）—— A1 / A2 两条验收判据成立

---

## Phase 5: User Story 3 - 路由结果不跨轮残留（Priority: P3）

**Goal**: `EphemeralValue` 通道 —— **路由通道**；`clear()` ⇒ 回到「无值」；一步内多值 ⇒ **显式失败**

**Independent Test**: 往路由通道写一个值 ⇒ 触发 `clear()` ⇒ 断言通道回到「无值」（判定为假 + 读取抛错），且**不是**上一次的值、也**不是** `None` 冒充有值

### Tests for User Story 3（MUST 先写 · MUST 先失败）

- [X] T021 [P] [US3] 在 `tests/runtime/test_channel_semantics.py` 写**清空语义**用例：`EphemeralValue("route", str)` 写入 ⇒ `get()` 读得到 · `clear()` ⇒ `is_available() is False` · `get()` **抛** `EmptyChannelError`（MUST NOT 返回上一次的值 / MUST NOT 返回 `None`）· 清空后再写入 ⇒ 恢复「有值」且新值 == 刚写入的值（**无残余状态**）· 连续 `clear()` 两次 ⇒ 第二次返回**假**（幂等）（**验收判据 A3** · SC-003）
- [X] T022 [US3] 在 `tests/runtime/test_channel_errors.py` 写**路由通道冲突**用例：一次 `update(["a","b"])` ⇒ 抛 `InvalidChannelUpdateError` 且 `.received_count == 2` · `.expected_count == 1` · `.key == "route"` · 通道**值不变**（SC-006 · SC-016 · SC-018）
- [X] T023 [US3] 在 `tests/runtime/test_channel_semantics.py` 写**清空 ≠ 回到初始状态**用例：归约型通道 `clear()` 后 ⇒ 「无值」且其值 **NOT** 等于初始空值；此后写入 ⇒ 按 FR-007 情形 ① 处理（**此时通道无值 ⇒ 首次写入直存、归约器调用次数 == 0**）（FR-022 ③ · SC-023 ④ · 裁定 17 ①）
  > **📌 与上游的等价性**：归约型在**步末**保留其值（上游 `update([])` 是 no-op）⇒ 调度层**不**对其调
  > `clear()`（**B7F1** · contract §7 `B-2`）—— 本用例只断言 `clear()` **被显式调用时**的语义

### Implementation for User Story 3

- [X] T024 [US3] 实现 `src/freegraph/runtime/channel.py` 的 `EphemeralValue(key, value_type)`：继承 `Channel`；**MUST 声明 `__slots__ = ()`**（不引入新槽 ⇒ 实例**无 `__dict__`** · 裁定 17 ①）；`reducer` 恒为**空**；初始「无值」（**不推导**空值）；`update(values)`：空序列 ⇒ **无操作**返回假（⚠️ **清空走 `clear()`**，不靠空序列）· **多于一个值 ⇒ 抛 `InvalidChannelUpdateError`（值不变）** · 恰好一个 ⇒ 覆盖为最新值 · 返回**真**；**覆写** `clear()` ⇒ 清到「**无值**」并返回「状态是否真的变化」（从「有值」清成「无值」⇒ **真**；已是「无值」⇒ **假** · 幂等 · FR-009 / 裁定 17 ①）
- [X] T025 [US3] 导出 `EphemeralValue`：`src/freegraph/runtime/__init__.py` 追加（**9 → 10** 个符号）

**Checkpoint**: US1–US3 独立可测（覆盖 + 归约 + 路由清空）—— A1 / A2 / A3 三条验收判据成立

---

## Phase 6: User Story 4 - 状态语义只有一处实现点（Priority: P4）

**Goal**: **schema → 通道的映射入口**（`build_channel` / `build_channels`）+ 抽象**真的**可替换 + 通道**纯净**（不随 key 数增长 / 无副作用 / 浅引用）

**Independent Test**: 写一个**只依赖通道抽象**的第三方通道实现（测试内自定义），断言它能被同一个映射入口创建、被同一套读取 / 清空流程使用 —— 证明抽象**真的**是可替换的实现单元

### Tests for User Story 4（MUST 先写 · MUST 先失败）

- [X] T026 [P] [US4] 在 `tests/runtime/test_channel_mapping.py` 写**映射规则**用例：解析一份含 `messages: Annotated[list, operator.add]` 与 `llm_calls: int` 的 schema ⇒ `build_channels` 产出「`messages` ⇒ `BinaryOperatorAggregate`」+「`llm_calls` ⇒ `LastValue`」· 通道数 == key 数 · **保序**（键序 == `SchemaSpec.keys` 序）· 归约型通道的 `reducer` **就是**规格里的**同一引用**（身份判定）· `build_channel(spec.channels["llm_calls"])` ⇒ `LastValue`（SC-008 · SC-019）
- [X] T027 [US4] 在 `tests/runtime/test_channel_mapping.py` 写**路由通道与映射自洽**用例：`EphemeralValue` **不由** schema 派生（MUST 支持**直接实例化**）· 规格标注「有归约器」但归约器为**空** ⇒ `build_channel` 抛**内置 `ValueError`**（MUST NOT 新增错误类型）（SC-008 · SC-026）
- [X] T028 [P] [US4] 在 `tests/runtime/test_channel_semantics.py` 写**可替换性 + 名字面**用例：一个**只依赖抽象**的自定义子类能被创建 / 写入 / 读取 / 清空（**不改动**抽象与既有三类通道）· 名字面逐字一致（4 操作 `update`/`get`/`is_available`/`clear` · 4 属性 `key`/`value_type`/`value`/`reducer` · 4 类名 · 2 映射入口名 · 2 错误名）（SC-017 · SC-019）
- [X] T029 [P] [US4] 在 `tests/runtime/test_channel_purity.py` 写**纯净性与规模**用例：**公开**属性集合（4 个 `property`）**恰为** {`key`, `value_type`, `value`, `reducer`}（**不是** `dir()` 全集 —— ⚠️ 实现用 `__slots__` 私有槽 ⇒ 断言 MUST 取**公开属性名** · ⚠️ **必须沿 MRO 收集**：`{n for c in type(ch).__mro__ for n, v in c.__dict__.items() if isinstance(v, property)}` —— `type(ch).__dict__` **只**含该类自身定义的属性（属性在基类上时取到**空集**）· 裁定 17 ①）**且** 断言**实例槽位**集合 ⊆ {`_key`, `_value_type`, `_value`, `_reducer`}（沿 MRO 收集各类的 `__slots__`）· **实例 MUST 无 `__dict__`**（`not hasattr(ch, '__dict__')` ⇒ 子类**未**声明 `__slots__ = ()` 时**必失败** · 裁定 17 ①）· 通道**不持有**其它通道 / 状态表的引用 ⇒ **① 主判据 = 引用类型白名单**（`gc.get_referents(ch)` 中 MUST NOT 出现 `dict` / `SchemaSpec` / 其它 `Channel` 实例 · 裁定 17 ③）+ **② 辅助判据 = 计数探针**：`len(gc.get_referents(ch))` 在 schema 有 **1** 个 key 与有 **1000** 个 key 时**相等**（**MUST NOT** 用墙钟耗时 · research D-12 · ⚠️ 计数相等**不能**替代白名单 —— 实测持有整张状态表时计数仍相等）· 通道**浅引用**用户对象（`ch.value is 传入对象`）· **不校验**写入值类型 · **无同步原语**（无锁 / 无原子性保证）· 写入入口**只有** `update()`（SC-009 · SC-022 · SC-024 · SC-025）
- [X] T030 [US4] 在 `tests/runtime/test_channel_purity.py` 写**导入副作用**用例：**在子进程**里导入 `freegraph.runtime` ⇒ `sys.modules` 增量中**非标准库**条目数 == **0** · **环境变量读取次数 == 0** · **出站连接次数 == 0**（复用既有 `run_in_subprocess` 夹具 · ⚠️ **MUST 在子进程**执行 —— 同进程已被 pytest 污染）（SC-005）

- [X] T031 [P] [US4] 在 `tests/runtime/test_channel_semantics.py` 写**参数化组合**用例（立项书 **S5 ③**「属性 / 参数化测试：枚举 reducer 类型 × 通道组合」——本 feature 是「通道 × 归约器」的**唯一落点** ⇒ 该层等价证据 MUST 落在本 feature）：用 `pytest.mark.parametrize` 枚举「**归约器类型** × **通道类型**」的组合（归约器：`operator.add` / `max` / 一个自定义二元函数；通道：`LastValue` / `BinaryOperatorAggregate` / `EphemeralValue`）⇒ 组合数 **≥ 12**；每组自带**相容的值类型**（`operator.add`+`list` · `max`+`int` · 自定义+`tuple` —— ⚠️ 归约器与值类型**不得**配成不兼容组合，否则断言的是「归约器报错」而非「语义恒成立」）；断言四条语义在**所有组合**下成立 —— ① 覆盖型写入 ⇒ 读到**末值**；② 归约型写入序列 == **从初始值起**的逐次归约（基准按该组的 `value_type` 推导）；③ 路由型清空后 ⇒ **无值**；④ 一步内多值 ⇒ **显式失败**且值不变；⚠️ **MUST NOT** 用 `skip` / `xfail` 掩盖组合（被跳过的组合数 == 0）

### Implementation for User Story 4

- [X] T032 [US4] 实现 `src/freegraph/runtime/mapping.py` 的 `build_channel(spec: ChannelSpec) -> Channel`：规格 `has_reducer` 为真 ⇒ `BinaryOperatorAggregate(key=spec.key, value_type=spec.value_type, reducer=spec.reducer)`（**同一引用**）· 否则 ⇒ `LastValue(key=spec.key, value_type=spec.value_type)`；规格标注「有归约器」但归约器为**空** ⇒ 抛**内置 `ValueError`**（FR-012 ①③ · FR-025 ②）
- [X] T033 [US4] 实现 `src/freegraph/runtime/mapping.py` 的 `build_channels(schema_spec: SchemaSpec) -> dict[str, Channel]`：按 `schema_spec.keys` **保序**遍历 ⇒ 每个 key **恰一个**通道（FR-012 ④）—— ⚠️ 返回**可变** `dict`（research D-14：下游 B5F2 / B7F1 要在其上增补内部通道）
- [X] T034 [US4] 导出映射入口：`src/freegraph/runtime/__init__.py` 追加 `build_channel` / `build_channels`（**10 → 12** 个符号 ⇒ L2 内部 API 最终 **12** 个）
- [X] T035 [US4] 契约守卫：在 `tests/runtime/test_channel_contract.py`（★ 新建 · 同目录）逐条比对 **spec FR-001…FR-027**（含 **FR-027** 参数化组合测试 · 澄清轮 Q15）与 **`contracts/channel-contract.md`** 的**冻结内容**（4 操作 / 4 属性 / 4 构造签名 / 三类语义 / 映射 M-1…M-4 / 错误 E-1…E-5 / 不变量 I-1…I-23 —— ⚠️ 契约 §6 的**全部 23 条**（含 **I-4** `is_available()` 恒不抛错 / **I-5** `value` 与 `get()` 同义）MUST 逐条被解析并断言）⇒ **MUST NOT** 在测试里另抄一份契约（**解析**该 Markdown 文件取样 —— 沿用既有门禁 **G25** 解析 `layer-registry.md` 的手法）· 同时逐条核对 `contracts/upstream-parity.md` 的 P-01…P-12（**共 12 条** · 含 **P-12** 清空语义三类统一）都有对应的实现与断言 —— 其中 spec FR-021 点名的**六类**语义（覆盖语义 / 一步内多值冲突 / 空值推导 / 首次写入的 `current` / 清空语义 / 有值无值判定）MUST **逐条**有实现与断言（FR-021 · SC-014）

**Checkpoint**: 四个故事全部独立可测 —— 通道语义**只有一处实现点**（收敛目标达成）

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 覆盖率取证 · 独立验收脚本 · 人工验证记录 · **发起者追认** · 冻结面审计

- [X] T036 [P] 覆盖率取证：在**开发期**临时安装 `coverage`（⚠️ **MUST NOT** 写进 `pyproject.toml` 的任何一处 · research D-13）⇒ `python -m coverage run --branch -m pytest -q tests/runtime` ⇒ `python -m coverage json -o /tmp/b5f1-cov.json` ⇒ `python -m coverage report --include="src/freegraph/runtime/*" --show-missing` ⇒ **三个数字都要记**（① **本 feature 新增/修改的代码** —— `channel.py` / `mapping.py` 的**行覆盖与分支覆盖 MUST 均为 100%**（**阻断判据**）；`errors.py` / `__init__.py` 只要求其**新增部分**（两个错误类 + 导出行）**被覆盖**；② **整包** `src/freegraph/runtime/` 的覆盖率 —— **记录但 MUST NOT 阻断**（⚠️ B4F1 的既有模块**从未设过**覆盖率判据**、无 100% 基线** ⇒ 不得由本 feature 承担其历史债）；③ **差分口径** —— `errors.py` / `__init__.py` 的「新增部分」**MUST** 以 `git diff -U0` 的**新增行号集合** ∩ `coverage json` 的 `executed_lines` / `executed_branches` 判定（未覆盖的新增行 / 新增分支数 MUST == **0**））
  ⇒ **⚠️ 三条取证纪律（裁定 17 ⑤ · research D-17 实测）**：① 分支覆盖 **MUST** 以 `--branch` 取证（实测：无 `--branch` 时 `coverage report` **不输出 Branch 列** ⇒ 分支覆盖**无从判定**）；② 文件级 `coverage report` **无法**区分「既有行」与「新增行」⇒ **MUST NOT** 以它单独作「新增部分」的判据；③ 「新增部分」的判定 **MUST** 走差分口径
  ⇒ 把**真实输出**粘进 `harness/verification/B5F1/manual-verification.md` 第 3 节（SC-015 · 口径见 spec FR-019 ② / SC-015）
- [X] T037 [P] 独立验收脚本的 **A1–A3** 段：`harness/verification/B5F1/acceptance.py` 落三条**验收判据**的断言 —— **A1** 归约器 `operator(current, new)` 语义一致（写入序列结果 == `operator.add` **从空值起**的逐次归约）· **A2** 无归约器 key 被覆盖（连续写入后读到末值）· **A3** 路由通道每 super-step 清空（清空后**无值**）⇒ 逐条输出 PASS / FAIL（SC-027）
- [X] T038 独立验收脚本的**内部判据**段：`harness/verification/B5F1/acceptance.py` 落其余 SC 的断言 —— 冲突显式失败 · 有值 / 无值可判定（含「值为 `None`」）· 空值推导 6 类 · 映射保序与身份 · 纯净性与规模探针 · 名字面 · 构造期校验（逐条对应 SC-002…SC-026）（SC-027）
- [X] T039 独立验收脚本的**冻结面审计**段：`harness/verification/B5F1/acceptance.py` 落 —— 依赖**三处**（`dependencies` / `[project.optional-dependencies]` / `[dependency-groups]`）**零新增** `langchain*` / `langgraph*` / `langsmith` · 公开面 **18 / 7** 未变 · `layer-registry.md` **零改动** · 门禁编号仍为 **30** · 新增源文件**署名头覆盖率 == 100%** · C4 / C8 的 `GATE-MOUNT:` 仍为 `not-landed`（SC-012 · SC-011 · SC-024）
- [X] T040 独立验收脚本的**两态与退出码**自测：`harness/verification/B5F1/acceptance.py` —— 未安装 freegraph 时自动把 `<repo>/src` 插入 `sys.path` 测源码树（依赖闭包那条标「◌ 环境未就绪」· **不判失败**）· `--require-installed` 时把「未安装」判为失败 · `--record` 产出**五段式**片段 ⇒ 自测三条路径的**退出码**分别为 `0` / `1` / `2`（SC-027）
- [X] T041 人工验证记录回填：`harness/verification/B5F1/manual-verification.md` —— **五段式**齐全（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）· **A1–A3 逐条有结论** · **来源覆盖表**对全部判据覆盖率 == **100%**（每条标注上游 `路径:行号` + 核实版本 `langgraph 1.2.11` / 澄清条号 / 宪法条款号）· **遗留问题**节登记 **DR-1…DR-5**（`__eq__`/`repr` 未冻结 · 类型可读文本未冻结 · `Overwrite` 不做 · 清空机制差异 · 层注册表措辞过时）（SC-013 · FR-020 · FR-021）
- [X] T042 **发起者追认**（plan 登记项 **R-1** · **阻断合入**）：宪法质量门禁 **3 / 4 / 5** 的四部分在本 feature **物理不可达成**（C4 回归 · C8 回归 · fake 模型轮 · 真实模型轮 —— 共享同一根因：**无图可跑**，读取层 = B5F2 · fresh 读 = B8F1 · 调度 = B7F1 · 编译执行 = B7F2 / B7F3）⇒ MUST **停下来等发起者追认**，MUST **NOT** 代签；追认文字 MUST 落在 `harness/verification/B5F1/manual-verification.md` ⇒ ⚠️ **MUST NOT** 改宪法正文 · **MUST NOT** 写一条永久红的 CI · **MUST NOT** 把 C4 / C8 的 `GATE-MOUNT:` 标记改成 `landed`
  > **✅ 已追认（2026-11-09）** —— 发起者在本会话中明示「**追认**」并指示收尾与提交推送；
  > 追认栏落在 `harness/verification/B5F1/manual-verification.md` §4.3；
  > 实现者**未代签** · 宪法正文**零改动** · CI **零改动** · C4 / C8 的 `GATE-MOUNT:` 仍为 `not-landed`
  > ⇒ 执行闸口 **A5 通过** ⇒ **可合入**。
- [X] T043 全量门禁核对：跑 `python -m pytest tests/ -ra`（**全绿** · 既有门禁零破坏）⇒ 跑 `harness/scripts/gates/gate_G*.py`（**10 条**逐条退出码 0）⇒ 核对 `.github/workflows/ci.yml` **零改动**（`testpaths = ["tests"]` ⇒ 新测试自动被收集）· 层注册表**零改动** ⇒ 门禁编号仍为 **30**（SC-011 · SC-012）
  > **📌 门禁的执行前置（裁定 17 外的可执行性补正）**：**10 条门禁并非全部可裸跑** ——
  > **G22** 需 `uv pip install` 建隔离 venv（**需网络**）· **G28** 需
  > `unshare --net --map-root-user`（**网络命名空间** · 脚本自身 MUST NOT 调 `unshare`）
  > ⇒ MUST 按 `.github/workflows/ci.yml` 的**分组配方**执行（G21 / G23 / G24 / G25 / G26 / G29 / G30
  > 本地直跑；G22 / G27 / G28 走 **Linux only** 步骤），**MUST NOT** 在无网络 / 无命名空间权限的
  > 环境下裸跑并把失败当作本 feature 的缺陷。
- [X] T044 执行 `quickstart.md` §1–§9 全文（验收闸口 **V1–V9** 逐条）⇒ 把**真实输出**记入 `harness/verification/B5F1/manual-verification.md` 第 3 节 ⇒ 逐条核对 V1–V9 结论（SC-013）
- [X] T045 文档合规核对：`README.md` 的 **API 兼容矩阵零新增行**（并在人工记录中显式记「无新增」以区别于「漏更新」）· `THIRD_PARTY_NOTICES` **零改动**（零新增依赖）· 新增源文件**署名头**齐全且模块 docstring 为首个语句（SC-012 · FR-019）· **同步 `harness/verification/README.md`** —— 「验收脚本」索引表**补 B5F1 行**（`acceptance.py` + `manual-verification.md` 链接 + 实测结论）且「`acceptance.py` 可选」一节的举例按本 feature 的实际状态更新（**沿用 B4F1 T059 的既有形态** · 文档合规 · 原则 X）
- [X] T046 提交前自检：核对**零改动清单**（见 Path Conventions）逐条未被触碰 ⇒ `grep -c 'NEEDS CLARIFICATION' spec.md` == **0** ⇒ 附录追溯表 **FR 27/27 · SC 28/28** 全覆盖 ⇒ `contracts/channel-contract.md` 的 `<!-- authority: yes -->` 标记在位 ⇒ 提交（**由发起者决定 commit 时机**）

---

## Dependencies & Execution Order

### 执行闸口（Phase 闸口 · 每道 MUST 全绿才进下一 Phase）

| 闸口 | 触发点 | MUST 验证 | 关联判据 |
|---|---|---|---|
| **A1** | Phase 1–2 结束 | `Channel` 抽象就位（**运行时不可实例化**）· 4 个属性只读 · `_MISSING` 哨兵 · 两个错误类型就位（结构化字段齐备 · **不携带用户值**）· `pytest tests/ -ra` **仍全绿**（既有门禁零破坏）· 层注册表**零改动** | FR-001 · FR-002 · FR-011 · FR-013 · FR-017 · FR-016 · SC-009 · SC-018 · SC-020 · SC-023 · SC-024 |
| **A2** | Phase 3 结束（US1） | 覆盖语义成立（连续两次写入 ⇒ 读到**末值** · 归约器调用次数 == 0）· 一步内多值 ⇒ **显式失败**且**值不变** · 初始「无值」· 写 `None` 后判定为「有值」 | FR-003 · FR-004 · FR-011 · SC-001 · SC-004 · SC-006 · SC-016 · SC-020（**验收判据 A2**） |
| **A3** | Phase 4–5 结束（US2–US3） | 归约语义与**空值起折**基准一致 · 归约器**身份**判定成立 · 空值推导 **6 类**全对 · 首次写入两分支（**无值 ⇒ 直存、归约器调用次数 == 0**）· 归约失败**不污染**状态 · 路由通道清空后**无值**（**不是** `None`）· 清空**幂等** | FR-005 · FR-006 · FR-007 · FR-008 · FR-009 · FR-010 · FR-022 · SC-002 · SC-003 · SC-007 · SC-010 · SC-021 · SC-023（**验收判据 A1 / A3**） |
| **A4** | Phase 6 结束（US4） | 映射规则 + **保序** + 归约器**身份** · 路由通道**不由** schema 派生 · 自定义子类**可替换** · 名字面逐字一致 · 规模探针（引用数**不随 key 数增长**）· 浅引用 · **零副作用三断言**全绿（`sys.modules` / 环境变量 / 出站）· 契约与上游对照**逐条**有实现与断言 | FR-012 · FR-013 · FR-015 · FR-021 · FR-023 · FR-024 · FR-025 · SC-005 · SC-008 · SC-014 · SC-017 · SC-019 · SC-022 · SC-025 · SC-026 |
| **A5** | 收官 | **T042 发起者追认**（登记项 R-1 · **阻断合入**）· 覆盖率**行/分支 100%** · 独立验收脚本 **PASS**（退出码 0）· 人工验证记录五段式 + 来源覆盖表齐全 · **A1–A3 逐条有结论** · quickstart 全文绿（V1–V9） | FR-019 · FR-020 · FR-026 · SC-013 · SC-015 · SC-027（**验收判据 A1–A3**） |

> **📌 编号说明（**四套**编号 · 同名不同义）**：本表的 **A1–A5 是「执行闸口」**（Phase 闸口）——
> 而 spec 的「**验收判据 A1–A3**」是**引文 §6 / 立项书 §5.2** 的编号
> （A1 归约器语义一致 · A2 无归约器 key 被覆盖 · A3 路由通道每 super-step 清空）；
> `quickstart.md` 的**验收闸口**用 **V1–V9**（Verification gates）；
> 宪法门禁是 **G1–G30** ⇒ **四套编号互不撞名** ⇒ 引用时 MUST 带限定语
> （「验收判据 A1（引文 §6）」/「执行闸口 A1」/「quickstart 闸口 V1」/「门禁 G21」）。

### MUST 由发起者亲自出面的闸口（实现阶段只能「备料」，不得代劳）

- **T042 —— 宪法质量门禁 3 / 4 / 5 的偏离登记追认**（plan 登记项 R-1）：四部分**共享同一根因**
  （验收基线跑通需要**完整内核运行时**，而通道层按立项书 §6.2 属 M1 中段；本 feature
  **不交付状态读取层与调度循环**）⇒ 依宪法 **v1.6.0** 的窄口径通则处置
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
- **US2（P2）**：Phase 2 后可开始 —— 与 US1 共用底座与错误契约，但**独立可测**
- **US3（P3）**：Phase 2 后可开始 —— 与 US1 共用覆盖语义与冲突错误，但**独立可测**
- **US4（P4）**：Phase 2 后可开始 —— 依赖三类通道**已就位**（映射入口要按类型分派），
  但**其测试**（可替换性 / 名字面 / 纯净性）可与 US1–US3 并行推进

### Within Each User Story

- **测试 MUST 先写且 MUST 先失败**（本 feature 的测试即判据）—— 实现任务**不标** `[P]` ⇒
  实现**不得**与同阶段的测试任务并行起草（实现须等测试先红）；**合入顺序**：测试先红 → 实现 → 转绿
- 底座（Foundational）→ 三类通道（US1–US3）→ 映射与收敛（US4）→ 守卫与纪律（Polish）
- Story complete before moving to next priority

### Parallel Opportunities

> **📌 纪律（澄清轮 Q15 修复 · I3）**：**实现任务一律不标 `[P]`** ⇒ 实现 MUST 等同阶段的测试
> **先红**；**合入顺序**：测试先红 → 实现 → 转绿。下列「并行」指**起草**层面的并行（不同文件）。

- **Phase 1**：T001 · T002 · T003 · T004 四条可并行（**四个不同文件**）；T005 依赖它们（取基线）
- **Phase 2**：T006 可与 T007 并行（**两个不同文件**：`errors.py` / `channel.py`）；T008 依赖二者
- **Phase 3**：T009 与 T010 / T011 / T012 分属**三个不同文件** ⇒ 可并行起草
  ⇒ ⚠️ T010 与 T009 **同在** `test_channel_semantics.py` ⇒ **落盘须串行**；
  T012（实现）**不标** `[P]`；T013 依赖 T012
- **Phase 4**：T014 · T015 · T016 · T017 分属**两个**文件 ⇒ T014 可与 T016 / T017 并行起草
  ⇒ ⚠️ T015 与 T014 **同文件** ⇒ 落盘须串行；T018 / T019（实现）**不标** `[P]`；T020 依赖 T019
- **Phase 5**：T021 · T022 · T023 分属**两个**文件 ⇒ T021 可与 T022 并行起草
  ⇒ ⚠️ T023 与 T021 **同文件** ⇒ 落盘须串行；T024（实现）**不标** `[P]`；T025 依赖 T024
- **Phase 6**：T026 · T028 · T029 · T031 四条**测试**任务分属**四个不同文件** ⇒ 四条可并行
  ⇒ ⚠️ T027 与 T026 **同文件**、T030 与 T029 **同文件** ⇒ 落盘须串行；
  T032 / T033（实现）与 T034（导出）**不标** `[P]`；T035（契约守卫）依赖前序实现
- **Phase 7**：T036 · T037 可并行（`coverage` 取证写人工记录 / 验收脚本的 A1–A3 段写 `acceptance.py`
  ⇒ **不同文件**）；T038–T040 与 T037 **同在** `acceptance.py` ⇒ **落盘须串行**
- 不同用户故事可由不同成员并行推进（底座 Phase 2 完成后）

---

## Parallel Example: User Story 2

```bash
# 并行组 1（**不同文件** ⇒ 可同时起草；实现任务不在组内）：
Task: "在 tests/runtime/test_channel_semantics.py 写归约语义用例"      # T014
Task: "在 tests/runtime/test_channel_errors.py 写归约失败与构造期校验用例"  # T016

# 并行组 2（**同一文件** ⇒ 落盘须串行，但可由同一成员连续完成）：
Task: "在 tests/runtime/test_channel_semantics.py 写空值推导与首次写入用例"  # T015
Task: "在 tests/runtime/test_channel_semantics.py 写归约型初始状态用例"      # T017

# 之后（**不标 [P]** ⇒ 须等上面的测试先红）：
Task: "实现 src/freegraph/runtime/channel.py 的空值推导 _derive_empty_value"   # T018
Task: "实现 src/freegraph/runtime/channel.py 的 BinaryOperatorAggregate"        # T019
```

---

## Implementation Strategy

### MVP First（User Story 1 Only）

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational（CRITICAL - blocks all stories）
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: 跑 `python3 harness/verification/B5F1/acceptance.py` 验证 A2（覆盖语义）独立成立
5. Deploy/demo if ready（⚠️ 本 feature **无图可跑** ⇒ 「demo」= 单元级演示）

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US1 → 验证 A2（覆盖）→ 里程碑
3. Add US2 → 验证 A1（归约）→ 里程碑
4. Add US3 → 验证 A3（路由清空）→ 里程碑
5. Add US4 → 验证收敛与纯净性 → 里程碑
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1（+ US3 的路由通道，同一 `channel.py` ⇒ 落盘协调）
   - Developer B: User Story 2（空值推导 + 归约型，同一 `channel.py` ⇒ 落盘协调）
   - Developer C: User Story 4 的测试（可替换性 / 名字面 / 纯净性 —— **独立文件**）
3. Stories complete and integrate independently

---

## 附录 · 任务 ↔ spec 追溯表

> **反向覆盖**：**FR 27/27 · SC 28/28** —— 每个 FR 与每个 SC **至少**被一条任务映射。
> （宪法原则 VI：「tasks MUST 逐条勾选、**可追溯到 spec 条目**」）

| 任务 | FR | SC | 说明 |
|---|---|---|---|
| T001 | FR-015 · FR-016 | — | `channel.py` 骨架（署名头 · 惰性顶层包） |
| T002 | FR-015 · FR-016 | — | `mapping.py` 骨架 |
| T003 | FR-019 | — | **五个**测试模块骨架 |
| T004 | FR-026 | SC-027 | 验收脚本骨架（两态 · 退出码 0/1/2） |
| T005 | FR-020 | SC-013 | 人工记录骨架 + 实现前绿基线 |
| T006 | FR-017 | SC-018 | 两个错误类型（结构化字段 · 继承 · 不携带用户值） |
| T007 | FR-001 · FR-002 · FR-011 · FR-013 | SC-004 · SC-009 · SC-020 · SC-023 | `Channel` 抽象（`__slots__` · 4 只读属性 · `_MISSING`） |
| T008 | FR-016 | SC-011 | 导出底座符号（4 → 7） |
| T009 | FR-003 · FR-004 | SC-001 · SC-020 | 覆盖语义用例（**验收判据 A2**） |
| T010 | FR-002 · FR-011 · FR-022 | SC-004 · SC-009 · SC-023 | 初始「无值」· 空写入无操作 · 只读 · 属性集 |
| T011 | FR-017 | SC-018 | 空通道读取的错误契约 |
| T012 | FR-003 · FR-004 · FR-011 | SC-001 · SC-004 · SC-006 · SC-020 | `LastValue`（覆盖 · 冲突失败 · 返回值口径） |
| T013 | FR-001 | SC-019 | 导出 `LastValue` |
| T014 | FR-005 · FR-007 · FR-014 | SC-002 · SC-010 · SC-021 | 归约语义用例 + **空值起折**基准（**验收判据 A1**） |
| T015 | FR-006 · FR-007 | SC-007 · SC-021 | 空值推导 6 类 · 首次写入两分支 · 空值独立实例 |
| T016 | FR-008 · FR-025 | SC-006 · SC-016 · SC-026 | 归约失败不污染 · 构造期校验（`TypeError` / `ValueError`） |
| T017 | FR-022 | SC-023 | 归约型初始状态三档 + 清空后无值 |
| T018 | FR-006 | SC-007 · SC-021 | 空值推导（剥包装 · 抽象容器 · 新实例） |
| T019 | FR-005 · FR-007 · FR-008 · FR-014 · FR-025 | SC-002 · SC-010 · SC-021 | `BinaryOperatorAggregate`（归约 · 两分支 · 失败不污染） |
| T020 | FR-001 | SC-019 | 导出 `BinaryOperatorAggregate` |
| T021 | FR-009 · FR-011 | SC-003 · SC-004 | 清空语义用例（**验收判据 A3**） |
| T022 | FR-004 · FR-010 · FR-017 | SC-006 · SC-016 · SC-018 | 路由通道冲突失败（结构化字段） |
| T023 | FR-007 · FR-022 | SC-023 | 清空 ≠ 回到初始状态 |
| T024 | FR-009 · FR-010 | SC-003 · SC-006 | `EphemeralValue`（清空 · 冲突失败） |
| T025 | FR-001 | SC-019 | 导出 `EphemeralValue` |
| T026 | FR-012 | SC-008 · SC-019 | 映射规则 · 保序 · 身份判定 |
| T027 | FR-012 · FR-025 | SC-008 · SC-026 | 路由通道显式创建 · 映射自洽 |
| T028 | FR-001 · FR-002 | SC-017 · SC-019 | 可替换性 + 名字面逐字一致 |
| T029 | FR-013 · FR-023 · FR-024 | SC-009 · SC-022 · SC-024 · SC-025 | 纯净性 · 规模探针 · 浅引用 · 无同步原语 |
| T030 | FR-015 | SC-005 | 导入副作用（子进程）· 零环境变量 · 零出站 |
| T031 | **FR-027** · FR-019 ③ | **SC-028** · SC-017 · SC-002 · SC-006 | **参数化组合**用例（归约器 × 通道 · 立项书 S5 ③） |
| T032 | FR-012 · FR-025 | SC-008 · SC-026 | `build_channel`（类型分派 · 身份 · 自洽校验） |
| T033 | FR-012 | SC-008 | `build_channels`（保序 · 每 key 一个） |
| T034 | FR-012 | SC-019 | 导出两个映射入口（10 → 12） |
| T035 | FR-018 · FR-021 | SC-014 · SC-012 | 契约守卫（解析 `channel-contract.md`）+ 上游对照逐条 |
| T036 | FR-019 | SC-015 | 覆盖率行/分支 100% 取证（不进依赖声明） |
| T037 | FR-026 | SC-027 · SC-002 · SC-001 · SC-003 | 验收脚本 **A1–A3** 段 |
| T038 | FR-021 · FR-026 | SC-027 · SC-014 | 验收脚本的内部判据段 |
| T039 | FR-015 · FR-016 · FR-018 · FR-023 | SC-011 · SC-012 · SC-024 | 验收脚本的冻结面审计段 |
| T040 | FR-026 | SC-027 | 两态运行 + 退出码 0/1/2 自测 + `--record` |
| T041 | FR-020 · FR-021 | SC-013 · SC-014 | 人工记录回填（五段式 · 来源覆盖表 · DR 登记） |
| T042 | FR-018 · FR-020 | SC-013 | **发起者追认**（R-1 · **阻断合入**） |
| T043 | FR-016 · FR-018 | SC-011 · SC-012 | 全量门禁核对（pytest · G21–G30 · CI 零改动） |
| T044 | FR-020 | SC-013 | 执行 quickstart §1–§9（V1–V9） |
| T045 | FR-019 · FR-018 | SC-012 | 兼容矩阵零新增 · `THIRD_PARTY_NOTICES` 零改动 · 署名头 |
| T046 | FR-016 · FR-018 | SC-011 | 提交前自检（零改动清单 · 追溯表 · 覆盖） |

> **SC 反向覆盖核对**（由上方正向表**逐条派生** · 保持两者一致）：
> SC-001 → T009/T012/T037 · SC-002 → T014/T019/T031/T037 · SC-003 → T021/T024/T037 ·
> SC-004 → T007/T010/T012/T021 · SC-005 → T030 · SC-006 → T012/T016/T022/T024/T031 ·
> SC-007 → T015/T018 · SC-008 → T026/T027/T032/T033 · SC-009 → T007/T010/T029 ·
> SC-010 → T014/T019 · SC-011 → T008/T039/T043/T046 · SC-012 → T035/T039/T043/T045 ·
> SC-013 → T005/T041/T042/T044 · SC-014 → T035/T038/T041 · SC-015 → T036 ·
> SC-016 → T016/T022 · SC-017 → T028/T031 · SC-018 → T006/T011/T022 ·
> SC-019 → T013/T020/T025/T026/T028/T034 · SC-020 → T007/T009/T012 · SC-021 → T014/T015/T018/T019 ·
> SC-022 → T029 · SC-023 → T007/T010/T017/T023 · SC-024 → T029/T039 ·
> SC-025 → T029 · SC-026 → T016/T027/T032 · SC-027 → T004/T037/T038/T040 ·
> SC-028 → T031
> ⇒ **28/28 全覆盖**（每条 SC 至少被一条任务映射 · 与上方正向表**逐条一致**）。
