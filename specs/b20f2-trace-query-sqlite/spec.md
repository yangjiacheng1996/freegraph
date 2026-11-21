# Feature Specification: B20F2 · Trace 查询 API + SQLite 后端

**Feature Branch**: `b20f2-trace-query-sqlite`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_specify` 钩子；既有 feature 同样在 `main` 上开发）

**Created**: 2026-11-21

**Status**: Draft

**Input**: User description: `harness/features/B20F2_Trace查询API与SQLite后端.md` —— 交付**本地 trace 的读取侧**：一个**查询 API**（按 `run_id` / `thread_id` / 时间范围 / 节点名检索）和一个 **SQLite 后端**（标准库 `sqlite3`，零第三方依赖），让用户能**按条件检索**历史运行轨迹。判定：**可按 run / thread / 时间 / 节点名检索，两个后端可替换**。

> **范围提醒**：本 feature 是 **L5 可观测层**的**读取侧 + SQLite 持久化后端**。
> 它在 B20F1 的**同一 `FileTraceStore` 对象上补齐查询 API**，并新增
> `SqliteTraceStore`；**MUST NOT** 改变 B20F1 已交付的写侧行为、文件命名、
> `kind` / 字段名、`0o600`、per-instance 锁与四路诊断。
> **不实现** OTLP 导出（B21F1）、前端 / UI（v2 / B26）、本地 Agent Server（v2 / D8）、
> Postgres 后端（v2）、保留期 / 清理（v1 不做）、评测 / 数据集（永不做）。
> `Span` 11 字段、`TraceSink` 3 方法、`TraceRecord` 字段面、`TraceQuery` 5 字段、
> `RunConfig` 9 字段、`freegraph.graph` 门面符号面**一律不改**。

---

## 形态锁定裁定（FR-005 / FR-006 / FR-009 的「写死」结论）

> 提示词要求：查询 API 的**请求 / 返回结构**、**排序**、**空过滤器上限**、
> **SQLite 注入形态** MUST 在本 feature 锁定。本节是**锁定结论**，
> `/speckit.plan` 与 `/speckit.implement` **MUST** 照此执行。

### 1. 公开读取载体（两个后端同一方法）

**锁定形态：`query(query: TraceQuery | None = None) -> list[dict[str, Any]]`，
同时存在于 `freegraph.observability.FileTraceStore` 与新增的
`freegraph.observability.SqliteTraceStore`。**

| 备选 | 是否采用 | 理由 |
|---|---|---|
| **同一 `query(TraceQuery)` 方法挂在两个 store 上** | ✅ **采用** | ① 直接满足 C27 ④「存储与查询经由同一协议、后端可替换」；② 调用方只持有对象、不 import 具体后端类，替换后端无需改调用代码；③ `TraceQuery` 已在 B2F1 逐字冻结，请求结构无需新增；④ 与 B20F1「在同一 `FileTraceStore` 对象上补齐查询 API」的交接要求一致。 |
| 在 L1 新增 `TraceStore` / `TraceQueryable` 协议 | ❌ **不采用** | L1 契约面（`protocols.py` 的 5 个协议）已冻结；C27 ④ 的「同一协议」可由**同一方法签名 + 结构化替换**满足，无需新增 L1 符号。若未来要提升为正式 `Protocol`，走 C27 / 契约修订。 |
| 查询函数 `freegraph.observability.query_traces(store, q)` | ❌ **不采用** | 让调用方依赖「函数 + store 具体类型」，弱化「后端可替换」；也把查询能力从 store 上剥离，违背 C27 ④。 |
| 返回 `Span` / `TraceRecord` 对象实例 | ❌ **不采用** | C27 ③ 要求结果纯数据、可直接 JSON 序列化；返回对象会迫使调用方再做序列化，且无法保留 B20F1 落盘的 `TraceRecord.to_jsonable()` 原样字段。 |

**共同协议（结构化）**：

```python
# 两个后端都必须满足；调用方按鸭子类型使用，不 import 具体类。
def query(self, query: TraceQuery | None = None) -> list[dict[str, Any]]: ...
```

- `query=None` 与 `query=TraceQuery()` **等价**（空过滤器 ⇒ 取全部）。
- 传入非 `TraceQuery` / 非 `None` 的参数 ⇒ `TypeError`。
- 查询是**同步**方法；v1 无 async。
- 查询**不参与**图执行路径；运行时 MUST NOT 自动调用 `query()`。
- 两个后端的**构造参数**不同（`directory` vs `database`）只是**存储定位差异**；
  注入后对 B19F1 的 sink 行为与对查询调用方的 `query()` 行为 MUST 完全一致，
  使用方 MUST NOT 感知具体后端。

### 2. SQLite 后端注入形态

**锁定形态：`freegraph.observability.SqliteTraceStore(database: str | os.PathLike[str], *,
on_error: Callable[[BaseException], None] | None = None)`。**

| 项 | 锁定值 |
|---|---|
| 参数名 | **`database`**（必填；`str` 或 `os.PathLike[str]`；单个 SQLite 文件路径；v1 不提供连接对象注入；`:memory:` / URI 不支持 ⇒ 构造时 `ValueError`） |
| 默认值 | **无**（MUST NOT 提供默认数据库路径；不注入 = 不落盘） |
| 路径处理 | 按传入值使用；**MUST NOT** `expanduser` / `expandvars` / 读环境变量 / 联网解析 |
| 数据库创建 | **惰性**：构造时不打开 / 不创建数据库；第一次真正写行时才创建**父目录**（`parents=True, exist_ok=True`）、数据库文件与内部表结构 |
| 查询侧副作用 | 查询 **MUST NOT** 创建数据库文件、内部表结构或改动已有数据；数据库不存在 ⇒ 返回空列表 |
| 写入模式 | 追加（每个 span / trace_record 一行）；不覆盖已有数据 |
| 失败隔离 | 与 B20F1 相同的四路诊断（`write_errors` / `last_error` / `on_error` / `logging.WARNING`）；永不阻断图执行 |
| 文件权限 | POSIX 上新建数据库文件 **不宽于 `0o600`**；已存在的数据库文件 MUST NOT 被主动放宽，实现 MAY 尝试收紧到 `0o600`、失败不阻断写入；v1 不提供权限配置参数；Windows 由平台 ACL 解释 |
| 并发 | 每个 store 实例一把进程内锁串行化写入；跨进程依赖 SQLite 文件锁 + 有限忙等待超时（内部实现细节，v1 不暴露为参数） |
| 表结构 | **内部实现细节**（C27 ⑤）；MUST NOT 暴露表名 / 列名 / SQL 作为公开 API |
| 公开面 | 只暴露 B19F1 sink 回调（`on_span_start` / `on_span_end` / `on_trace_record` / `current_span`）+ 诊断面（`write_errors` / `last_error`）+ `query`；**MUST NOT** 提供 `close()` / `__enter__` / `__exit__` / 上下文管理器 / 公开连接对象 |

### 3. 请求结构（C27 / DF6 / B2F1 冻结，不改）

**请求 = 已冻结的 `freegraph.contracts.TraceQuery`，恰好 5 个字段，全部可空、可任意组合：**

| 字段 | 类型 | 语义 | 本 feature 的匹配规则 |
|---|---|---|---|
| `run_id` | `str \| None` | 运行标识 | 与条目的 `run_id` **精确相等**；`None` = 不启用该过滤 |
| `thread_id` | `str \| None` | 会话标识 | 与条目的 `thread_id` **精确相等**；`None` = 不启用该过滤 |
| `node` | `str \| None` | 节点名 | 与条目的 `node` **精确相等**（大小写敏感、非子串）；`None` = 不启用。**全部匹配**：含该节点自身 span、该节点内部 `node` 同名的模型 / 工具 span、以及该节点的 record |
| `start_time` | `str \| None` | 时间窗起点（含） | 见 §6 |
| `end_time` | `str \| None` | 时间窗终点（含） | 见 §6 |

**组合语义**：所有非 `None` 字段以 **AND** 组合；`TraceQuery()`（五字段全 `None`）=
**空过滤器 = 取全部**。`None` 是**唯一**的「不启用」值；**空字符串 `""` 是字面值**
（按精确相等匹配，通常得到空结果），MUST NOT 被当成「未设置」。

**字段类型校验（2026-11-22 澄清 · 用户选择 A）**：5 个字段的运行时值 MUST 是 `str` 或
`None`；任一字段是其它类型（如 `int` / `bool` / `list`）⇒ 在读取任何数据前抛
`TypeError`。合法字符串但无法解析为时间 ⇒ 按 §6 抛 `ValueError`。
理由：避免把写错的查询静默当成「无匹配」而返回空结果。

**v1 明确不增加的过滤维度**：`checkpoint_id` / `task_id` / `superstep` / `kind` /
`parent` / span 名（`name`）/ 错误状态。`checkpoint_id` / `task_id` / `superstep`
**只作为返回字段**保留；若未来要升级为契约过滤器，**MUST** 走 C27 契约修订
（B18F1 D-2 / B19F1 D-1）。

### 4. 返回结构（写死）

**锁定：返回 `list[dict[str, Any]]`；每个元素是一条 B20F1 已落盘的「行视图」。**

- 结果元素**只允许** `kind="span"` 与 `kind="trace_record"` 两种；其它 `kind`
  MUST NOT 出现在结果中（跳过并记 `logging.WARNING`，见 §8）。
- `kind="span"` 元素：`kind` + **`Span` 的全部 11 字段**（`id` / `name` /
  `attributes` / `parent` / `start_time` / `end_time` / `context` / `thread_id` /
  `run_id` / `node` / `checkpoint_id`）。
- `kind="trace_record"` 元素：`kind` + **`TraceRecord.to_jsonable()` 的全部 13 字段**
  （`span_id` / `task_id` / `run_id` / `thread_id` / `checkpoint_id` / `node` /
  `superstep` / `triggers` / `concurrency_group` / `barrier_groups` / `input_state` /
  `output_state` / `error`）。
- 字段名 / 含义 **逐字沿用 B20F1 / B19F1**；本 feature **MUST NOT** 改名、重新定义、
  合并或丢弃任何字段。`span_id` ↔ `id` 的关联关系原样保留（不额外物化联合字段）。
- 结果元素**只含**上述已冻结字段；行内的**额外未知字段 MUST NOT 返回**（丢弃）。
  额外字段的取舍 MUST NOT 影响必需字段的校验或结果排序。
- 已知 `kind` 的行 MUST 含该 `kind` 的**全部必需字段**且值类型正确；缺失必需字段或
  类型不符 ⇒ 跳过该行并记 `WARNING`（见 §8），**MUST NOT** 返回残缺元素。
- 元素值 MUST 是**纯数据**：`dict` / `list` / `str` / `int` / `float` / `bool` / `None`；
  **MUST NOT** 含异常对象、类、函数、句柄、dataclass 实例或任何不可 JSON 序列化对象。
- 返回的列表与元素 MUST 是**独立副本**：调用方修改结果 MUST NOT 影响存储，
  MUST NOT 影响后续查询结果。
- 整个返回值 MUST 可被 `json.dumps(result)` 直接序列化（C27 ③ / P4 的 CI 断言前提）。

### 5. 默认排序（写死）

**锁定：默认按「条目的有效起始时刻」升序；同一时刻按固定次序打破平局。**

「有效起始时刻」的定义：

| 条目类型 | 有效起始时刻 |
|---|---|
| `kind="span"` | 该 span 的 `start_time` |
| `kind="trace_record"` | 其 `span_id` 在**同一 `run_id`** 且同一次查询可见的 span 中对应 `id` 的 span 的 `start_time` |
| `kind="trace_record"` 且找不到对应 span（如进程崩溃 / 并发查询只看到 record） | **无时刻**（见下） |

- 关联 MUST 在 **`(run_id, span_id)` ↔ `(run_id, id)`** 范围内进行；MUST NOT 跨 `run_id`
  关联（不同运行的 `span_id` 可能碰撞）。
- 「可见」= 满足同一 `TraceQuery` 过滤、且被本次查询读取到的 span；因过滤或快照原因
  找不到关联 span 的 record 按「无时刻」处理。

排序键（自左向右比较）：

1. **有有效起始时刻的条目在前，无时刻的条目在后**；
2. 有时刻：`start_time` **升序**（按解析后的 UTC 瞬时比较；精度 MUST **到纳秒**，
   MUST NOT 截断到微秒；对 B20F1 的规范格式 `YYYY-MM-DDTHH:MM:SS.nnnnnnnnn+00:00`
   可直接按字符串序比较——两者等价）；
3. 同一时刻：`run_id` **升序**（字符串序）；
4. 仍相同：`kind` 次序为 **`trace_record` 先于 `span`**（与 B20F1「同节点 record 行
   在 span 行之前」的写入顺序一致）；
5. 仍相同：稳定标识 **升序**——`trace_record` 用 `span_id`，`span` 用 `id`；
6. 无时刻的 record：排在有时刻条目之后，按 `(run_id, superstep, task_id, span_id)`
   升序。

**不变量**：同一存储、同一 `TraceQuery`、同一快照 ⇒ 排序结果**逐条相同**；
两个后端对同一份数据给出**相同排序**。完全相同的重复行无法区分，其相对顺序
MAY 任意，但不得影响其它条目的顺序。

**重复行口径**：完全相同的重复行按**多重集合**比较（条数与字段值 MUST 相等）；
其相对顺序 MAY 任意，**不参与**跨后端逐条顺序比较；同一后端连续查询 MUST 稳定。

### 6. 时间窗语义（写死）

- `start_time` / `end_time` 都是 **UTC ISO-8601 瞬时**；都**可空**；
  **闭区间** `[start_time, end_time]`（边界**包含**）。
- 只给 `start_time` ⇒ 仅应用下界（上界无界）；只给 `end_time` ⇒ 仅应用上界（下界无界）；
  两者都 `None` ⇒ 不启用时间过滤。
- 比较对象 = §5 的**有效起始时刻**（span 的 `start_time` / record 所关联 span 的
  `start_time`）。**不使用** `end_time` 做「区间相交」判定。
- 时间解析：接受带时区偏移的 ISO-8601 与末尾 `Z`；**无时区偏移按 UTC 解释**。
  比较精度 MUST **到纳秒**（小数位不足按右侧补 `0` 解释；MUST NOT 截断到微秒）。
  解析失败的查询时刻 ⇒ 在读取任何数据前抛 `ValueError`（查询调用方处理，
  不影响图执行）。
- `start_time > end_time`（倒置）⇒ 返回**空列表**，MUST NOT 抛错、MUST NOT 擅自交换。

### 7. 空过滤器、上限与分页（写死）

- **空过滤器（`TraceQuery()` 或 `query=None`）MUST 合法**，返回该存储中**全部匹配条目**，
  MUST NOT 因「没有过滤条件」报错。
- **上限：无隐式截断**。v1 返回全部匹配条目；`query` **不提供** `limit` / `offset` /
  分页参数。理由：本地 trace 是诊断数据、单次运行规模有限；隐式截断会让 CI 断言
  「恰好 N 次模型调用」产生假阴性。
- 若未来需要分页 / 上限，**MUST** 走 C27 契约修订；本 feature MUST NOT 私自新增参数。

### 8. 查询失败与只读语义（写死）

> **总原则（2026-11-22 澄清 · 用户选择 A）**：**尽量容错 + 告警**——能读多少返回多少；
> 可跳过的损坏记 `logging.WARNING`；只有**整个存储完全不可读**才把异常抛给查询调用方；
> **绝不自动修复 / 迁移 / 删除 / 重建**任何已有数据。

| 场景 | 锁定行为 |
|---|---|
| 存储不存在（目录不存在 / 数据库文件不存在） | 返回 **`[]`**，不报错、不创建任何文件 / 目录 / 表 |
| JSONL 行无法解析（截断 / 非 JSON / 非对象） | 跳过该行并记一条 `logging.WARNING`；其余行照常返回；**MUST NOT** 因单行损坏使整个查询失败 |
| 行的 `kind` 不是 `"span"` / `"trace_record"` | 跳过该行并记 `WARNING`；**MUST NOT** 出现在结果中（结果契约只含两种 `kind`） |
| 已知 `kind` 的行缺少必需字段 / 字段类型不符 | 跳过该行并记 `WARNING`；**MUST NOT** 返回残缺元素 |
| 已知 `kind` 的行携带额外未知字段 | 只返回已冻结字段，额外字段丢弃；不因额外字段失败 |
| JSONL 文件不可读（权限 / I/O） | 跳过该文件并记 `WARNING`，其余文件照常返回；若存在候选文件但**全部**不可读 ⇒ 异常传播给查询调用方 |
| JSONL 候选文件是符号链接 | 跳过该文件并记 `WARNING`；MUST NOT 跟随目录内符号链接读取（防止读出存储目录） |
| 目录路径存在但**不是目录**（普通文件） | 整个存储不可读 ⇒ 异常传播给查询调用方；不删除 / 不改写该文件 |
| SQLite 内部表结构不存在 | 视为空存储 ⇒ 返回 **`[]`** |
| SQLite 旧表存在但**不兼容**（缺必需列 / 类型冲突） | **不修改**旧表；视为无可用数据 ⇒ 返回 **`[]`** + `WARNING`。**额外多出的列不视为不兼容**，读取时忽略 |
| SQLite 单行 `payload` JSON 解码失败（含 `input_state` / `output_state` / `error` 等嵌套值） | 跳过该行并记 `WARNING`；其余行照常返回 |
| SQLite 文件损坏 / 非 SQLite / I/O 失败 | 整个存储不可读 ⇒ 异常传播给**查询调用方**；MUST NOT 传播进任何图执行路径；用户显式传入的 `database` 路径 MAY 是符号链接（按用户意图打开） |
| 返回结果被调用方修改 | 存储与后续查询**不受影响** |
| 并发写入进行中 | 查询 MUST NOT 返回**半行 / 未提交事务**的条目；该条目 MAY 被包含或跳过，取决于查询快照 |

- 查询是**只读操作**：MUST NOT 创建 / 截断 / 删除 / 改写任何存储文件或表；
  MUST NOT 触发建库、建表、迁移、修复、重建。
- 「查询失败不影响运行」（宪法原则 IV）在本 feature 的实现口径是：
  ① 运行时**从不自动调用** `query`；② `query` 独立于写入回调，其异常不会进入
  `on_span_start` / `on_span_end` / `on_trace_record` / `current_span`；
  ③ 补齐查询不得改变 B20F1 的写入隔离行为。

### 9. 内部实现细节声明

**表结构、列名、SQL、JSONL 文件命名 / 行结构、SQLite 文件布局一律是内部实现细节
（C27 ⑤）。** 对外只承诺：

1. `TraceQuery` 请求字段（§3）；
2. `query()` 返回结构（§4）；
3. 排序 / 时间窗 / 空过滤器 / 失败语义（§5–§8）；
4. 两个后端的可替换性。

Studio / 测试 / 用户 MUST NOT 直连 SQLite 表或 JSONL 文件；需要取数时**只能**经
`query()`（立项书 §5.8.4 的数据访问边界）。内部 schema 变化 MUST NOT 改变上述对外语义。

---

## Clarifications

### Session 2026-11-22（clarify 轮 · 用户参与）

- Q: 按节点名过滤时，该节点内部产生的模型调用 span / 工具调用 span（其 `node` 字段也是该节点名）是否也算匹配？
  → A: **全部匹配**。返回 `node` 字段等于该节点名的**所有**条目：节点自身 span、
  该节点内部 `node` 同名的模型 / 工具 span、以及该节点的 `trace_record`。
  理由：`node` 是「这一步」的分组键，排除子 span 会让「查这一步」不完整；且不必新增
  `kind` / `name` 过滤维度（新增需走 C27 修订）。
- Q: 查询遇到「存储存在但无法完整读取」时，两个后端采用什么统一策略？
  → A: **尽量容错 + 告警**：JSONL 坏行 / 不兼容旧表跳过并记 `WARNING`，能读多少返回多少；
  只有整个存储完全不可读（目录路径是普通文件、全部候选文件不可读、SQLite 文件损坏 /
  非 SQLite / I/O 失败）才把异常交给查询调用方；**绝不自动修复 / 迁移 / 删除 / 重建**。
  理由：trace 是诊断数据，尽量拿到可用信息；告警避免静默漏数据；修改已有数据风险不可接受。
- Q: `TraceQuery` 字段传错类型（如 `run_id=123` / `start_time=123`）时怎么处理？
  → A: **统一抛 `TypeError`**：5 个字段的运行时值必须是 `str` 或 `None`；任一字段类型不对
  即在读取数据前抛 `TypeError`。合法字符串但无法解析为时间仍抛 `ValueError`。
  理由：避免把写错的查询静默当成「无匹配」而返回空结果。
- Q: 查询遇到 spec 未定义的 `kind`（未来扩展或外部写入）时怎么处理？
  → A: **严格过滤 + 告警**：只返回 `kind="span"` / `"trace_record"`；未知 `kind` 跳过并记
  `WARNING`。理由：结果契约稳定，消费者只面对两种已知结构；未来新增 `kind` 应走 C27 修订。
- Q: JSONL 目录中 `trace-*.jsonl` 的 `run_id` 段不符合安全 allowlist 时，读还是不读？
  → A: **严格只读白名单文件名**：只读
  `^trace-[A-Za-z0-9][A-Za-z0-9_-]*\.jsonl$`；其它 `trace-*.jsonl` 跳过并记 `WARNING`。
  理由：与 B20F1 的 `run_id` 安全规则一致，避免把外部 / 遗留文件误当成本 feature 数据；
  只涉及目录内文件名，不做目录穿越。

### Session 2026-11-21（spec 阶段写死 · plan 不得再翻）

- Q: 查询结果应返回 `Span` / `TraceRecord` 对象，还是 JSON 视图？
  → A: **返回 B20F1 落盘的行视图（纯 `dict`）**。`list[dict[str, Any]]` 直接满足
  C27 ③ / P4 的 JSON 断言；保留 `TraceRecord.to_jsonable()` 全部 13 字段与 `Span`
  全部 11 字段；不在本 feature 重新构造对象、不要求 B19F1 提供第二套序列化。
- Q: 返回两类行（span + trace_record）还是一个统一结构？
  → A: **两类行都返回，用 `kind` 区分**（与 B20F1 落盘格式一致）。模型 / 工具 span
  只有 span 行；节点任务有 span 行与 record 行，经 `span_id` ↔ `id` 关联。统一结构会
  丢失字段，违反 D-1/D-2「保留字段、不重新定义」。
- Q: `run_id` / `thread_id` / `node` / 时间四类过滤器如何组合？
  → A: **AND 组合**；`None` 为「不启用」；空过滤器 = 取全部。空字符串是字面值。
- Q: 时间窗按什么时间、是否包含边界？
  → A: 按条目的**有效起始时刻**（span 的 `start_time`；record 用其关联 span 的
  `start_time`），**闭区间**，边界包含；倒置区间返回空列表。
- Q: 默认排序是什么？
  → A: **有效起始时刻升序**；同刻依次按 `run_id`、`kind`（record 先于 span）、
  稳定标识（`span_id` / `id`）升序；无关联 span 的 record 排在最后。
- Q: 空过滤器是否需要上限？
  → A: **无隐式截断，返回全部匹配条目**；v1 不提供 `limit` / `offset`；未来分页走
  C27 修订。理由：截断会让 CI 的「恰好 N 次」断言失真。
- Q: JSONL 后端如何实现查询，是否需要 B20F1 提供读方法？
  → A: **本 feature 自己读取 B20F1 的 `trace-<run_id>.jsonl`**（按已锁定行结构解析）；
  B20F1 **MUST NOT** 被要求新增查询方法（D-3）。JSONL 文件格式仍是内部实现细节。
- Q: SQLite 后端是否也实现写侧？
  → A: **是**。`SqliteTraceStore` 必须能作为 B19F1 sink 注入并落盘，否则无法与
  `FileTraceStore` 做「同一份数据、同一查询、等价结果」的可替换性判定（A6）。
  写侧语义与 B20F1 完全一致（失败隔离 / 诊断 / 不重试 / per-instance 锁）。
- Q: 是否需要新增 L1 `Protocol`？
  → A: **否**。两个后端共享同一 `query(TraceQuery | None)` 方法签名即可满足 C27 ④；
  L1 契约面已冻结，新增协议走契约修订。
- Q: `checkpoint_id` / `task_id` / `superstep` 是否成为过滤器？
  → A: **否（v1）**。它们只作为返回字段保留；新增为过滤器 MUST 走 C27 契约修订
  （B18F1 D-2）。
- Q: SQLite 的 Windows 文件锁差异如何处理？
  → A: 写入用 per-instance 锁 + SQLite 文件锁 + **有限**忙等待超时；并发写 + 查询
  MUST NOT 损坏数据库；该用例 MUST 在 Windows CI 上跑。超时按「写入失败」隔离，
  查询异常交给调用方。
- Q: 查询失败是否影响图执行？
  → A: **不影响**。运行时从不自动查询；查询与写入回调隔离；补齐查询不改变 B20F1
  的写侧隔离与图结果。

---

## 分析补丁记录（2026-11-22 · 完备性补丁）

> 以下补丁不改变已确认的 5 项澄清结论，只把实现前必须写死的细节补齐。

1. **record ↔ span 关联范围**：关联 MUST 在**同一 `run_id`** 内进行（`(run_id, span_id)` ↔
   `(run_id, id)`）；MUST NOT 跨 run 关联，防止 `span_id` 碰撞导致排序 / 时间窗错配。
   落点：§5、Edge Cases。
2. **已知 `kind` 行的字段完整性**：MUST 含该 `kind` 的全部必需字段且类型正确；
   缺字段 / 类型不符 ⇒ 跳过 + `WARNING`；额外未知字段 ⇒ 丢弃、不返回。
   落点：§4、§8、FR-004、FR-011、Edge Cases、SC-013、SC-014。
3. **SQLite 单行 `payload` JSON 损坏**：payload 内的 `input_state` / `output_state` /
   `error` 等值解码失败 ⇒ 只跳过该行 + `WARNING`，其余行照常。
   落点：§8、FR-011、Edge Cases、SC-013。
4. **SQLite 落盘细节**：首次写行惰性创建**父目录**（`parents=True, exist_ok=True`）；
   已存在数据库文件 MUST NOT 被主动放宽，实现 MAY 尝试收紧、失败不阻断。
   落点：§2、FR-019、SC-018。
5. **符号链接**：JSONL 候选文件是符号链接 ⇒ 跳过 + `WARNING`，MUST NOT 跟随读取；
   用户显式传入的 SQLite `database` 路径 MAY 按用户意图打开。
   落点：§8、FR-025、Edge Cases、SC-013。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 按 run / thread 精确回查一次运行 (Priority: P1)

作为用户，我刚跑完一次运行，手里有一个 `run_id`（从 `stream()` 事件或 trace 记录里
读到）；我也可能刚跑完一轮多轮对话，手里有 `thread_id`。我希望用它把**这一次运行**
或**这一轮会话**的全部 span / 记录取出来，复盘每一步。

**Why this priority**: `run_id` 是「把每个节点视作微服务」时的链路通行证；按 run 查是
C27 读取侧的最小价值切片。按 thread 查覆盖多轮会话复盘。

**Independent Test**: 分别向存储写入 2 次运行（`run_id` 不同，其中分属 2 个
`thread_id`）的 span + record；用 `TraceQuery(run_id=...)` 查询只返回该次运行的全部
条目；用 `TraceQuery(thread_id=...)` 查询只返回该 thread 的全部条目。

**Acceptance Scenarios**:

1. **Given** 存储中已有 run-A 与 run-B 的完整 trace，**When** 查询
   `TraceQuery(run_id="run-A")`，**Then** 返回的每一条都满足 `run_id == "run-A"`，
   且 run-A 的节点 / 模型 / 工具 span 与节点 record **全部在内**，run-B 的条目 **0 条**。
2. **Given** thread-1 与 thread-2 各有若干 run，**When** 查询
   `TraceQuery(thread_id="thread-1")`，**Then** 返回的全部条目 `thread_id == "thread-1"`，
   thread-2 的条目 **0 条**。
3. **Given** 上述结果，**When** 对整个返回值执行 `json.dumps`，**Then** 序列化成功，
   可直接用于 CI 断言。

---

### User Story 2 - 按时间范围定位一次运行 (Priority: P2)

作为用户，我希望按时间窗过滤，找出「昨天 14:00 那次运行」，排除窗外记录。

**Why this priority**: 用户常常只记得「大概什么时候跑的」，时间窗是 run / thread
之外的独立检索入口。

**Independent Test**: 写入跨多个时刻的 trace；用 `TraceQuery(start_time=..., end_time=...)`
查询，断言窗内条目全部返回、窗外条目全部排除；边界时刻的条目被包含。

**Acceptance Scenarios**:

1. **Given** 条目的**有效起始时刻**分别为 `T0 < T1 < T2`，**When** 查询
   `[T1, T1]`，**Then** 只返回有效起始时刻为 `T1` 的条目（闭区间）。
2. **Given** 同一数据，**When** 只提供 `start_time=T1`，**Then** 返回有效起始时刻
   `>= T1` 的条目。
3. **Given** `start_time > end_time`，**When** 查询，**Then** 返回 `[]`，不抛错。

---

### User Story 3 - 按节点名查最慢的那一步 (Priority: P3)

作为用户，我怀疑某个节点慢，希望只查该节点的 span / 记录。

**Why this priority**: 节点级过滤把「一次运行」缩小到「一步」，是定位慢节点 / 报错节点
的直接入口。

**Independent Test**: 写入含 `a` / `b` / `c` 节点的 trace；查询 `TraceQuery(node="b")`，
断言只返回 `node == "b"` 的条目（含节点 span、该节点内部的模型 / 工具 span 与 record），
不返回其它节点。

**Acceptance Scenarios**:

1. **Given** 多节点 trace，**When** 查询 `TraceQuery(node="b")`，**Then** 每条结果的
   `node == "b"`，其它节点条目 **0 条**。
2. **Given** 节点 `b` 内部调用了模型与工具，**When** 查询 `TraceQuery(node="b")`，
   **Then** 节点 `b` 自身的 span、其内部模型 / 工具 span、以及节点 `b` 的 record
   **均被返回**（不因 `kind` / `name` 不同而排除）。
3. **Given** fan-out 场景中某节点 task 的 `task_id` 为 `b:TaskId`，**When** 查询
   `TraceQuery(node="b")`，**Then** 该 record 因 `node == "b"` 被返回；查询 **不** 按
   `task_id` 过滤（v1 不支持 task_id 过滤）。

---

### User Story 4 - 在 CI 里写断言 (Priority: P4)

作为用户，我希望用查询 API 在自动化测试中断言「本次运行恰好 2 次模型调用」。

**Why this priority**: 这是 C27 对下承诺的「可写断言」能力；结果不稳定就无法作为 CI 判据。

**Independent Test**: 跑一次含 2 次模型调用的图；用 `run_id` 查询；断言
`len([x for x in result if x["kind"] == "span" and x["name"] == <模型 span 名>]) == 2`；
对结果执行 `json.dumps` 与相等比较。

**Acceptance Scenarios**:

1. **Given** 一次运行含 2 次模型 span，**When** 按 `run_id` 查询并计数，**Then** 计数 **== 2**。
2. **Given** 同一查询连续执行两次，**Then** 两次结果**逐条相等**（稳定排序）。
3. **Given** 返回结果被调用方原地排序 / 修改，**When** 再次查询，**Then** 结果不变。

---

### User Story 5 - 两个后端可替换 (Priority: P2)

作为用户，我希望把 JSONL 后端换成 SQLite 后端（或反过来），查询代码不用改。

**Why this priority**: C27 ④ 的可替换性是「同一协议」的判定；否则后端选择会泄漏到用户代码。

**Independent Test**: 用同一组 B19F1 事件分别写入 `FileTraceStore` 与
`SqliteTraceStore`；对同一 `TraceQuery` 分别查询，断言两个结果列表逐条相等。

**Acceptance Scenarios**:

1. **Given** 同一份事件流分别写入两个后端，**When** 执行同一空过滤器查询，
   **Then** 两个结果列表的条目数、字段值、排序**逐条相等**。
2. **Given** 同一份事件流，**When** 执行 `run_id` / `thread_id` / 时间 / 节点名
   四类过滤及组合，**Then** 两个后端的每个查询结果都相等。

---

### Edge Cases

- **空存储 / 目录不存在 / 数据库文件不存在**：返回 `[]`，不报错、不创建文件 / 表。
- **只写过 span、没有 record**（span-only 适配器）：查询正常返回 span 条目，
  record 条目 **0 条**；不判缺陷。
- **record 存在但关联 span 尚未落盘 / 已丢失**：record 仍返回；排序按「无时刻」处理；
  有任何时间界时该 record **不匹配时间过滤**（无法判定时刻）。
- **跨 run 的 `span_id` 碰撞**：record ↔ span 的关联 MUST 在**同一 `run_id`** 内完成；
  MUST NOT 把 record 关联到其它 run 的同 id span。
- **`run_id` 为空 / 含路径分隔符 / 含点号**：作为过滤值时**不用于拼路径**；
  JSONL 后端 MUST NOT 发生目录穿越，返回 `[]`；SQLite 后端按字面值精确匹配（通常 `[]`）。
- **目录中存在 `trace-*.jsonl` 但 `run_id` 段不符合 allowlist**（如 `trace-a.b.jsonl`、
  外部写入 / 旧版本遗留）：JSONL 查询 MUST 跳过该文件并记 `WARNING`，不读取其内容。
- **`thread_id` 为 `None` 的条目**：只有 `thread_id=None`（不启用过滤）时返回；
  用具体字符串过滤时不返回。
- **模型 / 工具 span 的 `node` 字段**：等于其所属节点名；按节点名过滤时**一并返回**，
  MUST NOT 因其 `kind` / `name` 与节点不同而排除。
- **未知 `kind` 行**（未来扩展 / 外部写入）：跳过并记 WARNING；不出现在结果中，
  MUST NOT 让旧消费者收到未知结构。
- **已知 `kind` 但字段缺失 / 类型不符**：跳过该行并记 WARNING；MUST NOT 返回残缺元素。
- **已知 `kind` 但携带额外未知字段**：只返回已冻结字段，额外字段丢弃；不因额外字段失败。
- **SQLite 单行 `payload` JSON 无法解码**（含 `input_state` / `output_state` / `error`）：
  只跳过该行并记 WARNING；其余行照常返回。
- **JSONL 候选文件是符号链接**：跳过并记 WARNING；MUST NOT 跟随读取存储目录外的内容。
- **空字符串过滤值**（`run_id=""` / `node=""`）：按字面值匹配，通常 `[]`；
  MUST NOT 当作「未启用」。
- **过滤字段类型错误**（`run_id=123` / `node=["b"]` / `start_time=123`）：
  在读取数据前抛 `TypeError`，不返回部分结果；合法字符串但时间无法解析 ⇒ `ValueError`。
- **时间界恰好等于条目的 `start_time`**：包含（闭区间）。
- **时区偏移 / `Z` / 无时区串**：按瞬时比较；无时区按 UTC；非法串 ⇒ `ValueError`。
- **倒置时间窗**：返回 `[]`，不抛错。
- **并发写 + 查询**：查询 MUST NOT 看到半行 JSON 或未提交事务；正在写的条目 MAY
  出现或不出现；查询结果仍可 JSON 序列化、排序合法。
- **JSONL 最后一行损坏 / 被截断**：跳过该行并记 WARNING，其余行照常返回。
- **JSONL 单个文件不可读 / 目录路径是普通文件**：单文件不可读 ⇒ 跳过并 WARNING；
  目录路径是普通文件（整个存储不可读）⇒ 查询抛底层异常给调用方；均不修改文件。
- **SQLite 旧表不兼容（缺列 / 类型冲突）**：不修改旧表，返回 `[]` 并记 WARNING。
- **同一条目被重复写入**（例如外部重复调用）：两条都会返回；本 feature 不去重。
- **返回结果原地修改**：存储与后续查询不受影响（返回独立副本）。
- **非 ASCII / 换行 / 控制字符**：原样保留在返回的 `dict` 中；`json.dumps` 正确转义。
- **大结果集**：v1 无隐式上限；调用方需自行控制存储规模（见 Assumptions）。
- **SQLite 数据库损坏 / 非 SQLite**：查询抛底层异常给调用方；不自动修复、不覆盖数据库。
- **Windows 文件锁**：并发写 + 查询在 Windows 上 MUST 不损坏数据库；忙等待超时后
  写入按失败隔离、查询异常交调用方。

---

## Upstream Parity *(mandatory — 宪法 v1.12.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11** / `langchain-core` **1.7.6** / `langsmith` **0.14.17**（取证于 2026-11-21，本仓库 `.venv` 实际安装版本；沿用 B20F1 的版本钉住口径）

> **口径说明**：上游**没有** freegraph 这样的「本地 trace 查询 API + 可替换本地后端」。
> 上游的可观测查询是 **LangSmith SaaS 的远端 run 查询**（`langsmith.Client.list_runs` /
> `read_run`），默认关闭，开启后经 HTTP 访问远端。因此本 feature 的主体落在原则 XI 的
> **必须自研区 ③（上游没有的能力）**、**①（零账号 / 零主动出站 / 零依赖）**；
> 只有「空过滤器取全部」「按 run id 过滤」「失败隔离」「默认关闭」几类**行为面**
> 可与上游对齐。

### §1 逐条对照（P-01…P-07）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| **P-01** | **本地 trace 查询能力** | **上游无本地查询**；查询是 LangSmith 远端 `langsmith/client.py:4224`（`list_runs`）/ `:4068`（`read_run`），返回远端 `Run` 模型 | 两个本地后端共享 `query(TraceQuery \| None) -> list[dict]`；无网络、无账号 | **DIFF**（自研区 ③：上游没有的能力） | 本地可检索是 freegraph 的增量价值；上游查询必须连 SaaS |
| **P-02** | **过滤器集合** | `langsmith/client.py:4224-4243`（`project_id` / `run_type` / `trace_id` / `filter` / `start_time` / `run_ids` / …） | 四类过滤器 `run_id` / `thread_id` / 时间范围 / 节点名，AND 组合；**不含** `checkpoint_id` / `task_id` / `superstep` | **DIFF**（自研形态）· **STRICTER**（过滤器面收窄到 C27 冻结项） | C27 / DF6 已冻结 5 字段请求；不收窄会让契约漂移 |
| **P-03** | **零出站 / 零账号** | `langsmith/client.py:139`（`httpx` 客户端）· `:619`（默认 `https://api.smith.langchain.com`）· `langsmith/_internal/_background_thread.py:377`（批量 ingest） | 查询只读本地文件 / 本地 SQLite；零网络、零账号、零 API key | **STRICTER** | 宪法原则 I / IV / V；「查询本地 trace」不得变成远端请求 |
| **P-04** | **空过滤器取全部** | `langsmith/client.py:4224` 的 `list_runs` 在无过滤参数时列举项目内 runs（远端语义，源码阅读） | `TraceQuery()` / `query=None` 返回本地全部条目；无隐式截断 | **DIFF**（表示 / 远端语义：本地列表 vs 远端迭代器；**不标 SAME 行为面**） | C27 / FR-009 的「空过滤器」要求；上游侧未实测，不宣称行为面等价 |
| **P-05** | **失败隔离** | `langchain_core/callbacks/manager.py:351-354`（handler 异常被捕获并记警告） | 查询独立于写入回调；写入失败隔离沿用 B20F1；查询异常只到调用方 | **SAME**（隔离语义）· **STRICTER**（写入可感知面沿用 B20F1 四路诊断） | 宪法原则 IV；本 feature 不削弱 B20F1 |
| **P-06** | **结果表示** | 上游返回 `ls_schemas.Run` 等 SDK 对象，需再序列化 | 返回纯 `dict` 列表（B20F1 行视图），直接 `json.dumps` | **DIFF**（表示层：SDK 模型 vs 纯数据） | C27 ③；P4 的 CI 断言要求纯数据 |
| **P-07** | **默认关闭 / 环境变量** | `langchain_core/tracers/context.py:114-120`（只有启用 tracing 才构造 tracer）· `langsmith/utils.py:119-144`（`LANGSMITH_*` 环境变量可影响开关） | 不显式注入 store ⇒ 零查询 / 零存储；查询只认显式 `TraceQuery`，不读环境变量 | **SAME**（默认关闭）· **STRICTER**（不读 env） | 宪法原则 I / 配置层黑名单 |

### §2 实测基线（沿用 B19F1 / B20F1 · 取证于 2026-11-21）

| # | 实验 | 结果 |
|---|---|---|
| **E-1** | 两节点线性图 `a → b`，`invoke()`，不传 callbacks，环境变量全清 | 正常返回；**无任何** callback 事件（默认关闭） |
| **E-2** | 同图，传入自定义 `BaseCallbackHandler` | 共 6 条 handler 事件；回调路径不填充 `_PARENT_RUN_TREE_REF` |
| **E-3** | `boom` 节点抛 `RuntimeError("boom")`，传入自定义 handler | 异常原样抛出；事件序列仍完成 run 生命周期（`on_chain_error`） |

> **实测来源**：B19F1 spec §2 的 `/tmp/b19_upstream_probe.py`（2026-11-21 实跑）。
> 本 feature **不新增**上游行为断言；P-01 / P-02 / P-03 / P-04 / P-07 的
> 「上游没有本地查询 / 查询走远端 / 空过滤器的远端迭代器语义 / 环境变量可影响开关」
> 取证于**上游源码阅读**与 `.venv` 实际安装版本，仅用于说明能力缺失与表示差异，
> **不**作为本 feature 的差分行为断言（P-05 的隔离语义由 E-1 / E-3 实测支撑）。

### §3 差分场景组 *(mandatory)*

> 编号段 **D-501…D-508**（避开 B18F1 的 D-201…D-208、B19F1 的 D-301…D-310、
> B20F1 的 D-401…D-408）。

| # | 场景 | 断言（结果 / 失败与否） | 判词 |
|---|---|---|---|
| **D-501** | 本地查询 vs 上游远端查询 | freegraph：本地 `query` 返回条目；上游：需账号 + 远端 `list_runs`；两侧图结果逐字相等 | DIFF（P-01 / P-06） |
| **D-502** | 零出站 | freegraph：socket 监测夹具「框架出站 == 0」；上游：查询经 HTTP 到 LangSmith | STRICTER（P-03） |
| **D-503** | 空过滤器 | freegraph：返回本地全部条目；上游：无过滤列举远端 runs | DIFF（表示 / 远端语义） |
| **D-504** | 四类过滤 + 组合 | freegraph：每个过滤只返回匹配项；两个后端结果相等 | DIFF（自研形态；上游无同款四类本地过滤） |
| **D-505** | 失败隔离 | freegraph：查询/写入失败都不改变图结果；写入诊断沿用 B20F1 | SAME（隔离）· STRICTER（诊断） |
| **D-506** | 环境变量 | freegraph：设置 `LANGSMITH_*` / `FREEGRAPH_*` 不改变查询 / 存储 | STRICTER（P-07） |
| **D-507** | 依赖闭包 | freegraph 基础安装闭包为空；`sqlite3` 属标准库；上游闭包含 `langsmith` / `httpx` 等 | STRICTER（P-03） |
| **D-508** | 并发写 + 查询 | freegraph：per-instance 锁 + SQLite 文件锁；无损坏、无半行；Windows / Linux 均通过 | DIFF（自研本地后端） |

⇒ **判词分布**：**SAME 行为面 1**（D-505 的隔离段）+
**STRICTER 4**（D-502 / D-505 诊断面 / D-506 / D-507）+ **DIFF 4**（D-501 / D-503
表示 / D-504 / D-508）。

⇒ **证据口径**：D-501 / D-503 / D-506 的上游侧是**能力 / 表示层说明**（源码阅读），
不是需要实测的差分行为断言；差分用例只对 freegraph 侧做可执行断言
（D-502 / D-505 / D-507 的零出站 / 隔离 / 依赖闭包除外）。

⇒ **落点**：`tests/differential/test_b20f2_trace_query_parity.py` ⇒ **CI 的 Linux 全量档真跑**
（上游缺席即 skip · 沿用 B5F2 的「缺席即 skip」纪律）。本 feature 不与上游做逐字节
结果对比，只对齐「失败隔离 / 默认关闭 / 零出站」三类行为面；空过滤器仅作本地语义说明
（上游侧未实测，不标 SAME 行为面）。

### §4 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **DIFF**（自研区 ③：上游没有的能力） | 上游无本地 trace 查询 API、无可替换本地查询后端（对应 **P-01 / P-06**） | C27 的读取侧必须自研；上游对应物是 LangSmith SaaS，引入即破零依赖 / 零出站 | 本 feature · B21F1（后端对接文档） |
| **X-2** | **STRICTER**（自研区 ①：零账号 / 零主动出站 / 零依赖） | 上游查询经 HTTP 访问 LangSmith（对应 **P-03**） | freegraph MUST 零第三方依赖、零环境变量、零主动出站；只读本地存储 | 宪法原则 I / II / IX · 本 feature |
| **X-3** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 返回纯 `dict` 行视图 vs 上游 SDK `Run` 模型（对应 **P-06**） | C27 ③ 要求 JSON 可序列化；纯数据便于 CI 断言，也保留 B19F1 `to_jsonable()` 原样字段 | 本 feature |
| **X-4** | **STRICTER**（更严的失败信号；隔离语义 SAME） | 写入失败 MUST 沿用 B20F1 的四路可感知（对应 **P-05** 的 STRICTER 半段；隔离语义 SAME） | 静默吞错会让用户以为 trace 已记录；宪法原则 IV 要求可诊断 | 本 feature |
| **X-5** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 本地 SQLite / JSONL 后端与内部 schema vs 上游远端存储（对应 **P-01**；P-03 的 STRICTER 由 **X-2** 承接） | 表结构 / 文件格式是 C27 ⑤ 的内部实现细节；本地后端才能离线可查 | 本 feature |
| **X-6** | **DIFF · STRICTER**（自研区 ③ / ②：上游没有的本地过滤器形态 + 收窄到 C27） | 上游 `list_runs` 的过滤器集合（`project_id` / `run_type` / `trace_id` / `filter` / `run_ids` / …）比 freegraph 的四类本地过滤器宽（对应 **P-02** 的 DIFF + STRICTER 两半段） | C27 / DF6 已冻结 5 字段请求；不把过滤器面收窄会让契约漂移 | 本 feature |
| **X-7** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 空过滤器的上游表示是远端 `list_runs` 迭代器；freegraph 返回本地 `list[dict]`（对应 **P-04**） | C27 ③ 要求 JSON 可序列化；本地列表便于 CI 断言 | 本 feature |
| **X-8** | **STRICTER**（自研区 ①：零环境变量） | 上游 `LANGSMITH_*` 等环境变量可影响 tracing / 查询开关；freegraph 不读 env（对应 **P-07** 的 STRICTER 半段；默认关闭行为面 SAME） | 宪法原则 I / 配置层黑名单；查询只认显式 `TraceQuery` | 本 feature |

### §5 破冻结面的回溯修订清单 *(本 feature 触发)*

> 本 feature **不改写**已发布的 B20F1 / B19F1 事实，只做**增量接线**与**必要的断言拆分**。

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| `freegraph.observability.__all__` 的**精确集合断言**（B20F1 交付） | `tests/facade/test_api_snapshot.py` 的精确集合断言 · `tests/contracts/test_b19f1_lazy.py` 的成员断言 | **只增不改**：新增 `SqliteTraceStore` 到 L5 导出面；既有符号逐字保留；`FileTraceStore` 增加 `query` 方法（非新符号） | 在 `harness/verification/B20F2/manual-verification.md` 追认 |
| B20F1 的「`FileTraceStore` 公开面**没有**查询方法」断言 / 文字 | `specs/b20f1-local-trace-jsonl/spec.md` 的 Clarifications 与 SC-006 相关断言；`specs/b20f1-local-trace-jsonl/contracts/file-trace-store-contract.md` §1 / §8 | **拆分而不删**：保留「写侧符号 / 行为 / 四路诊断 / 0o600 / 锁不变」断言；把「无查询方法」改为「查询方法归 B20F2，本 feature 不改变写侧；B20F2 增加 `query`」 | 在 `harness/verification/B20F2/manual-verification.md` 追认；B20F1 记录不回溯改写 |
| B20F1 的 `FileTraceStore` 公开面快照（若含方法集合） | 对应快照测试 | **只增** `query`；写侧方法逐字不变 | 同上 |

> **不破的冻结面**：`Span` 11 字段 · `TraceSink` 3 方法 · `TraceRecord` 字段面 ·
> `TraceQuery` 5 字段 · `RunConfig` 9 字段 · `SuperStepResult` / `PregelTask` ·
> `stream()` 事件信封 · `freegraph.graph` 门面符号面 · L1 契约 22 符号 ·
> B20F1 的 JSONL 写侧行结构 / 文件命名 / `kind` / `0o600` / per-instance 锁 / 四路诊断。
> **唯一新增公开符号**：`freegraph.observability.SqliteTraceStore`（L5，不进
> `freegraph.graph` 门面，`import freegraph` 仍不加载 L5）；`FileTraceStore.query`
> 是既有类的新方法，不是新符号。

---

## Requirements *(mandatory)*

### Functional Requirements

#### A. 查询 API 与返回结构

- **FR-001**：系统 MUST 提供查询方法 **`query(query: TraceQuery | None = None) -> list[dict[str, Any]]`**，
  同时挂在 `FileTraceStore` 与 `SqliteTraceStore` 上；两个后端的签名 / 语义 MUST 完全一致，
  调用方 MUST NOT 需要 import 具体后端类。
- **FR-002**：查询 MUST 支持四类过滤条件：**`run_id`**、`thread_id`、时间范围、节点名；
  四者 MUST 可任意组合；所有非 `None` 条件以 **AND** 组合；`None` 是唯一的「不启用」值。
- **FR-003**：查询结果 MUST 为 **`list[dict[str, Any]]`**；每个元素 MUST 是纯数据，
  整个返回值 MUST 可被 `json.dumps` 直接序列化（C27 ③）；MUST NOT 含不可序列化对象。
- **FR-004**：结果元素 MUST 保留 B20F1 的行视图：
  - `kind="span"`：`kind` + `Span` **11/11** 字段；
  - `kind="trace_record"`：`kind` + `TraceRecord.to_jsonable()` **13/13** 字段。
  字段名 / 语义 MUST NOT 改名或重新定义；`span_id` ↔ `id` 关联 MUST 保留。
  **未知 `kind` MUST NOT 返回**：跳过并记 `logging.WARNING`；结果只含上述两种 `kind`。
  已知 `kind` 的行 MUST 含全部必需字段且类型正确；缺失 / 类型不符 ⇒ 跳过 + `WARNING`。
  行内**额外未知字段 MUST NOT 返回**（丢弃）；额外字段不影响必需字段校验与排序。
- **FR-005**：返回的列表 / 元素 MUST 是独立副本；调用方修改结果 MUST NOT 影响存储或后续查询。
- **FR-006**：结果 MUST 按 §5 的**有效起始时刻升序**排序，并按写死的平局规则稳定排序；
  同一存储、同一查询、同一快照的结果 MUST 逐条相同。
- **FR-007**：时间过滤 MUST 按 §6 的有效起始时刻、闭区间、UTC ISO-8601 瞬时比较；
  接受 `Z` / 带偏移 / 无时区（按 UTC）；非法查询时刻 ⇒ `ValueError`；倒置区间 ⇒ `[]`。
- **FR-008**：节点名过滤 MUST 为对 `node` 字段的**精确相等**匹配（大小写敏感、非子串）；
  MUST 采用**全部匹配**：返回该节点自身 span、该节点内部 `node` 同名的模型 / 工具 span、
  以及该节点的 `trace_record`；MUST NOT 因 `kind` / `name` 不同而排除子 span。
  `task_id` / `superstep` / `checkpoint_id` MUST NOT 作为过滤器（只作返回字段）。
- **FR-009**：查询 MUST 接受空过滤器（`TraceQuery()` 或 `query=None`），返回该存储中的
  **全部匹配条目**；MUST NOT 报错；**无隐式上限 / 截断**；v1 MUST NOT 提供
  `limit` / `offset` / 分页参数。
- **FR-010**：查询 MUST 是只读操作：MUST NOT 创建 / 截断 / 删除 / 改写存储；
  存储不存在 ⇒ 返回 `[]`；MUST NOT 触发建库 / 建表 / 迁移。
- **FR-011**：查询 MUST 采用「**尽量容错 + 告警**」的统一策略：
  - JSONL 单行无法解析（截断 / 非 JSON / 非对象）⇒ 跳过该行并记 `logging.WARNING`，
    其余行照常返回；
  - 行的 `kind` 未知 ⇒ 跳过 + `WARNING`；
  - 已知 `kind` 的行缺少必需字段 / 字段类型不符 / 携带额外未知字段 ⇒ 缺字段或类型不符
    跳过 + `WARNING`；额外字段丢弃、不影响成功；
  - JSONL 单个文件不可读（权限 / I/O）⇒ 跳过该文件并记 `WARNING`；若存在候选文件但
    全部不可读 ⇒ 异常交给查询调用方；
  - JSONL 候选文件是符号链接 ⇒ 跳过 + `WARNING`，MUST NOT 跟随读取；
  - 目录路径存在但不是目录（普通文件）⇒ 异常交给查询调用方；
  - SQLite 内部表结构不存在 ⇒ `[]`；旧表不兼容（缺必需列 / 类型冲突）⇒ 不修改旧表、
    `[]` + `WARNING`；**额外多出的列不视为不兼容**（读取时忽略）；单行 `payload` JSON 无法解码（含 `input_state` /
    `output_state` / `error`）⇒ 跳过该行 + `WARNING`；
    数据库损坏 / 非 SQLite / I/O 失败 ⇒ 异常交给查询调用方；
  - MUST NOT 因单行 / 单文件损坏使整个查询失败；MUST NOT 自动修复 / 迁移 / 删除 / 重建。
- **FR-012**：查询 MUST NOT 返回半行 / 未提交事务的条目；并发写入中的条目 MAY 被包含
  或跳过，但结果 MUST 始终可序列化且排序合法。
- **FR-013**：查询参数类型不正确时 MUST 抛 `TypeError`：`query` 本身不是 `TraceQuery` /
  `None`，或 `TraceQuery` 的 5 个字段任一不是 `str` / `None`。校验 MUST 在读取数据前完成；
  合法字符串但无法解析为时间 ⇒ `ValueError`（§6）。

#### B. SQLite 后端

- **FR-014**：系统 MUST 提供 **`freegraph.observability.SqliteTraceStore`**，
  只用标准库 `sqlite3`；MUST NOT 引入任何第三方依赖。
- **FR-015**：`SqliteTraceStore` 的注入形态 MUST 为
  `SqliteTraceStore(database=..., *, on_error=None)`；`database` 必填、无默认；
  单个本地 SQLite 文件路径；`:memory:` / SQLite URI 不支持（构造时 `ValueError`）；
  MUST NOT 读环境变量 / `expanduser` / `expandvars`。
- **FR-016**：`SqliteTraceStore` MUST 实现与 `FileTraceStore` 相同的 B19F1 sink 写侧：
  `on_span_start`（no-op）/ `on_span_end`（**仅当 `span.end_time is not None` 时写 span 行；
  `end_time is None` 的开始快照 MUST no-op，不建库 / 目录 / 表**）/ `on_trace_record`（写 record 行）/
  `current_span()`（恒 `None`）；**`run_id` 安全 allowlist（空 / 不安全 ⇒ 诊断 + 跳过）**；
  字段名 / `kind` / 行语义与 B20F1 一致；
  **MUST NOT** 提供 `close()` / `__enter__` / `__exit__` / 上下文管理器 / 公开连接对象。
- **FR-017**：`SqliteTraceStore` 的写入失败 MUST 与 B20F1 一样**永不阻断图执行**，
  并提供 `write_errors` / `last_error` / 可选 `on_error` / `logging.WARNING` 四路可感知；
  `Exception` 隔离、`BaseException` 不吞；MUST NOT 重试同一行。
- **FR-018**：`SqliteTraceStore` 的写入 MUST 每个 store 实例一把进程内锁串行化；
  MUST NOT 使用模块级全局锁；JSON 序列化 / 用户 `on_error` MUST 在锁外。
- **FR-019**：`SqliteTraceStore` MUST 惰性创建**父目录**、数据库文件与内部表结构
  （首次写行时；父目录 `parents=True, exist_ok=True`）；构造与查询 MUST NOT 创建文件 /
  目录 / 表。POSIX 上新建数据库文件权限 MUST 不宽于 `0o600`；已存在文件 MUST NOT 被
  主动放宽，实现 MAY 尝试收紧、失败不阻断写入。
- **FR-020**：SQLite 的跨进程并发 MUST 依赖 SQLite 文件锁并设置**有限忙等待超时**；
  并发写 + 查询 MUST NOT 损坏数据库；MUST 在 Linux 与 **Windows CI** 上验证。
  忙等待超时的写入按失败隔离；查询异常交给调用方。
- **FR-021**：SQLite 的表结构 / 列名 / SQL MUST 是内部实现细节；MUST NOT 作为公开 API
  暴露；对外只承诺 §3 的请求结构、§4 的返回结构与 §5–§8 的查询语义。
- **FR-022**：`SqliteTraceStore` 的查询结果 MUST 与 `FileTraceStore` 对同一份数据的
  查询结果**逐条等价**（条目数、字段值、排序）；`input_state` / `output_state` /
  `error` 等 JSON 视图 MUST 在读写往返后保持原语义。

#### C. `FileTraceStore` 查询扩展（写侧不变）

- **FR-023**：本 feature MUST 在**同一 `FileTraceStore` 对象上补齐 `query()`**；
  MUST NOT 改变 B20F1 已交付的 `on_span_start` / `on_span_end` / `on_trace_record` /
  `current_span` 写侧行为、文件命名、`kind` / 字段名、`0o600`、per-instance 锁与四路诊断。
- **FR-024**：`FileTraceStore.query` MUST 按 B20F1 已锁定的
  `trace-<run_id>.jsonl` 行结构解析（`kind="span"` / `kind="trace_record"`）；
  MUST NOT 要求 B20F1 新增查询方法或第二套序列化。
- **FR-025**：`FileTraceStore.query` MUST **只读取**文件名匹配
  `^trace-[A-Za-z0-9][A-Za-z0-9_-]*\.jsonl$` 的文件（`run_id` 段必须符合 B20F1 的
  allowlist）；其它 `trace-*.jsonl` 文件 MUST 跳过并记 `logging.WARNING`；
  候选文件是**符号链接** MUST 跳过并记 `WARNING`，MUST NOT 跟随读取（防止读出存储目录）；
  MUST NOT 读取 / 改写其它文件；`run_id` 过滤值 MUST NOT 被直接用于拼接路径
  （无目录穿越）；不安全 / 非 allowlist 的 `run_id` 过滤 ⇒ `[]`。

#### D. 边界、依赖与架构

- **FR-026**：查询与 SQLite 后端 MUST **零出站**；MUST NOT 访问网络 / 外部服务 / 账号 /
  API key；MUST NOT 读任何环境变量。
- **FR-027**：系统 MUST NOT import `langchain` / `langchain-core` / `langsmith` /
  `langgraph*`；基础安装第三方依赖闭包 MUST 保持为空；`sqlite3` 属标准库。
- **FR-028**：新增代码 MUST 位于 **L5**，只依赖标准库 + L1 `Span` / `TraceQuery` +
  同层 `TraceRecord` / `_payloads` / `_query` / `FileTraceStore`；MUST NOT import
  L2 / L3 / L4；MUST NOT 进入 `freegraph.graph` 门面；`import freegraph` MUST NOT 加载 L5。
- **FR-029**：查询 MUST NOT 被运行时自动调用；补齐查询 MUST NOT 改变图执行结果、
  写侧隔离或 B20F1 的诊断行为（宪法原则 IV「可视化不阻断执行」）。
- **FR-030**：`TraceQuery` 5 字段 / `Span` 11 字段 / `TraceRecord` 字段面 /
  `TraceSink` 3 方法 / `RunConfig` 9 字段 MUST NOT 修改；MUST NOT 新增 L1 `Protocol`。
  唯一新增公开符号为 `SqliteTraceStore`；`FileTraceStore.query` 是既有类的新方法。
- **FR-031**：本 feature MUST NOT 实现 OTLP 导出（B21F1）、前端 / UI（v2 / B26）、
  本地 Agent Server（v2 / D8）、Postgres 后端（v2）、保留期 / 清理（v1）、
  评测 / 数据集（永不做）。
- **FR-032**：交付物 MUST 按 §5 的「破冻结面回溯修订清单」更新 `observability.__all__`
  精确集合断言、B20F1 的「无查询方法」文字 / 断言（拆分而不删）与相关方法快照；
  MUST NOT 回溯改写 B20F1 已发布的其它事实。
- **FR-033**：交付物 MUST 包含 `harness/verification/B20F2/manual-verification.md`，
  记录：四类过滤 + 组合的实测输出、JSONL / SQLite 等价结果、空过滤器结果、稳定排序、
  `json.dumps` 证据、并发写 + 查询证据（含 Windows 说明）、零出站证据、
  `__all__` / B20F1 断言修订的追认、**质量门禁 5 偏离声明**与发起者追认文字。
- **FR-034**：交付物 MUST 更新 `harness/demo/README.md` / `harness/verification/README.md`
  中与 B20F2 相关的行（查询 API 的稳定接口、SQLite 后端形态、内部格式不入 UI）。

### Key Entities *(include if feature involves data)*

- **`TraceQuery`**（L1，B2F1 冻结，本 feature 原样消费）：5 字段查询请求
  （`run_id` / `thread_id` / `node` / `start_time` / `end_time`），全可空、可组合。
- **查询结果条目**（本 feature 对外数据形态）：B20F1 行视图的纯 `dict`；
  `kind="span"`（11 字段）或 `kind="trace_record"`（13 字段）；整体可 JSON 序列化。
- **`FileTraceStore`**（L5，B20F1 交付）：JSONL 写入后端；本 feature 增加 `query()`，
  写侧行为不变。
- **`SqliteTraceStore`**（L5，本 feature 新增）：SQLite 写入 + 查询后端；写侧与
  `FileTraceStore` 同语义，查询结果等价；内部 schema 不对外。
- **`Span`**（L1，B2F1 冻结）：11 字段；查询返回其落盘视图。
- **`TraceRecord`**（L5，B19F1 交付）：13 字段；`to_jsonable()` 是唯一稳定视图；
  查询返回其落盘视图。
- **`write_errors` / `last_error` / `on_error`**（B20F1 诊断面，`SqliteTraceStore` 沿用）：
  写入失败的四路可感知信号；不是查询 API。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001（A1 · run 检索）**：写入 2 次运行（`run_id` 不同）的 trace；按 `run_id`
  查询 ⇒ 只返回该次运行的全部条目；另一运行的条目数 **== 0**；该运行的节点 / 工具 /
  模型 span 与节点 record 全部在内。
- **SC-002（A2 · thread 检索）**：写入 2 个 `thread_id` 的 trace；按 `thread_id`
  查询 ⇒ 只返回该 thread 的条目；另一 thread 的条目数 **== 0**。
- **SC-003（A3 · 时间检索）**：时间窗查询 ⇒ 窗内条目全部返回、窗外条目 **== 0**；
  边界时刻条目被包含；倒置区间返回 `[]`。
- **SC-004（A4 · 节点检索）**：按节点名过滤 ⇒ 返回条目 `node` 全部等于该节点名；
  该节点内部的模型 / 工具 span 与 `trace_record` **均在内**；其它节点条目 **== 0**。
- **SC-005（A5 · 组合过滤）**：四类过滤两两 / 多项组合 ⇒ 返回条目同时满足全部条件
  （AND）；与逐条过滤结果的交集（按同一排序键排序后）逐条相等。
- **SC-006（A6 · 后端可替换）**：同一份事件流分别写入 JSONL / SQLite；对同一
  `TraceQuery`（含空过滤器与四类过滤 + 组合）⇒ 两个后端的条目数、字段值、排序**逐条相等**；
  完全相同的重复行按**多重集合**比较（不比较其相对顺序）；不等条目数 **== 0**。
- **SC-007（空过滤器）**：在**只含合法 B20F1 行**的存储上，`TraceQuery()` 与
  `query=None` 都返回全部条目，条数 == 写入条数；无异常；无隐式截断。
  坏行 / 未知 kind / 字段残缺按 §8 跳过，不计入该等式的写入条数。
- **SC-008（JSON 可序列化）**：对每个查询结果执行 `json.dumps(result)` ⇒ 成功率
  **100%**；结果元素只含纯数据类型；不可序列化对象出现次数 **== 0**。
- **SC-009（稳定排序）**：同一查询连续执行 N 次、两个后端分别执行 ⇒ 结果逐条相同；
  排序符合 §5 的键；顺序不稳定次数 **== 0**。
- **SC-010（写侧不变）**：B20F1 的写侧回归全绿：文件命名 `trace-<run_id>.jsonl`、
  `kind` 双行、字段名 / 值、`0o600`（POSIX）、per-instance 锁、`write_errors` /
  `last_error` / `on_error` / WARNING、失败不阻断 / 不重试 / 无半行 —— 改动前后
  **逐条一致**；`FileTraceStore` 新增 `query` 方法不改变任何写侧断言。
- **SC-011（SQLite 持久化 / 并发）**：SQLite 写入后可由查询读回；并发写 + 查询
  （线程 / 进程）⇒ 数据库损坏次数 **== 0**、半行 / 未提交条目 **== 0**；
  Windows CI 用例不因文件锁差异失败（忙等待超时按既定语义处理）。
- **SC-012（零出站 / 零 env / 零第三方）**：socket 监测夹具断言「框架出站 == 0」；
  环境变量读取次数 **== 0**；`langchain*` / `langsmith` / `langgraph*` import 次数 **== 0**；
  基础安装依赖闭包仍为空集；`sqlite3` 为标准库。
- **SC-013（只读 / 容错 / 无副作用）**：存储不存在时查询 ⇒ `[]`，文件 / 目录 / 表新增数
  **== 0**；JSONL 坏行 / 未知 `kind` / 字段残缺 / 非 allowlist 文件名 / 符号链接文件
  被跳过且产生 WARNING；**存在候选文件但全部不可读 ⇒ 抛底层异常给调用方**；
  SQLite 不兼容旧表**未被修改**（前后哈希不变）、单行
  `payload` JSON 损坏只跳过该行；目录路径是普通文件 / SQLite 文件损坏时抛错给调用方；
  查询前后存储文件哈希不变；返回结果被修改后再次查询结果不变。
- **SC-014（内部格式边界 / 严格字段面）**：**读取面**只暴露 `query()` 与 §4 返回结构
  （写入面沿用 B19F1 sink 回调与 `write_errors` / `last_error` / `on_error` 诊断面）；
  MUST NOT 暴露表名 / 列名 / SQL / 文件格式构造器；结果元素只含已冻结字段，
  **额外未知字段出现次数 == 0**；`FileTraceStore` 与 `SqliteTraceStore` 均无
  「直连 schema」的公开方法。
- **SC-015（人工门禁）**：`harness/verification/B20F2/manual-verification.md` 存在，
  且含**非空**的四类过滤 / 组合实测输出、两后端等价证据、空过滤器 / 排序证据、
  `json.dumps` 输出、并发写 + 查询证据（含 Windows 说明）、零出站证据、
  `__all__` / B20F1 断言修订追认、**质量门禁 5 偏离声明**与发起者追认文字；
  由自动文档守卫核验。
- **SC-016（验收映射）**：A1–A6 每条都有至少一个可判定用例（见 §验收判据）。
- **SC-017（输入校验）**：`TraceQuery` 任一字段传非 `str` / `None` ⇒ 读取前抛 `TypeError`，
  返回条目数 **== 0**；5 个字段全为合法 `str` / `None` 时不因校验误报；
  合法字符串但时间不可解析 ⇒ `ValueError`。
- **SC-018（SQLite 落盘形态）**：`:memory:` / SQLite URI ⇒ 构造时 `ValueError`；
  首次写行时惰性创建父目录、数据库文件与表（开始快照 no-op 不创建任何文件 / 表）；
  构造与查询不创建文件 / 目录 / 表；POSIX 新建数据库文件 `mode & 0o077 == 0`；
  已存在文件权限不被主动放宽；父目录不可写时写入失败被四路诊断隔离、不阻断运行。

### 验收判据（= 立项书 §5.2 B20F2 小目标，逐条可判定）

> 小目标原文：可按 thread / 时间 / 节点名检索

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | **可按 run 检索** | 用例：按 `run_id` 过滤（一次运行的全部 span / record） |
| A2 | 可按 thread 检索 | 用例：按 `thread_id` 过滤 |
| A3 | 可按时间检索 | 用例：时间窗过滤（闭区间；窗外排除） |
| A4 | 可按节点名检索 | 用例：按节点名精确过滤 |
| A5 | 四类过滤**组合** | 组合用例（如 `run_id` + 节点名 + 时间窗） |
| A6 | 两后端可替换 | 同一查询在 JSONL / SQLite 后端结果逐条等价 |

---

## Dependencies & Out of Scope

### Dependencies

- **B20F1**（已交付）：`FileTraceStore` / `trace-<run_id>.jsonl` / `kind` 双行 /
  `Span` 11 字段 / `TraceRecord.to_jsonable()` 13 字段 / `span_id` ↔ `id` 关联 /
  `run_id` allowlist / 四路诊断 / per-instance 锁 / `0o600`。本 feature 读取其落盘
  数据，并在同一对象上补齐查询。
- **B19F1**（已交付）：`TraceRecord.to_jsonable()` 是唯一稳定 JSON 视图；本 feature
  MUST NOT 要求第二套序列化。
- **B18F1**（已交付）：span 提供 `run_id` / `thread_id` / `node` / `checkpoint_id`；
  v1 不把 `checkpoint_id` 作为过滤器。
- **B2F1 / C27 / DF6 / C23**：`TraceQuery` 5 字段请求结构、查询契约、关联键字段约定。
- **B21F1**（后续）：OTLP 导出插件 + 后端对接文档；与本 feature 的 `query()` 无直接
  数据依赖（B21F1 导出 `Span`，不消费查询 API）；其文档可选复用本 feature 的查询证据。

### Out of Scope

- **OTLP 导出 / 远端后端** —— B21F1。
- **前端 / UI / Studio** —— v2 / B26；Studio 只能走本 feature 的 `query()`，不直连
  SQLite 表或 JSONL 文件。
- **本地 Agent Server** —— v2 / D8。
- **Postgres 后端** —— v2 范围，未排 feature。
- **保留期 / 清理 / 轮转 / 压缩** —— v1 不做。
- **评测 / 数据集** —— 永不做。
- **`checkpoint_id` / `task_id` / `superstep` 过滤器** —— v1 不支持；新增走 C27 修订。
- **分页 / 上限 / `limit` / `offset`** —— v1 不提供；新增走 C27 修订。

---

## 质量门禁偏离（2026-11-21 · 发起者选择 A；2026-11-22 确认沿用 B20F1 先例）

### 质量门禁 5 · 真实模型轮

| 项 | 内容 |
|---|---|
| 被偏离门禁 | 质量门禁 5「人工验证记录，含真实模型一轮」 |
| 根因 | B20F2 是 **L5 本地 trace 读取层 + SQLite 后端**；验收对象是过滤语义、排序、后端等价与并发读写的正确性。真实模型轮不产生本 feature 的新判据，反而引入 provider 依赖。**本条沿用 B20F1（2026-11-21 · 发起者选择 A）的同一偏离口径**；判据未放宽。 |
| 判据未放宽 | 本地图 + fake 模型 / 本地 sink 的轮次照常执行；四类过滤、组合、空过滤器、排序、JSON 序列化、两后端等价、零出站、零环境变量、写侧回归等判据**一字未改**；人工记录五段式照常。 |
| 承接方 / 机制 | **B25F1（M4 · 双跑验收）**：在 B25F1 的人工验收中补真实模型轮（含 `SqliteTraceStore` / `FileTraceStore` 查询证据）；承接条款已写入 `harness/features/B25F1_双跑验收与迁移说明.md` 的「下游承接（B20F2）」；由 B20F2 tasks 的 T058 守卫。B21F1（OTLP）可选复用。B20F2 只交付 fake / 本地轮证据。 |
| 追认 | 发起者 2026-11-21 **选择 A（登记偏离）**；2026-11-22 分析会话**确认沿用 B20F1 先例**并补 B25F1 接线。正式追认文字 + 确认人 + 日期落 `harness/verification/B20F2/manual-verification.md`，由发起者本人签署。 |

> **先例**：B20F1 / B19F1 已按同一口径登记「fake / 本地轮 + 真实模型轮由后续 feature
> 承接」；本偏离**不降低**任何红线判据，也不改变 B20F2 的 A1–A6 验收。
> **适用依据**：本条沿用 B20F1 先例（非新增豁免），承接方 = B25F1（M4）；
> 承接条款见 `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B20F2）」。
> **未完成 B25F1 接线守卫（T058）前，本偏离不得视为已有效承接。**

---

## Assumptions

- **请求结构**沿用 B2F1 已冻结的 `TraceQuery`（5 字段）；本 feature **不新增字段**。
- **返回结构**锁定为 B20F1 行视图的 `list[dict]`；不重建 `Span` / `TraceRecord` 对象，
  不改变 `to_jsonable()`。
- **写入顺序 / 文件格式**已由 B20F1 写死；本 feature 只读，不重写、不迁移、不压缩。
- **时间语义**以 span 的 `start_time` 为事件时刻；record 用其关联 span 的 `start_time`；
  这是 C27 `TraceQuery` 只有一组时间界时的最简一致口径。
- **record ↔ span 关联**限定在**同一 `run_id`** 内（`(run_id, span_id)` ↔ `(run_id, id)`）；
  不同运行的 `span_id` 可能碰撞，不得跨 run 关联。
- **节点语义**：`node` 是图节点名；`task_id`（fan-out 时 `节点名:TaskId`）只作返回字段，
  不是 v1 过滤器。
- **空过滤器无上限**：v1 面向本地诊断与 CI 断言，单次运行规模有限；调用方负责控制
  存储规模。未来若需要分页 / 上限，走 C27 修订。
- **查询只读**：查询缺省不创建任何存储；这保证「只查一下」不会留下副作用。
- **SQLite 单文件**：`database` 是本地文件路径；v1 不提供连接对象 / URI / 网络数据库注入；
  `:memory:` / URI 不支持（构造时 `ValueError`）。
- **SQLite 表结构内部**：schema 变化不承诺兼容旧数据库；v1 不做迁移 / 版本号。
  若实现需要 schema 版本，MUST 为内部细节且不改变对外查询语义。
- **SQLite 落盘形态**：首次写行惰性创建父目录；新建数据库文件 `0o600`；已存在文件
  不主动放宽、可尝试收紧且失败不阻断；不兼容旧表不修改、返回空 + WARNING。
- **符号链接**：JSONL 查询不跟随候选文件符号链接（跳过 + WARNING）；用户显式传入的
  SQLite `database` 路径按用户意图打开。
- **并发**：单进程内由 per-instance 锁串行；跨进程依赖 SQLite 文件锁 + 有限忙等待；
  Windows 文件锁差异以 CI 用例覆盖，超时按「写入失败隔离 / 查询异常交调用方」处理。
- **失败隔离**：查询不在运行时自动执行；任何查询异常都不会进入图执行路径。
  写入失败继续沿用 B20F1 的四路诊断与「不阻断」承诺。
- **`BaseException`**：`KeyboardInterrupt` / `SystemExit` 等不被吞；只有 `Exception`
  范围的写入 / 查询失败被按本 spec 的语义处理。
- **内部格式边界**：表结构 / 文件格式 / 列名 / SQL 是内部实现细节（C27 ⑤）；
  Studio / 测试 / 用户只能经 `query()` 取数。
- **文档联动**：实现阶段 MUST 更新 `harness/demo/README.md`、
  `harness/verification/README.md` 的 B20F2 行，并生成
  `harness/verification/B20F2/manual-verification.md`；该记录 MUST 由自动文档守卫
  核验，且 MUST 含质量门禁 5 偏离声明与发起者追认文字。
