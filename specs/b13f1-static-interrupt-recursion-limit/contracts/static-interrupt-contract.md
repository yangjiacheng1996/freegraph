# 契约 · B13F1 · 静态中断点（`interrupt_before` / `interrupt_after`）

**Spec**: [../spec.md](../spec.md) · **Data Model**: [../data-model.md](../data-model.md) · **Date**: 2026-11-15
**上游版本**: `langgraph` **1.2.11**

> 本契约冻结**运行期语义 / 形状 / 校验 / 不变量**。语义以 `spec.md` 为**唯一权威**；
> 本文件若与 spec 冲突 ⇒ 以 spec 为准。

---

## §1 图定义侧的配置

### §1.1 字段

```python
@dataclass(frozen=True)
class GraphSpec:
    channels: dict[str, Channel]
    nodes: dict[str, NodeSpec]
    edges: dict[str | tuple[str, ...], tuple[str, ...]]
    conditional_edges: dict[str, Any] = field(default_factory=dict, kw_only=True)
    interrupt_before: str | Sequence[str] = field(default=(), kw_only=True)
    interrupt_after: str | Sequence[str] = field(default=(), kw_only=True)
```

- 两个字段 **keyword-only** · 缺省 `()` ⇒ 既有 `GraphSpec(...)` 调用**零改动**；
- 存储形态统一为 `tuple[str, ...]`（去重 · 保序）；
- **MUST NOT** 用 `RunConfig` 作为静态断点的载体。

### §1.2 归一与校验（构造期）

| # | 输入 | 结果 / 失败信号 |
|---|---|---|
| **V-22** | **裸值**是非 `"*"` 字符串（含空串 / 裸哨兵）；或序列元素非 `str`；或整体不是 `str` / `Sequence`（`None` 另行 ⇒ `TypeError`） | `TypeError` |
| **V-23** | **序列元素**为 `""` | `ValueError` |
| **V-24** | **序列元素**为 `__start__` / `__end__`；或序列中出现 `"*"` | `ValueError` |
| **V-25** | 序列元素不在 `spec.nodes` | `ValueError`（消息点名该节点） |
| — | 裸 `"*"` | 展开为当前节点表的**全部可执行节点**（排除 `__start__` / `__end__` 哨兵） |
| — | 重复元素 | 去重（保序） |
| — | `()` / 空序列 | 关闭 |
| — | `None` | `TypeError`（`compile()` 的 `None` 由 **B7F2** 归一为 `()`） |

> **B7F1 契约既有 V-1…V-9 与 B7F4 的 V-16 形态族一字不改**；**B11F1 的 V-15…V-21**（其 **V-16** 为 `goto` 槽位规则）**段不动**；本 feature 全局续编 **V-22…V-25**（只增）。
> ⚠️ **单一入口**：V-22…V-25 **只由** `normalize_static_points` 抛出；`_validate_graph_spec`
> MUST 只调用它并写回归一后的 `tuple`（**MUST NOT** 在 `__post_init__` 重复第二套校验）。
> `"*"` 的语义与上游 P-17 **同款**：裸 `"*"` = All（freegraph 展开为**可执行**节点）；
> `["*"]` = 不是节点名 ⇒ 失败。

---

## §2 `interrupt_before` 的语义

### §2.1 判定位置（逐字）

在 `_run_graph_loop` 的每一轮：

1. 若 `triggered is None` ⇒ `_determine_triggers(spec, state)`；
2. 若「无标准任务且 `state.fanout` 为空」⇒ 结束；
3. 递归上限检查（`state.step >= effective_limit`）⇒ 超限优先抛；
4. **静态 before 检查**：本轮待执行任务（标准 `triggered` + `state.fanout` 的任务）
   中**任一** `target ∈ spec.interrupt_before` ⇒ **整轮不执行**；
5. 否则正常 `_run_round`。

> ⚠️ **局部轮次计数器**：循环顶部的 `steps += 1` **不得**为 before 检查而移动
> （空终轮口径属 B7F1 冻结面）⇒ 静态 before 挂起时 `InterruptResult.steps`
> MUST 取 `循环 steps - 1`（不含本轮）。

### §2.2 挂起结果

| 项 | 值 |
|---|---|
| 返回类型 | `InterruptResult` |
| `state` | 本轮开始前的稀疏状态（`_sparse_state`） |
| `interrupts` | `()` |
| `executed` | 已执行过的节点（**不含**本轮目标） |
| `steps` | 已执行轮数（**不含**本轮） |
| `as_result_dict()` | `{**state, "__interrupt__": ()}` |

**副作用禁令**：

- **MUST NOT** 消费触发源版本；
- **MUST NOT** 合并本轮写入；
- **MUST NOT** 推进 `state.step`；
- **MUST NOT** 清空 `state.fanout`；
- **MUST NOT** 为静态断点写 `__interrupt__` 的 `put_writes`（载荷为空，无可留痕的节点级中断）。

---

## §3 `interrupt_after` 的语义

### §3.1 判定位置（逐字）

1. `_run_round` 成功返回（无真异常 / 无动态中断）；
2. 收集本轮写入，`state.step += 1`；
3. **静态 after 检查**：`round_executed` 中**任一** `target ∈ spec.interrupt_after`
   ⇒ 挂起；否则继续下一轮。⚠️ **MUST NOT** 把 `state.fanout`（下一轮待执行任务）
   纳入 after 判定 —— after 只看**本轮已执行**的任务。

### §3.2 挂起结果

| 项 | 值 |
|---|---|
| 返回类型 | `InterruptResult` |
| `state` | 本轮写合并后的稀疏状态 |
| `interrupts` | `()` |
| `executed` | 含本轮所有已执行节点（fan-out N 次 ⇒ 目标名出现 N 次） |
| `steps` | 含本轮 |
| `next`（metadata） | `_determine_triggers(spec, state)` 的标准下一轮节点；可为 `()` |
| `as_result_dict()` | `{**state, "__interrupt__": ()}` |

**恢复后**：**MUST NOT** 重跑本轮已执行的节点。

---

## §4 优先级

| 顺序 | 事件 |
|---|---|
| 1 | 递归超限（`GraphRecursionError`） |
| 2 | 静态 `interrupt_before` |
| 3 | 真异常（`_run_round` 阶段 ⑥） |
| 4 | 动态中断（`GraphInterrupt` 合并元组） |
| 5 | 静态 `interrupt_after` |
| 6 | 正常完成 |

- 同一节点同时配 before / after ⇒ **before 先挂起**；恢复后执行，**after 再挂起**；
- 静态 after **不得**吞掉真异常 / 动态中断的载荷；
- 静态 before 在递归检查**之后**判定（上游 P-18 同款）。

---

## §5 检查点写侧

### §5.1 metadata 形状

```python
{
    "next": tuple[str, ...],                  # 静态 before = 标准待执行目标；after = 下一轮触发；可空
    "interrupts": (),                         # 静态挂起 = 空元组
    "tasks": (),
    "scheduler": {
        "versions_seen": {...},
        "channel_versions": {...},
        "node_versions": {...},
        "dynamic_edges": {...},
        "fanout": {...},                      # F-3
        "suspension_kind": "static_before" | "static_after" | None,
        "static_ack": {"channel_versions": {...}} | None,
    },
    "suspension_kind": "static_before" | "static_after" | None,
    "static_ack": {"channel_versions": {...}} | None,
}
```

- `suspension_kind` / `static_ack` 同时镜像进 `scheduler` 子字典（**F-9 要求**；
  当前 L2 恢复从 `history.scheduler` 读取；B14F1 从顶层 metadata 读取）。
- **MUST NOT** 把 `suspension_kind` 放进 `InterruptResult`（仍 **4 字段**）。

### §5.2 `next` 的唯一口径

| kind | `next` |
|---|---|
| 动态中断 | 被中断的节点名（既有 B10F1 口径） |
| `static_before` | 本轮的标准目标节点（去重；fan-out 现场另存） |
| `static_after` | `_determine_triggers(spec, state)` 的标准下一轮节点（可为空） |

> **MUST NOT** 把「刚执行过的 after 目标」强行列入 `next`（否则恢复会重跑）。

---

## §6 恢复路径

### §6.1 `input=None`

- 从 `history.scheduler` 读 `suspension_kind` / `static_ack`；
- `first_round = _resume_target_nodes(snapshot, interrupts)`（可为空）；
- 调 `_run_graph_loop(..., static_ack=ack)`；静态 before 由 ack **抑制**，
  同一断点**不会**立即再次触发。

### §6.2 `Command(resume=...)`

- 仍要求 `resume is not None`（否则 `resume_value_required`）；
- 仍要求 checkpointer（否则 `checkpointer_required`）；
- 若 `interrupts == ()` 且 `suspension_kind` 为静态值 ⇒ **在进入 `per_node` 映射之前**
  直接走静态恢复分支（**不**执行 `next(iter(interrupts))`）；**不**抛
  `no_pending_interrupt`；**忽略** resume 值（没有节点级中断可接收）；
- **MUST 把 `history.scheduler` 的 `static_ack` 传给 `_run_graph_loop`**（否则静态
  `interrupt_before` 会在恢复首轮立即重挂）；
- 按 `snapshot.next` 继续；
- 若 `suspension_kind` 为空 / 非静态且 `interrupts == ()` ⇒ 既有
  `no_pending_interrupt`（**不变**）。

### §6.3 状态字典输入

- 先按通道写 `input`（新进度 ⇒ 通道版本推进）；
- 静态 ack 因版本推进而自然放行；
- 走既有「会话连续 + 状态字典」路径（不重写）；
- **空 `StateDict`（`input={}`）**：没有任何通道写入 ⇒ **与 `input=None` 同款传
  `static_ack`** ⇒ 同一断点不立即重挂（不得把「空 dict」当作「有新输入」）。

### §6.4 完成时清标记

若本次运行是**静态恢复**且最终返回 `SuperStepResult` ⇒ 写一次**完成快照**（**F-10** · 一次性完成写；**不是**每轮末快照，后者仍归 B14F1）：

```python
checkpointer.put(
    run_config,
    values=最终稀疏状态,
    metadata={
        "next": (),
        "interrupts": (),
        "tasks": (),
        "suspension_kind": None,
        "static_ack": None,
        "scheduler": {..., "fanout": {}, "suspension_kind": None, "static_ack": None},
    },
)
```

> 否则旧快照的 `next` / `suspension_kind` 会在后续 `input=None` 时被再次当成挂起。

---

## §7 防重复触发（ack）

```python
def static_allowed(ack, state):
    if ack is None:
        return True
    previous = ack["channel_versions"]
    current = state.channel_versions
    return any(
        current.get(key, 0) > previous.get(key, 0)
        for key in set(previous) | set(current)
    )
```

| 场景 | 触发 |
|---|---|
| 首次运行（ack=None） | ✅ |
| 恢复后无新写入 | ❌ 抑制 |
| **空 `StateDict`（`input={}`）恢复** | ❌ 抑制（无新写入，与 `input=None` 同款） |
| 恢复后执行并写了至少一个通道 | ✅ |
| 恢复后写入一个**新通道**（旧 ack 无此键） | ✅（新键视为 0 → >0） |
| 目标执行但无任何写入 | ❌ 抑制（上游同款） |

---

## §8 fan-out 交互

- `interrupt_before`：N 个 fan-out 任务**各自保留**（TaskId / 原样入参 / 顺序）⇒
  恢复后**恰好**重试 N 个；**MUST NOT** 合并 / 重排 / 重新生成；
- `interrupt_after`：N 个**各执行一次**；`executed` 中目标名出现 N 次；
- 载荷：`__interrupt__ == ()`；**MUST NOT** 伪造 N 个 `Interrupt`；
- `fanout` 账本形状见 data-model §3.2；缺键 ⇒ `{}`（旧快照宽容）。

---

## §9 低层入口

```python
run_super_step(spec, state, *, max_concurrency=None) -> SuperStepResult
run_super_steps(spec, state=None, *, max_steps=10007, max_concurrency=None) -> SuperStepResult
```

- 签名 / 返回类型 **一字不动**；
- 若 `spec.interrupt_before` 或 `spec.interrupt_after` 非空 ⇒ **V-26**：
  `ValueError`（消息点名「静态断点只在图级 run_graph 生效」）；
- **MUST NOT** 静默忽略，**MUST NOT** 为低层入口改返回类型。

---

## §10 不变量

| # | 不变量 |
|---|---|
| **I-S1** | before 命中 ⇒ 目标执行 0 次、本轮写入 0 条合并。 |
| **I-S2** | after 命中 ⇒ 目标执行 1 次（fan-out N 次）、本轮写入已合并。 |
| **I-S3** | 静态挂起 `interrupts == ()`；结果键 `"__interrupt__": ()`。 |
| **I-S4** | `InterruptResult` 仍 4 字段；`suspension_kind` / `static_ack` 只在 metadata / 账本。 |
| **I-S5** | `suspension_kind` 静态时 `next` 可空；`static_ack` 记录水位；不得仅以 `next` 非空判定。 |
| **I-S6** | 合法静态挂起不得被误判为 `no_pending_interrupt`。 |
| **I-S7** | 无新通道写入时同一断点不重复触发。 |
| **I-S8** | 优先级：递归 > before · 真异常 > 动态 > after > 完成。 |
| **I-S9** | fan-out N 个任务 before 全保留 / after 各一次；不合并、不伪造载荷。 |
| **I-S10** | fan-out 现场跨挂起逐项不变。 |
| **I-S11** | 低层入口非空静态字段 ⇒ 显式拒绝；签名 / 返回类型不变。 |
| **I-S12** | 裸 `"*"` = All（可执行节点）；`["*"]` / 裸非 `"*"` 字符串非法。 |
| **I-S13** | 静态恢复完成时**只写一次**完成快照（F-10），清 `suspension_kind` / `static_ack` / `next` / `fanout`；**不是**每轮末快照。 |
| **I-S14** | 空 `StateDict`（`input={}`）无新写入 ⇒ 与 `input=None` 同款传 `static_ack` ⇒ 同一断点不立即重挂。 |
| **I-S15** | `Command(resume=...)` 静态恢复 MUST 传 `static_ack`；`interrupt_before` 恢复首轮不得立即重挂。 |
