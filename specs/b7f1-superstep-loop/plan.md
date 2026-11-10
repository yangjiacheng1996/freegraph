# Implementation Plan: B7F1 · 任务准备与执行循环（super-step）

**Branch**: `b7f1-superstep-loop`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`
⇒ 无 `before_specify` 钩子；既有 7 个 feature 同样在 `main` 上开发） | **Date**: 2026-11-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b7f1-superstep-loop/spec.md`

**feature ID**: `B7F1`（**M1 运行时内核的第 4 个**（全局第 8 个 · 关键路径第 7 棒）· 前置 **B5F1 + B5F2** · 后续解锁 **B9F1**）

---

## Summary

交付 freegraph 的**调度内核**——**super-step 循环**：每轮「判定哪些节点被触发 → 准备任务 →
执行任务 → 收集写入 → 按通道语义合并写入 → 进入下一轮」。本 feature 交付的是**不依赖图构建器**的
运行时内核：调度循环 MUST 能用手写的图规格直接驱动与验收（立项书 §5.2 B7F1 行小目标第三条）。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **图规格**（`GraphSpec`） | 手写即可驱动的**纯数据**图定义 | 通道映射 + **保序**节点表 + 边表 + **预留的条件边字段**（本轮恒空） |
| **节点规格**（`NodeSpec`） | 「**订阅哪些通道 → 读 → 写**」 | 订阅集**既管触发、也管入参**（一个集合）· 节点函数 `f(state: dict) -> dict`（**C5**） |
| **触发判定 + 版本号** | 决定本轮**跑哪些节点** | 触发源分**通道** / **边**两类 · 统一按「**版本**比较」判定 · **不**依据「值是否变化」 |
| **初始化写入** | 跑**之前**由调用方直接写通道对象 = 「写入只由调度层发起」的**唯一豁免** | 走通道自身的 `update()` ⇒ **通道语义 / 归约器口径不绕道** · 版本恒为 **1** · 跑**之后** MUST NOT 成为触发依据（裁定 31） |
| **待写入（pending writes）** | 任务产出、**轮末统一合并** | 执行期间通道**正式值不动**（**C8** 的基础）· **按节点分组**（B8F1 的复用前提） |
| **写入合并** | 按通道**批量**合并 | 每通道**一次** `update(values)` ⇒ 归约型**按序归约**（**不**后写覆盖先写）· 覆盖型多写 ⇒ **显式失败** |
| **收敛判定** | 空任务集 ⇒ **立即终止** | 步数上限缺省 **25** ⇒ 超限抛 `GraphRecursionError` |
| **C4 回归推进** | 断言对象从「读取层产出」推进到「**真实节点收到的入参**」 | **读取层口径并存**（**不删**）· 挂载点两行**逐字不动** |

技术方案（调度层**只依赖标准库**，零第三方依赖）：

> ⚠️ **本表 = 摘要**（裁定 35 · 2026-11-11 分析轮第 3 次）：本表的「关键规则」列是**每条 MUST 的
> 一句话摘要** ⇒ **MUST 的完整口径以 `## Technical Context` 的 Constraints 表为准**（同源 ⇒
> 修改任一条 MUST 时 MUST **同步**两处）。

| 环节 | 手段 | 依据 |
|---|---|---|
| 模块落位 | `src/freegraph/runtime/superstep.py` ⇒ `runtime/` 已是**目录条目** ⇒ **层注册表零改动** | 裁定 17 · 层注册表 §0.2 规则 2 |
| 导出面 | `freegraph.runtime.__all__` **14 → 20**（6 个新符号）⇒ **L2 内部 API**、**不进**兼容矩阵 | 裁定 15 · FR-023 · SC-016 |
| 触发判定 | `∃ s ∈ sources(N) : has_value(s) ∧ version(s) > seen(N)[s]`（**两类触发源统一口径** · **逐触发源**） | 裁定 3 / **裁定 28** · FR-003 / FR-004 |
| **首轮触发** | 「**有值**」即算已写过一次（调度器首次见到有值的通道时记版本 1） | 裁定 21 · research **D-01**（上游 `_algo.py:1260-1278` **逐字同构**） |
| **版本归属** | 版本由**调度器**维护（记在 `SchedulerState`）⇒ **B5F1 的四个只读属性零改动** | 裁定 21 · research **C-2** |
| 节点入参 | **B5F2 的稀疏读**（`read_channels`）**限制到订阅集** ⇒ 与上游 `prepare_input` **逐字同构** | 裁定 2 · FR-008 · research **D-08** |
| 同轮顺序 | **节点表声明顺序**（节点表 MUST 保序） | 裁定 9（发起者拍板）· ⚠️ 与上游**名字序**不同 ⇒ parity **P-05** / **DR-2** |
| 写入合并 | **批量** `update(values)`（每通道一次）⇒ 归约型按序归约 | 裁定 5 · research **D-07**（上游**逐字同构**） |
| 覆盖型冲突 | **显式失败**（`InvalidChannelUpdateError` · B5F1 既有类型）⇒ **零新增错误类型** | 裁定 6 · FR-005 ② · SC-023 |
| 未知 key | **显式失败**（`InvalidUpdateError` · L1 已冻结）⇒ 与 **C6** 一致 · 与上游**分叉** | 裁定 7 · parity **P-07** |
| 原子性 | 一轮出错 ⇒ **本轮所有写入都不合并**（状态 = 轮次开始前）· **合并前快照 + 出错逐通道回滚**（`clear()` + `update([快照])` · 不套归约器）· **版本与值同进同退**（本轮出错 ⇒ 版本**不**推进） | 裁定 22 / **裁定 29** · FR-032 · SC-024 |
| 步末清空 | **只**对**路由型**调 `clear()`，**且只清「本轮未被写入的」**（**两个入口都执行** · 裁定 33） | 裁定 10（**plan 阶段实测收紧为 C**）· research **D-05** · 裁定 33 |
| **结果对象的跨轮累计** | 多轮入口：`executed` **累计** · `node_writes` 同名节点同通道**按轮次先后拼接** · 单轮入口 `steps` **恒为 1** | 裁定 34 · 契约 §5.3 · data-model §5 · SC-001 / SC-003 |
| **图规格校验** | **构造时**校验（V-1…V-3 · V-8）⇒ 失败信号 = 内置 **`ValueError`**（V-4 = `TypeError`） | 裁定 32 · 契约 §2.1.1 · data-model §2 / §6 |
| 收敛 | 任务集**为空** ⇒ 立即终止 ⇒ 与上游 `_loop.py:657-660` **逐字同构** | FR-010 · research **D-10** |
| 步数上限 | 缺省 **25** ⇒ 与上游 `DEFAULT_RECURSION_LIMIT` **逐字一致** | 裁定 24 · research **D-11** |
| 条件边字段 | **预留**（本轮恒空 · 非空即**显式失败**）⇒ B8F1 **只需填值** | 裁定 25 · FR-033 · 下游承接 **D-1** |
| 上游的隔离 | 内核**零上游导入** ⇒ **不需要** `differential` 组 ⇒ **断网**可跑完验收 | FR-019 / FR-022 · SC-014 / SC-018 |

**零新增公开 API、零新增错误类型、零新增门禁编号**：契约层 **18** 符号面与门面 **7** 符号面**一字不动**
（G7 / G15 / G19 恒成立）；`freegraph.runtime` 的导出从 **14 → 20** 个符号（**L2 内部 API**，
不进兼容矩阵）；`langgraph` **不写进任何依赖声明**（Phase 0 的取证 venv 建在**仓库外**）。

**上游核实已在 Phase 0 完成**（`langgraph 1.2.11` · 仓库外临时 venv · **不进仓库**）⇒ 详见
[research.md](./research.md) §1（**D-01…D-12**）与
[contracts/upstream-parity.md](./contracts/upstream-parity.md)（**13 条** + **6 条**实测基线）。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`pyproject.toml` 的 `requires-python = ">=3.11"`）；
**typing 构件上限 = 3.11**（宪法「运行时环境基线」）—— 本 feature 用到的构件**全部 ≤ 3.11**：
`collections.abc.Mapping` / `Sequence` / `Callable` · `dataclasses.dataclass`（标准库）·
`typing.Any` / `TypedDict`（仅测试侧）· `abc`。
**MUST NOT** 使用 `TypeAliasType`(3.12) / `override`(3.12) / `ReadOnly`(3.13) / `TypeIs`(3.13)
或 PEP 695 `type` 语句。**主判定 = CI 矩阵最低档 3.11 跑全量测试**。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []` · 沿用现状）。
**开发期**：`pytest` / `packaging`（既有 `[dependency-groups] dev`）—— **零新增**。
⚠️ **本 feature 不引入任何新依赖组**：`langgraph` **仅**在 Phase 0 的**仓库外临时 venv** 里用过
⇒ `pyproject.toml` **零改动** ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿（**未被触碰**）。
⚠️ 覆盖率工具**也不进依赖**（沿用 B5F1 / B5F2 的口径）⇒ 开发期临时安装、实测输出记入人工验证记录。

**Storage**: N/A —— 本 feature 无运行时持久化（checkpoint 属 **B14F1**）。
**仓库内的权威工件** = **纯文本 Markdown 契约**（两份）：
[superstep-contract.md](./contracts/superstep-contract.md)（调度契约 · **唯一权威**）·
[upstream-parity.md](./contracts/upstream-parity.md)（上游对照 · **证据表**）。

**Testing**: pytest + 标准库 `collections.abc` / `dataclasses` / `typing`。
**需要子进程的断言**（SC-014 的「内核路径零上游导入」· SC-018 的「零环境变量 / 零出站」）
**必须在子进程中执行** ⇒ **复用 B4F1 已有的 `tests/runtime/conftest.py` 夹具 `run_in_subprocess`**
（session 级）⇒ **既有 conftest 零改动**。

**Target Platform**: 任意 CPython 3.11+ 平台（Linux / macOS / Windows）。
CI 的 `testpaths = ["tests"]` ⇒ 新增的 `tests/runtime/test_superstep_*.py` **自动被收集**。

**Project Type**: library（Python 库；发行名 = 导入名 = `freegraph`；D1 决议：不拆独立发行包）。

**Performance Goals**: **N/A（不设时间预算）** —— 调度是**纯内存**、**单遍遍历**、无 I/O / 无网络 / 无锁。
**规模口径**用**结构口径**表达：触发判定是 `O(节点数 × 订阅数)`；合并是 `O(写入数)`；
待写入的空间 `O(本轮写入数)`（轮末即释放）。
⚠️ **MUST NOT** 用墙钟耗时做断言（CI 假红）。

**Constraints**（**主要**来自 spec 的 MUST 条目；未逐条列出的 FR 见 `tasks.md` 的追溯表）：

| 约束 | spec 条目 |
|---|---|
| 只依赖**标准库**；MUST NOT import `langchain*` / `langgraph*` / `langsmith` / `pydantic` / `typing_extensions` | FR-022 · SC-014 |
| 内核路径 MUST NOT import `langgraph` / `langchain*` / `langsmith`（**本 feature 零上游依赖**） | FR-019 · SC-014 |
| MUST **NOT** 读取**任何**环境变量；零出站；零文件 I/O；导入**无副作用** | FR-021 · SC-018 |
| 层纪律：L2 只向下依赖 L1；MUST NOT import L3 / L4 / L5 | FR-020 · SC-015 |
| 一个 super-step = 触发判定 → 任务准备 → 任务执行 → 写入收集 → 写入合并（**顺序固定**） | FR-001 · SC-001 |
| 触发判定 MUST 依据**版本号**；MUST NOT 依据「值是否变化」 | FR-002 · SC-003 |
| 「**有值**」即算已写过一次（调度器首次见到有值的通道时记版本 1）⇒ 首轮能触发 | FR-002 · 裁定 21 · SC-003 |
| 版本由**调度器**维护 ⇒ 通道对象 MUST NOT 新增版本属性（B5F1 冻结面） | FR-002 · 裁定 21 · SC-015 |
| 两类触发源（**通道** / **边**）**统一**按版本比较；标识空间 MUST 分离 | FR-003 · SC-003 |
| 「已消费版本」MUST 存于**独立的调度状态对象**（调用方持有）⇒ 同一份规格可安全跑多次 | FR-004 · 裁定 16 · SC-013 |
| 写入合并 MUST **批量**调一次 `update(values)`；MUST NOT 逐次调用 | FR-005 · SC-002 |
| 覆盖型通道同轮多写 ⇒ **显式失败**（`InvalidChannelUpdateError`） | FR-005 ② · SC-023 |
| 未知 key ⇒ **显式失败**（`InvalidUpdateError` · L1） | FR-007 · SC-007 |
| 执行期间通道**正式值 MUST NOT** 被改写；待写入 MUST **按节点分组** | FR-006 · SC-008 |
| 节点入参 = **订阅集 ∩ 有值集**（由 B5F2 的稀疏读产出） | FR-008 · SC-009 |
| 节点函数 MUST 以 `f(state: dict) -> dict` 被调用；返回 `None` / 非 `dict` ⇒ 显式失败 | FR-009 · SC-001 |
| 空任务集 ⇒ **立即终止** | FR-010 · SC-006 |
| 步数上限缺省 **25**；超限 ⇒ `GraphRecursionError`（对外载体归 B13F1） | FR-011 · SC-006 |
| MUST 能被**手写图规格**驱动；MUST NOT 依赖 `StateGraph` / `compile()` | FR-012 · SC-005 |
| 同轮执行顺序 = **节点表声明顺序**（节点表 MUST 保序） | FR-013 · SC-013 |
| 步末 MUST **只**对**「本轮未被写入的」路由型**通道调 `clear()`（**单轮入口同样执行** · 裁定 33） | FR-014 · SC-012 |
| **图规格校验 MUST 在构造时执行**；失败信号 MUST 逐条唯一（V-1 / V-2 / V-3 = 内置 `ValueError` · V-4 = 内置 `TypeError`） | SC-015 · 裁定 32 |
| 多轮入口的 `executed` **累计** / `node_writes` **按轮次先后拼接** / 单轮入口 `steps` **恒为 1** / 两入口的已消费版本**不串扰** | SC-001 / SC-003 · FR-004 · 裁定 34 |
| 节点异常 MUST **原样**传播 | FR-015 · SC-020 |
| C4 回归 MUST 断言**真实节点收到的入参**；**读取层口径并存**；挂载点**逐字不动** | FR-016 / FR-017 / FR-018 · SC-009 / SC-010 / SC-011 |
| 一轮 super-step MUST 是**原子**的（本轮出错 ⇒ 所有写入都不合并） | FR-032 · SC-024 |
| 「条件边」字段 MUST **预留**（本轮恒空 · 非空即失败） | FR-033 · SC-025 |
| 既有冻结面 MUST **一字不动**；MUST **NOT** 新增门禁编号 | FR-024 / FR-025 · SC-015 |
| **导出面**：`freegraph.runtime.__all__` **14 → 20**（新增 **6** 个符号）· MUST **NOT** 进 API 兼容矩阵 · MUST **NOT** 触碰 L1 的 **18** 符号面或门面的 **7** 符号面 | FR-023 · SC-016 |
| **图规格的通道映射 MUST 是**可变** `dict`**（`GraphSpec.channels` 可增补内部通道）· MUST **NOT** 用只读映射（`MappingProxyType`） | FR-034 · SC-015 |
| 新源文件 MUST 带**署名头**且 docstring 是首个语句；上游引用 MUST 标**版本 + `路径:行号`** | FR-026 / FR-029 · SC-019 |
| 新增代码**行 / 分支覆盖率 == 100%**；用例 MUST NOT 经由图构建器 | FR-027 · SC-017 |
| MUST **NOT** 实现 `invoke` / `stream` / `compile` / `StateGraph` / 并发 / `Command` / `interrupt` / `Send` / 条件边求值 / checkpoint / async | FR-028 · SC-015 |
| **初始化写入豁免**：跑**之前**调用方 MAY 直接向通道对象写初始值（**唯一**豁免 · 走通道自身的 `update()` ⇒ 通道语义不绕道）· 跑**之后** MUST NOT 成为触发依据 | FR-001 / FR-002 · 裁定 31 · SC-003 |
| 人工验证记录（五段式 + 来源覆盖表）+ **偏离登记 + 发起者追认** | FR-030 / FR-031 · SC-021 / SC-022 |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 通过项（逐条）

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith 依赖 · 自身零出站 · 零环境变量） | FR-019 / FR-021 / FR-022 · 既有 **G24**（配置层扫描 `src/freegraph/**`）· **G26**（网络静态扫描）· **G27**（零出站动态） | ✅ |
| 原则 II（内核纯净 · 状态语义 MUST 与 LangGraph 等价） | FR-022（零依赖）· **本 feature 零上游依赖**（连 `differential` 组都不需要）· **G3 / G21 / G22 / G23**（依赖闭包为空集）· `contracts/upstream-parity.md`（**13 条**逐条对照 + **6 条**实测基线）承载等价性 | ✅ |
| 原则 III（验收契约优先 · `target.py` 只读） | 本 feature **零改动** `target.py`；C4 的节点边界断言用**同名 key**（`messages` / `llm_calls`）⇒ 守住 `target.py:100` 的 `state.get('llm_calls', 0) + 1` | ⚠️ **「`target.py` 原样可跑」本 feature 物理不可达成** ⇒ 见**登记项 R-1** |
| 原则 IV（可诊断性） | N/A（本 feature **无运行期可观测面**；诊断靠既有错误类型的结构化字段 `key` / `invalid_keys` / `recursion_limit`） | ✅ 边界内 |
| 原则 V（人工验收是最终验收标准） | 人工验证记录（五段式 + 来源覆盖表 · SC-021） | ⚠️ **门禁 5 的「真实模型一轮」不适用** ⇒ 见**登记项 R-1** |
| 原则 VI（规格驱动 · tasks 可逐条勾选） | 本 plan + `tasks.md`（含 FR ↔ SC 追溯表） | ✅ |
| 原则 VII（职责边界 · 契约 C1–C27） | FR-009 / FR-012 = **C5** 的执行侧落地；FR-005 / FR-007 = **C6** 的执行侧落地；上游 MUST NOT import L3/L4/L5 | ⚠️ **门禁 3 的 C8 回归**不在本 feature ⇒ 见**登记项 R-1**；✅ **C4 的「节点边界」在本 feature 闭合**（承接 H-1） |
| 原则 VIII（证据与术语纪律） | `research.md` §1 每条决策附**实测方法 + 真实输出**（D-01…D-12 · 核实版本 `langgraph 1.2.11`）；上游引用标 `路径:行号`；**事实性表述的更正已登记**（research §3 的 C-1 / C-2） | ✅ |
| 原则 IX（许可证与商标红线 · NON-NEGOTIABLE） | **零新增依赖** ⇒ `THIRD_PARTY_NOTICES` **无需变更**；**零品牌资产**（重写语义，不复制上游代码） | ✅ |
| 原则 X（文档合规 + 源文件署名头） | FR-026（署名头 · 既有 **G30** 全仓扫描自动覆盖新文件）· 兼容矩阵**零新增行**（须在人工记录中显式记「无新增」） | ✅ |
| 运行时环境基线（Python 3.11 · typing 上限 3.11） | 本 feature 只用 ≤ 3.11 构件（Technical Context 已逐项列出）· 最低档 3.11 跑全量测试 | ✅ |
| 依赖白名单 / 黑名单（包层 · 配置层 · 网络层） | **零新增运行时依赖** ⇒ **G3 / G21 / G23 / G24 / G26 / G27** 恒绿 | ✅ |
| **跨 feature 承接的接线通则（v1.8.0）** | 上游 **H-1**（B5F2 → B7F1 · C4 节点边界）**已写入** B7F1 的提示词初稿（`harness/features/B7F1_…md` **§2** / **§9** / **§10** · ⚠️ **以小节号为准** —— 行号会随文件追加漂移）⇒ 本 feature 只需**复核措辞**；**H-2 / H-3 / H-4 / H-5**（B5F1 → B7F1 的三条口径交接 + B5F2 → B7F1 的稀疏读唯一实现）**已于 2026-11-11 追补写入** B7F1 的提示词初稿（§2）与 `harness/features/README.md` 的 B7F1 行 ⇒ 见**登记项 R-5**；下游 **D-1**（条件边字段预留 → B8F1）**MUST 在本 feature 接线** ⇒ 见**登记项 R-2**（落点 = tasks **T050** · ⚠️ **T050 ≠ T062** —— **T062** 是 **R-5** 的上游承接接线）；**裁定 26 / 27** 冻结的是**跨 feature 接口**且由**分析轮**拍板 ⇒ 须发起者背书 ⇒ 见**登记项 R-4**；**Q13**（Phase 2 收窄的任务组织决策）同属「分析轮拍板 · 无发起者背书」⇒ 并入 **T053** 的追认清单（⑤）；**裁定 28 / 29 / 30 / 31** 由 2026-11-11 分析轮的**发起者本人**拍板 ⇒ 无需追认；**裁定 36**（第 6 次一致性订正）**只改文档 · 不改判据** ⇒ 无需追认 | ⚠️ **R-2 / R-4 / R-5** |
| 质量门禁 1 / 2 / 6 / 7 | ① 规格 + tasks 可勾选 ② 依赖**零新增** ⑥ 证据（research + 对照表 + 来源覆盖表）⑦ 文档合规（署名头 + 兼容矩阵零新增） | ✅ |
| 质量门禁 3 / 4 / 5 的**内核运行时相关部分** | ⚠️ **物理不可达成** ⇒ **登记项 R-1**（偏离登记 + 发起者追认） | ⚠️ **见 R-1** |
| 发布门禁（发行产物纯度） | 本 feature **不接入**（B24F1）· 新增代码在 `src/freegraph/runtime/` 内 ⇒ **不污染**产物纯度；**零新增依赖** ⇒ sdist / wheel 零变更 | ✅ 边界内 |

### ⚠️ 登记项 R-1（宪法「质量门禁 3 / 4 / 5」的偏离登记 · 需发起者追认）

**依据**：宪法 **v1.6.0**「质量门禁的分阶段落地与发起者追认」（**窄口径**通则 · 首次适用 = B3F1）。
**本 feature 与 B5F1 / B5F2 的 R-1 同根因**（都需要**完整内核运行时**才能跑通验收基线）⇒
**沿用既有承接机制**，MUST NOT 新造。

| # | 被偏离的**具体门禁项** | 不可达成的根因 | 判据未被放宽的论证 | 承接方（feature ID + 里程碑） | 承接机制 |
|---|---|---|---|---|---|
| ① | **门禁 3** 的「**`harness/demo/target.py` 原样可跑**」 | 本 feature 按立项书 §5.2 只交付**调度内核**（`StateGraph` = **B6F1** · `compile()` = **B7F2** · `invoke()` = **B7F3** · 条件边 = **B8F1** · `get_graph` = **B22F1** · PNG = **B23F1**）⇒ **无图可编译、无入口可调** ⇒ 脚本物理跑不到验收点 | 固定脚本**一字未改**；本 feature 的 C4 断言用**同名 key**（`messages` / `llm_calls`）⇒ 与脚本第 100 行的 `state.get('llm_calls', 0) + 1` **同形**；**判据未放宽** | **B6F1 + B7F2 + B7F3 + B8F1 + B22F1 + B23F1**（M2）· **B25F1**（M4） | **已就位**：B3F1 的裁定 22 已把「fake 轮 / 真实模型轮」的承接条款写入各目标 feature 的提示词初稿 |
| ② | **门禁 3** 的 **C8**（条件边 fresh 状态） | fresh 读**原语**在 **B5F2**；**路由语义 + 独立回归测试**属 **B8F1**（M2） | 本 feature 交付 C8 的**前提**（待写入隔离 FR-006 + **按节点分组**）⇒ C8 的**判据未改** | **B8F1**（M2） | **已就位**：挂载点 `GATE-MOUNT: C8 · status=not-landed · owner=B8F1`（本 feature **MUST NOT** 改动 · FR-018 / SC-011） |
| ③ | **门禁 4** 的「**fake 模型跑通验收基线的一轮**」与**门禁 5** + 原则 V 的「人工验证记录含**真实模型一轮**」 | 两者都要求**完整内核运行时**（编译 + 执行）⇒ 属 **B7F2 / B7F3** ⇒ 本 feature **无图可跑** | CI **不写**一条永久红的断言（违宪 PR-4）；五段式记录 + 来源覆盖表**照常落地**（FR-030 · SC-021） | **B7F2 + B7F3**（M2）· **B25F1**（M4） | **已就位**（同上 · B3F1 裁定 22） |

**✅ 本 feature 相对 B5F2 的 R-1 的一处「收敛」**：**C4 的「节点边界」断言在本 feature 闭合**
（承接 **H-1** · FR-016 / FR-017）⇒ 宪法质量门禁第 3 项中「C4 / C8 两条独立回归测试」的
**C4 一条**的**契约边界完整闭合**（B5F2 只闭合到读取层口径）⇒ 门禁 3 的缺口**只剩 C8 一条**。

**红线（未被触碰）**：依赖红线（`langsmith` / `langchain*` / `langgraph*`）· 许可证红线 · 商标红线 ·
零出站红线 —— **全部在本 feature 照常执行**（FR-019 / FR-021 / FR-022 + G3 / G21 / G22 / G23 / G24 / G26 / G27）。

**⇒ 请发起者在合入前追认此登记项**（落点：`tasks.md` 的一条**阻断合入**的追认任务 ·
追认文字 MUST 落在 `harness/verification/B7F1/manual-verification.md`）。

### ⚠️ 登记项 R-2（**下游承接 D-1** 的跨 feature 文档改动 · 需发起者追认）

**依据**：宪法 **v1.8.0**「跨 feature 承接的接线通则」—— 本 feature 的规格中出现了**指名下一棒
feature（ID + 里程碑）**的跨 feature 义务（**D-1**）⇒ 该条款 MUST 写入**目标 feature 的提示词初稿**
⇒ 由目标 feature 的 spec 落成 **FR + 裁定** ⇒ 其 tasks 与契约同步接线。

| # | 动作 | 边界 | 落点 |
|---|---|---|---|
| ① | 在 `harness/features/B8F1_条件边路由与fresh读.md` 中**写入**：「B7F1 的手写图规格**预留了一个『条件边』字段**，本轮**恒为空**、填值即**显式失败**；B8F1 **只需填值**即可复用，无需改造 B7F1 的调度内核」 | **只接线** · 逐条最小改动 · MUST NOT 改动该文件的其余内容 | spec **FR-033** / **裁定 25** / **SC-025** · 下游承接 **D-1** |
| ② | 同步更新 `harness/features/README.md` 的 B8F1 行：**补「B7F1 侧**预留**了条件边字段」**的说明（**两侧各自填值**：B7F1 的 `GraphSpec.conditional_edges` + B5F2 差分夹具的**同名字段** ⇒ **不新造第三套**）—— ⚠️ 现有 B8F1 行已含「条件边字段已预留」字样，但指的是 **B5F2 差分夹具侧** ⇒ **MUST NOT** 视为已满足（措辞与 tasks **T050** 的 ⚠️ 一致 · 裁定 36） | 同上 | 同上 |
| ③ | 在 `tasks.md` 落一条**可勾选**的接线任务（**T050** · 下游承接 **D-1** 的文档改动）+ 一条**复核**任务（**T049** · 复核上游 **H-1** 在 B7F1 提示词初稿中的措辞未走样）—— ⚠️ **T050 ≠ T062**：**T050** = 下游承接 **D-1**（B7F1 → B8F1）· **T062** = 上游承接 **H-2…H-5**（B5F1 / B5F2 → B7F1 · 登记项 **R-5**）⇒ 两者**不可混用**（裁定 36 订正） | 复核**不重写** | 宪法 v1.8.0 |

**红线**：MUST **NOT** 越界实现 B8F1 的条件边**求值**（FR-028 / FR-033 · 显式失败即止）·
MUST **NOT** 新增门禁编号 · MUST **NOT** 放宽任何门禁判据。

### ⚠️ 登记项 R-3（**spec 的 FR-014 订正** · plan 阶段上游实测 · 已回写）

**依据**：spec **FR-029**（上游取证的行号纪律）+ 宪法原则 VIII（事实性结论 MUST 附来源）。

| # | 内容 |
|---|---|
| ① | Phase 0 实测（research **D-05** · `langgraph/pregel/_algo.py:333-341`）发现：上游步末**只清「本步未更新」的通道** ⇒ **本步写过的路由型通道的值存活到下一轮** ⇒ 原 FR-014（「步末对**全部**路由型通道调 `clear()`」）与之**不符** |
| ② | **已回写 spec**：FR-014 收紧 + SC-012 同步 + 裁定 10 由 B **收紧为 C**（**只补事实 · 判据只收紧不放宽**）⇒ **SC-001…SC-025 全部仍成立** |
| ③ | **理由**：B8F1 的条件边路由要读到「**本节点本次写入**」⇒ 路由通道的值**必须**存活到下一轮 ⇒ 裁定 10 的 B 会**破坏 C8** |

### ⚠️ 登记项 R-4（**裁定 26 / 27 的拍板来源** · 分析轮拍板 ⇒ 需发起者追认）

**依据**：宪法 **v1.8.0**「跨 feature 承接的接线通则」—— 裁定 **26**（节点入参的判定对象与
key 顺序）与裁定 **27**（两个入口的调度状态接收口径）冻结的是**跨 feature 的接口**
（**B7F2**（`compile()`）· **B7F3**（`invoke()`）· **B9F1**（`Command`）· **B12F1**（并发）
全部照它写）⇒ **MUST** 具备**发起者**背书。

| # | 内容 |
|---|---|
| ① | 裁定 26 / 27 由 **2026-11-10 分析轮**拍板（**非**澄清轮的发起者答复）⇒ 在 `spec.md` 的 `## Clarifications` 中**逐条标注**来源（**已落**） |
| ② | MUST **列入 `tasks.md` 的「发起者追认」清单**（`tasks.md` **T053** · **阻断合入**）⇒ 追认文字落在 `harness/verification/B7F1/manual-verification.md` |
| ③ | 追认前**不得**视作已获发起者背书；**MUST NOT** 以此放宽任何判据（两处裁定均**只收紧**判据：子映射顺序固定 + 入口接收口径固定） |

**红线**：MUST **NOT** 改宪法正文 · MUST **NOT** 写一条永久红的 CI · MUST **NOT** 越界实现
**B8F1** 的条件边求值。

### ⚠️ 登记项 R-5（**上游承接 H-2…H-5** 的口径一致性补齐 · 需发起者追认）

**依据**：宪法 **v1.8.0**「跨 feature 承接的接线通则」—— **触发条件（窄口径 · MUST）** =
「某个 feature 的规格中出现了**指名下一棒 feature（ID + 里程碑）**的跨 feature 义务」。

| # | 内容 |
|---|---|
| ① | **事实核验（2026-11-11 分析轮）**：**H-2 / H-3 / H-4 / H-5** 的上游原文（`specs/b5f1-channels/contracts/channel-contract.md:159` **B-2** · `specs/b5f1-channels/contracts/upstream-parity.md:44` **S-05** / `:34` **P-12** · `specs/b5f1-channels/spec.md:808` FR-023 ① · `specs/b5f1-channels/research.md` **D-14** · `specs/b5f2-sparse-state-read/spec.md` FR-038）**只指名了 feature ID、未指名里程碑**；且 **B5F1 自己的 `tasks.md`** 的具名承接方名单 = **B5F2**(C4·M1) · **B8F1**(C8·M2) · **B7F2 / B7F3**(fake 轮) —— **不含 B7F1(M1)** ⇒ **H-2…H-5 严格落在该 MUST 适用范围之外** ⇒ **不构成宪法 MUST 冲突**（**MUST NOT** 据此改宪法正文） |
| ② | **原 plan 的事实性陈述错误（已订正）**：原表述「H-1…H-5 … **已写入** B7F1 的提示词初稿」⇒ **不成立**（实测该文件只含 **H-1**）⇒ 已按**原则 VIII**（事实性表述 MUST 附来源）订正 |
| ③ | **处置（口径一致性补齐）**：本 feature 按**更严口径**承接 ⇒ 已把 **H-2 / H-3 / H-4 / H-5** **追补写入** `harness/features/B7F1_任务准备与super-step循环.md` §2 与 `harness/features/README.md` 的 B7F1 行（**只接线 · 逐条最小改动**）⇒ 使「提示词初稿 ↔ spec ↔ 上游契约」三方一致 |
| ④ | **落点**：`tasks.md` 的 **T062**（接线）· 追认文字落 `harness/verification/B7F1/manual-verification.md` |

**红线**：MUST **NOT** 改动宪法正文（窄口径**未被违反** ⇒ 无原则冲突）· MUST **NOT** 改动目标
feature 提示词初稿的**其余**内容（只接线）· MUST **NOT** 越界实现上游已交付的能力
（步末清空 / 写入路径 / 可变映射 / 稀疏读**均已在 B5F1 / B5F2 落地**，本 feature 只**消费**）·
MUST **NOT** 新增门禁编号 · MUST **NOT** 放宽任何门禁判据。

### 门禁编号纪律

**本 feature MUST NOT 新增门禁编号** —— 既有 **G1–G30** 的编号连续性是 B3F1 data-model 的不变量
（「门禁总数 == 30 · 编号连续」）⇒ 新模块由**既有门禁自动覆盖**：

| 既有门禁 | 对本 feature 的覆盖 |
|---|---|
| **G25**（导入图单向 · ARCH-1） | 新增的 `src/freegraph/runtime/superstep.py` = **L2**（层注册表已登记为**目录条目**）⇒ 自动纳入扫描；L2 → L3/L4/L5 的边数 == 0 即 SC-015。⚠️ **MUST NOT** 为该模块**单独立**注册表条目 ⇒ 会造成 L2 → L2 横向依赖误判 |
| **G30**（全仓署名头） | 新建源文件的署名头覆盖率 == 100%（SC-019）⇒ **无需**扩 G5 / G20 的硬编码清单 |
| **G4 / G24 / G26 / G27** | 零环境变量 / 零出站（FR-021 · SC-018） |
| **G3 / G21 / G22 / G23** | **零新增依赖**（连 `differential` 组都不需要）⇒ 依赖闭包 / 隔离环境 / 许可证断言恒绿 |
| **G2**（契约层零内部 import） | ⚠️ **本 feature 的新约束**：`tests/contracts/**` **禁止** import `freegraph.*` ⇒ 调度内核的用例**必须**住 `tests/runtime/` ⇒ **G2 恒绿**（SC-011 / SC-015） |
| **G29**（契约门禁载体 · C4 / C8 挂载点） | 本 feature **MUST NOT** 改动两条 `GATE-MOUNT:` 行（FR-018）⇒ G29 输出不变（SC-011） |
| **G7 / G15 / G19**（公开面） | 契约层 **18** 个 / 门面 **7** 个符号**一字不动** ⇒ `freegraph.runtime` 的 14 → 20 个导出**不计入**公开面（L2 内部 API） |
| **G9**（typing 构件上限 3.11） | 新模块的 typing 构件受检（AST 扫描 `src/freegraph/**`） |

> **⇒ 门禁编号总数仍为 30**（layer-registry.md 与 data-model 的不变量**零改动**）。

### 设计后复核（Phase 1 后 · 模板要求「Re-check after Phase 1 design」）

| 复核项 | 结论 |
|---|---|
| 宪法条款 | **无新增违反** —— Phase 1 产出的 5 份工件（`research.md` / `data-model.md` / `contracts/`×2 / `quickstart.md`）**全部**落在 L2 与 `specs/` 内 ⇒ 依赖 / 许可证 / 商标 / 零出站四条红线**不受影响** |
| 门禁编号 | **仍为 30**（G1–G30）—— Phase 1 **未新增**任何门禁脚本或编号；新增模块由 **G25** 与 **G30** 自动覆盖 |
| 公开面 | **零变更** —— 6 个新符号全部属 **L2 内部 API**；契约层 **18** 个 / 门面 **7** 个符号**一字不动**；兼容矩阵**零新增行** |
| 登记项 **R-1** | **仍然成立**（无图可跑 ⇒ 门禁 3 / 4 / 5 的三部分仍物理不可达成）⇒ 承接方与里程碑**未变**；⚠️ 但**C4 的节点边界已在本 feature 闭合** ⇒ 门禁 3 的缺口**只剩 C8** |
| 登记项 **R-2** | **新增**（下游承接 **D-1** 的跨 feature 文档改动）⇒ 处置 = **只接线**（B8F1 提示词初稿 + README）⇒ MUST NOT 越界实现条件边求值 |
| 登记项 **R-3** | **新增**（Phase 0 实测发现 FR-014 与上游分叉）⇒ **已回写 spec**（FR-014 / SC-012 / 裁定 10）⇒ 判据**只收紧不放宽** |
| 登记项 **R-4** | **新增**（裁定 26 / 27 由**分析轮**拍板 ⇒ 跨 feature 接口**缺发起者背书**）⇒ 处置 = 标注来源 + **列入 T053 追认清单** ⇒ 判据**只收紧不放宽** |
| 登记项 **R-5** | **新增**（**H-2…H-5** 的上游原文**只指名 ID、未指名里程碑** ⇒ 严格按 v1.8.0 的**窄口径**触发条件**不构成宪法 MUST 冲突**；但原 plan 的「已写入」陈述**不成立**）⇒ 处置 = **事实性陈述订正** + **口径一致性补齐**（追补写入目标 feature 的提示词初稿与 README）· 落 `tasks.md` **T062** ⇒ **MUST NOT** 改宪法正文 |
| 与上游的等价性 | `contracts/upstream-parity.md` 给出 **13 条**语义点（**P-01…P-13**）+ **6 条**实测基线（核实环境 `langgraph 1.2.11`）⇒ 满足 spec FR-029 / SC-019 |
| 事实性表述 | Phase 0 的实测发现 **1 处** spec 表述需更正（research **C-1**）⇒ **已回写 spec**（**只更正事实**，未改任何判据）⇒ SC-001…SC-025 **全部仍成立** |
| 规模口径的可判定性 | 执行次数 / 调用次数 / 逐元素相等 / 集合相等 / 逐字相等 ⇒ 全部**可自动判定**（`superstep-contract.md` §7 的 **I-1…I-15**） |
| 遗留登记 | **DR-1**（`versions_seen` 消费时点与失败后不回滚）· **DR-2**（同轮顺序 = 声明顺序 vs 上游名字序）· **DR-3**（上游 `consume()` / `finish()` 钩子未实现）—— 全部**只登记 · 不改判据** |
| **裁定 31 的口径闭合**（2026-11-11 分析轮第 2 次 · 发起者批准） | **新增** ⇒ ① **初始化写入豁免**（跑**之前**调用方直接写通道对象 = 「写入只由调度层发起」的**唯一**豁免）② 「**第一次查看某通道**」的操作点 = **触发判定阶段枚举订阅通道时** ⇒ **只收紧判据**（把两条原本并存的 MUST 缝成一条自洽口径）⇒ **FR / SC 的编号与总数零变动**（FR 34 · SC 25）· 落 `spec.md` 裁定 31 + 引文差异 ⑧ + `tasks.md` **T063** |
| **2026-11-11 分析轮第 3 次（三件套一致性核验 · 发起者裁决）** | **0 条 CRITICAL** · FR 34/34 · SC 25/25 · 宪法**无 MUST 冲突** ⇒ **新增裁定 32–35**（**只补口径 · 不新增 FR / SC**）：**32**（图规格校验 = **构造时** + V-1 收敛为 `ValueError`）· **33**（**两个入口都执行**步末清空）· **34**（多轮入口的**跨轮累计语义补判据** + 未订阅通道版本基值 **0** + `SchedulerState.step` 递增点）· **35**（重复档案的**唯一权威落点**）⇒ 落 `spec.md` 裁定 32–35 + `contracts/superstep-contract.md` §2.1.1 / §5.2 / §5.3 / §6 + `data-model.md` §2 / §3.2 / §4.1 / §6 + `tasks.md` **T064** · **FR / SC 编号与总数零变动**（FR 34 · SC 25）· **任务 62 → 63** ⇒ 判据**只收紧、不放宽** |
| **2026-11-11 分析轮第 6 次（三件套一致性核验 · **订正轮** · 发起者授权修复）** | **20 处漂移**（**0 条 CRITICAL** · 宪法**无 MUST 冲突** ⇒ 无需改宪法）⇒ **新增裁定 36**（**只改文档 · 不改需求 · 不改判据**）：**只收紧 / 等价**的 6 处 ⇒ 契约 §1（`GraphSpec` 签名改**语义表述** ·「缺省 = 空映射」+「MUST 用工厂语义」⇒ 照抄字面 `= {}` 会抛 `ValueError: mutable default`（**实测**）· 类型注解 `Mapping` → `dict` 以表达「保序 + 可变」）· 契约 §2.1 / §2.1.1（**V-8** 冻结为内置 `ValueError` ⇒ 与 SC-015 的「只用两种内置异常」一致）· 契约 §3.2（补「未被订阅通道的版本基值 = **0**」这条**已存在**的 MUST）· 契约 §5.4 / spec FR-032 ⚠️（补「快照**无值** ⇒ 只 `clear()`」的缺失分支）· spec SC-006（补「**多轮入口**专用」的入口限定）⇒ 另 14 处编号 / 措辞 / 落点漂移同步订正（plan **R-2 ② / ③** · tasks **T005 / T008 / T017 / T046 / T060 / T061**）⇒ **新增任务 T065**（FR-034 的可变映射断言）⇒ 落 `spec.md` 裁定 36 + `contracts/superstep-contract.md` §1 / §2.1 / §2.1.1 / §3.2 / §5.3 / §5.4 + `data-model.md` §2 / §5 / §6 + `tasks.md` **T065** ⇒ **FR / SC 编号与总数零变动**（FR 34 · SC 25）· **任务 63 → 64** ⇒ 判据**只收紧、不放宽** |

---

## Project Structure

### Documentation (this feature)

```text
specs/b7f1-superstep-loop/
├── plan.md                          # This file (/speckit.plan command output)
├── research.md                      # Phase 0 output —— D-01…D-12 上游实测取证 + DR-1…DR-3 遗留登记 + C-1…C-2 事实更正
├── data-model.md                    # Phase 1 output —— 调度实体模型 + 五阶段状态机 + 原子性边界 + 校验规则 + 不变量
├── quickstart.md                    # Phase 1 output —— 可照抄的验证手册（闸口 V1–V12）
├── spec.md                          # 规格（**澄清 Q1–Q25**（Q1–Q10 = 澄清轮 · Q11–Q13 = 分析轮 · Q14–Q19 = 2026-11-11 分析轮 · 发起者批准 · Q20–Q24 = 分析轮第 3 次 · 发起者裁决 · Q25 = 分析轮第 6 次 · 一致性订正）· **37 条裁定** · FR-001~FR-035 · SC-001~SC-026 · 追溯表 35 行）
├── checklists/
│   └── requirements.md              # 规格质量清单（16/16）
├── contracts/
│   ├── superstep-contract.md        # 调度契约（操作面 / 触发判定 / 五阶段 / 合并 / 不变量）—— **唯一权威**
│   └── upstream-parity.md           # 与上游 LangGraph 的逐条对照（**13 条**）+ 实测基线 + 保留通道名
└── tasks.md                         # Phase 2 output（/speckit.tasks —— 本命令不生成）
```

### Source Code (repository root)

```text
src/freegraph/
├── __init__.py                      # 既有 · **零改动**（顶层包惰性 · G1 / L-1）
├── graph.py                         # 既有 · **零改动**（门面 7 符号面 · G15 / G19）
├── _stategraph.py                   # 既有 · **零改动**
├── _primitives.py                   # 既有 · **零改动**
├── py.typed                         # 既有 · **零改动**（PEP 561）
├── contracts/                       # L1 契约层 · **零改动**（18 符号面 · G7 / G8）
│   └── ...                          #   —— 本 feature 复用 InvalidUpdateError / GraphRecursionError（**不新增**）
└── runtime/                         # L2 执行内核层（层注册表**已登记为目录条目** · **零改动**）
    ├── __init__.py                  # ★ 追加导出（14 → 20 个符号 · **L2 内部 API**，非公开门面）
    ├── errors.py                    # 既有（B5F1）· **零改动** —— 复用 EmptyChannelError / InvalidChannelUpdateError
    ├── schema.py                    # 既有（B4F1）· **零改动** —— ChannelSpec / SchemaSpec
    ├── reducer.py                   # 既有（B4F1）· **零改动**
    ├── channel.py                   # 既有（B5F1）· **零改动** —— Channel / LastValue / BinaryOperatorAggregate / EphemeralValue
    ├── mapping.py                   # 既有（B5F1）· **零改动** —— build_channel / build_channels
    ├── read.py                      # 既有（B5F2）· **零改动** —— read_channels / local_read（本 feature 的入参来源）
    └── superstep.py                 # ★ 调度内核（GraphSpec / NodeSpec / SchedulerState / SuperStepResult /
                                     #     run_super_step / run_super_steps）
                                     #   —— 只依赖标准库（collections.abc · dataclasses · typing）· 零第三方

tests/
├── conftest.py                      # 既有 · **零改动**
├── contracts/                       # 既有（G1–G13）· **零改动**
│   └── test_contract_regressions.py # ★ **零改动**（仅**核对**：两条 `GATE-MOUNT:` 行逐字未动 · FR-018 · SC-011）
├── facade/                          # 既有（G14–G20）· **零改动**
├── gates/                           # 既有（G21–G30）· **零改动**
└── runtime/                         # 本 feature 的测试（与既有 `tests/runtime/` **同目录**）
    ├── __init__.py                  # 既有（B4F1）· **零改动**
    ├── conftest.py                  # 既有（B4F1）· **零改动** —— **复用** `run_in_subprocess` 夹具
    ├── test_read_c4_sparse_state.py # ★ **改**：**追加**「真实节点收到的入参」断言（承接 H-1 · FR-016）
    │                                #   —— **保留**原读取层口径断言（FR-017）· 挂载点文件**零改动**（FR-018）
    ├── test_read_contract.py        # ★ **改**：导出面 **14 → 20**（**6 处**「14」表述 · FR-023）
    ├── test_superstep_basic.py      # ★ 单 super-step 跑通（A1 · SC-001）
    ├── test_superstep_merge.py      # ★ 写入合并（批量归约 + 覆盖型冲突 + 未知 key · SC-002 / SC-007 / SC-023）
    ├── test_superstep_trigger.py    # ★ 触发判定与版本号（SC-003 / SC-004）
    ├── test_superstep_convergence.py# ★ 收敛与步数上限（SC-006）
    ├── test_superstep_atomicity.py  # ★ 一轮 super-step 的原子性（SC-024）
    ├── test_superstep_clearing.py   # ★ 步末清空范围（SC-012）
    ├── test_superstep_determinism.py# ★ 确定性 + 同一规格可跑两次（SC-013）
    ├── test_superstep_purity.py     # ★ 纯净性（零上游导入 / 零环境变量 / 零出站 / 无构建器依赖 · SC-005 / SC-014 / SC-018）
    └── test_superstep_contract.py   # ★ **契约守卫**（解析 contracts/superstep-contract.md 的 I-1…I-15 · FR-027 · SC-017）

harness/verification/B7F1/
├── acceptance.py              # ★ **一键验收入口**（裁定 37 · FR-035 / SC-026 · tasks T066）
└── manual-verification.md     # ★ 人工验证记录（五段式 + 来源覆盖表 + **发起者追认** · R-1 / R-2）

harness/features/B8F1_条件边路由与fresh读.md
                                      # ★ **下游承接 D-1 的接线**（只接线 · 逐条最小改动 · R-2）
harness/features/README.md           # ★ 同步 B8F1 行（补「条件边字段已预留」· R-2）

# ── 本 feature **改到**的既有文件（**五处** · 登记项 R-1 / R-2 / R-3 / R-4 / R-5） ──
specs/b7f1-superstep-loop/spec.md    # ★ R-3 / R-4 · FR-014 / SC-012 / 裁定 10 的**事实性订正** + 裁定 28 / 29 / 30
tests/runtime/test_read_c4_sparse_state.py
                                      # ★ H-1 · C4 的**节点边界**断言（追加 · 不删）
tests/runtime/test_read_contract.py  # ★ FR-023 · 导出面 **14 → 20**（**6 处**同步 · 见 FR-023）
harness/features/B8F1_条件边路由与fresh读.md + harness/features/README.md
                                      # ★ R-2 · 下游承接 D-1 的接线（只接线）
harness/features/B7F1_任务准备与super-step循环.md
                                      # ★ R-5 · 上游承接 H-2…H-5 的**追补接线**（只接线 · 逐条最小改动）

# ── ⚠️ **已改（未提交）· 2026-11-11 分析轮 R-5 ③ 的接线已落地**（裁定 35 · 2026-11-11 分析轮第 3 次）──
#   harness/features/B7F1_任务准备与super-step循环.md  ← 已追补 H-2…H-5（git diff 可见 · 未提交）
#   harness/features/README.md                        ← 已补 B7F1 行的「承接 B5F1 / 承接 B5F2」
#   ⇒ 上两条在本清单中仍登记为「本 feature 改到的既有文件」：T062 是**核对**任务（核对措辞未走样），
#     T050 仍**未完成**（B8F1 的 D-1 条款尚未写入该文件 · README 的 B8F1 行仍只提 B5F2 侧）
```

**Structure Decision**:

- **落 `src/freegraph/runtime/superstep.py`** —— 层注册表**已登记** `src/freegraph/runtime/` 为 **L2**
  ⇒ **层注册表零改动**（spec FR-020）；本 feature 是该目录的**第四个**实现 feature
  （B4F1 解析层 · B5F1 通道层 · B5F2 读取层 · **B7F1 调度层**）。
  ⚠️ **MUST NOT** 为 `runtime/` 下的新模块**单独立**注册表条目 ⇒ 会造成 L2 → L2 的横向依赖误判
  （层注册表 §0.2 规则 2 · G25 实现 `gate_G25_import_graph.py:59-60` 只在**不同注册表条目**间判层边）。
- **调度层与通道层 / 读取层**（`channel.py` / `mapping.py` / `read.py`）**物理分离** —— 理由：
  ① B5F1 的 `Channel` 抽象与 B5F2 的两个读取入口都是**冻结面**（逐字冻结）⇒ 调度层 MUST NOT 改它们
  ⇒ 分离 ⇒ 冻结面零变更（FR-024）；② 调度层**只依赖**通道的**四个操作 + 一个判定**
  与读取层的**一个入口** ⇒ 依赖方向单一（L2 内 `superstep` → `read` → `channel`）⇒ **无环**；
  ③ 「调度内核**不经由图执行器 / 构建器**直接测试」（FR-012 / FR-027）⇒ 调度层必须能**独立 import
  与测试** ⇒ 分离更易。
  ⚠️ `src/freegraph/runtime/__init__.py` **MUST NOT** 被 `src/freegraph/__init__.py` import
  ⇒ 顶层包惰性（G1 / L-1）**恒成立**。
- **节点入参走 B5F2 的稀疏读**（不另写一份）—— 理由：C4 的契约边界是**节点入参**，
  而「稀疏读」只有一处实现（B5F2 FR-038 · 两个入口逐字相等）⇒ 调度层**复用**它
  ⇒ 「稀疏语义」**不可能**在调度层漂移 ⇒ FR-008 / SC-009 可判定（契约 **I-1 / I-2**）。
- **版本记在调度状态、NOT 记在通道** —— 理由：B5F1 的 `Channel` 只有**四个只读属性**
  （`key` / `value_type` / `value` / `reducer`）⇒ 加版本位 = 改**冻结面** ⇒ 不可行；
  ⇒ 版本归 `SchedulerState`（裁定 21 · research **C-2**）⇒ 通道层**零改动**。
- **测试落在 `tests/runtime/`** —— 理由：门禁 **G2** 的内部 import 档扫描 `tests/contracts/**`
  ⇒ 那里**禁止** import `freegraph.*` ⇒ 调度内核的用例**必须**住 `tests/runtime/`
  ⇒ **G2 恒绿**（沿用 B5F2 裁定 20 的同款口径）。
- **两份契约**（`superstep-contract.md` / `upstream-parity.md`）—— 沿用 **B3F1 的层注册表先例** +
  **B5F1 / B5F2 的契约先例**（机器可读 Markdown + `<!-- authority: yes -->` 标记）：
  ① `superstep-contract.md` 是**判据**（**唯一权威**）；
  ② `upstream-parity.md` 是**证据表**（逐条 `路径:行号` + 实测基线）⇒ **MUST NOT** 被测试解析
  （测试**直接断言行为** ⇒ 避免「判据与实现同源 ⇒ 自证」）。

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **宪法「质量门禁 3 / 4 / 5」的三部分在本 feature 物理不可达成**（`target.py` 原样可跑 · fake 模型轮 · 真实模型轮） | 三者**共享同一根因**：它们都要求**完整内核运行时**（编译 + 执行）存在，而 B7F1 按立项书 §5.2 只交付**调度内核**（`StateGraph` = B6F1 · `compile` = B7F2 · `invoke` = B7F3 · 条件边 = B8F1）⇒ **任何 spec 设计都无法在本 feature 满足这三条** ⇒ 依宪法 **v1.6.0** 的窄口径通则处置（偏离登记 + 发起者追认 + 具名承接方） | **替代方案 A：硬写进 CI**（让验收脚本在「无图可跑」时判通过而不登记）⇒ **静默稀释宪法** + 门禁语义被扭曲 ⇒ **不可行**。<br>**替代方案 B：写一条永久红的 CI** ⇒ 违反「feature 必须能独立通过门禁」· PR-4 ⇒ **不可行**。<br>**替代方案 C：改宪法正文** ⇒ 违反「**MUST NOT** 以本条删改宪法正文」⇒ **不可行**。<br>**替代方案 D：把 B7F1 扩成「调度 + 构建器 + invoke」** ⇒ 越过立项书的 feature 边界 ⇒ **不可行**。<br>**采用的处置**：**偏离登记（R-1）+ 发起者追认（`tasks.md` 的阻断合入任务）+ 承接条款已在目标 feature 的提示词初稿中既有**（B6F1 / B7F2 / B7F3 / B8F1 / B22F1 / B23F1 / B25F1）⇒ **红线判据一律不放宽**。 |
| **同轮执行顺序 = 声明顺序**（上游 = **节点名字典序**） | 发起者于 2026-11-10 澄清轮**主动选定**「我先声明的先跑」⇒ 贴近写图的人的直觉；且节点表**保序**即可 ⇒ **零额外成本** | **替代方案 A：照抄上游的名字序** ⇒ 用户会困惑「为什么 `agent` 排在 `cleanup` 后面」⇒ 与直觉冲突 ⇒ **发起者已否**。<br>**替代方案 B：拓扑序** ⇒ 有环的图（**循环是本 feature 的常态**）上无全序 ⇒ 需额外兜底规则 ⇒ 复杂度不划算。<br>**采用的处置**：**声明顺序** + 在 `upstream-parity.md` **P-05** 登记为**可观察差异**（非交换归约器的合并顺序两侧不同）⇒ **DR-2**（不改判据）。 |
| **一轮 super-step 采用「完全原子」**（本轮出错 ⇒ 所有写入都不合并） | 「一轮要么全成、要么全不成」是最好推理的性质 ⇒ 出错后用户看到的状态**自圆其说**，不会撞上「写了一半」的中间态；且它是 B5F1「归约器抛错 ⇒ **该通道**值不变」的**超集** | **替代方案 A：逐通道应用**（已合并的保留）⇒ 留下半成品状态，最难排查；且与上游**不完全一致**。<br>**替代方案 B：分两种错误处理**（执行阶段全不生效 / 合并阶段已合并的保留）⇒ 语义更绕、要区分两类错误。<br>**替代方案 C：版本一并回滚**（在调度状态上做事务性回滚）⇒ 异常已向上传播、运行终止 ⇒ 调度记录**无人在意** ⇒ 收益为零、复杂度显著上升（2026-11-11 分析轮核验）。<br>**采用的处置**：**完全原子**（裁定 22 · FR-032 / SC-024）+ **回滚机制**（合并前**快照** → 出错**逐通道回滚**：`clear()` + `update([快照值])` · **不套归约器** ⇒ 逐字还原 · **不改动** B5F1 的冻结面）+ **版本延后推进**（**全部合并成功后**才 +1 ⇒ 出错则**一个都不推进** ⇒ 值与版本**同进同退**、无幽灵触发）（**裁定 29**）⇒ 回滚面**极窄**（四类错误中**只有「归约器抛错」**需要真正回滚）⇒ ⚠️ 在**错误路径**上与上游**不完全一致**（上游在合并阶段的归约器出错时已合并的通道会保留）⇒ 登记为**机制差异**（不影响正常路径的可观察语义）。 |
| **未知 key ⇒ 显式失败**（上游 **warning + 静默忽略**） | C6 逐字要求「未知 key 报错」；静默丢弃用户的拼写错误是**无声失败** ⇒ 与 B5F1「非法输入 MUST 显式失败」的既有立场一致 | **替代方案 A：照抄上游的静默忽略** ⇒ 用户的拼写错误**无声消失** ⇒ 违反 C6 ⇒ **不可行**。<br>**替代方案 B：新增一个 L2 错误类型** ⇒ 破 L1 的冻结面（G7）⇒ **不可行**。<br>**采用的处置**：复用 **L1 已冻结的 `InvalidUpdateError`**（`invalid_keys` 列全部）⇒ **零新增错误类型** + 登记为 parity **P-07**（沿用 B5F2 的 **DR-2** 登记）。 |
| **「已消费版本」在 plan 阶段消费、且出错时**不**回滚** | 上游在 **apply 阶段**更新（research **D-02**）；但本 feature 的 FR-032 要求「一轮出错 ⇒ 全部写入不合并」⇒ 若已消费版本**回滚**、而通道值也回滚，二者一致；若只回滚其一 ⇒ 状态与调度记录**不一致** ⇒ 本 feature 选择「plan 阶段消费 + 不回滚」⇒ 因为异常已**向上传播**、**运行终止** ⇒ 调度记录**无人在意**（⚠️ **2026-11-10 分析轮**：research **D-02** 的决策句原写「出错时随本轮一并作废」⇒ **已订正**为「**不回滚**」⇒ 与本行 / data-model §4.2 / research **DR-1** 三处一致） | **替代方案 A：改在 apply 阶段消费**（与上游逐字同构）⇒ 但 apply 阶段可能因出错**根本不到达** ⇒ 已准备的任务的版本**永久未消费** ⇒ 下一轮会**重复触发**同一节点 ⇒ 与「同一版本不重复触发」冲突。<br>**替代方案 B：出错时回滚已消费版本** ⇒ 需要为调度状态实现**事务性回滚** ⇒ 复杂度显著上升，而**收益为零**（运行已终止）。<br>**采用的处置**：plan 阶段消费 + 不回滚 ⇒ 登记为 **DR-1**（已知边界 · 不改判据）。 |
| **图规格预留「条件边」字段**（本轮恒空 · 非空即失败） | B5F2 的差分夹具已用**同款手法**预留条件边字段（裁定 15）⇒ 仓库的**既有范式**；预留 ⇒ B8F1 **只需填值**即可复用 ⇒ 避免仓库出现**第三套**图规格形态 | **替代方案 A：不预留** ⇒ B8F1 要回头改 B7F1 的调度内核 ⇒ 破坏已冻结的接口；且要**第三套**形态。<br>**替代方案 B：把「边」设计成将来可带条件** ⇒ 本轮**没有任何东西可填** ⇒ 留不下「恒空即失败」的可判定判据。<br>**采用的处置**：**预留 + 恒空 + 非空即显式失败**（裁定 25 · FR-033 / SC-025）⇒ 按宪法 **v1.8.0** 落成**下游承接 D-1**（**只接线** · 登记项 **R-2**）⇒ **零越界**。 |
| **上游的 `consume()` / `finish()` 两个通道钩子未实现** | B5F1 冻结的 `Channel` 只有**四个操作**（`update` / `get` / `is_available` / `clear`）⇒ 加钩子 = 改**冻结面** ⇒ 不可行；且「运行结束时的 `finish()`」语义属 checkpoint / 收官（B7F3 / B14F1） | **替代方案 A：给 `Channel` 加 `consume()` / `finish()`**（上游同款）⇒ 改**冻结面** ⇒ 连带改 B5F1 的契约文件与 parity 表 ⇒ 代价远超收益。<br>**替代方案 B：在调度层用私有属性模拟**（如给通道塞一个 `finished` 标记）⇒ 绕过抽象写私有状态 ⇒ 违反 B5F1 的抽象纪律。<br>**采用的处置**：freegraph 的等价落点 = **步末对「本轮未被写入的路由型通道」调 `clear()`**（research **D-05**）⇒ 「最后一轮 `finish()`」**不实现** ⇒ 登记 parity **P-13** + **DR-3**（归 B7F3 / B14F1）。 |
| **FR-014 在 plan 阶段被上游实测收紧**（裁定 10 由 B → C） | 上游**只清「本步未更新」的通道**（research **D-05**）⇒ **本步写过的路由型通道的值存活到下一轮** ⇒ B8F1 的条件边路由 MUST 能读到「**本节点本次写入**」⇒ 原口径会**破坏 C8** | **替代方案 A：保留原口径 B**（步末清全部路由型）⇒ 路由通道的值**在本轮内消失** ⇒ B8F1 读不到 ⇒ **破坏 C8** ⇒ **不可行**。<br>**替代方案 B：直接照抄上游的 `update(EMPTY_SEQ)`** ⇒ 需要给通道加**空序列清空**语义 ⇒ 改 B5F1 的**冻结面** ⇒ **不可行**。<br>**采用的处置**：**裁定 10 收紧为 C**（只清「本轮未被写入的」路由型）⇒ **已回写 spec**（FR-014 / SC-012 · research **C-1**）⇒ **判据只收紧、不放宽**（登记项 **R-3**）。 |
