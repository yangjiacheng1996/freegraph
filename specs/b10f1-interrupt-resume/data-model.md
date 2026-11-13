# Data Model · B10F1 · `interrupt()` + `resume`（HITL 中断与恢复闭环）

**Spec**: [`spec.md`](./spec.md)（**唯一权威**）· **Contract**: [`contracts/interrupt-resume-contract.md`](./contracts/interrupt-resume-contract.md) · **Research**: [`research.md`](./research.md)

> ⚠️ **本文件只描述「**数据**」**⇒ 不描述**行为**（行为归契约）⇒ ⇒ **零新增 L1 符号**
> （全部新增实体落 **L2** ⇒ 门禁 G7 / G8 / G16 / G19 恒绿）。

---

## 1. 实体总览（**归属与新增性**）

| # | 实体 | 归属 | 新增？ | 载体 |
|---|---|---|---|---|
| **EM-1** | `Interrupt` | **L1**（既有） | ❌ 只消费 | `contracts/types.py:99-118` · 2 字段（`.value` / `.id`） |
| **EM-2** | `GraphInterrupt` | **L1**（既有） | ❌ 只消费 | `contracts/errors.py:102-129` · `.payload` = `tuple[Interrupt, ...]` |
| **EM-3** | `Command` | **L1**（既有） | ❌ 只消费 | `contracts/types.py:33-83` · 4 槽位 |
| **EM-4** | `StateSnapshot` | **L1**（既有） | ❌ 只消费 | `contracts/types.py:260-311` · 8 字段 |
| **EM-5** | `RunConfig` | **L1**（既有） | ❌ 只消费 | `contracts/types.py:151-256` · 9 字段 |
| **EM-6** | `InterruptResult` | **L2** | ✅ **新增** | `runtime/superstep.py` · **4 字段** |
| **EM-7** | `InterruptError` | **L2** | ✅ **新增** | `runtime/errors.py` · `.reason`（**封闭 5 码**） |
| **EM-8** | **任务现场**（task scratchpad） | **L2 私有** | ✅ **新增** | `runtime/_interrupt.py` · **4 字段** |
| **EM-9** | **运行级现场表** | **L2 私有** | ✅ **新增** | `runtime/_interrupt.py` · `{节点名: 任务现场}` |
| **EM-10** | **调度账本** | **L2**（既有载体 + 新增两个方法） | ➕ **只增方法** | `runtime/superstep.py` 的 `SchedulerState` |
| **EM-11** | **pending write** | **协议载荷**（L4 侧实现） | ➕ **载荷形状** | `(task_id, channel, value)` 三元组 |

---

## 2. 字段规格（**逐字冻结**）

### EM-6 · `InterruptResult`（**L2 新增** · 挂起态的结果对象）

```python
@dataclass(frozen=True, slots=True)
class InterruptResult:
    state: dict[str, Any]          # 合并后的稀疏状态（含中断前已产生的写入）
    interrupts: tuple[Interrupt, ...]  # 中断集合（= 被接住的 GraphInterrupt.args[0]）
    executed: tuple[str, ...]      # 已启动过的节点名（含被中断的 · 节点名序）
    steps: int                     # 实际跑过的轮数（如实计 · 含被中断的那轮 · 不含空轮）
```

| 字段 | 约束 | 依据 |
|---|---|---|
| `state` | **稀疏**（只含「当前有值」的通道 key）· **MUST NOT** 含 `__interrupt__` | C4 · B12F1 裁定 25 ③ |
| `interrupts` | **元组**（非 list）· 元素 = `Interrupt`（**非**嵌套元组） | spec 裁定 1 · B12F1 裁定 7 |
| `executed` | **节点名序**（**升序**）· **含**被中断的节点 · **不含**被取消的（从未启动）· ⚠️ **与 `SuperStepResult.executed` 同序**（同一口径 ⇒ 两个结果对象**可直接比较**） | B12F1 裁定 4 / 22 |
| `steps` | **≥ 1** · **含**被中断的那一轮 · **不含**那个「发现没任务了」的空轮 ⇒ ⚠️ **与 `SuperStepResult.steps` 计数口径「刻意不同」**（后者**含**空轮 · B7F1 冻结面）⇒ ⇒ 同一张图「挂起 N 轮」与「跑完 N+1 轮」⇒ ⇒ **数值不可直接比较**（**2026-11-13 分析轮拍板**）| B12F1 裁定 24（**如实计**） |

⚠️ **MUST NOT** 有第 5 个字段（澄清轮 **Q1**）⇒ ⇒ **MUST NOT** 带 `node_writes`。
⚠️ **方法** `as_result_dict() -> dict[str, Any]` = `{**state, "__interrupt__": interrupts}`。

### EM-7 · `InterruptError`（**L2 新增** · 失败信号）

```python
class InterruptError(FreegraphError):
    reason: str      # 封闭取值域（见下）
```

| 项 | 约束 |
|---|---|
| 继承 | **仅** `FreegraphError` ⇒ **MUST NOT** 继承 `ValueError`（用户的 `except ValueError` **不**误吞） |
| `.reason` | **封闭取值域**：`checkpointer_required` / `resume_value_required` / `ambiguous_resume` / `no_pending_interrupt` / `not_in_run` |
| 其他字段 | **MUST NOT** 携带会话标识 / 待恢复中断的 id 列表等**上下文**（澄清轮 **Q2**）⇒ ⇒ 异常**只**回答「**为什么失败**」 |
| 消息 | **英文**摘要 · **MUST** 点名失败原因（要点与上游逐字同款） |
| 导出面 | ⚠️ **MUST** 写进 `src/freegraph/runtime/errors.py` 的 `__all__`（**7 → 8**）⇒ ⇒ 与 `tasks.md` **T012-a** 第 ④ 处的**期望集合**（**7 + `InterruptError`**）**逐字对齐**（**否则该断言不可判定** · **2026-11-13 分析轮第二轮**）|

### EM-8 · **任务现场**（**L2 私有** · `runtime/_interrupt.py`）

```python
@dataclass
class _TaskScratchpad:
    resume: list[Any]          # 该节点已提供的恢复值（按节点内顺序）
    index: int                 # 该节点内第几次调用 interrupt()（原子计数）
    existing: Interrupt | None # 该节点先前挂起时的中断载荷（恢复时读回 ⇒ 复用其 .id）
    namespace: str | None      # 命名空间 f"{节点名}:{uuid4().hex}"（首次挂起时生成）
```

| 字段 | 约束 |
|---|---|
| `resume` | **列表**（上游同款 · `_algo.py:1301-1308`）· 空列表 = 无恢复值 |
| `index` | **从 0 起** · 每个节点**各自**计数（**不**跨节点） |
| `existing` | 恢复时 = pending writes 里那个 `Interrupt`（**原样**）⇒ ⇒ 复用其 `.id` ⇒ **跨恢复稳定** |
| `namespace` | **首次挂起时**生成（`uuid4().hex`）⇒ **不落盘**（恢复时靠 `existing.id` ⇒ **零新增持久化字段**）· ⚠️ **术语对齐（2026-11-13 分析轮）**：spec 裁定 6 / FR-003 说的「**任务标识**」**就是**本字段（`namespace`）—— 指「该节点本次『挂起 → 恢复』循环内的**随机 uuid4**」⇒ ⇒ 两者**同义**、**不是**两个东西 ⇒ ⇒ 引用时 MUST 写全（spec 用「任务标识」· data-model 用 `namespace`）|

⚠️ **每个节点一份** ⇒ ⇒ **不共享** ⇒ ⇒ 并发安全（**节点在各自的工作线程里**执行）。

### EM-9 · **运行级现场表**（**L2 私有**）

```python
{节点名: _TaskScratchpad}
```

⚠️ 由 `run_graph` 在**整次运行**期间设置 ⇒ ⇒ 任务现场**按节点名**取用 ⇒ ⇒
**无**跨层查找 ⇒ ⇒ 并发安全。

### EM-10 · **调度账本**（**既有载体 + 只增两个方法**）

| 既有字段（L2 · B7F1 冻结） | 编码（`.scheduler`） | 还原 |
|---|---|---|
| `versions_seen: dict[str, dict[tuple[str, str], int]]` | `{节点名: [[kind, ident, 版本], ...]}` | `{(kind, ident): 版本}` |
| `channel_versions: dict[str, int]` | **原样** | 原样 |
| `node_versions: dict[str, int]` | **原样** | 原样 |
| `dynamic_edges: dict[str, tuple[str, ...]]` | `{节点名: [目标, ...]}` | `tuple(目标, ...)` |
| `step: int` | **不落盘** | 重新计数 |
| `channels: dict[str, Channel]` | **不落盘** | `Channel.from_checkpoint(...)` 重建 |

⚠️ **只增方法**（`to_checkpoint` / `from_checkpoint`）⇒ ⇒ `SchedulerState()` 的**构造签名逐字不变**
⇒ ⇒ **B7F1 冻结面零破坏**（B12F1 增 `dynamic_edges` 时同款 · 裁定 12 / R-3 ①）。
⚠️ `versions_seen` 的 key 是**二元组** ⇒ JSON 不可直接序列化 ⇒ ⇒ **必须**用列表编码。

### EM-11 · **pending write**（**载荷形状**）

| 元素 | 类型 | 语义 |
|---|---|---|
| `task_id` | `str` | **节点名**（freegraph 取舍 · 更可读 · 上游用任务路径哈希） |
| `channel` | `str` | `__interrupt__` / `__resume__`（**上游同款** · `_internal/_constants.py:9` / `:11`） |
| `value` | `Any` | `__interrupt__` ⇒ 中断载荷**元组** · `__resume__` ⇒ 恢复值**列表** |

---

## 3. 关系（**谁引用谁**）

```
run_graph(spec, input, checkpointer=…, config=…)
   │
   ├─ Checkpointer（**L1 协议**）           ← L4 实现（B14F1）· L2 **只**依赖协议（ARCH-1）
   │     └─ get_tuple(config) → .snapshot / .pending_writes / .scheduler
   │
   ├─ SchedulerState（调度账本）            ← B7F1 既有 · 只增两个方法
   │     └─ Channel 实例（from_checkpoint）  ← B5F1 既有
   │
   ├─ 运行级现场表 {节点名: 任务现场}       ← EM-9（L2 私有）
   │     └─ 任务现场（resume / index / existing / namespace）   ← EM-8（L2 私有）
   │
   └─ 返回
         ├─ SuperStepResult（完成）          ← B7F1 既有 · 四字段零改动
         └─ InterruptResult（挂起）           ← EM-6（L2 新增）
               └─ as_result_dict() → {**state, "__interrupt__": interrupts}
                     └─ Interrupt（元素）      ← EM-1（L1 既有）
```

⚠️ **依赖方向**（门禁 **G25** · ARCH-1）：`L2 → L1` **单向** ⇒ ⇒ L2 **MUST NOT** import L4 / L5。
⚠️ **门面 → L2** 是 ARCH-1 的**唯一例外**（门面**可** import L1–L3）⇒ ⇒ ⚠️ **PR-4 回修**（初版写的
「**惰性** import L2 ⇒ 门面的**模块加载面**在 import 时**不变**」**已作废** —— 门禁 **G25** 扫 **AST** ⇒
**函数体内的惰性 import 同样判红**）⇒ ⇒ **唯一合法形态** = 机制住在 `runtime/_interrupt.py`（**L2 目录
条目内**）· 门面 `src/freegraph/graph.py` 用**模块级** `from .runtime._interrupt import interrupt`
（`facade-L1-L3` 例外）⇒ ⇒ ⇒ 门面的**模块加载面**会**多出 L2**（**不**含 L4 / L5 ⇒ 门禁 **G18** 恒绿）
⇒ ⇒ 顶层包仍**惰性**（G1 / ARCH-2 恒绿）。

---

## 4. 状态迁移（**一次运行的两种结束方式**）

> ⚠️ **编号前缀（2026-11-13 分析轮回修）**：本表的**状态迁移**编号一律用 **`SM-`** 前缀
> （`SM-1`…`SM-7`）⇒ ⇒ **与** spec §5 / plan / tasks 的「**破冻结面回溯修订清单 T-1**」**区分**
> （后者是**另一样东西** ⇒ ⇒ 原先两处**同名** ⇒ ⇒ 引用歧义）⇒ ⇒ **引用时 MUST 写全**。

```
                 ┌──────────────────────────────────────────┐
                 │  首 次 运 行（input = StateDict / None）  │
                 └───────────────┬──────────────────────────┘
                                 ▼
                    ┌───────────────────────────┐
        ┌──────────►│  第 1 轮 super-step        │◄──────────────┐
        │           │  （触发判定 → 执行 → 合并） │                │
        │           └───────┬───────────┬───────┘                │
        │                   │           │                        │
        │      有真异常      │           │  有中断                  │
        │                   ▼           ▼                        │
        │   ┌───────────────┐   ┌──────────────────┐              │
        │   │ 抛出真异常     │   │ **挂起**           │              │
        │   │ （中断元组丢弃）│   │ InterruptResult    │              │
        │   └───────────────┘   └────────┬─────────┘              │
        │                                │                        │
        │                    Command(resume=…)                     │
        │                                ▼                        │
        │                    ┌────────────────────┐               │
        │                    │ 读快照 + 待写入      │               │
        │                    │ 重建通道 + 调度账本  │               │
        │                    │ 显式跑 snapshot.next │               │
        │                    └────────┬───────────┘               │
        │                             ▼                           │
        └───────────────── 第 2 轮 super-step ────────────────────┘
                                  （触发判定与首次运行同款）
```

| 迁移 | 触发 | 结果 |
|---|---|---|
| **SM-1** 首次运行 | `input` 不是 `Command` | 走多轮循环 ⇒ 完成 ⇒ `SuperStepResult`；⚠️ **会话连续**（挂了 checkpointer 且该 `thread_id` **已有历史快照**）⇒ MUST **先读 `.scheduler`** 重建调度状态（**续跑** · **上游同款** · **实测 E-26**）⇒ ⇒ **两种输入形态行为不同**：**`input = None`** ⇒ **不**写通道 ⇒ **只有被中断的节点**重跑 ⇒ `.id` **不变**；**`input = StateDict`** ⇒ 先读 `.snapshot.values`、再把 `input` **按通道写入**叠加上去（**上游同款** · `langgraph/pregel/_loop.py:975-985`）⇒ ⇒ **写通道 ⇒ 版本推进 ⇒ 订阅节点重新触发** ⇒ 被触及的节点**重跑** ⇒ `.id` **可变** ⇒ ⇒ **不**消费 `__resume__` ⇒ ⇒ **不**触发恢复 |
| **SM-2** 挂起 | 某轮出现 `GraphInterrupt`（且**无**真异常） | **不再进入下一轮** ⇒ `InterruptResult`（`steps` 如实计） |
| **SM-3** 真异常 | 某轮出现真异常（**优先于**中断） | **抛出**原对象 ⇒ 中断元组**丢弃** |
| **SM-4** 恢复 | `input` 是 `Command(resume=…)` | 读快照 → 重建 → **显式**跑 `next` ⇒ 继续循环 ⇒ 完成 ⇒ `SuperStepResult` |
| **SM-5** 恢复后再挂起 | 恢复后节点在**下一个** `interrupt()` 处**无**恢复值 | **再次挂起** ⇒ `InterruptResult`（**新的**载荷 · **同一个** `.id`） |
| **SM-6** 恢复失败 | 未挂 checkpointer / 未提供恢复值 / 多挂起未按 id / 无挂起中断 | 抛 `InterruptError`（**五个** reason 之一 —— `checkpointer_required` / `resume_value_required` / `ambiguous_resume` / `no_pending_interrupt` / `not_in_run`；⚠️ 「未挂 checkpointer」与「未提供恢复值」**交叠**时**后者优先** · 上游同款 · **实测 E-25a / E-25b**）|
| **SM-7** 运行之外调用 | `interrupt()` 在**图运行之外** | 抛 `InterruptError(reason="not_in_run")` |

---

## 5. 校验规则（**逐条可判定**）

| # | 规则 | 判定 |
|---|---|---|
| **V-1** | `InterruptResult` 的**字段数 == 4** | `dataclasses.fields(...)` |
| **V-2** | `InterruptResult.state` **不含** `__interrupt__` | key 集合判定 |
| **V-3** | `InterruptResult.interrupts` 是**元组**且元素是 `Interrupt` | `isinstance` 逐元素 |
| **V-4** | `InterruptResult.executed` **升序**且**含**被中断的节点 · 且与 `SuperStepResult.executed`（**节点名序**）**同排序口径** | ⚠️ 中断轮**不**产出 `SuperStepResult`（FR-005 / 裁定 2）⇒ ⇒ **无对照物** ⇒ ⇒ 判据形态 = ① **逐字等于期望的节点名序**（如 `("a","b")`）② 它**是升序的** ⇒ ⇒ **不**断言「两个对象逐字相等」（**2026-11-13 分析轮回修**）|
| **V-5** | `InterruptResult.steps >= 1` ⇒ ⇒ **且**与 `SuperStepResult.steps`（**含**空轮）**口径不同 · 数值不可直接比较** ⇒ ⇒ ⚠️ **MUST NOT** 对两者做**算术比较**（**不**断言「挂起 N 轮 ⇒ 跑完 N+1 轮」—— 那依赖两套口径的巧合差值 · **2026-11-13 分析轮第二轮**）| 数值 |
| **V-6** | `.id` 匹配 `^[0-9a-f]{32}$` | 正则 |
| **V-7** | 同一节点同一轮的多个 `.id` **逐字相同** | 逐字相等 |
| **V-8** | 恢复时的 `.id` 与先前交给调用方的**逐字相同** | 逐字相等（**F-1**） |
| **V-9** | `InterruptError.reason` ∈ **封闭 5 码** | 集合判定 |
| **V-10** | `InterruptError` **不**是 `ValueError` 的子类 | `issubclass(..., ValueError) is False` |
| **V-11** | `SchedulerState()` 的**构造签名**逐字不变 | `inspect.signature` 快照 |
| **V-12** | `.scheduler` 是 **JSON 可序列化**的纯数据 | `json.dumps` / `json.loads` 往返 |
| **V-13** | `pending_writes` 的元素是**三元组** | `len(...) == 3` 逐元素 |
| **V-14** | 保留通道名 ∈ {`__interrupt__`, `__resume__`} | 集合判定 |
