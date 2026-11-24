# Specification Quality Checklist: B24F1 · 打包分发 + API 兼容矩阵 + `THIRD_PARTY_NOTICES`

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-24
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

- **项目特化说明（不影响通过判定）**：本仓库的 `spec-template` **强制要求**「Upstream Parity」章节
  携带上游 `路径:行号` 与实测锚点（宪法原则 XI / 原则 VIII），并将门禁脚本、矩阵文件名、
  产物目录作为**判据载体**写入。这些不是通用意义上的「实现细节泄漏」，而是本项目
  「可审计契约」的组成部分；因此 `No implementation details` 一项按**项目口径**判为通过。
- 所有用户场景均带**独立验收**方式；P1 三组（安装 / 纯度 / 机械拦截）与 P2 两组（矩阵 / README）
  各自可独立测试。
- **A-2** 已由发起者拍板为「部分等价」（2026-11-24 Clarifications），并登记纠正上游对齐批次 P3（commit `99d43aa`）漂移；
  不留 `[NEEDS CLARIFICATION]`。`goto` 缺省 `()` vs `None` 单列为 **Y-01（既有 DIFF）**，
  **不得**并入 X-06 的 STRICTER；`get_state` 无快照 `None` vs 上游空 `StateSnapshot` 与 `Send` 不可变
  分别登记为 **Y-02 / Y-03**（既有 DIFF）。`.gitignore` 已从 sdist 允许项移除（Release Gate 口径）。
- 18 项覆盖表把 SC-004 的「逐项可核对」落成可判定表格；下游承接 H-1…H-9 全部映射到 FR / SC。
- **Release Gate 的 `.gitignore` 口径**：sdist 根级 `.gitignore` 不允许；`uv build` 在输出目录生成的 `dist/.gitignore` 是构建工具标记，MUST 豁免；「额外产物」只针对归档类非 `.whl` / `.tar.gz` 文件。
- **纯度脚本的 METADATA 检查**只用标准库（`email.parser.Parser` + PEP 503 规范化），**MUST NOT import `packaging`**；发布流水线以系统 `python3` 直接执行该脚本。
- **构建产物依赖**：US1 / US3 的 T013 / T014 / T022 在无预构建 `dist/` 时 MUST 自行 `uv build`（不得假设 US2 先完成）。
- **SC-008** 的判据级覆盖由 T042 的自动文档守卫承担（宪法 v1.13.0）；写记录 / 审计任务不算判据覆盖。
- **质量门禁 5**（真实模型轮）已在 `spec.md` / `plan.md` / `tasks.md` 登记偏离（承接 **B25F1**，M4），并由发起者于 2026-11-24 analyse 轮追认；T046 为合入阻断追认任务。
- 本 feature 不新增门禁编号（FR-019）；**破 G8 / G19 / G29 的取行源**（`README → COMPAT.md`，已获发起者 2026-11-24 选项 A 追认）；不产生运行时行为变更。
- **宪法原则 XI 的可验证出口**由 **T050** 的最小差分组 `B24F1-D-01…D-03` 承担（只断言 Y-01 / Y-02 / Y-03 既有差异；上游缺席 skip）。
- **G19 的 `Command` 例外**为单点定向例外：仅 `行为等价 → 部分等价` 放行；`Command` 不整体移出单调检查，其它任何等级变化（含 `部分等价 → 不支持`）仍失败；其它行仍不可降级（并有 `Send` 降级与 `Command` 其它降级负向自检）。
- **README / `THIRD_PARTY_NOTICES` 的术语清理**已写入 T032 / T029 / T033：旧计数（31 / 93 / 契约层 18·20·21 / 门面 7）与旧 feature 编号（F1P1 / F24P1）MUST 清除；根文档的旧编号与旧计数已在本轮分析修复中直接清理。
