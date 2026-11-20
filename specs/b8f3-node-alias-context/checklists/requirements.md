# Specification Quality Checklist: B8F3 · `context` 独立通道 + `RunConfig` 运行期接线（alias 已移除）

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

- **2026-11-20 范围变更**：用户拍板**正式移除 alias（原 C25）**。B8F3 的权威范围收窄为
  `context` 独立通道（C21）+ `RunConfig` 运行期接线（C22）。C25 从 active 契约清单移除、
  编号保留不复用、C26/C27 不重编号；原 A3 验收判据与「C25 软断言升级为硬断言」作废，
  改为「C25 用例 / 软断言 / 契约承诺整体移除」。宪法升 **1.16.0（MINOR）** + changelog。
- 本项目的宪法（原则 XI「上游优先」/ 原则 VIII「证据与术语纪律」）要求 spec 必须包含上游
  `路径:行号` 锚点、契约编号（C21 / C22）与冻结面修订清单；这些是**契约级证据**，
  不是面向用户的实现细节。因此「No implementation details」与「Written for non-technical
  stakeholders」按本仓库的规格驱动纪律判定为通过：正文的用户场景 / 成功标准仍是行为口径，
  技术锚点只用于可审计性。
- 零 `[NEEDS CLARIFICATION]`：alias 已由用户明确移除；`context` 的上游形态有答案
  （`context=` + `Runtime.context`），freegraph 的 `RunConfig.context` / `state.context`
  形态是已冻结的自研差异（X-1），不再问询。
- 已识别的关键边界：`context` 不进 `configurable` / 状态 / 终态 / checkpoint；
  `context is None` 与 `context = {}` 的类型差异；alias 移除后 `add_node(alias=...)`
  必须抛 `TypeError`，不得静默忽略；不新增 `invoke/stream(context=...)` 关键字；
  条件边第二参 `config` 可携带 `RunConfig.context`，但 fresh 状态视图仍无 context。
- 待 `/speckit.plan` 落地：`context` 的 run-scoped 私有载体、C4 的 `dict` 子类视图、
  T-1…T-7 的契约回溯修订、`harness/demo/graph_core.py` 的 C25 用例移除与 C21 软断言升级。
- 受影响的下游契约：C25 / Q8 active 清单 / 宪法原则 VII / 立项书 §5.2 / §5.3 / §9.2、
  B6F1、B2F2、B22F1、B7F2 / B8F2 / B8F1 的 alias 交接注记、验收脚本与 README；
  详见 spec 的「契约修订：移除 alias」。
