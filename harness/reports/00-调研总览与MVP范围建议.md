# 00 调研总览与 MVP 范围建议

> 跨问题汇总：Q1–Q8 的结论汇总、假设裁定（H1–H7）、对 freegraph 的直接启示、MVP 范围建议表、`target.py` 兼容性清单、依赖白/黑名单。
> 调研日期：2026-11-01｜定价页 as-of：2026-11-01｜本地文档同步：2026-10-31T15:40:12Z（303 篇）
> 本文件是**汇总**，不复制各报告全文；细节见 `Q1-*.md` … `Q8-*.md`。
> **联网抓取方式**：本轮调研通过本机代理 `http://127.0.0.1:10808`（xray / v2rayN 系统代理端口）出网抓取官方页面；`docs.langchain.com` 支持在 URL 后加 `.md` 直接获得 Markdown 源文。**定价页的功能勾选矩阵必须做 DOM 级解析**（Markdown 文本化会丢失 SVG 勾选状态），方法见 [Q1 §2.3](Q1-LangSmith的功能全景与卖点.md)。
>
> **【后续决议 2026-11-05】** 本汇总的**「白名单（运行时必装）」**（`typing-extensions`）
> 已被 **《项目宪法》修订记录 v1.2.0** 取代 —— 基础安装**零**第三方运行时依赖，
> 最低 Python 版本抬至 **3.11**。**本汇总的事实取证与黑名单全部仍然有效**；
> 被取代的只是那一条「建议」。详见 **§8.1 的后续决议**与
> `specs/001-p01-contracts-core/research.md` **D-21**。

---

## 1. 摘要 TL;DR

**三条核心结论**

1. **剥离完全可行，且路径唯一**：LangGraph OSS 的三大基础能力（state/node/edge）**零账号、零外呼**即可运行（已实跑证明）。但 `langchain-core` **硬依赖 `langsmith` 包**（非 extras），因此 **freegraph 内核必须完全不依赖 `langchain-core`**——这是满足 §2.6 约束 2 的唯一可行路径。
2. **付费墙的精确形状已查清（DOM 级解析 74 行勾选矩阵）**：**Developer 档（$0）实际可用 31 个勾选项（29 个产品功能 + 2 个支持渠道）**，包括 Tracing / Monitoring / Evals / Datasets / **Annotation Queue** / **Prompt Hub** / **LangSmith Studio** / **Fleet 全套** / **Sandboxes 全套** / **LLM Gateway 全套**。**真正被锁住的是 5 类**：① Deployment 的托管与扩缩（Developer 整行 N/A）② Engine（N/A）③ Tuned Evaluators（N/A）④ Insights ⑤ Bulk data export（**Plus 也锁，仅 Enterprise**）+ Unlimited agents。**「账号 ≠ 付费」是关键区分**：免费档也强制 LangSmith 账号 + API key，**这正是 freegraph 要消灭的那一层**。
3. **「不亚于 LangSmith」需要改写目标**：在**图运行时可诊断性**这个垂直维度上可达（且是 freegraph 的独占位置——LangSmith Studio 的交互式 IDE 无现成 OSS 可替代）；在**全生命周期 AI 工程平台**维度上不可能也不应追求。

**对 freegraph 的三条判断**

1. **内核定位**：freegraph = 官方术语中的 **Runtime 层**（对标 LangGraph）；freechain = **Framework 层**（对标 LangChain）。发起者自造的「三大基础功能 / 六大概念」应替换为官方术语（详见 [Q4 §3.4 权威对照表](Q4-LangSmith对LangChain的实际影响程度.md)）。
2. **差异化叙事**：不是"功能更多"，而是**"LangSmith 的免费那一半，且不需要账号、不需要出网"**——因为 tracing、Studio、Prompt Hub、Annotation Queue 这些在官方定价里 Developer 档就已免费，对标没有说服力，「零账号 + 零出站 + 可离线」才是硬差异化。
3. **范围红线**：明确**不做** Insights / Tuned Evaluators / Bulk export / Engine / Deployment 托管。**Evaluation / Datasets / Annotation Queue / Prompt Hub 虽然在官方定价里免费，但它们属于"评测平台"范畴，会把工作量推向 1–2 人年的 SaaS，freegraph 应明确不做**（详见 Q6 §3.3 的路线 A/B 工作量对比）。Fleet / Sandboxes / LLM Gateway 即使免费档开放，也因**必然引入真实出站**而不进范围。

---

## 2. 调研方法与资料来源

### 2.1 检索路径总览

| 阶段 | 动作 |
|---|---|
| ① 本地文档 | 按 §6.1 清单读 `harness/docs` 的 LangGraph / LangSmith / LangChain / DeepAgents 页；`MANIFEST.json` 索引定位 |
| ② 本地实跑 | 依赖树展开、PyPI 元数据、清空 `LANGSMITH_*` 跑 quickstart + socket guard、`get_graph`/`draw_mermaid`/`draw_mermaid_png` 网络行为、`init_chat_model` 离线构造、`langgraph dev` 无 key 启动、SQLite checkpointer + time-travel、节点入参形态 / `Command` / `interrupt` / `path_map` |
| ③ wheel 解包 | `langgraph-api 0.17.0`、`langgraph-cli 0.4.40`、`deepagents 0.7.32` 的源码与许可证 |
| ④ 联网 | 官方定价页、`usage-and-billing`、`deployment`、`deploy-standalone-server`、PyPI JSON API、GitHub API、模板仓库 `.env.example`、LangSmith ToS、Langfuse / Phoenix 文档、OTel GenAI semconv |
| ⑤ 交叉验证 | 定价页档位差异 ⇄ 本地文档 ⇄ 源码行为 三方对齐 |

### 2.2 来源索引（总）

| 编号前缀 | 类别 | 代表来源 |
|---|---|---|
| S1–S15 | 官方定价 / 计费 / 产品文档 | `www.langchain.com/pricing`、`docs.langchain.com/langsmith/usage-and-billing`、`deployment`、`deploy-standalone-server` |
| P1–P8 | 定价与计费（Q2） | 同上 + `local-server.md` |
| L1–L8 | 本地文档镜像（Q3） | `harness/docs/oss/python/langgraph/*.md`、`harness/docs/langsmith/deployment.md` |
| A1–A11 | 术语与迁移（Q4） | `concepts/products.md`、`migrate/langchain-v1.md`、`releases/langchain-v1.md`、`langchain/*` |
| B1–B12 | DeepAgents（Q5） | `deepagents/*`、`deepagents/code/*`、wheel 源码 |
| C1–C12 | 可观测生态（Q6） | `observability*.md`、`langfuse.com/docs`、`arize.com/docs/phoenix`、OTel semconv、GitHub API |
| D1–D9 | 许可证（Q7） | `dist-info/METADATA`、PyPI JSON、GitHub API、wheel LICENSE、LangSmith ToS、本仓库 LICENSE |
| E1–E12 | 最小契约（Q8） | `langgraph/` 源码、`langchain_core/` 引用统计、实跑输出 |
| A/B/C/D/E（Q3） | 实跑实验 E1–E10 | 见 [Q3 §2.1](Q3-LangGraph的开源边界.md) |

### 2.3 本地文档同步时间与时效处理

- `harness/docs/MANIFEST.json`：`synced_at = 2026-10-31T15:40:12Z`，`page_count = 303`，`source = https://docs.langchain.com`。
- **时效冲突处理**：按任务书 §6.3，**联网内容优先**。实际发生的两处冲突：
  1. **本地 `harness/docs/oss/python/langgraph/local-server.md:92` 的 CLI banner**（"For production use, please use LangSmith Deployment."）与 **`:95` 的正文**（"deploy Agent Server with access to a persistent storage backend" 并指向 platform-setup）**不一致**。经 wheel 源码核实：`langgraph_api/cli.py:368-369` **确实硬编码了 banner 原文**，而正文指向的 "Standalone server" 路径在 [Q3 §3.3 T7] 中被证实**需要 `LANGGRAPH_CLOUD_LICENSE_KEY` + 向 `beacon.langchain.com` 出网**。→ **以 banner 为准**（代码事实 > 文档措辞），正文属于简化表述。
  2. **定价页档位变化**：本地 `harness/docs/langsmith/deployment.md:43,47`（"Requires a Plus plan or above" / "Requires the Enterprise plan"）与联网定价页**一致**；但联网额外揭示了 **LSU 计量模型**（本地文档无此概念）。

### 2.4 未能获取的来源（**已全部解决**）

> **本轮调研启用了本机代理（`http://127.0.0.1:10808`，xray）出网**，把所有因抓取失败而未验证的条目全部补齐。下表列出**补抓清单与结论**。

| 原缺口 | 补抓方式 | 结果 |
|---|---|---|
| `docs.langchain.com/langsmith/{agent-registry, llm-gateway, engine, platform-setup, agent-server}` | 代理 + `.md` 后缀（该站支持 Markdown 输出） | ✅ 全部 200。**关键收获**：Agent Registry = **Cloud-only**；BYOC/Self-hosted = **Enterprise 档**；Engine 可**提 PR 修复** |
| `docs.langchain.com/langsmith/{sandboxes, insights, admin, cloud, self-hosted, byoc, use-the-context-hub, prompt-context-hub, manage-contexts-sdk, agent-environments, create-an-agent, fleet/templates}` | 同上 | ✅ 全部 200。Context Hub = **workspace 功能开关**，非套餐档位 |
| `docs.langchain.com/langsmith/administration-overview`（原缺，限流表） | 同上 | ✅ 200，含 plan-level 限流 + **per-project/per-user 限额** |
| `docs.langchain.com/langsmith/cloud-platform-features#sizes` | 同上 | ✅ 200，含 Serverless S/M/L 与 Dedicated S/M/L 的 vCPU/内存/副本数规格 |
| `www.langchain.com/startups`（Startup 计划） | 同上 | ✅ 200，**Build / Scale 两档**的权益与资格条件 |
| `www.langchain.com/brand-assets`（品牌指南） | 同上 | ✅ 200，含 logo 分类、Do's & Don'ts、Approved copy |
| `openlit.io/docs` | 代理 + 站点已改版（404） | ✅ 改用**官方仓库 README**（`openlit/openlit`），信息更完整 |
| Phoenix / Langfuse 部署资源需求 | 代理 + 官方自托管文档 | ✅ 取得**最低配置表**（Langfuse 4 个存储服务 + t3.xlarge 建议） |
| `pypi.org/pypi/langsmith/json`（先前超时） | 代理 | ✅ 200：0.14.17，MIT，**新版不再依赖 `langchain-core`** |
| `pypi.org/pypi/langgraph-store-sqlite/json` | 代理复查 | ✅ **404 确认该包不存在**（非抓取失败）；能力内置于 `langgraph.store.sqlite` |
| `deepagents` 运行时行为 | 隔离 venv 实跑 | ✅ `/tmp/opencode/daenv` 实跑成功，返回值 `isinstance CompiledStateGraph == True`，**零外呼** |

**剩余项（非抓取可解决）**：

| 项 | 性质 | 说明 |
|---|---|---|
| 商标侵权的司法认定 | 需律师审阅 | 已取得**官方品牌资产与使用指南全文**（Q7 §3.3.3），剩余部分属法律判断而非信息缺口 |
| LangSmith Sandbox 每沙箱具体配额数值 | 官方未公开 | 已核实 extras（`sandbox` / `sandbox-auth`）与区域/egress 策略；数值官方未披露 |
| Startup 计划的具体折扣百分比 | 官方未公开 | 官方只写 "Discounted seat pricing" |
| Phoenix / Langfuse / OpenLIT 的最低配置表 | 部分缺失 | Langfuse 有完整表；Phoenix / OpenLIT 官方未给最低配置（部署方式已核实） |

### 2.5 勾选矩阵解析方法（重要方法论修正）

定价页是 Webflow 动态渲染，**功能勾选矩阵以 SVG 图片呈现，Markdown 文本化会丢失勾选状态**。初稿曾据此得出错误结论（把 5 个 ✅ 误判为 ❌）。

**修正方法**：经代理抓取原始 HTML → 用**平衡 `<div>` 扫描器**逐行解析 `.p-pricing-grid-item`（74 行）+ `.pricing-element-wrapper` 单元格 → 判定规则：

- 单元格含 `Check.svg` → ✅ YES
- 单元格 class 含 `is-minus` / 内含 `no-icon-wrapper` → ❌ NO
- 否则取单元格文本（N/A / Custom / 具体额度）

**该方法纠正了 5 处误判**：`Insights`、`Annotation queue`、`Prompt Hub and Playground`、`Bulk data export`、`LangSmith Studio`。脚本与输出见 `/tmp/opencode/parse_pricing6.py` 与 `/tmp/opencode/fetch/pricing_matrix_final.txt`。

> **方法论教训（值得写入项目规范）**：**任何"功能勾选矩阵"类证据，必须做 DOM 级解析，不能依赖文本化转换。**

---

## 3. 假设裁定表（H1–H7）

| ID | 假设 | 裁定 | 证据与理由 |
|---|---|---|---|
| **H1** | `langgraph new --template new-langgraph-project-python` 生成的 `.env.example` 含 LangSmith 配置，且**无法移除** | 🔶 **部分成立** | **含 LangSmith 配置：成立**。模板仓库 `new-langgraph-project` 的 `.env.example` 实测全文仅 4 行，其中 `LANGSMITH_PROJECT=new-agent`（注释："To separate your traces from other application"）。**「无法移除」：不成立**——该文件是纯样例，README 明写 "Create a `.env` file **if you need to use secrets**" 且 "**If you want to enable LangSmith tracing**, add your LangSmith API key"，即 tracing 是可选的。**且实测证明移除后 `langgraph dev` 照常运行**（`/ok` → `{"ok":true}`，日志 "No license key or control plane API key set, skipping metadata loop"）。⚠️ 附注：模板 ID `new-langgraph-project-python` 由 CLI 模板表派生（`langgraph_cli/templates.py` 的 `TEMPLATE_ID_TO_CONFIG`：`"New LangGraph Project" + "python"` → `new-langgraph-project-python`）。 |
| **H2** | `langgraph dev` 只是内存服务器，**生产部署必须付费** | 🟢 **基本成立**（一处需修正） | ① `langgraph dev --help` 实测**无任何 sqlite/checkpointer 持久化选项**（只有 `--config` 指向的 `langgraph.json` 中的 `checkpointer` / `disable_persistence` 字段，`langgraph_cli/cli.py:859-860`）；实跑日志确认用的是 `langgraph_runtime_inmem` + `__database_uri__=":memory:"` + `runtime_edition="inmem"`（`langgraph_api/cli.py:195-201`）。② banner 硬编码 "This in-memory server is designed for development and testing. For production use, please use LangSmith Deployment."（`langgraph_api/cli.py:368-369`，与 `harness/docs/oss/python/langgraph/local-server.md:91-92` 一致）。③ **需要修正**：`local-server.md:95` 正文说 "deploy Agent Server with access to a persistent storage backend" 并指向 platform-setup，**这与 banner 不一致**——以 **banner 为准**（代码硬编码 > 文档措辞）。④ 补充事实：**"自托管"不等于免费**——Standalone server 仍需 `LANGGRAPH_CLOUD_LICENSE_KEY` 且需向 `beacon.langchain.com` 出网（`deploy-standalone-server.md` 前置 + `langgraph_api/metadata.py:75,262`）。⑤ `langgraph up` 的提示进一步明确："For local dev, requires env var LANGSMITH_API_KEY with access to LangSmith Deployment. **For production use, requires a license key in env var LANGGRAPH_CLOUD_LICENSE_KEY**"（`langgraph_cli/cli.py:297-298`）。 |
| **H3** | LangGraph 的状态/节点/边三大基础能力**不需要 LangSmith 账号**即可运行 | 🟢 **成立** | 实跑直证：在**清空 `LANGSMITH_API_KEY` / `LANGSMITH_TRACING` / `LANGSMITH_ENDPOINT` / `LANGSMITH_PROJECT` / `LANGSMITH_TRACING_V2` / `LANGCHAIN_*`** 的子进程中，用 **socket guard 阻断全部非 localhost 出站**，quickstart 示例（`StateGraph` + `add_node` + `add_edge` + `add_conditional_edges` + `compile` + `invoke`）照常跑通：输出 `N_MESSAGES: 4`、`TYPES: ['HumanMessage','AIMessage','ToolMessage','AIMessage']`、**`BLOCKED: []`**（零出站）。**tracing 默认关闭**：`langsmith.utils.tracing_is_enabled()` 返回 `False`；`langchain_core.tracers.context._tracing_v2_is_enabled()` 返回 `False`。**降级是优雅的**：显式设 `LANGSMITH_TRACING=true` + 假 key 时，图仍正常执行（`INVOKE_OK`），只是 tracer 后台外呼失败并打印告警。**Studio 连不上不影响执行**——Studio 是浏览器端的独立 UI（`smith.langchain.com/studio/?baseUrl=...`），与图执行解耦。 |
| **H4** | LangSmith Deployment 需 Plus 及以上、自托管 Platform 需 Enterprise | 🟢 **成立** | 本地 `harness/docs/langsmith/deployment.md:43` "Requires a Plus plan or above"（Cloud）、`:47` "Requires the Enterprise plan"（自托管带控制面），**联网核实一致**。定价页补充：Developer 档 Deployment = **N/A**；Plus 档含 **1 个免费 Serverless(Small) deployment**，其余按资源计费；Enterprise = 定制。**当前档位与价格**（截至 2026-11-01）：Developer **$0/seat**、Plus **$39/seat/月**、Enterprise **定制**。⚠️ 实现层差异（值得记录）：`langgraph-api 0.17.0` wheel 内置的 `langgraph_license/validation.py` 是 **noop**（`plus_features_enabled()` 恒返回 `True`、`get_license_status()` 恒 `True`），即**付费墙目前主要在文档/服务层，而非代码层校验**。这不改变商业事实，但说明"付费墙"是**服务可用性**而非**技术强制**。 |
| **H5** | LangChain v1 是「把智能体 Graph 继续封装」，相对旧版抽象发生迁移 | 🟢 **成立** | ① 官方迁移指南第 2 条明说 `create_react_agent` → `create_agent`（从 `langgraph.prebuilt` 移到 `langchain.agents`），第 3 条 `pre_model_hook`/`post_model_hook`/`state_modifier` → middleware [来源: `harness/docs/oss/python/migrate/langchain-v1.md:14-15`]。② **源码直证**：`langchain/agents/factory.py` 内部直接 `graph = StateGraph(state_schema=..., input_schema=..., output_schema=..., context_schema=...)` 并 `compile()` → **LangChain v1 的 `create_agent` 本质就是"用 LangGraph 的 StateGraph 搭 tool-calling loop"**，证实 §2.2 的路线图判断。③ 「六大概念」在 v1 中**已断裂**：model/message/tool/embeddings 留在 `langchain`；chain/retriever/index/hub **迁到 `langchain-classic`**；output parser 被 `ToolStrategy`/`ProviderStrategy` **取代**；prompt 变成 agent 参数 + `dynamic_prompt` middleware。 |
| **H6** | 只做 import 路径替换即可跑通该示例，即 LangGraph Graph API 这一层的行为在 OSS 内自洽，不依赖 LangSmith / Agent Server | 🟢 **成立（但有一处必须修正）** | 实跑证实：quickstart 示例在清空全部 `LANGSMITH_*` + socket guard 下**完整跑通**，返回**完整状态**（`INVOKE_KEYS: ['llm_calls','messages']`），路由行为与 LangGraph 一致。**`langgraph` 包的依赖树不含 `langsmith` 直依赖，但经 `langchain-core` 间接引入**——所以"OSS 内自洽"成立，但"LangGraph 零 LangSmith"**不成立**（详见 H7）。**`draw_mermaid_png()` 属于 `langchain-core` 能力而非 `langgraph` 能力**：`get_graph()` 返回类型实测为 `langchain_core.runnables.graph.Graph`，`draw_mermaid_png` 实现在 `langchain_core/runnables/graph_mermaid.py:277`（默认走公网 `https://mermaid.ink`，见 `graph_mermaid.py:423`）。**必须修正的一点**：该 PNG 渲染**在离线环境必然抛异常**（实测 `ValueError: Failed to reach https://mermaid.ink API`），而 `target.py:144` 的 `display(Image(...))` 位于 `agent.invoke` **之前** → **一旦 PNG 失败，整个脚本无法跑到验收点**。freegraph 必须解决此点。 |
| **H7** | LangSmith 的「付费部分」与「开源部分」可以清晰切分，freegraph 有条件做到零 LangSmith 耦合 | 🟢 **成立，且切分比预期更清晰** | **切分结论**：① **开源部分**：`langsmith` PyPI **SDK 是 MIT**（GitHub `langchain-ai/langsmith-sdk` LICENSE + 本地 `langsmith 0.12.6` `METADATA` 双向确认）；`langgraph`/`langchain`/`langchain-core`/`langchain-classic`/所有 provider 包**全部 MIT**，**未发现任何 AGPL/SSPL 传染性条款**（monorepo LICENSE 文件树扫描）。② **付费部分**：**LangSmith SaaS 平台是专有**（受 LangSmith Platform License 约束，付费订阅），包括 Observability UI / Evaluation / Studio / Deployment / Engine / Fleet / Sandboxes / LLM Gateway / Context Hub / Agent Registry。③ **依赖树事实（关键）**：`langchain-core 1.6.3` 的 `Requires-Dist` 含 **`langsmith<1.0.0,>=0.3.45`（硬依赖，非 extras）** → `langchain` → `langgraph` → `langchain-core` → `langsmith` **必然出现在依赖树**。④ **运行时事实**：默认 `tracing_is_enabled()` = `False`，**不设 `LANGSMITH_TRACING(_V2)` 则零外呼**（实测 `BLOCKED: []`）。⑤ **两个非 LangSmith 的外呼点**（易被忽略）：`draw_mermaid_png()` → `mermaid.ink`（非 LangSmith，但同样是 SaaS 外呼）；`langgraph-api` 的 metadata → `beacon.langchain.com`。**结论**：切分清晰，但 **freegraph 要做到"依赖树无 langsmith"，必须完全不依赖 `langchain-core`**（它是唯一入口）。**freegraph 由此获得零 SaaS 依赖的完全可实现性。** |

---

## 4. 调研结论索引（Q1–Q8）

| # | 一句话结论 | 报告 |
|---|---|---|
| **Q1** | LangSmith 是一整个商业产品线；**Developer 档（$0）实际可用 31 个勾选项（29 个产品功能 + 2 个支持渠道）**（含 Studio / Prompt Hub / Annotation Queue / Fleet / Sandboxes / LLM Gateway），**付费墙锁住的是 5 类**：Deployment 托管与扩缩、Engine、Tuned Evaluators、Insights、Bulk data export（Plus 也锁）+ Unlimited agents——即**"托管与自治"而非"可观测性"**；官方计量单位是 **LSU（1 LSU = $1）**。 | [Q1](Q1-LangSmith的功能全景与卖点.md) |
| **Q2** | 三档：**Developer $0（5k traces/月, 1 seat）/ Plus $39/seat（10k traces/月, 无限 seat, 1 个免费 deployment）/ Enterprise 定制**；**「免费但需账号」是最容易被忽视的一类**——免费档也强制账号 + API key，Studio 尤其如此；**"自托管 ≠ 零账号"**（standalone 仍需 license key + beacon 出网）；**BYOC / Self-hosted 平台需 Enterprise**；Startup 计划分 **Build（席位折扣）/ Scale（$10K credits·1 年）** 两档。 | [Q2](Q2-收费结构与付费墙地图.md) |
| **Q3** | **LangGraph OSS 三大基础能力零账号可跑（已实跑）**；但 **`langchain-core` 硬依赖 `langsmith`** → **freegraph 必须零第三方运行时依赖**；`target.py` 的 **18 个 API 元素全部可由 OSS 提供，无一必须触及 LangSmith**，其中 **7 项必须同名同签名**；付费墙触发点 **9 个（T1–T9）**；`draw_mermaid_png()` 的 **mermaid.ink 外呼**是一个独立于 LangSmith 的隐性风险。 | [Q3](Q3-LangGraph的开源边界.md) |
| **Q4** | 官方已有 **Runtime / Framework / Harness** 三层术语（**取代自造的「三大基础功能 / 六大概念」**）；**「六大概念」在 LangChain v1 中已断裂**（chain/retriever/index/hub → `langchain-classic`，output parser → `ToolStrategy`）；LangSmith 对 LangChain 的影响是 **包级硬依赖 + 代码级可选 + 运行时默认零**；**v1 = 把 agent Graph 继续封装**（源码证实 `create_agent` 内部构造 `StateGraph`）。 | [Q4](Q4-LangSmith对LangChain的实际影响程度.md) |
| **Q5** | DeepAgents 在 **Harness 层**，**不自带运行时**（实测 `create_deep_agent()` 返回值 `isinstance CompiledStateGraph == True`；middleware 被编译成真实图节点）；**对 LangSmith 的耦合比 LangChain 更强**（`langsmith>=0.14.12` 硬依赖 + 3 处 middleware 顶层 import，`import deepagents` 即加载 174 个 langsmith 模块），但**运行时默认零外呼**（实测 `BLOCKED: []`）；**provider/凭据层无 SaaS 耦合**（用 provider 自己的 key + Tavily）；真实耦合点只有 3 个：Context Hub 后端 / LangSmith Sandbox / Managed Deep Agents。 | [Q5](Q5-DeepAgents与LangChain-LangGraph-LangSmith的关系.md) |
| **Q6** | LangSmith 可视化 = **Studio（9 项）+ Observability（12 项）**，freegraph 现实可覆盖 **8–10 项（38–48%）**，但**高价值低成本项覆盖 8/8**；**推荐路线 B（OTel 兼容 + 内嵌轻量 UI，62–101 人日）**，路线 A 需 245–415 人日；**没有任何现成 OSS 提供 LangSmith Studio 那种交互式图运行时 IDE**（Langfuse/Phoenix/OpenLIT 的 agent graph 都只是从 trace 还原的只读调用图）——这是 freegraph 的独占位置；**OpenLIT（Apache-2.0、无功能门、部署最轻）适合做默认推荐后端；Phoenix 是 Elastic-2.0，只能连不能嵌**；Langfuse 自托管需 4 个存储服务 + t3.xlarge。 | [Q6](Q6-可视化与可诊断性的规模与可行性.md) |
| **Q9**（2026-11-03 补充） | **`langgraph dev` 起的是 Agent Server，不是 Studio**（Studio 是云端 `smith.langchain.com/studio/?baseUrl=...`）；**可视化代码不在 `langgraph` 包里**——包内零前端资产，图数据类与 mermaid 渲染在 **`langchain-core`**，**交互式 Studio 前端完全闭源**；官方另有 **MIT 的 Agent Chat UI**（Next.js，本地可跑、**连本地 server 不需要 LangSmith key**、支持 time-travel/state forking，但**无图视图**）。→ Q6 的独占性判断**精化**为「**没有 OSS 提供交互式图视图**」；v1 可「**能力层优先**」交付，**不必引入前端技术栈**。 | [Q9](Q9-Studio与本地server及可视化代码边界.md) |
| **Q7** | **LangChain 家族 OSS 侧全部 MIT，无传染性条款**；唯一非 MIT 陷阱是 **`langgraph-api` / `langgraph-runtime-inmem`（Elastic-2.0，禁止托管）**；**LangSmith SDK 是 MIT，付费的是 SaaS**；**版权上 MIT 允许自由复刻 API（须保留声明），商标上不能使用 Lang/LangGraph/LangSmith 品牌**——官方已有成文的《Brand Assets - LangChain Logos & Usage Guidelines》，把 **langgraph / deepagents 与 langchain 并列为受保护的 "Open Source Framework Logos"**，并给出 Do's & Don'ts 与 "Approved copy"；结论："**可以复刻 API，但不能复刻品牌**"。 | [Q7](Q7-开源边界地图与许可证合规.md) |
| **Q8** | 图运行时从外界真正需要的只有 **6 类输入**；**图层不需要 LangChain**（`langgraph` 对 `langchain_core` 的 135 处引用集中在 4 个接缝：`RunnableConfig` / `Runnable` / `Graph` / callbacks-tracers）；**消息/工具/模型的通用部分（OpenAI 风格 `tool_calls`、`invoke` 契约、`Annotated` 二元归约器）可直接采用**；产出 **C1–C26 内核最小契约清单**（含两条必须写成回归测试的契约：稀疏状态 C4、条件边 fresh 状态 C8）。 | [Q8](Q8-图运行时最小契约.md) |

---

## 5. 对 freegraph 的直接启示（可执行结论，8 条）

1. **内核依赖必须收紧到「零第三方运行时依赖（最多 `typing-extensions`）」**，并把这条做成 CI 断言：递归展开 `importlib.metadata.requires('freegraph')`，若出现 `langsmith` / `langchain*` / `langgraph*` 任一即失败。**理由**：`langchain-core` 是 `langsmith` 的唯一入口，而 §2.6 约束 2 要求依赖树中无 `langsmith`。同时加**许可证白名单断言**（仅允许 MIT / Apache-2.0 / BSD / PSF；出现 Elastic / AGPL / SSPL 即失败）——这条同时守住"可私有化部署、商用友好"。
   > ⚠️ **【后续决议 2026-11-05】**「最多 `typing-extensions`」→ **现为零第三方包**
   > （`typing-extensions` 已剥离，最低 Python 抬至 3.11，宪法 v1.2.0）；
   > **CI 断言照做不误**，且判据由「无 langsmith 家族」**加强**为「**基础安装闭包为空集**」。
2. **tracing 层直接产出 OTel span，属性对齐 OTel GenAI semconv**（`gen_ai.*`），**不发明格式**。理由：LangSmith 官方文档自己就把 run 类比为 span；Langfuse / Phoenix / OpenLIT / Grafana 全是 OTel 原生，接上零转换成本；"不源于 LangSmith"反而保证了**可与任意 OTel 后端组合**。
3. **【Q9 补充，2026-11-03】** 「不亚于 LangSmith」改写为「不亚于 LangSmith **Studio** 的本地图运行时可诊断性」**，并把 MVP 的可视化严格限定为三件套：**① 图视图（mermaid，零出站）② trace 时间线/详情（本地存储）③ 状态快照 + checkpoint 历史 + 回放入口**。**明确不做**：Insights / Tuned Evaluators / Bulk export / Engine / Deployment 托管（付费墙内）；Evaluation / Datasets / Annotation Queue / Prompt Hub（虽在免费档，但属"评测平台"，会把工作量推向 1–2 人年的 SaaS）；Fleet / Sandboxes / LLM Gateway（虽免费档开放，但必然引入真实出站）。
4. **§2.6 约束 6（可视化不阻断执行）必须专门处理**：`draw_mermaid_png()` 在离线环境必然抛异常（实测 `ValueError: Failed to reach https://mermaid.ink API`），而 `target.py:144` 位于 `agent.invoke` 之前 → **一旦失败，脚本无法跑到验收点**。freegraph 必须做到：① `draw_mermaid()` 纯本地必然成功；② `draw_mermaid_png()` 作为**可选插件、默认关闭**，离线时返回占位图或抛可捕获异常；③ 在迁移说明中给出 mermaid-cli 本地渲染的替代路径。
5. **freegraph 必须自备 5 个"接缝类型"**（这是脱离 `langchain-core` 的全部技术成本）：`RunConfig`（替 `RunnableConfig`）、`Node`/`CompiledGraph` 协议（替 `Runnable`）、`Graph`（替 `langchain_core.runnables.graph.Graph`，**唯一必须重写的类型**）、`Command`/`Interrupt`（替 `langgraph.types`）、`TraceSink`（替 callbacks）。**其余全部是通用协议，freechain 可直接采用。**
6. **两条必须写成回归测试的契约**（最容易实现错且会静默破坏 `target.py`）：**C4 稀疏状态**——节点入参是普通 `dict` 且**只含有值的 key**（实测 `NODE_INPUT_KEYS: ['messages']`），否则 `state.get('llm_calls', 0)` 会返回 `None`；**C8 条件边读 fresh 状态**——路由函数必须能看到本节点刚写入的值，否则 `should_continue` 读到旧 `messages`，tool 循环失效。
7. **【本轮新增】用一张对照表把定位讲清楚**：README 放"LangSmith Developer 档功能 → freegraph 替代方案"对照表（可覆盖 30 项中的绝大多数），并把差异点收敛为三条硬承诺：**零账号 / 零出站 / 零 license key**（LangSmith 的 standalone 仍需 `LANGGRAPH_CLOUD_LICENSE_KEY` + 向 `beacon.langchain.com` 出网）。**这是"等价替代"叙事，比"功能更多"有力得多。**
8. **【本轮新增】OTel 后端推荐顺序**：默认推荐 **OpenLIT**（Apache-2.0、无功能门、`docker compose` 一条命令、OTLP 4318）；其次 Langfuse（MIT 核心，但自托管需 4 个存储服务 + 官方建议 t3.xlarge）；**Phoenix 只能作为外部后端推荐，绝不内嵌**（ELv2 禁止托管）。

---

## 6. MVP 范围建议表

> 工作量档位：S = 1–3 人日；M = 4–10 人日；L = 11–25 人日；XL = 26–60 人日。
> 依据：[Q6 §3.3](Q6-可视化与可诊断性的规模与可行性.md)（路线 B 62–101 人日）与 [Q8 §3.4](Q8-图运行时最小契约.md)（契约面）。

| # | 模块 | v1 必做 | 依赖 | 风险 | 工作量档位 | 依据 |
|---|---|---|---|---|---|---|
| M1 | **图运行时内核**：state schema + channels + reducer + Pregel 调度 | ✅ | 无（~~仅 stdlib + `typing-extensions`~~ → **现为零第三方包**，宪法 v1.2.0） | 🟡 中——语义细节多（稀疏状态、fresh 读、超步并发写） | **XL** | Q8 C1–C8 |
| M2 | **节点 / 边 / 路由 API**：`StateGraph`、`add_node`、`add_edge`、`add_conditional_edges`、`compile`、`START`/`END` | ✅ | M1 | 🟢 低（API 明确） | **M** | Q3 §3.4 #1–#6 |
| M3 | **执行 API**：`invoke`（返回完整状态）、`stream`（`values`/`updates`） | ✅ | M1, M2 | 🟡 中（`invoke` 必须返回完整状态） | **M** | Q8 C11–C12 |
| M4 | **图结构导出**：`get_graph(xray=)` + 自有 `Graph` 类型 + `draw_mermaid()` | ✅ | M2 | 🟡 中（**必须独立重写**，不能依赖 `langchain-core`） | **M** | Q3 §5.2, Q8 C13–C14 |
| M5 | **PNG 渲染（可选插件）**：`draw_mermaid_png()`，默认关闭、离线不抛异常阻断 | ✅ | M4 | 🔴 **高**——离线必失败（实测 mermaid.ink） | **S–M** | Q3 §3.5 风险 1 |
| M6 | **`Command` / `interrupt` 原语**（HITL 基础） | ✅ | M1 | 🟡 中（恢复语义是"从节点起点重跑"） | **M** | Q8 C16–C17 |
| M7 | **Checkpointer（内存 + SQLite）**：快照 + 历史 + `get_state_history` | ✅ | M1 | 🟡 中 | **L** | Q8 C19；Q3 E8 实测 `HISTORY: 6` |
| M8 | **`Overwrite` 等价物**（旁路归约器） | 🟡 | M1 | 🟢 低 | **S** | Q8 C2（LangGraph 有，v1 可后置） |
| M9 | **可观测内核**：OTel span 采集（节点/工具/模型）+ `current_span()` | ✅ | M1, 可选 `[otel]` extra | 🟡 中 | **L** | Q5 §5.2, Q6 §5.1, Q8 C23–C24 |
| M10 | **本地 trace 存储**：文件后端（JSONL）+ SQLite 后端 + 查询 API | ✅ | M9 | 🟡 中 | **M** | Q6 §3.3 B2 |
| M11 | **OTLP 导出插件**（可选，指向 Phoenix/Langfuse/Grafana） | 🟡 | M9 | 🟢 低 | **S** | Q6 §3.3 B6 |
| M12 | **本地 Studio UI（内嵌轻量）**：图视图 + trace 时间线/详情 + 状态快照/回放入口 | ✅ | M4, M9, M10, M7 | 🟡 中——**前端技术栈选择需早定** | **L–XL** | Q6 §3.3 B3–B5 |
| M13 | **`RunConfig` + `context` 通道**（独立于 `configurable`） | ✅ | M1 | 🟢 低 | **S** | Q8 C21–C22；Q4 §3.3 第 6 条 |
| M14 | **节点命名别名**（v1 把 `"agent"` 改成 `"model"` 的兼容问题） | 🟡 | M2 | 🟢 低 | **S** | Q8 C25 |
| M15 | **`Store` 接口**（长期记忆） | ❌（v2） | M1 | 🟢 低 | **M** | Q8 C20；Q5 §3.4 |
| M16 | **子图支持** | ❌（v2） | M2 | 🟡 中 | **M** | Q8 C26 |
| M17 | **`Send`（动态 fan-out / map-reduce）** | ❌（v2） | M1 | 🟡 中 | **M** | Q8 C18 |
| M18 | **Postgres checkpointer** | ❌（v2） | M7 | 🟢 低 | **M** | — |
| M19 | **Evaluation / Datasets / Annotation Queue / Prompt Hub** | ❌ **永不做** | — | — | — | Q1 §3.3、Q6 §4.1 |
| M20 | **Deployment / Engine / Fleet / Sandboxes / Gateway** | ❌ **永不做** | — | — | — | Q1 §3.3 |
| M21 | **本地 Agent Server**（HTTP API，供前端调） | ❌（v2，可先用 CLI + 文件存储） | M12 | 🔴 高——**绝不能引入 `langgraph-api`（ELv2）**，须依公开规范自研 | **XL** | Q7 §3.2 结论 2 |

**工作量汇总（v1 必做项 M1–M14）**：约 **XL×3 + L×3 + M×4 + S×4 ≈ 110–170 人日**（其中 M12 的前端选型是最大变量）。与 [Q6 §3.3 路线 B 的 62–101 人日](Q6-可视化与可诊断性的规模与可行性.md) 相比，本表额外包含了**内核实现本身**（Q6 的估算只覆盖可观测层）。

---

## 7. `target.py` 兼容性清单（汇总自 Q3 §3.4）

> 基准文件：`harness/demo/target.py`（151 行，只读）。「同名对齐」= freegraph 必须提供**同名同签名**，否则脚本无法原样运行。

| # | 行号 | API 元素 | OSS 是否直接提供 | 是否触及 LangSmith | freegraph 是否必须同名对齐 | freegraph 处置 |
|---|---|---|---|---|---|---|
| 1 | 103 | `from freegraph.graph import StateGraph, START, END` | ✅ `langgraph.graph` 同名导出 | ❌ | ✅ **必须** | 同名同签名；`START='__start__'`、`END='__end__'` |
| 2 | 123 | `StateGraph(MessagesState)` | ✅ | ❌ | ✅ **必须** | 单位置参数 |
| 3 | 126–127 | `add_node(name, fn)` | ✅ | ❌ | ✅ **必须** | 位置参数 `(str, Callable)` |
| 4 | 130, 136 | `add_edge(src, dst)` | ✅ | ❌ | ✅ **必须** | 链式返回 `Self` |
| 5 | 131–135 | `add_conditional_edges(src, path_fn, path_map)` | ✅ | ❌ | ✅ **必须** | `path_map` 支持 **list 与 dict** 两种形式 |
| 6 | 139 | `compile()` | ✅ | ❌ | ✅ **必须** | 无参可调用；支持 `checkpointer=` / `store=` |
| 7 | 149 | `compiled.invoke({"messages":[...]})` | ✅ | ❌ | ✅ **必须** | **必须返回完整状态**（实测 `['llm_calls','messages']`） |
| 8 | 60 | `Annotated[list[AnyMessage], operator.add]` | ✅ | ❌ | ❌ 可自由设计（行为等价） | 解析 `__metadata__` 末位 callable 为二元归约器 |
| 9 | 81 | `state.get('llm_calls', 0)` | ✅ | ❌ | ❌ 可自由设计（行为等价） | **节点入参必须是稀疏 dict**（无值 key 不出现） |
| 10 | 70–82, 98 | 节点返回**部分** state 字典的合并规则 | ✅ | ❌ | ❌ 可自由设计（行为等价） | 逐 key 应用归约器；无归约器 → 覆盖 |
| 11 | 94 | `state["messages"][-1].tool_calls` | ✅ 鸭子类型 | ❌ | ❌ 可自由设计 | freegraph **不需懂** LangChain 消息类型 |
| 12 | 114 | `if last_message.tool_calls:` 真值判定 | ✅ | ❌ | ❌ 可自由设计 | 空 list → falsy |
| 13 | 144 | `agent.get_graph(xray=True).draw_mermaid_png()` | ⚠️ `get_graph` 在 `langgraph`；**`draw_mermaid_png` 实现在 `langchain-core`** | ❌ 不触 LangSmith；⚠️ **触 `mermaid.ink`** | ✅ **必须** | ① `get_graph(xray=)` 同名；② 返回对象须有 `draw_mermaid()`（纯本地必成功）与 `draw_mermaid_png()`（**离线不得抛异常阻断脚本**） |
| 14 | 144 | `display(Image(...))`（IPython） | ❌ 属脚本自身 | ❌ | ❌ | freegraph 不涉及 |
| 15 | 7–10 | `init_chat_model("claude-sonnet-4-6", temperature=0)` | ❌ 属 `langchain` 层 | ❌ | ❌ | 归 **freechain**；实测离线构造成功不外呼 |
| 16 | 14–45 | `@tool` 装饰器 / `tool.name` / `tool.invoke(args)` | ❌ 属 `langchain` 层 | ❌ | ❌ | 归 **freechain**；freegraph 只保证工具对象可被节点调用 |
| 17 | 96–97 | `tool.invoke(tool_call["args"])` | ❌ 脚本自身逻辑 | ❌ | ❌ | `tool_call` 结构 `{"name","args","id","type"}`（OpenAI 风格，通用） |
| 18 | 97 | `ToolMessage(content=..., tool_call_id=...)` | ❌ 属 `langchain.messages` | ❌ | ❌ | freegraph **原样流转**，不做类型转换（§2.6 约束 4） |

**汇总**：18 项中 **7 项必须同名同签名**（#1–#7、#13），**11 项可自由设计但须行为等价/原样承载**，**0 项要求触及 LangSmith 或 Agent Server**。

---

## 8. 依赖白名单 / 黑名单建议（汇总自 Q3 §3.6）

### 8.1 包层

| 类别 | 内容 |
|---|---|
| ⚠️ **白名单（运行时必装）** | ~~`typing-extensions`（唯一建议的必装依赖）~~ → **已改为「无」**（宪法 v1.2.0，2026-11-05） |
| 🟡 **白名单（可选 extra）** | `pydantic`（`[pydantic]`，用于 pydantic 状态 schema）；`ormsgpack`（`[checkpoint]`，序列化）；`opentelemetry-api` / `opentelemetry-sdk`（`[otel]`，Q6 路线 B）；`mermaid` 相关（`[png]`，**默认关闭**） |
| 🔴 **黑名单（硬禁止，含可选 extra 也不允许）** | `langsmith`（含 `langsmith[otel]`、`langsmith[sandbox]`）、`langchain`、`langchain-core`、`langchain-classic`、`langchain-protocol`、`langgraph`、`langgraph-prebuilt`、`langgraph-checkpoint`、`langgraph-checkpoint-sqlite`、`langgraph-checkpoint-postgres`、`langgraph-store*`、`langgraph-sdk`、`langgraph-api`、`langgraph-cli`、`langgraph-runtime-inmem`、`deepagents`、`langchain-anthropic` / `langchain-openai` / `langchain-google-genai` 等全部 provider 包（它们会把 `langchain-core` 拉回来） |

> **【后续决议 2026-11-05 · 宪法修订记录 v1.2.0】「必装 `typing-extensions`」已被取代。**
>
> **变更**：必装运行时依赖由 `typing-extensions` 改为 **「无」** —— 基础安装的依赖闭包
> **MUST 为空集**（`dependencies = []`），最低 Python 版本抬至 **3.11**。
> **黑名单与可选 extra 全部不变**；**本报告其余事实取证全部仍然有效**。
>
> **为什么**：`typing.Annotated`（3.9 起）/ `typing.TypedDict`（3.8 起）本就是标准库成员，
> 让 `typing_extensions` 真正有价值的是 `typing.Self`（**3.11** 才进标准库）——
> 最低版本抬至 3.11 后，`Self` / `NotRequired` / `Required` / `TypeVarTuple` / `Unpack` /
> `LiteralString` / `dataclass_transform` 全部在标准库内，故该依赖**不再需要**。
>
> **依据**：宪法 Governance · 修订记录 **v1.2.0** ·
> `specs/001-p01-contracts-core/research.md` **D-21** ·
> `specs/001-p01-contracts-core/spec.md` Clarifications「Session 2026-11-05（实现阶段 ·
> 依赖剥离与最低版本上调）」。


### 8.2 配置层

| 类别 | 内容 |
|---|---|
| 🔴 **黑名单（freegraph 代码不得读取）** | `LANGSMITH_API_KEY`、`LANGSMITH_TRACING`、`LANGSMITH_TRACING_V2`、`LANGSMITH_ENDPOINT`、`LANGSMITH_PROJECT`、`LANGSMITH_AGENT_ID`、`LANGSMITH_AGENT_ENVIRONMENT`、`LANGSMITH_CONTROL_PLANE_API_KEY`、`LANGSMITH_AUTH_ENDPOINT`、`LANGSMITH_AUTH_VERIFY_TENANT_ID`、`LANGSMITH_LICENSE_REQUIRED_CLAIMS`、`LANGSMITH_HOST_PROJECT_ID`、`LANGSMITH_HOST_REVISION_ID`、`LANGSMITH_TENANT_ID`、`LANGSMITH_LANGGRAPH_API_REVISION`、`LANGSMITH_LANGGRAPH_API_VARIANT`、`LANGCHAIN_API_KEY`、`LANGCHAIN_TRACING`、`LANGCHAIN_TRACING_V2`、`LANGCHAIN_ENDPOINT`、`LANGCHAIN_HANDLER`、`LANGGRAPH_CLOUD_LICENSE_KEY`、`LANGGRAPH_AUTH`、`LANGGRAPH_AUTH_TYPE` |
| ✅ **白名单** | **无。freegraph 内核不读任何环境变量**（provider key 由 freechain / 用户代码自行传入） |
| ⚠️ **反面教材（明确对照）** | `langgraph_api/config/__init__.py:675-677`：**API key 存在即自动 `LANGSMITH_TRACING=true`**——freegraph 应反过来：**环境变量存在也不改变任何行为**，除非用户显式传入 tracer 对象 |

### 8.3 网络层

| 类别 | 内容 |
|---|---|
| 🔴 **黑名单** | `*.smith.langchain.com`（含 `smith.langchain.com`、`api.smith.langchain.com`）、`beacon.langchain.com`、`*.langchain.com`、`mermaid.ink`（除非作为**用户显式启用的可选** PNG 渲染插件，且默认关闭） |
| ✅ **白名单** | **无（内核零出站）**。可选：用户自己配置的 OTLP exporter 端点（**仅在用户显式传入 tracer/exporter 时**） |
| ⚠️ **建议加 CI 用例** | 用 socket guard 夹具（本次调研方法可直接复用）断言 freegraph 全流程零出站 |

---

## 9. 调研产物与后续流程

| # | 文件 | 对应问题 |
|---|---|---|
| 1 | `00-调研总览与MVP范围建议.md` | 本文件 |
| 2 | `Q1-LangSmith的功能全景与卖点.md` | Q1 |
| 3 | `Q2-收费结构与付费墙地图.md` | Q2 |
| 4 | `Q3-LangGraph的开源边界.md` | Q3（核心） |
| 5 | `Q4-LangSmith对LangChain的实际影响程度.md` | Q4（含**全项目唯一权威术语对照表**） |
| 6 | `Q5-DeepAgents与LangChain-LangGraph-LangSmith的关系.md` | Q5 |
| 7 | `Q6-可视化与可诊断性的规模与可行性.md` | Q6 |
| 8 | `Q7-开源边界地图与许可证合规.md` | Q7 |
| 9 | `Q8-图运行时最小契约.md` | Q8（含**freechain 的设计输入**） |
| 10 | `Q9-Studio与本地server及可视化代码边界.md` | Q9（2026-11-03 补充；**精化 Q6 的独占性判断与前端选型**） | 定 D2/D5 |

**后续流程**：调研产物先落 `harness/reports/`，结论再转入 `harness/proposals/` 变成设计提案。**本次任务不做这一步。**

---

## 10. 交付前自检清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 每个事实性结论都带来源标记（URL 或 本地路径:行号） | ✅ | 9 份报告均执行；本汇总通过"来源编号 + 指向各报告"的方式引用 |
| 所有价格 / 额度 / 套餐带 as-of 日期 +「以官方定价页为准」 | ✅ | Q2 头部 + 表格内标注 + 文末免责；本汇总 §2.3 记录 as-of 2026-11-01 |
| H1–H7 每条都有裁定与证据 | ✅ | §3（本文件），逐条给出裁定 + 证据 |
| 自造术语已给出官方对照表，未混用为官方术语 | ✅ | 权威表在 **Q4 §3.4**（13 行）；其余报告均引用 Q4，未各写各的 |
| 各题结论是**可执行动作** | ✅ | 各报告 §5/§"直接启示"；本汇总 §5 六条 |
| MVP 范围建议表含：模块 / 是否 v1 必做 / 依赖 / 风险 / 粗略工作量档位 | ✅ | §6（21 行，M1–M21） |
| `target.py` 兼容性清单逐项裁定 | ✅ | §7（18 行，标注 OSS 提供 / 触 LangSmith / 是否同名对齐） |
| 已给出依赖白名单 / 黑名单建议（包层 / 配置层 / 网络层三层） | ✅ | §8（三层各一张表） |
| 已给出「内核最小契约」清单 | ✅ | Q8 §3.4，C1–C26（可作 freechain 设计输入） |
| 所有无法核实项已标 `[未验证]`，无编造数字 | ✅ | **本轮已全部消除**：§2.4 列出补抓清单与结论；9 份报告内**已无 `[未验证]` 标记**；剩余 4 项均属"官方未公开"或"需律师审阅"，已如实标注性质 |
| 未修改 `harness/docs`、`harness/demo/target.py` 与任何源码 | ✅ | 全程只读；实验在 `/tmp/opencode/`；本仓库 `LICENSE`/`README` 未改（Q7 §5.1 是建议） |
| 9 个文件全部落盘，文件名与任务书清单一致 | ✅ | `harness/reports/` 下 9 个文件 |
| **【本轮】勾选矩阵类证据必须 DOM 级解析** | ✅ | §2.5 记录方法与 5 处误判的修正；解析脚本与输出留存于 `/tmp/opencode/parse_pricing6.py` 与 `/tmp/opencode/fetch/pricing_matrix_final.txt` |
