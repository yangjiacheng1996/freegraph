# Specification Quality Checklist: B20F2 · Trace 查询 API + SQLite 后端

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

- **口径澄清（C-1 · 公开读取载体）**：本 spec **写死**了
  `query(query: TraceQuery | None = None) -> list[dict[str, Any]]`，同时挂在
  `FileTraceStore` 与 `SqliteTraceStore` 上。这是提示词 FR-001 / FR-004 / C27 ④
  「同一协议、后端可替换」明确要求的**锁定项**，不是实现泄漏。
- **口径澄清（C-2 · 请求结构）**：请求沿用 B2F1 已冻结的 `TraceQuery` **5 字段**
  （`run_id` / `thread_id` / `node` / `start_time` / `end_time`，全可空、可组合）；
  本 feature **不新增** `checkpoint_id` / `task_id` / `superstep` 过滤器
  （B18F1 D-2 / B19F1 D-1）。
- **口径澄清（C-3 · 返回结构）**：结果 = B20F1 行视图的 `list[dict]`：
  `kind="span"` 11 字段 + `kind="trace_record"` 13 字段；纯数据、可直接
  `json.dumps`；`span_id` ↔ `id` 关联原样保留。该决定同时满足 C27 ③ 与 B19F1 D-1/D-2。
- **口径澄清（C-4 · 排序 / 时间窗 / 空过滤器）**：默认按**有效起始时刻升序**
  （record 用关联 span 的 `start_time`），平局依次按 `run_id`、`kind`
  （record 先于 span）、稳定标识；时间窗为**闭区间**、按 UTC 瞬时比较；
  空过滤器返回**全部**条目、**无隐式截断**、v1 不提供 `limit` / `offset`。
  这些均为提示词 FR-006 / FR-009 明确要求「写死」的判据。
- **口径澄清（C-5 · SQLite 注入与内部格式）**：
  `SqliteTraceStore(database=..., *, on_error=None)`；表结构 / 列名 / SQL /
  JSONL 行格式是**内部实现细节**（C27 ⑤），对外只暴露 `query()` 与返回结构；
  Studio 不直连 SQLite / JSONL（立项书 §5.8.4）。
- **口径澄清（C-6 · 写侧不变）**：本 feature 在**同一 `FileTraceStore`** 上补齐
  `query()`，并新增 `SqliteTraceStore`；MUST NOT 改变 B20F1 的写侧行为、文件命名、
  `kind` / 字段名、`0o600`、per-instance 锁与四路诊断。B20F1 的「无查询方法」文字 /
  断言按「拆分而不删」登记在 spec 的破冻结面修订清单中。
- **口径澄清（C-7 · 范围）**：不实现 OTLP / UI / Agent Server / Postgres /
  保留期 / 评测；不新增 L1 `Protocol`；唯一新增公开符号为
  `freegraph.observability.SqliteTraceStore`。
- **口径澄清（C-8 · 质量门禁 5）**：真实模型轮由 **B25F1（M4 双跑验收）** 承接
  （沿用 B20F1 先例；承接条款见 B25F1 提示词 §「下游承接（B20F2）」，由 tasks T058 守卫）；
  本 feature 只交付 fake / 本地轮证据，判据未放宽，追认文字由发起者签署。
