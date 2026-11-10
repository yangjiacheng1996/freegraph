# Implementation Plan: B5F2 · 稀疏状态读取（C4 独立回归测试）+ 差分测试夹具建立

**Branch**: `b5f2-sparse-state-read`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`
⇒ 无 `before_specify` 钩子；既有 6 个 feature 同样在 `main` 上开发） | **Date**: 2026-11-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b5f2-sparse-state-read/spec.md`

**feature ID**: `B5F2`（**M1 运行时内核**的第 7 个 feature · 前置 **B5F1** · 后续解锁 **B7F1**）

---

## Summary

交付 freegraph 的**状态读取层**与**差分测试夹具**——把「**稀疏状态**（C4）」这条最易被静默破坏的契约
钉成一条**独立回归测试**，并把「freegraph 与 LangGraph 等价」从**主张**变成**可复现的证据**：

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **稀疏读取**（`read_channels`） | 节点入参**只含当前有值的 channel** · 结果是**普通 `dict`** | 判据 = `is_available()`（**非**捕获异常）· `skip_empty` **缺省 `True`** |
| **fresh 读**（`local_read`） | 「**当前值 + 本任务本次写入**」的视图 | **副本法**（复制通道 → 在副本上 `update` → 读副本 → 丢弃）⇒ **绑定与可用性判定零污染**（作用域见 Constraints · 唯一表述源 = `read-contract.md` §3.3 / §4 **I-5**） |
| **C4 独立回归测试** | `"llm_calls" not in node_input` 且 `.get("llm_calls", 0) == 0` | 断言住在 `tests/runtime/`（**避开门禁 G2**）· 挂载点 `status` 翻 `landed` |
| **差分测试夹具** | 同一份**图规格**跑 `langgraph` 与 `freegraph` ⇒ 比对**三项投影** | 事件序列先**归一化**为 `(步序, 节点名, 写入)`；**空更新 ⇒ 写入为 `None`**（实测冻结） |

技术方案（读取层**只依赖标准库**，零第三方依赖）：

| 环节 | 手段 | 依据 |
|---|---|---|
| 读取抽象 | **同一模块**内的两个自由函数（`read_channels` / `local_read`）⇒ 全仓**无第三个**读取实现点 | 裁定 1 · FR-001 |
| 稀疏判据 | `Channel.is_available()`（**恒不抛错**）⇒ **机制**与上游不同、**语义**等价 | research **D-05** · parity P-01 |
| 结果形态 | **新建**的普通 `dict`（`type(result) is dict`）· 值**按引用**（**不**深拷贝） | 裁定 10 · FR-004 / FR-005 |
| 「空」的定义 | 「**无值**」⇒ 缺席；「**值为 `None`**」⇒ **出现**（值为 `None`） | 裁定 9 · parity P-09 |
| 不过滤模式 | `skip_empty=False` ⇒ 读到无值**抛 `EmptyChannelError`**（**不**以 `None` 冒充） | 裁定 3 · parity P-04（**不可观察**的分叉） |
| fresh 读构造 | **副本法**（`copy.copy` → 副本上 `update` → 读副本 → 丢弃）⇒ 与上游**逐字同构** | 裁定 4 · research **D-07** / **D-09** |
| 合并语义 | **复用** `Channel.update()`（覆盖 / 归约 / 冲突抛错）⇒ 读取层**不**另写归约逻辑 | 裁定 4 · FR-010 |
| 未知 key 的写入 | 抛 **既有**的 `InvalidChannelUpdateError` ⇒ **零新增错误类型** | 裁定 19 · FR-011 |
| 落位 | `src/freegraph/runtime/read.py` · 导出到 `freegraph.runtime.__all__`（12 → **14**） | 裁定 24 · FR-035 |
| 图规格的 schema | **字段描述**（纯数据）⇒ 运行时**动态构造****一个** `TypedDict` ⇒ 两侧消费**同一对象** | 裁定 21 · research **D-16** |
| 差分的比对 | **三项投影**（节点入参 / 输出状态 / 事件序列）⇒ 事件序列**先归一化** | 裁定 7 · 裁定 23 |
| 上游的隔离 | PEP 735 **`[dependency-groups] differential`**（**钉版本** `langgraph==1.2.11`）⇒ **不进** `Requires-Dist` · 既有 B4F1 依赖判据按 **R-3** **拆分取样范围 + 正向枚举** | 裁定 5 · FR-018 · 裁定 27 |
| 缺席时的行为 | **skip 而非 fail** + **专门 CI 步骤**真实执行（⇒ 不做「永远 skip ⇒ 假绿」） | 裁定 11 · 裁定 25 · FR-019 / FR-025 |

**零新增公开 API、零新增错误类型、零新增门禁编号**：契约层 **18** 符号面与门面 **7** 符号面**一字不动**
（G7 / G15 / G19 恒成立）；`freegraph.runtime` 的导出从 **12 → 14** 个符号（**L2 内部 API**，
不进兼容矩阵 · 沿用 B4F1 裁定 6 ③ / B5F1 裁定 6 ③）；`langgraph` **不写进任何发行依赖声明**。

**上游核实已在 Phase 0 完成**（`langgraph 1.2.11` · 临时 venv · **不进仓库**）⇒ 详见
[research.md](./research.md) §1（**D-01…D-18**）与
[contracts/upstream-parity.md](./contracts/upstream-parity.md)（**12 条** + 实测基线）。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`pyproject.toml` 的 `requires-python = ">=3.11"`）；
**typing 构件上限 = 3.11**（宪法「运行时环境基线」）—— 本 feature 用到的构件**全部 ≤ 3.11**：
`collections.abc.Mapping` / `Sequence` · `copy.copy`（标准库 · 非 typing）·
`typing.TypedDict`（**函数式**写法 · 3.11 完整支持）· `abc`。
**MUST NOT** 使用 `TypeAliasType`(3.12) / `override`(3.12) / `ReadOnly`(3.13) / `TypeIs`(3.13)
或 PEP 695 `type` 语句。**主判定 = CI 矩阵最低档 3.11 跑全量测试**。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []` · 沿用现状）。
**开发期**：`pytest` / `packaging`（既有 `[dependency-groups] dev`）—— **零新增**。
**本 feature 新增一个依赖组**（**不是** extra · 宪法 v1.7.0 禁止 v1.0 含 extra）：

```toml
[dependency-groups]
differential = [
    "langgraph==1.2.11",   # ← **钉版本**：与 parity 表的核实版本一致 ⇒ 换版本 MUST 重新核实全部行号
]
```

⚠️ **MUST NOT** 把 `langgraph` 写进 `[project].dependencies` / `[project.optional-dependencies]`
⇒ 门禁 **G3**（基础安装闭包为空集）/ **G21** / **G22** 恒绿（**PEP 735 依赖组不进 `Requires-Dist`**）。
⚠️ 覆盖率工具**也不进依赖**（沿用 B5F1 的口径）⇒ 开发期临时安装、实测输出记入人工验证记录。

**Storage**: N/A —— 本 feature 无运行时持久化（checkpoint 属 **B14F1**）。
**仓库内的权威工件** = **纯文本 Markdown 契约**（三份）：
[read-contract.md](./contracts/read-contract.md)（读取契约 · **唯一权威**）·
[upstream-parity.md](./contracts/upstream-parity.md)（上游对照 · **证据表**）·
[differential-fixture.md](./contracts/differential-fixture.md)（差分夹具契约 · **唯一权威**）。

**Testing**: pytest + 标准库 `collections.abc` / `copy` / `typing`。
**差分夹具**需要 `langgraph`（**缺席 ⇒ skip**）。
**需要子进程的断言**（SC-010 的「内核路径零上游导入」· SC-016 的「零环境变量 / 零出站」）
**必须在子进程中执行** ⇒ **复用 B4F1 已有的 `tests/runtime/conftest.py` 夹具 `run_in_subprocess`**
（session 级）⇒ **既有 conftest 零改动**。

**Target Platform**: 任意 CPython 3.11+ 平台（Linux / macOS / Windows）。
CI 的 `testpaths = ["tests"]` ⇒ 新增的 `tests/runtime/test_read_*.py` 与 `tests/differential/`
**自动被收集**。

**Project Type**: library（Python 库；发行名 = 导入名 = `freegraph`；D1 决议：不拆独立发行包）。

**Performance Goals**: **N/A（不设时间预算）** —— 读取是**纯内存**、**单遍遍历**、无 I/O / 无网络 / 无锁。
**规模口径**用**结构口径**表达（沿用 B5F1 的口径）：结果 `dict` 的 key 数 ≤ schema 的 key 数；
`local_read` 的副本活到函数返回即**丢弃** ⇒ 空间 `O(通道数)`（瞬时）。
⚠️ **MUST NOT** 用墙钟耗时做断言（CI 假红）。

**Constraints**（**主要**来自 spec 的 MUST 条目；未逐条列出的 FR 见 `tasks.md` 的追溯表）：

| 约束 | spec 条目 |
|---|---|
| 只依赖**标准库**；MUST NOT import `langchain*` / `langgraph*` / `langsmith` / `pydantic` / `typing_extensions` | FR-022 · SC-010 |
| 内核路径 MUST NOT import `langgraph`（`langgraph` 的导入**只**允许在测试代码与依赖组里） | FR-020 · SC-010 |
| MUST **NOT** 读取**任何**环境变量；零出站；零文件 I/O；导入**无副作用** | FR-023 · SC-016 |
| 结果 MUST 是**新建**的**普通 `dict`**（`type(result) is dict`）· 值**按引用** | FR-004 / FR-005 · SC-004 |
| 「空」MUST 是「**无值**」⇒ 缺席；「值为 `None`」⇒ **出现** | FR-006 · SC-003 |
| `skip_empty` **缺省 `True`**；`False` ⇒ 读到无值**抛 `EmptyChannelError`** | FR-007 · SC-003 / SC-027 |
| fresh 读 MUST 用**副本法**⇒ 通道的**绑定与可用性判定零污染**（作用域 = `contracts/read-contract.md` §3.3 / §4 **I-5**）；合并 MUST 复用 `Channel.update()`；⚠️「**值对象**被**就地修改型**归约器改写」属**已知面**（**不计入**该判据 · **不修**） | FR-009 / FR-010 · SC-005 |
| **两个稀疏入口 MUST 逐字相等**：`read_channels(channels)` 与 `local_read(channels, {}, fresh=False)` 的结果差异 == **0**（key 集合 + key 顺序 + 逐 key 值同一对象）⇒「稀疏读」只有一处实现 | FR-038 · SC-033 |
| 未知 key 的写入 ⇒ 抛**既有**的 `InvalidChannelUpdateError`；MUST **NOT** 新增错误类型 | FR-011 · SC-024 |
| C4 独立回归测试 MUST **否定式**断言；MUST NOT 写成宽松断言 | FR-012 · SC-001 / SC-002 |
| C4 挂载点 MUST 翻 `landed`；C8 挂载点 MUST **NOT** 改动；元测试 MUST **只**做路径扫描（G2） | FR-013 / FR-032 · SC-015 / SC-025 |
| 差分夹具 MUST 以**一份**图规格驱动两侧；图规格 = **线性单链** + **预留条件边字段** | FR-014 / FR-015 · SC-013 |
| 差分 MUST 比对**三项投影**；事件序列 MUST 先归一化（**空更新 ⇒ 写入为 `None`**） | FR-016 / FR-034 · SC-006 / SC-007 / **SC-032** / SC-028 |
| 判定记录 MUST 含**比对的具体字段**（MUST NOT 只写「一致」） | FR-017 · SC-019 |
| `langgraph` MUST 以 **PEP 735 依赖组**引入；MUST **NOT** 进 `Requires-Dist` / **MUST NOT** 用 extra | FR-018 · SC-008 |
| 既有 **B4F1** 的两条依赖判据 MUST 按 **R-3** **拆分取样范围**（发行面部分**逐字保留** + `[dependency-groups]` 改**正向枚举**）并**新增**「上游只许经 `--group differential` 安装」的正向约束（**原断言一条未放宽** · **红线总量不减**） | FR-037 · SC-031 |
| `langgraph` 缺席 ⇒ **skip 而非 fail**；MUST 有**专门 CI 步骤**真实执行 | FR-019 / FR-025 · SC-009 / SC-014 |
| 差分夹具 MUST 在 CI 中**真实执行** ≥ 1 次；MUST **NOT** 新增 required check 名 · MUST **NOT** 改 `ci-matrix` §1 的作业形状 ⇒ 落地形态 = 既有作业内的专门**步骤** · 且该步骤 MUST 位于**全量测试套件步骤（步骤 6）之前** | FR-019 / FR-025 · SC-014 |
| 图规格 MUST **预留「模型工厂」钩子**（本 feature **恒空** ⇒ 非空即**显式失败**）；MUST **NOT** 自行实现 fake 注入 | FR-036 · SC-030 |
| 读取层 MUST 落 **L2** 的独立文件 `runtime/read.py`；导出面 12 → **14**；MUST NOT 进兼容矩阵 | FR-021 / FR-035 · SC-011 / SC-029 |
| 既有冻结面**零改动**（契约层 18 / 门面 7 / 兼容矩阵 / `THIRD_PARTY_NOTICES` / 门禁编号） | FR-026 · SC-011 |
| 新建源文件 MUST 带**署名头**且 docstring 为首个语句 | FR-028 · SC-011 / SC-020 |
| 人工验证记录（五段式 + 来源覆盖表）落 `harness/verification/B5F2/` | — · SC-019 |
| 覆盖率判据只管本 feature 新增代码（`read.py` 全文 + `__init__.py` 的新增部分）行/分支 == **100%** | FR-027 · SC-018 |
| 读取层的**可判定不变量** MUST 由一条**契约守卫测试**逐条断言（**解析** `contracts/read-contract.md` §4 的 **I-1…I-11**）⇒ **MUST NOT** 只测行为而不校验契约文本（防「契约与实现同源即自证」） | FR-027（裁定 32 ②）· SC-018 |
| 「**零污染**」口径的**唯一表述源** = `contracts/read-contract.md` §3.3 / §4（**I-5**）⇒ 本 plan 与 tasks **只引用编号、不重述全文**（防措辞漂移 · 裁定 29 的成因） | FR-009 · SC-005 |

**Scale/Scope**: schema 的 **key 数**：典型 **2–20**（`target.py` = 2 个；用户 schema 常见 3–10 个）。
**实现 ≈ 340 行 / 测试 ≈ 520 行**（立项书 §5.2 的估算，作为 plan 的输入）。
本 feature **零新增公开 API** ⇒ 兼容矩阵**零新增行**。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 通过项（逐条）

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith 依赖 · 自身零出站 · 零环境变量） | FR-020 / FR-023 · 既有 **G24**（配置层扫描 `src/freegraph/**`）· **G26**（网络静态扫描）· **G27**（零出站动态） | ✅ |
| 原则 II（内核纯净 · 状态语义 MUST 与 LangGraph 等价） | FR-022（零依赖）· FR-018（上游**仅** PEP 735 依赖组）· **G21 / G22 / G3**（依赖闭包为空集）· `contracts/upstream-parity.md`（**12 条**逐条对照〔**9 条**带 `路径:行号` + **2 条**带实测编号 + **P-12** 上游侧待实测〕+ 实测基线）承载 C4 的等价性 | ⚠️ **既有 B4F1 依赖判据的取样范围拆分** ⇒ 见**登记项 R-3** |
| 原则 III（验收契约优先 · `target.py` 只读） | 本 feature **零改动** `target.py`；其 schema（`messages: Annotated[list[AnyMessage], operator.add]` · `llm_calls: int`）**必须能映射到通道**⇒ C4 回归测试用**同名 key** ⇒ 守住 `target.py:100` 的 `state.get('llm_calls', 0) + 1` | ✅ |
| 原则 IV（可诊断性） | N/A（本 feature **无运行期可观测面**；诊断靠既有错误类型的结构化字段 `key`） | ✅ 边界内 |
| 原则 V（人工验收是最终验收标准） | 人工验证记录（五段式 + 来源覆盖表）· 差分夹具的判定**记录具体字段**（SC-019） | ⚠️ **门禁 5 的「真实模型一轮」不适用** ⇒ 见**登记项 R-1** |
| 原则 VI（规格驱动 · tasks 可逐条勾选） | 本 plan + `tasks.md`（含 FR ↔ SC 追溯表） | ✅ |
| 原则 VII（职责边界 · 契约 C1–C27） | FR-003 = **C4** 的**执行侧**落地；FR-008 = **C8** 的**读取原语**（路由语义属 **B8F1**）；上游 MUST NOT import L3/L4/L5 | ⚠️ **门禁 3 的 C4「节点边界」与 C8 两条**不在本 feature ⇒ 见**登记项 R-1**；⚠️ **G29 判定 3 的文本按 R-4 最小修订**（**判定代码不变**） |
| 原则 VIII（证据与术语纪律） | `research.md` 每条决策附**实测命令 + 真实输出**（D-01…D-18）；上游引用标 `路径:行号` + 核实版本 `langgraph 1.2.11`；**事实性表述的更正已登记**（research §3 的 C-1…C-5） | ✅ |
| 原则 IX（许可证与商标红线 · NON-NEGOTIABLE） | 上游**仅**测试侧依赖（**不进发行元数据**）⇒ `THIRD_PARTY_NOTICES` **无需变更**；**零品牌资产**（只重写语义，不复制上游代码） | ✅ |
| 原则 X（文档合规 + 源文件署名头） | FR-028（署名头 · 既有 **G30** 全仓扫描自动覆盖新文件）· 兼容矩阵**零新增行**（须在人工记录中显式记「无新增」） | ✅ |
| 运行时环境基线（Python 3.11 · typing 上限 3.11） | 本 feature 只用 ≤ 3.11 构件（Technical Context 已逐项列出）· 最低档 3.11 跑全量测试 | ✅ |
| 依赖白名单 / 黑名单（包层 · 配置层 · 网络层） | 上游**不进发行依赖声明** ⇒ **G3 / G21 / G23** 恒绿；**零新增运行时依赖** ⇒ **G24 / G26 / G27** 恒绿 | ✅ |
| **跨 feature 承接的接线通则（v1.8.0）** | FR-031 / FR-036 · 裁定 15 / 裁定 18 / 裁定 26 / 裁定 33 ③ ⇒ **四条**承接条款**已写入** B7F1 / B8F1 / B25F1 的提示词初稿（宪法 v1.8.0 的**首次适用**）· 另 **裁定 27 / FR-037 → B4F1**（**B4F1 是上一棒 ⇒ 非本通则触发条件**）⇒ 按**同款形态**做「**只接线**」记录（处置依据 = 取样范围 bug 修复 + 发起者追认 · **无需宪法修订**）⇒ 第四处接线由 **T039** 复核并校正措辞 · 第五处（**B8F1 MUST 显式传 `fresh=True`** · FR-031 ② / SC-023）并入 **T039** 一并接线 | ✅ |
| 质量门禁 1 / 2 / 6 / 7 | ① 规格 + tasks 可勾选 ② 依赖**零发行新增** ⑥ 证据（research + 对照表 + 来源覆盖表）⑦ 文档合规（署名头 + 兼容矩阵零新增） | ✅ |
| 质量门禁 3 / 4 / 5 的**内核运行时相关部分** | ⚠️ **物理不可达成** ⇒ **登记项 R-1**（偏离登记 + 发起者追认） | ⚠️ **见 R-1** |
| 发布门禁（发行产物纯度） | 本 feature **不接入**（B24F1）· 新增代码在 `src/freegraph/runtime/` 内 ⇒ **不污染**产物纯度；依赖组**不进** sdist | ✅ 边界内 |

### ⚠️ 登记项 R-1（宪法「质量门禁 3 / 4 / 5」的偏离登记 · 需发起者追认）

**依据**：宪法 **v1.7.0**「质量门禁的分阶段落地与发起者追认」（**窄口径**通则 · 首次适用 = B3F1）。
**本 feature 与 B5F1 的 R-1 同根因、同承接方** ⇒ **沿用既有承接条款**，MUST NOT 新造承接机制。

| # | 被偏离的**具体门禁项** | 不可达成的根因 | 判据未被放宽的论证 | 承接方（feature ID + 里程碑） | 承接机制 |
|---|---|---|---|---|---|
| ① | **门禁 3** 的 **C4** —— 「节点入参只含有值的 key」的**完整**形态（断言对象 = **真实节点收到的 dict**） | 本 feature 按立项书 §5.2 只交付**读取层**（**调度循环属 B7F1**）⇒ **无「节点」** ⇒ 断言对象只能是「读取原语产出的那个 dict」（它**就是**调度器将要交给节点的那个 dict） | C4 的**判据一字未改**：`"llm_calls" not in node_input` / `.get("llm_calls", 0) == 0`（**否定式**）逐字落地；且**上游侧**已实测出对照值（`NODE_INPUT_KEYS: ['messages']` · research **D-11**） | **B7F1**（M1） | **承接条款已写入** `harness/features/B7F1_任务准备与super-step循环.md:41`（§2）· `:134`（§9 契约门禁）· `:142`（§10 交付物）⇒ 由 B7F1 的 spec 落成 **FR + 裁定**（宪法 **v1.8.0** 通则）⇒ 本 feature 的 `tasks.md` 留一条**复核**条目 |
| ② | **门禁 3** 的 **C8**（条件边 fresh 状态） | fresh 读**原语**在本 feature；**路由语义 + 独立回归测试**属 **B8F1**（M2） | 本 feature 交付 C8 的**读取原语**（fresh 视图 + 零污染）⇒ C8 的**判据未改** | **B8F1**（M2） | **已就位**：B3F1 落的挂载点 `GATE-MOUNT: C8 · status=not-landed`（本 feature **MUST NOT** 改动） |
| ③ | **门禁 4** 的「**fake 模型跑通验收基线的一轮**」与**门禁 5** + 原则 V 的「人工验证记录含**真实模型一轮**」 | 验收基线跑通需要**完整内核运行时**（编译 + 执行）⇒ 属 **B7F2 / B7F3** ⇒ 本 feature **无图可跑** | CI **不写**一条永久红的断言（违宪 PR-4）；五段式记录 + 来源覆盖表**照常落地** | **B7F2 + B7F3**（M1 / M2）· **B25F1**（M4） | **已就位**：B3F1 的裁定 22 已把「fake 轮」的承接条款写入 B7F2 / B7F3 / B25F1 的提示词初稿 |

**红线（未被触碰）**：依赖红线（`langsmith` / `langchain*` / `langgraph*`）· 许可证红线 · 商标红线 ·
零出站红线 —— **全部在本 feature 照常执行**（FR-020 / FR-022 / FR-023 + G3 / G21 / G22 / G23 / G24 / G26 / G27）。

**⇒ 请发起者在合入前追认此登记项**（落点：`tasks.md` 的一条**阻断合入**的追认任务 ·
追认文字 MUST 落在 `harness/verification/B5F2/manual-verification.md`）。

### ⚠️ 登记项 R-2（**CI 矩阵契约**的修订需求 · 需发起者追认）

**依据**：**FR-025** 要求「差分夹具 MUST 有**专门的 CI 步骤**真实执行」（**2026-11-09 已由 spec 裁定 25
更正**：原文写的是「专门的 CI **作业**」⇒ 该 MUST 建立在**未经证实的可行性假设**上 —— 写 spec 时
**未读过** `ci-matrix` 冻结面契约 ⇒ 宪法原则 VIII）⇒ 而
`specs/b3f1-scaffold-ci-gates/contracts/ci-matrix.md` 是**冻结面**（矩阵的**形状**与**分层**即实现契约），
且 §4.1 的 **7 个 required check 名** MUST 逐字不变（分支保护按 job 名精确匹配 ⇒ 改名即静默失效）。

| # | 事项 | 方案 | 契约影响 | 选定理由 |
|---|---|---|---|---|
| ① | 让差分夹具**真实执行**（而非永远 skip） | **方案 α′**：在**既有作业内新增一个独立步骤**（**步骤 5.6** · `uv pip install --python .venv --group differential`）⇒ 差分用例被**既有的 pytest 步骤 6** 收集并执行 | **新增 1 个 step**（**步骤 5.5 一字不动** ⇒ 保持「只做 v2.0 extras 预验证」的**单一语义** · G21 / G23 的取证面不被扰动）+ 契约的修订记录 ⇒ **§1 的 7 个作业形状不变** · **§4.1 的 7 个 required check 名不变** ⇒ **分支保护零变更** | **零新增 job 名** ⇒ 落地形态 = **既有作业内的专门「步骤」**（**裁定 25 / 裁定 A**）· 且**不让步骤 5.5 同时承担两件事**（v2.0 extras 预验证 vs 差分依赖）⇒ 两个语义的取证口径各自独立 |
| ② | 同上 | **方案 β**：新增第 8 个 job（名字进 required checks） | **§1 + §4.1 + 分支保护**三处 ⇒ 修订面最大 | ❌ 不选（成本 / 风险更高 · 且与 **裁定 25** 的约束句直接冲突） |
| ③ | 同上 | **方案 γ**：**不**改契约（差分夹具在 CI 永远 skip） | 零 | ❌ 不选（⇒ SC-014「真实执行次数 ≥ 1」不可达成 ⇒ **假绿**） |

**方案 α′ 的已知风险（**实现阶段 MUST 实测** · 落点 = tasks **T035**）**：
① **装该组的作业**（**至少 1 个** · 实测通过的那档 · Linux 全量档优先；其余档 **MAY** 装 ⇒ 装不上的档
   **不装**并登记）⇒ CI 时间与体积上升（可接受：上游只装在测试侧）；
② **G28（断网等价性 · Linux 档）**会在**断网**下带着 `langgraph` 跑全量套件 ⇒
   差分用例会在**断网**下**真实执行** ⇒ **MUST 实测** `langgraph` 在断网下可 import 且可跑通
   （**MUST NOT** 假设）⇒ 若失败 ⇒ 该用例 MUST 纳入 G28 的**可机读排除清单**（**MUST NOT** 删断言）；
③ **G22（隔离环境 · Linux 档）**建**自己的**隔离 venv 只装 `freegraph` ⇒ **不受**上游影响 ✓；
④ **G27（零出站动态 · Linux 档）**与 G28 同在**步骤 9**、**同一个 venv**（步骤 5.6 已装上游 ⇒ 带
   `langchain-core` / `langsmith`）里跑 `pytest tests/` 全量套件 + socket 监测 ⇒ 上游在 **socket 监测下**
   被 import 的行为 **MUST 实测**（**MUST NOT** 假设其零出站）⇒ 若出现上游自身的出站 ⇒ MUST 按
   「**框架出站 = 0**」的归因口径（只观测不阻断 · 按发起方归因）判定 **MUST NOT** 记到 freegraph 头上
   ⇒ **实测结论 MUST 落入人工验证记录**（2026-11-10 · 分析轮补登记）。
⑤ **执行口径（2026-11-10 · 分析轮补登记）**：CI 的测试步骤用
   `uv run --no-project --python .venv python -m pytest`（`--no-project` 是刻意为之：避免 uv **同步环境**
   ⇒ 不会把手工装入的 `differential` 组卸掉）⇒ **本地复现 MUST 用同款命令** ⇒ 若改用 `uv run`（**无**
   `--no-project`）⇒ uv 会同步环境并**卸载** `differential` 组 ⇒ 差分用例**全 skip** ⇒ **假绿**
   ⇒ tasks `T006` / `T034` 已同步该口径。

**红线（未被触碰）**：**MUST NOT** 改 §1 的作业形状 · **MUST NOT** 改 §4.1 的 required check 名 ·
**MUST NOT** 新增门禁编号 · **MUST NOT** 把上游写进发行依赖声明。
**落地形态**：**既有作业内的专门「步骤」**（= **新增步骤 5.6** · `uv pip install --python .venv --group differential`
· **步骤 5.5 一字不动**）⇒ **零新增 job 名 ⇒ 分支保护零变更**（spec **裁定 25**）。
⚠️ **位置约束（2026-11-09 · clarify 第四轮 · 裁定 30 增补）**：**步骤 5.6 MUST 位于 `ci.yml` 的
全量测试套件步骤（步骤 6）之前** —— 否则差分用例在步骤 6 执行时**尚未装上游** ⇒ **永远 skip**
⇒ `SC-014`「真实执行次数 ≥ 1」**不可达** ⇒ **假绿**（这正是 R-2 要防的那件事）。
⇒ 落地顺序 MUST 是：**步骤 5.5（extras 预验证）→ 步骤 5.6（`--group differential`）→ 步骤 6（全量测试套件）**。

**⇒ 请发起者在合入前追认此登记项**（落点：`tasks.md` 的一条**阻断合入**的追认任务 +
`ci-matrix.md` 的一次带修订记录的契约修订）。

### ⚠️ 登记项 R-3（**既有依赖判据的取样范围拆分** · 需发起者追认）

**依据**：本 feature 引入**第一个上游 dev / test 依赖**（PEP 735 的 `differential` 组 · FR-018 / 裁定 5），
而 **B4F1** 时期的既有判据 `test_dependency_declarations_contain_no_upstream_package`
（`tests/runtime/test_parse_contract.py:328-351`）把「零上游」的取样范围**覆盖到三处**声明 ——
`[project].dependencies` / `[project].optional-dependencies]` / **`[dependency-groups]`** ——
⇒ 该判据在 T001 之后**必然变红** ⇒ 若不显式处置，执行者极可能「删断言 / 放宽断言」。

**定性（2026-11-09 · clarify 第四轮 · spec 裁定 27 改写）**：本案的根因 = 「**原判据的取样范围与红线作用域
不一致**（把**开发工具链** `[dependency-groups]` 与**发行面**混为一谈）」⇒ 属「**取样范围 bug 修复**」
⇒ **不属**宪法 **v1.6.0** 的门禁偏离（其窄口径根因 = 「该 feature 按里程碑**不交付其前置能力**」·
与本案根因**不同**）· **不属**宪法 **v1.8.0** 的跨 feature 承接（其触发条件 = 「指名**下一棒** feature」·
**B4F1 是上一棒**）⇒ **无需宪法修订** ⇒ 宪法正文与门禁编号 **G1–G30** **一字不动**。
**处置 = 发起者追认（T043）+ 写入 B4F1 承接条款（只接线）+ 拆分取样范围 + 新增正向断言**
⇒ **红线总量不减**。

| # | 被处置的**具体判据** | 根因 | 判据未被放宽的论证 | 承接方 | 承接机制 |
|---|---|---|---|---|---|
| ① | `test_dependency_declarations_contain_no_upstream_package`：**「三处声明中零上游」** ⇒ **拆分取样范围** —— **发行面部分逐字保留**（`[project].dependencies` 零上游**一字不动**）+ `[dependency-groups]` 改**正向枚举**（含上游包名的组 == **恰好 1 个**且为 `differential`） | 本 feature 按 FR-018 引入**第一个**上游 dev / test 依赖；`[dependency-groups]` 是**开发工具链**（**从不**进发行元数据 · 宪法 v1.7.0 · 实测 `[dependency-groups] dev` 安装后 `Requires-Dist` 仍为 `None`）⇒ 原判据把**开发工具链**与**发行面**混为一谈 | ① 「必装依赖零上游」**原断言一字未动**；② extra 段本仓库 v1.0 **不存在**（宪法 v1.7.0）⇒ 天然为零；③ **新增**正向约束「上游只许出现在 `differential` 组」⇒ **红线总量增加**；④ `Requires-Dist` **整体为空**的判据（A5）**未动** | **B5F2**（M1 · **本 feature**） | 修订在本 feature 内落地（tasks **T041**）+ **指名承接条款**写入 `harness/features/B4F1_schema解析与归约器提取.md`（宪法 v1.8.0「只接线」）+ 发起者追认（tasks **T043**） |
| ② | `test_ci_workflow_never_installs_langgraph`：「`ci.yml` 中 `langgraph` 字样 == 0」 ⇒ **原文逐字保留** + **新增**一条正向断言（若出现上游安装，则**只许**经 `--group differential`；上游**不得**出现在发行依赖声明与基础安装步骤中） | T035 / T036 必须让 CI **真实安装**上游并跑差分夹具（FR-025 · SC-014）⇒ 否则「永远 skip ⇒ 假绿」 | ① **原断言一字未动**（`ci.yml` 文本中 `langgraph` 字样 == **0**）；② 「上游**不得**进发行依赖声明 / 基础安装步骤」**未放宽**；③ 「`Requires-Dist` 整体为空」**未动**；④ **新增**「安装路径 == 仅 `--group differential`」的**可判定**正向约束。<br>⚠️ **事实更正**：步骤 5.6 的命令串 `uv pip install --python .venv --group differential` **不含** `langgraph` 字样 ⇒ **原断言根本不会变红** ⇒ 原 R-3 ②「该判据必然变红」的前提**不成立** ⇒ 本行是**新增正向约束**（**不是**放宽） | **B5F2**（M1 · **本 feature**） | 同上（tasks **T042** / **T043**） |

**闸口归属（2026-11-09 · clarify 第四轮 · spec 裁定 28）**：**SC-031** 的 **① ② ③ ⑤** 在**执行闸口 A1**
验收 · **④**（`ci.yml` 的上游安装路径）在**执行闸口 A7** 验收（④ 的对象要到 **T035** 才进入 `ci.yml`
⇒ 在 A1 无法判定）⇒ **SC-031 措辞不动 · SC 编号不变**。

**红线（未被触碰）**：依赖红线（`langsmith` / `langchain*` / `langgraph*` 在**发行面**）· 许可证红线 ·
商标红线 · 零出站红线 —— **全部照常执行**（FR-020 / FR-022 / FR-023 + G3 / G21 / G22 / G23 / G24 / G26 / G27）。
⚠️ **覆盖面被拆分而非削减**：**发行面红线一字未动** + `[dependency-groups]` 由**混算**改为**正向枚举**
⇒ **红线总量不减**（新增一条「上游只许出现在 `differential` 组」的正向约束）。

**⇒ 请发起者在合入前追认此登记项**（落点：`tasks.md` 的一条**阻断合入**的追认任务 **T043** ·
追认文字 MUST 落在 `harness/verification/B5F2/manual-verification.md`）。

### ⚠️ 登记项 R-4（**G29 冻结契约**的最小修订 · 需发起者追认）

**依据**：`FR-013`（C4 挂载点的 `status` 由 `not-landed` 翻 `landed`）与 **G29 的判定细则**存在**直接冲突**
——`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 的 **G29 判定 3** 与
`harness/scripts/gates/gate_G29_contract_carrier.py` 的 **docstring**（`:19-24`）写的是
「挂载点 **MUST 明确标记为「未落地」**」（**B3F1 时期的快照措辞**）⇒ 与 `FR-026`
（「门禁编号与判定口径**一字不动**」）**自相矛盾**；且 `landed` 的**语义**（读取层口径 vs 节点边界口径）
**未定义** ⇒ 机器可读信号**强于**实际防线位置。
⚠️ **判定代码无冲突**：`gate_G29_contract_carrier.py:232` 的 `status not in {"not-landed", "landed"}`
**早已接受两态** ⇒ **CI 不会红** ⇒ 本项是**契约文本与实现的一致性**问题（不是 CI 阻断问题）。

| # | 被修订的**具体判据** | 根因 | 判据未被放宽的论证 | 承接方 | 承接机制 |
|---|---|---|---|---|---|
| ① | `architecture-gates.md` **G29 判定 3** 的第三段：「挂载点 **MUST 明确标记为「未落地」**（MUST NOT 伪装成『已通过』）」 ⇒ **改为两态口径**（`not-landed` / `landed`）+ **定义 `landed` 的语义**（该契约的独立回归测试**已存在且常驻 CI**；**断言对象的边界**由该 feature 的 `spec` 承担） | B5F2 交付 C4 的**读取层口径**独立回归测试 ⇒ 该契约**确已存在** ⇒ 旧的「MUST 未落地」措辞（当时 C4 / C8 两条都未建立的快照）不再成立 | ① **MUST NOT 伪装成「已通过」**这一**红线原样保留**（`landed` MUST 与事实相符）；② **判定代码一行未改**（两态皆接受）⇒ **零新判据、零放宽**；③ **门禁编号 G29 与 G1–G30 连续性不变**；④ 变更只是把「**单态快照**」改成「**两态 + 语义定义**」⇒ 覆盖面**扩大**而非削减 | **B5F2**（M1 · **本 feature**） | 修订在本 feature 内落地（tasks **T048**）+ 发起者追认（tasks **T049** · 阻断合入） |
| ② | `gate_G29_contract_carrier.py` 的 **docstring 第 3 点**（`:19-24`）⇒ 与 ① 同步 | 同上（docstring 是门禁判据的**人读镜像** ⇒ MUST NOT 与契约文本漂移） | 同 ① | 同 ① | 同 ① |

**闸口归属**：**T048**（修订）在 **执行闸口 A7** 验收 · **T049**（追认）是**阻断合入**的任务。

**红线（未被触碰）**：依赖红线 · 许可证红线 · 商标红线 · 零出站红线 —— **全部照常执行**；
**门禁编号 G1–G30 一字不动** · **宪法正文一字不动**（**无需宪法修订** ⇒ 本项**不属**宪法 v1.6.0 的
门禁偏离（其窄口径根因 = 「该 feature 按里程碑**不交付其前置能力**」）· 也**不属** v1.8.0 的跨 feature
承接（无「指名下一棒」的跨 feature 义务）⇒ 属「**冻结面最小修订**」· 与 **R-2** 的 `ci-matrix` 修订**同款形态**）。

**⇒ 请发起者在合入前追认此登记项**（落点：`tasks.md` 的一条**阻断合入**的追认任务 **T049** ·
追认文字 MUST 落在 `harness/verification/B5F2/manual-verification.md`）。

### 门禁编号纪律

**本 feature MUST NOT 新增门禁编号** —— 既有 **G1–G30** 的编号连续性是 B3F1 data-model 的不变量
（「门禁总数 == 30 · 编号连续」）⇒ 新模块由**既有门禁自动覆盖**：

| 既有门禁 | 对本 feature 的覆盖 |
|---|---|
| **G25**（导入图单向 · ARCH-1） | 新增的 `src/freegraph/runtime/read.py` = **L2**（层注册表已登记）⇒ 自动纳入扫描；L2 → L3/L4/L5 的边数 == 0 即 SC-011 |
| **G30**（全仓署名头） | 新建源文件的署名头覆盖率 == 100%（SC-011）⇒ **无需**扩 G5 / G20 的硬编码清单 |
| **G4 / G24 / G26 / G27** | 零环境变量 / 零出站（FR-020 / FR-023） |
| **G3 / G21 / G22 / G23** | 上游**不进发行依赖声明** ⇒ 依赖闭包 / 隔离环境 / 许可证断言恒绿 |
| **G2**（契约层零内部 import） | ⚠️ **本 feature 的新约束**：`tests/contracts/**` **禁止** import `freegraph.*` ⇒ C4 的断言**必须**住 `tests/runtime/`（裁定 20）⇒ **G2 恒绿**（SC-025） |
| **G29**（契约门禁载体 · C4 / C8 挂载点） | C4 挂载点的 `status` 由 `not-landed` 翻 `landed` ⇒ G29 输出「挂载点 C4：**已落地**」（SC-015）· ⚠️ **G29 判定 3 的文本按登记项 **R-4** 最小修订**（两态 + `landed` 语义定义）⇒ **判定代码不变** |
| **G7 / G15 / G19**（公开面） | 契约层 **18** 个 / 门面 **7** 个符号**一字不动** ⇒ `freegraph.runtime` 的 12 → 14 个导出**不计入**公开面（L2 内部 API） |

> **⚠️ 非 G 编号的既有判据（同样须处置）**：**B4F1** 的两条依赖判据
> （`tests/runtime/test_parse_contract.py` 的 `test_dependency_declarations_contain_no_upstream_package` ·
> `test_ci_workflow_never_installs_langgraph`）**不是** G 编号，但同样是**既有红线**
> ⇒ 本 feature 引入第一个上游 dev / test 依赖后 MUST 按**登记项 R-3** **拆分取样范围**（**红线未放宽**）
> ⇒ 见 **R-3** · 裁定 27 · 裁定 28 · FR-037 / SC-031 · tasks **T041 / T042 / T043**。

**⇒ 门禁编号总数仍为 30**（layer-registry.md 与 data-model 的不变量**零改动**）。

### 设计后复核（Phase 1 后 · 模板要求「Re-check after Phase 1 design」）

| 复核项 | 结论 |
|---|---|
| 宪法条款 | **无新增违反** —— Phase 1 产出的 6 份工件（`research.md` / `data-model.md` / `contracts/`×3 / `quickstart.md`）**全部**落在 L2 与 `specs/` 内 ⇒ 依赖 / 许可证 / 商标 / 零出站四条红线**不受影响** |
| 门禁编号 | **仍为 30**（G1–G30）—— Phase 1 **未新增**任何门禁脚本或编号；新增模块由 **G25**（导入图）与 **G30**（署名头）自动覆盖；C4 的落点由 **G2** 与 **G29** 共同约束 |
| 公开面 | **零变更** —— `read-contract.md` 冻结的两个入口（`read_channels` / `local_read`）+ 落位（`runtime/read.py`）+ 导出面（12 → 14）全部属 **L2 内部 API**；契约层 **18** 个 / 门面 **7** 个符号**一字不动** |
| 登记项 **R-1** | **仍然成立**（无图可跑 ⇒ 门禁 3 / 4 / 5 的四部分仍物理不可达成）⇒ 承接方与里程碑**未变**（B7F1 / B8F1 / B7F2 / B7F3 / B25F1） |
| 登记项 **R-2** | **新增**（Phase 1 的 CI 落地方式触发了 ci-matrix 契约的修订需求）⇒ 选定**方案 α′**（落地形态 = 既有作业内的**新增独立步骤 5.6** · 步骤 5.5 一字不动 · spec **裁定 25**）⇒ ⚠️ **第四轮增补**：**步骤 5.6 MUST 位于步骤 6（全量测试套件）之前**（spec **裁定 30**）；**实测项**：G28 断网下差分用例的真实执行 |
| 登记项 **R-3** | **新增**（引入第一个上游 dev / test 依赖 ⇒ 触发 **B4F1** 两条既有依赖判据的**取样范围拆分**）⇒ **拆分取样范围**（发行面部分**逐字保留** + `[dependency-groups]` 改**正向枚举**）+ **新增**「上游只许经 `--group differential` 安装」的正向约束（FR-037 / SC-031 · 裁定 27）⇒ **原断言一条未放宽**；⚠️ **第四轮改写**：定性为「**取样范围 bug 修复**」⇒ **无需宪法修订**（裁定 28）；**实测项**：拆分后的五条断言全成立（①②③⑤ 在 A1 · ④ 在 A7） |
| 登记项 **R-4** | **新增**（2026-11-10 · 分析轮第二轮 · spec **裁定 33 ②**）—— `FR-013`（C4 的 `status` 翻 `landed`）与 **G29 判定 3**（「挂载点 MUST 明确标记为『未落地』」）/ `gate_G29` docstring **直接冲突**，且与 `FR-026`（门禁判定口径一字不动）**自相矛盾** ⇒ **冻结面最小修订**（**判定代码不变** · `gate_G29:232` 早已接受两态 ⇒ 零新判据、零放宽）+ **发起者追认**（T049）⇒ **门禁编号 G1–G30 与宪法正文一字不动**；**实测项**：T048 落地后 G29 的输出仍为「挂载点 C4：**已落地**」且退出码 0 |
| 与上游的等价性 | `contracts/upstream-parity.md` 给出 **12 条**语义点（**P-12 的上游侧待实测** · tasks T044）+ **8 条**实测基线（核实环境 `langgraph 1.2.11`）⇒ 满足 spec FR-028 |
| 事实性表述 | Phase 0 的实测发现 **5 处** spec 表述需更正（research §3 的 C-1…C-5）⇒ **已回写 spec**（**只更正事实**，未改任何判据）⇒ SC-001…SC-031 **全部仍成立**（分析轮新增的 **SC-032** 与该结论**不冲突**） |
| 规模口径的可判定性 | 结果 `dict` 的 key 数 ≤ schema 的 key 数 · 副本**瞬时** ⇒ 全部**可自动判定**（`read-contract.md` §4 的 I-1…I-11） |
| **2026-11-10 · 分析轮修订**（spec **裁定 32**） | ① **新增 `SC-032`**（节点入参投影差异 == 0 ⇒ 三项投影**逐项**有判据）· ② **扩写 `FR-027`**（契约守卫的**正向**锚点）· ③ **`FR-037` ④ 可判定化**（`--group` 白名单 + `differential` 组内容 == 恰好 1 个上游声明）· ④ **R-2 补 G27 风险与 `uv run --no-project` 口径** ⇒ **只增判据、不放宽任何判据** · **零新增门禁编号** · **宪法正文与 G1–G30 一字不动** |
| **2026-11-10 · 分析轮第二轮修订**（spec **裁定 33**） | ① **名字来源的引用更正**（立项书 §5.2 → **guide.md:566 + Q8:121/:132** · 事实性）· ② **G29 冻结契约的最小修订**（登记项 **R-4** · 判定代码不变）+ **发起者追认**（T049）· ③ **立项书回改**（§4.2 S5 / §5.2 B5F2 行 / §9.2 落点 · 只接线 · T047）· ④ **两个稀疏入口 MUST 逐字相等**（新增 `FR-038` / `SC-033`）⇒ **只增判据 / 更正事实 / 登记冻结面修订** · **零新增门禁编号** · **宪法正文与 G1–G30 一字不动** |

---

## Project Structure

### Documentation (this feature)

```text
specs/b5f2-sparse-state-read/
├── plan.md                          # This file (/speckit.plan command output)
├── research.md                      # Phase 0 output —— D-01…D-18 决策 + 实测证据 + DR-1…DR-5 遗留登记 + C-1…C-5 事实更正
├── data-model.md                    # Phase 1 output —— 读取层实体模型 + fresh 读状态机 + 校验规则 + 不变量
├── quickstart.md                    # Phase 1 output —— 可照抄的验证手册（闸口 V1–V12）
├── spec.md                          # 规格（**五轮澄清 + 2026-11-10 分析轮（两轮）** · **33 条裁定** + **28 条澄清问答 Q1–Q28** · FR-001~FR-038 · SC-001~SC-033 · 追溯表 38 行）
├── checklists/
│   └── requirements.md              # 规格质量清单（16/16）
├── contracts/
│   ├── read-contract.md             # 读取契约（操作面 / 两种模式 / fresh 读状态机 / 不变量）—— **唯一权威**
│   ├── upstream-parity.md           # 与上游 LangGraph 的逐条对照（**12 条**）+ 实测基线 + 逐条行号复核
│   └── differential-fixture.md      # 差分夹具契约（图规格形态 / 三项投影 / 归一化 / 判定 / 不比对的范围）—— **唯一权威**
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
    ├── __init__.py                  # ★ 追加导出（12 → 14 个符号 · **L2 内部 API**，非公开门面）
    ├── errors.py                    # 既有（B5F1）· **零改动** —— 复用 EmptyChannelError / InvalidChannelUpdateError
    ├── schema.py                    # 既有（B4F1）· **零改动** —— ChannelSpec / SchemaSpec
    ├── reducer.py                   # 既有（B4F1）· **零改动**
    ├── channel.py                   # 既有（B5F1）· **零改动** —— Channel / LastValue / BinaryOperatorAggregate / EphemeralValue
    ├── mapping.py                   # 既有（B5F1）· **零改动** —— build_channel / build_channels
    └── read.py                      # ★ read_channels / local_read（稀疏读 + fresh 读 + 副本法）
                                     #   —— 只依赖标准库（collections.abc · copy）· 零第三方

tests/
├── conftest.py                      # 既有 · **零改动**
├── contracts/                       # 既有（G1–G13）· **仅**改挂载点文件的标记与元测试（见下）
│   └── test_contract_regressions.py # ★ GATE-MOUNT: C4 · status=not-landed → landed
│                                    #   + 一条**只做路径扫描**的元测试（MUST NOT import freegraph.* · G2）
├── facade/                          # 既有（G14–G20）· **零改动**
├── gates/                           # 既有（G21–G30）· **零改动**
├── runtime/                         # 本 feature 的测试（与既有 `tests/runtime/` **同目录**）
│   ├── __init__.py                  # 既有（B4F1）· **零改动**
│   ├── conftest.py                  # 既有（B4F1）· **零改动** —— **复用** `run_in_subprocess` 夹具
│   ├── test_read_c4_sparse_state.py # ★ **C4 独立回归测试**（否定式断言 · FR-012 · 判据 A1 / A2）
│   ├── test_read_semantics.py       # ★ 稀疏读的语义（普通 dict / key 集合 / None 值 / skip_empty 两分支）
│   ├── test_read_fresh.py           # ★ fresh 读（视图含写入 / 零污染 / 合并语义 / 未知 key 抛错）
│   ├── test_read_purity.py          # ★ 纯净性（导入无副作用 / 零环境变量 / 零出站 / 副本无 __dict__）
│   ├── test_read_contract.py        # ★ 契约守卫（**解析** contracts/read-contract.md 的 I-1…I-11 + 收敛 / 依赖隔离 / 冻结面）
│   └── ...                          # 既有（B4F1 / B5F1）· **零改动**
│                                    #   ⚠️ **例外**：`test_parse_contract.py` 的**两条依赖判据**
│                                    #   MUST 按登记项 **R-3** **拆分取样范围**（FR-037 · 裁定 27 · T041 / T042）
└── differential/                    # ★ 差分测试夹具（**测试侧** · MUST NOT 进 src/）
    ├── __init__.py                  # ★
    ├── conftest.py                  # ★ `langgraph` 缺席 ⇒ skip 的夹具（pytest.importorskip）
    ├── spec_builder.py              # ★ 图规格：字段描述 → 动态构造 TypedDict（**一个**）· 前置校验
    ├── driver.py                    # ★ freegraph 侧的**规格驱动器**（只用 B5F1 通道 + B5F2 读取层）
    ├── runner.py                    # ★ 两侧执行 + **三项投影**归一化 + 逐字段比对 + 判定记录
    └── test_differential.py         # ★ 差分用例（混合 schema · 三项投影 · 缺席 skip）

harness/verification/B5F2/
└── manual-verification.md           # ★ 人工验证记录（五段式 + 来源覆盖表 · 差分判定含具体字段）

.github/workflows/ci.yml             # ★ **新增步骤 5.6**（`uv pip install --python .venv --group differential`）
                                      #   （登记项 R-2 · 方案 α′）⇒ **步骤 5.5 一字不动** · 7 个作业形状
                                      #   与 required check 名**零变更**
pyproject.toml                       # ★ [dependency-groups] differential = ["langgraph==1.2.11"]
                                      #   ⇒ **不进**发行元数据（PEP 735）

# ── 本 feature **改到**的既有冻结面 / 上位文档（**三处例外** · 登记项 R-2 / R-3 / R-4） ──
specs/b3f1-scaffold-ci-gates/contracts/ci-matrix.md
                                      # ★ R-2 · 步骤 5.6 行 + 位置约束 + §2.1 修订记录（T036）
specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md
                                      # ★ R-4 · G29 判定 3 的**两态 + `landed` 语义**（T048）
harness/scripts/gates/gate_G29_contract_carrier.py
                                      # ★ R-4 · **docstring** 与契约文本同步（**判定代码不变** · T048）
harness/proposals/立项书.md
                                      # ★ 裁定 33 ③ · §4.2 S5 / §5.2 B5F2 行 / §9.2 落点（**只接线** · T047）
```

**Structure Decision**:

- **落 `src/freegraph/runtime/read.py`** —— 层注册表**已登记** `src/freegraph/runtime/` 为 **L2**
  ⇒ **层注册表零改动**（spec FR-021）；本 feature 是该目录的**第三个**实现 feature
  （B4F1 解析层 · B5F1 通道层 · **B5F2 读取层**）。
- **读取层**与**通道层**（`channel.py` / `mapping.py`）**物理分离** —— 理由：
  ① B5F1 的 `Channel` 抽象是**冻结面**（四个操作 + 四个属性 + 构造签名逐字冻结）⇒
  读取层 MUST NOT 改它 ⇒ 分离 ⇒ 冻结面零变更；
  ② 读取层**只依赖** `channel.py` 的**四个操作 + 一个判定**（`update` / `get` / `is_available` /
  `copy` 语义）⇒ 依赖方向单一（L2 内 `read` → `channel`）⇒ **无环**；
  ③ 「读取原语**不经由图执行**直接测试」（spec §8）⇒ 读取层必须能**独立 import 与测试** ⇒ 分离更易。
  ⚠️ `src/freegraph/runtime/__init__.py` **MUST NOT** 被 `src/freegraph/__init__.py` import
  ⇒ 顶层包惰性（G1 / L-1）**恒成立**。
- **C4 的断言住 `tests/runtime/`，挂载点文件只留「标记 + 元测试」** —— 理由：**门禁 G2** 的
  内部 import 档扫描 `tests/contracts/**` ⇒ 那里**禁止** import `freegraph.*`
  ⇒ 断言若住在挂载点文件里**必然**让 CI 的 G2 变红（裁定 20 · FR-013 / FR-032）。
  ⇒ 门禁 **G29** ③ 只解析**标记**、**不要求**断言本体住在该文件 ⇒ 两者**同时兼容**。
- **差分夹具落 `tests/differential/`（测试侧）** —— 理由：① 规格驱动器 MUST NOT 含调度逻辑
  （**B7F1** 的范围）⇒ 它是**测试侧**的替身 ⇒ MUST NOT 进 `src/`（spec 裁定 6）；
  ② `pyproject.toml` 的 sdist `exclude` **已含** `/tests` ⇒ 夹具**不进发行包**；
  ③ `pytest` 的 `testpaths = ["tests"]` ⇒ **CI 零改动**即被收集。
- **三份契约**（`read-contract.md` / `upstream-parity.md` / `differential-fixture.md`）——
  沿用 **B3F1 的层注册表先例** + **B5F1 的契约先例**（机器可读 Markdown + `<!-- authority: yes -->` 标记）：
  ① `read-contract.md` 与 `differential-fixture.md` 是**判据**（**唯一权威**）；
  ② `upstream-parity.md` 是**证据表**（逐条 `路径:行号` + 实测基线）⇒ **MUST NOT** 被测试解析
  （测试**直接断言行为** ⇒ 避免「判据与实现同源 ⇒ 自证」）。

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **宪法「质量门禁 3 / 4 / 5」的四部分在本 feature 物理不可达成**（C4 的**节点边界**断言 · C8 回归 · fake 模型轮 · 真实模型轮） | 四者**共享同一根因**：它们都要求**调度循环 / 完整内核运行时**存在，而 B5F2 按立项书 §5.2 只交付**读取层**（调度 = B7F1 · 路由 = B8F1 · 编译执行 = B7F2 / B7F3）⇒ **任何 spec 设计都无法在本 feature 满足这四条** ⇒ 依宪法 **v1.6.0** 的窄口径通则处置（偏离登记 + 发起者追认 + 具名承接方） | **替代方案 A：硬写进 CI**（让验收脚本在「无图可跑」时判通过而不登记）⇒ **静默稀释宪法** + 门禁语义被扭曲 ⇒ **不可行**。<br>**替代方案 B：写一条永久红的 CI** ⇒ 违反「feature 必须能独立通过门禁」· PR-4 ⇒ **不可行**。<br>**替代方案 C：改宪法正文** ⇒ 违反「**MUST NOT** 以本条删改宪法正文」⇒ **不可行**。<br>**替代方案 D：把 B5F2 扩成「读取 + 调度」** ⇒ 越过立项书的 feature 边界 ⇒ **不可行**。<br>**采用的处置**：**偏离登记（R-1）+ 发起者追认（`tasks.md` 的阻断合入任务）+ 承接条款已在目标 feature 的提示词初稿中既有**（B7F1 · B8F1 · B7F2 / B7F3 · B25F1）⇒ **红线判据一律不放宽**。 |
| **CI 矩阵契约（冻结面）需修订**：为满足 FR-025「差分夹具 MUST 有专门 CI 步骤真实执行」 | 差分夹具在**无上游**的环境里必然 **skip** ⇒ 若不修订契约，SC-014「真实执行次数 ≥ 1」**永不可达** ⇒ 差分证据退化为「主张」⇒ 与本 feature 的**全部价值**相悖 | **替代方案 A：新增第 8 个 job** ⇒ 改 §1 的矩阵形状 **+** §4.1 的 required check 名 **+** 分支保护配置 ⇒ 分支保护按 job 名精确匹配 ⇒ 修订面最大、风险最高 ⇒ **不选**（且与 spec **裁定 25** 的约束句直接冲突）。<br>**替代方案 B：不修订契约（永远 skip）** ⇒ **假绿** ⇒ **不可行**。<br>**替代方案 C：把 `langgraph` 装进既有的 `--group dev`** ⇒ **基础 CI 的 7 个作业本来就装 dev 组** ⇒ 在 **CI 侧**与方案 α′ 等价，但会让**开发者本地**也常驻上游 ⇒ **本地开发不必常驻上游** ⇒ **不选**。<br>**采用的处置**：**方案 α′** —— 在**既有作业内新增一个独立步骤**（**步骤 5.6** · `uv pip install --python .venv --group differential`）⇒ **步骤 5.5 一字不动**（保持「只做 v2.0 extras 预验证」的**单一语义**）⇒ §1 的 7 作业形状与 §4.1 的 7 个 required check 名**零变更** ⇒ **分支保护零变更** ⇒ 落地形态 = **既有作业内的专门「步骤」**（**裁定 25**）。 |
| **既有 B4F1 的两条依赖判据需拆分取样范围**（`test_dependency_declarations_contain_no_upstream_package` · `test_ci_workflow_never_installs_langgraph`） | 本 feature 引入**第一个**上游 dev / test 依赖 ⇒ 原判据把**开发工具链**（`[dependency-groups]`）与**发行面**混为一谈 ⇒ 必然变红 ⇒ 若不显式处置，执行者极可能「删断言 / 放宽断言」⇒ **原判据的覆盖面与红线作用域不一致**（**取样范围 bug 修复** · 裁定 27） | **替代方案 A：删断言 / 放宽断言** ⇒ 稀释判据 ⇒ **不可行**。<br>**替代方案 B：把 `langgraph` 放进 `[project].dependencies` 以「让它合法」** ⇒ 破发行依赖闭包为空集（G3 / G21 / SC-008）⇒ **不可行**。<br>**替代方案 C：放弃上游依赖组（差分夹具改为「有上游才跑」）** ⇒ SC-014「真实执行 ≥ 1 次」不可达成 ⇒ 差分证据退化为主张 ⇒ 与本 feature 的**全部价值**相悖 ⇒ **不可行**。<br>**采用的处置**：**登记项 R-3** —— **拆分取样范围**（发行面部分**逐字保留** + `[dependency-groups]` 改**正向枚举**：「上游只许出现在 `differential` 组」）+ **新增**一条 CI 正向断言（上游安装**只许**经 `--group differential`）⇒ **原断言一条未放宽、且覆盖面被拆分而非削减**（FR-037 / SC-031 · 裁定 27）⇒ 修订在本 feature 内落地（T041 / T042）+ **指名承接条款**写入 `harness/features/B4F1_schema解析与归约器提取.md`（宪法 v1.8.0「只接线」）+ 发起者追认（T043）⇒ ⚠️ **定性 = 取样范围 bug 修复 ⇒ 无需宪法修订**（不属 v1.6.0 的门禁偏离 · 不属 v1.8.0 的跨 feature 承接）。 |
| **`skip_empty=False` 的口径与上游分叉**（freegraph **抛 `EmptyChannelError`**；上游**以 `None` 填充**） | 上游的「以 `None` 填充」会把「**无值**」与「**值为 `None`**」**重新混判** ⇒ 直接违反 **B5F1 裁定 5** 冻结的「有值 / 无值严格可分」；且该分支**上游全包从未使用**（`skip_empty` 仅 2 处）⇒ **无实际等价性损失** | **替代方案 A：照抄上游（以 `None` 填充）** ⇒ 与 freegraph 自身的通道层**语义打架**（B5F1 的 `EmptyChannelError` 正是为区分二者而设）⇒ **不可行**。<br>**替代方案 B：删掉 `skip_empty=False` 这个模式** ⇒ 少一个分支，但上游**有** ⇒ 将来对齐时仍要加 ⇒ **不选**。<br>**采用的处置**：保留**抛错**口径 + 在 `upstream-parity.md` 的 **P-04** 登记为「**不可观察**的语义差异」+ **DR-1**（上游若开始使用该分支 ⇒ 触发重新评估）。 |
| **读取层的形状与上游不同**（无 `select` 参数 · 返回类型**恒为 `dict`** · `local_read` 签名简化 · 无 `managed` 语义） | freegraph 的读取层**只服务一个消费者**（B7F1 的节点入参组装 + B8F1 的路由读）⇒ 「读全部 · 返回 dict」的**恒定形状**比上游的「按 select 择读 · 返回 `dict \| Any`」**更可判定**；且 `managed` 值**不在** freegraph 的契约面内（C1–C27 无此条目） | **替代方案 A：照抄上游的 `select` 双形态** ⇒ 返回类型随入参而变 ⇒ 下游每次都要判 `isinstance` ⇒ **可判定性下降**；且 freegraph **没有** `select` 的使用场景（节点入参 = 全部 key）。<br>**替代方案 B：照抄上游的 `local_read` 签名**（含 `scratchpad` / `managed` / `task`）⇒ 把 freegraph **不实现**的 managed 语义引进内核 ⇒ 违反 C1–C27 的契约边界（原则 VII）⇒ **不可行**。<br>**采用的处置**：freegraph 的**简化签名** + 在 **P-02 / P-05 / P-11** 登记为**形状差异**（**非**语义差异）⇒ **B8F1** MUST NOT 假设 managed 语义（**DR-3**）。 |
| **副本法用标准库 `copy.copy`**（上游用 `BaseChannel.copy()` = `from_checkpoint(checkpoint())`） | B5F1 的 `Channel` 抽象是**冻结面**（四个操作 + 四个属性逐字冻结）⇒ **MUST NOT** 加 `copy()` 方法 ⇒ 只能走标准库；实测（research **D-09**）`copy.copy` 对 `__slots__` 通道**可行**（副本**无** `__dict__` · 归约器**同一引用** · 值**独立**） | **替代方案 A：给 `Channel` 加 `copy()`**（上游同款）⇒ 改**冻结面** ⇒ 连带改 B5F1 的契约文件与 parity 表 ⇒ 代价远超收益 ⇒ **不可行**。<br>**替代方案 B：深拷贝**（保证「就地修改型归约器」也不污染）⇒ 破坏用户对象身份（spec FR-005）且对不可拷贝对象**会失败**；且**上游同样浅共享**（`checkpoint()` 返回同一对象）⇒ **两侧同构**，不构成等价性缺口。<br>**采用的处置**：`copy.copy` + 在 `read-contract.md` §3.3 **写明**该已知面（**DR-4**）。<br>⚠️ **第四轮增补（裁定 29）**：「**就地修改型**归约器 ⇒ 改写**值对象**」属**已知面** ⇒ **不修**（深拷贝会破坏 FR-005 · 与上游分叉）⇒ **不计入**「零污染」判据（该判据的作用域 = **绑定与可用性判定**：`is_available()` 的结果 + `get()` 的取值）⇒ **MUST** 在 Edge Cases 与人工验证记录中**显式登记**。 |
| **差分夹具的「未知 key 写入」场景被排除在比对之外** | 上游**静默丢弃**未知 key、freegraph **显式失败** ⇒ 两侧**不等价地失败** ⇒ 若纳入比对 ⇒ 稳定报**假差异** ⇒ 会逼维护者放宽判据 ⇒ 反而掩盖真实差异 | **替代方案 A：把 freegraph 改为静默丢弃**（对齐上游）⇒ 用户的拼写错误**无声消失** ⇒ 违反 B5F1「非法输入 MUST 显式失败」的既有立场 ⇒ **不可行**。<br>**替代方案 B：把该场景纳入比对并接受「不等价」** ⇒ 差分夹具**永远红** ⇒ 门禁失效。<br>**采用的处置**：夹具侧**前置校验**拦截（`differential-fixture.md` §5）+ 该场景由 freegraph 的**单元测试独占断言**（**DR-2**）。 |
| **宪法 v1.8.0「跨 feature 承接的接线通则」**（本 feature 的**首次适用**） | B5F2 立的跨 feature 义务（C4 断言推进到节点边界 · 夹具接口预留条件边字段）若只写在 B5F2 的 spec 里 ⇒ **下一棒看不见** ⇒ 义务失联 ⇒ 而「义务失联」的代价是**静默**的（C4 的防线停在读取层）⇒ 必须有**强制**的交接机制 | **替代方案 A：只在 B5F2 的 spec 里写「B7F1 请承接」** ⇒ 无强制力 ⇒ 本 feature 的实测（**第一版 spec 就写错了 C4 断言的落点**）已证明其**不可靠**。<br>**替代方案 B：把规则写进宪法但**不限作用域**（凡有依赖就改后续提示词）⇒ 每个 feature 回头改 5 份别人的文档 ⇒ 噪音与 review 成本剧增 ⇒ **不选**。<br>**采用的处置**：宪法 **v1.8.0**（2026-11-09 发起者批准）—— 触发条件**收窄**为「**指名**下一棒的**跨 feature 义务**」，并配**四条红线**（不越界实现 / 不新增门禁编号 / 不放宽判据 / 只做最小改动）⇒ 与本 feature 的**三条**义务**精确对应**（B7F1 · B8F1 · B25F1）。 |
| **fake 模型注入在本 feature 的范围被收窄**（立项书 §9.2「fake 模型的注入机制」的落点**含 B5F2**） | 立项书 §4.2 **S5** 写「**差分夹具与 fake 轮共用同一套注入机制**」，而 §9.2 的落点表明写「fake 注入 + 断言点写入 §5.2 **B25F1** 小目标（CI 轮）与 §5.2 **B5F2 / B8F1**（差分夹具）」⇒ 本 feature 的差分夹具若**不**给出处置 ⇒ **与立项书不对齐**；但真在本 feature 实现 fake 注入 ⇒ 会让 `differential` 依赖组带上 `langchain` + `langsmith` + `pydantic` ⇒ 与立项书 §9.1「**避免矩阵成本爆炸**」相悖，且把 **B25F1 的主体提前实现**（越界 · FR-024） | **替代方案 A：本 feature 直接实现 fake 注入** ⇒ 依赖组膨胀 + 越界 + 提前实现 B25F1 的主体 ⇒ **不可行**。<br>**替代方案 B：删掉立项书的落点**（改立项书正文）⇒ 超出本 feature 的范围 ⇒ **不可行**。<br>**采用的处置**：**预留「模型工厂」钩子 + 指名承接条款归 B25F1**（spec **裁定 26** · FR-036 · SC-030）—— 图规格 MUST **预留**该字段（本 feature **恒空** ⇒ 非空即**显式失败**）⇒ 夹具接口对 **B25F1** 稳定；承接条款按宪法 **v1.8.0**「跨 feature 承接的接线通则」写入 `harness/features/B25F1_双跑验收与迁移说明.md`（**只接线** · 逐条最小改动）⇒ **只登记、不改判据**（research **DR-5**）。<br>⚠️ **（2026-11-10 · 分析轮第二轮 · 裁定 33 ③）**：立项书 §9.2 落点 / §4.2 S5 / §5.2 B5F2 行**已回改**（「**接口与钩子**归 B5F2 / **注入实现**归 B25F1」· tasks **T047**）⇒ 上位文档与 feature 规格**重新一致** ⇒ 上条「替代方案 B：删掉立项书的落点 ⇒ 超出本 feature 的范围」的结论**不变**（修订上位文档**只接线、不删条目**）。 |
| **G29 的冻结契约需最小修订**（`architecture-gates.md` G29 判定 3 + `gate_G29` docstring） | `FR-013`（C4 的 `status` 翻 `landed`）与 G29 判定 3 的「MUST 明确标记为『未落地』」**直接冲突**，且与 `FR-026`（门禁判定口径一字不动）**自相矛盾**；`landed` 的**语义**未定义 ⇒ 机器可读信号**强于**实际防线位置（C4 的节点边界断言归 B7F1） | **替代方案 A：把 C4 保持 `not-landed`、推迟到 B7F1 才翻** ⇒ 本 feature 的 C4 契约门禁缺口不解锁（与裁定 8 / 20 的前提相悖）⇒ **不选**。<br>**替代方案 B：改门禁判定代码**（新增第三态 / 改判定）⇒ 触碰冻结面的**实现** ⇒ **零必要**（代码早已接受两态）⇒ **不选**。<br>**采用的处置**：**登记项 R-4** —— **只改契约文本 + 脚本 docstring**（**判定代码一行未改**）⇒ 把「单态快照」改成「**两态 + `landed` 语义定义**」⇒ **零新判据、零放宽**· **门禁编号 G1–G30 与宪法正文一字不动**（tasks **T048**）+ **发起者追认**（tasks **T049** · 阻断合入）。 |
| **两个稀疏入口的等价关系此前未定义**（`read_channels` 与 `local_read(fresh=False)`） | 二者是**同一稀疏语义的两个入口**，而契约**只**分别定义、**未定义**二者的等价关系（tasks T024 原文只写「口径一致」）⇒ `FR-001` / `SC-012` 只约束「实现点数 == 1」⇒ **语义层**留有分叉空间 ⇒ 「稀疏读」可能两处实现、彼此漂移（正是 FR-001 要防的失败模式） | **替代方案 A：删掉 `local_read` 的 `fresh=False` 分支** ⇒ 与上游 `local_read(fresh=False)` 的形状差异扩大、且需改 `read-contract.md` §3.1 与 FR-008 ⇒ **不选**。<br>**替代方案 B：只写「口径一致」**（不要求逐字相等）⇒ 仍留分叉空间 ⇒ **不可行**。<br>**采用的处置**：**新增 `FR-038` / `SC-033`** —— 两个入口的结果 **MUST 逐字相等**（key 集合 + key 顺序 + 逐 key 值同一对象）⇒ **可判定**且**零新增实现点**（同一模块内共享实现）（tasks **T013**）。 |
