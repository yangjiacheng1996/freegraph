# Specification Quality Checklist: B2F1 · 5 个协议 + 5 个纯数据类

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-06
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] CHK001 No implementation details (languages, frameworks, APIs) — **豁免通过（记注）**：本 feature 的需求本体**就是契约面**（协议名 / 方法名 / 字段名 / 字段类型），这与 B1F1 spec 同例（契约层 spec 必须逐字写死形状，否则「契约冻结」无意义）。已核对：spec 未写代码组织、模块划分、序列化库选型、测试框架等实现手段。
- [x] CHK002 Focused on user value and business needs — 通过：5 个用户故事均以「谁 + 为何」表述（P1 freechain 持久化 / P2 上层注入可观测 / P3 图结构读取 / P4 契约冻结审计 / P5 跨仓库独立实现）。
- [x] CHK003 Written for non-technical stakeholders — **豁免通过（记注）**：本仓库 spec 的读者是实现者与**跨仓库接手方（freechain 开发者）**，协议面无法用非技术语言表述；已核对：每个用户故事都先讲「要达成什么」，再给技术判据。
- [x] CHK004 All mandatory sections completed — 通过：User Scenarios & Testing / Requirements / Success Criteria 齐备；另含 Clarifications、需求↔SC 追溯表、Key Entities、Out of Scope、Assumptions、依据。

## Requirement Completeness

- [x] CHK005 No [NEEDS CLARIFICATION] markers remain — 通过：**13 条澄清决策（Q1–Q13）**已澄清并回填（命名归属 `NodeFunc` / `Node`、span 类型归属、C27 协议面范围、图结构字段名与容器形态、`Checkpointer` 冻结粒度、`Span` 字段清单、`Store` 寻址语义、`CompiledGraph` 返回类别与参数名、span 生命周期、公开符号清单维护方式、四份交付物落盘位置等），正文无未闭合标记（`grep` 结果仅 Clarifications 段的一句说明性文字）。
- [x] CHK006 Requirements are testable and unambiguous — 通过：FR-001…FR-017 全部为「MUST + 可判定动作」；「恰为 / MUST NOT / MUST 只定义」等排他性表述消除了歧义。
- [x] CHK007 Success criteria are measurable — 通过：SC-001…SC-021 均含可数判据（数量 == 0 / 100% / 全覆盖 / 一次导入取到全部符号）。
- [x] CHK008 Success criteria are technology-agnostic (no implementation details) — **部分豁免（记注）**：SC-002 / SC-003 的「依赖闭包为空集」「零 `langchain*` import」是本项目**宪法红线**（原则 I / II）的唯一可判定口径，无法技术无关化；其余 SC 均以「对外可观察的结果」表述。
- [x] CHK009 All acceptance scenarios are defined — 通过：5 个用户故事共 19 条 Given/When/Then 场景，每条用户故事 ≥3 条且各自独立可测。
- [x] CHK010 Edge cases are identified — 通过：Edge Cases 段 **22 条**（命名冲突、协议默认实现掩盖缺实现、结构化子类型判定局限、span 父级/时间字段的 JSON 可序列化、未注入接收端、检查点标识承载、`Node` 归属裁定等）。
- [x] CHK011 Scope is clearly bounded — 通过：Out of Scope **12 条** + 「边界」明示；明确排除「第五个协议」（Q3 裁定）、公开门面（B2F2）、span 生产（B18F1）、接收端接入（B19F1）、trace 后端（B20F1/F2）、子图实现（v2）。
- [x] CHK012 Dependencies and assumptions identified — 通过：Assumptions **16 条**（复核结论属**过程记录**，已移入独立的「复核记录」节，**不计入** Assumptions）+ 前置依赖（B1F1）+ 后续解锁（B2F2 → B3F1）+ 对下游提示词口径的影响 3 条。

## Feature Readiness

- [x] CHK013 All functional requirements have clear acceptance criteria — 通过：spec 内新增「需求 ↔ 成功标准 追溯表」，FR-001…FR-017 逐条映射 SC 与 A1–A4 判据，无空缺。
- [x] CHK014 User scenarios cover primary flows — 通过：主流程（持久化接入 / 可观测接入 / 图结构读取 / 契约冻结 / 三协议端到端独立实现）全覆盖，且每条可独立验收。
- [x] CHK015 Feature meets measurable outcomes defined in Success Criteria — 通过：AC-A1↔SC-001、AC-A2↔SC-002/SC-003、AC-A3↔SC-003、AC-A4↔SC-005/SC-006 逐条对齐。
- [x] CHK016 No implementation details leak into specification — **豁免通过（记注）**：同 CHK001 —— 契约面的**形状**是需求本身；已核对无代码结构、无库选型、无测试实现细节。

## Notes

- **本次校验迭代**：2 轮（初稿 → 澄清 → 回填 → 复检；+ 2026-11-06 文档一致性复核）。
  复检项：`grep` 确认无未闭合澄清标记；FR / SC / 用户故事 / 场景 / Edge Cases /
  Out of Scope / Assumptions 计数已核对（**17 FR / 21 SC / 5 故事 / 19 场景 /
  22 Edge Cases / 12 Out of Scope / 16 Assumptions / 13 条澄清**）。
- **记注 1（CHK001 / CHK003 / CHK016）**：本仓库的 L1 契约层 spec 必须逐字写死公开形状，属项目惯例（B1F1 spec 同例），故对「无实现细节」「面向非技术读者」两项做**有据豁免**；豁免范围仅限「契约形状」，不含「如何实现」。
- **记注 2（CHK008）**：SC-002 / SC-003 的依赖口径直接引用宪法红线，非实现细节。
- **记注 3（澄清裁定）**：13 条澄清（Q1–Q13）已在 spec 的 Clarifications 段留痕，其中 Q8 于 2026-11-06 复核时**补充**了「`CompiledGraph` 参数名按 `data-model.md` §2.5 冻结为占位名」的裁定；并写入 FR-013 的冻结记录义务（④）与 Assumptions 的「对下游 feature 提示词的影响」——B18F1 交付物收窄、B22F1 命名不变、B2F1 提示词第 1 项协议名改为 `NodeFunc`。
- **记注 4（2026-11-06 一致性复核 · 第一轮）**：spec / plan / tasks 三件套 + Phase 0/1 产物的交叉复核共 22 项发现已全部就地修正（详见 `plan.md` §Phase 0 → 1 产出映射 之后的「文档一致性复核」小节）；其中「冻结面的**内容**」零改动，改动集中在**表述口径 / 判据边界 / 计数 / 仓库现状对齐**四处。
- **记注 5（2026-11-06 第二 / 三轮复核）**：第二轮 **22 项**（2 CRITICAL / 4 HIGH / 9 MEDIUM / 7 LOW）——两项 CRITICAL 经判定**均非 spec 设计缺陷**（门禁契约与任务描述的缺陷）⇒ 未开澄清轮，直接就地修正；第三轮（全局一致性）**4 项**（立项书 §5.4 的 P1 / DF4 / P5 / DF5 与 B18F1 提示词的全局漂移）⇒ 已同步修正立项书与下游提示词。
- **记注 6（2026-11-06 第四轮复核）**：`/speckit.analyze` 共 **19 项发现**（**0 CRITICAL** / 6 HIGH / 7 MEDIUM / 6 LOW）
  ——**无 CRITICAL ⇒ 无 spec 设计缺陷 ⇒ 未开澄清轮**，直接就地修正文档。冻结面的**内容一字未动**；
  spec 正文的改动仅四处**判据口径**：① **FR-005 ⑥** 的 `update_state` 签名简写补上 `config`
  （**参数顺序同属冻结面**，原简写与 `data-model.md` §2.5 矛盾）；② **FR-005 ②** 的 mode 类型口径
  与 `data-model.md` §2.5 统一为 `str | Sequence[str]`；③ **SC-011** 补「返回结构 = span 列表
  ⇒ 一批 span 整体亦可序列化」；④ 标题与 Input 引文补齐「5 个协议 + 5 个纯数据类」口径。
  复核过程记录已从 Assumptions 移入独立的「**复核记录**」节（Assumptions 仍为 **16** 条）。
- **记注 7（2026-11-06 第五轮复核）**：**14 项发现**（**1 CRITICAL** / 2 HIGH / 5 MEDIUM / 7 LOW）
  ——唯一的 CRITICAL 经判定为「任务排期缺陷」（G8 兼容矩阵门禁的测试改造在 tasks.md 中无落点）
  ⇒ 未开澄清轮，直接就地修正文档；冻结面的**内容一字未动**，改动集中在**判据口径 / 计数 / 排期**。
- **记注 8（2026-11-06 第六轮复核）**：**21 项发现**（**0 CRITICAL** / 5 HIGH / 9 MEDIUM / 7 LOW）
  ——复核范围**扩到仓库现状与上游运行时实测**（`Protocol.__protocol_attrs__` 是 `set`）。
  **无 CRITICAL ⇒ 未开澄清轮**；经发起者裁定两处（① `Checkpointer` / `Store` 的冻结粒度
  **以 `data-model.md` 为准**——参数名已冻结；② 兼容矩阵的**上游来源写进「差异说明」单元格**
  ——**保持 4 列**）后直接就地修正文档。冻结面的**内容除两处粒度澄清外一字未动**。
  **宪法无需修订**（无 MUST 违反项）。
- 标记 `[x]` 表示该项「需求质量」已被复核满足，不表示实现工作已完成。
