# Feature Specification: B10F1 · `interrupt()` + `resume`（HITL 中断与恢复闭环）

**Feature Branch**: `b10f1-interrupt-resume`

**Created**: 2026-11-13（初版）

**Status**: Draft

**Input**: User description: "B10F1 · `interrupt()` + `resume`（HITL 中断与恢复闭环）—— 交付**人工介入（HITL）的中断与恢复闭环**：节点在运行中调用 `interrupt(value)` 请求外部输入 → 图挂起并把中断信息交还调用方 → 调用方用 `Command(resume=...)` 提交输入 → **图从该节点的起点重跑**，节点在第二次执行时拿到 resume 值并继续跑完。恢复**必须**经由 checkpointer（快照 + pending writes）读取被中断处的状态；**MUST NOT** 提供「不挂 checkpointer 也能恢复」的内存态旁路；未挂 checkpointer 时调用恢复**必须**抛明确异常。"

---

## 0. 第一性目标与口径来源

> **上游 `langgraph` 1.2.11 是唯一权威**（宪法 **v1.9.0 原则 XI「上游优先」**）⇒ 本 spec 以
> 「**与上游行为面逐条同款**」为**缺省口径** ⇒ **只在失败信号上**允许 freegraph **更严**，
> 且 MUST **如实标注「比上游更严」并写明理由**。
> ⇒ 凡未显式标注「刻意分叉」者，一律 MUST **照抄上游**。

| 项 | 值 | 依据 |
|---|---|---|
| **feature ID** | `B10F1` | `harness/features/B10F1_interrupt与resume.md` 抬头 |
| **所属功能块** | B10（`interrupt` + `resume`） | 同上 |
| **架构层** | **L2 执行内核层**（`src/freegraph/runtime/**`）· 中断原语的**运行期机制**落 `src/freegraph/runtime/_interrupt.py`（**L2 目录条目内**）· 门面 `src/freegraph/graph.py` **模块级**转出该实现（**ARCH-1 的唯一例外** `facade-L1-L3`）⇒ ⚠️ **`src/freegraph/_primitives.py`（L2 单文件条目）MUST NOT import `runtime/`** —— 那是**跨注册表条目的同层 import** ⇒ **门禁 G25 判红**（实测）⇒ 见 **PR-4** | 提示词 §抬头 · 宪法 ARCH-1 · 层注册表 §1 · 门禁 G25 |
| **里程碑** | **M1 运行时内核**（第 11 个） | `harness/features/README.md` 开发顺序 |
| **前置依赖** | **B9F1**（`Command` 原语 · 已冻结） | 提示词 §抬头 |
| **规模（立项书口径）** | **2,945 行**（实现 1,091 / 测试 1,854 · ⚠️ **PR-10 的实施期实测口径** · 发起者 **2026-11-14** 已追认 · 立项书 §5.2 **已同步**）· 3 人日 ⇒ ⇒ ⚠️ **原口径 1,160 行**（实现 520 / 测试 640）· 3 人日 ⇒ ⇒ ⚠️ **PR-6 登记 +40 行**（分析轮补齐 4 条判据级覆盖缺口 + 1 条会话连续语义）⇒ ⇒ ⚠️ **PR-7 再登记 +60 行**（分析轮补齐 **3 条**测试级覆盖缺口：SC-008「真异常优先」· FR-013 末行「会话连续」的**测试** · SC-019 的 G29 三条判定逐条核对）⇒ ⇒ **实施口径 = 1,260 行**（实现 520 / 测试 740）· ✅ **发起者已确认**（**2026-11-13 分析轮** · 并入 V-1 的那一次追认 ⇒ **追认次数仍为 1 次**）⇒ ⇒ ✅ **立项书 §5.2 已同步**（2026-11-13 分析轮 · **发起者授权本轮回修代为同步** ⇒ B10F1 行 1,160 → **1,260** · 合计 31,220 → **31,320** 行） | 提示词 §抬头 · `tasks.md` §行数预算表 |
| **契约** | **C17**（中断原语 · Q8 §3.4 / §3.4.1 ④）· **C16**（`Command`）· **C19**（检查点接口）· **C4 / C6 / C8**（不得破坏 · ⚠️ **2026-11-13 分析轮回修**：初版误写 **C5**（节点函数签名）⇒ ⇒ 与 SC-019 / 提示词初稿 §9 的「C4 / C6 / C8」对齐 ⇒ ⇒ **C4** = 稀疏状态读） | `harness/reports/Q8-图运行时最小契约.md:259` · `:258` · `:261` |
| **上游版本（钉住）** | `langgraph` **1.2.11**（取证于 **2026-11-13** · 本仓库 `.venv` 内安装） | `.venv/lib/python3.11/site-packages/langgraph/` |
| **上游取证命令** | `.venv/bin/python` + `langgraph.checkpoint.memory.InMemorySaver`（**仅开发期** · 不进发行面） | 宪法「依赖白名单」：上游只作**差分测试侧**依赖 |
| **门禁约束（G25 · 导入图）** | 门面 → L2 的**唯一合法路径** = `src/freegraph/graph.py` 的**模块级** `ImportFrom`（`facade-L1-L3` 例外）⇒ ⇒ **L2 内部**（`runtime/` 内）互相 import = **同一注册表条目** ⇒ 合法 ⇒ ⇒ 但 `_primitives.py`（L2 **单文件条目**）↔ `runtime/`（L2 **目录条目**）**互相 import = 跨条目同层 = 违规** ⇒ ⇒ **MUST NOT**（**实测**：两种方向都判红） | 层注册表 §0.2 规则 3「模块定位口径」· §1 条目表 · 门禁 G25 · **PR-4** |

⚠️ **零出站 / 零环境变量 / 零第三方运行时依赖**（宪法原则 I / II · 依赖白名单）：
本 feature 的**生产代码** MUST NOT import `langchain` / `langchain-core` / `langgraph*` /
`langsmith` / `xxhash` / 任何第三方包 ⇒ MUST NOT 读任何环境变量 ⇒ MUST NOT 有任何出站。

⚠️ **宪法 v1.11.0 的两条补强与本 spec 的关系**（2026-11-13 分析轮）：① **原则 VI 的「判据级可追溯性」**
⇒ ⇒ 本 spec 的 **SC-008**（真异常优先）与 **FR-013 末行**（会话连续）曾只挂**实现**任务 ⇒ ⇒ ⇒
**判据不可测** ⇒ ⇒ ⇒ 已由 `tasks.md` 的 **T056 / T057** 补成**测试任务** ⇒ ⇒ ② **「破冻结面的三条」
① 的「冻结断言清单 MUST 实测化」** ⇒ ⇒ 本 spec §5 的清单已按**实测**由 **3 处**扩容为 **6 处**
（**PR-8**）⇒ ⇒ ⇒ **本 spec 的判据零放宽**（宪法原则 I–XII 与质量门禁的判据**一字未改**）。

⚠️ **上游锚点纪律**（原则 XI）：本 spec 的每条「上游行为」断言 MUST 带 **版本 + `路径:行号`**；
**行为**断言 MUST 有**实测**支撑 ⇒ 本 spec 的实测证据编号为 **E-1…E-26**（见 §Upstream Parity）。

---

## 承接条款（上游 feature → 本 feature）

> **宪法 v1.8.0「跨 feature 承接的接线通则」**：某个 feature 的规格中出现了**指名下一棒
> feature（ID + 里程碑）**的跨 feature 义务时，该条款 MUST 写入目标 feature 的提示词初稿
> ⇒ 由目标 feature 的 spec 落成 **FR + 裁定** ⇒ 其 tasks 与契约同步接线。
> **只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽任何门禁判据。**

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B9F1 → B10F1** | **M1** | **`Command` 的两条路径的边界**：`Command` 作为**图的输入**（`invoke(Command(resume=...))`）**不属** B9F1 ⇒ 归 **B7F3 / B10F1**；B9F1 只交付**节点返回值**那条路径（`resume` 位**本轮只被接受**：不抛错 · 不写入 · 不跳转）⇒ 本 feature MUST 在此基础上实现**恢复闭环**，且 MUST **NOT** 改写 B9F1 的 `goto` / `update` 语义；⚠️ L1 的 `NodeFunc` 虽允许 `None`（= 不写状态 · 忠实镜像上游）而 B7F1 的运行时仍拒绝 `None`（**既有偏差** · 已登记为遗留）⇒ 本 feature 的 `resume` 语义**不受**该偏差影响 | `specs/b9f1-command-primitive/spec.md` **裁定 7 / 21** · **引文差异 ⑩** · **FR-011 / SC-012** · `harness/features/B10F1_interrupt与resume.md` §2.1 | **FR-003** · **FR-013** · **FR-016** · 裁定 4 / 10 · SC-002 / SC-011 |
| **H-2** | **B12F1 → B10F1** | **M1** | **中断的承载形态与结果键接线**：① **载荷形态** —— B12F1 **合并抛出**一个 `GraphInterrupt`，其**载荷 = 元组**（`tuple[Interrupt, ...]` · **上游同款**）⇒ ⇒ 本 feature 的 `__interrupt__` 键 MUST 承载**该元组** ⇒ MUST **NOT** 另写一条收集路径；② **落点** —— ⚠️ B12F1 **中断轮 MUST NOT 产出 `SuperStepResult`**（四字段一个都不给）⇒ ⇒ **本 feature MUST 负责把接住的这个异常转成结果键**（接住 → 读 `exc.args[0]`（那个元组）→ 放进 `__interrupt__`）⇒ MUST **NOT** 要求 B12F1 预先产出带 `__interrupt__` 的结果对象；③ **`steps` 的载体** —— 中断轮不产出结果对象 ⇒ 挂起时 `steps` 口径（「**如实计**『实际跑过的轮数』」· B12F1 裁定 24）的**载体落在本 feature 产出的结果对象上**；④ **`.id` 的生成** —— `.id` 由**内核**自动生成（**上游同款**）⇒ MUST **NOT** 要求用户自带 `.id`；⑤ **暂停语义** —— 中断轮之后**不再进入下一轮**（恢复闭环归本 feature） | `specs/b12f1-concurrency-errors/spec.md` **裁定 7 / 8 / 9 / 14 / 20 / 24** · **FR-004 / FR-013 / FR-014** · **B12F1 的**下游承接 **D-1** · **回溯修订 T-9** · `specs/b12f1-concurrency-errors/data-model.md` §「`invoke()` 返回 dict 的 `__interrupt__` 键 = **元组**」 | **FR-002** · **FR-008** · **FR-009** · **FR-014** · 裁定 1 / 2 / 3 / 6 · SC-001 / SC-004 / SC-009 / SC-010 |
| **H-3** | **B12F1 → B10F1** | **M1** | **「真异常 + 中断同现」时的中断信息去向**：**上游同款** —— 真异常的 `raise exc` **先于**中断的合并抛出 ⇒ 一轮里既有真异常又有中断时 ⇒ **真异常抛出**、那批**中断元组被丢弃** ⇒ ⇒ 本 feature MUST **NOT** 指望「真异常抛出后还能从结果键里读到那批中断」⇒ ⇒ 本 feature 产出的 `__interrupt__` 键**只承载**「本轮**没有**真异常」时的中断集合；⚠️ MUST **NOT** 自创留痕形态（附注 / 调度状态字段）⇒ 原则 XI ③「自研必须论证」 | `specs/b12f1-concurrency-errors/spec.md` **FR-014** · **裁定 10** · **SC-013** · **偏离登记 X-4** · **B12F1 的**下游承接 **D-1 / D-6** | **FR-010** · 裁定 11 · SC-008 |
| **H-4** | **B1F1 → B10F1** | **M1** | **L1 已冻结的类型与协议，本 feature 只消费**：① `Interrupt`（`.value` / `.id`）与 `GraphInterrupt`（载荷挂在 `.payload` · **异常实参 `args[0]` = 同一个序列**）的类型、字段与构造签名 **一字不动**（`.id` 的**生成义务**归本 feature，但**类型**归 L1）；② `Command` 的字段与构造校验 **一字不动**（`resume` 位**已存在**）；③ `Checkpointer` 协议（**8 方法**）**只消费** ⇒ **L1 的 20 符号面零改动**（门禁 G7 / G8 / G16 / G19 恒绿）；④ `StateSnapshot`（**8 字段** · 含 `values` / `next` / `interrupts` / `tasks`）是「快照」的结构化载体 ⇒ 本 feature 的**检查点读侧契约** MUST 以它为准（**同类项同类承载** · 原则 XII ③） | `src/freegraph/contracts/types.py:99-118`（`Interrupt`）· `:260-311`（`StateSnapshot`）· `:33-83`（`Command`）· `src/freegraph/contracts/errors.py:102-129`（`GraphInterrupt`）· `src/freegraph/contracts/protocols.py:76-138`（`Checkpointer`） | **FR-001** · **FR-004** · **FR-011** · **FR-020** · 裁定 3 / 9 · SC-001 / SC-005 / SC-012 |
| **H-5** | **B7F1 → B10F1** | **M1** | **调度契约的跨 feature 接口 MUST 照写**：① **节点入参** —— 恢复时**被中断节点重新执行**的入参 MUST 等于 `read_channels(子映射)` 的结果、子映射 MUST 按「**通道映射的顺序**」构造 ⇒ MUST **NOT** 改写 key 顺序；② **合并路径** —— 恢复轮产生的写入 MUST 继续走 B7F1 的**批量**合并路径（每通道**一次** `Channel.update(values)`）⇒ MUST **NOT** 为恢复另写一条合并路径；③ **同轮顺序** —— 合并顺序 / 报告顺序 = **节点名序**（**上游同款**）；④ **步末清空** —— 恢复轮同样执行步末清空（裁定 33）；⑤ **调度状态** —— 恢复 MUST 重建调度状态（**已消费版本** / **通道版本** / **节点版本**）⇒ 恢复后的**触发判定**与首次运行**同款** | `specs/b7f1-superstep-loop/spec.md` **FR-005 / FR-008 / FR-013 / FR-014 / 裁定 26 / 27 / 33** · 契约 `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §3.2 / §4 / §5.3 | **FR-006** · **FR-017** · **FR-021** · 裁定 5 · SC-003 / SC-006 |

---

## Clarifications（澄清与裁定）

> **本 spec 的口径来源**：① **上游 `langgraph 1.2.11`**（唯一权威 · 宪法原则 XI）——
> 上游有答案的**一律照抄**（含上游的缺陷 ⇒ 更确定的口径）；② **发起者拍板**
> （`### Session 2026-11-13` 的 **5** 条）—— 只落在**上游没答案**的点
> （必须自研区 / 上游自身无定论）；③ **仓库内已冻结的跨 feature 契约**
> （B9F1 / B12F1 / B7F1 / B1F1 的承接条款）。
> ⇒ 全部走「**澄清与裁定**」表落成，**正文无未闭合的澄清标记残留**。
> ⇒ ⚠️ **原口径已修订**：「实质分歧点只有一处」的说法**作废** —— 澄清轮新增了 **5** 处
> 发起者拍板（挂起结果的字段集 · 失败信号的形态 · L1 冻结面的归属 · 门禁偏离处置 ·
> `.id` 任务标识含随机量）。

### Session 2026-11-13（澄清轮 · 发起者拍板）

> **收窄纪律**（宪法 v1.9.0 原则 XI）：每个要问的点 MUST **先查上游** ⇒ **上游有答案 ⇒
> 照抄 ⇒ 不许问** ⇒ 只许问**「上游没答案」**的点（落在**必须自研区**的 4 类里、或上游
> 自身无定论之处）⇒ ⇒ 本轮**只问**了 5 个**必须自研区**的点；**另**有 4 处「上游有答案」
> 的口径 **MUST NOT 拿来问** ⇒ 已**直接照抄**并落进正文（见下方「上游照抄补记」）。

- Q: 图因为中断挂起时，这次运行的结果对象应该包含哪些字段？（裁定 2 · FR-021）
  → A: **A（推荐）· 四个字段** —— 稀疏状态 + 中断集合（元素是 `Interrupt`）+ 已启动过的
  节点名 + 实际跑过的轮数；**不带**「待写入」⇒ 与 `SuperStepResult` **对称但不重复**
  ⇒ 落在 **裁定 2**（既有口径与之一致 ⇒ **确认**）· **FR-021** · SC-010。
- Q: 中断/恢复出错时，调用方应该拿到什么形态的失败信号？（裁定 3 · FR-011 · FR-013）
  → A: **A（推荐）· 一个异常 + 原因码** —— 新增 `InterruptError`（内核异常族的子类）+
  一个**取值封闭**的 `reason` 原因码字段；**消息只作英文摘要**；**不**把会话标识 /
  待恢复中断的 id 列表塞进异常对象（那是调用方自己传进去的）⇒ 落在 **裁定 3**
  （既有口径与之一致 ⇒ **确认**）· **FR-011** · **FR-013** · SC-011 / SC-012 ·
  偏离登记 **X-2**（**类型**与上游不同 · **消息要点**同款）。
- Q: L1 协议里 `invoke` 的入参类型要不要为了支持 `Command(resume=...)` 而放宽，这个「破冻结面」由哪一棒来做？（§破冻结面的回溯修订清单）
  → A: **A（推荐）· 留给 B7F3** —— **B10F1 不破 L1 冻结面**；「`invoke` 入参放宽为
  「状态字典或 `Command`」」**留到 B7F3**（M2 · 真正实现 `invoke` 的一棒）**一并做**
  ⇒ ⇒ **B10F1 的破冻结面清单只留**「L2 的 `runtime.__all__` 符号数」**一条**
  ⇒ ⇒ **理由**：B10F1 **不实现** `invoke`（属 B7F3）⇒ 现在破 L1 冻结面等于为一个
  **用不到的改动**提前消耗本 feature **唯一**的发起者追认名额（宪法：追认次数每 feature
  MUST ≤ 1 次）⇒ ⇒ 落在 §破冻结面的回溯修订清单 **T-1**（唯一一条）+ 下游承接 **D-3**。
- Q: 这个 feature 在 M1 阶段没有任何可用的 checkpointer 实现，人工验证记录里「HITL 恢复侧挂真实 saver 真跑一轮」这件事做不了，该怎么处置？（SC-020 · 宪法 v1.6.0）
  → A: **A（推荐）· 登记偏离 + 追认** —— 按宪法 v1.6.0「质量门禁的分阶段落地」办理：
  ① 在 **`plan.md`** 登记「**被偏离的具体门禁项**」+「**不可达成的根因**（含里程碑依据）」+
  「**判据未被放宽**的论证」+「**承接方**（B14F1 / M3）+ **承接机制**」；
  ② 在 **`tasks.md`** 放一条**阻断合入**的**追认任务**；
  ③ **追认文字**（发起者确认 + 日期）落 `harness/verification/B10F1/manual-verification.md`
  ⇒ ⇒ **挂起侧**（**不**依赖 saver）的人工验证**照常做** ⇒ ⇒ 落在 §门禁项的偏离登记
  **V-1** + 下游承接 **D-1**（承接方 **B14F1 / M3**）。

- Q: 中断 id 里那个「任务标识」要不要含随机量？（裁定 6 · FR-003 · 偏离登记 X-4）
  → A: **A（推荐·上游同款）· 随机 uuid4** —— 任务标识 = **随机 uuid4**（标准库 `uuid`）
  ⇒ ⇒ `.id` **不可猜** ⇒ ⇒ 「替这次审批拍板」的**能力凭据不可被推导**
  ⇒ ⇒ **跨恢复稳定**（F-1）由「**标识生成后随检查点持久化 · 恢复时读回复用**」保证
  ⇒ ⇒ **同一「挂起 → 恢复 → 再挂起」循环内复用同一个标识** ⇒ ⇒ 与上游**同款**
  （**实测 E-23**：上游的命名空间 = `"{节点名}:{随机 uuid4}"`）
  ⇒ ⇒ 落在 **裁定 6**（命名空间口径**改写**）+ **FR-003** + **P-05**；
  ⚠️ **未采纳**：B（完全确定性 ⇒ id 可复现但**可猜**）· C（混入会话标识 ⇒ 强度取决于
  用户取名习惯）。

#### 上游照抄补记（**MUST NOT 拿来问** · 已直接落进正文）

| # | 口径 | 上游锚点 | 落点 |
|---|---|---|---|
| **F-1** | `.id` MUST **跨恢复稳定** —— 同一节点的一次「挂起 → 恢复 → 在下一个 `interrupt()` 处再次挂起」循环内，**两次挂起产生的 `.id` 逐字相同** ⇒ ⇒ 命名空间**不得**随重跑次数变化 | **实测 E-17**（两次挂起的 id 相同）· `langgraph/types.py:967-974`（`from_ns` 用**同一个** `ns`） | **裁定 6**（命名空间口径改写）· FR-003 |
| **F-2** | `Command(resume=…)` 与 `Command(update=…)` **可以同时给出** ⇒ `update` 走**通道写入**、`resume` 走**恢复通道** ⇒ 两者**并存**、互不排斥 | `langgraph/pregel/_io.py:74-78`（`map_command`：`if cmd.resume is not None: yield (NULL_TASK_ID, RESUME, cmd.resume)` + `if cmd.update: …`） | **裁定 4**（表加一行）· FR-013 |
| **F-3** | `__interrupt__` 的元素 MUST **只**带 `.value` 与 `.id` ⇒ MUST **NOT** 增加「节点名」等额外字段（「哪个节点要批准」由 L1 已有的 `StateSnapshot.tasks` 承载 · 生产者归 **B15F1**） | `langgraph/types.py:593-597`（上游 `Interrupt` 只有 `value` / `id` 两个字段） | FR-002 · 裁定 1 |
| **F-4** | 在**已有历史快照**的会话（`thread_id`）上用**普通状态字典**调用 ⇒ 该次调用在**已有状态**上**继续写**（**会话连续**）⇒ **不是**恢复、**不**要求 checkpointer ⇒ ⚠️ **实测 E-26 ②**：**写通道 ⇒ 通道版本推进 ⇒ 订阅节点**重新触发** ⇒ ⇒ 被触及的节点**重跑** ⇒ ⇒ **`.id` 可变**（新的检查点 ⇒ 新的任务路径） | `langgraph/pregel/_loop.py:975-985`（`map_input` → 通道写入 · 落在已有 checkpoint 之上）· **实测 E-26 ②** | 裁定 4（表加注）· FR-013 末两行 |
| **F-5** | 在**已有历史快照**的会话上用 **`None`** 调用 ⇒ ⇒ **不**写任何通道 ⇒ ⇒ **只有被中断的节点**重跑（其它节点**不**重跑）⇒ ⇒ 结果与挂起时**完全相同** ⇒ ⇒ **`.id` 逐字不变**（**续跑**）⇒ ⚠️ ⇒⇒ **与 F-4 行为不同** ⇒ ⇒ MUST NOT 合并成一行 | `langgraph/pregel/_loop.py:975-985`（`map_input` 的 `None` 分支）· **实测 E-15 / E-26 ①** | 裁定 4（表加注）· FR-013 末两行 · 裁定 9 |

### Session 2026-11-13（plan 阶段回修 · **PR-1**）

> **背景**：`/speckit.plan` 阶段的**设计细化**发现了 spec 内部的一处**自相矛盾** ⇒
> **spec 是唯一权威** ⇒ ⇒ **必须回修 spec**（否则 plan 与 spec 打架 ⇒ tasks 无从落地）。
> ⚠️ **本条** **不是**「新的澄清」⇒ ⇒ **不占用**澄清轮的 5 问配额 ⇒ ⇒ **不**需要发起者再次拍板
> （改动的是**本 feature 自己**定义的**读侧契约** ⇒ **不是** L1 冻结面 ⇒ ⇒ 澄清轮 **Q3** 的拍板仍成立）。

- **PR-1**：spec **H-5 ⑤**（「恢复 MUST 重建调度状态」）与 spec **裁定 9 / FR-018**（读侧契约只有
  `.snapshot` + `.pending_writes` **两个**属性）**自相矛盾** ⇒ ⇒ **调度账本无处可取** ⇒ ⇒ 恢复后的
  **后续轮**触发判定会失效 ⇒ ⇒ **回修**：读侧契约**增**第三个具名属性 **`.scheduler`**（**调度账本** ·
  纯数据 · 可 JSON 序列化）⇒ ⇒ **落点**：**裁定 9**（裁定 + 理由两行）· **FR-018** · **下游承接 D-1**
  ⇒ ⇒ **配套契约**：`specs/b10f1-interrupt-resume/contracts/checkpoint-contract.md` §2 / §3
  ⇒ ⇒ **计划登记**：`plan.md` §Constitution Check 的 **PR-1**（**如实登记** · **不需要**追认）。

- **PR-4**：spec §0 的「架构层」行 / **Key Entities** / **Assumptions 8** 写「`interrupt()` 的
  **实现体**在 `src/freegraph/_primitives.py`（门面实现体）」⇒ ⇒ 而 **tasks T019** 写「在
  `_primitives.py` 惰性 import `freegraph.runtime._interrupt`」⇒ ⇒ 二者**互斥** ⇒ ⇒ **更关键**：
  **两个口径都会被门禁 G25 判红**（**实测**）—— 层注册表 §1 把 `src/freegraph/_primitives.py`
  登记为 **L2 单文件条目**、把 `src/freegraph/runtime/` 登记为**另一个 L2 目录条目** ⇒ 按 §0.2
  规则 3 的「模块定位口径」，二者**互相 import = 跨注册表条目的同层 import = 违规**
  （立项书 §5.1 铁律 3）⇒ ⇒ **实测两种方向都 FAIL**（`_primitives.py` → `runtime/` 与
  `runtime/superstep.py` → `_primitives.py` 均被判红；**惰性 import（函数体内）同样判红**
  —— 门禁扫 AST）⇒ ⇒ **回修**：**唯一合法形态** = 「机制整体住在 `src/freegraph/runtime/`
  这**一个注册表条目**内（`runtime/_interrupt.py`）· 门面 `src/freegraph/graph.py` 用
  **模块级** `ImportFrom` **直接转出**（`facade-L1-L3` 例外 ⇒ 门面 → L2 合法）·
  `src/freegraph/_primitives.py` **只留 `Send`**（MUST NOT import `runtime/`）」⇒ ⇒
  **实测**：G25 **PASS** + 门面的 G14 / G15 / G16 / G18 与架构门禁 **150 passed** ⇒ ⇒
  **落点**：**§0 表格「架构层」+「门禁约束（G25）」两行** · **Key Entities** · **Assumptions 8** ·
  **Out of Scope 第 15 条**（新增）· **§门禁约束** ⇒ ⇒ **配套**：`plan.md`（Summary + Project
  Structure + 触及文件表）· `tasks.md`（T002 / T019 / 新增门禁核对任务）·
  `contracts/interrupt-resume-contract.md` §1 / §4 · `contracts/upstream-parity.md` §2 ·
  `research.md` **DR-13** + §4 **PR-4** ⇒ ⇒ **不是 L1 冻结面**（L1 零改动）⇒ ⇒
  **不需要**发起者追认（**G25 的判据一字未改** —— 本回修恰恰是**让实现合规**，不是放宽判据）。

- **PR-8**（**2026-11-13 分析轮 · 实测**）：spec §5 的**破冻结面回溯修订清单（T-1）只登记了
  `runtime.__all__` 的 3 处代码断言** ⇒ ⇒ 而**分析轮**在沙箱里**实测**发现**另 3 处**既有冻结
  断言会因本 feature 的落地而**必红** ⇒ ⇒ ⇒ 按现 tasks 实施 ⇒ **pytest 必红** ⇒ ⇒ 违反宪法
  「MUST NOT 写**永久红**的 CI」⇒ ⇒ ⇒ **破冻结面清单 MUST 扩容为 6 处**：
  **④** `tests/runtime/test_read_contract.py::test_i9_the_reading_layer_adds_no_new_error_type`
  （`runtime/errors.py` 的 `__all__` **精确元组** + 其 `FreegraphError` 子类**精确清单**
  ⇒ **T-005** 加 `InterruptError` ⇒ 必红）· **⑤** `tests/facade/test_facade.py::TestInterrupt::test_raises_not_implemented`
  （门面 `interrupt` 恒抛 `NotImplementedError` ⇒ **T-018 / T-019** 接线后必红）·
  **⑥** `tests/runtime/test_superstep_concurrency.py` 里 `assert "NotImplementedError" in primitives`
  （守「`interrupt` 仍未接线」⇒ **T-019** 删实现体 + 清理陈旧 docstring 后必红 —— 当前**仅靠**
  docstring 里残留的字符串**侥幸通过**）⇒ ⇒ **回修**：§1.1（上游对照表）**增 3 行** +
  §5（回溯修订清单）**增 3 行** ⇒ ⇒ **均属「上游无此项 ⇒ 必须自研区 ③」⇒ 零行为面偏离**
  ⇒ ⇒ ⇒ **不**进 §4 偏离登记表（X-1…X-5 仍为 5 项）⇒ ⇒ ⇒ 但**冻结断言 MUST 回溯修订**
  （**判据零放宽**）⇒ ⇒ **发起者追认**（**并入 V-1 的那一次** ⇒ 追认次数仍为 1 次 · 宪法 E-6）
  ⇒ ⇒ **落点**：**§1.1** · **§5** · **§门禁项的偏离登记 V-1 的追认列** · **plan.md**
  （§破冻结面的回溯修订清单）· **tasks.md`（**T-012** + 附录）· `contracts/upstream-parity.md` §4 ·
  `research.md` §4 **PR-8**。


### 裁定 1 · `__interrupt__` 结果键的**元素形态**

| 项 | 内容 |
|---|---|
| **问题** | B12F1 的 D-1 与提示词 §2.1 说「`__interrupt__` 键的**元素类型 = 该元组**」；而 C17 说「结果含 `__interrupt__`（含 `.value` / `.id`）」；上游 `invoke()` 返回的又是 **list**。三者字面打架。 |
| **裁定** | **`result["__interrupt__"]` = 被接住的那个 `GraphInterrupt.args[0]`（即那个**元组**）**⇒ 其元素 = `Interrupt` 对象（带 `.value` / `.id`）**。换言之：**键的**值**就是那个元组**；元组的**元素**才是 `Interrupt`。 |
| **理由** | ① 提示词 §2.1 的**字面**：「接住 → 读 `exc.args[0]`（那个元组）→ 放进 `__interrupt__`」⇒ **键的值 = 那个元组**；② C17 的「元素含 `.value` / `.id`」⇒ 元素的类型 MUST 是 `Interrupt` ⇒ **元组自身不是元素**；③ 验收脚本 `harness/demo/graph_core.py:376-383` 的 `__interrupt__` 三条断言是**硬断言**（`check` 非 `soft`）且逐字为 `hasattr(first, "value")` / `hasattr(first, "id")`（其中 `first = itr[0] if isinstance(itr, (tuple, list)) else itr`）⇒ 若 `itr[0]` 是元组则该硬断言**必红** ⇒ **硬断言优先**；④ B12F1 的 `data-model.md` §「`invoke()` 返回 dict 的 `__interrupt__` 键」的值列写的是「**元组**」⇒ **键的值 = 元组**。 |
| **与上游的差异** | 上游 `invoke()`（v1 路径）返回的是 **list**（`langgraph/pregel/main.py:3951-3953` 的 `{**latest, INTERRUPT: interrupts}`，`interrupts` 是 `list`）⇒ freegraph 统一为**元组** ⇒ **DIFF**（结构差异 · 非更严 · 偏离登记 **X-1**）。 |

### 裁定 2 · 挂起时的**结果载体**（`SuperStepResult` 四字段冻结面零改动）

| 项 | 内容 |
|---|---|
| **问题** | `__interrupt__` MUST NOT 进 `SuperStepResult.state`（形态污染 · B12F1 裁定 25 ③）⇒ 而 `SuperStepResult` 的**四字段是冻结面**（B12F1 裁定 25 ②）⇒ 中断集合与 `steps` 该往哪儿放？ |
| **裁定** | 新增 **L2 的挂起结果类型 `InterruptResult`**（**4 个字段**：`state` / `interrupts` / `executed` / `steps`）⇒ `SuperStepResult` **四字段一字不动**（**不新增第 5 个字段**）⇒ `__interrupt__` **不进 `state`**。`InterruptResult` 提供 `as_result_dict() -> dict[str, Any]`（= `{**state, "__interrupt__": interrupts}`）⇒ **本 feature 独占「异常 → 结果键」的转成路径**（提示词 §2.1 的字面义务），B7F3 只调用它。<br>⚠️ **MUST NOT** 带「待写入」（`node_writes`）字段 —— 挂起时那些写入**已经合并进 `state`** ⇒ 该字段在挂起态**语义不明** ⇒ 带它等于多一份长期维护的承诺。 |
| **理由** | ① **层次对应优先于容器对应**（宪法 原则 XII）：上游的「结果」不是结构化对象而是**状态字典** ⇒ `__interrupt__` 是**字典的一个 key** ⇒ freegraph 的对应物在**结果字典**这一层 ⇒ 但**不能**因此给**单轮结果对象**加字段（B12F1 裁定 25 ②）；② `InterruptResult` 与 `SuperStepResult` **语义不同**（前者 = 「挂起」这种**结束方式**，后者 = 「一轮 / 跑完」）⇒ 不是「重复的载体」；③ 挂起时 `steps` = **如实计**（实际跑过的轮数 · **含**被中断的那一轮 · **不含**那个「发现没任务了」的空轮）⇒ B12F1 裁定 24 的**载体转移**在此落地 ⇒ ⇒ ⚠️ **两个结果类型的 `steps` 计数口径「刻意不同」（2026-11-13 分析轮拍板）**：`InterruptResult.steps` = **不含**空轮（挂起时**根本没有**空轮 —— 那一轮之后**不再进入下一轮**）· `SuperStepResult.steps` = **含**空轮（B7F1 冻结面 · `runtime/superstep.py` 的循环**先计数后判空轮**）⇒ ⇒ **同一张图**「挂起 N 轮」与「跑完 N+1 轮」⇒ ⇒ ⇒ **数值不可直接比较** ⇒ ⇒ MUST NOT 把两者的差值解读为「少跑了一轮」；④ ⚠️ **既有载体穷举（宪法 原则 XII 判据 ③ · MUST 先穷举 · 2026-11-13 分析轮补齐）** —— L1 **已有**的**同语义载体**逐条排查：<br>　（a）**L1 的 `StateSnapshot`**（`contracts/types.py:260-311`）**已有** `interrupts: tuple[Interrupt, ...]` 字段（与 `InterruptResult.interrupts` **同形**）⇒ ⇒ **排除**：`StateSnapshot` 的语义 = 「**某一时刻的完整定格**」（**快照** · **检查点**载体）· 8 个字段**全部必填**（`values` / `next` / `config` / `metadata` / `created_at` / `parent_config` / `tasks` / `interrupts`）⇒ 在**挂起**这一刻**构造**它需要凭空造出 `config` / `created_at` / `parent_config` / `tasks` 四个**挂起态并不存在**的量 ⇒ ⇒ 且它属 **L1 冻结面**（**20 符号面** · 门禁 G7 / G8 / G16 / G19 恒绿）⇒ ⇒ **新增字段即破冻结面** ⇒ ⇒ ⇒ **排除**；<br>　（b）**`SuperStepResult`**（B7F1 冻结面 · 四字段）⇒ ⇒ **排除**：其语义 = 「**一轮**的产物」· 而挂起是**跨轮**的**结束方式** ⇒ ⇒ 加字段即破 B12F1 裁定 25 ② 的**四字段冻结面** ⇒ ⇒ ⇒ **排除**（**MUST NOT** 新增第 5 个字段）；<br>　（c）**结果字典**（`{**state, "__interrupt__": interrupts}`）⇒ ⇒ **排除**：它是**门面层**的载体（原则 XII「层次对应优先于容器对应」）⇒ ⇒ **L2 的单轮结果对象 MUST NOT** 承载它（否则又回到「给单轮结果对象加字段」）⇒ ⇒ ⇒ **排除**；<br>　⇒ ⇒ **三项穷举后** ⇒ 「新增一个 L2 内部的结果载体」是**唯一**可行解 ⇒ ⇒ **不是**在**错误的位置**上新增**重复的载体**（原则 XII ③）⇒ ⇒ **零新增 L1 符号**（G7 恒绿）；⑤ ✅ **发起者 2026-11-13 拍板确认**（澄清轮 Q1）：**四个字段**（稀疏状态 + 中断集合 + 已启动过的节点名 + 实际跑过的轮数）⇒ **与 `SuperStepResult` 对称但不重复** ⇒ **不带**「待写入」。 |
| **落地** | `freegraph.runtime.__all__` 由 **20 → 23**（新增 `InterruptResult` · `InterruptError` · 裁定 10 的新入口）⇒ B12F1 `tasks.md` **T072** 的「`runtime.__all__` 符号数 == 20」断言 MUST **回溯修订**（见 §破冻结面的回溯修订清单 **T-1**）⇒ ⚠️ **L1 的 20 符号面零改动**（新增的三项全在 **L2** ⇒ 门禁 G7 / G8 / G16 / G19 恒绿）。 |

### 裁定 3 · 失败信号的**类型**（新增 L2 异常 `InterruptError`）

| 项 | 内容 |
|---|---|
| **问题** | 恢复路径有 4 类失败（未挂 checkpointer / 未提供恢复值 / 多个挂起中断未按 id 指定 / 没有挂起的中断）⇒ 用什么类型报？ |
| **裁定** | 新增 **L2 异常 `InterruptError`**（继承 `FreegraphError`，**不**继承 `ValueError`），带 **`.reason`**（**封闭取值域**的字符串）：`"checkpointer_required"` / `"resume_value_required"` / `"ambiguous_resume"` / `"no_pending_interrupt"` / `"not_in_run"`。**L1 的 20 符号面零改动**（G7 恒绿）⇒ 该类型落 **L2 的 `freegraph.runtime.errors`**（**L2 内部 API**）。 |
| **理由** | ① **可诊断性是一等功能**（宪法原则 IV）：MUST NOT 让上层靠**解析消息文本**取细节 ⇒ 结构化 `reason` 必备；② L1 的 `FreegraphError` docstring 承诺「上层只捕获基类 `FreegraphError` 即可兜住**全部**内核错误」⇒ 抛内置 `RuntimeError`（上游同款）会**破坏该冻结承诺** ⇒ 故**不**照抄上游的 `RuntimeError` 类型（**偏离登记 X-2 · DIFF · 非更严**）；③ **不**继承 `ValueError` ⇒ 用户既有的 `except ValueError` **不会**误吞中断相关的失败（沿用 `EmptyChannelError` 的继承纪律）；④ **不**新增 L1 符号 ⇒ G7 / G8 / G16 / G19 零改动；⑤ ⚠️ **异常对象 MUST **只**带 `reason`** —— **不**携带会话标识 / 待恢复中断的 id 列表等**上下文**（那些是调用方自己传进去的 ⇒ 异常不必重复携带）⇒ 异常**只**回答「**为什么失败**」，**不**回答「**现场是什么**」；⑥ ⚠️ **`errors.__all__` 的口径（2026-11-13 分析轮第二轮补齐 · 消除二义）** —— `InterruptError` **MUST** 写进 `src/freegraph/runtime/errors.py` 的 `__all__`（**7 → 8**）⇒ ⇒ 与 `tasks.md` **T012-a** 第 ④ 处的**期望集合**（**7 + `InterruptError`**）**逐字对齐**（**否则该断言不可判定**）⇒ ⇒ ⚠️ `runtime.errors.__all__` 的**变更面**（7 → 8）**属** §破冻结面的回溯修订清单 **T-1** 第 ④ 处的**处置范围**（**拆分而不删** · **判据零放宽**）。 |
| **消息** | 缺省摘要为**英文**（沿用仓库既有约定）且 MUST **点名**失败原因（如 `"Cannot resume without a checkpointer"` / `"resume value is required"`）⇒ **消息要点与上游逐字同款**（见 §Upstream Parity **P-08 / P-09 / P-10**）。 |
| **拍板** | ✅ **发起者 2026-11-13 拍板确认**（澄清轮 Q2）：**一个 `InterruptError` + 一个取值封闭的 `reason` 原因码**；**消息只作英文摘要**；**不**加上下文字段（选项 B）⇒ **不**新增异常类型、直接用内置 `RuntimeError`（选项 C）**不采纳**。 |

### 裁定 4 · `Command(resume=...)` 作为**图输入**的行为（FR-006 的写死）

| 项 | 内容 |
|---|---|
| **裁定** | 「`Command(resume=...)` 作为**图输入**」的**完整判定表**（输入形态 × 挂起中断数 → 行为）**逐字见 FR-013**（**「映射」的唯一事实源**）⇒ ⇒ 本裁定**不复制**该表（避免两处漂移 · 2026-11-13 分析轮 **A-01**）⇒ ⇒ ⚠️ **分工声明**（2026-11-13 分析轮）：**FR-013 = 映射**（什么输入 → 什么行为）· **本裁定 = 判定顺序**（先判哪一条）⇒ ⇒ ⇒ **实现口径只看这两处** ⇒ ⇒ ⇒ `contracts/interrupt-resume-contract.md` §6.1 **只**承载「顺序 + 上游依据」，**不**再复述判定表（避免第三处漂移）。 |
| **上游对照** | 逐条见 §Upstream Parity 的 **P-08**（未挂 checkpointer ⇒ 明确异常）· **P-09**（多个挂起中断 ⇒ 须按 id 指定）· **P-10**（**未提供**恢复值）· **P-15**（**非** `Command` 的输入**不**触发恢复）⇒ ⇒ 「按 id 的映射」与「**非** map 的 dict」的**上游启发式**见偏离登记 **X-3** ⇒ ⇒ 「`resume` 与 `update` **并存**」见上游照抄补记 **F-2** ⇒ ⇒ 「已有快照的会话 + **普通字典**输入 = **会话连续**」见补记 **F-4** ⇒ ⇒ 「已有快照的会话 + **`None`** 输入 = **只有被中断的节点重跑 · `.id` 不变**」见补记 **F-5**（⚠️ **实测 E-26** ⇒ 两种形态**行为不同**）。 |
| **判定顺序** | ① 输入**不是** `Command` ⇒ **首次运行**路径（**不**要求 checkpointer · **不**触发恢复）② `resume` 位**未提供**（`None`）⇒ `resume_value_required` ③ **未挂** checkpointer ⇒ `checkpointer_required` ④ 该会话**没有**挂起中断 ⇒ `no_pending_interrupt` ⑤ `resume` 是**标量** 且挂起中断 **> 1** ⇒ `ambiguous_resume` ⑥ `resume` 是 **dict** 且**全部 key** 都是**当前挂起中断的 id** ⇒ 按 id 逐个恢复（**未被指定的仍挂起**）⇒ ⚠️ **map 的「值」原样投递**给该节点（**标量即可** · **上游同款** · `langgraph/pregel/_algo.py:1313-1314` 的 `task_resume_write.append(mapped_resume_write)`）⇒ ⇒ 该值 = 该节点**下一个** `interrupt()` 的恢复值（**不是**「节点内全部中断值的列表」）⇒ ⇒ 同一节点的**第 2 个** `interrupt()` 因「恢复值不足」⇒ **再次挂起**（裁定 7 · **上游同款** · **实测 E-17**）⑦ `resume` 是 **dict** 但 key **不**全是挂起中断的 id ⇒ **普通恢复值**（**仅当**挂起中断数 == 1 时有效；**> 1** ⇒ 回到 ⑤ 的 `ambiguous_resume`）⑧ `resume` 与 `update` **并存** ⇒ 两者**各走各的通道**。<br>⚠️ **② 先于 ③**（**上游同款** · **实测 E-25a / E-25b**：上游的 checkpointer 检查**在 `if resume is not None` 之内** ⇒ `resume=None` 时**根本不触达**）⇒ ⇒ ⑦ 的「> 1 ⇒ `ambiguous_resume`」是为消除「普通恢复值**到底恢复哪一个**」的歧义。<br>⚠️ **空 dict**（`{}`）⇒ 归 ⑥（**真空为真** · **结构同款 · 未取证**）⇒ 恢复**零个** ⇒ 全部**仍挂起**。 |

> ⚠️ **「map 的识别规则」的上游差异说明**：上游用「**全部 key 长得像 `xxh3_128` 摘要**」来判定
> 「这是按 id 的恢复映射」（`langgraph/pregel/_loop.py:910-914`）⇒ 一个**恰好**长得像摘要的
> 普通字典会被**误判** ⇒ freegraph 改用「**全部 key 都是当前挂起中断的 id**」⇒ **更精确**
> （**STRICTER** · 非更严的失败信号，而是**消除歧义**）⇒ 偏离登记 **X-3**。

### 裁定 5 · 恢复时「**从节点起点重跑**」的载体（最容易实现错的语义）

| 项 | 内容 |
|---|---|
| **裁定** | 恢复时**被中断的节点函数从头重新执行一遍**（**整个函数**）⇒ **不保存**局部变量、**不**从中断点继续 ⇒ 节点内部靠 `interrupt()` 的**返回值**区分「首次执行」与「恢复执行」（写法：`answer = interrupt("approve?")`）。 |
| **理由** | ① 上游 docstring 逐字：「The graph resumes from the start of the node, **re-executing** all logic.」（`langgraph/types.py:864`）⇒ **上游同款**；② **实测 E-2 / E-8 / E-17**：恢复后节点函数的**前半段被再次执行**（副作用序列 `['enter', 'enter', 'got yes']`）⇒ 局部变量**不保留**；③ 「从中断点继续」= 保存了局部变量 ⇒ 与上游**语义不同** ⇒ 属**最易错点** ⇒ MUST 写成**独立可判定的验收判据**（SC-003 / A2）。 |

### 裁定 6 · `.id` 的**生成**（内核自动 · 零第三方依赖）

| 项 | 内容 |
|---|---|
| **裁定** | `.id` 由**内核自动生成**（MUST **NOT** 要求用户自带）⇒ 形态 = **32 位十六进制字符串**（16 字节摘要）⇒ 派生自「**节点名 + 该节点本次「挂起 → 恢复」循环内的任务标识**」组成的命名空间 ⇒ 摘要算法 = **标准库 `hashlib.blake2b(digest_size=16)`**。<br>⚠️ **该任务标识 = 随机 uuid4**（标准库 `uuid` · **上游同款** · **实测 E-23**）⇒ ⇒ `.id` **不可猜** ⇒ ⇒ 「替这次审批拍板」的**能力凭据不可被推导**（上游 `Interrupt.id` 的用途逐字：「Can be used to resume the interrupt directly」）。<br>⚠️ **该任务标识 MUST 跨恢复保持不变** ⇒ ⇒ 标识**生成一次后随「中断载荷（`Interrupt` 对象）」持久化在 pending writes 里**（**零新增持久化字段** —— uuid **不**落盘）· **恢复时读回并复用**（**不重算**）⇒ ⇒ 恢复时**读回**的 `.id` 与先前**交给调用方**的那个**逐字相同** ⇒ ⇒ 命名空间**不得**随「重跑次数」变化 ⇒ ⇒ **同一「挂起 → 恢复 → 再挂起」循环内复用同一个标识**。 |
| **理由** | ① **零第三方运行时依赖**（宪法依赖白名单：必装运行时依赖 = 无）⇒ MUST **NOT** 用上游的 `xxhash`（`xxh3_128_hexdigest`）⇒ 属原则 XI ①「零账号 / 零依赖的硬约束」**必须自研区**；② `blake2b(digest_size=16)` 的十六进制长度 = **32** ⇒ 与上游 `xxh3_128_hexdigest` 的长度**逐字相同** ⇒ **形态同款**（`Interrupt.id` 的用途 = 唯一定位一次中断 · 不依赖具体算法）；③ **同一节点同一轮内的多个 `interrupt()` 共享同一个 id**（**上游同款** · **实测 E-17**：两次中断的 id 相同）⇒ ⇒ freegraph 的命名空间**不含**「节点内第几次中断」；④ **不同节点的 id 互不相同**（**上游同款** · **实测 E-11**：两个节点的两个 id 不同）⇒ ⇒ 命名空间**必须含节点名**；⑤ ⚠️ **跨恢复稳定**（**上游同款** · **实测 E-17**：一次「挂起 → 恢复 → 在下一个 `interrupt()` 处再次挂起」的循环里，**两次挂起产生的 id 逐字相同**）⇒ ⇒ 命名空间**不得**随重跑次数变化 ⇒ ⇒ **照抄上游 · 补记 F-1**；⑥ ⚠️ **任务标识含随机量**（**上游同款** · **实测 E-23**：上游的命名空间 = `"{节点名}:{随机 uuid4}"`）⇒ ⇒ `.id` **不可猜** ⇒ ⇒ **恢复审批的能力凭据不可被推导** ⇒ ⇒ **照抄上游 · 澄清轮 Q5 拍板** ⇒ ⇒ 代价是「同一张图两次运行的 id 不同」⇒ ⇒ 该代价**不影响**「状态与节点序列的可复现性」（id 是**不透明句柄**· 非行为输出）⇒ ⇒ 差分判据 **DI-01** 已按「32 位十六进制 + 唯一」写 · **不比具体值** ⇒ ⇒ **恒绿**。 |
| **差异登记** | 摘要**算法**与上游不同（上游 `xxh3_128_hexdigest` · freegraph `blake2b-128`）⇒ **DIFF**（结构差异 · **非更严** · 偏离登记 **X-4** · 属原则 XI ① 自研区）；**长度**（32 位十六进制）与**唯一性**与上游**同款**；**命名空间形态**（节点名 + **随机 uuid4**）与上游**同款** ⇒ ⇒ **id 的不可猜性同款**。 |

### 裁定 7 · 同一节点内**多个** `interrupt()` 的 resume 匹配规则

| 项 | 内容 |
|---|---|
| **裁定** | 同一节点内的多个 `interrupt()` **按节点内的出现顺序**匹配 resume 值（第 1 个 `interrupt()` 取第 1 个恢复值 · 第 2 个取第 2 个）⇒ 恢复值**不足**时 ⇒ 节点在该处**再次挂起**（产生**新的**中断载荷）⇒ 再次提交恢复值即可继续。 |
| **理由** | ① 上游 docstring 逐字：「If a node contains multiple `interrupt` calls, LangGraph matches resume values to interrupts based on their order in the node.」（`langgraph/types.py:866-868`）⇒ **上游同款**；② **实测 E-17**：第一次恢复后节点在**第二个** `interrupt()` 处**再次挂起**（结果里的 `__interrupt__` 载荷变成 `second?`）· 第二次恢复才跑完 ⇒ **「再次挂起」而非报错**是上游行为；③ **实测 E-18**：更早的恢复值被**复用**（第 1 个 `interrupt()` 仍拿第 1 个恢复值）⇒ 恢复值按**任务**累积。 |

### 裁定 8 · 中断**前**已产生的写入**不丢失**（挂起不是回滚）

| 项 | 内容 |
|---|---|
| **裁定** | 节点中断时，**同一轮内其它节点**的写入 **照常合并**（中断**不是**「出错」⇒ 沿用 B12F1 的「整轮不原子」口径）⇒ **中断前**已落地的状态写入 **保留**（挂起**不是**回滚）⇒ 恢复时节点看到的入参**含**那些写入。 |
| **理由** | ① **上游同款**（**实测 E-21**）：一个节点中断 + 另一个节点成功写 `messages=['ok']` ⇒ 结果 `{'messages': ['ok'], '__interrupt__': [...]}` ⇒ 中断**不**丢弃同轮其它节点的写入；② **上游同款**（**实测 E-16**）：`pre` 节点写的 `count=99` 在中断后仍在 ⇒ 恢复后节点读到 `count=99` 并写出 `count=100` ⇒ **SC-004** 的依据；③ B12F1 的 `V-16` / 契约 §7 已冻结「中断**不是**失败 ⇒ 该节点视为**未完成**」⇒ 被中断节点**自身**的写入丢弃、**其它**节点的写入保留。 |

### 裁定 9 · **检查点最小契约**（读侧 + 写侧）—— L2 只消费 L1 协议

| 项 | 内容 |
|---|---|
| **问题** | L1 的 `Checkpointer` 协议（**8 方法** · B2F1 冻结）的**返回结构与载荷形状挂起 B14F1**（协议 docstring 逐字）⇒ 而本 feature（M1）必须**经由 checkpointer 读快照 + pending writes**才能恢复 ⇒ 两者之间需要一个**最小契约**。 |
| **裁定** | 本 feature 定义并**只消费**下列**最小契约**（L2 **不** import L4 实现 · ARCH-1 不变）：<br>**读侧** —— `checkpointer.get_tuple(config)` 的返回值 MUST 暴露**三个**具名属性：<br>　• `.snapshot` —— **L1 的 `StateSnapshot`**（含 `values` / `next` / `interrupts` / `tasks`）⇒ 快照的**载体**用 L1 **已有**的数据类（**同类项同类承载** · 原则 XII ③ · **零新增**）；<br>　• `.pending_writes` —— **待写入**序列（每个元素 = `(task_id, channel, value)` 三元组 · **上游同款** `PendingWrite`）；<br>　• `.scheduler` —— **调度账本**（**纯数据** · 可 JSON 序列化）⇒ 承载 `versions_seen` / `channel_versions` / `node_versions` / `dynamic_edges` ⇒ ⇒ 恢复 MUST 据此**重建调度状态**（**H-5 ⑤**）⇒ ⇒ **恢复后的触发判定与首次运行同款** ⚠️ **本属性是 plan 阶段回修新增**（**PR-1**）—— 初版只列两个属性 ⇒ 与 **H-5 ⑤** 自相矛盾 ⇒ ⇒ **不是 L1 冻结面**（是**本 feature 自己**定义的契约）⇒ ⇒ **L1 零改动**（`StateSnapshot` **不加**字段）⇒ ⇒ 与澄清轮 **Q3** 的拍板（「B10F1 不破 L1 冻结面」）**一致**。<br>⚠️ **「会话连续」路径同样 MUST 读 `.scheduler`**（**2026-11-13 分析轮拍板 · 照抄上游** · **实测 E-26**）⇒ ⇒ 该 `thread_id` 已有历史快照时 ⇒ 用 `.scheduler` 重建调度状态 ⇒ ⇒ **续跑**（检查点的调度状态被沿用）⇒ ⇒ ⚠️ **两种输入形态行为不同**（**实测 E-26**）⇒ ⇒ **`input = None`** ⇒ **不**写任何通道 ⇒ **只有被中断的节点**重跑 · `.id` **不变**；**`input = StateDict`** ⇒ **写通道** ⇒ **通道版本推进** ⇒ 订阅节点**重新触发** ⇒ 被触及的节点**重跑** · `.id` **可变** ⇒ ⇒ 与**恢复**路径（**显式**跑 `.snapshot.next` · **不走**触发判定）**刻意不同**（见 **FR-013** 末两行）。<br>**写侧** —— 挂起时 MUST 经由 `checkpointer.put(config, values=..., metadata=...)` 写**快照**、经由 `checkpointer.put_writes(config, writes=..., task_id=..., task_path=...)` 写**待写入**（含中断留痕）。<br>**保留通道名** —— 内部通道名 `__interrupt__`（中断留痕）与 `__resume__`（恢复值）⇒ **上游同款**（`langgraph/_internal/_constants.py:9` / `:11`）⇒ 且 `__interrupt__` **同时**是结果字典的**键名**（上游用**同一个**常量 · 原则 XI ②）。 |
| **理由** | ① L1 的协议用 `*args, **kwargs` + `-> Any` ⇒ **不**约束载荷形状 ⇒ 由本 feature 冻结**读侧 / 写侧**的最小面是**唯一**可行路径（**不**改 L1 ⇒ G7 / G8 / G16 / G19 零改动）；② 快照载体用 L1 已有的 `StateSnapshot` ⇒ **零新增数据类**；③ 读侧 / 写侧**成对**冻结 ⇒ 否则「写得出的读不回」⇒ ⇒ **下游承接 B14F1**（见 §下游承接条款 **D-1**）；④ `__interrupt__` / `__resume__` 两个通道名 **与上游逐字同款** ⇒ 上游形状的 saver 的**待写入**可直接被 freegraph 读取；⑤ ⚠️ **调度账本 MUST 是「一等」载体**（**不**塞进 `StateSnapshot.metadata`）⇒ 上游把 `channel_versions` / `versions_seen` 放在 `Checkpoint` 的**一等字段**里（`langgraph/checkpoint/base/__init__.py:105-112`）⇒ ⇒ 同款；⇒ 「借位 `metadata`」被排除（原则 XII「层次对应优先于容器对应」）。 |

### 裁定 10 · L2 的**入口形态**与「结果键」的归属

| 项 | 内容 |
|---|---|
| **裁定** | 本 feature 在 L2 新增**一个**入口 —— **`run_graph(spec, input=None, *, state=None, checkpointer=None, config=None, max_steps=10007, max_concurrency=None) -> SuperStepResult \| InterruptResult`** ⇒ **参数口径（逐条写死 · 消除歧义）**：① `input` = `StateDict \| Command \| None`（**图输入** · 为 `Command` ⇒ **恢复**路径）② ⚠️ **`state` = `SchedulerState \| None`（**调度状态** · ⚠️ **MUST NOT** 读成「状态字典」）** ③ `checkpointer` = `Checkpointer \| None`（**只消费** L1 协议 · **不**实现）④ `config` = `RunConfig \| None` ⑤ `max_steps` = `int`（**缺省 10007** · **上游同款**）⑥ `max_concurrency` = `int \| None` ⇒ 返回 **`SuperStepResult \| InterruptResult`**（**挂起 ⇒ `InterruptResult`**）⇒ **B7F3** 的 `invoke` 据此把 `InterruptResult` 转成 `{**state, "__interrupt__": interrupts}` ⇒ ⇒ **「异常 → `__interrupt__` 键」的转成路径只此一条**（本 feature 独占）。**既有**的 `run_super_step` / `run_super_steps` **签名与返回类型一字不动**（B7F1 冻结面）⇒ 新入口**另立**，MUST **NOT** 改写既有入口。 |
| **理由** | ① B12F1 的 D-1 + 提示词 §2.1：「本 feature MUST 负责把接住的这个异常转成结果键」+「MUST **NOT** 要求 B12F1 预先产出带 `__interrupt__` 的结果对象」⇒ 转成路径归本 feature；② B7F3 的 FR-006（承 B12F1 的 D-2 + Q12）逐字：「待 **B10F1** 落地后，`invoke` 才把它**转成**结果里的 `__interrupt__` 键 ⇒ **本 feature MUST NOT** 另写一条转成路径」⇒ 两棒**同一条**路径；③ 既有入口的返回类型是**冻结面** ⇒ 新入口另立（B12F1 增 `max_concurrency` 时也是「只**增** keyword-only」的最小组改面 · 本条改动面**更大** ⇒ 故另立）。 |

### 裁定 11 · 「真异常 + 中断同现」时的中断信息去向

| 项 | 内容 |
|---|---|
| **裁定** | 一轮里**既有真异常又有中断**时 ⇒ **真异常抛出**、那批中断元组**丢弃** ⇒ ⇒ `__interrupt__` 键**只承载**「本轮**没有**真异常」时的中断集合 ⇒ MUST **NOT** 自创留痕形态（附注 / 调度状态字段）⇒ 原则 XI ③「自研必须论证」。 |
| **理由** | ① **上游同款**（`langgraph/pregel/_runner.py:687` 的 `raise exc` **先于** `:690` 的合并抛出 ⇒ **B12F1 的实测 E-2e 已取证**：一个 future 抛 `ValueError`、另一个抛 `GraphInterrupt` ⇒ 抛出的是 `ValueError` ⇒ 中断元组**被丢弃**）；② B12F1 的 **FR-014 / 裁定 10 / SC-013** 已冻结并**已接线**到本 feature 的提示词初稿（H-3）；③ 上游另有 checkpoint 留痕（pending writes）⇒ freegraph v1 **无 checkpoint 实现** ⇒ 该批元组**丢弃** ⇒ 属**阶段性**差异 ⇒ **B14F1** 落地后**自动消解**（下游承接 **D-2**）。 |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 节点挂起并把「要审批什么」交还调用方（Priority: P1）

作为用户，我的审批节点调用 `interrupt("approve?")` 后，我希望图**停止执行**并把
「要审批什么」交给我，而不是抛一个看不懂的异常。

**Why this priority**: 这是 HITL 的**入口**——没有它，后面的恢复无从谈起；且它是本 feature
**最小可交付**的垂直切片（挂起 + 交还中断信息）⇒ 单独交付即有价值。

**Independent Test**: 执行一张只有一个审批节点的图 ⇒ 断言结果含 `__interrupt__` 键、
其元素带 `.value == "approve?"` 与可读的 `.id` ⇒ **不依赖** checkpointer、**不依赖**恢复。

**Acceptance Scenarios**:

1. **Given** 一个节点调用 `interrupt("approve?")` 的图，**When** 首次执行，**Then** 图**挂起**
   （**不**进入下一轮），结果含 `__interrupt__` 键，其元素的 `.value == "approve?"`、
   `.id` 是**非空字符串**且由**内核**生成（用户**未**自带）。
2. **Given** 同一轮里**另一个**节点正常写状态，**When** 图挂起，**Then** 那条写入**保留**
   （挂起**不是**回滚）⇒ 结果的状态部分含该写入。
3. **Given** 同一 super-step 里**两个**节点同时中断，**When** 图挂起，**Then** `__interrupt__`
   里的**两个**中断**都在**（一个都不丢）⇒ 元素集合与两个被中断节点一一对应。

---

### User Story 2 - 提交审批结果后图继续跑完（Priority: P2）

作为用户，我拿到中断信息后用 `Command(resume="yes")` 提交审批结果，我希望图**继续执行
到结束**，且最终状态里能看到审批结果。

**Why this priority**: HITL 的**闭环**在「恢复」这一半——只有 P1 则图永远停在审批处，
对用户**没有**可用价值。

**Independent Test**: 挂 checkpointer ⇒ 首次执行挂起 ⇒ 第二次以 `Command(resume="yes")`
执行 ⇒ 断言结果为**完成态**（**无** `__interrupt__`）且状态含 resume 值。

**Acceptance Scenarios**:

1. **Given** 图已因 `interrupt` 挂起且挂了 checkpointer，**When** 以
   `Command(resume="yes")` 再次执行，**Then** 图**跑完**、结果**无** `__interrupt__` 键、
   状态里含 `"yes"`。
2. **Given** 编译产物**未挂** checkpointer，**When** 以 `Command(resume="yes")` 执行，
   **Then** 抛**明确异常**且消息指明「恢复需要 checkpointer」⇒ **不**静默降级为内存态恢复。
3. **Given** 图已因 `interrupt` 挂起且挂了 checkpointer，**When** 以
   `Command(resume=None)`（**未提供**恢复值）执行，**Then** 抛**明确异常**（**不**静默无操作）。

---

### User Story 3 - 恢复时节点从头重跑（Priority: P3）

作为实现者，我需要知道恢复时的节点是**重新执行**的，从而在节点里用 `interrupt()`
的返回值做分支——这是 LangGraph 的既定语义。

**Why this priority**: 它是「从节点起点重跑」这条语义的**唯一可判定出口**⇒ 没有它，
「恢复」很容易被实现成「从中断点继续」（= 偷偷保存了局部变量）⇒ 而那会让节点作者
写出**依赖局部变量**的错误代码。

**Independent Test**: 节点内放一个自增计数器 ⇒ 首次执行被中断 ⇒ 恢复执行 ⇒ 断言
计数器**观察到「这是第 2 次进入节点」**。

**Acceptance Scenarios**:

1. **Given** 一个节点在 `interrupt()` **之前**有一段会留下痕迹的代码，**When** 恢复执行，
   **Then** 那段代码**再次执行**（痕迹出现两次）⇒ 证明**从头重跑**。
2. **Given** 恢复执行，**When** 节点调用 `interrupt("approve?")`，**Then** 该调用**返回**
   resume 值（**不**再次抛中断）⇒ 节点据此继续跑完。

---

### User Story 4 - 恢复路径确实经由 checkpointer（Priority: P4）

作为实现者，我需要确信「恢复」**不是**内存态的临时旁路——它必须真的从持久化层读回
被中断处的状态，这样即使进程重启、甚至几天之后，图仍能恢复。

**Why this priority**: 这是 C17 修订（2026-11-05 发起者拍板）的**硬要求**⇒ 也是本 feature
与「内存态恢复」这条捷径的**分界线**。

**Independent Test**: 用一个**记录调用**的 checkpointer 桩 ⇒ 断言恢复时它被调用且
读到了**该会话**的**快照 + pending writes**；未挂 checkpointer 时断言抛明确异常。

**Acceptance Scenarios**:

1. **Given** 挂了「记录型」checkpointer 桩的图，**When** 恢复执行，**Then** 桩记录到
   **该会话**（`thread_id`）的**快照读取**与**待写入读取**。
2. **Given** 同上，**When** 恢复执行，**Then** 被中断节点的**重跑**读到的入参 =
   **快照里的状态**（含中断前已产生的写入）。
3. **Given** 恢复后图**再次**挂起（新的一次中断），**When** 断言，**Then** 桩记录到
   **新的**快照写入与**待写入**写入 ⇒ ⇒ 挂起态**可被再次恢复**（闭环可重复）。

---

### Edge Cases

- **节点在 `interrupt()` 之前就抛了真异常** ⇒ 该异常**原样**抛出（中断**未**发生）⇒
  `__interrupt__` **不**产生（不是「中断 + 错误」并存）。
- **同一轮既有真异常又有中断** ⇒ **真异常**抛出、那批中断元组**丢弃**（裁定 11）。
- **节点内连续多次 `interrupt()`** ⇒ 第 1 个取第 1 个恢复值、第 2 个取第 2 个；
  恢复值**不足** ⇒ 在该处**再次挂起**（裁定 7）。
- **同一节点在**同一轮**内多次 `interrupt()`** ⇒ 它们的 `.id` **相同**
  （命名空间不含「节点内第几次」· 裁定 6）。
- **两个不同节点同时中断** ⇒ 两个 `.id` **互不相同** ⇒ 可用按 id 的映射分别恢复。
- **恢复值本身是一个 dict** ⇒ 只有当它的**全部 key 都是当前挂起中断的 id** 时才被当作
  「按 id 的映射」；否则它是**普通的恢复值**（裁定 4）。
- **恢复的会话（`thread_id`）里没有挂起的中断** ⇒ 抛明确异常
  （`reason="no_pending_interrupt"`）⇒ **不**静默跑完。
- **`interrupt()` 在图运行之外被调用**（不在任何节点里）⇒ 抛明确异常
  （`reason="not_in_run"`）⇒ **不**静默返回 `None`。
- **恢复后节点再次中断**（审批没通过，需要再问一次）⇒ 图**再次挂起**、产生**新的**
  中断载荷 ⇒ 调用方可再次提交恢复值（闭环可重复）。
- **恢复时 checkpointer 里查不到该会话**（会话已被删 / `thread_id` 写错）⇒ 抛明确异常
  （`reason="no_pending_interrupt"`）⇒ **不**当作「空状态从头跑」。
- **中断的 `value` 是任意对象**（dict / 自定义类 / `None`）⇒ 原样透出到
  `Interrupt.value` ⇒ **不**被序列化 / **不**被拷贝。

---

## Upstream Parity *(mandatory — 宪法 v1.9.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11**（取证于 **2026-11-13** · `.venv` 内安装 ·
上游只在**差分测试侧**使用 · 不进发行面）

**取证方式**：① 读源码（逐条带 `路径:行号`）；② **实跑**（本 spec 的 **E-1…E-26**）⇒
**行为**断言 MUST 有实测支撑（原则 XI「上游锚点纪律」）。

### §1 逐条对照（**P-01…P-17**）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| **P-01** | `interrupt(value)` 首次调用**抛**可识别的中断异常 | `langgraph/types.py:851`（`def interrupt`）· `:967-974`（`raise GraphInterrupt((Interrupt.from_ns(...),))`）· `langgraph/errors.py:102-107`（`GraphInterrupt`） | 同款：抛 `GraphInterrupt`（L1 已有 · `src/freegraph/contracts/errors.py:102-129`），载荷 = **1-元组**（`tuple[Interrupt, ...]`） | SAME | 上游同款；载荷形态由 B12F1 冻结（H-2） |
| **P-02** | 恢复后 `interrupt()` **返回**恢复值（**不**再抛） | `langgraph/types.py:955-958`（`return scratchpad.resume[idx]`）· `:960-965`（`get_null_resume` 分支） | 同款 | SAME | **实测 E-2 / E-17** |
| **P-03** | 恢复**从节点起点重跑**（整个节点函数重新执行） | `langgraph/types.py:864`（「The graph resumes from the start of the node, **re-executing** all logic.」） | 同款（裁定 5） | SAME | **实测 E-2 / E-8 / E-17**（副作用序列 `['enter','enter','got yes']`） |
| **P-04** | 中断信息落在**结果字典**的 `__interrupt__` **键** | `langgraph/pregel/main.py:3938-3954`（`{**latest, INTERRUPT: interrupts}`）· `langgraph/_internal/_constants.py:9`（`INTERRUPT = "__interrupt__"`） | 同款（**键名逐字相同**）⇒ 但**值的容器形态**为**元组**（上游 `invoke()` 为 **list**）⇒ 见 **X-1** | **DIFF**（容器形态 · 非更严） | 裁定 1 + B12F1 `data-model.md`（键的值 = 元组） |
| **P-05** | `.id` 由**内核自动生成**（用户**不**自带） | `langgraph/types.py:616-618`（`Interrupt.from_ns`）· `:607-612`（`xxh3_128_hexdigest`） · **实测 E-23**（命名空间 = `"{节点名}:{随机 uuid4}"`） | 同款（内核生成 · **不**要求用户自带 · 命名空间**含随机 uuid4** ⇒ **id 不可猜**）⇒ **摘要算法**不同（标准库 `blake2b-128` vs 上游 `xxh3-128`）⇒ 见 **X-4** | **DIFF**（算法 · 形态同款 · 非更严）⇒ ⇒ **偏离登记 = X-4**（**DIFF** · 必须自研区 ① · 零依赖硬约束） | 裁定 6 · 原则 XI ①「零依赖」自研区 · 澄清轮 Q5 |
| **P-06** | 中断**前**已产生的状态写入**不丢失** | — | 同款 | SAME | **实测 E-16**（`count=99` 保留 ⇒ 恢复后写出 `100`）· 裁定 8 |
| **P-07** | 同一轮**其它**节点的写入在挂起时**照常合并** | `langgraph/pregel/_runner.py:616-634`（`_should_stop_others`：「GraphInterrupts are not considered failures」） | 同款（沿用 B12F1 的 `V-16`） | SAME | **实测 E-21**（`messages=['ok']` 保留） |
| **P-08** | **未挂** checkpointer 时恢复 ⇒ **明确异常** | `langgraph/pregel/_loop.py:904-907`（`raise RuntimeError("Cannot use Command(resume=...) without checkpointer")`） | **消息要点逐字同款**；**类型**为 `InterruptError(reason="checkpointer_required")` ⇒ 见 **X-2** | **STRICTER**（结构化 + 属内核异常族） | 裁定 3 / 4 · **实测 E-3** |
| **P-09** | **多个**挂起中断 ⇒ 须**按 id** 指定恢复 | `langgraph/pregel/_loop.py:910-919`（`"When there are multiple pending interrupts, you must specify the interrupt id when resuming."`） | **消息要点逐字同款**；**类型**为 `InterruptError(reason="ambiguous_resume")` ⇒ 按 id 的映射形式同款 ⇒ 见 **X-2** / **X-3** | **STRICTER**（**失败信号** ⇒ **X-2**）· ⚠️ **识别规则**本身 = **DIFF**（**X-3** · 消除歧义 · **非更严**）| **实测 E-12 / E-19 / E-20** |
| **P-10** | **未提供**恢复值（`Command(resume=None)`） | ⚠️ **`UnboundLocalError`**（`langgraph/pregel/_loop.py:904-927` 的 `resume_is_map` 未绑定 ⇒ **上游缺陷**） | **抛** `InterruptError(reason="resume_value_required")` | **STRICTER**（上游缺陷 ⇒ 更确定） | 裁定 4 · 原则 XI ②「上游自身的缺陷」自研区 · **实测 E-13 / E-14** |
| **P-11** | 同一节点内**多个** `interrupt()` ⇒ 按**节点内顺序**匹配恢复值 | `langgraph/types.py:866-868`（docstring 逐字） | 同款（裁定 7） | SAME | **实测 E-17 / E-18** |
| **P-12** | 恢复值**不足** ⇒ **再次挂起**（**不**报错） | `langgraph/types.py:966-974`（无恢复值 ⇒ 再次 `raise GraphInterrupt`） | 同款 | SAME | **实测 E-17**（第二次恢复前仍挂起 · 载荷变成 `second?`） |
| **P-13** | 根图对中断的处置：**抑制** ⇒ 落进结果键（**不**抛给调用方） | `langgraph/pregel/_loop.py:1333-1339`（`if isinstance(exc_value, GraphInterrupt) and not self.is_nested: ... return True`） | 同款（**L2 内层**仍**合并抛出** · **根层**接住并转成结果键）⇒ **层次对应**（原则 XII） | SAME | B12F1 的 **D-1**（L2 抛 · 本 feature 转键）+ 裁定 10 |
| **P-14** | 中断轮**不产出**「跑完态」的结果 | `langgraph/pregel/_loop.py:1365-1377`（挂起时**只**写 `output`，**不**走完成分支） | 同款：挂起 ⇒ 返回 `InterruptResult`（**不是** `SuperStepResult`） | SAME | B12F1 裁定 24 / 裁定 8 |
| **P-15** | `invoke(None, config)` **不是**恢复入口（重挂起） | `langgraph/pregel/_loop.py:855`（注释称「None input: resume after interrupt」）但**实测**为**重挂起** | 同款：**非** `Command` 的输入走**首次运行**路径 ⇒ **不**触发恢复 | SAME | **实测 E-15**（`invoke(None)` 后中断载荷**原样**仍在） |
| **P-16** | 在图运行之外调用 `interrupt()` | `langgraph/config.py:26-29`（`raise RuntimeError("Called get_config outside of a runnable context")`） | **消息要点同款**；**类型**为 `InterruptError(reason="not_in_run")` ⇒ 见 **X-2** | **STRICTER**（结构化） | 裁定 3 · **实测 E-24** |
| **P-17** | 「真异常 + 中断同现」时，上游把中断元组写进 checkpoint 的 **pending writes**（**留痕**） | `langgraph/pregel/_runner.py:588-591` | 同款（**消息 / 异常类型**均照抄）⇒ ⇒ ⚠️ **但** freegraph v1 **无 checkpoint 实现** ⇒ ⇒ 那批中断元组**丢弃**（**MUST NOT** 自创留痕形态）⇒ ⇒ 属**阶段性**差异 ⇒ ⇒ **B14F1** 落地后**自动消解** | **DIFF**（阶段性 · **X-5**）| 裁定 11 · **实测 E-2e**（B12F1 取证） |

### §1.1 破冻结面冻结面的**上游对照**（宪法 v1.8.0「破冻结面的三条」第 ② 条）

> **要求**：某个 feature **必须**改动**已冻结**的契约面 / 符号面 / 冻结断言时 ⇒ ⇒ MUST 同时满足
> 三条 —— ① **回溯修订**冻结面的契约 + spec + 冻结断言；② 该 feature 的「**上游对照**表」MUST
> 写明「**上游有此项 ⇒ freegraph 原先缺**」或「**上游无此项 ⇒ 属自研区**」；③ **发起者追认**。

| 冻结面 | 上游有此项？ | 判定 |
|---|---|---|
| **`freegraph.runtime.__all__` 的**符号数冻结面**（20 ⇒ 23） | ❌ **上游无此项** | ⇒ ⇒ **属必须自研区 ③**（上游**没有** `runtime.__all__` 这个「L2 内部 API 导出面」的概念 —— 上游的 `langgraph/pregel/__init__.py` 不导出 `__all__` 清单）⇒ ⇒ ⇒ **零行为面偏离**（用户**看不见** L2 内部 API · 上游亦然）⇒ ⇒ 故**不**进 §4 偏离登记表（X-1…X-5 仍为 5 项）⇒ ⇒ ⇒ 但**冻结断言**仍 MUST **回溯修订**（§5 **T-1**）+ **发起者追认**（并入 V-1 的那一次） |
| **`SuperStepResult` 的四字段冻结面** | ✅ 上游**无**同名类型（上游的对应物是**状态字典**） | ⇒ ⇒ 属**必须自研区 ③**（freegraph 自有的结果对象）⇒ ⇒ **零改动**（§5 第二行）⇒ ⇒ **不构成偏离**（**层次对应优先于容器对应** · 原则 XII） |
| **`freegraph.runtime.errors` 的**符号面 + 异常类清单冻结面**（`__all__` 的**精确 7 元组** + `FreegraphError` 子类**精确清单** = 3 个） | ❌ **上游无此项**（上游**没有**「L2 内部 API 导出面」这个概念 —— `langgraph/errors.py` 无 `__all__` 清单） | ⇒ ⇒ 属**必须自研区 ③**（与 `runtime.__all__` 同源）⇒ ⇒ **零行为面偏离**（用户**看不见** L2 内部 API · 上游亦然）⇒ ⇒ 故**不**进 §4 偏离登记表（X-1…X-5 仍为 5 项）⇒ ⇒ ⇒ 但**冻结断言**仍 MUST **回溯修订**（§5 **T-1** 第 ④ 行）+ **发起者追认**（并入 V-1 的那一次）· **PR-8** |
| **门面 `interrupt` 的「未接线」测试冻结面**（`tests/facade/test_facade.py::TestInterrupt::test_raises_not_implemented` —— 断言门面 `interrupt` 恒抛 `NotImplementedError("interrupt 尚未接线（由 B10F1 交付）")`） | ❌ **上游无此项**（上游的 `interrupt` **立即可用** ⇒ 没有「未接线」态可断言） | ⇒ ⇒ 属**必须自研区 ③**（上游**没有**「占位未接线」这一中间态）⇒ ⇒ **零行为面偏离**（接线后 freegraph 的 `interrupt` 与上游**同款**）⇒ ⇒ ⇒ 但**冻结断言**仍 MUST **回溯修订**（§5 **T-1** 第 ⑤ 行）+ **发起者追认**（并入 V-1 的那一次）· **PR-8** |
| **`src/freegraph/_primitives.py` 的「未接线守卫」冻结面**（`tests/runtime/test_superstep_concurrency.py` 里 `assert "NotImplementedError" in primitives` —— 守「`interrupt` 仍未接线」） | ❌ **上游无此项**（上游**无**「门面私有模块 + 未接线占位」的形态） | ⇒ ⇒ 属**必须自研区 ③**（freegraph 自有的「占位 → 接线」中间态）⇒ ⇒ **零行为面偏离**（接线后该占位消失）⇒ ⇒ ⚠️ **实测**：该断言当前**仅靠** `_primitives.py` docstring 里残留的 "NotImplementedError" 字符串**侥幸通过** ⇒ ⇒ 一旦按 **PR-4** 删除实现体并清理 docstring ⇒ **必红** ⇒ ⇒ ⇒ 但**冻结断言**仍 MUST **回溯修订**（§5 **T-1** 第 ⑥ 行）+ **发起者追认**（并入 V-1 的那一次）· **PR-8** |

| **`freegraph.runtime.superstep.__all__` 的「精确列表」冻结面**（`tests/runtime/test_superstep_purity.py::test_importing_the_kernel_has_no_side_effects` —— 断言 `superstep.__all__` == **一份内联的 6 项精确列表**） | ❌ **上游无此项**（上游**没有** `runtime.superstep.__all__` 这个「L2 内部 API 导出面」的概念 · 上游的 `langgraph/pregel/__init__.py` 不导出 `__all__` 清单）⇒ ⇒ **属必须自研区 ③** ⇒ ⇒ **零行为面偏离**（用户**看不见** L2 内部 API · 上游亦然）⇒ ⇒ ⇒ **但**冻结断言**仍 MUST 回溯修订**（spec §5 **T-1** 第 ⑦ 处）+ **发起者追认**（并入 **V-1** 的那一次追认）· **PR-9**（**实施期实测新增**） |

⇒ ⇒ **本 feature 的破冻结面清单 = §5 的两行**（`runtime.__all__` 符号面 · 回溯修订；
`SuperStepResult` 四字段 · 零改动）**+ 2026-11-13 分析轮实测补入的 3 行**（`runtime.errors`
的符号面与异常类清单 · 门面 `interrupt` 的「未接线」测试 · `_primitives.py` 的「未接线守卫」
—— **三处 MUST 回溯修订** ⇒ 见 §5 · **PR-8**）**+ 2026-11-13 实施期实测再补入的 1 行**
（`superstep.__all__` 的「精确列表」—— **一处 MUST 回溯修订** ⇒ 见 §5 · **PR-9**）
⇒ ⇒ ⇒ **破冻结面清单 = §5 的 5 行「须回溯修订」+ §5 的 2 行「零改动 / 不回溯修订」**
⇒ ⇒ ⇒ （**契约**环节的处置见 **§5 表后的补记** —— 契约侧 **8 处**「仍 20」的**历史事实记录** ⇒ **不回溯修订**）
⇒ ⇒ **第 ③ 条（发起者追认）**并入 **V-1** 的那一次
⇒ ⇒ **追认次数仍为 1 次**（宪法 E-6）。

### §2 实测基线（**E-1…E-26** · `langgraph 1.2.11` · 取证于 2026-11-13）

| # | 实测项 | 观测结果 |
|---|---|---|
| **E-1** | 挂 checkpointer 的首次 `invoke`（中断） | 结果 = `{'messages': [], 'count': 0, '__interrupt__': [Interrupt(value='approve?', id='9b8b9782…')]}` ⇒ **`__interrupt__` 是 list** · 元素 = `Interrupt`（带 `.value` / `.id`） |
| **E-2** | `Command(resume="yes")` 恢复 | 结果 = `{'messages': ['answer=yes'], 'count': 1}` ⇒ **无** `__interrupt__`；节点执行计数 `[0, 0]` ⇒ **执行了两次** |
| **E-3** | **未挂** checkpointer + `Command(resume=...)` | `RuntimeError: Cannot use Command(resume=...) without checkpointer` |
| **E-4** | **未挂** checkpointer + 首次 `invoke`（中断） | 结果**照样**含 `__interrupt__` ⇒ **产出该键不依赖 checkpoint**（checkpoint 只管「恢复时还能读到」） |
| **E-5** | 同一节点两个 `interrupt()` 的首次执行 | 只**挂起一次**（第一个 `interrupt()` 即抛）⇒ `__interrupt__` 只有 **1** 个元素（`first?`） |
| **E-6** | 上一条 + 单值恢复 | **再次挂起**（载荷变成 `second?`）⇒ **不**报错（**实测 P-12**） |
| **E-7** | 上一条 + 按 id 的映射恢复（单 id） | `IndexError: list index out of range` ⇒ ⚠️ **上游缺陷**（映射分支的越界）⇒ freegraph **不**照抄该缺陷（§裁定 4 的映射规则以「全部 key 都是挂起 id」为准 ⇒ 该输入在本 feature 下会被当作**普通恢复值**） |
| **E-8** | 恢复时节点是否从起点重跑 | 副作用序列 `['enter']` → `['enter', 'enter', 'got yes']` ⇒ **前半段被再次执行**（**实测 P-03**） |
| **E-9** | `Interrupt.from_ns` 的 id | 32 位十六进制（如 `a9a47e0c558c063083061fbda0cb080d`）⇒ 与上游 `xxh3_128_hexdigest` **同长度** |
| **E-10** | `stream(stream_mode="updates")` 的中断块 | `{'__interrupt__': (Interrupt(...),)}` ⇒ **元组** ⇒ ⇒ 上游自身**两处形态不同**（`invoke` = list / `updates` = tuple）⇒ freegraph 统一为**元组**（**X-1**） |
| **E-11** | 两个节点同时中断 | `__interrupt__` 含 **2** 个元素 · `.value` 各自不同 · `.id` **互不相同** ⇒ **实测 P-05** |
| **E-12** | 跨节点多挂起中断 + 单值恢复 | `RuntimeError: When there are multiple pending interrupts, you must specify the interrupt id when resuming.` ⇒ **实测 P-09** |
| **E-13** | `Command(resume=None)` | ⚠️ `UnboundLocalError: cannot access local variable 'resume_is_map'` ⇒ **上游缺陷**（**实测 P-10**） |
| **E-14** | `Command()`（四位全 `None`） | ⚠️ 同上（`UnboundLocalError`） |
| **E-15** | `invoke(None, config)` | 结果与挂起时**完全相同**（中断载荷原样仍在）⇒ **不是**恢复入口（**实测 P-15**） |
| **E-16** | 中断前写入是否保留 | `pre` 写的 `count=99` 在挂起后仍在；恢复后节点读到 `99` 并写出 `100` ⇒ **实测 P-06 / SC-004** |
| **E-17** | 同节点多 `interrupt()` 的恢复匹配 | 恢复序列 `["a='X'", "a='X'", "b='Y'"]` ⇒ 第 1 个 `interrupt()` 拿第 1 个恢复值（**且被复用**）· 第 2 个拿第 2 个 ⇒ **实测 P-11 / P-12** |
| **E-18** | 再恢复一次 | 序列继续 `a='X'`（复用）· `b='Z'`（新值）⇒ 恢复值按**任务**累积 |
| **E-19** | 跨节点多挂起中断 + **按 id 的映射**恢复（不同通道） | 结果 = `{'a': 'A', 'b': 'B'}` ⇒ **映射形式可用**（**实测 P-09**） |
| **E-20** | 跨节点多挂起中断 + **部分** id 的映射 | 结果 = `{'a': 'A', '__interrupt__': [Interrupt(value='ask-B', …)]}` ⇒ 未指定的**仍挂起** |
| **E-21** | 中断轮里同轮其它节点的写入 | 结果 = `{'messages': ['ok'], '__interrupt__': [...]}` ⇒ **照常合并**（**实测 P-07**） |
| **E-22** | `CheckpointTuple` 的字段 | `config` / `checkpoint` / `metadata` / `parent_config` / `pending_writes` ⇒ `get_tuple` **一次调用**即得**快照 + pending writes** ⇒ freegraph 的读侧契约**一次调用**即可满足（裁定 9） |
| **E-23** | 中断任务的命名空间 | `ns = "{节点名}:{任务 uuid}"` ⇒ **含节点名** ⇒ ⇒ 不同节点 id 不同（**实测 P-05**） |
| **E-24** | 在图运行之外调用 `interrupt()` | `RuntimeError: Called get_config outside of a runnable context` ⇒ **实测 P-16** |
| **E-25a** | **未挂** checkpointer + `Command(resume=None)` | ⚠️ **不触达** checkpointer 检查（上游该检查**在 `if resume is not None` 之内** ⇒ `resume=None` ⇒ 整段跳过）⇒ ⇒ 落到 `resume_is_map` 未绑定 ⇒ ⚠️ `UnboundLocalError`（**上游缺陷** · 与 **E-13** 同源）⇒ ⇒ **上游既不报「缺 checkpointer」也不报「缺恢复值」** ⇒ ⇒ freegraph 的「**未提供恢复值优先**」（`resume_value_required`）是**更确定**的口径（原则 XI ②）|
| **E-25b** | **未挂** checkpointer + `Command(resume="yes")`（`resume` **非** `None`） | `RuntimeError: Cannot use Command(resume=...) without checkpointer`（= **E-3**）⇒ ⇒ **证明**：上游的 checkpointer 检查**只在 `resume is not None` 时才触达** ⇒ ⇒ 与 **E-25a** 合起来 ⇒ ⇒ **「未提供恢复值」必须先于「未挂 checkpointer」判定**（上游同款 · **实测**）|
| **E-26** | **「会话连续」路径（输入**非** `Command`）的两种形态**对比**（**2026-11-13 分析轮实测** · 图：`pre` → `ask`（`ask` 内 `interrupt("approve?")`）· 挂 `InMemorySaver` · 同一 `thread_id`） | ① **`invoke(None, cfg)`** ⇒ 结果**与挂起时完全相同**（`{'messages': [], 'count': 99, '__interrupt__': [Interrupt(value='approve?', id=**同一**)]}`）⇒ ⇒ **只重跑被中断的节点**（副作用序列 `['ask']` ⇒ `pre` **未**重跑）⇒ ⇒ **`.id` 逐字不变**（⇒ **续跑** · 检查点的**调度状态**被沿用）· **E-15 的「载荷原样仍在」在此得到确认**；② **`invoke({"messages": ["extra"], "count": 7}, cfg)`** ⇒ 结果 `{'messages': ['extra', 'extra'], 'count': 99, '__interrupt__': [Interrupt(..., id=**不同**)]}` ⇒ ⇒ 副作用序列 `['pre', 'ask']` ⇒ **`pre` 也重跑了**（⇒ 输入**写通道** ⇒ **通道版本推进** ⇒ 订阅节点**重新触发**）⇒ ⇒ **`.id` 变了**（⇒ 新的检查点 ⇒ 新的任务路径 ⇒ 新命名空间）⇒ ⇒ **不是**「续跑」⇒ ⚠️ ⇒⇒ **两种输入形态在上游行为不同** ⇒ ⇒ ⇒ **E-15 只覆盖 `None` 这一种** ⇒ ⇒ ⇒ **MUST NOT** 把二者合并成一行 |

### §3 差分场景组 *(mandatory)*

| # | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 |
|---|---|---|---|
| **DI-01** | 单节点中断 ⇒ 结果含 `__interrupt__` 且元素带 `.value` / `.id` | 上游从**结果键**取 · freegraph 从**挂起结果**取 ⇒ **集合比较**（不比顺序）⇒ 元素逐个断言 `.value` 相等 · `.id` **非空且 32 位十六进制**（**不**比具体值 —— 摘要算法不同 · **X-4**） | SAME |
| **DI-02** | `Command(resume=…)` 恢复 ⇒ 跑完且状态含恢复值 | 两侧的**最终状态**逐 key 相等 · 恢复值落在同一个 key 上 · 两侧**均无** `__interrupt__` | SAME |
| **DI-03** | 恢复时节点**从头重跑** | 节点内的**执行次数**（自增计数器）两侧**都 == 2** ⇒ **不**比较中间态 | SAME |
| **DI-04** | **未挂** checkpointer 时恢复 ⇒ **失败** | 两侧**都失败** ⇒ 判词 **STRICTER**（freegraph 的异常**类型**不同 ⇒ 差分探针只比「成功 / 失败」· **不**比异常类名 —— 比对器既有纪律） | STRICTER |
| **DI-05** | 中断**前**的写入**不丢失** | 两侧的**最终状态**逐 key 相等（中断前写入的那个 key 都在） | SAME |
| **DI-06** | 同一节点内**两个** `interrupt()` ⇒ 恢复值按**顺序**匹配 | 两侧的**最终状态**逐 key 相等（两个恢复值按序落位） | SAME |
| **DI-07** | 跨节点**两个**挂起中断 ⇒ `__interrupt__` **两个**元素 | **集合比较**（元素 `.value` 逐个相等）⇒ **不**比顺序（上游的合并顺序是竞态 · `langgraph/pregel/_runner.py:672`） | SAME |
| **DI-08** | 跨节点多挂起中断 + **单值**恢复 ⇒ **失败** | 两侧**都失败** ⇒ 判词 **STRICTER**（freegraph 的异常**类型**不同） | STRICTER |

⇒ **落点**：`tests/differential/parity_probe.py` ⇒ **CI 的 Linux 全量档真跑**
（上游缺席即 skip · 沿用 B5F2 的「缺席即 skip」纪律）。
⚠️ **既有差分场景（43 条 · 实测 `parity_probe._scenarios()`）逐字不变** ⇒ 本 feature 只**追加** **DI-01…DI-08**（**`DI-` 前缀** · 与既有 B12F1 / B7F4 的 `D-xx` **不重号**）。

### §4 偏离登记 *(三类：DIFF · STRICTER · 必须自研区 · 其余一律照抄)*

> ⚠️ **三态标注 MUST 一致（宪法 v1.12.0 原则 XI 补 · 2026-11-13 分析轮实测触发）** ——
> 本表与 §1「上游对照」表的**关系标注（`SAME` / `STRICTER` / `DIFF`）** MUST **逐字一致** ⇒ ⇒
> §1 标 **STRICTER** 的分叉 **MUST** 落在本表（并写明理由）⇒ ⇒ 本表的每一条 **MUST** 有 §1 的
> 对应行（**P-01…P-17**）⇒ ⇒ 两者 **MUST NOT** 各说各话 ⇒ ⇒ **判据零放宽**（只加**一致性**要求 ·
> **不新增门禁编号**）。
> ⇒ **本 feature 的映射（逐条可核）**：**P-04** ⇒ **X-1**（DIFF）· **P-05** ⇒ **X-4**（必须自研区 ①）·
> **P-08 / P-09 / P-10 / P-16** ⇒ **X-2**（STRICTER）· **P-09** 的识别规则 ⇒ **X-3**（DIFF）·
> **P-17** ⇒ **X-5**（DIFF · 阶段性）⇒ ⇒ **偏离总数 = 5**（与 §1 的分叉数**逐条相等**）。

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **DIFF（结构差异 · 非更严）** | `__interrupt__` 键的**值**的容器形态：上游 `invoke()` 返回 **list**（`langgraph/pregel/main.py:3951-3953`）· freegraph 返回**元组** | 上游自身**两处形态不同**（`invoke` = list · `updates` 流 = tuple · **实测 E-10**）⇒ freegraph **统一**为**元组** ⇒ 与 B12F1 的**中断载荷形态**（元组）一致 ⇒ **同类项同类承载**（原则 XII ③）· **不是**行为面的偏离 | 本 feature（**B10F1** · M1）· 追认 ≤ 1 次 |
| **X-2** | **STRICTER（失败信号更严 · 更结构化）** | 失败信号的**异常类型**：上游抛内置 `RuntimeError`（`langgraph/pregel/_loop.py:906` / `:917-919`）· freegraph 抛 `InterruptError`（`FreegraphError` 子类 · 带 `.reason`） | ① L1 的 `FreegraphError` docstring **冻结承诺**「上层只捕获基类 `FreegraphError` 即可兜住**全部**内核错误」⇒ 抛内置 `RuntimeError` 会**破坏**该承诺；② **可诊断性是一等功能**（宪法原则 IV）⇒ MUST NOT 让上层**解析消息文本**取细节 ⇒ **结构化 `reason`** 必备；③ **消息要点**与上游**逐字同款** ⇒ 用户可读性不降 | 本 feature（**B10F1** · M1）· 追认 ≤ 1 次 |
| **X-3** | **DIFF（结构差异 · 非更严 · 消除歧义）** | 「按 id 的恢复映射」的**识别规则**：上游用「全部 key 长得像 `xxh3_128` 摘要」（`langgraph/pregel/_loop.py:910-914`）· freegraph 用「**全部 key 都是当前挂起中断的 id**」 | 上游的启发式会把「恰好长得像摘要」的普通字典**误判**成映射（**实测 E-7** 的越界即源于此分支）⇒ freegraph 的规则**更精确** ⇒ 消除歧义（**非更严的失败信号**，而是**更准的识别**） | 本 feature（**B10F1** · M1） |
| **X-4** | **DIFF**（算法 · **必须自研区 ①** · 零依赖硬约束 · 非更严） | `.id` 的**摘要算法**：上游 `xxh3_128_hexdigest`（`xxhash` 包 · `langgraph/types.py:607-612` / `:618`）· freegraph 用标准库 `hashlib.blake2b(digest_size=16)`（⚠️ **命名空间形态与上游同款**：节点名 + **随机 uuid4** ⇒ ⇒ **仅**摘要算法不同 ⇒ **id 的不可猜性同款**）| 宪法「依赖白名单 / 黑名单」：**必装运行时依赖 = 无** ⇒ MUST **NOT** 引入 `xxhash` ⇒ 原则 XI ①「零账号 / 零主动出站 / 零依赖的硬约束」⇒ **自研优先**；⚠️ **形态仍同款**（**32 位十六进制** · **实测 E-9**）⇒ **id 的用途**（唯一定位一次中断）**不受影响** | 本 feature（**B10F1** · M1） |
| **X-5** | **DIFF（阶段性差异 · 消解条件已写死）** | 「真异常 + 中断同现」时上游把中断元组写进 checkpoint 的 **pending writes**（`langgraph/pregel/_runner.py:588-591`）⇒ **留了痕**；freegraph v1 **无 checkpoint 实现** ⇒ 那批元组**丢弃** | 该差异**源于「checkpoint 还没做」**（**B14F1 / M3**）⇒ 属**阶段性** ⇒ ⇒ **B14F1** 落地后**随 pending writes 留痕** ⇒ **自动与上游同款** ⇒ 本 feature MUST **NOT** 为此**自创**留痕形态（附注 / 调度状态字段）⇒ 原则 XI ③ | **B14F1** · **M3**（下游承接 **D-2**） |

### §5 破冻结面的回溯修订清单

> ⚠️ **本表共 7 行**（**5 行「须回溯修订」** · **2 行「零改动 / 不回溯修订」**）⇒ ⇒ 覆盖
> **7 处**冻结断言（行 1 = `runtime.__all__` 的 **3 处**代码断言 · 行 3–5 = **PR-8** 分析轮
> **实测**补入的 3 处 · 行 6 = **PR-9** **实施期实测**再补入的 1 处）⇒ ⇒ **七处 MUST 同改**
> （只改一处 ⇒ **pytest 必红**）。
> ⚠️ **「行数」与「处数」是两个口径** —— 6 行是**清单条目数**（含 2 行「不回溯修订」）·
> 6 处是**冻结断言的位置数**（行 1 占 3 处）⇒ ⇒ MUST NOT 混用（**2026-11-13 分析轮补齐**）。

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| **B12F1 `tasks.md` T072** 的「`freegraph.runtime.__all__` 的符号数 == **20**」**+** **三处**真正会红的**代码断言**（⚠️ 初版只登记了 ① —— **实测**另有 ② ③ ⇒ ⇒ 实现后 **pytest 必红** ⇒ 违反「MUST NOT 写**永久红**的 CI」）：① `tests/runtime/test_command_purity.py:255`（`assert len(runtime.__all__) == 20`）② `tests/runtime/test_superstep_concurrency.py:597`（`assert len(runtime.__all__) == 20`）③ `tests/runtime/test_read_contract.py:80`（`RUNTIME_SYMBOL_COUNT = 20`）+ `:547`（`assert len(runtime.__all__) == RUNTIME_SYMBOL_COUNT`）+ `:550`（`assert set(runtime.__all__) == {…20 个…}`） | ① `specs/b12f1-concurrency-errors/tasks.md` **T072** ⇒ 改为「与本 feature 的 `runtime.__all__` 清单**集合相等**」（**不硬编码数字** · 与该任务对 L1 符号面的既有做法**同款**）② 上述**三处**代码断言 ⇒ 同一改法（**断言集合** · **不**硬编码 23）③ `test_command_purity.py` / `test_read_contract.py` 的**函数名与 docstring**里的「twenty symbols」/「== **20**」**同步**（避免留下误导性命名）| **拆分而不删**（保留「集合相等」的判据形态 · 只去掉硬编码数字）⇒ ⇒ ⚠️ **判据零放宽**：仍是「**集合相等**」而非「≥ 20」 | 追认文字落 `harness/verification/B10F1/manual-verification.md`（**并入** V-1 的那一次追认 ⇒ **追认次数仍为 1 次**） |
| **B7F1 的 `run_super_step` / `run_super_steps` 签名与返回类型** | `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 | **零改动**（本 feature **另立**新入口 ⇒ 不改既有入口） | — |
| **`tests/runtime/test_read_contract.py::test_i9_the_reading_layer_adds_no_new_error_type`**（`runtime/errors.py` 的 `__all__` **精确 7 元组** + 其 `FreegraphError` 子类**精确清单** = 3 个） | ① `tests/runtime/test_read_contract.py:313-338` ⇒ 改为「`errors.__all__` **集合相等**（**允许**本 feature 新增的 `InterruptError`）」+「`FreegraphError` 子类清单**集合相等**（**允许** `InterruptError`）」 | **拆分而不删**（保留「符号面**零意外新增**」的判据形态 · 只去掉硬编码清单）⇒ ⇒ ⚠️ **判据零放宽**：仍是「集合相等」⇒ ⇒ ⚠️ **实测**：**无论** `InterruptError` 是否写进 `errors.__all__`，该测试**都必红**（第二段断言 AST 类清单）⇒ ⇒ ⇒ 新增的类型是**本 feature 的交付物**（契约 §1）⇒ ⇒ **T-1** 第 ④ 行 · **PR-8** | 追认文字落 `harness/verification/B10F1/manual-verification.md`（**并入** V-1 的那一次追认 ⇒ **追认次数仍为 1 次**） |
| **门面 `interrupt` 的「未接线」测试冻结面**（`tests/facade/test_facade.py::TestInterrupt::test_raises_not_implemented`） | `tests/facade/test_facade.py:315-330` ⇒ 改为「**接线后** `interrupt()` 抛 `InterruptError`（`reason="not_in_run"`）· **不再**抛 `NotImplementedError`」⇒ ⇒ 同步该类的 **docstring / 类名**（去掉「未接线（由 B10F1 交付）」措辞） | **拆分而不删**（保留「位置 / 关键字两种调用形态走**同一分支**」的判据形态）⇒ ⇒ ⚠️ **判据零放宽**：改为断言**新的**失败信号（**更具体**）⇒ ⇒ ⇒ ⚠️ **实测**：接线后该测试**必红** ⇒ ⇒ **T-1** 第 ⑤ 行 · **PR-8** | 追认文字落 `harness/verification/B10F1/manual-verification.md`（**并入** V-1 的那一次追认） |
| **`superstep.__all__` 的「精确列表」冻结面**（`tests/runtime/test_superstep_purity.py` 的 `test_importing_the_kernel_has_no_side_effects` —— 断言 `superstep.__all__` == **一份内联的精确列表**） | `tests/runtime/test_superstep_purity.py:122-146` ⇒ 改为「**与清单集合相等**」（清单 = `tests/runtime/_runtime_export_manifest.py` 的 `SUPERSTEP_EXPORT_SYMBOLS` · **单一事实源** ⇒ **不**硬编码数字）⇒ ⇒ ⚠️ **实测**：**实施期**按本 feature 的落地形态改动源码后跑既有测试 ⇒ **必红**（⇒ ⇒ **PR-9** · 宪法 v1.11.0「冻结断言清单 MUST 实测化」的**第二次**触发 ⇒ ⇒ 清单 **6 处 → 7 处**） | **拆分而不删**（保留「符号面**零意外新增**」的判据形态 · 只去掉硬编码清单）⇒ ⇒ ⚠️ **判据零放宽**：仍是「**集合相等**」（**不是**「⊇」）⇒ ⇒ ⚠️ 该断言**同时**守「导入调度内核**无副作用**」（零环境变量 / 零出站）⇒ ⇒ 那两条**保留** | 追认文字落 `harness/verification/B10F1/manual-verification.md`（**并入** V-1 的那一次追认 ⇒ **追认次数仍为 1 次**） |
| **`_primitives.py` 的「未接线守卫」冻结面**（`assert "NotImplementedError" in primitives`） | `tests/runtime/test_superstep_concurrency.py:790-795` ⇒ 改为「`_primitives.py` **只留 `Send`**（MUST NOT 含 `interrupt` 的实现体）」的**源码文本**断言（`"def interrupt" not in primitives`）⇒ ⇒ 同步该测试的 **docstring / 命名**（不再说「归 B10F1」） | **拆分而不删**（保留「占位**必须**被接线掉」的判据形态 · 从「文本里含 `NotImplementedError`」改成「**不含** `interrupt` 实现体」）⇒ ⇒ ⚠️ **判据零放宽**：新判据**更强**（定位到实现体本身）⇒ ⇒ ⇒ ⚠️ **实测**：当前**仅靠** docstring 残留字符串**侥幸通过**；按 **PR-4** 删实现体 + 清理 docstring 后**必红** ⇒ ⇒ **T-1** 第 ⑥ 行 · **PR-8** | 追认文字落 `harness/verification/B10F1/manual-verification.md`（**并入** V-1 的那一次追认） |
| **L1 `CompiledGraph.invoke` 的 `input` 注解**（`StateDict` ⇒ 须放宽为「状态字典或 `Command`」） | ⛔ **本 feature **不**回溯修订** —— **留到 B7F3**（澄清轮 Q3 · 发起者拍板）⇒ ⇒ 落在下游承接 **D-3** | **不动**（本 feature **不**触碰 L1 ⇒ G7 / G8 / G16 / G19 恒绿）⇒ ⇒ 风险：按 L1 协议编码的下游在 **B7F3** 之前**无法**按协议传 `Command`（**阶段性**限制 ⇒ 如实登记） | 由 **B7F3** 追认（**不在** B10F1 消耗本 feature 的唯一名额） |

> ⚠️ **「契约」环节的处置（2026-11-13 分析轮第二轮 · 补齐宪法 v1.8.0「破冻结面的三条」第 ① 条的**三个**环节）**：
> **契约侧**另有 **8 处**文档记载「`freegraph.runtime.__all__` **仍 20** / **零改动**」——
> `specs/b12f1-concurrency-errors/contracts/concurrency-contract.md:20` 与 `:32` ·
> `specs/b7f4-multisource-join/contracts/superstep-multisource-contract.md:15` / `:34` / `:45` ·
> `specs/b9f1-command-primitive/contracts/command-contract.md:14` 与 `:26` ·
> `specs/b7f1-superstep-loop/contracts/superstep-contract.md:15` 与 `:26`（记的是 **14 → 20**）
> ⇒ ⇒ **MUST NOT** 改写它们（**宪法原则 VIII**：「**已发布的事实 MUST NOT 改写**」——
> 它们是**各 feature 交付当时的历史记录**，而**不是**活约束）⇒ ⇒ 故**不回溯修订**，
> **理由 = 历史事实记录**（**≠「漏登记」**）⇒ ⇒ ⇒ **本清单至此穷举**
> （**契约 + spec + 冻结断言** 三环节齐备 · **宪法「破冻结面的三条」第 ① 条闭合**）
> ⇒ ⇒ **判据零放宽**（6 处冻结断言的处置**一字不改**）。

---

## Requirements *(mandatory)*

### Functional Requirements

#### A · 中断的产生与交还

- **FR-001**：系统 MUST 提供 `interrupt(value)` 函数（**位置或关键字**皆可 · **上游同款**）。
  首次调用（节点内 · 本次运行中该位置**尚无**可用的恢复值）时 MUST 抛出**可识别的**
  `GraphInterrupt`（L1 已冻结 · `freegraph.contracts.errors.GraphInterrupt`），其载荷 =
  **1-元组**（`tuple[Interrupt, ...]`），元素 = `Interrupt(value=value, id=<内核生成>)`。
  **MUST NOT** 修改 `GraphInterrupt` 的字段 / 构造签名 / 继承关系。

- **FR-002**：中断发生时，执行结果 MUST 含 **`__interrupt__`** 键（**键名逐字** =
  `"__interrupt__"` · 上游同款）；其值 = 被接住的那个 `GraphInterrupt.args[0]`（**元组**）·
  其元素 MUST 具备 `.value` 与 `.id` 两个**可读属性**（C17）；⇒ 元素 MUST **只**带这两个属性
  ⇒ **MUST NOT** 增加「节点名」等额外字段（**照抄上游 · 补记 F-3** · 上游 `Interrupt` 只有 `value` / `id`
  · `langgraph/types.py:593-597`）⇒ 「哪个节点要批准」由 L1 已有的 `StateSnapshot.tasks` 承载
  （生产者归 **B15F1** · 下游承接 **D-5**）。
  **MUST NOT** 把中断集合放进状态的稀疏字典里（形态污染 · B12F1 裁定 25 ③）。

- **FR-003**：`.id` MUST 由**内核自动生成**（MUST **NOT** 要求用户自带）⇒ 形态 =
  **32 位十六进制字符串**（非空）⇒ 派生自「**节点名 + 该节点本次「挂起 → 恢复」循环内的
  任务标识**」的命名空间 ⇒ 该任务标识 MUST 为**随机 uuid4**（标准库 `uuid`）⇒ ⇒ `.id`
  **不可猜**（恢复审批的能力凭据**不可被推导** · **上游同款** · **实测 E-23**）⇒ 摘要算法
  MUST 用**标准库**（`hashlib.blake2b(digest_size=16)`）⇒ **MUST NOT** 引入任何第三方依赖。
  **同一节点同一轮内**的多个 `interrupt()` **共享同一个** `.id`；**不同节点**的 `.id` MUST
  **互不相同**；⚠️ 该 `.id` MUST **跨恢复稳定** —— 标识**生成一次后随「中断载荷（`Interrupt` 对象）」
  持久化在 pending writes 里**（**零新增持久化字段**）· 恢复时**读回并复用**（**不重算**）⇒
  恢复时**读回**的值与先前**交给调用方**的那个**逐字相同**
  （**照抄上游 · 补记 F-1** · **实测 E-17**）；⚠️ **同一「挂起 → 恢复 → 再挂起」循环内**
  MUST **复用同一个**标识 ⇒ ⇒ 再次挂起时 `.id` 与第一次**逐字相同**（**澄清轮 Q5 拍板**）。

- **FR-004**：同一 super-step 内**多个**节点同时中断时，MUST **全部**交还
  （**一个都不丢**）⇒ `__interrupt__` 的元素集合与被中断的节点**一一对应**
  ⇒ MUST **NOT** 另写一条收集路径（直接复用 B12F1 的**合并抛出**语义）。

- **FR-005**：中断轮之后 MUST **不**再进入下一轮（**挂起**）⇒ MUST **NOT** 让被中断的
  节点被「幽灵触发」；⇒ 该轮**不产出**「跑完态」的结果（**挂起态**用专门的结果类型承载）。

- **FR-006**：挂起 MUST **不是回滚** ⇒ **中断前**已产生的状态写入 MUST **保留**；
  **同一轮内其它节点**的写入 MUST **照常合并**（沿用 B12F1 的「中断不是出错」口径）⇒
  恢复时被中断节点读到的入参 MUST 含那些写入。

- **FR-007**：一轮里**既有真异常又有中断**时，MUST **抛出真异常**、那批中断元组**丢弃**
  ⇒ ⇒ `__interrupt__` 键**只**承载「本轮**没有**真异常」时的中断集合 ⇒ MUST **NOT**
  自创留痕形态（附注 / 调度状态字段）。

#### B · 恢复

- **FR-008**：系统 MUST 支持 `Command(resume=...)` 作为**图的输入**（恢复输入）⇒ 恢复后
  节点里的 `interrupt(...)` MUST **返回** resume 值（**不**再次抛出中断）⇒ 节点据此继续跑完。

- **FR-009**：恢复 MUST **从被中断节点的起点重跑**（节点函数**整个重新执行**）⇒
  MUST **NOT** 保存局部变量、MUST **NOT** 从中断点继续 ⇒ 节点 MUST 靠 `interrupt()` 的
  **返回值**区分「首次执行」与「恢复执行」。

- **FR-010**：恢复 MUST **依赖 checkpointer** —— MUST **经由 checkpointer 读取被中断处的
  状态（**快照 + pending writes**）**并从节点起点重跑** ⇒ **MUST NOT** 提供
  「不挂 checkpointer 也能恢复」的**内存态旁路** ⇒ **MUST NOT** 在内核里持有任何
  「上一次运行的中断现场」（那正是内存态旁路）⇒ ⚠️ **「跨运行」**：MUST NOT **跨运行**持有（**本次运行内**从 checkpointer **读回**的现场**不在**此限 —— 那是「**经由 checkpointer**」的**结果**，不是旁路）。

- **FR-011**：编译产物 / 运行入口**未挂** checkpointer 时，调用恢复 MUST 抛**明确异常**
  （`InterruptError` · `reason="checkpointer_required"` · 消息 MUST 指明「恢复需要
  checkpointer」）⇒ MUST **NOT** 静默降级为内存态恢复。

- **FR-012**：挂起时 MUST 经由 checkpointer **写入**该会话的**快照**与**待写入**
  （含中断留痕）⇒ ⇒ 挂起态**可被再次恢复**（闭环**可重复**）⇒ 恢复过程中 MUST **NOT**
  在内核内存里另存一份「待恢复现场」。

- **FR-013**：`Command(resume=...)` 作为图输入的行为 MUST 写死为下表（**FR-006 的
  「未提供恢复值」口径在此闭合**）⇒ ⇒ ⚠️ **本表是「判定表」的**唯一事实源**（**裁定 4 只承载上游对照 · 不复制本表**）⇒ ⇒ **判定顺序**见 **裁定 4** 的「判定顺序」行 ⇒ ⇒ ⚠️ **分工声明**（2026-11-13 分析轮）：**本表 = 映射**（什么输入 → 什么行为）· **裁定 4 = 判定顺序**（先判哪一条）⇒ ⇒ ⇒ 两处**互补而不重叠** ⇒ ⇒ ⇒ 引用时 MUST 写全（「按 FR-013 的表 · 依裁定 4 的顺序」）。

  | 输入 | 挂起中断数 | 行为 |
  |---|---|---|
  | `resume` 为**标量** | == 1 | 用它恢复那一个挂起中断 |
  | `resume` 为**标量** | > 1 | 抛 `InterruptError(reason="ambiguous_resume")` |
  | `resume` 为 **dict** 且**全部 key 都是当前挂起中断的 id** | ≥ 1 | 按 id 逐个恢复（未被指定的**仍挂起**）⇒ ⚠️ **map 的「值」原样投递**给该节点（**上游同款** · `langgraph/pregel/_algo.py:1313-1314` 的 `task_resume_write.append(mapped_resume_write)` ⇒ ⇒ **标量即可**）⇒ ⇒ 该值 = 该节点**下一个** `interrupt()` 的恢复值（**不是**「节点内全部中断值的列表」）⇒ ⇒ 同一节点的**第 2 个** `interrupt()` 因「恢复值不足」⇒ **再次挂起**（裁定 7 · **上游同款** · **实测 E-17**）|
  | `resume` 为 **dict** 但 key **不**全是挂起中断的 id | == 1 | 该 dict 被当作**普通恢复值**（**不是** map）|
  | `resume` 为 **dict** 但 key **不**全是挂起中断的 id | > 1 | 抛 `InterruptError(reason="ambiguous_resume")`（**普通恢复值只能恢复一个** ⇒ 多挂起时**无法确定恢复哪一个** ⇒ 与标量同款）|
  | `resume` 为 **`None`**（未提供） | 任意 | 抛 `InterruptError(reason="resume_value_required")` |
  | `resume` 为 **`None`** 且**未挂** checkpointer | 任意 | 抛 `InterruptError(reason="resume_value_required")`（**未提供恢复值优先** · **上游同款** · **实测 E-25a / E-25b**：上游的 checkpointer 检查**在 `if resume is not None` 之内**⇒ `resume=None` 时**根本不触达** ⇒ ⇒ 故**先**判「未提供恢复值」）|
  | `resume` 为**空 dict**（`{}`） | 任意 | 归 **map** 分支（「全部 key 都是 id」**真空为真**）⇒ 恢复**零个** ⇒ 全部**仍挂起**（**不**报错）⇒ ⚠️ **结构锚点**（上游 `langgraph/pregel/_loop.py:910-914` 的 `all(...)` 同样**真空为真**）· **上游无实测取证** ⇒ ⇒ 故本行**不**写成可判定的行为断言 ⇒ ⇒ **SC / 差分场景 MUST NOT** 覆盖该输入（**如实登记**为「结构同款 · 未取证」）|
  | `Command(resume=…)` 与 `Command(update=…)` **同时**给出 | 任意 | `update` 走**通道写入**、`resume` 走**恢复通道** ⇒ 两者**并存**（**照抄上游** · 补记 **F-2**）⇒ ⇒ ⚠️ `update` 的通道写入**不**依赖 `resume` 的存在 ⇒ ⇒ **两者各自可判定** |
  | **非** `Command` 的输入且 `input` 为 **`None`**（`invoke(None, config)`） | — | 走**首次运行**路径（**不**要求 checkpointer、**不**触发恢复）；⚠️ 该 `thread_id` **已有历史快照** ⇒ ⇒ ⚠️ **续跑**（**上游同款** · **实测 E-26 ①**）：MUST **读该快照的 `.scheduler`** 重建调度状态 ⇒ ⇒ **不**写任何通道 ⇒ ⇒ **只有被中断的节点**重跑（其它节点**不**重跑）⇒ ⇒ 结果与挂起时**完全相同**（**E-15**）⇒ ⇒ `.id` **逐字不变**（**上游同款** · **实测 E-15 / E-26 ①**）· 补记 **F-1** · 裁定 6）⇒ ⇒ **不**消费 `__resume__` ⇒ ⇒ **不**触发恢复 |
  | **非** `Command` 的输入且 `input` 为 **`StateDict`** | — | 同走**首次运行**路径（**不**要求 checkpointer、**不**触发恢复）；⚠️ 该 `thread_id` **已有历史快照** ⇒ ⇒ MUST **读该快照的 `.scheduler`** 重建调度状态（**续跑** · **上游同款**）⇒ ⇒ 再把 `input` **按通道写入**叠加上去（**「叠加」的确切语义（2026-11-13 分析轮补齐 · 消除歧义）** = **按通道写入** · **覆盖型通道 ⇒ 覆盖** · **归约型通道 ⇒ 追加** ⇒ ⇒ **与 B5F1 的 `Channel.update` 同款** · **上游同款** · `langgraph/pregel/_loop.py:975-985` 的 `map_input`）⇒ ⇒ **MUST NOT** 另写一条叠加路径 ⇒ ⇒ ⚠️ **写通道 ⇒ 通道版本推进 ⇒ 订阅节点**重新触发** ⇒ ⇒ 因而被触及的节点会**重跑**（**上游同款** · **实测 E-26 ②**）⇒ ⇒ **`.id` 可变**（新的检查点 ⇒ 新的任务路径 ⇒ 新命名空间 · **实测 E-26 ②**）⇒ ⇒ **不**消费 `__resume__` ⇒ ⇒ **不**触发恢复 ⇒ ⇒ ⚠️ **两种输入形态在上游行为不同**（**实测 E-26**）⇒ ⇒ MUST **分两行**写死 |

- **FR-014**：该会话**没有**挂起的中断时提交恢复 MUST 抛**明确异常**
  （`InterruptError(reason="no_pending_interrupt")`）⇒ MUST **NOT** 静默当作「空状态从头跑」。

- **FR-015**：同一节点内**多个** `interrupt()` MUST 按**节点内的出现顺序**匹配恢复值
  ⇒ 恢复值**不足**时 MUST 在该处**再次挂起**（产生**新的**中断载荷）⇒ **不**报错。

#### C · 结构与边界

- **FR-016**：L2 MUST **只依赖 L1**（`freegraph.contracts`）⇒ **MUST NOT** import L4
  持久化层 / L5 可观测层的**实现** ⇒ 恢复路径 MUST **只**消费 L1 的 `Checkpointer` **协议**
  ⇒ （**导入图断言可判定** · 门禁 G25）。

- **FR-017**：本 feature MUST **只消费** L1 已冻结的类型（`Interrupt` / `GraphInterrupt` /
  `Command` / `RunConfig` / `StateSnapshot` / `Checkpointer`）⇒ MUST **NOT** 改写它们的
  字段、构造签名与注解 ⇒ ⇒ **L1 的 20 符号面零改动**（门禁 G7 / G8 / G16 / G19 恒绿）。

- **FR-018**：检查点的**读侧 / 写侧最小契约** MUST 是（裁定 9）：
  **读** —— `get_tuple(config)` 的返回值 MUST 暴露 `.snapshot`（L1 的 `StateSnapshot`）、
  `.pending_writes`（`(task_id, channel, value)` 三元组序列）**与** `.scheduler`（**调度账本** · 纯数据 ·
  可 JSON 序列化 · 承载 `versions_seen` / `channel_versions` / `node_versions` / `dynamic_edges`）
  ⚠️ **`.scheduler` 是 plan 阶段回修新增**（**PR-1**）⇒ 初版只列两个属性 ⇒ 与 **H-5 ⑤**「恢复 MUST 重建
  调度状态」自相矛盾 ⇒ ⇒ **不是 L1 冻结面** ⇒ ⇒ **L1 零改动** ⇒ ⇒ 澄清轮 **Q3** 的拍板仍成立；**写** ——
  `put(config, values=..., metadata=...)` 与
  `put_writes(config, writes=..., task_id=..., task_path=...)`；保留通道名 =
  `__interrupt__` / `__resume__`。
  ⚠️ **恢复轮的「显式首轮 / 触发后续轮」分工（口径写死 · 消除歧义 · 2026-11-13 分析轮补齐）**：
  **第 1 轮** = **显式**跑 `.snapshot.next` 的节点（**不走**触发判定 · **上游同款** ·
  `prepare_next_tasks` 按 checkpoint 的 `next` 重建）⇒ **第 2 轮起** = 用 `.scheduler`
  **重建**的调度状态走**触发判定**（⇒ 恢复后的后续轮触发判定与首次运行**同款** · **H-5 ⑤**）
  ⇒ ⇒ `.scheduler` **MUST NOT** 被当作「第 1 轮的触发判定输入」。

- **FR-019**：本 feature MUST **NOT** 交付任何 checkpointer **实现**
  （`MemorySaver` 属 B14F1 · `SqliteSaver` 属 B15F1）⇒ 本 feature 的测试 MUST 用
  **桩**（记录调用的测试替身）判定「恢复确实经由 checkpointer」。

- **FR-020**：本 feature MUST 在 L2 新增**一个**入口用于「首次运行 / 恢复」⇒ 其返回类型
  = `SuperStepResult | InterruptResult` ⇒ 既有入口 `run_super_step` / `run_super_steps`
  的**签名与返回类型 MUST 一字不动**（B7F1 冻结面）。

- **FR-021**：本 feature MUST **NOT** 改动既有 `SuperStepResult` 的**字段数**（**四字段**）
  ⇒ MUST **NOT** 新增第 5 个字段（MUST NOT 塞进 `state`）⇒ 挂起态由 `InterruptResult`
  承载，且 `InterruptResult` MUST 提供把中断集合转成 **`__interrupt__` 键**的转换
  （转成路径**只此一条**）。

- **FR-022**：恢复轮的写入 MUST 继续走 B7F1 的**批量**合并路径（每通道**一次**
  `Channel.update(values)`）⇒ MUST **NOT** 为恢复另写一条合并路径；恢复轮的**步末清空**
  MUST 与首次运行**同款**。

- **FR-023**：本 feature MUST **NOT** import `langchain` / `langchain-core` /
  `langgraph*` / `langsmith` / 任何第三方包 ⇒ MUST **NOT** 读任何环境变量 ⇒
  MUST **NOT** 有任何出站。

- **FR-024**：本 feature MUST **NOT** 实现：静态中断点 `interrupt_before` / `interrupt_after`
  （B13F1）· `recursion_limit`（B13F1）· `Send`（B11F1）· `async`（v2）· 子图（C26 · v2）·
  checkpointer 的任何实现（B14F1 / B15F1）· agent 层审批 UI（freechain）。

- **FR-025**：`interrupt()` 在**图运行之外**被调用时 MUST 抛**明确异常**
  （`InterruptError(reason="not_in_run")`）⇒ MUST **NOT** 静默返回 `None`。

- **FR-026**：本 feature MUST **更新** API 兼容矩阵中 `interrupt` 符号的那一行 ⇒ ⇒ **MUST NOT**
  增删兼容矩阵的**行**（门面 7 个符号**各恰一行** · 门禁 **G19** 的判据**零放宽**）⇒ ⇒ 更新
  内容 MUST 与本 feature 的**实际落地状态一致**（由「**中断 / 恢复行为待 B10F1 交付**」改为
  「**中断 / 恢复行为已落地**（B10F1）」）⇒ ⇒ 落点 = `README.md` 的「**API 兼容矩阵**」章节
  （⚠️ **该章节已入库** —— 由 B2F1 / B2F2 起**逐符号累积** · **终版**归 **B24F1 / M4**
  ⇒ ⇒ **不是**「首次落库」⇒ ⇒ **本 feature 可达成** ⇒ ⇒ **不**属「物理不可达成」
  ⇒ ⇒ **不**登记偏离）⇒ ⇒ ⚠️ `THIRD_PARTY_NOTICES` **无需更新**（本 feature **零**新增第三方
  代码 ⇒ **零**新增依赖 ⇒ 原则 X 的归属清单**零新增行**）⇒ ⇒ 落地任务见 `tasks.md` **T054**。

### Key Entities

| 实体 | 语义 | 关键属性 | 归属 |
|---|---|---|---|
| **`interrupt(value)`** | 节点内的「请求外部输入」原语 | 返回**恢复值**（`Any`）· 首次调用抛 `GraphInterrupt` | 门面导出名（**7 符号面零改动**）· **实现体**在 `src/freegraph/runtime/_interrupt.py`（**L2** · **PR-4**）· 门面 `graph.py` **模块级**转出 |
| **`GraphInterrupt`** | 可识别的中断异常（**上游同款**） | `.payload` = `tuple[Interrupt, ...]` · `args[0]` = 同一序列 | **L1 已冻结**（`contracts/errors.py`）· 只消费 |
| **`Interrupt`** | 一次中断的载荷 | `.value`（用户给的内容）· `.id`（**内核自动生成** · 32 位十六进制） | **L1 已冻结**（`contracts/types.py`）· 只消费 |
| **`__interrupt__`** | 执行结果中的**中断集合** | 键名 `"__interrupt__"` · 值 = **元组** · 元素 = `Interrupt` | 结果字典（**门面层**）· 键名由本 feature 冻结 |
| **`Command(resume=...)`** | 恢复输入 | `.resume`（`Any \| None`）· 其余三位 = B9F1 的 `goto` / `update` / `graph` | **L1 已冻结**（`contracts/types.py`）· 只消费 |
| **`InterruptResult`** | **挂起态**的结果对象 | `.state`（稀疏状态）· `.interrupts`（元组）· `.executed`（节点名序列）· `.steps`（**如实计**的实际轮数） | **本 feature 新增**（L2 内部 API） |
| **`InterruptError`** | 中断 / 恢复路径的**失败信号** | `.reason`（封闭取值域的 5 个码） | **本 feature 新增**（L2 内部 API） |
| **检查点读侧 / 写侧最小契约** | 本 feature 与 checkpointer 实现之间的**接缝** | 读：`.snapshot`（`StateSnapshot`）+ `.pending_writes` · 写：`put` / `put_writes` | 本 feature 定义 · **B14F1** 兑现（下游承接 **D-1**） |
| **恢复值（resume value）** | 外部提交的输入 | 标量或**按 id 的映射**（`{interrupt_id: 值}`） | 调用方 → `Command(resume=...)` |

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

| # | 判据 | 判定方式 |
|---|---|---|
| **SC-001** | 中断后结果含 `__interrupt__`，其元素的 `.value` 与 `.id` **均可读** | 断言 `result["__interrupt__"][0].value == "approve?"` 且 `.id` 是 32 位十六进制（**100%** 的中断用例） |
| **SC-002** | `Command(resume=...)` 之后图执行到**结束态**且状态含 resume 值 | 断言二次执行结果**无** `__interrupt__` 且状态里含 resume 值 |
| **SC-003** | 恢复时节点函数**被重新完整执行** | 节点内自增计数**观察到第 2 次进入**（**不**只断言「跑完了」） |
| **SC-004** | 中断前已产生的状态写入**不丢失**（挂起不是回滚） | 断言挂起后状态里那些写入仍在；恢复后节点读到的入参含它们 |
| **SC-005** | **恢复路径确实经由 checkpointer** | 用「记录 checkpointer 调用」的**桩**判定：恢复时 MUST 读到该 `thread_id` 的**快照 + pending writes**；未挂 checkpointer 时 MUST **抛明确异常**（**非**静默降级） |
| **SC-006** | L2 **不** import L4 的实现（只依赖 L1 冻结的 `Checkpointer` 协议） | **导入图断言**可判定（门禁 G25 的层注册表） |
| **SC-007** | L1 的**公开符号面零改动**（**20** 个） | 门禁 G7 / G8 / G16 / G19 恒绿（逐字相等） |
| **SC-008** | 「真异常 + 中断同现」时抛**真异常**、中断元组**丢弃** | 断言抛出的异常**是**那个真异常（类型 + 消息原样）且结果里**读不到**那批中断 |
| **SC-009** | 同一 super-step 内**多个**节点中断 ⇒ **全部**交还 | 断言 `__interrupt__` 的元素数 == 被中断节点数，且 `.value` 逐个对得上 |
| **SC-010** | 挂起时 `steps` **如实计**「实际跑过的轮数」 | 断言挂起结果的 `steps` == 实际跑过的轮数（**含**被中断的那轮 · **不含**那个空轮） |
| **SC-011** | 未挂 checkpointer 时恢复 ⇒ **明确异常** | 断言异常**类型**是 `InterruptError` 且 `.reason == "checkpointer_required"` 且消息指明「恢复需要 checkpointer」 |
| **SC-012** | 「未提供恢复值」的行为**写死且可判定** | 断言 `Command(resume=None)` / `Command()` ⇒ `InterruptError(reason="resume_value_required")` |
| **SC-013** | 恢复后图**再次挂起** ⇒ 可**再次**恢复（闭环可重复） | 断言第二次挂起产生**新的**中断载荷，且第三次提交恢复值后跑完 |
| **SC-014** | 同一节点内**多个** `interrupt()` 按**节点内顺序**匹配恢复值 | 断言第 1 个恢复值落在第 1 个 `interrupt()`、第 2 个落在第 2 个；恢复值不足 ⇒ **再次挂起**（**不**报错） |
| **SC-015** | 跨节点多挂起中断 ⇒ 单值恢复 **失败**；按 id 的映射恢复 **成功**（⚠️ 映射的**值** = **原样投递**给该节点（**标量即可** · **上游同款** · `langgraph/pregel/_algo.py:1313-1314` 的 `task_resume_write.append(mapped_resume_write)`）⇒ ⇒ 该值 = 该节点**下一个** `interrupt()` 的恢复值（**不是**「节点内全部中断值的列表」）—— 形状见 **FR-013** 表 ⑥ 行 · **裁定 4** ⑥ · research **DR-11**）| ⚠️ **两端各须有独立断言**（**缺一即不算达成**）：① 单值 ⇒ `InterruptError(reason="ambiguous_resume")`；② 按 id 的映射（**值原样投递**）⇒ 未指定的**仍挂起**、指定的**已恢复** ⇒ ⇒ **兼容断言**：同一用例另以 `{id: [值]}`（列表形态）再跑一次 ⇒ ⇒ 节点拿到的**就是那个列表** ⇒ ⇒ **两种形态都合法**（**不**强制列表）⇒ ⇒ 落地任务见 `tasks.md` **T052** |
| **SC-016** | 差分场景 **DI-01…DI-08** 全部符合判词 | `tests/differential/parity_probe.py` 的 Linux 全量档**真跑**（上游缺席即 skip） |
| **SC-017** | **零**第三方依赖 / **零**环境变量 / **零**出站 | 门禁 G21 / G22 / G23 / G24 / G26 / G27 恒绿 |
| **SC-018** | **依赖门禁**（阻断 · 红线） | 依赖树无 `langsmith` / `langchain*` / `langgraph*`（含**差分测试侧**的隔离断言 G22） |
| **SC-019** | **契约门禁**：C4 / C6 / C8 **零破坏** | ① **只读基准零改动**：`harness/demo/target.py` 与入库基准（`git show HEAD:…`）**逐字相同**（门禁 **G29** ①）⇒ **MUST NOT** 改它；② **验收脚本集**（`graph_core` / `agent_loop` / `visualization`）在门禁 **G29** ② 的**失败来源分级**下判为「**环境未就绪** ⇒ 通过」（退出码 ∈ **{0, 1, 2}** 且**全部**失败行源于 `NotImplementedError`）⇒ ⇒ **不**要求「真跑」（「真跑」属 **B7F2 / B7F3 · M2** ⇒ 见**偏离登记 V-4**）；③ **C4** 的独立回归测试**恒绿**（`tests/contracts/test_contract_regressions.py` 的挂载点 `status=landed`）；④ **C8** 的挂载点**保持** `status=not-landed · owner=B8F1 · milestone=M2`（**MUST NOT** 改写成 `landed`）⇒ ⇒ **门禁 G29 的三条判定恒绿** |
| **SC-020** | **人工门禁**：`harness/verification/B10F1/manual-verification.md` **五段式齐全**（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）⇒ ⚠️ 其中四处按 §门禁项的偏离登记 **V-1**（恢复侧真跑一轮 · → B14F1 / M3）· **V-2**（fake 模型跑通固定脚本一轮 · → B7F3 / M2）· **V-3**（真实模型再跑一轮 · → B7F3 / M2）· **V-4**（契约门禁的「`target.py` **真跑**」部分 · → B7F3 / M2）**延期**（已登记 + 待发起者追认）⇒ **已达成部分**（本 feature 自身的**挂起侧**人工验证 · 走 L2 入口）**照常**达成 ⇒ ⇒ ⚠️ 另须附（立项书 **§9.3**）：① 依赖断言轮的输出（隔离 venv 的依赖闭包清单 + `sys.modules` 检查结果）② 「框架出站」计数为 **0** 的监测记录 ③ 反向断言结果（运行期未 import `langchain`） | 文件存在且五段齐全（MUST **NOT** 伪造未实跑的输出）+ 偏离登记 **V-1 / V-2 / V-3 / V-4** 的四要素齐备 + **追认文字**落盘（**一次**打包）+ §9.3 的三份附件齐备 |
| **SC-021** | **证据门禁**：中断与恢复语义**标注源码行号** | 每条上游断言带 `langgraph 1.2.11` + `路径:行号`；**行为**断言带**实测**编号（E-1…E-26） |
| **SC-022** | **文档合规门禁**：API 兼容矩阵**已更新**（宪法原则 X · 质量门禁 7） | README「API 兼容矩阵」章节的 `interrupt` 行 MUST 由「**中断 / 恢复行为待 B10F1 交付**」更新为「**中断 / 恢复行为已落地**（B10F1）」⇒ ⇒ 门禁 **G19**（兼容矩阵**覆盖门面 7 个符号** · 各恰一行）+ 门禁 **G8** **恒绿**（判据零放宽）⇒ ⇒ ⚠️ **MUST NOT** 增删兼容矩阵的**行** |

### 门禁项的**偏离登记**（宪法 v1.6.0「质量门禁的分阶段落地」）

> ⚠️ **本表登记的是「**门禁项**的不可达成」**——不是**「上游差异」（后者在 §Upstream Parity §4）。
> ⚠️ **编号沿用既有 V-1**（避免打乱既有引用）⇒ ⇒ **四项**的**门禁序**见各行。
> ⚠️ **四项的追认打包为**同一次**（宪法 E-6：「追认次数每 feature MUST ≤ 1 次」）⇒ ⇒ 落
> `harness/verification/B10F1/manual-verification.md` 的**同一次**追认。
> ⇒ ⇒ ⚠️ **该次追认同时覆盖**：破冻结面回溯修订 **T-1**（**6 处**冻结断言 · **PR-8** 分析轮实测扩容）
> + 范围变更 **PR-6**（**+40** 行）· **PR-7**（**+60** 行）⇒ ⇒ **追认次数仍为 1 次**。

| # | 被偏离的**具体门禁项** | 不可达成的**根因**（含里程碑依据） | 判据**未被放宽**的论证 | 承接方 / 承接机制 | 追认 |
|---|---|---|---|---|---|
| **V-1** | **人工门禁**（宪法质量门禁第 5 条 + 原则 V）的「**恢复侧真跑一轮**」部分 —— 即「挂**真实** checkpointer → 中断 → `Command(resume=…)` → 跑完」这一轮 | **本 feature 按里程碑不交付其前置能力**：可用的 checkpointer 实现（`MemorySaver`）属 **B14F1 / M3**（L4 持久化层）⇒ 而本 feature 在 **M1**（L2 执行内核层）⇒ ⇒ M1 **物理不可达成**（本 feature **刻意不实现**任何 saver · FR-019 / Out of Scope 第 1 条） | ① **红线判据一律照常执行**：依赖门禁（无 `langsmith` / `langchain*` / `langgraph*`）、零环境变量、零出站、L1 符号面零改动、架构导入图 —— **全部照常**落地（SC-006 / SC-007 / SC-017 / SC-018）⇒ **未放宽任何红线判据**；② 恢复路径**本身**（读快照 + pending writes → 从节点起点重跑）**已**用**桩**（记录调用的测试替身）**可判定**（SC-005）⇒ ⇒ **不可达成的只是「用真实 saver 跑那一轮」**，**不是**「恢复语义没有验证」；③ **MUST NOT** 写**永久红**的 CI ⇒ 承接项**具名**且**有里程碑**（**B14F1 / M3**）⇒ 非无期限悬空 | **B14F1** · **M3**（下游承接 **D-1**）· 承接机制 = B14F1 落地 `MemorySaver` 后，在 B14F1 的 `manual-verification.md` 补上「**恢复侧真跑一轮**」的实测输出 | **发起者本人**在 `harness/verification/B10F1/manual-verification.md` 落**追认文字 + 确认 + 日期**（**未追认前 MUST NOT 合入** · **MUST NOT** 由实现者代签）· ⚠️ **澄清轮 Q4 · 发起者拍板**（登记档位 **A** · 2026-11-13 分析轮拍板）· ⚠️ **该次追认同时覆盖破冻结面回溯修订 T-1 的 6 处冻结断言 + PR-6 / PR-7 的范围变更** |
| **V-2** | **自动门禁**（宪法质量门禁第 4 条）+ **原则 V 的第 1 轮**（**fake / 伪模型跑通 MVP 验收基线的一轮**） —— 即跑 `harness/demo/target.py` 等固定脚本 | **本 feature 按里程碑不交付其前置能力**：固定脚本需 `compile()` + `invoke()`（`harness/demo/target.py:158,168`）⇒ 属 **B7F2 / B7F3**（**M2**）⇒ 而本 feature 在 **M1**（L2 执行内核层）⇒ ⇒ **M1 物理不可达成** | ① **红线判据一律照常执行**（依赖门禁 · 零环境变量 · 零出站 · L1 符号面 · 导入图）⇒ ⇒ **未放宽任何红线判据**；② 门禁 4 的**其余**部分（**CI 全绿** + 门禁 **G1–G30**）**照常**执行；③ **MUST NOT** 写**永久红**的 CI ⇒ 承接项**具名**且**有里程碑** ⇒ 非无期限悬空 | **B7F3** · **M2**（下游承接 **D-8**）· 承接机制 = B7F3 落地 `invoke()` 后，在 B7F3 的 `manual-verification.md` 补上「fake 模型跑通验收基线的一轮」的**实测输出** | **发起者本人**在 `harness/verification/B10F1/manual-verification.md` 落**追认文字 + 确认 + 日期**（**未追认前 MUST NOT 合入** · **MUST NOT** 由实现者代签）· ⚠️ **2026-11-13 分析轮拍板**（登记档位 **A**） |
| **V-3** | **人工门禁**（宪法质量门禁第 5 条）+ **原则 V 的第 2 轮**（**真实模型再跑一遍**） —— 即固定脚本在**真实模型**下再跑一轮 | **同 V-2 的根因**：固定脚本需 `compile()` + `invoke()` = **B7F2 / B7F3**（**M2**）⇒ ⇒ **M1 物理不可达成**（且本 feature **不涉及任何模型调用**） | **同 V-2** 的 ①②③ | **B7F3** · **M2**（下游承接 **D-8**）· 承接机制 = 同 **V-2**（在 B7F3 的 `manual-verification.md` 补上真实模型那一轮的**实测输出**） | 同 **V-2**（**同一次**追认打包 ⇒ **追认次数仍为 1 次**） |
| **V-4** | **契约门禁**（宪法质量门禁第 3 条）的「**`harness/demo/target.py` 原样可跑**（**真跑**）」这一部分 —— 即固定脚本在**真实内核运行时**下的完整跑通（**非**「环境未就绪」分级） | **本 feature 按里程碑不交付其前置能力**：`target.py` 需 `compile()` + `invoke()`（`harness/demo/target.py:158,168`）⇒ 属 **B7F2 / B7F3**（**M2**）⇒ 而本 feature 在 **M1**（L2 执行内核层）⇒ ⇒ **M1 物理不可达成**（本 feature **刻意不实现**门面 `invoke` · Out of Scope 第 8 条） | ① **只读基准零改动**这一条**照常执行**（门禁 **G29** ① ⇒ **MUST NOT** 改 `target.py`）⇒ ⇒ **未放宽任何红线判据**；② **验收脚本集**在门禁 **G29** ② 的**失败来源分级**下判为「**环境未就绪** ⇒ 通过」（⇒ **MUST NOT** 写**永久红**的 CI）⇒ ⇒ **门禁 G29 的三条判定全部可判定且恒绿**；③ **C4** 的独立回归测试**恒绿**（挂载点 `status=landed`）；④ **C8** 的挂载点**保持** `not-landed · owner=B8F1`（**MUST NOT** 伪装成 `landed`）；⑤ **判据零放宽**：承接方落地时**照原判据**执行（「`target.py` 原样**真跑**」⇒ 全绿）⇒ ⇒ **MUST NOT** 写**永久红**的 CI | **B7F3** · **M2**（下游承接 **D-3** 已含 `invoke` 接线）· 承接机制 = B7F3 落地 `invoke()` 后，在 B7F3 的 `manual-verification.md` 补上「**`target.py` 原样真跑一轮**（fake 模型轮）」的**实测输出** ⇒ ⇒ 与 **V-2**（门禁 4 的 fake 轮）**同棒承接** | **发起者本人**在 `harness/verification/B10F1/manual-verification.md` 落**追认文字 + 确认 + 日期**（**未追认前 MUST NOT 合入** · **MUST NOT** 由实现者代签）· ⚠️ **同一次**打包（**追认次数仍为 1 次** · 宪法 E-6）|

> ✅ **已达成部分（**不**属偏离 · MUST 照常做）**：本 feature **自身的**人工验证 —— 即
> 「用 **L2 入口**（`run_graph`）跑**挂起侧**」的**实测输出**（**五段式**照常齐全 · 见 **SC-020**）
> —— **照常达成** ⇒ ⇒ 「**不可达成的**」仅限两处：**固定脚本那一轮**（需门面 API · B7F2 / B7F3）
> 与**恢复侧那一轮**（需真实 saver · B14F1）⇒ ⇒ **MUST NOT** 把「本 feature 未跑固定脚本」
> 写成「本 feature 未验证」。

### 验收判据（= 立项书 §5.2 B10F1 小目标 · 逐条可判定）

> 小目标原文：**HITL 中断/恢复闭环；从节点起点重跑**

| # | 判据 | 判定方式 | 对应 SC |
|---|---|---|---|
| **A1** | **HITL 中断/恢复闭环** | 中断 → `Command(resume=)` → 跑到结束，状态含 resume 值 | SC-001 / SC-002 |
| **A2** | **从节点起点重跑** | 节点内计数证明第二次进入节点是**重新执行** | SC-003 |
| **A3** | **`__interrupt__` 含 `.value` / `.id`** | 断言（C17） | SC-001 |
| **A4** | **恢复须挂 checkpointer** | ① 挂 checkpointer 的用例：恢复确实读到了**快照 + pending writes**；② 未挂 checkpointer 的用例：**抛明确异常**（非静默降级） | SC-005 / SC-011 |

---

## Out of Scope（本 feature 明确不做）

1. **checkpointer 的任何实现**（`MemorySaver` → B14F1 · `SqliteSaver` → B15F1）⇒ 本 feature
   只定义并消费**读侧 / 写侧最小契约**（FR-018）。
2. **静态中断点** `interrupt_before` / `interrupt_after`（→ B13F1）。
3. **`recursion_limit`**（→ B13F1）。
4. **`Send`**（→ B11F1）。
5. **async**（v2 范围）。
6. **子图 / `Command.PARENT`**（C26 · v2）。
7. **`StateSnapshot` 的生产者**（`get_state()` → B15F1）⇒ 本 feature 只**消费**该类型作为
   快照载体。
8. **对外 `invoke()` API 的接线**（→ B7F3）⇒ 本 feature 只提供 L2 的入口与
   `InterruptResult.as_result_dict()` 的转换（转成路径**唯一**）。
9. **`compile(checkpointer=...)` 的门面接线**（→ B7F2）⇒ 本 feature 的 L2 入口
   **显式**接收 checkpointer。
10. **agent 层审批 UI / 通知**（→ freechain）。
11. **`update_state` / 时间旅行 / 分叉**（→ B16F1）。
12. **可观测层（span / trace）的中断标注**（→ B18F1 / B19F1）⇒ 本 feature **零**可观测面改动。
13. **兼容矩阵的**新增行** 与 `THIRD_PARTY_NOTICES` 的新增条目**（终版归 **B24F1 / M4**）⇒ ⇒
    ⚠️ **但**本 feature MUST **更新**兼容矩阵中 `interrupt` **那一行**（**FR-026** · **SC-022**
    · `tasks.md` **T054**）⇒ ⇒ **不是**「矩阵无需更新」⇒ ⇒ `THIRD_PARTY_NOTICES` **零新增行**
    （本 feature **零**新增第三方代码 ⇒ **零**新增依赖 ⇒ 原则 X 的归属清单**零改动**）。
14. **L1 `CompiledGraph.invoke` 的 `input` 注解放宽**（→ B7F3）⇒ ⚠️ **澄清轮 Q3 · 发起者拍板**：
    **B10F1 刻意不破**该 L1 冻结面 ⇒ ⇒ 下游承接 **D-3**（由 B7F3 破 + 追认）⇒ ⇒
    **阶段性限制**（如实登记）：按 L1 协议编码的下游在 **B7F3** 之前**无法**按协议传 `Command`。
15. **`src/freegraph/_primitives.py` 里的 `interrupt` 实现体**（⚠️ **PR-4**）⇒ ⇒ 该文件
    **只留 `Send`**（**零** `interrupt`）⇒ ⇒ **MUST NOT** import `runtime/`（**跨注册表条目的
    同层 import** ⇒ 门禁 **G25** 判红 · **实测**）⇒ ⇒ `interrupt` 的**运行期机制**归
    `src/freegraph/runtime/_interrupt.py`（**L2 目录条目内**）。
16. **多中断的「一次性全部恢复」UX**（如按 id 的映射在**门面层**的封装）⇒ 只提供原语。

---

## Assumptions

1. **B9F1 已落地**且 `Command` 的 `resume` 位**已存在**（L1 冻结）⇒ 本 feature 只补
   **运行期语义**，MUST **NOT** 改 `Command` 的字段。
2. **B12F1 已落地**且「多个中断被完整收集并**合并抛出**」的语义**已冻结**（载荷 = 元组）⇒
   本 feature **不重写**收集路径，只负责「接住 → 转成结果键」。
3. **B7F1 已落地**且 `run_super_step` / `run_super_steps` 的签名与 `SuperStepResult` 的
   四字段**已冻结** ⇒ 本 feature **另立**入口、不改既有面。
4. **上游 `langgraph 1.2.11` 是唯一权威**（宪法原则 XI）⇒ 本 spec 的所有上游锚点已带
   版本 + `路径:行号`，行为断言已**实测**（E-1…E-26）。
5. **零第三方运行时依赖**（宪法依赖白名单）⇒ `.id` 的摘要 MUST 用标准库
   （`hashlib.blake2b`）⇒ 与上游的 `xxhash` **不同**（偏离登记 **X-4**）⇒ id 的
   **长度与唯一性**与上游**同款**。
6. **M1 阶段没有可用的 checkpointer 实现** ⇒ 本 feature 的**恢复路径**可实现、可测试
   （用**桩**），但**用户**在 B14F1 之前**无法**端到端使用 HITL ⇒ 这是**里程碑顺序**
   决定的**阶段性**状态，MUST 在人工验证记录里**写明**（不得伪装成「已可用」）。
7. **facade 的导出面恰 7 个符号**（含 `interrupt`）⇒ 本 feature **只接线** `interrupt`
   的行为，MUST **NOT** 增删门面导出名（门禁 G15 / G16 / G19）。
8. **`interrupt()` 的位置**（⚠️ **PR-4** 回修）：**运行期机制**（两级 `ContextVar` · 任务现场 ·
   `.id` 生成 · resume 消费）落 **`src/freegraph/runtime/_interrupt.py`**（**L2 目录条目内**）·
   门面 **`src/freegraph/graph.py`** 用**模块级** `ImportFrom` **直接转出**（ARCH-1 的**唯一
   例外** `facade-L1-L3` ⇒ 门面 → L2 合法 · 门禁 **G17 / G18** 恒绿）⇒ ⇒
   `src/freegraph/_primitives.py`（**L2 单文件条目**）**只留 `Send`** ⇒ ⇒ **MUST NOT**
   import `runtime/`（**跨注册表条目的同层 import** ⇒ 门禁 **G25** 判红 · **实测**）⇒ ⇒
   门面 **可以**依赖 L2（ARCH-1 的唯一例外）⇒ MUST **NOT** 依赖 L4 / L5。
9. **Python 3.11 基线**（宪法运行时环境基线）⇒ 标准库 `hashlib.blake2b` /
   `contextvars` / `dataclasses(slots=True)` 均**可用** ⇒ MUST **NOT** 使用 3.12+ 的
   typing 构件（门禁 G9）。
10. **本 spec 的「实测」是在**开发期**用 `.venv` 里的上游跑出来的** ⇒ 上游**不进**发行面
    （依赖白名单：必装运行时依赖 = 无）⇒ 差分场景在**上游缺席时 skip**（既有纪律）。

---

## 下游承接条款（本 feature → 下一棒）

> ⚠️ **编号消歧（本 feature 用 `DI-` 前缀 · 2026-11-13 分析轮回修）**：本表的 **D-1…D-8**
> （**下游承接条款** · **一位数**）与「差分场景组」的 **DI-01…DI-08**（**两位数**）是**两套编号**
> ⇒ ⇒ 引用时 MUST 写全（`D-1` vs `DI-01`）。
> ⚠️ **另**：**探针文件内已有** B12F1 的 **D-01…D-15** 与 B7F4 的 **D-16…D-28**（场景名形如
> 「D-01 · 并发重叠」）⇒ ⇒ 本 feature 的差分场景**改用 `DI-` 前缀**（**interrupt-diff**）⇒
> ⇒ **同一文件内三套编号互不重号** ⇒ ⇒ grep / 引用无歧义 ⇒ ⇒ **既有场景名逐字不动**。
> ⚠️ **跨 feature 的 `D-` 引用消歧（2026-11-13 分析轮）**：**上游 feature（B12F1 / B9F1）自己的**
> 下游承接表**也用 `D-1` / `D-2` … 编号 ⇒ ⇒ 本 spec 里凡**引用他 feature 的编号**，MUST 写明
> 「**B12F1 的**」/「**B9F1 的**」**前缀** ⇒ ⇒ 例：H-2 / H-3 的来源列写「**B12F1 的**下游承接
> **D-1 / D-6**」⇒ ⇒ **本 spec 自己的** D-1…D-8 一律**不带**前缀 ⇒ ⇒ **消歧完成**。
>
> **宪法 v1.8.0**：本 feature 的规格中出现了**指名下一棒 feature（ID + 里程碑）**的跨 feature
> 义务时，该条款 MUST 写入**目标 feature 的提示词初稿**（`harness/features/<目标 feature>.md`）
> ⇒ 由目标 feature 的 spec 落成 **FR + 裁定** ⇒ 其 tasks 与契约同步接线。
> **只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽任何门禁判据。**

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 | 接线状态 |
|---|---|---|---|---|---|
| **D-1** | **B10F1 → B14F1** | **M3** | **检查点最小契约的兑现**：B10F1 定义了**读侧 / 写侧最小契约**（FR-018 · 裁定 9）⇒ **B14F1** 的 `MemorySaver` MUST **满足**它：① `get_tuple(config)` 的返回值 MUST 暴露 `.snapshot`（**L1 的 `StateSnapshot`** · 含 `values` / `next` / `interrupts` / `tasks`）、`.pending_writes`（`(task_id, channel, value)` 三元组序列）**与** `.scheduler`（**调度账本** · 纯数据 · 可 JSON 序列化）② `put(config, values=..., metadata=...)` 写**快照** ③ `put_writes(config, writes=..., task_id=..., task_path=...)` 写**待写入** ④ 保留通道名 `__interrupt__` / `__resume__` ⇒ ⇒ **B14F1 MUST NOT** 让 `MemorySaver` 写出「freegraph 读不回来」的私有形状 ⇒ ⇒ **B10F1 MUST NOT** 越界实现 saver；⚠️ **另**：B10F1 的**人工验证**里「**恢复侧真跑一轮**」按偏离登记 **V-1** 延期到 **B14F1 / M3** ⇒ ⇒ **B14F1** 的 `manual-verification.md` MUST 补上那一轮的**实测输出**（⚠️ **已达成部分**：B10F1 自身的**挂起侧**人工验证 · 走 L2 入口 ⇒ **照常**做） | FR-018 · FR-019 · 裁定 9 · SC-005 · SC-020 · 偏离登记 **V-1** | ⬜ **待接线**（写入 `harness/features/B14F1_Checkpointer协议与MemorySaver.md` · **只接线 · 逐条最小改动**） |
| **D-2** | **B10F1 → B14F1** | **M3** | **「真异常 + 中断同现」时的中断留痕（消解 **X-5**）**：上游把中断元组写进 checkpoint 的 **pending writes**（`langgraph/pregel/_runner.py:588-591`）⇒ freegraph v1 **无 checkpoint** ⇒ 那批元组**丢弃** ⇒ ⇒ **B14F1** 落地后 MUST 让中断元组**随 pending writes 留痕** ⇒ ⇒ **X-5 自动消解 · 回归上游同款** ⇒ **B14F1 MUST NOT** 把这件事当成「新功能」（它只是**上游本来就这样**）⇒ **B10F1 MUST NOT** 为此**自创**留痕形态 | FR-007 · 裁定 11 · SC-008 · 偏离登记 **X-5** | ✅ **已接线**（既有）· **本 feature 补一句** —— `harness/features/B14F1_Checkpointer协议与MemorySaver.md` **§2** 的「承接条款（B12F1 → B14F1 · M3 · 「真异常 + 中断同现」时的中断留痕）」**补一句「X-5 的消解条件」**（即「B14F1 落地后中断元组随 pending writes 留痕 ⇒ **X-5 自动消解**」）⇒ ⇒ 落 `tasks.md` **T049**（⚠️ **编号消歧**：同一件事在 **B12F1** 的偏离登记里叫 **X-4** ⇒ ⇒ 补写时 MUST 写「**B10F1 的 X-5**（B12F1 记作 X-4）」⇒ ⇒ **不**制造「同文件两个编号」的歧义） |
| **D-3** | **B10F1 → B7F3** | **M2** | **对外 `invoke()` 的接线 + L1 协议入参放宽（⚠️ **澄清轮 Q3 · 发起者拍板** · 破 L1 冻结面**留到本棒**）**：① **L1 `CompiledGraph.invoke` 的 `input` 注解** MUST 放宽为「`StateDict \| Command \| None`」（**上游同款** · `langgraph/pregel/main.py:3836-3838`）⇒ **B10F1 刻意**不破该冻结面 ⇒ ⇒ **B7F3** MUST 走「登记 + 回溯修订 + 发起者追认」流程（**不**消耗 B10F1 的追认名额）⇒ ⇒ B10F1 交付 L2 的入口（接受 `Command` 作为输入）+ `InterruptResult.as_result_dict()`（**唯一**的「异常 → `__interrupt__` 键」转成路径）⇒ ⇒ **B7F3** 的 `invoke` MUST：② 接受 `Command` 作为输入（**上游同款** · `langgraph/pregel/main.py:3836-3838`）③ 挂起时返回 `{**state, "__interrupt__": interrupts}`（**无**挂起时**不**含该键）④ **MUST NOT** 另写一条转成路径 ⑤ **MUST NOT** 把「未挂 checkpointer 时提交 `Command(resume=...)`」**静默降级** | FR-002 · FR-013 · 裁定 1 / 4 / 10 · SC-002 / SC-011 / SC-012 | ⬜ **待接线**（B7F3 的提示词初稿 **FR-006** 已含「待 B10F1 落地后转成 `__interrupt__` 键」⇒ **只接线 · 补「按 id 的映射恢复」与「未提供恢复值」两条口径**） |
| **D-4** | **B10F1 → B13F1** | **M1** | **静态中断点与递归上限的接缝**：B10F1 交付的是**动态**中断（节点内 `interrupt()` 调用）⇒ ⇒ **B13F1** 的 `interrupt_before` / `interrupt_after`（**静态**中断点）MUST **NOT** 与本 feature 的动态中断**混用**同一条挂起路径的语义 ⇒ 两者的**挂起态载体** MUST 一致（`InterruptResult` · 静态中断点的 `__interrupt__` 载荷为空元组）⇒ **B13F1 MUST NOT** 另写一条挂起路径 | FR-005 · FR-020 · 裁定 2 · SC-010 | ⬜ **待接线**（写入 `harness/features/B13F1_静态中断点与递归上限.md`） |
| **D-5** | **B10F1 → B15F1** | **M3** | **`StateSnapshot.interrupts` 的生产者**：本 feature 的检查点读侧契约以 **L1 的 `StateSnapshot`** 为快照载体（其中 `interrupts: tuple[Interrupt, ...]` 是**已存在**的结构化载体）⇒ ⇒ **B15F1** 的 `get_state()` MUST 把挂起处的中断写入 `StateSnapshot.interrupts`（元素 = `Interrupt`）⇒ ⇒ **B10F1 MUST NOT** 越界生产 `StateSnapshot` | FR-018 · 裁定 9 | ✅ **已接线**（既有）：B12F1 的 **D-7** 已把该口径写进 `harness/features/B15F1_SqliteSaver与状态历史.md` ⇒ **无需改动** |
| **D-8** | **B10F1 → B7F3** | **M2** | **MVP 验收基线的人工验证承接（⚠️ **2026-11-13 分析轮 · 登记档位 A**）**：B10F1 在 **M1** **物理不可达成**「固定脚本那一轮」（`harness/demo/target.py` 需 `compile()` + `invoke()` = B7F2 / B7F3 · M2）⇒ ⇒ 门禁 **4** 的「fake / 伪模型跑通验收基线的一轮」与门禁 **5** 的「真实模型再跑一遍」按 §门禁项的偏离登记 **V-2 / V-3** **延期** ⇒ ⇒ **B7F3** 的 `manual-verification.md` MUST 补上这两轮的**实测输出** ⇒ ⇒ **B10F1 MUST NOT** 把「本 feature 未跑固定脚本」写成「本 feature 未验证」（**已达成部分** = 本 feature 自身的**挂起侧**人工验证 · 走 L2 入口） | SC-020 · 偏离登记 **V-2 / V-3** | ⬜ **待接线**（写入 `harness/features/B7F3_invoke返回完整状态.md` · **只接线 · 逐条最小改动**） |
| **D-6** | **B10F1 → freechain** | **v2** | **HITL 装配层**：freegraph 提供**原语**（`interrupt()` / `Command(resume=)` / `__interrupt__`），freechain 负责**审批 UI / 通知 / 审批记录**（宪法原则 VII：freegraph 提供原语 · freechain 提供 agent 装配）⇒ ⇒ **B10F1 MUST NOT** 交付任何 UI / 通知 / 审批工作流 | Out of Scope 第 10 条 | — （跨项目 · 非本仓库） |
| **D-9** | **B10F1 → B15F1** | **M3** | **检查点读侧 / 写侧最小契约（与 B14F1 **同款**）**：本 feature 冻结的「**内核与 saver 的接缝**」（`contracts/checkpoint-contract.md`）适用于**任何** saver 实现⇒ ⇒ **B15F1 的 `SqliteSaver` MUST 满足它**（**读侧** `.snapshot` / `.pending_writes` / `.scheduler` · **写侧** `put(values=, metadata=)` / `put_writes(writes=, task_id=, task_path=)` · **保留通道名** `__interrupt__` / `__resume__` · `task_id` = 节点名 · **挂起时 `put` 的 `metadata` 载荷**原样存取）⇒ ⇒ **MUST NOT** 另立一套（⇒ ⇒ 避免两个 saver 的载荷形状**漂移**）⇒ ⇒ **B15F1 MUST NOT** 越界实现本 feature 的语义（**FR-019**） | FR-018 · FR-019 · 裁定 9 · SC-005 | ✅ **已接线**（写入 `harness/features/B15F1_SqliteSaver与状态历史.md` §2 · **只接线 · 逐条最小改动**） |
| **D-7** | **B10F1 → B16F1** | **M3** | **`update_state` / 时间旅行与本 feature 的边界**：本 feature 的恢复路径读的是 **checkpointer 的最新快照 + pending writes**（**不**改写历史）⇒ ⇒ **B16F1** 的 `update_state` / 分叉 MUST **NOT** 与本 feature 的恢复路径**共用**同一套「改写历史」的语义 ⇒ 两者**并存但独立** | FR-010 · FR-018 · 裁定 9 | ⬜ **待接线**（写入 `harness/features/B16F1_update_state与时间旅行.md`） |

---

## 软断言联动（验收脚本集）

| 项 | 内容 |
|---|---|
| **软断言** | `harness/demo/graph_core.py` 的 `case_interrupt_resume` 中，「C17 `Command(resume=)` 从节点起点重跑并拿到 resume 值」当前是**软断言**（`soft(...)` · 形态待 B14F1 拍板） |
| **形态已定** | 本 feature 落地后该断言的**形态已定**：① 首次执行 ⇒ 结果含 `__interrupt__`（元素带 `.value` / `.id`）② 挂 checkpointer ⇒ 以 `Command(resume=...)` 恢复 ⇒ 节点**从头重跑**并拿到 resume 值 |
| **升级时机（裁定）** | 该软断言 **MUST** 在 **B14F1** 结束时升级为**硬断言**（`check`）—— 理由：**B10F1** 只提供 L2 入口（**无** `compile()` / `invoke()` · 属 B7F2 / B7F3）⇒ **门面色**的断言在 M1 **物理不可达**；**B14F1** 是「**挂上真实 saver**」的第一个 feature ⇒ ⇒ 两者齐备的最早时点 = **B14F1** ⇒ ⇒ **升级动作 MUST 落在 B14F1**（MUST **NOT** 在 B10F1 里改 `graph_core.py` 的断言等级 —— 那会**必红**） |
| **验收判据的落点** | ⇒ 本 spec 的 **SC-002 / SC-003** MUST 在 **B7F3** 落地后由 `harness/demo/graph_core.py` 的**门面色**用例覆盖；⇒ **B14F1** 的 tasks MUST 含「把该软断言升级为硬断言」的一条（承接 **D-1** 所在的同一个 feature） |
