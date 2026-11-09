# Specification Quality Checklist: B5F1 · Channel 抽象 + `LastValue` + `BinaryOperatorAggregate` + `EphemeralValue`

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-08
**Feature**: [spec.md](../spec.md)

> **记注（与 B1F1 / B2F1 / B2F2 / B4F1 同例）**：本仓库的 spec 读者是**实现者**与**跨仓库接手方
> （freechain 开发者）**；凡「需求本体就是对外形状 / 数据契约」的 feature（契约层 · 门面 ·
> 本 feature 的通道操作面与语义口径），对「无实现细节」「面向非技术读者」两项做**有据豁免** ——
> 豁免范围**仅限契约形状**，不含「如何实现」。

## Content Quality

- [x] CHK001 No implementation details (languages, frameworks, APIs) — **豁免通过（记注）**：本 feature 的需求本体
  就是**通道的操作面与语义口径**（4 个冻结操作 + 三类通道的归约 / 覆盖 / 清空规则），
  与 B1F1 / B2F1 / B2F2 / B4F1 同例。已核对：spec 未指定模块划分、**类内部实现**、测试框架、
  序列化库、CI 配置；FR-002 只冻结**操作的名字与语义**（跨 feature 契约），实现形态由 plan 定；
  FR-006 的「剥离 / 映射 / 构造」三步是**判据**（与上游等价）而非实现手段；SC-015 只要求覆盖率数值与
  取证方式（MUST NOT 把覆盖率工具写进依赖声明）。
- [x] CHK002 Focused on user value and business needs — 通过：4 个用户故事均以「谁 + 为何」表述
  （P1 计数型 key 被覆盖 / P2 消息型 key 累积追加 / P3 路由结果不跨轮残留 /
  P4 状态语义只有一处实现点），每个故事先讲「要达成什么」，再给可判定的技术口径。
- [x] CHK003 Written for non-technical stakeholders — **豁免通过（记注）**：「二元归约器」「空值推导」
  「归约型通道自始有值」无法用非技术语言表述；但每个故事都先讲用户视角的结果
  （「`llm_calls` 真的是计数」「消息不会被冲掉」「上一轮的选择不会污染本轮」「改一处而不是改三处」），
  再给技术判据。
- [x] CHK004 All mandatory sections completed — 通过：User Scenarios & Testing / Requirements /
  Success Criteria 齐备；另含「澄清与裁定」（**4 轮澄清 Q1–Q15 + 17 条裁定 + 6 条引文差异说明**）、
  需求 ↔ SC **追溯表**、Key Entities（11 项）、Out of Scope（**12 条**）、Assumptions（**14 条**）、
  依据（9 组）；FR / SC 编号**连续无跳号**（FR-001…FR-027 · SC-001…SC-028 · 升序）。

## Requirement Completeness

- [x] CHK005 No [NEEDS CLARIFICATION] markers remain — 通过：**4 轮澄清（Q1–Q15）**已逐条选定并回填正文
  （第一轮 Q1 批量写入 + 冲突显式报错 / Q2 上游等价的空值与首次写入 / Q3 判定 + 抛错；
  第二轮 Q4 名字面全冻结 / Q5 `update()` 返回值 = 本次写了值 / Q6 A1 折叠起点 = 初始空值起折 /
  Q7 错误结构化字段 = `key`+`received_count`+`expected_count` / Q8 补可判定的规模口径；
  第三轮 Q9 初始状态按类型分三档 / Q10 只允许调度层写 + 不承诺线程安全 / Q11 浅引用不复制 /
  Q12 构造期用内置异常失败 / Q13 补落独立验收脚本；第四轮 Q14 覆盖率判据只管本 feature 新增代码 /
  Q15「持有」口径写死 + 规模探针写死 + 纳入参数化组合测试）+ **17 条裁定** + **6 条引文差异说明**
  已回填正文，正文**无未闭合标记**（实测 `grep -c 'NEEDS CLARIFICATION' spec.md` == 0）。
- [x] CHK006 Requirements are testable and unambiguous — 通过：FR-001…FR-021 全部「MUST + 可判定动作」；
  排他性表述消除了歧义（「**一次** `update` 调用中收到**多于一个**值」「空序列 MUST 是无操作」
  「初始值 = 该空实例（且通道自始『有值』）」「值类型不可实例化 ⇒ 直存新值、归约器调用次数 == 0」
  「MUST NOT 返回 `None` 冒充有值」「映射 MUST 保序」「每个 key MUST 恰产出一个通道」）；
  FR-002 以表格冻结 4 个操作的**名字 + 语义 + 返回值 + 无值行为** + **构造签名 + 属性名**
  （澄清轮 Q4）；FR-006 以三步冻结空值推导 + ④「空值每次构造新建独立实例」；
  FR-007 冻结首次写入的两条分支；FR-012 冻结两个映射入口名；FR-017 以表格冻结错误的结构化字段；
  FR-002 的 📌 口径块冻结 `update()` 返回值 = 「本次写了值」（Q5）。
- [x] CHK007 Success criteria are measurable — 通过：SC-001…SC-028 均含可数判据
  （命中率 == 100% / 次数 == 0 / 一致率 == 100% / 正确率 == 100% / 覆盖率 == 100% /
  边数 == 0 / 新增行数 == 0 / 缺失项数 == 0），并含**负向**判据（静默取末值次数 == 0 ·
  「无值」与「值为 `None`」混判次数 == 0 · 通道值被改变次数 == 0 · 持有多余引用的通道数 == 0）。
- [x] CHK008 Success criteria are technology-agnostic (no implementation details) — **部分豁免（记注）**：
  SC-005 的「`sys.modules` 快照」「层注册表 / import 图」、SC-015 的「行 / 分支覆盖率」、
  SC-002 的「`operator.add` 逐次归约」是本项目**宪法红线**（原则 I / II / ARCH-1）与
  **A1 判据**本身的唯一可判定口径，无法技术无关化；其余 SC 均以「对外可观察的结果」表述
  （读取结果 == 末值 / 归约结果逐元素相等 / 清空后判定为无值 / 映射正确率 / 捕获成功率）。
- [x] CHK009 All acceptance scenarios are defined — 通过：4 个用户故事共 **16 条** Given/When/Then 场景
  （US1 4 条 / US2 4 条 / US3 4 条 / US4 4 条），每条独立可测，且覆盖正向、冲突与失败路径。
- [x] CHK010 Edge cases are identified — 通过：Edge Cases 段 **25 条**（写入 `None` 仍是「有值」/
  一步内两值冲突 / 空写入序列 / **值类型不可实例化** / **抽象容器映射** / **typing 包装剥离** /
  归约器抛错 / 归约器非二元（通道不校验）/ 归约器返回 `None` / 归约器有状态 /
  同一归约器被两个 key 共用 / **两个同类型通道的空值必须互相独立** / **归约型通道被清空后停在无值** /
  连续清空两次 / 清空后再写入 / 路由通道一步内两值 / key 为空串 / 通道不感知运行期 /
  **绕过通道直接改状态** / **两线程同时写** / **用户就地修改写入的对象** /
  **写入不可拷贝对象** / **构造时传入不可调用的归约器** / **构造时传入非二元归约器** /
  上游版本漂移）。
- [x] CHK011 Scope is clearly bounded — 通过：Out of Scope **12 条** + FR-018；明确排除稀疏读取（B5F2）/
  调度循环（B7F1）/ `StateGraph` 构建器（B6F1）/ checkpoint 与通道复制（B14F1）/ 其它通道类型 /
  `add_messages` / `Overwrite` 旁路 / 通道注解形态 / 节点入参组装 / 兼容矩阵新增行 / CI 挂载 /
  第三方依赖引入。
- [x] CHK012 Dependencies and assumptions identified — 通过：Assumptions **14 条**（权威顺序 / 规模参考 /
  spec 目录命名与偏离记录 / 分支 / Python 基线与 typing 上限 / 内核零第三方依赖 + `langgraph` 仅本机参考 /
  上游行号引用纪律 / 代码落位 / 通道类命名已冻结 / 值的类型校验不做 / 既有冻结面零改动 /
  人工验证记录五段式 / 覆盖率取证不进依赖 / 前置 B4F1 与后续 B5F2 → B7F1 → B8F1）
  + 前置依赖（**B4F1**）+ 后续解锁链。

## Feature Readiness

- [x] CHK013 All functional requirements have clear acceptance criteria — 通过：spec 内含「需求 ↔ 成功标准
  追溯表」，**FR-001…FR-021** 逐条映射 SC 与 **A1–A3** 判据，无空缺；每条 FR 至少挂 **1** 条 SC
  （SC-016 ← FR-008 为唯一「只挂一条」的条目，已在追溯表反向覆盖注记中点明）。
- [x] CHK014 User scenarios cover primary flows — 通过：主流程（覆盖语义 / 归约语义 / 路由清空 /
  语义收敛）全覆盖，且每条可独立验收（US1 只做覆盖型通道即成立）。
- [x] CHK015 Feature meets measurable outcomes defined in Success Criteria — 通过：
  **A1** ↔ SC-002 / SC-007 / SC-016 · **A2** ↔ SC-001 / SC-006 · **A3** ↔ SC-003 / SC-006，
  逐条对齐且均为可数判据。
- [x] CHK016 No implementation details leak into specification — **豁免通过（记注）**：同 CHK001 ——
  需求本体即**操作面与语义口径**；已核对无库选型、无测试实现细节、无 CI 配置、无模块内部实现规定。

## Notes

- **本次校验迭代**：4 轮（初稿 → 自检 → 修正 → 复检；+ 澄清轮 Q1–Q3；+ `/speckit.clarify` 轮 Q4–Q8；
  + 第二轮 `/speckit.clarify` 轮 Q9–Q13）。计数已核对
  （**27 FR / 28 SC / 4 故事 / 16 场景 / 25 Edge Cases / 12 Out of Scope / 14 Assumptions /
  17 条裁定 + 15 条澄清问答（Q1–Q15 · 四轮）+ 6 条引文差异说明**）。
- **记注 1（CHK001 / CHK003 / CHK016）**：本仓库「对外形状 / 数据契约」类 spec 必须逐字写死字段与判据，
  属项目惯例（B1F1 / B2F1 / B2F2 / B4F1 同例）⇒ 对三项做**有据豁免**；豁免范围仅限「契约形状」，
  不含「如何实现」。
- **记注 2（CHK008）**：SC-002 / SC-005 / SC-011 / SC-015 的口径直接引用宪法红线与 A1 判据，
  非实现细节。
- **记注 3（澄清轮 Q1–Q3）**：就 spec 中 3 处会实质影响实现 / 验收的模糊点提问，发起者**逐条选定推荐项**
  （Q1 = A 批量写入 + 冲突显式报错 · Q2 = A 上游等价的空值与首次写入 · Q3 = A 判定 + 抛错），
  已全部回填正文（每条含候选、理由与落点，正文无未闭合标记）：
  **Q1** 写入接口 = 接收「本步写入序列」，`LastValue` / `EphemeralValue` 一步内多值 ⇒
  `InvalidChannelUpdateError`（新增 L2 错误类型）· **Q2** BinOp 空值 = 按类型推导（可实例化 ⇒ 自始有值；
  不可实例化 ⇒ 初始无值 + 首次直存不调归约器）· **Q3** 「有值 / 无值」= `is_available()` 布尔判定 +
  `get()` 抛 `EmptyChannelError`（「值为 `None`」≠「无值」）。
  **修订面**：新增 **裁定 1–14** + **引文差异说明 6 条**；FR-002（4 个操作冻结为表格）·
  FR-004 / FR-006 / FR-007 / FR-008 / FR-009 / FR-010 / FR-011 / FR-017（新增）· FR-020 / FR-021（新增）；
  SC-001…SC-018（18 条，含覆盖率与可替换性两条新增口径）。
- **记注 4（未闭合项）**：**无**。全部歧义点已在「澄清与裁定」段留痕并回填正文，
  正文无 `[NEEDS CLARIFICATION]` 标记（实测 `grep -c 'NEEDS CLARIFICATION' spec.md` == 0）。
  > **📌 修复记录（2026-11-08 · 第三轮澄清）**：本条曾因脚本替换误操作被**删除**，
  > 已按原意补回（内容不变）。
- **记注 5（偏离登记 · 目录命名）**：`.specify/init-options.json` 的 `feature_numbering: sequential`
  通用算法在本仓库**未被使用**（既有 5 个 spec 目录均无数字前缀，且以 feature ID 为键，
  与 `harness/features/` / `harness/verification/` 对齐）⇒ 本 feature 沿用既有约定
  `specs/b5f1-channels`，**显式偏离记录**于 Assumptions 第 3 条。
- **记注 6（证据取样 · 本会话实测）**：上游行号（`langgraph 1.2.11` · CPython 3.12.3）已在「依据」节
  逐条给出 —— `last_value.py:56-67`（一步内多值报错）· `binop.py:83-92`（空值推导）·
  `binop.py:126-128`（首次写入直存）· `ephemeral_value.py:55-60`（步末清空）·
  `pregel/_algo.py:317-320` / `:326-334`（批量写入 / `update(空序列)` 清空）·
  `pregel/_io.py:38-53`（C4 靠捕获 `EmptyChannelError` 实现）·
  `graph/state.py:1850-1873`（`_get_channel` 的映射规则）。
  Q2 的口径另有**实测依据**：Q8 契约 C4 行的「`NODE_INPUT_KEYS: ['messages']`」
  ⇒ BinOp 通道自始「有值」（空列表）、LastValue 通道自始「无值」。
- **记注 7（机制差异登记 · 非语义差异）**：上游靠「对本步未更新的通道调用 `update(空序列)`」让
  `EphemeralValue` 清空（`pregel/_algo.py:326-334`）；freegraph 改为**显式 `clear()`**（裁定 6）
  ⇒ **可观察语义等价**（值同样不跨步残留），**机制不同** ⇒ 登记为差异项，
  **不进兼容矩阵**（本 feature 零新增公开 API）。
- **记注 8（自检中收敛的两处）**：① FR-007 与 FR-006 曾有「初始空值」与「首次写入」的口径重叠
  ⇒ 拆为「推导空值」（FR-006）与「首次写入的 `current`」（FR-007）两条互斥职责；
  ② FR-019 的「覆盖率 100%」原表述可能被读作「要求 CI 装覆盖率工具」⇒ 补「取证在开发期完成 +
  MUST NOT 把覆盖率工具写进仓库依赖声明」（v1.0 依赖面为零）。
- 标记 `[x]` 表示该项「需求质量」已被复核满足，不表示实现工作已完成。
- **记注 9（`/speckit.clarify` 轮 · Q4–Q8 · 2026-11-08）**：就 spec 中**又一批**会实质影响
  下游 feature 与验收判据的模糊点提问，发起者**逐条选定推荐项**（Q4=A · Q5=A · Q6=A · Q7=A · Q8=A），
  已全部回填正文（每条含问题 / 候选 / 理由 / 落点，正文无未闭合标记）：
  **Q4** 下游可依赖的契约冻结范围 = **全冻结**（构造签名 + 属性名 + 映射入口名，落在 L2 内部 API，
  公开面零变更）· **Q5** `update()` 返回值 = 「**本次调用写了值**」（非空写入序列恒真，
  哪怕归约后值相等；与上游 `last_value.py:67` / `binop.py:144` 及 `pregel/_algo.py:319-324` 的
  「本步是否更新过通道」信号同构）· **Q6** A1 的折叠基准 = **从通道初始值（空值）起折**
  （与 `binop.py:143` 的 `operator(current, new)` 同构）· **Q7** 写入冲突错误的结构化字段 =
  `key` + `received_count` + `expected_count`（恒为 1），且错误对象 **NOT** 携带用户写入的值；
  `EmptyChannelError` **只**继承 `FreegraphError`（不继承 `ValueError`）·
  **Q8** 补**可判定的规模口径**（通道 NOT 持有其它通道 / 状态表引用 + 用**计数探针**而非墙钟耗时
  断言单通道操作不随 key 数增长）。
  **修订面**：FR-002（新增「构造签名与属性名」冻结表 + 📌 `update()` 返回值口径块）·
  FR-006 ④（空值每次构造新建独立实例）· FR-012（新增「映射入口」冻结）· FR-013 ①②（规模口径）·
  FR-017（结构化字段表 + 继承关系写死）· SC-002（📌 折叠起点说明）· SC-007（空值独立实例）·
  SC-009 / SC-018（收紧）；**新增 SC-019 / SC-020 / SC-021 / SC-022**（名字面一致率 /
  `update()` 返回值口径 / A1 折叠基准 / 规模口径）；Key Entities「通道（抽象）」补构造签名与属性名；
  Edge Cases **+1 条**（两个同类型通道的空值必须互相独立）；澄清记录 **+5 条**（Q4–Q8）；
  追溯表 FR-002 / FR-005 / FR-012 / FR-013 / FR-017 行更新 + 反向覆盖注记扩到 SC-022。
  **16 项清单状态无变化（16/16）**，追溯表 **21 FR ↔ 22 SC** 全覆盖。
- **记注 10（自查修正 · 与 Q2 口径直接相关）**：初稿的 FR-006 只写了「空值按类型推导」，
  **未写**「空值必须是每次构造新建的独立实例」⇒ 两个同类型归约型通道会**共享同一个空列表**
  ⇒ 一个通道的归约结果污染另一个（正确性缺陷）⇒ 已补 **FR-006 ④** + Edge Cases 1 条 +
  SC-007 追加断言（共享次数 == 0）。
- **记注 11（编号连续性 · 两轮澄清的编号修正）**：澄清轮新增的 SC 曾出现编号跳号
  （SC-023 落位在 SC-009 之后）⇒ 已重排为**连续无跳号**且升序；第三轮新增的 FR 曾被插在
  FR-021 之前（锚点固定在 FR-021 行）⇒ 已把 **FR-021 整块移回 FR-020 与 FR-022 之间**，
  现为 **FR-001…FR-027 / SC-001…SC-028 连续且升序**。
- **记注 13（`/speckit.analyze` 轮 · Q14–Q15 · 2026-11-09）**：对 **spec / plan / tasks** 三件套做
  **对齐性分析**（立项书 §4.2·§5.2·§5.3 + 宪法 v1.7.0 + 上游 `langgraph 1.2.11` 逐条核对）⇒
  **0 CRITICAL · 2 HIGH · 6 MEDIUM · 6 LOW**；发起者**逐条选定推荐项**并**要求全部修复**
  （不留到 implement）⇒ 落点如下：
  **Q14**（覆盖率判据范围）= **只管本 feature 新增/修改的代码**（`channel.py` / `mapping.py` 全文 +
  `errors.py` / `__init__.py` 新增部分）行/分支 == 100%；**整包**覆盖率**记录但不阻断**
  （实测依据：B4F1 **从未设过**覆盖率判据、无 100% 基线）⇒ spec **FR-019 ② / SC-015**、
  plan Constraints 表、tasks **T036**、quickstart §8 ③ 同步；
  **Q15** = ①「持有」写死为**两个**信号（公开 `property` 集合 + 实例槽位集合）⇒ spec **FR-013 ① / SC-009**、
  tasks **T029**、contracts **I-1**、data-model **I-1**；
  ② 规模探针**逐字冻结** = `len(gc.get_referents(ch))`（MUST NOT 用墙钟耗时 / 数行）⇒ spec **SC-022 ③**、
  contracts **I-2**、data-model **I-2**；
  ③ 立项书 **S5 ③**「属性 / 参数化测试：枚举 reducer 类型 × 通道组合」**纳入 B5F1**
  ⇒ 新增 spec **FR-027 / SC-028** + tasks **T031** + research **D-16** + plan Constraints 表。
  其余 MEDIUM / LOW（tasks 五个测试模块 · `value` 无值行为 · 抽象基类不可实例化 · `[P]` 与 TDD 顺序 ·
  P-01…P-11 措辞 · 附录行序 · quickstart 探针数值 · SC-005 导入模块 · `__init__.py` docstring 清单 ·
  「清空 ≠ 初始状态」的五处重复收敛）**同批修复**。
  **修订面**：spec（FR-013 ① / FR-019 ② / SC-005 / SC-009 / SC-015 / SC-022 ③ + **新增 FR-027 / SC-028**
  + 裁定 15/16 + 澄清 Q14/Q15 + 追溯表 + 计数）· plan（Constraints 表 + 两处计数）·
  research（**新增 D-16**）· tasks（**T031 新增** + 编号顺延 T031→T046 + 5 处内容修复 +
  附录重排 + 计数）· contracts（I-1 / I-2 / I-12）· data-model（I-1 / I-2 / I-12）·
  quickstart（§7 期望值 + §8 ③ 双数字口径）· 本清单（计数 + 本记注）。
  **16 项清单状态无变化（16/16）**，追溯表 **27 FR ↔ 28 SC** 全覆盖。
- **记注 14（`/speckit.analyze` 轮 · 第二轮 · 2026-11-09）**：对 **spec / plan / tasks** 三件套做
  **第二轮对齐性分析**（并**逐条实测复核**：上游 `langgraph 1.2.11` 的源码行为 · CPython 3.12.3 的
  `gc` / `__slots__` / `property` 语义 · `coverage 7.17.2` 的 report/json 输出形态）⇒
  **0 CRITICAL · 5 HIGH · 8 MEDIUM · 7 LOW**（共 20 项）。
  **发起者授权直接修改文件修复**（无 CRITICAL ⇒ 不必另开 `/speckit.clarify` 会话）⇒ **本轮全部落地**。
  **五个 HIGH（均属「可判定性 / 上游等价」的补齐，无一改变交付面或语义方向）**：
  **H1** `LastValue.clear()` 的语义与 spec 的四处「清空后一律为无值」**互斥**（contract §3.1 写
  「无操作 ⇒ 值不变」）⇒ 按 contract 自身的「冲突时以 spec 为准」规则**回修 contract**，
  三类通道**统一**为「`clear()` ⇒ 无值」（spec **裁定 17 ①** · FR-009 重写 · contract §1 / §2.2 /
  §3.1 / §3.2 / §3.3 / I-12 · data-model §2.1–2.4 / §3.1–3.3）；
  **H2** **上游实测**：上游**没有** `clear()`（`channels/base.py` 的 `BaseChannel` 无该方法），
  步末重置靠 `update(EMPTY_SEQ)`，而**三类通道反应各不相同** —— 覆盖型 / 归约型 **no-op**（值保留）
  · 路由型清空 ⇒ **等价落点是「步末调用哪些通道」**（不是「clear() 的语义」）⇒ 步末**只**清路由型
  落 **B7F1**（contract §7 `B-2` + upstream-parity **P-12 / S-05** + research **DR-6**）；
  **H3** `type(ch).__dict__` 的 `property` 集合取到的是**空集**（属性在基类上）⇒ 断言 MUST 沿 **MRO**
  收集（tasks T029）；**H4** 子类未声明 `__slots__` ⇒ 实例自带 `__dict__`、实测可写任意属性
  ⇒ 子类 **MUST** 声明 `__slots__ = ()`（spec FR-013 ① + contract I-1 + data-model I-1 +
  tasks T012 / T019 / T024）；**H5** 计数探针对「持有状态表」**不敏感**（实测 N=1 与 N=1000 计数**同为 6**）
  ⇒ SC-022 ① 补**引用类型白名单**为主判据、计数**降为辅助**（spec SC-022 ①③ + contract I-2 +
  data-model I-2 + tasks T029 + quickstart §7）。
  **八个 MEDIUM**：SC-022 残留重复段删除（spec）· FR-013 子项**重编号**①②③（spec + plan +
  data-model + research 引用同步）· tasks 附录**反向表按正向表重生成**（9 处失配 ⇒ 28/28 逐条一致）·
  「归约器调用次数 == 0」**限定单值写入**（spec FR-007 ② / SC-007 / 裁定 4 + contract §3.2 / I-10 +
  data-model I-10 + tasks T015）· FR-012 ② 返回类型 `Mapping` ⇒ **`dict`**（可变 · 下游要增补内部通道）·
  contract §6 **补 I-4 / I-5**（T035 的「逐条比对 I-1…I-23」原本取不到这两条）· tasks
  「**四个**测试模块」⇒ **五个**（tasks 3 处 + plan 1 处）· FR-013 ① 补 MRO 收集口径与「子类不引入新槽」。
  **七个 LOW**：research §1 标题 D-01…D-15 ⇒ **D-17** · §0.2 / D-12 的「引用数 = 4」标注为
  **原型值**（判据是「相等」而非某数字）· 补 `harness/verification/README.md` 索引任务（T045 ·
  沿用 B4F1 T059 形态）· 澄清轮次记法统一 · T043 补门禁**执行前置**（G22 需网络 / G28 需
  `unshare` ⇒ 按 CI 分组配方）· T035 范围补 **FR-027** · FR-006 ① 澄清「剥离**仅**在推导内部」。
  **覆盖率取证的三条纪律**（裁定 17 ⑤ · 实测 `coverage 7.17.2`）：**分支覆盖 MUST 以 `--branch` 取证**
  （实测：无 `--branch` 时 `coverage report` **不输出 Branch 列** ⇒ 分支覆盖**无从判定**）·
  文件级 report **无法**区分「既有行」与「新增行」⇒ 「新增部分」MUST 走**差分口径**
  （`git diff -U0` 的新增行号 ∩ `coverage json` 的 `executed_lines` / `executed_branches`）·
  spec **FR-019 ②** + tasks **T036** + quickstart **§8 ③** 同步。
  **修订面**：spec（**新增裁定 17** · FR-002 · FR-006 ① · FR-007 ② · **FR-009 重写** · FR-012 ② ·
  FR-013 ① · FR-019 ② · SC-004 ③ · SC-007 · SC-022 ①③ · SC-023 ④ · Edge Cases +1 条 ·
  引文差异说明 ③ · 澄清轮次记法）· contracts（§1 · §2.2 · §3.1 · §3.2 · §3.3 · §4 ·
  §6 I-1/I-2/**I-4**/**I-5**/I-10/I-12 · §7 `B-2`）· upstream-parity（**新增 P-12 / S-05** ·
  §1 计数 · §4 复现命令）· data-model（§2.1–2.5 · §3.1–3.3 · §4 I-1/I-2/I-10/I-12）·
  research（**新增 §0.3 实测证据块** · **新增 D-17** · §1 标题 · §2 **新增 DR-6** · §3 小结表）·
  tasks（T007 · T010 · T012 · T015 · T017 · T019 · T024 · T029 · T035 · T036 · T043 · T045 ·
  Path Conventions · Phase 1 Purpose · **附录反向表重生成**）· plan（Constraints 表 · 复杂度表 ·
  两处计数）· quickstart（§7 · §8 ③ · §9 ②）· 本清单（计数 + 本记注）。
  **16 项清单状态无变化（16/16）**，追溯表 **27 FR ↔ 28 SC** 全覆盖，tasks **46** 条 · FR **27/27** ·
  SC **28/28**（反向表与正向表**逐条一致**）。
- **记注 12（第二轮 `/speckit.clarify` · Q9–Q13 · 2026-11-08）**：发起者反馈「spec 仍有很多不确定
  的地方」⇒ 再问 5 处，发起者**逐条选定推荐项**（Q9=A · Q10=A · Q11=A · Q12=A · Q13=A），
  已全部回填正文：**Q9** 三类通道的**初始状态**按类型分三档写死（覆盖型 / 路由型 = 无值；
  归约型 = 空值·有值，类型不可实例化时才是无值）—— **本条同时收敛一处现存的口径冲突**
  （SC-004 原写「从未写入 ⇒ 无值」，与 FR-006「归约型自始有值」矛盾）；
  **Q10** 通道写入**只允许调度层发起** + **不承诺线程安全**（不引入同步原语）；
  **Q11** 通道**浅引用**用户对象（不复制 / 不转换 / 不校验类型）；
  **Q12** 构造期**当场失败**且用**内置** `TypeError` / `ValueError`（**不新增** L2 错误类型；
  不重做 B4F1 的二元性校验）；**Q13** 补落**独立验收脚本**
  `harness/verification/B5F1/acceptance.py`（零依赖 · 一条命令跑完 · `--record` 出五段式）。
  **修订面**：**新增 FR-022…FR-026**（初始状态 / 写入权限与并发 / 值的引用语义 /
  构造期校验 / 独立验收脚本）· **新增 SC-023…SC-027** · SC-004（口径修正：分覆盖型 / 归约型两档
  + 清空终态）· Edge Cases **+7 条**（25 条）· 澄清记录 **+5 条**（Q9–Q13 · 累计 13 条）；
  追溯表新增 FR-022…FR-026 五行 + FR-011 行扩列 · 反向覆盖注记扩到 SC-027。
  **16 项清单状态无变化（16/16）**，追溯表 **27 FR ↔ 28 SC** 全覆盖。
