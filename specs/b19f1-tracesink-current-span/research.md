# Research: B19F1 · `TraceSink` 接入 + `current_span()` + 默认关闭

**Date**: 2026-11-21
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Baseline**: `.venv/bin/python -m pytest -q --tb=no` ⇒ **1863 passed, 6 skipped**（2026-11-21 实跑）
**Upstream**: `langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`（`.venv` 实测）

> 本文件只记录**设计决策**（Decision / Rationale / Alternatives），不重复 spec 的 FR/SC。
> 所有上游行为断言均来自 spec 的 P-01…P-10 / E-1…E-3（已实测或已标注来源）。

---

## D-01 · 注入形态：`compile(*, tracer=...)`

- **Decision**：公开注入点 = `StateGraph.compile(*, tracer: TraceSink | None = None)`。
- **Rationale**：① `RunConfig` 是 L1 配置载体（**9 字段冻结面**）⇒ 不能装
  `TraceSink` 实例；② `invoke` / `stream` 的签名已冻结（C11 / C12）⇒ 追加关键字会破快照；
  ③ `compile()` 已是外部能力注入落点（`checkpointer=` / `store=`）⇒ 只增可选关键字；
  ④ `harness/demo/README.md` 已登记该候选；⑤ 与上游 `RunnableConfig.callbacks` 的
  DIFF 已在 spec X-3 登记。
- **Alternatives considered**：`RunConfig.tracer`（破纯数据 / 9 字段）；`invoke(tracer=)` /
  `stream(tracer=)`（破冻结签名）；L5 包装器（改公开形态，违反 spec FR-001）。

---

## D-02 · run scope 与双绑定：L5 `trace_run_scope` + L3 局部 import

- **Decision**：新增 `src/freegraph/observability/_inject.py` 的 `trace_run_scope(tracer)`：
  - `tracer is not None` ⇒ `producer = SpanProducer(receiver=tracer)`；同时进入
    `bind_tracer(producer)`（L5）与 `bind_span_tracer(producer)`（L2）；作用域结束解绑。
  - `tracer is None` ⇒ **仅在 B19F1 作用域内嵌套屏蔽时**进入 `bind_tracer(None)` +
    `bind_span_tracer(None)`；并置 `_B19F1_SCOPE_ACTIVE` 标记（token 恢复）。
  - `_stategraph.CompiledGraph.invoke` / `_stream_events` 在需要时**局部 import** 该入口。
- **审批**：R-1 / R-2 / R-3 **已于 2026-11-21 一次性获发起者追认**；同步更新
  `立项书 §5.1` / `spec §5` / `layer-registry.md` / `gate_G25_import_graph.py`。
- **Rationale**：D-1 要求**同一个** producer 同时被 L2 节点接缝与 L5 调用辅助看到；
  `SpanProducer` 属 L5，L2 节点接缝是唯一入口 ⇒ 绑定动作必须在能同时触达两层的 L5 模块；
  L3 是 `compile` / `invoke` / `stream` 的归属层 ⇒ 必须局部进入该 scope。
- **Alternatives considered**：
  - 在 L2 构造 producer ⇒ L2 需 import L5（反向依赖，更严重）。
  - 在 L3 重写 producer / 适配器 ⇒ 违反 D-1「MUST NOT 重新实现 span 生产」。
  - 只绑定 L2 ⇒ `invoke_model` / `invoke_tool` 的 L5 当前栈为空，模型 / 工具 span 失效。
- **Registration**：R-1（L3 → L5 · ARCH-1）· R-2（L5 → L2 `_span_hook` · ARCH-3 · 不读 `_stream_context`）· R-3（B18F1 断言拆分）——**三者已获发起者一次性追认（2026-11-21）**。**B8F2 的 R-6 已相应收窄**：L2 `_run_round` 读取 stream id；B19F1 从节点 start `Span` 继承，不直接读取。

---

## D-03 · 嵌套 / 重入：**B19F1 作用域内**无 tracer 才屏蔽外层

- **Decision**：每个 `invoke()` / `stream()` 都是一个 run scope：
  - 本产物有 tracer ⇒ 构造**自己的** producer / run_id（嵌套不继承外层）。
  - 本产物无 tracer ⇒ **仅当 `_B19F1_SCOPE_ACTIVE` 为真**（外层是 B19F1 注入作用域）时，
    进入 `trace_run_scope(None)` 把 L2 + L5 两层 hook 都置 `None`（**B19F1 作用域优先**：即使
    作用域内另有 B18F1 直接绑定也屏蔽）；若**当前无活动 B19F1 作用域**且外层是 B18F1 直接绑定
    或完全没有 tracer，则不引入新的屏蔽语义（零 L5 import / 保留既有绑定）。
- **Rationale**：FR-021 要求「B19F1 作用域内层未注入 ⇒ 不产 span」；若只屏蔽 L2，L5
  `current_span()` 仍会返回外层 span ⇒ 泄漏。同时 MUST NOT 打红 B18F1 的直接绑定测试
  （那是 B18F1 已交付的注入方式）。
- **Alternatives considered**：无条件屏蔽外层（打红作用域外的 B18F1 直接绑定）；隐式继承外层
  B19F1 producer（违反 FR-021）；只屏蔽 L2（L5 泄漏）；限制「不许嵌套」（不可实现 / 反直觉）。

---

## D-04 · L2 → L5 的记录载荷：纯数据 dict

- **Decision**：L2 `_span_hook` / `superstep._bind` 构造一个**纯数据** `payload`（dict），
  经 `getattr(tracer, "on_trace_record", None)` 交给 L5 `SpanProducer`；L5 再构造
  `TraceRecord`。L2 **MUST NOT** import L5 类型。
- **Rationale**：ARCH-3「跨层只经协议 + 纯数据」；L2 只做旁路采集；记录类型 / JSON 降级
  属 L5。若 L2 构造 L5 类型 ⇒ 反向依赖 + 记录语义内聚失败。
- **Alternatives considered**：L2 直接构造 `TraceRecord`（反向 import）；把记录塞进 `Span`
  （破 11 字段 / 节点 `attributes` 恒空）；只让 B20 从快照猜（`PregelTask` 无 input）。

**payload 形状（L2 私有约定）**：

```python
{
  "span_id": str, "task_id": str, "run_id": str, "thread_id": str | None,
  "checkpoint_id": str | None, "node": str, "superstep": int,
  "triggers": tuple[tuple[Any, ...], ...],
  "concurrency_group": tuple[str, ...],
  "barrier_groups": tuple[tuple[str, ...], ...],
  "input_state": Any, "output_state": Any, "error": BaseException | None,
}
```

---

## D-05 · 触发源标识：`("e", source)` + `("send", producer, index)`

- **Decision**：标准任务（静态边 / `Command.goto`）的触发源 = `("e", 源节点名)`；
  fan-out 任务 = `("send", 产生者节点名, Send 序号)`。
- **Rationale**：B7F1 已冻结**边触发源**空间 `("e", 源节点名)`；B9F1 把 `goto` 落在同一
  空间（同源口径）⇒ 静态边与 goto **一起**给。B11F1 明确 fan-out 是**派发任务**、不是
  第三类调度触发源 ⇒ trace 层用 `("send", ...)` 作为**展示标识**（不写进调度触发源空间）。
  这满足 FR-011「三类一起给」，又不违反 B9F1「不另造第三类触发源」。
- **Alternatives considered**：只暴露 `goto`（可观测面只剩一半）；只暴露静态边（漏 fan-out）；
  给 fan-out 造第三类调度触发源（违反 B9F1 H-1）。

**来源落点**：`superstep._trigger_groups` / `_satisfied_groups` 的 satisfied 组
（标准任务）；`state.fanout[producer_id]` + `task.index`（fan-out）。
**排序键（写死）**：统一用 `(kind, source, index)`；标准边 / `goto` 的 `("e", source)`
令 `index = -1`，MUST NOT 直接混排二元组 / 三元组。

---

## D-06 · 并发组与 `superstep`

- **Decision**：
  - `superstep` = 当前轮的 **0 起**轮次索引 = `state.step`（与 `PregelTask.id` 的
    `f"{state.step}:{task_id}"` 前缀一致）。
  - `concurrency_group` = 本轮**全部派发任务**的 `task_id` 元组（含被派发但未启动的取消
    任务；其自身无 record），按**标准任务节点名序 + fan-out 数值 TaskId 序**排列
    （B12F1 FR-009 / B11F1 F-14）。
  - **记录到达顺序不保证**：确定性只由 `triggers` / `concurrency_group` 字段内顺序承载。
- **Rationale**：完成时刻在并发下不确定；节点名序 / TaskId 序是确定性口径；0 起与既有
  `PregelTask.id` 对齐，避免 off-by-one。
- **Alternatives considered**：按完成时刻（竞态）；按声明顺序（B12F1 已取代）；要求
  `on_trace_record` 到达顺序一致（并发下不可保证）；1 起（与 `PregelTask.id` 不一致，易误读）。

---

## D-07 · 屏障组

- **Decision**：`barrier_groups` = 所有**已满足且成员数 > 1** 的触发组，每组 = 源节点名
  元组；按组元组排序。单源组不进入 `barrier_groups`（只进 `triggers`）。
- **Rationale**：B7F4 的口径是「组内全 · 组间任一」；`_satisfied_groups` 已给出满足的组，
  直接暴露**组**即可；不伪造 `SuperStepResult` 字段。
- **Alternatives considered**：只给代表源（丢失屏障成员）；只给组号（用户无法直接读）；
  写进 `Span.attributes`（破 B18F1 Q11）。

---

## D-08 · 回调顺序与 `current_span()`

- **Decision**：`on_span_start`（`current_span()` = 新 span）→ 节点执行 →
  `on_trace_record`（= 该节点 span）→ `on_span_end`（= 父级 / `None`）。
  仅当节点 span 已产生（`start is not None`）**且接收端实现 `on_trace_record`** 才构造 / 推送记录。
- **Rationale**：spec 2026-11-21 裁定 A；沿用 B18「先出栈再转发」⇒ 不改 producer；
  sink 可在记录回调内可靠关联当前节点。接收端回调异常隔离仅覆盖 **`Exception`**；
  `BaseException` 不吞（与 B18F1 `_forward` 一致）。
- **Alternatives considered**：先结束再记录（记录与节点不同时为当前）；改 B18 先转发再出栈
  （无必要回溯修订）；不写死顺序（实现漂移）。

---

## D-09 · 输入 / 输出采集与 JSON 安全降级

- **Decision**：`input_state` = 节点实际入参；`output_state` = **节点原始返回值**
  （`node.run` 的 raw return；归一结果 `writes` / `gotos` / `fanout` 仅用于调度，**不**进入
  `output_state`）；两者完整采集，L5 `json_safe()` 递归转换：
  - `str` / `int` / `float` / `bool` / `None` ⇒ 原样；
  - `dict` / `list` / `tuple` ⇒ 递归（`tuple` → list）；
  - 其它对象 / 循环引用 / bytes / 集合 ⇒ 确定性占位符
    `f"<{type.__module__}.{type.__qualname__}>"` / `"<cycle>"` / 排序后的列表；
  - **不**内省对象属性（隐私最小面）；**不**抛异常。
  - `TraceRecord.error` 保留**原异常对象**；`to_jsonable()` 把它转为
    `{"type": type(exc).__name__, "message": str(exc)}`（B20 落盘用）。
  - **raw / normalized 承载（写死）**：`_execute_node_pure_with_raw` 返回
    `(normalized, raw)`；`_bind` 解包后把 `normalized` 交回调度、`raw` 用于 `output_state`；
    接收端未实现 `on_trace_record` 时走原路径，不采集 raw / input-output。
- **Rationale**：spec 澄清 D；B20 是 JSONL ⇒ 必须在 B19F1 侧保证可序列化；不泄漏对象内容；
  `error` 的原对象语义由 D-6 要求保留。
- **Alternatives considered**：原样交 B20（B20 需重复降级且可能崩）；只记摘要（不满足等价
  记录）；`repr()` 对象（可能泄漏内容 / 不确定）。

> **SC-011 口径**：`json.dumps(record.to_jsonable())` 不抛；`record.error` 仍是原异常对象。
> 记录**不是**直接 `json.dumps(record)`（异常对象不可序列化）。

---

## D-10 · `current_span()` 的归属与导出

- **Decision**：`SpanProducer` 新增 `current_span() -> Span | None`（栈顶）；L5
  `observability/__init__.py` 导出模块函数 `current_span()`（读 `current_tracer()`）；
  **不**经 `freegraph.graph` 门面；`import freegraph` 不加载 L5。
- **Rationale**：C24；上游 `get_current_run_tree` 是自由函数 + contextvar（P-01），
  但 upstream 的 callback 路径不可得（E-2）⇒ freegraph 在节点执行期间更强；门面不得
  import L5（G18）⇒ 只能从 L5 模块导出。
- **Alternatives considered**：门面导出（破门面符号面 / 门面 import L5）；委托 sink 的
  `current_span` 方法（不可靠 / 无 sink 时为 None 但语义不同）；放进 L1（行为不属于 L1）。

---

## D-11 · 中断 / 取消与记录对齐

- **Decision**：`record 数 == 节点 span 数`。中断节点 `error` = 原 `GraphInterrupt`；
  **节点自身抛 `CancelledError` 等取消异常 = 原取消 / 异常**；**运行期只取消排队未启动任务
  （已启动任务跑完，不取消）**；从未启动的取消任务无 span、无 record。
- **Rationale**：B18 的异常路径仍产 end span（FR-010）；记录与 span 对齐可判定；
  D-6 的错误载体是原异常（+ `add_note`）。
- **Alternatives considered**：中断不产记录（中断现场缺失）；用字符串标记（违反错误载体
  口径）；取消一律不产（与 span 不对齐）。

---

## D-12 · 上游证据与差分

- **Decision**：钉 `langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`；
  差分 D-301…D-310；上游缺席即 skip。
- **Rationale**：宪法原则 XI / VIII；spec 的 E-1…E-3 已实测（`get_current_run_tree` 在
  callback 驱动的节点内返回 `None` 是**实测事实**，不是猜测）。
- **Alternatives considered**：沿用 B18F1 的旧版本 / 旧行号（拒绝）；只读源码不实测（拒绝）。

---

## 已决项（原「未决项」已收敛）

**无未决项。** 7 条 spec 澄清 + 本文件 D-01…D-12 已覆盖全部设计点；以下实现细节均已由
data-model / contracts / tasks 写死：

- `TraceRecord` 只提供 `to_jsonable()`；**不**新增 `as_dict`（避免双视图漂移）。
- `json_safe` 对 `set` / `frozenset` ⇒ **排序后的 list**；不可排序元素按降级后的字符串排序。
- L2 payload 的键名与 `TraceRecord` 字段**逐字一致**（见 data-model §8.2）。
- 层注册表只登记 **R-1**（`trace-wiring-L3-L5`）；R-2 / R-3 由
  `tests/contracts/test_architecture.py` 的拆分断言覆盖；R-2 **不读** `_stream_context`。
- **B8F2 的 R-6 已收窄**：L2 读取 stream id，B19F1 从节点 start `Span` 继承；T013 的例外
  断言只放行 `_inject.py` → `_span_hook`，不放行 `_stream_context`。
- **R-1 / R-2 / R-3 已获发起者一次性追认（2026-11-21）**；追认文字进 `manual-verification.md`。
