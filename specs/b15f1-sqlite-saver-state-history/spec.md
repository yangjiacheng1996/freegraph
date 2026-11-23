# Feature Specification: B15F1 · `SqliteSaver` + `get_state` / `get_state_history`

**Feature Branch**: `b15f1-sqlite-saver-state-history`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_specify` 钩子；既有 feature 同样在 `main` 上开发）

**Created**: 2026-11-22

**Status**: Draft

**Input**: User description: `harness/features/B15F1_SqliteSaver与状态历史.md` —— 交付**磁盘持久化**与**状态查询**：把 B14F1 的 `MemorySaver` 换成可落盘的 `SqliteSaver`（标准库 `sqlite3`，零第三方依赖），并实现对外的 `get_state()` 与 `get_state_history()`，让用户能「看当前状态」与「枚举历史快照」。判定：**历史快照可枚举**。

> **范围提醒**：本 feature 是 **L4 持久化层**的**磁盘后端** + **L1 `CompiledGraph` 的状态读取面**。
> 它**复用** B14F1 已冻结的读侧 / 写侧最小契约与 checkpoint 顺位 id 空间；**MUST NOT** 另立
> 第二套载体或 id 空间。**不实现** `update_state` / 时间旅行（B16F1）、`Store`（B17 已砍）、
> Postgres / async（v2）、trace 存储（B20F1 / B20F2）、子图（C26 · v2）。
> **MUST NOT** 改变图执行语义；**MUST** 保持运行时依赖闭包为空集。

---

## 承接条款（上游 feature → 本 feature）

> **宪法 v1.8.0「跨 feature 承接的接线通则」**：某 feature 的规格中出现**指名下一棒 feature**
> 的跨 feature 义务时，该条款 MUST 写入目标 feature 的 spec ⇒ 由本 spec 落成 **FR + 裁定**。
> **只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽任何门禁判据。**

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B10F1 → B15F1** | **M3** | **读侧 / 写侧最小契约与 B14F1 同款**：`get_tuple(config)` 暴露 `.snapshot` / `.pending_writes` / `.scheduler`；写侧关键字逐字 `values` / `metadata` / `writes` / `task_id` / `task_path`；保留通道 `__interrupt__` / `__resume__`；`put_writes` 目标由 `configurable["checkpoint_id"]` 指定（缺 key ⇒ `KeyError`）；挂起时 `metadata` 载荷原样存取。**MUST NOT** 另立一套。 | B10F1 **FR-018** · **裁定 9** · 下游承接 **D-1 / D-9** · `contracts/checkpoint-contract.md` §2…§6 | **FR-006 / FR-007 / FR-008 / FR-019** · **裁定 2 / 5 / 6** |
| **H-2** | **B12F1 → B15F1** | **M3** | **`StateSnapshot.interrupts` 的生产者口径**：`get_state()` MUST 把本轮待审批中断写入 `StateSnapshot.interrupts`（元素 = `Interrupt`）；顺序 = **标准任务按节点名序 · 含 fan-out 的轮按 TaskId 序**；与 `__interrupt__` 结果键**逐项一致**；MUST NOT 另造形态。 | B12F1 **FR-013** · **裁定 25 ④** · **SC-019** · 下游承接 **D-7** | **FR-018** · **裁定 8** · SC-008 |
| **H-3** | **B11F1 → B15F1** | **M3** | **task_id / 中断现场**：MUST 接受标准任务 `task_id` = 节点名、fan-out `task_id` = `f"{节点名}:{TaskId}"`；`.pending_writes` MUST 能区分同节点 N 个任务；MUST NOT 假设「一轮一个节点一个任务」。 | B11F1 下游承接 **D-8** · **F-13 / F-14** | **FR-020** · **裁定 8** · SC-010 |
| **H-4** | **B13F1 → B15F1** | **M3** | **静态挂起的历史表示**：`interrupts == ()` 且 `suspension_kind` / `static_ack` 为静态值（`next` 允许为空）；从历史静态快照恢复 MUST NOT 要求动态中断载荷；MUST NOT 假设「`next` 非空 ⇒ 必有中断」。 | B13F1 下游承接 **D-6** | **FR-019** · **裁定 8 / 9** · SC-009 |
| **H-5** | **B8F3 → B15F1** | **M3** | **`context` 不持久化 / 不得回退**：历史快照 MUST NOT 含 `context`；`get_state` / `get_state_history` MUST NOT 从快照还原 `context`；MUST NOT 回退到 `configurable` 承载 `context`，MUST NOT 重新引入节点别名。 | B8F3 下游承接 **D-1 / D-3** | **FR-021** · **裁定 7** · SC-011 |
| **H-6** | **B14F1 → B15F1** | **M3** | **读侧 / 写侧 / id 空间复用**：`.snapshot` / `.pending_writes` / `.scheduler`、写侧关键字、`put_writes` 目标、pending writes 去重 / 排序（`WRITES_IDX_MAP` + `writes_sort_key`）、checkpoint id 排序语义、`context` 不持久化；`get_state` / `get_state_history` 归本 feature；MUST NOT 另立第二套载体或 id 空间。 | B14F1 下游承接 **D-01** | **FR-006 / FR-007 / FR-008** · **裁定 5 / 6** |
| **H-7** | **B14F1 → B15F1** | **M3** | **`checkpoints` 档消费端**：消费 B14F1 已交付的 `on_checkpoint` / `list()` 数据源 **或对 `put` 返回 config 的 `get_tuple(written)` 等价读回**；事件与 `get_state()` 同形；允许 L2 私有 writer 复用 B14F1 写盘助手；MUST NOT 伪造事件或另立事件路径。 | B14F1 下游承接 **D-02** · B8F2 下游承接 **D-2 / D-5** | **FR-022** · **裁定 10** · SC-014 |
| **H-8** | **B14F1 → B15F1** | **M3** | **`NotImplementedError` 边界重新评估**：B14F1 的 `delete_for_runs` / `copy_thread` 在 v1 抛 `NotImplementedError`；本 feature 重新评估后仍保持 v1 未实现，且 MUST NOT 回改 `MemorySaver` 行为。 | B14F1 下游承接 **D-08** | **FR-010** · **裁定 11** |
| **H-9** | **B7F3 → B15F1** | **M3** | **`config` 注解放宽的归属**：`CompiledGraph.get_state` / `get_state_history` 的 `config` 注解仍为 **`RunConfig`**（无映射形态；D-5 原文写「`RunConfig \| None`」是同一冻结面的概括表述）⇒ 本 feature MUST 走「登记 + 回溯修订 + 发起者追认」，并 MUST 复用 B7F3 的**双形态载体边界**（`RunConfig` = 会话面 + `max_concurrency`；普通映射 = 运行期参数 ⇒ 原样交给 L2 ⇒ MUST NOT 在门面层翻译）。 | B7F3 下游承接 **D-5** · 契约 **CF-05** | **FR-023** · **裁定 1** · 破冻结面回溯修订清单 |
| **H-10** | **B10F1 → B15F1** | **M3** | **F-3 的 `tasks` 生产者**：`Interrupt` MUST **不**携带节点名；「哪个节点要审批」由 `StateSnapshot.tasks` 承载 ⇒ `get_state()` / `get_state_history()` MUST 在**读取层按上游 next-tasks 语义**重建 `PregelTask`：对 `snapshot.next` 中每个待执行目标生成一个任务，fan-out 轮另按 `.scheduler["fanout"]` 展开；`interrupts` 从 pending `__interrupt__` 按 `task_id` 关联；其余字段 `None`。**B14F1 存储的 `snapshot.tasks`（本轮完成态）MUST NOT 作为权威来源**；MUST NOT 给 `Interrupt` 增加字段。 | B10F1 **F-3** · **裁定 1** · `specs/b10f1-interrupt-resume/spec.md:126` · **2026-11-23 决策**（原则 XII） | **FR-037** · **裁定 8 / 13** · SC-027 |
| **H-11** | **B14F1 → B15F1** | **M3** | **`tasks` 读取权威移交**：B14F1 存储的「每轮完成态 / 挂起 `()`」`snapshot.tasks` MUST 保留为历史 / 流数据源；自本 feature 起，`CompiledGraph.get_state` / `get_state_history` / `stream(checkpoints)` 的 `tasks` MUST 由读取层按上游 **next-tasks** 重建（`next` + `.scheduler["fanout"]` + pending `__interrupt__`），**MUST NOT** 直接使用存储的 `snapshot.tasks`；B8F2 的 `stream(tasks)` 仍为完成态。 | B14F1 下游承接 **D-09** · `specs/b14f1-checkpointer-memory-saver/spec.md` 裁定 5 后注记 / FR-019 | **FR-037** · **裁定 8 / 13** · SC-027 · R-13 |
| **H-12** | **B8F2 → B15F1** | **M3** | **`checkpoints` 档消费端（D-2 / D-5）**：`stream(stream_mode="checkpoints")` 在挂真实 saver 且 `thread_id` 非空时，为本次运行每次成功 `put` 产出 1 条四键事件（`payload = StateSnapshot`，`tasks`/`interrupts` 为 next-tasks 投影）；无 saver / 无 `thread_id` ⇒ 0 条；**其它六档保持忽略 `checkpointer`**；不恢复历史。 | B8F2 下游承接 **D-2 / D-5** · `specs/b8f2-stream-modes/spec.md` FR-028 与 `checkpoints` 档说明 | **FR-022** · **裁定 10** · SC-014 · 回溯修订清单行 3 / 4 |

---

## Clarifications

### Session 2026-11-22

- Q: 是否有上游 `langgraph` 作为参考？ → A: 有。`langgraph 1.2.11` 已安装，可核对 `get_state` / `get_state_history`；`langgraph-checkpoint-sqlite 3.1.1`（MIT）在本机 uv 缓存中，源码路径 `/home/ctyun/.cache/uv/archive-v0/UtTk-BJ9thKpSH0Q/langgraph/checkpoint/sqlite/__init__.py`（645 行）。
- Q: 既然上游 SQLite 源码可用，是否把现有 spec 中自研的连接 / 并发 / `get_state` 口径改为与上游对齐？ → A: **全面对齐上游**。只保留 freegraph 已冻结的跨 feature 契约（B14F1 的 `put` 关键字 / `CheckpointTuple` 三字段 / int 版本号）与本项目红线（零第三方、`context` 不持久化）。
- Q: 中断挂起时，`get_state()` / `get_state_history()` 的 `StateSnapshot.tasks` 应如何承载「哪个节点要审批」？ → A: **`get_state` 与历史都从 pending `__interrupt__` 重建**。每个 `task_id` 一个 `PregelTask`：`id` = `task_id`，`name` = 节点名（fan-out 取冒号前），`path` = `(节点名,)`，`interrupts` = 该任务中断元组，其余字段 `None`。**（2026-11-23 修订：`tasks` 改为上游 next-tasks 语义，见下）**

### Session 2026-11-23

- Q: `StateSnapshot.tasks` 应采用「本轮已完成任务」（B14F1 存储口径）还是上游的「下一轮待执行任务」？ → A: **采用上游 next-tasks 语义，彻底打破 B14F1 的 `tasks` 冻结面**（宪法原则 XII「最优设计优先」+ 原则 XI「上游优先」）。`get_state` / `get_state_history`（以及 `stream(checkpoints)` 的 payload）MUST 在**读取层**按 `snapshot.next` + `.scheduler["fanout"]` + pending `__interrupt__` 重建任务；B14F1 存储的 `snapshot.tasks`（本轮完成态）**MUST NOT** 作为这些 API 的权威来源。B8F2 的 `stream(tasks)` 仍是「每完成一个 task 一条」的完成态事件，二者语义边界写死。
- Q: `SqliteSaver` 持久化 pending `__interrupt__` 的值（实际是 `(Interrupt,)` 元组）应如何编码？ → A: **channel-aware 编码**：`__interrupt__` 通道的值按 `Interrupt → {"value": ..., "id": ...}` 编码，读回重建为 `Interrupt` 对象；其余普通通道仍按纯 JSON。**MUST NOT** 对 `(Interrupt,)` 直接 `json.dumps`。
- Q: `get_state(None)` 是否应视为可成功读取？ → A: **否**。`None` 只在**类型注解层**接受；解析为空配置后缺 `thread_id` ⇒ **`ValueError`（点名 `thread_id`）**。SC-015 的「接受率」只统计 `RunConfig` / 普通映射；`None` 单独作为「缺 `thread_id` ⇒ `ValueError`」用例。

> **对齐结论**：采用上游的单连接 + `check_same_thread=False` + `threading.Lock` + `PRAGMA journal_mode=WAL` +
> `SqliteSaver(conn)` / `SqliteSaver.from_conn_string(...)` 形态；支持 `:memory:`；跨进程只依赖 SQLite 文件锁，
> **不**额外承诺严格跨进程同线程串行。`get_state` 在**未指定** `checkpoint_id` 时与上游一样把 pending writes
> 合并进 `values`；指定 `checkpoint_id` 时不合并。`StateSnapshot.tasks` 采用上游 **next-tasks** 语义：
> 由 `snapshot.next` + `.scheduler["fanout"]` + pending `__interrupt__` 在读取层重建，**不** 使用 B14F1 存储的
> 「本轮完成态」`snapshot.tasks`。仍保留的少数差异由**零第三方**（JSON 而非 serde）
> 与 B14F1 冻结契约（`put` 关键字 / 三字段 `CheckpointTuple` / int 版本号 / `task_path` 排序）造成。

---

## 形态锁定裁定（`/speckit.plan` 不得再翻）

> 提示词要求：`get_state` / `get_state_history` 的**对外调用形态**、历史**排序语义**、
> `SqliteSaver` 的**注入形态**与**失败行为** MUST 在本 feature 锁定并写死。
> 本节是锁定结论；实现细节（表结构 / SQL / 连接参数）由 plan 决定。

### 裁定 1 · 对外读取面与调用形态

**锁定：对外读取面 = `CompiledGraph.get_state` / `CompiledGraph.get_state_history`
（L1 协议 · B2F1 冻结的方法名 / 返回类别）；`SqliteSaver` 只实现 `Checkpointer` 的 8 个方法，
不提供 `get_state` / `get_state_history`。**

| 项 | 锁定值 |
|---|---|
| 方法位置 | `freegraph.graph` 门面返回的编译产物（L3 `CompiledGraph`） |
| 签名 | `get_state(config: RunConfig \| Mapping[str, Any] \| None) -> StateSnapshot \| None`<br>`get_state_history(config: RunConfig \| Mapping[str, Any] \| None, *, filter: Mapping[str, Any] \| None = None, before: RunConfig \| Mapping[str, Any] \| None = None, limit: int \| None = None) -> Iterator[StateSnapshot]` |
| 调用形态 | **只接受 `config` 载体**（`RunConfig` / 普通映射 / `None`）；**MUST NOT** 接受裸 `thread_id: str`（裸 `str` ⇒ `TypeError`）。⚠️ **`None` 仅在类型注解层接受**：解析为空配置后必然缺 `thread_id` ⇒ **`ValueError`**（不构成成功读取路径）。 |
| 会话标识 | `configurable["thread_id"]` 优先于顶层 `thread_id`（`RunConfig.resolved_thread_id()` 口径）；缺失 / 空串 ⇒ `ValueError`（点名 `thread_id`） |
| saver 来源 | 只用 `compile(checkpointer=...)` 注入的 saver；v1 **不支持** config 级 `checkpointer`（无子图） |
| 未挂 saver | `checkpointer` 为 `None` / `True` / `False` ⇒ `ValueError`（消息含 `No checkpointer set` · 上游同款） |
| 未找到快照 | `get_state` 返回 **`None`**（L1 协议空值语义）；`get_state_history` 返回**空迭代器** |
| 返回载体 | `StateSnapshot`（L1 冻结的 8 字段），**不是裸 dict** |

**L1 协议签名边界**：L1 `CompiledGraph` Protocol 的 `get_state_history` **保持 `config` 单参数**；
`filter` / `before` / `limit` 是 **L3 实现体**的 keyword-only 扩展，**不属于 L1 冻结面改动**
（与 R-3 / SC-023 一致）。

**理由**：① 与上游 `graph.get_state(config)` / `get_state_history(config)` 同款调用形态
（`langgraph/pregel/main.py:1392` / `:1480`）；② L1 已冻结这两个方法名与返回类别
（`src/freegraph/contracts/protocols.py:288-290`）；③ 双形态 `config` 复用 B7F3 的 CF-05，
**MUST NOT** 在门面层把映射翻译成 `RunConfig`。

### 裁定 2 · `SqliteSaver` 的公开注入形态（**全面对齐上游**）

**锁定：与上游 `langgraph-checkpoint-sqlite 3.1.1` 同款的两个入口（`__init__.py:85-130`）：**

```
SqliteSaver(conn: sqlite3.Connection, *, on_checkpoint: Callable[[StateSnapshot], None] | None = None)
SqliteSaver.from_conn_string(conn_string: str, *, on_checkpoint=None) -> Iterator[SqliteSaver]  # @contextmanager
```

| 项 | 锁定值 |
|---|---|
| 连接注入 | `SqliteSaver(conn)` 直接持有调用方传入的 `sqlite3.Connection`；**不**关闭调用方的连接 |
| 连接字符串 | `from_conn_string(conn_string)` 用 `sqlite3.connect(conn_string, check_same_thread=False)` 打开；退出 `with` 时关闭连接（上游 `closing(...)` 同款） |
| `:memory:` | **支持**（`from_conn_string(":memory:")`；上游同款） |
| 路径处理 | `conn_string` 原样交给 `sqlite3.connect`；**MUST NOT** `expanduser` / `expandvars` / 读环境变量 / 联网解析 |
| 线程安全 | 每实例一把 `threading.Lock`；单连接 + `check_same_thread=False`（`from_conn_string` 自动设置；`SqliteSaver(conn)` 由调用方负责）⇒ 同实例多线程串行化（上游 `__init__.py:95` / `:124` 同款） |
| 建库 / 建表 | `from_conn_string` 打开 / 创建数据库文件；首次操作时 `setup()` 执行 `PRAGMA journal_mode=WAL` + `CREATE TABLE IF NOT EXISTS`（上游 `__init__.py:132-166` 同款）；**不**要求「读取不创建文件 / 表」 |
| 事务 | 每次写操作在 `cursor()` 上下文内执行并 `commit()`；异常时回滚（上游 `__init__.py:168-189` 同款） |
| 回调扩展 | `on_checkpoint` 每次成功 `put` 恰调用一次（锁外、异常吞掉、不回滚），属 freegraph 对 B14F1 的扩展 |
| 不暴露 | **不**提供 `serde` 参数（零第三方；序列化见裁定 3）；**不**提供额外的 `close()`；连接生命周期由 `from_conn_string` 上下文或调用方管理 |
| 公开面 | `freegraph.persistence.__all__` 增加 `SqliteSaver`；`freegraph.graph` 门面 **MUST NOT** 转出（G18） |

**理由**：① 用户在 clarify 轮选择「全面对齐上游」⇒ 构造形态 / 连接模型 / `:memory:` / WAL 均照抄；
② 上游源码明确「单连接 + `check_same_thread=False` + 锁」的线程安全模型，freegraph 照抄；
③ 零第三方依赖只影响序列化（上游 serde → 标准库 JSON，裁定 3），不影响公开入口；
④ `on_checkpoint` 是 B14F1 已冻结的数据源扩展，不改变上游入口语义。

### 裁定 3 · 存储载荷与序列化

**锁定：`SqliteSaver` 用标准库 `json` 持久化「纯数据」载荷；读回时重建 L1 对象。**

| 载荷 | 写入 | 读回 |
|---|---|---|
| `values` | `json.dumps`（`Mapping` ⇒ JSON object） | `json.loads` ⇒ `dict` |
| `metadata` | JSON 安全归一（`next` / `interrupts` / `tasks` 转 array / object；`scheduler` 原样） | `dict`；`next` / `interrupts` / `tasks` 重建为 tuple / 对象；`.scheduler` = `metadata.get("scheduler", {})` 的副本 |
| `next` | JSON array | `tuple[str, ...]` |
| `interrupts` | 每个元素存 `{"value": ..., "id": ...}` | `tuple[Interrupt, ...]`（`Interrupt(value=..., id=...)`） |
| `tasks` | 每个元素存 `PregelTask` 的 JSON 安全投影（B14F1 历史「本轮完成态」字段；**读取 API 不再以其为权威**） | `tuple[PregelTask, ...]`；`path` / `interrupts` 重建为元组 |
| `writes`（pending write 的 `value`） | **channel-aware**：普通通道 `json.dumps(value)`；`channel == "__interrupt__"` 时每个 `Interrupt` 存 `{"value": ..., "id": ...}` | 普通通道 `json.loads`；`__interrupt__` 读回 `tuple[Interrupt, ...]`（元素按 `Interrupt(value=..., id=...)` 重建） |
| `parent_config` | 只存父 `checkpoint_id` | `RunConfig(thread_id=..., configurable={"checkpoint_id": ...})` |
| `created_at` | UTC ISO-8601 字符串 | 原样字符串 |

- 载荷 MUST 可被标准库 `json.dumps` 序列化（`__interrupt__` 先按上文投影为 JSON 安全对象，
  **MUST NOT** 对 `(Interrupt,)` 直接 `json.dumps`）；不可序列化 ⇒ **`TypeError`**，且该次调用
  **零写入**（原子性）。`PregelTask` 的 `error` 必须为 `None`（v1 持久化快照不含异常对象）；
  非 `None` ⇒ `TypeError`。
- **JSON 往返语义**：`values` 与 `metadata` 的任意用户容器遵循 `json` 语义（tuple → list）；
  **冻结字段** `next` / `tasks` / `interrupts` MUST 在读回时重建为 tuple（`Interrupt` /
  `PregelTask` 也重建为对象）。因此「任意 `values` 中的 tuple 往返后变 list」是**纯数据约束的
  已知差异**（登记 **X-05**），MUST NOT 声称与 `MemorySaver` 的任意对象深拷贝完全等价。
- **`PregelTask` 的持久化约束**：`state` MUST 为 `None`（v1 无子图）；`result` MUST 可 JSON
  序列化（否则 `TypeError`）；`error` MUST 为 `None`。读回时按对象重建。
- **`__interrupt__` 的 channel-aware 编码**：`put_writes` 收到 `channel == "__interrupt__"` 时，
  其值 MUST 是 `Interrupt`（或 `Interrupt` 序列）；编码为 `{"value", "id"}` 投影；读回
  `.pending_writes` 时 MUST 重建为 `Interrupt` 对象（与 `StateSnapshot.interrupts` 元素同型）。
  其它通道的值按普通 JSON 处理。**B14F1 存储的 `metadata["tasks"]` / `snapshot.tasks`
  仅保留为历史「本轮完成态」字段；`get_state` / `get_state_history` 的 `tasks` MUST 由
  裁定 8 / 13 的 next-tasks 算法重建。**
- **MUST NOT** 使用 `pickle` / msgpack / 第三方 serde（安全面 + 零依赖）。
- **Schema 对齐**：内部表结构镜像上游（`checkpoints` / `writes`；`checkpoint_ns` 在 v1 恒为
  `""`；主键 `(thread_id, checkpoint_ns, checkpoint_id)` / `(thread_id, checkpoint_ns,
  checkpoint_id, task_id, idx)`）⇒ 表名 / 列名 / SQL 仍是**内部实现细节**，不构成对外承诺。
  freegraph 额外保留一个内部 `task_path` 列（或等价存储），以复用 B14F1 的
  `.pending_writes` 排序 `(task_path, task_id, idx)`；上游 schema 无此列，属**内部结构差异**。
- 关系：上游用 `JsonPlusSerializer` / msgpack（`langgraph-checkpoint-sqlite 3.1.1` ·
  `__init__.py:70-80` / `:387-445`）⇒ freegraph 用**标准库 JSON** ⇒ 行为面是「纯数据 /
  可序列化」，实现面是 **DIFF**；本项为**必须自研区 ③（零依赖）**，登记 **X-05**。

### 裁定 4 · checkpoint 顺位 id 与父链

**锁定：完全复用 B14F1 的 checkpoint 顺位 id 空间，不另立第二套。**

- 每线程从 `1` 开始单调递增；格式 `f"{n:032d}"` ⇒ 字典序 == 数值序。
- 重启 / 新实例后，下一个 id = 该线程**已存最大 id + 1**（不是进程内计数器重置）。
- `parent_config` = 该线程上一快照的 `config`（首条为 `None`）。
  > ⚠️ **回溯修订（B16F1 · 2026-11-23 · 拆分而不删）**：自 B16F1 起，当
  > `config.configurable["checkpoint_id"]` 为**非空字符串**时，`parent_config` = 该 id
  > （显式父链，用于时间旅行分叉）；缺失 / 空串仍保持「上一快照（最新）」原语义。
  > 运行期常规写盘携带「当前 checkpoint id」作 parent，可观察行为不变。
  > 新口径见 `specs/b16f1-update-state-time-travel/spec.md` 裁定 3 / FR-017 / R-2。
- `checkpoint_id` 是 `get_state` 按 id 定位、`get_state_history` 排序、`before` 过滤的**唯一**依据。
- 同一实例内由 `threading.Lock` 串行化；`put` 的 `MAX+1` 在事务内完成。跨实例 / 跨进程不承诺严格同线程串行；id 冲突或 `database is locked` 按裁定 12 **原样传播，不额外重试**。MUST NOT 覆盖已有快照。

### 裁定 5 · 读侧 / 写侧最小契约（逐字复用 B14F1）

**锁定：`SqliteSaver` 的 8 个方法语义与 B14F1 `MemorySaver` 逐字一致；只换存储介质。**

- `get_tuple(config)` ⇒ `CheckpointTuple | None`，恰好三个字段 `.snapshot` / `.pending_writes` /
  `.scheduler`；`configurable["checkpoint_id"]` 有值 ⇒ 取指定快照（不存在 ⇒ `None`），
  否则取该线程最新快照。
- `put(config, *, values, metadata)` ⇒ 返回带新 `checkpoint_id` 的 `RunConfig`；
  `values` / `metadata` 必须是 `Mapping`（否则 `TypeError`）；快照 8 字段按 B14F1 组装。
  > ⚠️ **回溯修订（B16F1 · 2026-11-23 · 拆分而不删）**：显式
  > `configurable["checkpoint_id"]`（非空）⇒ `parent_config` = 该 id；缺失 / 空串仍为最新。
  > 见 `specs/b16f1-update-state-time-travel/spec.md` 裁定 3 / FR-017 / R-2。
- `put_writes(config, *, writes, task_id, task_path="")` ⇒ 目标由
  `configurable["checkpoint_id"]` 指定（缺 key ⇒ `KeyError`；指定 id 不存在 ⇒ `ValueError`）；
  `task_id` 非空 `str`（否则 `TypeError` / `ValueError`）。
- 去重键 `(task_id, WRITES_IDX_MAP.get(channel, idx))`：普通通道跨调用同 `(task_id, idx)`
  **首次生效**；保留通道（`__error__` / `__scheduled__` / `__interrupt__` / `__resume__`）
  **最后一次生效**（同一次调用内也覆盖）。
  > **名称说明**：`WRITES_IDX_MAP` / `writes_sort_key` 是**上游名**；freegraph 实际复用
  > `src/freegraph/persistence/memory.py` 的私有 `_WRITES_IDX_MAP`，排序键为
  > `(task_path, task_id, idx)`，不引入同名公开符号。
- `.pending_writes` 顺序 = `(task_path, task_id, idx)` 升序（`writes_sort_key`；B14F1 冻结）。
- `list(config=None, *, filter=None, before=None, limit=None)`：`config=None` 全部线程
  （线程按**首次写入顺序** · B14F1 冻结；与上游「全表 `checkpoint_id` 降序」不同，属 B14F1
  契约带来的**内部结构差异**）；同线程 checkpoint id **降序**；`before` 排除
  `id >= before_id`；`limit <= 0` ⇒ 空（B14F1 冻结；SQLite 原生负 `LIMIT` 视为无限，freegraph
  **不**采用该行为）；**`limit` 是全局上限（`config=None` 时跨线程累计）**；返回迭代器。
- `filter` 采用上游 `search_where` / `_metadata_predicate` 的口径（`langgraph-checkpoint-sqlite
  3.1.1` · `utils.py:9-100`）：key MUST 匹配 `^[a-zA-Z0-9_.-]+$`（否则 `ValueError`），值经
  `json_extract(CAST(metadata AS TEXT), '$.<key>')` 比较；`None` 用 `IS ?`，`bool` 转 `1/0`，
  `dict` / `list` 用无空格 JSON 串。这是 B14F1「顶层 key 精确匹配」的**上游同款扩展**。
- `get_next_version(current, channel=None)` ⇒ `int`：`None ⇒ 1`；`int`（非 `bool`）⇒ `current + 1`；
  其它 ⇒ `TypeError`（B14F1 的 X-02）。

### 裁定 6 · pending writes 与「真异常 + 中断同现」

**锁定：逐字复用 B14F1 / B10F1 的留痕口径；本 feature 只负责读出。**

- 挂起时 `put` 的 `metadata` 含 `next` / `interrupts` / `tasks` / `scheduler`；本 feature
  **原样存取**，MUST NOT 解释或改写调度账本。
- 「真异常 + 中断同现」时，B10F1 的 **X-5**（B12F1 记作 **X-4**）已把中断元组写入 pending writes
  （通道 `__interrupt__`）⇒ `get_state()` MUST 能把它投影到 `StateSnapshot.interrupts`
  （见裁定 8）。**这不是新功能**，只是把上游本来留下的痕迹读出来。
- MUST NOT 为中断留痕新增附注 / 调度字段 / 第二套载体。

### 裁定 7 · `context` 不持久化

- `SqliteSaver` MUST NOT 读取、保存、还原、透出 `RunConfig.context`；
  `snapshot.config.context` MUST 为 `None`；`metadata` / `.scheduler` MUST NOT 出现 `context`。
- `get_state` / `get_state_history` MUST NOT 从快照还原 `context`；本次调用的 `config.context`
  不参与读取。
- MUST NOT 回退到 `configurable` 承载 `context`；MUST NOT 重新引入节点别名。

### 裁定 8 · `get_state` 的组装与 next-tasks / `interrupts` 投影（**全面对齐上游**）

**锁定：`get_state` 在未指定 `checkpoint_id` 时像上游一样把 pending writes 合并进 `values`；
指定 `checkpoint_id` 时不合并。`get_state_history` 不合并 `values`。`tasks` 在两条路径都按
上游 **next-tasks** 语义（下一轮待执行任务）重建；**MUST NOT** 使用 B14F1 存储的
「本轮完成态」`snapshot.tasks` 作为权威来源。**

1. 取 `t = checkpointer.get_tuple(config)`；`t is None` ⇒ `get_state` 返回 `None`。
2. **指定 / 未指定的判定**：`configurable["checkpoint_id"]` **存在但为 `None` / 空串** ⇒
   视为**未指定**（取最新快照，并按下文合并 pending）；只有**非空字符串**才视为「指定 id」。
3. `values`：
   - **未指定** `configurable["checkpoint_id"]` ⇒ 以 `t.snapshot.values` 为底，按运行期同款
     的**通道归约语义**（C6）把 `t.pending_writes` 中**非保留通道且 `task_id ∈ snapshot.next`**
     的写入按 `(task_path, task_id, idx)` 升序合并进一份**副本**
     （上游 `apply_pending_writes=True` 同款 · `langgraph/pregel/main.py:1431` ·
     `:1239-1248` 的 `if tid not in next_tasks: continue`）；
   - **指定** `checkpoint_id` ⇒ 直接用 `t.snapshot.values`（上游同款：不应用 pending writes）；
   - 任何情况下 MUST NOT 修改存储中的快照；归约失败 ⇒ 原异常传播，存储零变化。
4. `next` / `config` / `metadata` / `created_at` / `parent_config` **原样**取自
   `t.snapshot`（其中 `t.snapshot.config` 即由 `thread_id` + `configurable["checkpoint_id"]`
   **重建**的值 ⇒ 与 FR-015「`config` 只含两键」等价；`context` 恒为 `None`）。
5. `tasks` 的组装（`get_state` 与 `get_state_history` **同款** · 上游 `prepare_next_tasks` 口径）：
   - **数据源**：`next_nodes = tuple(t.snapshot.next)`；`fanout = t.scheduler.get("fanout", {})`
     （`.scheduler` 由 B14F1 的 `CheckpointTuple` 提供；`fanout` 的形状 =
     `{producer_task_key: {"producer", "suppresses_static", "tasks": [{"target", "arg", "index", ...}]}}`）。
     **MUST NOT** 以 `tuple(t.snapshot.tasks)` 为底或与之合并。
   - **pending 中断索引**：遍历 `t.pending_writes` 中 `channel == "__interrupt__"` 的写入
     （按既有 `(task_path, task_id, idx)` 升序），按 `task_id` 归组；每个值 MUST 是
     `Interrupt` 或 `Interrupt` 序列（否则 `TypeError`），并**重建为 `Interrupt` 对象**。
   - **枚举 next tasks**（**两类来源的 `id` 域不同**：`next` 来源 = **运行时 `task_key` 权威**；
     `fanout` 账本来源 = **本地枚举 id** · **MUST NOT** 与之做相等 / 去重假设）：
     a. **fan-out 账本来源（已调度、尚未执行）**：按 `fanout` 的 producer task key 升序、再按
        各 `tasks` 的 `index` 升序，为每个 fan-out 项生成一个任务：
        `id = f"{target}:{index}"`（**本地枚举 id · 非运行时 `task_key`** —— 该任务尚未执行，
        运行时 `task_key`（全局 records 下标）尚未分配）、`name = target`、
        `path = (target, index)`、`interrupts = ()`（**尚未执行 ⇒ MUST 无 pending 中断**；
        MUST NOT 用 `pending.pop`）、其余字段 `None`；
     b. **`next` 中的任务项（已调度 / 挂起现场 · 以运行时 `task_key` 为准）**：对 `next_nodes`
        中的每一项（`next` 与 fanout 账本**不重叠**：运行时 `_determine_triggers` 不把 pending
        fan-out 写入 `next`）：
        - 若含 `:`（形如 `节点名:TaskId`，fan-out 挂起现场）⇒
          `id = next_node`（**= 运行时 `task_key`**）、`name = next_node.split(":", 1)[0]`、
          `path = (name, TaskId)`（`TaskId` 为冒号后的值，能转 `int` 时转 `int`）、
          `interrupts = pending.pop(id, ())`；
        - 否则（标准任务）⇒ `id = name = next_node`、`path = (next_node,)`、
          `interrupts = pending.pop(next_node, ())`；
        - 其余字段 `None`。
        ⚠️ **MUST NOT** 对 (a) 与 (b) 做跨源 `id` 去重 / 相等合并：两源若在同一 checkpoint
        同时出现，视为**两条独立任务**（并断言不变量）；差分只比较 `tasks`、不比较 fan-out 轮的
        `next` 字面值。
     c. **兜底**：`next_nodes` 为空且 `fanout` 为空 ⇒ `tasks = ()`；若仍有未关联的 pending
        `__interrupt__`（理论不应出现）⇒ 按 pending 顺序追加任务（`id = task_id`、
        `name = task_id.split(":", 1)[0]`、`path = (name,)`、`interrupts` = 该载荷），
        **MUST NOT** 静默丢弃。
   - **顺序**：按 `name` 升序；同名 fan-out 任务按 `TaskId`（`index` / 冒号后值）升序
     （标准任务按节点名序 · 含 fan-out 的轮按 TaskId 序 · B11F1 F-14）。
   - **静态挂起 / 普通快照**：`next` 非空 ⇒ `tasks` 为该 `next` 的任务（`interrupts` 来自 pending，
     无 pending 则为 `()`）；`next` 为空且无 fan-out ⇒ `tasks = ()`。
   - **MUST NOT** 伪造任务；任务只来自真实的 `next` / `fanout` / pending `__interrupt__`。
6. `interrupts` 的组装（`get_state` 与 `get_state_history` **同款**）：
   - 若第 5 步任一 `task.interrupts` 非空 ⇒ **按 `tasks` 顺序展平**各任务的载荷元组；
   - 否则若 `t.snapshot.interrupts` 非空 ⇒ 原样使用（兼容 B10F1 的历史快照）；
   - 否则 ⇒ `()`。
   ⇒ 有 pending `__interrupt__` 时 MUST 等于 `flatten(task.interrupts)`（同序）。
   ⚠️ **MUST NOT** 因为 `snapshot.interrupts` 非空就忽略 pending 中的**新**中断（否则恢复后
   真异常 + 中断同现会读到上一轮的旧中断）。
7. **fan-out 的两种来源注记**：fan-out 任务可能出现在
   (i) `snapshot.next` 中（形如 `节点名:TaskId` · 挂起现场；实测 `('worker:0','worker:1')`），或
   (ii) `.scheduler["fanout"]` 中（fan-out 已调度但尚未执行；此时 `snapshot.next` 可能为 `()`）。
   **两类来源互斥且 id 域不同**：(i) 的 `id` = 运行时 `task_key`（全局 records 下标，**权威**）；
   (ii) 的 `id` = 本地 `index`（每 producer 0 起，**非**运行时 `task_key`）。
   ⇒ **MUST NOT** 跨源按 `id` 合并 / 去重；差分只比较 `tasks`，**不比较** fan-out 轮的 `next` 字面值
   （上游为重复节点名，freegraph 为 `()` 或 `节点名:TaskId`）。
8. 对**每个** checkpoint，`get_state({"thread_id": t, "checkpoint_id": id})` 与
   `get_state_history` 中同 id 的元素 MUST **逐字段相等**（两者都不合并 pending writes）。
   未指定 id 的 `get_state` 的 `values` **可以**与 `get_state_history` 首元素不同
   （前者含 pending 合并 · 上游同款）。
9. `get_state` **MUST NOT** 返回 `None` 表示「线程存在但无快照」以外的语义；`None` 只表示
   该 `thread_id`（或指定 `checkpoint_id`）没有快照。

**理由**：① 用户在 clarify 轮选择全面对齐上游 ⇒ `values` 的 pending 合并照抄
（`langgraph/pregel/main.py:1431`）；② **2026-11-23 决策**：`tasks` 采用上游
`prepare_next_tasks` 的「下一轮待执行任务」语义（原则 XII 最优设计 + 原则 XI 上游优先）
⇒ 读取层从 `next` / `.scheduler["fanout"]` / pending `__interrupt__` 重建；③ pending 合并与
next-tasks 组装由 **L3 门面**在读取时调用 **L2 私有只读助手** `runtime._state_read` /
`merge_pending_writes`（复用 L2 的归约器与调度账本；L3→L2 为合法方向），不违反 ARCH-1
（L4 仍只依赖 L1）；④ B12F1 的 D-7 要求 `get_state` 的中断与 `__interrupt__` 结果键逐项一致
⇒ 必须读 pending `__interrupt__`；⑤ 合并 / 重建只发生在**返回副本**上，存储中的快照 /
写入分层**不被破坏**。

### 裁定 9 · 历史快照的排序与静态挂起

**锁定**：`get_state_history` 按 `checkpoint_id` **倒序**（最新在前），与上游文档同款。

- 顺序判据：`checkpoint_id` 字符串降序（32 位零填充 ⇒ 字典序 == 数值序）；
  与 `saver.list(..., before=..., limit=...)` 的输出顺序**逐条一致**。
- 数量判据：无过滤时，长度 == 该 `thread_id` 成功 `put` 的次数（每条快照 = 一次 `put`）。
- `values` 判据：历史元素直接用 `snapshot.values`，**不**合并 pending writes（上游
  `get_state_history` 同款 · `langgraph/pregel/main.py:1505-1530`）；
  `tasks` / `interrupts` 按**裁定 8 的 next-tasks 算法**从 `next` + `.scheduler["fanout"]` +
  pending writes 计算（上游 `_prepare_state_snapshot` 在历史路径同样计算 tasks / interrupts ·
  `main.py:1451-1480`）；**MUST NOT** 使用历史快照存储的「本轮完成态」`snapshot.tasks`。
- 静态挂起：`interrupts == ()` 合法；`suspension_kind` / `static_ack` 原样保留；
  `next` **允许为空**；MUST NOT 要求「`next` 非空 ⇒ 必有中断」。静态挂起时 `tasks` 仍为
  `next` 的任务（`interrupts == ()`），**不是**「无挂起」的等价物。
- 上游的额外 `__start__` 快照（`metadata["step"] == -1`）在 freegraph **不存在**；
  差分比较「实际 super-step 快照」时 MUST 按 B14F1 的既有口径排除该额外快照
  （该差异来自 B14F1 已记录的差分排除规则，**不登记新偏离编号**；X-04 仅指
  `checkpoints` 事件载荷形态）。
- `filter` / `before` / `limit`：`SqliteSaver` 后端逐字复用其 `list` 语义（B14F1 裁定 6 +
  上游 `search_where` / `_metadata_predicate` 的 key 校验与 JSON 提取）；`MemorySaver` 后端保持
  B14F1 顶层精确匹配（**不改** `MemorySaver`）；`limit <= 0` ⇒ 空；
  `before` 指向不存在的 id ⇒ 按字符串比较，不抛；`SqliteSaver` 的非法 `filter` key ⇒ `ValueError`。
- 返回**迭代器**；实现 MUST 在返回前**急切消费**底层查询结果（避免持有数据库游标）。

**证据**：上游 `get_state_history` 文档逐字「most recent checkpoint / `StateSnapshot` being the first
in the list」（`harness/docs/oss/python/langgraph/checkpointers.md:170`）；实测 E8
`HISTORY: 6`（`harness/reports/Q3-LangGraph的开源边界.md:43`）；上游实现见
`langgraph/pregel/main.py:1505-1530`。

### 裁定 10 · `stream(..., stream_mode="checkpoints")` 的消费端

**锁定：本 feature 完成 B8F2 的 `checkpoints` 档消费端接线，事件信封沿用 B8F2 的四键形态。**

- 条件：`compile(checkpointer=<真实 saver>)` **且** 生效 `thread_id` 非空。
- 产出：本次运行期间**每次成功 `put`** 恰好产出一条 `stream_mode == "checkpoints"` 事件；
  `payload` = 与该 checkpoint 对应的 `StateSnapshot`（与 `get_state()` **同形**：8 字段同构；
  `values` 为存储快照值，不保证等于 pending 合并结果；**`tasks` / `interrupts` 按裁定 8 的
  next-tasks 算法投影**，与 `get_state()` 对该 id 的结果一致；**不使用**存储的完成态
  `snapshot.tasks`）。
- 顺序：按 checkpoint 创建顺序（旧 → 新），与运行进度一致。
- 信封：`{"stream_mode", "payload", "run_id", "thread_id"}`（B8F2 裁定 1）**零改动**。
- 无 saver / 无 `thread_id`：`checkpoints` 档产出 **0 条**（不抛异常 · 不伪造）。
- MUST NOT 伪造事件；MUST NOT 从 `list()` 伪造「本次运行」之外的历史快照
  （历史枚举归 `get_state_history`）。
- 数据源 = B14F1 的 `on_checkpoint`（每次成功 `put` 一次）与 / 或 `list()`，**或**运行期对
  `put` 返回 config 的 `get_tuple(written).snapshot` 等价读回；用户未显式传 `on_checkpoint`
  时，`stream` 仍 MUST 能产出（由运行期接线保证）。
- **允许** L2 私有 `StreamCheckpointWriter` 复用 B14F1 写盘助手；它 MUST NOT 伪造事件，
  MUST NOT 改变其它 mode 的既有事件序列 ⇒ **不是**「另立事件路径」。
- **模式边界**：只有 `"checkpoints" in modes` 时写 saver；其它六档保持 B8F2 v1 的
  「忽略 checkpointer」语义。
- **不恢复历史**：stream MUST NOT 从历史快照恢复执行、MUST NOT 把历史快照并入本次事件；
  `StreamCheckpointWriter.prepare()` **允许**读取最新 `checkpoint_id` 以设置本次首条快照的父链
  （这不构成「恢复」）。只把本次运行的新快照追加到该 thread。

### 裁定 11 · `delete_for_runs` / `copy_thread` 的 v1 边界

**重新评估结论：v1 继续抛 `NotImplementedError`，不实现运行级删除 / 线程复制。**

- 与 B14F1 / 上游 `BaseCheckpointSaver` 同款（`langgraph/checkpoint/base/__init__.py:355-388`）。
- **MUST NOT** 回改 `MemorySaver` 的行为；两个后端在 v1 的边界一致。
- 运行级删除 / 线程复制若未来实现，MUST 走契约修订，并保持本 feature 的 id 空间与读侧载体不变。

### 裁定 12 · 失败信号与原子性

**锁定：不新增 L1 异常类型；持久化失败以**底层 `sqlite3.Error` 子类**原样传播，绝不静默。**

| 场景 | 锁定行为 |
|---|---|
| `SqliteSaver(conn)` 的 `conn` 不是 `sqlite3.Connection` | 属性使用处的底层异常传播（`AttributeError` / `TypeError`）；构造不做鸭子校验（上游同款） |
| `from_conn_string` 的路径不可打开 / 父路径不是目录 | `sqlite3.OperationalError` / `OSError` 原样传播 |
| 磁盘满 / 权限不足 / 文件损坏 | `sqlite3.OperationalError` / `sqlite3.DatabaseError` **原样传播**；MUST NOT 吞掉 / 包装 |
| `database is locked` | 不额外重试；由 SQLite 自身的忙等待 / 文件锁决定；仍失败 ⇒ 原样传播 `sqlite3.OperationalError`（同实例多线程由 `threading.Lock` 串行化，测试工作负载下 MUST NOT 泄漏） |
| `from_conn_string` 上下文退出后继续调用 | 底层 `sqlite3.ProgrammingError` 原样传播（连接已关闭 · 上游 `closing` 同款） |
| 单次 `put` / `put_writes` 失败 | 事务回滚 ⇒ **零残留**（不出现「快照已写、父链未写」的半成品） |
| `SqliteSaver` 的 `filter` key 不匹配 `^[a-zA-Z0-9_.-]+$` | `ValueError`（上游 `utils.py:9-25` 同款）；`MemorySaver` 保持 B14F1 顶层匹配（不校验 key） |
| 读取损坏行 / 未知格式 | 作为持久化损坏处理：该次读取失败并传播明确异常；MUST NOT 静默返回半快照 |

- MUST NOT 在失败时删除 / 重建 / 迁移用户数据库（只回滚本次事务）。
- MUST NOT 读环境变量、MUST NOT 出站。

### 裁定 13 · next-tasks 的 `PregelTask` 映射（**上游 `prepare_next_tasks` 口径**）

**锁定：`get_state` / `get_state_history` / `stream(checkpoints)` 的 `tasks` 按上游
next-tasks 语义重建 `PregelTask`（下一轮待执行任务），承载「哪些任务待执行 / 哪个节点要审批」，
且不给 `Interrupt` 增加节点名字段。B14F1 存储的 `snapshot.tasks`（本轮完成态）MUST NOT
作为权威来源。**

| 字段 | 标准任务 | fan-out 任务（`next` 来源 · 权威） | fan-out 任务（`fanout` 账本来源 · 未执行） |
|---|---|---|---|
| `id` | 节点名 | `next_node`（= **运行时 `task_key`** `f"{节点名}:{全局TaskId}"`） | `f"{节点名}:{本地index}"`（**本地枚举 id · 非运行时 `task_key`**） |
| `name` | 节点名 | 节点名（`id.split(":", 1)[0]`） | 节点名（`target`） |
| `path` | `(节点名,)` | `(节点名, TaskId)`（`TaskId` 为**运行时** `task_key` 冒号后的全局值） | `(节点名, 本地index)` |
| `interrupts` | 同 `id` / 节点名的 pending `__interrupt__` 载荷元组（无则 `()`） | 同 `id` 的 pending `__interrupt__` 载荷元组（无则 `()`） | **恒 `()`**（尚未执行 ⇒ 无 pending） |
| `error` / `state` / `result` | 均为 `None`（v1 无子图 / 未执行的任务无结果） | 同左 | 同左 |

- **任务来源**：`snapshot.next`（标准任务；其中 `节点名:TaskId` 项按 fan-out 任务处理，`id` 取运行时
  `task_key`）+ `.scheduler["fanout"]`（已调度未执行的 fan-out 任务，`id` 用本地 `index`）。
  **两源 id 域不同、互斥**：`MUST NOT` 跨源按 `id` 去重 / 相等合并；若同一 checkpoint 同时出现，
  视为两条独立任务并断言不变量。pending `__interrupt__` 只用于给 `next` 来源任务附加 `interrupts`
  （按运行时 `task_key` 关联）。
- **MUST NOT** 以 `snapshot.tasks` 为底、**MUST NOT** 与之合并或去重。
- **`id` 口径**：`next` 来源 = 运行时 `task_key`，与 `.pending_writes` 的 `task_id` 同款
  （标准 = 节点名；fan-out = `f"{节点名}:{全局TaskId}"`）；`fanout` 账本来源 = 本地 `index`
  （**不是**运行时 `task_key`，不得用于 pending 关联）。同一 checkpoint 内唯一；跨 checkpoint 可重复
  （上游用 UUID，但 L1 未冻结 `PregelTask.id` 生成方式 · B8F2 FR-020「生成方式不冻结」）。
- **顺序**：按 `name` 升序；同名 fan-out 任务按 `TaskId`（`next` 来源 = 运行时全局 TaskId；账本来源 =
  本地 `index`）升序（标准任务节点名序 · fan-out TaskId 序 · B11F1 F-14）。
- **静态挂起**：`tasks` = `next` 的任务，`interrupts == ()`；**不是**「无挂起」的等价物。
- **无 `next` 且无 fan-out** ⇒ `tasks = ()`（收敛快照 / 初始快照）。
- **真异常 + 中断同现**：pending `__interrupt__` 附着在 round-start 快照上；该快照的
  `next` / `fanout` 即错误轮的目标 ⇒ 重建出的任务带 pending `interrupts`，**不会**混入上一轮
  完成态任务。
- `get_state` 与 `get_state_history` **同款**；`get_state({"checkpoint_id": id})` 与历史同 id
  元素逐字段相等（含 `tasks`）。
- **MUST NOT** 给 `Interrupt` 增加 `name` / 节点名等字段（B10F1 F-3 · 上游 `Interrupt` 只有
  `value` / `id`）。

**理由**：① 2026-11-23 决策：采用上游 `prepare_next_tasks` 的 next-tasks 语义（原则 XII 最优设计 +
原则 XI 上游优先）⇒ 彻底推翻 B14F1 的「本轮完成态 tasks」读取权威；② B10F1 F-3 把节点名交给
`StateSnapshot.tasks`，生产者归本 feature；③ 上游 `_prepare_state_snapshot` /
`prepare_next_tasks` 从 checkpoint + pending writes 计算下一批任务并展平 `interrupts`
（`langgraph/pregel/main.py:1145-1210`）；④ 重建映射只产生**读取副本**，不改变存储，也不改变
`Interrupt` / `PregelTask` 的 L1 字段面。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 进程重启后状态还在（Priority: P1）

作为用户，我的应用重启后，希望上次的运行状态**能从磁盘取回**，而不是丢失。

**Why this priority**：这是本 feature 与 `MemorySaver` 的根本差异，也是「开箱即用的生产级 saver」的存在理由。

**Independent Test**：用 `SqliteSaver.from_conn_string(path)` 跑一张图 → 关闭进程 → 在
**新进程**用同一个 `path` 新建 `SqliteSaver.from_conn_string(path)` →
`get_state({"thread_id": "t"})` 返回的 8 字段与重启前一致。

**Acceptance Scenarios**：

1. **Given** 一个已写入两条快照的数据库文件，**When** 用 `from_conn_string(path)` 新建 saver，
   **Then** `get_tuple` 与 `get_state` 都能取回旧快照。
2. **Given** 上述数据库文件，**When** 在**新的 Python 子进程**中读取，
   **Then** 快照数、`values`、`next`、`configurable["checkpoint_id"]` 与父进程一致。
3. **Given** 数据库文件不存在，**When** `from_conn_string(path)` 打开并只做读取，
   **Then** 数据库 / 表按上游 `setup()` 行为创建，读取返回空（**不**要求「读取不创建文件」）。

---

### User Story 2 - 看当前状态（Priority: P1）

作为用户，我希望随时查看某会话「现在停在哪一步、下一步要干什么」。

**Why this priority**：这是宪法原则 IV「状态快照必须可见」的对外读取面。

**Independent Test**：`compiled.get_state({"thread_id": "t"})` 返回 `StateSnapshot`，
含 `values` / `next` / `config` / `metadata` / `created_at` / `parent_config` / `tasks` / `interrupts`。

**Acceptance Scenarios**：

1. **Given** 一个已跑完的会话，**When** `get_state`，**Then** 返回 8 字段完整的 `StateSnapshot`；
   `next == ()`，`config.configurable["checkpoint_id"]` 非空。
2. **Given** 一个静态挂起（`interrupt_before` / `interrupt_after`）的会话，
   **When** `get_state`，**Then** `next` 指向待执行节点，`interrupts == ()`，
   `suspension_kind` 可取静态值。
3. **Given** 一个动态中断挂起的会话，**When** `get_state`，
   **Then** `interrupts` 与 `invoke` 结果里的 `__interrupt__` 元组**逐项一致**。

---

### User Story 3 - 枚举历史快照做时间旅行（Priority: P1）

作为用户，我希望能列出这次会话的全部历史快照，从而挑一个点回放（回放本身属 B16F1）。

**Why this priority**：这是本 feature 的判定核心——「历史快照可枚举」。

**Independent Test**：`list(compiled.get_state_history({"thread_id": "t"}))` 的长度等于该线程的
`put` 次数，顺序为最新在前，`checkpoint_id` 严格递减。

**Acceptance Scenarios**：

1. **Given** 一个 `a → b` 的图跑完（含初始快照），**When** 枚举历史，
   **Then** 数量 == 成功 `put` 次数；首元素是最新快照，末元素是初始快照。
2. **Given** 同一会话传入 `limit=2` / `before=<id>` / `filter={"source": ...}`，
   **When** 枚举，**Then** 结果与 `SqliteSaver.list` 的同参数结果逐条一致。
3. **Given** 历史中的某个 `checkpoint_id`，**When** `get_state({..., "checkpoint_id": id})`，
   **Then** 返回的快照与历史中同 id 的元素逐字段相等。

---

### User Story 4 - 删除会话数据（Priority: P2）

作为用户，我希望能删掉某个会话的全部持久化数据。

**Why this priority**：隐私 / 清理是生产级 saver 的基本能力；协议已冻结 `delete_thread`。

**Independent Test**：`delete_thread("t")` 后 `get_state` 返回 `None`、历史为空、
`get_tuple` 返回 `None`，其它线程数据逐项不变。

**Acceptance Scenarios**：

1. **Given** 两个线程各有快照，**When** 删除其中一个，
   **Then** 被删线程不可见，另一线程不受影响。
2. **Given** 一个不存在的线程，**When** `delete_thread`，**Then** 幂等、不抛异常。
3. **Given** 删除后同一 `thread_id` 重新写入，**Then** 新线程从 checkpoint id `1` 开始，无旧数据。

---

### User Story 5 - 并发写不互相破坏（Priority: P2）

作为使用者，我可能在多线程 / Windows 上并发写同一个数据库，希望数据完整且不泄漏锁异常。

**Why this priority**：SQLite 的 Windows 文件锁差异是本 feature 最可能返工的点（立项书 §3.5）。

**Independent Test**：同一进程 N 个线程共用**同一个** `SqliteSaver` 实例各写若干快照与
pending writes，结束后每个线程的快照数 / `pending_writes` 内容正确，未出现
`database is locked` 泄漏；测试不做 `linux_only` 标记，在现有 `windows-2025` CI 上通过。

**Acceptance Scenarios**：

1. **Given** 同一 `SqliteSaver` 实例（单连接 + `threading.Lock`），**When** 8 个线程并发
   `put` / `get_tuple`，**Then** 无异常、无数据串扰、checkpoint id 唯一且单调。
2. **Given** 同一实例的并发读与写，**When** 读发生在写提交前，**Then** 读不会看到
   半事务（上游锁 + 事务同款）。
3. **Given** Windows CI，**When** 运行同一并发用例，**Then** 通过且无 `database is locked` 泄漏。
   （跨进程并发写不在严格承诺内；只要求不损坏。）

---

### User Story 6 - `checkpoints` 流式事件（Priority: P3）

作为用户，我希望在 `stream(stream_mode="checkpoints")` 中实时看到本次运行产生的 checkpoint。

**Why this priority**：这是 B8F2 / B14F1 指名交给本 feature 的消费端接线；不影响主执行语义。

**Independent Test**：挂 `SqliteSaver` 跑一张两节点图并消费 `checkpoints` 事件，
事件数 == 本次运行的成功 `put` 次数，每条 `payload` 都是 `StateSnapshot`，
且 `payload.config.configurable["checkpoint_id"]` 互不相同。

**Acceptance Scenarios**：

1. **Given** 挂了 saver 且有 `thread_id`，**When** 消费 `checkpoints`，
   **Then** 每个事件四键完整，`payload` 是 `StateSnapshot`，顺序与创建顺序一致。
2. **Given** 未挂 saver 或 `thread_id` 缺失，**When** 消费 `checkpoints`，
   **Then** 0 条事件、不抛异常、不伪造。
3. **Given** 线程已有历史快照，**When** 只跑一次新运行，
   **Then** `checkpoints` 只含**本次**新增的快照，不含旧历史。

### Edge Cases

- **未知线程**：`get_state` ⇒ `None`；`get_state_history` ⇒ 空；`delete_thread` ⇒ 幂等。
- **`checkpoint_id` 不存在**：`get_state` ⇒ `None`；`get_state_history` ⇒ 空（不抛）。
- **`checkpoint_id` 为 `None` / 空串**：视为**未指定** ⇒ `get_state` 取最新快照并按 pending
  合并；不构成「指定 id」。
- **`thread_id` 缺失 / 空串**：`get_state` / `get_state_history` ⇒ `ValueError`（点名 `thread_id`）。
- **`config` 为 `None`**：类型层接受，但解析后缺 `thread_id` ⇒ `ValueError`（不是成功读取路径）。
- **`checkpoint_ns` 非空**：`get_state` / `get_state_history` ⇒ `ValueError`（v1 无子图）；
  空串 / 缺失视为 `""`。
- **`filter` 非 `Mapping` / `before` 非 `RunConfig` / `Mapping` / `None`**：`TypeError`。
- **pending `__interrupt__` 载荷不是 `Interrupt` 或其序列**：重建 `tasks` / `interrupts` 时
  `TypeError`（不静默丢弃）。
- **`PregelTask.state` 非 `None` / `result` 不可 JSON 序列化 / `error` 非 `None`**：`TypeError`。
- **未挂 saver / `True` / `False`**：`get_state` / `get_state_history` ⇒ `ValueError`
  （消息含 `No checkpointer set`）。
- **裸 `str` / 数字作为 `config`**：`TypeError`（只接受 `RunConfig` / 映射 / `None`）。
- **`conn_string` 为 `:memory:`**：支持（上游同款）；数据只在连接生命周期内存在。
- **`conn_string` 路径不可打开 / 父路径是普通文件**：`sqlite3.OperationalError` / `OSError`
  原样传播；不删除 / 不改写该文件。
- **数据库不存在**：`from_conn_string(path)` 打开 / 创建文件；首次操作 `setup()` 建表（上游同款）。
- **磁盘满 / 权限不足 / 文件损坏**：`sqlite3.Error` 子类原样传播；不吞掉。
- **`database is locked`**：不额外重试；由 SQLite 自身忙等待 / 文件锁决定；仍失败 ⇒ 原样传播；
  同实例多线程由 `threading.Lock` 串行化，测试负载下 MUST NOT 泄漏。
- **`from_conn_string` 上下文退出后继续调用**：`sqlite3.ProgrammingError`（连接已关闭）。
- **`filter` key 含非法字符**：`SqliteSaver` ⇒ `ValueError`（上游 `^[a-zA-Z0-9_.-]+$` 同款）；
  `MemorySaver` 保持 B14F1 顶层精确匹配（不校验 key）。
- **`filter` 的 dotted key**：`SqliteSaver` 按上游 `json_extract` 路径语义；`MemorySaver`
  仍是 B14F1 的**顶层 key 精确匹配** ⇒ 两者对 dotted key 可能不同（B14F1 冻结带来的跨后端差异，
  **不**改 `MemorySaver`）。
- **载荷不可 JSON 序列化**：`TypeError`；该次调用零写入。
- **pending `__interrupt__` 值编码**：`put_writes` 收到 `Interrupt` / `Interrupt` 序列 ⇒ 按
  `{"value", "id"}` 投影后写盘；读回重建为 `Interrupt`；普通通道值仍按纯 JSON。
- **`tasks` 含非 `None` 的 `error`**：`TypeError`（v1 持久化快照不存异常对象）。
- **`metadata` 缺 `next` / `interrupts` / `tasks` / `scheduler`**：分别按 `()` / `()` / `()` / `{}` 处理。
- **`next` / `interrupts` / `tasks` 为 list**：读回归一为 `tuple`。
- **`values` 中的 tuple**：JSON 往返后变 list（C19 纯数据口径 · X-05）；
  冻结字段 `next` / `tasks` / `interrupts` 不受此影响，始终重建为 tuple。
- **`values` / `metadata` 非 `Mapping`**：`TypeError`。
- **重复写入**：普通通道跨调用同 `(task_id, idx)` 首次生效；保留通道最后一次生效
  （同一次调用内也覆盖）。
- **`put_writes` 缺 `checkpoint_id`**：`KeyError`；指定 id 不存在 ⇒ `ValueError`。
- **同一节点多个 fan-out 任务**：pending writes 的 `task_id` 互不相同，不得互相覆盖。
- **静态挂起 `interrupts=()`**：合法，不得误判为「无挂起」；`tasks` 为 `next` 的 next-tasks
  投影（`interrupts` 均为 `()`），**MUST NOT** 退化为 `snapshot.tasks`，MUST NOT 伪造成审批任务。
- **中断挂起**：`tasks` 为 next-tasks 投影；pending `__interrupt__` 按 `task_id` 附着到对应任务
  （标准任务 `id = 节点名`；fan-out `id = f"{节点名}:{TaskId}"`）；fan-out 的 `name` 取冒号前；
  `Interrupt` 不增加节点名字段。
- **真异常 + 中断同现**：`get_state` 的 `interrupts` / `tasks` 来自 round-start 快照的
  `next` / `fanout` + pending `__interrupt__`（即使 `snapshot.interrupts` 非空，也不得忽略
  pending 新中断）；**不会**混入上一轮完成态 `snapshot.tasks`；抛出的异常类型 / 消息 /
  identity 不变。
- **收敛快照**：`next == ()` 且无 fan-out ⇒ `tasks == ()`（与上游同款）。
- **`get_state` 无 `checkpoint_id` 且存在 pending writes**：`values` 按 C6 归约合并
  **`task_id ∈ snapshot.next`** 的非保留通道写入（上游同款）；游离 pending（任务不在
  `next`）**不合并**；指定 `checkpoint_id` ⇒ 不合并；`get_state_history` ⇒ 不合并。
- **`get_state` 无 id 与 `get_state_history` 首元素**：`interrupts` / `tasks` 可相同，
  但 `values` **可以不同**（前者含 pending 合并）⇒ MUST NOT 断言两者 `values` 必相等。
- **`context` 非空**：不出现在快照 / metadata / scheduler / pending writes 中；
  `snapshot.config.context is None`。
- **历史为空**：`get_state_history` 返回空迭代器，不抛。
- **`limit=0` / 负值**：空迭代器。
- **`before` 指向不存在的 id**：按字符串比较，不抛。
- **`list(config=None)`**：线程按首次写入顺序（B14F1 冻结；上游为全表 `checkpoint_id` 降序）；
  同线程 id 降序。
- **`delete_thread` 后重建**：新线程、计数器从 1 开始、无旧数据。
- **`delete_for_runs` / `copy_thread`**：v1 抛 `NotImplementedError`（上游 sync SQLite 未覆写）。
- **回调抛错**：不影响 `put` 的返回值与已提交快照；回调在锁外执行。
- **跨进程读取正在写入的数据库**：不返回半事务数据；写入完成前该快照 MAY 不可见；
  不承诺跨进程并发写的严格串行。
- **Windows 文件锁**：同实例多线程并发写 + 查询不损坏数据库；测试负载下忙等待不泄漏。
- **上游版本漂移**：换 `langgraph` 版本后，本 spec 的全部行号 MUST 重新核实。

---

## Upstream Parity *(mandatory — 宪法原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11**（取证于 **2026-11-22** · 本仓库 `.venv`）；
上游 SQLite 后端 **`langgraph-checkpoint-sqlite 3.1.1`**（MIT）源码已在本机 uv 缓存
（`/home/ctyun/.cache/uv/archive-v0/UtTk-BJ9thKpSH0Q/langgraph/checkpoint/sqlite/__init__.py`，645 行），
**作为行为锚点**；该发行包**未安装进 `.venv`** ⇒ 差分测试在不可导入时 **skip**。
SQLite 的**连接 / 并发 / WAL / 构造入口**按上游源码照抄；仅**序列化**因零第三方改为标准库 JSON
（登记 **X-05**），`put` / id 空间 / `CheckpointTuple` / `task_path` 排序因 **B14F1 已冻结**而保留
freegraph 口径。

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | `get_state(config)` 取最新 / 按 `checkpoint_id` | `langgraph/pregel/main.py:1392-1435` · 文档 `harness/docs/oss/python/langgraph/checkpointers.md:130` | 同款：`configurable["checkpoint_id"]` 有值取指定，否则取最新 | SAME | 照抄上游调用形态 |
| P-02 | 无快照时的 `get_state` | `langgraph/pregel/main.py:1152-1162`（返回空 `StateSnapshot`） | 返回 **`None`** | DIFF（X-01） | L1 `CompiledGraph` 协议已冻结「查不到返回空值」 |
| P-03 | `get_state` 合并 pending writes 进 `values` | `langgraph/pregel/main.py:1431`（`apply_pending_writes=CONFIG_KEY_CHECKPOINT_ID not in ...`）· `:1145-1162` | **无 `checkpoint_id` ⇒ 合并**（C6 归约 · 只改副本）；**有 `checkpoint_id` ⇒ 不合并** | SAME | 全面对齐上游；`get_state_history` 仍不合并（上游同款）。原 X-02 已撤销 |
| P-04 | `get_state_history` 排序 | `langgraph/pregel/main.py:1505-1530` · 文档 `checkpointers.md:170` · 实测 E8 `HISTORY: 6`（`Q3:43`） | 按 `checkpoint_id` **倒序**（最新在前） | SAME | 照抄上游排序语义 |
| P-05 | `get_state_history` 的 `filter` / `before` / `limit` | `langgraph/pregel/main.py:1480-1487` · `:1518-1523` · `langgraph/checkpoint/sqlite/utils.py:9-100` | 同名关键字；`filter` 的 key 校验 / JSON 提取照抄上游；`limit <= 0` / `list(None)` 线程顺序保留 B14F1 | SAME（带 B14F1 冻结差异） | 照抄上游签名与过滤实现；B14F1 的 `limit` / 线程顺序不破 |
| P-06 | 无 checkpointer 时的读取 | `langgraph/pregel/main.py:1400-1401` / `:1496-1497`（`ValueError("No checkpointer set")`） | 同样 `ValueError`，消息含 `No checkpointer set` | SAME | 照抄失败信号 |
| P-07 | `StateSnapshot` 8 字段 | `langgraph/types.py:684-701` | L1 `StateSnapshot` 8 字段逐字同构（**字段集合 / 类型**；`metadata` 内容为 freegraph 内部调度账本，差分投影排除） | SAME | B1F1 已冻结 |
| P-08 | 中断载体的顺序 | B12F1 裁定 25 / D-7（标准任务按节点名序 · fan-out 按 TaskId 序）· 上游 `GraphInterrupt` 元组语义 | `StateSnapshot.interrupts: tuple[Interrupt, ...]`，同序 | SAME | 照抄 B12F1 已冻结口径；上游同轮集合弹出为竞态（B12F1 X-7） |
| P-09 | `config` 载体 | 上游 `RunnableConfig`（`main.py:1392` / `:1480`） | `RunConfig \| Mapping[str, Any] \| None`（B7F3 CF-05） | DIFF（X-03） | freegraph 的已锁定双形态载体边界 |
| P-10 | `checkpoints` 事件载荷 | 上游 `_loop.py:631-636`（`map_debug_checkpoint` 产出 dict）· 实测 E-5（挂 saver 时 3 条） | 四键信封 + `payload` = `StateSnapshot`（`tasks` / `interrupts` 为 next-tasks 投影） | DIFF（X-04） | B8F2 的四键信封（X-1）+ L1 快照载体 |
| P-11 | SQLite 序列化 | `langgraph-checkpoint-sqlite 3.1.1` · `__init__.py:17-30`（serde / JsonPlusSerializer）· `:387-445`（`put` / `put_writes` 用 `dumps_typed`） | 标准库 `json`；纯数据；**`__interrupt__` 通道值 channel-aware 投影 `Interrupt→{value,id}`**；schema 内部 | DIFF（X-05） | 零第三方红线；上游 serde / msgpack 不可用 |
| P-12 | SQLite 连接 / 并发 / WAL | `langgraph-checkpoint-sqlite 3.1.1` · `__init__.py:85-130`（`__init__` / `from_conn_string`）· `:95`（`threading.Lock`）· `:124`（`check_same_thread=False`）· `:141`（`PRAGMA journal_mode=WAL`） | 照抄：单连接 + 每实例锁 + `check_same_thread=False` + WAL；`:memory:` 支持；跨进程只依赖 SQLite 文件锁 | SAME | 全面对齐上游；原 X-06 已撤销 |
| P-13 | `delete_thread` | `langgraph/checkpoint/base/__init__.py:344-353` | 删除该线程全部快照 / 写入；幂等 | SAME | 照抄协议语义 |
| P-14 | `delete_for_runs` / `copy_thread` | `langgraph/checkpoint/base/__init__.py:355-388`（基类 `NotImplementedError`） | v1 同样抛 `NotImplementedError` | SAME | 与上游 base / B14F1 一致 |
| P-15 | `get_next_version` | `langgraph/checkpoint/base/__init__.py:721-740`（**base 默认** `int+1`） | `int+1`（`None ⇒ 1`） | SAME（对照 **base 默认实现**） | 复用 B14F1 的 X-02 口径。⚠️ SQLite 后端覆写为**字符串版本** ⇒ 与 SQLite 对照为 DIFF，见 **P-21**；两行锚点不同，不矛盾 |
| P-16 | 保留通道名 | `langgraph/_internal/_constants.py:9,11,13,17` | `__interrupt__` / `__resume__` / `__error__` / `__scheduled__` 逐字 | SAME | B10F1 契约 §5 |
| P-17 | 配置级 checkpointer / 子图 | `langgraph/pregel/main.py:1396-1398`（`CONFIG_KEY_CHECKPOINTER`）· `:1403-1422`（子图） | v1 只用编译期 saver；无子图 | DIFF | C26 属 v2；不记偏离，属能力边界 |
| P-18 | `context` 持久化 | 上游 `RunnableConfig.configurable` 可携带任意值 | **不持久化**；`snapshot.config.context is None` | DIFF（X-07） | B8F3 D-1 / D-3 已冻结；本 feature 只执行 |
| P-19 | 建库 / 建表 | `__init__.py:132-166`（`setup()`：WAL + `checkpoints` / `writes` 表） | 镜像 `checkpoints` / `writes` 表；`checkpoint_ns` v1 恒 `""`；额外内部 `task_path` 列 | SAME（schema 内部细节） | 表结构不对用户承诺；`task_path` 为复用 B14F1 排序 |
| P-20 | `get_tuple` / `list` 的 pending 排序 | `__init__.py:191-380`（`ORDER BY task_id, idx`） | `(task_path, task_id, idx)` 升序（B14F1 `writes_sort_key`） | DIFF | B14F1 已冻结 `.pending_writes` 排序；内部多存 `task_path`。注：`WRITES_IDX_MAP` / `writes_sort_key` 为**上游名**；freegraph 实际复用私有 `_WRITES_IDX_MAP`、排序键为 `(task_path, task_id, idx)` |
| P-21 | `put` 的 id 来源 / `get_next_version` | `__init__.py:387-445`（`put` 用调用方 `checkpoint["id"]`）· `:626-644`（**SQLite** 字符串版本） | saver 生成每线程 `f"{n:032d}"`；`get_next_version` 返回 `int` | DIFF（对照 **SQLite 实现**） | B14F1 的 X-01 / X-02 已冻结 id 空间与 int 版本；本行锚点为 SQLite 后端（`put` 用调用方 id / 字符串版本）⇒ 与 P-15 的 base 对照不矛盾 |
| P-22 | `list(None)` 的线程顺序 | `__init__.py:295-380`（全表 `ORDER BY checkpoint_id DESC`） | 线程按首次写入顺序；同线程 id 降序 | DIFF | B14F1 裁定 6 已冻结 |
| P-23 | `filter` key 校验 | `utils.py:9-25`（`^[a-zA-Z0-9_.-]+$` · 非法 key ⇒ `ValueError`） | 照抄上游 | SAME | 安全面照抄；防止 SQL 注入 |
| P-24 | `tasks` / `interrupts` 组装（**next-tasks**） | `langgraph/pregel/main.py:1145-1210`（`prepare_next_tasks` / `_prepare_state_snapshot` 从 checkpoint + `pending_writes` 计算任务并展平 `interrupts`）· B10F1 **F-3** | `get_state` / 历史 / `stream(checkpoints)` 均在**读取层**按 `snapshot.next` + `.scheduler["fanout"]` + pending `__interrupt__` 重建 next-tasks（裁定 13）；`interrupts` 按任务顺序展平；**不使用** B14F1 存储的完成态 `snapshot.tasks` | SAME（`id` / `path` 编码为 freegraph 口径） | 2026-11-23 决策：彻底对齐上游 next-tasks；B14F1 存储字段降级为历史/流数据源 |
| P-25 | 缺失 `thread_id` 的读取信号 | `langgraph/pregel/main.py:1392` / `:1480`（挂 checkpointer 但缺 `thread_id`；实测 1.2.11 抛 `ValueError`，部分入口 `KeyError`） | 读取时缺 / 空 `thread_id` ⇒ `ValueError`（点名 `thread_id`） | STRICTER（X-08） | 与 B14F1 的 X-03 同源：显式失败优于静默共享会话 |

### 差分场景组 *(mandatory — 落 `tests/differential/`)*

> 上游 SQLite 后端源码在 uv 缓存中，但**未安装进 `.venv`** ⇒ 运行时不可导入时 **skip**
> （沿用 B5F2 / B9F1 / B14F1 的「缺席即 skip」纪律）。`get_state` / `get_state_history` 的上游
> 对照可用已安装的 `MemorySaver` 完成；SQLite 连接 / 并发 / WAL 的行为按上游源码对齐，差分在
> 不可导入时标 `SKIP (source-aligned)`；序列化差异按 **X-05** 判定。
> ⚠️ 上游的额外 `__start__` 快照（`metadata["step"] == -1`）在比较「实际 super-step 快照」时
> MUST **排除**（B14F1 已记录；**不占 X 编号**）。
> ⚠️ **比较投影**：`StateSnapshot.metadata` 的内容是 freegraph 内部调度账本（`next` / `interrupts` /
> `tasks` / `scheduler` / `suspension_kind` / `static_ack`），与上游 `{source, step, parents}` 不同
> ⇒ 差分**MUST NOT** 逐字比较 `metadata`；`created_at` 只比 ISO 形态；`config` / `parent_config`
> 的载体差异归 **X-03**。可逐字比较的字段 = `values` / `next`（fan-out 轮除外）/ `tasks`（语义）/
> `interrupts`。
> ⚠️ **fan-out 轮**：freegraph v1 的 fan-out 现场 `snapshot.next` 可能为 `()`（调度账本 pending）
> 或 `节点名:TaskId`（挂起现场），而上游为重复目标名 ⇒ fan-out 轮的差分只比较 `tasks`，
> **不比较** `next` 字面值。

| # | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 |
|---|---|---|---|
| D-01 | `get_state` 取最新 | `values` / `next`（非 fan-out）/ `tasks`（next-tasks 语义）/ `interrupts` 与上游一致；`metadata` / `created_at` / `config` 按上方投影排除 | SAME |
| D-02 | `get_state` 按 `checkpoint_id` | 指定 id 的快照 `values` / `next` 一致；不存在 ⇒ 下游 `None` / 上游空快照 | DIFF（X-01） |
| D-03 | `get_state_history` 数量 / 顺序 | 排除上游 `__start__` 后，快照序列倒序；`values` / `tasks` / `interrupts` 逐条一致（`metadata` / `created_at` / `config` 按投影排除） | SAME |
| D-04 | `get_state_history` 的 `filter` / `before` / `limit` | 集合 / 顺序 / 长度与上游同款；`filter` key 校验同款；`limit <= 0` / `list(None)` 线程顺序按 B14F1 | SAME（带 B14F1 冻结差异） |
| D-05 | 静态挂起的历史表示 | `interrupts == ()`；`suspension_kind` / `static_ack` 原样；`next` 可为空 | SAME |
| D-06 | 动态中断的 `get_state.interrupts` / `tasks` | `interrupts` 与结果 `__interrupt__` 元组逐项一致；`tasks` 为 next-tasks 且带对应 `interrupts`；顺序 = 标准节点名序 / fan-out TaskId 序 | SAME（顺序确定性差异**继承 B12F1 X-7**：上游集合弹出为竞态 · 本 feature 不重复登记；P-08 同款） |
| D-07 | 真异常 + 中断同现 | `get_state.interrupts` 含 pending `__interrupt__`；`tasks` 从 round-start 快照的 `next` / `fanout` 重建；异常 identity / 类型 / 消息不变 | SAME |
| D-08 | `context` 不持久化 | 快照 / metadata / scheduler / pending writes 中 `context` 出现次数 == 0 | DIFF（X-07） |
| D-09 | 无 checkpointer 读取 | 两侧均 `ValueError`（消息含 `No checkpointer set`） | SAME |
| D-10 | 缺失 `thread_id` 读取 | freegraph `ValueError`；上游实测 `ValueError` / `KeyError`（差异化） | STRICTER（X-08） |
| D-11 | `checkpoints` 事件 | freegraph：四键信封 + `StateSnapshot`（`tasks` / `interrupts` 为 next-tasks 投影）；上游：dict payload + 不同信封 | DIFF（X-04） |
| D-12 | `delete_thread` | 删除后两侧均不可见；其它线程不变 | SAME |
| D-13 | `SqliteSaver` ↔ `MemorySaver` 双后端 | 同操作序列的 `.snapshot` / `.pending_writes` / `.scheduler` 逐字段一致（`created_at` 只比格式） | SAME（freegraph 双后端对跑） |
| D-14 | 跨实例持久化 | 新实例 / 新子进程取回旧快照逐字段一致（**freegraph-only 部分始终运行**；是否附上游对照不影响本项） | SAME（freegraph-only；上游对照缺失只跳过对照，不跳过本项） |
| D-15 | 并发写 | **同实例**多线程：无损坏、无半事务、无 `database is locked` 泄漏；Linux / Windows 均通过；跨进程只要求不损坏（**freegraph 部分始终运行**；source-aligned 对照不可导入时只跳过对照） | SAME（上游单连接 + 锁 + WAL 口径） |
| D-16 | 不可序列化载荷 | `SqliteSaver` ⇒ `TypeError`；`MemorySaver` 可存（深拷贝） | DIFF（X-05 · 序列化） |
| D-17 | `get_state` 无 `checkpoint_id` + pending writes | 两侧都把 pending writes 按 C6 合并进 `values`（JSON 原生载荷） | SAME |
| D-18 | `get_state` 带 `checkpoint_id` + pending writes | 两侧都**不**合并 `values`；`tasks` 仍按 next-tasks 重建、`interrupts` 从 pending 投影 | SAME |
| D-19 | `from_conn_string` / `:memory:` / WAL / 建表 | 两侧都支持 `from_conn_string(":memory:")`；首次操作建表并启用 WAL | SAME（source-aligned；不可导入 ⇒ `SKIP`） |
| D-20 | `filter` 非法 key | 两侧均 `ValueError`（`^[a-zA-Z0-9_.-]+$`） | SAME |
| D-21 | next-tasks 重建 | `get_state` / 历史都含每个 `next` 目标 / fan-out 任务的 `PregelTask`（`id` / `name` / `path` / `interrupts`）；收敛快照 `tasks=()`；静态挂起 `tasks` 为 next-tasks 且 `interrupts=()`；pending 中断附着到对应任务；`interrupts` 与 `flatten(task.interrupts)` 同序 | SAME（`id` / `path` 为 freegraph 口径；fan-out 轮不比较 `next`） |

### 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 状态 | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|---|
| **X-01** | **有效** | 破已冻结契约面（L1 `CompiledGraph`） | P-02：`get_state` 无快照返回 `None`（上游返回空 `StateSnapshot`） | L1 协议已冻结「查不到返回空值，MUST NOT 抛异常」；本 feature **只执行** | B2F1（上游已冻结）· 本 feature |
| **X-02** | **已撤销**（2026-11-22 clarify） | 原「必须自研区 / 分层约束」 | 原 P-03：`get_state` 的 `values` 不合并 pending writes | **改为上游同款**：无 `checkpoint_id` ⇒ 合并；有 id ⇒ 不合并；编号保留不复用 | 本 feature · 已按上游对齐 |
| **X-03** | **有效** | 自研区 / 已锁定形态 | P-09：`config` 为 `RunConfig \| Mapping \| None`（上游仅 `RunnableConfig`） | B7F3 CF-05 已冻结双形态边界；本 feature 只放宽注解 | **B7F3**（已冻结）· 本 feature |
| **X-04** | **有效** | 自研区 ③（诊断事件形态） | P-10：`checkpoints` 事件 = 四键信封 + `StateSnapshot`（上游 dict payload / 不同信封） | B8F2 的四键信封（X-1）与 L1 快照载体已冻结；本 feature 只接线 | **B8F2**（信封）· 本 feature |
| **X-05** | **有效** | 自研区 ③（零依赖持久化） | P-11：标准库 `sqlite3` + `json`（上游 serde / msgpack） | 零第三方依赖是红线；序列化实现面 DIFF，行为面仍「纯数据」 | 本 feature |
| **X-06** | **已撤销**（2026-11-22 clarify） | 原「自研区 ③ / 跨平台并发」 | 原 P-12：per-instance 锁 + 短连接 + 有界重试 | **改为上游同款**：单连接 + 每实例锁 + `check_same_thread=False` + WAL；编号保留不复用 | 本 feature · 已按上游对齐 |
| **X-07** | **有效** | 破已冻结契约面（B8F3 的 D-1 / D-3） | P-18：`context` 不持久化 / 不从快照还原 | B8F3 已拍板 `context` 是运行期上下文；本 feature 只执行 | **B8F3**（已冻结）· 本 feature |
| **X-08** | **有效** | 更明确的失败信号 | D-10：缺失 `thread_id` ⇒ `ValueError`（上游实测 `ValueError` / `KeyError`） | 与 B14F1 的 X-03 同源：显式失败优于共享会话 | 本 feature · B14F1 知情 |

> **当前有效偏离 = 6 条**（X-01 / X-03 / X-04 / X-05 / X-07 / X-08）；
> **X-02 / X-06 已按 clarify 轮的上游对齐决议撤销**，编号保留不复用（宪法原则 VIII）。
> **X-04 仅指 `checkpoints` 事件载荷形态**；上游额外 `__start__` 快照的差分排除是 B14F1
> 已记录的测试口径，**不是偏离**、不占 X 编号。
> 另：P-20 / P-21 / P-22 的 B14F1 冻结差异（`task_path` 排序 / id 来源 / `list(None)` 线程顺序）
> 属**跨 feature 已冻结契约**，不在本 feature 新增偏离；P-19 的 schema 属内部实现细节。
> **X 表交叉引用**：P-20 / P-21 / P-22 的 DIFF 以本脚注为准（继承自 B14F1），
> MUST NOT 被读成「未登记的 new deviation」。
> **X-08 的对照行** = 上游对照 **P-25**（缺失 `thread_id` 的读取信号）+ 差分场景 **D-10**
> （缺失 `thread_id`；上游实测 `ValueError` / `KeyError`）——P-25 与 X-08 的关系标注逐字为
> **STRICTER**（原则 XI v1.12.0）；**P-17**（配置级 checkpointer / 子图）为**能力边界**
> （C26 属 v2），不是偏离、不占 X 编号。

### 破冻结面的回溯修订清单 *(必须有)*

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 / 处置 | 需发起者追认? |
|---|---|---|---|---|
| **L1 `CompiledGraph.get_state` / `get_state_history` 的 `config` 注解**（B2F1 · 当前 `RunConfig`） | `src/freegraph/contracts/protocols.py:288-290` · `specs/b2f1-contracts-protocols/spec.md` 的协议签名表 | **拆分而不删**：保留「历史注解」注记；新增放宽后的 `RunConfig \| Mapping[str, Any] \| None`；返回类别**不变** | 本 feature 落地时登记；追认文字落 `harness/verification/B15F1/manual-verification.md`（**D-5 · 每 feature 追认 ≤ 1 次**） | **是**（并入唯一一次追认 · R-3） |
| **`CompiledGraph` 的 `get_state` / `get_state_history` 仍抛 `NotImplementedError`（点名 B15F1）** | `src/freegraph/_stategraph.py:866-872` · `tests/runtime/test_conditional_edge_surface.py:102-103` · `tests/facade/test_compiled_graph.py:76-77` · `tests/facade/test_facade.py:231-232` | **拆分而不删**：保留「B15F1 之前未实现」的历史注记；改为真实实现 + 新增行为断言 | 本 feature 交付物 | **否**（宪法 v1.11.0 基线的冻结断言拆分，不占 v1.9.0 追认额度 · R-1） |
| **B8F2 的 `checkpoints` 档「v1 恒空」**（`specs/b8f2-stream-modes/spec.md` 的 D-2 / D-5 / 裁定 5 / FR-017 / SC-008） | `specs/b8f2-stream-modes/spec.md` 的下游承接状态 | **拆分而不删**：保留「B14F1 之前恒空」的历史；新增「B15F1 起：有 saver + `thread_id` 时按本次运行产出」；**非 `checkpoints` 六档语义零改动** | 本 feature 登记 | **否**（仅登记 · B8F2 既有下游承接 D-2 / D-5） |
| **B8F2 的 FR-028「`StreamSession` MUST 忽略 `checkpointer`（不读/写快照）· `checkpointer` 存在 MUST NOT 改变**非 `checkpoints` 六档**语义」**（B14F1 **H-8** 的「`StreamSession` 在 v1 忽略 `checkpointer`」同源） | `specs/b8f2-stream-modes/spec.md`（FR-028）· `specs/b14f1-checkpointer-memory-saver/spec.md`（H-8） | **拆分而不删**：保留「非 `checkpoints` 六档仍忽略 `checkpointer`、不读/写快照」的历史；新增「`checkpoints` 档 carve-out：有 saver + `thread_id` 时由本 feature 的 `StreamCheckpointWriter` 写盘并产事件」；**MUST NOT** 让 `checkpointer` 改变其它六档语义 | 本 feature 登记（与上行「v1 恒空」同一处置） | **否**（仅登记 · B8F2 既有 carve-out · R-4） |
| **B14F1 的 `StateSnapshot.tasks` 语义（「每轮完成态」+「挂起快照 tasks 恒为 `()`」）作为读取权威** | `specs/b14f1-checkpointer-memory-saver/spec.md` 的裁定 5 / FR-019 / 写侧表 · `specs/b8f2-stream-modes/spec.md` 的 `tasks` 档说明 | **拆分而不删**：保留 B14F1 的存储口径（供 `stream(tasks)` 完成态事件 / 历史数据源）；新增「自 B15F1 起：`CompiledGraph.get_state` / `get_state_history` / `stream(checkpoints)` 的 `tasks` MUST 由读取层按上游 next-tasks 语义重建，**MUST NOT** 直接使用存储的 `snapshot.tasks`」；B8F2 的 `stream(tasks)` 仍为完成态，语义边界写死 | **并入本 feature 唯一一次追认**（与 R-3 同一次；2026-11-23 · 原则 XII） | **是**（与 R-3 同一次 · R-13） |
| **B14F1 的 Out of Scope「`stream(checkpoints)` 消费端归 B15F1」** | `specs/b14f1-checkpointer-memory-saver/spec.md` · `plan.md` 的边界表 | **拆分而不删**：保留历史边界；在本 feature 关闭 D-02 | 本 feature 交付物 | **否**（交付物） |
| **`freegraph.persistence.__all__` 的精确集合断言**（B14F1 交付） | `tests/contracts/test_b14f1_contracts.py` 的符号集合 | **只增不改**：新增 `SqliteSaver`；既有 `MemorySaver` / `InMemorySaver` / `CheckpointTuple` 逐字保留 | 本 feature 交付物 | **否**（只增 · R-2） |

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：系统 MUST 提供 `freegraph.persistence.SqliteSaver`，并**结构化满足** L1 的
  `Checkpointer` 协议**全部八个**方法（`get_tuple` / `list` / `put` / `put_writes` /
  `delete_thread` / `delete_for_runs` / `copy_thread` / `get_next_version`）。
- **FR-002**：`SqliteSaver` MUST 只用**标准库 `sqlite3` + `json` + 标准库模块**；
  MUST NOT 引入第三方依赖；MUST NOT import `langchain` / `langchain-core` / `langgraph*` /
  `langsmith`；MUST NOT 读环境变量；MUST NOT 有任何出站；
  `src/freegraph/persistence/**` MUST 只**依赖** **L1 + 标准库**（L4 只依赖 L1 · ARCH-1）；
  **同层内部模块 import**（如 `._types` / `._json`）按层注册表允许，不构成跨层依赖。
- **FR-003**：`SqliteSaver` 的构造形态 MUST 与上游同款：
  `SqliteSaver(conn: sqlite3.Connection, *, on_checkpoint=None)` 与
  `SqliteSaver.from_conn_string(conn_string: str, *, on_checkpoint=None)`（上下文管理器）；
  `from_conn_string` MUST 用 `sqlite3.connect(conn_string, check_same_thread=False)` 打开，
  退出时关闭；MUST 支持 `:memory:`；MUST NOT 暴露 `serde` 参数；MUST NOT 提供默认路径。
- **FR-004**：`SqliteSaver` MUST 在首次操作时执行 `setup()`：`PRAGMA journal_mode=WAL` +
  `CREATE TABLE IF NOT EXISTS checkpoints / writes`（镜像上游）；
  `checkpoint_ns` 在 v1 恒为 `""`；表结构 / 列名 / SQL / 索引是**内部实现细节**；
  MUST NOT 要求「读取不创建文件 / 表」（上游 `from_conn_string` 打开 / 创建文件，
  `setup()` 首次操作建表）；MUST NOT 额外收紧 POSIX 文件权限（沿用 OS 默认 / umask）。
- **FR-005**：持久化载荷 MUST 为**纯数据**并用标准库 `json` 编码；不可 JSON 序列化 ⇒
  `TypeError` 且该次调用**零写入**；MUST NOT 使用 `pickle` / msgpack / 第三方 serde（X-05）。
- **FR-006**：`get_tuple(config)` MUST 返回 `CheckpointTuple | None`，恰好三个公开字段
  `.snapshot`（L1 `StateSnapshot`）· `.pending_writes`（`(task_id, channel, value)` 三元组序列）·
  `.scheduler`（纯数据字典）；`configurable["checkpoint_id"]` 有值 ⇒ 取指定快照
  （不存在 ⇒ `None`）；否则取该线程最新快照。
- **FR-007**：写侧关键字 MUST 逐字为
  `put(config, *, values=..., metadata=...)` 与
  `put_writes(config, *, writes=..., task_id=..., task_path=...)`；`put` MUST 返回带新
  `checkpoint_id` 的 `RunConfig`；`put_writes` 目标 MUST 由
  `configurable["checkpoint_id"]` 指定（缺 key ⇒ `KeyError`；指定 id 不存在 ⇒ `ValueError`）。
- **FR-008**：pending writes 的去重 / 覆盖 / 排序 MUST 逐字复用 B14F1：
  去重键 `(task_id, WRITES_IDX_MAP.get(channel, idx))`；普通通道跨调用同 `(task_id, idx)`
  **首次生效**；保留通道（`__error__` / `__scheduled__` / `__interrupt__` / `__resume__`）
  **最后一次生效**（同一次调用内也覆盖）；`.pending_writes` 按 `(task_path, task_id, idx)` 升序。
- **FR-009**：`SqliteSaver` MUST 复用 B14F1 的 checkpoint 顺位 id 空间：每线程 `f"{n:032d}"`
  单调递增；重启 / 新实例后下一个 id = 已存最大 id + 1；`parent_config` 指向上一快照；
  MUST NOT 另立第二套 id 空间。
- **FR-010**：`delete_thread(thread_id)` MUST 删除该会话的**全部**快照与 pending writes，
  幂等、不影响其它线程；`thread_id` 非 `str` ⇒ `TypeError`；删除后同 id 重建从 checkpoint id
  `1` 开始。`delete_for_runs` / `copy_thread` MUST 作为方法存在；v1 MUST 抛
  `NotImplementedError`（与 B14F1 / 上游 base 一致）；MUST NOT 回改 `MemorySaver` 行为。
- **FR-011**：`SqliteSaver` MUST 采用上游的并发模型：**单连接** + 每实例一把
  `threading.Lock` + `check_same_thread=False`（`from_conn_string` 自动设置；`SqliteSaver(conn)`
  由调用方负责）；同实例多线程的 `put` / `get_tuple` / `list` / `delete_thread` MUST 串行化、
  MUST NOT 串扰；同一线程的并发 `put` MUST 产生唯一且严格递增的 checkpoint id
  （事务内 `MAX+1`；**不额外重试**）。
  跨实例 / 跨进程只依赖 SQLite 文件锁 + WAL，**MUST NOT** 承诺严格跨进程同线程串行
  （上游同款；`database is locked` 原样传播）。
- **FR-012**：持久化失败（磁盘满 / 权限不足 / 文件损坏 / `database is locked`）MUST
  以底层 `sqlite3.Error` 子类**原样传播**；MUST NOT 吞掉 / 包装；单次 `put` / `put_writes`
  失败 MUST 原子回滚（零残留）；MUST NOT 删除 / 重建 / 迁移用户数据库；
  `from_conn_string` 退出后的调用 MUST 传播 `sqlite3.ProgrammingError`（连接已关闭）。
- **FR-013**：系统 MUST 实现 `CompiledGraph.get_state(config)`：`config` 接受
  `RunConfig | Mapping[str, Any] | None`（`None` 仅在类型层接受，解析后缺 `thread_id` ⇒
  `ValueError`）；MUST NOT 接受裸 `thread_id: str`；返回
  `StateSnapshot | None`；无快照 ⇒ `None`；MUST NOT 抛异常表示「查不到」。
- **FR-014**：`get_state` / `get_state_history` 在 `checkpointer` 为 `None` / `True` / `False` 时
  MUST 抛 `ValueError`（消息含 `No checkpointer set`）；生效 `thread_id` 缺失 / 空串时 MUST 抛
  `ValueError`（点名 `thread_id`）；`configurable["checkpoint_ns"]` 非空 ⇒ `ValueError`
  （v1 无子图 · 明确失败；空串 / 缺失视为 `""`）。
- **FR-015**：`get_state` 在**未指定** `configurable["checkpoint_id"]`（**含 `None` / 空串**）时
  MUST 把 pending writes 中**非保留通道且 `task_id ∈ snapshot.next`** 的写入按运行期同款通道
  归约（C6）合并进 `values` 的**副本**（上游 `apply_pending_writes=True` 同款 ·
  `:1239-1248` 的 `if tid not in next_tasks: continue`）；**指定非空** `checkpoint_id` 时 MUST
  直接使用 `snapshot.values`（不合并）。`next` / `config` / `metadata` / `created_at` /
  `parent_config` MUST 原样取自 `get_tuple().snapshot`；`tasks` MUST 按 **FR-037 / 裁定 13**
  以**上游 next-tasks 语义**从 `snapshot.next` + `.scheduler["fanout"]` + pending
  `__interrupt__` 重建（**MUST NOT** 使用 / 合并 `snapshot.tasks`）；`config` 只含 `thread_id` +
  `configurable["checkpoint_id"]`；`config.context` MUST 为 `None`；合并 MUST NOT 修改存储。
- **FR-016**：系统 MUST 实现
  `CompiledGraph.get_state_history(config, *, filter: Mapping[str, Any] | None = None, before: RunConfig | Mapping[str, Any] | None = None, limit: int | None = None) -> Iterator[StateSnapshot]`；
  `config` 载体同 FR-013（`None` 仅在类型层接受，解析后缺 `thread_id` ⇒ `ValueError`）；
  返回**迭代器**；无快照 ⇒ 空迭代器。**类型校验**：
  `filter` 非 `Mapping` / `None`、`before` 非 `RunConfig` / `Mapping` / `None`、
  `limit` 非 `int` / `None`（**`bool` 拒绝**）⇒ `TypeError`。L1 `CompiledGraph` Protocol
  的 `get_state_history` **保持 `config` 单参数**；三个关键字是 L3 实现体的 keyword-only 扩展
  （R-3 · SC-023）。
- **FR-017**：`get_state_history` MUST 按 `checkpoint_id` **倒序**（最新在前）；
  无过滤时长度 == 该 `thread_id` 成功 `put` 次数；`values` MUST 直接取自
  `snapshot.values`（**不**合并 pending writes）；当后端为 `SqliteSaver` 时，`filter` /
  `before` / `limit` MUST 复用其 `search_where` / `_metadata_predicate` 语义（含上游 key
  校验与 JSON 提取）；当后端为 `MemorySaver` 时，`filter` 保持 B14F1 的**顶层 key 精确匹配**
  （跨后端已知差异，**不改** `MemorySaver`）；`limit <= 0` ⇒ 空；
  实现 MUST 在返回前急切消费底层查询结果。
- **FR-018**：`get_state()` 与 `get_state_history()` 的 `StateSnapshot.interrupts` MUST 等于
  next-tasks 上的待审批中断：按 **FR-037 / 裁定 13** 的任务顺序**展平** `task.interrupts`
  （来自 `.pending_writes` 的 `__interrupt__`，最新留痕）；无任何任务中断时回退到
  `.snapshot.interrupts`；顺序 MUST 为**标准任务按节点名序 · 含 fan-out 的轮按 TaskId 序**；
  `get_state()` 的结果 MUST 与 `invoke` 结果的 `__interrupt__` 元组**逐项一致**；MUST NOT
  另造形态。
- **FR-019**：历史快照 MUST 原样表示静态挂起：`interrupts == ()` 合法；
  `suspension_kind` / `static_ack` 为静态值时原样保留；`next` **允许为空**；
  MUST NOT 要求「`next` 非空 ⇒ 必有中断」。
- **FR-020**：系统 MUST 接受标准任务 `task_id` = 节点名、fan-out `task_id` =
  `f"{节点名}:{TaskId}"`；`.pending_writes` MUST 能区分同一节点在一轮内的 N 个任务；
  MUST NOT 假设「一轮一个节点一个任务」。
- **FR-021**：`SqliteSaver` / `get_state` / `get_state_history` MUST NOT 读取 / 保存 / 还原 /
  透出 `context`；`snapshot.config.context` MUST 为 `None`；`metadata` / `.scheduler` /
  pending writes MUST NOT 出现 `context`；MUST NOT 回退到 `configurable` 承载 `context`；
  MUST NOT 重新引入节点别名。
- **FR-022**：`stream(..., stream_mode="checkpoints")` MUST 在挂真实 saver 且 `thread_id` 非空时，
  为本次运行期间**每次成功 `put`** 产出恰好一条事件；`payload` MUST 是 `StateSnapshot`
  （与 `get_state()` **同形**：8 字段同构；`values` 为存储快照值，不保证等于 pending 合并结果；
  `tasks` / `interrupts` MUST 按**裁定 13 的 next-tasks 算法**投影，与 `get_state()` 对该 id 的
  结果一致，**不使用**存储的完成态 `snapshot.tasks`）；
  信封 MUST 沿用 B8F2 的四键形态；无 saver / 无 `thread_id` ⇒ 0 条事件且不抛；
  **只有 `checkpoints` mode 写 saver；其它六档保持 B8F2 v1 的「忽略 checkpointer」语义**；
  **stream 不恢复历史**，只追加本次运行的新快照；数据源 = `on_checkpoint` / `list()` **或**
  对 `put` 返回 config 的 `get_tuple(written)` 等价读回；允许 L2 私有 writer 复用 B14F1
  写盘助手；MUST NOT 伪造历史事件或另立事件路径。
- **FR-023**：L1 `CompiledGraph.get_state` / `get_state_history` 的 `config` 注解 MUST 放宽为
  `RunConfig | Mapping[str, Any] | None`；MUST 走「登记 + 回溯修订 + 发起者追认」；
  MUST 复用 B7F3 的 CF-05 载体边界；MUST NOT 在门面层把普通映射翻译成 `RunConfig`。
- **FR-024**：本 feature MUST NOT 改变图执行语义：挂 / 不挂 `SqliteSaver`、
  有无 `thread_id` 的**单次执行**（节点执行序列、最终状态、错误信号）MUST 一致
  （不含显式恢复路径）。
- **FR-025**：`freegraph.persistence.__all__` MUST 增加 `SqliteSaver`；
  `from freegraph.persistence import SqliteSaver` MUST 成功；`freegraph.graph` 门面
  MUST NOT 转出 `SqliteSaver`（G18）。
- **FR-026**：系统 MUST 在 `tests/differential/` 落本 spec 的 D-01…D-21；上游 SQLite 后端
  源码可用但未安装 ⇒ 运行时不可导入时 **skip**（不是 fail）；`get_state` / `get_state_history`
  的上游对照可用 `MemorySaver` 完成；SQLite 连接 / 并发 / WAL 的源码对齐项可在不可导入时
  标 `SKIP (source-aligned)`。
- **FR-027**：并发写用例 MUST **跨平台**：不得标记 `linux_only`；MUST 在现有
  `windows-2025` CI 矩阵（`.github/workflows/ci.yml:49-50`）上运行并通过；
  用例 MUST 断言无 `database is locked` 泄漏。
- **FR-028**：跨进程持久化用例 MUST 存在：用新的 Python 子进程读取同一数据库文件并回传快照，
  父进程断言逐字段一致（P1 / SC-003）。
- **FR-029**：`harness/verification/B15F1/manual-verification.md` MUST 存在，含
  「环境 / 步骤 / 实际输出 / 结论 / 遗留问题」五段；实际输出 MUST 含**非空**的
  持久化往返实测（写入 → 新实例 / 新进程取回）与并发写实测结论；Windows 证据由 CI 记录；
  MUST 含本 feature **唯一一次追认文字**（R-3 `config` 注解放宽 + R-13 B14F1 `tasks` 回溯）；
  **质量门禁 5 合规**：本 feature MUST 跑 **fake 轮 + 真实模型轮** 两轮；真实模型轮使用
  `harness/demo/target.py` 或等价固定脚本，记录模型端点、调用次数与零出站归因；
  B25F1 只做跨 feature 复验，**不是**本 feature 的替代。
- **FR-030**：`created_at` MUST 用标准库 UTC 时钟生成并序列化为 ISO-8601 字符串；
  `metadata` / `created_at` 的可空性与 L1 `StateSnapshot` 一致。
- **FR-031**：`list(config=None, *, filter=None, before=None, limit=None)` MUST 支持：
  `config=None` 全线程（线程按**首次写入顺序** · B14F1）；同线程 id **降序**；
  `filter` 采用上游 `search_where` / `_metadata_predicate` 的 key 校验
  （`^[a-zA-Z0-9_.-]+$`，非法 ⇒ `ValueError`）与 `json_extract` 比较；
  `filter` 非 `Mapping` / `before` 非 `RunConfig` / `Mapping` / `None` ⇒ `TypeError`；
  `before` 排除 `id >= before_id`；**`limit` 为全局上限（`config=None` 时跨线程累计）**；
  `limit <= 0` ⇒ 空；返回迭代器。
- **FR-032**：`get_tuple` / `list` 返回的快照 / 写入 / 调度账本 MUST 是**独立副本**；
  调用方修改返回值 MUST NOT 影响存储或后续读取。
- **FR-033**：`SqliteSaver.from_conn_string` MUST 是上下文管理器：进入时打开连接、退出时关闭
  （上游 `closing` 同款）；`SqliteSaver(conn)` MUST NOT 关闭调用方的连接；MUST NOT 提供额外的
  `close()`；MUST NOT 提供额外的连接访问器（如 `get_conn()`）；`conn` 属性沿用上游同名持有面。
- **FR-034**：`conn_string` MUST 按传入值交给 `sqlite3.connect`；MUST NOT `expanduser` /
  `expandvars` / 读环境变量 / 联网解析。
- **FR-035**：`on_checkpoint` MUST 在每次成功 `put` 后恰调用一次；回调 MUST 在锁外执行；
  回调异常 MUST 被吞掉且 MUST NOT 回滚已提交快照。
- **FR-036**：本 feature MUST NOT 新增 L1 异常类型 / 改变 L1 的 `StateSnapshot` /
  `RunConfig` / `Interrupt` / `PregelTask` / `Checkpointer` 的字段面；
  唯一的 L1 改动是 FR-023 的 `config` 注解放宽（已登记）。
- **FR-037**：`get_state()` / `get_state_history()` / `stream(checkpoints)` 的 `tasks` MUST 按
  上游 **next-tasks** 语义重建：数据源 = `snapshot.next` + `.scheduler["fanout"]` + pending
  `__interrupt__`；**两类来源 `id` 域不同、互斥**：标准任务 `id = 节点名`、`next` 中已含 `:`
  的 fan-out 任务 `id = next_node`（**= 运行时 `task_key`**，`f"{节点名}:{全局TaskId}"`），
  `fanout` 账本来源的未执行任务 `id = f"{节点名}:{本地index}"`（**本地枚举 id · 非运行时
  `task_key`**）；`name` = 节点名（fan-out 取冒号前）；`path` = `(节点名,)`（标准）/
  `(节点名, TaskId)`（fan-out：`next` 来源取运行时全局 `TaskId`、账本来源取本地 `index`）；
  **`next`/pending 来源任务的 `id` MUST 与 `.pending_writes` 的 `task_id` 同款**；`fanout` 账本来源
  任务 `interrupts` 恒 `()` 且 **MUST NOT** 跨源按 `id` 合并 / 去重（同一 checkpoint 内唯一；
  生成方式不冻结）；`interrupts` = 同 `id` 的 pending `__interrupt__` 载荷元组（无则 `()`）；
  `error` / `state` / `result` = `None`；顺序 = 标准任务节点名序 · fan-out TaskId 序；
  `next` 为空且无 fan-out ⇒ `tasks = ()`；**MUST NOT** 使用 / 合并 B14F1 存储的
  `snapshot.tasks`；MUST NOT 给 `Interrupt` 增加节点名字段（B10F1 **F-3**）。

### Key Entities

- **`SqliteSaver`**：L4 的磁盘持久化 checkpointer；标准库 `sqlite3`；8 方法协议；
  上游同款 `SqliteSaver(conn)` / `from_conn_string(...)`；单连接 + 锁 + WAL；
  文件或 `:memory:`；schema / SQL / 序列化实现为内部细节。
- **`CompiledGraph.get_state` / `get_state_history`**：对外状态读取面；返回 L1
  `StateSnapshot`；调用形态锁定为 `config` 载体。
- **`StateSnapshot`**：L1 冻结的 8 字段快照（`values` / `next` / `config` / `metadata` /
  `created_at` / `parent_config` / `tasks` / `interrupts`）；`interrupts` 的元素是 `Interrupt`。
- **`CheckpointTuple`**：B14F1 冻结的读侧载体（`.snapshot` / `.pending_writes` / `.scheduler`）。
- **`RunConfig.thread_id`**：会话标识；`configurable["thread_id"]` 优先于顶层字段。

### 需求 ↔ 成功标准追溯表

| FR | 判定它的 SC | 判据 | 承接 |
|---|---|---|---|
| FR-001 | SC-006 | 协议 8 方法 | A1 / A2 |
| FR-002 | SC-005 | 零依赖 / 零 env / 零出站 | — |
| FR-003 | SC-015 / SC-022 | 构造形态 / 上游入口 | A3 |
| FR-004 | SC-003 / SC-022 | setup / WAL / 建表 | A3 |
| FR-005 | SC-007 / SC-013 | JSON 纯数据 / 原子性 | — |
| FR-006 | SC-007 | 读侧三字段 | A2 |
| FR-007 | SC-007 | 写侧五关键字 | A2 |
| FR-008 | SC-007 / SC-010 | 去重 / 排序 / fan-out | A2 |
| FR-009 | SC-001 / SC-007 / SC-012 | id 空间 / 父链 / 删除重建 | A1 |
| FR-010 | SC-006 / SC-012 | `delete_thread` / `NotImplementedError` 边界 | A3 |
| FR-011 | SC-004 | 并发 / Windows | A4 |
| FR-012 | SC-013 | 失败传播 / 原子回滚 | — |
| FR-013 | SC-002 / SC-015 | `get_state` / 双形态 | A2 |
| FR-014 | SC-015 | 无 saver / 缺 `thread_id` | A2 |
| FR-015 | SC-002 / SC-008 / SC-011 / SC-025 | 8 字段 / pending 合并 / 无 context | A2 |
| FR-016 | SC-001 / SC-016 | 历史方法 / 过滤 | A1 |
| FR-017 | SC-001 / SC-016 | 倒序 / 数量 / 过滤 | A1 |
| FR-018 | SC-008 | `interrupts` 投影 / 顺序 | A2 |
| FR-019 | SC-009 | 静态挂起 | A2 |
| FR-020 | SC-010 | fan-out task_id | A2 |
| FR-021 | SC-011 | `context` 不持久化 | — |
| FR-022 | SC-014 | `checkpoints` 事件 | — |
| FR-023 | SC-015 / SC-023 | 注解放宽 / 回溯修订 | — |
| FR-024 | SC-023 | 图执行语义不变 | — |
| FR-025 | SC-021 | 导出面 | — |
| FR-026 | SC-018 | 差分场景 | — |
| FR-027 | SC-004 | Windows 并发 | A4 |
| FR-028 | SC-003 / SC-019 | 跨进程持久化 | A3 |
| FR-029 | SC-020 | 人工验证记录 | — |
| FR-030 | SC-002 | `created_at` / 可空性 | A2 |
| FR-031 | SC-016 / SC-026 | `list` 语义 / filter 校验 | A1 |
| FR-032 | SC-017 | 独立副本 / 双后端 | — |
| FR-033 | SC-006 / SC-022 | from_conn_string 生命周期 | A3 |
| FR-034 | SC-005 / SC-015 | 路径处理 | — |
| FR-035 | SC-024 | 回调隔离 | — |
| FR-036 | SC-023 | L1 冻结面 | — |
| FR-037 | SC-027 | tasks 重建 / 节点名 | A2 |

> **双向覆盖核对**：FR-001…FR-037 全部在表；引用的 SC-001…SC-027 全部已定义；
> 验收判据 A1–A4 均至少挂一条**测试任务**（SC-001 / SC-002 / SC-003 / SC-004）。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：`get_state_history` 的长度（无过滤）== 该线程成功 `put` 次数（差异 == 0）；
  `checkpoint_id` 严格递减（逆序对 == 0）；与 `saver.list` 同参数结果逐条相等（差异 == 0）。
- **SC-002**：`get_state` 返回 `StateSnapshot`；8 字段全部可读且类型正确；
  `next` / `tasks` / `interrupts` 是元组；`tasks` 为**上游 next-tasks 投影**（收敛快照 ⇒ `()`；
  `next` 非空 ⇒ 每个待执行目标一个 `PregelTask`）；`config.configurable["checkpoint_id"]` 非空；
  `config.context is None`。
- **SC-003**：跨实例（同一进程用 `from_conn_string` 新建 saver）与**跨进程**（新 Python 子进程）
  读取同一数据库，快照的 `values` / `next` / `config` / `metadata` / `tasks` / `interrupts`
  逐字段相等（差异 == 0）；`:memory:` 只要求同连接生命周期内可读。
- **SC-004**：现有 `windows-2025` CI 矩阵上的**同实例多线程**并发写用例通过；
  `database is locked` 泄漏次数 == 0；并发后每个线程的快照数 / pending writes 内容正确
  （串扰 == 0）；跨进程只断言不损坏（不承诺无锁异常）。
- **SC-005**：运行时依赖闭包仍为空集（`dependencies == []`）；新增第三方包数 == 0；
  环境变量读取点 == 0；出站调用点 == 0；**G21 / G22 / G23 / G24 / G25 / G26 / G27** 判绿
  （G22 = 隔离环境依赖闭包 + `sys.modules` 无 langchain 家族；若本地无法起隔离 venv，
  MUST 在 manual-verification 记录并由 CI 运行，**MUST NOT** 静默跳过）。
- **SC-006**：`isinstance(SqliteSaver(...), freegraph.contracts.Checkpointer) is True`；
  8 个方法均可调用 / 可断言存在；v1 的 `delete_for_runs` / `copy_thread` 抛
  `NotImplementedError`（比率 == 100%）。
- **SC-007**：读侧三字段 / 写侧五关键字 / `put_writes` 的 `checkpoint_id` 目标 /
  pending writes 去重与排序与 B14F1 **逐项一致**（差异 == 0）；JSON 往返后
  `next` / `tasks` / `interrupts` 仍是 tuple，`Interrupt` / `PregelTask` 仍是对象；
  **pending `__interrupt__` 读回为 `tuple[Interrupt, ...]`（不是 dict）**；
  `values` 中用户 tuple 按 JSON 语义变为 list 属已登记差异（X-05）。
- **SC-008**：`get_state().interrupts` 与 `invoke` 结果 `__interrupt__` 元组**逐项相等**
  （差异 == 0）；`get_state_history` 的 `interrupts` / `tasks` 按同口径投影；顺序为
  「标准任务节点名序 · fan-out TaskId 序」；「真异常 + 中断同现」时能从 pending writes 读到
  并附着到对应 next task（命中率 == 100%）。
- **SC-009**：静态挂起的 `interrupts == ()`、`suspension_kind` / `static_ack` 原样往返
  （差异 == 0）；`next` 为空的静态快照合法；`tasks` 仍为 `next` 的 next-tasks 投影
  （`interrupts` 均为 `()`），**MUST NOT** 退化为 `snapshot.tasks`；误判「无挂起」次数 == 0。
- **SC-010**：`Send` fan-out 的 N 个任务在 pending writes 中有 N 个**唯一** `task_id`
  （形如 `f"{node}:{id}"`）；互相覆盖次数 == 0；标准任务 `task_id` == 节点名。
- **SC-011**：`context` 在快照 / metadata / scheduler / pending writes 中出现次数 == 0；
  `snapshot.config.context is None` 的比率 == 100%；从快照还原 `context` 的次数 == 0。
- **SC-012**：`delete_thread` 后 `get_tuple == None`、`get_state == None`、历史为空；
  其它线程数据逐项不变；重复删除抛异常次数 == 0；重建后 checkpoint id 从 1 开始。
- **SC-013**：磁盘满 / 权限不足 / 文件损坏 / `database is locked` 模拟下，`sqlite3.Error`
  子类原样传播（被吞掉次数 == 0）；单次失败后存储残留 == 0；用户数据库未被删除 / 重建；
  `from_conn_string` 退出后调用 ⇒ `sqlite3.ProgrammingError`（比率 == 100%）。
- **SC-014**：`checkpoints` 事件数 == 本次运行成功 `put` 次数（差异 == 0）；
  每条 `payload` 是 `StateSnapshot`；四键信封齐全；`payload.tasks` / `interrupts` 与
  `get_state()` 对该 id 一致（next-tasks 投影）；无 saver / 无 `thread_id` 时事件数 == 0；
  伪造事件数 == 0。
- **SC-015**：`config` 载体接受率 == 100%（`RunConfig` / 普通映射）；
  裸 `str` / 数字 ⇒ `TypeError` 的比率 == 100%；`None` 在类型层接受但解析后缺 `thread_id`
  ⇒ `ValueError` 的比率 == 100%（**不**计入“成功读取”）；缺失 / 空 `thread_id` ⇒ `ValueError`
  的比率 == 100%；未挂 saver ⇒ `ValueError`（含 `No checkpointer set`）的比率 == 100%。
- **SC-016**：`filter` / `before` / `limit` 组合结果与 `saver.list` 逐项相等（差异 == 0）；
  `limit <= 0` ⇒ 空；未知线程 ⇒ 空；未知 `checkpoint_id` ⇒ `None` / 空。
- **SC-017**：对**仅含 JSON 原生标量 / 容器**的载荷，同一操作序列在 `MemorySaver` 与
  `SqliteSaver` 上的 `.snapshot` / `.pending_writes` / `.scheduler` 逐字段一致
  （`created_at` 只比非空 + ISO 格式；差异 == 0）；非 JSON 原生对象属 X-05 的已知差异，
  **不**计入本判据。
- **SC-018**：差分场景 D-01…D-21 全部落 `tests/differential/`；上游 SQLite 运行时不可导入 ⇒
  skip（不是 fail；可标 `SKIP (source-aligned)`）；上游在场时通过率 == 100%；
  每条上游断言带版本 + `路径:行号`（缺失数 == 0）。
- **SC-019**：跨进程持久化子进程用例退出码 == 0，回传快照与父进程逐字段相等（差异 == 0）。
  > **注**：本项是 **SC-003 的跨进程专项**（判据为 SC-003 的子集）；保留以独立强调「子进程退出码 == 0」。
- **SC-020**：`harness/verification/B15F1/manual-verification.md` 存在；五段齐全；
  含**非空**的持久化往返实测输出与并发写实测结论；含 **fake 轮 + 真实模型轮** 两轮证据
  （真实模型轮含模型端点、调用次数、零出站归因）；含本 feature **唯一一次追认文字**
  （R-3 `config` 注解放宽 + R-13 B14F1 `tasks` 回溯）（文档守卫断言）。
- **SC-021**：`freegraph.persistence.__all__` 含 `SqliteSaver`；
  `from freegraph.persistence import SqliteSaver` 成功；`freegraph.graph` 无 `SqliteSaver`
  （命中数 == 0）。
- **SC-022**：`from_conn_string` 能打开 / 创建数据库文件；首次操作执行 `setup()`（WAL +
  `checkpoints` / `writes` 表）；`:memory:` 可用；不额外收紧 POSIX 文件权限（沿用 OS 默认）。
- **SC-023**：L1 符号面改动 == **2 处注解**（`get_state` / `get_state_history` 的 `config`）；
  新增 L1 异常类型数 == 0；新增门禁编号数 == 0；图执行语义差异 == 0。
- **SC-024**：`SqliteSaver` 的 `on_checkpoint` 回调次数 == 成功 `put` 次数；回调抛错后
  `put` 成功率 == 100%、已提交快照回滚次数 == 0。
- **SC-025**：`get_state` 无 `checkpoint_id` 且存在 pending writes 时，`values` 按 C6 归约合并
  **`task_id ∈ snapshot.next`** 的非保留通道写入（与上游 `if tid not in next_tasks: continue`
  同款；游离 pending 不合并；差异 == 0）；带 `checkpoint_id` 时不合并（差异 == 0）；
  `get_state_history` 的 `values` 不合并（差异 == 0）；合并后存储快照 / 写入零变化（差异 == 0）。
- **SC-026**：`SqliteSaver` 的 `filter` key 非法（不匹配 `^[a-zA-Z0-9_.-]+$`）⇒ `ValueError`
  的比率 == 100%；`SqliteSaver` 的 `filter` 的 `None` / `bool` / `dict` / `list` 值编码与上游
  一致（差异 == 0）。`MemorySaver` 的 `filter` 仍是 B14F1 顶层精确匹配，**不**要求 key 校验
  （跨后端已知差异，**不改** `MemorySaver`）。
- **SC-027**：`get_state().tasks` 与 `get_state_history` 同 id 元素的 `tasks` 均为**上游
  next-tasks 投影**：每个 `next` 目标 / fan-out 任务一个 `PregelTask`，`id` / `name` / `path` /
  `interrupts` 按裁定 13；收敛快照 ⇒ `tasks == ()`；静态挂起 ⇒ `tasks` 为 next-tasks 且
  `interrupts == ()`；重复 `id` 数 == 0；`interrupts` 与 `flatten(task.interrupts)` 逐项相等
  （差异 == 0）；**MUST NOT** 等于 B14F1 存储的「本轮完成态」`snapshot.tasks`；
  `Interrupt` 字段数 == 2（未增节点名）。

### 验收判据（立项书 §5.2 B15F1 小目标 · 逐条可判定）

> 小目标原文：**历史快照可枚举**

| # | 判据 | 判定方式 | 本 spec 的承载 |
|---|---|---|---|
| **A1** | 历史快照可枚举 | `get_state_history` 数量与顺序断言 | **SC-001 / SC-016** · FR-016 / FR-017 |
| **A2** | `get_state` 可用 | 返回 `StateSnapshot` 且字段完整 | **SC-002 / SC-008 / SC-027** · FR-013 / FR-015 / FR-018 / FR-037 |
| **A3** | 磁盘持久化生效 | 跨实例 / 跨进程取回用例 | **SC-003 / SC-019 / SC-022** · FR-004 / FR-028 |
| **A4** | Windows 并发写通过 | 现有 `windows-2025` CI 任务 | **SC-004 / SC-005** · FR-011 / FR-027 |

---

## Assumptions

- **上游取证环境**：本机 `.venv` 已安装 `langgraph 1.2.11`；`get_state` / `get_state_history`
  的锚点于 2026-11-22 核对；上游 SQLite 后端 **`langgraph-checkpoint-sqlite 3.1.1`（MIT）**
  源码在 uv 缓存中，**作为连接 / 并发 / WAL / 构造入口的行为锚点**；该发行包未安装进 `.venv`，
  差分运行时不可导入则 skip。
- **spec 目录命名**：speckit 通用规则为 `NNN-<short-name>`；本仓库既有 feature 全部采用
  `<b<N>f<M>-<slug>`（宪法 v1.4.2 的目录约定）⇒ 本 feature 用
  `specs/b15f1-sqlite-saver-state-history`（**已偏离通用规则 · 已登记**）。
- **分支**：本仓库无 `.specify/extensions.yml` ⇒ 无 `before_specify` 钩子 ⇒ 不创建分支，
  在 `main` 上开发。
- **Python 基线**：3.11+；实现只用标准库（`sqlite3` / `json` / `os` / `pathlib` /
  `datetime` / `threading` / `contextlib` / `collections.abc`）。
- **规模参考**：原始估算 1,240 行（实现 620 / 测试 620）· 3 人日；**2026-11-23 起**因 next-tasks
  重建（含 fan-out / 真异常同现）与 B14F1 回溯修订，实际规模会上调 ⇒ 在 plan **R-9** 与 tasks
  行数预算中如实登记，**MUST NOT** 通过削减判据来压行数。
- **低并发定位**：SQLite 是智能体开发的默认后端；并发目标 = **同实例多线程**（单连接 +
  `threading.Lock` 串行化）+ 少量实例；**不承诺**高并发 / 高吞吐；跨进程写只要求
  「不损坏、不半事务」（上游同款，不额外重试）。
- **后端定位**：`SqliteSaver` 是 freegraph **面向真实使用的默认推荐后端**（零依赖、零配置、
  可跨重启）；`MemorySaver` 定位为**开发 / 调试**（与上游一致：内存 saver 不用于生产）。
- **schema 边界**：数据库表名 / 列名 / SQL / 索引 / 事务参数是**内部实现细节**，
  MUST NOT 成为对外承诺；对外只承诺本 spec 的读侧 / 写侧语义与失败行为。
- **载荷纯数据**：checkpoint 的 `values` / `metadata` 预期为 JSON 可序列化的纯数据
  （C19 约束③）；非 JSON 载荷属用户侧错误（`TypeError`）。`pending __interrupt__` 的
  `Interrupt` 对象按 channel-aware 投影编码，不改变「纯数据」总约束。
- **`tasks` 语义**：自 2026-11-23 起统一为上游 **next-tasks**（下一轮待执行任务）；
  B14F1 存储的「本轮完成态」`snapshot.tasks` 保留为历史 / 流数据源，但**不是**读取 API 的权威。
  `StateSnapshot.metadata` 为 freegraph 内部调度账本投影，不参与上游字面对照。
- **`context`**：B8F3 已接线；本 feature 明确**不**持久化、**不**从快照还原。
- **无 async**：freegraph v1 无 async；`SqliteSaver` 只实现同步方法。
- **`delete_for_runs` / `copy_thread`**：v1 继续抛 `NotImplementedError`；
  运行级删除 / 线程复制属后续版本（重新评估结论见裁定 11）。
- **`stream(checkpoints)`**：B8F2 的七档语义与四键信封不变；本 feature 只把 `checkpoints`
  档从「恒空」改为「有 saver + `thread_id` 时产出本次运行的 checkpoint」。
- **跨进程测试**：用 `subprocess` 启动同解释器读取同一数据库（通过
  `from_conn_string`）；不使用平台特有 IPC；Windows / Linux / macOS 均可运行。
  **跨进程并发写**不在严格承诺内，只断言不损坏。
- **Windows CI**：现有 `.github/workflows/ci.yml` 已含 `windows-2025` × Python 3.11 / 3.14
  两个作业；本 feature 不新增 CI 文件，只新增不带 `linux_only` 标记的测试。
- **文件权限**：沿用 OS 默认 / umask（上游同款）；本 feature **不**额外收紧到 `0o600`；
  Windows 由平台 ACL 解释。
- **差分测试**：上游 `langgraph` 只在测试侧使用；生产依赖声明 MUST 保持 `dependencies = []`。
- **人工验证**：记录 MUST 由执行者如实转录，禁止代签；Windows 证据引用 CI 运行结果。
- **质量门禁 5 合规**：B15F1 MUST 跑 **fake 轮 + 真实模型轮**；真实模型轮使用
  `harness/demo/target.py` 或等价固定脚本，记录模型端点、调用次数与零出站归因；
  B25F1 只做跨 feature 复验（**不替代**本 feature 的真实模型轮）。
- **API 兼容矩阵**：`SqliteSaver` / `get_state` / `get_state_history` 的行由 **B24F1** 纳入；
  本 feature 只提供行为与证据。

---

## 依据

- 立项书 §3.5（支持矩阵 · Windows 文件锁差异）、§5.2（B15F1 行）、§5.3（C19 / C22）、
  §5.4（DF3 `StateSnapshot`）、§5.6（三件套之 ③）、§6.3（关键路径）、§9.1（门禁）。
- 源码参照（**langgraph 1.2.11**）：
  `langgraph/pregel/main.py:1145-1210`（`_prepare_state_snapshot` / `prepare_next_tasks`：
  next-tasks 计算 + pending writes 展平）·
  `:1392-1435`（`get_state`）· `:1480-1530`（`get_state_history`）·
  `:1431`（`apply_pending_writes`）·
  `langgraph/checkpoint/base/__init__.py:262-388`（`get_tuple` / `list` / `put` / `put_writes` /
  `delete_thread` / `delete_for_runs` / `copy_thread`）· `:721-740`（`get_next_version`）·
  `langgraph/types.py:684-701`（`StateSnapshot` 8 字段）·
  `langgraph/_internal/_constants.py:9,11,13,17`（保留通道名）。
- 源码参照（**langgraph-checkpoint-sqlite 3.1.1** · uv 缓存
  `/home/ctyun/.cache/uv/archive-v0/UtTk-BJ9thKpSH0Q/langgraph/checkpoint/sqlite/`）：
  `__init__.py:45-130`（`SqliteSaver` / `__init__` / `from_conn_string`）·
  `:95`（`threading.Lock`）· `:124`（`check_same_thread=False`）·
  `:132-166`（`setup()`：WAL + `checkpoints` / `writes` 表）·
  `:168-189`（`cursor()` 事务）· `:191-380`（`get_tuple` / `list`）·
  `:387-445`（`put` / `put_writes`）· `:484-495`（`delete_thread`）·
  `:626-644`（`get_next_version`）· `utils.py:9-25`（filter key 校验）·
  `utils.py:30-100`（`search_where` / `_metadata_predicate`）。
- 实测证据：E8（`SqliteSaver.from_conn_string(...)` + `get_state_history` ⇒ `HISTORY: 6` ·
  `harness/reports/Q3-LangGraph的开源边界.md:43`）；文档
  `harness/docs/oss/python/langgraph/checkpointers.md:130,170`。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C19 / C22）；B10F1
  `specs/b10f1-interrupt-resume/contracts/checkpoint-contract.md` §2…§6；B14F1
  `specs/b14f1-checkpointer-memory-saver/spec.md` 的裁定 3 / 4 / 5 / 6 / 11 / 12 与
  D-01 / D-02 / D-08；B12F1 的 D-7；B13F1 的 D-6；B11F1 的 D-8；B8F3 的 D-1 / D-3；
  B7F3 的 CF-05。
- 层与门禁：`specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`（L4 = `persistence`）·
  `harness/prompts/guide.md` §2.3 / §3.5（L4 只依赖 L1 · 持久化层不得 import 可观测层）。
- CI：`.github/workflows/ci.yml:49-50`（`windows-2025` × 3.11 / 3.14）。

---

## 下游承接（本 feature → 下游 · 只接线 · 逐条最小改动）

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 |
|---|---|---|---|---|
| **D-01** | **B16F1** | **M3** | `update_state` / 时间旅行 MUST 以本 feature 的 checkpoint 顺位 id 与父链为定位依据；MUST NOT 另造 id 空间；新快照 MUST 通过同一 `put` 渠道追加，`get_state_history` 继续可枚举且倒序。 | FR-007 / FR-009 / FR-017 · 裁定 4 / 9 |
| **D-02** | **B16F1** | **M3** | `update_state` / 分叉 MUST 不破坏原历史快照；`get_state` / `get_state_history` 的组装口径（含 `interrupts` 投影；`get_state` 无 id 时合并 pending、历史不合并）MUST 保持一致；MUST NOT 另写第二套快照组装路径。 | FR-015 / FR-018 · 裁定 8 |
| **D-03** | **B16F1** | **M3** | 从历史静态快照恢复 MUST NOT 要求动态中断载荷；`interrupts == ()` + `suspension_kind` / `static_ack` 的历史快照 MUST 可直接作为重放起点。 | FR-019 · 裁定 9 |
| **D-04** | **B24F1** | **M4** | API 兼容矩阵 MUST 增加 `freegraph.persistence.SqliteSaver`、`CompiledGraph.get_state`、`CompiledGraph.get_state_history` 三行（行为等价 / 部分等价 / 不支持逐项标注）；`manual-verification.md` MUST 纳入发布前人工验收。 | FR-001 / FR-013 / FR-016 / FR-025 / FR-029 |
| **D-05** | **B25F1** | **M4** | 双跑验收脚本 MUST 覆盖 `SqliteSaver` 的持久化往返、历史枚举、`get_state` 中断投影与 `checkpoints` 事件；**并对 B15F1 的真实模型轮做跨 feature 复验（不是替代）**；MUST NOT 修改 `harness/demo/target.py`。 | FR-022 / FR-028 / FR-029 · SC-003 / SC-014 / SC-019 / SC-020 |
| **D-06** | **B20F2** | **M3** | trace 的 SQLite 后端与本 feature 的 checkpoint SQLite 后端是**两套存储**；MUST NOT 共用表 / 文件 / 连接；`SqliteTraceStore` 的 schema 与 `SqliteSaver` 的 schema 互不影响。 | 裁定 2 / 3 · FR-002 |

---

## 下游承接状态（上游 → 本 feature 的核对）

| 来源 | 编号 | 状态 |
|---|---|---|
| **B10F1** | D-1 / D-9 · X-5 消解 · **F-3** | ✅ **已接线**（FR-006 / FR-007 / FR-008 / FR-018 · **FR-037 / 裁定 13 / SC-027**） |
| **B12F1** | D-7 | ✅ **已接线**（FR-018 · 裁定 8） |
| **B11F1** | D-8 | ✅ **已接线**（FR-020） |
| **B13F1** | D-6 | ✅ **已接线**（FR-019） |
| **B8F3** | D-1 / D-3 | ✅ **已接线**（FR-021 · 裁定 7） |
| **B14F1** | D-01 / D-02 / D-08 / **D-09** | ✅ **已接线**（FR-006 / FR-022 / FR-010 · **next-tasks 读取权威**：FR-018 / FR-037 / 裁定 13） |
| **B7F3** | D-5 | ✅ **已接线**（FR-023 · 裁定 1 · 破冻结面回溯修订清单） |
| **B8F2** | D-2 / D-5 | ✅ **已接线**（FR-022 · 裁定 10 · 回溯修订清单） |
