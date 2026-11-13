# freegraph 初始宪法（init_constitution）

> **用法**：本文件是 freegraph 项目的**初始宪法草案**，用于 `/speckit.constitution` 命令的输入。
>
> - 宪法正文位于本文件的 `<!-- CONSTITUTION-BODY-START -->` 与 `<!-- CONSTITUTION-BODY-END -->` 之间，
>   **只有这一段是宪法内容**；上面的说明与下面的注意事项都不是。
> - **推荐用法**：执行 `/speckit.constitution`，把下面宪法正文整段作为参数传入；命令会套用官方模板、
>   填写占位符、递增版本号，并把最终结果写入 `.specify/memory/constitution.md`。
> - **备选用法**：直接把宪法正文保存为 `.specify/memory/constitution.md`，随后用 `/speckit.constitution`
>   做一次版本对齐与治理条款补全。
> - **来源**：由 `harness/prompts/why_this_project.md` 的 **Part A 项目章程** + **Part C 流程约束** 合并改写，
>   并套用 Speckit 官方宪法模板（`Core Principles` / 附加章节 / `Governance` / 版本行）的结构。
> - **待办**：宪法中 `TODO(...)` 标记的字段需要在批准日由 `/speckit.constitution` 填实。
> - **📌 正文同步状态（2026-11-13 订正 · 重要）**：本文件的**宪法正文已与生效副本
>   `.specify/memory/constitution.md` 的规范性正文逐字同步**（**v1.10.1** · 2026-11-13）——
>   即：**从 `## Core Principles` 起、到版本行为止**，与生效副本**逐字一致**（已用脚本 diff 校验）。
>   **本次同步顺带补齐了一处既有隐患**：本模板此前停留在 **v1.6.0**（**缺**原则 **XI / XII**
>   与「**跨 feature 承接的接线通则**」）⇒ ⇒ 再次执行 `/speckit.constitution` 本会把它们
>   **从宪法里抹掉**（条款回退）⇒ ⇒ 现已消除。
>   ⇒ **再次执行 `/speckit.constitution` MUST NOT 造成任何条款回退**；
>   若日后宪法有新修订，**本模板 MUST 同批同步**（宪法修订记录 v1.4.1 已确立此纪律：
>   「否则下一次 `/speckit.constitution` 会把旧条款重新生成回宪法」）。
>   ⇒ **同步操作**：把 `.specify/memory/constitution.md` 的 `## Core Principles` 起、
>   到版本行为止的**规范性正文**整段复制到本文件的两个标记之间（**保留**本文件的版本行格式
>   与「修订记录**缺席**状态」——**修订记录已归档**，见下）。
> - **🗄 版本变更历史已归档（2026-11-13）**：修订记录的**全部版本条目**已移至
>   **`.specify/memory/constitution-changelog.md`** ⇒ ⇒ 该归档**非规范**、**不进入**上下文窗口
>   ⇒ ⇒ **本模板同样 MUST NOT 收录它**（本文件向来的「修订记录缺席状态」由此**正式化**）。
> - **调研回填状态**：Q1–Q8 调研已于 **2026-11-01** 完成并落盘于 `harness/reports/`（9 份报告）。
>   本文件原标 `[待调研]` 的条款**已按调研结论全部回填**（对应关系见文末附表）；
>   条款中引用的具体清单、表格与数字**均以对应报告为唯一权威来源**，本文件只做引用不做复制。
>   结论固化条款一律遵循「**只能细化验收契约，不能削弱**」（原则 III）。

---

<!-- CONSTITUTION-BODY-START -->

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
- ⚠️ **v1.11.0 补 · 可追溯性 MUST 到「判据级」（MUST）**：tasks 的追溯 MUST **落到判据** ⇒ ⇒
  每条 **Success Criterion（SC）** MUST 至少挂**一条能判定它**的任务 ⇒ ⇒ ⇒ 「**实现**任务」**不**构成
  判定覆盖（它只产出行为、**不**产出判据）⇒ ⇒ ⇒ ⇒ SC MUST 挂**测试任务**（或等价的**可执行**判据）
  ⇒ ⇒ ⇒ 追溯表 MUST **双向**（spec → tasks 与 tasks → spec **各自**齐备）⇒ ⇒ ⇒ 「**测试级**覆盖缺口」
  MUST 在 tasks 落成**显式**任务 ⇒ ⇒ ⇒ **MUST NOT** 用「实现任务」冒充判据覆盖 ⇒ ⇒ ⇒ **MUST NOT**
  以「SC 已挂在某条实现任务上」为由认定判据可测 ⇒ ⇒ ⇒（理由：**判据不可测 ⇒ 该判据形同虚设** ⇒ ⇒
  与原则 IV「可诊断性是一等功能」同源）
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
  - **C27（本地 trace 存储与查询）的细则（v1.0.0 引入 · 2026-11-13 自历史段上提）**：
    ① **查询维度 MUST 可组合**（`thread_id` / `run_id` / 节点名 / `checkpoint_id`）·
    ② **请求与返回结构 MUST JSON 可序列化** ·
    ③ **存储与查询 MUST 遵守同一协议**且**后端可替换** ·
    ④ **数据结构与文件格式属内部实现细节**（**MUST NOT** 成为对外承诺）。
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
- **已发布的事实 MUST NOT 改写** —— 它是「**历史**」而非「现状」（v1.2.0 引入 ·
  2026-11-13 自历史段上提）⇒ ⇒ 例如**已发布的包元数据**（`Requires-Dist` / `Requires-Python`）
  属**已发生的事实**，**MUST NOT** 回头改写成「现状」⇒ ⇒ 若现状变了 ⇒ **另起一条新事实**，
  **MUST NOT** 覆盖旧记录 ⇒ ⇒ 「现状」与「历史」**MUST** 在文档中可区分。

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

### XI. 上游优先（Upstream-First）—— 上游 `langgraph` 是唯一权威

> **2026-11-12 决议 · v1.9.0 新增**（MINOR）。**背景**：本项目的产品本质是
> 「**零账号 / 零主动出站 / 零依赖**的 langgraph 替代品」⇒ 从设计到代码**照抄上游**即可；
> 但 speckit 流程曾让「智能体 + 大模型自由发挥」⇒ feature 之间越来越无法对齐 ⇒
> **需要人工决策的地方越来越多** ⇒ 本条把「决策来源」**收回**到上游。

- **判定顺序（MUST · 不得跳步）**：每个设计点 MUST 按下列顺序裁决 ——
  1. **上游有同款实现** ⇒ **照抄**（**含上游的缺陷与怪癖**；只抄**行为面**，
     不抄上游的依赖、账号与出站机制）；
  2. **上游没有** ⇒ 落「**必须自研区**」（下条 · 只有 4 类）⇒ **MUST** 登记并论证；
  3. **自研区的点** ⇒ **MUST** 在该 feature 的「上游对照」表里写明「上游无此项 +
     理由 + 判据」⇒ ⇒ **MUST NOT** 以「没查上游」充当理由。
- **上游锚点纪律（MUST）**：每条「上游行为」断言 MUST 带 **版本 + `路径:行号`**；
  **行为**断言 MUST 有**实测**支撑（**只读源码不足以支撑行为断言** —— 上游的
  集合 `pop()` 顺序、`update([])` 的清空语义等**只有实测才算数**）。
- **必须自研区（穷举 · 只有 4 类 · 不在其中的分叉一律照抄）**：
  ① **零账号 / 零主动出站 / 零依赖**的硬约束（与上游冲突时**自研优先** —— 这是本项目的
     产品承诺，不是「更好的实现」）；② **上游自身的缺陷 / 不确定**（如上游的竞态、
     上游的「静默忽略」）⇒ freegraph 保留**更确定**或**更严格**的口径，并**如实标注**
     「比上游更严」；③ **上游没有的能力**（freegraph 自创的诊断 / trace 家族等）；
  ④ **下游 langchain 兼容**所需的**适配层**。
- **行为面 vs 失败信号（MUST）**：**成功路径的可观察状态** MUST **照抄上游**；
  **失败信号** MAY 比上游**更严**（例如「未知 key ⇒ 显式失败」强于上游的「warning + 忽略」），
  但 MUST **标注「比上游更严」并写明理由** ⇒ ⇒ **MUST NOT** 用「更严」掩盖
  **行为面**的偏离。
- ⚠️ **v1.12.0 补 · 三态标注 MUST 一致（MUST）**：一个 feature 的「**上游对照**表」与「**偏离登记**表」
  对**同一处分叉**给出的**关系标注**（`SAME` / `STRICTER` / `DIFF`）MUST **逐字一致** ⇒ ⇒
  对照表标 **STRICTER** 的分叉 MUST 落在偏离登记里（并写明理由）⇒ ⇒ 偏离登记的**每一条** MUST 有
  对照表的**对应行** ⇒ ⇒ 两者 MUST NOT **各说各话** ⇒ ⇒ ⚠️ **理由**（B10F1 的实测发现）：
  两张表用**不同的分类词**（偏离登记写「DIFF（结构差异 · 非更严）」· 对照表写「STRICTER」）
  ⇒ ⇒ 读者**无从判断**该分叉到底算不算「比上游更严」⇒ ⇒ ⇒ 而原则 XI 的「失败信号 MAY 更严」
  **以标注为准** ⇒ ⇒ ⇒ 标注不一致 ⇒ ⇒ **该分叉实际未被有效标注** ⇒ ⇒ ⇒ **判据零放宽**
  （只加**一致性**要求 ⇒ ⇒ **不新增门禁编号** · **不放宽**任何既有判据）。
- **照抄的三条纪律（MUST）**：① **逐字**照抄（含上游的命名、默认值与异常类型家族）；
  ② **MUST NOT** 「顺手优化」上游的怪癖（上游的怪癖是**兼容性面**的一部分）；
  ③ 上游**版本**变化时 MUST **重新核实**全部锚点并**改写版本号** ⇒ **MUST NOT** 沿用
  旧版本的行号。
- **可验证出口（MUST · 本原则的落地方式）**：每个 feature MUST 交付**一组**
  「**上游 ↔ freegraph 同场景对跑**」的**差分场景**（`tests/differential/`）⇒
  场景判词三态：`SAME`（必须逐字一致）/ `STRICTER`（刻意更严 · 须写理由）/
  `DIFF`（已知结构差异 · 须写理由）⇒ ⇒ **任何 feature 让地基与上游分叉 ⇒ 差分用例立刻红**
  ⇒ ⇒ 这是「上游优先」**唯一**的可自动化判据（**MUST NOT** 只靠人工比对源码）。
- **与原则 VI（规格驱动开发）的关系**：本条**不改变** speckit 流程 ⇒ 它**改变**的是
  spec 的**内容来源**：spec 的每条判据 MUST 先问「上游怎么说」，**MUST NOT** 先问
  「模型觉得怎么做」⇒ ⇒ **发起者提问 MUST 收窄**到「上游没答案」的那一类。

**Rationale**：freegraph 的全部价值主张是「**无账号、无主动出站、无依赖**」的 langgraph 替代品
⇒ 它的**正确性**不来自「更好的设计」，而来自「**与上游同款**」⇒ 一旦允许自由发挥，
用户拿到的就是**另一个**框架 ⇒ 兼容性与可预测性同时失守 ⇒ 本条把**唯一的权威源**
写进宪法，使「照抄」成为**默认**、「自研」成为**须论证**的例外。

### XII. 最优设计优先（Optimal-Design-First）—— 既有设计不是理由

> **2026-11-12 决议 · v1.10.0 新增**（MINOR）。**背景**：本项目反复出现「因为旧设计**已存在**
> （甚至已冻结），于是新能力被硬塞进**次优形态**」的决策 —— 典型如：把**控制信号**
> （中断）塞进**状态投影**（`state`）⇒ 污染「state == 合并后的稀疏状态」这一语义；
> 把**上游的 dict 形态**（`__interrupt__` 是字典的一个 key）**错搬**成**dataclass 的字段**；
> 又如：明知上游把中断**抛出**、由根图层**抑制**，却让 L2 既抛又留一个**永远为空**的字段
> ⇒ ⇒ 这些都是「**在既有设计上做局部最优**」的产物，而不是**全局最优**。

- **判定顺序（MUST · 不得跳步）**：
  1. **先问「这个形态的最优解是什么」** —— 从**语义**出发（这个东西**是什么**），
     **MUST NOT** 从「现在手边有什么」出发；
  2. **再问「既有形态是否已经是最优」** —— 既有设计**不是**理由，只是**待检验的对象**
     ⇒ 若它**确已最优** ⇒ 照用（**零成本**，且 MUST 在 spec 里**写明**它为何最优）；
  3. **若既有形态确非最优** ⇒ **破而后立** ⇒ MUST 走「破冻结面的三条」（登记 + 回溯修订 +
     发起者追认）⇒ **MUST NOT** 因为「破冻结面麻烦」或「迁移成本高」而**保留次优形态**。
- **与原则 XI 的关系（MUST NOT 混用）**：
  - 原则 XI 管「**做什么**」（上游有 ⇒ 照抄）；**本条管「长什么样」**（照抄的**形态**如何取最优）；
  - ⇒ 「最优」**MUST NOT** 成为**自创上游已有能力**的理由 ⇒ 自研仍**只限**原则 XI 的 4 类
    必须自研区 ⇒ ⇒ **先照抄内容，再优化形态**；
  - ⇒ 「最优」**MUST NOT** 牺牲**可判定性** ⇒ 判据 **MUST NOT** 因形态优雅而弱化 ⇒
    改判据 MUST 是「**更新**」（新增能力所需）而非「**放宽**」。
- **「既有形态确非最优」的正当性判据（MUST 四条全满足）**：
  ① 新能力**确实**需要新载体（**MUST NOT** 能塞进既有载体而不**损害其语义**）；
  ② 迁移代价**可控且最小**（下游 feature 的改动 MUST 是**机械、最小**的）；
  ③ **MUST 先穷举既有的、同语义的载体**（**含 L1 已有的数据类与其字段**）⇒
     **MUST NOT** 在**错误的位置**上新增一个**重复**的载体（⇒ 避免「两处都有一份」）；
  ④ MUST **登记 + 回溯修订 + 发起者追认**（沿用「跨 feature 承接的接线通则」的「破冻结面」三条
     ⇒ **追认次数每 feature MUST ≤ 1 次**）。
- **层次对应优先于容器对应（MUST）**：当上游把某信息放在**某一层**的产物里时，freegraph MUST
  **在对应层**放 ⇒ ⇒ **MUST NOT** 把「上游某一层的产物」错搬到「另一层的容器」里
  （⇒ 典型反例：上游的「结果」是**状态字典** ⇒ 其 `__interrupt__` 是**字典的一个 key**
  ⇒ freegraph 的对应物是**门面返回的 dict** ⇒ **MUST NOT** 因此给**单轮结果对象**加字段）。
- **冻结面的真实含义（MUST）**：冻结面保护的是「**无谓的破坏**」⇒ **MUST NOT** 把冻结面当作
  「**保留次优设计**」的理由 ⇒ 但冻结面一旦被破，其**迁移路径 MUST 一并落成**
  （受影响 feature 逐个跟进 ⇒ 逐条最小改动）。
- **MUST NOT** 以「最优」为名**推翻**原则 XI 的「照抄」默认值 ⇒ 「最优」的**内容**仍是上游的。

**Rationale**：本项目的价值来自「**可预测**」⇒ 一个「在既有设计上打补丁」出来的 API
表面能用，但**每一条不自然的口径**都会变成用户的**心智负担**与下游的**长期债务**
⇒ ⇒ **形态的正确性是产品价值的一部分**，不是实现细节 ⇒ ⇒ 与原则 XI 合起来：
**内容照抄上游** + **形态取全局最优** + **冻结面不是保留次优的理由**。

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
| `.specify/memory/constitution.md` | 本宪法的**生效副本**（由 `/speckit.constitution` 生成）—— **唯一权威** · **只含规范性正文** |
| `.specify/memory/constitution-changelog.md` | 本宪法的**版本变更历史（归档）** —— **非规范** · **不进入**上下文窗口 · **日常开发与 `/speckit.*` 流程 MUST NOT 加载** |

### 依赖白名单 / 黑名单

每个特性**MUST** 复核依赖清单。白 / 黑名单以 `harness/reports/Q3-LangGraph的开源边界.md` §3.6
与 `harness/reports/Q7-开源边界地图与许可证合规.md` §3.1 的结论为准——
**但必装依赖一项以本宪法正文为准**（Q3 §3.6 原建议「必装 `typing-extensions`」
**已被本宪法取代**（2026-11-05 决议：剥离 `typing-extensions`，使基础安装零第三方依赖）：
必装依赖 = **无**；
该报告 §3.6 的其余部分——**黑名单、配置层、网络层**——仍然有效）：

- **包层白名单**：**必装运行时依赖 = 无**（基础安装**零第三方依赖**，`dependencies = []`）。
  > **2026-11-08 修订（v1.7.0）—— v1.0 的依赖面收敂到「零」**：
  > **v1.0 的发行元数据 MUST NOT 出现任何依赖包名** ⇒
  > ① **必装运行时依赖 = 无**（2026-11-05 决议：剥离 `typing-extensions`）；
  > ② **可选 extra 在 v1.0 亦不存在** —— 原列的 `pydantic`（`[pydantic]`）·
  > `ormsgpack`（`[checkpoint]`）· `opentelemetry-api` / `opentelemetry-sdk`（`[otel]`）·
  > `playwright`（`[png]`）**四个 extra 单元全部移入 v2.0 范围** ⇒
  > v1.0 的 `pyproject.toml` **MUST NOT** 含 `[project.optional-dependencies]`；
  > ③ 四个 extra **均非内核的必要条件**（实测：内核与契约层对这四个包**零引用**，
  > 契约层只用标准库）⇒ 移走它们**不阻断**任何 v1.0 内核里程碑
  > （B6F1 建图 / B7F2 compile / B7F3 invoke）；
  > ④ **v2.0 的 extras 声明落在仓库内**（**不进发行包**）：`specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml`
  > —— 门禁 **G21 / G23** 对**该清单**取证 ⇒ v1.0 就完成**预验证**（许可证 / 黑名单），
  > v2.0 落地时只需把清单搬进 `pyproject.toml`，**门禁实现零改动**；
  > ⑤ 基础安装的依赖闭包 **MUST 为空集**（由 G3 门禁断言）——**v1.0 更强**：
  > 不只是「基础安装为空」，而是**整个发行元数据无依赖包名**；
  > ⑥ **原 v1.5.0 的 `[png]` 条目**（确切包名 `playwright` + 三条硬约束）**保留其效力**，
  > 但**适用版本改为 v2.0**，且 `[png]` 的**渲染后端留待 v2.0 专项调研后决策**
  > （候选：`playwright`（白名单下唯一实测可行 · 需另装浏览器二进制）·
  > 自研最小 SVG→PNG 渲染器（纯标准库 · 永久零依赖）· 继续只出占位 PNG）。
  >
  > **2026-11-05 修订**：原为「`typing-extensions`（唯一建议的**必装**运行时依赖）」，
  > 现改为**必装依赖为空**——`typing-extensions` 已从基础安装剥离（2026-11-05 决议）。
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
  理由（依据：2026-11-05 决议 · `research.md` D-21）：3.11 一次性补齐 **7 项**
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
  - ⚠️ **v1.9.0 补 · 与原则 XI 的关系（MUST NOT 混用）**：本条**只**处置「**门禁项在本 feature
    物理不可达成**」的情形 ⇒ ⇒ **MUST NOT** 用本条为「**与上游 langgraph 行为不同**」开门：
    行为面的偏离**只**能落在原则 XI 的**必须自研区**（4 类）之内 ⇒ ⇒ **不属本条** ⇒ ⇒
    既**不需**偏离登记、**也不需**追认（**照抄即可**）；而**破已冻结的契约面**属
    「跨 feature 承接」与**发起者追认**的**另两条**通则（见下），**同样不属本条**。
  - **被延后的 MUST 是「门禁项中的某一部分」，MUST NOT 是「整条门禁」**——
    例：门禁 **5** 的「人工验证记录存在且五段式齐全」**MUST** 照常落地，
    被延后的只是其中的「**真实模型一轮**」（无图可跑）。
    ⚠️ **v1.10.2 补 · 「依赖内核运行时」是示例而非穷举**：**适用范围的判定以本条开头的
    两要件为准**（「某一部分在当前 feature **物理不可达成**」+「根因是该 feature
    **按里程碑不交付其前置能力**」）⇒ ⇒ 「**依赖内核运行时**」只是**最常见**的一类根因，
    **MUST NOT** 据此排除**同类**的其他根因（例：**门禁 7** 的「**API 兼容矩阵已更新**」——
    兼容矩阵按 **B24F1 / M4** 才首次落库 ⇒ 当前 feature **按里程碑不交付其前置能力**
    ⇒ ⇒ **属本条** ⇒ ⇒ **MUST NOT** 以「该部分不依赖内核运行时」为由**拒绝登记**）。
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
     （**不源于门禁偏离**的跨 feature 承接，见「跨 feature 承接的接线通则」。）
  2. **发起者追认**（MUST 由**发起者**本人作出）：**追认文字 + 发起者确认 + 日期**
     MUST 落在 `harness/verification/<feature>/manual-verification.md`；
     **未追认前 MUST NOT 合入**；**MUST NOT** 由实现者代签。
- **红线（本条 MUST NOT 做什么）**：
  - MUST NOT 以本条**放宽或稀释任何门禁判据** —— **原则 I / II / IX 的红线不适用本条**：
    依赖红线（`langsmith` / `langchain*` / `langgraph*`）· 许可证红线 · 商标红线 · 零出站红线
    **MUST** 在**每个** feature 落地（可延后的只有**能力型**门禁项中**物理不可达成**的那一部分
    ⇒ ⇒ **判据以本条「适用范围」的两要件为准**）。
  - MUST NOT 写**永久红**的 CI；被偏离的门禁 MUST 落**挂载点**并**明确标记「未落地」**
    （MUST NOT 伪装成「已通过」）。
  - MUST NOT 把本条当作**长期豁免**：承接项 MUST 有**具名的承接方与里程碑**，
    MUST NOT 无期限悬空；**MUST NOT** 以本条为由删改宪法正文。
  - MUST NOT 用本条**规避**「本 feature 必须能独立通过其可适用门禁」的要求。
- **登记与复核**：每一条被偏离的门禁 MUST 在**人工验证记录**中登记（可审计）；
  本条的使用情况 MUST 在**下一次宪法修订**时复核 —— 若同类偏离**反复出现** ⇒
  MUST 重新评估**该门禁项的判据本身**（或调整里程碑切分），**MUST NOT** 继续依赖本条兜底。

### 跨 feature 承接的接线通则（2026-11-09 决议 · v1.8.0）

> **背景**：本项目的里程碑切分（立项书 §6）按 feature 进行 ⇒ 任一 feature 都可能对**后续** feature
> 留下**跨 feature 义务**（接口冻结 / 断言推进 / 口径交接 / 证据复用 / 契约载体移交）。
> 此前「承接条款 MUST 写入目标 feature 的提示词初稿」只写在「质量门禁的分阶段落地与发起者追认」里
> ⇒ 其作用域**仅限**「某条质量门禁在当前 feature 物理不可达成」的偏离情形；而**不源于门禁偏离**的
> 跨 feature 义务**无明文** ⇒ 依赖执行者自觉 ⇒ 易失联。
> 本条把该机制**上提为一般通则**（**只扩大覆盖面，不放宽任何判据**）。

- **触发条件（窄口径 · MUST）**：某个 feature 的规格中出现了**指名下一棒 feature（ID + 里程碑）**的
  **跨 feature 义务** —— 即「本 feature 冻结的接口 / 建立的断言 / 交接的口径 / 产出的证据载体，
  后续 feature MUST 按某方式承接」。
  - **属本条**：接口冻结（下一棒 MUST 复用而非重造）· 断言推进（下一棒 MUST 把断言推到更强的
    边界）· 口径交接（下一棒 MUST 按已冻结的口径实现）· 证据复用（下一棒 MUST 复用本 feature
    建立的夹具 / 载体）。
  - **不属本条**：单纯的前置依赖关系（下一个 feature 依赖本 feature 的**产物**，但**没有任何**
    「MUST 如何承接」的约定）· 已在本 feature 内完成、无需下一棒动作的事项。
- **接线动作（MUST）**：该承接条款 MUST 写入**目标 feature 的提示词初稿**
  （`harness/features/<目标 feature>.md`）⇒ 由目标 feature 的 spec 落成 **FR + 裁定** ⇒
  其 tasks 与契约同步接线；本 feature 的 `plan.md` + `tasks.md` MUST 留**可勾选**条目。
- **红线（本条 MUST NOT 做什么）**：
  - MUST **NOT** 越界实现下一棒的动作（该动作属目标 feature 的范围）；
  - MUST **NOT** 新增门禁编号（既有 **G1–G30** 的编号连续性是不变量）；
  - MUST **NOT** 放宽或稀释任何门禁判据（**原则 I / II / IX** 的红线一律照常执行）；
  - MUST **NOT** 因此条改动目标 feature 提示词初稿的**其余**内容（只接线 · 逐条最小改动）。
- ⚠️ **v1.9.0 补 · 「破冻结面」的登记与追认（MUST）**：当某 feature **必须**改动**已冻结**的
  契约面 / 符号面 / 冻结断言时 ⇒ ⇒ **MUST** 同时满足三条：
  ① **回溯修订**该冻结面的**契约 + spec + 冻结断言**（**既有断言拆分而不删**）
     ⇒ ⇒ ⚠️ **v1.11.0 补 · 冻结断言清单 MUST「实测化」（MUST）**：清单 MUST 由**实测**得出 ——
     **在沙箱里按本 feature 的落地形态改动源码 ⇒ 跑既有测试套件 ⇒ 变红的断言即入清单**
     ⇒ ⇒ **MUST NOT** 只凭推理登记 ⇒ ⇒ ⇒ 清单 MUST **逐条**带 **`文件:行号`** + **变红原因**
     ⇒ ⇒ ⇒ **基线义务（MUST）**：实施**开始前** MUST 先跑一遍既有测试套件并**记录绿基线**
     （计数）⇒ ⇒ ⇒ 变红才可**归因**到本 feature ⇒ ⇒ ⇒ 既有测试**变红** ⇒ ⇒ **MUST** 先判
     「是否由本 feature 的落地形态导致」⇒ ⇒ ⇒ 再判「是否属冻结断言」⇒ ⇒ ⇒ **MUST NOT** 以
     「实现期再说」放过 ⇒ ⇒ ⇒（理由：**变红 ⇒ 永久红的 CI** ⇒ 违反 v1.6.0 的红线；
     而**推理**只能覆盖「已知」的断言 ⇒ ⇒ **实测**才能覆盖「漏登记」的断言）;
  ② **该 feature 的「上游对照」表** MUST 写明「**上游有此项 ⇒ freegraph 原先缺**」或
     「**上游无此项 ⇒ 属自研区**」⇒ ⇒ **MUST NOT** 以「更方便」为理由破冻结面；
  ③ **发起者追认**（追认文字 MUST 落在 `harness/verification/<feature>/manual-verification.md`
     ⇒ **未追认前 MUST NOT 合入**）⇒ ⇒ **追认次数每 feature MUST ≤ 1 次**。
- **首次适用**：**B5F2**（M1）—— C4 独立回归测试**推进到真实节点入参**（归 **B7F1**）·
  差分夹具的图规格**预留条件边字段**（供 **B8F1** 填值复用）。
  落地物：`specs/b5f2-sparse-state-read/spec.md` 裁定 15 / 18 / FR-031 ·
  `harness/features/B7F1_任务准备与super-step循环.md` §2 · §9 · §10 ·
  `harness/features/B8F1_条件边路由与fresh读.md` §2 · §7 · `harness/features/README.md`。

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
- **合规复核**：每次修订**MUST** 复核原则 **I–XI** 的可验证性
  （**2026-11-12 补**：原则 XI 的可验证出口 = 「**差分场景组**」· 见原则 XI 末条）；
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
- **修订记录（归档）**：每次修订的「**变更了什么 / 为什么 / 受影响的原则与特性 / 迁移方案**」
  **MUST** 追加到 **`.specify/memory/constitution-changelog.md`**（**归档文件**）
  ⇒ ⇒ 该归档是**审计与追溯**用 ⇒ **MUST NOT** 被当作规范来源 ⇒ ⇒ **规范性判断 MUST 以本文件为准**
  ⇒ ⇒ **日常开发与 `/speckit.*` 流程 MUST NOT 加载该归档文件**（它**不进入**上下文窗口 ——
  这正是它被拆出来的目的：原宪法中本段占 **47%** 的篇幅却对「当前该怎么做」零增益）；
  ⇒ ⇒ 本文件（生效副本）**只保留规范性正文 + 版本行**，**不含**历史条目。

**Version**: 1.12.0 | **Ratified**: 2026-11-05（发起者批准；首次批准即定版为 1.0.0） | **Last Amended**: 2026-11-13

<!-- CONSTITUTION-BODY-END -->

---

## 附：与调研产物的对应关系

> 调研完成日期：**2026-11-01**｜报告位置：`harness/reports/`（9 份，含 `00-调研总览与MVP范围建议.md` 汇总）

| 宪法条款 | 依赖的调研结论 | 回填状态 |
|---|---|---|
| I. 零 LangSmith 依赖 | `Q3` §3.3（付费墙触发点 T1–T9 / 三层剥离定义）、§3.6（黑白名单）、`Q2` §3.4 | ✅ 已回填（补 `mermaid.ink`、`beacon.langchain.com`、`langchain-core` ⟺ `langsmith` 等价性） |
| II. 内核纯净 | `Q8` §3.2.4、§3.3.1（135 处引用的接缝分析）、§3.4（C1–C8） | ✅ 已回填（修正工具契约表述；补 C4 / C8 回归测试要求） |
| III. 验收契约优先 | `Q3` §3.4（18 项逐项裁定）、§3.5（PNG 离线路径） | ✅ 已回填（固化 7 项同名清单 + PNG 阻断约束） |
| IV. 可诊断性 | `Q6` §3.1（21 项能力清单）、§2.1（自托管部署成本对比）、§3.3（路线 A/B 工作量）、§4.2（对比表） | ✅ 已回填（选定路线 B + 三件套范围 + 后端对接政策） |
| V. 人工验收 | 无（流程性条款）；方法补自 `Q3` 实跑 E3 / E4 | ✅ 已回填（补 socket guard 零出站证据要求） |
| VI. 规格驱动 | 无（流程性条款） | ✅ 已定 |
| VII. 职责边界 | `Q8` §3.4（C1–C27 · 2026-11-05 由 C1–C26 扩为 C1–C27）、`Q7` §3.1、`Q1` §3.3 / `Q2` §3.4（三类「不做」理由） | ✅ 已回填（冻结契约清单 + 固化不做清单） |
| VIII. 证据与术语 | `Q4` §3.4（权威术语表）、`Q1` §2.3（DOM 级解析方法） | ✅ 已回填（补 DOM 级解析纪律） |
| IX. 依赖许可证与商标红线 | `Q7` §3.1（许可证矩阵）、§3.2（ELv2 托管禁令）、§3.3.3（官方品牌指南） | ✅ **本版新增原则**（NON-NEGOTIABLE） |
| X. 文档合规义务 | `Q7` §3.3.1（MIT 保留声明义务）、§5.7（兼容矩阵） | ✅ **本版新增原则**（门禁项，可补正） |
| 依赖白 / 黑名单 | `Q3` §3.6（包层/配置层/网络层三层）、`Q7` §3.1（许可证矩阵） | ✅ 已回填（三层清单 + Elastic-2.0 附加黑名单） |
| 目标第 2 条精确化 | `Q6` §3.4（达成度裁定）、`Q1` §3.3（付费墙形状） | ✅ 已回填（垂直维度限定 + 不构成削弱的说明） |
| 术语约定章节 | `Q4` §3.1（官方 Runtime/Framework/Harness）、§3.3（六大概念在 v1 已断裂）、`Q5` §3.1 | ✅ 已回填（替代自造术语 + freechain 四元组建议） |

### 本版相对初稿的变更摘要

| 类型 | 变更 | 依据 |
|---|---|---|
| **新增** | 原则 IX（许可证与商标红线，NON-NEGOTIABLE）+ 原则 X（文档合规义务） | `Q7` 全面结论（初稿完全未涉及许可证） |
| **精确化** | 原则 IV 技术路线（路线 B）、原则 VII 契约清单（C1–C27）与不做清单、原则 III 的 7 项同名清单 | `Q3` / `Q6` / `Q8` |
| **修正错误** | 原则 II 的工具契约（`args` / `id` 属 tool_call 字典，非工具对象属性） | `Q8` §3.2.4 实测 |
| **补强** | 原则 I 网络黑名单（`mermaid.ink`）、原则 IV 后端对接政策（不得内嵌 Elastic-2.0 后端）、原则 V 零出站证据要求、原则 VIII DOM 级解析纪律 | `Q3` 实跑 / `Q6` / `Q7` |
| **回填** | 全部 `[待调研]` 标记（6 处 = 正文 3 处 + 附表 3 处） | 本文件 Governance 条款强制要求 |
