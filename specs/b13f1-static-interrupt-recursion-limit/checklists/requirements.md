# Specification Quality Checklist: B13F1 · 静态中断点（`interrupt_before` / `interrupt_after`）+ `recursion_limit`

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-15
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

**Validation round 1 — 2026-11-15（初版 spec 写定后的自检）· 结果：16 / 16 项全部通过**
（无失败项 ⇒ 无需修复迭代 ⇒ 无 checkbox 状态变化）。

**Validation round 2 — 2026-11-15（用户澄清 Q10–Q14 后复验）· 结果：16 / 16 项保持通过**
（本次澄清调整了 A3 延期、`recursion_limit` 载体、低层入口行为、静态断点写法；
**无 checkbox 状态变化**；当轮 FR 仍 31、SC 仍 24）。

**Validation round 3 — 2026-11-15（分析后修复）· 结果：16 / 16 项保持通过**
（本轮修复分析发现的规格对齐问题：新增 **FR-032**（README 软断言清单同步）与
**F-10**（静态恢复完成快照）；收窄 F-5；差分 D-41 / D-42 / D-45 / D-46 改用 list 形态；
**SC 仍 24**；无 checkbox 状态变化）。

**Validation round 4 — 2026-11-15（第二次分析后修复）· 结果：16 / 16 项保持通过**
（本轮修复：**F-3 补齐 B11F1 的「`fanout` 不落盘」冻结面拆分**（`send-contract.md` §5.1 ·
`data-model.md` I-12 · `tasks.md` T019 · `plan.md` PR-8 · `research.md` DR-02）；
**两条静态恢复入口（`input=None` / `Command(resume=...)`）明确传 `static_ack`**；
**after 的 ack 接线进入实现任务**；补空 `StateDict` 的防重复口径与 F-10 普通完成反向用例；
修正 V-16 编号说明 / FR-009 措辞 / T106 路径 / T105 `[P]`；**FR 仍 32、SC 仍 24**；
无 checkbox 状态变化）。

**Validation round 5 — 2026-11-15（第三次分析后修复）· 结果：16 / 16 项保持通过**
（本轮修复：**`recursion_limit=None` 明确为「未提供」并跳过类型校验**；**FR-005 区分
`SchedulerState.step` 与局部 `steps`**；**SC-006 的 `invoke` 部分明确由 B7F3 D-3 收口**；
**X-1 / X-2 / X-6 / X-8 追认落入 T103 / T114 + SC-021**；**F-3 的 B11F1 同步清单统一**
（补 `quickstart.md` DR-02 / `spec.md` D-3 / `research.md` D-08，F-14 仅顺序口径说明）；
**P-13 上游锚点修正**（`_loop.py:861-864` / `:1030`）；**D-8 映射补 T106**；
**契约 V-22 的 `None` 措辞修正**；data-model 不变量标题改为 **I-S1…I-S15**。
**FR 仍 32、SC 仍 24**；无 checkbox 状态变化）。

> ⚠️ **本 checklist 的判定口径**（与本仓库既有 feature 一致）：仓库的 spec 天然携带
> **契约名 / 路径 / 行号 / 门禁编号**（宪法原则 VIII「证据与术语纪律」的载体）⇒
> 「No implementation details」一条的口径是「**MUST NOT 规定**实现方式（怎么写）**」，
> **不是**「MUST NOT 引用被交付的**产物名**（写什么）」⇒ 例如「`GraphSpec` 的两个
> keyword-only 字段」属**产物名 + 落位约束**（B7F1 冻结面 / 验收判据的可判定对象）⇒
> **不判失败**。

### 逐项核对

| # | 项 | 核对结论（依据） |
|---|---|---|
| 1 | No implementation details | ✅ 全部 FR 以「MUST 做什么 / MUST NOT 做什么」表述；实现手段（检查点账本键、`__post_init__`、`_run_round` 阶段）只出现在**落位约束**与**回溯修订**中，且是可判定的结构面 |
| 2 | Focused on user value | ✅ 8 个用户故事全部以「用户想要什么 + 怎么判定」表述（before / after / 死循环 / 载体 / 默认值 / fan-out / 优先级 / 无回归） |
| 3 | Written for non-technical stakeholders | ✅ 用户故事与 Edge Cases 用业务语言；技术术语集中在 FR / 裁定 / Upstream Parity（与仓库既有 feature 同款） |
| 4 | All mandatory sections completed | ✅ 用户场景 · Edge Cases · **上游对照 + 差分场景组 + 偏离登记 + 回溯修订清单** · 需求（含裁定 / 追溯表）· 关键实体 · Out of Scope · 成功标准 · 假设 · 依据 —— **无占位符残留** |
| 5 | No [NEEDS CLARIFICATION] markers | ✅ 全文 **0** 处标记；提示词点名「spec 阶段必须写死」的项已分别落成 **裁定 1–14**（Clarifications · Q1–Q14 + 编号映射表） |
| 6 | Requirements testable | ✅ **32** 条 FR 全部带**可判定的失败信号**（异常类型 + 消息要点）或**可数的结果**（次数 / 顺序 / 内容 / 比率） |
| 7 | Success criteria measurable | ✅ **24** 条 SC 全部含量化口径（比率 == 100% · 现象次数 == 0 · 覆盖率 == 100% · 重复 ≥ 3 次逐项相等） |
| 8 | Success criteria technology-agnostic | ✅ SC 只断言**可观察行为**（执行次数 / 状态内容 / 异常类型 / 环境变量读取次数 / 覆盖率 / 文档形态）⇒ **不含**框架或工具选型 |
| 9 | All acceptance scenarios defined | ✅ **8** 个用户故事共 **23** 条验收场景（Given / When / Then）；覆盖提示词 P1–P3 + A1–A3 |
| 10 | Edge cases identified | ✅ **27** 条 Edge Cases：空配置 / before+after 同节点 / 入口 / 末尾 / 未触发 / 非法名字 / `START`/`END`/`["*"]` / 裸 `"*"` All（可执行节点） / 重复 / fan-out / 动态中断 / 真异常 / 递归顺序 / 非法上限 / dict 未知键 / 优先级 / checkpointer / 防重复 / 空 StateDict `input={}` / 不可序列化 arg / 低层入口 |
| 11 | Scope clearly bounded | ✅ Out of Scope **12** 条（持久化 / compile-invoke / 构建器 / async / 子图 / 重试超时 / `Send` 变更 / 调用时覆盖 / `"*"` / trace / 兼容矩阵 / 新契约门禁） |
| 12 | Dependencies and assumptions identified | ✅ **Assumptions** 列明 6 个前置 feature、Python 基线、零依赖、上游 1.2.11 取证、spec 命名、端到端延期（**EV-1**） |
| 13 | All FRs have clear acceptance criteria | ✅ 「需求 ↔ 成功标准 追溯表」32 行；每条 FR 至少挂 1 条 SC |
| 14 | User scenarios cover primary flows | ✅ P1 before / P2 after / P3 递归超限 / 载体 / 默认值 / fan-out / 优先级 / 向后兼容 —— 无空缺 |
| 15 | Feature meets measurable outcomes | ✅ A1（SC-003）· A2（SC-001 / SC-002）· A3（SC-005 + **EV-1** 的具名承接 + 退出码 2）逐条可判定 |
| 16 | No implementation details leak | ✅ 实现细节只作为**可判定结构面**（`GraphSpec` 字段 / `InterruptResult` 四字段 / 调度账本键）出现，且均有上游对照或冻结面依据 |

### 覆盖统计

| 项 | 数量 |
|---|---|
| FR | **32** |
| SC | **24** |
| 上游对照 P | **20** |
| 差分场景 D-38…D-49 | **12** |
| 偏离登记 X | **8** |
| 回溯修订 F | **10** |
| 用户故事 | **8** |
| 验收场景 | **23** |
| Edge Cases | **27**（round 4 增「空 `StateDict` `input={}`」） |

### 已知延期（不阻塞 spec 定稿）

| # | 延期项 | 承接方 | 里程碑 |
|---|---|---|---|
| **EV-1** | `graph_core.py` 的 `case_recursion_limit` **端到端真跑**（需 `compile()` / `invoke()`）；M1 门面未就绪时脚本以退出码 2 结束 | **B7F3**（下游承接 **D-3**） | M2 |

> ⚠️ 该延期**不是**判据放宽：`soft(...)` → `check(...)` 的升级与异常类型收紧在 B13F1
> 立即落地；L2 等价硬测试**当下真跑通过**；端到端真跑由 B7F3 按原判据执行。
