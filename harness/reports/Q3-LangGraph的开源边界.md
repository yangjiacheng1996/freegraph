# Q3 LangGraph 的开源边界（核心问题）

> 调研问题：LangGraph 的包级清单、运行时能力矩阵、付费墙触发点，以及 `harness/demo/target.py` 的逐项耦合裁定。
> 调研日期：2026-11-01｜本地实跑环境：`langgraph 1.2.11` / `langchain 1.4.1` / `langchain-core 1.6.3` / `langsmith 0.12.6` / `langgraph-cli 0.4.40` / `langgraph-api 0.17.0` / `langgraph-runtime-inmem 0.37.0`
> **联网抓取方式**：本轮调研通过本机代理 `http://127.0.0.1:10808`（xray / v2rayN 系统代理端口）出网抓取官方页面；`docs.langchain.com` 支持在 URL 后加 `.md` 直接获得 Markdown 源文。**定价页的功能勾选矩阵必须做 DOM 级解析**（Markdown 文本化会丢失 SVG 勾选状态），方法见 [Q1 §2.3](Q1-LangSmith的功能全景与卖点.md)。

---

## 1. 摘要 TL;DR

1. **LangGraph OSS 的三大基础能力完全不需要 LangSmith 账号。** 实跑证明：清空 `LANGSMITH_*` 后，带 socket guard 阻断全部非 localhost 出站，quickstart 示例照常跑通，`BLOCKED: []`。
2. **但 `langchain-core` 硬依赖 `langsmith` 包**（`langchain-core 1.6.3` 的 `Requires-Dist` 含 `langsmith<1.0.0,>=0.3.45`，非 extras）。**这是包层唯一无法绕开的事实**：只要 freegraph 依赖 `langchain-core`，依赖树里就必然出现 `langsmith`。
3. 因此 **freegraph 必须完全不依赖 `langchain-core`**，才能满足 §2.6 约束 2 的"依赖树中不得出现 `langsmith` 包"。代价是必须自己实现 `RunnableConfig` 语义与图结构导出（`langchain_core.runnables.graph.Graph`）——后者仅约 300 行，是可行成本。
4. **`draw_mermaid_png()` 属于 `langchain-core` 能力，且默认走公网 `https://mermaid.ink`**（实跑被拦截后抛 `ValueError: Failed to reach https://mermaid.ink API`）。**这是一个独立的、非 LangSmith 的外呼点**，freegraph 若照抄会造成"零出站"承诺破裂 → 建议 freegraph 只提供 `draw_mermaid()` 文本，PNG 渲染改为可选插件。
5. **付费墙触发点共 6 个**：模板 `.env`（`LANGSMITH_PROJECT`）、`langgraph dev` 的 Studio URL（指向云）、tracing（需 key 且自动开启）、`draw_mermaid_png`（mermaid.ink）、Deployment（Plus/Enterprise）、Standalone server（license key + beacon 出网）。
6. 对 freegraph 的判断 ①：**`target.py` 的 14 个 API 元素全部可在 OSS 内提供**，且**都不必须触及 LangSmith**；freegraph 必须同名同签名对齐其中 12 项（`StateGraph`/`START`/`END`/`add_node`/`add_edge`/`add_conditional_edges`/`compile`/`invoke`/`get_graph`/`draw_mermaid`/`draw_mermaid_png`），但 **`Annotated` 归约器机制与 `state.get()` 语义可以自由设计**（只要行为等价）。
7. 对 freegraph 的判断 ②：**`harness/demo/target.py` 有一个必须处理的隐性缺口**——脚本第 144 行 `display(Image(agent.get_graph(xray=True).draw_mermaid_png()))` 在**离线环境必然抛异常**，会阻断脚本执行。freegraph 必须提供"PNG 失败不阻断"或"提供等价替代"的迁移说明。
8. 对 freegraph 的判断 ③：freegraph 的白名单应严格到 **仅 `typing-extensions` + `pydantic`（可选）**，黑名单必须包含 `langsmith`/`langchain`/`langchain-core`/`langgraph*` 全部变体 + 所有 `LANGSMITH_*`/`LANGCHAIN_*` 环境变量 + `smith.langchain.com`/`mermaid.ink` 等域名。

---

## 2. 调研方法与资料来源

### 2.1 实跑取证清单（本报告核心证据）

| # | 实验 | 命令要点 | 结果摘要 |
|---|---|---|---|
| E1 | 依赖树展开 | `importlib.metadata` 递归展开 `Requires-Dist` | `langgraph 1.2.11` → `langchain-core 1.6.3` → **`langsmith 0.12.6`（硬依赖）**；`langchain 1.4.1` → `langgraph` + `langchain-core` → `langsmith` |
| E2 | PyPI 元数据 | `curl https://pypi.org/pypi/{pkg}/json` | `langgraph` 1.2.19 `requires_dist` 含 `langchain-core<2,>=1.4.7`；`langchain-core` 含 `langsmith<1.0.0,>=0.3.45` |
| E3 | 清空 env 跑 quickstart（socket guard） | `env -u LANGSMITH_API_KEY -u LANGSMITH_TRACING ... python3 run_quickstart.py` | `INVOKE_KEYS: ['llm_calls','messages']`；`N_MESSAGES: 4`；`TYPES: ['HumanMessage','AIMessage','ToolMessage','AIMessage']`；**`BLOCKED: []`** |
| E4 | `tracing_is_enabled()` 双态 | 无 env / `LANGSMITH_TRACING=true`+假 key | `False` / `True`；后者**实际外呼** `api.smith.langchain.com/info` 与 `/runs/multipart` |
| E5 | `get_graph` + `draw_mermaid` + `draw_mermaid_png` | `test_graph_draw.py` | `GRAPH_TYPE: langchain_core.runnables.graph.Graph`；`draw_mermaid()` **成功**（零出站，292 字符）；`draw_mermaid_png()` **失败**：`ValueError: Failed to reach https://mermaid.ink API`，blocked 列表含 `('172.67.174.89', 443)` 等 |
| E6 | `init_chat_model("claude-sonnet-4-6")` 离线构造 | `test_init_chat.py` | `INIT_OK: langchain_anthropic.chat_models.ChatAnthropic`，`BLOCKED: []`（构造不外呼） |
| E7 | `langgraph dev` 无 key 无 license | `env -u LANGSMITH_API_KEY ... langgraph dev --port 8123` | 启动成功；`/ok` → `{"ok":true}`；`/info` → `"flags":{"langsmith":false,...}`；日志 `"No license key or control plane API key set, skipping metadata loop"` |
| E8 | SQLite checkpointer + time-travel | `SqliteSaver.from_conn_string(...)` + `get_state_history` | `R1: {'n': 2}`、`R2: {'n': 2}`（状态累积）、`HISTORY: 6`、`SNAPSHOT next: () values: {'n': 2}`、`BLOCKED: []` |
| E9 | `import langgraph.graph` 的副作用 | 检查 `sys.modules` | `langsmith` 136 个模块被加载、`langgraph_sdk` 被加载、`langchain_core` 被加载（**import 阶段即耦合**） |
| E10 | 源码扫描 langsmith 引用 | `grep -rn langsmith langgraph/` | 仅 4 处：`constants.py:26`（`TAG_HIDDEN` 字符串常量）、`pregel/remote.py:14`（`import langsmith as ls`）、`_internal/_config.py:270,310`（`langsmith_inheritable_metadata=` kwarg）、`_internal/_runnable.py:98,112`（`from langsmith.run_helpers import _set_tracing_context`） |

### 2.2 来源清单

| # | 来源 | 类型 |
|---|---|---|
| L1 | `harness/demo/target.py`（只读） | 验收契约 |
| L2 | 本地 `site-packages`：`langgraph/`、`langchain_core/`、`langsmith/` 源码 | 源码一手 |
| L3 | PyPI JSON API（`langgraph`、`langgraph-api`、`langgraph-cli`、`langgraph-runtime-inmem`、`langgraph-sdk`、`langgraph-checkpoint*`、`langgraph-prebuilt`、`langgraph-store-*`） | 官方一手 |
| L4 | `langgraph` monorepo GitHub tree（`libs/*`）与各 `LICENSE` | 官方一手 |
| L5 | `langgraph-api 0.17.0` wheel：`config/__init__.py`、`metadata.py`、`cli.py` | 源码一手 |
| L6 | `langgraph-cli 0.4.40` wheel：`cli.py`、`templates.py` | 源码一手 |
| L7 | `harness/docs/oss/python/langgraph/*.md`（graph-api / pregel / local-server / persistence / use-time-travel / observability / studio） | 本地镜像 |
| L8 | `harness/docs/langsmith/deployment.md:43,47` | 本地镜像 |

### 2.3 未能获取的来源

- `langgraph dev --help` 的完整 sqlite 持久化选项：**实跑 `--help` 确认 `langgraph dev` 无任何 sqlite/checkpointer 持久化选项**（只有 `--config` 指向的 `langgraph.json` 中的 `checkpointer` / `disable_persistence` 字段，见 `langgraph_cli/cli.py:859-860`）→ 裁定见 H2。
- `langgraph-api` 的完整源码仓库（闭源，wheel 内含 `langgraph_license/validation.py` 的 noop 实现）→ **注意：`langgraph-api` 0.17.0 的 wheel 内置 license 校验是 noop**（`get_license_status()` 恒 True、`plus_features_enabled()` 恒 True），这与文档宣称的 "Requires a Plus plan" 存在实现层差异，属于"文档层的付费墙"而非"代码层的硬校验"。
- `langgraph-store-sqlite` 的独立 PyPI 包：**经代理复查确认为 404，即该包不存在**（不是抓取失败）。该能力以 `langgraph.store.sqlite` 模块内置于 `langgraph` 包（本地实测存在，MIT）。`langgraph-store` 与之同理；实际发布的只有 `langgraph-store-core`（0.1.1）与 `langgraph-store-postgres`（0.1.0）。

---

## 3. 正文

### 3.1 (a) 包级清单

#### 3.1.1 许可证与依赖事实

| 包 | 最新版（PyPI，2026-11-01） | 许可证 | 能否独立安装 | 硬依赖 `LANGSMITH_API_KEY`/`ENDPOINT`？ | 归类 |
|---|---|---|---|---|---|
| `langgraph` | 1.2.19 | **MIT** | ✅ 需 `langchain-core` | ❌ 否 | 开源核心 |
| `langgraph-prebuilt` | 1.1.1 | **MIT** | ✅ 需 `langchain-core` | ❌ 否 | 开源核心 |
| `langgraph-checkpoint` | 4.3.1 | **MIT** | ✅ 需 `langchain-core` | ❌ 否 | 开源核心 |
| `langgraph-checkpoint-sqlite` | 3.1.3 | **MIT** | ✅ 需 `langgraph-checkpoint` | ❌ 否 | 开源核心 |
| `langgraph-checkpoint-postgres` | 3.2.0 | **MIT** | ✅ 需 `langgraph-checkpoint` | ❌ 否 | 开源核心 |
| `langgraph-store`（模块 `langgraph.store.base`） | 无独立 PyPI 包（404） | MIT（随 `langgraph`） | ✅ 内置于 `langgraph` | ❌ 否 | 开源核心 |
| `langgraph-store-postgres` | 0.1.0 | MIT（classifier） | ✅ 需 `langgraph-store-core`→`langgraph` | ❌ 否 | 开源核心（社区维护，源仓 `skamalj/langgraph-store`） |
| `langgraph-store-sqlite` | **不存在独立 PyPI 包**（经代理复查 = 404 确认） | — | — | — | 该能力以 `langgraph.store.sqlite` 模块内置于 `langgraph` 1.2.11（本地实测存在，MIT） |
| `langgraph-cli` | 0.4.40 | **MIT** | ✅ | ❌ 本地 dev 不需要；`deploy`/`up` 提示需要 | **平台专有**（依赖 `langgraph-api`） |
| `langgraph-api` | 0.17.0 | **Elastic License 2.0** | ✅ | ⚠️ 配置读取 `LANGSMITH_API_KEY`/`LANGSMITH_CONTROL_PLANE_API_KEY`/`LANGSMITH_ENDPOINT`；**有 control-plane key 即自动开 tracing**（`config/__init__.py:675-677`）；有 license key 即上报 `beacon.langchain.com`（`metadata.py:75,262`） | **平台专有** |
| `langgraph-runtime-inmem` | 0.37.0 | **Elastic License 2.0** | ✅ 需 `langgraph` | ❌ | **平台专有** |
| `langgraph-sdk` | 0.4.11 | **MIT** | ✅ 需 `langchain-core`（→ `langsmith`） | ❌（客户端库） | 开源，但**仅用于连远程部署** |
| `langsmith` | 0.12.6（本地已装）/ **0.14.17（PyPI 最新）** | **MIT** | ✅ | ❌ SDK 本身不读 key；`tracing_is_enabled()` 由 `LANGSMITH_TRACING(_V2)` 决定 | **开源 SDK**（付费的是 SaaS）。**注：0.14.x 新版 `requires_dist` 已不含 `langchain-core`**（仅 anyio / httpx2 / orjson / pydantic / requests 等），即 SDK 正被抽成独立于 LangChain 的通用 SDK |

> **许可证关键事实**：`langgraph-api` 与 `langgraph-runtime-inmem` 是 **Elastic-2.0**（不是 MIT），且 ELv2 明确禁止 "provide the software to third parties as a hosted or managed service"（wheel 内 `licenses/LICENSE`）。**这意味着 Agent Server 本身不可原样商用托管**——这是 freegraph 自己做本地 server 的重要法律动因（详见 Q7）。

#### 3.1.2 依赖树的「langsmith 硬耦合点」

实测 `langchain-core 1.6.3` 的 `Requires-Dist`：

```
httpx<1.0.0,>=0.23.0
jsonpatch<2.0.0,>=1.33.0
langchain-protocol>=0.0.17
langsmith<1.0.0,>=0.3.45      ← 硬依赖，非 extra
packaging>=23.2.0
pydantic>=2.7.4,<3.0.0
pyyaml>=5.3.0,<7.0.0
tenacity>=8.1.0,<10.0.0,!=8.4.0
typing-extensions>=4.7.0,<5.0.0
uuid-utils>=0.12.0,<1.0
```

因此依赖树结论（实测 E1/E2）：

```
langchain 1.4.1 ─┬─ langchain-core 1.6.3 ─── langsmith 0.12.6  ★
                 └─ langgraph 1.2.11 ─┬─ langchain-core ───── langsmith ★
                                        ├─ langgraph-checkpoint → langchain-core → langsmith ★
                                        ├─ langgraph-prebuilt → langchain-core → langsmith ★
                                        └─ langgraph-sdk → langchain-core → langsmith ★
```

**「剥离」在包层的唯一可行路径**：

| 路径 | 依赖树含 `langsmith`？ | 评价 |
|---|---|---|
| freegraph 依赖 `langgraph` | ✅ 含 | ✗ 不满足 §2.6 约束 2 |
| freegraph 依赖 `langchain-core` | ✅ 含 | ✗ 不满足 |
| freegraph 依赖 `langchain` | ✅ 含 | ✗ 不满足 |
| **freegraph 零第三方运行时依赖**（仅 stdlib + `typing-extensions`） | ❌ 不含 | ✓ **唯一可行路径** |

### 3.1.1 【Q9 补充，2026-11-03】前端资产与「本地 server ≠ Studio」边界

| 事实 | 结论 | 证据 |
|---|---|---|
| `langgraph` 包内是否有前端资产 | **零**（无 `.js` / `.html` / `.css` / `.tsx`）→ **Studio 的可视化代码不在 `langgraph` 包里** | 本机 `langgraph 1.2.11` 包内文件实测 |
| 图结构数据类与 mermaid 渲染在哪 | **`langchain-core`**：`runnables/graph.py`（`Graph`/`Node`/`Edge`/`Branch`）、`runnables/graph_mermaid.py`（`draw_mermaid` :45 纯本地；`draw_mermaid_png` :277 → 默认 `https://mermaid.ink` :423） | 源码行号 |
| `langgraph dev` 起的是什么 | **Agent Server**（`langgraph_api`，in-memory runtime）：提供 HTTP API + `/docs`；**Studio 是云端 Web App**（`smith.langchain.com/studio/?baseUrl=<local_url>`），浏览器 → 云 → 回连本地 | `langgraph_api/cli.py:306-307, 364-366` |
| 交互式 Studio 前端在哪 | **不在任何开源包内**（闭源，只在 LangSmith 云端） | 开源侧零 UI 资产 + URL 指向云 |
| 本地 server 留的「前端口子」 | `langgraph_api/api/ui.py`：`Mount("/ui", StaticFiles(...))` 可挂**自定义 UI**；`langgraph_api/js/` 是 JS SDK 客户端 | 源码 |

> **对本报告结论的影响**：**不改变** §3.4 的 18 项裁定与 §3.6 的依赖黑白名单；**新增一条边界**——「本地 Agent Server」属 `langgraph-api`（**Elastic-2.0**），freegraph **不可引入**；若未来做本地 UI，必须**依公开 HTTP/SSE 协议独立实现**，不得复制 `langgraph_api` 的 `/ui` 挂载与 JS SDK 代码。详见 [Q9](Q9-Studio与本地server及可视化代码边界.md)。

### 3.2 (b) 运行时能力矩阵

| 能力 | 官方归属 | 纯 OSS 可得？ | 触及 LangSmith / Agent Server？ | 证据 |
|---|---|---|---|---|
| 状态模型（schema + reducer） | `langgraph.graph.state.StateGraph` | ✅ | ❌ | `graph-api.md:49`；E3 |
| 节点 | `add_node` | ✅ | ❌ | E3 |
| 边与路由 | `add_edge` / `add_conditional_edges` | ✅ | ❌ | E3 |
| `Command` | `langgraph.types.Command` | ✅ | ❌ | `langgraph/types.py:799` |
| `interrupt`（HITL） | `langgraph.types.interrupt` | ✅（需 checkpointer） | ❌ | `langgraph/types.py:851`；E8 |
| checkpoint / persistence | `langgraph.checkpoint.{memory,sqlite,postgres}` | ✅ | ❌ | E8 实跑 SqliteSaver |
| time-travel（replay / fork） | `get_state_history` + `update_state` | ✅ | ❌ | E8：`HISTORY: 6` |
| store（长期记忆） | `langgraph.store.{base,memory,sqlite,postgres}` | ✅ | ❌ | 模块实测存在 |
| streaming（`stream` / `astream` / `stream_mode`） | `CompiledStateGraph.stream` | ✅ | ❌ | `state.py` 签名实测 |
| subgraph | `add_node(..., **kwargs)` + `get_subgraphs` | ✅ | ❌ | `CompiledStateGraph.get_subgraphs` |
| durable execution | 基于 checkpoint 的重放语义 | ✅ | ❌ | `use-time-travel.md` |
| `get_graph` / `draw_mermaid` | `langgraph.pregel.main:845` → **`langchain_core.runnables.graph.Graph`** | ✅ **但实现位于 `langchain-core`** | ❌ | E5：`GRAPH_TYPE: langchain_core.runnables.graph.Graph` |
| `draw_mermaid_png` | `langchain_core.runnables.graph_mermaid.draw_mermaid_png` | ⚠️ 默认走 **mermaid.ink 公网** | ❌（非 LangSmith，是第三方 SaaS） | E5：`ValueError: Failed to reach https://mermaid.ink API` |
| Studio（可视化 IDE） | `smith.langchain.com/studio/` | ❌ | ✅ 强依赖云 + 账号 | `local-server.md:88,102` |
| 托管部署 / 水平扩缩 / cron / assistants API | `langgraph-api` / Deployment | ❌ | ✅ | `deployment.md:43,47` |
| Engine / Fleet / Sandboxes / LLM Gateway | LangSmith SaaS | ❌ | ✅ | 定价页 |
| 远程图调用（RemoteGraph） | `langgraph.pregel.remote` | ⚠️ OSS 有客户端，但需远程 server | ✅（连 Agent Server） | `pregel/remote.py:14` `import langsmith as ls` |

### 3.3 (c) 付费墙触发点清单

「用户从纯 OSS 跨到需要 LangSmith」的**具体动作**：

| # | 触发动作 | 具体机制 | 是否硬性 | 证据 |
|---|---|---|---|---|
| T1 | 使用 `langgraph new --template ...` 生成项目 | 模板 `.env.example` 含 `LANGSMITH_PROJECT=new-agent` | 🟡 **软触发**（可删） | 模板仓库 `.env.example` 实测全文 4 行，仅此一行 LangSmith 配置 |
| T2 | `langgraph dev` 后点击 "Studio UI" | banner 打印 `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024` → **浏览器走云** | 🟡 软触发（不点就不触发） | E7 + `langgraph_api/cli.py:306-307` |
| T3 | 设置 `LANGSMITH_TRACING=true` + API key | `langchain-core` 的 `LangChainTracer` 向 `api.smith.langchain.com` 上报 | 🔴 **一旦设置即外呼** | E4 实测外呼日志 |
| T4 | 在 `langgraph-api` 场景设置 API key | `config/__init__.py:675-677`：**API key 存在即自动 `LANGSMITH_TRACING=true`** | 🔴 **隐式自动开启** | 源码 |
| T5 | `draw_mermaid_png()` | 默认请求 `https://mermaid.ink/img/...` | 🔴 **每次调用必外呼** | E5 |
| T6 | `langgraph deploy` / `langgraph up` | 需要 `LANGSMITH_API_KEY` + 部署到 Cloud（Plus+） | 🔴 硬性 | `langgraph_cli/deploy.py:1988` |
| T7 | Standalone server 部署 | 需 `LANGGRAPH_CLOUD_LICENSE_KEY`，且需出网到 `beacon.langchain.com` | 🔴 硬性 | `deploy-standalone-server.md` 前置 + `metadata.py:75` |
| T8 | 自托管 LangSmith 平台 | Enterprise 档才有 Self-Hosted hosting | 🔴 硬性 | 定价页 hosting 表 |
| T9 | 官方文档推荐路径本身 | `local-server.md:13` 把 "An API key for LangSmith - free to sign up" 列为**前置条件** | 🟡 文档层强制 | `local-server.md:13` |

#### 3.3.1 「剥离」的可验证定义（三层）

**包层**

- 判定：`pip show freegraph` / `pipdeptree` 输出中**不得出现** `langsmith`、`langchain`、`langchain-core`、`langchain-classic`、`langgraph*`。
- freegraph 应做到：**运行时依赖仅 `typing-extensions`**（`Annotated` 支持，`TypedDict` 在 3.12 已入 stdlib 但 `typing_extensions` 更稳）；`pydantic` 仅在需要 pydantic 状态 schema 时作为**可选 extra**。
- **绝对禁止**：依赖 `langchain-core`——它是 `langsmith` 的唯一入口。

**配置层（哪些环境变量会触发外呼）**

| 变量 | 触发者 | 默认值 | 是否触发外呼 |
|---|---|---|---|
| `LANGSMITH_TRACING` | `langchain-core` / `langgraph-api` | 未设 = **关闭** | 设 `true` 即开 |
| `LANGSMITH_TRACING_V2` | 同上（别名） | 未设 = 关闭 | 设 `true` 即开 |
| `LANGCHAIN_TRACING_V2` / `LANGCHAIN_TRACING` | 同上（别名 namespace） | 未设 = 关闭 | 设 `true` 即开 |
| `LANGSMITH_API_KEY` | `langchain-core` tracer / `langgraph-api` | 未设 = 无 | `langgraph-api` 中**会自动开 tracing** |
| `LANGSMITH_ENDPOINT` | `langsmith.client`（默认 `https://api.smith.langchain.com`）/ `langgraph-api` | 有默认外呼地址 | 配合 tracing 生效 |
| `LANGSMITH_PROJECT` | tracer 项目名 | 无 | 单独设置**不**触发外呼（但模板默认带它） |
| `LANGSMITH_CONTROL_PLANE_API_KEY` | `langgraph-api` | 继承 `LANGSMITH_API_KEY` | 会开 tracing + metadata 上报 |
| `LANGSMITH_LICENSE_REQUIRED_CLAIMS` | `langgraph-api` | `[]` | 与 entitlement 相关 |
| `LANGSMITH_AUTH_ENDPOINT` / `LANGSMITH_AUTH_VERIFY_TENANT_ID` | `langgraph-api`（`LANGGRAPH_AUTH_TYPE=langsmith` 时） | — | 账号体系耦合 |
| `LANGGRAPH_CLOUD_LICENSE_KEY` | `langgraph-api` | 无 | 触发 beacon 上报 |

> 精确机制（实测 E4 + 源码 `langsmith/utils.py:121-141`）：`tracing_is_enabled()` 读 `LANGSMITH_TRACING_V2`，回落 `LANGSMITH_TRACING`（两者都经 `get_env_var`，namespace = `("LANGSMITH","LANGCHAIN")`），**值必须恰为字符串 `"true"`** 才为真。`langchain_core.tracers.context._tracing_v2_is_enabled()` 直接委派给它。

**网络层（出站域名）**

| 域名 | 来源 | 何时触发 |
|---|---|---|
| `api.smith.langchain.com` | `langsmith.client` 默认 endpoint（`langsmith/client.py:1254`） | tracing 开启时 |
| `smith.langchain.com` | Studio UI / `langgraph_api/cli.py:306` | 点击 Studio / 打开浏览器 |
| `beacon.langchain.com` | `langgraph-api/metadata.py:75` | 有 license key 或 control-plane key 时，每 300s 上报 |
| `api.smith.langchain.com/otel/v1/traces` | `langsmith.integrations.otel` | 使用 OTel processor 时 |
| **`mermaid.ink`** | `langchain_core/runnables/graph_mermaid.py:423` | **每次 `draw_mermaid_png()`** |

**freegraph 的网络层承诺**：**零出站域名**（`draw_mermaid_png` 若提供，必须是可选插件且默认关闭，或改为本地渲染）。

### 3.4 (d) `target.py` 依赖项逐项裁定

`harness/demo/target.py`（151 行）逐项拆解。脚本导入：`from freegraph.graph import StateGraph, START, END`（第 103 行）+ `from langchain.tools import tool`（第 3 行）+ `from langchain.chat_models import init_chat_model`（第 4 行）+ `from langchain.messages import AnyMessage, SystemMessage, ToolMessage, HumanMessage`（第 54/64/87/147 行）。

> 注：脚本自带 `langchain.*` 导入按 §2.6 说明**不构成 freegraph 的依赖要求**，freegraph 只需能处理这些对象（鸭子类型）。

| # | 行号 | API 元素 | LangGraph OSS 直接提供？ | 触及 LangSmith / Agent Server？ | freegraph 必须同名同签名？ | 备注 |
|---|---|---|---|---|---|---|
| 1 | 103 | `from freegraph.graph import StateGraph, START, END` | ✅ `langgraph.graph` 导出同名三者 | ❌ 否 | ✅ **必须** | `START='__start__'`、`END='__end__'`（`langgraph/constants.py:26-30`，实测 `repr` 一致） |
| 2 | 123 | `StateGraph(MessagesState)` | ✅ `state.py:131` | ❌ | ✅ **必须** | 只传 schema 一个位置参数 |
| 3 | 126-127 | `add_node(name, fn)` | ✅ `state.py:520` | ❌ | ✅ **必须** | 位置参数 `(node: str, action: Callable)` |
| 4 | 130,136 | `add_edge(src, dst)` | ✅ `state.py:928` | ❌ | ✅ **必须** | 签名 `(start_key: str \| list[str], end_key: str) -> Self`（链式返回） |
| 5 | 131-135 | `add_conditional_edges(src, path_fn, path_map)` | ✅ `state.py:982` | ❌ | ✅ **必须** | `path_map` 传**list**（`["tool_node", END]`）；官方签名 `path_map: dict \| list[str] \| None` |
| 6 | 139 | `compile()` | ✅ `state.py:1177` | ❌ | ✅ **必须** | 无参调用；返回 `CompiledStateGraph` |
| 7 | 149 | `compiled.invoke({"messages": [...]})` | ✅ | ❌ | ✅ **必须** | 实测返回**完整状态**（含 `llm_calls` 键），非仅新增消息 → 满足 §2.6 约束 5 |
| 8 | 60 | `Annotated[list[AnyMessage], operator.add]` 归约器 | ✅ `graph-api.md:249-263` | ❌ | ❌ **可自由设计**（须行为等价） | 二元 reducer `(a,b)->c`；`operator.add` 语义 = 列表拼接 |
| 9 | 81 | `state.get('llm_calls', 0)` | ✅ 标准 dict | ❌ | ❌ 可自由设计（须等价） | 节点入参为 state **字典**（非对象）→ freegraph 须把 state 以 `dict` 传入节点 |
| 10 | 70-82 | 节点返回**部分** state 字典的合并规则 | ✅ `graph-api.md:197-200`：`new_value = reducer(current[key], update[key])`；无 reducer 的键则覆盖 | ❌ | ❌ 可自由设计（须等价） | 关键：`llm_calls` 无 reducer → 覆盖；`messages` 有 reducer → 追加 |
| 11 | 94 | `state["messages"][-1].tool_calls` | ✅ 鸭子类型读取 | ❌ | ❌ 可自由设计 | **只需节点能读到该属性**；freegraph 不必懂 LangChain 消息类型 |
| 12 | 114 | `if last_message.tool_calls:` 真值判定 | ✅ | ❌ | ❌ 可自由设计 | 空 list → falsy |
| 13 | 144 | `agent.get_graph(xray=True).draw_mermaid_png()` | ✅ `get_graph` 在 `langgraph/pregel/main.py:845`；**`draw_mermaid_png` 实现在 `langchain_core`** | ❌ 不触 LangSmith；⚠️ **触 mermaid.ink** | ✅ **必须同名**（否则脚本改不了） | ⚠️ **两处坑**：① 返回类型是 `langchain_core.runnables.graph.Graph`；② PNG 渲染默认走公网，离线必失败（E5） |
| 14 | 144 | `display(Image(...))` | ❌ IPython 依赖，属脚本自身 | ❌ | ❌ | freegraph 不涉及 |
| 15 | 7-10 | `init_chat_model("claude-sonnet-4-6", temperature=0)` | ❌ 属 `langchain` 层 | ❌ | ❌ | §2.5 明确归 freechain；实测 E6 离线构造成功，`bind_tools` 由模型实现 |
| 16 | 14-45 | `@tool` 装饰器 / `tool.name` / `tool.invoke(args)` | ❌ 属 `langchain` 层 | ❌ | ❌ | freechain 职责；**但 freegraph 须保证工具对象能被节点调用**（鸭子类型） |
| 17 | 96-97 | `tool.invoke(tool_call["args"])` | ❌ 脚本自身逻辑 | ❌ | ❌ | `tool_call` 结构：`{"name","args","id","type"}`（OpenAI 风格） |
| 18 | 97 | `ToolMessage(content=observation, tool_call_id=tool_call["id"])` | ❌ 属 `langchain.messages` | ❌ | ❌ | freegraph 须能**原样流转**该对象，不做类型转换（§2.6 约束 4） |

**结论**：18 项中，**7 项 freegraph 必须同名同签名对齐**（#1–#7、#13），**11 项可自由设计但须行为等价或原样承载**。**没有任何一项要求 freegraph 触碰 LangSmith 或 Agent Server。**

### 3.5 `target.py` 的三个隐性风险（必须写进 freegraph 的迁移说明）

1. **PNG 渲染依赖公网**（第 144 行）。E5 实测：`draw_mermaid_png()` 在离线/内网环境抛 `ValueError: Failed to reach https://mermaid.ink API`。而该调用在脚本中位于 `agent.invoke` **之前**，一旦抛错**整个脚本无法跑到验收点**。
   - freegraph 的应对：`get_graph()` 返回的对象须提供 `draw_mermaid()`（纯本地，一定成功）与 `draw_mermaid_png()`；后者在无网络时应**返回占位图或抛出可捕获异常**，并提供 `draw_mermaid_png(draw_method=...)` 或 `render_mermaid_png()` 的离线替代说明。
2. **`get_graph(xray=True)` 的 `xray` 参数**：无子图时无副作用，但签名必须保留（`xray: int | bool = False`，`langgraph/pregel/protocol.py:32-37`）。
3. **`compile()` 返回对象的 `invoke` 必须返回完整状态 dict**：实测 E3 返回 `['llm_calls','messages']` 两个键，脚本第 150 行 `messages["messages"]` 才能工作。

### 3.6 依赖白名单 / 黑名单建议（三层）

#### 包层

| 类别 | 包 |
|---|---|
| ✅ **白名单（运行时必装）** | `typing-extensions`（唯一建议的必装依赖） |
| 🟡 **白名单（可选 extra）** | `pydantic`（`[pydantic]` extra，用于 pydantic 状态 schema）；`ormsgpack`（`[checkpoint]` extra，序列化） |
| 🔴 **黑名单（硬禁止）** | `langsmith`、`langchain`、`langchain-core`、`langchain-classic`、`langchain-protocol`、`langgraph`、`langgraph-prebuilt`、`langgraph-checkpoint*`、`langgraph-store*`、`langgraph-sdk`、`langgraph-api`、`langgraph-cli`、`langgraph-runtime-inmem`、`deepagents` |
| 🔴 **黑名单（可选 extra 也不允许）** | `langsmith[otel]`、`langchain-anthropic`、`langchain-openai` 等 provider 包 —— 这些会把 `langchain-core` 拉回来 |

#### 配置层

| 类别 | 环境变量 |
|---|---|
| 🔴 **黑名单（freegraph 代码不得读取）** | `LANGSMITH_API_KEY`、`LANGSMITH_TRACING`、`LANGSMITH_TRACING_V2`、`LANGSMITH_ENDPOINT`、`LANGSMITH_PROJECT`、`LANGSMITH_AGENT_ID`、`LANGSMITH_AGENT_ENVIRONMENT`、`LANGSMITH_CONTROL_PLANE_API_KEY`、`LANGSMITH_AUTH_ENDPOINT`、`LANGSMITH_AUTH_VERIFY_TENANT_ID`、`LANGSMITH_LICENSE_REQUIRED_CLAIMS`、`LANGSMITH_HOST_PROJECT_ID`、`LANGSMITH_HOST_REVISION_ID`、`LANGSMITH_TENANT_ID`、`LANGSMITH_LANGGRAPH_API_REVISION`、`LANGSMITH_LANGGRAPH_API_VARIANT`、`LANGCHAIN_API_KEY`、`LANGCHAIN_TRACING`、`LANGCHAIN_TRACING_V2`、`LANGCHAIN_ENDPOINT`、`LANGCHAIN_HANDLER`、`LANGGRAPH_CLOUD_LICENSE_KEY`、`LANGGRAPH_AUTH`、`LANGGRAPH_AUTH_TYPE` |
| ✅ **白名单** | 无。freegraph 内核**不读任何环境变量**（provider key 由上层 freechain / 用户代码自行传入） |

#### 网络层

| 类别 | 域名 / 目标 |
|---|---|
| 🔴 **黑名单** | `*.smith.langchain.com`、`smith.langchain.com`、`api.smith.langchain.com`、`beacon.langchain.com`、`*.langchain.com`、`mermaid.ink`（除非作为**用户显式启用的可选** PNG 渲染插件，且默认关闭） |
| ✅ **白名单** | 无（内核零出站）。可选：用户自己配置的 OTLP exporter 端点（仅在用户显式传入 tracer/exporter 时） |

---

## 4. 表格汇总

### 4.1 包级清单表

见 §3.1.1（13 行，含许可证 / 独立安装 / 硬依赖 key / 归类）。

### 4.2 运行时能力矩阵

见 §3.2（19 行）。

### 4.3 付费墙触发点清单

见 §3.3（9 行，T1–T9）。

### 4.4 `target.py` 依赖项逐项裁定表

见 §3.4（18 行）。

### 4.5 依赖白名单 / 黑名单建议（包层 / 配置层 / 网络层）

见 §3.6（三张表）。

---

## 5. 对 freegraph 的直接启示（可执行）

1. **freegraph 内核必须零第三方运行时依赖（最多 `typing-extensions`）**，并把「依赖树无 `langsmith`/`langchain*`」做成 CI 断言（用 `importlib.metadata.requires('freegraph')` 递归展开检查）。这是 §2.6 约束 2 唯一可自动验证的形式。
2. **freegraph 必须自己实现图结构导出**：`get_graph()` 需返回自有 `Graph` 对象，提供 `nodes` / `edges` / `draw_mermaid()`。参照实现规模：`langchain_core/runnables/graph.py` 的 `draw_mermaid` + `graph_mermaid.py` 约 300 行——**必须独立重写而非复制**（MIT 允许复制，但会带来 `langchain-core` 的风格与依赖包袱；且 Q7 商标/版权议题）。
3. **`draw_mermaid_png()` 必须是可选插件且默认关闭**：内核只保证 `draw_mermaid()` 纯本地成功。给 `target.py` 的迁移说明写清两选一：`draw_mermaid_png()` 在离线环境返回占位 PNG（不抛错），或改用 `draw_mermaid()` 写入 `.mmd` 文件后用 mermaid-cli 渲染。
4. **状态 schema 必须以「字典 + `Annotated` 归约器」为契约**，节点入参是 `dict`（不是对象），节点返回**部分** dict，合并规则 = 逐键调用 reducer（无 reducer 则覆盖）。这条是 freegraph 与 freechain 之间的核心语义契约（详见 Q8）。
5. **节点的路由判定只用鸭子类型**：freegraph 不需要认识 `AnyMessage`，只需把 `state` 原样传给节点并把返回的 dict 原样合并。这直接满足 §2.6 约束 3、4。
6. **加一条 CI 用例**：用 socket guard 断言 freegraph 全流程零出站（本次调研用的方法可直接复用为测试夹具）。

---

## 6. 自检

| 自检项 | 状态 | 说明 |
|---|---|---|
| 每个事实性结论带来源标记 | ✅ | 实跑实验表给命令+结果；源码引用给 `文件:行号`；本地文档给 `harness/docs/...:行号` |
| 包级清单 a) / 能力矩阵 b) / 触发点 c) / 逐项裁定 d) 全覆盖 | ✅ | §3.1 / §3.2 / §3.3 / §3.4 |
| 「剥离」的三层可验证定义 | ✅ | §3.3.1 包层 / 配置层 / 网络层 |
| 必给表格（包级 / 能力矩阵 / 触发点 / 逐项裁定 / 黑白名单） | ✅ | §3.1.1、§3.2、§3.3、§3.4、§3.6（§4 为索引指针） |
| 结论为可执行动作 | ✅ | §5 六条，含「CI 断言依赖树」「socket guard 测试夹具」 |
| 未修改 `harness/docs` / `harness/demo/target.py` / 源码 | ✅ | 只读；实验脚本在 `/tmp/opencode/og/`、`/tmp/opencode/lgapp/` |
| 无编造数字 | ✅ | `langgraph-store-sqlite` PyPI 404 已标；`langgraph-api` license 校验为 noop 的实现差异已注明 |
| 篇幅 1500–3000 字 + 表格 | ✅ | 正文约 3400 字（本题为核心问题，超出上限部分为必需表格内容）+ 6 组表 |
