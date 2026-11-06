---

description: "B2F1 · 4 类可插拔协议（NodeFunc/Checkpointer/TraceSink/Store）+ CompiledGraph 协议（合计 5 个协议）+ 5 个纯数据类 —— 任务清单"
---

# Tasks: 4 类可插拔协议 + `CompiledGraph` 协议 + 5 个纯数据类

**Input**: Design documents from `/specs/b2f1-contracts-protocols/`

**Prerequisites**: plan.md（必读）、spec.md（必读 · 含 **13** 条澄清决策 + FR-017）、research.md（**20** 条决策 D-01…D-20 + 13 条挂起项交接表）、data-model.md（5 协议 + 5 数据类 + 不变式）、contracts/public-api.md（**唯一权威** · 18 符号 + C1–C27 对照表）、contracts/architecture-gates.md（**13** 条门禁 G1–G13）、quickstart.md（验收指南）

**Tests**: **包含**。spec 的 SC-001…SC-021 全部要求「可自动判定」的断言，feature 提示词 §10 亦把「协议结构化子类型自测 fixture」列为交付物 ⇒ 本清单按 **TDD 顺序**组织：每个故事的**测试任务排在实现任务之前**，且测试**必须先失败**。

**Organization**: 任务按用户故事分组，每个故事可独立实现、独立测试、独立验收。

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可与同阶段其他任务并行（不同文件、无依赖）
- **[Story]**：所属用户故事（US1…US5）
- 描述中**必须含确切文件路径**与**具体取值**（签名、字段清单、方法集、常量），以免实现时二次决策

## Path Conventions

- 源码：`src/freegraph/contracts/`（契约层 · 本 feature 新增 `protocols.py` / `graph.py` / `trace.py`，扩充 `__init__.py`；`types.py` / `errors.py` **不动**）
- 测试：`tests/contracts/`（本 feature 新增 `test_protocols.py` / `test_graph.py` / `test_span.py` / `fixtures/`，扩充 `test_architecture.py`）
- 冻结面文档：`specs/b2f1-contracts-protocols/contracts/public-api.md`（**唯一权威**）、`specs/b2f1-contracts-protocols/contracts/architecture-gates.md`
- 人工记录：`harness/verification/B2F1/manual-verification.md`
- **改动边界**：**可改** —— `README.md` 的「## API 兼容矩阵」章节**仅限本层 10 行**（T033 写入 / T054 复核；**既有 8 行逐字不动**），该章节的「证据来源」小节**可追加**本层来源行号（分行标注版本）；`harness/verification/README.md` 的「当前已有记录」表**仅可登记 B2F1 行**（T037）
- **不得改动**：`pyproject.toml`（依赖白名单仍 `dependencies = []`）、`THIRD_PARTY_NOTICES`（本 feature 零新增第三方依赖 ⇒ 无需新增登记，补全归 B24F1）、`src/freegraph/__init__.py`（顶层包惰性）、`src/freegraph/contracts/types.py` 与 `errors.py`（B1F1 已冻结）

---

## 阶段 1: Setup（共享基础设施）

**Purpose**: 建立本 feature 的目录骨架与测试基础设施（B1F1 已建 `tests/contracts/` 与 `conftest.py`，本 feature **复用**、只新增夹具目录与三个新模块的骨架）。

- [X] T001 [P] 创建 `tests/contracts/fixtures/` 目录与 `tests/contracts/fixtures/__init__.py`：文件**只含**署名头 `# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph`（第 1 行）+ 模块 docstring（docstring MUST 是首个语句）+ 一行 `__all__ = []` 占位；**不含任何实现**。作用：使 `from fixtures.external_impl import ...` 在 `tests/contracts/`（无 `__init__.py` ⇒ pytest 把该目录插入 `sys.path`）下可解析
- [X] T002 [P] 复核 `src/freegraph/contracts/__init__.py` 现状（既有 **8** 个符号：`StateDict` / `Command` / `StateSnapshot` / `RunConfig` / `FreegraphError` / `InvalidUpdateError` / `GraphRecursionError` / `GraphInterrupt`）：记录既有 `__all__` 的**顺序**，本 feature 的追加位一律**接在既有 8 项之后**，既有 8 项的顺序与拼写**一个字都不许改**
- [X] T003 [P] 确认 `src/freegraph/py.typed` 存在且**内容为空**（PEP 561：顶层一个标记即覆盖全部子包）——**不得**新建 `src/freegraph/contracts/py.typed`
- [X] T004 [P] 复核 `tests/contracts/conftest.py`（B1F1 已建）暴露的 `repo_root` / `src_dir` / `contracts_dir` 三个 fixture 与 `FREEGRAPH_TEST_INSTALLED=1` 开关：本 feature **复用、不改**；新测试一律用 `contracts_dir.parent / "fixtures"` 定位夹具目录，**不得**硬编码绝对路径
- [X] T005 [P] 创建三个新模块的**骨架**（各文件**只含**署名头 + 模块 docstring，**不含任何实现**）：`src/freegraph/contracts/protocols.py`（docstring 说明「5 个协议：NodeFunc / Checkpointer / TraceSink / Store / CompiledGraph；纯抽象、无默认实现、无继承链」）、`src/freegraph/contracts/graph.py`（docstring 说明「图结构自有类型 Graph / Node / Edge；**不复用** `langchain_core.runnables.graph`；与 B2F2 的 `freegraph/graph.py`（公开门面）路径不同、互不冲突」）、`src/freegraph/contracts/trace.py`（docstring 说明「可观测数据面 Span / TraceQuery；C27 的请求结构」）

---

## 阶段 2: Foundational（阻塞前置）

**Purpose**: 把 B1F1 的门禁基线**扩展**到本 feature 的新增面（多一个文件、多一个测试目录），并建立「公开符号清单 → 门禁期望值」的单一来源机制。**本 feature 的所有用户故事都依赖这些机制**。

- [X] T006 扩展 `tests/contracts/test_architecture.py` 的 **G2** 扫描（**两档范围** · B2F1 第二轮复核裁定 2026-11-06）：① **内部 import 判定**覆盖 `src/freegraph/contracts/**` **+ `tests/contracts/**`**（含 `fixtures/`）——凡指向 `freegraph` **顶层**或 `freegraph.*` 中**前缀不是** `freegraph.contracts` 的 import 即违规（`from freegraph.contracts import ...` 与 `from freegraph.contracts.protocols import ...` **合法**）；② **第三方 import 判定**覆盖 `src/freegraph/contracts/**` **+ `tests/contracts/fixtures/**`**（**仅夹具目录**）——黑名单含 `langchain` / `langchain-core` / `langgraph` / `langsmith` / `pydantic` / `typing_extensions` / 任何非标准库顶层包；**其余 `tests/contracts/**` 的测试文件豁免第三方判定**（`pytest` 是**开发期工具**，测试基础设施须用它驱动门禁）——MUST NOT 因 `import pytest` 报违规。**G4 的扫描范围同步扩到 `tests/contracts/fixtures/**`**（夹具不得读环境变量 / 不得 import 网络库）；**其余测试文件豁免 G4**（`test_architecture.py` 须用 `subprocess` / `os.environ` 驱动子进程门禁）；**本任务 MUST 同时完成既有 `TestGateSelfCheck` 中 3 个 G2 自检用例的「档位迁移」**（见 T056 ①）——`scan_imports` 拆成**两档**后，既有自检若仍走「一次扫描覆盖两档」的入口，则会**假绿**（抓不到某一档）或**假红**（把合法豁免当成违规）⇒ 迁移**不做完，G2 的自检即失效**
- [X] T007 扩展 `tests/contracts/test_architecture.py` 的 **G5** 署名头扫描：把本 feature 新增的 `.py`（`src/freegraph/contracts/protocols.py` / `graph.py` / `trace.py` / `tests/contracts/fixtures/__init__.py` / `fixtures/external_impl.py` / `tests/contracts/test_protocols.py` / `test_graph.py` / `test_span.py`）纳入**逐字首行相等**断言，并断言其**模块 docstring 是首个语句**；**并追加断言** `tests/contracts/test_architecture.py` 的**模块 docstring 首句已含「十三条架构门禁」**（与 `contracts/architecture-gates.md` 的 G1–G13 一致）——该文件现状写的是「**八条**架构门禁」（B1F1 遗留），本 feature MUST NOT 留下过时的门禁面声明（该断言在本任务完成后 MUST 通过；docstring 的重写落在 T008 ④）
- [X] T008 在 `tests/contracts/test_architecture.py` 增加一个**清单解析辅助函数**（供 G7 / G8 使用）：读取 `specs/b2f1-contracts-protocols/contracts/public-api.md` 的 §0 代码块，**规则写死为**：① 定位**唯一**以 `from freegraph.contracts import (` 起始、以 `)` 结束 的代码块（该文件另有代码块 ⇒ MUST 锚定本块，MUST NOT 取全文第一个代码块），并**丢弃这两行锚点本身**（它们不是符号）；② 块内每行先 `strip()`，**跳过空行**与**以 `#` 开头的行**（注释行不是符号）；③ 余下每行按 `,` 切分取**首段**再 `strip()`，并**断言**其匹配 `^[A-Za-z_][A-Za-z0-9_]*$`（不匹配即报可读错误并点名文件路径与期望形状，MUST NOT 静默跳过）；④ 抽出的符号名集合 MUST 为 **18** 个（否则报可读错误，MUST NOT 静默返回空集）；**并 MUST 按 §0 的分组注释把结果切分为「B1F1 既有 8 个」与「B2F1 新增 10 个」两段**（分组注释行含「B1F1 已冻结的 8 个」/「B2F1 新增的 10 个」）——供 G7 的「新增集合」断言与 G8 的「行内来源行号只对新增行成立」判定使用；**并断言「新增集合恰为 FR-012 所列 10 个」（`NodeFunc` / `Checkpointer` / `TraceSink` / `Store` / `CompiledGraph` / `Graph` / `Node` / `Edge` / `Span` / `TraceQuery`）、**既有集合恰为 8 个**——多一个 / 少一个都判失败（**SC-017「新增恰为 10 个」的机械落点**）；⑤ **并在本任务内一并改造既有 G7**（B2F1 第二轮复核裁定 · 2026-11-06）——既有断言 `set(contracts.__all__) == PUBLIC_SYMBOLS`（`tests/contracts/test_architecture.py:370`，硬编码 **8** 个）自 **T014 起必然失败**（`__all__` 变 11 个），而 US4 的 Checkpoint 要求 `test_architecture.py` 全绿 ⇒ **G7 MUST 在本阶段就改造**，且**拆成两段**以保证全程可绿：<br>① **子集断言（始终启用 · 本任务落地）**——`set(contracts.__all__) ⊆ §0 解析出的 18 个`（抓住「偷偷多导出一个」；构造期 `__all__` 尚未齐全时恒成立）；<br>② **集合相等断言（全部 18 个导出后启用 · 在 T040 落地）**——`set(contracts.__all__) == §0 解析出的 18 个`（抓住「漏导出」）；<br>③ 本任务同时**删除** `PUBLIC_SYMBOLS` 硬编码常量、**清理**陈旧注释与陈旧命名（`:16` / `:43` / `:361` / `:364` / `:771` 的「恰 8 个」/「那 8 个名字」/「契约层的 8 个公开符号」→「恰 18 个（自 §0 解析）」；测试方法名 `test_all_equals_exactly_eight_symbols` → `test_all_equals_public_symbols`；`TestPublicSymbolSurface` 的类 docstring 同步）与 `:380` 的「（归 B2F1）」→ 改为「归 **v2**（B11F1 / B10F1）；本 feature **不导出**」；**删除常量 MUST 在本任务 ⑥（G8 改造）完成之后执行**——否则 `:779` 会因常量已删而 `NameError`；**本文件模块 docstring 的「门禁总览」MUST 一并重写**（现状 `:5` 写「契约层的**八条架构门禁**（US3）」、`:7-21` 的 RST 表只列 G1–G8 且 `:16` 写「G7 公开符号面**恰为 8 个**」）⇒ 改为「**十三条架构门禁**（G1–G6 继承 B1F1 · **G7 / G8 修改** · **G9–G13 新增**）」、把 G9–G13 五行补进该表、门禁定义出处改为 `specs/b2f1-contracts-protocols/contracts/architecture-gates.md`（B1F1 的文件只含 G1–G9）——**MUST NOT** 留下「八条」或「恰为 8 个」的字样（该文件对外声明的门禁面 MUST 与 `architecture-gates.md` 一致）；④ `test_every_name_is_gettable` 改为遍历**当前 `__all__`**（`for name in contracts.__all__: assert hasattr(contracts, name)`）——既保住「`__all__` 里的名字确实绑定」的缺陷检出，又不在构造期误报；<br>⑤ **同时改造既有 G8**（`tests/contracts/test_architecture.py:770-779` 的 `test_compat_matrix_covers_every_public_symbol`）——原断言 `set(rows) == PUBLIC_SYMBOLS` 依赖本任务将删除的常量，且 T033 给 README 补 10 行后 18 ≠ 8 必然失败 ⇒ **G8 MUST 在本任务内改掉**（与 G7 同批，**不另开任务**），且**同样拆成两段**（否则 T008~T033 之间 README 尚未补入新增 10 行 ⇒ 门禁必红）：<br>**① 子集段（始终启用 · 本任务落地）**——期望值**从 `public-api.md` §0 解析**（复用本任务的解析函数，**不得**硬编码 18）后，对**矩阵中当前已存在的行**逐条判定：（a）每行的首列符号 ∈ §0 的 18 个（抓「清单外符号」）；（b）矩阵行数 ≤ 18（抓「重复 / 超量」）；（c）每行含「对应上游符号 / 等价程度 / 差异说明」**三列**（四列）；（d）**行内上游来源行号**只对「**有上游同名符号**的**新增 10 行**」成立——`Checkpointer` / `Store` / `CompiledGraph` / `Graph` / `Node` / `Edge` 须含 `路径:行号`，`NodeFunc` / `TraceSink` / `Span` / `TraceQuery` 须写「**无上游对应**（自由设计）」+ 契约条目号（C5 / C6、C23 / C24、C27）；**既有 8 行逐字不动**（其来源以矩阵章节的「证据来源」小节为准，**不**对其断言行内行号）——本段在 T033 之前只对既有的 8 行生效（新增 10 行尚未入矩阵 ⇒ 恒成立）；<br>**② 集合相等段（README 补入新增 10 行后启用 · 在 T033 落地）**——矩阵首列符号集合 == §0 解析出的 18 个（抓「漏写」）；**该段由 T033 在写入 README 之后启用**，与 G7 的集合相等段（在 T040 启用）**同构**
- [X] T009 **复核** **G9**（typing 构件上限 = 3.11）的 AST 扫描覆盖 `src/freegraph/contracts/protocols.py` / `graph.py` / `trace.py`（本 feature 用到的 `Protocol` / `runtime_checkable` / `dataclass` / `Mapping` / `Sequence` / `Iterator` **全部 ≤ 3.11**，MUST NOT 因此放宽门禁）——**注**：既有 `scan_runtime_baseline(src_dir / "freegraph")` 已以 `rglob("*.py")` **递归覆盖 `src/freegraph/**`**，故本任务实为**复核**（确认三个新模块落在扫描范围内且无违规），**MUST NOT** 重写扫描器
- [X] T059 在 `tests/contracts/test_architecture.py` 增加 **G10**（协议**纯抽象**）的 AST 断言：**协议类体内的方法体必须只有 `...`**（`ast.Expr` 包 `ast.Constant(Ellipsis)`；出现 `pass` / `raise NotImplementedError` / 赋值 / `return` 即失败）——扫描目标为 `src/freegraph/contracts/protocols.py` 中的协议类；**协议尚未落地时（构造期）扫描结果为空 ⇒ 判为通过**，协议类一旦出现即自动受检。**并带门禁自检**：在**临时目录**造一个含 `pass` 方法体的协议文件，断言扫描确实报出（自检须在临时目录内进行，不得污染仓库）。**本任务在 Foundational 落地的理由**：FR-007「协议 MUST 为纯抽象」是 **MUST 级**约束，而默认实现会让「只声明部分方法」的假实现**静默通过**结构化子类型判定——若等到 US5 末才落地门禁，T011–T039 写协议期间**无任何自动判据**（原 T042 的排期缺陷，B2F1 第四轮复核裁定）

**Checkpoint**: `python3 -m pytest tests/contracts -q` 全绿（此时新增断言只覆盖门禁**范围扩展**、**G7 的子集段**（T008 ②①）、**G8 的子集段**（T008 ⑤①）与 **G10**（T059）——G7 的**集合相等段**在全部 18 个符号导出后启用（见 T040），G8 的**集合相等段**在 README 补入本层 10 行后启用（见 T033）；既有「恰 8 个」的硬编码断言与 `PUBLIC_SYMBOLS` 常量已在本阶段拆除（**G8 改造先行、常量后删**），故不会出现「T014 一导出就红」）。

---

## 阶段 3: User Story 1 - freechain 只靠协议实现自己的持久化后端 (Priority: P1) 🎯 MVP

**Goal**: 交付**节点函数协议** `NodeFunc` 与**两个存储面协议** `Checkpointer`（检查点，6 方法）/ `Store`（长期存储，6 方法），使 freechain 只靠协议就能实现自己的持久化后端。

**Independent Test**: 实现一个**只声明协议方法**的假 checkpointer（不继承任何 freegraph 基类），静态类型检查接受其为 `Checkpointer` 实例、运行时结构化子类型判定为真；**缺任一方法**的变体判定为**假**。

### 测试（先写，先失败）

- [X] T010 [P] [US1] 写 `tests/contracts/test_protocols.py` 的 US1 部分（先写、**必须先失败**）：① `Checkpointer` 的方法集**集合恰为** 6 个——`get_tuple` / `list` / `put` / `put_writes` / `delete_thread` / `get_next_version`（**断言用集合相等**；**MUST NOT** 断言成员的**定义顺序**——`typing.Protocol` 的成员集合是 `set`（CPython 3.11 / 3.12 实测：`{'c','b','a'}`），顺序随 `PYTHONHASHSEED` 变化，按序断言必然 flaky）；② `Store` 的方法集**集合恰为** 6 个——`get` / `search` / `put` / `delete` / `list_namespaces` / `batch`（同 ①，**不判顺序**）；③ `NodeFunc` 只有 `__call__` 一个成员，其注解为 `(state: StateDict) -> StateDict \| Command \| None`；④ 三个协议均可做 `isinstance` 判定（`runtime_checkable` 生效）；⑤ 每个协议构造一个**缺任一方法**的实现 ⇒ 判定为**假**；⑥ **「协议方法体只有 `...`」的 AST 断言不在本任务实现**——统一落在 **G10**（**T059**，Foundational 阶段即已落地），避免同一判据两处实现漂移（对应序号⑥ 删除；G10 的扫描器在 T059 就位，协议类一旦出现即自动受检）

### 实现

- [X] T011 [US1] 在 `src/freegraph/contracts/protocols.py` 实现 `NodeFunc`：`@runtime_checkable class NodeFunc(Protocol)`，唯一成员 `def __call__(self, state: StateDict) -> StateDict | Command | None: ...`（方法体**只有** `...`）；docstring MUST 写明「入参为**稀疏**状态字典；返回**部分状态**字典 / **命令原语** / 空值」与「`isinstance` 对任意**可调用对象**恒为真（因其自带 `__call__`）——『合法节点函数』由**静态类型检查**判定」
- [X] T012 [US1] 在 `src/freegraph/contracts/protocols.py` 实现 `Checkpointer`：`@runtime_checkable class Checkpointer(Protocol)`，6 个方法**纯抽象**（方法体只有 `...`），**方法名与参数名逐字按 `data-model.md` §2.2 冻结**（`get_tuple(config: RunConfig)` / `list(config: RunConfig, …)` / `put(config: RunConfig, …)` / `put_writes(config: RunConfig, …)` / `delete_thread(thread_id: str)` / `get_next_version(…)`），**返回类型以 `Any` 占位**——**返回结构与载荷形状挂起 B14F1**（形状定死后期难改）；docstring 写明「**返回结构与载荷形状挂起 B14F1**」+ 三条**已冻结的最小约束**（① 方法集合恰为六个 ② 读写面 MUST 能承载**检查点标识** ③ 载荷 MUST 为**纯数据**、可 JSON 序列化）
- [X] T013 [US1] 在 `src/freegraph/contracts/protocols.py` 实现 `Store`：`@runtime_checkable class Store(Protocol)`，6 个方法**纯抽象**；**方法名与参数名逐字按 `data-model.md` §2.4 冻结**（`get(namespace, key)` / `search(namespace_prefix, …)` / `put(namespace, key, value)` / `delete(namespace, key)` / `list_namespaces(prefix, …)` / `batch(ops, …)`），**`namespace` 的载体类型以 `Any` 占位**；docstring 写明「命名空间 = **层级路径**（多段），键 = 字符串；**具体载体形态挂起 v2**」；docstring 另写明「取值 MUST 为**纯映射**；**v1 无实现**（契约 C20 仍冻结，实现后补 v2）」
- [X] T014 [US1] 在 `src/freegraph/contracts/__init__.py` **追加**再导出 `NodeFunc` / `Checkpointer` / `Store`：`from .protocols import Checkpointer, NodeFunc, Store` + `__all__` 追加这三个名字（**既有 8 项的顺序不动**——见 T002）
- [X] T015 [US1] 在 `tests/contracts/fixtures/external_impl.py` 实现假 `Checkpointer` 与假 `Store`（各 6 个方法齐备、方法体自洽：内存字典存储 + 版本号自增）：该文件**只**允许 `from freegraph.contracts import ...` 与标准库 import，**MUST NOT** import 任何 freegraph 内部模块或第三方包；**所有方法 MUST 写全类型注解**（**参数名 MUST 与协议逐字相同**：`config` / `thread_id` / `namespace` / `key` / `value` / `namespace_prefix` / `prefix` / `ops`；**未冻结部分（返回类型 / 载荷 / 命名空间载体）用 `Any` 占位**并与协议一致）——`mypy --strict` 的前提（SC-004 · B2F1 第二轮复核裁定 2026-11-06）
- [X] T016 [US1] 在 `tests/contracts/test_protocols.py` 补 US1 断言：夹具中 `Checkpointer` / `Store` 实例的 `isinstance` 判定为**真**、缺方法变体为**假**、方法集**集合相等**断言

**Checkpoint**: `python3 -m pytest tests/contracts/test_protocols.py -q` 全绿；`PYTHONPATH=src python3 -c "from freegraph.contracts import Checkpointer, NodeFunc, Store"` 成功。

---

## 阶段 4: User Story 2 - 上层注入自己的可观测接收端 (Priority: P2)

**Goal**: 交付**可观测接收端协议** `TraceSink`（3 方法）与 **span 类型** `Span`（11 字段），使上层能注入自己的接收端，把运行轨迹接到既有日志系统。

**Independent Test**: 实现一个假接收端收集 `on_span_start` / `on_span_end` 调用；静态类型检查与结构化子类型判定均通过；断言两次回调**按 `id` 配对**且**开始时的快照不被事后改写**。

### 测试（先写，先失败）

- [X] T017 [P] [US2] 写 `tests/contracts/test_span.py`（先写、**必须先失败**）：① `Span` 的**字段清单恰为 11 个**且名字逐字为 `id` / `name` / `attributes` / `parent` / `start_time` / `end_time` / `context` / `thread_id` / `run_id` / `node` / `checkpoint_id`；② `end_time` 缺省为 `None`；③ **必带四项**（`thread_id` / `run_id` / `node` / `checkpoint_id`）均可读；④ `attributes` / `context` 为**浅拷贝**（构造后改原 dict 不影响实例）；⑤ **不可变**（改字段抛 `FrozenInstanceError`）；⑥ **不可哈希**（`hash()` 抛 `TypeError`）；⑦ 字段级相等（同字段值相等、异值不等）；⑧ **100% 可 JSON 序列化**（`json.dumps(asdict(span))` 不抛错）；⑨ `TraceSink` 三方法判定为真、缺方法变体为假；⑩ **返回结构 = span 列表**的序列化断言（SC-011 的列表子句）：`json.dumps([asdict(s) for s in spans])` 不抛错

### 实现

- [X] T018 [US2] 在 `src/freegraph/contracts/trace.py` 实现 `Span`（本模块 **MUST NOT** import `protocols`——`protocols` 依赖本模块，反向 import 会造成循环导入）：`@dataclass(frozen=True, slots=True, kw_only=True)`；11 个字段的类型与缺省按 `data-model.md` §3.4 逐字（`id: str` / `name: str` / `attributes: Mapping[str, Any] = field(default_factory=dict)` / `parent: str | None = None` / `start_time: str` / `end_time: str | None = None` / `context: Mapping[str, Any] = field(default_factory=dict)` / `thread_id: str | None = None` / `run_id: str` / `node: str` / `checkpoint_id: str | None = None`）——**映射型字段的缺省 MUST 用 `field(default_factory=dict)`**（dataclass 的可变缺省 `= {}` 会被 `ValueError` 拒绝；B1F1 `types.py:117` 同款）；`__post_init__` 用 `object.__setattr__` 把 `attributes` / `context` **浅拷贝**为新映射——**浅拷贝 MUST 用 `dict(...)`**（与 B1F1 `RunConfig.metadata` 同款），**MUST NOT** 用 `MappingProxyType`（**不可 JSON 序列化**，会让 SC-011 / SC-014 的 JSON 可序列化断言落不了地）；**零值校验**（不校验 `run_id` 非空、不校验时间格式）；**并补 FR-010 ① / SC-005 ③ 的配套断言**（本 feature 的直接落点，勿依赖 B1F1 的回归测试代劳）：`RunConfig` 的字段清单 MUST 恰为 `["thread_id", "context", "metadata", "tags"]`（`thread_id` **在**清单内 ⇒ 会话标识由运行配置承载）且 **`"run_id"` 不在**清单内 ⇒ 单次运行标识**不进**运行配置（C22 · D11 已冻结，本 feature MUST NOT 增删该清单）
- [X] T019 [US2] 在 `src/freegraph/contracts/protocols.py` **追加** `TraceSink`：`@runtime_checkable class TraceSink(Protocol)`，3 个方法**纯抽象**——`on_span_start(self, span: Span) -> None` / `on_span_end(self, span: Span) -> None` / `current_span(self) -> Span | None`；docstring MUST 写明**回调载荷语义**（开始收「`end_time` 为空」的实例 → 结束收**同 `id`、`end_time` 已填的新实例** → 两次**按 `id` 配对** → 开始时的实例**不被事后改写**）与「`current_span()` 在无当前 span 时返回**空值**，MUST NOT 抛异常」
- [X] T020 [US2] 在 `src/freegraph/contracts/__init__.py` **追加**再导出 `TraceSink` 与 `Span`（`__all__` 接在既有项之后）
- [X] T021 [US2] 在 `tests/contracts/fixtures/external_impl.py` **追加**假 `TraceSink`：记录 `on_span_start` / `on_span_end` 的调用序列（存 `id` 与 `end_time`），`current_span()` 返回**空值**语义；**方法 MUST 写全类型注解**（`on_span_start(self, span: Span) -> None` / `on_span_end(self, span: Span) -> None` / `current_span(self) -> Span | None`，逐字按协议签名）——`mypy --strict` 的前提（SC-004）
- [X] T022 [US2] 在 `tests/contracts/test_span.py` 补 US2 断言：用 `dataclasses.replace(start_span, end_time=...)` 造「结束版」，断言 `id` 相同、`end_time` 已填、**原实例的 `end_time` 仍为 `None`**（不被改写）、两次回调按 `id` 可配对

**Checkpoint**: `python3 -m pytest tests/contracts/test_span.py -q` 全绿；`PYTHONPATH=src python3 -c "from freegraph.contracts import Span, TraceSink"` 成功。

---

## 阶段 5: User Story 3 - 图结构可被外部读取与绘制 (Priority: P3)

**Goal**: 交付**自有**的图结构类型 `Graph` / `Node` / `Edge`（**不复用** `langchain_core.runnables.graph`），使上层能读节点与边、画图、做结构断言。

**Independent Test**: 构造含若干节点与边的图结构对象，断言暴露节点集合与边集合、元素是本层纯数据类、节点名与别名可读且互不混淆、普通边与条件边可区分。

### 测试（先写，先失败）

- [X] T023 [P] [US3] 写 `tests/contracts/test_graph.py`（先写、**必须先失败**）：① `Node` 的**字段恰为 3 个**（`id` / `name` / `metadata`）、`name` 缺省时**归一为 `id`**、`metadata` 浅拷贝；② `Edge` 的**字段恰为 4 个**（`source` / `target` / `conditional` / `condition`）、`conditional` 缺省 `False`、`condition` 缺省 `None`；③ `Graph` 的**字段恰为 2 个**且类型为 `tuple[Node, ...]` / `tuple[Edge, ...]`、缺省 `()`；④ 三者**不可变**（改字段抛 `FrozenInstanceError`）；⑤ 三者**不可哈希**（`hash()` 抛 `TypeError`；**`Edge` 也要不可哈希**——其四字段全是标量，须靠显式 `__hash__ = None` 达成）；⑥ 字段级相等；⑦ 字段值**可 JSON 序列化**；⑧ **无**承载对象引用的字段（字段类型只落在标量 / 映射 / 元组 / 本层纯数据类之内）

### 实现

- [X] T024 [US3] 在 `src/freegraph/contracts/graph.py` 实现 `Node`（本模块 **MUST NOT** import `protocols`——`protocols` 依赖本模块，反向 import 会造成循环导入）：`@dataclass(frozen=True, slots=True, kw_only=True)`；字段 `id: str` / `name: str | None = None` / `metadata: Mapping[str, Any] = field(default_factory=dict)`（**映射型字段的缺省 MUST 用 `field(default_factory=dict)`**——dataclass 的可变缺省 `= {}` 会被 `ValueError` 拒绝；B1F1 `types.py:117` 同款）；`__post_init__` 用 `object.__setattr__` 把 `name` 为 `None` 时**归一为 `id`**、把 `metadata` **浅拷贝**（**MUST 用 `dict(...)`**，同 L3 口径）；**零值校验**；docstring MUST 写明「`name` 的**输入**类型是 `str | None`，但**构造后恒为 `str`**（缺省归一为 `id`）——读侧 MUST 视其为 `str`，无需 `or` 回落」
- [X] T025 [US3] 在 `src/freegraph/contracts/graph.py` 实现 `Edge`：`@dataclass(frozen=True, slots=True, kw_only=True)`；字段 `source: str` / `target: str` / `conditional: bool = False` / `condition: str | None = None`；**类体 MUST 显式写 `__hash__ = None`**（否则 dataclass 会自动生成 `__hash__`，与「四类统一不可哈希」冲突——依据 CPython `dataclasses._hash_action` 的 `(False, True, True, True) → None`）
- [X] T026 [US3] 在 `src/freegraph/contracts/graph.py` 实现 `Graph`：`@dataclass(frozen=True, slots=True, kw_only=True)`；字段 `nodes: tuple[Node, ...] = ()` / `edges: tuple[Edge, ...] = ()`；**零值校验**（节点唯一性、边端点存在性由生产者保证）
- [X] T027 [US3] 在 `src/freegraph/contracts/__init__.py` **追加**再导出 `Graph` / `Node` / `Edge`
- [X] T028 [US3] 在 `tests/contracts/test_graph.py` 补 US3 断言：`Edge` 不可哈希、`Node.name` 缺省归一、两个集合为元组且元素类型正确

**Checkpoint**: `python3 -m pytest tests/contracts/test_graph.py -q` 全绿；`PYTHONPATH=src python3 -c "from freegraph.contracts import Edge, Graph, Node"` 成功。

---

## 阶段 6: User Story 4 - 契约清单可被一次性冻结与审计 (Priority: P4)

**Goal**: 把「契约冻结」落成**可审计的实物**——C27 的查询请求结构 `TraceQuery`、18 个符号的**唯一权威清单**、**C1–C27 逐条对照表**、**冻结记录**、**人工验证记录**，以及 `README.md` 兼容矩阵里**本层 10 个符号**的行（宪法原则 X「扩展 API 兼容面的特性 MUST 更新清单」）。

**Independent Test**: 在契约层中查证 C27 的请求 / 返回结构与 C22 / C23 的字段约定；核对冻结对照表覆盖 C1–C27 **全部 27 条**且无遗漏；断言仓库内「自称权威」的公开符号清单文件**恰为 1 个**。

### 测试（先写，先失败）

- [X] T029 [P] [US4] 写 `tests/contracts/test_span.py` 的 `TraceQuery` 部分（先写、**必须先失败**）：① 字段**恰为 5 个**且名字逐字为 `run_id` / `thread_id` / `node` / `start_time` / `end_time`；② 五字段**全部可空**（缺省 `None`）；③ 可**任意组合**（穷举 32 种组合构造不抛错）；④ **全空 = 取全部**的语义（由查询实现保证，本层只断言「全空可构造」）；⑤ **可 JSON 序列化**；⑥ **可哈希**（五字段全为标量 ⇒ dataclass 默认可哈希——**有意如此**，与另四类的「不可哈希」不同）

### 实现

- [X] T030 [US4] 在 `src/freegraph/contracts/trace.py` **追加** `TraceQuery`（本模块 **MUST NOT** import `protocols`）：`@dataclass(frozen=True, slots=True, kw_only=True)`；5 个字段全为 `str | None = None`；**不覆写** `__hash__`（保持默认可哈希）
- [X] T031 [US4] 在 `src/freegraph/contracts/__init__.py` **追加**再导出 `TraceQuery` ⇒ 累计 17 个符号（`CompiledGraph` 待 T039 补齐为 18 个）
- [X] T032 [US4] **复核并校准** `specs/b2f1-contracts-protocols/contracts/public-api.md`（plan 阶段已产出）：① §0 的符号清单 MUST **恰含 18 个**（**8 个 B1F1 既有 + 10 个本 feature 新增**，两组的分组注释须正确）；**「与 `contracts/__init__.py` 的 `__all__` 集合相等」由 G7 判定**（G7 已在 Foundational 的 T008 拆成「子集段 + 集合相等段」并**不依赖本任务的执行时机**）——本任务**只需人工核对清单本身**（`__all__` 的追加顺序按任务执行序，见「共享文件」表，与 §0 的分组顺序不同属预期）；② §1.1 的**每个协议行 MUST 附来源**——**有上游同名能力者**给 `路径:行号`（如 `langgraph/checkpoint/base/__init__.py:239`）**并标注核实版本**；**无上游同名能力者**（`NodeFunc` / `TraceSink`）写「**无上游同名符号**」+ **契约条目号**（C5 / C6、C23 / C24）+ 最接近的上游物（若有）——**MUST NOT** 为凑行号而指向无关的上游位置（如 `TraceSink` 行不得指向 `pregel/main.py:845`，那是 `get_graph`）；**MUST NOT** 与 README 章节级「证据来源」小节所声明的版本混用而不加标注；③ §2 的 **C1–C27 冻结对照表 MUST 覆盖全部 27 条**（**「状态」列 MUST 为二态**：取值**恰为** `已冻结` / `挂起` 二者之一，**MUST NOT** 带限定词如「已冻结（协议面）」——限定词归「备注」列；**「修订」为独立列**，取值 `—` 或 `D11`，其非空项 MUST **恰为** 4 条（C17 / C22 / C23 / C27）；统计行须自洽：**已冻结 15 + 挂起 12 = 27、遗漏 0**，「修订」列**不计入**二态统计）；④ §3 的冻结记录 MUST 写明 spec FR-013 的**四件事**（C27 已落契约层 / span 必带四项已进类型定义 / `run_id` 归运行时层且不进 `RunConfig` / 本 feature 的三项裁定）；⑤ §5 的**移交后续 feature** 表 MUST 含 16 条（第 4 条按 B2F1 复核裁定改为「**参数名已按 `data-model.md` §2.5 冻结为占位名**，行为细节挂起 B7F3 / B8F2 / B15F1 / B16F1」；第 11 条口径 = 「兼容矩阵的**本层 10 行已在本 feature 补入**；**有上游对应者须附来源行号、无上游对应者写「无上游对应」+ 契约编号**」；全库补全与定稿归 B24F1；「`THIRD_PARTY_NOTICES` 无需新增登记」）；⑥ **与唯一权威逐条对照**——以 `harness/reports/Q8-图运行时最小契约.md` §3.4（+ §3.4.1，D11 增补与字段级约定）为基准，逐条比对 C1–C27 的**契约项名**与**最小要求关键语义**（至少：契约项名、`v1 归属 feature`、C22 / C23 / C27 的字段级约定），**差异数 MUST == 0**；**MUST NOT 只校验条目数与状态标注**——「数量对但内容被改写」的表 MUST 判失败（宪法原则 VII：「契约清单以 Q8 为唯一权威，MUST NOT 擅自增删条目」）
- [X] T033 [US4] 在 `README.md` 的「## API 兼容矩阵」章节**补入本层新增的 10 个公开符号**的行：`NodeFunc` / `Checkpointer` / `TraceSink` / `Store` / `CompiledGraph` / `Graph` / `Node` / `Edge` / `Span` / `TraceQuery`；每行**四列**（freegraph 符号 / 对应上游符号 / 等价程度〔行为等价 · 部分等价 · 不支持〕/ 差异说明），**MUST NOT 新增第 5 列**（既有 8 行**逐字不动** ⇒ 同表列数必须一致）；**上游来源行号追加在该行的「差异说明」单元格末尾**（与说明文字以 `；` 分隔）——**有上游同名符号者**附来源行号（如 `langgraph/checkpoint/base/__init__.py:239`、`langchain_core/runnables/graph.py:65`）；**无上游同名符号者**（`NodeFunc` / `TraceSink` / `Span` / `TraceQuery`）在「对应上游符号」列写「**无上游对应**（自由设计）」、在差异说明列注明**契约条目号**（C5 / C6、C23 / C24、C27），**MUST NOT** 硬凑行号（B2F1 第二轮复核裁定 2026-11-06 · SC-021 与 G8 同步改判）；**既有 8 行逐字不动**（其上游来源维持章节级「证据来源」小节的写法——G8 的行内来源要求只对**有上游对应**的**新增 10 行**成立，见 `contracts/architecture-gates.md` G8）；并在该章节的「证据来源」小节追加**本层来源行号且标注版本**（本轮核实环境 = `langgraph 1.2.11` / `langchain-core 1.6.3`，与该小节现有声明的 `LangGraph 1.2.19` / `langchain-core 1.7.6` **分行标注**、MUST NOT 混为一谈，**并注明「行号以各自标注的版本为准」**）；**并在该小节加一句**章节级提示——「**表内新增行的上游行号以 `langgraph 1.2.11` / `langchain-core 1.6.3` 为准，与既有行的 `1.2.19` / `1.7.6` 版本不同**」——**仅逐行标注易被读者误读为同一版本**（第四轮复核裁定）（宪法原则 X「每个扩展 API 兼容面的特性 MUST 更新两份清单」+ B1F1 FR-016 的「填入本层内容」口径）；**并在本任务写入 README 之后，启用 G8 的「集合相等段」**（`矩阵首列符号集合 == §0 解析出的 18 个`）——该段由 **T008** 预留、在此启用（与 G7 的集合相等段在 **T040** 启用**同构**）：README 补入本层 10 行之前不可启用（否则门禁必红），补入之后 MUST 立即启用（抓「漏写」）；**启用前 MUST 先确认本任务的 10 行已全部写入且逐符号合规**（行内来源行号只对 6 个有上游同名符号者成立）
- [X] T034 [US4] **复核**（plan 阶段已落盘，**不重写**）`specs/b1f1-contracts-core/contracts/public-api.md` 顶部的取代提示：确认 ① 首行附近有 `<!-- authority: no -->` 标记；② 标题**之前**有「📌 历史快照 —— 已由 B2F1 取代」的提示段且指向 `specs/b2f1-contracts-protocols/contracts/public-api.md`（18 个符号）；③ 该文件其余内容**逐字未改**（B1F1 的 8 符号清单与冻结记录仍完整有效）——**MUST NOT** 删改任何既有内容
- [X] T035 [US4] 在 `tests/contracts/test_architecture.py` 增加 **G12**（公开符号面**唯一权威**）：扫描仓库内 `**/public-api.md`，读取其**首行附近**的**机器标记** `<!-- authority: yes -->` / `<!-- authority: no -->`——标记为 `yes` 的文件数 **== 1**，且该文件 MUST 是 `specs/b2f1-contracts-protocols/contracts/public-api.md`；**标记缺失**时按「非权威」处理并在报错中点名该文件（MUST NOT 静默通过）；**判定只认标记、MUST NOT** 用「唯一手工维护点」「权威来源」等**关键词**判定（B1F1 旧文件正文仍含这些字样，关键词判定会误计为 2 个）；**并写门禁自检**——临时伪造第二个标记为 `yes` 的文件，断言门禁确实报出（自检须在**临时目录**内进行，不得污染仓库；**伪造文件 MUST 命名为 `public-api.md`**——G12 扫的是 `**/public-api.md`，文件名不符则扫不到、自检**假绿**）
- [X] T036 [US4] **复核并校准** `harness/verification/B2F1/manual-verification.md`（plan 阶段已产出的骨架）：① 五段式齐备（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）；② A1–A4 判据表齐备；③ **三处「不适用」子项显式记录**（原则 III 的 `target.py` 原样可跑归 B2F2 / B7F3；原则 V 的「双跑」归无运行时场景；原则 II 的 C4 / C8 回归测试归 B5F2 / B8F1）；④ 第 3 节的实测输出**保持占位 `_待填_`**——**MUST NOT 伪造输出**（人工执行后由 T050 回填）；⑤ **§6「后续 feature 注意事项」的移交项 MUST 与 `contracts/public-api.md` §5 的 16 条逐条对齐**（编号可不同，**内容集合必须相同**；合并须显式标注）——**现状已满足**（骨架已列 16 条：① 「兼容矩阵 10 行」与「`THIRD_PARTY_NOTICES`」已**拆为 2 条**；② 已含「公开 API 门面 `freegraph/graph.py` → **B2F2**」与「`mermaid` 文本 / PNG 渲染 → **B22F1 / B23F1**」）⇒ 本任务**只需复核**其仍与 §5 一致，**MUST NOT** 回退或改写内容集合；⑥ **§5 标题的 SC 引用**——**现状已满足**（「冻结记录（**SC-006** / **SC-020** / **FR-013**）」；**SC-008 是「契约层零行为」**，与冻结记录无关）⇒ 本任务**只需复核**
- [X] T037 [US4] **复核**（plan 阶段已落盘）`harness/verification/README.md` 的「当前已有记录」表中 **B2F1 行**已登记（记录链接 + 状态「🚧 骨架已就位，待人工执行后回填实测输出」）；若缺失则补登记

**Checkpoint**: `python3 -m pytest tests/contracts/test_architecture.py -q` 全绿（含新增 G12）；`public-api.md` 的 §0 **恰含 18 个符号**（「与 `__all__` 集合相等」的机器判定归 G7 的**集合相等段**，在 T040 全部导出后启用——本阶段生效的是 G7 的**子集段**）；`README.md` 兼容矩阵**已含本层 10 个符号**（逐符号核对）；**G8 的「集合相等段」已在本任务（T033）写入 README 之后启用**（在此之前生效的是 T008 落地的**子集段**）。

---

## 阶段 7: User Story 5 - 跨仓库接手方能凭契约独立实现任何一项可插拔能力 (Priority: P5)

**Goal**: 收口**编译产物能力面** `CompiledGraph`（6 方法），并用一个**零内部依赖**的夹具**同时**实现 `Checkpointer` / `TraceSink` / `Store` 三个协议 + 静态类型检查通过，证明契约确实可被外部实现。

**Independent Test**: 一份**只** import `freegraph.contracts` 的夹具同时实现三个协议，静态类型检查（mypy 可用时）与运行时结构化子类型判定**全部通过**；在未装任何 LangChain 家族包的环境中导入契约层，依赖闭包为空集。

### 测试（先写，先失败）

- [X] T038 [P] [US5] 写 `tests/contracts/test_protocols.py` 的 US5 部分（先写、**必须先失败**）：① `CompiledGraph` 的方法集**集合恰为** 6 个——`invoke` / `stream` / `get_graph` / `get_state` / `get_state_history` / `update_state`（**集合断言，不判顺序**——理由同 T010 ①）；② `get_graph` 的 `xray` 为**关键字参数**且缺省 `False`；③ `get_state` 的返回注解含 `None`（**查不到返回空值**）；④ `stream` 的返回注解元素类型为 `dict[str, Any]`（**纯数据字典**，**非** `Any`）；⑤ 夹具中 `Checkpointer` / `TraceSink` / `Store` 实例的 `isinstance` 判定**三者全真**；⑥ 任一协议缺方法变体判**假**

### 实现

- [X] T039 [US5] 在 `src/freegraph/contracts/protocols.py` **追加** `CompiledGraph`：`@runtime_checkable class CompiledGraph(Protocol)`，6 个方法**纯抽象**，返回类别与**参数名**逐字按 `data-model.md` §2.5（B2F1 复核裁定：参数名**冻结为占位名**，不再挂起）—— `invoke(self, input: StateDict, config: RunConfig | None = None) -> StateDict` / `stream(self, input: StateDict, config: RunConfig | None = None, *, stream_mode: str | Sequence[str] = "values") -> Iterator[dict[str, Any]]` / `get_graph(self, *, xray: bool = False) -> Graph` / `get_state(self, config: RunConfig) -> StateSnapshot | None` / `get_state_history(self, config: RunConfig) -> Iterator[StateSnapshot]` / `update_state(self, config: RunConfig, values: StateDict, as_node: str | None = None) -> StateSnapshot`；docstring 写明「`get_state` **查不到返回空值**、MUST NOT 抛异常」与「**行为细节挂起** B7F3 / B8F2 / B15F1 / B16F1；**参数名为冻结的占位名**，下游确需改名者走**契约修订**流程，MUST NOT 就地改型」
- [X] T040 [US5] 在 `src/freegraph/contracts/__init__.py` **追加**再导出 `CompiledGraph` ⇒ `__all__` 达 **18** 个；**并同步更新本文件的模块 docstring**（现文「公开符号面**恰为 8 个**」「本层不导出 `Send` 与 `interrupt`（**二者归 B2F1**）」两处均已失真 ⇒ 改为「恰为 **18** 个」与「二者归 **v2**（B11F1 / B10F1），本 feature **不导出**」）；**并在此启用 G7 的「集合相等段」**（`set(contracts.__all__) == §0 解析出的 18 个`）——此时 18 个符号已全部导出，集合相等方可成立（G7 的**子集段**已在 T008 始终启用）
- [X] T041 [US5] 在 `tests/contracts/test_architecture.py` 补 **G7 的门禁自检**——**G7 的主体改造已在 Foundational 的 T008（子集段）与 T040（集合相等段）完成**（期望值**从 `public-api.md` §0 解析**，**不得**硬编码 18），本任务**只补自检**：① 临时**多**导出一个符号 ⇒ 门禁报出（子集段即报）；② 临时**少**导出一个符号 ⇒ 门禁报出（集合相等段即报）；自检均须在**临时目录**内进行，不得污染仓库
- [X] T042 [US5] 在 `tests/contracts/test_architecture.py` 增加 **G11**（结构化子类型判定可用）：完整实现判**真**、每个协议缺方法变体判**假**；**G13**（**纯数据纪律**）：以 `typing.get_type_hints` 解析 `Graph` / `Node` / `Edge` / `Span` / `TraceQuery` 的字段注解，字段类型 MUST 落在**白名单**之内（`str` / `int` / `float` / `bool` / `None` / `Mapping[str, Any]` / `tuple[...]` / 本层纯数据类；`Any` **仅允许**出现在 `Mapping[str, Any]` 的**值位**），出现可调用类型或白名单外的类型即失败——**白名单口径与 `contracts/architecture-gates.md` G13 同口径**（第四轮复核：原「不得含任意**对象实例类型**」在 `get_type_hints` 下不可机械判定）；两条门禁**各带门禁自检**。**G10（协议纯抽象）不在本任务**——已在 Foundational 的 **T059** 落地（避免 FR-007 在 T011–T039 期间无自动判据）
- [X] T043 [US5] 在 `tests/contracts/fixtures/external_impl.py` **补齐**：三类协议的**完整实现**齐备（US1 / US2 已写，本任务补齐「三者同时满足」所需的交叉断言辅助）+ 一个**缺方法变体工厂**（用于 G11 / US5 判假用例）；该文件**只**允许 `from freegraph.contracts import ...` 与标准库 import；**全部方法 MUST 写全类型注解**（**参数名 MUST 与协议逐字相同**：协议侧 `Checkpointer` = `config` / `thread_id`、`Store` = `namespace` / `key` / `value` / `namespace_prefix` / `prefix` / `ops`；**未冻结部分（返回类型 / 载荷 / 命名空间载体）用 `Any` 占位**并与协议一致；缺方法变体工厂的缺失方法**故意不实现**，其存在性即判定依据）——`mypy --strict` 的前提（SC-004）
- [X] T044 [US5] 新增**静态类型检查**用例（SC-004 · B2F1 第二轮复核裁定 2026-11-06 · **三处一起收紧**）：① **前提**——以 `importlib.util.find_spec("mypy")` 判定 mypy 是否可用；**可用**时 MUST 以 `MYPYPATH=src`（或已安装的发行包）让 mypy 能解析 `freegraph.contracts`——**未安装 freegraph 且无 `MYPYPATH` 时该用例 `skip`**（MUST NOT 失败），skip 原因 MUST 写明「mypy 是**开发期工具**且 `freegraph` 未安装 ⇒ 该判据不可执行」；② **断言**——对 `tests/contracts/fixtures/external_impl.py` 跑 `mypy --strict` 并断言**无错**（**前提**：夹具方法已按协议签名**写全类型注解**，见 T015 / T021 / T043；`--strict` 的 `disallow_untyped_defs` 会把漏注解直接判错）；③ **一致性断言**（SC-004「证明协议确实可被外部实现」的落点）——新增**显式**的一致性检查：把夹具的 `Checkpointer` / `TraceSink` / `Store` 实例分别**传给形参标注为对应协议类型**的函数（或以 `assert_type` / `reveal_type` 断言），使 mypy **静态验证**三者确实满足协议——**仅编译夹具文件不构成协议实现的证明**（MUST NOT 只跑 mypy 而不做一致性断言）
- [X] T045 [US5] 在 `tests/contracts/test_protocols.py` 新增**注解结构兜底断言**（不依赖 mypy，任何环境都跑）：比对夹具三类协议实现与协议本身的方法**名 / 参数名 / 参数顺序 / 注解**——**方法名与参数顺序用 `inspect.signature(cls.method)` 取**（`typing.get_type_hints(cls)` 取的是**类级注解**，拿不到方法签名，勿误用），**注解用 `typing.get_type_hints(cls.method)`** 取，再与协议侧同法取值逐项比对（挡「签名写错」这类失守；**不替代** T044 的静态类型检查）
- [X] T046 [US5] 在 `tests/contracts/test_span.py` 补 `TraceQuery` 断言（5 字段逐字、全可空、可组合、全空可构造、可 JSON 序列化、可哈希）
- [X] T056 [US5] **改造既有** `tests/contracts/test_architecture.py` 的 `TestGateSelfCheck`（**不另起平行自检**）：本 feature **改写了** G2 / G4 / G5 / G9 的判定范围，故这四条门禁的**自检 MUST 在既有 `TestGateSelfCheck` 上就地改造 / 扩充**——**MUST NOT** 在别处再写一份同判据的自检（两处漂移）。**既有 5 个自检用例的迁移口径**：① `test_third_party_import_is_detected` / `test_internal_import_is_detected` / `test_package_escaping_relative_import_is_detected` —— `scan_imports` 拆成**两档**（内部档 / 第三方档）后，这三个用例 MUST 改为调用**各自对应的那一档扫描函数**（若保留「两档合一」的入口，它 MUST NOT 再作为门禁判据）；② `test_env_var_read_is_detected` —— G4 的扫描范围扩到 `tests/contracts/fixtures/**`，本用例 MUST 补一个「**夹具目录内**的违规文件」变体；③ `test_g9_detects_newer_typing_constructs`（8 组参数化）—— **保持不变**（G9 的判定未变，仅新增模块落在既有扫描范围内）；④ **G5 自检为新增**（既有 `TestSignatureHeader` 无自检）——在**临时目录**造一个首行缺署名头 / 模块 docstring 不是首个语句的文件，断言扫描确实报出；⑤ **G2 新增「pytest 豁免」子例**——造一个只 `import pytest` 的文件，断言**不**报出（验证两档范围）；⑥ **G4 新增「夹具目录」变体**——在**临时目录**造含 `import socket` 的**夹具**文件，断言报出；⑦ **G9 新增「3 个新模块已落在扫描范围内」的复核**（`scan_runtime_baseline` 已是目录入参，**MUST NOT 重写扫描器**）。**全部自检 MUST 在临时目录内进行，不得污染仓库**。
- [X] T057 [US5] 新增「**公开符号面 18 个符号的注解可解析**」断言（SC-010 / FR-012）：对契约层导出的**全部 18 个符号**（5 个协议 + 5 个数据类 + B1F1 的 8 个）逐一用 `typing.get_type_hints` 解析其注解（协议取其方法注解，数据类取其字段注解），断言**无未解析的字符串注解**、无解析异常（判据：解析结果中不出现未解析的 `str` 注解占位）；本任务**补齐** SC-010 中「每个符号的类型注解可被标准类型自省工具完整解析」这一子句——此前只有 G13 覆盖 5 个数据类
- [X] T058 [US5] **复核** `tests/contracts/test_architecture.py` 既有的「**单独导入契约层不加载任何内部层模块**」**子进程**断言（SC-002 的运行时子句）在新增三个模块后**仍全绿**——既有断言为 `test_importing_contracts_loads_no_internal_layer` 与 `test_importing_contracts_does_not_pull_known_layers`（点名 `freegraph.runtime` / `freegraph.graph` / `freegraph.persistence` / `freegraph.observability` 四层一个都不许出现）⇒ **本任务 MUST NOT 重复实现同一断言**（重复实现即判据两处漂移）；与 G1 的「顶层包惰性」互补：G1 断言 `import freegraph` 不连带加载契约层，本任务复核 `import freegraph.contracts` 不连带加载内部层

**Checkpoint**: `python3 -m pytest tests/contracts -q` 全绿；`PYTHONPATH=src python3 -c "from freegraph.contracts import *"` 暴露的符号**恰为 18 个**。

---

## 阶段 8: Polish & Cross-Cutting Concerns

**Purpose**: 跨故事的一致性与交付完整性收口。

- [X] T047 [P] 复核 `src/freegraph/contracts/` 下**六个** `.py`（`__init__.py` / `types.py` / `errors.py` / `protocols.py` / `graph.py` / `trace.py`）与 `tests/contracts/` 下**全部**新增 `.py`：署名头逐字正确、模块 docstring 为首个语句、无 `TODO` / `FIXME` / `print(` / `breakpoint()` 等调试残留；**并确认 `contracts/__init__.py` 的模块 docstring 已更新**（「恰为 8 个」→「恰为 **18** 个」；「`Send` / `interrupt` 二者归 B2F1」→「归 **v2**（B11F1 / B10F1），本 feature **不导出**」）——否则该文件会对外声明一个**已不成立**的符号面；并确认 `types.py` 与 `errors.py` **一字未改**（`git diff HEAD -- src/freegraph/contracts/types.py src/freegraph/contracts/errors.py` 为空）
- [X] T048 跑全量验证：`python3 -m pytest tests/contracts -q` 全绿，**并**执行 `specs/b2f1-contracts-protocols/quickstart.md` 第 1–3 节全部步骤（两处都要，不能只跑单测）
- [X] T049 [P] 隔离环境验收（照 `specs/b2f1-contracts-protocols/quickstart.md` §2.1–§2.4 执行）：建 CPython **3.11** venv → `pip install .` → `pip list` **只有** `freegraph`；依赖闭包（`importlib.metadata.requires` 递归展开）**为空集**；`import freegraph.contracts` 成功且墙钟 **< 300 ms**；`import freegraph` 后 `sys.modules` 中的 **`freegraph.*` 条目恰为** `['freegraph']`（其余为标准库条目，不在断言范围内）
- [X] T050 **人工**：按 `quickstart.md` 执行并**回填** `harness/verification/B2F1/manual-verification.md` 的第 1 节（环境）、第 3 节（**真实**输出）、第 4 节（结论逐条对照 A1–A4）、第 5 节（冻结记录）；MUST 标注 mypy 是否 `skip`、MUST 保留三处「不适用」子项的显式记录；**MUST NOT 伪造输出**——**未回填前本 feature MUST NOT 宣布完成**（宪法原则 X）
- [X] T051 回填 `specs/b2f1-contracts-protocols/plan.md` 的「Scale/Scope」**实测值**（实现行数 / 测试行数 / 用例数 / 文档行数）——立项书估算为「实现 480 / 测试 340」，实测可能更高（**测试尤其**），差异记在案
- [X] T052 复核 `specs/b2f1-contracts-protocols/contracts/public-api.md` §2 的 C1–C27 对照表与**实现**逐条相符（每条状态与实际冻结面一致，无「声称已冻结实则未落地」）；确认 §5 的 **16 条**移交项完整
- [X] T053 [P] 复核 `pyproject.toml` **未改动**：`git diff HEAD -- pyproject.toml` 为空（**须带 `HEAD`**——裸 `git diff` 不覆盖已 `git add` 的改动）；依赖白名单仍 `dependencies = []`、**未新增 extras、未新增第二发行包**（D1）
- [X] T054 [P] 复核 `README.md` 的兼容矩阵**已含本层 10 个新符号的行**（逐符号断言：每个符号**恰有一行**，且该行含「对应上游符号 / 等价程度 / 差异说明」三列；**有上游同名符号者**另须含**上游来源行号**，**无上游同名符号者**（`NodeFunc` / `TraceSink` / `Span` / `TraceQuery`）须写「无上游对应」+ 契约条目号——FR-017 / SC-021），**既有 8 行逐字未改**——**该条 MUST 有机械判据**：`git diff HEAD -- README.md`（**须带 `HEAD`**）的**删除行集合 MUST 为空**，且新增行 MUST 落在**两个白名单**内——① 本层 **10 个新符号**的矩阵行（逐行核对首列符号名）；② 「**证据来源**」小节内的**追加行**（T033 同时追加本层来源行号 + 一句「行号以各自标注的版本为准」的章节级提示）——**白名单外的新增行一律判失败**（报错须点名该行内容）；只靠人工比对不满足 SC-021 的「行数与内容断言」；确认 `THIRD_PARTY_NOTICES` §2 **无新增登记**（本 feature **零**新增第三方依赖 ⇒ 无需登记）
- [X] T055 提交：按仓库提交风格（中文 conventional commits，如 `feat(contracts): B2F1 5 个协议 + 5 个纯数据类`），**只**提交本 feature 相关文件（`src/freegraph/contracts/`、`tests/contracts/`、`specs/b2f1-contracts-protocols/`、`harness/verification/B2F1/`、`harness/verification/README.md`、`specs/b1f1-contracts-core/contracts/public-api.md` 的取代提示）
  > **提交与推送的前置条件（发起者裁定 · 2026-11-06）**：**提交与推送均以「本 feature 的
  > implement 全部完成」为前置**——MUST NOT 在 implement 未完成时提交；且该「完成」MUST 含
  > **T050**（人工回填**真实**输出，未回填前本 feature 不得宣布完成 · 宪法原则 X）与
  > **T051**（回填实测行数）两道收口。**推送**同样在本 feature 的 implement 完成后进行
  > （发起者已授权）；但本清单的执行者**默认不推送**，MUST 待发起者明确指令后才推。

---

## 追溯矩阵（spec 条目 → 任务）

> 供 `/speckit.analyse` 机械核对：spec 的每一条 FR / SC 都有落点，无遗漏、无悬空。

### 功能需求（FR）

| FR | 摘要 | 落点任务 |
|---|---|---|
| FR-001 | 节点函数协议 `NodeFunc` | T011 · T010 · T016 |
| FR-002 | 检查点协议 `Checkpointer`（6 方法 + 最小约束） | T012 · T010 · T015 · T016 |
| FR-003 | 可观测接收端协议 `TraceSink`（3 方法 + 回调载荷语义） | T019 · T017 · T021 · T022 |
| FR-004 | 长期存储协议 `Store`（6 方法 + 寻址语义，v1 无实现） | T013 · T010 · T015 · T016 |
| FR-005 | 编译产物协议 `CompiledGraph`（6 方法 + 返回类别） | T039 · T038 · T041 |
| FR-006 | 图结构数据类 `Graph` / `Node` / `Edge`（字段逐字 + 不可哈希） | T024 · T025 · T026 · T023 · T028 |
| FR-007 | 全部协议 `runtime_checkable` + **纯抽象** | T010 · T011 · T012 · T013 · T019 · T039 · **T059（G10）** · T042（G11） |
| FR-008 | 契约层零内部 import + 零 `langchain*` import | T006 · T043 · T047 · T056（G2 自检） |
| FR-009 | C27 数据契约面（`TraceQuery` 5 字段 + 约束文字） | T030 · T029 · T046 · T032 |
| FR-010 | C22 / C23 字段约定落地（`Span` 11 字段 + 必带四项） | T018 · T017 · T022 · T032 |
| FR-011 | 零第三方依赖 / 零出站 / 零环境变量 | T049 · T053 · T006 |
| FR-012 | 公开符号面一次性可取 + 无同名歧义 + 新增 10 符号清单 | T014 · T020 · T027 · T031 · T040 · T041 · T008 · T057（18 符号注解可解析） |
| FR-013 | 冻结对照表（C1–C27）+ 冻结记录（四件事） | T032 · T052 · T034 · T050 |
| FR-014 | 证据来源 + 人工验证记录 | T036 · T037 · T050 · T032 |
| FR-015 | 每个新源文件携带署名头（含 `tests/`） | T001 · T005 · T007 · T047 · T056（G5 自检） |
| FR-016 | 只交付类型、无行为（无方法体 / 无后端 / 无门面） | T011–T013 · T019 · T039 · T047 |
| FR-017 | 兼容矩阵**填入本层 10 个符号** + 上游来源 | T033 · T054 |

### 成功标准（SC）

| SC | 摘要 | 落点任务 |
|---|---|---|
| SC-001 | 18 个符号一次性取到 | T014 · T020 · T027 · T031 · T040 · T041 |
| SC-002 | 单独导入无副作用 + 依赖闭包为空集 | T049 · T048 · T058（导入契约层不加载内部层） |
| SC-003 | AST 扫描：零内部依赖 + 零 `langchain*` | T006 · T047 · T056（G2 自检） |
| SC-004 | 零内部依赖夹具同时实现三协议 + 静态类型检查 | T015 · T021 · T043 · T044 · T045 |
| SC-005 | D11 三项修订全部落地可查 | T018（含 C22 标识职责断言）· T030 · T032 · T052 |
| SC-006 | C1–C27 全 27 条逐条标注、遗漏 0 | T032 · T052 |
| SC-007 | 结构化子类型判定：完整实现真 / 缺方法假 | T010 · T016 · T017 · T038 · T042（G11） |
| SC-008 | 契约层零行为（无默认实现、无副作用） | T011–T013 · T019 · T039 · **T059（G10）** · T049 |
| SC-009 | 新建源文件 100% 署名头 | T007 · T047 · T056（G5 自检） |
| SC-010 | 公开符号面无同名歧义 + 注解可解析 | T041 · T042（G13）· T008 · T057（18 符号逐一解析） |
| SC-011 | `Span` / `TraceQuery` 100% 可 JSON 序列化（含「返回结构 = span 列表」的整体序列化） | T017（⑩ 列表子句）· T029 · T046 |
| SC-012 | 人工验证记录已产出（A1–A4 逐条核对 + 来源无遗漏） | T036 · T050 |
| SC-013 | 图结构字段清单逐字一致 + 无对象引用字段 | T023 · T024 · T025 · T026 · T028 · T042（G13） |
| SC-014 | span 字段清单逐字一致（11 字段）+ 必带四项可读 | T017 · T018 · T022 |
| SC-015 | `CompiledGraph` 六个方法的返回类别逐条一致 | T038 · T039 |
| SC-016 | `Span` 不可变 + 同 `id` 新实例 + 配对 100% | T018 · T021 · T022 |
| SC-017 | 新增公开符号恰为 10 个 + 完整清单同步为 18 | T008（§0 的「既有 / 新增」切分 + 新增集合断言）· T040 · T041 · T032 |
| SC-018 | `TraceQuery` 字段清单逐字 + 全可空可组合 | T029 · T030 · T046 |
| SC-019 | 四类数据类不可哈希 + 相等语义可用 | T023 · T024 · T025 · T026 · T028 |
| SC-020 | 四份交付物落盘 + 权威唯一 | T032 · T033 · T036 · T037 · T035（G12）· T052 |
| SC-021 | 兼容矩阵逐符号覆盖本层 10 个符号 | T033 · T054 |

### 门禁（architecture-gates.md G1–G13）

| 编号 | 落点任务 | 编号 | 落点任务 |
|---|---|---|---|
| G1 顶层包惰性 | T049 · T058 | G8 文档合规（逐符号覆盖） | **T008**（G8 改造**子集段**：期望值从 §0 解析 + 行 ⊆ 18 + 三列齐全 + 来源行号只对有上游同名符号者）· **T033**（**集合相等段**启用）· T032 · T054 |
| G2 零内部 + 零第三方 import | T006 · T043 · T047 · **T056**（自检） | G9 typing 上限 3.11 | T009 · T047 · **T056**（自检） |
| G3 依赖闭包为空 | T049 | G10 协议纯抽象 | **T059** · T010 |
| G4 零环境变量零出站 | T006 · T047 · **T056**（自检） | G11 结构化子类型判定 | T042 · T010 · T016 |
| G5 署名头 | T007 · T047 · **T056**（自检） | G12 唯一权威 | T035 · T034 |
| G6 `py.typed` | T003 | G13 纯数据纪律 | T042 · T023 |
| G7 公开符号面恰 18 个 | **T008**（子集段）· **T040**（集合相等段）· T041（自检） | | |

### 使能任务（无直接 FR/SC，但为其余任务铺路）

| 任务 | 使能对象 |
|---|---|
| T001 夹具目录与 `__init__.py` | T015 · T021 · T043 · T044 |
| T002 `__init__.py` 现状复核（既有 8 项顺序） | T014 · T020 · T027 · T031 · T040 |
| T003 `py.typed` 确认 | 全部（发行产物类型标记） |
| T004 `conftest.py` 复用与定位口径 | 全部新测试 |
| T005 三个模块骨架 | T011–T013 · T018–T019 · T024–T026 · T030 · T039 |
| T008 清单解析辅助 + **G7 子集段改造** + **G8 子集段改造** | T040（G7 集合相等段）· T033（G8 集合相等段）· T041（自检）· T032 |
| T051 回填 `plan.md` 的 Scale/Scope 实测值 | （Polish 收口 · 无直接 FR/SC） |
| T055 提交（中文 conventional commits · MUST NOT 推送） | （Polish 收口 · 无直接 FR/SC；宪法原则 VI「文档与代码同批提交」） |

---

## Dependencies & Execution Order

### feature Dependencies

- **Setup（阶段 1）**: 无依赖 — 可立即开始
- **Foundational（阶段 2）**: 依赖 Setup — **阻塞全部用户故事**
- **User Stories（阶段 3–7）**: 全部依赖 Foundational 完成
  - 可按优先级串行推进（P1 → P2 → P3 → P4 → P5），也可在 Foundational 完成后并行
- **Polish（阶段 8）**: 依赖全部用户故事完成

### User Story Dependencies

- **US1 (P1)**: Foundational 之后即可开始 — **无**其他故事依赖
- **US2 (P2)**: Foundational 之后即可开始 — **无**其他故事依赖（`TraceSink` 引用 `Span`，两者同在 US2 内）
- **US3 (P3)**: Foundational 之后即可开始 — **无**其他故事依赖
- **US4 (P4)**: 依赖 US1–US3 的符号已存在（§0 清单与 `__all__` 的集合相等由 **G7** 判定——G7 已在 Foundational 就位，**不受本故事的执行时机影响**）；但 `TraceQuery` 的实现**不依赖**任何故事
- **US5 (P5)**: 依赖 US1 / US2 / US3 —— `CompiledGraph` 的签名引用 `Graph`（US3）与 `Span`（US2）；夹具同时实现三个协议（US1 / US2）

### 共享文件（**必须串行**，不可并行）

| 文件 | 追加任务（**按序执行**） |
|---|---|
| `src/freegraph/contracts/protocols.py` | T011 → T012 → T013 → T019 → T039 |
| `src/freegraph/contracts/trace.py` | T018 → T030 |
| `src/freegraph/contracts/__init__.py` | T014 → T020 → T027 → T031 → T040 |
| `tests/contracts/test_architecture.py` | T006 → T007 → T008 → T009 → **T059** → T035 → T041 → T042 → T056 → T057 → T058 |
| `README.md`（兼容矩阵） | T033（唯一写入点，US4）→ T054（复核） |
| `tests/contracts/fixtures/external_impl.py` | T015 → T021 → T043 |
| `tests/contracts/test_protocols.py` | T010 → T016 → T038 |
| `tests/contracts/test_span.py` | T017 → T022 → T029 · T046 |

> **同文件任务 MUST 串行**——标了 `[P]` 的任务只与**不同文件**的任务并行。

### Within Each User Story

- 测试**先写、必须先失败**，再写实现
- 数据类先于引用它的协议（`Span` → `TraceSink`；`Graph` → `CompiledGraph`）
- 协议先于夹具（夹具实现协议）
- 实现完成后即补断言，再进 Checkpoint

### Parallel Opportunities

- 阶段 1 的 T001–T005 全部可并行（不同文件、无依赖）
- 阶段 3–7 各段的**测试编写任务**可与别处的实现任务并行
- `trace.py`（T018）与 `protocols.py`（T011–T013）可并行（不同文件）
- Polish 的 T047 / T049 / T053 / T054 可并行
- **T056 / T057 / T058 同属 `test_architecture.py`** ⇒ 三者**必须串行**（见「共享文件」表），
  不可与彼此并行；与**不同文件**的任务可并行
- **不同用户故事可由不同成员并行**（本项目为单人推进，此处仅备将来协作）

---

## Parallel Example: User Story 2

```bash
# 先写测试（失败），与 trace.py 的实现并行：
Task: "写 tests/contracts/test_span.py（先写、先失败）"
Task: "在 src/freegraph/contracts/trace.py 实现 Span"

# 两者完成后（协议引用数据类）：
Task: "在 src/freegraph/contracts/protocols.py 追加 TraceSink"
```

---

## Implementation Strategy

### MVP First（User Story 1 优先）

1. 完成阶段 1: Setup
2. 完成阶段 2: Foundational（**关键** — 阻塞全部故事）
3. 完成阶段 3: User Story 1（`NodeFunc` / `Checkpointer` / `Store` + 夹具）
4. **停下并验证**：单独跑 `tests/contracts/test_protocols.py` + `PYTHONPATH=src` 导入
5. 该阶段即可交付价值：**freechain 能只靠协议接上自己的持久化后端**

### Incremental Delivery

1. Setup + Foundational → 地基就绪
2. US1 → 独立验证 → 交付（持久化协议）
3. US2 → 独立验证 → 交付（可观测接入 + span 类型）
4. US3 → 独立验证 → 交付（图结构自有类型）
5. US4 → 独立验证 → 交付（契约冻结实物：对照表 + 清单 + 人工记录）
6. US5 → 独立验证 → 交付（编译产物能力面 + 端到端可实现性证明）
7. Polish → 全量验证 + 人工回填 + 提交

### Parallel Team Strategy（本项目为单人，此处仅备将来多人协作）

1. 先共同完成 Setup + Foundational
2. 然后：
   - 成员 A：US1（`protocols.py` 的 `NodeFunc` / `Checkpointer` / `Store`）
   - 成员 B：US2（`trace.py` + `TraceSink`）
   - 成员 C：US3（`graph.py`）
3. **注意**：`protocols.py` / `trace.py` / `__init__.py` 是**共享文件**——同一时刻**只能一人**改（见「共享文件」表）

---

## Notes

- [P] 任务 = 不同文件、无依赖；**同文件任务一律串行**
- [Story] 标签映射到 spec 的用户故事，供追溯矩阵机械核对
- 每个用户故事都应能**独立完成、独立测试**
- 测试**先写并确认失败**再实现
- **协议必须纯抽象**：任何默认实现都会让「缺实现」的假实现静默通过结构化子类型判定（G10）
- **数据类零值校验**：只做类型注解、缺省归一、容器浅拷贝；值级守卫会与后续 30 个 feature 的实际用法反复冲突
- 提交按逻辑分组逐次进行；**MUST NOT** 推送（除非发起者明确要求）
- 人工验证记录的第 3 节**只填真实输出**——未回填前**不得**宣布 feature 完成（原则 X）
- **公开符号面清单的机器标记**：两份 `public-api.md` 首行附近各带 `<!-- authority: yes|no -->`；门禁 G12 **只认标记**、不看字样（B1F1 旧文件正文仍含「唯一手工维护点」等字样，关键词判定会误计为 2 个）
- **兼容矩阵由本 feature 填入本层内容**（FR-017 / SC-021）：既有 8 行**逐字不动**，新增 10 行逐符号给出来源；**全库**补全与定稿归 B24F1。
  **行内来源行号的要求只对「有上游同名符号」的新增行成立**（G8 判据，见 `contracts/architecture-gates.md` G8）——
  `NodeFunc` / `TraceSink` / `Span` / `TraceQuery` **无上游同名符号** ⇒ 该 4 行写
  「无上游对应」+ 契约条目号；既有 8 行的来源以矩阵章节的「证据来源」小节为准。
- **上游来源须标版本**：本轮行号核实环境 = `langgraph 1.2.11` / `langchain-core 1.6.3`
  （`research.md` 头部）；写入 README 的「证据来源」小节时**分行标注版本**，MUST NOT 与该小节
  现有声明的 `LangGraph 1.2.19` / `langchain-core 1.7.6` 混为一谈（T032 / T033）。
- **2026-11-06 文档一致性复核**（`/speckit.analyze`）：本清单已按复核结论就地修正——
  T008（§0 解析规则）、T032（集合一致 + 版本标注）、T033（G8 口径 + 版本标注）、
  T034 / T037（改为「复核」）、T035（G12 只认标记）、T039（参数名冻结为占位名），
  并新增 **T056**（G2 / G5 / G9 门禁自检）· **T057**（18 符号注解可解析）·
  **T058**（导入契约层不加载内部层）⇒ 任务总数由 55 增至 **58**。
- **2026-11-06 第二轮文档一致性复核**（`/speckit.analyze` · **22 项发现**：2 CRITICAL /
  4 HIGH / 9 MEDIUM / 7 LOW）：**CRITICAL 两项经判定均非 spec 设计缺陷**
  （C1 = 门禁契约与任务的扫描范围缺陷；C2 = 任务排期缺陷）⇒ 未开澄清轮，
  直接就地修正文档。任务数**仍为 58**（**未新增任务**，全部修正并入既有任务）：
  T006（G2/G4 改**两档范围** + pytest 豁免）· T008（**G7 提前改造**并拆「子集段 /
  集合相等段」+ 清理硬编码常量与陈旧注释）· T010 ⑥（纯抽象断言**统一归 G10**，
  去重）· T015 / T021 / T043（夹具方法**写全类型注解**）· T032（§0 与 `__all__` 的
  集合相等交由 G7 判定 + §1.1「无上游同名符号者写契约编号」）· T033（**有上游对应者**
  才附行号，无对应者写「无上游对应」+ 契约编号 + README 版本分行标注）· T040
  （启用 G7 集合相等段 + 更新 `__init__.py` 的 docstring）· T041（G7 只补自检）·
  T044（mypy 三处收紧：`MYPYPATH` / 注解前提 / **显式协议一致性断言**）· T047
  （复核 `__init__.py` docstring）· T056（G4 纳入自检，共 4 条）。
- **任务编号非单调**：T056–T058 位于「阶段 7（US5）」小节内，而 T047–T055 位于
  「阶段 8（Polish）」小节内——**编号沿用首轮复核时的追加序**（保持 ID 稳定），
  **执行序**以「共享文件」表与「Dependencies & Execution Order」小节为准，与编号大小无关。
- **公开符号面的个数只引用、不重写**：「18 个」这一数字的**唯一权威 = `contracts/public-api.md` §0**；
  本清单、plan、spec 与人工记录**只引用**该处（MUST NOT 各写一份）——门禁的期望值亦**从 §0 解析**
  （T008 / G7 / G8），**不得硬编码**（T008 ④ / T041 已如此要求）。
- **2026-11-06 第四轮文档一致性复核**（`/speckit.analyze` · **19 项发现：0 CRITICAL / 6 HIGH / 7 MEDIUM / 6 LOW**）：
  **无 CRITICAL ⇒ 无 spec 设计缺陷 ⇒ 未开澄清轮**，直接就地修正文档。任务数 **58 → 59**
  （**新增 T059**，其余全部修正并入既有任务）：
  T009 后**新增 T059**（**G10 协议纯抽象**提前到 Foundational 落地 + 自检；原在 US5 末的 T042
  ⇒ FR-007「MUST 纯抽象」在 T011–T039 期间无任何自动判据）· T010 ⑥（G10 落点改指 T059）·
  T017 ⑩（SC-011 补「返回结构 = span 列表」的整体序列化断言）· T018（补 FR-010 ① / SC-005 ③ 的
  `RunConfig` 字段清单断言——本 feature 的直接落点）· T032 ⑥（**与 Q8 §3.4 逐条对照**，差异数 MUST == 0）·
  T036 ⑤⑥（人工记录 §6 移交项**补齐 16 条** + §5 标题的 SC 引用纠正）· T042（G10 移出、**G13 改白名单口径**）·
  T045（修正 API 用法：方法名 / 参数顺序用 `inspect.signature`，注解用 `get_type_hints(cls.method)`）·
  T054（「既有 8 行逐字未改」的 **`git diff HEAD -- README.md` 机械判据**）·
  阶段标题由 `## feature N` 改为 `## 阶段 N`（避与宪法 v1.4.0 的 feature = `B<n>F<m>` 撞义）。
- **2026-11-06 第五轮复核**（`/speckit.analyze` · **14 项发现：1 CRITICAL / 2 HIGH / 5 MEDIUM / 7 LOW**）：
  **唯一的 CRITICAL 经判定为「任务排期缺陷」而非 spec 设计缺陷**（spec 的 FR-012 / FR-017 /
  SC-017 / SC-021 与门禁契约 G8 的口径本就一致且正确，缺口**只在 tasks.md**）⇒ **未开澄清轮**，
  直接就地修正文档。**任务数仍为 59**（未新增任务，全部修正并入既有任务）：
  **T008**（**G8 的测试改造并入本任务** + **两段落地**：子集段 T008 / 集合相等段 T033——因 README 的 10 行由 T033 写，故若在 T008 就按「18 个逐个恰有一行」判定，**T008~T033 门禁恒红**、两个 Checkpoint 都过不去；另 §0 解析函数加「既有 / 新增」切分 + 新增集合 == FR-012 的 10 个断言 + 清理 `:364` / `:771` 与陈旧测试方法名 + **「删常量」排在「G8 改造」之后**）·
  **T033**（README 写入后**启用 G8 的集合相等段**）· **T009 / T058**（改写为「复核」——既有门禁已覆盖，重复实现即判据漂移）· **T018 / T024**（映射型字段缺省 MUST 用 `field(default_factory=dict)`——dataclass 拒绝可变缺省）· **T032**（对照表状态口径 → 二态 + 正交修订标注）· **T035**（自检伪造文件 MUST 名为 `public-api.md`）· **T036**（⑤⑥ 现状已满足 → 改写为「复核」）·
  连带：`architecture-gates.md` G7 增「新增集合段」、G8 补「两段落地」；`spec.md` FR-006 / Q12 / FR-013 /
  SC-006 / SC-017 与「复核记录 · 第五轮」；`plan.md` 的 research 决策数 13→20 + 「第五轮复核」小节；
  `harness/prompts/guide.md` 与 `harness/features/B2F1_*.md` 的**全局漂移**同步（9 处 + 4 处）。
  **冻结面的内容一字未动**；**宪法无需修订**（无 MUST 违反项）。

---

## 执行记录（2026-11-06 · 实现者单人串行推进）

> **59 个任务全部完成**（T001–T059，均已勾选 `[X]`）。全程按 **TDD 顺序**推进：
> 每个故事的**测试任务排在实现任务之前**，且测试**先失败**再实现。
> 最终实测：**284 个用例**（**278 passed + 6 skipped**）· 隔离 venv 内
> **283 passed + 1 skipped**（G3 真跑）· `mypy --strict` 对契约层与夹具**全绿**。

### 三处**执行期的口径判定**（冻结面**内容一字未动**，只改**落地方式**）

| # | 事项 | 判定 | 理由 |
|---|---|---|---|
| 1 | **T007 / T015 / T010 / T017 / T023 的文件创建时机** | 四个测试 / 夹具文件（`fixtures/external_impl.py` / `test_protocols.py` / `test_graph.py` / `test_span.py`）在**阶段 2（T007）先建为「署名头 + 模块 docstring」的骨架**，各任务的正文内容随后填入 | G5 的断言要求这四个文件**存在**且带署名头；若等到各自的任务才创建，**阶段 2 的 Checkpoint 必红**。骨架**不含任何实现**，不破坏 TDD（正文仍是「先写、先失败」） |
| 2 | **`Graph` 的不可哈希** | `Graph` 类体**显式**写 `__hash__ = None`（与 `Edge` 同款） | 冻结面（`public-api.md` §1.3）写「`Node` / `Edge` / `Graph` / `Span` **统一不可哈希**」——dataclass 默认会为 `Graph` 生成 `__hash__`，使「空图可哈希、非空图不可哈希」的不一致漏出去。`data-model.md` §4.3 给出的机制（元素不可哈希 ⇒ 自身不可哈希）**只对非空图成立** ⇒ 以**冻结面的行为口径**为准，显式声明 |
| 3 | **`__hash__ = None` 与 mypy** | 两处均写 `__hash__ = None  # type: ignore[assignment]` | mypy 对 `__hash__ = None` 有既有误报（`object.__hash__` 声明为 `Callable[[], int]`）。改用 `ClassVar[None]` **不解决**该误报，且会让 `typing.get_type_hints(cls)` 把 `__hash__` 算进**类级注解** ⇒ 污染「字段清单恰为 N 个」的断言 |

### 两处**文档校准**（T032 ⑥ 的机械对照结果）

| # | 事项 | 处置 |
|---|---|---|
| 1 | `contracts/public-api.md` §2 的 **C18** 契约项名原为「动态 fan-out（`Send`）」 | 改回 Q8 §3.4 的逐字名「**动态 fan-out**」⇒ 与 Q8 §3.4 / 立项书 §5.3 的**契约项名差异数 = 0**（`Send` 的提及保留在备注列） |
| 2 | §2 的 **C1 / C9** 的「落地位置 / 挂起归属」列原为「B4F1 / B5F1」/「B2F2」 | 对齐立项书 §5.3 的归属列 ⇒ **B4F1（类型于 B1F1 冻结）** / **B2F2（导出）/ B6F1（使用）**；并在 §2 的表头说明该列的**两种语义**（已冻结行记落地面、挂起行记 v1 归属 feature） |

### **未执行**的子项（显式记在案，**非忽略**）

| # | 子项 | 原因 | 归属 |
|---|---|---|---|
| 1 | **T049 的 CPython 3.11 隔离实测** | 本机只装了 CPython **3.12.3**（`/usr/bin/python3.12`） | **B3F1** 的 CI 矩阵（最低档 3.11）；已记入 `harness/verification/B2F1/manual-verification.md` §1 / §3.7 / §7 遗留问题 7——**MUST NOT 伪造输出** |
| 2 | **附加 A 的 3.13 / 3.14 档实测** | 同上（本机无 3.13 / 3.14 解释器） | 同上 |

> **不推送**：按本清单的「提交与推送的前置条件」，本 feature 的 implement 已全部完成
> （含 **T050** 真实输出回填与 **T051** 实测行数回填），**提交**已执行；**推送**待发起者明确指令。
