# B7F1 · Phase 0 研究记录（上游实测取证 + 决策登记）

**核实环境**：上游 `langgraph==1.2.11` · CPython **3.11.16**（临时 venv · **不进仓库依赖**）
—— 核实于 **2026-11-10**。
⚠️ **换上游版本后 MUST 重新核实全部行号**（宪法原则 VIII）。
⚠️ **取证环境隔离**：临时 venv 建在 `/tmp/opencode/lgvenv` ⇒ **仓库的 `pyproject.toml`
与 `Requires-Dist` 零改动** ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿（沿用 B5F2 的同款口径）。

> **本文件是「证据」载体，不是「判据」载体** —— 判据的唯一权威是
> [contracts/superstep-contract.md](./contracts/superstep-contract.md)；
> 本文件与 [contracts/upstream-parity.md](./contracts/upstream-parity.md) **MUST NOT** 被测试解析
> （测试**直接断言行为** ⇒ 避免「判据与实现同源 ⇒ 自证」的循环论证）。

---

## §1 上游实测取证（D-01…D-12）

### 核实方法（一次性采集）

```bash
# 临时 venv（仓库外）
python3 -m venv /tmp/opencode/lgvenv
/tmp/opencode/lgvenv/bin/pip install "langgraph==1.2.11"

# 关键函数的定义位置
grep -n "^def \|^async def \|^class " /tmp/opencode/lgvenv/lib/python3.11/site-packages/langgraph/pregel/_algo.py
# 触发判定 / 写入合并 / 步末清空 / versions_seen
sed -n '232,347p' .../langgraph/pregel/_algo.py     # apply_writes
sed -n '1260,1278p' .../langgraph/pregel/_algo.py    # _triggers
sed -n '392,516p' .../langgraph/pregel/_algo.py     # prepare_next_tasks
sed -n '1356,1392p' .../langgraph/pregel/_algo.py   # prepare_input（PULL 入参）
sed -n '599,700p'   .../langgraph/pregel/_loop.py    # tick（super-step 循环）
```

---

### D-01 · 触发判定 = 「**有值** ∧ **版本比较**」；无已消费记录时只看「**有值**」

**上游**：`langgraph/pregel/_algo.py:1260-1278`（`_triggers`）

```python
def _triggers(
    channels: Mapping[str, BaseChannel],
    versions: ChannelVersions,
    seen: ChannelVersions | None,
    null_version: V,
    proc: PregelNode,
) -> bool:
    if seen is None:
        for chan in proc.triggers:
            if channels[chan].is_available():
                return True
    else:
        for chan in proc.triggers:
            if channels[chan].is_available() and versions.get(  # type: ignore[operator]
                chan, null_version
            ) > seen.get(chan, null_version):
                return True
    return False
```

**结论**：上游的触发判定 = `is_available() ∧ (version > seen)`；**当该节点没有已消费记录时**
（`seen is None`）**只看 `is_available()`** —— 即「**有值即触发**」。
⇒ **本 feature 的裁定 21（「有值」即算已写过一次 ⇒ 记版本 1）是上游的逐字同构实现** ✔
⚠️ **2026-11-11 分析轮订正**（裁定 28 · **发起者批准**）：freegraph **实现** `is_available()` 这一合取项
（`has_value(s)`），且其层级为**逐触发源**（**不是**逐节点 AND）⇒ 与上游 `_triggers` **逐字同构**
（parity **P-02** 由「机制差异」改为「**逐字同构**」）。「清空**不是**写入 ⇒ 版本不推进」是 freegraph
让 `has_value` 变假（路由型通道步末被清空）的**实现手段**，**不**是替代该合取项。

**落点**：FR-002 · 裁定 21 · parity P-01 / P-03。

---

### D-02 · 「已消费版本」按**节点名**分组，在**写入合并阶段**更新

**上游**：`langgraph/pregel/_algo.py:264-271`（`apply_writes` 内）

```python
    # update seen versions
    for task in tasks:
        checkpoint["versions_seen"].setdefault(task.name, {}).update(
            {
                chan: checkpoint["channel_versions"][chan]
                for chan in task.triggers
                if chan in checkpoint["channel_versions"]
            }
        )
```

**结论**：上游的 `versions_seen` 结构 = **`节点名 → {通道 key → 版本}`** —— 与本 spec 的
**Key Entities「已消费版本（`versions_seen`）」逐字同构** ✔（裁定 4 / FR-004）。
⚠️ **时点差异**：上游在 **apply（合并）阶段**更新；freegraph 在 **plan（任务准备）阶段**消费
（⇒ 计划阶段就「消费掉」版本）。**差异的可观察后果**：上游若某轮**失败**（`apply_writes` 未被调用）
⇒ `versions_seen` **未更新** ⇒ 同一节点**下一轮仍会被触发**；freegraph 的 plan 阶段消费**已经发生**
⇒ 下一轮**不会**再触发。
⇒ 本 feature 的选择理由（**2026-11-11 分析轮订正**）：**FR-032（原子性）只约束「通道的正式值」**
（FR-032 的原文：「本轮产生的全部待写入 MUST 不被合并 ⇒ 通道的正式值 MUST 保持本轮开始前的样子」），
**并不约束** `versions_seen` ⇒ 原句「若已消费版本不回滚 ⇒ 状态与调度记录会不一致 ⇒ 所以不回滚」
是**非推论**，已删除。真正的取舍是：① 选 **apply（合并）阶段**消费 ⇒ 该阶段可能因出错**根本不到达**
⇒ 已准备的任务的版本**永久未消费** ⇒ 下一轮会**重复触发**同一节点 ⇒ 与 **FR-004**「同一版本 MUST NOT
重复触发同一节点」**直接冲突**；② 选 **plan（任务准备）阶段**消费 + 出错**回滚**已消费版本 ⇒ 需要在
调度状态上实现**事务性回滚**，而异常已向上传播、**运行终止** ⇒ 调度记录**无人在意** ⇒ 复杂度显著
上升而**收益为零**。⇒ **决策**：`versions_seen` 的消费点选在 **plan 阶段**，且**出错时已消费版本不**回滚**
（见 data-model §4.2 的**原子性边界**）⇒ 落成 **DR-1**（已知边界 · 登记不改判据）。
⚠️ **2026-11-10 分析轮订正**：本段原文写「**且在出错时随本轮一并作废**」⇒ 与
data-model §4.2（**不**回滚）· plan 的 Complexity Tracking（**不**回滚）· 本表 **DR-1**
（**不**回滚）**三处相反** ⇒ **以「不回滚」为准**（异常已向上传播 ⇒ 运行终止 ⇒ 调度记录
无人在意）⇒ 措辞已订正，**判据不变**。
**落点**：FR-004 · 裁定 16 · parity P-04 · DR-1。

---

### D-03 · 通道版本是**全局单调计数器**，所有通道共享

**上游**：`langgraph/pregel/_algo.py:273-284` + `:322-331`

```python
    # Find the highest version of all channels
    if get_next_version is None:
        next_version = None
    else:
        next_version = get_next_version(
            (max(checkpoint["channel_versions"].values())
             if checkpoint["channel_versions"] else None), None)
    ...
    for chan, vals in pending_writes_by_channel.items():
        if chan in channels:
            if channels[chan].update(vals) and next_version is not None:
                checkpoint["channel_versions"][chan] = next_version
```

**结论**：上游的「版本」= 一个**全局单调计数器** `next_version`（所有通道共享同一计数器），
**每写成功一次**（`update()` 返回真）就把它记到该通道上。
⇒ 本 feature 的**每通道独立版本**是**机制差异**（比较**只在同一通道内**进行 ⇒ 可观察等价）✔
⇒ 但**版本推进的时机**与上游**逐字一致**：`update()` 返回**真**才推进（FR-002）✔
**落点**：FR-002 · parity P-02。

---

### D-04 · 上游的**同轮执行顺序**是「**按节点名排序**」，不是声明顺序

**上游**：`langgraph/pregel/_algo.py:476-484`（`prepare_next_tasks` 内）

```python
    if updated_channels and trigger_to_nodes:
        triggered_nodes: set[str] = set()
        for channel in updated_channels:
            if node_ids := trigger_to_nodes.get(channel):
                triggered_nodes.update(node_ids)
        # Sort the nodes to ensure deterministic order
        candidate_nodes: Iterable[str] = sorted(triggered_nodes)
```

**结论**：上游为**确定性**（注释逐字「Sort the nodes to ensure deterministic order」），
但排序键是**节点名**；`apply_writes` 再按**任务路径**排一次（`_algo.py:258-259`
`tasks = sorted(tasks, key=lambda t: task_path_str(t.path[:3]))`，PULL 任务的路径是 `(PULL, 名字)`）
⇒ **上游的合并顺序 = 按节点名字典序**。
⚠️ **本 feature 的裁定 9 = 声明顺序**（发起者于 2026-11-10 澄清轮**主动选定**）⇒
**与上游存在可观察差异**：当两个节点在同轮写**同一个归约通道**、且归约器**不满足交换律**
（如 `operator.sub`）时，两侧的**合并顺序不同 ⇒ 结果不同**。
⇒ **登记为可观察差异**（parity **P-05**）⇒ **不改判据**（发起者已拍板）⇒ 落 **DR-2**（未来对齐点）。
**落点**：FR-013 · 裁定 9 · SC-013 · parity P-05 · DR-2。

---

### D-05 · 步末清空：**只清「本步未更新」的通道** ⇒ **本步写过的路由通道本轮不清**

**上游**：`langgraph/pregel/_algo.py:333-341`（`apply_writes` 内）

```python
    # Channels that weren't updated in this step are notified of a new step
    if bump_step:
        for chan in channels:
            if channels[chan].is_available() and chan not in updated_channels:
                if channels[chan].update(EMPTY_SEQ) and next_version is not None:
                    checkpoint["channel_versions"][chan] = next_version
                    if channels[chan].is_available():
                        updated_channels.add(chan)
```

配合 `channels/last_value.py:56-58` / `channels/binop.py:123-125`（两者对 `update([])` **no-op**）
与 `channels/ephemeral_value.py:56-61`（`update([])` ⇒ 清为 `MISSING`）。

**结论**：上游的有效规则 = 「步末对**本步未更新**的通道调 `update(EMPTY_SEQ)`」
⇒ 覆盖型 / 归约型 **no-op**（**值保留**）· 路由型 ⇒ **清空**
⇒ **本步被写入过的路由型通道，其值存活到下一轮**。
⚠️ **本 feature 的原 FR-014（步末对**全部**路由型通道调 `clear()`）与之不符** ⇒
**已回写 spec**：FR-014 收紧为「**只清『本轮未被写入的』路由型通道**」· SC-012 同步 ·
裁定 10 由 B **收紧为 C**（**只更正事实，未改任何判据**）。
**理由**：B8F1 的条件边路由要在**下一轮**读到「本节点本次写入」⇒ 路由通道的值**必须**存活到下一轮。
**落点**：FR-014 · SC-012 · 裁定 10 · 承接 H-2 · parity P-06 · spec 更正 **C-1**。

---

### D-06 · 未知通道的写入：上游 **warning + 静默忽略**；freegraph **显式失败**

**上游**：`langgraph/pregel/_algo.py:310-314`

```python
            else:
                logger.warning(
                    f"Task {task.name} with path {task.path} wrote to unknown channel {chan}, ignoring it."
                )
```

**结论**：上游**静默丢弃**未知 key（只 `logger.warning`）⇒ **与 C6「未知 key 报错」分叉**。
⇒ freegraph 抛 `InvalidUpdateError`（**L1 契约层已冻结**）是**与 C6 一致**、**与上游分叉**的选择
⇒ 沿用 **B5F2 的既有登记**（research **DR-2** · `specs/b5f2-sparse-state-read/contracts/`）。
**落点**：FR-007 · 裁定 7 · parity P-07。

---

### D-07 · 写入合并走**批量** `update(values)`；**未知 key 不进待写入**

**上游**：`langgraph/pregel/_algo.py:298-320`

```python
    # Group writes by channel
    pending_writes_by_channel: dict[str, list[Any]] = defaultdict(list)
    for task in tasks:
        for chan, val in task.writes:
            if chan in (NO_WRITES, PUSH, RESUME, INTERRUPT, RETURN, ERROR, ERROR_SOURCE_NODE):
                pass
            elif chan in channels:
                pending_writes_by_channel[chan].append(val)
            else:
                logger.warning(...)
    # Apply writes to channels
    updated_channels: set[str] = set()
    for chan, vals in pending_writes_by_channel.items():
        if chan in channels:
            if channels[chan].update(vals) and next_version is not None:
                ...
```

**结论**：上游**先按通道分组**、再**一次** `update(vals)` ⇒ **批量归约** ✔
⇒ **本 feature 的裁定 5（批量路径）与上游逐字同构** ✔
⚠️ 上游的 `NO_WRITES` / `PUSH` / `RESUME` / `INTERRUPT` / `RETURN` / `ERROR` 是**控制流保留通道名**
⇒ 属 **B9F1 / B10F1 / B12F1** 的落点 ⇒ 本 feature **零实现**（登记 parity P-08）。

**落点**：FR-005 · 裁定 5 · parity P-08。

---

### D-08 · 节点入参 = **该节点订阅的通道 ∩ 当前有值的通道**

**上游**：`langgraph/pregel/_algo.py:1356-1370`（`prepare_input`）

```python
    if isinstance(proc.channels, list):
        val: dict[str, Any] = {}
        for chan in proc.channels:
            if chan in channels:
                if channels[chan].is_available():
                    val[chan] = channels[chan].get()
            else:
                val[chan] = managed[chan].get(scratchpad)
```

**结论**：上游的节点入参 = **`proc.channels`（该节点的输入 schema）里 `is_available()` 的那些** ——
**既不是整张状态表，也不含无值通道** ⇒ 与 **C4** 逐字同构 ✔
⇒ **本 feature 的裁定 2 / FR-008 是上游的逐字同构实现** ✔
⇒ 且「**订阅**」在 freegraph 里**同时**是触发源与入参来源（裁定 2 的 ⚠️ 段）⇒ 与上游
（`proc.triggers` 与 `proc.channels` 同源）一致 ✔

**落点**：FR-008 · 裁定 2 · SC-009 · parity P-09。

---

### D-09 · 静态边编译成 **Branch** ⇒ 目标节点在**下一 tick** 执行

**上游**：`langgraph/graph/state.py:928`（`add_edge`）· `:1399`（`compiled.attach_branch(start, name, branch)`）
· `langgraph/pregel/_algo.py:800+`（`prepare_push_task_functional`）

**结论**：`add_edge(a, b)` 在编译期被挂成 `a` 的 **Branch** ⇒ `a` 执行完后产生一个 **PUSH 任务** ⇒
`b` 在**下一 tick**（= 下一 super-step）执行 ⇒
⇒ 本 feature 的「**边触发源**（源节点的执行版本）+1 ⇒ 目标节点下一轮被触发」**语义等价** ✔
（**机制差异**：上游用 Branch/PUSH 任务，freegraph 用版本号比较）。
**落点**：FR-003 · 裁定 3 · parity P-10。

---

### D-10 · 收敛判定：**空任务集 ⇒ 立即终止**

**上游**：`langgraph/pregel/_loop.py:657-660`（`tick`）

```python
        # if no more tasks, we're done
        if not self.tasks:
            self.status = "done"
            return False
```

**结论**：上游的终止判定**逐字**就是「本轮任务集为空 ⇒ done」✔ ⇒ **FR-010 与上游逐字同构** ✔
**落点**：FR-010 · SC-006 · parity P-11。

---

### D-11 · `recursion_limit` 缺省 = **25**

**上游**：`langchain_core/runnables/config.py:171`（`DEFAULT_RECURSION_LIMIT = 25`）·
`:268`（`recursion_limit=DEFAULT_RECURSION_LIMIT`）·
`langgraph/pregel/_loop.py:1701`（`self.stop = self.step + self.config["recursion_limit"] + 1`）

**结论**：上游缺省 **25** ✔ ⇒ **本 feature 的裁定 24（缺省 25）与上游逐字一致** ✔
⚠️ 上游的 `recursion_limit` 是**对外载体**（`RunnableConfig`）⇒ **freegraph 的载体归 B13F1**
（本 feature 只提供内核侧上限 + `GraphRecursionError`，FR-011）。

**落点**：FR-011 · 裁定 24 · SC-006 · parity P-12。

---

### D-12 · 上游另有两个**通道钩子**（`consume` / `finish`）与「最后一轮 `finish()`」

**上游**：`langgraph/channels/base.py:101`（`consume()` · 默认 no-op）· `:112`（`finish()` · 默认 no-op）
· `langgraph/channels/last_value.py:130-136`（`LastValue.consume()` · 仅当 `finished` 才清值）
· `:138-145`（`LastValue.finish()` · 置 `finished=True`）
· `langgraph/pregel/_algo.py:343-346`（最后一轮对**所有**通道调 `finish()`）

**结论**：上游把「**读过的通道消费掉**」与「**运行结束**」表达为**两个独立钩子**；
**B5F1 冻结的 `Channel` 抽象只有四个操作**（`update` / `get` / `is_available` / `clear`）
⇒ **MUST NOT** 给通道加钩子（冻结面）⇒
⇒ freegraph 的等价落点 = **步末对「本轮未被写入的路由型通道」调 `clear()`**（D-05）
⇒ 「运行结束时的 `finish()`」**本 feature 不实现**（语义属 **B7F3 / checkpoint**）⇒ 登记 parity **P-13**。

**落点**：FR-014 · FR-028 · parity P-13 · Out of Scope。

---

## §2 遗留登记（DR-1…DR-3 · **只登记 · 不改判据**）

| # | 遗留 | 性质 | 触发重新评估的条件 | 归属 |
|---|---|---|---|---|
| **DR-1** | `versions_seen` 的**消费时点**与上游不同（plan vs apply）；且**出错时**已消费版本**不回滚** | **机制差异**（可观察边界） | 若将来出现「失败后重试同一调度状态」的用法 ⇒ 需补回滚 | 本 feature（数据模型 §4 已写明**原子性边界**） |
| **DR-2** | 同轮执行顺序 = **声明顺序**（上游 = 节点名字典序）⇒ 非交换归约器的**合并顺序**两侧不同 | **可观察差异**（发起者已拍板） | 若与非交换归约器相关的用例出现 ⇒ 复核 | 本 feature（parity **P-05**）· 发起者裁定 9 |
| **DR-3** | 「最后一轮对所有通道调 `finish()`」与「读过的通道 `consume()`」两个上游钩子**未实现** | **机制差异**（语义归 checkpoint / 收官） | B7F3 交付 `invoke()` 的完整状态语义时 | **B7F3 / B14F1** |

---

## §3 spec 事实性更正（C-1 … · **只更正事实 · 未改任何判据**）

| # | spec 原文 | 实测结论 | 处置 |
|---|---|---|---|
| **C-1** | FR-014：「super-step 结束时，MUST **只**对**路由型**通道调用 `clear()`」 | 上游只清「**本步未更新**」的通道（`_algo.py:333-341`）⇒ **本步写过的路由通道本轮不清** | **已回写 spec**：FR-014 收紧 + SC-012 同步 + 裁定 10 由 B → **C**（**只补事实**，判据只收紧不放宽） |
| **C-2** | FR-002：「每个通道 MUST 维护**写入版本**」 | 通道对象**没有**版本位（B5F1 冻结的**四个只读属性**）⇒ 版本只能由**调度器**维护（裁定 21 已在澄清轮闭合） | **一致**（澄清轮已闭合，无需再改） |

> ⚠️ **本轮实测**除 C-1 外，**未发现其它与 spec 判据相抵触的事实** ⇒
> **SC-001…SC-025 全部仍成立**（C-1 属**收紧**，SC-012 的判据只变得更可判定）。

---

## §4 遗留的取证动作（**plan 阶段**已完成 · 转交 tasks 阶段取证）

| 动作 | 状态 | 落点 |
|---|---|---|
| 上游 `_triggers` / `prepare_next_tasks` / `apply_writes` 的**行号核实** | ✅ **已完成**（D-01…D-12 · `langgraph 1.2.11` · 2026-11-10） | contracts/upstream-parity.md |
| 上游的**可观察差异**是否需在**差分夹具**中比对 | ⚠️ **归 B8F1**（差分夹具的扩展属 B8F1 · Out of Scope） | 下游承接 **D-1** 的姊妹项 · 登记于 parity P-05 |
| `recursion_limit` 的**对外载体** | ⚠️ **归 B13F1**（FR-011 的 ⚠️ 段已声明） | 交接 |
