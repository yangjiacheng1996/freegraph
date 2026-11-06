# Implementation Plan: 5 个协议（4 类可插拔协议 + `CompiledGraph`）+ 5 个纯数据类（契约层协议面冻结）

**Branch**: `b2f1-contracts-protocols` | **Date**: 2026-11-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b2f1-contracts-protocols/spec.md`

**feature ID**: `B2F1`（M0 地基 · 31 个 feature 中的第 2 个）

---

## Summary

在 B1F1 交付的契约层地基（`src/freegraph/contracts/`）之上，**一次性把 freegraph 的全部
对外协议定义齐**，并落成「接口契约冻结」：

- **5 个协议**（全部 `typing.Protocol` + `runtime_checkable`、**纯抽象无默认实现**）：
  `NodeFunc`（节点函数）/ `Checkpointer`（检查点）/ `TraceSink`（可观测接收端）/
  `Store`（长期存储）/ `CompiledGraph`（编译产物能力面）；
- **5 个纯数据类**：`Graph` / `Node` / `Edge`（图结构，**自有重写**，不复用
  `langchain_core.runnables.graph`）/ `Span`（可观测事件）/ `TraceQuery`（C27 查询请求）。

本 feature **不交付任何运行时行为**：协议全是抽象方法，没有一个方法体；数据类只做
「冻结 + 缺省归一 + 浅拷贝」，**零构造期值校验**。它交付的是**此后 30 个 feature
全部要引用的类型契约**，且该层**不依赖任何 freegraph 内部模块**（ARCH-2），使跨仓库
姊妹项目 freechain 能只取契约而不拖进运行时。

技术上，全部实现由三个标准库机制承载：`typing` 的 `Protocol` / `runtime_checkable`
（3.8+）、`dataclasses` 的**冻结数据类**（3.7+）、`ast` + `subprocess` 的架构断言。
**基础安装零第三方运行时依赖**（`dependencies = []`，沿用 B1F1 与宪法 v1.2.0 的结论）。

**冻结面（后续 30 个 feature 引用、不可轻改）**——完整清单与 C1–C27 对照表以
**`specs/b2f1-contracts-protocols/contracts/public-api.md` 为唯一权威**（声明取代
B1F1 的同名文件，后者作为历史快照保留）：

| 冻结项 | 内容 |
|---|---|
| 公开符号面 | **恰 18 个** = B1F1 的 8 个 + 本 feature 新增 10 个（`NodeFunc` / `Checkpointer` / `TraceSink` / `Store` / `CompiledGraph` / `Graph` / `Node` / `Edge` / `Span` / `TraceQuery`）——**该数字的唯一权威 = `contracts/public-api.md` §0**；下游文档**只引用、不另写**（防多处抄写漂移） |
| 协议方法集 | `NodeFunc.__call__` / `Checkpointer` 六方法 / `TraceSink` 三方法 / `Store` 六方法 / `CompiledGraph` 六方法 —— **恰为**，不多不少，**纯抽象**；**以集合相等判定**（**成员定义顺序不作判据**——`Protocol.__protocol_attrs__` 是 `set`） |
| 图结构字段 | `Graph.nodes/edges`（不可变元组）/ `Node.id`+`name`+`metadata` / `Edge.source`+`target`+`conditional`+`condition` |
| span 字段 | 11 字段（`id`/`name`/`attributes`/`parent`/`start_time`/`end_time`/`context` + **必带四项** `thread_id`/`run_id`/`node`/`checkpoint_id`） |
| 查询请求字段 | `TraceQuery` 5 字段（`run_id`/`thread_id`/`node`/`start_time`/`end_time`），全可空、可组合 |
| 相等 / 哈希 | **五个**数据类**字段级相等**；其中**四个**（`Node` / `Edge` / `Graph` / `Span`）**统一不可哈希**（含 `Edge`——需显式 `__hash__ = None`，见 `data-model.md` §4.3）；`TraceQuery` **有意可哈希**（五字段全为标量、无映射字段） |
| span 生命周期 | `Span` **不可变**；开始回调收「`end_time` 为空」实例，结束回调收**同 `id`、已填 `end_time` 的新实例**，按 `id` 配对 |
| C1–C27 对照 | 逐条「已冻结 / 挂起」（**「状态」列为二态**；D11 的 4 条修订在**独立的「修订」列**标注，**正交**、不计入二态统计）——见 `contracts/public-api.md` §2 |

---

## Technical Context

**Language/Version**: Python ≥ 3.11（`pyproject.toml` 的 `requires-python = ">=3.11"`；本机开发环境实测 CPython **3.12.3**，隔离验收另在 CPython 3.11.x 上实测——沿用 B1F1 的双档口径）。
**typing 构件上限 = 3.11**（宪法「运行时环境基线」v1.3.0）：MUST NOT 使用 `TypeAliasType`(3.12) / `override`(3.12) / `ReadOnly`(3.13) / `TypeIs`(3.13) 或 PEP 695 `type` 语句——由**架构门禁 G9** 静态断言把关。
本 feature 用到的 typing 构件**全部 ≤ 3.11**：`Protocol` / `runtime_checkable`（3.8+）、`TypeAlias`（3.10）、`Literal`（3.8）、`ClassVar`（3.8）、`Mapping` / `Sequence` / `Iterator`（3.9）、`dataclass`（3.7）——**无需** `typing_extensions` 兜底。

**Primary Dependencies**: **无**（基础安装零第三方运行时依赖，`dependencies = []` 沿用现状，本 feature **不改** `pyproject.toml` 的依赖声明）。
开发期工具（**不进发行包**）：`pytest`（实测 7.4.4）+ `mypy`（静态类型检查，**可选**——本机未安装时相关用例 `skip`，口径与 G3 依赖闭包「需隔离环境才真跑」一致）。

**Storage**: N/A —— 本 feature 无持久化。`Span` / `TraceQuery` 仅为**类型定义**，其落盘与查询由 B20F1 / B20F2 实现。

**Testing**: pytest（开发期实测 7.4.4）+ 标准库 `ast` / `subprocess` / `typing`（`get_type_hints`）/ `dataclasses`。
架构断言（零内部 import、零第三方 import、依赖闭包、公开符号面、协议纯抽象）**必须在子进程中执行**——测试进程自身已导入 pytest，无法用同进程 `sys.modules` 判定（沿用 B1F1 的判定口径）。

**Target Platform**: 任意 CPython 3.11+ 平台（Linux / macOS / Windows）。本 feature 无平台特定代码、无 C 扩展、无文件 IO 契约、无网络。

**Project Type**: library（Python 库；发行名 = 导入名 = `freegraph`，契约层为**主发行包内的子模块**，不拆独立发行包 —— D1 已拍板）。

**Performance Goals**: 隔离 venv 中 `python -c "import freegraph.contracts"` 的**墙钟 < 300 ms**（含解释器冷启动）——沿用 B1F1 的阈值（基线实测 154 ms / 3.12.3），新增三个模块后仍须在预算内。
协议**只被定义、不被执行**——本 feature 无运行时路径，**无**吞吐 / 延迟指标。

**Constraints**:
- **零**第三方运行时依赖（基础安装闭包 MUST 为空集）；**不得**引入 pydantic 等可选依赖（避免把 extras 的依赖拉成必装）
- **typing 构件上限 = 3.11**（见上）
- 契约层**零** freegraph 内部模块 import（ARCH-2 / FR-008）；包**内部**相对导入合法（B1F1 口径）
- 协议**纯抽象**：MUST NOT 提供任何默认实现（默认实现会让「只声明部分方法」的假实现**静默通过**结构化子类型判定，掩盖缺实现——FR-007）
- 协议**不提供基类继承链**（架构纪律 PD-1）——扩展靠组合或结构化子类型判定
- 数据类**零构造期值校验**（只做类型注解 + 冻结 + 缺省归一 + 浅拷贝）——沿用 B1F1 的校验边界口径
- **零出站**、**不读任何环境变量**（FR-011）
- **零出站 / 零环境变量**亦适用于测试夹具（外部实现夹具不得 import 网络库）
- 每个新源文件携带署名头（FR-015 / 宪法原则 X）
- 发行产物须带 `py.typed`（沿用 B1F1 现状，顶层一个即覆盖全部子包）

**Scale/Scope**（**实测值已回填 · 2026-11-06**）：实现 ≈ **536 行**（立项书 §5.2 估算 **480 行**
⇒ **+12%**，偏差在可接受区间）——
`protocols.py`（5 协议 · 242 行）+ `graph.py`（3 类 · 130 行）+ `trace.py`（2 类 · 126 行）+
`contracts/__init__.py` 扩充（38 行）；
测试 ≈ **2,053 行**（立项书估算 **340 行** ⇒ **+504%**，**显著超出**——与「风险」第 1 条的预判一致）——
新增 `test_protocols.py`（382）+ `test_graph.py`（221）+ `test_span.py`（257）+
`fixtures/__init__.py`（13）+ `fixtures/external_impl.py`（248）= **1,121 行**，
**外加** `test_architecture.py` 由 972 行扩到 **1,904 行**（**+932 行** · 13 条门禁 + 各自的自检）；
**用例数 284**（**278 passed + 6 skipped** · 本机未装 freegraph / mypy）；
文档 ≈ **3,837 行**（spec 881 + plan 399 + tasks 438 + research 406 + data-model 340 +
quickstart 447 + public-api 261 + architecture-gates 254 + requirements 清单 59 +
人工验证记录 352）。
> **行数口径（避免与立项书 §5.2 打架）**：立项书 §5.2 的 B2F1「**820 行**」= 实现 480 + 测试 340
> （**不含文档行数**）；本 feature 的**文档产出另计**。
> **实测**：实现 536 + 测试 2,053 = **2,589 行**（立项书估 820 ⇒ **+216%**），
> **其中测试的超出是主因**（13 条门禁 × 各自的门禁自检 + 21 条成功标准的逐条断言）。
> **登记（不改立项书）**：测试/实现的行数比 ≈ **3.8 : 1**，远超「契约层的价值在断言密度」的
> 预期口径——本 feature 恰是**契约冻结面**本身，故门禁密度天然最高；后续 feature 的估算
> 宜按「实现 1 : 测试 1.5~2」取值，而非 1 : 0.7。
> 立项书的**总口径（30,600 行 / 93 人日）不因本 feature 的偏差调整**——文档行数不进其统计口径，
> 且测试行数超出**不改变交付面**（仍是 5 个协议 + 5 个纯数据类 + 13 条门禁）。
公开符号面 **18 个**（新增 10 个）；协议 **5 个**；纯数据类 **5 个**。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 要求 | 本 feature 的满足方式 | 判定 |
|---|---|---|---|
| **原则 I** 零 LangSmith 依赖 | 依赖树无 `langsmith` / `langchain*` / `langgraph*`；不读 `LANGSMITH_*` / `LANGCHAIN_*`；不向 `*.langchain.com` / `mermaid.ink` 出站 | FR-011（**零**第三方运行时依赖，闭包为空集）+ FR-011（零环境变量、零出站）；SC-002 断言依赖闭包为空；门禁 G4 扫描源码无 `os.environ` / `os.getenv`；**图结构类型自有重写**（不复用 `langchain_core.runnables.graph`——复用即把 `langchain-core` → `langsmith` 拖回依赖树，直接破红线） | ✅ 通过 |
| **原则 II** 内核纯净 | 核心层不 import langchain；状态 schema 用标准 `TypedDict`，**不得自带并行状态类型体系** | FR-008（契约层零内部 import + 零 `langchain*` import）；FR-001 的 `NodeFunc` 入参类型直接复用 B1F1 的 `StateDict`（= `dict[str, Any]` 别名，**不新造状态类型体系**）；门禁 G2 | ✅ 通过（**C4 / C8 回归测试子项本 feature 不适用**——契约层无运行时，C4 稀疏状态与 C8 条件边 fresh 读的回归测试分别归 **B5F2** / **B8F1**，已显式记录、非忽略） |
| **原则 III** 验收契约优先 | `harness/demo/target.py` 原样可跑 | 本 feature **不修改** `target.py`；它当前依赖尚未交付的 `freegraph.graph` 门面（**B2F2**）与运行时（**B7F3**），故「原样可跑」在本 feature **不适用**——不得为凑这条门禁而提前交付门面 | ✅ 不适用（记录在案） |
| **原则 IV** 可诊断性是一等功能 | 失败可被上层结构化读取，而非只能解析日志字符串 | FR-003 冻结 `TraceSink` 的**三个方法**（`on_span_start` / `on_span_end` / `current_span`）与 `current_span()` 的**空值语义**（不抛异常）；FR-010 的 span **必带四项**让 trace 可按会话 / 运行 / 节点 / 检查点对齐——可诊断性的**协议面**在本 feature 落定 | ✅ 通过 |
| **原则 V** 人工验收是最终验收标准 | 本 feature 结束须有人工验证记录（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）；MVP 验收基线须 fake 模型 + 真实模型**各跑一遍** | `quickstart.md` 给出可复制的验证步骤；人工记录骨架落 `harness/verification/B2F1/manual-verification.md`（**由人执行后填入实测输出**）。**「双跑」子项在本 feature 不适用**（无运行时、无模型调用；C4 / C8 的回归测试分别归 B5F2 / B8F1），已显式记录、非忽略 | ✅ 通过（双跑子项不适用） |
| **原则 VI** 规格驱动开发 | 有 proposal 与 spec，再进 tasks 与实现 | 本 feature：spec（`specs/b2f1-contracts-protocols/spec.md`，含 **13** 条澄清决策）→ 本 plan → tasks → 实现 | ✅ 通过 |
| **原则 VII** 职责边界与内核契约 | 不做 freechain 能力；契约清单以 Q8 **C1–C27** 为唯一权威 | ① **不实现**任何协议的方法体（行为分别归 B14F1 / B15F1 / B19F1 / B20F1 / B20F2）；② **不实现** `Store`（C20 仍冻结，v1 无实现，B17 已砍）；③ 契约清单**逐条对照**落 `contracts/public-api.md` §2（C1–C27 全 27 条，**MUST NOT 擅自增删条目**）；④ D11 的三项修订（C27 增补 / C23 字段约定 / C22 标识约定）**全部落地**（FR-009 / FR-010 / SC-005）；⑤ 不做 LangChain 层能力 | ✅ 通过 |
| **原则 VIII** 证据与术语纪律 | 事实性结论带来源标记；术语准确 | `research.md` 每条决策标注依据（Q8 §3.4 / §3.4.1 / 立项书 §5.3.1 / LangGraph 1.2.11 与 langchain-core 1.6.3 源码核实路径:行号）；术语统一：「节点函数协议 = `NodeFunc`」「图节点元素 = `Node`」「会话标识 = `thread_id`」「单次运行标识 = `run_id`」 | ✅ 通过 |
| **原则 IX** 依赖许可证与商标红线 | 无 Elastic-2.0 / AGPL / SSPL；API 同名对齐不得暗示 affiliation | **零**第三方运行时依赖（闭包为空集 ⇒ 许可证白名单校验恒通过）；图结构类型**同名但自有实现**（`Graph` / `Node` / `Edge`），**不复制上游代码**、不复用其类型——避免「声明兼容」被读成「暗示 affiliation」；兼容矩阵**本 feature 填入本层内容**（新增 10 行的逐符号等价判定；**有上游同名符号者**附来源行号、**无对应者**写「无上游对应」+ 契约条目号 —— FR-017）；`THIRD_PARTY_NOTICES` 因**零**新增第三方依赖**无需新增登记**；**全库**矩阵的补全与定稿归 B24F1 | ✅ 通过 |
| **原则 X** 文档合规义务 | 每个源文件带署名头；发布 `py.typed`；第三方代码入 `THIRD_PARTY_NOTICES`；**API 兼容矩阵 MUST 维护**；**MUST NOT 在清单缺项的情况下宣布该特性完成** | FR-015（署名头，**范围含 `tests/` 下的新增测试文件**与夹具）+ `py.typed` 沿用 B1F1 现状；公开符号面清单落 `contracts/public-api.md`（**唯一权威**，取代 B1F1 同名文件）；**FR-017**：兼容矩阵**本 feature 填入本层内容**（新增 10 行：逐符号等价判定；**有上游同名符号者**附来源行号、**无对应者**写「无上游对应」+ 契约条目号），既有 8 行逐字不动；`THIRD_PARTY_NOTICES` **无需新增登记**（零新增依赖）；**全库**补全与定稿归 B24F1（写入 `contracts/public-api.md` §5 移交表） | ✅ 通过 |

**门禁结论**：无违反项 ⇒ **Complexity Tracking 表不适用**（不填）。

> **已知偏离登记（宪法「质量门禁」第 3 项）** —— 2026-11-06 经发起者裁定，**登记而不改宪法**：
> | 宪法条款 | 本 feature 的处置 | 恢复归属 |
> |---|---|---|
> | **质量门禁第 3 项 · 契约门禁**：`harness/demo/target.py` 原样可跑 | **不适用** —— 本 feature **零运行时、零门面**，脚本依赖的 `freegraph.graph` 门面（B2F2）与运行时（B7F3）尚未交付 | **B2F2 / B7F3** |
> | **质量门禁第 3 项 · 契约门禁**（立项书 §9.1 门禁 3 的**第二个子项**）：「固定脚本为只读基准，**CI 断言其 diff 为空**」 | **不适用** —— 本 feature **不修改** `target.py`，该断言属**流水线工程设施** | **B3F1**（CI 门禁） |
> | **质量门禁第 3 项 · 两条独立回归测试**（C4 稀疏状态 / C8 条件边 fresh 读） | **不适用** —— 二者都是**运行时语义**，契约层无状态、无调度 | **B5F2 / B8F1** |
> | **原则 V · 「MVP 验收基线双跑」**（fake 模型 + 真实模型各一遍） | **不适用** —— 本 feature 无模型调用、无运行时 | B25F1（MVP 验收轮） |
>
> **本偏离不构成对原则 II / III / V 实质要求的弱化**：三条 MUST 的**语义与判定方式均未改动**
> （C4 / C8 的回归要求原样保留在 B5F2 / B8F1；`target.py` 仍是只读基准；双跑要求原样保留），
> 只是**本 feature 尚未触达其适用面**。**本条不触发宪法修订**（宪法文本无需改动）——
> 若后续 feature 出现「有运行时却不做 C4 / C8 回归」的同类情形，再走 §Governance 修订流程。

> **人工验证记录的落盘路径（已对齐 · 宪法 v1.4.1）**：宪法「质量门禁」第 5 项与原则 V 正文
> 曾把人工验证记录的路径写作 `harness/features/<feature>/`，而仓库**实际惯例**是
> `harness/verification/<feature>/`（有明文目录约定见 `harness/verification/README.md`）。
> 本 feature 沿用**仓库惯例**（`harness/verification/B2F1/manual-verification.md`）；
> 该宪法残留（v1.3.0 目录迁移的遗留）已于 **2026-11-06** 经**独立的宪法修订**
> （**v1.4.1 · PATCH**）更正 ⇒ 本 feature 的 spec / plan / tasks 与宪法现已**完全一致**。

> **原则 X 的「填入本层内容」处置**：B1F1 的 FR-016 建立了 `README.md` 兼容矩阵与
> `THIRD_PARTY_NOTICES` 两份活文档，并把口径定为「**填入本层内容**在本 feature、
> **补全与定稿**归 B24F1」。B2F1 新增 10 个公开符号 ⇒ 属「扩展 API 兼容面的特性」，
> 原则 X 要求**本 feature 更新矩阵**。本 feature 的处置：① **FR-017** —— 在兼容矩阵
> **补入本层 10 行**（逐符号：对应上游符号 / 等价程度 / 差异说明；**有上游同名符号者**另附来源行号、**无对应者**写「无上游对应」+ 契约条目号），
> 既有 8 行逐字不动；② `THIRD_PARTY_NOTICES` 因**零**新增第三方依赖**无需新增登记**；
> ③ 门禁 G8 的断言**按符号清单驱动**（期望值从 `contracts/public-api.md` §0 解析）——
> 本 feature 起 G8 由「覆盖 8 个」扩展为「覆盖清单所列的全部符号」，清单变更时断言同步变更；
> **取行范围 = 「## API 兼容矩阵」章节内**（不扫全文）；
> **「行内须含上游来源行号」的子项只对本 feature 新增的 10 行中「**有上游同名符号**者」成立**
> （`NodeFunc` / `TraceSink` / `Span` / `TraceQuery` **无上游同名符号** ⇒ 该 4 行写
> 「无上游对应」+ 契约条目号，**MUST NOT** 硬凑行号）——**且矩阵保持 4 列，来源行号写进
> 该行的「差异说明」单元格末尾**（既有 8 行逐字不动 ⇒ 不可新增列）——
> 既有 8 行按 FR-017 **逐字不动**
> （其上游来源集中在矩阵章节的「证据来源」小节，见 G8 判据），二者不冲突；
> ④ 全库矩阵的**补全与定稿**仍归 B24F1（登记在 `contracts/public-api.md` §5）。

---

## Project Structure

### Documentation (this feature)

```text
specs/b2f1-contracts-protocols/
├── plan.md                  # 本文件（/speckit.plan 输出）
├── spec.md                  # 特性规格（/speckit.specify + 两轮 clarify 的产出 · 13 条澄清）
├── research.md              # Phase 0 输出：设计决策台账（**20 条决策 D-01…D-20** + 上游证据 + **13 条**挂起项交接表）
├── data-model.md            # Phase 1 输出：5 个协议 + 5 个数据类的字段与语义
├── quickstart.md            # Phase 1 输出：可运行的验收指南
├── contracts/
│   ├── public-api.md        # ★ 唯一权威：18 符号清单 + C1–C27 冻结对照表 + 冻结记录（声明取代 B1F1 同名文件）
│   └── architecture-gates.md# ★ 架构门禁契约：G1–G13 及其判定方式（G7 8→18 · 新增 G10–G13）
├── checklists/
│   └── requirements.md      # 规格质量清单（/speckit.specify + clarify 维护）
└── tasks.md                 # Phase 2 输出（/speckit.tasks 创建，本命令不生成）

harness/verification/B2F1/
└── manual-verification.md   # 人工验证记录（原则 V 人工门禁 · 骨架由本 feature 产出，实测输出由人执行后填入）
```

**取代声明**：`specs/b1f1-contracts-core/contracts/public-api.md` 保留为 **B1F1 的历史快照**
（B1F1 的 8 符号清单与类型冻结记录**逐字不改**），其「唯一手工维护点」地位由本 feature 的
`contracts/public-api.md` 取代；本 feature 在 B1F1 该文件**顶部加一行取代提示**（不删改任何
既有内容），以保证「权威唯一」（SC-020）成立。

### Source Code (repository root)

```text
src/freegraph/
├── __init__.py                 # 既有 · 顶层包保持惰性（只暴露 __version__）—— 本 feature 不动
├── py.typed                    # 既有 · PEP 561 标记（顶层一个即覆盖全部子包）—— 本 feature 不动
└── contracts/                  # ★ 本 feature 扩展（B1F1 已建 types.py / errors.py / __init__.py）
    ├── __init__.py             # 扩充：公开符号面 8 → 18 + __all__
    ├── types.py                # 既有（B1F1）· StateDict / Command / StateSnapshot / RunConfig —— 本 feature 不动
    ├── errors.py               # 既有（B1F1）· 异常体系 —— 本 feature 不动
    ├── protocols.py            # ★ 新增：NodeFunc / Checkpointer / TraceSink / Store / CompiledGraph
    ├── graph.py                # ★ 新增：Graph / Node / Edge（图结构自有类型）
    └── trace.py                # ★ 新增：Span / TraceQuery（可观测数据面 + C27 查询请求）

tests/contracts/
├── conftest.py                 # 既有（B1F1）· 让 pytest 能找到 src/ 下的包
├── test_types.py               # 既有（B1F1）· 本 feature 不动
├── test_errors.py              # 既有（B1F1）· 本 feature 不动
├── test_architecture.py        # 既有（B1F1）· 本 feature 扩展：G7 8→18 · G8 按清单 · 新增 G10–G13
├── test_protocols.py           # ★ 新增：5 个协议的方法集 / 纯抽象 / 结构化子类型判定 / 外部实现可接受
├── test_graph.py               # ★ 新增：Graph / Node / Edge 的字段、冻结、不可哈希、相等语义
├── test_span.py                # ★ 新增：Span 11 字段、不可变、生命周期回调语义、TraceQuery 5 字段、JSON 可序列化
└── fixtures/
    ├── __init__.py            # ★ 新增：空占位（署名头 + docstring + `__all__ = []`）——使夹具可被绝对导入
    └── external_impl.py       # ★ 新增：零内部依赖的外部实现夹具（同时实现 Checkpointer / TraceSink / Store）
```

**结构决策**：

- **契约层从 3 个模块扩到 6 个**：`protocols.py` 承接 5 个协议（B1F1 的 plan 已预告
  「使后续 B2F1（4 类协议）可新增 `protocols.py` 而不与本层纠缠」）；`graph.py` 与 `trace.py`
  分开，使「图结构」与「可观测数据面」互不纠缠，且 `contracts/__init__.py` 只做再导出。
  代价：导入契约层时多加载 3 个模块——已计入 SC-002 的 300 ms 预算（B1F1 基线 154 ms）。
- **`contracts/graph.py` 与未来的 `freegraph/graph.py` 同名不同义**：前者是**契约层的图结构
  数据类**，后者是 **B2F2 的公开门面**（`StateGraph` / `START` / `END`）。二者路径不同
  （`freegraph.contracts.graph` vs `freegraph.graph`），**不构成导入冲突**；已在两个模块的
  docstring 中互相注明，避免读者混淆。备选方案（改名为 `graphdata.py` / `structure.py`）
  被否——同名更能对上上游 `langchain_core.runnables.graph` 的心智模型，且契约层内部命名
  本就自由。
- **`trace.py` 而非 `span.py`**：该模块同时承载 `Span` 与 `TraceQuery`（C27 查询请求），
  二者同属「可观测数据面」，命名取上位概念。
- **夹具独立成文件**（`tests/contracts/fixtures/external_impl.py`）：SC-004 要求「一个
  **零内部依赖**的夹具能同时实现三个协议」——若夹具写在测试文件里，会被 pytest 的导入
  机制与同目录 import 污染；独立文件使「它只 import `freegraph.contracts`」这件事
  **可被静态扫描判定**（G2 的扫描范围覆盖 `tests/`）。
- **不新建 `harness/` 下的门禁脚本**：CI 门禁归 **B3F1**；本 feature 的门禁以 pytest 断言
  交付（B3F1 时把这些断言接进流水线即可）——沿用 B1F1 的既有决策。
- **`pyproject.toml` 不动**：依赖仍为 `dependencies = []`，`requires-python` 仍 `>=3.11`；
  本 feature 不新增 extras、不新增发行包（D1）。

---

## Phase 0 → Phase 1 产出映射

| Phase | 产出 | 状态 |
|---|---|---|
| Phase 0 | `research.md`（**20 条决策 D-01…D-20** 的台账 + 上游源码证据 + **13 条**挂起项交接表） | ✅ 已完成 |
| Phase 1 | `data-model.md`、`contracts/public-api.md`（18 符号 + C1–C27 对照 + 冻结记录）、`contracts/architecture-gates.md`（G1–G13）、`quickstart.md` | ✅ 已完成 |

**Phase 1 后复核**：宪法门禁逐条重新过一遍 —— 结论与上方「Constitution Check」一致，
**无新增违反项**。Phase 1 期间的三项实质性收紧：
① 「协议齐全」由 spec 的**类别描述**落到**逐字的方法集与签名**（`data-model.md` §2–§3）；
② 「公开符号面」由「一次性取到」落到**集合相等断言**（恰 18 个，G7）+ **唯一权威文件**断言（G12）；
③ 「纯数据纪律」落到**字段级断言**——四个数据类**不得**出现承载对象引用的字段（G13），
   且 `Edge` 须显式 `__hash__ = None` 才能兑现「统一不可哈希」（`data-model.md` §4.3）。

**文档一致性复核（2026-11-06 · `/speckit.analyze`）**：spec / plan / tasks 三件套 + Phase 0/1
产物 + 仓库现状的交叉复核，共 22 项发现，**全部已就地修正**（未改任何冻结面的**内容**，
只改**表述口径 / 判据边界 / 计数 / 仓库现状对齐**）。四处关键裁定：

| # | 裁定 | 落点 |
|---|---|---|
| 1 | **`CompiledGraph` 的参数名**按 `data-model.md` §2.5 的逐字签名**冻结为占位名**（原挂起各实现 feature）——理由：协议签名不写死参数名即无法实现，静态类型检查（SC-004）与对外文档都需要确切签名；**行为细节**仍挂起，下游改名走契约修订流程 | spec FR-005 / Q8 / Assumptions · data-model §2.5 / §6 · public-api §1.1 / §3 / §5 · research D-08（补修订记）· tasks T039 |
| 2 | **门禁 G8 的「行内须含上游来源行号」只对本 feature 新增的 10 行成立**（既有 8 行按 FR-017 **逐字不动**）——原判据要求 18 行全带行号，与 FR-017 直接冲突 ⇒ G8 必失败（**该条已被第二轮裁定 3 进一步收窄为「只对有上游同名符号者」**） | architecture-gates G8 · plan「原则 X 的处置」③ · tasks T032 / T033 / T041 / T054 |
| 3 | **门禁 G12 只认机器标记** `<!-- authority: yes\|no -->`（B1F1 旧文件正文含「唯一手工维护点」「权威来源」字样，关键词判定必然数出 2 个） | architecture-gates G12 · tasks T035（Notes 本已一致） |
| 4 | **人工验证记录路径**：宪法原则 V 正文与质量门禁第 5 项的 `harness/features/<feature>/` 残留（v1.3.0 目录迁移的遗留）经**独立宪法修订 v1.4.1（PATCH）**更正为 `harness/verification/<feature>/` ⇒ 本 feature 无需改路径 | `.specify/memory/constitution.md`（v1.4.1）· plan 上方说明块 |

另有：SC 计数 20 → **21**（SC-021 补入 tasks 头部与人工记录）、`Node.name` 类型口径统一为
`str | None = None` + 构造期归一、`A1–A4` 判据在 spec 内补指针、§0 清单解析规则修正
（锚点行 / 缩进注释行不得当作符号）、T034 / T037 由「新增」改「复核」（取代提示与
`authority: no` 标记已在 plan 阶段落盘）、新增 3 条任务（T056–T058：G2/G5/G9 门禁自检、
18 符号注解可解析、`import freegraph.contracts` 后无内部层模块）。

**第二轮文档一致性复核（2026-11-06 · `/speckit.analyze` 复检）**：共 **22 项发现**
（2 CRITICAL / 4 HIGH / 9 MEDIUM / 7 LOW）。**两项 CRITICAL 经判定均非 spec 设计缺陷**
——① G2 扫描范围扩到 `tests/` 后 `import pytest` 恒违规：spec 的 FR-008 / SC-003 口径
（只约束契约层）本无问题，缺陷在**门禁契约与任务描述**；② 既有 G7 硬编码「恰 8 个」、
其更新排到导出开始之后：spec 的 FR-012 / SC-017 已要求「与实际导出集合相等」，
缺陷在**任务排期**（本 plan 的风险表早已写对缓解，只是 tasks 未落到排期上）。
⇒ **未开 `/speckit.clarify` 澄清轮**，直接就地修正文档；**冻结面的内容一字未动**。

四处关键裁定：

| # | 裁定 | 落点 |
|---|---|---|
| 1 | **G2 改「两档范围」**：内部 import 档扫 `src/**` + `tests/**`；第三方 import 档**只扫 `tests/contracts/fixtures/**`**（其余测试文件豁免 `pytest`）——否则门禁恒失败 | architecture-gates G2 · tasks T006 / T056 |
| 2 | **G7 拆成两段并提前到 Foundational**：**子集段**（始终启用）在 T008、**集合相等段**（18 个符号全部导出后）在 T040——保证 US1–US4 全程可绿；硬编码常量与陈旧注释一并清除 | architecture-gates G7 · tasks T008 / T040 / T041 |
| 3 | **「行内上游来源行号」只对「有上游同名符号」者成立**：`NodeFunc` / `TraceSink` / `Span` / `TraceQuery` **无上游同名符号** ⇒ 写「无上游对应」+ 契约条目号（C5 / C6、C23 / C24、C27），**MUST NOT** 硬凑行号 | spec FR-017 / SC-021 · architecture-gates G8 · public-api §1.1 / §4 / §5 · tasks T032 / T033 |
| 4 | **SC-004 的 mypy 判据三处收紧**：① 夹具方法**写全类型注解**（`--strict` 的 `disallow_untyped_defs` 前提）；② `MYPYPATH=src`（或已安装包），未装包即 skip 并写明原因；③ 新增**显式协议一致性断言**（把夹具实例传给形参标注为协议类型的函数）——仅编译夹具**不构成**「协议可被外部实现」的证明 | tasks T015 / T021 / T043 / T044 |

另有：G4 的扫描范围同步扩到夹具目录（原文「夹具同样受检」此前**只有文字、无任务与实现支撑**）、
`contracts/__init__.py` 的模块 docstring（「恰为 8 个」/「`Send`/`interrupt` 归 B2F1」）纳入
T040 / T047 的复核范围、协议纯抽象的 AST 断言**去重**（统一归 G10）、
结构树补 `tests/contracts/fixtures/__init__.py`、§2.2 签名表中的 `...` 加说明、
manual-verification 骨架第 3 节的预填块统一标注为「**期望输出**（非实测）」。
**任务总数仍为 58**（未新增任务，全部修正并入既有任务）。

**全局一致性复核（2026-11-06 · 第三轮 · 读立项书 / Q8 / 下游提示词后）**：
上一轮只在 B2F1 的 feature 目录内做交叉核对，**未读** `harness/proposals/立项书.md`
（= §5.2 执行总表 / §5.3 契约副本 / §5.4 接口总览）与 `harness/reports/Q8-图运行时最小契约.md`
（契约唯一权威）。补读后发现 **4 处全局漂移**（均**非** B2F1 的 spec 设计缺陷，而是
**上游总览与下游提示词未随冻结面同步**），**已一并修正**：

| # | 漂移 | 影响 | 处置 |
|---|---|---|---|
| 1 | 立项书 §5.4 的 **P1 仍写 `Node`**（协议名） | 与 §5.2 的 B2F1 行、feature 提示词、B2F1 的 Q1 裁定冲突；且与**图结构元素 `Node` 撞名** | 立项书 §5.4 更名 **`NodeFunc`** + 写明 Q1 命名裁定（§5.4.1 的 Governance 四要素说明） |
| 2 | 立项书 §5.4 的 **DF4 `Span` 仍写 6 字段** | 与**立项书自己的 §5.3.1（C23 必带四项）**、B2F1 冻结的 **11 字段**均不一致 | DF4 补齐为 **11 字段**（含 `id`）+ 指向 §5.3.1 与 B2F1 冻结面 |
| 3 | 立项书 §5.4 **缺 `CompiledGraph` 与图结构三类** | §5.2 的 B2F1 行已列 `CompiledGraph`/`Graph`/`Node`/`Edge`，但接口总览无对应行 ⇒ 两节互不一致 | 新增 **P5 `CompiledGraph`** + **DF5**（`Graph`/`Node`/`Edge` + **必须自有重写**红线）+ **DF6**（`TraceQuery`） |
| 4 | **B18F1 提示词**的 `Span` 字段口径**缺 `id`** | 按该提示词实现会产出**无 `id`** 的 span ⇒ `parent`（父 span 的标识）**无从引用**，C27 的 JSON 可序列化前提落不了地 | B18F1 提示词三处同步：背景口径 / FR-001 / 实体表 —— **11 字段逐字**、字段面归 B2F1、**MUST NOT 增删字段** |

另：把 `CompiledGraph` 参数名冻结的**下游义务**补登进 spec Assumptions
（**B7F3 / B8F2 / B15F1 / B16F1** 以占位名为基线，改名走契约修订），
并在 plan 风险表新增「全局文档漂移」一行。**契约 C1–C27 的编号与语义一字未动**，
**Q8 无需修订**（立项书 §5.4 本就是它的总览副本）。

**第四轮文档一致性复核（2026-11-06 · `/speckit.analyze` · 19 项发现：0 CRITICAL / 6 HIGH / 7 MEDIUM / 6 LOW）**：
**无 CRITICAL ⇒ 无 spec 设计缺陷 ⇒ 未开 `/speckit.clarify` 澄清轮**，直接就地修正文档。
冻结面的**内容一字未动**；改动集中在**表述口径 / 机械判据 / 追溯补强**三处：

| # | 裁定 | 落点 |
|---|---|---|
| 1 | **`update_state` 的参数顺序矛盾**：FR-005 ⑥ 写作 `update_state(values, as_node=None)`（省略 `config`），与 `data-model.md` §2.5 / T039 的 `update_state(config, values, as_node=None)` 冲突——**位置参数顺序同属冻结面** | spec FR-005 ⑥ · data-model §2.5（不动）· tasks T039（不动） |
| 2 | **`stream` 的 mode 类型统一**为 `str \| Sequence[str]`（原 FR-005 ② 只说「字符串」，与 data-model 不一致） | spec FR-005 ② · data-model §2.5（不动）· tasks T039（不动） |
| 3 | **G13 的判定规则改写为白名单**（原「不得含任意**对象实例类型**」在 `get_type_hints` 口径下不可机械判定，而 `Mapping[str, Any]` 是否违规无定论） | architecture-gates G13 · tasks T042 |
| 4 | **补 Q8 唯一权威的对照校验任务**（此前只校「条目数 + 状态标注」，不校内容与 Q8 一致） | tasks T032 ⑥ |
| 5 | **G10 提前到 Foundational 落地**（原在 US5 末的 T042 ⇒ FR-007「MUST 纯抽象」在 T011–T042 之间**无任何自动判据**） | tasks 新增 **T059**（Foundational）· T042 改为 G11 + G13 |
| 6 | **人工记录与证据链补强**：§6 移交项补回 16 条 · §5 标题的 SC 引用纠正 · 「既有 8 行逐字未改」给出 `git diff` 机械判据 · quickstart 的 G8 脚本补到与门禁同口径 | manual-verification §5 / §6 · tasks T036 / T054 · quickstart §2.5 |

另：**宪法质量门禁第 3 项的「不适用」按发起者裁定登记为「已知偏离」**（见上方「已知偏离登记」）——
**不改宪法**。全局同步：立项书 §5.2 B2F1 行补 `Span` / `TraceQuery`（与 §5.4 对齐）·
spec / plan / 人工记录 / 提示词的**标题口径统一**为「5 个协议 + 5 个纯数据类」·
tasks 的阶段标题由 `feature N` 改为 `阶段 N`（避与宪法 v1.4.0 的 feature = `B<n>F<m>` 撞义）。

**第五轮文档一致性复核（2026-11-06 · `/speckit.analyze` · 14 项发现：1 CRITICAL / 2 HIGH / 5 MEDIUM / 7 LOW）**：
本轮把复核范围**扩到仓库现状**（`src/freegraph/contracts/`、`tests/contracts/test_architecture.py`、
`harness/verification/B2F1/`、`harness/prompts/guide.md`），并**实跑核实**了 27 个上游行号
（`langgraph 1.2.11` / `langchain-core 1.6.3` 已装，逐条命中 ✓）。

**唯一的 CRITICAL（C1）经判定为「任务排期缺陷」而非 spec 设计缺陷** ⇒ **未开澄清轮**：
spec 的 FR-012 / FR-017 / SC-017 / SC-021 与门禁契约 G8 的口径**本就一致且正确**
（期望值从 `public-api.md` §0 解析、逐符号恰有一行、三列齐全、来源行号只对有上游同名符号者），
缺口**只在 tasks.md**：无人执行 G8 的**测试改造**，而 T008 明令删除 `PUBLIC_SYMBOLS` 常量
⇒ `tests/contracts/test_architecture.py:779` 报 `NameError` ⇒ 阶段 2 Checkpoint 必红。

四处关键裁定：

| # | 裁定 | 落点 |
|---|---|---|
| 1 | **G8 的测试改造并入 T008**（与 G7 同批，**不另开任务**），且**同样拆成两段**——**① 子集段**（T008 落地 · 始终启用）：矩阵当前已有行 ⊆ §0 的 18 个 + 行数 ≤ 18 + 三列齐全 + 行内来源行号只对**已存在的**新增行成立；**② 集合相等段**（**T033** 写入 README 后启用）：矩阵符号集合 == §0 的 18 个。**为何必须两段**：README 的 10 行由 T033（US4）写、G8 的改造在 T008（Foundational）——若在 T008 就按「18 个逐个恰有一行」判定，T008~T033 门禁**恒红** ⇒ 两个 Checkpoint 都过不去（与 G7 的两段落地同构：子集段 T008 / 集合相等段 T040）；**「删常量」MUST 排在「G8 改造」之后** | tasks T008 ⑤ · T033 · 阶段 2 / 阶段 6 Checkpoint · 追溯矩阵（G8 / SC-017 行）· architecture-gates G8 |
| 2 | **guide.md 的全局漂移本轮一并修**——P1 仍写 `Node`（与 Q1 撞名）、B2F1 行缺 `Span` / `TraceQuery`、`RunConfig` 被说成 `TypedDict`（实为 frozen dataclass）、「C1–C26」未随 D11 更新 | harness/prompts/guide.md（9 处） |
| 3 | **冻结对照表的状态口径统一为「二态 + 正交修订标注」**——`public-api.md` §2 的「修订」从来只以备注出现、从未作为「状态」值；spec FR-013 / SC-006 与 tasks T032③ 三处对齐到「已冻结 / 挂起」二态 + 4 条修订另标 | spec FR-013 / SC-006 · tasks T032③ |
| 4 | **research.md 的决策数 13 → 20**——「13」是**挂起项**数不是**决策**数（决策为 D-01…D-20）；plan 两处口径漂移已修（tasks 的口径本已正确） | plan Project Structure · plan Phase 0→1 产出映射 |

另修 7 处 LOW/MEDIUM：FR-006 的不可哈希**理由逐类化**（`Edge` 全为标量 ⇒ 须显式
`__hash__ = None`；`Graph` 随元素不可哈希）· SC-017 补「新增恰为 10 个」的机械判据落点 ·
T018 / T024 的映射型字段缺省改写为 `field(default_factory=dict)`（dataclass 拒绝可变缺省）·
T009 / T058 改写为「复核」（既有门禁已覆盖，重复实现即漂移）· T035 补自检文件的命名约束 ·
T036 的 ⑤⑥ 改写为「复核（现状已满足）」· D-08 标题与 D-09 的 `Node.name` 口径同步 ·
`data-model.md` 补「哈希语义」的唯一维护点说明。**冻结面的内容一字未动**，
**宪法无需修订**（无 MUST 违反项）。

**第六轮文档一致性复核（2026-11-06 · `/speckit.analyze` · **21 项发现**
（**0 CRITICAL** / 5 HIGH / 9 MEDIUM / 7 LOW））**：本轮把复核范围**扩到仓库现状**
（`src/freegraph/contracts/`、`tests/contracts/test_architecture.py`、`README.md`、
`harness/verification/`、立项书 §5.3.1 / §5.4）与**上游运行时的实测行为**
（`typing.Protocol.__protocol_attrs__` 在 CPython 3.12.3 实测为 **`set`**
——`{'c','b','a'}`）。**无 CRITICAL ⇒ 未开澄清轮**；经**发起者裁定两处**后直接就地修正文档。
**冻结面的内容除下述两处粒度澄清外一字未动**，**宪法无需修订**。

| # | 裁定 | 落点 |
|---|---|---|
| 1 | **协议方法集改为「集合相等」判定**——「成员定义顺序」MUST NOT 纳入冻结面（按序断言必 flaky） | spec FR-007 · tasks T010 ①② / T038 ① · data-model §2 通用规则 ④ · architecture-gates G11 · public-api §1.3 |
| 2 | **兼容矩阵「上游来源」的落位写死**：**保持 4 列**，来源行号**写进该行的「差异说明」单元格末尾** ⇒ 消除「新增第 5 列」与 FR-017「既有 8 行逐字不动」的冲突 | spec FR-017 / SC-021 · tasks T033 / T054 · public-api §1.1 / §4 / §5-11 · architecture-gates G8 · quickstart §2.5 |
| 3 | **T056 改为「改造既有 `TestGateSelfCheck`」**（既有文件已含 G2 / G4 / G9 自检；T006 把 `scan_imports` 拆成两档后既有自检会假绿 / 假红） | tasks T006 末句 · T056 全文 · architecture-gates §2 |
| 4 | **T054 的机械判据放宽为两个白名单**（10 个新符号行 + 「证据来源」小节追加行）⇒ 消除与 T033 的硬矛盾 | tasks T054 |
| 5 | **冻结对照表「状态」列统一为二态 + 独立的「修订」列**（此前 public-api 表头「三态」/ 表内限定词 / spec+tasks「二态 + 正交」三套口径并存） | public-api §2 表 + 表头 + 统计行 · spec FR-013 / SC-006 · tasks T032③ |
| 6 | **`Checkpointer` / `Store` 的参数名冻结**（发起者裁定：**以 `data-model.md` 为准**）——挂起的只有返回类型 / 载荷形状（B14F1）与命名空间载体类型 / `batch` 操作表示（v2） | spec Q5 / Q7 补充 + FR-002 / FR-004 + Assumptions · data-model §2.2 / §2.4 / §6 · public-api §1.1 / §2 / §5 · research D-05 / D-06 + 挂起项表 · tasks T012 / T013 / T015 / T043 |
| 7 | **`test_architecture.py` 的门禁总览 docstring 纳入任务范围**（现状「八条架构门禁」+ G1–G8 表） | tasks T007 追加断言 · T008 ③ 追加条款 |
| 8 | **`stream` 的元素类型冻结为 `dict[str, Any]`**（原 `Iterator[Any]` ≠ FR-005②「纯数据字典」） | spec FR-005 ② / SC-015 · data-model §2.5 · tasks T038 ④ / T039 |
| 9 | **`Store` 的参数名逐字镜像上游**——`search` = `namespace_prefix`、`list_namespaces` = `prefix`（**上游 LangGraph 1.2.11 的原样命名**，核实 `langgraph/store/base/__init__.py`）⇒ **不改名**；上游的这个命名分歧**显式登记**（原则 VIII） | spec FR-004 / Q7 补充 · data-model §2.4 · research D-06 · tasks T013 / T015 / T043 |

另修 7 处 LOW：public-api 头部「4 类协议 + 图结构数据类」→「5 个协议 + 5 个纯数据类」与
「FR-001…FR-016」→「FR-001…FR-017」· 契约三件套 + Phase 0/1 产物 + checklist + 人工记录索引表的
**7 处标题术语**统一 · `quickstart.md` §2.5 的 G8 取行改为**章节内**（与门禁 G8 同口径）·
T018 的 `copy.copy` 理由更正（真正不可序列化的是 `MappingProxyType`）· 立项书 §5.4 的 P1 补
「实现形态 = `Protocol` + `__call__`」· 立项书 §5.3.1 / §5.4 的 C23 第四项补「字段名 = `node`」·
人工记录 §6 第 11 条补「上游来源写进差异说明单元格」子句。

---

## Complexity Tracking

**无违反项** —— Constitution Check 十条门禁全部通过（原则 III 因 `target.py` 依赖尚未交付的
B2F2 门面与 B7F3 运行时而「不适用」，已在门禁表中显式记录，非忽略），故本表不适用。

---

## 风险与后续依赖

| 风险 | 影响 | 缓解 |
|---|---|---|
| **估算与实测的缺口**：立项书估「实现 480 / 测试 340」，但本 feature 有 **13 条门禁** + **21 条成功标准** + **18 个公开符号** | 实现与测试的实际行数可能显著超出估算（测试尤其） | 估算偏差**回填**到本 plan 的「Scale/Scope」小节（实现后）；门禁断言尽量用**参数化**写法摊薄行数；测试与实现的行数比不作硬约束（契约层的价值在断言密度） |
| **`Edge` 意外可哈希**：`Edge` 四字段全是标量，`@dataclass(frozen=True)` 会自动生成 `__hash__` → 与 SC-019 的「四类统一不可哈希」冲突 | 用户按「不可哈希」预期写代码会踩 `TypeError` 之外的**不一致**（有的能放 set 有的不能） | 在 `Edge` 类体显式写 `__hash__ = None`（CPython `dataclasses` 的 `_hash_action` 对「显式定义 `__hash__`」不覆盖）——`data-model.md` §4.3 已写死该做法与依据 |
| **`TraceQuery` 意外可哈希**（五字段全为 `str \| None`） | 与四类的「不可哈希」口径不一致 | **记录在案、不视为缺陷**（它本就没有映射字段）；`data-model.md` §4.3 显式说明差异与理由——「不可哈希」的根因是**含映射字段**，不是一条无理由的禁令 |
| **`NodeFunc` 的结构化子类型判定对**任意可调用对象**恒为真** | `isinstance(f, NodeFunc)` 几乎不会失败（函数自带 `__call__`） | 这是 `runtime_checkable` 协议含 `__call__` 的固有性质；spec 的 Edge Cases 已记录该局限；本 feature 的验收**不依赖**该判定来证明「节点函数合法」，而依赖**静态类型检查**（SC-004 的 mypy 路径） |
| **协议签名中的 `Any` 占位**（`Checkpointer` 参数 / `Store` 命名空间）被下游当成「已冻结的具体类型」 | 下游实现按 `Any` 写，事后收紧时产生「静默不兼容」 | 占位处**逐个写明挂起归属**（`data-model.md` §2.2 / §2.4），并在 `contracts/public-api.md` 的「移交后续 feature」表登记；收紧属**契约修订**流程（宪法 §Governance） |
| **公开符号面 8 → 18 的变更**波及 B1F1 的门禁 G7 与文档 | B1F1 的 `test_architecture.py` 断言「恰 8 个」会**当场失败**（自第一次追加导出起即失败） | 本 feature **同步修改**该断言为「**从 `public-api.md` §0 解析**」并**拆成两段**落地：**子集段**（始终启用，抓「偷偷多导出」）在 Foundational 的 T008 落地、**集合相等段**（抓「漏导出」）在 18 个符号全部导出后（T040）启用——**保证 US1–US4 全程可绿**；硬编码常量与三处「恰 8 个」的陈旧注释**一并清除**（含 `Send` / `interrupt` 归属注释：归 **v2** B11F1 / B10F1）；兼容矩阵**本 feature 补入本层 10 行**（FR-017 / SC-021），全库补全与定稿**移交 B24F1**（已在 `contracts/public-api.md` §5 登记） |
| **G2 门禁的扫描范围过宽**（扩到 `tests/contracts/**` + 黑名单含「任何非标准库顶层包」） | 测试文件必然带 `import pytest` ⇒ 门禁**恒失败** | **两档范围**：内部 import 档扫 `src/**` + `tests/**`；第三方 import 档**只扫 `tests/contracts/fixtures/**`**，其余测试文件豁免（`pytest` 是开发期工具）；「夹具零内部依赖」由内部 import 档的绝对导入白名单保证，判据不受损（G2 细则见 `contracts/architecture-gates.md`） |
| **B1F1 的 `contracts/public-api.md` 与本 feature 的同名文件并存** → 两个文件自称权威 | 读者取到旧清单 | 本 feature 在 B1F1 文件**顶部加一行取代提示**（不删改既有内容），并由门禁 **G12** 断言「仓库内自称权威的公开符号清单文件数 == 1」 |
| **下游提示词的口径需同步**（B18F1 / B22F1 / B2F1 本身） | 下游按旧口径实现 → 冲突 | 已在 spec 的 Assumptions「对下游 feature 提示词的影响」逐条列明：**B18F1** 交付物收窄为「span 生产行为」（类型面以本 feature 为准）；**B22F1** 的 `Graph`/`Node`/`Edge` 命名**不变**；**B2F1 提示词**第 1 项协议名改为 `NodeFunc`；**B2F1 提示词**的 `Send` / `interrupt` 仍**不导出**（v2） |
| **全局文档漂移**（第二轮复核发现）：立项书 §5.4 的 P1 仍写 `Node`、DF4 `Span` 仍写 6 字段、且无 `CompiledGraph` 与图结构条目；B18F1 提示词的 `Span` 字段口径缺 `id` | freechain 读接口总览会与冻结面**不一致**（`Node` 撞名）；B18F1 按旧提示词实现会产出**无 `id`** 的 span → `parent` 无从引用、C27 的 JSON 可序列化前提落不了地 | **已同步（2026-11-06）**：立项书 §5.4（更名 + P5 / DF5 / DF6 + DF4 11 字段 + 自有重写红线 + §5.4.1 的 Governance 四要素说明）· B18F1 提示词（`Span` 字段面归 B2F1、11 字段逐字、**MUST NOT 增删字段**）· B2F1 spec Assumptions 补登 **B7F3 / B8F2 / B15F1 / B16F1** 以占位名为基线 |
