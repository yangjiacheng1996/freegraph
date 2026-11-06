# freegraph 提示词

> 本文件自包含，不依赖仓库内其他提示词或调研文件。
>
> 结构说明：
> - **Part A 项目章程**：长期上下文，可沉淀进 `.specify/memory/constitution.md`（Speckit 宪法）或保留在仓库根文档。
> - **Part B 调研任务书**：**本次要执行的完整提示词**，自包含，只产出报告，不写代码。
> - **Part C 流程约束**：项目级开发流程，建议移入 `.specify/memory/constitution.md`，避免每次调研都加载无关上下文。
>
> 若只想跑调研，直接使用 Part B。

---

## Part A 项目章程（长期上下文）

### A1. 背景与动机

本项目由个人发起者的真实痛点驱动：LangChain 家族（LangGraph / LangChain / DeepAgents）的核心开源能力免费，但**观测、Studio 调试、托管部署**等环节通过 LangSmith 设置付费墙。付费墙的具体位置目前**尚未核实**（见 Part B 的假设表 H1-H8），本项目的第一步就是把它查清楚。

发起者的核心诉求：
1. **彻底剥离，不共存**：freegraph **不依赖 LangSmith**——不引入 `langsmith` 包、不读取 `LANGSMITH_*` 环境变量、不向 `smith.langchain.com` 发起任何请求。
   目标是让付费的 LangSmith **完全从技术栈中消失**，框架做到**绝对安全**（无遥测外传、无 SaaS 依赖、可审计、可离线运行）。
2. **内核纯净**：freegraph 作为图运行内核，**不 import langchain**。对外只依赖**鸭子类型**（消息对象、工具调用、模型返回值），
   任何上层（LangChain、本团队未来计划开发的 freechain）都能挂载而不被绑死。
3. **可私有化部署**：产物能在内网/私有环境运行，开源许可证清晰、商用友好。
4. **可诊断**：不牺牲调试体验。Graph 的运行轨迹（trace）、状态快照（state）、中断（interrupt）、重放（time-travel）必须可见、可查、可回溯。这一块是LangSmith的主要卖点，整个开源团队就是依赖诊断功能获取收入，本项目希望把这一块也开源，框架100%安全。

### A1.1 两项目路线图（重要）

| 项目 | 定位 | 依赖关系 |
|---|---|---|
| **freegraph**（本项目） | 图运行内核：状态模型 / 节点 / 边与路由 / 运行时 / 可观测 | 零 LangChain、零 LangSmith 依赖 |
| **freechain**（后续项目） | 替代 LangChain 的上层：模型抽象、工具、消息、agent 构造 | **基于 freegraph** 构建 |

当前 LangChain 把"图函数"与"智能体装配层"封装在一起（详见 Part B 的 Q4/Q8）。freegraph 只做**内核**，
把 LangChain 那一层留给 freechain 重建，从而把 LangSmith 与 LangChain 一起替换掉。

> 因此本项目的验收标准里，**"能否与 LangChain 共存"不是目标**；目标是"**能否不依赖 LangChain 与 LangSmith 而独立跑通**"。

### A2. 项目目标（定位）

在**复刻 LangGraph 三大基础能力**（状态模型 / 节点 / 边与路由）的前提下，提供**彻底剥离 LangSmith、且内核不依赖 LangChain** 的图运行与可观测能力。

参考验收目标（属愿望而非既定事实，需 Part B 核实其可行性）：
- 在 LangGraph Quickstart 示例中，仅把 `langgraph` 字样替换为 `freegraph`，即可运行起一个功能一致的 tool-calling 循环智能体。→ 已具体化为 A5 的验收基线。
- freegraph 提供不亚于 LangSmith 的可视化与可诊断性。

> 注意：这两条验收目标均涉及**耦合面**与**工作量**，Part B 的 Q3/Q6/Q7/Q8 就是为它们做可行性评估。评估结论可能显著改变项目范围（见 Part B 第 10 节）。

### A3. 术语约定（重要）

发起者使用的"三大基础功能""六大概念"为**自造表述**，非官方术语。报告中必须先给出官方术语对照表，再做映射，避免自造词污染结论。已知官方对应关系待核实：

| 自造表述 | 待核实的官方对应 |
|---|---|
| 三大基础功能 | Graph API 的 state schema / node / edge（+ 官方的 Command、interrupt 等） |
| 六大概念 | LangChain 早期抽象（model / message / prompt / retriever / chain / output parser 等） |
| tool 循环智能体 | 官方的 tool-calling loop / agent（LangChain v1 `create_agent`） |

### A4. 非目标（本阶段）

- **不在 freegraph 内重建 LangChain 层**：模型抽象（`init_chat_model`）、`@tool` 装饰器、消息体系、agent 装配（`create_agent`）
  属于 **freechain** 的职责。freegraph 只需**能承载**这些对象（鸭子类型），不实现它们。
- 不追求覆盖 LangSmith 全部企业功能（Fleet、Marketplace、Agent Registry、Context Hub 等），仅在 Part B 中做边界识别。
- 不做多语言/多模型的完整 provider 矩阵。
- 不追求与 LangChain **共存**：共存不作为验收项（见 A1 诉求 1 与 A1.1）。
- **async 全套（`ainvoke`/`astream`）不在 v1 范围**：归 **v2 范围内（未排 feature）**。初判「v1 不做」已于 2026-11-03 修订——LangGraph 已实现 async，**能力对等是跟进要求**；v1 不排期的理由是需同步/异步两套调度与测试，且 v1 无 async 依赖方。目标脚本不需要 async。详见立项书 §4.6 与 §12-D4。

### A5 MVP 验收基线：`harness/demo/target.py` 必须可运行

**验收脚本**：`harness/demo/target.py`（仓库内文件，**只读基准，不得修改**）。

**来源**：LangGraph Quickstart 的 "Full code example"
（<https://docs.langchain.com/oss/python/langgraph/quickstart#full-code-example>），
仅把其中的 `langgraph` 字样**机械替换**为 `freegraph`（即 `from freegraph.graph import StateGraph, START, END`），
其余一字未改。

> 说明：脚本中 `from langchain.tools import tool` / `langchain.chat_models` / `langchain.messages` 等导入是**脚本自身**携带的，
> 不构成 freegraph 的依赖要求。freegraph 只需**能处理**这些对象（鸭子类型），不要求安装它们。
> 待 freechain 完成后，该脚本的 langchain 导入会被替换为 freechain 导入——本项目不负责那一步。

硬性约束：

1. **只换包名，不改脚本**。freegraph 必须提供与 LangGraph Graph API **同名同签名**的接口，使该脚本**原样**可运行。
2. **彻底剥离 LangSmith**（本项目的核心安全属性，必须可验证）：
   - freegraph 的**依赖树中不得出现 `langsmith` 包**（`pip show` / `pipdeptree` 可证）；
   - 代码中**不得读取** `LANGSMITH_API_KEY` / `LANGSMITH_TRACING` / `LANGSMITH_ENDPOINT` 等环境变量；
   - **不得**向 `smith.langchain.com` / `*.langchain.com` 发起任何网络请求（无遥测、无外呼）；
   - 无 LangSmith 账号、无 API Key、断网环境下，freegraph 自身功能必须完整可用。
   > 调研时需注意区分：LangSmith 的 **PyPI SDK 包 `langsmith` 是开源的**，真正付费的是 **LangSmith SaaS / 平台**。
   > "剥离"的准确定义见 Part B 的 Q3c 与 H7（依赖树事实）。
3. **内核不依赖 LangChain**：freegraph 核心代码**不得 import langchain**。对外只接受**鸭子类型**：
   任何具备 `.tool_calls` 属性的消息对象、任何可 `invoke` 的模型、任何 `@tool` 风格的可调用对象都能被图运行时处理。
   目的是让 **freechain** 能在其上重建 LangChain 能力而不被绑死（见 A1.1）。
4. **兼容 LangChain v1 消息对象（仅兼容，不依赖）**：脚本的状态 schema 使用 `langchain.messages.AnyMessage` / `ToolMessage` / `HumanMessage`，
   归约器用 `operator.add`。freegraph 必须**原样接收并流转**这些对象，不得自带一套 message 类型并强制转换。
5. **返回语义**：`agent.invoke({"messages": [...]})` 必须返回带 `messages` 键的**完整状态**（不是仅新增消息）；
   `state["messages"][-1].tool_calls` 的条件路由行为必须与 LangGraph 一致。
6. **可视化不阻断执行**：脚本末尾 `agent.get_graph(xray=True).draw_mermaid_png()` 需要出图。
   freegraph 必须提供等价的图结构导出（`get_graph` / mermaid 文本 / PNG 渲染），
   或给出明确的替代调用方式与迁移说明（该项是否必须由 freegraph 自行渲染 PNG，待 Part B 结论确定）。
7. **可测试性**：CI 用 fake / 伪模型替代 `claude-sonnet-4-6`（避免真实调用与费用），人工验收再跑真实模型，**两条都要过**。

> 说明：该脚本依赖的 API 元素清单、以及其中哪些由 LangGraph OSS 提供、哪些触及 LangSmith，
> 正是 Part B 的 Q3d 要回答的内容；本节是**验收契约**，Part B 的调研结论不得削弱它，只能细化它。

---

## Part B 调研任务书（本次执行）

### B1. 你的角色与任务

你是 freegraph 项目的技术调研员。任务：**回答下述调研问题，产出一份可直接支撑 freegraph 立项与 MVP 范围决策的报告**。

- 读者：发起者本人 + 后续要写代码的 AI 代理。因此报告要**结论先行、可执行**，不是资料摘抄。
- 语言：中文（保留官方英文术语原文，必要时附中文）。
- 产出物：`harness/reports/` 下的**按题分文件**报告集 + 一份跨题汇总
  （实际落盘：`Q1-…md` … `Q9-…md` 共 9 份 + `00-调研总览与MVP范围建议.md`；
   **Q9 为 2026-11-03 的补充调研**，触发自立项书的 D2/D5 决策需要）
  > 原始任务书要求单文件 `LangGraph开源程度评估.md`；执行时按「一题一文件 + 汇总」拆分，便于增量修订（Q9 即增量修订）。

### B2. 输出契约（必须严格满足）

1. **落盘路径**：单文件 `harness/reports/LangGraph开源程度评估.md`（原约定）→ **实际执行为按题分文件 + 汇总**（见 B1）。每份报告须能独立阅读、独立引用。
2. **结构**：必须包含以下章节，顺序不变；可增补小节，不得删减。

   | # | 章节 | 内容要求 |
   |---|---|---|
   | 0 | 摘要 TL;DR | ≤10 行。3 条核心结论 + 对 freegraph 的 3 条判断 |
   | 1 | 调研方法与资料来源 | 检索路径、来源清单、本地文档同步时间、未能获取的来源 |
   | 2 | 假设裁定表 | H1-H8 逐条裁定（成立/部分成立/不成立/未验证）+ 证据 |
   | 3 | LangSmith 产品全景与卖点 | Q1 |
   | 4 | LangSmith 收费与付费墙地图 | Q2，含套餐表 |
   | 5 | LangGraph 开源边界 | Q3，含包级清单表 + 运行时能力矩阵 + 付费墙触发点清单 + **target.py 依赖项逐项裁定** |
   | 6 | LangChain v1 的实际依赖情况 | Q4 + 官方术语对照表 |
   | 7 | DeepAgents 的依赖情况 | Q5 |
   | 8 | 观测与可视化层的规模评估与替代方案 | Q6 |
| 8.1 | **Studio 与本地 server 的关系、可视化代码的开源边界** | **Q9（2026-11-03 补充）**：Agent Server ≠ Studio；可视化代码归属（`langgraph` vs `langchain-core` vs `langgraph-api`）；本地 OSS UI 盘点 |
   | 9 | 内核最小契约：freegraph 与 freechain 的接口边界 | Q8，含"图运行时对外界的最小需求"清单 |
   | 10 | 对 freegraph 的直接启示 | 3-6 条**可执行**结论 + MVP 范围建议表 + **target.py 兼容性清单** + **依赖白/黑名单建议** |
   | 11 | 许可证与合规提示 | Q7 |

3. **引用规范**：
   - 每条事实性结论后附来源标记：`[来源: https://...]` 或 `[来源: harness/docs/...md:行号]`。
   - **价格、额度、套餐一律标注 as-of 日期**（格式 `截至 YYYY-MM-DD`），并附"以官方定价页为准，价格可能变动"。
   - 引用官方原文时**控制在 25 字以内**并给出处，不整段复制。
4. **不编造**：无法核实的信息一律标 `[未验证]` 并说明缺什么证据（缺哪个页面、缺哪个字段）。**禁止**用推测填充表格。
5. **篇幅**：正文 1500-3000 字 + 表格。目标是信息密度，不是完整度。
6. **报告末尾附自检清单结果**（见 B8），已满足的项标 ✅，未满足标 ⚠️ 并说明原因。

### B3. 待验证假设表（重要：这些是待核实的命题，不是前提）

下列判断在本任务书中以**待核实命题**的形式给出，不作为既定前提。请逐条核实并裁定，**不要因为它们被这样陈述就默认成立**。

| ID | 假设 | 核实线索 |
|---|---|---|
| H1 | `langgraph new --template new-langgraph-project-python` 生成的 `.env.example` 含 LangSmith 配置，且**无法移除** | 模板仓库实际文件内容；删掉后 `langgraph dev` 是否仍可运行 |
| H2 | `langgraph dev` 只是内存服务器，**生产部署必须付费** | `langgraph dev --help` 是否有 sqlite 持久化选项；`langgraph up` 自托管路径是否免费；`harness/docs/oss/python/langgraph/local-server.md` 中 **CLI banner 文案**与紧随其后的**正文文案不一致**（banner 说 "For production use, please use LangSmith Deployment"，正文说 "deploy Agent Server with access to a persistent storage backend" 并指向 platform-setup）——以哪个为准，为什么 |
| H3 | LangGraph 的状态/节点/边三大基础能力**不需要 LangSmith 账号**即可运行 | 无 `LANGSMITH_API_KEY` 时的实际行为；tracing 是否默认开启；Studio 连不上时是否优雅降级 |
| H4 | LangSmith Deployment 需 Plus 及以上、自托管 Platform 需 Enterprise | 本地已见 `harness/docs/langsmith/deployment.md:43`（Plus plan or above）与 `:47`（Enterprise plan）；需联网核实当前档位与价格 |
| H5 | LangChain v1 是"把智能体 Graph 继续封装"，相对旧版抽象发生迁移 | 用官方 migrate / v1 架构文档核实；核实"六大概念"在新版中的存续情况 |
| H6 | **只做 import 路径替换（langgraph→freegraph）即可跑通**该示例，即 LangGraph Graph API 这一层的行为在 OSS 内自洽，不依赖 LangSmith / Agent Server | 本地已装 `langgraph 1.2.11`、`langchain 1.4.1`：在**清空 `LANGSMITH_*` 环境变量**的子进程中直接运行原始 quickstart 示例，观察是否报错；检查 `langgraph` 包的依赖树是否引入 `langsmith`；确认 `get_graph().draw_mermaid_png()` 属于 `langchain-core` 能力还是 `langgraph` 能力 |
| H7 | **LangSmith 的"付费部分"与"开源部分"可以清晰切分**，freegraph 有条件做到零 LangSmith 耦合 | 核实：`langsmith` PyPI SDK 是否开源（许可证）、哪些能力属于付费 SaaS；`langchain` / `langgraph` / `langchain-core` 的依赖树里是否硬依赖 `langsmith` 包（本地 `pip show` / `pipdeptree` 即可查）；LangChain 的 tracing 集成在**不设** `LANGSMITH_API_KEY` 时是否默认关闭（`LANGSMITH_TRACING` 默认值） |
| **H8** | **`langgraph dev` 启动的本地 server 就是 Studio；Studio 的可视化代码在 `langgraph` 包内（或其某个子包内）** | 核实：`langgraph dev` 实际启动什么（Agent Server vs Studio）；`langgraph` / `langchain-core` / `langgraph-api` 三者各自承载什么；本地是否存在可替代 Studio 的开源 UI。**详见 Q9** |

### B4. 本地文档优先阅读清单（只读，勿全量通读）

`harness/docs` 共 318 篇，多数是 provider/集成类，与本次调研无关。**优先读以下路径**：

- **LangGraph 核心**：`harness/docs/oss/python/langgraph/` 下的
  `overview.md`、`graph-api.md`、`functional-api.md`、`pregel.md`、`quickstart.md`、`local-server.md`、`persistence.md`、`checkpointers.md`、`stores.md`、`application-structure.md`、`deploy.md`、`observability.md`、`studio.md`、`ui.md`、`event-streaming.md`、`interrupts.md`、`use-time-travel.md`、`workflows-agents.md`
- **LangSmith**：`harness/docs/langsmith/` 下的
  `observability.md`、`observability-concepts.md`、`observability-studio.md`、`observability-stack.md`、`studio.md`、`deployment.md`、`deployment-quickstart.md`、`deployment-revisions.md`、`evaluation.md`、`evaluation-concepts.md`、`evaluation-types.md`、`evaluation-approaches.md`、`observability-quickstart.md`
- **LangChain v1**：`harness/docs/oss/python/langchain/` 下的
  `overview.md`、`agents.md`、`component-architecture.md`、`middleware/`（目录）、`deploy.md`、`observability.md`
- **DeepAgents**：`harness/docs/oss/python/deepagents/` 下的
  `overview.md`、`comparison.md`、`quickstart.md`、`going-to-production.md`、`models.md`、`subagents.md`；以及 `harness/docs/oss/deepagents/code/` 下的 `overview.md`、`configuration.md`、`credentials.md`、`providers.md`、`subagents.md`
- **索引**：`harness/docs/MANIFEST.json`（含每篇的 url/path/description，用于按需定位）、`harness/docs/llms.txt`
- **验收基准**：`harness/demo/target.py`（只读）——LangGraph Quickstart "Full code example" 的机械替换版，是 freegraph 的 MVP 验收契约（见 A5）。
- **本地可实测**：`langgraph 1.2.11` / `langchain 1.4.1` / `langchain-core 1.6.3` 已安装。
  凡"OSS 是否已覆盖"能靠实跑得出答案的，**优先实跑取证**，比读文档更硬。
  注意：`langgraph dev` / `langgraph up` 等 CLI 来自 `langgraph-cli`，本地未安装，相关核实走文档与源码。
- **注意**：本地**没有**定价/计费专页；`harness/docs/langsmith/observability.md:61` 指向的 `langsmith/usage-and-billing` 页**本地缺失**，需联网抓取。

### B5. 联网调研规则

- **一手源优先**：`docs.langchain.com` / `docs.langchain.com/llms.txt`、`www.langchain.com/pricing`、官方定价页、`github.com/langchain-ai/*`（`LICENSE`、`PRICING.md`、templates 仓库、issue/PR 讨论）、PyPI 元数据（license classifier、`requires_dist` 是否依赖 langsmith 包）。
- **定价页是动态渲染抓不到时**：改用官方公告/文档中的套餐描述/官方 GitHub 仓库中的价格文件，并在报告中标注"定价页未直接抓到，仅二手确认"。
- **时效冲突**：本地文档 `synced_at = 2026-10-31`。与联网内容冲突时**以联网为准**，并在报告中列出差异。
- **二手来源**（博客、论坛、对比文章）只能用于交叉验证，不得作为唯一数字来源。
- **抓取失败**：标 `[未验证]`，写明尝试过哪些 URL。禁止猜测。

### B6. 调研问题清单

**Q1 LangSmith 的功能全景与卖点**
LangSmith 到底有哪些功能块（如 Observability/Tracing、Studio、Datasets & Evaluations、Annotation Queues、Prompt Hub/Playground、Deployment/Platform、LLM Gateway、Engine、Context Hub、Agent Registry、Fleet 等）？各自解决什么痛点？**付费用户真正买的是什么**（请用官方定价页的档位差异反向印证哪些功能是付费卖点）。

**Q2 收费结构与付费墙地图**
套餐档位（开发者/Plus/Enterprise 或实际档位名）、计量单位（trace 数、seat、扩展量、retention）、免费额度与上限、各功能分别属于哪一档。**明确列出：哪些必须付费、哪些免费、哪些是"免费但需账号"**（账号 ≠ 付费，这两者的区别对本项目至关重要）。

**Q3 LangGraph 的开源边界（本报告的核心问题）**
- **a) 包级清单**：`langgraph`、`langgraph-prebuilt`、`langgraph-checkpoint`、`langgraph-checkpoint-sqlite`、`langgraph-checkpoint-postgres`、`langgraph-store`、`langgraph-store-sqlite`、`langgraph-store-postgres`、`langgraph-cli`、`langgraph-api`、`langgraph-sdk`、`langgraph-runtime-inmem` 等，各自：许可证、能否独立安装、是否硬依赖 `LANGSMITH_API_KEY` / `LANGSMITH_ENDPOINT`、属于"开源核心"还是"平台专有"。
- **b) 运行时能力矩阵**：状态模型 / 节点 / 边与路由 / Command / interrupt / checkpoint 与 time-travel / store / streaming / subgraph / durable execution —— 哪些完全在 OSS 内、哪些依赖 LangGraph Platform。
- **c) 付费墙触发点清单**：列出**用户从"纯 OSS"跨到"需要 LangSmith"的具体动作**（如 `langgraph dev`、Studio UI、托管 Deployment、tracing 默认行为、LLM Gateway、模板自带的 `.env`）。
  同时给出 **"剥离"的可验证定义**（对应 A5 约束 2），分三层：
  - **包层**：`langsmith` SDK 包是否出现在 `langchain` / `langgraph` / `langchain-core` 的依赖树中？freegraph 的依赖树应如何做到不含它？
  - **配置层**：哪些环境变量会触发外呼（`LANGSMITH_API_KEY`、`LANGSMITH_TRACING`、`LANGSMITH_ENDPOINT`、`LANGSMITH_PROJECT`…）？默认是否开启？
  - **网络层**：有哪些出站域名（`smith.langchain.com`、`api.smith.langchain.com`、遥测端点）？freegraph 应保证零出站。
- **d) 耦合面（以 `harness/demo/target.py` 为基准逐项裁定）**：为 A5 的验收契约做评估。**先读该脚本**，把它依赖的 API 元素逐个列出，至少覆盖：
  `freegraph.graph` 模块需导出的 `StateGraph` / `START` / `END`；
  `StateGraph(schema)` 构造、`add_node(name, fn)`、`add_edge(src, dst)`、
  `add_conditional_edges(src, path_fn, path_map)`（path_map 中含 `END`）、
  `compile()`、`compiled.invoke({"messages": [...]})`（返回完整状态）、
  `compiled.get_graph(xray=True).draw_mermaid_png()`。
  状态层：`Annotated[list[AnyMessage], operator.add]` 归约器语义、`state.get(key, default)`、节点返回**部分**状态字典时的合并规则、
  `messages[-1].tool_calls` 的条件路由判定。
  对每一项回答：LangGraph OSS 是否直接提供？是否触及 LangSmith / Agent Server？freegraph 必须**同名同签名**对齐，还是可以自由设计？
  结论汇总为第 10 节的"target.py 兼容性清单"。

**Q4 LangSmith 对 LangChain 的实际影响程度**
LangChain v1（`create_agent`、middleware、provider 抽象）与旧版抽象的迁移关系。分三层回答：**运行时强依赖 / 可选集成 / 仅商业引导**。并给出"官方术语 ↔ 发起者自造术语"对照表（见 A3）。

**Q5 DeepAgents 与 LangChain / LangGraph / LangSmith 的关系**
DeepAgents 处于什么抽象层（基于 LangChain agent + Graph？自带运行时？）、是否强依赖 LangSmith、其 provider/凭据配置是否引入 SaaS 耦合。

**Q6（新增）"不亚于 LangSmith 的可视化与可诊断性"的规模与可行性**
拆解 LangSmith Studio + Observability 的能力清单，逐项标注：**必须自研** vs **可用现成 OSS 满足**。评估 OpenTelemetry、Langfuse、Phoenix（arize）、OpenLIT 等方案能覆盖多少。给出两条路线的对比：
- 路线 A：自研整套 Studio/追踪后端
- 路线 B：OTel 兼容的追踪协议 + 内嵌轻量可视化 UI
分别的工作量估算与"不亚于 LangSmith"这一目标的达成度。

**Q7（新增）开源边界地图与许可证合规**
输出一张地图：LangGraph OSS 核心 / LangSmith 付费墙 / freegraph 拟覆盖区域。标注各块许可证（如 MIT/Apache-2.0 是否商用友好、有无 AGPL/SSPL 类传染性条款）、以及"复刻 API 名称/接口"在商标与版权上的注意事项。

**Q8（新增）图运行时的"最小契约"：freegraph 与 freechain 的接口边界**
这是 freegraph / freechain 两项目分工的**技术依据**，请回答：

1. **一个图运行时到底需要从外界拿什么？** 以 LangGraph 的实际实现为参照，列出图执行所需的最小外部能力，例如：
   状态 schema 的归约器机制、消息对象的最小属性集（如 `content`、`tool_calls`、`id`、`tool_call_id`）、
   模型调用契约（`invoke(input) -> AIMessage`）、工具调用契约（可调用对象 + `name` + `args` + `id`）、
   路由函数契约（返回节点名或结束标记）。
2. 这些最小契约中，**哪些是 LangChain 特有概念、哪些是通用协议**（例如 OpenAI 风格的 `tool_calls` 结构）？
   通用部分可以被 freechain 直接采用；LangChain 特有部分由 freechain 做适配层。
3. **图层是否真的需要 LangChain？** 用依赖关系证据回答：LangGraph 的 `graph` 模块对 `langchain-core` 的依赖强度
   （是否仅为类型/序列化便利），以及是否存在"不装 langchain 也能跑图"的路径。
4. 产出一份 **"内核最小契约"清单**：freegraph 对上（freechain）承诺哪些接口，对下（用户/脚本）承诺哪些语义。
   这份清单即 freechain 的设计输入（写入第 9 章）。

**Q9（补充，2026-11-03）Studio 与本地 server 的关系，及可视化代码的开源边界**

> 触发原因：立项书 §12-D2（前端栈选型）与 §12-D5（Studio UI 是否进 v1）需要事实依据，不能靠偏好拍板。

请回答：

1. **`langgraph dev` 启动的 local server 是不是 Studio？** 核实它实际提供什么（HTTP API？`/docs`？SSE？），以及 Studio UI 的 URL 指向哪里（本地路径还是云端域名）；官方文档对二者关系的表述是什么。
2. **Studio 的可视化代码在哪个包里？** 逐个核实：
   - `langgraph` 包内是否存在任何前端资产（`.js` / `.html` / `.css` / `.tsx`）？
   - 图结构数据类（`Graph` / `Node` / `Edge`）与 mermaid 渲染（`draw_mermaid` / `draw_mermaid_png`）分别归属哪个包、哪些行？
   - **交互式 Studio 前端**（图视图、状态检查器、prompt 编辑、run 控制）是否存在于任何开源包中？
   - 本地 server 提供了哪些「前端口子」（静态 UI 挂载？JS SDK？），它们属于哪个包、什么许可证？
3. **本地是否已有可替代 Studio 的开源 UI？** 盘点官方及社区的本地调试 UI（如 Agent Chat UI 一类），逐项给出：许可证、能否本地运行、**连本地 server 是否需要账号/API key**、覆盖 Studio 的哪些能力、缺哪些能力。
4. **产出一张「Studio 能力 × 代码归属 × 开源与否」对照表**，并据此**精化或推翻** Q6 的结论「没有任何现成 OSS 提供 Studio 那种图运行时 IDE」——**结论只能精化，不能削弱 Q6 的独占性判断**。
5. **对 freegraph 的直接启示**：v1 的可视化三件套是否必须引入前端技术栈？若不必，「能力层优先」的最小实现是什么？若做 v2 完整 UI，有无可借鉴的开源实现（须同时说明许可证义务）？

> **取证要求**：以**源码行号 + 包内文件实测**为主，文档为辅；闭源部分**不得推测**，只做「双证据判定」（如「开源侧零 UI 资产」+「URL 指向云」）。产出独立报告 `harness/reports/Q9-Studio与本地server及可视化代码边界.md`。

### B7. 禁止事项

- 本任务**只产出报告**：不写 freegraph 实现代码，不创建功能模块，不改任何已有源码。
- **不修改 `harness/docs/**`** 与 **`harness/demo/target.py`**（均为只读；后者是 MVP 验收契约，改它等于改验收标准）。
- 不执行 `pip install`/`npm install` 全量安装等破坏性或耗时操作；如必须实机验证 H1-H3/H6，只能在 `/tmp` 下隔离目录做最小验证，且要在报告中说明验证方式与结论。
- 不把 `harness/reports/` 下的报告集（Q1–Q9 + `00-调研总览与MVP范围建议.md`）之外的文件当作交付物；**不得修改 `harness/docs/**`、`harness/demo/target.py` 与既有报告的原始结论**（增量修订只能以「精化 / 补充」形式追加，并注明日期与依据）。

### B8. 交付前自检清单

- [ ] 每个事实性结论都带来源标记（URL 或 本地路径:行号）
- [ ] 所有价格/额度/套餐带 as-of 日期 + "以官方定价页为准"
- [ ] H1-H8 每条都有裁定与证据
- [ ] 自造术语已给出官方对照表，未混用为官方术语
- [ ] 第 10 节结论是**可执行动作**（如"freegraph 的 tracing 层应采用 OTel semantic conventions 的 X/Y/Z 属性以兼容现有面板"），不是口号
- [ ] MVP 范围建议表含：模块 / 是否 v1 必做 / 依赖 / 风险 / 粗略工作量档位（人日量级）
- [ ] **target.py 兼容性清单已逐项裁定**：`harness/demo/target.py` 用到的每个 API 元素都在表内，标注 OSS 是否提供 / 是否触及 LangSmith / freegraph 是否必须同名对齐
- [ ] 已给出 freegraph 的**依赖白名单 / 黑名单建议**（包层 / 配置层 / 网络层三层，对应 A5 约束 2 与 H7）
- [ ] 已给出 **"内核最小契约"清单**（第 9 章），可作为 freechain 的设计输入
- [ ] 所有无法核实项已标 `[未验证]`，无编造数字
- [ ] 未修改 `harness/docs`、`harness/demo/target.py` 与任何源码

---

## Part C 流程约束（建议移入 `.specify/memory/constitution.md`）

- 本项目全程采用 OpenCode + Speckit 编写代码。
- 每个特性走标准流程：proposal → spec → tasks → 实现。
- **充分的人工测试是最终验收标准**：自动测试通过不等于验收通过，必须有人工验证记录（记录文件落在 `harness/verification/<feature>/manual-verification.md`）。
- **MVP 验收基线**：`harness/demo/target.py` 必须**原样**跑通——
  fake/伪模型跑一遍（CI 可自动化），真实模型再跑一遍（人工验收），两次都要过；
  且必须在**不设任何 `LANGSMITH_*` 环境变量**的干净环境下验证（对应 A5 约束 2：彻底剥离 LangSmith，不以共存为目标）。
- **零依赖红线**（写在宪法里，后续每个特性都要复核）：freegraph 不得引入 `langsmith` 包、不得读取 `LANGSMITH_*`、不得有指向 `*.langchain.com` 的出站请求、核心层不得 import `langchain`。
- **两项目边界**：本仓库只做 freegraph（内核）；freechain（LangChain 替代层）在后续项目中基于 freegraph 构建，不在当前范围内实现，但接口契约必须对齐 Q8 的"内核最小契约"。
- 调研产物先落 `harness/reports/`，结论再转入 `harness/proposals/` 变成设计提案。
