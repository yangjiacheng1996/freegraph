# Upstream Parity · B14F1 · Checkpointer / `MemorySaver`

**Feature**: B14F1 · **Date**: 2026-11-22 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Upstream**: `langgraph` **1.2.11**（取证于 2026-11-22）

> 本文件是**差分场景组**与**上游锚点**的契约。判词：
> `SAME` = 逐条一致；`STRICTER` = freegraph 刻意更严（须写理由）；`DIFF` = 已登记差异。
> 三态标注 MUST 与 spec 的 P 表 / X 表**逐字一致**（宪法原则 XI）。
> 差分落 `tests/differential/test_b14f1_checkpoint_parity.py`；上游缺席 ⇒ **skip**。

---

## 1. 上游锚点（只列本 feature 依赖的）

| # | 语义 | 上游锚点 |
|---|---|---|
| A-01 | `PendingWrite = tuple[str, str, Any]` | `checkpoint/base/__init__.py:32` |
| A-02 | `Checkpoint` / `CheckpointTuple` | `checkpoint/base/__init__.py:93-147` |
| A-03 | `BaseCheckpointSaver` 的 8 方法 | `checkpoint/base/__init__.py:199,262,277,301,324,344,355,374,721` |
| A-04 | `InMemorySaver` / `MemorySaver` 别名 | `checkpoint/memory/__init__.py:34,634` |
| A-05 | `get_tuple` / `list` | `checkpoint/memory/__init__.py:239,321` |
| A-06 | `put` / `put_writes` | `checkpoint/memory/__init__.py:430,476` |
| A-07 | `delete_thread` / `delete_for_runs` / `copy_thread` | `checkpoint/memory/__init__.py:514` · `checkpoint/base/__init__.py:355,374` |
| A-08 | `get_next_version`（默认 int / memory 字符串） | `checkpoint/base/__init__.py:721-740` · `checkpoint/memory/__init__.py:622-630` |
| A-09 | checkpoint id 生成（`uuid6`） | `pregel/_checkpoint.py:31,209` |
| A-10 | 中断写 pending writes / 真异常优先 / 合并中断 | `pregel/_runner.py:588-591,687,690` |
| A-11 | `checkpoints` 事件 / `map_debug_checkpoint` | `pregel/_loop.py:631-636` · `pregel/debug.py:144-185` |
| A-12 | `StateSnapshot` 8 字段 | `types.py:684-701` |
| A-13 | `ensure_valid_checkpointer` | `types.py:109-118` · `graph/state.py:1179,1234` |
| A-14 | 保留通道名 | `_internal/_constants.py:9,11,13,17` |
| A-15 | `True` / `False` 运行期分支 | `pregel/main.py:2579-2583` |

> ⚠️ 换上游版本 MUST 重新核实全部行号（原则 VIII / FR-035）。

---

## 2. 语义点对照（P-01…P-21）

> 与 spec §Upstream Parity 的 P 表**逐字一致**；此处只列判词与关键差异。

| # | 语义点 | freegraph 口径 | 关系 |
|---|---|---|---|
| **P-01** | 内存 saver 入口 / 别名 | `freegraph.persistence.MemorySaver`；`InMemorySaver` 同对象（模块路径由层注册表固定 · 包名差异非行为偏离） | SAME |
| **P-02** | pending write 三元组 / 排序 | `(task_id, channel, value)`；顺序 = `(task_path, task_id, idx)` 升序 | SAME |
| **P-03** | `get_tuple` 最新 / 按 id | 最新 / 指定 / 不存在 `None` | SAME |
| **P-04** | `list` 顺序 / 过滤 | `config=None` 线程**插入序**；同线程 id 降序；`filter` / `before` / `limit` | SAME |
| **P-05** | `put` 快照 + 父链 + 返回 config | 返回带新 id 的 `RunConfig`；关键字由 B10F1 冻结（非行为偏离） | SAME |
| **P-06** | `put_writes` 去重 / 覆盖 | 键 `(task_id, WRITES_IDX_MAP.get(channel, idx))`；普通跨调用同 idx 首次；保留最后（同调用内也覆盖） | SAME |
| **P-07** | `delete_thread` | 删除快照 + 写入 + 内部状态；幂等 | SAME |
| **P-08** | `delete_for_runs` / `copy_thread` | 存在；v1 `NotImplementedError` | SAME |
| **P-09** | `get_next_version` | `int+1` | DIFF（X-02） |
| **P-10** | checkpoint id 生成 | 每线程单调 32 位零填充十进制 | DIFF（X-01） |
| **P-11** | `StateSnapshot` 8 字段 | L1 8 字段逐字同构 | SAME |
| **P-12** | 保留通道名 | `__interrupt__` / `__resume__` / `__error__` / `__scheduled__` | SAME |
| **P-13** | 真异常 + 中断同现 | 先 `put_writes`，再原样抛 | SAME |
| **P-14** | `checkpoints` 事件数据源 | `on_checkpoint` + `list()`；stream 消费端归 B8F2 / B15F1 | SAME |
| **P-15** | 编译期 checkpointer 校验 | `None` / `True` / `False` / 满足 L1 协议的鸭子类型；其它 `TypeError` | DIFF（X-08） |
| **P-16** | 线程隔离存储键 | `thread_id` 一级键 | SAME |
| **P-17** | 开发 / 调试定位 | 内存实现；生产归 B15F1 | SAME |
| **P-18** | 缺失 `thread_id` | 运行期跳过；直接调用 `ValueError` | DIFF（X-03） |
| **P-19** | `context` 持久化 | 明确不持久化；`snapshot.config.context is None` | DIFF（X-04） |
| **P-20** | 序列化 / 拷贝 | `copy.deepcopy` 而非 msgpack | DIFF（X-05） |
| **P-21** | `True` / `False` 运行期 | 编译接受、运行期视为无 saver | DIFF（X-06） |

---

## 3. 差分场景组（D-01…D-15）

> 全部落 `tests/differential/test_b14f1_checkpoint_parity.py`；
> `pytest.importorskip("langgraph")`；上游缺席 ⇒ skip。
>
> ⚠️ 上游 `InMemorySaver` 额外保存 `__start__` checkpoint（`metadata["step"] == -1`）；
> 「实际 super-step 快照」计数 MUST 排除它。

| # | 场景 | 断言 | 判词 |
|---|---|---|---|
| **D-01** | 单节点图 + `MemorySaver` | 完成；快照数 == 1 + 1；`next=()` | SAME |
| **D-02** | `a → b` 两节点图 | 快照数 == 2 + 1；每轮 `values` 稀疏状态一致 | SAME |
| **D-03** | `get_tuple` 最新 / 指定 id | 返回值一致；未知 id ⇒ `None` | SAME |
| **D-04** | `put_writes` 去重 / 覆盖 / 排序 | 普通跨调用同 `(task_id, idx)` 首次；保留最后（同调用内也覆盖）；按 `(task_path,task_id,idx)` | SAME |
| **D-05** | 两个 `thread_id` 并行 | 互不可见；`delete_thread` 只清一个 | SAME |
| **D-06** | `list` 的 `filter` / `before` / `limit` | 结果集合 / 顺序 / 长度一致；`config=None` 线程插入序 | SAME |
| **D-07** | `interrupt` → `Command(resume=...)` | 只重跑被中断节点且从节点起点重跑；拿到 resume 值；已完成节点不重复 | SAME |
| **D-08** | `interrupt_before` 挂起 → 恢复 | 静态挂起（`interrupts=()`）可恢复；完成快照只写一次 | SAME |
| **D-09** | `Send` fan-out 挂起 | 多任务 `task_id` 各自唯一；pending writes 去重 / 排序同款 | SAME |
| **D-10** | 多源屏障暂停 → 恢复 | 目标不重复触发；`seen` 保留 | SAME |
| **D-11** | 真异常 + 中断同现 | 抛真异常；pending writes 含中断元组 | SAME |
| **D-12** | 非法 checkpointer 编译 | 两侧 `TypeError` | SAME（B7F2 X-4 消解） |
| **D-13** | `checkpointer=True` / `False` | 编译接受、记录；运行期不落盘；不抛 `AttributeError` | DIFF（X-06） |
| **D-14** | 缺失 `thread_id` + checkpointer | 上游明确失败（实测 1.2.11 抛 `ValueError`）；freegraph 正常执行且不落盘 | DIFF（X-03） |
| **D-15** | 非空 `context` | 上游可能写入 config；freegraph 快照中 `context is None` | DIFF（X-04） |

### 3.1 比较口径

- **快照数**：`len(list(config))`；两侧均按「实际执行轮数 + 1」。
- **`values`**：只比较稀疏状态；不比较内部对象 identity。
- **`next`**：元组逐项相等。
- **pending writes**：按 `(task_path, task_id, idx)` 排序后逐项比较（上游 `writes_sort_key`）；
  保留通道的覆盖语义逐条比较。
- **异常**：只比较成功 / 失败 + 类型名 + 是否原样抛出；不比较消息（上游措辞不同）。
- **真异常 + 中断**：比较 pending writes 是否含 `__interrupt__`；比较异常 identity / 类型 / 消息
  与「未挂 saver」时一致（freegraph 内部对照）。

---

## 4. 偏离登记（X-01…X-08）

| # | 类别 | 被偏离的判据 | 理由 | 承接方 |
|---|---|---|---|---|
| **X-01** | 自研区（内存实现细节） | P-10：checkpoint id 用每线程单调计数器，非 `uuid6` | 标准库无 `uuid6`；零填充十进制可排序；B15F1 可换后端自定 | 本 feature · B15F1 知情 |
| **X-02** | 自研区（版本命名空间） | P-09：`get_next_version` 返回 `int`，非上游 memory 字符串 | B7F1 的调度版本是 `int`；统一命名空间避免漂移 | 本 feature · B15F1 知情 |
| **X-03** | 更明确的失败信号 / 更宽容的落盘 | P-18：无 `thread_id` 时运行期跳过；直接调用 `ValueError`（上游明确失败 · 实测 `ValueError`） | SC-005：注入 checkpointer 不改变执行结果；不静默共享会话 | 本 feature |
| **X-04** | 破已冻结契约面（B8F3 D-1 / D-3） | P-19：`context` 不持久化 | B8F3 已拍板 `context` 是运行期上下文 | **B8F3**（上游已冻结） |
| **X-05** | 自研区（内存实现细节） | P-20：`copy.deepcopy` 而非 msgpack | 零第三方依赖；内存 saver 无需跨进程序列化 | 本 feature · B15F1 知情 |
| **X-06** | 自研区（v1 能力边界） | P-21：`True` / `False` 运行期视为无 saver | v1 无子图（C26 属 v2）；保持 B7F2 记录面不破 | **B7F2**（记录面不变）· C26（v2） |
| **X-07** | 更明确的失败信号 | P-06：`put_writes` 指定 id 不存在 ⇒ `ValueError`（上游静默写入悬挂桶） | 与 X-03 同源；缺 `checkpoint_id` 的 `KeyError` 仍逐字上游 | 本 feature · B15F1 知情 |
| **X-08** | 自研区（零依赖约束） | P-15：接受任何满足 L1 `Checkpointer` 的鸭子类型对象（上游要求 `BaseCheckpointSaver` 子类） | 零依赖 preclude import 上游基类；协议是唯一等价判定 | 本 feature · B7F2 知情 |

> **失败信号 STRICTER 清单**：`delete_thread(non-str)` ⇒ `TypeError`；
> `get_next_version` 非 `int` / `bool` ⇒ `TypeError`；`put_writes` 指定 id 不存在 ⇒ `ValueError`。
> 均属失败信号，非成功路径行为面偏离。

> **P-14 的消费端边界不登记为偏离**：D-2 只要求数据源；`stream(checkpoints)` 接线归
> B8F2 / B15F1，属 **Out of Scope**（能力边界 · 非偏离）。

---

## 5. 回归 / 差分门禁

| 门禁 | 判据 |
|---|---|
| **上游在场** | D-01…D-12 通过率 == 100%；D-13…D-15 按判词接受差异 |
| **上游缺席** | 全部 skip（不是 fail） |
| **既有场景** | `parity_probe.py` 的其它场景**逐字不变**；仅 D-77 判词更新（R-1） |
| **证据** | 每条上游断言带版本 + `路径:行号`；缺失数 == 0 |
| **三态一致** | P 表 / X 表 / D 表的 SAME / STRICTER / DIFF 标注逐字一致 |

---

## 6. 与 spec 的对应

| 本文件 | spec |
|---|---|
| P-01…P-21 | §Upstream Parity 的 P 表 |
| D-01…D-15 | §差分场景组 |
| X-01…X-08 | §偏离登记 |
| A-01…A-15 | §依据 / P 表的行号 |
