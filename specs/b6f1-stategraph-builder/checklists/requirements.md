# Specification Quality Checklist: B6F1 · `StateGraph` 构建器

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-15
**Feature**: [spec.md](../spec.md)

> **2026-11-20 后续修订（C25 正式作废）**：本清单中的 alias / D-74 记录保留为历史；
> 差分场景 **D-74** 已迁移到 **B8F3 D-142**，`parity_probe.py` 不再承载。

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
（零失败项 ⇒ 无需修复迭代 ⇒ 无 checkbox 状态变化）。

**Validation round 2 — 2026-11-15（上游锚点 / 接口一致性复核）· 结果：16 / 16 项保持通过**
（补齐保留字符、缺 `action`、空多源 source、路由通道 `guard=False` 等上游锚点；
新增偏离登记 X-4 与差分 D-58 / D-59；无 checkbox 状态变化）。

**Validation round 3 — 2026-11-15（澄清轮 · 接口载体 Q10）· 结果：16 / 16 项保持通过**
（发起者确认选项 A：私有 `_build_spec()` + `_BuilderSpec`；无 checkbox 状态变化）。

**Validation round 4 — 2026-11-15（澄清轮 · 路由通道位置 Q11）· 结果：16 / 16 项保持通过**
（发起者确认选项 A：路由通道放进 `_BuilderSpec.channels`；无 checkbox 状态变化）。

**Validation round 5 — 2026-11-15（澄清轮 · 更严失败信号 Q12）· 结果：16 / 16 项保持通过**
（发起者确认选项 A：保留更严的显式早失败；同时把上游可选 `add_node` 关键字与
窄 `input_schema` 推断登记为明确的范围边界；无 checkbox 状态变化）。

**Validation round 6 — 2026-11-15（`/speckit.analyze` 修复轮 · 方案 A）· 结果：16 / 16 项保持通过**
（修复 B8F1 L2 → L3 层级冲突、`START`/`END` 矩阵、`defer` 追溯、SC-007/012/013 测试覆盖、
`targets` 含 `END`、plan 遗漏 `test_stategraph_spec.py`、差分 CLI 接线等；无 checkbox 状态变化）。

**Validation round 7 — 2026-11-15（`/speckit.analyze` 第二轮修复）· 结果：16 / 16 项保持通过**
（修复 SC-001 静态边数、P-02 三态标注、`validate(interrupt)` 上游对齐、单源/多源 `END` 过滤、
D-2 条件边交接载体、差分 D-50…D-65、设计决策 DD-01…DD-15、SC-006/SC-015 覆盖、
条件 START 入口、H-5/H-7 映射、FR-003 注解、Out of Scope `destinations` 等；
无 checkbox 状态变化）。

**Validation round 8 — 2026-11-15（`/speckit.analyze` 第三轮修复）· 结果：16 / 16 项保持通过**
（修复双向追溯 T050、P-03/P-05/P-06c/P-14 实测与 E-18…E-23、`validate()` 顺序改为
「源 → 入口 → 目标 → 空节点表」（X-5）、T046 签名口径、H-2 校验职责、FR-001 构造期
私有容器、引文差异 5、X-4 的 D-66、FR-003 非法 `start_key`、`path_map=None` 快照语义、
普通 callable `.name` 不参与取名、Runnable 范围边界 X-6；无 checkbox 状态变化）。

**Validation round 9 — 2026-11-15（`/speckit.analyze` 第四轮修复 · 发起者授权）· 结果：16 / 16 项保持通过**
（修复 X-2 / Q12 把 SAME 的 D-69 误列为更严偏离；明确 H-2 的「语义一致」仅限
V-1 / V-2 / V-3，B9F1 保留名检查 / V-16 归 B7F2 最终门（第五轮已校正 V-14 标签）；P-13 限定为「非 defer SAME」并引用
B7F4 X-03；补 FR-013 / FR-015 任务追溯；T002 / T037 署名头；US3 场景 4 / D-53
有效 START 入口前置；D5 / T035 复用已有 E-18…E-23；D7 / T047 与 T046 返回语义对齐；
FR-007 ⑤ 明确新通道实例；T032 显式更新 `test_not_wired_methods_produce_no_real_semantics`（第五轮拆为 T032a/T032b）；
无 checkbox 状态变化）。

**Validation round 10 — 2026-11-15（`/speckit.analyze` 第五轮修复 · 发起者授权）· 结果：16 / 16 项保持通过**
（修复 X-3 分类为原则 XII 形态优化；补 P-02b / P-11 上游锚点与 E-24 / D-74；
收紧 FR-001 构造期保存口径与 T032a 精确 `vars(graph)` 断言；修正 T047 缺 action；
T032a 前移、T042–T044 后移；冻结 `conditional_edges` plain mapping 形状；
V-14 标签改为 B9F1 保留名检查；P-04c / P-07c / X-2 的「运行期」改为
`validate()` / `compile()`；D-56 / P-10 限定 Literal 条件；P-13 拆为 P-13 / P-13b，
新增 X-7；补 P-03c / P-04d；FR-018 浅拷贝边界、SC-001 原样口径、T001–T003 过程义务、
T033 方法级 docstring / 未交付方法消息；无 checkbox 状态变化）。

**Validation round 11 — 2026-11-15（`/speckit.analyze` 第六轮修复 · 发起者授权）· 结果：16 / 16 项保持通过**
（修复 `_ConditionalEdgeSpec` 缺 `branch`（D-2 普通映射所需）；明确 B7F2 保留完整
`_BuilderSpec` / `node_records` 供其他用途；C25 已正式作废，B8F3 不再读取 alias；明确 `path_map` 公开注解冻结、
运行时接受任意 Hashable；把“非 TypedDict”edge case 改为以 B4F1 接受面为准；
在“破冻结面”节登记 `test_facade.py` 的既有测试口径更新；统一 metadata 浅拷贝措辞；
澄清静态断点“构建器侧零动作、正向透传归 B7F2”；补 research / quickstart / parity 标题
的一致性；无 checkbox 状态变化）。

- All checklist items pass on the first validation pass.
- The specification intentionally freezes internal interface names (`_build_spec`,
  `_BuilderSpec`, `_ConditionalEdgeSpec`, `_NodeRecord`) because the user prompt requires
  the B6F1 -> B7F2 interface to be written down in this spec. These names are private
  (underscore-prefixed), are not exported by `freegraph.graph`, and do not change the
  public API snapshot.
- Upstream parity anchors are pinned to `langgraph 1.2.11` and include `path:line`
  evidence; behavior-only probes are deferred to `tests/differential/parity_probe.py`
  because this feature does not execute nodes.
- No `[NEEDS CLARIFICATION]` markers were needed: the prompt supplies the required
  decisions, and the remaining interface choices are documented in the Clarifications
  section with explicit rationale.
