# Implementation Plan: B19F1 · `TraceSink` 接入 + `current_span()` + 默认关闭

**Branch**: `b19f1-tracesink-current-span`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_plan` 钩子；既有 feature 同样在 `main` 上开发）
| **Date**: 2026-11-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b19f1-tracesink-current-span/spec.md`

**Feature ID**: `B19F1`（M3 可诊断 · **第 24 个** · 前置：**B18F1**；承接 **B2F1 / B7F1 / B8F2 / B8F3 / B9F1 / B11F1 / B12F1 / B7F4 / B18F1**；本 feature 完成后解锁 **B20F1**）

> **范围提醒**：本 feature **只做接入与推送**，不重新生产 span、不改 `Span` 11 字段、
> 不改 `TraceSink` 3 方法、不改 `RunConfig` 9 字段、不改 `SuperStepResult` / `PregelTask`。
> `SpanProducer` 复用 B18F1；本地 trace 存储（B20F1 / B20F2）、OTLP（B21F1）、UI（v2）
> 不在本 feature 范围。注入形态已在 spec 锁定为 **`compile(*, tracer=...)`**。

---

## Summary

交付 freegraph 的 **可观测接入层**：用户显式给 `compile(tracer=...)` 注入一个
`TraceSink`，运行时在**每次 `invoke()` / `stream()` 的 run scope** 内构造一个
`SpanProducer` 并**双绑定** L2 / L5；span 按 `on_span_start → on_trace_record →
on_span_end` 推送；同时提供 `current_span()`；未注入时完全静默（含**屏蔽外层 tracer**）。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **注入点** | `StateGraph.compile(*, tracer: TraceSink \| None = None)` | 只持有 sink；`compile()` 无参仍可调用；顶层且无外层 tracer 时 `None` ≡ 未注入 |
| **run scope + 双绑定** | 每次 `invoke()` / `stream()` 构造一个 `SpanProducer`，同一实例绑定 L2 `_span_hook` 与 L5 `_producer` | run-scoped；结束即解绑；**仅 B19F1 注入作用域内的嵌套无 tracer 运行屏蔽外层**（作用域外的 B18F1 直接绑定保持既有语义） |
| **推送** | `on_span_start` / `on_span_end` 成对（异常路径也成对） | 开始 = `end_time` 空；结束 = 同 `id`、`end_time` 已填 |
| **`current_span()`** | L5 模块函数，返回上下文内最内层 `Span` | 无则 `None`；不委托给 sink 的 `current_span` |
| **补充 trace 记录** | 每节点任务一条，经**可选鸭子类型** `on_trace_record(record)` 推送 | 不是 `TraceSink` 协议成员；**不实现 ⇒ 零影响（不构造 payload / 不采集 input-output）** |
| **记录内容** | `span_id` / `task_id` / `run_id` / `thread_id` / `checkpoint_id` / `node` / `superstep` / 触发源 / 并发组 / 屏障组 / `input_state` / `output_state` / `error` | 输入输出完整采集 + JSON 安全降级；`error` = 原异常对象 |
| **确定性** | `triggers` 按统一键 `(kind, source, index)`（标准项 `index = -1`）；`concurrency_group` 按标准节点名序 + fan-out **数值** TaskId 序（B11F1 F-14） | 不用完成时刻、不用声明顺序；记录**到达顺序**不保证 |
| **默认关闭** | 未注入且无外层 tracer ⇒ 不构造 `Span` / `SpanProducer` / 记录 / id，不读环境变量 | 允许一次廉价 contextvar 判断；B18F1 直接绑定不计入「无外层 tracer」 |
| **零扩张** | 不改 L1 / 门面 / `runtime.__all__`；只在 L5 模块新增 `current_span` / `TraceRecord` 等 | `import freegraph` 仍惰性 |
| **差分** | D-301…D-310（避 B18F1 的 D-201…D-208） | 上游缺席即 skip |

**技术方案（关键落点）**：

| 环节 | 落点 |
|---|---|
| 注入点 | `src/freegraph/_stategraph.py`：`StateGraph.compile(*, tracer=...)` → `CompiledGraph._tracer` |
| run scope（L5） | **新增** `src/freegraph/observability/_inject.py`：`trace_run_scope(tracer)`，内部双绑定 L2 `bind_span_tracer` + L5 `bind_tracer` |
| invoke run-id | `_stategraph.CompiledGraph.invoke`：注入非空时用 `bind_run_ids(uuid4, resolved_thread_id)` **优先**建立每次运行独立的 id；B18F1 的 L2 `_run_graph` 绑定为 **fallback**（仅当 `_STREAM_RUN_ID` 为空），二者共用同一载体、每次注入运行恰一次有效绑定；`stream` 由 `StreamSession` 绑定 |
| 嵌套屏蔽 | `_stategraph` 在「本产物无 tracer 但外层有 tracer」时进入 `trace_run_scope(None)`，把两个 hook 都置 `None`（FR-021）；**B19F1 作用域优先于其内部的 B18F1 直接绑定** |
| 当前 span 栈 | B18F1 `SpanProducer`：新增 `current_span()`；L5 `current_span()` 读 `current_tracer()` |
| 补充记录（L5） | **新增** `src/freegraph/observability/_record.py`：`TraceRecord` + `json_safe()` 降级 + `to_jsonable()` |
| L2 采集接缝 | `src/freegraph/runtime/_span_hook.py` + `superstep.py`：`_run_round` 的 `_bind` 在 `end_node_span` **之前**、且**仅当 `tracer.wants_trace_records` 为真**时，构造 payload 并调用可选 `tracer.on_trace_record(payload)` |
| 触发源 / 并发组 / 屏障组 | `superstep._trigger_groups` / `_satisfied_groups` 的 `satisfied` 组；`state.step`；本轮 `records` |
| 输出状态 | 捕获 `node.run` 的**原始返回值**（raw return）；`_execute_node_pure` 的归一结果（`writes` / `gotos` / `fanout`）仍用于调度，但**不**作为 record 的 `output_state`；JSON 降级处理内部对象 |
| 记录推送 | `SpanProducer.on_trace_record(payload)` → `TraceRecord` → 接收端可选方法（异常隔离） |
| 零开销 | 无 tracer、无 B19F1 作用域、且无 B18F1 直接绑定 ⇒ 不 import L5、不构造 producer、不构造 payload；**有 tracer 但接收端无 `on_trace_record` ⇒ 不构造 payload** |
| 时间源 | 复用 B18F1（标准库 UTC ISO-8601 · 严格正耗时） |
| 测试 | `tests/observability/` · `tests/runtime/` · `tests/contracts/` · `tests/differential/test_b19f1_trace_access_parity.py` |

**零新增运行时依赖**。**破冻结面**：`compile()` 追加可选关键字（只增不改）。
**新增已追认例外**：**R-1 L3 → L5**（仅 tracer 接线）· **R-2 L5 → L2 私有 hook**（仅双绑定 `_span_hook`；id 由节点 start `Span` 继承，**不读** `_stream_context`）· **R-3**（B18F1 断言拆分）——**三者已获发起者一次性追认（2026-11-21）**。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`requires-python = ">=3.11"`）；
允许 `contextvars` / `dataclasses` / `datetime` / `time` / `uuid` / `logging` / `inspect` / `typing`。
**MUST NOT** 使用 3.12+ 的 `TypeAliasType` / `override` / `TypeIs` / PEP 695 `type`。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []`）。
开发期：`pytest`（既有 `dev`）· 差分：`langgraph==1.2.11` / `langchain-core==1.7.6` /
`langsmith==0.14.17`（既有 `differential` 组）。`pyproject.toml` **零改动** ⇒ G3 / G21 / G22 / G23 恒绿。

**Storage**: N/A（本 feature 不落盘；trace 存储归 B20F1 / B20F2）。

**Testing**: pytest —— `tests/observability/`（`current_span` / `TraceRecord` / JSON 降级 / 可选回调）·
`tests/runtime/`（run scope / 双绑定 / 记录采集 / 屏蔽外层 / 中断与取消）·
`tests/facade/`（`compile(tracer=...)` 签名与快照）· `tests/contracts/`（L1 / 门面 / `runtime.__all__` 零扩张 · 门禁）·
`tests/differential/test_b19f1_trace_access_parity.py`（D-301…D-310）。

**Target Platform**: Linux / macOS / Windows · CPython 3.11+ · 零出站。

**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A（不设墙钟预算）** —— 未注入且无外层 tracer 时只做一次
contextvar 读取 + `is None` 判断；不引入 I/O / 网络 / 线程池。MUST NOT 用耗时做断言（CI 假红）。

**Constraints**（主要来自 spec）：

| 约束 | spec 条目 |
|---|---|
| 只依赖标准库 + L1；零第三方依赖 | FR-007 / FR-008 · SC-005 |
| 零出站 / 零环境变量 / 导入无副作用 | FR-008 · SC-005 |
| 注入形态锁定 `compile(*, tracer=...)` | FR-001 |
| `TraceSink` 静态注解仍 3 方法；运行期最小面 = start/end；`SpanOnlySink` 属有意鸭子类型扩展 | FR-001 / FR-006 |
| 双绑定同一 `SpanProducer`，run-scoped | FR-009 · SC-002 |
| 未注入且无任何外层 tracer ⇒ 零 span / 零 producer / 零记录 / 零 id / 不读 env | FR-005 · SC-002 |
| **B19F1 作用域内**嵌套无 tracer ⇒ **屏蔽外层**，不产出 span / record；**B19F1 作用域优先于其内部的 B18F1 直接绑定**；作用域外的直接绑定保持既有语义 | FR-021 · SC-016 |
| **sink 实现 `on_trace_record` 时** `on_span_start → on_trace_record → on_span_end`；未实现时 start → end | FR-002 / FR-003 · SC-015 |
| `current_span()` 嵌套恢复、空上下文 `None` | FR-003 / FR-004 · SC-004 |
| 每节点任务一条记录；`span_id` + `task_id` | FR-015 · SC-011 / SC-014 |
| 记录与 span 一一对齐（含中断 / 取消） | FR-015 · SC-017 |
| 输入 / 输出完整采集 + JSON 安全降级 | FR-015 · SC-011 / SC-013 |
| `error` = 原异常对象（+ `add_note`） | FR-015 · SC-017 |
| 触发源覆盖静态边 + goto + fan-out；确定性由 `triggers` / `concurrency_group` 字段顺序承载（标准触发源 `index = -1`；到达顺序不保证） | FR-011 / FR-013 · SC-008 |
| 并发组 / 屏障组统一暴露 | FR-012 / FR-014 · SC-009 |
| `stream()` 与 span 共享 `run_id` / `thread_id`；invoke 由注入点优先绑定、L2 为 fallback，每次注入运行恰一次有效绑定 | FR-010 · SC-007 |
| 接收端 **`Exception`** 隔离（含可选记录回调）；`BaseException` 不吞 | FR-017 · SC-010 |
| 不扩 L1 / 门面 / `runtime.__all__`；L5 入口不进 facade | FR-018 / FR-019 |
| `Span.context` 不承载 C21 `context` | FR-016 |

> **无 NEEDS CLARIFICATION**：spec 的 7 条澄清已收敛全部未决点；本 plan 只落实现方法。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith / 零出站 / 零环境变量） | 零新增依赖；无 env / 网络；G24 / G26 / G27 | 通过 |
| 原则 II（零 LangChain · 状态语义等价） | 不 import `langchain*` / `langgraph*` / `langsmith`；C4 / C8 回归保持 | 通过 |
| 原则 III（验收契约优先 · `target.py` 只读） | `target.py` **零改动**；`compile()` 无参仍可调用 | 通过 |
| 原则 IV（可诊断性 · 可视化不阻断） | 记录 / 回调失败均不阻断图执行；push 失败可丢弃 | 通过 |
| 原则 V（人工验收） | `harness/verification/B19F1/manual-verification.md` + 零出站证据 | 计划交付（真实模型轮偏离见 R-9） |
| 原则 VI（规格驱动 · 判据级覆盖） | spec FR-001…FR-021 / SC-001…SC-017 · tasks 追溯（/speckit.tasks） | 通过 |
| 原则 VII（职责边界 · C23 / C24） | `TraceSink` / `current_span` 落地；C27 仍归 B20 | 通过 |
| 原则 VIII（证据与术语） | spec P-01…P-10 / E-1…E-3 + `路径:行号`；`get_current_run_tree` 对应已标注 | 通过 |
| 原则 IX（许可证 / 商标） | 零新增依赖 ⇒ `THIRD_PARTY_NOTICES` 零变更 | 通过 |
| 原则 X（署名头 / 文档） | 新源文件带署名头；`harness/demo/README.md` 形态更新 | 通过 |
| 原则 XI（上游优先） | 上游无自有 `TraceSink` / `current_span` ⇒ 自研区 ③；`get_current_run_tree` 对应已实测 | 通过（X-1…X-5） |
| 原则 XII（最优设计 / 零重复载体） | 复用 `SpanProducer`；记录与 `Span` 分离；不另立运行时依赖 | 通过 |
| 立项书 **ARCH-1**（单向依赖） | ⚠️ **R-1**：L3 `_stategraph.py` 在 tracer 注入 / 屏蔽时**局部 import** L5 `_inject`；同步更新 `立项书 §5.1` / `spec §5` / `layer-registry.md` / `gate_G25_import_graph.py` | ✅ **已获发起者一次性追认（2026-11-21）** |
| 立项书 **ARCH-2**（顶层惰性） | `import freegraph` 不加载 L5 / `_stategraph` | 通过 |
| 立项书 **ARCH-3**（跨层只经协议 + 纯数据） | ⚠️ **R-2**：L5 `_inject` 仅绑定 L2 私有 `_span_hook`；**不读** `_stream_context` | ✅ **已获发起者一次性追认（2026-11-21）** |
| B18F1 的「L5 只 import 标准库 + L1」断言 | **拆分而不删**：纯模块保持；`_inject.py` 走 R-2 | ⚠️ **测试拆分** |
| **L1 配置冻结面 / 纯数据纪律** | `RunConfig` 不装 `TraceSink`（9 字段冻结）；记录是 L5 自有数据类型 | 通过 |

### 登记例外（Phase 0 裁决 · 必须写入 verification 追认）

| # | 被偏离条款 | 内容 | 为什么必须 | 更简替代及拒绝理由 |
|---|---|---|---|---|
| **R-1** | 立项书 **ARCH-1**（高层可 import 低层，反向禁止） | `src/freegraph/_stategraph.py`（L3）**局部 import** `freegraph.observability._inject`（L5），**仅在** `tracer is not None` 或「需屏蔽外层 tracer」时执行 | spec 已锁定公开形态 = `compile(tracer=...)`；L3 必须能进入 L5 的 run scope 才能构造 / 绑定 `SpanProducer`。L3 → L5 是**唯一**能让锁定形态落地的接缝。**已获发起者一次性追认（2026-11-21）**；同步更新 `立项书 §5.1` / `spec §5` / `layer-registry.md` / `gate_G25_import_graph.py`。 | ① 把公开形态改为 L5 包装器 / 上下文管理器 ⇒ 违反 spec FR-001 的「写死」；② 把 `SpanProducer` 下移到 L2 ⇒ 破 B18F1 的分层与 L5 归属；③ 在 L3 重写 producer ⇒ 违反 D-1「MUST NOT 重新实现 span 生产」 |
| **R-2** | 立项书 **ARCH-3**（跨层只经 Protocol + 纯数据） | `src/freegraph/observability/_inject.py`（L5）**仅**绑定 L2 私有 `_span_hook.bind_span_tracer`；**不读** `_stream_context`（run_id / thread_id 由节点 start `Span` 继承） | D-1 要求**同一个** `SpanProducer` 同时绑定 L2 与 L5；producer 在 L5，L2 hook 是唯一节点接缝。**已获发起者一次性追认（2026-11-21）** | ① 把双绑定放进 L2 ⇒ L2 需 import L5（反向更严重）；② 在 L3 重写 producer ⇒ 同 R-1 ③；③ 把 producer 下移 L1/L2 ⇒ 破 B18F1 设计 |
| **R-3** | B18F1 的「L5 只 import 标准库 + L1」**已交付断言** | 拆分为「纯模块断言」+「`_inject.py` 例外断言」；**不删**原断言 | 双绑定必须让 L5 读 / 绑 L2 私有 hook（R-2）。**已获发起者一次性追认（2026-11-21）** | 保留原断言 ⇒ 本 feature 无法实现；删除 ⇒ 违反「拆分而不删」 |

> **红线**：R-1 / R-2 只覆盖 **tracer 接线**：R-1 仅允许 `_stategraph.py` → `observability._inject`；
> R-2 仅允许 `observability._inject` → `runtime._span_hook`（`bind_span_tracer`）；**不**允许读 `runtime._stream_context`。
> **MUST NOT** 扩展为「任意 L3 → L5」或「任意 L5 → L2 私有依赖」的通行证。

### Post-Design Re-check（Phase 1 后）

| 检查 | 结果 |
|---|---|
| L1 符号面仍 22 / 门面仍 8 / `runtime.__all__` 不变 | ✅（本 feature 只新增 L5 模块符号） |
| `import freegraph` 仍只加载 `freegraph` | ✅（L5 仅在注入 / 屏蔽时局部 import） |
| `compile()` 无参可调用 | ✅（`tracer` 是 keyword-only 可选） |
| `Span` / `TraceSink` / `RunConfig` / `SuperStepResult` / `PregelTask` 零改动 | ✅ |
| 未注入且无外层 tracer ⇒ 零 L5 import / 零 producer / 零记录 | ✅（run scope 直接跳过） |
| 依赖闭包为空 / 零 env / 零出站 | ✅（只标准库 + L1；L2 私有 hook 不引入第三方） |
| 上游差分组 D-301…D-310 有落点 | ✅（见 contracts/upstream-parity.md；**P-09 ↔ D-310 ↔ X-5**、**P-10 ↔ D-309 ↔ X-4**） |
| R-1 / R-2 / R-3 一次性追认（立项书 §5.1 / spec §5 / layer-registry / G25） | ✅（2026-11-21 · 发起者确认） |
| B18F1 直接绑定测试保持绿（仅 B19F1 作用域屏蔽） | ✅（T024 回归 + `_B19F1_SCOPE_ACTIVE` 标记） |
| T017 不依赖 Phase 6 record 实现 | ✅（record 断言移至 T038/T035） |
| 执行次序 = `triggers` / `concurrency_group` 字段顺序；到达顺序不断言 | ✅（D-06 / T036 / T037） |
| SC-011 以 `json.dumps(record.to_jsonable())` 判定 | ✅（2026-11-21） |
| FR-015 覆盖 `invoke()` + `stream()`；`output_state` = raw return | ✅（2026-11-21） |
| invoke `run_id`：注入点优先，B18F1 L2 fallback；每次注入运行恰一次有效绑定 | ✅（2026-11-21 第四轮） |
| B8F2 R-6 收窄：L2 读取 stream id，B19F1 不读 `_stream_context` | ✅（2026-11-21 第四轮） |
| T031 共享守卫先于 T019/T020；T027 复用同一守卫 | ✅（2026-11-21 第四轮） |
| `triggers` 统一排序键（标准项 `index = -1`） | ✅（2026-11-21 第四轮） |
| 接收端隔离仅覆盖 `Exception`；`BaseException` 不吞 | ✅（2026-11-21 第四轮） |
| B19F1 作用域优先于其内部的 B18F1 直接绑定 | ✅（2026-11-21 第四轮） |
| raw / normalized 私有承载：`_execute_node_pure_with_raw` + `_bind` 解包 | ✅（2026-11-21 第四轮） |

---

## Project Structure

### Documentation (this feature)

```text
specs/b19f1-tracesink-current-span/
├── plan.md                      # 本文件
├── research.md                  # Phase 0
├── data-model.md                # Phase 1
├── quickstart.md                # Phase 1
├── contracts/
│   ├── trace-sink-contract.md   # 注入 / run scope / current_span / 回调顺序
│   ├── trace-record-contract.md # TraceRecord / 触发源 / 并发组 / JSON 降级
│   └── upstream-parity.md       # P-01…P-10 / D-301…D-310 / X-1…X-5
├── checklists/
│   └── requirements.md
└── tasks.md                     # Phase 2（/speckit.tasks）
```

### Source Code (repository root)

```text
src/freegraph/
├── _stategraph.py               # L3：compile(tracer=) / run scope / 嵌套屏蔽
├── contracts/                   # L1：零改动（Span / TraceSink / RunConfig）
├── runtime/
│   ├── superstep.py             # L2：_run_round 采集 trigger/concurrency/barrier + record payload
│   ├── _span_hook.py            # L2：节点 span 接缝 + 可选 on_trace_record 调用
│   ├── _stream_context.py       # L2：id 载体（只读 / 复用；零改动）
│   └── _stream.py               # L2：StreamSession（零改动）
└── observability/               # L5
    ├── __init__.py              # 新增导出：current_span / TraceRecord（不进 facade）
    ├── _producer.py             # 既有（B18F1）；本 feature 新增 current_span() / wants_trace_records / on_trace_record(payload)
    ├── _record.py               # 新增：TraceRecord + json_safe + to_jsonable
    ├── _inject.py               # 新增：trace_run_scope（双绑定 / 屏蔽）
    ├── _invoke.py               # 既有：invoke_model / invoke_tool（零改动）
    └── _time.py                 # 既有：时间源（零改动）

tests/
├── observability/               # current_span / TraceRecord / JSON / 可选回调
├── runtime/                     # run scope / 双绑定 / 记录 / 屏蔽 / 中断取消
├── facade/                      # compile(tracer=...) 签名与 API 快照
├── contracts/                   # 零扩张 / 门禁 / 依赖方向 / 署名头
└── differential/
    └── test_b19f1_trace_access_parity.py   # D-301…D-310
```

**Structure Decision**: 单包库（发行名 = 导入名 = `freegraph`）。本 feature 不在仓库根新增
目录；只新增 L5 私有模块与测试文件。`harness/demo/README.md` 更新形态锁定条目。

---

## Phase 0: Research（摘要 · 详见 [research.md](./research.md)）

| # | 决策 | 理由 | 备选 |
|---|---|---|---|
| **D-01** | 注入形态 = `compile(*, tracer=...)` | spec 已锁定；`RunConfig` 纯数据不能装对象；`invoke` / `stream` 签名冻结 | 运行配置注入（拒绝） |
| **D-02** | run scope 在 L5 `_inject.trace_run_scope`；L3 局部 import | 同一 producer 双绑定 L2 + L5；L3 只能局部进入 L5 | L2 内构造 / L3 重写（拒绝） |
| **D-03** | **仅当处于 B19F1 注入作用域**（`_B19F1_SCOPE_ACTIVE`）且本产物无 tracer 时，进入 `trace_run_scope(None)` 屏蔽两层 hook；作用域外的 B18F1 直接绑定不触发屏蔽；作用域内的直接绑定按 B19F1 作用域优先被屏蔽 | FR-021：不隐式继承外层 B19F1 producer；保留 B18F1 直接绑定测试语义 | 只屏蔽 L2（L5 `current_span` 会泄漏外层）；无条件屏蔽（打红 B18F1） |
| **D-04** | 记录载荷 = L2 纯数据 dict；L5 构造 `TraceRecord` | 避免 L2 import L5；ARCH-3「协议 + 纯数据」 | L2 构造 L5 类型（拒绝） |
| **D-05** | 触发源 = `("e", source)`；fan-out = `("send", producer, index)` | 复用 B7F1 边触发源；fan-out 不是第三类调度触发源，只作 trace 标识 | 只暴露 goto / 只暴露静态边（拒绝） |
| **D-06** | 并发组 = 本轮全部 `task_id`（标准按节点名序 + fan-out 按**数值** TaskId 序）；`superstep = state.step`（0 起）；**记录到达顺序不保证** | 确定性由字段内顺序承载；与 `PregelTask.id` 前缀一致 | 完成时刻 / 声明顺序 / 到达顺序（拒绝） |
| **D-07** | 屏障组 = 已满足的**多源组**（tuple of source names） | B7F4 的组内全 / 组间任一；与触发源同源 | 只给代表源 / 组号（信息不足） |
| **D-08** | 记录在 `on_span_end` **之前**推送；仅当 `start is not None` **且接收端实现 `on_trace_record`** | FR-002 / FR-015；`current_span()` 内 = 该节点 span；不实现 ⇒ 不构造 payload | 结束后推送 / 无条件构造 payload（拒绝） |
| **D-09** | 输入 / 输出完整采集 + L5 `json_safe` 降级；`error` 保留原异常 | spec D-6 / 澄清 D；B20 可落 JSONL | 只记摘要 / 原样交 B20（拒绝） |
| **D-10** | `current_span()` = L5 模块函数，读 `current_tracer()` 栈顶 | C24；不委托 sink 的 `current_span` | 经门面导出（拒绝：门面不得 import L5） |
| **D-11** | 中断 / 取消与 span 对齐 | 有 span 就有 record；`error` = 原异常 | 只记成功（拒绝） |
| **D-12** | 上游证据钉 `langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17` | 宪法原则 XI / VIII | 沿用旧版本（拒绝） |

**无 NEEDS CLARIFICATION。**

---

## Phase 1: Design（摘要）

- **[data-model.md](./data-model.md)**：`TraceRecord` 字段 / 不变量、`TaskTraceMeta`（L2 纯数据）、
  `SpanProducer` 扩展、触发源 / 并发组 / 屏障组 / JSON 降级算法、生命周期与对齐规则。
- **[contracts/trace-sink-contract.md](./contracts/trace-sink-contract.md)**：注入形态、run scope、
  双绑定、嵌套屏蔽、`current_span`、回调顺序、可选记录回调、异常隔离、零开销。
- **[contracts/trace-record-contract.md](./contracts/trace-record-contract.md)**：记录字段与
  `task_id` / 触发源 / 并发组 / 屏障组 / `superstep` / JSON 视图 / 错误载体 / 对齐规则。
- **[contracts/upstream-parity.md](./contracts/upstream-parity.md)**：P-01…P-10、E-1…E-3、
  D-301…D-310、X-1…X-5、破冻结面清单。
- **[quickstart.md](./quickstart.md)**：可执行的端到端验证（记录型 sink、嵌套、默认关闭、
  异常、中断、流式 id、跨图独立、JSON 降级、env no-op）。

---

## Risks & Registrations

| # | 风险 / 事项 | 处置 |
|---|---|---|
| **R-1** | L3 → L5 局部 import（锁定形态的架构代价） | **已获发起者一次性追认（2026-11-21）**；登记 ARCH-1 例外；更新 `立项书 §5.1` / `spec §5` / 层注册表 + G25；只允许 `_stategraph.py` → `observability._inject`；verification 追认 |
| **R-2** | L5 → L2 私有 hook 双绑定 | **已获发起者一次性追认（2026-11-21）**；登记 ARCH-3 例外；**只允许** `_inject.py` → `_span_hook`（`bind_span_tracer`）；**不读** `_stream_context`（id 由节点 start `Span` 继承）。**B8F2 的 R-6 已相应收窄**：L2 读取同一对 id，B19F1 不再直接读取 |
| **R-3** | B18F1 的「L5 只 import L1」断言会红 | **已获发起者一次性追认（2026-11-21）**；**拆分而不删**：纯模块断言保留；`_inject.py` 单独例外断言；`test_architecture.py` 同步 |
| **R-4** | 嵌套无 tracer 会隐式继承外层 tracer | `trace_run_scope(None)` 同时屏蔽 L2 + L5，**仅当 `_B19F1_SCOPE_ACTIVE` 为真**；**B19F1 作用域优先**：作用域内的 B18F1 直接绑定也被屏蔽；作用域外的直接绑定保持绿；测试覆盖 B19F1 嵌套 + 作用域外直接绑定回归 + 作用域内直接绑定屏蔽 |
| **R-5** | 记录与 span 对齐（中断 / 取消） | `_bind` 仅在 `start is not None` **且 `tracer.wants_trace_records`** 时产 record；异常 / 中断路径先 record 再 end；测试 `record 数 == span 数` |
| **R-6** | `compile()` 新增关键字触发 API 快照 | 更新 `tests/facade/test_api_snapshot.py` 快照（更新**非**放宽）；`compile()` 无参仍可调用 |
| **R-7** | JSON 降级与 `error` 原异常的张力 | `TraceRecord.error` 保留异常对象；`to_jsonable()`（B20 落盘用）把 error 转为 `{type, message}`；**spec SC-011 已同步为 `json.dumps(record.to_jsonable())`**（2026-11-21） |
| **R-8** | 记录载荷中的内部对象（`_FanOutTask` / `Command`） | `json_safe` 一律降级为类型名 / 占位符；普通 dict/list/tuple/标量逐字保留 |
| **R-9** | 真实模型轮 | 本 feature **不需要**外部模型 provider；fake 轮 + **本地真实 `TraceSink` 轮**完成。按宪法 v1.6.0「质量门禁的分阶段落地」登记**质量门禁 5 偏离**：真实模型轮由 **B21F1** 承接；**发起者确认 2026-11-21**；MUST NOT 伪装成已通过 |
| **R-10** | 触发源 / 并发组的确定性 | 触发源按统一键 `(kind, source, index)`，标准边 / `goto` 的 `index = -1`；`concurrency_group` = 本轮**派发集**（含被派发但未启动的取消任务；其自身无 record），按「标准节点名序 + fan-out **数值** TaskId 序」；**记录到达顺序不保证**；测试重复运行 ≥3 次字段逐字一致 |
| **R-11** | `checkpoint_id` 仍为 `None` | 合法现状（B18F1 Q5）；记录字段可读；B14F1 后续补 |
| **R-12** | B8F2 **R-6** 与 B19F1 **R-2** 口径漂移 | 已收窄 R-6 为「L2 `_run_round` 读取 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`；B19F1 从节点 start `Span` 继承，不直接读取 `_stream_context`」；T013 的例外断言**只放行** `_inject.py` → `_span_hook`，**不放行** `_stream_context` |

---

## Green Baseline & Red List（宪法 v1.11.0 的基线义务）

### 基线（**2026-11-21 · 实施前实跑**）

```
.venv/bin/python -m pytest -q --tb=no
1863 passed, 6 skipped in 107.96s (0:01:47)
```

**跳过项**（均为环境 / 开关导致的既有 skip，非本 feature 相关）：
`C8` 元测试占位 · `IPython` 缺失的 PNG 用例 · `mypy` 未安装 · 上游 PNG 未开启 ·
API 快照未开启更新 · Windows 时钟精度档。

### 变红清单（**预登记** · 实测后 MUST 逐条核对）

| # | 可能变红的既有断言 | 变红原因 | 处置 |
|---|---|---|---|
| **B-1** | `tests/contracts/test_architecture.py::TestB18F1LayeringAndLaziness::test_l5_observability_imports_only_stdlib_and_l1` | `_inject.py` 为双绑定 import L2 私有 hook（R-2） | **拆分而不删**：纯模块断言保留；`_inject.py` 例外断言（R-3） |
| **B-2** | 层注册表 / G25 的 L3 → L5 方向 | `_stategraph.py` 局部 import L5 `_inject`（R-1） | 登记 `trace-wiring-L3-L5` 例外；只允许该文件 → `observability._inject` |
| **B-3** | `tests/facade/test_api_snapshot.py` | `compile()` 追加可选关键字 `tracer` | 更新快照（更新**非**放宽）；无参调用断言保持 |
| **B-4** | `tests/contracts/` 的 `freegraph.runtime.__all__` 符号数 | 若把 L2 私有 helper 加进 `runtime.__all__` | 新 helper 走 `_` 前缀私有模块 / `__all__ = []` |
| **B-5** | C4 / C8 回归 | 若 `_bind` 改动影响节点入参 / 状态 | `_bind` 只**旁路采集**，不碰 `node_input` / 返回值；未知 key 仍由 B4F1 处理 |
| **B-6** | `tests/runtime/test_stream_*` 的 `run_id` / `thread_id` | 若 invoke 的 `bind_run_ids` 覆盖 stream 绑定 / 嵌套 id | stream 路径零改动；invoke 只在注入运行内绑定；嵌套注入独立、结束恢复 |
| **B-7** | 依赖 / 环境变量 / 出站门禁 | 若引入 `opentelemetry` / `langsmith` / 读 env | 只用标准库 + L1；零 env；零出站 |
| **B-8** | B18F1 直接绑定测试：`tests/runtime/test_node_spans.py`、`test_concurrency_spans.py`、`test_span_ids.py`、`test_node_record_carriers.py`、`test_span_lifetime.py`、`tests/observability/test_zero_overhead.py::test_bound_tracer_produces_spans_for_sanity`、`tests/differential/test_b18f1_span_parity.py` 的 D-202/D-206/D-208 | 若 T027 无条件屏蔽外层 tracer，会把这些直接 `bind_producer` + `compiled.invoke()` 用例打成 0 span | **MUST 保持绿**：仅当 `_B19F1_SCOPE_ACTIVE` 为真时屏蔽；T024 增加 B18F1 直接绑定回归；**不得改写 B18F1 既有断言** |
| **B-9** | Phase 3 US1 的 record 断言 | 若 T017 在 Phase 6 之前要求 record，则 US1 无法独立变绿 | record 断言移至 T038/T035；T017 只测 span / id / stream 信封 |
| **B-10** | B7F2 / B7F3 / B8F1 / B8F2 / B23F1 的 `vars(compiled)` == 11 键断言 | 本 feature 新增私有 `_tracer` ⇒ 12 键 | **更新（非放宽）**：断言集合加入 `_tracer`、计数改 12；同步 B8F1 / B7F2 验收脚本与 B8F1 / B7F3 人工验证文字 |

> 实施前 MUST 重跑基线；若变红，先判「是否由本 feature 落地形态导致」→ 再判「是否属冻结断言」；
> **MUST NOT** 以「实现期再说」放过。**B-8 是硬约束**：不得靠修改 B18F1 测试来「修复」。

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **R-1** L3 `_stategraph.py` → L5 `observability._inject`（ARCH-1 反向） | spec 锁定 `compile(tracer=...)`；只有 L5 能构造 `SpanProducer` 并双绑定；L3 必须进入 L5 run scope。**2026-11-21 已获发起者一次性追认并登记**（立项书 §5.1 / spec §5 / layer-registry / G25） | L5 包装器 / 上下文管理器 ⇒ 违反 spec 的注入形态；producer 下移 L2 ⇒ 破 B18F1；L3 重写 ⇒ 违反 D-1 |
| **R-2** L5 `_inject.py` → L2 私有 `_span_hook`（ARCH-3 例外） | D-1 要求同一 producer 双绑定；L2 hook 是唯一节点接缝；id 由 start `Span` 继承，无需读 L2 id 载体 | 在 L2 构造 producer ⇒ L2 import L5（更严重）；L3 重写 ⇒ 重复生产；新增第二套 id 载体 ⇒ 破 D11 |
| **R-3** 拆分 B18F1 的 L5-only-L1 断言 | 上位例外 R-2 的必然结果；原断言保护「纯生产 / 纯数据」模块仍有效 | 保留原断言 ⇒ 本 feature 不可实现；删除 ⇒ 违反「拆分而不删」 |

---

## Implementation Sequencing（供 /speckit.tasks 展开）

1. **Setup / Foundational**：`TraceRecord` / `json_safe` / `SpanProducer.current_span` /
   `on_trace_record` / `_inject.trace_run_scope` / L2 payload 形状。
2. **US1（推送 + 默认关闭）**：`compile(tracer=)`、**共享守卫（T031，先于 T019/T020）**、
   invoke/stream run scope、双绑定、span 配对、异常路径（**不含 record**）。
3. **US2（嵌套 + current_span）**：`current_span()`、嵌套恢复、B19F1 作用域内跨图屏蔽、
   B18F1 直接绑定回归。
4. **US3（默认关闭零副作用）**：无注入 / 环境变量 / L5 惰性 / 零构造计数。
5. **承接义务**：`invoke()` + `stream()` 两路径的触发源 / 并发组 / 屏障组 / 中断取消 /
   输入输出（`output_state` = raw return）/ JSON 降级 / 字段顺序确定性。
6. **Polish**：差分 D-301…D-310、契约守卫、API 快照、层注册表例外、
   `harness/demo/README.md`、人工验证记录（含门禁 5 偏离登记）。

---

## Notes

- `harness/demo/target.py` **零改动**（只读基准）。
- 不新增运行时依赖、不新增 L1 / 门面 / `runtime.__all__` 符号、不新增第二套 `run_id` 载体。
- L2 只**旁路采集**记录；不改节点签名 / 状态 / `SuperStepResult` / `PregelTask`。
- `SpanProducer` 是唯一 producer；记录与 `Span` 分离；`Span.context` 恒空（C21 `context` 不进入）。
- 人工验证记录：`harness/verification/B19F1/manual-verification.md`（fake + 本地真实 sink + 零出站证据 + **R-1/R-2/R-3 一次性追认（日期）** + **质量门禁 5 偏离登记（日期）**）。
