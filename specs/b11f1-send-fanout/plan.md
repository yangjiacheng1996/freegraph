# Implementation Plan: B11F1 · `Send`：动态 fan-out / map-reduce

**Branch**: `b11f1-send-fanout` | **Date**: 2026-11-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/b11f1-send-fanout/spec.md`（**2026-11-14 澄清轮两轮后**的版本）

> **本 plan 的工件**：Phase 0 → [research.md](./research.md) · Phase 1 → [data-model.md](./data-model.md) ·
> [contracts/send-contract.md](./contracts/send-contract.md) ·
> [contracts/upstream-parity.md](./contracts/upstream-parity.md) · [quickstart.md](./quickstart.md)
> ⇒ **Phase 2 的 `tasks.md` 由 `/speckit.tasks` 产出**（本命令**不**产出）。
> ⚠️ **唯一权威**：本 feature 的**需求与判据**以 `spec.md` 为准 ⇒ 本 plan 只**承接**它 ⇒
> ⇒ 本 plan 与 contracts / research 里的数值**一律以 spec 为准**（若不一致 ⇒ 以 spec 为准并回修本 plan）。

---

## Summary

**交付什么**：让 L2 调度内核**真正支持 `Send` 的动态 fan-out** —— 条件边 / 节点可以返回
`Send`（**目标节点 + 自定义入参**）⇒ **同一个目标节点被调用多次**，每次拿到**自己的**入参 ⇒
⇒ **map-reduce 模式可运行**（立项书 §5.2 B11F1 行的小目标）。

**技术路线**（零第三方依赖 · 零出站 · 零环境变量）：

| 关注点 | 落法 |
|---|---|
| **载体** | **双载体**：**A** = `Command.goto` 装 `Send`（**上游同款** · 澄清轮第 2 次 **B**）· **B** = 节点**直接返回** `Send` / `list[Send]` / `tuple[Send, ...]`（**验收脚本锁定**）⇒ 二者**共用同一套** fan-out 语义 |
| **落点** | **下一轮**执行（与 `goto` **同族的落点**）· 它是**派发任务**、**不登记为边触发源**（**不消费**触发源版本）⇒ **上游同款**（SEND tasks in superstep n+1） |
| **入参形态** | **arg 逐字替代**标准入参（**不合并** · **不过滤**）⇒ **上游同款**（实测 E-3 / E-4） |
| **多次调用** | **N 个 `Send` ⇒ N 次独立调用**（同轮并发 · 上限同 B12F1）⇒ **上游同款**（E-1 / E-6） |
| **任务标识** | **TaskId** = **本轮任务的规范序号（`int` · 0 起）** ⇒ 按 **FR-005 的上游任务序**分配：**标准触发任务按目标节点名序 → fan-out 任务按产生者任务序 · `Send` 序号** ⇒ **排序键 = TaskId 本身** ⇒ 归并顺序**天然确定** ⇒ ⚠️ 同一节点在一轮内执行多次 ⇒ **各次任务各有独立 TaskId**（MUST NOT 只用节点名做键）。**持久化 `task_id`（F-13）**：标准任务 = **节点名**；fan-out 任务 = **`f"{节点名}:{TaskId}"`** |
| **抑制所需标识** | `_FanOutTask` **逐任务携带 `suppresses_static`**（载体 A=`False` · 载体 B=`True` · **归一形状的载体信息源**）· `_FanOut` **携带 `producer`（产生者节点名）与 `suppresses_static`（抑制判定的唯一聚合源 · MUST 由其 `tasks` 的载体标志聚合 · 同一执行内全部同值）⇒ 载体 B 抑制按 **(producer, target)** 匹配（**归一形状 MUST NOT 丢失载体/产生者信息**） |
| **并发器** | **复用** B12F1 的线程池与上限 ⇒ ⚠️ **结果槽的键**由节点名改为 **TaskId**（否则同节点多任务**互相覆盖**） |
| **写入路径** | **复用** B7F1 的**批量**合并（每通道**一次** `Channel.update(values)`），但**收集顺序改为 TaskId 序**（标准任务按目标名序 → fan-out 按产生者任务序 + `Send` 序号）⇒ 写收集同时产出 **`ordered_writes: list[(TaskId, target, writes)]`**，`_group_writes` 遍历它（不再遍历 `sorted(spec.nodes)`）；`node_writes` 仍按目标节点名聚合供结果 ⇒ **MUST NOT** 另写一条合并实现 |
| **失败信号** | 目标不存在 ⇒ **显式失败**（`ValueError` · **同时点名产生者与目标**）⇒ **比上游更严**（**X-1**） |
| **与静态边并存** | **按载体分列**：载体 A **叠加**（上游同款）· 载体 B **`Send` 胜出**（验收脚本锁定）⇒ ⚠️ **DR-03** |
| **可验证出口** | 交付 **9 条差分探针场景**（**D-29…D-37** · `tests/differential/parity_probe.py`）⇒ CI Linux 全量档**真跑** |

**与上游的关系**（宪法原则 XI）：**内容照抄上游**（载体 · 落点 · 入参 · 次数 · 并发 · 归并顺序 · 「既派发又写入」）
⇒ 仅三处**刻意**分叉（**X-1 / X-3 / X-6**）⇒ 逐条登记于
[contracts/upstream-parity.md](./contracts/upstream-parity.md)。

---

## Technical Context

**Language/Version**: Python **>= 3.11**（typing 构件上限 = **3.11** · 禁用 `TypeAliasType` / `override` / `ReadOnly` / `TypeIs` / PEP 695 `type` 语句）

**Primary Dependencies**: **零**（`dependencies = []`）⇒ ⚠️ 上游 `langgraph` / `langchain-core` **仅作 dev/test 依赖**（PEP 735 依赖组）⇒ **绝不进** `Requires-Dist` ⇒ 门禁 **G3 / G21 / G23** 恒绿

**Storage**: **N/A**（v1 无 checkpoint ⇒ **B14F1 / M3**）⇒ 本 feature **零文件 I/O** · 零持久化（⚠️ **B11F1 交付时** fan-out 载荷**不落盘** · research D-08 / DR-02；**B13F1 F-3 起** `to_checkpoint` 含 `fanout`，存储仍归 B14F1）

**Testing**: **pytest**（dev 依赖组）+ **差分探针**（`tests/differential/parity_probe.py`）⇒ 上游**缺席即 skip**（B5F2 的「缺席即 skip」纪律）

**Target Platform**: Linux / macOS / Windows（**线程**语义跨平台 ⇒ 无 POSIX-only 依赖）

**Project Type**: **library**（可复用内核 · 无服务 / 无 UI）

**Performance Goals**:
- 一轮 fan-out 的墙钟时间 ≈ **最慢的那个任务**（而非各任务之和）⇒ 夹具可判定（SC-010 · 上游 E-6：两个各 0.3s ⇒ **0.308s**）
- 实际并发度 == `min(本轮任务数, min(32, cpu+4))` ⇒ 缺省**有上限**（**上游同款**）
- 连续运行 **≥ 10** 轮后进程内线程数**不增长** ⇒ **零悬挂线程**（沿用 B12F1 的 I-16 · **由 T025 的线程计数子例覆盖**）

**Constraints**:

| # | 约束 | 依据 |
|---|---|---|
| C-1 | **零出站** / **零环境变量** / **零文件 I/O** | 宪法原则 **I / II** · FR-013 |
| C-2 | **L2 只依赖 L1** ⇒ **MUST NOT** import 门面（L3）/ L4 / L5 · **MUST NOT** 横向依赖其它 L2 模块 | 宪法 **ARCH-1** · FR-012 · 门禁 **G25** |
| C-3 | `freegraph.runtime.__all__` **仍为 23** ⇒ fan-out 模块 MUST 是**私有**（`_fanout.py`） | FR-014 · B12F1 裁定 13 的**同款**先例 |
| C-4 | `SuperStepResult` **四字段冻结面零改动**（只改 `executed` 的**成员口径**） | 裁定 13 · B12F1 裁定 25 |
| C-5 | `SchedulerState()` **构造签名逐字不变** ⇒ **只增一个带缺省值的字段** | B9F1 裁定 12 的**同款**先例 |
| C-6 | 门禁编号 **G1–G30** **连续无跳号**、总数 == **30** | FR-021 |
| C-7 | **NOT** 引入 async / 事件循环抽象 | FR-020 |
| C-8 | **NOT** 读环境变量 ⇒ 上游的 `LANGGRAPH_DEFAULT_RERECURSION_LIMIT` 覆盖**不采纳** | 沿用 B12F1 的 C-8 |
| C-9 | ⚠️ **L1 冻结面**：符号面 **20 → 21** · `Command.goto` 注解 · `NodeFunc.__call__` 返回联合 ⇒ **仅此三处**（**经发起者特批** · 澄清轮第 2 次 **B**）；⚠️ **另加 docstring / C5 注记**（`Send` 入参可为非 dict · **非签名变更** · **H3 / F-11**） | FR-003 / FR-012 / FR-014 · 裁定 11 / 14 · **PR-1…PR-3** |

**Scale/Scope**: 立项书 §5.2 的 **980 行 / 3 人日** ＝ **初版口径** ⇒ ⚠️ 本 plan 的实际规模以 `tasks.md`
（**已产出 · T001–T095**）为准 ⇒ 立项书的数字 MUST 由**发起者**在 feature 收尾时重估回写
（本 feature **MUST NOT** 单方面改上位文档 ⇒ **T092** 登记「遗留问题」）

**本 feature 的主要改动面**（**摘要** ⇒ ⚠️ **完整清单见「触及的文件」表**）：

| # | 文件 | 动作 | 说明 |
|---|---|---|---|
| 1 | `src/freegraph/contracts/types.py` | **改** | `Send` 的类型定义**迁入**（与 `Command` 同模块）· `Command.goto` 注解放宽 |
| 2 | `src/freegraph/contracts/__init__.py` | **改** | 导出 `Send`（**20 → 21**）· 更新模块 docstring（「本层不导出 Send」已过时） |
| 3 | `src/freegraph/contracts/protocols.py` | **改** | `NodeFunc.__call__` 返回联合增补 `Send` / `list[Send]` / `tuple[Send, ...]` |
| 4 | `src/freegraph/graph.py` | **改** | 门面从 **L1** 转出 `Send`（导出面 **7** 不变） |
| 5 | `src/freegraph/_primitives.py` | **删** | 文件整体（`Send` 迁出 ⇒ 只剩它） |
| 6 | `src/freegraph/runtime/_fanout.py` | **新增** | fan-out 载荷的解析 / 校验 / 任务构造 / 触发组抑制 / **TaskId** / **`producer`**（**私有**） |
| 7 | `src/freegraph/runtime/superstep.py` | **改** | 归一扩展 · 阶段 ②′ · 触发组抑制 · 落回 · 写入收集（`ordered_writes`）· `executed` · **`by_name` 键改 TaskId** |
| 8 | `src/freegraph/runtime/_concurrency.py` | **改** | 结果槽的键 → **TaskId** · `_TaskOutcome` 增 `fanout` 字段 |
| 8b | `src/freegraph/runtime/_interrupt.py` | **改** | **任务级现场键**由节点名改为**任务标识**（TaskId）⇒ 同节点 N 次 fan-out **不共享 scratchpad**（与 B10F1 恢复口径对齐） |
| 9 | `tests/differential/parity_probe.py` | **改** | 追加 **D-29…D-37**（判词三态） |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 通过项（逐条 · 原则 I–XII）

| 原则 | 判定 | 本 feature 的落实 |
|---|---|---|
| **I** 零 LangSmith 依赖 | ✅ | 零导入（SC-021）· 上游仅 dev/test 依赖组 |
| **II** 内核纯净 | ✅ | 零 LangChain / LangGraph 导入 · 零出站 · 零环境变量（FR-013） |
| **III** 验收契约优先 | ✅ | 载体 **B** **逐字**照搬验收脚本的 C18 形态（节点返回 `list[Send]` + 同一条静态边）⇒ **MUST NOT** 改写 `harness/demo/`（**核对项** · T-13）· ⚠️ 该用例当前**不可跑**（B6F1 / B7F2 / B7F3 未接线）⇒ 如实登记（quickstart §0.3） |
| **IV** 可诊断性是一等功能 | ✅（**更严** · 不新增可观测面） | 失败消息**同时点名产生者与目标**（澄清轮第 2 次 Q3 = **A** · SC-003）⇒ 本 feature **零新增** span / trace / 结果字段（FR-020）⇒ 触发源的暴露归 **B19F1**（**D-5**） |
| **V** 人工验收是最终验收标准 | ✅ | `harness/verification/B11F1/manual-verification.md`（**五段式** + **来源覆盖表 100%**）+ **追认文字**（FR-016 / SC-017） |
| **VI** 规格驱动开发 | ✅ | 三件套齐备（spec · plan · 契约）⇒ `tasks.md` 由 `/speckit.tasks` 逐条勾选 |
| **VII** 职责边界与内核契约 | ✅ | 契约 **C1–C27** 的**条目**零改动（只落**运行期语义**）⇒ ⚠️ **例外**：**L1 的 `Send` 类型落位**（见「破冻结面」）⇒ **C18** 的**语义**由本 feature 交付 |
| **VIII** 证据与术语纪律 | ✅ | 上游引用带**版本 + `路径:行号`**（FR-015）· **行为**断言全部有**实测**支撑（E-1…E-11 · research §1）· 术语统一（`Send` / fan-out 任务 / fan-out 载荷 / 边触发源） |
| **IX** 依赖许可证与商标红线 | ✅ | 零新增依赖 ⇒ **G3 / G21 / G23** 恒绿 |
| **X** 文档合规义务 | ✅ | 署名头逐字（FR-018）· 兼容矩阵**零新增行**（仅 `Send` / `Command` / `NodeFunc` 三行**措辞更新**） |
| **XI** 上游优先 | ✅（**内容照抄**） | 载体 / 落点 / 入参 / 次数 / 并发 / **归并顺序（P-13）** / 「既派发又写入」**全部照抄** ⇒ 仅 **3 条**刻意分叉（**X-1 / X-3 / X-6**）⇒ **9 条差分场景**（D-29…D-37）落地 ⇒ 对照表与偏离登记的标注**逐字一致**（v1.12.0） |
| **XII** 最优设计优先 | ✅ | 载体与类型落位**取上游的最优形态**（同模块 · 一次返回两件事）⇒ 而非在既有形态上打补丁 ⇒ 破冻结面时**一并回溯修订 + 追认**（不保留次优形态） |

### ⚠️ 登记项（**偏离登记 + 发起者追认** · 宪法原则 XI / 跨 feature 承接通则）

| # | 登记项 | 类别 | 判据 | 追认范围 |
|---|---|---|---|---|
| **PR-1** | `Send` 的**类型定义**归 **L1**（与 `Command` 同模块） | **破 L1 冻结面**（经发起者特批 · 澄清轮第 2 次 **B**） | FR-012 / FR-014 · 裁定 11 | **F-1…F-14** 一次性追认（≤ 1 次） |
| **PR-2** | L1 公开符号面 **20 → 21** | **破 L1 冻结面**（G7 基线） | FR-014 · SC-015 | 同上 |
| **PR-13** | **B10F1 任务标识 / 中断现场** 从「节点名 · 一轮一个节点一个任务」拆分为「标准 = 节点名 · fan-out = `节点名:TaskId`」 | **破跨 feature 冻结契约**（**F-13**） | FR-009 · SC-011 · DR-01 | **F-1…F-14** 一次性追认（≤ 1 次） |
| **PR-14** | **B7F1 / B9F1 / B12F1 / B10F1（`.executed`）的顺序 / 阶段模型 / 执行次数** 增补 fan-out 分支（**F-14**） | **破跨 feature 冻结契约** | FR-005 / FR-009 / FR-010 · SC-008 / SC-011 / SC-022 | 同上 |
| **PR-3** | `Command.goto` 注解 + `NodeFunc.__call__` 返回联合的**放宽** | **破 L1 冻结面**（协议面） | FR-012 / FR-014 | 同上 |
| **PR-4** | 并发器结果槽的**键**由节点名改为 **TaskId**（本轮规范序号 `int`） | **内部结构变更**（**非**公开面） | FR-004 / FR-010 · research D-02 | 不进追认范围（**私有**） |
| **PR-5** | `SchedulerState` **新增一个**带缺省值的字段 `fanout: dict[TaskId, _FanOut]`（**按产生者任务**记录 · 不是按节点名；`_FanOut` **另带 `producer`** 供载体 B 抑制按 `(producer, target)` 匹配，并带 **`suppresses_static`（抑制判定的唯一聚合源）**） | **内部结构变更**（构造签名**不变**） | FR-002 / FR-005 / FR-006 · research D-03 | 不进追认范围 |
| **PR-6** | 归一形状**增一个键** `fanout`（`_FanOutTask` **逐任务携带 `suppresses_static`** · **归一形状的载体信息源**）+ `_TaskOutcome` **增一个字段** + 写收集产出 **`ordered_writes`（按 TaskId 序）** | **内部结构变更**（**非**公开面） | FR-001 / FR-005 / FR-006 · research D-05 | 不进追认范围（**契约文档已回溯修订** · **T-10 / T-12** 改为核验项） |
| **PR-7** | **载体 A / 载体 B** 的「与静态边并存」口径**不同** | **刻意**（两边各服从自己的权威） | FR-006 · 裁定 5 · **DR-03** | **须在人工验证记录里显著写明**（不追认） |
| **PR-8** | **B11F1 交付时** fan-out 载荷**不落盘**（⚠️ **B13F1 F-3 起拆分**：`to_checkpoint` 含 `fanout`，存储仍归 B14F1） | **已知限制**（载荷含用户对象） | research D-08 · **DR-02** | 归 **B14F1**（**D-3**） |
| **PR-9** | **立项书 §5.1** 的分层裁定修订（`Send` 从 L2 归 L1：L2 层描述 / L1 层描述 / 公开 API 行 / ARCH-1 行）+ **§5.2** 的 B11F1 依赖列（补 `B1F1,B9F1,B12F1,B10F1`）+ **§5.3** 的 C18 行（`v2 提供` ⇒ `v1 提供（B11F1）`） | **上位文档修订** | 裁定 11 · **F-6** | **须由发起者本人签字** |
| **PR-10** | **下游接线 D-1…D-8**（往 **7** 份目标 feature 的提示词初稿追加条款） | 宪法 v1.8.0 的接线通则 | 下游承接表 | 不进追认范围 |
| **PR-11** | **差分场景 D-29…D-37**（追加到既有探针） | 可验证出口 | FR-019 | 不进追认范围 |
| **PR-12** | fan-out 任务的**中断 id** 可能重复 | **已知限制 · 本 feature 修复**（任务级现场键 → TaskId · **F-13**） | **DR-01** | **T027**（上下文隔离）· **T034**（用例）· **T093 / T095**（持久化 / B15F1）· 与 **B10F1** 的恢复口径对齐 |

**登记项 → 任务落点**（**可机械核对** · 与 `tasks.md` 的同名附录逐条一致）：

| 登记项 | 落点任务 | 登记项 | 落点任务 | 登记项 | 落点任务 |
|---|---|---|---|---|---|
| **PR-1**（`Send` 归 L1） | T006 · T008 · T009 · T010 · T011 | **PR-7**（两载体口径分列） | T054 · T056 | **PR-10**（下游接线） | T076…T081 · T095 |
| **PR-2**（L1 符号面 20 → 21） | T007 · T067 | **PR-8**（载荷不落盘 → **B13F1 F-3 拆分**） | T019 · T078 | **PR-11**（差分场景） | T060 · T061 · T062 |
| **PR-13**（B10F1 任务标识 / 中断现场） | T093 · T095 | **PR-14**（B7F1/B9F1/B12F1/B10F1 顺序 / 阶段 / 执行次数） | T094 | — | — |
| **PR-3**（协议面放宽） | T008 · T009 · T073 | **PR-9**（立项书修订） | T068 | **PR-12**（中断隔离） | T027 · T034 · T093 · T095 |
| **PR-4**（结果槽键 → TaskId） | T014 · T015 | **PR-5**（`SchedulerState.fanout`） | T013 | **PR-6**（归一形状 / `ordered_writes`） | T012 · T015 · T035 · T036 · T059 |

### 破冻结面的回溯修订清单（**T-1…T-15** · **拆分而不删**）

> ⚠️ **实测化**（宪法 v1.11.0）：下表的「变红」判定来自 **research §2** 的**实跑探测**
> （绿基线 **1184 passed / 4 skipped**）⇒ **MUST NOT** 只凭推理登记。

| # | 对应 | 冻结面（`文件:行号`） | 处置 |
|---|---|---|---|
| **T-1** | **F-1** | 层注册表 `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` §1 的 `src/freegraph/_primitives.py` 条目 | **删除**该**陈旧条目**（文件随之删除）⇒ 其余 **11** 条**一字不动** · G25 的**判定规则**一字不动 ⇒ ⚠️ **MUST NOT** 为 `runtime/_fanout.py` 新增条目（否则 L2 → L2 横向依赖误判） |
| **T-2** | **F-2** | `tests/runtime/test_superstep_concurrency.py:800-808`（「`_primitives.py` 只留 `Send`」） | **拆分而不删**：原断言的**意图**（「`interrupt` 的实现体不在门面私有模块里」）**保留** ⇒ 改为对 `runtime/_interrupt.py` 的断言 + 增补「`Send` 的类型定义在 **L1**」 |
| **T-3** | **F-3** | `tests/facade/_gatesupport.py:46` · `:60`（`SIGNED_SOURCE_FILES` / `FACADE_MODULES`） | **移除**已删文件的条目 ⇒ G20 / G14 的**判据一字不动** |
| **T-4** | **F-4** | README「兼容矩阵」的 **`Send` 行 + `Command` 行 + `NodeFunc` 行** | **零新增行**；`Send` 行**措辞更新 MAY**；`Command` 行 MUST 删去「`goto` 目标**只能是节点名**（上游可混入 `Send` —— 归 v2 / B11F1）」这句**已过时**的措辞；`NodeFunc` 行 MUST 在「返回形态」增补 `Send` / `list[Send]` / `tuple[Send, ...]`（与 F-11 对齐） |
| **T-5** | **F-5** | `tests/contracts/test_architecture.py:450` · `:1511`（G7）· `tests/runtime/test_read_contract.py:63` · `:561` · `tests/runtime/test_command_purity.py:287` · `specs/b1f1-contracts-core/contracts/public-api.md` §0（**清单来源**） | **拆分而不删**：基线 **20 → 21** + **集合成员**增 `Send`（集合相等的判定逻辑**一字不动**）⇒ 清单与断言**同步** |
| **T-6** | **F-6** | `harness/proposals/立项书.md` §5.1 的 **4 处**（L2 层描述 / L1 层描述 / 公开 API 行 / ARCH-1 行）· §5.2 的 B11F1 依赖列 · **§5.3 的 C18 行** | **逐处**改为「`Send` 属 **L1**（纯数据类 · 运行期语义归 L2 · B11F1）· `interrupt` 属 L2」；§5.2 依赖列补 `B1F1,B9F1,B12F1,B10F1`；§5.3 的 C18 行「对上承诺 = `v2 提供`」⇒ **`v1 提供（B11F1）`**；§5.1 / §5.3 的**其余行一字不动** ⇒ ⚠️ **须由发起者本人签字**（**PR-9**） |
| **T-7** | **F-7** | `harness/proposals/上游对齐审计.md` §2.1 **P-05**（「上游可装 `Send`」）与 §3 **第 13 行** | **P-05** 标注「✅ 已关闭（B11F1）」；第 13 行的**落位**一项标注「已消解」⇒ 其余 3 处（可变性 / 哈希性 / `timeout`）**留待上游对齐批次 P3-8** |
| **T-8** | **F-8** | `specs/b2f1-contracts-protocols/contracts/public-api.md` · `specs/b2f2-public-api-facade/contracts/facade-api.md` · ⚠️ **plan 级补充**：`specs/b2f2-public-api-facade/contracts/architecture-gates.md:143`（「`Send` 归 L2」一句） | `Send` 的**层级归属**与 `Command.goto` 的**注解**逐字更新 ⇒ **零新增符号** |
| **T-9** | **F-9** | `specs/b1f1-contracts-core/data-model.md:70` 与 `specs/b1f1-contracts-core/contracts/public-api.md:103`（`goto` 字段行） | 「目标**只能是节点名**」⇒ 逐字改为「目标**可以是节点名或 `Send`**（`Send` 归 L1 · B11F1 接线）」⇒ 其余条目**一字不动** |
| **T-10** | **F-10** | `specs/b9f1-command-primitive/contracts/command-contract.md` 的「`goto` 的形态解析」节（**V-12 / V-13 / V-14** · **I-5**）与 §2 的**归一形状** | **增补**「`goto` 槽位里的 `Send` 元素」的逐元素分派与失败信号 · 归一形状**增一个键** `fanout` ⇒ **既有断言一条不删** |
| **T-11** | **F-11** | `src/freegraph/contracts/protocols.py` 的 `NodeFunc.__call__` 注解与 docstring · `tests/contracts/test_protocols.py:136` | 返回联合**增补** `Send` / `list[Send]` / `tuple[Send, ...]` ⇒ 七形态 ⇒ **拆分而不删**（四形态的既有断言**保留**） |
| **T-12** | **F-12** | `specs/b12f1-concurrency-errors/contracts/concurrency-contract.md` §4（`_TaskOutcome` 的形状） | **增补** `fanout` 字段与「键 = TaskId」的口径 ⇒ 既有断言**一条不删** |
| **T-13** | **核对项**（⚠️ **不是回溯修订** ⇒ **不计入** SC-020 的「F-1…F-14 逐条落地」条数） | `harness/demo/graph_core.py` 的 **C18** 用例 | **核对**（**不改**）⇒ 确认形态与 §1 一致 ⇒ ⚠️ 当前**不可跑**（构建器未接线）⇒ 如实登记 |
| **T-14** | **F-13** | `specs/b10f1-interrupt-resume/contracts/checkpoint-contract.md` §5 · `interrupt-resume-contract.md` §3 / §4.1 · `specs/b10f1-interrupt-resume/spec.md` 的任务现场 / `.id` 段 | **拆分而不删**：`task_id` = 标准任务节点名 / fan-out 任务 `f"{节点名}:{TaskId}"`；任务级现场表键改「任务标识」；`namespace` 仍 `f"{节点名}:{uuid4}"`；`__interrupt__` / `__resume__` 按任务区分 | **拆分而不删**（原单任务断言保留） |
| **T-15** | **F-14** | `specs/b7f1-superstep-loop/contracts/superstep-contract.md` I-1 / I-2 / I-3 / I-4 / I-12 / §4 / §5 · `specs/b9f1-command-primitive/contracts/command-contract.md` I-5 / I-6 · `specs/b12f1-concurrency-errors/contracts/concurrency-contract.md` §3 / §4 / §5 / §6 / I-2 / I-3 / I-8 / I-12 / V-15 · 各 spec 的对应注记 · `specs/b10f1-interrupt-resume/{spec.md, contracts/interrupt-resume-contract.md}` 的 `.executed` 顺序 | **拆分而不删**：增补阶段 ②′；**含 fan-out 的轮**里提交 / 首个异常 / 落回 / 合并 / `executed` / `dynamic_edges` = TaskId 序（标准任务在前）；标准任务之间仍节点名序；I-3 拆为「标准 ≤1 · fan-out N」 | **拆分而不删**（原单任务 / 标准任务断言保留） |

> ⚠️ **2026-11-14 回溯修订收口**：**T-6 / T-10 / T-12 / T-14 / T-15** 的目标文档已在工作区**提前落地**
> （F-6 / F-13 / F-14 全量；F-10 / F-12 的剩余项已随本轮补齐）⇒ ⇒ tasks 中的对应任务
> **T068 / T072 / T074 / T093 / T094 改为“核验 + 补齐剩余 + 记录签字”**（见 `tasks.md`）
> ⇒ **MUST NOT 回退已落地修订**；发现差异才最小补齐。

### 门禁编号纪律

**G1–G30 恒成立 · 编号连续无跳号 · 总数 == 30**（FR-021）⇒ 本 feature **零新增门禁编号**
⇒ 新增代码 MUST 被既有门禁**自动覆盖**（G21 依赖 / G25 导入图 / G26 静态出站 / G27 零出站 /
G29 契约载体 / G30 署名头）⇒ ⇒ **门禁实现零改动**。

### 设计后复核（Phase 1 后 · 模板要求「Re-check after Phase 1 design」）

| 复核项 | 结果 |
|---|---|
| **原则 XI 的判定顺序** | 每个设计点先问「上游怎么说」⇒ 载体 / 落点 / 入参 / 次数 / 并发 / 归并顺序 / 「既派发又写入」**全部照抄** ⇒ 仅 **3 条**刻意分叉且**逐条登记**（X-1 / X-3 / X-6）✅ |
| **必须自研区（4 类）** | ① 零账号 / 零出站 / 零依赖 ⇒ **照常**；② 上游自身的静默忽略 ⇒ **更严**（X-1）；③ 上游没有的能力 ⇒ 「节点直接返回 `list[Send]`」（X-6）与「载体 B 的静态边口径」（X-3）；④ 下游兼容 ⇒ 本 feature **不涉及** ✅ |
| **三态标注一致性**（v1.12.0） | 对照表 **P-07 = STRICTER** ⇒ 偏离登记有 **X-1** ✅；对照表 **P-09 / P-10b = DIFF** ⇒ 偏离登记有 **X-6 / X-3** ✅；**X-5** 对应 **P-02 = DIFF** ✅；**P-13 = SAME**（归并顺序照抄上游）⇒ 偏离登记**无对应行**（正确）✅ ⇒ **逐条对应 · 无孤行** ✅ |
| **协议 / 运行时一致** | `NodeFunc` 的返回联合**已**增补 `Send` / `list[Send]` / `tuple[Send, ...]`（T-11）⇒ **无分歧** ✅ |
| **层纪律（ARCH-1）** | `Send` 在 **L1** ⇒ L2 运行期**向下** import L1 ✅ ⇒ 门面的转出**向下** ✅ ⇒ **零反向 import** ✅ |
| **导出面** | L1 **21**（经特批）· 门面 **7** · `runtime.__all__` **23** ⇒ 新增模块**私有** ⇒ **零新增导出** ✅ |
| **可判定性** | 判据全部**可自动判定**：24 条 FR · 22 条 SC · 14 条不变量（I-1…I-14）· 7 条校验规则（V-15…V-21）⇒ **MUST NOT** 出现「无法自动核对」的口径 ✅ |
| **回溯修订的完备性** | 实测化完成（research §2 · **C-01…C-12**）⇒ 测试变红项 **7** 处；**另加契约语义冲突 2 类**（**F-13** B10F1 任务标识 / 中断现场 · **F-14** B7F1/B9F1/B12F1/B10F1（`.executed`）顺序 / 阶段 / 执行次数）⇒ 文档与契约修订合计 **T-1…T-15** 逐条对应 ⇒ **MUST NOT** 遗漏 ✅ |

---

## Project Structure

### Documentation (this feature)

```text
specs/b11f1-send-fanout/
├── plan.md              # 本文件（/speckit.plan 产出）
├── research.md          # Phase 0（上游实测 + 回归面探测 + 设计决策 + 遗留登记）
├── data-model.md        # Phase 1（实体 / 形状 / 阶段 / 校验规则 / 不变量）
├── quickstart.md        # Phase 1（可运行的验证场景）
├── contracts/
│   ├── send-contract.md      # 运行期语义契约（逐字）
│   └── upstream-parity.md     # 上游逐条对照 + 差分场景 + 实测基线
├── spec.md              # 需求与判据的**唯一权威**
├── checklists/
│   └── requirements.md # 规格质量清单（16/16）
└── tasks.md             # Phase 2（/speckit.tasks 产出 —— 本命令**不**产出）
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/            # L1 契约层（C1–C27 · 5 协议 · 纯数据类（含 Send））
│   ├── types.py          # ← 改：Send 的类型定义迁入（与 Command 同模块）+ goto 注解放宽
│   ├── protocols.py      # ← 改：NodeFunc.__call__ 返回联合增补 Send / list[Send] / tuple[Send, ...]
│   └── __init__.py       # ← 改：导出 Send（__all__ 20 → 21）
├── graph.py              # ← 改：门面从 L1 转出 Send（导出面 7 不变）
├── _primitives.py        # ← 删：Send 迁出 ⇒ 文件整体删除
└── runtime/              # L2 执行内核层（层注册表的**目录条目** ⇒ 新模块零注册表改动）
    ├── _fanout.py        # ← 新增：fan-out 载荷解析 / 校验 / 任务构造 / 触发组抑制 / TaskId（私有）
    ├── superstep.py      # ← 改：归一扩展 · 阶段 ②′ · 抑制 · 落回 · 写入收集 · executed
    ├── _concurrency.py   # ← 改：结果槽的键 → TaskId · _TaskOutcome 增 fanout 字段
    └── _interrupt.py     # ← 改：任务级现场键 → 任务标识（TaskId）· N 次同节点中断独立（F-13）

tests/
├── runtime/
│   ├── test_send_fanout.py      # ← 新增：fan-out 运行期语义（FR-001…FR-011）
│   └── test_send_contract.py    # ← 新增：L1 侧契约（Send 的形状 + 注解 + 导出面）
├── contracts/             # ← 改：G7 基线（T-5）· NodeFunc 联合（T-11）
├── runtime/               # ← 改：符号面基线（T-5）· `_primitives` 断言（T-2）
├── facade/                # ← 改：扫描清单（T-3）
└── differential/
    └── parity_probe.py    # ← 改：追加 D-29…D-37

harness/
├── verification/B11F1/    # ← 新增：acceptance.py（机械层）+ manual-verification.md（五段式 + 追认）
├── features/              # ← 改：下游接线 D-1…D-8（7 份目标 feature 的提示词初稿）
├── proposals/             # ← 改：立项书 §5.1 / §5.2（T-6）· 上游对齐审计（T-7）
└── demo/graph_core.py     # ← 核对（T-13 · 不改）
```

### ── 本 feature **触及**的文件（**表格 30 行** · 不含 `+` 辅助行） ──

| # | 文件 | 动作 | 落点 |
|---|---|---|---|
| 1 | `src/freegraph/contracts/types.py` | 改 | `Send` 定义迁入（**在 `Command` 之前**）· `goto` 注解 · 模块 docstring（「四个核心类型」→ 五个）· `Command` docstring 的 `goto` 字段表 |
| 2 | `src/freegraph/contracts/__init__.py` | 改 | 导出 `Send`（20 → 21）· 更新模块 docstring（「本层不导出 Send」⇒ 导出） |
| 3 | `src/freegraph/contracts/protocols.py` | 改 | `NodeFunc.__call__` 联合（含 `tuple[Send, ...]`）+ docstring（T-11） |
| 4 | `src/freegraph/graph.py` | 改 | 门面转出 `Send` · 模块 docstring（`_primitives` 的引用） |
| 5 | `src/freegraph/_primitives.py` | **删** | 文件整体（T-1 / T-2 / T-3） |
| 6 | `src/freegraph/runtime/_fanout.py` | **新增** | fan-out 载荷 / 校验 / 任务构造 / 抑制 / **TaskId** / **`producer`**（**私有**） |
| 7 | `src/freegraph/runtime/superstep.py` | 改 | 归一扩展 · 阶段 ②′ · 抑制 · 落回 · 写入收集（`ordered_writes`）· `executed` · `SchedulerState.fanout` · `by_name` 键改 TaskId |
| 8 | `src/freegraph/runtime/_concurrency.py` | 改 | 结果槽键 → TaskId · `_TaskOutcome` 增 `fanout` |
| 8b | `src/freegraph/runtime/_interrupt.py` | 改 | 任务级现场键 → 任务标识（TaskId）⇒ 同节点 N 次 fan-out 各自独立（DR-01） |
| 9 | `tests/runtime/test_send_fanout.py` | **新增** | 运行期语义用例（FR-001…FR-011） |
| 10 | `tests/runtime/test_send_contract.py` | **新增** | L1 侧契约用例 |
| 11 | `tests/differential/parity_probe.py` | 改 | D-29…D-37（9 条） |
| 11b | `tests/differential/test_parity_probe.py` | 核验 | 新场景由 `parity_probe.py` **自动发现** ⇒ 本文件核验其被打包进 CI（**Linux 全量档真跑** · 上游缺席即 skip）；仅在**需显式登记**时才改 |
| 12 | `tests/contracts/test_architecture.py` | 改 | G7 基线 20 → 21（T-5） |
| 13 | `tests/contracts/test_protocols.py` | 改 | NodeFunc 返回联合（T-11） |
| 14 | `tests/runtime/test_read_contract.py` | 改 | 符号面基线（T-5） |
| 15 | `tests/runtime/test_command_purity.py` | 改 | 符号面基线（T-5） |
| 16 | `tests/runtime/test_superstep_concurrency.py` | 改 | `_primitives` 断言（T-2） |
| 17 | `tests/facade/_gatesupport.py` | 改 | 扫描清单（T-3） |
| 18 | `README.md` | 改 | 兼容矩阵 `Send` / `Command` / `NodeFunc` 三行（T-4） |
| 19 | `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` | 改 | 陈旧条目删除（T-1） |
| 20 | `specs/b1f1-contracts-core/{data-model.md, contracts/public-api.md}` | 改 | `goto` 字段描述（T-9） |
| 21 | `specs/b2f1-contracts-protocols/contracts/public-api.md` | 改 | `Send` 层级 + `goto` 注解（T-8） |
| 22 | `specs/b2f2-public-api-facade/contracts/{facade-api.md, architecture-gates.md}` | 改 | `Send` 层级（T-8） |
| 23 | `specs/b9f1-command-primitive/contracts/command-contract.md` | 改 | `goto` 解析 + 归一形状（T-10）· I-5 / I-6（T-15） |
| 23b | `specs/b7f1-superstep-loop/{spec.md, contracts/superstep-contract.md}` | 改 | I-1 / I-2 / I-3 / I-4 / I-12 / §4 / §5 的 fan-out 分支（T-15） |
| 24 | `specs/b12f1-concurrency-errors/contracts/concurrency-contract.md` | 改 | 结果槽形状（T-12）· §3 / §4 / §5 / §6 / I-3 / I-8 / I-12（T-15） |
| 24b | `specs/b10f1-interrupt-resume/{spec.md, contracts/checkpoint-contract.md, contracts/interrupt-resume-contract.md}` | 改 | `task_id` / 任务现场 / 命名空间（T-14） |
| 25 | `harness/proposals/{立项书.md, 上游对齐审计.md}` | 改 | §5.1 全部落点 + §5.2 依赖列（T-6）· P-05 / 第 13 行（T-7） |
| 26 | `harness/features/{B8F1, B13F1, B14F1, B19F1, B24F1, B6F1, B15F1}*.md` | 改 | 下游接线 **D-1…D-8**（**只接线 · 逐条最小改动**） |
| + | `harness/verification/B11F1/{acceptance.py, manual-verification.md}` | **新增** | 机械层一键验收 + 五段式 + **追认** |
| + | `harness/demo/graph_core.py` | **核对** | C18 用例（**不改** · T-13） |

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified** —— 本 feature 有
> **经发起者特批的破 L1 冻结面** ⇒ 逐条登记（登记项 **PR-1…PR-14**）⇒ 与 constitution v1.8.0 的
> 「破冻结面的三条」对齐：**回溯修订**（T-1…T-15）· **上游对照**（P-04 / P-11 / P-12 / P-13 / P-14 = SAME）·
> **发起者追认**（一次 · ≤ 1 次）。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **PR-1 / PR-2 / PR-3 · L1 冻结面**（`Send` 归 L1 · 符号面 20 → 21 · `goto` / `NodeFunc` 注解放宽） | **照抄上游**（上游的 `Send` 与 `Command` **同模块且公开**）⇒ 且只有这样才能让「一次返回里既派发又写入」（上游 E-8）与「`Command.goto` 装 `Send`」**同款可用** ⇒ ⇒ **发起者已拍板**（澄清轮第 2 次 **B**） | **留在 L2** ⇒ ① L1 的 `goto` 注解**无法引用** `Send` ⇒ 协议 / 运行时**分歧**；② 运行期与类型**跨条目** ⇒ G25 判红；③ 「既派发又写入」**做不出来** ⇒ ⇒ 与上游**能力不对等** ⇒ **代价**：破 L1 冻结面（**T-1…T-15** 回溯修订 + **一次**追认） |
| **PR-4 · 并发器结果槽的键**（节点名 → TaskId） | 同一节点在一轮内**可有多个任务** ⇒ 旧的 `dict[str, _TaskOutcome]` 会**互相覆盖** ⇒ 静默丢结果 | **按节点名 + 列表** ⇒ 结果槽的键不再是**可哈希的唯一标识** ⇒ 「首个异常 = 扫第一个」的确定性口径**被破坏**（B12F1 裁定 5）⇒ ⇒ **必须**换成**唯一且有序**的键 ⇒ **TaskId = 本轮规范序号（`int`）** 恰好**同时**满足「唯一」与「有序（= 归并次序键）」 |
| **PR-5 · `SchedulerState` 新增一个字段** | fan-out 载荷必须**跨轮存活**（下一轮才执行）⇒ 运行期记账；同一节点在一轮内可执行多次 ⇒ 载荷必须**按产生者任务**区分 | 放进 `dynamic_edges` ⇒ 那里只放**字符串**目标名 ⇒ 载荷含**用户对象** ⇒ **放不下**；按节点名做键 ⇒ **同一节点的多次执行互相覆盖** ⇒ ⇒ **单独一个字段 `fanout: dict[TaskId, _FanOut]`**（B9F1 裁定 12 的**同款**先例 ⇒ `SchedulerState()` 签名**不变**）· `_FanOut.producer` 保留**产生者节点名**（否则载体 B 的静态边抑制无法按 `(producer, target)` 匹配） |
| **PR-6 · 归一形状增一个键** | fan-out 任务与写入**同轮**产出 ⇒ 归一为**一种内部形状**是 B9F1 的既有结构 | 另写一条 fan-out 归一路径 ⇒ 与 B9F1 裁定 4 的教训（「两条路径迟早分叉」）**同款** ⇒ ⇒ **增一个键** |
| **PR-7 · 两条载体的静态边口径不同** | 载体 A **照抄上游**（叠加）· 载体 B **照验收脚本**（`Send` 胜出）⇒ 两者**各服从自己的权威** | 统一成「叠加」⇒ **验收脚本 C18 必红**（其 `worker` 以 `state['n']` 取值 ⇒ 标准入参那次 `KeyError`）；统一成「`Send` 胜出」⇒ **载体 A 与上游分叉**（原则 XI 要求**行为面照抄**）⇒ ⇒ **只能分列** ⇒ ⚠️ 代价 = **同一张图换写法调用次数可能不同** ⇒ **MUST 显著写进文档 / 人工验证记录**（DR-03） |
| **PR-8 · fan-out 载荷不落盘** | 载荷含 `arg: Any`（**用户对象**）⇒ 未必可 JSON 序列化 ⇒ 落盘会引入**新的失败面** | 落盘 ⇒ 需定义序列化协议 ⇒ 属 **B14F1** 的**契约设计** ⇒ ⇒ **越界** ⇒ ⇒ 本 feature **不落盘** + 登记（DR-02）+ 承接 **D-3**。⚠️ **2026-11-15 · B13F1 F-3 回溯修订**：`to_checkpoint` 的**键编码**由 B13F1 接管（增 `fanout`）；**实际存储 / 序列化协议**仍归 **B14F1**（拆分而不删） |
| **PR-13 · B10F1 任务标识 / 中断现场**（F-13） | 同一节点一轮内 N 个 fan-out 任务 MUST 有**各自独立**的中断现场与 pending writes ⇒ 旧的「`task_id` = 节点名 · 一轮一个节点一个任务」会**串扰** | 保留节点名做 `task_id` ⇒ N 次中断共享同一现场 ⇒ 恢复值按 id 匹配**歧义** ⇒ ⇒ **拆分**为「标准任务 = 节点名 · fan-out 任务 = `f"{节点名}:{TaskId}"`」 |
| **PR-14 · B7F1 / B9F1 / B12F1 / B10F1（`.executed`）顺序 / 阶段模型 / 执行次数**（F-14） | fan-out 任务与标准任务同轮共存 ⇒ 必须定义**确定**的提交 / 首个异常 / 落回 / 合并 / `executed` / `dynamic_edges` 次序；且阶段模型新增 ②′ | 继续用「节点名序」⇒ 同节点多任务**无唯一序**，且与上游任务序（标准在前、fan-out 在后）分叉 ⇒ ⇒ **TaskId 序**是唯一同时满足「唯一 / 有序 / 可复现」的键 |
