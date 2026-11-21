# Contract: Trace 查询 API（`query`）

**Feature**: B20F2 · **Date**: 2026-11-22 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)

> `query()` 是 **L5** 本地 trace 的**稳定读取接口**。表结构 / 文件格式是 C27 ⑤ 的
> **内部实现细节**；Studio / 测试 / 用户 MUST NOT 直连 SQLite 表或 JSONL 文件。
> 本 contract 把**对外可见的查询语义**写死，`/speckit.implement` MUST 照此执行。

---

## 1. 公开签名

```python
class FileTraceStore:
    def query(self, query: TraceQuery | None = None) -> list[dict[str, Any]]: ...

class SqliteTraceStore:
    def query(self, query: TraceQuery | None = None) -> list[dict[str, Any]]: ...
```

| 规则 | 内容 |
|---|---|
| 两个后端 | 同一签名 / 同一语义；调用方 MUST NOT 需要 import 具体后端类 |
| `query=None` | 等价于 `TraceQuery()`（空过滤器） |
| 非 `TraceQuery` / 非 `None` | `TypeError`（读取前） |
| 字段类型 | 5 字段任一非 `str` / `None` ⇒ `TypeError`（读取前） |
| 同步 | v1 同步；无 async |
| 自动调用 | 运行时 MUST NOT 自动调用 `query()` |
| 返回 | 新 `list[dict]`；元素为独立副本 |

**MUST NOT 提供**：`limit` / `offset` / 分页参数；`search` / `read` / `read_all` 等
第二套读取 API；表名 / 列名 / SQL / 连接对象。

---

## 2. 请求（`TraceQuery` · 冻结）

```python
TraceQuery(
    run_id=None,
    thread_id=None,
    node=None,
    start_time=None,
    end_time=None,
)
```

| 字段 | 匹配 |
|---|---|
| `run_id` | 条目 `run_id` **精确相等**；`None` 不启用 |
| `thread_id` | 条目 `thread_id` **精确相等**；`None` 不启用 |
| `node` | 条目 `node` **精确相等**（大小写敏感、非子串）；`None` 不启用 |
| `start_time` | 闭区间下界（含）；UTF-8 / UTC ISO-8601 |
| `end_time` | 闭区间上界（含）；UTF-8 / UTC ISO-8601 |

**组合**：所有非 `None` 字段 **AND**；`TraceQuery()` = 取全部；`None` 是唯一「不启用」；
`""` 是字面值（通常 `[]`）。

**v1 不支持的过滤器**：`checkpoint_id` / `task_id` / `superstep` / `kind` /
`name` / `parent` / 错误状态。`checkpoint_id` / `task_id` / `superstep` 只作返回字段。

---

## 3. 返回（`list[dict[str, Any]]`）

### 3.1 只允许两种 `kind`

- `kind="span"`：`kind` + `Span` **11 字段**。
- `kind="trace_record"`：`kind` + `TraceRecord.to_jsonable()` **13 字段**。
- 其它 `kind` ⇒ 跳过 + `logging.WARNING`；**不返回**。

### 3.2 字段规则

| 规则 | 内容 |
|---|---|
| 字段名 | 逐字沿用 B20F1 / B19F1；MUST NOT 改名 / 重新定义 |
| 必需字段 | 已知 `kind` MUST 含该 kind 的全部必需字段且类型正确 |
| 额外字段 | **丢弃**，不返回 |
| 关联 | `trace_record.span_id` ↔ `span.id` 原样保留（不物化联合字段） |
| 纯数据 | `dict` / `list` / `str` / `int` / `float` / `bool` / `None`；无对象 / 类 / 函数 / 句柄 |
| 序列化 | 整个返回值 MUST 可 `json.dumps(result)` |
| 副本 | 返回列表 / 元素是独立副本；调用方修改不影响存储 / 后续查询 |

### 3.3 缺字段 / 类型不符

| 场景 | 行为 |
|---|---|
| 未知 `kind` | 跳过 + WARNING |
| 已知 `kind` 缺必需字段 | 跳过 + WARNING |
| 已知 `kind` 字段类型不符 | 跳过 + WARNING |
| 额外未知字段 | 丢弃；不影响成功 |
| `superstep=True`（`bool`） | 类型不符（`type(x) is int` 才通过）⇒ 跳过 |

---

## 4. 节点过滤（A4）

**精确相等 + 全部匹配**：

- 节点 `b` 自身 span（`node == "b"`）；
- 节点 `b` 内部产生的模型 / 工具 span（其 `node` 也是 `"b"`）；
- 节点 `b` 的 `trace_record`。

MUST NOT 因 `kind` / `name` 与节点不同而排除子 span。`task_id`（fan-out 时
`节点名:TaskId`）**不是** v1 过滤器；它只作返回字段。

---

## 5. 时间窗（A3）

| 规则 | 内容 |
|---|---|
| 精度 | UTC ISO-8601 → **纳秒**整数；MUST NOT 截断到微秒 |
| 时区 | 接受 `Z` / `±HH:MM` / `±HHMM`；无时区按 UTC |
| 区间 | **闭区间** `[start_time, end_time]`；边界包含 |
| 单边 | 只给 `start_time` ⇒ 仅应用下界（上界无界）；只给 `end_time` ⇒ 仅应用上界（下界无界） |
| 比较对象 | **有效起始时刻**（见 §6） |
| 倒置 | `start_time > end_time` ⇒ `[]`；不抛错、不交换 |
| 非法串 | `ValueError`（读取前） |

---

## 6. 有效起始时刻与排序（A1/A2/A5/A6）

### 6.1 有效起始时刻

| 条目 | 有效起始时刻 |
|---|---|
| `span` | 该 span 的 `start_time` |
| `trace_record` | 同一 `run_id` 且 `span_id == id` 的 span 的 `start_time` |
| record 无关联 span | **无时刻** |

- 关联 MUST 在 `(run_id, span_id)` ↔ `(run_id, id)` 内；**MUST NOT 跨 run**。
- 「可见」= 满足同一查询过滤、且被本次查询读取到的 span。

### 6.2 排序

```text
timed.sort(key=(start_ns, run_id, kind_rank, stable_id))
  kind_rank: trace_record=0, span=1
  stable_id: record.span_id / span.id

untimed.sort(key=(run_id, superstep, task_id, span_id))

result = timed + untimed
```

- 有时刻在前；无时刻 record 在后。
- 同一存储 / 查询 / 快照 ⇒ 结果逐条相同；两后端排序相同。
- 完全相同的重复行相对顺序 MAY 任意；不影响其它条目。
- 跨后端比较时，**完全相同的重复行按多重集合比较**（不比较其相对顺序）。

---

## 7. 空过滤器 / 上限（A5 / SC-007）

- `query(None)` / `TraceQuery()` MUST 合法；返回存储中全部**合法**匹配条目
  （坏行 / 未知 kind / 字段残缺按 §9 跳过）。
- **无隐式截断**；v1 不提供 `limit` / `offset` / 分页。
- 未来分页 / 上限 MUST 走 C27 契约修订。

---

## 8. 只读 / 副作用

- 查询 MUST NOT 创建 / 截断 / 删除 / 改写任何存储文件 / 表。
- MUST NOT 触发建库 / 建表 / 索引 / 迁移 / 修复 / 重建。
- 存储不存在 ⇒ `[]`；构造 / 查询零副作用。
- 查询前后存储文件哈希 MUST 不变。
- 查询不在图执行路径；任何查询异常不进入 `on_span_start` / `on_span_end` /
  `on_trace_record` / `current_span`。

---

## 9. 容错（尽量容错 + 告警）

| 场景 | 行为 |
|---|---|
| JSONL 行无法解析（截断 / 非 JSON / 非对象） | 跳过 + WARNING |
| 未知 `kind` | 跳过 + WARNING |
| 已知 `kind` 缺字段 / 类型不符 | 跳过 + WARNING |
| 已知 `kind` 额外字段 | 丢弃；不失败 |
| JSONL 单文件不可读（权限 / I/O） | 跳过 + WARNING；全部普通候选不可读 ⇒ 抛错 |
| JSONL 候选是符号链接 | 跳过 + WARNING；不跟随 |
| JSONL 文件名非白名单 | 跳过 + WARNING |
| 目录路径是普通文件 | 抛底层异常给调用方 |
| SQLite 表不存在 | `[]` |
| SQLite 旧表缺必需列 / 类型冲突 | `[]` + WARNING；不修改；额外多出的列忽略 |
| SQLite 单行 `payload` JSON 无法解码（含嵌套 `input_state` / `output_state` / `error`） | 跳过 + WARNING |
| SQLite 文件损坏 / 非 SQLite / I/O | 抛底层异常给调用方 |
| 写入进行中 | 不返回半行 / 未提交事务；条目 MAY 包含或跳过 |

**MUST NOT**：自动修复 / 迁移 / 删除 / 重建；静默吞掉整库错误。

---

## 10. 后端可替换（A6 / SC-006）

- 同一份 B19F1 事件流分别写入 `FileTraceStore` / `SqliteTraceStore`；
- 对同一 `TraceQuery`（空过滤器 + 四类过滤 + 组合）查询；
- 两个结果列表的**条目数 / 字段值 / 排序逐条相等**；
  **完全相同的重复行按多重集合比较**（不比较其相对顺序）。
- 不等 ⇒ 缺陷，MUST NOT 以「后端差异」解释。

---

## 11. 明确不做

- `limit` / `offset` / 分页。
- `checkpoint_id` / `task_id` / `superstep` / `kind` / `name` / `parent` 过滤。
- 返回 `Span` / `TraceRecord` 对象。
- 直连 SQLite 表 / JSONL 文件。
- OTLP / UI / Postgres / 保留期 / 评测（见 spec Out of Scope）。

---

## 12. 验收映射

| 判据 | 覆盖 |
|---|---|
| A1 按 run | `run_id` 精确过滤 |
| A2 按 thread | `thread_id` 精确过滤 |
| A3 按时间 | 闭区间 / 有效起始时刻 / 倒置 |
| A4 按节点 | 精确匹配 + 全部子 span / record |
| A5 组合 | 四类 AND + 空过滤器 |
| A6 两后端 | 同一查询逐条等价 |
| SC-003 / SC-008 | 纯数据 + `json.dumps` |
| SC-009 | 稳定排序 |
| SC-013 / SC-014 | 只读 / 容错 / 严格字段面 |
| SC-017 | 类型校验 |
