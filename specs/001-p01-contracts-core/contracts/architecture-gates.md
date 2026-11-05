# 架构门禁契约（architecture-gates.md）

**Feature**: F1P1 · 契约层骨架 · **Date**: 2026-11-05
**依据**: spec FR-001 / FR-007 / FR-008 / FR-009 / FR-010 / FR-011 / FR-013 · SC-002 / SC-003 / SC-006 / SC-007 · 宪法 ARCH-2 与原则 I / II / X

> 本文件把「架构红线」写成**可自动判定**的断言。
> 断言的**执行位置**是 pytest（`tests/contracts/test_architecture.py`）；
> **接入 CI 流水线**归 **F3P1**（本 Phase 只交付断言，不动流水线）。

---

## 门禁总表

| # | 门禁 | 判定方式 | 判定位置 | 失败后果 |
|---|---|---|---|---|
| **G1** | 顶层包**惰性**：`import freegraph` 不连带加载任何子模块 | 子进程 `sys.modules` 快照 | 单测 | 阻断合入 |
| **G2** | 契约层**零** freegraph 内部模块 import + **零**第三方 import（**仅标准库**获准） | `ast` 静态扫描 | 单测 | 阻断合入 |
| **G3** | 依赖闭包：**基础安装（无 extras）**为**空集**；**extras 变体**的闭包只含宪法依赖白名单内的包 | `importlib.metadata.requires()` 递归展开 | 隔离环境验收 | 阻断合入 |
| **G4** | **零环境变量读取** + **零出站** | `ast` 扫描 `os.environ` / `os.getenv` / 网络模块 | 单测 | 阻断合入 |
| **G5** | **每个新源文件带署名头**且 docstring 为首个语句 | AST + 文本扫描 | 单测 | 阻断合入 |
| **G6** | `py.typed` 存在且为空（PEP 561） | 文件存在性 + 内容断言 | 单测 | 阻断合入 |
| **G7** | 公开符号面**恰为 8 个** | `__all__` 集合相等 | 单测 | 阻断合入 |
| **G8** | **文档合规门禁**：兼容矩阵覆盖全部 8 个公开符号 + `THIRD_PARTY_NOTICES` 存在 | 解析 `README.md` 矩阵章节 + 文件存在性 | 单测 | 阻断合入 |

---

## G1 · 顶层包惰性

**契约**：`import freegraph` 后，`sys.modules` 中**不得**出现 `freegraph.contracts` / `freegraph.graph` / `freegraph.runtime` / `freegraph.persistence` / `freegraph.observability`。

**判定**：在**子进程**中执行（同进程已被 pytest 污染，不可用）：

```text
python -c "import freegraph, sys; print(sorted(m for m in sys.modules if m.startswith('freegraph')))"
→ 期望输出：['freegraph']
```

**延伸**（spec SC-006 后半句）：`import freegraph.contracts` 后，`sys.modules` 中**不含任何 freegraph 内部层模块**（契约层自身的子模块 `freegraph.contracts.types` / `freegraph.contracts.errors` 不受限）：

```text
python -c "import freegraph.contracts, sys; print(sorted(m for m in sys.modules if m.startswith('freegraph')))"
→ 期望输出：['freegraph', 'freegraph.contracts', 'freegraph.contracts.errors', 'freegraph.contracts.types']
```

> **判定口径（与 tasks.md T015 一致）**：对 `import freegraph` —— 已加载模块清单**恰为** `['freegraph']`；
> 对 `import freegraph.contracts` —— **不含任何内部层模块**即可（契约层自身的子模块名**不受限**，
> 故新增/改名子模块不必改这条断言）。上面两行是**当前**的预期输出，供人工核对，不是逐字比对基准。

**实现要点**：子进程须能定位 `src/` —— 注入 `PYTHONPATH=src`（不依赖 cwd，也不要求先 `pip install`）。

---

## G2 · 契约层零内部 import

**契约**：`src/freegraph/contracts/**` 的源码中**不得**出现指向 freegraph 内部层的 import（FR-008 / ARCH-2）。

**判定**：`ast` 静态扫描 `src/freegraph/contracts/**/*.py` 的 `Import` / `ImportFrom`：

| 目标模块 | 允许？ |
|---|---|
| `freegraph.contracts`（自身，包内绝对导入） | ✅ |
| **包内相对导入**（`from .types import ...` / `from . import types`，即 `ImportFrom.level ≥ 1` 且解析后落在 `freegraph.contracts` 内） | ✅ —— `contracts/__init__.py` 的再导出**必须**用它 |
| `freegraph`（顶层包） | ❌ —— 契约层连顶层包都不引，避免顶层包将来长东西时形成回边 |
| `freegraph.runtime` / `freegraph.graph` / `freegraph.persistence` / `freegraph.observability` / 任何**包外** `freegraph.*` | ❌ |
| 标准库（`dataclasses` / `typing` / `collections.abc` / `datetime` …） | ✅ —— 判据：`module` ∈ `sys.stdlib_module_names`（Python 3.10+ 的标准库清单） |
| **任何第三方** | ❌ —— 基础安装**零**第三方运行时依赖（FR-007 / 宪法 v1.2.0）；含 `langchain` / `langchain_core` / `langsmith` / `langgraph` 全系列，亦含 **已剥离的 `typing_extensions`**（最低 Python ≥3.11 后不再需要） |

> **判定口径（相对导入如何解析）**：`ImportFrom.level == 0` ⇒ 绝对导入，模块名直接参与上表比对；
> `level ≥ 1` ⇒ 相对导入，只在**本包内**解析（`level=1` 即 `freegraph.contracts.*`），故**合法**；
> 若相对导入试图跳到包外（`from ..runtime import X`，即 `level ≥ 2`）⇒ **违规**。

> **为什么必须把第三方也挡掉**：FR-005 明令「MUST NOT 复用 LangChain 家族的运行配置类型（复用即把
> `langsmith` 拖回依赖树）」，FR-007 明令「契约层 MUST **零**第三方运行时依赖」——
> 而 `from langchain_core.runnables import RunnableConfig` **既不匹配 `freegraph.*`**，
> **也不是标准库**，若 G2 只拦 `freegraph.*`，这条红线**根本不会被任何断言抓到**。
> G3（依赖闭包）虽能抓到，但它是**隔离环境**断言（本地恒 skip），不是常驻回归。

**为什么用静态扫描而非运行时观测**：运行时探测只能发现「本次导入真的发生了」；静态扫描能发现「代码里写了但当前路径没走到」的隐患——正是 ARCH-2 要拦的那类。

**被否的备选**：`import-linter` / `grimp` 等工具（新依赖，违反 FR-007，且规则很简单，自写更省）。

---

## G3 · 依赖闭包为空集（零第三方运行时依赖）

**契约**：递归展开 freegraph 自身声明的依赖后，**基础安装（不含任何 extras 变体）**的闭包
**MUST 为空集**——无 `langsmith` / `langchain*` / `langgraph*`，亦无 `typing-extensions`
（SC-002 / 宪法原则 I / 宪法 v1.2.0）。

> **2026-11-05 变更**：本门禁原为「闭包 == `{typing-extensions}`」，
> 现改为「闭包 == **空集**」——`typing-extensions` 已从基础安装剥离，
> 最低 Python 版本抬至 **3.11**（详见 `research.md` D-21 与宪法修订记录 v1.2.0）。

> **口径（基础安装 vs extras 变体）**：SC-002 只约束**基础安装**的闭包 —— 宪法依赖白名单允许
> `pydantic` / `ormsgpack` / `opentelemetry-*` / mermaid 相关作为**可选 extra**（F3P1 引入），
> 故 extras 变体的闭包**另按白名单校验**（只允许白名单内的包，不得出现传染性许可证）。
> **基础安装的必装依赖白名单自宪法 v1.2.0 起为空**。
> **判定时须剥离 extras marker**：解析 `Requires-Dist` 时丢弃 `; extra == "..."` 条件，
> 否则基础安装的闭包会被 extras 依赖污染。
> （基础安装闭包为空时，该剥离是**必要**的——否则 extras 的依赖会被算进基础安装。）

**判定**：

```text
requires("freegraph")                       → 顶层声明（空）
  └─ 对每个依赖递归 requires(dep)            → 闭包
       → 闭包集合 == set()   （空集）
```

**执行位置**：**隔离环境**（需已安装的 dist-info 元数据）。未安装时该断言应 `skip`，**不是**失败。

**依赖白名单**（宪法）：**必装依赖 = 无**（自宪法 v1.2.0 起）；
可选 extras `pydantic` / `ormsgpack` / `opentelemetry-*` / mermaid 相关（本 Phase **不新增**任何 extra）。

**红线等价性**（宪法原则 I 的推论）：`langchain-core` 硬依赖 `langsmith`，故「依赖树无 `langsmith`」⟺「依赖树无 `langchain-core`」——二者是同一条红线，**不得只挡一层**。

**许可证白名单校验**（宪法质量门禁第 2 条：「递归展开 `importlib.metadata.requires()` + 许可证白名单校验」）：
闭包内每个包的许可证 MUST ∈ {MIT, Apache-2.0, BSD-2/3, PSF}；
MUST NOT 出现 Elastic-2.0 / AGPL / SSPL / BUSL 等传染性或限制性许可证（宪法原则 IX）。
本 Phase 的基础安装闭包为**空集** ⇒ 许可证白名单校验**恒通过**，
但**仍需显式断言**——不得默认「闭包小就安全」。
（一旦 F3P1 引入 extras，该断言即在 extras 闭包上变为实质断言。）

---

## G4 · 零环境变量 + 零出站

**契约**：freegraph 内核**不读任何环境变量**（`LANGSMITH_*` / `LANGCHAIN_*` / `LANGGRAPH_CLOUD_LICENSE_KEY` 一律不读），**不发起任何出站请求**（FR-013 / 宪法原则 I）。

**判定**：`ast` 扫描契约层源码，断言**不出现**：

| 禁止的模式 | 对应模块 / API |
|---|---|
| `os.environ` / `os.getenv` / `os.environb` | 环境变量读取 |
| `socket` / `http` / `urllib` / `requests` / `httpx` | 网络访问 |
| `subprocess` | 外部进程调用 |
| `langchain` / `langchain_core` / `langsmith` / `langgraph` | LangChain 家族（G2 已覆盖，此处双保险） |

**判定口径（避免假阳性）**：以 **AST** 为准——只检查 `Import` / `ImportFrom` 的**模块名**与
`Attribute` / `Name` 访问（如 `os.environ`），**不扫 docstring 与注释**。
纯文本子串匹配（`grep`）会把「docstring 里提到 `subprocess` / `urllib`」误判为违规——
`quickstart.md` §2.5 的手工复核脚本是**文本粗筛**，正式门禁以本文件的 AST 口径为准。

**注意**：本门禁针对**契约层**。全仓库范围的同类扫描归 F3P1 的 CI 门禁。

---

## G5 · 署名头

**契约**：本 Phase 新建的**每一个源文件**（含 `tests/` 下的 4 个测试文件）顶部 MUST 携带署名头（FR-010 / 宪法原则 X）：

```text
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
```

**判定**：

1. 文件首行**逐字**等于上述署名行；
2. 模块 docstring 仍是**首个语句**（署名行是注释，不构成语句 —— 用 AST 断言「模块体第一个非 docstring 节点之前没有别的语句」，即 `ast.get_docstring` 非空且 `body[0]` 是 docstring 表达式）；
3. 例外：`py.typed`（PEP 561 要求为空）与 `harness/demo/target.py`（只读基准，宪法原则 III 禁止修改）；
4. **扫描范围**：本 Phase 新建的 `src/freegraph/contracts/` 下 3 个文件 + `src/freegraph/__init__.py` + `tests/contracts/` 下 4 个文件（`conftest.py` / `test_types.py` / `test_errors.py` / `test_architecture.py`）。

**为什么必须逐文件带**：MIT 允许**整份或单个文件被复制**，而复制不会带走 `LICENSE` —— 署名必须随文件流动。这是「个人作品集」定位下署名头的兑现机制。

---

## G6 · `py.typed`（PEP 561）

**契约**：发行产物须带 `py.typed`（FR-009）。

**判定**：`src/freegraph/py.typed` **存在**且**内容为空**。

**为什么只在顶层放一个**：PEP 561 规定 `py.typed` 标记在**顶层包**即覆盖其全部子包；为子包再放一个既冗余、又会被部分工具误报。本 Phase **不新建** `contracts/py.typed`。

---

## G7 · 公开符号面恰为 8 个

**契约**：契约层的公开符号面 MUST 严格等于 FR-002…FR-006 列举的四个核心类型与异常体系（FR-015）。

**判定**：

1. `set(freegraph.contracts.__all__) == {8 个名字}` —— **集合相等**（不是「都包含」），才能抓住「偷偷多导出一个」；
2. 每个名字都能从 `freegraph.contracts` 直接取到；
3. 契约层模块内**不得**出现名为 `Send` / `interrupt` 的公开符号（它们归 F2P1）。

---

## G8 · 文档合规门禁（兼容矩阵 + 第三方归属）

**契约**：宪法原则 X + 立项书 §9.1 门禁 7 —— 「`THIRD_PARTY_NOTICES` 已登记、API 兼容矩阵已更新」
是**每个特性合入前必须全部通过**的质量门禁；「**MUST NOT** 在清单缺项的情况下宣布该特性完成」。

**判定**：

| 子项 | 判定方式 |
|---|---|
| `THIRD_PARTY_NOTICES` 存在 | 仓库根文件存在性 |
| 兼容矩阵覆盖全部公开符号 | 解析 `README.md` 的「## API 兼容矩阵」章节，取表格**第一列**的反引号符号名，断言其集合**等于**契约层的 8 个公开符号 |
| 互操作声明存在 | 断言兼容矩阵章节含「不构成 affiliation」字样 |

> **为什么可自动判定**：兼容矩阵的第一列就是公开符号名 —— 于是「文档有没有跟上代码」这条
> 最容易掉队的门禁，变成了**一条断言**，而不是靠人记得去更新文档。

**依据**：spec FR-016；宪法原则 X；立项书 §5.2（补全与定稿归 F24P1）/ §9.1 门禁 7。

---

## 门禁与断言的对应关系（供 tasks 直接引用）

| 门禁 | 对应 spec 条目 | 对应 SC | 落地文件 |
|---|---|---|---|
| G1 | FR-001 / FR-011 | SC-006 | `tests/contracts/test_architecture.py` |
| G2 | FR-005 / FR-007 / FR-008 | SC-003 | 同上 |
| G3 | FR-007 | SC-002 | `quickstart.md` 步骤 2（隔离环境）+ `test_architecture.py`（已安装时） |
| G4 | FR-013 | —（SC-002 归 G3） | `tests/contracts/test_architecture.py` |
| G5 | FR-010 | SC-007 | 同上 |
| G6 | FR-009 | —（`py.typed` 属 FR-009 的发行面部分） | 同上 |
| G7 | FR-015 | — | 同上 |
| G8 | FR-016 | — | 同上（另需 `README.md` 与仓库根文件） |

> **SC-004（字段与注解 100% 覆盖、可被 `typing.get_type_hints` 完整解析）不由 G6/G7 承担**——
> 它落在 `tests/contracts/test_types.py` 的注解断言（tasks T007）。

---

## 本 Phase **不**建立的门禁（避免越权）

| 事项 | 归属 | 理由 |
|---|---|---|
| CI 流水线接入 | F3P1 | 本 Phase 只交付断言，不动 `.github/workflows/` |
| 发行产物纯度扫描 | 已有 `harness/scripts/check_dist_purity.py` | 本 Phase 不产出新发行包 |
| 全仓库依赖与出站扫描 | F3P1 | 本 Phase 只扫契约层 |
| `target.py` 验收 | 原则 III | 依赖尚未交付的 F2P2 门面 + F7P3 运行时 |
| API 兼容矩阵与免责声明 | F24P1 | 原则 X；本 Phase 不新增互操作面 |
