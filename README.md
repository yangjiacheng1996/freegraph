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
| `NodeFunc` | 无上游对应（自由设计） | 不支持 | 契约条目 **C5 / C6**（节点函数签名 / 节点返回值合并）——上游以普通 `dict` 调用节点函数，**无同名协议类**；返回**形态**已冻结（部分状态字典 / 命令原语 / 空值），逐 key 归约语义挂起 B4F1 / B5F1 |
| `Checkpointer` | `langgraph.checkpoint.base.BaseCheckpointSaver` | 部分等价 | 六方法的**方法名与参数名**逐字对齐；freegraph **纯抽象、无默认实现**，上游是带实现的基类；**返回类型与载荷形状挂起 B14F1**；上游来源 `langgraph/checkpoint/base/__init__.py:239`（`get_tuple`）/ `:253`（`list`）/ `:277`（`put`）/ `:300`（`put_writes`）/ `:320`（`delete_thread`）/ `:692`（`get_next_version`） |
| `TraceSink` | 无上游对应（自由设计） | 不支持 | 契约条目 **C23 / C24**（可观测挂钩 / 当前 span 上下文）——上游**无 span 推送协议**，其 `callbacks` / `tracers` 是**非同名**物 |
| `Store` | `langgraph.store.base.BaseStore` | 部分等价 | 六方法与**参数名**逐字镜像上游（`search` 的 `namespace_prefix` 是位置参数、`list_namespaces` 的 `prefix` 是关键字参数——上游的这个命名分歧**照抄不统一**）；命名空间**载体形态**与 `batch` 操作表示挂起 v2；上游来源 `langgraph/store/base/__init__.py:733`（`batch`）/ `:756`（`get`）/ `:779`（`search`）/ `:856`（`put`）/ `:937`（`delete`）/ `:946`（`list_namespaces`） |
| `CompiledGraph` | `langgraph.pregel.Pregel` | 部分等价 | 六方法的**返回类别**与**参数名（占位名）**已对齐（`invoke` → 完整状态字典 / `stream` → `dict[str, Any]` 事件迭代器 / `get_state` 查不到返回空值）；**行为细节挂起** B7F3 / B8F2 / B15F1 / B16F1；上游来源 `langgraph/pregel/main.py:3783`（`invoke`）/ `:2655`（`stream`）/ `:845`（`get_graph`）/ `:1392`（`get_state`）/ `:1480`（`get_state_history`）/ `:2515`（`update_state`） |
| `Graph` | `langchain_core.runnables.graph.Graph` | 部分等价 | **同名但自有实现**——不复用、不复制上游代码；freegraph 的节点 / 边集合是**不可变元组**（上游是 `dict[str, Node]` / `list[Edge]`）；上游来源 `langchain_core/runnables/graph.py:255` |
| `Node` | `langchain_core.runnables.graph.Node` | 部分等价 | **同名但自有实现**；freegraph 的 `name` 缺省**归一为 `id`**、`metadata` 是纯映射（上游 `Node.data` 装的是可调用对象 / pydantic 对象）；上游来源 `langchain_core/runnables/graph.py:95` |
| `Edge` | `langchain_core.runnables.graph.Edge` | 部分等价 | **同名但自有实现**；freegraph 多一个 `conditional` 位并显式**不可哈希**（上游是 `NamedTuple`，可哈希）；上游来源 `langchain_core/runnables/graph.py:65` |
| `Span` | 无上游对应（自由设计） | 不支持 | 契约条目 **C23 / C24**（可观测挂钩 / 当前 span 上下文）· 数据格式 **DF4**——11 字段、必带 `thread_id` / `run_id` / `node` / `checkpoint_id`；上游的近似物是 LangSmith 的 `RunTree`（**非同名**物） |
| `TraceQuery` | 无上游对应（自由设计） | 不支持 | 契约条目 **C27**（本地 trace 存储与查询）——5 字段全可空、可组合，全空 = 取全部；freegraph 自有的本地 trace 查询契约 |
| `StateGraph` | `langgraph.graph.StateGraph` | 部分等价 | 构造**只接受** `schema` 一个位置参数（上游另有 `context_schema` / `input_schema` / `output_schema`）；`add_node` 的参数名为 `name` / `fn`（上游 `node` / `action`）且新增 `alias` 关键字；`compile` 只保留 `checkpointer` / `store` 两个关键字（上游另含 `cache` / `interrupt_before` / `interrupt_after` / `debug` / `name` / `transformers`）；**构建器行为待 B6F1 / B7F2 交付**；上游来源 `langgraph/graph/state.py:131`（核实环境 `langgraph 1.2.11`） |
| `START` | `langgraph.constants.START` | 行为等价 | 值与语义均一致（`'__start__'`）；上游来源 `langgraph/constants.py:30`（核实环境 `langgraph 1.2.11`） |
| `END` | `langgraph.constants.END` | 行为等价 | 值与语义均一致（`'__end__'`）；上游来源 `langgraph/constants.py:28`（核实环境 `langgraph 1.2.11`） |
| `Send` | `langgraph.types.Send` | 部分等价 | 形状等价（`node` / `arg`）；**freegraph 侧不可变**（上游可变）；**fan-out 行为待 B11F1 交付**；上游来源 `langgraph/types.py:704`（核实环境 `langgraph 1.2.11`） |
| `interrupt` | `langgraph.types.interrupt` | 部分等价 | 形状等价（`value`）；**中断 / 恢复行为待 B10F1 交付**；上游来源 `langgraph/types.py:851`（核实环境 `langgraph 1.2.11`） |

**证据来源**（截至 2026-11-05，按 LangGraph 1.2.19 / langchain-core 1.7.6 源码核实）：
`langgraph/types.py:711`（`StateSnapshot`）· `:738`（`Send`）· `:833`（`Command`）·
`langgraph/errors.py:51`（`GraphBubbleUp`）· `:68`（`GraphRecursionError`）· `:91`（`InvalidUpdateError`）· `:103`（`GraphInterrupt`）·
`langchain_core/runnables/config.py:57`（`RunnableConfig`）。
另见 `harness/reports/Q8-图运行时最小契约.md` §3.4 与 `harness/proposals/立项书.md` §5.3。

**本层（契约层协议面 · B2F1）来源**（截至 2026-11-06，按 **langgraph 1.2.11** / **langchain-core 1.6.3** 源码核实）：
`langgraph/checkpoint/base/__init__.py:239`（`get_tuple`）· `:253`（`list`）· `:277`（`put`）· `:300`（`put_writes`）· `:320`（`delete_thread`）· `:692`（`get_next_version`）·
`langgraph/store/base/__init__.py:733`（`batch`）· `:756`（`get`）· `:779`（`search`）· `:856`（`put`）· `:937`（`delete`）· `:946`（`list_namespaces`）·
`langgraph/pregel/main.py:3783`（`invoke`）· `:2655`（`stream`）· `:845`（`get_graph`）· `:1392`（`get_state`）· `:1480`（`get_state_history`）· `:2515`（`update_state`）·
`langchain_core/runnables/graph.py:255`（`Graph`）· `:95`（`Node`）· `:65`（`Edge`）。

> **行号以各自标注的版本为准** —— **表内新增行**（B2F1 的 10 个 + B2F2 的 5 个符号）的上游行号以
> **langgraph 1.2.11** / **langchain-core 1.6.3** 为准，与既有 8 行的
> **LangGraph 1.2.19** / **langchain-core 1.7.6** **版本不同**；两套行号各自有效，
> **不可混用**。

License: MIT
