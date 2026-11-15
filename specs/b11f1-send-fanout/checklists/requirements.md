# Specification Quality Checklist: B11F1 · `Send`：动态 fan-out / map-reduce

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-14（初版）· **2026-11-14 更新**（`/speckit.clarify` 两轮澄清后的复验）· **2026-11-14 再更新**（三件套一致性分析 + 修复轮后的复验）
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

**Validation round 7 — 2026-11-14（用户授权的第 5 轮收口修复）· 结果：16 / 16 项保持通过**
本轮修复：US5/US6 载体 A 测试顺序 · T001/T005 文件创建顺序 · 同文件测试任务去掉 `[P]` ·
T067/T071 并行冲突 · 已提前落地的回溯修订改为“核验 + 补齐剩余” · `suppresses_static` 判定源统一 ·
覆盖率命令改为 diff 覆盖率口径 · FR-022 追溯补全 · 线程泄漏覆盖并入 T025。
任务总数仍 **95**；FR **24/24** · SC **22/22** · 反向覆盖 **95/95** 不变。

**Validation round 6 — 2026-11-14（第四轮三件套一致性分析 + 修复轮）· 结果：16 / 16 项全部通过**
（**无失败项 · 无 checkbox 状态变化**）—— 本轮修复 **3 HIGH / 3 MEDIUM / 8 LOW**：
① **INC-1**：立项书 §5.3 **C18 行**「对上承诺 v2 提供」⇒ **v1 提供（B11F1）**，并纳入 **F-6 / T-6 / T068**；
② **INC-2**：B11F1 依赖列补 **B10F1**（spec Assumptions / F-6 / plan T-6 · PR-9 / tasks T068 / 本 checklist 第 12 项）；
③ **INC-3**：plan 与 upstream-parity 的「边触发源空间」措辞改为「**与 `goto` 同族的落点 · 派发任务（不登记为边触发源）**」；
④ **COV-1**：SC-022 的 fan-out 判据（`executed` 逐次 / `node_versions +N` / 值序列 TaskId 序）并入 **T033**（测试任务）；
⑤ **TRC-1**：三张追溯附录表与任务正文**逐条对齐**（SC-020 的区间为**按回溯组聚合**，已显式说明）；
⑥ **AMB-1**：同一产生者一轮内多次执行且载体混合的抑制口径写死为「**任一载体 B 执行即抑制**」，并入 FR-006 / SC-005 / T052 / T053；
⑦ LOW：plan 规模口径与数据类计数、upstream-parity 表头、澄清轮 Q4 编号、plan `test_parity_probe.py` 动作、条件边范围的 SC 覆盖声明；
⑧ **SPC-1**：SC-007 增补「不触发有值门槛」、SC-008 增补「覆盖型通道同轮多写 ⇒ 显式失败」子句；
⑨ **DUP-1**：归并顺序以 **spec FR-005 为唯一权威**，其余文档保留交叉引用式复述（可审计，不视为缺陷）。

**Validation round 5 — 2026-11-14（第三轮三件套一致性分析 + 修复轮）· 结果：16 / 16 项全部通过**
（**无失败项 · 无 checkbox 状态变化**）—— 本轮修复 **2 CRITICAL / 3 HIGH / 5 MEDIUM / 4 LOW**：
① **C1**：新增 **F-13 / T-14**（B10F1 `task_id` / 任务现场 → 标准节点名 / fan-out `节点名:TaskId`）+ **D-8**（B15F1）+ D-3（B14F1）；
② **C2**：新增 **F-14 / T-15**（B7F1 I-3 / I-12、B9F1 I-5 / I-6、B12F1 §3 / §4 / §5 / §6 / I-3 / I-8 / I-12 的 TaskId 序）；
③ **H1**：SC-014 / FR-012 的 identity 改为**可判定**的 `graph.Send is contracts.Send`；④ **H2**：FR-014 改为**三处经特批**的 L1 变更；
⑤ **H3**：`NodeFunc` / C5 增补「`Send` 入参可为非 dict」例外；⑥ **M1**：FR-002 明确 fan-out 不是边触发源、不消费版本；
⑦ **M2 / M3 / M4**：补齐屏障 / 其它 producer 静态边 / 未知 key / 覆盖型多写 / 首异常顺序 / 两载体对比测试；
⑧ **M5**：立项书 §5.1 **4 处** + §5.2 依赖列；⑨ **L1 / L2 / L4 / L5**：PR-2 映射、tuple、research C-07、plan/quickstart 文案；**L3（T013/T014 顺序）经复核不成立**（T014 已在 T013 之前，依赖声明正确）⇒ 不改。
⇒ 新增任务 **T093 / T094 / T095** ⇒ 任务总数 **95**；**F-1…F-14** / **T-1…T-15** / **D-1…D-8**。

**Validation round 4 — 2026-11-14（第二轮三件套一致性分析 + 修复轮）· 结果：16 / 16 项全部通过**
（**无失败项 · 无 checkbox 状态变化**）—— 本轮共修复 **5 HIGH / 7 MEDIUM / 11 LOW**：
差分场景编号按全局序列续编 **D-29…D-37**（避开 B7F4 的 D-16…D-28）· `NodeFunc` 协议补 `tuple[Send, ...]` ·
内部形状补 `_FanOut.producer` / `_FanOut.suppresses_static`（聚合判定源）/ `_FanOutTask.suppresses_static`（归一形状信息源） · **多源屏障组不抑制**写入 spec FR-006/SC-005 ·
`interrupt` 任务级现场键改 TaskId（同节点 N 次调用独立）· 修正 G2 说明 / T091/T068 追溯 / PR-6 落点 /
上游行号（`_algo.py:253-256`）· README `NodeFunc` 行纳入允许的措辞更新等。

**Validation round 3 — 2026-11-14（**三件套一致性分析 + 修复轮**后的复验）· 结果：16 / 16 项全部通过**
（**无失败项 · 无 checkbox 状态变化**）—— 分析轮共查出 **11** 处问题（**2 HIGH / 6 MEDIUM / 3 LOW**）
⇒ 已**逐条修复**（发起者授权「直接修改所有 `specs/` 中的文件」）⇒ 复验见下表。

| 分析项 | 修复落点 | 状态 |
|---|---|---|
| **A1**（HIGH）tasks 的 SC **摘要表 ↔ 附录**漂移 5 处 | `tasks.md`：摘要表与三张附录表**改为同源脚本生成**（区间写法按整段展开）⇒ **漂移归零** | ✅ |
| **A2**（HIGH）spec 的归并顺序**对标准触发任务留白** | `spec.md` FR-005 **回写**（澄清轮第 3 次 **Q4** + **2026-11-14 复核更正**：**标准触发任务全部排在 fan-out 之前**；归并顺序 = **上游任务序**，`pregel/_algo.py:253-256`）· 裁定 6 / SC-008 / 引文差异 ⑨ / 依据同步 | ✅ |
| **A3**（MEDIUM）三个 Edge Case **无任务承载** | `tasks.md`：T021（**自投**）· T022（**非 dict / `None` 入参**）· T023（**残留 fan-out 的清空**）**并入既有测试任务** | ✅ |
| **A4**（MEDIUM）立项书 §5.2 的 **B11F1 依赖列**只写 `B7F1` | `tasks.md` **T068** 扩为「§5.1 分层裁定 **+** §5.2 依赖列（补 `B9F1,B12F1`）」⇒ 与 spec 的 H-1 / H-4 对齐 | ✅ |
| **A5**（MEDIUM）任务未引用**裁定 / 承接条款 / 登记项** | `tasks.md`：关键任务描述补「（裁定 N · H-N · PR-N）」+ 新增附录「**裁定 / 承接条款 / 登记项 → 任务**」（30 行） | ✅ |
| **A6**（MEDIUM）plan 的「触及的文件」表**漏** `tests/differential/test_parity_probe.py` | `plan.md`：表内补 **11b** 行（表格 26 → **27** 行） | ✅ |
| **A7**（MEDIUM）**三套命名空间**共用 `FR-xxx` / `P-xx` | `spec.md` 依据：外部编号**加限定词**（「**B7F1 的** FR-032」·「**上游对齐审计 §3 的** P-16」）+ 新增**命名空间约定**段 | ✅ |
| **A8**（LOW）plan 的 `T-13` 是**核对项**却混在回溯清单里 | `plan.md`：T-13 标注「**不是回溯修订** ⇒ **不计入** SC-020 的回溯条数」 | ✅ |
| **A9**（LOW）tasks 闸口 G-2 的「提前」含糊 | `tasks.md`：G-2 改为「Phase 2 **只出骨架** ⇒ MUST NOT 落地任何 fan-out 的**可观察行为**」 | ✅ |
| **A10**（LOW）tasks 未指向 **research §3**（设计决策） | `tasks.md`「路径约定」新增一行指引（`research.md` **§3** · D-01…D-11） | ✅ |
| **A11**（LOW）plan 的 **PR-4…PR-8** 在 tasks 里无落点 | `plan.md` 新增「**登记项 → 任务落点**」表（12 项逐条）+ `tasks.md` 新增同名附录（逐条一致） | ✅ |

**Validation round 2 — 2026-11-14（`/speckit.clarify` 两轮澄清后的复验）· 结果：16 / 16 项全部通过**
（**无失败项 · 无 checkbox 状态变化** ⇒ 复验前后均为 **16 / 16**）。

> **本轮（澄清轮）的变化摘要**（3 个提问全部落盘 · 发起者拍板）：
> **Q1 = B**（能「既派发又写入」· **照抄上游** ⇒ `Send` 归 **L1** · `Command.goto` **可装 `Send`** ⇒
> **双载体** ⇒ **X-2 / X-4 两条偏离消解** ⇒ 回溯修订清单扩为 **F-1…F-8**）·
> **Q2 = A**（归并顺序 = **上游任务序**：标准触发任务按目标节点名序 → fan-out 任务按产生者任务序 · 载荷内 `Send` 序号；**2026-11-14 复核更正**）·
> **Q3 = A**（失败消息**同时点名产生者与目标**）。
> ⇒ 连带新增：**用户故事 6**（一次返回里既派发又写入）· 上游对照 **P-10b / P-12** ·
> 差分场景 **D-36 / D-37** · 下游承接 **D-7**（静态中断点 × fan-out）· Key Entities「归并顺序」。

**Validation round 1 — 2026-11-14（初版 spec 写定后的自检）· 结果：16 / 16 项全部通过**
（**无失败项** ⇒ 无需修复迭代 ⇒ 无 checkbox 状态变化）。

> ⚠️ **本 checklist 的判定口径**（与本仓库既有 feature 一致）：仓库的 spec 天然携带
> **契约名 / 路径 / 行号 / 门禁编号**（宪法原则 VIII「证据与术语纪律」的载体）⇒
> 「No implementation details」一条的口径是「**MUST NOT 规定**实现方式（怎么写）**」，
> **不是**「MUST NOT 引用被交付的**产物名**（写什么）」⇒ 例如「`Send` 的类型定义住在
> `freegraph/contracts/types.py`」属**产物名 + 落位约束**（G25 / 立项书 §5.1 的可判定对象）⇒ **不判失败**。

### 逐项核对

| # | 项 | 核对结论（依据） |
|---|---|---|
| 1 | No implementation details | ✅ 全部 FR 以「MUST 做什么 / MUST NOT 做什么」表述；实现手段（模块划分、线程池、字典结构）**只**在**裁定 11** 的落位约束与 **FR-012** 出现，且该处是 **G25 / 立项书 §5.1 的可判定对象**（层归属）⇒ 属**落位约束**而非**实现方式规定** |
| 2 | Focused on user value | ✅ 5 个用户故事全部以「用户想要什么 + 怎么判定」表述（P1 多次不同入参 / P2 归约汇合 / P3 目标写错要报错 / P4 无 `Send` 时行为不变 / P5 混合调度可判定） |
| 3 | Written for non-technical stakeholders | ✅ 用户故事与 Edge Cases 用业务语言；技术术语集中在 FR / 裁定（与仓库既有 feature 同款） |
| 4 | All mandatory sections completed | ✅ 用户场景 · Edge Cases · **上游对照 + 差分场景组 + 偏离登记 + 回溯修订清单** · 需求（含裁定 / 引文差异 / 追溯表）· 关键实体 · 成功标准 · 假设 · 依据 —— **无占位符残留** |
| 5 | No [NEEDS CLARIFICATION] markers | ✅ 全文 **0** 处标记；提示词点名「spec 阶段必须写死」的四处（入参形态 / 目标不存在 / 混合调度 / 载体）已分别落成**裁定 3 / 7 / 5 / 1**；澄清轮两轮的 **3** 个提问与答案落在 **Clarifications · Session 2026-11-14（两条会话）** ⇒ **不残留任何未闭合标记** |
| 6 | Requirements testable | ✅ 24 条 FR 全部带**可判定的失败信号**（异常类型 + 消息要点）或**可数的结果**（次数 / 顺序 / 内容） |
| 7 | Success criteria measurable | ✅ 22 条 SC 全部含量化口径（比率 == 100% · 现象次数 == 0 · 覆盖率 == 100% · 重复 ≥ 3 次逐项相等） |
| 8 | Success criteria technology-agnostic | ✅ SC 只断言**可观察行为**（调用次数 / 入参内容 / 状态值 / 异常类型 / 覆盖率 / 文档形态）⇒ **不含**框架、语言、工具名 |
| 9 | All acceptance scenarios defined | ✅ **6** 个用户故事共 **13** 条验收场景（Given / When / Then · 澄清轮新增**用户故事 6** = 载体 A「既派发又写入」2 条）+ **22** 条 Edge Cases |
| 10 | Edge cases identified | ✅ 空列表 / 混合列表 / `goto` 槽位**混装**（节点名 + `Send`）/ `goto` 槽位**非法元素** / `node` 非 `str` / 空串 / `__parent__` / `START` / `END` / `arg` 为 `None` / **失败消息形态** / 目标被别的源静态触发 / 自投 / 重复 arg / 轮内出错 / 轮内中断 / 残留 fan-out 等 **逐条**列出 |
| 11 | Scope clearly bounded | ✅ 「Out of Scope」**10** 条（条件边路由 / `Send` 类型变更 / 子图 / async / recursion_limit / checkpoint / defer-task / 可观测面 / 对外 API / 构建器 / 兼容矩阵新增行 / **载体 B 的「既派发又写入」**）⇒ 与 FR-020 逐条对齐（澄清轮后 `Command.goto` 装 `Send` **已移出** Out of Scope ⇒ 归入交付面） |
| 12 | Dependencies and assumptions identified | ✅ 前置依赖（B7F1 / B1F1 / B9F1 / B12F1 / **B10F1**）· 承接条款 H-1…H-4 · 下游承接 **D-1…D-8**（**各自带接线状态**）· Assumptions **19** 条（含上游取证环境与实测编号 **E-01…E-11**） |
| 13 | FR ↔ SC 双覆盖 | ✅ 追溯表 **24** 行（FR-001…FR-024）· 末段列明**反向覆盖**（无空缺）· 每条 FR ≥ 1 条 SC · 每条 SC ≥ 1 条 FR ⇒ **机器核对**（脚本抽取 FR / SC 编号 + 追溯表行）**通过** |
| 14 | User scenarios cover primary flows | ✅ P1 = 小目标本体（map-reduce 可运行）· P2 = 汇合 · P3 = 失败可判定 · P4 = 回归不破 · P5 = 混合调度 · **P6 = 一次返回里既派发又写入**（澄清轮新增）⇒ 覆盖 **A1 / A2 / A3** 三条验收判据 |
| 15 | Feature meets measurable outcomes | ✅ 判据 **A1** ⇒ SC-001 · **A2** ⇒ SC-002 · **A3** ⇒ SC-003（**逐条对应**）⇒ 另加 19 条回归 / 结构 / 纪律类 SC |
| 16 | No implementation details leak | ✅ 见第 1 项的说明；另经复查：**未规定**具体数据结构（除裁定 11 的落位约束）· **未规定**线程池用法（沿用 B12F1 的既有实现）· **未规定**测试文件名（只给**落点目录**）· **未规定**归并排序的实现（只给**次序键**） |

### 复查时**发现并修复**的四处（已落盘 · **判据零变动**）

1. **追溯表的覆盖缺口（CRITICAL · 双覆盖判据）**：初稿的追溯表缺 **SC-001 / SC-004 / SC-022**
   三条 ⇒ 「每条 SC 至少挂 1 条 FR」**不成立** ⇒ **修复**：SC-001 补挂 **FR-003 / FR-004**
   （次数与各次入参）· SC-004 补挂 **FR-001**（fan-out 是**新增**返回形态 ⇒ 既有形态一字不变）·
   SC-022 补挂 **FR-010**（执行记录与版本口径）⇒ 末段的**反向覆盖**说明同步改写 ⇒
   修复后 **FR 24 × SC 22 双覆盖、无空缺**（机器核对通过）。
2. **FR-007 的 Markdown 笔误**：``**`ValueError``**`` / ``**`TypeError``**`` ⇒ 已改为
   ``**`ValueError`**`` / ``**`TypeError`**``（**纯排印**）。
3. **回溯修订清单的编号缺失**：清单的**四行**原先**无编号** ⇒ 而 FR-012 / 裁定 11 / FR-022
   均以 **F-1…F-4** 指代 ⇒ **修复**：四行逐条编号 **F-1…F-4**。
4. **下游承接的接线落点**：初稿统一写「§2.1」⇒ 核实目标文件后改为**逐条写实**
   （B8F1 / B24F1 / B6F1 有 **§2.1**；B13F1 **无 §2.1** ⇒ 落 `## 下游承接` 块；
   B14F1 / B19F1 已有 `## 下游承接` 块 ⇒ 落该块）⇒ **只接线 · 逐条最小改动**的口径不变。
   ⚠️ 另修正 **F-1** 一行：初稿写「冻结断言『条目总数 == 12』」⇒ 经核**仓库无此断言**
   ⇒ 改为「其余 **11** 条**一字不动** + G25 的**判定规则**一字不动 + **MUST NOT** 为迁入后的
   模块新增注册表条目」。

### 遗留（**不阻断** `/speckit.plan` · 但 MUST 在 plan / tasks 阶段闭合）

- **L-1（接线动作本身尚未执行）**：下游承接 **D-1…D-7** 的**接线动作**（往 **6** 份目标 feature 的
  提示词初稿追加条款；**D-2 / D-7 同属 B13F1**）属 **plan / tasks 阶段**的动作（宪法 v1.8.0「接线动作 MUST」在本 spec 落成
  FR + 裁定）⇒ 本 spec 只**记录义务与落点**（FR-024 + 追溯表）⇒ **待 plan / tasks 闭合**。
- **L-2（破冻结面的实测化清单）**：FR-022 要求「**先跑绿基线**、变红才可归因」⇒
  **冻结断言清单 MUST 由实测得出**（宪法 v1.11.0）⇒ 本 spec 的回溯修订清单 **F-1…F-10**
  是**依据源码与门禁实现**列出的**候选**⇒ **实施开始前** MUST 按 FR-022 的基线义务**实测化**
  （⇒ 若实测发现清单外的变红断言 ⇒ **追加**到清单 · 判据**只收紧、不放宽**）。
  ⚠️ 澄清轮后破面**扩大**（新增 **F-5** G7 的 L1 符号面基线 · **F-6** 立项书 §5.1 的分层裁定 ·
  **F-7** 上游对齐审计 · **F-8** 两份契约文档）⇒ **实测化的范围随之扩大**（澄清轮后已再补 **F-9 / F-10** ⇒ 共 **10** 条）。
- **L-3（追认）**：偏离登记 **X-1 / X-3 / X-6**（**X-2 / X-4 已消解** · 编号留空）与破冻结面
  **F-1…F-10** 的**发起者追认** MUST 落在 `harness/verification/B11F1/manual-verification.md`
  ⇒ **未追认前 MUST NOT 合入**（宪法 v1.8.0 · FR-016 / FR-022 · SC-020）⇒ 属**合入前**义务 ·
  **不阻断** spec / plan。
- **L-6（plan 阶段的实测化新增两条 · 2026-11-14）**：`/speckit.plan` 的**回归面探测**（research §2 · **C-01…C-12**）
  实测出两条**清单外**的变红项 ⇒ 按 **FR-022 的实测化义务**追加到 spec 的回溯修订清单：
  **F-11**（`NodeFunc.__call__` 的返回联合 · 协议 / 运行时必须一致）与
  **F-12**（B12F1 契约的**结果槽形状** · 结果槽的键由节点名改为任务标识）
  ⇒ 清单由 **F-1…F-10** 扩为 **F-1…F-12** ⇒ plan 的回溯修订清单对应 **T-1…T-13**。
- **L-5（破冻结面清单的漏项已补 · 2026-11-14 复检）**：复检仓库现状时发现三处**漏登记**的冻结面
  ⇒ 已补入回溯修订清单：**F-4** 扩展为 README 兼容矩阵的 **`Send` 行 + `Command` 行**
  （`Command` 行那句「`goto` 目标**只能是节点名**（上游可混入 `Send` —— 归 v2 / B11F1）」已过时）
  ⇒ **F-9**（B1F1 冻结文档 `data-model.md` 与 `public-api.md` 的 `goto` 字段行 · 同句已过时）
  ⇒ **F-10**（B9F1 契约 `command-contract.md` 的 `goto` 形态解析节 · 须增补 `Send` 元素分支）
  ⇒ ⇒ 清单由 **F-1…F-8** 扩为 **F-1…F-10** ⇒ ⚠️ **这三条由仓库现状推导 · 无需发起者决策**
  ⇒ 但仍属**破冻结面** ⇒ 同样要**回溯修订 + 追认**（FR-022 / SC-020）。
- **L-4（澄清轮的三处「按宪法自动裁定」· 非提问项 · 请复核）**：① **`Send` 是否进
  `freegraph.contracts.__all__`** ⇒ 上游的 `Send` **公开且与 `Command` 同模块** ⇒ 按「上游有答案 ⇒
  照抄」取**进**（⇒ L1 符号面 **20 → 21** · **F-5**）；② **载体 A 与载体 B 在「与静态边并存」时的
  口径不同** ⇒ 原则 XI（成功路径的**可观察状态 MUST 照抄上游** ⇒ 载体 A **叠加**）与原则 III
  （验收契约优先 ⇒ 载体 B **`Send` 胜出**）**共同裁定** ⇒ 已写入 **裁定 5** 的**按载体分列表**并要求
  「MUST 显著写进文档 / 人工验证记录」；③ **`Send` 目标不存在时的**报错时点** ⇒ 照抄仓库既有范式
  （B9F1 裁定 8：产生该 `Send` 的**那一轮**立即失败）⇒ 已写入 **FR-007**。
