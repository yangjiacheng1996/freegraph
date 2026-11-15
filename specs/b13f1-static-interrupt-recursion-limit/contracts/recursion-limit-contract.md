# 契约 · B13F1 · `recursion_limit`

**Spec**: [../spec.md](../spec.md) · **Data Model**: [../data-model.md](../data-model.md) · **Date**: 2026-11-15
**上游版本**: `langgraph` **1.2.11**

> 本契约冻结 `recursion_limit` 的**载体 / 默认值 / 校验 / 计数 / 失败信号 / 交互**。
> 语义以 `spec.md` 为**唯一权威**；本文件若与 spec 冲突 ⇒ 以 spec 为准。

---

## §1 载体与优先级

### §1.1 规范载体

```python
run_graph(spec, input=None, *, ..., config={"recursion_limit": 3})
```

- **普通 dict** 是规范载体（与 `harness/demo/graph_core.py` 的调用形态逐字一致）；
- `RunConfig(recursion_limit=3)` 是**等价备用载体**；
- **MUST NOT** 新增显式 `recursion_limit=` 关键字（上游 1.2.11 也没有）。

### §1.2 优先级（从高到低）

| 顺序 | 来源 |
|---|---|
| 1 | dict 的 `"recursion_limit"` **或** `RunConfig.recursion_limit`（**互斥二选一**） |
| 2 | 既有 `max_steps`（L2 内部直控 · 缺省 10007） |
| 3 | `DEFAULT_RECURSION_LIMIT = 10007` |

> ⚠️ **dict 与 `RunConfig` 是互斥的替代载体**（一次运行只接受**一个** `config` 对象）⇒
> **不存在「同时提供两者」的路径**。`recursion_limit=None` ⇒ 视为未提供，落回下一层。

### §1.3 `config` 的接受形态

| 输入 | 处理 |
|---|---|
| `None` | `RunConfig()` |
| `RunConfig` | 原样 |
| `Mapping[str, Any]` | `RunConfig.from_dict(config, ignore_unknown=True)` |
| 其它 | `TypeError`（V-R3） |

---

## §2 默认值

| 项 | 值 |
|---|---|
| 常量 | `DEFAULT_RECURSION_LIMIT = 10007` |
| 来源 | 上游 `langgraph/_internal/_config.py:32` 的有效缺省 |
| 环境变量 | **不读**（含 `LANGGRAPH_DEFAULT_RECURSION_LIMIT`） |
| 文档 | MUST 写死 10007（spec / quickstart / docstring） |

> 上游可由环境变量覆盖；freegraph **硬编码**（宪法原则 I 的零环境变量红线 · X-4）。

---

## §3 校验（V-R1…V-R4）

| # | 规则 | 失败信号 | 消息要点 |
|---|---|---|---|
| **V-R1** | **非 `None` 值**且 `type(value) is not int`（含 `bool`） | `TypeError` | 点名 `recursion_limit` 与非法类型 |
| **V-R2** | `value < 1` | `ValueError` | 含 `at least 1` |
| **V-R3** | `config` 不是 `None` / `Mapping` / `RunConfig` | `TypeError` | 点名 `config` |
| **V-R4** | dict 的未知键 | **忽略** | 不报错（`ignore_unknown=True`） |

- 校验 MUST 在**入口立即**发生（哪怕本轮没有任务）；
- **`recursion_limit=None` MUST 跳过 V-R1 / V-R2**：它表示「未提供」⇒ 落回 `max_steps` /
  `DEFAULT_RECURSION_LIMIT`；**MUST NOT** 因 `None` 抛 `TypeError`；
- `bool` / 浮点被拒绝（**比上游更严** · X-7）；
- `0` / 负数 ⇒ `ValueError`；`"3"` / `1.5` / `True` ⇒ `TypeError`。

---

## §4 计数口径

| 事件 | 计 1 轮？ |
|---|---|
| 本轮执行了 ≥ 1 个标准任务 / fan-out 任务 | ✅（不论任务数） |
| 被 `interrupt_before` 拦住、未执行任何任务 | ❌ |
| `interrupt_after` 所在轮 | ✅ |
| 终轮「发现没有任务」的空轮 | ❌（`state.step` 口径） |
| fan-out 任务在下一轮执行 | ✅（B11F1 的 D-2） |
| 从静态挂起恢复 | ✅ **新的独立预算**（每次 `run_graph` 重新计数；`step` 不落盘 · B10F1） |

> ⚠️ **计数范围 = 单次 `run_graph`**：静态挂起恢复不累计、不回填步数 ⇒ 与 B10F1 的
> 「`SchedulerState.step` 不落盘」一致；`static_ack` 只做断点防重复，**不承载步数**。

**判定顺序**（`_run_graph_loop`）：

1. 触发判定；
2. 无任务 ⇒ 结束（空终轮不计）；
3. `state.step >= effective_limit` 且仍有任务 ⇒ `GraphRecursionError`；
4. 静态 before 检查；
5. 执行本轮；`state.step += 1`。

⇒ **恰好 `effective_limit` 轮执行**；第 `effective_limit + 1` 轮有待执行任务时抛错。

---

## §5 失败信号

```python
GraphRecursionError(
    recursion_limit=effective_limit,
    current_step=state.step,
)
```

- 类型 = L1 的 `freegraph.contracts.errors.GraphRecursionError`；
- 结构化属性：`.recursion_limit` / `.current_step`；
- 消息含「递归超限」语义与两个数值（B1F1 的英文摘要即满足）；
- **MUST NOT** 包装成 `RuntimeError` / 其它类型；
- **MUST NOT** 在超限时返回挂起态 / 静默停止。

---

## §6 与静态断点的交互

| 场景 | 结果 |
|---|---|
| 上限已达 **且** 静态 before 命中 | **递归超限优先**（`GraphRecursionError`） |
| 静态 before 挂起（未执行） | 该轮**不计**入上限 |
| 静态 after 挂起（已执行） | 该轮**计入**上限 |
| 从静态挂起恢复 | **每次 `run_graph` 独立预算**；`SchedulerState.step` 不落盘（B10F1 冻结面）⇒ 恢复后从本轮**重新计数**；`static_ack` 只负责防重复触发，**不承载步数** |
| fan-out 轮 | 计入（不绕过） |

---

## §7 不变量

| # | 不变量 |
|---|---|
| **I-R1** | 默认有效上限 = 10007；零环境变量。 |
| **I-R2** | 计数单位 = super-step 执行轮；N 个任务同轮 = 1 轮。 |
| **I-R3** | fan-out 轮计入；不绕过上限。 |
| **I-R4** | 超限抛 `GraphRecursionError`，结构化属性如实。 |
| **I-R5** | dict / RunConfig 互斥（一次一个） > max_steps > 默认；不新增显式关键字。 |
| **I-R6** | 0 / 负数 ⇒ `ValueError`；非 int / bool / 浮点 ⇒ `TypeError`；入口立即失败。 |
| **I-R7** | dict 未知键忽略；`recursion_limit` 非法值不忽略。 |
| **I-R8** | `GraphRecursionError` 原样传播，不被包装。 |
