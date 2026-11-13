# B8F1 · 条件边路由求值 + `END` 终止 + fresh 读（C8 独立回归测试）★

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B8F1` |
> | 所属 功能块 | B8（路由语义 + stream + 别名/context） |
> | 架构层 | L2 执行内核层 |
> | 里程碑 | M2 图定义与对外 API（第 17 个） |
> | 前置依赖 | **B5F2, B7F1** |
> | 规模 | 1,100 行（实现 480 / 测试 620）· 3 人日 |
> | 建议 short-name | `b8f1-conditional-edges-fresh-read` |
> | MVP 必需（★） | **是**（固定脚本所需 6 项之一） |

---

## 提示词正文

### 1. 目标

交付**条件边**的路由语义：路由函数在正确的时机被调用、看到正确的状态视图、返回的
目标被正确解析（含 `path_map` 的 list / dict 双形态）、`END` 能终止整张图。
本 feature 的判定是：**路由函数看到本节点刚写入的值**（C8 fresh 读）。

### 2. 背景与上下文

- **C8 fresh 读**是全项目**最易被静默破坏**的两条契约之一：
  路由函数必须看到「**当前值 + 本节点本次写入**」。
  - 后果：若路由函数读到旧消息，`target.py` 的 `should_continue` 会判定「不调用工具」
    → 工具循环失效（退化为单轮）或死循环。
  - 实现要点：LangGraph 的 `local_read(fresh=True)`
    （`langgraph/pregel/_algo.py:188-224`）是 C8 语义的**唯一来源**——
    freegraph 必须把这个读取**单独抽出、单独命名、单独测试**，而不是散落在调度逻辑里。
- **C7 路由函数契约**：`path_fn(state) -> str | Hashable | Sequence[Hashable]`；
  返回 `END` 结束；`path_map` 支持 list 与 dict 两种形态。
- **`path_map` dict 形态的语义**是「路由函数返回值 → 目标节点名」的映射；
  list 形态则是「允许的目标集合」（返回值直接就是目标节点名）。
- **差分夹具复用**：本 feature 是 C8 回归测试的落点，同时**复用** B5F2 建立的差分
  测试夹具（同一图规格双实现比对）。
- **夹具接口口径（B5F2 → B8F1 · M1）**：B5F2 交付的夹具**已预留条件边字段**
  （B5F2 交付时该字段恒空 · 夹具不据此分支）⇒ **本 feature 只需填值即可复用同一夹具**；
  MUST NOT 重造夹具接口（MUST NOT 使 B5F2 已产出的差分证据作废）。
  该口径由 B5F2 的 `specs/b5f2-sparse-state-read/spec.md`（FR-015 / 裁定 15）落成。
- **条件边字段口径（B7F1 → B8F1 · M2）**：B7F1 交付的手写图规格
  `GraphSpec` **已预留一个「条件边」字段** `conditional_edges`，本轮（**B7F1**）
  **恒为空**、**填值即显式失败**（内置 `ValueError` · 校验规则 **V-8**）⇒
  **B8F1 只需填值**即可复用，**无需改造 B7F1 的调度内核**。
  ⚠️ **两侧各自填值**即可（B7F1 的 `GraphSpec.conditional_edges` **+** B5F2 差分夹具的
  同名字段）⇒ **不新造第三套**图规格形态。
  该口径由 B7F1 的 `specs/b7f1-superstep-loop/spec.md`（FR-033 / 裁定 25 · 下游承接
  **D-1**）落成 · 契约见
  `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §2.1。
- **`local_read` 的调用口径（B5F2 → B8F1 · M1 · FR-031 ② / SC-023）**：
  **B8F1 MUST 在使用 `local_read` 时显式传 `fresh=True`**（`fresh` 的缺省是 `False`）
  · MUST **NOT** 依赖缺省 · MUST **NOT** 假设上游的 `managed` 语义
  （research **DR-3** · 上游 `local_read` 的第四类入参 freegraph **不实现**）。
  该口径由 B5F2 的 `specs/b5f2-sparse-state-read/spec.md`（FR-031 / 裁定 33 ③）落成
  · 契约见 `specs/b5f2-sparse-state-read/contracts/read-contract.md` §1.1。

### 2.1 背景与上下文（补充 · 2026-11-11）

- **承接条款（B9F1 → B8F1 · M2 · `node_writes` 的归属口径）**：B9F1 已冻结「`Command.update` 的写入
  **归源节点**名下」（`node_writes` 仍**按节点分组**）⇒ **本 feature 的 fresh 读**（「本节点**本次**写入」）
  **读得到** `Command` 的写入 ⇒ **零改动**、**形态不变**（分组维度不变 ⇒ B9F1 的归一**不破坏**本 feature 的前提）。
  该口径由 B9F1 的 `specs/b9f1-command-primitive/spec.md`（**裁定 16** · FR-004）落成。
### 3. 用户场景

**P1 — 路由基于本节点的最新产出**
作为用户，我的模型节点刚写入了带 `tool_calls` 的消息，路由函数据此决定「去工具节点」
还是「结束」。

- **独立验收**：路由函数收到的状态里含本节点刚写的消息。

**P2 — 两种 path_map 都能用**
作为用户，我用 list 声明「可去的节点」，也用 dict 声明「返回值 → 节点」的映射。

- **独立验收**：list / dict 各一例，路由目标与预期一致。

**P3 — 返回 END 真的终止**
作为用户，路由函数返回 `END` 时，整张图停止执行，不再进入后续节点。

- **独立验收**：`END` 之后的目标节点执行次数 == 0。

### 4. 功能需求

- **FR-001**：系统 MUST 在条件边源节点**执行完毕后**求值路由函数。
- **FR-002**：路由函数 MUST 通过 **fresh 读**获取状态：可见「当前值 + 本节点本次写入」
  （**C8**）。
- **FR-003**：系统 MUST 支持 `path_map` 的 **list** 与 **dict** 两种形态（C7）：
  - list：路由函数的返回值**直接**作为目标节点名（取值必须在 list 内）；
  - dict：路由函数的返回值作为 **key**，其对应的 value 为目标节点名。
- **FR-004**：系统 MUST 支持路由函数返回**序列**（多个目标 → 并行 fan-out 到多个节点）。
- **FR-005**：路由函数返回 `END`（值 `'__end__'`）时 MUST 终止整张图的执行。
- **FR-006**：路由返回值**不在 `path_map` 内**时 MUST 抛出明确异常（消息指明返回值
  与可选目标）。
- **FR-007**：系统 MUST 提供 **C8 独立回归测试**：断言路由函数看到本节点刚写入的值。
- **FR-008**：系统 MUST 复用差分夹具，比对 freegraph 与 langgraph 的**路由判定**
  （`path_map` 的 list / dict 两形态各一例）。
- **FR-009**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量。

### 5. 成功标准

- **SC-001**：C8 回归测试通过——路由函数可见本节点本次写入（100%）。
- **SC-002**：`path_map` 的 list 与 dict 两形态各有一例路由结果正确。
- **SC-003**：路由返回 `END` → 后续节点执行次数 == 0。
- **SC-004**：路由返回值非法 → 抛出明确异常（可由异常类型 + 消息判定）。
- **SC-005**：差分比对中，freegraph 与 langgraph 的路由判定一致。

### 6. 验收判据（= 立项书 §5.2 B8F1 小目标，逐条可判定）

> 小目标原文：C8 独立回归测试通过：路由函数看到本节点刚写入的值；**差分测试夹具
> 建立**：路由判定与 `langgraph` 一致（`path_map` 的 list / dict 两形态各一例）

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 路由函数看到本节点刚写入的值 | C8 独立回归测试 |
| A2 | 差分：路由判定与 langgraph 一致 | 差分夹具（list / dict 各一例） |
| A3 | `END` 终止 | 终止用例断言 |
| A4 | `path_map` 双形态 | list / dict 各一例 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| 路由函数契约 | `path_fn(state) -> str \| Hashable \| Sequence[Hashable]` | **C7** |
| fresh 读 | 「当前值 + 本节点本次写入」 | **C8** |
| `END` | 终止标记（`'__end__'`） | **C9** |
| 路由通道 | `EphemeralValue`，每 super-step 清空 | C7 / C8 |

> **口径提醒**：fresh 读的**读取原语**在 B5F2（`freegraph.runtime.local_read`）；
> 本 feature 交付的是「在路由求值这个具体时机使用它」的语义 + 独立回归测试。
> 差分夹具的**接口口径**见 §2「夹具接口口径（B5F2 → B8F1）」。

### 8. 边界（本 feature 明确不做）

- 不实现 `stream()`（属 B8F2）。
- 不实现 `Send` fan-out 的调度（属 B11F1）——路由返回**序列**的多目标 fan-out
  若与 `Send` 语义重叠，须在 spec 中明确区分。
- 不实现节点别名（属 B8F3）/ `context` 通道（属 B8F3）。
- 不实现 `get_graph` / PNG（属 B22F1 / B23F1）。
- 不实现 checkpoint（属 B14F1）。
- 不实现 async（v2 范围）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**。
- **ARCH-1**：L2 只依赖 L1。
- **契约门禁第 3 项**：C8 独立回归测试常驻 CI（与 C4 一起）。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：fresh 读语义须标注源码依据
  （`langgraph/pregel/_algo.py:188-224`）。

### 10. 交付物与后续

- **交付物**：条件边求值（list / dict 双 `path_map`、序列返回值、`END` 终止、
  非法返回值报错）、**C8 独立回归测试**、差分比对扩展、单元测试 + 人工验证记录。
- **后续解锁**：**B8F2**（`stream`）→ **B22F1** → **B23F1**。
- **★ MVP 六项最小交付集**：本 feature 是其中第 4 项。本 feature 完成后，
  `target.py` 的**工具循环**（`should_continue` → `tool_node` → `llm_call`）路径已具备
  全部语义要素——只差 `get_graph` / PNG（B22F1 / B23F1）与 `invoke` 的完整对接。
- **风险提示**：C8 是**静默破坏**型契约——写错时代码照样跑通，只是循环行为不对。
  因此回归测试必须是**否定式断言**（断言路由函数**看到了**新值，而不只是「跑通了」）。

---

## 下游承接（**B7F4** · 2026-11-13 · **只接线 · 逐条最小改动**）

- **D-3 · 条件边路由 MUST NOT 受屏障影响**：条件边的路由判定归 **B8F1** ⇒ ⇒
  「**条件边的目标集合**」与「**屏障组**」是**两套**语义 ⇒ ⇒ **MUST NOT 混用** ⇒ ⇒
  ⇒ **B8F1 MUST NOT** 把「多源边」当作「条件边」求值 ⇒ ⇒ 判据 **FR-007** / **FR-016**。
  ⇒ 落点：`specs/b7f4-multisource-join/spec.md` 的**承接条款 D-3** · 登记项 **PR-4**。

## 依据

- 立项书 §5.2（B8F1 行）、§5.3（C7 / C8 / C9 与「两条必须独立回归的契约」表）、
  §4.2（S5 等价证据三层）、§9.1（门禁第 3 项）、§9.2（fake 断言点）。
- 源码参照：`langgraph/pregel/_algo.py:188-224`（`_read_channels` 的 fresh 读）、
  `langgraph/graph/state.py:982`（`add_conditional_edges`）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C7 / C8）。
- 验收脚本：`harness/demo/graph_core.py`（条件边 list / dict 两形态用例）、
  `harness/demo/target.py:126-137`（`should_continue`）。
