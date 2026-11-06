# feature 0 · 设计决策台账（research.md）

**功能块**: B2F1 · 5 个协议 + 5 个纯数据类
**Branch**: `b2f1-contracts-protocols` · **Date**: 2026-11-06
**输入**: [spec.md](./spec.md)（含 **13** 条澄清决策 · 两轮 clarify）

> 本文是 `/speckit.plan` 的 feature 0 产出：把 spec 里「已冻结但未定实现形态」的部分，
> 逐条落成**可执行的决策**，并记录被否掉的备选与理由。
> 依据纪律：每条决策的「依据」列给出来源标记（`本地路径:行号` / 契约编号 / 上游源码核实），
> 满足宪法原则 VIII。
>
> **上游版本**：核实环境 `langgraph 1.2.11` / `langchain-core 1.6.3`（与 Q8 §2 的实跑环境一致）。

---

## D-01 · 契约层的文件切分（3 → 6 个模块）

- **决策**：契约层由 3 个模块扩为 **6 个** —— 新增 `protocols.py`（5 个协议）、
  `graph.py`（`Graph` / `Node` / `Edge`）、`trace.py`（`Span` / `TraceQuery`）；
  `types.py` / `errors.py` **不动**；`__init__.py` 扩充为 18 个符号的再导出。
- **理由**：B1F1 的 plan 已预告「使后续 B2F1（4 类协议）可新增 `protocols.py` 而不与本层纠缠」；
  「图结构」与「可观测数据面」是两类关注点，分开后可独立演进（B22F1 只碰 `graph.py`，
  B18F1 / B19F1 只碰 `trace.py`）。`__init__.py` 只做再导出，公开符号面一目了然。
- **被否的备选**：① 全塞进 `types.py` —— 该文件将从 209 行涨到约 450 行，且「核心类型 /
  图结构 / 可观测」三族混排；② 每个类型一个文件（10 个）—— 文件过碎，且协议族被拆散；
  ③ `contracts/graph.py` 改名 `graphdata.py` / `structure.py` —— 避免与 B2F2 的
  `freegraph/graph.py`（公开门面）混淆；但二者路径不同（`freegraph.contracts.graph` vs
  `freegraph.graph`）**不构成导入冲突**，且同名更贴合上游
  `langchain_core.runnables.graph` 的心智模型。
- **依据**：spec FR-001…FR-010；B1F1 `research.md` D-01；B1F1 `plan.md` §结构决策。

## D-02 · 协议的实现机制（`typing.Protocol` + `runtime_checkable`）

- **决策**：5 个协议一律用 `typing.Protocol` + `@runtime_checkable` 定义，
  **不提供基类继承链**。
- **理由**：`runtime_checkable` 让用户**无需显式继承**即可满足协议（FR-007 的核心诉求）；
  「协议用 `typing.Protocol` 定义、实现用数据类」是本项目的架构纪律 **PD-1**；不提供基类
  是因为基类继承链会把可选 extra（pydantic / otel）的依赖渗进基础安装。
- **注意**：`runtime_checkable` 的判定**只比对方法名是否存在**、不比对签名 —— 「签名写错」
  判不出来，由**静态类型检查**承担（见 D-19）。
- **被否的备选**：① 抽象基类 `ABC` + `abstractmethod` —— 用户**必须继承**，违反 FR-007；
  ② 类型别名（`Callable[...]`）而非协议 —— 无法表达「一组方法」的结构化判定（`Store` /
  `Checkpointer` 各有 6 个方法），也无法作为注解表达「某个对象实现了这组方法」。
- **依据**：spec FR-007；`harness/prompts/guide.md` §3.5.4 PD-1；架构纪律（`guide.md` §3.5.2）。

## D-03 · `NodeFunc` 用 `__call__` 协议，而不是类型别名

- **决策**：`NodeFunc` 定义为含 `__call__` 的协议：
  `def __call__(self, state: StateDict) -> StateDict | Command | None: ...`
- **理由**：spec FR-001 要求「以协议定义节点函数契约」；用 `__call__` 协议而非
  `Callable[[StateDict], ...]` 别名，是为了让**协议面可被结构化判定**、且与另外 4 个协议
  同构（用户拿到的是一组统一的「协议」概念）。
- **已知局限（须写进 docstring）**：`isinstance(some_function, NodeFunc)` **几乎恒为真**
  ——因为任何可调用对象都自带 `__call__`。该判定的价值在于「**不是**可调用对象时判失败」，
  不在于「是不是合法的节点函数」；后者由**静态类型检查**承担。
- **被否的备选**：① `NodeFunc: TypeAlias = Callable[[StateDict], StateDict | Command | None]`
  —— 无法做结构化判定；② 协议 + `__call__` 但**不**标 `runtime_checkable` —— 用户失去
  「无需继承即可满足」的免注册表优势（FR-007 明确要求）。
- **依据**：spec FR-001 + 澄清 Q1（协议名 `NodeFunc`）；Q8 §3.4 C5（`f(state: dict) -> dict | Command`）。

## D-04 · 协议**纯抽象**：不提供任何默认实现

- **决策**：5 个协议的方法体**一律只有 `...`**（无 `pass`、无默认返回、无 `raise NotImplementedError`）。
- **理由**：若给协议方法提供默认实现，「只声明部分方法」的假实现会**静默通过**结构化子类型
  判定，把「缺实现」这一真实缺陷掩盖到运行时才暴露。spec FR-007 明确要求「纯抽象」。
- **被否的备选**：① `raise NotImplementedError` 作为默认体 —— 仍会让 `isinstance` 判真，
  掩盖缺实现（同上）；② 抽象方法 + `ABCMeta` —— 同 D-02 的备选 ①，用户必须继承。
- **落地**：门禁 **G10** 以 AST 断言「协议类体内**不得**出现非 `...` 的方法体」。

## D-05 · `Checkpointer` 的冻结粒度与 `Any` 占位

> **2026-11-06 第六轮复核修订（发起者裁定）**：**方法名与参数名已冻结**（参数名同属冻结面——
> 协议签名不写死参数名即无法实现，静态类型检查 SC-004 与对外文档都需要确切签名）；
> **挂起的只有返回类型 / 载荷形状**（仍归 B14F1）。逐字见 `data-model.md` §2.2。

- **决策**：冻结**方法集（恰 6 个）+ 语义 + 参数名 + 最小约束**；**返回结构与载荷形状挂起
  B14F1**，协议签名中尚未定形的部分以 `Any` 占位并在 docstring 注明挂起归属。
- **理由**：spec 澄清 Q5 裁定「只冻结方法名 + 语义 + 最小约束」——现在钉死载荷形状，
  后期大概率返工；而 B14F1（内存）/ B15F1（SQLite）两个后端一起给出经验后再定形状更准。
  本 feature 仍守住「六方法齐全」这个**可判定**判据（SC-007）。
  **（参数名的例外 · 2026-11-06 复核）**：**方法名与参数名**必须冻结——协议签名不写死参数名
  即无法实现（下游 B14F1 / B15F1 各自实现时改名成本高），且静态类型检查（SC-004）与
  对外文档都需要确切签名。
- **最小约束（四条，已冻结）**：① 方法集合恰为六个；② **方法名与参数名**（`config` /
  `thread_id` 等，逐字见 `data-model.md` §2.2）；③ 读写面 MUST 能承载**检查点标识**
  （C23 要求 span 必带它）；④ 载荷 MUST 为**纯数据**（可 JSON 序列化）。
- **被否的备选**：① 完整签名逐字冻结（**含返回类型**）——「形状错了改不动」；
  ② 新增专属载荷数据类把形状一次定死 —— 公开面 +1、且改不动。
- **依据**：spec FR-002 + 澄清 Q5（+ 第六轮复核补充）；Q8 §3.4 C19；上游方法集核实
  `langgraph/checkpoint/base/__init__.py:239`（`get_tuple`）/ `:253`（`list`）/ `:277`（`put`）/
  `:300`（`put_writes`）/ `:320`（`delete_thread`）/ `:692`（`get_next_version`）。

## D-06 · `Store` 的命名空间形态挂起 v2（参数以 `Any` 占位）

> **2026-11-06 第六轮复核修订（发起者裁定）**：**方法名与参数名已冻结**（`namespace` /
> `key` / `value` / `namespace_prefix` / `prefix` / `ops`）；**挂起的只有命名空间的载体类型与
> `batch` 的操作表示**（仍归 v2）。
> **参数名逐字镜像上游（兼容锚点 · 2026-11-06 第六轮复核核实）**：`search` 的首参名为
> **`namespace_prefix`**、`list_namespaces` 的首参名为 **`prefix`**——**上游 LangGraph
> 1.2.11 的原样命名**（核实 `langgraph/store/base/__init__.py`：
> `search(self, namespace_prefix, /, …)` / `list_namespaces(self, *, prefix=None, …)`），
> freegraph 刻意逐字镜像（D-09 的「保留上游核心名作兼容锚点」原则）⇒ **MUST NOT** 为
> 「一个概念一个名字」而改名（① 改之即偏离上游；② 两者连**参数形态**都不同——
> `search` 的是位置参数、`list_namespaces` 的是关键字参数，本就不是同一个参数位）。
> **上游的这个命名分歧在此显式登记**（宪法原则 VIII 的证据纪律）。

- **决策**：冻结**方法集（恰 6 个）+ 参数名 + 寻址语义（命名空间 = 层级路径，键 = 字符串）
  + 取值为纯映射**；命名空间的**具体载体形态**（层级元组 vs 点分字符串）与 `batch` 的**操作表示**
  挂起 v2，协议签名中以 `Any` 占位。
- **理由**：spec 澄清 Q7 裁定「只冻结语义层」——v1 无任何实现会用到这个形状，此刻定死只有
  返工风险、没有收益；「命名空间是层级路径」这一层语义已足够让 freechain 做设计输入。
- **上游的双口径（记录在案）**：上游长期存储接口用**层级元组**
  （`langgraph/store/base/__init__.py:71` `namespace: tuple[str, ...]`），而检查点的命名空间
  用字符串（`langgraph/checkpoint/base/__init__.py:800` `checkpoint_ns`）——freegraph 暂不
  选边，待有实现经验再定。
- **被否的备选**：① 直接冻结为层级元组 —— 现在选边等于替 v2 做决定；② 冻结为点分字符串 ——
  同样选边，且与上游两套口径都不完全同构。
- **依据**：spec FR-004 + 澄清 Q7；Q8 §3.4 C20；宪法原则 VII（`Store` v1 无实现、B17 已砍）。

## D-07 · `TraceSink` 的回调载荷语义（不可变 `Span` + 同 `id` 新实例）

- **决策**：`Span` **不可变**；`on_span_start` 收到「`end_time` 为空」的实例；
  `on_span_end` 收到**同 `id`、`end_time` 已填的新实例**；两次回调**按 `id` 配对**；
  开始时收到的实例 MUST NOT 在事后被改写。
- **理由**：spec 澄清 Q9 裁定。守住纯数据纪律（与 B1F1 的「不可变记录 + 字段级相等语义」
  一致）；「开始时的快照不会被事后改写」是**可断言**的性质（B19F1 的嵌套与配对测试依赖它）；
  配对复用已冻结的 `Span.id` 字段，不新增机制。
- **连带影响**：`current_span()` 返回的「当前 span」是**进行中**的实例（`end_time` 为空），
  而 `on_span_end` 收到的是**完成版**——二者同 `id`、非同实例。B19F1 的「内层结束后外层
  恢复为当前 span」按 `id` 或按实例栈均可实现，**本 feature 不规定**该实现细节。
- **被否的备选**：① `Span` 可变、结束时就地补 `end_time` —— 接收端最省事，但破坏不可变
  纪律，且「开始时的快照」会被事后改写；② `on_span_end(span, end_time)` 多带一个参数 ——
  与「三方法 + 载荷语义」的口径不齐，且结束时刻本就是 span 的字段；③ 不规定、整体挂起 B19F1
  —— B19F1 会踩在未冻结面上，且本 feature 是契约冻结落点。
- **依据**：spec FR-003 / FR-010 + 澄清 Q9；Q8 §3.4 C23 / C24。

## D-08 · `CompiledGraph` 冻结返回类别（**参数名已改判为冻结为占位名**）

> **B2F1 复核修订（2026-11-06 · 文档一致性复核）**：本条的「参数名」部分**已改判** ——
> **参数名按 `data-model.md` §2.5 的逐字签名冻结为占位名**（`input` / `config` /
> `stream_mode` / `xray` / `as_node`），**行为细节**仍挂起各实现 feature。
> **改判理由**：协议签名不写死参数名即**无法实现**——静态类型检查（SC-004）与对外文档
> 都需要确切签名，且四个下游 feature（B7F3 / B8F2 / B15F1 / B16F1）各自实现在即，
> 彼时再改即成「契约修订」。下游确需改名者走**契约修订**流程。
> 原「参数名一旦公布即成契约，此刻定名易冲突」的顾虑由「占位名 + 修订流程」消解。
> 已同步：spec Q8 / FR-005 / Assumptions · data-model §2.5 / §6 ·
> public-api §1.1 / §3 / §5 · tasks T039。**冻结面的其余部分未变。**

- **决策（原始）**：冻结六个方法的**返回类别** —— `invoke` → 完整状态字典；`stream` → 事件迭代器
  （元素为纯数据字典）；`get_graph(xray=False)` → `Graph`；`get_state` → 状态快照
  （**查不到返回空值**，不抛异常）；`get_state_history` → 状态快照迭代器；
  `update_state(values, as_node=None)` → 状态快照。**参数名与实现细节挂起**
  > **⚠️ 此行的签名简写已被上方的「B2F1 复核修订」覆盖**：参数名**已冻结为占位名**，且
  > **完整签名含 `config` 且顺序在前** —— 逐字见 `data-model.md` §2.5：
  > `update_state(config, values, as_node=None)`。实现时**以 §2.5 为准**
  > （本行仅保留为**原始决策记录**）。
  （`invoke` → B7F3、`stream` → B8F2、状态查询 → B15F1、`update_state` → B16F1）。
- **理由**：spec 澄清 Q8 裁定。返回类别是 freechain 写适配层的**最低必需信息**（再少就写
  不了）；参数名一旦公布即成契约，而各方法分别由四个下游 feature 实现，此刻定名易冲突。
- **「查不到返回空值」的取舍**：上游 `get_state` 在无快照时返回的是一个「空快照」而非异常
  （`langgraph/pregel/main.py:1392`）——freegraph 与之同构，用户脚本不必到处兜异常；
  代价是「查不到」与「空状态」在返回值上同形，须靠 `next` 为空来分辨。
- **被否的备选**：① 查不到时抛异常 —— 用户脚本到处要 `try/except`，与本项目「不抛无谓异常」
  的基调不符；② 完整签名逐字冻结 —— 同 D-05 的备选 ①。
- **依据**：spec FR-005 + 澄清 Q8；Q8 §3.4 C10 / C11 / C12 / C13；上游核实
  `langgraph/pregel/main.py:845`（`get_graph`）/ `:1392`（`get_state`）/ `:1480`
  （`get_state_history`）/ `:2515`（`update_state`）/ `:2655`（`stream`）/ `:3783`（`invoke`）。

## D-09 · 图结构数据类的字段清单（对齐上游核心名，砍掉 `data`）

- **决策**：字段清单**逐字冻结**为 ——
  `Graph.nodes: tuple[Node, ...]` / `Graph.edges: tuple[Edge, ...]`；
  `Node.id: str`（节点名）/ `Node.name: str | None = None`（别名，缺省在 `__post_init__`
  **归一为 `id`** —— B2F1 复核已统一口径；逐字见 `data-model.md` §3.1 与 spec FR-006）/
  `Node.metadata: Mapping[str, Any]`（缺省 `field(default_factory=dict)`）；
  `Edge.source: str` / `Edge.target: str` / `Edge.conditional: bool` /
  `Edge.condition: str | None`（条件名）。
- **理由**：spec 澄清 Q4 裁定。保留上游 `langchain_core.runnables.graph` 的**核心字段名**
  （`id` / `name` / `source` / `target` / `conditional`）作兼容锚点；**砍掉** `data`
  ——上游那里它装的是可调用对象 / pydantic 对象（`langchain_core/runnables/graph.py:72`
  `data: Stringifiable | None`、`:102` `data: TypeBaseModel | RunnableType[Any, Any] | None`），
  freegraph 的纯数据纪律**装不下**，留一个永远为空的字段没有意义。
- **容器用不可变元组**而非上游的 `dict[str, Node]` / `list[Edge]`：与「不可变记录」自洽，
  且避免 `nodes` 是 dict 时「顺序不保证」的额外语义需要解释。
- **被否的备选**：① 完全对齐上游字段（含 `data` + dict 容器）——`data` 装不下对象，
  且 dict 容器引入顺序语义；② 只冻结语义、字段名留到 B22F1 ——冻结面留到那时，
  本 feature 的「契约冻结」只覆盖到语义层。
- **依据**：spec FR-006 + 澄清 Q4；上游核实 `langchain_core/runnables/graph.py:65`（`Edge`）/
  `:95`（`Node`）/ `:255`（`Graph`）；Q8 §3.4 C13 / C25。

## D-10 · `Node.name` 的缺省归一（`__post_init__` 填成 `id`）

- **决策**：`Node.name` 的缺省值为 `None`，但在 `__post_init__` 中**归一为 `id`**
  （`object.__setattr__`，因 `frozen=True`）；因此 `node.name` **恒为字符串**，
  未给别名时等于节点名。
- **理由**：spec 澄清 Q4 的措辞是「`name`（别名，**缺省同 id**）」——「缺省同 id」是**可断言**
  的行为，若留 `None` 则读取方每次都要写 `node.name or node.id`，把「缺省语义」的责任
  推给每一个调用方。归一后该语义由类型自己保证。
- **与 B1F1 的同构做法**：`RunConfig.__post_init__` 亦用 `object.__setattr__` 做容器归一
  （B1F1 `research.md` D-04 / D-19）——同一模式，零新机制。
- **被否的备选**：① 留 `None` + 属性 `display_name` 回落 —— 把「缺省语义」推给调用方；
  ② 用 `__post_init__` 抛错要求显式给别名 —— 对「只有一个名字」的常见图过度约束。
- **依据**：spec FR-006 + 澄清 Q4；B1F1 `research.md` D-04 / D-19。

## D-11 · `Span` 的 11 字段清单与字段形态

- **决策**：`Span` 冻结 11 字段 —— `id`（span 唯一标识）/ `name`（span 名）/
  `attributes`（属性，命名对齐 `gen_ai.*`）/ `parent`（**父 span 的 `id`**，无父为空）/
  `start_time` / `end_time`（**UTC ISO-8601 字符串**）/ `context`（附加上下文）
  + **必带四项** `thread_id` / `run_id` / `node`（节点名）/ `checkpoint_id`。
- **理由**：spec 澄清 Q6 裁定。三个 `_id` 名字是宪法原则 VII 与 Q8 §3.4.1 已写死的
  （`thread_id` 会话级 / `run_id` 运行级 / `checkpoint_id` 检查点级）；补 `id` 是因为
  「父级」必须靠**标识**引用——放对象引用则 JSON 序列化落地不了，C27 第 ③ 条作废；
  `node` 与既有 `Node.id`（节点名）对齐，避免同一概念两个词。
- **`parent` 为标识字符串、时间为 ISO 字符串**是 C27「JSON 可序列化」的**前提**：
  span 会被落盘（JSONL / SQLite），故其字段不得含对象引用或非字符串时间。
- **被否的备选**：① 「节点名」字段叫 `node_name` —— 更自解释，但与 `Node.id` 割裂；
  ② 父级放**对象引用** —— 不可 JSON 序列化，C27 作废；③ 只冻结必带四项，其余留给 B18F1
  —— 公开类型半成品，后续极可能再动冻结面。
- **依据**：spec FR-010 + 澄清 Q6；Q8 §3.4.1 ②（C23 字段约定）；立项书 §5.4 DF4。

## D-12 · `TraceQuery` 的 5 字段清单

- **决策**：`TraceQuery` 冻结 5 字段 —— `run_id` / `thread_id` / `node`（**与 span 侧同名**）
  + `start_time` / `end_time`（时间范围，**UTC ISO-8601 字符串**，与 span 的起止字段同名）；
  五字段**全部可空、可组合**，全空 = 取全部。
- **理由**：spec 澄清 Q11 裁定。一个概念在项目里只有一个名字，是本项目「术语纪律」最省心的
  做法；时间字段名与 span 侧同名后，用户从 span 上读到的时间可直接当过滤条件用，零转换。
- **被否的备选**：① `since` / `until` —— 与 span 侧 `start_time` / `end_time` 割裂；
  ② 时间范围合并为单个 `time_range` 元组 —— 组合过滤的表达力下降（无法表达「只给起点」）。
- **依据**：spec FR-009 + 澄清 Q11；Q8 §3.4.1 ①（C27 查询过滤器：`run_id` / `thread_id` /
  时间范围 / 节点名，四者可组合）。

## D-13 · 数据类的哈希语义（统一不可哈希）

- **决策**：`Graph` / `Node` / `Edge` / `Span` **一律不可哈希**（`__hash__ = None`），
  只保证**字段级相等**；`TraceQuery` 保持 dataclass 默认（**可哈希**——其五字段全为标量）。
- **理由**：spec 澄清 Q12 裁定。根因是**含映射字段**（`metadata` / `attributes` / `context`），
  哈希必然在运行时抛错；统一口径（四个都不可哈希）比「有的能有的不能」更易文档化。
- **实现要点（必须显式写 `__hash__ = None`）**：`Edge` 的四字段全是标量，
  `@dataclass(frozen=True)` 会**自动生成** `__hash__` → 与「统一不可哈希」冲突。
  CPython `dataclasses` 的 `_hash_action` 表对「类体中**显式**定义 `__hash__`」的组合
  **不做覆盖**（`(False, True, True, True) → None`），故在类体写 `__hash__ = None` 即可。
- **`TraceQuery` 可哈希不是缺陷**：它本就没有映射字段；记在案以免读者以为漏了。
- **被否的备选**：① 只让含映射字段的 `Node` / `Span` 不可哈希 —— 口径不统一；
  ② 为了可哈希而把映射字段改成不可变映射 —— 推翻 D-09 / D-11 刚定下的字段清单。
- **依据**：spec FR-006 / FR-010 + 澄清 Q12；B1F1 `research.md` D-02（「`frozen=True` 会自动
  生成 `__hash__`，但装着 dict 时哈希会抛 `TypeError`」的同源判断）；CPython `dataclasses` 源码。

## D-14 · `Span` 的不可变性

- **决策**：`Span` 用 `@dataclass(frozen=True, slots=True, kw_only=True)`；
  `attributes` / `context` 在 `__post_init__` 中**浅拷贝**为自身持有的新映射。
- **理由**：与 D-07 的回调语义配套（结束由新实例承载 ⇒ 类型必须不可变）；与 B1F1 的
  「不可变记录 + 浅拷贝」口径一致（`RunConfig.metadata` / `StateSnapshot.metadata` 同款）。
- **浅拷贝而非深拷贝**：与 B1F1 D-19 同口径——深拷贝会让嵌套容器的复制成本随数据量放大，
  且与「只读映射」声明不符。
- **被否的备选**：① 不拷贝（直接持调用方的 dict）—— 调用方事后修改原 dict 会静默改到
  已构造的「不可变记录」，正是 B1F1 用拷贝规避的缺陷；② 深拷贝 —— 成本与语义都不必要。
- **依据**：spec FR-010 + 澄清 Q9；B1F1 `research.md` D-19。

## D-15 · C27 不落第五个协议

- **决策**：本 feature 只落 C27 的**请求 / 返回纯数据结构**（`TraceQuery` + 结果集合 = span
  列表）+「存储与查询 MUST 经由同一协议、后端可替换」的**约束文字**；**不定义**「存储与查询」
  协议本身。冻结对照表相应条目标「数据已冻结 / 协议面挂起（B20F1）」。
- **理由**：spec 澄清 Q3 裁定——**协议面此刻定死，若后续 feature 增多导致要改，就是大面积
  返工**；把方法集留到有后端实现经验（B20F1 / B20F2）之后一次定准，风险最低。
- **被否的备选**：① 一并落第五个协议（写入 + 查询方法面）——公开面 +1、方法集此刻定死；
  ② 只落写入侧、查询侧归 B20F2 ——违背 C27「同一协议」的字面要求。
- **依据**：spec FR-009 + 澄清 Q3；Q8 §3.4.1 ①（C27 五条）；宪法原则 VII（契约清单以 Q8
  为唯一权威，MUST NOT 擅自增删条目——**挂起不等于增删**）。

## D-16 · 公开符号面的维护方式（spec 列新增、完整清单在 `public-api.md`）

- **决策**：spec 内**逐字列出本 feature 新增的 10 个符号**；**完整清单（18 个）的唯一权威**
  为 `specs/b2f1-contracts-protocols/contracts/public-api.md`，并由该文件声明**取代**
  B1F1 的同名文件（后者作为历史快照保留，仅顶部加一行取代提示）。
- **理由**：spec 澄清 Q10 / Q13 裁定。spec 自包含地写死「新增了什么」（冻结记录可直接引用），
  而**完整清单不复制**进 spec ——避免两处手工维护漂移（沿用 B1F1 FR-015 的口径：完整清单的
  唯一手工维护点是 `contracts/public-api.md`）。
- **被否的备选**：① spec 里列完整 18 个 ——两处手工同步、易漂移；② 只用类别描述 ——
  实现时增删符号不会被任何判据发现。
- **落地**：门禁 **G7** 断言 `__all__` **集合相等**为 18 个；门禁 **G12** 断言「仓库内自称
  权威的公开符号清单文件数 == 1」。
- **依据**：spec FR-012 / FR-013 + 澄清 Q10 / Q13；B1F1 `research.md` D-17 / D-20。

## D-17 · 四份交付物的落盘位置

- **决策**：公开符号清单（18 个）+ C1–C27 冻结对照表 + 冻结记录**合并**落
  `specs/b2f1-contracts-protocols/contracts/public-api.md`；架构门禁契约落
  `contracts/architecture-gates.md`；人工验证记录落 `harness/verification/B2F1/manual-verification.md`。
- **理由**：spec 澄清 Q13 裁定——不新增目录结构、与 B1F1 的交付形态对称；且「符号面 +
  冻结状态」放同一文件最便于审计（对照表每一行都能指向同文件里的符号定义）。
- **被否的备选**：① 三份文件分开（`public-api.md` / `contract-freeze.md` / …）——多一个文件
  要维护；② 人工验证记录也放 feature 目录 ——与仓库现行惯例（`harness/verification/`）不同。
- **依据**：spec FR-013 / FR-014 + 澄清 Q13；`harness/verification/README.md` 的目录约定。

## D-18 · 门禁的扩展（G7 8→18 · G8 按清单 · 新增 G10–G13）

> **B2F1 第二轮复核修订（2026-11-06 · 文档一致性复核）**：本条的三处口径已收窄——
> ① **G7** 不再是「恰 8 个 → 恰 18 个」的**一次性替换**，而是**分两段落地**：
> **子集段**（始终启用，抓「偷偷多导出」）在 Foundational 落地、**集合相等段**
> （抓「漏导出」）在 18 个符号全部导出后启用——理由：既有 G7 硬编码「恰 8 个」，
> 自第一次追加导出起**必然失败**，一次性替换的排期落在导出之后会让 US1–US4 全程红。
> ② **G2 / G4 的扫描范围**改为**两档**：内部 import 档扫 `src/**` + `tests/**`；
> 第三方 import 档**只扫 `tests/contracts/fixtures/**`**（其余测试文件豁免 `pytest`）——
> 理由：一刀切到「任何非标准库顶层包即违规」会让门禁因 `import pytest` **恒失败**。
> ③ **G8 的「行内上游来源行号」只对「有上游同名符号」者成立**——`NodeFunc` / `TraceSink` /
> `Span` / `TraceQuery` 无上游同名符号，写「无上游对应」+ 契约条目号。
> 已同步：architecture-gates G2 / G4 / G7 / G8 · spec FR-017 / SC-021 · plan（风险表 +
> 第二轮复核记录）· public-api §1.1 / §4 / §5 · tasks T006 / T008 / T032 / T033 / T040 / T041 / T054 / T056。

- **决策**：继承 B1F1 的 **G1–G9**；修改 **G7**（公开符号面由「恰 8 个」改为「恰 18 个」）；
  **G8** 的「兼容矩阵覆盖全部公开符号」改为「覆盖 `public-api.md` 所列符号」；
  新增四条 ——
  - **G10 协议纯抽象**：协议类体内**不得**出现非 `...` 的方法体（AST 断言）；
  - **G11 结构化子类型判定可用**：每个协议可做 `isinstance` 判定，且**完整实现判真、
    缺任一方法判假**（运行时证据）；
  - **G12 公开符号面唯一权威**：仓库内自称权威的公开符号清单文件数 == 1；
  - **G13 纯数据纪律**：四个数据类的字段注解**不得**含可调用 / 对象类型（不得有装对象引用的字段）。
- **理由**：B1F1 的门禁是「架构红线」的自动化；B2F1 新增了「协议纯抽象」「符号面唯一权威」
  「纯数据纪律」三条**本 feature 特有**的不变量，若不落成断言，它们会在下一次改动里悄悄
  失守——而这三条正是本 feature 全部价值的所在。
- **被否的备选**：① 全部塞进 G2（AST 扫描）——G2 的语义会失焦，报错信息变得不可读；
  ② 只在 spec 里写「须如此」——不可自动判定，等于没有门禁。
- **依据**：spec FR-007 / FR-012 / SC-017 / SC-019 / SC-020；B1F1 `contracts/architecture-gates.md`
  （G1–G9 的形态与判定方式）。

## D-19 · 静态类型检查的可选工具与 skip 口径

- **决策**：SC-004「通过静态类型检查」以 **mypy**（**开发期工具，不进发行包 `dependencies`**）
  对 `tests/contracts/fixtures/external_impl.py` 执行；**本机未安装 mypy 时该用例 `skip`**
  （不失败），并在人工验证记录中标注——口径与 G3 依赖闭包「需隔离环境才真跑」一致。
- **理由**：mypy 是开发期工具，与 pytest 同性质（**不进发行包**），不违反「基础安装零依赖」；
  而「缺工具就失败」会让本地开发无谓受阻，「缺工具就静默通过」则会让判据名存实亡 ——
  `skip` + 人工记录是两者之间的诚实口径。
- **兜底断言（无 mypy 也能跑）**：以 `typing.get_type_hints` 解析协议与夹具的方法注解，
  逐项断言**方法名与参数名**一致 —— 这不是静态类型检查，但能挡住「签名写错」这类
  最常见的失守；**SC-004 的「静态类型检查」仍以 mypy 为准**，兜底断言不替代它。
- **被否的备选**：① 把 mypy 加进 `dependencies` ——违反「基础安装零依赖」；② 完全不引入静态
  类型检查、只靠 `get_type_hints` ——SC-004 的字面要求落空。
- **依据**：spec SC-004；宪法「依赖白名单」（必装 = 无；开发期工具不进发行包）；
  B1F1 `plan.md` 的「开发期依赖不进发行包」口径。

## D-20 · 外部实现夹具的形态与位置

- **决策**：夹具独立成文件 `tests/contracts/fixtures/external_impl.py`，
  **只 import `freegraph.contracts`**（不 import 任何 freegraph 内部模块），**同时实现**
  `Checkpointer` / `TraceSink` / `Store` 三个协议。
- **理由**：SC-004 要求「一个**零内部依赖**的夹具能同时实现三个协议」——若夹具写在测试文件里，
  会与 pytest 的导入机制、同目录 import 混在一起，「零内部依赖」这件事**不可被静态扫描判定**；
  独立文件后，G2 的扫描范围覆盖 `tests/` 即可判定。
- **被否的备选**：① 夹具写在 `test_protocols.py` 内 ——「零内部依赖」不可静态判定；
  ② 三个夹具各一文件 ——SC-004 要求「同时实现」，拆开反而验证不了「三者互不冲突」。
- **依据**：spec SC-004；`harness/prompts/guide.md` §3.5.3（协议交互全景图）。

---

## 挂起项交接表（Phase 0 汇总）

> 下表是本 feature **明确不做**、且**已指定归属**的事项——它们不是「未决问题」，
> 而是**已决策的挂起**（spec 的冻结对照表据此逐条标注）。

| # | 挂起项 | 归属 feature | 依据 |
|---|---|---|---|
| 1 | 检查点的快照元组 / 待写入数据的**具体字段形状 + 返回类型** | **B14F1** | spec FR-002 + 澄清 Q5（+ 第六轮复核补充）；C19 |
| 2 | `Store` 命名空间的**具体载体形态**与 `batch` 的**操作表示** | **v2**（B17 已砍，契约仍冻结） | spec FR-004 + 澄清 Q7；C20 |
| 3 | `stream()` 的 **mode 枚举全集** | **B8F2** | spec FR-005 + 澄清 Q8；C12 |
| 4 | `CompiledGraph` 各方法的**行为细节与实现**（**参数名已冻结为占位名** · D-08 复核修订） | **B7F3 / B8F2 / B15F1 / B16F1** | spec FR-005 + 澄清 Q8 |
| 5 | 「存储与查询」协议的方法集（写入 / 查询） | **B20F1** | spec FR-009 + 澄清 Q3；C27 |
| 6 | **span 的生产行为**（节点 / 工具 / 模型三级） | **B18F1** | spec FR-010 + 澄清 Q2；C23 / DF4 |
| 7 | **`TraceSink` 的接入与 `current_span()` 的嵌套实现** | **B19F1** | spec FR-003 + 澄清 Q7 / Q9；C24 |
| 8 | **子图**实现（C26）——v1 只保 `get_graph(xray=)` 签名兼容 | **v2** | spec Out of Scope；C26 |
| 9 | **`mermaid` 文本导出 / PNG 渲染** | **B22F1 / B23F1** | spec Out of Scope；C14 / C15 |
| 10 | **公开 API 门面** `freegraph/graph.py` | **B2F2** | spec Out of Scope |
| 11 | **兼容矩阵与 `THIRD_PARTY_NOTICES` 的补全与定稿** | **B24F1** | 宪法原则 X；B1F1 FR-016 的移交口径 |
| 12 | **架构断言接入 CI 流水线** | **B3F1** | B1F1 的既有移交口径 |
| 13 | **`Send` / `interrupt` 的导出** | **v2**（`Send` 归 B11F1、`interrupt` 归 B10F1） | spec Out of Scope；C18 / C17 |

---

## 决策索引（速查）

| # | 决策 | 落点 |
|---|---|---|
| D-01 | 契约层 3 → 6 个模块（`protocols.py` / `graph.py` / `trace.py`） | 目录结构 |
| D-02 | 协议 = `typing.Protocol` + `runtime_checkable`，无继承链 | 协议面 |
| D-03 | `NodeFunc` = 含 `__call__` 的协议 | 协议面 |
| D-04 | 协议**纯抽象**（方法体只有 `...`） | 协议面 · G10 |
| D-05 | `Checkpointer` 冻结方法集 + 语义 + **参数名**；返回类型 / 载荷形状以 `Any` 占位（挂起 B14F1） | 协议面 |
| D-06 | `Store` 冻结方法集 + 语义 + **参数名** + 寻址语义；命名空间载体形态挂起 v2 | 协议面 |
| D-07 | `TraceSink` 回调载荷 = 不可变 `Span` + 同 `id` 新实例 | 协议面 · G11 |
| D-08 | `CompiledGraph` 冻结返回类别；**参数名按 §2.5 冻结为占位名**（2026-11-06 复核修订），行为细节挂起 | 协议面 |
| D-09 | 图结构字段逐字冻结（砍 `data`、元组容器） | 数据模型 |
| D-10 | `Node.name` 缺省归一为 `id` | 数据模型 |
| D-11 | `Span` 11 字段（`parent` 为标识、时间为 ISO 字符串） | 数据模型 |
| D-12 | `TraceQuery` 5 字段（与 span 侧同名） | 数据模型 |
| D-13 | 四个数据类**统一不可哈希**（`Edge` 显式 `__hash__ = None`） | 数据模型 · G13 |
| D-14 | `Span` 不可变 + 映射字段浅拷贝 | 数据模型 |
| D-15 | C27 不落第五个协议 | 范围 |
| D-16 | spec 列新增 10 个，完整清单在 `public-api.md` | 公开面 · G7 / G12 |
| D-17 | 四份交付物的落盘位置 | 交付物 |
| D-18 | 门禁 G1–G13（G7 8→18 · G8 按清单 · 新增 G10–G13） | 门禁 |
| D-19 | 静态类型检查用 mypy（可选工具 + `skip` 口径） | 测试 |
| D-20 | 外部实现夹具独立成文件、零内部依赖 | 测试 · G2 |
