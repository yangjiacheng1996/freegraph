# B4F1 · schema 解析 + 归约器提取

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B4F1` |
> | 所属 功能块 | B4（schema 解析 + reducer 提取） |
> | 架构层 | L2 执行内核层 |
> | 里程碑 | M1 运行时内核（第 5 个） |
> | 前置依赖 | **B2F2** |
> | 规模 | 940 行（实现 480 / 测试 460）· 3 人日 |
> | 建议 short-name | `b4f1-schema-reducer-parse` |
> | MVP 必需（★） | 否 |

---

## 提示词正文

### 1. 目标

把用户写的**状态 schema**（标准 `TypedDict` + `Annotated`）翻译成运行时可执行的
**通道规格**：为 schema 的每一个 key 推导出一条通道规格，并从 `Annotated` 的元数据中
**提取归约器**。本 feature 的核心判定是：`Annotated[list[AnyMessage], operator.add]`
必须被正确识别为**二元归约器**，而不是被当成普通注解忽略。

### 2. 背景与上下文

- **不重建状态类型体系**：状态 schema 由用户以标准 `TypedDict` 表达，freegraph 采纳
  `Annotated[T, reducer]` 这一 PEP 593 标准机制。freegraph **不得**自带一套并行状态类型
  体系（宪法原则 II）。
- **归约器机制是通用协议，不是 LangChain 特有**（Q8 §1 第 2 条）：`Annotated[T, reducer]` +
  `reducer(current, new) -> value` 的二元函数约定，freechain 可直接采用。
- **二元性是硬要求**：`reducer` MUST 恰好接受 **2 个位置参数**。LangGraph 的
  `_is_field_binop` 用同一判据（`langgraph/graph/state.py:1820-1935`）。判据错误会导致
  非二元 callable 被误当作归约器，运行时才炸。
- **Pydantic schema** 属可选支持（`[pydantic]` extra），本 feature 以 `TypedDict` 为主路径，
  Pydantic 路径若纳入须在 spec 中写明支持到什么程度。

### 3. 用户场景

**P1 — 带归约器的 key 被正确识别**
作为用户，我用 `Annotated[list[AnyMessage], operator.add]` 声明消息通道时，希望 freegraph
知道这个 key 是**追加**而不是**覆盖**，以便多次节点写入的消息能累积成完整对话历史。

- **独立验收**：对 `Annotated[list, operator.add]` 解析出的通道规格，其归约器是
  `operator.add` 本身，且被判定为二元。

**P2 — 不带归约器的 key 走默认覆盖语义**
作为用户，我声明 `llm_calls: int` 这类**计数型** key 时，希望每次节点写入都**覆盖**
上一次的值，而不是累加。

- **独立验收**：对无 `Annotated` 的 key，解析结果标记为「无归约器 / 默认覆盖」。

**P3 — 非归约器的注解不被误判**
作为用户，我的 schema 里可能有别的 `Annotated` 用法（例如 `Annotated[int, "说明文字"]`），
希望它**不会**被误当成归约器。

- **独立验收**：元数据末位不是 callable 时，解析结果为「无归约器」。

### 4. 功能需求

- **FR-001**：系统 MUST 接受标准 `TypedDict` 作为状态 schema；MUST NOT 要求用户继承任何
  freegraph 基类（C1）。
- **FR-002**：系统 MUST 为 schema 的**每一个 key** 产出一条通道规格（`ChannelSpec` 一类的
  纯数据），至少承载：key 名、类型信息、是否带归约器、归约器引用。
- **FR-003**：系统 MUST 从 `Annotated[T, ...]` 的元数据中提取归约器：**取元数据末位元素**，
  且**当且仅当**该元素是「恰好接受 2 个位置参数」的 callable 时，才认定为归约器
  （C2）。
- **FR-004**：系统 MUST 支持 `Annotated` 元数据中含多个非归约器条目（如
  `Annotated[list, "描述", operator.add]`），只把末位 callable 当归约器。
- **FR-005**：系统 MUST 对**无归约器**的 key 标记「默认覆盖」语义（C3）。
- **FR-006**：系统 MUST 拒绝或明确处理**非法 schema**：非 `TypedDict` 的对象、
  归约器位置参数数 ≠ 2 的 callable——行为须明确（抛错或降级为无归约器），
  并在 spec 中写死。
- **FR-007**：解析结果 MUST 是**纯数据**（可被契约层的类型表达），不得夹带运行期对象；
  归约器本身是唯一的例外（它是用户提供的 callable，按引用持有）。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读取环境变量。

### 5. 成功标准

- **SC-001**：`Annotated[list[AnyMessage], operator.add]` 被识别为二元归约器，
  且归约器引用与 `operator.add` 为同一对象（100% 判定）。
- **SC-002**：无 `Annotated` 的 key 100% 标记为默认覆盖。
- **SC-003**：元数据末位非 callable、或 callable 位置参数数 ≠ 2 时，100% 不被当作归约器。
- **SC-004**：schema 解析不产生任何 import 副作用、无环境变量读取、无网络访问。
- **SC-005**：解析结果可被序列化/比较（纯数据），便于在测试中直接断言。

### 6. 验收判据（= 立项书 §5.2 B4F1 小目标，逐条可判定）

> 小目标原文：`Annotated[list, operator.add]` 被正确识别为二元归约器

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | `Annotated[list, operator.add]` 被正确识别为二元归约器 | 单元测试断言解析结果中的归约器引用 + 二元性标记 |
| A2 | 二元性判据与 LangGraph 一致 | 对照 `langgraph/graph/state.py:1820-1935` 的 `_is_field_binop` 行为取样比对 |
| A3 | 无归约器 key 走覆盖语义 | 单元测试断言（C3 标记） |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| 状态 schema | 用户提供的 `TypedDict`；每个 key 映射到一个通道 | **C1** |
| 通道规格（`ChannelSpec`） | 解析产物：key / 类型 / 归约器 / 默认语义 | C1 / C2 / C3 |
| 归约器 | `Annotated` 元数据末位的二元 callable：`reducer(current, new) -> value` | **C2** |

> **口径提醒**：C3（默认覆盖语义）的**执行**在 B5F1 的 `LastValue` 通道里；本 feature 只
> 负责把「无归约器」这一事实解析出来。

### 8. 边界（本 feature 明确不做）

- 不实现通道本身（`LastValue` / `BinaryOperatorAggregate` / `EphemeralValue`）——
  属 **B5F1**。
- 不实现状态读取（稀疏语义）——属 **B5F2**。
- 不实现调度循环——属 **B7F1**。
- 不实现 `StateGraph` 构建器——属 **B6F1**（本 feature 产出的通道规格正是构建器的输入）。
- 不做 Pydantic schema 的完整支持（如纳入，须写明支持边界）。
- 不实现 `add_messages` 这类 LangChain 特有归约器（属 freechain 层）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`；
  本层**只允许标准库**（Pydantic 若支持则走可选 extra）。
- **零出站 / 零环境变量**。
- **ARCH-1**：L2 只向下依赖 L1 契约层；MUST NOT import L3/L4/L5。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：判据来源须标注（`langgraph` 源码路径:行号 / Q8 条号）。

### 10. 交付物与后续

- **交付物**：schema 解析器 + 通道规格纯数据类型 + 归约器提取与二元性判定 +
  单元测试 + 人工验证记录。
- **后续解锁**：**B5F1**（通道实现，接收本 feature 的解析产物）。
- **风险提示**：归约器二元性判据若写错，**错误只在运行期暴露**（表现为归约调用参数数
  不符）。本 feature 的测试必须覆盖「非二元 callable 被拒绝」这一负向用例。

---

## 依据

- 立项书 §5.2（B4F1 行）、§5.3（C1 / C2 / C3 / C4 / C8）、§5.4（DF1 `StateDict`）、
  §9.2（fake 注入机制）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C1–C26）与 §1 摘要第 2 条
  （通用 vs LangChain 特有判别）。
- 源码参照：`langgraph/graph/state.py:1820-1935`（`_get_channel` / `_is_field_binop`）。
- 宪法 `.specify/memory/constitution.md`：原则 II（内核纯净）。
