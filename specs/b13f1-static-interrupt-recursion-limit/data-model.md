# Data Model · B13F1 · 静态中断点 + `recursion_limit`

**Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md) · **Date**: 2026-11-15

> **纪律**：本文件只落**实体 / 形状 / 校验 / 不变量**（可自动判定的部分）⇒
> **MUST NOT** 改写 spec 的任何语义 ⇒ 一切语义以 `spec.md` 为**唯一权威**。
> ⚠️ 新增私有模块（`_static.py` / `_recursion.py`）**不进** `freegraph.runtime.__all__`
> （仍 **23** 个符号）⇒ **不进** API 兼容矩阵。

---

## §1 实体总览

| # | 实体 | 层 | 公开性 | 关系 |
|---|---|---|---|---|
| **EM-1** | **静态断点字段**（`GraphSpec.interrupt_before` / `.interrupt_after`） | L2 | **公开**（`freegraph.runtime.GraphSpec` 是 L2 内部 API） | 图定义侧 → 一个节点名集合 |
| **EM-2** | **静态断点命中**（before / after） | 运行期（L2） | 内部 | 一个挂起事件 |
| **EM-3** | **静态挂起标记**（`suspension_kind` / `static_ack`） | 运行期（L2） | 内部（检查点 metadata） | 一个挂起现场 ↔ 一次恢复 |
| **EM-4** | **有效递归上限**（`recursion_limit`） | 运行期（L2） | 公开（dict / `RunConfig`） | 一个图运行 → 一个上限 |
| **EM-5** | **`fanout` 检查点账本** | 运行期（L2） | 内部 | 静态 before 的 N 个 fan-out 任务跨挂起保留 |
| **EM-6** | **`InterruptResult`** | L2 | 公开（`freegraph.runtime`） | 静态 / 动态挂起的**同一**结果载体 |
| **EM-7** | **`GraphRecursionError`** | L1 | 公开（`freegraph.contracts`） | 递归超限的失败信号 |
| **EM-8** | **运行配置载体**（dict / `RunConfig`） | L1 / 调用侧 | 公开 | `recursion_limit` 的来源 |

---

## §1.1 EM-1 · `GraphSpec` 的静态断点字段

```python
# src/freegraph/runtime/superstep.py —— GraphSpec（只增两个 keyword-only 字段）
@dataclass(frozen=True)
class GraphSpec:
    channels: dict[str, Channel]
    nodes: dict[str, NodeSpec]
    edges: dict[str | tuple[str, ...], tuple[str, ...]]
    conditional_edges: dict[str, Any] = field(default_factory=dict, kw_only=True)
    interrupt_before: str | Sequence[str] = field(default=(), kw_only=True)
    interrupt_after: str | Sequence[str] = field(default=(), kw_only=True)
```

| 字段 | 类型（构造入参） | 存储形态 | 缺省 | 语义 |
|---|---|---|---|---|
| `interrupt_before` | `str \| Sequence[str]` | `tuple[str, ...]` | `()` | 在目标节点**执行前**整轮挂起 |
| `interrupt_after` | `str \| Sequence[str]` | `tuple[str, ...]` | `()` | 在目标节点**执行并写合并后**挂起 |

**归一规则**（`normalize_static_points` · `_static.py`）：

1. 裸 `"*"` ⇒ **当前节点表的全部可执行节点**（排除 `__start__` / `__end__` 哨兵；顺序 = 节点表插入顺序）；
2. 裸非 `"*"` 字符串（含 `""` / `"__start__"` / `"__end__"` / 普通节点名）⇒ `TypeError`（**V-22**）；
3. 只接受 `Sequence[str]`（`str` 已由第 2 条处理）：逐元素校验 ⇒ 去重（保序）⇒ `tuple`；
   `Mapping` / `set` / 其它非 `Sequence` 可迭代对象 ⇒ `TypeError`（**V-22**）；
4. `None` ⇒ `TypeError`（**B7F2** 负责把 `compile()` 的 `None` 归一为 `()`）；
5. 哈希/不可哈希无关：存 `tuple`，`GraphSpec` 本身仍不可哈希（含 dict 字段）。

### 1.2 校验规则（V-22…V-25 · 构造期 · **单一入口**）

| # | 规则 | 失败信号 | 消息要点 |
|---|---|---|---|
| **V-22** | **裸值**是非 `"*"` 字符串（含空串 / 裸哨兵）；或序列元素非 `str`；或整体不是 `str` / `Sequence`（`None` 另行按 §1.1 第 4 条 ⇒ `TypeError`） | `TypeError` | 点名 `interrupt_before` / `interrupt_after` 与非法值 |
| **V-23** | **序列元素**为空串 `""` | `ValueError` | 点名空串 |
| **V-24** | **序列元素**为 `__start__` / `__end__`，或序列里出现 `"*"`（如 `["*"]`） | `ValueError` | 点名该元素与「不是可挂起的节点名」 |
| **V-25** | 序列元素不在 `spec.nodes` | `ValueError` | 点名该节点（与上游 `Interrupt node ... not found` 同语义） |

> ⚠️ **B7F1 契约既有 V-1…V-9 与 B7F4 的 V-16 形态族一字不改**；**B11F1 的 V-15…V-21**（其 **V-16** 为 `goto` 槽位规则）**段不动**；本 feature 全局续编 **V-22…V-25**（只增）。
> ⚠️ **单一入口**：V-22…V-25 **只由** `normalize_static_points` 抛出；`_validate_graph_spec`
> MUST 只调用它（并写回归一后的 `tuple`），**MUST NOT** 在 `__post_init__` 重复第二套校验。

### 1.3 低层入口拒绝（V-26 · 入口期）

| # | 规则 | 失败信号 | 消息要点 |
|---|---|---|---|
| **V-26** | `run_super_step` / `run_super_steps` 收到 `interrupt_before` 或 `interrupt_after` **非空**的 `GraphSpec` | `ValueError` | 「静态断点只在图级 `run_graph` 生效；低层入口不支持」 |

---

## §2 静态挂起 / 恢复的**状态机**

### 2.1 before（整轮不执行）

```text
RUNNING
  │  determine triggers + recursion check
  │  static_before hit?  ── no ──▶ 正常执行本轮
  │        │ yes
  ▼        ▼
STATIC_BEFORE_SUSPENDED
  ├─ state      = 本轮开始前的稀疏状态
  ├─ interrupts = ()
  ├─ executed   = 已执行过的节点（不含目标）
  ├─ steps      = 已执行轮数（不含本轮）
  ├─ next       = 本轮的标准目标节点（fan-out 现场另存）
  └─ kind       = "static_before"
```

- **不**消费触发源版本、**不**合并写入、**不**推进 `state.step`；
- fan-out 任务仍在 `state.fanout`（并在账本 `fanout` 键里持久化）；
- `__interrupt__` 载荷 = `()`。

### 2.2 after（写合并后挂起）

```text
RUNNING
  │  _run_round(...) 成功
  │  state.step += 1
  │  static_after hit? ── no ──▶ 下一轮
  │        │ yes
  ▼        ▼
STATIC_AFTER_SUSPENDED
  ├─ state      = 本轮写合并后的稀疏状态
  ├─ interrupts = ()
  ├─ executed   = 含本轮所有已执行节点（fan-out N 次则重复 N 次）
  ├─ steps      = 已执行轮数（含本轮）
  ├─ next       = _determine_triggers(spec, state)（标准下一轮触发节点）
  └─ kind       = "static_after"
```

- 目标节点**已执行**；恢复后**不重跑**；
- 若目标是最后节点 ⇒ `next == ()`，仍靠 `suspension_kind` 识别；
- 若本轮有静态 after 命中且有 fan-out 产出 ⇒ `fanout` 账本保留，恢复时先跑 fan-out。

### 2.3 恢复分支（`_first_graph` / `_resume_graph`）

| 输入 | `suspension_kind` | 行为 |
|---|---|---|
| `None` | 静态值 | `first_round = snapshot.next`（可空）；传 `static_ack` 继续 |
| `None` | 非静态 | 既有 B10F1「会话连续」路径（不变） |
| `Command(resume=...)` | 静态值 + `interrupts == ()` | **不**抛 `no_pending_interrupt`；忽略 resume 值；按 `snapshot.next` 继续；**MUST 传 `static_ack`**（否则静态 before 恢复首轮立即重挂） |
| `Command(resume=...)` | 非静态 + `interrupts == ()` | 既有 `no_pending_interrupt`（不变） |
| `Command(resume=...)` | 非静态 + `interrupts` 非空 | 既有动态恢复（不变） |
| `StateDict`（**非空写入**） | 任意 | 先按通道写输入（新进度）⇒ 再继续；静态 ack 由新版本自然放行 |
| **空 `StateDict`（`{}`）** | 静态值 | 无任何通道写入 ⇒ **与 `input=None` 同款传 `static_ack`** ⇒ 同一断点不立即重挂 |
| 任意 | 任意 + 无 checkpointer | 不声称恢复；`Command` 路径抛 `checkpointer_required`（`input=None` / `{}` 视为新运行） |

### 2.4 完成时的清标记（D-08）

```text
静态恢复 → SuperStepResult
  ⇒ checkpointer.put(
       values = 最终稀疏状态,
       metadata = {
         "next": (),
         "interrupts": (),
         "tasks": (),
         "suspension_kind": None,
         "static_ack": None,
         "scheduler": {..., "fanout": {}, "suspension_kind": None, "static_ack": None},
       },
     )
```

> 目的：防止旧快照的 `next` / `suspension_kind` 在后续 `input=None` 时被再次当成挂起
> （静态 before 会重复执行）。这是**完成快照**，不是新的挂起路径；登记为 **F-10**
> （一次性完成写；每轮末快照仍归 B14F1，不得重复 / 冲突）。

### 2.5 防重复触发（ack）

```python
def static_allowed(ack: Mapping[str, Any] | None, state: SchedulerState) -> bool:
    if ack is None:
        return True
    previous = ack["channel_versions"]
    current = state.channel_versions
    return any(
        current.get(key, 0) > previous.get(key, 0)
        for key in set(previous) | set(current)
    )
```

| 场景 | 结果 |
|---|---|
| 首次运行（ack = `None`） | 允许触发 |
| 静态挂起后立即恢复、无新写入 | **抑制**（防死循环） |
| 恢复后执行了至少一个写通道 | 允许再次触发 |
| 恢复后写入一个**新通道**（旧 ack 无此键） | 允许再次触发（新键视为 0 → >0） |
| 目标执行但**没有**任何通道写入 | 抑制（与上游 `should_interrupt` 同款） |

---

## §3 检查点形状

### 3.1 `_suspend_metadata`（静态 / 动态共用）

```python
{
    "next": tuple[str, ...],                 # 静态 next 可为空
    "interrupts": tuple[Interrupt, ...],     # 静态 = ()
    "tasks": (),
    "scheduler": {
        "versions_seen": ...,
        "channel_versions": ...,
        "node_versions": ...,
        "dynamic_edges": ...,
        "fanout": {...},                      # 新增（F-3）
        "suspension_kind": "static_before" | "static_after" | None,
        "static_ack": {"channel_versions": {...}} | None,
    },
    "suspension_kind": "static_before" | "static_after" | None,
    "static_ack": {"channel_versions": {...}} | None,
}
```

> **为什么镜像两份**：当前 `Checkpointer.get_tuple` 的 `_CheckpointTuple` 只把 `.scheduler`
> 暴露给 L2（`tests/runtime/test_interrupt_checkpoint.py:77-79`）⇒ L2 恢复从 `scheduler`
> 读取；B14F1 的 `MemorySaver` 从顶层 metadata 读取 ⇒ 两边都覆盖。

### 3.2 `fanout` 账本编码（F-3）

```python
"fanout": {
    "0": {
        "producer": "fan",
        "suppresses_static": False,
        "tasks": [
            {"target": "worker", "arg": {"n": 1}, "index": 0, "suppresses_static": False},
            {"target": "worker", "arg": {"n": 2}, "index": 1, "suppresses_static": False},
        ],
    },
    ...
}
```

| 键 | 类型 | 说明 |
|---|---|---|
| 外层 key | `str(int)` | 产生者 **TaskId**（JSON 对象的键只能是字符串） |
| `producer` | `str` | 产生者节点名（按 `(producer, target)` 抑制） |
| `suppresses_static` | `bool` | 载体 B = `True`；载体 A = `False` |
| `tasks[].target` | `str` | 目标节点名 |
| `tasks[].arg` | `Any` | **原样**入参（JSON 兼容时可直接往返；非 JSON 见 DR-01） |
| `tasks[].index` | `int` | 载荷内序号 |
| `tasks[].suppresses_static` | `bool` | 逐任务载体标志 |

- `from_checkpoint`：缺 `"fanout"` 键 ⇒ `{}`（旧快照宽容）；
- 外层 key 能转 `int` ⇒ 转；否则保持原样（防御性解码，不抛）；
- ⚠️ **恢复链路**：`_restore_scheduler` MUST 把 `from_checkpoint` 还原出的 `fanout`
  回填到 `state.fanout`（只改 `to_checkpoint` / `from_checkpoint` 不够；否则纯 fan-out
  before 挂起恢复时任务现场丢失）。
- ⚠️ **破 B11F1 冻结面（F-3 · 拆分而不删）**：B11F1 交付时 `to_checkpoint` **不含** `fanout`
  （`contracts/send-contract.md` §5.1 · `data-model.md` I-12 · `tasks.md` T019 · `plan.md` PR-8 ·
  `research.md` DR-02）；自 **B13F1** 起**含** `fanout`（静态挂起必须跨挂起保留 fan-out 现场）⇒
  B11F1 的「不含」历史断言保留并标注「B13F1 F-3 起被拆分」。持久化**存储**仍归 B14F1。

### 3.3 `InterruptResult`（**不变** · 4 字段）

| 字段 | 静态 before | 静态 after |
|---|---|---|
| `state` | 本轮开始前 | 本轮写合并后 |
| `interrupts` | `()` | `()` |
| `executed` | 不含目标 | 含目标（fan-out N 次则重复 N 次） |
| `steps` | 不含本轮 | 含本轮 |

`as_result_dict()` = `{**state, "__interrupt__": ()}`。

---

## §4 EM-4 · 有效递归上限

### 4.1 解析优先级

```text
config["recursion_limit"]           # dict 形态（规范载体）
  ↕ 互斥二选一（一次运行只接受一个 config 对象）
  RunConfig.recursion_limit          # 等价备用载体
  > max_steps                        # 既有 L2 内部直控参数（缺省 10007）
  > DEFAULT_RECURSION_LIMIT = 10007  # 最终缺省
```

> ⚠️ **不新增** `recursion_limit=` 关键字（上游 1.2.11 也没有）⇒
> `run_graph` 只放宽 `config` 注解；**不存在「同时提供 dict 与 RunConfig」的路径**。

### 4.2 校验规则（V-R1…V-R4）

| # | 规则 | 失败信号 |
|---|---|---|
| **V-R1** | **非 `None` 值**且 `type(value) is not int`（含 `bool`） | `TypeError` |
| **V-R2** | `value < 1` | `ValueError`（消息含 `at least 1`） |
| **V-R3** | `config` 不是 `None` / `Mapping` / `RunConfig` | `TypeError` |
| **V-R4** | dict 里的未知键 | **忽略**（`ignore_unknown=True`） |

> ⚠️ **`recursion_limit=None` 跳过 V-R1 / V-R2**：视为「未提供」⇒ 落回 `max_steps` /
> `DEFAULT_RECURSION_LIMIT`；**MUST NOT** 因 `None` 抛 `TypeError`。

### 4.3 计数口径

| 事件 | 是否计 1 轮 |
|---|---|
| 本轮执行了 ≥ 1 个标准任务 / fan-out 任务 | ✅ **1 轮**（不论任务数） |
| 被 `interrupt_before` 拦住、未执行任何任务 | ❌ **0 轮** |
| `interrupt_after` 所在轮 | ✅ **1 轮** |
| 终轮「发现没有任务」的空轮 | ❌ 不计（`SchedulerState.step` 口径） |
| fan-out 任务在下一轮执行 | ✅ 计下一轮（B11F1 的 D-2 · 不绕过上限） |
| 从静态挂起恢复 | ✅ **新的独立预算**（每次 `run_graph` 重新计数；`step` 不落盘 · B10F1） |

上限判定：`state.step >= effective_limit` **且**仍有待执行任务 ⇒
`GraphRecursionError(recursion_limit=effective_limit, current_step=state.step)`。

> ⚠️ **计数范围 = 单次 `run_graph`**：静态挂起恢复不累计、不回填步数 ⇒ 与 B10F1
> 的「`SchedulerState.step` 不落盘」一致；`static_ack` 只做断点防重复，不承载步数。

---

## §5 EM-8 · 运行配置载体

```python
run_graph(
    spec,
    input=None,
    *,
    state=None,
    checkpointer=None,
    config: RunConfig | Mapping[str, Any] | None = None,
    max_steps: int = 10007,
    max_concurrency: int | None = None,
)
```

| `config` 形态 | 处理 |
|---|---|
| `None` | `RunConfig()`；`config_limit = None` |
| `RunConfig` | 原样；`config_limit = config.recursion_limit` |
| `Mapping` | `RunConfig.from_dict(config, ignore_unknown=True)`；`config_limit = .recursion_limit` |
| 其它 | `TypeError`（V-R3） |

> `RunConfig.from_dict(..., ignore_unknown=True)` 会保留 `thread_id` / `configurable`
> 等既有字段 ⇒ checkpointer 仍能工作。

---

## §6 不变量（I-S1…I-S15 · I-R1…I-R8）

### 静态断点

| # | 不变量 |
|---|---|
| **I-S1** | `interrupt_before` 命中 ⇒ 目标执行 **0** 次；本轮写入 **0** 条合并。 |
| **I-S2** | `interrupt_after` 命中 ⇒ 目标执行 **1** 次（fan-out N 次）；本轮写入已合并。 |
| **I-S3** | 静态挂起的 `interrupts == ()`；`as_result_dict()` 含 `"__interrupt__": ()`。 |
| **I-S4** | 静态挂起**不**新增 `InterruptResult` 字段；`suspension_kind` / `static_ack` 只在 metadata / 账本。 |
| **I-S5** | `suspension_kind` 为静态值时，`next` **允许为空**；不得仅以 `next` 非空判定静态挂起。 |
| **I-S6** | 合法静态挂起**不得**被误判为 `no_pending_interrupt`。 |
| **I-S7** | 同一断点在无新通道写入时**不**重复触发；有新写入后可再次触发。 |
| **I-S8** | 优先级：递归超限 > 静态 before；真异常 > 动态中断 > 静态 after > 完成。 |
| **I-S9** | fan-out 的 N 个任务在 before 时全部保留、after 时各执行一次；**不**合并、**不**伪造载荷。 |
| **I-S10** | fan-out 现场（目标 / 原样入参 / TaskId / 抑制标志）跨静态挂起**逐项不变**。 |
| **I-S11** | 低层入口收到非空静态字段 ⇒ **显式拒绝**（V-26）；签名 / 返回类型不变。 |
| **I-S12** | `"*"` 在构造期展开为当前节点表的**可执行节点**（排除 `__start__` / `__end__`）；`["*"]` 与裸非 `"*"` 字符串非法。 |
| **I-S13** | 静态恢复完成时**只写一次**完成快照（F-10），清 `suspension_kind` / `static_ack` / `next` / `fanout`；**不是**每轮末快照。 |
| **I-S14** | 空 `StateDict`（`input={}`）无任何通道写入 ⇒ 与 `input=None` 同款传 `static_ack` ⇒ 同一断点不立即重挂。 |
| **I-S15** | `Command(resume=...)` 静态恢复 MUST 传 `static_ack`；`interrupt_before` 恢复首轮不得立即重挂；`input=None` 与 `Command` 两条入口同款。 |

### 递归上限

| # | 不变量 |
|---|---|
| **I-R1** | 默认有效上限 = **10007**；不读任何环境变量。 |
| **I-R2** | 计数单位 = **super-step 执行轮**；N 个任务同轮 = 1 轮。 |
| **I-R3** | fan-out 轮**计入**；不绕过上限。 |
| **I-R4** | 超限抛 `GraphRecursionError`；`.recursion_limit` / `.current_step` 如实。 |
| **I-R5** | dict / `RunConfig` 互斥（一次一个） > `max_steps` > 默认；**不新增**显式关键字。 |
| **I-R6** | **非 `None` 值**的 `0` / 负数 ⇒ `ValueError`；非 `int` / `bool` / 浮点 ⇒ `TypeError`；入口立即失败。`None` 视为未提供（落回下一层），**不**抛 `TypeError`。 |
| **I-R7** | dict 未知键忽略；`recursion_limit` 非法值不忽略。 |
| **I-R8** | `GraphRecursionError` 原样传播，不被包装。 |
