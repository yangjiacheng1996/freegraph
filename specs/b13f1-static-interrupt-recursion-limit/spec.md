# Feature Specification: B13F1 · 静态中断点（`interrupt_before` / `interrupt_after`）+ `recursion_limit`

**Feature Branch**: `b13f1-static-interrupt-recursion-limit`

**Created**: 2026-11-15

**Status**: Draft

**Input**: User description: "B13F1 · 静态中断点（`interrupt_before` / `interrupt_after`）+ `recursion_limit` —— 交付两项运行期安全阀：① 在指定节点**之前** / **之后**人为挂起（静态中断点）；② 当图陷入循环时抛**明确的**递归超限异常而不是无限跑下去。本 feature 的判定是：**递归超限抛明确异常**。静态中断 MUST 与 B10F1 的动态中断共用同一套挂起 / 恢复机制（`InterruptResult` · 空载荷），`recursion_limit` 的载体 MUST 在本 feature 锁定为普通 dict 形态。"

---

## 承接条款（上游 feature → 本 feature）

> **宪法 v1.8.0「跨 feature 承接的接线通则」**：某个 feature 的规格中出现了**指名下一棒
> feature（ID + 里程碑）**的跨 feature 义务时，该条款 MUST 写入目标 feature 的提示词初稿
> ⇒ 由目标 feature 的 spec 落成 **FR + 裁定** ⇒ 其 tasks 与契约同步接线。
> **只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽任何门禁判据。**

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B10F1 → B13F1** | **M1** | **静态中断的挂起态载体 MUST 与动态中断同款**：`InterruptResult`（**4 字段** `state` / `interrupts` / `executed` / `steps`）· 静态中断的 `__interrupt__` 载荷 = **空元组** `()`（静态断点没有「要审批什么」）· **MUST NOT** 新增结果类型 / 第 5 个字段 / 另一条挂起路径 | `specs/b10f1-interrupt-resume/spec.md` **FR-005** · **FR-020** · **裁定 2** · **SC-010** · **下游承接 D-4** | **FR-004** · **裁定 4** · SC-006 / SC-016 |
| **H-2** | **B10F1 → B13F1** | **M1** | **恢复机制同款且不可旁路**：静态中断的恢复 MUST 走与动态中断**同一条**图级入口；恢复 MUST 挂 checkpointer（**MUST NOT** 提供「不挂 checkpointer 也能恢复」的内存态旁路）；「该会话没有挂起中断」的失败信号 **MUST NOT** 误伤**合法的静态挂起** | `specs/b10f1-interrupt-resume/spec.md` **FR-013** · **裁定 4 / 10** · **SC-011 / SC-012** | **FR-007** · **裁定 9** · SC-011 / SC-012 |
| **H-3** | **B11F1 → B13F1** | **M1** | **B11F1 的 D-2（递归上限 × fan-out）**：fan-out 任务在**下一轮**执行 ⇒ `recursion_limit` MUST 把 **fan-out 轮**计入步数 ⇒ **MUST NOT** 让 fan-out 绕过上限 | `specs/b11f1-send-fanout/spec.md` **下游承接 D-2** · **FR-002** · **SC-007** | **FR-013** · **裁定 5** · SC-008 |
| **H-4** | **B11F1 → B13F1** | **M1** | **B11F1 的 D-7（静态断点 × fan-out）**：`interrupt_before` / `interrupt_after` 挂在目标节点上时，fan-out 的 **N 次调用各自独立命中**该断点 ⇒ **MUST NOT** 让 N 次调用**共享一条任务记录**；N 次命中按 B12F1 裁定 7 的**收集 / 合并**口径处理。⚠️ 静态断点的载荷为**空元组**（H-1）⇒ **MUST NOT** 为凑「N 条中断」而伪造 N 个载荷元素（见 **裁定 8** 的**引文差异 ①**） | `specs/b11f1-send-fanout/spec.md` **下游承接 D-7** · **FR-009 / FR-010 / FR-020** · **SC-011** | **FR-015** · **FR-016** · **裁定 8** · SC-009 / SC-010 |
| **H-5** | **B7F1 → B13F1** | **M1** | **轮次计数口径照写**：`recursion_limit` 计 **super-step 执行轮**（N 个任务同轮只算 1 轮）· 空终轮不计 · 既有 `run_super_step` / `run_super_steps` 的**签名与返回类型一字不动**；静态断点只在**图级入口**生效；低层手动入口收到**非空**静态字段 MUST **显式拒绝**（保持冻结签名） | `specs/b7f1-superstep-loop/spec.md` **FR-003 / FR-005 / FR-007 / FR-032** · `contracts/superstep-contract.md` **§1 / §3 / §5** | **FR-013** · **FR-017** · **裁定 5 / 13** · SC-007 / SC-015 |
| **H-6** | **B1F1 → B13F1** | **M1** | **复用契约层异常**：递归超限 MUST 抛 `GraphRecursionError`（**已定义** · 结构化字段 `recursion_limit` + `current_step`）⇒ **MUST NOT** 新造异常 / 新 L1 符号 / 改异常构造签名 | `src/freegraph/contracts/errors.py` **`GraphRecursionError`** · `specs/b1f1-contracts-core/spec.md` | **FR-014** · **裁定 6** · SC-003 / SC-016 |
| **H-7** | **B12F1 → B13F1** | **M1** | **优先级同款**：真异常 > 动态中断 > 静态中断；静态中断**不得**吞掉真异常、**不得**改写动态中断的合并载荷；静态 after 只在「本轮无错、无动态中断」时判定 | `specs/b12f1-concurrency-errors/spec.md` **裁定 7 / 8 / 11** · `contracts/concurrency-contract.md` **§3 / §4 / §6** | **FR-009** · **裁定 7** · SC-010 |
| **H-8** | **验收脚本 / README → B13F1** | **M1** | **载体形态锁定**：`harness/demo/graph_core.py` 的 `case_recursion_limit` 以 **dict 形态** `invoke(input, {"recursion_limit": 3})` 调用 ⇒ 本 feature MUST 锁定该载体并把 **软断言升级为硬断言**；`harness/demo/README.md` 的软断言清单 MUST 同步（移除 `recursion_limit` 一行） | `harness/demo/graph_core.py` **`case_recursion_limit`** · `harness/demo/README.md`「硬断言 vs 软断言」 | **FR-021 / FR-022 / FR-023 / FR-032** · **裁定 2 / 12** · SC-005 / SC-006 |

---

## 下游承接条款（本 feature → 下一棒）

> **宪法 v1.8.0**：本 feature 的规格中出现了**指名下一棒 feature（ID + 里程碑）**的跨 feature 义务时，
> 该条款 MUST 写入**目标 feature 的提示词初稿** ⇒ 由目标 feature 的 spec 落成 **FR + 裁定** ⇒ 其 tasks 与契约同步接线。
> **只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽任何门禁判据。**

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 | 接线状态 |
|---|---|---|---|---|---|
| **D-1** | **B13F1 → B7F2** | **M2** | **`compile()` 的静态断点关键字**：`compile(interrupt_before=..., interrupt_after=...)` MUST 被接受，并 MUST **原样填入** `GraphSpec.interrupt_before` / `interrupt_after`（同一套语义）；接受形态 MUST 与上游逐字一致：**裸 `"*"`（All）或 `list[str]`**，裸非 `"*"` 字符串 / 元组 / `["*"]` 失败，**`None` 归一为 `()`**；⚠️ `GraphSpec` 本身接受 `Sequence[str]`（含 tuple）⇒ **tuple 的拒绝只在 B7F2 的 compile 入口层**；**MUST NOT** 在构建 / 编译层另立第三套静态断点载体 | **FR-002** · **裁定 3** · SC-006 / SC-014 | ⏳ **待接线**：`harness/features/B7F2_compile编译.md` 的 `## 下游承接` 块内追加一条 |
| **D-2** | **B13F1 → B7F2** | **M2** | **构造期校验的可达性**：`compile()` 收到不存在的断点节点名 MUST 在**编译期**失败（`ValueError` · 消息点名该节点），不得推迟到 `invoke()`；`START` / `END` / 空串 / `["*"]` / 裸非 `"*"` 字符串 / 非 `str` 的失败信号与 `GraphSpec` 构造期**逐字同款**；`None` MUST 归一为 `()`；裸 `"*"` MUST 按上游解释为**全部可执行节点** | **FR-003** · **裁定 3** · SC-014 | ⏳ **待接线**：同 D-1（同一文件） |
| **D-3** | **B13F1 → B7F3** | **M2** | **`invoke(input, config)` 的 dict 载体透传**：`invoke` MUST 接受普通 dict 形态的 `config` 并把 `"recursion_limit"` **原样**交给 L2；MUST **NOT** 丢弃 / 改名 / 另写一条解析路径；MUST **NOT** 把 `GraphRecursionError` 包装成别的类型；`harness/demo/graph_core.py` 的硬断言 MUST 在此棒**真跑通过** | **FR-010 / FR-014 / FR-021 / FR-023** · **裁定 2 / 6 / 12** · SC-005 / SC-006 / SC-013 | ⏳ **待接线**：`harness/features/B7F3_invoke返回完整状态.md` 的 `## 下游承接` 块内追加一条 |
| **D-4** | **B13F1 → B7F3** | **M2** | **静态挂起的对外结果**：`invoke` 在静态挂起时 MUST 返回 `InterruptResult.as_result_dict()`（**含** `"__interrupt__": ()`）· **MUST NOT** 另写一条「静态中断 → 结果键」的转成路径；恢复时 MUST 接受 `input=None`（规范形态）与 `Command(resume=...)`（值**不投递**给任何节点） | **FR-004 / FR-007** · **裁定 4 / 9** · SC-006 / SC-011 / SC-012 | ⏳ **待接线**：同 D-3（同一文件） |
| **D-5** | **B13F1 → B14F1** | **M3** | **静态挂起的持久化**：`MemorySaver` MUST 能原样存取**静态挂起**的快照 + 调度账本（`interrupts = ()` · `suspension_kind` · `static_ack` · `next` 可为空）⇒ **MUST NOT** 要求「静态挂起也必须有一条动态中断载荷」才能恢复；**fan-out 载荷**（目标 + 原样入参 + TaskId）MUST 随调度账本一起保存 / 还原（**F-3**）；**F-10 的完成快照由 B13F1 写一次**，B14F1 的每轮末快照 MUST NOT 与之重复 / 冲突 | **FR-007 / FR-016** · **裁定 9 / 10** · SC-011 / SC-012 | ⏳ **待接线**：`harness/features/B14F1_Checkpointer协议与MemorySaver.md` 的 `## 下游承接` 块内追加一条 |
| **D-6** | **B13F1 → B15F1 / B16F1** | **M3** | **状态历史 / 时间旅行**：历史快照 MUST 能把「静态挂起」表示为 `interrupts == ()` 且 `suspension_kind` / `static_ack` 为静态值（`next` **允许为空**）；从历史静态快照恢复 MUST 不要求动态中断载荷；**MUST NOT** 继续假设「`next` 非空 ⇒ 必有中断」 | **FR-007** · **裁定 9** · SC-011 | ⏳ **待接线**：`harness/features/B15F1_SqliteSaver与状态历史.md` 与 `harness/features/B16F1_update_state与时间旅行.md` 的 `## 下游承接` 块内各追加一条 |
| **D-7** | **B13F1 → B6F1** | **M2** | **构建器不得拒绝 / 改名**：`StateGraph` 构建器 MUST 允许用户把 `interrupt_before` / `interrupt_after` 一路带到 `compile()`；**MUST NOT** 在 `add_node` / `add_edge` 层静默丢弃这两个配置 | **FR-002** · **裁定 3** · SC-006 | ⏳ **待接线**：`harness/features/B6F1_StateGraph构建器.md` 的 `## 下游承接` 块内追加一条 |
| **D-8** | **B13F1 → B24F1** | **M4** | **兼容矩阵**：`compile` 行的 `interrupt_before` / `interrupt_after` 关键字与 `recursion_limit` 的 dict 载体 MUST 被记录为**已交付**；**零新增行**（仅事实性措辞更新） | **FR-010 / FR-021** · SC-016 | ⏳ **待接线**：`harness/features/B24F1_打包分发与兼容矩阵.md` 的 `## 下游承接` 块内追加一条 |

---

## Clarifications

### Session 2026-11-15（设计裁定 · 提示词初稿已点名「spec 阶段必须写死」的项）

> **背景**：提示词初稿已把大部分语义写死（静态断点 before / after · 递归超限抛明确异常 ·
> 挂起载体与 B10F1 一致 · 载体形态待锁定），但仍有三处会外溢到用户代码的接口决策：
> ① `recursion_limit` 的**载体与优先级**；② 静态断点的**配置落位**；③ 静态挂起在
> **fan-out × 恢复 × 结果键**上的可观察口径。本节逐条拍板，**plan 阶段不得再翻**。

- **Q1（`recursion_limit` 的载体）**：放普通 dict、放 `RunConfig`，还是两者都支持？
  → **A：普通 dict 是规范载体**（`invoke(input, {"recursion_limit": 3})` · 与
  `harness/demo/graph_core.py` 逐字一致）· **`RunConfig.recursion_limit` 是等价备用载体**
  （已存在的 L1 字段 · B1F1 / 上游对齐 P3 已落地）。⚠️ **dict 与 `RunConfig` 是互斥的替代载体**
  （一次运行只接受**一个** `config` 对象）⇒ **不存在「同时提供两者」的路径**；若上层只持有
  `RunConfig`，以其 `recursion_limit` 字段为准。⚠️ **L2 MUST NOT 新增显式 `recursion_limit=`
  关键字**（上游 1.2.11 也没有该关键字）⇒ 内部直控继续用既有的 `max_steps`。
  ⇒ 落点：**FR-010** · **裁定 2** · SC-006。
- **Q2（静态断点的配置落位）**：放 `RunConfig`、放构建器参数，还是放 L2 图规格？
  → **A：图定义侧 = `GraphSpec` 的两个 keyword-only 字段**（`interrupt_before` /
  `interrupt_after` · 缺省空）⇒ 这是 L2 手写图规格的「定义方」位置；`RunConfig` 是
  单次运行的配置，**MUST NOT** 成为静态断点的载体（否则同一张图换一次运行就换一套结构）。
  `compile(interrupt_before=...)` 的对外形态由 **B7F2** 填进这两个字段（**D-1 / D-2**）。
  ⇒ 落点：**FR-002** · **裁定 3** · SC-006 / SC-014。
- **Q3（静态挂起的结果键）**：上游静态断点在 `invoke()` 结果里**没有** `__interrupt__` 键
  （实测：`GraphInterrupt()` 空载荷 ⇒ 结果字典只有状态键）。freegraph 要不要补这个键？
  → **A：补 `"__interrupt__": ()`**（**空元组**）—— 理由：提示词 P1 要求「明确的挂起信号」，
  且与动态中断共用**同一个**结果载体（H-1）；上游「静默返回半截状态」无法区分「正常停」与
  「被静态断点拦住」。这是**刻意的结构差异**（**X-1**），不是更严的失败信号。
  ⇒ 落点：**FR-004** · **裁定 4** · SC-006。
- **Q4（`interrupt_before` 的粒度）**：只拦住目标节点、同轮其它节点照跑，还是**整轮**不跑？
  → **A：整轮不跑**（上游 `_loop.py:667-670` 在**执行前**抛 `GraphInterrupt` ⇒ 本轮所有任务
  都不执行）⇒ 与上游同款；目标节点**未执行**、本轮写入**一条都不合并**、触发源版本
  **一个都不消费** ⇒ 恢复时同一批任务原样重试。
  ⇒ 落点：**FR-005** · **裁定 7** · SC-001 / SC-007。
- **Q5（`interrupt_after` 的粒度）**：本轮写入何时合并？目标节点执行几次？
  → **A：本轮先完整执行并合并写入，再挂起**（上游 `_loop.py:720-723` 在 `after_tick`
  写合并之后抛）⇒ 目标节点**恰好执行一次**（fan-out 则 N 次各一次）· 挂起态 `state` **含**
  本轮写入 · `steps` **计入**本轮 · 恢复后**不重跑**刚刚执行过的节点。
  ⇒ 落点：**FR-006** · **裁定 7** · SC-002。
- **Q6（静态挂起如何恢复）**：`input=None`、`Command(resume=...)`、还是别的专用入口？
  → **A：`input=None` 是规范形态；`Command(resume=...)` 也接受**（与动态中断共用对外形态），
  但静态挂起**没有**要投递的节点级中断 ⇒ `resume` 的**值不被投递给任何节点**（上游实测：
  静态挂起后 `Command(resume="X")` 与 `input=None` 行为一致，值被忽略）。恢复 MUST 挂
  checkpointer（H-2）；「没有挂起中断」的失败信号 MUST NOT 误伤静态挂起（**裁定 9**）。
  ⇒ 落点：**FR-007** · SC-011 / SC-012。
- **Q7（递归上限的计数单位）**：按节点调用次数，还是按 super-step 轮次？
  → **A：按 super-step 执行轮**（N 个任务同轮 = 1 轮）；fan-out 在**下一轮**执行 ⇒
  fan-out 轮**照常计数**（H-3）⇒ **MUST NOT** 以「节点调用次数」计数。
  ⇒ 落点：**FR-013** · **裁定 5** · SC-007 / SC-008。
- **Q8（静态断点 × fan-out 的「N 次中断」）**：B11F1 的 D-7 要求 N 次调用**各自独立命中**、
  **不得共享一条中断记录**；但静态断点的载荷按 H-1 是**空元组**。二者如何同时成立？
  → **A：以「任务粒度」独立，以「挂起载荷」为空** ——
  **before**：N 个 fan-out 任务**各自保留为独立任务**（各自的 TaskId / 原样入参 / 各自
  待执行），**一个都不执行**；**after**：N 个任务**各执行一次**；两种情况下**挂起事件只有
  一个**、`__interrupt__` **仍为空元组**。D-7 的「N 次中断」落实为「N 个**任务级**命中」，
  **不是** N 个载荷元素；**MUST NOT** 为了凑数伪造 N 个 `Interrupt`。
  ⇒ 落点：**FR-015 / FR-016** · **裁定 8** · **引文差异 ①** · SC-009 / SC-010。
- **Q9（A3 / `graph_core.py` 的软断言升级时机）**：`invoke()` 属 B7F3（M2），M1 的 B13F1
  如何满足「软断言升级为硬断言并**通过**」？
  → **A：分两段落地** —— ① **本 feature 立即**把 `soft(...)` 升级为 `check(...)` 并把异常
  判定收紧到 `GraphRecursionError`（**不再**用「任意异常即通过」的宽口径）；② **本 feature
  立即**提供**同调用形态**的 L2 硬测试（`run_graph(..., config={"recursion_limit": 3})` ⇒
  `GraphRecursionError`），**当下真跑通过**；③ `graph_core.py` 的**端到端真跑**依赖
  `compile()` / `invoke()`（**B7F2 / B7F3 · M2**）⇒ 作为**具名承接 D-3** 在 B7F3 收口，
  B13F1 **MUST NOT** 写下永久红的 CI，也 **MUST NOT** 伪造端到端输出。
  ⇒ 落点：**FR-021 / FR-022 / FR-023** · **裁定 12** · SC-005 · **环境偏离 EV-1**。
- **Q10（用户澄清确认 · 引用 Q9）**：A3 / M1–M2 边界。
  → **A：同 Q9**（保持 L2-only；软断言立即升级 + L2 等价硬测试；端到端真跑具名延期 **B7F3**
  · **MUST NOT** 提前实现 `compile()` / `invoke()`）。
  ⇒ 落点：**裁定 12** · **FR-023** · **环境偏离 EV-1** · SC-005。
- **Q11（用户澄清确认 · 引用 Q1）**：`recursion_limit` 是否还需要显式关键字？
  → **A：同 Q1**（照抄上游：**不需要**显式 `recursion_limit=` 关键字；**dict / `RunConfig`**
  为互斥载体，**`max_steps`** 仅作 L2 内部直控；优先级 **dict / RunConfig > max_steps > 10007**）。
  ⇒ 落点：**FR-010** · **裁定 2** · SC-006。
- **Q12（用户澄清 · 低层入口）**：`run_super_step` / `run_super_steps` 收到带静态断点字段的
  `GraphSpec` 时应该怎么做？
  → **A：显式拒绝** —— 签名与返回类型**保持不变**；抛明确异常并说明「静态断点只在图级
  `run_graph` 生效」⇒ 避免用户误以为断点已生效；**MUST NOT** 静默忽略，也 **MUST NOT**
  为低层入口改返回类型。
  ⇒ 落点：**FR-017** · **裁定 13** · **X-6** · **F-8** · SC-015。
- **Q13（用户澄清 · 静态断点写法）**：`interrupt_before` / `interrupt_after` 是否接受裸字符串？
  → **A（按上游修正）：裸 `"*"` = 全部**可执行**节点；非 `"*"` 的裸字符串一律拒绝；`["*"]` 也拒绝。**
  ⚠️ **两层口径必须分开**：
  ① **`GraphSpec` 字段**（L2 图规格）接受 `str | Sequence[str]` ⇒ **tuple 也合法**；
  失败类型：**裸** `""` / 裸哨兵 / 裸普通节点名 ⇒ `TypeError`（V-22）；**序列元素**
  `""` ⇒ `ValueError`（V-23），序列中的哨兵 / `"*"` ⇒ `ValueError`（V-24），未知节点
  ⇒ `ValueError`（V-25）；`Mapping` / `set` / 非 `Sequence` ⇒ `TypeError`；
  ② **`compile()` 关键字**（B7F2）的接受形态与上游**逐字一致**：裸 `"*"` 或 `list[str]`；
  tuple / 裸非 `"*"` 字符串 / `["*"]` ⇒ 失败；`None`（compile 的缺省）归一为 `()`。
  上游实测：`compile(interrupt_before="*")` 接受（All）· `compile(interrupt_before=["*"])`
  抛 `ValueError` · `compile(interrupt_before="review")` 与
  `compile(interrupt_before=("review",))` 抛 `TypeError` ·
  `compile(interrupt_before=["review"])` 接受。`GraphSpec` 在构造期把 `"*"` **展开为当前
  节点表的全部可执行节点**（**排除 `__start__` / `__end__` 哨兵**），后续匹配不再有通配符。
  ⇒ 落点：**FR-002 / FR-003** · **裁定 3** · **P-17** · **E-11** · SC-014。
- **Q14（用户澄清 · 静态挂起标记）**：静态挂起在检查点里如何标记，才能在 `next` 为空时仍能恢复？
  → **A：增加显式 `suspension_kind`**（`static_before` / `static_after`）—— 静态挂起的判定
  MUST 是「`interrupts == ()` **且** `suspension_kind` 为静态值」；并用 **`static_ack`**
  记录挂起时的通道版本水位（防重复触发）；`next` **允许为空**（最后一个节点 after 挂起 /
  before 时只有 fan-out 任务）。**MUST NOT** 用「`next` 非空」单独作为静态挂起的判据；
  **MUST NOT** 把空 `next` 的静态挂起误判为 `no_pending_interrupt`。
  上游没有 freegraph 的 `no_pending_interrupt` 失败信号，因此该标记是**必须自研的接缝**。
  ⇒ 落点：**FR-007** · **裁定 14** · **F-9** · **X-8** · **P-19** · SC-011 / SC-012。

#### 裁定编号映射（本 spec 的**唯一**裁定编号表）

| 裁定 | 内容 | 来源 |
|---|---|---|
| **裁定 1** | 交付静态断点 before / after，且与动态中断**共用**挂起载体与恢复机制 | 提示词 §1 / §2 · H-1 / H-2 |
| **裁定 2** | `recursion_limit` 的规范载体 = 普通 dict；`RunConfig` 是**互斥替代载体**（一次运行一个）；**dict / RunConfig > `max_steps` > 默认 10007**；**不新增显式关键字** | **Q1** · **Q11** |
| **裁定 3** | 静态断点配置落在 `GraphSpec` 的两个 keyword-only 字段；裸 `"*"` = 全部**可执行**节点（排除 `__start__` / `__end__`），`["*"]` 与裸非 `"*"` 字符串非法；`compile()` 由 B7F2 填入 | **Q2** · **Q13** |
| **裁定 4** | 静态挂起复用 `InterruptResult`；`interrupts == ()`；结果键为 `"__interrupt__": ()` | **Q3** |
| **裁定 5** | `recursion_limit` 按 **super-step 执行轮**计数；fan-out 轮计入 | **Q7** · H-3 / H-5 |
| **裁定 6** | 递归超限复用 L1 的 `GraphRecursionError`，不新造异常 | **H-6** |
| **裁定 7** | before = 整轮不执行；after = 写合并后挂起；优先级 = 递归 > before · 真异常 > 动态中断 > after > 完成 | **Q4 / Q5** · **H-7** |
| **裁定 8** | fan-out × 静态断点：N 个任务独立命中；挂起载荷仍为空元组；不伪造 N 条载荷 | **Q8** · H-4 |
| **裁定 9** | 静态恢复走同一入口；`input=None` 规范、`Command(resume=...)` 接受但值不投递；必须挂 checkpointer；不误判 `no_pending_interrupt` | **Q6** · H-2 |
| **裁定 10** | 静态挂起必须原样保留 fan-out 现场（目标 / 入参 / TaskId / 抑制标志）⇒ 调度账本增补 `fanout` 键 | H-4 · **F-3** |
| **裁定 11** | 防重复触发：自上次静态挂起以来无通道版本推进 ⇒ 同一断点不再触发；水位由 **`static_ack`** 记录 | **FR-008** · P-10 |
| **裁定 12** | `graph_core` 软断言立即升级 + L2 等价硬测试当下通过；端到端真跑具名延期到 B7F3 | **Q9** |
| **裁定 13** | 静态断点只在图级入口 `run_graph` 生效；`run_super_step` / `run_super_steps` 收到非空静态字段时**显式拒绝**（签名 / 返回类型不变） | **H-5** · **Q12** · **X-6** |
| **裁定 14** | 静态挂起用显式 `suspension_kind`（`static_before` / `static_after`）标记，并用 `static_ack` 记录通道版本水位；`next` 允许为空；不得用 `next` 非空单独判定静态挂起 | **Q14** · **F-9** · **X-8** |

#### 引文差异（提示词 / 承接文档 vs 本 spec）

| # | 差异 | 处置 |
|---|---|---|
| **引文差异 ①** | B11F1 的 **D-7** 逐字要求「fan-out 的 N 次调用各自独立命中该断点 ⇒ **N 次中断**按 B12F1 裁定 7 的收集 / 合并口径处理」；而提示词 §2 / H-1 又要求静态断点的 `__interrupt__` 载荷为**空元组** ⇒ 「N 次中断」与「空载荷」字面冲突 | **裁定 8 / Q8**：**任务粒度独立、挂起载荷为空** —— before 时 N 个任务各自保留且都不执行，after 时 N 个各执行一次；`__interrupt__` 仍为 `()`；D-7 的「N 次中断」落实为「N 个任务级命中」，**不是** N 个载荷元素。**MUST NOT** 伪造 N 个 `Interrupt` |
| **引文差异 ②** | 提示词 **SC-005 / A3** 要求 `graph_core.py` 的软断言「升级为硬断言并**通过**」；但 `graph_core` 的 `compile()` / `invoke()` 属 **B7F2 / B7F3（M2）** ⇒ M1 物理上无法端到端真跑 | **裁定 12 / Q9 / 环境偏离 EV-1**：软断言升级 + 异常类型收紧**立即**落地；L2 等价硬测试**当下通过**；端到端真跑作为**具名承接 D-3** 在 B7F3 收口；MUST NOT 写永久红 CI / 伪造输出 |
| **引文差异 ③** | 提示词（**修复前**）表格写「M1 运行时内核（第 13 个）」「M1 全部 **9** 个 feature」；而立项书 §5.2 / §6.2 的 M1 实际为 **10** 个 feature（含 B7F4 / B13F1） | 以**立项书 §5.2 / §6.2** 为准（宪法「权威顺序」）⇒ 本 spec 的 Assumptions 写 **10 feature / 30 人日**；提示词已同步修正为 **§5.2 行序第 14 个 / 10 feature / 30 人日**；该数字只影响排期说明，不影响判据 |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 在指定节点前挂起（Priority: P1）

作为用户，我能把图配成「跑到 `review` 节点之前先停一下」，从而检查到达该节点时的状态；
`review` 本身**一次都没有执行**。

**Why this priority**: 这是静态中断点的**存在理由**（提示词 P1）——调试与人工介入
必须在目标动作**发生之前**看到干净状态。

**Independent Test**: 一张 `START → review → END` 的图，配置 `interrupt_before=("review",)`
⇒ 断言执行结果为挂起态、`review` 的副作用计数 == **0**、状态里**没有** `review` 的写入。

**Acceptance Scenarios**:

1. **Given** 图配置了 `interrupt_before=("review",)`，**When** 从入口运行，**Then** 返回挂起态，
   且 `review` 未执行、其写入未合并。
2. **Given** 同一张图在 `review` 之前还有节点 `prepare`，**When** 运行，**Then** `prepare`
   执行完成、`review` 未执行，挂起态 `state` 只含 `prepare` 的写入。
3. **Given** 已挂起在 `review` 之前，**When** 不带新输入继续运行，**Then** `review` 执行一次，
   且**不会**在同一断点上再次挂起。

---

### User Story 2 - 在指定节点后挂起（Priority: P1）

作为用户，我也能在 `review` 执行完之后挂起，从而检查它的产出；`review` 的副作用计数
恰好是 **1**。

**Why this priority**: 这是提示词 P2 的独立验收；「执行前」与「执行后」是两种不同的
调试视角，必须都可判定。

**Independent Test**: 同一张图配置 `interrupt_after=("review",)` ⇒ 断言 `review` 副作用计数
== **1**、挂起态 `state` 含 `review` 的写入、恢复后**不重跑** `review`。

**Acceptance Scenarios**:

1. **Given** 图配置了 `interrupt_after=("review",)`，**When** 运行，**Then** `review` 已执行一次，
   返回挂起态。
2. **Given** `review` 是路径上的最后一个节点，**When** 它执行完，**Then** 仍然返回挂起态
   （不直接判为完成）；恢复后才完成。
3. **Given** 已挂起在 `review` 之后，**When** 继续运行，**Then** `review` 不再执行，后续节点照常。

---

### User Story 3 - 死循环被明确拦住（Priority: P1）

作为用户，我的图有个自环 bug；我希望它在有限步内**抛出明确异常**，而不是把机器跑挂。

**Why this priority**: 这是本 feature 的**立项判据 A1**（小目标原文「递归超限抛明确异常」）。

**Independent Test**: 自环图 + `recursion_limit=3` ⇒ `invoke` / L2 入口抛出
`GraphRecursionError`，结构化属性 `recursion_limit == 3`，消息含超限语义。

**Acceptance Scenarios**:

1. **Given** 一个 `loop → loop` 的自环图，**When** 以 `{"recursion_limit": 3}` 运行，**Then**
   抛出 `GraphRecursionError`（不是 `RecursionError` / 不是挂起 / 不是静默停止）。
2. **Given** 同一张图，**When** 不提供 `recursion_limit`，**Then** 使用**文档化默认值
   10007**（可由测试断言；不会在 25 步就误报）。
3. **Given** `recursion_limit` 为 `0` / 负数 / 非整数，**When** 运行，**Then** 在入口**立即**
   显式失败（`ValueError` / `TypeError`），而不是跑到一半才失败。

---

### User Story 4 - 载体形态锁定为普通 dict（Priority: P2）

作为用户，我能用最普通的写法把运行期参数传进去：
`invoke(input, {"recursion_limit": 3})`；我不需要为了一个上限去构造特殊配置对象。

**Why this priority**: 提示词 FR-006 / A3 逐字要求锁定载体；`harness/demo/graph_core.py`
已经用 dict 形态调用，锁定后该项才能从软断言升级为硬断言。

**Independent Test**: 用 dict 形态与 `RunConfig` 形态各跑一次自环图 ⇒ 两者都抛
`GraphRecursionError`；二者是**互斥替代载体**（不同时提供）；dict 与 `max_steps` 同时
出现时 **dict 优先**。

**Acceptance Scenarios**:

1. **Given** `invoke(input, {"recursion_limit": 3})`，**When** 图自环，**Then** 抛出
   `GraphRecursionError`。
2. **Given** `RunConfig(recursion_limit=3)`，**When** 图自环，**Then** 同上。
3. **Given** dict 里的 `recursion_limit=5`（或 `RunConfig(recursion_limit=5)`）与
   `max_steps=2` 同时提供，**When** 运行，**Then** 以 **5** 为准（dict / `RunConfig`
   均优先于 `max_steps`）。
4. **Given** dict 里带有其它运行期键（如 `max_concurrency`），**When** 只关心
   `recursion_limit`，**Then** 其它键**不导致失败**（仅读取已知键）。

---

### User Story 5 - 默认上限有明确取值（Priority: P2）

作为用户，我不设置 `recursion_limit` 时也有一个**写进文档**的安全上限，而不是「无限」或
「凭实现心情」。

**Why this priority**: 提示词 SC-004 要求默认值可由测试断言；上游的有效缺省是 10007，
但上游可由环境变量覆盖——freegraph 必须**硬编码且零环境变量**。

**Independent Test**: 读取/断言默认上限 == **10007**；同一测试证明环境变量
`LANGGRAPH_DEFAULT_RECURSION_LIMIT` 不会改变 freegraph 的行为。

**Acceptance Scenarios**:

1. **Given** 不提供任何上限，**When** 查询有效上限（或跑一轮超过 25 步仍不误报），**Then**
   实际上限 == 10007。
2. **Given** 进程环境里设置了 `LANGGRAPH_DEFAULT_RECURSION_LIMIT=1`，**When** 运行，**Then**
   行为与未设置时**逐字相同**（零环境变量红线）。

---

### User Story 6 - 静态断点与 fan-out 的交互可判定（Priority: P2）

作为用户，我的 `fan` 节点派出 N 个 fan-out 任务到同一个 `worker`；如果我在 `worker` 上挂了
静态断点，我希望 **N 个任务各自独立**命中，而不是被合并成一个任务。

**Why this priority**: 承接 B11F1 的 **D-2 / D-7**；fan-out 与静态断点的交互是 M1 收口的
最后一个组合面。

**Independent Test**: `fan` 返回两个 `Send("worker", ...)`，`interrupt_before=("worker",)`
⇒ `worker` 调用计数 == **0**，两个任务都保留为待执行；`interrupt_after=("worker",)`
⇒ `worker` 调用计数 == **2**（各一次），随后挂起。

**Acceptance Scenarios**:

1. **Given** 两个 fan-out 任务指向 `worker` 且 `interrupt_before=("worker",)`，**When** 运行，
   **Then** `worker` 执行 **0** 次，挂起态保留两个独立待执行任务（各自的入参不丢失）。
2. **Given** 同上但 `interrupt_after=("worker",)`，**When** 运行，**Then** `worker` 执行 **2** 次，
   随后挂起；挂起态含两次写入。
3. **Given** 挂起在 fan-out 的 `worker` 之前，**When** 恢复，**Then** 恰好执行原来那两个任务
   （不是 1 个、不是 3 个），且各自入参**逐字不变**。

---

### User Story 7 - 动态与静态中断可共存且优先级确定（Priority: P2）

作为用户，我可能在同一次运行里既有节点内 `interrupt()`、又有静态断点；我希望失败与挂起的
先后顺序是**确定的**，而不是取决于线程调度。

**Why this priority**: 承接 B10F1 / B12F1；两种中断共用载体但不能混淆语义。

**Independent Test**: 一个节点内先抛真异常时，静态 after **不**生效（真异常优先）；
节点内 `interrupt()` 与静态 after 同时命中时，动态中断优先；同一节点同时配 before 与
after 时，before 先挂起，恢复后 after 在**下一次**执行后挂起。

**Acceptance Scenarios**:

1. **Given** 节点抛真异常且该节点也在 `interrupt_after` 里，**When** 运行，**Then** 抛出原异常
   （不返回挂起态）。
2. **Given** 节点内 `interrupt()` 且该节点也在 `interrupt_after` 里，**When** 运行，**Then**
   按动态中断挂起（载荷 = 节点的中断元组，**不是**空元组）。
3. **Given** 同一节点同时在 `interrupt_before` 与 `interrupt_after` 里，**When** 首次运行，
   **Then** before 先挂起；恢复后该节点执行，after 再挂起。

---

### User Story 8 - 未配置静态断点时行为完全不变（Priority: P3）

作为既有用户，我不配置 `interrupt_before` / `interrupt_after` 时，升级后的运行行为必须与
之前**逐字一致**。

**Why this priority**: 本 feature 是 M1 的收口；任何既有 M1 feature 的回归都不可接受。

**Independent Test**: 既有 B7F1 / B9F1 / B10F1 / B11F1 / B12F1 的测试**一条不改**全部通过；
`GraphSpec` 的既有构造写法**零改动**；`run_super_step` / `run_super_steps` 的返回类型与
签名不变。

**Acceptance Scenarios**:

1. **Given** 一个既有 `GraphSpec(...)` 调用（不写新字段），**When** 构造与运行，**Then**
   行为与 B13F1 之前**逐字相同**。
2. **Given** 低层入口 `run_super_step` / `run_super_steps`，**When** 传入带**非空**静态断点
   字段的 `GraphSpec`，**Then** 它们**显式拒绝**（消息说明「静态断点只在 `run_graph` 生效」），
   签名与返回类型保持不变。

---

### Edge Cases

- **空配置**：`interrupt_before=()` / `interrupt_after=()` ⇒ 永不挂起，行为与未配置一致。
- **同一节点同时出现在 before 与 after**：before 先命中；恢复并执行后 after 再命中。
- **目标节点是入口节点**：before 在首轮就挂起；`state` 只含输入写入。
- **目标节点是最后一个节点**：after 在执行完后挂起；此时 `next` 可能为空 ⇒ 仍 MUST 用
  `suspension_kind` 识别为静态挂起，恢复后直接完成，不重跑。
- **before 时本轮只有 fan-out 任务**：`next` 可能为空 ⇒ 仍 MUST 用 `suspension_kind`
  识别为静态挂起，并保留 fan-out 现场供恢复。
- **目标节点从未被触发**：不挂起（不会因为「配置了」就凭空挂起）。
- **配置了不存在的节点名**：构造期 `ValueError`，消息点名该节点（与上游编译期
  `Interrupt node ... not found` 同语义）。
- **配置了 `START` / `END` / 空串 / `["*"]` / 裸非 `"*"` 字符串 / 非字符串**：显式失败，不得静默忽略；**裸 `"*"`** 是合法的「全部**可执行**节点」写法（上游同款）。⚠️ **裸值**空串 / 裸哨兵 ⇒ `TypeError`（V-22）；**序列元素**空串 ⇒ `ValueError`（V-23），序列中的哨兵 / `"*"` ⇒ `ValueError`（V-24）。
- **重复节点名**：去重（成员语义），不产生第二次挂起。
- **before 轮里既有标准任务又有 fan-out 任务**：**整轮**不执行；两类任务都保留。
- **fan-out 的 N 个任务命中 after**：N 个各执行一次；`executed` 里目标名出现 N 次。
- **动态中断与静态 after 同轮**：动态中断优先；静态 after 不记录。
- **真异常与静态 after 同轮**：真异常优先；不返回挂起态。
- **递归上限与静态 before 同轮**：先判递归上限（`GraphRecursionError` 优先）。
- **递归上限正好等于已执行轮数且仍有待执行任务**：抛 `GraphRecursionError`，不执行下一轮。
- **递归上限为 0 / 负数 / 非 int / bool**：入口显式失败（`ValueError` / `TypeError`）；
  **`None` 除外**：视为未提供并落回下一层（见上一行）。
- **dict 里同时有 `recursion_limit` 与其它运行期键**：只读已知键，其它键不导致失败。
- **同时有 dict 与 `RunConfig` 值**：**不存在该路径**（二者互斥；一次运行一个 `config`）；
  **dict 与 `max_steps` 同时给**：dict 优先。
- **`recursion_limit=None`**：视为未提供，落回下一个载体 / 默认值。
- **静态挂起后不挂 checkpointer 就 `Command(resume=...)`**：`checkpointer_required`
  （B10F1 既有失败信号，不静默降级）。
- **静态挂起后 `input=None` 且未挂 checkpointer**：按 B10F1 既有语义视为**新的一次运行**
  （不是恢复），不得声称已恢复。
- **静态挂起后立即用 `input=None` 恢复、没有任何新输入**：同一断点**不得**再次触发
  （否则死循环）。
- **静态挂起后用空 StateDict `input={}` 恢复**：没有任何通道写入 ⇒ 按 FR-008 的
  「自上次静态挂起以来没有任何通道版本推进」口径 ⇒ 同一断点**不得**立即再次触发
  （与 `input=None` 同款；恢复路径 MUST 同样传 `static_ack`）。
- **目标节点执行后没有任何通道写入**：静态断点按上游「自上次中断以来必须有过更新」的
  口径**不**重复触发（避免恢复即再挂起）。
- **恢复后再次走到同一目标且产生了新写入**：断点**可以**再次触发。
- **fan-out 的 `Send.arg` 不是 JSON 可序列化对象**：属 B14F1 持久化口径；本 feature 的
  内存态挂起 MUST 原样保留该对象，MUST NOT 改写 / 丢弃。
- **`run_super_steps` 传入带静态断点的 `GraphSpec`**：**显式拒绝**（`ValueError` · 消息说明
  「静态断点只在图级 `run_graph` 生效」），**MUST NOT** 静默忽略；文档 MUST 显著说明。

---

## Upstream Parity *(mandatory — 宪法 v1.9.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11**（取证于 2026-11-15 ·
`/home/ctyun/.local/lib/python3.12/site-packages/langgraph`）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | **递归上限的有效缺省 = 10007** | `langgraph/_internal/_config.py:32`（`DEFAULT_RECURSION_LIMIT = int(getenv("LANGGRAPH_DEFAULT_RECURSION_LIMIT", "10007"))`） | **硬编码 10007** · **不读环境变量** | SAME（数值）/ DIFF（不读 env） | 宪法原则 I 的零环境变量红线 ⇒ **X-4** |
| P-02 | **上限的载体 = 运行时 config 的 `recursion_limit` 键** | 上游 `RunnableConfig["recursion_limit"]`（`_internal/_config.py:184-186`） | **普通 dict** `{"recursion_limit": N}` 为规范载体 · `RunConfig.recursion_limit` 等价 | SAME | 与 `graph_core.py` 的调用形态逐字一致 |
| P-03 | **上限必须 ≥ 1** | `langgraph/pregel/main.py:2563-2564`（`ValueError("recursion_limit must be at least 1")`） | 入口立即 `ValueError` · 非 `int` / `bool` / 浮点 ⇒ `TypeError` | SAME（≥1）/ **STRICTER（类型更严）** | 早失败优于跑到一半失败 ⇒ **X-7** |
| P-04 | **上限按 super-step 轮次计** | `langgraph/pregel/main.py:3004-3011`（`out_of_steps`）· `pregel/_loop.py:608`（`step > stop`）· `_loop.py:1701`（`stop = step + recursion_limit + 1`） | 每个**执行轮**计 1；N 个任务同轮仍计 1；空终轮不计 | SAME | 与 B7F1 的 `SchedulerState.step` 口径对齐 |
| P-05 | **超限异常类型与结构化信息** | 上游 `GraphRecursionError` 类体为空（`langgraph/errors.py:87-99`）· 消息 `main.py:3005-3011` | L1 的 `GraphRecursionError(recursion_limit, current_step)`（结构化属性） | SAME（类型）/ DIFF（消息措辞 + 结构化） | B1F1 已冻结（**H-6**） |
| P-06 | **静态断点的配置在「图定义侧」** | `langgraph/graph/state.py:1177-1188`（`compile(..., interrupt_before=, interrupt_after=)`）· `pregel/main.py:768-769` / `:814-815`（`interrupt_*_nodes`） | `GraphSpec` 的 keyword-only `interrupt_before` / `interrupt_after`；`compile()` 由 **B7F2** 填入 | DIFF（载体） | freegraph 的图定义侧是 `GraphSpec` ⇒ **X-2** |
| P-07 | **静态断点节点名必须在图里** | 实测 1.2.11：`compile(interrupt_before=["nope"])` ⇒ `ValueError: Interrupt node \`nope\` not found`（`langgraph/graph/state.py:1177-1188` 的 compile 校验入口） | `GraphSpec` 构造期 `ValueError`，消息点名该节点 | SAME（失败信号）/ **STRICTER（时机更早）** | 构造期失败与 B7F1「构造时校验」一致 ⇒ **X-3** |
| P-08 | **`interrupt_before` = 执行前整轮挂起** | `langgraph/pregel/_loop.py:667-670`（`prepare_next_tasks` 之后、执行之前抛 `GraphInterrupt()`） | 递归检查之后、消费触发源 / 执行任务之前挂起；整轮不执行 | SAME | 上游实测：`before calls={'a':0,'b':0}` |
| P-09 | **`interrupt_after` = 写合并后挂起** | `langgraph/pregel/_loop.py:720-723`（`after_tick` 的 `apply_writes` 之后抛） | 本轮执行 + 写合并之后、下一轮之前挂起 | SAME | 上游实测：`after calls={'a':1,'b':0}` |
| P-10 | **静态断点只在「自上次中断以来有更新」时触发** | `langgraph/pregel/_algo.py:155-185`（`should_interrupt` 的 `any_updates_since_prev_interrupt`） | 同一断点在恢复后、无新通道写入时**不**重复触发 | SAME | 防止「恢复即再挂起」死循环 |
| P-11 | **静态中断的异常载荷为空** | `_loop.py:670` / `:723` 抛 `GraphInterrupt()`（无参数） | 内部同样以**空载荷**表示静态挂起 | SAME | 静态断点没有「要审批什么」 |
| P-12 | **静态挂起在 `invoke()` 结果里的键** | `langgraph/pregel/_loop.py:667-670` / `:720-723`（静态断点抛**空载荷** `GraphInterrupt()`）· `langgraph/pregel/main.py:3938-3954`（结果键只在有中断集合时装配）· **实测 E-03 / E-04**：静态挂起结果**没有** `__interrupt__` 键（只有状态键） | **返回** `"__interrupt__": ()`（空元组） | DIFF（结构性） | 提示词 P1 要求「明确挂起信号」+ H-1 的载体一致 ⇒ **X-1** |
| P-13 | **静态挂起后的恢复入口** | `langgraph/pregel/_loop.py:861-864`（`is_resuming` 的 `self.input is None` 判定）· `:1030`（`CONFIG_KEY_RESUMING` 缺失才报空输入）· **实测 E-05**：`invoke(None, config)` 继续执行 `snapshot.next` | `run_graph(spec, None, checkpointer=..., config=...)` 同款 | SAME | 与 B10F1 会话连续路径同族 |
| P-14 | **静态挂起后 `Command(resume=...)` 的值被忽略** | `langgraph/pregel/_loop.py:904-925`（恢复值只按**挂起中断**投递）· `:667-670` / `:720-723`（静态断点**不产生**节点级中断载荷）· **实测 E-06**：静态挂起后 `Command(resume="X")` 与 `None` 行为一致 | 接受 `Command(resume=...)`，值**不投递**给任何节点 | SAME | 没有节点级中断可接收该值 |
| P-15 | **fan-out N 个任务命中静态断点** | `langgraph/pregel/_algo.py:962-986`（`SEND` 任务在 superstep n+1 执行 · 每个 PUSH 任务有独立 task id）· `:253-256`（任务按路径排序）· `langgraph/pregel/_loop.py:667-670` / `:720-723`（静态断点）· **实测 E-07 / E-08**：`Command(goto=[Send,Send])` + `interrupt_before=["w"]` ⇒ 3 个待执行任务（1 个静态边 + 2 个 Send）、`w` 执行 0 次；`interrupt_after` ⇒ 3 个各执行 1 次、单个挂起、`interrupts=()` | 同款：N 个任务独立保留 / 独立执行；挂起事件 1 个、载荷空 | SAME（任务粒度）/ DIFF（载荷记录 ⇒ **X-1**） | 与 H-4 的 **B11F1 的 D-7** 对齐 ⇒ **裁定 8** |
| P-16 | **同一节点同时配 before 与 after** | `langgraph/pregel/_loop.py:667-670`（before）· `:720-723`（after）· **实测 E-09**：首次 before 挂起；恢复后执行，after 再挂起 | 同款 | SAME | 优先级确定 |
| P-17 | **裸 `"*"` = 全部可执行节点；`["*"]` 不是节点名** | `langgraph/graph/state.py:1177-1188`（`compile(..., interrupt_before=, interrupt_after=)`）· `:1257-1264`（`interrupt_before = interrupt_before or []` 与列表拼接）· **实测 E-11**：`compile(interrupt_before="*")` ⇒ 接受（`interrupt_before_nodes == "*"`）· `compile(interrupt_before=["*"])` ⇒ `ValueError`（`Interrupt node \`*\` not found`） | 裸 `"*"` = 全部**可执行**节点（构造期展开；排除 `__start__` / `__end__`）；`["*"]` ⇒ `ValueError` | SAME | 与上游编译期可观察行为一致 |
| P-18 | **递归上限判定先于静态 before** | `_loop.py:608-610`（`out_of_steps` 先判）后才 `prepare_next_tasks` / 静态 before | 递归检查先于静态 before 判定 | SAME | 优先级见 **裁定 7** |
| P-19 | **静态挂起且 `next` 为空时的标记** | `langgraph/pregel/_loop.py:720-723`（最后节点 after 抛静态断点）· `:904-927`（恢复路径只按挂起中断 / snapshot 处理，**无** `no_pending_interrupt` 信号）· **实测 E-13**：最后节点 after `snapshot.next == ()`，恢复 `input=None` 直接完成 | freegraph 增加 `suspension_kind`（`static_before` / `static_after`）+ `static_ack` ⇒ `next` 为空仍可恢复 | DIFF（结构性） | freegraph 的 `no_pending_interrupt` 需要显式区分 ⇒ **X-8** · **F-9** |
| P-20 | **低层手动入口** | **缺席断言**（检索范围 = `langgraph/pregel/` 与 `langgraph/graph/`）：上游**没有** `run_super_step` / `run_super_steps` 这类手动入口（它们属 freegraph 的内部循环） | freegraph 的低层入口收到**非空**静态字段 ⇒ 显式拒绝（`ValueError`） | DIFF（自研区 ③） | 上游无此入口 ⇒ **X-6** |

> ⚠️ **F-3 的 `fanout` 账本持久化**：上游没有 freegraph 的 `SchedulerState` 账本
> （上游的 fan-out 任务由自身 checkpoint 机制整体处理）⇒ 属**自研区 ③ / 内部契约变更**，
> **不**新增 P 行；该变更登记在 **F-3**（拆 B11F1 的「不落盘」冻结面）。

### 差分场景组 *(mandatory)*

> **落点**：`tests/differential/parity_probe.py` ⇒ **CI 的 Linux 全量档真跑**
> （上游缺席即 skip · 沿用 B5F2 的「缺席即 skip」纪律）。
> ⚠️ 编号从 **D-38** 起（B11F1 已用到 **D-37**）。

| # | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 |
|---|---|---|---|
| D-38 | 自环图 + `recursion_limit=3` | 两侧都抛 `GraphRecursionError`（类型可判定）；freegraph 的 `.recursion_limit == 3` | SAME |
| D-39 | 不设置上限、跑超过 25 轮但仍远小于 10007 | 两侧都不在第 25 轮误报（证明有效缺省 > 25） | SAME |
| D-40 | 每轮 2 个节点的自环 + `recursion_limit=3` | 两侧都只执行 **3 个 super-step**（不是 3 次节点调用）；随后抛超限异常 | SAME |
| D-41 | `interrupt_before=["a"]`（两侧统一用 list 形态；tuple 仅 `GraphSpec` 接受，见 P-17 / Q13） | 目标 `a` 执行 **0** 次；两侧都不合并本轮写入；freegraph 返回 `__interrupt__ == ()`，上游**无**该键 | DIFF（仅结果键） |
| D-42 | `interrupt_after=["a"]`（两侧统一用 list 形态；含 `a` 为最后节点、`next == ()` 的子场景） | 目标 `a` 执行 **1** 次；状态含 `a` 的写入；`next` 为空时两侧都仍可恢复（freegraph 靠 `suspension_kind`）；freegraph 返回 `__interrupt__ == ()`，上游**无**该键 | DIFF（仅结果键） |
| D-43 | 静态 before 挂起后用 `input=None` 恢复 | 两侧目标都恰好执行 **1** 次，结果一致 | SAME |
| D-44 | 静态 after 挂起后用 `Command(resume="X")` 恢复 | 两侧都继续执行、`X` 不投递给任何节点 | SAME |
| D-45 | `fan` 返回 `Command(goto=[Send("w",…), Send("w",…)])`（载体 A）· **无** `fan→w` 静态边 ⇒ N=2 · `interrupt_before=["w"]`（两侧统一用 list 形态） | 两侧 `w` 都执行 **0** 次。⚠️ 本场景**只判执行次数**，**不判**上游 `snapshot.next` / 任务保留（E-07 含标准边，纯 fan-out 的空 `next` 未实测）；任务保留与恢复由本地用例 **T076** 覆盖 | SAME |
| D-46 | 同 D-45 的图 + `interrupt_after=["w"]`（两侧统一用 list 形态） | 两侧 `w` 都执行 **2** 次（各一次），随后挂起 | SAME |
| D-47 | 同一节点同时配 before / after | 两侧顺序都是 **before → 恢复 → 执行 → after** | SAME |
| D-48 | `interrupt_before=["nope"]` / 裸 `"*"` / `["*"]` | `["nope"]` 两侧都失败并点名；裸 `"*"` 两侧都表示全部（可执行）节点；`["*"]` 两侧都失败。失败**时机**差异（freegraph 构造期 vs 上游 compile 期）见 **X-3**，差分探针只判可观察成败 | SAME |
| D-49 | 节点抛真异常且该节点配 `interrupt_after` | 两侧都抛**原异常**，不返回挂起态 | SAME |

⇒ **落点**：`tests/differential/parity_probe.py` ⇒ **CI 的 Linux 全量档真跑**
（上游缺席即 skip · **MUST NOT** 判失败）。

### 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **破已冻结的契约面 / 结构性差异（DIFF）** | P-12 / P-15：静态挂起在 `invoke()` 结果里**补** `"__interrupt__": ()`（上游**没有**该键） | 提示词 P1 要求「明确的挂起信号」；与动态中断共用 `InterruptResult` 载体（H-1）⇒ 上游的「静默半截状态」无法区分正常停与静态挂起 | **B7F3**（对外结果键）· 追认文字落 `harness/verification/B13F1/manual-verification.md` |
| **X-2** | **结构性差异（必须自研区 ③ · DIFF）** | P-06：静态断点由 `GraphSpec` 字段承载（上游是 `compile()` 关键字） | freegraph 的图定义侧在 L2 是 `GraphSpec`；`compile()` 属 M2（B7F2）⇒ 本 feature 必须在 L2 可独立验收（M1 收口） | **B7F2**（D-1 / D-2）· 追认文字同上 |
| **X-3** | **更严的失败信号（时机 · STRICTER）** | P-07：不存在的断点节点名在 **`GraphSpec` 构造期**失败（上游在 `compile()` 期） | B7F1 的既有纪律「构造时显式失败」（**B7F1 的**裁定 32）⇒ 更早暴露；失败类型与消息要点与上游一致 | 无需追认（判据零放宽） |
| **X-4** | **结构性差异（零环境变量红线 · DIFF）** | P-01：缺省值**硬编码** 10007（上游可由 `LANGGRAPH_DEFAULT_RECURSION_LIMIT` 覆盖） | 宪法原则 I：内核 MUST NOT 读任何环境变量；环境变量存在不得改变行为 | 无需追认（红线） |
| **X-5** | **结构性差异（异常消息 · DIFF）** | P-05：freegraph 的 `GraphRecursionError` 消息为英文摘要 + 结构化属性（上游类体为空） | B1F1 已冻结（`GraphRecursionError.recursion_limit` / `.current_step`）⇒ 上层无须解析消息 | 无需追认（继承 B1F1） |
| **X-6** | **结构性差异（必须自研区 ③ · DIFF）** | P-20：静态断点只在**图级入口** `run_graph` 生效；低层 `run_super_step` / `run_super_steps` 收到非空静态字段时**显式拒绝** | 上游**没有**这类低层入口 ⇒ 无同款行为可抄；低层入口的返回类型是冻结的 `SuperStepResult`（B7F1 冻结面）⇒ 不能返回 `InterruptResult`；「静默忽略」会误导用户 ⇒ 显式拒绝更可诊断 | **B7F1 契约**（F-8）· 追认文字同上 |
| **X-7** | **更严的失败信号（类型校验 · STRICTER）** | P-03：上游对 `recursion_limit` 的 `bool` / `float` **实际宽容**（实测 `True` ≈ 1、`1.5` 可用）；freegraph **拒绝** `bool` 与浮点，要求 `int` | 「把布尔 / 小数当上限」几乎必然是调用方 bug ⇒ 显式失败优于静默截断；与 B9F1 的「显式失败优于静默」同族 | 无需追认（判据零放宽）· **FR-012** |
| **X-8** | **结构性差异（检查点标记 · DIFF）** | P-19：freegraph 在静态挂起的检查点 metadata 里增加 `suspension_kind`（`static_before` / `static_after`）与 `static_ack`（版本水位）；上游没有这些标记（上游 `next` 直接指向任务，且没有 `no_pending_interrupt` 失败信号） | freegraph 的恢复路径必须区分「静态挂起且 `next` 为空」与「没有挂起中断」；不增加显式标记就只能把空 `next` 误判为完成 / 无中断 | **B14F1 / B15F1 / B16F1**（D-5 / D-6）· 追认文字同上 |

### 破冻结面的回溯修订清单 *(若有)*

> **拆分而不删**：下表每一行都只**增补**判据 / 字段 / 措辞，**不删除**既有断言；
> 若某条既有断言按原样会变红，MUST 在同一 PR 内**拆分**为「旧场景断言 + 新场景断言」。

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| **F-1 · `GraphSpec` 构造签名** | `src/freegraph/runtime/superstep.py` 的 `GraphSpec`；`specs/b7f1-superstep-loop/contracts/superstep-contract.md` **§1 / §2** | **只增**两个 keyword-only 字段（缺省 `()`）⇒ 既有 `GraphSpec(...)` 调用**零改动**；构造签名行**增补**新字段 | 追认落 `harness/verification/B13F1/manual-verification.md` |
| **F-2 · `GraphSpec` 校验表** | 同上契约 **§2.1.1**；`_validate_graph_spec` | **只增** V-22…V-25 **的调用点**：`_validate_graph_spec` MUST 调用 `normalize_static_points`（单一路径；归一与校验都在 `_static.py`，**MUST NOT** 在 `__post_init__` 重复第二套）⇒ **B7F1 契约**既有 V-1…V-9 与 **B7F4 的 V-16 形态族**一条不改；**B11F1 的 V-15…V-21**（其 **V-16** 为 `goto` 槽位规则）一段不动；本 feature 全局续编 **V-22…V-25**；**V-26 属入口期**（见 F-8） | 同上 |
| **F-3 · `SchedulerState` 检查点账本** | `SchedulerState.to_checkpoint` / `from_checkpoint`；`specs/b10f1-interrupt-resume/contracts/checkpoint-contract.md` **§3**；`specs/b10f1-interrupt-resume/spec.md` **裁定 9**；**⚠️ B11F1 的冻结面**：`specs/b11f1-send-fanout/contracts/send-contract.md` **§5.1**、`specs/b11f1-send-fanout/data-model.md` **I-12**、`specs/b11f1-send-fanout/tasks.md` **T019**、`specs/b11f1-send-fanout/plan.md` **PR-8**、`specs/b11f1-send-fanout/research.md` **DR-02 / D-08**、`specs/b11f1-send-fanout/quickstart.md` **DR-02**；`specs/b11f1-send-fanout/spec.md` **D-3**（「`fanout` 不落盘」的落盘口径）与 **F-14**（顺序口径，**不**是落盘口径；仅作「不受影响」说明） | **只增** `fanout` 键（缺省 `{}`）⇒ 旧快照缺该键时还原为**空**（宽容解码）；既有键逐字不变；**挂起时**的 `suspension_kind` / `static_ack` 镜像键见 **F-9**。<br>⚠️ **破 B11F1 冻结面（拆分而不删）**：B11F1 交付时 `to_checkpoint` **不含** `fanout`（DR-02 · I-12 · T019 · PR-8）；**自 B13F1 起**改为**含** `fanout`（静态挂起必须跨挂起保留 fan-out 现场 · SC-009 / T076）⇒ B11F1 的「不含」历史断言保留并标注「**B13F1 F-3 起被拆分**」；持久化**存储**仍归 B14F1（D-5），本 feature 只负责**账本编码**（`fanout` 键） | 同上 · **B11F1 追认**落 `manual-verification.md` |
| **F-4 · `run_graph` 签名** | `run_graph`；`specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md` **§2**；`specs/b10f1-interrupt-resume/spec.md` **裁定 10** | `config` 注解**放宽**为 `RunConfig \| Mapping[str, Any] \| None`；**MUST NOT** 新增 `recursion_limit=` 关键字（内部直控仍用 `max_steps`）⇒ 既有位置 / 关键字调用零改动 | 同上 |
| **F-5 · 恢复路径的「无挂起中断」判定** | `_resume_graph` / `_first_graph`；`specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md` **§6.2**；`specs/b10f1-interrupt-resume/spec.md` **裁定 4** | **拆分**：`suspension_kind` 为 `static_before` / `static_after` ⇒ 合法**静态挂起**（`next` **允许为空**）⇒ 继续；**非静态**（`suspension_kind` 为空）且**无动态中断** ⇒ 仍按 B10F1 抛 `no_pending_interrupt`（**不论 `next` 是否为空**） | 同上 |
| **F-6 · 验收脚本 `case_recursion_limit`** | `harness/demo/graph_core.py` | `soft(...)` → `check(...)`；异常判定收紧为 `GraphRecursionError`；**不删**既有「自环图」用例形态 | 追认落 `harness/verification/B13F1/manual-verification.md` |
| **F-7 · README 软断言清单** | `harness/demo/README.md` | 删除 `recursion_limit` 的软断言行；保留 C25 一行；「形态一旦拍板即升级」的规则文字保留 | 同上 |
| **F-8 · B7F1 低层入口说明** | `specs/b7f1-superstep-loop/contracts/superstep-contract.md` **§1 / §5** · `specs/b7f1-superstep-loop/spec.md` | **只增** **V-26** + 一句：「静态断点属图级策略，`run_super_step` / `run_super_steps` 收到非空静态字段时显式拒绝」⇒ 既有签名 / 返回类型判据**一字不改** | 同上 |
| **F-9 · 静态挂起检查点 metadata** | `_suspend_metadata` / `_write_suspend`；`specs/b10f1-interrupt-resume/contracts/checkpoint-contract.md` **§4**（写侧载荷）；`specs/b10f1-interrupt-resume/spec.md` **裁定 9** | **只增** `suspension_kind` / `static_ack` 两个 metadata 键（缺省 `None`；静态值 `static_before` / `static_after`；`static_ack` = 通道版本水位）⇒ 旧快照缺键时按 `None` 解码（宽容）；既有 `next` / `interrupts` / `tasks` / `scheduler` 的**既有键**逐字不变；**本 feature 的实现 MUST 把这两个键镜像进 `scheduler` 子字典**（供当前 `get_tuple` 读取；B14F1 同时持久化顶层 metadata） | 同上 |
| **F-10 · 静态恢复完成快照** | `_clear_static_suspension`（`run_graph` 完成路径）；`specs/b10f1-interrupt-resume/contracts/checkpoint-contract.md` **§4**；`specs/b10f1-interrupt-resume/spec.md` **裁定 9** | **只增**一条**一次性完成写**：静态恢复返回 `SuperStepResult` 时 `checkpointer.put` 写完成快照（`next=()` / `interrupts=()` / `tasks=()` / `suspension_kind=None` / `static_ack=None` / `fanout={}`）⇒ **不是**「每轮末快照」（后者仍归 B14F1）⇒ **MUST NOT** 与 B14F1 的持久化策略重复 / 冲突 | 同上 |

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：系统 MUST 支持**静态中断点**：在指定节点执行**前**或执行**后**挂起。
- **FR-002**：静态中断点的配置 MUST 通过**图定义侧**提供 —— **`GraphSpec` 的两个
  keyword-only 字段** `interrupt_before` / `interrupt_after`（`str | Sequence[str]` ·
  缺省空 ⇒ **tuple 合法**）⇒ **裸 `"*"` = 全部可执行节点**（上游同款；排除
  `__start__` / `__end__`）；**`compile()` 的接受形态另由 B7F2 收紧为裸 `"*"` / `list[str]`
  （D-1 / D-2）**；**MUST NOT** 以 `RunConfig` 作为静态断点的载体。
- **FR-003**：静态断点配置 MUST 在 `GraphSpec` **构造时**校验，且 MUST 走**单一入口**：
  `GraphSpec.__post_init__` → `_validate_graph_spec` → `normalize_static_points`
  （**MUST NOT** 在 `__post_init__` 另写一套校验）。裸 `"*"` MUST 展开为
  **当前节点表的全部可执行节点**（上游 All 语义；**排除 `__start__` / `__end__` 哨兵**）。
  **失败信号逐条写死**：
  - **裸值**（整个值是字符串）：裸 `"*"` 合法并展开；其余任意裸字符串（含 `""` /
    `"__start__"` / `"__end__"` / 普通节点名）⇒ `TypeError`（**V-22**）；
  - **序列元素**：非 `str` ⇒ `TypeError`（**V-22**）；`""` ⇒ `ValueError`（**V-23**）；
    `"__start__"` / `"__end__"` / `"*"` ⇒ `ValueError`（**V-24**）；不在 `spec.nodes`
    ⇒ `ValueError`（**V-25** · 消息点名该节点）；
  - 重复名字 MUST 去重；空序列 = 关闭；`None` ⇒ `TypeError`（**B7F2** 归一为 `()`）。
- **FR-004**：静态挂起 MUST 复用 **`InterruptResult`**（4 字段 `state` / `interrupts` /
  `executed` / `steps`）⇒ `interrupts` MUST 是**空元组** `()`；`as_result_dict()` MUST 产出
  `{**state, "__interrupt__": ()}`；**MUST NOT** 新增结果类型 / 第 5 个字段 / 另一条挂起路径。
  ⚠️ `suspension_kind` MUST **NOT** 成为 `InterruptResult` 的字段 —— 它只住在**检查点
  metadata**（**F-9**）⇒ `InterruptResult` 仍严格是 **4 字段**。
  `executed` MUST 如实列出**到挂起时实际执行过**的节点（确定序：标准任务按节点名序 ·
  fan-out 任务按 TaskId 序）⇒ `interrupt_before` 的目标 MUST NOT 出现；`interrupt_after`
  的目标 MUST 出现（fan-out N 次则出现 N 次）。
- **FR-005**：`interrupt_before` MUST 在**递归检查之后、消费触发源 / 执行任何任务之前**判定：
  若本轮任一待执行任务（标准触发或 fan-out）的目标在断点集合里 ⇒ **整轮不执行**；目标
  **未执行**；本轮**不合并写入**、**不消费触发源版本**、**不推进 `SchedulerState.step`**。
  ⚠️ **轮次计数口径**：循环顶部的局部计数器 `steps += 1` **保持不变**（空终轮口径属 B7F1
  冻结面）⇒ before 挂起时 `InterruptResult.steps` MUST 取 **`steps - 1`**（不含本轮）。
- **FR-006**：`interrupt_after` MUST 在本轮**完整执行并合并写入之后、下一轮之前**判定：
  若本轮任一已执行任务的目标在断点集合里 ⇒ 挂起；目标**已执行**（fan-out N 次各一次）；
  挂起态 `state` **含**本轮写入；`steps` **计入**本轮；恢复后**不重跑**已执行节点。
- **FR-007**：静态挂起 MUST 走**同一条**图级入口与恢复机制：`input=None` 是规范恢复形态；
  `Command(resume=...)` MUST 被接受（值**不投递**给任何节点）；恢复 MUST 挂 checkpointer
  （**MUST NOT** 内存态旁路）。恢复时 MUST 把检查点里的 **`static_ack`** 传给
  `_run_graph_loop` —— **`input=None` 与 `Command(resume=...)` 两条恢复入口同款**，
  before / after 两种静态挂起也同款 ⇒ 否则静态 before 会在恢复首轮**立即重挂**。
  静态挂起 MUST 用**显式 `suspension_kind`** 标记
  （`static_before` / `static_after`）⇒ **合法静态挂起 = `interrupts == ()` 且
  `suspension_kind` 为静态值**；`next` **允许为空**（最后一个节点 after 挂起 / before 时
  只有 fan-out 任务）⇒ **MUST NOT** 用「`next` 非空」单独判定静态挂起，也 **MUST NOT**
  把空 `next` 的静态挂起误判为 `no_pending_interrupt`。挂起写侧 MUST 记录可恢复的 `next`：
  `interrupt_before` ⇒ 本轮未执行的标准目标节点（fan-out 现场另存）；`interrupt_after` ⇒
  按写后状态计算出的**下一轮**触发节点（MUST NOT 把刚执行过的目标强行列入 `next`）。
  静态恢复完成（返回 `SuperStepResult`）时 MUST 写完成快照清 `suspension_kind` / `static_ack`
  （`next=()` / `interrupts=()` / `tasks=()` / `fanout={}`）⇒ 防止后续 `input=None` 重放旧挂起。
  该**一次性完成写**登记为 **F-10**（见回溯修订清单）。
- **FR-008**：静态断点 MUST 具备**防重复触发**语义（与上游 `should_interrupt` 同款）：同一
  断点在「自上次静态挂起以来**没有任何通道版本推进**」时 MUST NOT 再次触发；该版本水位
  MUST 以 **`static_ack`** 记录；目标再次执行并产生新写入后 MAY 再次触发。空 `StateDict`
  （`input={}`）不产生通道写入 ⇒ 按本口径**抑制**重挂（与 `input=None` 同款）。
- **FR-009**：优先级 MUST 确定：**递归超限 > 静态 before**；**真异常 > 动态中断 > 静态
  after > 正常完成**；同一节点同时配 before 与 after 时，before 先命中；恢复后该节点
  **首次执行完成**后 after 命中。
- **FR-010**：`recursion_limit` 的**规范载体** MUST 是普通 dict：
  `invoke(input, {"recursion_limit": N})`；L2 `run_graph` MUST 同时接受
  `RunConfig.recursion_limit`。⚠️ **dict 与 `RunConfig` 是互斥的替代载体**（一次运行只接受
  **一个** `config` 对象）⇒ **不存在「同时提供两者」的路径**；若上层只持有 `RunConfig`，
  以其字段为准。**优先级**：**dict / `RunConfig`（二选一） > 既有 `max_steps` > 默认值**。
  **MUST NOT** 新增显式 `recursion_limit=` 关键字（上游 1.2.11 也没有该关键字）⇒ L2 内部
  直控继续用 `max_steps`。
  ⚠️ **`invoke` 属 B7F3（M2）**：对外 `invoke(input, {"recursion_limit": N})` 的 dict 载体
  透传由**下游承接 D-3** 收口；本 feature 只在 L2 `run_graph` 上判 FR-010。
- **FR-011**：`recursion_limit` 的**默认值 MUST 为 10007**（上游 1.2.11 的有效缺省）·
  **硬编码** · MUST NOT 读任何环境变量（含 `LANGGRAPH_DEFAULT_RECURSION_LIMIT`）·
  MUST 在 spec 与用户文档中写死。
- **FR-012**：`recursion_limit` MUST 校验：**非 `None` 值**的类型为 `int` 且**不是** `bool`；
  值 MUST `>= 1`；非 `None` 的非法类型 ⇒ `TypeError`；`< 1` ⇒ `ValueError`（消息 MUST
  指出「at least 1」）；校验 MUST 在**入口立即**发生（哪怕本轮没有任务）。
  ⚠️ **`recursion_limit=None` MUST 视为「未提供」**：不进入本校验，落回 `max_steps` /
  `DEFAULT_RECURSION_LIMIT`（见 Edge Cases）；**MUST NOT** 因 `None` 抛 `TypeError`。
- **FR-013**：`recursion_limit` MUST 计数 **super-step 执行轮**：一个执行轮内无论有 1 个
  还是 N 个任务（含 fan-out）都只计 **1**；空终轮不计；被 `interrupt_before` 拦住而**没有
  执行任何任务**的轮不计；`interrupt_after` 所在轮**计入**。MUST NOT 按节点调用次数计数。
  ⚠️ 计数范围 = **单次 `run_graph` 调用**：跨静态挂起恢复时使用**新的独立预算**（不累计、
  不回填），与 **B10F1** 的「`SchedulerState.step` 不落盘、恢复时重新计数」冻结口径一致。
  ⚠️ 这里的「空终轮不计」**只**指 `recursion_limit` 的计数口径；`SuperStepResult.steps`
  的「含空终轮」口径属 **B7F1 冻结面**，本 feature MUST NOT 改变。
- **FR-014**：超限时 MUST 抛契约层的 **`GraphRecursionError`**：结构化属性
  `recursion_limit` 与 `current_step` MUST 如实反映；消息 MUST 含「递归超限」语义与两个
  数值；MUST NOT 包装 / 改写成其它异常类型。
- **FR-015**：fan-out 与静态断点的交互 MUST 满足 H-3 / H-4：fan-out 轮**照常计入**上限；
  `interrupt_before` ⇒ N 个 fan-out 任务**各自保留、一个都不执行**；`interrupt_after` ⇒
  N 个**各执行一次**；**MUST NOT** 把 N 个任务合并成一个；**MUST NOT** 伪造 N 个中断载荷。
- **FR-016**：静态挂起 MUST **原样保留** fan-out 任务（目标节点名 + 原样入参 + TaskId 顺序 +
  抑制标志）⇒ 恢复后 MUST 恰好重试同样的 N 个任务、入参**逐字不变**、顺序按 TaskId；
  MUST NOT 丢失、改写、合并或重新生成任务。
- **FR-017**：既有低层入口 `run_super_step` / `run_super_steps` 的**签名与返回类型 MUST
  一字不动**；静态断点 MUST 只在 `run_graph`（图级入口）生效；低层入口收到**非空**静态
  字段时 MUST **显式拒绝**（**V-26** · `ValueError` · 消息说明「静态断点只在 `run_graph`
  生效」）；**MUST NOT** 静默忽略，也 **MUST NOT** 为低层入口改返回类型；`GraphSpec` 的缺省
  空字段 MUST 使既有调用方**零改动**。
- **FR-018**：本 feature **MUST NOT** 新增 L1 符号 / 新契约条目（C1–C27 之外）/ 新门禁编号；
  MUST NOT 破坏 C4 / C6 / C8 / C17。
- **FR-019**：内核路径 MUST NOT import `langchain*` / `langgraph*` / `langsmith`；
  MUST NOT 读环境变量；MUST 零出站；MUST 只依赖标准库；ARCH-1：L2 只依赖 L1。
- **FR-020**：同一份图规格重复执行 **≥ 3** 次 ⇒ 最终状态、执行序列、挂起 / 超限的判定
  MUST **逐项相等**（确定性 · 不依赖完成时刻的竞态）。
- **FR-021**：`harness/demo/graph_core.py` 的 `case_recursion_limit` MUST 把
  `soft(...)` 升级为 `check(...)`，并把异常判定收紧为 **`GraphRecursionError`**
  （MUST NOT 让「任意异常」通过）。
- **FR-022**：本 feature MUST 提供与 `graph_core` **同调用形态**的 L2 硬测试：
  `run_graph(..., config={"recursion_limit": 3})` ⇒ `GraphRecursionError`，**当下真跑通过**。
- **FR-023**：`graph_core.py` 的**端到端真跑**依赖 `compile()` / `invoke()`（B7F2 / B7F3 ·
  M2）⇒ 作为**具名承接 D-3** 在 B7F3 收口（**2026-11-15 用户澄清拍板：保持 L2-only，延期端到端**）；
  M1 阶段 `graph_core.py` MUST 先检测「门面未就绪」（`compile()` / `invoke()` 为桩）并以
  **退出码 2（环境未就绪）** 结束，**MUST NOT** 把它计入硬断言 FAIL；退出码 **1** 只留给
  真实硬断言失败。本 feature MUST NOT 写永久红的 CI，也 MUST NOT 伪造端到端输出；该延期
  MUST 记入人工验证记录的「遗留问题」。
- **FR-024**：所有上游**行为**断言 MUST 带**版本 + `路径:行号`**；**缺席断言** MUST 带
  **检索范围**（如「检索 `langgraph/pregel/` 无同名入口」）；差分场景 **D-38…D-49** MUST 落
  `tests/differential/parity_probe.py`（上游缺席即 skip）。
- **FR-025**：MUST 有 `harness/verification/B13F1/manual-verification.md`，五段式齐全
  （验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）+ 来源覆盖表；未实跑项 MUST 如实登记；
  该记录 MUST 包含 **F-1…F-10** 与 **X-1 / X-2 / X-6 / X-8** 的追认文字（X-1 的承接方为
  B7F3，X-2 为 B7F2，X-6 为 B7F1 契约 F-8，X-8 为 B14F1 / B15F1 / B16F1）。
- **FR-026**：本 feature MUST NOT 越界实现：持久化后端（B14F1 / B16F1）· `compile()` /
  `invoke()` / `stream()`（B7F2 / B7F3 / B8F2）· 构建器（B6F1）· async · 子图 /
  `Command.PARENT` · 节点级重试 / 超时 · `Send` 语义变更 · trace（B19F1）。
- **FR-027**：失败消息 MUST 便于定位：不存在的断点节点名 MUST 点名该名字；递归超限消息
  MUST 给出 `recursion_limit` 与 `current_step`；MUST NOT 用含糊的「出错了」。
- **FR-028**：dict 载体里的**未知键** MUST 被忽略（它们可能属于其它运行期参数）；
  但 `recursion_limit` 的**非法值** MUST 显式失败（FR-012）——「宽容未知、严格已知」。
- **FR-029**：`GraphSpec` 的静态断点字段 MUST 不可变 / 防御性拷贝（构造后外部修改传入
  的 list 不得改变规格）；运行期 MUST NOT 改写它们。
- **FR-030**：对外公开 API 面 MUST 保持 **7 个符号**；`recursion_limit` 不新增门面符号，
  只通过 dict / `RunConfig` 字段承载。
- **FR-031**：本 feature MUST 提供**纯 L2 单元测试**（不经由构建器 / `compile()` /
  `invoke()`），且新增代码的**行 / 分支覆盖率 MUST 为 100%**。
- **FR-032**：`harness/demo/README.md` 的软断言清单 MUST 同步删除 `recursion_limit`
  一行（载体已锁定）；「形态一旦拍板即升级」的规则文字与 C25 一行 MUST 保留；
  MUST NOT 新增 / 删除其它行。

### 需求 ↔ 成功标准 追溯表

> 判据编号沿用提示词 §6（**A1–A3**）；既有门禁编号沿用 **G1–G30**（**勿与 A 编号混义**）。
> **每条 FR 至少挂 1 条 SC · 每条 SC 至少挂 1 条 FR**（**FR 32 条 · SC 24 条**）。

| FR | 主题 | 对应 SC | 主要判据 |
|---|---|---|---|
| FR-001 | 静态断点 before / after | SC-001 / SC-002 | 两条用例都可判定 |
| FR-002 | 配置落位 = `GraphSpec` 字段 | SC-006 / SC-014 | 字段生效 · 非法配置失败 |
| FR-003 | 构造期校验 | SC-014 | 失败率 == 100% · 消息点名 |
| FR-004 | 挂起载体 = `InterruptResult` · 空载荷 | SC-006 / SC-001 / SC-002 | `__interrupt__ == ()` · 无新类型 |
| FR-005 | before 整轮挂起 | SC-001 / SC-007 | 目标 0 次 · 不消费版本 |
| FR-006 | after 写后挂起 | SC-002 | 目标 1 次 · 状态含写入 |
| FR-007 | 静态恢复同款 · checkpointer | SC-011 / SC-012 | 两种恢复形态 · 无误判 |
| FR-008 | 防重复触发 | SC-011 | 立即恢复不重挂 |
| FR-009 | 优先级 | SC-010 | 四层优先级成立 |
| FR-010 | `recursion_limit` 载体 / 优先级 | SC-006 | dict / RunConfig / max_steps 三者 |
| FR-011 | 默认 10007 · 零环境变量 | SC-004 | 默认值断言 · env 无效 |
| FR-012 | 上限校验 | SC-004 / SC-013 | 非法值入口失败 |
| FR-013 | 轮次计数 | SC-007 / SC-008 | 轮 vs 节点调用 · fan-out 计入 |
| FR-014 | 复用 `GraphRecursionError` | SC-003 / SC-013 | 类型 · 结构化属性 · 不包装 |
| FR-015 | fan-out × 静态断点 | SC-009 / SC-008 | N 任务独立 · 不合并 |
| FR-016 | fan-out 现场保留 | SC-009 | 恢复后任务 / 入参 / 顺序逐项相等 |
| FR-017 | 低层入口冻结 | SC-015 | 签名 / 返回类型差异 == 0 |
| FR-018 | 无新 L1 / 契约 / 门禁 | SC-016 | 符号面 / 条目 / 编号差异 == 0 |
| FR-019 | 依赖 / 层纪律 | SC-018 / SC-019 | 导入 0 · 出站 0 · env 0 |
| FR-020 | 确定性 | SC-017 | ≥3 次逐项相等 |
| FR-021 | `graph_core` 软断言升级 | SC-005 | `soft` 0 次 · `check` ≥1 |
| FR-022 | L2 等价硬测试 | SC-005 | 当下真跑通过 |
| FR-023 | 端到端延期具名 | SC-005 / SC-021 / SC-024 | 具名承接 · 无永久红 |
| FR-024 | 上游纪律 · 差分 | SC-022 | 行号覆盖率 · D-38…D-49 |
| FR-025 | 人工验证记录 | SC-021 | 五段式 · 来源覆盖 |
| FR-026 | 不越界 | SC-020 | 越界数 == 0 |
| FR-027 | 失败消息可定位 | SC-003 / SC-014 | 点名节点 / 两个数值 |
| FR-028 | 宽容未知 · 严格已知 | SC-006 / SC-004 | 未知键不失败 · 非法值失败 |
| FR-029 | 字段不可变 / 防御性拷贝 | SC-015 / SC-017 | 外部修改不影响规格 |
| FR-030 | 公开 API 面不变 | SC-016 | 门面仍 7 符号 |
| FR-031 | 纯 L2 测试 · 覆盖率 | SC-023 | 行 / 分支 100% |
| FR-032 | README 软断言清单同步 | SC-005 | README 无 `recursion_limit` 行 · C25 保留 |

> **反向覆盖**：SC-001 ← FR-001 / FR-004 / FR-005 · SC-002 ← FR-001 / FR-004 / FR-006 ·
> SC-003 ← FR-014 / FR-027 · SC-004 ← FR-011 / FR-012 / FR-028 ·
> SC-005 ← FR-021 / FR-022 / FR-023 / FR-032 · SC-006 ← FR-002 / FR-004 / FR-010 / FR-028 ·
> SC-007 ← FR-005 / FR-013 · SC-008 ← FR-013 / FR-015 · SC-009 ← FR-015 / FR-016 ·
> SC-010 ← FR-009 · SC-011 ← FR-007 / FR-008 · SC-012 ← FR-007 ·
> SC-013 ← FR-012 / FR-014 · SC-014 ← FR-002 / FR-003 / FR-027 ·
> SC-015 ← FR-017 / FR-029 · SC-016 ← FR-018 / FR-030 · SC-017 ← FR-020 / FR-029 ·
> SC-018 ← FR-019 · SC-019 ← FR-019 · SC-020 ← FR-026 · SC-021 ← FR-023 / FR-025 ·
> SC-022 ← FR-024 · SC-023 ← FR-031 · SC-024 ← FR-023 —— **无空缺**。

### Key Entities

- **静态中断点**：图定义侧的一个「节点名 + before/after」配置 —— 决定运行到该节点**之前**
  或**之后**挂起；成员语义（顺序无关）· 裸 `"*"` = 全部**可执行**节点（构造期展开；排除
  `__start__` / `__end__`）· 其余只允许真实节点名（`START` / `END` / `["*"]` 非法）。
- **`GraphSpec.interrupt_before` / `.interrupt_after`**：本 feature 新增的两个 keyword-only
  字段（缺省 `()`）—— 静态断点的**唯一** L2 载体；由 B7F2 从 `compile()` 关键字填入。
- **`InterruptResult`（复用 · 4 字段）**：静态挂起的**唯一**结果载体 —— `state` / `interrupts`
  （空元组）/ `executed` / `steps`；`as_result_dict()` 产出 `__interrupt__` 空元组。
- **`recursion_limit`（有效上限）**：super-step 执行轮的**安全阀**；规范载体是普通 dict 的
  `"recursion_limit"` 键；默认 **10007**；硬编码、零环境变量。
- **`GraphRecursionError`（L1 复用）**：递归超限的**显式失败信号** —— 结构化属性
  `recursion_limit` / `current_step`；消息只是摘要。
- **静态挂起现场**：挂起时写入 checkpointer 的纯数据 —— 快照 `values` + 调度账本
  （`versions_seen` / `channel_versions` / `node_versions` / `dynamic_edges` / **`fanout`**）+
  `next`（待执行节点 · **允许为空**）+ `interrupts = ()` + **`suspension_kind`**
  （`static_before` / `static_after`）+ **`static_ack`**（挂起时的通道版本水位）；
  挂起时 `scheduler` 子字典另含这两个键的**镜像**（供当前 `get_tuple` 读取）；
  **不含**伪载荷。
- **静态挂起确认（anti-repeat）**：记录「上次静态挂起时的通道版本水位」⇒ 没有新写入时同一
  断点不重复触发；目标再次执行并推进版本后可以再次触发。
- **fan-out 任务身份**：每个 `Send` 对应一个独立任务（TaskId 序 · 目标 + 原样入参）⇒
  静态 before 时 N 个各自保留、after 时 N 个各执行一次；**MUST NOT** 共享一条任务记录。
- **dict 运行配置**：`invoke` 的第二参数 —— 至少承载 `"recursion_limit"`；未知键忽略；
  `RunConfig` 是**互斥的等价备用载体**（一次运行只接受一个 `config` 对象）。
- **`graph_core` 硬断言**：`case_recursion_limit` 的 `check(...)` —— 判定异常类型必须是
  `GraphRecursionError`；端到端真跑在 B7F3 收口。

### Out of Scope

- **持久化后端实现**（`MemorySaver` / `SqliteSaver` / 历史 / 时间旅行）—— 属 B14F1 / B15F1 /
  B16F1；本 feature 只消费 `Checkpointer` 协议、只做内存态挂起。
- **`compile()` / `invoke()` / `stream()` 的对外 API** —— 属 B7F2 / B7F3 / B8F2；
  本 feature 只提供 L2 入口与下游接线。
- **`StateGraph` 构建器** —— 属 B6F1。
- **async** —— v2。
- **子图 / `Command.PARENT`** —— v2（C26）。
- **节点级重试 / 超时** —— 不在 v1 范围。
- **`Send` 的语义 / 类型变更** —— 属 B11F1 / 上游对齐批次。
- **`interrupt_before` / `interrupt_after` 的「调用时覆盖」形态** —— 本 feature 只锁定
  **图定义侧**；上游 1.2.11 的 `invoke(..., interrupt_before=...)` 实测不生效 ⇒ 不作为
  v1 契约。
- **`["*"]` 作为节点名** —— 上游编译期拒绝（P-17）⇒ freegraph 同样拒绝；**裸 `"*"`**
  作为「全部**可执行**节点」的 All 写法**支持**（上游同款；排除 `__start__` / `__end__`）。
- **可观测面**（trace / span）—— 属 B19F1。
- **API 兼容矩阵新增行 / `THIRD_PARTY_NOTICES` 变更** —— 属 B24F1；本 feature 零新增行。
- **新增契约条目 / 新增门禁编号** —— 本 feature 零新增；C1–C27 与 G1–G30 保持不变。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001（判据 A2 · `interrupt_before`）**：目标节点执行次数 == **0** 的比率 == **100%**；
  挂起态 `state` 不含目标节点本轮写入的比率 == **100%**；「目标先执行了再挂起」的现象
  出现次数 == **0**。
- **SC-002（判据 A2 · `interrupt_after`）**：目标节点执行次数 == **1** 的比率 == **100%**
  （fan-out 时 == N）；挂起态 `state` 含目标本轮写入的比率 == **100%**；恢复后目标
  **重跑**的次数 == **0**。
- **SC-003（判据 A1 · 递归超限）**：自环图 + `recursion_limit=3` ⇒ 抛出
  `GraphRecursionError` 的比率 == **100%**；`.recursion_limit == 3` 的比率 == **100%**；
  消息含「递归超限」语义与两个数值的比率 == **100%**；「无限运行 / 静默停止 / 抛
  `RecursionError`」的现象出现次数 == **0**。
- **SC-004（默认上限 · 校验）**：未设置时有效上限 == **10007** 的断言成立率 == **100%**；
  设置 `LANGGRAPH_DEFAULT_RECURSION_LIMIT` 后行为**逐字不变**的比率 == **100%**；环境变量
  读取次数 == **0**；`recursion_limit` 为 `0` / 负数 ⇒ `ValueError`；**除 `None` 外**的
  非 `int` / `bool` ⇒ `TypeError` 的比率 == **100%**（`None` 视为未提供，不属非法）。
- **SC-005（判据 A3 · 软断言升级）**：`graph_core.py` 的 `case_recursion_limit` 中
  `soft(` 出现次数 == **0**、`check(` 出现次数 ≥ **1**、异常判定引用
  `GraphRecursionError` 的比率 == **100%**；L2 等价硬测试**当下通过**的比率 == **100%**；
  M1 门面未就绪时脚本以**退出码 2** 结束（不判 FAIL）的比率 == **100%**；
  端到端真跑的延期**具名**（B7F3 · D-3）且未写永久红 CI 的比率 == **100%**；
  `README.md` 中 `recursion_limit` 软断言行被删除、C25 行保留的比率 == **100%**。
- **SC-006（载体形态锁定）**：dict 形态 `{"recursion_limit": N}` 生效的比率 == **100%**；
  `RunConfig(recursion_limit=N)` 生效的比率 == **100%**；dict / `RunConfig` **互斥且各自优先于
  `max_steps`** 的比率 == **100%**；`run_graph` 出现显式 `recursion_limit=`
  关键字的实现数 == **0**（`RunConfig.recursion_limit` 字段不算）；
  「同时提供 dict 与 `RunConfig`」的实现路径数 == **0**；dict 里未知键导致失败的现象次数
  == **0**；「另写一条解析路径」的实现数 == **0**。
  ⚠️ **`invoke(input, {"recursion_limit": N})` 属 B7F3（M2）**：其 dict 载体透传、不包装
  `GraphRecursionError`、无显式关键字等对外判据，由**下游承接 D-3** 在 B7F3 收口；本 feature
  的 SC-006 只判 **L2 `run_graph`** 部分。
- **SC-007（轮次计数）**：每轮 2 个节点、上限 3 ⇒ 只执行 **3** 轮（不是 3 次节点调用）的
  比率 == **100%**；空终轮被计入上限的现象次数 == **0**；被 before 拦住而未执行的轮被
  计入的现象次数 == **0**；**静态挂起恢复后沿用旧步数的现象次数 == 0（每次 `run_graph`
  使用独立预算）**。
- **SC-008（fan-out 计入上限 · B11F1 的 D-2）**：fan-out 轮被计入步数的比率 == **100%**；fan-out
  绕过上限的现象次数 == **0**。
- **SC-009（fan-out 独立命中 · B11F1 的 D-7）**：before 时 N 个 fan-out 任务全部保留、执行次数 == **0**
  的比率 == **100%**；after 时 N 个各执行一次的比率 == **100%**；N 个任务被合并成 1 个的
  现象次数 == **0**；恢复后任务数 / 入参 / 顺序与挂起前**逐项相等**的比率 == **100%**。
- **SC-010（优先级）**：真异常 > 动态中断 > 静态 after > 正常完成的判定成立率 == **100%**；
  递归超限先于静态 before 的比率 == **100%**；before 先于 after 的比率 == **100%**；
  「静态 after 吞掉真异常 / 动态载荷」的现象次数 == **0**。
- **SC-011（静态恢复 · `input=None`）**：静态挂起后用 `input=None` 恢复、目标恰好执行一次的
  比率 == **100%**；同一断点立即重复触发的次数 == **0**；无 checkpointer 时**不**声称恢复的
  比率 == **100%**；`next` 为空的静态挂起（最后节点 after / 纯 fan-out before）仍可恢复的
  比率 == **100%**；`suspension_kind` 正确标记的比率 == **100%**；`static_ack` 正确记录 /
  完成清空的比率 == **100%**。
- **SC-012（静态恢复 · `Command(resume=...)`）**：静态挂起后 `Command(resume=...)` 被接受、
  值不投递、流程继续的比率 == **100%**（**含 `interrupt_before`：恢复首轮不得因缺少
  `static_ack` 而立即重挂**）；合法静态挂起（**含 `next` 为空**）被误判为
  `no_pending_interrupt` 的次数 == **0**；**`Command(resume=...)` 路径**未挂 checkpointer
  时抛 `checkpointer_required` 的比率 == **100%**。⚠️ `input=None` 且未挂 checkpointer
  按 Edge Cases 视为**新运行**（**不**要求 `checkpointer_required`）。
- **SC-013（错误传播）**：`GraphRecursionError` 原样到达调用方的比率 == **100%**；
  「被包装成 `RuntimeError` / 其它类型」的现象次数 == **0**。
- **SC-014（配置校验）**：不存在的断点节点名 / `START` / `END` / 空串 / `["*"]` / 裸非
  `"*"` 字符串 / 非 `str` ⇒ 构造期显式失败（类型可判定 + 消息点名）的比率 == **100%**；
  裸 `"*"` ⇒ 展开为全部**可执行**节点且不失败的比率 == **100%**；「静默忽略」的用例数 == **0**。
- **SC-015（向后兼容）**：既有 M1 测试**一条不改**全部通过的比率 == **100%**；既有
  `GraphSpec(...)` 调用零改动的比率 == **100%**；`run_super_step` / `run_super_steps` 的
  签名 / 返回类型差异 == **0**；低层入口对非空静态字段**显式拒绝**的比率 == **100%**；「静默忽略 / 挂起」的现象次数 == **0**。
- **SC-016（结构纪律）**：L1 符号面差异 == **0**；门面导出面仍 **7** 个；契约条目仍
  C1–C27；门禁编号仍 G1–G30 且连续；`THIRD_PARTY_NOTICES` 差异 == **0**；API 兼容矩阵
  新增行 == **0**。
- **SC-017（确定性）**：同一份规格重复执行 **≥ 3** 次 ⇒ 最终状态、执行序列、挂起 / 超限
  判定**逐项相等**（差异 == **0**）；两次独立运行互不影响的比率 == **100%**。
- **SC-018（依赖隔离 · 零出站）**：`src/freegraph/**` 对 `langchain*` / `langgraph*` /
  `langsmith` 的导入次数 == **0**；环境变量读取次数 == **0**；出站次数 == **0**；
  第三方运行时依赖数 == **0**。
- **SC-019（层纪律）**：L2 → L3 / L4 / L5 的依赖边数 == **0**；L2 → L1 的方向合法的比率
  == **100%**；`GraphSpec` 与 `run_graph` 的改动全部落在 L2 的比率 == **100%**。
- **SC-020（不越界）**：B14F1 / B15F1 / B16F1 / B7F2 / B7F3 / B8F2 / B6F1 / B19F1 的实现
  代码被本 feature 修改的处数 == **0**；越界实现数 == **0**。
- **SC-021（人工验证记录）**：`harness/verification/B13F1/manual-verification.md` **存在**
  且**五段式**齐全；来源覆盖表对全部判据（A1–A3 + SC + FR）**以及 X-1 / X-2 / X-6 / X-8
  追认**的覆盖率 == **100%**；
  未实跑项（graph_core 端到端 · → B7F3）如实记入「遗留问题」的比率 == **100%**；
  伪造输出数 == **0**。
- **SC-022（上游纪律 · 差分）**：上游**行为**断言带版本 + `路径:行号` 的比例 == **100%**；
  **缺席断言**带检索范围的比例 == **100%**；**D-38…D-49** 在
  `tests/differential/parity_probe.py` 中全部存在且判词齐备的比率 == **100%**；
  上游缺席时 skip（不判失败）的比率 == **100%**。
- **SC-023（可测性 · 覆盖率）**：新增代码的行 / 分支覆盖率 == **100%**；不经由构建器 /
  `compile()` 的纯 L2 单元用例数 ≥ **1**。
- **SC-024（无永久红）**：CI 中「因本 feature 新增的永久失败断言」条数 == **0**；所有延期
  项都有**具名承接方 + 里程碑**的比率 == **100%**。

---

## Assumptions

- **权威顺序**：宪法 > 立项书 > 本 feature 提示词初稿 > 仓库现状；本 spec 的裁定
  1–14 按此顺序解决引文与上位文档的冲突。
- **规模参考**：680 行（实现 320 / 测试 360）· 3 人日（提示词表格值 · 立项书 §5.2），
  作为 plan 的输入而非本 spec 的约束。
- **spec 目录命名**：沿用仓库既有的「**feature ID 前缀**」约定 ⇒
  `specs/b13f1-static-interrupt-recursion-limit`（**不带**三位序号）。
- **分支**：本仓库**无** `.specify/extensions.yml` ⇒ 无 `before_specify` 钩子 ⇒ 本次
  **不创建** git 分支，与既有 feature 一致。
- **Python 基线**：`>= 3.11`；typing 构件上限 = **3.11**。
- **内核依赖面**：**零第三方依赖**（`dependencies = []`）；`langgraph` **仅**以 PEP 735
  依赖组出现在**测试侧**（`differential` 组）⇒ 本 feature MUST NOT 让内核依赖它。
- **上游取证环境**：本机已安装 `langgraph 1.2.11`
  （`/home/ctyun/.local/lib/python3.12/site-packages/langgraph`）⇒ 本 spec 引用的行为与
  行号均为**本轮实际核对 / 实测**所得；换版本 MUST 重新核实（宪法原则 VIII · FR-024）。
- **上游实测记录（本轮 · 脚本不进仓库）**：
  **E-01** 自环 + `recursion_limit=3` ⇒ `GraphRecursionError`（消息含 limit）
  ⇒ **E-02** 未设置上限的缺省有效值 == **10007**（`ensure_config()`）
  ⇒ **E-03** 静态 before 目标执行 **0** 次、结果**无** `__interrupt__` 键
  ⇒ **E-04** 静态 after 目标执行 **1** 次、结果**无** `__interrupt__` 键
  ⇒ **E-05** 静态 before 后 `input=None` 恢复 ⇒ 目标执行 1 次
  ⇒ **E-06** 静态挂起后 `Command(resume="X")` 与 `None` 行为一致（值被忽略）
  ⇒ **E-07** `Command(goto=[Send,Send])` + 静态边 `fan→w` + `interrupt_before=["w"]` ⇒
  3 个待执行任务（1 个标准 + 2 个 fan-out）、`w` 执行 0 次、`interrupts == ()`
  ⇒ **E-08** 同上 + `interrupt_after=["w"]` ⇒ 3 个任务各执行 1 次、单个挂起
  ⇒ **E-09** 同一节点同时配 before/after ⇒ before → 恢复 → 执行 → after
  ⇒ **E-10** `compile(interrupt_before=["nope"])` ⇒ `ValueError: Interrupt node \`nope\` not found`
  ⇒ **E-11** `compile(interrupt_before="*")` ⇒ 接受（All）· `compile(interrupt_before=["*"])` ⇒
  `ValueError`（`"*"` 不是节点）· 裸 `"review"` / `("review",)` ⇒ `TypeError`
  ⇒ **E-12** 节点抛真异常 + `interrupt_after` ⇒ 原异常优先，不返回挂起态
  ⇒ **E-13** 最后节点 `interrupt_after` ⇒ `snapshot.next == ()`，`invoke(None, config)` 直接完成
  ⇒ **E-14** `recursion_limit` 为 `True` / `1.5` ⇒ 上游实际接受（`True ≈ 1`）；`"3"` ⇒ `TypeError`。
- **代码落位**：L2 = `src/freegraph/runtime/`（层注册表**已登记为目录条目**）⇒ 新增 / 修改的
  模块**自动**被该条目覆盖 ⇒ **层注册表零改动**。
- **既有冻结面**：门面 **7** 符号面 · L1 契约层 **21** 符号面 · `freegraph.runtime.__all__`
  **23** 个符号 · C1–C27 · G1–G30 —— 本 feature **不新增、不删除**；`GraphSpec` / `run_graph`
  的签名是**兼容扩展**（只增 keyword-only 字段 / 放宽注解）⇒ 按 **F-1…F-10** 回溯修订。
  ⚠️ **F-3 例外**：B11F1 的「`fanout` 不落盘」冻结面按 **F-3** **拆分而不删**
  （B11F1 文档同步修订：`contracts/send-contract.md §5.1` / `data-model.md I-12` /
  `tasks.md T019` / `plan.md PR-8` / `research.md DR-02·D-08` / `quickstart.md DR-02` /
  `spec.md D-3` + 发起者追认；F-14 仅顺序口径说明）。
- **`GraphSpec` 扩展的兼容性**：两个新字段都有缺省 `()` ⇒ 既有 `GraphSpec(channels=...,
  nodes=..., edges=...)` 调用**逐字不变**；构造签名行**只增**。
- **`recursion_limit` 与 `max_steps` 的关系**：`max_steps` 是 B7F1 / B10F1 的既有内部参数，
  本 feature **保留**它（不破坏既有调用），但**对外规范载体**是 `recursion_limit`；
  dict / `RunConfig` 是**互斥**载体（一次运行一个），二者均优先于 `max_steps`（FR-010）。
  **不新增**显式 `recursion_limit=` 关键字（2026-11-15 用户澄清拍板 B · 照抄上游）。
- **计数范围**：`recursion_limit` 按**单次 `run_graph` 调用**计数；静态挂起恢复使用新的
  独立预算（`SchedulerState.step` 不落盘 · 与 B10F1 一致；FR-013）。
- **检查点载体**：本 feature **不实现**任何具体 saver；测试用 B10F1 既有的
  `StubCheckpointer` 或等价内存实现。**职责边界**：`fanout` 的**账本编码**（`to_checkpoint` /
  `from_checkpoint` 增键）归 **本 feature（F-3）**；**实际存储 / 落盘策略**（`MemorySaver` /
  `SqliteSaver`）归 **B14F1**（D-5）。⚠️ 本 feature 的测试用 **JSON 兼容** `arg`；
  非 JSON 兼容 `arg` 的持久化失败面归 B14F1（DR-01）。
- **人工验证记录**：采用仓库既有的**五段式** + **来源覆盖表**；未实跑的项 MUST 显式记入
  「遗留问题」（MUST NOT 伪造输出）。
- **端到端延期**：`graph_core.py` 的 `case_recursion_limit` 端到端真跑需要 `compile()` /
  `invoke()`（B7F2 / B7F3 · M2）⇒ M1 只能做到「软断言升级 + L2 等价硬测试通过」；
  该延期登记为 **EV-1**，承接方 **B7F3**（D-3）。
- **前置依赖**：**B10F1**（动态中断 / 恢复 · `InterruptResult` · checkpointer 协议）·
  **B11F1**（fan-out 任务身份 · D-2 / D-7）· **B7F1**（super-step 计数 · 冻结入口）·
  **B1F1**（`GraphRecursionError`）· **B12F1**（错误 / 中断优先级）。
- **后续解锁**：**M2 全部 8 个 feature**（B6F1 构建器 → … → B8F3）——M2 结束时
  `harness/demo/target.py` 的 fake 模型轮应能跑通（MVP 验收点）。
- **M1 里程碑达成**：本 feature 完成 = M1（运行时内核，10 feature / 30 人日）就绪 ⇒
  「状态模型、super-step 调度、Command / HITL / Send / 并发 / 静态断点 / 递归上限全部就绪；
  **运行时可独立验收（不依赖构建器）**」。

### 环境偏离登记

| # | 门禁 / 判据 | 偏离内容 | 为什么 M1 不可达成 | 承接方 / 追认 |
|---|---|---|---|---|
| **EV-1** | 判据 **A3 / SC-005** 的「`graph_core.py` 硬断言**端到端真跑通过**」 | 本 feature 只做「软断言升级 + L2 等价硬测试」，`graph_core` 的 `compile()` / `invoke()` 真跑延期；**M1 门面未就绪时以退出码 2 结束（不判 FAIL）** | `compile()` 属 **B7F2**、`invoke()` 属 **B7F3**（M2）⇒ M1 无门面 API；MUST NOT 写永久红 CI | **B7F3** · **M2**（D-3）· 追认文字落 `harness/verification/B13F1/manual-verification.md` |

---

## 依据

- **立项书**：`harness/proposals/立项书.md` **§5.2**（**B13F1 行**：层 L2 · 里程碑 M1 ·
  依赖 B10F1 · **680** 行 · 小目标「递归超限抛明确异常」· 3 人日）· **§5.3**（C17 与契约
  修订流程）· **§6.2**（里程碑 M1/M2 定义）· **§9.1**（门禁）· **§9.2**（软 / 硬断言约定）。
- **提示词初稿**：`harness/features/B13F1_静态中断点与递归上限.md` **§1–§10**
  （目标 / 背景与上下文 / 承接条款 / 用户场景 P1–P3 / 功能需求 FR-001–FR-008 /
  成功标准 SC-001–SC-005 / 验收判据 A1–A3 / 关键实体与契约 / 边界 / 红线与质量门禁 /
  交付物与后续）。
- **契约权威**：`harness/reports/Q8-图运行时最小契约.md` **§3.4**（**C17** · `__interrupt__`）·
  `:248`（**C6** · 逐 key 应用 reducer；未知 key 报错）· **C4 / C8**。
- **验收脚本**：`harness/demo/graph_core.py` 的 `case_recursion_limit`（A8 组 · 当前
  `soft(...)`）· `harness/demo/README.md`「硬断言 vs 软断言」（软断言清单与「形态一旦拍板
  就升级为硬断言」规则）。
- **上游源码参照**（**已核实** · `langgraph 1.2.11` · 行号本轮实际核对）：
  `langgraph/_internal/_config.py:32`（`DEFAULT_RECURSION_LIMIT = int(getenv(..., "10007"))`）·
  `:184-186`（`recursion_limit` 的 config 键）·
  `langgraph/pregel/main.py:2563-2564`（`recursion_limit must be at least 1`）·
  `:3004-3011`（`out_of_steps` → `GraphRecursionError`）·
  `langgraph/pregel/_loop.py:608-610`（步数上限先判）· `:667-670`（静态 before 抛
  `GraphInterrupt()`）· `:720-723`（静态 after 抛 `GraphInterrupt()`）·
  `langgraph/pregel/_algo.py:155-185`（`should_interrupt` · 自上次中断以来的更新判定）·
  `langgraph/graph/state.py:1177-1188`（`compile(..., interrupt_before=, interrupt_after=)`）·
  `langgraph/pregel/main.py:768-769` / `:814-815`（`interrupt_*_nodes`）。
- **前置 feature 的规格与契约**：`specs/b10f1-interrupt-resume/spec.md`
  （**FR-005 / FR-020 / FR-024** · **裁定 2 / 4 / 9 / 10** · **SC-010 / SC-011 / SC-012** ·
  下游承接 **D-4**）· `contracts/{checkpoint-contract.md, interrupt-resume-contract.md}`
  （**F-3 / F-4 / F-5 / F-9 / F-10** 的修订对象）· `specs/b11f1-send-fanout/spec.md`（**下游承接 D-2 / D-7** ·
  **D-3**（`fanout` 落盘口径）· **F-13 / F-14**）· `specs/b11f1-send-fanout/{contracts/send-contract.md, data-model.md, tasks.md, plan.md, research.md, quickstart.md}`
  （**F-3 的 B11F1 冻结面拆分对象**：`fanout` 不落盘 ⇒ 自 B13F1 起落盘）· `specs/b7f1-superstep-loop/spec.md`（**FR-003 / FR-005 / FR-007 /
  FR-032** · **B7F1 的**裁定 30 / 32 / 34）· `specs/b12f1-concurrency-errors/spec.md`
  （**裁定 7 / 8 / 11**）· `specs/b1f1-contracts-core/spec.md`（异常体系）。
- **仓库现状**：`src/freegraph/runtime/superstep.py`（`GraphSpec` · `SchedulerState` ·
  `InterruptResult` · `run_super_step` / `run_super_steps` / `run_graph` ·
  `_run_round` 的五个阶段）· `src/freegraph/runtime/_interrupt.py`（动态中断原语）·
  `src/freegraph/runtime/_fanout.py`（fan-out 任务形状）·
  `src/freegraph/contracts/errors.py`（`GraphRecursionError`）·
  `src/freegraph/contracts/types.py`（`RunConfig.recursion_limit`）·
  `src/freegraph/graph.py`（门面 7 符号）· `src/freegraph/_stategraph.py`（`compile()` 仍为
  M0 桩 ⇒ B7F2 / B7F3）。
- **宪法**（`.specify/memory/constitution.md`）：原则 **I**（零 LangSmith 依赖 · 零环境变量）·
  **II**（内核纯净）· **III**（验收契约优先）· **IV**（可诊断性）· **V**（人工验收）·
  **VI**（规格驱动开发 · 判据级可追溯）· **VII**（契约 C1–C27）· **VIII**（证据与术语纪律）·
  **IX**（许可证）· **X**（署名头 + 文档合规）· **XI**（上游优先 · 三态标注一致）·
  **XII**（最优设计优先）· **v1.8.0**（跨 feature 承接 + 破冻结面的三条）。

### 术语与编号约定

- **本 feature 内部编号**：`FR-xxx`（需求）· `SC-xxx`（判据）· `P-xx`（上游对照）·
  `X-x`（偏离登记）· `F-x`（回溯修订）· **`D-1…D-8`**（本 feature 的下游承接）·
  **`D-01…D-14`**（`research.md` §3 / `plan.md` 的**设计决策**）· **`D-38…D-49`**（差分场景）·
  `H-x`（上游 feature → 本 feature 的承接）· `V-1…V-26` / `V-R1…V-R4`（校验规则）·
  `EV-1`（环境偏离；**刻意避开** GraphSpec 校验规则 `V-1…V-26` 的编号空间）。
- **外部编号 MUST 带限定词**（避免误当本 feature 的编号）：例如「**B11F1 的** D-2 / D-7」·
  「**B10F1 的** FR-005」「**B7F1 的** FR-011」；`tasks.md` / `plan.md` 中引用 B11F1 的
  D-2 / D-7 时 MUST 写成「**B11F1 的** D-2 / D-7」。
- **三态标注 MUST 一致**（宪法 v1.12.0）：上游对照表的 `SAME` / `STRICTER` / `DIFF` 与
  偏离登记表逐条对应；标 `DIFF` 的分叉 MUST 在偏离登记里有对应行（本 spec 为 **X-1…X-8**）。
