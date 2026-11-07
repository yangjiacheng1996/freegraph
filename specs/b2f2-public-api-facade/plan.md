# Implementation Plan: 公开 API 门面 `freegraph/graph.py`（7 符号导出面）+ API 签名快照冻结

**Branch**: `b2f2-public-api-facade` | **Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b2f2-public-api-facade/spec.md`

**feature ID**: `B2F2`（M0 地基 · 31 个 feature 中的第 3 个 · 前置 **B1F1** / **B2F1**）

---

## Summary

交付 freegraph 的**唯一公开 API 门面** `freegraph/graph.py`，并用**签名快照测试**把它的对外形状钉死：

- **导出面恰 7 个符号**：`StateGraph` / `START` / `END` / `Command` / `Send` / `interrupt` / `RunConfig`
  —— 两处口径同时成立（`__all__` 集合相等 **且** 模块内公开名集合相等）；
- **门面的实现体全部下沉**：`StateGraph` / `Send` / `interrupt` 三个**外壳**住在门面之外的
  私有模块（`_stategraph.py` / `_primitives.py`），门面文件内**零类体 / 零函数体**
  （ARCH-4 · 裁定 3）；
- **API 签名快照**：把 7 个符号的**完整调用签名**（参数名 / 缺省值 / 关键字-only 标记 /
  参数与返回注解）+ 常量字面值 + 公开属性序列化为**稳定可复现**的纯文本并入库比对；
  任何漂移在**测试**里**显式可见**（diff 呈现、须人工确认；**CI 流水线的挂载归 B3F1**）；
- **顶层包惰性**：`import freegraph` **不连带加载**门面与契约层（D1 决议附加约束 · ARCH-2）——
  用**子进程 `sys.modules` 快照**判定。

本 feature **零行为**：四个构建 / 编译方法与 `interrupt` 一律抛内置 `NotImplementedError`
（消息点名归属 feature），`StateGraph(schema)` **可构造但未接线**。
验收基准脚本 `harness/demo/target.py:122` 的那行 import 从本 feature 起**必须能成功执行**——
但**脚本本身仍跑不通**（它需要 6 个 feature 齐备），本 feature **MUST NOT** 宣称脚本可跑通。

技术上，全部实现由四个标准库机制承载：`dataclasses` 的**冻结数据类**（`Send`）·
`inspect.signature` 的签名渲染 + **自定义注解规范化**（快照生成）· `ast` 的架构断言 ·
`subprocess` 的模块加载面断言。**基础安装零第三方运行时依赖**（`dependencies = []`，
沿用 B1F1 / B2F1 与宪法 v1.2.0 的结论）。

**冻结面（后续 28 个 feature 引用、不可轻改）**——门面导出面的**清单**与**签名**分属两份契约：

| 冻结项 | 内容 | 权威 |
|---|---|---|
| **导出面清单** | **恰 7 个**符号（5 个门面自有 + 2 个契约层转出） | [`contracts/facade-api.md`](./contracts/facade-api.md) §0（**手写**） |
| **完整签名** | 7 个符号的调用签名 / 字段 / 常量值 / 公开属性 | `contracts/public-api-snapshot.txt`（**机器生成**） |
| **快照格式** | 条目语法 · 排序 · 注解规范化 6 条 · UTF-8/LF | [`contracts/snapshot-format.md`](./contracts/snapshot-format.md) |
| **门禁 G14–G20** | 零实现体 / 导出面两处相等 / 快照比对 / 依赖卫生 / 模块加载面 / 兼容矩阵覆盖 / **署名头（门面侧）** | [`contracts/architecture-gates.md`](./contracts/architecture-gates.md) |

> **为何清单与签名分离**：若门禁的「期望的 7 个符号」从**生成的**快照解析，判定就成了
> 「代码 → 快照 → 快照 vs 代码」的**循环论证**（research D-07）。

---

## Technical Context

**Language/Version**: Python ≥ 3.11（`pyproject.toml` 的 `requires-python = ">=3.11"`；
本机开发环境实测 CPython **3.12.3**，隔离验收另在 CPython 3.11.x 上实测——沿用 B1F1 / B2F1 的双档口径）。
**typing 构件上限 = 3.11**（宪法「运行时环境基线」）：MUST NOT 使用 `TypeAliasType`(3.12) /
`override`(3.12) / `ReadOnly`(3.13) / `TypeIs`(3.13) 或 PEP 695 `type` 语句——由门禁 **G9** 静态断言把关。
本 feature 用到的 typing 构件**全部 ≤ 3.11**，**无需** `typing_extensions` 兜底：
① **门面自有代码**（`graph.py` / `_stategraph.py` / `_primitives.py`）实际用到的 =
`Self`（3.11+ · `StateGraph` 四个方法的返回注解）· `Any` · `Callable`；
② **快照需渲染的**（契约层转出类的注解）另含 `Literal` / `ClassVar` / `Mapping` /
`Sequence`（3.8+）· `dataclass`（3.7+）——它们**不出现在门面自有代码里**，
只作为快照的**渲染对象**。

**Primary Dependencies**: **无**（基础安装零第三方运行时依赖，`dependencies = []` 沿用现状，
本 feature **不改** `pyproject.toml` 的依赖声明）。
开发期工具（**不进发行包**）：`pytest`（实测 7.4.4 / 9.2.0）+ `mypy`（静态类型检查，**可选**——
本机未安装时相关用例 `skip`，口径与 B2F1 一致）。

**快照更新入口的形态（裁定 · research D-09 · spec FR-011 ①）**：**`pytest --update-api-snapshot`**
—— 一个 pytest 命令行开关（`pytest_addoption` + `action="store_true"`），**默认关闭**；
常规执行 pytest **MUST NOT** 改动快照文件；更新后的快照 MUST 经**人工 review diff** 后方可提交。
落点：`tasks.md` T004（注册开关）· T024 / T031（生成与入库）· `contracts/snapshot-format.md` §4 / §6。

**Storage**: N/A —— 本 feature 无持久化。快照文件是**仓库内的纯文本**（入库比对），
不是运行时产物。

**Testing**: pytest（开发期实测 7.4.4）+ 标准库 `ast` / `subprocess` / `inspect` / `dataclasses` /
`difflib`（快照 diff）。
**需要子进程的断言**（顶层包惰性 · 门面的模块加载面）**必须在子进程中执行**——测试进程自身已导入
pytest，同进程 `sys.modules` 不可作依据（沿用 B1F1 的判定口径）。

**Target Platform**: 任意 CPython 3.11+ 平台（Linux / macOS / Windows）。本 feature 无平台特定代码、
无 C 扩展、无文件 IO 契约、无网络。

**Project Type**: library（Python 库；发行名 = 导入名 = `freegraph`，门面与契约层均为
**主发行包内的子模块**，不拆独立发行包 —— D1 已拍板）。

**Performance Goals**（= **FR-019 / SC-018**）：隔离 venv 中 `import freegraph.graph` 的
**墙钟 < 120 ms**；**计时口径（唯一）**——以 `time.perf_counter()` 在 import 语句**前后**取差、
**不含解释器自身启动**、**暖机后 best-of-3**、**基准 CPython 3.11.x**（立项书 §3.5 的 CI 最低档 ·
实测命令见 `tasks.md` T040）——基线实测（2026-11-07 · CPython 3.12.3 · 暖机 best-of-3）：
`import freegraph.contracts` = **50–63 ms**；新增三个零 I/O 模块后仍须在预算内。
门面**只有形状、没有执行路径**——本 feature **无**吞吐 / 延迟指标。

**Constraints**:
- **零**第三方运行时依赖（基础安装闭包 MUST 为空集）；**不得**引入 pydantic 等可选依赖
- **typing 构件上限 = 3.11**（见上）
- **门面零实现体**（AST 判据 · FR-006）——门面的具体实现体 MUST 位于下层模块（裁定 3）
- **顶层包惰性**：`freegraph/__init__.py` MUST **NOT** 导入门面（D1 决议附加约束 · FR-013）
- 门面**零**环境变量读取、**零**出站 / 文件 I/O、**零** `langchain*` / `langgraph*` / `langsmith` import
  （FR-014 · 门禁 G17）
- 门面**不得**横向依赖 L4（持久化）/ L5（可观测）（ARCH-2 · 门禁 G18）
- **契约层的 18 符号面 MUST NOT 改变**（`Send` / `interrupt` **不进**契约层 · 裁定 2 · SC-015）
- **快照不得**含内存地址 / 时间戳 / 哈希序 / 版本号（可复现 · FR-010 ②）
- 每个新源文件携带署名头（FR-017 / 宪法原则 X）
- 发行产物须带 `py.typed`（沿用现状，顶层一个即覆盖全部子包）

**Scale/Scope**（**估算值 · 实现后回填**）：立项书 §5.2 的 B2F2 估「**560 行**（实现 260 / 测试 300）· 3 人日」。
本 feature 的**实现**预估与该估算同量级（三个新模块 ≈ 200–260 行：门面 ≈ 60 · 外壳 ≈ 120 · 文档字符串占多数）；
**测试**预估**显著超出**（300 行）：**7 条**新增门禁（G14–G20 · 各带**自检**）+ **18** 条成功标准的逐条断言 +
快照生成 / 比对 / 可复现 / 更新入口 / 自检五组用例。
> **行数口径（避免与立项书 §5.2 打架）**：立项书的「560 行」= 实现 260 + 测试 300（**不含文档行数**）；
> 本 feature 的**文档产出另计**（spec + plan + tasks + research + data-model + quickstart +
> 三份契约）。**登记（不改立项书）**：后续 feature 的估算宜按「实现 1 : 测试 1.5~2」取值——
> B2F1 的实测比值是 **3.8 : 1**（契约冻结面天然门禁密度最高），本 feature 预计落在 **2 : 1** 上下。
> 公开符号面 **7 个**（门面自有 5 + 契约层转出 2）；**新增门禁 7 条**（G14–G20）。
>
> **✅ 实现后的行数实测（2026-11-07 回填 · 登记，不改立项书）**：
>
> | 类别 | 立项书估算 | **实测** | 落点 |
> |---|---|---|---|
> | **实现** | 260 | **193 行** | `src/freegraph/graph.py` 45 · `_stategraph.py` 89 · `_primitives.py` 59（文档字符串占多数） |
> | **测试** | 300 | **2 195 行** | `tests/facade/` 7 个文件：`conftest.py` 105 · `_gatesupport.py` 525 · `_snapshot_tools.py` 380 · `test_facade.py` 349 · `test_api_snapshot.py` 309 · `test_facade_gates.py` 511 · `__init__.py` 16 |
> | **文档** | 不计入 | **3 749 行** | `specs/b2f2-public-api-facade/**`（spec / plan / tasks / research / data-model / quickstart / 3 份契约 / 清单）+ `harness/verification/B2F2/manual-verification.md` + 验收脚本 `acceptance.py` 661 行（**另计**，属 harness 产物） |
>
> **实测比值 = 实现 1 : 测试 11.4 : 1** —— **远高于**本 plan 的「2 : 1」预估，也高于
> B2F1 的 3.8 : 1。**偏差归因**（登记，供后续 feature 的估算取用）：
> ① **7 条新增门禁各带自检**（8 条自检）+ **18 条成功标准**逐条落断言；
> ② 门禁**辅助模块**（`_gatesupport.py` 525 + `_snapshot_tools.py` 380 = **905 行**）
> 占测试行数的 41% —— 这部分是**可复用的判定基建**，不是「一次性断言」；
> ③ **快照渲染器**须逐条实现注解规范化 6 条 + dataclass 取数 4 条（D-21）+
>   文本层规则 8 条 ⇒ 本身即是一个带冻结契约的子模块。
> ⇒ **登记（不改立项书）**：门禁密度型 feature 的估算宜按「**实现 1 : 测试 8~12 : 1**」取值，
> 并把**门禁辅助模块**单列（它们是**跨 feature 可复用**的资产）。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 要求 | 本 feature 的满足方式 | 判定 |
|---|---|---|---|
| **原则 I** 零 LangSmith 依赖 | 依赖树无 `langsmith` / `langchain*` / `langgraph*`；不读 `LANGSMITH_*` / `LANGCHAIN_*`；不向 `*.langchain.com` / `mermaid.ink` 出站 | FR-014 ①②③（零第三方 import、零环境变量、零出站 / 零 I/O）；门禁 **G17**（**两档** · research D-22）静态扫描门面的三个模块；**零新增第三方依赖** ⇒ `THIRD_PARTY_NOTICES` 无需新增登记（FR-017） | ✅ 通过 |
| **原则 II** 内核纯净 | 核心层不 import langchain；状态 schema 用标准 `TypedDict`，**不得自带并行状态类型体系** | FR-014 ① + 门禁 G17；`schema` 注解用 `Any` 且**明确不新造**状态类型体系（C1 的类型体系归 **B4F1** 收紧）——**不引入**并行体系 | ✅ 通过（**C4 / C8 回归测试子项不适用**——本 feature 零运行时，回归测试分别归 **B5F2** / **B8F1**，已显式记录、非忽略） |
| **原则 III** 验收契约优先 | `harness/demo/target.py` 原样可跑；7 项 MUST 同名同签名 | FR-002 / FR-007 / FR-008 逐字冻结**第 1–6 项**的同名同签名（`freegraph.graph` 导出 `StateGraph` / `START` / `END` + `START='__start__'` / `END='__end__'` · `StateGraph(schema)` · `add_node(name, fn)` + `alias` · `add_edge(src, dst)` 链式 · `add_conditional_edges(src, path_fn, path_map)` 双形态 · `compile()` 无参可调用）；**第 7 项**（`invoke` 返回完整状态）属 **B7F3**，本 feature **不实现**（裁定 7）。**MUST NOT** 修改 `target.py`（FR-016） | ✅ 部分适用（**第 1–6 项的签名面**在本 feature 冻结并入快照；**脚本原样可跑**须待运行时交付 ⇒ 登记为「已知偏离」，见下） |
| **原则 IV** 可诊断性是一等功能 | 失败可被上层结构化读取，而非只能解析日志字符串 | FR-009 的未接线异常**类型固定**（内置 `NotImplementedError`）+ **消息点名归属 feature** ⇒ 用户一眼看出「还没实现」而非「内核坏了」；spec §4 统一文案格式 + `test_facade.py` 的消息正则断言 | ✅ 通过 |
| **原则 V** 人工验收是最终验收标准 | 结束须有人工验证记录（环境 / 步骤 / 实际输出 / 结论 / 遗留问题） | FR-015（人工记录落 `harness/verification/B2F2/manual-verification.md`，**五段式**，第 3 节 MUST 贴**真实输出**，未实跑项 MUST 记入遗留问题）；`quickstart.md` 给出可复制步骤 | ✅ 通过（**「双跑」子项不适用**——无运行时、无模型调用，已显式记录、非忽略） |
| **原则 VI** 规格驱动开发 | 有 proposal 与 spec，再进 tasks 与实现 | spec（**19 FR / 18 SC** · **12 条裁定 + 12 条澄清问答 Q1–Q12**）→ 本 plan → tasks → 实现 | ✅ 通过 |
| **原则 VII** 职责边界与内核契约 | 不做 freechain 能力；契约清单以 Q8 **C1–C27** 为唯一权威 | ① **不实现**任何行为（构建 / 编译 / 执行 / 原语语义分别归 B6F1 / B7F2 / B7F3 / B9F1 / B10F1 / B11F1）；② **不改动**契约层的 18 符号面与任何已冻结字段 / 方法集（裁定 2 · SC-015）；③ 门面导出面的**清单**与**签名**分属两份契约（`facade-api.md` / 快照文件），与契约层的 `public-api.md` **各管一面、不重复**；④ **不做** freechain 侧适配（未来事项） | ✅ 通过 |
| **原则 VIII** 证据与术语纪律 | 事实性结论带来源标记；术语准确 | `research.md` §6 列出本 feature 引用的**全部**上游位置（`langgraph 1.2.11` 逐条实测命中 ✓）；术语统一：「导出面」「公开名」「未接线」「快照」「清单」；上游版本随引用标注（**换版本 MUST 重新核实**，MUST NOT 凭记忆沿用） | ✅ 通过 |
| **原则 IX** 依赖许可证与商标红线 | 无 Elastic-2.0 / AGPL / SSPL；API 同名对齐不得暗示 affiliation | **零**第三方运行时依赖（闭包为空集 ⇒ 许可证白名单校验恒通过）；门面**只做导出**，**不复制上游代码**、不复用上游类型（`Send` / `interrupt` 是**自有实现**）——避免「声明兼容」被读成「暗示 affiliation」；兼容矩阵**本 feature 补入本层 5 行**（逐符号等价判定 + 上游来源行号）；`THIRD_PARTY_NOTICES` 因**零**新增依赖**无需新增登记** | ✅ 通过 |
| **原则 X** 文档合规义务 | 每个源文件带署名头；发布 `py.typed`；第三方代码入 `THIRD_PARTY_NOTICES`；**API 兼容矩阵 MUST 维护**；**MUST NOT 在清单缺项的情况下宣布该特性完成** | FR-017（署名头，**范围含 `tests/facade/` 下的新增测试文件**）+ `py.typed` 沿用现状；FR-012（兼容矩阵**补入本层 5 行**：4 列不变、既有 18 行逐字不动、等价程度按当前状态如实标注、上游来源行号写进「差异说明」末尾）；`THIRD_PARTY_NOTICES` **无需新增登记**；**全库**矩阵的补全与定稿归 **B24F1**（写入 `facade-api.md` §6 移交表） | ✅ 通过 |

**门禁结论**：无违反项 ⇒ **Complexity Tracking 表不适用**（不填）。

### 架构纪律核对（立项书 §5.1 · ARCH-1 / ARCH-2 / ARCH-3 / ARCH-4）

> 宪法原则之外，**立项书 §5.1 的四条架构纪律**同样是本 feature 的判定依据
> （ARCH-1 由 CI 的 import 图断言把关；ARCH-4 的执行手段正是本 feature 交付的 API 快照测试）。

| 纪律 | 要求 | 本 feature 的满足方式 | 判定 |
|---|---|---|---|
| **ARCH-1** 依赖方向单向；L1 不依赖任何内部层 | 高层可 import 低层，反向 import 视为违规；跨层单元只能 import L1 与更低层 | **门面的「层」记为跨层单元（层 =「—」，2026-11-07 发起者裁定）**——它的导出面按定义横跨 **L1–L3**（`Command` / `RunConfig` 属 L1 · `Send` / `interrupt` 属 L2 · `StateGraph` 属 L3），故它是 **ARCH-1 的唯一例外**（可 import L1–L3，仍**不得** import L4 / L5）。例外条款已登记于**立项书 §5.1 的 ARCH-1 条目**与 **§5.2 的 B2F2 行**（层列 →「—」、跨层列 →`✔（公开 API）`）。本 feature 期间门面**只 import L1**（`freegraph.contracts`）与自己的私有外壳模块 ⇒ 无违规 | ✅ 通过（**依赖发起者的立项书修订**；B6F1 / B10F1 / B11F1 接线后由该例外条款兜住，见「风险与后续依赖」第 1 行） |
| **ARCH-2** 契约层可独立安装，零第三方依赖 | 单独 import 无副作用；`freegraph/__init__.py` MUST 保持惰性 / 空壳 | FR-013（顶层包**不**导入门面）+ 门禁 **G18**（子进程 `sys.modules` 快照）+ FR-014 ④（门面不横依赖 L4 / L5）；**零新增第三方依赖** ⇒ 依赖闭包仍为空集 | ✅ 通过 |
| **ARCH-3** 跨层只经由 `Protocol` + 纯数据类 | 跨层交互只用协议或纯数据类 | 门面的 `compile()` 返回**协议** `CompiledGraph`（B2F1 冻结）· `Command` / `RunConfig` 是契约层**纯数据类**（B1F1 冻结）· `StateGraph` 是**构建器**（不跨层交互）· `Send` 是**纯载荷型数据类**（`arg` 为用户载荷，**不是**跨层契约载体）——四者均不构成「以具体实现跨层耦合」 | ✅ 通过 |
| **ARCH-4** 公开 API 面只经由 L1 导出 | API 快照测试 | FR-001（唯一门面 `freegraph/graph.py`）+ FR-010 / FR-011（**API 签名快照** = 本 feature 的执行手段）+ FR-006（门面零实现体）+ 门禁 **G14 / G15 / G16** | ✅ 通过 |

> **已知偏离登记（宪法「质量门禁」第 3 项）** —— 登记而不改宪法：
>
> | 宪法条款 | 本 feature 的处置 | 恢复归属 |
> |---|---|---|
> | **质量门禁第 3 项 · 契约门禁**：`harness/demo/target.py` **原样可跑** | **部分适用** —— 本 feature 交付门面的**导出面**（第 122 行的 import **从本 feature 起可成功执行**），但脚本**仍跑不通**：它需要 `StateGraph` 的构建 / 编译 / 执行能力（**B6F1 / B7F2 / B7F3**）与运行时。**MUST NOT** 为凑这条门禁而提前交付行为 | **B6F1 / B7F2 / B7F3** |
> | **质量门禁第 3 项 · 契约门禁**（立项书 §9.1 门禁 3 的**第二个子项**）：「固定脚本为只读基准，**CI 断言其 diff 为空**」 | **部分适用** —— 本 feature **不修改** `target.py`（FR-016）⇒ **判据本身已满足**（`tasks.md` T041 以 `git diff --exit-code` 就地断言 diff 为空）；但**流水线上的 CI 断言**尚未建立 | **B3F1**（CI 门禁） |
> | **质量门禁第 3 项 · 两条独立回归测试**（C4 稀疏状态 / C8 条件边 fresh 读） | **不适用** —— 二者都是**运行时语义**，门面无状态、无调度 | **B5F2 / B8F1** |
> | **原则 V · 「MVP 验收基线双跑」**（fake 模型 + 真实模型各一遍） | **不适用** —— 本 feature 无模型调用、无运行时 | **B25F1**（MVP 验收轮） |
>
> **本偏离不构成对原则 III 实质要求的弱化**：7 项同名同签名的**签名面**已在本 feature
> **逐字冻结并入快照**（原则 III 的「同名同签名」要求原样保留）；缺的只是**行为实现**，
> 归属 M1 / M2 的既有 feature。**本条不触发宪法修订**。

> **人工验证记录的落盘路径**：沿用**仓库惯例** `harness/verification/<feature>/`
> （有明文目录约定见 `harness/verification/README.md`），即
> `harness/verification/B2F2/manual-verification.md`。

> **原则 X 的「填入本层内容」处置**：沿用 B1F1 / B2F1 的既有口径——「**填入本层内容**在本 feature、
> **补全与定稿**归 B24F1」。本 feature **补入本层 5 行**（`StateGraph` / `START` / `END` / `Send` /
> `interrupt`），**既有 18 行逐字不动**；`THIRD_PARTY_NOTICES` 因**零**新增依赖**无需新增登记**；
> 门禁 **G19** 的断言**按门面清单驱动**（期望值从 `facade-api.md` §0 解析）。

---

## Project Structure

### Documentation (this feature)

```text
specs/b2f2-public-api-facade/
├── plan.md                  # 本文件（/speckit.plan 输出）
├── spec.md                  # 特性规格（/speckit.specify + clarify 的产出 · 19 FR / 18 SC · 12 裁定 + 12 问答）
├── research.md              # Phase 0 输出：设计决策台账（**23 条决策 D-01…D-23** + 上游证据 + 13 条挂起项交接表）
├── data-model.md            # Phase 1 输出：7 个导出符号的冻结规格 + 快照格式规则 + 未接线语义表
├── quickstart.md            # Phase 1 输出：可运行的验收指南
├── contracts/
│   ├── facade-api.md        # ★ 门面导出面清单（**7 个** · 手写 · 门禁 G15 的期望值来源）
│   ├── snapshot-format.md   # ★ 快照格式契约（条目语法 · 注解规范化 6 条 · 更新流程）
│   └── architecture-gates.md# ★ 门禁契约：继承 G1–G13 + **新增 G14–G20**
├── checklists/
│   └── requirements.md      # 规格质量清单（/speckit.specify + clarify 维护 · 16/16 通过）
└── tasks.md                 # Phase 2 输出（/speckit.tasks 创建，本命令不生成）

specs/b2f2-public-api-facade/contracts/
└── public-api-snapshot.txt  # ★ API 签名快照（**机器生成** · 入库比对 · 由实现阶段的
                             #   `pytest --update-api-snapshot` 生成并经人工 review diff 后提交）

harness/verification/B2F2/
└── manual-verification.md   # 人工验证记录（原则 V 人工门禁 · 五段式 · 骨架由本 feature 产出）
```

**与既有权威的关系**：契约层的 `specs/b2f1-contracts-protocols/contracts/public-api.md`
（它管 18 个契约层符号）**除 §5 移交表加一行指向本快照外逐字不动**
（FR-010 ④ · Q8 ③ · `tasks.md` T038）；本 feature 的 `contracts/facade-api.md` 管**门面的 7 个符号**。
本 feature **不产出** `public-api.md` ⇒ 门禁 **G12**（唯一权威）**不受影响**。

### Source Code (repository root)

```text
src/freegraph/
├── __init__.py             # 既有 · 顶层包保持惰性（只暴露 __version__）—— 本 feature **不动**
├── py.typed                # 既有 · PEP 561 标记 —— 本 feature 不动
├── graph.py                # ★ 新增：公开 API 门面（**零实现体** · 只做导出 + 两个常量）
├── _stategraph.py          # ★ 新增：StateGraph 外壳（构造可成功 · 四方法未接线）
├── _primitives.py          # ★ 新增：Send 外壳（frozen dataclass）· interrupt 外壳（未接线）
└── contracts/              # 既有（B1F1 / B2F1）—— 本 feature **逐字不动**
    ├── __init__.py         #   公开符号面仍恰 18 个（SC-015 · 门禁 G7 恒成立）
    ├── types.py            #   Command / RunConfig（门面原样转出的两个类型）
    ├── errors.py           #   异常体系 —— 不动（本 feature 不新增任何公开错误类型）
    ├── protocols.py        #   NodeFunc / Checkpointer / Store / CompiledGraph（注解引用）
    ├── graph.py            #   Graph / Node / Edge（契约层图结构 · 与门面同名不同义）
    └── trace.py            #   Span / TraceQuery

tests/facade/               # ★ 新增测试目录（门面不在 contracts 包内 ⇒ 测试也独立成目录）
├── __init__.py             # ★ 空占位（使 `tests/facade/` 可被绝对导入）
├── conftest.py             # ★ sys.path 注入 + `--update-api-snapshot` 选项 + fixture
├── _gatesupport.py         # ★ 门禁共享辅助（AST 扫描 · 子进程 sys.modules · §0 清单解析）
├── _snapshot_tools.py      # ★ `normalize_annotation`（N-1…N-6）· `render_api_snapshot`（纯函数）
├── test_facade.py          # ★ 导出面 / 常量 / 转出同一性 / StateGraph 外壳 / Send / interrupt
├── test_api_snapshot.py    # ★ 快照渲染（纯函数）· 比对 · 可复现 · 更新入口 · 自检三例
└── test_facade_gates.py    # ★ 门禁 G14–G20（7 条门禁 · 8 条自检 —— G15 两段各一条）
```

**结构决策**：

- **门面的「层」= 跨层单元（层 =「—」）**（2026-11-07 发起者裁定 · 立项书 §5.1 ARCH-1 例外
  + §5.2 B2F2 行）——门面的导出面按定义横跨 L1–L3，它**不是**任何单一层的成员；
  本 feature 期间门面只 import L1（`freegraph.contracts`）与自己的私有外壳模块。
- **门面 = 一个模块 `graph.py`，外壳 = 两个私有模块**（research D-01）——
  ① 门面必须是 `freegraph/graph.py`（FR-001 + 交付物口径）；② 外壳用**下划线前缀** ⇒
  用户无法绕过门面构造第二套入口（FR-001 / User Story 3）；
  ③ `StateGraph`（未来 L3）与 `Send` / `interrupt`（未来 L2）**分模块** ⇒
  B6F1 与 B10F1 / B11F1 各自演进时不争抢同一文件；
  ④ **不**把外壳放进契约层（B2F1 冻结记录 §5 第 14 条 + `StateGraph` 属 L3）；
  ⑤ **不**做成 `freegraph/graph/` 包（与 FR-001 冲突，且与 `freegraph.contracts.graph` 更易混淆）。
- **门面不使用 `from __future__ import annotations`**（research D-02）——该 future import 会留下
  名为 `annotations` 的**公开绑定**（实测），直接破坏「公开名恰 7 个」的判据；门面本身零注解。
- **外壳模块亦不使用** future import（research D-03）——契约层注解在运行时是**求值对象**
  （实测），外壳保持同一形态 ⇒ 快照渲染**一套规则通吃**，不必为字符串注解另写一套。
- **快照生成器是纯函数** `render_api_snapshot(namespace) -> str`（research D-10）——
  自检用例（FR-011 ②「故意改坏 ⇒ 确实失败」）用**人造命名空间**喂它，**零副作用**、
  可在任意环境跑。
- **期望的导出面清单手写在 `facade-api.md` §0**（research D-07）——门禁判定**非循环**；
  文件名**不叫** `public-api.md`（research D-08）——否则门禁 G12 恒红。
- **门禁测试文件不叫 `test_architecture.py`**（research D-16）——与
  `tests/contracts/test_architecture.py` 同名会在无 `__init__.py` 的目录下触发 pytest 的
  `import file mismatch`（**收集期直接报错**）。
- **`Send` 是 frozen dataclass 但**不用** `kw_only=True`**（research D-13）——
  契约层的五个数据类一律 `kw_only=True`，但 `graph_core.py` 与上游都用**位置参数**
  `Send("worker", {...})` ⇒ `kw_only=True` 会直接 `TypeError`。
  这是本 feature **唯一**与契约层 dataclass 惯例不同处，**显式登记**在
  `data-model.md` §2.5 与快照中。
- **`harness/demo/graph_core.py` 不改**（research D-18）——M0 阶段其用例必然全红
  （预期**退出码 1** 而非 2）；改它会削弱断言口径（FR-016）。
- **不新建 `harness/` 下的门禁脚本**、**不改** `.github/workflows/`——CI 门禁归 **B3F1**；
  本 feature 的门禁以 pytest 断言交付（沿用 B1F1 / B2F1 的既有移交口径）。

---

## Phase 0 → 1 产出映射

| Phase | 产出 | 状态 |
|---|---|---|
| Phase 0 | `research.md`（**23 条决策 D-01…D-23** 的台账 + 上游源码证据 + **13 条**挂起项交接表） | ✅ 已完成 |
| Phase 1 | `data-model.md`（7 个符号的冻结规格 + 快照格式规则 + 未接线语义表）、`contracts/facade-api.md`（7 符号清单 + 冻结记录）、`contracts/snapshot-format.md`（格式契约）、`contracts/architecture-gates.md`（继承 G1–G13 + **新增 G14–G20**）、`quickstart.md` | ✅ 已完成 |

**Phase 1 后复核**：宪法门禁逐条重新过一遍 —— 结论与上方「Constitution Check」一致，
**无新增违反项**。Phase 1 期间的三项实质性收紧：
① 「门面只做导出」由 spec 的**文字**落到 **AST 判据**（门面模块内 `class` / `def` == 0 · 门禁 G14）；
② 「导出面恰 7 个」落到**两处集合相等**（`__all__` **且** 公开名集合 · 门禁 G15），
   且期望值来自**手写清单** ⇒ 判定**非循环**；
③ 「签名冻结」落到**机器可判的快照**（逐字节比对 + 可复现 + 更新入口默认不生效 · 门禁 G16），
   快照文本的**格式**本身也被冻结（`snapshot-format.md`）。

**与既有 feature 的关系**（避免误伤）：
本 feature **只新增** `src/freegraph/graph.py` / `_stategraph.py` / `_primitives.py` 与 `tests/facade/`；
**不修改** `src/freegraph/contracts/**`（⇒ 门禁 G7 的「恰 18 个」**恒成立** · SC-015）、
**不修改** `tests/contracts/**`（⇒ 门禁 G1–G13 的实现**零改动**；本 feature 新建源文件的**署名头**
由门面侧的**门禁 G20** 覆盖，见 `contracts/architecture-gates.md` G20）、**不修改**
`harness/demo/target.py`（⇒ 只读基准的 diff 为空 · SC-014）。

---

## Complexity Tracking

**无违反项** —— Constitution Check 十条门禁全部通过（原则 III 的「脚本原样可跑」与原则 V 的
「双跑」在本 feature **尚未触达其适用面**，已在门禁表中显式登记为「已知偏离」，非忽略），
故本表不适用。

---

## 风险与后续依赖

| 风险 | 影响 | 缓解 |
|---|---|---|
| **快照的跨 Python 版本漂移**：`typing` 的渲染形态在不同小版本间有差异（`typing.Any` vs `Any`、`Optional[X]` vs `X \| None`） | CI 的 3.11 档与开发机的 3.12 档生成不同文本 ⇒ 快照比对**恒红** | `snapshot-format.md` §2 的**注解规范化 6 条**（N-1…N-6）收敛已知差异源；快照文本**不含**任何版本信息；CI 最低档固定 3.11（门禁 G9 已把关） |
| **「注解规范化」自身漂移**（新增类型 / 新写法 ⇒ 规范化规则不够用） | 快照出现新的形态差异 ⇒ 比对恒红 | 规范化规则**逐条冻结**在 `snapshot-format.md`；新增规则属**契约修订**（先改格式契约 ⇒ 再重生成快照 ⇒ 人工 review diff） |
| **快照文件与代码不同步**（有人改了签名却忘了更新快照） | 测试判红（挂进 CI 后即 CI 判红）⇒ **这是预期行为**（P2 的核心价值） | 快照比对**逐字节**（门禁 G16）；提供**显式**更新入口（`pytest --update-api-snapshot`），更新后**人工 review diff** 再提交；MUST NOT 提供静默自动更新（FR-011） |
| **`Send` 不用 `kw_only=True`** 与契约层 dataclass 惯例不一致 | 后人「顺手统一」⇒ `Send("w", {...})` 位置调用直接 `TypeError`（`graph_core.py` 的用法即破） | 在 `data-model.md` §2.5、`facade-api.md` §2、`research.md` D-13 **三处显式登记**理由与依据；快照里也会呈现（`__init__(self, node: str, arg: Any)`） |
| **门面被「顺手」re-export 到 `freegraph/__init__.py`** | D1 决议第 ④ 条失效 ⇒ 契约层「可独立消费」的收益归零 | 门禁 **G1**（既有实现的口径**已是** `freegraph.*` 子模块全量 —— 断言恰为 `['freegraph']`）+ **G18**（子进程 `sys.modules` 快照）在 CI 中常驻；spec FR-013 明文禁止 |
| **门面被「顺手」写入实现体**（图省事直接定义 `class StateGraph`） | ARCH-4 破功；B6F1 接线时无处安放 | 门禁 **G14**（AST 判据，报行号）+ 裁定 3 的三层记录（spec / `facade-api.md` §5 / 门禁） |
| **`from __future__ import annotations` 被引入门面**（未来重构时） | 引入名为 `annotations` 的公开绑定 ⇒ 公开名变成 8 个 ⇒ 门禁 G15 恒红 | 门禁 G15 会**立刻报出**多出的公开名；`data-model.md` §1.1 R-3 与 research D-02 已写明原因 |
| **`Send` 的「不可变」与上游「可变」的差异** | freechain 迁移时若照抄上游的「改载荷再返回」写法会撞 `FrozenInstanceError` | 差异**写进兼容矩阵**的「差异说明」列（`Send` 行 · research D-17）；`Send` 不可变是**有意**决定（避免调度器读到旧值的时序坑） |
| **门禁密度导致测试行数超出立项书估算**（估 300 行，实际预计 ~600–900 行） | 与立项书 §5.2 的「560 行」有偏差 | 偏差**回填**到本 plan 的「Scale/Scope」小节（实现后）；门禁断言尽量用**参数化**写法摊薄行数；**登记不改立项书**（与 B2F1 的同一口径） |
| **既有门禁被误伤**（改动 `tests/contracts/**` 触发 G1–G13 变红） | 门禁全线变红，排查成本高 | 本 feature **不修改** `tests/contracts/**` 与 `src/freegraph/contracts/**`（SC-015）；既有门禁只**复核**、以「复核」任务落地 |
| **`graph_core.py` 的用例全红**被误读为「本 feature 没做完」 | 误判交付状态 | spec FR-009 / FR-018 / Out of Scope 与 quickstart 的场景 C **明写**预期行为：**退出码 1**（断言失败）而非 2（环境未就绪）；人工记录第 4 节结论中写明「用例未转绿是预期状态」 |
| **门面的层归属未落地即接线**（A1 的历史风险 · 已闭环）：B6F1 / B10F1 / B11F1 把外壳搬到 L2 / L3 后，L1 门面 import L2/L3 会违反 ARCH-1 | 若不修订，等 M2 接线时才会暴露违规、届时返工面波及三个 feature | **已闭环（2026-11-07 发起者裁定）**：门面的「层」记为**跨层单元（层 =「—」）**，作为 ARCH-1 的**唯一例外**；例外条款 + §5.2 的 B2F2 行已修订进立项书。**建议 B6F1 / B10F1 / B11F1 的提示词显式引用该例外条款**（它们接线时门面将首次 import L3 / L2） |
| **下游 feature 接线时改了门面导出面**（如 B6F1 加了第 8 个导出符号） | 破坏「门面是唯一入口」的冻结面 | 任何导出面变化都会**同时**触发门禁 G15 与快照 G16 ⇒ 显式可见；合法变更须走「快照更新 + 人工 review」流程（`snapshot-format.md` §6） |
