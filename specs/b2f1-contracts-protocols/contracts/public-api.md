<!-- authority: yes -->

# 公开 API 冻结契约（public-api.md）

**功能块**: B2F1 · 5 个协议 + 5 个纯数据类 · **Date**: 2026-11-06
**权威来源**: [spec.md](../spec.md)（FR-001…FR-017 + **13** 条澄清决策）·
[research.md](../research.md)（D-01…D-20）· [data-model.md](../data-model.md)
**契约性质**: **冻结面** —— 本文件列出的符号名、字段名、字段类型、方法集、语义
一经落地，后续 30 个 feature 全部引用；改名成本极高

> **📌 取代声明**：本文件**取代**
> `specs/b1f1-contracts-core/contracts/public-api.md` —— 后者作为 **B1F1 的历史快照**保留
> （其 8 符号清单与类型冻结记录**逐字不改**），但**不再是公开符号面的权威**。
> 仓库内自称权威的公开符号清单文件**恰为 1 个**（门禁 **G12** 断言）。

---

## 0. 公开符号面

```python
from freegraph.contracts import (
    # ── B1F1 已冻结的 8 个（历史快照见 b1f1-contracts-core/contracts/public-api.md）──
    StateDict,             # 状态字典（类型别名）
    Command,               # 命令原语
    StateSnapshot,         # 状态快照
    RunConfig,             # 运行配置
    FreegraphError,        # 内核异常基类
    InvalidUpdateError,    # ├ 节点返回了 schema 中不存在的 key
    GraphRecursionError,   # ├ 递归超限
    GraphInterrupt,        # └ 节点主动中断

    # ── B2F1 新增的 10 个（本 feature 的交付面）──
    NodeFunc,              # 节点函数协议（Callable[[StateDict], StateDict | Command | None]）
    Checkpointer,          # 检查点协议（6 方法）
    TraceSink,             # 可观测接收端协议（3 方法）
    Store,                 # 长期存储协议（6 方法 · v1 无实现）
    CompiledGraph,         # 编译产物协议（6 方法）
    Graph,                 # 图结构
    Node,                  # 图节点元素
    Edge,                  # 边元素
    Span,                  # 可观测事件载体
    TraceQuery,            # trace 查询请求（C27 数据面）
)
```

**恰好 18 个**。不多、不少：

> 本节是**公开符号面的唯一手工维护点** —— spec / plan / tasks / `README.md` 兼容矩阵中的同款
> 清单均以本节为准（spec FR-012）。

- `__all__` **集合相等**断言为这 18 个名字（集合断言才能抓住「偷偷多导出一个」）。
- 契约层**不得**出现名为 `Send` / `interrupt` 的公开符号（v2；归 B11F1 / B10F1）。
- `import freegraph.contracts` **不得**连带加载任何 freegraph 内部层模块。

---

## 1. 冻结面速查

### 1.1 五个协议（**纯抽象**：方法体只有 `...`；`runtime_checkable`；无继承链）

| 协议 | 方法集（**恰为**） | 签名摘要 | 契约 |
|---|---|---|---|
| `NodeFunc` | `__call__` | `(state: StateDict) -> StateDict \| Command \| None` | C5 / C6 |
| `Checkpointer` | `get_tuple` / `list` / `put` / `put_writes` / `delete_thread` / `get_next_version` | **方法名与参数名已冻结**（逐字见 `data-model.md` §2.2）；**返回类型占位**（`Any`）——**载荷形状挂起 B14F1** | C19 |
| `TraceSink` | `on_span_start` / `on_span_end` / `current_span` | `(span: Span) -> None` ×2；`() -> Span \| None` | C23 / C24 |
| `Store` | `get` / `search` / `put` / `delete` / `list_namespaces` / `batch` | **方法名与参数名已冻结**（逐字见 `data-model.md` §2.4）；命名空间为层级路径、**载体形态挂起 v2** | C20 |
| `CompiledGraph` | `invoke` / `stream` / `get_graph` / `get_state` / `get_state_history` / `update_state` | 返回类别已冻结；**参数名按 `data-model.md` §2.5 冻结为占位名**（B2F1 复核裁定） | C10 / C11 / C12 / C13 |

**各协议的上游来源**（宪法原则 VIII · 证据门禁；FR-014 要求「协议语义与上游同名能力的
对应关系 MUST 附来源」）——
**核实环境：`langgraph 1.2.11` / `langchain-core 1.6.3`**（见 `research.md` 头部；
行号以该版本为准，引用时 MUST 标注版本）：

| 协议 | 上游来源（`路径:行号`） |
|---|---|
| `NodeFunc` | **无上游同名符号**（上游以普通 `dict` 调用节点函数，无同名协议类）· 契约 **C5 / C6**；最接近的上游物：`langgraph/graph/state.py`（Q8 §3.2.2 · E4） |
| `Checkpointer` | `langgraph/checkpoint/base/__init__.py:239`（`get_tuple`）/ `:253`（`list`）/ `:277`（`put`）/ `:300`（`put_writes`）/ `:320`（`delete_thread`）/ `:692`（`get_next_version`） |
| `TraceSink` | **无上游同名符号**（上游无 span 推送协议）· 契约 **C23 / C24**；最接近的上游物是 LangChain 的 `callbacks` / `tracers`（**非同名**物）——**MUST NOT** 以不相干的上游位置充数 |
| `Store` | `langgraph/store/base/__init__.py:733`（`batch`）/ `:756`（`get`）/ `:779`（`search`）/ `:856`（`put`）/ `:937`（`delete`）/ `:946`（`list_namespaces`） |
| `CompiledGraph` | `langgraph/pregel/main.py:3783`（`invoke`）/ `:2655`（`stream`）/ `:845`（`get_graph`）/ `:1392`（`get_state`）/ `:1480`（`get_state_history`）/ `:2515`（`update_state`） |

> **「无上游同名符号」怎么写（B2F1 第二轮复核裁定 · 2026-11-06）**：本层 10 个符号中
> `NodeFunc` / `TraceSink` / `Span` / `TraceQuery` 在上游**没有同名符号** ⇒
> README 兼容矩阵的该 4 行 MUST 写「**无上游对应**（自由设计）」+ **契约条目号**
> （C5 / C6、C23 / C24、C27），**MUST NOT** 硬凑行号（宪法原则 VIII 的证据纪律）。
> 与 spec FR-017 / SC-021、门禁 G8 **同口径**。
>
> **上游来源的落位（B2F1 第六轮复核裁定 · 2026-11-06）**：兼容矩阵**保持 4 列**
> （既有 8 行**逐字不动** ⇒ 同表列数必须一致，**MUST NOT** 为来源单开一列）；
> 「有上游同名符号者」的来源行号（`路径:行号`）**写进该行的「差异说明」单元格末尾**
> （与说明文字以 `；` 分隔）。

**五个纯数据类的上游对应**（与 §1.2 的字段清单配套；`README.md` 兼容矩阵的 5 个数据类行据此写来源）：

| 类型 | 上游对应 | 说明 |
|---|---|---|
| `Graph` / `Node` / `Edge` | `langchain_core/runnables/graph.py:255`（`Graph`）/ `:95`（`Node`）/ `:65`（`Edge`） | **同名但自有实现**——**不复用、不复制上游代码**（原则 IX：避免「声明兼容」被读成「暗示 affiliation」） |
| `Span` | **无上游同名符号** · 契约 **C23 / C24**（DF4） | 上游的近似物是 LangSmith 的 `RunTree`（**非同名**） |
| `TraceQuery` | **无上游同名符号** · 契约 **C27** | C27 是 freegraph 自有的本地 trace 查询契约 |

**协议面共同约定**：

- **纯抽象**：MUST NOT 有任何默认实现（否则缺实现的假实现会静默通过结构化子类型判定）——G10。
- **结构化子类型判定只比对方法名存在性**，不比对签名 ⇒ 「签名写错」由**静态类型检查**承担——G11。
- **零构造期校验 / 零方法体**：协议不定义任何行为。

### 1.2 五个纯数据类（`frozen=True` · `slots=True` · `kw_only=True`）

| 类型 | 字段 | 类型 | 缺省 | 契约 |
|---|---|---|---|---|
| `Node` | `id` | `str` | —（必填） | C13 / C25 |
| | `name` | `str \| None` | `None` → **归一为 `id`** | |
| | `metadata` | `Mapping[str, Any]` | 空映射 | |
| `Edge` | `source` | `str` | —（必填） | C13 / C14 |
| | `target` | `str` | —（必填） | |
| | `conditional` | `bool` | `False` | |
| | `condition` | `str \| None` | `None` | |
| `Graph` | `nodes` | `tuple[Node, ...]` | `()` | C13 |
| | `edges` | `tuple[Edge, ...]` | `()` | |
| `Span` | `id` | `str` | —（必填） | C23 / C24 · DF4 |
| | `name` | `str` | —（必填） | |
| | `attributes` | `Mapping[str, Any]` | 空映射 | |
| | `parent` | `str \| None` | `None`（**父 span 的 id**，非对象引用） | |
| | `start_time` | `str` | —（必填，UTC ISO-8601） | |
| | `end_time` | `str \| None` | `None`（未结束时为空） | |
| | `context` | `Mapping[str, Any]` | 空映射 | |
| | `thread_id` | `str \| None` | `None`（**会话标识**） | C22 / C23 |
| | `run_id` | `str` | —（必填，**单次运行标识**） | |
| | `node` | `str` | —（必填，**节点名**） | |
| | `checkpoint_id` | `str \| None` | `None`（**检查点标识**） | |
| `TraceQuery` | `run_id` | `str \| None` | `None` | C27 |
| | `thread_id` | `str \| None` | `None` | |
| | `node` | `str \| None` | `None` | |
| | `start_time` | `str \| None` | `None`（UTC ISO-8601） | |
| | `end_time` | `str \| None` | `None`（UTC ISO-8601） | |

### 1.3 冻结的行为与不变式

| 项 | 冻结内容 |
|---|---|
| 协议纯抽象 | 5 个协议的方法体**只有** `...`（G10） |
| 方法集的判定口径 | **集合相等**（G11）；**成员的定义顺序 MUST NOT 纳入冻结面**——`typing.Protocol` 的成员集合是 `set`（CPython 3.11 / 3.12 实测：`{'c','b','a'}`），顺序随 `PYTHONHASHSEED` 变化 |
| 结构化子类型判定 | 完整实现判**真**、缺任一方法判**假**（G11） |
| 数据类不可变性 | 构造后字段不可改（改即抛 `FrozenInstanceError`） |
| 容器防御性拷贝 | `Node.metadata` / `Span.attributes` / `Span.context` 浅拷贝；`Graph` 两个集合为元组 |
| 相等语义 | 五个数据类**字段级相等**（同字段值 → 相等） |
| 哈希语义 | `Node` / `Edge` / `Graph` / `Span` **统一不可哈希**（`Edge` 须显式 `__hash__ = None`）；`TraceQuery` 可哈希（**有意如此**） |
| span 生命周期 | 不可变；开始收「`end_time` 为空」实例、结束收**同 `id`、已填 `end_time` 的新实例**，按 `id` 配对；开始快照**不被事后改写** |
| 构造期校验 | **零值校验**——只做类型注解、缺省归一、容器浅拷贝；其余由生产者保证 |
| JSON 可序列化 | `Span` 与 `TraceQuery` **100% 可 JSON 序列化**（C27 前提） |
| `get_state` 空值语义 | 查不到会话状态时返回**空值**，**MUST NOT** 抛异常 |
| `Node.name` 缺省语义 | 归一后**恒为字符串**（未给别名时等于 `id`） |
| `run_id` 的生成方 | **运行时**生成，MUST NOT 可由用户指定或覆盖，**不进** `RunConfig` 字段清单 |

---

## 2. 契约清单 C1–C27 冻结对照表

> **「状态」二态**：**已冻结**（本 feature 落定冻结面）/ **挂起**（**已决策**归某 feature，
> 本处不定形状）。
> **「修订」是独立列**（取值 `—` 或 `D11`），**正交标注**（D11 的字段级修订，本 feature
> 已落进类型定义），**不计入**「已冻结 / 挂起」的二态统计。
> **「落地位置 / 挂起归属」列的两种语义**：**已冻结**行记**落地面**（哪个类型 / 方法
> 承载它）；**挂起**行记**v1 归属 feature**（与 `harness/proposals/立项书.md` §5.3 的
> 「归属 feature」列逐条一致）。
> **MUST NOT 擅自增删条目**（宪法原则 VII）——本表覆盖 **C1–C27 全部 27 条**。

| # | 契约项 | 状态 | 修订 | 落地位置 / 挂起归属 | 备注 |
|---|---|---|---|---|---|
| C1 | 状态 schema | 挂起 | — | B4F1（类型于 B1F1 冻结） | `NodeFunc` 的入参类型用 `StateDict`（= `dict[str, Any]` 别名），**不自造状态类型体系** |
| C2 | 归约器机制 | 挂起 | — | B4F1 | — |
| C3 | 默认归约语义 | 挂起 | — | B5F1 | — |
| C4 | 稀疏状态 | 挂起 | — | B5F2 | 回归测试归 B5F2；本层只保证入参类型是普通 `dict` |
| C5 | **节点函数签名** | 已冻结 | — | `NodeFunc.__call__` | `(state: StateDict) -> StateDict \| Command \| None` |
| C6 | 节点返回值合并 | 已冻结 | — | `NodeFunc` 返回三形态 | **形态**已冻结；逐 key 归约语义挂起 B4F1 / B5F1 |
| C7 | 路由函数契约 | 挂起 | — | B8F1 | — |
| C8 | 条件边读状态 | 挂起 | — | B8F1 | 回归测试归 B8F1 |
| C9 | 起止标记 | 挂起 | — | B2F2（导出）/ B6F1（使用） | 门面归 B2F2 |
| C10 | **编译** | 已冻结 | — | `CompiledGraph` 六方法 | **协议面**已冻结；具体编译行为归 B7F2 |
| C11 | **执行** | 已冻结 | — | `CompiledGraph.invoke` → **完整状态字典** | **协议面**已冻结；行为归 B7F3 |
| C12 | 流式 | 已冻结 | — | `CompiledGraph.stream` → 事件迭代器 | **协议面**已冻结（元素类型 = `dict[str, Any]`）；**mode 枚举全集挂起 B8F2** |
| C13 | **图结构导出** | 已冻结 | — | `Graph` / `Node` / `Edge` 字段逐字 + `get_graph(xray=)` | **自有类型**，不复用 `langchain_core.runnables.graph` |
| C14 | mermaid 导出 | 挂起 | — | B22F1 | 消费 `Graph` / `Edge`（条件边可表达） |
| C15 | PNG 渲染 | 挂起 | — | B23F1 | — |
| C16 | 命令原语 | 已冻结 | — | `Command` + `NodeFunc` 引用它 | **B1F1 已冻结**；本 feature 不改 `Command` |
| C17 | 中断原语 | 挂起 | D11 | B10F1 | 恢复 MUST 挂 checkpointer ⇒ 本 feature 的 `Checkpointer` 协议面承载「检查点标识」 |
| C18 | 动态 fan-out | 挂起 | — | v2（B11F1） | 本 feature **不导出** `Send` |
| C19 | **检查点接口** | 已冻结 | — | `Checkpointer` 六方法 | **方法集 + 最小约束 + 参数名**已冻结（逐字见 `data-model.md` §2.2）；**载荷形状与返回类型挂起 B14F1** |
| C20 | 存储接口 | 已冻结 | — | `Store` 六方法 | **方法集 + 寻址语义 + 参数名**已冻结（逐字见 `data-model.md` §2.4）；**v1 无实现**（B17 已砍）；命名空间载体形态挂起 v2 |
| C21 | 运行时上下文 | 已冻结 | — | `RunConfig.context` | **B1F1 已冻结**；独立通道，不塞 `configurable` |
| C22 | **运行配置** | 已冻结 | D11 | `RunConfig` 四字段 | 标识职责划分已落进类型定义——`thread_id` 在 `RunConfig` 内；**`run_id` 不进 `RunConfig`** |
| C23 | **可观测挂钩** | 已冻结 | D11 | `TraceSink` 三方法 + `Span` 11 字段 | **协议面 + span 字段**已冻结；span 必带 `thread_id` / `run_id` / 节点名（字段名 `node`）/ `checkpoint_id`；**缺 `run_id` 视为实现缺陷** |
| C24 | 当前 span 上下文 | 已冻结 | — | `TraceSink.current_span()` → `Span \| None` | **协议面**已冻结；嵌套实现归 B19F1 |
| C25 | **节点命名** | 已冻结 | — | `Node.id` 唯一 + `Node.name` 别名 | **图结构面**已冻结；运行时别名校验归 B8F3 |
| C26 | 子图 | 挂起 | — | v2 | v1 只保 `get_graph(xray=)` **签名兼容** |
| C27 | **本地 trace 存储与查询** | 已冻结 | D11 | `TraceQuery` 5 字段 + `Span` 11 字段 | **数据面**已冻结；「存储与查询同一协议、后端可替换」的**协议面挂起 B20F1**；本 feature 只落请求 / 返回结构与该约束文字 |

**统计**：**已冻结 15 条**（C5 / C6 / C10 / C11 / C12 / C13 / C16 / C19 / C20 / C21 / C22 /
C23 / C24 / C25 / C27）· **挂起 12 条**（C1 / C2 / C3 / C4 / C7 / C8 / C9 / C14 / C15 / C17 /
C18 / C26）· **「修订」列非空 4 处**（C17 / C22 / C23 / C27 · 正交标注，**不计入**二态统计）·
**遗漏 0 条**（15 + 12 = 27）。

---

## 3. 冻结记录（spec FR-013 的四件事）

1. **C27 条目已落契约层** —— `TraceQuery`（5 字段）与 `Span`（11 字段）已定义；请求 / 返回
   结构 **100% 可 JSON 序列化**；「存储与查询 MUST 经由同一协议、后端可替换」以**约束文字**
   记入 §2 的 C27 行与 `research.md` D-15；**协议面挂起 B20F1**。
2. **span 必带字段已在类型定义中体现** —— `Span` 的 `thread_id` / `run_id` / `node` /
   `checkpoint_id` 四项**均可读**（§1.2）；`run_id` **必填**（缺它视为实现缺陷）。
3. **`run_id` 的生成职责归属运行时层** —— 由运行时在每次 `invoke` / `stream` 开始时生成，
   **MUST NOT** 可由用户指定或覆盖，**不进** `RunConfig` 的字段清单（B1F1 冻结的四字段
   **未增删**）。
4. **本 feature 的三项裁定** ——
   ① **命名**：`NodeFunc`（节点函数协议）/ `Node`（图节点元素）/ `Edge`（边元素）——「`Node`」一词此后**唯一**
   指图结构节点元素；② **范围**：**不落**「存储与查询」第五个协议（C27 协议面挂起 B20F1）；
   ③ **粒度**：各协议的冻结粒度见 spec FR-002 / FR-004 / FR-005 —— `Checkpointer` 冻结
   **方法集 + 语义 + 参数名 + 最小约束**（**载荷形状与返回类型挂起 B14F1**）、
   `Store` 冻结**方法集 + 语义 + 参数名 + 寻址语义**（**载体形态挂起 v2**）、
   `CompiledGraph` 冻结**返回类别 + 参数名（按 `data-model.md` §2.5 冻结为占位名）**——
   **行为细节**挂起各实现 feature。

---

## 4. 门禁摘要

架构门禁的完整定义见 [architecture-gates.md](./architecture-gates.md)（**G1–G13**）。
本 feature 的增量：

| 门禁 | 内容 | 状态 |
|---|---|---|
| G7 | 公开符号面**恰为 18 个**（由 8 扩展） | 本 feature 修改 |
| G8 | 文档合规门禁：**兼容矩阵逐符号覆盖 `public-api.md` §0 所列符号**（期望值从 §0 解析）；**保持 4 列**（既有 8 行逐字不动 ⇒ 不可新增列），**行内上游来源行号只对「有上游同名符号」的**新增 10 行**成立**——**写在「差异说明」单元格末尾**；**无上游同名符号者**——`NodeFunc` / `TraceSink` / `Span` / `TraceQuery`——写「无上游对应」+ 契约条目号） | 本 feature 修改（改为清单驱动 + 逐符号；**本 feature 起即可启用**——本层 10 行已在本 feature 补入） |
| G10 | 协议**纯抽象**（方法体只有 `...`） | 本 feature 新增 |
| G11 | 结构化子类型判定可用（完整实现判真 / 缺方法判假） | 本 feature 新增 |
| G12 | 公开符号面**唯一权威**（**机器标记** `<!-- authority: yes -->` 的清单文件数 == 1） | 本 feature 新增 |
| G13 | **纯数据纪律**（数据类字段不得含可调用 / 对象类型） | 本 feature 新增 |

---

## 5. 移交后续 feature

| # | 事项 | 归属 | 性质 |
|---|---|---|---|
| 1 | 检查点载荷的**具体字段形状 + 返回类型** | **B14F1** | `Checkpointer` 的**方法集 + 语义 + 参数名**已冻结；只细化载荷与返回类型 |
| 2 | `Store` 命名空间**载体形态** + `batch` **操作表示** | **v2** | `Store` 的**方法集 + 语义 + 参数名**已冻结；契约 C20 仍冻结，v1 无实现 |
| 3 | `stream()` 的 **mode 枚举全集** | **B8F2** | `stream` 的返回类别已冻结 |
| 4 | `CompiledGraph` 各方法的**行为细节与实现** | **B7F3 / B8F2 / B15F1 / B16F1** | 返回类别与**参数名**已冻结（占位名） |
| 5 | 「存储与查询」协议的方法集 | **B20F1** | C27 的数据面已冻结 |
| 6 | **span 的生产行为**（节点 / 工具 / 模型三级） | **B18F1** | `Span` 的**类型面**以本文件为准 |
| 7 | `TraceSink` 的**接入** + `current_span()` 的**嵌套实现** | **B19F1** | 协议面已冻结 |
| 8 | 子图实现（C26） | **v2** | v1 只保 `get_graph(xray=)` 签名兼容 |
| 9 | `mermaid` 文本 / PNG 渲染 | **B22F1 / B23F1** | 消费本文件的 `Graph` / `Edge` |
| 10 | 公开 API 门面 `freegraph/graph.py` | **B2F2** | 本 feature **不交付** |
| 11 | `README.md` **兼容矩阵**补本层 **10 个**新符号（等价判定：协议面 / 数据面分别标注；**保持 4 列**，**来源行号写进该行的「差异说明」单元格末尾**——既有 8 行逐字不动 ⇒ 不可新增列；**有上游同名符号者附来源行号，无对应者写「无上游对应」+ 契约条目号**） | **B24F1**（全库补全与定稿） | **本 feature 已填入本层 10 行**（FR-017 / SC-021）；B24F1 只做全库总校对与定稿 |
| 12 | `THIRD_PARTY_NOTICES` 的补登 | **B24F1** | 本 feature **零**新增第三方依赖 ⇒ **无需新增登记**（依赖登记表不变） |
| 13 | 架构断言接入 CI 流水线 | **B3F1** | 本 feature 只交付 pytest 断言；CI 须**先装包**，否则 G3 恒 skip |
| 14 | `Send` / `interrupt` 的导出 | **v2**（B11F1 / B10F1） | 公开符号面严格 = 18 个 |
| 15 | **B18F1 提示词**的交付物口径 | **B18F1** | 收窄为「span **生产**行为」（类型面以本文件为准） |
| 16 | **B22F1 提示词**的 `Graph` / `Node` / `Edge` 命名 | **B22F1** | **不变**（与本文件一致） |
