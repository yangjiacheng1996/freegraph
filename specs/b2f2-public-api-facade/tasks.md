---

description: "B2F2 · 公开 API 门面 `freegraph/graph.py`（7 符号导出面）+ API 签名快照冻结 + 顶层包惰性断言 —— 任务清单"
---

# Tasks: B2F2 · 公开 API 门面 `freegraph/graph.py`（7 符号导出面）+ API 签名快照冻结

**Input**: Design documents from `/specs/b2f2-public-api-facade/`

**Prerequisites**: plan.md（必读）、spec.md（必读 · 含 **12 条裁定 + 12 条澄清问答 Q1–Q12** · FR-019）、research.md（**23 条决策 D-01…D-23**）、data-model.md（7 个符号的冻结规格 + 快照格式规则）、contracts/facade-api.md（**唯一手写权威** · 7 符号）、contracts/snapshot-format.md（快照格式契约）、contracts/architecture-gates.md（**13 条门禁 G1–G13 + 新增 G14–G20**）、quickstart.md（验收指南）

**Tests**: **含**测试任务 —— 本 feature 的需求本体就是**形状与判据**
（**18 条成功标准** + **7 条新增门禁**（G14–G20）各带自检，**自检共 8 条**——
G15 的两段各一条），
测试是**交付面的一部分**，不是可选项。

**Organization**: 任务按用户故事分组，每个故事可**独立实现、独立测试、独立交付**。

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可并行（**不同文件**且无未完成依赖）——同一文件内的后续任务**不标** `[P]`
- **[Story]**：所属用户故事（US1…US4）
- 每条任务都带**确切文件路径**；冻结面的**逐字内容**在 `contracts/` 与 `data-model.md` 中，本文件**只引用不复制**
- **逐条追溯**：每条任务对应的 **FR / SC** 见文末「**附录 · 任务 ↔ spec 追溯表**」
  （宪法原则 VI：「tasks MUST 逐条勾选、**可追溯到 spec 条目**」）

## Path Conventions

- 单项目：`src/` · `tests/` 在仓库根
- 门面：`src/freegraph/graph.py` · 外壳：`src/freegraph/_stategraph.py` · `src/freegraph/_primitives.py`
- 门面测试：`tests/facade/`（**不叫** `test_architecture.py` —— 与 `tests/contracts/test_architecture.py`
  同名会在无 `__init__.py` 的目录下触发 pytest 的 `import file mismatch`；见 `research.md` D-16）
- 契约文件：`specs/b2f2-public-api-facade/contracts/`

> **⚠️ 落地拆分提示**：导出面**恰 7 个**是本 feature 的**终态**。US1 先交付 **3 个**
> （`StateGraph` / `START` / `END`），US3 才补齐其余 **4 个** ⇒ 门禁 **G15 按两段落地**
> （子集段始终启用 / 集合相等段在 US3 后启用，见 `contracts/architecture-gates.md` G15）。
> **MUST NOT** 为了「让门禁好看」而在 US1 阶段塞入占位导出。

---

## Phase 1: Setup（共享基础设施）

**Purpose**：门面的测试脚手架与门禁**共享辅助**，不产出任何用户可见能力。

- [X] T001 [P] 创建 `tests/facade/conftest.py`：署名头（`# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph`）+ docstring 为首个语句 + `sys.path` 注入（把 `<repo>/src` 插入最前；`FREEGRAPH_TEST_INSTALLED=1` 时跳过 —— 沿用 `tests/contracts/conftest.py` 的既有口径）+ fixture `repo_root` / `src_dir` / `spec_dir`
- [X] T002 [P] 创建 `tests/facade/_gatesupport.py`（署名头 + docstring）：① AST 辅助 —— 统计模块内 `class` / `def` / `async def` 语句数并返回**违规行号**、扫描 import（**两档制 · research D-22**）：① **内部档** —— 导入路径的**层段**（首段为 `freegraph` 时取**第二段**，否则取**首段**）∈ {`persistence`, `observability`} 即违规（`freegraph.contracts` 与门面包内私有模块**合法**；**L2 / L3 合法** —— ARCH-1 唯一例外 · 裁定 9）；② **第三方档** —— `langchain*` / `langgraph*` / `langsmith` / `pydantic` / `typing_extensions` 即违规（**标准库**用 `sys.stdlib_module_names` 判定 ⇒ `freegraph.*` **不属**本档）、扫描 `os.environ` / `os.getenv`、扫描出站与文件 I/O（`socket` / `urllib` / `http` / `open(` / `Path.write_*` / `subprocess`）；② `run_in_subprocess(code) -> str`（用 `sys.executable` 跑子进程并回传 `sys.modules` 快照 —— **必须子进程**，测试进程自身已导入 pytest；**必须注入 `PYTHONPATH=<src_dir>`** 并把 `cwd` 设为**临时目录**（防仓库根同名目录劫持导入）—— 照抄既有 `tests/contracts/test_architecture.py` 的 `_run_python` 口径，否则子进程 import 不到 `freegraph`、门禁**假红**）；③ `parse_manifest_symbols(path) -> set[str]`（按 `contracts/facade-api.md` §0 的解析规则：取 `from ... import (` 与配对 `)` 之间的行、跳过 `#` 注释行、每行取第一个逗号前的标识符、返回**集合**）
- [X] T003 [P] 创建 `tests/facade/__init__.py`（空占位：署名头 + docstring + `__all__ = []`）—— 使 `tests/facade/` 可被绝对导入，避免门禁辅助被 pytest 的 rootdir 插入机制重复导入
- [X] T004 在 `tests/facade/conftest.py` 注册 `--update-api-snapshot` 开关：`pytest_addoption` + `action="store_true"` + 读取 helper；**默认关闭**（常规跑 pytest 绝不改快照文件 —— spec FR-011 ①）

**Checkpoint**：测试脚手架可跑（`pytest tests/facade/ --collect-only` 无错）

---

## Phase 2: Foundational（阻塞性前置）

**Purpose**：三个源码模块的**骨架** + 三条**在任何用户故事之前就必须常驻**的门禁。

**⚠️ CRITICAL**：US1–US4 的全部工作都依赖本阶段的模块骨架与门禁辅助。

- [X] T005 [P] 创建 `src/freegraph/graph.py`：署名头 + 模块 docstring（须写明：**唯一公开入口** · **零实现体** · **不得**使用 `from __future__ import annotations`（该 future import 会留下名为 `annotations` 的公开绑定，破坏「公开名恰 7 个」判据 —— 见 `research.md` D-02）· 门面只做导出与常量）+ `__all__ = []`（**此阶段为空**）+ **不得**有任何 import / 类体 / 函数体
- [X] T006 [P] 创建 `src/freegraph/_stategraph.py`：署名头 + 模块 docstring（占位：说明「本模块承载 `StateGraph` 外壳，未来由 **B6F1** 在同一门面导出名下接线；门面导出面 MUST NOT 因接线而改变」）—— **此阶段无类体**
- [X] T007 [P] 创建 `src/freegraph/_primitives.py`：署名头 + 模块 docstring（占位：说明「本模块承载 `Send` / `interrupt` 外壳，未来由 **B11F1** / **B10F1** 接线」）—— **此阶段无类体**
- [X] T008 在 `tests/facade/test_facade_gates.py` 落**门禁 G14**（门面零实现体）：AST 断言 `src/freegraph/graph.py` 内 `class` / `def` / `async def` 语句数 **== 0**，违规时报**行号**；**并落其自检**（临时造一处 `def` ⇒ 断言门禁确实报出）—— 判定细则见 `contracts/architecture-gates.md` G14
- [X] T009 在 `tests/facade/test_facade_gates.py` 落**门禁 G15 子集段**：`set(freegraph.graph.__all__) ⊆`（`contracts/facade-api.md` §0 解析出的 7 个）**且**门面模块内公开名集合 `⊆` 同一集合；**并落其自检**（往门面塞一个第 8 个公开名 ⇒ 断言门禁确实报出）；依赖 T008（同一文件）
- [X] T010 在 `tests/facade/test_facade_gates.py` 落**门禁 G17**（门面依赖卫生 · **两档制 · research D-22**）：AST 扫描 `src/freegraph/graph.py` + `_stategraph.py` + `_primitives.py`，断言 ① **内部档**：指向 **L4 / L5**（层段 ∈ {`persistence`, `observability`}）的 import 数 **== 0**（`freegraph.contracts` 与门面包内私有模块**合法**；**L2 / L3 合法** —— 门面是 ARCH-1 的唯一例外 · 裁定 9 ⇒ B6F1 / B10F1 / B11F1 接线后不假红）；② **第三方档**：`langchain*` / `langgraph*` / `langsmith` / `pydantic` / `typing_extensions` 的 import 数 **== 0**（**标准库**用 `sys.stdlib_module_names` 判定 ⇒ `freegraph.*` **不属**本档）；③ 环境变量读取数 == 0；④ 出站 / 文件 I/O 调用数 == 0；**并落其自检两例**（① 临时造一处 `os.environ` 读取 ⇒ 断言门禁确实报出；② 临时造一处 `from freegraph.persistence import X` ⇒ 断言**内部档**确实报出，而 `from freegraph.contracts import X` **不报**、`from freegraph.runtime import X` **不报**（L2 合法））；依赖 T009（同一文件）
- [X] T011 在 `tests/facade/test_facade_gates.py` 落**门禁 G20**（本 feature 新建源文件的**署名头**）：**逐文件**断言本 feature 新建的 10 个 `.py` 首行逐字等于 `# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph`，且模块 docstring 是首个语句；文件清单见 `contracts/architecture-gates.md` G20；**并落其自检**（临时破坏某文件的署名头 ⇒ 断言门禁确实报出）；依赖 T010（同一文件）
- [X] T012 复核**既有门禁 G1–G13 未被影响**：执行 `pytest tests/contracts/test_architecture.py -q` 断言全绿（**本 feature MUST NOT** 修改 `src/freegraph/contracts/**` 与 `tests/contracts/**` —— 见 `plan.md`「与既有 feature 的关系」）
  > **⚠️ 实测偏离（已登记 · 不改本任务的判据，只登记事实）**：`src/freegraph/contracts/**` **逐字未动** ✅；
  > `tests/contracts/test_architecture.py` 有**一处**改动——既有门禁 **G8** 的**整表**判据
  > （「矩阵首列符号集合 == 契约层 18 个」）与 spec **FR-012 ③**（兼容矩阵 MUST 补入门面的 5 行）
  > **互斥** ⇒ G8 按其**声明范围**（`contracts/architecture-gates.md` §3：「G8 的范围 = 契约层 18 个符号」）
  > **收敛为按层判定**（「契约层 18 个齐备」+「无重复行」），**整表**的「无清单外符号」判据
  > 移交门禁 **G19**（门面侧）。**契约层的任何一条判据都未被削弱**。
  > 另有一处**顺带修复**：`_symbol_annotations` 原依赖 `Protocol.__protocol_attrs__`
  > （**只在 3.12+ 存在**）⇒ 在 **3.11 最低档**恒失败（**该缺陷在本 feature 之前即存在**，
  > 已在 pristine 工作树上复现）→ 改为跨版本稳定的枚举方式。
  > 详见 `harness/verification/B2F2/manual-verification.md` §5 遗留 #1 与 #4。

**Checkpoint**：三个模块骨架就位、G14 / G15 子集段 / G17 三条门禁常驻且带自检、既有门禁全绿

---

## Phase 3: User Story 1 - 验收基准脚本的 import 能成立 (Priority: P1) 🎯 MVP

**Goal**：`from freegraph.graph import StateGraph, START, END` 在**隔离环境**执行成功（退出码 0）——
哪怕 `StateGraph` 此刻只是未接线的外壳。

**Independent Test**：新建裸 venv → `pip install .` → 执行该 import ⇒ 退出码 0；
且 `pip list` 中只有 `freegraph`（依赖闭包为空集）。

### Tests for User Story 1 ⚠️（先写、先失败）

- [X] T013 [P] [US1] 在 `tests/facade/test_facade.py` 写两组断言：**import 冒烟**（子进程执行 `from freegraph.graph import StateGraph, START, END`，断言**退出码 0** 且三个名字均可取到 —— SC-001 / A1）＋ **常量取值**（`START == '__start__'`、`END == '__end__'` 逐字相等，且两者均为 `str` —— SC-002 / C9）
- [X] T014 [US1] 在 `tests/facade/test_facade.py` 写两组断言：**导出面子集**（`{"StateGraph", "START", "END"} ⊆ set(freegraph.graph.__all__)` 且门面公开名集合 ⊇ 同一集合 —— **不断言**恰 7 个，那是 US3 的集合相等段）＋ **构造语义**（`StateGraph(schema)` 构造成功且不抛异常；`StateGraph(schema, extra)` 抛 `TypeError`；构造**无副作用** —— SC-010）；依赖 T013（同一文件）
- [X] T015 [US1] 在 `tests/facade/test_facade.py` 写**未接线异常**断言：`add_node` / `add_edge` / `add_conditional_edges` / `compile` 各抛 `NotImplementedError`，且消息匹配正则 `(?:add_node|add_edge|add_conditional_edges|compile) 尚未接线（由 B\dF\d 交付）`（SC-011）**＋「未越界」断言**（四个方法**不产生**任何节点 / 边 / 编译产物的真实语义，`compile()` **不返回**可执行产物 —— **SC-016**；与未接线断言同批落地，避免纠错面扩大到**已定稿**的快照 / 兼容矩阵）；依赖 T014（同一文件）

### Implementation for User Story 1

- [X] T016 [US1] 在 `src/freegraph/_stategraph.py` 实现 `StateGraph` 外壳：`__init__(self, schema: Any) -> None`（**恰一个**必填位置参数、参数名 `schema`；私有存 `self._schema`；**零校验**、**零副作用**）＋ 四个方法按 `data-model.md` §2.1 的**逐字签名**实现，方法体**只**抛 `NotImplementedError`，消息格式见 `data-model.md` §4（`add_node` / `add_edge` / `add_conditional_edges` → B6F1；`compile` → B7F2）；**不得**暴露任何公开属性（`schema` 私有 —— D-11）
- [X] T017 [US1] 在 `src/freegraph/graph.py` 落地 `START = "__start__"` / `END = "__end__"`（**字符串常量**，非枚举）与 `from ._stategraph import StateGraph`，并把 `__all__` 设为**本阶段的 3 个**（`StateGraph` / `START` / `END`）—— 集合相等段在 US3 启用
- [X] T018 [US1] 按 `quickstart.md` §2 做**隔离环境**验收：**新建一个裸 venv 并记下其路径**（后续 T039 / T040 **复用同一个 venv**，不得各建一套）→ `pip install .` → 执行 `from freegraph.graph import StateGraph, START, END` ⇒ 退出码 0；`pip list` 只有 `freegraph`；把 venv 路径与实测输出记入 `harness/verification/B2F2/manual-verification.md`

**Checkpoint**：US1 可独立验收 —— 隔离环境 import 退出码 0；G14 / G15 子集段 / G17 仍绿

---

## Phase 4: User Story 2 - 公开 API 的形状不会悄悄漂移 (Priority: P2)

**Goal**：入库一份**可复现**的签名快照，并让任何签名变更在**测试**里**显式可见**
（diff 呈现、须人工确认；**CI 流水线的挂载归 B3F1** —— spec 裁定 Q12）。

**Independent Test**：故意把门面中任一方法的**参数名**或**注解**改掉 ⇒ 快照比对测试**失败**且输出
**差异行数 ≥ 1**；同一份代码两次生成快照**逐字节相同**。

### Tests for User Story 2 ⚠️（先写、先失败）

- [X] T019 [P] [US2] 在 `tests/facade/_snapshot_tools.py`（署名头 + docstring）实现 `normalize_annotation(ann) -> str`：**逐条**实现 `contracts/snapshot-format.md` §2 的 **N-1…N-6**（去外层引号 · 去 `typing.` / `collections.abc.` 限定前缀 · `Optional[X]`→`X | None` 与 `Union[X, Y]`→`X | Y`（保持原成员顺序）· `NoneType`→`None` · 空白归一 · 缺省返回注解记 `-> None`）
- [X] T020 [US2] 在 `tests/facade/_snapshot_tools.py` 实现 `render_api_snapshot(namespace: Mapping[str, Any]) -> str`：**纯函数**（无 I/O、无副作用 —— D-10）；条目语法 `[kind] name`（kind ∈ constant/function/class/method/attribute）· 顶级与类内条目**按字典序** · 类内缩进 **2 空格** · **参数顺序逐字保留**（顺序是语义，不排序）· 常量记字面值 · 属性记「名: 注解 = 缺省值」＋只读/可写标注 · **必填参数记 `= <required>`** · dunder 不记但**记 `__init__`** · **dataclass 属性的取数 MUST 逐条实现 `contracts/snapshot-format.md` §1.1 的 D-21-1…D-21-4**（缺省值取 `dataclasses.fields()` 的 `.default` / `.default_factory()`、ClassVar 取 `cls.__annotations__`、frozen ⇒ `(readonly)`、注解取 `fields()[i].type`；**MUST NOT** 用 `getattr(cls, name)` 取缺省值）；依赖 T019（同一文件）
- [X] T021 [P] [US2] 在 `tests/facade/test_api_snapshot.py` 写两组断言：**逐字节比对**（渲染结果 == `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`，不等时输出 **diff** 且差异行数 ≥ 1）＋ **可复现性**（同一份代码两次渲染**逐字节相同**，差异字节数 == 0）
- [X] T022 [US2] 在 `tests/facade/test_api_snapshot.py` 写三组断言：**更新入口默认不生效**（常规执行 pytest **不改动**快照文件，内容逐字节不变）＋ **显式更新幂等**（`--update-api-snapshot` 在代码未变时产出相同文本）＋ **自检三例**（**必须走真实的比对路径** —— research **D-23**）：把比对对象指向 `tmp_path` 下一份**被改动过**的快照文件，断言比对**确实失败**且 **diff 非空**。**零副作用**：不碰真源码、只在 `tmp_path` 下操作。**必须覆盖三例**：① 把某方法**参数改名**；② **改动某方法的参数注解或返回注解** —— Q3「全冻」的核心收益，缺它则注解漂移仍会悄悄溜过；③ **新增一个公开属性** —— Q6 专门立的口径，缺它属性漂移仍会悄悄溜过。**注意**：MUST NOT 只断言「渲染结果 ≠ 入库文本」（那只验证**渲染器**，守不住「比对逻辑本身坏掉」这条失效模式 —— FR-011 ② / SC-005）；依赖 T021（同一文件）
- [X] T023 [US2] 在 `tests/facade/test_api_snapshot.py` 写**快照文本合规**断言：编码 **UTF-8**（无 BOM）· 换行 **LF**（无 CRLF）· **末行带换行** · 不含时间戳 / 绝对路径 / Python 版本号 / 内存地址 · 顶级条目集合 == 门面**当前**导出面集合（随 US3 增长而增长 —— **不硬编码 7**）；依赖 T022（同一文件）

### Implementation for User Story 2

- [X] T024 [US2] 执行 `pytest tests/facade/test_api_snapshot.py --update-api-snapshot` **生成并入库** `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`（当前为 US1 的 3 个符号；UTF-8 / LF / 末行换行），**人工 review diff 后**提交
- [X] T025 [US2] 在 `tests/facade/test_facade_gates.py` 落**门禁 G16**（快照逐字节比对 + 可复现 + 更新入口默认不生效）并**落其自检**（故意改坏 ⇒ 断言门禁确实报出）

**Checkpoint**：US2 可独立验收 —— 改任一参数名或注解 ⇒ 快照比对**失败并输出 diff**；两次生成逐字节相同

---

## Phase 5: User Story 3 - 上层开发者有单一可信入口 (Priority: P3)

**Goal**：门面**一次性**提供全部 7 个符号（`StateGraph` / `START` / `END` / `Command` / `Send` /
`interrupt` / `RunConfig`），上层不必在多个模块间拼凑。

**Independent Test**：门面导出面与 `contracts/facade-api.md` §0 **集合相等**（7 个，多 / 少都失败）；
`harness/demo/graph_core.py` 的**导入段成功**（脚本**不**以退出码 2 结束）。

### Tests for User Story 3 ⚠️（先写、先失败）

- [X] T026 [P] [US3] 在 `tests/facade/test_facade.py` 写**导出面集合相等**断言：`set(freegraph.graph.__all__) ==`（`contracts/facade-api.md` §0 解析出的 7 个）**且**门面模块内公开名集合 `==` 同一集合（**启用 G15 的集合相等段** —— SC-003）**并落其自检**（故意从门面**删掉一个导出符号** ⇒ 断言集合相等段**确实报出「漏导出」**——子集段抓不到这一类；`contracts/architecture-gates.md` §2 要求每条新增门禁有自检，G15 的**两段各一条**：子集段在 T009）
- [X] T027 [US3] 在 `tests/facade/test_facade.py` 写两组断言：**转出对象同一性**（`freegraph.graph.Command is freegraph.contracts.Command` 且 `RunConfig` 同理 ⇒ **True**，同一对象非副本 / 非子类 —— FR-004）＋ **`Send`**（构造成功；`Send("w", {...})` 与 `Send(node="w", arg={...})` **两种形态都合法**；改其属性**失败**；**不可哈希**（`hash(Send(...))` 抛 `TypeError`）—— SC-017 / Q7 / **FR-005 ① · 裁定 11**：frozen dataclass 默认**仍会**生成 `__hash__` ⇒ 「不可哈希」必须**显式** `__hash__ = None`）；依赖 T026（同一文件）
- [X] T028 [US3] 在 `tests/facade/test_facade.py` 写两组断言：**`interrupt`**（调用抛 `NotImplementedError` 且消息匹配 `interrupt 尚未接线（由 B10F1 交付）`；位置与关键字两种调用形态同分支）＋ **验收脚本导入段**（子进程执行 `python harness/demo/graph_core.py`，断言退出码 **≠ 2**；退出码 1 = 用例未转绿，是 M0 的**预期状态** —— SC-011；**并同样断言** `harness/demo/acceptance.py` 的 A1 前置自检**导入段**成功（退出码 ≠ 2）—— 它与 `graph_core.py` 同为既有消费者、独立锁定同样的 7 个名字）；依赖 T027（同一文件）

### Implementation for User Story 3

- [X] T029 [US3] 在 `src/freegraph/_primitives.py` 实现两个外壳：① `Send` = `@dataclass(frozen=True, slots=True)`，字段 `node: str` / `arg: Any`，**刻意不用 `kw_only=True`**（`graph_core.py` 与上游都用位置参数 —— D-13）＋ 类体显式 `__hash__ = None`（不可哈希）；② `interrupt(value: Any) -> Any` = 模块级函数，函数体**只**抛 `NotImplementedError`（消息点名 B10F1）；① 的「显式 `__hash__ = None`」是 **FR-005 ① · 裁定 11** 的硬要求（`slots=True` 下亦成立，实测 `Send.__dict__["__hash__"] is None`）
- [X] T030 [US3] 在 `src/freegraph/graph.py` 补 `from .contracts import Command, RunConfig` 与 `from ._primitives import Send, interrupt`，把 `__all__` 设为**恰好 7 个**（`StateGraph` / `START` / `END` / `Command` / `Send` / `interrupt` / `RunConfig`），并按 `contracts/facade-api.md` §0 的**分组顺序**书写
- [X] T031 [US3] **重新生成快照**：执行 `pytest tests/facade/test_api_snapshot.py --update-api-snapshot` ⇒ 快照含 **7 个**顶级条目，**人工 review diff 后**提交（走 `contracts/snapshot-format.md` §6 的「合法变更」流程）
- [X] T032 [US3] 在 `README.md` 的「## API 兼容矩阵」章节**追加 5 行**（`StateGraph` / `START` / `END` / `Send` / `interrupt`）：**保持 4 列不变**、**既有 18 行逐字不动**、等价程度与「差异说明」文案**逐字**按 `research.md` **D-17** 的表格（上游来源行号写在「差异说明」单元格末尾，标注核实环境 `langgraph 1.2.11`）；**章节末尾的版本口径注已于 2026-11-07 预先更新**为「**表内新增行**（B2F1 的 10 个 **+ B2F2 的 5 个**）」—— 本任务**只需确认、无需再改**；**注意**：该括注已提前引用本 feature 的 5 行 ⇒ **追加 5 行之前 README 暂时自相矛盾**，追加后即闭合
- [X] T033 [US3] 在 `tests/facade/test_facade_gates.py` 落**门禁 G19**（兼容矩阵覆盖门面 7 个符号：各恰有一行 · 等价程度逐符号一致 · 新增 5 行含上游来源行号 · 既有 18 行逐字未改）并**落其自检**

**Checkpoint**：US3 可独立验收 —— 7 个符号一次性取齐；`graph_core.py` 导入段成功（退出码 ≠ 2）

---

## Phase 6: User Story 4 - 顶层包保持惰性 (Priority: P4)

**Goal**：`import freegraph` **不连带加载**任何子模块（门面 / 契约层 / 运行时 / 持久化 / 可观测），
门面**不横向依赖** L4 / L5。

**Independent Test**：子进程 `import freegraph` 后 `sys.modules` 中 `freegraph.*` 的子模块数 **== 0**。

### Tests for User Story 4 ⚠️（先写、先失败）

- [X] T034 [P] [US4] 在 `tests/facade/test_facade_gates.py` 落**门禁 G18**（**两组断言**）：① 子进程 `import freegraph.graph` ⇒ **不含**持久化层 / 可观测层子模块（**== 0**）；② 子进程 `from freegraph.graph import StateGraph` ⇒ `freegraph.contracts` **被加载**（**反向断言**：门面**可以**依赖 L1 契约层）；**并落其自检**（① 临时造一处 `from freegraph.persistence import X` ⇒ 断言模块加载面确实报出；② 临时改门面使其连带加载 L4 ⇒ 断言确实报出）。**注意**：`import freegraph` ⇒ `freegraph.*` 子模块数 == 0 这一条**由既有门禁 G1 直接产出**（其实现口径**已是** `freegraph.*` 全量），G18 §1-② 已声明「本条不另写断言」—— **本任务不重复实现**
- [X] T035 [US4] 在 `tests/facade/test_facade_gates.py` 加「`freegraph/__init__.py` **未导入门面**」的**源码文本断言**（扫 `src/freegraph/__init__.py` 不含对 `graph` 的导入语句）＋自检（**不得**真的改 `__init__.py`）；依赖 T034（同一文件）
- [X] T036 [US4] 复核既有门禁 **G7**（契约层 `__all__` 仍恰 18 个、**不含** `Send` / `interrupt`）与 **G12**（唯一权威扫描 `**/public-api.md` —— 本 feature **不产出**该文件名）仍绿（SC-015）

**Checkpoint**：US4 可独立验收 —— 惰性断言全绿；契约层 18 符号面未受影响

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**：跨故事的文档、证据与验收收尾。

- [X] T037 [P] 回填**人工验证记录** `harness/verification/B2F2/manual-verification.md`：五段式（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）；第 3 节 MUST 粘贴**真实输出**（替换「期望输出（非实测）」占位）；未实跑的平台 / 版本 MUST 记入第 5 节（**MUST NOT 伪造输出**）；逐条核对 **A1 / A2 / A3**（SC-013）；**并补第 4 节的「导出面 7 符号 × 来源」覆盖表**（每符号一行，来源列填 FR-015 要求的出处；**未列出的符号数 == 0**）—— 这是 SC-013「无来源项数 == 0」的**载体**
- [X] T038 [P] 在 `specs/b2f1-contracts-protocols/contracts/public-api.md` 的 **§5 移交表加一行**指向本 feature 的快照（FR-010 ④）—— **只加一行**，其余内容**逐字不动**
- [X] T039 [P] 隔离环境**全量**验收：**复用 T018 建的同一个 venv**（不新建）→ `pip install pytest` → 跑 `pytest -q` **全绿**；并复跑 `python -c "from freegraph.graph import StateGraph, START, END"` 退出码 0；把实测输出记入 `harness/verification/B2F2/manual-verification.md` 第 3 节
- [X] T040 实测**性能预算**：**复用 T018 建的同一个 venv**（**基准解释器 = CPython 3.11.x**；本机若无 3.11，MUST 在人工验证记录第 5 节登记为遗留问题）⇒ **先预热一次** import，再取**三次**的**最小值**：`python -c "import freegraph.graph" && python -c "import time; t=time.perf_counter(); import freegraph.graph; print(time.perf_counter()-t)"` ⇒ 墙钟 **< 120 ms**（FR-019 / SC-018）；**同时**按同一口径实测基线 `import freegraph.contracts` ⇒ 把**实测值 + 基线值 + 测量环境（OS / CPU / Python 版本）**记入 `harness/verification/B2F2/manual-verification.md` 第 3 节。**唯一计时口径**（FR-019 / SC-018）：以 `time.perf_counter()` 在 import 语句**前后**取差、**不含解释器自身启动**、**暖机 best-of-3**、**基准 CPython 3.11.x**
- [X] T041 复核**红线**：`THIRD_PARTY_NOTICES` **未变**（零新增第三方依赖）· `pyproject.toml` **未变**（`dependencies = []` / `requires-python = ">=3.11"`）· `git diff --exit-code -- harness/demo/target.py` 退出码 **0**（只读基准未被修改 —— FR-016）
- [X] T042 走查 `quickstart.md` 的 **场景 A–K 共 11 个**，逐条记录实际结果到人工验证记录第 2 / 3 节
- [X] T043 复核**门禁自检齐全**：`tests/facade/test_facade_gates.py` 中 G14 / G15 / G16 / G17 / G18 / G19 / G20 **各有一条自检**（**7 条**；其中 **G15 的两段各一条** —— 子集段在 T009、集合相等段在 T026）；并确认既有门禁实现**零改动**（`git diff --stat -- tests/contracts/ src/freegraph/contracts/` 输出为空 —— 顶层包惰性的 `freegraph.*` 全量口径**本已**在既有 G1 实现中，**无须扩展**）；**SC-016 的「未越界」断言已随 T015 落地**，本任务只复核不新增
  > **⚠️ 实测偏离（已登记）**：门禁自检**齐全且多于下限**——`tests/facade/test_facade_gates.py` 里
  > 共 **12 条**自检（G14 两条 · G15 两段各一条 · G16 一条 · G17 两条 · G18 三条 · G19 一条 · G20 一条），
  > 下限是 **8 条**（G15 两段各一条）✅；`tests/facade/test_facade.py` 另有 **1 条** G15 集合相等段自检
  > （T026 要求落在此处）⇒ **合计 13 条**。
  > 「既有门禁实现**零改动**」这一条**未成立**：`tests/contracts/test_architecture.py` 的
  > **G8 判据按其声明范围收敛**（原因与影响见 T012 的注记与人工验证记录 §5 遗留 #1）。
  > `src/freegraph/contracts/**` 与 G1 / G2 / G3 / G4 / G5 / G6 / G7 / G9…G13 的实现**均未改动** ✅。
- [X] T044 复核**规格质量清单** `specs/b2f2-public-api-facade/checklists/requirements.md` 的 **16 项**仍全部通过；若实现暴露了需求缺口，MUST 回填 spec 并同步 plan / contracts（**MUST NOT** 就地改型）
- [X] T045 回填**实现后的行数实测**到 `plan.md` 的「Scale/Scope」小节（实现 / 测试 / 文档三行数 + 与立项书「560 行」估算的偏差）—— **登记不改立项书**（沿用 B2F1 的口径）
- [X] T046 产出 `harness/verification/B2F2/acceptance.py`（**逐 feature 可运行验收脚本** · 与 B1F1 / B2F1 同口径 —— `harness/verification/README.md` 的目录约定把 `acceptance.py` 与 `manual-verification.md` 列为**固定文件名**）：把本 feature 的验收判据落成**可判定的断言**（**A1 / A2 / A3** 三项判据 + SC-001…SC-018 的关键项）⇒ **两态运行**（环境**已安装** freegraph ⇒ 测**发行产物**；**未安装** ⇒ 自动把 `<repo>/src` 插入 `sys.path` 测**源码树**，且「依赖闭包为空集」那条判据标「◌ 环境未就绪」**不判失败**）· 退出码 **0 = PASS / 1 = FAIL / 2 = 环境未就绪** · `--record out.md` 产出**五段式**（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）片段供 T037 回填 · `--require-installed` 可要求当前环境已安装 freegraph；**零第三方依赖**（只 import Python 标准库 + 被验收的 freegraph 本身）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup（Phase 1）**：无依赖 —— 可立即开始
- **Foundational（Phase 2）**：依赖 Setup —— **阻塞全部用户故事**
- **User Stories（Phase 3–6）**：均依赖 Foundational；之后可**并行**推进（若人手允许）或按 **P1 → P2 → P3 → P4** 顺序推进
- **Polish（Phase 7）**：依赖全部目标用户故事完成

### User Story Dependencies

- **User Story 1（P1）**：Foundational 之后即可开始 —— **不依赖**其他故事
- **User Story 2（P2）**：Foundational + **US1** 之后开始（快照要记录**已存在**的门面形状）
- **User Story 3（P3）**：Foundational + US1 之后开始；**启用** G15 的集合相等段；**重新生成**快照（依赖 US2 的渲染器）
- **User Story 4（P4）**：Foundational 之后即可开始（只依赖子进程断言与三个模块存在 —— 二者由 Foundational 提供）

### Within Each User Story

- 测试**先写**并**先失败**，再写实现
- 模块骨架 → 实现体 → 门禁断言
- 生成物（快照）必须经**人工 review diff** 后提交
- 故事完成后再进入下一优先级

### Parallel Opportunities

- Phase 1 的 T001 / T002 / T003 全部 `[P]`（三个不同文件）；T004 与 T001 **同文件** ⇒ 串行
- Phase 2 的 T005 / T006 / T007 **三路并行**（三个不同模块）；T008–T011 **同文件** ⇒ 串行
- 每个故事内**首个**测试任务 `[P]`（新建文件），同文件的后续测试任务**不标** `[P]`
- **US2 与 US3 的部分工作可并行**：US3 的 `Send` / `interrupt` 实现（T029）与 US2 的快照工具（T019 / T020）分处不同文件 ⇒ 可并行；**但 T031（重新生成快照）必须在 T030 之后**
- **US4 与 US2 / US3 可并行**（不同断言面、不同文件区段）

---

## Parallel Example: User Story 1

```bash
# 先写测试（新建文件 ⇒ 可与别的故事并行）
Task: "T013 在 tests/facade/test_facade.py 写 import 冒烟 + 常量取值两组断言"
# 同一文件的后续断言串行追加
Task: "T014 在 tests/facade/test_facade.py 写导出面子集 + 构造语义两组断言"
Task: "T015 在 tests/facade/test_facade.py 写未接线异常断言"
# 实现（依赖测试已失败）
Task: "T016 在 src/freegraph/_stategraph.py 实现 StateGraph 外壳"
Task: "T017 在 src/freegraph/graph.py 落地 START / END 与 StateGraph 导出"
```

```bash
# Phase 2 的模块骨架三路并行
Task: "T005 创建 src/freegraph/graph.py"
Task: "T006 创建 src/freegraph/_stategraph.py"
Task: "T007 创建 src/freegraph/_primitives.py"
```

---

## Implementation Strategy

### MVP First（User Story 1 only）

1. 完成 Phase 1：Setup（测试脚手架 + 门禁辅助）
2. 完成 Phase 2：Foundational（三个模块骨架 + G14 / G15 子集段 / G17）
3. 完成 Phase 3：User Story 1
4. **停下并验证**：隔离环境 `from freegraph.graph import StateGraph, START, END` 退出码 0
5. 此时**可演示**：验收基准脚本的 import 段已成立；`StateGraph` 仍不可用（**预期**）

> **MVP 的边界**：US1 完成时门面导出 **3** 个符号；**恰 7 个**是 US3 之后的终态。
> **MUST NOT** 在 US1 阶段塞入占位导出去「凑」7 个。

### Incremental Delivery

1. Setup + Foundational → 基础就位（三条门禁常驻）
2. US1 → 独立验证 → 可演示（**MVP**：import 成立）
3. US2 → 独立验证（改签名即失败）→ 形状被钉住
4. US3 → 独立验证（7 符号齐备 + `graph_core.py` 导入段成立）
5. US4 → 独立验证（顶层包惰性 + 门面不横依赖 L4 / L5）
6. Polish → 人工记录 + 文档 + 红线复核

### Parallel Team Strategy

1. 团队共同完成 Setup + Foundational
2. 之后可并行：
   - 开发 A：US2（快照工具 + 比对 + 自检）
   - 开发 B：US3（`Send` / `interrupt` + 导出面补齐 + 矩阵行）
   - 开发 C：US4（惰性与加载面断言）
   - 开发 D：US1（门面 + `StateGraph` 外壳）—— **最先可交付**
3. **T031（重新生成快照）** 必须在 US2 的渲染器与 US3 的导出面补齐**都**完成后执行（唯一的跨故事串行点）

---

## 附录 · 任务 ↔ spec 追溯表

> **依据**：宪法原则 VI ——「tasks **MUST** 可逐条勾选、**可追溯到 spec 条目**」。
> 本表把 **46 条任务**逐条映射到 `spec.md` 的 **FR-001…FR-019** / **SC-001…SC-018**
> 与验收判据 **A1–A3**；标「—」者属**工程设施 / 交付收尾**，不直接产出新判据
> （但仍服务于既有 SC）。
> **本次补全（2026-11-07 分析轮 · C-1）**：此前 30 条任务**无** FR/SC 引用。

| 任务 | 对应 FR | 对应 SC | 说明 |
|---|---|---|---|
| T001 | — | — | 测试脚手架（`conftest.py`）· 工程设施，支撑 SC-005 / SC-009 / SC-012 |
| T002 | FR-002 / FR-014 | SC-009 | 门禁共享辅助（`_gatesupport.py`）· D-22 两档扫描 |
| T003 | — | — | `tests/facade/__init__.py` · 工程设施 |
| T004 | FR-011 | SC-005 | `--update-api-snapshot` 开关（**默认关闭**） |
| T005 | FR-001 / FR-006 | SC-004 | 门面骨架（**零实现体**） |
| T006 | FR-006 / FR-018 | — | `StateGraph` 外壳骨架 |
| T007 | FR-005 / FR-006 | — | `Send` / `interrupt` 外壳骨架 |
| T008 | FR-006 | SC-004 | 门禁 **G14**（零实现体 · AST） |
| T009 | FR-002 | SC-003 | 门禁 **G15 子集段** |
| T010 | FR-014 | SC-009 | 门禁 **G17**（依赖卫生 · **两档制**） |
| T011 | FR-017 | SC-014 | 门禁 **G20**（署名头 · 10 个新文件） |
| T012 | — | SC-015 | 复核既有门禁 G1–G13 · 质量门禁第 1 项 |
| T013 | FR-003 | SC-001 / SC-002 | import 冒烟 + 常量取值 |
| T014 | FR-002 / FR-007 | SC-010 | 导面子集 + 构造语义 |
| T015 | FR-009 / FR-018 | SC-011 / SC-016 | 未接线异常 + **未越界**（SC-016 前移至此） |
| T016 | FR-007 / FR-008 | SC-010 | `StateGraph` 外壳实现（构造 + 四方法未接线） |
| T017 | FR-001 / FR-002 / FR-003 | SC-001 / SC-002 | `START` / `END` + `StateGraph` 导出 |
| T018 | — | SC-001 | 隔离环境验收（**建 venv**，T039 / T040 复用）· A1 |
| T019 | FR-010 | SC-006 | `normalize_annotation`（N-1…N-6） |
| T020 | FR-010 | SC-006 | `render_api_snapshot`（纯函数 · **D-21-1…D-21-4**） |
| T021 | FR-010 / FR-011 | SC-005 / SC-006 | 快照逐字节比对 + 可复现 |
| T022 | FR-011 | SC-005 | 更新入口默认不生效 + **自检三例**（D-23 真实比对路径） |
| T023 | FR-010 | SC-006 | 快照文本合规（UTF-8 / LF / 末行换行 / 无非确定内容） |
| T024 | FR-010 | SC-005 | 生成并入库快照 · A2 |
| T025 | FR-010 / FR-011 | SC-005 | 门禁 **G16**（快照比对） |
| T026 | FR-002 | SC-003 | 导出面**集合相等**（启用 G15 相等段） |
| T027 | FR-004 / FR-005 | SC-017 | 转出对象同一性 + `Send`（不可变 / **不可哈希** / 关键字形态） |
| T028 | FR-005 / FR-009 | SC-011 | `interrupt` 未接线 + 验收脚本导入段（退出码 ≠ 2） |
| T029 | FR-005 | — | `Send`（frozen dataclass · 显式 `__hash__ = None`）· `interrupt` 外壳 |
| T030 | FR-002 / FR-004 / FR-005 | SC-003 | 补齐 7 符号导出面 |
| T031 | FR-010 | SC-005 | 重新生成快照（7 个顶级条目） |
| T032 | FR-012 | SC-012 | `README.md` 兼容矩阵**追加 5 行** + 同步版本口径注 |
| T033 | FR-012 | SC-012 | 门禁 **G19**（兼容矩阵覆盖门面 7 符号） |
| T034 | FR-013 / FR-014 | SC-007 / SC-008 | 门禁 **G18**（模块加载面） |
| T035 | FR-013 | SC-007 | `__init__.py` 未导入门面（源码文本断言） |
| T036 | FR-005 | SC-015 | 复核既有门禁 **G7** / **G12** |
| T037 | FR-015 | SC-013 | 人工验证记录（五段式 + **来源覆盖表**） |
| T038 | FR-010 | — | B2F1 `public-api.md` §5 移交表**加一行** |
| T039 | — | SC-001 / SC-015 | 隔离环境**全量**验收（复用 T018 的 venv） |
| T040 | FR-019 | SC-018 | **导入开销预算**实测（唯一计时口径） |
| T041 | FR-016 / FR-017 | SC-014 | 红线复核（`THIRD_PARTY_NOTICES` / `pyproject.toml` / `target.py`） |
| T042 | FR-015 | SC-013 | 走查 `quickstart.md` 场景 A–K |
| T043 | — | SC-016 | 复核门禁自检齐全（7 条）· 质量门禁第 4 项 |
| T044 | — | — | 复核规格质量清单 16 项 · 质量门禁第 1 项（规格门禁） |
| T045 | — | — | 回填实现后行数实测（登记，不改立项书） |
| T046 | FR-015 | SC-013 | 逐 feature 验收脚本 `harness/verification/B2F2/acceptance.py`（与 B1F1 / B2F1 同口径 · 五段式 `--record`） |

> **口径说明**：① 一条任务可对应**多条** FR / SC（跨故事任务常见）；
> ② 「工程设施」类任务（T001 / T002 / T003 / T045）不产出判据，其存在是为了让
> **判据类**任务可执行；③ T040 对应的 **FR-019 / SC-018** 是 2026-11-07 分析轮
> 新增的**导入开销预算**（spec 裁定 12）。

---

## Notes

- `[P]` = 不同文件、无未完成依赖；**同一文件内的后续任务不标** `[P]`
- `[Story]` 标签映射到 spec 的用户故事（US1…US4），便于追溯
- **本 feature 零行为**：四个方法与 `interrupt` **必须**抛 `NotImplementedError` —— 实现者**不得**「顺手」把行为写进来（属 B6F1 / B7F2 / B10F1 / B11F1）
- **冻结面只引用不复制**：符号清单看 `contracts/facade-api.md` §0 · 签名看 `contracts/public-api-snapshot.txt`
  与 `data-model.md` §2 · 快照格式看 `contracts/snapshot-format.md` · 门禁看 `contracts/architecture-gates.md`
- 每个任务完成后**单独提交**；每个 Checkpoint 处停下验证
- 避免：模糊任务、同文件冲突、跨故事依赖破坏独立性
- **`harness/demo/target.py` 是只读基准** —— 任何任务都**不得**修改它
