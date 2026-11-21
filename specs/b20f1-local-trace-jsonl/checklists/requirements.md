# Specification Quality Checklist: B20F1 · 本地 Trace 存储：JSONL 文件后端（零依赖）

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

- **口径澄清（C-1 · 形态锁定）**：本 spec **写死**了「`FileTraceStore(directory=...)`
  经 B19F1 的 `compile(tracer=...)` 注入」与文件命名 `trace-<run_id>.jsonl`。
  这是提示词 FR-006 / §10 明确要求的**锁定项**，不是实现泄漏。
- **口径澄清（C-2 · 双行结构）**：JSONL 含 `kind="span"`（`Span` 全部 11 字段）与
  `kind="trace_record"`（B19F1 `to_jsonable()` 全部字段）两类行；`kind` 是唯一新增字段。
  该决定同时满足 FR-003 的「Span 全部字段」与 B19F1 D-1/D-3 的「原样消费 record」。
- **口径澄清（C-3 · 失败感知）**：写入失败永不阻断执行，但 MUST 通过
  `write_errors` / `last_error` / 可选 `on_error` / `logging.WARNING` 四路可感知；
  `Exception` 隔离、`BaseException` 不吞。该取舍已写成 A4 / SC-004 的可判定条目。
- **口径澄清（C-4 · 默认关闭）**：未注入 ⇒ 零文件 / 零目录 / 零环境变量读取；
  只构造 `FileTraceStore` 不运行也零副作用；`directory` 必填、无默认目录。
- **口径澄清（C-5 · 冻结面）**：`Span` 11 字段 / `TraceSink` 3 方法 / `TraceRecord` 字段面 /
  `RunConfig` 9 字段 / 门面符号面均不变；唯一新增公开符号是 L5
  `freegraph.observability.FileTraceStore`，并已登记到「破冻结面的回溯修订清单」
  （更新 `observability.__all__` 精确集合断言，只增不改）。
- **口径澄清（C-6 · 内部格式）**：`kind` / 文件名 / 行序 / 编码是**内部实现细节**（C27 ⑤），
  但本 spec 写死以保证可重复验收；查询 API 归 B20F2，Studio 不直连文件格式。
- **口径澄清（C-7 · 范围）**：本 feature 只写不读；查询 API、SQLite 后端、OTLP、UI、
  保留期 / 清理均明确排除。测试可读回自己写的文件，但不构成公开查询 API。
