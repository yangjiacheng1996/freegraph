# Research: B20F2 · Trace 查询 API + SQLite 后端

**Date**: 2026-11-22
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Baseline**: `.venv/bin/python -m pytest -q --tb=no` ⇒ **1991 passed, 7 skipped**（2026-11-22 实跑）
**Upstream**: `langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`（`.venv` 实测）
**Python**: `.venv` 3.11.16；`requires-python >= 3.11`

> 本文件只记录**设计决策**（Decision / Rationale / Alternatives），不重复 spec 的 FR/SC。
> 上游行为断言来自 spec 的 P-01…P-07 / E-1…E-3；本 feature 不新增上游行为探针。
> 所有 I/O 决策都服从三条红线：**零第三方依赖**、**零出站 / 零环境变量**、
> **L5 只依赖 L1（同层允许）**。

---

## D-01 · 公开读取载体：两个 store 上同一 `query(TraceQuery | None)`

- **Decision**：`freegraph.observability.FileTraceStore` 与
  `freegraph.observability.SqliteTraceStore` 都提供：

  ```python
  def query(self, query: TraceQuery | None = None) -> list[dict[str, Any]]: ...
  ```

  `None` ≡ `TraceQuery()`；空过滤器返回全部匹配条目；不提供 `limit` / `offset`。
- **Rationale**：spec FR-001 / C27 ④ 锁定；`TraceQuery` 已在 B2F1 逐字冻结（5 字段）；
  同一签名让调用方按鸭子类型替换后端，不需要 import 具体类；不新增 L1 `Protocol`
  （避免契约修订）。
- **Alternatives considered**：
  - 在 L1 新增 `TraceStore` / `TraceQueryable` Protocol ⇒ 破 L1 冻结面 / 需契约修订。
  - 独立函数 `query_traces(store, q)` ⇒ 调用方仍依赖具体类型，弱化可替换性。
  - 返回 `Span` / `TraceRecord` 对象 ⇒ 违反 C27 ③ 的 JSON 可序列化要求，且需第二套序列化。
  - 把 `limit` / `offset` 塞进 `TraceQuery` ⇒ 改冻结字段面；spec 明确 v1 不做分页。

---

## D-02 · 共享查询引擎：`_query.py`（纯函数、无 I/O）

- **Decision**：新增 `src/freegraph/observability/_query.py`，提供：
  - `normalize_query(query) -> TraceQuery`：类型校验 + 空值归一。
  - `parse_instant_ns(text) -> int`：UTC ISO-8601 → 纳秒整数；非法 ⇒ `ValueError`。
  - `normalize_row(row) -> dict | None`：按 `kind` 校验必需字段 / 类型；丢弃额外字段；
    未知 kind / 残缺 ⇒ `None`（调用方记 WARNING）。
  - `finalize(rows, query) -> list[dict]`：构建 `(run_id, span_id) -> start_ns` 索引、
    四类过滤、有效起始时刻、稳定排序、返回独立列表。
  - 模块只 import 标准库 + L1 `TraceQuery` + 同层 `TraceRecord`；**不 import `sqlite3` / 文件 API**。
- **Rationale**：A6 要求两后端对同一查询逐条等价；共享一套过滤 / 排序 / 校验是
  **唯一可机械保证**的方式，避免两份逻辑漂移。纯函数便于单元测试与复用。
- **Alternatives considered**：
  - 每个后端各写一套 ⇒ 语义漂移，A6 只能靠碰巧。
  - 把查询逻辑放 `_file_store.py`，SQLite 反向 import ⇒ 后端耦合 / 循环风险。
  - 用 SQL 完成全部过滤 / 排序 ⇒ JSONL 无法复用；record 与 span 的跨行关联也难统一。
  - 引入 ORM / 查询库 ⇒ 破零第三方依赖。

---

## D-03 · 共享行构造：`_payloads.py`

- **Decision**：新增 `src/freegraph/observability/_payloads.py`：
  - `span_to_dict(span: Span) -> dict[str, Any]`：手工 11 字段 + `kind="span"`。
  - `record_to_dict(record: TraceRecord) -> dict[str, Any]`：
    `{"kind": "trace_record", **record.to_jsonable()}`。
  - `_file_store.py` 改为 import 这两个函数；原 `_span_to_dict` / `_record_to_dict`
    删除（纯函数搬迁，**行为逐字不变**）。
- **Rationale**：两后端必须写 / 读**同一行视图**；共享构造避免字段顺序 / 浅拷贝 /
  `kind` 包装出现第二套。原则 XII「零重复载体」。
- **Alternatives considered**：
  - 在 `_file_store.py` 保留并让 `_sqlite_store.py` import 私有函数 ⇒ 后端耦合，
    SQLite 模块依赖 JSONL 模块，职责不清晰。
  - 两处各复制一份 ⇒ 字段漂移风险；B20F1 契约测试可能只覆盖一份。
  - 用 `dataclasses.asdict` ⇒ 深拷贝 / 嵌套对象更敏感；B20F1 已明确不用。

---

## D-04 · JSONL 查询：只读扫描 + 白名单 + 容错

- **Decision**：`FileTraceStore.query()`：
  1. `normalize_query` / 时间解析在读取前完成；
  2. 若 `query.run_id` 非空且不符合 `^[A-Za-z0-9][A-Za-z0-9_-]*$` ⇒ 直接返回 `[]`；
  3. `directory` 不存在 ⇒ `[]`；存在但不是目录 ⇒ 抛 `NotADirectoryError`；
  4. 用 `Path.iterdir()`（或 `os.scandir`）枚举候选：
     - 文件名 MUST 匹配 `^trace-<safe run_id>\.jsonl$`；否则跳过 + WARNING；
     - 候选是**符号链接** ⇒ 跳过 + WARNING；MUST NOT 跟随；
     - 只接受普通文件；
     - 若 `query.run_id` 非空，只读对应 run 文件；
  5. 逐行 `json.loads`；`normalize_row`；坏行 / 未知 kind / 残缺 ⇒ 跳过 + WARNING；
  6. `finalize`；返回。
  - 查询**不获取写入锁**；读取到正在追加的半行 ⇒ `json.loads` 失败 ⇒ 跳过。
  - 单文件 I/O 失败 ⇒ 跳过 + WARNING；若存在普通候选文件但全部不可读 ⇒ 抛最后一个异常。
- **Rationale**：spec FR-010 / FR-011 / FR-024 / FR-025；B20F1 只写不读，本 feature 自己读；
  白名单 / 符号链接规则防外部数据与目录外读取；不加读锁避免影响写侧。
- **Alternatives considered**：
  - 对所有 `trace-*.jsonl` 宽松读取 ⇒ 可能读入外部 / 遗留文件，违反 spec。
  - 跟随符号链接 ⇒ 可能读出存储目录外内容。
  - 查询持写入锁 ⇒ 与写线程竞争，违背「写侧不变 / 不阻断」；且不必要。
  - 让 B20F1 增加读方法 ⇒ 违反 D-3「B20F1 只写不读」。

---

## D-05 · SQLite 内部 schema：单表 `trace_entries`

- **Decision**：内部表（表名 / 列名**不对外**）：

  ```sql
  CREATE TABLE IF NOT EXISTS trace_entries (
      seq        INTEGER PRIMARY KEY AUTOINCREMENT,
      kind       TEXT NOT NULL,
      run_id     TEXT NOT NULL,
      thread_id  TEXT,
      node       TEXT NOT NULL,
      checkpoint_id TEXT,
      span_id    TEXT NOT NULL,
      start_time TEXT,
      payload    TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_trace_run ON trace_entries(run_id);
  CREATE INDEX IF NOT EXISTS idx_trace_thread ON trace_entries(thread_id);
  CREATE INDEX IF NOT EXISTS idx_trace_node ON trace_entries(node);
  CREATE INDEX IF NOT EXISTS idx_trace_span ON trace_entries(run_id, span_id);
  CREATE INDEX IF NOT EXISTS idx_trace_start ON trace_entries(start_time);
  ```

  - `payload` = B20F1 行视图的 `json.dumps(..., ensure_ascii=False)`；
  - `span_id` = span 的 `id` 或 record 的 `span_id`；
  - `start_time` = span 的 `start_time`；record 为 `NULL`；
  - 查询**读取全部 payload**，用 `json.loads` 还原后交给 `_query.finalize`。
- **Rationale**：schema 是 C27 ⑤ 的内部细节；单表 + payload 保证写入 / 读取行视图与
  JSONL **逐字同源**；v1 以正确性 / 等价性优先，不做 SQL 下推；索引为未来优化留位。
  `seq` 仅内部排序 / 调试，查询排序仍由 `_query.finalize` 决定。
- **Alternatives considered**：
  - 多表规范化（span / record / state 分表）⇒ 读写复杂、JOIN 多、行视图易漂移。
  - 只存 JSONL 文本 / 文件指针 ⇒ 失去 SQLite 的持久化 / 并发价值。
  - SQL 下推全部过滤 / 排序 ⇒ record 需 JOIN span、时间窗与无时刻 record 语义复杂，
    两后端等价难保证。
  - 公开表名 / 列名 ⇒ 违反 C27 ⑤ 数据访问边界。

---

## D-06 · SQLite 连接与并发：短生命周期连接 + per-instance 锁 + busy timeout

- **Decision**：
  - 每个 store 实例持有自己的 `threading.Lock`；写操作与诊断更新在锁内；
    JSON 序列化与 `on_error` 在锁外；
  - **每次写 / 查询使用短生命周期 `sqlite3.connect`**，用 `try/finally` 关闭；
    `timeout=5.0`（或 `PRAGMA busy_timeout=5000`）；
  - 查询不持有写入锁（与 JSONL 一致，避免阻塞写）；
  - 跨进程依赖 SQLite 文件锁；超时写入 ⇒ 失败隔离；查询超时 ⇒ 异常交调用方；
  - 不使用模块级全局锁 / 连接池 / 持久连接。
- **Rationale**：短生命周期连接避免线程亲和（`check_same_thread`）、持久句柄、
  关闭 API、跨进程 stale 连接；与 B20F1「逐行短生命周期」口径一致。SQLite 自身
  处理跨进程文件锁；有限 busy timeout 防止无限等待。
- **Alternatives considered**：
  - 每实例一个持久连接（`check_same_thread=False`）⇒ 线程安全 / 关闭 / WAL 生命周期复杂。
  - 连接池 ⇒ 引入额外状态 / 第三方或自研池，超出范围。
  - 无 busy timeout ⇒ Windows 文件锁冲突下立即失败 / 或无限等待。
  - 模块全局锁 ⇒ 不同实例互相阻塞。

---

## D-07 · SQLite 落盘：惰性父目录 / 库 / 表；`0o600`；失败四路诊断

- **Decision**：
  - 构造零副作用；
  - 首次写行：`path.parent.mkdir(parents=True, exist_ok=True)` → 若库文件不存在，
    用 `os.open(path, O_WRONLY | O_CREAT | O_EXCL, 0o600)` 预创建 → `sqlite3.connect` →
    `CREATE TABLE IF NOT EXISTS` + 索引 → `INSERT` → `commit` → `close`；
  - 已存在库文件：不主动放宽权限；实现 MAY 尝试收紧到 `0o600`，失败不阻断；
  - 写入失败（父目录不可写 / 库损坏 / 旧表不兼容 / 磁盘满 / 序列化失败）⇒
    `write_errors += 1`、`last_error = f"{type(exc).__name__}: {exc}"`、可选 `on_error`
    （锁外）、`logging.WARNING`；**不重试**；`BaseException` 不吞；
  - 查询只读：库不存在 ⇒ `[]`；不建库 / 不建表 / 不迁移。
- **Rationale**：spec FR-017 / FR-019 / SC-018；与 B20F1 权限与诊断口径一致；
  预创建 `0o600` 避免 SQLite 默认权限受 umask 影响过宽。
- **Alternatives considered**：
  - 让 SQLite 自己建文件 ⇒ 权限由 umask 决定，可能过宽。
  - 对已存在文件 `chmod 0o600` ⇒ 可能改变用户已有设置；spec 只要求不放宽。
  - 构造时建库 / 建表 ⇒ 只构造就有副作用，违反「查询 / 构造零副作用」。

---

## D-08 · 结果行：严格 B20F1 视图 + 字段校验 + 额外字段丢弃

- **Decision**：
  - `kind="span"` 必需字段（12 个含 `kind`）：
    `kind` / `id` / `name` / `attributes` / `parent` / `start_time` / `end_time` /
    `context` / `thread_id` / `run_id` / `node` / `checkpoint_id`；
  - `kind="trace_record"` 必需字段（14 个含 `kind`）：
    `kind` / `span_id` / `task_id` / `run_id` / `thread_id` / `checkpoint_id` /
    `node` / `superstep` / `triggers` / `concurrency_group` / `barrier_groups` /
    `input_state` / `output_state` / `error`；
  - 类型校验：字符串字段为 `str` / 可空字段为 `str | None`；`attributes` / `context`
    为 `dict`；`superstep` 为 `int`（**排除 `bool`**）；`triggers` /
    `concurrency_group` / `barrier_groups` 为 `list`；`error` 为 `dict | None`
    （`type` / `message` 为 `str`）；`input_state` / `output_state` 为 JSON 值；
  - 额外未知字段 **MUST NOT** 返回（丢弃）；
  - 未知 `kind` / 缺字段 / 类型不符 ⇒ 跳过 + WARNING；
  - 返回的每个 dict 都是新对象（来自 `json.loads` / 行构造），调用方修改不影响存储。
- **Rationale**：spec §4 / §8；结果契约稳定，CI 断言可直接用；防止未来扩展字段
  泄漏给旧消费者。`bool` 是 `int` 子类，故 `superstep` 用 `type(x) is int` 排除。
- **Alternatives considered**：
  - 原样返回额外字段 ⇒ 结果结构随存储漂移。
  - 宽松类型（如 `superstep=True`）⇒ 排序 / 断言出现意外。
  - 返回残缺元素 ⇒ 违反 11/13 字段契约。

---

## D-09 · 时间：纳秒精度 + 闭区间 + 有效起始时刻

- **Decision**：
  - `parse_instant_ns(text)`：
    1. 去掉首尾空白；`Z` / `z` 后缀归一为 `+00:00`；
    2. 按 `YYYY-MM-DDTHH:MM:SS[.fraction][offset]` 解析；
    3. 小数部分**右侧补 0 / 左侧截到 9 位**，单独作为纳秒；
    4. base 时间用 `datetime.fromisoformat(base + offset)` 得到秒级 / 微秒级；
       **不使用**其 `microsecond` 作为最终小数（避免 9 位被截到 6 位）；
    5. 返回 `int(epoch_seconds) * 1_000_000_000 + nanos`；
    6. 无 offset ⇒ 按 UTC；非法 ⇒ `ValueError`。
  - 过滤：闭区间 `[start, end]`；只给一边则另一边无界；两边都 `None` 不过滤；
  - 有效起始时刻：span 用 `start_time`；record 用**同一 `run_id`** 关联 span 的 `start_time`；
    找不到 ⇒ 无时刻；有任何时间界 ⇒ 无时刻 record 不匹配；
  - `start > end` ⇒ `[]`（不抛错、不交换）。
- **Rationale**：B20F1 的规范时间戳是 9 位小数；`datetime.fromisoformat` 在 3.11 会
  截断到微秒，直接比较会丢精度。闭区间 / 倒置语义由 spec 锁定。
- **Alternatives considered**：
  - 直接用 `datetime` 比较 ⇒ 微秒截断，纳秒级边界误判。
  - 简单字符串比较 ⇒ 对 `Z` / 偏移 / 不同小数位不安全；对规范格式可用但需先归一。
  - 区间相交（span 与窗口有重叠）⇒ spec 明确不用 `end_time`，且 record 无 end_time。

---

## D-10 · 排序：有效起始时刻 + 稳定平局键

- **Decision**：
  - 先分两组：有有效起始时刻 / 无时刻；
  - 有时刻组排序键：`(start_ns, run_id, kind_rank, stable_id)`；
    `kind_rank`：`trace_record=0`、`span=1`；`stable_id`：record 用 `span_id`、span 用 `id`；
  - 无时刻组排序键：`(run_id, superstep, task_id, span_id)`；
  - 两组拼接：有时刻在前；
  - 完全相同的重复行相对顺序 MAY 任意；不影响其它条目。
- **Rationale**：spec §5 写死；两后端共享；`record` 在 `span` 前与 B20F1 写入顺序一致。
- **Alternatives considered**：
  - 按文件行序 / SQLite `seq` ⇒ 两后端不等价；并发写入顺序不稳定。
  - 只按 `start_time` 字符串 ⇒ record 无 start_time，需额外规则。
  - 按 `node` / `task_id` 排 ⇒ 不是时间线；不满足「时间升序」。

---

## D-11 · 容错与只读：尽量容错 + 告警

- **Decision**：
  - JSONL 坏行 / 未知 kind / 字段残缺 / 额外字段 / 非白名单文件名 / 符号链接 ⇒
    跳过 + `logging.WARNING`；
  - 单个 JSONL 文件不可读 ⇒ 跳过 + WARNING；全部候选不可读 ⇒ 抛错；
  - 目录路径是普通文件 / SQLite 文件损坏 / 非 SQLite ⇒ 抛底层异常给调用方；
  - SQLite 内部表不存在 ⇒ `[]`；旧表不兼容 ⇒ `[]` + WARNING（不修改）；
    单行 `payload` JSON 解码失败（含嵌套 `input_state` / `output_state` / `error`）
    ⇒ 跳过 + WARNING；
  - 查询 **MUST NOT** 创建 / 截断 / 删除 / 改写 / 迁移 / 修复任何存储；
  - 查询不在运行时自动执行；任何查询异常不进入图执行路径。
- **Rationale**：spec §8 + 用户 clarify A；trace 是诊断数据，尽量返回可用信息；
  静默漏数据不可接受，故用 WARNING；修改已有数据风险不可接受。
- **Alternatives considered**：
  - 严格抛错 ⇒ 一行损坏就完全无法诊断。
  - 全部吞掉返回 `[]` ⇒ 静默漏数据，CI 断言可能假绿。
  - 自动修复 / 迁移 ⇒ 修改用户数据，风险最高。

---

## D-12 · 请求校验：读取前统一 `TypeError` / `ValueError`

- **Decision**：
  - `query` 不是 `TraceQuery` / `None` ⇒ `TypeError`；
  - `TraceQuery` 5 字段任一不是 `str` / `None` ⇒ `TypeError`；
  - 合法字符串但时间不可解析 ⇒ `ValueError`；
  - 倒置时间窗 ⇒ `[]`（不抛错）；
  - 校验在读取任何数据之前完成。
- **Rationale**：spec §3 + 用户 clarify A；避免把写错的查询静默当成「无匹配」。
- **Alternatives considered**：
  - 非字符串自然不匹配 ⇒ 静默 `[]`，隐藏调用方错误。
  - 宽松转字符串 ⇒ 可能意外匹配真实数据。
  - 倒置抛错 ⇒ spec 明确返回 `[]`。

---

## D-13 · SQLite 写侧诊断：本地实现，不改 B20F1 写侧

- **Decision**：`SqliteTraceStore` 自带 `_write_errors` / `_last_error` /
  `_report(exc)`，语义与 `FileTraceStore` 完全一致（`last_error` 格式、
  `on_error` 锁外、重入防递归、WARNING、不重试、`BaseException` 不吞）；
  **不重构** `FileTraceStore._report`。
- **Rationale**：B20F1 写侧行为是冻结面；抽取共享 diagnostics 会改其内部结构 /
  测试（如 `store._directory` 直接赋值），风险大于收益。两处逻辑小且由
  `test_b20f2_sqlite_write.py` 与既有 B20F1 测试分别守护。
- **Alternatives considered**：
  - 抽 `_diagnostics.py` 并让两个 store 共用 ⇒ 需改 B20F1 写侧，回归风险。
  - 让 `SqliteTraceStore` 继承 `FileTraceStore` ⇒ 继承写盘 / 文件语义，职责错误。
  - 复制整个 `FileTraceStore` ⇒ 文件逻辑与 SQLite 逻辑混杂。

---

## D-14 · 导出与分层：只新增 `SqliteTraceStore`

- **Decision**：
  - `observability.__all__` 只增 `SqliteTraceStore`；`FileTraceStore.query` 是既有类的新方法；
  - 不新增 L1 Protocol；不改 `freegraph.graph` / `runtime.__all__`；
  - `import freegraph` 不加载 L5；
  - 新模块只 import 标准库 + L1 `Span` / `TraceQuery` + 同层；
  - `sqlite3` 只出现在 `_sqlite_store.py`；`_file_store.py` 仍不 import `sqlite3`。
- **Rationale**：spec FR-028 / FR-030；ARCH-1 / ARCH-2 / ARCH-3；B20F1 门禁
  `test_b20f1_gates.py` 的 `FORBIDDEN_ROOTS` 已含 `sqlite3`，必须保持 `_file_store.py` 干净。
- **Alternatives considered**：
  - 把 `SqliteTraceStore` 放 L2 / 门面 ⇒ 破分层 / 惰性。
  - 新增 L1 `TraceStore` Protocol ⇒ 契约冻结面变更。
  - 把 sqlite3 逻辑放 `_file_store.py` ⇒ 污染 JSONL 后端 / 破 B20F1 门禁。

---

## D-15 · 测试 / 验收 / 差分 / 文档落点

- **Decision**：
  - 单元 / 集成：`tests/observability/test_b20f2_*.py`（查询 API / 校验 / 容错 /
    只读 / SQLite 写侧 / 生命周期 / 并发 / 后端等价）；
  - 契约 / 门禁：`tests/contracts/test_b20f2_contracts.py` / `test_b20f2_gates.py`；
  - 冻结面更新：`test_api_snapshot.py` / `test_b19f1_lazy.py` / `test_b19f1_gates.py` /
    `test_b20f1_contracts.py` / `test_architecture.py`（只增 / 拆分）；
  - 差分：`tests/differential/test_b20f2_trace_query_parity.py`（D-501…D-508；
    上游缺席即 skip）；
  - 一键验收：`harness/verification/B20F2/acceptance.py`（A1–A6）；
  - 守卫：`tests/runtime/test_acceptance_script.py` 追加 B20F2；
    `tests/runtime/test_b20f2_manual_record_guard.py`（SC-015）；
  - 文档：`harness/demo/README.md` / `harness/verification/README.md`；
  - 人工：`harness/verification/B20F2/manual-verification.md`。
- **Rationale**：原则 VI 判据级覆盖；原则 V 人工门禁；证据门禁要求实测输出；
  差分 D-501…D-508 与 spec §3 对齐。
- **Alternatives considered**：
  - 只写单元测试 ⇒ 不覆盖真实图 / 并发 / 两后端等价 / 文档门禁。
  - 不写差分 ⇒ 违反原则 XI。
  - 不改 README ⇒ 违反 spec FR-034。

---

## 已决实现细节（供 tasks / implement 直接照做）

- `normalize_query`：`None` → `TraceQuery()`；对 5 字段逐一 `isinstance(value, str)` 或
  `value is None`；`bool` 不是 `str`，自然被拒。
- `parse_instant_ns`：正则建议
  `^(?P<date>\d{4}-\d{2}-\d{2})[T ](?P<time>\d{2}:\d{2}:\d{2})(?:\.(?P<frac>\d+))?(?P<tz>Z|[+-]\d{2}:?\d{2})?$`；
  `frac` 右补 0 到 9 位；`tz` 缺省 `+00:00`；`datetime.fromisoformat` 只用于
  `date + time + tz`（无小数）→ epoch 秒；最终 `seconds*10**9 + int(frac9)`。
- `normalize_row`：先看 `kind`；未知 ⇒ `None`。按 `kind` 的必需字段集合检查
  `set(row) >= required`；缺失 ⇒ `None`；类型不符 ⇒ `None`；返回
  `{key: row[key] for key in allowed}`（丢弃额外字段）。
- `finalize`：
  1. 对每个合法 span 建 `index[(run_id, id)] = parse_instant_ns(start_time)`；
  2. 对每个合法 record 查 `index.get((run_id, span_id))`；
  3. `run_id` / `thread_id` / `node` 精确匹配；时间界按有效起始时刻；
  4. 排序键见 D-10；
  5. 返回新 list（元素本身已是新的 dict）。
- JSONL 文件名正则：`^trace-([A-Za-z0-9][A-Za-z0-9_-]*)\.jsonl$`；
  `run_id` 过滤值先用同一 allowlist 校验；不安全 ⇒ `[]`。
- SQLite schema 版本：v1 **不做** `user_version` / 迁移；表列校验用
  `PRAGMA table_info(trace_entries)` 的列名集合；缺表 ⇒ `[]`；列不匹配 ⇒ `[]` + WARNING。
- SQLite `database`：按普通文件路径处理；**不支持** `:memory:` / URI
  （`:memory:` / URI 在构造时**显式拒绝** ⇒ `ValueError`，避免「以为持久化」）。
- SQLite 查询连接：`sqlite3.connect(str(path), timeout=5.0)`；`PRAGMA busy_timeout=5000`；
  `PRAGMA query_only=ON`；`finally: close()`。
- SQLite 写入连接：同一 `timeout`；`isolation_level` 默认；`commit()` 成功即成功；
  不额外 `fsync`；不重试。
- `on_error` 重入：与 B20F1 一样用 `threading.local` 标记 `in_on_error`；重入不再回调。
- 日志：`logging.getLogger(__name__).warning("trace query skipped ...", exc_info=...)` /
  `"trace write failed: %s"`；不打印敏感状态。
- 差分 D-501…D-508 的落点：`tests/differential/test_b20f2_trace_query_parity.py`；
  上游缺席时 `pytest.importorskip` / 既有 skip 纪律。
