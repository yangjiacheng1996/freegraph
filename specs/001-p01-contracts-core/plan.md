# Implementation Plan: 契约层骨架（四个核心类型 + 异常体系）

**Branch**: `001-p01-contracts-core` | **Date**: 2026-11-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-p01-contracts-core/spec.md`

**Phase ID**: `F1P1`（M0 地基 · 31 个 Phase 中的第 1 个）

---

## Summary

交付 freegraph 的**唯一数据与类型契约层**——一个位于 `src/freegraph/contracts/` 的子模块，
定义四类核心类型（状态字典 `StateDict`、命令原语 `Command`、状态快照 `StateSnapshot`、
运行配置 `RunConfig`）与一套统一异常体系（`FreegraphError` + 三个子异常）。

本 Phase **不交付任何运行时行为**：无调度、无 channel、无状态读写、无公开 API 门面。
它交付的是「此后 30 个 Phase 全部要引用的类型地基」，并且这块地基**不依赖任何 freegraph 内部模块**
（ARCH-2），使跨仓库姊妹项目 freechain 能只取契约而不拖进运行时。

技术上，本 Phase 的全部实现由三个标准库机制承载：
`typing` 的类型别名与 `ClassVar`、`dataclasses` 的冻结数据类、`ast` + `subprocess` 的架构断言。
**基础安装零第三方运行时依赖**（`dependencies = []`）——`typing-extensions` 已于
宪法 **v1.2.0** 剥离（最低 Python 抬至 3.11 后 `Self` / `NotRequired` / `Required` /
`TypeVarTuple` / `Unpack` / `LiteralString` / `dataclass_transform` 全部进入标准库）。

冻结面（后续 30 个 Phase 引用、不可轻改）——**下表的「公开符号面」清单以 `contracts/public-api.md` §0 为唯一手工维护点**：

| 冻结项 | 内容 |
|---|---|
| 公开符号面 | 恰好 8 个：`StateDict` / `Command` / `StateSnapshot` / `RunConfig` / `FreegraphError` / `InvalidUpdateError` / `GraphRecursionError` / `GraphInterrupt` |
| `StateSnapshot` 字段 | `values` / `next` / `config` / `metadata` / `created_at` / `tasks` / `interrupts`（七字段，类型逐个冻结） |
| `RunConfig` 字段 | `thread_id` / `context` / `metadata` / `tags`（四字段） |
| `Command` 语义位 | `goto` / `update` / `resume`（三选一必填、可任意组合）+ `Command.PARENT` |
| 异常属性名 | `invalid_keys` / `recursion_limit` + `current_step` / `payload` |
| 文档合规 | `THIRD_PARTY_NOTICES` + `README.md` 的「API 兼容矩阵」—— 两份**活文档**，覆盖本层 8 个符号（FR-016） |

---

## Technical Context

**Language/Version**: Python ≥ 3.11（仓库 `pyproject.toml` 的 `requires-python = ">=3.11"`；本机开发环境实测 CPython 3.12.3，隔离验收另在 CPython 3.11.16 上实测。**不使用** 3.12+ 语法（PEP 695 `type` 语句 / `TypeAliasType`），亦不使用 3.13+ 语法（`ReadOnly` / `TypeIs`），以免再抬高最低版本）

**Primary Dependencies**: **无**（基础安装零第三方运行时依赖）。契约层用到的 `TypeAlias`（3.10）、`Literal`（3.8）、`ClassVar`（3.8）、`Mapping` / `Sequence`（3.9）均已是标准库成员，**无需** `typing_extensions` 兜底。
测试期依赖 `pytest`（开发期工具，**不进发行包**的 `dependencies`，extras 与 CI 门禁归 F3P1）

**Storage**: N/A —— 本 Phase 无持久化。`StateSnapshot` 仅为**类型定义**（承载检查点快照的形状），其存取由 F14P1 / F15P1 实现

**Testing**: pytest（开发期实测 7.4.4）+ 标准库 `unittest.mock` / `subprocess` / `ast`。架构断言（顶层包惰性、契约层零内部 import、依赖闭包）**必须在子进程中执行**——测试进程自身已导入 pytest，无法用同进程 `sys.modules` 判定

**Target Platform**: 任意 CPython 3.11+ 平台（Linux / macOS / Windows）。本 Phase 无平台特定代码、无 C 扩展、无文件 IO 契约

**Project Type**: library（Python 库；发行名 = 导入名 = `freegraph`，契约层为**主发行包内的子模块**，不拆独立发行包 —— D1 已拍板）

**Performance Goals**: 隔离 venv 中 `python -c "import freegraph.contracts"` 的**墙钟 < 300 ms**（含解释器冷启动）。
本机实测基线（用于设定阈值）：解释器启动 ≈ 30 ms ⇒ 预算取 300 ms 留足余量，
同时仍能拦住「契约层偷偷拉起重量级依赖」这类退化。
（**基础安装零依赖后不再有 `import typing_extensions` 的 ≈ 90 ms 开销**；
阈值仍取 300 ms，以覆盖将来引入可选 extra 依赖的情形。）

**Constraints**:
- **零**第三方运行时依赖（基础安装闭包 MUST 为空集）；**不得**引入 pydantic（避免把可选 extras 的依赖拉成必装）
- **构造期只做两条冻结校验**：`Command()` 三语义位全空、`RunConfig.from_dict` 遇未知键；其余**只做类型注解、不校验值**（`created_at` 格式 / `thread_id` 实际类型 / `tags` 元素类型均不在构造期校验）——见 spec Assumptions
- **容器防御性拷贝**：`StateSnapshot` 只拷 `metadata`；`RunConfig` 拷 `metadata` + `tags`；均为**浅拷贝**
- 契约层**零** freegraph 内部模块 import（ARCH-2 / FR-008）
- 顶层包**惰性**：`import freegraph` MUST NOT 连带加载任何子模块（FR-011）
- **零出站**、**不读任何环境变量**（FR-013）
- 每个新源文件携带署名头（FR-010 / 宪法原则 X）
- 发行产物须带 `py.typed`（FR-009 / PEP 561）

**Scale/Scope**: 实现 ≈ 520 行（3 个源文件）+ 测试 ≈ 520 行（4 个测试文件 —— 含 8 条门禁断言与门禁自检；**以断言条数为准**，估算随实现微调）+ 文档 ≈ 90 行（`THIRD_PARTY_NOTICES` + README 兼容矩阵章节 —— **两份已先行起草，本 Phase 为复核并对齐**）；公开符号面恰好 8 个；本 Phase 是 31 个 Phase 中唯一的「纯类型地基」，后续 30 个 Phase 全部引用本层

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 要求 | 本 Phase 的满足方式 | 判定 |
|---|---|---|---|
| **原则 I** 零 LangSmith 依赖 | 依赖树无 `langsmith` / `langchain*` / `langgraph*`；不读 `LANGSMITH_*` / `LANGCHAIN_*`；不向 `*.langchain.com` / `mermaid.ink` 出站 | FR-007（**零**第三方运行时依赖，闭包为空集）+ FR-013（零环境变量、零出站）；SC-002 断言依赖闭包为空；架构断言扫描源码中无 `os.environ` / `os.getenv` | ✅ 通过 |
| **原则 II** 内核纯净 | 核心层不 import langchain；状态 schema 用标准 `TypedDict`，**不得自带并行状态类型体系** | FR-002（`StateDict` = 与 `dict[str, Any]` 兼容的**别名**，非新造类）；FR-008（契约层零内部 import）；架构断言扫描源码无 `langchain` / `langsmith` | ✅ 通过（**C4 / C8 回归测试子项本 Phase 不适用**——契约层无运行时，回归测试分别归 F5P2 / F8P1，已显式记录、非忽略） |
| **原则 III** 验收契约优先 | `harness/demo/target.py` 原样可跑 | 本 Phase **不修改** `target.py`；它当前依赖尚未交付的 `freegraph.graph` 门面（F2P2）与运行时（F7P3），故「原样可跑」在本 Phase **不适用**——不得为凑这条门禁而提前交付门面 | ✅ 不适用（记录在案） |
| **原则 IV** 可诊断性是一等功能 | 失败可被上层结构化读取，而非只能解析日志字符串 | FR-006：三个异常各暴露结构化属性（`invalid_keys` / `recursion_limit`+`current_step` / `payload`），错误消息仅为摘要 | ✅ 通过 |
| **原则 V** 人工验收是最终验收标准 | 本 Phase 结束须有人工验证记录（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）；MVP 验收基线须 fake 模型 + 真实模型**各跑一遍** | `quickstart.md` 给出可复制的验证步骤；人工记录落 `harness/features/F1P1/manual-verification.md`。**「双跑」子项在本 Phase 不适用**（无运行时、无模型调用；C4 稀疏状态与 C8 条件边的回归测试分别归 F5P2 / F8P1），已显式记录、非忽略 | ✅ 通过（双跑子项不适用） |
| **原则 VI** 规格驱动开发 | 有 proposal 与 spec，再进 tasks 与实现 | 本 Phase：spec（`specs/001-p01-contracts-core/spec.md`，含 **15** 条澄清记录）→ 本 plan → tasks → 实现 | ✅ 通过 |
| **原则 VII** 职责边界与内核契约 | 不做 freechain 能力；契约清单以 Q8 C1–C27 为唯一权威 | 不实现 `Store` / 4 类协议（F2P1）、不做 LangChain 层能力；本 Phase 冻结的类型逐条对应 C1 / C4 / C6 / C11 / C16 / C17 / **C19（checkpointer 协议所承载的「快照形状」；协议本身归 F2P1）** / C21 / C22 | ✅ 通过 |
| **原则 VIII** 证据与术语纪律 | 事实性结论带来源标记；术语准确 | `research.md` 每条决策标注依据（Q8 §3.4 / 立项书 §5.3.1 / LangGraph 1.2.19 源码核实）；术语统一用「状态字典 / 命令原语 / 状态快照 / 运行配置」 | ✅ 通过 |
| **原则 IX** 依赖许可证与商标红线 | 无 Elastic-2.0 / AGPL / SSPL；API 同名对齐不得暗示 affiliation | **零**第三方运行时依赖（闭包为空集，许可证白名单校验随之恒通过）；**FR-016** 落两份活文档——`THIRD_PARTY_NOTICES` + `README.md` 的「API 兼容矩阵」，其中含「兼容意图为互操作，**不构成 affiliation**」声明；**FR-016 另要求 `README.md` 含「独立实现、非 LangChain Inc. 产品」声明**（原则 IX 商标禁令的明文要求，不以「不构成 affiliation」一句替代） | ✅ 通过 |
| **原则 X** 文档合规义务 | 每个源文件带署名头；发布 `py.typed`；第三方代码入 `THIRD_PARTY_NOTICES`；**API 兼容矩阵 MUST 维护**；**MUST NOT 在清单缺项的情况下宣布该特性完成** | FR-010（署名头，**范围含 `tests/` 下的 4 个测试文件**——原则 X 的「仓库内的脚本」按「本仓库新增的一切 `.py`」执行）+ FR-009（`py.typed`）+ **FR-016**：本 Phase **建立并填入** `THIRD_PARTY_NOTICES` 与 `README.md` 的「API 兼容矩阵」两份**活文档**（两份文件已先行起草，本 Phase 的动作是**复核并对齐**而非从零创建），并填入本层 8 个符号的等价判定（补全与定稿归 F24P1，但**建立与填写在本 Phase**） | ✅ 通过 |

**门禁结论**：无违反项 ⇒ **Complexity Tracking 表不适用**（不填）。

---

## Project Structure

### Documentation (this feature)

```text
specs/001-p01-contracts-core/
├── plan.md              # 本文件（/speckit.plan 输出）
├── spec.md              # 特性规格（/speckit.specify + 两轮 clarify 的产出）
├── research.md          # Phase 0 输出：设计决策台账
├── data-model.md        # Phase 1 输出：四类型 + 异常体系的数据模型
├── quickstart.md        # Phase 1 输出：可运行的验收指南
├── contracts/
│   ├── public-api.md    # 公开 API 冻结契约（8 个符号的签名与语义）
│   └── architecture-gates.md  # 架构门禁契约（8 条门禁及其判定方式）
├── checklists/
│   └── requirements.md  # 规格质量清单（/speckit.specify 维护）
└── tasks.md             # Phase 2 输出（/speckit.tasks 创建，本命令不生成）

仓库根（本 Phase · 活文档 · 补全与定稿归 F24P1）——**两份文件已先行起草，本 Phase 的动作是「复核并对齐」而非从零创建**：

THIRD_PARTY_NOTICES     # 第三方代码归属 + 依赖登记 + 「不构成 affiliation」声明（FR-016）—— 已存在
README.md                # 「API 兼容矩阵」章节 —— 8 个公开符号的等价判定（FR-016）—— 章节已存在
```

### Source Code (repository root)

```text
src/freegraph/
├── __init__.py                 # 既有 · 顶层包保持惰性（只暴露 __version__）
├── py.typed                    # 既有 · PEP 561 标记（顶层一个即覆盖全部子包）
└── contracts/                  # ★ 本 Phase 新增
    ├── __init__.py             # 公开符号面（8 个）+ __all__
    ├── types.py                # StateDict / Command / StateSnapshot / RunConfig
    └── errors.py               # FreegraphError / InvalidUpdateError / GraphRecursionError / GraphInterrupt

tests/
└── contracts/                  # ★ 本 Phase 新增
    ├── conftest.py             # 让 pytest 能找到 src/ 下的包（开发期免安装）
    ├── test_types.py           # 四类型的字段、构造、校验、冻结语义
    ├── test_errors.py          # 异常体系结构、属性、基类捕获
    └── test_architecture.py    # 架构门禁（惰性 / 零内部+零第三方 import / 依赖闭包 / 零环境变量 / 署名头 / py.typed / __all__ / 文档合规）
```

**结构决策**：

- **单包 + 单发行包**（D1 已拍板，2026-11-04）。契约层是主发行包 `freegraph` 内的**子模块** `freegraph.contracts`，不新增第二个发行包 —— 将来若重开 D1，拆分成本 = 移动目录 + 加 shim 包，**零契约变更**。
- **契约层拆 3 个文件而非 1 个**：`types.py` 与 `errors.py` 分开，使后续 F2P1（4 类协议）可新增 `protocols.py` 而不与本层纠缠；`__init__.py` 只做再导出与 `__all__` 声明。SC-006 已明确「契约层自身的子模块不受 `sys.modules` 判定限制」，故此拆分不违反惰性门禁。
- **顶层包不动**：`src/freegraph/__init__.py` 现状已满足 FR-011（只暴露 `__version__`），本 Phase 仅补一段说明惰性契约的注释，不新增任何导入。
- **测试放 `tests/contracts/`**（仓库当前无 `tests/` 目录，本 Phase 首次建立）。架构断言用**子进程**执行，因为 `sys.modules` 判定不能在已导入 pytest 的测试进程内做。
- **不新建 `harness/` 下的门禁脚本**：CI 门禁归 F3P1；本 Phase 的门禁以 pytest 断言交付（F3P1 时把这些断言接进流水线即可）。

---

## Phase 0 → Phase 1 产出映射

| Phase | 产出 | 状态 |
|---|---|---|
| Phase 0 | `research.md`（20 条设计决策） | ✅ 已完成 |
| Phase 1 | `data-model.md`、`contracts/public-api.md`、`contracts/architecture-gates.md`（**8** 条门禁）、`quickstart.md` | ✅ 已完成 |

**Phase 1 后复核**：宪法门禁逐条重新过一遍 —— 结论与上方「Constitution Check」一致，**无新增违反项**。
Phase 1 期间的三项实质性收紧：
① 「契约层零内部 import」由 spec 层的 MUST 落到**可执行的 AST 断言**（G2）；
② SC-001 的「同量级」落到**可判定的 300 ms 阈值**；
③ 宪法原则 X 的**文档合规门禁**（立项书 §9.1 门禁 7）从「人工评审、延后到 F24P1」改为
**本 Phase 即建立并填写**两份活文档（FR-016：`THIRD_PARTY_NOTICES` + `README.md` 的「API 兼容矩阵」），
并落成**可自动判定的 G8 断言**（断言兼容矩阵覆盖全部 8 个公开符号）——
「文档有没有跟上代码」从此不再依赖人记得去更新。

---

## Complexity Tracking

**无违反项** —— Constitution Check 十条门禁全部通过（原则 III 因 `target.py` 依赖尚未交付的
F2P2 门面与 F7P3 运行时而「不适用」，已在门禁表中显式记录，非忽略），故本表不适用。

---

## 风险与后续依赖

| 风险 | 影响 | 缓解 |
|---|---|---|
| `GraphInterrupt.payload` 的**具体类型**属 F2P1 / F10P1（`Send` / `interrupt` 归 F2P1），本 Phase 只能以宽松类型承载 | 属性**名**已冻结（`payload`），但其类型注解在 F2P1 落地时会被收紧 | 收紧**元素类型**不属契约破坏（spec Assumptions 已授权：`tasks` / `interrupts` / `payload` 的**元素类型**归 F2P1，**字段注解本身不动**）；属性名与载荷结构（`.value` / `.id`）已冻结。**注意**：字段**注解**本身（`RunConfig` 四字段 / `StateSnapshot` 七字段）自本 Phase 起**一并冻结** —— F4P1 / F8P3 只能新增字段、不得改动已有字段的注解 |
| `Command.PARENT` 的字符串哨兵 `"__parent__"` 理论上可与用户节点名撞名 | 极低概率 | 已写入 spec Edge Cases：该名字视为**保留名**，节点名校验归 F7P2 / F9P1 |
| 本 Phase 交付的类型被后续 Phase 反复引用，改名成本极高 | 一次冻结、长期引用 | spec 已把 8 个符号名、字段名、属性名、常量值逐个写死（**15** 条澄清记录）；SC-008 要求把冻结记录写入 Phase 验收记录 |
