# Specification Quality Checklist: B22F1 · `get_graph(xray=)` + 自有 `Graph` 类型 + `draw_mermaid()`

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-20
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

- **记注 1（技术锚点的必要性）**：本仓库的 spec 模板与宪法原则 XI 明确要求
  「上游行为断言 MUST 带版本 + `路径:行号`」、跨 feature 承接 MUST 落 FR + 裁定、
  验收判据 MUST 到判据级。故 `Upstream Parity` / `Clarifications` / `Assumptions`
  中的源码路径、行号、类型名与契约编号是**治理要求的可追溯锚点**，
  不是面向实现的技术选型；功能需求本身（FR-001…FR-029）仍以**可判定的行为**表述。
- **记注 2（零澄清标记）**：动态目标来源、`END` 边来源、mermaid 转义 / 头部口径、
  导出与 `stream()` 的隔离均已在 `Clarifications` 以 Q1–Q8 拍板；
  上游有答案处一律照抄（原则 XI），无答案处给出唯一裁定 ⇒ **零** `[NEEDS CLARIFICATION]`。
- **记注 3（与上游的刻差分叉）**：P-01 / P-05 / P-07 / P-10 / P-12 为 **DIFF**；
  P-04 为 **SAME（结构）/ DIFF（标签）**；P-14 为 **SAME（常规）/ DIFF（末步单源：自环 / 循环）**；
  P-08 / P-11 为 **STRICTER**；其余（含 P-09 静态声明、P-13、P-15～P-19）为 **SAME**；
  全部在「偏离登记」X-01…X-13 留痕。
- **记注 4（冻结面 · 发起者 2026-11-20 追认）**：为采用上游最优设计，本 feature **破**
  B1F1（`Command` 泛型）· B6F1（`add_node` 增 `destinations`）· B7F2（快照携带声明）·
  B9F1（原运行期记录 D-8 作废）· B2F1（`Graph` 追加 `draw_mermaid`；`Edge.condition`
  对无标签声明边放宽为 `None`）；逐条落「破冻结面的回溯修订清单」T-1…T-6。
- **记注 5（clarify 轮用户决策）**：① 原「累积并集」作废，改为上游静态声明（图与运行次数无关）；
  ② 采用「类型推断 + destinations」两者都做；③ 无标签声明边 `condition=None`（照抄上游）。
- **记注 6（验收映射）**：立项书 §5.2 的 A1–A4 已逐条映射到 SC-001 / SC-003 / SC-004 /
  SC-008 / SC-009，无悬空判据。
