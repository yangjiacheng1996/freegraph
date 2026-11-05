# F6P1 · `StateGraph` 构建器 ★

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | Phase ID | `F6P1` |
> | 所属 Feature | F6（`StateGraph` 构建器） |
> | 架构层 | L3 图定义层 |
> | 里程碑 | M2 图定义与对外 API（第 14 个） |
> | 前置依赖 | **F4P1** |
> | 规模 | 1,320 行（实现 700 / 测试 620）· 3 人日 |
> | 建议 short-name | `p06-stategraph-builder` |
> | MVP 必需（★） | **是**（固定脚本所需 6 项之一） |

---

## 提示词正文

### 1. 目标

交付 `StateGraph` 构建器：用户用**同名同签名**的 API 声明「状态 schema + 节点 + 边
+ 条件边」，得到一个可编译的图定义。本 Phase 的判定是：**构建器 API 与 LangGraph
同名同签名**——因为 `harness/demo/target.py` 第 145–155 行的建图代码必须原样可用。

### 2. 背景与上下文

- **为什么构建器排在运行时之后**：LangGraph 的图定义层 import 运行时层
  （`langgraph/graph/state.py:73-75`），而运行时层不 import 图定义层。因此运行时
  先行（M1），构建器退化为**薄适配器**：它只做「schema → 通道规格 + 节点规格 + 边
  → 路由」的翻译，运行时行为由已验收的 L2 承担。
- **同名同签名是硬要求**（宪法原则 III 第 2–5 项）：`StateGraph(schema)`、
  `add_node(name, fn)`、`add_edge(src, dst)`、`add_conditional_edges(src, path_fn,
  path_map)` 的方法名与位置参数形态不得改变。
- **`path_map` 双形态**：`add_conditional_edges` 的 `path_map` MUST 同时支持
  **list**（`["tool_node", END]`）与 **dict**（`{"a": "node_a"}`）两种形式（C7）——
  验收脚本两种各有一例。
- **构建器不做运行时**：本 Phase 的构建器负责**记录**节点与边；把记录翻译成可执行
  图是 **F7P2 `compile()`** 的事。

### 3. 用户场景

**P1 — 原样写出验收脚本的建图代码**
作为项目发起者，我希望 `harness/demo/target.py` 的建图段落（第 142–155 行）**一字不改**
就能跑起来。

- **独立验收**：该段代码原样执行不抛 `AttributeError` / `TypeError`。

**P2 — 条件边的两种 path_map 都能用**
作为用户，我既会用 list 形态声明分支目标，也会用 dict 形态把「返回值 → 节点名」显式
映射。

- **独立验收**：list 与 dict 各一例，均能成功构建。

**P3 — 建图错误能被指出**
作为用户，我把节点名写错（边指向不存在的节点）时，我希望 freegraph **早点报错**
（构建期）而不是运行时才炸。

- **独立验收**：构建期抛出明确异常，消息指明问题节点。

### 4. 功能需求

- **FR-001**：系统 MUST 提供 `StateGraph(schema)` 构造器，**只接受 schema 一个位置
  参数**（C1 / 宪法原则 III 第 2 项）。
- **FR-002**：系统 MUST 提供 `add_node(name, action)`，位置参数为 `(str, Callable)`，
  并 MUST 支持关键字 `alias`（C25；形态待 F8P3 拍板，本 Phase 可先接受该参数）。
- **FR-003**：系统 MUST 提供 `add_edge(start_key, end_key)`，其中 `start_key` 可为
  `str` 或 `list[str]`，且 MUST 返回可用于链式调用的对象（C9 / 宪法原则 III 第 4 项）。
- **FR-004**：系统 MUST 提供 `add_conditional_edges(source, path, path_map)`，
  `path_map` MUST 同时支持 **list 与 dict** 两种形态（C7 / 宪法原则 III 第 5 项）。
- **FR-005**：系统 MUST 接受 `START` / `END` 作为节点名使用（值分别为 `'__start__'` /
  `'__end__'`）。
- **FR-006**：系统 MUST 在**构建期**检测并报出明显错误：边指向不存在的节点、
  重复节点名、缺少起点等；错误消息 MUST 指明具体问题。
- **FR-007**：系统 MUST 把用户声明的节点与边**转成内部规格**（节点规格 + 路由通道 +
  分支规格），供 F7P2 编译使用；本 Phase **不执行**任何节点。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量；
  MUST NOT 有任何 I/O。

### 5. 成功标准

- **SC-001**：`harness/demo/target.py` 第 142–155 行的建图代码**原样**执行成功。
- **SC-002**：`add_conditional_edges` 的 list 与 dict 两种 `path_map` 各有一例通过。
- **SC-003**：构建期错误检测：3 类错误各有一例被捕获且消息可定位问题。
- **SC-004**：`add_edge` 的链式返回形态可判定（`add_edge(...).add_edge(...)` 可用）。
- **SC-005**：构建器产出的内部规格可被 F7P2 消费（本 Phase 与 F7P2 的接口形态在本
  Phase 的 spec 中写死）。

### 6. 验收判据（= 立项书 §5.2 F6P1 小目标，逐条可判定）

> 小目标原文：构建器 API 与 LangGraph 同名同签名

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | API 与 LangGraph 同名同签名 | 逐项比对 `StateGraph` / `add_node` / `add_edge` / `add_conditional_edges` 的方法名、位置参数、返回语义 |
| A2 | `path_map` 双形态 | list / dict 各一例 |
| A3 | 建图代码原样可写 | `target.py:142-155` 原样执行成功 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `StateGraph` | 图构建器 | C1 / C9 / C10 |
| 节点规格 | 「名字 → 函数」+ 别名 | C5 / **C25** |
| 边规格 | 静态边 / 条件边（含 `path_map` 双形态） | **C7** / C9 |
| 路由通道 | 条件边判定结果的承载（`EphemeralValue`） | C7 / C8 |

> **口径提醒**：`path_map` 的 dict 形态语义是「路由函数返回值 → 目标节点名」的映射
> （C7）；本 Phase 只**记录**该映射，实际求值在 F8P1。

### 8. 边界（本 Phase 明确不做）

- 不实现 `compile()`（属 F7P2）——本 Phase 的产物是「可被编译的构建器」。
- 不实现 `invoke()`（属 F7P3）。
- 不实现条件边的**求值**与 fresh 读（属 F8P1）。
- 不实现 `stream()`（属 F8P2）。
- 不实现 `get_graph` / `draw_mermaid`（属 F22P1 / F23P1）。
- 不实现节点别名的完整语义（属 F8P3）——本 Phase 只接受 `alias` 参数。
- 不实现子图（v2，C26）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**。
- **ARCH-1**：L3 只依赖 L1 / L2；MUST NOT 反向 import。
- **契约门禁第 3 项**：本 Phase 不产生回归，但 MUST NOT 破坏 M1 已有的语义。
- **人工门禁**：`harness/features/<feature>/manual-verification.md`。
- **证据门禁**：同名同签名的逐项比对 MUST 附 LangGraph 源码行号
  （`langgraph/graph/state.py:928` `add_edge`、`:982` `add_conditional_edges`）。

### 10. 交付物与后续

- **交付物**：`StateGraph` 构建器（4 个方法 + 构建期校验 + 内部规格产物）、
  单元测试 + 人工验证记录。
- **后续解锁**：**F7P2**（`compile()`）→ **F7P3**（`invoke()`）。
- **★ MVP 六项最小交付集**：本 Phase 是其中第 1 项；六项齐备时
  `harness/demo/target.py` 才能跑通 fake 模型轮（M2 验收点，串行口径第 20 个 Phase /
  第 60 天）。
- **风险提示**：构建器 API 的**参数形态**一旦与 LangGraph 有偏差，验收脚本就会失败。
  建议本 Phase 的 spec 直接把 §7 的「逐项比对表」作为 FR 附件列全，避免 plan 阶段
  凭记忆补参数。

---

## 依据

- 立项书 §4.3（18 项 API 裁定 · 7 项同名同签名）、§5.1（分层拍板）、§5.2（F6P1 行）、
  §5.3（C1 / C5 / C7 / C9 / C10 / C25）、§6.2（M2 里程碑）、§9.1（门禁）。
- 源码参照：`langgraph/graph/state.py:131`（`StateGraph`）、`:928`（`add_edge`）、
  `:982`（`add_conditional_edges`）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4。
- 验收脚本：`harness/demo/target.py:142-155`、`harness/demo/graph_core.py`。
- 宪法 `.specify/memory/constitution.md`：原则 III（7 项 MUST 同名同签名）。
