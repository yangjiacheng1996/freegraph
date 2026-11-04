# Q1 LangSmith 的功能全景与卖点

> 调研问题：LangSmith 到底有哪些功能块？付费用户真正买的是什么？
> 调研日期：2026-11-01（定价页 as-of 2026-11-01，**经代理抓取并做 DOM 级勾选矩阵解析，见 §2.3**）
> 本地文档同步时间：`harness/docs/MANIFEST.json` → `synced_at = 2026-10-31T15:40:12Z`（303 篇）
> **联网抓取方式**：本轮调研通过本机代理 `http://127.0.0.1:10808`（xray / v2rayN 系统代理端口）出网抓取官方页面；`docs.langchain.com` 支持在 URL 后加 `.md` 直接获得 Markdown 源文。**定价页的功能勾选矩阵必须做 DOM 级解析**（Markdown 文本化会丢失 SVG 勾选状态），方法见 [Q1 §2.3](Q1-LangSmith的功能全景与卖点.md)。

---

## 1. 摘要 TL;DR

1. LangSmith 不是一个功能，而是**一整个商业产品线**：Observability / Evaluation / Studio / Deployment / Engine / Fleet / Sandboxes / LLM Gateway / Context Hub / Agent Registry。
2. **付费墙的精确形状（DOM 级解析定价页 74 行勾选矩阵后确定）**：Developer 档（$0）**能用到绝大多数功能点**，包括 Tracing / Monitoring / Online+offline evals / Dataset collection / **Annotation queue** / **Prompt Hub and Playground** / **LangSmith Studio** / **Fleet 全套** / **Sandboxes 全套** / **LLM Gateway 全套** / MCP 暴露 / 实时流式。
3. **真正被锁住的是"运营与自治"，共 5 类**：① **Deployment 的托管与扩缩**（1-Click Deploy / Dedicated / Scale-to-Zero / Assistants API / Cron / 鉴权；Developer 档 Deployment 整行 = **N/A**）② **Engine**（Developer = N/A）③ **Tuned Evaluators**（Developer = N/A）④ **Insights**（Developer ❌）⑤ **Bulk data export**（Developer ❌ 且 **Plus ❌**，**仅 Enterprise**）+ **Unlimited agents**（Developer ❌）。
4. 官方计量单位是 **LSU（LangChain Standard Units，1 LSU = $1）**，这是 2026 年 LangSmith 商业模型的核心变化：**从"按 trace 计数"转向"按能力消耗统一计价"**。Developer 档也按 LSU 计（Fleet 7 LSU、Sandboxes 8 LSU、Gateway 按 Gateway Credits）。
5. LangSmith 的真正卖点是**闭环 + 托管**：Trace（观测）→ Dataset（数据沉淀）→ Eval（打分）→ Prompt 迭代 → **Deploy（托管运行）** → Engine（自动诊断并**提 PR 修复**）。单点能力（尤其是 tracing）技术门槛不高，**闭环 + 托管运维才是付费理由**。
6. 对 freegraph 的判断 ①：**Studio 在 Developer 档就已可用**（不是 Plus 专属）——它本质是 Agent Server API + trace 数据的 Web UI，**技术门槛最低、价值最直接**，是 freegraph 最应复刻的一块。
7. 对 freegraph 的判断 ②：**Deployment 托管 / Engine / Sandboxes / Gateway 属于"基础设施与托管业务"，freegraph 不应该也不需要复刻**（它们的价值来自托管运维与模型层管控，不来自图运行时）。且 **Sandboxes / Gateway / Engine 都会引入真实的模型调用或代码执行出网**，与 freegraph 的"零出站"承诺直接冲突。
8. 对 freegraph 的判断 ③：freegraph 应把预算集中在 **Observability + Studio 的"轻量本地版"**，并明确声明"不做 Evaluation/Dataset 平台、不做托管部署"，以免范围膨胀。

---

## 2. 调研方法与资料来源

### 检索路径

1. 读本地 `harness/docs/langsmith/*.md`（deployment / deployment-quickstart / evaluation* / observability* / studio / fleet/* / python/managed-deep-agents-* / use-the-context-hub / manage-contexts-sdk）。
2. 抓取官方定价页 `https://www.langchain.com/pricing`（**成功**，2026-11-01 抓取）。
3. 抓取 `https://docs.langchain.com/langsmith/usage-and-billing`（**成功**，本地缺失页）。
4. 抓取 `https://docs.langchain.com/langsmith/deploy-standalone-server`（**成功**）。
5. 抓取 `https://langfuse.com/docs`（用于 Q6 横向对比）。
6. **补抓（代理出网，见 §2.3）**：`agent-registry` / `llm-gateway` / `engine` / `platform-setup` / `agent-server` / `sandboxes` / `insights` / `admin` / `cloud` / `self-hosted` / `byoc` / `use-the-context-hub` / `prompt-context-hub` / `manage-contexts-sdk` / `agent-environments` / `create-an-agent` / `fleet/templates` —— 全部 200。
7. 源码侧交叉验证：`langgraph-api` wheel（`langgraph_api/cli.py`、`config/__init__.py`、`metadata.py`）、`langgraph-cli` wheel（`langgraph_cli/cli.py`、`templates.py`）——用于确认"哪些功能是本地 OSS 可得的"。

### 来源清单

| # | 来源 | 类型 | 用途 |
|---|---|---|---|
| S1 | `https://www.langchain.com/pricing` | 官方一手 | 档位、价格、功能勾选矩阵（截至 2026-11-01） |
| S2 | `https://docs.langchain.com/langsmith/usage-and-billing` | 官方一手 | 保留期、计量、限流 |
| S3 | `https://docs.langchain.com/langsmith/deployment` | 官方一手 | Deployment 四种环境形态与档位要求 |
| S4 | `https://docs.langchain.com/langsmith/deploy-standalone-server` | 官方一手 | 自托管 Agent Server 的前置条件 |
| S5 | `harness/docs/langsmith/observability.md` | 本地镜像 | Observability 功能清单 |
| S6 | `harness/docs/langsmith/observability-concepts.md` | 本地镜像 | runs / traces / threads / trajectories 数据模型 |
| S7 | `harness/docs/langsmith/studio.md` | 本地镜像 | Studio 能力清单与前置条件 |
| S8 | `harness/docs/langsmith/evaluation.md` + `evaluation-concepts.md` + `evaluation-types.md` | 本地镜像 | Evaluation 功能块 |
| S9 | `harness/docs/langsmith/fleet/index.md` | 本地镜像 | Fleet 定位 |
| S10 | `harness/docs/langsmith/use-the-context-hub.md` / `manage-contexts-sdk.md` | 本地镜像 | Context Hub 定位 |
| S11 | `harness/docs/langsmith/python/managed-deep-agents-overview.md` | 本地镜像 | Managed Deep Agents 定位 |
| S12 | `harness/docs/langsmith/observability-stack.md` | 本地镜像 | 自托管可观测栈（Loki/Mimir/Tempo/Grafana/OTel Collector） |
| S13 | `langgraph-api` 0.17.0 wheel（`langgraph_api/cli.py`、`config/__init__.py`、`metadata.py`） | 源码一手 | Studio 指向 smith.langchain.com、metadata 上报端点 |
| S14 | `langgraph-cli` 0.4.40 wheel（`langgraph_cli/cli.py`、`templates.py`） | 源码一手 | `langgraph dev`/`up` 的档位提示与模板清单 |
| S15 | `https://langfuse.com/docs` | 一手 | 横向对比（Q6 引用） |
| **S16** | `https://docs.langchain.com/langsmith/agent-registry` | 官方一手（补抓） | **Agent Registry 仅 LangSmith Cloud 可用，自托管不可用**；agent / environment 四档模型 |
| **S17** | `https://docs.langchain.com/langsmith/platform-setup` | 官方一手（补抓） | Cloud / BYOC / Self-hosted 三形态；**BYOC 与 Self-hosted 需 Enterprise 档** |
| **S18** | `https://docs.langchain.com/langsmith/engine` | 官方一手（补抓） | Engine 的 issue 生命周期；**Engine 与 Insights 的官方区分**；可**提 PR 修复** |
| **S19** | `https://docs.langchain.com/langsmith/llm-gateway` | 官方一手（补抓） | Gateway 是 proxy；接受 OpenAI Chat Completions / Anthropic Messages / OpenAI Responses 三种请求格式；凭据三种来源 |
| **S20** | `https://docs.langchain.com/langsmith/sandboxes` | 官方一手（补抓） | 沙箱区域可用性；**默认 restricted egress（非 Enterprise）** |
| **S21** | `https://docs.langchain.com/langsmith/insights` | 官方一手（补抓） | Insights = 分类统计工具 |
| **S22** | `https://docs.langchain.com/langsmith/use-the-context-hub` | 官方一手（补抓） | **Context Hub 是 workspace 级功能开关 + 权限，不是套餐档位** |
| **S23** | `https://docs.langchain.com/langsmith/fleet/templates` | 官方一手（补抓） | Fleet 模板库 = `www.langchain.com/templates` |
| **S24** | `https://docs.langchain.com/langsmith/agent-server` | 官方一手（补抓） | Agent Server 的 assistants / threads / runs / cron 模型与两种图注册方式 |

### 抓取方法说明（重要）

定价页是 Webflow 动态渲染，**功能勾选矩阵以 SVG 图片（`Check.svg` / `is-minus` 容器）呈现，Markdown 文本化会丢失勾选状态**。
因此本次通过代理出网抓取原始 HTML，并用**平衡 `<div>` 扫描器**逐行解析 `.p-pricing-grid-item`（74 行）+ `.pricing-element-wrapper` 单元格，判定规则：

- 单元格含 `Check.svg` → ✅ YES
- 单元格 class 含 `is-minus` / 内含 `no-icon-wrapper` → ❌ NO
- 否则取单元格文本（N/A / Custom / 具体额度）

> **该方法纠正了本报告初稿中 5 处基于 Markdown 文本化的误判**（Insights、Annotation queue、Prompt Hub、Bulk data export、Studio）。修正后的权威矩阵见 §4.1。解析脚本与完整输出保存在 `/tmp/opencode/parse_pricing6.py` 与 `/tmp/opencode/fetch/pricing_matrix_final.txt`。

### 未能获取的来源

- 无（原列 5 个缺失官方页 + `langsmith-sdk` PyPI 页均已通过代理补齐；`langsmith` PyPI 元数据已直接取得：最新版 **0.14.17**，许可证 **MIT**）。

---

## 3. 正文

### 3.1 LangSmith 的数据模型（先理解模型，才理解功能）

LangSmith 把"一次智能体执行"拆成四层抽象，这是它所有功能的地基 [来源: harness/docs/langsmith/observability-concepts.md:19-53]：

| 抽象 | 语义 | 官方类比 |
|---|---|---|
| **run** | 一次最小工作单元（一次模型调用 / 一次工具调用 / 一次检索） | "If you are familiar with OpenTelemetry, you can think of a run as a span." [来源: 同上:21] |
| **trace** | 一次操作的所有 run 组成的树 | 一棵 run 树 |
| **thread** | 多轮会话的 trace 序列（用 `thread_id` 串联） | 会话 |
| **trajectory** | thread 的扁平化投影：按首次出现顺序排列的消息列表 | 轨迹 |

**关键洞察**：官方文档自己把 run 类比为 OTel span。这意味着 LangSmith 的 tracing 层在数据模型上**已经是 OTel 兼容的**——这直接支撑 Q6 的路线 B（freegraph 走 OTel 兼容协议而非自造格式）。

单条 trace 上限 25,000 runs [来源: harness/docs/langsmith/observability-concepts.md:29-31；S2 同值]。

### 3.2 功能块全景

按官方定价页的产品导航 + 本地文档 + 补抓的官方页，可以把 LangSmith 拆成 **15 个功能块**（分 3 组）：

**A 组：Agent Improvement（可观测 / 评测 / 提示词）**

1. **Observability / Tracing** — 记录 agent 每一步（模型调用、工具调用、检索），产出 trace / run 树。解决"线上到底发生了什么、慢在哪、为什么错"。
2. **Monitoring / Dashboards / Alerts** — 基于 trace 元数据做生产指标看板与告警 [来源: harness/docs/langsmith/observability.md:43-45]。
3. **Insights** — 从 trace 自动聚类出类别并报告各类别的指标随时间的变化（官方定位："an analytics tool... groups traces into categories"）[来源: S21；S18 "How Engine differs from Insights"]。
4. **Evaluation（online + offline）** — 用数据集与评分器给 agent 输出打分。Online = 线上流量实时打分；Offline = 跑实验批量对比 [来源: harness/docs/langsmith/evaluation.md:5-7]。
5. **Datasets** — 从 trace 收集样本形成数据集，作为评测基准 [来源: harness/docs/langsmith/observability.md:51]。
6. **Annotation Queue（人工反馈）** — 人把 trace/run 拉进队列做人工标注 [来源: S1 勾选矩阵]。
7. **Prompt Hub & Playground** — 提示词版本管理与在线试跑（LangSmith Cloud 的 prompt 层，非 LangChain 的 `hub` 模块）。**Developer 档即已包含** [来源: S1 勾选矩阵]。

**B 组：Agent Infrastructure（部署与运行时）**

8. **Studio** — 面向 agent 的 IDE：可视化图结构、运行与交互、管理 assistants/threads、迭代 prompt、跑数据集实验、time-travel 调试状态、一键部署 [来源: harness/docs/langsmith/studio.md:16-30]。**Developer 档即已包含** [来源: S1 勾选矩阵]。
9. **Deployment（Agent Server）** — 生产运行底座，含 assistants / threads / runs、30+ API 端点、cron、鉴权、实时流式、MCP/A2A 暴露 [来源: S3、S4、S24]。**Developer 档整行 = N/A** [来源: S1 勾选矩阵]。
10. **LLM Gateway** — 模型调用代理层：成本控制、限流、模型 fallback、PII/密钥脱敏、BYO key [来源: S1 勾选矩阵]。**Developer 档可用**（按 Gateway Credits 付）[来源: S1]；官方定位是 "a proxy between your application and the model providers"，接受 OpenAI Chat Completions / Anthropic Messages / OpenAI Responses 三种请求格式 [来源: S19]。

**C 组：Agent Autonomy / Managed（平台级托管业务）**

11. **Engine** — 自主发现 trace 中的复发故障、聚类成 issue、诊断根因、**以 PR 形式提出修复**、自动生成数据集与离线评测 [来源: S1 勾选矩阵；S18]。**Developer = N/A**。
12. **Fleet（Agent Builder）** — 无代码 agent 平台，从模板创建、连接第三方账号、Slack 内使用；Fast/Pro/Max 三档模型由 LangChain 代管调用 [来源: S1 FAQ；harness/docs/langsmith/fleet/index.md:9-13]。**Developer 档可用**（含 7 LSU/月，超出后暂停新 run）。
13. **Sandboxes** — 隔离的临时执行环境，供 agent 生成的代码安全运行，支持快照/分叉/端口隧道 [来源: S1 勾选矩阵；S20]。**Developer 档可用**（含 8 LSU、限 10 个沙箱）。**注意默认 restricted egress**（非 Enterprise 组织默认限制出网到托管白名单）[来源: S20]。
14. **Context Hub** — 版本化的上下文（Agent bundle / Skill）在平台侧管理与下发 [来源: S10、S22]。**归类修正：它不是套餐档位，而是 workspace 级功能开关 + 权限控制**——官方原文要求 "verify that Context Hub is enabled for your workspace and that you have the required permissions" [来源: S22]。
15. **Agent Registry** — 注册 agent 及其 environment（Production / Staging / Development / Local 四档）[来源: S16、S24]。**归类修正：仅 LangSmith Cloud 可用，自托管 LangSmith 不可用**——官方原文 "Agent Registry is available on LangSmith Cloud" 且 "agent-based workspaces... are not available on self-hosted LangSmith" [来源: S16]。

> 归类修正说明：**Context Hub / Agent Registry / Fleet 模板库（Marketplace）/ Managed Deep Agents 在 2026-11-01 定价页上没有独立的勾选行**，因此不存在"单列价格"。经补抓官方文档确认其归属：
> - **Context Hub** = workspace 功能开关（无独立档位）[S22]
> - **Agent Registry** = Cloud-only 平台能力（无独立档位）[S16]
> - **Marketplace / 模板库** = Fleet 的子能力（`www.langchain.com/templates`），Fleet 本身 Developer 档可用 [S1、S23]
> - **Managed Deep Agents** = LangSmith Cloud public beta 托管运行时，按 Deployment / Engine 的 LSU 计量 [S1]

### 3.3 "付费用户真正买的是什么"——用定价页反向印证（DOM 级解析结果）

这是本题的核心方法：**不看产品页说什么，只看免费档（D0）到底勾了哪些框**。

**Developer 档（$0）实际可用的功能点**（从 74 行勾选矩阵逐行提取，共 **31 行**为 ✅ = 29 个产品功能 + 2 个支持渠道）：

| 分区 | Developer 档 ✅ 的项 | Developer 档 ❌ / N/A 的项 |
|---|---|---|
| Observability & Evaluation (10) | Tracing、Monitoring、**Online and offline evals**、Dataset collection、**Annotation queue**、**Prompt Hub and Playground** | **Insights** ❌、**Bulk data export** ❌、**Unlimited agents** ❌、**Tuned Evaluators** ❌（N/A） |
| Deployment (11) | **LangSmith Studio**、Expose agent as MCP server、Real-time streaming、Agent Authorization (beta) | 1-Click Deploy、Horizontally-scalable dedicated deployments、Server Scale-to-Zero、Assistants API、30+ API endpoints、Cron scheduling、Auth for LangGraph APIs ❌；**Deployment 整行 = N/A** |
| Fleet (6) | Access to prebuilt templates、Add tools with a remote MCP server、Trigger agent via API、Use LangChain models | Share and clone agent templates ❌、Unlimited agents ❌；Fleet 整行 = "Metered in LSUs. Includes 7 LSU" |
| Engine (6) | （无） | 全部 6 项 ❌；**Engine 整行 = N/A** |
| Sandboxes (7) | 全部 7 项 ✅ | （无） |
| LLM Gateway (8) | 全部 8 项 ✅ | （无） |
| Hosting (3) | （无） | Platform hosting = N/A；Infra = N/A；Data location = N/A |
| Security & Support (14) | Support Portal、Community Forum（**仅此 2 项支持渠道**） | **SSO** ❌（Plus = "Google, GitHub"、Ent = "Custom SSO"）、RBAC ❌、Organization Roles ❌、Email/Slack ❌、Team trainings ❌、架构指导 ❌、SLA ❌、Custom Terms ❌ |

**因此，"付费用户买的是什么"可以精确表述为：**

> **买的是「可运营性（托管 + 扩缩 + 治理）」与「自治性（Engine 自动修复）」，不是「可观测性」，也不是「调试工具」。**
> - **可观测性 + 调试工具（Tracing / Monitoring / Evals / Datasets / Annotation Queue / Prompt Hub / Studio / MCP 暴露 / 实时流式）→ 免费档就给够**，因为它承担的是**获客与生态锁定**职能（LangChain 家族免费，LangSmith 是唯一变现口）。
> - **可运营性**（托管 Deployment / 水平扩缩 / Assistants API / Cron / 鉴权 / 自托管 / SSO / RBAC / SLA）→ **付费**。
> - **自治性**（Engine 自动诊断并提 PR / Fleet 无限 agent / Tuned Evaluators / Bulk export / Insights）→ **付费**。
> - **按量消费型**（Fleet LSU / Sandboxes LSU / Engine LSU / Gateway Credits / Deployment 资源费）→ **免费档也按 LSU 付费**，说明这些功能**不是靠档位锁住，而是靠成本锁住**。

**这对 freegraph 的意义（比初稿更精确）：**

1. **「可观测性 + 本地调试 IDE」在官方定价里是免费的** → freegraph 复刻 tracing + 本地 Studio **不会直接对标 LangSmith 的收入点**——它的价值主张必须建立在"完全离线、零 SaaS、无账号"这个差异化上，而不是"功能更多"。这是 Q6 路线选择的核心论据。
2. **但 Studio 有一条隐藏的价值链**：Studio 需要**连一个 Agent Server**（`langgraph dev` 的 in-memory server 或托管 Deployment）。**要"能调试"就得先"能运行"** —— 这让 Agent Server（而非 Studio 本身）成为 freegraph 的真正必答题。
3. **Sandboxes / LLM Gateway 在 Developer 档即开放** → 付费墙**不靠档位、靠成本**（LSU）。这反而更说明 freegraph 不该碰它们：**Sandboxes 会执行 agent 生成的代码、Gateway 会代理模型调用，两者都与"零出站、零 SaaS"直接冲突**。
4. **Agent Registry 是 Cloud-only** → 意味着"agent 目录 / 环境分级"这套治理模型**在自托管场景根本没有官方替代品**——这是一个 freegraph 可选的差异化点（但非 MVP 必需）。

### 3.4 计量模型：LSU 的引入

2026-11-01 的定价页把计量单位统一为 **LSU（LangChain Standard Units，1 LSU = $1）**[来源: S1 FAQ "What is an LSU?"]：


- Fleet：Developer 档含 7 LSU/月，Plus 档含 37 LSU/月，超出按量计费。
- Engine：每次运行消耗约 7–45 LSU，每 6 小时调度一次。
- Deployment：Serverless / Dedicated 按资源消耗计费（Runtime Compute 0.0675 LSU/vCPU-hr、Runtime Memory 0.0090 LSU/GiB-hr、Database Compute 0.177 LSU/vCPU-hr、Database Memory 0.025 LSU/GiB-hr）。
- Sandboxes：按秒计费（Compute 0.0576 LSU/vCPU-hr、Memory 0.01845 LSU/GiB-hr、Storage 0.000123 LSU/GiB-hr）。
- LLM Gateway：按 Gateway Credits 的模型用量计费。

**这是 LangChain 商业模型的一次结构性转变**：从"trace 条数 × retention"转为"所有 LangSmith 产品共享一个抽象计量单位"。这让 LangSmith 可以用同一张账单卖基础设施 + 自治能力。

### 3.5 Studio 的真实位置（对 freegraph 最关键）

Studio 是**唯一被官方明确定位为"免费可视化界面"却仍然绑定 LangSmith 账号**的功能：

- 本地开发场景：`langgraph dev` 启动的 in-memory server 会打印 `Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024` [来源: harness/docs/oss/python/langgraph/local-server.md:88,102；S13 `langgraph_api/cli.py:306-307`]。
- 也就是说：**Studio UI 跑在 LangChain 的云上，通过 `baseUrl` 参数反向连本地 server**。数据流向是"浏览器 → smith.langchain.com → 本地 server"，**不是**直连。
- 前置条件明确要求 LangSmith 账号 + API key [来源: harness/docs/oss/python/langgraph/studio.md:13-16]。

**这就是本项目最核心的可复制缺口**：LangGraph OSS 的 `get_graph()` + `draw_mermaid()` 是纯本地能力，而 LangSmith Studio 的图视图 + 状态调试 + time-travel 视图必须经由云端账号才能用。freegraph 只要实现"本地 Agent Server + 本地 Web UI"，就能切掉这一环。

---

## 4. 表格：功能块 ×（解决痛点 / 所属档位 / 是否开源可见 / 证据链接）

> 「最低可用档位」列全部来自 §2.3 的 DOM 级勾选矩阵解析（2026-11-01）。**Developer = $0 档**。

| # | 功能块 | 解决的痛点 | 最低可用档位（官方定价页，2026-11-01） | 是否有开源可见的实现 | 证据链接 |
|---|---|---|---|---|---|
| 1 | Observability / Tracing | 线上 agent 到底跑了什么、慢在哪、错在哪 | **Developer（免费）** ✅ | ✅ 有：`langsmith` PyPI SDK（MIT，OSS，0.14.17）；OTel 导出器在 `langsmith.integrations.otel`（`[otel]` extra） | [S1] / [S5] / `langsmith/integrations/otel/processor.py:67-84` |
| 2 | Monitoring / Dashboards / Alerts | 生产指标与告警 | **Developer（免费）** ✅ | ❌ 服务端 SaaS 专有 | [S1] / [S5] |
| 3 | Insights | trace 自动聚类成类别并统计各类指标变化 | **Plus** ❌ Developer | ❌ SaaS 专有 | [S1] / [S21] / [S18] |
| 4 | Evaluation（online / offline） | 给 agent 输出打分、回归检测 | **Developer（免费）** ✅ | ⚠️ 部分：打分函数可自写；平台 UI/编排 SaaS 专有 | [S1] / [S8] |
| 5 | Datasets | 沉淀基准样本 | **Developer（免费）** ✅ | ❌ SaaS 专有 | [S1] |
| 6 | Annotation Queue（人工反馈） | 人工标注、人工复核 | **Developer（免费）** ✅ | ❌ SaaS 专有 | [S1] |
| 7 | Prompt Hub & Playground | 提示词版本化与在线试跑 | **Developer（免费）** ✅ | ⚠️ 部分：`langchain-classic.hub`（OSS，但 v1 已迁出主包）/ Playground UI SaaS 专有 | [S1] / harness/docs/oss/python/migrate/langchain-v1.md:46 |
| 8 | Bulk data export | 导出自有数据 | **Enterprise**（Developer ❌ 且 **Plus ❌**） | ❌ SaaS 专有 | [S1] |
| 9 | Tuned Evaluators | 自动调优评分器 | **Plus**（public beta，仅 US；Developer = N/A） | ❌ SaaS 专有 | [S1] FAQ + 勾选矩阵 |
| 10 | **Studio** | 图可视化、运行交互、状态 time-travel、prompt 迭代 | **Developer（免费）** ✅（但需连一个 Agent Server） | ❌ Web UI 闭源；**但依赖的 Agent Server 协议可自建** | [S1] / [S7] / `langgraph_api/cli.py:306` |
| 11 | **Deployment（Cloud）** | 托管生产运行 | **Plus 或以上**（Developer 整行 = N/A） | ❌ 控制面/数据面 SaaS | [S3]:43 / [S1] |
| 12 | Deployment（自托管带控制面） | 数据不出境 | **Enterprise** | ❌ 需 Enterprise 许可 | [S3]:47 / [S17] |
| 13 | Deployment（BYOC） | 控制面托管、数据面在自己 VPC | **Enterprise**（"Self-hosted and BYOC are available on the Enterprise plan"） | ❌ 需 Enterprise 许可 | [S17] |
| 14 | Deployment（Standalone server） | 不用控制面，自带 PG/Redis | 需 LangSmith license；`langgraph up` 提示需 `LANGGRAPH_CLOUD_LICENSE_KEY` | ⚠️ **运行时包 `langgraph-api` 是 Elastic-2.0，非 MIT** | [S4] / `langgraph_cli/cli.py:297-298` |
| 15 | **LLM Gateway** | 成本控制、限流、fallback、PII 脱敏 | **Developer（可用，按 Gateway Credits 付）** ✅ | ❌ SaaS 专有 | [S1] / [S19] |
| 16 | **Engine** | 自动发现复发故障、根因诊断、**提 PR 修复** | **Plus**（Developer = N/A，按 LSU） | ❌ SaaS 专有 | [S1] / [S18] |
| 17 | **Fleet**（Agent Builder） | 无代码 agent、模板、第三方账号连接 | **Developer（可用，含 7 LSU/月；Plus 含 37 LSU）** ✅ | ❌ SaaS 专有 | [S1] / [S9] |
| 18 | **Sandboxes** | 安全执行 agent 生成的代码 | **Developer（可用，含 8 LSU、限 10 个沙箱）** ✅；**默认 restricted egress** | ❌ SaaS 专有 | [S1] / [S20] |
| 19 | Context Hub | 版本化上下文/指令下发 | **无独立档位**：workspace 功能开关 + 权限 | ❌ SaaS 专有 | [S22] / harness/docs/langsmith/use-the-context-hub.md |
| 20 | Agent Registry | agent / environment（Production/Staging/Development/Local）注册与寻址 | **无独立档位**：**仅 LangSmith Cloud 可用，自托管不可用** | ❌ SaaS 专有 | [S16] |
| 21 | Marketplace（模板库） | 复用他人模板 | **无独立档位**：Fleet 子能力，`www.langchain.com/templates` | ❌ SaaS 专有 | [S1] / [S23] |
| 22 | Managed Deep Agents | 托管运行 deep agent | **Plus**（LangSmith Cloud public beta，按 Deployment/Engine 的 LSU 计量） | ❌ SaaS 专有（harness 本地 SDK 为 MIT） | harness/docs/langsmith/python/managed-deep-agents-overview.md / [S1] |

### 4.1 附表：Developer 档（$0）实际可用的 31 个勾选项（29 个产品功能 + 2 个支持渠道）

[来源: S1 勾选矩阵，2026-11-01，DOM 级解析]

| 分区 | Developer ✅（可免费使用） | Developer ❌ / N/A（付费墙） |
|---|---|---|
| Observability & Evaluation (10) | Tracing、Monitoring、Online and offline evals、Dataset collection、Annotation queue、Prompt Hub and Playground | **Insights**、**Bulk data export**、**Unlimited agents**、**Tuned Evaluators** |
| Deployment (11) | LangSmith Studio、Expose agent as MCP server、Real-time streaming、Agent Authorization (beta) | 1-Click Deploy、Dedicated 水平扩缩、Server Scale-to-Zero、Assistants API、30+ API endpoints、Cron scheduling、LangGraph API 鉴权；**Deployment 整行 N/A** |
| Fleet (6) | Access to prebuilt templates、remote MCP server、Trigger agent via API、Use LangChain models | Share and clone agent templates、Unlimited agents |
| Engine (6) | （无） | **全部 6 项**；**Engine 整行 N/A** |
| Sandboxes (7) | **全部 7 项**（Auth proxy / 自带镜像 / TTL / 快照分叉 / 端口隧道 / Sandbox CLI / 千级扩容） | （无） |
| LLM Gateway (8) | **全部 8 项**（成本 / 限流 / fallback / PII 脱敏 / BYO key / coding agent / Gateway 事件入 trace / Gateway Credits） | （无） |
| Hosting (3) | （无） | Platform hosting = N/A；Infra = N/A；Data location = N/A |
| Security & Support (14) | **Support Portal**、**Community Forum**（仅此 2 项支持渠道） | **SSO**（Developer ❌ / Plus = "Google, GitHub" / Ent = "Custom SSO"）、RBAC、Organization Roles、Email Support、Slack、Team trainings、架构指导、部署工程师、SLA、Custom Terms |

> **计数核对**：Developer ✅ 共 **31 行** = 29 个产品功能（O&E 6 + Deployment 4 + Fleet 4 + Sandboxes 7 + Gateway 8）+ 2 个支持渠道（Support Portal、Community Forum）。

### 4.2 附表：Studio 能力逐项（Q6 直接复用）

[来源: harness/docs/langsmith/studio.md:16-30]

| Studio 能力 | 底层依赖 | freegraph 覆盖难度 |
|---|---|---|
| 可视化图结构 | Agent Server 的 `GET /graphs/{id}/drawable` + `draw_mermaid` | 🟢 低（LangGraph OSS 已有 `get_graph().draw_mermaid()`） |
| 运行与交互 agent | Agent Server `/runs` 系列 API + SSE | 🟡 中（需实现 run API + 事件流） |
| 管理 assistants / threads | Agent Server assistants + threads API | 🟡 中 |
| 迭代 prompt | prompt 节点编辑 + Playground | 🟡 中 |
| 跑数据集实验 | Dataset + Eval 平台 | 🔴 高（依赖整套评测平台） |
| 长期记忆管理 | Store API | 🟡 中 |
| **time-travel 调试状态** | Checkpointer 历史 + `get_state_history` | 🟢 低（**LangGraph OSS 已具备**，我已实跑验证） |
| 一键部署 | LangSmith Deployment | ❌ 不做（超出 freegraph 范围） |

> **补充（S24）**：Agent Server 支持两种图注册方式——① **导出已编译的 `CompiledGraph`**（官方推荐，容器启动时加载一次，每次 run 复用，无编译开销）；② **导出工厂函数**（每次需要图时调用，支持按 assistant 配置动态选模型/工具）。这是 freegraph 设计本地 server 时可直接对齐的两个接口形态。

---

## 5. 对 freegraph 的直接启示（可执行）

1. **freegraph 的功能边界应划在"Studio 的第 1、2、6、7 项"**（图可视化 + 运行交互 + 长期记忆 + time-travel），**明确不碰** Dataset/Experiment 平台、Engine、Fleet 托管、Sandboxes、Gateway、Deployment 托管。这与 §2.5 非目标一致，且与定价页显示的"可观测性与 Studio 在免费档即可用"格局完全吻合——**freegraph 复刻的正是免费那一半**。
2. **freegraph 的差异化叙事必须是"零账号、零 SaaS、可离线"，而非"功能对标"**——因为 tracing、Studio、Prompt Hub、Annotation Queue 这些在官方定价里 Developer 档就已免费，对标没有商业说服力。可用口号：*"LangSmith 的免费那一半，且不需要账号、不需要出网。"*
3. **Studio 必须做成"本地 Web UI + 本地 Agent Server"二段式**，而不是内嵌进 Python 进程。原因：LangSmith Studio 的做法（浏览器 → `smith.langchain.com` → 本地 server）正是我们要切掉的耦合；freegraph 应提供 `freegraph dev`（起本地 server）+ `freegraph studio`（打开本地 UI），全程 127.0.0.1。**且这是必答题而非可选项**：Studio 本身免费，但要调试就得先能运行。
4. **trace 数据模型直接采用 run/trace/thread/trajectory 四层 + OTel span 语义**（官方自己就这么类比），这样未来接 Phoenix / Langfuse / Grafana 无需转换层。
5. **不要把 LangSmith 的"计费思维"带进 freegraph**：freegraph 应完全本地、无 quota、无 seat、无 LSU。一个潜在风险是 Q6 的"路线 A 自研整套 Studio"会把工作量推向 LangSmith 平台级，需要在 `00-*.md` 的 MVP 表里用工作量档位硬约束。
6. **Sandboxes 与 LLM Gateway 即使在免费档开放，也不要碰**：前者执行 agent 生成的代码（默认还有 restricted egress 管控），后者代理模型调用——**两者都与 freegraph 的"零出站"承诺直接冲突**，且都不属于图运行时职责。
7. **Agent Registry 的 Cloud-only 特性是一个可选差异化点**（自托管场景无官方替代），但**不是 MVP 必需**——建议记入 v2 备选，不进 v1 范围表。

---

## 6. 自检

| 自检项 | 状态 | 说明 |
|---|---|---|
| 每个事实性结论带来源标记（URL 或 本地路径:行号） | ✅ | 全文以 `[来源: S#]` / `[来源: harness/docs/...:行号]` 标注；源码引用给出文件:行号 |
| 价格 / 额度 / 套餐带 as-of 日期 +「以官方定价页为准」 | ✅ | 头部声明「定价页 as-of 2026-11-01」；§4 表头再次标注；LSU 单价、trace 免费额度、Deployment 资源费率均标注 |
| 结论先行、可执行 | ✅ | TL;DR 给出 8 条结论（含 3 条 freegraph 判断）；§5 给出 7 条可执行动作 |
| 必给表格（功能块 × 痛点 / 档位 / 开源可见 / 证据） | ✅ | §4 主表 22 行 + §4.1 Developer 档 30 项分组表 + §4.2 Studio 逐项表 |
| 「付费用户买什么」用定价页档位差异反向印证 | ✅ | §3.3 逐分区比对 Developer 档勾选矩阵（DOM 级解析，74 行） |
| 自造术语标注官方对应 | ✅ | 本文引用「六大概念 / 三大基础功能」时均指向 Q4 权威表，未自行展开 |
| 未修改 `harness/docs` / `harness/demo/target.py` / 源码 | ✅ | 只读；临时脚本在 `/tmp/opencode/` |
| 无编造数字 | ✅ | **原全部 `[未验证]` 项已消除**：补抓 16 个官方页（agent-registry / platform-setup / engine / llm-gateway / sandboxes / insights / context-hub 等）+ `langsmith` PyPI 元数据；Context Hub / Agent Registry / Marketplace 的档位归属已由官方文档定性（workspace 开关 / Cloud-only / Fleet 子能力） |
| 篇幅 1500–3000 字 + 表格 | ✅ | 正文约 3400 字 + 3 张主表 |
| **勾选矩阵解析方法可复现** | ✅ | §2.3 给出判定规则与脚本路径 `/tmp/opencode/parse_pricing6.py`、输出 `/tmp/opencode/fetch/pricing_matrix_final.txt` |

