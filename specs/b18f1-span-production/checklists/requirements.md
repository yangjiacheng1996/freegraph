# Specification Quality Checklist: B18F1 · Span 数据类生产（节点 / 工具 / 模型三级 span）

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-20
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

- **口径澄清（C-1）**：`Span` 已由 B2F1 交付并冻结 11 字段；B18F1 **只生产**，MUST NOT 增删字段。
  本 spec 的「功能需求」写的是**生产行为**，不是重新定义数据类型。
- **口径澄清（C-2 / Q1 / Q2）**：B18F1 的 **tracer = `SpanProducer`**（显式启用的 span 生产接缝）；**receiver = 接收端**（测试可注入计数夹具 / B19F1 的 `TraceSink`）。
  公开 `TraceSink` 注入点与 `current_span()` 归 **B19F1**。模型 / 工具 span 通过**鸭子类型可观测接缝**
  产生——不对任意节点函数体做魔法拦截（不可实现且违反零开销 / 不改用户对象 / 零依赖）。
- **口径澄清（C-3 / Q3）**：模型 / 工具语义属性 100% `gen_ai.*`；**节点 span 属性恒为空映射**（Q11）；`error.type` 在模型 / 工具失败时 MUST 写，是唯一允许的 OTel general 属性。该口径**不放宽**
  提示词 SC-001 的模型 / 工具属性判据。
- **零 `[NEEDS CLARIFICATION]`**：关键歧义（生产接缝、公开注入归属、节点属性命名空间、`invoke()` 的
  `run_id`、`checkpoint_id` 何时有值、内容采集、异常行为、是否新增公开门面）均已在
  `Clarifications` Q1–Q8 以项目内既有契约 / 上游事实 / 宪法裁定作答。
- **技术锚点的判定**：本项目的宪法（原则 VIII「证据与术语纪律」/ 原则 XI「上游优先」/ 原则 VI
  「判据级追溯」）要求 spec 必须包含**契约编号**（C23 / C24）、**上游 `路径:行号`**、
  **`gen_ai.*` 的 semconv 出处**与**冻结面声明**。这些是**契约级证据**，不是面向用户的实现细节；
  「No implementation details」与「Written for non-technical stakeholders」按本仓库的规格驱动纪律
  判定为通过：用户场景 / 成功标准仍是行为口径，技术锚点只用于可审计性。
- **已识别的关键边界**：未启用生产时 span 构造数 == 0 / 回调数 == 0 / 不生成 **span 专用** `run_id` / 不读环境变量；
  `run_id` 空即缺陷；`checkpoint_id` 可为 `None`（B14F1 补值）；`Span.context` 不得承载 C21 的
  `context`；不重引入 alias；不扩大公开门面；不引入 `opentelemetry-*` / `langchain*` / `langsmith`。
- **2026-11-20 分析修复**：新增「原则 IV 的字段载体映射」+ **FR-029 / SC-016 / D-6**，
  明确节点 span 只承担节点名 / 耗时，输入 / 输出由 `stream()` 事件 + `PregelTask.result` 承接，
  错误由原样抛出的异常（+ `add_note`）承接，`PregelTask.error` 不作为失败路径载体；B19F1/B20 承接 + 捕获机制；
  同步修正 D-3 / D-204 的 `error.type` 例外、FR-016（v1 恒 `chat`）、任务追溯表、并行示例、
  `error.type` / outside-node awaitable / 无 tracer 形状校验测试，以及 ARCH-3 的私有 `_SpanTracer` Protocol。
- **clarify 轮已拍板（2026-11-20）**：Q9 模型 / 工具元数据采**极简集**（只写 operation、request.model、tool.name、tool.call.id；
  不写 provider / usage / response / finish_reasons / tool.description / conversation.id）；Q10 埋点接缝 = **一次性调用辅助**
  `invoke_model` / `invoke_tool`（L5 非门面、可 import）；Q11 节点 span 属性**恒为空映射**；Q12 `error.type` 只写
  **模型 / 工具失败 span**；Q13 节点外调用辅助函数 = 直接调用、不产生 span；Q14 辅助函数名即意图，形状不匹配抛 `TypeError`；
  Q15 `Span.context` v1 **恒为空映射**；Q16 v1 **只支持同步** `invoke`，返回 awaitable 时结束 span 并抛 `TypeError`（不提供异步辅助）。
- **待 `/speckit.plan` 落地**：L2 单一节点执行接缝的具体形态（contextvar / 私有回调，保持 L2 不 import L5）；
  **tracer（`SpanProducer`）/ receiver** 的符号与生命周期；`invoke_model` / `invoke_tool` 的最终模块路径；并发下当前 span 栈的传播；
  接收端异常隔离的具体落点；`invoke()` 路径 run-scoped `run_id` 的绑定位置；严格正耗时的纳秒级实现；
  semconv 文档版本钉死与属性对照表落库位置；SC → 测试任务的判据级覆盖（tasks 阶段）。
- **受影响的下游 / 上游**：B19F1（消费生产结果 + 公开注入 + `SpanProducer` 双绑定 + invoke 逐节点承接）、B20F1 / B20F2（JSON 存储 / 查询 + invoke 逐节点承接）、
  B21F1（OTLP 映射）、B14F1（checkpoint_id 补值）；README **独立「可观测属性」章节**（**不改** API 兼容矩阵）。
- **2026-11-21 分析修复**：统一 tracer=`SpanProducer` / receiver 术语；`gen_ai.operation.name` 恒 `chat`；空工具名始终写；`json.dumps(dataclasses.asdict(span))`；C27 查询维度改为 run_id/thread_id/时间/节点名；`bind_run_ids` 与只读口径对齐；子 span 继承 `checkpoint_id`；补 FR-029/SC-016 追溯与跨 feature 接线任务；`error.type` 改为失败时 MUST 写；stream 失败路径的错误载体改为原样异常；模型 / 工具 span 的 parent 改为“本节点 span 子树”；补 RunIdBindingCounter 与 T059 落点。
