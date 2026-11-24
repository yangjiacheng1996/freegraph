# API 兼容矩阵

> 本文件是**唯一权威**的逐符号 / 逐项兼容矩阵；`README.md` 只保留能力处置表与指向本文件的链接。

## API 兼容矩阵

> **兼容意图为互操作，不构成 affiliation** —— freegraph 与 LangChain / LangGraph / LangSmith
> **无从属、授权或合作关系**，亦未使用其商标、logo、品牌色或官方文案。

| freegraph 符号 | 对应上游符号 | 等价程度 | 差异说明 |
|---|---|---|---|
| `StateDict` | （LangGraph 1.2.19 无同名公开符号） | 行为等价 | 与 `dict[str, Any]` 完全等价；上游把同一形状内联为 `dict[str, Any]`，未单列类型名 |
| `Command` | `langgraph.types.Command` | 部分等价 | **B22F1 起泛型化**（`Command[N]`；字段 / 构造 / `PARENT` / 运行期语义不变，仅用于图渲染推断）；四个语义位 `goto` / `update` / `resume` / `graph` **同名同义**（**上游同款** · 2026-11-12 上游对齐 P3 · 上游 `langgraph/types.py:821-824`）；**无构造期校验**（上游同款 · `Command()` 合法）；`goto` 目标**可以是节点名或 `Send`**（上游同款 · B11F1）；**运行期语义已落地**（B9F1 · `goto` 落到**边触发源**空间 · `update` 与普通返回值**共用同一条合并路径**）；节点亦可返回**命令列表**（上游同款）；**`update` 接受 list/tuple of 2-tuples**（上游同款 · 上游 `langgraph/types.py:836-840`）；**节点返回 `None` ⇒ 无写入**（上游同款 · 上游 `langgraph/graph/state.py:1459-1460`） **B24F1 纠漂移（Y-01 / X-06）**：B1F1 原为「部分等价」；上游对齐批次 P3（commit `99d43aa`，2026-11-13）改为「行为等价」属未授权漂移（B22F1 `125ba0f` 仅追加泛型化措辞、未改第三列），本 feature 恢复并登记纠正来源。**Y-01**：`Command().goto` 缺省值上游 `()` vs freegraph `None`（B1F1 冻结）= **DIFF**（成功路径可观察差异，**不属「更严」**）。**X-06**：非法 `goto` 目标 / 非 dict `update` 显式失败 = **STRICTER**（B9F1 X-1 / X-4）。**X-2 / X-3**：B9F1 的异常类型差异（不是本 spec 的 X-02 / X-03）。 |
| `StateSnapshot` | `langgraph.types.StateSnapshot` | 行为等价 | **8** 个字段**同名同序**（**上游同款** · 2026-11-12 上游对齐 P3 · 上游 `langgraph/types.py:683-701`）；`created_at` / `metadata` **可空**（上游同款）；`tasks` / `interrupts` 的元素类型 = `PregelTask` / `Interrupt`（上游同款）；`config` / `parent_config` 的类型是 freegraph 自有的 `RunConfig`，不是 `RunnableConfig` |
| `RunConfig` | `langchain_core.runnables.RunnableConfig` | 行为等价 | **9** 个键**同名同义**（**上游同款** · 2026-11-12 上游对齐 P3 · 上游 `langchain_core/runnables/config.py:80-124`）：`tags` / `metadata` / `max_concurrency` / `recursion_limit` / `run_name` / `run_id` / `configurable` **齐备**；`thread_id` **顶层**保留（上游放在 `configurable` 内 ⇒ 由 `resolved_thread_id()` **两种写法都解析**）；**不含** `callbacks`（上游的类型在 `langchain_core` ⇒ 照抄即引入依赖 ⇒ 回调走 freegraph 自有的 `TraceSink`）；`context` 是**独立通道**（契约 C21），**不塞进 `configurable`** |
| `FreegraphError` | （无对应） | 不支持 | freegraph 自创的统一基类——上游三个错误分属 `Exception` / `RecursionError` / `GraphBubbleUp` 三棵互不相干的继承树，无法只捕获一个基类兜住全部内核错误 |
| `InvalidUpdateError` | `langgraph.errors.InvalidUpdateError` | 部分等价 | 同名、同触发条件；freegraph 额外暴露 `.invalid_keys`（上游只有消息字符串） |
| `GraphRecursionError` | `langgraph.errors.GraphRecursionError` | 部分等价 | 同名、同触发条件；freegraph 额外暴露 `.recursion_limit` / `.current_step`（上游只有消息字符串） |
| `GraphInterrupt` | `langgraph.errors.GraphInterrupt` | 行为等价 | 同名、同触发条件；`.payload` 是**中断序列**（**上游同款** · 2026-11-12 上游对齐 P3 · 上游 `langgraph/errors.py:102-107`），异常实参 `args[0]` 即该序列（上游同款）；元素为 `Interrupt`（带 `.value` / `.id` · 契约 C17）；两者均可被 `except Exception` 捕获 |
| `Interrupt` | `langgraph.types.Interrupt` | 行为等价 | **上游同款**（2026-11-12 上游对齐 P3 · 上游 `langgraph/types.py:575-620`）：`.value` / `.id` **同名同义** ⇒ 契约 C17 的「元素须带 `.value` 与 `.id`」有了**类型载体**；`.id` 的**自动生成**归 **B10F1**（上游按 checkpoint 命名空间派生） |
| `PregelTask` | `langgraph.types.PregelTask` | 行为等价 | **上游同款**（2026-11-12 上游对齐 P3 · 上游 `langgraph/types.py:637-646`）：七字段**同名同义**（`id` / `name` / `path` / `error` / `interrupts` / `state` / `result`）⇒ 快照的 `tasks` 元素类型与上游**一致** |
| `StreamWriter` | `langgraph.types.StreamWriter` | 行为等价 | **上游同款**（B8F2）：`Callable[[Any], None]` 类型别名（上游 `langgraph/types.py:138`）；由 `get_stream_writer()` 取得 · 无流时 no-op · 节点签名声明 `writer` 时按关键字注入 |
| `NodeFunc` | 无上游对应（自由设计） | 不支持 | 契约条目 **C5 / C6**（节点函数签名 / 节点返回值合并）——上游以普通 `dict` 调用节点函数，**无同名协议类**；返回**形态**已冻结（部分状态字典 / 命令原语 / **命令列表** / **`Send` / `list[Send]` / `tuple[Send, ...]`** / 空值），逐 key 归约语义**已落地**（B4F1 / B5F1）——**`Command` 的运行期语义已落地**（B9F1 · **命令列表**形态与上游 `ToolNode` 自身即用的形态同款） **无上游同名协议**（C5 / C6）；返回形态含**命令列表**与 `Send` / `list[Send]` / `tuple[Send, ...]`。 |
| `Checkpointer` | `langgraph.checkpoint.base.BaseCheckpointSaver` | 行为等价 | **八**方法的**方法名与参数名**逐字对齐（**上游同款** · 2026-11-12 上游对齐 P3 · 由六增八：新增 `delete_for_runs` / `copy_thread` —— 二者在**上游是必须实现**的 ⇒ **上游形状的 saver 直接满足本协议**）；freegraph **纯抽象、无默认实现**，上游是带实现的基类；**未含**上游的**异步变体**（v1 无 async）；**返回类型与载荷形状已由 B14F1 的 `MemorySaver` 落地**；上游来源 `langgraph/checkpoint/base/__init__.py:239`（`get_tuple`）/ `:253`（`list`）/ `:277`（`put`）/ `:300`（`put_writes`）/ `:320`（`delete_thread`）/ `:331`（`delete_for_runs`）/ `:350`（`copy_thread`）/ `:692`（`get_next_version`） |
| `TraceSink` | 无上游对应（自由设计） | 不支持 | 契约条目 **C23 / C24**（可观测挂钩 / 当前 span 上下文）——上游**无 span 推送协议**，其 `callbacks` / `tracers` 是**非同名**物 |
| `Store` | `langgraph.store.base.BaseStore` | 行为等价 | 六方法与**参数名**逐字镜像上游（`search` 的 `namespace_prefix` 是位置参数、`list_namespaces` 的 `prefix` 是关键字参数——上游的这个命名分歧**照抄不统一**）；**命名空间类型收紧为 `tuple[str, ...]`**（**上游同款** · 2026-11-12 上游对齐 P3 · 上游 `langgraph/store/base/__init__.py:311` 的 `NamespacePath`）⇒ **上游形状的 store 直接满足本协议**；**未含**上游的**异步变体**（v1 无 async）；`batch` 操作表示挂起 v2；上游来源 `langgraph/store/base/__init__.py:733`（`batch`）/ `:756`（`get`）/ `:779`（`search`）/ `:856`（`put`）/ `:937`（`delete`）/ `:946`（`list_namespaces`） |
| `CompiledGraph` | `langgraph.pregel.Pregel` | 部分等价 | 六方法的**返回类别**与**参数名（占位名）**已对齐（`invoke` → 完整状态字典 / `stream` → `dict[str, Any]` 事件迭代器 / `get_state` 查不到返回空值）；**`stream` 已交付**（B8F2 · 七种 mode · 四键信封 · `custom` 轮末批量 X-6）· **`get_state` / `get_state_history` 已交付**（B15F1 · 上游 **next-tasks** 语义 · 历史按 `checkpoint_id` 倒序 · `checkpoints` 档已接线）· **`update_state` / 时间旅行已交付**（B16F1 · `update_state` 返回 `RunConfig` · `invoke(None, snapshot.config)` 重放 · 分叉不污染原历史）；上游来源 `langgraph/pregel/main.py:3783`（`invoke`）/ `:2655`（`stream`）/ `:845`（`get_graph`）/ `:1392`（`get_state`）/ `:1480`（`get_state_history`）/ `:2515`（`update_state`） **Y-02**：`get_state` 无快照返回 `None` vs 上游空 `StateSnapshot` = **DIFF**（B15F1 P-02 / X-01）；`update_state` 无 `task_id` / 时间旅行线性重放 = **v1 能力边界**（非「更严」· B16F1）。 |
| `Graph` | `langchain_core.runnables.graph.Graph` | 部分等价 | **同名但自有实现**——不复用、不复制上游代码；freegraph 的节点 / 边集合是**不可变元组**（上游是 `dict[str, Node]` / `list[Edge]`）；**B22F1 起**提供 `draw_mermaid()`（纯本地、零出站）；**B23F1 起**提供 `draw_mermaid_png()`（v1 固定示意图标占位 PNG，零出站、离线不阻断）；上游来源 `langchain_core/runnables/graph.py:255` **v1.0 PNG = 合法占位图（非真实图形渲染）**；**v2.0 `[png]` 真实渲染升级路径**（B23F1 D-3 / FR-018）。 |
| `Node` | `langchain_core.runnables.graph.Node` | 部分等价 | **同名但自有实现**；freegraph 的 `name` 缺省**归一为 `id`**、`metadata` 是纯映射（上游 `Node.data` 装的是可调用对象 / pydantic 对象）；上游来源 `langchain_core/runnables/graph.py:95` |
| `Edge` | `langchain_core.runnables.graph.Edge` | 部分等价 | **同名但自有实现**；freegraph 多一个 `conditional` 位并显式**不可哈希**（上游是 `NamedTuple`，可哈希）；上游来源 `langchain_core/runnables/graph.py:65` |
| `Span` | 无上游对应（自由设计） | 不支持 | 契约条目 **C23 / C24**（可观测挂钩 / 当前 span 上下文）· 数据格式 **DF4**——11 字段、必带 `thread_id` / `run_id` / `node` / `checkpoint_id`；上游的近似物是 LangSmith 的 `RunTree`（**非同名**物） |
| `TraceQuery` | 无上游对应（自由设计） | 不支持 | 契约条目 **C27**（本地 trace 存储与查询）——5 字段全可空、可组合，全空 = 取全部；freegraph 自有的本地 trace 查询契约 |
| `StateGraph` | `langgraph.graph.StateGraph` | 行为等价 | **参数名与关键字逐字对齐上游**（**上游同款** · 2026-11-12 上游对齐 P3）：构造 `state_schema` / `context_schema` / `input_schema` / `output_schema` · `add_node(node, action=None, *, defer=False, metadata=None, destinations=None)`（含**单 callable** 形态 `add_node(fn)`）· `add_edge(start_key, end_key)` · `add_conditional_edges(source, path, path_map=None)` · `compile(checkpointer=None, *, cache, store, interrupt_before, interrupt_after, debug, name, transformers)` · 另补上游同款的 `add_sequence` / `set_entry_point` / `set_conditional_entry_point` / `set_finish_point` / `validate` / `set_node_defaults` 六个方法· **构建器已交付（B6F1）；`compile` 已交付（B7F2）；`invoke` 已交付（B7F3）；**条件边路由求值已交付（B8F1）** —— 路由函数在源节点任务**成功落回**后被求值（**fresh 读**：看到「当前值 + 本节点本次写入」）、`path_map` 支持 **list / dict / `None`** 三形态、返回 `END` 终止整张图、返回序列 ⇒ 多目标同轮并行、返回 `Send` ⇒ 复用 **B11F1** 的 fan-out 构造器；上游来源 `langgraph/graph/state.py:131`（类本体）/ `:216-224`（构造）/ `:667-682`（`add_node`）/ `:928`（`add_edge`）/ `:982-989`（`add_conditional_edges`）/ `:1032-1077`（`add_sequence`）/ `:1079` · `:1092` · `:1116` · `:1129-1175` · `:272-335` / `:1177-1188`（`compile`） **H-4 / B13F1**：`interrupt_before` / `interrupt_after` 关键字与 `recursion_limit` 的 dict 载体均已交付。 |
| `START` | `langgraph.constants.START` | 行为等价 | 值与语义均一致（`'__start__'`）；上游来源 `langgraph/constants.py:30`（核实环境 `langgraph 1.2.11`） |
| `END` | `langgraph.constants.END` | 行为等价 | 值与语义均一致（`'__end__'`）；上游来源 `langgraph/constants.py:28`（核实环境 `langgraph 1.2.11`） |
| `Send` | `langgraph.types.Send` | 部分等价 | 形状等价（`node` / `arg`）；**freegraph 侧不可变**（上游可变）；**fan-out 行为已落地**（B11F1 · `Command.goto` 可装 `Send` · 类型定义在 L1）；上游来源 `langgraph/types.py:704`（核实环境 `langgraph 1.2.11`） **freegraph 侧不可变（上游可变） = DIFF（Y-03）**；**运行期语义已落地**（B11F1 fan-out）；**`Send` 类型定义住 L1**（`freegraph/contracts/types.py`）。 |
| `get_stream_writer` | `langgraph.config.get_stream_writer` | 行为等价 | **上游同名函数**（B8F2）：返回当前 `StreamWriter`；无流时为 no-op；上游来源 `langgraph/config.py:126` |
| `interrupt` | `langgraph.types.interrupt` | 部分等价 | 形状等价（`value`，**位置或关键字**皆可）；**中断 / 恢复行为已落地**（B10F1）—— 节点内首次调用抛 `GraphInterrupt`（载荷 = **1-元组**）· 恢复时**返回** resume 值（**从节点起点重跑** · **不**保存局部变量）· **恢复 MUST 挂 checkpointer**（未挂 ⇒ `InterruptError`，**不**静默降级）；⚠️ **失败信号**的**类型**与上游不同（上游内置 `RuntimeError` ⇒ freegraph `InterruptError` · 属内核异常族 · **消息要点**逐字同款）⇒ **`.id` 的摘要算法**不同（上游 `xxh3_128` ⇒ freegraph 标准库 `blake2b-128` · **同长 32 位十六进制** ⇒ **零第三方依赖**）；上游来源 `langgraph/types.py:851`（核实环境 `langgraph 1.2.11`） |

## 18 项覆盖表

> Q3 §3.4 的 18 个 `target.py` API 元素；编号与义务以 Q3 为唯一权威。

| # | target.py API 元素 | 上游是否直接提供 | freegraph 处置 | 等价程度 | 证据 |
|---|---|---|---|---|---|
| 1 | `from freegraph.graph import StateGraph, START, END` | ✅ | 同名导出（`START='__start__'` / `END='__end__'`） | 行为等价 | Q3 §3.4 #1 |
| 2 | `StateGraph(MessagesState)` | ✅ | 只传 schema 一个位置参数 | 行为等价 | Q3 §3.4 #2 |
| 3 | `add_node(name, fn)` | ✅ | 位置参数 `(str, Callable)` | 行为等价 | Q3 §3.4 #3 |
| 4 | `add_edge(src, dst)` | ✅ | `(str \| list[str], str)` · 链式返回 · **多源汇合边支持（H-1）** | 行为等价 | Q3 §3.4 #4 · B7F4 D-6 |
| 5 | `add_conditional_edges(src, path_fn, path_map)` | ✅ | `path_map` 支持 list / dict / `None` | 行为等价 | Q3 §3.4 #5 · B8F1 |
| 6 | `compile()` | ✅ | 无参可调用；另接受 `interrupt_before` / `interrupt_after` 等上游关键字（H-4） | 行为等价 | Q3 §3.4 #6 · B13F1 D-8 |
| 7 | `compiled.invoke({"messages": [...]})` | ✅ | 返回**完整状态** dict | 行为等价 | Q3 §3.4 #7 |
| 8 | `Annotated[list[AnyMessage], operator.add]` 归约器 | ✅ | 二元 reducer `(a,b)->c` | 行为等价 | Q3 §3.4 #8 |
| 9 | `state.get('llm_calls', 0)` | ✅ | 节点入参是**普通 dict** | 行为等价 | Q3 §3.4 #9 |
| 10 | 节点返回**部分** state 的合并规则 | ✅ | 有 reducer 则归约；无 reducer 则覆盖 | 行为等价 | Q3 §3.4 #10 |
| 11 | `state["messages"][-1].tool_calls` | ✅ | 鸭子类型读取；freegraph 不需要懂消息类型 | 行为等价 | Q3 §3.4 #11 |
| 12 | `if last_message.tool_calls:` 真值判定 | ✅ | 空 list ⇒ falsy（鸭子类型） | 行为等价 | Q3 §3.4 #12 |
| 13 | `get_graph(xray=True).draw_mermaid_png()` | ✅ | 方法名同名；**v1.0 占位 PNG**（合法可展示字节、零出站、离线不阻断）；v2.0 `[png]` 真实渲染（DIFF 已登记 · X-01） | 部分等价 | Q3 §3.4 #13 · B23F1 D-3 |
| 14 | `display(Image(...))` | ❌（IPython，脚本自身） | 不属 freegraph 范围；不阻断脚本（原样承载 · 不属范围） | 行为等价 | Q3 §3.4 #14 |
| 15 | `init_chat_model(...)` | ❌（`langchain` 层） | 不属 freegraph 范围（归 freechain；原样承载 · 不属范围） | 行为等价 | Q3 §3.4 #15 |
| 16 | `@tool` / `tool.name` / `tool.invoke` | ❌（`langchain` 层） | freegraph 仅原样承载工具对象（鸭子类型），不做类型转换（原样承载 · 不属范围） | 行为等价 | Q3 §3.4 #16 |
| 17 | `tool.invoke(tool_call["args"])` | ❌（脚本自身逻辑） | 不属 freegraph 范围（原样承载 · 不属范围） | 行为等价 | Q3 §3.4 #17 |
| 18 | `ToolMessage(...)` | ❌（`langchain.messages`） | freegraph 原样流转该对象，不做类型转换（原样承载 · 不属范围） | 行为等价 | Q3 §3.4 #18 |

## 下游承接行

> 本段行**不参与**机读段的符号集合判据；下游行名统一写作 `CompiledGraph.<method>`。

| 行 | 等价程度 | 证据 / 来源 |
|---|---|---|
| 多源汇合边 `add_edge([a, b], c)` | 行为等价 | B7F4 D-6 · `langgraph/graph/state.py:928` |
| `MemorySaver` | 行为等价 | B14F1 D-07 |
| `InMemorySaver` | 行为等价（与 `MemorySaver` **同一对象 / 别名**） | B14F1 D-07 |
| `CheckpointTuple` | 行为等价（**恰三公开字段**） | B14F1 D-07 |
| `SqliteSaver` | 部分等价（MIT 改编；`json` 序列化差异 · X-07） | B15F1 D-04 |
| `CompiledGraph.get_state` | **部分等价**（**Y-02**：无快照返回 `None` vs 上游空 `StateSnapshot` · B15F1 P-02 / X-01） | B15F1 D-04 |
| `CompiledGraph.get_state_history` | **行为等价**（排序 / `filter` / `before` / `limit` 对齐上游 · P-04 / P-05，注明 B14F1 冻结差异） | B15F1 D-04 |
| `CompiledGraph.update_state` | 部分等价（返回 `RunConfig` · `as_node` · **无 `task_id`**） | B16F1 D-01 |
| 时间旅行重放 / 分叉 | 部分等价（`invoke(None, snapshot.config)` + `update_state` + `Command(resume)`；v1 线性） | B16F1 D-01 |
| `OtlpExporter` | 不支持（无上游对应 / 自由设计；Upstream Parity 关系 = DIFF） | B21F1 D-1 |

## 证据与来源

- **机读段**每行在「差异说明」中附上游 `路径:行号`、Q3 §3.4 或对应 feature 的实测锚点；禁止无依据的兼容性断言。
- **18 项覆盖表**逐项引用 Q3 §3.4 的编号；#4 另引 B7F4 D-6（多源汇合边）。
- **下游承接行**引用 B7F4 / B14F1 / B15F1 / B16F1 / B21F1 的 spec 与实测。
- **Store 澄清**：`Store` 为**协议等价 · v1 无实现**（`compile(store=...)` 仅接受并 warning）· `batch` 操作表示挂起 v2；机读行逐字保持既有，澄清仅在本节。
- **差分场景**：G-01…G-07 的覆盖映射落在 `tests/differential/test_differential.py` / `tests/differential/parity_probe.py` / `tests/differential/test_b15f1_state_parity.py` / `tests/differential/test_b16f1_time_travel_parity.py` / `tests/differential/test_b21f1_otlp_parity.py` / `tests/differential/test_b24f1_matrix_parity.py` 的真实场景名；不得把 `G-xx` 直接当作测试用例名。
- **版本口径**：既有行保留原引用版本（如 `StateDict` 的 `1.2.19`）；新增 / 复核行与差分测试统一以 `langgraph 1.2.11` 为准；每行 `路径:行号` 与声明版本一致。
- **Y-01**：`Command.goto` 缺省 `()` vs `None` = DIFF；**具名承接 B25F1（M4）**，运行时对齐归 v2。
- **Y-02**：`get_state` 无快照 `None` vs 上游空 `StateSnapshot` = DIFF（B15F1 X-01）；本 feature 只登记。
- **Y-03**：`Send` 不可变 vs 上游可变 = DIFF（B11F1）；本 feature 只登记。
- **v1 能力边界**：`update_state` 无 `task_id`、时间旅行线性重放；非「更严」。

## 维护规则

- 新增公开符号 / 兼容面 / 上游版本变化 ⇒ 同一个 feature 更新本文件。
- `README.md` MUST 链接本文件（**绝对 GitHub URL**：`https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md`），**MUST NOT** 复制完整矩阵。
- G8 / G19 / G29 的取行源均为本文件的 `## API 兼容矩阵` 章节；门禁编号零新增。
- `COMPAT.md` / `THIRD_PARTY_NOTICES` MUST NOT 进入 wheel / sdist。
