# feature 1 · 数据模型（data-model.md）

**功能块**: B2F1 · 5 个协议 + 5 个纯数据类
**Branch**: `b2f1-contracts-protocols` · **Date**: 2026-11-06
**输入**: [spec.md](./spec.md) · [research.md](./research.md)（D-01…D-20）

> **字段清单的优先级（B2F1 复核裁定 · 2026-11-06）**：本文的字段表是
> `contracts/public-api.md` §1.2 的**同源镜像**；两处不一致时 **MUST 以 spec 的
> FR-006 / FR-010 正文为准**，并**同步修正** `public-api.md`（不得就地改型）。
> （本轮已据此统一 `Node.name` 的类型口径：`str | None = None` + 构造期归一为 `id`。）
>
> **哈希语义同样只有一个手工维护点**：`contracts/public-api.md` §1.3（本文 §4.3 与
> spec SC-019 / plan 的「相等 / 哈希」行**只引用**、不各写一份）——避免「四类统一不可哈希 +
> `TraceQuery` 有意可哈希」这条口径在四处并列抄写而漂移。
> **映射型字段的缺省写法**：本文的「空映射」= **`field(default_factory=dict)`**
> （dataclass 拒绝可变缺省 `= {}`；B1F1 `types.py:117` 同款）。
> 
> 本文是 `/speckit.plan` 的 feature 1 产出：把 spec 里已冻结的形状落成**可实现的类型定义**
> （字段、注解、不变式、生命周期）。**全部内容只依赖标准库**，零第三方依赖。
> 依据纪律：字段名与契约编号的对应逐条给出（宪法原则 VIII）。

---

## 1. 实体关系

```text
                    ┌──────────────────────────────┐
   用户实现 ───────▶│ 5 个协议（Protocol · 纯抽象） │
                    └──────────────────────────────┘
                      NodeFunc      Checkpointer
                      TraceSink     Store
                      CompiledGraph
                            │ 签名引用
                            ▼
        ┌───────────────────────────────────────────┐
        │ 5 个纯数据类（冻结 dataclass）              │
        │ Graph  Node  Edge   Span   TraceQuery     │
        └───────────────────────────────────────────┘
                            │ 复用（B1F1 已冻结，**不改动**）
                            ▼
     StateDict   Command   StateSnapshot   RunConfig
```

**要点**：协议**只引用**数据类与 B1F1 的既有类型；数据类**不引用**协议；
数据类之间只有 `Graph → Node / Edge` 一处组合关系，`Span` 与 `TraceQuery` **互不引用**
（查询的结果集合 = span 列表，但 `TraceQuery` 不持有 span）。

---

## 2. 协议面

> **通用规则（5 个协议一致）**：
> ① `typing.Protocol` + `@runtime_checkable`；
> ② **纯抽象** —— 方法体只有 `...`（D-04，门禁 G10）；
> ③ **不提供基类继承链**（PD-1）；
> ④ 方法集合**恰为**下列清单，不多不少（门禁 G11）——**以集合相等判定**，**成员的定义顺序
>    MUST NOT 纳入冻结面**（`typing.Protocol` 的成员集合是 `set`，CPython 3.11 / 3.12 实测：
>    `{'c','b','a'}`，顺序随 `PYTHONHASHSEED` 变化）；
> ⑤ **零构造期校验、零方法体** —— 协议不定义任何行为。

### 2.1 `NodeFunc` —— 节点函数协议

| 成员 | 签名 | 语义 |
|---|---|---|
| `__call__` | `(state: StateDict) -> StateDict \| Command \| None` | 节点函数契约：入参为**稀疏**状态字典；返回**部分状态字典** / **命令原语** / 空值（不写状态） |

- **对应契约**：C5（节点函数签名）/ C6（返回值合并 —— 逐 key 归约语义归 B4F1 / B5F1，本协议只冻结返回形态）
- **判定方式**：`isinstance(f, NodeFunc)` —— 对任意**可调用对象**恒为真（因其自带 `__call__`）；
  该判定的价值是「不是可调用对象时判失败」，**不是**「是不是合法节点函数」（D-03）。
  「合法节点函数」由**静态类型检查**判定（SC-004 · mypy 路径）。
- **不冻结**：节点函数的**参数个数**（只一个 `state`）——运行时是否注入第二参数属实现层。

> ### 2.2 `Checkpointer` —— 检查点协议

> **占位记号说明**：本表中的 `<…待定>` 是**文档记号**（「此处的参数尚未冻结」），
> **不是** Python 的省略号 `...`——实现时该位置填 `Any` 占位（见 D-05 / D-06）。
> **已冻结 vs 挂起（2026-11-06 第六轮复核修订 · 发起者裁定）**：**方法名与参数名已冻结**
> （下表逐字给出；参数名同属冻结面——协议签名不写死参数名即无法实现，静态类型检查 SC-004
> 与对外文档都需要确切签名）；**挂起的只有返回类型 / 载荷结构**（归 **B14F1**）。

| 成员 | 签名（**参数名已冻结** · D-05；**返回类型挂起 B14F1**） | 语义 |
|---|---|---|
| `get_tuple` | `(config: RunConfig) -> Any` | 取回**最新**快照；无快照时返回空值语义 |
| `list` | `(config: RunConfig, <其余参数待定>) -> Any` | 列举**历史**快照（可带过滤 / 上界） |
| `put` | `(config: RunConfig, <其余参数待定>) -> Any` | 写入一个**快照** |
| `put_writes` | `(config: RunConfig, <其余参数待定>) -> Any` | 写入**待写入数据**（pending writes） |
| `delete_thread` | `(thread_id: str) -> Any` | 删除某**会话**的全部快照与写入 |
| `get_next_version` | `(<参数待定>) -> Any` | 生成**下一个版本号**（单调递增） |

- **已冻结的最小约束（四条）**：① 方法集合**恰为**上述六个；② **方法名与参数名**（如上）；
  ③ 读写面 MUST 能承载**检查点标识**（C23 要求 span 必带它）；④ 载荷 MUST 为**纯数据**
  （可 JSON 序列化）。
- **占位说明**：返回类型处的 `Any` **不是**「随便什么」，而是「**返回结构与载荷形状挂起
  B14F1**」的显式标记；收紧属契约修订流程（宪法 §Governance），不是就地改型。
- **对应契约**：C19 —— 冻结的是**协议面 + 参数名**；**载荷形状与返回类型挂起 B14F1**
  （C17 要求「中断恢复 MUST 挂 checkpointer」，这会反过来影响载荷要装什么，故不宜此刻定死）。

### 2.3 `TraceSink` —— 可观测接收端协议

| 成员 | 签名 | 语义 |
|---|---|---|
| `on_span_start` | `(span: Span) -> None` | 一个 span **开始**：收到「`end_time` 为空」的实例 |
| `on_span_end` | `(span: Span) -> None` | 一个 span **结束**：收到**同 `id`、`end_time` 已填的新实例** |
| `current_span` | `() -> Span \| None` | **当前** span（无当前 span 时返回**空值**，MUST NOT 抛异常） |

- **回调载荷语义（D-07 · Q9）**：两次回调按 **`id` 配对**；开始时收到的实例 MUST NOT 在事后
  被改写（其 `end_time` 始终为空）。
- **「不注入即零开销零外呼」**：本协议**不提供**任何默认实现——运行时若未注入 sink，
  **不得**创建「空接收端」对象（那是行为，属 B19F1）。
- **对应契约**：C23（可观测挂钩）/ C24（当前 span 上下文）。

### 2.4 `Store` —— 长期存储协议

| 成员 | 签名（**参数名已冻结** · D-06；**载体类型挂起 v2**） | 语义 |
|---|---|---|
| `get` | `(namespace, key) -> Any` | 按 **(命名空间, 键)** 取一项 |
| `search` | `(namespace_prefix, <其余参数待定>) -> Any` | 在命名空间**前缀**下检索多项 |
| `put` | `(namespace, key, value) -> Any` | 写入一项 |
| `delete` | `(namespace, key) -> Any` | 删除一项 |
| `list_namespaces` | `(prefix, <其余参数待定>) -> Any` | 列出命名空间（层级路径） |
| `batch` | `(ops, <其余参数待定>) -> Any` | **批量**执行多个操作 |

- **已冻结的语义层（四条）**：① 方法集合**恰为**上述六个；② **方法名与参数名**（如上——
  `namespace` / `key` / `value` / `namespace_prefix` / `prefix` / `ops`；**`namespace` 的载体类型以 `Any`
  占位**）；③ 命名空间 = **层级路径**（多段组成），**键 = 字符串**；④ 取值 MUST 为**纯映射**
  （可 JSON 序列化）。
- **参数名逐字对齐上游（兼容锚点 · 2026-11-06 第六轮复核核实）**：
  `search` 的首参名为 **`namespace_prefix`**、`list_namespaces` 的首参名为 **`prefix`**——
  **二者是上游 LangGraph 1.2.11 的原样命名**（核实：
  `langgraph/store/base/__init__.py` `search(self, namespace_prefix, /, …)` /
  `list_namespaces(self, *, prefix=None, …)`），freegraph **刻意逐字镜像**（D-09 的
  「保留上游核心名作兼容锚点」原则）——**MUST NOT** 为「一个概念一个名字」而改名：
  ① 改之即偏离上游（兼容锚点失效）；② 两者连**参数形态**都不同（`search` 的
  `namespace_prefix` 是**位置参数**，`list_namespaces` 的 `prefix` 是**关键字参数**），
  本就不是同一个参数位。**上游的这个命名分歧在此显式登记**（宪法原则 VIII 的证据纪律），
  下游实现 MUST 照抄，不得自行统一。
- **挂起**：命名空间的**具体载体形态**（层级元组 / 点分字符串）与 `batch` 的**操作表示**
  **挂起 v2**（D-06）——故 `namespace` 参数的**类型**在签名中以 `Any` 占位。
- **v1 无实现**：本协议**只定义类型**；契约 C20 仍冻结（freechain 的设计输入），实现后补（v2）。
- **对应契约**：C20。

### 2.5 `CompiledGraph` —— 编译产物协议

| 成员 | 签名（**返回类别已冻结**，D-08） | 返回类别 |
|---|---|---|
| `invoke` | `(input: StateDict, config: RunConfig \| None = None) -> StateDict` | **完整状态字典** |
| `stream` | `(input: StateDict, config: RunConfig \| None = None, *, stream_mode: str \| Sequence[str] = "values") -> Iterator[dict[str, Any]]` | **事件迭代器**（**元素类型 = `dict[str, Any]`**，纯数据字典） |
| `get_graph` | `(*, xray: bool = False) -> Graph` | **图结构** |
| `get_state` | `(config: RunConfig) -> StateSnapshot \| None` | **状态快照**（**查不到返回空值**，不抛异常） |
| `get_state_history` | `(config: RunConfig) -> Iterator[StateSnapshot]` | **状态快照迭代器** |
| `update_state` | `(config: RunConfig, values: StateDict, as_node: str \| None = None) -> StateSnapshot` | **状态快照** |

- **已冻结**：六个方法的**返回类别** + **参数名（占位名 · B2F1 复核裁定）** +
  `get_state` 的**空值语义**（不抛异常）。
- **挂起**：各方法的**行为细节与实现** —— `invoke` → B7F3、`stream` → B8F2（mode 枚举）、
  状态查询 → B15F1、`update_state` → B16F1。
- **参数名的口径（B2F1 复核裁定 · 2026-11-06）**：上表签名中的参数名
  （`input` / `config` / `stream_mode` / `xray` / `as_node`）**冻结为占位名**——
  理由：协议签名不写死参数名即无法实现，静态类型检查（SC-004）与对外文档都需要确切签名。
  下游 feature 确需改名者 MUST 走**契约修订**流程，MUST NOT 就地改型。
  （spec 的 Q8 / FR-005 已据此回写；原口径「参数名挂起各实现 feature」作废。）
- **`stream` 的 mode 取值为字符串**（枚举全集归 B8F2）；v1 **只保** `get_graph(xray=)` 的
  **签名兼容**（子图实现属 v2）。
- **元素类型的冻结（2026-11-06 第六轮复核修订）**：`stream` 的元素类型**冻结为
  `dict[str, Any]`**（原 `Iterator[Any]` 与 spec FR-005②「元素为纯数据字典」不等价 ⇒
  冻结面未表达该约束）。
- **对应契约**：C10（编译）/ C11（执行）/ C12（流式）/ C13（图结构导出）。

---

## 3. 纯数据类

> **通用规则（5 个数据类一致）**：
> ① `@dataclass(frozen=True, slots=True, kw_only=True)` —— 不可变 + 字段级相等 + 有 `repr`；
> ② **零构造期值校验**（只做类型注解、缺省归一、容器浅拷贝）；
> ③ 字段值**均可 JSON 序列化**（不得含对象引用）；
> ④ 四个类**统一不可哈希**（`TraceQuery` 除外，见 §4.3）。

### 3.1 `Node` —— 图节点元素

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `id` | `str` | —（必填） | **节点名**，唯一 |
| `name` | `str \| None` | `None` → **归一为 `id`** | **别名**（C25：节点名唯一，允许别名） |
| `metadata` | `Mapping[str, Any]` | 空映射 | 附加信息（可为空映射） |

- **不变式**：`name` 归一后**恒为字符串**（D-10）；`id` 非空由调用方保证（**不校验**）。
- **对应契约**：C13（图结构）/ C25（节点命名）。

### 3.2 `Edge` —— 边元素

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `source` | `str` | —（必填） | 起点**节点名** |
| `target` | `str` | —（必填） | 终点**节点名** |
| `conditional` | `bool` | `False` | 是否**条件边** |
| `condition` | `str \| None` | `None` | 条件名（非条件边时为空） |

- **不变式**：`conditional` 为真时 `condition` **MUST** 非空——本层**不校验**（值级守卫会与
  后续 30 个 feature 的实际用法反复冲突），由生产者（图定义层）保证。
- **对应契约**：C13 / C14（C14 的 mermaid 渲染消费本类型）。

### 3.3 `Graph` —— 图结构

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `nodes` | `tuple[Node, ...]` | `()` | 节点集合（**不可变元组**） |
| `edges` | `tuple[Edge, ...]` | `()` | 边集合（**不可变元组**） |

- **不变式**：`nodes` 的元素 `id` **唯一**——本层**不校验**（去重属图定义层）。
- **容器用元组而非上游的 `dict[str, Node]` / `list[Edge]`**（D-09）：与不可变记录自洽，
  且避免「顺序不保证」的额外语义。
- **对应契约**：C13。

### 3.4 `Span` —— 可观测事件载体（**11 字段**）

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `id` | `str` | —（必填） | **span 唯一标识**（`parent` 引用它） |
| `name` | `str` | —（必填） | span 名（节点 / 工具 / 模型三级命名） |
| `attributes` | `Mapping[str, Any]` | 空映射 | 属性（命名对齐 OTel GenAI 的 `gen_ai.*`） |
| `parent` | `str \| None` | `None` | **父 span 的 `id`**（**不是对象引用**）；无父为空 |
| `start_time` | `str` | —（必填） | 起始时刻（**UTC ISO-8601 字符串**） |
| `end_time` | `str \| None` | `None` | 结束时刻（UTC ISO-8601）；**未结束时为空** |
| `context` | `Mapping[str, Any]` | 空映射 | 附加上下文 |
| `thread_id` | `str \| None` | `None` | **会话标识**（C22；由 `RunConfig` 承载） |
| `run_id` | `str` | —（必填） | **单次运行标识**（C22 / C23；由运行时生成，**不可为空**） |
| `node` | `str` | —（必填） | **节点名**（C23 必带） |
| `checkpoint_id` | `str \| None` | `None` | **检查点标识**（C23 必带；未挂检查点时为空） |

- **必带四项（C23 · D11）**：`thread_id` / `run_id` / `node` / `checkpoint_id` —— 四项
  **均可读**；**缺 `run_id` 的 span 视为实现缺陷**（宪法原则 VII）。
- **JSON 可序列化（C27 前提）**：`parent` 为**标识字符串**、时间为 **ISO 字符串**，
  `attributes` / `context` 为纯映射 —— 整个 span 可被标准库序列化器直接序列化。
- **不可变（D-07 / D-14）**：`attributes` / `context` 在 `__post_init__` 中**浅拷贝**。
- **对应契约**：C23 / C24；数据格式 **DF4**。

### 3.5 `TraceQuery` —— trace 查询请求（C27）

| 字段 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `run_id` | `str \| None` | `None` | 运行标识过滤 |
| `thread_id` | `str \| None` | `None` | 会话标识过滤 |
| `node` | `str \| None` | `None` | 节点名过滤 |
| `start_time` | `str \| None` | `None` | 时间范围起点（UTC ISO-8601） |
| `end_time` | `str \| None` | `None` | 时间范围终点（UTC ISO-8601） |

- **五字段全部可空、可组合**；**全空 = 取全部**（C27 的「空过滤器」）。
- **字段名与 span 侧同名**（D-12）——一个概念一个名字。
- **对应契约**：C27（**数据面已冻结**；协议面挂起 B20F1）。

---

## 4. 不变式与校验边界

### 4.1 构造期校验（**零值校验**）

| 类型 | 构造期**做**什么 | 构造期**不**做什么 |
|---|---|---|
| `Node` | `name` 缺省归一为 `id`；`metadata` 浅拷贝 | 不校验 `id` 非空 / 唯一 / 类型 |
| `Edge` | —（`condition` 不校验） | 不校验 `source` / `target` 指向存在的节点 |
| `Graph` | — | 不校验节点唯一 / 边端点存在 |
| `Span` | `attributes` / `context` 浅拷贝 | 不校验 `run_id` 非空 / 时间格式 / `parent` 指向存在的 span |
| `TraceQuery` | — | 不校验时间范围先后（`start > end` 归查询实现处理） |

**理由**（沿用 B1F1 的校验边界口径）：值级守卫会与后续 30 个 feature 的实际用法
（持久化后端回读、JSON 整包透传、图定义层的动态构造）反复冲突，每次冲突都要动已冻结的
公开面。格式与类型由**生产者**保证。

### 4.2 不可变性

- 五个数据类一律 `frozen=True` —— 构造后**字段不可改**（改即抛 `FrozenInstanceError`）。
- **浅不可变**：`metadata` / `attributes` / `context` 装的是**拷贝**后的新映射，
  但其中的**嵌套容器**仍与调用方共享同一对象（本层不做深拷贝）。
- `Graph.nodes` / `Graph.edges` 是**元组**——元素本身不可变，序列本身也不可变。

### 4.3 哈希语义（统一不可哈希）

| 类型 | 可哈希？ | 说明 |
|---|---|---|
| `Node` | ❌ | 含 `metadata`（映射）——哈希必抛 `TypeError` |
| `Edge` | ❌ | 四字段全是标量，dataclass **会自动生成** `__hash__` ⇒ **必须显式写 `__hash__ = None`** |
| `Graph` | ❌ | 元素不可哈希 ⇒ 自身不可哈希 |
| `Span` | ❌ | 含 `attributes` / `context`（映射） |
| `TraceQuery` | ✅（**有意如此**） | 五字段全为标量，无映射字段 ⇒ dataclass 默认可哈希——**记录在案，非缺陷** |

**实现要点**：`Edge` 类体**必须**显式写 `__hash__ = None`——CPython `dataclasses` 的
`_hash_action` 表对「类体中**显式**定义 `__hash__`」的组合**不做覆盖**
（`(False, True, True, True) → None`），故该写法生效且不会被 dataclass 改回。
「不可哈希」的根因是**含映射字段**，不是一条无理由的禁令（见 `research.md` D-13）。

### 4.4 标识与生命周期

| 标识 | 层级 | 承载者 | 用户可否指定 |
|---|---|---|---|
| `thread_id` | **会话** | `RunConfig`（B1F1 已冻结） | ✅ 可指定 |
| `run_id` | **单次运行** | **运行时**生成 | ❌ **MUST NOT 可指定或覆盖** |
| `node`（span 内） | 图节点 | `Span.node` | ❌ 由运行时填 |
| `checkpoint_id` | 检查点 | `Span.checkpoint_id` | ❌ 由运行时填（未挂检查点时为空） |

**span 生命周期（状态迁移）**：

```text
  [未开始]
      │  on_span_start(span₀)      span₀.end_time is None
      ▼
  [进行中] ────────────────────────── current_span() 返回 span₀
      │  on_span_end(span₁)         span₁.id == span₀.id, span₁.end_time 非空
      ▼
  [已结束]                          span₀ 的 end_time **仍为 None**（不可变）
```

- 一次运行一个 `run_id`（该次运行的所有 span 共享它）。
- `stream()` 事件与 `TraceSink` 的 span **共享同一** `run_id` / `thread_id`（C22 ↔ C23）。

---

## 5. 与 B1F1 既有类型的关系（**只复用，不改动**）

| 既有类型 | 本 feature 的用法 | 是否改动 |
|---|---|---|
| `StateDict` | `NodeFunc.__call__` 的入参类型 / `CompiledGraph.invoke` 的入参 | ❌ 不改 |
| `Command` | `NodeFunc.__call__` 的返回形态之一 | ❌ 不改 |
| `StateSnapshot` | `CompiledGraph.get_state` / `get_state_history` / `update_state` 的返回类型 | ❌ 不改 |
| `RunConfig` | `Checkpointer` 与 `CompiledGraph` 的 `config` 参数类型；**承载 `thread_id`** | ❌ 不改（**且不得新增字段**——`run_id` 不进 `RunConfig`，C22 · D11） |
| 异常体系 | 本层**不抛**任何异常（零构造期值校验 ⇒ 无校验失败路径） | ❌ 不改 |

---

## 6. 挂起项（**本文只列与本文字段/签名直接相关的 7 条**；完整 **13 条**见 `research.md` §挂起项交接表 —— 两表口径一致，本表是该表的**子集**）

| # | 挂起项 | 归属 |
|---|---|---|
| 1 | 检查点载荷的**具体字段形状 + 返回类型** | B14F1 |
| 2 | `Store` 命名空间**载体形态** + `batch` **操作表示** | v2 |
| 3 | `stream()` 的 **mode 枚举全集** | B8F2 |
| 4 | `CompiledGraph` 各方法的**行为细节与实现**（**参数名已冻结为占位名** · B2F1 复核裁定） | B7F3 / B8F2 / B15F1 / B16F1 |
| 5 | 「存储与查询」协议的方法集 | B20F1 |
| 6 | span 的**生产行为** | B18F1 |
| 7 | `TraceSink` 的**接入**与 `current_span()` 的**嵌套实现** | B19F1 |
