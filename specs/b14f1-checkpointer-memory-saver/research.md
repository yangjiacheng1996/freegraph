# Research · B14F1 · Checkpointer 协议 + `MemorySaver`（快照 + pending writes 双层持久化）

> **输入**：`spec.md`（**唯一权威** · 5 条澄清轮拍板 + 13 条形态锁定裁定 + FR-001…FR-035 +
> SC-001…SC-025 + P-01…P-21 + X-01…X-08）· 宪法 **v1.16.1** · 上游 `langgraph` **1.2.11**
> （取证于 **2026-11-22** · `.venv` 内安装 · 仅差分测试侧使用）。
>
> **判定纪律**（宪法原则 XI）：每条决策先问「上游怎么说」⇒ 上游有答案 ⇒ **照抄**；
> 只在**必须自研区**自研并**如实登记**（spec 的 X-01…X-08）。
> **形态纪律**（原则 XII）：内容照抄 + 形态取最优；快照与写入**分层**，调度账本**一等**，
> `CheckpointTuple` **恰好 3 字段**。

---

## §1 现状盘点（动手前的事实基线）

| # | 事实 | 取证 | 影响 |
|---|---|---|---|
| **F-01** | L1 `Checkpointer` 已是 **8 方法**的结构化协议（`runtime_checkable`），返回类型 `Any` | `src/freegraph/contracts/protocols.py:76-138` | 本 feature **只实现**，L1 零改动 |
| **F-02** | L1 `StateSnapshot` 是 **8 字段**的冻结 dataclass | `src/freegraph/contracts/types.py:260-311` | 读侧载体**直接复用**，零新增快照类型 |
| **F-03** | `RunConfig` 有 **9 字段**（含 `thread_id` / `configurable` / `context` / `metadata` / `tags`） | `src/freegraph/contracts/types.py:151-256` | `snapshot.config` 只承载 `thread_id` + `checkpoint_id`；`context=None` |
| **F-04** | `RunConfig.resolved_thread_id()` 接受顶层 `thread_id` 或 `configurable["thread_id"]` | `src/freegraph/contracts/types.py:245-256` | 统一用该入口取生效线程 id |
| **F-05** | 运行期已有 `run_graph` / `_first_graph` / `_resume_graph` / `_run_graph_loop` / `_run_round` | `src/freegraph/runtime/superstep.py:2060,2314,2410,2490` | 落盘接线的**既有唯一路径** |
| **F-06** | 挂起写已由 B10F1 / B13F1 落地：`_write_suspend` 调 `put` + `put_writes`；`_clear_static_suspension` 写 F-10 完成快照 | `src/freegraph/runtime/superstep.py:2337-2407` | 本 feature **只补**初始 / 每轮 / 错误轮；挂起写仅改为把 `put` 返回的显式 config 传给 `put_writes`，**不改**其快照 / metadata 语义（挂起快照 `tasks=()`） |
| **F-07** | `start_node_span` 已接受 `checkpoint_id` 参数，但运行期调用点传 `None` | `src/freegraph/runtime/_span_hook.py:140-170` · `superstep.py:1460` | 只需把当前 id 传入；`Span` 11 字段零改动 |
| **F-08** | `_run_round` 有三个调用点（`run_super_step` / `run_super_steps` / `_run_graph_loop`） | `superstep.py:1715,1839,2126` | 只增 **keyword-only** 私有参数，缺省不改既有调用 |
| **F-09** | `_run_round` 的 ⑥ 收尾点：真异常 `raise error` **先于** `raise GraphInterrupt(interrupts)` | `superstep.py:1590-1620` | 真异常同现时中断**不会**进入 `_run_graph_loop` ⇒ 需私有收集器 |
| **F-10** | `compile()` 当前接受 + 记录任意 `checkpointer`，不做类型校验 | `src/freegraph/_stategraph.py:1169-1220` | 本 feature 在 L3 边界补校验 |
| **F-11** | `freegraph.graph` 门面 **禁止** import L4 / L5（G18） | `tests/facade/_gatesupport.py` | `MemorySaver` **不**从门面转出 |
| **F-12** | `src/freegraph/persistence/` 已在层注册表登记为 **L4** | `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` §1 | 新包零注册表改动；G25 可直接判 |
| **F-13** | 当前基线 **2111 passed / 8 skipped**（2026-11-22 实跑） | `.venv/bin/python -m pytest -q --tb=no` | 实施后必须回到全绿（除 skip） |
| **F-14** | README 的 `Checkpointer` 行写「返回类型与载荷形状挂起 B14F1」；边界段写「编译期不做类型校验」 | `README.md:122,167` | R-5：本 feature 落地后更新文档 + 测试文本 |
| **F-15** | `harness/demo/README.md` 的待锁定清单仍列 `MemorySaver` 模块路径；`graph_core.py` 的恢复段仍是 `soft(...)` | `harness/demo/README.md:101,121` · `harness/demo/graph_core.py:392-435` | FR-027：移除待锁定条目 + `soft→check` |

---

## §2 设计决策（D-01…D-20）

### D-01 · L4 包结构与公开面

- **Decision**：新增 `src/freegraph/persistence/`：
  - `__init__.py`：`__all__ = ["MemorySaver", "InMemorySaver", "CheckpointTuple"]`；
  - `_types.py`：`CheckpointTuple`；
  - `memory.py`：`MemorySaver` / `InMemorySaver = MemorySaver`。
  只 import `freegraph.contracts`（L1）+ 标准库；**不** import L2 / L3 / L5。
- **Rationale**：层注册表固定 L4 = `persistence`；门面 G18 禁止转出 L4；上游
  `langgraph.checkpoint.memory` 是独立子包 ⇒ 同构。`CheckpointTuple` 是读侧载体，
  与 `MemorySaver` 同包便于 `get_tuple` 返回。
- **Alternatives considered**：
  - 放 `freegraph.checkpoint` ⇒ 层注册表未登记；新增条目 = 改冻结面。
  - 放 `freegraph.graph` 门面 ⇒ G18 判红。
  - 把 `CheckpointTuple` 放 L1 ⇒ 破 L1 符号面（C19 只要求 `Any` 返回，不要新符号）。
  - 每个 saver 一个模块但共享 `_types` ⇒ 可；本 feature 只有内存 saver，保持最小。

### D-02 · 存储模型：快照 + 写入**分层**

- **Decision**：每 `thread_id` 一份 `_ThreadStore`：
  - `snapshots: dict[str, _StoredCheckpoint]`（快照 8 字段 + 调度账本）；
  - `order: list[str]`（插入序 · 便于 `list` 排序）；
  - `writes: dict[str, dict[tuple[str, int], _StoredWrite]]`（按 checkpoint id 分桶，
    桶内键 = `(task_id, idx)` · 上游同款）；
  - `next_seq: int`（顺位 id 生成）；
  - `latest_id: str | None`。
  `_StoredWrite` 保存 `task_id` / `channel` / `value` / `task_path` / `idx`
  （普通通道 `idx` = 本次调用内位置；保留通道 `idx` = `WRITES_IDX_MAP` 负值）。
- **Rationale**：快照用于「回到某一步」，pending writes 用于「崩溃后重放」⇒ **两种数据**；
  分开存储才能保证 `put_writes` 不污染 `values`，且 `get_tuple` 能按 checkpoint 精确取回。
- **Alternatives considered**：
  - 把写进快照的 `values` ⇒ 违反 FR-003 分层，且无法区分「已合并 / 未落地」。
  - 只存一个扁平列表 ⇒ 无法按 checkpoint 取回 / 删除 / 排序。
  - 用 `metadata` 塞 pending writes ⇒ 借位，违反原则 XII。

### D-03 · checkpoint 顺位 id

- **Decision**：每线程从 `1` 开始，格式 `f"{n:032d}"`；`get_tuple` / `list` / `before`
  按字符串序（== 数值序）比较；`delete_thread` 后重建从 `1` 开始。
- **Rationale**：标准库无 `uuid6`；零填充十进制字符串字典序 == 数值序，满足排序与
  `before` 过滤；内存 saver 无跨进程需求 ⇒ 计数器足够。上游用 `uuid6(clock_seq=step)`
  （`_checkpoint.py:31,209`）⇒ 登记 **X-01**。
- **Alternatives considered**：
  - `uuid4().hex` ⇒ 不可排序，`before` 需额外元数据。
  - `time.time_ns()` ⇒ 同纳秒冲突风险；时钟回拨风险。
  - `uuid1()` ⇒ 依赖 MAC / 时间，且非严格单调；跨平台差异。

### D-04 · 版本命名空间（`get_next_version`）

- **Decision**：`get_next_version(current, channel=None) -> int`：
  `current is None => 1`；`int` 且非 `bool` => `current + 1`；其它 => `TypeError`。
  `put` **原样保存** `metadata["scheduler"]`，**不**调用 `get_next_version` 改写调度版本。
- **Rationale**：B7F1 的 `channel_versions` / `node_versions` 是 `dict[str, int]`；
  上游 `BaseCheckpointSaver.get_next_version` 默认也是 `int+1`（`base/__init__.py:721-740`）。
  若照抄上游 `InMemorySaver` 的字符串形式（`memory/__init__.py:622-630`），会引入第二套
  版本命名空间，导致「触发判定所用版本」与「持久化版本」漂移 ⇒ 登记 **X-02**。
- **Alternatives considered**：
  - 字符串 `<32 位递增>.<16 位随机>` ⇒ 上游内存同款，但与 B7F1 整数版本不一致。
  - 双形态（int 入 int 出 / str 入 str 出）⇒ 增加歧义，SC-004 难判定。
  - 方法抛 `NotImplementedError` ⇒ 协议可用性下降，FR-005 不可满足。

### D-05 · 读侧载体 `CheckpointTuple`

- **Decision**：`@dataclass(frozen=True, slots=True)`，**恰好 3 个公开字段**：
  `snapshot: StateSnapshot` · `pending_writes: tuple[tuple[str, str, Any], ...]` ·
  `scheduler: dict[str, Any]`。不加上游 `.config` / `.checkpoint` / `.metadata` 别名。
- **Rationale**：B10F1 契约 §2 逐字要求三个具名属性；用户已确认选项 A。额外字段会产生
  「两套事实来源」，且上游 `checkpoint` 是 `Checkpoint` TypedDict，与 freegraph 的
  `StateSnapshot` 形态不同 ⇒ 不加别名更清晰。
- **Alternatives considered**：
  - 加上游只读别名 ⇒ 公开面变多，B15F1 需同步两套。
  - 加上游完整第二套结构 ⇒ 两套状态载体，维护成本高。
  - 返回普通 `dict` ⇒ 失去「具名属性」契约与 IDE 可读性。

### D-06 · `put` / `put_writes` 语义

- **Decision**：
  - `put(config, *, values, metadata) -> RunConfig`：校验 `Mapping`；**先深拷贝再落锁提交**；
    生成新 id；`parent_config` = 上一快照 config；返回 `RunConfig(thread_id=..., configurable={"checkpoint_id": id})`。
  - `put_writes(config, *, writes, task_id, task_path="") -> None`：目标 = `configurable["checkpoint_id"]`
    指定的快照（缺 key ⇒ `KeyError`；指定 id 不存在 ⇒ `ValueError` · X-07）；
    去重键 `(task_id, WRITES_IDX_MAP.get(channel, idx))`：普通通道跨调用同 `(task_id, idx)`
    首次生效，保留通道最后生效（**同调用内也覆盖**）；`.pending_writes` 按
    `(task_path, task_id, idx)` 升序（`writes_sort_key`）。
  - `list(config=None, *, filter=None, before=None, limit=None)`：`config=None` 全线程按存储
    **插入序**；同线程 id 降序；`filter` 匹配 metadata 顶层 key；`before` 排除
    `id >= before_id`；`limit<=0` 空；返回迭代器。
  - `get_tuple(config)`：按 `configurable["checkpoint_id"]` 取指定，否则最新；不存在 ⇒ `None`。
  - `delete_thread(thread_id)`：删快照 + 写入 + 内部状态；幂等。
  - `delete_for_runs` / `copy_thread`：存在，v1 `NotImplementedError`（上游内存 saver 同款）。
- **Rationale**：逐条对齐 B10F1 写侧契约与上游 `InMemorySaver` 的读写语义；`put` 返回带
  id 的 config 与上游 `put` 返回 `RunnableConfig` 同款，并给运行期提供 span `checkpoint_id`。
- **Alternatives considered**：
  - `put_writes` 隐式创建快照 ⇒ 历史里出现非执行快照，SC-001 计数不可判定。
  - 普通通道「最后生效」⇒ 与上游 `WRITES_IDX_MAP` 语义不符。
  - `put` 不返回 config ⇒ 运行期需再 `get_tuple` 取 id，多一次读且可能竞态。

### D-07 · `thread_id` 缺失 / 无效

- **Decision**：运行期 `effective_checkpointer` 在生效 `thread_id` 为 `None` / 空串时归一为
  `None`（不调用 saver）；直接调用 `MemorySaver` 的 `get_tuple` / `put` / `put_writes` /
  `list(config)` ⇒ `ValueError`。`list(None)` 不需要 `thread_id`。
- **Rationale**：SC-005 要求「注入 checkpointer 不改变执行结果」；无 `thread_id` 时无法定义
  会话，静默共享会话更危险。上游缺 `configurable["thread_id"]` 抛 `KeyError` ⇒ 本 feature
  用更明确的 `ValueError` ⇒ 登记 **X-03**。
- **Alternatives considered**：
  - 自动生成临时 `thread_id` ⇒ 用户拿不到 id，无法取回。
  - 固定匿名 id ⇒ 多个无会话运行共享状态。
  - 直接抛 `ValueError` ⇒ 改变「不挂 saver 也能跑」的既有行为（SC-005 红）。

### D-08 · 每轮快照持久化策略

- **Decision**：
  - **全新会话**：在第一个 `_run_round` **之前**写一条**惰性初始快照**（`next` = 第一轮触发集）；
    若先命中 `interrupt_before`，由挂起写**兼任**初始快照（不重复）。
  - **每轮执行完成**（合并成功后）：写一条每轮快照；`next` = 下一轮触发集（收敛 ⇒ `()`）；
    `interrupts=()`；`tasks` = 本轮 `PregelTask`；`scheduler` = `state.to_checkpoint()`。
  - **动态中断**：`_write_suspend` 的挂起写就是该轮快照；不再写每轮快照；`tasks=()`。
  - **静态 `interrupt_after`**：挂起写**代替**该轮每轮快照；`tasks=()`。
  - **静态 `interrupt_before`**：挂起写计入「待执行轮」；首轮前命中时兼作初始快照；`tasks=()`。
  - **`static_resume` 完成**：最后一轮跳过每轮 `put`，由 B13F1 的 `_clear_static_suspension`
    写一次 F-10 完成快照（不重复 / 不冲突）。
  - **收敛空轮**：不产生快照。
  - **会话连续 / 恢复**：不写新的初始快照；从历史快照的 id 开始，后续按每轮 / 挂起写。
- **Rationale**：用户已确认选项 A；该策略让 SC-001 / SC-015 的计数可判定，且不重复。
- **Alternatives considered**：
  - 每事件都写 ⇒ 历史出现重复快照。
  - 只写挂起快照 ⇒ 失去逐步历史。
  - 只写每轮快照、静态挂起复用上一轮 ⇒ 挂起现场不完整。

### D-09 · 「真异常 + 中断同现」的留痕机制

- **Decision**：新增 L2 私有 `runtime/_checkpoint.py` 的 `ContextVar`（如
  `_ROUND_INTERRUPTS`）作为**本轮中断收集器**。`_run_graph_loop` 在调用 `_run_round` 前
  set 收集器；`_run_round` 在 ⑥ 发现「有真异常 + 有中断」时，把
  `[(task_key, (payload,)), ...]` 写入收集器，然后**照旧** `raise error`；
  `_run_graph_loop` 捕获后，先用 `put_writes` 留痕，再原样 `raise error`。
  `_run_round` 的返回类型 / 既有异常对象**零改动**。
- **Rationale**：上游 `_runner.py:588-591` 在真异常抛出前写中断到 checkpoint；本 feature
  需要同样的**留痕**，但不能把中断塞进异常（B12F1 裁定 10 / 原则 XI ③）。
  contextvar 是纯内部机制，不改变用户可见行为。
- **Alternatives considered**：
  - 在异常上加私有属性 ⇒ 仍是「在异常上挂数据」，违反 B12F1 的「不自创留痕形态」精神。
  - 改 `_run_round` 返回私有结果对象 ⇒ 波及两个低层入口，改动面大。
  - 把中断写进 `SchedulerState` ⇒ 违反「不自创持久化载体」。

### D-10 · 节点 span 的 `checkpoint_id`

- **Decision**：`_run_round` 增 keyword-only `checkpoint_id: str | None = None`；
  `_bind` 调 `start_node_span(..., checkpoint_id=checkpoint_id)`。`_run_graph_loop` 维护
  `current_checkpoint_id`：
  - 全新会话：初始 `put` 返回的 config 的 id；
  - 恢复 / 会话连续：历史 `snapshot.config.configurable["checkpoint_id"]`；
  - 每个每轮 / 挂起写之后：更新为最新 `put` 返回的 id；
  - 无 saver / 无 thread_id：`None`。
- **Rationale**：`start_node_span` 已有该参数（F-07）；不新增 `Span` 字段、不改 B18F1 的
  子 span 继承逻辑。上游节点 span 的 `checkpoint_id` 也来自当前 checkpoint。
- **Alternatives considered**：
  - 在 `Span` 上加新字段 ⇒ 破 11 字段冻结面。
  - 运行期全局变量 ⇒ 并发不安全。
  - 在每个节点执行后查 `get_tuple` ⇒ 额外 O(N) 读，且与执行的 checkpoint 时点不一致。

### D-11 · `checkpoints` 事件数据源

- **Decision**：`MemorySaver(*, on_checkpoint: Callable[[StateSnapshot], None] | None = None)`。
  每次成功 `put` 后，**释放锁**，把一份**深拷贝**的 `StateSnapshot` 交给回调；回调异常
  吞掉（不传播、不回滚）。`list()` 提供历史枚举。**不**改 `StreamSession`。
- **Rationale**：用户确认选项 A；不依赖 L5；测试可直接计数；失败隔离与 trace sink 同款。
  D-2 只要求数据源；消费端接线归 B8F2 / B15F1。
- **Alternatives considered**：
  - 只给 `list()` ⇒ 运行中无法实时收到事件。
  - `subscribe()` / `iter_checkpoints()` ⇒ 需管理订阅生命周期，API 更大。
  - 内部事件队列 + `drain_events()` ⇒ 调用方需轮询，且队列无界增长风险。

### D-12 · `snapshot.config` 与 `context`

- **Decision**：`snapshot.config = RunConfig(thread_id=<生效 id>,
  configurable={"checkpoint_id": <新 id>})`；`context=None`；**不复制**调用方的
  `metadata` / `tags` / 其它 `configurable` 键。`metadata` 存 `put` 传入的深拷贝，
  **不**注入 `context`。恢复时不从快照还原 `context`。
- **Rationale**：上游 `InMemorySaver.put` 返回的 config 只含 `configurable` 的
  `thread_id` / `checkpoint_ns` / `checkpoint_id`；freegraph 无 `checkpoint_ns` ⇒
  最小形态 = `thread_id` + `checkpoint_id`。B8F3 D-1 / D-3 明确 `context` 不持久化。
- **Alternatives considered**：
  - 复制整个调用方 config ⇒ `context` 可能落盘，违反 B8F3。
  - 把 `context` 塞进 `configurable` ⇒ 明确禁止。
  - 把 `scheduler` 从 `metadata` 移除、只留 `.scheduler` ⇒ 违反 B10F1 的 metadata 形状。

### D-13 · 编译期 `checkpointer` 校验

- **Decision**：在 `_stategraph.py` 新增私有 `_validate_checkpointer(checkpointer)`：
  - `None` / `True` / `False` ⇒ 接受；
  - `isinstance(checkpointer, Checkpointer)` ⇒ 接受；
  - 其它 ⇒ `TypeError`（消息点名期望 `BaseCheckpointSaver` 等价物 / `True` / `False` / `None`）。
  `compile()` 在构造 `CompiledGraph` 前调用；**不改**记录方式。
- **Rationale**：B7F2 D-4 要求补上游同款校验；L3 不能 import L4（向上 import 违规），
  故校验用 L1 的 `runtime_checkable` 协议 + 私有函数。`True` / `False` 是上游允许的哨兵；
  freegraph v1 无子图，运行期视为无 saver（X-06）。
- **Alternatives considered**：
  - 在 L4 提供 `ensure_valid_checkpointer` 让 L3 import ⇒ L3 → L4 违规。
  - 改 L1 协议/新增函数 ⇒ 破 L1 符号面。
  - 只在运行期校验 ⇒ B7F2 D-4 未消解，用户错误延迟暴露。

### D-14 · 失败信号

- **Decision**：非法参数用内置 `TypeError` / `ValueError`，消息点名参数；深拷贝失败原异常
  传播；不新增 L1 异常；无 I/O ⇒ 无 `OSError` / 超时类失败。
- **Rationale**：spec 裁定 13；B1F1 的异常面零改动。
- **Alternatives considered**：
  - 新增 `CheckpointError` ⇒ 破 L1 异常面 / 需契约修订。
  - 吞掉深拷贝错误 ⇒ 存储半成品或共享引用，违反 FR-031。

### D-15 · 运行期归一化 `checkpointer`

- **Decision**：`run_graph` 入口调用 `effective_checkpointer(checkpointer, run_config)`：
  - `None` / `True` / `False` ⇒ `None`；
  - 生效 `thread_id` 为 `None` / 空串 ⇒ `None`；
  - 否则返回原对象（**鸭子类型**；**不在运行期判 `isinstance(..., Checkpointer)`**）。
  下游所有 `get_tuple` / `put` / `put_writes` 只看归一化后的值。
- **Rationale**：一处归一化，避免在每个调用点重复判 bool / thread_id；`True` / `False`
  不会在运行期触发 `AttributeError`；无 `thread_id` 时 SC-005 保持。
  **运行期不判协议**是刻意取舍：L2 的既有测试桩（`StubCheckpointer` / `_ProbeCheckpointer`）
  只实现恢复路径用到的 3 个方法（B7F3 的 F-05 冻结），若运行期判 8 方法会被归一为 `None`
  而破坏既有测试与差分；协议校验只在 **L3 `compile()`** 边界（FR-010）完成。
- **Alternatives considered**：
  - 运行期判 8 方法协议 ⇒ 既有 3 方法桩全部失效，红点不可控。
  - 每个调用点各自判断 ⇒ 容易漏；行为不一致。
  - 在 `CompiledGraph.invoke` 归一化 ⇒ L3 需知道 bool 语义；且 `run_graph` 仍可能被直接调用。

### D-16 · 初始快照的「惰性」实现

- **Decision**：`_run_graph_loop` 增 `is_fresh: bool`（仅 `_first_graph` 的 `history is None`
  路径为 `True`）。在static_before 检查之后、`_run_round` 之前，若 `is_fresh` 且尚未写初始
  快照 ⇒ `put_initial(...)`，并更新 `current_checkpoint_id`。static_before 命中时直接
  `_write_suspend(...)` 并返回，不写初始。
- **Rationale**：静态 before 首轮前命中时快照数应为 1（挂起写兼任初始），惰性写保证不重复。
- **Alternatives considered**：
  - 进入 `_run_graph_loop` 立即写初始 ⇒ 静态 before 首轮命中时出现 2 条，SC-001 红。
  - 不写初始 ⇒ SC-001 的「+1」缺少载体。

### D-17 · 每轮快照的 `next` 计算

- **Decision**：每轮合并成功后，先算 `next_nodes = _determine_triggers(spec, state)`（以及
  `state.fanout` 的目标）；若 `interrupt_after` 命中 ⇒ 用该 `next_nodes` 写挂起快照；
  否则写每轮快照；若 `next_nodes` 为空且无 fanout ⇒ 每轮快照的 `next=()`，下一轮循环收敛
  退出；`static_resume` 且收敛 ⇒ 跳过该每轮 `put`，由 F-10 写完成快照。
- **Rationale**：`next` 必须反映「下一步要执行的节点」，不能只写 `()`；`_determine_triggers`
  是既有纯函数（F-05），提前调用不改变状态。
- **Alternatives considered**：
  - 只在下一次循环顶部写上一轮快照 ⇒ 收敛时没有 `next=()` 的终态快照。
  - 每轮都写 `next=()` ⇒ B15F1 的 `get_state().next` 错误。

### D-18 · `put` 的原子性

- **Decision**：在锁外完成所有校验与深拷贝，构造 `_StoredCheckpoint` / 新 `StateSnapshot`；
  然后在锁内一次性更新 `snapshots` / `order` / `latest_id` / `next_seq`；最后释放锁并调用
  `on_checkpoint`。任一步失败 ⇒ 不修改存储。
- **Rationale**：FR-031 要求「要么完整提交，要么完全不变」；深拷贝在锁外可减少锁持有时间。
- **Alternatives considered**：
  - 先写存储再深拷贝 ⇒ 失败留下半成品。
  - 全程持锁深拷贝 ⇒ 锁持有时间长，回调可能阻塞。

### D-19 · 差分测试的组织

- **Decision**：新增 `tests/differential/test_b14f1_checkpoint_parity.py`，用
  `pytest.importorskip("langgraph")`；D-01…D-15 直接对跑 freegraph `MemorySaver` +
  `run_graph` 与上游 `InMemorySaver` + `StateGraph.compile()`；比较快照计数 / `values` /
  `next` / pending writes / 恢复结果 / 静态挂起 / fan-out / 屏障 / 真异常留痕 / 编译期校验。
  既有 `parity_probe.py` **只改** D-77 的判词（R-1），不改其它场景。
- **Rationale**：新文件隔离 checkpoint 语义，避免 2,700+ 行探针的耦合；上游缺席 skip 纪律不变。
- **Alternatives considered**：
  - 全部塞进 `parity_probe.py` ⇒ 改动面大、既有场景风险。
  - 只做 freegraph 内部测试 ⇒ 无法证明上游同款（宪法原则 XI）。

### D-20 · 行数与范围

- **Decision**：按 spec 的 1,200 行（实现 560 / 测试 640）排期；实施期实测超支 MUST 在
  `tasks.md` §行数预算表登记（R-7），**不**削减 FR / SC。
- **Rationale**：运行期接线 + 差分探针 + 冻结断言回溯修订可能超预算；透明登记优于悄悄超支。
- **Alternatives considered**：
  - 先砍测试 ⇒ 判据不可测（违反原则 VI）。
  - 先砍差分 ⇒ 无法证明上游同款（违反原则 XI）。

---

## §3 上游取证摘要（`langgraph` 1.2.11）

| 语义 | 锚点 |
|---|---|
| `PendingWrite` 三元组 / 排序 | `checkpoint/base/__init__.py:32` · `:185-196`（`writes_sort_key`） |
| `WRITES_IDX_MAP`（去重索引） | `checkpoint/base/__init__.py:815-824` |
| `Checkpoint` / `CheckpointTuple` | `checkpoint/base/__init__.py:93-147` |
| `BaseCheckpointSaver` 8 方法 | `checkpoint/base/__init__.py:199,262,277,301,324,344,355,374,721` |
| `InMemorySaver` / 别名 | `checkpoint/memory/__init__.py:34,634` |
| `get_tuple` / `list` / `put` / `put_writes` / `delete_thread` | `checkpoint/memory/__init__.py:239,321,430,476,514` |
| `get_next_version` | `checkpoint/base/__init__.py:721-740`（默认 int）· `checkpoint/memory/__init__.py:622-630`（字符串） |
| checkpoint id 生成 | `pregel/_checkpoint.py:31,209`（`uuid6`） |
| 中断写 pending writes / 真异常优先 / 合并中断 | `pregel/_runner.py:588-591,687,690` |
| `checkpoints` 事件 | `pregel/_loop.py:631-636` · `pregel/debug.py:144-185` |
| `StateSnapshot` 8 字段 | `types.py:684-701` |
| 编译期校验 | `types.py:109-118` · `graph/state.py:1179,1234` |
| 保留通道名 | `_internal/_constants.py:9,11,13,17` |
| `True` / `False` 运行期分支 | `pregel/main.py:2579-2583` |

---

## §4 与 spec 的对应

| research 决策 | spec 落点 |
|---|---|
| D-01 / D-05 | 裁定 1 / 3 · FR-001 / FR-009 / FR-011 |
| D-02 / D-06 | 裁定 6 · FR-003 / FR-013 / FR-015 / FR-016 |
| D-03 / D-04 | 裁定 4 · FR-005 · SC-004 |
| D-07 | 裁定 7 · FR-018 · X-03 |
| D-08 / D-16 / D-17 | 裁定 5 · FR-002 / FR-019 · SC-001 / SC-015 |
| D-09 | 裁定 10 · FR-021 · SC-018 |
| D-10 | 裁定 11 · FR-022 · SC-019 |
| D-11 | 裁定 11 · FR-023 · SC-020 |
| D-12 | 裁定 12 · FR-024 · SC-021 |
| D-13 | 裁定 2 · FR-010 · SC-013 |
| D-14 | 裁定 13 · FR-031 |
| D-15 | 裁定 2 / 7 · FR-007 / FR-018 |
| D-18 | FR-031 · SC-002 |
| D-19 | FR-033 / FR-035 · SC-025 |
| D-20 | R-7 · tasks 行数预算 |
