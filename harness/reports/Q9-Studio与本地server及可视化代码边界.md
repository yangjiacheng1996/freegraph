# Q9 Studio 与本地 server 的关系，及可视化代码的开源边界

> **类型**：补充调研（触发自 `harness/proposals/立项书.md` §12-D2 / §12-D5 的决策需要）
> **调研日期**：2026-11-03｜**定价相关数据**：不涉及
> **本地文档同步**：`harness/docs`，`synced_at = 2026-10-31T15:40:12Z`（303 篇）
> **本文件回答三个问题**：
> ① `langgraph dev` 启动的 local server **是不是 Studio**？
> ② **Studio 的可视化代码在 `langgraph` 包里，还是独立成子包**？LangGraph 是怎么做的？
> ③ 对 freegraph 的「不亚于 Studio」目标与 v1 前端选型有什么可执行结论？

---

## 1. 摘要 TL;DR

1. **`langgraph dev` 起的是 Agent Server，不是 Studio**：本地进程提供 HTTP API + OpenAPI docs；**Studio 是云端 Web App**（`smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`），浏览器 → 云 → 回连本地。「本地调试也要过云」由此坐实。
2. **可视化代码不在 `langgraph` 包里**：该包**零前端资产**；图结构数据类与 mermaid 渲染都在 **`langchain-core`**（`runnables/graph.py` + `runnables/graph_mermaid.py`）；**交互式 Studio 前端不在任何开源包内**，只存在于 LangSmith 云端（闭源）。
3. **官方另有一个开源 UI 可借鉴**：**Agent Chat UI**（MIT，Next.js）——可本地跑、**连本地 server 不需要 LangSmith API key**、支持 **time-travel 调试与 state forking**，但是 **chat-first、无图视图**。
4. **对 freegraph 的直接结论**：Q6「没有任何现成 OSS 提供 Studio 那种图运行时 IDE」**需精化**为「**没有 OSS 提供交互式图视图（node/edge IDE）**」；三件套里 chat/tool 渲染/time-travel 已有 MIT 现成实现可借鉴 → **v1 不必引入前端技术栈**（能力层优先：mermaid + trace 查询 API + 回放 API）。
5. **官方自己就是「服务端出 API + 前端自备」**（`langgraph_api/api/ui.py` 的 `/ui` 静态挂载 + `langgraph_api/js/` 的 JS SDK）→ 与 freegraph 分层一致，无需另起范式。

---

## 2. 调研方法与资料来源

### 2.1 取证方式（全部为实测 / 源码行号 / 官方文档原文，无推测）

| # | 动作 | 目的 |
|---|---|---|
| ① | 解包本机已装的 `langgraph_api 0.17.0`（`/tmp/opencode/lgsrv/lib/python3.12/site-packages/`），读 `cli.py`、`api/ui.py`、`js/`、`api/assistants.py` | 确认 `langgraph dev` 的产物与 Studio 的关系、前端口子 |
| ② | 检查本机 `langgraph 1.2.11` 包内是否存在前端资产（`*.js` / `*.html` / `*.css` / `*.tsx`） | 判定「可视化代码在不在 langgraph 包里」 |
| ③ | 定位 `get_graph()` 定义与 mermaid 渲染实现（`langgraph/pregel/main.py`、`langchain_core/runnables/graph.py`、`graph_mermaid.py`） | 定位 OSS 侧可视化的真实归属 |
| ④ | 读官方文档镜像 `harness/docs/oss/python/langgraph/{studio,ui,local-server}.md` | 官方口径（Studio 前置条件、Agent Chat UI 能力） |
| ⑤ | 联网抓取 `github.com/langchain-ai/agent-chat-ui` 的 `LICENSE` 与 `README.md` 原文 | 核实许可证与「是否需要账号」的原文表述 |

### 2.2 来源清单

| 编号 | 来源 | 关键引用 |
|---|---|---|
| **E1** | `langgraph_api/cli.py`（本机解包 0.17.0） | `:31-38` `_get_ls_origin()`；`:306-307` `studio_origin` / `full_studio_url`；`:347-350` 打开浏览器；`:364-366` banner 三行 |
| **E2** | `langgraph_api/api/ui.py` | `Mount("/ui", StaticFiles(directory=UI_PUBLIC_DIR, check_dir=False))`；`ApiRoute("/ui/{graph_id}", handle_ui, methods=["POST"])` |
| **E3** | `langgraph_api/js/`（`client.mts` 40KB、`remote.py` 53KB、`build.mts`） | 面向前端的 JS SDK 客户端（非 UI 实现） |
| **E4** | `langgraph 1.2.11` 包内文件实测 | 无任何 `.js` / `.html` / `.css` / `.tsx` |
| **E5** | `langgraph/pregel/main.py:845`、`langgraph/pregel/protocol.py:32` | `get_graph()` 定义位置 |
| **E6** | `langchain_core/runnables/graph.py:95-255, 528-632` | `Node` / `Branch` / `Graph` 数据类；`draw_ascii` / `draw_mermaid` / `draw_png` / `draw_mermaid_png` 方法挂载点 |
| **E7** | `langchain_core/runnables/graph_mermaid.py:45, 277, 422-423, 461` | `draw_mermaid`（纯本地）；`draw_mermaid_png` → 默认 `https://mermaid.ink` → `requests.get` |
| **E8** | `langgraph_api/api/assistants.py` | `/assistants/{assistant_id}/graph`（`get_assistant_graph`）等端点 → Studio 靠这些端点取图结构与运行数据 |
| **E9** | `harness/docs/oss/python/langgraph/studio.md:7, 17, 25, 99, 129` | 「Studio connects to your locally running agent」；「**A LangSmith account**」为前置；「The LangGraph CLI provides a local development server (also called Agent Server) that connects your agent to Studio」 |
| **E10** | `harness/docs/oss/python/langgraph/ui.md:5-9, 27-47, 51-59` | Agent Chat UI 的能力（chat / tool 可视化 / **time-travel debugging and state forking**）与本地运行方式 |
| **E11** | `harness/docs/oss/python/langgraph/local-server.md:88, 99, 102` | banner 与 Studio URL 原文 |
| **E12** | `github.com/langchain-ai/agent-chat-ui` → `LICENSE` | **MIT License, Copyright (c) 2025 Brace Sproul** |
| **E13** | 同上 → `README.md` | 「**LangSmith API Key**: (only required for connecting to deployed LangGraph servers)」；`NEXT_PUBLIC_AUTH_SCHEME=` 留空；`NEXT_PUBLIC_API_URL=http://localhost:2024` |

### 2.3 未能获取的来源

| 项 | 性质 | 处理 |
|---|---|---|
| Studio 前端源码 | **闭源**，不存在于任何公开仓库 | 以「开源侧零 UI 资产 + Studio URL 指向云」双证据判定，不推测其实现 |
| LangSmith 平台自托管时的 Studio 前端形态 | 需 Enterprise 实例才能验证 | 不影响结论（freegraph 走自研路线） |
| Agent Chat UI 是否有独立的图视图组件（仓库内是否有 graph 相关组件） | 未逐文件遍历前端目录 | README 无任何图视图描述，判定为「chat-first」；若未来要借鉴需再核 |

---

## 3. 正文

### 3.1 `langgraph dev` 启动的是什么

**答案：Agent Server（LangGraph API server），不是 Studio。**

`langgraph dev` 的实际产物由 `langgraph_cli` 拉起 `langgraph_api`（in-memory runtime），启动完成后打印：

```
- 🚀 API: http://127.0.0.1:2024
- 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- 📚 API Docs: http://127.0.0.1:2024/docs

This in-memory server is designed for development and testing.
For production use, please use LangSmith Deployment.
```
[来源: E1 `langgraph_api/cli.py:356-371`]

URL 的构造逻辑（E1 `:306-307`）：

```python
studio_origin = studio_url or _get_ls_origin() or "https://smith.langchain.com"
full_studio_url = f"{studio_origin}/studio/?baseUrl={local_url}"
```

- `studio_url`：可由 CLI 显式覆盖（自托管 LangSmith 时用）；
- `_get_ls_origin()`（E1 `:31-38`）：**仅在 `tracing_is_enabled()` 为真时**返回 `Client()._host_url`，即必须已配置 LangSmith key 且开启 tracing；
- 兜底：`https://smith.langchain.com`。

> **因此有两条重要事实**：
> ① **Studio 的前端在云端**，本地 server 只是它回连的后端 → 「本地调试也要过云」是结构性事实，不是配置问题；
> ② 若 `_get_ls_origin()` 生效，Studio 会指向**你的 LangSmith 主机**（自托管场景即自托管 UI）——但**自托管 LangSmith 平台属 Enterprise 档**（Q2 §3.6），且该平台仍需 license key + beacon 出网。

官方文档口径一致（E9）：「The LangGraph CLI provides a local development server (also called **Agent Server**) that **connects your agent to Studio**」；且前置条件列出「**A LangSmith account**」「**A LangSmith API key**」。

### 3.2 Studio 的可视化代码在哪个包里？—— 开源边界实测

| 层 | 组件 | 归属 | 证据 |
|---|---|---|---|
| 图运行时 | `StateGraph` / `add_node` / `add_edge` / `compile` / Pregel 调度 | `langgraph` | E4/E5 |
| **图结构数据** | `Graph` / `Node` / `Edge` / `Branch` 数据类 | **`langchain_core/runnables/graph.py`** | E6 |
| **静态图渲染** | `draw_mermaid()`（纯本地文本）、`draw_mermaid_png()`（默认走公网 `mermaid.ink`） | **`langchain_core/runnables/graph_mermaid.py`** | E7 |
| **交互式 Studio 前端**（图视图、状态检查器、prompt 编辑、run 控制） | —— | **不在任何开源包内**；只存在于 LangSmith 云端（闭源） | E4（开源侧零 UI 资产）+ E1（URL 指向云）+ E9 |
| 本地 server 的「前端口子」 | `Mount("/ui", StaticFiles(...))`（可挂自定义 UI）＋ `langgraph_api/js/`（JS SDK 客户端） | `langgraph_api`（**Elastic-2.0**） | E2/E3 |
| 本地 server 的数据出口 | `/assistants`、`/assistants/{id}/graph`、`/threads/{id}/runs/stream`（SSE）等 HTTP 端点 | `langgraph_api` | E8 |

**关键结论**：

> ① **`langgraph` 包内零前端资产**（E4）→ 「Studio 的可视化代码在 langgraph 包里」这一猜测**不成立**；
> ② OSS 侧确实存在可视化能力，但它的代码归属是 **`langchain-core`**（图数据类 + mermaid 渲染），且**只覆盖「静态图」**（mermaid 文本 / PNG），**不覆盖任何交互**；
> ③ **交互部分 100% 在云端**：Studio 前端通过 `baseUrl` 回连本地 server 的 HTTP API（E8）取图结构与运行数据，**在浏览器里自己渲染**；
> ④ 反过来看，**官方留了「服务端出 API + 前端自备」的口子**（E2 的 `/ui` 静态挂载）→ 这正是 freegraph 想走的架构，**官方自己也承认这条路径可行**。

### 3.3 一个此前未被纳入评估的 OSS：Agent Chat UI（MIT）

Q6 的 OSS 选型表评估的是 **trace/observability 后端**（Langfuse / Phoenix / OpenLIT / Grafana），**没有评估「本地 UI」**。本轮补上：

| 项 | 事实 | 证据 |
|---|---|---|
| 是什么 | Next.js 应用：与任何「有 `messages` 键」的 LangGraph server 对话；chat 界面 + tool 可视化 + artifacts 侧栏 | E13 README；E10 |
| 差异化能力 | 官方文档称其支持「**time-travel debugging and state forking**」 | E10 `:7` |
| 许可 | **MIT License, Copyright (c) 2025 Brace Sproul** | E12 |
| 本地运行 | `npx create-agent-chat-app` / `git clone` + `pnpm install && pnpm dev` → `http://localhost:3000`；亦有托管版 `agentchat.vercel.app` | E13；E10 `:27-47` |
| **是否需要账号** | 「LangSmith API Key: (**only required for connecting to deployed** LangGraph servers)」→ **连本地 server 不需要**；`NEXT_PUBLIC_AUTH_SCHEME=` 留空 | E13 |
| 连接方式 | `NEXT_PUBLIC_API_URL=http://localhost:2024` + `NEXT_PUBLIC_ASSISTANT_ID=<graph 名>` | E13 |
| **缺什么** | **没有 Studio 的图视图**（交互式 node/edge IDE）——它是 chat-first 界面 | E13（README 无图视图描述） |
| 生产化路径 | 提供 API Passthrough 代理方案（把 LangSmith key 放在服务端） | E13 |

> **对本项目的意义**：Q6 §3.2 的结论「**没有任何一个现成 OSS 提供 LangSmith Studio 那种图运行时 IDE**」需要**精化**（不是推翻）：
> - **仍成立**：没有 OSS 提供 **交互式图视图**（node/edge 可交互 IDE）——这仍是 freegraph 的独占位置；
> - **需修正**：chat / tool 渲染 / **time-travel** / **state forking** 这些 Studio 能力，**已有 MIT 现成实现**，且**本地可跑、不需要账号** → 它们不是「必须自研」，而是「可借鉴」（采用须保留 MIT 声明 → `THIRD_PARTY_NOTICES`）。

### 3.4 对 freegraph 的可执行结论（5 条）

1. **Q6 的独占性判断精化**：freegraph 的独占位置 = **交互式图视图 + 回放入口**；chat/tool/time-travel 可借鉴 Agent Chat UI（MIT）的架构与交互模式。
2. **v1 不必引入前端技术栈**（会显著改变 §7 的成本模型）：三件套可「**能力层优先**」交付 ——
   - 图视图 → `draw_mermaid()`（B7-1，纯本地零出站）；
   - trace 时间线/详情 → 本地 trace 存储 + 查询 API（B6-3）；
   - 状态快照 + checkpoint 历史 + 回放入口 → `get_state_history()` + `update_state()`（B5-2 / B5-3）。
   UI 若要，只做**只读轻量查看器**（单文件 HTML + 读本地 JSON/SQLite），**不引入 Node 构建链**。
3. **若 v2 做完整 UI**，可直接借鉴 MIT 的 Agent Chat UI：chat + tool 渲染 + time-travel + state forking 的交互范式已经跑通，**freegraph 只需把「图视图」这一块补上**（这恰是官方没有的部分）。
4. **协议层先行的顺序**：freegraph 的内核先出**契约层**（P01–P02）→ 再出数据/API（B6/B5）→ 最后才是 UI 子包。这与官方「server 出 API、frontend 自备」的结构一致。
5. **法律边界不变**：Agent Chat UI 是 MIT（可借鉴、须保留声明）；`langgraph_api` 是 **Elastic-2.0**（**绝不能引入或复制**，含其 `/ui` 挂载实现与 JS SDK）→ freegraph 若做本地 UI，必须**依据公开 HTTP/SSE 协议独立实现**，不能抄 `langgraph_api` 的代码。

---

## 4. 表格

### 4.1 Studio 能力 × 代码归属（Q9 结论汇总）

| Studio / 本地调试能力 | 代码归属 | 开源？ | 对 freegraph 的含义 |
|---|---|---|---|
| 图运行（state/node/edge/调度） | `langgraph` | ✅ MIT | 复刻（内核） |
| 图结构数据类（`Graph`/`Node`/`Edge`） | `langchain-core` | ✅ MIT | **独立重写**（不得依赖，见原则 II） |
| 静态图（mermaid 文本） | `langchain-core` | ✅ MIT | 复刻（纯本地、零出站） |
| 静态图 PNG | `langchain-core` | ✅ MIT 但**依赖公网 `mermaid.ink`** | **必须做成默认关闭的可选插件**（原则 I） |
| 本地 Agent Server（HTTP API + SSE） | `langgraph-api` | ❌ **Elastic-2.0** | **不可引入**；如需只能依公开 OpenAPI 规范自研 |
| 自定义 UI 静态挂载（`/ui`） | `langgraph-api` | ❌ Elastic-2.0 | 同上 |
| 前端 JS SDK 客户端 | `langgraph_api/js/`（+ npm `@langchain/langgraph-sdk`） | ✅（JS SDK 部分） | 可借鉴协议用法 |
| chat / tool 渲染 / time-travel / state forking | **Agent Chat UI** | ✅ **MIT** | **可借鉴**（须保留声明） |
| **交互式图视图（node/edge IDE）+ 状态检查器 + prompt 编辑 + run 控制** | **LangSmith 云端** | ❌ 闭源 | **freegraph 独占位置，必须自研** |

### 4.2 Q6 结论的精化对照

| Q6 原结论（2026-11-01） | Q9 精化（2026-11-03） | 性质 |
|---|---|---|
| 「没有任何一个现成 OSS 提供『LangSmith Studio 那种图运行时 IDE』」 | 「**没有 OSS 提供交互式图视图（node/edge IDE）**；但 OSS 侧存在 MIT 的 **Agent Chat UI**，覆盖 chat / tool 渲染 / **time-travel** / **state forking**，且本地可跑、**不需要账号**」 | **精化**（不推翻独占性判断） |
| 路线 B v1 可视化三件套 = 图视图 + trace 时间线 + 状态快照/回放 | 保持不变，但**实现路径可降级为「能力层优先」**：mermaid + 查询 API + 回放 API，UI 子包可延后 | **实施顺序调整** |
| 路线 B 工作量 62–101 人日 | **待按 Q9 结论复核**：B3「内嵌 Web UI（15–25 人日）」在「只做只读查看器」口径下可显著下降；**具体数值须在 Q9 结论落入 P22–P25 的 spec 时重估**，本报告不臆造新数字 | **标注待复核** |

---

## 5. 对 freegraph 的直接指引（可执行）

1. **修订立项书 §4.6 / §12-D2 / §12-D5**：把「Studio UI 是否进 v1」从「无依据的偏好之争」变成「有实测依据的取舍」——v1 只做能力层 + 只读查看器；完整交互式图视图留 v2 并作为独占卖点。
2. **修订 Q6 §3.2 关键结论 1 与 §4.1 选型表**：加入 Agent Chat UI 一行（MIT / 本地可跑 / 无需账号 / 无图视图），并把「必须自研」的标注限定到「图视图」单项。
3. **修订 Q3 §3.1 包级清单**：`langgraph` 包**零前端资产**、`langchain-core` 承载图数据类与 mermaid 渲染、`langgraph-api` 承载 Agent Server 与 `/ui` 挂载（Elastic-2.0）——三者边界需在包级表里写清。
4. **给 freechain 的提示**：freechain 若要做「应用层 UI」，Agent Chat UI 是可直接参考的 MIT 参照物。
5. **红线复述**：`langgraph-api` / `langgraph_api/js` **ELv2，禁止复制**；Agent Chat UI MIT 可借鉴但须进 `THIRD_PARTY_NOTICES`。

---

## 6. 自检清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 每个事实性结论带来源标记 | ✅ | 全部结论均指向 E1–E13（源码 `文件:行号` / 本地文档路径 / 官方仓库原文） |
| 未使用未核实的数字 | ✅ | 本报告不含人日/价格估算；路线 B 工作量一栏明确标「待复核」 |
| 闭源部分不做推测 | ✅ | Studio 前端按「双证据判定」（开源侧零 UI 资产 + URL 指向云）定性，不推测实现 |
| 自造术语未混入 | ✅ | 使用官方术语（Agent Server / Studio / Agent Chat UI）；「交互式图运行时 IDE」标注为发起者表述 |
| 未修改 `harness/docs` / `harness/demo/target.py` / 源码 | ✅ | 全程只读；实测在 `/tmp/opencode/lgsrv/` 的既有解包目录 |
| 结论可执行 | ✅ | §5 的 5 条均为可落地的文档修订与实施顺序调整 |
| 溯源到既有报告 | ✅ | 与 Q3（包级边界）、Q6（可视化路线）、Q7（许可证）交叉引用；本报告不推翻原结论，只做精化 |
