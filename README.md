# freegraph

> **⚠️ 状态：当前 `0.0.x` 是历史「占位版」（name-reservation placeholder）序列。**
> **v0.0.2 起**：每个源文件带署名头（Copyright + MIT + 项目地址）——MIT 允许文件被单独
> 复制，而复制不会带走 `LICENSE`，因此署名必须随每个文件流动。
> **v0.0.2 已发布**（2026-11-05）：发行产物纯度门禁在真实发布链路上首次执行并通过——
> wheel / sdist 均无任何仓库内容。
> **v0.0.3 起**：基础安装**零第三方运行时依赖**（原唯一的 `typing-extensions` 已剥离），
> 最低 Python 版本 **3.11**。
> **v0.0.4 起**：B25F1 收口——fake CI 轮 + 真实模型人工轮双跑、`diagnostics.py`、
> 迁移说明与最终 README；v1 图运行时能力随 `0.0.x` 占位序列继续发布。
>
> 当前仓库已交付 v1 的图运行时能力（Graph API、状态 / 持久化 / 时间旅行、可观测与 OTLP 导出、
> PNG 占位渲染）；发行包仍将在 v1.0 收口时一次性离开 `0.0.x`。实现路线见仓库内
> `harness/proposals/立项书.md`（32 个 feature / 96 人日 / v1.0）。

> **独立实现声明**：freegraph 为**独立实现、非 LangChain Inc. 产品**——
> 与 LangChain / LangGraph / LangSmith 无从属、授权或合作关系。
> 文中出现的相关名称仅为描述 **API 兼容目标**（同名 API 便于迁移），
> 不暗示任何 affiliation；逐符号的等价程度见仓库根 **`COMPAT.md`**（唯一权威矩阵）。

三条对外承诺（v1.0 交付时兑现）：

| 承诺 | 含义 |
|---|---|
| **零账号** | 无需 LangSmith 账号、API key 或 license key |
| **零出站** | freegraph **自身**不主动发起任何出站连接，且**不阻断用户代码**出网 |
| **零第三方运行时依赖** | 基础安装**不装任何第三方包**——`pip install freegraph` 后 site-packages 里只有 freegraph 自己 |

## 快速上手

```bash
# 基础安装（零第三方运行时依赖）
pip install freegraph

# 可选：OTLP gRPC 导出（v1.0 唯一具名 extra）
pip install "freegraph[otlp]"
```

最小图：

```python
from freegraph.graph import END, START, StateGraph

def add_one(state: dict) -> dict:
    return {"value": state.get("value", 0) + 1}

graph = StateGraph({"value": int})
graph.add_node("add_one", add_one)
graph.add_edge(START, "add_one")
graph.add_edge("add_one", END)
print(graph.compile().invoke({"value": 0}))
```

验收入口（开发 / 人工验收用，不需要 `pip install` 进运行时）：

```bash
# fake 轮（CI 可自动化；需要测试侧 acceptance 组：langchain + IPython）
python harness/verification/B25F1/fake_round.py

# 真实模型轮（人工；凭据由环境显式配置，优先官方直连）
python harness/verification/B25F1/real_round.py --record /tmp/b25f1-real.md
```

> `harness/demo/` 的四组零依赖验收脚本与 `diagnostics.py` 见
> [`harness/demo/README.md`](https://github.com/yangjiacheng1996/freegraph/blob/main/harness/demo/README.md)。

**设计与实现原理全部公开**：仓库
[`yangjiacheng1996/freegraph`](https://github.com/yangjiacheng1996/freegraph) 含有

- 立项书（范围、成本、里程碑与契约 C1–C27）
- Q1–Q9 调研报告（LangSmith / LangGraph / DeepAgents 的实测取证）
- 项目宪法（原则 I–X 与质量门禁）、开发指南与全部提示词
- 验收脚本集（`harness/demo/`，零第三方依赖）

**发行包本身是干净的**：PyPI 上的 `freegraph` 只含 `src/freegraph/` 下的包代码与
必要的元数据（README / LICENSE / pyproject.toml）——仓库里的调研报告、提示词与
验收脚本是**开发辅助材料**，留在 GitHub 上供学习，不会被 `import` 引入。
发布流水线有一道**纯度门禁**（`harness/scripts/check_dist_purity.py`）对此做断言。

## 依赖面

**基础安装零依赖** —— `pip install freegraph` 的 `dependencies` 为空；
发行元数据里**唯一**的可选依赖是 B21F1 的 `[otlp]` 具名例外（宪法 v1.17.0）：

```bash
pip install freegraph          # site-packages 里只有 freegraph 自己
pip install "freegraph[otlp]"  # 可选：OTLP gRPC 导出（默认不装）
```

> **v2.0 预告**：另有四个**可选 extra**（`[pydantic]` 结构化状态 schema ·
> `[checkpoint]` checkpoint 序列化 · `[otel]` OpenTelemetry 可观测内核 ·
> `[png]` 本地 PNG 渲染）—— 它们的声明与**许可证 / 黑名单预验证**已在仓库内完成
> （`specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml`），**v2.0 落地时才进入
> 发行元数据**。**四个 extra 都不是内核的必要条件** —— 内核与契约层只用标准库。

## 开发与验收

> **合入前 CI 必须全绿** —— 7 个作业（3 平台 × 2 个 Python 档 + Linux arm64 最低档）
> 覆盖全量测试套件与 10 条质量门禁（G21–G30）；任一作业变红即不得合入。
> 分支保护（必过检查 = 7 个 `gates (...)` 作业）的**可照抄设置步骤**见
> `harness/verification/B3F1/manual-verification.md`。

门禁脚本本身在 `harness/scripts/gates/`（**不进发行包**），逐条可独立执行：

```bash
uv venv --python 3.11
uv pip install --python .venv --group dev
uv pip install --python .venv -e .
uv pip install --python .venv -e ".[pydantic,checkpoint,otel,png]"
uv run --no-project --python .venv python -m pytest tests/ -ra
uv run --no-project --python .venv python harness/scripts/gates/gate_G21_dependencies.py
```

## 可观测属性（B18F1）

> 本 feature 只生产 span，不接入 `TraceSink`（B19F1）、不落盘（B20）、不导出 OTLP（B21F1）。
> 属性命名对齐 OpenTelemetry GenAI semconv（`open-telemetry/semantic-conventions-genai`，
> Apache-2.0）；v1 只写下列**最小集**，内容类属性（`gen_ai.input.messages` 等）默认不采集。

| span 层级 | v1 写入的属性 | 说明 |
|---|---|---|
| 节点级 | **空映射** | 节点身份由 `name` / `node` 字段表达；不写 `freegraph.*` 结构属性 |
| 模型级 | `gen_ai.operation.name`（恒 `chat`）· `gen_ai.request.model`（可读时） | 模型名来源：对象 `model_name` → `model`；读不到则省略 |
| 工具级 | `gen_ai.operation.name`（`execute_tool`）· `gen_ai.tool.name`（空串也写）· `gen_ai.tool.call.id`（调用方显式提供且非空时） | 名称格式：`execute_tool <tool.name>` |
| 通用 | `error.type`（仅模型 / 工具失败时 MUST 写；值为 `type(exc).__name__` / `_OTHER`） | 节点 span 即使失败也不写 `error.type` |

> 模型 span 名称：`chat <model>`（可读模型名时）或 `chat`；节点 span 名称 = 节点内部名。
> 本 feature **不写** `gen_ai.system`（已弃用）；provider 标识如未来写入只使用
> `gen_ai.provider.name`。

## OTLP 导出（B21F1 · 可选 `[otlp]`）

安装：`pip install "freegraph[otlp]"`。把 freegraph 自有的 `Span` 以**标准 OTLP** 导出到用户**显式提供**的端点 / 导出器；
默认关闭、无默认端点、不读环境变量、导出失败不阻断图执行。

```python
from freegraph.observability import OtlpExporter

# 端点模式（gRPC；本地明文示例）
exporter = OtlpExporter(endpoint="127.0.0.1:4317", insecure=True)
graph = builder.compile(tracer=exporter)

# 导出器模式（例如用户自装官方 HTTP exporter）
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
exporter = OtlpExporter(exporter=OTLPSpanExporter(endpoint="http://127.0.0.1:4318/v1/traces"))
```

- `endpoint=` 只接受 `host:port`（不带 URL scheme）；`insecure=False` 默认 TLS。
- `headers` / `timeout` 仅端点模式；`exporter=` 模式由用户对象自行负责 TLS / 认证。
- `[otlp]` 只含官方 gRPC 协议实现 + OTel SDK；**不含** `certifi` / HTTP exporter /
  `opentelemetry-exporter-otlp` 元包。
- 三个后端示例：[`harness/examples/B21F1/`](harness/examples/B21F1/)（OpenLIT / Langfuse / Phoenix）。

**能力分工 / 重叠说明**：freegraph 负责**本地运行时诊断**（图视图、状态快照、
checkpoint / time-travel、交互式调试）；OpenLIT / Langfuse / Phoenix 负责**外部 trace
浏览 / 分析 / 评测 / Prompt 管理**——重叠是**分层互补**，不是替代关系。
**三示例并列、无默认推荐**。

**已知失效风险**：OpenLIT 旧路径 `openlit.io/docs` **404**，现行文档为
`https://docs.openlit.io/latest/overview`（as-of 2026-11-24，仓库 README 可作回退）；
OTel 后端 API / 版本变更可能使示例失效；HTTP exporter 是**用户侧依赖**（其闭包含
`certifi`（MPL-2.0），不进 freegraph 的 `[otlp]`）；Phoenix 为 Elastic-2.0 ⇒ **只连不嵌**。

## 能力 → freegraph 处置

> 下表**逐字复刻**立项书 §3.2 的定稿表体（as-of **2026-11-01**，以官方定价页为准）；
> 随每次范围变更更新。

| 能力 | Developer $0 | Plus $39/seat/月 | Enterprise | freegraph v1 |
|---|---|---|---|---|
| Tracing / Monitoring / Evals / Datasets / Annotation Queue / Prompt Hub / Studio | ✅ | ✅ | ✅ | ❌ 不做（评测平台范畴） |
| 本地图结构可视化（mermaid） | ✅（OSS 自带） | ✅ | ✅ | ✅ 做（零出站） |
| 本地 trace 记录 / thread / trajectory | ✅（须账号） | ✅ | ✅ | ✅ 做（本地存储） |
| 状态快照 + checkpoint 历史 + time-travel | ✅（须账号 + 云） | ✅ | ✅ | ✅ 做 |
| 交互式图运行时 IDE（node/edge 可交互图视图 + 运行时事件流联动） | ✅（须账号 + 云） | ✅ | ✅ | ❌ **不做（v2）**：完整 IDE 属 B26，本轮未排 feature |
| 本地图运行时诊断**能力层**（mermaid 图视图 + trace 查询 + 回放 API，不含任何前端 UI 代码） | ✅（须账号 + 云） | ✅ | ✅ | ✅ 做（v1 三件套，能力层优先） |
| Deployment 托管与扩缩 / Engine / Insights / Tuned Evaluators / Bulk export | ❌ | 部分 | ✅ | ❌ 永不做 |
| Fleet / Sandboxes / LLM Gateway（免费但必出站） | ✅ | ✅ | ✅ | ❌ 永不做 |

## 运行期语义与已知边界

> ⚠️ **`invoke()` 的返回值是「只读快照」· 不要原样回喂给下一次 `invoke`**（B7F3）——
> `invoke()` 返回**完整状态**：键集 == schema 全部 key（按 schema 声明顺序），
> 从未被写的覆盖型（无归约器）key 以 `None` 补齐。回喂会把补齐的 `None`
> 真的写进通道 ⇒ 节点里 `state.get("llm_calls", 0) + 1` 会 **`TypeError`**。

> **v1 的 `store=` 边界**：`compile(store=...)` 仍被接受（API 兼容），但
> **v1 不支持 `Store`**——该参数只被记录并发出 1 条 warning，不会生效。
> **checkpointer 的行为已由 B14F1 的 `MemorySaver` 落地**：`compile(checkpointer=...)`
> 在编译期校验类型，挂载真实 saver 后可按 `thread_id` 持久化 / 恢复。
> **B15F1 增补**：新增 `SqliteSaver`（磁盘 · 默认推荐）与
> `compiled.get_state(config)` / `compiled.get_state_history(config)`；`update_state` 与
> **时间旅行已交付**（B16F1 · `update_state` 返回 `RunConfig` · `invoke(None, snapshot.config)` 重放）。

## API 兼容矩阵

> **唯一权威**的逐符号 / 逐项兼容矩阵位于仓库根
> [`COMPAT.md`](https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md)。
> README **只保留**本指针与「能力 → freegraph 处置」表，**不维护第二份完整矩阵**。
>
> **兼容意图为互操作，不构成 affiliation** —— freegraph 与 LangChain / LangGraph / LangSmith
> **无从属、授权或合作关系**，亦未使用其商标、logo、品牌色或官方文案。

## English

- **Independent implementation**: FreeGraph is an independent implementation and is **not a LangChain Inc. product**; it is not affiliated with, authorized by, or partnered with LangChain, LangGraph, or LangSmith.
- **Three promises**: zero account (including zero license key), zero egress from FreeGraph itself, and zero third-party runtime dependencies for the base install.
- **Install**: `pip install freegraph` installs no third-party runtime dependency; `pip install "freegraph[otlp]"` optionally adds the OTLP gRPC exporter.
- **Capabilities**: the v1 capability layer covers the Graph API, state snapshots / checkpoint history / time travel, local trace query, and offline graph visualization. The full Studio IDE is out of scope for v1.
- **Per-symbol compatibility**: see [`COMPAT.md`](https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md) for the authoritative behavior-equivalence matrix.

License: MIT
