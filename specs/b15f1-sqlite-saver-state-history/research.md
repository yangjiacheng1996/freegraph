# Research · B15F1 · `SqliteSaver` + `get_state` / `get_state_history`

> **输入**：`spec.md`（**唯一权威** · 6 条 clarify 拍板（2026-11-22 ×3 + 2026-11-23 ×3） + 13 条形态锁定裁定 + FR-001…FR-037 +
> SC-001…SC-027 + P-01…P-25 + D-01…D-21 + X-01…X-08）· 宪法 **v1.16.1** ·
> 上游 `langgraph` **1.2.11**（`.venv` 已装）·
> `langgraph-checkpoint-sqlite` **3.1.1**（MIT · uv 缓存 · 未安装进 `.venv`）。
>
> **判定纪律**（宪法原则 XI）：每条决策先问「上游怎么说」⇒ 上游有答案 ⇒ **照抄**；
> 只在**必须自研区**自研并**如实登记**。上游 SQLite 的**连接 / 并发 / WAL / 构造入口 / 建表**
> 已照抄；**序列化**因零第三方改为标准库 JSON（X-05）；`put` / id / `CheckpointTuple` /
> `task_path` 排序因 **B14F1 已冻结**而保留 freegraph 口径。
>
> **形态纪律**（原则 XII）：复用 `StateSnapshot` / `CheckpointTuple` / `PregelTask`；
> 不另造第二套快照 / id / 读侧载体。

---

## §1 现状盘点（动手前的事实基线）

| # | 事实 | 取证 | 影响 |
|---|---|---|---|
| **F-01** | L1 `Checkpointer` 是 **8 方法**的结构化协议 | `src/freegraph/contracts/protocols.py:90-140` | `SqliteSaver` 结构化满足；L1 零改动 |
| **F-02** | L1 `StateSnapshot` 是 **8 字段**冻结 dataclass | `src/freegraph/contracts/types.py:291-340` | 读侧直接复用，零新增快照类型 |
| **F-03** | `PregelTask` / `Interrupt` 字段面已冻结 | `src/freegraph/contracts/types.py:129-180` | `tasks` / `interrupts` 重建只用既有字段 |
| **F-04** | `RunConfig.resolved_thread_id()` 支持顶层 / `configurable["thread_id"]` | `src/freegraph/contracts/types.py:245-256` | 统一取生效 thread id |
| **F-05** | L4 已有 `MemorySaver` / `CheckpointTuple` | `src/freegraph/persistence/memory.py:120-361` · `_types.py` | SQLite 复用同一读侧契约与 id 空间 |
| **F-06** | `CompiledGraph.get_state` / `get_state_history` 仍抛 `NotImplementedError` | `src/freegraph/_stategraph.py:866-872` | 本 feature 替换为真实实现 |
| **F-07** | `stream` 主循环在 L3 `_stream_events`；每轮调 L2 `_stream_tick` | `src/freegraph/_stategraph.py:747-864` · `runtime/superstep.py:1755` | `checkpoints` 事件需在 L3 接线 + L2 写盘助手 |
| **F-08** | B14F1 的写盘逻辑在 `_run_graph_loop` / `_write_suspend` / `put_initial` / `put_step` | `runtime/superstep.py:2083-2407` · `runtime/_checkpoint.py` | 流式写盘复用这些助手，不另写一套 |
| **F-09** | pending writes 的元素是 `(task_id, channel, value)`；`.pending_writes` 按 `(task_path, task_id, idx)` 排序 | `persistence/memory.py:139-157` · B14F1 契约 | `get_state` 的合并 / 重建沿用该顺序 |
| **F-10** | L2 有 `_restore_channels` / `_apply_input_writes` / `_reject_unknown_keys` / `_sparse_state` | `runtime/superstep.py:1956-2025` · `:796` · `:1684` | 新增只读合并助手可复用通道逻辑 |
| **F-11** | `StreamSession` 当前忽略 checkpointer；不暴露 run table | `runtime/_stream.py:1-160` | 需增可选 saver / writer / table 暴露 |
| **F-12** | 门面禁止转出 L4（G18）；层注册表固定 L4 = `persistence` | `tests/facade/_gatesupport.py` · `layer-registry.md` §1 | `SqliteSaver` 只从 `freegraph.persistence` 导入 |
| **F-13** | 基线 **2191 passed / 8 skipped**（2026-11-22 实跑） | `.venv/bin/python -m pytest -q --tb=no` | 实施后必须回到全绿（除 skip） |
| **F-14** | 上游 SQLite 同步 saver 源码 645 行 | `/home/ctyun/.cache/uv/archive-v0/UtTk-BJ9thKpSH0Q/langgraph/checkpoint/sqlite/__init__.py` | 连接 / 锁 / WAL / setup / filter 可照抄 |
| **F-15** | 上游 SQLite 依赖 `aiosqlite` / `sqlite-vec` / `langchain_core` / `JsonPlusSerializer` | `langgraph_checkpoint_sqlite-3.1.1.dist-info/METADATA` · `__init__.py:1-40` | **不照抄依赖**；只移植同步 `sqlite3` 路径 |

---

## §2 设计决策（D-01…D-20）

### D-01 · L4 包结构与公开面

- **Decision**：新增 `src/freegraph/persistence/sqlite.py` 与 `_json.py`；
  `__init__.py` 的 `__all__` **只增** `SqliteSaver`。只 import `freegraph.contracts`（L1）+ 标准库。
- **Rationale**：层注册表固定 L4 = `persistence`；门面 G18 禁止转出 L4；上游 SQLite 是
  独立子包（`langgraph.checkpoint.sqlite`）⇒ 同构。`SqliteSaver` 与 `MemorySaver` 共享
  `CheckpointTuple`，不新增读侧载体。
- **Alternatives considered**：
  - 放 `freegraph.graph` ⇒ G18 判红。
  - 新增 `freegraph.checkpoint` 层 ⇒ 层注册表未登记，新增条目 = 改冻结面。
  - 把 `SqliteSaver` 塞进 `memory.py` ⇒ 职责混杂、层内文件过大。
  - 新增 `SqliteCheckpointTuple` ⇒ 违反 B14F1「三字段载体唯一」；排除。

### D-02 · 上游移植范围

- **Decision**：照抄 `langgraph-checkpoint-sqlite 3.1.1` 的**同步** `SqliteSaver` 的：
  `__init__` 持有 `conn` / `threading.Lock` / `is_setup`；`from_conn_string`（`closing` +
  `check_same_thread=False`）；`setup()`（WAL + 两表）；`cursor()`（锁 + 事务）；
  `get_tuple` / `list` / `put_writes` / `delete_thread` 的 SQL 形状；`filter` 的 key 校验与
  `json_extract`。**不**照抄 `aiosqlite` / `sqlite-vec` / `JsonPlusSerializer` / `BaseCheckpointSaver` /
  `RunnableConfig`。
- **Rationale**：宪法 XI（上游有同款 ⇒ 照抄）；零第三方 + 只依赖 L1 ⇒ 只移植同步、标准库路径。
  B14F1 的 `put` / id / `CheckpointTuple` 是**跨 feature 冻结契约**，优先于上游形态。
  ⚠️ **归属**：改编上游 MIT 代码 ⇒ `THIRD_PARTY_NOTICES` §1 必须登记（R-11）；
  源文件带**本项目**署名头，同时保留上游 MIT 版权声明。
- **Alternatives considered**：
  - 从零自研连接 / 锁 / WAL ⇒ 重复上游已验证的实现，增加返工。
  - 照抄 `from_conn_string(":memory:")` 之外的 URI / 连接对象注入 ⇒ v1 不需要。
  - 照抄 serde / msgpack ⇒ 破零依赖红线。
  - 照抄上游 `put` 四参数 ⇒ 破 B14F1 冻结写侧关键字。

### D-03 · 公开入口与生命周期

- **Decision**：
  ```python
  SqliteSaver(conn: sqlite3.Connection, *, on_checkpoint=None)
  SqliteSaver.from_conn_string(conn_string: str, *, on_checkpoint=None)  # @contextmanager
  ```
  `from_conn_string` 打开 / 关闭连接；`SqliteSaver(conn)` 不关闭调用方连接；不提供 `close()` /
  `serde`；支持 `:memory:`。
- **Rationale**：与上游同款入口；`on_checkpoint` 是 B14F1 的数据源扩展；上下文管理器让
  Windows / 测试临时文件可及时释放。
- **Alternatives considered**：
  - `SqliteSaver(database)` 单参数（早期 spec 草案）⇒ clarify 轮改为全面对齐上游，已撤销。
  - 长期连接 + 无 `from_conn_string` ⇒ 上游不兼容且文件句柄难管理。
  - 提供 `close()` ⇒ 与上游入口不一致；上下文管理器已覆盖主要场景。

### D-04 · 内部 schema 与线程顺序

- **Decision**：内部两表（表名 / 列名不对外）：
  - `checkpoints(thread_id, checkpoint_ns DEFAULT '', checkpoint_id, parent_checkpoint_id,
    created_at, values, metadata, PRIMARY KEY(thread_id, checkpoint_ns, checkpoint_id))`
  - `writes(thread_id, checkpoint_ns DEFAULT '', checkpoint_id, task_id, task_path, idx,
    channel, value, PRIMARY KEY(thread_id, checkpoint_ns, checkpoint_id, task_id, idx))`
  `checkpoint_ns` v1 恒 `""`；`list(None)` 的线程顺序按该线程**首次写入**（`MIN(rowid)`）。
- **Rationale**：镜像上游 `checkpoints` / `writes`；`values` / `metadata` 分列便于 `filter`
  用 `json_extract(CAST(metadata AS TEXT), ...)`；额外 `task_path` / `created_at` 列用于
  B14F1 的排序与 8 字段快照；`MIN(rowid)` 零额外表即可复现 B14F1 的插入序。
- **Alternatives considered**：
  - 单张 JSON 大表 ⇒ `filter` 无法走 SQL；`list` 分页 / 排序更难。
  - 不存 `task_path` ⇒ 无法复现 B14F1 的 `.pending_writes` 排序。
  - 不加 `threads` 表 ⇒ 用 `MIN(rowid)` 已够；避免多一份状态。
  - 用上游 `uuid6` / 调用方 id ⇒ 破 B14F1 的 32 位单调 id 空间。

### D-05 · JSON 序列化

- **Decision**：`_json.py` 提供：
  - `encode_values(values) -> str` / `decode_values(text) -> dict`；
  - `encode_metadata(metadata) -> str` / `decode_metadata(text) -> dict`；
  - `encode_writes` / `decode_writes`；
  - `encode_task` / `decode_task`、`encode_interrupt` / `decode_interrupt`。
  `values` / 任意 metadata 走标准库 JSON；`next` / `tasks` / `interrupts` / `path` 读回重建
  tuple / 对象；**pending `__interrupt__` 的值 channel-aware 投影为 `{"value","id"}` 并读回
  `Interrupt`（MUST NOT 直接 `json.dumps((Interrupt,))`）**；非 JSON ⇒ `TypeError`，该次调用零写入。
- **Rationale**：零依赖；C19「纯数据」；冻结字段必须保持 L1 类型；X-05 已登记
  「用户 `values` 中 tuple 往返变 list」。
- **Alternatives considered**：
  - `pickle` ⇒ 安全风险 + C19 纯数据不符。
  - msgpack / 上游 `JsonPlusSerializer` ⇒ 第三方依赖。
  - 自定义 tuple 标记 ⇒ 与用户数据冲突风险；v1 不做。
  - 只存 `repr` ⇒ 不可逆。

### D-06 · checkpoint 顺位 id / 父链

- **Decision**：完全复用 B14F1：每线程 `f"{n:032d}"` 单调；`put` 在写事务内取
  `MAX(checkpoint_id)` + 1；`parent_checkpoint_id` = 写入前的最新 id；`delete_thread` 后
  重建从 `1` 开始。
- **Rationale**：B14F1 已冻结；字符串序 == 数值序；`before` / `list` 可直接 SQL 比较；
  跨重启由 `MAX` 恢复，不依赖进程内计数器。
- **Alternatives considered**：
  - 上游 `uuid6` / 调用方 `checkpoint["id"]` ⇒ B14F1 冻结面不允许。
  - 进程内计数器 ⇒ 重启后从 1 开始会冲突。
  - `time.time_ns()` ⇒ 时钟回拨 / 同纳秒冲突。

### D-07 · 写侧语义

- **Decision**：
  - `put(config, *, values, metadata)`：`values` / `metadata` 必须是 `Mapping`；JSON 编码；
    写事务；返回 `RunConfig(thread_id=..., configurable={"checkpoint_id": new_id})`；
    快照 8 字段按 B14F1 组装；`created_at` UTC ISO-8601。
  - `put_writes(config, *, writes, task_id, task_path="")`：目标由
    `configurable["checkpoint_id"]` 指定（缺 key ⇒ `KeyError`；不存在 ⇒ `ValueError`）；
    去重键 `(task_id, WRITES_IDX_MAP.get(channel, idx))`；普通通道 `INSERT OR IGNORE`、
    保留通道 `INSERT OR REPLACE`（**逐写**判定，逐字 B14F1；不照抄上游 `all(...)` 的整批判定）。
- **Rationale**：B14F1 的写侧关键字 / 去重 / 排序已冻结；`sqlite3` 的 `INSERT OR IGNORE` /
  `REPLACE` 能直接表达「首次 / 最后」语义；JSON 编码失败时事务回滚。
- **Alternatives considered**：
  - 照抄上游 `all(w[0] in WRITES_IDX_MAP ...)` ⇒ 混合写入时语义与 B14F1 不一致。
  - 在 Python 里先读后写 ⇒ 多一次查询 + 竞态窗口；用 SQL 唯一键更稳。
  - 把 `task_path` 丢掉 ⇒ 破 B14F1 排序。

### D-08 · 读侧与 list

- **Decision**：
  - `get_tuple(config) -> CheckpointTuple | None`；按 `configurable["checkpoint_id"]` 或最新；
    读 `writes` 按 `(task_path, task_id, idx)` 升序；`.scheduler` = metadata 的 `scheduler` 副本。
  - `list(config=None, *, filter=None, before=None, limit=None) -> Iterator[CheckpointTuple]`：
    `config=None` 线程按首次写入；同线程 id 降序；`filter` 用上游 key 校验 + `json_extract`；
    `before` 用 `checkpoint_id < ?`；`limit <= 0` ⇒ 空；全局 limit（跨线程累计）。
- **Rationale**：B14F1 冻结 `CheckpointTuple` 三字段与 `.pending_writes` 排序；上游的
  `filter` / `before` / `limit` 形状可照抄；`list(None)` 保留 B14F1 插入序。
- **Alternatives considered**：
  - 把所有线程一次 `ORDER BY checkpoint_id DESC` ⇒ 与 B14F1 `list(None)` 语义不同。
  - 用 `json_extract` 的 dotted key 同时改 `MemorySaver` ⇒ 破 B14F1 冻结面；不改。
  - `limit` 负值按 SQLite 无限 ⇒ 与 B14F1 `limit <= 0` 空冲突；保留 B14F1。

### D-09 · pending writes 的只读合并

- **Decision**：新增 L2 私有 `merge_pending_writes(spec, values, pending_writes) -> dict`：
  1. `SchedulerState()` + `_restore_channels(spec, state, values)`；
  2. 按 `.pending_writes` 顺序收集**非保留通道**的写入（`(task_path, task_id, idx)` 已排序）；
  3. `_reject_unknown_keys`（未知 key ⇒ `InvalidUpdateError`，与运行期同款）；
  4. 每通道 `Channel.update(values)`；
  5. `_sparse_state(spec, state)` 返回新 dict。
  **不**推进 `channel_versions` / `node_versions`，**不**写回存储。
- **Rationale**：`get_state` 无 `checkpoint_id` 时与上游一样合并 pending writes；L3 可依赖 L2，
  L4 仍只依赖 L1（ARCH-1 不破）；复用通道归约，不另写一套。
- **Alternatives considered**：
  - 在 L4 合并 ⇒ L4 只能依赖 L1，拿不到 `GraphSpec` / 归约器。
  - 在 L3 重写归约 ⇒ 与运行期漂移；MUST 复用 `Channel.update`。
  - 直接修改快照 `values` ⇒ 污染存储；只操作副本。

### D-10 · `tasks` / `interrupts` 重建

- **Decision**：**L2** 私有 `runtime/_state_read`（与 `superstep.py` / `_recursion.py` 同条目；由 L3 `_stategraph` 调用）：
  - `tasks`：**上游 next-tasks**——枚举 `snapshot.next` 与 `.scheduler["fanout"]`（fan-out 账本）；
    **两类来源 id 域不同、互斥**：`next` 来源（含 `节点名:TaskId` 挂起现场）的 `id` = 运行时
    `task_key`（全局 records 下标 · 权威），账本来源（已调度未执行）的 `id` = 本地 `index`
    （每 producer 0 起 · 非 `task_key`）；**MUST NOT** 跨源按 `id` 去重 / 相等合并（运行时
    `_determine_triggers` 不把 pending fan-out 写入 `next`）；`next`/pending 来源的 interrupts 按
    运行时 `task_key` 从 `pending __interrupt__` 附着，账本来源 `interrupts` 恒 `()`；
    标准任务 `id=name=节点名`、`path=(节点名,)`；fan-out `next` 来源 `path=(node, 全局TaskId)`、
    账本来源 `path=(node, 本地index)`；`error/state/result=None`；**不使用** `snapshot.tasks`。
  - `interrupts`：按任务顺序展平；无任务中断回退 `snapshot.interrupts`。
  - `get_state` / `get_state_history` / `stream(checkpoints)` payload 同款；历史同 id 与
    `get_state(id)` 逐字段相等。
- **Rationale**：2026-11-23 决策：上游 `prepare_next_tasks` 的 next-tasks 语义更优（HITL /
  time-travel / `next` 一致），原则 XII 最优设计 + 原则 XI 上游优先 ⇒ 读取层重建；
  B10F1 F-3 把节点名交给 `tasks`；B14F1 的存储「本轮完成态」降级为历史 / 流数据源；
  pending 是最新留痕（真异常 + 中断同现只写 pending），读取时附着即可。
- **Alternatives considered**：
  - 只复制 `snapshot.tasks` ⇒ 与上游「下一轮待执行」语义冲突，收敛快照会残留完成态任务。
  - 只从 pending `__interrupt__` 重建 ⇒ 普通 `next` 任务看不到，且收敛 / 静态挂起语义错。
  - 给 `Interrupt` 加 `name` ⇒ 破 L1 字段面 / 上游同款。
  - 从 `next` 单推 fan-out 任务 ⇒ fan-out 轮 `snapshot.next` 可能为空（B11F1 冻结），必须读 `.scheduler["fanout"]`。

### D-11 · config / 失败信号

- **Decision**：`get_state` / `get_state_history` 的 `config` 接受 `RunConfig | Mapping | None`；
  `resolve_config` 归一；裸 `str` / 数字 ⇒ `TypeError`；缺 / 空 `thread_id` ⇒ `ValueError`；
  `configurable["checkpoint_ns"]` 非空 ⇒ `ValueError`；无可用 saver ⇒ `ValueError`（含
  `No checkpointer set`）。
- **Rationale**：与上游调用形态同款；B7F3 的 CF-05 双形态边界；v1 无子图 ⇒ 非空 ns 明确失败。
- **Alternatives considered**：
  - 接受裸 `thread_id` ⇒ 与上游 / L1 协议不一致。
  - 非空 ns 静默忽略 ⇒ 可能读错 checkpoint；明确失败更安全。
  - 无 saver 返回 `None` ⇒ 与上游 / 现有恢复失败信号不一致。

### D-12 · L1 `config` 注解

- **Decision**：`contracts/protocols.py:288-290` 的 `get_state` / `get_state_history`
  `config` 注解改为 `RunConfig | Mapping[str, Any] | None`；返回类别不变；走「登记 + 回溯修订 +
  发起者追认」。
- **Rationale**：spec H-9 / FR-023 / SC-023；B7F3 的双形态边界；只改 2 处，不新增 L1 符号。
- **Alternatives considered**：
  - 保持 `RunConfig` 只在实现体放宽 ⇒ 协议 / 实现不一致，静态检查漏报。
  - 新增 L1 `StateReader` 协议 ⇒ 改 L1 符号面，超出 D-5。
  - 改 `update_state` 注解 ⇒ 属 B16F1，越界。

### D-13 · `checkpoints` 流式档

- **Decision**：仅当 `"checkpoints" in stream_mode` 且 saver 有效 + `thread_id` 非空时：
  - 用 `StreamCheckpointWriter` 在**本次运行**写初始（仅 thread 无历史时）/ 每轮 / 挂起 / 错误轮；
  - 每次成功 `put` 后通过 `get_tuple(written)` + **next-tasks 组装**读回快照
    （`values` 取存储快照；`tasks` / `interrupts` 与 `get_state()` 一致）；
  - L3 产出 `{"stream_mode":"checkpoints","payload":<StateSnapshot>,"run_id","thread_id"}`；
  - 无 saver / 无 `thread_id` / 无 `checkpoints` mode ⇒ 0 条；不恢复历史、不改其它 mode。
- **Rationale**：B14F1 D-02 只要求消费数据源；B8F2 七档语义不变；读回 `get_tuple` 不依赖用户
  是否传 `on_checkpoint`；`put` 的返回 config 提供 id，读回即同源快照。
- **Alternatives considered**：
  - 所有 stream mode 都写 saver ⇒ 改变 B8F2 v1 的其它 mode 行为 / 测试。
  - 依赖用户 `on_checkpoint` ⇒ 用户未传则无事件。
  - 从 `list()` 伪造事件 ⇒ 违反「不伪造历史」。
  - 恢复历史 / 支持 `Command` ⇒ 超出 B8F2 v1 边界，属后续 feature。

### D-14 · 并发 / Windows

- **Decision**：单连接 + 每实例 `threading.Lock` + `check_same_thread=False` + WAL；
  `from_conn_string` 设置 `check_same_thread=False`；`SqliteSaver(conn)` 由调用方负责；
  同实例多线程串行；跨实例 / 跨进程只依赖 SQLite 文件锁；不额外重试。
- **Rationale**：照抄上游并发模型；低并发定位；Windows 文件锁差异由现有 CI 真跑；
  spec 不承诺跨进程严格串行。
- **Alternatives considered**：
  - 短连接 / 每操作连接 ⇒ 与上游不一致，且跨实例 `:memory:` 不可用。
  - 有界重试 ⇒ 上游没有；本 feature **不采用**（原 X-06 已撤销）。
  - WAL 关闭 ⇒ 读写并发差；上游已用 WAL。

### D-15 · 失败 / 原子性

- **Decision**：`cursor()` 用 `try / except: rollback / else: commit`；`sqlite3.Error` 子类
  原样传播；`put` / `put_writes` 单次失败零残留；不删除 / 重建 / 迁移用户库；
  `from_conn_string` 退出后调用 ⇒ `sqlite3.ProgrammingError`。
- **Rationale**：spec FR-012；比上游「finally commit」更明确地保证失败不半写；
  不包装异常 ⇒ 调用方可见底层失败。
- **Alternatives considered**：
  - 照抄上游 `finally: commit()` ⇒ 异常时可能提交半事务，违反 spec。
  - 包装成 `PersistenceError` ⇒ 新增异常类型，spec 不做。
  - 失败自动重建库 ⇒ 删用户数据，红线。

### D-16 · 文件权限 / 生命周期

- **Decision**：文件权限跟随 OS 默认 / umask；不额外 `chmod 0o600`；`from_conn_string` 关闭连接；
  `SqliteSaver(conn)` 不关闭调用方连接；不提供额外 `close()`。
- **Rationale**：spec 选择上游口径；`SqliteSaver(conn)` 的所有权归调用方；上下文管理器覆盖
  主要生命周期。
- **Alternatives considered**：
  - 0o600 ⇒ 早期草案；clarify 轮改为上游默认。
  - 提供 `close()` ⇒ 与上游入口不一致。
  - 每次操作短连接 ⇒ 与上游不一致。

### D-17 · filter / list(None)

- **Decision**：`filter` 采用上游 `_metadata_predicate`：key 匹配 `^[a-zA-Z0-9_.-]+$`
  （否则 `ValueError`），值经 `json_extract`；`None` / `bool` / `dict` / `list` 编码同上游；
  `before` 用 `checkpoint_id < ?`；`limit <= 0` ⇒ 空；`list(None)` 线程按首次写入。
- **Rationale**：上游 filter 是安全 / 兼容锚点；B14F1 的 `limit` / `list(None)` 冻结面保留。
- **Alternatives considered**：
  - 只支持顶层精确匹配 ⇒ 与上游 SQLite filter 不同；但 `MemorySaver` 保持 B14F1。
  - 支持负 `limit` = 无限 ⇒ 与 B14F1 冲突。
  - 跟随 `MemorySaver` 的 dotted key 行为 ⇒ 与上游 `json_extract` 不同；保留差异并登记。

### D-18 · 差分 / 基线

- **Decision**：新增 `tests/differential/test_b15f1_state_parity.py`（D-01…D-21）；
  `get_state` / 历史对照用已安装 `MemorySaver`；上游 SQLite 不可导入 ⇒ `SKIP (source-aligned)`；
  **SQLite 专属场景必须单独 `pytest.importorskip("langgraph.checkpoint.sqlite")`**（仅
  `importorskip("langgraph")` 不够，实测该子包未安装）；基线 **2191 passed / 8 skipped**。
- **Rationale**：上游 SQLite 包未安装；源码对齐项无法运行时对跑；state 读取可用 `MemorySaver`。
- **Alternatives considered**：
  - 把 uv 缓存路径加进 `sys.path` 强行导入 ⇒ 依赖其 `aiosqlite` / `sqlite-vec`，脆弱。
  - 把上游 SQLite 加进 dev 依赖 ⇒ 与「未安装」现状不符；不必要。
  - 只写 freegraph 单测、不做差分 ⇒ 违反原则 XI 的可验证出口。

### D-19 · 人工 / 文档

- **Decision**：新增 `harness/verification/B15F1/manual-verification.md`（五段式）；
  `README.md` 更新 `CompiledGraph` / `Checkpointer` 行；不新增兼容矩阵行（B24F1）。
- **Rationale**：原则 V / X；B24F1 是矩阵定稿方（spec D-04）；上游 SQLite 代码改编
  已在 `THIRD_PARTY_NOTICES` §1 登记（R-11）。
- **Alternatives considered**：
  - 在 B15F1 直接加矩阵行 ⇒ 越界，且 B24F1 还要再改。
  - 只靠 pytest ⇒ 违反人工门禁。

### D-20 · 红线 / 登记

- **Decision**：不新增门禁编号；R-1 / R-2 为已知必红；R-3 为 L1 注解追认；
  R-5 / R-6 为 stream 边界；R-9 行数实施期登记。
- **Rationale**：spec 的范围 / 红线。
- **Alternatives considered**：
  - 新增 G 编号 ⇒ 违反「零新增门禁」。
  - 放宽冻结测试 ⇒ 判据只可更严；拆分而不删。

---

## §3 上游证据索引

| 主题 | 上游锚点 |
|---|---|
| 同步 saver / 构造 / `from_conn_string` | `langgraph-checkpoint-sqlite 3.1.1` · `__init__.py:45-130` |
| 锁 / `check_same_thread=False` / WAL | 同上 `:95` / `:124` / `:141` |
| `setup()` / 两表 | 同上 `:132-166` |
| `cursor()` 事务 | 同上 `:168-189` |
| `get_tuple` / `list` | 同上 `:191-380` |
| `put` / `put_writes` | 同上 `:387-445` |
| `delete_thread` | 同上 `:484-495` |
| `get_next_version`（字符串） | 同上 `:626-644`（freegraph 用 B14F1 的 `int+1`） |
| filter key 校验 / `json_extract` | 同上 `utils.py:9-100` |
| `get_state` / 历史 / pending 合并 / tasks / interrupts | `langgraph 1.2.11` · `pregel/main.py:1145-1210` / `:1392-1435` / `:1480-1530` / `:1431` |
| `StateSnapshot` 8 字段 | `langgraph/types.py:684-701` |
| 保留通道名 | `langgraph/_internal/_constants.py:9,11,13,17` |
| 实测 E8 `HISTORY: 6` | `harness/reports/Q3-LangGraph的开源边界.md:43` |

---

## §4 结论

- **所有 NEEDS CLARIFICATION 已闭合**（spec 的 6 条 clarify + 13 条裁定）。
- **可照抄的已照抄**：连接 / 锁 / WAL / setup / schema 形状 / filter。
- **必须自研 / 冻结差异已登记**：JSON（X-05）、`put` / id / `CheckpointTuple` / `task_path`
  （B14F1 冻结）、`config` 双形态（X-03）、`checkpoints` 事件（X-04）、`context`（X-07）。
- **实现顺序**见 plan 的 P0–P9；**差分 / 人工 / 全量回归**为收口门。
