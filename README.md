# freegraph

> **⚠️ 状态：v0.0.x 是「占位版」（name-reservation placeholder），内核尚未实现。**
> **v0.0.2 起**：每个源文件带署名头（Copyright + MIT + 项目地址）——MIT 允许文件被单独
> 复制，而复制不会带走 `LICENSE`，因此署名必须随每个文件流动。
> **v0.0.2 已发布**（2026-11-05）：发行产物纯度门禁在真实发布链路上首次执行并通过——
> wheel / sdist 均无任何仓库内容。
> **v0.0.3 起**：基础安装**零第三方运行时依赖**（原唯一的 `typing-extensions` 已剥离），
> 最低 Python 版本 **3.11**。
>
> 本次发布**只为在 PyPI 上锁定 `freegraph` 这个发行名**（发行名 = 导入名）。
> 目前 `import freegraph` 只会返回一个版本号，**没有任何图运行时能力**——
> 请勿用于生产，也不要把它当作 LangGraph 的可用替代品。
>
> 实现路线见仓库内 `harness/proposals/立项书.md`（31 个 feature / 93 人日 / v1.0）。

**English:** FreeGraph is a fully account-free, drop-in replacement for LangGraph,
faithfully replicating its API while maintaining LangChain compatibility — build and
run graph-based AI workflows without LangSmith or external account dependencies.

> **独立实现声明**：freegraph 为**独立实现、非 LangChain Inc. 产品**——
> 与 LangChain / LangGraph / LangSmith 无从属、授权或合作关系。
> 文中出现的相关名称仅为描述 **API 兼容目标**（同名 API 便于迁移），
> 不暗示任何 affiliation；逐符号的等价程度见下文「**API 兼容矩阵**」章节。

三条对外承诺（v1.0 交付时兑现）：

| 承诺 | 含义 |
|---|---|
| **零账号** | 无需 LangSmith 账号、API key 或 license key |
| **零出站** | freegraph **自身**不主动发起任何出站连接，且**不阻断用户代码**出网 |
| **零第三方运行时依赖** | 基础安装**不装任何第三方包**——`pip install freegraph` 后 site-packages 里只有 freegraph 自己 |

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

## API 兼容矩阵

> **兼容意图为互操作，不构成 affiliation** —— freegraph 与 LangChain / LangGraph / LangSmith
> **无从属、授权或合作关系**，亦未使用其商标、logo、品牌色或官方文案。
> 本表逐符号标注 freegraph 与上游的等价程度，是**活文档**（随每个 feature 新增的公开面更新，
> 由 B24F1 补全与定稿）。

| freegraph 符号 | 对应上游符号 | 等价程度 | 差异说明 |
|---|---|---|---|
| `StateDict` | （LangGraph 1.2.19 无同名公开符号） | 行为等价 | 与 `dict[str, Any]` 完全等价；上游把同一形状内联为 `dict[str, Any]`，未单列类型名 |
| `Command` | `langgraph.types.Command` | 部分等价 | 三个语义位 `goto` / `update` / `resume` 同名同义；freegraph **无 `graph` 字段**（目标图由 `Command.PARENT` 表达），且 `goto` 目标**只能是节点名**（上游可混入 `Send`） |
| `StateSnapshot` | `langgraph.types.StateSnapshot` | 部分等价 | 上游 **8** 个字段，freegraph **7** 个（**无 `parent_config`**）；`created_at` 上游为 `str \| None`，freegraph **必填**且恒为 UTC ISO-8601；`config` 的类型是 freegraph 自有的 `RunConfig`，不是 `RunnableConfig` |
| `RunConfig` | `langchain_core.runnables.RunnableConfig` | **不支持**（刻意替代） | 字段集完全不同：freegraph 为 `thread_id` / `context` / `metadata` / `tags`，**不含** `configurable` / `callbacks` / `recursion_limit` / `run_name`；`context` 是**独立通道**（契约 C21），**不塞进 `configurable`** |
| `FreegraphError` | （无对应） | 不支持 | freegraph 自创的统一基类——上游三个错误分属 `Exception` / `RecursionError` / `GraphBubbleUp` 三棵互不相干的继承树，无法只捕获一个基类兜住全部内核错误 |
| `InvalidUpdateError` | `langgraph.errors.InvalidUpdateError` | 部分等价 | 同名、同触发条件；freegraph 额外暴露 `.invalid_keys`（上游只有消息字符串） |
| `GraphRecursionError` | `langgraph.errors.GraphRecursionError` | 部分等价 | 同名、同触发条件；freegraph 额外暴露 `.recursion_limit` / `.current_step`（上游只有消息字符串） |
| `GraphInterrupt` | `langgraph.errors.GraphInterrupt` | 部分等价 | 同名、同触发条件；freegraph 暴露 `.payload`（按契约 C17 带 `.value` 与 `.id`）；两者均可被 `except Exception` 捕获 |

**证据来源**（截至 2026-11-05，按 LangGraph 1.2.19 / langchain-core 1.7.6 源码核实）：
`langgraph/types.py:711`（`StateSnapshot`）· `:738`（`Send`）· `:833`（`Command`）·
`langgraph/errors.py:51`（`GraphBubbleUp`）· `:68`（`GraphRecursionError`）· `:91`（`InvalidUpdateError`）· `:103`（`GraphInterrupt`）·
`langchain_core/runnables/config.py:57`（`RunnableConfig`）。
另见 `harness/reports/Q8-图运行时最小契约.md` §3.4 与 `harness/proposals/立项书.md` §5.3。

License: MIT
