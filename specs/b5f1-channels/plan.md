# Implementation Plan: B5F1 · Channel 抽象 + `LastValue` + `BinaryOperatorAggregate` + `EphemeralValue`

**Branch**: `b5f1-channels` | **Date**: 2026-11-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b5f1-channels/spec.md`

**feature ID**: `B5F1`（**M1 运行时内核**的第 6 个 feature · 前置 **B4F1** · 后续解锁 **B5F2**）

---

## Summary

交付 freegraph 的**通道抽象**与三类通道实现，把「**覆盖 vs 归约 vs 清空**」这条状态语义
收敛到**一个**实现点（spec §1 的核心价值）：

| 通道 | 语义 | 关键规则 |
|---|---|---|
| `LastValue` | **无归约器 ⇒ 覆盖**（C3） | 一次写入调用收到多于一个值 ⇒ **显式失败** |
| `BinaryOperatorAggregate` | **有归约器 ⇒ `reducer(current, new)`**（C2） | 空值按**类型**推导；首次写入分「有值 / 无值」两分支 |
| `EphemeralValue` | **路由通道 · 每 super-step 清空**（C7 / C8） | 显式 `clear()` ⇒ 回到「无值」；一步内多值 ⇒ **显式失败** |

外加：**统一抽象**（`Channel`）· **schema → 通道的映射入口**（`build_channel` / `build_channels`）·
**两个 L2 错误类型**（`EmptyChannelError` / `InvalidChannelUpdateError`）· **独立验收脚本**。

技术方案（全部**标准库**，零第三方依赖）：

| 环节 | 手段 | 依据 |
|---|---|---|
| 抽象形态 | `abc.ABC` + `@abstractmethod`（`clear()` 给默认无操作实现） | research **D-01** · spec FR-001 / FR-002 |
| 属性只读 | `__slots__`（私有槽）+ 4 个只读 `property` | research **D-02** · spec FR-002 / FR-013 |
| 「无值」表示 | 模块私有 sentinel `_MISSING = object()`（**MUST NOT** 用 `None`） | research **D-03** · spec FR-011 ③ |
| 空值推导 | 剥 `Annotated`/`Required`/`NotRequired` → 抽象容器映射 → `typ()`（失败 ⇒ 初始「无值」） | research **D-05** / **D-06** / **D-07** · spec FR-006 |
| 首次写入 | 有值 ⇒ `reducer(current, new)`；无值 ⇒ **直存**（不调归约器） | research **D-08** · spec FR-007 · 裁定 4 |
| 冲突检测 | 写入**之前**统一检测（`len(values) > 1` ⇒ 抛错，值不变） | research **D-09** · spec FR-004 / FR-010 |
| 映射规则 | 有归约器 ⇒ BinOp；无 ⇒ LastValue；路由 ⇒ Ephemeral（显式创建） | spec FR-012 · 裁定 8 |
| 错误类型 | L2 手写 `__init__` + 结构化字段（`key` / `received_count` / `expected_count`）+ 英文摘要 | research **D-10** · spec FR-017 |
| 规模口径探针 | `len(gc.get_referents(channel))`（**不**计时、**不**数行） | research **D-12** · spec FR-013 ①② · SC-022 |

**零新增依赖、零新增公开 API、零新增门禁编号**：契约层 18 符号面与门面 7 符号面**一字不动**
（G7 / G15 / G19 恒成立）；`freegraph.runtime` 的导出从 **4 → 12** 个符号（**L2 内部 API**，
不进兼容矩阵 · 沿用 B4F1 裁定 6 ③）；`langgraph` **不写进任何依赖声明、CI 也不装**。

**四处「与上游机制不同、但语义等价」的登记**（详见 [research.md](./research.md) §3 与
[contracts/upstream-parity.md](./contracts/upstream-parity.md)）：

1. **清空机制**：freegraph = 显式 `clear()`；上游 = 对本步未更新的通道调 `update(空序列)`
   （`pregel/_algo.py:326-334`）⇒ **可观察语义等价**（spec 裁定 6）。
2. **剥离口径**：freegraph = 窄口径（只剥 `Annotated`/`Required`/`NotRequired`）；
   上游 = 无差别剥 `__origin__`（`binop.py:22-28`）⇒ **空值结果完全等价**（research D-05）。
3. **抽象容器映射**：freegraph 与上游**同 6 项**（`binop.py:83-88`）⇒ 无差异。
4. **冲突异常的落地**：`LastValue` / `EphemeralValue` 在**通道层**抛（上游亦然），
   异常类型是 freegraph 自有的 `InvalidChannelUpdateError`（上游用 `InvalidUpdateError`）。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`pyproject.toml` 的 `requires-python = ">=3.11"`）；
**typing 构件上限 = 3.11**（宪法「运行时环境基线」）—— 本 feature 用到的 typing 构件**全部 ≤ 3.11**：
`typing.Any` · `collections.abc.Callable` / `Sequence` / `Mapping` · `abc.ABC` / `abstractmethod` ·
`typing.Protocol`（**仅**用于类型标注）· `gc.get_referents`（标准库 · 非 typing）。
**MUST NOT** 使用 `TypeAliasType`(3.12) / `override`(3.12) / `ReadOnly`(3.13) / `TypeIs`(3.13)
或 PEP 695 `type` 语句。**主判定 = CI 矩阵最低档 3.11 跑全量测试**（含 `tests/runtime/`）。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []` · 沿用现状）。
**开发期**：`pytest`（既有 `[dependency-groups] dev`）—— **零新增**。
**本 feature MUST NOT 把 `langgraph` 写进任何依赖声明**（沿用 B4F1 澄清 Q5 的口径）
⇒ 与上游的对照由 `contracts/upstream-parity.md` 的**逐条 `路径:行号`** 承载（spec FR-021）。
⚠️ **覆盖率工具也不进依赖**（research D-13）⇒ 开发期临时安装、实测输出记入人工验证记录。

**Storage**: N/A —— 本 feature 无运行时持久化（checkpoint 属 **B14F1**）。
**仓库内的权威工件** = **纯文本 Markdown 契约**
（`contracts/channel-contract.md` = 通道契约的唯一权威 · `contracts/upstream-parity.md` = 上游对照表）。

**Testing**: pytest + 标准库 `abc` / `collections.abc` / `gc` / `typing` / `operator`。
**需要子进程的断言**（SC-005 的「导入后 `sys.modules` 增量中非标准库条目数 == 0」·
「环境变量读取次数 == 0」·「出站连接次数 == 0」）**必须在子进程中执行**
⇒ **复用 B4F1 已有的 `tests/runtime/conftest.py` 夹具 `run_in_subprocess`**（session 级；
回传 `env_reads` / `egress` 两个计数器）⇒ **既有 conftest 零改动**。

**Target Platform**: 任意 CPython 3.11+ 平台（Linux / macOS / Windows）。
CI 的 `testpaths = ["tests"]` ⇒ 新增 `tests/runtime/test_channel_*.py` **自动被收集**，**CI 配置零改动**。

**Project Type**: library（Python 库；发行名 = 导入名 = `freegraph`；D1 决议：不拆独立发行包）。

**Performance Goals**: **N/A（不设时间预算）** —— 通道操作是**纯内存**、**常数级**、无 I/O / 无网络 / 无锁。
**规模口径**用**结构探针**表达（research **D-12** · **D-17**）：① **主判据 = 引用类型白名单**
（`gc.get_referents(channel)` 中 MUST NOT 出现 `dict` / `SchemaSpec` / 其它 `Channel` 实例
⇒ 结构上不可能遍历全体 key）；② **辅助判据 = 计数探针**：`len(gc.get_referents(channel))`
在 schema 有 1 个 key 与有 1000 个 key 时 MUST **相等** ⇒ 「单通道操作不随 key 数增长」
（spec FR-013 ②③ / SC-022 ①③ · 裁定 17 ③）。
⚠️ **MUST NOT** 用墙钟耗时做断言（CI 假红 · spec FR-013 ③）。
⚠️ 计数相等**不能替代**白名单（实测：持有整张状态表时计数在 N=1 与 N=1000 时**同为 6**）。

**Constraints**（**主要**来自 spec 的 MUST 条目；未逐条列出的 FR 见 `tasks.md` 的追溯表）：

| 约束 | spec 条目 |
|---|---|
| 只依赖**标准库**；MUST NOT import `langchain*` / `langgraph*` / `langsmith` / `pydantic` / `typing_extensions` | FR-015 · SC-005 |
| MUST NOT 读取**任何**环境变量；零出站；零文件 I/O；导入**无副作用** | FR-015 · SC-005 |
| 通道**只持** {key, 值类型, 当前值, 归约器引用}；MUST NOT 持节点 / 图 / 配置 / 时钟 / 句柄 / 锁；**子类 MUST NOT 引入新槽**（⇒ 实例 MUST 无 `__dict__`） | FR-013 ① · SC-009 |
| 通道 **MUST NOT** 持有其它通道 / 状态表的引用（⇒ 结构上不可能遍历全体 key） | FR-013 ②③ · SC-022 |
| 写入 **MUST 只**由调度层发起；**不承诺**线程安全；MUST NOT 引入同步原语 | FR-023 · SC-024 |
| 通道**浅引用**用户对象（不复制 / 不转换 / 不校验类型） | FR-024 · SC-025 |
| 构造期**当场失败**（内置 `TypeError` / `ValueError`）；MUST NOT 重做二元性校验 | FR-025 · SC-026 |
| 覆盖型 / 路由型：一步内多值 ⇒ **显式失败**；归约型：逐个归约 | FR-004 / FR-010 / FR-005 |
| 归约型：首次写入的 `current` 分「有值 ⇒ 归约 / 无值 ⇒ 直存」两分支 | FR-007 · 裁定 4 |
| 清空后的状态**一律**「无值」（清空 ≠ 回到初始状态） | FR-022 ③ · SC-023 |
| 「有值 / 无值」判定**完全可判定**；「值为 `None`」≠「无值」 | FR-011 · SC-004 |
| 错误类型落 **L2**；捕获走基类 `FreegraphError`；结构化字段逐字冻结；MUST NOT 携带用户值 | FR-017 · SC-018 |
| 名字面逐字冻结（4 操作 + 4 属性 + 4 类名 + 2 映射入口 + 2 错误名） | FR-002 / FR-012 · SC-019 |
| L2 MUST 只向下依赖 L1；MUST NOT import L3/L4/L5；**层注册表零改动** | FR-016 · SC-011 |
| 零新增公开 API（契约层 **18** 个 / 门面 **7** 个）；兼容矩阵**零新增行** | FR-018 · SC-012 |
| 新建源文件 MUST 带**署名头**且 docstring 为首个语句 | FR-019 · SC-011 |
| 人工验证记录（五段式 + 来源覆盖表）落 `harness/verification/B5F1/` | FR-020 · SC-013 |
| 独立验收脚本 `acceptance.py`（零依赖 · 一条命令跑完 · `--record` 五段式） | FR-026 · SC-027 |
| **覆盖率判据只管本 feature 新增/修改的代码**（`channel.py`/`mapping.py` 全文 + `errors.py`/`__init__.py` 新增部分）行/分支 == 100%；**整包**覆盖率**记录但不阻断**（B4F1 无基线） | FR-019 ② · SC-015 · 澄清轮 Q14 |
| **参数化组合测试**（归约器类型 × 通道类型 · 组合数 ≥ 12 · **不得** skip/xfail 掩盖） | FR-027 · SC-028 · 立项书 S5 ③ |

**Scale/Scope**: schema 的 **key 数**：典型 **2–20**（`target.py` = 2 个；用户 schema 常见 3–10 个）。
**实现 ≈ 520 行 / 测试 ≈ 540 行**（立项书 §5.2 的估算，作为 plan 的输入）。
本 feature **零新增公开 API** ⇒ 兼容矩阵**零新增行**。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 通过项（逐条）

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith 依赖 · 自身零出站 · 零环境变量） | FR-015 · 既有 **G24**（配置层扫描 `src/freegraph/**`）· **G26**（网络静态扫描）· **G27**（零出站动态） | ✅ |
| 原则 II（内核纯净 · 状态语义 MUST 与 LangGraph 等价） | FR-015（零依赖）· **G21 / G22**（依赖黑名单 + 隔离环境 `sys.modules`）· FR-021 + `contracts/upstream-parity.md`（**逐条 `路径:行号`** 承载 C2 / C3 的等价性） | ✅ |
| 原则 III（验收契约优先 · `target.py` 只读） | 本 feature **零改动** `target.py`；其 schema（`messages: Annotated[list[AnyMessage], operator.add]` · `llm_calls: int`）**必须能映射到通道** ⇒ SC-008 的映射正确率 | ✅ |
| 原则 IV（可诊断性） | N/A（本 feature **无运行期可观测面**；诊断靠 FR-017 的结构化错误字段） | ✅ 边界内 |
| 原则 V（人工验收是最终验收标准） | FR-020（`harness/verification/B5F1/manual-verification.md` · 五段式 + 来源覆盖表）· FR-026（独立验收脚本 `acceptance.py`） | ⚠️ **门禁 5 的「真实模型一轮」不适用** ⇒ 见**登记项 R-1** |
| 原则 VI（规格驱动 · tasks 可逐条勾选） | 本 plan + `tasks.md`（含 FR ↔ SC 追溯表） | ✅ |
| 原则 VII（职责边界 · 契约 C1–C27） | FR-003 / FR-005 = **C2 / C3** 的**执行侧**落地；FR-011 = **C4** 的**前置**（有值 / 无值判定）；C7 / C8 的**路由侧**消费属 **B8F1** | ⚠️ **门禁 3 的 C4 / C8 两条独立回归**不在本 feature ⇒ 见**登记项 R-1** |
| 原则 VIII（证据与术语纪律） | `research.md` 每条决策附**实测命令 + 真实输出**；上游引用标 `路径:行号` + 核实版本 `langgraph 1.2.11`（`contracts/upstream-parity.md`） | ✅ |
| 原则 IX（许可证与商标红线 · NON-NEGOTIABLE） | **零新增依赖**（FR-015）⇒ `THIRD_PARTY_NOTICES` 无需变更；**零品牌资产**（不复制上游代码，只重写语义） | ✅ |
| 原则 X（文档合规 + 源文件署名头） | FR-019（署名头 · 既有 **G30** 全仓扫描自动覆盖新文件）· 兼容矩阵**零新增行**（须在人工记录中显式记「无新增」） | ✅ |
| 运行时环境基线（Python 3.11 · typing 上限 3.11） | 本 feature 只用 ≤ 3.11 构件（Technical Context 已逐项列出）· 最低档 3.11 跑全量测试 | ✅ |
| 依赖白名单 / 黑名单（包层 · 配置层 · 网络层） | 零新增依赖 ⇒ **G21 / G23 / G24 / G26 / G27** 恒绿 | ✅ |
| 质量门禁 1 / 2 / 6 / 7 | ① 规格 + tasks 可勾选 ② 依赖零新增 ⑥ 证据（research + 对照表 + 来源覆盖表）⑦ 文档合规（署名头 + 兼容矩阵零新增） | ✅ |
| 质量门禁 3 / 4 / 5 的**内核运行时相关部分** | ⚠️ **物理不可达成** ⇒ **登记项 R-1**（偏离登记 + 发起者追认） | ⚠️ **见 R-1** |
| 发布门禁（发行产物纯度） | 本 feature **不接入**（B24F1）· 新增代码在 `src/freegraph/` 内 ⇒ **不污染**产物纯度 | ✅ 边界内 |

### ⚠️ 登记项 R-1（宪法「质量门禁 3 / 4 / 5」的偏离登记 · 需发起者追认）

**依据**：宪法 **v1.7.0**「质量门禁的分阶段落地与发起者追认」（**窄口径**通则 · 首次适用 = B3F1 ·
B4F1 沿用同一处置）。**本 feature 与 B4F1 的 R-1 同根因、同承接方** ⇒ **沿用既有承接条款**，
MUST NOT 新造承接机制。

| # | 被偏离的**具体门禁项** | 不可达成的根因 | 判据未被放宽的论证 | 承接方（feature ID + 里程碑） | 承接机制 |
|---|---|---|---|---|---|
| ① | **门禁 3** 的「**C4**（稀疏状态）+ **C8**（条件边 fresh 状态）两条**独立回归测试**」 | 二者都要求**状态读取层**与**调度循环**存在：C4 的读取属 **B5F2**、C8 的 fresh 读属 **B8F1**、super-step 循环属 **B7F1** ⇒ 本 feature（M1 第 6 个）**按里程碑不交付其前置能力** | 本 feature 交付的是 C2 / C3 的**执行侧**（通道语义）+ C4 的**前置**（有值 / 无值判定）；C4 / C8 的**判据一字未改** | **B5F2**（C4 · M1）· **B8F1**（C8 · M2） | **挂载点已存在**（B3F1 落）⇒ 本 feature **零改动** `tests/contracts/test_contract_regressions.py:28-29`（`GATE-MOUNT: C4/C8 · status=not-landed · owner=B5F2/B8F1`）⚠️ 本 feature **MUST NOT** 改成 `landed` ⇒ 只需在本 feature 的**人工验证记录**中**再次登记 + 追认**（承接方与里程碑**未变**） |
| ② | **门禁 4** 的「**fake 模型跑通验收基线的一轮**」 | 验收基线跑通需要**完整内核运行时**（编译 + 执行）⇒ 属 **B7F2 / B7F3** ⇒ B5F1 **无图可跑** | CI **不写**一条永久红的断言（违宪 PR-4）；本 feature 只落**挂载点**并在人工记录中标记「未落地」 | **B7F2 + B7F3**（M1 / M2） | **已就位**：B3F1 的裁定 22 已把「fake 轮」的承接条款写入 B7F2 / B7F3 的提示词初稿 |
| ③ | **门禁 5** + 原则 V 的「人工验证记录含**真实模型一轮**」 | 无图可跑 ⇒ 无从接真实模型 | **五段式记录 + 来源覆盖表照常落地**（FR-020）+ **独立验收脚本照常落地**（FR-026）；被延后的只是「真实模型一轮」这一**部分** | **B7F3 / B25F1**（M2 / M4） | **已就位**：B25F1（双跑验收）的提示词初稿承接 fake 轮 |

**红线（未被触碰）**：依赖红线（`langsmith` / `langchain*` / `langgraph*`）· 许可证红线 · 商标红线 ·
零出站红线 —— **全部在本 feature 照常执行**（FR-015 + G21 / G23 / G24 / G26 / G27）。

**⇒ 请发起者在合入前追认此登记项**（落点：`tasks.md` 的一条**阻断合入**的追认任务 ·
追认文字 MUST 落在 `harness/verification/B5F1/manual-verification.md`）。

### 门禁编号纪律

**本 feature MUST NOT 新增门禁编号** —— 既有 **G1–G30** 的编号连续性是 B3F1 data-model 的不变量
（「门禁总数 == 30 · 编号连续」）⇒ 新模块由**既有门禁自动覆盖**：

| 既有门禁 | 对本 feature 的覆盖 |
|---|---|
| **G25**（导入图单向 · ARCH-1） | 新增的 `src/freegraph/runtime/channel.py` / `mapping.py` = **L2**（层注册表已登记）⇒ 自动纳入扫描；L2 → L3/L4/L5 的边数 == 0 即 SC-011 |
| **G30**（全仓署名头） | 新建源文件的署名头覆盖率 == 100%（SC-011）⇒ **无需**扩 G5 / G20 的硬编码清单 |
| **G4 / G24 / G26 / G27** | 零环境变量 / 零出站（FR-015） |
| **G21 / G22 / G23** | 零新增依赖 ⇒ 依赖闭包 / 隔离环境 / 许可证断言恒绿 |
| **G7 / G15 / G19**（公开面） | 契约层 **18** 个 / 门面 **7** 个符号**一字不动** ⇒ `freegraph.runtime` 的 4 → 12 个导出**不计入**公开面（L2 内部 API · B4F1 裁定 6 ③） |

**⇒ 门禁编号总数仍为 30**（layer-registry.md 与 data-model 的不变量**零改动**）。

> **📌 登记（research DR-5）**：`layer-registry.md:98` 仍写着 `src/freegraph/runtime/`「**尚未存在**」——
> 该措辞已被 B4F1 的实现**过时**（目录已创建），但**层归属（L2）本身正确** ⇒
> 本 feature **MUST NOT** 改层注册表（**冻结面**）⇒ **只登记、不修改**；
> 该措辞的刷新归 **B3F1** 的后续维护。

### 设计后复核（Phase 1 后 · 模板要求「Re-check after Phase 1 design」）

| 复核项 | 结论 |
|---|---|
| 宪法条款 | **无新增违反** —— Phase 1 产出的 4 份工件（`research.md` / `data-model.md` / `contracts/`×2 / `quickstart.md`）**全部**落在 L2 与 `specs/` 内 ⇒ 依赖 / 许可证 / 商标 / 零出站四条红线**不受影响** |
| 门禁编号 | **仍为 30**（G1–G30）—— Phase 1 **未新增**任何门禁脚本或编号；新增模块由 **G25**（导入图）与 **G30**（署名头）自动覆盖 |
| 公开面 | **零变更** —— `contracts/channel-contract.md` 冻结的 4 操作 / 4 属性 / 4 类名 / 2 映射入口 / 2 错误名全部属 **L2 内部 API**；契约层 **18** 个 / 门面 **7** 个符号**一字不动**（已实测：`len(c.__all__) == 18` · `len(g.__all__) == 7`） |
| 登记项 **R-1** | **仍然成立**（无图可跑 ⇒ 门禁 3 / 4 / 5 的四部分仍物理不可达成）⇒ 承接方与里程碑**未变**（B5F2 / B8F1 / B7F2 / B7F3 / B25F1） |
| 新增的**独立**登记 | **DR-1**（`__eq__` / `repr` 未冻结）· **DR-2**（类型可读文本）· **DR-3**（`Overwrite` 不做）· **DR-4**（清空机制差异）· **DR-5**（层注册表措辞过时）⇒ 全部**只登记、不改判据**，承接方见 research §2 |
| 与上游的等价性 | `contracts/upstream-parity.md` 逐条给出 **12 条语义点 + 5 条调度层侧 + 4 条不做**的 `路径:行号`（核实环境 `langgraph 1.2.11`）⇒ 满足 spec FR-021 |
| 规模口径的可判定性 | research **D-12** 的探针已**实测**（`gc.get_referents` ⇒ N=1/100/1000 恒为 4）⇒ SC-022 有可自动判定的载体 |

---

## Project Structure

### Documentation (this feature)

```text
specs/b5f1-channels/
├── plan.md                          # This file (/speckit.plan command output)
├── research.md                      # Phase 0 output —— D-01…D-17 决策 + 实测证据 + DR-1…DR-6 遗留登记
├── data-model.md                    # Phase 1 output —— 通道实体模型 + 状态机 + 不变量
├── quickstart.md                    # Phase 1 output —— 可照抄的验证手册（闸口 V1–V9）
├── spec.md                          # 规格（四轮澄清 · **17 条裁定** + **15 条澄清问答 Q1–Q15** · FR-001~FR-027 · SC-001~SC-028）
├── checklists/
│   └── requirements.md              # 规格质量清单（16/16）
├── contracts/
│   ├── channel-contract.md          # 通道契约（操作面 / 三类语义 / 状态机 / 错误 / 不变量）—— **唯一权威**
│   └── upstream-parity.md           # 与上游 LangGraph 的逐条语义对照（每条带 `路径:行号` + 核实版本）
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
│   └── ...
└── runtime/                         # L2 执行内核层（层注册表**已登记** · **零改动**）
    ├── __init__.py                  # ★ 追加导出（4 → 12 个符号 · **L2 内部 API**，非公开门面）
    ├── errors.py                    # ★ 追加 EmptyChannelError / InvalidChannelUpdateError
    ├── schema.py                    # 既有（B4F1）· **零改动** —— ChannelSpec / SchemaSpec
    ├── reducer.py                   # 既有（B4F1）· **零改动**
    ├── channel.py                   # ★ Channel（抽象）+ LastValue + BinaryOperatorAggregate
    │                                #   + EphemeralValue + 空值推导 + _MISSING sentinel
    └── mapping.py                   # ★ build_channel / build_channels（消费 B4F1 的 ChannelSpec / SchemaSpec）

tests/
├── conftest.py                      # 既有 · **零改动**
├── contracts/                       # 既有（G1–G13）· **零改动**（含 C4/C8 挂载点 · MUST NOT 改 status）
├── facade/                          # 既有（G14–G20）· **零改动**
├── gates/                           # 既有（G21–G30）· **零改动**
└── runtime/                         # 本 feature 的测试（与既有 `tests/runtime/` **同目录**）
    ├── __init__.py                  # 既有（B4F1）· **零改动**
    ├── conftest.py                  # 既有（B4F1）· **零改动** —— **复用** `run_in_subprocess` 夹具
    ├── test_schema_parse.py         # 既有（B4F1）· **零改动**
    ├── test_future_annotations.py   # 既有（B4F1）· **零改动**
    ├── test_binary_criterion.py     # 既有（B4F1）· **零改动**
    ├── test_parse_contract.py       # 既有（B4F1）· **零改动**
    ├── test_typed_dict_variants.py  # 既有（B4F1）· **零改动**
    ├── test_channel_semantics.py    # ★ 三类通道的语义（覆盖 / 归约 / 清空 · 初始状态 · 返回值口径）
    ├── test_channel_errors.py       # ★ 错误契约（结构化字段 · 继承 · 捕获路径）
    ├── test_channel_mapping.py      # ★ 映射入口（build_channel / build_channels · 保序 · 归约器身份）
    ├── test_channel_purity.py       # ★ 纯净性（属性集 · 规模探针 · 浅引用 · 构造期校验 · import 副作用）
    └── test_channel_contract.py     # ★ 契约守卫（**解析** contracts/channel-contract.md 逐条比对 · FR-021）
                                     #   —— 独立文件：与「纯净性」文件的 import 副作用断言物理隔离

harness/verification/B5F1/
├── acceptance.py                    # ★ 独立验收脚本（FR-026 · 零依赖 · 一条命令跑完 A1–A3 + 全部 SC）
└── manual-verification.md           # ★ 人工验证记录（FR-020 · 五段式 + 来源覆盖表）
```

**Structure Decision**:

- **落 `src/freegraph/runtime/`** —— 层注册表**已登记**该路径为 **L2**（B4F1 起创建）⇒
  **层注册表零改动**（spec FR-016）；本 feature 是该目录的**第二个**实现 feature。
- **模块切分（`channel` / `mapping` / `errors` / `__init__`）**：
  ① `channel.py` 承载**通道核心**（抽象 + 三类实现 + 空值推导 + `_MISSING`）——
     它**不 import** B4F1 的 `schema.py` ⇒ 通道层可**独立测试**、与解析层**零耦合**；
  ② `mapping.py` 单独承载**schema → 通道**的派生（`build_channel` / `build_channels`）——
     它是**唯一** import B4F1 `ChannelSpec` / `SchemaSpec` 的地方 ⇒
     **B6F1（`StateGraph` 构建器）只需 import 这一个模块**，不必碰通道实现细节；
  ③ `errors.py` **追加**两个错误类型（与 B4F1 的 `InvalidSchemaError` 同文件 ⇒
     异常族集中、docstring 可统一维护）；**既有 `InvalidSchemaError` 一字不动**；
  ④ `__init__.py` 只做导出（12 个符号：`Channel` / `LastValue` / `BinaryOperatorAggregate` /
     `EphemeralValue` / `build_channel` / `build_channels` / `EmptyChannelError` /
     `InvalidChannelUpdateError` + B4F1 的 4 个）—— **L2 内部 API**，**不是**公开门面 ⇒
     门面 7 符号面**零改动**（G15 / G19）。
  ⚠️ `src/freegraph/runtime/__init__.py` **MUST NOT** 被 `src/freegraph/__init__.py` import
  ⇒ 顶层包惰性（G1 / L-1）**恒成立**。
- **测试落 `tests/runtime/`** —— 与既有的 B4F1 测试**同目录**（同属 L2 的测试）⇒
  **复用** `tests/runtime/conftest.py` 的 `run_in_subprocess` 夹具（session 级）⇒
  **既有 conftest 零改动**；`pyproject.toml` 的 `testpaths = ["tests"]` ⇒ **CI 零改动**即被收集。
  ⚠️ **五个新测试模块的落位理由**：
  ① `test_channel_semantics.py` —— 三类通道的**语义**（FR-002…FR-011 / FR-022）；
  ② `test_channel_errors.py` —— **错误契约**单独成文件（FR-017 / FR-025），
     避免「语义文件」与「错误文件」互相污染断言来源；
  ③ `test_channel_mapping.py` —— **映射入口**单独成文件（FR-012）—— 它依赖 B4F1 的解析产物；
  ④ `test_channel_purity.py` —— **纯净性 / 规模 / import 副作用**单独成文件（FR-013 / FR-015 / FR-023 / FR-024）；
  ⑤ `test_channel_contract.py` —— **契约守卫**单独成文件：**解析** `contracts/channel-contract.md`
     逐条比对冻结内容（FR-021 · SC-014）—— 与「纯净性」文件的 import 副作用断言**物理隔离**
     （避免同进程 `sys.modules` 互相污染）
     ⇒ 其中「导入后 `sys.modules` 增量」的断言**必须**在**子进程**里做
     （pytest 收集期已 import 大量模块 ⇒ 同进程不可用 —— 沿用 B4F1 的既有口径）。
- **契约的单一权威 = `contracts/channel-contract.md`**（机器可读 Markdown + `<!-- authority: yes -->` 标记）
  —— 沿用 **B3F1 的层注册表先例**（机器可读 Markdown + 权威标记 + 既有门禁 G25 直接解析它）。
  ⚠️ **与 B4F1 的差别**：`upstream-parity.md` 是**证据表**（逐条 `路径:行号`），
  **测试不解析它** —— 测试**直接断言行为** ⇒ 避免「表与断言同源 ⇒ 自证」
  （B4F1 的判定表相反：它是**判据**，故必须解析它）。
- **`EmptyChannelError` / `InvalidChannelUpdateError` 落 L2 而非契约层** —— 契约层 18 符号面是**冻结面**
  （G7 / G8 / 快照）⇒ 加导出符号要连带改公开面文档 / 门禁 / API 快照 / 兼容矩阵 ⇒ 代价与收益不成比例；
  用户侧 `except FreegraphError`（FR-017 ③）**完全够用**。
  ⚠️ 登记：`src/freegraph/contracts/errors.py` 的 docstring 称其为「内核异常族的**唯一定义处**」，
  但同一 docstring 也写明「后续**可新增子类**」⇒ 本 feature 在 L2 新增子类属该表述的允许范围；
  **本 feature 不改该文件**（契约层零改动）⇒ 登记为措辞口径的澄清，**不改判据**。

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **宪法「质量门禁 3 / 4 / 5」的三部分在本 feature 物理不可达成**（C4 回归 · C8 回归 · fake 模型轮 · 真实模型轮） | 四者**共享同一根因**：它们都要求**状态读取层 / 调度循环 / 完整内核运行时**存在，而 B5F1 按立项书 §5.2 / §6.2 只交付**通道层**（读取 = B5F2 · fresh 读 = B8F1 · 调度 = B7F1 · 编译执行 = B7F2 / B7F3）⇒ **任何 spec 设计都无法在本 feature 满足这四条** ⇒ 依宪法 **v1.6.0** 的窄口径通则处置（偏离登记 + 发起者追认 + 具名承接方） | **替代方案 A：硬写进 CI**（让验收脚本在「无图可跑」时判通过而不登记）⇒ **静默稀释宪法** + 门禁语义被扭曲 ⇒ **不可行**。<br>**替代方案 B：写一条永久红的 CI** ⇒ 违反「feature 必须能独立通过门禁」· PR-4 ⇒ **不可行**。<br>**替代方案 C：改宪法正文** ⇒ 违反「**MUST NOT** 以本条删改宪法正文」⇒ **不可行**。<br>**替代方案 D：把 B5F1 扩成「通道 + 读取 + 运行时」** ⇒ 越过立项书的 feature 边界 ⇒ **不可行**。<br>**采用的处置**：**偏离登记（R-1）+ 发起者追认（`tasks.md` 的阻断合入任务）+ 承接条款已在目标 feature 的提示词初稿中既有**（B5F2 · B8F1 · B7F2 / B7F3 · B25F1）⇒ **红线判据一律不放宽**（依赖 / 许可证 / 商标 / 零出站四条红线在本 feature 照常执行）。 |
| **通道抽象用 `abc.ABC` 而非 `typing.Protocol`** | 「唯一实现点」需要**运行时**可判定的继承关系（抽象类不可实例化）⇒ 且 `clear()` 的**默认无操作**实现需要一个「基类提供默认、子类覆写」的机制 | **替代方案 A：`Protocol`** ⇒ 只在**类型检查期**生效；运行期 `Channel("k", int)` 仍可实例化 ⇒ 「抽象」名存实亡；且与 `Protocol` 并存会形成**第二个**「通道长什么样」的判定点。<br>**替代方案 B：鸭子类型（无抽象基类）** ⇒ 三个子类各自实现 `clear()` 的默认行为 ⇒ 同一语义**重复三遍** ⇒ 违背「收敛」；且「通道只持 4 项」无法用 `__slots__` 统一强制。<br>**采用的处置**：`abc.ABC` + `@abstractmethod` + 基类默认实现（research **D-01** · 实测：实例化抽象类 → `TypeError`）。 |
| **空值推导的剥离用**窄口径**（只剥 `Annotated` / `Required` / `NotRequired`），而非上游的**无差别剥 `__origin__`** | `value_type` MUST 与 B4F1 冻结的 `ChannelSpec.value_type` **同名同义** ⇒ 保留泛型别名（`list[AnyMessage]` 不退化为 `list`）才是「用户在 schema 里写的那个类型」 | **替代方案 A：照抄上游的无差别剥除** ⇒ `list[AnyMessage]` 被悄悄变成 `list` ⇒ 与 B4F1 的冻结字段**不等价**（下游 B5F2 读到的类型信息与 schema 不一致）。<br>**替代方案 B：完全不剥** ⇒ `Required[list]()` 抛 `TypeError` ⇒ 该类 schema 的通道永远「无值」⇒ 与上游**分叉**（research **D-05** 实测）。<br>**采用的处置**：窄口径 + 逐层剥离 ⇒ **空值结果与上游完全等价**（research D-05 的实测表逐条可比），**机制不同** ⇒ 登记为「机制差异 · 结果等价」（不进兼容矩阵）。 |
| **三类通道的清空走**显式 `clear()`**（一律 ⇒ 无值），而非上游的「`update(空序列)`」** | ① 通道 **MUST NOT** 感知 super-step 边界（spec FR-009）⇒ 「本步没有写入」这件事**只有调度层知道**；② FR-001 要求抽象含「状态清空」这一**独立**操作 ⇒ 与「写入」分开 | **替代方案 A：照抄上游的 `update(空序列)` 机制** ⇒ 「清空」语义被塞进「写入」操作里 ⇒ 抽象的三个操作**语义不纯**；且「空序列 ⇒ 无操作」与「空序列 ⇒ 清空」两种口径会在**其它两类通道**上打架（`LastValue.update([])` 该不该清空？）。<br>**替代方案 B：通道自己记步号，到点自清** ⇒ 通道要持有时钟 / 步计数器 ⇒ 违反 FR-009 / FR-013（「只持纯数据」）。<br>**采用的处置**：显式 `clear()`（基类默认无操作 ⇒ **三类通道全部覆写** · 裁定 17 ①）⇒ **可观察语义等价**（值不跨步残留），登记为**机制差异**（spec 裁定 6 · research DR-4）。 ⚠️ **本轮 analyze 轮的补充**：上游**没有** `clear()`，三类通道对 `update([])` 的反应**各不相同**（覆盖型 / 归约型 **no-op**、路由型清空 · research D-17 实测）⇒ **等价落点是「步末调用哪些通道」** ⇒ 步末**只**清路由型（**B7F1** · contract §7 `B-2` · upstream-parity P-12 / S-05 · research DR-6）。 |
| **`build_channels` 返回**可变** `dict`（与 B4F1 的不可变 `SchemaSpec.channels` 形态不同）** | 下游（**B5F2** 读取层 / **B7F1** 调度层）需要在这份映射之上**增补内部通道**（如路由通道）⇒ 不可变映射会逼调用方先拷贝 | **替代方案 A：返回 `MappingProxyType`**（与 B4F1 同款）⇒ 每次增补都要「拷贝成新 dict」⇒ 多一次心智负担，且**返回值语义**（可变的活集合 vs 冻结的解析产物）本就不同 ⇒ 形态不同是**有意的**。<br>**替代方案 B：另设一个可变入口** ⇒ 两个入口 ⇒ **第二个**「通道集合长什么样」的判定点 ⇒ 违背「收敛」。<br>**采用的处置**：返回**保序** `dict`（3.7+ 保序 · research **D-14**），并在 `data-model.md` 登记「与 B4F1 的形态差异及其理由」。 |
