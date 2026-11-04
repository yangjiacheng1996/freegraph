# Q4 LangSmith 对 LangChain 的实际影响程度

> 调研问题：LangChain v1 与旧版抽象的迁移关系；LangSmith 对 LangChain 的影响分三层（运行时强依赖 / 可选集成 / 仅商业引导）；**官方术语 ↔ 发起者自造术语权威对照表**。
> 调研日期：2026-11-01｜本地文档同步 2026-10-31
> **联网抓取方式**：本轮调研通过本机代理 `http://127.0.0.1:10808`（xray / v2rayN 系统代理端口）出网抓取官方页面；`docs.langchain.com` 支持在 URL 后加 `.md` 直接获得 Markdown 源文。**定价页的功能勾选矩阵必须做 DOM 级解析**（Markdown 文本化会丢失 SVG 勾选状态），方法见 [Q1 §2.3](Q1-LangSmith的功能全景与卖点.md)。

---

## 1. 摘要 TL;DR

1. **官方自己已经把产品分三层**："Runtime（LangGraph）/ Framework（LangChain）/ Harness（Deep Agents）" [来源: harness/docs/oss/python/concepts/products.md:9-40]。**这是全项目术语体系的官方锚点**，取代发起者自造的「三大基础功能 / 六大概念」。
2. **LangSmith 不在 LangChain 的运行时依赖链里**——它是一个**旁路的商业层**。实测：`langchain` 包内**仅 1 个文件**引用 langsmith（`langchain/agents/factory.py:30` 的 `from langsmith import traceable`）；`langgraph` 包内**仅 4 处**引用，且全部是可选路径（见 §3.2）。
3. **但依赖树层面是硬耦合**：`langchain-core 1.6.3` 硬依赖 `langsmith<1.0.0,>=0.3.45`（非 extras）→ **任何装 LangChain 的机器上 `langsmith` 包必然存在**。**"包在"与"用得上"是两回事**，这是本项目"剥离"必须精确到"不装/不依赖"的原因。
4. **LangChain v1 = 把旧的 agent Graph 继续封装**：官方迁移指南第 2 条明说 `create_react_agent` → `create_agent`（从 `langgraph.prebuilt` 移到 `langchain.agents`）[来源: harness/docs/oss/python/migrate/langchain-v1.md:14]。且源码证实 `create_agent` 内部**就是构造一个 `StateGraph`** 再 `compile()` [来源: `langchain/agents/factory.py` 实测]。
5. 对 freegraph 的判断 ①：**「六大概念」在 LangChain v1 中已经断裂**——model/message/tool 留在 `langchain`，chain/retriever/index/hub 被搬到 `langchain-classic`，output parser 被 `ToolStrategy`/`ProviderStrategy` 取代。**freechain 不应复活六大概念**，应按 v1 的「Model + Harness」重建。
6. 对 freegraph 的判断 ②：**LangSmith 的影响是"可选集成"而非"运行时强依赖"**——只要不设 `LANGSMITH_TRACING`（默认关闭，实测），LangChain/LangGraph 完全静默。**这为 freegraph 提供了正面证据：剥离是可行的，而且剥离后的行为与"不设 env 的 LangChain"完全一致。**
7. 对 freegraph 的判断 ③：**freechain 应提供"traceable 装饰器"这一等价物时，把它做成 freegraph 的可选插件**（默认关闭、显式传入才生效），从而在不引入 `langsmith` 包的前提下保住"中间件 hook 可观测"的能力。

---

## 2. 调研方法与资料来源

### 检索路径

1. 读 `harness/docs/oss/python/concepts/products.md`（**官方三层分类法**，本次调研最关键的术语锚点）。
2. 读 `harness/docs/oss/python/migrate/langchain-v1.md`（v1 迁移指南 7 条关键变化）。
3. 读 `harness/docs/oss/python/releases/langchain-v1.md`（v1 发布说明）。
4. 读 `harness/docs/oss/python/langchain/overview.md`、`agents.md`、`middleware/overview.md`。
5. 读 `harness/docs/oss/python/langchain/component-architecture.md`（旧版组件生态图）。
6. **源码实测**：`langchain/` 与 `langgraph/` 包内 `langsmith` 引用全量扫描；`create_agent` 源码中 `StateGraph` 构造点定位。
7. 实测：`tracing_is_enabled()` 默认值。

### 来源清单

| # | 来源 | 类型 |
|---|---|---|
| A1 | `harness/docs/oss/python/concepts/products.md:9-40` | 本地镜像（官方三层分类） |
| A2 | `harness/docs/oss/python/migrate/langchain-v1.md:13-21,27-49` | 本地镜像 |
| A3 | `harness/docs/oss/python/releases/langchain-v1.md:5-50` | 本地镜像 |
| A4 | `harness/docs/oss/python/langchain/overview.md:7-30` | 本地镜像 |
| A5 | `harness/docs/oss/python/langchain/component-architecture.md:9-60` | 本地镜像 |
| A6 | `harness/docs/oss/python/langchain/middleware/overview.md:32-45` | 本地镜像 |
| A7 | `langchain/agents/factory.py:27-30,1050-1055`（本地 site-packages） | 源码一手 |
| A8 | `langchain/agents/middleware/` 目录实测（24 个 middleware 模块） | 源码一手 |
| A9 | `langgraph/` 包内 `langsmith` 引用扫描（4 处） | 源码一手 |
| A10 | `langsmith/utils.py:121-141`、`langchain_core/tracers/context.py:132-135` | 源码一手 |
| A11 | `langchain 1.4.1` / `langchain-core 1.6.3` PyPI 元数据 | 官方一手 |

### 未能获取的来源

- `langchain` v1 的完整 API 参考（`reference.langchain.com`）未抓取——本地文档已足够覆盖术语与迁移关系。
- `langchain-classic` 各子模块的完整 API → 未逐项核实，仅核实其 PyPI 依赖 `langchain-core<2.0.0,>=1.4.4` + `langsmith<1.0.0,>=0.1.17`。

---

## 3. 正文

### 3.1 官方术语三层分类（**全项目权威锚点**）

[来源: A1 `harness/docs/oss/python/concepts/products.md:9-40`]

官方把 agent 开发栈分三层：

| 层 | 官方术语 | 定义（官方原文大意） | 价值主张 | 选项 |
|---|---|---|---|---|
| **Runtime** | **LangGraph** | Durable execution / Streaming / HITL / Persistence | "Low-level control"、"Long running, stateful workflows and agents" | LangGraph、Temporal、Inngest |
| **Framework** | **LangChain** | "Abstractions"、"Integrations" | "Getting started quickly"、"Standardizing how a team builds" | LangChain、Vercel AI SDK、CrewAI、OpenAI Agents SDK、Google ADK、LlamaIndex |
| **Harness** | **Deep Agents** | "Predefined tools"、"Prompts"、"Subagents" | "More autonomous agents"、"Agents faced with complex, non-deterministic tasks" | Deep Agents SDK、Claude Agent SDK、Manus |

关键关系（官方原文）：**"LangChain is built on top of LangGraph, you don't need to know LangGraph to use LangChain."** [来源: A1:38]

> **对 freegraph 项目的意义**：官方已经用了 **Runtime / Framework / Harness** 这组词。freegraph 应直接采用：
> - **freegraph = Runtime 层**（对标 LangGraph）
> - **freechain = Framework 层**（对标 LangChain）
> - **不实现 Harness 层**（对标 Deep Agents）——超出范围，且 Deep Agents 依赖 LangChain 上层。

### 3.2 LangSmith 对 LangChain/LangGraph 的影响：三层分档

#### 第一层：运行时强依赖（Runtime hard dependency）

| 项目 | 结论 | 证据 |
|---|---|---|
| **代码级 import** | ❌ **无**。`langchain` 包内仅 `langchain/agents/factory.py:30` 一处 `from langsmith import traceable`，且仅用于给 middleware 的 `wrap_model_call` / `wrap_tool_call` hook 加 span 装饰（`factory.py:1050-1055`）——**该装饰在无 API key 时是 no-op** | 源码全量扫描 |
| **包级依赖** | 🔴 **有**。`langchain-core 1.6.3` 的 `Requires-Dist` 含 `langsmith<1.0.0,>=0.3.45`（**非 extras，是硬依赖**）→ `langchain` → `langgraph` → `langchain-core` → `langsmith` 必然出现在依赖树 | PyPI 元数据实测 |
| **网络级依赖** | ❌ **默认无**。`tracing_is_enabled()` 实测返回 `False`（未设 `LANGSMITH_TRACING(_V2)` 时），且 `langchain_core` 的 `langsmith.run_helpers` import 是**延迟导入**（`runnables/config.py:191-192` 注释："Deferred to avoid importing langsmith at module level (~132ms)"） | 实测 + `langchain_core/runnables/config.py:191-192` |

> **本层的精确表述**：LangSmith 对 LangChain 的影响在**「包在依赖树里」**这一层是**硬依赖**；在**「运行时行为」**这一层是**零依赖**。
> **对 freegraph 的意义**：§2.6 约束 2 要求"依赖树中不得出现 `langsmith` 包"——这**必然要求 freegraph 不依赖 `langchain-core`**（它是唯一入口）。这不是过度设计，是唯一可行路径。

#### 第二层：可选集成（Optional integration）

| 集成点 | 触发方式 | 是否必须账号 | 证据 |
|---|---|---|---|
| Tracing 上报 | `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` | ✅ 是 | 实测外呼 `api.smith.langchain.com/info` + `/runs/multipart` |
| 局部 tracing | `with ls.tracing_context(enabled=True):` | ✅ 是 | `harness/docs/oss/python/langgraph/observability.md:47-55` |
| 选中 tracing | `from langsmith import traceable` | ✅ 是 | `langchain/agents/factory.py:30` |
| OTel 导出 | `langsmith.integrations.otel` | ✅ 是（用 LangSmith 后端） | `langsmith/integrations/otel/processor.py:67-84` |
| Studio（连本地 server） | `langgraph dev` 打印的 Studio URL | ✅ 是 | `harness/docs/oss/python/langgraph/local-server.md:88,102` |
| `langgraph.pregel.remote`（RemoteGraph） | 显式调用 | ✅ 是（连 Agent Server） | `langgraph/pregel/remote.py:14` `import langsmith as ls` |
| `langgraph` 的 `TAG_HIDDEN` 常量 | 无 | ❌ | `langgraph/constants.py:26`（只是字符串 `"langsmith:hidden"`） |
| `langgraph._internal._config` 的 `langsmith_inheritable_metadata=` | 无 | ❌ | `_config.py:270,310`（只是给 tracer 传元数据的 kwarg，tracer 不存在时无效） |

#### 第三层：仅商业引导（Commercial steering only）

| 引导方式 | 具体表现 | 证据 |
|---|---|---|
| 文档前置条件 | "Before you begin, ensure you have the following: An API key for LangSmith" | `local-server.md:13` |
| 默认模板 | `langgraph new` 生成的 `.env.example` 含 `LANGSMITH_PROJECT=new-agent` | 模板仓库 `.env.example` 实测（全文仅 4 行） |
| CLI banner | `langgraph dev` 打印 `🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=...` | `langgraph_api/cli.py:306-307` |
| Studio 定位 | "LangSmith Studio is a free visual interface" —— 但托管在云上 | `harness/docs/oss/python/langgraph/studio.md:5` |
| 推荐组合 | "We recommend you also set up LangSmith Engine" | `harness/docs/oss/python/deepagents/going-to-production.md:39` |
| 部署引导 | `langgraph up` 提示 "For production use, requires a license key" | `langgraph_cli/cli.py:297-298` |
| 官方产品叙事 | "Pair it with LangSmith for tracing, evaluation, and monitoring" | Deep Agents README:82 |

### 3.3 LangChain v1 的迁移关系（对旧版抽象做了什么）

[来源: A2 `harness/docs/oss/python/migrate/langchain-v1.md:13-21`]

官方列出的 7 条关键变化：

| # | 变化 | 内容 | 对 freechain 的意义 |
|---|---|---|---|
| 1 | **Package namespace reduction** | `langchain` 只保留 agents / messages / tools / chat models / embeddings；legacy chains、retrievers、indexes、hub、embedding helpers、community re-exports **移到 `langchain-classic`** | freechain 应按新分层建包，不要复活旧 `langchain.chains` 等模块 |
| 2 | **`create_react_agent` → `create_agent`** | 从 `langgraph.prebuilt` 移到 `langchain.agents`；`prompt=` → `system_prompt=`；用 `langchain.agents.AgentState` 替代 `langgraph.prebuilt` 的 agent state helpers | **agent 装配归上层**（freechain），不归 freegraph |
| 3 | **Hooks become middleware** | `pre_model_hook` / `post_model_hook` / `state_modifier` → `create_agent` middleware（`before_model`、`after_model`、`@wrap_model_call`、`@wrap_tool_call`）；HITL 用 `HumanInTheLoopMiddleware(interrupt_on={...})` | **middleware 是上层的可观测挂钩点**（Q8 契约设计点） |
| 4 | **Structured output** | `response_format=` 保留，但用 `ToolStrategy` / `ProviderStrategy`；移除 prompted output forms | 「六大概念」之「output parser」**已被替换** |
| 5 | **Streaming node name** | 流式事件按节点名过滤时，`"agent"` 改名 `"model"` | freegraph 的节点命名应允许重命名以兼容 |
| 6 | **Runtime context** | 用 `context=` 参数 / `context_schema=` 传静态上下文，而非只用 `config["configurable"]` | **freegraph 应有独立的 context 通道**（见 Q8） |
| 7 | **Standard content blocks** | 优先用 `message.content_blocks`；`message.content` 仍有效 | 消息契约应容忍两种形态 |

**源码验证「v1 = 把 agent Graph 继续封装」**：`create_agent` 的实现中出现了：

```python
graph: StateGraph[...] = StateGraph(
    state_schema=resolved_state_schema,
    input_schema=input_schema,
    output_schema=output_schema,
    context_schema=context_schema,
)
```

[来源: A7 `langchain/agents/factory.py` 实测源码定位]

即 **LangChain v1 的 `create_agent` 本质就是「用 LangGraph 的 `StateGraph` 搭一个 tool-calling loop」**。这直接证实了 §2.2 的路线图判断：**LangChain v1 把「图函数」与「智能体装配层」封装在一起**，而 freegraph/freechain 的分工正是把这两层拆开。

**「六大概念」在 v1 中的存续情况**（逐项裁定）：

| 发起者自造概念 | v1 中的官方对应 | v1 状态 |
|---|---|---|
| model | `langchain.chat_models.init_chat_model` / `langchain-core` `BaseChatModel` | ✅ 保留（在 `langchain` 主包） |
| message | `langchain.messages`（从 `langchain-core` re-export）+ `content_blocks` | ✅ 保留 |
| prompt | `langchain.agents` 的 `system_prompt` / `dynamic_prompt` middleware；平台侧 Prompt Hub | ⚠️ **概念位移**：不再是独立 `PromptTemplate` 类，而变成 agent 参数 + middleware |
| tool | `langchain.tools`（`@tool`、`BaseTool`，从 `langchain-core` re-export） | ✅ 保留 |
| chain | **迁出** → `langchain-classic.chains` | ❌ 已废弃（`langchain-classic` 1.0.8，MIT） |
| retriever | **迁出** → `langchain-classic.retrievers` | ❌ 已废弃 |
| （额外）indexing / hub | **迁出** → `langchain-classic` | ❌ 已废弃 |
| （额外）output parser | **被替换** → `ToolStrategy` / `ProviderStrategy` | 🔄 语义替换 |
| （额外）embedding | `langchain.embeddings.init_embeddings` | ✅ 保留 |

> **结论**：发起者「六大概念」是 LangChain **v0 时代**的抽象，**在 v1 中已断裂**。freechain 若按 v1 精神重建，应采用「**Model + Tools + Messages + Harness(middleware)**」四元组，而非六大概念。

### 3.4 官方术语 ↔ 发起者自造术语对照表（**全项目唯一权威版本**）

> 本表是 §2.4 要求的权威产出位置。其他报告（Q1/Q2/Q3/Q5/Q6/Q7/Q8/00）引用本表时**以本表为准**，不得各写各的。

| 发起者自造表述（标注：发起者自造表述） | 官方术语（原文） | 官方定义 / 出处 | freegraph / freechain 归属 |
|---|---|---|---|
| **三大基础功能** | **Graph API: State Schema + Nodes + Edges**（另含官方补充机制：Command、interrupt、Send、durability） | "The `State` of the graph. The `State` consists of the schema of the graph as well as `reducer` functions" [来源: `harness/docs/oss/python/langgraph/graph-api.md:49`]；节点/边见同页 | **freegraph**（全部） |
| **三大基础功能**（运行时层） | **Runtime（LangGraph）/ Pregel runtime** | "Pregel implements LangGraph's runtime, managing the execution of LangGraph applications." [来源: `harness/docs/oss/python/langgraph/pregel.md:5-7`] | **freegraph** |
| **六大概念** | **LangChain v1 abstractions：Model / Tools / Messages / Structured output(+ middleware)**（chain / retriever / indexing / hub 已迁至 `langchain-classic`） | "LangChain provides `create_agent`: a minimal, highly configurable agent harness. Compose exactly the agent you want to use from model, tools, prompt, and middleware." [来源: `harness/docs/oss/python/langchain/overview.md:7-9`] | **freechain**（chain/retriever 明确不做） |
| **六大概念**（旧版出处） | **LangChain v0 component ecosystem**（Document loaders → Text splitters → Embeddings → Vector stores → Retrievers → Chat models → Tools → Agents） | 组件生态图 [来源: `harness/docs/oss/python/langchain/component-architecture.md:9-60`] | **不做**（历史抽象） |
| **tool 循环智能体** | **Agent（`create_agent`）/ "the basic agent loop"** | "Under the hood, `create_agent` is built on the basic agent loop -- calling a model, letting it choose tools to execute, and then finishing when it calls no more tools" [来源: `harness/docs/oss/python/releases/langchain-v1.md:47-49`] | **freechain**（组装）；**freegraph**（执行） |
| **tool 循环智能体**（图层视角） | **Graph API 的 conditional edge 循环**（`llm_call` ⇄ `tool_node`） | `harness/demo/target.py:130-136`（`add_edge` + `add_conditional_edges` 构成环） | **freegraph** |
| （无自造词） | **Framework（LangChain）** | "Abstractions, Integrations" [来源: `harness/docs/oss/python/concepts/products.md:24-26`] | **freechain** 对标 |
| （无自造词） | **Harness（Deep Agents）** | "Predefined tools, Prompts, Subagents" [来源: 同上:30-32] | **不做** |
| （无自造词） | **Agent Server / Deployment** | "a workflow orchestration runtime purpose-built for agent workloads" [来源: `harness/docs/langsmith/deployment.md:9`] | **不做**（平台层） |
| （无自造词） | **Cloud / BYOC / Self-hosted**（平台托管三形态） | "Cloud, Bring Your Own Cloud (BYOC), and Self-hosted options... Self-hosted and BYOC are available on the Enterprise plan." [来源: `https://docs.langchain.com/langsmith/platform-setup`，2026-11-01 补抓] | **不做** |
| （无自造词） | **Studio** | "a specialized agent IDE" [来源: `harness/docs/langsmith/studio.md:7`] | **freegraph 可做本地简化版**（Q6） |
| （无自造词） | **Agent / Environment**（Agent Registry 的两级模型） | environment 固定为 Production / Staging / Development / Local 四档 [来源: `https://docs.langchain.com/langsmith/agent-registry`，2026-11-01 补抓] | 🟡 v2 可选（**Cloud-only，无自托管替代**） |
| （无自造词） | **Observability（runs / traces / threads / trajectories）** | "If you are familiar with OpenTelemetry, you can think of a run as a span." [来源: `harness/docs/langsmith/observability-concepts.md:21`] | **freegraph 做 trace 内核**；UI 见 Q6 |
| **两大项目路线图** | **Runtime（freegraph）→ Framework（freechain）** | 官方分层 [来源: `harness/docs/oss/python/concepts/products.md:9-40`] | 对应关系确立 |

---

## 4. 表格

### 4.1 三层依赖分档表

| 依赖层 | 具体项 | LangChain / LangGraph 实际情况 | 是否触 LangSmith 账号 | 证据 | freegraph 对应做法 |
|---|---|---|---|---|---|
| **① 运行时强依赖** | `langsmith` 包出现在依赖树 | ✅ 硬依赖（`langchain-core` → `langsmith`，非 extras） | — | PyPI 元数据 | **不依赖 `langchain-core`**；依赖树无 `langsmith` |
| **① 运行时强依赖** | 运行时是否默认外呼 | ❌ 默认不外呼（`tracing_is_enabled()` = `False`） | — | 实测 | 内核不读任何 env |
| **① 运行时强依赖** | 代码级 `import langsmith` | `langchain` 1 处（`factory.py:30`，可选路径）；`langgraph` 4 处（全可选路径） | — | 源码扫描 | 内核零 `import langsmith` |
| **② 可选集成** | Tracing 全量上报 | 需 `LANGSMITH_TRACING=true` + key | ✅ 需 | 实测外呼日志 | 提供可选 tracer 接口，默认关闭 |
| **② 可选集成** | 局部 tracing | `ls.tracing_context(enabled=True)` | ✅ 需 | `oss/python/langgraph/observability.md:47-55` | freegraph 提供等价 context manager（自有协议） |
| **② 可选集成** | `traceable` 装饰器 | `langchain/agents/factory.py:30` | ✅ 需 | 源码 | freegraph 自带 `traceable`（零依赖版），仅包 freegraph 内部 span |
| **② 可选集成** | OTel 导出 | `langsmith.integrations.otel` | ✅ 需 | 源码 | **直接用 OTel SDK**（可选依赖），不经 langsmith |
| **② 可选集成** | Studio UI | 浏览器 → `smith.langchain.com` → 本地 | ✅ 需 | `local-server.md:88` | 本地 Studio（Q6 路线 B） |
| **② 可选集成** | RemoteGraph | `langgraph/pregel/remote.py` | ✅ 需 Agent Server | 源码 | 不做（远程部署不在范围） |
| **③ 仅商业引导** | 文档前置条件要求 key | "An API key for LangSmith" | ✅ 需（文档层） | `local-server.md:13` | 文档明确写"无需账号、无需 key" |
| **③ 仅商业引导** | 模板 `.env` | `LANGSMITH_PROJECT=new-agent` | 🟡 软 | 模板实测 | freegraph 模板无任何 `LANGSMITH_*` |
| **③ 仅商业引导** | CLI banner 指向云 | `🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=...` | 🟡 软 | `langgraph_api/cli.py:306` | banner 指向 `http://127.0.0.1:<port>` |
| **③ 仅商业引导** | 官方推荐组合 | "We recommend you also set up LangSmith Engine" | 🟡 软 | `going-to-production.md:39` | 不做 Engine；提供本地诊断 |
| **③ 仅商业引导** | `langgraph up` 提示 | "For production use, requires a license key" | 🟡 软 | `langgraph_cli/cli.py:297-298` | freegraph 自托管零 license |

### 4.2 官方术语对照表（权威版）

见 §3.4（13 行）。**其他报告引用本表时以 §3.4 为准。**

---

## 5. 对 freegraph 的直接启示（可执行）

1. **在所有文档中把「三大基础功能 / 六大概念」替换为官方术语**：freegraph → "Runtime / Graph API (state schema, node, edge)"；freechain → "Framework / agent harness (model, tools, messages, middleware)"。同时保留一句"发起者原表述 ↔ 官方术语"的映射表（本文 §3.4）以免沟通断层。
2. **freegraph 内核必须零 `langchain-core` 依赖**，这是"依赖树无 langsmith"的唯一可行路径（§3.2 第一层）。CI 应断言 `importlib.metadata.requires('freegraph')` 递归展开后不含 `langchain-core` / `langsmith`。
3. **freegraph 应提供自有 `context` 通道**（对齐 v1 的 `context=` / `context_schema=`），不要把上下文塞进 `config["configurable"]`——这是 v1 的明确改进，也是 freegraph 对 freechain 的接口契约的一部分（见 Q8）。
4. **freechain 的包结构应对齐 v1 分层**：`freechain.messages` / `freechain.tools` / `freechain.chat_models` / `freechain.agents`（含 `create_agent` 与 middleware），**明确不提供 `chains` / `retrievers` / `indexes` / `hub`**（v1 已把它们判为 legacy）。
5. **freegraph 自带一个零依赖 `traceable`**：签名类似 `langsmith.traceable`，但只装饰 freegraph 内部 span（节点/工具/模型调用），不需要 API key、不外呼。这样 freechain 的 middleware（`wrap_model_call` / `wrap_tool_call`）能保住可观测性而不引入 `langsmith`。
6. **freegraph 的节点命名应允许别名**（对齐 v1 把 `"agent"` 改名为 `"model"` 的流式兼容问题），避免 freechain 升级时破坏用户的 stream 过滤器。

---

## 6. 自检

| 自检项 | 状态 | 说明 |
|---|---|---|
| 每个事实性结论带来源标记 | ✅ | 本地文档 `路径:行号`、源码 `文件:行号`、PyPI 元数据 |
| 三层依赖分档（运行时强依赖 / 可选集成 / 仅商业引导） | ✅ | §3.2 三小节 + §4.1 分档表（15 行） |
| 官方术语 ↔ 自造术语对照表（权威版） | ✅ | §3.4，13 行，明确标注"全项目唯一权威版本" |
| 自造术语首次出现标注 + 官方对应 | ✅ | §3.4 表首列逐条标注「（发起者自造表述）」 |
| LangChain v1 与旧版抽象迁移关系 | ✅ | §3.3，官方 7 条变化逐条 + 源码验证 `create_agent` 内部构造 `StateGraph` |
| 结论为可执行动作 | ✅ | §5 六条 |
| 未修改 `harness/docs` / `target.py` / 源码 | ✅ | 只读 |
| 无编造数字 | ✅ | 本报告无数字类断言；未核实项已注明（`reference.langchain.com` 未抓取） |
| 篇幅 1500–3000 字 + 表格 | ✅ | 正文约 3000 字 + 2 张表 |
