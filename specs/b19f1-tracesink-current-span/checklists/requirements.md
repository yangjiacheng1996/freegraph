# Specification Quality Checklist: B19F1 · `TraceSink` 接入 + `current_span()` + 默认关闭

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-21
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **口径澄清（C-1 · 注入点形态）**：本 spec **写死**了「编译期关键字
  `StateGraph.compile(*, tracer=...)`」，并给出与「运行配置注入」的取舍理由（`RunConfig` 是
  L1 纯数据 / 9 字段冻结 ⇒ 不能装对象引用；`invoke` / `stream` 签名已冻结）。
  该细节是**提示词 FR-001 明确要求的锁定项**，不是实现泄漏。
- **口径不变量（C-2 · 冻结面）**：`Span` 11 字段 / `TraceSink` 3 方法 / `RunConfig` 9 字段 /
  `SuperStepResult` / `PregelTask` / `stream()` 信封 / 门面 8 符号 / L1 22 符号**均不变**；
  唯一新增公开关键字是 `compile(*, tracer=...)`，并已登记到「破冻结面的回溯修订清单」。
- **口径澄清（C-3 · 默认关闭）**：未注入 sink **且无任何外层 tracer** ⇒ span 构造 0、回调 0、
  `SpanProducer` 构造 0、span 专用 `run_id` 绑定 0、环境变量读取 0；`LANGSMITH_TRACING=true`
  不改变行为（SC-002 / SC-005）。B18F1 直接绑定不计入「无外层 tracer」。
- **口径澄清（C-4 · 双绑定 / 层间例外）**：注入点构造**一个** `SpanProducer`（接收端 = 用户
  `TraceSink`），同一实例同时绑定 L2 `_span_hook` 与 L5 `_producer`，且为 **run-scoped**
  （FR-009）。该接缝涉及 **R-1（L3 `_stategraph.py` → L5 `_inject`）**、
  **R-2（L5 → L2 私有 `_span_hook` 双绑定；不读 `_stream_context`）**、
  **R-3**（B18F1 断言拆分）；**三者已获发起者一次性追认（2026-11-21）**，
  MUST NOT 扩展为例外通行证。**B8F2 的 R-6 已相应收窄**：L2 `_run_round` 读取
  `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`，B19F1 从节点 start `Span` 继承，不直接读取。
- **口径澄清（C-5 · D-6 承接机制）**：`invoke()` **与 `stream()`** 路径逐节点
  `(node, input_state, output_state, error)` **由本 feature 经 L2 既有节点接缝（扩展 hook）
  捕获**；`output_state` = **节点原始返回值**（`node.run` raw return），归一结果仅用于调度；
  错误载体 = 原抛异常（+ `add_note`）；不把 `Span` 当容器（FR-015）。
  选择理由：`PregelTask` 无 `input` 字段，单靠 B20 快照无法完整还原输入状态。
- **口径澄清（C-6 · 触发源 / 并发 / 屏障）**：B9F1 / B11F1 / B12F1 / B7F4 的承接义务落在
  **本 feature 自有的补充 trace 记录**（与 `Span` 分离）；**当 sink 实现 `on_trace_record` 时**
  MUST 暴露触发源 / 并发组 / 屏障组；执行次序由 `triggers` / `concurrency_group` **字段内**
  的确定性顺序承载（标准任务节点名序；含 fan-out 的轮按**数值** TaskId 序），
  **MUST NOT** 用完成时刻 / 声明顺序 / 记录到达顺序（FR-011…FR-014）。
  `concurrency_group` = 本轮派发集（含未启动取消任务；其自身无 record）。
- **口径澄清（C-7 · 导出位置）**：`current_span()` 与 `TraceRecord` 从 L5
  `freegraph.observability` 导出；`trace_run_scope` 是 L5 内部入口，不对外导出；
  不经 `freegraph.graph` 门面（门面不得 import L5），`import freegraph` 保持惰性（FR-018）。
- **口径澄清（C-8 · invoke run-id）**：`invoke()` 由注入点**优先** `bind_run_ids`；B18F1 的
  L2 `_run_graph` 绑定为 **fallback**（仅当 `_STREAM_RUN_ID` 为空）。二者共用同一载体，
  **每次注入运行恰一次有效绑定**，MUST NOT 产生两个不同 `run_id`。
- **口径澄清（C-9 · `triggers` 排序）**：统一排序键 `(kind, source, index)`；标准边 / `goto`
  的 `("e", source)` 使用 `index = -1`，MUST NOT 直接混排二元组 / 三元组。
- **口径澄清（C-10 · 接收端异常隔离）**：FR-017 / SC-010 的「异常」= **`Exception`**；
  `BaseException`（`KeyboardInterrupt` / `SystemExit`）MUST NOT 被吞（与 B18F1 `_forward` 一致）。
- **口径澄清（C-11 · 静态类型 vs 运行期最小面）**：`compile(tracer=...)` 静态注解仍为
  `TraceSink | None`；运行期只要求 `on_span_start` / `on_span_end`，`SpanOnlySink` 属有意的
  鸭子类型扩展，测试用 `typing.cast` / `# type: ignore` 表达。
- **口径澄清（C-12 · 作用域优先级）**：当前存在 B19F1 注入作用域时，**B19F1 作用域优先**
  （即使作用域内另有 B18F1 直接绑定，无 tracer 运行仍屏蔽）；无活动 B19F1 作用域时，
  B18F1 直接绑定保持既有语义。
- **口径澄清（C-13 · raw / normalized 承载）**：`_execute_node_pure_with_raw` 返回
  `(normalized, raw)`；`_bind` 解包后把 `normalized` 交回调度、`raw` 用于 `output_state`；
  接收端未实现 `on_trace_record` 时走原路径，不采集 raw / input-output。
- **上游证据**：Upstream Parity 表逐条带 `langgraph 1.2.11` / `langchain-core 1.7.6` /
  `langsmith 0.14.17` 的 `路径:行号`；`get_current_run_tree` 的对应关系已在 P-01 标注来源
  （`langsmith/run_helpers.py:107-113` · `langsmith/_internal/_context.py:27,30-37`）。
- **无澄清项**：提示词已给出全部关键决策（注入形态二选一、双绑定、id 关联、默认关闭、
  下游承接）；spec 只做**锁定与展开**，未新增 `[NEEDS CLARIFICATION]`。
- **2026-11-21 分析修复（analyze）**：C1（R-1）已批准并登记；I1（SC-011 → `to_jsonable`）、
  I2（FR-011/012/014 条件式）、I3（FR-015 → invoke+stream）、A1（`output_state` = raw return）、
  G1（`TraceRecord` 导出）、T1/T2（tasks 并行 / 顺序）已修。
- **2026-11-21 第二轮修复**：X-4 ↔ **P-10 / D-309**；R-2 收窄为仅 `_span_hook`；SC-010 图级
  `FailingSink`；SC-012 / FR-006 `SpanOnlySink`；FR-010 `RunConfig.run_id` 忽略；取消语义改为
  「节点自身取消 / 运行期只取消未启动任务」；可选记录仅在接收端实现时构造 payload；基线
  更新为 `1863 passed, 6 skipped`；B19F1 实为第 **24** 个 feature。
- **2026-11-21 第三轮修复**：**I1** 保留 B18F1 直接绑定（仅 B19F1 作用域触发嵌套屏蔽）；**K1**
  R-1/R-2/R-3 一次性追认；**K2** 质量门禁 5 偏离登记；**S1** A6 恢复 + A7；**D1** T017 移除
  record 断言；**A1** 执行次序 = 字段顺序；**P1** 补 **D-310 / X-5**（P-09）；**A3/A5/G1/A4/L1–L6**
  同步修订。
- **2026-11-21 第四轮修复**：**X1** 保留 R-2、收窄 B8F2 R-6；**X2** run-id 注入点优先 / L2 fallback；
  **T1** T031 前移到 T018 之后；**A1** `triggers` 统一排序键；**U1** raw 承载写死；**T2** 统一
  `TaskTraceMeta`；**A2** `Exception` 隔离；**A3** 静态注解 / 运行期最小面差异；**A4** B19F1 作用域优先；
  **G1–G3** 补边缘测试、追溯映射与措辞。修复 ID 的定义见 `spec.md`「分析修复记录」与
  `plan.md` Post-Design Re-check。
