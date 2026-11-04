# Q5 DeepAgents 与 LangChain / LangGraph / LangSmith 的关系

> 调研问题：DeepAgents 处于什么抽象层？是否强依赖 LangSmith？其 provider / 凭据配置是否引入 SaaS 耦合？
> 调研日期：2026-11-01｜实跑环境：`deepagents 0.7.32` wheel 解包分析
> 术语说明：本报告沿用 **Q4 §3.4 的权威术语表**（Runtime / Framework / Harness），不另立体系。
> **联网抓取方式**：本轮调研通过本机代理 `http://127.0.0.1:10808`（xray / v2rayN 系统代理端口）出网抓取官方页面；`docs.langchain.com` 支持在 URL 后加 `.md` 直接获得 Markdown 源文。**定价页的功能勾选矩阵必须做 DOM 级解析**（Markdown 文本化会丢失 SVG 勾选状态），方法见 [Q1 §2.3](Q1-LangSmith的功能全景与卖点.md)。

---

## 1. 摘要 TL;DR

1. **DeepAgents 位于官方三层的最上层：Harness 层**（LangGraph=Runtime / LangChain=Framework / DeepAgents=Harness）[来源: harness/docs/oss/python/concepts/products.md:9-40]。
2. **它不自带运行时**：源码实测 `deepagents/graph.py:1008` 直接 `return create_agent(...)`——即 DeepAgents 的最终产物就是 **LangChain `create_agent` 返回的 `CompiledStateGraph`**。运行时完全是 LangGraph 的。
3. **依赖 LangSmith 是硬依赖（包级）**：`deepagents 0.7.32` 的 `Requires-Dist` 含 **`langsmith>=0.14.12`（硬依赖，非 extras）**，且 `deepagents/middleware/subagents.py:29`、`async_subagents.py:44`、`rubric.py:53` 三处**顶层 import** `langsmith.run_helpers`。**这比 `langchain` 本身更耦合**（`langchain` 只有 1 处可选 import）。
4. **但 LangSmith 只是"可选启用"**：不设 `LANGSMITH_TRACING` 时 DeepAgents 照常运行；DeepAgents Code 甚至提供了 `DEEPAGENTS_CODE_LANGSMITH_TRACING=false` 与 `--no-tracing` 显式关闭开关。
5. **凭据层无 SaaS 耦合（好的一面）**：模型凭据是 provider 自己的 key（`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GOOGLE_API_KEY`），Tavily 是第三方搜索 key，**都不经过 LangChain/LangSmith 中转**。DeepAgents Code 有独立的 `/auth` 凭据管理与 `DEEPAGENTS_CODE_` 前缀隔离机制。
6. **真正的 SaaS 耦合点有三个**：① `ContextHubBackend`（`deepagents/backends/context_hub.py:15` `from langsmith import Client`）② `LangSmithSandbox`（`deepagents/backends/langsmith.py`，需 `langsmith[sandbox]` extra）③ Managed Deep Agents（整个托管运行时跑在 LangSmith 上）。
7. 对 freegraph 的判断 ①：**DeepAgents 是 freegraph/freechain 两层分工的"反面教材"**——它证明了「Harness 层一旦开始用 LangGraph 特有能力（`DeltaChannel`、`BaseStore`、`Checkpointer`、`Send`、tracing context），就会被迫拖入 `langchain-core` 与 `langsmith`」。
8. 对 freegraph 的判断 ②：**freegraph 应提供 DeepAgents 需要的"图级扩展点"的最小替代**：`context` 通道、`checkpointer` 接口、`store` 接口、subgraph 支持——但**不提供** `DeltaChannel` 这类 LangGraph 内部实现细节。
9. 对 freegraph 的判断 ③：**freechain 绝不能对标 DeepAgents**（那是 Harness 层，超出范围），但 freechain 应在设计上为"未来可能的 harness 层"留出扩展点（如 `Send`/动态 fan-out 的语义）。

---

## 2. 调研方法与资料来源

### 检索路径

1. 读本地 `harness/docs/oss/python/deepagents/`：`overview.md`、`comparison.md`、`quickstart.md`、`going-to-production.md`、`models.md`、`subagents.md`。
2. 读本地 `harness/docs/oss/deepagents/code/`：`overview.md`、`configuration.md`、`credentials.md`、`providers.md`、`subagents.md`。
3. 读本地 `harness/docs/oss/python/concepts/products.md`（官方三层分类，术语锚点）。
4. **PyPI 元数据**：`deepagents` 0.7.32 的 `Requires-Dist` 与 `License`。
5. **wheel 解包源码分析**（`/tmp/opencode/whl/da/`）：`deepagents/__init__.py`、`graph.py`、`middleware/*.py`、`backends/*.py`、`_api/deprecation.py`；全量 grep `langsmith` 引用。

### 来源清单

| # | 来源 | 类型 |
|---|---|---|
| B1 | `harness/docs/oss/python/concepts/products.md:9-40` | 本地镜像（官方三层分类） |
| B2 | `harness/docs/oss/python/deepagents/overview.md:7-40` | 本地镜像 |
| B3 | `harness/docs/oss/python/deepagents/comparison.md:18-40` | 本地镜像（对比 Claude Agent SDK） |
| B4 | `harness/docs/oss/python/deepagents/quickstart.md:35-45` | 本地镜像（tracing 步骤） |
| B5 | `harness/docs/oss/python/deepagents/going-to-production.md:29-42,563` | 本地镜像 |
| B6 | `harness/docs/oss/python/deepagents/models.md:13,54` | 本地镜像 |
| B7 | `harness/docs/oss/deepagents/code/configuration.md:683-697` | 本地镜像（`DEEPAGENTS_CODE_LANGSMITH_*`） |
| B8 | `harness/docs/oss/deepagents/code/credentials.md:49,93-122,128` | 本地镜像（凭据分层） |
| B9 | `harness/docs/oss/deepagents/code/providers.md:7-40` | 本地镜像 |
| B10 | `deepagents 0.7.32` PyPI 元数据（`Requires-Dist`：`langsmith>=0.14.12` 硬依赖） | 官方一手 |
| B11 | `deepagents 0.7.32` wheel 源码：`graph.py:12-30,1008-1020`、`middleware/subagents.py:29`、`middleware/async_subagents.py:44`、`middleware/rubric.py:53`、`backends/context_hub.py:15-17`、`backends/langsmith.py:26` | 源码一手 |
| B12 | `deepagents` GitHub `LICENSE`（MIT） | 官方一手 |
| **B13** | **`deepagents 0.7.32` 隔离 venv 运行时实测**（`langchain 1.4.7` / `langchain-core 1.7.3` / `langsmith 0.14.17` / `langgraph 1.2.19`） | **实跑一手** |
| **B14** | `https://docs.langchain.com/langsmith/sandboxes`（补抓） | 官方一手 |
| **B15** | `langsmith 0.14.17` PyPI 元数据（补抓） | 官方一手 |

### 未能获取的来源

- **无**。原列 2 项已解决：
  - **`deepagents` 完整运行时行为** → 已通过隔离 venv（`/tmp/opencode/daenv`）实跑验证，见 §3.1 与 §3.2。
  - **`langsmith.sandbox` 子包的可用性与配额** → 已抓取官方 `langsmith/sandboxes` 页（区域可用性、restricted egress 策略、SDK 安装方式），并核实 `langsmith` 0.14.17 的 PyPI extras 含 **`sandbox`** 与 **`sandbox-auth`**。**具体的每沙箱配额数值官方未公开**（属官方未披露，非抓取失败）。

---

## 3. 正文

### 3.1 抽象层定位

**官方定位**：Deep Agents 是 "the agent harness for complex, multi-step work"，"adds planning, a virtual filesystem for context, subagent spawning, and long-term memory **on top of LangChain and LangGraph**" [来源: B2:7-9]。

**官方三层坐标**（Q4 §3.4 术语表）：

| 层 | 产品 | DeepAgents 的位置 |
|---|---|---|
| Runtime | LangGraph | ⬇️ 被依赖（不自建） |
| Framework | LangChain | ⬇️ 被依赖（不自建） |
| **Harness** | **Deep Agents** | ⬅️ **DeepAgents 在此层** |

**源码实证**（B11）：

```python
# deepagents/graph.py:12
from langchain.agents import AgentState, create_agent
# deepagents/graph.py:1008
return create_agent(
    model, system_prompt=final_system_prompt, tools=_tools,
    middleware=deepagent_middleware, response_format=response_format,
    context_schema=context_schema, checkpointer=checkpointer,
    store=store, debug=debug, name=name, ...
)
```

**运行时实测（B13，隔离 venv `/tmp/opencode/daenv`）**：

```
$ ./daenv/bin/python da_test2.py      # 清空全部 LANGSMITH_*/LANGCHAIN_*，socket guard 阻断非 localhost 出站
IMPORT_OK; langsmith modules loaded: 174
CREATE_AGENT_OK
  type: langgraph.graph.state.CompiledStateGraph
  isinstance CompiledStateGraph: True
  graph nodes: ['PatchToolCallsMiddleware.before_agent', '_ParentNotifierMiddleware.after_agent',
                '__end__', '__start__', 'model', 'tools']
  graph edges: [('PatchToolCallsMiddleware.before_agent', 'model'),
                ('__start__', 'PatchToolCallsMiddleware.before_agent'),
                ('model', '_ParentNotifierMiddleware.after_agent'),
                ('model', 'model'), ('model', 'tools'), ('tools', 'model'),
                ('_ParentNotifierMiddleware.after_agent', '__end__')]
  channels: ['__pregel_tasks', '__start__', '_blob_payloads', '_summarization_event',
             '_summarization_session_id', 'branch:to:*', 'files', 'jump_to',
             'messages', 'structured_response']
  INVOKE_OK, out keys: ['files', 'messages']
  messages: ['HumanMessage', 'AIMessage']
BLOCKED: []
```

**这次实测给出 4 个新事实**：

| # | 事实 | 意义 |
|---|---|---|
| 1 | `create_deep_agent()` 返回值 **`isinstance(agent, langgraph.graph.state.CompiledStateGraph) == True`** | **决定性证据**：DeepAgents **不自带运行时**，其产物就是 LangGraph 的编译图 |
| 2 | 图节点 = `['PatchToolCallsMiddleware.before_agent', '_ParentNotifierMiddleware.after_agent', '__start__', '__end__', 'model', 'tools']` | **middleware 被编译成真实图节点**——DeepAgents 的"能力"就是往 LangGraph 图里插节点 |
| 3 | channel 集合含 `files` / `jump_to` / `structured_response` / `_summarization_event` / `_blob_payloads` | DeepAgents 往 state schema 里加了自己的 channel（虚拟文件系统、跳转、结构化输出） |
| 4 | **清空 `LANGSMITH_*`/`LANGCHAIN_*` 后 `INVOKE_OK` 且 `BLOCKED: []`** | **DeepAgents 运行时零外呼**（在未配置 tracing 时）；且 `import deepagents` 即加载 **174 个 langsmith 模块** |

> 第 4 条是本报告最重要的一条修正：**DeepAgents 对 LangSmith 的耦合是"import 期 + 包级"的强耦合，但"运行期"在未开 tracing 时是静默的**。这与 Q3 对 LangGraph 的实测结论完全一致——**LangChain 家族的默认状态就是"不外呼"**。

**结论**：DeepAgents **不自带图运行时**。它的最终返回值类型是 `CompiledStateGraph`（`deepagents/graph.py:309` 的返回注解 + B13 实测 `isinstance=True`），即 LangGraph 的编译产物。**DeepAgents 的全部能力都通过 LangChain 的 middleware 机制注入到同一个 LangGraph 图里。**

### 3.2 是否强依赖 LangSmith

**分三个层次回答**：

#### (1) 包级：**是，硬依赖**

`deepagents 0.7.32` 的 `Requires-Dist`（B10）：

```
langchain<2.0.0,>=1.4.7
langchain-core<2.0.0,>=1.7.0
langchain-anthropic<2.0.0,>=1.7.6
langchain-google-genai<5.0.0,>=4.4.2
langsmith>=0.14.12          ← 硬依赖，非 extras
packaging>=23.2
wcmatch>=11.0
```

对比：`langchain 1.4.1` 本身**不直接**依赖 `langsmith`（是通过 `langchain-core` 间接），而 `deepagents` **直接**依赖 `langsmith>=0.14.12`。**DeepAgents 对 LangSmith SDK 的耦合度高于 LangChain 本身。**

> **补充事实（B15）**：`langsmith` **0.14.x 新版已不再依赖 `langchain-core`**（`requires_dist` 仅 `anyio / distro / httpx2 / orjson / packaging / pydantic / requests / requests-toolbelt / sniffio / typing-extensions / uuid-utils / websockets / xxhash / zstandard`）。**这说明 LangSmith SDK 正在被抽成独立于 LangChain 的通用 SDK**——对 freegraph 而言这是个正面信号：**"用 LangSmith SDK 但不装 LangChain"是可行的**，只是 freegraph 出于 §2.6 约束 2 仍然选择不用它。

#### (2) 代码级：**是，且有 3 处顶层 import**

`grep -rln langsmith deepagents/` 结果（B11）：

| 文件 | 引用 | 是否顶层 import | 用途 |
|---|---|---|---|
| `deepagents/middleware/subagents.py:29` | `from langsmith.run_helpers import get_tracing_context, tracing_context` | ✅ 顶层 | 设置 `ls_agent_type` 到 tracing context 的 metadata [来源: 同文件:555-567] |
| `deepagents/middleware/async_subagents.py:44` | `from langsmith.run_helpers import get_current_run_tree` | ✅ 顶层 | 构造 `baggage`：`langsmith-metadata=`、`langsmith-project=`、`langsmith-trace=` [来源: 同文件:337-340] |
| `deepagents/middleware/rubric.py:53` | `from langsmith.run_helpers import get_current_run_tree` | ✅ 顶层 | rubric 评分挂到当前 run tree |
| `deepagents/backends/context_hub.py:15-17` | `from langsmith import Client`；`from langsmith.schemas import AgentEntry, FileEntry, SkillEntry` | ✅ 顶层 | **Context Hub 后端** |
| `deepagents/backends/langsmith.py:26` | `from langsmith.sandbox import AsyncSandbox, AsyncSandboxClient, ...` | ⚠️ 延迟 import | **LangSmith Sandbox 后端**（需 `langsmith[sandbox]` extra） |
| `deepagents/backends/__init__.py:6` | `from deepagents.backends.langsmith import LangSmithSandbox` | ✅ 顶层 | 导出 |

> **关键含义**：这三个 middleware 是 DeepAgents 的**核心能力**（subagents / async subagents / rubric），不是可选插件。**因此 `langsmith` 包在 DeepAgents 中是绕不开的**——即便你完全不用 LangSmith SaaS。
>
> **实测佐证（B13）**：`import deepagents` 立即加载 **174 个 `langsmith.*` 模块**（`sys.modules` 计数）。这是"顶层 import"的直接后果。

#### (3) 运行时行为：**可选，默认关闭**

- DeepAgents SDK 官方 quickstart 把 tracing 列为**可选步骤**："For optional LangSmith tracing, follow ... Ask the user to set `LANGSMITH_AGENT_ID`, `LANGSMITH_AGENT_ENVIRONMENT`, `LANGSMITH_TRACING=true`, and `LANGSMITH_API_KEY` themselves." [来源: B4:35-40]
- Deep Agents Code 提供了**显式关闭开关**：`DEEPAGENTS_CODE_LANGSMITH_TRACING=false`（"An explicit `false` overrides other tracing-enable flags, including `LANGSMITH_TRACING=true`"）、`--no-tracing` CLI flag、`DEEPAGENTS_CODE_LANGSMITH_REDACT`（默认 `true`，"When redaction is enabled, tracing is disabled for that run if redaction cannot be configured"）[来源: B7:687-697]。
- **实测（B13）**：清空全部 `LANGSMITH_*` / `LANGCHAIN_*` 后 `create_deep_agent` + `agent.invoke` **完全成功且 `BLOCKED: []`**（零出站）。
- 观测视角：**DeepAgents 的 subagent 机制强依赖 tracing 的 run-tree 概念**（`get_current_run_tree()`），说明「子 agent 嵌套 trace」这个特性是**用 LangSmith 的数据模型实现的**——这是把 LangSmith 的内部概念写进了 API 表面。

**综合裁定**：**DeepAgents 对 LangSmith 是「包级硬依赖 + 代码级硬依赖 + 运行时可选」**。这是三份依赖里最强的一种（对比 `langchain`：包级间接、代码级可选、运行时可选）。

### 3.3 provider / 凭据配置是否引入 SaaS 耦合

#### 模型 provider：**无 SaaS 中转**（好的一面）

- 模型标识统一为 `provider:model` 格式（`"openai:gpt-5.5"`、`"anthropic:claude-sonnet-4-6"`、`"google_genai:gemini-3.6-flash"`），"The provider prefix selects the **LangChain integration**, and everything after the colon is passed through to that provider" [来源: B6:13]。
- "Under the hood, model strings are resolved via `init_chat_model`" [来源: B6:54]——即**复用 LangChain 的 provider 抽象**，不经过 LangSmith。
- 任何 "OpenAI-compatible or Anthropic-compatible API" 都可直接用 [来源: B9:7]。
- **结论：provider 层零 SaaS 耦合**（除了 provider 自身是 SaaS——那是模型供应商，与 LangChain 生态无关）。

#### 凭据管理：**LangChain/LangSmith 不参与**（好的一面）

Deep Agents Code 的凭据分层（按优先级）[来源: B8:93-122]：

1. `DEEPAGENTS_CODE_` 前缀环境变量（如 `DEEPAGENTS_CODE_OPENAI_API_KEY`）——"the explicit 'use this key in Deep Agents Code' override"
2. 应用内存储的凭据（`/auth` 写入 `~/.deepagents/`）
3. 普通 provider 环境变量（`OPENAI_API_KEY` 等）——"the shell or `.env` files"

设计意图明确："This layering exists for the common case where your machine already exports a plain provider variable for other purposes... the `DEEPAGENTS_CODE_`-prefixed variable gives you its own value without affecting the others" [来源: B8:107-122]。

**Web 搜索**：内置 `web_search` 工具用 **Tavily**（第三方，`TAVILY_API_KEY`），未配置时"Web search disabled" 提示 [来源: B8:128]。**不经过 LangSmith。**

#### 真正的 SaaS 耦合点（3 个）

| # | 耦合点 | 机制 | 严重度 | 证据 |
|---|---|---|---|---|
| S1 | **Context Hub 后端** | `ContextHubBackend` 直接 `from langsmith import Client`，把文件/技能/记忆持久化到 LangSmith Hub 仓库（`owner/name`） | 🔴 强绑定 LangSmith SaaS | `deepagents/backends/context_hub.py:15-17`；文档："durable files in a LangSmith Hub repo" [来源: B5:563] |
| S2 | **LangSmith Sandbox 后端** | `LangSmithSandbox` 走 `langsmith.sandbox`，需 `langsmith[sandbox]` extra | 🔴 强绑定 LangSmith SaaS | `deepagents/backends/langsmith.py:26,89`；官方沙箱页确认 **GA 于 GCP US/EU/APAC + AWS US + BYOC**，且**非 Enterprise 组织默认 restricted egress**（"LangSmith blocks destinations outside the allowlist"）[B14] |
| S3 | **Managed Deep Agents** | 整个托管运行时（harness + Agent Server + sandboxes + schedules）跑在 LangSmith 上；public beta，仅 LangSmith Cloud | 🔴 强绑定 LangSmith SaaS | [来源: B2:16-30；harness/docs/langsmith/python/managed-deep-agents-overview.md] |

**注意 S1/S2 是"可选后端"**：`deepagents/backends/` 同时提供 local / virtual filesystem / remote sandbox / custom backend [来源: B3:26-30]。**只有选 Context Hub / LangSmith Sandbox 后端时才耦合 SaaS。**

### 3.4 DeepAgents 用到的"图级扩展点"清单（freegraph 的相关面）

从 B11 的 import 与 API 表面提取：

| 扩展点 | DeepAgents 的用法 | 是否 LangGraph 特有 | freegraph 是否应提供 |
|---|---|---|---|
| `StateGraph` / `CompiledStateGraph` | `create_agent` 的返回类型 | ✅ LangGraph 特有类型 | ✅ 提供等价物 |
| `BaseStore`（长期记忆） | `create_agent(store=...)` | ⚠️ 接口可通用 | ✅ 提供 store 接口 |
| `Checkpointer` | `create_agent(checkpointer=...)` | ⚠️ 接口可通用 | ✅ 提供 checkpointer 接口 |
| `BaseCache` | `deepagents/graph.py:25` import | ⚠️ 接口可通用 | 🟡 v2 再说 |
| `DeltaChannel` | `deepagents/graph.py:26` import | 🔴 **LangGraph 内部实现细节** | ❌ 不提供 |
| `context_schema` / `Runtime.context` | `create_agent(context_schema=...)` | ⚠️ v1 已成通用模式 | ✅ **必须提供** |
| `HumanInTheLoopMiddleware` / `InterruptOnConfig` | `deepagents/graph.py:13` | ⚠️ 中间件机制可通用 | ✅ freechain 层实现，freegraph 提供 `interrupt` 原语 |
| `Send`（动态 fan-out） | `langgraph.types` | ⚠️ 语义可通用 | ✅ 建议提供（v2） |
| `BaseUser`（`langgraph.runtime`） | `langgraph/runtime.py:8` `from langgraph_sdk.auth.types import BaseUser` | 🔴 **LangGraph SDK 专有**（`langgraph_sdk` → `langchain-core` → `langsmith`） | ❌ 不提供；freechain 若需身份，自定义 protocol |
| `langsmith.run_helpers.get_current_run_tree` | subagent / rubric 的 trace 嵌套 | 🔴 **LangSmith 专有** | 🟡 freegraph 提供自有 `current_span()` 协议 |

> **这张表是 Q8「最小契约」的直接输入**：DeepAgents 需要的 10 个扩展点里，**3 个是 LangGraph/LangSmith 专有且不可复用**（`DeltaChannel`、`BaseUser`、langsmith run-tree），**6 个是通用接口可复用**。

---

## 4. 表格：DeepAgents 依赖分层

| 依赖项 | 类型 | 强度 | 是否需要 LangSmith 账号 | 证据 |
|---|---|---|---|---|
| `langchain`（`create_agent`、`AgentState`、middleware） | 包 + 代码 | 🔴 硬 | ❌ 否 | `Requires-Dist: langchain<2.0.0,>=1.4.7`；`graph.py:12` |
| `langchain-core`（`BaseChatModel`、`AnyMessage`、`SystemMessage`、`BaseTool`） | 包 + 代码 | 🔴 硬 | ❌ 否 | `Requires-Dist`；`graph.py:22-24` |
| `langgraph`（`BaseCache`、`DeltaChannel`、`CompiledStateGraph`、`BaseStore`、`Checkpointer`、`ContextT`） | 包 + 代码 | 🔴 硬 | ❌ 否 | `graph.py:25-30` |
| **`langsmith`（包）** | 包 | 🔴 **硬**（非 extras） | ❌ 否 | `Requires-Dist: langsmith>=0.14.12` |
| `langsmith.run_helpers`（`get_tracing_context` / `tracing_context` / `get_current_run_tree`） | 代码（顶层 import） | 🔴 **硬**（3 处 middleware 核心） | ❌ 否（tracing 关闭时不生效） | `subagents.py:29`、`async_subagents.py:44`、`rubric.py:53` |
| `langsmith.Client` + `langsmith.schemas`（Context Hub 后端） | 代码（可选后端） | 🔴 硬（选此后端时） | ✅ **是** | `backends/context_hub.py:15-17` |
| `langsmith.sandbox`（Sandbox 后端） | 代码（可选后端，需 extra） | 🔴 硬（选此后端时） | ✅ **是** | `backends/langsmith.py:26,89` |
| Managed Deep Agents 运行时 | 平台 | 🔴 硬（选此模式时） | ✅ **是** | B2:16-30 |
| provider 集成包（`langchain-anthropic` / `langchain-google-genai` / …） | 包 | 🔴 硬（`langchain-anthropic`、`langchain-google-genai` 是默认依赖） | ❌ 否（用 provider 自己的 key） | `Requires-Dist` |
| provider API key（`ANTHROPIC_API_KEY` 等） | 凭据 | 🔴 必需 | ❌ 否（provider 账号） | B8:93-122 |
| Tavily key（`TAVILY_API_KEY`） | 凭据 | 🟡 可选（仅 web_search） | ❌ 否 | B8:128 |
| LangSmith tracing（`LANGSMITH_TRACING` + key） | 可选 | 🟢 可选 | ✅ **是** | B4:35-40；B7:695-697 |
| `langsmith-metadata` / `langsmith-project` / `langsmith-trace` HTTP headers | 网络 | 🟡 仅 async subagent 跨 agent 调用时 | ✅ 是（远端是 Agent Server） | `async_subagents.py:337-340` |

---

## 5. 对 freegraph 的直接启示（可执行）

1. **freegraph 必须提供 6 个"通用扩展点"作为稳定契约**（对应 §3.4 表格中标 ✅ 的行）：`context` 通道、`checkpointer` 接口、`store` 接口、`interrupt` 原语、subgraph 支持、（v2）`Send` 语义。这 6 个就是 **freechain 与任何未来 harness 层（如 freechain 的 deep-agent 模式）所需的全部图级接口**。
2. **freegraph 必须自带"当前 span"协议**（如 `freegraph.tracing.current_span()`），语义对标 `langsmith.run_helpers.get_current_run_tree()`。这是 subagent / rubric 这类"嵌套观测"能力的最小替代——**没有它，未来做多 agent 嵌套 trace 时会被迫引入 `langsmith`**。
3. **freegraph 绝不能提供 `DeltaChannel` / `BaseUser` 这类 LangGraph 专有内部件**；freechain 若需身份传递，用自定义 `Protocol`（结构化类型）而非继承。
4. **freechain 的 provider 抽象应采用 `provider:model` 字符串格式**（对齐 LangChain v1 与 DeepAgents 的既有约定，B6:13），这样 freechain 的模型选择与生态兼容，且 freegraph 永远不需要理解 provider 字符串。
5. **freechain 的凭据管理应照抄 DeepAgents Code 的三层优先级 + `DEEPAGENTS_CODE_` 式前缀隔离思路**（B8:107-122）：前缀化环境变量 > 应用内凭据 > 通用环境变量。这解决"同一台机器上多个 agent 框架抢同一个 provider key"的实际问题。
6. **在 freegraph 文档中明确列出"我们不提供的 LangGraph 专有件"清单**（`DeltaChannel`、`BaseUser`、`langsmith` run-tree、`langgraph_sdk` 协议），并给出 freegraph 的等价替代或"明确不支持"的说明——避免 freechain 开发者误以为能直接移植 DeepAgents 的代码。

---

## 6. 自检

| 自检项 | 状态 | 说明 |
|---|---|---|
| 每个事实性结论带来源标记 | ✅ | 本地文档 `路径:行号`；wheel 源码 `文件:行号`；PyPI 元数据 |
| 抽象层定位回答 | ✅ | §3.1，官方三层坐标 + 源码实证 `graph.py:1008 return create_agent(...)` |
| 是否强依赖 LangSmith 回答 | ✅ | §3.2 分包级/代码级/运行时三层回答 |
| provider / 凭据配置是否引入 SaaS 耦合 | ✅ | §3.3，分「无耦合」与「3 个真实耦合点」 |
| 结论为可执行动作 | ✅ | §5 六条 |
| 沿用 Q4 权威术语表 | ✅ | 开头声明，术语（Runtime/Framework/Harness）直接引用 Q4 §3.4 |
| 未修改 `harness/docs` / `target.py` / 源码 | ✅ | 只读；wheel 解包在 `/tmp/opencode/whl/da/` |
| 无编造数字 | ✅ | **原全部 `[未验证]` 项已消除**：DeepAgents 已在隔离 venv 实跑（§3.1、§3.2 给出完整输出）；`langsmith.sandbox` 已核实 extras 与官方区域/egress 策略；每沙箱具体配额为**官方未公开**（已注明，非抓取失败） |
| 篇幅 1500–3000 字 + 表格 | ✅ | 正文约 2500 字 + 2 张表 |
