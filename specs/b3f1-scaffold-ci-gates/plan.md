# Implementation Plan: B3F1 · 项目脚手架（extras 划分 + `src/` 布局 + 类型标记）+ 7 项质量门禁的自动化落地

**Branch**: `b3f1-scaffold-ci-gates` | **Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b3f1-scaffold-ci-gates/spec.md`

**feature ID**: `B3F1`（M0 地基 · 31 个 feature 中的第 4 个 · 前置 **B1F1** / **B2F1** / **B2F2**）

---

## Summary

一次性建起 freegraph 的**工程设施**，交付两类东西：

**① 项目脚手架**——把 `pyproject.toml` 从「只有基础依赖」补成**完整的 extras 划分**，
并确立 Python 版本矩阵：

> **⚠️ v1.0 的依赖面 = 零（2026-11-08 · 裁定 26 · 宪法 v1.7.0 · 发起者已决）**：
> 「freegraph v1.0 不希望看到依赖包，所有依赖包放到 v2.0」⇒
> **v1.0 的 `pyproject.toml` 不含 `[project.optional-dependencies]`** ⇒
> **发行元数据零依赖包名**（实测：`Requires-Dist` == `None`）；
> 下表的四个 extra **移入 v2.0 范围**，其声明落在
> **`contracts/extras-v2.toml`**（**不进发行包**）⇒ 门禁 **G21 / G23** 对该清单
> **取证** ⇒ **v1.0 即完成预验证**（v2.0 落地时只需把清单搬进 `pyproject.toml`
> ⇒ **门禁实现零改动**）。
> ⇒ 下表因此是「**v2.0 的目标闭包**」，**不是** v1.0 的交付内容。

| extra（**v2.0 范围**） | 内容 | 实测依赖闭包 | 许可证判定 |
|---|---|---|---|
| `[pydantic]` | 结构化状态 schema 支持 | `annotated-types` · `pydantic-core` · `typing-extensions` · `typing-inspection` | ✅ 全绿 |
| `[checkpoint]` | checkpoint 序列化 | `ormsgpack`（闭包为空） | ✅ 全绿 |
| `[otel]` | 可观测性内核（OTel API + SDK） | `opentelemetry-api` · `opentelemetry-sdk` · `opentelemetry-semantic-conventions` · `typing-extensions` | ✅ 全绿 |
| `[png]` | 本地 PNG 渲染（**默认关闭** · **宪法 v1.5.0 已列明** = `playwright`）<br>**⚠️ 渲染后端方向留待 v2.0 专项调研**（D-16） | `playwright` · `greenlet` · `pyee` · `typing-extensions` | ✅ 全绿（`Apache-2.0`） |

> **⚠️ `[png]` 的后端取自宪法 v1.5.0（2026-11-08 分析轮订正）**：本 plan 的职责**只**是**核验**
> `playwright` 的**许可证标识 ∈ 白名单**（实测 `Apache-2.0` · research D-02）与**运行期零出站**
> （Chromium **本地**渲染 · research D-04）⇒ **MUST NOT** 另选后端。
> 宪法 v1.5.0 已把包层白名单条里「mermaid 相关」这一**类别式**表述**已被宪法 v1.5.0 取代**为确切包名 `playwright`
> 并追加三条硬约束 (a) 默认关闭 / (b) 许可证白名单 / (c) 零出站 ⇒ **plan 阶段「选型」已不存在**。

> **⚠️ 闭包的版本敏感性（2026-11-07 实测补记 · 复核节奏 2026-11-08 发起者决议）**：上表的闭包是**当前解析结果**（`pydantic` 解析到 2.13.x）。
> 因 extras 的版本约束是**开区间**（`pydantic>=2.0`），上游**新增一个传递依赖**即会让闭包多出一个包名
> ⇒ G3 的「12 名白名单」将失配 ⇒ **CI 变红**。处置：**T003** 的白名单 MUST 视为**需随上游复核**的清单
> （**复核的双触发点**：**extras 的版本约束变更**、或 **CI 因闭包失配而红** —— 二者任一即触发）；
> **FR-018** 的「不得放宽」约束的是**判据**，
> 而「上游新增了一个传递依赖」属**事实变化**⇒ 处置方式是**重新实测闭包并追认更新白名单**（仍须发起者追认），
> **MUST NOT** 以「放宽白名单以让它变绿」的方式绕过（那会把未复核的包名直接放行）。
> ⇒ **已决：保持版本约束为开区间**（不收紧版本上界）—— 失配时的红是**安全侧**。

**基础安装的依赖闭包 MUST 仍为空集**（`dependencies = []` · 沿用现状 · 宪法 v1.2.0）。

**② 10 条新门禁（G21–G30）+ 既有 20 条（G1–G20）接线进 CI**——
门禁是「**契约的执行机制**」，本 feature 的交付判据是**反向的**：
**故意引入 `langchain-core` → CI 必须失败**（spec SC-001 / **验收判据 A1**（引文 §6 · 门禁生效 = 负向验证 · 对应**执行闸口 A2**））。

技术上，10 条门禁全部由**标准库**承载：`ast`（静态扫描）· `importlib.metadata`（依赖闭包与许可证证据）·
`subprocess`（隔离环境 / 模块加载面）· `socket`（零出站监测 · **只观测不阻断**）·
`difflib`（只读基准 diff）· `git`（工作树隔离副本 · 负向验证）。**门禁工具链本身零第三方依赖**
（`packaging` 仅作为**开发期**依赖用于 SPDX 表达式解析，见 research D-05）。

**三处「实测发现的、与既有材料冲突」的问题**（详见 [research.md](./research.md)）：

1. **既有门禁 G3 在引入 extras 后必然变红**（**实测**：实际变红的是「**白名单子集断言**」——
   旧枚举语义下 extras 闭包为 **20** 个包，其中 **8** 个不在 4 个占位包名内；
   「许可证断言」实为 **`pytest.skip`**（那 8 个包**均未安装** ⇒ 落入 G3 既有的 `missing` 分支）
   ⇒ **不构成变红原因**；且 **`dnspython` 不在闭包内**（它是 `email-validator` 的依赖，
   而 `email-validator` 本身未安装 ⇒ 递归到它时即取不到元数据）⇒ 只有 `email-validator`（Unlicense）进闭包）
   ⇒ 本 feature 必须**填充 G3 中由 B2F1 明确预告的占位常量**——
   这是 **裁定 8 的唯一一处例外**（已登记于 Constitution Check · 判据句逐字未动，**净效果是变严**）。
2. **`[otel]` 不可含 `opentelemetry-exporter-otlp`**（实测：其闭包含 `requests` → `certifi`
   **(MPL-2.0)**，不在白名单）⇒ `[otel]` 取**宪法原文所列**的 `opentelemetry-api` + `opentelemetry-sdk`；
   exporter 归 **B21F1**（OTLP 导出插件）解决。
3. **SVG→PNG 的纯 Python 路线几乎全被白名单拒绝**（实测：`cairosvg`/`svglib`/`pycairo` = LGPL ·
   `pillow` = `MIT-CMU`/`HPND` · `matplotlib` 的闭包含 `pillow` 且 `numpy` 的表达式含 `0BSD`/`Zlib`/`CC0-1.0`）
   ⇒ `[png]` 取 **playwright**（Apache-2.0，闭包全绿，**唯一**可行后端）—— **宪法 v1.5.0 已列明**
   （原「mermaid 相关」的类别式表述**已被宪法 v1.5.0 取代** ⇒ plan 只**核验**许可证与零出站，**MUST NOT** 另选后端）。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`pyproject.toml` 的 `requires-python = ">=3.11"` · 裁定 1）；
**typing 构件上限 = 3.11**（宪法「运行时环境基线」）——MUST NOT 使用 `TypeAliasType`(3.12) /
`override`(3.12) / `ReadOnly`(3.13) / `TypeIs`(3.13) 或 PEP 695 `type` 语句。
**主判定 = CI 矩阵最低档 3.11 跑全量测试**（SC-002b · **含架构门禁的**测试** —— `tests/contracts/` 与 `tests/facade/` 承载的 G1–G20）；**辅判定 = 既有门禁 G9**（FR-017 · 只接线，判据零改动）。
本 feature 的门禁代码用到的 typing 构造**全部 ≤ 3.11**（`Self` · `Literal` · `TypeAlias` · `Protocol` · `TypedDict`）。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []` · 沿用现状）。
**开发期工具**（不进发行包）：`pytest`（实测 7.4.4）+ `packaging>=24.2`
（**SPDX 表达式解析** · `packaging.licenses` 模块自 24.2 才存在 —— 实测本机 `packaging 24.0` 无该模块；
research D-05 有实测验证）。
**声明方式** = `pyproject.toml` 的 **`[dependency-groups] dev`**（PEP 735）· 安装 = `uv pip install --python .venv --group dev`
（**实测 uv 0.12.7 支持** · `--python` 接受**venv 目录** ⇒ **跨平台**）⇒ **不进 `Requires-Dist`**（**实测**：装 dev 组后 `Requires-Dist` 中**不带 `extra ==` 标记的条目数**仍为 **0**）
⇒ 基础闭包仍为空集（G3 不受影响），
**且不参与 extras 变体枚举**（dependency-gate.md §2.2）。
> **⚠️ 口径订正（2026-11-07 分析轮 · 实测）**：「`Requires-Dist` 为 `None`」这一表述**只在未声明 extras 时成立** ——
> **T002 声明四个 extras 后**，实测 `Requires-Dist` 变成**一个含 5 个条目的 list**（每个都带 `extra == '...'` 标记 —— `pydantic` / `ormsgpack` / `opentelemetry-api` / `opentelemetry-sdk` / `playwright`）。
> ⇒ **基础闭包为空集**的正确判据是「**不带 `extra ==` 标记的条目数 == 0**」（T045 · 闸口 A1），
> **MUST NOT** 断言「`Requires-Dist` 为 `None`」。
**CI 的安装步骤**（contracts/ci-matrix.md §2）：⓪ **建 venv**（`uv venv --python <档位>` —— **必做**：
`uv pip install` 在**无活动虚拟环境**时报 `No virtual environment found` 并以**退出码 2** 失败（**实测**）
⇒ 无此步则**步骤 4 在 7/7 作业上直接失败**）；① 装 dev 组；② 装发行形态；
③ **全部 7 个作业 MUST 装齐四个 extras 的依赖**（`uv pip install --python .venv -e ".[pydantic,checkpoint,otel,png]"` · 只装 Python 包、不装浏览器二进制 · **跨平台写法**）——
**这不是可选项**：不装则 G23 取不到许可证据（要么必红、要么退化为空门禁 ⇒ **违宪**）、G21 的闭包走不到末端、
G3 的 12 名白名单永不触达（**实测**：四个 extras 的完整闭包**恰好 12 个包**，与 G3 白名单逐一命中）。
**③ 的适用范围订正（2026-11-07）**：原写「**Linux 全量作业** MUST 额外装齐」—— 但 G21 的判定要求 extras 的
**传递依赖已安装**才能完成递归取证（architecture-gates G21「未安装 ⇒ 判失败」）⇒ **非 Linux 作业不装 extras 即必红**
⇒ ③ 的范围改为**全部 7 个作业**。
**⚠️ 解释器路径 MUST 跨平台（2026-11-08 分析轮订正 · C1）**：CI 与手册的命令串**只出现 venv 目录 `.venv`**
—— 安装用 `uv pip install --python .venv …`（**实测 uv 0.12.7 接受 venv 目录**），
调用用 `uv run --no-project --python .venv python …`（`--no-project` ⇒ **不解析项目、不同步环境**
⇒ MUST NOT 让它把已装的四个 extras 依赖卸掉）⇒ **MUST NOT** 出现任何平台专属的解释器路径
（Windows 上 `uv venv` 生成的是 `.venv\Scripts\python.exe` ⇒ 硬编码 POSIX 路径会让 `windows-2025` 的 2 个作业**必红**）。
详见 `contracts/ci-matrix.md` §2.0。

**Storage**: N/A —— 本 feature 无运行时持久化。门禁的**清单类工件**是**仓库内的纯文本**（入库比对）：
层注册表 · 断网排除清单 · 门禁契约文档。

**Testing**: pytest（开发期实测 7.4.4）+ 标准库 `ast` / `subprocess` / `importlib.metadata` /
`socket` / `difflib` / `tempfile`。
**需要子进程 / 隔离环境的断言**（G22 隔离 venv · G1/G18 模块加载面）**必须在子进程中执行**
——测试进程自身已导入 pytest（沿用 B1F1 的判定口径）。

**Target Platform**: 任意 CPython 3.11+ 平台（Linux / macOS / Windows）。
**断网等价性任务（G28）仅 Linux**（网络命名空间 · 裁定 10）；**Windows / macOS 跑子集**。

**Project Type**: library（Python 库；发行名 = 导入名 = `freegraph`；D1 决议：不拆独立发行包）+
**工程设施**（本 feature 是**跨层单元** · 层 = 「—」· 立项书 §5.1 的跨层单元清单）。

**Performance Goals**: **N/A**（本 feature 无运行时热路径）。**门禁自身的耗时**是唯一的非功能指标：
单条门禁 MUST 在 **≤ 60 s** 内完成（CI 作业预算）；G22（隔离 venv + 安装）与 G28（断网重跑全量）
是仅有的两条可能超时的门禁 → 二者在 CI 中**独占 step**，并允许 **≤ 10 min** 的 job 超时。
> **⚠️ 2026-11-08 分析轮订正 · 与 G27 的观测面口径对齐**：契约（G27「独立入口的观测面」= **在 egress 监测下跑整个测试套件**）
> 意味着 **G27 的独立可执行入口会再执行一遍全量测试套件** ⇒ 它是**第三条**可能超时的门禁
> ⇒ **本条 MUST 同步修订为「G22 / G27 / G28 三条可能超时」**，且 G27 独立入口在 CI 中**独占 step**（Linux only · 步骤 9）。
> **不缩小观测面**（缩小 ⇒ 空断言 ⇒ 违宪 SC-006 ①）⇒ 代价登记在此（CI 成本 · Linux 作业的测试套件跑两遍）。

**Constraints**（**主要**来自 spec 的 MUST 条目；未逐条列出的 FR 见 `tasks.md` 的追溯表）:

| 约束 | spec 条目 |
|---|---|
| 基础安装依赖闭包 **= 空集** | FR-001 · SC-002 |
| `requires-python` = `>=3.11` 且**不设上限** | FR-001 · FR-003 · 裁定 1 |
| 依赖闭包（**含全部 extras 变体**）无 `langsmith` / `langchain*` / `langgraph*` / **`deepagents`**（**v1.0 的判据对象 = `contracts/extras-v2.toml`** · 裁定 26） | FR-005 ① |
| **验收环境**内 freegraph **不碰** `langchain`（**③① 声明级 + 导入级**在 B3F1 交付；**③② 运行期待 M2**） | FR-005 ③① · 裁定 22 |
| 许可证 ∈ **{MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, PSF-2.0}**（**精确** · SPDX 表达式**逐叶子**判定） | FR-006 · 裁定 17/18 |
| **v1.0 的发行元数据零依赖包名**（`Requires-Dist` **整个为空**） | 裁定 26 · 宪法 v1.7.0 |
| 配置层：`LANGSMITH_*` / `LANGCHAIN_*` / `LANGGRAPH_CLOUD_LICENSE_KEY` / `LANGGRAPH_AUTH*` **零读取**；内核**零**环境变量读取 | FR-007 |
| 导入图**单向**（L1→L6 递增；**同层 import 仅 L1 与 L6 允许，L2–L5 之间禁止横向依赖** · 立项书 §5.1 铁律 3；跨层只 import L1 及更低） | FR-008 |
| 零出站：**只观测不阻断** + **第一个非标准库帧**归因 · 只对「框架出站」断言 = 0 | FR-009 ② · 裁定 19 |
| freegraph **不得**安装任何出网拦截机制 | FR-009 ③ |
| 断网等价性：全量测试套件 + **可机读**排除清单 | FR-010 · 裁定 16 |
| 兼容矩阵**分层**判定（已入库严格阻断 / 未建全只报告） | FR-012 ② · 裁定 13 |
| 全仓署名头覆盖率 **= 100%**（两个具名例外） | FR-013 · 裁定 5 |
| **第三方品牌资产**：图像 / 品牌色 / 官方 Approved copy 文案 **命中数 == 0**（自有资产白名单**当前为空集**） | **FR-021** · 裁定 23 |
| 既有门禁 **G1–G20 判据零改动** | FR-016 ② · 裁定 8 |
| **不得**放宽任何白名单 / **不得**引入豁免机制 | FR-018 |
| 分支保护 + required check（**由发起者执行**） | FR-020 · 裁定 20 |

**Scale/Scope**（**实现后回填 · 2026-11-08 · T054**）：

| 项 | 立项书 §5.2 的估算 | **实测** | 说明 |
|---|---|---|---|
| 实现 | ≈ 620 行 | **3,612 行** | 共享判定库 `_gatekit.py` **1,392** + 10 个门禁薄壳 **2,070** + CI workflow **150** |
| 测试 | ≈ 480 行 | **829 行** | `tests/gates/`（`__init__.py` 14 + `conftest.py` 91 + `test_gates.py` 673）+ `tests/contracts/test_contract_regressions.py` 51 |
| 文档 | ≈ 1,200 行 | **4,546 行** | `specs/b3f1-scaffold-ci-gates/**`（spec / plan / research / data-model / quickstart / tasks + 4 份契约 + checklist）+ `harness/verification/B3F1/manual-verification.md` |
| **合计** | **1,100 行** | **≈ 8,987 行** | —— |

> **⚠️ 与立项书估算的偏离（登记 · 不改立项书 · 沿用 B2F2 的「行数口径」做法）**：
> 实测量约为估算的 **8.2 倍**。**原因**（不压缩）：
> ① 立项书把「**7 项**质量门禁」当作一个整体计，而实测它需要 **10 条独立编号**的门禁
> + **1 份共享判定库** + **1 份 CI 矩阵契约** + **1 份层注册表**
> —— FR-016 ① 要求每条门禁有**独立编号 + 独立报错**（可定位性），压缩即违背 spec；
> ② 本仓库的既有风格是**判据自带长篇 docstring**（把契约条款、实测证据、失败模式
> 写进代码 —— 门禁代码本身就是**契约的执行机制**），故实现行数高于「纯逻辑」的估算；
> ③ 文档侧因 spec 经**四轮澄清**（25 条裁定 + 13 条问答）而膨胀。
> ⇒ **登记，不改立项书**（同 R-3 的处置）。

**登记（不改立项书）**：立项书 §5.2 的 B3F1 估「**1,100 行**（实现 620 / 测试 480）· 3 人日」。
本 feature 的**实现**实测 **3,612 行**（共享判定库 1,392 + 10 个门禁薄壳 2,070 +
CI workflow 150），**测试**实测 **829 行**，**文档产出**实测 **4,546 行**
⇒ **合计 ≈ 8,987 行**，**显著超出**立项书的 1,100 行估算。
**原因**：立项书的估算把「7 项质量门禁」当作一个整体计，而实测发现它需要 **10 条独立编号**的门禁
+ 1 份共享判定库 + 1 份 CI 矩阵契约 + 1 份层注册表。**不压缩**——门禁的**可定位性**（FR-016 ①）
要求每条门禁有独立编号与独立报错，压缩即违背 spec。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 通过项（逐条）

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith 依赖 · 自身零出站） | G21 依赖黑名单 · G23 许可证 · G24 配置层 · G26 网络静态 · G27 零出站动态 | ✅ |
| 原则 II（内核纯净 · 零 langchain import） | G21 ① + G22 ②（`sys.modules` 断言）· G25 导入图 · **FR-005 ③① 落地于 G22 场景②**（③② 运行期待 **M2** · **裁定 22**） | ✅ |
| 原则 III（契约冻结 · `target.py` 只读） | G29 契约载体（diff 断言 + C4/C8 挂载点） | ✅ |
| 原则 IV（可观测技术选型 · 路线 B） | FR-004 `[otel]` = `opentelemetry-api` + `opentelemetry-sdk`（**与宪法依赖白名单逐字一致**） | ✅ |
| 原则 V（人工验收 + 门禁 4 的 D12 措辞） | FR-009 ②（只观测不阻断 + 归因）· FR-010 断网 · FR-019 人工记录 | ✅ |
| 原则 VI（规格门禁 · tasks 可勾选） | 本 plan + `tasks.md` | ✅ |
| 原则 VII（契约 C1–C27 权威范围） | 本 feature **零契约变更**（只新增挂载点，不改任何冻结面） | ✅ |
| 原则 VIII（证据与术语纪律） | `research.md` 全部结论附**实测命令 + 输出**；`Harness` 术语沿用官方对照表 | ✅ |
| 原则 IX（许可证与商标红线 · NON-NEGOTIABLE） | G23（5 个精确 SPDX id + 4 级证据链 + ELv2 点名 · 取证口径 = **并集口径** · spec 裁定 25）· **FR-021 / G30 判定第 6 项（第三方品牌资产：图像 / 品牌色 / 官方 Approved copy 文案）** · FR-018（零豁免） | ✅（**见下方「唯一例外」**；品牌资产段的「自有资产白名单」口径见 **spec 裁定 23**） |
| 原则 X（文档合规 + 源文件署名头） | G30 全仓署名头 · FR-012 兼容矩阵分层 · FR-020 分支保护 · **T050（`THIRD_PARTY_NOTICES` §2「第三方运行时依赖」表的说明文字同步 —— 原则 X 的第三方归属义务）** | ✅ |
| 运行时环境基线（Python 3.11 · typing 上限 3.11） | FR-015 ①（矩阵最低档 3.11 跑全量）· FR-017（接线 G9） | ✅ |
| 依赖白名单 / 黑名单（包层 · 配置层 · 网络层） | G21 / G23 / G24 / G26 / G27 | ✅ |
| 质量门禁 1–7 | SC-003（4 项全自动 + 3 项存在性检查 · 存在性检查落 `tasks.md` **T056**） | ⚠️ **门禁 3 / 4 / 5 三项在本 feature 不适用** —— 三者**共享同一根因**：「MVP 验收基线的跑通需要内核运行时，内核运行时按 立项书 §6.2 属 **M2**（固定脚本最小交付集 = B6F1 / B7F2 / B7F3 / B8F1 / B22F1 / B23F1）」，而本 feature **不交付内核功能** ⇒ ① **门禁 3** 的「MUST 包含 C4 与 C8」⇒ 只落**挂载点**并明确标「未落地」（FR-011 ②）；② **门禁 4** 的「fake 模型跑通验收基线的一轮」⇒ 以 **G29 ②** 的「退出码 ∈ {0,1,2} + 按失败来源细分」**部分落地**；③ **门禁 5**（原则 V 同款）的「人工记录含**真实模型一轮**」⇒ 无图可跑 ⇒ 以 T048 的五段式记录 + 零出站 / 断网全绿实测证据覆盖 ⇒ **三条一并登记为偏离 ⇒ 由 `tasks.md` T057 一并追认（阻断合入）**（见「复核后新增的登记项」**R-4**）；**⚠️ 退出码口径已订正**（CI 中 freegraph 已安装 ⇒ 退出码为 **1** 而非 2 ⇒ G29 ② 按失败来源细分，见 R-4）；**MUST NOT** 改宪法正文、**MUST NOT** 写一条永久红的 CI；门禁 1 / 2 / 6 / 7 ✅（门禁 2 的**第三方品牌资产**部分由 **FR-021 / G30 判定第 6 项**承担 · 见 spec 裁定 23） |
| 发布门禁（发行产物纯度） | **本 feature 不接入**（B24F1）· 本 feature 只提供**先行检查**（SC-005） | ✅ 边界内 |

### ⚠️ 唯一一处例外（对 **裁定 8** 的例外 · 需发起者追认）

**裁定 8**：「本 feature MUST NOT 修改既有门禁 **G1–G20** 的**判据**（含其硬编码文件清单）」。

**实测结论**：既有门禁 **G3** 在 extras 引入后**必然变红**，且**无法**在不动它的前提下变绿。

- **G3 的判据句**：「extras 变体闭包 MUST 只含宪法依赖白名单内的包」+「闭包内每个包的许可证 MUST ∈ 白名单」
  —— **这两句判据本 feature 逐字保留**。
- **G3 的两处占位**（**由 B2F1 自己在注释里预告**）：
  `tests/contracts/test_architecture.py:924` 的 docstring 写着
  「extras **由 B3F1 引入**——本 feature 无 extras，该条**为空断言**」·
  「它在 **B3F1 引入 extras** 后立即变为**实质断言**」。
  ⇒ **填充这两个占位正是 B3F1 的本职工作**。
- **实测的两处失配**（证据见 research D-06 · **2026-11-07 复核订正**）：
  1. `CONSTITUTION_DEPENDENCY_WHITELIST`（现为 4 个占位包名）覆盖不了真实闭包 —— 实测在**旧枚举语义**下
     extras 闭包为 **20** 个包，其中 **8** 个不在 4 个占位包名内（`email-validator` / `furo` / `objgraph` /
     `opentelemetry-configuration` / `psutil` / `setuptools` / `sphinx` / `tzdata`）⇒ **白名单子集断言变红**；
  2. G3 的 `dependency_closure(..., with_extras=True)` **过度近似**——它把**传递依赖自己的 extras**
     也展开进来，于是 `pydantic` 的 `email` extra 拉进 `email-validator`（**`Unlicense`**，不在白名单）。
     **⚠️ 订正两处细节**：① 这 8 个包**均未安装**（`email-validator` 等只是 `pydantic` 的 `email` extra 的成员，
     CI 未装该 extra）⇒ G3 既有的许可证断言落入其 `missing` 分支 ⇒ **`pytest.skip` 而非变红**
     ⇒ **实际变红的是第 1 项的白名单子集断言**；② **`dnspython` 不在闭包内**（它是 `email-validator` 的依赖，
     而 `email-validator` 本身未安装 ⇒ 递归到它时即取不到元数据）—— 故「`email-validator` 与 `dnspython` 二者」
     这一表述**不成立**（只有前者进闭包）。
     **这正是新门禁 G23「fail-on-missing」不可省略的理由**（G3 的 skip-on-missing 会让许可证断言被整体跳过）。
- **不动它的代价**：CI **从本 feature 上线起永久变红** ⇒ 违背宪法「feature 必须能独立通过门禁」· PR-4；
  而「放宽白名单把 ISC / Unlicense 加进去」被 **FR-018** 明令禁止 ⇒ **此路不通**。
- **本 feature 的处置**（**净效果 = 变严，不是变松**）：

  | 改动 | 性质 | 方向 |
  |---|---|---|
  | `CONSTITUTION_DEPENDENCY_WHITELIST`：4 个占位包 → **四个 extra 真实闭包的确切包名集合**（**12 个** · 有限 · 逐个列名 · 无通配符 · 无前缀匹配） | 常量填充（B2F1 已预告） | **更精确** |
  | extras 变体枚举：从「无差别剥离 / 保留 extras marker」→ **只枚举 freegraph 自身的 extras 变体**（传递依赖按其**基础依赖**展开） | 枚举语义修正（修正一个**过近似**缺陷） | **更正确** |
  | 许可证取值：G3 保持**既有的两条来源** + **skip-on-missing**（判据零改动）；**4 级证据链 + fail-on-missing** 由**新门禁 G23** 独立承担 | 不动 | — |

- **边界**：G3 的**判据句零改动**；**放宽判据**一处也没有；G23 作为**新门禁**独立实现严格口径，
  两者**并存不互斥**（G23 更严 ⇒ 总体门禁效果为严）。
  ⚠️ **已登记的差异**：G3 的许可证口径是**子串匹配**（`"MIT" in upper`）且白名单含 `"PSF"`，
  G23 是**精确 id + SPDX 表达式逐叶子**且白名单含 `"PSF-2.0"` ⇒ **`MIT-CMU` 在 G3 通过、在 G23 被拒**。
  **G23 严于 G3 ⇒ 总体效果为严**；该差异**登记为已知取舍**（与 B2F2 的「G5 / G20 署名头分两处维护」同类）。

**⇒ 请发起者在合入前追认此例外**（见 `tasks.md` 的 **T049**（阻断合入的追认任务）· 与人工验证记录同步）。

### Post-design 复核（Phase 1 设计完成后 · 2026-11-07）

**结论：与上方初判一致 —— 唯一例外仍是 G3。** 设计阶段的实测（research D-02 ~ D-06）
**新增**了两条需要登记的事实，但**没有**产生新的宪法冲突。

| # | 设计后复核项 | 结论 |
|---|---|---|
| 1 | 四个 extra 的闭包**逐个**经严格白名单判定 | ✅ 全绿（research D-02 表）· 无一需放宽 |
| 2 | `[otel]` 的 exporter 问题 | ⚠️ **已绕开**（取宪法原文的 api+sdk）· exporter 归 **B21F1**（research D-03）· **不违反**宪法（原则 IX 是 NON-NEGOTIABLE ⇒ 保住白名单是**服从**而非违反） |
| 3 | `[png]` 的后端 | ✅ `playwright`（唯一全绿方案 · research D-02）· 运行期零出站（裁定 7 · D-04）· **宪法 v1.5.0 已把包层白名单条收敛为确切包名 `playwright`** ⇒ 本 plan 的职责**只**是**核验**许可证标识与零出站，**MUST NOT** 另选后端（**2026-11-08 分析轮订正**） |
| 4 | SPDX 表达式的逐叶子判定 | ✅ 与 **FR-006 ④**（裁定 18）**逐字一致**；用 `packaging.licenses` 实现（research D-05）· **未**引入任何自制对照表 ⇒ 不违反裁定 18 |
| 5 | 门禁实现的落点（`harness/scripts/gates/`） | ✅ **不进发行包** ⇒ 不违反宪法「发布门禁」第 1 条（发行产物只含 `src/` 包代码与必要元数据） |
| 6 | 零出站夹具的位置 | ✅ **测试侧**工件 · 不在 `src/freegraph/**` 内 ⇒ 不违反 FR-009 ③（「不得安装任何出网拦截机制」） |
| 7 | 门禁工具链自身的第三方依赖 | ✅ 仅 `packaging`（开发期 · `Apache-2.0 OR BSD-2-Clause` ⇒ 两叶皆白名单）· 门禁代码本身**不进发行包** |
| 8 | 新增的 pytest 配置 | ✅ `testpaths` 把收集范围钉死在 `tests/` ⇒ 裁定 16 的「核心用例 = 全量测试套件」有了确定含义 · **不影响**既有两层测试 |
| 9 | **G3 占位填充** | ⚠️ **唯一例外**（同上文）· **判据句零改动** · **净效果变严** ⇒ 不违反 FR-018 · **待追认** |
| 10 | 既有门禁 G1–G20 的其余 19 条 | ✅ **判据零改动** · 只接线进 CI 矩阵（裁定 8） |
| 11 | 契约冻结面（C1–C27 / 门面 7 符号 / API 快照） | ✅ **零变更** · 只新增「挂载点」与「接线」（FR-011 / FR-012） |
| 12 | `THIRD_PARTY_NOTICES` | ✅ 本 feature **不引入**任何运行时第三方依赖（extras 的依赖**不进发行包**的必装依赖）⇒ **无需**登记新条目；但 §2 的 `Third-party runtime dependencies` 表的**说明文字**须同步「extras 已就位」（由 tasks 落实） |
| 13 | 发布门禁 | ✅ **未接入**（B24F1）· `publish.yml` **零改动** |
| 13b | 第三方**品牌资产**检查（原则 IX 第三条） | ✅ 并入 **G30 判定第 6 项**（不新增门禁编号 ⇒ 裁定 4 的 G21–G30 连续性不受影响）· 立项书 §9.1 门禁 2 的「无第三方商标资产」此前**零检查** · **2026-11-08 分析轮订正**：该段的两个子域（品牌色值 / "Approved copy" 文案）已钉死**具名清单 + 来源标记**（载体 = G30 **判定第 6 项**本身），清单为空时 MUST NOT 记作「已自动判定」⇒ **待取证**（见 spec FR-021 ①「判定分工」/ SC-016 限定语） |
| 13c | 验收环境的**运行时反向断言**（FR-005 ③） | ✅ 并入 **G22 的场景 ②**（同一 venv 额外装 `langchain-core` ⇒ **声明级 + 导入级断言**（③①）⇒ 断言 `sys.modules` 从未出现 `langchain`/`langchain_core`/`langgraph` + 零出站）· 立项书 §9.2 断言③ / D12「两套断言」之第二套 · **⚠️「跑最小图」的运行期断言（③②）不在本 feature 交付** ⇒ 延后至 **M2**（见 **R-5**） |
| 14 | 门禁对**用户**的影响 | ✅ 只约束 freegraph **自身**（裁定 6 · D12）· 用户脚本装什么**不受门禁约束** |

**复核后新增的登记项（不构成冲突）**

> **📌 ID 命名空间说明（2026-11-08 分析轮订正 · 消解 ID 撞车）**：本表的编号为 **plan 级「登记项 R-n」**，
> **与 `research.md` 的「遗留与登记 DR-n」是两个不同的序列** ⇒ 引用时 MUST 带限定语
> （「plan 登记项 R-4」/「research DR-4」）。**本表的 R-4 已被宪法 v1.6.0 修订记录引用 ⇒ MUST NOT 改名。**

| 项 | 内容 | 归属 |
|---|---|---|
| **R-1** | `opentelemetry-exporter-otlp` 的合规解法（`certifi`/MPL-2.0 与 `protobuf` 散文式标识） | **B21F1** |
| **R-2** | 既有 G3 与新 G23 的许可证口径差异（`MIT-CMU` 在 G3 通过 / 在 G23 被拒） | **已知取舍** · G23 更严 ⇒ 总体为严 |
| **R-3** | 文档产出 ≈ 1,200 行，超出立项书的 1,100 行估算 | **登记，不改立项书**（沿用 B2F2 的「行数口径」做法） |
| **R-4** | **宪法「质量门禁 3 / 4 / 5」三项在本 feature 不适用** —— 三者**共享同一根因**：「MVP 验收基线的跑通需要内核运行时，而内核运行时按 立项书 §6.2 属 **M2**（固定脚本最小交付集 = B6F1 / B7F2 / B7F3 / B8F1 / B22F1 / B23F1）；本 feature 属 **M0 地基**、**不交付内核功能**」⇒ ① **门禁 3**（MUST 包含 **C4** 与 **C8**）⇒ 本 feature 只落**挂载点**并**明确标记为「未落地」**（FR-011 ② · 契约 G29 ③）；② **门禁 4**（**fake 模型跑通验收基线的一轮**）⇒ 内核运行时未接线（`StateGraph` 的四个方法一律 `raise NotImplementedError`）⇒ 以 **G29 ②** 的「退出码 ∈ **{0, 1, 2}**，且**退出码 1 且失败全部源于 `NotImplementedError`** 时判为**环境未就绪**（通过）」作**部分落地** —— **⚠️ 退出码口径订正（2026-11-07 实测）**：验收脚本集的退出码 **2 只在 freegraph 不可导入时**出现（`except ImportError` 分支）；而 CI 中 freegraph **已安装**（ci-matrix §2 步骤 5）⇒ 三个脚本 import 成功 ⇒ 走到用例体并因 `NotImplementedError` 被记为**断言失败** ⇒ **退出码为 1**（**实测**：freegraph 可导入时三者退出码**全为 1**；不可导入时才是 2）；③ **门禁 5**（原则 V 同款：人工验证记录**含真实模型一轮**）⇒ 无图可跑 ⇒ 以 T048 的**五段式记录** + 零出站 / 断网全绿实测证据覆盖 | **M2 / M4 承接**（B7F2 建 fake 注入 · B25F1 双跑验收 · 里程碑依据 立项书 §6.2）· **三条一并由 `tasks.md` **T057** 发起者追认（阻断合入）**（与 T049 同级 · **2026-11-08 分析轮订正**）· **宪法本身不变**（偏离登记，**不改宪法**；依 裁定 ②）· **门禁 3 / 4 / 5 的判据本身一字未改**（偏离登记，**不改判据**；依 裁定 ②）· **⚠️ 宪法层面的结构性张力（已由宪法 v1.6.0 消解 · 2026-11-08 发起者批准）**：宪法「每个特性在合入前 MUST 全部通过」与「M0 feature 不具备跑验收基线的能力」之间的张力，**已由宪法 v1.6.0 新增的「质量门禁的分阶段落地与发起者追认」章节确立通则**（窄口径适用范围 + 「偏离登记 + 发起者追认」双要件 + 四条红线 + 登记与复核）⇒ 本 feature 的偏离登记与追认即依该通则执行 ⇒ **「宪法尚无通则 ⇒ 需另起一次 MINOR 修订」这一登记项已消解** |
| **R-5** | **FR-005 ③②（运行期 · 最小图）延后至 M2** —— B3F1 属 M0 地基，内核运行时**尚未存在**（`src/freegraph/_stategraph.py` 的四个方法一律 `raise NotImplementedError`）⇒ 原口径**不可执行**（硬写 ⇒ CI 永久红，违反 PR-4）⇒ B3F1 只交付 **FR-005 ③①（声明级 + 导入级）** | **spec 裁定 22**（spec 侧**已补齐** · `/speckit.clarify` 第 4 轮）· **M2 承接**（B6F1 建图 / B7F2 compile / **B7F3** invoke · 里程碑依据 立项书 §6.2）· **红线不放宽**（③① 已是可判定形式 · FR-018 无豁免） |

**⇒ Constitution Check 通过（附一处待追认的例外 —— 既有门禁 G3 的占位填充）。**
**⇒ 另有两项经实测澄清的 CI 阻断级缺陷已在 spec 裁定 22 之外单独订正**（不改变 Constitution Check 的结论）：
① **G29 ② 的退出码口径**（原「∈ {0, 2}」在 CI 条件下**必然失败** ⇒ 7/7 作业全红，违反 PR-4）⇒ 改为 {0, 1, 2} + 按失败来源细分（见 **R-4**）；
② **G21 的「未安装 ⇒ 判失败」规则** 与 ci-matrix 的非 Linux 子集**互斥**（非 Linux 作业不装 extras ⇒ G21 必红）⇒ **全部 7 个作业**均装齐四个 extras 的依赖（见 ci-matrix §2 步骤 5.5）。
③ **CI 安装步骤缺 venv** ⇒ `uv pip install` 在 runner 上直接失败（`No virtual environment found`，退出码 2）⇒ 补 `uv venv --python <档位>` 步骤并全用显式 `--python .venv`（**venv 目录** · 跨平台 · 见 ci-matrix §2.0）（见 ci-matrix §2 步骤 3.5–5.5）。

---

## Project Structure

### Documentation (this feature)

```text
specs/b3f1-scaffold-ci-gates/
├── plan.md                    # This file (/speckit.plan command output)
├── research.md                # Phase 0 output —— D-01..D-15 决策 + 实测证据
├── data-model.md              # Phase 1 output —— 门禁的静态工件模型
├── quickstart.md              # Phase 1 output —— 可照抄的验证手册
├── spec.md                    # 规格（已完成四轮澄清 · 25 条裁定 · 13 条澄清问答）
├── checklists/
│   └── requirements.md        # 规格质量清单（16/16）
├── contracts/
│   ├── architecture-gates.md  # G21–G30 的判据定义（**新增门禁的权威**）
│   ├── dependency-gate.md     # 依赖门禁契约（黑名单 · 许可证证据链 · extras 变体语义）
│   ├── layer-registry.md      # 层注册表（**机器可读** · FR-008 ②）
│   └── ci-matrix.md           # CI 矩阵契约（7 作业 · runner 钉死 · 分层）
└── tasks.md                   # Phase 2 output（/speckit.tasks —— 本命令不生成）
```

### Source Code (repository root)

```text
src/freegraph/                       # 既有（**本 feature 不改一个字节** —— 判据零改动 + 零契约变更）
├── __init__.py
├── graph.py                         # 跨层单元（公开 API 门面 · L1–L3 · ARCH-1 唯一例外）
├── _stategraph.py
├── _primitives.py
├── py.typed                         # PEP 561（既有 · FR-002 已满足）
└── contracts/                       # L1 契约层
    └── ...

harness/scripts/                     # 既有工具（3 个 · 本 feature 为其补签名头）
├── audit_feature_drafts.py
├── check_dist_purity.py             # 发行产物纯度门禁（发布流水线用 · B24F1 接入）
├── fetch_docs.py
└── gates/                           # ★ 新增 —— 10 条新门禁的可独立执行检查
    ├── _gatekit.py              #   共享判定库（AST / 许可证证据链 / SPDX 表达式 / 归因 / 报告格式）
    ├── gate_G21_dependencies.py     #   G21 依赖闭包黑名单（声明级 · 全部 extras 变体）
    ├── gate_G22_isolated_env.py     #   G22 隔离环境断言（venv + sys.modules）
    ├── gate_G23_licenses.py         #   G23 许可证白名单（4 级证据链 · 5 个精确 id）
    ├── gate_G24_config_layer.py     #   G24 配置层（LANGSMITH_* / LANGCHAIN_* / 零环境变量）
    ├── gate_G25_import_graph.py     #   G25 导入图单向（ARCH-1）
    ├── gate_G26_network_static.py   #   G26 网络静态扫描
    ├── gate_G27_zero_egress.py      #   G27 零出站动态断言（socket 夹具 · 只观测不阻断）
    ├── gate_G28_offline_equiv.py    #   G28 断网等价性（Linux 网络命名空间）
    ├── gate_G29_contract_carrier.py #   G29 契约门禁载体（只读基准 diff + C4/C8 挂载点）
    └── gate_G30_attribution.py      #   G30 全仓署名头

harness/proposals/                   # 既有（**发行与文档**跨层单元 · 层 = 「—」· 本轮登记进
                                    #   contracts/layer-registry.md §1 · 立项书 §5.1 的第三个跨层单元）

THIRD_PARTY_NOTICES                  # 既有（**T050** 同步其 §2「第三方运行时依赖」表的说明文字 · 原则 X）

tests/
├── contracts/                       # 既有（G1–G13 · **判据零改动**；仅 G3 常量填充）
├── facade/                          # 既有（G14–G20 · 零改动）
└── gates/                           # ★ 新增 —— 门禁的测试与反向用例
    ├── __init__.py
    ├── conftest.py                  #   路径基线 + socket 夹具 + 隔离副本夹具
    ├── test_gates.py                   # 单一文件承载 10 条门禁的**正向断言 + 反向用例**（tasks 已定）
    └── data/
        └── offline_exclusions.txt   #   断网排除清单（**逐条理由** · FR-010 ④）

.github/workflows/
├── publish.yml                      # 既有（发布流水线 · 本 feature **不接入**）
└── ci.yml                           # ★ 新增 —— 7 作业矩阵 + 逐条门禁调用

harness/verification/B3F1/
└── manual-verification.md           # ★ 新增 —— 人工验证记录（含分支保护设置步骤）
```

**Structure Decision**:

- **门禁代码落在 `harness/scripts/gates/`**（而非 `src/freegraph/`）—— 理由：门禁是**工程设施**，
  **跨层单元**（层 = 「—」），且 **MUST NOT** 进入发行包（发布门禁：发行产物只含 `src/freegraph/` +
  必要元数据）。放进 `src/` 会污染发行包并违反 FR-002 的 `src/` 布局语义。
  （`harness/` 已在 `pyproject.toml` 的 sdist `exclude` 中，且 `check_dist_purity.py` 已断言其不入产物。）
- **门禁判定逻辑集中在 `_gatekit.py`，10 个门禁各一个薄壳** —— 薄壳只做「参数解析 → 调用判定 →
  打印报告 → 退出码」，**重活全在共享库** ⇒ ① 满足 FR-016「逐条调用 + 退出码即判定」；
  ② 避免「同一判据两处实现」（裁定 8 的第三条理由）；③ 10 个薄壳 ≈ 250 行，落在 620 行预算内。
- **测试落在 `tests/gates/`**，与既有的 `tests/contracts/` · `tests/facade/` **平级** ——
  沿用仓库既有的「一层一个测试目录 + `conftest.py` 提供路径基线」惯例。
- **层注册表与断网排除清单是**仓库内的纯文本工件**（入库比对）—— 沿用 B1F1 / B2F2 的
  `specs/<feature>/contracts/*.md` + 机器标记（G12 的既有手法）惯例；断网排除清单因需被 CI 逐条读取，
  放在 `tests/gates/data/`（**与测试同址** ⇒ 改清单必然改测试同提交）。
- **共享库命名 = `_gatekit.py`（不是 `_gatesupport.py`）** —— 仓库既有 `tests/facade/_gatesupport.py`
  （B2F2 落 · 555 行），同名会让「两份不同内容的 `_gatesupport`」共存 ⇒ 人与 AI 代理都易误 import。
  故新共享库改名 `_gatekit.py`（`harness/scripts/gates/_gatekit.py`），**全 feature 文档一致**。
- **⚠️ 已登记的判据重叠（不构成冲突 · 第三次「同一判据两处维护」）**：既有 `tests/facade/_gatesupport.py`
  已含 `import_violations` / `env_and_io_violations` / `signature_header_violations` / `compat_matrix_rows`
  / `layer_segment` 等实现，与本 feature 的 **G24 / G25 / G29 / G30** 判据**大面积重叠**。
  **方向是「更严」而非「更松」**（既有 = 硬编码文件清单的子集判据；新增 = 注册表驱动 / 全仓域 / 更细的形态覆盖），
  故**总体门禁效果为严**。处置：**登记，不合并**（既有文件属 B2F2 的冻结实现，本 feature 不改它）——
  与 B2F2 的「G5 / G20 署名头分两处维护」同类。**新增两条硬约束**：
  ① **环境变量读取 MUST 覆盖 `from os import environ/getenv/environb` 的导入形态**（与既有实现同口径 · tasks T010）；
  ② **G29 的 README 矩阵比对 MUST 引用既有 G8 / G19，MUST NOT 重复实现**（裁定 8 第三条理由 · tasks T027）。
- **⚠️ 已登记的判据重叠 · 第二处（2026-11-08 分析轮订正 · 发起者已决议 · 本 feature 不改）**：
  `harness/demo/acceptance.py` 的 `EgressProbe`（第 138–181 行）是**仓库内第三份出站归因实现**，
  其规则为「**调用栈中出现 `freegraph/` 包路径 ⇒ 框架出站**」——
  正是**裁定 19 明确否决**的旧口径（会把「用户出站」误判为「框架出站」⇒ 门禁假红）。
  它与本 feature 的 `_gatekit.attribute_egress`（裁定 19 口径）**相反**。
  **后果**：若人工验收编排器（`acceptance.py`）与 G27 同时出现在**同一份**人工验证记录里
  ⇒ 会出现**两套相反口径**的零出站证据。
  **处置（2026-11-08 发起者决议）**：**登记，不改** —— `acceptance.py` 不在宪法原则 III 的只读清单内，
  但属 **M4** 的验收资产 ⇒ 本 feature 改它会扩大范围；**新增两条硬约束**：
  ③ **本 feature 的零出站证据 MUST 一律取自 `_gatekit`（裁定 19 口径）**
  ⇒ **MUST NOT** 引用 `acceptance.py` 的 `EgressProbe` 结果（tasks **T048**）；
  ④ **`acceptance.py` 的退出码断言归 B25F1**（双跑验收）⇒ 本 feature 只登记不判定（tasks **T027 ④**）。
  **统一到 `_gatekit` 的落点 = B25F1**（与 B2F2 的「G5 / G20 署名头分两处维护」同类取舍 · 已登记，不合并）。

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **对裁定 8 的唯一例外**：既有门禁 **G3** 的**占位常量与 extras 枚举语义**被填充 / 修正（G3 的**判据句逐字未动**） | ① G3 **自己的 docstring 预告**「extras 由 B3F1 引入……它在 B3F1 引入 extras 后立即变为实质断言」（`tests/contracts/test_architecture.py:924-931`）；② 实测：G3 的 `with_extras=True` **过度近似**（把 `pydantic` 的 `email` extra 也展开）⇒ 旧枚举语义下 extras 闭包为 **20** 个包、其中 **8** 个不在 4 个占位包名内 ⇒ **白名单子集断言变红**（**2026-11-08 分析轮订正**：**实际变红的是白名单子集断言**；「许可证断言」实为 `pytest.skip`（那 8 个包**均未安装**）⇒ 不构成变红原因；且 **`dnspython` 不在闭包内**（`email-validator` 未安装 ⇒ 递归到此即止）⇒ 只有 `email-validator`（Unlicense）进闭包）；③ 不动的代价 = **CI 从本 feature 上线起永久变红**（违反 PR-4「feature 必须能独立通过门禁」）；④ 「把 ISC / Unlicense 加进白名单」被 **FR-018** 明令禁止 | **替代方案 A：不动 G3** ⇒ CI 永久红，且**无法**通过合法手段变绿（放宽白名单被 FR-018 禁止）⇒ **不可行**。<br>**替代方案 B：放宽 G3 的白名单**（加 ISC / Unlicense）⇒ **直接违反 FR-018 与宪法原则 IX（NON-NEGOTIABLE）** ⇒ **不可行**。<br>**替代方案 C：放弃 extras**（只交付基础安装）⇒ **违反 FR-001 / FR-004**（extras 划分是本 feature 的主交付物之一）⇒ **不可行**。<br>**替代方案 D：把 extras 的依赖声明成「无 marker 的顶层依赖」** ⇒ 破坏 PEP 621 的 extras 语义，用户无法选择性安装 ⇒ **不可行**。<br>**采用的处置**：**判据句零改动 + 净效果变严**（白名单从 4 个宽泛占位 → **12 个确切包名**；枚举从过近似 → 精确变体）。**待发起者追认**。 |
| **既有门禁 G3 与新门禁 G23 的许可证口径不同**（G3 = 子串匹配 + `"PSF"`；G23 = 精确 SPDX id + 表达式逐叶子 + `"PSF-2.0"`）⇒ `MIT-CMU` 在 G3 通过、在 G23 被拒 | 裁定 8 禁止改 G3 的判据；G23 是**新门禁**，可独立实现 spec 要求的严格口径（裁定 17/18） | **替代方案：统一口径** ⇒ 必须改 G3 ⇒ 与裁定 8 冲突（本 feature 已在 G3 上登记**唯一一处**例外，不宜再扩大）。<br>**差异方向**：**G23 严于 G3** ⇒ 总体门禁效果为严，**不存在漏判**（`MIT-CMU` 这类变体被 G23 拦住）。<br>**登记为已知取舍**（与 B2F2 的「G5 / G20 署名头分两处维护」同类）。 |
| **文档产出 ≈ 1,200 行**，显著超出立项书 B3F1 的「1,100 行」估算 | 立项书的估算把「7 项质量门禁」当作**一个整体**计；实测它需要 **10 条独立编号**的门禁 + 1 份共享判定库 + 4 份契约（架构门禁 / 依赖门禁 / 层注册表 / CI 矩阵） | **替代方案：压缩文档**（合并契约 / 删层注册表）⇒ 门禁的判据**失去唯一权威** ⇒ 违反 FR-016 ①（失败须指名规则编号）与 FR-008 ②（层归属须**可机读**）。<br>**处置**：**登记，不改立项书**（沿用 B2F2 的「行数口径」做法）；**不压缩**。 |
| **宪法「质量门禁 3 / 4 / 5」三项在本 feature 不可达成**（**C4/C8** · **fake 模型轮** · **真实模型一轮**） | 三者**共享同一根因**：MVP 验收基线的跑通需要**内核运行时**，而内核运行时按 立项书 §6.2 属 **M2**（固定脚本最小交付集 = B6F1 / B7F2 / B7F3 / B8F1 / B22F1 / B23F1）；本 feature 是 **M0 地基** feature、**不交付内核功能**（spec §8）⇒ **任何 spec 设计都无法在本 feature 满足这三条** ⇒ 本 feature 以「**偏离登记 + 发起者追认**」处置（与 T049 同级） | **替代方案 A：硬写进去**（例如让 G29 把「环境未就绪」当「通过」而**不登记**）⇒ **静默稀释宪法** + 门禁语义被扭曲（`NotImplementedError` 被当成成功）⇒ **不可行**。<br>**替代方案 B：写一条永久红的 CI** ⇒ 违反 PR-4「feature 必须能独立通过门禁」⇒ **不可行**。<br>**替代方案 C：改宪法正文**（把这三条写成「内核未落地时免检」）⇒ 依 **裁定 ②**「**MUST NOT** 改宪法」⇒ **不可行**（且属宪法 Governance 的修订流程）。<br>**已走的合法路径（2026-11-08 发起者批准）**：**不碰门禁判据**，改为在**宪法新增一条流程性通则**（「质量门禁的分阶段落地与发起者追认」· **v1.6.0**）—— 它**只**规定「某条门禁物理不可达成时如何合法地登记与追认」，**MUST NOT** 削弱任何红线（原则 I / II / IX 的红线 MUST 在每个 feature 落地）⇒ 与「替代方案 C」的本质区别 = **不写「免检」，写「登记 + 追认 + 具名承接方」**。<br>**采用的处置**：**偏离登记（R-4）+ 发起者追认（T057 · 阻断合入）+ 承接路径写入目标 feature 的提示词初稿**（裁定 22 既有机制）⇒ **红线与门禁判据一律不放宽**（FR-018）。 |
