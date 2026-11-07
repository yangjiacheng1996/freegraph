# 架构门禁契约（architecture-gates.md）

**功能块**: B2F2 · 公开 API 门面 `freegraph/graph.py` + API 签名快照 · **Date**: 2026-11-07
**权威来源**: [spec.md](../spec.md)（FR-002 / FR-006 / FR-010 / FR-011 / FR-012 / FR-013 / FR-014）·
[facade-api.md](./facade-api.md) §0 · [snapshot-format.md](./snapshot-format.md) · [research.md](../research.md)
**契约性质**: **冻结面** —— 每条门禁的**判定方式**即实现契约；改判定方式 = 改冻结面

> G1–G13 **继承自 B2F1**（`specs/b2f1-contracts-protocols/contracts/architecture-gates.md`），
> 本 feature **新增 G14–G20**。
> 本文件是**累计门禁清单**的当前版本；B2F1 的同名文件保留为历史快照。

---

## 0. 门禁总览

| # | 门禁 | 判定方式 | 状态 |
|---|---|---|---|
| **G1** | 顶层包**惰性**（`import freegraph` 不连带加载**任何** `freegraph.*` 子模块） | 子进程 `sys.modules` 快照 | **继承**（既有实现的实际口径**已是** `freegraph.*` 全量 —— `tests/contracts/test_architecture.py:534-538` 断言恰为 `['freegraph']`；**无须扩展**） |
| **G2** | 契约层**零**内部 import + **零**第三方 import | AST 静态扫描（两档范围） | 继承（**不适用于门面**——门面的依赖面由 G17 判） |
| **G3** | 依赖闭包**为空**（基础安装零第三方依赖） | `importlib.metadata.requires()` 递归展开 | 继承 |
| **G4** | **零**环境变量读取 + **零**出站 | AST 扫描 | 继承（**不适用于门面**——由 G17 判） |
| **G5** | 每个新源文件带署名头且 docstring 为首个语句 | 逐文件首行逐字相等 | 继承（**范围不变** · 硬编码清单**不扩** —— 本 feature 的新文件由 **G20** 覆盖，见 §3） |
| **G6** | `py.typed` 存在且为空（PEP 561） | 文件存在 + 大小 == 0 | 继承 |
| **G7** | 契约层公开符号面**恰为 18 个** | `__all__` **集合相等** | 继承（本 feature **不得**使其变红 ⇒ SC-015） |
| **G8** | 文档合规门禁（兼容矩阵覆盖**契约层 18 个**符号） | 逐符号覆盖 + 4 列 | 继承（**门面 7 个符号**的覆盖由 **G19** 判） |
| **G9** | **运行时环境基线**：typing 构件上限 = 3.11 | AST 扫描禁用构件 + CI 最低档 3.11 | 继承（**范围扩到门面三个模块**） |
| **G10** | 协议**纯抽象**（方法体只有 `...`） | AST | 继承（不适用于门面——门面零方法体） |
| **G11** | 结构化子类型判定可用 | 运行时 | 继承 |
| **G12** | 公开符号面**唯一权威**（扫 `**/public-api.md`） | 机器标记 `<!-- authority: yes\|no -->` | 继承（本 feature **不产出**该文件名 ⇒ 不受影响） |
| **G13** | **纯数据纪律**（数据类字段不得含可调用 / 对象类型） | 注解扫描 | 继承（不适用于门面——门面无数据类） |
| **G14** | 门面**零实现体** | AST：`class` / `def` / `async def` == 0 | **新增** |
| **G15** | 门面导出面**两处相等** | `__all__` 集合 **且** 公开名集合 == `facade-api.md` §0 | **新增** |
| **G16** | **API 快照**逐字节比对 + **可复现** + 更新入口**默认不生效** | 生成 vs 入库快照 | **新增** |
| **G17** | 门面**依赖卫生**（零**第三方** import / 零环境变量 / 零 I/O）——**两档**（内部 / 第三方） | AST 静态扫描 | **新增**（2026-11-07 分析轮修订：第三方档判据由「任何非标准库顶层包」**收窄**，见 §1 G17） |
| **G18** | 门面的**模块加载面**（不横依赖 L4 / L5 + 顶层包惰性） | 子进程 `sys.modules` 快照 | **新增** |
| **G19** | 兼容矩阵**覆盖门面 7 个符号**（各恰有一行 + 等价程度 + 上游来源） | 章节内取行 | **新增** |
| **G20** | 本 feature **新建源文件**的**署名头**（宪法原则 X） | 逐文件首行逐字相等 | **新增** |

---

## 1. 逐条判定细则

### G1 · 顶层包惰性（继承）

**判定**：**子进程**执行 `import freegraph` 后，`sys.modules` 中 `freegraph.*` 的**子模块数 == 0**
（只有 `freegraph` 本身）。

- **既有实现的实际口径（2026-11-07 复核）**：`tests/contracts/test_architecture.py:534-538`
  的断言已是「`import freegraph` 后已加载的 `freegraph.*` 模块**恰为** `['freegraph']`」
  ⇒ **本就覆盖任何 `freegraph.*` 子模块**，**无须扩展**、**无须改动 `tests/contracts/**`**
  （本 feature 的「既有门禁实现零改动」纪律因此得以保持）。
  门面一旦被顶层包 re-export（`from .graph import ...`），该断言即会失败 ⇒ 覆盖面天然到位，
  D1 决议第 ④ 条「契约层可独立消费」的收益仍然受保护。
- **必须子进程执行**：测试进程自身已导入 pytest，同进程 `sys.modules` 不可用。
- 门面视角的同一条纪律落在 **G18**（门面不横依赖 L4 / L5），两者**判定方式不同、作用域互补**。

### G14 · 门面零实现体（**新增**）

**判定**：AST 扫描 `src/freegraph/graph.py`：

1. `class` / `def` / `async def` 语句数 **== 0**（违规时报出**行号**与语句名）；
2. 模块体只允许：`Import` / `ImportFrom` / `Assign`（**常量赋值**：`START` / `END` / `__all__`）/
   `Expr`（仅模块 docstring）；出现其他语句类型即失败。

> **为什么用 AST 而不是「门面里没写实现」的人读**：FR-006 是 MUST 级约束，
> 而「门面看起来很薄」是主观判断——AST 判据可机械执行、可在 CI 中常驻。

### G15 · 门面导出面两处相等（**新增**）

**判定**：**两处同时**成立（任一不成立即失败）：

1. `freegraph.graph.__all__` 的**集合** == 从 `contracts/facade-api.md` §0 解析出的 7 个名字；
2. `freegraph.graph` 模块内**所有不以下划线开头的名字**的**集合** == 同一集合。

**解析规则**（`facade-api.md` §0 已写死）：只取 `from ... import (` 与配对 `)` 之间的行 →
跳过 `#` 注释行 → 每行取第一个逗号前的标识符 → 结果为**集合**（顺序不作判据）。

**落地分两段**（与 B2F1 的 G7 同构 —— 因 US1 先交付 3 个符号、US3 才补齐 7 个，
若一开始就按「恰 7 个」判定，US1–US2 期间**门禁恒红** ⇒ 阶段 Checkpoint 全都过不去）：

| 段 | 断言 | 启用时机 | 抓什么 |
|---|---|---|---|
| ① **子集段** | `set(__all__) ⊆ §0 解析出的 7 个` **且** 公开名集合 `⊆` 同一集合 | **始终启用**（Foundational 起） | 「偷偷多导出一个」 |
| ② **集合相等段** | `set(__all__) == §0 解析出的 7 个` **且** 公开名集合 `==` 同一集合 | **US3 交付完 7 个符号后**启用 | 「漏导出」 |

> **两段并存**：② 判「总数与内容」，① 判「不多不少」——二者**不可互相替代**。
> US3 启用 ② 之后，① 仍然有效（防止后续 feature 又加出第 8 个符号）。
>
> **两段各须一条自检**（§2 的「每条新增门禁 MUST 有自检用例」按**段**落地）：
> 子集段的自检 = 「塞一个第 8 个公开名 ⇒ 报出」；**集合相等段的自检 = 「删掉一个导出符号
> ⇒ 报出『漏导出』」**——子集段抓不到这一类，缺它则「漏导出」这条失效模式无保护。

> **为何两处都要**：`__all__` 单独判有漏洞——`from ._impl import helper` 未进 `__all__` 时，
> `from freegraph.graph import helper` 照样可用（spec Q1）。
>
> **为何期望值来自手写清单**：从**生成的**快照解析期望值 ⇒ 「代码 → 快照 → 快照 vs 代码」
> 的**循环论证**（research D-07）。

### G16 · API 快照比对（**新增**）

**判定**（三项）：

1. **逐字节比对**：由门面生成的快照文本 == `contracts/public-api-snapshot.txt` 的**字节**；
   不一致 ⇒ 失败并输出 **diff**（差异行数 ≥ 1）。
2. **可复现**：同一份代码**两次生成**的快照**逐字节相同**（差异字节数 == 0）。
3. **更新入口默认不生效**：常规执行 pytest **MUST NOT** 改动快照文件（文件内容逐字节不变）。

**配套自检**：MUST 含「故意改动某个参数名 ⇒ 断言比对**确实失败**」的自检用例——
用**人造命名空间**喂纯函数 `render_api_snapshot`（research D-10），**零副作用**。

### G17 · 门面依赖卫生（**新增** · **两档判据**）

**判定**：AST 扫描门面的**三个模块**（`graph.py` / `_stategraph.py` / `_primitives.py`）：

| 档 | 禁止项 | 判据 |
|---|---|---|
| ① **内部 import** | 指向 **L4（持久化）/ L5（可观测）** 的 import（**与 FR-014 ④ 同口径**） | 导入路径的**层段** ∈ {`persistence`, `observability`} 即失败（报行号）；**层段** = 路径首段为 `freegraph` 时的**第二段**，否则为**首段**（⇒ `from freegraph.persistence import X` 的层段 = `persistence` ⇒ **违规**）；**指向 `freegraph.contracts`（L1 契约层）与门面包内私有模块（`_stategraph` / `_primitives`）的 import 合法**；**L2 / L3 合法**——门面是 **ARCH-1 的唯一例外**（可 import L1–L3 · 裁定 9），B6F1 / B10F1 / B11F1 接线后**必须** import L2 / L3 |
| ② **第三方 import** | `langchain*` / `langgraph*` / `langsmith` / `pydantic` / `typing_extensions` | 导入名匹配即失败（报行号）；**标准库**（判据见下）与 **`freegraph.*`（内部）不在本档** |
| ③ **环境变量读取** | `os.environ` / `os.getenv` / `os.environb` | 属性链匹配即失败（报行号） |
| ④ **出站 / 文件 I/O** | `socket.*` / `urllib.*` / `http.*` / `open(` / `Path.write_*` / `subprocess.*` | 属性链 / 调用名匹配即失败（报行号） |

> **⚠️ 第三方档判据的修订理由（2026-11-07 分析轮 · 对应发现 **U-1**）**：原第三方档写作
> 「**任何非标准库顶层包**」——但门面**必须** import `freegraph.contracts`
> （`Command` / `RunConfig` 原样转出 ＋ `NodeFunc` / `Checkpointer` / `Store` /
> `CompiledGraph` 的注解），而 `freegraph` **不是标准库** ⇒ 按字面执行，该档会对本
> feature 的**必需代码恒红**。B2F1 的 **G2** 已就同一类缺陷留过判例（「一刀切 ⇒ 因
> `import pytest` 恒失败」）；本条按其**两档**结构修订，与 G2 同构。
>
> **判据细节**：
> - **标准库判定**用 `sys.stdlib_module_names`（Python 3.10+ 标准库 ⇒ 合 **3.11 基线**），
>   **不**依赖人工维护的白名单 ⇒ 跨 Python 版本不漂移；
> - **相对导入**（`from .contracts import ...` / `from ._stategraph import ...`）与
>   **绝对导入**（`from freegraph.contracts import ...`）**同等合法**（与 B2F1 的 G2 同口径）；
> - **「层段」**取 import 路径的**层段**（判据见上表 ①）：首段为 `freegraph` 时取**第二段**，
>   否则取**首段**（`from freegraph.contracts.types import X` ⇒ 层段 `contracts` · **合法**；
>   `from freegraph.persistence import X` ⇒ 层段 `persistence` ⇒ **违规**）；
> - **本档与 FR-014 ① 的关系**：FR-014 ① 的规范文本（「MUST NOT import `langchain` /
>   `langchain-core` / `langgraph*` / `langsmith`」，及本档的 `pydantic` /
>   `typing_extensions` 收敛项）**一字未动**；本门禁是该规范文本的
>   **机械判定方式**，两者的关系是「规范 → 判据」，不是两份规范。
> - **内部档的范围与 FR-014 ④ 同口径**（只禁 **L4 / L5**）——**L2 / L3 合法**：
>   门面是 **ARCH-1 的唯一例外**（可 import L1–L3 · 裁定 9），
>   B6F1 / B10F1 / B11F1 接线后门面**必须** import L2（`Send` / `interrupt` 归 L2）
>   与 L3（`StateGraph` 归 L3）⇒ 禁 L2 / L3 会让后续 feature **必然假红**。

> **扫描范围含外壳模块**：外壳是门面的一部分（用户经门面触达），其依赖面同样受红线约束。
> **例外**：门面**不得** import `subprocess`（本 feature 零出站）；测试文件**不在**本扫描范围
> （测试需要 `subprocess` 驱动子进程门禁 —— 与 B2F1 的 G4 例外口径同构）。

### G18 · 门面的模块加载面（**新增**）

**判定**（**必须子进程执行**）：

1. `import freegraph.graph` 后，`sys.modules` 中**不含**持久化层与可观测层子模块
   （即不含任何 `freegraph.persistence*` / `freegraph.observability*` 形态的模块）⇒ **== 0**；
  2. `import freegraph` 后，`sys.modules` 中 `freegraph.*` 的**子模块数 == 0**
     （**= G1 的同口径复述** —— 判据与 G1 **完全相同**，**由 G1 的实现直接产出**，
     本条**不另写断言**；此处保留仅为「门面视角」的表述完整性）；
3. `from freegraph.graph import StateGraph` 后，`freegraph.contracts` **被加载**（门面**可以**
   依赖 L1 契约层 —— 这是**期望**而非违规）。

> **反向断言的用意**：只判「不该加载的没加载」会漏掉「该加载的也没加载」这种死代码；
> 第 3 条把「门面确实用到了契约层」钉住（`Command` / `RunConfig` 是原样转出 ⇒ 必然加载）。

### G19 · 兼容矩阵覆盖门面 7 个符号（**新增**）

**判定**：在 `README.md` 的「## API 兼容矩阵」**章节内**取行（**MUST NOT** 扫全文），断言：

1. 门面 7 个符号**各恰有一行**（首列符号集合 == `facade-api.md` §0 的 7 个）；
2. 本 feature 补入的 5 行（`StateGraph` / `START` / `END` / `Send` / `interrupt`）**齐全**；
3. 每行**恰 4 列**，且「等价程度」列的取值 **逐符号**与 `facade-api.md` / spec FR-012 ④ 一致
   （`StateGraph` / `Send` / `interrupt` = 部分等价；`START` / `END` = 行为等价）；
4. 新增 5 行**含上游来源 `路径:行号`**（写在「差异说明」单元格末尾 —— 沿用 B2F1 的 4 列纪律）；
5. **既有 18 行逐字未改**（行数与内容断言 —— 与 B2F1 的 G8 同构）。

> **取行范围**：只在「## API 兼容矩阵」章节内取行——README 其它章节里以 `| \`符号\`` 开头的
> 表格行会被误判（与 B2F1 G8 的同一条教训）。

### G20 · 本 feature 新建源文件的署名头（**新增**）

**判定**：**逐文件**断言本 feature 新建的**每一个** `.py` 的**首行**逐字等于

```
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
```

且**模块 docstring 是首个语句**（宪法原则 X；与既有门禁 G5 同款口径）。

**扫描范围**（本 feature 新建的 10 个文件）：

```
src/freegraph/graph.py
src/freegraph/_stategraph.py
src/freegraph/_primitives.py
tests/facade/__init__.py
tests/facade/conftest.py
tests/facade/_gatesupport.py
tests/facade/_snapshot_tools.py
tests/facade/test_facade.py
tests/facade/test_api_snapshot.py
tests/facade/test_facade_gates.py
```

> **为何在门面侧另立一条，而不扩既有 G5 的清单**：既有 G5 的扫描清单
> `SIGNED_SOURCE_FILES`（`tests/contracts/test_architecture.py:112`）是**硬编码元组**，
> 把本 feature 的新文件加进去**必须修改** `tests/contracts/test_architecture.py` ——
> 而本 feature 的既定纪律是「**既有门禁实现零改动**」（见 `plan.md`「与既有 feature 的关系」）。
> 两条路径**各守一头**：既有 G5 继续守契约层那批文件，本门禁守本 feature 新建的这批。
> **代价**：署名头判据从此分两处维护（契约层侧 + 门面侧）——已登记为**已知取舍**。
> **例外清单**沿用宪法：`py.typed` 与 `harness/demo/target.py` 不适用。

---

## 2. 门禁的执行方式

- **全部以 pytest 断言交付**，本 feature **不新建** `harness/` 下的门禁脚本、**不改**
  `.github/workflows/` —— **CI 门禁归 B3F1**（沿用 B1F1 / B2F1 的既有移交口径）。
- **需要子进程的判定**（G1 / G18）**必须在子进程执行**（测试进程自身已导入 pytest）。
- **落点**：本 feature 的门禁测试住在 `tests/facade/test_facade_gates.py`
  （**不叫** `test_architecture.py` —— 与 `tests/contracts/test_architecture.py` 同名会在
  无 `__init__.py` 的目录下触发 pytest 的 `import file mismatch`，research D-16）。
- **门禁自检**：每条**新增**门禁 MUST 有**自检用例**——故意造一处违规，门禁**确实报出**才算通过
  （沿用 B2F1 的做法：只测「合规时通过」的门禁等于没测）。G14–G20 共 **7 条** ⇒ **7 条门禁**，
  **自检 8 条**——**G15 的两段各一条**（子集段 T009 · 集合相等段 T026）。
- **既有门禁的复核**：G7（契约层 18 符号面）与 G12（唯一权威）在本 feature **只复核、不修改**
  ⇒ 以「复核」任务落地（SC-015）。

---

## 3. 与既有门禁的分工（避免重复判定）

| 判据 | 既有归属 | 本 feature |
|---|---|---|
| 契约层的第三方 import / 环境变量 / 出站 | **G2** / **G4**（范围 = `src/freegraph/contracts/**`） | **G17**（范围 = 门面的三个模块 · **两档**）——**不重叠** |
| 顶层包惰性 | **G1**（既有实现的口径**已是** `freegraph.*` 子模块全量 —— 恰为 `['freegraph']`） | **G18**（门面视角复述，**判据相同、不重复实现**） |
| 兼容矩阵 | **G8**（范围 = 契约层 18 个符号） | **G19**（范围 = 门面 7 个符号）——**不重叠** |
| 公开符号面「恰 N 个」 | **G7**（契约层 == 18） | **G15**（门面 == 7）——**不重叠** |
| 唯一权威清单 | **G12**（扫 `**/public-api.md`） | 本 feature **不产出**该文件名 ⇒ **不受影响** |
| 源文件署名头 | **G5**（范围 = B2F1 的 8 个新文件 · 硬编码元组） | **G20**（范围 = 本 feature 的 10 个新文件）——**同一判据、两个文件域，刻意不合并**（既有 G5 的硬编码清单**不扩**，以保住「既有门禁实现零改动」纪律；代价：署名头判据分两处维护，**已登记为已知取舍**） |

> **⚠️ G8 的口径收敛（2026-11-07 实现轮 · spec 裁定 13）**：兼容矩阵自本 feature 起
> **同时**承载**契约层 18 个**与**门面层 7 个**符号 ⇒ 既有 G8 的**整表**判据
> （「矩阵首列符号集合 **==** 契约层 18 个」）与之**互斥** ⇒ G8 改为**按层**判定
> （「契约层 18 个**齐备**」+「无重复行」），**整表**的「无清单外符号」判据由
> **G19** 承担（新增「整表 == 契约层 18 个 ∪ 门面层 7 个」一条）。
> **契约层的任何一条判据都未被削弱**；`src/freegraph/contracts/**` **逐字未动**。
> 详见 `spec.md` 裁定 13 · `harness/verification/B2F2/manual-verification.md` §5 遗留 #1。
