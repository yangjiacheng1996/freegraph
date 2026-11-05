# Specification Quality Checklist: F1P1 契约层骨架（四个核心类型 + 异常体系）

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-05
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

**Iteration 1（2026-11-05）**

- 本 spec 刻意保留了公开符号名（`StateDict` / `Command` / `StateSnapshot` / `RunConfig` /
  `FreegraphError` / `InvalidUpdateError` / `GraphRecursionError` / `GraphInterrupt`）与包名
  `freegraph.contracts`。判定依据：这些符号**就是**本特性的交付物本身（Phase 提示词 §10 明确要求
  「spec 阶段须把命名与字段逐一写死」），不写出来反而会让 spec 不可判定；已刻意排除的内容是
  「怎么实现」（文件怎么切、怎么写类、用哪个基类、用哪个检查器）——一律留给 plan 阶段。
- 已核对本 spec 引用的每一条事实性结论均在「依据」节有来源标记
  （立项书 §5.1/§5.2/§5.3/§5.3.1/§5.4/§5.5/§9.1/§12 · Q8 §3.4/§3.4.1 · 宪法原则 I/II/VI/VII/X），
  满足宪法原则 VIII 的证据门禁。
- 迭代 1 留 3 项澄清（均属「命名 / 公开面 / 影响后续 31 个 Phase 引用」级别，无合理默认值）：
  ① 统一异常基类名 ② 四个核心类型的表示形态 ③ `Send` / `interrupt` 是否本 Phase 导出。

**Iteration 2（2026-11-05）· 全部通过**

用户答复已回写 spec，3 处标记全部清除：

| 澄清项 | 结论 | 回写位置 |
|---|---|---|
| 统一异常基类名 | **`FreegraphError`**（品牌前缀，不因语义窄化而二次改名） | FR-006 · Key Entities · Edge Cases |
| 四个核心类型的表示形态 | **`StateDict` = `dict[str, Any]` 类型别名**（硬约束：节点注解收到普通 dict 必须类型通过）；**`RunConfig` / `Command` / `StateSnapshot` = 不可变类**（具名参数构造、构造后不可改、具 repr 与字段级相等）；`Command` 另带类级常量 `Command.PARENT`；`RunConfig` 提供**裸 dict 构造路径** | FR-014 · Key Entities · User Story 1 场景 3 · Edge Cases · Assumptions |
| `Send` / `interrupt` 是否导出 | **不导出**（公开符号面严格 = 四类型 + 异常体系），归 F2P1 | FR-015 · Out of Scope |

- 决策依据补充核实（不作为 spec 的事实断言，仅供 plan 阶段参考）：LangGraph 1.2.19 源码中
  `StateSnapshot` 为 NamedTuple（`config` 字段类型为 TypedDict 形态的 `RunnableConfig`）、
  `Command` 为 `@dataclass(kw_only=True, slots=True, frozen=True)` 且
  `PARENT: ClassVar[Literal["__parent__"]]`、`RunnableConfig` 为 `TypedDict, total=False`。
  freegraph 的选择**刻意偏离** LangGraph 的混合形态（LangGraph 的配置是 TypedDict，freegraph 的运行配置是类），
  理由见 Assumptions（发起者评估：freechain 侧一次性适配成本可接受，换取形状由构造保证、不可变、字段不漂移）。
- 复跑校验结果：4 项内容质量条目全过；8 项需求完整性条目全过；4 项特性就绪条目全过。
  无 [NEEDS CLARIFICATION] 残留（`grep -c` 计数 = 0）。
- 遗留：无。下一站 `/speckit.plan`。

**Iteration 3（2026-11-05）· 澄清会话复核**

`/speckit.clarify` 提出 5 项澄清并全部获答，已回写 spec 的 `## Clarifications`（Session 2026-11-05，5 条）与相应章节：

| # | 澄清主题 | 结论 | 回写章节 |
|---|---|---|---|
| 1 | 命令原语三语义位的填写规则 | 至少填一个（全空即构造抛 `FreegraphError`）；三者可任意组合 | FR-003 · Edge Cases · SC-005 · Key Entities |
| 2 | 状态字典是否支持按 schema 参数化 | 不支持；用户改用自己的 `TypedDict` 标注节点签名 | FR-002 · Edge Cases · Key Entities |
| 3 | 裸 dict → 运行配置的构造路径与陌生键策略 | `from_dict` 默认严格（未知键抛错）+ `ignore_unknown=True` 宽松开关 | FR-014 · Edge Cases · Key Entities · User Story 1 场景 3 |
| 4 | 快照七字段的类型与时间戳格式 | 元组 + UTC ISO-8601 字符串（`created_at` 必填） | FR-004 · Edge Cases · Key Entities |
| 5 | 三个异常各自携带的信息 | 各暴露结构化属性（未知 key 列表 / 递归上限与已达步数 / 中断载荷） | FR-006 · Key Entities · SC-005 |

- 复跑校验结果：**16/16 条目全部通过（与澄清前一致，无状态翻转）**——澄清消除了 spec 内部的
  自相矛盾（FR-003「三者均可选」vs Edge Cases「须被明确拒绝」）与若干未固化的字段类型，
  未引入任何新的实现细节或未决项。
- 本轮唯一新增的降级项（已在 spec 内以默认假设固化、不构成阻塞）：`RunConfig` 四个字段的
  **具体类型注解**（`thread_id: str | None` / `context: Any` / `metadata: Mapping[str, Any]` /
  `tags: Sequence[str]`）采用默认值，属类型注解层面细节，不涉及已冻结的字段名与字段清单，
  可在 F4P1 / F8P3 按实际用法细化。
**Iteration 4（2026-11-05）· 收口扫描复核**

发起者询问「是否还存在模棱两可的地方、是否需要再跑一轮 clarify」后做了一次**全量重扫**，
发现并处理 4 项：

| # | 问题 | 处理 |
|---|---|---|
| 1 | **spec 自相矛盾（自行检出）**：SC-006 写「导入契约层后已加载模块只含顶层包与契约层」，但契约层拆成 `types.py` + `errors.py` 后 `sys.modules` 必然还含子模块，该措辞不成立 | 改为「**不含任何 freegraph 内部层模块**（契约层自身的子模块不受此限）」 |
| 2 | `Command.PARENT` 的**值与类型**未冻结 | 冻结为字符串哨兵 `"__parent__"`（与 LangGraph 同构） |
| 3 | `goto` 字段的**类型形态**未冻结 | 冻结为 `str \| Sequence[str] \| None`（单个=节点名，一组=任意序列；元组与列表都收） |
| 4 | 三个异常的**结构化属性名**未冻结 | 冻结为 `invalid_keys` / `recursion_limit` + `current_step` / `payload`（载荷保持对象形态，与 C17 一致） |

- 回写位置：FR-003（`goto` 类型 + `PARENT` 哨兵）· FR-006（属性名）· FR-014（指向 FR-003）·
  Key Entities · SC-005 · SC-006（措辞修正）· Edge Cases（新增「节点名 `__parent__` 属保留名」一条）。
- `## Clarifications` 现有 **8** 条问答对（Session 2026-11-05，两轮合并记录），无重复、无残留标记。
- 复跑校验结果：**16/16 条目全部通过（无状态翻转、无回归）**。
- 剩余非阻塞项（已在 spec 内以默认假设固化）：`RunConfig` 四字段的具体类型注解（属注解层面细节，
  不涉及已冻结的字段名与字段清单，可在 F4P1 / F8P3 无痛细化）；SC-001「同量级」无数值阈值
  （建议 plan 阶段定一个具体上限）；`tasks` / `interrupts` 元素类型（已明确归 F2P1）。
- 结论：**可以进入 `/speckit.plan`**。spec 阶段的命名与字段冻结义务（Phase 提示词 §10）已履行完毕。
- 下一站 `/speckit.plan`。

**Iteration 5（2026-11-05）· `/speckit.analyse` 后修复复核**

`/speckit.analyse` 检出 **18 项**问题（1 CRITICAL / 4 HIGH / 7 MEDIUM / 6 LOW），已按用户批准的方案修复。
spec 的实质变更：

| 变更 | 内容 | 来源 |
|---|---|---|
| **FR-016（新增）** | MUST 落两份**活文档**：仓库根 `THIRD_PARTY_NOTICES` + `README.md` 的「API 兼容矩阵」章节（覆盖本层 8 个符号，逐个标注「行为等价 / 部分等价 / 不支持」） | C1（宪法原则 X 门禁 7） |
| FR-004 | `metadata` 由可变 `dict[str, Any]` 统一为只读 `Mapping[str, Any]` | M5 |
| FR-005 | 补「可变性约定 MUST 与状态快照统一」 | M5 |
| Out of Scope | 补「**不补全也不定稿**兼容矩阵与 `THIRD_PARTY_NOTICES` —— 补全归 F24P1」 | C1 |
| Assumptions | 补三条：**容器防御性拷贝**（M3）· **`metadata` 可变性统一为 `Mapping`**（M5）· **`StateDict` 的可判定口径**（`get_origin(...) is dict`，且**不得**用 `is` / `isinstance` 判定 —— L1 / H1 / H2） | M3 · M5 · L1 |

复验结果：**16/16 条目全部通过（无状态翻转、无回归、无新增未勾选项）**——
本次变更收紧的是**可判定性**而非范围，spec 的用户价值、边界与成功标准均未改变。
H1/H2/H3 三个「断言写法本身会红」的缺陷属 **tasks.md** 层，已在 tasks.md 修正（并附实测证据）；
C1 的实质落地在 plan.md / tasks.md / README.md / `THIRD_PARTY_NOTICES` 四处，本节仅记录 spec 侧的契约变更。

- 下一站：`/speckit.implement`。

**Iteration 6（2026-11-05）· `/speckit.analyze` 复检（spec 更新后）**

发起者更新了 spec / plan / tasks 后重跑一致性分析：检出 **22 项**（0 CRITICAL / 2 HIGH / 9 MEDIUM / 11 LOW），
经发起者拍板 4 项决策后**全部修复**。三份核心文档的 FR/SC 覆盖为 **24/24（100%）**，无缺件。

4 项需发起者拍板的决策：

| # | 决策主题 | 结论 | 落地位置 |
|---|---|---|---|
| 1 | `metadata` 传 `None` 的行为（Edge Case 说「原样持有」 vs 防御性拷贝抛 `TypeError`） | **以防御性拷贝为准**，改写 Edge Case（拷贝副作用，非主动校验） | spec Edge Cases · research D-19 · spec Assumptions |
| 2 | 四字段**注解**是否随字段一并冻结 | **本 Phase 起一并冻结**（F4P1/F8P3 只能新增字段）；`tasks`/`interrupts`/`payload` 的**元素类型**仍归 F2P1 | spec Assumptions · public-api.md §6 · plan 风险表 · tasks T007/T029 · research 移交表 |
| 3 | 原则 IX「独立实现、非 LangChain Inc. 产品」声明是否补自动断言 | **补**，断言扩到 README **全文**（该声明在顶部、不在矩阵章节内） | tasks T021（G8） |
| 4 | SC-002 的 extras 口径 | **收窄为「基础安装（无 extras）闭包」**，extras 闭包另按宪法白名单校验 | spec SC-002 · architecture-gates G3 · quickstart §2.2 · tasks T019 · F1P1 提示词初稿 |

其余修复（不涉决策）：`data-model.md` I-01 判定口径（`is` → `==`，附实测证据）· 澄清条数 8 → 15（5 处）·
FR-014 的 repr / 相等语义补断言 · G4 属性类判定的门禁自检补负向用例 · T028 补追溯落点 ·
Phase 1 checkpoint 的 pytest 退出码 5 · US1 的环境口径 · `[P]` 标记与 Parallel Opportunities 对齐 ·
`git diff HEAD` 修正 · 「32 Phase / 96 人日 / C1–C26」过时数字（README · `src/freegraph/__init__.py`）·
F1P1 提示词初稿的 SC-006 / C16 / SC-002 旧口径回写。

- 复跑校验结果：**16/16 条目全部通过**（无状态翻转、无回归、无新增未勾选项）—— 本轮变更全部是
  **一致性与可判定性**的收紧，spec 的用户价值、边界与成功标准均未改变。
- 结论：**可以进入 `/speckit.implement`**。
