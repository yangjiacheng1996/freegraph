# Research · B16F1 · `update_state` + 时间旅行回放

> **输入**：`spec.md`（**唯一权威** · 11 条 Clarifications 定案 + 10 条形态锁定裁定 +
> FR-001…FR-026 + SC-001…SC-018 + P-01…P-23（含 P-01b / P-03b 拆分，共 25 行）+ D-01…D-17 + X-01…X-06）·
> 宪法 **v1.16.1** · 上游 `langgraph` **1.2.11**（`.venv` 已装）·
> 官方镜像 `harness/docs/oss/python/langgraph/use-time-travel.md` /
> `checkpointers.md`。
>
> **判定纪律**（宪法原则 XI）：每条决策先问「上游怎么说」⇒ 上游有答案 ⇒ **照抄**；
> 只在**必须自研区**自研并**如实登记**。freegraph 只保留已冻结的载体 / id / 父链口径
> （C19 / B14F1 / B15F1）与红线（零第三方、`context` 不持久化、无 async）。
>
> **形态纪律**（原则 XII）：复用 `StateSnapshot` / `RunConfig` / `CheckpointTuple` /
> 调度账本；不另造第二套快照 / id / 合并路径。

---

## §1 现状盘点（动手前的事实基线）

| # | 事实 | 取证 | 影响 |
|---|---|---|---|
| **F-01** | L1 `CompiledGraph.update_state` 当前签名 `(config: RunConfig, values: StateDict, as_node=None) -> StateSnapshot` | `src/freegraph/contracts/protocols.py:296-298` | 本 feature 改为双形态 `config` + 返回 `RunConfig`（R-1） |
| **F-02** | L3 `CompiledGraph.update_state` 当前抛 `NotImplementedError("update_state 由 B16F1 交付")` | `src/freegraph/_stategraph.py:975-977` | 替换为真实实现 |
| **F-03** | L2 图级入口 `run_graph` 已有 `_first_graph` / `_resume_graph` 两条路径 | `src/freegraph/runtime/superstep.py:2451-2761` | 重放 / 分叉接线落在这两条路径 + 新 `_time_travel` |
| **F-04** | `_first_graph` 用 `checkpointer.get_tuple(run_config)`；显式 id 不存在时 `history is None` 会**按全新会话**跑 | `superstep.py:2563-2585` | 必须新增「显式 id 不存在 ⇒ `ValueError`」（FR-010） |
| **F-05** | `_resume_graph` 用 `get_tuple(run_config)`，会取 config 指定的旧 id | `superstep.py:2657` | 改为只读最新快照 + pending writes（R-3 / X-04） |
| **F-06** | `_run_graph_loop` 跟踪 `current_checkpoint_id`，但 `put_step` / `_write_suspend` / `_clear_static_suspension` 仍把原始 `run_config` 传给 `put` | `superstep.py:2122-2330` · `:2376-2448` | 父链推进需要统一传 `config_for_checkpoint(run_config, current_id)` |
| **F-07** | L4 `MemorySaver.put` / `SqliteSaver.put` 的 parent 固定为「最新」 | `persistence/memory.py:230-260` · `sqlite.py:373-420` | 增加「显式 id ⇒ 该 id」的向后兼容扩展（R-2） |
| **F-08** | L2 有 `_restore_scheduler` / `_restore_channels` / `_run_channels` / `_evaluate_source_routes` / `_commit_outcome` / `_merge_writes` / `_clear_step_end` / `_determine_triggers` | `superstep.py:796-1400` · `:1956-2075` | `update_state` 复用正常执行路径，不写第二套 |
| **F-09** | `SchedulerState` 含 `versions_seen` / `channel_versions` / `node_versions` / `dynamic_edges` / `fanout`；`to_checkpoint` / `from_checkpoint` 严格互逆 | `superstep.py:270-382` | `as_node` 推断 / 后继 / fan-out 全部基于既有账本 |
| **F-10** | B15F1 的 `_state_read.assemble_snapshot` 从 `snapshot.next` + `.scheduler["fanout"]` + pending `__interrupt__` 重建 tasks / interrupts | `runtime/_state_read.py:140-243` | 新分支快照无需另写读取路径 |
| **F-11** | `Command(resume)` 的 `__resume__` pending writes 写在 `snapshot_config`（当前实现可能是旧 id） | `superstep.py:2722-2740` | 最新定位后只写最新，原历史 pending 零变化 |
| **F-12** | 静态挂起用 `suspension_kind` / `static_ack`；恢复时 `static_ack` 必须传给 `static_allowed` | `runtime/_static.py:1-124` · B13F1 FR-007 | replay 保留 ack；`update_state` 清空 ack |
| **F-13** | `StreamCheckpointWriter` 跟踪 `current_checkpoint_id`，但 `put_step` 仍用原始 `_run_config` | `runtime/_stream_checkpoint.py:40-110` | `put` 扩展后必须改为「当前 id 作 parent」 |
| **F-14** | L2 `runtime/` 是层注册表的 **L2 目录条目**；同条目内部 import 不产生层边 | `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md:98` | 新 `runtime/_time_travel.py` 无需改注册表 |
| **F-15** | 门面 `freegraph.graph` 不转出 L4；`CompiledGraph` 方法是能力面 | `src/freegraph/graph.py` · G18 | 不新增模块级导出 |
| **F-16** | 基线 **2266 passed / 10 skipped**（2026-11-23 实跑） | `.venv/bin/python -m pytest -q --tb=no` | 实施后必须回到全绿（除 skip） |
| **F-17** | 上游 final replay **会**写 `source="fork"` 快照（不重跑节点） | 实测：线性图 history `4 → 5`，新增 `((), 'fork', 3)` | 与 spec SC-016「正常终态零新快照」不一致 ⇒ **X-06**（spec 已订正；自研区 ②：上游文档/实现不一致） |
| **F-18** | 上游 `should_interrupt` 以 `versions_seen["__interrupt__"]` 为水位；恢复时把水位设为当前通道版本 | `langgraph/pregel/_algo.py:155-185` · `_loop.py:946-951` | freegraph `static_ack` 同构；静态 replay 保留 ack |

---

## §2 设计决策（D-01…D-15）

### D-01 · `update_state` 的落点与分层

- **Decision**：L3 `CompiledGraph.update_state` 只做「门面编排 + 调用 L2」，真正的
  基准定位 / `as_node` 推断 / C6 合并 / 后继 / `put` 在**新增 L2 私有**
  `src/freegraph/runtime/_time_travel.py`。
- **Rationale**：① L4 不能应用归约器 / 调度账本；② L3 → L2 是合法方向（ARCH-1）；
  ③ `runtime/` 是 L2 目录条目，同条目内部 import 不产生层边（F-14）；
  ④ L3 门面不翻译 config（B7F3 CF-05）。
- **Alternatives considered**：
  - 放在 L4 saver：无法应用 C6 / 调度 / 路由；排除。
  - 放在 L3 `_stategraph.py` 全实现：门面膨胀、难复用 L2 私有助手；排除。
  - 新增 L3 独立模块：`_stategraph.py` 已 L3，新增同层模块会引入 L3 同层横向依赖；
    排除。

### D-02 · 合并 / 后继复用正常执行路径

- **Decision**：`update_state` 的 `values` 构造为
  `writes = {key: (value,)}` + `_TaskOutcome`；走：
  1. `_restore_scheduler` / `_restore_channels`（从基准快照）；
  2. 清空 `state.fanout`（基准的 pending fan-out 不属于新分支）；
  3. `_evaluate_source_routes(as_node, writes, channels, route_config)`；
  4. `_commit_outcome(..., task_id=0, target=as_node, outcome=_TaskOutcome(writes=...),
     extra_gotos=..., extra_fanout=...)`（`TaskId` 是 int；本分支只有一个产生者）；
  5. `_merge_writes(spec, state, [(as_node, as_node, writes)])`；
  6. `_clear_step_end`；7. `_determine_triggers` 得 `next`；8. `put`。
- **Rationale**：C6（归约 / 覆盖）与 C8（fresh 条件边）只有一条路径；`as_node`
  后继与普通节点执行同款；fan-out 复用 `make_fanout` / `.scheduler["fanout"]`；
  不执行 `as_node` 节点函数（上游 update_state 也只跑 writers）。
- **Alternatives considered**：
  - 直接 `Channel.update` 后手写 `next`：绕过 C8 / 条件边 / fan-out；排除。
  - 执行 `as_node` 节点函数：会重复副作用（LLM / 工具）；排除。
  - 复制上游 `apply_writes`：引入第二套合并路径；排除。

### D-03 · `as_node` 推断

- **Decision**：镜像上游 `main.py:1875-1935`：
  - 显式 `as_node` ⇒ 必须 `str` 且在 `spec.nodes`；否则 `InvalidUpdateError`；
  - 省略且图恰 **1 个节点** ⇒ 使用该节点（上游 `main.py:1904-1908` 同款兜底）；
  - 省略且多节点 ⇒ 从基准快照的 `versions_seen` 取「最后更新者」：
    对每个 `n ∈ spec.nodes` 收集 `(v, n)`（`v` 为其 seen 值）；若唯一最大 ⇒ 该节点；
    若最大并列 ⇒ `InvalidUpdateError("Ambiguous update, specify as_node")`；
    若 `versions_seen` 无节点记录 ⇒ 同款歧义错误；
  - **MUST NOT** 回退 `node_versions` / 入口节点；推断结果必须仍在 `spec.nodes`。
- **Rationale**：上游同款（单节点兜底 + `versions_seen`，无 `node_versions` 回退）；
  显式失败优于静默选错分支。
- **Alternatives considered**：
  - 回退 `node_versions`：上游无此口径，会形成未登记偏离；排除。
  - 默认入口节点：上游只在恰一个节点 / `input_channels` 时兜底；freegraph v1 无
    `input_channels` ⇒ 该兜底列能力边界（spec 裁定 9）；多节点且无历史 ⇒ 显式失败。
  - 默认最后一个执行节点（不检测并列）：可能静默选错；排除。

### D-04 · `as_node` 后继 / 条件边 / fan-out

- **Decision**：`next = _determine_triggers(spec, state)`（标准触发目标，节点名序）；
  条件边 / `Command.goto` 目标经 `_evaluate_source_routes` 写入
  `state.dynamic_edges[as_node]`；`Send` fan-out 写入 `state.fanout[as_node]`；
  新快照 `metadata["next"] = tuple(next)`，`metadata["scheduler"] = state.to_checkpoint()`
  （含 `fanout`）；`tasks=()` / `interrupts=()`。
- **Rationale**：B15F1 的读取层从 `next` + `.scheduler["fanout"]` 重建 next-tasks；
  上游 `update_state` 跑 as_node writers 后由 `apply_writes` 触发后继；fan-out 只在
  账本里，不塞进 `next`。
- **Alternatives considered**：
  - 把 fan-out 目标塞进 `next`：B15F1 的 next-tasks 会把它们当标准任务；排除。
  - 保留基准的 pending fan-out：会复用旧任务；排除（新分支从 as_node 后继重新开始）。

### D-05 · 父链与 `put` 扩展

- **Decision**：
  - L4 `MemorySaver.put` / `SqliteSaver.put`：`configurable["checkpoint_id"]` 非空 ⇒
    parent = 该 id（必须已存在，否则 `ValueError`）；缺失 / 空串 ⇒ parent = 最新；
  - L2 `_run_graph_loop` / `_stream_checkpoint`：每次写盘用
    `config_for_checkpoint(run_config, current_id)` 作 `put` 的 config；写完推进
    `current_id`；
  - `update_state` 用 `config_for_checkpoint(cfg, base_id)` 作 `put` 的 config；
  - 新 id 仍由 saver 生成 `MAX+1`。
- **Rationale**：上游 `put` 的 parent = `config["configurable"].get("checkpoint_id")`
  （`memory/__init__.py:459`）；分支内逐条接续；既有「无 id ⇒ 最新」调用零变化。
- **Alternatives considered**：
  - 另立 `put_branch` 方法：违反「同一 `put` 渠道追加」（D-01）且新增公开面；排除。
  - 在 L3 门面层改 `RunConfig`：违反 CF-05「不翻译」；排除。
  - 不改 L4、只在 `update_state` 后手工修父链：破坏存储一致性；排除。

### D-06 · 重放起点校验

- **Decision**：`_first_graph` 若 `checkpoint_id_of(run_config)` 非空：
  - `get_tuple(run_config)` 为 `None` ⇒ **`ValueError`**（消息点名 `checkpoint_id`）；
  - **MUST NOT** 回退到最新 / 全新会话（无论 `input` 是 `None` 还是 dict）；
  - 未挂 saver / `True` / `False` 的 `No checkpointer set` **仅**在该显式 id 分支生效；
    无显式 id 的普通 `invoke` / 续跑保持 B15F1 / B7F3 行为（FR-020 / SC-017）。
- **Rationale**：FR-010 / SC-004；显式失败优于静默污染；不误伤普通运行。
- **Alternatives considered**：
  - 回退最新：用户以为从历史点重放，实际跑最新；排除。
  - 回退 fresh：会写新会话；排除。

### D-07 · 非 no-op replay 的 branch anchor

> **规范来源**：spec **裁定 10 / FR-026**（本决策是其实现面展开）。

- **Decision**：显式历史 id + **有工作**（`next` 非空 / fanout 非空 / 静态挂起 /
  pending 动态中断 / 非空 input dict）⇒ 在 `_first_graph` 先写一条 branch anchor：
  - `parent_config` = 基准快照 config；
  - `values` = 基准 `values`；
  - `metadata.next` = 基准 `next`；`suspension_kind` / `static_ack` = 基准值；
    `scheduler` = 基准 scheduler；`interrupts=()` / `tasks=()`；
  - 后续执行使用 `current_checkpoint_id` = anchor id；**恢复状态仍从基准 history 读取**
    （pending 动态中断 / 静态 ack 来自基准）。
  - **正常终态 no-op**（`next==()` 且无 fanout / 静态 / pending；`input` 为 None / 空 dict）⇒ **不写 anchor**。
  - **已是分支 anchor**：显式 id 指向 `update_state` 产出的分支快照（`fork_config`）⇒
    该分支快照兼任 anchor，**不再写**额外 anchor；`current_checkpoint_id` = 分支快照 id。
- **Rationale**：上游 `_loop.py:952-965` 在 time-travel 首轮写 `source="fork"` 快照；
  保证首轮中断 / 真异常 / `__resume__` 不会写到原快照（SC-014）；
  同时给分支一个明确父链起点。`update_state` 的分支快照已承担该起点职责。
- **Alternatives considered**：
  - 不写 anchor，靠「错误时懒创建」：复杂且易漏；排除。
  - 所有 replay 都写 anchor（含正常终态）：违反 SC-016；排除。
  - 把 anchor 写进 pending writes 而非快照：读取层不可见；排除。

### D-08 · `Command(resume)` 最新定位

- **Decision**：`_resume_graph` 的 `get_tuple` 使用「仅 `thread_id`」的配置
  （忽略 `configurable["checkpoint_id"]`）；`snapshot_config` = 最新快照 config；
  `__resume__` 写最新；`_run_graph_loop` 的 `current_id` = 最新 id。
- **Rationale**：B10F1 FR-010 / 裁定 9「恢复读最新快照」；防旧 id 误写历史；
  与上游 `invoke(Command(resume), fork_config)` 形态兼容（旧 id 不误导定位）。
- **Alternatives considered**：
  - 按 config 的 checkpoint_id 恢复：会写旧快照 pending，污染历史；排除。
  - 按「config id 的祖先最新」：复杂且无上游依据；排除。

### D-09 · 静态 ack 的保留 / 清空

- **Decision**：
  - 静态快照 `invoke(None, static_snapshot.config)`：**保留 `static_ack`**，
    `static_allowed` 判定「自上次静态挂起以来无新写入」⇒ 越过已确认断点继续；
  - 从断点**之前**重放：基准无 ack（或 ack 旧）⇒ 重放节点产生新写入 ⇒
    `static_allowed` 为真 ⇒ 断点**再次触发**；
  - `update_state` 新分支：`suspension_kind=None` / `static_ack=None`；后继若命中
    `interrupt_before` / `interrupt_after` ⇒ 正常再次暂停。
- **Rationale**：B13F1 FR-007「恢复必须传 static_ack，否则首轮立即重挂」；
  上游 `versions_seen[INTERRUPT]` 水位同构；分叉是新执行起点，旧 ack 不应泄漏。
- **Alternatives considered**：
  - replay 也清空 ack：静态快照 replay 立即重挂，违背 B13F1 FR-007；排除。
  - update_state 保留 ack：可能绕过审批点；排除。

### D-10 · `context`

- **Decision**：`update_state` / replay 不读取、不保存、不还原、不透出
  `RunConfig.context`；新快照 `config.context is None`；`metadata` / `scheduler` /
  pending writes 不出现 `context`；不把 `context` 塞进 `configurable`。
- **Rationale**：B8F3 D-1 / D-3；spec X-03。
- **Alternatives considered**：持久化 context / 从历史恢复：破 B8F3；排除。

### D-11 · 失败信号

- **Decision**：全部复用既有 `ValueError` / `TypeError` / `InvalidUpdateError` /
  `FreegraphError`；消息点名 `thread_id` / `checkpoint_id` / 节点 / key；不新增 L1 异常。
- **Rationale**：spec 裁定 8；L1 冻结面；B12F1 「更严失败信号」口径。
- **Alternatives considered**：新增 `TimeTravelError`：破 L1 异常面；排除。

### D-12 · L1 协议改动

- **Decision**：只改 `CompiledGraph.update_state`：
  `config: RunConfig | Mapping[str, Any] | None`；返回 `RunConfig`；
  `values: StateDict`；`as_node: str | None = None`。
- **Rationale**：上游 `RunnableConfig`（`main.py:2515-2526`）；
  `use-time-travel.md:78-96` 的 `fork_config` 用法；R-1 已获发起者追认。
- **Alternatives considered**：
  - 保留 `StateSnapshot` 返回：与上游 / 文档形态不一致；排除（R-1 已批准）。
  - 增加 `task_id`：v1 不做并行任务；能力边界；排除。

### D-13 · stream 写盘父链

- **Decision**：`StreamCheckpointWriter` 的 `put_initial` / `put_step` / `_write_suspend`
  一律用「当前 checkpoint id 作 parent」的 config；`prepare` 的 `get_tuple` 使用
  **仅 thread_id** 的配置（忽略用户 config 的 `checkpoint_id`），保持 B8F2「stream 不恢复历史」。
- **Rationale**：`put` 扩展后，原始 `_run_config` 若带旧 id 会让每次写盘都 parent 旧 id；
  必须推进；stream v1 不恢复历史（B8F2 FR-028 / B15F1 裁定 10）。
- **Alternatives considered**：
  - 让 stream 也读历史：破 B8F2；排除。
  - 不改 stream：父链错乱；排除。

### D-14 · 测试 / 差分

- **Decision**：
  - 单元 / facade / runtime / persistence / contracts / differential 全覆盖；
  - D-02 只比较「不执行节点 / 终态一致」，**不比较快照数**（X-06 · 正常终态）；
  - 上游缺席 ⇒ skip；
  - 三处冻结断言「拆分而不删」；
  - `test_protocols.py` 增加 `update_state` 返回 `RunConfig` 断言。
- **Rationale**：A1–A3 判据级覆盖；宪法原则 VI；上游 final replay 写 fork checkpoint
  的事实差异（F-17）。
- **Alternatives considered**：
  - 把 D-02 写成「快照数一致」：会与上游实测冲突；排除。
  - 只写 facade 测试：覆盖不到 scheduler / 父链 / 静态 / resume；排除。

### D-15 · 文档 / 人工验收

- **Decision**：更新 `README.md` 的 `CompiledGraph` 行；移除 `harness/demo/README.md`
  的 `update_state` 待锁定行并补锁定说明；新增
  `harness/verification/B16F1/manual-verification.md`（五段式 + fake + 真实模型两轮 +
  R-1 追认文字）；下游提示词接线（R-14）。
- **Rationale**：FR-022 / FR-024；门禁 5；spec 下游承接 D-01…D-05。
- **Alternatives considered**：
  - 不跑真实模型：门禁 5 不合规；排除。
  - 修改 `target.py`：宪法原则 III 禁止；排除。

---

## §3 上游取证（关键锚点）

### 3.1 `update_state` / `bulk_update_state`

- `langgraph/pregel/main.py:2515-2526`：
  `update_state(config, values, as_node=None, task_id=None) -> RunnableConfig`
  → `bulk_update_state(config, [[StateUpdate(values, as_node, task_id)]])`。
- `main.py:1590-2054`：`bulk_update_state` 的 `perform_superstep`：
  - `saved = checkpointer.get_tuple(config)`；
  - `checkpoint_config` 由 `saved.config` 派生；
  - `values` 走 `as_node` 的 `flat_writers`（含 reducers）；
  - `checkpointer.put(checkpoint_config, ...)` ⇒ parent = `configurable["checkpoint_id"]`；
  - 未挂 checkpointer ⇒ `ValueError("No checkpointer set")`（`:1617`）。
- `main.py:1875-1935`：`as_node` 推断（`versions_seen` 最后更新者；歧义 ⇒
  `InvalidUpdateError("Ambiguous update, specify as_node")`）。
- `main.py:1957-2008`：`as_node` writers + `apply_writes` + 触发后继。

### 3.2 父链

- `langgraph/checkpoint/memory/__init__.py:430-473`：
  `put` 的 parent = `config["configurable"].get("checkpoint_id")`（`:459`）。
- freegraph 现状：`MemorySaver.put` / `SqliteSaver.put` 固定 parent = 最新
  ⇒ 需要 R-2 扩展。

### 3.3 时间旅行文档

- `harness/docs/oss/python/langgraph/use-time-travel.md`
  - `:18-72` Replay：`invoke(None, prior_config)`；重新执行节点；**正常终态** no-op（**不重跑节点**）；
  - `:78-123` Fork：`update_state` → `invoke(None, fork_config)`；原历史完整；
  - `:104` values 走指定节点 writers（含 reducers）；execution resumes from that node's successors；
  - `:128-170` interrupts 在 time travel 中再次触发。
- `checkpointers.md:163,235-236`：`metadata.source` = `input` / `loop` / `update`；
  freegraph metadata 是内部账本，不承诺 source（P-19）。
- `checkpointers.md:255`：update 与 node update 同款，reducers 累加。

### 3.4 静态断点 / 恢复

- `langgraph/pregel/_algo.py:155-185`：`should_interrupt` 以
  `checkpoint["versions_seen"].get(INTERRUPT, {})` 为水位。
- `_loop.py:946-951`：`is_resuming` 时把 `versions_seen[INTERRUPT]` 设为当前通道版本
  ⇒ 无新写入时不再暂停。
- `_loop.py:952-965`：time-travel (`is_time_traveling`) 且 source 不是 update/fork ⇒
  清旧 INTERRUPT pending writes + `_put_checkpoint({"source": "fork"})`。
- 实测（F-17）：final replay 也会写 `source="fork"` 快照（但**不重跑节点**）。

### 3.5 上游实测

```text
线性图 a → b：
history before 4 [((), 'loop', 2), (('b',), 'loop', 1), (('a',), 'loop', 0),
                  (('__start__',), 'input', -1)]
invoke(None, final.config)  # 不重跑节点
history after  5 [((), 'fork', 3), ((), 'loop', 2), ...]
```

⇒ 与 spec SC-016「**正常终态** replay 零新快照」不一致；实现按 spec（STRICTER · X-06 · 自研区 ②：上游文档/实现不一致），
差分 D-02 只比执行 / 终态（X-06）。

---

## §4 未决点 / parity 事实订正

| # | 点 | 状态 | 处置 |
|---|---|---|---|
| **U-01** | 上游 final replay 写 fork checkpoint | **已取证**（F-17） | 实现按 SC-016 零新快照；D-02 比执行；spec 已把 P-12 / D-02 改 STRICTER + 新增 X-06（自研区 ②） |
| **U-02** | 上游 `metadata.source` | 已知差异（P-19） | freegraph metadata 内部账本；不承诺 source；差分排除 |
| **U-03** | 上游 fresh-thread `update_state` | 能力边界 | v1 不支持；显式失败；文档 / 差分排除 |
| **U-04** | 上游 `task_id` / `values=None + END` | 能力边界 | v1 不暴露 / `TypeError`；文档 / 差分排除 |
| **U-05** | 上游 `stream` 回放 | 能力边界（B8F2 冻结） | v1 只 `invoke`；文档 / 差分排除 |
| **U-06** | 上游恢复按 config 的 checkpoint 树 | freegraph STRICTER（X-04） | 只读最新；D-03/D-17 差分只比最终状态 / pending 保护 |

> **结论**：除 U-01 的 parity 标注订正外，spec 的用户决策点已全部收敛；
> 无 NEEDS CLARIFICATION。X-06 只改**标注 / 判据不放松**（自研区 ②），不影响实现。

---

## §5 风险与验证

| # | 风险 | 缓解 |
|---|---|---|
| **RK-1** | 父链推进漏改某个 `put` 调用点 | 统一 `config_for_checkpoint`；双后端父链 + 历史完整性测试 |
| **RK-2** | `as_node` 后继 / fan-out 与运行期不一致 | 复用 `_evaluate_source_routes` / `_commit_outcome` / `_determine_triggers`；D-06 |
| **RK-3** | replay / update_state 写原快照 pending | anchor + resume 最新定位；SC-014 专项 |
| **RK-4** | 静态 ack 混用 | replay 保留 / update_state 清空；D-17 |
| **RK-5** | L4 `put` 扩展破既有行为 | 显式 id 才生效；全量 2266+ 基线回归 |
| **RK-6** | final replay 差分与上游快照数不同 | D-02 只比执行；X-06 已落 spec |
| **RK-7** | G25 判新 L2 模块未登记 | 放 `runtime/` 目录条目；不 import L4；设计后复核 |
| **RK-8** | 行数超预算 | tasks 如实登记；不削 FR / SC |

---

## §6 结论

- 设计上**复用**既有 L2 调度 / 合并 / 路由 / 读取路径，**不另造**第二套快照、id、合并或
  读取逻辑。
- 唯一 L1 改动（`update_state` 返回类别 + config 注解）已按 R-1 追认；唯一 L4 改动
  （`put` 显式父链）向后兼容；L2 新文件同层内部 import 不产生层边。
- 时间旅行 / 分叉 / 中断 / 静态四条路径的边界已分别落在
  `time-travel-contract.md` / `update-state-contract.md` / `put-parent-contract.md` /
  `upstream-parity.md`。
- **唯一事实订正**：**X-06**（上游 final replay 的 fork checkpoint vs spec SC-016 正常终态零新快照；自研区 ②）；**已落 spec**。
