# Specification Quality Checklist: B3F1 · 项目脚手架 + extras 划分 + CI 门禁

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-07
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] CHK001 No implementation details (languages, frameworks, APIs)
  - **判定**：本 feature 的**主题本身**是工程设施（门禁 / 脚手架），「不写实现细节」的通用要求在此**降级为「不锁定实现手段，只锁定可判定结果」**。
  - **证据**：spec 只写**可判定的结果**（依赖闭包为空集 · 框架出站数 == 0 · 矩阵最低档 == 3.11 · 门禁失败须含规则编号）；把**实现手段的选择权**显式下放给 plan（FR-019「门禁的实现落点……具体文件划分由 plan 决定」）。
    - **⚠️ 一处已过期的下放项（2026-11-08 分析轮订正）**：原文此处引用的「FR-004 ②『具体渲染后端属 plan 级决策』」**已被宪法 v1.5.0 取代**——`[png]` 的后端**已由宪法收敛为确切包名 `playwright`**（原「mermaid 相关」这一**类别式**表述不可判定）⇒ plan 阶段的职责**由「选型」收窄为「核验」**（许可证标识 ∈ 白名单 + 运行期零出站）· FR-004 ② 已同步改写。
  - **例外说明**：spec 中出现的 `pyproject.toml` / `py.typed` / `socket` / `ast` / `sys.modules` 等**是本 feature 的判定对象本身**（被检物的形状即需求），不是「实现方案的选择」——这是 B1F1 / B2F1 / B2F2 已确立的同例口径。
- [x] CHK002 Focused on user value and business needs
  - **证据**：4 条 User Story 全部以「作为**谁**、我希望能**什么**」写成（P1 发起者 · P2 用户 · P3 内网用户 · P4 发起者），并各自给出**可独立验收**的判据。
- [x] CHK003 Written for non-technical stakeholders
  - **判定**：**部分通过（已知偏差）**。本仓库的 spec 是**工程规格**（读者 = 实施者与评审者），非商业文档。
  - **缓解**：所有「技术断言」都配了**业务侧等价表述**（如 FR-005「依赖闭包干净」= P3「基础安装只装一个包」；FR-009 ②「框架出站 = 0」= P2「freegraph 自己不偷偷联网」）；「为什么」段落（Why this priority）说明了业务价值。
- [x] CHK004 All mandatory sections completed
  - **证据**：User Scenarios & Testing · Edge Cases · Requirements · Key Entities · Success Criteria · Assumptions —— **全部存在且无占位符残留**（模板注释块已删除）。
  - **附加**：仓库惯例的「澄清与裁定」节（**25 条裁定 + 13 条澄清问答**，附权威依据与取舍）置于正文之前 —— 与 B2F2 spec 的体例一致。

## Requirement Completeness

- [x] CHK005 No [NEEDS CLARIFICATION] markers remain
  - **判定**：**0 个残留**。
  - **说明**：引文的 3 处规范冲突（`>=3.10` vs `>=3.11` · 矩阵最低档 · 矩阵最高档 3.13 vs 3.14）**未**用澄清标记，而是按仓库已确立的**权威顺序**（宪法 > 立项书 > 提示词初稿 > 仓库现状，`harness/features/README.md`「冲突处理」条 + 宪法 Governance）**裁定闭合** —— 每条裁定均给出**上位的、可追溯的**依据（宪法条款名 + 修订记录版本 + 立项书章节行号），**存在合理默认**，不满足澄清标记的启用条件。
  - **留痕**：裁定 3（最高档 3.13 vs 3.14）标注了「**若发起者另有偏好，改这一处即可**（不牵动任何其它条款）」—— 属**低成本可翻转**，故不占澄清额度。
- [x] CHK006 Requirements are testable and unambiguous
  - **证据**：**21 条 FR**（FR-001 ~ FR-020 + FR-021）全部用 **MUST / MUST NOT** 表述，且每条都带**可判定的量**（== 0 / 为空集 / == 100% / 恰好 / 逐字 / 逐个指名）。
  - **关键歧义已消解**：① 「无 `langchain*`」→ FR-005 ① 明确含**子包与 provider 包**；② 「许可证白名单」→ FR-006 ③ 明确**规范化 + 双来源 + 取不到即失败**（FR-006 ②）；③ 「导入图单向」→ FR-008 ② 明确**可机读注册表**而非路径猜测；④ 「零出站」→ 裁定 7 + FR-009 ② 明确**只包装哪两个入口 + 放行全部连接 + 按调用栈归因 + 只对框架出站断言**；⑤ 「只观测不阻断」→ FR-009 ③ 明确 freegraph **不得安装任何拦截机制**。
- [x] CHK007 Success criteria are measurable
  - **证据**：**SC-001 ~ SC-016**（含子项 SC-002b / SC-002c · SC-003 ①②）全部含量化判据（闭包为空集 · 出站数 == 0 · 最低档 == 3.11 · 通过率 == 100% · 覆盖率 == 100% · 失败率 == 100% · `git status` 干净比例 == 100%）。
- [x] CHK008 Success criteria are technology-agnostic (no implementation details)
  - **判定**：**部分通过（已知偏差 · 与 CHK001 同源）**。SC 中的「隔离 venv」/「socket 监测夹具」/「Python 版本档」是**被判定对象的形态**，在本 feature 中即需求本身。
  - **缓解**：所有 SC 都以**结果**表述而非工具表述（「依赖闭包为空集」而非「`pip freeze` 输出为空」；「框架出站条目数 == 0」而非「未调用 `socket.connect`」）。
- [x] CHK009 All acceptance scenarios are defined
  - **证据**：4 条 User Story 共 **11 条**验收场景（Given / When / Then 齐备），每条 User Story 另有**独立验收方式**（Independent Test）。
- [x] CHK010 Edge cases are identified
  - **证据**：**13 条**边界场景，覆盖：extras 变体的间接引入 · 许可证明取不到 · 许可证表达式规范化 · ELv2 点名 · 门禁自读环境变量 · OTLP exporter 例外 · socket 归因误判 · 断网下的本地回环 · Windows 路径语义 · 负向验证污染工作树 · 既有门禁硬编码清单的缺口。
- [x] CHK011 Scope is clearly bounded
  - **证据**：① Assumptions 末条逐条保留引文 §8 的 **5 项「不做」**；② FR-011 ② / FR-012 ① 明确**挂载点 ≠ 已落地**（MUST NOT 伪装成「已通过」）；③ 引文 §7 的「发布流水线接入」明确归后续 feature（裁定前的差异说明已注明 `check_dist_purity.py` 与 `publish.yml` **已存在**）。
- [x] CHK012 Dependencies and assumptions identified
  - **证据**：Assumptions 覆盖权威顺序 · 核心用例定义 · 隔离环境语义 · extras 变体枚举 · 平台范围 · 落点选择 · 既有门禁处置 · 不做清单 · 规模参考；裁定 3 / 5 / 6 / 7 / 9 / 10 / 11 均附**上位依据**。

## Feature Readiness

- [x] CHK013 All functional requirements have clear acceptance criteria
  - **证据**：FR-001 ~ FR-021 **逐条**映射到 SC-001 ~ SC-016 或引文 §6 的验收判据 A1–A5（映射见 spec 正文与 plan 的追溯表）。
  - **覆盖抽查**：FR-001/002/003/004 → SC-002 · FR-005/006/007 → SC-001/SC-002c · FR-008 → SC-002b · FR-009/010 → SC-004/SC-006 · FR-011/012 → SC-003 · FR-013 → SC-008 · FR-014 → SC-001/SC-009/SC-010 · FR-015/016/017 → SC-002b/SC-002c/SC-007 · FR-018 → SC-007 · FR-019 → SC-003。
- [x] CHK014 User scenarios cover primary flows
  - **证据**：主流程 = 「破坏红线 → 被拦住」（P1）·「自身不联网 → 可判定」（P2）·「基础安装够轻 → 可判定」（P3）·「历史 feature 补检 → 不留暗坑」（P4）—— **四个主流程全覆盖**，且 P1–P3 与引文 §3 的 P1–P3 **一一对应**（P4 为引文 §10 末段「人工复核 M0 三者」的可验收化）。
- [x] CHK015 Feature meets measurable outcomes defined in Success Criteria
  - **证据**：引文 §6 的 **A1–A5 五条验收判据全部映射**（A1 → SC-001；A2 → SC-002；A3 → SC-006；A4 → SC-002b/SC-002c；A5 → SC-008），且每条都有判定方式。
- [x] CHK016 No implementation details leak into specification
  - **判定**：**部分通过（已知偏差 · 与 CHK001 / CHK008 同源）**。
  - **说明**：泄漏的「实现细节」仅限 **被判定对象的形状**（`Requires-Dist` / `sys.modules` / 层编号 L1–L6 / 许可证标识符 / 环境变量前缀 / socket 入口）—— 这些是**红线本身的定义**，删掉它们则需求不可判定。
  - **已明确下放 plan 的**：门禁脚本的文件划分 · `[png]` 的渲染后端 · 门禁检查的具体语言形态。

## Notes

- **判定摘要**：**16 / 16 项通过**（其中 CHK003 / CHK008 / CHK016 标注为「部分通过 · 已知偏差」，偏差原因与缓解措施已逐条写明，**均属本 feature 主题（工程设施门禁）的固有属性**，非疏漏）。
- **未闭合项**：**无**。0 个 `[NEEDS CLARIFICATION]` 残留。
- **澄清会话（`/speckit.clarify` · 2026-11-07 · 5 题全闭合）**：
  1. **署名头扫描域** → 全仓所有受版本控制的 `.py`（`src/` + `tests/` + `harness/`），例外仅 `py.typed` 与 `harness/demo/target.py`；本 feature 需为存量缺头文件补头。**（2026-11-07 分析轮复核修正：原答「10 个」已作废 —— 实测全仓 37 个 `.py` 中 35 个已合规（9 个把头放在 shebang 之后）⇒ 真正缺头的只有 **1 个** —— `harness/scripts/audit_feature_drafts.py`）**。
  2. **兼容矩阵判定语义** → 分层：已入库的 `README.md` 矩阵章节**严格阻断**，尚未建立的 `COMPAT.md` **只报告不阻断**；API 快照**严格阻断**。
  3. **反向用例强制范围** → **8 条强制**（G21–G26 / G29 / G30）；G27 零出站动态与 G28 断网以「正向断言 + 人工取证」覆盖。
  4. **CI 矩阵档位** → 3 OS × {3.11, 3.14} x86_64 **+ Linux arm64 最低档** = **7** 作业。
  5. **断网任务的核心用例** → **全量测试套件**，显式排除「断网任务自身」与「必须能建立连接」的用例，排除清单**可机读且逐条有理由**。
  → 落点：裁定 5（改写）· 裁定 13–16（新增）· FR-010 ③④⑤ · FR-012 ②③④ · FR-013 ④⑤ · FR-014 ②①②③ · FR-015 ④①②③ · SC-004 / SC-008 / SC-009 / SC-011 / SC-012。
- **澄清会话（`/speckit.clarify` · 2026-11-07 · **第 2 轮** · 4 题全闭合）**：
  1. **许可证明的读取来源** → **四级有序证据链**：`License-Expression`（PEP 639）→ `License` 字段 → `License ::` 分类器 → `dist-info/licenses/` 授权文件原文；取到即止，四者皆无才判失败。**实测依据**：`pydantic` 2.13.4 仅声明 `License-Expression: MIT`（其余皆空）⇒ 漏掉第 1 条会把合规包判死。
  2. **白名单的匹配口径** → **严格精确匹配** 5 个 SPDX 标识符；变体（`MIT-CMU` / `MIT-0` / `HPND`）**一律不放行**；MUST NOT 引入等价对照表 / 家族判定 / 豁免入口；无可行后端的 extra **如实登记为延后**。**实测依据**：`Pillow` 的标识为 `HPND`。
  3. **「框架出站」的归因判据** → **第一个非标准库帧**规则（跳过标准库帧后遇到的第一个自写帧在 `freegraph/` 内 ⇒ 框架出站）；四种栈形态 MUST 全判对；归因函数 MUST 有**合成调用栈**的单元断言。
  4. **「门禁生效」是否包含合并拦截** → **必须包含**：仓库 MUST 启用**分支保护**并把 CI 设为 **required check**；执行方为**发起者**（实测本机无 `gh`、无令牌）⇒ 交付**可照抄的设置步骤**；未启用前标为「未完成」。
  → 落点：裁定 17–20（新增）· FR-006 ①①①–③ / ③④①–④ · FR-009 ②①–④ · FR-020 ①–⑤ · SC-006 / SC-013 / SC-014 / SC-015 · Edge Cases（+2 条）· Key Entities（+1 条）· Assumptions（+1 条）。
- **已知取舍（登记待 plan 消解）**：
  1. 裁定 3（CI 矩阵最高档 = 3.14）—— 依据为立项书 §3.5 的两处**专门矩阵行** + 已入库的 `pyproject.toml` classifiers；引文写 3.13、立项书同表「Python 上限」行写 3.13。**已于 2026-11-07 澄清会话确认取 3.14**（不再是开放项）。
  2. CHK003 / CHK008 / CHK016 的「非技术读者 / 无实现细节」偏差 —— 属**体例性偏差**（工程规格），已用业务侧等价表述缓解。
  3. 门禁编号 **G21–G30** 的**具体归属**（哪条门禁落在哪个文件、哪条判据放在测试侧还是脚本侧）由 plan 决定；spec 只冻结**编号连续性**与**判据内容**。
  4. **`[png]` extra 的具体渲染后端** —— 由 plan 决定（MUST 在 plan 阶段核验许可证标识；PSF 系绘图库 / Apache-2.0 系浏览器渲染方案为候选，**不锁定包名**）。
  5. **分支保护的执行** —— 属**仓库设置**，本环境**无 `gh` CLI、无 GitHub 令牌**（已实测）⇒ 只能由**发起者**执行；本 feature 交付「设置步骤 + 验收闭环」。
- **下一阶段**：`/speckit.clarify` 已于 2026-11-07 完成**四轮**（共 13 题，全部闭合）；下一步 = **`/speckit.plan`**（`plan.md` / `tasks.md` / `research.md` / 4 份契约 **已产出**）· **本轮分析（`/speckit.analyze`）已把三件的阻断项修完**。
- **澄清会话（`/speckit.clarify` · 2026-11-07 · **第 3 轮** · 2 题全闭合 · 本轮修订）**：① **既有门禁 G3 的占位填充** → 裁定 8 增补**唯一一处具名例外**（只填 `CONSTITUTION_DEPENDENCY_WHITELIST` 的 **12 个确切包名** + extras 变体枚举语义，**判据句与许可证取值方式逐字不动** ⇒ **净效果变严**；**须发起者追认后方可合入** · `tasks.md` **T049** 阻断合入）；② **`[otel]` 的内容** → 取**宪法依赖白名单原文所列**的 `opentelemetry-api` + `opentelemetry-sdk`（**MUST NOT** 含任何 OTLP exporter —— 其闭包含 `certifi`(**MPL-2.0**) ⇒ 必然被 **G23** 拒；exporter 的合规解法**归 B21F1**，本轮只登记三条方向）。**FR / SC 的编号与条数不变**（**该轮当时的口径**：20 FR / 17 SC）；新增裁定 **21**（累计 21 条裁定 · 11 条澄清问答记录）。
  → 落点：裁定 8（改写）· 裁定 21（新增）· FR-001（改写）· FR-004（改写）· FR-004 ③（改写）· FR-016 ②（改写）· 裁定 6（补落点）· Assumptions（既有门禁的处置）· 引文差异说明第 ④ 条（新增）。
- **澄清会话（`/speckit.clarify` · 2026-11-07 · **第 4 轮** · 2 题全闭合 · 本轮修订）**：① **FR-005 ③ 的「运行期」一半不可执行** → **拆分交付**：B3F1 只交付 **③①（声明级 + 导入级）**，**③②（运行期 · 最小图）延后至 M2**（实测：`StateGraph` 的四个方法一律 `raise NotImplementedError` ⇒ M0 地基无内核运行时 ⇒ 硬写即 CI 永久红 · 违反 PR-4）⇒ **红线不放宽**（③① 已是可判定形式）· **不引入豁免机制**（FR-018）· **不改宪法** · **不新增门禁编号**；② **延后项的承接机制 + 里程碑口径订正** → **承接条款写进目标 feature 的提示词初稿**（`harness/features/B6F1|B7F2|B7F3` 的 §9/§10）⇒ 该 feature 的 spec 落成 **FR + 裁定**（**红线本身**在 立项书 §9.2 断言②③ **常驻登记**，不因延后而注销）；**并订正** 里程碑为 **M2**、`invoke` 归 **B7F3**（分析轮的「M1 承接」经 立项书 §6.2 复核为笔误 —— B6F1 / B7F2 / B7F3 属 `M2 图定义与对外 API`；下游 `tasks.md` / `plan.md` / `contracts/` / `quickstart.md` 的同源措辞**已全量同步**）。**FR / SC 的编号与条数不变**（**该轮当时的口径**：20 FR / 17 SC）；新增裁定 **22**（累计 **22 条裁定 · 13 条澄清问答记录**）。
  → 落点：裁定 22（新增 · 含承接路径 + 里程碑口径更正）· FR-005 ③（拆为 ③①②）· FR-011 ②（C4 → M1 / C8 → M2）· 裁定 6（补落点）· SC-006 ① · Assumptions（+2 条）· Key Entities（验收环境 · 补分阶段指针）· `tasks.md` T043 ③ 与追溯表 · `plan.md` R-4 / R-5 · `contracts/architecture-gates.md` G22 场景② 与 G29 ② · `quickstart.md` §G29 期望输出 · `harness/features/B6F1|B7F2|B7F3` 的 §9/§10 承接条款。
- **分析轮（`/speckit.analyze` · 2026-11-07 · 三件对齐审查）**：发现 **4 项阻断实施**的问题并已修复 ——
  ① **CI 不装 extras** ⇒ G23 取不到许可证据（要么必红、要么退化为空门禁 · **违宪**）、G21 闭包走不到末端、G3 的 12 名白名单永不触达 ⇒ Linux 全量作业**必须加装四个 extras 的依赖**（**实测**：闭包**恰好 12 个包**，与 T003 白名单逐一命中）；② **仓库无开发期依赖声明** ⇒ CI 的 `pytest` 与 G23 的 `packaging` 装不上 ⇒ `pyproject.toml` 增 `[dependency-groups] dev`（PEP 735 · **不进发行包 / 不进 `Requires-Dist`** · 实测 `Requires-Dist = None`）；③ **署名头补法与断言口径错** ⇒ T004「只加首行」+ T028「断言首行逐字相等」与宪法原则 X 冲突 ⇒ 改为「**首行或 shebang 之后**」；④ **tasks 内部过期任务号 4 处**（追认任务 = **T049**）。
  另修正：extras 变体数 **5 → 6**（4 处）· 兼容矩阵行数口径 **18 ∪ 7 = 23 行** · FR-010 ② 回环措辞 · `--self-test-negative` 退出码语义 · G27「**两个入口 · 同一实现**」· **署名头存量清单由「10 个」更正为「1 个」**（实测全仓 37 个 `.py` 中 35 个已合规 · 9 个把头放在 shebang 之后）。
  → 落点：spec.md（裁定 5 · FR-010 ② · FR-012 ② · FR-013 ⑤ · SC-008）· plan.md（**未改**）· tasks.md（T001 · T004 · T012 · T014 · T022 · T029 · T030 · T031 · T037 + 4 处任务号）· contracts/ci-matrix.md · contracts/architecture-gates.md · contracts/dependency-gate.md · data-model.md · quickstart.md §2.4 / §3.2 · pyproject.toml。
  → **FR / SC 的编号与条数**：本轮**新增** **FR-021**（第三方品牌资产 · 宪法原则 IX 第三条）与 **SC-016**（品牌资产合规的可测判据）⇒ **21 FR / 18 SC**；
     既有编号 **FR-001 ~ FR-020 / SC-001 ~ SC-015 全部不变**（新增项为**追加**，零漂移）· 任务数仍 **56**（T001–T056 · 无增删改号）。
  → **第三轮（`/speckit.analyze` · 2026-11-07 · 对齐审查 + 修复）**：发现并修复 **6 项阻断实施**的问题（**全部经实测复现**）——
  ① **G29 ② 的退出码判据在 CI 必失败**：退出码 2 仅走 `except ImportError` 分支，而 CI 步骤 5 已 `uv pip install -e .` ⇒ freegraph **可导入** ⇒ 三个脚本走到用例体、因 `NotImplementedError` 被记为**断言失败** ⇒ **退出码 1**（**实测**：freegraph 可导入时三者退出码**全为 1**）⇒ 原「∈ {0, 2}」⇒ **7/7 作业全红**（违反 PR-4）⇒ 改为 **{0, 1, 2}** + 按**失败来源**细分（1 且全部源于 `NotImplementedError` ⇒ 环境未就绪 ⇒ 绿）；
  ② **G21 的「未安装 ⇒ 判失败」与 CI 矩阵的非 Linux 子集互斥**：非 Linux 作业只装基础包 ⇒ `requires('pydantic')` 抛 `PackageNotFoundError`（**实测**）⇒ 按 G21 自身规则必红 ⇒ **四个 extras 的依赖改为全部 7 个作业都装**；
  ③ **CI 安装步骤缺 venv** ⇒ `uv pip install` 报 `No virtual environment found`（**退出码 2** · **实测**）⇒ 补 `uv venv --python <档位>` 步骤 + 全部 uv 命令用显式 `--python`；
  ④ **`packaging.licenses` 无叶子遍历 API**（**实测 24.2 / 25.0 / 26.3**：公开面只有 `canonicalize_license_expression` / `InvalidLicenseExpression` / `NormalizedLicenseExpression`，**无** `LicenseExpression` 类、**无**公开树 API）⇒ D-05 与 T011 的「MUST NOT 手工切分字符串」不可实施 ⇒ 改为「对**规范化输出**按空白分词、剔除 AND/OR/WITH/括号」（**实测** `'MIT AND PSF-2.0'` → `{MIT, PSF-2.0}`）；
  ⑤ **G30 的品牌资产断言缺 spec 依据**（spec.md 全文 **0 命中**）且口径过宽（「白名单为空 ⇒ 禁一切图像」比宪法原则 IX 第三条更宽）⇒ **新增顶层 FR-021 + SC-016**（自有资产走「已具名的自有品牌资产白名单」· 当前为空集）+ FR-018① 补该例外通道 + group D 标题补 IX；
  ⑥ **CLI 契约不完整 ⇒ 6 条强制反向用例不可执行**（G24/G25/G26/G30 无「被检树根」参数、G25 无「层注册表」参数、G29 的「入库基准」无载体）⇒ §2.1 补 `--root` / `--registry` / `--baseline`；
  另修正：**G3 的失配机制**（实际变红的是**白名单子集断言**，许可证断言实为 `pytest.skip`；`dnspython` 不在闭包内）· **T045 的 `Requires-Dist` 口径**（声明 extras 后 `requires()` 返回带 marker 的 5 个条目、**非 `None`**）· **T042 ② 的注入模块名**（`langchain-core` 只提供 `langchain_core`、不提供 `langchain` ⇒ MUST 注入 `langchain_core`）· **T014 的隔离副本缺 `README.md` / `LICENSE`**（`pyproject.toml` 硬引用 ⇒ 构建失败）· **裁定 3 的计票论证**（实际 3.14 ×2 / 3.13 ×3 ⇒ 「多数」不成立，成立的是**专精性规则**）· **裁定 22 的 M1 残留**（3 处 ⇒ M2）· **CI job 名绑定**（required check 按 job 名精确匹配 ⇒ MUST 逐字对齐 ci-matrix §4.1）。
  → 落点：spec.md（**裁定 23 / 24 / 25 新增** · FR-015 ⑤ 新增 · FR-021 新增 · FR-006 ⓪ 新增 · SC-016 新增 · FR-018 ① · group D 标题 · Key Entities · 裁定 3 / 裁定 8 / 裁定 22 · SC-006 ① · Assumptions）· plan.md（原则 IX 行 · R-4 · G3 失配描述 · extras 表 · Technical Context）· tasks.md（T001/T011/T014/T017–T021/T027/T028/T030/T031/T034/T037/T042/T045 + 追溯表 16 行 + 执行闸口 A1 + 并行约束）· contracts/architecture-gates.md（G21 注 · G29 判定 1/2 · G30 判定 1–6 · §2.1 · §3/§4）· contracts/ci-matrix.md（§1 子集 · §2 步骤 3.5–5.5 · §3.1/§3.2 · §4.1）· contracts/dependency-gate.md（§4.2）· quickstart.md（§0.1 · §4.3 · §6 · §6.1）。
  → **第二轮已清零的剩余项**：立项书 §5.5 两处同步（**§12 新增 D14**：exporter 移出 `[otel]` + `[png]` v1 即交付，两段式）+ B21F1 行与 §7.5 单点敏感性加注 + B23F1 提示词初稿同步 · tasks 头部计数（21 裁定 / 11 问答 / **8** 条不变量）· 人工验证记录统一为仓库既有 **五段式**（`harness/verification/README.md`）· SC-005 措辞 · plan 的 T-G3 → **T049** 与「7+ 个」→ **12 个** · Path Conventions 命名理由 · `Requires-Dist` 期望值（实测 `None`）· 合同层「未安装依赖 ⇒ 显式失败，不静默跳过」· research D-02 的「需追认」改为「已闭合」。
- **分析轮（`/speckit.analyze` · **2026-11-08** · 第二轮 · 对齐审查 + 修复 + 发起者裁决）**：本轮共 **17 项**发现，**全部已修复**（除 2 条已登记为「按已决处置执行」）——
  - **CRITICAL（1 项 · 已由发起者裁决关闭）**：宪法「质量门禁 3 / 4 / 5」在 M0 地基 **物理不可达成**（C4/C8 回归 · fake 模型轮 · 真实模型轮均需内核运行时）⇒ 原处置为「偏离登记 R-4 + T057 发起者追认」，但**宪法本身缺「分阶段落地 + 发起者追认」的通则** ⇒ **宪法已修订为 v1.6.0**，新增「**质量门禁的分阶段落地与发起者追认**」章节（窄口径适用范围 + 「偏离登记 + 发起者追认」双要件 + 四条红线 + 登记与复核）；**发起者 2026-11-08 裁决 = 接受逐 feature 追认**（T049 / T057 阻断合入 + 人工验证记录留证）；**宪法本身未削弱任何红线**（原则 I / II / IX 的红线 MUST 在每个 feature 落地）。
  - **HIGH（2 项 · 已修）**：① **跨层单元内部 import 无判定行** —— FR-008 正文「跨层单元只能 import L1 与更低层」按字面读 ⇒ 10 个门禁脚本 `import _gatekit` 即违规 ⇒ **G25 上线当天全红**（违反 PR-4）⇒ 新增 **FR-008 ④**（同一跨层单元内部不产生层边 + **模块定位口径**）· `layer-registry.md` §0.2 规则 3 · `data-model.md` §5.2 真值表 · `architecture-gates.md` G25 第 4 条 —— **四处逐字一致**；② **G23 的 `--root` 取证作用域未写死** ⇒ 假元数据不可见 ⇒ **反向用例空转** ⇒ G23 细则 + §2.1 CLI 表 + `tasks.md` T016 三处写死「`<root>/<name>-<version>.dist-info/METADATA` + 在该根目录下查 `*.dist-info`」。
  - **MEDIUM（8 项 · 已修）**：`acceptance.py` 的**第三份出站归因实现**（用**已被裁定 19 否决**的旧口径）登记为**已知判据重叠**（plan「已登记的判据重叠」表 + T048 / T027 ④ 的证据口径约束）· 隔离副本构造收敛为**共享函数** `_gatekit.make_isolated_copy()`（T008 / T014 / T029）· FR-017 措辞由「实现」改为「执行（既有 G9 · 只接线）」· 本清单的**计数订正**（21 FR / 18 SC / 24 裁定 / 13 问答 / 13 条 Edge Case / 57 任务）· T039 的排除清单条目**恰为 3 条**（去掉 **T043** —— 它是门禁脚本的创建任务、不是 pytest 用例）· G28 的**命名空间归属**（脚本 MUST NOT 自行 `unshare`）· `acceptance.py` 的退出码断言**归 B25F1** · 白名单复核的**双触发点**（版本约束变更 / CI 因闭包失配而红）**已决**：维持开区间。
  - **LOW（6 项 · 已修）**：SC-005 标注为「宪法发布门禁的派生判据 · 无独立 FR」· FR-010 ③(a) 补「本 feature 无 G28 的 pytest 用例 ⇒ 该类当前为空」· T031 措辞由「Linux 作业调 G21–G30 全部」改为「**步骤 7 = 7 条（三个平台逐字相同）+ 步骤 9 的 3 条（Linux only）= Linux 合计 10 条**」· quickstart §3.2 补「**先 `git add` 再跑 G30**」（`git ls-files` 只含受版本控制的文件）· Key Entities「门禁」补**三层术语消歧**（门禁编号 G* / 宪法质量门禁 1–7 / FR·SC）· `full_install` marker 无使用者（**保留为预留**，已说明，无需改动）。
  - **发起者裁决（3 项 · 按裁决执行）**：① 宪法偏离 → **接受逐 feature 追认**（宪法已升 v1.6.0 确立通则）；② `acceptance.py` 旧归因 → **登记为已知重叠，本 feature 不改**；③ 白名单版本敏感性 → **维持开区间 + 明确双触发复核**。
  → 落点：**宪法**（新增章节 + v1.6.0 修订记录 + 页脚）· `harness/prompts/init_constitution.md`（同批补入该章节）· spec.md（FR-008 ④ · FR-010 ③(a) · FR-017 · SC-005 · Key Entities）· plan.md（判据重叠表第二处 · 版本敏感性的双触发与已决）· tasks.md（T008 · T014 · T016 · T027 ④ · T029 · T031 · T038 · T039 · T048 · 落地顺序提示）· contracts/architecture-gates.md（G23 注 · G23 §2.1 CLI 行 · G25 第 4 条）· contracts/layer-registry.md §0.2 · data-model.md §5.2 · quickstart.md §3.2 · 本清单（计数订正）。
  → **FR / SC 的编号与条数不变**：**21 FR / 18 SC** · **任务数 57**（T001–T057 · 无增删改号）· 追溯表 **57/57** 行齐全。
  → **下一阶段**：**`/speckit.implement`**（三件已对齐 · 阻断项已清零；合入前仍须完成 **T049 / T057** 两条发起者追认）。
