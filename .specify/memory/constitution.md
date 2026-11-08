<!--
本文件是 freegraph 的**项目宪法（生效副本）**。

版本历史，以及每次修订的「变更了什么 / 为什么 / 受影响的原则与特性 / 迁移方案」，
见文末 **Governance · 修订记录**；待决与已决事项见 `harness/proposals/立项书.md` §12。

**2026-11-05 定版为 1.0.0**：经发起者批准，原则 V 门禁 4 的措辞（零出站的观测口径）
与原则 VII 的 MINOR 修订（契约清单权威范围由 C1–C26 扩为 **C1–C27** + 标识与关联键约定）
一并生效。
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
- 中断与恢复（interrupt / resume）、状态回溯（time-travel）**MUST** 可用；
  **恢复 MUST 挂 checkpointer**——**MUST NOT** 提供「不挂 checkpointer 也能恢复」的内存态
  旁路（内存态恢复不可靠；`interrupt` 的主场景是 time travel，须跨长时间 / 跨重启可恢复；
  SQLite 是智能体开发的事实标准，故必须采用 checkpointer）。未挂 checkpointer 时调用恢复
  **MUST** 抛明确异常。
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

- 人工验证记录**MUST** 落在 `harness/verification/<feature>/` 下（`manual-verification.md`）——
  该目录为「人工验证记录」的**唯一**约定位置（见「目录约定」表）；`harness/features/` 只放
  **feature 提示词初稿**，两者**MUST NOT** 混放。
- 记录**MUST** 写明：验证环境、验证步骤、实际输出、结论、遗留问题。
- MVP 验收基线**必须**跑两遍且都通过：
  1. **fake / 伪模型**跑一遍（CI 可自动化，用于回归）；
  2. **真实模型**再跑一遍（人工验收，用于确认端到端真实行为）。
- 上述两次验证**MUST** 在**不设任何 `LANGSMITH_*` 环境变量**的干净环境下进行，
  **并且 MUST** 有「零出站」的可判定证据：**SHOULD** 采用 **socket 监测夹具**——
  **只观测、不阻断**（记录目标与调用栈后**放行**所有连接），**按调用栈归因**区分
  「**框架出站**」（调用栈出现 `freegraph/` 包路径）与「**用户出站**」（模型调用、节点自建
  HTTP 客户端等），**只对前者断言 = 0**；**用户出站记录在案但不判失败**，人工轮允许出现
  「模型厂商端点」一条并**在验证记录中写明**——Q3 调研已验证该方法可行且可复用为 CI 断言。
  > **口径来源**：立项书 §12 **D12**（2026-11-05 批准）+ §9.2「框架零出站的验证方法」。
  > **理由**：freegraph 是**函数胶水 / 工作流框架**，承诺的是「自己不会偷偷联网」，
  > **不是**「你的程序不许联网」；拦截式守卫会阻断用户节点的正常出网，属反直觉设计
  > （立项书 §10 的 R11）。原则 I「自身零出站、断网可用」的实质要求**不变**。

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
- freegraph v1 **MUST NOT** 提供**跨会话 / 跨图**的长期记忆能力（`Store`）——
  **图 = 一个进程**（定位推导，见「项目定位与范围 · 定位补充」）。契约 **C20** 仍**冻结**
  （它是 freechain 的设计输入），**实现后补**（v2）；`compile(store=...)` 关键字仍被接受，
  但 v1 **背后无实现**——文档 **MUST** 显式写明，不得让用户误以为传入即生效。
- freegraph **MUST NOT** 做多语言 / 多模型 provider 矩阵。
- freegraph **MUST NOT** 以「与 LangChain 共存」为验收目标。
- 跨仓库接口**MUST** 对齐「内核最小契约」，freegraph 对上（freechain）承诺接口、
  对下（用户 / 脚本）承诺语义。**契约清单以 `harness/reports/Q8-图运行时最小契约.md` 的 C1–C27 为唯一权威**
  （含：状态 schema 与归约器机制、稀疏状态、节点签名与部分状态合并、路由函数与 `path_map` 双形态、
  起止标记、编译与执行、streaming mode、图结构导出、mermaid 导出与 PNG 渲染、`Command` / `interrupt` /
  `Send`、checkpointer 与 store 接口、`context` 通道、运行配置、可观测挂钩、当前 span 上下文、节点命名别名、
  子图、**本地 trace 存储与查询**）。
  **MUST** 在 freechain 开工前冻结该清单，并**MUST NOT** 擅自增删条目。
- **标识与关联键约定（2026-11-05 修订，与 C1–C27 一并冻结）**：
  - `thread_id` = **会话**标识，由 `RunConfig` 承载；`run_id` = **单次运行**标识，
    由运行时在每次 `invoke` / `stream` 开始时生成，**MUST NOT 可由用户指定或覆盖**
    （**用户不设置**；`run_id` **不进** `RunConfig`——它是运行期产物而非配置项；
    用户自带标识需求用 `thread_id` / `metadata` / `tags` 承担）；
  - **一次运行一个 `run_id`**：该次运行的所有节点、工具、模型调用与事件共享它
    （把每个节点视作一个微服务，则 `run_id` 是**链路监控的唯一通行证**，
    等价于分布式追踪的 trace id）；
  - **`run_id` MUST 可查**：它是本地 trace 查询 API（C27）的过滤器之一，
    使「精确回查某一次运行」成为可能；
  - **每个 span MUST 带** `thread_id` / `run_id` / 节点名 / `checkpoint_id`
    （挂接 checkpointer 时有值，否则为空）；**缺 `run_id` 的 span 视为实现缺陷**；
  - `stream()` 产出的事件与 `TraceSink` 收到的 span **共享同一 `run_id` / `thread_id`**，
    MAY 按 id 合并为一条时间线。
  → **违反上述任一条的 PR 不得合入**（这是 C27 与将来的 Studio 子包得以「不改内核」实现的前提）。
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
- **源文件署名头**：**每一个源文件**（`src/` 下的包代码，以及仓库内的脚本）**MUST** 在文件
  顶部携带署名头，形如：
  `# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph`
  （有 shebang 的脚本放在 shebang **之后**；模块 docstring 仍**MUST** 是首个语句）。
  例外：`py.typed`（PEP 561 要求为空）与 `harness/demo/target.py`（**只读基准**，
  宪法原则 III 禁止修改）。
  **Rationale**：本项目是**个人作品集 / 名片**（见「项目定位与范围 · 项目性质」），
  许可证为 **MIT**——MIT 允许**整份或单个文件被复制**（这正是采纳面最大的原因），
  而**复制不会带走 `LICENSE`**。因此署名必须**随每个文件一起流动**，
  否则被单独 copy 的那一段代码就与作者无关了——**署名头就是 MIT 的「名片」兑现机制**。

**Rationale**：API 名称兼容在著作权上通常不侵权（版权保护的是表达，不保护接口与方法论），
这是开源生态互操作的通行做法。但**「宣称兼容」与「暗示 affiliation」是两回事**——
兼容矩阵与免责声明就是把后者挡在前面的机制。归属清单则是 MIT 许可证「保留版权与许可声明」
这一义务的落地载体。

**Requirement**：**MUST** 在每个引入新依赖、或扩展 API 兼容面的特性中更新上述两份清单；
**MUST NOT** 在清单缺项的情况下宣布该特性完成；**MUST** 为新增的每一个源文件加上署名头
（静态检查由 B3F1 的 CI 门禁落地，见 `harness/features/B3F1_项目脚手架与CI门禁.md`）。

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

### 定位补充：freegraph 是**通用图框架**，不止于智能体开发（2026-11-05 决议）

> freegraph 的初衷是把它建成一个**通用图框架**——目标场景除**智能体开发**外，还包括
> **RPA 自动化**、**脚本编排**（在一定程度上**替代 `main` 函数**）、
> **可视化工作流编排**。
>
> **由此得出的一条范围边界（决定性）**：这类场景的共同前提是「**图 = 一个进程**」——
> 因此**跨会话 / 跨图**的能力（如长期记忆 `Store`）**不属于 v1**，属 v2 预备。
> 该边界不是「先不做再说」的临时取舍，而是**定位推导出的硬边界**：
> 违反它会引入进程间的状态语义（谁持有、怎么过期、如何跨进程可见），复杂度陡增且
> **违背「通用图框架 / 单进程」的初衷**。
>
> **注**：本条是**定位补充**，**不改变**两条验收目标（G1 固定脚本可跑 / G2 本地可诊断）。
>
> **项目性质（2026-11-05 补充）**：本项目是**个人开源项目**——同时是**作品集 / 名片 /
> 能力证明**（个人项目在求职与商务合作中的展示物），**非以盈利为直接目的**。
> 该性质直接决定了**许可证选择**：**MIT**（D3 已决，2026-11-05）——MIT 的**单向兼容性**
> 使本项目的代码可被嵌入**任意**许可族的下游项目，最大化采纳面；而 Apache-2.0 的
> 额外条款（专利授权 / 商标隔离 / 贡献者再授权 / NOTICE / §9 收费承接支持）**对本项目
> 均属空条款**（无专利组合、无自有商标资产、无外部贡献者、原则 X 已用
> `THIRD_PARTY_NOTICES` 覆盖归属义务、明确不做 SaaS 变现）。
> 由此也意味着：**本仓库本身（宪法 / 调研报告 / 验收脚本 / feature 规格）就是作品集主体**——
> 「可审计的契约」与「充分的人工验证」既是质量底线，也是能力证明。

### 非目标

- 不在 freegraph 内重建 LangChain 层。
- 不做多语言 / 多模型完整 provider 矩阵。
- 不追求与 LangChain 共存。
- **不做 LangSmith 的托管 / 自治 / 评测平台能力**——具体清单与理由分类见原则 VII。

### 术语约定

#### 本项目的开发层级词表（四层，**互斥、不可混用**）

> **2026-11-05 统一（宪法 v1.4.0）**。此前「Phase」与 speckit 的「feature」同名不同义，
> 且本项目的「Feature」层级与 speckit 的「feature」层级同名不同义——
> 一词二义是本项目最持久的概念混淆源。本表是**唯一权威**。

| 层级 | 中文 | English | ID 形式 | 数量 | 含义 |
|---|---|---|---|---|---|
| 1 | **层** | `layer` | `L1`–`L6` | 6 | **代码归属层**（依赖层级，取值封闭） |
| 2 | **领域** | `area` | `A1`–`A8` | 8 | **交付分组**（粗粒度；体量表见立项书 §4.4） |
| 3 | **功能块** | `block` | `B1`–`B25` | 25 | **交付单元**（一个可独立验收的垂直切片；含 1–3 个 feature） |
| 4 | **feature** | `feature` | `B<n>F<m>` | 31 | **最小开发单位 = speckit 的一次闭环**（一次 `/speckit.implement` 闭环） |

- **MUST NOT** 把「功能块」与「feature」混用：前者是**交付单元**（多个 feature 的分组），
  后者是**最小开发单位**（一次闭环 = 一个 feature）。
- **MUST NOT** 把「层」与「领域」混用：「层」是**代码归属**（L1–L6），
  「领域」是**交付分组**（A1–A8）——一个领域可跨多层，一个层可含多个领域。
- **MUST NOT** 把「领域」与「作用域（scope）」混用：「领域」= 交付分组；
  「作用域」= 依赖红线/配置层/网络层的适用边界（立项书 §9.2）。
- **ID 形式互不冲突**：`L<n>` / `A<n>` / `B<n>` / `B<n>F<m>` /
  `E`/`S`/`R`/`D`/`C`（事实/指标/风险/决策/契约）——四套命名空间的分配规则见立项书 §4.4。
- **参考**：`harness/features/` = feature 提示词初稿；
  `harness/verification/<feature>/manual-verification.md` = 该 feature 的人工验证记录；
  `specs/<feature-id>-<short-name>/` = speckit 的 feature 目录（**直接用规划 ID**，
  **不带** Speckit 的三位序号——见 `harness/prompts/guide.md` §4.7）。

#### 官方术语对照

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
| `harness/features/` | **feature 提示词初稿**（`B<n>F<m>_*.md`，每 feature 一份 `/speckit.specify` 提示词）+ 导航文件 `README.md`（开发顺序） |
| `harness/verification/` | **人工验证记录**（原则 V 人工门禁）——按 feature 分目录：`<feature>/manual-verification.md`（`<feature>` = feature ID，如 `B1F1`）；含 `README.md` 说明该目录的约定 |
| `harness/demo/target.py` | MVP 验收契约（**只读**） |
| `harness/docs/` | 同步下来的官方文档快照（**只读**） |
| `THIRD_PARTY_NOTICES` | 第三方代码归属与许可声明清单（原则 X） |
| `.specify/memory/constitution.md` | 本宪法的生效副本（由 `/speckit.constitution` 生成） |

### 依赖白名单 / 黑名单

每个特性**MUST** 复核依赖清单。白 / 黑名单以 `harness/reports/Q3-LangGraph的开源边界.md` §3.6
与 `harness/reports/Q7-开源边界地图与许可证合规.md` §3.1 的结论为准——
**但必装依赖一项以本宪法正文为准**（Q3 §3.6 原建议「必装 `typing-extensions`」
已被本宪法修订记录 **v1.2.0** 取代：必装依赖 = **无**；
该报告 §3.6 的其余部分——**黑名单、配置层、网络层**——仍然有效）：

- **包层白名单**：**必装运行时依赖 = 无**（基础安装**零第三方依赖**，`dependencies = []`）。
  可选 extra：`pydantic`（`[pydantic]`）、`ormsgpack`（`[checkpoint]`）、
  `opentelemetry-api` / `opentelemetry-sdk`（`[otel]`）、
  **`playwright`（`[png]`，**默认关闭** · 本地 Chromium 渲染 · 许可证 Apache-2.0）**。
  > **2026-11-05 修订**：原为「`typing-extensions`（唯一建议的**必装**运行时依赖）」，
  > 现改为**必装依赖为空**——`typing-extensions` 已从基础安装剥离（见修订记录 v1.2.0）。
  > 基础安装的依赖闭包 **MUST 为空集**（由 G3 门禁断言）。
  > **2026-11-08 修订（v1.5.0）**：原写「mermaid 相关（`[png]`）」——**类别式表述不可判定**
  > （无确切包名 ⇒ 无法核验许可证、无法枚举闭包、无法写入门禁白名单），且与本条其余各 extra
  > 「逐包名列」的取法不一致（`[otel]` 已是逐包名列）⇒ 收敛为**唯一实测可行的后端 `playwright`**
  > （Apache-2.0；完整闭包 `playwright` / `greenlet` / `pyee` / `typing-extensions` 实测全绿）。
  > `[png]` extra 的三条硬约束 **MUST** 同时成立：
  > **(a) 默认关闭**（不装即不可用，基础安装 MUST NOT 拉起其依赖）；
  > **(b) 依赖闭包 MUST 全部落在原则 IX 的许可证白名单 {MIT, Apache-2.0, BSD-2/3, PSF} 内**；
  > **(c) 零出站**（MUST NOT 依赖任何远程渲染服务——`mermaid.ink` 仍在网络层黑名单内）。
  > 浏览器二进制由用户**显式**执行 `playwright install chromium` 获取（属**安装期**动作）
  > ⇒ **基础安装的零第三方运行时依赖承诺不受影响**（四个 extra 均默认关闭）。
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

### 运行时环境基线（Python 版本与 typing 构件上限）

本项目**MUST** 在 **Python 3.11** 上运行与开发，且**MUST NOT** 使用任何
**3.11 之后**才进入标准库的 typing 构件。本条与「依赖白名单」同属**硬约束**——
它决定「什么样的代码能被写出来」，而不只是「能装什么包」。

- **最低版本 = 3.11**：``requires-python`` MUST 为 ``>=3.11``。
  理由（依据：修订记录 v1.2.0 · `research.md` D-21）：3.11 一次性补齐 **7 项**
  typing 构件（`Self` / `NotRequired` / `Required` / `TypeVarTuple` / `Unpack` /
  `LiteralString` / `dataclass_transform`），使**基础安装零第三方依赖**成为可能；
  而 3.12 与 3.13 各只补 2 项，性价比更低；3.10 已于 2026-10 结束安全支持。
- **typing 构件上限 = 3.11**：源码 **MUST NOT** 出现下列 3.12+ / 3.13+ 构件——
  | 构件 | 进入 stdlib | 所属版本 |
  |---|---|---|
  | `TypeAliasType`（PEP 695 `type X = ...` 语法与 `typing.TypeAliasType`） | 3.12 | ❌ 禁用 |
  | `override`（PEP 698） | 3.12 | ❌ 禁用 |
  | `ReadOnly`（PEP 705，`TypedDict` 的只读键） | 3.13 | ❌ 禁用 |
  | `TypeIs`（PEP 742） | 3.13 | ❌ 禁用 |
  | PEP 695 `type` 语句语法本身 | 3.12 | ❌ 禁用 |
  同样 **MUST NOT** 使用 3.12+ 的**语法**（如 PEP 695 `type` 语句）与
  3.11+ 的**其他**标准库新增（`asyncio.timeout`、`tomllib`、`StrEnum` 等
  **运行时**构件虽不属 typing，但同样须按「只用 3.11」的纪律判断，见下方判定口径）。
- **判定口径（MUST 可自动判定）**：
  1. **主判定 = CI 最低档**：CI 矩阵的**最低版本档 MUST 为 3.11**，
     且**全量**跑测试（含架构门禁）——任何 3.12+ 构件在该档**天然不可用**
     （`ImportError` / `AttributeError` / `SyntaxError`）。
  2. **辅判定 = AST 静态断言**：架构门禁 **G9** MUST 以 `ast` 扫描
     `src/freegraph/**/*.py`，显式点名上表的禁用构件并给出可读报错
     （报错信息 MUST 指明「你用了 3.12+ 的 X」），而非让开发者对着
     一个 `ImportError` 猜原因。
  3. **人工判定**：新引入的第三方构件或标准库构件时，
     MUST 确认其**首次进入 stdlib 的版本 ≤ 3.11**；不确定时以
     `hasattr(typing, "<name>")` 在 3.11 上实测为准。
- **违反后果**：属**阻断性缺陷**——MUST NOT 合入。
  「本机 Python 是 3.12/3.13 所以能用」**不是**理由：
  本地能跑的代码在 3.11 上会直接崩，而 3.11 是本项目的**承诺下限**。
- **与原则 II 的关系**：原则 II 要求「内核纯净（零 langchain）」，
  本条要求「内核**只用 3.11 以内的标准库构件**」——
  二者叠加的结果是：**契约层与内核 MUST NOT 需要任何第三方包即可运行**。

**Rationale**：Python 的 typing 是个**只增不减**的演进序列，每代都往标准库里塞新构件。
若不设上限，开发者会不知不觉地用上本机新版本才有的构件（`Self`、`TypeAliasType`、
`override`……），把「3.11 是下限」这条承诺在**代码里**悄悄破掉——而这种破坏
**不会在开发机上暴露**，只在用户装包时才炸。设上限 + 可自动判定，
是把承诺**钉进代码**而不是钉进文档。

**Requirement**：本条 MUST 由 **G9 静态断言**与 **CI 最低版本档**双重落地（见上方判定口径）；
`requires-python` MUST 保持 `>=3.11`；CI 矩阵最低档 MUST 为 3.11；
任何违反视为阻断性缺陷。

### 质量门禁

每个特性在合入前**MUST** 全部通过：

1. **规格门禁**：有 proposal 与 spec，tasks 可逐条勾选（原则 VI）。
2. **依赖门禁（红线，阻断）**：依赖树无 `langsmith` / `langchain-core` / Elastic-2.0 / AGPL / SSPL，
   无 `LANGSMITH_*` / `LANGCHAIN_*` 读取，无 `*.langchain.com` / `mermaid.ink` 出站，
   无第三方商标资产（原则 I / II / IX）。
   **MUST** 以可自动执行的断言落地（递归展开 `importlib.metadata.requires()` + 许可证白名单校验）。
   **基础安装（不含 extras）的依赖闭包 MUST 为空集**——零第三方运行时依赖是本项目的
   对外承诺之一（README「零第三方运行时依赖」），**MUST** 可被断言判定。
3. **契约门禁**：`harness/demo/target.py` 原样可跑（原则 III），
   **MUST** 包含 C4（稀疏状态）与 C8（条件边 fresh 状态）两条独立回归测试（原则 II）。
4. **自动门禁**：CI 全绿，且包含 fake 模型跑通验收基线的一轮（原则 V），
   **SHOULD** 附带 socket 监测夹具的零出站断言（**只观测不阻断 + 按发起方归因**，
   断言「框架出站 = 0」，原则 V + 立项书 §9.2）。
5. **人工门禁**：`harness/verification/<feature>/manual-verification.md` 下有完整人工验证记录，含真实模型一轮（原则 V）。
6. **证据门禁**：新增结论均有来源标记，术语准确（原则 VIII）。
7. **文档合规门禁**：`THIRD_PARTY_NOTICES` 已登记、API 兼容矩阵已更新（原则 X）。

### 质量门禁的分阶段落地与发起者追认（2026-11-08 决议 · v1.6.0）

> **背景（结构性张力）**：上面「质量门禁」要求**每个特性在合入前 MUST 全部通过**；
> 但 **M0 地基类** feature **不交付内核功能** ⇒ 凡**依赖内核运行时**的门禁项
> （门禁 **3** 的 C4 / C8 两条独立回归 · 门禁 **4** 的 fake 模型跑通验收基线一轮 ·
> 门禁 **5** + 原则 V 的真实模型一轮）在该 feature **物理不可达成**
> —— 硬写进去 = 一条**永久红**的 CI（且违反「feature 必须能独立通过门禁」）。
> 本条是该张力的**唯一通用处置规则**（**首次适用 = B3F1**：其 `spec.md` **裁定 22** /
> `plan.md` **登记项 R-4** / `tasks.md` **T057**）。

- **适用范围（窄口径 · MUST）**：某条**质量门禁**中的**某一部分**在当前 feature **物理不可达成**，
  且**不可达成的根因**是「**该 feature 按里程碑不交付其前置能力**」
  （例：「MVP 验收基线的跑通需要内核运行时，而内核运行时按 立项书 §6.2 属 **M2**」）⇒ **属本条**。
  - **被延后的 MUST 是「门禁项中依赖内核运行时的那一部分」，MUST NOT 是「整条门禁」**——
    例：门禁 **5** 的「人工验证记录存在且五段式齐全」**MUST** 照常落地，
    被延后的只是其中的「**真实模型一轮**」（无图可跑）。
  - **不属本条**：「本 feature 还没做」/「做起来成本高」/「暂时不方便」/「判据不好写」/「先放过，以后再说」。
- **处置方式（唯一 · 二者缺一不可）**：**偏离登记 + 发起者追认**。
  1. **偏离登记**（MUST 在 feature 文档内可审计）：
     ① 被偏离的**具体门禁项** · ② **不可达成的根因**（含里程碑依据）·
     ③ **判据未被放宽**的论证（红线判据一律照常执行）·
     ④ **承接方**（目标 feature ID + 里程碑）与**承接机制**
     （承接条款 MUST 写入目标 feature 的提示词初稿 ⇒ 由其 spec 落成 **FR + 裁定** ⇒ 其 tasks 与契约同步接线，
     **只接线、MUST NOT 新增门禁编号**）·
     ⑤ 落点 = feature 的 `plan.md`（登记项 / Complexity Tracking）**+** `tasks.md`
     （一条**阻断合入**的追认任务）。
  2. **发起者追认**（MUST 由**发起者**本人作出）：**追认文字 + 发起者确认 + 日期**
     MUST 落在 `harness/verification/<feature>/manual-verification.md`；
     **未追认前 MUST NOT 合入**；**MUST NOT** 由实现者代签。
- **红线（本条 MUST NOT 做什么）**：
  - MUST NOT 以本条**放宽或稀释任何门禁判据** —— **原则 I / II / IX 的红线不适用本条**：
    依赖红线（`langsmith` / `langchain*` / `langgraph*`）· 许可证红线 · 商标红线 · 零出站红线
    **MUST** 在**每个** feature 落地（可延后的只有**依赖内核运行时**的**能力型**门禁项）。
  - MUST NOT 写**永久红**的 CI；被偏离的门禁 MUST 落**挂载点**并**明确标记「未落地」**
    （MUST NOT 伪装成「已通过」）。
  - MUST NOT 把本条当作**长期豁免**：承接项 MUST 有**具名的承接方与里程碑**，
    MUST NOT 无期限悬空；**MUST NOT** 以本条为由删改宪法正文。
  - MUST NOT 用本条**规避**「本 feature 必须能独立通过其可适用门禁」的要求。
- **登记与复核**：每一条被偏离的门禁 MUST 在**人工验证记录**中登记（可审计）；
  本条的使用情况 MUST 在**下一次宪法修订**时复核 —— 若同类偏离**反复出现** ⇒
  MUST 重新评估**该门禁项的判据本身**（或调整里程碑切分），**MUST NOT** 继续依赖本条兜底。

### 发布门禁（Release Gate）

**发布 / 分发发行包时**（而非逐特性合入时）**MUST** 通过下列门禁；它与上面的
「质量门禁」相互独立，**MUST NOT** 互相替代：

0. **发版节奏**：v1 期间**只发两版**——「全部 31 个 feature 开发完成」发 `0.1.0`，
   「充分调试 + 内测 + 健壮性加固」之后发 `v1.0.0`；**中间 MUST NOT** 发任何
   预发布版（**中间版本不可删除、只能 yank**，每发一版即一条永久记录；且 `0.0.x`
   的定位是「占位版」，功能落地后须一次性离开它）。依据：立项书 §12 **D13** +
   §6.2.1。**MUST NOT** 在未达成该节列出的触发条件时擅自发版。

1. **发行产物纯度门禁**：构建产物的内容 **MUST** 仅含**包代码**（`src/<pkg>/`）与
   **必要元数据**（README / LICENSE / pyproject.toml / PKG-INFO）。
   **MUST NOT** 含任何**仓库内容**——`harness/`（调研报告 / 提示词 / 立项书 / 验收脚本）、
   `.specify/`（宪法与 spec 模板）、`.opencode/`（speckit 命令）、`node_modules/` 等
   均属**开发辅助材料**：它们**留在 GitHub 上供读者学习本项目的全部原理**，
   但**不得**进入发行包（否则会被他人 `import` 引入）。
   **MUST** 以可自动执行的断言落地，并在发布流水线中于**上传之前**强制执行
   （`harness/scripts/check_dist_purity.py`）；断言不通过时 **MUST** 中止发布——
   PyPI 上的版本一旦发布**不可删除**（只能 yank），故**MUST** 在上传前拦截。

> **为什么单列为发布门禁而非质量门禁**：质量门禁是「逐特性合入前」的检查，
> 作用于源码；发布门禁是「产物出厂前」的检查，作用于**打包结果**——
> 后者无法由源码审查替代（同一份源码在不同打包配置下产出的内容不同）。
> 「GitHub 上看全部原理」与「PyPI 上的包是干净的」**必须同时成立**，本门禁是后者的兜底。

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
  - 原则 IV 选定路线 B；原则 VII 冻结 C1–C27 并固化「不做」清单（2026-11-05 由 C1–C26 扩为 C1–C27）；
  - 原则 III 补入 PNG 离线路径与 7 项同名清单；原则 VIII 补入 DOM 级解析纪律。
- **新调研的效力**：后续新增调研结论若与本宪法冲突，**MUST** 先走修订流程，
  **MUST NOT** 以「调研报告更新了」为由绕过宪法。
- **修订记录**：
  - **v0.0.1（2026-11-03）**｜项目更名 `opengraph` → **`freegraph`**、姊妹项目
    `openchain` → **`freechain`**（起因：两个名称在 PyPI 上均被永久占用，不可转让复用；
    实测取证见 `harness/proposals/更名与迁移说明.md`）。同时修订：① 原则 III 的具体验收 API 名
    （`from freegraph.graph import ...`）；② 原则 V 门禁 4 的方法性措辞
    （socket 夹具改为「只观测不阻断 + 按发起方归因」，零出站证据改为「框架自身出站数 = 0」，
    不阻断用户代码出网）。**原则 I–X 的实质要求均未改变**，仅 API 名与方法措辞变化；
    迁移方案与受影响特性见 `harness/proposals/更名与迁移说明.md`。
    （说明：原「文件头 SYNC IMPACT REPORT」临时块已随 **v1.0.0** 移除——它属未提交前的草稿材料，
    且含已失效的描述（「立项书 §12.1 已关闭事项」「评审 1 未处置」）；修订记录以本节为准。）
  - **v0.0.2（2026-11-04）**｜**新增「发布门禁（Release Gate）」章节**（新增章节，
    按 0.x 预发布语义记为 **0.0.2**；MAJOR/MINOR 策略下本应记 MINOR，但项目未开工、
    宪法未批准，故按 0.x 语义记 0.0.2，待批准时统一定版）。
    - **变更了什么**：新增「发行产物纯度门禁」一条——构建产物 **MUST** 仅含包代码
      （`src/<pkg>/`）与必要元数据，**MUST NOT** 含任何仓库内容
      （`harness/` / `.specify/` / `.opencode/` / `node_modules/` 等）；
      **MUST** 以可自动执行的断言落地，并在发布流水线中于上传之前强制执行。
    - **为什么**：本仓库把**全部项目内容**放在 GitHub 上供读者学习原理，
      而 PyPI 上的发行包必须保持干净——仓库内容属开发辅助材料，
      不应被他人 `import` 引入。且 **PyPI 上的版本一旦发布不可删除**（只能 yank），
      必须在上传前拦截；仅靠打包配置（`only-include`）不足以保证——那是「配置」而非「机制」。
    - **受影响的原则与特性**：**原则 I–X 的实质要求均未改变**，原则 IX（许可证与商标红线）
      与原则 X（文档合规义务）亦未受影响；本条为**独立的新增门禁**，只约束**发布环节**。
      已在 §9.1（质量门禁）与 §5.2 B24F1（打包分发）同步引用。
    - **迁移方案**：无既有特性受影响（项目未开工）。落地物已就位：
      `harness/scripts/check_dist_purity.py`（断言，已用 `force-include` 做过负向验证）
      + `.github/workflows/publish.yml` 在 `uv publish` 之前插入该门禁
      + `pyproject.toml` 的 `only-include` / `exclude` 作为前置双保险。

  - **v1.0.0（2026-11-05）｜首次批准并定版**——本版由**立项书 §12 的 D11 与 D12** 触发，
    两项均为「M0 前置」（不阻塞 B1F1 的编码，但阻塞 B2F1 契约冻结与 B3F1 CI 门禁生效），
    现已由发起者**批准并落地**。
    - **变更了什么**（两处原则修订 + 一处 housekeeping）：
      1. **原则 VII 的 MINOR 修订**：契约清单的权威范围由 **C1–C26 扩为 C1–C27**
         （新增 **C27 = 本地 trace 存储与查询**：写入 / 查询（按 `thread_id` / 时间 / 节点名，
         可组合）/ **请求与返回结构 MUST JSON 可序列化** / 存储与查询同一协议且后端可替换 /
         表结构与文件格式属内部实现细节）；并**补齐标识与关联键约定**——
         `thread_id`（会话，`RunConfig` 承载）与 `run_id`（单次运行，运行时生成，用户不设置）
         的职责划分、**每个 span MUST 带** `thread_id` / `run_id` / 节点名 / `checkpoint_id`
         （缺 `run_id` 即为实现缺陷）、`stream()` 事件与 `TraceSink` 的 span **共享同一
         `run_id` / `thread_id`**。
      2. **原则 V 的方法性措辞（PATCH，= D12）**：零出站证据的实现口径由
         「socket guard **拦截**所有非 localhost 的 `socket.connect`，断言拦截列表为空」
         改为「socket **监测**夹具**只观测不阻断 + 按发起方归因**」——记录目标与调用栈后
         **放行**全部连接；调用栈含 `freegraph/` 包路径判为「框架出站」，否则判为「用户出站」；
         **只对前者断言 = 0**，用户出站**记录在案但不判失败**（人工轮允许「模型厂商端点」一条
         并须写明）。质量门禁第 4 项同步。
      3. **housekeeping**：移除文件头的临时「SYNC IMPACT REPORT」草稿块（其内容含已失效描述）；
         「演进触发」条目的契约范围同步为 C1–C27；目录约定补入 `harness/features/`
         （feature 提示词初稿 + 人工验证记录）。
    - **为什么**：① **C27 缺位**会让本地 trace 的存储与查询**无契约可依**，
      而它是 v1「三件套」之第 ② 件（trace 时间线 / 详情）的能力载体，且是将来 Studio 子包
      「只通过查询 API 取数、不直连 SQLite 表」这一边界的前提；**span 缺关联键**与
      **两条事件通道无共享标识**会让 trace 树无法与图结构 / checkpoint 历史对齐，
      届时 Studio 子包必须**改内核**才能补——三条缺口因此合并为 **D11** 一次修订。
      ② 零出站的「拦截式守卫」与 freegraph 的产品定位冲突（它是函数胶水 / 工作流框架，
      承诺「自己不会偷偷联网」，而非「你的程序不许联网」）；拦截式实现会阻断用户节点里的
      正常外网访问，属反直觉设计（立项书 §10 的 **R11**），故改为只观测 + 归因。
    - **受影响的原则与特性**：**原则 I–X 的实质要求均未改变**——
      原则 I「自身零出站、断网可用」不变；原则 V「MUST 有零出站的可判定证据」不变，
      仅**方法**由「拦截」改为「只观测 + 按发起方归因」；原则 VII「契约清单以 Q8 为唯一权威、
      MUST NOT 擅自增删条目」不变，本次是**经批准**的增补（Q8 §3.4.1 + 立项书 §5.3.1）。
      受影响特性：M0 的 **B2F1**（契约冻结前置解除）、**B3F1**（CI 门禁口径确定）、
      M3 的 **B8F2 / B18F1 / B19F1 / B20F1 / B20F2**（须实现 C22 / C23 字段约定与 C27）。
    - **迁移方案**：**无破坏性变更**——v1 尚未开工，**无已实现特性需要迁移**；
      C1–C26 的语义与编号**未变**（仅增补 C27 + 补齐字段约定）；已冻结的类型形状
      （`RunConfig` 四字段、`StateSnapshot` 七字段等）**不变**（`run_id` **不进** `RunConfig`，
      由运行时生成）。落地物：Q8 §3.4.1 · 立项书 §5.3 / §5.3.1 / §5.8.3 · 立项书 §12 的
      D11 / D12 状态与 §13.3 签署 · 本宪法原则 V / 原则 VII 正文与本条记录。

  - **v1.1.0（2026-11-05）｜MINOR —— 砍掉 `Store`（B17F1），并补入「通用图框架」定位**
    - **变更了什么**：① **项目定位**新增「定位补充」小节——freegraph 是**通用图框架**
      （不止智能体开发，还包括 **RPA 自动化**、**脚本编排**、在一定程度上**替代 `main` 函数**、
      **可视化工作流编排**），并据此确立「**图 = 一个进程**」这条范围边界；
      ② **原则 VII** 新增一条：`v1` **MUST NOT** 提供**跨会话 / 跨图**的长期记忆（`Store`）
      ——**B17 / B17F1 已从 v1 移除**（合计口径由 25 功能块 / 32 feature / 31,520 行 / 96 人日
      变为 **24 功能块 / 31 feature / 30,600 行 / 93 人日**），契约 **C20 仍冻结**（实现后补）；
      ③ `compile(store=...)` 关键字仍被接受但 v1 **背后无实现**，文档 MUST 显式写明；
      ④ **项目性质补充**：明确本项目是**个人开源项目**（作品集 / 名片 / 能力证明，
      非以盈利为直接目的），并据此锁定**许可证 = MIT**（D3，2026-11-05）——
      MIT 的**单向兼容性**最大化下游采纳面；Apache-2.0 的额外条款对本项目均为空条款。
    - **为什么**：发起者 2026-11-05 决议——Store 是**跨会话 / 跨图**能力，而 freegraph 的初衷
      是做成**通用图框架**（智能体 / RPA / 脚本 / 可视化工作流编排），这类场景的共同前提是
      「**图 = 一个进程**」；跨图能力**太复杂，且违背初衷** → 砍掉。这是一条**定位推导出的
      硬边界**，不是「先不做再说」的临时取舍。附带收益：省 3 人日 / 920 行。
    - **受影响的原则与特性**：**原则 I–X 的实质要求均未改变**——原则 VII 原本就要求
      「MUST NOT 擅自增删契约条目」，本次是**经批准的**范围收缩（C20 保留、不删不改）；
      原则 IV（四类诊断能力）不受影响（Store 不在其依赖链上）；原则 IX / X 不受影响。
      受影响特性：立项书 §12 **D5**（Store 与 Studio UI 一并归 v2）、§4.6、§5.2（删 B17F1 行）、
      §6 / §7（totals：94 天 / 93,000 元 / 186,000 元）。
    - **迁移方案**：**无破坏性变更**——v1 尚未开工，**无已实现特性需要迁移**；C1–C27 的
      语义与编号**未变**（仅 C20 的 v1 归属标为「已砍 / 实现后补」）；
      `harness/features/B17F1_*.md` 初稿已删除，`harness/features/README.md` 的行序表
      与里程碑 / 关键路径视图已同步为 31 feature。

  - **v1.2.0（2026-11-05）｜MINOR —— 剥离 `typing-extensions`（基础安装零依赖）+ 最低 Python 版本抬至 3.11**
    - **变更了什么**：① **依赖白名单**的**必装运行时依赖由 `typing-extensions` 改为「无」**
      ——`pyproject.toml` 的 `dependencies` 改为 **空列表**，基础安装的依赖闭包 **MUST 为空集**；
      ② **最低 Python 版本由 `>=3.10` 抬至 `>=3.11`**（`requires-python`）；③ 质量门禁第 2 项
      补入「基础安装闭包 MUST 为空集」的可判定口径；④ `THIRD_PARTY_NOTICES` §2
      「第三方运行时依赖」表随之清空（§1「引入的第三方代码」本已为空）。
    - **为什么**：
      ① **原依赖的存在理由本身是错的**——立项书 §5.4（E18 / 第 190 行）把最低版本定为
      ≥3.10 的理由写作「`typing.Protocol` / `TypeAlias` / **`Self`** 在 3.10 起可用」，
      但 **`typing.Self` 是 3.11 才进入标准库的**（实测 Python 3.10.21 无 `Self`）；
      且同一行本已写明「`typing-extensions` 只需兜底少数新特性，**不作为最低版本约束**」。
      ② **实测证明 3.10 的标准库足以支撑 v1 全部 31 个 feature**：31 份 feature 提示词用到的
      typing 构造只有 `Annotated`(20) / `Protocol`(8) / `TypedDict`(7) / `runtime_checkable`(1) /
      `get_type_hints`(1)，**全部是 3.10 标准库成员**；`Self` / `NotRequired` / `TypeVarTuple` /
      `Unpack` / `LiteralString` / `dataclass_transform` / `asyncio.TaskGroup` /
      `ExceptionGroup` 在提示词中出现 **0 次**（B12F1 FR-008 明写「本 feature **不引入 async**
      （v2 范围）——并发用**线程**实现即可」）。缺口可用标准库惯用法闭合：
      `Self` → `TypeVar` bound 惯用法、`assert_never` → `NoReturn`、
      `Required`/`NotRequired` → 结构化识别（freegraph 自身**不需要命名**它们，鸭子类型哲学）。
      ③ **既然缺口要用惯用法绕，不如抬到 3.11 一次拿齐**：3.11 一次性补齐 7 项 typing
      （`Self` / `NotRequired` / `Required` / `TypeVarTuple` / `Unpack` / `LiteralString` /
      `dataclass_transform`），而 3.12 与 3.13 **各只补 2 项**（3.12：`TypeAliasType` / `override`；
      3.13：`ReadOnly` / `TypeIs`）——3.11 的「typing 增量 / 兼容面损失」性价比最高；
      ④ **Python 3.10 已于 2026-10 结束安全支持**（本版定稿于 2026-11）——为一个即将 v1.0 的
      新项目把底线定在一个**已停止安全支持**的 Python 上，是不该做的决定；
      ⑤ 附带收益：`pip install freegraph` 将**安装零个包**，README 的「零第三方运行时依赖」
      承诺第一次**字面为真**（此前是「只有一个包」，读起来仍像打折）。
    - **受影响的原则与特性**：**原则 I–X 的实质要求均未改变**——原则 I（零 LangSmith 依赖）
      不变且**更严**（闭包从「一个包」收紧为「零个包」）；原则 II（内核纯净）不变；
      原则 IX 的**许可证白名单 {MIT, Apache-2.0, BSD-2/3, PSF} 不变**（删除一个依赖不与该白名单冲突，
      且剥离后闭包为空、白名单校验**恒通过**）；原则 X（文档合规义务）不变，
      只是 `THIRD_PARTY_NOTICES` §2 的登记项由「有一行」变为「空表」。
      受影响特性：**B1F1**（本 feature 的依赖闭包门禁 G3 由「闭包 == {typing-extensions}」
      改为「闭包 == 空集」；契约层实现**零改动**——实测其从不 import 该包）；
      **B3F1**（CI 矩阵最低版本由 3.10 改 3.11、依赖门禁断言改写）；
      **B24F1**（打包元数据 `Requires-Dist` 由一条变零条、`Requires-Python` 抬版本）；
      **B2F1 / B4F1 / B6F1**（可用 `Self` / `NotRequired` 等 3.11 typing，**MUST NOT** 再 import
      `typing_extensions`）。
    - **迁移方案**：**无破坏性变更**——v1 尚未发布任何含内核实现的版本，**无已实现特性需要迁移**；
      已冻结的类型形状（`StateDict` / `Command` / `StateSnapshot` / `RunConfig` 四类型 + 异常体系
      共 8 个符号）**完全不变**——本次只改**依赖声明**与**解释器版本下限**，
      **MUST NOT** 触及任何公开符号名、字段名、字段注解或行为。
      已在 PyPI 占位发布的 **v0.0.2**（`Requires-Dist: typing-extensions>=4.7.0`、
      `Requires-Python: >=3.10`）是**历史事实，不予改写**；下一次发布以 **v0.0.3** 为准
      （`Requires-Dist` 无、`Requires-Python: >=3.11`）。
      落地物：`pyproject.toml` · `.specify/memory/constitution.md`（本条 + 依赖白名单 + 质量门禁第 2 项）·
      `harness/proposals/立项书.md`（§5.4 E18 / §5.5 / §12）· `specs/b1f1-contracts-core/`
      （spec FR-007 / SC-002 · plan · research · tasks · quickstart · architecture-gates G3）·
      `tests/contracts/test_architecture.py`（G2 / G3 / G8 断言）· `README.md` · `THIRD_PARTY_NOTICES`。

> **2026-11-04 补充（不影响版本号）**：`freegraph` 已在 PyPI 上占位发布 **v0.0.1**
> （owner = PyPI 账号 `yangjiacheng1996`，发行名 = 导入名 = `freegraph`；
> 发布通道 = GitHub Actions Trusted Publishing（OIDC），工作流
> `.github/workflows/publish.yml`，无需 API token / 密码）。该版本**不含任何内核实现**，
> 仅用于锁定名称；`freechain` 亦已于同日占位发布 v0.0.1。**规范性正文与原则 I–X 全部未改动**，
> 故**不 bump 版本号**（Version 仍为 0.0.1，Last Amended 仍为 2026-11-03）。
>
> **2026-11-05 补充（仍为占位版，bump 到 v0.0.2）**：`freegraph` 发布 **v0.0.2**——
> 目的有二：① **实测「发行产物纯度门禁」**（发布门禁 Release Gate 自 v0.0.2 起首次在真实
> 发布链路上执行；本地已双向验证：污染产物 → 门禁失败并拒绝发布；干净产物 → 通过）；
> ② **落实原则 X 的「源文件署名头」义务**——每个源文件带
> `Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph`。
> 该版本**仍不含任何内核实现**，仅用于锁定名称 + 验证发布链路。**原则 I–X 全部未改动**
> （版本号属发行元数据，非规范性正文）。
>
> **发布结果（2026-11-05，已验证）**：`freegraph 0.0.2` 发布成功；**发行产物纯度门禁在真实
> 发布链路上首次执行并通过**（此前只做过本地验证）。远端产物独立复核：
> wheel 仅含 `freegraph/__init__.py` + `freegraph/py.typed` + dist-info；sdist 仅含
> `src/freegraph/` + README + LICENSE + pyproject + PKG-INFO；**无 `harness/` / `.specify/` /
> `.opencode/` 等任何仓库内容**；元数据 `License: MIT`、`Requires-Dist: typing-extensions>=4.7.0`
> （**仅一个必装依赖**）、`Requires-Python: >=3.10`；**源文件署名头已随包发布**
> （`freegraph/__init__.py` 第 1 行即 `Copyright (c) 2026 杨家成 · MIT License · <仓库地址>`）。
> → **发布门禁（Release Gate）自此从「机制」变为「已验证生效的机制」。**
>
> **2026-11-05 补充（下一版 v0.0.3 将改元数据；v0.0.2 的历史记录不改写）**：
> 依本宪法修订记录 **v1.2.0**（剥离 `typing-extensions`、最低 Python 抬至 3.11），
> 下一次发布将改为 **`Requires-Dist` 无（零第三方运行时依赖）**、
> **`Requires-Python: >=3.11`**，版本号 **v0.0.3**。
> 上文 v0.0.2 的 `Requires-Dist: typing-extensions>=4.7.0` / `Requires-Python: >=3.10`
> 是**已发布的事实**，**MUST NOT** 改写——它是「历史」而非「现状」。
> 本次变更**不触及**任何原则 I–X 的实质要求，也**不触及**任何已冻结的公开面
> （`freegraph.contracts` 的 8 个符号、字段名、字段注解与行为**全部不变**）。

  - **v1.3.0（2026-11-05）｜MINOR —— 新增「运行时环境基线」章节：最低 Python 3.11 且 typing 构件不得高于 3.11**
    - **变更了什么**：新增章节 **「运行时环境基线（Python 版本与 typing 构件上限）」**
      （位于「质量门禁与交付流程」之下，紧随「依赖白名单 / 黑名单」），规定两条硬约束：
      ① **最低版本 = 3.11**（`requires-python` MUST 为 `>=3.11`）；
      ② **typing 构件上限 = 3.11** —— 源码 **MUST NOT** 出现
      `TypeAliasType`（PEP 695）、`override`（PEP 698）、`ReadOnly`（PEP 705）、
      `TypeIs`（PEP 742）或 PEP 695 的 `type` 语句语法（均为 3.12+ / 3.13+ 构件）。
      本条**明确给出判定口径**：① **主判定 = CI 矩阵最低档 MUST 为 3.11 且跑全量测试**
      （3.12+ 构件在该档天然不可用）；② **辅判定 = 架构门禁 G9** 以 `ast` 静态扫描
      并给出可读报错；③ 人工判定以「该构件首次进入 stdlib 的版本 ≤ 3.11」为准。
      同时明确「本机 Python 是 3.12/3.13 所以能用」**不是**理由。
    - **为什么**：v1.2.0 把最低版本抬到 3.11 之后，「3.11 是下限」这条承诺就**只存在于
      `pyproject.toml` 的一行字与文档里**——代码层面并无约束。Python 的 typing 是
      **只增不减**的演进序列，开发者会不知不觉地用上本机新版本才有的构件，
      把承诺在**代码里**悄悄破掉；而这种破坏**不会在开发机上暴露**，
      只在用户装包时才炸（`ImportError` / `AttributeError` / `SyntaxError`）。
      设上限 + 可自动判定，是把承诺**钉进代码**而不是钉进文档。
      另：v1.2.0 已把 `typing-extensions` 剥离，若不加此约束，
      开发者很可能在「反正要写 `Self`」时把 `typing_extensions` 加回来——
      那会把刚兑现的「零第三方依赖」推倒。**两条约束互为闭环。**
    - **受影响的原则与特性**：**原则 I–X 的实质要求均未改变**——原则 II（内核纯净）
      的要求**不变**（仍是「零 langchain」），本条是**与之叠加**的独立约束，
      二者合起来的结果是「内核 MUST NOT 需要任何第三方包即可运行」；
      原则 IX（许可证与商标红线）不涉及；原则 X（文档合规义务）不涉及。
      **本条本身不是一条新原则**（未新增「原则 XI」），而是交付流程下的一个章节——
      理由：全仓库约 30 处文档以「原则 I–X」作交叉引用，新增原则会引发大范围措辞返工，
      而本条的**性质是工程约束**（决定能写出什么代码），不是**价值取向**（决定为什么）。
      受影响特性：**全部 31 个 feature**（每个 feature 的实现都受此约束）；
      **B3F1**（CI 矩阵最低档 MUST 为 3.11，且须跑全量测试——这是本条的**主判定**）；
      **B4F1 / B6F1 / B7F1 / B8F3**（`Self` / `NotRequired` / `TypeVarTuple` /
      `Unpack` 等**恰好**在 3.11 可用，故这些 feature **不受影响**）；
      **B2F1**（四类协议的协议定义 MUST 只用 ≤3.11 构件）。
      **已冻结的公开面不受影响**——`freegraph.contracts` 的 8 个符号、
      字段名、字段注解与行为**全部不变**（其注解本就在 3.11 标准库内）。
    - **迁移方案**：**无破坏性变更**——本条约束的是**未来**写出的代码，
      不要求任何既有代码改动；已交付的 `freegraph.contracts`（v0.0.3）
      **本已合规**（实测：其全部 typing 构件均 ≤3.11）。
      落地物：宪法「运行时环境基线」章节（本条）·
      `tests/contracts/test_architecture.py` 的 **G9** 静态断言（含门禁自检）·
      `harness/proposals/立项书.md` §5.4 E18 与最低版本行（补「typing 构件上限」）·
      `harness/features/B3F1_项目脚手架与CI门禁.md`（CI 矩阵最低档 + G9 门禁）·
      `specs/b1f1-contracts-core/`（plan / research D-21 / architecture-gates G9）。
    - **housekeeping（同批）**：① **人工验证记录迁出 `harness/features/`**——
      新增顶层目录 **`harness/verification/`**，按 feature 分目录存放
      `<feature>/manual-verification.md`（`<feature>` = feature ID，如 `B1F1`）。
      **理由**：`harness/features/` 是**feature 提示词初稿**的目录（每 feature 一份
      `/speckit.specify` 提示词），把**人工验证记录**混在其中会让
      「提示词」与「验收产物」两类性质完全不同的文档混在一个目录里；
      独立成目录后，「每个 feature 的验收记录在哪」是一个**一眼可见**的约定。
      ② 已同步全仓 **38 处**路径引用（30 份 feature 提示词 + 立项书 + guide.md +
      更名说明 + 本层 plan / quickstart / tasks）。③ 宪法「目录约定」表同步补行。
      **迁移方案**：路径变更，**不影响**任何原则的实质要求与任何已冻结的公开面；
      已用 `git mv` 保留文件历史（GitHub 上显示为 rename 而非 delete + add）。

  - **v1.4.0（2026-11-05）｜MINOR —— 统一开发层级词表：Phase → feature、Feature → 功能块、域 → 领域**
    - **变更了什么**：新增「术语约定」下的**开发层级词表（四层）**，并据此把全仓库的
      术语与 ID 统一：
      | 层级 | 旧称 | 新称 | ID |
      |---|---|---|---|
      | 1 | 层 | **层** layer | `L1`–`L6`（不变） |
      | 2 | 域 | **领域** area | `A1`–`A8`（ID 不变） |
      | 3 | **Feature** | **功能块** block | `F<n>` → **`B<n>`** |
      | 4 | **Phase** | **feature** | `F<n>P<m>` → **`B<n>F<m>`** |
      同时：立项书 §5.2 执行明细表**新增「领域」列**（此前「领域」只存在于 §4.4 体量表，
      日常开发看不见）；`harness/features/` 的 31 份提示词初稿与
      `harness/verification/B1F1/`、`specs/b1f1-contracts-core/` 同步重命名。
    - **为什么**：**一词二义**是本项目最持久的概念混淆源——立项书的「Phase」与
      speckit 的「feature」**同名不同义**（speckit 的一次闭环 = 一个 feature =
      立项书的「Phase」），而立项书的「Feature」层级又与 speckit 的「feature」
      **同名不同义**（前者是含 1–3 个 Phase 的交付单元，后者是最小闭环）。
      开发时用 `/speckit.implement` 拆 tasks 成多个「Phase」，与立项书的「Phase」
      撞车，徒增沟通成本。统一后：**feature = 最小开发单位 = speckit 闭环**
      （与工具链天然对齐），**功能块 = 交付单元**，**领域 = 交付分组**，**层 = 代码归属**——
      四层各一个字母，互斥且不可混用。
    - **受影响的原则与特性**：**原则 I–X 的实质要求均未改变**；**已冻结的公开面
      （`freegraph.contracts` 的 8 个符号 / 字段名 / 字段注解 / 行为）完全不变**——
      本次只改**项目自身的开发术语与 ID 命名**，不触及任何用户可见的 API。
      受影响：全部 31 个 feature 的文档与 ID；立项书 §4.4 / §5.2；宪法「目录约定」与
      「术语约定」；`harness/features/` 导航；`harness/verification/`；`specs/` 目录名；
      `harness/prompts/guide.md` 与 `harness/prompts/old.md`（后者加失效横幅，不改写原文）。
    - **迁移方案**：**无破坏性变更**——改名不改变任何交付内容与行为；改动为
      **ID 与散文措辞**两类，已用脚本批量执行并逐项校验（`F<n>P<m>` 1597 处、
      裸 `F<n>` 340 处、散文 828 + 191 处、文件名 31 份）；
      `.specify/templates/` 与 `.specify/scripts/`（speckit 工具链自身）**原样不动**——
      其中的 "feature" 本就指 speckit 的 feature，改名后**恰好与新体系一致**。
       附带修复：立项书 §4.4 表头叫「域」而正文叫「家族体量」的**自相矛盾**，
       本次一并统一为「领域」。

  - **v1.4.1（2026-11-06）｜PATCH —— 修正 v1.3.0 目录迁移遗留的 2 处路径残留（人工验证记录）**
    - **变更了什么**：把**原则 V 正文**与「**质量门禁第 5 项**」两处的人工验证记录路径
      由 `harness/features/<feature>/` 更正为 **`harness/verification/<feature>/manual-verification.md`**；
      并在原则 V 处补一句「该目录为人工验证记录的**唯一**约定位置，`harness/features/` 只放
      feature 提示词初稿，两者 MUST NOT 混放」。
    - **为什么**：**v1.3.0 的 housekeeping 已把人工验证记录整体迁出 `harness/features/`**
      （新增 `harness/verification/`，并同步全仓 38 处路径引用 + 补入「目录约定」表），
      但**这两处漏改**——导致同一份宪法内部自相矛盾：正文说记录在 `harness/features/<feature>/`，
      而「目录约定」表与「术语约定」说在 `harness/verification/<feature>/`。
      后果是：① 规范正文与仓库现状冲突（实现时不知该落哪）；② 质量门禁第 5 项的
      「人工门禁」按字面无法被判定为通过；③ 后续 feature 会各自猜测路径 → 目录重新混放。
      该残留在 **B2F1 的文档一致性复核**中被发现并修正（属 v1.3.0 迁移的收尾，非新要求）。
    - **受影响的原则与特性**：**原则 I–X 的实质要求均未改变**——原则 V 的核心义务
      （「自动测试通过**不等于**验收通过」「每个特性 MUST 有人工验证记录」
      「记录 MUST 写明验证环境 / 步骤 / 实际输出 / 结论 / 遗留问题」「MVP 验收基线 MUST 双跑」）
      **一字未动**；本次只更正**落盘路径**这一实施细节，使正文与「目录约定」表、
      与仓库现状（`harness/verification/{B1F1,B2F1}/manual-verification.md`）
      三者一致。质量门禁第 5 项的**判定口径不变**（仍要求「完整人工验证记录 + 真实模型一轮」）。
      受影响特性：**全部 31 个 feature 的人工验证记录落盘位置**（此前 B1F1 已按
      `harness/verification/` 实际落盘，属「先做对了、文档没跟上」；本次只把文档补齐）。
    - **迁移方案**：**无破坏性变更**、**无文件迁移**——路径早在 v1.3.0 就已迁移完毕，
      本次只改宪法文本中 2 处残留；已实现特性的代码与文档**零改动**。
      落地物：本宪法原则 V 正文 + 质量门禁第 5 项 + 本条修订记录 + 页脚版本号；
      **同批修正「模板 / 引导文档」里的同源残留**（否则下一次 `/speckit.constitution`
      会把旧路径重新生成回宪法）——`harness/prompts/init_constitution.md`
      （原则 V 正文 + 目录约定表 + 质量门禁第 5 项）· `harness/prompts/guide.md`（规格门禁行）·
      `harness/prompts/why_this_project.md`（人工记录路径）· `harness/demo/README.md`
      （`--record` 示例路径）。
      （按「版本策略」，本条属**措辞/路径残留的非语义性修订** → 记 **PATCH**，
      版本号 **1.4.0 → 1.4.1**；发起者 2026-11-06 批准。）

  - **v1.4.2（2026-11-07）｜PATCH —— 修正「术语约定」里 `specs/` 目录命名的一处过期表述**
    - **变更了什么**：把「术语约定 · 开发层级词表」的「参考」条目中
      `specs/<NNN>-<short-name>/` 更正为 **`specs/<feature-id>-<short-name>/`**，
      并补一句「**直接用规划 ID，不带** Speckit 的三位序号（见 `harness/prompts/guide.md` §4.7）」。
    - **为什么**：本条是 **v1.4.0** 术语统一时的**遗漏**——那一版已把 `specs/001-p01-contracts-core/`
      重命名为 `specs/b1f1-contracts-core/`（修订记录 v1.4.0「受影响」栏明列
      「`specs/` 目录名」），但「参考」条目的**写法**仍是改名前的 `<NNN>-` 形态
      ⇒ 同一份宪法内部与仓库现状**自相矛盾**：B1F1 / B2F1 的实际目录**都不带序号**，
      而宪法文字说带。该矛盾在 **B2F2 的文档一致性复核**中被发现：
      B2F2 的目录被 Speckit 的自动编号器建成了 `specs/001-b2f2-public-api-facade/`，
      正是照着这条过期表述（或照着工具链默认值）建出来的 ⇒ 同一约定下出现了**两种目录名**。
      修正后与 `harness/prompts/guide.md` §4.7「本仓库的目录命名约定（2026-11-05 定）」
      （「feature 目录**直接用规划 ID** …… **不带** Speckit 的三位序号」）**一致**，
      也与三个 feature 的实际目录一致。
    - **受影响的原则与特性**：**原则 I–X 的实质要求均未改变**——本次只更正
      「术语约定 · 参考」里**一个目录名写法**，属**措辞/路径残留的非语义性修订**；
      原则 VI（规格驱动开发）与原则 VIII（证据与术语纪律）的**判定口径不变**
      （仍要求 spec 可追溯、术语准确）。
      受影响特性：**全部 31 个 feature 的 speckit 产物目录**——B2F2 的目录已由
      `specs/001-b2f2-public-api-facade/` 更名为 `specs/b2f2-public-api-facade/`，
      与 B1F1 / B2F1 同形；**分支名同步**为 `b2f2-public-api-facade`。
    - **迁移方案**：**无破坏性变更**、**无代码改动**——speckit 工具链的路径解析
      只认 `.specify/feature.json` 的 `feature_directory`（`common.sh` 的
      `resolve_feature_dir`），**不依赖目录名格式** ⇒ 目录更名 + 同步更新
      `.specify/feature.json` 与**全仓 19 处路径引用**即可
      （`check-prerequisites.sh --json --require-spec --require-tasks` 已实测通过，
      `FEATURE_DIR` 正确解析为 `specs/b2f2-public-api-facade`）。
      落地物：本宪法「术语约定 · 参考」条目 + 本条修订记录 + 页脚版本号；
      **同批修正「引导文档」里的同源残留**（否则下一次 `/speckit.constitution`
      会把旧写法重新生成回宪法）——`harness/prompts/guide.md` 的
      §4.2 切分规则 **PR-1** 与 §4.6 质量门禁落地表的「规格门禁」行
      （两处 `specs/NNN-*` → `specs/b<n>f<m>-<slug>/`）。
      （按「版本策略」，本条属**措辞/路径残留的非语义性修订** → 记 **PATCH**，
      版本号 **1.4.1 → 1.4.2**；发起者 2026-11-07 批准。）

  - **v1.5.0（2026-11-08）｜MINOR —— 收敛 `[png]` extra 的包层白名单条目：类别式表述 → 确切包名**
    - **变更了什么**：把「依赖白名单 / 黑名单」条之**包层白名单**列表项的末项
      「mermaid 相关（`[png]`，**默认关闭**）」替换为
      「**`playwright`（`[png]`，**默认关闭** · 本地 Chromium 渲染 · 许可证 Apache-2.0）**」，
      并在该条下追加一段修订注记，写明 `[png]` extra 的三条硬约束：
      **(a) 默认关闭**（不装即不可用，基础安装 MUST NOT 拉起其依赖）；
      **(b) 依赖闭包 MUST 全部落在原则 IX 的许可证白名单 {MIT, Apache-2.0, BSD-2/3, PSF} 内**；
      **(c) 零出站**（MUST NOT 依赖任何远程渲染服务——`mermaid.ink` 仍在网络层黑名单内）。
      另：浏览器二进制由用户**显式**执行 `playwright install chromium` 获取（属**安装期**动作）
      ⇒ 基础安装的零第三方运行时依赖承诺不受影响。
      **其余各条一字未动**：包层 / 配置层 / 网络层 / 核心层四条黑名单、原则 I–X 的正文
      实质要求、「运行时环境基线」章节、「质量门禁 1–7」、「发布门禁」、「目录约定」
      与「术语约定」全部原样。
    - **为什么**：
      ① **实测**：原则 IX 白名单严格口径（{MIT, Apache-2.0, BSD-2/3, PSF}）下，
      **全部纯 Python SVG→PNG 后端实测被拒** —— `cairosvg` / `svglib` / `pycairo` = **LGPL**
      （传染性）· `pillow` = **`MIT-CMU` / `HPND`**（同族变体标识符不放行）· `matplotlib` 的闭包含
      `pillow` 且 `numpy` 的 SPDX 表达式含 `0BSD` / `Zlib` / `CC0-1.0` · `pymupdf` = **AGPL** ·
      `resvg-py` = **无任何许可证信息** ⇒ **`playwright` 是唯一闭包全绿的后端**
      （Apache-2.0；闭包 `greenlet` / `pyee` / `typing-extensions` 皆白名单）。
      （来源：`harness/proposals/立项书.md` §5.5「PNG 渲染的候选方案与取舍」表及其下的
      「v1 口径（D14 修订后）」注记 —— **2026-11-07 · D14 实测**。）
      ② **上位决议**：立项书 §12 的 **D14** 已于 **2026-11-07** 由发起者确认——
      `[png]` = `playwright`，v1 即交付**两段式**（未装 = 占位 PNG；装了 = 本地真实渲染，
      运行期零出站，浏览器二进制属安装期动作）。
      ③ **可判定性缺口**（本次修订的直接动因）：「mermaid 相关」既**非确切包名**、
      也**非有限集合** ⇒ **无法**被 B3F1 的新门禁 **G23**（许可证白名单 · 四级证据链 ·
      fail-on-missing）核验、**无法**被 **G21**（依赖闭包 · 递归展开）枚举
      ⇒ 门禁在该条上**不可判定**；且同一条里 `[otel]` 已是「取宪法白名单**原文所列**」的
      逐包名列（`opentelemetry-api` / `opentelemetry-sdk`，**不含**任何 exporter），
      `[png]` 却把后端下放给 plan ⇒ **同一份宪法内两套取法**。本次统一为「逐包名列」。
      ④ **方向是收窄而非放宽**：原表述无确切包名 ⇒ 收敛后**唯一可能引入的包 = `playwright`**，
      其许可证 Apache-2.0 ∈ 原则 IX 白名单 ⇒ 与「不得放宽白名单」的方向一致。
      ⑤ **原则 VIII 的证据纪律**：调研报告 `harness/reports/Q3-LangGraph的开源边界.md` §3.6 与
      `harness/reports/00-调研总览与MVP范围建议.md` §8 里的「mermaid 相关」是**历史调研原文**，
      按原则 VIII「事实性结论 MUST 附来源标记、MUST NOT 改写历史」**不动**——
      本条以「修订记录」形式记录其已被 v1.5.0 收敛。
    - **受影响的原则与特性**：**原则 I–X 的实质要求均未改变**——原则 I（自身零出站）**更明确**
      （`[png]` 的 (c) 零出站 + `mermaid.ink` 仍在网络层黑名单内）；原则 II（内核纯净）不变；
      **原则 IX 的许可证白名单 {MIT, Apache-2.0, BSD-2/3, PSF} 不变**
      （`playwright` = Apache-2.0 ∈ 白名单；本条**不引入**任何新许可证、不放宽任何变体标识符）；
      原则 X / 质量门禁 1–7 / 「运行时环境基线」（Python 3.11 · typing 上限 3.11）均不变。
      受影响特性：
      · **B3F1** —— extras 划分 = **4 个** extra；既有门禁 **G3** 的占位白名单由 4 个占位包名
        扩为**四个 extra 真实闭包的 12 个确切包名**（`annotated-types` / `greenlet` /
        `opentelemetry-api` / `opentelemetry-sdk` / `opentelemetry-semantic-conventions` /
        `ormsgpack` / `playwright` / `pydantic` / `pydantic-core` / `pyee` /
        `typing-extensions` / `typing-inspection`）——**有限集合 · 逐个列名 · 无通配符**；
      · **B23F1** —— PNG 交付形态 = **两段式**（未装 `[png]` = 占位 PNG；装了 = 本地真实渲染）；
      · **B24F1** —— 打包元数据的 `Requires-Dist` 多出 4 组 `extra ==` 标记条目，
        **基础安装的依赖闭包仍为空集**。
    - **迁移方案**：**无破坏性变更**——v1 未发布任何含内核实现的版本，
      **无已实现特性需要迁移**；**已冻结的公开面完全不变**（`freegraph.contracts` 的 18 个符号、
      门面 7 个符号、API 签名快照、C1–C27 契约清单）——本次**只改依赖声明的白名单表述**，
      MUST NOT 触及任何公开符号名、字段名、字段注解或行为；
      **已发布的历史版本元数据（PyPI 上的 v0.0.1 / v0.0.2 / v0.0.3）是历史事实，不予改写**。
      落地物：本宪法「依赖白名单 / 黑名单」条（本条）· 本条修订记录 · 页脚版本号
      （**1.4.2 → 1.5.0**）；**待同批同步（本次修订命令范围外，须手工跟进）**：
      `harness/proposals/立项书.md` §5.5 包层白名单行与 §12 的 D14 行（同步副本）·
      `harness/features/B3F1_项目脚手架与CI门禁.md` 的 `[png]` 表述
      （= 后续 `/speckit.specify` 的输入）· `specs/b3f1-scaffold-ci-gates/` 的 spec
      （FR-001 / 裁定 11 引用宪法 v1.5.0）。
      **（同批同步已于 2026-11-08 完成 —— 三处均已落地，此条不再是待办）**：
      立项书 §5.5 包层白名单行 + §12 的 D14 行 · `harness/features/B3F1_*.md` 的 `[png]` 表述（= `playwright`）·
      `specs/b3f1-scaffold-ci-gates/` 的 spec（FR-001 / FR-004 ② / 裁定 11 / 引文差异说明第 ⑧ 条）。
      （按「版本策略」，本条属**对既有条款的实质性扩充**（把不可判定的类别表述改为确切包名
      + 新增 3 条 MUST 子条件）→ 记 **MINOR**，版本号 **1.4.2 → 1.5.0**；
      发起者 2026-11-08 批准。）

  - **v1.6.0（2026-11-08）｜MINOR —— 新增「质量门禁的分阶段落地与发起者追认」通则**
    - **变更了什么**：在「质量门禁与交付流程」章节下**新增一个子章节**
      「**质量门禁的分阶段落地与发起者追认**」（位于「质量门禁」清单之后、「发布门禁」之前），
      规定一条**通用处置规则**——当某条**质量门禁**在当前 feature **物理不可达成**
      （根因 = 该 feature 按里程碑**不交付其前置能力**，典型如「MVP 验收基线的跑通需要内核运行时，
      而内核运行时按 立项书 §6.2 属 M2」）时，MUST 以
      「**偏离登记 + 发起者追认**」处置，二者**缺一不可**；并写明**窄口径的适用范围**、
      **四条红线（MUST NOT 放宽判据 / MUST NOT 写永久红 CI / MUST NOT 当长期豁免 / MUST NOT 删改宪法正文）**
      与**登记与复核**要求。
      **原则 I–X 的正文与语义**、**质量门禁 1–7 各项的判据**、**发布门禁**、
      **依赖白名单 / 黑名单**、**运行时环境基线**、**目录约定**与**术语约定** —— **一律未动**。
    - **为什么**：
      ① **结构性张力**已被显式记录在案：「每个特性在合入前 MUST 全部通过」与
      「M0 地基 feature 不具备跑验收基线的能力」**不能同时成立**——
      若无通则，任何地基类 feature 都会面临「要么写一条永久红的 CI、要么静默稀释宪法」的二选一，
      两者都违反本宪法的自身要求；
      ② 此前 B3F1 的处置（`spec.md` 裁定 22 · `plan.md` 登记项 R-4 · `tasks.md` T057）
      是**逐 feature 的一次性安排**，其「宪法层面的已知张力」只在 B3F1 的文档里登记，
      **宪法本身没有对应的通则** ⇒ 下一个遇到同类情形的 feature 会重新踩坑；
      ③ 本条**不削弱任何红线**：被允许延后的**只有依赖内核运行时的能力型门禁项**，
      而依赖红线 / 许可证红线 / 商标红线 / 零出站红线**MUST 在每个 feature 落地**；
      ④ 本条**可被判定**：偏离登记与追认留证**都是人工可核对的工件**
      （feature 的 `plan.md` + `tasks.md` + `manual-verification.md`），
      满足 Governance「新增条款是否可被自动化检查或人工检查明确判定」的复核要求。
    - **受影响的原则与特性**：**原则 I–X 的实质要求均未改变**——本条是**交付流程章节下的一个流程性条款**，
      **不是**第十一条原则（理由与「运行时环境基线」章 v1.3.0 的处理同源：它是**工程流程**约束，
      不是**价值取向**；且全仓库大量文档以「原则 I–X」作交叉引用，新增原则会引发大范围措辞返工）。
      **质量门禁 1–7 的判据未变**；本条只提供「某条门禁在特定 feature 不可达成时」的**唯一合法出口**。
      **受影响特性**：**B3F1**（首次适用 —— 其偏离登记与追认任务 **T049 / T057** 即依本条执行）；
      **后续同类 feature**（任何按里程碑不交付内核运行时的地基类 / 前置类 feature）。
    - **迁移方案**：**无破坏性变更**——v1 尚未发布任何含内核实现的版本，
      **无已实现特性需要迁移**；**已冻结的公开面完全不变**
      （`freegraph.contracts` 的 18 个符号、门面 7 个符号、API 签名快照、C1–C27 契约清单）——
      本次**只新增一条流程性条款**，MUST NOT 触及任何公开符号名、字段名、字段注解或行为。
      **B3F1 侧的落地**：其 `spec.md` / `plan.md` / `tasks.md` 中原「宪法尚无通则 ⇒ 属一次独立的宪法 MINOR 修订」
      的登记文字**由本条关闭**（该登记项**已消解**，不再需要另起一次修订）；
      B3F1 的**偏离登记（R-4）与追认任务（T057）内容不变**，仍须由发起者在合入前完成追认。
      **同步落点**：本宪法（新增章节 + 本条修订记录 + 页脚版本号 **1.5.0 → 1.6.0**）·
      `harness/prompts/init_constitution.md`（同批补入该章节，避免下次重新生成时丢失）·
      `specs/b3f1-scaffold-ci-gates/`（spec 裁定 22 / Assumptions · plan 登记项 R-4 · tasks T057 的
      「宪法尚无通则」表述改为「已由宪法 v1.6.0 确立通则」）。
      （按「版本策略」，本条属**新增章节** → 记 **MINOR**，版本号 **1.5.0 → 1.6.0**；
      发起者 2026-11-08 批准。）



**Version**: 1.6.0 | **Ratified**: 2026-11-05（发起者批准；首次批准即定版为 1.0.0） | **Last Amended**: 2026-11-08
