<!-- authority: yes -->

# 流式契约（Stream Contract）—— B8F2 的**唯一权威**

**Feature**: `B8F2` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**核实环境**: CPython **3.11.16** · 上游 `langgraph` **1.2.11**（核实于 2026-11-19）

> 本文件是「流式长什么样、怎么用」的**唯一权威**（沿用 B3F1 / B5F1 / B5F2 / B7F1 / B8F1
> 的机器可读 Markdown + `<!-- authority: yes -->` 先例）。
> **spec** 讲「**要什么**」· 本文件讲「**是什么**」· `upstream-parity.md` 讲「**证据**」。
> ⚠️ 本文件 MUST NOT 被测试**解析**；测试**断言行为**。

---

## 1. 签名与载体（**逐字冻结**）

### 1.1 L1 协议（`CompiledGraph.stream`）

```python
def stream(
    self,
    input: StateDict,
    config: RunConfig | Mapping[str, Any] | None = None,
    *,
    stream_mode: str | Sequence[str] | None = None,
) -> Iterator[dict[str, Any]]: ...
```

- **参数名** `input` / `config` / `stream_mode` **冻结**（B2F1 占位名）。
- **默认档**：`stream_mode=None` ⇒ **`"updates"`**（上游 `CompiledStateGraph` 同款 ·
  `langgraph/graph/state.py:1357`）；`None` 与省略等价，不报错。
- **返回类别** = `Iterator[dict[str, Any]]`（每个元素 = 四键信封）。
- **`config` 注解放宽**为 `RunConfig | Mapping[str, Any] | None`（T-3 · B7F3 D-5）；
  普通映射 MUST **原样**交给 L2（MUST NOT 翻译成 `RunConfig`）。
- **`input` 注解**沿用 `StateDict`；`Command` / `None` 的恢复路径**不属本 feature**
  （`Command` ⇒ 第一次迭代抛 `TypeError`；`None` 视为「无输入写入」）。

### 1.2 L2 私有落点

| 文件 | 角色 | 导出 |
|---|---|---|
| `src/freegraph/runtime/_stream_context.py` | contextvar：`StreamWriter` / `CustomSink` / `RoundCapture` / 当前 TaskId / **`_STREAM_RUN_ID` / `_STREAM_THREAD_ID`** | **私有**（`__all__ = []`） |
| `src/freegraph/runtime/_stream.py` | `StreamSession`：初始化 / `bind_run` / contextvar 绑定（含 run_id / thread_id）/ 初始稀疏状态 | **私有**（`__all__ = []`） |
| `src/freegraph/runtime/superstep.py` | `_run_round` 记录 `PregelTask` + 中断 capture；`SuperStepResult.tasks`；**私有 `_run_single_step` / `_stream_tick`**（与 `run_super_step` 共用单轮实现） | 既有公开 **9** 符号（`SUPERSTEP_EXPORT_SYMBOLS`；私有助手不进 `__all__`） |
| `src/freegraph/runtime/_concurrency.py` | 每任务 `copy_context()` | 既有私有 |

- **零新增公开 L2 符号**：`freegraph.runtime.__all__` 仍 **23**。
- **MUST NOT** 改动 `run_super_step` / `run_super_steps` 的签名。

---

## 2. 事件信封（**唯一形态**）

```python
{
    "stream_mode": str,        # 七种之一
    "payload": Any,            # 该档载荷
    "run_id": str,             # uuid4().hex，每次 stream() 一个
    "thread_id": str | None,   # 会话标识
}
```

| 规则 | 内容 |
|---|---|
| 键集 | **恰为四键**（`set(e) == {...}`） |
| id | 同一 `stream()` 的全部事件共享 `run_id`；跨流不同 |
| `thread_id` | `configurable["thread_id"]` 优先于顶层 `thread_id`；未提供 ⇒ `None` |
| `RunConfig.run_id` | **忽略**（事件 `run_id` 恒由运行时生成） |
| 运行标识载体 | `StreamSession` 把 `run_id` / `thread_id` 绑定到 L2 私有 contextvar `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`；B18F1 / B19F1 的 span MUST 读取同一对值（D-3） |
| 禁止 | MUST NOT 在 `payload` 里再挂 `run_id` / `thread_id` |
| 多 mode | 同一信封，`stream_mode` 字段区分（**不走** `(mode, payload)` 元组） |

---

## 3. 七种 mode 的 v1 语义

| mode | 产出 | 载荷 | 粒度 / 顺序 |
|---|---|---|---|
| `values` | 初始状态 + 每个完成的 super-step | 完整状态 `dict` | 初始 1 条 + 每步 1 条 |
| `updates` | 每个完成的 task | `{节点名: {通道: 值 \| 元组}}` | 每 task 1 条 |
| `checkpoints` | **空序列** | —— | 0 条（B14F1） |
| `tasks` | 每个完成的 task（含被中断） | `PregelTask` | 每 task 1 条 |
| `debug` | 每个 `tasks` 事件的包裹 | `{step, timestamp, type, payload}` | 每 task 1 条 |
| `messages` | **空序列** | —— | 0 条（freechain） |
| `custom` | 每次 `StreamWriter` 写入 | 用户传入的对象（原样） | TaskId 序 + 任务内写入序 |

### 3.1 `values`

- 归一 = `_full_state`（`src/freegraph/_stategraph.py:235-267`）· **L2 MUST NOT** 复制。
- 键集 == schema 全集（路由通道不进）· 无值 key 填 `None` · 归约型类型空值保留。
- 中断收尾：`payload` 含 `"__interrupt__"`（元组）。
- 终态判据：同图 / 同输入 / 无静态断点 / 无会话历史 ⇒ 最后一条 `payload` == `invoke()` 终态。

### 3.2 `updates`

- 载荷 = `{节点名: {通道 key: 值 | 值的元组}}`。
- 同一 task 对同一通道多次写入 ⇒ **按写入顺序的元组**。
- 全部 `updates` 按**通道归约语义**合并后 == `invoke()` 终态（限定同 3.1）。
- 中断收尾：额外一条 `{"__interrupt__": <元组>}`。

### 3.3 `tasks`

- `payload` = `freegraph.contracts.PregelTask` **实例**（七字段）。
- 每个**已完成** task 一条；**被中断的 task** 也补发一条（`error=None` ·
  `interrupts` 非空 · `result` = 已发生写入）。
- **失败 task 不产出**（失败轮不返回 `SuperStepResult`；已发生 `custom` 先 flush）。
- `SuperStepResult.tasks: tuple[PregelTask, ...]`（末尾 · 缺省 `()`）；
  单轮 = 本轮 · 多轮 = 累计；**中断轮不进 `SuperStepResult.tasks`**。

`PregelTask` 字段语义：

| 字段 | 语义 |
|---|---|
| `id` | 运行内唯一 `str`；生成方式不冻结；不跨运行比较 |
| `name` | 节点名（fan-out = 目标名） |
| `path` | 标准 `(节点名,)`；fan-out `(目标名, TaskId:int)` |
| `error` | 原异常对象；成功 / 挂起 ⇒ `None` |
| `interrupts` | `tuple[Interrupt, ...]`；无中断 ⇒ `()` |
| `state` | v1 **恒 `None`** |
| `result` | 与 `updates` 同形；无写 ⇒ `{}` |

### 3.4 `debug`

```python
{"step": int, "timestamp": str, "type": "task_result", "payload": PregelTask}
```

- `step` = **1 起**的 super-step 序号（同轮多 task 相同；**进入每轮时递增**，中断轮同样占一个序号）。
- `timestamp` = UTC ISO-8601（含 `+00:00` 时区偏移 · `datetime.now(timezone.utc).isoformat()`；MUST 可被 `datetime.fromisoformat` 解析）。
- v1 **无** checkpoint 类 debug 事件。
- 中断 task 同样补发一条。

### 3.5 `custom`

- 来源 = `get_stream_writer()(value)` 或节点签名的 `writer(value)`（关键字注入）；`value` **原样**产出。
- 顺序 = TaskId 升序 + 任务内写入序。
- **时机 = 轮末批量**（每轮 L2 单轮入口结束后；不是逐写即时）⇒ **P-23 / X-6**。
- 中断 / 失败：本轮已发生的先产出，再收尾 / 重抛。
- 无流：`get_stream_writer()` 返回 no-op。

### 3.6 `checkpoints` / `messages`

- 两者 v1 **恒为空序列**（零事件、零异常）。
- `checkpoints` 真实源归 **B14F1**；`messages` 的 LangChain 抽取归 **freechain**。
- MUST NOT 伪造事件；MUST NOT 把 `SuperStepResult.state` 伪装成 checkpoint。

---

## 4. 生命周期与顺序

```text
stream() 调用
  ├─ 解析 stream_mode（None ⇒ "updates"；非法 / 空 ⇒ 立即抛）
  └─ 返回惰性迭代器（零执行）
第一次 next()
  ├─ 校验 input（Command / 非法类型 ⇒ TypeError；None = 无输入写入）
  ├─ 会话初始化（输入写入 / bind_run / contextvar / run_id / thread_id）
  ├─ values 请求 ? → 初始 values 事件
  └─ 轮循环
        _stream_tick(spec, state, max_steps=..., max_concurrency=..., route_config=raw_config)
        │  ← 复用 _determine_triggers；触发集非空且 state.step >= max_steps ⇒ GraphRecursionError（执行前）
        │  ← 触发集为空 ⇒ 返回 None ⇒ 结束
        ├─ 成功且 executed 非空 → custom → updates → tasks → debug → values
        ├─ 收敛（返回 None）→ 结束
        ├─ GraphInterrupt → custom → updates(__interrupt__) → tasks → debug → values(__interrupt__) → 结束
        └─ 其他异常 → custom（已发生）→ 重抛原异常
finally：复原 contextvar token；零悬挂线程
```

- **跨档顺序固定**：`custom → updates → tasks → debug → values`（同轮内）。
- **惰性**：调用 `stream()` 不执行图；不迭代 ⇒ 零执行。
- **提前停止**：`close()` / 停止迭代 ⇒ 只执行到已完成的轮次；零悬挂线程；不吞异常。
- **递归上限**：轮循环 MUST 复用 B13F1 的 `recursion_limit` / `max_steps` 解析口径
  （`resolve_limit`）；`_stream_tick` MUST 在**执行前**判「触发集非空 且
  `state.step >= max_steps` ⇒ `GraphRecursionError`」⇒ **恰好收敛于上限不误抛**、
  **MUST NOT 多跑一轮**（零新增错误类型）。
- **双参路由**：`_stream_tick` 的 `route_config` MUST 是用户交给 `stream()` 的**原始**
  `config`（`RunConfig` / 普通映射 / `None` · **逐字**）⇒ 与 `invoke` 的第二参同口径。
- **静态断点**：`interrupt_before` / `interrupt_after` 在 stream v1 **不支持**；复用 V-26 的
  `ValueError`（首次迭代抛出，点名「静态断点只在图级 `run_graph` 生效」）⇒ MUST NOT 静默忽略。
- **checkpointer**：`StreamSession` MUST **忽略** `checkpointer`（不读/写快照、不触发恢复）；
  其存在 MUST NOT 改变七档语义。
- **并发度**：`max_concurrency` 由流式会话从 `config`（`RunConfig.max_concurrency` 或普通
  映射同名字段）解析后传给 L2 单轮入口；`stream()` **不新增**该关键字。
- **运行标识载体**：`run_id` / `thread_id` 由 `StreamSession` 绑定 L2 私有 contextvar
  `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`，供 B18F1 / B19F1 读取。

---

## 5. `StreamWriter`（contextvar + `copy_context()`）

| 项 | 契约 |
|---|---|
| 类型 | `StreamWriter = Callable[[Any], None]`（L1 · `contracts/types.py`） |
| 公开入口 | `freegraph.graph.get_stream_writer()`（门面 7→8） |
| 无流 | 返回 no-op（不抛） |
| 传播 | `run_tasks_concurrently` 的**每任务** `copy_context()`（`_executor.py:64` 的 `copy_context()` / `:71` 的 `ctx.run`；async 见 `:164`） |
| 线程安全 | 写入 MUST 线程安全；按 TaskId + 写入序确定排序 |
| 产出时机 | **轮末批量**（每轮 L2 单轮入口结束后）⇒ P-23 / X-6 |
| 禁止 | MUST NOT 另立显式传参载体（原则 XII）· MUST NOT 塞进 `_TaskOutcome` |
| 关键字注入 | **交付**（FR-036）：节点签名声明参数名 **`writer`**（`POSITIONAL_OR_KEYWORD` / `KEYWORD_ONLY`；注解 ∈ `StreamWriter` / `"StreamWriter"` / 空）⇒ 以**关键字**注入当前 `get_stream_writer()`；`**kwargs` / 其它参数名 / 注解不匹配 ⇒ 不注入；无流时注入 no-op。⚠️ `stream_writer` 是 **runtime key**，不是参数名（上游 `_runnable.py:183-188` · E-17）。 |
| 运行标识载体 | `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`（L2 私有 contextvar）· 供 B18F1 / B19F1 读取（FR-027 / D-3） |

---

## 6. 中断与失败

### 6.1 中断（`GraphInterrupt`）

- `tasks` / `debug`：为被中断 task 补发一条（`interrupts` 非空）。
- `custom`：本轮已记录的先产出。
- `values`：收尾 `payload` 含 `"__interrupt__"`（元组）。
- `updates`：收尾 `payload = {"__interrupt__": <元组>}`。
- 迭代器**正常结束**（不把 `GraphInterrupt` 抛给消费者）。
- L2 私有生成器/会话 MUST 捕获本轮 task 定格（即使 L2 单轮入口抛异常）；
  **MUST NOT** 改 `SuperStepResult` / `InterruptResult` 的字段。

### 6.2 失败（真实异常）

- 已发生的 `custom` 先产出。
- 失败轮的 `values` / `updates` / `tasks` / `debug` **不产出**。
- 原异常 **原类型 + 原消息**重抛（不包装 / 不吞）。
- 之前成功的轮次事件不回撤。

---

## 7. 校验规则（VS-1…VS-11）

| # | 场景 | 失败信号 |
|---|---|---|
| VS-1 | `stream_mode` 非 `str` / 非 `Sequence[str]` / 非 `None` | `TypeError` |
| VS-2 | 值不在七种闭集（或空序列） | `ValueError`（点名 + 列合法值） |
| VS-2b | `stream_mode=None` | 解析为 `"updates"`（不失败） |
| VS-3 | `stream_mode=[]` | `ValueError` |
| VS-4 | 重复 mode | 去重保序（不失败） |
| VS-5 | `input` 是 `Command` | `TypeError`（点名恢复路径归 B14F1 / B15F1） |
| VS-6 | `input` 非 `dict` / `None` | `TypeError` |
| VS-7 | `config` 非法类型 | `TypeError`（L2 `resolve_config`） |
| VS-8 | `RunConfig.run_id` 非空 | **忽略**（不失败） |
| VS-9 | 无流 `get_stream_writer()` | no-op（不失败） |
| VS-10 | 失败 / 中断 | 见 §6 |
| VS-11 | `input=None` | 允许 = 无输入写入；`Command` ⇒ `TypeError` |

---

## 8. 不变量（IS-1…IS-25）

| # | 不变量 |
|---|---|
| IS-1 | 每条事件键集恰为四键 |
| IS-2 | 同一流共享 `run_id`；跨流不同 |
| IS-3 | `thread_id` 与 `config` 一致 |
| IS-4 | `values` 最后一条 `payload` == `invoke` 终态（限定） |
| IS-5 | `updates` 归约合并 == `invoke` 终态（限定） |
| IS-6 | `tasks` 每条是 `PregelTask`；每完成 task 一条 |
| IS-7 | `debug` 键集 + `type == "task_result"` + 1 起 step（含中断轮）+ `timestamp` 可被 `datetime.fromisoformat` 解析且为 UTC |
| IS-8 | `custom` 轮末批量产出，顺序 = TaskId 升序 + 任务内写入序（P-23 / X-6） |
| IS-9 | `checkpoints` / `messages` 长度 == 0 且不抛 |
| IS-10 | 非法 mode ⇒ 调用时 `ValueError` |
| IS-11 | 惰性：不迭代 ⇒ 零执行 |
| IS-12 | 提前停止 ⇒ 零悬挂线程 |
| IS-13 | 中断 ⇒ task 补发 + `__interrupt__` + 正常结束 |
| IS-14 | 失败 ⇒ custom 先出 + 原异常重抛 + 失败轮无 values/updates/tasks/debug |
| IS-15 | `run_super_step` / `run_super_steps` 签名不变 |
| IS-16 | 导出面 == 8 / 22 / 23 |
| IS-17 | `SuperStepResult` = 原 4 + `tasks`；`InterruptResult` 仍 4 |
| IS-18 | `vars(compiled)` == 11 键 |
| IS-19 | 零新增依赖 / 零出站 / 零环境变量 |
| IS-20 | 轮循环超 `recursion_limit` **且触发集非空** ⇒ `GraphRecursionError`（**执行前**）；恰好收敛于上限 ⇒ 不抛、不多跑一轮 |
| IS-21 | `max_concurrency` 从 `config`（`RunConfig.max_concurrency` 或普通映射同名字段）解析并传给 L2 单轮入口；`stream()` 不新增该关键字 |
| IS-22 | 声明 `writer` 的节点在 `stream` 中得到注入；`stream_writer` 不注入；`invoke` 中为 no-op |
| IS-23 | `input=None` = 无输入写入；`Command` 在**首次迭代**被拒绝（调用时不报错） |
| IS-24 | 条件边图在 `stream` 下的路由目标序列与 `invoke` 一致（复用同一实现）；**双参路由第二参 == 原始 `config`** |
| IS-25 | `_STREAM_RUN_ID` / `_STREAM_THREAD_ID` 与本流全部事件的 `run_id` / `thread_id` 一致；B18F1 / B19F1 读取同一对值 |

---

## 9. 破冻结面与回溯修订（T-1…T-5）

| # | 冻结面 | 回溯修订 | 处置 |
|---|---|---|---|
| T-1 | B7F1 `SuperStepResult` 构造签名 | `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1/§5.3 + `spec.md` + `superstep.py:348-377` | **拆分而不删**：原 4 字段保留 + 追加 `tasks` |
| T-2 | B12F1「四字段零改动」 | `specs/b12f1-concurrency-errors/spec.md` 裁定 25 ② / FR-013 | **只补注记**；原描述不改写 |
| T-3 | L1 + L3 `stream` 的 `config` 注解 + `stream_mode` 默认值 | `src/freegraph/contracts/protocols.py:278-286` + `src/freegraph/_stategraph.py:357-365`（concrete 由 T022 落地，T064 只复核）+ B2F1 `public-api.md` / `specs/b2f1-contracts-protocols/data-model.md` §2.5 + **B7F2 `specs/b7f2-compile/contracts/compile-contract.md` §2.4 / `specs/b7f2-compile/data-model.md` §2.3 / `specs/b7f2-compile/plan.md` Phase A / `specs/b7f2-compile/tasks.md` T006（只补注记）** + `README.md`（由 T068 执行） | **拆分而不删**：原 `RunConfig \| None` 为子集；显式 `"values"` 仍合法；默认改为 `None ⇒ "updates"`；B7F2 原描述保留 |
| T-4 | B10F1 契约 §3 + `_interrupt.py` docstring | `specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md` §3 + `src/freegraph/runtime/_interrupt.py:15-27` | **只补注记**：线程池现继承 contextvars |
| T-5 | B2F2 门面 7 + B2F1 契约清单 21 | `specs/b2f2-public-api-facade/contracts/facade-api.md` §0 + `public-api-snapshot.txt` + `specs/b2f1-contracts-protocols/contracts/public-api.md` §0 + `tests/contracts/test_architecture.py` G7 解析器 + `README.md`（由 T068 执行）+ 源码模块 docstring（`contracts/types.py` / `contracts/__init__.py` / `graph.py` / `_stategraph.py` · 只补计数/注记） | **拆分而不删**：原 7 / 21 保留 + 追加 8 / 22 |

> 追认次数 == **1**（T-1…T-5 共用）· 追认文字 MUST 落
> `harness/verification/B8F2/manual-verification.md`。

---

## 10. 边界（本契约不规定的事）

- `astream` / 异步流（v2）。
- trace span 生产 / `TraceSink` 接入（B18F1 / B19F1）。
- `checkpoints` 真实源（B14F1）· `messages` LangChain 抽取（freechain）。
- 会话连续 / `Command` 恢复 / checkpoint 持久化（B14F1 / B15F1 / B16F1）。
- 静态断点（`interrupt_before` / `interrupt_after`）在 `stream()` 下的行为（v1 显式拒绝 · V-26 口径）。
- 节点别名解析（B8F3）· 图导出（B22F1 / B23F1）· 前端 UI（B26）。
