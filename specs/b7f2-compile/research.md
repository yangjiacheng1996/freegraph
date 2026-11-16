# 研究与技术决策（B7F2 · `compile()` → `CompiledGraph`）

**Feature**: `specs/b7f2-compile/` · **Date**: 2026-11-16 · **上游**: `langgraph 1.2.11`
（`.venv/lib/python3.11/site-packages/langgraph`）

> **纪律**（宪法原则 XI）：每个设计点先问上游；**上游有答案 ⇒ 照抄**。本文件只记录
> **上游锚点 + 实测**与**照抄之后的落法**；凡是「上游没有答案」的地方，MUST 在
> §3 明确标为**必须自研区**并给出判据。

---

## 1. 上游实测取证（E-25…E-55）

> **可复现性**：本次取证脚本的**入库版本** = `harness/verification/B7F2/probe_upstream.py`
> （tasks 中落一条）；本节只记录**观测结果**。全部在
> `langgraph 1.2.11` + 未设 `LANGSMITH_*` / `LANGCHAIN_*` 的干净环境下取得。

| # | 观测点 | 实测结果 |
|---|---|---|
| **E-25** | `langgraph.graph.__all__` | `END` / `MessageGraph` / `MessagesState` / `START` / `StateGraph` / `add_messages` —— **不含** `CompiledStateGraph` |
| **E-26** | `hasattr(langgraph.graph, "CompiledStateGraph")` | `False` ⇒ 门面**不导出**编译产物类 |
| **E-27** | `StateGraph(...).compile()`（无参） | **OK** · 返回 `CompiledStateGraph` |
| **E-28** | `compile(checkpointer=None, store=None)` | **OK** |
| **E-29** | `compile(checkpointer=object())` | **`TypeError`**：`Invalid checkpointer provided. Expected an instance of `BaseCheckpointSaver`, `True`, `False`, or `None`. …` |
| **E-30** | `compile(store=object())` | **OK**（上游的 store 真能生效） |
| **E-31** | 编译产物公开属性 | `checkpointer` / `store` / `cache` / `debug` / `name` / `interrupt_before_nodes` / `interrupt_after_nodes` / `nodes` / `channels` / `builder` **全部存在**（⚠️ **不含** `transformers`；上游对应属性名为 `stream_transformers`（`pregel/main.py:831`）⇒ freegraph 的 `transformers` 命名登记 **X-12**） |
| **E-32** | 编译产物方法面 | `invoke` / `stream` / `get_graph` / `get_state` / `get_state_history` / `update_state` **全在** |
| **E-33** | 缺省值 | `debug=False` · `name="LangGraph"` · `interrupt_before_nodes=[]` · `interrupt_after_nodes=[]` |
| **E-34** | `compile(interrupt_before="*")` | **OK** |
| **E-35** | `compile(interrupt_before=["*"])` | **`ValueError`**：`Interrupt node `*` not found` |
| **E-36** | `compile(interrupt_before="")` | **OK**（`"" or []` ⇒ 当作「不配置」· **静默接受**） |
| **E-37** | `compile(interrupt_before="a")` | **`TypeError`**：`can only concatenate str (not "list") to str`（拼接副作用） |
| **E-38** | `compile(interrupt_before=("a",))` | **`TypeError`**：`can only concatenate tuple (not "list") to tuple` |
| **E-39** | `compile(interrupt_before=["nope"])` | **`ValueError`**：`Interrupt node `nope` not found` |
| **E-40** | `compile(interrupt_before=["a"])` | **OK** |
| **E-41** | `compile()` 后 `add_node(...)` | **`warnings.warn` 捕获数为 0**（不是 warnings 机制） |
| **E-42** | 同一构建器 `compile()` 两次 | **两个不同对象**（`x is not y`） |
| **E-43** | 编译产物的 `channels` / `nodes` | `channels` 含 `__pregel_tasks` / `__start__` / `branch:to:a` / `branch:to:b` / 状态通道；`END` **不在** `nodes`（且 `branch:to:<node>` 对**每个节点**都建，不限于条件边目标） |
| **E-44** | `START -> END` 空图 `compile()` | **OK**（上游接受空图） |
| **E-45** | `compile(interrupt_after=("a",))` | **`TypeError`**：`can only concatenate list (not "tuple") to list` |
| **E-46** | `compile(interrupt_before={"a"})`（`set`） | **`TypeError`**：`unsupported operand type(s) for +: 'set' and 'list'` |
| **E-47** | `compile(interrupt_before="*")` 后读 `compiled.interrupt_before_nodes` | **`"*"`（原值，未展开）** |
| **E-48** | `compile(interrupt_before=["a"], interrupt_after=["b"])` 后读两个属性 | `['a']` / `['b']`（**原值**，不是归一化元组） |
| **E-49** | 同 E-41 的 `warnings.catch_warnings(record=True)` | **0 条** |
| **E-50** | 同 E-41 的 `logging` 捕获 | **1 条**：`Adding a node to a graph that has already been compiled. This will not be reflected in the compiled graph.` ⇒ 上游用 **`logging.warning`** |
| **E-51** | 缺入口（无 `START` 边）`compile()` | **`ValueError`**：`Graph must have an entrypoint: add at least one edge from START to another node` |
| **E-52** | 边指向不存在节点 `compile()` | **`ValueError`**：`Found edge ending at unknown node `ghost`` |
| **E-53** | `compile(store=sentinel)` 后 `compiled.store is sentinel` | **`True`**（身份保留，不复制） |
| **E-54** | `compile(debug=True)` → `compiled.debug` | **`True`** |
| **E-55** | `compile(name="my-graph")` → `compiled.name` | `"my-graph"` |

**E 编号承接**：E-01…E-24 属 B6F1（构建器）；本 feature 从 **E-25** 起。**不重号、不复用**。

### 1.1 由实测得出的**直接结论**

1. **`compile()` 无参可调用**（E-27）且 `checkpointer=None / store=None` 被接受（E-28）⇒
   spec 的 A2 / A3 是**照抄**上游，不是自设目标。
2. **静态断点的容器形态**：上游**实际**拒绝元组 / 裸非 `"*"` 字符串 / `set`（E-37 / E-38 / E-45 / E-46，
   全部 `TypeError`），但**静默接受裸空串**（E-36）⇒ freegraph 的入口容器门
   （`None` / `str` / `list`；**`str` 原样透传，裸非 `"*"` 串由 `GraphSpec` 归一抛 `TypeError`**）
   **对前四类与上游同类失败信号**，**只对裸空串更严**（X-2）。
3. **编译产物公开注入项与断点配置**（E-31 / E-33 / E-47 / E-48 / E-53 / E-54 / E-55）⇒ freegraph
   **照抄暴露**（S-1）；**形态/命名差异** = 断点属性暴露**归一后的元组**（上游保留原值）⇒ **X-11** +
   `transformers` 属性名（上游为 `stream_transformers`）⇒ **X-12**。
4. **「已编译后改图」的提示是 `logging.warning`**（E-49 / E-50），不是 `warnings.warn` ⇒
   freegraph **不复制**该副作用（X-5）；本 feature 的 `store=` 提示**独立于它**（`warnings.warn`，
   裁定 14），二者**不是同一条机制**、不冲突。
5. **上游对空图放行**（E-44）而 freegraph 的 `GraphSpec` V-3 **拒绝** ⇒ 该差异属 **B6F1 X-5**
   （不是本 feature 新增），但会在**编译期**首次可观察 ⇒ **已在 B6F1 的「差分 D-72 / 偏离 X-5」登记**，
  本 feature **不新增差分行、不新增偏离编号**（避免同一分叉两处登记）。

---

## 2. 上游源码锚点（版本 + 路径:行号）

| 语义点 | 锚点（`langgraph 1.2.11`） |
|---|---|
| `compile()` 签名与关键字 | `langgraph/graph/state.py:1177-1189` |
| `ensure_valid_checkpointer` 调用 / 定义 | `langgraph/graph/state.py:1234` · `langgraph/types.py:109-118` |
| 断点归一（`or []`）与 `validate` 调用 | `langgraph/graph/state.py:1264-1272` |
| `validate()` 本体（源 / 入口 / 目标 / 断点节点 / `compiled=True`） | `langgraph/graph/state.py:1129-1175` |
| 编译产物构造 | `langgraph/graph/state.py:1346-1371` |
| `attach_node` / `attach_edge` / `attach_branch` | `langgraph/graph/state.py:1373-1399` · `:1444` · `:1551` · `:1577` |
| `CompiledStateGraph(Pregel)` | `langgraph/graph/state.py:1404-1407` · `langgraph/pregel/main.py:450` |
| 公开属性赋值 | `langgraph/pregel/main.py:800-830`（`nodes` / `channels` / `interrupt_*_nodes` / `debug` / `checkpointer` / `store` / `cache` / `name`） |
| 路由通道 | `langgraph/graph/state.py:98`（`branch:to:{}`）· `:1525-1530`（`EphemeralValue(Any, guard=False)`） |
| 通道集合（含 `START` 与 `__pregel_tasks`） | `langgraph/graph/state.py:1354-1358` |
| 6 方法 | `langgraph/pregel/main.py:845`（`get_graph`）· `:1392` · `:1480` · `:2515` · `:2616+` · `:3783+` |
| 通道规格 / 每次运行新建 | `langgraph/channels/last_value.py:50-54` · `langgraph/channels/base.py:61-64` |
| 门面导出面 | `langgraph/graph/__init__.py`（`__all__` 6 项） |

---

## 3. 设计决策（DR-1…DR-16）

### DR-1 · 编译产物落点：L3 单文件（**上游无对应 · 必须自研区 ③/④**）

- **决策**：`CompiledGraph` 与 `StateGraph` **同模块** `src/freegraph/_stategraph.py`。
- **理由**：`specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` 把
  `src/freegraph/_stategraph.py` 登记为**文件级 L3 条目**；`gate_G25_import_graph.py:92-100`
  对「同层（L2–L5）横向 import」**一律判违规**（`source.path == target.path` 才豁免，
  而两条文件级条目的 `path` 不同）⇒ 若新建 `src/freegraph/_compiled.py`：
  ① `_stategraph.py` 导入它 ⇒ **L3 → L3 违规**；② 或必须**改冻结的层注册表**
  （`<!-- authority: yes -->` 的唯一权威）并同步 `tests/facade/_gatesupport.py` 的
  `FACADE_MODULES` / `SIGNED_SOURCE_FILES`。
- **被否方案**：新文件 + 注册表新增条目 —— 代价更大、动到冻结面；
  门面中转（`graph.py` 注入类）—— 隐式耦合、可读性差。
- **判据**：G25 绿、层注册表**零改动**、`src/freegraph/` 下仍无 L3 横向边。
- **性质**：属**必须自研区 ③**（上游没有「L3 分层」这回事）⇒ 已在 spec 裁定 2 的
  「L3 私有模块」框架内；**具体文件名**由本 plan 落定并回修 spec 的括注（见 §5 补记 P-1）。

### DR-2 · `compile()` 不做第二次 schema 解析

- **决策**：只调 `self._build_spec()`（B6F1 D-1 冻结入口）。
- **理由**：B6F1 的 `_build_spec()` 已完成 `parse_state_schema` / `build_channels` /
  构建期末校验并返回**新快照**；重解析会破坏「唯一入口」并带来两次校验的漂移。
- **判据**：`compile()` 内零 `parse_state_schema` 调用（AST / 覆盖率可查）。

### DR-3 · 图规格适配：只做 END 过滤 + 组装

- **决策**：`GraphSpec(channels=<新映射>, nodes=<原样>, edges=<过滤后>, interrupt_before=…,
  interrupt_after=…)`；`conditional_edges` **不传**。
- **理由**：① `GraphSpec.nodes` 是 `dict[str, NodeSpec]`，与 `_BuilderSpec.nodes` **同构** ⇒
  直接复用；② V-2 不接受 `END` 作为目标 ⇒ 单源 `END` 必须过滤（B6F1 D-1）；
  ③ `conditional_edges` 非空即 V-8 失败 ⇒ 只能挂私有字段（X-6）。
- **为什么 `channels` 用**新映射**：B7F1 FR-034 允许调用方（B8F1）在运行期向
  `GraphSpec.channels` **增补内部通道**；若与 `_builder_spec.channels` 同一个 dict，
  增补会**改写构建器快照**（违反 FR-008 的「MUST NOT 改写其内容」）。**模板对象**仍是同一批
  （通道规格本来就是「共享模板 + 每次运行克隆」· P-15）。

### DR-4 · 校验：全部委托 `GraphSpec.__post_init__`（单一真源）

- **决策**：不在 `compile()` 里另写 V-1 / V-2 / V-3 / V-14 / V-16 / V-22…V-25。
- **理由**：B7F1 的校验在**构造时**执行（裁定 32）；B6F1 的构建期末校验已覆盖 schema / 源 /
  入口 / 目标 / 空节点表 ⇒ 两层**串联**即完整覆盖 spec 的 C-01…C-14，**零重复实现**。
- **判据**：`compile()` 内不出现 `raise ValueError` / `raise TypeError` 的**图结构**判定
  （唯一例外：断点**容器形态**门 · DR-5）。

### DR-5 · 静态断点：入口层只判**容器形态**

- **决策**：
  ```python
  def _static_points(value, field_name):
      if value is None:            # 归一为 ()
          return ()
      if isinstance(value, (str, list)):   # "*" / 裸串 / list 原样交 GraphSpec
          return value
      raise TypeError(f"{field_name} must be '*' or a list of node names, "
                      f"got {type(value).__name__} (V-22)")
  ```
- **理由**：B13F1 D-1 要求「tuple 的拒绝**只在** B7F2 的 compile 入口层」；D-2 要求
  `START` / `END` / 空串 / `["*"]` / 裸非 `"*"` 字符串 / 非 `str` 的失败信号与
  `GraphSpec` 构造期**逐字同款** ⇒ **白名单 + 委托**是唯一能同时满足两者的写法
  （裸串交给 `normalize_static_points` 才会得到**逐字相同**的 `TypeError` 消息）。
- **被否方案**：入口层自己逐元素校验 ⇒ 消息必然与 `normalize_static_points` 漂移。
- **判据**：D4 用**字符串相等**比较两条失败消息（同一字段、同一非法值）。

### DR-6 · 注入项：接受 + 记录 + 不校验；`store` 非 `None` 发 1 条 warning

- **决策**：`checkpointer` / `store` / `cache` / `debug` / `name` / `transformers` 全部原样记录；
  **零类型校验**；`store is not None` ⇒ `warnings.warn("v1 不支持 Store …", stacklevel=2)`。
- **理由**：① 上游在编译期校验 checkpointer（E-29）⇒ freegraph v1 **故意不做**（X-4），
  因为 v1 无实现，校验只会把「尚未就绪」误报成「用户错误」，且补校验归 B14F1（D-4）；
  ② `store` 在 v1 **永久**无实现（原则 VII）⇒ 用户必须**当场**知道（用户裁定 A · 裁定 14）；
  ③ 上游的「已编译后改图」提示是 `logging.warning`（E-49/E-50），与本条的 `warnings.warn`
   **不是同一机制**，不冲突。
- **判据**：`pytest.warns` 捕获 1 条；`store=None` 时 `warnings.catch_warnings` 为空。

### DR-7 · 断点对外形态：暴露**归一后的元组**

- **决策**：`compiled.interrupt_before_nodes` / `interrupt_after_nodes` = `GraphSpec` 归一后的
  保序元组（`"*"` 已展开、`None` → `()`）。
- **理由**：① 单一语义只留**一个载体**（原则 XII）——`GraphSpec` 已是归一真源，再存一份
  用户原值就出现「两处都有一份」；② 用户读到的是**实际会生效的节点集合**（比原值更可诊断，
  原则 IV）；③ `"*"` 的**展开时机**差异上游已归 B13F1 X-2。
- **代价**：与上游 E-47 / E-48 的**形态**不同（语义等价）⇒ **登记 X-11 / P-03d**。
- **被否方案**：暴露原值 —— 需在产物里再存一份原值（两份载体），且与 `GraphSpec` 可能不同步。

### DR-8 · 能力面：6 方法全部显式未实现

- **决策**：6 个方法签名**逐字**对齐 L1 协议，方法体抛
  `NotImplementedError("… 尚未接线（由 B7F3 / B8F2 / B22F1 / B15F1 / B16F1 交付）")`。
- **理由**：B6F1 的未交付方法已用同一模式（`NotImplementedError` + 点名归属）；
  spec FR-004 要求「MUST NOT 静默不存在」。`get_state` 的「查不到 ⇒ 空值」是**已实现后**的语义
  （spec FR-011 的边界说明）。
- **判据**：`hasattr` 6/6；每个方法调用 ⇒ `NotImplementedError` 且消息含归属 feature 编号。

### DR-9 · 幂等与快照：每次 `compile()` 新产物

- **决策**：不缓存产物、不设 `compiled` 标志、不复刻上游的改图提示（X-5）。
- **理由**：E-42 实测上游两次 `compile()` 也是两个独立对象（**SAME**）；B6F1 已裁定不复制
  `compiled` 标志副作用。
- **判据**：连续两次 `compile()` ⇒ 改其中一份的私有状态不影响另一份（D2）。

### DR-10 · 条件边 plain mapping 的形状

- **决策**：`dict[str, tuple[dict[str, Any], ...]]`，内层 5 键逐字
  `{"branch", "path", "path_map", "targets", "route_channels"}`；顺序 = 登记顺序；
  `branch` 取自 `_ConditionalEdgeSpec.branch`。
- **理由**：B6F1 D-2 **逐字冻结**该形状；B8F1 只消费该映射 / L2 的 `GraphSpec.conditional_edges`，
  **MUST NOT** import `_stategraph`。
- **判据**：SC-010 的结构断言 + 顺序断言。

### DR-11 · 私有字段名冻结

- **决策**：`_spec` / `_builder_spec` / `_conditional_edges` 三个名字**是跨 feature 接口**。
- **理由**：上游用**公开**属性交接（`builder` / `channels` / `nodes` · E-31）；freegraph
  把这些保持私有（X-10），就必须**冻结字段名**，否则 B8F1 / B8F3 / B22F1 只能靠猜。
- **判据**：D2 断言三个属性存在且类型正确；`vars(compiled)` 的公开 key 集合恰为 8 项。

### DR-12 · `graph_core.py` 的守卫改探 `invoke`

- **决策**：`_facade_ready()` 先 `compile()` 最小合法图，再 `invoke()` 探桩；
  `NotImplementedError` ⇒ `False` ⇒ 退出码 **2**（保持）。
- **理由**：B7F2 后 `compile()` 不再抛 `NotImplementedError` ⇒ 若守卫仍探 `compile`，
  `graph_core` 会开始**真跑用例**并以「`invoke` 未实现」判失败（退出码 1）⇒
  `tests/runtime/test_acceptance_script.py` 与 `TestAcceptanceScriptsCanImportTheFacade` **变红**；
  而 `graph_core` 的**全部用例**都依赖 `invoke`（B7F3）⇒ M2 中途它本就**不该**真跑。
- **判据**：`graph_core` 仍输出 `[环境未就绪]` 且退出码 2；B7F3 落地后自动转为真跑（零改动）。

### DR-13 · 差分探针：`CompileScenario`

- **决策**：新增 `CompileScenario(name, verdict, note, fg, up)` + 归一化摘要比较：
  - 失败 ⇒ 比 `exc_type`（`SAME` 要求同名）；
  - 成功 ⇒ 比摘要 `(6 方法齐备, store 身份保留, store 警告条数, 断点元组, 产物类名可忽略)`。
- **理由**：既有 `BuilderScenario` 只比 OK/ERROR（构建阶段无可观察产物）；编译阶段**有产物**
  ⇒ 摘要必须**离散化**（不能比对象身份）。**不改**既有 runtime / builder 场景。
- **判据**：`D-75…D-91` 逐条 `ok=True`（上游缺席 ⇒ 空列表 ⇒ `skip`）。

### DR-14 · 既有测试口径：拆分不删

- **决策**：`TestNotWired` 拆为「compile 已接线」+「5 个构建方法仍未交付」；
  `NOT_WIRED_PATTERN` 收窄到仍适用的模式；保留 `vars(graph)` 的精确集合断言。
- **理由**：宪法 v1.11.0「冻结断言清单 MUST 实测化 + 拆分而不删」；spec「破冻结面」节已登记
  这 2 处测试口径更新。
- **判据**：`pytest tests/facade/test_facade.py` 绿；无删除的断言（只有改写与新增）。

### DR-15 · 文档：只做事实性更新

- **决策**：`README.md` 的 `StateGraph` 行、`harness/demo/README.md` 的软/硬断言清单、
  `graph.py` 的模块 docstring 同步；**符号面零变化**。
- **理由**：原则 X（文档合规）+ G19（兼容矩阵逐符号覆盖）。
- **判据**：`test_api_snapshot.py` 逐字节不变；G19 绿。

### DR-16 · 不越界

- **决策**：不实现 `invoke` / `stream` / 条件边求值 / 图导出 / checkpointer 与 store 的行为 /
  别名语义 / `defer` 屏障。
- **理由**：spec §8 的边界；越界会让「编译」与「执行」不可区分，且抢走下位 feature 的判据。
- **判据**：`compile()` 执行期用户函数调用计数 == 0；产物方法的异常消息点名归属 feature。

---

## 4. 实现落点（逐函数 / 逐类）

| 落点 | 文件 | 内容 |
|---|---|---|
| `CompiledGraph`（新类） | `_stategraph.py` | `__init__` / 8 个公开属性 / 3 个冻结私有字段 / 6 个能力面方法 / `_NOT_IMPLEMENTED` 消息表 |
| `StateGraph.compile`（改） | `_stategraph.py` | 入口形态门 → `_build_spec()` → END 过滤 → `GraphSpec` → 条件边映射 → 注入项 → `warnings` → 返回产物 |
| `_static_points`（新私有函数） | `_stategraph.py` | 断点容器形态门（DR-5） |
| `_graph_spec_from`（新私有函数） | `_stategraph.py` | `_BuilderSpec` → `GraphSpec`（END 过滤 · DR-3） |
| `_conditional_mapping`（新私有函数） | `_stategraph.py` | `_BuilderSpec.conditional_edges` → plain mapping（DR-10） |
| 模块 docstring | `_stategraph.py` | 补「B7F2 已交付编译；`invoke` 待 B7F3」 |
| 门面 docstring | `graph.py` | 删「compile 仍抛 NotImplementedError（归 B7F2）」 |

### 4.1 零改动清单

- `src/freegraph/runtime/**`（B7F1 / B4F1 / B5F1 / B10F1 / B13F1 的冻结面）
- `src/freegraph/contracts/**`（L1 · `CompiledGraph` 协议**不动**）
- `src/freegraph/graph.py` 的**导出面**（7 符号）
- `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`（**不新增源文件**）
- `tests/facade/_gatesupport.py`（同上）
- `tests/facade/test_api_snapshot.py` / `tests/contracts/**` / `tests/gates/**`
- `harness/demo/target.py`（只读基准）

---

## 5. 待核对项 / 已知边界

| # | 项 | 处置 |
|---|---|---|
| **K-1** | 上游为**每个节点**建 `branch:to:<node>`（E-43），freegraph 只为**条件边静态目标**建（B6F1 裁定 3 / FR-020） | **既有边界**（B6F1 已裁）；本 plan 把它并入 spec 的 **P-14 / X-8** 口径（同一「通道集合」分叉），**不新增**偏离编号 |
| **K-2** | 上游的 `channels` 含 `__start__` 与 `__pregel_tasks`（E-43）；freegraph 无 | 已由 **X-8**（`START` 通道）覆盖；`__pregel_tasks` 属 L2 的 send/fan-out 实现（B11F1），不在编译层 |
| **K-3** | 上游 `name` 缺省 `"LangGraph"`（E-33）；freegraph 缺省 `None`（B2F2 快照冻结 `name: str \| None = None`） | **SAME 接受面**；缺省值差异属签名冻结面（B2F2），不属本 feature ⇒ 在 **P-17** 的备注里注明（不改判词） |
| **K-4** | 上游 `debug` 缺省读环境变量（`get_debug()`） | **X-9**；freegraph 硬编码 `False`（B2F2 快照） |
| **K-5** | 上游对空图放行（E-44），freegraph V-3 拒绝 | **B6F1 的 D-72 / X-5** 已登记；编译期只是同一分叉的**再次可观察** ⇒ 本 feature **不新增差分行 / 偏离编号**（`D-86` 是「缺入口」，不是空图） |
| **K-6** | 上游 `compile()` 末尾 `return compiled.validate()`（`state.py:1401`） | freegraph 的「产物校验」= `GraphSpec` 构造期校验（无 Pregel 级 validate）⇒ 结构差异归 **X-1**（分层接缝） |
| **K-7** | 本 plan 的**证据脚本**尚未入库 | tasks 落一条：`harness/verification/B7F2/probe_upstream.py`（可复现 E-25…E-55） |

> **补记 P-1（plan 阶段 · 回修 spec）**：spec Q2 的括注写 `freegraph/_compiled.py`；
> 按 DR-1 落为**同模块** `src/freegraph/_stategraph.py`。**决策本身（L3 私有模块 · 类名 ·
> 不继承协议 · 不进门面）一字未改**，只修正**文件名**并补理由。另把 K-1 / K-3 的事实并入
> P-14 / X-8 / P-17 的备注（判词不变）。

---

## 6. 换版本复核清单

上游版本变化时 MUST 全部重跑并**改写版本号**：

1. 重跑 `harness/verification/B7F2/probe_upstream.py` ⇒ 核对 **E-25…E-55** 逐条；
2. 重核 §2 的**全部行号**（`state.py` / `pregel/main.py` / `channels/*` / `types.py`）；
3. 重跑差分 `D-75…D-91`（判词与摘要口径不变则应全绿）；
4. 重点复核：`compile()` 的断点容器失败**类型**（E-37/E-38/E-45/E-46 目前是拼接 `TypeError`）、
   `store=` 是否仍无警告、`compiled` 的公开属性集合（E-31）、以及「已编译后改图」是否仍是
   `logging`（E-49/E-50）。
