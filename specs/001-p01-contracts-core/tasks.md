---

description: "F1P1 · 契约层骨架（contracts 包 + 四个核心类型 + 异常体系）—— 任务清单"
---

# Tasks: 契约层骨架（四个核心类型 + 异常体系）

**Input**: Design documents from `/specs/001-p01-contracts-core/`

**Prerequisites**: plan.md（必读）、spec.md（必读 · 含 **15** 条澄清记录 + FR-016）、research.md（20 条决策）、data-model.md（5 实体 + 16 条不变式）、contracts/public-api.md（冻结 API · **规范源**）、contracts/architecture-gates.md（8 条门禁）、quickstart.md（验收指南）

**Tests**: **包含**。spec 的 SC-002…SC-007 全部要求「可自动判定」的断言，Phase 提示词 §10 亦把「对应单元测试」列为交付物 ⇒ 本清单按 **TDD 顺序**组织：每个故事的**测试任务排在实现任务之前**，且测试**必须先失败**。

**Organization**: 任务按用户故事分组，每个故事可独立实现、独立测试、独立验收。

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可与同阶段其他任务并行（不同文件、无依赖）
- **[Story]**：所属用户故事（US1/US2/US3）
- 描述中**必须含确切文件路径**与**具体取值**（签名、常量值、字段清单），以免实现时二次决策

## Path Conventions

- 源码：`src/freegraph/contracts/`（契约层）、`src/freegraph/__init__.py`（顶层包 · 保持惰性）
- 测试：`tests/contracts/`
- 活文档：`THIRD_PARTY_NOTICES`（仓库根）、`README.md` 的「API 兼容矩阵」章节
- 人工记录：`harness/features/F1P1/manual-verification.md`
- 规格产物：`specs/001-p01-contracts-core/`

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 建立契约层目录骨架与**测试基础设施**（仓库当前**无** `tests/` 目录，本 Phase 首次建立；freegraph 当前**未安装**，故测试须自寻 `src/`）。

- [X] T001 创建 `tests/contracts/` 目录与 `tests/contracts/conftest.py`：用 `pathlib.Path(__file__).resolve().parents[2]` 定位**仓库根**，把 `<repo>/src` 用 `sys.path.insert(0, ...)` 插入**最前**（源码优先，避免测到已安装的旧版本）；**用 pytest fixture 暴露路径**（`repo_root` / `src_dir` / `contracts_dir` 三个 fixture）—— **不得**用「模块级常量 + `from conftest import ...`」跨文件引用（那依赖 pytest 的 rootdir 插入机制，非惯用法，且 `tests/` 一旦加 `__init__.py` 即失效）；同时加**环境变量开关** `FREEGRAPH_TEST_INSTALLED=1` ⇒ 跳过 `sys.path` 注入（供 F3P1 的 CI「先 `pip install .` 再跑 pytest」用，否则测的是源码树而非发行产物）；**文件首行 MUST 带署名头**（宪法原则 X 的范围含 `tests/`，见 T002）
- [X] T002 创建 `src/freegraph/contracts/` 包目录与三个模块文件 `src/freegraph/contracts/__init__.py`、`src/freegraph/contracts/types.py`、`src/freegraph/contracts/errors.py`：每个文件**只含**署名头注释 `# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph`（位于第 1 行）+ 模块 docstring（docstring MUST 是首个语句），**不含任何实现**。**署名头的适用范围 = 本 Phase 新建的每一个 `.py`**——含 `tests/` 下 4 个测试文件（分别在 T001 / T007 / T011 / T015 带上）
- [X] T003 [P] 确认 `src/freegraph/py.typed` 存在且**内容为空**（PEP 561：顶层一个标记即覆盖全部子包）——**不得**新建 `src/freegraph/contracts/py.typed`
- [X] T004 [P] 在 `src/freegraph/__init__.py` 的模块 docstring 中补一段「顶层包保持惰性（FR-011）：只暴露 `__version__`，不导入任何子模块」的说明——**不得**新增任何 `import` 语句，`__all__` 仍只能是 `["__version__"]`

**Checkpoint**: `python3 -m pytest tests/contracts -q` 能正常运行（此时**0 个用例**——pytest 在「无用例收集」时返回**退出码 5**，属正常，**不是失败**；若报 `ModuleNotFoundError` 才是 `conftest.py` 的 `src/` 注入未生效）。

---

## Phase 2: Foundational（阻塞前置）

**Purpose**: 异常族的**基类** `FreegraphError`。它被 US1（`Command` 构造期校验 MUST 抛它）与 US2（三个子类 MUST 派生自它）**共同依赖**，故置于基础阶段。

- [X] T005 [P] 写 `tests/contracts/test_errors.py` 的基类断言（**先写、先失败**）：断言 `FreegraphError` 派生自 `Exception`、`except FreegraphError` 能捕获其实例、其 `str(exc)` 含调用方传入的消息
- [X] T006 [P] 实现 `FreegraphError` 于 `src/freegraph/contracts/errors.py`：直接继承 `Exception`、**不自定义 `__init__`**（刻意让它只做「类型锚点 + 统一捕获点」），模块 docstring 写明「本文件是内核异常族的唯一定义处；上层只捕获基类即可兜住全部内核错误；后续可新增子类但基类名不得改」

**Checkpoint**: `python3 -m pytest tests/contracts/test_errors.py -q` 全绿。

---

## Phase 3: User Story 1 - 外部项目直接引用状态与运行配置类型 (Priority: P1) 🎯 MVP

**Goal**: 交付 `StateDict` / `Command` / `StateSnapshot` / `RunConfig` 四个类型，使外部项目（如 freechain）能直接引用并用它们标注节点签名。

**Independent Test**: 在**源码树**（仓库根 + `PYTHONPATH=src`，freegraph 当前**未安装**）下执行 `from freegraph.contracts import StateDict, RunConfig` 成功；`typing.get_type_hints` 能完整解析这两个类型的注解；且导入过程**未加载任何内部层模块**。**隔离环境（只装 freegraph 基础包）下的同等验收由 T023 执行**（属 US3 的架构门禁批次，见 Dependencies 的说明）。

**覆盖的不变式**：I-01 / I-02 / I-03 / I-04 / I-05 / I-06 / I-07 / I-08 / I-09 / I-10 / I-11 / I-14 / I-16

### 测试（先写，先失败）

- [X] T007 [P] [US1] 写 `tests/contracts/test_types.py` 的**全部**断言（一次写全，覆盖 I-01…I-11、I-14、I-16 与 **SC-004**；**文件首行 MUST 带署名头**），注意下列各项**必须按此写法**，否则断言本身就会红：① `StateDict` 的可判定口径 = `typing.get_origin(StateDict) is dict` 且 `StateDict == dict[str, Any]` —— **不得**用 `is` 判定（实测 `dict[str, Any] is dict[str, Any]` 为 **False**），**不得**用 `isinstance(x, StateDict)`（参数化泛型不是合法的 `isinstance` 第二参数，会抛 `TypeError`）；② `Command()` 必抛 `FreegraphError`、三语义位可任意组合（含「跳转+写入」「恢复+跳转」）、`Command.PARENT == "__parent__"`、`Command.PARENT` **不在** `Command.__slots__` 中（证明它是 `ClassVar` 而非字段）、`update={}`（显式但为空）合法而三全空非法；③ 三个记录类构造后字段不可改（赋值抛 `FrozenInstanceError`）、`typing.get_type_hints` 能完整解析且**无残留字符串注解**（**注意**：`get_type_hints` 的返回里**含** `PARENT` 这一 `ClassVar` 项 —— 字段数 MUST 用 `dataclasses.fields()` 判定，**不得**断言「注解条数 == 字段数」）；**并断言 `repr` 与字段级相等语义**（FR-014 冻结项，此前无覆盖）：`repr(cmd)` 形如 `Command(goto=..., update=..., resume=...)`（含字段名）、`Command(goto="a") == Command(goto="a")` 为 `True`、`Command(goto="a") == Command(goto="b")` 为 `False`；④ `StateSnapshot` 七字段全必填（缺任一字段构造失败）、`metadata` 注解是 `Mapping` 形态（**字段注解自本 Phase 起一并冻结** —— F4P1 / F8P3 只能新增字段、不得改动已有字段的注解，见 spec Assumptions）、`created_at` 匹配 UTC ISO-8601 正则 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$`；⑤ `RunConfig()` 可全空构造、`from_dict({"threadId": "t"})` 抛 `FreegraphError` 且消息点名 `threadId`、`from_dict(..., ignore_unknown=True)` 忽略未知键、**哈希** `hash(cfg)` 抛 `TypeError`（因 `metadata` 装的是 dict，本类不可哈希）；⑥ **拷贝语义（I-16 · 三条）**：`cfg.metadata is not d["metadata"]`、`cfg.tags is not d["tags"]`（元组化后是**新**对象）、`snap.metadata is not passed`——且**只拷这两处**：快照**没有** `tags` 字段，**不得**对它断言拷贝；⑦ **构造期只做两条冻结校验（负向断言）**：`StateSnapshot(created_at="not-a-date")` **MUST 不抛错**、`RunConfig(thread_id=123)` **MUST 不抛错**（契约层只做类型注解，不校验值——见 spec Assumptions）

### 实现

- [X] T008 [P] [US1] 实现 `src/freegraph/contracts/types.py` 的 `StateDict` 与 `Command`：`StateDict: TypeAlias = dict[str, Any]`（`TypeAlias` 取自**标准库** `typing`，Python 3.10 已有；**不得**写成新造类、**不得**支持 `StateDict[MySchema]` 参数化）；`Command` 用 `@dataclass(frozen=True, slots=True, kw_only=True)`，字段 `goto: str | Sequence[str] | None = None`、`update: StateDict | None = None`、`resume: Any | None = None`，类级常量 `PARENT: ClassVar[Literal["__parent__"]] = "__parent__"`；在 `__post_init__` 中当三者**全为 `None`** 时抛 `FreegraphError`；**不归一化** `goto`（传元组存元组、传列表存列表）；docstring MUST 写明「浅不可变」（`update` 装的是 dict、`goto` 可能装 list，其内容仍可变）+「运行时（F9P1）解释 `goto` 时 MUST 先判 `isinstance(x, str)` —— `str` 本身也是 `Sequence[str]`」
- [X] T009 [US1] 实现 `src/freegraph/contracts/types.py` 的 `StateSnapshot` 与 `RunConfig`（同一文件，与 T008 串行）：`StateSnapshot` 七字段**全部必填、无默认值** —— `values: StateDict`、`next: tuple[str, ...]`、`config: RunConfig`、`metadata: Mapping[str, Any]`、`created_at: str`（UTC ISO-8601）、`tasks: tuple[Any, ...]`、`interrupts: tuple[Any, ...]`；`RunConfig` 四字段**全部可选** —— `thread_id: str | None = None`、`context: Any = None`、`metadata: Mapping[str, Any] = field(default_factory=dict)`、`tags: Sequence[str] = field(default_factory=tuple)`；**`Mapping` / `Sequence` MUST 从 `collections.abc` 导入**（`typing.Mapping` 已废弃，且会让 `get_type_hints` 的 repr 与 API 快照不一致）；实现 `@classmethod from_dict(cls, d: Mapping[str, Any], *, ignore_unknown: bool = False) -> "RunConfig"`：用 `dataclasses.fields(cls)` 取字段名做未知键比对（**不得**硬编码字段名清单），出现四字段之外的键时默认抛 `FreegraphError` 并在消息中点名该键，`ignore_unknown=True` 时忽略未知键；**容器防御性拷贝（范围已定）**——`StateSnapshot.__post_init__` **只拷 `metadata`**（`object.__setattr__(self, "metadata", dict(metadata))`），`RunConfig.__post_init__` 拷 `metadata` + `tags`（`object.__setattr__(self, "metadata", dict(metadata))` 与 `object.__setattr__(self, "tags", tuple(tags))`；`frozen=True` 下普通赋值会抛 `FrozenInstanceError`，故 MUST 用 `object.__setattr__`），使构造后本对象持有的容器与调用方传入的**不是同一个对象**（I-16）；拷贝为**浅拷贝**（嵌套容器不深拷）；**快照没有 `tags` 字段 —— 不得对其做拷贝或断言**；**两个类型的 `__post_init__` MUST NOT 校验值**（只做类型注解：不得因 `created_at` 格式不符或 `thread_id` 类型不符而抛错）；docstring MUST 写明「浅不可变」与「**本类不可哈希**（`hash()` 抛 `TypeError`，因 `metadata` 装的是 dict）」
- [X] T010 [US1] 在 `src/freegraph/contracts/__init__.py` 中再导出 `StateDict` / `Command` / `StateSnapshot` / `RunConfig` / `FreegraphError` 五个符号，并把 `__all__` 设为这 5 个名字（**三个子类由 US2 追加后补齐为 8 个** —— 本阶段不得提前写入尚未存在的符号）

**Checkpoint**: `python3 -m pytest tests/contracts/test_types.py -q` 全绿；`PYTHONPATH=src python3 -c "from freegraph.contracts import StateDict, RunConfig"` 成功（freegraph 当前未安装，源码树导入须带 `PYTHONPATH=src`）。

---

## Phase 4: User Story 2 - 运行时实现者用统一异常语义表达失败 (Priority: P2)

**Goal**: 三个具名异常 `InvalidUpdateError` / `GraphRecursionError` / `GraphInterrupt` 派生自 `FreegraphError`，各带**冻结名**的结构化属性，上层只捕获基类即可兜住全部内核错误。

**Independent Test**: 断言三子异常同基类、基类派生 `Exception`、`except FreegraphError` 一次捕获三者；三个异常的结构化属性可直接读取，**无须解析错误消息**。

**覆盖的不变式**：I-12 / I-13

### 测试（先写，先失败）

- [X] T011 [P] [US2] 写 `tests/contracts/test_errors.py` 的三子异常断言（**先写、先失败**，覆盖 I-12 / I-13 与 **SC-005**；**文件首行 MUST 带署名头**）：① `issubclass(InvalidUpdateError, FreegraphError)` 等三条成立，且 `issubclass(FreegraphError, Exception)`；② `except FreegraphError` 逐一捕获三例（无一漏网），并**额外断言 `Command()` 抛出的 `FreegraphError` 也可被基类捕获**（SC-005 后半句 · 跨故事的一条）；③ `InvalidUpdateError(["a"]).invalid_keys == ("a",)`、`GraphRecursionError(25, 25).recursion_limit == 25` 且 `.current_step == 25`、`GraphInterrupt(payload).payload is payload`；④ `message` 缺省时自动生成一句摘要、可选关键字 `message="..."` 能覆盖；⑤ **默认摘要 MUST 为英文且点名未知 key**（US2 验收场景 3）：`str(InvalidUpdateError(["typo"]))` MUST 含 `typo`，且 MUST 为英文（断言 `re.search(r"[一-鿿]", msg) is None`）

### 实现

- [X] T012 [US2] 在 `src/freegraph/contracts/errors.py` 追加 `InvalidUpdateError` 与 `GraphRecursionError`（同一文件，与 T013 串行）：`InvalidUpdateError(invalid_keys: Iterable[str], *, message: str | None = None)` —— 属性 `invalid_keys` 存为 `tuple[str, ...]`；`GraphRecursionError(recursion_limit: int, current_step: int, *, message: str | None = None)` —— 属性 `recursion_limit` / `current_step`；两者 MUST 调 `super().__init__(message)` 并在 `message` 缺省时由属性自动生成一句人话摘要
- [X] T013 [US2] 在 `src/freegraph/contracts/errors.py` 追加 `GraphInterrupt(payload: Any, *, message: str | None = None)` —— 属性名 **`payload`**（冻结面）；本 Phase 的类型标注为 `Any`（**具体载荷类型属 F2P1** —— `Send` / `interrupt` 归 F2P1，此刻不存在可标注的类型，自造载荷类会违反 FR-015 的公开符号面约束），但 **docstring MUST 写明结构约定**：载荷对象须带 `.value` 与 `.id`（契约 C17）
- [X] T014 [US2] 在 `src/freegraph/contracts/__init__.py` 追加再导出 `InvalidUpdateError` / `GraphRecursionError` / `GraphInterrupt`，并把 `__all__` 补齐为**恰好 8 个**符号：`StateDict` / `Command` / `StateSnapshot` / `RunConfig` / `FreegraphError` / `InvalidUpdateError` / `GraphRecursionError` / `GraphInterrupt`

**Checkpoint**: `python3 -m pytest tests/contracts/test_errors.py -q` 全绿。

---

## Phase 5: User Story 3 - 契约层可被单独审计与冻结 (Priority: P3)

**Goal**: 把八条红线变成**可自动判定**的断言：顶层包惰性、契约层零内部 import、零第三方 import、依赖闭包**为空集**、零环境变量零出站、署名头、`py.typed`、公开符号面恰 8 个；并落两份**活文档**（`THIRD_PARTY_NOTICES` + API 兼容矩阵）。

**Independent Test**: 静态扫描断言契约层导入图中**零**条边指向 freegraph 内部模块、**零**条指向第三方；在子进程中检查 `import freegraph` 与 `import freegraph.contracts` 之后的 `sys.modules` 清单；断言兼容矩阵覆盖全部 8 个公开符号。

**覆盖的门禁**：G1 / G2 / G3 / G4 / G5 / G6 / G7 / G8

### 测试（本 Phase 无新源文件，全部是断言）

- [X] T015 [US3] 写 `tests/contracts/test_architecture.py` 的 **G1（顶层包惰性）· SC-006**（**文件首行 MUST 带署名头**）：用 `subprocess.run([sys.executable, "-c", <内联脚本>], env={**os.environ, "PYTHONPATH": str(src_dir)})` 在**子进程**中分别导入 `freegraph` 与 `freegraph.contracts`，断言：前者已加载的 `freegraph.*` 模块**恰为** `['freegraph']`；后者**不含**任何内部层模块（`freegraph.runtime` / `freegraph.graph` / `freegraph.persistence` / `freegraph.observability`），而契约层自身子模块（`freegraph.contracts.types` / `freegraph.contracts.errors`）**不受限**（子模块改名不必改这条断言）。**必须用子进程** —— 测试进程已被 pytest 污染，同进程 `sys.modules` 不可作依据
- [X] T016 [US3] 在 `tests/contracts/test_architecture.py` 追加 **G2（零内部 import + 零第三方 import）· SC-003** 与 **G4（零环境变量 + 零出站）**：用标准库 `ast` 解析 `src/freegraph/contracts/**/*.py` 的 `Import` / `ImportFrom`，断言① **绝对导入**（`ImportFrom.level == 0`）的目标**不得**为 `freegraph` 顶层或任何**包外** `freegraph.*`；**包内相对导入合法**（`level >= 1` 且解析后落在 `freegraph.contracts` 内——`contracts/__init__.py` 的再导出**必须**用它）；`level >= 2`（跳到包外，如 `from ..runtime import X`）⇒ 违规；② 目标**只允许标准库**（判据：`module` ∈ `sys.stdlib_module_names`，Python 3.11+ 标准库清单）—— **任何第三方都禁止**（含已剥离的 `typing_extensions`：最低 Python ≥3.11 后 `Self` / `NotRequired` 等均在标准库内）（`from langchain_core.runnables import RunnableConfig` 这类「复用 LangChain 类型」的导入 MUST 被抓到，它是 FR-005 / FR-007 的红线所在，而 G3 只在隔离环境生效、不是常驻回归）；③ 源码中不出现 `os.environ` / `os.getenv` / `os.environb` / `socket` / `http` / `urllib` / `requests` / `httpx` / `subprocess` / `langchain*` / `langsmith` / `langgraph`——**判定 MUST 以 AST 为准**（只查 `Import`/`ImportFrom` 的模块名与 `Attribute`/`Name` 访问），**MUST NOT** 用纯文本子串匹配（否则 docstring 里提到 `subprocess` / `urllib` 会假阳性）。**扫描逻辑 MUST 抽成可传入目录的纯函数**（如 `scan_imports(contracts_dir) -> list`），供 T022 的门禁自检复用
- [X] T017 [US3] 在 `tests/contracts/test_architecture.py` 追加 **G5（署名头）· SC-007** 与 **G6（`py.typed`）**：遍历本 Phase 新建的每个源文件（`src/freegraph/__init__.py` + `src/freegraph/contracts/` 下三个文件 + **`tests/contracts/` 下四个文件**：`conftest.py` / `test_types.py` / `test_errors.py` / `test_architecture.py`），断言首行**逐字**等于 `# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph`，并用 `ast` 断言模块 docstring 是**首个语句**；G6 断言 `src/freegraph/py.typed` 存在且**内容为空**
- [X] T018 [US3] 在 `tests/contracts/test_architecture.py` 追加 **G7（公开符号面）· I-15**：断言 `set(freegraph.contracts.__all__)` **集合等于** 8 个名字（**集合断言**才能抓住「偷偷多导出一个」；只断言「都包含」会漏）、每个名字都能 `getattr` 取到，且契约层**不得**出现名为 `Send` / `interrupt` 的公开符号
- [X] T019 [US3] 在 `tests/contracts/test_architecture.py` 追加 **G3（依赖闭包 + 许可证白名单）· SC-002**：用 `importlib.metadata.requires("freegraph")` 递归展开闭包，拆成**两条**断言 —— ① **基础安装闭包**（**须剥离 extras marker**：解析 `Requires-Dist` 时丢弃 `; extra == "..."` 条件）**MUST 为空集**，且不含 `langsmith` / `langchain` / `langchain-core` / `langgraph` / `langgraph-core` / `typing-extensions`；② **extras 变体闭包**（若存在）**只含**宪法依赖白名单内的包（`typing-extensions` / `pydantic` / `ormsgpack` / `opentelemetry-api` / `opentelemetry-sdk`；`[png]` 的 mermaid 相关包由 **F3P1** 定点后补入该清单）—— **extras 由 F3P1 引入，本 Phase 无 extras，该条在无 extras 时为空断言**；**并对闭包内每个包断言许可证 ∈ {MIT, Apache-2.0, BSD-2/3, PSF}**（宪法质量门禁第 2 条：递归展开 + **许可证白名单校验**；不得默认「闭包小就安全」）——许可证信息取自 `importlib.metadata.metadata(pkg).get("License")` / `License-Expression`，取不到时该断言 `skip` 并提示；**freegraph 未安装（无 dist-info）时该用例 MUST `skip` 而非失败** —— 这条门禁在本地**恒 skip**，真正生效的是 **T023** 的隔离环境脚本（quickstart §2.2）；F3P1 接 CI 时必须先装包，否则这条门禁形同虚设
- [X] T020 [P] [US3] **复核并对齐**两份**活文档**（**FR-016**；两份文件已先行起草，本任务的动作是**核对内容是否与本层实际交付一致并补齐缺口**，不是从零创建）：① 仓库根 `THIRD_PARTY_NOTICES` —— 核对 §1「引入的第三方代码」为空表 + 说明（本 Phase 源码无第三方代码）、§2「第三方运行时依赖」**表为空**（基础安装零第三方依赖——登记一个已剥离的包同样是登记不准）、§3「互操作与 affiliation 声明」含「兼容意图为互操作，不构成 affiliation」、§4「维护规则」齐全；② `README.md` 的「## API 兼容矩阵」章节 —— 核对表格四列（freegraph 符号 / 对应上游符号 / 等价程度 / 差异说明）**逐个列出 8 个符号**：`StateDict`=行为等价（上游 1.2.19 无同名公开符号）、`Command`=部分等价（上游多 `graph` 字段、`goto` 可混 `Send`）、`StateSnapshot`=部分等价（上游 8 字段含 `parent_config`、freegraph 7 字段；`created_at` 上游可空、freegraph 必填）、`RunConfig`=**不支持**（刻意替代 `RunnableConfig`，字段集不同、`context` 独立通道）、`FreegraphError`=不支持（上游三个错误分属三棵继承树）、`InvalidUpdateError`/`GraphRecursionError`/`GraphInterrupt`=部分等价（同名同触发条件，freegraph 多暴露结构化属性），并附**证据来源**（截至 2026-11-05，LangGraph 1.2.19 / langchain-core 1.7.6 的 `文件:行号`）+「不构成 affiliation」声明；③ **README 顶部 MUST 含「独立实现、非 LangChain Inc. 产品」声明**（宪法原则 IX · 第三方商标禁令）——现有 README 的英文简介「maintaining LangChain compatibility」措辞**保留不改**（描述的是 API 兼容，非「与 LangChain 共存」），但 MUST 另有上述独立实现声明；**不得**新建独立文件（`README.md` 已在 sdist 的 `only-include` 里，无需改 `pyproject.toml`）
- [X] T021 [US3] 在 `tests/contracts/test_architecture.py` 追加 **G8（文档合规门禁）**：断言仓库根 `THIRD_PARTY_NOTICES` 存在；解析 `README.md` 的「## API 兼容矩阵」章节（正则 MUST 用 `r"^## API 兼容矩阵\s*$(.*?)(?=^## |\Z)"` —— 该章节是 README 的**最后一个** `##` 章节，其后没有下一个 `##`，用 `^## ` 收尾会**匹配失败**），取表格**第一列**的反引号符号名，断言其集合**等于**契约层的 8 个公开符号；断言该章节含「不构成 affiliation」字样 —— 使「文档有没有跟上代码」这条最容易掉队的门禁变成**可执行断言**；**另断言 `README.md` 全文（含顶部）含「独立实现、非 LangChain Inc. 产品」字样**（宪法原则 IX · 第三方商标禁令 —— 该声明按 T020 放在 README **顶部**、落在矩阵章节**之外**，故不能靠上面的章节解析覆盖，必须扫全文）；**另断言 `THIRD_PARTY_NOTICES` 的 §2「第三方运行时依赖」表**无**已登记的运行时依赖**（原则 X 的依赖登记义务 = 登记**实际存在**的依赖；判定只看**表格数据行**，章节正文对剥离历史的说明性提及不计入）
- [X] T022 [US3] 在 `tests/contracts/test_architecture.py` 追加**门禁自检**（US3 验收场景 4「刻意引入违规改动 → 断言失败并阻断合入」）：用 `tmp_path` 造**三个**含违规改动的临时契约层目录 —— ① 含第三方导入（`from langchain_core.runnables import RunnableConfig`）② 含**内部**导入（`from freegraph.runtime import X`）与包外相对导入（`from ..runtime import X`）③ 含**属性类违规**（`import os` + `os.environ["LANGSMITH_API_KEY"]` 读取）——分别喂给 T016 抽出的扫描纯函数，断言它**确实报出**对应违规（**① 与内部导入须分别验证**，否则无法证明两条判定各自有效；**③ 用于证明 G4 的属性类判定确实有效** —— 否则「零环境变量 / 零出站」这条原则 I 门禁的有效性未被验证）；再对真实目录断言**无**违规 —— 证明门禁真的有效，而不是恰好没触发
- [X] T023 [US3] 执行 `specs/001-p01-contracts-core/quickstart.md` 第 2 节的**隔离环境验收 · SC-001**：建 venv（`python3 -m venv /tmp/fg-verify`）→ `pip install .` → 依赖闭包脚本 → 导入耗时脚本（断言 < 300 ms）→ 两条 `sys.modules` 清单 → 静态门禁脚本 → 第 3 节冒烟脚本；**先创建 `harness/features/F1P1/` 目录**（当前不存在），把**真实输出**逐条采集下来（**本任务只负责采集原始输出**；成文归 T024）
- [X] T024 [US3] 在 `harness/features/F1P1/manual-verification.md` 落**人工验证记录**（原则 V 人工门禁）：五段齐全 —— **环境**（Python 版本 / 平台 / freegraph 版本 / pytest 版本）、**步骤**（照 `specs/001-p01-contracts-core/quickstart.md` 第 1–3 节）、**实际输出**（粘贴 T023 采集的**真实**输出，非「符合预期」；单测输出取 `python3 -m pytest tests/contracts -q` 的原始末行）、**结论**、**遗留问题**；**双跑子项在本 Phase 不适用**（无运行时、无模型调用）须在「结论」段显式记一句，非忽略
- [X] T025 [US3] 在 `harness/features/F1P1/manual-verification.md` 追加「**类型冻结记录**」一节（SC-008）：逐个列出 8 个符号的**名称 / 字段清单 / 字段类型 / 结构化属性名 / 常量值 / 表示形态**，内容 MUST 与 `specs/001-p01-contracts-core/contracts/public-api.md` 的「冻结面速查」一致（该文件是冻结面的**唯一规范源**），并注明「后续 30 个 Phase 的唯一引用基准」

**Checkpoint**: 三条用户故事均可独立验证；八条门禁全部有可执行断言且全绿；门禁自检证明门禁有效。

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 跨故事的一致性与交付完整性收口。

- [X] T026 [P] 复核 `src/freegraph/__init__.py` 与 `src/freegraph/contracts/` 下三个 `.py` 文件：署名头逐字正确、模块 docstring 为首个语句、无 `TODO` / `FIXME` / `print(` / `breakpoint()` 等调试残留
- [X] T027 [P] 核对交付物齐备：`specs/001-p01-contracts-core/` 下 `plan.md` / `research.md` / `data-model.md` / `contracts/public-api.md` / `contracts/architecture-gates.md` / `quickstart.md` / `checklists/requirements.md` / `tasks.md` 均存在；`THIRD_PARTY_NOTICES` 存在于仓库根**且其 §2 无已登记的运行时依赖**；`README.md` 含「## API 兼容矩阵」章节**且含「独立实现、非 LangChain Inc. 产品」声明**；并用 `git diff HEAD -- pyproject.toml` 验证**为空**（**须带 `HEAD`** —— 裸 `git diff` 不覆盖已 `git add` 的改动；依赖白名单仍为 `dependencies = []`（**零第三方运行时依赖**），**未新增 extras、未新增第二发行包** —— 属 F3P1）
- [X] T028 [US3] 跑全量验证：`python3 -m pytest tests/contracts -q` 全绿，且 `specs/001-p01-contracts-core/quickstart.md` 第 1–3 节全部通过（两处都要，不能只跑单测）
- [X] T029 [US3] 在 `harness/features/F1P1/manual-verification.md` 补记「后续 Phase 注意事项」：`GraphInterrupt.payload` 的**具体元素类型**归 F2P1 收紧（属性名与载荷结构已冻结，不得改动）；`RunConfig` 四字段与 `StateSnapshot` 七字段的**字段注解已随字段一并冻结**（F4P1 / F8P3 只能**新增字段**、不得改动已有字段的注解）；`tasks` / `interrupts` **元素类型**归 F2P1；节点名 `__parent__` 属**保留名**，校验归 F7P2 / F9P1；`invoke` 入口「容忍裸 dict」行为归 F7P3；架构断言接入 CI 流水线归 F3P1；兼容矩阵与 `THIRD_PARTY_NOTICES` 的**补全与定稿**归 F24P1（**建立与本层填写**已在本 Phase 完成）

---

## 追溯矩阵（spec 条目 → 任务）

> 供 `/speckit.analyse` 机械核对：spec 的每一条 FR / SC 都有落点，无遗漏、无悬空。

### 功能需求（FR）

| FR | 摘要 | 落点任务 |
|---|---|---|
| FR-001 | 契约层导入成功且无副作用 | T002 · T010 · T014 · T015 · T016 |
| FR-002 | 状态字典（稀疏、`dict` 兼容、不参数化） | T007 · T008 |
| FR-003 | 命令原语（三语义位、`PARENT`、填写规则） | T007 · T008 |
| FR-004 | 状态快照（七字段与类型） | T007 · T009 |
| FR-005 | 运行配置（四字段、不复用 LangChain 类型） | T007 · T009 · T016 |
| FR-006 | 统一异常体系（基类 + 三子类 + 结构化属性） | T005 · T006 · T011 · T012 · T013 |
| FR-007 | 第三方依赖**为零**（基础安装闭包为空集） | T016 · T019 · T020 · T027 |
| FR-008 | 契约层零内部 import | T016 |
| FR-009 | 完整类型注解 + `py.typed` | T003 · T007 · T017 |
| FR-010 | 每个新源文件携带署名头（含 `tests/`） | T001 · T002 · T007 · T011 · T015 · T017 · T026 |
| FR-011 | 顶层包保持惰性 | T004 · T015 |
| FR-012 | 冻结定义落盘记入 Phase 验收记录 | T025 |
| FR-013 | 零环境变量 + 零出站 | T016 |
| FR-014 | 四个类型的表示形态冻结 | T008 · T009 · T010 · T014 |
| FR-015 | 公开符号面恰为 8 个 | T010 · T014 · T018 |
| FR-016 | 两份活文档（`THIRD_PARTY_NOTICES` + 兼容矩阵） | T020 · T021 · T027 · T029 |

### 成功标准（SC）

| SC | 摘要 | 落点任务 |
|---|---|---|
| SC-001 | 隔离环境导入成功且 < 300 ms | T023 |
| SC-002 | 依赖闭包**为空集**（基础安装） | T019 · T023 |
| SC-003 | AST 扫描：零内部 import 边 | T016 |
| SC-004 | 四类型字段与注解 100% 覆盖 | T007 |
| SC-005 | 异常结构约束与属性可读（+ 三语义位全缺省抛出的错误可被基类捕获） | T011 · T007 |
| SC-006 | 顶层包惰性（`sys.modules` 判定） | T015 |
| SC-007 | 署名头 100% 且 docstring 首个语句 | T017 |
| SC-008 | 冻结记录写入 Phase 验收记录 | T025 |

> **全量验证落点**：T028（跑全量单测 + quickstart 第 1–3 节）覆盖 **SC-001…SC-007** 的整体交付确认。

### 不变式（data-model.md I-01…I-16）与门禁（architecture-gates.md G1…G8）

| 编号 | 落点任务 | 编号 | 落点任务 |
|---|---|---|---|
| I-01 `StateDict` 等价 | T007 | I-09 `from_dict` 严格 | T007 |
| I-02 `Command()` 抛错 | T007 | I-10 `ignore_unknown` | T007 |
| I-03 语义位任意组合 | T007 | I-11 `RunConfig` 全空构造 | T007 |
| I-04 `PARENT` 值 | T007 | I-12 三子异常同基类 | T011 |
| I-05 冻结语义 | T007 | I-13 结构化属性 | T011 |
| I-06 注解可解析 | T007 | I-14 空 vs 未提供 | T007 |
| I-07 七字段必填 | T007 | I-15 公开符号面 | T018 |
| I-08 `created_at` 格式 | T007 | I-16 容器防御性拷贝 | T007 · T009 |
| G1 顶层包惰性 | T015 | G5 署名头 | T017 |
| G2 零内部 import + 零第三方 | T016 · T022 | G6 `py.typed` | T017 |
| G3 依赖闭包 | T019 · T023 | G7 公开符号面 | T018 |
| G4 零环境变量零出站 | T016 | G8 文档合规门禁 | T021 |

### 使能任务（无直接 FR/SC，但为其余任务铺路）

| 任务 | 使能对象 |
|---|---|
| T001 `conftest.py` 与 fixture | T007 · T011 · T015–T022 全部测试 |
| T002 三个模块骨架（署名头 + docstring） | T006 · T008 · T009 · T012 · T013 · T026 |

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 —— 可立即开始
- **Foundational (Phase 2)**: 依赖 Phase 1 —— **阻塞** US1 与 US2（`Command` 的构造期校验 MUST 抛 `FreegraphError`）
- **User Stories (Phase 3+)**: 全部依赖 Phase 2 完成
  - US1 与 US2 的**源文件不同**（`types.py` vs `errors.py`），可并行；US1 的 `__init__.py` 再导出依赖 US1 实现 + Phase 2 基类
  - US3 的**测试**依赖 US1 + US2 完成（`__all__` 恰 8 个的断言需要三子类就位）
- **Polish (Phase 6)**: 依赖全部目标用户故事完成

### User Story Dependencies

- **User Story 1 (P1)**: 依赖 Foundational（`FreegraphError` 基类）—— 不依赖其他故事。**环境口径**：US1 的 checkpoint 在**源码树**（`PYTHONPATH=src`）下执行；spec 要求的「只装 freegraph 基础包」的**隔离环境**同等验收由 **T023**（US3 的架构门禁批次）执行
- **User Story 2 (P2)**: 依赖 Foundational（基类本身）—— 三个子类不依赖 US1；但 US1 的 `Command` 校验需要 US2 的基类，故**基类被放在基础阶段**而非 US2 阶段
- **User Story 3 (P3)**: 依赖 US1 + US2（`__all__` 集合断言与兼容矩阵的 8 个符号都需要全部就位）—— 仍可独立测试（门禁断言不依赖运行时）

### Within Each User Story

- **测试 MUST 先写并先失败**，再写实现（spec 的 SC-002…SC-007 均要求可自动判定的断言）
- 同一文件内的任务**不可并行**：`types.py`（T008 → T009）、`errors.py`（T006 → T012 → T013）、`test_architecture.py`（T015 → T016 → T017 → T018 → T019 → T021 → T022）
- 实现完成后必须**立刻**跑该故事的测试文件（checkpoint）
- 跨文件的任务可并行：`types.py` 与 `__init__.py` 之间有依赖（先类型后导出）

### Parallel Opportunities

> 与任务清单里的 `[P]` 标记**逐条一致**（正文声称可并行的任务均已带 `[P]`）。

- Phase 1：T003 / T004 可并行（不同文件、只读或各自编辑）
- Phase 2：T005 可与 Phase 1 的 T003 / T004 并行；T006 可与 Phase 1 的 T003 / T004 并行（`errors.py` vs `__init__.py` / `py.typed`）
- Phase 3：T007 可与 Phase 2 的 T006 并行（不同文件）；T008 可与 T007 并行（`types.py` vs `test_types.py`）
- Phase 4：T011 可与 Phase 3 的 T007 / T008 并行（`test_errors.py` vs `test_types.py` vs `types.py`）
- Phase 5：T015…T022 全部在 `test_architecture.py`（T020 改文档除外）—— **串行**；T020（写文档）可与 T015–T019 并行
- **本项目为单人串行推进**（立项书 §5.2），并行标注仅供将来多人协作参考

---

## Parallel Example: User Story 1

```bash
# 并行组 1：写测试（先失败）与写基础阶段实现
Task: "写 tests/contracts/test_types.py 的全部断言（覆盖 I-01…I-11、I-14、I-16 与 SC-004）"
Task: "实现 FreegraphError 于 src/freegraph/contracts/errors.py"

# 并行组 2：类型实现（同一文件，串行）
Task: "实现 src/freegraph/contracts/types.py 的 StateDict 与 Command"
Task: "实现 src/freegraph/contracts/types.py 的 StateSnapshot 与 RunConfig（同一文件，与前一条串行）"

# 并行组 3：门面再导出（依赖组 2）
Task: "在 src/freegraph/contracts/__init__.py 中再导出 5 个符号并设置 __all__"
```

---

## Implementation Strategy

### MVP First（User Story 1 优先）

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational（**关键** —— 阻塞所有故事）
3. 完成 Phase 3: User Story 1
4. **停下并验证**：单独跑 `python3 -m pytest tests/contracts/test_types.py -q`，并执行 `from freegraph.contracts import StateDict, RunConfig` 冒烟
5. 此时本 Phase 已交付「四类型可被外部引用」这一核心价值 —— freechain 已能只取契约

### Incremental Delivery

1. Setup + Foundational → 地基就位
2. US1 → 单独验证 → 四类型可引用（**MVP**）
3. US2 → 单独验证 → 异常族完整，`__all__` 补齐为 8 个
4. US3 → 单独验证 → 八条门禁全部可自动判定 + 两份活文档落盘
5. Polish → 冻结记录 + 人工验证记录落盘 → **Phase 验收完成**

### Parallel Team Strategy（本项目为单人，此处仅备将来多人协作）

1. 团队共同完成 Setup + Foundational
2. 之后：成员 A 做 US1（`types.py`）、成员 B 做 US2（`errors.py` 的三子类）、成员 C 准备 US3 的门禁测试骨架与活文档
3. US3 的最终断言须等 A、B 合流后跑

---

## Notes

- **[P]** = 不同文件、无依赖；同文件内的任务**不得**标 [P]
- **[Story]** 标签映射到 spec.md 的用户故事，供追溯
- 每个用户故事都应**独立可完成、可测试**
- **提交**：由实现者按 Phase 提交（**文档与代码 MUST 同批提交** —— 宪法原则 VI）；提交粒度建议「一个 Phase 一次提交」
- **规范源**：`specs/001-p01-contracts-core/contracts/public-api.md` 是**冻结面**（符号名 / 字段名 / 属性名 / 常量值 / 行为）的唯一规范源；spec.md 是**需求**来源、data-model.md 是**数据模型**来源 —— 三处若有冲突，以 public-api.md 为准
- 遇到任一 checkpoint 即停下验证该故事
- 避免：模糊任务、同文件冲突、跨故事依赖破坏独立性
- **本 Phase 不交付任何运行时行为** —— 出现调度 / channel / 状态读写即越界（spec Out of Scope）
- **不得**改动 `pyproject.toml` 的依赖白名单、**不得**新增 extras、**不得**新增第二发行包（D1 已拍板）
  > **2026-11-05 实施期变更（已获发起者批准）**：依赖白名单由 `["typing-extensions>=4.7.0"]`
  > 改为 **`[]`**（基础安装零第三方运行时依赖），`requires-python` 由 `>=3.10` 抬至 **`>=3.11`**。
  > 起因与依据见 `research.md` **D-21**、spec Clarifications「Session 2026-11-05（实现阶段 ·
  > 依赖剥离与最低版本上调）」、宪法修订记录 **v1.2.0**。
  > **已冻结的公开面（8 个符号 / 字段名 / 字段注解 / 行为）完全未变**——
  > 本次只改**依赖声明**与**解释器版本下限**。**未新增 extras、未新增第二发行包**（不变）。
- **不得**在本 Phase 导出 `Send` / `interrupt`（归 F2P1），**不得**提前交付 `freegraph/graph.py` 门面（归 F2P2）
- **不得**跳过文档合规门禁（FR-016 / G8）：`THIRD_PARTY_NOTICES` 与兼容矩阵 MUST 在本 Phase 就建立并填入本层内容，**不得**以「F24P1 会补」为由留空
- **不得**再引入 `typing_extensions`（已剥离；最低 Python ≥3.11 后 `Self` / `NotRequired` /
  `Required` / `TypeVarTuple` / `Unpack` / `LiteralString` / `dataclass_transform` 均在标准库内）
