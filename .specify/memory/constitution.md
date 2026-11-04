<!--
=== SYNC IMPACT REPORT (temporary scratch material — remove before committing) ===

Constitution update: 0.0.0（未发布草案）-> 0.0.1（项目更名 + 原则 III 验收 API 名同步 + 原则 V 门禁 4 方法措辞修正）

- Version change: 0.0.0（未发布草案）-> 0.0.1
- 版本号口径：**项目尚未开工（32 个 Phase 全部未开始），宪法未经发起者批准**
  （Ratified 仍为 TODO），因此保持 **`0.0.x` 预发布编号**，不标 1.x —— 1.x 会误导读者
  认为「已批准且已定版」。首次经发起者批准时定版为 **1.0.0**。
- Bump type: **PRE-1.0 修订（0.0.0 -> 0.0.1）**。本次改动含「对既有原则的实质性扩充」
  （原则 III 的具体验收 API 名随项目更名而变），按 MAJOR/MINOR/PATCH 策略本应记 MINOR；
  但因**尚无任何已实现特性、宪法亦未批准**，故按 0.x 预发布语义记为 0.0.1，
  待批准时统一定版。**原则 III 的实质要求不变** —— 仍为「只换包名、不改脚本」的机械替换验收。
- 变更了什么：
  1. 项目名 PROJECT_NAME：opengraph -> freegraph；姊妹项目 openchain -> freechain
     （全文 token 同步替换：opengraph×45 / openchain×13 处）。
  2. 原则 III 的具体 API 名：`from opengraph.graph import ...` ->
     `from freegraph.graph import ...`；验收基准路径不变（`harness/demo/target.py`）。
  3. 原则 VII / 项目定位 / 质量门禁 / 目录约定中的项目名同步。
  4. 原则 V 门禁 4 的方法性措辞：socket 夹具「拦截」->「只观测不阻断 + 按发起方归因」
     （零出站证据改为「由框架自身发起的出站数 = 0」，不阻断用户代码出网）。
- 为什么：
  - `opengraph`（Erik Rivera，"A module to parse the Open Graph Protocol" 0.5）与
    `openchain`（"Openchain Library" 0.1.0rc3）在 PyPI 上均已被**永久占用**，
    不可转让、不可复用（实测 2026-11-03，`https://pypi.org/pypi/opengraph/json`、
    `https://pypi.org/pypi/openchain/json`）。
  - `freegraph` **已于 2026-11-04 由本项目在 PyPI 占位发布 v0.0.1**
    （owner = PyPI 账号 `yangjiacheng1996`，发行名 = 导入名 = `freegraph`；
    发布通道 = GitHub Actions Trusted Publishing（OIDC），无需 API token / 密码）；
  - `freechain` **亦已于 2026-11-04 由同一账号占位发布 v0.0.1**
    （依赖 `freegraph>=0.0.1`；两个 PyPI 名称均已锁定）；
    `github.com/freegraph` 与 `github.com/freechain` 已由发起者注册。
  - 原则 V 的方法性措辞修正理由：opengraph/freegraph 是**函数胶水 / 工作流框架**，
    承诺「自己不会偷偷联网」而非「你的程序不许联网」；拦截式守卫会阻断用户节点的
    正常出网，属反直觉设计（见立项书 §10 的 R11）。
- 受影响的原则与特性：
  - 原则 III（验收契约优先）：仅具体 API 名变化，实质要求不变。
  - 原则 V（人工验收是最终验收标准）：门禁 4 的**方法**变化，「MUST 有零出站的可判定
    证据」这一 Requirement 不变；原则 I 的实质要求（自身零出站、断网可用）不变。
  - 原则 VII（职责边界与内核契约）：项目名与姊妹项目名变化；C1-C26 契约清单本身不变。
  - 原则 I / II / IV / VI / VIII / IX / X：不变（红线与实现无关）。
  - 特性：**32 个 Phase 均未开工**，无已实现特性需要迁移。
- 迁移方案：
  1. `harness/demo/target.py` 第 103 行 import 机械替换（本次唯一的脚本改动，
     属「只换包名」性质的**平移**，非削弱）；文件头新增来源与更名记录说明。
  2. 全部调研报告 / 提案 / 指南 / 笔记中的项目名 token 同步替换；**原始结论、事实、
     证据、数字一律未改动**（仅项目标识 token）。
  3. 立项书新增 §12.1「已关闭事项」，记录 D10（发行名 / 导入名 / 项目名）决议。
  4. `harness/proposals/更名与迁移说明.md` 记录完整迁移清单与取证。
- Deferred items / follow-up TODOs:
  - TODO(RATIFICATION_DATE): 初始宪法尚未由发起者批准；批准日填实（ISO YYYY-MM-DD）。
  - 原则 VII 的三项契约缺口（本地 trace 存储与查询 / span 关联键 / 事件通道标识）
    仍待按 Governance 修订流程增补（立项书 §5.8.3）。
  - 立项书评审 1 的 H / M / L 级条目尚未逐条处置。
- Notes:
  - No bracket tokens of the form ALL_CAPS_IDENTIFIER remain.
  - Cited research artefacts verified present: harness/reports/ Q1-Q9 + 00 overview (10 份)；
    Q8 C1-C26 契约表与立项书 §5.3 已对齐（评审 1 的 C1 已处置）。
  - `harness/docs/`（官方文档镜像，318 篇）保持只读，未做任何改动。

=== END SYNC IMPACT REPORT -->
-->

# freegraph Constitution

## Core Principles

### I. 零 LangSmith 依赖（NON-NEGOTIABLE）

freegraph 的代码、依赖树、配置与网络行为中，**不得存在任何 LangSmith 痕迹**。

- 依赖树中**不得出现** `langsmith` 包（须可由 `pip show` / `pipdeptree` 举证）。
  **推论（Q3 实证）**：`langchain-core` 的 `Requires-Dist` 硬依赖 `langsmith`（非 extras），
  故「依赖树无 `langsmith`」⟺「依赖树无 `langchain-core`」。二者是同一条红线，**MUST NOT** 只挡一层。
- 代码中**不得读取** `LANGSMITH_API_KEY` / `LANGSMITH_TRACING` / `LANGSMITH_ENDPOINT` / `LANGSMITH_PROJECT` 等环境变量。
- **不得**向 `smith.langchain.com` / `api.smith.langchain.com` / `beacon.langchain.com` / `*.langchain.com`
  或任何 LangChain 遥测端点发起出站请求。
- **零出站是本原则的真正边界，超出 LangSmith 范围的第三方 SaaS 同样禁止**：
  `mermaid.ink`（LangGraph 的 `draw_mermaid_png()` 默认渲染服务，Q3 实测每次调用必外呼）**MUST NOT** 被默认启用。
- **不得**在无 LangSmith 账号、无 API Key、断网环境下出现功能降级。

**Rationale**：LangSmith 的付费墙正是本项目要剥离的对象。「不共存」是本项目与 LangSmith 的**竞争前提**，
若内核仍隐式依赖 LangSmith SDK，则「剥离」无从谈起。反面教材是 LangChain 自身的实现：
`langgraph-api` 的 `config/__init__.py:675-677` 写着「if langsmith api key is set, enable tracing
unless explicitly disabled」——**API key 存在即自动开 tracing**。freegraph 必须反过来：
**环境变量存在也不得改变任何行为**，除非用户显式传入 tracer 对象。

**Requirement**：**MUST NOT** 引入 `langsmith` / `langchain-core` 依赖（含任何 extra 引入的传递依赖）、
**MUST NOT** 读取 `LANGSMITH_*` / `LANGCHAIN_*`、**MUST NOT** 向 `*.langchain.com` 或 `mermaid.ink` 出站。
每个特性的 PR 与 CI 都必须复核本条；违反即为阻断性缺陷，不接受「临时豁免」。

### II. 内核纯净：零 LangChain 依赖

freegraph **只做图运行内核**，核心层**不得 import langchain**，**依赖声明中也不得出现 `langchain-*`**。
对外只接受**鸭子类型**。

- 消息对象：任何具备 `.tool_calls` 属性的对象；`tool_calls` 为 list，元素为
  `{"name": str, "args": dict, "id": str, "type": "tool_call"}`（OpenAI 风格，通用协议）。
  freegraph **MUST NOT** 依赖 `.content` / `.id` / `.tool_call_id` 的具体语义，也 **MUST NOT** 强制转换用户传入的对象。
- 模型：任何提供 `invoke(input) -> 消息对象` 的可调用对象。
- 工具：任何提供 `name`（str）、`invoke(args) -> Any`、`description` 的可调用对象。
  **注意**：`args` / `id` 是 **tool_call 字典**的字段，**不是**工具对象的属性——实现时**MUST NOT** 混淆。
- 路由函数：任何返回节点名或结束标记（`END`）的可调用对象；**MUST** 支持 `path_map` 的 list 与 dict 两种形式。
- 状态 schema：使用标准 `Annotated` + 归约器（如 `operator.add`）表达，**不得**自带一套并行状态类型体系。
- 状态语义**MUST** 与 LangGraph 行为等价（Q8 契约 C1–C8），其中两条最易实现错、**MUST** 有独立回归测试：
  - **C4 稀疏状态**：节点入参是**普通 `dict`**，且**只包含当前有值的 channel**。
    空 channel 的 key **MUST NOT** 出现在入参中（否则 `state.get(key, default)` 返回 `None` 而非 `default`）。
  - **C8 条件边读 fresh 状态**：路由函数**MUST** 能读到「当前值 + 本节点本次写入」。

**Rationale**：freechain（LangChain 替代层）需要在 freegraph 之上重建模型抽象、工具、消息与 agent 装配。
若内核绑死 langchain，freechain 就被绑死，两项目分层随之失效。反之，Q8 已证明
LangGraph 对 `langchain_core` 的 135 处引用只集中在 4 个接缝（`RunnableConfig` / `Runnable` /
`Graph` / callbacks-tracers），**这 4 个接缝由 freegraph 自有类型替代即可完全脱钩**。

**Requirement**：**MUST NOT** 在核心层 import 或声明依赖 `langchain` / `langchain-core` / `langchain-*`；
**MUST** 以鸭子类型承载上层对象，**MUST NOT** 强制转换用户传入的消息对象；
**MUST** 保持 C1–C8 状态语义等价，**MUST** 为 C4 与 C8 保留回归测试。

### III. 验收契约优先：`harness/demo/target.py` 原样可跑

`harness/demo/target.py` 是 freegraph 的 **MVP 验收契约**，是**只读基准**，任何特性都不得修改它。

- freegraph 必须提供与 LangGraph Graph API **同名同签名**的接口。Q3 逐项裁定后，以下 **7 项 MUST 同名同签名**
  （其余 11 项 API 元素 MUST 行为等价或原样承载，**MUST NOT** 要求 freegraph 懂 LangChain 消息/工具类型）：
  1. `freegraph.graph` 导出 `StateGraph` / `START` / `END`（`START='__start__'`、`END='__end__'`）
  2. `StateGraph(schema)`——只传 schema 一个位置参数
  3. `add_node(name, fn)`——位置参数 `(str, Callable)`
  4. `add_edge(src, dst)`——`(str | list[str], str)`，链式返回
  5. `add_conditional_edges(src, path_fn, path_map)`——`path_map` 支持 list 与 dict
  6. `compile()`——无参可调用
  7. `compiled.invoke({"messages": [...]})`——**MUST 返回带 `messages` 键的完整状态**（不是仅新增消息）
- 归约器语义、`state.get(key, default)`、节点返回部分状态字典时的合并规则、
  `messages[-1].tool_calls` 的条件路由判定，均必须与 LangGraph 一致（详见原则 II 的 C4 / C8）。
- 该脚本自带的 `langchain.*` 导入是**脚本自身**的要求，不构成 freegraph 的依赖要求；
  freegraph 只需**能处理**这些对象（见原则 II）。
- 图可视化若不阻断执行：`get_graph` 的等价导出（mermaid 文本 / PNG 渲染）**MUST** 提供；
  若 freegraph 不自行渲染 PNG，**MUST** 给出明确的替代调用方式与迁移说明。
- **PNG 渲染的硬约束（Q3 实测）**：`target.py` 第 144 行的 `draw_mermaid_png()` 位于第 149 行的 `invoke()` **之前**。
  LangGraph 的实现默认请求公网 `https://mermaid.ink`，离线环境**必然抛异常**（实测
  `ValueError: Failed to reach https://mermaid.ink API`）→ **脚本会在到达验收点之前中断**。
  因此 freegraph 的 `draw_mermaid_png()` **MUST NOT** 在无网络时抛出阻断性异常
  （**MUST** 返回占位结果或抛出可捕获异常）；`draw_mermaid()`（纯 mermaid 文本）**MUST** 完全本地、必然成功、零出站。

**Rationale**：这是「能否不依赖 LangChain 与 LangSmith 而独立跑通」这一目标的唯一可判定形式。
验收标准一旦可被随手修改，项目的存在理由就失去锚点。

**Requirement**：**MUST NOT** 修改 `harness/demo/target.py`；**MUST** 以「只换包名，不改脚本」的方式通过验收。
验收契约的**细化**允许，**削弱**不允许。

### IV. 可诊断性是一等功能（NON-NEGOTIABLE）

不牺牲调试体验。Graph 的运行轨迹（trace）、状态快照（state）、中断（interrupt）、重放（time-travel）
**必须可见、可查、可回溯**。

- 图运行时的每一次节点执行都必须产生可观测记录，**MUST** 包含：节点名、输入状态、输出状态、耗时、错误。
- 中断与恢复（interrupt / resume）、状态回溯（time-travel）**MUST** 可用。
- 可观测协议**MUST** 采用 OpenTelemetry 兼容的追踪协议与语义约定（semantic conventions），
  以便复用现成面板，而不是自造私有格式。属性命名**SHOULD** 对齐 OTel GenAI semconv（`gen_ai.*`）。
- 可视化层**MUST NOT** 阻断执行；可视化不可用时，核心执行**MUST** 继续。
- **技术路线已选定（Q6 裁定）：路线 B —— OTel 兼容追踪协议 + 内嵌轻量可视化 UI。**
  路线 A（自研整套 Studio / 追踪后端，245–415 人日）**MUST NOT** 采用。
  v1 的可视化**MUST** 限定为三件套：
  1. **图视图**——mermaid 文本渲染，纯本地、零出站；
  2. **trace 时间线 / 详情**——本地存储（文件 / SQLite 后端）；
  3. **状态快照 + checkpoint 历史 + 回放入口**。
  freegraph **MUST NOT** 在 v1 内建评测平台（Evaluation / Datasets / Annotation Queue / Prompt Hub）。
- **后端对接政策**：`freegraph` **MUST** 以 OTLP 等标准协议输出，用户**MAY** 自行接入
  OpenLIT（Apache-2.0、无功能门、部署最轻）、Langfuse（MIT 核心）或 Phoenix。
  **MUST NOT** 内嵌 Phoenix——其许可证为 Elastic-2.0，明文禁止「provide the software to third parties
  as a hosted or managed service」（详见原则 IX）。
- **独占性论据（Q6）**：**没有任何现成 OSS 提供 LangSmith Studio 那种「交互式图运行时 IDE」**
  （Langfuse / Phoenix / OpenLIT 的 agent graph 都只是从 trace 还原的**只读调用图**，
  不能改 prompt、不能跑图、不能 time-travel）。这正是 freegraph 值得自研的部分，**MUST NOT** 放弃。

**Rationale**：诊断能力是 LangSmith 的主要卖点，也是本项目决定开源替代的部分。
把它降级为「以后再说」等于抹掉项目一半的价值主张。

**Requirement**：**MUST** 在 v1 交付中提供 trace / state / interrupt / time-travel 四类能力的最小可用实现；
**MUST** 按路线 B 的三件套范围实现可视化；**MUST NOT** 走路线 A；**MUST NOT** 内嵌 Elastic-2.0 组件。

### V. 人工验收是最终验收标准

自动测试通过**不等于**验收通过。每个特性**MUST** 有人工验证记录。

- 人工验证记录**MUST** 落在 `harness/features/<feature>/` 下。
- 记录**MUST** 写明：验证环境、验证步骤、实际输出、结论、遗留问题。
- MVP 验收基线**必须**跑两遍且都通过：
  1. **fake / 伪模型**跑一遍（CI 可自动化，用于回归）；
  2. **真实模型**再跑一遍（人工验收，用于确认端到端真实行为）。
- 上述两次验证**MUST** 在**不设任何 `LANGSMITH_*` 环境变量**的干净环境下进行，
  **并且 MUST** 有「零出站」的可判定证据：**SHOULD** 采用 socket guard 夹具
  （拦截所有非 localhost 的 `socket.connect`，断言拦截列表为空）——Q3 调研已验证该方法可行且可复用为 CI 断言。

**Rationale**：本项目要替代的是「跑起来对不对」这件事，自动断言无法覆盖语义正确性；
而 LangSmith 式的诊断能力恰恰依赖真实运行轨迹，只测不跑等于自欺。
「零出站」同理——**不设 env 不等于没外呼**：Q3 实测显示，一旦设置 `LANGSMITH_TRACING=true`，
`langchain-core` 会真的向 `api.smith.langchain.com` 上报 run（被拦截后打印
`Failed to get info from https://api.smith.langchain.com`）。

**Requirement**：**MUST NOT** 将「CI 通过」作为特性验收完成的唯一依据；
**MUST** 在特性目录留下人工验证记录后方可宣布完成。

### VI. 规格驱动开发（Speckit）

本项目全程采用 **OpenCode + Speckit** 编写代码。每个特性走标准流程：

```
proposal → spec → tasks → 实现 → (人工验证) → 验收
```

- 每个特性**MUST** 先有 proposal（`harness/proposals/`）与 spec，再进入 tasks 与实现。
- tasks **MUST** 可逐条勾选、可追溯到 spec 条目。
- 调研产物**MUST** 先落 `harness/reports/`，结论**MUST** 再转入 `harness/proposals/` 变成设计提案，
  **MUST NOT** 用未落盘的结论直接进入实现。
- 文档与代码**MUST** 同批提交；**MUST NOT** 出现「先写代码后补规格」。

**Rationale**：本项目的核心资产是「可审计的契约」（零依赖红线、API 同名对齐）。
若开发过程不可追溯，这些契约会在迭代中悄悄失守。

**Requirement**：**MUST** 走完整流程；**MUST NOT** 在无 spec 的情况下写实现代码。

### VII. 职责边界与内核契约

本仓库**只做 freegraph（图运行内核）**。freechain（LangChain 替代层）是**后续独立项目**，
基于 freegraph 构建，不在本仓库范围内实现。

- freegraph **MUST NOT** 实现 `init_chat_model`、`@tool` 装饰器、消息体系、`create_agent` 等
  LangChain 层能力；只需**能承载**它们（鸭子类型）。
- freegraph **MUST NOT** 做多语言 / 多模型 provider 矩阵。
- freegraph **MUST NOT** 以「与 LangChain 共存」为验收目标。
- 跨仓库接口**MUST** 对齐「内核最小契约」，freegraph 对上（freechain）承诺接口、
  对下（用户 / 脚本）承诺语义。**契约清单以 `harness/reports/Q8-图运行时最小契约.md` 的 C1–C26 为唯一权威**
  （含：状态 schema 与归约器机制、稀疏状态、节点签名与部分状态合并、路由函数与 `path_map` 双形态、
  起止标记、编译与执行、streaming mode、图结构导出、mermaid 导出与 PNG 渲染、`Command` / `interrupt` /
  `Send`、checkpointer 与 store 接口、`context` 通道、运行配置、可观测挂钩、当前 span 上下文、节点命名别名、子图）。
  **MUST** 在 freechain 开工前冻结该清单，并**MUST NOT** 擅自增删条目。
- **freegraph 明确不做的 LangSmith 能力（Q1 / Q2 逐档裁定后固化，理由分三类）**：
  - **① 付费墙内（Plus / Enterprise）**：Deployment 的托管与水平扩缩（1-Click Deploy、Dedicated、
    Scale-to-Zero、Assistants API、Cron、鉴权）、**Engine**、Tuned Evaluators、Insights、Bulk data export
    （Plus 也锁，仅 Enterprise）、Unlimited agents、自托管控制面（Enterprise）。
  - **② 免费档开放但属「评测平台」，范围过大**：Evaluation（online / offline）、Datasets、
    Annotation Queue、Prompt Hub & Playground。**MUST NOT** 因「官方免费」就纳入。
  - **③ 免费档开放但必然引入出站**：Fleet、Sandboxes、LLM Gateway。Sandboxes 执行 agent 生成的代码，
    Gateway 代理模型调用，**与原则 I 的零出站直接冲突**。
  - 另：Fleet 模板市场（Marketplace）与 Agent Registry 属 SaaS 治理能力；
    Agent Registry **仅 Cloud 可用、自托管无官方替代**，freegraph **MUST NOT** 依赖它。
- **不做跨仓库的 freechain 实现**：freechain 只**消费** freegraph 的契约，**MUST NOT** 反向要求内核为其定制。

**Rationale**：范围一旦模糊，freegraph 会被拖回「再造一个 LangChain」的状态，
两项目分层与 freechain 的独立性同时失效。

**Requirement**：**MUST** 在跨仓库协作前冻结内核最小契约；
**MUST** 遵守上列三类「不做」清单，新增能力**MUST** 先论证不属于这三类。

### VIII. 证据与术语纪律

结论**必须**可追溯，术语**必须**准确。

- 事实性结论**MUST** 附来源标记（URL 或 `本地路径:行号`）。
- 价格、额度、套餐 **MUST** 标注 as-of 日期（`截至 YYYY-MM-DD`）并附「以官方定价页为准」。
- 无法核实的信息 **MUST** 标 `[未验证]` 并写明缺哪个页面 / 缺哪个字段 / 试过哪些 URL；
  **MUST NOT** 用推测填充表格或结论。
- **动态渲染页面的证据 MUST 做 DOM 级解析**：功能勾选矩阵、开关状态、徽标等以 SVG / CSS 呈现的信号，
  **MUST NOT** 仅凭 Markdown 文本化结果下结论。**依据**：Q1 调研中曾因定价页勾选矩阵被文本化
  而误判 5 项（Insights / Annotation Queue / Prompt Hub / Bulk data export / Studio），
  DOM 级解析后结论完全反转。此类证据**MUST** 记录解析方法与可复现的脚本位置。
- 发起者的自造表述（「三大基础功能」「六大概念」「tool 循环智能体」等）
  **MUST** 标注为自造表述，**MUST** 先给出官方术语对照表再使用，**MUST NOT** 将自造词当作官方术语。
  **官方术语对照表以 `harness/reports/Q4-LangSmith对LangChain的实际影响程度.md` §3.4 为唯一权威**
  （官方三层分类：Runtime / Framework / Harness；freegraph 对标 Runtime，freechain 对标 Framework，
  Harness 层不做）。项目文档**SHOULD** 直接使用官方术语。

**Rationale**：本项目的立项依据是一份调研报告；报告若掺入推测，后续所有设计决策都会建在流沙上。
自造术语一旦流入代码与文档，会污染整个生态的沟通。证据的**获取方式**同样属于证据质量的一部分——
错误的采集方法产生的错误数据，其危害大于没有数据。

**Requirement**：**MUST** 遵守引用与 `[未验证]` 标注规范；**MUST NOT** 输出无来源的事实性断言；
**MUST** 对动态渲染页面的信号做 DOM 级解析。

### IX. 依赖许可证与商标红线（NON-NEGOTIABLE）

本项目要可私有化部署、开源、商用友好（项目目标）。以下三条**不可逆**——一旦发布即无法收回，
因此**不接受任何形式的临时豁免**；削弱本原则**必须**走 MAJOR 版本修订（见 Governance）。

- **许可证白名单**：依赖的许可证**MUST** 属于 {MIT, Apache-2.0, BSD-2/3, PSF}。
  **MUST NOT** 引入 `Elastic-2.0` / `AGPL` / `SSPL` / `BUSL` 等**传染性或限制性**许可证的依赖。
- **Elastic-2.0 组件禁令**：**MUST NOT** 引入、复制或内嵌 `langgraph-api`、
  `langgraph-runtime-inmem`、Phoenix 等 Elastic-2.0 组件。
  ELv2 明文禁止 "provide the software to third parties as a hosted or managed service"——
  **这恰好否掉 freegraph 最可能的商业模式（托管版）**。
  若 freegraph 未来实现本地 Agent Server，**MUST** 仅依据**公开文档与公开 OpenAPI 规范**独立实现。
- **第三方商标禁令**：**MUST NOT** 使用 LangChain / LangSmith / langchain / langgraph / deepagents 的
  **商标、logo、图标、品牌色或品牌形态**（官方《Brand Assets & Usage Guidelines》已把
  langgraph / deepagents 与 langchain 并列为受保护的 "Open Source Framework Logos"）；
  **MUST NOT** 照抄官方 "Approved copy" 描述文案；
  **MUST** 在 README 与文档中声明「独立实现、非 LangChain Inc. 产品」。

**Rationale**：LangChain 家族的 OSS 侧全部是 MIT，**未发现传染性条款**——这是 freegraph 可以
合法「复刻 API」的许可证基础。但 `langgraph-api` / `langgraph-runtime-inmem` / Phoenix 的 Elastic-2.0
是一个随时会被忽视的法律地雷，尤其在「我们也要提供托管版」的叙事下。
**关键事实（Q7 实证）**：OSS wheel 里的 `langgraph_license/validation.py` 是 **noop**
（`get_license_status()` 恒返回 True、`plus_features_enabled()` 恒返回 True），
而 `langgraph_api/self_hosted_logs.py:94-95` 却从同一个模块 import 了 wheel 里**根本不存在**的
`CUSTOMER_ID` / `CUSTOMER_NAME`（源码注释 `# type: ignore[unresolved-import]`）。
这说明厂商预留了**闭源 companion 包**来替换这个 noop → **技术上当前能绕过，法律上从来不可用**。
商标同理：logo 一旦印在文档 / 官网 / 宣传物料上就撤不回来。
**MIT 解决「能不能抄代码」，商标解决「能不能叫这个名字」，两者相互独立。**

**Requirement**：本原则三条 **MUST NOT** **MUST** 由 CI 断言自动校验（见质量门禁第 2 项）；
任一被违反即视为阻断性缺陷，**MUST NOT** 以「临时豁免」「先跑通再换」等理由放行。

### X. 文档合规义务

以下两项是**必须做的文档 / 登记义务**。它们属门禁项：遗漏可以补正，但**MUST NOT** 长期缺失。

- **API 兼容矩阵**：允许为互操作目的使用同类 API 名称，但**MUST** 维护一张
  「行为等价 / 部分等价 / 不支持」的**兼容矩阵**，并注明「兼容意图为互操作，**不构成 affiliation**」。
- **第三方归属**：任何引入的第三方代码**MUST** 进入 `THIRD_PARTY_NOTICES`（或同类清单），
  保留其原始版权与许可声明。

**Rationale**：API 名称兼容在著作权上通常不侵权（版权保护的是表达，不保护接口与方法论），
这是开源生态互操作的通行做法。但**「宣称兼容」与「暗示 affiliation」是两回事**——
兼容矩阵与免责声明就是把后者挡在前面的机制。归属清单则是 MIT 许可证「保留版权与许可声明」
这一义务的落地载体。

**Requirement**：**MUST** 在每个引入新依赖、或扩展 API 兼容面的特性中更新上述两份清单；
**MUST NOT** 在清单缺项的情况下宣布该特性完成。

## 项目定位与范围（Additional Context）

### 目标

在**复刻 LangGraph Graph API 的三大基础能力**（官方术语：**state schema / node / edge**，
另含官方补充机制 `Command` / `interrupt` 等）的前提下，提供**彻底剥离 LangSmith、
且内核不依赖 LangChain** 的图运行与可观测能力。两条参考验收目标：

1. LangGraph Quickstart 示例中仅把 `langgraph` 字样替换为 `freegraph`，即可跑起功能一致的
   tool-calling 循环智能体（已具体化为原则 III）。
2. freegraph 提供**不亚于 LangSmith Studio 的本地图运行时可诊断性**（见原则 IV）。

> 两条均为**愿望而非既定事实**，其可行性与工作量由调研 Q3 / Q6 / Q7 / Q8 裁定，
> 结论**只能细化**验收契约，**不能削弱**它。
>
> 关于第 2 条的**精确化说明（Q6 裁定，不构成削弱）**：官方「LangSmith」是一个覆盖
> Observability / Evaluation / Deployment / Engine / Fleet / Sandboxes / Gateway 的完整商业产品线，
> 「不亚于」全栈在 freegraph 的定位下不可达也无需追求。Q6 裁定把第 2 条精确化为
> **「在图运行时可诊断性这一垂直维度上不亚于 LangSmith Studio」**——该维度上 freegraph
> **可达**（Studio 独有的「交互式图运行时 IDE」无任何现成 OSS 可替代，是 freegraph 的独占位置），
> 且给出了达成路径（路线 B）与达成度估计。**垂直维度的限定是精化，不是降格。**

### 两项目路线图

| 项目 | 定位 | 依赖关系 |
|---|---|---|
| **freegraph**（本仓库） | 图运行内核：状态模型 / 节点 / 边与路由 / 运行时 / 可观测 | 零 LangChain、零 LangSmith 依赖 |
| **freechain**（后续项目） | 替代 LangChain 的上层：模型抽象、工具、消息、agent 构造 | 基于 freegraph 构建 |

### 非目标

- 不在 freegraph 内重建 LangChain 层。
- 不做多语言 / 多模型完整 provider 矩阵。
- 不追求与 LangChain 共存。
- **不做 LangSmith 的托管 / 自治 / 评测平台能力**——具体清单与理由分类见原则 VII。

### 术语约定

「三大基础功能」「六大概念」「tool 循环智能体」均为**发起者自造表述，非官方术语**。
官方术语对照表以 `harness/reports/Q4-LangSmith对LangChain的实际影响程度.md` **§3.4** 为唯一权威。

**官方三层分类（Q4 裁定，替代自造的「三大基础功能 / 六大概念」表述）**：

| 官方层 | 官方产品 | freegraph 的对应 |
|---|---|---|
| **Runtime** | LangGraph | ✅ **freegraph 对标此层** |
| **Framework** | LangChain | ✅ **freechain 对标此层** |
| **Harness** | Deep Agents | ❌ 不做 |

> **补充裁定（Q5）**：「六大概念」是 LangChain **v0 时代**的抽象，在 **v1 中已断裂**——
> chain / retriever / indexing / hub 迁至 `langchain-classic`，output parser 被
> `ToolStrategy` / `ProviderStrategy` 取代。freechain 若按 v1 精神重建，
> **SHOULD** 采用「Model + Tools + Messages + Harness(middleware)」四元组，**MUST NOT** 复活六大概念。

## 质量门禁与交付流程（Development Workflow & Quality Gates）

### 目录约定

| 路径 | 用途 |
|---|---|
| `harness/prompts/` | 提示词（调研任务书、宪法等） |
| `harness/reports/` | 调研报告（每题一份 + 汇总报告） |
| `harness/proposals/` | 设计提案（调研结论转化的规格来源） |
| `harness/features/<feature>/` | 每个特性的人工验证记录 |
| `harness/demo/target.py` | MVP 验收契约（**只读**） |
| `harness/docs/` | 同步下来的官方文档快照（**只读**） |
| `THIRD_PARTY_NOTICES` | 第三方代码归属与许可声明清单（原则 X） |
| `.specify/memory/constitution.md` | 本宪法的生效副本（由 `/speckit.constitution` 生成） |

### 依赖白名单 / 黑名单

每个特性**MUST** 复核依赖清单。白 / 黑名单以 `harness/reports/Q3-LangGraph的开源边界.md` §3.6
与 `harness/reports/Q7-开源边界地图与许可证合规.md` §3.1 的结论为准：

- **包层白名单**：`typing-extensions`（唯一建议的**必装**运行时依赖）。
  可选 extra：`pydantic`（`[pydantic]`）、`ormsgpack`（`[checkpoint]`）、
  `opentelemetry-api` / `opentelemetry-sdk`（`[otel]`）、mermaid 相关（`[png]`，**默认关闭**）。
- **包层黑名单**：`langsmith`（含 `langsmith[otel]` / `langsmith[sandbox]`）、`langchain`、
  `langchain-core`、`langchain-classic`、`langchain-protocol`、`langgraph*` 全系列、
  `deepagents`，以及全部 provider 包（`langchain-anthropic` / `langchain-openai` /
  `langchain-google-genai` 等——它们会把 `langchain-core` 拉回来）。
  **额外黑名单（许可证，见原则 IX）**：`langgraph-api`、`langgraph-runtime-inmem`、
  Phoenix 等 Elastic-2.0 组件。
- **配置层黑名单**：读取 `LANGSMITH_*` / `LANGCHAIN_*` / `LANGGRAPH_CLOUD_LICENSE_KEY` /
  `LANGGRAPH_AUTH*` 等环境变量（原则 I）。**freegraph 内核 MUST NOT 读取任何环境变量**——
  provider key 由 freechain / 用户代码自行传入。
- **网络层黑名单**：向 `*.smith.langchain.com` / `smith.langchain.com` / `beacon.langchain.com` /
  `*.langchain.com` 出站（原则 I）；**`mermaid.ink` 亦在黑名单**（非 LangSmith，但同样违反零出站）。
  **freegraph 内核 MUST 零出站**；可选的 OTLP exporter 仅在用户显式传入时生效。
- **核心层黑名单**：import `langchain` / `langchain-core`（原则 II），
  且**依赖声明中亦不得出现**（`import` 不出现 ≠ 依赖树干净）。

### 质量门禁

每个特性在合入前**MUST** 全部通过：

1. **规格门禁**：有 proposal 与 spec，tasks 可逐条勾选（原则 VI）。
2. **依赖门禁（红线，阻断）**：依赖树无 `langsmith` / `langchain-core` / Elastic-2.0 / AGPL / SSPL，
   无 `LANGSMITH_*` / `LANGCHAIN_*` 读取，无 `*.langchain.com` / `mermaid.ink` 出站，
   无第三方商标资产（原则 I / II / IX）。
   **MUST** 以可自动执行的断言落地（递归展开 `importlib.metadata.requires()` + 许可证白名单校验）。
3. **契约门禁**：`harness/demo/target.py` 原样可跑（原则 III），
   **MUST** 包含 C4（稀疏状态）与 C8（条件边 fresh 状态）两条独立回归测试（原则 II）。
4. **自动门禁**：CI 全绿，且包含 fake 模型跑通验收基线的一轮（原则 V），
   **SHOULD** 附带 socket guard 的零出站断言（原则 V）。
5. **人工门禁**：`harness/features/<feature>/` 下有完整人工验证记录，含真实模型一轮（原则 V）。
6. **证据门禁**：新增结论均有来源标记，术语准确（原则 VIII）。
7. **文档合规门禁**：`THIRD_PARTY_NOTICES` 已登记、API 兼容矩阵已更新（原则 X）。

## Governance

- 本宪法**优先于**其他一切实践与文档约定；与本文件冲突的既有做法，以本文件为准。
- **修订流程**：修订提案 **MUST** 说明「变更了什么 / 为什么 / 受影响的原则与特性 / 迁移方案」；
  原则增删或语义重定义**MUST** 经发起者批准，并**MUST** 附带对已实现特性的影响评估与迁移计划。
- **版本策略**：遵循语义化版本。
  - **0.x 阶段（当前）**：项目未开工、宪法未批准期间，版本保持 `0.0.x`；
    `0.x` 表示「尚未定版，条款可能随实现反馈调整」。**首次批准即定版 1.0.0**。
  - **MAJOR**：原则被移除或语义重定义（向后不兼容的治理变更）。
  - **MINOR**：新增原则 / 章节，或对既有原则的实质性扩充。
  - **PATCH**：措辞澄清、错别字、非语义性修订。
- **合规复核**：每次修订**MUST** 复核原则 I–X 的可验证性；
  尤其**MUST** 检查新增条款是否可被自动化检查或人工检查明确判定。
- **待定项处理**：`TODO(...)` 字段**MUST** 在批准时由 `/speckit.constitution` 填实；
  `[待调研]` 条款**MUST** 在 `harness/reports/` 出具后回填，**MUST NOT** 在依据缺失时长期悬空。
  （Q1–Q8 已于 2026-11-01 出具，本版已完成全部 `[待调研]` 回填。）
- **演进触发**：调研结论（Q1–Q8）**MAY** 触发宪法修订，尤其是原则 IV 的可观测技术选型
  与原则 VII 的内核最小契约。**本版即由 Q1–Q8 结论触发**：
  - 新增原则 IX（许可证与商标红线，NON-NEGOTIABLE）与原则 X（文档合规义务，门禁项）
    ——两者按严重度拆分：只有不可逆的法律红线（依赖许可证白名单 / Elastic-2.0 组件 / 第三方商标）
    标 NON-NEGOTIABLE；可补正的文档登记义务（归属清单 / 兼容矩阵）单列为门禁项；
  - 原则 IV 选定路线 B；原则 VII 冻结 C1–C26 并固化「不做」清单；
  - 原则 III 补入 PNG 离线路径与 7 项同名清单；原则 VIII 补入 DOM 级解析纪律。
- **新调研的效力**：后续新增调研结论若与本宪法冲突，**MUST** 先走修订流程，
  **MUST NOT** 以「调研报告更新了」为由绕过宪法。
- **修订记录**：
  - **v0.0.1（2026-11-03）**｜项目更名 `opengraph` → **`freegraph`**、姊妹项目
    `openchain` → **`freechain`**（起因：两个名称在 PyPI 上均被永久占用，不可转让复用；
    实测取证见文件头 SYNC IMPACT REPORT）。同时修订：① 原则 III 的具体验收 API 名
    （`from freegraph.graph import ...`）；② 原则 V 门禁 4 的方法性措辞
    （socket 夹具改为「只观测不阻断 + 按发起方归因」，零出站证据改为「框架自身出站数 = 0」，
    不阻断用户代码出网）。**原则 I–X 的实质要求均未改变**，仅 API 名与方法措辞变化；
    迁移方案与受影响特性见文件头 SYNC IMPACT REPORT 与 `harness/proposals/更名与迁移说明.md`。

> **2026-11-04 补充（不影响版本号）**：`freegraph` 已在 PyPI 上占位发布 **v0.0.1**
> （owner = PyPI 账号 `yangjiacheng1996`，发行名 = 导入名 = `freegraph`；
> 发布通道 = GitHub Actions Trusted Publishing（OIDC），工作流
> `.github/workflows/publish.yml`，无需 API token / 密码）。该版本**不含任何内核实现**，
> 仅用于锁定名称；`freechain` 亦已于同日占位发布 v0.0.1。**规范性正文与原则 I–X 全部未改动**，
> 故**不 bump 版本号**（Version 仍为 0.0.1，Last Amended 仍为 2026-11-03）。

**Version**: 0.0.1 | **Ratified**: TODO(RATIFICATION_DATE): 宪法待发起者批准，批准日填实（ISO YYYY-MM-DD）并定版为 1.0.0 | **Last Amended**: 2026-11-03
