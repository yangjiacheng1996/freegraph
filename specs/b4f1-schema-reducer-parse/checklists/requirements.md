# Specification Quality Checklist: B4F1 · 状态 schema 解析 + 归约器提取（`TypedDict` + `Annotated` → 通道规格）

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-08
**Feature**: [spec.md](../spec.md)

> **记注（与 B2F2 / B3F1 同例）**：本仓库的 spec 读者是**实现者**与**跨仓库接手方（freechain 开发者）**；
> 凡「需求本体就是对外形状 / 数据契约」的 feature（契约层 · 门面 · 本 feature 的解析产物字段与
> 二元性判据），对「无实现细节」「面向非技术读者」两项做**有据豁免**——豁免范围**仅限契约形状**，
> 不含「如何实现」。

## Content Quality

- [x] CHK001 No implementation details (languages, frameworks, APIs) — **豁免通过（记注）**：本 feature 的需求本体
  就是**解析产物的数据契约**（字段构成 + 取值域）与**二元性判据**（与上游逐条一致），与 B1F1 / B2F1 / B2F2 同例。
  已核对：spec 未指定模块划分、**函数命名**（FR-020 明确「解析入口的函数名由 plan 定」）、测试框架、
  序列化库、CI 配置；FR-009 用「**等价于** `get_type_hints(..., include_extras=True)`」表述**判据**而非实现手段；
  FR-011 的投影只规定**必须可序列化**与**确定性**，不规定实现方式。
- [x] CHK002 Focused on user value and business needs — 通过：4 个用户故事均以「谁 + 为何」表述
  （P1 追加语义被识别 / P2 计数型 key 走覆盖 / P3 别的 `Annotated` 不被误判 / P4 写错的 schema 在解析期就报错），
  每个故事都先讲「要达成什么」，再给可判定的技术口径。
- [x] CHK003 Written for non-technical stakeholders — **豁免通过（记注）**：「二元归约器」「`Annotated` 末位元数据」
  「位置参数计数口径」无法用非技术语言表述；但每个故事都先讲用户视角的结果
  （「消息能累积成完整历史」「`llm_calls` 真的是计数」「说明文字不会让语义变味」「建图前就报错」），
  再给技术判据。
- [x] CHK004 All mandatory sections completed — 通过：User Scenarios & Testing / Requirements / Success Criteria 齐备；
  另含「澄清与裁定」（**14 条裁定** + **6 条引文差异说明**）、需求 ↔ SC **追溯表**、Key Entities（7 项）、
  Out of Scope（**12 条**）、Assumptions（**14 条**）、依据（9 组）。

## Requirement Completeness

- [x] CHK005 No [NEEDS CLARIFICATION] markers remain — 通过：**14 条裁定**（非法 schema 抛错不降级 / 异常类型 /
  `TypedDict` 鸭子判定 / `Required` 剥离 / 注解解析方式 / 落位与公开面 / Pydantic 不支持 / A2 比对方式 /
  「类」与「签名不可取」/ 引用持有 / 纯数据与投影 / 继承与 `__slots__` / 通道注解形态）
  + **6 条引文差异说明**（FR-006 二选一 · SC-003 口径细化 · Pydantic 边界 · 类型拆分 · SC-004 具体化 · 标准库依赖）
  已回填正文，正文**无未闭合标记**（实测 `grep -c 'NEEDS CLARIFICATION' spec.md` == 0）。
- [x] CHK006 Requirements are testable and unambiguous — 通过：FR-001…FR-020 全部「MUST + 可判定动作」；
  排他性表述消除了歧义（「**恰好** 2 个位置参数」「计数口径 = 位置专用 + 位置或关键字，`*args` / `**kwargs` /
  keyword-only **不计入**」「**顶层**的 `Required` / `NotRequired`」「保序」「取值域固定为
  `{overwrite, reduce}`」「**零新增**公开 API」）；FR-004 / FR-007 / FR-020 给出逐项可断言的清单与取值域。
- [x] CHK007 Success criteria are measurable — 通过：SC-001…SC-017 均含可数判据
  （命中率 == 100% / 次数 == 0 / 覆盖率 == 100% / 条数 == key 数 / 一致率 == 100% / 抛错次数 == 1 /
  边数 == 0 / 新增行数 == 0 / CI 安装次数 == 0），并含**负向**判据（静默降级次数 == 0 ·
  被接受为归约器次数 == 0 · 因 key 可选而拒绝 schema 的次数 == 0 · 必填性校验触发次数 == 0）。
- [x] CHK008 Success criteria are technology-agnostic (no implementation details) — **部分豁免（记注）**：
  SC-004 的「与上游 `_is_field_binop` 判定结果一致」、SC-011 / SC-012 的「`sys.modules` 快照」「层注册表 / import 图」
  是本项目**宪法红线**（原则 I / II / ARCH-1）与 **A2 判据**本身的唯一可判定口径，无法技术无关化；
  其余 SC 均以「对外可观察的结果」表述（解析结果相等 / 错误消息含 key 名 / 规格条数 == key 数）。
- [x] CHK009 All acceptance scenarios are defined — 通过：4 个用户故事共 **16 条** Given/When/Then 场景
  （P1 4 条 / P2 4 条 / P3 4 条 / P4 4 条），每条独立可测，且覆盖正向、误判与错误路径。
- [x] CHK010 Edge cases are identified — 通过：Edge Cases 段 **30 条**（`operator.add` 身份判定 /
  多条目元数据 / 字符串元数据 / **类**末位 / 内置类型末位 / 3 参 / 1 参 / `a,*args` / `a,b,*args` / `a,b,*,c` /
  `*,a,b` / `Required` 包裹 / 继承 / **`total=False` 可选 key** / **字符串注解下的 `Required` 不可辨** /
  字符串注解 / 不可解析前向引用 / 非 TypedDict / **多问题只报第一个** / 空 TypedDict /
  `__slots__` / 同一 callable 复用 / 有状态归约器 / 归约器不被调用 / 中间条目是类或实例 /
  上游版本漂移与判定表快照）。
- [x] CHK011 Scope is clearly bounded — 通过：Out of Scope **12 条** + FR-015；明确排除通道实现（B5F1）/
  稀疏状态读取（B5F2）/ 调度循环（B7F1）/ `StateGraph` 构建器（B6F1）/ Pydantic（v2.0）/
  `add_messages`（freechain）/ `Annotated[T, SomeChannel]` 形态 / `Overwrite` 旁路 / 归约器执行语义 /
  兼容矩阵新增行 / CI 挂载 / 第三方依赖引入。
- [x] CHK012 Dependencies and assumptions identified — 通过：Assumptions **14 条**（权威顺序 / 规模参考 /
  spec 目录命名与偏离记录 / 分支 / Python 基线与 typing 上限 / 内核零第三方依赖 / `langgraph` 仅 dev-test 依赖与
  核实版本 / 上游行号引用纪律 / 代码落位与层注册表零改动 / 类型可读文本口径 / 既有冻结面零改动 /
  人工验证记录五段式 / A2 比对只比判定结果 / 前置 B2F2 与后续 B5F1）
  + 前置依赖（**B2F2**）+ 后续解锁（**B5F1**）。

## Feature Readiness

- [x] CHK013 All functional requirements have clear acceptance criteria — 通过：spec 内含「需求 ↔ 成功标准 追溯表」，
  **FR-001…FR-021** 逐条映射 SC 与 **A1–A3** 判据，无空缺；每条 FR 至少挂 **1** 条 SC。
- [x] CHK014 User scenarios cover primary flows — 通过：主流程（追加识别 / 覆盖语义 / 不误判 / 早失败）全覆盖，
  且每条可独立验收（P1 只解析一个带归约器的 key 即成立）。
- [x] CHK015 Feature meets measurable outcomes defined in Success Criteria — 通过：
  **A1** ↔ SC-001 / SC-004 / SC-010 · **A2** ↔ SC-003 / SC-004 / SC-014 · **A3** ↔ SC-002 / SC-008，
  逐条对齐且均为可数判据。
- [x] CHK016 No implementation details leak into specification — **豁免通过（记注）**：同 CHK001 ——
  需求本体即**数据契约**（字段与取值域）；已核对无库选型、无测试实现细节、无 CI 配置、无模块命名规定。

## Notes

- **本次校验迭代**：2 轮（初稿 → 自检 → 修正 → 复检；+ 2026-11-08 澄清轮 Q1–Q5）。计数已核对
  （**21 FR / 17 SC / 4 故事 / 16 场景 / 30 Edge Cases / 12 Out of Scope / 14 Assumptions /
  14 条裁定 + 10 条澄清问答（Q1–Q10 · 两轮）+ 6 条引文差异说明**）。
- **记注 1（CHK001 / CHK003 / CHK016）**：本仓库「对外形状 / 数据契约」类 spec 必须逐字写死字段与判据，
  属项目惯例（B1F1 / B2F1 / B2F2 同例）⇒ 对三项做**有据豁免**；豁免范围仅限「契约形状」，不含「如何实现」。
- **记注 2（CHK008）**：SC-004 / SC-011 / SC-012 的口径直接引用宪法红线与 A2 判据，非实现细节。
- **记注 3（自检中修正的一处）**：初稿的 SC-003 沿用引文原文「位置参数数 ≠ 2 时 100% 不被当作归约器」，
  与 FR-007 的「抛错」口径之间存在**「不被当作归约器」是否蕴含「解析成功」的歧义**
  ⇒ 已在裁定 1 与 SC-003 中逐字补「**且解析失败**（MUST NOT 静默降级）」，两处口径一致化。
- **记注 4（未闭合项）**：**无**。全部歧义点已在「澄清与裁定」段留痕并回填正文，正文无 `[NEEDS CLARIFICATION]` 标记。
- **记注 5（偏离登记 · 目录命名）**：`.specify/init-options.json` 的 `feature_numbering: sequential`
  通用算法在本仓库**未被使用**（既有 4 个 spec 目录均无数字前缀，且以 feature ID 为键，
  与 `harness/features/` / `harness/verification/` 对齐）⇒ 本 feature 沿用既有约定
  `specs/b4f1-schema-reducer-parse`，**显式偏离记录**于 Assumptions 第 3 条。
- **记注 6（证据取样 · 本会话实测）**：裁定 3 / 4 / 9 的实测依据（`typing.is_typeddict` 对
  `typing_extensions.TypedDict` 返回 `False`；`Required[Annotated[...]]` 顶层 `__metadata__` 为 `None`；
  `inspect.signature(str)` 抛 `ValueError`）与上游行号（`langgraph/graph/state.py:1853-1858` / `:1904-1922`，
  核实环境 `langgraph 1.2.11`）已逐条写入裁定与「依据」节。
- 标记 `[x]` 表示该项「需求质量」已被复核满足，不表示实现工作已完成。
- 记注 10（2026-11-08 澄清轮 · Q1–Q5）：就 spec 中 5 处会实质影响实现 / 验收的模糊点提问，
  发起者**逐条选定推荐项 A**，已全部回填正文（每条含理由与落点，正文无未闭合标记）：
  **Q1** 通道规格的「类型信息」= **只存基类型 `T`**（不保留 `Annotated` 包装 / 原始注解）·
  **Q2** 可选 key（`total=False` / `NotRequired[...]`）= **记录但不执行**（带「必选/可选」标记，
  校验归 B7F3；新增 FR-021 + SC-016）· **Q3** 多问题 schema = **快速失败**（只报第一个）·
  **Q4** 错误类型**放在 L2、靠基类捕获**（`except FreegraphError` / `except ValueError` 均可捕获；
  契约层 18 符号面与门面 7 符号面**零改动**）· **Q5** A2 对照 = **本 feature 零依赖声明、CI 不装
  `langgraph`**（判定表是上游行为的固化快照；实时对照留给 B5F2 / B8F1 的差分夹具；本机临时装一份
  当参考读物允许）。
  **修订面**：**裁定 8 改写** + **新增 FR-021 / SC-016**；FR-002 / FR-007 / FR-016 / FR-019 / FR-020 收紧；
  追溯表新增 FR-021 行；Edge Cases +3 条；Key Entities +1 项；Assumptions 改写 1 条。
  **16 项清单状态无变化（16/16）**，追溯表 **21 FR ↔ 17 SC** 全覆盖。
- 记注 11（2026-11-08 第二轮澄清 · Q6–Q10）：就 spec 中**又一批**会实质影响实现 / 验收的模糊点提问，
  发起者逐条选定（Q6=A · Q7=A · Q8=A · Q9=B · Q10=A），已全部回填正文（正文无未闭合标记）：
  **Q6** 末位元素是**类 / 可调用实例**时 = **纯机械判定**（类与实例都不特殊排除）——
  ⚠️ 本条**修正了裁定 9 的漏洞**：原表述「类在末位 ⇒ 拒绝」只对「`__init__` 无参的类」成立，
  实测 `class TwoArgInit`（`__init__(self, a, b)`）的签名恰为 `(a, b)` ⇒ 机械判据会**接受**它
  （与上游同构）；裁定 9 已改写 + 补 7 条实测事实。
  **Q7** 错误对象**带结构化字段**（「出错的 key」+ 封闭取值域的原因码
  `not_a_typed_dict` / `reducer_not_binary` / `annotation_unresolvable`；消息只作英文摘要）——
  与仓库既有 `InvalidUpdateError` 同构。
  **Q8** 通道规格 / 规格集的**字段名现在就冻结**
  （`ChannelSpec` = `key` / `value_type` / `reducer` / `has_reducer` / `semantics` / `required`；
  `SchemaSpec` = `channels` / `keys`）—— 这是 B4F1 → B5F1 → B6F1 的**跨 feature 契约**。
  **Q9** A2 判定表的**最低覆盖面** = 二元性判定 **≥ 14 类** + 归约器提取 **≥ 2 类**
  （逐条对应上游判据的一个分支）。
  **Q10** 投影里归约器的标识 = **模块名 + 限定名**（并连带补齐两处漏洞：可调用实例取**其类型**的
  模块名 + 限定名；兜底 `repr` MUST 抹除内存地址形态 ⇒ 快照不假红）。
  **修订面**：裁定 9 **改写** · FR-003 ③ / FR-007 ⑥ / FR-011（改写）/ FR-016 ①-a·①-b（新增 16 行覆盖表）/
  FR-020（**改写**为含字段名的表格）· **新增 SC-017** · SC-004 / SC-005 / SC-006 收紧 ·
  Edge Cases **+4 条**（类 3 签名 / 可调用实例 / partial 与绑定方法 / lambda 与实例的投影标识）·
  Key Entities 改写 2 条 + 新增 1 条 · 「依据」节补 7 条实测取样 · 追溯表 FR-007 增列 SC-017。
  **16 项清单状态无变化（16/16）**，追溯表 **21 FR ↔ 17 SC** 全覆盖。
- 记注 12（2026-11-08 分析轮 · `/speckit.analyze` 的 13 项发现 · **0 CRITICAL** ⇒ 未新开 clarify 会话，
  按授权**直接修文件**）：**A1** 人工验证记录文件**无创建任务** ⇒ T005 改为「**创建骨架** + 取基线」、
  T052 改为「**回填**」（**不新增任务 ID** ⇒ 避免 51 条重编号）；**A2** 错误类型的「捕获路径」与
  「读结构化字段的路径」在 Q4 与 Q7 之间有缝隙 ⇒ **新增裁定 14**（捕获用基类；读字段 MAY 从
  `freegraph.runtime` import 具体子类 ⇒ **零冻结面变更**）；**A3** 4 条 Edge Case 无覆盖 ⇒ 并入
  T015 / T016 / T023；**A4** FR-021 ② 与 SC-011 的 import 期口径无断言 ⇒ 并入 T024 / T048；
  **A5** FR-002 与 FR-020 ① 字段清单重复 ⇒ FR-002 改为指向 FR-020 ①；**A6** SC-014 与 FR-017
  负向形态重复枚举 ⇒ SC-014 改为引用 FR-017；**A7** 「类型信息」↔ `value_type` 术语漂移 ⇒ FR-002 括注；
  **A8** `tests/contracts/test_contract_regressions.py` 未入零改动清单 ⇒ 已补（含「MUST NOT 改
  `status=not-landed`」）；**A9** FR-013 对 `pydantic` 的禁令在 v1.0 是**空断言** ⇒ 加标注（保留为 v2.0 前置防线）；
  **A10** T004 缺「输入表达式求值机制」⇒ 已补（映射到 `binary-criterion.md` §4 夹具清单）；
  **A11** `ci.yml` 是 FR-016 ③ 的**第 4 处**声明位 ⇒ 并入 T049 + 闸口 A4；**A12** 立项书 C1 字面含
  Pydantic ⇒ 在 spec「依据」节登记（**不改立项书**）。
  **修订面**：spec（FR-002 / FR-007 ⑤⑥ / FR-013 / SC-014 / SC-017 + **裁定 14** + 依据）·
  plan（Structure Decision + 门禁纪律）· research D-08 · contracts/schema-parse-contract §4 ·
  quickstart §4 · tasks（T004 / T005 / T015 / T016 / T023 / T024 / T048 / T049 / T052 + 零改动清单 +
  闸口 A4 + 追溯表 9 行）。
  **FR / SC 条数不变（21 / 17）· 任务条数不变（56）** ⇒ 追溯表 21/21 · 17/17 仍全覆盖。
  **16 项清单状态无变化（16/16）**（本次为**措辞与覆盖面**收敛，未新增需求 ⇒ CHK005–CHK015 的判定结论不变）。
