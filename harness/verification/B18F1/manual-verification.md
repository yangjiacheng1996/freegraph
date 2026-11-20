# B18F1 人工验证记录

**Feature**: B18F1 · Span 数据类生产（节点 / 工具 / 模型三级 span）
**Date**: 2026-11-21
**Owner**: 实施者（T049 收口）

## 1. 验证环境

- Python: CPython **3.11.16**（`.venv`）
- `langgraph` **1.2.11** / `langchain-core` **1.7.6** / `langsmith` **0.14.17**
- 日期: 2026-11-21

### 1.1 基线

```text
$ .venv/bin/python -m pytest -q --tb=no
1778 passed, 6 skipped in 114.64s
```

跳过项：C8 元测试占位 · IPython 缺失的 PNG · mypy 未安装 · 上游 PNG 未开启 · API 快照未开启更新 · Windows 时钟精度档。

### 1.2 零开销 / US3

```text
$ .venv/bin/python -m pytest -q tests/observability/test_zero_overhead.py tests/runtime/test_no_env_reads.py tests/contracts/test_architecture.py
134 passed in 4.25s
```

零开销计数（实际运行输出）：

```text
ZERO_OVERHEAD {'span': 0, 'bind': 0}
BOUND_SPANS ['demo_node', 'chat demo-model', 'execute_tool multiply'] ended 3
EGRESS []
```

- 未绑定 tracer：`Span` 构造数 **0**，`bind_run_ids` 调用数 **0**，出站 **0**。
- 绑定 tracer：节点 / 模型 / 工具三级 span 各 1 个，结束快照 3 个。

### 1.3 并发

```text
$ .venv/bin/python -m pytest -q tests/runtime/test_concurrency_spans.py tests/observability/test_producer.py
5 passed in 0.18s
```

覆盖：3 个并发节点的 worker span 各自 `parent is None`；3 个工具 span 的 parent 集合 == worker span id 集合；无跨任务父子；`copy_context` 任务栈独立。

### 1.4 quickstart

```text
quickstart §2 OK: ['demo_node', 'chat demo-model', 'execute_tool multiply']
quickstart §5.1 dependency closure: empty
quickstart §5.2 lazy import: ok
quickstart §6 stream/span ids OK 0c9cb39b9e6947cca3d775023ac592cf None
```

## 2. 验证步骤

1. 跑基线（§1.1）。
2. 跑零开销 / 环境变量 / 架构门禁（§1.2）。
3. 跑并发 / 任务栈隔离（§1.3）。
4. 跑 quickstart §2 / §5 / §6（§1.4）。
5. 跑 B18F1 定向测试（见 §3）。
6. 跑全量回归（见 §3）。

## 3. 实际输出

### 3.1 B18F1 定向测试

```text
$ .venv/bin/python -m pytest -q tests/observability tests/runtime/test_node_spans.py \
    tests/runtime/test_concurrency_spans.py tests/runtime/test_span_ids.py \
    tests/runtime/test_span_lifetime.py tests/runtime/test_node_record_carriers.py \
    tests/runtime/test_no_env_reads.py tests/contracts/test_trace_carrier_contract.py \
    tests/contracts/test_downstream_wiring.py tests/differential/test_b18f1_span_parity.py
64 passed in 1.50s
```

### 3.2 差分组

```text
$ .venv/bin/python -m pytest -q tests/differential/test_b18f1_span_parity.py
8 passed in 0.91s
```

覆盖 D-201…D-208（上游缺席即 skip；本机上游 1.2.11 实际执行）。

### 3.3 一键验收

```text
$ .venv/bin/python harness/verification/B18F1/acceptance.py
[PASS] A1 三级 span 各一例
[PASS] A1 三级 span 均已成对结束
[PASS] A1 节点属性 / context 恒空
[PASS] A1 模型 span 最小属性集
[PASS] A1 工具 span 最小属性集
[PASS] A1 模型 span parent == 节点 span id
[PASS] A1 工具 span parent == 节点 span id
[PASS] A2 未绑定 tracer ⇒ Span 构造数 == 0
[PASS] A2 未绑定 tracer ⇒ span 专用 run_id 绑定数 == 0
[PASS] A3 RunConfig.run_id 被忽略
[PASS] A3 stream 事件与 span 共享 run_id
[PASS] A3 stream 事件与 span 共享 thread_id
[PASS] A4 3 个并发节点各 1 个节点 span
[PASS] A4 并发顶层节点 parent 均为 None
[PASS] A4 工具 span 只挂在本任务节点下
[PASS] A5 freegraph.graph 公开符号数不变（8）
[PASS] A5 freegraph.runtime.__all__ 不变（23）
[PASS] A5 基础安装依赖闭包为空
[PASS] A5 新源码无禁用 import / env 读取（[]）
[PASS] A6 框架出站 == 0
[PASS] A7 人工验证记录存在且非空
[PASS] A7 人工验证记录含 B18F1
B18F1 acceptance: PASS（22 项检查）
```

### 3.4 graph_core 验收场景

```text
$ .venv/bin/python harness/demo/graph_core.py
[B18F1 · Span 数据类生产]
  ✔ B18F1 节点执行结果正确
  ✔ B18F1 节点 / 模型 / 工具三级 span 各一例
  ✔ B18F1 三级 span 均已成对结束

── graph_core 汇总 ──
断言 37 条 · 通过 37 · 失败 0
结论：PASS
```

### 3.5 全量回归

```text
$ .venv/bin/python -m pytest -q --tb=no
1861 passed, 6 skipped in 116.06s
```

与基线相比：**+83 passed**，**0 failed**；既有跳过项不变。

## 4. 结论

- 节点 / 工具 / 模型三级 span 生产已落地；节点 span 自动产生，模型 / 工具 span 只经显式 `invoke_model` / `invoke_tool` 产生。
- 未绑定 tracer 时零 span / 零回调 / 零 span 专用 `run_id`；环境变量不启用生产。
- `stream()` 事件与 span 共享同一 `run_id` / `thread_id`；`RunConfig.run_id` 被忽略。
- 异常路径开始 / 结束 span 成对、原对象重抛；模型 / 工具失败写 `error.type`；节点 span 属性恒空。
- 依赖闭包仍为空集；`import freegraph` 不加载 L5 / L2 hook；公开门面符号数不变。
- 全量测试与差分组均通过。

### 4.1 人工验收签署

- **验收结论**：**PASS**
- **发起者**：杨家成
- **签署日期**：**2026-11-21**
- **签署说明**：发起者确认「人工验收通过」，同意按本记录收尾、提交与推送。

## 5. 遗留问题

- `checkpoint_id` 在 v1 仍为 `None`；B14F1 落地后通过既有运行期接缝补节点 span（D-4）。
- `invoke()` 路径的逐节点输入 / 输出 / 错误由 B19F1 / B20 承接（D-6）；本 feature 不闭合该路径。
- `TraceSink` 公开注入点与 `current_span()` 归 B19F1；本地存储 / 查询归 B20；OTLP 归 B21F1。

## 6. 零出站证据

- 实际计数输出：`EGRESS []`（quickstart 场景 + 绑定 tracer）。
- 源码扫描：`src/freegraph/observability/**` 与 `src/freegraph/runtime/_span_hook.py` **零**
  `socket` / `http` / `urllib` / `requests` / `httpx` / `langchain*` / `langsmith` / `opentelemetry` import。
- 全量测试包含 G4（零环境变量 / 零出站）门禁并通过。

## 7. 偏离登记与发起者追认

- 本 feature **不需要外部模型 provider**：
  - **fake 轮**：quickstart 的 `FakeModel` / `FakeTool`（真实 Python 对象，非 `Mock`）。
  - **真实轮**：本地真实实现了 `invoke` 的 `Model` / `Tool` 类（quickstart §2 / §6 与定向测试），
    实际执行、实际产生 span。
- 因此 **R-3 的“外部 provider 轮不可达”偏离不触发**，无需发起者追认；若审查要求外部模型轮，
  按 plan R-3 登记偏离并由 **B21F1** 承接。
- D-1 / D-4 / D-6 / R-4 跨 feature 接线证据：`tests/contracts/test_downstream_wiring.py`（T058）
  与 `tests/contracts/test_trace_carrier_contract.py`（T056）通过；目标提示词已含承接段。

## 8. Red List 复核（T054）

- ✅ L2 不 import L5（`tests/contracts/test_architecture.py::TestB18F1LayeringAndLaziness`）。
- ✅ L5 不 import L2（同上）。
- ✅ 公开门面符号数不变：`freegraph.graph.__all__` = 8；`freegraph.runtime.__all__` = 23。
- ✅ `import freegraph` 只加载 `freegraph`（不加载 L5 / `_span_hook`）。
- ✅ 未绑定 tracer：`Span` 构造数 0 / `bind_run_ids` 0 / 回调 0 / 无 env 读取。
- ✅ 节点签名 / 状态 / `SuperStepResult` / `PregelTask` / `RunConfig` / `Span` 字段零改动。
- ✅ `stream()` / `StreamSession` / `bind_stream` 零改动；`bind_run_ids` 为 L2 私有新增。
- ✅ 时间严格正：`end_time > start_time`（含极快调用）。
- ✅ 并发不串父：每任务 `copy_context()`；跨任务父子数 0。
- ✅ 属性最小集；节点 / `context` 恒空；`error.type` 仅模型 / 工具失败。
- ✅ 零新增运行时依赖；无 `opentelemetry-*` / `langchain*` / `langsmith`。
