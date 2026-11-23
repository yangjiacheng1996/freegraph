# Feature Specification: B14F1 · Checkpointer 协议 + `MemorySaver`（快照 + pending writes 双层持久化）

**Feature Branch**: `b14f1-checkpointer-memory-saver`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_specify` 钩子；既有 feature 同样在 `main` 上开发）

**Created**: 2026-11-22

**Status**: Draft

**Input**: `harness/features/B14F1_Checkpointer协议与MemorySaver.md` —— 交付**检查点能力的第一段**：把 C19 协议落成第一个可用实现 `MemorySaver` —— 在每个 super-step 结束时把**状态快照**与**待写入（pending writes）**分别持久化，并提供按 `thread_id` 取回的能力。判定：**快照 + pending writes 双层持久化**。前置依赖 **B7F3**。

> **范围提醒**：本 feature 是 **L4 持久化层**的**第一段**，交付 **L1 `Checkpointer` 协议的完整实现** + **运行期每轮落盘接线** + **读侧最小契约**。它**不**交付 `SqliteSaver` / `get_state` / `get_state_history` / `update_state` / 时间旅行 / `Store` / Postgres / 跨进程共享（分别归 B15F1 / B15F1 / B16F1 / B16F1 / 已砍 B17 / v2 / v2）。`StateSnapshot` 的 **8 字段**、`Checkpointer` 协议的 **8 方法**、`RunConfig` 的 **9 字段**、`Span` 的 **11 字段**、`freegraph.graph` 门面符号面**一律不改**。

---

## 0. 第一性目标与口径来源

> **上游 `langgraph` 1.2.11 是唯一权威**（宪法 **原则 XI「上游优先」**）⇒ 本 spec 以「**与上游 checkpoint 行为面逐条同款**」为缺省口径 ⇒ **只在失败信号 / 已冻结的跨 feature 契约上**允许刻意分叉，且 MUST **如实标注**并写明理由。

| 项 | 值 | 依据 |
|---|---|---|
| **feature ID** | `B14F1` | 提示词抬头 |
| **所属功能块** | B14（Checkpointer 协议 + MemorySaver） | 同上 |
| **架构层** | **L4 持久化层**（`src/freegraph/persistence/**`）· ⚠️ **L4 只依赖 L1 + 标准库** ⇒ **MUST NOT** import L2 / L3 / L5（ARCH-1 / ARCH-3 · G25） | 提示词 §9 · `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` §1 |
| **里程碑** | **M3 可诊断**（第 26 个） | 提示词抬头 |
| **前置依赖** | **B7F3**（`invoke()` 全状态 · 已交付） | 提示词抬头 |
| **规模（立项书口径）** | **1,200 行**（实现 560 / 测试 640）· 3 人日 | 提示词抬头 |
| **契约** | **C19**（检查点接口）· **C17**（中断原语）· **C16**（`Command`）· **C22**（`RunConfig`）· **C23**（span 必带 `checkpoint_id`）· **C21**（`context` 独立通道 · 不持久化） | `harness/reports/Q8-图运行时最小契约.md` §3.4 |
| **上游版本（钉住）** | `langgraph` **1.2.11**（取证于 **2026-11-22** · 本仓库 `.venv` 内安装） | `.venv/lib/python3.11/site-packages/langgraph/` |
| **上游取证命令** | `.venv/bin/python` + `langgraph.checkpoint.memory.InMemorySaver`（**仅开发期** · 不进发行面） | 宪法「依赖白名单」：上游只作**差分测试侧**依赖 |
| **门禁约束（G25 · 导入图）** | `src/freegraph/persistence/` 已登记为 **L4**；L4 只能向下依赖 **L1**（本 feature **不**使用 L2 / L3 能力）⇒ **MUST NOT** 横向依赖 L5（可观测层） | 层注册表 §0.2 规则 2 · §1 条目表 · G25 |

⚠️ **零出站 / 零环境变量 / 零第三方运行时依赖**（宪法原则 I / II / V）：
本 feature 的**生产代码** MUST NOT import `langchain` / `langchain-core` / `langgraph*` /
`langsmith` / 任何第三方包 ⇒ MUST NOT 读任何环境变量 ⇒ MUST NOT 有任何出站。
`MemorySaver` 的存储、时间源、拷贝、锁、ID 生成 MUST 全部用**标准库**。

⚠️ **协议方法集的事实订正（提示词 6 → 冻结面 8）**：提示词 §2 把方法集写成
`get_tuple` / `list` / `put` / `put_writes` / `delete_thread` / `get_next_version` **六个**；
但 **B2F1 已于 2026-11-12 上游对齐 P3 冻结为八个**（增 `delete_for_runs` / `copy_thread`，
见 `src/freegraph/contracts/protocols.py:76-138`）⇒ 本 feature MUST 实现**全部八个**
⇒ 提示词的六项清单是**上游对齐前的简写**，**不是**要缩减冻结面 ⇒ **L1 协议零改动**。

⚠️ **`MemorySaver` 的定位**：**开发 / 调试**（与上游 `InMemorySaver` 一致），
**不适用于生产** ⇒ 生产 / 长期 / 跨重启场景由 **B15F1 的 `SqliteSaver`** 承担
⇒ 本 feature MUST NOT 把内存态实现宣传为「可跨进程 / 跨重启恢复」。

---

## Clarifications

### Session 2026-11-22

- Q: 对于「每创建一个 checkpoint 一条事件」的数据源，你希望 `MemorySaver` 采用哪一种公开形态?（FR-023 / 裁定 11） → A: **选项 A** —— 构造参数 `on_checkpoint` 回调（每次成功 `put` 恰调用一次）+ `list()` 历史枚举。
- Q: `get_next_version` 的返回类型，你希望采用哪一种?（FR-005 / SC-004 / 裁定 4） → A: **选项 A** —— 返回 `int`（`None → 1`，`k → k + 1`），与 B7F1 的调度版本同命名空间。
- Q: `get_tuple` 返回的读侧载体 `CheckpointTuple`，你希望它暴露哪些字段?（FR-011 / 裁定 3） → A: **选项 A** —— 恰好 3 个字段：`.snapshot` / `.pending_writes` / `.scheduler`。
- Q: 当用户挂了 `checkpointer` 但没有提供 `thread_id` 时，你希望系统怎么处理?（FR-018 / 裁定 7 / 偏离 X-03） → A: **选项 A** —— 运行期跳过全部落盘；直接调用 saver 时抛 `ValueError`。
- Q: 静态挂起（`interrupt_before` / `interrupt_after`）时，快照数量与「每轮快照」怎么衔接?（FR-019 / 裁定 5 / SC-001 / SC-015） → A: **选项 A** —— 初始惰性写；挂起写计入该轮；`interrupt_after` 用挂起写代替每轮快照；首轮前 `interrupt_before` 兼作初始快照；收敛空轮不写。

---

## 承接条款（上游 feature → 本 feature）

> **宪法「跨 feature 承接的接线通则」**：上游 feature 的规格中出现**指名本 feature**的
> 跨 feature 义务时，该条款 MUST 在本 spec 落成 **FR + 裁定**。
> **只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽任何门禁判据。**

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B10F1 → B14F1** | **M3** | **检查点读侧 / 写侧最小契约**：① `get_tuple(config)` 返回值 MUST 暴露 `.snapshot`（L1 `StateSnapshot` · 8 字段）· `.pending_writes`（`(task_id, channel, value)` 三元组序列）· `.scheduler`（纯数据 · JSON 可序列化）；② `put(config, values=..., metadata=...)` 写快照 · `put_writes(config, writes=..., task_id=..., task_path=...)` 写待写入（目标由 `configurable["checkpoint_id"]` 指定 · 缺 key ⇒ `KeyError`）；③ 保留通道名 `__interrupt__` / `__resume__` 逐字同款；④ 标准任务 `task_id` = 节点名；⑤ 挂起时 `metadata` 载荷 `next` / `interrupts` / `tasks` / `scheduler` **原样存取**；⑥ 人工验证补「恢复侧真跑一轮」；⑦ **B10F1 的 X-5**（「真异常 + 中断同现」时中断元组丢弃）在本 feature 落地后**自动消解** | `specs/b10f1-interrupt-resume/spec.md` FR-018 / FR-019 · 裁定 9 · SC-005 / SC-020 · 偏离登记 X-5 · 下游承接 D-1 / D-2 · `specs/b10f1-interrupt-resume/contracts/checkpoint-contract.md` §2…§6 | **FR-011…FR-014** · **FR-021** · **FR-026** · 裁定 3 / 6 / 10 |
| **H-2** | **B12F1 → B14F1** | **M3** | **跨进程 / 跨重启的会话隔离**：MUST 保证「同一 `thread_id` 的连续调用」与「不同 `thread_id` 的并行调用」状态互不干扰；会话状态按 `thread_id` 落在 checkpointer 上；**进程内**隔离由 B7F2 / B7F3 承担（每次 `invoke` 新建通道实例）⇒ 本 feature 只承担**持久侧**的隔离 | `specs/b12f1-concurrency-errors/spec.md` FR-024 · 裁定 23（已作废）· 下游承接 D-5 · 回溯修订 T-7 | **FR-004** · **FR-018** · 裁定 7 · SC-003 |
| **H-3** | **B12F1 → B14F1** | **M3** | **「真异常 + 中断同现」时的中断留痕**：上游把中断元组写进 checkpoint 的 pending writes（`_runner.py:588-591`）⇒ 即便真异常优先抛出（`:687`），待审批项也留痕 ⇒ 本 feature MUST 让中断元组随 pending writes 落盘 ⇒ MUST NOT 把这件事当「新能力」宣传；MUST NOT 为此在异常上加附注 / 落调度状态字段 | `specs/b12f1-concurrency-errors/spec.md` FR-014 · 裁定 10 · SC-013 · 偏离登记 X-4（消解条件）· 下游承接 D-6 | **FR-021** · 裁定 10 · SC-018 |
| **H-4** | **B13F1 → B14F1** | **M3** | **静态挂起持久化**：MUST 能原样存取静态挂起的快照 + 调度账本（`interrupts=()` · `suspension_kind` · `static_ack` · `next` 可为空）⇒ MUST NOT 要求「静态挂起也必须有动态中断载荷」；fan-out 载荷 MUST 随调度账本一起保存 / 还原；**F-10 的完成快照由 B13F1 写一次**，本 feature 的每轮末快照 MUST NOT 与之重复 / 冲突 | `specs/b13f1-static-interrupt-recursion-limit/spec.md` FR-007 / FR-016 · 裁定 9 / 10 · 下游承接 D-5 | **FR-019** · 裁定 5 / 9 · SC-015 |
| **H-5** | **B11F1 → B14F1** | **M3** | **`Send` 的 pending writes**：由 `Send` 产生的调用 MUST 与普通调用同款地进入 pending writes（标准 `task_id` = 节点名；fan-out `task_id` = `f"{节点名}:{TaskId}"`）⇒ MUST NOT 为 fan-out 另立载体；MUST 接受「一轮一个节点可有多个任务」 | `specs/b11f1-send-fanout/spec.md` FR-005 / FR-009 / FR-020 · 下游承接 D-3 · F-13 / F-14 | **FR-020** · 裁定 6 · SC-016 |
| **H-6** | **B7F4 → B14F1** | **M3** | **跨 checkpoint 的屏障状态持久化**：MUST 让「屏障的已消费状态」跨 checkpoint 存活（否则暂停后恢复 ⇒ 屏障被重放 ⇒ 目标被重复触发）⇒ MUST NOT 自创持久化载体（沿用调度状态里的 `seen` / `versions_seen`） | `specs/b7f4-multisource-join/spec.md` 承接条款 D-4 · 登记项 PR-4 · FR-004 / FR-016 | **FR-019** · 裁定 9 · SC-017 |
| **H-7** | **B7F2 → B14F1** | **M3** | **编译期 checkpointer 类型校验**：B7F2 只接受 + 记录 + 不报错；本 feature MUST 补上游同款的编译期校验（`ensure_valid_checkpointer` ⇒ `TypeError`）⇒ 校验口径由本 feature 冻结；`CompiledGraph.checkpointer` 是只读交接面，MUST NOT 要求 B7F2 改写记录方式 | `specs/b7f2-compile/spec.md` 下游承接 D-4 · FR-016 · 裁定 7 · 偏离登记 X-4 · SC-015 · `langgraph/types.py:109-118` | **FR-010** · 裁定 2 · SC-013 |
| **H-8** | **B8F2 → B14F1** | **M3** | **`checkpoints` 档的真实数据源**：B8F2 的 `checkpoints` 档 v1 恒为空序列（无伪造事件）⇒ 本 feature MUST 提供「每创建一个 checkpoint 一条事件」的数据源，并复用 `_loop.py:631-636` / `debug.py:144` 的「checkpoint 事件 vs `get_state()` 同形」口径；`StreamSession` 在 v1 忽略 `checkpointer`（不读/写快照、不触发恢复）；⚠️ **B15F1 起（✅ 已交付）**：`checkpoints` 档 carve-out（有 saver + `thread_id` 时由 B15F1 的 `StreamCheckpointWriter` 写盘并产事件），其余六档不变 | `specs/b8f2-stream-modes/spec.md` 下游承接 D-2 · FR-017 · 裁定 5 | **FR-023** · 裁定 11 · SC-020 |
| **H-9** | **B8F3 → B14F1** | **M3** | **`context` 不持久化**：MUST NOT 把 `context` 写入 checkpoint、MUST NOT 在恢复时从快照还原 `context`；checkpoint 契约 MUST NOT 为 `context` 预留持久化字段或「内存态恢复」旁路；MUST 以「`context` 已接线、alias 已移除」为前提，MUST NOT 回退到 `configurable` 承载 `context` | `specs/b8f3-node-alias-context/spec.md` 下游承接 D-1 / D-3 · FR-003 / FR-008 / FR-009 · 裁定 5 | **FR-024** · 裁定 12 · SC-021 |
| **H-10** | **B18F1 → B14F1** | **M3** | **`checkpoint_id` 补值**：节点 span 接受运行期 `checkpoint_id`（v1 `None`），模型 / 工具 span 从节点 span 继承 ⇒ 本 feature 挂接 checkpointer 后 MUST 通过既有运行期接缝把当前 checkpoint 标识填入**节点 span** ⇒ MUST NOT 回改 `Span` 的 11 字段 · MUST NOT 要求 B18F1 重写子 span 继承 | `specs/b18f1-span-production/spec.md` 下游承接 D-4 · plan D-05 · tasks T057 | **FR-022** · 裁定 11 · SC-019 |
| **H-11** | **B7F3 → B14F1** | **M3** | **checkpointer 的落盘职责**：B7F3 只透传编译产物持有的 `checkpointer`（MUST NOT 自己落盘 / 自己实现 saver）⇒ 落盘与 `MemorySaver` 归本 feature ⇒ 「挂起 → 恢复」路径在本 feature 落地后有正式载体；未挂 checkpointer 时 `Command(resume=...)` MUST 继续抛 `InterruptError(reason="checkpointer_required")` | `specs/b7f3-invoke-full-state/spec.md` 下游承接 D-4 · 契约 CF-04 | **FR-007** · **FR-028** · 裁定 2 / 7 · SC-014 |
| **H-12** | **B1F1 / B2F1 → B14F1** | **M1** | **L1 已冻结的类型与协议，本 feature 只实现 / 消费**：`StateSnapshot` 8 字段、`Checkpointer` 8 方法、`RunConfig` 9 字段、`Span` 11 字段、`Interrupt` / `PregelTask` 的类型面**一字不动**；`Checkpointer.get_tuple` 的返回结构挂起本 feature 解冻 ⇒ **L1 符号面零改动** | `src/freegraph/contracts/types.py:260-311` · `src/freegraph/contracts/protocols.py:76-138` · `src/freegraph/contracts/trace.py:27-92` | **FR-001** · **FR-011** · **FR-012** · **FR-025** · 裁定 1 / 3 |

---

## 形态锁定裁定（本 feature 必办 · `/speckit.plan` 与 `/speckit.implement` MUST 照此执行）

### 裁定 1 · `MemorySaver` 的模块路径

**锁定**：规范入口 = **`freegraph.persistence.MemorySaver`**。

| 项 | 锁定值 |
|---|---|
| 包目录 | `src/freegraph/persistence/`（**L4** · 层注册表已登记） |
| 公开路径 | `from freegraph.persistence import MemorySaver` |
| 实现文件 | `src/freegraph/persistence/memory.py`（**内部实现细节**；公开符号 `MemorySaver` / `InMemorySaver` / `CheckpointTuple` 的兼容矩阵行按 **D-07** 由 **B24F1 / B25F1** 增加；B14F1 只更新 `Checkpointer` 行） |
| 上游兼容别名 | `freegraph.persistence.InMemorySaver is MemorySaver`（**同一对象** · 照抄上游 `memory/__init__.py:634` 的别名习惯；**不**是第二套实现） |
| 构造签名 | `MemorySaver(*, on_checkpoint: Callable[[StateSnapshot], None] \| None = None)` —— 无必填参数；`on_checkpoint` 是 H-8 的**数据源**（见裁定 11） |
| 导出面 | `freegraph.persistence.__all__` = `["MemorySaver", "InMemorySaver", "CheckpointTuple"]`（`CheckpointTuple` 见裁定 3） |
| 门面 | `freegraph.graph`（门面）**MUST NOT** 转出 `MemorySaver`（`facade-L1-L3` 例外**不覆盖 L4** · G18）⇒ 用户从 `freegraph.persistence` 直接注入 |

**理由**：① 层注册表已把 L4 固定为 `persistence`；② 门面不得 import L4（G18），故不放在 `freegraph.graph`；
③ 与上游 `langgraph.checkpoint.memory` 的「独立持久化子包」定位同构；④ 模块路径一旦锁定，
`harness/demo/graph_core.py` 的硬断言与 `harness/demo/README.md` 的待锁定清单随之关闭。

### 裁定 2 · `compile(checkpointer=...)` 的注入与编译期校验

**锁定**：注入用法 = `g.compile(checkpointer=MemorySaver())`（**既有 B7F2 关键字** · 不改名）；
编译期校验在 **L3 `compile()` 边界**完成（**MUST NOT** 让 L3 import L4 —— L3 低于 L4，向上 import 违规）。

| 传入值 | 编译期 | 运行期落盘 |
|---|---|---|
| `None` | 接受 | 不落盘 |
| `True` / `False` | **接受并原样记录**（上游 `ensure_valid_checkpointer` 同款 · `types.py:109-118`） | **不落盘**（v1 无子图继承语义 · C26 属 v2）⇒ 视为「无 saver」，MUST NOT 抛 `AttributeError` |
| 满足 `freegraph.contracts.Checkpointer` 的对象 | 接受 | 落盘 |
| 其它对象 / 字符串 / 数字 | **抛 `TypeError`**，消息点名「期望 `BaseCheckpointSaver` 等价物、`True`、`False` 或 `None`」 | —— |

- 校验用 **L1 的 `runtime_checkable` 协议**（`isinstance(obj, Checkpointer)`）⇒ **零 L1 符号新增**；
  校验函数是 **L3 私有实现**（前导下划线），不进公开面。
- `CompiledGraph.checkpointer` 的**记录方式零改动**（B7F2 冻结面）⇒ 本 feature 只在构造前插入校验。
- 该行为是 **B7F2 偏离登记 X-4 的消解**：B7F2 的差分场景 D-77（非 saver 对象被接受）在本 feature 后
  **改为 `TypeError`** ⇒ 必须在 `tests/differential/` 与 B7F2 的执行记录中同步（**不是**新增偏离）。

### 裁定 3 · 读侧载体：`CheckpointTuple`

> **2026-11-22 澄清轮 · 用户确认选项 A**（恰好 3 个字段 · 不加上游别名 / 第二套结构）。

**锁定**：`get_tuple(config)` 返回 **`freegraph.persistence.CheckpointTuple`**（`frozen=True, slots=True`），
**恰好三个公开字段**（与 B10F1 契约 §2 逐字对应）：

| 字段 | 类型 | 语义 |
|---|---|---|
| `snapshot` | `freegraph.contracts.StateSnapshot` | L1 的 **8 字段**快照（见裁定 5 / FR-012） |
| `pending_writes` | `tuple[tuple[str, str, Any], ...]` | `(task_id, channel, value)` 三元组 · 按 `(task_path, task_id, idx)` 升序（上游 `writes_sort_key`）· 只含该 checkpoint 的写入 |
| `scheduler` | `dict[str, Any]` | 调度账本（纯数据 · JSON 可序列化）· `put` 的 `metadata["scheduler"]` **原样** |

- **不新增** `.config` / `.checkpoint` / `.metadata` 字段 ⇒ 与上游 `CheckpointTuple` 的形态差异
  是**已冻结的跨 feature 契约**（B10F1 `checkpoint-contract.md` §2），不是本 feature 的偏离。
- `get_tuple` 查不到 ⇒ **返回 `None`**（不抛异常）⇒ B10F1 视为「没有挂起的中断」。

### 裁定 4 · 版本号：**双命名空间**，不得互相改写

本 feature 涉及两种**不同**的版本，MUST 严格区分：

| 命名空间 | 载体 | 类型 | 谁维护 | 用途 |
|---|---|---|---|---|
| **调度版本** | `metadata["scheduler"]["channel_versions"]` / `node_versions` / `versions_seen` | `int` | **L2 调度器**（B7F1） | **触发判定**（`version(s) > seen`） |
| **checkpoint 顺位** | `CheckpointTuple.snapshot.config.configurable["checkpoint_id"]` | 每线程单调递增的 32 位零填充十进制字符串 | **`MemorySaver`** | `get_tuple` 取指定快照 / `list` 排序 / `before` 过滤 / span 的 `checkpoint_id` |

- **锁定**：`MemorySaver.put` MUST **原样保存** `metadata["scheduler"]`，**MUST NOT** 重新编号、
  归一化或调用 `get_next_version` 改写调度版本 ⇒ ⇒ **触发判定所用的版本 == 持久化后的版本**（SC-004）。
- **锁定**（**2026-11-22 澄清轮 · 用户确认选项 A**）：`get_next_version(current, channel=None)`
  返回 **`int`**：`current is None ⇒ 1`；`isinstance(current, int) 且非 bool ⇒ current + 1`；
  其它 ⇒ `TypeError`。⇒ 与 **B7F1 的 `dict[str, int]` 通道版本**同命名空间
  （**MUST NOT** 返回上游 memory 的字符串形式）。
  关系：**SAME** 上游 `BaseCheckpointSaver.get_next_version` 的默认整数语义（`base/__init__.py:721-740`）；
  **DIFF** 上游 `InMemorySaver` 的字符串覆写（`memory/__init__.py:622-630`）⇒ 登记 **X-02**。
- **锁定**：checkpoint 顺位 id 由 `MemorySaver` 每线程从 `1` 开始递增，格式 `f"{n:032d}"`
  ⇒ 字典序 == 数值序 ⇒ `list` / `before` 可排序。上游用 `uuid6`（`_checkpoint.py:31,209`）
  ⇒ 登记 **X-01**（标准库无 uuid6；单调计数器更适合内存 saver）。
- **跨 feature 断言**：同一次运行中，`get_tuple().scheduler["channel_versions"][ch]` == 该轮
  `SchedulerState.channel_versions[ch]`（逐 key 相等）；`get_next_version(prev)` == `prev + 1`。

### 裁定 5 · 每轮快照的持久化策略与计数

> **2026-11-22 澄清轮 · 用户确认选项 A**（初始惰性写；挂起写计入该轮；`interrupt_after` 代替该轮每轮快照；
> 首轮前 `interrupt_before` 兼作初始快照；收敛空轮不写）。

**锁定**：`MemorySaver` 只是存储；**写盘时机**由运行期接线（本 feature 在 L2/L3 的既有
`run_graph` 路径中，用**鸭子类型**调用 saver，**不 import L4**）负责。

| 时机 | 写什么 | `next` | `interrupts` / `tasks` | 备注 |
|---|---|---|---|---|
| **初始（round 0）** | `put` | 第一轮将执行的节点名 | `()` / `()` | **惰性**：在第一个 `_run_round` **之前**写；若先命中 `interrupt_before`，则该挂起写**兼任初始快照**（不重复写） |
| **每轮执行完成** | `put` | **下一轮**将执行的节点名；收敛 ⇒ `()` | `()` / 本轮 `tasks`（**历史 / 流数据源**；⚠️ 自 **B15F1** 起，`get_state` / `get_state_history` / `stream(checkpoints)` 的 `tasks` 由读取层按上游 **next-tasks** 重建，**MUST NOT** 直接使用本字段） | 在**写入合并成功之后**写 ⇒ 失败轮不写 |
| **动态中断挂起** | `put` + `put_writes` | 挂起快照的 `next`（可为空） | 本轮中断 / `()` | **该写就是本轮的快照**（不再另写每轮快照）；**挂起快照的 `tasks` 恒为 `()`**（与 B10F1 的冻结挂起写一致） |
| **静态 `interrupt_before` 挂起** | `put` | 待执行节点名 | `()` / `()` | 若**此前无任何快照**，它**兼任初始快照** |
| **静态 `interrupt_after` 挂起** | `put` | `next` | `()` / `()` | **代替**该轮的每轮快照（不重复）；**挂起快照的 `tasks` 恒为 `()`** |
| **静态恢复完成（F-10）** | `put`（由 B13F1 写一次） | `()` | `()` / `()` | 本 feature 的每轮策略 MUST NOT 与之重复 / 冲突 |

> ⚠️ **自 B15F1 起（✅ 已交付 · B15F1）**：本 feature 存储的 `tasks`（「每轮完成态」/ 挂起 `()`）
> 保留为**历史 / 流数据源**；**`CompiledGraph.get_state` / `get_state_history` /
> `stream(checkpoints)` 的 `tasks` MUST 由读取层按上游 next-tasks 语义重建**
> （`snapshot.next` + `.scheduler["fanout"]` + pending `__interrupt__`），**MUST NOT** 直接使用
> `snapshot.tasks`。B8F2 的 `stream(tasks)` 仍是「每完成一个 task 一条」的完成态事件，二者
> 语义边界写死。此为 B15F1 于 **2026-11-23** 按宪法原则 XII「最优设计优先」+ 原则 XI「上游优先」
> 作出的**回溯修订**（**拆分而不删**：原存储口径保留）。

**计数判据**：
- **正常跑完**的图：快照数 == **实际执行过的 super-step 轮数 + 1**（初始）。
  「实际执行过」= 至少跑了一个节点；**收敛空轮不产生快照**。
- **动态中断挂起**：快照数 == **含挂起轮在内的已执行轮数 + 1**（初始 + 每轮一个；挂起轮一个）。
- **静态挂起**：挂起快照**计入**该轮的快照；`interrupt_before` 在首轮前命中时，
  挂起快照**就是**初始快照 ⇒ 快照数 == **0 + 1**。
- 该策略 MUST NOT 改变图的**状态 / 节点执行次数 / 返回 dict**（SC-005）。

### 裁定 6 · `put` / `put_writes` 的写入语义

**锁定（读侧 / 写侧关键字逐字）**：

```
put(config, *, values, metadata) -> RunConfig
put_writes(config, *, writes, task_id, task_path="") -> None
```

- `put`：
  - `values` MUST 是 `Mapping` ⇒ 存**深拷贝**；`metadata` MUST 是 `Mapping` ⇒ 存**深拷贝**；否则 `TypeError`。
  - 为当前 `thread_id` 生成**新的 checkpoint 顺位 id**，`parent_config` = 上一快照的 `config`（首个为 `None`）。
    > ⚠️ **回溯修订（B16F1 · 2026-11-23 · 拆分而不删）**：自 B16F1 起，当
    > `config.configurable["checkpoint_id"]` 为**非空字符串**时，`parent_config` = 该 id
    > （显式父链，用于时间旅行分叉）；缺失 / 空串仍保持「上一快照（最新）」原语义。
    > 运行期常规写盘携带「当前 checkpoint id」作 parent，可观察行为不变。
    > 新口径见 `specs/b16f1-update-state-time-travel/spec.md` 裁定 3 / FR-017 / R-2。
  - 返回一个新的 `RunConfig`，其 `configurable["checkpoint_id"]` = 新 id（**上游同款**：`put` 返回带 id 的 config）；
    `thread_id` = 生效的 `thread_id`；`context` = `None`（见裁定 12）；**不**复制 `metadata` / `tags`。
  - 新快照的 8 字段按 FR-012 组装：`values` / `next` / `config` / `metadata` / `created_at` /
    `parent_config` / `tasks` / `interrupts`；后四者从 `metadata` 的 `next` / `tasks` / `interrupts` 取，
    缺省分别为 `()` / `()` / `()`；`metadata` 字段 = 原 `metadata` 深拷贝；`created_at` = 当前 UTC ISO-8601。
- `put_writes`：
  - `writes` = `(channel, value)` 对的序列；`channel` MUST 是 `str`；`task_id` MUST 是非空 `str`；
    `task_path` 缺省 `""`（内部保存，**不**出现在 `.pending_writes` 三元组里）。
  - 目标快照 MUST 由 `config.configurable["checkpoint_id"]` 指定（**上游同款**）：
    缺该 key ⇒ `KeyError`；该 id 在本线程不存在 ⇒ `ValueError`（更明确的失败信号 · 登记 **X-07**）。
    **MUST NOT** 隐式回退到「最新快照」⇒ **不**隐式创建快照。
  - 去重键**逐字照抄上游**：`inner_key = (task_id, WRITES_IDX_MAP.get(channel, idx))`
    （`WRITES_IDX_MAP = {__error__: -1, __scheduled__: -2, __interrupt__: -3, __resume__: -4}` ·
    `base/__init__.py:815-824`）。普通通道 `idx` = 本次调用内的位置 ⇒ 跨调用同 `(task_id, idx)`
    **首次写入生效**（后续忽略）；保留通道 ⇒ 负索引 ⇒ **最后一次生效**（覆盖，**同一次调用内也覆盖**）。
  - `.pending_writes` 返回**上游同款排序**：按 `(task_path, task_id, idx)` 升序
    （`writes_sort_key` · `base/__init__.py:185-196`）；值存**深拷贝**。
- `list(config=None, *, filter=None, before=None, limit=None)`：
  - `config=None` ⇒ 全部线程（`thread_id` 按存储**插入序** · 上游同款、不排序；同线程 checkpoint id **降序**）；
    `config` 有 `thread_id` ⇒ 只列该线程；`config.configurable["checkpoint_id"]` 有值 ⇒ 只列该 id。
  - `filter` 按 `metadata` 顶层 key 精确匹配（AND）；`before` 排除 id **>= before 的 id**（同线程）；
    `limit <= 0` ⇒ 空；否则最多 `limit` 条。返回**迭代器**（上游 `list` 同款）。
- `get_tuple(config)`：`configurable["checkpoint_id"]` 有值 ⇒ 取该快照（不存在 ⇒ `None`）；
  否则取该线程**最新**快照。`.pending_writes` 只含该快照的写入。
- `delete_thread(thread_id)`：删除该线程的**全部**快照 + 写入 + 内部状态；幂等；不影响其它线程；
  之后 `get_tuple` ⇒ `None`、`list` ⇒ 空。
- `delete_for_runs(run_ids)` / `copy_thread(source, target)`：**存在**（协议结构性要求），
  v1 **抛 `NotImplementedError`**（上游 `InMemorySaver` 未覆写、由基类抛出 · `base/__init__.py:355,374`）
  ⇒ 登记 **SAME**；本 feature **不**实现运行级删除 / 线程复制（属 B15F1 / B16F1 的存储后端职责）。

### 裁定 7 · `thread_id` 缺失 / 无效时的行为

> **2026-11-22 澄清轮 · 用户确认选项 A**（运行期跳过落盘；直接调用 saver 抛 `ValueError`）。

- **运行期**（`invoke` / `run_graph`）：生效 `thread_id`（`RunConfig.resolved_thread_id()`）为
  `None` / 空串时，**跳过全部 saver 调用**（不 `get_tuple`、不 `put`、不 `put_writes`）
  ⇒ ⇒ 图照常执行，结果与未注入 checkpointer **一致**（SC-005）⇒ **MUST NOT** 静默把 `None` 当成一个共享会话。
- **直接调用 `MemorySaver`**：`get_tuple` / `put` / `put_writes` / `list(config)` 遇到缺失
  `thread_id` ⇒ 抛 **`ValueError`**（点名 `thread_id`）；`list(None)` 不需要 `thread_id`。
  ⇒ 与上游「缺 `thread_id` 时明确失败（实测 `ValueError`）」的差异登记 **X-03**（更明确的失败信号）。
- `delete_thread` 的 `thread_id` MUST 是 `str`；非 `str` ⇒ `TypeError`。

### 裁定 8 · 隔离、拷贝与纯数据

- **线程隔离**：存储键至少含 `thread_id`；不同 `thread_id` 的快照 / 写入 / 计数器**互不可见**。
- **防御性拷贝**：`put` / `put_writes` 存入**深拷贝**；`get_tuple` / `list` 返回**深拷贝**
  （`snapshot` / `pending_writes` / `scheduler` 中的可变容器都不与内部存储共享）
  ⇒ 调用方修改返回值 MUST NOT 污染已存快照，也 MUST NOT 跨线程串扰。
- **可拷贝前提**：载荷 MUST 可被标准库 `copy.deepcopy`；不可拷贝的对象 ⇒ 原异常传播
  （**MUST NOT** 静默退化为共享引用）。`scheduler` 由 B10F1 保证 **JSON 可序列化**的纯数据；
  `MemorySaver` **不**额外做 JSON 编码（上游用 msgpack，本 feature 用深拷贝 ⇒ 登记 **X-05**）。
- **线程安全**：`MemorySaver` 的公开方法 MUST 在**每实例一把 `threading.RLock`** 下串行化
  （`on_checkpoint` 回调在释放锁**之后**调用）；并发 `put` / `get_tuple` / `list` / `delete_thread`
  MUST NOT 导致 `RuntimeError` 或数据串扰。
- **回调隔离**：`on_checkpoint` 抛出的异常 MUST NOT 传播给 `put` 的调用方、MUST NOT 回滚已提交的快照
  ⇒ 「一个观察者坏了不能拖垮落盘」（与 trace sink 的失败隔离同款）。

### 裁定 9 · 静态挂起 / fan-out / 屏障的**原样存取**

- `.snapshot.interrupts` 与 `.snapshot.tasks` 从 `metadata` 的 `interrupts` / `tasks` 取；
  **静态挂起允许 `interrupts == ()` 且 `next == ()`** ⇒ MUST NOT 要求「必须有动态中断载荷」。
- `.scheduler` MUST 原样保存 / 还原 `suspension_kind` / `static_ack` / `fanout` / `versions_seen` /
  `channel_versions` / `node_versions` / `dynamic_edges` 的全部既有键（含**屏障的 `seen`**）。
  ⇒ 屏障恢复后目标 MUST NOT 被重复触发（SC-017）。
- `task_id` 口径：标准任务 = **节点名**；fan-out = **`f"{节点名}:{TaskId}"`**
  ⇒ 同一轮同一节点可有**多个** `task_id` ⇒ MUST NOT 假设「一轮一个节点一个任务」。
- fan-out 载荷（目标 + 原样入参 + TaskId）MUST 随调度账本一起保存 / 还原；
  `MemorySaver` **不**解释 fan-out 结构（**不透明载荷**）。

### 裁定 10 · 「真异常 + 中断同现」的中断留痕

- 运行期在同一轮里既收集到**真异常**又收集到**中断**时，MUST **先**把该轮的每个中断元组
  经 `put_writes` 写入**该轮起点所用的 checkpoint**（失败轮不新建快照；`task_id` = 对应节点名 / fan-out task key；
  `channel = "__interrupt__"`；`value` = 该任务的中断元组），**然后**原样抛出真异常。
- 真异常的**类型 / 消息 / 对象 identity** MUST NOT 改变；MUST NOT **为中断留痕**用
  `add_note` / 调度状态字段「自创留痕」⇒ 该行为的唯一载体 = **pending writes**
  （上游同款 · `_runner.py:588-591`）；⚠️ B12F1 既有的其余并发失败附注
  （`attach_failure_notes` · X-2）是**另一件事**，MUST 保留。
- 该轮若尚无 `put`（失败轮不合并）⇒ pending writes 附着在**上一轮**（或初始）checkpoint 上
  ⇒ `get_tuple` 能读到 ⇒ **B10F1 / B12F1 的 X-5 / X-4 自动消解**。
- MUST NOT 把本项宣传为「新能力」——它只是上游本来就这样。

### 裁定 11 · `checkpoint_id` 进节点 span + `checkpoints` 事件数据源

- **span**：运行期 MUST 维护「当前 super-step 起点所用的 checkpoint id」（初始快照 id；
  后续轮 = 上一轮落盘后的 id）⇒ 通过 `start_node_span(..., checkpoint_id=<id>)` 的**既有参数**
  填入**节点 span**；模型 / 工具 span 继续从节点 span 继承。`Span` 的 11 字段**零改动**；
  未挂 checkpointer / `thread_id` 缺失 ⇒ `checkpoint_id is None`（合法现状）。
- **事件数据源**（**2026-11-22 澄清轮 · 用户确认选项 A**）：`MemorySaver` MUST 提供两条同源出口：
  1. `on_checkpoint(snapshot: StateSnapshot)` 构造参数（可选）——**每次成功的 `put` 恰调用一次**；
  2. `list()` 的历史枚举。
  ⇒ 两者给出的快照 MUST 与 `get_tuple().snapshot` **同形**（8 字段 · 同 id · 同 values / next / tasks / interrupts）。
- **边界**：本 feature **只交付数据源**；`stream(..., stream_mode="checkpoints")` 的**消费端接线**
  仍归 **B8F2 / B15F1**（B8F2 v1 忽略 `checkpointer`；⚠️ **B15F1 起（✅ 已交付）** `checkpoints` 档 carve-out）
  ⇒ 本 feature MUST NOT 伪造 stream 事件，
  MUST NOT 在 `StreamSession` 里另立一条 checkpoint 路径。该边界列入 **Out of Scope**（能力边界 · **非偏离**）。

### 裁定 12 · `context` 不持久化

- `MemorySaver` MUST NOT 读取、保存、还原、透出 `RunConfig.context`；
  `snapshot.config.context` MUST 为 `None`；`metadata` MUST NOT 由本 feature 注入 `context`。
- 恢复路径的 `context` 由调用方本次传入的 `RunConfig` 决定（B8F3 已接线）⇒ **不**从快照还原。
- MUST NOT 把 `context` 塞进 `snapshot.config.configurable`；MUST NOT 回退到 `configurable` 承载 `context`。

### 裁定 13 · `MemorySaver` 的失败信号（不新增异常类型）

- 非法参数（非 `Mapping` / 非 `str` / 缺 `thread_id` /
  `put_writes` 缺 `checkpoint_id` / 指定 id 不存在 /
  `get_next_version` 的非法 `current`）⇒ 使用**内置** `TypeError` / `ValueError` / `KeyError`
  （`put_writes` 缺 `checkpoint_id` 逐字上游 ⇒ `KeyError`；其余点名参数）。
- 不做 I/O、不读环境变量、不联网 ⇒ 不存在 `OSError` / 超时 / 权限类失败。
- 深拷贝失败 ⇒ 原异常传播（不包装）。
- **MUST NOT** 新增 L1 异常类型（B1F1 的异常面零改动）。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 每一步的状态都被记下来了（Priority: P1）

作为用户，我跑完一张图后，希望能在**每一步**看到状态快照，从而复盘状态如何演进。

**Why this priority**：这是本 feature 的**判定核心**——「快照持久化」若不可用，后续所有状态历史 /
时间旅行都无从谈起。

**Independent Test**：用 `MemorySaver` 跑一张两节点的顺序图（`a → b`），
`list(RunConfig(thread_id="t"))` 的长度为 **3**（初始 + `a` 后 + `b` 后），
且每条的 `values` 与对应轮次的稀疏状态一致。

**Acceptance Scenarios**：

1. **Given** 一张 `a → b` 的图与 `thread_id="t"`，**When** `invoke` 正常跑完，
   **Then** 历史快照数 == 实际执行轮数 + 1，且最后一条 `next == ()`。
2. **Given** 同一张图，**When** 不注入 checkpointer 跑完，**Then** 无任何快照被创建，
   且返回的完整状态与注入时**逐字段相等**。
3. **Given** 两次不同 `thread_id` 的运行，**When** 分别 `list`，**Then** 各自只看到自己的快照。

---

### User Story 2 - 未落地的写入也被记下来了（Priority: P1）

作为实现者，我需要 pending writes 被单独保存，以便崩溃后能重放。

**Why this priority**：快照与 pending writes 是**两种不同的数据**；只存快照会丢失
「哪些任务的哪些写入还没合并」。

**Independent Test**：`put(config, values={"x": 1}, metadata={...})` 后，
`put_writes(config, writes=[("x", 2)], task_id="n", task_path="n")`，
`get_tuple(config).pending_writes == (("n", "x", 2),)`；快照的 `values` 仍为 `{"x": 1}`
（**分层**：写入不合并进快照）。

**Acceptance Scenarios**：

1. **Given** 一个已 `put` 的线程，**When** `put_writes` 写入 `(task_id, channel, value)`，
   **Then** `get_tuple` 返回的 `.pending_writes` **逐三元组**相等。
2. **Given** 同一 `(task_id, channel)` 被普通通道写入两次，**When** 取回，
   **Then** **首次**写入生效；保留通道 `__interrupt__` / `__resume__` 则**最后一次**生效。
3. **Given** 一个不存在的线程，**When** 直接 `put_writes`，**Then** 抛 `ValueError`（点名先 `put`）。

---

### User Story 3 - 按 thread 隔离不同会话（Priority: P1）

作为用户，我同时跑两个会话，希望它们的 checkpoint **互不干扰**。

**Why this priority**：B12F1 的 D-5 明确把**持久侧**的会话隔离归本 feature；
隔离破坏 = 会话串扰 = 数据污染。

**Independent Test**：`thread-1` 与 `thread-2` 各写两条快照；
`get_tuple` / `list` 只看到自己的；`delete_thread("thread-1")` 后 `thread-2` 的数据**逐字节不变**。

**Acceptance Scenarios**：

1. **Given** `thread-1` 与 `thread-2` 各有数据，**When** 分别 `get_tuple`，
   **Then** 返回的 `.snapshot.values` / `.pending_writes` 互不可见。
2. **Given** `thread-1` 有多条快照，**When** `delete_thread("thread-1")`，
   **Then** 该线程的快照 + 写入清零，`thread-2` 不受影响。
3. **Given** 两个线程并发 `put` / `get_tuple`，**When** 结束后检查，**Then** 无串扰、无异常。

---

### User Story 4 - 挂起后用真实的 `MemorySaver` 恢复（Priority: P2）

作为用户，我在节点里 `interrupt("approve?")` 挂起后，希望通过 `Command(resume="yes")`
从节点起点重跑并拿到恢复值——**恢复必须走 checkpointer**。

**Why this priority**：宪法原则 IV 已拍板「恢复 MUST 挂 checkpointer」；
本 feature 是该决策的**第一个可用载体**（B10F1 的 V-1 人工验证承接）。

**Independent Test**：`app = g.compile(checkpointer=MemorySaver())`；
第一次 `invoke(..., cfg)` 挂起；第二次 `invoke(Command(resume="yes"), cfg)` 跑完，
返回含 `answer=yes`，且**只重跑被中断节点、并从该节点起点重跑**（图不从起点重跑），
`interrupt()` 之后的代码只执行一次。

**Acceptance Scenarios**：

1. **Given** 一个会 `interrupt` 的节点与同一 `thread_id`，**When** 首次 `invoke` 挂起，
   **Then** 快照 + `__interrupt__` 待写入都已落盘。
2. **Given** 上述挂起态，**When** `invoke(Command(resume="yes"), cfg)`，
   **Then** **只重跑被中断节点**（从该节点起点重跑）、拿到 `resume` 值并跑完；
   **已完成节点不重复执行**；历史快照继续追加。
3. **Given** 未挂 checkpointer，**When** `invoke(Command(resume=...))`，
   **Then** 抛 `InterruptError(reason="checkpointer_required")`（**原样传播**）。

---

### User Story 5 - 静态挂起 / fan-out / 屏障跨 checkpoint 存活（Priority: P2）

作为实现者，我需要静态挂起（`interrupt_before` / `interrupt_after`）、`Send` fan-out
与多源屏障的现场能被原样存取，恢复后不重复触发、不丢任务。

**Why this priority**：B13F1 / B11F1 / B7F4 的 D-5 / D-3 / D-4 把这三类现场**指名**交给本 feature。

**Independent Test**：带静态断点的图挂起后 `get_tuple`，`.scheduler` 含
`suspension_kind` / `static_ack` / `fanout` / `versions_seen`；恢复后完成快照**只写一次**，
且屏障目标未被重复触发。

**Acceptance Scenarios**：

1. **Given** `interrupt_before=["b"]` 且 `a` 已跑完，**When** 挂起后 `get_tuple`，
   **Then** `.snapshot.next` 指向 `b`，`.scheduler["suspension_kind"] == "static_before"`，
   `.snapshot.interrupts == ()`。
2. **Given** 一个 `Send` fan-out 产生两个任务，**When** 挂起后检查 pending writes，
   **Then** 两个 `task_id` 分别为 `f"{node}:{id}"`，**不**共用节点名。
3. **Given** 一个多源屏障，**When** 在屏障前暂停再恢复，
   **Then** 已消费的 `seen` 保留，屏障目标**不**被第二次触发。

---

### User Story 6 - `checkpoint_id` 可关联到 span 与事件（Priority: P3）

作为用户，我希望每个节点 span 与每条 checkpoint 事件都带同一个 `checkpoint_id`，
从而把 trace 与状态历史对齐。

**Why this priority**：B18F1 的 D-4 与 B8F2 的 D-2 把这两个可观测出口指名交给本 feature；
它们是「可诊断」的关联键，但不影响主执行语义。

**Independent Test**：挂 `MemorySaver` + tracer 跑一张单节点图，
节点 span 的 `checkpoint_id` 非 `None` 且等于最新快照 config 里的 id；
构造时传 `on_checkpoint`，回调次数 == `put` 次数，载荷与 `get_tuple().snapshot` 同形。

**Acceptance Scenarios**：

1. **Given** 挂了 checkpointer + tracer，**When** 跑一个节点，**Then** 节点 span 的
   `checkpoint_id` == 该轮起点快照的 id；子 span 继承同一个值。
2. **Given** 未挂 checkpointer，**When** 跑同一张图，**Then** 节点 span 的
   `checkpoint_id is None`（合法 · 不伪造）。
3. **Given** 构造时传 `on_checkpoint`，**When** 每次 `put` 成功，
   **Then** 回调恰收到一条与 `get_tuple().snapshot` 同形的快照；回调抛错不影响落盘。

---

### Edge Cases

- **未知线程**：`get_tuple` ⇒ `None`；`list` ⇒ 空；`delete_thread` ⇒ 幂等、不抛。
- **空写入**：`put_writes(writes=[])` ⇒ 合法，不新增三元组。
- **无 checkpoint 的写入**：`put_writes` 缺 `checkpoint_id` ⇒ `KeyError`（上游同款）；
  指定 id 不存在 ⇒ `ValueError`（X-07）；**不隐式建快照、不取最新**。
- **重复写入**：普通通道跨调用同 `(task_id, idx)` 首次生效；保留通道最后一次生效
  （**同一次调用内也覆盖**）；普通通道同一次调用内的不同 `idx` 全保留。
- **`metadata` 缺键**：`next` / `interrupts` / `tasks` / `scheduler` 缺失 ⇒ 分别按 `()` / `()` / `()` / `{}` 处理。
- **`next` / `interrupts` / `tasks` 为 list**：归一为 `tuple`；`scheduler` 保持 `dict`。
- **`values` / `metadata` 非 `Mapping`**：`TypeError`（点名参数）。
- **深拷贝失败**：原异常传播，存储不留下半成品（一次 `put` 要么完整提交，要么完全不变）。
- **`thread_id` 缺失**：运行期跳过落盘；直接调用 saver ⇒ `ValueError`。
- **`thread_id` 为 `""`**：同「缺失」处理（空串不是合法会话标识）。
- **`get_next_version`**：`None ⇒ 1`；`0 ⇒ 1`；`k ⇒ k+1`；`"1"` / `True` ⇒ `TypeError`。
- **checkpoint id 排序**：`f"{n:032d}"` 的字典序与数值序一致；`before` 用同线程 id 比较。
- **`list(before=...)`**：排除 `id >= before_id` 的项；`before` 指向不存在的 id ⇒ 按字符串比较，不抛。
- **`list(limit=0)` / 负值**：空序列。
- **`list(filter=...)`**：只匹配 `metadata` 顶层 key；值按 `==` 比较。
- **`delete_thread` 后重建**：同 id 重新 `put` ⇒ 新线程、计数器从 1 开始、无旧数据。
- **`copy_thread` / `delete_for_runs`**：存在但抛 `NotImplementedError`（v1 边界）。
- **编译期非法 checkpointer**：`object()` / `"saver"` / `0` / `[]` ⇒ `TypeError`。
- **`checkpointer=True` / `False`**：编译接受、原样记录；运行期不落盘、不抛 `AttributeError`。
- **`checkpointer=None`**：运行期零 saver 调用；返回状态与注入时一致。
- **`context` 非空**：不得出现在 `snapshot.config` / `.scheduler` / pending writes 中。
- **静态挂起且 `interrupts=()`**：合法，不得被误判为「无挂起」。
- **`interrupt_before` 首轮前命中**：挂起快照兼任初始快照，快照数 == 1。
- **`interrupt_after` 命中**：挂起快照代替该轮每轮快照，不重复。
- **真异常 + 中断同现**：pending writes 有中断；抛出的异常对象 identity / 类型 / 消息不变。
- **fan-out 同轮多任务**：同一节点名可对应多个 `task_id`；不得互相覆盖。
- **屏障暂停恢复**：`seen` 保留；目标不重复触发。
- **回调抛错**：不影响 `put` 的返回值与已提交快照。
- **回调内再调用 saver**：锁已释放 ⇒ 不死锁（重入安全）。
- **并发**：两个线程同时 `put` / `get_tuple` ⇒ 串行化，无数据串扰。
- **上游版本漂移**：换 `langgraph` 版本后，本 spec 的全部行号 MUST 重新核实。

---

## Upstream Parity *(mandatory — 宪法原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11**（取证于 **2026-11-22** · 本仓库 `.venv`）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | 内存 saver 入口与别名 | `checkpoint/memory/__init__.py:34`（`InMemorySaver`）· `:634`（`MemorySaver = InMemorySaver`） | `freegraph.persistence.MemorySaver`；`InMemorySaver` 为同一对象别名（**模块路径由层注册表固定为 L4**；包名差异非行为偏离） | SAME | 层注册表固定 L4 = `persistence` |
| P-02 | pending write 三元组 / 排序 | `checkpoint/base/__init__.py:32`（`PendingWrite = tuple[str, str, Any]`）· `:185-196`（`writes_sort_key`） | `(task_id, channel, value)` 三元组；顺序按 `(task_path, task_id, idx)` 升序 | SAME | B10F1 契约 §2 · 实测 1.2.11 |
| P-03 | `get_tuple` 取最新 / 按 id | `checkpoint/memory/__init__.py:239-320` | 取最新；`configurable["checkpoint_id"]` 有值则取指定；不存在 ⇒ `None` | SAME | 上游同款 |
| P-04 | `list` 顺序 / 过滤 | `checkpoint/memory/__init__.py:321-427` | `config=None` 时线程按存储**插入序**；同线程 id 降序；`filter` / `before` / `limit` 同款 | SAME | 上游同款 · 实测 1.2.11 |
| P-05 | `put` 写快照 + 父链 + 返回新 config | `checkpoint/memory/__init__.py:430-473` · `:459` | 写快照 + `parent_config`；返回带新 `checkpoint_id` 的 `RunConfig`（关键字由 B10F1 冻结为 `values` / `metadata`，**属跨 feature 契约、非行为偏离**） | SAME | 跨 feature 契约已冻结 |
| P-06 | `put_writes` 去重 / 覆盖 | `checkpoint/memory/__init__.py:476-512` · `checkpoint/base/__init__.py:815-824`（`WRITES_IDX_MAP`） | 去重键 `(task_id, WRITES_IDX_MAP.get(channel, idx))`；普通通道跨调用同 `(task_id, idx)` 首次生效；保留通道最后生效（**同调用内也覆盖**） | SAME | 上游同款 · 实测 1.2.11 |
| P-07 | `delete_thread` | `checkpoint/memory/__init__.py:514-528` | 删除该线程快照 + 写入 + 内部状态；幂等 | SAME | 上游同款 |
| P-08 | `delete_for_runs` / `copy_thread` | `checkpoint/base/__init__.py:355-388`（基类 `NotImplementedError`）· `memory/__init__.py` 未覆写 | 方法存在；v1 抛 `NotImplementedError` | SAME | 上游内存 saver 同样未实现 |
| P-09 | `get_next_version` | `checkpoint/base/__init__.py:721-740`（默认 `int+1`）· `memory/__init__.py:622-630`（字符串覆写） | `int+1`（`None ⇒ 1`） | DIFF（X-02） | 与 B7F1 的 `dict[str, int]` 同命名空间；**不**照抄 memory 的字符串覆写 |
| P-10 | checkpoint id 生成 | `pregel/_checkpoint.py:31,209`（`uuid6(clock_seq=step)`） | 每线程单调递增 32 位零填充十进制字符串 | DIFF | 标准库无 uuid6；内存 saver 用计数器即可排序 ⇒ **X-01** |
| P-11 | `StateSnapshot` 8 字段 | `langgraph/types.py:684-701` | L1 `StateSnapshot` 8 字段逐字同构 | SAME | B1F1 已冻结 |
| P-12 | 保留通道名 | `langgraph/_internal/_constants.py:9,11,13,17`（`INTERRUPT` / `RESUME` / `ERROR` / `SCHEDULED`） | `__interrupt__` / `__resume__` 逐字；`__error__` / `__scheduled__` 同款保留 | SAME | B10F1 契约 §5 |
| P-13 | 真异常 + 中断同现时中断留痕 | `pregel/_runner.py:588-591`（中断写 pending writes）· `:687`（真异常先抛）· `:690`（合并中断） | 先 `put_writes(__interrupt__, ...)`，再原样抛真异常 | SAME | 消解 B10F1 X-5 / B12F1 X-4 |
| P-14 | `checkpoints` 事件数据源 | `pregel/_loop.py:631-636`（`_emit("checkpoints", map_debug_checkpoint, ...)`）· `debug.py:144-185`（事件 vs `get_state()` 同形） | `on_checkpoint` + `list()` 提供同形数据源；stream 消费端归 B8F2 / B15F1 | SAME | D-2 只要求数据源；消费端接线属 Out of Scope（能力边界 · 非偏离） |
| P-15 | 编译期 checkpointer 校验 | `types.py:109-118`（`ensure_valid_checkpointer`）· `graph/state.py:1179,1234` | 接受 `None` / `True` / `False` / 满足 L1 `Checkpointer` 的**鸭子类型**对象；其它 ⇒ `TypeError` | DIFF（X-08） | **比上游更宽松**：上游要求 `BaseCheckpointSaver` 子类，freegraph 用 `runtime_checkable` 协议（零依赖必然取舍） |
| P-16 | 线程隔离的存储键 | `checkpoint/memory/__init__.py:93`（`storage[thread_id][checkpoint_ns][checkpoint_id]`） | `thread_id` 为一级键；不同线程互不可见 | SAME | B12F1 D-5 |
| P-17 | `MemorySaver` 的开发 / 调试定位 | `checkpoint/memory` 的文档与上游实践（仅内存、进程结束即丢失） | 明确定位为开发 / 调试；生产归 B15F1 | SAME | 发起者 2026-11-05 拍板 |
| P-18 | 缺失 `thread_id` | 上游挂 checkpointer 但缺 `thread_id` ⇒ 明确失败（实测 1.2.11 抛 `ValueError`；部分入口为 `KeyError`） | 运行期跳过落盘；直接调用 saver ⇒ `ValueError` | DIFF（更明确 / 更宽容） | SC-005（注入不改变执行结果）⇒ **X-03** |
| P-19 | `context` 的持久化 | 上游 `RunnableConfig` 可携带任意 `configurable`，checkpoint 会保存 config | 明确**不**持久化 `context`；`snapshot.config.context is None` | DIFF | B8F3 D-1 / D-3 ⇒ **X-04** |
| P-20 | 序列化 / 拷贝 | 上游 msgpack serde（`memory/__init__.py:93` 的 `serde`） | 标准库 `copy.deepcopy`（进程内内存实现） | DIFF | 零第三方依赖；B15F1 再做序列化 ⇒ **X-05** |
| P-21 | `checkpointer=True` / `False` 的**运行期**语义 | `types.py:100`（`Checkpointer` = `None` 或 `bool` 或 `BaseCheckpointSaver`）· `pregel/main.py:2579-2583`（`False` / `True` 的运行期分支） | 编译接受并记录；运行期视为「无 saver」（v1 无子图 · C26 属 v2） | DIFF | 保持 B7F2 的记录面不破；避免运行期 `AttributeError` ⇒ **X-06** |

### 差分场景组 *(mandatory — 落 `tests/differential/`)*

> 上游缺席 ⇒ **skip**（沿用 B5F2 / B9F1 的「缺席即 skip」纪律）；CI 的 Linux 全量档真跑。
>
> ⚠️ **上游的额外起点快照**：`langgraph 1.2.11` 的 `InMemorySaver` 会额外保存一个
> `__start__` checkpoint（`metadata["step"] == -1`）；差分比较「实际 super-step 快照」
> 时 MUST **排除**它（否则两边计数稳定差 1）。

| # | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 |
|---|---|---|---|
| D-01 | 单节点图 + `MemorySaver` | 完成；快照数 == 1 + 1；`next=()` | SAME |
| D-02 | `a → b` 两节点图 | 完成；快照数 == 2 + 1；每轮 `values` 稀疏状态一致 | SAME |
| D-03 | `get_tuple` 取最新 / 指定 id | 两者返回的 `values` / `next` 与预期一致；未知 id ⇒ `None` | SAME |
| D-04 | `put_writes` 去重 / 覆盖 / 排序 | 普通通道跨调用同 `(task_id, idx)` 首次生效；保留通道最后生效（**同调用内也覆盖**）；`.pending_writes` 按 `(task_path, task_id, idx)` 升序 | SAME |
| D-05 | 两个 `thread_id` 并行 | 互不可见；`delete_thread` 只清一个 | SAME |
| D-06 | `list` 的 `filter` / `before` / `limit` | 结果集合 / 顺序 / 长度与上游同款；`config=None` 线程按**插入序** | SAME |
| D-07 | `interrupt` → `Command(resume=...)` | 完成；**只重跑被中断节点且从该节点起点重跑**；拿到 resume 值；已完成节点不重复执行 | SAME |
| D-08 | `interrupt_before` 挂起 → 恢复 | 挂起快照（`interrupts=()`）可恢复；完成快照只写一次 | SAME |
| D-09 | `Send` fan-out 挂起 | 多任务 `task_id` 各自唯一；pending writes 去重 / 排序与上游同款 | SAME |
| D-10 | 多源屏障暂停 → 恢复 | 目标不重复触发；`seen` 保留 | SAME |
| D-11 | 真异常 + 中断同现 | 抛真异常；pending writes 含中断元组 | SAME（上游留痕） |
| D-12 | 非法 checkpointer 编译 | 上游 `TypeError`；freegraph `TypeError` | SAME（B7F2 X-4 消解） |
| D-13 | `checkpointer=True` / `False` | 编译接受、记录；运行期不落盘；不抛 `AttributeError` | DIFF（X-06 · v1 无子图继承） |
| D-14 | 缺失 `thread_id` + checkpointer | 上游明确失败（实测 1.2.11 抛 `ValueError`）；freegraph 正常执行且不落盘 | DIFF（X-03） |
| D-15 | 非空 `context` | 上游可能写入 config；freegraph 快照中 `context is None` | DIFF（X-04） |

### 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-01** | 自研区（内存实现细节） | P-10：checkpoint id 用每线程单调计数器，非上游 `uuid6` | 标准库无 `uuid6`；`f"{n:032d}"` 字典序 == 数值序，满足 `list` / `before`；换 B15F1 时 id 由 SQLite 后端自定 | 本 feature · B15F1 知情 |
| **X-02** | 自研区（版本命名空间） | P-09：`get_next_version` 返回 `int`，非上游 `InMemorySaver` 的字符串 | B7F1 的调度版本是 `int`；双命名空间会让「触发判定所用版本」与「持久化版本」漂移 ⇒ **统一为 int** | 本 feature · B15F1 知情 |
| **X-03** | 更明确的失败信号 / 更宽容的落盘 | P-18：缺失 `thread_id` 时运行期跳过落盘、直接调用 saver 抛 `ValueError`（上游明确失败 · 实测 `ValueError`） | SC-005 要求「注入 checkpointer 不改变执行结果」；无 `thread_id` 时无法定义会话，静默共享会话更危险 | 本 feature |
| **X-04** | 破已冻结契约面（B8F3 的 D-1 / D-3） | P-19：`context` **不**持久化（上游 config 可携带） | B8F3 已拍板 `context` 是运行期上下文、不是持久状态；B14F1 MUST NOT 为它预留字段 | **B8F3**（上游已冻结）· 本 feature **只执行** |
| **X-05** | 自研区（内存实现细节） | P-20：用 `copy.deepcopy` 而非 msgpack serde | 零第三方依赖；内存 saver 无需跨进程序列化；B15F1 的 SQLite 后端再定义序列化（JSON / 文本） | 本 feature · B15F1 知情 |
| **X-06** | 自研区（v1 能力边界） | P-21 的 `True` / `False`：上游有子图继承语义，freegraph v1 无子图（C26 属 v2）⇒ 编译接受、运行期视为无 saver | 保持 B7F2 的「接受 + 记录」不破；避免运行期 `AttributeError`；不新增子图能力 | **B7F2**（记录面不变）· C26（v2） |
| **X-07** | 更明确的失败信号 | P-06 / 裁定 6：`put_writes` 指定的 `checkpoint_id` 在本线程不存在 ⇒ `ValueError`（上游不校验、直接写入悬挂桶） | 与 X-03 同源：显式失败优于静默悬挂；缺 `checkpoint_id` 的 `KeyError` 仍逐字上游 | 本 feature · B15F1 知情 |
| **X-08** | 自研区（零依赖约束） | P-15：编译期接受任何满足 L1 `Checkpointer` 的鸭子类型对象（上游要求 `BaseCheckpointSaver` 子类） | 结构化的「零依赖」要求 preclude import 上游基类；协议是唯一可行的等价判定 | 本 feature · B7F2 知情 |

> **失败信号 STRICTER 清单（原则 XI 允许 · 均如实标注）**：
> ① `delete_thread(non-str)` ⇒ `TypeError`（上游无类型校验）；
> ② `get_next_version` 非 `int` / `bool` ⇒ `TypeError`（上游 base 对 `str` 抛 `NotImplementedError`）；
> ③ `put_writes` 指定 id 不存在 ⇒ `ValueError`（上游静默写入悬挂桶 · 见 X-07）。
> 三者均属**失败信号**而非成功路径行为面，**不**放宽任何既有判据。

### 破冻结面的回溯修订清单 *(若有)*

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| **B7F2 的 X-4 / 差分 D-77**（编译期**不**校验 checkpointer） | `specs/b7f2-compile/spec.md` 的 X-4 消解条件 · `tests/differential/` 的 D-77 期望 | **拆分而不删**：D-77 的「上游抛 `TypeError`」保留；freegraph 列由「接受」改为「抛 `TypeError`」 | 本 feature 落地即消解（B7F2 的 D-4 已指名） |
| **B7F2 的测试期望**（`compile(checkpointer=object())` 不抛） | B7F2 的 `tests/` / 差分探针 | **拆分而不删**：保留「历史行为」注记；新增「B14F1 起抛 `TypeError`」断言 | 同上 |
| **B10F1 的 V-1**（恢复侧人工验证不可达成） | `harness/verification/B14F1/manual-verification.md` | **补齐实测输出**（中断 → `Command(resume=…)` → 跑完）；旧记录不作废，追加「恢复侧实测」段 | 本 feature 的人工验证记录 |
| **B8F2 的 D-2**（`checkpoints` 恒空） | `specs/b8f2-stream-modes/spec.md` 的下游承接状态 | **拆分而不删**：保留「v1 恒空」历史；新增「数据源已由 B14F1 提供；消费端接线待 B15F1」 | 本 feature 登记 · B15F1 承接 |
| **`harness/demo/README.md` 的待锁定清单** | 「`MemorySaver` 的模块路径 → B14F1 未定」一行 | **移除该条**；在验收脚本清单补「已锁定：`freegraph.persistence.MemorySaver`」 | 本 feature 交付物 |
| **`harness/demo/graph_core.py` 的软断言** | `case_interrupt_resume` 的 `soft(...)` | **改为 `check(...)`** + 挂真实 `MemorySaver`；「从节点起点重跑并拿到 resume 值」失败即 FAIL | 本 feature 交付物 |

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：系统 MUST 提供 `freegraph.persistence.MemorySaver`，并**结构化满足** L1 的 `Checkpointer` 协议
  **全部八个**方法（`get_tuple` / `list` / `put` / `put_writes` / `delete_thread` /
  `delete_for_runs` / `copy_thread` / `get_next_version`）；`InMemorySaver` MUST 是同一对象的别名。
- **FR-002**：运行期 MUST 在**每个 super-step 结束时**写入状态快照（初始快照 + 每个**实际执行过**的轮一个；
  收敛空轮不写）；挂起轮的挂起写**计入**该轮，MUST NOT 与每轮快照重复（裁定 5）。
- **FR-003**：系统 MUST 把**单个任务的写入**（pending writes）与快照**分层**持久化；
  `put_writes` 的写入 MUST NOT 自动合并进快照的 `values`。
- **FR-004**：系统 MUST 按 `thread_id` 隔离快照与写入；不同 `thread_id` 的数据 MUST 互不可见。
- **FR-005**：系统 MUST 维护 checkpoint **顺位 id**（每线程单调递增 · 可排序）；
  `get_next_version` MUST 单调递增（`int+1` · **2026-11-22 用户确认选项 A**）；
  MUST NOT 改写调度器写入的 `channel_versions` / `node_versions` / `versions_seen`（裁定 4）。
- **FR-006**：系统 MUST 支持 `delete_thread(thread_id)`：删除该会话的**全部**快照与写入，幂等，
  不影响其它线程。
- **FR-007**：checkpointer MUST 可通过 `compile(checkpointer=...)` 注入（B7F2 已支持该关键字）；
  未注入（`None`）或注入 `True` / `False` 时，**单次执行**的结果 MUST 与注入真实 saver 时
  **语义一致**（不落盘）；**不含**显式恢复路径（`Command(resume=...)` 仍要求真实 saver，见 FR-028）。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core` / `langgraph*` / `langsmith` / 任何第三方包；
  MUST NOT 读环境变量；MUST NOT 有任何出站；`src/freegraph/persistence/**` MUST 只 import **L1 + 标准库**。
- **FR-009**：`MemorySaver` 的模块路径 MUST 锁定为 `freegraph.persistence.MemorySaver`
  （实现文件 `src/freegraph/persistence/memory.py`；`InMemorySaver` 同对象别名）。
- **FR-010**：`compile()` MUST 在编译期校验 `checkpointer`：`None` / `True` / `False` /
  满足 `Checkpointer` 协议的对象 ⇒ 接受；其它 ⇒ `TypeError`（消息点名期望类型）；
  MUST NOT 改变 `CompiledGraph.checkpointer` 的记录方式。
- **FR-011**：`get_tuple(config)` MUST 返回 `CheckpointTuple`（或 `None`），且 MUST 暴露
  `.snapshot`（L1 `StateSnapshot`）· `.pending_writes`（`(task_id, channel, value)` 三元组序列）·
  `.scheduler`（纯数据字典）**三个具名属性**，**恰好三个公开字段**
  （**2026-11-22 用户确认选项 A** · 不加上游别名 / 第二套结构）。
- **FR-012**：`.snapshot` MUST 是 L1 的 `StateSnapshot`，**8 字段全部可读**：
  `values` / `next` / `config` / `metadata` / `created_at` / `parent_config` / `tasks` / `interrupts`；
  `next` / `tasks` / `interrupts` MUST 是 `tuple`；`metadata` MUST 是 `Mapping`；`parent_config` 首条为 `None`。
- **FR-013**：写侧关键字 MUST 逐字为 `put(config, values=..., metadata=...)` 与
  `put_writes(config, writes=..., task_id=..., task_path=...)`；`put` MUST 返回带新 `checkpoint_id` 的
  `RunConfig`；`put_writes` 的目标 MUST 由 `config.configurable["checkpoint_id"]` 指定
  （缺 key ⇒ `KeyError`；指定 id 不存在 ⇒ `ValueError` · X-07），**MUST NOT** 隐式取最新。
- **FR-014**：保留通道名 MUST 逐字为 `__interrupt__`（中断留痕）与 `__resume__`（恢复值）；
  `__error__` / `__scheduled__` MUST 作为上游同款保留名被接受（不解释）。
- **FR-015**：`MemorySaver` MUST 支持按 `config.configurable["checkpoint_id"]` 取指定快照；
  未给 id ⇒ 取最新；id 不存在 ⇒ `None`。
- **FR-016**：`list(config=None, *, filter=None, before=None, limit=None)` MUST 支持：
  `config=None` 全线程；`filter` 按 metadata 顶层 key；`before` 排除 `id >= before_id`；
  `limit <= 0` ⇒ 空；返回**迭代器**，最新在前。
- **FR-017**：系统 MUST 对存入 / 取出的 `values` / `metadata` / `pending_writes` / `scheduler`
  做**防御性深拷贝**；可变容器 MUST NOT 在存储与调用方之间共享。
- **FR-018**：运行期在生效 `thread_id` 为 `None` / 空串时 MUST 跳过全部 saver 调用
  （不 `get_tuple` / 不 `put` / 不 `put_writes`），执行结果与未注入 checkpointer 一致；
  **运行期归一化只判 `None` / `True` / `False` / `thread_id`，MUST NOT 在运行期判
  `isinstance(..., Checkpointer)`**（协议校验只在编译期 · FR-010）；
  直接向 `MemorySaver` 的 `get_tuple` / `put` / `put_writes` / `list(config)` 传入
  缺失 / 空 `thread_id` 的 config ⇒ `ValueError`（`list(None)` 仍合法；
  `put_writes` 缺 `checkpoint_id` ⇒ `KeyError`；**2026-11-22 用户确认选项 A**）。
- **FR-019**：系统 MUST 原样存取静态挂起现场（`interrupts=()` 合法 · `suspension_kind` ·
  `static_ack` · `next` 可为空）与调度账本的全部既有键（含屏障 `seen` 与 fan-out 载荷）；
  MUST NOT 为静态挂起额外要求动态中断载荷；**挂起快照的 `tasks` MUST 为 `()`**
  （与 B10F1 的冻结挂起写一致；仅「每轮执行完成」的 `put` 填本轮 `PregelTask`）；
  快照计数 MUST 按裁定 5 的「初始惰性写 + 挂起写计入该轮 + 不重复」策略
  （**2026-11-22 用户确认选项 A**）。⚠️ **自 B15F1 起**：存储的 `tasks` 仅作历史 / 流数据源；
  `get_state` / `get_state_history` / `stream(checkpoints)` 的 `tasks` MUST 由读取层按上游
  next-tasks 重建（见裁定 5 后注记；R-13 / B15F1 回溯修订）。
- **FR-020**：系统 MUST 接受标准任务 `task_id` = 节点名、fan-out `task_id` = `f"{节点名}:{TaskId}"`；
  MUST 接受同一轮同一节点有多个任务；MUST NOT 为 fan-out 另立持久化载体。
- **FR-021**：同一轮「真异常 + 中断同现」时，系统 MUST 先把该轮每个中断元组经
  `put_writes(round_start_config, writes=[("__interrupt__", (payload,))], task_id=..., task_path=...)`
  写入**该轮起点所用的** checkpoint（`round_start_config.configurable["checkpoint_id"]`
  = 该轮起点 id；失败轮**不新建快照**；附着在上一轮或初始快照上），再**原样**抛出真异常；
  MUST NOT 改变异常类型 / 消息 / identity；MUST NOT **为中断留痕**新增附注或调度状态字段
  （B12F1 既有的其余并发失败 `attach_failure_notes` MUST 保留）。
- **FR-022**：挂接 checkpointer 后，运行期 MUST 通过 `start_node_span(..., checkpoint_id=...)` 的
  **既有参数**把当前 checkpoint id 填入节点 span；模型 / 工具 span 继续继承；
  `Span` 的 11 字段 MUST NOT 改动；未挂 checkpointer ⇒ `checkpoint_id is None`。
- **FR-023**：`MemorySaver` MUST 提供「每创建一个 checkpoint 一条事件」的**数据源**：
  可选 `on_checkpoint(snapshot)`（每次成功 `put` 恰一次）+ `list()` 历史枚举；两者载荷 MUST 与
  `get_tuple().snapshot` **同形**。`stream(checkpoints)` 的消费端接线归 B8F2 / B15F1；
  本 feature MUST NOT 伪造 stream 事件。**（2026-11-22 澄清轮 · 用户确认选项 A）**
- **FR-024**：`MemorySaver` MUST NOT 读取 / 保存 / 还原 / 透出 `RunConfig.context`；
  `snapshot.config.context` MUST 为 `None`；MUST NOT 把 `context` 塞进 `configurable` 或 `metadata`。
- **FR-025**：本 feature MUST NOT 改动 L1 的 `Checkpointer` / `StateSnapshot` / `RunConfig` / `Span` /
  `Interrupt` / `PregelTask` 的符号面与字段；MUST NOT 新增 L1 异常类型。
- **FR-026**：`harness/verification/B14F1/manual-verification.md` MUST
  包含**恢复侧真跑一轮**的实测输出（真实 `MemorySaver`：`interrupt` → `Command(resume=…)` → 跑完），
  并含「环境 / 步骤 / 实际输出 / 结论 / 遗留问题」五段。
- **FR-027**：`harness/demo/README.md` MUST 移除「`MemorySaver` 的模块路径」待锁定条目；
  `harness/demo/graph_core.py` 的 `case_interrupt_resume` MUST 挂真实 `MemorySaver`
  并把对应 `soft(...)` 改为 `check(...)`（失败即 FAIL）。
- **FR-028**：未挂 checkpointer 时，`Command(resume=...)` MUST 继续抛
  `InterruptError(reason="checkpointer_required")`；本 feature MUST NOT 提供「不挂 checkpointer 也能恢复」
  的内存态旁路。
- **FR-029**：`delete_for_runs` / `copy_thread` MUST 作为方法存在（协议结构面）；
  v1 MUST 抛 `NotImplementedError`（上游内存 saver 同款）。
- **FR-030**：`MemorySaver` 的可变状态 MUST 由**每实例一把锁**保护；并发 `put` / `get_tuple` / `list` /
  `delete_thread` MUST NOT 串扰；`on_checkpoint` 回调 MUST 在锁外调用且其异常 MUST NOT 影响落盘。
- **FR-031**：一次 `put` MUST 原子提交（要么完整写入快照 + 父链 + 内部状态，要么完全不变）；
  深拷贝失败 ⇒ 原异常传播，存储 MUST NOT 留下半成品。
- **FR-032**：`MemorySaver` MUST NOT 做 I/O、MUST NOT 打开文件 / 网络 / 读环境变量；
  `created_at` MUST 用标准库 UTC 时钟生成。
- **FR-033**：系统 MUST 在 `tests/differential/` 落本 spec 的 D-01…D-15（上游缺席 ⇒ skip）；
  差分探针 MUST 覆盖快照数、pending writes 去重、thread 隔离、恢复、静态挂起、fan-out、屏障、
  真异常 + 中断、编译期校验、`context` 不持久化。
- **FR-034**：本 feature MUST NOT 改变图执行的语义：注入 / 不注入 checkpointer 的
  **单次执行**（节点执行序列、最终状态、错误信号）MUST 一致（`None` / `True` / `False` /
  无 `thread_id` 均跳过落盘，见 FR-007 / FR-018）；**不含**显式恢复路径（恢复要求真实 saver · FR-028）。
- **FR-035**：证据门禁：本 spec 的每条上游行为断言 MUST 带 **`langgraph` 1.2.11 + `路径:行号`**；
  换版本 MUST 重新核实全部锚点。

### Key Entities *(include if feature involves data)*

- **`Checkpointer`（协议）**：快照 + 历史持久化接口，**8 方法**；L1 已冻结（C19）。
- **`MemorySaver`**：本 feature 的内存实现；按 `thread_id` 分区的快照 + pending writes 双层存储；
  开发 / 调试定位。
- **`CheckpointTuple`**：读侧载体，三个字段 `snapshot` / `pending_writes` / `scheduler`。
- **`StateSnapshot`**：L1 的 8 字段快照（`values` / `next` / `config` / `metadata` /
  `created_at` / `parent_config` / `tasks` / `interrupts`）。
- **待写入（pending writes）**：`(task_id, channel, value)` 三元组序列；与快照分层。
- **调度账本**：`metadata["scheduler"]` 的纯数据字典（`versions_seen` / `channel_versions` /
  `node_versions` / `dynamic_edges` / `fanout` / `suspension_kind` / `static_ack`）。
- **checkpoint 顺位 id**：每线程单调递增的 32 位零填充十进制字符串；`span.checkpoint_id` 的来源。
- **`RunConfig.thread_id`**：会话标识（C22）；缺省时运行期跳过落盘。

### 需求 ↔ 成功标准追溯表

| FR | SC | 判据 |
|---|---|---|
| FR-001 | SC-006 | 八方法存在 + `isinstance(..., Checkpointer)` |
| FR-002 | SC-001 / SC-005 | 快照计数 + 执行结果不变 |
| FR-003 | SC-002 | pending writes 分层取回 |
| FR-004 | SC-003 | 两 thread 互不可见 |
| FR-005 | SC-004 | 单调递增 + 调度版本不被改写 |
| FR-006 | SC-011 | 删除后零残留 |
| FR-007 | SC-005 / SC-014 | 注入前后一致；无 saver 不落盘 |
| FR-008 | SC-024 | 依赖 / 环境 / 出站门禁 |
| FR-009 | SC-012 | 模块路径可 import |
| FR-010 | SC-013 | 编译期 `TypeError` |
| FR-011 | SC-007 | 三属性齐全 |
| FR-012 | SC-008 | 8 字段 / 父链 |
| FR-013 | SC-002 / SC-008 | 关键字逐字 + `put` 返回 config |
| FR-014 | SC-009 | 保留通道名逐字 |
| FR-015 | SC-010 | 指定 id 取回 |
| FR-016 | SC-010 | 过滤 / 排序 / 上限 |
| FR-017 | SC-003 / SC-008 | 防御性拷贝 |
| FR-018 | SC-005 / SC-014 | 无 thread_id 跳过 |
| FR-019 | SC-015 / SC-017 | 静态挂起 / 屏障 |
| FR-020 | SC-016 | fan-out task_id |
| FR-021 | SC-018 | 真异常 + 中断留痕 |
| FR-022 | SC-019 | span checkpoint_id |
| FR-023 | SC-020 | 事件数据源 |
| FR-024 | SC-021 | context 不持久化 |
| FR-025 | SC-024 | L1 符号面零改动 |
| FR-026 | SC-022 | 人工验证记录 |
| FR-027 | SC-023 | demo 脚本硬断言 |
| FR-028 | SC-014 | 未挂 saver 的恢复失败信号 |
| FR-029 | SC-006 | 两方法存在且 v1 `NotImplementedError` |
| FR-030 | SC-003 | 并发隔离 |
| FR-031 | SC-002 | 原子提交 / 无半成品 |
| FR-032 | SC-024 | 零 I/O / 零环境变量 |
| FR-033 | SC-025 | 差分覆盖 |
| FR-034 | SC-005 | 执行语义不变 |
| FR-035 | SC-025 | 上游锚点齐全 |

### Out of Scope

- **不实现** `SqliteSaver` / 持久化文件后端 / `get_state` / `get_state_history`（归 B15F1）。
- **不实现** `update_state` / 时间旅行回放 / fork 分支（归 B16F1）。
- **不实现** `Store` / `MemoryStore`（B17 已砍 · 2026-11-05；C20 契约仍冻结、实现后补 v2）。
- **不实现** Postgres / 跨进程 / 跨机共享 thread（v2）。
- **不实现** `stream(checkpoints)` 的消费端接线（归 B8F2 / B15F1；本 feature 只交付数据源）。⏳ **B15F1 已交付（计划交付消费端；实现前仍为空）**。
- **不实现** async saver 方法（`aget` / `aput` / …；freegraph v1 无 async）。
- **不实现** `delete_for_runs` / `copy_thread` 的语义（v1 只保留方法面）。
- **不实现** 子图的 checkpointer 继承（`True` / `False` 的子图语义 · C26 属 v2）。
- **不实现** 运行时序列化 / 反序列化格式（B15F1 的 SQLite 后端负责）。
- **不改变** 图执行语义、`freegraph.graph` 门面符号面、L1 契约面、`Span` 11 字段。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：**完成运行**的快照数 == **实际执行的 super-step 轮数 + 1**（初始快照）；
  收敛空轮产生 **0** 条快照；动态中断挂起时，快照数 == 含挂起轮的已执行轮数 + 1。
- **SC-002**：`put_writes` 写入的三元组经 `get_tuple().pending_writes` 取回后**逐项相等**
  （内容一致）；**去重 / 排序逐字上游**（普通通道跨调用同 `(task_id, idx)` 首次；
  保留通道最后生效（同调用内也覆盖）；顺序 = `(task_path, task_id, idx)` 升序）；
  快照 `values` 不因写入而改变；一次 `put` 失败时存储变化 == **0**。
- **SC-003**：`thread-1` 与 `thread-2` 的快照 / pending writes **互不可见**（交叉读取命中数 == 0）；
  `delete_thread` 后残留 == 0，另一线程数据逐项不变；并发读写串扰次数 == 0。
- **SC-004**：checkpoint id **严格单调递增**（每线程）；`get_next_version(None) == 1`、
  `get_next_version(k) == k + 1`；运行后 `.scheduler["channel_versions"]` 与调度器版本
  **逐 key 相等**（被改写的 key 数 == 0）。
- **SC-005**：对同一张图与**可深拷贝**的载荷，注入 / 不注入 checkpointer 的
  **单次执行**（节点执行序列、最终状态、错误信号）逐项相等（差异项 == 0）；无 `thread_id` 时
  注入 checkpointer 也**不改变**结果；**不含**显式恢复路径（恢复要求真实 saver）。
- **SC-006**：`isinstance(MemorySaver(), freegraph.contracts.Checkpointer) is True`；
  八个方法均可调用 / 可断言存在；`delete_for_runs` / `copy_thread` 在 v1 抛 `NotImplementedError`。
- **SC-007**：`get_tuple(config)` 的返回值具名属性 `.snapshot` / `.pending_writes` / `.scheduler`
  三项全部存在；`.snapshot` 是 `StateSnapshot` 实例。
- **SC-008**：`.snapshot` 的 **8 字段**全部可读且类型正确；`parent_config` 链首条为 `None`、
  后续逐条指向前一快照；`next` / `tasks` / `interrupts` 是元组。
- **SC-009**：`__interrupt__` / `__resume__` 的字面量在写入与读回路径中**逐字一致**；
  `__error__` / `__scheduled__` 被接受且不被解释；保留通道在同一次调用内重复写入时
  **最后一次生效**（上游 `WRITES_IDX_MAP` 同款）。
- **SC-010**：`list` 的 `filter` / `before` / `limit` 组合结果与预期集合**逐项相等**；
  最新在前；`limit<=0` ⇒ 空；指定 `checkpoint_id` 的 `get_tuple` 命中率 == 100%（存在时）。
- **SC-011**：`delete_thread` 后 `get_tuple == None`、`list == []`、`put_writes` 无残留；
  重复删除抛异常次数 == 0。
- **SC-012**：`from freegraph.persistence import MemorySaver, InMemorySaver` 成功；
  `InMemorySaver is MemorySaver`；`freegraph.persistence` 对 L2 / L3 / L5 的 import 数 == 0。
- **SC-013**：`compile(checkpointer=<非法>)` 抛 `TypeError` 的比率 == 100%；
  `None` / `True` / `False` / `MemorySaver()` 被接受的比率 == 100%；`CompiledGraph.checkpointer`
  的记录值与传入值逐项相等（**记录方式未改**）。
- **SC-014**：未挂 checkpointer（`None` / `True` / `False`）或 `thread_id` 缺失时，
  saver 调用次数（`get_tuple` / `put` / `put_writes`）== 0；`Command(resume=...)` 在
  未挂 checkpointer 时抛 `InterruptError(reason="checkpointer_required")` 的比率 == 100%。
- **SC-015**：静态挂起（`interrupt_before` / `interrupt_after`）的 `suspension_kind` / `static_ack` /
  `fanout` / `next` 原样往返（差异项 == 0）；`interrupts=()` 的静态挂起可恢复；
  完成快照只写 **1** 次，与每轮快照重复次数 == 0。
- **SC-016**：`Send` fan-out 的每个任务在 pending writes 中有**唯一** `task_id`
  （形如 `f"{node}:{id}"`）；同一节点多任务互相覆盖次数 == 0；普通任务 `task_id` == 节点名。
- **SC-017**：多源屏障在暂停 → 恢复后，`seen` 保留；目标节点**重复触发次数 == 0**。
- **SC-018**：真异常 + 中断同现时，pending writes 含该轮中断元组（命中率 == 100%）；
  抛出的异常对象 **identity / 类型 / 消息**与未挂 saver 时逐项相等（改动次数 == 0）；
  异常上**新增附注数 == 0**，调度状态中**新增留痕字段数 == 0**。
- **SC-019**：挂 checkpointer + tracer 时，节点 span 的 `checkpoint_id` **非空**且等于该轮起点
  快照的 id（相等率 == 100%）；子 span 与节点 span 的 `checkpoint_id` 一致率 == 100%；
  未挂 checkpointer 时 `checkpoint_id is None` 的比率 == 100%；`Span` 字段数 == **11**（未变）。
- **SC-020**：`on_checkpoint` 回调次数 == 成功 `put` 次数；每次载荷与 `get_tuple().snapshot`
  同形（8 字段逐项一致）；回调抛错后 `put` 仍成功且已提交快照不回滚（回滚次数 == 0）；
  `stream(checkpoints)` 的伪造事件数 == 0。
- **SC-021**：`context` 在 `snapshot.config` / `metadata` / `.scheduler` / pending writes 中
  出现次数 == 0；`snapshot.config.context is None` 的比率 == 100%；恢复时从快照还原 `context`
  的次数 == 0。
- **SC-022**：`harness/verification/B14F1/manual-verification.md`
  存在；含**恢复侧真跑一轮**的非空实测输出；五段（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）齐全
  （文档守卫断言）。
- **SC-023**：`harness/demo/README.md` 的待锁定清单中「`MemorySaver` 的模块路径」条目数 == 0；
  `graph_core.py` 的 `case_interrupt_resume` 中对应 `soft(` 调用数 == 0、`check(` 覆盖该断言；
  `python harness/demo/graph_core.py` 退出码 == **0**。
- **SC-024**：依赖树新增第三方包数 == 0；环境变量读取点 == 0；出站调用点 == 0；
  G25 对 `src/freegraph/persistence/**` 判绿；L1 符号面差异 == 0；新增门禁编号数 == 0。
- **SC-025**：差分场景 D-01…D-15 全部落 `tests/differential/`；上游缺席时 **skip**（不是 fail）；
  上游在场时通过率 == 100%；本 spec 的每条上游断言带版本 + `路径:行号`（缺失数 == 0）。

### 验收判据（立项书 §5.2 B14F1 小目标 · 逐条可判定）

> 小目标原文：**快照 + pending writes 双层持久化**

| # | 判据 | 判定方式 | 本 spec 的承载 |
|---|---|---|---|
| **A1** | 快照持久化 | 快照数量 == 轮数 + 1；`values` 内容可校验 | **SC-001 / SC-008** · FR-002 / FR-012 |
| **A2** | pending writes 持久化 | 写入后可取回（内容一致） | **SC-002** · FR-003 / FR-013 |
| **A3** | 按 thread 隔离 | 两 thread 互不可见 | **SC-003** · FR-004 / FR-018 |
| **A4** | `MemorySaver` 满足 `Checkpointer` 协议 | 结构化子类型检查 | **SC-006** · FR-001 / FR-029 |

---

## Assumptions

- **上游取证环境**：本机 `.venv` 已安装 `langgraph 1.2.11`；本 spec 的锚点均为 2026-11-22 实测核对；
  换版本 MUST 重新核实全部行号（宪法原则 VIII）。
- **spec 目录命名**：speckit 通用规则为 `NNN-<short-name>`；本仓库既有 feature 全部采用
  `<b<N>f<M>-<slug>`（宪法 v1.4.2 的目录约定）⇒ 本 feature 用
  `specs/b14f1-checkpointer-memory-saver`（**已偏离通用规则 · 已登记**）。
- **分支**：本仓库无 `.specify/extensions.yml` ⇒ 无 `before_specify` 钩子 ⇒ 不创建分支，在 `main` 上开发。
- **Python 基线**：3.11+；实现只用标准库（`copy` / `threading` / `datetime` / `collections.abc`）。
- **规模参考**：1,200 行（实现 560 / 测试 640）· 3 人日；若运行期接线与差分探针超预算，
  在 plan 的登记项中如实登记，**MUST NOT** 通过削减判据来压行数。
- **`MemorySaver` 的定位**：**开发 / 调试**；不保证跨进程 / 跨重启；生产 / 长期场景由 B15F1 承担
  （发起者 2026-11-05 拍板）。
- **`InMemorySaver` 别名**：为上游可读性保留，与 `MemorySaver` **同一对象**；不构成第二套实现。
- **无 async**：freegraph v1 无 async；`Checkpointer` 协议只声明同步方法（B2F1 已冻结）。
- **`delete_for_runs` / `copy_thread`**：v1 只保留方法面并抛 `NotImplementedError`（上游内存 saver 同款）；
  运行级删除 / 线程复制属 B15F1 / B16F1。
- **`context`**：B8F3 已接线；本 feature 明确**不**持久化、**不**从快照还原。
- **`stream(checkpoints)`**：B8F2 v1 忽略 `checkpointer`（⚠️ **B15F1 起 `checkpoints` 档 carve-out** · ✅ 已交付）；本 feature 只交付数据源，
  消费端接线属 B8F2 / B15F1（Out of Scope · 能力边界 · 非偏离）。✅ **B15F1 已交付**。
- **深拷贝**：状态载荷预期可被 `copy.deepcopy`；不可拷贝对象属用户侧异常，原异常传播。
- **无 `thread_id`**：运行期跳过落盘（X-03）；这是为 SC-005 服务的明确取舍，不是静默共享会话。
- **差分测试**：上游 `langgraph` 只在测试侧使用；生产依赖声明 MUST 保持 `dependencies = []`。
- **人工验证**：B10F1 的 V-1 由本 feature 补齐；记录 MUST 由执行者如实转录，禁止代签。

---

## 依据

- 立项书 §5.2（B14F1 行）、§5.3（C19 / C22 / C23）、§5.4（P2 `Checkpointer` 协议 + DF3 `StateSnapshot`）、
  §6.3（关键路径）、§9.1（门禁）。
- 源码参照（**langgraph 1.2.11**）：
  `langgraph/checkpoint/base/__init__.py`（`PendingWrite` / `Checkpoint` / `CheckpointTuple` /
  `BaseCheckpointSaver` / `get_next_version` / `WRITES_IDX_MAP`）·
  `langgraph/checkpoint/memory/__init__.py`（`InMemorySaver` / `get_tuple` / `list` / `put` /
  `put_writes` / `delete_thread` / `get_next_version` / `MemorySaver` 别名）·
  `langgraph/pregel/_checkpoint.py`（checkpoint id 生成）·
  `langgraph/pregel/_runner.py:588-591,687,690`（中断留痕 + 真异常优先）·
  `langgraph/pregel/_loop.py:631-636,1081`（`checkpoints` 事件 / `_put_checkpoint`）·
  `langgraph/pregel/debug.py:144-185`（`map_debug_checkpoint`）·
  `langgraph/types.py:109-118,684-701`（`ensure_valid_checkpointer` / `StateSnapshot`）·
  `langgraph/graph/state.py:1179,1234`（`compile` 的 checkpointer 关键字与校验）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C19 / C17 / C22 / C23）。
- 跨 feature 接缝：`specs/b10f1-interrupt-resume/contracts/checkpoint-contract.md` §2…§6。
- 层与门禁：`specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`（L4 = `persistence`）·
  `harness/prompts/guide.md` §2.3 / §3.5（L4 只依赖 L1）。
- 验收脚本约定：`harness/demo/README.md`（M3 待锁定形态清单 + 软断言清单）。

---

## 下游承接（本 feature → 下游 · 只接线 · 逐条最小改动）

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 |
|---|---|---|---|---|
| **D-01** | **B15F1** | **M3** | `SqliteSaver` MUST 复用本 feature 冻结的读侧载体（`.snapshot` / `.pending_writes` / `.scheduler`）、写侧关键字（`values` / `metadata` / `writes` / `task_id` / `task_path`）、**`put_writes` 目标由 `configurable["checkpoint_id"]` 指定（缺 key ⇒ `KeyError`）**、**pending writes 去重 / 排序（`WRITES_IDX_MAP` + `writes_sort_key`）**、checkpoint id 排序语义与 `context` 不持久化口径；`get_state` / `get_state_history` 的对外方法归 B15F1 | FR-011…FR-016 · FR-024 · 裁定 3 / 4 / 6 / 12 |
| **D-02** | **B15F1** | **M3** | `stream(checkpoints)` 的消费端接线由 B15F1 完成：消费本 feature 的 `on_checkpoint` / `list()` 数据源，事件与 `get_state()` 同形。✅ **B15F1 已交付**：有 saver + `thread_id` 时按本次运行产出；无 saver 仍空；只在 `checkpoints` mode 写 | FR-023 · 裁定 11 · Out of Scope（能力边界） |
| **D-03** | **B16F1** | **M3** | `update_state` / 时间旅行 MUST 以本 feature 的 checkpoint 顺位 id 与父链为定位依据；MUST NOT 另造 id 空间 | FR-005 · FR-012 · 裁定 4 / 5 |
| **D-04** | **B18F1** | **M3** | 节点 span 的 `checkpoint_id` 由本 feature 的运行期接缝填值；B18F1 MUST NOT 重新实现子 span 继承 | FR-022 · 裁定 11 |
| **D-05** | **B8F2** | **M3** | `checkpoints` 档的数据源已由本 feature 交付；消费端接线状态需在 B8F2 的执行记录中更新（**不改 B8F2 的其余六档语义**；`checkpoints` 档 carve-out 由 B15F1 承接） | FR-023 · 裁定 11 · Out of Scope（能力边界） |
| **D-06** | **B21F1** | **M3** | OTLP 导出 MAY 复用 `span.checkpoint_id` 与 checkpoint 事件；MUST NOT 要求本 feature 增删 `Span` 字段 | FR-022 / FR-023 |
| **D-07** | **B24F1 / B25F1** | **M4** | API 兼容矩阵 MUST 增加 `freegraph.persistence.MemorySaver` / `InMemorySaver` / `CheckpointTuple` 三行；`manual-verification.md` MUST 纳入发布前人工验收 | FR-009 / FR-026 |
| **D-08** | **B15F1 / B16F1** | **M3** | 本 feature 的 `delete_for_runs` / `copy_thread` 的 `NotImplementedError` 边界 MUST 在后端实现时重新评估（若 B15F1 实现，则不得回改本 feature 的 `MemorySaver` 行为） | FR-029 · 裁定 6 |
| **D-09** | **B15F1** | **M3** | **`tasks` 权威语义移交**：自 B15F1 起，`CompiledGraph.get_state` / `get_state_history` / `stream(checkpoints)` 的 `StateSnapshot.tasks` MUST 由 B15F1 读取层按上游 **next-tasks** 语义重建（`snapshot.next` + `.scheduler["fanout"]` + pending `__interrupt__`）；本 feature 存储的「本轮完成态」`tasks` 保留为历史 / 流数据源，**MUST NOT** 作为这些 API 的权威来源；B8F2 的 `stream(tasks)` 仍为完成态 | 裁定 5 后注记 · FR-019 · FR-020 |

---

## 下游承接状态（上游 → 本 feature 的核对）

| 来源 | 编号 | 状态 |
|---|---|---|
| **B10F1** | D-1 / D-2 · X-5 消解 | ✅ **已接线**（本 spec FR-011…FR-014 / FR-021 / FR-026） |
| **B12F1** | D-5 / D-6 | ✅ **已接线**（FR-004 / FR-018 / FR-021） |
| **B11F1** | D-3 | ✅ **已接线**（FR-020） |
| **B13F1** | D-5 | ✅ **已接线**（FR-019） |
| **B7F4** | D-4 | ✅ **已接线**（FR-019） |
| **B7F2** | D-4 | ✅ **已接线**（FR-010） |
| **B8F2** | D-2 | ✅ **已接线**（FR-023 · 数据源）· ✅ **B15F1 已交付（消费端）** |
| **B8F3** | D-1 / D-3 | ✅ **已接线**（FR-024） |
| **B18F1** | D-4 | ✅ **已接线**（FR-022） |
| **B7F3** | D-4 | ✅ **已接线**（FR-007 / FR-028） |
