# B5F1 · Channel 抽象 + `LastValue` + `BinaryOperatorAggregate` + `EphemeralValue`

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B5F1` |
> | 所属 功能块 | B5（Channel 抽象 + LastValue/BinOp） |
> | 架构层 | L2 执行内核层 |
> | 里程碑 | M1 运行时内核（第 6 个） |
> | 前置依赖 | **B4F1** |
> | 规模 | 1,060 行（实现 520 / 测试 540）· 3 人日 |
> | 建议 short-name | `b5f1-channels` |
> | MVP 必需（★） | 否 |

---

## 提示词正文

### 1. 目标

交付 freegraph 的**通道抽象**与三类通道实现：**无归约器 → 覆盖**（`LastValue`）、
**有归约器 → 归约**（`BinaryOperatorAggregate`）、**每 super-step 清空**（`EphemeralValue`，
供路由通道使用）。通道是 freegraph 状态模型的唯一读写单元——所有状态的写入、合并、
读取都必须经由通道，从而让「覆盖 vs 归约」这条语义只有**一个**实现点。

### 2. 背景与上下文

- LangGraph 的通道实现是其状态语义的核心（`langgraph/channels/last_value.py:20-52`、
  `langgraph/channels/binop.py:123-153`）。freegraph **重写而非复制**，但语义必须等价。
- 通道分类决定了两条关键契约：
  - **C3（默认归约语义）**：无 reducer → **覆盖**（左值丢弃）。
  - **C2（归约器机制）**：归约器是**二元**函数 `reducer(current, new) -> value`。
- `EphemeralValue` 是**路由通道**：条件边的判定结果每 super-step 清空，避免上一轮的
  路由结果污染下一轮。
- 通道抽象的收益是**收敛**：状态写入只有一条路径 → 「归约器覆盖规则写错」这类静默
  破坏被限制在一个地方。

### 3. 用户场景

**P1 — 计数型 key 每次被覆盖**
作为用户，我的 schema 里有 `llm_calls: int`（无归约器）。我希望节点写 `llm_calls: 1` 后
下一个节点读到的是 `1` 而不是 `2`。

- **独立验收**：同一通道连续写入两个不同值，读取结果是后者。

**P2 — 消息型 key 累积追加**
作为用户，我的 schema 里有 `messages: Annotated[list, operator.add]`。我希望两个节点
先后写入消息后，读取结果是**拼接后的完整列表**。

- **独立验收**：同一通道写入两次，读取结果等于 `operator.add(first, second)`。

**P3 — 路由结果不跨轮残留**
作为实现者，我希望路由通道的判定结果在每个 super-step 结束后被清空，从而第二轮的
路由不受第一轮影响。

- **独立验收**：写入路由值 → 触发清空 → 读取得到「空」语义。

### 4. 功能需求

- **FR-001**：系统 MUST 提供统一的**通道抽象**，至少包含「写入（update）」「读取（get /
  read）」与「状态清空（可空）」三类操作；通道 MUST 是可替换的实现单元。
- **FR-002**：系统 MUST 实现 `LastValue` 通道：写入即**覆盖**（丢弃旧值），
  读取返回最近一次写入值（C3）。
- **FR-003**：系统 MUST 实现 `BinaryOperatorAggregate` 通道：写入时调用
  `reducer(current, new)` 并保存结果；**首次写入**时 `current` 取该通道的「空值」
  语义（C2）。
- **FR-004**：系统 MUST 实现 `EphemeralValue` 通道：每次 super-step 结束时被清空。
- **FR-005**：三类通道 MUST 具备一致的可替换接口，使 B4F1 的解析结果能**按 schema key
  映射到通道类型**（有归约器 → BinOp；无归约器 → LastValue；路由专用 → Ephemeral）。
- **FR-006**：通道 MUST 只持有**纯数据 + 用户提供的归约器引用**，MUST NOT 感知节点、
  图结构或运行配置。
- **FR-007**：系统 MUST 提供「通道无值」与「通道有值」的**可判定区分**——这是 C4
  稀疏状态的基础（B5F2 实现读取语义）。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量；
  MUST NOT 有任何 I/O。

### 5. 成功标准

- **SC-001**：`LastValue` 连续写入 2 次后读取结果 = 最后一次写入值（100% 判定）。
- **SC-002**：`BinaryOperatorAggregate` 连续写入 2 次后读取结果
  = `reducer(current, new)`（与 `operator.add` 的拼接结果逐元素相等）。
- **SC-003**：`EphemeralValue` 在清空后读取到「无值」（不是上一次的值、也不是 `None`
  冒充有值）。
- **SC-004**：通道的「有值 / 无值」判定 100% 可判定，无第三种模糊状态。
- **SC-005**：三类通道的实现不依赖任何 `langchain*` 包，且不产生 import 副作用。

### 6. 验收判据（= 立项书 §5.2 B5F1 小目标，逐条可判定）

> 小目标原文：归约器 `operator(current, new)` 语义一致；无归约器 key 被覆盖

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 归约器 `operator(current, new)` 语义一致 | 单元测试：通道写入序列的结果 == `operator.add` 逐次归约的结果 |
| A2 | 无归约器 key 被覆盖 | 单元测试：`LastValue` 连续写入后读取为末值 |
| A3 | 路由通道每 super-step 清空 | 单元测试：`EphemeralValue` 清空后无值 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| 通道（抽象） | 状态的唯一读写单元 | C1 / C3 |
| `LastValue` | 无归约器 → 覆盖 | **C3** |
| `BinaryOperatorAggregate` | 有归约器 → `reducer(current, new)` | **C2** |
| `EphemeralValue` | 路由通道，每 super-step 清空 | C7 / C8（供 B8F1 使用） |

> **口径提醒**：本 feature 的通道**不含**读取时的稀疏语义——「读到无值的 key 时返回什么」
> 由 B5F2 的读取层决定，通道只负责如实表达「有值 / 无值」。

### 8. 边界（本 feature 明确不做）

- 不实现 schema 解析（属 B4F1）与状态读取（属 B5F2）。
- 不实现调度循环（属 B7F1）——因此本 feature 的通道只能被**直接单元测试**，
  不能通过跑图验证。
- 不实现 `Topic` / `Barrier` 等 LangGraph 有而 v1 不需要的通道类型（v1 只需三类）。
- 不实现 `add_messages` 等 LangChain 特有归约器（属 freechain 层）。
- 不实现 checkpoint 写入（属 B14F1）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**。
- **ARCH-1 / ARCH-3**：L2 只依赖 L1；通道只经由协议与纯数据交互。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：与 LangGraph 的语义对应须标注源码行号。

### 10. 交付物与后续

- **交付物**：通道抽象 + 三类通道实现 + 与 B4F1 解析结果的映射规则 + 单元测试 +
  人工验证记录。
- **后续解锁**：**B5F2**（稀疏状态读取，C4 回归测试落点）→ **B7F1**（调度循环）。
- **风险提示**：本 feature 是**纯单元可测**的 feature（没有图可跑），因此测试覆盖率要求
  最高；「首次写入时 `current` 取什么」这一细节若选错，会让
  `operator.add` 的结果与 LangGraph 差一个前缀元素。

---

## 依据

- 立项书 §5.2（B5F1 行）、§5.3（C2 / C3 / C4）、§5.4（协议纪律）。
- 源码参照：`langgraph/channels/last_value.py:20-52`、`langgraph/channels/binop.py:123-153`
  （含 `Overwrite`）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4。
- 架构纪律：`harness/prompts/guide.md` §3.5、§5（跨 feature 持续约束）。
