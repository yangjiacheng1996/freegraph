# Implementation Plan: B9F1 · `Command` 原语（`goto` / `update` + `Command.PARENT`）

**Branch**: `b9f1-command-primitive`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`
⇒ 无 `before_specify` 钩子；既有 8 个 feature 同样在 `main` 上开发） | **Date**: 2026-11-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b9f1-command-primitive/spec.md`

**feature ID**: `B9F1`（**M1 运行时内核的第 5 个**（全局第 9 个 · 关键路径第 8 棒）· 前置 **B7F1** ·
后续解锁 **B12F1** → **B10F1**）

---

## Summary

交付 freegraph 的 **`Command` 原语的运行期语义**：节点可以返回一个 `Command`，**同时**表达
「**跳转到哪个节点**」与「**更新哪些状态**」两件事 —— 本 feature 的判定是
「**跳转与状态更新必须同时生效**」（立项书 §5.2 B9F1 行小目标逐字）。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **节点返回值的三形态** | `dict` / `Command` / `list[Command \| dict]` | **归一**为**一种内部形状** ⇒ 「未知 key 报错」「归约器语义」「批量合并」「原子性」**全部复用 B7F1 的同一条路径**（零分叉） |
| **`goto` 的落点** | 「下一个要执行的节点」 | MUST 落在 B7F1 的**边触发源**空间（`("e", 源节点名)`）⇒ **不另造第三种语义**（承接 **H-1**） |
| **`update` 的落点** | 状态更新 | MUST 与普通 `dict` 返回**走同一条写入路径**（承接 **H-2**）⇒ 未知 key ⇒ `InvalidUpdateError`（**C6**） |
| **动态边表** | 源节点 → 其**最近一次执行**的跳转目标 | 落在**调度状态**上（**只增一个带缺省字段** ⇒ `SchedulerState()` 的构造签名**逐字不变**）⇒ 四个下游 feature **零改动** |
| **`Command.PARENT`** | 「跳向父图」的保留标记 | v1 **无子图** ⇒ **显式失败**（`NotImplementedError`）⇒ 与「拼错名字」（`ValueError`）**可区分** |
| **终止标记 `END`** | 「这一位没有下一站」 | **不产生跳转**、**不终止整张图** ⇒ 终止是「**收敛**」的结果 |

技术方案（**只依赖标准库**，零第三方依赖）：

> ⚠️ **本表 = 摘要**（沿用 **B7F1** 裁定 35 的口径）：本表的「关键规则」列是**每条 MUST 的
> 一句话摘要** ⇒ **MUST 的完整口径以 `## Technical Context` 的 Constraints 表为准**（同源 ⇒
> 修改任一条 MUST 时 MUST **同步**两处）。

| 环节 | 手段 | 依据 |
|---|---|---|
| 模块落位 | **修改** `src/freegraph/runtime/superstep.py`（**既有文件**）⇒ `runtime/` 已是**目录条目** ⇒ **层注册表零改动** | spec FR-015 · 层注册表 §0.2 规则 2 |
| 导出面 | **零新增**（`freegraph.runtime.__all__` **仍 20**）⇒ `Command` 的对外导出沿用 L1 / 门面 | 裁定 13 · FR-016 · SC-015 |
| 返回值归一 | 三形态 → **一种内部形状**（待写入 + 跳转目标）⇒ 合并路径**唯一** | 裁定 4 · FR-001 / FR-004 |
| `goto` 的落点 | **边触发源** `("e", 源节点名)` ⇒ 源节点的**执行版本** +1 ⇒ 目标**下一轮**被触发 | 裁定 1 · FR-002 · research **D-01** |
| 目标的生命周期 | 源节点**最近一次执行**决定 ⇒ 再次执行且无 `goto` ⇒ **旧目标被清空** | 裁定 2 · FR-009 · research **D-01**（上游分支通道 = `EphemeralValue` ⇒ 步末即清） |
| `goto` × 静态边 | **叠加**（上游**实测同款**）⇒ 两边目标**都**被触发 | 裁定 3 · FR-008 · research **D-02** |
| 目标的触发门槛 | **无「有值」门槛**（边触发源只比版本号）⇒ 目标**订阅的通道没值也照跑** | 裁定 17 · FR-002 · research **D-09**（上游实测三组） |
| 目标的入参 | **正常稀疏读**（`read_channels(子映射)` · 子映射按**通道映射顺序**构造）⇒ **读得到**源节点本次 `update` | 裁定 17 · FR-002 · research **D-09** |
| 终止标记 `END` | **不产生跳转**（该位不产生动作）⇒ **不终止整张图** | 裁定 5 · FR-007 · research **D-03** |
| 终止标记的判定 | L2 **MUST NOT** import 门面（ARCH-1）⇒ **字面量** `"__end__"` 判定 ⇒ 门面 `END` 值 MUST **逐字相等**（可自动核对） | 裁定 6 · FR-007 · SC-008 |
| 非法目标 | **显式失败**（`ValueError` · 点名目标）⇒ 与上游的「warning + 忽略」**刻意分叉** | 裁定 8 · FR-007 · parity **P-07** |
| `Command.PARENT` | **显式失败**（`NotImplementedError` · 点名「子图属 v2 能力」） | 裁定 7 · FR-005 · parity **P-08** |
| 空槽位 / 空列表 | **明确无操作**（零写入 + 零跳转 + 仍计入执行记录） | 裁定 10 / 15 · FR-006 · parity **P-05 / P-09** |
| 命令列表 | **支持**（上游同款）⇒ **按列表顺序**依次生效（写入按序合并 · 每条 `goto` 各自成边） | 裁定 15 · FR-001 / FR-004 · research **D-08** |
| 写入的归属 | 归**源节点**名下（`node_writes` 的按节点分组）⇒ **B8F1** 的 fresh 读**读得到** | 裁定 16 · FR-004 · SC-022 |
| 原子性 | `Command.update` 引发的错误 ⇒ **整轮**不合并 · 值保持轮初 · **版本不推进** | FR-012 · SC-013 |
| 跳转的**可观察出口** | **不加字段**（四字段冻结面不动）⇒ 证据 = 下一轮 `executed` + **L1 `StateSnapshot.next`**（与上游**同款**的字段） | 裁定 18 · FR-016 · research **D-10** |
| 可观测层 | **零越界** ⇒ 触发源的暴露口径归 **B19F1**（**已接线**） | 裁定 19 · FR-022 · 下游承接 **D-3** |

**零新增公开 API、零新增错误类型、零新增门禁编号**：契约层 **18** 符号面与门面 **7** 符号面**一字不动**
（G7 / G15 / G19 恒成立）；`freegraph.runtime` 的导出**仍 20** 个符号（**L2 内部 API**，不进兼容矩阵）；
⚠️ **兼容矩阵**（2026-11-11 分析轮 · 发起者拍板 · Q2）：**零新增行** + 既有 `Command` / `NodeFunc` 两行的
**措辞更新 MAY**（仅限事实性更新）⇒ 与宪法原则 X 的「MUST 更新清单」**并存**（原「MUST NOT 触碰」口径**已收敛**）；
`langgraph` **不写进任何依赖声明**（Phase 0 的取证环境是**用户 site-packages** ⇒ 非仓库依赖）。

**上游核实已在 Phase 0 完成**（`langgraph 1.2.11` · **用户 site-packages** · **不进仓库**）⇒ 详见
[research.md](./research.md) §1（**D-01…D-10**）与
[contracts/upstream-parity.md](./contracts/upstream-parity.md)（**12 条**对照 + **8 组**实测基线 + **3 条**刻意分叉）。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`pyproject.toml` 的 `requires-python = ">=3.11"`）；
**typing 构件上限 = 3.11**（宪法「运行时环境基线」）—— 本 feature 用到的构件**全部 ≤ 3.11**：
`collections.abc.Callable` / `Sequence` · `dataclasses.dataclass` / `field` · `typing.Any`。
**MUST NOT** 使用 `TypeAliasType`(3.12) / `override`(3.12) / `ReadOnly`(3.13) / `TypeIs`(3.13)
或 PEP 695 `type` 语句。**主判定 = CI 矩阵最低档 3.11 跑全量测试**。
⚠️ **Phase 0 取证用的是 CPython 3.12.3**（用户 site-packages）⇒ **上游行为**取证结论成立，
但 freegraph 侧的实现仍 MUST 在 **3.11** 上成立（**两件事** · research §4 第 3 条）。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []` · 沿用现状）。
**开发期**：`pytest` / `packaging`（既有 `[dependency-groups] dev`）—— **零新增**。
⚠️ **本 feature 不引入任何新依赖组**：`langgraph` 装在**用户 site-packages**、**不在**仓库 venv 里
⇒ `pyproject.toml` **零改动** ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿（**未被触碰**）。
⚠️ 覆盖率工具**也不进依赖**（沿用 B5F1 / B5F2 / B7F1 的口径）⇒ 开发期临时安装、实测输出记入人工验证记录。

**Storage**: N/A —— 本 feature 无运行时持久化（checkpoint 属 **B14F1**）。
**仓库内的权威工件** = **纯文本 Markdown 契约**（两份）：
[command-contract.md](./contracts/command-contract.md)（命令契约 · **唯一权威**）·
[upstream-parity.md](./contracts/upstream-parity.md)（上游对照 · **证据表**）。

**Testing**: pytest + 标准库 `collections.abc` / `dataclasses` / `typing`。
**需要子进程的断言**（SC-014 的「内核路径零上游导入」· SC-018 的「零环境变量 / 零出站」）
**必须在子进程中执行** ⇒ **复用 B4F1 已有的 `tests/runtime/conftest.py` 夹具 `run_in_subprocess`
（session 级）⇒ **既有 conftest 零改动**。

**Target Platform**: 任意 CPython 3.11+ 平台（Linux / macOS / Windows）。
CI 的 `testpaths = ["tests"]` ⇒ 新增的 `tests/runtime/test_command_*.py` **自动被收集**。

**Project Type**: library（Python 库；发行名 = 导入名 = `freegraph`；D1 决议：不拆独立发行包）。

**Performance Goals**: **N/A（不设时间预算）** —— 归一是**单遍遍历**、无 I/O / 无网络 / 无锁。
**规模口径**用**结构口径**表达：归一 **O(返回值规模)** · 动态边登记 **O(目标数)** ·
触发判定的额外成本 **O(节点数 × 动态边数)**（仍是**单遍**）· 动态边表空间 **O(节点数 × 目标数)**。
⚠️ **MUST NOT** 用墙钟耗时做断言（CI 假红）⇒ 判据用「执行次数 / 调用次数 / 逐元素相等 /
集合相等 / 逐字相等」（data-model §8）。

**Constraints**（**主要**来自 spec 的 MUST 条目；未逐条列出的 FR 见 `tasks.md` 的追溯表）：

| 约束 | spec 条目 |
|---|---|
| 只依赖**标准库**；MUST NOT import `langchain*` / `langgraph*` / `langsmith` / `pydantic` / `typing_extensions` | FR-014 · SC-014 |
| MUST **NOT** 读取**任何**环境变量；零出站；零文件 I/O；导入**无副作用** | FR-014 · SC-014 |
| 层纪律：L2 只向下依赖 L1；MUST NOT import L3 / L4 / L5（⇒ **终止标记 MUST 以字面量判定**） | FR-015 · SC-015 · 裁定 6 |
| ⚠️ **经特批的**唯一例外**：**L1 的 `NodeFunc.__call__` 返回联合**放宽出「**命令列表**」⇒ **L1 的符号集合与数量不变**（18 个 ⇒ **G7 恒绿**）· MUST NOT 改动其余任何 L1 符号 | FR-001 / FR-016 · **裁定 21** · 登记项 **R-7** |
| 节点返回值 MUST 是 `dict` / `Command` / `list[Command \| dict]` 之一；其它 ⇒ `TypeError` | FR-001 · SC-003 |
| 归一后**只有一种内部形状** ⇒ 三种写法**共用同一条合并路径** ⇒ MUST NOT 分叉 | FR-004 · SC-003 |
| `Command.update` 的写入 MUST 归**源节点**名下（`node_writes` 的按节点分组） | FR-004 · SC-022 |
| 命令列表 MUST **按列表顺序**依次生效（写入按序合并 · 每条 `goto` 各自成边） | FR-001 / FR-004 · SC-021 |
| `Command.goto` MUST **先判 `isinstance(x, str)`**；序列 ⇒ 多目标；空序列 ⇒ 无跳转 | FR-007 · SC-011 |
| `goto` 的目标 MUST 在节点表内（或为终止标记）⇒ 否则 **显式失败**（`ValueError` · 点名目标） | FR-007 · SC-009 |
| `goto == Command.PARENT` ⇒ **显式失败**（`NotImplementedError` · 点名「子图属 v2 能力」） | FR-005 · SC-005 |
| `END` ⇒ **不产生跳转**、**不终止整张图**；更新**照常生效** | FR-007 · SC-008 |
| `goto` MUST 落在**边触发源**空间（`("e", 源节点名)`）⇒ MUST NOT 另造第三种语义 | FR-002 · SC-001 / SC-007 |
| `goto` 目标 MUST 在**下一轮**被触发；MUST **无「有值」门槛**；入参 = **正常稀疏读** | FR-002 · SC-023 |
| `goto` 目标 MUST 由源节点的**最近一次执行**决定（再次执行无 `goto` ⇒ 旧目标被清空） | FR-009 · SC-010 |
| `goto` 与静态边 MUST **叠加**（MUST NOT 互相取消） | FR-008 · SC-007 |
| 槽位为空 / 空列表 ⇒ **明确无操作**（零写入 + 零跳转 + 仍计入执行记录） | FR-006 · SC-006 |
| `Command.resume` MUST 被**接受**；本轮 MUST NOT 产生任何恢复效果 | FR-011 · SC-012 |
| `Command.update` 非 `dict` ⇒ `TypeError`；未知 key ⇒ `InvalidUpdateError`（**C6**） | FR-010 / FR-004 · SC-004 |
| `Command.update` 引发的错误 ⇒ **整轮原子**（不合并 · 值不变 · 版本不推进） | FR-012 · SC-013 |
| 节点入参口径 MUST 照写（`read_channels(子映射)` · 子映射按**通道映射顺序**构造）；MUST NOT 依赖「调用方复用同一个调度状态」 | FR-013 · SC-019 |
| `SuperStepResult` 的**四字段冻结面 MUST NOT 动**；跳转的可观察证据 = 下一轮 `executed` + L1 `StateSnapshot.next` | FR-016 · SC-024 |
| **导出面零新增**（`freegraph.runtime.__all__` **仍 20**）；L1 **18** / 门面 **7** 符号面**一字不动**；`THIRD_PARTY_NOTICES` **零改动**；**兼容矩阵零新增行** + 既有 `Command` / `NodeFunc` 两行的**措辞更新 MAY**（其余行一字不动 · FR-016 的口径） | FR-016 · SC-015 |
| MUST **NOT** 实现可观测层的任何观测面（触发源的暴露归 **B19F1**） | FR-022 · SC-025 |
| MUST **NOT** 实现：`Command` 作为**图的输入** · 子图与 `PARENT` 的跨层传播 · `resume` 的恢复效果 · `Send` · `invoke` / `stream` / `compile` / `StateGraph` · 并发 · 条件边求值 · checkpoint · async | FR-022 · SC-015 |
| 新源文件 MUST 带**署名头**且 docstring 是首个语句；上游引用 MUST 标**版本 + `路径:行号`** | FR-021 / FR-017 · SC-020 |
| 新增代码**行 / 分支覆盖率 == 100%**；用例 MUST NOT 经由图构建器 | FR-020 · SC-016 |
| 人工验证记录（五段式 + 来源覆盖表）+ **偏离登记 + 发起者追认** | FR-018 / FR-019 · SC-017 / SC-018 |

**Scale/Scope**: **880 行**（实现 **420** / 测试 **460**）· **3 人日**（提示词表格值 · 立项书 §5.2）
—— 作为 plan 的输入而非硬约束；⚠️ **本 feature 的实际增量集中在 `superstep.py` 的「归一」子步骤
+ 动态边表**（其余是既有代码的**扩展**而非新写）。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 通过项（逐条）

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith 依赖 · 自身零出站 · 零环境变量） | FR-014 · 既有 **G24**（配置层扫描 `src/freegraph/**`）· **G26**（网络静态扫描）· **G27**（零出站动态） | ✅ |
| 原则 II（内核纯净 · 状态语义 MUST 与 LangGraph 等价） | FR-014（零依赖）· **本 feature 零上游依赖**（连 `differential` 组都不需要）· **G3 / G21 / G22 / G23**（依赖闭包为空集）· `contracts/upstream-parity.md`（**12 条**逐条对照 + **8 组**实测基线 + **3 条**刻意分叉）承载等价性 | ✅ |
| 原则 III（验收契约优先 · `target.py` 只读） | 本 feature **零改动** `target.py`；`harness/demo/graph_core.py:317-335` 的 C16 用例（`Command(goto=END, update=...)`）是**下游**的验收点（本 feature **不交付** `compile()`） | ⚠️ **「`target.py` 原样可跑」本 feature 物理不可达成** ⇒ 见**登记项 R-1** |
| 原则 IV（可诊断性） | N/A（本 feature **无运行期可观测面** ⇒ 归 **B19F1**；诊断靠失败信号的**结构化信息**：点名目标 / 点名 `__parent__`） | ✅ 边界内 |
| 原则 V（人工验收是最终验收标准） | 人工验证记录（五段式 + 来源覆盖表 · SC-017） | ⚠️ **门禁 5 的「真实模型一轮」不适用** ⇒ 见**登记项 R-1** |
| 原则 VI（规格驱动 · tasks 可逐条勾选） | 本 plan + `tasks.md`（含 FR ↔ SC 追溯表） | ✅ |
| 原则 VII（职责边界 · 契约 C1–C27） | FR-004 / FR-007 = **C6** 的执行侧落地 · FR-002 = **C16** 的运行期语义落地 · FR-005 = **C26** 的 v1 边界（只保签名兼容 + 显式失败）· 上游 MUST NOT import L3/L4/L5 | ✅ |
| 原则 VIII（证据与术语纪律） | `research.md` §1 每条决策附**实测方法 + 真实输出**（D-01…D-10 · 核实版本 `langgraph 1.2.11`）；上游引用标 `路径:行号`；**事实性表述的更正已登记**（research §3 的 C-1 / C-2） | ✅ |
| 原则 IX（许可证与商标红线 · NON-NEGOTIABLE） | **零新增依赖** ⇒ `THIRD_PARTY_NOTICES` **无需变更**；**零品牌资产**（重写语义，不复制上游代码） | ✅ |
| 原则 X（文档合规 + 源文件署名头） | FR-021（署名头 · 既有 **G30** 全仓扫描自动覆盖新文件）· 兼容矩阵**零新增行** + 既有 `Command` / `NodeFunc` 两行**措辞更新 MAY**（**Q2 的收敛** ⇒ 与原则 X 的「MUST 更新清单」**并存**） | ✅ |
| 运行时环境基线（Python 3.11 · typing 上限 3.11） | 本 feature 只用 ≤ 3.11 构件（Technical Context 已逐项列出）· 最低档 3.11 跑全量测试 | ✅ |
| 依赖白名单 / 黑名单（包层 · 配置层 · 网络层） | **零新增运行时依赖** ⇒ **G3 / G21 / G23 / G24 / G26 / G27** 恒绿 | ✅ |
| **跨 feature 承接的接线通则（v1.8.0）** | 上游 **H-1…H-4**（B7F1 的触发源体系 / 合并路径 / 入参与调度状态口径 · B1F1 的类型面）**照写**（本 feature 是**消费方**，不需改上游提示词初稿）⇒ plan 阶段**复核措辞未走样**；下游 **D-1**（B12F1 · 并发语义）· **D-2**（B10F1 · resume）· **D-3**（B19F1 · 触发源暴露口径）**已接线**（B12F1 / B19F1 的提示词初稿**已追加条款**）⇒ 见**登记项 R-5** | ⚠️ **R-5** |
| 质量门禁 1 / 2 / 6 / 7 | ① 规格 + tasks 可勾选 ② 依赖**零新增** ⑥ 证据（research + 对照表 + 来源覆盖表）⑦ 文档合规（署名头 + 兼容矩阵零新增） | ✅ |
| 质量门禁 3 / 4 / 5 的**内核运行时相关部分** | ⚠️ **物理不可达成** ⇒ **登记项 R-1**（偏离登记 + 发起者追认） | ⚠️ **见 R-1** |
| 发布门禁（发行产物纯度） | 本 feature **不接入**（B24F1）· 改动在 `src/freegraph/runtime/` 内 ⇒ **不污染**产物纯度；**零新增依赖** ⇒ sdist / wheel 零变更 | ✅ 边界内 |

### ⚠️ 登记项 R-1（宪法「质量门禁 3 / 4 / 5」的偏离登记 · 需发起者追认）

**依据**：宪法 **v1.6.0**「质量门禁的分阶段落地与发起者追认」（**窄口径**通则 · 首次适用 = B3F1）。
**本 feature 与 B5F1 / B5F2 / B7F1 的 R-1 同根因**（都需要**完整内核运行时**才能跑通验收基线）⇒
**沿用既有承接机制**，MUST NOT 新造。

| # | 被偏离的**具体门禁项** | 不可达成的根因 | 判据未被放宽的论证 | 承接方（feature ID + 里程碑） | 承接机制 |
|---|---|---|---|---|---|
| ① | **门禁 3** 的「**`harness/demo/target.py` 原样可跑**」 | 本 feature 只交付**运行期语义**（`StateGraph` = **B6F1** · `compile()` = **B7F2** · `invoke()` = **B7F3** · 条件边 = **B8F1** · `get_graph` = **B22F1** · PNG = **B23F1**）⇒ **无图可编译、无入口可调** ⇒ 脚本物理跑不到验收点 | 固定脚本**一字未改**；本 feature 的用例用**同名 key**（`messages`）⇒ 与脚本的 `state.get('llm_calls', 0) + 1` **同形**；**判据未放宽** | **B6F1 + B7F2 + B7F3 + B8F1 + B22F1 + B23F1**（M2）· **B25F1**（M4） | **已就位**：B3F1 的裁定 22 已把「fake 轮 / 真实模型轮」的承接条款写入各目标 feature 的提示词初稿 |
| ② | **门禁 4** 的「**fake 模型跑通验收基线的一轮**」与**门禁 5** + 原则 V 的「人工验证记录含**真实模型一轮**」 | 两者都要求**完整内核运行时**（编译 + 执行）⇒ 属 **B7F2 / B7F3** ⇒ 本 feature **无图可跑** | CI **不写**一条永久红的断言（违宪 PR-4）；五段式记录 + 来源覆盖表**照常落地**（FR-018 · SC-017） | **B7F2 + B7F3**（M2）· **B25F1**（M4） | **已就位**（同上 · B3F1 裁定 22） |
| ③ | **门禁 3** 的 **C16**（命令原语）的**端到端**断言 | `Command` 的**类型**在 **B1F1**、**运行期语义**在本 feature、**对外入口**在 **B7F3** ⇒ 「从门面 `invoke` 跑一条 `Command`」的端到端断言**物理不可达成** | 本 feature 用**手写图规格**驱动 ⇒ `Command` 的运行期语义**可独立判定**（SC-001…SC-025）⇒ 端到端断言**留给 B7F3**（不改判据） | **B7F3**（M2） | **已就位**（B7F3 的提示词初稿把 `Command` 列为对外 API 面的一部分） |

**红线（未被触碰）**：依赖红线（`langsmith` / `langchain*` / `langgraph*`）· 许可证红线 · 商标红线 ·
零出站红线 —— **全部在本 feature 照常执行**（FR-014 + G3 / G21 / G22 / G23 / G24 / G26 / G27）。

**⇒ 请发起者在合入前追认此登记项**（落点：`tasks.md` 的一条**阻断合入**的追认任务 ·
追认文字 MUST 落在 `harness/verification/B9F1/manual-verification.md`）。

### ⚠️ 登记项 R-2（**裁定 1 / 2 / 4 / 6 / 8 / 10 / 11 / 13 / 14 的拍板来源** · spec 阶段由 agent 拍板 ⇒ 需发起者追认）

**依据**：宪法 **v1.8.0** + 原则 VIII（决策 MUST 可审计）—— 裁定 **1 / 2 / 4 / 6 / 8 / 10 / 11 / 13 / 14**
是在 **specify 阶段由 agent 依仓库既有范式拍板**的（**发起者未逐条答复**）⇒ 其中若干条冻结了
**跨 feature 的接口**（`NodeSpec.run` 的接受面 · `SchedulerState` 的形状 · 导出面）
⇒ **MUST** 具备**发起者**背书。

| # | 裁定 | 冻结的跨 feature 影响 | 为何仍需追认 |
|---|---|---|---|
| ① | **裁定 11**（`NodeSpec.run` 的返回类型注解放宽） | **B7F2 / B7F3 / B8F1 / B12F1** 都照着 B7F1 的 `NodeSpec` 写 ⇒ 类型面**协变放宽**（不破构造签名） | 冻结的是**跨 feature 的类型面** |
| ② | **裁定 13**（导出面零新增） | `freegraph.runtime.__all__` **仍 20** ⇒ 既有断言 `tests/runtime/test_read_contract.py` 的符号数断言**不需要再动** | 冻结的是**跨 feature 的导出面** |
| ③ | **裁定 4**（归一为同一份待写入 ⇒ 共用一条合并路径） | **B8F1** 消费 `node_writes` ⇒ 归一口径影响下游 | 跨 feature 的数据形状 |
| ④ | **裁定 1 / 2 / 6 / 8 / 10** | 触发源空间 / 生命周期 / 终止标记 / 非法目标 / 空槽位 | 跨 feature 的语义口径（虽多为一处之内的判定） |

**处置**：① 在 `spec.md` 的 `## Clarifications` 与裁定表**逐条标注来源**（**已落**：裁定表已注明
「**spec 阶段拍板**」）；② MUST **列入 `tasks.md` 的「发起者追认」清单**（**阻断合入**）⇒ 追认文字落在
`harness/verification/B9F1/manual-verification.md`；③ 追认前**不得**视作已获发起者背书；
**MUST NOT** 以此放宽任何判据（这九条**只收紧或等价**）。

⚠️ **对照**：澄清轮**由发起者本人拍板**的裁定（**3 / 5 / 7 / 9 / 12**（第 1 轮）+ **15 / 16 / 17 / 18 / 19**
（第 2 轮））⇒ **无需**追认。

**红线**：MUST **NOT** 改宪法正文 · MUST **NOT** 写一条永久红的 CI · MUST **NOT** 放宽任何判据。

### ⚠️ 登记项 R-3（**两处跨 feature 的冻结面扩展** · 需发起者追认 + 字段名由本 plan 冻结）

**依据**：宪法 **v1.8.0** + B7F1 的「既有冻结面 MUST 零改动」口径 —— 本 feature 需要**两处**扩展，
二者都**不改变任何构造签名与名字**（⇒ 调用方**零改动**），但仍是**冻结面的扩展** ⇒ MUST 登记。

| # | 扩展 | 内容 | 不破冻结面的论证 | 落点 |
|---|---|---|---|---|
| ① | **`SchedulerState` 增一个带缺省字段**（裁定 12 · 澄清轮第 2 次 **Q5** · 发起者拍板） | 字段名 = **`dynamic_edges`**（`dict[str, tuple[str, ...]]` · 缺省用**工厂语义**）· **本 plan 冻结** | `SchedulerState()` 的**构造签名与名字逐字不变** ⇒ **B7F2 / B7F3 / B8F1 / B12F1 零改动**；字段属 **L2 内部状态**、**不进公开面** ⇒ 不触 G7 / G15 | data-model §3.1 · FR-002 · SC-015 · **追认项** |
| ② | **V-4 的返回值接受面放宽**（裁定 15 · 澄清轮第 2 次 **Q1** · 发起者拍板） | 节点返回值：`dict` / `Command` / `list[Command \| dict]`（原为「`dict` 或 `None` ⇒ `TypeError`」） | **协变放宽**（**接受面变大** ⇒ 既有调用方**零破坏**）⇒ 与裁定 11 **同款**；⚠️ **B7F1 的 V-4 口径文本**在 B7F1 的契约里描述的是「不是 `dict` ⇒ `TypeError`」⇒ 该表述**仍然成立**（`list` 也不在「必须是 `dict`」的旧口径里 ⇒ **旧口径不需要改**）⇒ **MUST NOT** 回头改 B7F1 的契约 | FR-001 · SC-003 · **追认项** |

⚠️ **R-3 ② 的一处必须核对的点**（**事实性核对**）：B7F1 的 `superstep-contract.md` **§2.1.1** 的
**V-4** 行写「节点返回值**不是 `dict`**，含 `None` ⇒ 内置 `TypeError`」⇒ 本 feature 放宽后，
「返回 `list`」**不再是** V-4 的失败场景 ⇒ **B7F1 的契约文本**若被逐字引用，会与本 feature 的
FR-001 **表面冲突** ⇒ **处置**：本 feature 的 **V-9**（返回值形态非法）是 B7F1 **V-4 的超集**
（`dict` / `Command` / `list` 之外的形态 ⇒ 仍 `TypeError`）⇒ **B7F1 的契约文本无需改动**
（它描述的是「`dict` 之外 ⇒ `TypeError`」，本 feature 只是**多接收两种**）⇒
**MUST NOT** 改 B7F1 的契约文件 ⇒ **tasks 阶段的一条核对任务**（核对措辞未走样）。

**红线**：MUST **NOT** 改动 B7F1 的**构造签名与名字** · MUST **NOT** 新增 L1 / 门面的公开符号 ·
MUST **NOT** 改 B7F1 的契约文件 · MUST **NOT** 新增门禁编号 · MUST **NOT** 放宽任何判据。

### ⚠️ 登记项 R-4（**对 B7F1「只用两种内置异常」不变量的刻意偏离** · 需发起者追认）

**依据**：B7F1 契约 §2.1.1 的「不变式」行 —— 「一个 feature 只用**两种**内置异常
（`ValueError` / `TypeError`）」⇒ 本 feature 引入**第三种**（`NotImplementedError`）。

| # | 内容 |
|---|---|
| ① | **偏离点**：`Command.PARENT` ⇒ `NotImplementedError`（裁定 7 · 澄清轮第 2 次 **Q2** · 发起者拍板） |
| ② | **理由**：① `Command.PARENT` 是**合法常量**（不是写错了）只是**本版本未实现子图** ⇒ 与「目标名写错」（`ValueError`）**语义不同** ⇒ 用**不同的异常类型**分开表达（**可区分** ⇒ SC-005 的一条断言）；② **仓库已有同款用法**：`interrupt()`（`src/freegraph/_primitives.py`）与 `StateGraph` 的方法在**未接线**时都抛 `NotImplementedError` 并**点名归属的 feature** ⇒ 与之一致 |
| ③ | **零新增错误类型**：用的是**内置**异常 ⇒ **L1 的 18 符号面零改动**（G7 恒绿）· **零新增 L2 错误类型** |
| ④ | **处置**：① 在 spec 的 FR-005 / 裁定 7 / SC-005 **逐条登记**（**已落**）；② MUST **列入 `tasks.md` 的追认清单**（**阻断合入**）⇒ 追认文字落在 `harness/verification/B9F1/manual-verification.md`；③ MUST **NOT** 因此放宽任何判据（**只增一条可区分性断言**） |

**红线**：MUST **NOT** 新增 L1 / L2 的错误类型（复用内置 + B5F1 的既有类型）· MUST **NOT** 把
`NotImplementedError` 与 `ValueError` **合并**（V-13 / V-14 MUST 可区分）· MUST **NOT** 新增门禁编号。

### ⚠️ 登记项 R-5（**下游承接 D-1 / D-3 的跨 feature 文档改动** · 需复核 + 追认）

**依据**：宪法 **v1.8.0**「跨 feature 承接的接线通则」—— 本 feature 的规格中出现了**指名下一棒
feature（ID + 里程碑）**的跨 feature 义务（**D-1** / **D-3**）⇒ 该条款 MUST 写入**目标 feature 的
提示词初稿** ⇒ 由目标 feature 的 spec 落成 **FR + 裁定**。

| # | 动作 | 状态 | 落点 |
|---|---|---|---|
| ① | **D-1**（B9F1 → B12F1 · M1）：并发下 `Command` 的语义 MUST 保持可判定（各节点的 `goto` 目标**互不吞并**；`Command.update` 继续走**批量**合并路径） | ✅ **已接线**：`harness/features/B12F1_并发执行与错误传播.md` **§2** 追加一条（**只接线 · 逐条最小改动** · 其余内容一字未动） | 下游承接 **D-1** · FR-004 / FR-008 / FR-022 · SC-025 |
| ② | **D-3**（B9F1 → B19F1 · M3）：触发源**同源**（`goto` 与静态边一起暴露）⇒ 本 feature **未**新增任何跳转观测字段 | ✅ **已接线**：`harness/features/B19F1_TraceSink与current_span.md` **§2** 追加一条（**只接线 · 逐条最小改动**） | 下游承接 **D-3** · FR-022 · 裁定 19 · SC-025 |
| ③ | **D-2**（B9F1 → B10F1 · M1）：`Command.resume` 的运行期行为归 B10F1 | ✅ **已就位**（既有）：`harness/features/B10F1_interrupt与resume.md` **§7** 逐字「`goto`/`update` 语义在 **B9F1**」⇒ **无需改动** | 下游承接 **D-2** · FR-011 · SC-012 |
| ④ | **处置**：**tasks 阶段各落一条「复核措辞未走样」的核对任务**（**不重写**）+ 一条**阻断合入的追认任务**（R-5 的追认文字落在人工验证记录） | 待落 | 宪法 v1.8.0 |

**红线**：MUST **NOT** 越界实现 B12F1 的并发合并 / B19F1 的触发源暴露 / B10F1 的恢复效果 ·
MUST **NOT** 改动目标 feature 提示词初稿的**其余**内容（只接线）· MUST **NOT** 新增门禁编号 ·
MUST **NOT** 放宽任何门禁判据。

### ⚠️ 登记项 R-6（**分析轮的三处收敛** · 2026-11-11 · **发起者本人拍板 ⇒ 无需追认**）

**依据**：`/speckit.analyze` 的三件套一致性核验（FR **23/23** · SC **25/25** 双覆盖 · 追溯表 **40** 行
双向无空缺 · 任务格式 **40/40** 合规 · 宪法**无 MUST 冲突**）⇒ 产出 **2 HIGH + 3 MEDIUM + 6 LOW**，
其中 **3** 条属「**判据不可实现 / 不可判定**」⇒ **发起者逐条拍板**（**只消除冲突 · 只补断言**）。

| # | 发现 | 处置（**判据只收紧、不放宽** · **FR / SC 的编号与总数零变动**） | 落点 |
|---|---|---|---|
| ① | **归一形状**用 `dict[str, Any]` ⇒ 命令列表里**两条命令写同一个 key** 时**后者覆盖前者** ⇒ 与 FR-004 / 裁定 15 冲突 ⇒ **SC-021① 不可实现** | 形状改为**每 key 一个值序列**（`dict[str, tuple[Any, ...]]`）⇒ 与 B7F1 的 `node_writes` **同构** ⇒ **合并路径零改动** | **裁定 20** · data-model §2 · contract §2 · tasks **T007 / T018** |
| ② | FR-016 的「MUST NOT **触碰** API 兼容矩阵」与宪法原则 X 的「MUST **更新**清单」**字面互斥** | FR-016 收敛为「**零新增行** + 既有 `Command` / `NodeFunc` 两行**措辞更新 MAY**」⇒ **只消除字面冲突 · 不放宽判据** | **裁定 20** · **FR-016** · **SC-015** · tasks **T012** |
| ③ | **SC-008** 第三子句（门面 `END` == L2 字面量）与 **SC-015** 的两个「构造签名逐字不变」子句**无断言承载** | 三条断言**并入 T030** ⇒ **不新增任务 · 不新增判据** | **裁定 20** · tasks **T030** + 追溯表 + 判据总表 |
| ④ | plan 的**源码树缺** `test_command_goto_errors.py` / `test_command_noop.py`（tasks 与 quickstart 均为 **11** 个模块） | plan 的源码树**补两行**（纯文档同步） | 本 plan 的 Project Structure |
| ⑤ | 其余 LOW（术语三样 / 措辞重复 / 注解先于行为 / 改动面未含 plan+tasks / 兼容矩阵措辞可选 / README 行号**已标版本**） | ① 术语统一为「动态边表（`dynamic_edges`）」· ② 删重复措辞 · ③ T010 补「骨架期一律 `NotImplementedError`」· ④ plan 的「改到的既有文件」补 `plan.md` / `tasks.md` · ⑤ 矩阵两行措辞更新**已在 plan 阶段落地**（`README.md` 的 `Command` / `NodeFunc` 两行 · **零新增行** · 等价程度不变）⇒ T012 降级为**核对** · ⑥ README **不动**（其行号取自 **1.2.19** 且**已标版本** ⇒ 非漂移） | 分散落点 |

**红线**：MUST **NOT** 改宪法正文 · MUST **NOT** 放宽任何判据 · MUST **NOT** 新增门禁编号 ·
MUST **NOT** 改 `harness/reports/Q8-…`（契约清单只读）· MUST **NOT** 改 B7F1 的契约 / spec。

### ⚠️ 登记项 R-7（**破 L1 冻结面** · `NodeFunc.__call__` 增补「命令列表」· **需发起者追认**）

**依据**：**宪法 v1.8.0** + B7F1 的「既有冻结面 MUST 零改动」口径 —— 本 feature 需要**放宽 L1 的
`NodeFunc.__call__` 返回联合**（增 `list[Command | StateDict]`）⇒ **破 L1 的冻结面**（**符号集合与数量
不变**）⇒ MUST 登记 + 追认。

| # | 内容 |
|---|---|
| ① | **放宽点**：`freegraph.contracts.protocols.NodeFunc.__call__` 的返回联合 = `StateDict \| Command \| None` ⇒ **`StateDict \| Command \| list[Command \| StateDict] \| None`**（**代码 + docstring**） |
| ② | **为什么必须改**：L1 的三形态**从未讨论**「一个节点发出多条命令」（B1F1 / B2F1 / Q8 **零命中**）⇒ 若只让**运行时**接受列表 ⇒ **协议与运行时分歧**（用 `NodeFunc` 标注的节点**类型层**无法表达列表返回）⇒ **协议 MUST 与运行时一致**；且上游 LangGraph 的 **`ToolNode` 自身即返回命令列表**（`prebuilt/tool_node.py:890-920` 实测）⇒ **同款** |
| ③ | **门禁零影响**：**G7** 判「契约层公开符号面**恰为 18 个** · `__all__` **集合相等**」⇒ 改**注解**（**不新增符号**）⇒ **恒绿**；**G8** 判「矩阵逐符号覆盖 + 4 列」⇒ **恒绿**（⚠️ 但 G8 的**「既有 18 行逐字未改」**判据 ⇒ `Command` / `NodeFunc` 两行**经特批**进**白名单**（只放行「差异说明」列 ⇒ **等价程度 MUST NOT 变**）· 见登记项 **R-7 ④**）；**C5 / C6 的条目本身一字未动**（Q8 §3.4 仍为唯一权威）⇒ 变更的只是 `NodeFunc.__call__` 的**承载签名** |
| ④ | **回溯修订清单（实现期实测补全 · 共 11 处）**：**代码 1 处** —— `src/freegraph/contracts/protocols.py`（注解 + docstring）· **文档 6 处** —— B2F1 的 `contracts/public-api.md`（**5** 处：符号清单注释 / 逐符号表 / 上游对照行 / C5 行 / C6 行）+ B2F1 的 `spec.md`（FR-001 冻结口径 + 理由留痕）+ B7F1 的 `contracts/superstep-contract.md`（**V-4** 行 · 与 B9F1 的三形态不再矛盾）+ B7F1 的 `spec.md`（**FR-009** 措辞）· **冻结断言 2 处** —— `tests/contracts/test_protocols.py`（`test_call_signature_is_frozen`）· `tests/facade/test_facade_gates.py`（**G8 的「既有 18 行逐字未改」判据** ⇒ `Command` / `NodeFunc` 两行进**白名单** + **新增「等价程度 MUST NOT 变」断言**）· **执行记录回溯注记 2 处** —— B2F1 的 `tasks.md` / `research.md`（**只加注记 · 不改历史记录**）· B7F1 的 `plan.md` / `tasks.md`（同上）· **提示词初稿接线 2 处** —— `harness/features/B2F1_四类协议与图数据类.md` / `harness/features/B7F1_任务准备与super-step循环.md`（宪法 v1.8.0 的**接线动作** · 只接线 · 逐条最小改动）⇒ **MUST NOT** 改动其余任何 L1 符号 / B7F1 的契约 |
| ⑤ | **附带登记（既有偏差 · 不在本 feature 修）**：L1 的协议允许 `None`（= 不写状态 · **忠实镜像上游**）而 **B7F1 的运行时 V-4 拒绝它** ⇒ 登记为**遗留**（B7F1 的 parity 表未登记）⇒ **MUST NOT** 顺带放宽 B7F1 的 V-4 判据（改它 = 放宽判据 ⇒ 违宪） |
| ⑥ | **处置**：① spec 的 **FR-001 / FR-016 / H-4 / 裁定 21 / 引文差异 ⑩** 已落（**FR / SC 的编号与总数零变动**）；② **MUST 列入 `tasks.md` 的追认清单**（**阻断合入**）⇒ 追认文字落在 `harness/verification/B9F1/manual-verification.md`；③ **MUST NOT** 改宪法正文 · **MUST NOT** 改 Q8 / 立项书 §5.3（**C5 / C6 的条目本身不动**）· **MUST NOT** 新增门禁编号 |

**红线**：MUST **NOT** 改动 L1 的**符号集合与数量**（**18** 个）· MUST **NOT** 改动其余任何 L1 符号的签名
· MUST **NOT** 改 Q8 / 立项书的 **C5 / C6 条目** · MUST **NOT** 放宽 B7F1 的 **V-4** 判据 ·
MUST **NOT** 新增门禁编号 · MUST **NOT** 放宽任何判据。

### ⚠️ 登记项 R-8（**已落地 feature 的验收脚本漂移** + **人工验收复跑** · 需发起者签字）

**依据**：B9F1 的破冻结面返工**改动了 L1 的公开签名** ⇒ 凡**记载旧签名**的**人工验收记录**即失效
⇒ 宪法原则 V（人工验收是最终验收标准）+ 宪法 **v1.6.0**（**MUST NOT** 由实现者代签）。

| # | 内容 | 状态 |
|---|---|---|
| ① | `harness/verification/B2F1/acceptance.py` 的 **SC021** 断言「兼容矩阵逐符号覆盖公开符号面（**18** 个）」**已过期**（B2F2 交付时矩阵**合法地增补了门面的 5 个符号** ⇒ 矩阵共 **23** 行 ⇒ 该脚本未同步）⇒ **与本次返工无关**（矩阵的**符号集合**返工前后**完全相同**）⇒ **已按「补齐过期」修复**：期望值补为「契约层 18 ∪ 门面新增 5 = **23**」⇒ 断言**恢复为真**、**非放宽**（与 B7F1 的 R-3「事实性订正」同款） | ✅ 已修（124/124 PASS） |
| ② | **机械层已复跑并留证**：**B2F1 124/124 PASS** · **B2F2 76/76 PASS** · **B7F1 104/104 PASS** ⇒ 结论已记入 tasks **T042 ⑤** | ✅ 已完成（机械层） |
| ③ | **人工验收记录的复跑与签字**：L1 的公开签名已变 ⇒ B2F1 / B2F2 的人工验收记录中**记载旧签名**的部分**已失效** ⇒ **MUST 由发起者复跑** `harness/verification/<feature>/acceptance.py` 并**签字**（原则 V · **MUST NOT** 由实现者代签） | ✅ **已闭合（2026-11-11）** —— 发起者亲自复跑 **B2F1 124/124 · B2F2 76/76 · B7F1 104/104**（全 **PASS**）⇒ 三份记录的「**补充验收**」段已**如实转录**输出并标注「**发起者验收**」（**实施者未代签**） |
| ④ | **对 B2F1 / B7F1 的定向三件套核验**（等价于 `/speckit.analyze` 的**只读**读法）：已核 —— 「spec 已改 ⇒ plan / tasks 是否漂移」= **是**（执行记录里的旧签名表述）⇒ 已用**回溯修订注记**闭合（**只加注记 · 不改历史记录**）⇒ 残留漂移 == **0** | ✅ 已完成 |
| ⑤ | **B7F1 的两处「内核零越界标识符」断言因本 feature 落地而**过期**（**补齐过期**）—— B7F1 的禁用名清单**含** `Command`（彼时 `Command` 归 B9F1 ⇒ B7F1 的内核**不实现**它）⇒ 本 feature 落地后，`Command` 的**运行期语义**（`goto` / `update`）**由 L2 内核实现**⇒ `Command` **不再是**越界标识符 ⇒ **仅移除这一项**（`tests/runtime/test_superstep_purity.py` 的 `FORBIDDEN_NAMES` + `harness/verification/B7F1/acceptance.py` 的同名常量）⇒ **其余六项 / 七项逐字保留**（`invoke` / `stream` / `compile` / `StateGraph` / `Send` / `interrupt` / `async`）⇒ 判据**只移除一处**、**不放宽其余**（宪法 v1.6.0「MUST NOT 以此放宽任何门禁判据」）⇒ **B7F1 的验收脚本内容已变 ⇒ MUST 由发起者复跑并签字**（同 ③ 的义务） | ⏳ **待发起者复跑签字**（**阻断合入** · T039） |

**红线**：MUST **NOT** 由实现者代签人工验收 / 追认 · MUST **NOT** 借本 feature 顺带改 B2F1 的验收脚本
（属**另一次**修订）· MUST **NOT** 改宪法正文 · MUST **NOT** 新增门禁编号。

### ⚠️ 登记项 R-9（**破冻结面返工对后续 feature 的影响面** · 已接线 · 需追认）

**依据**：宪法 **v1.8.0**「跨 feature 承接的接线通则」—— 破 L1 冻结面**改变了下游 feature 看到的契约面**
⇒ 影响到的**指名** feature MUST **写入其提示词初稿** ⇒ 由其 spec 落成 **FR + 裁定**。

| # | 后续 feature | 返工带来的影响 | 处置 |
|---|---|---|---|
| ① | **B6F1**（构建器 · M2） | `NodeFunc.__call__` 增「**命令列表**」⇒ `add_node(name, fn)` **MUST 接受**该形态（**透传** ⇒ 零代码改动） | ✅ 已接线（**§2.1**） |
| ② | **B8F1**（条件边 + fresh 读 · M2） | `Command.update` 的写入**归源节点** ⇒ fresh 读**读得到**；`node_writes` 的**分组维度不变** ⇒ **零改动** | ✅ 已接线（**§2.1**） |
| ③ | **B10F1**（interrupt + resume · M1） | `Command` 作为**图的输入**不属 B9F1；L1 允许 `None` 而 B7F1 运行时拒绝它 ⇒ **既有偏差** ⇒ `resume` **不受**影响 | ✅ 已接线（**§2.1**） |
| ④ | **B11F1**（`Send` · M1） | `Send` 的落点 MUST 与「`goto` 落点 = **边触发源**空间」**同族**；上游 fan-out 用**一条** `Command` 的 `goto` 装**多个 `Send`** ⇒ **不需要**「命令列表」 | ✅ 已接线（**§2.1**） |
| ⑤ | **B12F1**（并发 · M1） | 「**多节点 × 多命令**」的归并顺序 MUST 由 B12F1 一并拍板（可复现 · 不受竞态影响） | ✅ **D-1 已扩充**（**§2** 的承接条款块内追加一条 · **只接线**） |
| ⑥ | **B22F1**（图渲染 · M3） | `goto` 可为**序列** ⇒ 渲染须画**多条边**；freegraph 的 `Command` **非泛型** ⇒ 目标只能来自**运行期**的跳转记录 ⇒ B22F1 **自行设计**该来源（**DR-1**） | ✅ 已接线（**§2.1**） |
| ⑦ | **B24F1**（兼容矩阵定稿 · M4） | 定稿 MUST **保留** B9F1 对 `Command` / `NodeFunc` 两行的更新（**零新增行** · **等价程度 MUST NOT 变**） | ✅ 已接线（**§2.1**） |
| ⑧ | **其余 12 个**（B7F2 / B7F3 / B8F2 / B13F1 / B14F1…B16F1 / B18F1…B21F1 / B23F1 / B25F1） | **零影响**（不碰节点返回值形态 / `node_writes` / `Command` 的类型面 / 兼容矩阵）⇒ **MUST NOT** 无谓接线 | 无需接线（**已核**） |

**红线**：MUST **NOT** 改动目标 feature 提示词初稿的**其余**内容（**只接线 · 逐条最小改动**）·
MUST **NOT** 越界实现下游 feature 的动作（尤其 ⑤ 的归并顺序归 **B12F1**、⑥ 的来源设计归 **B22F1**）·
MUST **NOT** 新增门禁编号 · MUST **NOT** 放宽任何判据。

### 门禁编号纪律

**本 feature MUST NOT 新增门禁编号** —— 既有 **G1–G30** 的编号连续性是 B3F1 data-model 的不变量
（「门禁总数 == 30 · 编号连续」）⇒ 本 feature **只改既有文件**、**不新增门禁脚本**：

| 既有门禁 | 对本 feature 的覆盖 |
|---|---|
| **G25**（导入图单向 · ARCH-1） | 本 feature **只改** `src/freegraph/runtime/superstep.py`（L2 · 目录条目）⇒ 自动纳入扫描；L2 → L3/L4/L5 的边数 == 0 即 SC-015。⚠️ **MUST NOT** 为新模块单独立注册表条目 |
| **G30**（全仓署名头） | 若新增源文件 ⇒ 署名头覆盖率 == 100%（SC-020）⇒ **无需**扩 G5 / G20 的硬编码清单 |
| **G4 / G24 / G26 / G27** | 零环境变量 / 零出站（FR-014 · SC-014） |
| **G3 / G21 / G22 / G23** | **零新增依赖**（连 `differential` 组都不需要）⇒ 依赖闭包 / 隔离环境 / 许可证断言恒绿 |
| **G2**（契约层零内部 import） | 本 feature 的用例**必须**住 `tests/runtime/`（**不得** import `freegraph.*`）⇒ **G2 恒绿** |
| **G29**（契约门禁载体 · C4 / C8 挂载点） | 本 feature **MUST NOT** 改动两条 `GATE-MOUNT:` 行 ⇒ G29 输出不变 |
| **G7 / G15 / G19**（公开面） | 契约层 **18** 个 / 门面 **7** 个符号**一字不动** ⇒ `freegraph.runtime` 的 **20** 个导出**不计入**公开面（L2 内部 API）｜⚠️ **G7 判的是「符号面恰为 18 个 · `__all__` 集合相等」** ⇒ **登记项 R-7** 放宽 `NodeFunc.__call__` 的**注解**（**不新增符号**）⇒ **G7 恒绿**；**G8**（矩阵逐符号覆盖 + 4 列）亦**恒绿** |
| **G9**（typing 构件上限 3.11） | 新增 / 修改代码的 typing 构件受检（AST 扫描 `src/freegraph/**`） |

> **⇒ 门禁编号总数仍为 30**（layer-registry.md 与 data-model 的不变量**零改动**）。

### 设计后复核（Phase 1 后 · 模板要求「Re-check after Phase 1 design」）

| 复核项 | 结论 |
|---|---|
| 宪法条款 | **无新增违反** —— Phase 1 产出的 5 份工件（`research.md` / `data-model.md` / `contracts/`×2 / `quickstart.md`）**全部**落在 `specs/` 内 ⇒ 依赖 / 许可证 / 商标 / 零出站四条红线**不受影响** |
| 门禁编号 | **仍为 30**（G1–G30）—— Phase 1 **未新增**任何门禁脚本或编号；改动落在既有文件 ⇒ 由 **G25** / **G30** 自动覆盖 |
| 公开面 | **零变更** —— `Command` 的对外导出沿用 L1 / 门面的既有位置；`freegraph.runtime` 的 **20** 个导出不动；契约层 **18** 个 / 门面 **7** 个符号**一字不动**；兼容矩阵**零新增行**（+ 既有两行**措辞更新 MAY** · FR-016 的口径） |
| 登记项 **R-1** | **仍然成立**（无图可跑 ⇒ 门禁 3 / 4 / 5 的三部分仍物理不可达成）⇒ 承接方与里程碑**未变** |
| 登记项 **R-2** | **新增**（spec 阶段的 9 条裁定缺发起者背书）⇒ 处置 = 标注来源 + **列入 tasks 的追认清单** ⇒ 判据**只收紧不放宽** |
| 登记项 **R-3** | **新增**（两处跨 feature 冻结面扩展：动态边字段 + V-4 接受面）⇒ 处置 = **本 plan 冻结字段名** + 追认 + 一条「**B7F1 契约措辞未走样**」的核对任务（R-3 ② 的核对点） |
| 登记项 **R-4** | **新增**（第三种内置异常）⇒ 处置 = 登记 + 追认 + **V-13 / V-14 可区分**断言 ⇒ 判据**只增不放宽** |
| 登记项 **R-5** | **新增**（下游承接 D-1 / D-3 的跨 feature 文档改动）⇒ 处置 = **只接线**（B12F1 / B19F1 的提示词初稿**已追加条款**）+ **复核任务** + 追认 |
| 与上游的等价性 | `contracts/upstream-parity.md` 给出 **12 条**语义点（**P-01…P-12**）+ **8 组**实测基线 + **3 条**刻意分叉（**X-1…X-3**）⇒ 满足 spec FR-017 / SC-020 |
| 事实性表述 | Phase 0 的复核发现 **2 处** spec 计数漂移（research **C-1 / C-2**）⇒ **已回写 spec**（**只更正事实**，未改任何判据）⇒ SC-001…SC-025 **全部仍成立** |
| 规模口径的可判定性 | 执行次数 / 调用次数 / 逐元素相等 / 集合相等 / 逐字相等 ⇒ 全部**可自动判定**（`command-contract.md` §9 的 **I-1…I-14**） |
| 遗留登记 | **DR-1**（上游 `Command` 是泛型 ⇒ 图渲染侧不可逐字照抄 · 归 B22F1）· **DR-2**（触发源机制差异 ⇒ 暴露口径归 B19F1）—— 全部**只登记 · 不改判据** |

---

## Project Structure

### Documentation (this feature)

```text
specs/b9f1-command-primitive/
├── plan.md                          # This file (/speckit.plan command output)
├── research.md                      # Phase 0 output —— D-01…D-10 上游实测取证 + DR-1…DR-2 遗留登记 + C-1…C-2 事实更正
├── data-model.md                    # Phase 1 output —— 实体模型 + 归一形状 + 动态边生命周期 + 校验规则 V-9…V-14 + 不变量 I-1…I-14
├── quickstart.md                    # Phase 1 output —— 可照抄的验证手册（闸口 V1–V12）
├── spec.md                          # 规格（**澄清 2 轮 10 问** · **19 条裁定** · FR-001~FR-023 · SC-001~SC-025 · 追溯表 23 行）
├── checklists/
│   └── requirements.md              # 规格质量清单（16/16）
├── contracts/
│   ├── command-contract.md          # 命令契约（返回值三形态 · goto/update 形态解析 · 触发落点 · 合并 · 失败信号 · 不变量）—— **唯一权威**
│   └── upstream-parity.md           # 与上游 LangGraph 的逐条对照（**12 条**）+ **8 组**实测基线 + **3 条**刻意分叉
└── tasks.md                         # Phase 2 output（/speckit.tasks —— 本命令不生成）
```

### Source Code (repository root)

```text
src/freegraph/
├── __init__.py                      # 既有 · **零改动**（顶层包惰性 · G1 / L-1）
├── graph.py                         # 既有 · **零改动**（门面 7 符号面 · G15 / G19）
├── _stategraph.py                   # 既有 · **零改动**
├── _primitives.py                   # 既有 · **零改动**（`Send` / `interrupt` 的未接线壳）
├── py.typed                         # 既有 · **零改动**（PEP 561）
├── contracts/                       # L1 契约层 · **零改动**（18 符号面 · G7 / G8）
│   └── types.py                     #   —— 本 feature **只读** `Command` / `Command.PARENT`（**不新增、不改字段**）
└── runtime/                         # L2 执行内核层（层注册表**已登记为目录条目** · **零改动**）
    ├── __init__.py                  # 既有 · **零改动**（导出面**仍 20** · 裁定 13）
    ├── errors.py                    # 既有（B5F1）· **零改动**
    ├── schema.py                    # 既有（B4F1）· **零改动**
    ├── reducer.py                   # 既有（B4F1）· **零改动**
    ├── channel.py                   # 既有（B5F1）· **零改动**
    ├── mapping.py                   # 既有（B5F1）· **零改动**
    ├── read.py                      # 既有（B5F2）· **零改动** —— `read_channels`（目标节点的入参来源）
    └── superstep.py                 # ★ **本 feature 的唯一落点**（归一子步骤 + 动态边表 + 失败信号分类）
                                     #   —— 只依赖标准库 + L1；**零第三方**；**四字段结果对象不动**

tests/
├── conftest.py                      # 既有 · **零改动**
├── contracts/                       # 既有（G1–G13）· **零改动**
│   └── test_contract_regressions.py # ★ **零改动**（两条 `GATE-MOUNT:` 行逐字未动）
├── facade/                          # 既有（G14–G20）· **零改动**
├── gates/                           # 既有（G21–G30）· **零改动**
└── runtime/                         # 本 feature 的测试（与既有 `tests/runtime/` **同目录**）
    ├── __init__.py                  # 既有（B4F1）· **零改动**
    ├── conftest.py                  # 既有（B4F1）· **零改动** —— **复用** `run_in_subprocess` 夹具
    ├── test_command_goto_update.py  # ★ 跳转 + 更新**同时生效**（A1 / A2 · SC-001 / SC-002）
    ├── test_command_merge_parity.py # ★ 三形态**共用同一条合并路径**（A3 · SC-003 · SC-004 · SC-023）
    ├── test_command_parent.py       # ★ `Command.PARENT` 与**保留名**的可判定失败（SC-005）
    ├── test_command_goto_errors.py  # ★ 非法跳转目标 / 非法形态 ⇒ 显式失败（SC-009）
    ├── test_command_noop.py         # ★ 空槽位 / 空列表 / `resume` 只被接受（SC-006 / SC-012）
    ├── test_command_goto_semantics.py # ★ 叠加 / END / 触发门槛 / 入参 / 生命周期（SC-007 / SC-008 / SC-010 / SC-023）
    ├── test_command_list.py         # ★ 命令列表（上游同款 · SC-021）
    ├── test_command_atomicity.py    # ★ 原子性覆盖 `Command` 路径（SC-013）
    ├── test_command_determinism.py  # ★ 确定性 + 调度状态不串扰（SC-019）
    ├── test_command_purity.py       # ★ 纯净性（零上游导入 / 零环境变量 / 零出站 / 无构建器依赖 · SC-014 / SC-016）
    └── test_command_contract.py     # ★ **契约守卫**（解析 contracts/command-contract.md 的 I-1…I-14 · SC-016）

harness/verification/B9F1/
├── acceptance.py                    # ★ **一键验收入口**（一条命令跑完全部闸口 · 退出码 0/1/2 · **B7F1** 裁定 37 的同款先例）
└── manual-verification.md           # ★ 人工验证记录（五段式 + 来源覆盖表 + **发起者追认** · R-1…R-5）

harness/features/B12F1_并发执行与错误传播.md
                                       # ★ **下游承接 D-1 的接线**（已改 · 只接线 · R-5）
harness/features/B19F1_TraceSink与current_span.md
                                       # ★ **下游承接 D-3 的接线**（已改 · 只接线 · R-5）

# ── 本 feature **改到**的既有文件（**二十四处** · 登记项 R-1…R-9） ──
src/freegraph/runtime/superstep.py     # ★ 归一子步骤 + 动态边表（`SchedulerState.dynamic_edges`）+ 失败信号分类
specs/b9f1-command-primitive/spec.md   # ★ R-3 / R-5 / R-6 · 事实性更正 C-1 / C-2 + 分析轮的三处收敛
specs/b9f1-command-primitive/plan.md   # ★ R-6 · 登记项 R-6 + Constraints / 源码树的同步订正
specs/b9f1-command-primitive/tasks.md  # ★ R-6 / R-7 · T007 / T010 / T012 / T018 / T030 / T041 的措辞与断言补齐（追溯表同步）
src/freegraph/contracts/protocols.py   # ★ R-7 · **破 L1 冻结面**：`NodeFunc.__call__` 的返回联合增补「命令列表」
specs/b2f1-contracts-protocols/contracts/public-api.md
                                       # ★ R-7 · 回溯修订（**5** 处：符号清单注释 / 逐符号表 / 上游对照行 / C5 行 / C6 行）
specs/b2f1-contracts-protocols/spec.md # ★ R-7 · 回溯修订（FR-001 的冻结口径 + 理由留痕）
specs/b7f1-superstep-loop/contracts/superstep-contract.md
                                       # ★ R-7 · 回溯修订（**V-4** 行 · 与 B9F1 的三形态不再矛盾）
specs/b7f1-superstep-loop/spec.md       # ★ R-7 · 回溯修订（**FR-009** 措辞）
tests/contracts/test_protocols.py       # ★ R-7 · 回溯修订（**冻结签名断言** · 与新联合同步）
tests/facade/test_facade_gates.py       # ★ R-7 · 回溯修订（**G8 的「既有行逐字未改」判据** · 两行进白名单 + 等价程度不变断言）
specs/b2f1-contracts-protocols/tasks.md    # ★ R-7 / R-8 · **执行记录回溯修订注记**（只加注记 · 不改历史记录）
specs/b2f1-contracts-protocols/research.md # ★ R-7 / R-8 · 同上（并说明「被否备选①」现被 B9F1 采纳）
specs/b7f1-superstep-loop/plan.md          # ★ R-7 / R-8 · **执行记录回溯修订注记**
specs/b7f1-superstep-loop/tasks.md         # ★ R-7 / R-8 · 同上
harness/features/B2F1_四类协议与图数据类.md      # ★ R-8 · **接线**（宪法 v1.8.0 · 只接线 · 最小改动）
harness/features/B7F1_任务准备与super-step循环.md # ★ R-8 · **接线**（同上）
harness/features/B6F1_StateGraph构建器.md           # ★ R-9 · **接线**（节点函数的返回形态）
harness/features/B8F1_条件边路由与fresh读.md        # ★ R-9 · **接线**（`node_writes` 的归属口径）
harness/features/B10F1_interrupt与resume.md         # ★ R-9 · **接线**（`Command` 两条路径的边界）
harness/features/B11F1_Send动态fan-out.md           # ★ R-9 · **接线**（`Send` 的落点与「命令列表」的关系）
harness/features/B12F1_并发执行与错误传播.md        # ★ R-9 · **D-1 已扩充**（命令列表的并发维度）
harness/features/B22F1_get_graph与draw_mermaid.md  # ★ R-9 · **接线**（`goto` 序列 ⇒ 多条边 · 非泛型 ⇒ 来源自设计）
harness/features/B24F1_打包分发与兼容矩阵.md        # ★ R-9 · **接线**（兼容矩阵的定稿口径）
README.md                                 # ★ R-6 · 兼容矩阵**既有 `Command` / `NodeFunc` 两行的措辞更新**（**零新增行** · 等价程度不变）
harness/features/B12F1_…md + harness/features/B19F1_…md
                                       # ★ R-5 · 下游承接 D-1 / D-3 的接线（只接线）
```

**Structure Decision**:

- **落 `src/freegraph/runtime/superstep.py`（改既有文件，不新增模块）** —— 层注册表**已登记**
  `src/freegraph/runtime/` 为 **L2** ⇒ **层注册表零改动**（spec FR-015）；⚠️ **MUST NOT** 为
  `runtime/` 下的新模块**单独立**注册表条目 ⇒ 会造成 L2 → L2 的横向依赖误判
  （层注册表 §0.2 规则 2 · G25 实现 `gate_G25_import_graph.py:59-60` 只在**不同注册表条目**间判层边）。
  ⇒ **理由**：本 feature 的产出是**「归一 + 动态边」两个子步骤** ⇒ 它们**必须**与既有的五阶段
  （触发判定 → 任务准备 → 任务执行 → 写入收集 → 写入合并）**同处一个模块**才能共享
  `_trigger_sources` / `_node_input` / `_collect_writes` / `_merge_writes` 的内部口径
  ⇒ **拆模块反而会制造 L2 内的横向 import**。
- **不新建 `command.py`** —— 备选方案：把「`Command` 的解释」单独放 `runtime/command.py` ⇒
  它必须被 `superstep.py` import ⇒ **同一注册表条目内的单元内部引用**（合法）但**徒增一层**；
  而 `Command` 的**类型**在 L1 ⇒ 运行时只需**解释**它 ⇒ 解释逻辑的**唯一实现点**放在
  `superstep.py` 内 ⇒ **单一实现点**原则（与「稀疏读只有一处实现」同款）。
- **写入复用 B7F1 的合并路径**（不新建合并器）—— 理由：C6 要求「未知 key 报错」，而**归一**把三种
  返回值压成**同一种内部形状** ⇒ 合并器**只见一种输入** ⇒ 「两条路径分叉」在**结构上**不可能发生
  （裁定 4 · 风险提示的正面防线）。
- **动态边表落在 `SchedulerState`**（不新建状态对象、不放图规格）—— 理由：B7F1 已把「已消费版本 /
  轮次计数 / 各通道版本」等**运行期**记录统一放在调度状态里（裁定 16 / 21）⇒ `goto` 目标**同址**
  才不出现第二套状态；放图规格会破坏「同一份规格可安全跑多次」；放模块级全局会跨运行串扰。
- **测试落在 `tests/runtime/`** —— 理由：门禁 **G2** 的内部 import 档扫描 `tests/contracts/**`
  ⇒ 那里**禁止** import `freegraph.*` ⇒ 本 feature 的用例**必须**住 `tests/runtime/`
  ⇒ **G2 恒绿**（沿用 B7F1 的同款口径）。
- **两份契约**（`command-contract.md` / `upstream-parity.md`）—— 沿用 **B3F1 的层注册表先例** +
  **B5F1 / B5F2 / B7F1 的契约先例**（机器可读 Markdown + `<!-- authority: yes -->` 标记）：
  ① `command-contract.md` 是**判据**（**唯一权威**）；
  ② `upstream-parity.md` 是**证据表**（逐条 `路径:行号` + 实测基线）⇒ **MUST NOT** 被测试解析
  （测试**直接断言行为** ⇒ 避免「判据与实现同源 ⇒ 自证」）。

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **宪法「质量门禁 3 / 4 / 5」的三部分在本 feature 物理不可达成**（`target.py` 原样可跑 · fake 模型轮 · 真实模型轮） | 三者**共享同一根因**：它们都要求**完整内核运行时**（编译 + 执行）存在，而 B9F1 按立项书 §5.2 只交付**`Command` 的运行期语义**（`StateGraph` = B6F1 · `compile` = B7F2 · `invoke` = B7F3 · 条件边 = B8F1）⇒ **任何 spec 设计都无法在本 feature 满足这三条** ⇒ 依宪法 **v1.6.0** 的窄口径通则处置（偏离登记 + 发起者追认 + 具名承接方） | **替代方案 A：硬写进 CI**（让验收脚本在「无图可跑」时判通过而不登记）⇒ **静默稀释宪法** + 门禁语义被扭曲 ⇒ **不可行**。<br>**替代方案 B：写一条永久红的 CI** ⇒ 违反「feature 必须能独立通过门禁」· PR-4 ⇒ **不可行**。<br>**替代方案 C：改宪法正文** ⇒ 违反「**MUST NOT** 以本条删改宪法正文」⇒ **不可行**。<br>**替代方案 D：把 B9F1 扩成「`Command` + 构建器 + invoke」** ⇒ 越过立项书的 feature 边界 ⇒ **不可行**。<br>**采用的处置**：**偏离登记（R-1）+ 发起者追认（`tasks.md` 的阻断合入任务）+ 承接条款已在目标 feature 的提示词初稿中既有**（B6F1 / B7F2 / B7F3 / B8F1 / B22F1 / B23F1 / B25F1）⇒ **红线判据一律不放宽**。 |
| **引入**第三种**内置异常**（`NotImplementedError`）⇒ 偏离 B7F1「一个 feature 只用两种内置异常」的不变量 | `Command.PARENT` 是**合法常量**、只是**本版本未实现子图** ⇒ 与「目标名写错了」（`ValueError`）**语义不同** ⇒ 用**不同的异常类型**分开表达，用户（及下游 freechain）可分别捕获「还没做」与「写错了」（澄清轮第 2 次 **Q2** · 发起者拍板） | **替代方案 A：一律用 `ValueError`** ⇒ 两类语义**混在一类**里 ⇒ 下游**无法分别捕获**（「v2 才有的能力」与「你拼错了名字」被混为一谈）⇒ **语义损失**（发起者**已否**）。<br>**替代方案 B：新增一个 L2 错误类型**（如 `UnsupportedFeatureError`）⇒ **破** L1 的冻结面（G7）⇒ **不可行**。<br>**替代方案 C：照抄上游的静默忽略** ⇒ 提示词**点名要避免**的「静默失效」⇒ **不可行**。<br>**采用的处置**：**内置 `NotImplementedError`**（**零新增错误类型** · L1 冻结面不动）+ 仓库既有用法同款（`interrupt()` 未接线）+ **可区分性断言**（SC-005）⇒ **登记项 R-4**（追认）⇒ 判据**只增不放宽**。 |
| **非法跳转目标 ⇒ 显式失败**（上游 **warning + 静默忽略**） | C6「未知 key 报错」的同款立场 + B7F1 的 V-2 同款（边的端点不在节点表 ⇒ 显式失败）⇒ 静默忽略会让流程「悄悄少跑一段」，最终产出**看起来正常**、实则缺了一半 ⇒ **极难排查** | **替代方案 A：照抄上游的静默忽略** ⇒ 无声失败 ⇒ 与 C6 的立场**直接冲突** ⇒ **不可行**。<br>**替代方案 B：只警告不失败**（折中）⇒ 仍是无声失败（只是多一行日志）⇒ **不可行**。<br>**采用的处置**：**显式失败**（`ValueError` · 点名目标）⇒ 登记为 parity 的**可观察分叉 X-1**（**只登记 · 不改判据**）。 |
| **`SchedulerState` 增一个带缺省字段** ⇒ **跨 feature 冻结面的扩展** | `goto` 目标必须被**记住**（直到源节点再次执行）⇒ 需要一处**运行期**存储；而 B7F1 已把「已消费版本 / 轮次计数 / 各通道版本」统一放在调度状态里 ⇒ **同址**才不出现第二套状态（澄清轮第 2 次 **Q5** · 发起者拍板） | **替代方案 A：另建一个 B9F1 专属状态对象** ⇒ 要改 B7F1 已冻结的**入口签名**（`run_super_step(spec, state)`）⇒ **B7F2 / B7F3 / B8F1 / B12F1 四个下游 feature 全要改** ⇒ **不可行**。<br>**替代方案 B：放进 `GraphSpec`** ⇒ 图规格是**静态**的 ⇒ 运行期的跳转记录会把「跑过几次」混进规格 ⇒ **破坏**「同一份规格可安全跑多次」（FR-004）⇒ **不可行**。<br>**替代方案 C：模块级全局变量** ⇒ **跨运行串扰**（同一进程跑两张图 ⇒ 互相污染）⇒ **不可行**。<br>**采用的处置**：**调度状态 + 一个带缺省值的字段**（`dynamic_edges`）⇒ `SchedulerState()` 的**构造签名与名字逐字不变** ⇒ 四个下游 feature **零改动** ⇒ **登记项 R-3**（追认 + 本 plan 冻结字段名）⇒ 判据**只收紧**（多了可断言的生命周期语义）。 |
| **节点返回值放宽到三种形态**（`dict` / `Command` / `list[Command \| dict]`）⇒ **放宽 B7F1 的 V-4 接受面** | 上游**支持**命令列表（`state.py:1456-1484` / `:1752-1758`）⇒ 保持上游一致 ⇒ **零兼容代价**（对 `target.py` / `acceptance.py` / C16 契约 / 官方文档口径**全部零影响** · 澄清轮第 2 次 **Q1** 的评估结论）；且「**放宽接受面**」是**协变安全**的（既有调用方**零破坏** · 与裁定 11 同款） | **替代方案 A：v1 不支持列表**（显式失败）⇒ 与上游**刻意分叉** ⇒ 照搬上游代码时「节点返回命令列表」的写法**直接报错** ⇒ **兼容代价**（发起者**已否**：偏好与上游一致 + 上游久经测试）。<br>**替代方案 B：只允许 `Command` 元素**（不接受混入 `dict`）⇒ 上游**允许**混入（`_get_updates` 的 `else` 分支）⇒ C 会**自造**一处与上游的分歧 ⇒ **无收益**。<br>**替代方案 C：为列表单开一条合并路径**⇒ 正是提示词 §10 点名的「两条路径迟早分叉」⇒ **不可行**。<br>**采用的处置**：**三形态归一为一种内部形状** ⇒ **一条**合并路径（裁定 4）⇒ 列表顺序 = 生效顺序（与上游 `updates.extend(...)` **逐字一致**）⇒ **登记项 R-3 ②**（追认）⇒ 判据**只增不放宽**（SC-021）。 |
