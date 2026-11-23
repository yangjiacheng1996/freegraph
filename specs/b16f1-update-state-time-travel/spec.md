# Feature Specification: B16F1 · `update_state` + 时间旅行回放

**Feature Branch**: `b16f1-update-state-time-travel`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_specify` 钩子；既有 feature 同样在 `main` 上开发）

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: `harness/features/B16F1_update_state与时间旅行.md` —— 交付**时间旅行**：用户可以从**任意历史 checkpoint 重放**，也可以**分叉**（基于某个历史快照修改状态后重新继续跑）。本 feature 的判定是：**可从历史 checkpoint 重放**。

> **范围提醒**：本 feature 是 **L4 持久化层**的**回放入口** + **L1 `CompiledGraph` 的状态更新面**。
> 它**复用** B14F1 / B15F1 已冻结的 checkpoint 顺位 id、`parent_config` 父链、
> `put` / `put_writes` 渠道与 `get_state` / `get_state_history` 组装口径；
> **MUST NOT** 另立 id 空间、第二套快照组装路径或第二套「改写历史」语义。
> **不实现** `Store`（B17 已砍）、Postgres / async（v2）、前端 UI（B26）、
> trace 存储（B20F1 / B20F2）、并行分支执行 / 分支树 UI（v1 只保线性重放；每次 `update_state` 产生一条新分支，同一 thread 可多次分叉）。
> **MUST NOT** 改变普通运行的图执行语义；**MUST** 保持运行时依赖闭包为空集。

---

## 承接条款（上游 feature → 本 feature）

> **宪法 v1.8.0「跨 feature 承接的接线通则」**：某 feature 的规格中出现**指名下一棒 feature**
> 的跨 feature 义务时，该条款 MUST 写入目标 feature 的 spec ⇒ 由本 spec 落成 **FR + 裁定**。
> **只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽任何门禁判据。**

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B10F1 → B16F1** | **M3** | **「恢复」与「时间旅行」的边界**：B10F1 的恢复路径读 checkpointer 的**最新快照 + pending writes** ⇒ **MUST NOT** 改写历史；`update_state` / 分叉 MUST NOT 与恢复路径共用同一套「改写历史」语义；两者**并存但独立**。 | B10F1 **FR-010** · **FR-018** · **裁定 9** · 下游承接 **D-7** | **FR-009 / FR-010 / FR-013** · **裁定 4 / 6** · SC-002 / SC-011 |
| **H-2** | **B13F1 → B16F1** | **M3** | **静态挂起的历史表示**：历史快照 MUST 能把「静态挂起」表示为 `interrupts == ()` 且 `suspension_kind` / `static_ack` 为静态值（`next` 允许为空）；从历史静态快照恢复 MUST NOT 要求动态中断载荷；MUST NOT 假设「`next` 非空 ⇒ 必有中断」。 | B13F1 下游承接 **D-6** | **FR-011** · **裁定 5** · SC-011 |
| **H-3** | **B8F3 → B16F1** | **M3** | **`context` 不持久化 / 不得回退**：`update_state` 与时间旅行回放 MUST NOT 把 `context` 写入 checkpoint 或从历史快照恢复 `context`；`context` 仍只来自本次运行的 `RunConfig.context`。MUST NOT 回退到 `configurable` 承载 `context`；MUST NOT 重新引入节点别名。 | B8F3 下游承接 **D-1 / D-3** | **FR-012** · **裁定 7** · SC-010 |
| **H-4** | **B14F1 → B16F1** | **M3** | **checkpoint 定位**：`update_state` / 时间旅行 MUST 以 B14F1 的 checkpoint 顺位 id 与 `StateSnapshot.parent_config` 父链为定位依据；MUST NOT 另造 id 空间或重排父链。`delete_for_runs` / `copy_thread` 的 `NotImplementedError` 边界在本 feature **重新评估后仍保持 v1 未实现**，且 MUST NOT 回改 `MemorySaver` 的既有行为。 | B14F1 下游承接 **D-03 / D-08** | **FR-005 / FR-016 / FR-017** · **裁定 2 / 3 / 9** |
| **H-5** | **B15F1 → B16F1** | **M3** | **checkpoint 顺位 id / 父链 / 组装口径**：新快照 MUST 通过同一 `put` 渠道追加；`get_state_history` 继续可枚举且倒序；`update_state` / 分叉 MUST NOT 破坏原历史；`get_state` / `get_state_history` 的组装口径（含 `interrupts` 投影；`get_state` 无 id 时合并 pending、历史不合并）MUST 保持一致；MUST NOT 另写第二套快照组装路径；历史静态快照 MUST 可直接作为重放起点。 | B15F1 下游承接 **D-01 / D-02 / D-03** | **FR-005 / FR-008 / FR-009 / FR-011** · **裁定 3 / 5 / 6** |
| **H-6** | **B7F3 → B16F1** | **M3** | **`config` 注解放宽的归属**：L1 `CompiledGraph.update_state` 的 `config` 注解仍为 `RunConfig`（无映射形态）⇒ 本 feature MUST 走「登记 + 回溯修订 + 发起者追认」，并 MUST 复用 B7F3 的**双形态载体边界**（`RunConfig` = 会话面 + `max_concurrency`；普通映射 = 运行期参数 ⇒ 原样交给 L2 ⇒ MUST NOT 在门面层翻译）。 | B7F3 下游承接 **D-5** · 契约 **CF-05** | **FR-002 / FR-018** · **裁定 1** · 破冻结面回溯修订清单 |

---

## Clarifications

### Session 2026-11-23（依据本仓库上游对齐审计 + `use-time-travel.md` 定案）

- Q: `update_state` 的返回类别应采用 B2F1 冻结的 `StateSnapshot`，还是上游的 `RunnableConfig`？ → A: **采用上游 `RunConfig`**。`harness/proposals/上游对齐审计.md` 的 **P-12** 已把「`update_state` 返回 `StateSnapshot` / 上游返回 `RunnableConfig`」登记为**差异 ①**，**P3-6** 已把「`update_state` 返回 `RunnableConfig`」列为 B2F1 的待对齐项 ⇒ 本 feature 按原则 XI 落地，并走「破冻结面回溯修订 + 发起者追认」。这样 `fork_config = graph.update_state(...)` → `graph.invoke(None, fork_config)` 与上游文档逐字同款（`use-time-travel.md:78-96`）。**（2026-11-23 发起者追认：批准改为 `RunConfig` · 选项 A · R-1）**
- Q: `update_state` 是否支持上游的 `task_id` 关键字与 `values=None, as_node=END` 的「清空任务」形态？ → A: **v1 不支持**。V1 只保**线性重放 + 每次调用一条新分支**（同一 thread 可分叉多次）；`task_id` 服务并行任务关联，`values=None + END` 服务清空任务树，二者均属并行 / 多分支语义 ⇒ 登记为**能力边界**（非偏离编号），留待 v2。
- Q: 从「静态挂起」的历史快照调用 `update_state` 时，新快照的 `suspension_kind` / `static_ack` 应怎么处理？ → A: **清空静态标记**（新快照 `suspension_kind = None` / `static_ack = None`）⇒ 新分支是**新的执行起点**，旧的静态确认不得泄漏；若后继再次命中 `interrupt_before` / `interrupt_after`，按正常规则**再次暂停**。MUST NOT 保留旧 ack 绕过审批点。
- Q: 从静态挂起快照执行 `invoke(None, static_snapshot.config)` 时，是保留 `static_ack` 继续，还是清空 ack 重新暂停？ → A: **保留 `static_ack` 继续（选项 A）**。上游用 `versions_seen[INTERRUPT]` 作为「上次中断时的通道版本水位」（`langgraph/pregel/_algo.py:155-185`）；恢复 / 从该快照重放时 `_first` 把水位设为当前通道版本（`_loop.py:946-951`）⇒ `should_interrupt` 因「自上次中断后无新写入」而**不重复暂停**。只有从断点**之前**重放、且重放节点产生新写入时，静态断点才会再次触发。freegraph 的 `static_ack` 与该水位同构；`update_state` 分叉写入新版本 ⇒ 静态断点会再次触发（故分叉清空 ack）。
- Q: `update_state` 的 `as_node` 省略时如何推断？给出显式节点名时如何影响继续执行的起点？ → A: **沿用上游口径**：省略时，图恰 **1 个节点** ⇒ 使用该节点（上游 `main.py:1904-1908` 同款兜底）；否则从基准快照的版本历史（`versions_seen`）推断「最后一个更新状态的节点」，**MUST NOT** 回退到 `node_versions` / 入口节点；无法无歧义推断 ⇒ `InvalidUpdateError`（消息含 `Ambiguous update, specify as_node`）。新快照的 `next` = `as_node` 的**后继节点集合**（出边 + 条件边 + fan-out（`Send`）按运行期同款路由 / 触发语义在更新后的状态上求值）⇒ 随后 `invoke(None, fork_config)` 从这些后继继续执行。`as_node` 不存在 ⇒ `InvalidUpdateError`（消息点名该节点）。
- Q: 直接对**历史**快照调用 `invoke(Command(resume=...), historical.config)` 时，恢复值写到哪？ → A: **恢复路径只读该 `thread_id` 的最新快照 + pending writes，忽略 `configurable["checkpoint_id"]`**（与 B10F1 的「最新快照」口径一致）。这样：(a) 时间旅行重放 / 分叉后恢复的是**新追加的暂停点**，不会改写历史快照的 pending writes；(b) 与上游 `use-time-travel.md:163-170` 的 `invoke(Command(resume="Bob"), fork_config)` 调用形态兼容（配置中的旧 id 不误导恢复定位）。
- Q: 若最新快照正处于动态中断挂起，而从更早的历史快照分叉出新分支，旧挂起中断怎么恢复？ → A: **允许分叉**；旧 pending 仍完整保留在旧快照，但不再是「最新」⇒ 要恢复它，先对旧快照 `invoke(None, old_snapshot.config)` **重新触发中断**，再对新的暂停点 `Command(resume=...)`。MUST NOT 为旧分支自动复制中断载荷、MUST NOT 让恢复改写旧快照的 pending writes。
- Q: 「v1 只保线性重放 + 单次分叉」应怎么理解？ → A: **每次 `update_state` 只产生一条新分支；同一 thread 可以分叉多次**（历史可有多条分支）。V1 仍只做**线性执行**，不提供并行分支执行、分支树 / 按分支枚举 API 或分支 UI；分支结构由 `parent_config` 读取。
- Q: `stream()` 是否也是 v1 的回放入口？ → A: **否**。B8F2 的 `stream` v1 不读 saver（`_stream.py` 的模块边界），且本 feature 的判定只要求「可从历史 checkpoint 重放」⇒ v1 的**唯一回放入口** = `invoke(None, snapshot.config)`。`stream` 保持 B8F2 的「忽略 checkpointer 恢复」语义（能力边界，非偏离）。**（2026-11-23 发起者确认：保持 B8F2 冻结面 · 选项 A）**
- Q: `update_state` 能否在**全新 thread** 上作为「初始化状态」使用？ → A: **v1 不支持**。FR-005 要求「起点不存在 / thread 不存在」抛明确异常 ⇒ `update_state` MUST 以**已存在**的基准快照为起点（显式 id 或该 thread 的最新快照）。全新会话的状态初始化仍走 `invoke(state)`。上游的「fresh thread `update_state` 初始化」属 v2 能力边界。
- Q: **正常终态** checkpoint 的 replay 是否也写 branch anchor / fork checkpoint？ → A: **不写**；按 SC-016 **零新快照**（更严）。上游文档称终态 replay 是 no-op，但实测 `invoke(None, final.config)` 会写一条 `source="fork"` 快照（**不重跑节点**）⇒ 属**上游自身缺陷 / 不确定**（自研区 ②）；freegraph 取文档口径，登记 **X-06**；差分 D-02 只比较「不执行节点 / 终态一致」，**不比较快照数**。**（2026-11-23 发起者确认）**（anchor 的完整定义见**裁定 10 / FR-026**；非 no-op replay 才写 anchor）

> **对齐结论**：`update_state` 的对外形态、分叉 / 重放语义、`as_node` 后继语义、恢复定位
> 全部按上游 `langgraph 1.2.11` 与 `use-time-travel.md` 照抄；freegraph 只保留
> 已冻结的载体 / id / 父链口径（C19 / B14F1 / B15F1）与本项目红线
> （零第三方、`context` 不持久化、无 async）。少数 v1 能力边界（`task_id` /
> `values=None` / fresh-thread 初始化 / `stream` 回放）在「偏离登记」后以**能力边界**
> 标注，不占偏离编号。**正常终态** replay 的「零新快照」是**更严**口径（**X-06**）：
> 上游文档称 no-op，但实测会写 `source="fork"` 快照（不重跑节点）⇒ 属**上游自身缺陷 / 不确定**（自研区 ②）；freegraph 取文档口径，按 SC-016 不写。

---

## 形态锁定裁定（`/speckit.plan` 不得再翻）

> 提示词要求：`update_state(...)` 的**对外调用形态 MUST 在本 feature 锁定并写死**。
> 本节是锁定结论；实现细节（新增 L2 助手 / 父链推进的落点 / 后继求值的复用方式）由 plan 决定。

### 裁定 1 · `update_state` 的对外签名与返回载体

**锁定：对外方法 = `CompiledGraph.update_state`（L3 编译产物）；签名逐字为：**

```python
update_state(
    config: RunConfig | Mapping[str, Any] | None,
    values: StateDict,
    as_node: str | None = None,
) -> RunConfig
```

| 项 | 锁定值 |
|---|---|
| 方法位置 | `freegraph.graph` 门面返回的编译产物（L3 `CompiledGraph`） |
| 参数 `config` | `RunConfig` / 普通映射 / `None` 三形态；**MUST NOT** 接受裸 `str` / 数字（⇒ `TypeError`）。⚠️ `None` 仅在**类型注解层**接受：解析为空配置后缺 `thread_id` ⇒ **`ValueError`**（不构成成功调用路径） |
| 参数 `values` | `StateDict`（`dict[str, Any]` 的别名）⇒ **MUST** 是 `Mapping`（任意 `Mapping` 运行时复制为 dict）；非 `Mapping`（含 `None`）⇒ **`TypeError`** |
| 参数 `as_node` | `str \| None`；非 `str` / `None` ⇒ `TypeError`；省略 ⇒ 推断；推断失败 / 不存在 ⇒ `InvalidUpdateError` |
| 返回 | **`RunConfig`**（新快照的 config：`thread_id` = 生效 thread；`configurable["checkpoint_id"]` = 新 id；`context` = `None`）；**不是** `StateSnapshot`、**不是**裸 dict |
| 会话标识 | `configurable["thread_id"]` 优先于顶层 `thread_id`（`RunConfig.resolved_thread_id()` 口径）；缺失 / 空串 ⇒ `ValueError`（点名 `thread_id`） |
| saver 来源 | 只用 `compile(checkpointer=...)` 注入的 saver；未挂 / `True` / `False` ⇒ `ValueError`（消息含 `No checkpointer set`） |
| 无 `task_id` | v1 **不暴露** `task_id` 关键字（能力边界）；不接受 `values=None` 的「清空任务」形态 |
| 对外导出 | `freegraph.graph` 门面**不新增**导出的模块级函数；`update_state` 只是编译产物方法 |

**L1 协议改动**：`CompiledGraph.update_state` 的 `config` 注解放宽为
`RunConfig | Mapping[str, Any] | None`，返回类别由 `StateSnapshot` 改为 **`RunConfig`**。
其余五个方法、其余 L1 符号面与字段面**一律不改**。本改动走
「登记 + 回溯修订 + 发起者追认」（见「破冻结面回溯修订清单」R-1）。

**理由**：① 上游 `update_state` 返回 `RunnableConfig`
（`langgraph/pregel/main.py:2515-2526`）⇒ freegraph 以 `RunConfig` 对齐；
② `use-time-travel.md:78-96` 的 `fork_config = graph.update_state(...)` →
`graph.invoke(None, fork_config)` 形态要求返回的是**可继续执行的 config**；
③ B7F3 的 CF-05 已冻结双形态 `config` 载体边界 ⇒ 本 feature 只沿用、不翻译；
④ `task_id` / `values=None` 属并行 / 多分支能力 ⇒ v1 明确不做。

### 裁定 2 · 基准 checkpoint 的定位与「起点不存在」

**锁定：`update_state` 以「显式 `configurable["checkpoint_id"]` 指定」或「该 thread 的最新快照」
为唯一基准；基准必须已存在。**

| 场景 | 锁定行为 |
|---|---|
| `configurable["checkpoint_id"]` 为非空 `str` | 以该 id 的已存快照为基准；该 id 在本 thread **不存在** ⇒ **`ValueError`**（消息点名 `checkpoint_id`） |
| `configurable["checkpoint_id"]` 缺失 / `None` / 空串 | 以该 `thread_id` 的**最新**快照为基准（`get_tuple` 同款） |
| `thread_id` 不存在 / 该 thread 无任何快照 | ⇒ **`ValueError`**（消息点名 `thread_id` / 无基准快照）；**MUST NOT** 静默新建 thread 或写入初始快照 |
| `checkpoint_ns` 非空 | ⇒ `ValueError`（v1 无子图；空串 / 缺失视为 `""`） |
| 基准快照为**静态挂起** | 合法；`interrupts == ()` 与 `suspension_kind` / `static_ack` 原样参与基准读取，不要求动态中断载荷；**新快照的静态标记 MUST 清空**（见裁定 4） |
| 基准快照为**动态中断挂起** | 合法；但新快照 **MUST NOT** 复制原快照的 pending `__interrupt__`（见裁定 4） |

**理由**：① 上游 `perform_superstep` 用 `get_tuple(config)` 取基准（`main.py:1650-1666`）；
② FR-005 / SC-004 要求「起点不存在」可由**异常类型 + 点名**判定；
③ B10F1 已冻结「恢复路径读最新快照」；本 feature 让 `update_state` 也遵循「显式 id 优先、否则最新」，
与读取面 `get_state` 的定位口径一致。

### 裁定 3 · 新快照的 id / 父链 / 历史完整性（只追加）

**锁定：`update_state` 产生的新快照通过**同一 `put` 渠道追加**；id = 该 thread 的
`MAX(checkpoint_id) + 1`（B14F1 顺位 id 空间）；`parent_config` = **基准快照的 config**；
原快照一律不改。**

- 新 id MUST 沿用 `f"{n:032d}"`（字典序 == 数值序）；MUST NOT 另造 id 空间；
  MUST NOT 覆盖已有 id；MUST NOT 重排父链。
- 新快照的 `parent_config` MUST 指向**本次的基准 checkpoint**（不是 thread 的最新快照，
  也不是上一分支的 tip）⇒ 分支结构由 `parent_config` 链表达。
- 后续由 `invoke(None, returned_config)` 产生的快照 MUST 继续链在**本分支的新快照**之后
  （不是回到原 thread 的旧最新）⇒ 即：一次分叉 / 重放内部是**线性追加**，首条边从基准点接出。
- **只追加**：原快照的 `values` / `next` / `config` / `metadata` / `created_at` /
  `parent_config` / `tasks` / `interrupts` 与 pending writes MUST NOT 被修改、删除或重排。
- `get_state_history` 继续可枚举：原快照数 + 本分支新增快照数；顺序仍按 `checkpoint_id`
  **倒序**（最新在前）；`get_state({checkpoint_id})` 对任一 id 仍可取回原快照。
- v1 **不提供**分支树 / 按分支枚举 API；历史是**扁平倒序列表**，分支结构由 `parent_config` 读取。
  这是「线性重放 + 每次调用一条新分支；同一 thread 可多次分叉」的冻结口径。

**实现约束（对 `put` 的最小扩展）**：当 `put(config, ...)` 的
`configurable["checkpoint_id"]` 为**非空字符串**时，新快照的 `parent_config` MUST = 该 id；
缺失 / 空串时保持 B14F1 的「上一快照（最新）」语义。该扩展**不改变可观察行为**：运行期常规写盘
MUST 以「当前 checkpoint id」作为 `configurable["checkpoint_id"]` 传给 `put`（首次写入时为空），
故父链仍逐条接续；仅当调用方传入**与最新快照不同**的显式历史 id 时分叉，父链才指向该历史点。
上述两点合起来登记为**跨 feature 回溯修订**（R-2）。运行期在每个新快照写出后 MUST 把
「当前 checkpoint id」推进到新 id，使同一分支内的父链逐条接续。

**理由**：① 上游 `put` 的 parent = `config["configurable"].get("checkpoint_id")`
（`langgraph/checkpoint/memory/__init__.py:459`）；`update_state` 的 `checkpoint_config`
由 `saved.config` 派生 ⇒ parent 指向被分叉点（`main.py:1656-1666`）；
② D-01 / D-03 要求「同一 `put` 渠道追加 + `parent_config` 父链定位」；
③ 只追加保证 P3 / SC-002 的「原历史完整可枚举」。

### 裁定 4 · `update_state` 的合并语义与写入归属

**锁定：`values` 按**与普通节点写入 / 图输入写入完全相同的通道语义（C6）**合并；
`as_node` 只决定「归属节点」与「继续执行的起点」，MUST NOT 另造归约规则。**

- **合并（C6）**：对 `values` 的每个 key 走**同一条** `Channel.update([value])` 路径：
  - 覆盖型通道 ⇒ **覆盖**为新值；
  - 归约型通道 ⇒ **按归约器追加 / 归约**（如 `operator.add` ⇒ `old + [new]`）；
  - 未知 key（schema 中不存在）⇒ **`InvalidUpdateError`**（`invalid_keys` = 未知 key 元组）；
  - 一次 `update_state` 内每个 key **一个值**；MUST NOT 借 `update_state` 绕过
    `InvalidChannelUpdateError` 的「单次写入单值」规则。
- **不可变**：合并 MUST 在**副本**上完成；存储中的基准快照与 pending writes MUST NOT 被修改；
  不可合并 / 不可深拷贝 ⇒ 原异常传播，存储**零变化**（原子性）。
- **`as_node` 的语义**：
  - 显式给出 ⇒ MUST 是已存在的节点名（否则 `InvalidUpdateError`，消息点名该节点）；
  - 省略且图恰 **1 个节点** ⇒ 使用该节点（上游 `main.py:1904-1908` 同款兜底）；
  - 省略且多节点 ⇒ 从基准快照的 `versions_seen` 推断「最后一个更新状态的节点」；
    **MUST NOT** 回退到 `node_versions` / 入口节点；无法无歧义推断 ⇒
    `InvalidUpdateError`（消息含 `Ambiguous update, specify as_node`）；
  - 新快照的 `next` = `as_node` 的**后继节点集合**（出边 + 条件边 + fan-out（`Send`）按运行期
    同款路由 / 触发语义在更新后的状态上求值，按节点名序）；无后继 ⇒ `next == ()`；
  - 记录口径上等价于「`as_node` 产出了这批写入」；MUST NOT 真执行 `as_node` 的节点函数。
- **新快照的其它字段**：
  - `values` = 基准 `values` 经 C6 合并 `values` 后的**完整稀疏状态**；
  - `next` = 如上（`as_node` 的后继）；
  - `interrupts` = `()`；`tasks` = `()`（`update_state` 不执行任务）；
  - `metadata` = 与运行期同款的内部调度账本投影（`next` / `interrupts` / `tasks` /
    `suspension_kind` / `static_ack` / `scheduler`）；`scheduler` MUST 与更新后的
    版本 / 触发状态一致；
  - **静态标记清空**：`suspension_kind = None`、`static_ack = None` ⇒ 新分支是新的执行起点；
    若后继再次命中 `interrupt_before` / `interrupt_after`，按正常规则**再次暂停**；
    MUST NOT 保留基准快照的静态 ack 来绕过审批点。⚠️ 该清空**只适用于 `update_state` 新分支**；
    从静态快照 `invoke(None, static_snapshot.config)` 的重放**保留** `static_ack`（裁定 6）。
  - pending writes = **不复制**基准快照的 pending `__interrupt__` / `__resume__`；
    新快照本身不携带 pending writes。

**理由**：① 上游文档逐字「values are applied using the specified node's writers
(including reducers)」（`use-time-travel.md:104`）；「update is treated the same as a node
update ... with reducers accumulate」（`checkpointers.md:255`）；② C6 是已冻结的合并语义
⇒ MUST 复用同一条通道更新路径，不得为 `update_state` 写第二套；③ `as_node` 后继语义
来自 `use-time-travel.md:104` 与 `main.py:1875-2008` 的 `as_node` 推断 / writers 执行。

### 裁定 5 · 重放（replay）的对外入口与语义

**锁定：v1 的**唯一**回放入口 = `invoke(None, snapshot.config)`；**
`snapshot.config` 必须携带非空的 `thread_id` + `checkpoint_id`。**

| 项 | 锁定值 |
|---|---|
| 入口 | `CompiledGraph.invoke(None, snapshot.config)`；`snapshot` 来自 `get_state` / `get_state_history` |
| 起点不存在 | `configurable["checkpoint_id"]` 非空但该快照不存在 ⇒ **`ValueError`**（点名 `checkpoint_id`）；MUST NOT 回退到「最新快照」或「全新会话」 |
| 未挂 saver / `True` / `False`（**仅当入口携带显式 `checkpoint_id`**） | ⇒ **`ValueError`**（消息含 `No checkpointer set`）；MUST NOT 回退到「全新会话」；无显式 id 的普通 `invoke` 保持 B15F1 / B7F3 行为 |
| `checkpoint_ns` 非空 | ⇒ **`ValueError`**（v1 无子图） |
| 状态恢复 | 从**指定快照**恢复 `values` + 调度账本 + `next`（同 B15F1 的读取口径）；**不**合并 pending writes 进 `values` |
| 继续执行 | 从 `snapshot.next` 的节点开始**重新执行**（不是读缓存）；节点后的 LLM / API / 中断都会再次触发，结果可能与当时不同 |
| 非 no-op 的 anchor | 非**正常终态**的重放 MUST 先通过同一 `put` 渠道写一条 branch anchor（裁定 10 / FR-026） |
| 正常终态快照 | **正常终态**（`next == ()` 且无 fanout / 无静态挂起 / 无 pending 中断）的重放是 **no-op**：不执行节点、**不产生任何新快照**；`static_after` 的 `next==()` 不是正常终态（按 FR-011 继续并写完成快照） |
| 历史影响 | 只把**新产生**的快照追加到同一 thread；原快照逐项不变；新快照父链从**重放点**接出 |
| `stream` | v1 **不是**回放入口；`stream` 保持 B8F2 的「忽略 checkpointer 恢复」语义（能力边界） |
| `Command` | 回放入口只接受 `None`；`Command(resume=...)` 走**恢复**路径（裁定 6），不属重放 |

**理由**：① 上游文档逐字「Invoke the graph with a prior checkpoint's config to replay from
that point」与「Replay re-executes nodes—it doesn't just read from cache... Replaying from the
final checkpoint (no next nodes) is a no-op」（`use-time-travel.md:18-72`）；
② B10F1 已冻结 `invoke(None, ...)` 的「会话连续 / 恢复轮」语义，本 feature 只把它接到
**任意历史 checkpoint**；③ 不读缓存、不伪造历史（D-01 / D-02）。

### 裁定 6 · 中断恢复与时间旅行的组合

**锁定：恢复路径（`Command(resume=...)`）只读该 thread 的**最新快照 + pending writes**，
忽略 `configurable["checkpoint_id"]`；时间旅行重放 / 分叉后恢复的是**新追加的暂停点**。**

- **动态中断的重放**：从历史中断点 `invoke(None, historical.config)` ⇒ 被中断节点**重跑**，
  再次 `interrupt()` 暂停 ⇒ 追加一条新暂停快照（父链接续重放点）。随后
  `invoke(Command(resume=...), <同一 thread 的 config>)` ⇒ 恢复**最新**暂停点并跑完。
- **恢复定位**：`Command(resume=...)` 的 `get_tuple`  MUST 用「最新快照」（`configurable`
  中的旧 `checkpoint_id` 被**忽略**）；MUST NOT 把 `__resume__` pending writes 写到
  历史快照上 ⇒ **原历史快照的 pending writes 零变化**。
- **分叉后的旧挂起**：若最新快照原本处于动态中断挂起，而用户从更早的历史点分叉，
  旧 pending 仍完整保留在旧快照，但不再是「最新」⇒ 要恢复它，先对旧快照
  `invoke(None, old_snapshot.config)` **重新触发中断**，再对新的暂停点 `Command(resume=...)`；
  MUST NOT 自动把旧中断载荷复制到新分支。
- **静态挂起的重放**：历史静态快照（`interrupts == ()` + 静态 `suspension_kind` /
  `static_ack`）MUST 可直接作为重放起点；`invoke(None, static_snapshot.config)` MUST
  **保留 `static_ack`**（B13F1 FR-007 · 上游 `versions_seen[INTERRUPT]` 水位口径）⇒ 直接越过
  已确认的静态断点继续；若重放起点在断点**之前**、重放节点产生新写入 ⇒ 静态断点 MUST
  **再次触发**；恢复 MUST NOT 要求动态中断载荷；MUST NOT 假设「`next` 非空 ⇒ 必有中断」。
- **分叉后的中断**：`update_state` 产出新的分支点后，`invoke(None, fork_config)` 可按正常
  执行再次触发中断；随后按上款恢复。
- **边界**：「恢复」与「时间旅行」**并存但独立**：恢复不调用 `update_state`，
  `update_state` / 重放不调用恢复路径的「改写」逻辑；两者只共享 `put` / `put_writes` 存储渠道。
- **历史保护**：重放 / 分叉路径产生的任何 pending writes（`__resume__` / 真异常 + 中断留痕）
  MUST 只落在**本次新追加**的 checkpoint 上；MUST NOT 写入被分叉 / 被重放的原快照。

**理由**：① B10F1 D-7 要求两套语义**并存但独立**；② B13F1 D-6 要求静态快照可作重放起点；
③ 上游文档「interrupts are always re-triggered during time travel... pauses for a new
`Command(resume=...)`」（`use-time-travel.md:128-170`）；④ 恢复写 `__resume__` 是「最新快照」
的正常恢复，不是改写历史。

### 裁定 7 · `context` 不持久化 / 不从历史恢复

- `update_state` MUST NOT 读取、保存、合并、透出 `RunConfig.context`；
  新快照的 `config.context` MUST 为 `None`；`metadata` / `scheduler` / pending writes
  MUST NOT 出现 `context`。
- 重放 MUST NOT 从历史快照恢复 `context`；本次 `invoke` 的 `RunConfig.context` 只影响
  本次运行，与历史快照无关。
- MUST NOT 回退到 `configurable` 承载 `context`；MUST NOT 重新引入节点别名。

### 裁定 8 · 失败信号汇总（不新增 L1 异常类型）

| 场景 | 锁定行为 |
|---|---|
| 未挂 saver / `True` / `False`（`update_state` / **显式 `checkpoint_id` 重放**） | `ValueError`（消息含 `No checkpointer set`） |
| `config` 缺 / 空 `thread_id` | `ValueError`（点名 `thread_id`） |
| `config` 是裸 `str` / 数字 | `TypeError`（`resolve_config` 同款；只接受 `RunConfig` / 映射 / `None`） |
| 显式 `checkpoint_id` 不存在 | `ValueError`（点名 `checkpoint_id`） |
| thread 不存在 / 无基准快照 | `ValueError`（点名 `thread_id` / 无基准快照） |
| `checkpoint_ns` 非空 | `ValueError`（v1 无子图） |
| `values` 等非 `Mapping` | `TypeError` |
| `values` 含 schema 未知 key | `InvalidUpdateError`（`invalid_keys` 非空） |
| `as_node` 非 `str` / `None` | `TypeError` |
| `as_node` 不存在 | `InvalidUpdateError`（消息点名该节点） |
| `as_node` 省略且无法无歧义推断 | `InvalidUpdateError`（消息含 `Ambiguous update, specify as_node`） |
| 合并失败 / 深拷贝失败 | 原异常传播；存储**零变化**（原子性） |

- MUST NOT 新增 L1 异常类型；上述信号全部复用既有 `ValueError` / `TypeError` /
  `InvalidUpdateError` / `FreegraphError`（B12F1 的「更严失败信号」口径）。
- 消息 MUST 点名出错对象（`thread_id` / `checkpoint_id` / 节点名 / key）⇒ 用户无须解析文本
  即可定位。

### 裁定 9 · v1 的能力边界（不属于偏离编号）

| 能力 | v1 处置 | 上游对照 | 理由 |
|---|---|---|---|
| 并行任务关联 `task_id` | **不暴露** | `main.py:2515-2526` 接受 `task_id` | v1 只保线性 + 每次调用一条分支（可多次分叉） |
| `values=None, as_node=END` 清空任务 | **不支持**（`None` ⇒ `TypeError`） | `main.py:1668-1730` | 属并行 / 多分支语义 |
| 全新 thread 上的 `update_state` 初始化 | **不支持**（须已有基准快照） | `perform_superstep` 的 `saved is None` 分支 | FR-005 要求起点不存在即失败；初始化走 `invoke(state)` |
| 上游 `input_channels` 的省略 `as_node` 兜底 | **不提供** | `main.py:1909-1911` | v1 无 input channel（research D-03）；多节点且无 `versions_seen` ⇒ 显式失败 |
| `stream()` 回放 | **不支持** | 上游 `stream` 不专门定义重放 | B8F2 `stream` v1 不读 saver |
| 分支树 / 多分支枚举 API | **不提供** | 上游也无独立分支树 API | 用 `parent_config` 读取；v2 再加 UI |
| async `aupdate_state` | **不提供** | 上游有 | v1 无 async |
| `Store` / Postgres | **不提供** | — | B17 已砍 / v2 |

> 以上均属**能力边界**（与 B15F1 P-17 的「配置级 checkpointer / 子图」同款处置），
> **不占偏离编号**、不新增门禁。

### 裁定 10 · branch anchor（非 no-op replay / 历史续跑的首条分支快照）

**锁定：以显式历史 `checkpoint_id` 为起点、且本次不是「正常终态 no-op」的重放 / 历史续跑，
MUST 在**执行前**先通过同一 `put` 渠道写一条 **branch anchor**；原快照零变化。
`update_state` 产出的分支快照**兼任**本分支 anchor；从该分支快照再执行时 MUST NOT 另写 anchor。**

| 项 | 锁定值 |
|---|---|
| 触发 | 入口携带**显式历史 `checkpoint_id`**，且满足任一：`next` 非空 / 有 fanout / 静态挂起 / 有 pending 中断 / 本次 `input` 为非空状态字典 |
| 不触发（no-op） | **正常终态**（`next == ()` 且无 fanout / 无静态 / 无 pending）且 `input` 为 `None` 或空 dict ⇒ 零新快照（SC-016）；`static_after` 的 `next==()` 不属正常终态（FR-011） |
| 不触发（已是分支 anchor） | 入口的显式 id 指向 `update_state` 产出的**分支快照**（即 `fork_config`）⇒ 该分支快照**兼任**本分支 anchor；`invoke(None, fork_config)` MUST NOT 再写 anchor；分支快照初始 pending 为空，可承载本分支首轮 pending 留痕，但 MUST NOT 回写原历史快照 |
| 字段 | 8 字段 `StateSnapshot`；`values` / `next` / `metadata.scheduler` / `metadata.suspension_kind` / `metadata.static_ack` 与**基准快照**一致；`metadata.interrupts == ()`、`metadata.tasks == ()` |
| `config` | `thread_id` = 生效 thread；`configurable["checkpoint_id"]` = 新 id；`context is None` |
| `parent_config` | **基准快照的 config** |
| pending writes | **初始空**；基准的动态 pending **不复制**（执行时仍从基准 history 读取） |
| id | 该 thread `MAX(checkpoint_id) + 1`（`f"{n:032d}"`）；同一 `put` 渠道；**不覆盖**已有 id |
| 后续 | anchor 写入后把「当前 checkpoint id」推进为 anchor id；后续执行快照逐条链在 anchor 之后 |
| 历史影响 | 只追加；原快照 8 字段与 pending writes 逐项不变；`get_state_history` 继续倒序可枚举 |

- **作用**：让首轮的 `__interrupt__` / `__resume__` / 真异常中断留痕只落在**新追加**的
  checkpoint 上（SC-014），不写被重放 / 被续跑的原快照。
- **分支快照兼任 anchor**：`update_state` 产出的分支快照就是该分支的首条快照 / anchor；
  后续 `invoke(None, fork_config)` 不再追加 anchor。执行期的 pending 留痕可落该分支快照
  或后续新快照，但 MUST NOT 落原历史快照；分支快照的初始 pending 为空。
- **与 replay / B7F3 续跑的边界**：`invoke(None, snapshot.config)` 是**重放**；
  `invoke(state_dict, historical.config)` 是 **B7F3 的「会话连续 + 状态字典输入」续跑**、
  **不是**重放入口，但二者**都**以显式历史 id 为起点 ⇒ **都**适用本裁定的 anchor 保护；
  续跑不因 anchor 改变其「dict 叠加 + 节点重新触发」语义。
- **计数口径**：一次非 no-op replay（从**既有历史快照**起）的历史增量 =
  **1 条 anchor + 后续执行快照**；一次 `update_state` 分叉 = **1 条分支快照（兼任 anchor）+
  后续执行快照**，**不另写 anchor**；正常终态 replay = **0**。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 从历史某一步重放（Priority: P1）

作为用户，我跑到第 3 步时结果不对，希望**回到第 2 步的状态重新跑一遍**，以复现并定位问题。

**Why this priority**：这是本 feature 的判定核心——「可从历史 checkpoint 重放」。

**Independent Test**：跑一张 `a → b → c` 的图 → `get_state_history` 找到第 2 步后的快照 →
`invoke(None, that_snapshot.config)` ⇒ `b` / `c` **重新执行**，最终状态与「第 2 步状态 + 后续逻辑」
一致；原历史快照逐项不变。

**Acceptance Scenarios**：

1. **Given** 一个已跑完的线性图，**When** 从**每一个**历史 checkpoint（除去 `next == ()` 的**正常终态**：无 fanout / 无静态 / 无 pending）
   `invoke(None, snapshot.config)`，**Then** 都从该快照的 `next` 重新执行并到达一致的终态。
2. **Given** 一个 `next == ()` 的**正常终态**快照，**When** `invoke(None, snapshot.config)`，
   **Then** 不执行节点、不产生新快照（no-op）。
3. **Given** 重放引用了不存在的 `checkpoint_id`，**When** `invoke(None, config)`，
   **Then** 抛 `ValueError`（点名 `checkpoint_id`），**不**回退到最新 / 全新会话。

---

### User Story 2 - 改状态再继续（分叉）（Priority: P1）

作为用户，我回到第 2 步，把某个字段改成我想要的值再继续，得到一条**新分支**。

**Why this priority**：这是 `update_state` 的对外价值；用户要「试另一条分支」。

**Independent Test**：`fork_config = graph.update_state(cp.config, values={"field": ...})` ⇒
断言新快照的 `values` 已按 C6 合并、`parent_config` = 基准快照；`graph.invoke(None, fork_config)`
从新分支继续；**原快照逐项不变**。

**Acceptance Scenarios**：

1. **Given** 一个历史快照，**When** `update_state(cp.config, {"x": 1})`，
   **Then** 返回 `RunConfig`（新 `checkpoint_id`）；新快照 `values["x"] == 1`；
   `parent_config` 指向 `cp.config`；`get_state_history` 仍含原快照。
2. **Given** 归约型通道（如 `messages: Annotated[list, operator.add]`），
   **When** `update_state(cp.config, {"messages": ["new"]})`，
   **Then** 新快照的 `messages` = 原值 + `["new"]`（不是覆盖）。
3. **Given** `as_node="a"`，**When** `update_state(cp.config, {"x": 1}, as_node="a")`，
   **Then** 新快照 `next` = `a` 的后继节点；`invoke(None, fork_config)` 从这些后继继续。
4. **Given** `values` 含 schema 未知 key，**When** `update_state(...)`，
   **Then** 抛 `InvalidUpdateError`，存储零变化。

---

### User Story 3 - 重放不产生历史污染（Priority: P1）

作为用户，我重放了很多次，希望原有 checkpoint 历史**仍然完整可枚举**。

**Why this priority**：这是 P3 的独立验收，也是本 feature 最易返工的风险点
（「重放」与「分叉」互相污染）。

**Independent Test**：记录重放前某 thread 的所有 `checkpoint_id` 与 8 字段；重放 / 分叉多次后，
逐 id 取回并断言 8 字段逐项不变；`get_state_history` 的数量 = 原数量 + 新分支数量，
顺序仍为 `checkpoint_id` 倒序。

**Acceptance Scenarios**：

1. **Given** 一个含 N 条快照的 thread，**When** 从历史点重放 3 次，
   **Then** 原 N 条快照的 8 字段与 pending writes 逐项不变；新快照只追加。
2. **Given** 同一 thread 已分叉，**When** 再次从另一历史点分叉，
   **Then** 每个新分支的首条快照 `parent_config` = 各自的分叉点；原父链不被重排。
3. **Given** 重放产生新快照后，**When** `get_state_history`，
   **Then** 仍可按 `checkpoint_id` 倒序枚举全部快照（含两个分支）。

---

### User Story 4 - 中断 / 静态挂起与时间旅行的组合（Priority: P2）

作为用户，我从一个**中断点**重放，或从一个**静态挂起**的历史快照继续；`Command(resume=...)`
语义仍然可用。

**Why this priority**：宪法原则 IV 要求 interrupt 与 time-travel 四类能力**同时可用**；
B10F1 / B13F1 已把两套语义的边界写死。

**Independent Test**：跑一张含 `interrupt()` 的图到挂起 → 从挂起前的历史快照
`invoke(None, cp.config)` ⇒ 再次暂停并追加新暂停快照 → `invoke(Command(resume="X"), thread_config)`
⇒ 恢复**最新**暂停点跑完；原历史快照的 pending writes 不变。
静态挂起用例：从 `interrupts == ()` 的历史静态快照直接重放，不要求动态载荷。

**Acceptance Scenarios**：

1. **Given** 一个动态中断的历史快照，**When** 从它 `invoke(None, ...)`，
   **Then** 被中断节点重跑并再次暂停；恢复用最新暂停点，原快照 pending writes 零变化。
2. **Given** 一个静态挂起的历史快照，**When** `invoke(None, snapshot.config)`，
   **Then** 按 `next` 继续，**不**要求 `interrupts` 非空、**不**抛「缺动态载荷」。
3. **Given** 从分叉点 `update_state` 后执行到中断，**When** `Command(resume=...)`，
   **Then** 恢复的是新分支的暂停点；原历史仍完整。

---

### User Story 5 - 明确的失败与边界（Priority: P2）

作为用户，我希望起点不存在、thread 不存在、未挂 saver、非法写入等情形**立即失败**，
且错误可判定，而不是静默跑错分支。

**Why this priority**：时间旅行一旦静默回退到「最新 / 全新会话」，会污染排查结论；
FR-005 / SC-004 要求明确异常。

**Independent Test**：分别构造未挂 saver、缺 `thread_id`、非法 `checkpoint_id`、
未知 state key、`as_node` 歧义 / 不存在等场景，断言异常类型 + 消息点名。

**Acceptance Scenarios**：

1. **Given** 未挂 saver，**When** `update_state` / **显式 `checkpoint_id` 的重放**，
   **Then** `ValueError`（含 `No checkpointer set`）；无显式 id 的普通 `invoke` 行为不变。
2. **Given** `checkpoint_id` 不存在，**When** `update_state` / 重放，
   **Then** `ValueError`（点名 `checkpoint_id`），存储零变化。
3. **Given** `as_node` 省略且无法推断 / 指向不存在节点，
   **When** `update_state`，**Then** `InvalidUpdateError`（消息点名问题）。

### Edge Cases

- **`config=None`**：类型层接受；解析后缺 `thread_id` ⇒ `ValueError`（不是成功路径）。
- **`config` 为裸 `str` / 数字**：`TypeError`。
- **`configurable["thread_id"]` 与顶层 `thread_id` 冲突**：前者优先（`RunConfig.resolved_thread_id()`）。
- **`checkpoint_id` 为 `None` / 空串**：`update_state` 视为「未指定」⇒ 用该 thread 最新快照；
  不是「非法 id」。
- **`checkpoint_id` 为显式非空但不存在**：`ValueError`；**MUST NOT** 回退到最新。
- **thread 不存在 / 空历史**：`update_state` ⇒ `ValueError`；**MUST NOT** 新建 thread。
- **`checkpoint_ns` 非空**：`ValueError`（v1 无子图）。
- **无显式 `checkpoint_id` 的普通 `invoke` / 续跑**：未挂 saver 时保持 B15F1 / B7F3 行为，
  不因本 feature 改为 `No checkpointer set`；本 feature 的 saver 强制只作用于 `update_state`
  与显式 `checkpoint_id` 的重放。
- **`values={}`（空映射）**：合法；仍产生一个新分支快照（`next` 按 `as_node` 后继），
  但 `values` 内容不变。
- **`values` 含未知 key**：`InvalidUpdateError`；`invalid_keys` 保序。
- **归约型通道**：`values` 按归约器追加；不可变类型归约失败 ⇒ 原异常、存储零变化。
- **覆盖型通道**：直接覆盖。
- **同一 key 在一次 `values` 中出现两次**：不可能（`Mapping` 单键单值）。
- **`as_node` 显式**：必须存在；否则 `InvalidUpdateError`。
- **`as_node` 省略**：图恰 1 个节点 ⇒ 该节点；多节点 ⇒ 从基准快照 `versions_seen` 推断；
  歧义 / 无历史 ⇒ `InvalidUpdateError`；MUST NOT 回退 `node_versions` / 入口节点。
- **`as_node` 无后继**：新快照 `next == ()`；`invoke(None)` 为 no-op。
- **基准快照为静态挂起**：可直接作为 `update_state` 基准；`suspension_kind` / `static_ack` 原样参与基准读取，但**新快照 MUST 清空静态标记**；若后继再次命中静态断点 ⇒ 正常再次暂停；不得绕过审批点。
- **基准快照为动态中断**：新快照不复制 pending `__interrupt__`；不自动恢复。
- **重放正常终态快照**：no-op，零新快照；`static_after` 的 `next==()` 不是正常终态，按 FR-011 继续并写完成快照。
- **重放中断快照**：节点重跑、再次暂停；恢复走最新暂停点。
- **重放静态挂起快照**：`invoke(None, static_snapshot.config)` **保留 `static_ack`**，越过已确认的
  静态断点继续；从断点**之前**重放且产生新写入时，静态断点**再次触发**；
  `update_state` 新分支则清空 ack（与前者不同，均按 B13F1 / 上游水位口径）。
- **最新快照挂起时从更早历史点分叉**：允许；旧 pending 留在旧快照但不再是「最新」；
  要恢复它 MUST 先对旧快照 `invoke(None, old_snapshot.config)` 重新触发中断，
  再对新的暂停点 `Command(resume=...)`；MUST NOT 自动复制旧中断载荷。
- **`invoke(state_dict, historical.config)`**：沿用 B7F3 的「会话连续 + 状态字典输入」语义
  （以该历史快照为基准、把 dict 按 C6 叠加、从 `snapshot.next` 继续），**不是**本 feature 的
  「重放」入口（重放 = `invoke(None, ...)`）；它仍只追加新分支，且因以显式历史 id 为起点，
  MUST 按裁定 10 / FR-026 先写 branch anchor 以保护原快照；若该显式 id 已是
  `update_state` 分支快照（兼任 anchor）则**不再写**额外 anchor。
- **重放 / 分叉期间发生真异常 + 中断**：中断留痕只写新追加的 checkpoint，不写原快照；
  异常类型 / 消息 / identity 不变。
- **多次重放同一历史点**：每次各产生一条新分支首快照，`parent_config` 都指向同一分叉点；
  原快照不变；历史中出现多个同父分支（扁平列表）。
- **`update_state` 返回值被丢弃**：不影响存储（新快照已提交）；用户仍可用
  `get_state({"thread_id": ...})` 取最新。
- **`update_state` 返回的 `RunConfig` 再传给 `update_state`**：以该新快照为基准，继续分叉（合法）。
- **`update_state` 分叉后再 `invoke(None, fork_config)`**：分支快照兼任 anchor，**不**再追加
  anchor；历史增量 = 分支快照 + 执行快照；分支快照初始 pending 为空，首轮 pending 留痕
  可落该分支快照或后续新快照，但 MUST NOT 回写原历史快照。
- **`context` 非空**：不出现在新快照 / metadata / scheduler / pending writes；
  `snapshot.config.context is None`。
- **`SqliteSaver` 与 `MemorySaver`**：两者 MUST 语义一致（同操作序列的 8 字段 / 父链 / 历史顺序一致；
  `created_at` 只比格式）。
- **JSON 纯数据边界**：`SqliteSaver` 下不可 JSON 序列化的 `values` ⇒ `TypeError` 且零写入
  （B15F1 X-05 已登记）；`MemorySaver` 可存非 JSON 对象（深拷贝）。
- **上游版本漂移**：换 `langgraph` 版本后，本 spec 的全部行号 MUST 重新核实。

---

## Upstream Parity *(mandatory — 宪法原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11**（取证于 **2026-11-23** · 本仓库 `.venv`）；
文档镜像 **`harness/docs/oss/python/langgraph/use-time-travel.md`** 与
**`harness/docs/oss/python/langgraph/checkpointers.md`**。上游 `update_state` /
`bulk_update_state` / `MemorySaver.put` 的源码作为行为锚点；freegraph 只保留已冻结的
载体 / id / 父链口径（C19 / B14F1 / B15F1）与红线（零第三方、`context` 不持久化、无 async）。

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | `update_state` 返回载体 | `langgraph/pregel/main.py:2515-2526`（`(config, values, as_node=None, task_id=None) -> RunnableConfig`） | `(config, values, as_node=None) -> RunConfig`；**不暴露 `task_id`** | SAME（返回载体；`task_id` 见 P-17 能力边界） | 返回「可继续执行的 config」是时间旅行的前提；`task_id` 属并行任务 |
| P-01b | `update_state` 的 `config` 载体 | 上游 `RunnableConfig` | `RunConfig \| Mapping[str, Any] \| None` | **DIFF（X-01）** | B7F3 CF-05 已冻结双形态边界；本 feature 只沿用 |
| P-02 | 未挂 checkpointer | `main.py:1617`（`ValueError("No checkpointer set")`） | 同款 `ValueError`，消息含 `No checkpointer set` | SAME | 照抄失败信号 |
| P-03 | 基准快照定位 | `main.py:1650-1666`（`saved = checkpointer.get_tuple(config)`） | 显式 `checkpoint_id` 优先；缺省取该 thread 最新 | SAME（基准定位） | 读取面 `get_state` 同款 |
| P-03b | 显式 `checkpoint_id` 不存在 | 上游部分入口实测 `ValueError` / `KeyError` / 空结果 | 明确 `ValueError`（点名 `checkpoint_id`） | **STRICTER（X-05）** | FR-005 / FR-010 要求明确失败；显式失败优于静默回退 |
| P-04 | 只追加 / 原历史完整 | `use-time-travel.md:84`（「does not roll back... original execution history remains intact」） | 新 id = MAX+1；原 8 字段与 pending writes 逐项不变 | SAME | 照抄上游语义 |
| P-05 | `parent_config` = 被分叉点 | `langgraph/checkpoint/memory/__init__.py:430-473` · `:459`（parent = `config["configurable"].get("checkpoint_id")`） | 显式 `configurable["checkpoint_id"]` 时 parent = 该 id；否则保持 B14F1「最新」 | SAME（对 `put` 的最小扩展 · R-2） | 分支结构由父链表达；既有调用零变化 |
| P-06 | `values` 走归约器 / 覆盖规则 | `use-time-travel.md:104` · `checkpointers.md:255` · `main.py:1950-2008`（`run.invoke` + `apply_writes`） | 同一 `Channel.update([value])` 路径（C6）；未知 key ⇒ `InvalidUpdateError` | SAME | 复用 C6；不写第二套合并 |
| P-07 | `as_node` 省略时的推断 | `main.py:1875-1935`（单节点兜底；从 `versions_seen` 取最后更新者；歧义 ⇒ `InvalidUpdateError("Ambiguous update, specify as_node")`） | 单节点兜底 + `versions_seen` 推断同款；歧义 ⇒ 同消息要点；MUST NOT 回退 `node_versions` | SAME | 照抄上游（`input_channels` 兜底属 v1 能力边界，见裁定 9） |
| P-08 | `as_node` 不存在 | `main.py:1937` / `:1946`（`InvalidUpdateError(f"Node {as_node} does not exist")`） | 同款异常类型；消息点名节点 | SAME | 照抄 |
| P-09 | 继续执行的起点 = `as_node` 后继 | `use-time-travel.md:104` · `main.py:1957-2008`（按 `as_node` 的 writers 产生写入并触发后继） | 新快照 `next` = `as_node` 后继（出边 + 条件边 + fan-out 按运行期路由 / 触发语义求值）；随后 `invoke(None)` 从 `next` 继续 | SAME | 照抄上游语义；freegraph 用触发 / 边模型表达 |
| P-10 | 重放入口 = `invoke(None, prior_config)` | `use-time-travel.md:18-72`（「Invoke the graph with a prior checkpoint's config」） | 同款：`invoke(None, snapshot.config)` | SAME | 照抄调用形态；`stream` 不在 v1（P-18） |
| P-11 | 重放会重新执行节点 | `use-time-travel.md:24`（「Replay re-executes nodes—it doesn't just read from cache」） | 从 `snapshot.next` 重新执行；不读缓存 | SAME | 照抄 |
| P-12 | **正常终态**重放为 no-op | `use-time-travel.md:24`（「Replaying from the final checkpoint (no next nodes) is a no-op」）· 实测：上游仍写 `source="fork"` 快照（不重跑节点） | **正常终态**（`next == ()` 且无 fanout / 静态 / pending）⇒ 不执行、**零新快照**；`static_after` 的 `next==()` 不在此列（FR-011） | **STRICTER（X-06）** | 上游**文档与实现不一致**（文档称 no-op，实测写 fork checkpoint）⇒ 属**上游自身缺陷 / 不确定**（自研区 ②）；freegraph 取文档口径 / 更确定行为 |
| P-13 | 中断在时间旅行中再次触发 | `use-time-travel.md:128-170`（「interrupts are always re-triggered」） | 重放中断点 ⇒ 节点重跑、再次暂停；`Command(resume)` 恢复最新暂停点 | SAME | 照抄；恢复定位见 P-14 |
| P-14 | 恢复路径的定位 | B10F1 **FR-010 / 裁定 9**（最新快照 + pending writes）· 上游 `invoke` 实际按 config 的 checkpoint 树继续 | `Command(resume)` 只读**最新**快照 + pending writes；忽略旧 `checkpoint_id`；原历史 pending writes 零变化 | STRICTER（X-04） | 与 B10F1 冻结口径一致；防「旧 id 误写历史」的静默污染 |
| P-15 | 重放 / 分叉的 pending writes 归属 | 上游在 `perform_superstep` 中把 `put_writes` 落到 `checkpoint_config`；时间旅行分支不写原快照 | 任何 `__resume__` / 真异常中断留痕只写**新追加**的 checkpoint；MUST NOT 写原快照 | SAME（行为不变量；**不占 X**） | 只追加是 P3 / SC-002 的硬要求；不另立偏离编号 |
| P-16 | `context` 不持久化 | 上游 `RunnableConfig.configurable` 可携带任意值 | 不持久化 / 不从历史恢复；`snapshot.config.context is None` | DIFF（X-03） | B8F3 D-1 / D-3 已冻结；本 feature 只执行 |
| P-17 | `task_id` / `values=None + END` / fresh-thread 初始化 | `main.py:2515-2526`（`task_id`）· `:1668-1730`（`None + END`）· `:1650-1666`（`saved is None` 分支） | v1 **不支持**（`task_id` 不暴露；`None` ⇒ `TypeError`；须已有基准快照） | 能力边界（不占 X） | v1 只保线性 + 每次调用一条分支（可多次分叉）（FR-019 / 裁定 9） |
| P-18 | `stream` 与时间旅行 | 上游 `stream` 不专门定义「从历史恢复」 | v1 `stream` **不是**回放入口；保持 B8F2 的「忽略 checkpointer 恢复」 | 能力边界（不占 X） | B8F2 v1 边界；FR-002 只要求 `invoke` |
| P-19 | `metadata` 的 `source` 字段 | `checkpointers.md:163,235-236`（`source` = `input` / `loop` / `update`） | freegraph `metadata` 是内部调度账本；**不承诺** `source` 字段；分叉识别靠 `parent_config` | DIFF（**继承 B14F1 / B15F1 已登记**；不新增 X） | B14F1 / B15F1 已冻结 metadata 内容为调度账本；差分排除该字段 |
| P-20 | 历史中的额外 `__start__` 快照 | 上游 `metadata["step"] == -1` 的额外快照 | freegraph **不存在**该快照 | DIFF（**继承 B14F1 已记录**；不新增 X） | B14F1 冻结口径；差分比较时排除 |
| P-21 | 配置级 checkpointer / 子图 | `main.py:1612` 的 `CONFIG_KEY_CHECKPOINTER` 与子图分支 | v1 只用编译期 saver；无子图 | 能力边界（不占 X） | C26 属 v2 |
| P-22 | 并发 / 多分支 | 上游 `bulk_update_state` 支持多 superstep / 多分支 | v1 每次调用只支持单次 `update_state`（单 superstep）与线性重放；同一 thread 可多次分叉 | 能力边界（不占 X） | FR-019 / 裁定 9 |
| P-23 | 静态断点的重放 / 恢复 | `langgraph/pregel/_algo.py:155-185`（`should_interrupt` 以 `versions_seen[INTERRUPT]` 为水位）· `_loop.py:946-951`（恢复时把水位设为当前通道版本） | freegraph `static_ack` 与水位同构：`invoke(None, static_snapshot.config)` 保留 ack 继续；从断点前重放产生新写入才再次触发；`update_state` 新分支清空 ack | SAME（水位载体差异属 B13F1 X-8） | B13F1 FR-007 已冻结「恢复必须传 static_ack」；本 feature 只接线 |

### 差分场景组 *(mandatory — 落 `tests/differential/`)*

> 上游 `langgraph 1.2.11` 已在 `.venv`，差分可运行时真跑；上游缺席 ⇒ **skip**（沿用 B5F2 / B14F1 的
> 「缺席即 skip」纪律）。差分只比较**行为面**：节点执行序列、最终状态、`next`、`values`、
> `tasks` / `interrupts` 语义、异常类型 / 消息要点、历史数量与顺序；`metadata` / `created_at` /
> `config` 载体按 B15F1 的投影排除。上游额外 `__start__` 快照在比较时排除（P-20）。

| # | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 |
|---|---|---|---|
| D-01 | 从中间 checkpoint 重放 | 两侧从同一逻辑点重新执行后续节点，最终状态一致；原快照数量 / 内容不变 | SAME |
| D-02 | 从**正常终态** checkpoint 重放 | 两侧都**不执行节点**、终态一致；freegraph **零新快照**，上游写一条 `source="fork"` 快照；**不比较快照数** | **STRICTER（X-06）** |
| D-03 | 重放中断点 | 两侧都重新触发中断；恢复后跑完；原 pending 不变（freegraph 用最新暂停点） | SAME |
| D-04 | `update_state` 覆盖型 | 新快照 `values` = 基准 + 覆盖；`parent_config` = 基准；原快照不变 | SAME |
| D-05 | `update_state` 归约型 | 归约器追加（如 messages）；与上游逐项一致 | SAME |
| D-06 | `update_state` + `as_node` | 新快照 `next` = `as_node` 后继（含条件边 / fan-out）；`invoke(None)` 从后继继续；节点序列一致 | SAME |
| D-07 | `as_node` 歧义 / 不存在 | 两侧均 `InvalidUpdateError`；消息要点一致 | SAME |
| D-08 | 未挂 saver / 缺 `thread_id` | 两侧均 `ValueError`（消息含 `No checkpointer set` / 点名 `thread_id`） | SAME（缺 `thread_id` 为 STRICTER · X-05 同源） |
| D-09 | 显式 `checkpoint_id` 不存在 | freegraph `ValueError`（点名 id）；上游行为按该版本实现（可能空 / 抛） | STRICTER（X-05） |
| D-10 | `update_state` 返回载体 | freegraph `RunConfig`（`thread_id` + 新 `checkpoint_id`）；上游 `RunnableConfig` | SAME（返回载体形态 · R-1；`config` 载体见 X-01） |
| D-11 | `context` 不持久化 | 快照 / metadata / scheduler / pending writes 中 `context` 出现次数 == 0 | DIFF（X-03） |
| D-12 | 历史枚举 / 顺序 | 原快照 + 新分支；倒序；原父链不变；上游额外 `__start__` 排除 | SAME |
| D-13 | 多次重放 | 每次追加新分支；原快照逐项不变；`parent_config` 均指向同一分叉点 | SAME（freegraph-only 部分始终运行） |
| D-14 | `SqliteSaver` ↔ `MemorySaver` | 同一重放 / 分叉序列的 8 字段 / 父链 / 历史顺序一致（`created_at` 只比格式） | SAME（freegraph 双后端对跑） |
| D-15 | 静态挂起重放 | `interrupts == ()` + 静态 `suspension_kind` / `static_ack`；直接重放，不要求动态载荷 | SAME |
| D-16 | 重放 / 分叉期间的真异常 + 中断 | 中断留痕只写新 checkpoint；原快照 pending 零变化；异常 identity 不变 | SAME（更严不变量） |
| D-17 | 静态断点的重放 / 分叉 | 从静态快照 `invoke(None, ...)` 保留 ack 继续；从断点前重放产生新写入 ⇒ 再次暂停；`update_state` 新分支清空 ack ⇒ 再次暂停；两侧的「是否暂停」判定一致 | SAME（水位载体差异属 B13F1 X-8） |

### 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 状态 | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|---|
| **X-01** | **有效** | 自研区 ④（下游兼容适配层） | P-01b / D-10：`config` 为 `RunConfig \| Mapping \| None`（上游仅 `RunnableConfig`） | B7F3 CF-05 已冻结双形态边界；本 feature 只沿用 | **B7F3**（已冻结）· 本 feature |
| **X-02** | **有效** | 破已冻结契约面（B2F1） | `CompiledGraph.update_state` 返回 `RunConfig`（B2F1 原冻结 `StateSnapshot`）· **B2F1 冻结面**（上游对照 P-01 为 SAME）· R-1 | 上游 `RunnableConfig`（`main.py:2515-2526`）+ 时间旅行继续执行的调用形态；`上游对齐审计.md` **P-12 / P3-6** 已登记该对齐项；X-02 是**对 B2F1 冻结面的回溯修订**，不是新的上游行为偏离 | **B2F1 知情** · 本 feature（**唯一一次追认** R-1） |
| **X-03** | **有效** | 破已冻结契约面（B8F3） | P-16：`context` 不持久化 / 不从历史恢复 | B8F3 D-1 / D-3 已拍板；本 feature 只执行 | **B8F3**（已冻结）· 本 feature |
| **X-04** | **有效** | 自研区 ②（更严的恢复定位 · 上游静默污染 / 不确定） | P-14：`Command(resume)` 只读最新快照，忽略旧 `checkpoint_id` | 上游按 config 的 checkpoint 树继续，可能把 pending 写回旧快照；freegraph 取更确定的「最新快照」口径，防旧 id 误写历史 / 静默回退；与 B10F1「最新快照」一致 | 本 feature · B10F1 知情 |
| **X-05** | **有效** | 更明确的失败信号 | P-03b / D-08 / D-09：缺 `thread_id` / 不存在的 `checkpoint_id` ⇒ `ValueError`（上游部分入口实测 `ValueError` / `KeyError` / 空结果） | 与 B14F1 X-03 / B15F1 X-08 同源：显式失败优于静默共享 / 回退 | 本 feature · B14F1 / B15F1 知情 |
| **X-06** | **有效** | **自研区 ②（上游自身缺陷 / 不确定）** | P-12 / D-02：**正常终态** replay **零新快照**（不写 fork checkpoint）；上游文档称 no-op，但实测写 `source="fork"` 快照（不重跑节点） | 上游**文档与实现不一致** ⇒ 属上游自身缺陷 / 不确定（自研区 ②）；freegraph 取文档口径 / 更确定行为；SC-016 锁定零新快照；差分 D-02 只比较执行 / 终态 | 本 feature · 上游自身缺陷/不确定（②） |

> **当前有效偏离 = 6 条**（X-01 / X-02 / X-03 / X-04 / X-05 / X-06）。
> **X-02 是本 feature 唯一的「破冻结面」追认项**（`update_state` 返回类别），
> 追认文字落 `harness/verification/B16F1/manual-verification.md`（R-1）。
> 另：P-17 / P-18 / P-21 / P-22 为**能力边界**；P-19 / P-20 为**继承 B14F1 / B15F1 已登记的内部结构差异**；
> **不新增 X**；不得被读成「未登记的新偏离」。**P-15 为 SAME 行为不变量，不占 X**；
> P-01 / P-03 已拆分为「返回 / 定位（SAME）」与「config / 失败（DIFF / STRICTER）」，避免三态混写。

### 破冻结面的回溯修订清单 *(必须有)*

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 / 处置 | 需发起者追认? |
|---|---|---|---|---|
| **L1 `CompiledGraph.update_state` 的返回类别 = `StateSnapshot`**（B2F1 · `protocols.py:296-298`） | `src/freegraph/contracts/protocols.py:248,296-298` · `specs/b2f1-contracts-protocols/spec.md` 的 Q8 / FR-005 ⑥ / data-model §2.5 | **拆分而不删**：保留「B2F1 历史注解 = StateSnapshot」注记；新增「自 B16F1 起返回 `RunConfig`」；**参数名 / 顺序不变**；其余五个方法不变 | 本 feature 落地时登记；追认文字落 `harness/verification/B16F1/manual-verification.md`（**R-1 · 唯一一次追认**） | **已追认**（2026-11-23 · 发起者选 **A**） |
| **L1 `CompiledGraph.update_state` 的 `config` 注解 = `RunConfig`**（B2F1 / B7F3 D-5） | `src/freegraph/contracts/protocols.py:296-298` · `specs/b7f3-invoke-full-state/spec.md` CF-05 | **拆分而不删**：保留「历史注解」注记；放宽为 `RunConfig \| Mapping[str, Any] \| None`；返回类别见上行 | 与 R-1 同批；**不额外占追认额度** | **是**（并入 R-1） |
| **`tests/runtime/test_conditional_edge_surface.py` 的 `update_state` → B16F1 未实现断言** | `tests/runtime/test_conditional_edge_surface.py:102-111` | **拆分而不删**：保留「B16F1 之前未实现」的历史注记；改为已实现的正面断言（未挂 saver ⇒ `ValueError`；有 saver ⇒ 返回 `RunConfig`） | 本 feature 交付物 | **否**（基线冻结断言拆分） |
| **`tests/facade/test_compiled_graph.py::test_each_unready_method_raises_not_implemented_naming_owner` 的 `update_state` 未实现断言** | `tests/facade/test_compiled_graph.py:76-78` | **拆分而不删**：同上 | 本 feature 交付物 | **否** |
| **`tests/facade/test_facade.py::test_compile_returns_a_product_but_capability_methods_are_not_implemented` 的 `update_state` 未实现断言** | `tests/facade/test_facade.py:234-236` | **拆分而不删**：同上 | 本 feature 交付物 | **否** |
| **B14F1 裁定 6 / B15F1 裁定 4 / 5 的 `put` 父链 = 最新快照** | `specs/b14f1-checkpointer-memory-saver/spec.md` 裁定 6 · `specs/b15f1-sqlite-saver-state-history/spec.md` 裁定 4 / 5 · `src/freegraph/persistence/memory.py:230-260`（parent `:252-256`） / `sqlite.py:373-420`（parent `:401`） | **拆分而不删**：保留「无显式 id ⇒ 父链 = 最新」；新增「显式 `configurable["checkpoint_id"]` ⇒ 父链 = 该 id」；既有调用零变化 | 本 feature 交付物（R-2 · 扩展不改既有行为） | **否**（向后兼容扩展） |
| **B10F1 恢复路径对 `checkpoint_id` 的定位**（当前实现 `get_tuple(config)` 会取指定 id） | `src/freegraph/runtime/superstep.py:2657`（`_resume_graph` 的 `get_tuple`） | **拆分而不删**：保留「历史 `checkpoint_id` 可被传入」的注记；新增「恢复定位 = 该 thread 最新快照；旧 id 忽略」；`__resume__` 只写最新快照 | 本 feature 交付物（R-3 · 防历史污染） | **否**（与 B10F1 FR-010 的「最新快照」口径对齐） |
| **`harness/demo/README.md` 的「`update_state(...)` 的签名 = B16F1 未说签名」待锁定条目** | `harness/demo/README.md:118` | **移除该行**；在「已锁定」处补一行指向本 spec 裁定 1 | 本 feature 交付物 | **否** |

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：系统 MUST 在 `CompiledGraph` 上实现 `update_state(config, values, as_node=None) -> RunConfig`；
  参数 / 返回类别逐字按裁定 1；`values` MUST 是 `Mapping`；MUST NOT 暴露 `task_id`、
  MUST NOT 接受 `values=None`。
- **FR-002**：`update_state` / 重放 MUST 接受 `config: RunConfig | Mapping[str, Any] | None`；
  `configurable["thread_id"]` 优先；缺失 / 空串 ⇒ `ValueError`（点名 `thread_id`）；
  裸 `str` / 数字 ⇒ `TypeError`；MUST NOT 在门面层把映射翻译成 `RunConfig`。
- **FR-003**：`update_state` 与**携带显式 `checkpoint_id` 的重放入口** MUST 要求
  `compile(checkpointer=...)` 注入真实 saver；`None` / `True` / `False` ⇒ `ValueError`
  （消息含 `No checkpointer set`）；`checkpoint_ns` 非空 ⇒ `ValueError`（v1 无子图）。
  无显式 `checkpoint_id` 的普通 `invoke` / 续跑 MUST 保持 B15F1 / B7F3 行为不变
  （FR-020 / SC-017）。
- **FR-004**：`update_state` MUST 以「显式 `configurable["checkpoint_id"]`」或「该 thread 最新快照」
  为基准；显式 id 不存在 / thread 不存在 / 无基准快照 ⇒ **`ValueError`**；
  MUST NOT 静默新建 thread 或回退到全新会话。
- **FR-005**：`update_state` MUST 通过**同一 `put` 渠道**追加新快照：id = 该 thread 的
  `MAX(checkpoint_id) + 1`（`f"{n:032d}"`）；`parent_config` = **基准快照的 config**；
  MUST NOT 覆盖 / 重排 / 删除原快照；MUST NOT 另造 id 空间。
- **FR-006**：`update_state` 的 `values` MUST 走**与普通节点 / 输入写入相同的通道合并语义（C6）**：
  覆盖型 ⇒ 覆盖；归约型 ⇒ 按归约器追加 / 归约；未知 key ⇒ `InvalidUpdateError`；
  合并 MUST 在副本上完成，存储零变化（原子性）；MUST NOT 另写第二套合并规则。
- **FR-007**：`update_state` 的 `as_node` MUST 按裁定 4 处理：显式 ⇒ 必须是已存在节点
  （否则 `InvalidUpdateError`）；省略且单节点 ⇒ 该节点；省略且多节点 ⇒ 从基准快照
  `versions_seen` 推断最后更新者（歧义 ⇒ `InvalidUpdateError`，消息含
  `Ambiguous update, specify as_node`；MUST NOT 回退 `node_versions` / 入口节点）；新快照 `next` =
  `as_node` 的后继节点集合（出边 + 条件边 + fan-out（`Send`）按运行期同款路由 / 触发语义在
  更新后状态上求值）；无后继 ⇒ `next == ()`。
- **FR-008**：`update_state` 的新快照 MUST 具备完整 8 字段：`values` = C6 合并后的稀疏状态；
  `next` = FR-007 的后继集合；`config` = `thread_id` + 新 `checkpoint_id`（`context is None`）；
  `metadata` = 与运行期同款的内部调度账本；`created_at` = UTC ISO-8601；
  `parent_config` = 基准快照 config；`tasks == ()`；`interrupts == ()`；
  `suspension_kind == None` 且 `static_ack == None`（静态标记清空 · 见裁定 4）；
  pending writes MUST NOT 从基准快照复制。
- **FR-009**：系统 MUST 支持**从任意历史 checkpoint 重放**，入口 = `invoke(None, snapshot.config)`；
  必须从指定快照恢复 `values` / 调度账本 / `next`，并从 `snapshot.next` **重新执行**；
  MUST NOT 读缓存、MUST NOT 伪造历史。
- **FR-010**：重放时若 `configurable["checkpoint_id"]` 为非空但该快照不存在 ⇒ **`ValueError`**
  （点名 `checkpoint_id`）；MUST NOT 回退到最新快照或全新会话。
- **FR-011**：历史静态快照（`interrupts == ()` + 静态 `suspension_kind` / `static_ack`）
  MUST 可直接作为重放起点；`invoke(None, static_snapshot.config)` MUST **保留 `static_ack`**
  （上游 `versions_seen[INTERRUPT]` 水位口径）⇒ 越过已确认的静态断点继续；从断点**之前**
  重放且产生新写入时，静态断点 MUST **再次触发**；MUST NOT 要求动态中断载荷；
  MUST NOT 假设「`next` 非空 ⇒ 必有中断」。⚠️ `update_state` 新分支仍按 FR-008 清空 ack。
- **FR-012**：`update_state` / 重放 MUST NOT 读取 / 保存 / 还原 / 透出 `RunConfig.context`；
  `snapshot.config.context` MUST 为 `None`；`metadata` / `scheduler` / pending writes
  MUST NOT 出现 `context`；MUST NOT 回退到 `configurable` 承载 `context`；
  MUST NOT 重新引入节点别名。
- **FR-013**：`Command(resume=...)` 的恢复路径 MUST **只读该 thread 的最新快照 + pending writes**，
  忽略 `configurable["checkpoint_id"]`；MUST NOT 把 `__resume__` 写到历史快照上；
  时间旅行重放 / 分叉后恢复的是**新追加的暂停点**；「恢复」与「时间旅行」MUST 并存但独立，
  MUST NOT 共用「改写历史」语义。若最新快照原本挂起而用户从更早历史点分叉，旧 pending
  仍保留在旧快照；要恢复它 MUST 先重放旧快照重新触发中断，MUST NOT 自动复制旧中断载荷。
- **FR-014**：重放 / 分叉 MUST **只追加**：原快照的 8 字段与 pending writes 逐项不变；
  `get_state_history` 继续按 `checkpoint_id` 倒序可枚举；MUST NOT 提供分支树 / 按分支枚举 API
  （v1 用 `parent_config` 读取分支）。
- **FR-015**：重放**正常终态**快照（入口 = `invoke(None, snapshot.config)`；`next == ()` 且无 fanout / 无静态挂起 / 无 pending 中断）MUST 为 no-op：不执行节点、不产生新快照。**`static_after` 的 `next==()` 不是正常终态**：按 FR-011 继续并写完成快照（B13F1 F-10）。`invoke(state_dict, historical.config)` 属 B7F3 续跑、不是重放，按 FR-026 写 anchor。
- **FR-016**：本 feature MUST NOT 实现 `delete_for_runs` / `copy_thread`；
  两者继续抛 `NotImplementedError`（与 B14F1 / B15F1 / 上游 base 一致）；
  MUST NOT 回改 `MemorySaver` / `SqliteSaver` 的既有删除 / 复制行为。
- **FR-017**：系统 MUST 为 `put` 增加「显式父链」的最小扩展：当
  `configurable["checkpoint_id"]` 为非空 `str` 时，新快照 `parent_config` = 该 id；
  缺失 / 空串时保持 B14F1 的「最新快照」语义；运行期常规写盘 MUST 携带**当前** checkpoint id
  作 parent（父链逐条接续，可观察行为不变）；`MemorySaver` 与 `SqliteSaver` MUST 一致；
  既有调用方（不传**显式历史 id**）行为零变化。
- **FR-018**：L1 `CompiledGraph.update_state` 的 `config` 注解 MUST 放宽为
  `RunConfig | Mapping[str, Any] | None`，返回类别 MUST 改为 `RunConfig`；
  MUST 走「登记 + 回溯修订 + 发起者追认」；其余 L1 符号面 / 字段面 / 异常类型 MUST NOT 改动。
- **FR-019**：本 feature MUST NOT 实现：`task_id`、`values=None + as_node=END`、fresh-thread
  `update_state` 初始化、并行 / 多分支树、async、`Store`、Postgres、前端 UI、
  trace 存储 / 查询、`stream` 回放。
- **FR-020**：本 feature MUST NOT 改变普通运行的图执行语义：未携带 `checkpoint_id` 的
  `invoke` / `stream`（节点序列、最终状态、错误信号、快照数）MUST 与 B15F1 一致；
  `stream(checkpoints)` 的既有语义不变。
- **FR-021**：依赖 / 环境门禁：MUST NOT import `langchain` / `langchain-core` / `langgraph*` /
  `langsmith`；MUST NOT 读环境变量；MUST NOT 有任何出站；
  `src/freegraph/persistence/**` MUST 只依赖 **L1 + 标准库**（ARCH-1）；
  新增第三方依赖数 MUST == 0。
- **FR-022**：`harness/demo/README.md` MUST 移除「`update_state(...)` 的签名」待锁定条目，
  并补记本 spec 裁定 1 的锁定结论；MUST NOT 修改 `harness/demo/target.py`。
- **FR-023**：系统 MUST 在 `tests/differential/` 落本 spec 的 D-01…D-17；
  上游 `langgraph` 缺席 ⇒ skip（不是 fail）；每条上游断言 MUST 带版本 + `路径:行号`。
- **FR-024**：`harness/verification/B16F1/manual-verification.md` MUST 存在，含
  「环境 / 步骤 / 实际输出 / 结论 / 遗留问题」五段；实际输出 MUST 含**非空**的
  「重放 → 状态一致」「分叉 → 原历史不变」「归约 / 覆盖合并」实测；
  含本 feature **唯一一次追认文字**（R-1：`update_state` 返回类别 + `config` 注解放宽）；
  **质量门禁 5 合规**：MUST 跑 **fake 轮 + 真实模型轮**两轮；真实模型轮使用
  `harness/demo/target.py` 或等价固定脚本，记录模型端点、调用次数与零出站归因；
  B25F1 只做跨 feature 复验，**不是**本 feature 的替代。
- **FR-025**：失败信号 MUST 按裁定 8：全部复用既有 `ValueError` / `TypeError` /
  `InvalidUpdateError`；MUST NOT 新增 L1 异常类型；消息 MUST 点名出错对象。
- **FR-026**：非 no-op 重放 / 历史续跑 MUST 先通过同一 `put` 渠道追加一条 **branch anchor**
  （8 字段、`parent_config` = 基准、静态标记 / scheduler 同基准、`interrupts == ()` /
  `tasks == ()`、pending 不复制、id = `MAX+1`）；**正常终态 no-op MUST NOT 写 anchor**；
  由 `update_state` 产生的分支快照**兼任**本分支 anchor ⇒ 从该分支快照
  `invoke(None, fork_config)` MUST NOT 再写 anchor；分支快照初始 pending 为空，
  可承载本分支首轮 pending 留痕，但 MUST NOT 回写原历史快照；
  `invoke(state_dict, historical.config)` 属 B7F3 续跑、不是重放，但同受 anchor 保护；
  anchor 的字段 / 触发 / 父链 / 计数口径按裁定 10 与 SC-008 / SC-016。

### Key Entities

- **`CompiledGraph.update_state`**：L3 的对外状态更新面；锁定签名见裁定 1；返回新分支的 `RunConfig`。
- **`update_state` 产生的新快照**：8 字段 `StateSnapshot`；`parent_config` = 基准快照；
  `next` = `as_node` 后继；`interrupts == ()`；`tasks == ()`；**兼任本分支 anchor**。
- **重放（time-travel replay）**：`invoke(None, snapshot.config)`；从历史快照继续执行；
  只追加新快照；不读缓存。
- **branch anchor**：非 no-op replay / 历史续跑的首条分支快照；`parent_config` = 基准、
  pending 不复制（裁定 10 / FR-026）；`update_state` 的分支快照**兼任** anchor。
- **分叉（fork）**：`update_state` + `invoke(None, fork_config)`；新分支；原历史完整；
  分支快照即 anchor，后续 `invoke` 不再追加 anchor。
- **`StateSnapshot.parent_config`**：分支结构的唯一载体；首条分支快照指向分叉点。
- **`Command(resume=...)`**：中断恢复；只读最新快照 + pending writes；与时间旅行并存但独立。
- **`RunConfig`**：双形态 `config` 载体（B7F3 CF-05）；`context` 不持久化。

### 需求 ↔ 成功标准追溯表

| FR | 判定它的 SC | 判据 | 承接 |
|---|---|---|---|
| FR-001 | SC-006 | 签名 / 返回载体 | A3 |
| FR-002 | SC-006 / SC-015 | 双形态 config / 失败 | A3 |
| FR-003 | SC-004 / SC-015 / SC-017 | saver / thread / ns；普通 `invoke` 行为不变 | A3 |
| FR-004 | SC-004 / SC-015 | 基准定位 / 起点不存在 | A1 / A3 |
| FR-005 | SC-002 / SC-007 | 只追加 / 父链 / id | A2 |
| FR-006 | SC-003 | C6 合并 | A3 |
| FR-007 | SC-009 | as_node / 后继 | A3 |
| FR-008 | SC-007 / SC-010 | 8 字段 / context | A2 |
| FR-009 | SC-001 / SC-016 | 重放入口 / no-op | A1 |
| FR-010 | SC-004 | 起点不存在 | A1 |
| FR-011 | SC-011 | 静态快照 | A1 / A2 |
| FR-012 | SC-010 | context | — |
| FR-013 | SC-011 | 恢复组合 / 历史保护 | A1 / A2 |
| FR-014 | SC-002 / SC-008 / SC-014 | 历史完整 / 倒序 | A2 |
| FR-015 | SC-016 | 正常终态 no-op | A1 |
| FR-016 | SC-017 | 删除 / 复制边界 | — |
| FR-017 | SC-007 | put 父链扩展 | A2 |
| FR-018 | SC-006 / SC-012 | L1 改动 / 追认 | — |
| FR-019 | SC-017 | 能力边界 | — |
| FR-020 | SC-017 | 普通运行不变 | — |
| FR-021 | SC-005 | 零依赖 / env / 出站 | — |
| FR-022 | SC-018 | README 锁定 | — |
| FR-023 | SC-012 | 差分场景 | — |
| FR-024 | SC-013 | 人工验证记录 | — |
| FR-025 | SC-015 | 失败信号 | A3 |
| FR-026 | SC-008 / SC-014 / SC-016 | branch anchor / 计数 / 历史保护 | A1 / A2 |

> **双向覆盖核对**：FR-001…FR-026 全部在表；SC-001…SC-018 全部已定义；
> 验收判据 A1–A3 均至少挂一条**测试任务**（SC-001 / SC-002 / SC-003）。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：对线性图 `a → b → c` 的**每个**历史 checkpoint（`next` 非空者），
  从该快照 `invoke(None, snapshot.config)` 都能到达一致终态（通过率 == 100%）；
  执行的节点集合 == 该点之后的节点（节点序列差异 == 0）。
- **SC-002**：重放 / 分叉后，原 N 条快照的 8 字段与 pending writes 逐项相等
  （差异 == 0）；原 `checkpoint_id` 集合不变；原父链不被重排（差异 == 0）。
- **SC-003**：`update_state` 的写入按 C6 合并：归约型通道 `new == old ⊕ value`（差异 == 0）；
  覆盖型通道 `new == value`（差异 == 0）；未知 key ⇒ `InvalidUpdateError`（比率 == 100%）。
- **SC-004**：起点不存在 / thread 不存在 ⇒ `ValueError`（可由异常类型判定）的比率 == 100%；
  消息点名 `thread_id` / `checkpoint_id` 的比率 == 100%；存储零变化（残留 == 0）；
  **MUST NOT** 静默回退到最新 / 全新会话（次数 == 0）。
- **SC-005**：运行时依赖闭包仍为空集（`dependencies == []`）；新增第三方包数 == 0；
  环境变量读取点 == 0；出站调用点 == 0；`src/freegraph/persistence/**` 无 L2–L5 import
  （ARCH-1 判绿）。
- **SC-006**：`CompiledGraph.update_state` 的签名 / 返回类别与裁定 1 逐字一致；
  未挂 saver ⇒ `ValueError`（含 `No checkpointer set`）；L1 新增异常类型数 == 0；
  除 `update_state` 之外的五方法 / 字段面 / 门面符号面零改动。
- **SC-007**：分叉新快照的 `parent_config` == 基准快照 config（差异 == 0）；
  新 id > 原 thread 最大 id（严格递增）；后续本分支快照逐条链在新快照之后；
  原父链不变；`MemorySaver` 与 `SqliteSaver` 逐项一致。
- **SC-008**：`get_state_history` 在重放 / 分叉后仍可枚举全部快照；
  长度 == 原数量 + 本次新增快照数（从**既有历史快照**起的非 no-op replay =
  **anchor + 执行快照**；`update_state` 分叉 = **分支快照（兼任 anchor）+ 执行快照**，
  **不另写 anchor**；正常终态 replay = **0**，按裁定 10 / SC-016 计数）；
  `checkpoint_id` 严格递减（逆序对 == 0）；`get_state({id})` 对任一原 id 仍可逐字段取回。
- **SC-009**：`as_node` 显式 / 单节点兜底 / 省略推断 / 歧义 / 不存在五种情形的行为与裁定 4 一致；
  新快照 `next` == `as_node` 后继（差异 == 0）；跨 node 条件边按运行期路由求值
  （与普通运行同款）；歧义 / 不存在 ⇒ `InvalidUpdateError`（比率 == 100%）。
- **SC-010**：`context` 在新快照 / metadata / scheduler / pending writes 中出现次数 == 0；
  `snapshot.config.context is None` 的比率 == 100%；从历史恢复 `context` 的次数 == 0。
- **SC-011**：动态中断重放 ⇒ 重新触发中断，追加新暂停快照；`Command(resume)` 恢复**最新**暂停点
  并跑完；原快照 pending writes 变化 == 0；静态历史快照直接重放成功率 == 100%，
  「缺动态载荷」异常次数 == 0；静态快照 `invoke(None, ...)` **保留 ack 继续**的比率 == 100%；
  从断点前重放产生新写入 ⇒ 再次暂停的比率 == 100%；`update_state` 新分支清空 ack 的比率 == 100%。
- **SC-012**：差分场景 D-01…D-17 全部落 `tests/differential/`；上游在场时通过率 == 100%；
  缺席 ⇒ skip（不是 fail）；每条上游断言带版本 + `路径:行号`（缺失数 == 0）。
- **SC-013**：`harness/verification/B16F1/manual-verification.md` 存在；五段齐全；
  含**非空**的重放 / 分叉 / 合并实测输出；含 **fake 轮 + 真实模型轮**两轮证据
  （真实模型轮含模型端点、调用次数、零出站归因）；含本 feature **唯一一次追认文字**
  （R-1）（文档守卫断言）。
- **SC-014**：重放 / 分叉期间产生的 pending writes（`__resume__` / 真异常中断留痕）
  落在原快照上的次数 == 0；只落在新追加 checkpoint 的比率 == 100%；
  原快照 pending writes 逐项不变。
- **SC-015**：`update_state` / **显式 `checkpoint_id` 重放**的失败信号与裁定 8 逐条一致：
  未挂 saver / 缺 `thread_id` / 坏 id / 坏 ns ⇒ `ValueError`；非 Mapping ⇒ `TypeError`；
  未知 key / 坏 `as_node` ⇒ `InvalidUpdateError`；消息点名率 == 100%；
  存储零变化（残留 == 0）。
- **SC-016**：**正常终态**快照（`next == ()` 且无 fanout / 无静态 / 无 pending）重放执行节点数 == 0、新快照数 == 0（no-op）；
  上游写 fork checkpoint 但不重跑节点，本条为 **STRICTER（X-06）**；`static_after` 的 `next==()` 不适用本条（按 FR-011 继续并写完成快照）。
- **SC-017**：未携带 `checkpoint_id` 的普通 `invoke` / `stream` 的节点序列、最终状态、
  快照数与 B15F1 行为逐项一致（差异 == 0）；`stream(checkpoints)` 事件语义不变；
  v1 能力边界（`task_id` / `None + END` / fresh-thread / async / 分支树）实现数 == 0。
- **SC-018**：`harness/demo/README.md` 不再含「`update_state(...)` 的签名」未锁定条目
  （命中数 == 0）；新增锁定说明指向本 spec；`harness/demo/target.py` 修改数 == 0。

### 验收判据（立项书 §5.2 B16F1 小目标 · 逐条可判定）

> 小目标原文：**可从历史 checkpoint 重放**

| # | 判据 | 判定方式 | 本 spec 的承载 |
|---|---|---|---|
| **A1** | 可从历史 checkpoint 重放 | 历史点重放用例（多个历史点各一例） | **SC-001 / SC-011 / SC-016** · FR-009 / FR-010 / FR-011 / FR-015 |
| **A2** | 分叉不污染原历史 | 重放后历史快照数量与内容不变 | **SC-002 / SC-008 / SC-014** · FR-005 / FR-014 / FR-017 |
| **A3** | `update_state` 合并语义正确 | 归约器 / 覆盖两例 | **SC-003 / SC-009 / SC-015** · FR-001 / FR-006 / FR-007 |

---

## Assumptions

- **上游取证环境**：本机 `.venv` 已安装 `langgraph 1.2.11`；`update_state` /
  `bulk_update_state` / `MemorySaver.put` 的锚点于 2026-11-23 核对；
  文档镜像 `use-time-travel.md` / `checkpointers.md` 已在本仓库。
- **semantics 的权威**：`update_state` 的行为以 `langgraph 1.2.11` + `use-time-travel.md`
  为唯一权威；freegraph 只在**已冻结的载体 / id / 父链**上保留自有口径（C19 / B14F1 / B15F1）。
- **spec 目录命名**：speckit 通用规则为 `NNN-<short-name>`；本仓库既有 feature 全部采用
  `<b<N>f<M>-<slug>`（宪法 v1.4.2 的目录约定）⇒ 本 feature 用
  `specs/b16f1-update-state-time-travel`（**已偏离通用规则 · 已登记**）。
- **分支**：本仓库无 `.specify/extensions.yml` ⇒ 无 `before_specify` 钩子 ⇒ 不创建分支，
  在 `main` 上开发。
- **Python 基线**：3.11+；实现只用标准库（`copy` / `datetime` / `collections.abc` /
  `typing` 等）；零第三方运行时依赖。
- **规模参考**：原始估算 1,040 行（实现 480 / 测试 560）· 3 人日；因父链扩展、
  `as_node` 后继求值、历史保护不变量与差分，实际规模可能上调 ⇒ 在 plan / tasks 中如实登记，
  **MUST NOT** 通过削减判据来压行数。
- **存储后端**：`MemorySaver` 与 `SqliteSaver` 都 MUST 满足本 spec 的时间旅行语义；
  `SqliteSaver` 的纯数据 / JSON 约束（B15F1 X-05）继续适用。
- **`metadata` 口径**：freegraph `metadata` 是内部调度账本（`next` / `interrupts` / `tasks` /
  `suspension_kind` / `static_ack` / `scheduler`），不承诺上游的 `source` 字段；
  分叉识别用 `parent_config`。
- **`context`**：B8F3 已接线；本 feature 明确**不**持久化、**不**从历史恢复。
- **无 async**：freegraph v1 无 async；`update_state` 只同步。
- **无前端 UI**：本 feature 只交付能力层（`get_state_history` + `invoke(None, config)` +
  `update_state`）；UI 归 B26 / v2。
- **UI 预留**：`get_state_history` 的 `StateSnapshot.config` + `update_state` 返回的 `RunConfig`
  已足以让 B26 调用；MUST NOT 为 UI 新增私有接口。
- **差分测试**：上游 `langgraph` 只在测试侧使用；生产依赖声明 MUST 保持 `dependencies = []`。
- **人工验证**：记录 MUST 由执行者如实转录，禁止代签；Windows / 多解释器证据引用 CI。
- **质量门禁 5 合规**：B16F1 MUST 跑 **fake 轮 + 真实模型轮**；真实模型轮使用
  `harness/demo/target.py` 或等价固定脚本；B25F1 只做跨 feature 复验（**不替代**）。
- **API 兼容矩阵**：`CompiledGraph.update_state` / 时间旅行相关行由 **B24F1** 纳入；
  本 feature 只提供行为与证据。

---

## 依据

- 立项书 §4.2（S7 差分表 · time-travel 一行）、§5.2（B16F1 行）、§5.3（C19 / C16 / C17）、
  §5.6（三件套）、§5.8.1（可视化 12 项之「状态 · 回放与分叉」）、§5.8.2（第 5 项）、
  §6.3（关键路径）、§9.1（门禁）。
- 官方文档镜像：`harness/docs/oss/python/langgraph/use-time-travel.md`
  （`Replay` `:24-72` · `Fork` `:78-123` · `Interrupts` `:128-170`）·
  `harness/docs/oss/python/langgraph/checkpointers.md`（`source` `:163,235-236` ·
  reducer `:255`）。
- 源码参照（**langgraph 1.2.11**）：
  `langgraph/pregel/main.py:1590-2054`（`bulk_update_state`）·
  `:2515-2526`（`update_state`）· `:1650-1666`（基准 / `checkpoint_config`）·
  `:1875-1937`（`as_node` 推断 / 校验）· `:1950-2008`（writers / `apply_writes`）·
  `:1617`（`No checkpointer set`）·
  `langgraph/checkpoint/memory/__init__.py:430-473`（`put` · parent `:459`）·
  `langgraph/types.py:631`（`StateUpdate`）·
  `langgraph/pregel/main.py:1392`（`get_state`）· `:1480`（`get_state_history`）·
  `:3783`（`invoke`）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C19 / C16 / C17）；
  `harness/proposals/上游对齐审计.md` P-12 / P3-6（`update_state` 返回 `RunnableConfig`）；
  B10F1 `specs/b10f1-interrupt-resume/spec.md`（FR-010 / FR-018 / 裁定 9 / D-7）；
  B13F1 D-6；B8F3 D-1 / D-3；B14F1 裁定 6 / D-03 / D-08；B15F1 裁定 4 / 5 / 9 / D-01 / D-02 / D-03；
  B7F3 CF-05。
- 层与门禁：`specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`（L4 = `persistence`）·
  `harness/prompts/guide.md` §2.3 / §3.5（L4 只依赖 L1）。
- 宪法 `.specify/memory/constitution.md`：原则 IV（trace / state / interrupt / time-travel
  四类能力 MUST 有最小可用实现）· 原则 XI（上游优先）· 原则 XII（最优设计优先）。

---

## 下游承接（本 feature → 下游 · 只接线 · 逐条最小改动）

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 |
|---|---|---|---|---|
| **D-01** | **B24F1** | **M4** | API 兼容矩阵 MUST 增加 `CompiledGraph.update_state` 行（返回 `RunConfig` · `as_node` · 无 `task_id`）与「时间旅行重放 / 分叉」行（`invoke(None, snapshot.config)` + `update_state` + `Command(resume)`）；`manual-verification.md` MUST 纳入发布前人工验收。 | FR-001 / FR-009 / FR-013 / FR-018 / FR-024 |
| **D-02** | **B25F1** | **M4** | 双跑验收脚本 MUST 覆盖：历史点重放、`update_state` 覆盖 / 归约、分叉后原历史不变、中断组合；**并对 B16F1 的真实模型轮做跨 feature 复验（不是替代）**；MUST NOT 修改 `harness/demo/target.py`。 | FR-009 / FR-024 · SC-001 / SC-002 / SC-003 / SC-013 |
| **D-03** | **B26F1（v2 · UI）** | **v2** | 前端时间旅行 UI MUST 只消费既有能力面：`get_state_history` → 选择 `snapshot.config` → `invoke(None, config)` 重放；`update_state` → `invoke(None, fork_config)` 分叉；MUST NOT 要求新增私有接口或直接读写 saver。 | FR-009 / FR-019 · 裁定 1 / 5 |
| **D-04** | **Postgres 后端（v2）** | **v2** | 同一 `Checkpointer` 协议与父链扩展（显式 `checkpoint_id` ⇒ parent）MUST 在 Postgres 后端复用；时间旅行语义零变化；MUST NOT 另造 id 空间。 | FR-005 / FR-017 · 裁定 3 |
| **D-05** | **B20F1 / B20F2** | **M3** | checkpoint 与 trace 是两套存储：时间旅行 / `update_state` MUST NOT 写 trace 存储；重放产生的 trace 由既有 tracer 记录，与 checkpoint 历史互不影响。 | FR-019 · 裁定 9 |

---

## 下游承接状态（上游 → 本 feature 的核对）

| 来源 | 编号 | 状态 |
|---|---|---|
| **B10F1** | D-7 · FR-010 / FR-018 / 裁定 9 | ✅ **已接线**（FR-013 · 裁定 6） |
| **B13F1** | D-6 | ✅ **已接线**（FR-011 · 裁定 5 / 6） |
| **B8F3** | D-1 / D-3 | ✅ **已接线**（FR-012 · 裁定 7） |
| **B14F1** | D-03 / D-08 | ✅ **已接线**（FR-004 / FR-005 / FR-016 / FR-017 · 裁定 2 / 3） |
| **B15F1** | D-01 / D-02 / D-03 | ✅ **已接线**（FR-005 / FR-008 / FR-009 / FR-011 / FR-014 · 裁定 3 / 5 / 6） |
| **B7F3** | D-5 · CF-05 | ✅ **已接线**（FR-002 / FR-018 · 裁定 1 · 破冻结面回溯修订清单 R-1） |
