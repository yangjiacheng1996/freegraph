# Implementation Plan: B12F1 · 节点执行 + 并发执行 + 错误传播 + `GraphInterrupt` 合并

**Branch**: `b12f1-concurrency-errors` | **Date**: 2026-11-12（**上游对齐修订轮 · 重写**）· 2026-11-13（**对账补记** · 回溯修订清单补 **T-10 / T-11**） | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/b12f1-concurrency-errors/spec.md`（**2026-11-12 修订版** + **2026-11-13 对账补记**）

> ⚠️ **本 plan 是**重写**，不是增量**：初版 plan（497 行）建立在**旧口径**上
> （节点表顺序 · 并发度不限 · 失败**不**取消其余任务 · 中断集合落**调度状态字段**）⇒
> 而 spec 已于 2026-11-12 按**上游 `langgraph 1.2.11` 逐条对齐**（修订清单 **V-1…V-7** ·
> 澄清轮 **Q11…Q18** · 新增 **裁定 25**）⇒ ⇒ 初版 plan / research / data-model /
> quickstart / contracts **全部作废** ⇒ 本 plan 逐份重出。
> ⇒ **重写的权威输入** = 本 feature 的 `spec.md`（**唯一权威**）+ 宪法 **v1.10.0**。
> ⚠️ **2026-11-13 对账补记**：spec 的「裁定 3 / R-3」结论（「P2-c 已落地 ⇒ **只承接、不再改写**」）
> 与 B7F1 spec 的 Out of Scope（逐字「并发节点执行 —— 属 B12F1 … **FR-013 的顺序承诺届时失效**」）
> **直接矛盾** ⇒ 本 feature **MUST 回溯修订** B7F1 契约 §4（阶段 ③「串行」→ 并发 · 追加阶段 ③′ / ⑥）
> 与 B7F1 spec FR-013（「执行」承诺）⇒ ⇒ **回溯修订清单由 T-1…T-9 扩为 T-1…T-11**（spec 与本 plan **同步**）
> ⇒ **登记项 PR-7 的追认范围同步扩为 T-1…T-11**（**追认次数仍为 1 次**）。

---

## Summary

**交付什么**：让 L2 调度内核**真正执行节点函数**，并处理三件真实使用中立刻会遇到的事 ——
① 同一 super-step 内的**多节点并发执行**；② 节点抛异常时的**错误传播**；
③ 多个节点同时中断时的 **`GraphInterrupt` 合并**。

**技术路线**（零第三方依赖 · 零出站 · 零环境变量）：

| 关注点 | 落法 |
|---|---|
| **并发机制** | **标准库线程池**（`concurrent.futures.ThreadPoolExecutor`）⇒ **NOT** async（v2 范围） |
| **并发度** | 缺省 **`min(32, cpu+4)`**（**上游同款** · `langchain_core/runnables/config.py:660-674`）· 显式 `max_concurrency=N` ⇒ `min(本轮任务数, N)`（**N 不被 32 再夹**） |
| **取值校验** | **入口即失败**（**哪怕本轮没有节点要跑**也报错）⇒ 类型不符 ⇒ 内置 `TypeError` · `< 1` ⇒ 内置 `ValueError`（两者均**点名该参数**）⇒ **上游同款**（标准库线程池在**构造时**校验）⇒ `bool` 按 `int` 收 ⇒ 落 tasks **T012 / T023** |
| **写隔离** | 每任务一个**结果槽**（私有 · 不写共享调度状态）⇒ 轮末**统一落回** ⇒ 杜绝竞态 |
| **合并路径** | **零改动** —— 仍走 B7F1 的**批量**合并（每通道**一次** `Channel.update(values)`）⇒ **MUST NOT** 另写并发合并路径 |
| **错误传播** | 首个异常（**节点名序**·确定）**原样**抛出（类型 / 消息 / 对象 identity 逐字一致）⇒ 其余失败以**附注**记录 |
| **取消语义** | 首个真实异常 ⇒ **取消「排队未启动」**的任务（**上游同款**）· **运行中者不中断**、但**被等待** |
| **中断** | 收集全部 ⇒ **合并抛出**一个 `GraphInterrupt`（载荷 = **元组** · **节点名序**）⇒ 上游同款 |
| **顺序口径** | **节点名序**（**上游同款** · `_algo.py:482`）⇒ 非交换归约器的合并结果**可复现** |
| **节点入参口径** | 入参 MUST 等于 `read_channels(子映射)` 的结果 · 子映射 MUST 按「**通道映射的顺序**」构造 ⇒ **MUST NOT** 改写 key 顺序 ⇒ 全部入参在**任何节点执行前**确定（承接 **H-1** · spec FR-011 · 裁定 26）⇒ 落 tasks **T054** |
| **`Command` 的并发语义** | ① 各节点的 `goto` 目标**不互相吞并** ② `Command.update` 走**同一条**批量合并路径 ③ 归并顺序 ==「**节点名序 × 命令列表顺序**」（承接 **H-2** · spec FR-012 · 裁定 15）⇒ 落 tasks **T051 / T052 / T053** |
| **可验证出口** | 交付 **15 条差分探针场景**（**D-01…D-15** · `tests/differential/parity_probe.py`）⇒ CI Linux 全量档**真跑** |

**唯一权威**：本 feature 的**需求与判据**以 `spec.md` 为**唯一权威**；本 plan 只**承接**它 ⇒
⇒ 下表与 contracts / research 里的数值**一律以 spec 为准**（若不一致 ⇒ 以 spec 为准并回修本 plan）。

**上游对齐口径**（本轮修订的实质）：**内容照抄上游 + 形态取最优**（宪法 **v1.10.0**（含原则 XI 与 XII））⇒
本 plan 的**全部**设计决策 MUST 先问「上游怎么说」，只在**失败信号**上更严（**X-1 / X-2 / X-3 / X-7**）
并**如实标注**。

---

## Technical Context

**Language/Version**: Python **>= 3.11**（typing 构件上限 = **3.11** · 禁用 `TypeAliasType` / `override` / `ReadOnly` / `TypeIs` / PEP 695 `type` 语句）· 异常**附注**机制（`BaseException.add_note`）是 **3.11** 引入 ⇒ **允许**

**Primary Dependencies**: **零**（`dependencies = []`）⇒ 并发实现 MUST 只用**标准库**
（`concurrent.futures` / `threading`）⇒ ⚠️ 上游 `langgraph` / `langchain-core` **仅作 dev/test 依赖**
（PEP 735 依赖组）⇒ **绝不进 `Requires-Dist`** ⇒ 门禁 **G3 / G21 / G23** 恒绿

**Storage**: **N/A**（v1 无 checkpoint ⇒ **B14F1 / M3**）⇒ 本 feature **零文件 I/O**、零持久化

**Testing**: **pytest**（dev 依赖组）+ **差分探针**（`tests/differential/parity_probe.py` ·
`test_parity_probe.py`）⇒ 上游**缺席即 skip**（沿用 B5F2 的「缺席即 skip」纪律）

**Target Platform**: Linux / macOS / Windows（**线程**语义跨平台 ⇒ 无 POSIX-only 依赖）

**Project Type**: **library**（可复用内核 · 无服务 / 无 UI）

**Performance Goals**:
- 一轮 super-step 的墙钟时间 ≈ **最慢的那个节点**（而非各节点之和）⇒ 并发夹具可判定（SC-001）
- 实际并发度 == `min(本轮任务数, min(32, cpu+4))` ⇒ 缺省**有上限**（**上游同款**）
- 连续运行 **≥ 10** 轮后进程内线程数**不增长**（SC-025）⇒ **零悬挂线程**

**Constraints**:
| # | 约束 | 依据 |
|---|---|---|
| C-1 | **零出站** / **零环境变量** / **零文件 I/O** | 宪法原则 **I / II** · FR-007 |
| C-2 | **L2 只依赖 L1** ⇒ **MUST NOT** import 门面（L3）/ L4 / L5 · **MUST NOT** 横向依赖其它 L2 模块 | 宪法 **ARCH-1** · FR-015 · 门禁 **G25** |
| C-3 | `freegraph.runtime.__all__` **仍为 20** ⇒ 并发执行器 MUST 是**内部模块** | **FR-016** · 裁定 13 |
| C-4 | `SuperStepResult` **四字段冻结面零改动** | 裁定 25（**依原则 XII 重判**）· 契约 §1 |
| C-5 | `SchedulerState()` **构造签名逐字不变** ⇒ **不新增任何字段** | 裁定 25 · 契约 §1 |
| C-6 | 门禁编号 **G1–G30** **连续无跳号**、总数 == **30** | FR-025 |
| C-7 | **NOT** 引入 async / 事件循环抽象 | FR-008 |
| C-8 | **NOT** 读环境变量 ⇒ 上游的 `LANGGRAPH_DEFAULT_RECURSION_LIMIT` 覆盖**不采纳**（硬编码 10007） | P2-c 已落地 |

**Scale/Scope**: 立项书 §5.2 的 **1,080 行 / 3 人日** ＝ **初版口径** ⇒ ⚠️ **已被本轮修订超越**
（差分场景 **15** 条 · 回溯修订 **11** 项 · 下游接线 **7** 处 · 追认 **11** 项 · tasks **83** 条）
⇒ ⇒ **实际规模以 `tasks.md` 的 83 条任务为准**；立项书的数字 MUST 由**发起者**在 feature 收尾时重估回写
（⚠️ **2026-11-13 补记**：该重估**本 feature MUST NOT** 单方面改上位文档 ⇒ 落点见 `tasks.md`
的「遗留问题」登记任务）

**本 feature 的主要改动面**（**摘要 · 8 行** ⇒ ⚠️ **完整清单见本 plan 末尾「本 feature **触及**的文件」
· 表格 23 行 / 实际 28 个文件**）—— 下表**只列主要项**，**MUST NOT** 当作完整改动面）：

| # | 文件 | 动作 | 说明 |
|---|---|---|---|
| 1 | `src/freegraph/runtime/_concurrency.py` | **新增** | 并发执行器（**内部** · **不进 `__all__`** ⇒ 导出面仍 20） |
| 2 | `src/freegraph/runtime/superstep.py` | **改** | `_execute_node` 拆分（纯执行 / 落回）· `_run_round` 阶段 ③ 并发化 · 两个入口增 `max_concurrency` |
| 3 | `tests/runtime/test_superstep_concurrency.py` | **新增** | 并发 / 错误传播 / 中断合并的单元用例 |
| 4 | `tests/runtime/test_superstep_errors.py` | **新增** | 异常 identity / 取消语义 / 附注格式 |
| 5 | `tests/differential/parity_probe.py` | **改** | 追加 **D-01…D-15** 场景组（判词三态） |
| 6 | `tests/differential/test_parity_probe.py` | **改** | 打包器（CI Linux 全量档真跑） |
| 7 | `harness/verification/B12F1/acceptance.py` | **新增** | 机械层一键验收（原则 V） |
| 8 | `harness/verification/B12F1/manual-verification.md` | **新增** | 五段式人工验证记录 + **追认文字** |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 通过项（逐条 · 原则 I–XII）

| 原则 | 判定 | 本 feature 的落实 |
|---|---|---|
| **I** 零 LangSmith 依赖 | ✅ | 零导入（SC-018）· 上游仅 dev/test 依赖组 |
| **II** 内核纯净 | ✅ | 零 LangChain / LangGraph 导入 · 零出站 · 零环境变量 |
| **III** 验收契约优先 | ✅ | 本 feature 对契约 **C1–C27 零改动**（只落**运行期语义**）⇒ ⚠️ **例外登记（2026-11-13 · X1 / R-10）**：**上游对齐批次 P3**（发起者已批准）已改 **C17 / C19 / C20** 并扩了 L1 的公开符号面（18 → 20）⇒ ⇒ 该部分**不由本 feature 承担**（**本 feature 的基线改为 20** · 回溯修订已在批次内完成 ⇒ **不重复追认**）<br>⚠️ **2026-11-13 分析轮补记**：验收契约侧的 **A7** 用例（`harness/demo/graph_core.py:403-441`）现状只断言「两个节点都跑了」（`sorted(out["messages"]) == ["left","right"]`）⇒ **不构成 A1「真并发」判据**（无时间窗 / 无屏障）⇒ 该文件本 feature **只核对**（**核对项** · 见「触及的文件」表第 23 行）⇒ **差距如实登记**进人工验证记录的「遗留问题」段（并入 **PR-11** 的遗留问题面）⇒ **不得**把 A7 现状误当作 A1 已通过 |
| **IV** 可诊断性是一等功能 | ✅（**不新增可观测面** · 承接） | 本 feature **零新增 span / trace / 结果字段**（FR-016 · 裁定 12）⇒ 原则 IV 的「每次节点执行 MUST 产生含**节点名 / 输入 / 输出 / 耗时 / 错误**的可观测记录」由 **B18F1 / B19F1** 交付；⚠️ 并发引入后「**同轮哪些节点并发执行**」这一可观测事实 MUST 由 **B19F1** 在 trace 层统一暴露（**下游承接 D-3**）⇒ 本 feature **MUST NOT** 期待 B19F1 预先提供并发分组信息，也 **MUST NOT** 自造可观测字段 |
| **V** 人工验收是最终验收标准 | ✅ | `harness/verification/B12F1/manual-verification.md`（五段式 + 来源覆盖表 == 100%） |
| **VI** 规格驱动开发 | ✅ | 本 plan / research / data-model / quickstart / contracts 全部由 `spec.md` 派生（**spec 是唯一权威**） |
| **VII** 职责边界与内核契约 | ✅ | **L2 only**（C-1–C27）· 本 feature **MUST NOT** 改 C1–C27 任一条 ⇒ ⚠️ **批次例外（2026-11-13 · X1 / R-10）**：**上游对齐批次 P3**（`harness/proposals/上游对齐审计.md` §3 · **发起者已批准**）已改 **C17 / C19 / C20** ⇒ 本 feature **只承接**（基线改为 20）+ **不重复追认** |
| **VIII** 证据与术语纪律 | ✅ | 上游引用**全部**带 **版本 + `路径:行号`**（FR-019）· **行为断言全部有实测**（research §1 的 **E-1…E-6**） |
| **IX** 依赖许可证与商标红线 | ✅ | 零新增依赖 · `THIRD_PARTY_NOTICES` 零改动 |
| **X** 文档合规义务 | ✅ | 新源文件**署名头** == 100%（FR-023） |
| **XI** 上游优先 | ✅ | **行为面逐条照抄**（V-1…V-8）· 只有**失败信号**更严（X-1 / X-2 / X-3 / X-7）且**如实标注** · 自研**零** |
| **XII** 最优设计优先 | ✅ | **裁定 25**：先穷举既有同语义载体（L1 的 `StateSnapshot.interrupts` **已存在**）⇒ **不需要破**冻结面 ⇒ **四字段** |

### ⚠️ 登记项（**偏离登记 + 发起者追认** · 宪法原则 XI / 跨 feature 承接通则）

> ⚠️ **编号体系**：本表的 **PR-n**（**P**lan **R**egistration）= **plan 阶段**的登记项（须发起者追认）
> ⇒ **MUST NOT** 与 **spec.md** 的「刻意偏离与回溯修订（登记）」的 **R-n**（**S**pec **R**egistration）混淆
> ⇒ 两套编号**内容不同**：**PR-n** ＝「要追认什么」；**R-n** ＝「偏离 / 回溯修订了什么」
> ⇒ **T-n**（**回溯修订清单**）＝「要改哪份契约的哪一节」⇒ **PR-7 ↔ T-1…T-11**。
> ⇒ **R-n ↔ T-n** 的对应（与 spec 的「编号体系」表**同口径**）：**R-1↔T-1 · R-2↔T-2 · R-3↔T-3 · R-7↔T-5 · R-8↔T-8 · R-9↔T-7**。
> ⚠️ **R-3** 另挂 **T-10 / T-11**（FR-013 的「**执行**」层 · 2026-11-13 对账补记）⇒ 与 spec 的 **R-3** 行一致。

> **追认次数 ≤ 1 次**（宪法）⇒ 下列 **11 项**打包成**一次**追认 · 追认文字 MUST 落在
> `harness/verification/B12F1/manual-verification.md` ⇒ **未追认前 MUST NOT 合入**。
> ⚠️ **判据只收紧、不放宽**；依赖 / 许可证 / 商标 / 零出站四条红线**照常执行**。

| # | 登记项 | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|---|
| **PR-1** | **首个异常**的选取 = **节点名序**（确定） | 更严失败信号（X-1） | 上游从 `done` **集合** `pop()` ⇒ **竞态**（**实测** 50 次 ⇒ **26 / 24** 分布） | 上游**自身不确定** ⇒ 落在「必须自研区 ②」⇒ 保留**更确定**的口径并**如实标注** | **不承接**（本 feature 内闭合）· 一次追认 |
| **PR-2** | **其余并发失败**以**附注**记录（**固定格式**且**三样齐全**：**节点名** · **异常类型名** · **消息**）| 更严失败信号（X-2） | 上游把其余异常只落 checkpoint 的 `ERROR` 通道 ⇒ **调用方看不到**（`_runner.py:595-603`） | 上游**丢弃**其余异常 ⇒ 失败信号**更严** | **不承接** · 一次追认 |
| **PR-3** | **整轮原子**含「**节点抛真异常**」这一类 | 更严失败信号（X-3） | 上游**无回滚**（`_algo.py:315-323`）⇒ 出错轮「成功节点合并、失败节点不合并」 | 上游留下「**写了一半**」的中间态 ⇒ 消除它 = **更严** ⇒ 承 **B7F1 的 FR-032**（冻结面 MUST NOT 被破） | **B7F1**（承 FR-032）· 一次追认 |
| **PR-4** | **中断元组内元素顺序** = **节点名序** | 更严失败信号（X-7） | 上游从 `done` **集合** `pop()` ⇒ 该顺序**竞态**（**实测** 200 次 ⇒ **199 / 1** 分布） | 同 **X-1**（上游自身不确定）⇒ 与「首个异常」**同款取舍** | **不承接** · 一次追认 |
| **PR-5** | **根图对中断的处置**（**合并抛出** vs 上游**抑制** + 结果键） | 结构差异（X-4 · **DIFF** · **临时**） | 上游根图**抑制** ⇒ 落进结果键 `__interrupt__`（`_loop.py:1336-1339`） | freegraph v1 **没有**「根图抑制 + 结果键」机制 ⇒ **结构差异**（**不是**更严）⇒ ⇒ **MUST NOT** 自创留痕形态（原则 XI ③） | **B10F1**（结果键）· **B14F1**（真异常同现时的留痕 · **D-6**）⇒ **B10F1 落地后消解** |
| **PR-6** | **多源汇合边**（AND / 屏障）**不实现** | 结构差异（X-5 · **DIFF** · 能力缺口） | 上游 `add_edge([a,b], c)` 可表达（`graph/state.py:1560-1575`） | 补它会**破 B7F1 的 `edges` 冻结面** ⇒ 本 feature **MUST NOT** 顺手做 | **B7F4（M1）**（立项书 §5.2 已排期 · 依赖含 **B12F1** · 提示词初稿 `harness/features/B7F4_多源汇合边与屏障.md` **已落盘**）⇒ **本 feature 不承接** |
| **PR-7** | **回溯修订 B7F1 契约 / spec / 冻结断言**（**T-1…T-11**） | 破冻结面（**拆分而不删**） | 见 §「破冻结面的回溯修订清单」 | ① 顺序口径由「节点表顺序」改为「**节点名序**」（**P2-c 已落地**）⇒ 契约里**残留**的旧措辞 MUST 订正；② ⚠️ **T-10 / T-11**（**本次真正被破的冻结面** · 2026-11-13 对账补记）：契约 §4 阶段 ③「按**节点表顺序串行**执行」⇒ **并发**（+ 阶段 ③′ / ⑥）· B7F1 spec FR-013「MUST 按节点名序**执行**」⇒ 拆分为「合并 / 报告顺序 = 节点名序」+「执行时序**不确定**」⇒ ⇒ **追认文字 MUST 逐条覆盖 T-1…T-11** | **B7F1**（契约 + spec + `test_i12`）· 一次追认 |
| **PR-8** | **既有 7 处「同轮完成顺序」断言**的拆分（⚠️ **2026-11-13 · T007 实跑据实**：初版口径 **10** 处 ⇒ 实跑 **7** 处 / **5** 个文件） | 判据**只收紧** | 串行模式**保留原逐字断言**（一条不删）+ 并发模式加**顺序无关但有力**的断言 | 那 7 条断言记录的**从来不是** freegraph 的**契约**（对外承诺的是**节点名序**）⇒ 判据**不弱化**<br>⚠️ **2026-11-13 订正（实施期据实落定）**：**「10 处」是初版口径**（`research.md` §2 **C-01** · 基线 626）⇒ **T007 的 C-01 探测重跑**（原型 + **真实实现**双证 · **3/3 次一致**）⇒ **权威条数 == 7** ⇒ ⇒ spec FR-006 / 裁定 19 / **R-6** 与本登记项已**据实订正为 7**（**拆分义务本身不变**）⇒ 实跑清单见 `harness/verification/B12F1/manual-verification.md` §2.3 | **B7F1 / B9F1**（用例）· 一次追认 |
| **PR-9** | **调度状态落回时机的收紧** | 刻意收紧（对现状） | 现状在**执行期**就写 `dynamic_edges` / `node_versions` ⇒ 改为「轮末统一落回」 | 并发写共享可变状态 = **竞态来源** ⇒ 出错轮**不**推进任何版本 ⇒ 消除「**幽灵触发**」 | **不承接** · 一次追认 |
| **PR-10** | **下游承接 D-1…D-7** 的**跨 feature 文档改动** | 接线 | **只接线 · 逐条最小改动** ⇒ **逐条明细在 `tasks.md` 的 **T071**（本 plan **MUST NOT** 重复维护同一份清单** ⇒ 否则两处会漂移**） | 宪法 v1.8.0 的承接通则 | **B10F1 / B7F2 / B7F3 / B14F1 / B19F1 / B15F1**（提示词初稿）· 一次追认 |
| **PR-11** | **宪法「质量门禁 3 / 4 / 5」的三部分在本 feature 物理不可达成**（⚠️ **2026-11-13 补记** · 依宪法 **v1.6.0** 的窄口径通则处置） | **门禁项偏离**（质量门禁 · 非上游差异） | ① **被偏离的门禁项**：**门禁 3** 的「**C8**（条件边 fresh 状态）两条**独立回归测试**」之 **C8** 那一条 · **门禁 4** 的「**fake 模型跑通验收基线的一轮**」 · **门禁 5** + 原则 V 的「人工验证记录含**真实模型一轮**」<br>② **不可达成的根因**（含里程碑依据）：三者**共享同一根因** —— 它们都要求**完整内核运行时**（`StateGraph` 构建器 + `compile()` + `invoke()` + 条件边）存在，而本 feature 按**立项书 §5.2 只交付 L2 的并发执行 / 错误传播 / 中断合并**（`StateGraph` = **B6F1** · `compile` = **B7F2 / M2** · `invoke` = **B7F3 / M2** · 条件边 = **B8F1 / M2** · C8 回归的 owner = **B8F1**）⇒ ⇒ **本 feature 无图可跑** ⇒ ⇒ 任何 spec 设计都**无法**在本 feature 满足这三条<br>③ **判据未被放宽的论证**：**C8 的判据一字未改**（仍挂在 `tests/contracts/test_contract_regressions.py` 的 `GATE-MOUNT: C8 · status=not-landed · owner=B8F1` ⇒ **MUST NOT** 改成 `landed`）⇒ 本 feature **零改动**该文件；**门禁 4 / 5** 的判据**同样一字未改** ⇒ 承接方落地时**照原判据**执行 ⇒ **零放宽**<br>④ **红线照常执行**：依赖 / 许可证 / 商标 / 零出站**四条红线**在本 feature **照常执行**（**不适用**本条延后）⇒ 且 **MUST NOT** 写一条**永久红**的 CI（⇒ 人工验证记录**照常**五段式 + **来源覆盖表 == 100%**）<br>⑤ **落点**：本 `plan.md` 的**本登记项** + `tasks.md` 的**T080**（**一次**追认 · 并入同一次打包）+ `harness/verification/B12F1/manual-verification.md` 的**「遗留问题」段**（可审计） | 宪法 **v1.6.0**「质量门禁的分阶段落地与发起者追认」（窄口径通则）· **先例**：`specs/b4f1-schema-reducer-parse/plan.md`（门禁 3）· `specs/b9f1-command-primitive/plan.md`（门禁 4 / 5） | **B8F1**（C8 回归 · M2）· **B7F3**（`invoke` · M2）· **B25F1**（双跑验收 · M4）· **B7F2**（`compile` · M2）· 一次追认 |

### 破冻结面的回溯修订清单（**T-1…T-11** · **拆分而不删**）

> ⚠️ **本清单**只含「**由本 feature 触发**」的破冻结面回溯修订 ⇒ ⇒ **不含**「**上游对齐批次 P3**」
> 对 L1 的改动（公开符号面 18 → 20 · C17 / C19 / C20）—— 该批次的回溯修订**已在批次内完成**
> （`specs/b2f1-contracts-protocols/contracts/public-api.md` + `specs/b2f1-contracts-protocols/spec.md`
> · **发起者已批准**）⇒ ⇒ 本 feature **只承接**（基线改为 20）⇒ **登记 = spec 的 R-10**
> ⇒ **不重复追认**（追认仍为 **PR-1…PR-11 打包成的一次**）⇒ **不新增 T-n**。

| # | 冻结面 | 回溯修订位置 | 冻结断言处置 | 承接方 |
|---|---|---|---|---|
| **T-1** | B7F1 契约 §5.3（`SuperStepResult.executed` 的语义措辞） | `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §5.3 | 「按执行顺序」→「本轮**被启动过**的节点集合 · 按**节点名序**」⇒ 字段数 / 名字 / 类型**逐字不变** | **B7F1** |
| **T-2** | B7F1 契约 §1（两个入口的签名） | 同上 §1 | 各增 keyword-only 的 `max_concurrency: int \| None = None`（**兼容扩展**）· 缺省 = `min(32, cpu+4)` | **B7F1** |
| **T-3** | B7F1 FR-013（同轮**顺序口径**承诺） | `specs/b7f1-superstep-loop/spec.md` FR-013 | 「节点表顺序」→「**节点名序**」（**P2-c 已落地**）⇒ 本 feature 只**承接**、不再改写（⚠️ **仅限「顺序口径」这一层**；FR-013 的「**执行**」层**另见 T-11**） | **B7F1** |
| **T-4** | B7F1 契约 §4 / §5.1（五阶段表与批量合并规则里**残留**的「节点表顺序」措辞） | 同上 §4（阶段 ① / ③）· §5.1（批量行） | 「节点表顺序」→「**节点名序**」⇒ 与 **I-12** 对齐 | **B7F1** |
| **T-5** | B7F1 契约 §5.3（`steps` 在中断挂起时的口径） | 同上 §5.3 | 补「挂起时**如实计**『实际跑过的轮数』」的分支 ⇒ ⚠️ 其**载体**在**将来 B10F1** 的结果对象上（本 feature 侧**无载体**） | **B7F1** + **B10F1** |
| **T-6** | 既有 **7 处**「同轮完成顺序」断言（⚠️ **2026-11-13 · T007 实跑据实**：初版 **10** 处 ⇒ **7** 处） | `tests/runtime/test_superstep_*.py` · `tests/runtime/test_command_*.py` | **拆分而不删**（串行保留原断言 + 并发加顺序无关断言） | **B7F1 / B9F1** |
| **T-7** | B7F1 契约 §7 的 **I-13**（多会话隔离） | 同上 §7 | 加注记「该判定口径在 **P2-b 之后首次成立**」⇒ 偏离登记 **X-6 消解** | **B7F1** |
| **T-8** | B7F1 契约 §7 的 **I-12**（并发下执行顺序不确定） | 同上 §7 | 「**节点名序 == 报告顺序**（`executed` 的口径）」⇒ **同步** `tests/runtime/test_superstep_contract.py` 的 `test_i12` 的 docstring / 命名 | **B7F1** |
| **T-9** | **B10F1** 的 `__interrupt__` 结果键接线 | `harness/features/B10F1_interrupt与resume.md` FR-007 + 结果键口径 | 元素类型由「载荷对象集合」改为「**元组**」⇒ 元素的 `.value` / `.id` 逐字可读 | **B10F1** |
| **T-10** | B7F1 契约 §4 的阶段表（**五阶段** → ③ / ③′ / ⑥ · 阶段 ③ 由「串行」改为「并发」） | 同上 §4（**标题** + 阶段 ③ 行） | 阶段 ① / ② / ④ / ⑤ 的**语义与编号逐字不变** ⇒ 阶段 ③ **细分**为 ③（**并发执行**）/ ③′（**判定与落回**）并**追加**阶段 ⑥（**收尾**）⇒ 原「按**节点表顺序串行**执行」一条**拆分而不删** | **B7F1** |
| **T-11** | B7F1 spec FR-013（同轮**执行**顺序承诺 · **并发下失效**） | `specs/b7f1-superstep-loop/spec.md` FR-013（+ 其 Out of Scope 里「并发节点执行 —— 属 B12F1 … FR-013 的顺序承诺届时失效」一句的**对账**） | 「MUST 按**节点名**序**执行**」**拆分**为「① **合并顺序**与**报告顺序** MUST 按**节点名**序（**可复现**）② **执行**的**时间**先后在并发下**不确定** ⇒ MUST **NOT** 作为任何可观察顺序的判据」⇒ **顺序承诺本身不撤销** | **B7F1** |

### 门禁编号纪律

- 既有 **G1–G30** MUST 保持**连续无跳号**、总数 == **30**（FR-025）⇒ **本 feature 不新增门禁编号**。
- **差分探针**跑在既有的 **CI Linux 全量档**里 ⇒ **零**新增门禁（**B3F1 的 CI 已含该档**）⇒
  ⇒ 「差分门禁」= **既有门禁的加强**（同一档里多跑一组用例）⇒ **MUST NOT** 新增编号。
- **G25**（层注册表）：新模块落 `src/freegraph/runtime/`（**目录条目已登记**）⇒ **层注册表零改动**
  ⇒ ⚠️ **MUST NOT** 为 `runtime/` 下的新模块单独立条目（会造成 L2 → L2 横向依赖误判）。

### 设计后复核（Phase 1 后 · 模板要求「Re-check after Phase 1 design」）

| # | 复核项 | 结果 |
|---|---|---|
| 1 | 原则 **XI**（上游优先）：本 plan 的每个设计点是否都**先问过「上游怎么说」** | ✅ 并发度 / 取消 / 中断形态 / 顺序 / 合并路径 / 异常呈现 —— **全部照抄**；差异仅 **X-1…X-5 / X-7**（**X-6 已消解** · P2-b 落地）且**已标注** |
| 2 | 原则 **XII**（最优设计优先）：**是否先穷举了既有同语义载体** | ✅ 中断信息 ⇒ 穷举得 **L1 已有的 `StateSnapshot.interrupts`** ⇒ **不需要破**冻结面 ⇒ **四字段**（裁定 25） |
| 3 | 原则 **XII** 的「层次对应优先于容器对应」 | ✅ 上游 `_runner` **抛** / 根图**抑制** ⇒ freegraph L2 **抛** / 门面**抑制** ⇒ 逐层对应 |
| 4 | **导出面**是否仍为 **20** | ✅ 并发执行器落**内部模块** `_concurrency.py` ⇒ **不进 `__all__`** |
| 5 | **四字段**冻结面 / **`SchedulerState()` 签名** | ✅ **零改动**（裁定 25）⇒ **不新增任何带缺省值的字段** |
| 6 | **层纪律**（ARCH-1） | ✅ 新模块在 **L2** ⇒ 只 import **L1**（`freegraph.contracts`）⇒ **MUST NOT** import 门面 / L4 / L5 |
| 7 | **零出站 / 零环境变量 / 零文件 I/O** | ✅ 并发实现只用 `concurrent.futures` ⇒ `os.cpu_count()` 是**系统调用**（**非**环境变量）⇒ 合规 |
| 8 | **门禁编号** | ✅ **零新增**（G1–G30 连续） |
| 9 | **判据只收紧、不放宽** | ✅ 既有 **7** 处顺序断言**一条不删**（**拆分而不删** · ⚠️ **2026-11-13 · T007 实跑据实**：初版 **10** 处）· SC 总数 **26 → 29**（**新增 3 条**，**零条放宽**） |
| 10 | **追认次数** | ✅ **1 次**（**PR-1…PR-11** 打包 · 含 **T-1…T-11** 的回溯修订 + **门禁 3 / 4 / 5 的偏离登记**（PR-11））⇒ 落在 `harness/verification/B12F1/manual-verification.md` |

---

## Project Structure

### Documentation (this feature)

```text
specs/b12f1-concurrency-errors/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output —— 上游实测 E-1…E-6 + 设计决策
├── data-model.md        # Phase 1 output —— 实体 · 状态机 · 校验规则 · 不变量
├── quickstart.md        # Phase 1 output —— 可跑的验收指南
├── contracts/
│   ├── concurrency-contract.md   # 并发契约（**唯一权威**）
│   └── upstream-parity.md        # 上游对照（**证据表**）
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/            # L1 · 契约层（**本 feature 零改动**）
│   ├── errors.py         #   GraphInterrupt（payload = 元组）· **零改动**
│   └── types.py          #   Interrupt · StateSnapshot（interrupts）· **零改动**
├── runtime/              # L2 · 执行内核层（**本 feature 的落点**）
│   ├── __init__.py       #   导出面 **20 个符号**（**零改动**）
│   ├── superstep.py      #   ★ 改：_execute_node 拆分 · _run_round 并发化 · 两入口增 max_concurrency
│   ├── _concurrency.py   #   ★ 新增：并发执行器（**内部** · **不进 __all__**）
│   ├── channel.py        #   **零改动**（合并路径沿用）
│   ├── read.py           #   **零改动**（稀疏读沿用）
│   └── errors.py         #   **零改动**
└── graph.py              # 门面（facade-L1-L3）· **零改动**（本 feature 不碰）

tests/
├── runtime/
│   ├── test_superstep_concurrency.py   # ★ 新增：并发 · 顺序 · 合并语义
│   ├── test_superstep_errors.py         # ★ 新增：异常 identity · 取消 · 附注 · 中断
│   ├── test_superstep_contract.py       # ★ 改：test_i12 的 docstring / 命名（T-8）
│   ├── test_superstep_*.py              # ★ 改：7 处顺序敏感断言的拆分（T-6）
│   └── test_command_*.py                # ★ 改：同上
└── differential/
    ├── parity_probe.py                   # ★ 改：追加 D-01…D-15 场景组
    └── test_parity_probe.py              # ★ 改：打包器（CI Linux 全量档真跑）

harness/verification/B12F1/
├── acceptance.py          # ★ 新增：机械层一键验收（原则 V）
└── manual-verification.md # ★ 新增：五段式 + 追认文字
```

**Structure Decision**：**沿用仓库既有的 L1 / L2 / 门面三层**（层注册表 `layer-registry.md` 已登记
`src/freegraph/runtime/` 为**目录条目**）⇒ ⇒ **层注册表零改动**、门禁 **G25** 实现零改动 ⇒
⇒ 并发执行器 MUST 作为 **L2 内的**非导出模块（`_concurrency.py`）存在 ⇒
⇒ ⚠️ **MUST NOT** 为它在 `runtime/` 下单独立注册表条目（会造成 L2 → L2 的横向依赖误判）。

### ── 本 feature **触及**的文件（**表格 23 行 · 实际 28 个文件** · 新增 **5** / 修改 **20** / 核对 **3** · 登记项 PR-1…PR-11 / T-1…T-11 / 下游承接 D-1…D-7） ──

> ⚠️ **计数订正（2026-11-13 · 对账补记）**：本表**表格 23 行**，但**第 8 行**一行代表 **5 个**测试文件
> · **第 18 行**一行代表 **2 个**文件（`acceptance.py` + `manual-verification.md`）⇒ ⇒
> **实际触及 28 个文件**（新增 **5** · 修改 **20** · 核对 **3**）⇒ ⇒ 原写的「十九处 · 修改 **14**」**已过时**。
> ⚠️ **2026-11-13 分析轮补记**：新增第 **23** 行（`harness/demo/graph_core.py` · **核对**项）⇒
> 表格 **22 → 23 行** · 实际触及 **27 → 28 个文件** · **核对 2 → 3**。

| # | 文件 | 动作 | 依据 |
|---|---|---|---|
| 1 | `src/freegraph/runtime/superstep.py` | **改** | 阶段 ③ 并发化 · `_execute_node` 拆分 · 两入口增 `max_concurrency` |
| 2 | `src/freegraph/runtime/_concurrency.py` | **新增** | 并发执行器（内部） |
| 3 | `tests/differential/parity_probe.py` | **改** | 追加 **D-01…D-15** |
| 4 | `tests/differential/test_parity_probe.py` | **改** | 打包器 |
| 5 | `tests/runtime/test_superstep_concurrency.py` | **新增** | — |
| 6 | `tests/runtime/test_superstep_errors.py` | **新增** | — |
| 7 | `tests/runtime/test_superstep_contract.py` | **改** | **T-8**（`test_i12`） |
| 8 | `tests/runtime/test_command_contract.py` · `tests/runtime/test_command_goto_semantics.py` · `tests/runtime/test_command_list.py` · `tests/runtime/test_command_merge_parity.py` · `tests/runtime/test_superstep_trigger.py` | **改** | **T-6**（**5** 个文件 / **10** 处顺序敏感断言的拆分 · 清单见 research **§2 C-01**）|
| 9 | `specs/b7f1-superstep-loop/contracts/superstep-contract.md` | **改** | **T-1 / T-2 / T-4 / T-5 / T-7 / T-8 / T-10** |
| 10 | `specs/b7f1-superstep-loop/spec.md` | **改** | **T-3 / T-11** |
| 11 | `specs/b12f1-concurrency-errors/contracts/concurrency-contract.md` | **核对** | 本 feature 的唯一权威契约（**已于 2026-11-13 产出** · 已含阶段 ③ / ③′ / ⑥ 口径 ⇒ 实现期若有出入 MUST 同步该契约 · 归 **T001** 核对） |
| 12 | `specs/b12f1-concurrency-errors/contracts/upstream-parity.md` | **核对** | 证据表（**已于 2026-11-13 产出** · 归 **T001** 核对） |
| 13 | `harness/features/B10F1_interrupt与resume.md` | **改** | **D-1 / T-9**（+ Q17 的补充） |
| 14 | `harness/features/B14F1_Checkpointer协议与MemorySaver.md` | **改** | **D-5 / D-6** |
| 15 | `harness/features/B7F2_compile编译.md` | **改** | **D-4** |
| 16 | `harness/features/B7F3_invoke返回完整状态.md` | **改** | **D-2 / D-4** |
| 17 | `harness/features/B19F1_TraceSink与current_span.md` | **改** | **D-3** |
| 18 | `harness/verification/B12F1/{acceptance.py,manual-verification.md}` | **新增** | 原则 V |
| 19 | `harness/features/B15F1_SqliteSaver与状态历史.md` | **改** | **D-7**（`StateSnapshot.interrupts` 的**生产者口径** · 裁定 25 ④ · **M3**）⇒ ⚠️ **该条款已由 2026-11-13 02:42 落盘** ⇒ 实现期**只核对**（tasks **T071**）|
| 20 | `specs/b2f1-contracts-protocols/contracts/public-api.md` | **改** | **R-10**（§0 的「**恰好 N 个**」文案 18 → **20** + P3 批次注记 · G7 行 · 「公开符号面严格 = N 个」行）⇒ **判据零改动**（清单驱动）|
| 21 | `specs/b2f1-contracts-protocols/spec.md` | **改** | **R-10**（FR-012 / SC-017 的**回溯注记** · **不改写历史**）|
| 22 | `tests/contracts/test_architecture.py` | **改** | **T082**（G7 docstring 的「**恰为 18 个**」文案 → **清单驱动 · 当前 20 个** ⇒ **断言零改动**）|
| 23 | `harness/demo/graph_core.py` | **核对** | ⚠️ **2026-11-13 分析轮补记**：spec 把该文件的 **A7** 用例（`:403-441` · 并发与错误传播）当作**验收契约锚点**引用（`:380-382` 的 `hasattr(first,"value")` 更是「裁定 7」的决定性理由）⇒ 但它**既不在**本表、**也不在** `tasks.md` 的任何任务里 ⇒ **契约面无演进责任人** ⇒ 本 feature **只核对**（**不改逻辑** —— 它依赖 `StateGraph` / `compile()` / `invoke()`，属 **B7F2 / B7F3**）⇒ **核对内容** = A7 的两个断言与 **A1 / A2** 的差距（如实登记进人工验证记录的「遗留问题」段 ⇒ 登记项 **PR-11** 的遗留问题面）⇒ ⚠️ **A1 的真并发判据**（时间窗 / 屏障）本 feature **无法**在 A7 里落地（无图可跑）⇒ **不得**把 A7 现状误当作 A1 已通过 |

> ⚠️ **零改动清单（断言 · 指「**本 feature** 的改动面」）**：`src/freegraph/contracts/**`（L1 冻结面）· `src/freegraph/runtime/channel.py`
> · `src/freegraph/runtime/read.py` · `src/freegraph/runtime/__init__.py`（导出面 **20**）·
> `src/freegraph/graph.py`（门面 **7**）· `src/freegraph/_stategraph.py` ·
> `pyproject.toml`（依赖面零）· `THIRD_PARTY_NOTICES` · **API 兼容矩阵** · **门禁实现**。
> ⇒ ⚠️ **例外说明（2026-11-13 · R-10）**：L1 在**上游对齐批次 P3**（发起者已批准 · 已落地）里
> **已有一次**改动（`Interrupt` / `PregelTask` · C17 / C19 / C20）⇒ ⇒ 「零改动」指
> **本 feature 自身**对 L1 **零新增** ⇒ ⇒ **判据基线 = 20**（非 18）。

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **并发执行器作为独立的 L2 内部模块**（`_concurrency.py`） | 并发度计算 · 线程池生命周期 · **取消语义** · 结果槽收集 · **首个异常选取** · **附注** · **中断合并** —— **七件事职责耦合**，混进 `superstep.py`（**实测 `:1018` 行** · 2026-11-13）会让 B7F1 的既有逻辑无法单独阅读 ⇒ ⇒ **另立模块的理由是「职责分离」，不是「文件太大」** | **不另立模块**：`_run_round`（`:903-932` · **实测约 30 行**）本身不长 ⇒ **故「文件太大」不是理由**；真正的理由是**职责分离** —— 再塞七件事 ⇒ 阶段 ③ / ③′ / ⑥ 的并发语义**淹没**在 B7F1 的既有逻辑里 ⇒ 审查与回归都无从下手 ⇒ ⇒ 另立**内部**模块 ⇒ **导出面零变化**（`_concurrency.py` **不进 `__all__`**）⇒ 冻结面**不受影响** |
| **每任务一个「结果槽」**（而不是直接写共享调度状态） | 并发写共享可变状态是**竞态来源**（即便 CPython 的 dict 写入原子，「读-改-写」与「迭代」仍不安全）⇒ 执行期 MUST 只产出**私有**结果 | **直接写共享状态**（现状）：同轮「A 成功、B 抛错」时 A 的版本**已推进** ⇒ 出错轮出现「**值没合并、版本却推进**」的**幽灵触发** ⇒ 且并发下是**数据竞争** ⇒ ⇒ 改「轮末按**节点名序**统一落回」⇒ 与 B7F1 的**五阶段**结构同构 ⇒ 零新概念 |
| **每轮一个线程池**（而不是复用全局池） | 线程池 MUST 在**本轮返回前**结束 ⇒ **零悬挂线程**（SC-025）⇒ 且「一轮之内」的并发度上限语义清晰 | **复用全局池**：线程跨轮存活 ⇒ 「连续 ≥ 10 轮线程数不增长」仍可满足，但**归属**不清（哪一轮的线程？）⇒ ⇒ 每轮新建 + 关闭 ⇒ 与上游 `BackgroundExecutor.__exit__`（`_executor.py:93-119`）**同款** |
| **首次异常 = 节点名序**（而非完成时刻） | 完成时刻 ⇒ **竞态** ⇒ 同一张图两次运行抛不同的异常 ⇒ **不可复现** ⇒ 违反 SC-002 / SC-005 | **完成时刻**（上游同款）：**实测** 50 次 ⇒ **26 / 24** 分布 ⇒ 判据不可判定 ⇒ ⇒ 取**节点名序**（**比上游更严** · **X-1** · 已标注） |
| **其余失败以 `add_note` 附注**（而非丢弃） | 上游丢弃 ⇒ 失败信息**无声消失** ⇒ 违反「**MUST NOT 静默吞掉**」 | **丢弃**（上游同款）：调用方**看不到** ⇒ ⇒ 附注（**标准库**机制 · 不改类型 / 消息 / 对象 identity）⇒ **比上游更严** · **X-2** · 已标注 |
| **取消「排队未启动」者**（而**非**全部） | 「取消全部」会**中断运行中的用户代码** ⇒ 用户**无法**善后 ⇒ 且与上游**不符** | **取消全部**：上游只对**未完成**的 future 调 `.cancel()` ⇒ 运行中的**取消不掉**（`cancel()` 返回 `False`）⇒ ⇒ 照抄 ⇒ **V-2** |
| **中断元组顺序 = 节点名序** | 上游顺序**竞态**（**实测** 200 次 ⇒ **199 / 1**）⇒ 「待审批列表」顺序会飘 | **照抄上游顺序**：用户看到的顺序**不可复现** ⇒ ⇒ **节点名序**（**比上游更严** · **X-7** · 已标注） |
| **质量门禁 3 / 4 / 5 的三部分在本 feature 物理不可达成**（**登记项 PR-11** · 宪法 **v1.6.0** 窄口径通则） | 三者**共享同一根因**：都要求**完整内核运行时**（`StateGraph` + `compile()` + `invoke()` + 条件边）存在，而本 feature 按立项书 §5.2 **只交付 L2 的并发执行 / 错误传播 / 中断合并**（`StateGraph` = **B6F1** · `compile` = **B7F2 / M2** · `invoke` = **B7F3 / M2** · 条件边 = **B8F1 / M2**）⇒ ⇒ **本 feature 无图可跑** ⇒ ⇒ 任何 spec 设计都**无法**在本 feature 满足这三条 ⇒ 依宪法 **v1.6.0** 处置（**偏离登记 PR-11 + 发起者追认（并入 T080 的一次）+ 具名承接方**）⇒ ⇒ **红线判据一律不放宽** | **替代方案 A：硬写进 CI**（让验收脚本在「无图可跑」时判通过而不登记）⇒ **静默稀释宪法** + 门禁语义被扭曲 ⇒ **不可行**。<br>**替代方案 B：写一条永久红的 CI** ⇒ 违反「feature 必须能独立通过其可适用门禁」⇒ **不可行**。<br>**替代方案 C：改宪法正文** ⇒ 违反「**MUST NOT** 以本条删改宪法正文」⇒ **不可行**。<br>**替代方案 D：把 B12F1 扩成「并发 + 构建器 + invoke」** ⇒ 越过立项书的 feature 边界 ⇒ **不可行**。<br>**采用的处置**：**偏离登记（PR-11）+ 发起者追认（`tasks.md` 的 **T080** · 同一次打包）+ 承接条款已在目标 feature 的提示词初稿中既有**（B6F1 / B7F2 / B7F3 / B8F1 / B25F1）⇒ **红线判据一律不放宽**。 |
