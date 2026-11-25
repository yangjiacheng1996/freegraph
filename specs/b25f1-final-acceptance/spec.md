# Feature Specification: B25F1 · 双跑验收（fake CI + 真实模型人工）+ 迁移说明 + README 收口

**Feature Branch**: `b25f1-final-acceptance`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_specify` 钩子；既有 feature 同样在 `main` 上开发）

**Created**: 2026-11-25

**Status**: Accepted（人工验收通过 2026-11-26）

**Input**: User description: `harness/features/B25F1_双跑验收与迁移说明.md` —— 完成 **v1.0 的最终验收**：让固定脚本 `harness/demo/target.py` **原样**跑通两轮（① fake 模型 · CI 可自动化；② 真实模型 · 人工验收），并产出《人工验收记录》、**迁移说明**与最终 **README**。判定：**双跑通过；框架零出站断言通过**。

> **范围提醒**：本 feature 是**交付 / 验收单元**（跨层 · 层 =「—」），**不新增运行时能力**，
> **不新增契约条目**，**不新增门禁编号**。它**只**兑现立项书 §4.2 的 S4 / S6 与 §4.3 的 18 项裁定：
> ① 用**外部注入**让固定脚本原样跑 fake 轮（CI）；② 人工跑**真实模型轮**并留证据；
> ③ 提供**只观测不阻断**的零出站监测与本 feature 的断网等价性验证；
> ④ 补齐 M3 的 `harness/demo/diagnostics.py`；⑤ 交付迁移说明与最终 README。
> **MUST NOT** 修改 `harness/demo/target.py`（宪法原则 III 的只读基准，diff 必须为空）；
> **MUST NOT** 修改 `src/freegraph/` 的任何运行时 / 契约 / 持久化 / 可观测语义；
> **MUST NOT** 放宽任何既有判据。
> **不实现**：真实模型之外的 provider 矩阵（属 freechain）、异步调用（v2）、前端 UI（v2 / B26）、
> 评测 / 数据集（永不做）、Postgres / 子图 / 完整 Studio（v2）。

---

## 承接条款（上游 feature → 本 feature）

> 宪法「跨 feature 承接的接线通则」：上游 feature 指名本 feature 的跨 feature 义务
> MUST 在本 spec 落成 **FR + 裁定**；**只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽判据**。

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B8F1 → B25F1** | **M4** | **fake 注入与路由函数正交**：路由函数是**用户函数**；注入机制 MUST NOT 让注入只对节点生效而对路由函数失效；**MUST NOT** 在注入层**改写**路由函数的返回值语义。 | `specs/b8f1-conditional-edges-fresh-read/spec.md` 下游承接 **D-5** | FR-001 · FR-002 · Assumption A-04 |
| **H-2** | **B23F1 → B25F1** | **M4** | **PNG 实测记录**：fake 轮与真实轮 MUST 记录 `draw_mermaid_png()` 的实际输出（字节数 / PNG 结构判据结果 / 框架出站 = 0）；MUST NOT 用「符合预期」替代实测；真实轮受环境限制时 MUST 登记**环境偏离**，MUST NOT 用「未验证」替代。`target.py` 仍为只读基准。 | `specs/b23f1-draw-mermaid-png-offline/spec.md` 下游承接 **D-1** · `contracts/png-contract.md` §9.2 | FR-012 · FR-016 · SC-004 |
| **H-3** | **B20F1 → B25F1** | **M4** | **本地 JSONL trace 真实轮**：真实模型轮 MUST 在至少一次调用中注入 `FileTraceStore(directory=...)`；记录 `trace-<run_id>.jsonl` 实测证据（文件数 / `kind="span"` 行 / `kind="trace_record"` 行 / 模型 span 的 `parent` 指向节点 span / C23 四项关联键）；记录「框架出站 == 0」。 | `specs/b20f1-local-trace-jsonl/spec.md` 质量门禁 5 偏离登记 | FR-012 · FR-013 · SC-004 |
| **H-4** | **B20F2 → B25F1** | **M4** | **trace 查询双后端真实轮**：真实模型轮 MUST **分别（两次独立运行）**注入 `FileTraceStore(directory=...)` 与 `SqliteTraceStore(database=...)`；记录两者 `query()` 的四类过滤 / 组合 / 空过滤器的**实际输出**（含结果条数与 `json.dumps` 证据）。两次运行 MUST 使用同一真实模型接入，并捕获 `run_id` / `thread_id` / 时间窗。 | `specs/b20f2-trace-query-sqlite/spec.md` 质量门禁 5 偏离登记 | FR-012 · FR-013 · SC-004 |
| **H-5** | **B21F1 → B25F1** | **M4** | **OTLP 真实轮**：真实模型轮 MUST 显式构造并注入 `OtlpExporter`（`endpoint=` 或 `exporter=` 模式）；记录实际 OTLP 导出证据（接收端 / 收到的 span 数 / `name` / `trace_id` / `parent` / `gen_ai.*` 属性）；用户显式启用的 OTLP 端点不计入框架出站。 | `specs/b21f1-otlp-export/spec.md` 质量门禁 5 偏离登记 | FR-012 · FR-014 · SC-002 · SC-004 |
| **H-6** | **B15F1 → B25F1** | **M4** | **SQLite 检查点真实轮复验**：真实模型轮 MUST 注入 `SqliteSaver.from_conn_string(path)`；记录 `get_tuple` / `get_state` / `get_state_history` / `stream(checkpoints)` 的**实际输出**（持久化往返、历史数量 / 倒序、`tasks` / `interrupts`、事件数与 payload）。本 feature 做**跨 feature 复验（不是替代）**。 | `specs/b15f1-sqlite-saver-state-history/spec.md` 质量门禁 5 合规 | FR-012 · FR-015 · SC-004 |
| **H-7** | **B14F1 → B25F1** | **M4** | **发布前人工验收清单**：B14F1 的 `harness/verification/B14F1/manual-verification.md`（含真实 `MemorySaver` 恢复侧实测）与 `harness/verification/B14F1/acceptance.py` MUST 纳入本 feature 的发布前人工验收清单；**MUST NOT** 回改 B14F1 记录，**MUST NOT** 把「自动验收通过」冒充人工验收。 | `specs/b14f1-checkpointer-memory-saver/spec.md` 下游承接 **D-07** | FR-008 · FR-019 · SC-004 |
| **H-8** | **B16F1 → B25F1** | **M4** | **时间旅行覆盖 + 复验**：专用探针 / 诊断验收脚本 MUST 覆盖历史点重放、`update_state` 覆盖 / 归约、分叉后原历史不变、中断组合；MUST 对 B16F1 的真实模型轮做**跨 feature 复验（不是替代）**；MUST NOT 修改 `target.py`。 | `specs/b16f1-update-state-time-travel/spec.md` 下游承接 **D-02** | FR-015 · SC-003 · SC-004 |
| **H-9** | **B24F1 → B25F1** | **M4** | **发行产物 / 矩阵真实轮 + Y-01 文档记录**：真实模型轮 MUST 覆盖 B24F1 的发行产物与 `COMPAT.md` 声明；迁移说明 / 验收记录 MUST 保留 `Command.goto` 缺省 `()` vs `None` 的既有 **DIFF（Y-01）** 并提示 v1 行为；运行时对齐归 **v2 独立契约修订**。 | `specs/b24f1-packaging-compat-matrix/spec.md` 质量门禁偏离 · **Y-01** | FR-009 · FR-012 · FR-017 · SC-005 |
| **H-10** | **B5F2 → B25F1** | **M4** | **模型工厂钩子**：B5F2 的差分夹具预留「模型工厂」钩子（恒空；非空即显式失败；图规格恒为纯本地节点）⇒ 本 feature MUST 提供 **fake 模型工厂**，并让差分夹具能跑**模型形状**的图规格。本 feature **只新增模型形状入口** `build_model_graph_spec`，**MUST NOT** 放宽 B5F2 既有钩子的拒绝语义。 | `specs/b5f2-sparse-state-read/spec.md` **FR-036 / 裁定 26** | FR-001 · FR-018 · SC-006 |
| **H-11** | **B7F1 → B25F1** | **M4** | **质量门禁 3 / 5 的固定脚本承接**：`target.py` **原样可跑**与**真实模型一轮**在本 feature 前的里程碑物理不可达成 ⇒ 本 feature MUST 承接**双跑验收**（① fake 轮 + ② 真实模型轮），并另做 freegraph 与 LangGraph 的**上游差分跑**（差分佐证，不替代双跑），**MUST NOT** 改动固定脚本任何一行。 | B3F1 **裁定 22** · `specs/b7f1-superstep-loop/spec.md` | FR-001 · FR-011 · FR-018 · FR-020 · SC-001 · SC-005 |

---

## Clarifications

### Session 2026-11-25

- Q: CI 轮如何在不改 `target.py` 的前提下替换模型？ → A: **测试层猴补** `langchain.chat_models.init_chat_model`（返回实现 `invoke()` 的 `FakeModel`），并同时提供等价的外部注入入口（如 `sitecustomize.py`）供固定脚本子进程使用；`import` 后替换 `target.model` / `target.model_with_tools` 仅作**备选**，不作主路径。注入代码 **MUST 只存在于测试 / 验收层**，MUST NOT 成为 `freegraph` 运行时依赖。
- Q: 「双跑」到底指哪两轮？ → A: **① fake 轮（CI 自动化）** 与 **② 真实模型轮（人工）**；此外，为证明「只换包名即可跑通」，本 feature MUST 用同一 fake 输入在 freegraph 与上游 LangGraph 上**同跑并比对**（差分佐证，**不替代**双跑）。
- Q: 退出码如何区分「环境未就绪」与「断言失败」？ → A: **`0 = PASS` / `1 = 断言失败` / `2 = 环境未就绪`**。缺 `freegraph` / 缺 `langchain` / 缺 `IPython` / 缺真实模型凭据或网络均归 **2**；只有「能力已就绪但契约未兑现」才归 **1**。
- Q: 真实模型轮使用哪个厂商 / 端点？ → A: 由**环境显式配置**且仅用于人工轮；本 feature **不实现 provider 矩阵**。验收记录 MUST 写明厂商 / 端点 / 模型标识；凭据缺失或网络受限时 MUST 登记**环境偏离**（继续记录已能实测的部分），**MUST NOT** 用「未验证」替代。
- Q: 零出站如何归因？ → A: socket 夹具只包装 `socket.connect` / `socket.create_connection`，**只记录不阻断**；按 **G27「第一个非标准库帧」** 归因（裁定 19）：从栈顶跳过全部标准库帧，第一个非标准库帧在 `freegraph/` 包内 ⇒ 判「框架出站」，否则判「用户出站」。**只对框架出站断言 = 0**；模型厂商端点、用户显式启用的 OTLP 端点等属**用户出站**，**记录在案但不判失败、不设目标白名单**。
- Q: README 与 `COMPAT.md` 的分工？ → A: **`COMPAT.md` 是唯一权威**的逐符号矩阵；README **只保留**能力处置表、三条承诺、独立实现声明与指向 `COMPAT.md` 的**绝对链接**，**MUST NOT** 复制第二份完整矩阵。
- Q: `diagnostics.py` 的 API 形态以谁为准？ → A: 以 M3 各 feature 已锁定的形态为准：`compile(tracer=TraceSink)`（B19F1）、`FileTraceStore(directory=...)` / `SqliteTraceStore(database=...)` 与 `query(TraceQuery | None) -> list[dict]`（B20F1 / B20F2）、`freegraph.persistence.MemorySaver`（B14F1）、`update_state(config, values, as_node=None) -> RunConfig`（B16F1）、`SqliteSaver.from_conn_string(path)`（B15F1）、`OtlpExporter(endpoint=/exporter=)`（B21F1）。
- Q: 真实模型轮的多个观测 / 持久化组件应如何组织？ → A: **选项 A（混合）**——固定脚本**原样**真实跑一轮，承担 A2 / 零出站 / PNG；另用一份**专用探针脚本**（同一 agent 循环形状、真实模型）承担 trace / OTLP / checkpoint / 时间旅行 / query 过滤证据。这样不改 `target.py`，也避免猴补 `compile` / `invoke` 造成「表面没改、实际改了」的争议。
- Q: 真实模型轮的「用户出站」允许口径应如何判定？ → A: **选项 C（宽松白名单）**——freegraph 是**通用型图框架**，不限定只用于智能体开发；因此**只对框架出站断言 = 0**，用户出站**逐条记录但不判失败**，**MUST NOT** 对用户出站的目标做白名单校验。人工轮仍**记录**实际发生的大模型端点 / OTLP 端点等信息，供追溯，但不作为通过条件。
- Q: 「断网等价性」验证轮应如何实现？ → A: **选项 A（双层）**——默认在进程内禁用 `socket` 连接（可移植、无特权）；Linux CI 若具备 `unshare -n` / 容器网络隔离能力，再加跑一次 OS 级断网作为**增强证据**；不具备时登记**环境偏离**，不判失败。
- Q: 真实模型轮应通过哪种接入方式调用固定脚本硬编码的模型？ → A: **选项 D（环境自适应）**——优先**官方直连**（官方 SDK + 官方环境变量）；受限时允许操作者使用**兼容网关**。验收记录 MUST 写明**实际路径**与原因，**MUST NOT** 把网关写成官方直连；本 feature **不**扩大 provider 矩阵。
- Q: `target.py` 的「只读基准 diff 断言」以什么为基线？ → A: **选项 A（双重基线）**——① 仓库内固定 `target.py` 的 **SHA-256**（测试常量或 `.sha256` 文件），逐内容比对；② CI 再与**基线 ref**（如 `origin/main`）做 `git diff`。两者都过才算；**MUST NOT** 只依赖 `git diff HEAD`（无法发现已提交篡改）。
- Q: 立项书 §4.2 S4 / §9.2 原写 `messages` 长度 = 3，与固定脚本实际行为不符，如何处理？ → A: **以 4 为准**（`HumanMessage` + `AIMessage(tool_call)` + `ToolMessage` + 最终 `AIMessage`；`SystemMessage` 不进入状态）。**立项书 §4.2 S4 / §9.2 已事实性更正为 4**，并注明「3 只是 System + AI + Tool 的三点投影」；本决策由发起者 2026-11-25 确认。
- Q: 两个 `acceptance.py` 的职责如何区分？ → A: `harness/demo/acceptance.py` = **四组验收脚本（graph_core / agent_loop / visualization / diagnostics）的编排器**；`harness/verification/B25F1/acceptance.py` = **B25F1 一键验收**（A1/A3/A4/A5，`--real` 跑 A2）。spec / plan / tasks MUST 使用全路径，MUST NOT 用裸 `acceptance.py` 指代。
- Q: 零出站的发起方归因以哪条规则为准？ → A: **G27 的「第一个非标准库帧」规则**（裁定 19）：从栈顶向下跳过全部标准库帧，第一个非标准库帧在 `freegraph/` 包内 ⇒ 框架出站；否则用户出站。spec / plan / tasks MUST 统一该口径。
- Q: `diagnostics.py` 与立项书「验收脚本集四组」如何对齐？ → A: **四组 = graph_core / agent_loop / visualization / diagnostics**；`diagnostics.py` 是其中**第四组**（不另计为「四组之外」），`harness/demo/acceptance.py` 是编排器、自身检查计入退出码。立项书 / README 的旧表述按本 spec 落成此定义（立项书已于 B25F1 同批修订；README 由 T039 修订）。
- Q: 立项书原写「人工轮允许模型厂商端点一条，断言除该条外为空」，与已定的用户出站口径冲突，如何处理？ → A: **以本 spec 的 C 口径为准**——freegraph 是通用型图框架；只断言**框架出站 = 0**，用户出站**逐条记录、不判失败、不设目标白名单**。**立项书 §9.2 / D12 与宪法 v1.18.0 已同步更新**，把「允许一条」改为「记录在案、不作为通过条件」。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CI 自动跑通验收基线 (Priority: P1)

作为项目发起者，我希望每次提交 CI 都自动用 **fake 模型**原样跑一遍固定脚本，从而**回归不退化**。

**Why this priority**: 这是 MVP 的**最终自动化判据**（A1 / A5）。它同时守住「固定脚本零修改」与
「工具循环 / C4 / C8 语义不被静默破坏」，是 v1.0 收口的基石。

**Independent Test**: 在干净环境执行 CI 验收任务 → 固定脚本退出码 0 →
断言 `messages` 长度 == 4、`llm_calls == 2`、工具结果 == 7、返回状态含 `messages` 与 `llm_calls`
两个键；再断言 `target.py` 的双重基线通过（SHA-256 一致 + 基线 ref diff 为空）。

**Acceptance Scenarios**:

1. **Given** 干净环境与已安装的 `freegraph` / `langchain`，**When** CI 用 fake 注入原样执行
   `harness/demo/target.py`，**Then** 脚本退出码为 0，且四条固定断言点全部成立。
2. **Given** 同一 fake 注入，**When** 检查导入链，**Then** `freegraph` 运行时从未 import
   `langchain` / `langchain_core`（注入只发生在测试 / 验收层）。
3. **Given** 仓库工作树，**When** 按双重基线检查 `harness/demo/target.py`（SHA-256 + 基线 ref diff），
   **Then** 两者均一致 / 为空。

---

### User Story 2 - 人工用真实模型跑一遍 (Priority: P1)

作为项目发起者，我希望在**真实模型**上再跑一遍，确认端到端真实行为（不只是 fake）。

**Why this priority**: 宪法原则 V 规定人工验收是**最终验收标准**；fake 只能证明契约形状，
不能证明真实 provider 的端到端行为。

**Independent Test**: 在登记的环境（OS / Python / 依赖 / 环境变量清理方式）里配置真实模型凭据，
**两段式**组织：① 原样执行固定脚本（A2 / 零出站 / **B23F1 PNG 实测**）；② 用专用探针脚本
（同一 agent 循环形状、真实模型）注入 B15F1 / B16F1 / B20F1 / B20F2 / B21F1 要求的可观测 /
持久化组件，并记录各自实测证据。两段均在同一个登记环境内完成。

**Acceptance Scenarios**:

1. **Given** 一个可用的真实模型端点，**When** 原样执行固定脚本，**Then** 脚本退出码 0，
   `messages` / `llm_calls` / 工具结果与 fake 轮的契约断言一致，且**实际输出非空**并写入验收记录。
2. **Given** 真实模型轮，**When** 查看验收记录，**Then** 「框架出站」为 **0**，用户出站逐条记录；
   记录**写明**实际发生的大模型端点（以及用户启用的 OTLP 端点，若启用），但不以其目标作为通过条件。
3. **Given** 真实模型凭据缺失或网络受限，**When** 执行人工轮，**Then** 记录登记**环境偏离**
   （含已完成与未完成的范围），**MUST NOT** 写「未验证」或「符合预期」替代实测。
4. **Given** 真实模型轮注入 `FileTraceStore` / `SqliteTraceStore`（**两次独立运行**）/
   `OtlpExporter` / `SqliteSaver`，**When** 查看记录，**Then** 各组件均附**非空实测输出**
   （文件数 / 行数 / `query()` 结果条数与 `json.dumps` / span 数 / 历史条目等），并注明来源。

---

### User Story 3 - 能证明 freegraph 自己没有偷偷联网 (Priority: P1)

作为用户，我希望能拿到「框架出站 = 0」的可判定证据。

**Why this priority**: 「零出站」是三条对外承诺之一；没有可判定证据，它就只是口号。

**Independent Test**: 运行**只观测不阻断**的 socket 监测夹具，按 G27「第一个非标准库帧」归因；
断言「框架出站」计数 == 0；用户出站逐条记录但不判失败。

**Acceptance Scenarios**:

1. **Given** fake 轮与依赖断言轮，**When** 查看监测记录，**Then** 「框架出站」条目数为 **0**。
2. **Given** 真实模型轮，**When** 查看监测记录，**Then** 「框架出站」为 **0**；用户出站**逐条记录**
   且可以指向任意目标（freegraph 是通用型图框架，**MUST NOT** 对用户出站设目标白名单），
   记录中写明实际发生的大模型端点 / OTLP 端点等信息。
3. **Given** 监测夹具运行期间，**When** 用户节点发起连接，**Then** 连接被**放行**（夹具不阻断），
   仅被记为用户出站，且**不判失败**。

---

### User Story 4 - 从 LangGraph 迁过来的人知道要改什么 (Priority: P2)

作为 LangGraph 用户，我需要一份迁移说明（哪些 API 同名、哪些要改、差异在哪）。

**Why this priority**: 迁移说明是 v1.0 对外可用性的最后一公里；缺失会让「兼容目标」无法落地。

**Independent Test**: 打开 `harness/proposals/更名与迁移说明.md` 的迁移章节与最终 README，
逐项核对同名 API、需改 API、已知差异（含 `Command.goto` 的 **Y-01**）、`COMPAT.md` 链接。

**Acceptance Scenarios**:

1. **Given** 一位 LangGraph 用户，**When** 阅读迁移说明，**Then** 能区分「同名直接可用」、
   「同名但行为有差异」、「需改写」三类，并知道去 `COMPAT.md` 查逐符号细节。
2. **Given** 迁移说明与验收记录，**When** 搜索 `Command.goto`，**Then** 能找到
   `()` vs `None` 的既有 **DIFF（Y-01）** 及 v1 行为提示。
3. **Given** 最终 README，**When** 查找兼容矩阵，**Then** 只看到能力处置表与
   `COMPAT.md` 的**绝对链接**，没有第二份完整逐符号矩阵。

---

### Edge Cases

- **`target.py` 含 `IPython.display` 导入**：缺 `IPython` 时属**环境未就绪（退出码 2）**，
  MUST NOT 判断言失败，也 MUST NOT 修改脚本规避。
- **`init_chat_model` 注入时机**：固定脚本在导入期即解析 `langchain.chat_models`；
  注入 MUST 在其导入前生效（子进程 / `sitecustomize` / conftest 顺序），否则会退化为真实网络调用。
- **fake 只产出文本、不产出 `tool_calls`**：判失败——验收基线会退化为「单轮无工具」，
  无法覆盖工具循环 / C4 / C8。
- **fake 输出序列不足 2 轮**：判失败（第 1 轮 `tool_call` → 第 2 轮最终答案，缺一不可）。
- **fake 的 `tool_call.id` 缺失或与 `ToolMessage.tool_call_id` 不匹配**：判失败。
- **工具结果不是 7**：判失败（`add(3, 4)` 的期望值）。
- **`messages` 长度不是 4**：判失败（初始 HumanMessage + AIMessage(tool_call) + ToolMessage + 最终 AIMessage）。
  **口径自查（上游已定）**：`SystemMessage` 只进入模型输入、**不进入状态**（固定脚本的
  `MessagesState.messages` 用 `operator.add` 累积）⇒ 简报中的「3（System + AIMessage(tool_call) +
  ToolMessage）」是**三点投影**，不是最终状态长度；长度断言 MUST 以上游实测的 **4** 为准。
- **`invoke()` 只返回 `messages` 而缺 `llm_calls`（或反之）**：判失败（完整状态契约）。
- **注入顺带替换路由函数 / 改写其返回值**：判失败（违反 H-1 正交性）。
- **监测夹具改成「拦截」**：判失败——宪法原则 V 要求**只观测不阻断**；用户节点正常出网不得被阻断。
- **把模型厂商端点误判为框架出站**：MUST 按 G27「第一个非标准库帧」归因；误判会导致真实轮假红。
- **对用户出站目标做白名单校验**（只要不是大模型端点就判失败）：违反 A3 口径 ⇒ 判实现错误；
  freegraph 是通用型图框架，用户出站只记录、不判失败、不设目标白名单。
- **真实轮无凭据 / 断网**：登记**环境偏离**；不得把「未跑到」写成「通过」。
  若真实模型轮**完全无法执行**（既无官方直连凭据、也无可用兼容网关），本 feature **MUST NOT**
  宣布完成——A2 是硬判据。环境偏离只豁免**条件增强项**（如 OS 级断网）或**已完成的子项**，
  **不豁免真实模型轮本身**（宪法原则 V）。
- **`LANGSMITH_*` 残留**：三轮（⓪ 依赖断言 / ① CI / ② 人工）MUST 在**清空全部 `LANGSMITH_*`**
  的干净环境下进行；未清空判环境未就绪。
- **断网等价性轮**：进程内禁用 `socket` 连接时核心用例 MUST 全绿；若某用例偷偷出网 ⇒ 暴露为失败。
  OS 级断网（`unshare -n` / 容器网络隔离）属**条件增强**：环境不具备时登记环境偏离，
  MUST NOT 把「跑不了 OS 级」写成「没验证」，也 MUST NOT 因此判失败。
- **`harness/demo/acceptance.py` 缺 `diagnostics.py`**：编排器 MUST 将 diagnostics 纳入并通过；
  缺失判失败而非跳过。
- **单组脚本能跑、编排器不能跑**：判失败——验收以编排器退出码为准。
- **退出码把「环境未就绪」压成「断言失败」**：判失败（0 / 1 / 2 必须可区分）。
- **`target.py` 被格式化 / 换行 / 注释改动**：即使语义不变，SHA-256 或基线 ref diff 不一致 ⇒
  判失败（只读基准）。
- **只靠 `git diff HEAD` 检测 `target.py`**：只能发现未提交改动，已提交篡改会漏检 ⇒ 判实现错误；
  MUST 使用「SHA-256 + 基线 ref diff」双重基线。
- **基线 ref 不可用**（浅克隆 / 无 `origin/main`）：MUST 明确登记环境偏离并保留 SHA-256 断言，
  MUST NOT 静默跳过或把「无法比较」当成「通过」。
- **README 重新引入完整兼容矩阵**：判失败（`COMPAT.md` 唯一权威）。
- **README 的 `COMPAT.md` 用相对路径**：判失败（PyPI 落地页会 404，必须绝对 URL）。
- **验收记录用「符合预期」替代实测输出**：判失败（证据门禁）。
- **把兼容网关写成官方直连**：判失败（证据门禁）；记录 MUST 写明实际接入路径与原因。
- **真实轮顺带扩大 provider 矩阵**（例如声称支持多家后端）：判失败；本 feature 只验证**一条**
  环境显式配置的接入路径。
- **把自动 acceptance 通过冒充人工验收**：判失败（原则 V；B14F1 记录不可回改）。

---

## Upstream Parity *(mandatory — 宪法 v1.9.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11**（`pyproject.toml` 钉死 · 差分夹具核实版本）·
`langgraph` **1.2.19**（兼容矩阵既有行引用版本，仅复述）·
`langchain-core` **1.6.3 / 1.7.6** · `langchain` v1（固定脚本自身依赖，测试 / 人工轮使用）
（取证于 2026-11-05 / 2026-11-06 / 2026-11-24 / 2026-11-25）

> **版本口径（MUST）**：差分测试与新增行统一以 **`langgraph==1.2.11`** 为准；换版本 MUST
> 重新核实全部锚点。本 feature **不新增运行时行为**，因此本节聚焦于**固定脚本所依赖的
> 上游语义**与**验收方法**是否忠实；每行锚点以本仓库 `harness/demo/target.py` 的实际行号为准。

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | 固定脚本 18 项 API 元素 | `harness/demo/target.py` 第 22-23 / 26-29 / 33-63 / 69 / 73-80 / 86-101 / 109-117 / 126-137 / 142-158 / 163 / 166-170 行；裁定见 `harness/reports/Q3-LangGraph的开源边界.md` §3.4 | 7 项同名同签名 + 1 项方法名同名（PNG 占位）+ 10 项行为等价 / 原样承载（逐项见 B24F1 的 18 项覆盖表） | SAME / DIFF | #13 PNG 占位为 DIFF（B23F1）；#14–#18 不属 freegraph 范围，原样承载 |
| P-02 | 工具调用循环语义（`llm_calls` / 工具结果 / 消息累积） | 上游 Quickstart 同款循环；`langgraph/graph/state.py:131` / `:928` / `:1177-1188`；`langgraph/pregel/main.py:3783` | B7F3 / B8F1 / B9F1 已交付；`state.get('llm_calls', 0)` 为普通 dict 读取 | SAME | — |
| P-03 | 条件边 fresh 读（C8） | `langgraph/graph/state.py:982-989` | 条件边路由对最新 state 求值；`tool_calls` 真值判定为鸭子类型 | SAME | H-1：fake 注入 MUST 与路由函数正交 |
| P-04 | `get_graph(xray=True).draw_mermaid_png()` | `langgraph/pregel/main.py:845`；上游默认经 `langchain_core` 请求 `mermaid.ink` | v1.0 返回合法占位 PNG（零出站、离线不阻断）；真实渲染归 v2.0 | DIFF | 零出站硬约束；B23F1 已登记（本 feature 只实测记录） |
| P-05 | 模型工厂 / fake 注入 | **无上游同名物**（验收方法自研） | 测试层猴补 `init_chat_model` + `FakeModel`；仅测试 / 人工轮使用 | SAME（对脚本兼容性）/ DIFF（方法自研） | 不改变上游脚本；注入不改运行时 |
| P-06 | 零出站观测方法 | **无上游同名物**（宪法原则 V 自研） | socket 只观测不阻断 + **G27「第一个非标准库帧」归因**；仅对框架出站断言 0 | DIFF（方法自研） | 属原则 XI「必须自研区」③「上游没有的能力」 |
| P-07 | `Command.goto` 缺省值（迁移文档事实） | `langgraph/types.py:821-840` | freegraph `None`（上游 `()`） | DIFF（**Y-01**） | 既有成功路径差异；B24F1 已登记，本 feature 在迁移说明 / 验收记录**保留**并提示 v1 行为；对齐归 v2 |

### 差分场景组 *(mandatory)*

> 本 feature **不新增运行时行为**，但宪法原则 XI 的可验证出口仍是**差分场景组**。
> 本组用于证明「固定脚本只换包名即可跑通」与「fake 轮 / 真实轮的契约断言成立」。
> `B25F1-D-01…D-04` 默认落在 `tests/differential/test_b25f1_final_acceptance.py`；
> **D-04 的模型工厂断言**落在 `tests/differential/test_b25f1_model_factory.py`；
> **D-03 是只读基准守卫**（非上游差分场景，可复用 T010 的断言）。
> 上游缺席即 `pytest.skip`，沿用 B5F2「缺席即 skip」纪律。

| # | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 |
|---|---|---|---|
| **B25F1-D-01** | 同一 fake 输入在 freegraph 与 LangGraph 上跑固定脚本 | 节点序列 / `messages` 长度 == 4 / `llm_calls` == 2 / 工具结果 == 7 / 最终状态键集一致 | SAME |
| **B25F1-D-02** | 工具循环 · C4 · C8 回归 | 第 1 轮产生 `tool_calls` → 工具节点执行 → 第 2 轮文本答案；`state.get('llm_calls', 0)` 与条件边 fresh 读均正确 | SAME |
| **B25F1-D-03** | 固定脚本只读基准（守卫） | `harness/demo/target.py` 双重基线通过（SHA-256 一致 + 基线 ref diff 为空） | SAME（零改动） |
| **B25F1-D-04** | 新增模型形状入口（`build_model_graph_spec`） | 经 `build_model_graph_spec(..., model_factory=fake_factory)` 注入后，差分夹具能跑**模型形状**的图规格；`build_graph_spec` 的纯本地规格在 `model_factory` 非空时仍 `GraphSpecError` | SAME |

> **B5F2 钩子口径（H-10）**：B5F2 交付时模型工厂钩子恒空 ⇒ 非空即**显式失败**；
> 本 feature **不改该旧钩子**，而是新增 `build_model_graph_spec` 承载模型形状规格 ⇒
> MUST NOT 让旧钩子在模型形状下重新变成「恒空即通过」。

### 偏离登记 *(仅限三类 · 其余一律照抄)*

> **本 feature 不新增任何运行时 / 契约 / 持久化 / 可观测偏离**（不修改 `src/freegraph/`）。
> 下表登记的是**验收方法层**的自研点与**既有**成功路径差异的记录义务；后者不属三类，
> 仅因本 feature 被具名承接而**复述**（不占新编号、不改判据）。

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| X-01 | 必须自研区（上游没有的能力） | 零出站观测夹具 / fake 注入机制（仅测试与验收层，非运行时） | 上游无同名物；`target.py` 只读，只能靠外部注入；观测必须「只观测不阻断」 | 本 feature（B25F1）· 不新增门禁编号 |
| — | 既有成功路径差异（非「更严」· 仅复述） | **Y-01** `Command.goto` 缺省 `()` vs `None` | B24F1 已登记；本 feature **只记录 Y-01、不改运行时** | 运行时对齐归 **v2 独立契约修订**；**Y-01 的文档承接 = 本 feature** |

> **Y-02 / Y-03** 由 **B24F1 自登记**，本 feature **不承接、不复述**；仅 **Y-01** 的文档记录由本 feature 承接。

### 破冻结面的回溯修订清单 *(若有)*

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| `tests/differential/spec_builder.py`（B5F2 / B8F1 差分夹具） | **只增** `build_model_graph_spec(...)`（FR-018 / SC-006，H-10）；`build_graph_spec` 的纯本地 `model_factory` 非空拒绝语义**不变** | B8F1 A10「零改动清单」把 `spec_builder.py` 从零改动文件移出，改由 `tests/differential/test_differential.py` 的既有拒绝语义测试保护（**只增不改**） | B25F1（H-10）· 发起者 2026-11-25 |
| 其余冻结面 | `src/freegraph/**` / `harness/demo/target.py` / 契约 / 门禁判据**零改动** | — | — |

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001（fake 模型注入）**：系统 MUST 提供 **fake 模型注入**（猴补
  `langchain.chat_models.init_chat_model` 并返回实现 `invoke()` 的 `FakeModel`），且注入只存在于
  测试 / 验收层；**MUST NOT** 修改 `harness/demo/target.py`；注入机制 MUST 与路由函数**正交**
  （MUST NOT 只对节点生效、MUST NOT 改写路由函数返回值语义）。
- **FR-002（fake 能力与固定输出序列）**：fake MUST 能产生 `tool_calls`，并按固定 **2 轮**序列返回：
  ① 第 1 轮 `tool_calls=[{name:'add', args:{'a':3,'b':4}, id:'call_1'}]`；
  ② 第 2 轮最终文本答案（与脚本的「Add 3 and 4.」对齐）。
- **FR-003（固定断言点）**：CI 验收 MUST 断言：`messages` 长度 == 4（初始 HumanMessage +
  AIMessage(tool_call) + ToolMessage + 最终 AIMessage；`SystemMessage` 只进入模型输入、不进入状态）、
  `llm_calls` == 2、
  工具结果 == 7、`invoke()` 返回完整状态（含 `messages` 与 `llm_calls` 两个键）。
  任一不成立 ⇒ 退出码 1。
- **FR-004（零出站监测夹具）**：系统 MUST 提供**只观测、不阻断**的零出站夹具：
  包装 `socket.connect` / `socket.create_connection` 以记录目标与调用栈，**放行**所有连接；
  按 **G27「第一个非标准库帧」** 归因（裁定 19）：从栈顶跳过全部标准库帧，第一个非标准库帧
  在 `freegraph/` 包内 ⇒ 「框架出站」，否则「用户出站」；**只对框架出站断言 = 0**；
  用户出站**逐条记录但不判失败**，且 **MUST NOT** 对其目标做白名单校验
  （freegraph 是**通用型图框架**，不限定只用于智能体开发）。
- **FR-005（断网等价性）**：系统 MUST 提供**断网等价性**验证轮，采用**双层**实现：
  ① **进程内层（必做）**——在进程内禁用 `socket` 连接，核心用例（fake 轮 / `graph_core` /
  `agent_loop` / `visualization` / `diagnostics`）MUST 全绿；
  ② **OS 级（条件增强）**——Linux CI 若具备 `unshare -n` / 容器网络隔离能力，MUST 再加跑一次
  OS 级断网并记录结果；不具备该能力时 MUST 登记**环境偏离**，MUST NOT 因此判失败。
- **FR-006（diagnostics.py）**：系统 MUST 补齐 `harness/demo/diagnostics.py`，覆盖
  trace / checkpoint / 时间旅行的可诊断性验收，并纳入 `harness/demo/acceptance.py` 编排。
- **FR-007（退出码与编排）**：`harness/demo/acceptance.py` MUST 编排**四组验收脚本**
  （`graph_core` / `agent_loop` / `visualization` / `diagnostics`）并全绿；target fake 步作为
  **A1 独立步骤**运行，**不计入四组**。`harness/verification/B25F1/acceptance.py` 是
  **B25F1 一键验收入口**（A1/A3/A4/A5，
  `--real` 跑 A2），**不替代**前者。两者退出码约定 **`0 = PASS` / `1 = 断言失败` /
  `2 = 环境未就绪`**，三者 MUST 可区分。
- **FR-008（人工验收记录）**：系统 MUST 产出
  `harness/verification/B25F1/manual-verification.md`，含五要素：验证环境（OS / Python / 依赖 /
  环境变量清理方式）、验证步骤、**实际输出**、结论、遗留问题；并附三项附件：
  ① 依赖断言轮输出；②「框架出站 = 0」监测记录；③ 反向断言结果。
  记录中的事实 MUST 带来源；遗留问题 MUST 逐条列出。
- **FR-009（迁移说明）**：系统 MUST 交付**迁移说明**（LangGraph → freegraph 的差异清单），
  至少区分「同名直接可用 / 同名但行为有差异 / 需改写」三类，并保留 **Y-01** 的 v1 行为提示；
  逐符号细节 MUST 指向 `COMPAT.md`，MUST NOT 复制完整矩阵。
- **FR-010（最终 README）**：系统 MUST 交付最终 README：快速上手 + 三条对外承诺
  （零账号（含零 license key） / 零出站 / 零第三方运行时依赖）+ 能力处置表 + 独立实现声明；
  README MUST 保留 **`COMPAT.md` 唯一权威矩阵的绝对链接**
  （`https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md`），
  **MUST NOT** 重新引入完整兼容矩阵。
- **FR-011（固定脚本零改动 · 双重基线）**：CI MUST 以**双重基线**断言 `harness/demo/target.py`
  未被修改：① **内容真值**——仓库内固定其 **SHA-256**（测试常量或 `.sha256` 文件），逐内容比对；
  ② **历史真值**——与**基线 ref**（如 `origin/main`）做 `git diff`，结果 MUST 为空。
  两者都过才算通过；**MUST NOT** 只依赖 `git diff HEAD`（无法发现已提交篡改）。
  任何格式化 / 换行 / 注释改动同样判失败。
- **FR-012（真实模型轮证据与组织形态）**：真实模型轮 MUST 采用**两段式**组织：
  ① **固定脚本段**——原样跑通 `target.py`，承担 A2 / 零出站 / PNG 证据；
  ② **专用探针段**——用一个同一 agent 循环形状、真实模型的专用脚本，注入 B15F1 / B16F1 /
  B20F1 / B20F2 / B21F1 要求的可观测 / 持久化组件并产出对应证据。
  **MUST NOT** 通过猴补 `compile` / `invoke` 把组件塞进固定脚本段（避免「表面没改、实际改了」）。
  两段均 MUST 记录**实际输出**（非「符合预期」）：模型标识 / 端点、**接入路径**（官方直连 /
  兼容网关）、最终消息、工具结果、结论；框架出站 MUST == 0，用户出站**逐条记录但不判失败**。
  接入方式 MUST **优先官方直连**；受限时 MAY 使用兼容网关，但记录 MUST 写明实际路径与原因，
  **MUST NOT** 把网关写成官方直连，也 **MUST NOT** 因此扩大 provider 矩阵。
  若兼容网关需要 `base_url`，MAY 在真实轮**外部包装** `init_chat_model` 仅做接线；
  该包装 MUST NOT 伪造模型输出，且 MUST 在验收记录中写明（`target.py` 仍零改动）。
  凭据 / 网络受限时 MUST 登记**环境偏离**，MUST NOT 用「未验证」替代；
  环境偏离 MUST 写明已完成与未完成范围。
- **FR-013（承接 B20F1 / B20F2 · trace 实测）**：真实模型轮 MUST **分别（两次独立运行）**注入
  `FileTraceStore(directory=...)` 与 `SqliteTraceStore(database=...)`，记录 JSONL 证据
  （文件数 / `kind="span"` 行 / `kind="trace_record"` 行 / 模型 span `parent` 指向节点 span /
  C23 四项关联键）与两者 `query()` 的四类过滤 / 组合 / 空过滤器实际输出
  （结果条数 + `json.dumps` 证据）。
- **FR-014（承接 B21F1 · OTLP 实测）**：真实模型轮 MUST 显式构造并注入 `OtlpExporter`
  （`endpoint=` 或 `exporter=`），记录实际导出证据（接收端 / span 数 / `name` / `trace_id` /
  `parent` / `gen_ai.*` 属性）；用户显式启用的 OTLP 端点**不计入框架出站**。
- **FR-015（承接 B15F1 / B16F1 · 持久化与时间旅行）**：真实模型轮 MUST 在**专用探针段**注入
  `SqliteSaver.from_conn_string(path)` 并记录 `get_tuple` / `get_state` / `get_state_history` /
  `stream(checkpoints)` 的实际输出；专用探针 / 诊断验收脚本 MUST 覆盖历史点重放、
  `update_state` 覆盖 / 归约、分叉后原历史不变、中断组合；对 B15F1 / B16F1 的真实轮做
  **跨 feature 复验（不是替代）**。上述覆盖 MUST NOT 通过猴补 `compile` / `invoke` 塞进固定脚本段。
- **FR-016（承接 B23F1 · PNG 实测）**：fake 轮与真实轮 MUST 记录 `draw_mermaid_png()` 的实际输出
  （返回类型 / 字节数 / PNG 结构判据结果 / 框架出站 = 0），MUST NOT 写「符合预期」替代实测。
- **FR-017（承接 B24F1 · 发行产物与 Y-01）**：真实模型轮 MUST 覆盖 B24F1 的发行产物与
  `COMPAT.md` 声明（基础安装零依赖、`[otlp]` 唯一 extra、纯度门禁通过等）；迁移说明与验收记录
  MUST 保留 **Y-01**（`Command.goto` 缺省 `()` vs `None`）并提示 v1 行为；运行时对齐归 v2。
- **FR-018（承接 B5F2 / B7F1 · 模型工厂与上游差分跑）**：系统 MUST 提供 fake 模型工厂，
  并**经新增入口** `tests/differential/spec_builder.py::build_model_graph_spec(..., model_factory=...)`
  让差分夹具能跑**模型形状**的图规格；**MUST NOT** 放宽 `build_graph_spec` 的纯本地
  `model_factory` 非空拒绝语义（B5F2 FR-036 / 裁定 26 保持不变）。
  系统 MUST 在 freegraph 与 LangGraph 上**同跑并比对**固定脚本（**上游差分跑**；节点序列 /
  最终状态），证明「只换包名即可跑通」；MUST NOT 修改仓库内固定脚本。
  **LangGraph 侧的运行方式** MUST 在验收记录中注明，且 MUST 属于以下两类之一：
  ① 在**临时目录**生成只替换包名的副本后执行；② 用**运行时模块别名**把 `freegraph` 指向
  `langgraph` 后执行。两类都 MUST 保证仓库内 `target.py` 零改动。
- **FR-019（承接 B14F1 · 发布前人工验收清单）**：发布前人工验收清单 MUST 纳入
  B14F1 的 `harness/verification/B14F1/manual-verification.md`（含真实 `MemorySaver` 恢复侧实测）
  与 `harness/verification/B14F1/acceptance.py`；**MUST NOT** 回改 B14F1 记录，
  **MUST NOT** 把自动验收通过冒充人工验收。
- **FR-020（依赖红线与反向断言）**：freegraph 自身依赖闭包 MUST NOT 含 `langsmith` /
  `langchain*` / `langgraph*`；运行期 `sys.modules` MUST NOT 出现 `langchain` / `langchain_core`
  （CI 静态扫描 + 运行时检查）；该反向断言 MUST 作为交付证据写入验收记录。
- **FR-021（干净环境）**：三轮验收（⓪ 依赖断言轮 / ① CI 轮 / ② 人工轮）MUST 在
  **清空全部 `LANGSMITH_*`** 的干净环境下进行；验收记录 MUST 写明清空方式。
- **FR-022（不新增运行时改动）**：本 feature MUST NOT 修改 `src/freegraph/` 的运行时 / 契约 /
  持久化 / 可观测语义；MUST NOT 新增门禁编号；MUST NOT 放宽任何既有判据。

### Key Entities *(include if feature involves data)*

- **固定脚本（只读基准）**：`harness/demo/target.py`；LangGraph Quickstart 的机械替换版，
  动它即违反宪法原则 III；验收以**双重基线**为准（SHA-256 一致 + 基线 ref diff 为空）。
- **Fake 模型**：测试 / 验收层的模型替身；必须实现 `invoke()`、能产生 `tool_calls`，
  并按固定 2 轮序列返回；不得成为运行时依赖。
- **固定输出序列**：第 1 轮 tool_call（`add(3, 4)`，`id='call_1'`）→ 第 2 轮最终文本答案。
- **固定断言点**：`messages` 长度 == 4（System 不进入状态）、`llm_calls` == 2、工具结果 == 7、完整状态含两键。
- **零出站监测记录**：按「框架出站 / 用户出站」归因的连接记录；只对框架出站断言 0。
- **人工验收记录**：`harness/verification/B25F1/manual-verification.md`；五要素 + 三附件。
- **迁移说明**：LangGraph → freegraph 的迁移差异清单；指向 `COMPAT.md` 作为唯一权威。
- **最终 README**：快速上手 + 三条承诺 + 能力处置表 + 独立实现声明 + `COMPAT.md` 绝对链接。
- **diagnostics 验收脚本**：`harness/demo/diagnostics.py`；覆盖 trace / checkpoint / 时间旅行。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001（双跑通过）**：fake 轮（CI 自动化）与真实模型轮（人工）均**原样**跑通固定脚本，
  四条固定断言点全部成立。
- **SC-002（零出站断言通过）**：「框架出站」计数 == **0**；用户出站**逐条记录但不判失败**，
  且**不按目标设白名单**（freegraph 是通用型图框架）；记录中写明实际发生的大模型端点 /
  OTLP 端点等信息。
- **SC-003（验收脚本集全绿）**：四组验收脚本（`graph_core` / `agent_loop` / `visualization` /
  `diagnostics`）经 `harness/demo/acceptance.py` 编排后退出码 **0**；断网等价性轮的
  **进程内层**同样全绿，OS 级增强层按环境条件记录。
- **SC-004（人工验收记录完整）**：五要素（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）齐备 +
  三项附件（依赖断言输出 / 出站监测 / 反向断言）齐备；含 B15F1 / B16F1 / B20F1 / B20F2 /
  B21F1 / B23F1 / B24F1 要求的**非空实测证据**；含 **B14F1 的 `manual-verification.md` 与
  `harness/verification/B14F1/acceptance.py` 引用**；含**接入路径**（官方直连 / 兼容网关，
  gateway 不得写成官方直连）；
  环境受限处已登记**环境偏离**而非「未验证」。
- **SC-005（文档与只读基准）**：迁移说明与最终 README 齐备；README 保留 `COMPAT.md`
  **绝对链接**且**不复制**完整兼容矩阵；`target.py` 的**双重基线**均通过（SHA-256 一致 +
  基线 ref diff 为空）；迁移说明与验收记录保留 **Y-01** 的 v1 行为提示。
- **SC-006（模型工厂与差分佐证）**：**新增的模型形状入口** `build_model_graph_spec`
  能注入 fake 模型工厂并跑通**模型形状**图规格；B5F2 的 `build_graph_spec` 对**非空**
  `model_factory` 仍显式失败；同一 fake 输入在 freegraph 与 LangGraph 上的**上游差分跑**
  比对通过（上游缺席即 skip，不判失败）。

### Acceptance Criteria（= 立项书 §5.2 B25F1 小目标）

> 小目标原文：MVP 完成：双跑通过（**CI 轮经 `conftest.py` 猴补 `init_chat_model` 注入 fake，
> 固定输出序列 + 断言点见 §9.2**），框架零出站断言通过（只观测归因）。

| # | 判据 | 判定方式 | 对应需求 |
|---|---|---|---|
| **A1** | **fake 轮通过** | CI 任务：固定脚本原样跑通，断言点全成立 | FR-001 / FR-002 / FR-003 |
| **A2** | **真实模型轮通过** | 人工验收记录（含实际输出） | FR-008 / FR-012 |
| **A3** | **框架零出站断言通过** | 监测记录「框架出站 = 0」；用户出站逐条记录、不判失败、不设目标白名单 | FR-004 / FR-012 / FR-021 |
| **A4** | **验收脚本集全绿** | `harness/demo/acceptance.py` 退出码 0（含 diagnostics） | FR-006 / FR-007 |
| **A5** | **`target.py` 未被修改** | **双重基线**：SHA-256 一致 + 基线 ref diff 为空 | FR-011 / FR-022 |

> **A2 的严格判定属发布 / 人工门禁**：常驻 CI 采用 T019 的 skip 规则（记录未就绪或仅有环境偏离时
> skip），避免永久红 CI（宪法 v1.13.0）；发布门禁以**真实轮证据存在性**独立阻断，**MUST NOT**
> 用空记录冒充绿。真实模型轮未完成 ⇒ 仍不得宣布 v1.0 收口。

---

## Assumptions

- **A-01（环境）**：CI 与人工轮均具备 CPython `>=3.11`；**CI 的 Linux x86 全量档**
  （`ubuntu-24.04` 3.11/3.14）装有 `langchain` / 上游 `langgraph==1.2.11`（差分组）与 `IPython`；
  其余档不安装这三者 ⇒ 相关用例 `importorskip`（skip，非失败）。真实轮另有可用的模型凭据与网络。
  缺任一项 ⇒ 退出码 2 或环境偏离登记。OS 级断网（`unshare -n` / 容器网络隔离）属**条件增强**，
  不具备时只登记环境偏离。
- **A-02（注入层）**：fake 注入与零出站夹具只存在于 `tests/` / `harness/`，**不进入发行包**；
  `freegraph` 运行时的第三方依赖闭包保持为空。
- **A-03（fake 消息对象）**：fake 返回的消息对象具备固定脚本所需的鸭子类型字段
  （`tool_calls`、`content`、`pretty_print()` 等）；实现可复用 `langchain` 的消息类。
- **A-04（路由正交）**：固定脚本的 `should_continue` 是用户函数；注入不改变其输入 / 返回值语义，
  也不改变条件边对最新 state 的求值方式（B8F1 D-5）。
- **A-05（零出站观测）**：「框架出站」按 **G27「第一个非标准库帧」** 归因（裁定 19），
  已由宪法 **v1.18.0** 的原则 V 锁定；**只观测不阻断**，不阻断用户代码出网。
- **A-06（真实模型来源）**：真实模型轮由环境显式配置的**单一**接入执行，**优先官方直连**；
  受限时 MAY 使用兼容网关，但记录 MUST 写明实际路径与原因。本 feature **不**实现 provider 矩阵
  （属 freechain），也不承诺多后端一致性；**MUST NOT** 把网关写成官方直连。
- **A-07（文档权威）**：`COMPAT.md` 是逐符号兼容性的**唯一权威**；README 与迁移说明只做摘要与链接。
  B24F1 已迁源完成，本 feature 不回退该结构。
- **A-08（无新增契约 / 门禁）**：本 feature 不新增契约条目、不新增门禁编号；所有断言都是对
  既有 S4 / S6 与 18 项裁定的**兑现**，失败即表示既有能力未达成，而非新增要求。
- **A-09（诊断 API 形态）**：`diagnostics.py` 只使用 M3 各 feature 已锁定的 API 形态；
  若某形态与实现不符，按「契约优先」修正实现而非绕过脚本。
- **A-10（记录不可回改）**：既有 `harness/verification/<feature>/manual-verification.md` 为历史事实，
  本 feature 只新增自己的记录并引用它们，**MUST NOT** 回改（原则 VIII）。
- **A-11（消息长度口径 · 上游已定）**：固定脚本的最终 `messages` 长度 = **4**
  （Human + AI(tool_call) + ToolMessage + AI 最终答案）；`SystemMessage` 不进入状态。
  **立项书 §4.2 S4 / §9.2** 与简报中的「3（System + AI + Tool）」仅是三点投影，
  **不**作为长度断言；立项书已事实性更正为 4。该口径由 `operator.add` 归约与
  上游同款 Quickstart 行为直接决定，**不需再澄清、只照抄**。
