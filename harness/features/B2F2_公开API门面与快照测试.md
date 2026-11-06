# B2F2 · 公开 API 门面 `freegraph/graph.py` + API 快照测试

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B2F2` |
> | 所属 功能块 | B2（公开 API 门面与签名冻结） |
> | 架构层 | L1 契约层（门面文件 `freegraph/graph.py` 属公开 API 门面，ARCH-4 约束其只经由 L1 导出） |
> | 里程碑 | M0 地基（第 3 个） |
> | 前置依赖 | **B1F1, B2F1** |
> | 规模 | 560 行（实现 260 / 测试 300）· 3 人日 |
> | 建议 short-name | `b2f2-public-api-facade` |
> | MVP 必需（★） | 否（但它是**验收契约第 1 项**的落点） |

---

## 提示词正文

### 1. 目标

交付 freegraph 的**唯一公开 API 门面** `freegraph/graph.py`，并用**签名快照测试**把它的
对外形状钉死。验收基准脚本 `harness/demo/target.py` 第 122 行要求的那一行
`from freegraph.graph import StateGraph, START, END` 从本 feature 起**必须能成功执行**——
即使 `StateGraph` 此刻还只是尚未接上运行时实现的外壳。

### 2. 背景与上下文

- 立项书 §4.3 的 **18 项 API 裁定**是 MVP 验收契约。其中 **7 项 MUST 同名同签名**
  （否则固定脚本原样跑不起来），本 feature 负责其中与「导出面」相关的第 1 项：
  `freegraph.graph` 导出 `StateGraph` / `START` / `END`，且 `START='__start__'`、
  `END='__end__'`。
- 架构纪律 **ARCH-4**：公开 API 面**只经由 L1 导出**——门面的具体实现体放在下层，
  门面本身只做「导出 + 签名声明」。
- 门面同时是**未来 freechain 的主入口**：freechain 面向用户的 API 也应从同一门面导出，
  避免出现第二套入口。
- `harness/demo/graph_core.py` 已经锁定了门面的**导出清单与调用形态**（见 §7），
  本 feature 须与之一致——但 `graph_core.py` 的用例在 M1/M2 才逐条转绿。

### 3. 用户场景

**P1 — 验收基准脚本能 import 成功**
作为项目发起者，我希望能验证「只换包名」的验收契约在**第一个可运行的 feature** 就已经
成立一半：哪怕 `StateGraph` 尚未接上运行时，`from freegraph.graph import StateGraph,
START, END` 也必须成功——这能把「导出面写错」这类低级错误提前到 M0 暴露。

- **独立验收**：在干净环境执行该 import，退出码 0。

**P2 — 公开 API 形状不会悄悄漂移**
作为维护者，我希望能有一份**签名快照**，任何对公开 API 的改动都在 CI 中显式可见
（diff 出来需人工确认），从而避免「实现悄悄改了签名，用户代码半夜崩掉」。

- **独立验收**：修改门面中任一函数的参数名，CI 的 API 快照测试失败。

**P3 — 上层开发者有单一可信入口**
作为 freechain 开发者，我希望能从**一个模块**取到全部需要的符号（`StateGraph` /
`START` / `END` / `Command` / `Send` / `interrupt` / `RunConfig`），而不是在多个模块
间拼凑，也不需要知道内部包结构。

- **独立验收**：门面导出的符号清单与 §7 表格一致。

### 4. 功能需求

- **FR-001**：系统 MUST 提供模块 `freegraph/graph.py`，作为**唯一公开入口**。
- **FR-002**：门面 MUST 导出 `StateGraph`、`START`、`END`；`START` 的值 MUST 为
  `'__start__'`，`END` 的值 MUST 为 `'__end__'`（C9）。
- **FR-003**：门面 MUST 同时导出 `Command` / `Send` / `interrupt` / `RunConfig`
  （C16 / C17 / C18 / C22），使上层不必深入内部包。
- **FR-004**：门面 MUST NOT 定义业务实现体；实现体 MUST 位于下层模块，门面只做导出。
- **FR-005**：系统 MUST 提供 **API 快照测试**：把公开导出的符号名与**完整调用签名**
  （含参数名、默认值、关键字-only 标记）序列化为稳定文本并入库比对。
- **FR-006**：API 快照的变更 MUST 在 CI 中可见（diff 呈现），并 MUST 与
  `COMPAT.md`（API 兼容矩阵）保持一致。
- **FR-007**：`StateGraph` 在本 feature MUST 是**可构造但功能未接线**的外壳：
  构造签名与调用形态 MUST 已冻结（`StateGraph(schema)` 只接受一个位置参数），
  但 `add_node` / `compile` / `invoke` 的**行为**在 B6F1 / B7F2 / B7F3 交付；
  本 feature MUST NOT 因此宣称脚本可跑通。
- **FR-008**：门面 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读取任何
  环境变量。
- **FR-009**：**顶层包 MUST 保持惰性**——MUST NOT 为了「方便」在
  `freegraph/__init__.py` 中 `from freegraph.graph import ...`；`import freegraph`
  MUST NOT 连带加载 `freegraph.graph` 及其下层（**D1 决议的附加约束**：顶层包一旦
  拖进门面，`import freegraph.contracts` 就会连带加载 L3 → L2，契约层「可独立消费」
  的收益随之失效）。门面 MUST 由用户**显式** `from freegraph.graph import ...` 才加载。

### 5. 成功标准

- **SC-001**：`from freegraph.graph import StateGraph, START, END` 在隔离环境执行成功。
- **SC-002**：`START == '__start__'` 且 `END == '__end__'`（C9 取值被断言钉死）。
- **SC-003**：公开 API 快照测试在 CI 中常驻，任何签名变更导致 CI 失败并输出 diff。
- **SC-004**：门面导出的符号清单与本 spec 的导出面表格**逐项一致**（不多不少）。
- **SC-005**：门面模块对下层模块的 import 关系满足 ARCH-4（公开 API 只经由 L1 导出）。
- **SC-006**：**顶层包惰性**——`import freegraph` 后 `sys.modules` 中**不含**
  `freegraph.graph` / `freegraph.contracts` / 任何运行时 / 持久化 / 可观测子模块；
  而 `import freegraph.graph` 后 `sys.modules` 中**不含**持久化层与可观测层
  （门面不得横向依赖 L4 / L5）。

### 6. 验收判据（= 立项书 §5.2 B2F2 小目标，逐条可判定）

> 小目标原文：`from freegraph.graph import StateGraph, START, END` 可用；签名快照入库

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | `from freegraph.graph import StateGraph, START, END` 可用 | 隔离环境执行 import，退出码 0 |
| A2 | 签名快照入库 | 仓库中存在快照文件，且 CI 中跑快照比对测试 |
| A3 | **顶层包惰性（D1 决议附加约束 · ARCH-2 可判定项）** | `import freegraph` 后的 `sys.modules` 检查（SC-006） |

### 7. 关键实体与契约

**导出面清单（必须与 §4.3 的 18 项裁定对齐）**

| 符号 | 类型 | 契约 | 本 feature 状态 |
|---|---|---|---|
| `StateGraph` | 构建器外壳 | C1 / C9 / C10 | 外壳（行为在 B6F1 / B7F2） |
| `START` | 常量 `'__start__'` | C9 | ✅ 就位 |
| `END` | 常量 `'__end__'` | C9 | ✅ 就位 |
| `Command` | 原语类型 | C16 | 类型（行为在 B9F1） |
| `Send` | 原语类型 | C18 | 类型（行为在 B11F1） |
| `interrupt` | 原语函数 | C17 | 类型（行为在 B10F1） |
| `RunConfig` | 运行配置 | C22 | 类型（行为在 B8F3） |

**调用形态（`harness/demo/graph_core.py` 已锁定，实现必须对齐）**

| 调用 | 形态 | 依据 |
|---|---|---|
| `StateGraph(schema)` | 只传 schema 一个位置参数 | C1 / 宪法原则 III 第 2 项 |
| `add_node(name, fn, alias=...)` | 位置参数 `(str, Callable)` + 关键字 `alias` | C25 / B8F3 |
| `add_edge(src, dst)` | `(str \| list[str], str)`，链式返回 | C9 / 宪法原则 III 第 4 项 |
| `add_conditional_edges(src, path_fn, path_map)` | `path_map` 支持 **list 与 dict** 两种形态 | C7 / 宪法原则 III 第 5 项 |
| `compile(checkpointer=..., store=...)` | 无参可调用 + 两个可选关键字 | C10 / C19 / C20 |
| `invoke(input, config)` | `config` 同时接受 `RunConfig` 与普通 dict | C11 / C22 |
| `recursion_limit` | 走 dict 形态 | B13F1 |

> `draw_mermaid` / `draw_mermaid_png` 属 `Graph` 对象，**不在本 feature 的门面导出面内**
> （B22F1 / B23F1 交付）。

### 8. 边界（本 feature 明确不做）

- 不实现 `StateGraph` 的构建能力（`add_node` / `add_edge` / `add_conditional_edges`）——
  属 **B6F1**。
- 不实现 `compile()` —— 属 **B7F2**；不实现 `invoke()` —— 属 **B7F3**。
- 不实现 `get_graph` / `draw_mermaid` —— 属 **B22F1**；不实现 `draw_mermaid_png` ——
  属 **B23F1**。
- 不在本 feature 让 `harness/demo/target.py` 跑通（它需要 6 个 feature 齐备，见 §10）。
- 不建立 `COMPAT.md` 的完整矩阵内容（**B24F1** 落终版），本 feature 只保证快照与矩阵的
  一致性检查有挂载点。
- **不在 `freegraph/__init__.py` 里 re-export 门面符号**（**D1 已拍板，2026-11-04**：
  v1 单一发行包、契约层为主包子模块；顶层包惰性是该决议的附加约束，见 FR-009）——
  门面只由 `from freegraph.graph import ...` 进入。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：门面不得引入 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**：门面不做任何 I/O。
- **ARCH-4**：公开 API 面只经由 L1 导出；API 快照测试是该约束的执行手段。
- **ARCH-2（含顶层包惰性）**：门面 MUST NOT 横向依赖 L4 / L5；
  `freegraph/__init__.py` MUST NOT 导入门面（**D1 决议附加约束**）。
- **契约门禁**：`harness/demo/target.py` 是**只读基准**，CI 断言其 diff 为空。
- **人工门禁**：人工验证记录落 `harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：导出面与调用形态的每一条都须能追溯到 §4.3 的 18 项裁定或
  `harness/demo/graph_core.py` 的具体行。

### 10. 交付物与后续

- **交付物**：`src/freegraph/graph.py` 门面、API 快照文件与快照测试、
  顶层包惰性的 `sys.modules` 断言、人工验证记录。
- **后续解锁**：**B3F1**（CI 门禁，把 API 快照检查挂进流水线）→ M1 全部 feature。
- **★ MVP 六项最小交付集**：`B6F1` + `B7F2` + `B7F3` + `B8F1` + `B22F1` + `B23F1`
  —— 本 feature 不在其中，但**它是那六项的前置门面**。

---

## 依据

- 立项书 §4.3（18 项 API 裁定）、§5.1（ARCH-4 / ARCH-2 含顶层包惰性）、§5.2（B2F2 行）、
  §5.9（PNG 硬约束）、§9.1（质量门禁第 3 项：固定脚本 diff 断言）、
  **§12 的 D1 决议（2026-11-04：v1 同包子模块 + 顶层包惰性约束）**。
- 宪法 `.specify/memory/constitution.md`：原则 III（验收契约优先 · 7 项同名同签名清单）。
- 验收脚本：`harness/demo/graph_core.py`（门面导出面与调用形态的锁定点）、
  `harness/demo/target.py`（第 122 行 import）。
