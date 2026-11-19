# Specification Quality Checklist: B23F1 · `draw_mermaid_png()`：离线不阻断 ★

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

- **记注 1（技术锚点的必要性）**：本仓库 spec 模板与宪法原则 XI 要求
  「上游行为断言 MUST 带版本 + `路径:行号`」、跨 feature 承接 MUST 落 FR + 裁定、
  验收判据 MUST 到判据级。故 `Upstream Parity` / `Clarifications` / `Assumptions` 中的
  源码路径、行号、PNG 块名与契约编号是**治理要求的可追溯锚点**，不是面向实现的技术选型；
  功能需求本身（FR-001…FR-020）仍以**可判定的行为**表述。
- **记注 2（零澄清标记）**：方法签名 / 占位图语义 / PNG 合法性判据 / 离线路径 / 文本复用 /
  失败信号 / 确定性 / 公开面 / v1-v2 边界 / 并发均在 `Clarifications` 以 Q1–Q10 拍板；
  上游有答案处照抄（原则 XI），无答案处给出唯一裁定 ⇒ **零** `[NEEDS CLARIFICATION]`。
- **记注 3（与上游的刻差分叉）**：P-04 / P-09 / P-11 为 **STRICTER**；
  P-05 / P-06 / P-07 / P-10 / P-12 / P-14 为 **DIFF**；P-01 / P-02 / P-03 / P-08 / P-13 为
  **SAME（挂载 / 类别 / 文本来源 / 判据）**；全部在「偏离登记」X-01…X-05 留痕。
- **记注 4（v1 口径）**：宪法 v1.7.0 / 立项书 D15 冻结「v1.0 无 extra」⇒ 本 feature 只交付
  方案 C（占位 PNG）；真实渲染与 `[png]` extra 归 v2.0 / B26（**D-2**）。
- **记注 5（冻结面 · 仅追加）**：`Graph` 只追加 `draw_mermaid_png()` 方法（**T-1**）；
  字段 / 构造签名 / 不可哈希 / `__all__` / 既有 `draw_mermaid` 语义**均不改**。
- **记注 6（验收映射）**：立项书 §5.2 的 A1–A4 已逐条映射到 SC-001 / SC-002 / SC-005 /
  SC-003，无悬空判据；固定脚本 diff（SC-009）与人工验证记录（SC-009）为门禁项。
- **记注 7（零出站的最强判据）**：「捕获网络异常后返回占位」**不算合规**（请求已发出）⇒
  FR-007 要求实现路径**无网络代码**，并以静态扫描 + socket 监测双证据（SC-003）判定。
