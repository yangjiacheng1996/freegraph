# 功能块 Specification: 公开 API 门面 `freegraph/graph.py`（7 符号导出面）+ API 签名快照冻结 + 顶层包惰性断言

**Feature Branch**: `b2f2-public-api-facade`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "B2F2 · 公开 API 门面 `freegraph/graph.py` + API 快照测试" —— 完整提示词正文见 `harness/features/B2F2_公开API门面与快照测试.md`。要点：交付 freegraph 的**唯一公开 API 门面** `freegraph/graph.py`（导出 `StateGraph` / `START` / `END` / `Command` / `Send` / `interrupt` / `RunConfig` 共 **7** 个符号），用**签名快照测试**把对外形状钉死，并断言**顶层包惰性**（`import freegraph` 不连带加载门面与契约层）。本 feature 是 M0 地基的第 3 个 feature，**只有类型与形状、没有行为**——`StateGraph` 此刻是可构造但功能未接线的外壳。
> **⚠️ 引文与本 spec 正文的差异**（引文为 `/speckit.specify` 的原始输入，正文以澄清裁定为准）：① 引文 §7 的导出面表把 `Command` / `Send` / `interrupt` / `RunConfig` 列为「类型（行为在 B9F1 / B11F1 / B10F1 / B8F3）」，但**未说明类型面的落点**——本 spec 裁定：`Send` / `interrupt` 的**外壳**在本 feature 就位（否则 `harness/demo/graph_core.py:48-56` 的 7 名字一次性 import 必然失败、整脚本以退出码 2 结束），而**契约层的 18 符号面不变**（见裁定 2）；② 引文 §7 的调用形态表把 `invoke(input, config)` 列入门面调用面，但 `invoke` 属**编译产物**（`CompiledGraph`）——该签名已由 B2F1 冻结，本 feature **只记录、不改、不进快照**（见裁定 7）。

---

## Clarifications

> 本节记录本 feature 的**裁定**（提示词未逐字规定、或与仓库既有冻结面存在张力处的取舍）。全部裁定均已闭合，正文**无未闭合的澄清标记残留**。

### Session 2026-11-07

- **裁定 1（导出面恰为 7 个符号 · 边界）**：门面导出面 **恰为** `StateGraph` / `START` / `END` / `Command` / `Send` / `interrupt` / `RunConfig` —— **不多、不少**。
  `CompiledGraph` / `Graph` / `Node` / `Edge` / `Span` / `TraceQuery` **不**进门面（它们属契约层，由 `freegraph.contracts` 进入）；`draw_mermaid` / `draw_mermaid_png` 属 `Graph` 对象，**不在门面导出面内**（B22F1 / B23F1）。
  **依据**：提示词 §7 导出面表（7 行）· `harness/demo/graph_core.py:48-56` 的 import 段（逐字 7 个名字：`END` / `START` / `Command` / `RunConfig` / `Send` / `StateGraph` / `interrupt`）· `harness/demo/target.py:122`（3 个名字）。
  > **与 Q1 的分工**：本裁定只管「**哪些**符号算公开」的**边界**；「**如何机械判定**」
  > （`__all__` 集合相等 **且** 模块内公开名集合相等）见 **Q1** —— 两者各管一面、不重复。
  > **仓库内已有 5 个门面消费者，导出面被三方独立印证**（2026-11-07 复核补入）：`harness/demo/graph_core.py:48-56` 与 `harness/demo/acceptance.py:51-58` 各自**恰好** import 同样的 7 个名字；`harness/demo/agent_loop.py:33-39`（5 个）与 `harness/demo/visualization.py:36-40`（3 个）是其**子集**；`harness/demo/target.py:122`（3 个）亦为子集。**无一处要求第 8 个符号** ⇒ 导出面「恰 7 个」得到仓库现状的独立确认。
  > `harness/demo/acceptance.py:195-205` 另**独立断言**了 `START == "__start__"` / `END == "__end__"` ⇒ FR-003 的取值同样得到仓库现状的确认。

- **裁定 2（`Send` / `interrupt` 的类型面在本 feature 就位 · 与 B2F1 冻结记录的关系）**：
  门面 **MUST** 导出 `Send` / `interrupt`（提示词 FR-003），二者以**外壳**形式在本 feature 就位（`Send` 可构造；`interrupt` 可调用但 MUST 抛「未接线」异常）。
  **契约层 `freegraph.contracts` 的 18 符号面 MUST NOT 因此改变**——B2F1 冻结记录 §5 第 14 条「`Send` / `interrupt` 的导出 → v2（B11F1 / B10F1）」指的是**契约层**的公开符号面，不是**门面**；本 feature 新增的 5 个门面符号不进入契约层，故 G7（契约层 `__all__` 集合相等 == 18）**恒成立**。
  **行为**分别归 **B11F1**（`Send` 的动态 fan-out）与 **B10F1**（`interrupt` 的中断 / 恢复）。
  **依据**：提示词 FR-003 + §7 状态列（「类型（行为在 B11F1 / B10F1）」）· `harness/demo/graph_core.py:48-56`（7 个名字一次性 import ⇒ 缺任一个即整脚本无法启动）· `specs/b2f1-contracts-protocols/contracts/public-api.md` §0 / §5 第 14 条。

- **裁定 3（门面「零实现体」的机械判据）**：门面模块 **MUST NOT** 定义任何类体 / 函数体——**AST 判据**：门面模块内的 `class` / `def` / `async def` 语句数 **== 0**（仅允许 import、常量赋值、`__all__` 与文档字符串）。
  `StateGraph` / `Send` / `interrupt` 的实现体 MUST 位于**门面之外的下层模块**；B6F1 / B10F1 / B11F1 起在**同一门面导出名下**接线，**门面导出面 MUST NOT 因接线而改变**。
  **依据**：提示词 FR-004（「门面 MUST NOT 定义业务实现体；实现体 MUST 位于下层模块」）+ ARCH-4。

- **裁定 4（`StateGraph` 构造签名的参数名 = `schema`）**：冻结为 **`StateGraph(schema)`——恰一个必填位置参数，参数名 `schema`**。
  **刻意不**逐字镜像上游的 `state_schema`（上游另有 `context_schema` / `input_schema` / `output_schema` 三个可选参数，`langgraph/graph/state.py:216`）；freegraph v1 一律不提供（`context` 独立通道归 **B8F3**）。
  **依据**：宪法原则 III 第 2 项（逐字 `StateGraph(schema)`）· 提示词 §7 调用形态表 · 上游 `langgraph/graph/state.py:216`（差异须写入兼容矩阵的「差异说明」列）。
  > **参数名的冻结口径（2026-11-07 复核澄清）**：本 spec 冻结的是 **freegraph 侧**的参数名
  > （`schema` / `name` / `fn` / `src` / `dst` / `path_fn` / `path_map`），**逐字对齐宪法原则 III
  > 第 2–5 项**；立项书 §4.3 义务列引用的 `node` / `action` / `start_key` / `end_key` / `source` /
  > `path` 是**上游**的参数名（该列描述的是上游形状），**不是** freegraph 的冻结面。
  > 两者**不冲突**；差异已在兼容矩阵的「差异说明」列登记（`StateGraph` 行）。

- **裁定 5（三个构建方法的返回语义 = 链式返回自身）**：`add_node` / `add_edge` / `add_conditional_edges` **均链式返回自身**。
  宪法原则 III 第 4 项明确要求 `add_edge` 链式返回；上游三者**同形**（`add_node` → `Self`（`langgraph/graph/state.py:667`）/ `add_edge` → `Self`（`:928`）/ `add_conditional_edges` → `Self`（`:982`））⇒ 逐条对齐上游可减少 freechain 的适配成本。
  > **口径澄清（2026-11-07 分析轮）**：本裁定冻结的是**签名面**——三个方法的
  > **返回注解 MUST 为 `Self`**（research D-12）；**运行时**的链式返回归 **B6F1**。
  > 本 feature 尚未接线时，四个方法按 **FR-009** 一律抛 `NotImplementedError`
  > （**MUST NOT** 在本 feature 返回自身）——否则与 FR-009 / SC-011 的
  > 「MUST NOT 静默成功」直接互斥。

- **裁定 6（`compile` 的两个可选关键字为 keyword-only）**：冻结为 `compile(*, checkpointer=None, store=None)`——**无参可调用** + **两个可选关键字**。
  上游为 `compile(self, checkpointer=None, *, cache=None, store=None, interrupt_before=None, interrupt_after=None, debug=False, name=None, transformers=None)`（`langgraph/graph/state.py:1177`），多出八个关键字；freegraph v1 一律不提供（`interrupt_before` / `interrupt_after` 属 **B13F1** 的**运行期**配置，不在本冻结面）。

- **裁定 7（`invoke` 的 `config` 形态不属本冻结面）**：`invoke(input, config)` 的**协议签名**已由 B2F1 冻结为 `invoke(self, input: StateDict, config: RunConfig | None = None) -> StateDict`（`src/freegraph/contracts/protocols.py`），本 feature **MUST NOT** 改动它。
  提示词 §7 所述「`config` 同时接受 `RunConfig` 与普通 dict」属 **B7F3** 的**运行时行为**（dict → `RunConfig.from_dict` 转换），**不是签名变更** ⇒ **不进** API 快照。`recursion_limit` 走 dict 形态同理（**B13F1**）。
  **依据**：提示词 §7 调用形态表 · B2F1 冻结面（`public-api.md` §1.1 `CompiledGraph` 行）。

- **裁定 8（快照文件的落位与「唯一手工维护点」）**：API 快照文件落 **`specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`**（沿用 B1F1 / B2F1 的 `specs/<feature>/contracts/` 目录惯例），是**门面导出面与调用签名的唯一手工维护点**；快照的**生成器**与**快照文件**分离——生成器在测试侧，快照文件入库。
  格式 MUST **稳定可复现**：同一份代码两次生成 MUST **逐字节相同**（不含内存地址 / 哈希序 / 时间戳）。

- **裁定 9（兼容矩阵的一致性口径 —— 补 5 行，不是「跳过」）**：兼容矩阵的载体是 `README.md` 的「## API 兼容矩阵」章节（`COMPAT.md` 若届时存在亦适用；**终版归 B24F1**）。
  宪法原则 X 要求「扩展 API 兼容面的特性 MUST 更新兼容矩阵」⇒ 本 feature **MUST 按 B2F1 的口径补入本层新增的 5 行**（`StateGraph` / `START` / `END` / `Send` / `interrupt`），**保持 4 列不变**（既有 18 行逐字不动）；「快照 ↔ 矩阵」一致性检查 = 「门面 7 符号在矩阵中各**恰有一行**」的**集合相等**判定。
  > **与提示词 §8 边界的关系**：提示词说「不建立 `COMPAT.md` 的完整矩阵内容（B24F1 落终版），本 feature 只保证快照与矩阵的一致性检查有挂载点」——本 feature **不建立完整矩阵**（全库补全与定稿仍归 B24F1），但**补本层 5 行**是宪法原则 X 的硬义务（B2F1 已就其 10 行立过同例），且使一致性检查得以**严格判定**而非「跳过 + 缺口名单」。

- **裁定 10（「唯一维护点」的归属 —— 2026-11-07 分析轮）**：文档间曾出现**互斥表述** ——
  FR-010 ④ 与 Key Entities 称**机器生成**的 `public-api-snapshot.txt` 是「门面导出面与
  调用签名的**唯一手工维护点**」，而 `contracts/facade-api.md` §0 称**手写**清单是
  「门面导出面的唯一手工维护点」。
  → **A：分工明确化** —— **导出面清单（哪些符号算公开）的唯一手写权威 =
  `contracts/facade-api.md` §0**；**调用签名的唯一入库 / 比对点 =
  `public-api-snapshot.txt`**（**机器生成**，非手写）。
  **理由**：与 research **D-07**（判定**非循环**：期望值必须来自独立于代码的手写清单）
  及 `contracts/snapshot-format.md` 的分工表（「清单管『哪些』、快照管『长什么样』」）一致；
  且用「手工维护点」称呼**生成物**本身是措辞错误。
  已落 **FR-010 ④** · Key Entities · `contracts/facade-api.md` §0。

- **裁定 11（`Send` 的可哈希性 —— 2026-11-07 分析轮）**：`Send` 的「**不可哈希**」此前
  只出现在 `data-model.md` §2.5 / research D-13 / `tasks.md` T027，**spec 的 FR-005 与
  SC-017 均未提及** ⇒ 一个**已进入冻结面**（会进快照）的公开行为缺 spec 依据
  （违反宪法原则 VI「tasks MUST 可追溯到 spec 条目」）。
  → **A：写进 spec** —— `Send` MUST **不可哈希**（显式 `__hash__ = None`）。
  **理由**：① 可哈希性是**用户可见行为**（能否放进 `set` / 作 `dict` 键）；② frozen dataclass
  默认**仍会**生成 `__hash__`，「不可哈希」**必须显式声明**（实测
  `Send.__dict__["__hash__"] is None` 才成立）；③ 与本仓库 `Node` / `Edge` / `Graph` /
  `Span` 的「统一不可哈希」纪律同构。
  已落 **FR-005 ①** · **SC-017** · `data-model.md` §2.5 · `tasks.md` T027。

- **裁定 12（导入开销预算入 spec —— 2026-11-07 分析轮）**：`< 120 ms` 的导入开销预算此前
  只活在 `plan.md` 的「Performance Goals」与 `tasks.md` T040，**spec 的成功标准里没有
  对应条目** ⇒ 判据无 spec 锚点。
  → **A：升格为 spec 判据** —— 新增 **FR-019**（预算 + **唯一计时口径**）与
  **SC-018**（隔离环境实测 + 记入人工验证记录第 3 节）。
  **理由**：可量化的 NFR 属成功标准的本职；「计时口径」必须**唯一**，否则「< 120 ms」会因
  「是否含解释器冷启动」而歧义（`plan.md` 的表述与 T040 的实测命令此前不一致，已一并对齐
  为「**以 `time.perf_counter()` 在 import 语句前后取差，不含解释器启动**」）。
  > **阈值收紧（2026-11-07 分析轮 · 第二轮）**：原阈值 `< 300 ms` 建立在**不可复现**的
  > 基线（154 ms）之上——按当前工作树实测，真实基线约 **50–63 ms**（暖机 best-of-3），
  > 300 ms 的阈值对 **3× 回归**仍然通过 ⇒ 阈值收紧为 **`< 120 ms`**（≈ 基线的 2 倍），
  > 并把**测量环境**（CPython 3.11.x · 暖机 best-of-3）写进 FR-019 的**唯一计时口径**。
  已落 **FR-019** · **SC-018** · 追溯表 · `plan.md` 的 Performance Goals · `tasks.md` T040
  · `research.md` D-19。

- **裁定 13（兼容矩阵扩容后 **既有门禁 G8** 的口径收敛 —— 2026-11-07 实现轮）**：
  实现 FR-012 ③（兼容矩阵 MUST 补入门面的 5 行）时暴露一处**判据冲突**——
  **既有**门禁 **G8**（B2F1 落）的**整表**判据是「矩阵首列符号集合 **==** 契约层的
  18 个符号」，而矩阵自本 feature 起**同时**承载**契约层 18 个**与**门面层 7 个**
  ⇒ 两条要求**互斥**（补 5 行 ⇒ G8 恒红）。
  → **A：G8 按其**声明范围**收敛，整表判据移交门面侧** —— 本 feature 的门禁契约
  （`contracts/architecture-gates.md` §3）早已声明「**G8 的范围 = 契约层 18 个符号**
  / **G19 的范围 = 门面 7 个符号**——**不重叠**」；既有实现之所以恒红，是因为它把
  「契约层」误实现成了「整张表」。⇒ G8 改为**按层**判定（「契约层 18 个**齐备**」
  +「无重复行」），**整表**的「无清单外符号」判据由 **G19** 承担。
  **理由**：① **规范文本不动**（FR-012 ③ 与 G8 的**声明范围**都成立）；
  ② **G8 针对契约层的任何一条判据都未被削弱**（「不多」与「不少」两条全留）；
  ③ **归属正确**——「整表完整性」本就属覆盖面更广的一方（门面侧 G19 同时判两层）。
  已落 `tests/contracts/test_architecture.py` 的 G8 判据 · `tests/facade/test_facade_gates.py`
  的 G19（新增「整表 == 契约层 18 个 ∪ 门面层 7 个」一条）· `tasks.md` T012 / T043 的注记
  · `harness/verification/B2F2/manual-verification.md` §5 遗留 #1。

- **Q1（导出面判定口径）**：门面的「导出面」按什么口径判定，才算「不多不少」？
  → **A：C（两处都断言）** —— 门面 MUST 定义 `__all__`（集合恰为那 7 个名字，沿用 B2F1
  门禁 G7 的既有口径），**且**门面模块内所有**不以下划线开头**的公开名 MUST 恰为这 7 个
  （AST 判据）。
  **理由**：单独用 `__all__` 有漏洞——有人写了 `from ._impl import helper` 却没把它加进
  `__all__`，`from freegraph.graph import helper` 照样能用，`__all__` 断言抓不到；
  两条都断言可堵死该漏洞，且与仓库既有口径兼容。已落 **FR-002** 与 **SC-003**。

- **Q2（未接线时抛什么异常）**：门面外壳里「尚未接线」的方法被调用时，应抛哪种异常？
  → **A（内置 `NotImplementedError`）** —— 语义直白「本功能尚未实现」，**零新增公开错误类型**、
  契约层 18 符号面完全不动；异常消息 MUST 点明「尚未接线」并指名归属 feature。
  **理由**：另两条路都有代价——新增 `FreegraphError` 子类会多出一个可被 import 的公开名，
  与 Q1-C 的「公开名恰 7 个」打架；复用 `GraphInterrupt` 会把「尚未实现」说成「运行期中断」。
  已落 **FR-009** / **SC-011** / Assumptions 与两条 Edge Cases。

- **Q3（签名快照要不要连类型注解一起冻）**：快照里要不要把参数和返回值的**类型注解**也冻住？
  → **A（全冻）** —— **参数注解 + 返回注解**都进快照（PEP 484 意义上的完整签名），
  注解按「**规范化文本**」记录（别名是否解析成展开形态由 plan 定，但 MUST 稳定、
  MUST NOT 因 Python 小版本差异抖动）。
  **理由**：注解是用户代码真正依赖的东西（`RunConfig | None` 被悄悄换成 `dict`，
  用户的 `isinstance` 判断就翻车）；本项目的验收契约本就是「同名同签名」，类型属于签名的一部分。
  B6F1 / B7F2 交付真实实现后想调类型也不是没门路——照样出 diff、走人工确认。
  已落 **FR-010** / **SC-005** / Assumptions。

- **Q4（合法变更时快照文件怎么更新）**：当签名确实需要做合法变更时，快照文件该怎么更新？
  → **A（提供显式的更新入口）** —— 系统 MUST 提供一个**显式的人工更新入口**
  （如 `pytest --update-api-snapshot` 标记或独立脚本；具体形态由 plan 定），该入口
  MUST **仅在被显式调用时**生效，MUST NOT 在常规测试执行中触发；更新后的快照 MUST 经
  **人工 review diff** 后方可提交。
  **理由**：既不藏漂移（默认跑测试绝不改文件），也不让人手抄格式；纯手工编辑在
  快照是「门面唯一权威」的前提下容易变成长期噪声。
  已落 **FR-011**（新增 ①）与 **SC-005**。

- **Q5（兼容矩阵 5 行的「等价程度」怎么填）**：README 兼容矩阵新补的 5 行，「等价程度」列
  该怎么填？ → **A（按当前实现状态如实标注）** ——
  `StateGraph` = **部分等价**（构建器行为待 B6F1 / B7F2 交付）·
  `START` / `END` = **行为等价**（值与语义均一致）·
  `Send` = **部分等价**（形状等价；**freegraph 侧不可变、上游可变**；行为待 B11F1）·
  `interrupt` = **部分等价**（形状等价，行为待 B10F1）。
  5 行的上游来源逐行写明：`langgraph/graph/state.py:131` / `langgraph/constants.py:30` /
  `langgraph/constants.py:28` / `langgraph/types.py:704` / `langgraph/types.py:851`
  （核实环境 `langgraph 1.2.11`）。
  **理由**：矩阵是「活文档」，如实标注能让读者一眼看出「哪些已完全等价、哪些还在路上、
  分别归哪个 feature 交付」；统一写「部分等价」会把已完全等价的 `START` / `END` 拉低，
  按终态标注则会让读者误以为能力现已可用。
  已落 **FR-012**（新增 ④）与 **SC-012**。

- **Q6（快照要不要记录公开属性 / property）**：快照除了方法与常量，**公开属性 /
  property** 要不要一并记录？ → **A（记录）** —— 快照 MUST 记录属性名、注解与
  **只读 / 可写**属性。
  **理由**：快照宣称「公开 API 形状不会悄悄漂移」，若只记方法 + 常量，B6F1 交付真实
  `StateGraph` 时新增的公开属性（如 `schema`）会**悄悄漂过**快照，与 Q3「全冻」的严口径
  自相矛盾。已落 **FR-010**（新增 ①）与 **SC-005**。

- **Q7（`Send` / `interrupt` 的参数能否用关键字传 · `Send` 是否可变）**：
  → **A（允许关键字传；`Send` 冻结为不可变）** —— `Send(node, arg)` 与 `interrupt(value)`
  的参数**位置或关键字皆可**（实测上游 `langgraph/types.py:704` / `:851` 同形，
  `Send(node='x', arg=1)` 合法）；`Send` MUST 为**不可变记录**。
  **理由**：逐字镜像上游的调用写法，减少 freechain 的适配成本；`Send` 取不可变则与本仓库
  「不可变记录」基调一致，避免「调度器已读到旧值、用户又改了载荷」的时序坑。
  上游 `Send` **可变**，该差异 MUST 写进兼容矩阵。已落 **FR-005** / **FR-012 ④** /
  **SC-017** / Assumptions。

- **Q8（三个 plan 级小项）**：① 快照文本的编码 / 换行；② 人工验证记录的格式；
  ③ 两个权威清单的关系 → **A（全部写死）** ——
  ① 快照文本 **UTF-8 / LF / 末行带换行**（避免跨平台 diff 噪声）；
  ② 人工验证记录采用仓库既有的**五段式**（环境 / 步骤 / 实际输出 / 结论 / 遗留问题），
  第 3 节 MUST 粘贴**真实输出**，未实跑的项 MUST 显式记入遗留问题（MUST NOT 伪造）；
  ③ B2F1 的 `public-api.md` §5 移交表 MUST **加一行**指向本快照——两个权威各管一面
  （18 个契约层符号 vs 7 个门面符号），MUST NOT 出现第二份自称门面的权威清单。
  已落 **FR-010**（新增 ②③④）与 **FR-015**。

- **Q9（门面的层归属 · ARCH-1 合规 · 2026-11-07 分析轮）**：门面的导出面横跨 **L1–L3**
  （`Command` / `RunConfig` 属 L1 契约层 · `Send` / `interrupt` 属 L2 执行内核层 ·
  `StateGraph` 属 L3 图定义层），而立项书 §5.2 原把 B2F2 归 **L1 契约层** ——
  按 ARCH-1「反向 import 视为违规」，B6F1 / B10F1 / B11F1 接线后**L1 门面必须 import L2/L3**。
  → **A：门面的「层」记为跨层单元（层 =「—」）**，作为 **ARCH-1 的唯一例外**
  （可 import L1–L3，仍**不得** import L4 持久化 / L5 可观测）；
  例外条款与 B2F2 行的层归属已由**发起者**修订于立项书 §5.1 / §5.2（2026-11-07）。
  **理由**：门面确实横跨多层，「跨层单元」是既有的分类口径（工程设施 / 发行与文档同类），
  而 ARCH-1 的例外只放宽**这一条**，不动「依赖永远向下」的整体纪律。
  已落 Key Entities · `contracts/facade-api.md` 的层归属块 · `plan.md` 的「架构纪律核对」小节。

- **Q10（参数名的冻结口径 · 2026-11-07 分析轮）**：冻结的参数名以**宪法原则 III 第 2–5 项**
  为准（`schema` / `name` / `fn` / `src` / `dst` / `path_fn` / `path_map`），
  还是以立项书 §4.3「freegraph 义务」列引用的**上游**名（`node` / `action` / `start_key` /
  `end_key` / `source` / `path`）为准？
  → **A：维持宪法口径** —— 立项书义务列描述的是**上游形状**，与宪法**不冲突**；
  差异登记在兼容矩阵的 `StateGraph` 行。
  **理由**：宪法优先（且 `target.py` 用**位置调用**，参数名不影响脚本跑通）；
  与 freegraph 自身的 `Node.id` 术语也更一致。已落 **裁定 4** 的补充说明与
  `contracts/facade-api.md` §2 的「参数名的冻结口径」块。

- **Q11（署名头门禁的覆盖缺口 · 2026-11-07 分析轮）**：既有 **G5** 的扫描清单
  `SIGNED_SOURCE_FILES`（`tests/contracts/test_architecture.py:112`）是**硬编码元组**
  ⇒ 本 feature 新建的源文件**不在**其中 ⇒ FR-017 无自动判据；而补它**必须改**既有门禁文件。
  → **A：在门面侧另立一条门禁 G20**（逐文件断言本 feature 新建文件的署名头），
  **不**改既有 `tests/contracts/**`（保住「既有门禁实现零改动」的纪律）。
  **代价（已知取舍）**：署名头判据从此分两处维护（契约层侧 + 门面侧）。
  已落 **FR-010 ⑤** 与 `contracts/architecture-gates.md` **G20**。

- **Q12（快照测试「在 CI 中」的措辞 · 2026-11-07 分析轮）**：spec 的 SC-005 写「**常驻**（随
  全量测试执行）」、Out of Scope 写「CI 门禁归 B3F1」，口径本已一致；只有 **User Story 2 的
  叙述句**写成了「在 CI 里显式可见」。
  → **A：叙述句改为「在**测试**里显式可见（CI 流水线的挂载归 B3F1）」** —— 只改措辞，
  **不动**任何判据（SC-005 / FR-010 / FR-011 的要求一字未改）。已落 User Story 2。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 验收基准脚本的 import 在第一个可运行的 feature 即成立 (Priority: P1)

作为项目发起者，我希望能**现在**就执行 `from freegraph.graph import StateGraph, START, END`
并得到退出码 0——哪怕 `StateGraph` 此刻还只是没有接上运行时的外壳——以便把「导出面写错」
这类低级错误提前到 M0 暴露，而不是等到 M1/M2 全部实现完才发现。

**Why this priority**: 这是**验收契约第 1 项**（宪法原则 III 第 1 条）的落点，也是
`harness/demo/target.py:122` 这行**只读基准**能开始跑的前提。导出面写错 ⇒ 基准脚本
在第一行就断 ⇒ 后面所有工作都建立在一个从未被验证的地基上。

**Independent Test**: 在隔离环境执行该 import，退出码 0（不依赖任何第三方包）。

**Acceptance Scenarios**:

1. **Given** 一个只装了 freegraph 基础包的环境（零第三方依赖），**When** 执行 `from freegraph.graph import StateGraph, START, END`，**Then** 退出码 0，且 `StateGraph` / `START` / `END` 三个名字均可取到。
2. **Given** 同一环境，**When** 执行 `import freegraph.graph` 后检查已加载的模块，**Then** 其中**不含**任何持久化层与可观测层子模块（门面不得横向依赖 L4 / L5）。
3. **Given** 同一环境，**When** 执行 `harness/demo/graph_core.py`，**Then** 脚本**不因 ImportError 以退出码 2 结束**（用例本身尚未转绿是预期的——本 feature 只保证导入段成立）。
4. **Given** 一个从未安装过 LangChain 家族任一包的环境，**When** 导入门面并取用全部 7 个符号，**Then** 全程成功，依赖闭包为空集。

---

### User Story 2 - 公开 API 的形状不会悄悄漂移 (Priority: P2)

作为维护者，我希望能有一份**入库的签名快照**，把门面的导出符号名与**完整调用签名**
（参数名、默认值、关键字-only 标记）钉死；任何改动都在**测试**里**显式可见**（diff 呈现、
需人工确认；**CI 流水线的挂载归 B3F1**）——以便避免「实现悄悄改了签名，用户代码半夜崩掉」。

**Why this priority**: 本功能块（B2）的名字就是「公开 API 门面与**签名冻结**」。冻结
若没有**可执行的判据**就只是一句口号；快照测试是这条口号唯一能被机器执行的形式。

**Independent Test**: 改动门面中任一函数的**参数名**，快照比对测试**失败**且输出
**可读的差异**（diff 行数 ≥ 1）。

**Acceptance Scenarios**:

1. **Given** 已入库的快照与当前门面，**When** 跑快照比对，**Then** 逐字节一致 ⇒ 测试通过。
2. **Given** 门面上某个方法的参数被改名，**When** 跑快照比对，**Then** 测试失败，且输出**指明差异所在**的文本。
3. **Given** 同一份代码，**When** 连续两次生成快照，**Then** 两次结果**逐字节相同**（快照可复现，不含时间戳 / 地址 / 哈希序）。
4. **Given** 有人往门面上**多加一个导出符号**，**When** 跑导出面断言，**Then** 测试失败（集合相等断言，多一个也失败）。

---

### User Story 3 - 上层开发者有单一可信入口 (Priority: P3)

作为 freechain 开发者，我希望能从**一个模块**取到全部需要的符号
（`StateGraph` / `START` / `END` / `Command` / `Send` / `interrupt` / `RunConfig`），
而不必在多个模块间拼凑、也不必知道内部包结构——以便未来 freechain 面向用户的 API
与 freegraph **共用同一入口**，不出现第二套入口。

**Why this priority**: 门面是**架构纪律 ARCH-4**（公开 API 面只经由 L1 导出）的唯一
落点；门面一旦有两个，freechain 就必须挑一个（或两个都支持）——那是长期技术债。

**Independent Test**: 门面导出的符号清单与本 spec 的导出面表格**逐项一致**（集合相等，
不多不少），且每个符号都能**一次性**取到。

**Acceptance Scenarios**:

1. **Given** 门面的导出面，**When** 与本 spec 的导出面表比对，**Then** 集合相等（多一个 / 少一个都失败）。
2. **Given** 一个上层模块，**When** 只 `from freegraph.graph import ...`，**Then** 全部所需符号**一次取齐**，无须再 import 内部包。
3. **Given** `Command` / `RunConfig` 两个契约层类型，**When** 从门面取用，**Then** 取到的**就是契约层那个对象**（同一对象，非副本、非子类）。
4. **Given** 需要 `draw_mermaid` 的用户，**When** 查阅门面导出面，**Then** 该能力**不在**门面导出面内（属 `Graph` 对象，B22F1 / B23F1），文档无误导。

---

### User Story 4 - 顶层包保持惰性，契约层仍可被单独消费 (Priority: P4)

作为 freechain（只想要契约层）的开发者，我希望能 `import freegraph.contracts` 而
**不**连带加载门面 / 图定义层 / 运行时 / 持久化 / 可观测层——以便跨仓库分层真正成立
（freechain 只依赖契约，不依赖 freegraph 的内部实现）。

**Why this priority**: 这是 **D1 决议（2026-11-04）的附加约束**（ARCH-2 的可判定项）。
顶层包一旦为了「方便」拖进门面，`import freegraph.contracts` 就会连带加载
L3 → L2，契约层「可独立消费」的收益随之**失效**——D1 决议第 ④ 条的收益即告作废。

**Independent Test**: 子进程执行 `import freegraph` 后检查 `sys.modules`，其中**不含**
`freegraph.graph` / `freegraph.contracts` / 任何运行时 / 持久化 / 可观测子模块。

**Acceptance Scenarios**:

1. **Given** 一个干净解释器，**When** 执行 `import freegraph` 后取 `sys.modules` 快照，**Then** 其中 `freegraph.*` 的子模块数为 0（只有 `freegraph` 本身）。
2. **Given** 同一环境，**When** 执行 `from freegraph.graph import StateGraph`，**Then** 成功，且 `freegraph.contracts` 被加载（门面**可以**依赖 L1 契约层）。
3. **Given** 有人往 `freegraph/__init__.py` 里加 `from .graph import ...`，**When** 跑惰性断言，**Then** 断言失败并点名该文件。
4. **Given** 同一环境，**When** 执行 `import freegraph.contracts`，**Then** 契约层可被**单独消费**（不连带加载门面 / 运行时 / 持久化 / 可观测）。

---

### Edge Cases

- **门面只有「导出」没有「实现」**：门面 MUST NOT 定义类体 / 函数体（裁定 3）。若有人为了
  「方便」把 `StateGraph` 直接写进门面文件，AST 断言 MUST 报出**行号**。
- **`StateGraph` 此刻是「可构造但未接线」**：构造 MUST 成功；`add_node` / `add_edge` /
  `add_conditional_edges` / `compile` MUST 抛**内置 `NotImplementedError`**（Q2 裁定），
  MUST NOT 静默返回
  `None` 或空对象——静默成功会让用户的图「看起来建好了」却永不执行，比报错更坏。
- **`StateGraph` 多传一个位置参数**：MUST 失败（`TypeError`）——构造函数**只**接受
  `schema` 一个位置参数（宪法原则 III 第 2 项）。
- **`add_node` 的第三个参数是位置传入**：冻结为 **keyword-only**（`alias=`）——传成位置参数
  MUST 失败，避免与上游 `add_node(node, action, *, defer=...)` 的参数序混用。
- **`path_map` 传 list 还是 dict**：两者**都**是合法形态（宪法原则 III 第 5 项）——本 feature
  只冻结**签名**（第三个参数名为 `path_map`），**取值校验**归 B8F1。
- **`compile()` 无参可调用**：MUST 支持零参数调用（宪法原则 III 第 6 项）——两个可选关键字
  都有缺省值。
- **`interrupt` 在没有运行上下文时被调用**：MUST 抛**内置 `NotImplementedError`**
  （B10F1 之前无运行期）；MUST NOT 抛 `NameError` / `AttributeError` 之类的**意外**异常。
- **`Send` 尚未接线时构造**：MUST 可构造成功（它是纯载荷型原语），但其**被运行时消费**的
  行为归 B11F1。
- **快照文本里出现内存地址 / 哈希序**：快照 MUST 可复现（裁定 8）——同一份代码两次生成
  MUST 逐字节相同，否则快照测试会**假红**（flaky）。
- **快照文件与门面导出面不同步**：测试 MUST 失败并输出 diff；**MUST NOT** 提供「自动更新快照」
  的开关来掩盖差异——更新必须走**人工确认**（这正是 P2 的价值）。
- **有人往门面上多加一个导出符号**：导出面集合相等断言 MUST 失败（多一个也失败）。
- **顶层包被「顺手」改成 re-export**：`freegraph/__init__.py` MUST NOT 导出门面；惰性断言
  MUST 在**子进程**里执行（测试进程自身已导入 pytest，同进程 `sys.modules` 不可用）。
- **门面误 import 持久化 / 可观测层**：MUST NOT 横向依赖 L4 / L5（ARCH-2）；`import freegraph.graph`
  之后的 `sys.modules` 快照 MUST 不含该两层子模块。
- **门面误读环境变量 / 发起出站**：MUST NOT（宪法原则 I / II / 依赖黑名单）——门面的零 I/O
  是「零账号 / 零出站」对外承诺的落点之一。
- **上游版本漂移**：本 spec 引用上游行号的环境为 **`langgraph 1.2.11` / `langchain-core 1.6.3`**
  （实测）；引用时 MUST 标注版本，换版本后行号 MUST 重新核实（MUST NOT 凭记忆沿用）。
- **`graph_core.py` 的用例全红**：M0 阶段的**预期状态**（本 feature 只保证导入段成立）；
  MUST NOT 因此宣称验收脚本已跑通。
- **`harness/demo/target.py` 被「顺手」改了**：MUST NOT——它是**只读基准**（宪法原则 III），
  CI 断言其 diff 为空。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：系统 MUST 提供模块 **`freegraph/graph.py`**，作为 freegraph 的**唯一公开 API 门面**。
  用户 MUST NOT 需要（也 MUST NOT 被引导）从 `freegraph.contracts` 或任何内部模块直接取用
  面向用户的图构建能力。

- **FR-002**：门面 MUST 导出 **恰 7 个**符号，**不多不少**：
  `StateGraph` / `START` / `END` / `Command` / `Send` / `interrupt` / `RunConfig`。
  **判定口径（Q1 裁定 · 两处 MUST 同时成立）**：
  ① 门面 MUST 定义 `__all__`，其**集合恰为**上述 7 个名字（沿用 B2F1 门禁 G7 的既有口径）；
  ② 门面模块内**所有不以下划线开头的公开名** MUST **恰为**上述 7 个（AST 判据）——
  抓「导出了但没进 `__all__`」这条 `__all__` 单独断言抓不到的漏洞。
  `CompiledGraph` / `Graph` / `Node` / `Edge` / `Span` / `TraceQuery` MUST NOT 出现在门面导出面内
  （它们属契约层）；`draw_mermaid` / `draw_mermaid_png` MUST NOT 出现在门面导出面内
  （属 `Graph` 对象 · B22F1 / B23F1）。

- **FR-003**：`START` 的值 MUST 为 **`'__start__'`**，`END` 的值 MUST 为 **`'__end__'`**（C9）。
  两者 MUST 是**字符串常量**（非枚举成员、非自定义对象）。

- **FR-004**：`Command` / `RunConfig` MUST **原样转出**契约层的既有类型——门面取到的
  MUST **就是** `freegraph.contracts` 里的那一个对象（同一对象，非副本、非子类、非包装），
  且 MUST NOT 改动其字段清单（B1F1 已冻结的四字段 / 三个语义位**逐字不动**）。

- **FR-005**：`Send` / `interrupt` MUST 以**外壳**形式在本 feature 就位并由门面导出
  （裁定 2）：
  ① `Send` MUST 可构造（形状：两个参数 `node` 与 `arg`，**位置或关键字皆可**——逐字镜像
  上游 `langgraph/types.py:704`，实测上游 `Send(node='x', arg=1)` 合法）；
  `Send` MUST 为**不可变记录**（属性不可改）——与本仓库「不可变记录」基调一致，避免
  「调度器已读到旧值、用户又改了载荷」的时序坑；**上游 `Send` 是可变的**，该差异 MUST
  写进兼容矩阵的「差异说明」列（FR-012 ④）。
  `Send` MUST **不可哈希**（显式 `__hash__ = None`）——**注意**：`frozen=True` 的 dataclass
  默认**仍会**生成 `__hash__`，「不可哈希」必须**显式声明**（实测：`Send.__dict__["__hash__"]
  is None` 才成立）；此口径与本仓库 `Node` / `Edge` / `Graph` / `Span` 的
  「统一不可哈希」纪律同构（research D-13）。
  `Send` **被运行时消费**的行为归 **B11F1**；
  ② `interrupt` MUST 可调用（形状：一个参数 `value`，**位置或关键字皆可**——上游
  `langgraph/types.py:851` 同形），但在无运行上下文时 MUST 抛
  **内置 `NotImplementedError`**（Q2 裁定；不抛意外异常），其**中断 / 恢复**行为归 **B10F1**；
  ③ 二者 MUST NOT 进入**契约层**的公开符号面——`freegraph.contracts.__all__` MUST 仍
  **恰为 18 个**（B2F1 的 G7 恒成立）。

- **FR-006**：门面模块 MUST **零实现体**——**AST 判据**：门面模块内的 `class` / `def` /
  `async def` 语句数 **== 0**（仅允许 import、常量赋值、`__all__` 与文档字符串）。
  `StateGraph` / `Send` / `interrupt` 的实现体 MUST 位于**门面之外的下层模块**（裁定 3）；
  B6F1 / B10F1 / B11F1 MUST 在**同一门面导出名下**接线，**门面导出面 MUST NOT 因接线而改变**。

- **FR-007**：`StateGraph` 的**构造签名** MUST 冻结为 **`StateGraph(schema)`**——恰一个
  必填位置参数、参数名 `schema`（裁定 4）；构造 MUST 成功，MUST NOT 抛异常；
  多传一个位置参数 MUST 失败（`TypeError`）。
  构造后 MUST **不产生任何运行时副作用**（不读环境变量、不发起任何 I/O）。

- **FR-008**：`StateGraph` 的**公开方法签名** MUST 冻结为（宪法原则 III 第 3–6 项 +
  裁定 5 / 6）：
  | 方法 | 冻结签名 | 形态要点 |
  |---|---|---|
  | `add_node` | `add_node(name, fn, *, alias=None)` | 位置参数 `(str, Callable)`（宪法原则 III 第 3 项）+ 关键字 `alias`（C25 · B8F3） |
  | `add_edge` | `add_edge(src, dst)` | `(str \| list[str], str)`，返回注解 `Self`（链式语义 · 宪法原则 III 第 4 项） |
  | `add_conditional_edges` | `add_conditional_edges(src, path_fn, path_map)` | `path_map` **同时支持 list 与 dict** 两种形态（宪法原则 III 第 5 项） |
  | `compile` | `compile(*, checkpointer=None, store=None)` | **无参可调用** + 两个可选 keyword（C10 / C19 / C20） |
  三个构建方法的**返回注解 MUST 为 `Self`**（链式语义 · 裁定 5 / research D-12）；
  `alias` MUST 为 **keyword-only**。
  > **本 feature 的运行时口径**：链式语义是**签名面**的冻结（返回注解 = `Self`），
  > **不是**运行时行为——本 feature 尚未接线，四个方法按 **FR-009** 一律抛
  > `NotImplementedError`（本 feature **MUST NOT** 返回自身）。

- **FR-009**：**未接线**行为 MUST 显式失败——上述四个方法与 `interrupt` 在本 feature MUST 抛
  **内置 `NotImplementedError`**（Q2 裁定：语义直白「本功能尚未实现」，且**零新增公开错误类型**、
  契约层 18 符号面不动）；异常消息 MUST 点明「尚未接线」并指名归属 feature；
  MUST NOT 抛 `NameError` / `AttributeError` 之类的**意外**异常，MUST NOT 静默成功。
  本 feature MUST NOT 因此宣称 `harness/demo/target.py` 或 `graph_core.py` 的用例已跑通。

- **FR-010**：系统 MUST 提供 **API 快照**——把门面的导出符号名与**完整调用签名**
  （参数名、默认值、keyword-only 标记、**参数注解与返回注解的规范化文本**（Q3 裁定：全冻，
  PEP 484 意义上的完整签名）；常量含**字面值**；类含其**公开方法**与**公开属性 /
  property** 的签名与只读性）序列化为**稳定文本**并**入库**比对。
  ① **公开属性 / property MUST 进快照**——否则 B6F1 交付真实 `StateGraph` 时新增的任何
  公开属性都会**悄悄漂过**快照，与 Q3「全冻」的严口径自相矛盾；快照 MUST 记录
  属性名、注解与**只读 / 可写**属性。
  > **注**：`schema` 在本 feature **私有**（`self._schema` · research D-11）⇒ M0 快照**无**
  > `StateGraph` 的 `[attribute]` 条目；B4F1 只**收紧其注解**（`contracts/facade-api.md` §6-7），
  > **不**把它变成公开属性。
  ② 快照文本 MUST **可复现**：同一份代码连续两次生成 MUST **逐字节相同**（MUST NOT 含
  内存地址 / 哈希序 / 时间戳等非确定性内容）；排序 MUST 确定（符号名、类内方法名与
  属性名均按**字典序**）。
  ③ 快照文本的编码与换行 MUST 固定：**UTF-8 / LF / 末行带换行**（避免跨平台 diff 噪声）。
  ④ 快照文件落 **`specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`**
  （裁定 8），是门面**调用签名**的**唯一入库 / 比对点**（**机器生成**，非手写）；
  门面**导出面清单**（哪些符号算公开）的**唯一手写权威**是
  `contracts/facade-api.md` §0（**手写**清单，**非**本快照）——两者**各管一面、不重复**：
  清单管「**哪些**」，快照管「**长什么样**」（裁定 10 · research D-07 / D-06）。
  B2F1 的 `specs/b2f1-contracts-protocols/contracts/public-api.md` §5 移交表 MUST **加一行**
  指向本快照——两个权威各管一面（**18 个契约层符号** vs **7 个门面符号**），
  MUST NOT 出现第二份自称门面的权威清单（G12 的唯一权威纪律）。
  ⑤ **本 feature 新建的每一个源文件** MUST 携带**署名头**且 docstring 为首个语句——
  由门面侧的**门禁 G20** 覆盖（**刻意不**扩既有 G5 的硬编码清单 —— 那是
  `tests/contracts/test_architecture.py` 的既有实现，本 feature 不改它；
  理由与取舍见 `contracts/architecture-gates.md` G20）。

- **FR-011**：系统 MUST 提供**快照比对测试**——快照与当前门面的实际形状**逐字节比对**；
  不一致时 MUST 失败并输出**可读的差异**（diff）。
  MUST NOT 提供「静默自动更新快照」的路径——更新 MUST 经**人工确认**（P2 的核心价值）。
  ① 系统 MUST 提供**显式的更新入口**（如 `pytest --update-api-snapshot` 标记或独立脚本；
  具体形态由 plan 定）：该入口 MUST **仅在被显式调用时**生效，MUST NOT 在常规测试执行中
  触发；更新后的快照 MUST 经**人工 review diff** 后方可提交。
  ② 测试 MUST 含**自检用例**：故意改动某个参数名 ⇒ 断言该测试**确实失败**（只测「合规时通过」
  的门禁等于没测）。

- **FR-012**：API 快照 MUST 与**兼容矩阵**保持一致——
  ① 兼容矩阵的载体是 `README.md` 的「## API 兼容矩阵」章节（`COMPAT.md` 若届时存在亦适用）；
  ② 门面 7 个符号 MUST 在矩阵中**各恰有一行**（集合相等判定）；
  ③ 本 feature MUST 按 B2F1 的口径**补入本层新增的 5 行**（`StateGraph` / `START` / `END` /
  `Send` / `interrupt`），**矩阵保持 4 列不变**（既有 18 行**逐字不动**），「有上游同名符号者」
  MUST 在「差异说明」单元格末尾附**上游来源 `路径:行号`**（并标注核实版本），
  「无上游同名符号者」写「无上游对应（自由设计）」+ **契约条目号**；
  ④ 5 行的「**等价程度**」MUST 按**当前实现状态**如实标注（Q5 裁定）——
  `StateGraph` = **部分等价**（构建器行为待 B6F1 / B7F2 交付）·
  `START` / `END` = **行为等价**（值与语义均一致）·
  `Send` = **部分等价**（形状等价；**freegraph 侧不可变、上游可变**；行为待 B11F1）·
  `interrupt` = **部分等价**（形状等价，行为待 B10F1）；
  5 行的上游来源 MUST 分别为 `langgraph/graph/state.py:131`（`StateGraph`）/
  `langgraph/constants.py:30`（`START`）/ `langgraph/constants.py:28`（`END`）/
  `langgraph/types.py:704`（`Send`）/ `langgraph/types.py:851`（`interrupt`），
  核实环境 MUST 标注为 `langgraph 1.2.11`；
  ⑤ 全库矩阵的**补全与定稿**仍归 **B24F1**。

- **FR-013**：**顶层包 MUST 保持惰性**（D1 决议附加约束 · ARCH-2）——
  ① `freegraph/__init__.py` MUST **NOT** `from .graph import ...`（MUST NOT 以任何形式
  导入门面符号）；② `import freegraph` MUST NOT 连带加载 `freegraph.graph` /
  `freegraph.contracts` / 任何运行时 / 持久化 / 可观测子模块；③ 门面 MUST 由用户**显式**
  `from freegraph.graph import ...` 才加载。
  该断言 MUST 在**子进程**中执行（测试进程自身已导入 pytest，同进程 `sys.modules` 不可用）。

- **FR-014**：门面的依赖卫生 MUST 满足红线——
  ① MUST NOT import `langchain` / `langchain-core` / `langgraph*` / `langsmith`
  （门禁 **G17** 的第三方档另加禁 `pydantic` / `typing_extensions`——本 feature 的
  typing 构件上限 = 3.11，故二者**本不应出现**；此项是**判据的机械化收敛**，
  与「零第三方运行时依赖」的项目级约束同向）；
  ② MUST NOT 读取**任何**环境变量（`os.environ` / `os.getenv` 等）；
  ③ MUST **零出站 / 零 I/O**（不写文件、不发网络、不起后台线程）；
  ④ MUST NOT **横向依赖 L4（持久化）/ L5（可观测）**——`import freegraph.graph` 之后的
  `sys.modules` 快照 MUST 不含该两层子模块。

- **FR-015**：**证据门禁**——导出面与调用形态的**每一条** MUST 能追溯到来源：
  宪法原则 III 的 7 项同名同签名清单 / 立项书 §4.3 的 18 项裁定 / `harness/demo/graph_core.py`
  的**具体行** / 上游 `路径:行号`（须标注核实版本）。
  > **仓库内消费者的证据链（2026-11-07 复核补入）**：导出面「恰 7 个」由 **5 个既有消费者**
  > 独立印证 —— `harness/demo/graph_core.py:48-56`（恰 7 个）·
  > `harness/demo/acceptance.py:51-58`（恰 7 个）· `harness/demo/agent_loop.py:33-39`（5 个 · 子集）·
  > `harness/demo/visualization.py:36-40`（3 个 · 子集）· `harness/demo/target.py:122`（3 个 · 子集）；
  > 取值由 `harness/demo/acceptance.py:195-205` 独立断言（`START` / `END`）。
  本 feature MUST 产出**人工验证记录**，落 **`harness/verification/B2F2/manual-verification.md`**，
  逐条核对 **A1–A3** 三项验收判据并给出结论（原则 V）；记录 MUST 采用仓库既有的
  **五段式**结构（环境 / 步骤 / 实际输出 / 结论 / 遗留问题，见 `harness/verification/README.md`），
  第 3 节 MUST 粘贴**真实输出**而非「符合预期」，未实跑的平台 / 版本 MUST 显式记入
  「遗留问题」（MUST NOT 伪造输出）。

- **FR-016**：**只读基准**——`harness/demo/target.py` MUST NOT 被修改（CI 断言其 diff 为空）；
  `harness/demo/graph_core.py` 本 feature **可**随实现演进，但 MUST NOT 削弱其断言口径。

- **FR-017**：本 feature 新建的**每一个源文件** MUST 携带**署名头**
  （`# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph`，
  且模块 docstring 为首个语句；宪法原则 X）；MUST **零新增第三方运行时依赖**
  ⇒ `THIRD_PARTY_NOTICES` **无需新增登记**；MUST 沿用 **Python ≥ 3.11** 基线与
  typing 构件上限（禁 3.12+ / 3.13+ 构件）。

- **FR-018**：本 feature **只交付门面与形状**——MUST NOT 实现构建能力
  （`add_node` / `add_edge` / `add_conditional_edges` 的行为归 **B6F1**）、MUST NOT 实现
  `compile()` 的**行为**（**B7F2**）、MUST NOT 实现 `invoke()` 的**行为**（**B7F3**）、
  MUST NOT 实现 `get_graph` / `draw_mermaid`（**B22F1**）与 `draw_mermaid_png`（**B23F1**）、
  MUST NOT 改动**契约层的 18 符号面**、MUST NOT 在 `freegraph/__init__.py` 里 re-export
  门面符号、**MUST NOT** 建立 `COMPAT.md` 的完整矩阵内容（终版归 **B24F1**）。

- **FR-019**：门面的**导入开销** MUST 保持在预算内——在**隔离环境**（裸 venv，仅装
  freegraph 基础包）中 `import freegraph.graph` 的**墙钟** MUST **< 120 ms**。
  **计时口径（唯一）**：
  ① 以 `time.perf_counter()` 在 import 语句**前后**取差，**不含解释器自身启动**；
  ② **暖机后**测量——同一 venv 内先跑一次预热 import，再取**三次**的**最小值**
  （排除首次 `.pyc` 落盘 / 磁盘冷启动噪声）；
  ③ **基准解释器 = CPython 3.11.x**（立项书 §3.5 的 CI 最低档 · typing 构件上限同档）；
  ④ **测量环境** MUST 记入人工验证记录第 1 节（OS / CPU / Python 版本）。
  **基线（实测 · CPython 3.12.3 · 暖机 best-of-3 · 2026-11-07）**：
  `import freegraph.contracts` = **50–63 ms** ⇒ 三个新增模块（门面 + 两个外壳，
  均为**零 I/O** 的纯定义模块）MUST NOT 把总耗时推过该预算。
  > **为何收紧到 120 ms**：原 `< 300 ms` 的阈值建立在一个**不可复现**的基线
  > （154 ms）之上——按当前工作树实测，真实基线约 50–63 ms ⇒ 300 ms 的阈值对
  > **3× 回归**仍然通过，判据形同虚设；120 ms ≈ 基线的 **2 倍**，既留足余量
  > （本 feature 新增三个零 I/O 模块），又能抓住实质回归（原则 VIII · 证据纪律）。

### 需求 ↔ 成功标准 追溯表

> **A1–A3 的定义**（= 立项书 §5.2 的 B2F2 小目标 + D1 决议附加约束）：
> **A1** `from freegraph.graph import StateGraph, START, END` 可用 ·
> **A2** 签名快照入库 ·
> **A3** 顶层包惰性（`import freegraph` 后的 `sys.modules` 检查）。

| FR | 主题 | 对应 SC | 主要判据 |
|---|---|---|---|
| FR-001 | 唯一公开入口 `freegraph/graph.py` | SC-001 / SC-003 | A1 |
| FR-002 | 导出面恰为 7 个符号 | SC-003 | A1 |
| FR-003 | `START` / `END` 的取值 | SC-002 | A1 |
| FR-004 | `Command` / `RunConfig` 原样转出 | SC-003 / SC-010 | A1 |
| FR-005 | `Send` / `interrupt` 外壳 + 契约层 18 符号面不变 | SC-003 / SC-009 / SC-010 / SC-015 / SC-017 | A1 |
| FR-006 | 门面零实现体（AST 判据） | SC-004 | A1 |
| FR-007 | `StateGraph(schema)` 构造签名冻结 | SC-010 | A1 |
| FR-008 | 四个公开方法的签名冻结 | SC-003 / SC-010 | A1 |
| FR-009 | 未接线显式失败 | SC-011 | A1 |
| FR-010 | API 快照（稳定 / 可复现 / 含注解与公开属性 / 入库） | SC-005 / SC-006 | A2 |
| FR-011 | 快照比对测试 + 自检用例 | SC-005 | A2 |
| FR-012 | 快照 ↔ 兼容矩阵一致性（补 5 行） | SC-012 | A2 |
| FR-013 | 顶层包惰性 | SC-007 | A3 |
| FR-014 | 门面依赖卫生（零 import / 零环境变量 / 零 I/O / 不横依赖 L4-L5） | SC-008 / SC-009 | A1 |
| FR-015 | 证据门禁 + 人工验证记录（五段式） | SC-013 | A1–A3 |
| FR-016 | 只读基准 `target.py` | SC-014 | — |
| FR-017 | 署名头 / 零新增依赖 / 3.11 基线 | SC-014 | — |
| FR-018 | 边界（只交付门面与形状） | SC-011 / SC-015 / SC-016 | — |
| FR-019 | 导入开销预算（< 120 ms） | SC-018 | — |

### Key Entities

- **公开 API 门面（`freegraph/graph.py`）**: freegraph 的**唯一**用户可见入口；
  **只做导出 + 形状声明**，**零实现体**（裁定 3）；对应架构纪律 **ARCH-4**；
  是未来 freechain 面向用户 API 的**同一入口**。
  **层归属 = 跨层单元（层 =「—」，2026-11-07 发起者裁定）**：门面的导出面横跨 **L1–L3**
  （`Command` / `RunConfig` 属 L1 契约层 · `Send` / `interrupt` 属 L2 执行内核层 ·
  `StateGraph` 属 L3 图定义层）⇒ 它是 **ARCH-1 的唯一例外**（可 import L1–L3，
  仍**不得** import L4 持久化 / L5 可观测），登记于立项书 §5.1 的 ARCH-1 条目与 §5.2 的 B2F2 行。
- **门面导出面（7 个符号）**: `StateGraph` / `START` / `END` / `Command` / `Send` /
  `interrupt` / `RunConfig` —— 集合相等断言（多 / 少都失败）；
  其中 `Command` / `RunConfig` 是**契约层既有类型**的原样转出，其余 5 个由门面新增。
- **构建器外壳（`StateGraph`）**: **可构造但功能未接线**的图构建器；
  构造签名与四个公开方法的签名**已冻结**，**行为**分别归 B6F1 / B7F2；
  未接线时 MUST 抛明确异常。
- **原语外壳（`Send` / `interrupt`）**: 控制原语的**类型面**（可构造 / 可调用但未接线）；
  行为分别归 B11F1 / B10F1；**不进**契约层的 18 符号面（裁定 2）。
- **API 签名快照（`contracts/public-api-snapshot.txt`）**: 门面**调用签名**的
  **唯一入库 / 比对点**（**机器生成** · 非手写）；变更 MUST 走人工确认。
  门面**导出面清单**的**唯一手写权威**是 `contracts/facade-api.md` §0（裁定 10）。
- **快照比对测试**: 把「实际门面形状」与「入库快照」逐字节比对的测试；
  不一致时输出 diff；MUST 含**自检用例**（故意改坏 ⇒ 确实失败）。
- **顶层包惰性契约**: `import freegraph` MUST NOT 连带加载任何子模块（D1 决议附加约束 ·
  ARCH-2 的可判定项）；断言 MUST 在**子进程**执行。
- **兼容矩阵行**: `README.md`「## API 兼容矩阵」章节中门面 7 符号各一行；
  本 feature 补入 5 行（`StateGraph` / `START` / `END` / `Send` / `interrupt`），
  保持 4 列；全库定稿归 **B24F1**。

### Out of Scope

- 不实现 `StateGraph` 的**构建能力**（`add_node` / `add_edge` / `add_conditional_edges` 的
  行为）——属 **B6F1**。
- 不实现 `compile()` 的**行为**（只冻结签名）——属 **B7F2**；不实现 `invoke()` 的**行为**
  ——属 **B7F3**。
- 不实现 `get_graph` / `draw_mermaid`——属 **B22F1**；不实现 `draw_mermaid_png`——
  属 **B23F1**。
- 不实现 `Send` 的动态 fan-out（**B11F1**）、`interrupt` 的中断 / 恢复（**B10F1**）、
  `Command` 的运行时语义（**B9F1**）、节点别名行为（**B8F3**）、`recursion_limit`（**B13F1**）。
- 不让 `harness/demo/target.py` / `graph_core.py` 的**用例**跑通——本 feature 只保证
  `graph_core.py` 的**导入段**成立（用例在 M1/M2 逐条转绿）。
- 不建立 `COMPAT.md` 的完整矩阵内容——终版归 **B24F1**；本 feature 只补本层 5 行。
- 不改动**契约层**的 18 符号面与任何已冻结字段 / 方法集（B1F1 / B2F1 的冻结面逐字不动）。
- 不在 `freegraph/__init__.py` 里 re-export 门面符号（**D1 已拍板，2026-11-04**）——
  门面只由 `from freegraph.graph import ...` 进入。
- 不把 API 快照检查挂进 CI 流水线——**CI 门禁归 B3F1**；本 feature 只交付 pytest 断言
  （沿用 B1F1 / B2F1 的既有移交口径）。
- 不新增任何第三方依赖（⇒ `THIRD_PARTY_NOTICES` 不变）；不引入 Pydantic 等可选依赖。
- 不自研图渲染 / 图片渲染（**B22F1 / B23F1**）；不做子图实现（C26 属 v2）。
- 不为 freechain 提供**第二套**入口——freechain 的用户 API MUST 复用同一门面（未来事项）。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：**A1** —— 在只装了 freegraph 基础包（**零第三方依赖**）的隔离环境中执行
  `from freegraph.graph import StateGraph, START, END`，**退出码 0**；
  `import freegraph.graph` 不触发任何出站、不读任何环境变量。
- **SC-002**：`START == '__start__'` 且 `END == '__end__'`（**逐字相等**，C9 取值被断言钉死）；
  两者均为 `str` 类型。
- **SC-003**：门面导出面与本 spec 的导出面表**集合相等**（**恰 7 个**；多一个 / 少一个
  / 换成别的都判失败），且**两处口径同时成立**：`__all__` 集合 == 期望集合
  **且**模块内公开名（不以下划线开头）集合 == 期望集合；其中 `Command` / `RunConfig`
  与 `freegraph.contracts` 中的同名对象**是同一对象**（`is` 判定）。
- **SC-004**：门面模块**零实现体**——AST 扫描断言门面模块内 `class` / `def` / `async def`
  语句数 **== 0**（违规时报出**行号**）。
- **SC-005**：**A2** —— 快照文件**已入库**（存在性断言）且快照比对测试**常驻**（随全量测试
  执行）；**故意把门面中任一方法的参数改名 ⇒ 该测试失败且输出 diff（差异行数 ≥ 1）**；
  **故意改动任一方法的参数注解或返回注解 ⇒ 同样触发失败并输出 diff**；
  **故意新增一个公开属性 / property ⇒ 同样触发失败并输出 diff**；
  故意多导出一个符号 ⇒ 导出面断言失败；
  **显式更新入口存在且默认不生效**——常规跑测试 MUST NOT 改动快照文件（内容逐字节不变）。
- **SC-006**：快照**可复现**——同一份代码连续两次生成的快照**逐字节相同**（差异字节数 == 0），
  且文本中**不含**内存地址 / 时间戳 / 哈希序等非确定性内容。
- **SC-007**：**A3** —— 子进程执行 `import freegraph` 后，`sys.modules` 中 `freegraph.*`
  的**子模块数 == 0**（只有 `freegraph` 本身；**不含** `freegraph.graph` /
  `freegraph.contracts` / 任何运行时 / 持久化 / 可观测子模块）。
- **SC-008**：子进程执行 `import freegraph.graph` 后，`sys.modules` 中**不含**持久化层与
  可观测层子模块（**== 0**）——门面不横向依赖 L4 / L5。
- **SC-009**：静态扫描断言门面模块中——`langchain*` / `langgraph*` / `langsmith` 的
  import 数 **== 0**、`os.environ` / `os.getenv` 等环境变量读取数 **== 0**、
  出站 / 文件 I/O 调用数 **== 0**。
- **SC-010**：`StateGraph(schema)` **可构造成功**（不抛异常）；**多传一个位置参数 ⇒
  `TypeError`**；四个公开方法的**签名**与本 spec FR-008 **逐项一致**（参数名、默认值、
  keyword-only 标记、**返回注解**——三个构建方法为 `Self`）。
- **SC-011**：未接线方法与 `interrupt` **抛 `NotImplementedError`**（异常类型逐字可判、
  消息点名未接线与归属 feature），**静默成功数 == 0**；`harness/demo/graph_core.py` 的
  **导入段成功**（脚本**不**以退出码 2「环境未就绪」结束）。
- **SC-012**：兼容矩阵中门面 7 个符号**各恰有一行**（集合相等）；本 feature 补入的 5 行
  齐全，且其「等价程度」逐符号与 FR-012 ④ 一致（`StateGraph` / `Send` / `interrupt` =
  部分等价；`START` / `END` = 行为等价）；**既有 18 行逐字未改**（行数与内容断言）；
  新增 5 行 MUST 含**上游来源 `路径:行号`**（写在「差异说明」单元格末尾）。
- **SC-013**：**人工验证记录**已产出（落 `harness/verification/B2F2/manual-verification.md`），
  逐条核对 **A1–A3** 三项验收判据并给出结论；导出面与调用形态的**每一条**都有来源标记
  （**无来源项数 == 0**）——该判据的**载体**：记录第 4 节 MUST 含一张
  「**导出面 7 符号 × 来源**」的**覆盖表**（每符号一行，来源列填 §FR-015 要求的出处），
  **未列出该表的符号数 == 0**。
- **SC-014**：本 feature 新建的源文件 **100%** 携带署名头（静态扫描可判定）；
  **零新增第三方运行时依赖**（`THIRD_PARTY_NOTICES` 行数不变）；`harness/demo/target.py`
  的 **diff 为空**（只读基准未被修改）。
- **SC-015**：契约层的公开符号面**未受影响**——`freegraph.contracts.__all__` **仍恰为 18 个**
  （B2F1 的 G7 恒成立），且**不含** `Send` / `interrupt`（裁定 2）。
- **SC-016**：本 feature **未越界**——`StateGraph` 的四个方法**无任何业务实现**
  （不产生节点 / 边 / 编译产物的真实语义），`compile()` 不返回可执行产物，
  `invoke` 不存在于门面导出面内。
- **SC-017**：`Send` **可构造且不可变**（改其属性即失败）；**且 MUST 不可哈希**
  （`hash(Send(...))` 抛 `TypeError`）；`Send(node=..., arg=...)` 与
  `interrupt(value=...)` 的**关键字形态合法**（与上游同形）；二者均为**导出面成员**
  （计入 SC-003 的 7 个符号）。
- **SC-018**：**导入开销预算**（FR-019）——在**隔离环境**（裸 venv，仅装 freegraph 基础包）
  中按 FR-019 的**唯一计时口径**（暖机 · best-of-3 · 基准 CPython 3.11.x）实测
  `import freegraph.graph` 的墙钟 **< 120 ms**；**基线值**（`import freegraph.contracts`）
  MUST 一并实测并记入 `harness/verification/B2F2/manual-verification.md` 第 3 节
  （含测量环境：OS / CPU / Python 版本）。

## Assumptions

- **门面与外壳的模块落位**：门面 = `src/freegraph/graph.py`；`StateGraph` / `Send` /
  `interrupt` 的外壳 MUST 位于 `src/freegraph/` 下**不属契约层**的模块
  （`freegraph/contracts/` 的 18 符号面 MUST NOT 变），由 B6F1 / B10F1 / B11F1 在
  **同一门面导出名下**接线。具体模块名由 plan 决定（spec 只约束「不在门面内」与
  「不在契约层内」两条）。
- **契约层 18 符号面不变**：`Send` / `interrupt` 只进**门面**，不进 `freegraph.contracts`
  （裁定 2）；B2F1 的 G7（集合相等 == 18）在本 feature 后**仍恒成立**。
- **`Send` / `interrupt` 的最小形状**：`Send(node, arg)`（两个参数，**位置或关键字皆可**、
  **不可变记录**——与上游的「可变」差异记入兼容矩阵）· `interrupt(value)`（一个参数，
  位置或关键字皆可，返回恢复值 `Any`）。二者**不含**上游的多余可选参数
  （上游 `Send` 另有 `timeout=` 关键字、`interrupt` 无额外参数）。
- **`StateGraph` 外壳的最小形状**：仅「构造 + 四个已冻结签名的方法」；MUST NOT 在本 feature
  追加任何**未在 §7 调用形态表内**的公开方法（否则快照会把未经裁定的形状钉死）。
- **`alias` 为 keyword-only**：冻结为 `add_node(name, fn, *, alias=None)`；传成位置参数 MUST
  失败（避免与上游 `add_node(node, action, *, defer=...)` 的参数序混用）。
- **`interrupt` 的异常类型**：本 feature 的未接线调用 MUST 抛**内置 `NotImplementedError`**
  （Q2 裁定）——语义直白、**不新增任何公开错误类型**、契约层 18 符号面不动；
  `freegraph` 的错误体系（`FreegraphError` 及其三个子类）**保持原样**，本 feature 不新增成员。
- **`invoke` / `recursion_limit` 的形态**：属**编译产物**协议（B2F1 已冻结）与**运行时行为**
  （B7F3 / B13F1），**不进**本 feature 的快照（裁定 7）；门面**不导出** `CompiledGraph`。
- **上游来源的核实环境**：`langgraph 1.2.11` / `langchain-core 1.6.3`（本机实测）；
  行号以该版本为准，引用时 MUST 标注版本，换版本后 MUST 重新核实（MUST NOT 凭记忆沿用）。
  本 spec 引用的上游位置：`langgraph/constants.py:28`（`END`）/ `:30`（`START`）·
  `langgraph/types.py:704`（`Send`）/ `:851`（`interrupt`）·
  `langgraph/graph/state.py:131`（`StateGraph`）/ `:216`（`__init__`）/ `:667`（`add_node`）/
  `:928`（`add_edge`）/ `:982`（`add_conditional_edges`）/ `:1177`（`compile`）。
- **快照的生成方式**：生成器在**测试侧**、快照文件**入库**（裁定 8）；**导出面清单**
  （哪些符号算公开）的**唯一手写权威** = `contracts/facade-api.md` §0；**调用签名**的
  **唯一入库 / 比对点** = **机器生成**的 `contracts/public-api-snapshot.txt`——
  两者**各管一面、不重复**（裁定 10），spec / plan / tasks / README 中的同款清单
  均以 `contracts/facade-api.md` §0 为准。
  快照记录**参数注解与返回注解的规范化文本**（Q3 裁定）；「规范化」的具体口径（如类型别名
  是否解析成其展开形态）由 plan 定，但 MUST **稳定**——同一份代码两次生成 MUST 逐字节相同，
  且 MUST NOT 因 Python 小版本差异而产生抖动。
- **兼容矩阵的载体**：当前是 `README.md` 的「## API 兼容矩阵」章节（`COMPAT.md` 未创建，
  终版归 B24F1）；既有 18 行**逐字不动**，本 feature 只**追加** 5 行。
- **顶层包惰性的现状**：`freegraph/__init__.py` 当前只导出 `__version__`（B1F1 已就位），
  本 feature **不改**它，只**加断言**（防「顺手 re-export」）。
- **CI 挂载归 B3F1**：本 feature 只交付 pytest 断言（沿用 B1F1 / B2F1 的移交口径），
  **不改** `.github/workflows/`。
- **freechain 的门面复用属未来事项**：本 feature 只保证「门面是唯一入口」这一事实，
  不实现 freechain 侧的任何适配。
- **最小 Python 版本 3.11 / 零第三方依赖**：沿用 B1F1 结论；本 feature MUST NOT 引入
  任何第三方运行时依赖，⇒ `THIRD_PARTY_NOTICES` 不变。

## 依据

- 立项书 §4.3（18 项 API 裁定 · 7 项 MUST 同名同签名）、§5.1（**ARCH-2** 含顶层包惰性 /
  **ARCH-4** 公开 API 只经由 L1 导出 / L1–L6 分层）、§5.2（B2F2 行）、
  §9.1（质量门禁第 3 项：固定脚本 diff 断言）、§12（**D1 决议**，2026-11-04：v1 同包子模块
  + 顶层包惰性约束）。
- 宪法 `.specify/memory/constitution.md`：**原则 III**（验收契约优先 · 7 项同名同签名清单：
  `freegraph.graph` 导出 `StateGraph` / `START` / `END`（`START='__start__'`、`END='__end__'`）/
  `StateGraph(schema)` / `add_node(name, fn)` / `add_edge(src, dst)` 链式返回 /
  `add_conditional_edges(src, path_fn, path_map)` / `compile()`）、
  **原则 I**（零环境变量 · 零出站）、**原则 II**（零 LangChain 依赖）、
  **原则 V**（人工验收是最终验收标准）、**原则 VIII**（证据与术语纪律）、
  **原则 IX**（依赖许可证与商标红线）、**原则 X**（兼容矩阵 + 署名头 + `THIRD_PARTY_NOTICES`）。
- 验收脚本：`harness/demo/graph_core.py:48-56`（门面导出面 **7 个名字**的锁定点）、
  `harness/demo/target.py:122`（`from freegraph.graph import StateGraph, START, END` · 只读基准）。
- 前置 feature 规格：`specs/b1f1-contracts-core/spec.md`（四个核心类型 · 异常体系 · 依赖纪律）、
  `specs/b2f1-contracts-protocols/spec.md` 与 `contracts/public-api.md`（**契约层 18 符号面**
  · C1–C27 冻结对照表 · 门禁 G1–G13）与 `contracts/architecture-gates.md`（G1 顶层包惰性 ·
  G2 零内部 import · G4 零环境变量 · G5 署名头 · G7 公开符号面恰为 18 · G8 兼容矩阵 ·
  G12 公开符号面唯一权威）。
- 上游同名能力对照（证据 · 核实环境 `langgraph 1.2.11`）：
  `langgraph/constants.py:28`（`END = "__end__"`）/ `:30`（`START = "__start__"`）·
  `langgraph/types.py:704`（`class Send`）/ `:851`（`def interrupt(value: Any) -> Any`）·
  `langgraph/graph/state.py:131`（`class StateGraph`）/ `:216`（`__init__`）/
  `:667`（`add_node` → `Self`）/ `:928`（`add_edge` → `Self`）/
  `:982`（`add_conditional_edges` → `Self`）/ `:1177`（`compile`）。
- 本 feature 提示词初稿：`harness/features/B2F2_公开API门面与快照测试.md`。
