# Feature Specification: B7F2 · `compile()` → `CompiledGraph` ★

**Feature Branch**: `b7f2-compile`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "B7F2 · `compile()` → `CompiledGraph` —— 把构建器产出的「节点 + 边 + schema」规格编译成一个可执行对象 `CompiledGraph`：节点挂载、路由通道就位、条件边分支就位、可选能力（checkpointer / store）注入。判定 = 图可编译；`compile()` 无参可调用。本 feature 是 **MVP 六项最小交付集**的第 2 项；前置依赖 **B6F1**。"

---

## 承接条款（上游 feature → 本 feature）

> 宪法 v1.8.0「跨 feature 承接的接线通则」：上游 feature 指名本 feature 的跨 feature 义务
> MUST 在本 spec 落成 **FR + 裁定**；**只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽判据**。

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B7F1 → B7F2** | **M2** | **图规格形态**：本 feature MUST 把 L3 的声明式规格**适配**为 B7F1 的 `GraphSpec`（通道映射 + **保序**节点表 + 边表 + **预留**的条件边字段）与 `NodeSpec`（**订阅集** + 节点函数）⇒ **MUST NOT 另造第三套形态**；节点入参口径 MUST 等于 `read_channels(子映射)` 的结果、子映射 MUST 按「**通道映射的顺序**」构造 ⇒ **MUST NOT** 改写 key 顺序；调度状态口径 MUST NOT 改写 `run_super_step(spec, state)` / `run_super_steps(spec, state=None, *, max_steps=...)` 两个入口的接收口径；校验 MUST 在**构造时**执行 ⇒ 本 feature 的适配器 MUST 依赖此口径（**构造期**即暴露问题） | `specs/b7f1-superstep-loop/spec.md` FR-033 / 裁定 25 / 裁定 26 / 裁定 27 / 裁定 32 · `contracts/superstep-contract.md` §1 / §2.1 / §2.1.1 | FR-004 · FR-005 · 裁定 4 / 5 · SC-004 / SC-009 |
| **H-2** | **B6F1 → B7F2** | **M2** | **构建器快照消费**：`compile()` MUST 从 `StateGraph._build_spec()` 取得 `_BuilderSpec`；**仅过滤单源** `END` 目标，多源 **V-16 形态**与 `__parent__` 原样保留给 `GraphSpec` 最终失败（⚠️ **源含 `START`** 的形态由构建器 `add_edge` 立即层拒绝，见 Edge Cases）；`_BuilderSpec.conditional_edges` MUST **机械翻译**为 plain mapping（内层 `"branch"` 取自 `_ConditionalEdgeSpec.branch`，MUST NOT 重新推断）并存放在 `CompiledGraph` 私有字段；同时保留**完整** `_BuilderSpec`（至少 `node_records`）供 B8F3；B7F2 阶段 MUST NOT 填充 `GraphSpec.conditional_edges` | `specs/b6f1-stategraph-builder/spec.md` **D-1 / D-2** · FR-007 / FR-016 · 裁定 2 / 6 | FR-007 · FR-008 · FR-009 · FR-010 · 裁定 5 / 12 / 13 · SC-006 / SC-010 |
| **H-3** | **B12F1 → B7F2** | **M2** | **编译产物持「规格」**：多会话隔离**已由 2026-11-12 P2-b 在 L2 落地**（每次运行从规格新建通道实例）⇒ **本 feature 的义务收窄为「对外暴露」**：编译产物 MUST 持通道**规格**（而非把活实例直接交给运行）⇒ 与 **B7F3** 的「每次 `invoke` 新建实例」**共同**落成「一次编译、多会话隔离」的**门面级**验收；MUST NOT 越界到 L2 去改 `Channel` 的冻结面或 `GraphSpec.channels` 的语义 | `specs/b12f1-concurrency-errors/spec.md` **FR-024** · 裁定 23（**已作废**）· 下游承接 **D-4** · 回溯修订 **T-7** | FR-012 · 裁定 10 · SC-011 / SC-012 |
| **H-4** | **B13F1 → B7F2** | **M2** | **静态断点关键字**：`compile(interrupt_before=..., interrupt_after=...)` MUST 被接受，并 MUST 原样填入 `GraphSpec.interrupt_before` / `interrupt_after`；**净接受值**与上游逐字一致：**裸 `"*"` 或 `list[str]`**，裸非 `"*"` 字符串 / 元组 / `["*"]` 失败，`None` 归一为 `()`；MUST NOT 另立第三套静态断点载体；不存在的断点节点名 MUST 在**编译期**失败（`ValueError`，消息点名该节点），不得推迟到 `invoke()`；`START` / `END` / 空串 / `["*"]` / 裸非 `"*"` 字符串 / 非 `str` 的失败信号与 `GraphSpec` 构造期**逐字同款**；裸 `"*"` = 全部可执行节点 | `specs/b13f1-static-interrupt-recursion-limit/spec.md` 下游承接 **D-1 / D-2** · FR-002 / FR-003 · 裁定 3 | FR-013 · FR-014 · 裁定 6 · SC-005 / SC-007 |
| **H-5** | **B7F4 → B7F2** | **M2** | **边表键类型的知情面**：`GraphSpec.edges` 的**键类型**已放宽为 `str \| tuple[str, ...]`（**兼容性扩展** · 只放宽不收紧）⇒ ⇒ 本 feature 的 `compile()` MUST **照原样透传**边表 ⇒ ⇒ **MUST NOT** 在编译层重建屏障语义 ⇒ ⇒ 本 feature 的**破冻结面**（B7F1 契约 §1 / §2.1）对 `compile()` **无行为影响**（但本 feature MUST **知情**） | `specs/b7f4-multisource-join/spec.md` 下游承接 **D-5** · 登记项 **PR-4** | FR-007 · 裁定 5 · SC-009 |
| **H-6** | **B3F1 → B7F2** | **M2** | **最小图可被编译**：承接 B3F1 延后的 FR-005 ③② 的「**编译**」环节 —— 最小图 MUST **可被编译**；运行期断言在 **B7F3** 闭环点亮。**只接线，MUST NOT 新增门禁编号**；红线**不放宽**（FR-018 无豁免）—— ③② 是同一红线的**运行期加强**，非判据放宽 | `specs/b3f1-scaffold-ci-gates/spec.md` 裁定 22 · `harness/proposals/立项书.md` §6.2 | FR-020 · 裁定 11 · SC-014 |
| **H-7** | **B2F1 / B2F2 → B7F2** | **M1** | **能力面协议与门面冻结**：`CompiledGraph` 的**协议**（6 方法 · 返回类别 + 参数名）已在 B2F1 冻结；本 feature 只交付**实现** ⇒ MUST NOT 改协议签名、**MUST NOT** 增删门面导出符号（`freegraph.graph` 的 7 个符号冻结）；实现体 MUST 住在**私有模块**（L3）⇒ MUST NOT 进门面导出面 | `specs/b2f1-contracts-protocols/spec.md` · `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt` · `contracts/facade-api.md` §0 | FR-003 · FR-010 · FR-017 · 裁定 2 · SC-013 |

---

## 下游承接条款（本 feature → 下一棒）

> 本 feature 冻结「编译产物」这唯一跨 feature 接口。**只接线 · 逐条最小改动**。

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 |
|---|---|---|---|---|
| **D-1** | **B7F2 → B7F3** | **M2** | **`invoke()` 的执行语义**：`CompiledGraph.invoke(input, config=None)` MUST 驱动 L2 的 `run_graph(spec, input, *, checkpointer=..., config=..., ...)`（B10F1 的图级入口）并把 `SuperStepResult` / `InterruptResult` 归一成**完整状态字典**（C11）；每次 `invoke` MUST **新建**通道实例（多会话隔离的另一半 · H-3）；MUST NOT 另写一条「编译 → 执行」的路径。**编译产物持规格**这一半由本 feature 交付 ⇒ 两侧**共同**落成「一次编译、多会话隔离」 | FR-012 · 裁定 10 · SC-011 / SC-012 |
| **D-2** | **B7F2 → B8F1** | **M2** | **条件边分支规格的交接载体**：B7F2 已在 `CompiledGraph` 的私有字段持有条件边的 plain mapping（外层 key = 源节点名；内层每项 = `{"branch", "path", "path_map", "targets", "route_channels"}`；顺序 = 登记顺序；`"branch"` 取自 `_ConditionalEdgeSpec.branch`）⇒ **B8F1 MUST 从 `compiled._conditional_edges` 读取**并填入 `GraphSpec.conditional_edges`（落地时承接 V-8 放宽）；**路由求值 MUST 只消费 L2 的 `GraphSpec.conditional_edges`**；MUST NOT import `freegraph._stategraph` / `_ConditionalEdgeSpec`，MUST NOT 重新归一化 `path_map`，MUST NOT 另起路由通道命名（沿用 `branch:to:<target>`）；B7F2 阶段 `GraphSpec.conditional_edges` **恒空** | FR-009 / FR-010 · 裁定 12 / 13 · SC-010 |
| **D-3** | **B7F2 → B8F3** | **M2** | **别名交接载体**：B7F2 已在 `CompiledGraph` 的私有字段保留**完整 `_BuilderSpec`**（含 `node_records`）⇒ **B8F3 MUST 从该保留读取 `_NodeRecord.alias`** 实现别名寻址语义，MUST NOT 要求用户重新声明别名，MUST NOT 要求 B7F2 改写快照内容 | FR-008 · 裁定 3 · SC-010 |
| **D-4** | **B7F2 → B14F1** | **M3** | **checkpointer 的编译期校验补齐**：上游在编译期对非法 checkpointer 抛 `TypeError`（`ensure_valid_checkpointer`）⇒ **B14F1 MUST 补上上游同款的编译期类型校验**（freegraph 的 `Checkpointer` 是**结构化协议** ⇒ 校验口径由 B14F1 冻结）；本 feature 只做「接受 + 记录 + 不报错」 | FR-016 · 裁定 7 · 偏离登记 X-4 · SC-015 |
| **D-5** | **B7F2 → B22F1** | **M3** | **图结构导出的数据来源**：`CompiledGraph.get_graph(*, xray=False)`（B22F1 实现）MUST 从本 feature 交付的 `GraphSpec`（节点表 / 边表 / 通道表）与条件边映射**导出**结构；MUST NOT 重新解析构建器状态；`draw_mermaid` / `draw_mermaid_png` 归 B23F1 | FR-010 · 裁定 3 · SC-013 |

---

## Clarifications

### Session 2026-11-16（设计裁定 · spec 阶段写死，plan 不得再翻）

> **背景**：提示词初稿已写死「同名同签名 · 无参可调用 · `checkpointer=` / `store=` 被接受 ·
> 编译期静态校验 · 能力面 6 方法」，但**三处**仍会外溢到用户代码或下游 feature 的接口决策：
> ① **编译期校验的严格程度**（提示词 §10 自陈「本 feature 的主要决策点」）；
> ② **编译产物的形态与归属**（编译产物是「运行时本身」还是「持有运行时的门面」）；
> ③ **未就绪方法与未就绪关键字的失败信号**（「抛未实现」用什么类型 / 「静默接受」到哪一步）。
> 本节逐条拍板。

- **Q1（`compile()` 的签名）**：保持 B6F1 / B2F2 冻结的签名**逐字不变**？
  → **A：是**。签名以 `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`
  为权威：`compile(self, checkpointer=None, *, cache=None, store=None,
  interrupt_before=None, interrupt_after=None, debug=False, name=None,
  transformers=None) -> CompiledGraph`。本 feature **只实现**它，**MUST NOT** 增删 /
  改名 / 改序任何关键字（否则 B2F2 的公开 API 快照逐字节失效）。
  ⇒ 落点：FR-001 · 裁定 1 · SC-001 / SC-002 / SC-013。
- **Q2（编译产物的实现体放哪、叫什么）**：放 `freegraph.graph` 门面？还是 L3 私有模块？
  → **A：L3 私有模块**（**落点 = `freegraph/_stategraph.py`** · 与构建器**同模块**）
  + 实现类名 **`CompiledGraph`**
  > **2026-11-16 · plan 阶段补记（P-1）**：初版括注写的是 `freegraph/_compiled.py`。
  > 层注册表把 `src/freegraph/_stategraph.py` 登记为**文件级 L3** 条目，而 G25 对
  > **L2–L5 的同层横向 import 一律判违规** ⇒ 新建 `_compiled.py` 会让 `_stategraph.py`
  > 导入它构成 **L3 → L3** 违规（或必须改**冻结**的层注册表）⇒ 改为**同模块**。
  > **决策本身（L3 私有模块 · 类名 · 不继承协议 · 不进门面）一字未改**。
  （与 L1 协议同名 · 宪法原则 III 的「同名同签名」精神）⇒ ① **MUST NOT** 进
  `freegraph.graph` 的导出面（7 符号是 B2F2 冻结面）；② **MUST NOT** 继承 L1 的
  `CompiledGraph` 协议（L1 协议是**纯抽象 · 无继承链** · PD-1）⇒ 满足协议靠
  **结构化子类型**判定；③ 用户只通过 `compile()` 的返回值拿到它。
  ⇒ 落点：FR-003 / FR-017 · 裁定 2 · SC-013。
- **Q3（编译产物内部持有什么）**：编译产物 MUST 持哪些东西？
  → **A：五组** —— ① `_spec`（L2 的 `GraphSpec`：节点任务规格 + 触发依赖 + 通道表
  含路由通道）；② `_builder_spec`（**完整** `_BuilderSpec`，含 `node_records`，供 B8F3）；
  ③ `_conditional_edges`（条件边的 plain mapping，供 B8F1）；④ 被注入的可插拔能力与
  编译选项（`checkpointer` / `store` / `cache` / `debug` / `name` / `transformers`）；
  ⑤ **归一后**的 `interrupt_before` / `interrupt_after`（元组）。
  ⇒ **①②③ 三个私有字段名是**冻结的跨 feature 接口**（B8F1 / B8F3 / B22F1 MUST 按名
  读取）；⇒ **④⑤ MUST 以公开实例属性**暴露（`checkpointer` / `store` / `cache` /
  `debug` / `name` / `transformers` / `interrupt_before_nodes` /
  `interrupt_after_nodes`）—— 上游 `Pregel` **同款**（`pregel/main.py:814-831`；
  `transformers` 的命名差异见 **X-12**）⇒
  ⇒ 用户**能读到**注入项（SC-002 / SC-015 的可观察口径）⇒ ⇒ **除这 8 个注入项与
  断点属性外**，公开属性面 MUST 为空（其余状态一律私有）。
  ⇒ 落点：FR-008 / FR-009 / FR-010 / FR-016 · 裁定 3 · SC-002 / SC-010 / SC-015。
- **Q4（编译期检查清单 vs 明确不检查项）**：编译期到底查什么？
  → **A：两条清单都要写死**（FR-005 检查清单 14 项 / FR-006 不检查项 7 项）。
  ⚠️ 提示词 §2 举的「**节点不可达**」例子**不做**（理由见 Q9）；提示词 §3 P3 说的
  「**路由目标不在 `path_map` 里**」在编译期**不可判定**（只有调用路由函数才知道返回值）
  ⇒ 编译期只查「`path_map` 的**目标节点**存在」与「`path_map` **形态**合法」，
  「路由**返回值**不在 `path_map` 中」⇒ 运行期由 B8F1 显式失败。
  ⇒ 落点：FR-005 / FR-006 · 裁定 4 / 9 · SC-004 / SC-006。
- **Q5（`END` 目标与多源边的处理）**：编译期怎么处理指向 `END` 的边？
  → **A：只过滤**单源键（`str`）中目标为 `END` 的边（freegraph 的节点表**不含** `END`
  ⇒ 不过滤会被 V-2 判死）；过滤后目标元组为空的**源键整体移除**；**多源键**（`tuple`）
  的 `END` 目标**MUST NOT** 过滤 ⇒ 原样交给 `GraphSpec` 的 **V-16** 显式失败
  （B7F4：「多源目标 MUST NOT 为 `__end__`」）；`__parent__` 节点名同理原样交给
  `GraphSpec` 的保留名检查（B9F1 FR-005）显式失败。
  ⇒ 落点：FR-007 · 裁定 5 · SC-008。
- **Q6（静态断点的容器形态与失败信号）**：`compile()` 入口怎么收紧形态？
  → **A：入口只接受 `None` / `str` / `list`**；`None` 归一为 `()`；裸 `"*"`
  ⇒ 全部可执行节点（由 `GraphSpec` 归一，编译期即展开）；**`str` 原样透传**（含裸非
  `"*"` 字符串与空串 ⇒ 由 `GraphSpec` 归一在 `compile()` 调用点抛 `TypeError`，
  以保证消息与构造期**逐字同款**）；**元组 / `set` / 数值等其它容器** ⇒ 入口层
  `TypeError`（**V-22 家族**）；**元素级**失败信号（空串 V-23 / 哨兵与 `"*"` V-24 /
  未知节点 V-25）MUST 由 `GraphSpec` 的归一函数产出 ⇒ **逐字同款**（B13F1 D-2）
  ⇒ ⇒ 入口层**只做容器形态门**，MUST NOT 另写一套元素校验。
  ⇒ 落点：FR-013 / FR-014 · 裁定 6 · SC-007。
- **Q7（`checkpointer` / `store` 在编译期怎么处理）**：接受到什么程度？要不要校验类型？
  → **A：接受任意对象并记录；MUST NOT 报错；MUST NOT 做类型校验**。理由：① v1 的
  checkpointer 实现归 B14F1、store **无实现**（B17 已砍 · 宪法原则 VII）⇒ 编译期做
  「实现合法性」判定会把「**尚未就绪**」误报成「**用户错误**」；② 上游的编译期类型
  校验由 **B14F1** 补齐（下游承接 **D-4**）；③ `store=` 的 v1 语义 MUST 在**文档**中
  显式写明「v1 不支持 `Store`」（原则 VII）⇒ **MUST NOT** 静默生效。
  ⇒ 落点：FR-016 · 裁定 7 · 偏离登记 X-3 / X-4 · SC-015。
- **Q8（未就绪能力面的失败信号）**：6 个方法里未就绪的那些抛什么？
  → **A：内置 `NotImplementedError`**，消息**点名归属 feature**
  （`invoke` → B7F3；`stream` → B8F2；`get_graph` → B22F1；`get_state` /
  `get_state_history` → B15F1；`update_state` → B16F1）⇒ 与 B6F1 的未交付方法同款
  ⇒ **MUST NOT** 抛 `AttributeError`、**MUST NOT** 静默返回 `None`、**MUST NOT** 新增
  异常类型（FR-022）。
  ⇒ 落点：FR-011 · 裁定 8 · SC-008 / SC-015。
- **Q9（可达性 / 环是否在编译期检查）**：
  → **A：不检查**。理由：① 上游 `compile()` **不做**可达性 / 环检查（照抄 · 原则 XI）；
  ② `path_map=None` 的**动态路由**使静态可达性判定**不健全**（编译期无法知道路由会
  跳到哪）⇒ 误判会误伤合法用法（提示词 §10 自陈的「过严会误伤」）；③ 环由运行期的
  步数上限（`recursion_limit` · B13F1）负责 ⇒ 编译期不重复。
  ⇒ 落点：FR-006 · 裁定 9 · SC-006。
- **Q10（编译产物持「活通道实例」还是「规格」）**：
  → **A：持规格**。编译产物持 `GraphSpec.channels` 的**模板**（未写入任何值的通道）⇒
  每次运行由 L2 从规格**新建**实例（B12F1 的 P2-b · `superstep.py:575-591` 的
  `_run_channels`）⇒ ⇒ 「一次编译、多会话隔离」在 L2 已成立（H-3）⇒ 本 feature 的
  义务只是「**对外暴露**」⇒ 编译期 MUST NOT 写入任何通道值、MUST NOT 把活实例交给运行。
  ⇒ 落点：FR-012 · 裁定 10 · SC-011 / SC-012。
- **Q11（重复编译与「已编译后再改图」）**：编译后还能改图吗？要不要警告？
  → **A：能改，且不发警告**。上游 `compile()` 末尾把 `self.compiled = True`
  （`state.py:1174`），此后 `add_node` / `add_edge` / `add_conditional_edges` 会发
  **`logging` 提示**（实测 E-49 / E-50：**不是** `warnings.warn`）
  ⇒ **B6F1 已裁定不复制
  该副作用**（范围边界）⇒ 本 feature **MUST NOT** 引入 `compiled` 标志或 warning；
  同一构建器**可多次 `compile()`**，每次取**独立快照**，产物彼此互不影响。
  ⇒ 落点：FR-014 / FR-019 · 裁定 11 · 偏离登记 X-5 · SC-012。
- **Q12（条件边的交接载体形状）**：plain mapping 的确切形状？
  → **A：逐字按 B6F1 D-2** —— `dict[str, tuple[dict[str, Any], ...]]`：外层 key =
  `source`；内层每个 dict 的 key / value 逐字为
  `{"branch": str, "path": Callable, "path_map": dict[Hashable, str] | None,
  "targets": tuple[str, ...], "route_channels": tuple[str, ...]}`；顺序 = 登记顺序；
  `"branch"` MUST 取自 `_ConditionalEdgeSpec.branch`（**MUST NOT** 重新推断）；
  `path_map` 已是归一化结果（原样搬运）。
  ⇒ 落点：FR-009 · 裁定 12 · SC-010。
- **Q13（`GraphSpec.conditional_edges`）**：B7F2 填不填？
  → **A：不填（恒空）**。B7F1 的 `GraphSpec.conditional_edges` 是**预留**字段，非空即
  V-8 显式失败 ⇒ B7F2 **MUST NOT** 填 ⇒ 条件边分支规格只挂在 `CompiledGraph` 的私有
  字段里（B6F1 D-2）⇒ 由 **B8F1** 落地时填入并承接 V-8 放宽（下游承接 D-2）。
  ⇒ 落点：FR-004 / FR-009 · 裁定 13 · SC-010。

### 裁定编号映射（本 spec 的唯一裁定编号表）

| 裁定 | 内容 | 来源 |
|---|---|---|
| **裁定 1** | `compile()` 签名逐字沿用 B6F1 / B2F2 冻结面；只实现、不增删关键字 | Q1 · H-7 |
| **裁定 2** | 编译产物实现体在 L3 私有模块；类名 `CompiledGraph`；不继承 L1 协议；不进门面导出面 | Q2 · H-7 |
| **裁定 3** | 编译产物持五组内容：`_spec` / `_builder_spec` / `_conditional_edges`（**三个私有字段名冻结为跨 feature 接口**）+ 注入项（**公开实例属性**，上游 `Pregel` 同款；`transformers` 命名差异见 X-12）+ 归一后的断点（**公开实例属性** `interrupt_before_nodes` / `interrupt_after_nodes`）；除此以外公开属性面 MUST 为空 | Q3 · H-2 / D-2 / D-3 / D-5 |
| **裁定 4** | 编译期检查清单 14 项（MUST 查）与不检查项 7 项（MUST NOT 查）逐条写死 | Q4 · H-1 |
| **裁定 5** | 只过滤单源 `END` 目标；空目标元组的源键整体移除；多源形态原样交给 V-16 | Q5 · H-2 / H-5 |
| **裁定 6** | 静态断点：入口只做**容器形态门**（`None` / `str` / `list`；`str` 原样透传）；元素级与裸字符串失败信号由 `GraphSpec` 归一逐字产出 | Q6 · H-4 |
| **裁定 7** | `checkpointer` / `store` 接受 + 记录 + 不报错 + 不做类型校验；`store` v1 无实现须写明 | Q7 · H-7 · D-4 |
| **裁定 8** | 未就绪能力面抛内置 `NotImplementedError`，消息点名归属 feature | Q8 |
| **裁定 9** | 编译期**不做**可达性 / 环检查 | Q4 / Q9 |
| **裁定 10** | 编译产物持通道**规格**（模板），运行期由 L2 新建实例 | Q10 · H-3 |
| **裁定 11** | 可重复编译、产物独立；不引入 `compiled` 标志与「改图」警告 | Q11 |
| **裁定 12** | 条件边 plain mapping 的形状逐字按 B6F1 D-2 | Q12 · H-2 |
| **裁定 13** | B7F2 **MUST NOT** 填 `GraphSpec.conditional_edges`（恒空） | Q13 · H-2 · D-2 |
| **裁定 14** | 传入 **`store=`** 时 MUST 发**恰好 1 条** `warnings.warn`（点名「v1 不支持 `Store`」）；其余「已接受但 v1 无行为」的注入项（`checkpointer` / `cache` / `transformers` / `debug` / `name`）**只记录 + 文档写明**，MUST NOT 发警告 | 第二轮用户裁定（选项 A）· 偏离登记 X-3 |

### 引文差异（提示词初稿 vs 本 spec）

| # | 差异 | 处置 |
|---|---|---|
| **引文差异 1** | 提示词 §2 把「**节点不可达**」列为编译期校验的例子 | **裁定 9 / FR-006**：编译期**不做**可达性检查（上游同款 + 动态路由不健全 + 会误伤合法用法）⇒ 明确列入「不检查项」 |
| **引文差异 2** | 提示词 §3 P3 的独立验收写「**路由目标不在 `path_map` 里**」应在编译期被指出 | **裁定 4 / FR-005 / FR-006**：编译期可判定的是「`path_map` 的**目标节点**不存在」与「`path_map` **形态**非法」；「路由**返回值**不在 `path_map` 中」只有调用路由函数才知道 ⇒ 编译期**不可判定** ⇒ 归 B8F1 运行期显式失败（提示词该处措辞不精确，此处写死） |
| **引文差异 3** | 提示词 §4 FR-004 说未就绪方法「可先抛明确『未实现』异常」，未指定类型 | **裁定 8 / FR-011**：冻结为内置 `NotImplementedError`（与 B6F1 同款）⇒ MUST NOT 新增异常类型 |
| **引文差异 4** | 提示词 §4 FR-002 说「关键字 MUST 被接受且被记录到编译产物中」，未说是否校验类型 | **裁定 7 / FR-016**：接受 + 记录 + **不校验类型** + **不报错**；`store` 的 v1 无实现 MUST 在文档写明；**第二轮用户裁定**：传 `store=` 时**额外发 1 条 warning**（当场可见 · 裁定 14） |
| **引文差异 5** | 提示词 §9 说「编译产物结构与 LangGraph 的对应须标注源码行号（`langgraph/graph/state.py:1177` `compile`）」 | 本 spec 按 **langgraph 1.2.11** 本次取证逐行展开（`state.py:1177-1189` 签名 · `:1234` checkpointer 校验 · `:1264-1272` 归一与校验 · `:1346-1371` 产物构造 · `:1373-1399` 挂载 · `:1404-1407` 类定义）⇒ 行号以本次取证为准 |
| **引文差异 6** | 提示词 §7 把「`CompiledGraph`」列为关键实体，未说明它与 L1 协议的关系 | **裁定 2 / FR-003**：实现体在 L3 私有模块、类名同名、**不继承** L1 纯抽象协议（结构化子类型）⇒ 门面导出面零变化 |
| **引文差异 7** | 提示词 §2 说「编译产物**就是**运行时」（上游 `CompiledGraph(Pregel)`） | **裁定 10 / FR-012 / 偏离登记 X-1**：freegraph **分层归属不同** —— 编译产物**持有并驱动** L2 运行时，而非成为运行时的基类 ⇒ 这是**已知结构差异**（原则 XII「层次对应优先于容器对应」），非功能缺失 |

### Session 2026-11-16 · 第二轮（上游自查补记 · clarify 阶段）

> **纪律**（宪法 v1.9.0 原则 XI + clarify 的收窄纪律）：**上游有答案 ⇒ 照抄 ⇒ 不问用户**。
> 本轮逐条复查了初版 spec 的 5 处「自设约束」，结论全部是**上游已有答案** ⇒
> **直接照抄并改写 spec**（不产生新问题、不消耗用户决策预算）。

| # | 初版 spec 的自设约束 | 上游答案（`langgraph 1.2.11`） | 处置 |
|---|---|---|---|
| **S-1** | 编译产物「**公开属性面 MUST 为空**」（初版 FR-002 / FR-010 / 裁定 3） | 上游 `Pregel` **公开暴露** `checkpointer`（`pregel/main.py:819`）· `store`（`:820`）· `cache`（`:821`）· `debug`（`:818`）· `name`（`:830`）· `interrupt_before_nodes` / `interrupt_after_nodes`（`:814-815`） | **照抄**：注入项与断点配置 MUST 以**公开实例属性**暴露（FR-010 / 裁定 3 / SC-002 / SC-015 改写）；其余（`_spec` / `_builder_spec` / `_conditional_edges`）保持私有 ⇒ 新增 **P-03c** 与 **X-10** |
| **S-2** | 「编译产物类不进门面导出面」被写成 freegraph 的**自设**约束 | 上游 `langgraph/graph/__init__.py` 的 `__all__` **不含** `CompiledStateGraph` ⇒ 上游同款 | **照抄并补锚点**：新增 **P-03b**（判词 SAME）⇒ FR-002 的「零新增导出」有了上游依据 |
| **S-3** | `debug` 的缺省行为未在 Upstream Parity 中登记 | 上游 `debug=None` ⇒ `get_debug()`（`pregel/main.py:818`）读 `langchain_core.globals` 的**环境变量** | **登记差异**：新增 **P-17b** 与 **X-9**（零环境变量红线 · 与 B13F1 X-4 同族）⇒ freegraph 缺省**硬编码** `False` |
| **S-4** | FR-011 让 6 个方法全部抛 `NotImplementedError`，与 L1 协议「`get_state` **查不到** MUST NOT 抛异常」的措辞**表面冲突** | 上游无「未实现」态（6 方法全部实现）⇒ 上游**无答案** ⇒ 属自研区，但**无需用户决策**：协议那条约束的是**已实现后**的「查不到」语义 | **加边界说明**（FR-011 末段）：`NotImplementedError` 是「**尚未交付**」信号，与协议的「查不到 ⇒ 空值」**不同层、不冲突** |
| **S-5** | 编译产物的私有字段名只写在裁定 3 里，**未声明**它们是跨 feature 冻结接口 | 上游用 `compiled.builder`（`state.py:1408`）等公开属性做交接；freegraph 走私有载体 ⇒ **必须冻结字段名**，否则 B8F1 / B8F3 / B22F1 无从按名读取 | **补冻结声明**：FR-008 / FR-010 / 裁定 3 明确 `_spec` / `_builder_spec` / `_conditional_edges` 三个**字段名冻结**（下游承接 D-2 / D-3 / D-5 按名读取） |

- Q: 用户给 `compile()` 传了 `store=`（或 `checkpointer=`）这类「v1 背后没有实现」的能力时，编译这一步要不要给用户一个**当场可见的信号**（比如发一条 warning），还是只默默记下来、在文档里写明？ → A: **选项 A** —— 只对 **`store=`** 发**恰好 1 条** `warnings.warn`（v1 **永久**无实现 ⇒ 警告永不过期、无需下游撤除）；`checkpointer=` / `cache=` / `transformers=` / `debug=` / `name=` 只记录 + 文档写明（`checkpointer` 只是**暂时**未实现 · B14F1 落地即真 ⇒ 不给它加「以后要记得删」的警告）。⇒ 落点：FR-016 · SC-015 · Edge Cases · 偏离登记 X-3 · 裁定 14 |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 一行拿到可执行图 (Priority: P1)

作为用户，我写完建图代码后调 `agent_builder.compile()`，就得到一个**带完整能力面**的
可执行对象，不需要自己拼装任何规格。

**Why this priority**: 这是本 feature 的**最高判据**（提示词 P1 / A1 / A2 / SC-001），
也是 **MVP 六项最小交付集**的第 2 项。

**Independent Test**: 建一张 2 节点的图 → 调 `compile()`（**无参**）⇒ 断言返回一个
非空对象，且 `invoke` / `stream` / `get_graph` / `get_state` / `get_state_history` /
`update_state` **六个方法全部存在**（`hasattr` 逐个断言）。

**Acceptance Scenarios**:

1. **Given** 一张含 2 个节点与 3 条静态边的合法图，**When** 调用 `compile()`（无参），
   **Then** 成功返回一个编译产物对象（非 `None`），且其 6 个能力面方法全部存在。
2. **Given** 同一张图，**When** 连续调用 `compile()` 两次，**Then** 两次都成功，
   返回**两个彼此独立**的产物（改其中一个不影响另一个）。
3. **Given** 一张合法图，**When** 调用 `compile()`，**Then** 编译过程**不执行**任何
   用户节点函数 / 路由函数 / 归约器（调用计数为 0）。

---

### User Story 2 - 编译时能注入可插拔能力 (Priority: P1)

作为用户，我希望能 `compile(checkpointer=..., store=...)` 传入自己的持久化与存储实现，
**接口先立住**，后续能力上线时不必改我的调用代码。

**Why this priority**: 「同名同签名」是宪法原则 III 第 6 项的**硬要求**；验收脚本
`harness/demo/graph_core.py` 的 A3 组会**直接断言**这两个关键字被接受（不抛 `TypeError`）。

**Independent Test**: 对同一张合法图分别调用 `compile()`、`compile(checkpointer=None,
store=None)`、`compile(checkpointer=object(), store=object())` ⇒ 三次都**不抛异常**，
且传入的对象能在编译产物上被**读到**（记录生效）。

**Acceptance Scenarios**:

1. **Given** 一张合法图，**When** 调用 `compile(checkpointer=None, store=None)`，
   **Then** 不抛 `TypeError`，编译成功。
2. **Given** 一张合法图，**When** 调用 `compile(checkpointer=<任意对象>, store=<任意对象>)`，
   **Then** 不抛异常；两个对象被**记录**到编译产物（可经公开实例属性读到），
   且**恰好 1 条** warning 提示「v1 不支持 `Store`」。
3. **Given** 传入的 `store`，**When** 用户阅读文档，**Then** 文档**显式写明**
   「v1 不支持 `Store`」⇒ 用户不会误以为传入即生效。

---

### User Story 3 - 编译期发现图定义的问题 (Priority: P1)

作为用户，我希望「边指向不存在的节点」「路由目标不在 `path_map` 里」这类问题在
**编译时**被指出，而不是跑到一半才炸。

**Why this priority**: 提示词 P3 / SC-003 要求 3 类错误各有一例且消息可定位；
**编译期校验**是本 feature 相对上游的主要增量之一。

**Independent Test**: 三类错误各建一个反例，断言异常类型为内置 `ValueError` /
`TypeError`、消息含**问题节点名 / 分支名**，且**在 `compile()` 调用点**抛出
（不是推迟到运行期）。

**Acceptance Scenarios**:

1. **Given** 已登记节点 `a` 且已 `add_edge(START, "a")`，**When**
   `add_edge("a", "missing")` 后调用 `compile()`，**Then** 抛 `ValueError`，
   消息含 `missing`。
2. **Given** 已登记节点 `a`，**When** `add_conditional_edges("nope", router, ["a"])`
   后调用 `compile()`，**Then** 抛 `ValueError`，消息含 `nope`。
3. **Given** `add_conditional_edges("a", router, {"x": "missing"})`，**When** 调用
   `compile()`，**Then** 抛 `ValueError`，消息含源节点、分支与目标节点名。
4. **Given** 上述任一错误图，**When** 调用 `compile()`，**Then** 失败发生在**编译调用点**
   （不是 `invoke()` 时），且**消息点名具体问题**。

---

### User Story 4 - 静态断点随编译一并落地 (Priority: P2)

作为用户，我希望能 `compile(interrupt_before=["my_node"])` 把「在某个节点前暂停」的
意图交给编译，并且**写错的节点名当场被指出**，而不是等我跑到那个节点才发现配置无效。

**Why this priority**: B13F1 已交付静态断点的内核语义，但**对外形态**（`compile()` 的
两个关键字 + 编译期可达性）由本 feature 承担（承接 H-4）；写错节点名的**早失败**
是「编译期是最后的机会做静态检查」的直接体现。

**Independent Test**: 分别用 `interrupt_before=None` / `"*"` / `["a"]` / `["nope"]` /
`("a",)` / `"a"` 六种形态调用 `compile()` ⇒ 逐个断言接受或失败，且失败信号与
`GraphSpec` 构造期**逐字同款**。

**Acceptance Scenarios**:

1. **Given** 一张含节点 `a` 的图，**When** 调用 `compile(interrupt_before=["a"])`，
   **Then** 编译成功，且断点配置落在编译产物的图规格里（节点名 `a`）。
2. **Given** 一张含节点 `a` 的图，**When** 调用 `compile(interrupt_before="*")`，
   **Then** 编译成功，且断点被解释为**全部可执行节点**。
3. **Given** 一张图，**When** 调用 `compile(interrupt_before=["nope"])`，
   **Then** 在**编译期**抛 `ValueError`，消息含 `nope`。
4. **Given** 一张图，**When** 调用 `compile(interrupt_before=("a",))`（元组），
   **Then** 在**编译期**抛 `TypeError`（容器形态非法）。

---

### User Story 5 - 一次编译，多次安全使用 (Priority: P2)

作为用户，我希望**编译一次**就能在多个会话里反复用，而且互不干扰；并且我在编译之后
继续改构建器，**已经编译好的那张图也不会被改坏**。

**Why this priority**: B12F1 已把「每次运行从规格新建通道实例」落在 L2；本 feature 的
义务是把它**对外暴露**（H-3）；「编译产物是快照」则是编译期语义正确性的基础
（否则「编译后改图」会静默改变已编译产物）。

**Independent Test**: 编译一张图 → 改构建器（再加一个节点）→ 断言已编译产物的节点表
**未变**；连续两次 `compile()` → 断言两个产物的节点表**互不影响**。

**Acceptance Scenarios**:

1. **Given** 已编译的产物与同一构建器，**When** 在构建器上再 `add_node("c", fn)`，
   **Then** 已编译产物的节点表**不变**（仍是编译时的快照）。
2. **Given** 同一构建器，**When** 调用 `compile()` 两次，**Then** 两个产物的节点表 /
   边表 / 通道表**彼此独立**（改一个不影响另一个）。
3. **Given** 已编译的产物，**When** 检查其持有的通道，**Then** 每个通道都是**未被写入过
   值的规格模板**（零状态残留）。

---

### User Story 6 - 编译期零副作用 (Priority: P3)

作为用户，我希望编译这一步**不**偷偷跑我的节点、**不**读我的环境变量、**不**联网，
以免「只是编译一下」却触发了副作用。

**Why this priority**: 宪法原则 I（零出站 / 零环境变量）与原则 V（零出站的可判定
证据）是**红线**；且编译期副作用会与运行期副作用混淆，破坏可诊断性。

**Independent Test**: 编译一个节点 / 路由函数 / 归约器都带调用计数器的图 ⇒ 编译后
计数器全为 0；用 socket 监测夹具观测 ⇒ freegraph 自身出站连接数 = 0。

**Acceptance Scenarios**:

1. **Given** 节点函数 / 路由函数 / 归约器都带调用计数器，**When** 调用 `compile()`，
   **Then** 三个计数器全部为 0。
2. **Given** 任意环境变量（含 `LANGSMITH_*`），**When** 调用 `compile()`，
   **Then** 编译行为**不因环境变量而改变**，且 freegraph 自身发起 0 次出站连接。

---

### Edge Cases

- **空图 / 空节点表**：`compile()` 在构造图规格时**显式失败**（内置 `ValueError`），
  MUST NOT 产出一个空的可执行图。
- **缺少 `START` 入口**：编译期失败（内置 `ValueError`，消息含 `entrypoint` / `START`），
  错误早于运行期。
- **单源边指向 `END`**：编译期**过滤**该目标（freegraph 的节点表不含 `END`）；若该源
  因此**没有任何目标**，该源键**整体移除**（不留空边）。
- **多源边的目标为 `END`**：**MUST NOT** 过滤 ⇒ 原样交给图规格的 **V-16** ⇒ 编译期
  显式失败（内置 `ValueError`）。
- **多源边的目标数 ≠ 1**：MUST NOT 提前拒绝 ⇒ 原样交给图规格的 **V-16** ⇒ 编译期
  显式失败。
- **多源边的源含 `START`**：**构建器立即层 `add_edge` 已拒绝**（`START` 不在节点表
  ⇒ `ValueError`）⇒ 不属于 `compile()` 路径；若直接构造图规格，则由 **V-16** 显式失败。
- **节点名为 `__parent__`**：MUST NOT 在编译层另立检查 ⇒ 原样交给图规格的**保留名
  检查** ⇒ 编译期显式失败（内置 `ValueError`）。
- **`path_map=None`（动态路由）**：合法；编译期**不**知道路由会跳向何处 ⇒
  MUST NOT 因此报错；条件边分支规格照常挂好（`targets=()` / `route_channels=()`）。
- **`path_map` 的目标含 `END`**：合法；`END` **不建**路由通道（沿用 B6F1 的口径）。
- **同一目标被多个分支引用**：共享同一个 `branch:to:<target>` 路由通道（沿用 B6F1）。
- **`interrupt_before=None`**：归一为 `()`（不配置）。
- **`interrupt_before="*"`**：展开为**全部可执行节点**（排除 `START` / `END`）。
- **`interrupt_before=[]`（空列表）**：合法 ⇒ 等价于「不配置」。
- **`interrupt_before=["*"]`**：**失败**（`"*"` 只能是裸值，不能作为元素）。
- **`interrupt_before=[""]`（空串元素）**：失败（内置 `ValueError`）。
- **`interrupt_before=["__start__"]` / `["__end__"]`**：失败（内置 `ValueError`，
  二者不是可挂起的节点名）。
- **`interrupt_before=[123]`（非 `str` 元素）**：失败（内置 `TypeError`）。
- **`interrupt_before=("a",)`（元组）**：**入口层**失败（内置 `TypeError`）⇒ 图规格
  本身接受序列（这是 B13F1 D-1 指定的「只在 compile 入口层收紧」）。
- **`interrupt_before="a"`（裸非 `"*"` 字符串）**：入口层原样透传 `str` ⇒ **由
  `GraphSpec` 归一在 `compile()` 调用点失败**（内置 `TypeError`，与构造期逐字同款）。
- **`interrupt_before` 与 `interrupt_after` 同时给**：两个字段**各自独立**校验与归一。
- **`checkpointer=False`**：**接受**并记录（上游的「不用 checkpointer」语义）⇒
  MUST NOT 报错 ⇒ MUST NOT 发警告（见下条）。
- **`cache=` / `debug=` / `name=` / `transformers=`**：接受并记录；v1 **无行为**
  ⇒ MUST NOT 报错、MUST NOT 静默生效（`cache` 归 v2 extras · `transformers` 归 B8F2 ·
  `debug` 归可观测层 · `name` 归 B22F1 的图导出）。
- **`store=` 传入非 `Store` 对象**：接受并记录 ⇒ MUST NOT 报错（MUST NOT 静默生效）
  ⇒ **发恰好 1 条 `warnings.warn`**（点名「v1 不支持 `Store`」· 裁定 14）。
- **`store=` 未传 / 传 `None`**：MUST **不**发警告（警告条数 == **0**）。
- **`checkpointer=` 传入对象（含 `False`）**：接受并记录 ⇒ MUST NOT 报错 ⇒
  **MUST NOT** 发警告（裁定 14 ②：它的「未实现」是**暂时**的，B14F1 落地即真）。
- **对**已编译**的构建器继续 `add_node` / `add_edge`**：允许；MUST NOT 发警告
  （B6F1 已裁定不复制上游的 `compiled` 标志副作用）；**下一次** `compile()` 取新快照。
- **同一构建器 `compile()` 两次**：合法；两次产物**彼此独立**。
- **编译产物被用户拿到后改其私有字段**：本 feature 不冻结私有字段的不可变性
  （MUST NOT 因此新增异常类型）⇒ 但**公开属性面 MUST 为空**（注入项与断点属性
  除外 · FR-010）。
- **图规格的条件边字段**：B7F2 阶段**恒空** ⇒ 图规格的 V-8 校验**不触发**。
- **`invoke()` / `stream()` 等未就绪方法被调用**：抛内置 `NotImplementedError`，
  消息点名归属 feature ⇒ MUST NOT 抛 `AttributeError`、MUST NOT 静默返回 `None`。

---

## Upstream Parity *(mandatory — 宪法 v1.9.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11**（取证于 2026-11-16 ·
`/home/ctyun/workspace/github/freegraph/.venv/lib/python3.11/site-packages/langgraph`）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | `compile()` 的方法名与关键字集合 | `langgraph/graph/state.py:1177-1189`（签名） | 同名同签名；关键字集合逐字沿用 B6F1 / B2F2 冻结面 | SAME | 宪法原则 III 第 6 项 |
| P-02 | `compile()` **无参可调用** | `langgraph/graph/state.py:1177-1189`（全部关键字有缺省） | 同款：全部关键字可省 | SAME | 宪法原则 III 第 6 项 · 验收脚本 A3 |
| P-03 | 编译产物**类型与基类链** | `langgraph/graph/state.py:1404-1407`（`CompiledStateGraph(Pregel)`）· `langgraph/pregel/main.py:450`（`class Pregel`） | `CompiledGraph` **持有并驱动** L2 运行时，**不**是运行时的基类 | DIFF | freegraph 把执行内核（L2）与图定义（L3）**分层归属** ⇒ X-1 |
| P-03b | 编译产物类**是否进门面导出面** | `langgraph/graph/__init__.py`（`__all__` = `END` / `START` / `StateGraph` / `add_messages` / `MessagesState` / `MessageGraph` · **不含** `CompiledStateGraph`） | **不进** `freegraph.graph` 的导出面（7 符号冻结 · B2F2）⇒ 用户只从 `compile()` 的返回值拿到它 | SAME | 上游同款 ⇒ 「零新增导出」有上游依据，非自设约束 |
| P-03c | 编译产物**公开暴露的属性** | `langgraph/pregel/main.py:814-815`（`interrupt_after_nodes` / `interrupt_before_nodes`）· `:818`（`debug`）· `:819`（`checkpointer`）· `:820`（`store`）· `:821`（`cache`）· `:830`（`name`）· `:831`（`stream_transformers`）· `:800`（`nodes`）· `:804`（`channels`） | 暴露**注入项与断点配置**为公开实例属性（`checkpointer` / `store` / `cache` / `debug` / `name` / `transformers` / `interrupt_before_nodes` / `interrupt_after_nodes`）；**内部规格**（`_spec` / `_builder_spec` / `_conditional_edges`）保持私有 | SAME（`checkpointer` / `store` / `cache` / `debug` / `name` / 断点）/ **DIFF（`transformers` 命名 ⇒ X-12**；不公开 `nodes` / `channels` / `builder` ⇒ **X-10**） | 注入项同款照抄 ⇒ 用户可观察；`transformers` 沿用 compile 关键字名、与上游 `stream_transformers` 不同名 ⇒ **X-12**；内部规格私有是分层接缝 ⇒ X-10 |
| P-03d | 断点属性的**值形态** | `langgraph/pregel/main.py:814-815` + 实测 E-47 / E-48（上游**保留原值**：`"*"` 仍是 `"*"`、`None` ⇒ `[]`、list 原样） | `interrupt_before_nodes` / `interrupt_after_nodes` 暴露 **`GraphSpec` 归一后的保序元组**（`"*"` 已展开、`None` → `()`） | DIFF | 单一语义只留一个载体（原则 XII）· 用户读到的是**实际生效**的节点集合 ⇒ X-11（**2026-11-16 plan 阶段补记**） |
| P-04 | 编译产物**挂载节点** | `langgraph/graph/state.py:1373-1375`（`attach_node` 循环）· `:1444`（`attach_node` 定义） | 编译产物持**节点任务规格**（订阅集 + 节点函数）⇒ 结构同构 | SAME | 原则 XI 照抄 · 分层只改归属不改结构 |
| P-05 | 静态断点的**接受形态与归一** | `langgraph/graph/state.py:1183-1184`（关键字）· `:1264-1265`（`or []` 归一）· `:1525-1530`（`"*"` 的运行期解释） | 接受 `None` / 裸 `"*"` / `list[str]`；`None` ⇒ `()`；`"*"` ⇒ **全部可执行节点**（**编译期**展开） | SAME | 可观察语义同款；**展开时机**差异（编译期 vs 运行期）已由 **B13F1 的 X-2** 登记 |
| P-05b | 静态断点的**裸空串** | `langgraph/graph/state.py:1264`（`interrupt_before or []` ⇒ `""` 被当作「不配置」） | 入口原样透传 `str` ⇒ **由 `GraphSpec` 归一在 `compile()` 调用点**显式失败（内置 `TypeError` · V-22 家族） | STRICTER | 上游的静默接受会让用户以为配置生效 ⇒ X-2 |
| P-05c | 静态断点的**元组 / 裸非 `"*"` 字符串** | `langgraph/graph/state.py:1267-1272`（`str` / `tuple` 与 `list` 拼接 ⇒ 编译期 `TypeError`） | 元组 ⇒ **入口层**显式失败；裸非 `"*"` 串 ⇒ **入口原样透传，由 `GraphSpec` 归一在 `compile()` 调用点**失败（内置 `TypeError` · V-22 家族）⇒ **失败信号家族一致** | SAME | 上游是**拼接副作用**、freegraph 是**显式门** ⇒ 消息不同、类型同款 |
| P-06 | **编译期校验** | `langgraph/graph/state.py:1267-1272`（`self.validate(...)`）· `:1129-1175`（`validate`：源 → 入口 → 目标 → 断点节点） | 编译期做**等价**校验（源 / 入口 / 目标 / 断点可达性 / 节点表非空）⇒ 逐条见 FR-005 | SAME | 校验项与失败信号同款；**顺序**同款（先源 / 入口，再目标） |
| P-07 | 编译产物**挂载边** | `langgraph/graph/state.py:1391-1395`（`attach_edge` 两条循环）· `:1551`（`attach_edge` 定义） | 编译产物持**触发依赖**（边表）⇒ 结构同构 | SAME | 原则 XI 照抄 |
| P-08 | **边表键类型**（单源 / 多源） | `langgraph/graph/state.py:1391-1395`（上游 `self.edges` / `self.waiting_edges` **分开**） | 键为 `str \| tuple[str, ...]`，**照原样透传** ⇒ MUST NOT 在编译层重建屏障语义 | SAME | **B7F4** 的兼容性扩展（只放宽不收紧）· H-5 |
| P-09 | `store=` 关键字 | `langgraph/graph/state.py:1182`（关键字）· `:1367`（传给产物）· `langgraph/pregel/main.py:820`（`self.store = store`） | 关键字**被接受并记录**，v1 **背后无实现**（B17 已砍 · 宪法原则 VII）⇒ MUST NOT 报错、MUST NOT 静默生效；**额外发 1 条 warning**（裁定 14） | DIFF | 原则 VII 定位推导出的硬边界 ⇒ X-3 |
| P-10 | `checkpointer=` 关键字与**编译期类型校验** | `langgraph/graph/state.py:1179`（关键字）· `:1234`（`ensure_valid_checkpointer`）· `langgraph/types.py:109-118`（非法 saver ⇒ `TypeError`） | 关键字**被接受并记录**；**编译期不做**类型校验 | DIFF | v1 的 checkpointer 实现归 B14F1 ⇒ 「尚未就绪」不应被误报为「用户错误」⇒ X-4（下游承接 D-4） |
| P-11 | 编译产物**挂载条件分支** | `langgraph/graph/state.py:1397-1399`（`attach_branch` 循环）· `:1577`（定义） | 分支规格挂在 `CompiledGraph` 的**私有普通映射**；`GraphSpec.conditional_edges` **恒空** | DIFF | 分层接缝：L2 的预留字段由 **B8F1** 填 ⇒ X-6 |
| P-12 | 指向 `END` 的边 | `langgraph/graph/state.py:1391-1392`（`attach_edge(start, END)` 保留） | 单源 `→ END` 的边在编译期被**过滤**（freegraph 的节点表不含 `END`） | DIFF | 分层接缝：B6F1 D-1 + 图规格 V-2 ⇒ 语义等价（到达 `END` = 停止）⇒ X-7 |
| P-13 | 编译后的「**已编译**」状态与改图提示 | `langgraph/graph/state.py:1174`（`self.compiled = True`）· `:788-791` / `:945-948` / `:1012-1015`（其后 `add_node` / `add_edge` / `add_conditional_edges` 发 **`logging` 提示** —— 实测 E-49 / E-50：`warnings` 捕获 0 条、`logging` 捕获 1 条） | **不**设 `compiled` 标志、**不**发任何提示；可重复编译 | DIFF | **B6F1** 已裁定不复制该副作用（范围边界）⇒ X-5 |
| P-14 | 通道集合（`START` 通道 + 路由通道） | `langgraph/graph/state.py:1354-1358`（`channels={**self.channels, **self.managed, START: EphemeralValue(self.input_schema)}`）· `:98`（`_CHANNEL_BRANCH_TO`）· `:1525-1530`（路由通道 = `EphemeralValue(Any, guard=False)`） | 路由通道 `branch:to:<target>` + `EphemeralValue(Any, guard=False)` **同款**；**不**额外建 `START` 通道（入口由边表哨兵承担）；路由通道**只为条件边静态目标**建（上游为**每个节点**建 · 实测 E-43） | DIFF | 入口哨兵机制属 L2 的既有冻结面；「只为条件边目标建」是 **B6F1 裁定 3 / FR-020** 的既有口径（首在编译期可观察）⇒ X-8 |
| P-15 | 编译产物只持通道**规格** · 每次运行新建实例 | `langgraph/channels/last_value.py:50-54`（`from_checkpoint` → `self.__class__(...)`）· `langgraph/channels/base.py:61-64`（docstring 逐字「Return a **new identical channel**」） | 编译产物持通道**模板**；每次运行由 L2 从规格新建实例（`superstep.py:575-591` 的 `_run_channels`） | SAME | 上游同款 ⇒ 「一次编译、多会话隔离」天然成立 |
| P-16 | 编译产物的**能力面**（6 方法） | `langgraph/pregel/main.py:845`（`get_graph`）· `:1392`（`get_state`）· `:1480`（`get_state_history`）· `:2515`（`update_state`）· `:2616+`（`stream`）· `:3783+`（`invoke`） | 6 方法**全部存在**；未就绪者抛内置 `NotImplementedError`（消息点名归属 feature） | SAME（方法面）/ DIFF（未就绪者的失败信号） | 方法面是 B2F1 冻结的**协议**；未就绪者 MUST NOT 抛 `AttributeError` |
| P-17 | 其余编译选项（`cache` / `debug` / `name` / `transformers`） | `langgraph/graph/state.py:1180-1188`（关键字）· `:1364-1368`（传给产物） | 接受并记录；v1 **无行为** | SAME（接受面） | 关键字集合与接受面同款；行为差异归各自归属 feature。⚠️ `name` 的**缺省值**上游是 `"LangGraph"`（实测 E-33）、freegraph 是 `None`（B2F2 快照冻结）⇒ 属**签名冻结面**，不另登记偏离 |
| P-17b | `debug` 的**缺省值来源** | `langgraph/pregel/main.py:818`（`debug if debug is not None else get_debug()`）· `get_debug` 来自 `langchain_core.globals`（**读环境变量**） | `debug` 缺省**硬编码** `False`（B6F1 冻结签名）⇒ **零环境变量读取** | DIFF | 宪法原则 I：环境变量存在 MUST NOT 改变任何行为 ⇒ X-9（与 B13F1 X-4 同族） |
| P-18 | **可达性 / 环**的编译期检查 | 上游 `compile()` **不做**（`state.py:1267-1272` 只调 `validate()`） | **不做** ⇒ 明确列入「不检查项」 | SAME | 原则 XI 照抄 + 动态路由使静态判定不健全 ⇒ 裁定 9 |

> **实测覆盖说明**：P-01 / P-02 / P-05 / P-05b / P-05c / P-06 / P-09 / P-10 / P-13 / P-17
> 的**行为**断言 MUST 有实测支撑（上游缺席即 skip · 沿用 B5F2 的「缺席即 skip」纪律）；
> P-03 / P-04 / P-07 / P-11 / P-12 / P-14 / P-15 / P-16 / P-18 属**结构面**断言
> （源码锚点 + 差分场景的可观察结果）⇒ 换版本时 MUST 一并重跑。

### 差分场景组 *(mandatory)*

> **落点**：`tests/differential/parity_probe.py` ⇒ CI 的 Linux 全量档真跑
> （上游缺席即 `skip`）。本 feature 的差分只做**编译**，**不执行**节点。

| # | 场景 | 断言（编译成败 / 异常类型 / 可观察产物） | 判词 |
|---|---|---|---|
| D-75 | 最小合法图 + `compile()`（无参） | 两侧均编译成功；产物非空且具备 6 方法能力面 | SAME |
| D-76 | `compile(checkpointer=None, store=None)` | 两侧均编译成功 | SAME |
| D-77 | `compile(checkpointer=<非 saver 对象>)` | 上游编译期抛 `TypeError`；freegraph **接受并记录** | DIFF（X-4） |
| D-78 | `compile(store=<任意对象>)` | 两侧均编译成功；freegraph v1 **无实现**（不生效）**且发 1 条 warning**；上游的 store **真能生效**、不发 warning | DIFF（X-3） |
| D-79 | `compile(interrupt_before=["nope"])`（未知节点） | 两侧均**编译期**失败；freegraph 消息含 `nope` | SAME |
| D-80 | `compile(interrupt_before="*")` | 两侧均成功；freegraph 在**编译期**展开为全部可执行节点 | SAME（展开时机差异归 B13F1 X-2） |
| D-81 | `compile(interrupt_before=("a",))`（元组） | 两侧均**编译期** `TypeError` | SAME（P-05c） |
| D-82 | `compile(interrupt_before="")`（裸空串） | 上游**接受**（当作不配置）；freegraph `TypeError` | STRICTER（X-2） |
| D-83 | `compile(interrupt_before="a")`（裸非 `"*"` 字符串） | 两侧均**编译期** `TypeError` | SAME（P-05c） |
| D-84 | `compile(interrupt_before=["*"])` | 两侧均**编译期**失败（元素非法） | SAME |
| D-85 | 边指向不存在的节点 | 两侧均**编译期**失败；freegraph 消息含目标名 | SAME |
| D-86 | 缺少 `START` 入口 | 两侧均**编译期**失败；消息含 `entrypoint` / `START` | SAME |
| D-87 | 条件边源不存在 | 两侧均**编译期**失败；freegraph 消息含源节点名 | SAME |
| D-88 | `path_map` 目标指向不存在的节点 | 两侧均**编译期**失败；freegraph 消息含源 / 分支 / 目标 | SAME |
| D-89 | `path_map=None`（动态路由） | 两侧均编译成功；freegraph **不**在编译期报错 | SAME |
| D-90 | `compile()` 后再 `add_node` | 上游发 warning；freegraph **不发**、编译产物不变 | DIFF（X-5） |
| D-91 | 同一构建器连续 `compile()` 两次 | 两次产物彼此独立；上游亦为两次独立产物 | SAME |

### 偏离登记 *(三类 + 已知不支持（DIFF）· 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | 结构性差异（分层接缝 · DIFF） | P-03：编译产物**不是**运行时的基类，而是**持有并驱动** L2 运行时的门面 | 上游 `CompiledStateGraph(Pregel)`（`state.py:1404-1407`）的编译产物**就是**运行时；freegraph 把执行内核（L2）与图定义（L3）**分层归属**（立项书 §5.1）⇒ 原则 XII「层次对应优先于容器对应」⇒ 这是**已知结构差异**，非能力缺失 | 既有（分层拍板）· **B7F3** 起逐棒沿用 |
| **X-2** | 更严失败信号（STRICTER） | P-05b：静态断点的**裸空串** `interrupt_before=""` ⇒ 编译期 `TypeError` | 上游 `interrupt_before or []`（`state.py:1264`）把 `""` 当作「不配置」而**静默接受** ⇒ 用户会以为配置生效 ⇒ freegraph 显式早失败（V-22 家族） | 本 feature 内闭合 · 判据零放宽 |
| **X-3** | 结构性差异（定位边界 · DIFF） | P-09：`store=` 的 v1 语义 —— **接受并记录，但背后无实现**，且**额外发 1 条 warning**（裁定 14） | 宪法原则 VII：「图 = 一个进程」⇒ 跨会话 `Store` **不属 v1**（B17 已砍 · 2026-11-05）⇒ 关键字仍被接受（API 兼容 · C10），但**MUST NOT** 静默生效，文档 MUST 显式写明；**上游的 store 是真能用的** ⇒ 上游无此警告的对应物 ⇒ freegraph 补一条**当场可见**的信号（用户不必等到「对话没记忆」才发现没生效） | 既有（原则 VII）· v2 补实现 |
| **X-4** | 结构性差异（能力未就绪 · DIFF） | P-10：编译期**不做** checkpointer 的类型校验 | 上游 `ensure_valid_checkpointer`（`types.py:109-118`）在编译期对非法 saver 抛 `TypeError`；freegraph v1 的 checkpointer 实现归 **B14F1** ⇒ 编译期做「实现合法性」判定会把「**尚未就绪**」误报成「**用户错误**」 | **B14F1**（下游承接 D-4）MUST 补上上游同款的编译期校验 |
| **X-5** | 结构性差异（范围边界 · DIFF） | P-13：不复制上游的 `compiled=True` 标志与「已编译后再改图」的 **`logging` 提示**（上游用 `logging`，**不是** `warnings` · E-49/E-50） | **B6F1** 已裁定不复制该副作用（范围边界，不影响校验判据）⇒ 本 feature 继承 | 既有（B6F1 P-09 / 裁定 9） |
| **X-6** | 结构性差异（分层接缝 · DIFF） | P-11：条件边分支规格挂 `CompiledGraph` 的**私有普通映射**；`GraphSpec.conditional_edges` **恒空** | B7F1 的 `conditional_edges` 是**预留**字段（非空即 V-8 失败）⇒ B7F2 填它会**直接失败**；分支规格改由 L3 私有载体交接（B6F1 D-2）⇒ 由 B8F1 填入并承接 V-8 放宽 | **B8F1**（下游承接 D-2） |
| **X-7** | 结构性差异（分层接缝 · DIFF） | P-12：单源 `→ END` 的边在编译期被**过滤** | freegraph 的图规格节点表**不含** `END`（`END` 是终止哨兵）⇒ 不过滤会被 V-2 判死；语义等价（到达 `END` = 停止） | 既有（B6F1 D-1 + 图规格 V-2） |
| **X-8** | 结构性差异（分层接缝 · DIFF） | P-14：编译产物**不**额外建 `START` 通道 | 上游把 `START` 作为一条 `EphemeralValue(input_schema)` 通道（`state.py:1354-1358`）；freegraph 的入口由**边表哨兵**承担（L2 既有冻结面）⇒ 入口语义等价 | 既有（L2 契约 §2.1） |
| **X-9** | 结构性差异（零环境变量红线 · DIFF） | P-17b：`debug` 的缺省值**硬编码** `False`（上游 `debug=None` ⇒ `get_debug()` 读 `langchain_core.globals` 的**环境变量**） | 宪法原则 I：环境变量存在 MUST **NOT** 改变任何行为 ⇒ 与 **B13F1 X-4**（递归上限硬编码 10007）同族 | 既有（红线）· 无需追认 |
| **X-10** | 结构性差异（分层接缝 · DIFF） | P-03c：编译产物**不公开** `nodes` / `channels` / `builder`（上游 `Pregel` 三者皆公开） | ① freegraph 的编译产物持**快照**而非活构建器 ⇒ 公开活构建器会与 FR-019 的「编译后改图不影响已编译产物」语义打架；② 内部规格经由 **B22F1 的 `get_graph()`** 导出（下游承接 D-5）⇒ 无需用户直接摸内部结构 | 既有（分层接缝 + FR-019）· **B22F1** 承接导出 |
| **X-11** | 结构性差异（形态优化 · DIFF） | P-03d：断点属性 `interrupt_before_nodes` / `interrupt_after_nodes` 暴露**归一后的保序元组**（上游**保留原值**：`"*"` / list / `None` ⇒ `[]`） | 原则 XII：同一语义只留**一个载体** —— `GraphSpec` 已是归一真源，再存一份用户原值就出现「两处都有一份」；且用户读到的是**实际会生效**的节点集合（原则 IV 可诊断性）。**语义等价**，只是可见形态不同；`"*"` 的**展开时机**差异已由 **B13F1 的 X-2** 登记 | 本 feature 内闭合 · **2026-11-16 plan 阶段补记**（实测 E-47 / E-48 发现） |
| **X-12** | 命名形态差异（DIFF） | P-03c：freegraph 的公开属性名为 `transformers`，上游 `Pregel` 的对应属性名为 `stream_transformers`（`pregel/main.py:831`；E-31 的公开属性清单**不含** `transformers`） | 与 `compile(transformers=...)` 关键字**同名**、单一载体（原则 XII）；语义等价，只是可见属性名不同；改名为 `stream_transformers` 会与冻结的 compile 关键字割裂 | 本 feature 内闭合 · **2026-11-16 analyze 修复轮补记**（对照实测 E-31 / `main.py:831`） |

### 破冻结面的回溯修订清单

本 feature **不破**任何既有公开契约面：

- `freegraph.graph` 的 7 个导出符号不变（B2F2 冻结面）；
- `StateGraph.compile` 的公开签名**逐字不变**（B2F2 快照仍成立）；
- L1 的 `CompiledGraph` **协议**不变（6 方法 · 返回类别 · 参数名）；
- B7F1 的 `GraphSpec` / `NodeSpec` / `run_super_step` / `run_super_steps` 签名与语义不变；
- B6F1 的 `_build_spec()` / `_BuilderSpec` / `_ConditionalEdgeSpec` / `_NodeRecord` 形状不变。

**既有测试口径更新（非公开冻结面 · 按宪法 v1.11.0 记录）**：

- `tests/facade/test_facade.py::TestNotWired`：`compile()` 不再抛 `NotImplementedError`，
  测试 MUST 收窄到「其余未交付方法」（`add_sequence` / `set_entry_point` /
  `set_conditional_entry_point` / `set_finish_point` / `set_node_defaults`）。
- `harness/demo/graph_core.py` 的 `main()` / `_facade_ready()` 守卫：`compile()` 不再抛
  `NotImplementedError` ⇒ 改为「**先跑 A3（`case_build_and_compile`）再探 `invoke`**」：
  ① `compile()` 仍不可用 ⇒ 沿用退出码 **2**（不变）；
  ② `compile()` 可用、`invoke()` 仍未就绪（B7F3）⇒ **在 A3 通过之后**以退出码 **2**
  结束并打印 `[环境未就绪]`；
  ③ `invoke()` 也就绪 ⇒ 正常跑全部用例（退出码 0 / 1）。
  ⚠️ **MUST NOT** 把守卫改成「产物具备 6 方法能力面 ⇒ 视为已就绪」——那会让
  `graph_core` 在 `invoke` 未就绪时跑完全部用例并以 **1** 结束，打红既有硬断言
  `test_graph_core_exits_two_when_the_facade_is_not_ready`（rc == 2）。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001（`compile()` 入口）**：系统 MUST 提供 `compile()`，**无参可调用**（C10 ·
  宪法原则 III 第 6 项）。签名 MUST **逐字**沿用 B6F1 / B2F2 的冻结面：
  `compile(self, checkpointer=None, *, cache=None, store=None, interrupt_before=None,
  interrupt_after=None, debug=False, name=None, transformers=None) -> CompiledGraph`；
  MUST NOT 增删 / 改名 / 改序任何关键字；MUST NOT 因「关键字未就绪」而抛
  `TypeError`（除用户传入非法**容器形态**的静态断点，见 FR-013）。

- **FR-002（编译产物）**：系统 MUST 把构建器规格编译成**一个**可执行对象并返回。
  该对象 MUST 满足 L1 的 `CompiledGraph` **协议**（6 方法全部可被结构化子类型判定
  命中）⇒ **MUST NOT** 继承该协议（L1 协议纯抽象 · 无继承链 · PD-1）；MUST 住在
  **L3 私有模块** ⇒ **MUST NOT** 进入 `freegraph.graph` 的导出面（上游同款：
  `langgraph/graph/__init__.py` 的 `__all__` **不**含 `CompiledStateGraph`）；
  除 FR-010 列出的**注入项与断点属性**外，其公开属性面 MUST 为空。

- **FR-003（可执行结构）**：编译产物 MUST 持以下可执行结构：
  ① **节点任务规格**（订阅集 + 节点函数）；② **每节点的触发依赖**（边表）；
  ③ **路由通道**（`branch:to:<target>` 的 `EphemeralValue` · `guard=False`）；
  ④ **分支规格**（条件边的源 / 分支名 / 路由函数 / 归一化 `path_map` / 静态目标 /
  路由通道名）。
  ⇒ ①②③ 落在 L2 的 `GraphSpec` 里；④ 落在编译产物的**私有普通映射**里。

- **FR-004（图规格形态）**：本 feature MUST 把 L3 的声明式规格**适配**为 B7F1 的
  `GraphSpec` / `NodeSpec` ⇒ **MUST NOT** 另造第三套形态；MUST NOT 改写节点入参的
  key 顺序（子映射 MUST 按「**通道映射的顺序**」构造）；MUST NOT 改写
  `run_super_step` / `run_super_steps` 的接收口径；B7F2 阶段
  `GraphSpec.conditional_edges` **MUST 恒空**（⇒ 图规格的 V-8 校验不触发）。

- **FR-005（编译期检查清单 · MUST 查）**：编译期 MUST 执行以下**逐条**检查，失败
  MUST 在**编译调用点**抛出，且消息 MUST 指明具体问题：

  | # | 检查项 | 失败信号 | 判定来源 |
  |---|---|---|---|
  | C-01 | schema 合法性 | `InvalidSchemaError`（B4F1） | `parse_state_schema` |
  | C-02 | 静态边源存在（`START` 除外） | 内置 `ValueError` | 构建器构建期末层 |
  | C-03 | 入口存在（`START` 作为某条边的源） | 内置 `ValueError`（消息含 `entrypoint` / `START`） | 构建器构建期末层 |
  | C-04 | 静态边目标存在（`END` 除外） | 内置 `ValueError` | 构建器构建期末层 + 图规格 V-2 |
  | C-05 | 条件边源存在 | 内置 `ValueError` | 构建器构建期末层 |
  | C-06 | 条件边目标存在（`END` 除外） | 内置 `ValueError`（消息含源 / 分支 / 目标） | 构建器构建期末层 |
  | C-07 | 节点表非空 | 内置 `ValueError` | 构建器 + 图规格 V-3（**防御性**：compile 链路中空图先命中 C-03/C-04） |
  | C-08 | 节点订阅的通道存在 | 内置 `ValueError` | 图规格 V-1（**防御性**：`_build_spec()` 的订阅集恒来自 schema 通道） |
  | C-09 | 保留节点名（`__parent__`） | 内置 `ValueError` | 图规格（保留名检查） |
  | C-10 | 多源边的形态（非空 / 不含 `START` / 目标恰为一个 / 目标不为 `END`） | 内置 `ValueError` | 图规格 V-16 |
  | C-11 | 静态断点的**容器形态**（`None` / `str` / `list` 之外） | 内置 `TypeError` | **compile 入口层**（`str` 原样透传；裸非 `"*"` 串由 `GraphSpec` 归一在 `compile()` 调用点抛 `TypeError`） |
  | C-12 | 静态断点的**元素**（空串 / `START` / `END` / `"*"` / 非 `str` / 未知节点） | 内置 `ValueError` / `TypeError`（与图规格构造期**逐字同款**） | 图规格归一（V-22…V-25） |
  | C-13 | `path_map` 的**形态**（容器 / 元素 / value 的类型） | 内置 `TypeError` | 构建器立即层 |
  | C-14 | `path_map` 的**目标节点**存在 | 内置 `ValueError` | 构建器构建期末层 |

  ⚠️ 检查 MUST 在**编译期**完成 ⇒ MUST NOT 推迟到 `invoke()` / `stream()`。
  ⚠️ **例外（C-13）**：`path_map` 的**形态**由构建器**立即层**在
  `add_conditional_edges` 时就已失败 ⇒ 它**早于** `compile()`（不满足「编译期」的
  字面时机，但方向更早、更严）⇒ 其用例 MUST 包裹**登记调用**，MUST NOT 假定
  `compile()` 会抛。C-13 的失败信号由 B6F1 冻结，本 feature 不重复判定。

- **FR-006（明确不检查项 · MUST NOT 查）**：编译期 MUST **NOT** 做以下判定
  （逐条列明，避免「过严误伤」与「过松推迟」两种失败）：

  | # | 不检查项 | 理由 | 归属 |
  |---|---|---|---|
  | N-01 | 路由函数的**返回值**是否在 `path_map` 中 | 只有**调用**路由函数才知道返回值；`path_map=None` 的动态路由在编译期**不可知** | B8F1 运行期显式失败 |
  | N-02 | 节点函数的**返回形态**（`dict` / `Command` / 命令列表 / `Send` / `None`） | 运行期才知道 | B7F3 / B9F1 / B11F1 |
  | N-03 | 节点**可达性** / 不可达节点 | 动态路由使静态可达性判定**不健全**；上游**不做** | 无（明确不做） |
  | N-04 | 环 / 死循环 | 运行期的步数上限（`recursion_limit`）负责 | B13F1 |
  | N-05 | `checkpointer` / `store` 是否满足协议 | v1 无实现；「尚未就绪」不应被误报为「用户错误」 | B14F1（下游承接 D-4） |
  | N-06 | 节点入参形状 / 归约器组合是否合法 | 运行期才知道 | B4F1 / B5F1 |
  | N-07 | `path_map` 的**键**（路由返回值）是否可枚举 | 编译期不可知 | B8F1 |

- **FR-007（`END` 过滤与多源透传）**：编译期 MUST **仅过滤单源键**（`str`）中目标为
  `END` 的边；过滤后目标元组为空的**源键 MUST 整体移除**（不留空边）；**多源键**
  （`tuple`）的 `END` 目标 MUST NOT 被过滤 / 提前拒绝 ⇒ MUST 原样交给图规格的
  **V-16** 显式失败；节点名 `__parent__` MUST 原样交给图规格的**保留名检查**显式失败。
  ⇒ 边表 MUST **照原样透传**（键类型 `str | tuple[str, ...]`）⇒ MUST NOT 在编译层
  重建屏障语义。

- **FR-008（构建器快照消费）**：系统 MUST 从 `StateGraph._build_spec()` 取得
  `_BuilderSpec` ⇒ MUST NOT 重新解析 schema、MUST NOT 重造节点表 / 边表 / 通道表、
  MUST NOT 另立第三套图规格；MUST 保留**完整** `_BuilderSpec`（至少 `node_records`）
  于编译产物的私有字段（**字段名 MUST 冻结为 `_builder_spec`** —— 跨 feature 接口，
  供 B8F3 读取别名），且 MUST NOT 改写其内容。

- **FR-009（条件边的机械翻译）**：系统 MUST 把 `_BuilderSpec.conditional_edges`
  **机械翻译**为 plain mapping `dict[str, tuple[dict[str, Any], ...]]`：外层 key =
  `source`；内层每个 dict 的 key / value 逐字为
  `{"branch": str, "path": Callable[..., Any], "path_map": dict[Hashable, str] | None,
  "targets": tuple[str, ...], "route_channels": tuple[str, ...]}`；顺序 = 登记顺序；
  `"branch"` MUST 取自 `_ConditionalEdgeSpec.branch`（**MUST NOT** 重新推断）；
  `path_map` MUST 原样搬运（已是归一化结果，`None` 保持 `None`）。
  该映射 MUST 存放在编译产物的**私有字段**里。

- **FR-010（编译产物的持有面）**：编译产物 MUST 持有：① L2 的 `GraphSpec`
  （私有字段 `_spec`）；② 完整 `_BuilderSpec`（私有字段 `_builder_spec`）；
  ③ 条件边的 plain mapping（私有字段 `_conditional_edges`）——
  ①②③ 的**字段名 MUST 冻结**（B8F1 / B8F3 / B22F1 MUST 按名读取）；④ 被注入的
  `checkpointer` / `store` / `cache` / `debug` / `name` / `transformers`；
  ⑤ **归一后**的 `interrupt_before` / `interrupt_after`（元组）。
  ⇒ ④⑤ MUST 以**公开实例属性**暴露（**MUST NOT** 用 `@property` —— 否则
  `vars(compiled)` 看不到它们，SC-010 的「11 键」口径不成立）；除 `transformers` 外，
  属性名 MUST 与上游 `Pregel` 同款：
  `checkpointer` / `store` / `cache` / `debug` / `name` /
  `interrupt_before_nodes` / `interrupt_after_nodes`
  （上游 `langgraph/pregel/main.py:814-815` / `:818-830`）；**例外**：`transformers`
  沿用 `compile()` 关键字名（上游对应属性名为 `stream_transformers` · `:831`）⇒
  **命名形态差异登记 X-12** ⇒ 用户 MUST 能读到
  被注入的对象（⇒ SC-002 / SC-015 的可观察口径）；⇒ **④⑤ 之外**的公开属性面
  MUST 为空（内部规格一律私有）。
  **「只读」的口径**：只读 = **用户不需要写**；本 feature **MUST NOT** 断言
  「赋值被拒」（不为此新增异常类型 · FR-018）。
  另：`_spec.channels` 与 `_builder_spec.channels` MUST 是**两个独立的映射对象**
  ⇒ 运行期对 `_spec.channels` 的内部通道增补 MUST NOT 改写构建器快照
  （FR-008 的「MUST NOT 改写其内容」）。

- **FR-011（能力面 6 方法）**：编译产物 MUST 具备 `invoke` / `stream` / `get_graph` /
  `get_state` / `get_state_history` / `update_state` **六个**方法（**MUST NOT** 静默
  不存在 ⇒ MUST NOT 出现 `AttributeError`）；本 feature **未就绪**者 MUST 抛内置
  `NotImplementedError`，消息 MUST 点名归属 feature（`invoke` → B7F3 ·
  `stream` → B8F2 · `get_graph` → B22F1 · `get_state` / `get_state_history` → B15F1 ·
  `update_state` → B16F1）⇒ MUST NOT 静默返回 `None`、MUST NOT 新增异常类型。
  ⚠️ **与 L1 协议措辞的边界**：协议里「`get_state` **查不到**时返回**空值**、
  MUST NOT 抛异常」约束的是**已实现之后**的「查不到」语义；本条的
  `NotImplementedError` 是「**该能力尚未交付**」信号 ⇒ **两者不同层、不冲突**
  （实现落地后 MUST 恢复协议的「查不到 ⇒ 空值」语义）。

- **FR-012（通道「规格」· 多会话隔离）**：编译产物 MUST 持通道**规格**（模板）⇒
  MUST NOT 在编译期向任何通道写入值；MUST NOT 把「已被某次运行写过值」的通道实例交给
  运行；每次运行的通道实例 MUST 由 L2 从规格**新建** ⇒ 「一次编译、多会话隔离」在
  编译产物这一侧 MUST 成立（本 feature 交付**持规格**的一半；**每次 `invoke` 新建
  实例**的一半归 B7F3）。

- **FR-013（静态断点关键字）**：`compile(interrupt_before=..., interrupt_after=...)`
  MUST 被接受，并 MUST 原样填入 `GraphSpec.interrupt_before` / `interrupt_after`。
  ① **容器形态** = FR-005 的 **C-11**（唯一规范正文）：MUST 只接受 `None` /
  `str` / `list`；`None` 归一为 `()`；**`str` 原样透传**（裸非 `"*"` 字符串（含空串）
  由 `GraphSpec` 归一在 `compile()` 调用点抛内置 `TypeError`，与构造期**逐字同款**）；
  元组 / `set` / 数值等其它容器 ⇒ 入口层抛内置 `TypeError`（**V-22 家族**）。
  ② **元素级** = FR-005 的 **C-12**：失败信号 MUST 与图规格构造期**逐字同款**
  （空串 / `START` / `END` / `"*"` / 非 `str` / 未知节点）⇒ ⇒ 入口层 MUST **只做
  容器形态门**（`str` 原样透传），MUST NOT 另写一套元素校验。
  ③ MUST NOT 另立第三套静态断点载体。

- **FR-014（静态断点的编译期可达性）**：不存在的断点节点名 MUST 在**编译期**失败
  （内置 `ValueError`，消息**点名该节点**），MUST NOT 推迟到 `invoke()`；裸 `"*"`
  MUST 解释为**全部可执行节点**（排除 `START` / `END`）。

- **FR-015（编译期零副作用）**：编译 MUST **NOT** 执行任何节点函数 / 路由函数 /
  归约器；MUST NOT 读任何环境变量；MUST NOT 有任何 I/O / 出站；MUST NOT 产生任何
  线程 / 子进程。

- **FR-016（可插拔能力的注入）**：`checkpointer=` / `store=` MUST 被接受并**记录**到
  编译产物 ⇒ MUST NOT 抛 `TypeError`、MUST NOT 报错；MUST **NOT** 在编译期做类型
  校验；MUST **NOT** 静默生效 ⇒ 文档 MUST 显式写明「**v1 不支持 `Store`**」
  （宪法原则 VII）与「checkpointer 的行为归 B14F1」。`cache=` / `debug=` / `name=` /
  `transformers=` 同样 MUST 被接受并记录（v1 无行为 ⇒ MUST NOT 报错）。
  ① **传入 `store=`（非 `None`）时 MUST 发恰好 1 条 `warnings.warn`**，消息 MUST 点名
  「v1 不支持 `Store`」（⇒ 用户当场知道「没生效」）；**未传 `store=` 时 MUST 不发**
  （警告条数 == **0**）⇒ ⇒ 该警告是 v1 的**长期事实**（v2 补实现后随 `Store` 一并
  落地），MUST NOT 留下「以后要记得撤除」的尾巴。
  ② `checkpointer=` / `cache=` / `transformers=` / `debug=` / `name=` **MUST NOT** 发
  警告（它们要么**暂时**未实现 · 各自归属 feature 落地即真 ⇒ 警告会变成需要下游撤除
  的尾巴；要么语义明确无歧义）⇒ 只记录 + 文档写明。

- **FR-017（公开 API 面零新增）**：`freegraph.graph` 的 7 个导出符号 MUST 不变；
  `StateGraph` 的公开方法签名 MUST 不变（B2F2 快照仍逐字节成立）；编译产物的实现
  类 MUST NOT 出现在公开快照中。

- **FR-018（异常类型面）**：编译期的失败 MUST 只用内置 `ValueError` / `TypeError`
  （schema 非法沿用 B4F1 的 `InvalidSchemaError`；未就绪能力面用内置
  `NotImplementedError`）⇒ 本 feature MUST NOT 新增任何异常类型。

- **FR-019（重复编译与快照隔离）**：同一构建器 MUST **可多次** `compile()`，每次
  MUST 产出**独立**的产物（节点表 / 边表 / 通道表 / 条件边映射彼此不共享可变状态）；
  构建器在编译后的任何变更 MUST **NOT** 影响已编译的产物；本 feature MUST **NOT**
  引入「已编译」标志、**MUST NOT** 发「已编译后再改图」的警告。

- **FR-020（最小图可编译）**：最小图（2 节点 + `START` / `END` 边）MUST **可被
  编译**（承接 B3F1 延后的 FR-005 ③② 的「编译」环节）⇒ 运行期断言留给 B7F3
  ⇒ **MUST NOT** 新增门禁编号、红线**不放宽**。

- **FR-021（顺序与确定性）**：通道 key 顺序 MUST = schema 声明顺序（其后追加路由
  通道，顺序 = 静态目标首次出现顺序）；节点表顺序 MUST = 登记顺序；边表顺序 MUST =
  登记顺序（源键顺序 + 目标顺序）；条件边顺序 MUST = 登记顺序；分支目标 / 路由通道
  顺序 MUST = 归一化映射的首次出现顺序。相同输入的两次 `compile()` MUST 产生
  **结构等价**的产物。

- **FR-022（固定脚本）**：`harness/demo/target.py` MUST NOT 被修改（只读基准）；
  `harness/demo/graph_core.py` 的 A3 组（`compile()` 无参可调用 · 产物具备
  `invoke` / `stream` · `compile(checkpointer=None, store=None)` 被接受）MUST 通过。

- **FR-023（依赖与分层）**：本 feature MUST **NOT** import `langchain` /
  `langchain-core` / `langsmith` / `langgraph*`；MUST NOT 读任何环境变量；
  MUST 只依赖标准库与 L1 / L2 内部模块；L3 MUST **NOT** 被 L1 / L2 反向 import。

- **FR-024（不越界到下游语义）**：本 feature MUST **NOT** 实现 `invoke()` 的执行
  语义、`stream()`、条件边求值、`get_graph` / `draw_mermaid`、checkpointer / store 的
  **行为**、节点别名语义 ⇒ 相应能力 MUST 保持显式「未实现」信号。

- **FR-025（`checkpointer` 的 v1 语义与下游补齐）**：MUST NOT 在编译期对
  `checkpointer` 做协议校验（见 FR-006 N-05）⇒ **B14F1** MUST 补上上游同款的
  编译期类型校验 ⇒ 本 feature MUST 在**下游承接**中点名该义务。

### Key Entities

| 实体 | 语义 | 契约 |
|---|---|---|
| **`CompiledGraph`** | 编译产物；对外能力面协议在 B2F1 已定义；本 feature 交付实现 | **C10** / C11 / C12 / C13 / C19 |
| **`GraphSpec`** | L2 的手写图规格（通道映射 + 保序节点表 + 边表）；编译产物的可执行结构主体 | C5 / C6 / C7 · H-1 |
| **节点任务规格 `NodeSpec`** | 「订阅 channel → 读 → 写」 | C5 / C6 · H-1 |
| **分支规格** | 条件边（`path_map` 双形态）的交接载体 | C7 · FR-009 |
| **路由通道** | `EphemeralValue`，键名 `branch:to:<target>`，每 super-step 清空 | C7 / C8 · FR-003 |
| **`_BuilderSpec`** | 构建器 → 编译层的冻结内部规格（含 `node_records`，供 B8F3） | FR-008 · D-3 |
| **可注入能力** | `checkpointer` / `store` / `cache` / `debug` / `name` / `transformers`（v1 记录不生效） | C19 / C20 · FR-016 |

### 需求 ↔ 成功标准 追溯表

| 需求 | 成功标准 | 验收判据 |
|---|---|---|
| FR-001 | SC-001 / SC-002 / SC-013 | A2 / A3 |
| FR-002 | SC-001 / SC-013 | A1 |
| FR-003 | SC-004 / SC-009 | A1 |
| FR-004 | SC-009 / SC-010 | A1 |
| FR-005 | SC-003 / SC-006 / SC-007 / SC-008 | A1 |
| FR-006 | SC-006 | A1 |
| FR-007 | SC-008 | A1 |
| FR-008 | SC-010 | A1 |
| FR-009 | SC-010 | A1 |
| FR-010 | SC-010 / SC-015 | A1 |
| FR-011 | SC-008 / SC-015 | A1 |
| FR-012 | SC-011 / SC-012 | A1 |
| FR-013 | SC-005 / SC-007 | A1 |
| FR-014 | SC-005 / SC-007 | A1 |
| FR-015 | SC-005 | A1 |
| FR-016 | SC-002 / SC-015 | A3 |
| FR-017 | SC-013 | A1 |
| FR-018 | SC-003 / SC-008 | A1 |
| FR-019 | SC-012 | A1 |
| FR-020 | SC-014 | A1 |
| FR-021 | SC-004 / SC-012 | A1 |
| FR-022 | SC-001 / SC-014 | A3 |
| FR-023 | SC-005 | A1 |
| FR-024 | SC-008 / SC-015 | A1 |
| FR-025 | SC-015 | A1 |

### Out of Scope

- `invoke()` 的**执行语义** —— 属 **B7F3**（本 feature 只保证方法存在且显式未实现）。
- `stream()` —— 属 **B8F2**。
- 条件边**求值**与 fresh 读 —— 属 **B8F1**（本 feature 只把分支规格挂好）。
- `get_graph()` / `draw_mermaid()` / `draw_mermaid_png()` —— 属 **B22F1** / **B23F1**。
- 状态查询（`get_state` / `get_state_history` / `update_state`）—— 属 **B15F1** /
  **B16F1**。
- checkpointer 的**行为**与**编译期类型校验** —— 属 **B14F1**（本 feature 只接受 + 记录）。
- `Store` 的**行为** —— v1 **无实现**（B17 已砍 · 2026-11-05 · 宪法原则 VII）。
- `cache=` 的**行为** —— v2 extras（`specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml`）。
- `transformers=` 的**行为** —— 属 **B8F2**（流式转换器）。
- `debug=` 的**行为** —— 属可观测层（B19F1 及以后）。
- 节点**别名**语义 —— 属 **B8F3**（本 feature 只保留 `_BuilderSpec.node_records`）。
- `defer=True` 的节点专用屏障 —— **B7F4** 的 X-03（本 feature 只透传）。
- 多源汇合的**屏障语义** —— **B7F4**（本 feature 只透传边表）。
- 子图 —— v2（C26）。
- 任何运行期行为 / 持久化 / trace。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：`compile()` **无参**调用成功，返回**非空**的编译产物实例；
  `harness/demo/graph_core.py` 的 A3 组「`compile()` 无参可调用」断言**通过**
  （口径：`graph_core` 在**编译可用时先执行 A3 组**；随后若 `invoke` 仍未就绪
  （B7F3），则在 **A3 通过之后**以**退出码 2** 结束 —— 既有
  `tests/runtime/test_acceptance_script.py` 的「rc == 2」硬断言因此**保持绿**）。
- **SC-002**：`compile(checkpointer=None, store=None)` 被接受（**不抛异常**）；
  `compile(checkpointer=<任意对象>, store=<任意对象>)` 亦被接受，且两个对象可经
  **公开实例属性** `compiled.checkpointer` / `compiled.store` **读到**（同一对象，
  `is` 相等）⇒ 被记录并可观察的比率 **100%**；`harness/demo/graph_core.py` 的 A3 组
  「`compile(checkpointer=None, store=None)` 关键字被接受」断言**通过**（同 SC-001 的
  「先跑 A3、再以退出码 2 结束」口径）。
- **SC-003**：编译期校验的 **3 类错误**（边目标不存在 / 条件边源不存在 / 条件边目标
  不存在）各有一例被捕获；异常类型为内置 `ValueError`，消息含**问题节点名**；
  且失败发生在**编译调用点**（不是运行期）。
- **SC-004**：编译产物的能力面 **6 个方法全部存在**（`hasattr` 逐个断言，命中率
  **100%**）；未就绪者抛内置 `NotImplementedError`（**零** `AttributeError`）。
- **SC-005**：编译过程**不读环境变量**、**不发起网络请求**（freegraph 自身出站连接数
  == **0**）、**不执行**任何用户函数（节点 / 路由 / 归约器的调用计数 == **0**）。
- **SC-006**：编译期检查清单的 **14 项**各有**至少一例**被验证（正向或反例；
  其中 **C-07 / C-08 为防御性检查**，以正向用例覆盖即可）；「明确不检查项」的 **7 项**
  各有**至少一例**证明编译期**未**对其报错（尤其：动态路由 `path_map=None` 的图
  **编译成功**）。
- **SC-007**：静态断点的 **6 种形态**（`None` / 裸 `"*"` / `list[str]` / 元组 /
  裸非 `"*"` 字符串 / 未知节点名）各有一例；**元素级与裸字符串**形态（空串 / `START` /
  `END` / `"*"` / 非 `str` / 裸非 `"*"` 串）的失败信号与图规格构造期**逐字同款**的
  比率 == **100%**；**容器形态**（元组 / `set` / 数值等）只要求同为内置 `TypeError`；
  未知节点名的失败消息**点名该节点**的比率 == **100%**。
- **SC-008**：单源 `END` 目标被过滤（过滤后该源若无其它目标则该边**整体消失**）；
  多源 `END` 目标与多源目标数 ≠ 1 在编译期**显式失败**（内置 `ValueError`）；
  `__parent__` 节点名在编译期**显式失败**；未就绪能力面抛 `NotImplementedError` 的
  方法数 == **6**（本 feature 内 6 个方法**全部**未就绪 ⇒ 消息分别点名 B7F3 / B8F2 /
  B22F1 / B15F1 / B15F1 / B16F1）。
- **SC-009**：编译产物的**节点表 / 通道表**与 B6F1 的构建器快照**逐项一致**
  （节点数、通道 key 序列、订阅集）；**边表在应用 FR-007 的单源 `END` 过滤后**与快照
  逐项一致（过滤后边数 == 快照边数减去被移除的单源 `END` 项）；节点入参的 key 顺序
  MUST 等于「通道映射的顺序」⇒ 顺序一致的比率 == **100%**；边表键类型**未被改写**
  （`str` / `tuple` 原样）。
- **SC-010**：条件边的 plain mapping 形状**逐字**符合 B6F1 D-2（外层 key = 源节点名；
  内层 5 个 key 逐字一致；顺序 = 登记顺序；`"branch"` 取自构建器登记值）的比率
  == **100%**；`GraphSpec.conditional_edges` **恒空**（B7F2 阶段填充次数 == **0**）；
  完整 `_BuilderSpec`（含 `node_records`）**保留**在编译产物上。
- **SC-011**：编译产物持有的通道**全部是未被写入过值的规格模板**（**非零**状态残留的
  通道数 == **0**）；编译产物**不**持有任何「已被某次运行写过值」的通道实例。
- **SC-012**：同一构建器连续 `compile()` 两次 ⇒ 两个产物的可变状态**互不影响**
  （改一个的通道 / 边 / 节点**不影响**另一个的比率 == **100%**）；构建器在编译后
  新增节点 ⇒ 已编译产物的节点表**不变**（比率 == **100%**）；编译后改图**不**产生
  警告。
- **SC-013**：`freegraph.graph` 的 **7 个导出符号不变**；B2F2 的公开 API 快照
  **逐字节不变**；编译产物的实现类**不出现**在公开快照中；`freegraph.graph` 内
  **零**新增导出。
- **SC-014**：最小图（2 节点 + `START` / `END` 边）**可被编译**；固定脚本
  `harness/demo/target.py` 的 git diff 为**空**。
- **SC-015**：`checkpointer` / `store` / `cache` / `debug` / `name` / `transformers`
  六个关键字**全部被接受且被记录**（记录的比率 == **100%**、报错的比率 == **0%**），
  且可经**公开实例属性**逐个读到（同名属性齐全的比率 == **100%**）；
  传入 `store=` 时发出的 `warnings.warn` **恰好 1 条**（消息点名「v1 不支持
  `Store`」），未传 `store=` 时警告条数 == **0**；其余注入项引发的警告条数 == **0**；
  文档**显式写明**「v1 不支持 `Store`」与「checkpointer 的行为归 B14F1」。
- **SC-016**：差分场景 **D-75…D-91** 的判词与 Upstream Parity 表**逐条一致**；
  上游缺席即 `skip`（沿用 B5F2 纪律）；判词与对照表不一致的行数 == **0**。

---

## Assumptions

- 上游版本固定为 `langgraph 1.2.11`（核实环境：`.venv/lib/python3.11/site-packages/langgraph`）。
  换版本 MUST 重新核实 `路径:行号`，MUST NOT 凭记忆沿用。
- B6F1 的 `_build_spec()` / `_BuilderSpec` / `_ConditionalEdgeSpec` / `_NodeRecord`
  已交付且冻结；本 feature 只消费，MUST NOT 私自扩展其字段（需要扩展 MUST 走正式
  回溯修订）。
- B7F1 的 `GraphSpec` / `NodeSpec` 已交付且冻结；本 feature 的适配 MUST NOT 改写
  其构造签名、字段语义与两个低层入口的接收口径。
- B5F1 的 `Channel` / `EphemeralValue` 已交付；本 feature 只实例化与透传。
- B4F1 的 `InvalidSchemaError` 原样向上传播；本 feature MUST NOT 包装或降级。
- B13F1 的静态断点归一函数是**唯一**的断点形态判定来源；本 feature MUST NOT 另写
  一套元素校验（只做容器形态门）。
- B8F1 落地时会把条件边映射填入 `GraphSpec.conditional_edges` 并承接 V-8 放宽；
  在那之前该字段恒空。
- B8F3 从本 feature 保留的 `_BuilderSpec.node_records` 读取 `_NodeRecord.alias`。
- B14F1 补上上游同款的 checkpointer 编译期类型校验（下游承接 D-4）。
- 「同名同签名」的签名比较口径 = 方法名 + **必填位置参数 / 顺序** + 返回语义 +
  关键字**接受面**；MUST NOT 要求默认值或注解逐字相同（本 feature 未改任何默认值）。
- 编译产物的**私有字段名**（`_spec` / `_builder_spec` / `_conditional_edges`）属
  **实现细节**，不构成对外承诺；注入项与归一断点**只以 8 个公开实例属性持有，不另存
  私有副本**（⇒ `vars(compiled)` 恰 11 键）；对外承诺只有「6 方法能力面」与
  「编译期失败信号」。
- `harness/demo/target.py` 是**只读基准**；本 feature 不修改任何一行。
- 本 feature 只交付「**编译**」环节；固定脚本端到端可跑仍需 B7F3 / B8F1 / B22F1 /
  B23F1 齐备。

---

## 依据

- 立项书 §4.3（第 6 项 `compile()`）、§5.1（编译产物即运行时实例 · 分层拍板）、
  §5.2（B7F2 行）、§5.3（C10 / C11 / C12 / C13 / C19 / C20）、§6.2（M2 里程碑）、
  §9.1（门禁）。
- 宪法 `.specify/memory/constitution.md`：原则 I（零出站 / 零环境变量）· 原则 III
  （7 项 MUST 同名同签名）· 原则 VI（可追溯性 MUST 到判据级）· 原则 VII（`Store`
  不属 v1 · `compile(store=...)` 仍被接受）· 原则 IX（依赖许可证红线）· 原则 X
  （文档合规）· 原则 XI（上游优先）· 原则 XII（最优设计优先 · 层次对应优先）。
- 上游源码（`langgraph 1.2.11`）：`langgraph/graph/state.py:1177-1189`（`compile`
  签名）· `:1234`（`ensure_valid_checkpointer` 调用）· `:1264-1272`（断点归一与
  `validate` 调用）· `:1346-1371`（`CompiledStateGraph` 构造）· `:1373-1399`
  （`attach_node` / `attach_edge` / `attach_branch` 挂载）· `:1404-1407`（类定义）·
  `:1525-1530`（路由通道 `EphemeralValue(Any, guard=False)`）· `:98`
  （`_CHANNEL_BRANCH_TO`）· `langgraph/pregel/main.py:450`（`class Pregel`）· `:814-831`
  （公开属性 · `stream_transformers`）· `:845`（`get_graph`）·
  `langgraph/channels/last_value.py:50-54` ·
  `langgraph/channels/base.py:61-64` · `langgraph/types.py:109-118`。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C10 编译 / C19
  checkpointer / C20 store）。
- 调度契约：`specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §2.1 /
  §2.1.1（`GraphSpec` / `NodeSpec` 形态 · V-1 / V-2 / V-3 / V-8 / V-16 · 裁定 26 /
  裁定 27 / 裁定 32）。
- 上游承接：`specs/b6f1-stategraph-builder/spec.md` **D-1 / D-2** ·
  `specs/b13f1-static-interrupt-recursion-limit/spec.md` **D-1 / D-2** ·
  `specs/b12f1-concurrency-errors/spec.md` **D-4** ·
  `specs/b7f4-multisource-join/spec.md` **D-5** ·
  `specs/b3f1-scaffold-ci-gates/spec.md` 裁定 22。
- 验收脚本：`harness/demo/graph_core.py`（`case_build_and_compile` · A3 组）·
  `harness/demo/target.py`（只读基准）。
- 公开 API 快照：`specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`
  （`StateGraph.compile` 的冻结签名）。
