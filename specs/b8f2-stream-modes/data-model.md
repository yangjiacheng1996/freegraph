# 数据模型（Data Model）—— B8F2 的多模式流式输出

**Feature**: `B8F2` · **Spec**: [spec.md](./spec.md)
**契约**: [contracts/stream-contract.md](./contracts/stream-contract.md)
**核实环境**: CPython **3.11.16** · 上游 `langgraph` **1.2.11**（取证于 2026-11-19）

> **落位**：流式**主循环**与**信封组装**落 **L3**（`src/freegraph/_stategraph.py`）；
> 流式**会话初始化 / contextvar / custom 缓冲 / round capture** 落 **L2 私有**
>（`src/freegraph/runtime/_stream.py` + `_stream_context.py`）⇒ 方向仍是 **L3 → L2**。
> ⇒ **零新增公开 L2 符号**（`freegraph.runtime.__all__` 仍 **23**）。
> ⇒ **MUST NOT** 被测试解析（测试**直接断言行为**）。

---

## 1. 实体总览

| 实体 | 角色 | 生命周期 | 可变性 |
|---|---|---|---|
| **`StreamMode`（闭集）** | 七种合法 mode 名 | 编译期常量 | 不可变 |
| **`StreamEvent`（四键信封）** | 对外可见的唯一事件形态 | 单次 `stream()` | 一次性 `dict` |
| **`StreamWriter`** | 节点侧写入自定义数据的可调用对象 | 运行级（contextvar） | 无状态闭包 / no-op |
| **`CustomSink`（私有）** | 本轮 custom 写入的线程安全缓冲 | 单轮 | 轮末清空 |
| **`RoundCapture`（私有）** | 中断轮的任务定格（`PregelTask`） | 单轮 | 轮末清空 |
| **`StreamSession`（私有）** | 流式运行的初始化 + contextvar 载体 + `max_concurrency` / `max_steps` | 单次 `stream()` | `finally` 复原 |
| **`_run_single_step` / `_stream_tick`（私有）** | L2 单轮执行：`run_super_step` 与 `_stream_tick` 的**唯一**共享实现；`_stream_tick` 透传原始 `route_config`、执行前精确判上限 | 单轮 | 无状态函数 |
| **`_STREAM_RUN_ID` / `_STREAM_THREAD_ID`（私有）** | 单次运行的 `run_id` / 会话 `thread_id` 的 L2 contextvar 载体 | 单次 `stream()` | `finally` 复原 |
| **`PregelTask`（L1 既有）** | task 完成定格（七字段） | 单轮 / 累计 | frozen |
| **`SuperStepResult.tasks`（新增）** | 每轮完成 task 的定格 | 跨轮累计 | frozen |
| **`run_id` / `thread_id`** | 单次运行 / 会话标识 | 单次 `stream()` | 不可变字符串 |

---

## 2. 实体表

### 2.1 `StreamMode`（闭集）

| 项 | 契约 |
|---|---|
| 取值 | `values` / `updates` / `checkpoints` / `tasks` / `debug` / `messages` / `custom` |
| 来源 | `langgraph/types.py:122-124`（`StreamMode` Literal）⇒ **逐字同名** |
| 默认档 | 签名默认 `None`；`None` ⇒ **`"updates"`**（上游 `CompiledStateGraph` 同款 · `state.py:1357` · 实测 E-18） |
| 校验 | 非法值 / 空序列 ⇒ **调用时** 内置 `ValueError`（点名非法值 + 列出七种合法值）· 非 `str` / 非 `Sequence` / 非 `None` ⇒ `TypeError` · 重复 ⇒ 去重保序 |
| 单值 / 序列 | `str` ⇒ 单 mode；`Sequence[str]` ⇒ 多 mode；`None` ⇒ 默认档；每条事件的 `stream_mode` 标明来源 |

### 2.2 `StreamEvent`（四键信封）

| 字段 | 类型 | 语义 | 不变量 |
|---|---|---|---|
| `stream_mode` | `str` | 该事件来自哪一档 | ∈ 七种合法值 |
| `payload` | `Any` | 该档的载荷 | 见 §2.4…§2.10 |
| `run_id` | `str` | 本次 `stream()` 的运行标识 | 非空；同一流内**全部事件相同**；跨流**不同** |
| `thread_id` | `str \| None` | 会话标识 | 来自 `config`；未提供 ⇒ `None` |

- **键集恰为四键** ⇒ MUST NOT 在 `payload` 里再挂 id（避免污染状态 / 自定义数据）。
- 信封由 L3 组装（`_event(...)` 私有助手）⇒ L2 MUST NOT 构造信封。

### 2.3 `StreamWriter` / `CustomSink`

| 项 | 契约 |
|---|---|
| 类型别名 | `StreamWriter = Callable[[Any], None]`（L1 · `contracts/types.py`） |
| 公开入口 | `freegraph.graph.get_stream_writer() -> StreamWriter`（门面 7→8） |
| 实现落点 | `src/freegraph/runtime/_stream_context.py`（L2 私有） |
| 无流行为 | 返回 **no-op** 可调用对象（不抛异常 · 上游 `config.py:13-14`） |
| 跨线程 | 由 `run_tasks_concurrently` 的**每任务** `copy_context()` 传播（`_executor.py:64` 的 `copy_context()` / `:71` 的 `ctx.run`；async `:164`） |
| `CustomSink` | 线程安全；键 = 本轮 **TaskId（int）**；值 = 该任务的写入序列（按调用顺序） |
| 顺序 | 轮末按 **TaskId 升序 + 任务内写入序** 产出 |
| 时机 | **轮末批量**（每轮 L2 单轮入口结束后；不是逐写即时）⇒ **P-23 / X-6** |
| 禁止 | MUST NOT 把 custom 写入塞进 `_TaskOutcome`（H-7 · 原则 XII） |
| 关键字注入 | 节点签名声明 **`writer`**（`POSITIONAL_OR_KEYWORD` / `KEYWORD_ONLY`；注解 ∈ `StreamWriter` / `"StreamWriter"` / 空）⇒ 以关键字注入 `get_stream_writer()`；`**kwargs` / 其它参数名 / 注解不匹配 ⇒ 不注入；无流 no-op；`stream_writer` 是 runtime key，不是参数名 |

### 2.4 `values` 载荷

| 项 | 契约 |
|---|---|
| 形态 | 普通 `dict`（**完整状态**） |
| 键集 | == schema 全集（**路由通道不进**）· 顺序 == schema 声明顺序 |
| 无值 key | 填 `None`（**仅覆盖型通道**）；归约型类型空值 `[]` / `0` 原样保留 |
| 归一 | **唯一实现点** = `_full_state`（`_stategraph.py:235-267`）· **L2 MUST NOT** 复制 |
| 节奏 | **初始状态**一条 + **每个完成的 super-step** 一条 |
| 中断收尾 | `payload` 额外含 `"__interrupt__"`（元组） |
| 终态判据 | 无静态断点 / 无会话历史时，最后一条 `payload` == `invoke()` 终态 |

### 2.5 `updates` 载荷

| 项 | 契约 |
|---|---|
| 形态 | `{节点名: {通道 key: 值 \| 值的元组}}` |
| 粒度 | 每个**完成的 task** 一条 |
| 单写 | 该通道的值（标量） |
| 同 task 同通道多写 | **按写入顺序的元组**（保留归约顺序） |
| 合并 | 按**通道归约语义**逐条应用（MUST NOT 简单 `dict.update`） |
| 中断收尾 | 额外一条 `{"__interrupt__": <元组>}` |

### 2.6 `tasks` 载荷（`PregelTask`）

| 字段 | 类型 | 语义 | 不变量 |
|---|---|---|---|
| `id` | `str` | 运行内唯一任务标识 | **生成方式不冻结**；实现建议 `f"{step}:{TaskId}"`，跨运行不可比较 |
| `name` | `str` | 节点名（fan-out = 目标名） | 与 `updates` 的键同口径 |
| `path` | `tuple[str \| int \| tuple, ...]` | 任务路径 | 标准 `(节点名,)`；fan-out `(目标名, TaskId)` |
| `error` | `Exception \| None` | 真实异常对象（原对象） | 成功 / 挂起 ⇒ `None` |
| `interrupts` | `tuple[Interrupt, ...]` | 该 task 的中断载荷 | 无中断 ⇒ `()` |
| `state` | `RunConfig \| StateSnapshot \| None` | v1 **恒 `None`** | 子图 / per-task 快照归 v2 / B15F1 |
| `result` | `Any \| None` | 该 task 的更新载荷 | 与 `updates` 同形；无写 ⇒ `{}` |

- **粒度**：每个**已完成** task 一条（含**被中断**的 task）。
- **中断 task**：`error=None` · `interrupts` 非空 · `result` = 已发生写入。
- **失败 task**：不产出事件（失败轮不产出 `SuperStepResult`）；已发生的 `custom` 先 flush。
- **`SuperStepResult.tasks`**：`tuple[PregelTask, ...]` · 追加在末尾 · 缺省 `()` ·
  单轮 = 本轮 · 多轮 = 累计；**中断轮不产出结果对象** ⇒ 中断 task 只进 `stream()` 事件，
  不进 `SuperStepResult.tasks`。

### 2.7 `debug` 载荷

| 字段 | 类型 | 语义 |
|---|---|---|
| `step` | `int` | **1 起**的 super-step 序号（同轮多 task 相同；**进入每轮时递增**，中断轮同样占一个序号） |
| `timestamp` | `str` | UTC ISO-8601（`datetime.now(timezone.utc).isoformat()`）；MUST 可被 `datetime.fromisoformat` 解析 |
| `type` | `str` | v1 **恒 `"task_result"`** |
| `payload` | `PregelTask` | 与同轮 `tasks` 事件**同一个**对象 |

- v1 **无** checkpoint 类 debug 事件（`checkpoints` 源归 B14F1）。
- 中断 task 同样补发一条。

### 2.8 `custom` 载荷

| 项 | 契约 |
|---|---|
| 来源 | 节点内 `get_stream_writer()(value)` |
| 形态 | **原样** = 用户传入的对象（不包装 / 不改写 / 不 JSON 化） |
| 顺序 | TaskId 升序 + 任务内写入序 |
| 时机 | **轮末批量**（P-23 / X-6） |
| 中断 | 本轮已记录的先产出，再收尾 |
| 失败 | 本轮已记录的先产出，再重抛原异常 |

### 2.9 `checkpoints` / `messages` 载荷

| mode | v1 行为 | 边界 |
|---|---|---|
| `checkpoints` | **恒为空序列**（零事件、零异常） | 真实源归 **B14F1** |
| `messages` | **恒为空序列**（零事件、零异常） | LangChain LLM token 流归 freechain；有源时**原样透传** |

### 2.10 `run_id` / `thread_id`

| 字段 | 生成 | 解析 |
|---|---|---|
| `run_id` | `uuid4().hex`（L3 · 每次 `stream()` 一个） | 用户不可指定；`RunConfig.run_id` **忽略**（澄清 A） |
| `thread_id` | 来自 `config` | `configurable["thread_id"]` 优先于顶层 `thread_id`（`RunConfig.resolved_thread_id()`） |
| L2 载体 | `StreamSession` 绑定 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID` | B18F1 / L2 的 span MUST 读取同一对 contextvar；B19F1 从节点 span 继承（D-3） |

---

## 3. 关系（ER 式文字图）

```text
StateGraph.compile()
  └── CompiledGraph
        ├── .stream(input, config, *, stream_mode)  ← L3 门面
        │     ├── StreamSession（L2 私有）
        │     │     ├── SchedulerState
        │     │     ├── StreamWriter（contextvar）
        │     │     ├── CustomSink（每轮 · 轮末批量）
        │     │     ├── RoundCapture（每轮 · 中断用）
        │     │     └── _STREAM_RUN_ID / _STREAM_THREAD_ID（contextvar）
        │     ├── L2 单轮入口 `_stream_tick`（私有）/ `run_super_step`（公开）
        │     │     └── `_run_single_step` → `_run_round` / `_evaluate_*` / `_determine_triggers`
        │     ├── 事件信封（四键）
        │     └── run_id / thread_id
        └── .invoke(...)  ← B7F3 既有
              └── _full_state（同一归一实现点）
```

---

## 4. 状态机（一次 `stream()` 的生命周期）

### 4.1 文字图

```text
[调用 stream()]
   │ 校验 stream_mode（非法 / 空 ⇒ 立即失败）
   ▼
[惰性迭代器已返回]  ← 尚未执行任何节点
   │ 第一次 next()
   ▼
[会话初始化]  ← 输入写入 / bind_run / contextvar / run_id / thread_id
   │  ← checkpointer 被忽略（不读/写快照、不触发恢复）
   │  ← 含静态断点（interrupt_before/after）⇒ ValueError（V-26 口径）
   │
   ├── values 请求 ? → 产出「初始状态」事件
   ▼
[轮循环]  ← while True
   │ _stream_tick(spec, state, max_steps=..., max_concurrency=..., route_config=raw_config)
   │   ← 复用 _determine_triggers；触发集非空且 state.step >= max_steps ⇒ GraphRecursionError（执行前）
   │   ← 触发集为空 ⇒ 返回 None ⇒ 结束
   ├── 成功且 executed 非空
   │     → custom → updates → tasks → debug → values
   │     → 下一轮
   ├── 收敛（返回 None）
   │     → 结束（不产出空轮事件）
   ├── GraphInterrupt
   │     → custom → updates(__interrupt__) → tasks → debug → values(__interrupt__)
   │     → 结束
   └── 其他异常
         → custom（已发生）→ 重抛原异常
[结束]  ← finally 复原 contextvar token；零悬挂线程
```

### 4.2 迁移表

| 当前 | 事件 / 条件 | 下一 |
|---|---|---|
| 调用 `stream()` | 合法 mode | 惰性迭代器（未执行） |
| 调用 `stream()` | 非法 mode / 空序列 | **抛** `ValueError` / `TypeError`（不返回迭代器） |
| 惰性迭代器 | 第一次 `next()` | 会话初始化 |
| 会话初始化 | 图含静态断点（`interrupt_before` / `interrupt_after`） | **抛** `ValueError`（V-26 口径；不执行节点） |
| 会话初始化 | `values` 被请求 | 初始 `values` 事件 → 轮循环 |
| 会话初始化 | `values` 未请求 | 轮循环 |
| 轮循环 | L2 单轮入口（`_stream_tick`）成功且 `executed` 非空 | 产出本轮事件 → 下一轮 |
| 轮循环 | 已达 `recursion_limit` 且**触发集非空** | **执行前抛** `GraphRecursionError`（零新增错误类型） |
| 轮循环 | 恰好达到 `recursion_limit` 但触发集为空 | 结束（**不误抛**） |
| 轮循环 | `_stream_tick` 返回 `None`（触发集为空） | 结束 |
| 轮循环 | `GraphInterrupt` | 收尾事件（含 task / custom）→ 结束 |
| 轮循环 | 其他异常 | flush custom → **重抛** |
| 任意 | 消费者 `close()` | `finally` 复原 → 结束（不再执行后续轮） |

### 4.3 事件顺序（跨档固定）

同一轮内：`custom → updates → tasks → debug → values`。
初始 `values`（若请求）在**第一轮之前**。
`custom` 是**轮末批量**（本轮 L2 单轮入口结束后按 TaskId 序产出 · **P-23 / X-6**），不是逐写即时。
中断收尾沿用同一顺序（`updates` = `{"__interrupt__": ...}`，`values` 含 `__interrupt__`）。

---

## 5. 校验规则表

| # | 场景 | 失败信号 | 时机 |
|---|---|---|---|
| **VS-1** | `stream_mode` 非 `str` / 非 `Sequence[str]` / 非 `None` | 内置 `TypeError` | `stream()` **调用时** |
| **VS-2** | `stream_mode` 值不在闭集（或空序列） | 内置 `ValueError`（点名 + 列合法值） | 调用时 |
| **VS-2b** | `stream_mode=None` | 解析为 `"updates"`（不失败） | 调用时 |
| **VS-3** | `stream_mode=[]` | 内置 `ValueError` | 调用时 |
| **VS-4** | 重复 mode | 去重保序（**不失败**） | 调用时 |
| **VS-5** | `input` 是 `Command` | 内置 `TypeError`（点名「恢复路径归 B14F1 / B15F1」） | 第一次迭代 |
| **VS-6** | `input` 非 `dict` / `None` | 内置 `TypeError` | 第一次迭代 |
| **VS-7** | `config` 非法类型 | 由 L2 `resolve_config` 抛 `TypeError` | 第一次迭代 |
| **VS-8** | `run_id` 从 `RunConfig.run_id` 传入 | **忽略**（不失败） | 第一次迭代 |
| **VS-9** | 无流时 `get_stream_writer()` | **no-op**（不失败） | 任意 |
| **VS-10** | 失败轮 / 中断轮 | 见 §4 | 轮末 |
| **VS-11** | `input=None` | 允许（无输入写入）；`Command` ⇒ `TypeError` | 第一次迭代 |

---

## 6. 不变量表（逐条可判定）

| # | 不变量 | 判据 |
|---|---|---|
| **IS-1** | 每条事件是 `dict` 且键集恰为 `{stream_mode, payload, run_id, thread_id}` | `set(e) == {...}` |
| **IS-2** | 同一 `stream()` 的全部事件共享同一 `run_id`；两次流不同 | 集合基数 == 1 / 2 |
| **IS-3** | `thread_id` 与 `config` 一致 | 等值 |
| **IS-4** | `values` 事件数 == `1 + 执行步数`；最后一条 `payload` == `invoke` 终态（限定） | 等值 |
| **IS-5** | `updates` 合并 == `invoke` 终态（按通道归约） | 等值 |
| **IS-6** | `tasks` 每条 `payload` 是 `PregelTask`；每完成 task 恰一条 | `isinstance` + 计数 |
| **IS-7** | `debug` 每条键集 == `{step, timestamp, type, payload}`；`type == "task_result"`；`step` 1 起且同轮相同（含中断轮）；`timestamp` 可被 `datetime.fromisoformat` 解析且为 UTC | 等值 / 解析断言 |
| **IS-8** | `custom` 在**轮末批量**产出，顺序 == TaskId 升序 + 任务内写入序（P-23 / X-6） | 序列等值 |
| **IS-9** | `checkpoints` / `messages` 长度 == 0 且不抛 | 计数 |
| **IS-10** | 非法 mode ⇒ 调用时 `ValueError` | `pytest.raises` |
| **IS-11** | 惰性：不迭代 ⇒ 节点执行次数 == 0 | 计数 |
| **IS-12** | 提前停止 ⇒ `freegraph-node` 线程数 == 0 | `threading.enumerate` |
| **IS-13** | 中断 ⇒ `tasks` / `debug` 为被中断 task 补发一条；`values` / `updates` 含 `__interrupt__`；流正常结束 | 断言 |
| **IS-14** | 失败 ⇒ custom 先产出；原异常原样重抛；失败轮 values/updates/tasks/debug 不产出 | 断言 |
| **IS-15** | `run_super_step` / `run_super_steps` 签名逐字不变 | `inspect.signature` |
| **IS-16** | `freegraph.runtime.__all__` == 23；`freegraph.graph.__all__` == 8；`freegraph.contracts.__all__` == 22 | 计数 |
| **IS-17** | `SuperStepResult` 字段 = 原 4 个 + `tasks`（末尾）；`InterruptResult` 仍 4 个 | `dataclasses.fields` |
| **IS-18** | `vars(compiled)` 仍 == 11 键 | 计数 |
| **IS-19** | 零新增第三方依赖 / 零出站 / 零环境变量 | 门禁 |
| **IS-20** | 轮循环超 `recursion_limit` **且触发集非空** ⇒ `GraphRecursionError`（与 `invoke` 同款）；**执行前**抛；恰好收敛于上限 ⇒ 不抛 | `pytest.raises` + 节点调用计数 |
| **IS-21** | `max_concurrency` 从 `config`（`RunConfig.max_concurrency` 或普通映射同名字段）解析并传给 L2 单轮入口；`stream()` 不新增该关键字 | 计数 / 行为断言 |
| **IS-22** | 声明 `writer` 的节点在 `stream` 中收到注入；`stream_writer` 不注入；`invoke` 中为 no-op | 行为断言 |
| **IS-23** | `stream(None)` = 无输入写入，图仍由静态入口触发；`Command` 在首次迭代抛 `TypeError` | 行为断言 |
| **IS-24** | 条件边图在 `stream` 下的路由目标序列与 `invoke` 一致（复用同一实现）；**双参路由的第二参 == 用户交给 `stream()` 的原始 `config`** | 序列 / 终态等值 + 逐字等值 |
| **IS-25** | `_STREAM_RUN_ID` / `_STREAM_THREAD_ID` 与本流全部事件的 `run_id` / `thread_id` 一致；B18F1 / L2 读取同一对值，B19F1 继承 | 等值 |

---

## 7. 与既有实体的持有面影响

| 实体 | 变化 | 兼容性 |
|---|---|---|
| `SuperStepResult` | **追加** `tasks: tuple[PregelTask, ...] = ()` | 既有 4 字段原样；按关键字构造零改动 |
| `InterruptResult` | **零改动** | 4 字段 |
| `CompiledGraph` | 私有字段**零新增**（`vars(compiled)` 仍 11） | `stream` 方法体替换 |
| `freegraph.contracts` | +`StreamWriter`（21→22） | 纯新增 |
| `freegraph.graph` | +`get_stream_writer`（7→8） | 纯新增 |
| `freegraph.runtime` | **不变**（23） | `_stream.py` / `_stream_context.py` / `_run_single_step` / `_stream_tick` 私有 |
| `_TaskOutcome` | **不变**（5 字段） | custom 不进结果槽 |

---

## 8. 边界（本模型不规定的事）

- 子图命名空间 `ns`（v2 · C26）。
- `messages` 的 LangChain 消息抽取（freechain）。
- checkpoint 持久化 / 会话连续 / `Command` 恢复（B14F1 / B15F1 / B16F1）。
- 静态断点（`interrupt_before` / `interrupt_after`）在 `stream()` 下的行为：v1 **显式拒绝**（`ValueError` · V-26 口径）。
- `checkpointer` 的读写 / 调用：`StreamSession` **忽略**它（FR-028）。
- trace span 的生产 / `TraceSink` 接入（B18F1 / B19F1）。
- 前端 / UI 消费（B26）。
