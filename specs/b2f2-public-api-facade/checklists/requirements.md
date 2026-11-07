# Specification Quality Checklist: B2F2 · 公开 API 门面 `freegraph/graph.py` + API 签名快照

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-07
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] CHK001 No implementation details (languages, frameworks, APIs) — **豁免通过（记注）**：本 feature 的需求本体**就是公开形状**（导出符号清单 + 完整调用签名 + 快照文本格式），与 B1F1 / B2F1 同例（不逐字写死形状，「契约冻结 / 签名冻结」即名不副实）。已核对：spec 未指定序列化库、测试框架、CI 配置、模块命名等实现手段；FR-006 只约束「门面内零类体 / 零函数体」这条**可机械判定**的边界，模块落位留给 plan（见 Assumptions 第 1 条）。
- [x] CHK002 Focused on user value and business needs — 通过：4 个用户故事均以「谁 + 为何」表述（P1 验收基准 import 成立 / P2 形状不漂移 / P3 单一可信入口 / P4 契约层可单独消费），每个故事都先讲要达成的结果，再给可判定的技术口径。
- [x] CHK003 Written for non-technical stakeholders — **豁免通过（记注）**：本仓库 spec 的读者是实现者与**跨仓库接手方（freechain 开发者）**；公开 API 的符号名与签名无法用非技术语言表述。已核对：每个用户故事都先讲「要达成什么」，再给技术判据。
- [x] CHK004 All mandatory sections completed — 通过：User Scenarios & Testing / Requirements / Success Criteria 齐备；另含 Clarifications（**12 条裁定 + 12 条澄清问答（Q1–Q12）**）、需求↔SC 追溯表、Key Entities、Out of Scope、Assumptions（**14 条**）、依据。

## Requirement Completeness

- [x] CHK005 No [NEEDS CLARIFICATION] markers remain — 通过：**9 条裁定**（导出面边界 / `Send`·`interrupt` 的类型面落点与契约层 18 符号面不变 / 门面零实现体的机械判据 / `StateGraph` 参数名 = `schema` / 三个构建方法链式返回 / `compile` 两关键字 keyword-only / `invoke` 不属本冻结面 / 快照落位与可复现 / 兼容矩阵补 5 行）+ **8 条澄清问答 Q1–Q8**（导出面判定口径 / 未接线异常类型 / 快照是否含类型注解 / 快照更新入口 / 兼容矩阵等价程度填法 / 快照是否记公开属性 / `Send`·`interrupt` 参数与可变性 / 三个 plan 级小项）**+ 4 条分析轮决策 Q9–Q12**（门面的层归属与 ARCH-1 合规 / 参数名冻结口径 / 署名头门禁覆盖缺口 / 快照测试「CI」措辞）**+ 3 条分析轮裁定 10–12**（唯一维护点的分工明确化 / `Send` 的可哈希性 / 导入开销预算入 spec）已回填正文，正文无未闭合标记。
- [x] CHK006 Requirements are testable and unambiguous — 通过：FR-001…FR-019 全部为「MUST + 可判定动作」；排他性表述（「恰 7 个」「集合相等」「== 0」「逐字节相同」）消除了歧义；FR-002 / FR-008 / FR-010 给出逐项可断言的清单。
- [x] CHK007 Success criteria are measurable — 通过：SC-001…SC-018 均含可数判据（退出码 0 / 集合相等 / 语句数 == 0 / 差异行数 ≥ 1 / 逐字节相同 / 子模块数 == 0 / 无来源项数 == 0 / 墙钟 < 120 ms）。
- [x] CHK008 Success criteria are technology-agnostic (no implementation details) — **部分豁免（记注）**：SC-004 / SC-009 的「AST 扫描」「`sys.modules` 快照」是本项目**宪法红线**（原则 I / II / ARCH-2）的唯一可判定口径，无法技术无关化；其余 SC 均以「对外可观察的结果」表述。
- [x] CHK009 All acceptance scenarios are defined — 通过：4 个用户故事共 16 条 Given/When/Then 场景，每条 ≥3 条且各自独立可测。
- [x] CHK010 Edge cases are identified — 通过：Edge Cases 段 **17 条**（门面只有导出没有实现 / 未接线必须显式失败 / 多传位置参数 / `alias` 位置传入 / `path_map` 双形态 / `compile()` 无参 / `interrupt` 无运行上下文 / `Send` 未接线时可构造 / 快照含内存地址导致 flaky / 禁止静默自动更新快照 / 多导出符号 / 顶层包被顺手 re-export / 门面误依赖 L4-L5 / 门面误读环境变量 / 上游版本漂移 / `graph_core.py` 用例全红是预期 / `target.py` 被改动）。
- [x] CHK011 Scope is clearly bounded — 通过：Out of Scope **12 条** + FR-018；明确排除构建能力（B6F1）/ `compile` 行为（B7F2）/ `invoke` 行为（B7F3）/ 可视化（B22F1·B23F1）/ `Send`·`interrupt`·`Command` 行为（B11F1·B10F1·B9F1）/ 别名行为（B8F3）/ `recursion_limit`（B13F1）/ 契约层 18 符号面 / 顶层包 re-export / 完整兼容矩阵（B24F1）/ CI 挂载（B3F1）。
- [x] CHK012 Dependencies and assumptions identified — 通过：Assumptions **14 条**（模块落位 / 契约层不变 / `Send`·`interrupt` 最小形状 / `StateGraph` 外壳最小形状 / `alias` keyword-only / 异常类型 / `invoke` 不进快照 / 上游核实环境与行号 / 快照生成方式 / 兼容矩阵载体 / 顶层包现状 / CI 归 B3F1 / freechain 复用为未来事项 / 3.11 与零依赖）+ 前置依赖（B1F1、B2F1）+ 后续解锁（B3F1 → M1 全部 feature）。

## Feature Readiness

- [x] CHK013 All functional requirements have clear acceptance criteria — 通过：spec 内含「需求 ↔ 成功标准 追溯表」，FR-001…FR-019 逐条映射 SC 与 A1–A3 判据，无空缺。
- [x] CHK014 User scenarios cover primary flows — 通过：主流程（验收基准 import / 形状冻结 / 单一入口 / 顶层包惰性）全覆盖，且每条可独立验收。
- [x] CHK015 Feature meets measurable outcomes defined in Success Criteria — 通过：A1↔SC-001/002/004、A2↔SC-005/006/012、A3↔SC-007 逐条对齐。
- [x] CHK016 No implementation details leak into specification — **豁免通过（记注）**：同 CHK001 —— 公开 API 的**形状**是需求本身；已核对无库选型、无测试实现细节、无 CI 配置、无模块命名规定。

## Notes

- **本次校验迭代**：3 轮（初稿 → 自检 → 修正 → 复检；+ 2026-11-07 澄清轮 Q1–Q8；+ 2026-11-07 分析轮 Q9–Q12 与裁定 10–12）。计数已核对（**19 FR / 18 SC / 4 故事 / 16 场景 / 17 Edge Cases / 12 Out of Scope / 14 Assumptions / 12 条裁定 + 12 条澄清问答**）。
- **记注 1（CHK001 / CHK003 / CHK016）**：本仓库的「公开 API 形状」类 spec 必须逐字写死符号与签名，属项目惯例（B1F1 / B2F1 同例），故对「无实现细节」「面向非技术读者」两项做**有据豁免**；豁免范围仅限「契约形状」，不含「如何实现」。
- **记注 2（CHK008）**：SC-004 / SC-009 的依赖口径直接引用宪法红线，非实现细节。
- **记注 3（裁定 2 与 B2F1 冻结记录的关系）**：B2F1 `public-api.md` §5 第 14 条「`Send` / `interrupt` 的导出 → v2」指的是**契约层**的 18 符号面；本 feature 新增的是**门面**导出面。二者不冲突，契约层 `__all__` 仍恰为 18（SC-015 为其判据）。
- **记注 4（裁定 9 与提示词 §8 的关系）**：提示词说「不建立完整矩阵内容（B24F1 落终版）」；本 spec 据宪法原则 X 补入**本层 5 行**（B2F1 已就其 10 行立过同例），全库定稿仍归 B24F1 —— 二者不冲突。
- **记注 5（未闭合项）**：**无**。全部歧义点已在 Clarifications 段留痕并回填正文，正文无 `[NEEDS CLARIFICATION]` 标记。
- **记注 6（2026-11-07 澄清轮 · Q1–Q5）**：`/speckit.clarify` 就 5 处「判定口径 / 冻结粒度」提问并全部回填：
  Q1 导出面判定口径 = **`__all__` 集合相等 且 模块内公开名集合相等**（两处都断言，堵死「导出了但没进 `__all__`」的漏洞）·
  Q2 未接线时抛**内置 `NotImplementedError`**（零新增公开错误类型，与 Q1 的「公开名恰 7 个」不打架）·
  Q3 快照**全冻**参数注解与返回注解（PEP 484 意义上的完整签名，注解按规范化文本记录）·
  Q4 快照提供**显式的人工更新入口**（默认跑测试绝不改文件，更新后须 review diff）·
  Q5 兼容矩阵 5 行按**当前实现状态**如实标注等价程度（`StateGraph` / `Send` / `interrupt` = 部分等价；`START` / `END` = 行为等价）。
  落点：FR-002 / FR-009 / FR-010 / FR-011 / FR-012 + SC-003 / SC-005 / SC-011 / SC-012 + Assumptions 3 条 + Edge Cases 2 条。
  **16 项清单状态无变化（16/16 仍全部通过）**——澄清只把口径写死，未新增需求缺口。
- **记注 7（2026-11-07 封口轮 · Q6–Q8）**：Q1–Q5 之后经复查发现 3 处 spec **完全未提**的缺口
  （`property` / `positional` / `不可变` 三关键词实测零命中），发起人选择「按推荐值直接写进 spec」
  而不再开新一轮提问，故记为 Q6–Q8：Q6 快照**必须记录公开属性 / property**（否则 B6F1 新增
  `schema` 之类属性会悄悄漂过快照，与 Q3「全冻」自相矛盾）·
  Q7 `Send` / `interrupt` 参数**位置或关键字皆可**（镜像上游）+ `Send` **冻结为不可变**
  （上游可变，差异入兼容矩阵）· Q8 三个 plan 级小项写死（快照 **UTF-8 / LF / 末行换行**、
  人工验证记录用**五段式**且第 3 节贴真实输出、B2F1 `public-api.md` §5 加一行指向本快照）。
  落点：FR-005 / FR-010 / FR-012 ④ / FR-015 + **新增 SC-017** + Assumptions 1 条 + 澄清记录 3 条。
  **16 项清单状态仍无变化（16/16）**，追溯表 19 FR ↔ 18 SC 全覆盖（2026-11-07 分析轮后）。
- **记注 8（2026-11-07 `/speckit.analyze` 三件套交叉核对 · 12 项发现）**：spec / plan / tasks 逐条对照，
  另读 `harness/proposals/立项书.md` §4.3 / §5.1 / §9.1 与仓库既有消费者（`harness/demo/` 4 个脚本）。
  **1 CRITICAL / 3 HIGH / 5 MEDIUM / 3 LOW**，已按发起者答复**全部落地**：
  ① **A1（CRITICAL · 架构）**：门面的导出面横跨 L1–L3，而 B2F2 原归 L1 ⇒ 接线后违反 ARCH-1
     ⇒ **门面的「层」改记为跨层单元（层 =「—」）**并作为 ARCH-1 唯一例外（立项书 §5.1 例外条款
     + §5.2 的 B2F2 行已由**发起者**修订；spec Key Entities · plan 架构纪律核对 · facade-api 层归属块同步）；
  ② **A2（HIGH）**：plan 增设「**架构纪律核对（ARCH-1 / ARCH-2 / ARCH-3 / ARCH-4）**」小节
     （此前只核了宪法原则 I–X，未核立项书的架构纪律）；
  ③ **B1（HIGH）**：参数名冻结口径澄清为「**宪法原则 III 优先**」，立项书 §4.3 义务列引用的是
     **上游**参数名（不冲突，差异已在兼容矩阵登记）→ 裁定 4 与 facade-api §2 各补一段说明；
  ④ **C1（HIGH）**：既有 **G5** 的扫描清单是**硬编码元组** ⇒ 本 feature 新建文件无署名头判据
     ⇒ **门面侧另立门禁 G20**（**不改** `tests/contracts/**`，保住「既有门禁零改动」纪律）；
     代价（署名头判据分两处维护）已登记；
  ⑤ **C2（C3）**：子进程辅助补 `PYTHONPATH` 注入与临时 cwd（否则门禁假红）；快照自检扩到
     「新增公开属性」一例（Q6 的口径原本无自检护栏）；
  ⑥ **D1（MEDIUM · 证据）**：导出面「恰 7 个」获**仓库内 5 个消费者**独立印证
     （`graph_core.py:48-56` / `acceptance.py:51-58` 恰 7 个；`agent_loop.py:33-39` /
     `visualization.py:36-40` / `target.py:122` 为子集），取值另由 `acceptance.py:195-205` 断言
     ⇒ 补入 FR-015 与裁定 1；
  ⑦ **A3（B2 · E1 · C4 · C5）**：`Send` 的 ARCH-3 判定显式登记 · 「CI 常驻」措辞统一
     （**经复核为原措辞误判**，SC-005 原本就写「随全量测试执行」）· 快照规则去重
     （`data-model.md` §1.2 改为 ID 索引）· 补 SC-016 的断言 · 隔离 venv 复用。
  **修订面**：冻结面的**内容一字未动**（导出面 7 个符号 / 签名 / `START`·`END` 取值均不变）；
  **宪法无需修订**（宪法不含分层条款，分层纪律在立项书）。**任务数 44 → 45**（新增 G20）。
- 标记 `[x]` 表示该项「需求质量」已被复核满足，不表示实现工作已完成。
- 记注 9（2026-11-07 第二轮 `/speckit.analyze` 交叉核对 · 25 项发现）：spec / plan / tasks /
  四份契约 / research / quickstart / README 逐条对照，**2 CRITICAL / 4 HIGH / 13 MEDIUM / 6 LOW**，
  **已全部落地**（冻结面的**内容**除「`Send` 不可哈希」与「导入开销预算」两条**新增**外，
  其余**一字未动**）：
  ① **U-1（CRITICAL · 门禁判据）**：G17 的第三方档写作「任何非标准库顶层包」⇒ 会把门面
     **必需**的 `freegraph.contracts` import 判为违规 ⇒ 改为**两档制**（research **D-22**）；
  ② **U-2（CRITICAL · 快照格式）**：dataclass 属性的**缺省值取数口径缺失** ⇒ 增
     **D-21-1…D-21-4**（`contracts/snapshot-format.md` §1.1）；
  ③ **I-1**：「唯一维护点」的互斥表述 ⇒ 明确「清单 = 唯一**手写**权威 / 快照 = 唯一**入库比对点**」
     （裁定 10）；④ **I-2**：`Send` 的「不可哈希」写入 **FR-005 ① / SC-017**（裁定 11）；
  ⑤ **I-3**：快照自检**增强到真实比对路径**（research **D-23**）；
  ⑥ **G-1**：SC-013 的「无来源项数 == 0」落到人工记录第 4 节的**来源覆盖表**；
  ⑦ **G-2**：导入开销预算升格为 **FR-019 / SC-018**（裁定 12，含唯一计时口径）；
  ⑧ 其余 MEDIUM / LOW：门禁条数 6→7（4 处）、澄清计数 8→12（5 份文档 + 4 条新落点）、
     G5 / G20 重叠与 §3 分工表、G1 与 G18② 的重复声明、`tasks.md` US2 的「CI」措辞、
     plan / research 的文件清单过时、D-04 与 N-1…N-6 的口径澄清、README 版本口径注、
     **45 条任务逐条补 FR/SC 追溯表**（宪法原则 VI；**第二轮追加 T046 后为 46 条**）、
     data-model R-4 措辞、
     SC-016 断言前移至 T015 等。
  **第二轮（2026-11-07 · 分析轮）追加修复**：① spec 的「快照 = 唯一手工维护点」与
  **裁定 10 / FR-010 ④** 的互斥表述；② plan 的「B2F1 `public-api.md` **逐字不动**」与
  **FR-010 ④ / T038** 的冲突；③ **FR-008「链式返回自身」与 FR-009 / SC-011 的互斥**
  （改为「返回注解 MUST 为 `Self`」）；④ **SC-005 的三种「故意改动」漏了「注解改动」一例**
  （T022 / research D-23 补为三例）；⑤ **G17 内部档的「层段」定义自相矛盾** +
  禁止范围严于 FR-014 ④（会在 B6F1 / B10F1 / B11F1 接线后假红）⇒ 统一为只禁 L4 / L5；
  ⑥ **G1「作用域扩展」是空操作**（既有实现口径已是 `freegraph.*` 全量）⇒ 改述并与
  「既有门禁零改动」对齐；⑦ 导入开销阈值钉环境 + 重测基线（154 ms → 50–63 ms）+ 收紧为
  **120 ms**；⑧ 补 `harness/verification/B2F2/acceptance.py`（**T046**）；
  ⑨ G15 集合相等段补自检；⑩ `README` 版本口径注已预先更新 ⇒ T032 改为「只需确认」。
  **宪法无需修订**（本轮发现仍为**制品层**问题，宪法条款本身无缺陷）。
  **16 项清单状态仍无变化（16/16）**，追溯表 19 FR ↔ 18 SC 全覆盖（**46 条任务**）。
