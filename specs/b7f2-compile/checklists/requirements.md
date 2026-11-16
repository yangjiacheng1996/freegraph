# Specification Quality Checklist: B7F2 · `compile()` → `CompiledGraph`

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-16
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

**Validation round 1 — 2026-11-16（初版 spec 写定后的自检）· 结果：16 / 16 项全部通过**
（零失败项 ⇒ 无需修复迭代 ⇒ 无 checkbox 状态变化）。

**逐项判定依据**：

- *No implementation details*：全部需求以「用户可观察的行为 / 失败信号 / 判据」表述；
  源码路径与行号只出现在 **Upstream Parity** 与 **依据** 两节（宪法原则 VIII 的
  证据纪律要求），不出现在需求正文。
- *Focused on user value*：6 条 User Story 全部以用户视角写成（拿到可执行图 / 注入
  可插拔能力 / 早失败 / 断点落地 / 一次编译多次安全使用 / 编译期零副作用）。
- *All mandatory sections completed*：User Scenarios & Testing · Upstream Parity（含
  差分场景组 + 偏离登记 + 破冻结面）· Requirements（FR + Key Entities + 追溯表 +
  Out of Scope）· Success Criteria · Assumptions **全部填写**，无占位符残留。
- *Requirements are testable*：FR-005 的**编译期检查清单 14 项**与 FR-006 的**明确
  不检查项 7 项**逐条给出失败信号与判定来源 ⇒ 无歧义；FR-013 / FR-014 把静态断点的
  容器形态门与元素级失败信号分开写死。
- *Success criteria are measurable*：16 条 SC 全部含量化口径（比率 == 100% / == 0% /
  计数 / 逐条一致），其中 SC-003 / SC-006 / SC-007 逐项对应提示词 §5 的 SC-001…SC-005。
- *Technology-agnostic*：SC 表述为「被记录 / 被读到 / 显式失败 / 零残留」等可观察结果，
  不点名实现手段（`GraphSpec` 等内部载体只在 FR 正文作为**契约引用**出现）。
- *All acceptance scenarios are defined*：6 条 User Story 各有 2–4 条 Given/When/Then，
  覆盖提示词 P1 / P2 / P3 三条独立验收。
- *Edge cases are identified*：30 条 Edge Cases 覆盖空图 / 缺入口 / `END` 过滤 /
  多源形态 / `__parent__` / 动态路由 / 静态断点 8 种非法形态 / 未就绪关键字 /
  重复编译 / 编译后改图。
- *Scope is clearly bounded*：Out of Scope 逐条点名归属 feature（B7F3 / B8F1 / B8F2 /
  B8F3 / B14F1 / B15F1 / B16F1 / B22F1 / B23F1 / v2 extras）。
- *Dependencies and assumptions identified*：承接条款 H-1…H-7 + 下游承接 D-1…D-5 +
  Assumptions 13 条（含上游版本钉死与「签名比较口径」）。

**无 `[NEEDS CLARIFICATION]` 标记**：提示词初稿已给出全部关键决策；剩余的实现级选择
（编译产物实现体位置、私有字段清单、静态断点容器门、checkpointer 校验时机）已在
Clarifications 的 **14 条裁定**中写死并写明理由，plan 阶段不得再翻。

**已知的有意偏离**（原则 XI 的「必须自研区」穷举为**四类**，不在其中的分叉一律照抄）：12 条偏离登记 **X-1…X-12**，
其中 1 条 STRICTER（X-2 · 裸空串静态断点）、11 条 DIFF（分层接缝 / 定位边界 /
能力未就绪 / 零环境变量红线 / 形态优化 / 命名形态），每条均有对照表对应行且关系标注
**逐字一致**（宪法 v1.12.0）。

**上游锚点**：钉死 `langgraph 1.2.11`（取证于 2026-11-16 · `.venv` 实际安装版本），
每条上游行为断言附 `路径:行号`；行为面断言由差分场景 **D-75…D-91** 覆盖（上游缺席
即 skip）；差分判词与 Upstream Parity 表逐条一致（SC-016 判据）。

**与提示词初稿的差异**（已在 spec「引文差异」表登记 7 条）：其中**引文差异 2** 是
实质澄清 —— 提示词 P3 说的「路由目标不在 `path_map` 里」在编译期**不可判定**
（只有调用路由函数才知道返回值），编译期只查「`path_map` 的目标节点存在」与
「`path_map` 形态合法」；「路由返回值不在 `path_map` 中」归 B8F1 运行期显式失败。
**引文差异 1** 同理 —— 提示词 §2 举的「节点不可达」**不做**（裁定 9）。

**Validation round 2 — 2026-11-16（`/speckit.clarify` 轮）· 结果：16 / 16 项保持通过**
（无 checkbox 状态变化）。

- *上游自查补记 5 条（S-1…S-5）*：初版 spec 的 5 处「自设约束」经上游核对**全部有
  上游答案** ⇒ 按收窄纪律**照抄、不问用户** ⇒ 已改写：注入项与断点配置改为**公开
  只读属性**（上游 `Pregel` 同款 · 新增 P-03c / X-10）；门面不导出编译产物类有了
  上游依据（新增 P-03b · SAME）；`debug` 缺省**硬编码** `False`（新增 P-17b / X-9 ·
  零环境变量红线）；`NotImplementedError` 与 L1 协议「查不到 ⇒ 空值」的**层级边界**
  写进 FR-011；`_spec` / `_builder_spec` / `_conditional_edges` 三个**字段名冻结**
  为跨 feature 接口。
- *用户裁定 1 条*：`store=` 传入非 `None` 时**发恰好 1 条 `warnings.warn`**
  （选项 A · 裁定 14）；其余「已接受但 v1 无行为」的注入项**只记录 + 文档写明**、
  MUST NOT 发警告 ⇒ 已落 FR-016 / SC-015 / Edge Cases / X-3 / D-78。

**Validation round 3 — 2026-11-16（`/speckit.plan` 阶段的上游实测补记）· 结果：16 / 16 项保持通过**
（无 checkbox 状态变化）。

- 新增实测 **E-25…E-55**（`langgraph 1.2.11`）：`compile()` 无参 / `store=` 无警告 /
  `checkpointer=object()` ⇒ `TypeError` / 元组与裸串断点 ⇒ `TypeError` / 裸空串 ⇒ **放行** /
  `["*"]` 与未知节点 ⇒ `ValueError` / 产物公开属性 8 项 + `nodes`/`channels`/`builder` /
  「已编译后改图」是 **`logging`** 而非 `warnings` / 空图放行。
- 由实测**新增**：**P-03d + X-11**（断点属性暴露**归一后的元组**；上游保留原值 ⇒ 形态优化类
  DIFF）；**P-14 / X-8** 补「路由通道只为条件边静态目标建（上游每节点建）」；
  **P-17** 补「`name` 缺省值差异属签名冻结面」；**Q2 的落地文件名**由 `_compiled.py` 修正为
  同模块 `_stategraph.py`（L3 单文件 · 避免 G25 的 L3→L3 违规 · 裁定本身未改）。
- 偏离计数（round 3 当轮）：**10 → 11** 条（X-1…X-11；round 5 已增至 X-1…X-12）。

**Validation round 4 — 2026-11-16（`/speckit.analyze` 修复轮 · 发起者授权）· 结果：16 / 16 项保持通过**
（无 checkbox 状态变化）。

- **A1（判据反转）**：`SC-011` 的「**零**状态残留的通道数 == 0」改为「**非零**状态残留的通道数 == 0」。
- **I1 / I2（`graph_core` 三角冲突）**：统一为「**先跑 A3、再探 `invoke`**」——`SC-001` / `SC-002`
  写明 A3 组真跑通过且随后以**退出码 2** 结束；破冻结面**禁止**把守卫改成「6 方法能力面 ⇒ 已就绪」
  （会打红 `test_graph_core_exits_two_when_the_facade_is_not_ready` 的 `rc == 2` 硬断言）。
- **A2（载体形态）**：`FR-002` / `FR-010` / 裁定 3 / `P-03c` 的「公开只读属性」统一为**公开实例属性**
  （**MUST NOT** 用 `@property`，否则 `vars()` 11 键口径不成立）；「只读 = 用户不需要写」写入 FR-010。
- **A3（时机例外）**：`CV-13` / `C-13` 明确「**早于** `compile()`」（B6F1 立即层），其用例包裹
  `add_conditional_edges`；同步 `data-model.md` / `compile-contract.md`。
- **A4（机制术语）**：`P-13` / `X-5` / `Q11` 的「warning」改为 **`logging` 提示**（实测 E-49/E-50；
  与本 feature `store` 的 `warnings.warn` 区分）。
- **D1（去重）**：`FR-013` ①② 改为引用 `FR-005` 的 **C-11 / C-12**（单一规范正文）。
- **I3 / I4 / I5 / I6 / I7 / U1 / U2（tasks / plan）**：`T020` 收窄为行为断言 + 新增 **`T043b`**
  （README 文本，紧随 T043）；`T013` 补齐 `test_not_wired_compile_reports_b7f2` 并把「删除」改为
  「替换为反面断言」；`T005` 明确 **11 个参数** + **协议导入别名 `CompiledGraphProtocol`**；
  `T023` 的 CV-13 包裹登记调用、CV-11/12 只做引用；`T042` 改为「先跑 A3 再退出 2」；
  plan 的 `E1` / `DD-15` / `R-2` / 改动面 #12 同步，并补 **plan Phase A–E ↔ tasks Phase 1–9** 映射。
- 任务总数 **54 → 55**（`T043b`）；FR / SC / 裁定 / 偏离计数（round 4 当轮）不变（25 / 16 / 14 / 11；round 5 已增至 X-1…X-12）。
- **宪法**：本轮**无需修改**（分析未发现任何 MUST 违规）。

**Validation round 5 — 2026-11-16（`/speckit.analyze` 第二轮修复 · 发起者授权）· 结果：16 / 16 项保持通过**
（无 checkbox 状态变化）。

- **INC-1（SC-009 边数口径）**：明确「边表在应用 FR-007 的单源 `END` 过滤**后**与快照一致」。
- **INC-2（11 键冻结面）**：删除 Assumptions 中 `_checkpointer` / `_store` 的私有字段示例；
  plan A1 改为「仅 3 个私有字段 + 8 个公开实例属性，不另存私有副本」。
- **INC-3（静态断点归属）**：统一为「入口接受 `None` / `str` / `list`，`str` 原样透传；
  裸非 `"*"` 字符串由 `GraphSpec` 归一在 `compile()` 调用点抛 `TypeError`（逐字同款）」。
- **INC-4（`transformers` 命名）**：新增 **X-12**（freegraph `transformers` ↔ 上游
  `stream_transformers`）；修正 E-31 不含 `transformers` 的引证。偏离计数 **11 → 12**。
- **INC-5（D-2 交接）**：明确 B8F1 从 `compiled._conditional_edges` 读取并填入
  `GraphSpec.conditional_edges`，路由求值只消费 L2 字段。
- **INC-6（SC-007）**：逐字同款限定为元素级与裸字符串；容器形态只要求同为 `TypeError`。
- **COV-1（C-07/C-08）**：标注为防御性检查，覆盖以正向用例为准；T023 同步。
- **COV-2（README 文档）**：T043 补「checkpointer 的行为归 B14F1」文本。
- **INC-7（data-model）**：修正 §9 的 V 编号与 §6 的校验顺序。
- **UND-1 / INC-8 / INC-9 / COV-3**：修正多源 `START` 的 Edge Case、plan↔tasks 映射、
  「删除 vs 替换」措辞、SC-010 追溯行与 T053 门禁清单。
- **宪法**：本轮**无需修改**（未发现 MUST 红线违规；X-12 为原则 XI 的命名形态 DIFF）。
