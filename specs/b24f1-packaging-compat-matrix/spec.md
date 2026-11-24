# Feature Specification: B24F1 · 打包分发 + API 兼容矩阵 + `THIRD_PARTY_NOTICES`

**Feature Branch**: `b24f1-packaging-compat-matrix`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_specify` 钩子；既有 feature 同样在 `main` 上开发）

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: `harness/features/B24F1_打包分发与兼容矩阵.md` —— 交付**发行就绪**的产物：把 freegraph 打成可发布的 Python 包，产出 **API 兼容矩阵**与**第三方归属清单**，并把「**发行产物纯度门禁**」接进发布流水线。判定：**发行包就绪；兼容矩阵与归属清单齐备；发行产物纯度门禁通过**。

> **范围提醒**：本 feature 是**发行单元**（跨层 · 层 =「—」），**不新增运行时能力**。
> 它**只**做四件事：① 打包元数据与 extras 收口；② 把**已存在**的纯度断言脚本接入发布流水线并做负向验证；
> ③ 首次落库**独立权威文件 `COMPAT.md`**（兼容矩阵本身早已在 README 落库 · B2F2；含 18 项 + 契约条目 + 全部下游承接行）；④ 定稿 `THIRD_PARTY_NOTICES` 与 README。
> **MUST NOT** 修改 `src/freegraph/` 的任何运行时 / 契约 / 持久化 / 可观测语义；
> **MUST NOT** 新增门禁编号；除本 spec 已登记并获发起者追认的 B24F1 单符号（`Command`）纠漂移例外外，**MUST NOT** 放宽任何既有判据。
> **不实现** `target.py` 双跑验收与迁移说明（B25F1）、首次真实发布（占位版已发布）、Postgres / async / 子图 / 完整 Studio UI（v2）、
> LICENSE 的 MIT → Apache-2.0 切换（**D3 已决 2026-11-05：保持 MIT**）、免费文档站。

---

## 承接条款（上游 feature → 本 feature）

> 宪法 v1.8.0「跨 feature 承接的接线通则」：上游 feature 指名本 feature 的跨 feature 义务
> MUST 在本 spec 落成 **FR + 裁定**；**只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽判据**。

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B7F4 → B24F1** | **M4** | **多源汇合边**：兼容矩阵 MUST **新增一条**——上游 `add_edge([a, b], c)` ⇒ freegraph **支持**（L2 `GraphSpec` 元组键 · L3 `add_edge` 接线归 B6F1）。**导出面零新增 ≠ 兼容矩阵零变**（**B7F4 的**偏离登记 X-01 注记，**不是**本 spec 的 X-01）⇒ MUST NOT 漏记。 | `specs/b7f4-multisource-join/spec.md` 承接 **D-6** · 登记项 **PR-4 / PR-5** | FR-004 · FR-012 · 18 项覆盖 #4 · SC-004 |
| **H-2** | **B9F1 → B24F1** | **M4** | **`Command` / `NodeFunc` 两行的定稿口径**：MUST 保留 B9F1 对两行**差异说明**的事实性更新（「运行期语义已落地」·「命令列表」形态）⇒ **零新增行**、等价程度 **MUST 保持 B9F1 定稿值（`Command` = 部分等价 · `NodeFunc` = 不支持）**，**不得按 P3 漂移值回退**；**MUST NOT** 按旧措辞回退。 | `specs/b9f1-command-primitive/spec.md` 下游承接 **D-9** · **裁定 20 / 21** · FR-016 | FR-004 · FR-012 · SC-004 · Assumption A-2 |
| **H-3** | **B11F1 → B24F1** | **M4** | **`Send` / `Command` / `NodeFunc` 三行**：`Send` 运行期语义（fan-out）已落地 ⇒ 措辞 MUST 事实性更新（记录「运行期语义已落地」）；`Send` 类型定义现住 **L1**（`freegraph/contracts/types.py`，与 `Command` 同模块）MUST 注明；**`Send` 侧不可变（上游可变）MUST 在差异说明中保留**；`Command` 行删去过时的「`goto` 只能是节点名」；`NodeFunc` 行增补返回形态 `Send` / `list[Send]` / `tuple[Send, ...]`。 | `specs/b11f1-send-fanout/spec.md` 下游承接 **D-4** · 裁定 11 | FR-004 · FR-012 · SC-004 |
| **H-4** | **B13F1 → B24F1** | **M4** | **`compile` 行**：`interrupt_before` / `interrupt_after` 关键字与 `recursion_limit` 的 dict 载体 MUST 被记录为**已交付**；**零新增行**（仅事实性措辞更新）。 | `specs/b13f1-static-interrupt-recursion-limit/spec.md` 下游承接 **D-8** | FR-004 · FR-012 |
| **H-5** | **B14F1 → B24F1** | **M4** | **三行新增**：`freegraph.persistence.MemorySaver` / `InMemorySaver` / `CheckpointTuple`；`MemorySaver` 与 `InMemorySaver` 是**同一对象（别名）**；`CheckpointTuple` **恰好三个公开字段**。B14F1 自身只更新 `Checkpointer` 行，三行定稿归本 feature。 | `specs/b14f1-checkpointer-memory-saver/spec.md` 下游承接 **D-07** | FR-004 · FR-012 · SC-004 |
| **H-6** | **B15F1 → B24F1** | **M4** | **三行新增**：`freegraph.persistence.SqliteSaver` = **部分等价**（MIT 改编 · `json` 序列化差异 · X-07）；`CompiledGraph.get_state` = **部分等价**（无快照返回 `None` vs 上游空 `StateSnapshot` · B15F1 P-02 / X-01）；`CompiledGraph.get_state_history` = **行为等价**（排序 / `filter` / `before` / `limit` 对齐上游 · B15F1 P-04 / P-05，注明 B14F1 冻结差异）；人工验收 MUST 纳入发布前人工验收。 | `specs/b15f1-sqlite-saver-state-history/spec.md` 下游承接 **D-04** | FR-004 · FR-012 · FR-014 · SC-004 |
| **H-7** | **B16F1 → B24F1** | **M4** | **两行新增**：`CompiledGraph.update_state`（返回 `RunConfig` · `as_node` · **无 `task_id`**）与「**时间旅行重放 / 分叉**」行（`invoke(None, snapshot.config)` + `update_state` + `Command(resume)`）；人工验收 MUST 纳入发布前人工验收。 | `specs/b16f1-update-state-time-travel/spec.md` 下游承接 **D-01** | FR-004 · FR-012 · FR-014 · SC-004 |
| **H-8** | **B21F1 → B24F1** | **M4** | **打包 / extra / 兼容矩阵**：① 发行元数据**只允许** `[otlp]` 一个 extra；基础 `dependencies = []` 与零出站承诺不变；② 纯度门禁 MUST NOT 把 `[otlp]` 误判为「v1.0 不允许的 extra」；`[otlp]` 闭包 ⊆ 19 名白名单（含 `protobuf` 的具名 SPDX 归一）；③ 兼容矩阵 / README MUST 记录 OTLP 能力与三后端示例（OpenLIT / Langfuse / Phoenix，并列无默认推荐）；`OtlpExporter` 按「无上游对应 / 不支持（自由设计）」登记；④ `pip install "freegraph[otlp]"` MUST 可安装且不拉入 `certifi` / HTTP exporter / `opentelemetry-exporter-otlp` 元包；⑤ MUST NOT 回退 B21F1 的 `[otlp]`、G23 `protobuf` 归一、G26 / B19F1 import 例外。 | `specs/b21f1-otlp-export/spec.md` 形态锁定裁定 **§1 / §6** · `contracts/dependency-and-gate-contract.md` | FR-001 · FR-004 · FR-006 · FR-007 · FR-012 · FR-013 · FR-016 · FR-017 · SC-004 / SC-005 / SC-006 / SC-007 |
| **H-9** | **B23F1 → B24F1** | **M4** | **打包与 PNG 口径**：兼容矩阵 MUST 记录「**v1.0 PNG = 合法占位图（非真实图形渲染）**」与 v2.0 `[png]` 升级路径；`pyproject.toml` MUST **除 `[otlp]` 具名例外外**不含其它 `[project.optional-dependencies]`；基础安装闭包 MUST 仍为空集；B23F1 的 PNG 调用面（**零必需参数、返回 `bytes`**）MUST NOT 被破坏。 | `specs/b23f1-draw-mermaid-png-offline/spec.md` 下游承接 **D-3** · `contracts/png-contract.md` §9.1 | FR-001 · FR-004 · FR-012 · FR-018 · SC-004 / SC-005 |

---

## Clarifications

### Session 2026-11-24

- Q: `Command` 行的「等价程度」最终应如何定稿？ → A: **部分等价**（恢复 B9F1 定稿值；依据 = 上游 `Command().goto == ()` vs freegraph `None` · B9F1 parity 的 X-1 / X-4 更严失败信号 · X-2 / X-3 异常类型差异）⇒ 同时**纠正上游对齐批次 P3（commit `99d43aa`，2026-11-13）引入的「行为等价」漂移**（B22F1 的 `125ba0f` 仅追加泛型化措辞、未改第三列），并在矩阵差异说明中注明该纠正来源。
- Q: `Command.goto` 缺省 `()` vs `None` 应归入哪一类偏离？ → A: **单列为既有行为面差异 Y-01（DIFF，成功路径可观察差异）**，**不得**并入 X-06「更严的失败信号」。B24F1 **只登记、不改运行时**（`goto=None` 属 B1F1 冻结面；本 feature 的破冻结面追认已用于 G8/G19/G29，按「每 feature ≤1 次」不叠加）；**具名承接 = B25F1（M4）**（在双跑验收 / 迁移说明中保留该记录并提示 v1 行为），运行时对齐（若需）归 **v2 独立契约修订**；MUST 在 `manual-verification.md` 遗留问题中显式列出。
- Q: SC-008（人工验收记录）如何满足宪法 v1.13.0 的判据级覆盖？ → A: **新增自动文档守卫** `tests/runtime/test_b24f1_manual_record_guard.py`（T042），断言记录存在、五段式、正文非空、含必需实测输出，并核验 B25F1 提示词的「下游承接（B24F1）」小节；守卫 **MUST** 排在 T039 记录写就之后，**MUST NOT** 以写记录 / 审计任务冒充判据覆盖。
- Q: API 兼容矩阵的权威源放在哪里，README 与 `COMPAT.md` 如何分工？ → A: **`COMPAT.md` 为唯一权威**的逐符号 / 逐项矩阵；README **只保留**「能力 → freegraph 处置」表 + affiliation 声明 + 指向 `COMPAT.md` 的链接 / 摘要 ⇒ **MUST NOT** 在 README 维护第二份完整矩阵。
- Q: README 顶部「v0.0.x 占位版 · 内核尚未实现 · 没有任何图运行时能力」这段与现状不符的状态说明，B24F1 应如何处理？ → A: **B24F1 更新**为与当前已交付能力一致的状态说明：保留「占位版本」客观事实，**删除**「内核尚未实现 / 没有任何图运行时能力 / 请勿当作可用替代品」等过时断言；B25F1 只做最终文案润色。
- Q: `COMPAT.md` 的契约条目覆盖范围应多大？ → A: **全量迁入**现有 README 的公开符号矩阵（约 27 行）+ 18 项 + H-1…H-9 下游新增行；README 只保留能力处置表与指向 `COMPAT.md` 的链接 / 摘要。**MUST NOT** 只挑少量「关键契约条目」而丢失既有逐符号事实。
- Q: README 的「中文为主 + 英文并行」应做到什么深度？ → A: **中文为主 + 英文覆盖关键段落**（独立实现声明 / 三条承诺 / 安装与 `[otlp]` / 能力处置摘要 / 指向 `COMPAT.md` 的链接），**不要求**逐节全译；SC-007 按此口径判定。
- Q: G8 / G19 / G29 的取行源是否迁到 `COMPAT.md`？ → A: **是**（**选项 A · 2026-11-24**）：`COMPAT.md` 为唯一权威，README 只留能力表 + 链接；同步更新 G8 / G19 / G29 的取行源（`README → COMPAT.md`），并为 `Command` 恢复「部分等价」加 B24F1 例外。  **不新增门禁编号**；此项已登记为破冻结面并获发起者追认。**G19 的 `Command` 例外是单点定向例外**：
  仅允许 `Command` 发生唯一一次 `行为等价 → 部分等价` 的**纠漂移**；
  `Command` **不整体移出**「等价程度 MUST NOT 变差」单调检查，其它任何等级变化
  （含 `部分等价 → 不支持`）MUST 继续失败；其它行仍不可降级。
  **同批 MUST 迁移**其他 README 矩阵消费者（`tests/runtime/test_parse_contract.py`）；G19 的 baseline MUST 为 `HEAD:COMPAT.md` 优先、`HEAD:README.md` 回退（都无则 skip），**MUST NOT** 固定 `HEAD:README.md`。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 装上就能用，且基础安装没有第三方依赖 (Priority: P1)

作为用户，我在**隔离的干净环境**里执行 `pip install freegraph`，期望安装成功、
`import freegraph` 成功，且 `pip freeze` 里**没有**任何第三方运行时依赖
（只有 `freegraph` 自身与 `pip`）。

**Why this priority**: 「零第三方运行时依赖」是本项目最核心的产品承诺（宪法原则 I / IX），
也是发行包「就绪」的第一判定。没有它，其余发行产物都失去意义。

**Independent Test**: 新建隔离 venv → `pip install <wheel>` → `python -c "import freegraph"` →
`pip freeze` 与预期集合逐字比对；全程不访问网络（或使用本地产物）。

**Acceptance Scenarios**:

1. **Given** 一个全新的隔离 venv，**When** 安装本 feature 构建出的 wheel，**Then** 安装成功、`import freegraph` 成功。
2. **Given** 同一环境，**When** 执行 `pip freeze`，**Then** 除 `freegraph` 与 `pip`（及构建/安装器自身）外**没有任何包**。
3. **Given** 同一 wheel 的元数据，**When** 读取 `Requires-Dist`，**Then** 基础依赖为空；唯一可选依赖组是 `[otlp]`。
4. **Given** 已发布/待发布的 `pyproject.toml`，**When** 枚举 `[project.optional-dependencies]`，**Then** 只有 `otlp` 一个键，**没有** `pydantic` / `checkpoint` / `otel` / `png`。

---

### User Story 2 - 发行包里没有仓库杂物 (Priority: P1)

作为用户，我 `pip install freegraph` 之后，**不应该**在 site-packages / 安装文件清单里
看到 `harness/`、`.specify/`、`.opencode/`、`specs/`、调研报告或验收脚本这些
**开发辅助材料**。

**Why this priority**: 仓库内容一旦进入发行包就会被他人 `import` 引入，且 PyPI 版本
**发布后不可删除**（只能 yank）。这是不可逆事故，必须在发布前机械拦截。

**Independent Test**: 构建 wheel + sdist → 运行 `harness/scripts/check_dist_purity.py dist/` →
断言退出码 0；再逐个打开产物核对内容清单。

**Acceptance Scenarios**:

1. **Given** 构建产出的 wheel，**When** 列出其全部文件，**Then** 只含 `freegraph/` 包代码与 `freegraph-*.dist-info/` 元数据。
2. **Given** 构建产出的 sdist，**When** 列出其文件，**Then** 只含 `src/freegraph/` 与 `README.md` / `LICENSE` / `pyproject.toml` / `PKG-INFO` 等允许项（**不含 `.gitignore`**）。
3. **Given** 任一产物，**When** 检查是否含 `harness/` / `.specify/` / `.opencode/` / `.github/` / `specs/` / `tests/` / `test/` / `dist/` / `.venv/` / `node_modules/` / `__pycache__/` / `.gitignore`，**Then** 命中数为 **0**。
4. **Given** wheel 产物，**When** 检查必需文件，**Then** `freegraph/__init__.py` 与 `freegraph/py.typed` **都存在**；sdist 的 `src/freegraph/__init__.py` / `README.md` / `LICENSE` / `pyproject.toml` / `PKG-INFO` **都存在**（防「空包」通过）。

---

### User Story 3 - 发布前有一道机械拦截 (Priority: P1)

作为项目发起者，我希望发布流水线在 `uv publish` **之前**自动运行纯度断言；
一旦产物里混进仓库文件就**中止发布**，而不是发布后才发现。

**Why this priority**: 只靠 `pyproject.toml` 的 `only-include` / `exclude` 是**配置层**约束，
有人改一行配置就会静默失效。必须是**独立于构建配置**的断言，并在上传前强制执行。

**Independent Test**: ① 正常产物 → 门禁退出码 0；② 故意把一个仓库文件（如 `harness/report.md`）
放进 `dist/` 的 sdist/wheel 副本 → 门禁退出码非 0 且输出明确的「拒绝发布」信息；
③ 检查发布工作流，断言纯度步骤位于 publish 步骤**之前**。

**Acceptance Scenarios**:

1. **Given** 干净产物，**When** 运行纯度门禁，**Then** 退出码 0，逐个产物打印「仅含包代码与必要元数据」。
2. **Given** 被恶意混入 `harness/` 文件的产物副本，**When** 运行纯度门禁，**Then** 退出码非 0，并指出具体违规路径。
3. **Given** `dist/` 不存在或为空，**When** 运行纯度门禁，**Then** 快速失败（退出码非 0），不误报成功。
4. **Given** 发布工作流定义，**When** 阅读 job 步骤顺序，**Then** 「构建 → 纯度断言 → 发布」严格有序，且纯度步骤失败会使 job 失败、发布不执行。

---

### User Story 4 - 我能查 freegraph 与 LangGraph 的兼容程度 (Priority: P2)

作为用户，我想知道 freegraph 哪些 API 与上游**行为等价**、哪些**部分等价**、哪些**不支持**，
并能查到每一条的依据（18 项固定脚本 API 元素 + 契约层符号 + 持久化 / 时间旅行 / OTLP 等新增面）。

**Why this priority**: 兼容矩阵是宪法原则 X 的**强制文档义务**，也是「宣称兼容」与
「暗示 affiliation」之间的法律隔离带。它不阻断安装，但缺失即不得宣布发行就绪。

**Independent Test**: 打开 `COMPAT.md`，逐项核对 §4.3 的 18 项、全部下游承接行、三档标注与
affiliation 免责声明；对照 `THIRD_PARTY_NOTICES` 检查第三方归属完整。

**Acceptance Scenarios**:

1. **Given** `COMPAT.md`，**When** 逐行核对 18 项（Q3 §3.4 的 `target.py` 元素），**Then** 每项都有 freegraph 处置、等价程度、差异说明与依据。
2. **Given** `COMPAT.md`，**When** 查找下游承接要求的行，**Then** 以下**全部存在**：多源汇合边、`MemorySaver`、`InMemorySaver`、`CheckpointTuple`、`SqliteSaver`、`CompiledGraph.get_state`、`CompiledGraph.get_state_history`、`CompiledGraph.update_state`、时间旅行重放 / 分叉、`OtlpExporter`（下游行名统一写作 `CompiledGraph.<method>`）。
3. **Given** 任一矩阵行，**When** 追查其依据，**Then** 可定位到 Q3 §3.4 裁定、上游 `路径:行号`、或对应 feature 的实测记录；**没有无依据的断言**。
4. **Given** `COMPAT.md` 与 README，**When** 搜索 affiliation 声明，**Then** 均明确写有「兼容意图为互操作，不构成 affiliation」。

---

### User Story 5 - README 能让新用户一眼看懂边界 (Priority: P2)

作为潜在用户，我希望 README 以**中文为主 + 英文覆盖关键段落**说明：freegraph 是**独立实现、非 LangChain Inc. 产品**；
三条承诺（**零账号（含零 license key） / 零出站 / 零第三方运行时依赖**）；以及一张
「**能力 → freegraph 处置**」表（立项书 §3.2 定稿表体，**5 列逐字复刻** + as-of 日期）。

**Why this priority**: README 是 PyPI 落地页与第一接触面；商标与归属声明是原则 IX 的红线。

**Independent Test**: 通读 README，检查双语段落、独立实现声明、三条承诺、§3.2 能力处置表、
`COMPAT.md` 链接、`[otlp]` 安装说明；再做商标/品牌资产扫描。

**Acceptance Scenarios**:

1. **Given** README，**When** 查找声明，**Then** 存在「独立实现、非 LangChain Inc. 产品」且中英双语表达一致。
2. **Given** README，**When** 查找三条承诺，**Then** 「零账号（含零 license key） / 零出站 / 零第三方运行时依赖」逐条出现且有解释。
3. **Given** README，**When** 查找「能力 → freegraph 处置」表，**Then** **逐字复刻**立项书 §3.2 的 **5 列**（能力 / Developer `$0` / Plus `$39/seat/月` / Enterprise / freegraph v1）与 **8 行**，并附 as-of 日期（含「做 / 不做（v2）/ 永不做」三档）。
4. **Given** README 与全部随包文档，**When** 扫描 LangChain / LangSmith / langgraph 的商标、logo、品牌色或官方文案，**Then** 未发现品牌资产（**允许**为说明互操作而使用的纯文字名称，且均伴随免责声明）。

---

### Edge Cases

- **空 / 缺失 `dist/`**：纯度门禁 MUST 快速失败，不得把「没有产物」误判为干净。
- **只构建了 wheel 或只构建了 sdist**：门禁 MUST 对实际存在的每个产物分别检查；若一个都没有 ⇒ 失败。
- **额外产物类型**（如 `.tar.gz` 以外的压缩包、`.zip`）：MUST NOT 被静默忽略；`check_dist_purity.py` MUST 对 `dist/` 内任何**归档类**非 `.whl` / `.tar.gz` 文件（如 `.zip` / `.tar` / `.tgz` / `.tar.bz2`）判失败；**`uv build` 自动生成的 `dist/.gitignore` 属于构建工具标记，MUST 显式豁免**（不得把「干净构建」误判为污染）。负向用例 MUST 覆盖 `evil.zip`。
- **`[otlp]` 被误判**：门禁与打包检查 MUST 把 `[otlp]` 视为**唯一合法** extra；其余四个 extra 出现在发行元数据 ⇒ 失败。
- **`[otlp]` 闭包被污染**：出现 `certifi` / `requests` / `opentelemetry-exporter-otlp-proto-http` / `opentelemetry-exporter-otlp` 元包 ⇒ 依赖门禁失败（**精确包名**；`opentelemetry-exporter-otlp-proto-grpc` 是允许项）。
- **许可证标识为散文**：`protobuf` 的 `3-Clause BSD License` 只允许**具名归一**为 `BSD-3-Clause`；MUST NOT 建立通用对照表或放宽白名单。
- **wheel 缺 `py.typed`**：MUST 失败（PEP 561 承诺不可丢）。
- **wheel 根级出现非 `freegraph/` / 非 `freegraph-*.dist-info/` 的文件**（如 `freegraph-evil.txt`）：
  MUST 失败；`freegraph-` 前缀本身不构成合法豁免。
- **sdist 缺 `PKG-INFO` / `LICENSE` / `pyproject.toml`**：MUST 失败（无法重建 wheel 或违反许可展示）。
- **sdist 含 `.gitignore`**：MUST 失败（`.gitignore` 是仓库根文件，不属于 Release Gate 的
  「必要元数据」；MUST NOT 因 hatchling 默认附带而放行）。
- **Windows 路径分隔符**：门禁对 `\` 与 `/` MUST 归一后判定，避免漏检。
- **负向验证污染真实 `dist/`**：负向用例 MUST 在**临时副本 / 临时目录**中构造，MUST NOT 修改真实构建产物。
- **README 英文未覆盖关键段落**（声明 / 三条承诺 / 安装与 `[otlp]` / 能力处置摘要 / `COMPAT.md` 链接）：
  不满足双语要求；仅有英文而缺中文主体，亦不满足「中文为主」。
- **`COMPAT.md` / `THIRD_PARTY_NOTICES` 被误打进产物**：两者属**仓库文档**，MUST NOT 进入 wheel / sdist；
  发行包内只能通过 README 的**绝对 GitHub URL** 指向仓库版本。
- **D3 已决（2026-11-05）**：LICENSE MUST 保持 **MIT**；MUST NOT 擅自切换为 Apache-2.0。
- **`import freegraph` 连带加载重层**：安装验收 MUST 只断言 `import freegraph` 成功；若版本门面保持惰性，MUST NOT 因本 feature 破坏该惰性。

---

## Upstream Parity *(mandatory — 宪法 v1.9.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.19**（**兼容矩阵既有行**所引用的证据版本，如 `StateDict` 行）· `langgraph` **1.2.11**（**契约层差分核实版本** · `pyproject` 钉死 · **新增 / 复核行与差分测试以此为准**）· `langchain-core` **1.6.3 / 1.7.6**（取证于 2026-11-05 / 2026-11-06 / 2026-11-24）

> **版本口径（MUST）**：`COMPAT.md` 的**既有行**保留其原先引用的版本（含 `StateDict` 的 `1.2.19`），
> **MUST NOT** 为统一版本号而改动既有行；**新增 / 复核行**与**差分测试**统一以 **`1.2.11`** 为准；
> 本 spec 的下游对照表锚点**未特别注明者均为 `1.2.11`**。每行的 `路径:行号` MUST 与其声明版本一致
> （宪法原则 XI 的锚点纪律）。

> **本 feature 的性质**：发行 / 文档单元，**不新增运行时行为**。因此本节的「上游对照」
> 聚焦于**兼容矩阵所陈述的事实**是否与上游一致；每条事实 MUST 可追溯到 §4.3 的裁定、
> 上游 `路径:行号`、或既有 feature 的实测。**MUST NOT** 在本 feature 新增或改写运行时语义。

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | `StateGraph` / `START` / `END` / `add_node` / `add_edge` / `add_conditional_edges` / `compile` / `invoke` 同名同签名 | `langgraph/graph/state.py:131` / `:216-224` / `:667-682` / `:928` / `:982-989` / `:1177-1188`；`langgraph/pregel/main.py:3783`；`langgraph/constants.py:28,30` | 逐字对齐（B6F1 / B7F2 / B7F3 / B8F1 已交付） | SAME | — |
| P-02 | 归约器 / 稀疏状态 / 部分状态合并 / 鸭子类型消息 | `harness/reports/Q8-图运行时最小契约.md` §3.4（C4 · C5 · C6 · C8） | 行为等价（B4F1 / B5F1 / B5F2 / B8F1） | SAME | — |
| P-03 | `get_graph(xray=True).draw_mermaid_png()` | `langgraph/pregel/main.py:845`（`get_graph`）；上游 PNG 默认经 `langchain_core` 请求 `mermaid.ink` | 方法名同名；**v1.0 返回固定示意图标占位 PNG**（64×64 · 3 方框 + 2 连线 · 零出站 · 离线不阻断）；真实渲染归 v2.0 `[png]` | DIFF | 零出站硬约束；真实渲染引入依赖 / 出站，属 v2。**已由 B23F1 登记** |
| P-04 | `Command` / `NodeFunc` / `Send` 运行期语义与返回形态 | `langgraph/types.py:704`（`Send`）· `:821-824` / `:836-840`（`Command`）· `langgraph/graph/state.py:1459-1460` | 运行期语义已落地（B9F1 / B11F1）；`Send` 类型定义住 L1；`Command` 的 `goto` 缺省为 `None`（上游 `()`），非法目标 / 非 dict `update` 显式失败（上游静默忽略）；`Send` 侧不可变（上游可变）；`NodeFunc` 为 freegraph 自有协议，无上游同名物 | SAME / STRICTER / DIFF | 运行期成功路径 = **SAME**；失败信号 MAY 比上游更严 ⇒ **STRICTER**（X-06）；`goto` 缺省 `()` vs `None` 是**成功路径可观察差异** ⇒ **DIFF**（**Y-01** · 既有偏差 · 不属「更严」）；`Send` 不可变 vs 上游可变 = **DIFF**（B11F1 · 矩阵「部分等价」）；`NodeFunc` 无上游同名协议（C5 / C6）⇒ 矩阵按「不支持（无上游对应）」登记，**不是**「比上游更严」 |
| P-05 | `compile` 的 `interrupt_before` / `interrupt_after` 与 `recursion_limit` dict 载体 | `langgraph/graph/state.py:1177-1188`；`langchain_core/runnables/config.py:80-124` | 已交付（B13F1） | SAME | — |
| P-06 | `Checkpointer` / `MemorySaver` / `SqliteSaver` / `CheckpointTuple` | `langgraph/checkpoint/base/__init__.py:239,253,277,300,320,331,350,692`；`langgraph-checkpoint-sqlite 3.1.1` | `Checkpointer` 八方法对齐；`MemorySaver` = `InMemorySaver` 别名；`CheckpointTuple` 恰三公开字段；`SqliteSaver` 为 MIT 改编（已登记） | SAME / DIFF | `SqliteSaver` 移除 serde/msgpack/aiosqlite/langchain_core，序列化改标准库 `json`（**X-07** · B15F1 已登记于 `THIRD_PARTY_NOTICES` §1） |
| P-07 | `get_state` / `get_state_history` / `update_state` / 时间旅行 | `langgraph/pregel/main.py:1392` / `:1480` / `:2515`；`use-time-travel.md:78-96,163-170` | `get_state` 按上游 next-tasks 语义；历史按 `checkpoint_id` 倒序；`update_state` 返回 `RunConfig`、支持 `as_node`、**无 `task_id`**；`invoke(None, snapshot.config)` 重放 / 分叉（B15F1 / B16F1）；`get_state` 无快照返回 `None`（上游空 `StateSnapshot`） | SAME / STRICTER / DIFF | `get_state` / `get_state_history` 的 next-tasks / 倒序 / 过滤语义 = **SAME**；`update_state` 的失败信号 MAY 更严 ⇒ **STRICTER**（本 spec **X-04** / B16F1；`interrupt` 恢复未挂 checkpointer 同属 X-04），`get_state` 缺 `thread_id` 的失败信号 = **STRICTER**（B15F1 **X-08**，不是本 spec 的 X-04）；`get_state` 的 `None` vs 上游空 `StateSnapshot` = **DIFF**（B15F1 P-02 / X-01）；`update_state` 无 `task_id`、`values=None, as_node=END` 与时间旅行线性重放 = **v1 能力边界** ⇒ 矩阵标「部分等价」，**不属「更严」** |
| P-08 | 多源汇合边 `add_edge([a, b], c)` | `langgraph/graph/state.py:928`（签名 `str \| list[str]`） | 支持（L2 `GraphSpec` 元组键 · L3 接线 B6F1） | SAME | 宪法原则 X：**导出面零新增 ≠ 兼容矩阵零变**（B7F4 D-6） |
| P-09 | `OtlpExporter` | **无上游同名物** | freegraph L5 自由设计：`TraceSink` 三方法；端点 / 导出器两种显式注入；默认关闭、零出站 | DIFF | 属原则 XI「必须自研区」③「上游没有的能力」；**矩阵等价程度 =「不支持（无上游对应 / 自由设计）」**（B21F1）——其中「不支持」表示**上游无对应物**，**不表示** freegraph 不提供该能力；与 Upstream Parity 的「关系 = DIFF」是两个轴，不矛盾 |
| P-10 | 固定脚本 18 项 API 元素 | `harness/demo/target.py` 第 3 / 4 / 54 / 64 / 87 / 103 / 123 / 126-127 / 130 / 131-135 / 136 / 139 / 144 / 147 / 149 行；裁定见 `harness/reports/Q3-LangGraph的开源边界.md` §3.4 | 逐项见下方 18 项覆盖表 | SAME / DIFF | #13 PNG 为 DIFF（占位）；#14–#18 不属 freegraph 范围（**行为等价 · 原样承载**，不做类型转换） |

### 18 项覆盖表 *(SC-004 的逐项判据 · Q3 §3.4)*

| # | `target.py` API 元素 | 上游是否直接提供 | freegraph 处置 | 等价程度 | 证据 |
|---|---|---|---|---|---|
| 1 | `from freegraph.graph import StateGraph, START, END` | ✅ | 同名导出（`START='__start__'` / `END='__end__'`） | 行为等价 | Q3 §3.4 #1 |
| 2 | `StateGraph(MessagesState)` | ✅ | 只传 schema 一个位置参数 | 行为等价 | Q3 §3.4 #2 |
| 3 | `add_node(name, fn)` | ✅ | 位置参数 `(str, Callable)` | 行为等价 | Q3 §3.4 #3 |
| 4 | `add_edge(src, dst)` | ✅ | `(str \| list[str], str)` · 链式返回 · **多源汇合边支持**（H-1） | 行为等价 | Q3 §3.4 #4 · B7F4 D-6 |
| 5 | `add_conditional_edges(src, path_fn, path_map)` | ✅ | `path_map` 支持 list / dict / `None` | 行为等价 | Q3 §3.4 #5 · B8F1（`None` 形态） |
| 6 | `compile()` | ✅ | 无参可调用；另接受 `interrupt_before` / `interrupt_after` 等上游关键字（H-4） | 行为等价 | Q3 §3.4 #6 · B13F1 D-8 |
| 7 | `compiled.invoke({"messages": [...]})` | ✅ | 返回**完整状态** dict | 行为等价 | Q3 §3.4 #7 |
| 8 | `Annotated[list[AnyMessage], operator.add]` 归约器 | ✅ | 二元 reducer `(a,b)->c` | 行为等价 | Q3 §3.4 #8 |
| 9 | `state.get('llm_calls', 0)` | ✅ | 节点入参是**普通 dict** | 行为等价 | Q3 §3.4 #9 |
| 10 | 节点返回**部分** state 的合并规则 | ✅ | 有 reducer 则归约；无 reducer 则覆盖 | 行为等价 | Q3 §3.4 #10 |
| 11 | `state["messages"][-1].tool_calls` | ✅ | 鸭子类型读取；freegraph 不需要懂消息类型 | 行为等价 | Q3 §3.4 #11 |
| 12 | `if last_message.tool_calls:` 真值判定 | ✅ | 空 list ⇒ falsy（鸭子类型） | 行为等价 | Q3 §3.4 #12 |
| 13 | `get_graph(xray=True).draw_mermaid_png()` | ✅ | 方法名同名；**v1.0 占位 PNG**（合法可展示字节、零出站、离线不阻断）；v2.0 `[png]` 真实渲染（DIFF 已登记 · X-01） | 部分等价 | Q3 §3.4 #13 · B23F1 D-3 |
| 14 | `display(Image(...))` | ❌（IPython，脚本自身） | 不属 freegraph 范围；不阻断脚本（原样承载 · 不属范围） | 行为等价 | Q3 §3.4 #14 |
| 15 | `init_chat_model(...)` | ❌（`langchain` 层） | 不属 freegraph 范围（归 freechain；原样承载 · 不属范围） | 行为等价 | Q3 §3.4 #15 |
| 16 | `@tool` / `tool.name` / `tool.invoke` | ❌（`langchain` 层） | freegraph 仅原样承载工具对象（鸭子类型），不做类型转换（原样承载 · 不属范围） | 行为等价 | Q3 §3.4 #16 |
| 17 | `tool.invoke(tool_call["args"])` | ❌（脚本自身逻辑） | 不属 freegraph 范围（原样承载 · 不属范围） | 行为等价 | Q3 §3.4 #17 |
| 18 | `ToolMessage(...)` | ❌（`langchain.messages`） | freegraph 原样流转该对象，不做类型转换（原样承载 · 不属范围） | 行为等价 | Q3 §3.4 #18 |

> **口径**：18 项中 **7 项同名同签名**（#1–#7）· **1 项方法名同名**（#13，字节行为另定）·
> **10 项行为等价 / 原样承载**（#8–#12、#14–#18）；其中 **#14–#18 不属 freegraph 范围**
> （由脚本自身 / `langchain` / freechain 提供，freegraph **不转换、不阻断、原样承载**）；
> **0 项触及 LangSmith**。
>
> **`path_map` 的三种形态**：立项书 §4.3 #5 列出的 list / dict 是**最小义务**；`None`
> （缺省 ⇒ 由上游同款语义推导）为 B8F1 已交付能力，本矩阵按**实际支持**记录。

### 差分场景组 *(mandatory)*

> 本 feature **不新增运行时行为**，但仍 **MUST 交付一组最小差分场景**（宪法原则 XI 的可验证出口）：
> 用于证明矩阵所陈述的**既有行为事实**与上游一致，且**不要求对齐**任何既有差异（Y-01 / Y-02 / Y-03）。
> 下表编号 `G-01…G-07` 是**本 spec 的覆盖映射编号**，**不是** `tests/differential/` 里既有的场景 ID；
> **新增的最小差分组**以 `B24F1-D-01…D-03` 命名，落在
> `tests/differential/test_b24f1_matrix_parity.py`（上游缺席即 skip；**不改运行时**）。
> 落地时 MUST 在 `COMPAT.md` 行内引用**实际存在的场景名**，**MUST NOT** 把 `G-xx` 当作测试用例名。

| #（覆盖映射） | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 | 既有套件落点（示例） |
|---|---|---|---|---|
| G-01 | `StateGraph` 构建 + 条件边 + `invoke` 完整状态 | 与上游同图同输入 ⇒ 节点序列 / 最终状态键集一致 | SAME | `test_differential.py` / `parity_probe.py` 的图运行场景 |
| G-02 | 稀疏状态 + `state.get(default)` + 部分更新合并 | 节点入参不含空 channel；无 reducer 覆盖、有 reducer 归约 | SAME | `test_differential.py` 的状态语义场景 |
| G-03 | `Command` / 命令列表 / `Send` fan-out | 成功路径：目标集合 / 写入归属 / 最终状态一致；失败路径：非法目标 / 非 dict `update` 显式失败 | SAME（运行期成功路径）/ STRICTER（失败信号 · X-06）/ DIFF（`goto` 缺省值 · Y-01；`Send` 不可变 · Y-03） | `test_differential.py` / `parity_probe.py` 的命令与 fan-out 场景 |
| G-04 | `interrupt` / `resume` / 静态挂起 / `recursion_limit` | 中断载荷、挂起点、恢复起点一致；超限抛同名错误 | SAME | `parity_probe.py` 的中断 / 静态挂起场景 |
| G-05 | `get_state` / `get_state_history` / `update_state` / 重放分叉 | next-tasks 语义、历史倒序、分叉不污染原历史 | SAME / STRICTER / DIFF（`get_state` 无快照 `None` · Y-02）/ 能力边界（`update_state` 无 `task_id`、时间旅行线性） | `test_b15f1_state_parity.py` · `test_b16f1_time_travel_parity.py` |
| G-06 | 多源汇合边 `add_edge([a, b], c)` | 两个源都完成后目标只执行一次 | SAME | `parity_probe.py` 的 B7F4 屏障场景 |
| G-07 | `get_graph(xray=True)` + `draw_mermaid()` / `draw_mermaid_png()` | mermaid 文本合法；PNG 为合法占位字节；零框架出站 | DIFF（PNG 占位 · X-01） | `parity_probe.py` 的 `graph D-01…D-15` 与 `png D-01…D-10`（以实际场景名为准） |

**B24F1 最小差分组（MUST · 宪法原则 XI 的可验证出口）**

| # | 场景 | 断言 | 判词 | 落点 |
|---|---|---|---|---|
| **B24F1-D-01** | `Command().goto` 缺省值 | 上游实测 `()`；freegraph `None` ⇒ 两侧差异与 `COMPAT.md` 的 `Command` 行 **Y-01** 一致 | DIFF | `tests/differential/test_b24f1_matrix_parity.py` |
| **B24F1-D-02** | `Send` 可变性 | 上游可变；freegraph 不可变 ⇒ 与 `COMPAT.md` 的 `Send` 行 **Y-03** 一致 | DIFF | 同上 |
| **B24F1-D-03** | `get_state` 无快照 | 上游返回空 `StateSnapshot`；freegraph 返回 `None` ⇒ 与 `COMPAT.md` 的 `get_state` 行 **Y-02** 一致 | DIFF | 同上 |

> 本组**只记录并断言既有差异**（不改运行时）：Y-01 的文档承接归 **B25F1**，Y-02 / Y-03 在本 feature 登记，
> 运行时对齐（若需）归 **v2 独立契约修订**。上游缺席时该测试 MUST `pytest.skip`（不是失败）。

### 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| X-01 | 必须自研区（零出站 / 零依赖） | `draw_mermaid_png()` 真实渲染 | v1 零出站 / 零依赖；占位 PNG 为契约合法形态（与 B23F1 X-03 同类） | **B23F1**（已登记）· v2.0 `[png]` |
| X-02 | 上游没有的能力 | `OtlpExporter`（无上游同名物） | freegraph 自有 L5 导出插件 | **B21F1**（已登记） |
| X-03 | 必须自研区（零依赖 / 零出站 / 零账号） | `FreegraphError` / `TraceSink` / `Span` / `TraceQuery` 等自有符号 | 上游无同名物或上游实现引入依赖 / 账号 / 出站 | 既有契约层（B1F1 / B2F1 / B18F1 / B20F2） |
| X-04 | 更严的失败信号 | `update_state` 无歧义推断失败 / `interrupt` 恢复未挂 checkpointer | 显式失败优于静默忽略 | **B10F1 / B16F1**（已登记） |
| X-05 | 必须自研区（零依赖） | `interrupt.id` 摘要算法 `xxh3_128` → `blake2b-128` | 零第三方依赖；同长十六进制 | **B10F1**（已登记） |
| X-06 | 更严的失败信号（**仅失败面**） | `Command` 的非法 `goto` 目标 / 非 dict `update` | 显式失败优于上游静默忽略 ⇒ 与 **Y-01** 共同使兼容矩阵定为**部分等价** | **B9F1**（X-1 / X-4 已登记）· 本 feature 定稿纠正（Clarifications 2026-11-24） |
| X-07 | 必须自研区（零依赖） | `SqliteSaver` 的序列化与依赖面 | 移除 serde / msgpack / `aiosqlite` / `langchain_core`，改用标准库 `json`（零第三方依赖） | **B15F1**（`THIRD_PARTY_NOTICES` §1 已登记） |

> ⚠️ **X-06 只覆盖失败信号**。`Command.goto` 缺省 `()` vs `None` 是**成功路径可观察差异**
> ⇒ **不属**「更严的失败信号」，**MUST NOT** 记入 X-06；见下方 **Y-01 / Y-02 / Y-03** 的既有偏差登记。

### 既有行为面差异（非「更严」· 已具名承接）

> 本表**不属**上方三类自研区。它登记的是**已存在的**成功路径行为面差异 ⇒
> **MUST NOT** 被解释为「比上游更严」或「三类之一」。B24F1 **不改运行时**，
> 只如实登记；**具名承接 = B25F1（M4）**，运行时对齐归 v2；MUST 在本 feature 的
> `manual-verification.md` 遗留问题中显式列出。

| # | 差异 | 上游 | freegraph | 关系 | 处置 / 承接 |
|---|---|---|---|---|---|
| **Y-01** | `Command.goto` 的缺省值 | `Command().goto == ()` | `Command().goto is None`（B1F1 冻结 `goto: ... \| None = None`） | **DIFF**（成功路径可观察差异） | **本 feature 只登记 · 不改运行时**（B1F1 缺省值属冻结面；本 feature 的破冻结面追认已用于 G8/G19/G29，按「每 feature ≤1 次」不叠加）。**具名承接：B25F1（M4）** 在双跑验收 / 迁移说明中保留该记录并提示 v1 行为；运行时对齐（若需）归 **v2 独立契约修订**。发起者已于 2026-11-24 clarify 接受该既有偏离；MUST 在 `COMPAT.md` 的 `Command` 行与 `manual-verification.md` 遗留问题中**双处**注明。 |
| **Y-02** | `get_state` 无快照时的返回值 | 上游返回空 `StateSnapshot` | freegraph 返回 `None`（L1 已冻结） | **DIFF**（既有差异 · B15F1 X-01） | 本 feature 只登记；`COMPAT.md` 的 `get_state` 行注明；运行时对齐归 **v2 独立契约修订**。 |
| **Y-03** | `Send` 是否可变 | 上游 `Send` 可变 | freegraph 侧不可变 | **DIFF**（既有差异 · B11F1） | 本 feature 只登记；`COMPAT.md` 的 `Send` 行注明「形状等价 + 不可变差异」；运行时对齐归 v2。 |

> **v1 能力边界（非偏离 · 不占 X / Y 编号）**：`update_state` 不暴露 `task_id`、
> 不接受 `values=None, as_node=END`，时间旅行只保线性重放（B16F1）。这些是**能力边界**，
> 不是「比上游更严」；矩阵按「部分等价」登记，说明写进 `COMPAT.md` 的对应行与「证据与来源」。

### 破冻结面的回溯修订清单 *(若有)*

> **依据**：发起者 2026-11-24 在 clarify 后选择 **A**（`COMPAT.md` 唯一权威；README 只留能力表 +
> 链接；同步改写 G8 / G19 / G29）。以下为**已获追认**的冻结面更新；正式追认文字落
> `harness/verification/B24F1/manual-verification.md`。

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| **G8** 从 README 取行 | `tests/contracts/test_architecture.py` · `specs/b2f1-contracts-protocols/contracts/architecture-gates.md` §G8 · `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 总览 | 取行源改为 `COMPAT.md`；新增「README 只能有指针、不得有完整矩阵」断言；**判据强度不降** | 2026-11-24 · 选项 A |
| **G19** 从 README 取行 + 禁止降级 | `tests/facade/test_facade_gates.py` · `tests/facade/_gatesupport.py` · `specs/b2f2-public-api-facade/contracts/architecture-gates.md` §G19 · `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 总览 | 取行源改为 `COMPAT.md`；新增 **B24F1 定向例外**：仅 `Command` 允许「行为等价 → 部分等价」的**纠漂移**；`Command` **不整体移出**单调检查，其它任何等级变化（含 `部分等价 → 不支持`）MUST 失败；其它行仍不可降级 | 2026-11-24 · 选项 A |
| **G29 `--check-compat`** | `harness/scripts/gates/gate_G29_contract_carrier.py` · `architecture-gates.md` §G29 判定 4 | 由「COMPAT vs README」改为「COMPAT 为权威 + README 仅指针」；仍复用 `_gatesupport` 取行 | 2026-11-24 · 选项 A |
| 不破 | `src/freegraph/**` · `harness/demo/target.py` · 契约 / 门面符号面 · `dependencies` / `[otlp]` · G21 / G23 / G26 / G30 | 零改动 | — |

> **实测义务（宪法 v1.9.0 / v1.11.0）**：T002 / T010 MUST 在临时副本中按本 feature 的落地形态改动
> `COMPAT.md` / README / 门禁取行源，跑既有测试套件，记录**变红的断言清单**（逐条 `文件:行号` +
> 变红原因）。至少覆盖：G8 取行 / affiliation / 列数断言；G19 取行 / baseline / `Command` 例外 /
> **`Command` 定向例外（`行为等价 → 部分等价` 放行，其它等级变化失败）/ `Send` 降级负向自检**；`tests/runtime/test_parse_contract.py` 的矩阵断言；
> `gate_G29_contract_carrier.py --check-compat`。
> 清单 MUST 落 `manual-verification.md` 附录。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001（打包产物）**：系统 MUST 产出可安装的 **wheel + sdist**；基础安装 `dependencies = []`，
  **零第三方运行时依赖**；发行元数据中的 `[project.optional-dependencies]` MUST **有且仅有 `otlp`**
  一个键（宪法 v1.17.0 唯一具名例外）；其余四个 extra（`[pydantic]` / `[checkpoint]` / `[otel]` / `[png]`）
  MUST NOT 进入 v1.0 发行元数据。
- **FR-002（产物纯度）**：发行产物 MUST **仅含** `src/freegraph/` 包代码与必要元数据
  （README / LICENSE / pyproject.toml / PKG-INFO / `py.typed`）；
  MUST NOT 含 `harness/` / `.specify/` / `.opencode/` / `.github/` / `specs/` / `tests/` / `test/`
  / `dist/` / `.venv/` / `node_modules/` / `__pycache__/` / `.gitignore`。
  wheel 根级只允许 `freegraph/` 与 `freegraph-*.dist-info/`；任何其它 `freegraph-` 前缀文件
  （如 `freegraph-evil.txt`）⇒ **失败**（`freegraph-` 前缀本身不构成合法豁免）。
  `COMPAT.md` / `THIRD_PARTY_NOTICES` 属**仓库文档**，MUST NOT 进入 wheel / sdist；
  发行包内只能通过 README 的**绝对 GitHub URL** 指向仓库版本（例如
  `https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md`）——
  **MUST NOT** 依赖相对路径（PyPI 落地页上会 404）。
- **FR-003（纯度门禁接入）**：系统 MUST 使用**独立于构建配置**的断言脚本
  `harness/scripts/check_dist_purity.py`，并在发布流水线中于 **`uv publish` 之前**强制执行；
  断言失败 ⇒ **中止发布**。脚本 MUST NOT 依赖 `pyproject.toml` 的 `only-include` / `exclude` 作为判据；
  脚本 MUST **只使用 Python 标准库**（含 METADATA 解析；**MUST NOT** `import packaging`），
  以保证发布流水线用系统 `python3` 可直接执行。
- **FR-004（API 兼容矩阵）**：系统 MUST 交付 `COMPAT.md`，以「**行为等价 / 部分等价 / 不支持**」三档
  覆盖：① Q3 §3.4 的 **18 项**（逐项可核对，见 18 项覆盖表）；
  ② **全量**契约层 / 门面公开符号矩阵（现有 README 的逐符号表 **全量迁入**；
  **并集 27 = 契约层 22 ∪ 门面层 8**，其中 `Command` / `RunConfig` / `Send` 去重；
  **不得硬编码旧 18/7、20/7、20/8**）；
  ③ **全部下游承接行**（多源汇合边、`MemorySaver`、`InMemorySaver`、`CheckpointTuple`、`SqliteSaver`、
  `CompiledGraph.get_state`、`CompiledGraph.get_state_history`、`CompiledGraph.update_state`、时间旅行重放 / 分叉、`OtlpExporter`；下游行名统一写作 `CompiledGraph.<method>`）。
  `Store` 行等价程度保持**行为等价**且机读行**逐字不改**；「协议等价 · v1 无实现 · `batch` 挂起 v2」的
  澄清 MUST 落在 `COMPAT.md` 的「**证据与来源**」章节。该「逐字不改」MUST 由
  `tests/contracts/test_b24f1_compat.py` 的专用断言对照 baseline（`HEAD:COMPAT.md` 优先、
  `HEAD:README.md` 回退）核验——**MUST NOT** 依赖 G19 的「等价程度不变差」检查
  （`Store` 在既有白名单内，G19 不保证其差异说明逐字不变）。
  机读段内 MUST 注明「**兼容意图为互操作，不构成 affiliation**」。
  `Command` 行 MUST 标注为**部分等价**，差异说明 MUST 分别记录：
  ① `goto` 缺省 `()` vs `None` = **DIFF**（既有偏差 **Y-01** · 成功路径可观察差异 · **不得**写成「更严」）；
  ② X-1 / X-4 的显式失败 = **STRICTER**（**X-06**）；
  ③ X-2 / X-3 的异常类型差异（B9F1 的偏差编号，**不是**本 spec 的 X-02/X-03）。
  本 feature MUST 同时**纠正上游对齐批次 P3（commit `99d43aa`）引入的「行为等价」漂移**并在矩阵中注明纠正来源（B22F1 的 `125ba0f` 仅措辞更新）。
  下游承接的事实性更新 MUST 一并落库：**H-4** 在 `StateGraph`（`compile`）行记录
  `interrupt_before` / `interrupt_after` 与 `recursion_limit` 的 dict 载体；**H-9 / FR-018** 在 `Graph`
  行记录 v1 占位 PNG 与 v2 `[png]` 升级路径；**H-3** 在 `Send` 行 MUST 记录「运行期语义已落地」与
  「freegraph 侧不可变（上游可变）」（**Y-03**）；`NodeFunc` 行 MUST 记录「无上游同名协议」；**H-6** 的
  `CompiledGraph` 机读行 **与**下游 `get_state` 行 MUST **双处**按 **Y-02** 标注 DIFF；**H-7** 的
  `CompiledGraph` 机读行 **与**下游 `update_state` / 时间旅行行 MUST **双处**标注
  **v1 能力边界**（非「更严」）。下游行名统一写作 `CompiledGraph.get_state` /
  `CompiledGraph.get_state_history` / `CompiledGraph.update_state`。
  `COMPAT.md` MUST 是**唯一权威**的逐符号 / 逐项矩阵；README **MUST NOT** 维护第二份完整矩阵。
- **FR-005（第三方归属）**：系统 MUST 定稿 `THIRD_PARTY_NOTICES`，登记全部**引入的第三方代码**
  （复制 / 改编 / vendored）与**可选 extra 依赖**的原始版权与许可声明；`SqliteSaver` 的 MIT 改编
  MUST 保留 LangChain, Inc. 版权声明；`[otlp]` 闭包 MUST 逐包登记。
- **FR-006（README）**：系统 MUST 交付 README（**中文为主 + 英文覆盖关键段落**），含
  「**独立实现、非 LangChain Inc. 产品**」声明与三条对外承诺
  （**零账号（含零 license key） / 零出站 / 零第三方运行时依赖**）。
  英文 MUST 至少覆盖：独立实现声明、三条承诺、安装与 `[otlp]`、能力处置摘要、指向 `COMPAT.md`
  的链接；**MUST NOT** 要求逐节全译（SC-007 按此口径判定）。
  **「中文为主」的判定口径**：除上述英文关键段落外，README 的其余章节说明文字 MUST 为中文；
  英文关键段落 MUST 以**显式子标题 / 标注**呈现（或集中于独立的英文摘要段），
  **MUST NOT** 以「英文散落在各节」冒充关键段覆盖。
  **可执行判定**：所有 `##` 级章节标题 MUST 为中文；唯一例外是显式的
  `## English` / `## English Summary` 段（或带 `[English]` 标注的段落）。
  非英文段内 MUST NOT 出现连续 3 段以上纯英文正文；英文段 MUST 覆盖
  独立实现声明 / 三条承诺 / 安装与 `[otlp]` / 能力处置摘要 / `COMPAT.md` 链接。
  该结构由 `tests/contracts/test_b24f1_docs.py` 断言（作为「中文为主」的可执行判据）。
  README 的 **OTLP 段 MUST 保留**（H-8③）：记录 OTLP 导出能力与**三后端示例**
  （**OpenLIT / Langfuse / Phoenix**），三者**并列、无默认推荐**；不得写入「官方推荐 / 默认后端」措辞。
  README **顶部状态说明** MUST 与当前已交付能力一致：MAY 保留「占位版本」的客观描述，
  **MUST NOT** 出现「内核尚未实现」「没有任何图运行时能力」「请勿当作可用替代品」
  「请勿用于生产」「不要把它当作…可用替代品」等**过时断言**；
  最终文案润色可由 B25F1 收口，但事实性修正归本 feature。
- **FR-007（能力处置表）**：README MUST 含「**能力 → freegraph 处置**」表，**逐字复刻**
  立项书 §3.2 的 **5 列**（能力 / Developer `$0` / Plus `$39/seat/月` / Enterprise / freegraph v1）与 **8 行**，
  并附 as-of 日期（`2026-11-01`，以官方定价页为准）；MUST NOT 只保留 3 列摘要或删减行。
  该表随每次范围变更更新；README MUST 链接 `COMPAT.md` 作为逐符号细节的**唯一权威源**
  （**绝对 GitHub URL** · 见 FR-002），**MUST NOT** 在 README 复制或维护第二份完整兼容矩阵。
- **FR-008（py.typed 与商标）**：发行包 MUST 含 `py.typed`；README 与文档 MUST NOT 使用任何
  LangChain 系**商标资产**（logo / 图标 / 品牌色 / 官方文案 / 暗示官方身份的表述，原则 IX）。
  **纯文字提及**上游产品名（如 `LangGraph` / `langgraph` 关键字与描述）属**互操作说明的
  nominative use**，**允许**，但 MUST 与 README 的「独立实现、不构成 affiliation」声明配套；
  MUST NOT 把纯文字名称做成 logo / 品牌视觉或官方身份暗示。
- **FR-009（Python 版本）**：`requires-python` MUST 为 `>=3.11` 且**不设上限**。
- **FR-010（负向验证）**：系统 MUST 提供可自动执行的负向验证：故意把仓库文件混入产物副本 ⇒
  纯度断言**退出码非 0**；该验证 MUST 在临时副本中进行，MUST NOT 污染真实 `dist/`。
- **FR-011（安装验收）**：系统 MUST 在**隔离环境**验证：基础安装成功、`import freegraph` 成功、
  依赖闭包为空；`pip install "freegraph[otlp]"` 成功且不拉入 `certifi` /
  `opentelemetry-exporter-otlp-proto-http` / `opentelemetry-exporter-otlp` **元包**
  （**精确包名**；`opentelemetry-exporter-otlp-proto-grpc` 是允许项，MUST NOT 用子串误判）。
- **FR-012（下游承接落库）**：本 feature MUST 逐条落库 H-1…H-9 的矩阵要求（**规范细则见 FR-004；本条只强调承接义务**：**既有 machine 行更新 H-2 / H-3 / H-4 / H-9 + 下游新增行 H-1 / H-5 / H-6 / H-7 / H-8**）；**MUST NOT** 遗漏任何一条
  （宪法原则 X：兼容矩阵 MUST NOT 漏记）。**MUST NOT** 把「导出面零新增」误当成「兼容矩阵零变」。
- **FR-013（许可证）**：LICENSE MUST 保持 **MIT**（**D3 已决 2026-11-05** ⇒ 不擅自切换）；`[otlp]` 闭包逐包
  ∈ {MIT, Apache-2.0, BSD-2/3, PSF}；`protobuf` 的散文标识 `3-Clause BSD License` 只允许经
  **仅此一包 / 仅此一字符串**的权威 SPDX 归一为 `BSD-3-Clause`；MUST NOT 放宽白名单或引入通用对照表。
  **开发 / 差分测试的 `dependency-groups`**（`dev` / `differential`）不属发行依赖，不参与本判据。
  **「LICENSE 保持 MIT」MUST** 由 `tests/contracts/test_b24f1_packaging.py`（或 `test_b24f1_notices.py`）
  的可执行断言核验：`pyproject.toml` 的 `license` / `License-Expression` 为 MIT，且 `LICENSE` 文本含 MIT 条款。
- **FR-014（人工门禁）**：系统 MUST 产出 `harness/verification/B24F1/manual-verification.md`，
  写明验证环境、步骤、实际输出、结论、遗留问题；B15F1 / B16F1 要求的人工验收 MUST 纳入。
  该记录的**判据级覆盖 MUST** 由**可自动核验的文档守卫断言**承担（宪法 v1.13.0）：
  断言记录**存在**、五段式齐备、正文**非空**、含**必需的实测输出**（命令 / `pip freeze` /
  纯度退出码 / `B24F1 acceptance: PASS` / G8-G19-G29 追认文字 / 既有偏差 **Y-01 / Y-02 / Y-03** 的遗留项 /
  **质量门禁 5 偏离与 B25F1 承接追认**），
  **MUST NOT** 以「写记录」或「审计」任务冒充判定覆盖；守卫 MUST 安排在记录写就之后
  （**MUST NOT** 造成永久红的 CI）。
  `B24F1 acceptance: PASS` MUST 来自**环境就绪的实际运行**：**CI Linux 作业（具备网络或
  uv / PIP 缓存，可完成 `[otlp]` 依赖安装）** 或**本地已就绪环境**；**不得假设 CI `.venv`
  已装的 extras 会被新建隔离 venv 继承**。若为本地就绪环境，记录 MUST 写明环境与命令；
  若引用 CI，记录 MUST 写明作业名、运行标识与 `[otlp]` 依赖来源。本地缺 `[otlp]` 依赖导致的 `exit 2`（环境未就绪）
  **MUST NOT** 替代 PASS 写入记录。
  `B24F1 acceptance: PASS` MUST 由 `harness/verification/B24F1/acceptance.py` 的**顶层编排**
  统一输出（逐项运行 A1–A3 / US1–US5 子检查后汇总；**A1–A3 = 提示词 §6 的三项验收判据**：
  A1 发行包就绪 / A2 兼容矩阵与归属清单齐备 / A3 纯度门禁通过）；**MUST NOT** 由分散的检查各自打印 PASS
  （落点 **T049**）。
- **FR-015（证据可追溯）**：兼容矩阵**每一项** MUST 可追溯到 Q3 §3.4 裁定、上游 `路径:行号`、
  或对应 feature 的实测记录；MUST NOT 输出无依据的兼容性断言。
- **FR-016（不回退）**：本 feature MUST NOT 回退 B21F1 的 `[otlp]`、G23 的 `protobuf` SPDX 归一、
  G26 网络静态扫描例外、B19F1 的 L5 import 例外；MUST NOT 放宽任何既有依赖 / 网络 / 商标门禁。
- **FR-017（`[otlp]` 不误判）**：打包检查与纯度门禁 MUST 把 `[otlp]` 视为**唯一合法** extra；
  MUST NOT 因其存在而判定「v1.0 不允许 extra」；其余 extra 出现 ⇒ 失败。
- **FR-018（PNG 调用面不破）**：本 feature MUST NOT 改变 B23F1 的 `draw_mermaid_png()` 调用面
  （**零必需参数、返回 `bytes`**）；矩阵 MUST 记录 v1.0 占位 PNG 与 v2.0 `[png]` 升级路径。
  该不破坏性 MUST 由 `src/freegraph/` 零改动 + B23F1 既有 PNG 测试
  （`tests/contracts/test_graph_png.py`）共同判定。
- **FR-019（门禁编号零新增）**：本 feature MUST NOT 新增门禁编号；只更新**既有** G8 / G19 / G29
  的取行源（`README → COMPAT.md`，已登记为破冻结面）与文档落库；**MUST NOT** 放宽其
  覆盖面 / 列数 / 不重复 / affiliation 判据。

### Key Entities *(include if feature involves data)*

- **发行产物（Wheel / SDist）**：可发布到 PyPI 的构建结果；关键属性 = 文件清单、元数据、依赖声明、`py.typed`。
- **兼容矩阵行**：`COMPAT.md` 的一条记录；关键属性 = freegraph 符号 / API 元素、对应上游符号、等价程度（三档）、差异说明、证据来源。
- **第三方归属条目**：`THIRD_PARTY_NOTICES` 的一条记录；关键属性 = 项目、来源、许可证、引入方式、修改、版权声明保留位置。
- **能力处置条目**：README 表中的一行；关键属性 = 能力、Developer / Plus / Enterprise 三档、
  freegraph v1 处置（做 / 不做（v2）/ 永不做）、as-of 日期。
- **纯度门禁结果**：一次产物检查的结论；关键属性 = 产物名、类型（wheel / sdist）、违规项列表、退出码。
- **负向用例**：被故意污染的产物副本；关键属性 = 混入路径、期望失败、实际退出码。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001（发行包就绪）**：在隔离环境安装 wheel 成功，`import freegraph` 成功；基础依赖闭包
  `pip freeze` 仅含 `freegraph` 与安装器自身。
- **SC-002（纯度通过）**：`check_dist_purity.py dist/` 对 wheel + sdist **均返回退出码 0**；
  产物清单中仓库内容命中数为 **0**（判定时**豁免 `dist/.gitignore`**——它是 `uv build` 的目录标记，不是发行产物）。
- **SC-003（负向拦截）**：故意混入一个仓库文件后，纯度断言**退出码非 0**，且发布流水线在
  `uv publish` 之前中断（工作流步骤顺序可核对）。
- **SC-004（矩阵与归属齐备）**：`COMPAT.md` 覆盖 18 项（逐项可核对）+ **现有公开符号矩阵全量迁入**
  + **H-1…H-9 的矩阵落库（既有行更新 H-2/H-3/H-4/H-9 + 下游新增行 H-1/H-5/H-6/H-7/H-8）**，且 `Command` 行 = **部分等价**（含纠正 P3/`99d43aa` 漂移的来源注记；
  **Y-01 / Y-02 / Y-03** 的既有差异标注为 **DIFF**，**X-06** 只覆盖失败信号）；
  `THIRD_PARTY_NOTICES` 覆盖引入代码与 `[otlp]` 闭包；两文件均含 affiliation 免责声明；
  **并交付宪法原则 XI 的最小差分组 `B24F1-D-01…D-03`**（`tests/differential/test_b24f1_matrix_parity.py`；
  只断言 Y-01 / Y-02 / Y-03 既有差异，上游缺席 skip，**不改运行时**）。
- **SC-005（依赖与许可证）**：基础安装依赖闭包为**空集**；`pyproject.toml` 只有 `[otlp]` 一个 extra；
  **发行元数据中声明的依赖**（含 `[otlp]` 闭包）许可证 ∈ {MIT, Apache-2.0, BSD-2/3, PSF}；
  无 Elastic-2.0 / AGPL / SSPL。**开发 / 差分测试的 `dependency-groups`**（`dev` / `differential`）
  **不进发行包、不参与本判据**（其许可证仍由既有门禁约束）。
- **SC-006（`[otlp]` 可用且不污染）**：`pip install "freegraph[otlp]"` 成功；环境中**没有**
  `certifi` / `opentelemetry-exporter-otlp-proto-http` / `opentelemetry-exporter-otlp` **元包**
  （**精确包名**；`opentelemetry-exporter-otlp-proto-grpc` 是允许项，MUST NOT 用子串误判）。
- **SC-007（README 合规）**：README 为中文为主，且英文覆盖**关键段落**（独立实现声明 / 三条承诺 /
  安装与 `[otlp]` / 能力处置摘要 / `COMPAT.md` 链接）；**「中文为主」按 FR-006 的结构化判定**
  （英文仅覆盖上述关键段落、其余正文为中文；英文关键段落须有显式 `## English` / `[English]` 标注，
  非英文段不得连续 3 段纯英文）；含独立实现声明与三条承诺
  （**零账号（含零 license key） / 零出站 / 零第三方运行时依赖**）；**逐字复刻** §3.2 的
  **5 列**（能力 / Developer `$0` / Plus `$39/seat/月` / Enterprise / freegraph v1）**+ 8 行**
  能力处置表并附 as-of 日期；OTLP 段保留 **OpenLIT / Langfuse / Phoenix**
  三后端并列且**无默认推荐**；指向 `COMPAT.md` 的链接为**绝对 GitHub URL**；
  顶部状态说明与当前已交付能力一致（**无**「内核尚未实现 / 没有任何能力 / 请勿用于生产」类过时断言）；
  品牌资产扫描命中数为 **0**。
- **SC-008（人工验收）**：`harness/verification/B24F1/manual-verification.md` 存在且含
  **实际输出**（非「符合预期」），覆盖基座安装、纯度正向、纯度负向、`[otlp]` 安装、矩阵逐项核对；
  并含 **G8/G19/G29 追认**与**质量门禁 5 偏离 + B25F1 承接追认**；
  **MUST** 由可自动核验的**文档守卫断言**判定（存在 + 五段式 + 必需实测输出 + 非空），
  且守卫 MUST 核验 `harness/features/B25F1_双跑验收与迁移说明.md` 含「下游承接（B24F1）」
  与 **Y-01** / **真实模型轮** 字样（T047；B24F1 记录另含 **Y-02 / Y-03**）；
  **MUST NOT** 以「写记录 / 审计」任务冒充判据级覆盖（宪法 v1.13.0）。

---

## Assumptions

- **A-1（D3 已决 2026-11-05）**：`LICENSE` 保持 **MIT**（立项书 §12 D3 · 宪法「D3 已决」）；
  本 feature MUST NOT 切换为 Apache-2.0。
- **A-2（`Command` 行的等价程度口径 · 已由发起者拍板 2026-11-24）**：`Command` 行定稿为
  **部分等价**。依据：① 上游实测 `Command().goto == ()`，freegraph 为 `None`
  ——这是**成功路径可观察差异** ⇒ 标 **DIFF（Y-01）**，**不属「更严」**；
  ② B9F1 parity 的 X-1（非法 `goto` 目标）/ X-4（非 dict `update`）为**更严失败信号**（**X-06**）；
  ③ X-2 / X-3 的异常类型与上游不同（B9F1 的编号）。历史事实：B1F1 该行原为「部分等价」，
  **上游对齐批次 P3（commit `99d43aa`，2026-11-13）改为「行为等价」属未授权的漂移**；
  B22F1 的 `125ba0f` 仅追加泛型化措辞、未改第三列。本 feature 按发起者决定**恢复原值**并登记纠正，
  **不构成**对宪法原则 VIII「已发布事实」的改写（兼容矩阵是**活文档**，B24F1 起位于 `COMPAT.md`，不是 PyPI 元数据）。
  ⚠️ **Y-01 的处理**：B24F1 **只登记、不改运行时**（B1F1 冻结 `goto=None` 缺省；本 feature 的
  破冻结面追认已用于 G8/G19/G29，按「每 feature ≤1 次」不叠加）；**具名承接 = B25F1（M4）**
  在双跑验收 / 迁移说明中保留该记录，运行时对齐（若需）归 **v2 独立契约修订**；
  MUST 在 `manual-verification.md` 遗留问题中显式列出。发起者已于 2026-11-24 clarify 接受该既有偏离。
  `NodeFunc` 仍保持 **不支持**（H-2 的定稿口径不变）。
- **A-3（矩阵归属与发布形态 · 已由发起者拍板 2026-11-24）**：`COMPAT.md` = **唯一权威**的
  逐符号 / 逐项矩阵；**就兼容矩阵而言**，README = **§3.2 能力处置表（5 列逐字复刻）+
  免责声明 + 指向 `COMPAT.md` 的链接 / 摘要**（D7 的发布形态；README 仍保留
  OTLP / 依赖面 / 开发与验收等既有章节）。既有 README 完整符号表 MUST **迁入**
  `COMPAT.md`；README MUST NOT 维护第二份完整矩阵；两者 MUST 一致，MUST NOT 出现互相矛盾的两份矩阵。
  README 的 `COMPAT.md` 链接 MUST 为**绝对 GitHub URL**（COMPAT.md 不进发行包）。
- **A-4（版本号）**：本 feature 不负责确定最终发布版本；当前 `0.0.x` 占位版本可继续使用，
  版本决策归发布动作 / B25F1；本 feature 只保证「产物就绪」。
- **A-5（「两个包」口径）**：P1 的「`pip freeze` 只有两个包」指 `freegraph` + `pip`（安装器自身常驻）；
  构建工具链 / 隔离器的临时包不计入运行时依赖闭包。
- **A-6（18 项口径）**：18 项 = `harness/demo/target.py` 的 18 个 API 元素，裁定以
  `harness/reports/Q3-LangGraph的开源边界.md` §3.4 为唯一权威；MUST NOT 自行增删项。
- **A-7（README 收口 · 已由发起者拍板 2026-11-24）**：本 feature 交付 README 的发布基线，
  并**负责修正**顶部过时的「内核尚未实现 / 没有任何图运行时能力」类断言（保留占位版本客观描述）；
  最终文案润色可由 B25F1 收口，但本 feature 的 SC-007 判据不因此放宽。
- **A-8（门禁 7 的可达性 · 依宪法 v1.15.0 订正）**：兼容矩阵**早已落库**（`README.md` 的
  「API 兼容矩阵」章节 · **B2F2 交付**）⇒ 门禁 7 的「兼容矩阵已更新」判据**对后续 feature 可达**。
  本 feature **MUST NOT** 以「首次落库 / 物理不可达成」为由登记分阶段偏离；它只把**权威载体**
  从 README **迁移**到独立文件 `COMPAT.md`（**B24F1 起 `COMPAT.md` = 权威；README = 指针**）。
  B7F4 的登记项 PR-5 是 **2026-11-13 的历史登记**；
  宪法 **v1.15.0（2026-11-16）** 已明确订正「按 B24F1 / M4 才首次落库」的过期表述。
  **上位文档同步**：立项书 §6.2.1 第 6 条（「README 的 API 兼容矩阵」）与 D7 的能力处置表
  分工易混——自 B24F1 起，**能力处置表仍在 README**（D7），**逐符号 API 兼容矩阵位于
  `COMPAT.md`**；§6.2.1 第 6 条的文字已在本轮分析修复中同步，**T048** 负责实现期复核（不改变任何判据）。
- **A-9（不实现首次真实发布）**：PyPI 占位版已存在；本 feature 只验证「接入 + 负向拦截」，
  首次真实发布不在本 feature 范围。
- **A-10（纯文字产品名的允许口径）**：`pyproject.toml` 的 `keywords`（含 `langgraph`）与
  `description`（如 “drop-in replacement for the LangGraph Graph API”）属**互操作说明的
  nominative use**，**允许保留**；前提是 README 的独立实现 / 不构成 affiliation 声明齐备，
  且 MUST NOT 使用 logo / 品牌视觉 / 官方文案。若发起者要求更保守（移除相关关键字 / 措辞），
  须另起变更，本 feature 不擅自删除。
- **A-11（dev / differential 依赖的归属）**：`dependency-groups` 中的 `pytest` / `packaging` /
  `langgraph==1.2.11` 仅测试侧使用，**不进发行包**、不登记为发行依赖、不参与 SC-005 / FR-013
  的许可证白名单判据（沿用 B3F1 / B5F2 的既有口径）。

---

## 质量门禁偏离（2026-11-24 · 沿用 B19F1 / B20F1 / B20F2 / B21F1 先例 · 已追认）

> 依据宪法「质量门禁的分阶段落地与发起者追认」（v1.6.0）。本偏离**不降低**任何红线判据；
> 正式追认文字 MUST 落 `harness/verification/B24F1/manual-verification.md`。

| 项 | 内容 |
|---|---|
| 被偏离门禁 | **质量门禁 5**「人工验证记录，含真实模型一轮」 |
| 根因 | B24F1 是**发行 / 文档单元**（跨层 · 不新增运行时行为），**不交付 MVP 双跑轮**；真实模型轮是 **B25F1（M4）的 MVP 判据**（B25F1 SC-001 / A2），B24F1 无对应的运行期判据 ⇒ 按 v1.6.0「按里程碑不交付其前置能力」的同类处置，登记偏离并具名承接 **B25F1**。先例：B19F1 / B20F1 / B20F2 / B21F1 已按同一口径追认；本偏离**不降低**任何红线判据。 |
| 判据未放宽 | 本 feature 的人工记录仍按原则 V 五段式、含**实际输出**（隔离安装 `pip freeze` / 纯度正负向退出码 / `[otlp]` / 矩阵逐项核对）；文档守卫 T042 照常；质量门禁 1–4 / 6–7 照常。 |
| 承接方 / 机制 | **B25F1（M4 · 双跑验收与迁移说明）**：在 B25F1 的 fake / 真实模型两轮中覆盖 B24F1 的发行产物与 `COMPAT.md` 声明；承接条款 MUST 写入 `harness/features/B25F1_双跑验收与迁移说明.md` 的「下游承接（B24F1）」（**已在本轮分析修复中接线；T047 复核**），并由 B24F1 的文档守卫核验追认文字。 |
| 追认 | **已由发起者于 2026-11-24 确认**（B24F1 analyse 轮）；文字落 `harness/verification/B24F1/manual-verification.md`。 |

---

## Out of Scope（本 feature 明确不做）

- `target.py` 双跑验收与迁移说明（**B25F1**）。
- CI 发布流水线的**首次真实发布**（占位版已发布；本 feature 只接入门禁并验证负向用例）。
- Postgres / async / 子图 / 完整 Studio UI（v2）。
- LICENSE 的 MIT → Apache-2.0 切换（**D3 已决 2026-11-05：保持 MIT**）。
- 免费文档站（README + 仓库文档为主）。
- 任何运行时 / 契约 / 持久化 / 可观测语义变更（`src/freegraph/` 零改动）。
- **修复既有行为面差异 Y-01 / Y-02 / Y-03**（`Command.goto` 缺省 `()` vs `None`；`get_state` 无快照 `None` vs 上游空 `StateSnapshot`；`Send` 不可变 vs 上游可变）——本 feature **只登记**，
  不改运行时；运行时对齐（若需）归 **v2 独立契约修订**。**Y-01 的文档记录由 B25F1（M4）承接**；
  **Y-02 / Y-03 在本 feature 的 `COMPAT.md` 与 `manual-verification.md` 登记，不写 B25F1 承接**。
