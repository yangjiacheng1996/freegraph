# Implementation Plan: B18F1 · Span 数据类生产（节点 / 工具 / 模型三级 span）

**Branch**: `b18f1-span-production`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`
⇒ 无 `before_plan` 钩子；既有 feature 同样在 `main` 上开发）
| **Date**: 2026-11-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b18f1-span-production/spec.md`

**Feature ID**: `B18F1`（M3 可诊断 · **第 23 个** · 前置：**B7F3**；
承接 **B2F1 / B7F3 / B8F2 / B8F3 / Q6 / Q8-D11**；本 feature 完成后解锁 **B19F1**）

> **范围提醒（2026-11-20 用户拍板）**：B18F1 **只生产** span，不接入 `TraceSink`、不实现
> `current_span()`、不落盘、不导出 OTLP。`Span` 的 11 字段面归 **B2F1**，本 feature
> **MUST NOT** 增删字段。模型 / 工具元数据取**极简集**（Q9）；节点 span 属性**恒为空映射**
> （Q11）；`Span.context` **恒为空映射**（Q15）；v1 **只支持同步** `invoke`（Q16）。

---

## Summary

交付 freegraph 的 **span 生产行为**：节点 span 自动产生；模型 / 工具 span 由显式的
`invoke_model` / `invoke_tool` 一次性调用辅助产生；未绑定生产接收端时零 span、零回调、零环境变量。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **L2 节点 span 接缝** | 每次节点任务执行前后产生节点 span | 单一接缝 · 不改节点签名 / 状态 / `SuperStepResult` / `PregelTask` |
| **L5 生产引擎** | `SpanProducer` 管理当前 span 栈、父子关系、接收端转发 | L5 只 import 标准库 + L1；`run_id` / `thread_id` 从当前节点 span 继承 |
| **L5 调用辅助** | `invoke_model` / `invoke_tool` | 鸭子类型校验 · 形状错配 `TypeError` · awaitable `TypeError` · 节点外透传 |
| **关联键** | `thread_id` / `run_id` / `node` / `checkpoint_id` | `run_id` 非空；`thread_id` 来自 `RunConfig`；`checkpoint_id` 可为 `None`（模型 / 工具 span 从节点 span 继承） |
| **属性面** | 模型 / 工具 `gen_ai.*` 极简集；节点空映射 | `error.type` 在模型 / 工具失败时 MUST 出现 |
| **原则 IV 载体** | 节点名 / 耗时由节点 span；输入 / 输出 / 错误由 `stream()` 的 `values`/`updates`/`tasks` + `PregelTask.result` + 原样抛出的异常 + B19F1/B20 承接 | 节点 span 不扩属性；`invoke()` 逐节点三项归 B19F1/B20 且 MUST 写死承接机制（R-7） |
| **零开销** | 未绑定接收端 ⇒ 零 span / 零回调 | 一次廉价守卫；不生成 span 专用运行 id（`stream()` 事件 id 不属 span 生产）；不读环境变量 |
| **差分场景** | D-201…D-208 | SAME 行为面 5 / 纯 DIFF 1 / STRICTER 2（D-202/203/208 同时含表示层 DIFF）；上游缺席即 skip |
| **人工门禁** | `harness/verification/B18F1/manual-verification.md` | fake + 真实轮（或登记偏离）· 零出站证据 |

**技术方案（关键落点）**：

| 环节 | 落点 |
|---|---|
| 节点执行接缝 | `src/freegraph/runtime/superstep.py:1361-1368` 的 `_run_round._bind._inner` |
| 新增 L2 私有 hook | `src/freegraph/runtime/_span_hook.py`（`__all__ = []`）· 绑定 / 读取 tracer、构造节点 Span |
| 运行 id 复用 | `src/freegraph/runtime/_stream_context.py:91-144` 的两个既有 contextvar；**新增** `bind_run_ids()` 私有助手 |
| invoke 路径 id 绑定 | `src/freegraph/runtime/superstep.py:2239-2255` 的 `run_graph`：仅在 tracer 已绑定且当前无 id 时绑定一次 |
| stream 路径 id 绑定 | `src/freegraph/runtime/_stream.py:110-118` 的 `StreamSession.__enter__`（**零改动**，复用既有 `bind_stream`） |
| 新增 L5 包 | `src/freegraph/observability/`：`_producer.py` / `_invoke.py` / `__init__.py` |
| 当前 span 栈 | L5 `SpanProducer` 的 run-scoped `ContextVar[tuple[_SpanFrame, ...]]` |
| 时间源 | 标准库 `time.time_ns()` + UTC ISO-8601（9 位小数）· 保证 end > start |
| 接收端 | 鸭子类型 `on_span_start` / `on_span_end`；B19F1 的 `TraceSink` 可直接对接 |
| 零新增公开面 | `freegraph.runtime.__all__` 不变；`freegraph.graph` 门面不变；L1 契约符号不变 |

**零新增**：运行时依赖 · 公开 L1/L2/门面符号 · 错误类型 · 公开关键字。
**破冻结面**：**无**。本 feature 不修改 `Span` / `TraceSink` / `RunConfig` / `SuperStepResult` /
`PregelTask` / `stream()` 信封 / 节点签名。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`requires-python = ">=3.11"`）；
允许 `contextvars` / `dataclasses` / `time` / `uuid` / `inspect` / `logging` / `typing`。
**MUST NOT** 使用 3.12+ 的 `TypeAliasType` / `override` / `TypeIs` / PEP 695 `type`。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []`）。
开发期：`pytest`（既有 `dev`）· 差分：`langgraph==1.2.11`（既有 `differential` 组）。
`pyproject.toml` **零改动** ⇒ G3 / G21 / G22 / G23 恒绿。

**Storage**: N/A（本 feature 不落盘；trace 存储归 B20F1 / B20F2）。

**Testing**: pytest —— `tests/runtime/`（L2 节点接缝 / 零开销 / 父子栈）·
`tests/facade/` 或 `tests/observability/`（`invoke_model` / `invoke_tool` 公开可 import 的行为）·
`tests/contracts/`（属性 / JSON / 公开面 / G3 依赖闭包 / G7 公开面）· `tests/gates/`（G21–G30 环境变量等）·
`tests/differential/test_b18f1_span_parity.py`（D-201…D-208）·
`tests/runtime/test_acceptance_script.py`（验收脚本回归）。

**Target Platform**: Linux / macOS / Windows · CPython 3.11+ · 零出站。

**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A（不设墙钟预算）** —— 未绑定接收端时只做一次 contextvar 读取 +
`is None` 判断；不引入 I/O / 网络 / 线程池。MUST NOT 用耗时做断言（CI 假红）。

**Constraints**（主要来自 spec 的 MUST 条目）：

| 约束 | spec 条目 |
|---|---|
| 只依赖标准库；MUST NOT import `langchain*` / `langgraph*` / `langsmith` / `opentelemetry-*` | FR-019 |
| 零出站 / 零环境变量 / 导入无副作用 | FR-020 |
| `Span` 11 字段逐字不改 | FR-001 · H-1 |
| 未启用生产 ⇒ 零 span / 零回调 / 不生成 span 专用运行 id | FR-002 · SC-003 |
| 节点 span 每次任务执行一个；不改签名 / 状态 / 结果字段 | FR-004 |
| 模型 / 工具 span 只能经 `invoke_model` / `invoke_tool` 产生 | FR-005 / FR-006 |
| 形状不匹配 ⇒ `TypeError`；awaitable ⇒ 结束 span + `TypeError` | FR-006 / FR-028 · Q14 / Q16 |
| 父子关系用父 span 的 `id` 字符串；嵌套逐层 | FR-007 |
| 时间严格正耗时；UTC ISO-8601；标准库 | FR-009 · SC-005 |
| 异常原样重抛；开始 / 结束成对 | FR-010 · SC-007 |
| 四项关联键可读；`run_id` 非空；`thread_id` 来自 `RunConfig` | FR-011 · SC-006 |
| `stream()` 与 span 共享同一 `run_id` / `thread_id` | FR-012 · H-3 |
| 模型 / 工具属性只写 Q9 最小集；节点属性恒空；`error.type` 在模型 / 工具失败时 MUST 写 | FR-013 / FR-017 / FR-018 · SC-001 |
| `Span.context` 恒空映射 | FR-023 · SC-011 |
| L5 只 import 标准库 + L1；**零 L2 import**；`run_id` / `thread_id` 从节点 span 继承 | FR-021 / ARCH-3 |
| 不扩大公开门面 / L1 契约符号；`import freegraph` 不加载 L5 | FR-022 · SC-012 |
| 并发任务各自独立 span 栈；沿用 B8F2 的 `copy_context()` | FR-024 · SC-010 |
| 接收端异常隔离；不改变图执行结果 | FR-025 |
| 不实现 `TraceSink` 注入 / `current_span()` / 存储 / OTLP / UI | FR-026 |
| 只支持同步 `invoke` | FR-028 · Q16 |
| 原则 IV 的输入 / 输出 / 错误由组合载体承担；节点 span 只承担节点名 / 耗时 | FR-029 · SC-016 · R-7 |

> **无 NEEDS CLARIFICATION**：spec 的 Q1–Q16 已收敛全部设计决策；本 plan 只落实现方法。

---

## 绿基线记录（宪法 v1.11.0 的基线义务）

### 基线（**2026-11-20 · 实施前**）

```
.venv/bin/python -m pytest -q --tb=no
1778 passed, 6 skipped in 121.56s (0:02:01)
```

**跳过项**（均为环境 / 开关导致的既有 skip，非本 feature 相关）：
`C8` 元测试占位 · `IPython` 缺失的 PNG 用例 · `mypy` 未安装 · 上游 PNG 未开启 ·
API 快照未开启更新 · Windows 时钟精度档。

### 变红清单（**预登记** · 实测后 MUST 逐条核对）

| # | 可能变红的既有断言 | 变红原因 | 处置 |
|---|---|---|---|
| **B-1** | `tests/facade/test_api_snapshot.py` 的公开面快照 | 若误把 `invoke_model` / `invoke_tool` 加进 `freegraph.graph` 门面 | **MUST NOT** 加门面；新增符号只在 L5 模块 |
| **B-2** | `tests/contracts/` 的 `freegraph.runtime.__all__` 符号数 | 若把 L2 hook 的符号加进 `runtime.__all__` | hook 是 `_` 前缀私有模块 · `__all__ = []` |
| **B-3** | `tests/contracts/test_architecture.py` 的 import 图 | 若 L2 import L5 或 L5 import L2 业务模块 | L2 只经鸭子类型 hook；L5 零 L2 import |
| **B-4** | `tests/runtime/test_stream_*` 的 `run_id` / `thread_id` 断言 | 若 invoke 路径的 `bind_run_ids` 覆盖已有 stream 绑定 | **只在当前 `run_id is None` 时绑定**；stream 路径零改动 |
| **B-5** | C4 / C8 回归 | 若节点接缝改了入参 / 状态 | 接缝只包 `fn()`，**不碰** `state` / `node_input` |
| **B-6** | 依赖 / 环境变量门禁 | 若引入 `opentelemetry` / `langsmith` / 读 env | 只用标准库 + L1；无 env 读取 |

> 实施前 MUST 重跑基线；若变红，先判「是否由本 feature 的落地形态导致」→ 再判「是否属冻结断言」；
> **MUST NOT** 以「实现期再说」放过（宪法 v1.11.0）。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith / 零出站 / 零环境变量） | 零新增依赖 · 无 env 读取 · 无网络；G24 / G26 / G27 | 通过 |
| 原则 II（零 LangChain · 状态语义等价） | 不 import `langchain*` / `langgraph*`；C4 / C8 回归保持 | 通过 |
| 原则 III（验收契约优先 · `target.py` 只读） | `target.py` **零改动**；验收走既有 `graph_core.py` / `acceptance.py` | 通过 |
| 原则 IV（可诊断性 · 可视化不阻断） | 生产失败 / 接收端异常均不阻断图执行；原则 IV 的字段由组合载体承担（节点 span + `stream()`/`PregelTask` + B19F1/B20） | 通过（见 R-7） |
| 原则 V（人工验收） | `harness/verification/B18F1/manual-verification.md` + 零出站证据 | 通过（计划交付；见 R-3） |
| 原则 VI（规格驱动 · 判据级覆盖） | spec FR-001…FR-029 / SC-001…SC-016 · tasks 追溯 | 通过（tasks 落地） |
| 原则 VII（职责边界 · C23 / C24） | C23 字段约定落地；C24 仍归 B19F1；active = C1–C24 + C26–C27 | 通过 |
| 原则 VIII（证据与术语） | `research.md` E-1…E-4 + 上游 `路径:行号`；semconv 出处逐条附 | 通过 |
| 原则 IX（许可证 / 商标） | 零新增依赖 ⇒ `THIRD_PARTY_NOTICES` 零变更 | 通过 |
| 原则 X（署名头 / 文档） | 新源文件带署名头；属性对照表落文档 | 通过 |
| 原则 XI（上游优先） | 上游无自有 `Span` ⇒ 自研区 ③；默认关闭 / 父子 / 失败成对与上游 SAME | 通过（X-1…X-4 已登记） |
| 原则 XII（最优设计 / 零重复载体） | 单一 `Span` 数据类 · 单一 `run_id` 载体 · 单一当前 span 栈 | 通过 |
| 立项书 ARCH-1（单向依赖） | L2 `_span_hook` 不 import L5；L5 `observability` 不 import L2 业务模块 | 通过（见 R-1） |
| 立项书 ARCH-2（顶层惰性） | `import freegraph` 不加载 `freegraph.observability` / `runtime._span_hook` | 通过 |
| 立项书 ARCH-3（跨层 Protocol + 纯数据） | L2 ↔ L5 只经 `Span`（L1）+ 鸭子类型 tracer；L5 零 L2 import | 通过（见 R-1） |
| 运行时基线（3.11 · typing 上限） | Technical Context 逐项 ≤ 3.11 · G9 | 通过 |
| 依赖白名单 / 黑名单 | 零新增运行时依赖 | 通过 |
| 跨 feature 承接（v1.8.0） | H-1…H-7；D-1…D-6；B19F1 的双绑定说明（R-4）· 目标提示词已接线 | 通过（B14F1/B19F1/B20F1/B20F2/B21F1 提示词已补承接段） |
| 质量门禁 3 / 4 / 5 | C4 / C8 回归保持；fake 轮 + 真实轮 / 偏离登记；人工记录 | 通过（见 R-3） |
| 发布门禁 | 不接入（B24F1）；新增代码在 `src/` · 零依赖 | 通过 |

### 登记项 R-1（**零 L2 import** · 不使用 ARCH-3 例外）

**背景**：B8F2 的 **D-3 / H-9** 为 **B18F1 / B19F1** 登记了只读
`_STREAM_RUN_ID` / `_STREAM_THREAD_ID` 的 ARCH-3 例外（`specs/b8f2-stream-modes/spec.md`
§FR-027 / §ARCH-3 例外；2026-11-20 发起者授权）。

**B18F1 的取舍**：本 feature **不使用**该例外——L5 `observability` **零 L2 import**；L2 `_span_hook.py`
定义私有 `typing.Protocol` `_SpanTracer`（`on_span_start` / `on_span_end` / `current_span_id`），
L5 `SpanProducer` 结构化满足它但 **MUST NOT import** 它：

- L2 `_span_hook` 从 `_stream_context.current_stream_ids()` 读取两个 id，写入节点 `Span`；
- L5 生产者 / helpers 从**当前节点 span**（`Span.run_id` / `Span.thread_id` / `Span.node`）
  继承这些值，**不直接读 L2**；
- 因此 L5 只 import 标准库 + L1；B8F2 的例外留给 **B19F1**（若其需要）；
- **MUST NOT** 扩展为任意 L5 → L2 私有依赖；**MUST NOT** 把 trace 数据塞进 `stream()` 信封；
  **MUST NOT** 新增第二套 id 载体。

### 登记项 R-2（**B8F2 私有模块的兼容扩展** · `bind_run_ids`）

**问题**：`invoke()` 路径当前没有绑定 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`；B18F1 的
invoke span 需要非空 `run_id`。

**处置**：在 `src/freegraph/runtime/_stream_context.py` **新增私有助手** `bind_run_ids(run_id, thread_id)`
（`__all__` 仍为空），**只**设置既有两个 contextvar；`run_graph` 仅在
「tracer 已绑定 **且** 当前 `run_id is None`」时使用它。

**不破冻结面的论证**：
- `StreamSession` 仍通过既有 `bind_stream` 绑定（B8F2 FR-027 逐字满足）；
- `bind_run_ids` 是 **L2 私有模块的新私有符号**，不进 `__all__`、不进 API 兼容矩阵；
- **不新增第二套载体**：两个 contextvar 与 stream 路径完全相同；
- `run_id` 仍由运行时生成、用户不可设置 / 覆盖；`RunConfig.run_id` 仍被忽略。

**同步**：更新 `_stream_context.py` 的模块 docstring 注记——`bind_stream` 仍是 `StreamSession` 的唯一绑定入口；`bind_run_ids` 是 B18F1 invoke 路径的私有助手（只设置两个 id，不碰 writer / sink / capture）。

**spec 同步**：spec §5 已由“只读”订正为“**stream 路径只读、invoke 路径经 `bind_run_ids` 绑定同一对 contextvar**”，与 FR-012 / Q4 一致；不新增第二套载体。

**追认**：不需破冻结面追认；只需在 `research.md` / `data-model.md` 记录该私有扩展。

### 登记项 R-3（**质量门禁 5 的「真实模型轮」** · 可能偏离）

**问题**：B18F1 是**通用 span 生产**，不依赖任何模型 provider；本机无外部模型凭据。

**处置**：
- **fake 轮**（必跑）：用真实自由对象（非测试替身）验证节点 / 模型 / 工具 span 的完整生命周期；
  用计数接收端验证零开销；
- **真实轮**：优先用**真实本地对象**（真实实现了 `invoke` 的类，而非 `Mock`）；若审查要求
  **外部模型 provider 轮**，则按宪法 v1.6.0「质量门禁的分阶段落地」登记偏离 + 发起者追认，
  承接方 **B21F1**（真实 OTLP 后端对接），**MUST NOT** 伪装成已通过。

**红线**：不影响依赖 / 环境变量 / 零出站 / 许可证四条红线；红线照常执行。

### 登记项 R-4（**B19F1 的双绑定接缝** · 只接线）

B18F1 的 **tracer（= `SpanProducer`）** 需要同时被 **L2 节点接缝**与 **L5 调用辅助**看到：
- L2 通过 `runtime._span_hook.bind_span_tracer(tracer)` 绑定；
- L5 通过 `observability._producer.bind_tracer(tracer)` 绑定（私有）。
- B18F1 的测试夹具自行绑定两处；**B19F1 的公开注入点 MUST 构造 `SpanProducer`（接收端 = 用户 `TraceSink`），并把同一个 `SpanProducer` 同时绑定两处**（B19F1 可 import 两层；B18F1 不代做公开注入）。这是 B19F1 的承接接线，**MUST NOT** 新增门禁编号；绑定 MUST 是 run-scoped（作用域结束即失效，FR-003 / T059）。
- **接线落点**：`harness/features/B19F1_TraceSink与current_span.md` 的「下游承接（B18F1 → 本 feature）」段；spec **D-1**；tasks **T057**。

### 登记项 R-5（**公开面零扩张**）

- 不新增 `freegraph.graph` 门面符号；
- 不新增 `freegraph.runtime.__all__` 符号；
- 不新增 L1 契约符号；
- `invoke_model` / `invoke_tool` / `SpanProducer` 只在 `freegraph.observability` 模块内；
  **是否由 B19F1 再导出**归 B19F1。

### 登记项 R-7（**原则 IV 的字段载体组合** · 只接线）

**问题**：宪法原则 IV 要求每次节点执行的可观测记录含节点名、输入状态、输出状态、耗时、错误；
B18F1 的节点 span 按 Q11/Q12 固定空属性且不写 `error.type`。

**处置**：不为 B18F1 扩节点 span 属性；按「组合载体」闭合：

| 字段 | B18F1 | 既有 / 下游 |
|---|---|---|
| 节点名 | 节点 span `name` / `node` | `PregelTask.name` |
| 耗时 | 节点 span `start_time` / `end_time` | — |
| 输入状态 | **不写**（Q11） | `stream_mode="values"` step 前状态 + B19F1/B20 |
| 输出状态 | **不写**（Q11） | `updates` / `tasks` + `PregelTask.result` + B19F1/B20 |
| 错误 | **不写**（Q12）；模型 / 工具 span 失败时 MUST 写 `error.type` | 原样抛出的异常（+ `add_note`）/ B19F1/B20；`PregelTask.error` 仅非抛出快照可见 |

**承接**：`invoke()` 路径的逐节点输入 / 输出 / 错误由 **B19F1 / B20** 提供等价 trace record；
B19F1/B20 的 spec MUST 落成该承接，并 **MUST 写死承接机制**：B19F1 MUST 通过 L2 既有节点接缝
（或其扩展 hook）捕获 `(node, input_state, output_state, error)`，或 B20 MUST 从 `PregelTask` / `SuperStepResult`
快照取等价记录。B18F1 只承诺 `stream()` 路径的既有载体可还原 + 节点 span 的
节点名 / 耗时。**接线落点**：`harness/features/B19F1_TraceSink与current_span.md`、
`harness/features/B20F1_本地Trace存储JSONL.md`、`harness/features/B20F2_Trace查询API与SQLite后端.md`
的承接段；tasks **T057 / T058**。

---

## Project Structure

### Documentation (this feature)

```text
specs/b18f1-span-production/
├── plan.md                         # 本文件
├── spec.md                         # 权威 spec（Q1–Q16 已收敛）
├── research.md                     # Phase 0：决策 + 上游实测 + 代码锚点
├── data-model.md                   # Phase 1：实体 / 生命周期 / 不变量 / 验证矩阵
├── quickstart.md                   # Phase 1：可执行验证指南
├── contracts/
│   ├── span-production-contract.md # L2 节点接缝 + L5 生产者 / 接收端
│   ├── invoke-helpers-contract.md  # invoke_model / invoke_tool 行为面
│   └── upstream-parity.md          # P / E / D / X 对照
├── checklists/requirements.md      # 规格质量清单
└── tasks.md                        # Phase 2 输出（/speckit.tasks 生成，本命令不创建）
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/
│   ├── trace.py                    # Span / TraceQuery（B2F1 冻结 · 零改动）
│   └── types.py                    # RunConfig（零改动）
├── runtime/
│   ├── _span_hook.py               # 新增：L2 私有 hook（绑定 tracer / 构造节点 Span）
│   ├── _stream_context.py          # 改：新增私有 bind_run_ids()；既有 bind_stream 不动
│   ├── superstep.py                # 改：_run_round._bind 包节点执行；run_graph 绑定 invoke id
│   ├── _stream.py                  # 零改动（StreamSession 已绑定 id）
│   ├── _concurrency.py             # 零改动（既有 copy_context）
│   └── __init__.py                 # __all__ 不变
├── observability/                  # 新增 L5 包（不进 freegraph/__init__.py）
│   ├── __init__.py                 # invoke_model / invoke_tool / SpanProducer
│   ├── _producer.py                # 当前 span 栈 / 父子 / 接收端 / 时间 / id
│   ├── _invoke.py                  # 鸭子类型校验 / awaitable / 节点外透传
│   └── _time.py                    # UTC ISO-8601 · 严格正耗时（标准库）
└── __init__.py                     # 零改动（仍不 import L5）

tests/
├── observability/
│   ├── conftest.py                 # RecordingReceiver / FailingReceiver / 构造计数 / bound_tracer
│   ├── test_invoke_helpers.py      # 形状 / awaitable / 节点外 / 属性 / 返回值
│   ├── test_producer.py            # 当前 span 栈 / 父子 / 接收端异常隔离
│   ├── test_span_attributes.py     # 允许清单 / asdict JSON / 节点空映射
│   └── test_zero_overhead.py       # 未绑定 ⇒ Span 构造数 == 0 / 回调数 == 0
├── runtime/
│   ├── test_node_spans.py          # 节点 span / 异常成对
│   ├── test_concurrency_spans.py   # 并发父子 / 跨任务不串父（T041）
│   ├── test_node_record_carriers.py # 原则 IV：stream 载体可还原输入 / 输出 / 错误（T055）
│   ├── test_span_ids.py            # run_id / thread_id 同源 / invoke id
│   ├── test_span_lifetime.py       # run-scoped 生命周期（T059）
│   └── test_no_env_reads.py        # 环境变量守卫
├── contracts/
│   ├── test_architecture.py        # 既有 G3 / G7 依赖闭包 / 公开面守卫（复用）
│   ├── test_trace_carrier_contract.py # 原则 IV 载体映射 / B19F1/B20 承接文档守卫（T056）
│   └── test_downstream_wiring.py   # 目标提示词承接段守卫（T058）
└── differential/
    ├── parity_probe.py             # 既有差分组
    └── test_b18f1_span_parity.py   # B18F1 D-201…D-208

harness/
├── demo/
│   ├── graph_core.py               # 可加一个 span 生产验收场景（不改 target.py）
│   └── acceptance.py               # 覆盖描述按需同步
└── verification/
    └── B18F1/
        ├── acceptance.py           # 新增：一键验收 A1–A7
        └── manual-verification.md  # 新增：fake / 真实轮 + 零出站 + 偏离登记
```

**Structure Decision**：单项目库（`src/` + `tests/` + `harness/`）。
- `runtime/_span_hook.py` 属 **L2 私有**（`__all__ = []`），不进 `freegraph.runtime.__all__`；
- `observability/` 属 **L5**，模块内符号可 import，但 **MUST NOT** 进 `freegraph.graph` 门面；
- `freegraph/__init__.py` **零改动** ⇒ `import freegraph` 不加载 L5（ARCH-2）；
- 无新子包进入发行元数据（仍是同一个 `freegraph` 包）。

---

## Complexity Tracking

| 复杂度 | 为什么需要 | 更简单的替代为什么被拒绝 |
|---|---|---|
| 新增 L2 `_span_hook.py` | 节点执行在 L2；L2 **不能** import L5（ARCH-1）；需要中立 hook 让 L5 绑定 tracer | 让 L2 直接 import L5 ⇒ 反向依赖；让 L5 包住节点函数 ⇒ 需改 `_stategraph` / 节点签名，且 L2 仍要调用 L5 |
| 新增 L5 `observability/` 包 | 用户可 import 的 `invoke_model` / `invoke_tool` 属 L5；生产者 / 时间 / 属性逻辑集中 | 全部塞进 L2 ⇒ 用户 API 落错层；全部塞进门面 ⇒ 破公开面冻结 |
| 双绑定（L2 hook + L5 tracer） | 两层都需看到同一个 tracer，但 L2 ↔ L5 不能互相 import 业务模块 | 单一全局变量 ⇒ 破层纪律；把 tracer 放进 `RunConfig` ⇒ 改冻结字段 / 引入配置面 |
| `bind_run_ids()` 私有助手 | invoke 路径没有 stream 会话，但 span 需要非空 `run_id` | 在 invoke 里另生成一套 id ⇒ 违反「单一载体」；复用 `bind_stream` ⇒ 会意外绑定 stream writer / custom sink |
| 当前 span 栈放 L5 | 父子关系 / 嵌套 / 并发隔离都属生产者语义；L2 只负责节点边界 | 放 L2 ⇒ L5 辅助函数还要读 L2 业务栈（违反 FR-021）；放 L1 ⇒ 契约层带行为 |
| 时间 / id 的 L2 / L5 各一份小助手 | L2 造节点 Span、L5 造模型 / 工具 Span，且两层不能共享业务模块 | 把时间 / uuid 塞进 L1 ⇒ 契约层带行为；L5 import L2 时间助手 ⇒ 违反 FR-021 |

---

## Phase 0: Outline & Research

**输出**：[research.md](./research.md)

已解决的关键未知点（无 `NEEDS CLARIFICATION`）：

| # | 未知点 | 结论 | 依据 |
|---|---|---|---|
| **D-01** | 节点 span 在哪一层产生 | **L2 `_run_round._bind`** 的单一节点执行接缝 | `superstep.py:1361-1368`；L2 不能 import L5 |
| **D-02** | L2 与 L5 如何解耦 | L2 私有 `_span_hook` + 鸭子类型 tracer；L5 提供 tracer 实现 | ARCH-1 / ARCH-3；spec FR-021 |
| **D-03** | 当前 span 栈放哪 | **L5 `SpanProducer` 的 ContextVar** | 父子 / 嵌套 / 并发归生产者；L2 只报节点边界 |
| **D-04** | invoke 路径 `run_id` | **`run_graph` 仅在 tracer 已绑定且无 id 时绑定一次** | spec Q4 / FR-012；`_stream_context.py` 既有载体 |
| **D-05** | checkpoint_id | v1 **恒 `None`**（不伪造）；节点 span 接受运行期值，模型 / 工具 span 从节点 span **继承** | spec Q5 / D-4；B14F1 后续补节点 span |
| **D-06** | 时间源 / 正耗时 | **`time.time_ns()` + UTC ISO-8601（9 位小数）**；end_ns = max(end_ns, start_ns + 1) | 标准库；spec FR-009 |
| **D-07** | 模型 / 工具属性 | **Q9 极简集**：operation（模型**恒 `chat`**）+ request.model / tool.name + tool.call.id | spec Q9 / FR-016；semconv 允许清单 |
| **D-08** | 节点属性 / context | **恒空映射** | spec Q11 / Q15 |
| **D-09** | error.type | 仅模型 / 工具失败；值 = `type(exc).__name__` / `_OTHER` | spec Q12 / FR-018 |
| **D-10** | 辅助函数行为 | 形状错配 `TypeError`；awaitable `TypeError`；节点外透传 | spec Q13 / Q14 / Q16 |
| **D-11** | 零开销守卫 | 每任务一次 `current_span_tracer()` + `is None`；无 span / 无回调 / 无 span 专用 id；tracer 作用域由注入方管理（作用域结束即失效） | spec FR-002 / FR-003 / SC-003 / T059 |
| **D-12** | 并发隔离 | 沿用 B8F2 每任务 `copy_context()`；L5 栈为 ContextVar | `_concurrency.py:223`；spec FR-024 |
| **D-13** | 接收端（receiver）异常 | 隔离；MAY `logging.warning`；不传播 / 不改变执行 | spec FR-025 / SC-007；上游 `callbacks/manager.py:351-354` |
| **D-14** | 公开面 | 零新增门面 / L1 / L2 `__all__`；helpers 在 L5 模块 | spec FR-022 / Q8 |

---

## Phase 1: Design & Contracts

**输出**：[data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

### 1. 数据模型

- `Span`（B2F1 · 11 字段）· 节点 / 模型 / 工具三种生产形态；
- `SpanProducer` / `_SpanFrame` / 接收端协议；
- 运行上下文（`run_id` / `thread_id` / `node` / `checkpoint_id`）；
- 生命周期状态机（idle → node start → 嵌套 model/tool → end / exception）；
- 不变量：父链、栈平衡、时间严格递增、属性允许清单、JSON 可序列化、零开销。

### 2. 契约

- `contracts/span-production-contract.md`：L2 节点接缝 + L5 生产者 / 接收端 / 时间 / 关联键；
- `contracts/invoke-helpers-contract.md`：`invoke_model` / `invoke_tool` 签名、形状、
  awaitable、节点外行为、属性、返回值；
- `contracts/upstream-parity.md`：P-01…P-11 / E-1…E-4 / D-201…D-208 / X-1…X-4。

### 3. Quickstart

- 绑定 tracer → 跑节点 / 模型 / 工具场景 → 检查三层 span；
- 未绑定 → 零 span；
- 依赖闭包 / import 惰性 / 环境变量守卫；
- 差分探针。

---

## Work Breakdown（供 `/speckit.tasks` 拆解）

### Phase A：L2 运行 id 与私有 hook

1. 在 `runtime/_stream_context.py` 新增 `bind_run_ids(run_id, thread_id)` 私有上下文管理器；
   保持 `bind_stream` 行为零改动。
2. 新增 `runtime/_span_hook.py`：
   - `bind_span_tracer(tracer)` / `current_span_tracer()`；
   - `start_node_span(tracer, node, run_id, thread_id, checkpoint_id=None)`；
   - `end_node_span(tracer, start_span)`；
   - `start_node_span` MUST 在构造开始 Span 后调用 `tracer.on_span_start(start)`；
     `end_node_span` MUST 在构造结束 Span 后调用 `tracer.on_span_end(end)`；
   - 鸭子类型 tracer 协议（`on_span_start` / `on_span_end` / `current_span_id`）；
   - UTC ISO-8601 / 严格正耗时 / `uuid4().hex`。
3. `runtime/superstep.py` 的 `run_graph`：仅在 tracer 已绑定且 `run_id is None` 时
   `bind_run_ids`；嵌套 / stream 已有 id 时零改动。

### Phase B：L5 生产引擎

4. 新增 `observability/_time.py`：与 L2 hook 同款的 UTC ISO-8601 / 正耗时助手。
5. 新增 `observability/_producer.py`：
   - `_SpanFrame(span, kind)` + `ContextVar[tuple[_SpanFrame, ...]]`；
   - `on_span_start` / `on_span_end` / `current_span_id` / `current_node_span`；
   - `make_model_span` / `make_tool_span`（v1 最小属性集）；
   - 接收端 `on_span_start` / `on_span_end` 转发 + 异常隔离。
6. 新增 `observability/_invoke.py`：
   - `invoke_model(obj, input, *, call_id=None)` / `invoke_tool(obj, args, *, call_id=None)`；
   - 形状校验（Q14）· awaitable 拒绝（Q16）· 节点外透传（Q13）；
   - 返回值原样；异常原样重抛；模型 / 工具失败时 `error.type`。
7. 新增 `observability/__init__.py`：导出 helpers + `SpanProducer`（非门面）。

### Phase C：节点执行接缝

8. `runtime/superstep.py` 的 `_run_round._bind._inner`：在 `fn()` 前后包节点 span；
   tracer 为 `None` 时只走原 `fn()`（一次判断）。
9. 节点 span 的 `parent` 取 `tracer.current_span_id()`；`name == node`；
   `attributes={}` / `context={}` / `checkpoint_id=<运行期值 | None>`。
10. 异常路径：结束 span（同 id、`end_time`）后原样重抛；节点 span 不写 `error.type`。

### Phase D：行为面收口

11. 模型 / 工具 span 的父链（节点 / 嵌套工具 / 模型）· 名称格式 · 属性最小集。
12. 时间严格正耗时 · `run_id` 非空 · `thread_id` 同源 · `node` = 所属节点。
13. 并发：每个任务线程独立栈；不得跨任务父子；不新增上下文传播机制。
14. 接收端异常隔离；零开销守卫；无 env 读取。

### Phase E：测试与差分

15. `tests/observability/test_invoke_helpers.py`：形状 / awaitable / 节点外 / 返回值 / 属性。
16. `tests/observability/test_producer.py`：父链 / 嵌套 / 接收端异常 / 栈平衡。
17. `tests/observability/test_zero_overhead.py`：未绑定 ⇒ Span 构造数 == 0 / 回调数 == 0。
18. `tests/runtime/test_node_spans.py`：节点 span / 异常成对；`tests/runtime/test_concurrency_spans.py`：并发父子 / 跨任务不串父。
19. `tests/runtime/test_span_ids.py`：stream 与 span 的 `run_id` / `thread_id` 同源；
    `RunConfig(run_id=...)` 被忽略；invoke 路径一个 run_id。
20. `tests/observability/test_span_attributes.py`：允许清单 / 节点空映射 / `dataclasses.asdict(span)` 的 JSON。
21. 复用 `tests/contracts/test_architecture.py` 的 G3 / G7：依赖闭包为空集 + 公开面 / import 图守卫。
22. `tests/differential/test_b18f1_span_parity.py`：D-201…D-208；上游缺席即 skip。
23. 公开面 / import 惰性 / 环境变量守卫。

### Phase F：文档与人工门禁

24. `harness/verification/B18F1/manual-verification.md`：fake / 真实轮 + 零出站证据 + 偏离登记。
25. README：新增**独立「可观测属性」章节**（D-5 MUST）；**MUST NOT** 改动「API 兼容矩阵」（逐符号、4 列、manifest 内）。
26. 若需要，`harness/demo/graph_core.py` 增加 span 生产验收场景（**不改 `target.py`**）。
27. `tests/runtime/test_node_record_carriers.py`：验证 `stream()` 的 `values` / `updates` / `tasks` +
    `PregelTask.result` 可还原原则 IV 的输入 / 输出；错误由原样抛出的异常（+ `add_note`）还原，
    `PregelTask.error` 不作为失败路径载体；`invoke()` 路径承接归 B19F1/B20（R-7）。
28. `tests/contracts/test_trace_carrier_contract.py`：文档守卫，断言 spec 的 D-6 / FR-029 / SC-016
    与 B19F1/B20 承接条款 + 捕获机制存在，错误载体 = 原样异常，且节点 span 属性仍为空。
29. **承接接线**：把 B18F1 的 D-1 / D-2 / D-3 / D-4 / D-6 / R-4 写进 `harness/features/B14F1...` / `B19F1...` /
    `B20F1...` / `B20F2...` / `B21F1...` 的「下游承接」段；`tests/contracts/test_downstream_wiring.py` 做文档守卫。
30. `harness/verification/B18F1/acceptance.py`：一键验收 A1–A7；`tests/runtime/test_acceptance_script.py` 增加 pytest 包装。

---

## Pre-registered Red List（实施时逐条核对）

1. **L2 不得 import L5**：`runtime/*.py` 的 import 图 MUST NOT 出现 `freegraph.observability`。
2. **L5 不得 import L2**：`observability/*.py` 只允许 `freegraph.contracts.*` + 标准库；
   MUST NOT import `superstep` / `_span_hook` / `_stream` / `_stream_context`。
3. **门面零扩张**：`freegraph.graph.__all__` 不变；`freegraph.runtime.__all__` 不变。
4. **`freegraph/__init__.py` 零改动**：`import freegraph` 后 `sys.modules` 不含
   `freegraph.observability` / `freegraph.runtime._span_hook`。
5. **未绑定 tracer**：`Span` 构造数 == 0；不生成 **span 专用** `run_id`；不读 env。
6. **节点签名 / 状态**：`_run_round._bind` 只包 `fn()`，不改 `node_input` / `state`。
7. **`stream()` 零影响**：`StreamSession` / `bind_stream` 不动；事件信封 / `run_id` 不变。
8. **`RunConfig` 零改动**：`run_id` 仍被忽略；不新增字段。
9. **时间严格正**：`end_time > start_time`；同 id 的开始 / 结束成对。
10. **并发不串父**：每个任务的当前栈独立；跨任务父子数 == 0。
11. **属性最小集**：模型 / 工具只写 Q9 允许键；节点空映射；`context` 空映射；
    `error.type` 在模型 / 工具失败时 MUST 写。
12. **依赖 / 许可证**：零新增运行时依赖；无 `opentelemetry-*` / `langchain*` / `langsmith`。
13. **原则 IV 载体**：节点 span 只承担节点名 / 耗时；输入 / 输出 / 错误由 `stream()` 事件（`values` / `updates` / `tasks`）+ `PregelTask.result` + 原样抛出的异常 + B19F1/B20 承接；`PregelTask.error` 不作为失败路径载体；节点 span 属性仍为空（R-7）。
14. **跨 feature 接线**：B14F1（`checkpoint_id`）、B19F1（`SpanProducer` 双绑定 + invoke 逐节点记录 + 捕获机制）、
    B20F1/B20F2（JSON 记录 / 查询维度 + 捕获机制）、B21F1（OTLP 1:1）提示词 MUST 含 B18F1 的承接段；由 `test_downstream_wiring.py` 守卫。

---

## Risks & Mitigations

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| **RK-1** | 为图省事让 L2 import L5 | 破 ARCH-1 / 依赖方向 | 只用 `_span_hook` + 鸭子类型；CI import 图守卫 |
| **RK-2** | 为图省事让 L5 import L2（`superstep` / `_stream_context` 等） | 破 FR-021 / ARCH-3 | L5 零 L2 import；从节点 span 继承 id；代码审查 + import 守卫 |
| **RK-3** | invoke 路径 `run_id` 为空 | C23 缺陷 / 测试红 | `run_graph` 仅在 tracer 绑定时 `bind_run_ids`；测试强断言 |
| **RK-4** | `bind_run_ids` 覆盖 stream 已绑定 id | stream 事件与 span 不同源 | 只在 `run_id is None` 时绑定；stream 路径零改动 |
| **RK-5** | 并发任务串父 | trace 树错乱 | L5 栈为 ContextVar；沿用 `copy_context()`；并发测试 |
| **RK-6** | 时间精度不足导致 `end == start` | SC-005 红 | `time.time_ns()` + 9 位小数；必要时 `end_ns = max(end_ns, start_ns + 1)` |
| **RK-7** | 接收端抛异常改变图结果 | 可观测失败影响执行 | 隔离 + MAY `logging.warning`；测试固定 |
| **RK-8** | 误把 helpers 加进公开门面 | API 快照红 / 冻结面破 | helpers 只在 `freegraph.observability`；门面零改动 |
| **RK-9** | 模型 / 工具属性读太多 / 读私有字段 | 脆弱 / 隐私 / Q9 违约 | 只读 `model_name` / `model` + `name` + 显式 `call_id` |
| **RK-10** | 真实模型轮不可达 | 人工门禁 5 偏离 | fake 轮必跑；真实轮优先本地真实对象；外部 provider 轮登记偏离（R-3） |
| **RK-11** | 新增私有模块漏署名头 | 宪法原则 X / G30 红 | 每个新文件带署名头；模块 docstring 首语句 |
| **RK-12** | `Span` 构造被误当成「零开销」 | 计数夹具失真 | 对 `_span_hook.Span` / `_producer.Span` 双点计数；未绑定路径两处都不构造 |

---

## Phase 1 Re-check（设计后）

| 检查项 | 结果 |
|---|---|
| 宪法 Check 全部通过 | ✅（R-1…R-5、R-7 已登记；R-6 继承自 B8F2） |
| 无 `NEEDS CLARIFICATION` | ✅（spec Q1–Q16 收敛） |
| 无破冻结面 | ✅（`Span` / `TraceSink` / `RunConfig` / `SuperStepResult` / `PregelTask` / 门面 / 信封；`bind_run_ids` 为 L2 私有扩展） |
| 依赖闭包仍为空集 | ✅（只用标准库 + L1） |
| L2 / L5 依赖方向 | ✅（L2 不 import L5；L5 零 L2 import） |
| 公开面零扩张 | ✅（helpers + `SpanProducer` 在 L5 模块，不进 `freegraph.graph`） |
| 零开销可测 | ✅（未绑定 ⇒ Span 构造数 == 0 / 回调数 == 0） |
| B19F1 可消费 | ✅（开始 / 结束两个同 id 快照；双绑定接缝 R-4） |
| 原则 IV 字段载体 | ✅（组合载体 + 承接机制 + B19F1/B20；R-7 / FR-029 / SC-016） |

---

## 本 plan 阶段的「零源码改动」声明

本 `/speckit.plan` 只生成 / 更新 spec 目录内的规划与设计产物：
`plan.md` / `research.md` / `data-model.md` / `quickstart.md` / `contracts/*`。
**MUST NOT** 在本阶段修改 `src/` / `tests/` / `harness/demo/target.py`。
实现从 `/speckit.tasks` 之后的 `/speckit.implement` 开始。
