# Implementation Plan: B20F2 · Trace 查询 API + SQLite 后端

**Branch**: `b20f2-trace-query-sqlite`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_plan` 钩子；既有 feature 同样在 `main` 上开发）

**Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b20f2-trace-query-sqlite/spec.md`

**Feature ID**: `B20F2`（M3 可诊断 · **第 26 个** · 前置：**B20F1**；承接 **B18F1 / B19F1 / B2F1 / C27 / DF6**；本 feature 完成后解锁 **B21F1**）

> **范围提醒**：本 feature 是 **L5 可观测层的读取侧 + SQLite 持久化后端**。
> 它在 B20F1 的**同一 `FileTraceStore` 对象上补齐查询 API**，并新增
> `SqliteTraceStore`；**MUST NOT** 改变 B20F1 已交付的写侧行为、文件命名、
> `kind` / 字段名、`0o600`、per-instance 锁与四路诊断。
> **不实现** OTLP 导出（B21F1）、前端 / UI（v2 / B26）、本地 Agent Server（v2 / D8）、
> Postgres 后端（v2）、保留期 / 清理（v1 不做）、评测 / 数据集（永不做）。
> `Span` 11 字段、`TraceSink` 3 方法、`TraceRecord` 字段面、`TraceQuery` 5 字段、
> `RunConfig` 9 字段、`freegraph.graph` 门面符号面**一律不改**。

---

## Summary

交付 **本地 trace 的读取侧**：`FileTraceStore.query()` 与新增的
`SqliteTraceStore.query()` 共享同一查询语义，按 **`run_id` / `thread_id` / 时间范围 /
节点名** 四类条件检索本地 trace，返回 **B20F1 落盘行视图的 `list[dict]`**（`kind="span"`
11 字段 + `kind="trace_record"` 13 字段）。新增 **`SqliteTraceStore`** 作为可替换持久化
后端（标准库 `sqlite3`，零第三方依赖），写侧与 `FileTraceStore` 同语义，查询结果逐条等价。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **公开读取载体** | `query(query: TraceQuery \| None = None) -> list[dict[str, Any]]` | 两个后端同一签名；`None` ≡ `TraceQuery()`；空过滤器 = 全取 |
| **四类过滤** | `run_id` / `thread_id` / 时间范围 / 节点名 | **AND** 组合；`None` 不启用；空字符串是字面值 |
| **节点过滤** | 精确 `node` 匹配 | **全部匹配**：节点 span + 内部模型 / 工具 span + record |
| **返回结构** | B20F1 行视图的纯 `dict` 列表 | `kind` 只允许两种；字段 11/13 逐字；额外字段丢弃；JSON 可序列化 |
| **排序** | 有效起始时刻升序 | record 用**同一 `run_id`** 关联 span 的 `start_time`；平局按写死键 |
| **时间窗** | 闭区间 UTC 瞬时 | 精度到纳秒；倒置 ⇒ `[]`；非法串 ⇒ `ValueError` |
| **空过滤器** | 返回全部匹配条目 | **无隐式截断**；v1 不提供 `limit` / `offset` |
| **失败语义** | 尽量容错 + 告警 | 坏行 / 未知 kind / 非白名单 / 符号链接跳过 + WARNING；整库不可读才抛错；只读 |
| **SQLite 后端** | `SqliteTraceStore(database=..., *, on_error=None)` | 标准库 `sqlite3`；写侧同 B20F1；schema 内部；惰性建父目录 / 库 / 表；`0o600` |
| **可替换性** | 同一事件流写入两个后端 | 对同一查询结果逐条相等（A6 / SC-006） |
| **零扩张** | 不改 L1 / 门面 / `runtime.__all__` | 唯一新增公开符号 = L5 `SqliteTraceStore`；`FileTraceStore.query` 是新方法 |

**技术方案（关键落点）**：

| 环节 | 落点 |
|---|---|
| 共享查询引擎 | **新增** `src/freegraph/observability/_query.py`：请求校验 / 时间解析 / 行校验 / 过滤 / 排序（纯函数、无 I/O） |
| 共享行构造 | **新增** `src/freegraph/observability/_payloads.py`：`span_to_dict` / `record_to_dict`（从 `_file_store.py` 纯函数搬迁，写侧语义零改动） |
| JSONL 查询 | **修改** `src/freegraph/observability/_file_store.py`：新增 `query()`；只读扫描白名单文件；写侧行为不变 |
| SQLite 后端 | **新增** `src/freegraph/observability/_sqlite_store.py`：`SqliteTraceStore`（写 + 查询） |
| 导出 | **修改** `src/freegraph/observability/__init__.py`：`__all__` 只增 `SqliteTraceStore` |
| 冻结面更新 | `tests/facade/test_api_snapshot.py` / `tests/contracts/test_b20f1_contracts.py` / `test_b19f1_lazy.py` / `test_b19f1_gates.py` / `test_architecture.py`（**只增 / 拆分**） |
| 测试 | `tests/observability/test_b20f2_*.py` · `tests/contracts/test_b20f2_*.py` · `tests/differential/test_b20f2_trace_query_parity.py` · `tests/runtime/test_b20f2_manual_record_guard.py` |
| 人工验收 | **新增** `harness/verification/B20F2/acceptance.py` + `manual-verification.md`；质量门禁 5 偏离（真实模型轮由 B25F1 承接） |
| 文档联动 | `harness/demo/README.md` 增加 SQLite 后端 / `query()` 稳定接口；`harness/verification/README.md` 更新 B20F2 行 |

**零新增运行时依赖**。**无 ARCH 例外**：新增 L5 模块只 import 标准库 + L1 `Span` /
`TraceQuery` + 同层 `TraceRecord` / `_payloads` / `_query`；`sqlite3` 仅出现在
`_sqlite_store.py`。**唯一冻结面更新**：L5 `observability.__all__` 精确集合**只增**
`SqliteTraceStore`；B20F1 的「无查询方法」断言按**拆分而不删**处理。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`requires-python = ">=3.11"`，本机 `.venv` 为 3.11.16）；
允许标准库 `sqlite3` / `json` / `os` / `pathlib` / `re` / `threading` / `logging` /
`datetime` / `collections.abc` / `typing`。**MUST NOT** 使用 3.12+ 的
`TypeAliasType` / `override` / `TypeIs` / PEP 695 `type`。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []`）。`sqlite3` 属标准库。
开发期：`pytest`（既有 `dev`）· 差分：`differential` 组仅钉 `langgraph==1.2.11`；
`langchain-core==1.7.6` / `langsmith==0.14.17` 为其实测传递版本（as-of `.venv`）。
`pyproject.toml` **零改动** ⇒ G3 / G21 / G22 / G23 恒绿。

**Storage**: 本地 **JSONL 文件**（B20F1，`directory` 注入）+ 本地 **SQLite 文件**
（本 feature，`database` 注入）。**不实现**远端 / Postgres / OTLP 存储。

**Testing**: pytest ——
`tests/observability/test_b20f2_*.py`（查询语义 / 排序 / 类型校验 / 只读容错 /
SQLite 写侧 / 并发 / 后端等价）·
`tests/contracts/test_b20f2_contracts.py` / `test_b20f2_gates.py`（导出面 / 冻结字段 /
L5 依赖方向 / 零 env / 零出站 / 零第三方）·
`tests/differential/test_b20f2_trace_query_parity.py`（D-501…D-508；上游缺席即 skip）·
`tests/runtime/test_acceptance_script.py`（追加 B20F2 一键验收守卫）·
`tests/runtime/test_b20f2_manual_record_guard.py`（SC-015 文档守卫）。

**Target Platform**: Linux / macOS / Windows · CPython 3.11+ · 零出站。
**Windows 必跑**：并发写 + 查询的文件锁差异（spec §风险提示 / FR-020 / SC-011）。

**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A（不设墙钟预算）**。v1 以**正确性 / 后端等价性**优先；
查询不做 SQL 下推、不做分页；本地 trace 规模有限。MUST NOT 用耗时做断言（CI 假红）。

**Constraints**（主要来自 spec）：

| 约束 | spec 条目 |
|---|---|
| 只依赖标准库 + L1；零第三方依赖；`sqlite3` 属标准库 | FR-014 / FR-027 · SC-012 |
| 零出站 / 零环境变量 / 导入无副作用 | FR-026 / FR-027 · SC-012 |
| 两个后端同一 `query(TraceQuery \| None)` 签名 | FR-001 / FR-004 · SC-006 |
| 四类过滤 + AND 组合 + 空过滤器全取 | FR-002 / FR-009 · SC-001…SC-007 |
| 节点过滤「全部匹配」（含模型 / 工具子 span） | FR-008 · SC-004 |
| 返回 B20F1 行视图；字段 11/13 逐字；额外字段丢弃 | FR-003 / FR-004 · SC-008 / SC-014 |
| 稳定排序（有效起始时刻 / 纳秒精度 / 同 run 关联） | FR-006 / FR-007 · SC-009 |
| 时间窗闭区间；非法串 `ValueError`；倒置 `[]` | FR-007 · SC-003 / SC-017 |
| 字段类型错误统一 `TypeError`（读取前） | FR-013 · SC-017 |
| 尽量容错 + 告警；整库不可读才抛错；只读 | FR-010 / FR-011 / FR-012 · SC-013 |
| SQLite 写侧同 B20F1；四路诊断；不重试 | FR-016 / FR-017 / FR-018 · SC-010 / SC-018 |
| SQLite 惰性建父目录 / 库 / 表；`0o600`；已存在不放宽 | FR-019 · SC-018 |
| SQLite 单文件路径；`:memory:` / URI 不支持（构造时 `ValueError`） | FR-015 |
| 跨进程并发 + Windows CI；忙等待超时 | FR-020 · SC-011 |
| schema / 文件格式内部；Studio 只走 `query()` | FR-021 · SC-014 |
| 不扩 L1 / 门面 / `runtime.__all__`；不新增 L1 Protocol | FR-028 / FR-030 · SC-014 |
| OTLP / UI / Agent Server / Postgres / 保留期 / 评估不做 | FR-031 |

> **无未决澄清**：spec 的 clarify 轮裁定 + 形态锁定裁定 + 5 条完备性补丁
> 已收敛全部未决点；本 plan 只落实现方法。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith / 零出站 / 零环境变量） | 零新增依赖；无 env / 网络；G24 / G26 / G27 | 通过 |
| 原则 II（零 LangChain · 状态语义等价） | 不 import `langchain*` / `langgraph*` / `langsmith`；既有回归保持 | 通过 |
| 原则 III（验收契约优先 · `target.py` 只读） | `target.py` **零改动**；不改变 `compile(tracer=...)` 形态 | 通过 |
| 原则 IV（可诊断性 · 可视化不阻断） | 查询不在运行时自动执行；写入失败隔离沿用 B20F1；查询只读 | 通过 |
| 原则 V（人工验收） | `harness/verification/B20F2/manual-verification.md` + 零出站证据 + **质量门禁 5 偏离**（真实模型轮由 B25F1 承接；沿用 B20F1 先例；T058 守卫接线） | 计划交付（偏离已登记） |
| 原则 VI（规格驱动 · 判据级覆盖） | spec FR-001…FR-034 / SC-001…SC-018 · tasks 追溯（/speckit.tasks）· **SC-015 文档守卫** | 通过（补齐后） |
| 原则 VII（职责边界 · C27 / DF6） | 只做 C27 的读取侧 + SQLite 后端；不改 L1 契约面；不新增过滤维度 | 通过 |
| 原则 VIII（证据与术语） | spec P-01…P-07 / E-1…E-3 / D-501…D-508 + `路径:行号`；`query` / `TraceQuery` / `kind` 术语统一 | 通过 |
| 原则 IX（许可证 / 商标） | 零新增依赖 ⇒ `THIRD_PARTY_NOTICES` 零变更 | 通过 |
| 原则 X（署名头 / 文档） | 新增 `_query.py` / `_payloads.py` / `_sqlite_store.py` 带署名头；README 更新 | 通过 |
| 原则 XI（上游优先） | 上游无本地查询（自研区 ③）；失败隔离 / 默认关闭 / 零出站对齐；空过滤器仅作表示层说明（不标 SAME 行为面）；D-501…D-508；P ↔ X 三态一致 | 通过（X-1…X-8） |
| 原则 XII（最优设计 / 零重复载体） | **共享 `_query.py`**（过滤 / 排序 / 校验）与 `_payloads.py`（行构造）；不另立第二套序列化 | 通过 |
| 立项书 **ARCH-1**（单向依赖） | L5 → L1（`Span` / `TraceQuery`）+ 同层；`sqlite3` 仅 `_sqlite_store.py`；无 L5 → L2/L3/L4 | 通过 |
| 立项书 **ARCH-2**（顶层惰性） | `import freegraph` 不加载 L5；`SqliteTraceStore` 不进 `freegraph.graph` | 通过 |
| 立项书 **ARCH-3**（跨层只经协议 + 纯数据） | 只消费 `Span` / `TraceRecord` 纯数据；查询返回纯 `dict` | 通过 |
| **L5 依赖面断言**（B18F1 / B19F1 / B20F1） | 新模块只 import 标准库 + `freegraph.contracts` + 同层相对导入 | 通过（无需拆分） |
| **B20F1 的 `observability.__all__` 精确集合** | 只增 `SqliteTraceStore`；既有 6 符号逐字保留 | 更新（非放宽） |
| **B20F1 的「无查询方法」断言** | 拆分而不删：保留写侧 / 生命周期断言；把 `query` 从「禁止」改为「B20F2 新增」 | 更新（非放宽） |

### 冻结面 / 回溯修订清单

| 冻结面 | 回溯修订位置 | 处置 | 追认 |
|---|---|---|---|
| `freegraph.observability.__all__` 精确集合断言（B20F1） | `tests/facade/test_api_snapshot.py` 的精确集合；`tests/contracts/test_b19f1_lazy.py` 的成员断言 | **只增不改**：新增 `SqliteTraceStore`；既有 `FileTraceStore` / `SpanProducer` / `TraceRecord` / `current_span` / `invoke_model` / `invoke_tool` 逐字保留；`trace_run_scope` 仍不导出 | `harness/verification/B20F2/manual-verification.md` 追认 |
| B20F1 的「`FileTraceStore` 公开面**没有**查询方法」断言 / 文字 | `tests/contracts/test_b20f1_contracts.py::test_public_face_is_write_only_and_has_diagnostics`；`specs/b20f1-local-trace-jsonl/spec.md` 的 Clarifications / SC-006 文字；`specs/b20f1-local-trace-jsonl/contracts/file-trace-store-contract.md` §1 / §8 | **拆分而不删**：保留写侧 4 方法 + 2 诊断属性 + 无生命周期断言；`queries` 期望由 `[]` 改为 `["query"]`；`search` / `read` / `read_all` 仍禁止；B20F1 文字**只追加**「查询方法归 B20F2，写侧不变」的说明，不删除原事实 | 同上；B20F1 记录不回溯改写 |
| `SIGNED_SOURCE_FILES` / L5 门禁扫描清单 | `tests/contracts/test_architecture.py` · `tests/contracts/test_b19f1_gates.py` | 追加 `_query.py` / `_payloads.py` / `_sqlite_store.py`（**只增**）；原断言继续覆盖既有模块 | 同上 |
| **不破** | `Span` 11 字段 · `TraceSink` 3 方法 · `TraceRecord` 13 字段 · `TraceQuery` 5 字段 · `RunConfig` 9 字段 · `SuperStepResult` / `PregelTask` · `stream()` 信封 · 门面 8 符号 · L1 22 符号 · `freegraph.runtime.__all__` · B20F1 JSONL 写侧行结构 / 文件命名 / `kind` / `0o600` / 锁 / 四路诊断 | 零改动 | — |

**无 ARCH-1 / ARCH-3 例外**：本 feature 不需要 L3 → L5 或 L5 → L2 的新接缝。

### 质量门禁 5 偏离登记（2026-11-21 · 发起者选择 A；2026-11-22 确认沿用 B20F1 先例）

| 项 | 内容 |
|---|---|
| 被偏离门禁 | 质量门禁 5「人工验证记录，含真实模型一轮」 |
| 根因 | B20F2 是 L5 本地 trace 读取层 + SQLite 后端；验收对象是过滤语义 / 排序 / 后端等价 / 并发读写，真实模型轮不产生本 feature 的新判据。**沿用 B20F1（2026-11-21 · 发起者选择 A）的同一偏离口径**；判据未放宽。 |
| 判据未放宽 | 本地图 + fake 模型 / 本地 sink 的轮次照常；四类过滤、组合、空过滤器、排序、JSON 序列化、两后端等价、零出站、零 env、写侧回归**一字未改** |
| 承接方 / 机制 | **B25F1（M4 · 双跑验收）** 补真实模型轮（含 `SqliteTraceStore` / `FileTraceStore` 查询证据；承接条款已写入 `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B20F2）」，由 T058 守卫）；B21F1（OTLP）可选复用；B20F2 只交付 fake / 本地轮证据 |
| 追认 | 发起者 2026-11-21 **选择 A（登记偏离）**；2026-11-22 分析会话**确认沿用 B20F1 先例**并补 B25F1 接线；正式追认文字 + 确认人 + 日期落 `harness/verification/B20F2/manual-verification.md`，由发起者本人签署 |

### Post-Design Re-check（Phase 1 后）

| 检查 | 结果 |
|---|---|
| L1 符号面仍 22 / 门面仍 8 / `runtime.__all__` 不变 | ✅（只新增 L5 `SqliteTraceStore`） |
| `import freegraph` 仍只加载 `freegraph` | ✅（L5 惰性） |
| `Span` / `TraceSink` / `TraceRecord` / `TraceQuery` / `RunConfig` 零改动 | ✅ |
| `FileTraceStore` 写侧行为 / 文件格式 / 锁 / 诊断零改动 | ✅（只加 `query()`；纯函数搬迁） |
| JSONL / SQLite 查询结果逐条等价 | ✅（共享 `_query.py` + `tests/observability/test_b20f2_backend_parity.py`） |
| 四类过滤 / 组合 / 空过滤器 / 排序 / 时间窗 | ✅（见 `contracts/query-api-contract.md`） |
| 容错 / 只读 / 类型校验 / 未知 kind / 符号链接 | ✅（见 `contracts/query-api-contract.md` §7–§9） |
| SQLite 惰性建库 / 权限 / 并发 / Windows | ✅（见 `contracts/sqlite-store-contract.md`） |
| 上游差分组 D-501…D-508 有落点；X-1…X-8 与 P-01…P-07 三态一致 | ✅（见 `contracts/upstream-parity.md`） |
| 人工验证记录 + 一键验收脚本 | ✅（`harness/verification/B20F2/`） |
| 质量门禁 5 偏离 + 文档守卫 | ✅（`tests/runtime/test_b20f2_manual_record_guard.py`；B25F1 承接真实模型轮） |

---

## Project Structure

### Documentation (this feature)

```text
specs/b20f2-trace-query-sqlite/
├── plan.md                              # 本文件
├── research.md                          # Phase 0
├── data-model.md                        # Phase 1
├── quickstart.md                        # Phase 1
├── contracts/
│   ├── query-api-contract.md            # 请求 / 返回 / 过滤 / 排序 / 时间 / 失败 / 边界
│   ├── sqlite-store-contract.md         # 构造 / 写侧 / schema / 并发 / 权限 / 生命周期
│   └── upstream-parity.md               # P-01…P-07 / D-501…D-508 / X-1…X-8 / 冻结面
├── checklists/
│   └── requirements.md
└── tasks.md                             # Phase 2（/speckit.tasks）
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/
│   └── trace.py                         # L1：Span / TraceQuery（零改动；只消费）
└── observability/                       # L5
    ├── __init__.py                      # 修改：__all__ 只增 SqliteTraceStore
    ├── _file_store.py                   # 修改：新增 query()；写侧行为不变
    ├── _payloads.py                     # 新增：span_to_dict / record_to_dict（共享行构造）
    ├── _query.py                        # 新增：请求校验 / 时间解析 / 行校验 / 过滤 / 排序
    ├── _sqlite_store.py                 # 新增：SqliteTraceStore（写 + 查询）
    ├── _producer.py                     # 既有（B18F1 / B19F1；零改动）
    ├── _record.py                       # 既有：TraceRecord.to_jsonable（零改动）
    ├── _inject.py                       # 既有（B19F1；零改动）
    └── _invoke.py / _time.py            # 既有（零改动）

tests/
├── observability/
│   ├── test_b20f2_query_api.py          # run / thread / 空过滤器 / 字段 / JSON
│   ├── test_b20f2_query_time.py         # 时间窗 / 纳秒 / 时区 / 倒置 / 有效起始时刻
│   ├── test_b20f2_query_node.py         # 节点精确匹配 + 模型 / 工具子 span + record
│   ├── test_b20f2_query_result.py       # 排序 / 独立副本 / JSON 断言 / 重复查询
│   ├── test_b20f2_query_validation.py   # 类型错误 / 坏时间 / 倒置 / 读取前校验
│   ├── test_b20f2_query_tolerance.py    # 坏行 / 未知 kind / 字段残缺 / 额外字段 / 符号链接 / 非白名单
│   ├── test_b20f2_query_read_only.py    # 缺失存储 / 目录是文件 / 不建文件 / 哈希不变
│   ├── test_b20f2_sqlite_write.py       # 写侧同 B20F1 / 四路诊断 / 不重试
│   ├── test_b20f2_sqlite_lifecycle.py   # 惰性建父目录 / 库 / 表 / 0o600 / 已存在不放宽 / 无 close
│   ├── test_b20f2_sqlite_concurrency.py # 并发写 + 查询 / 跨线程 / 跨进程 / busy timeout
│   └── test_b20f2_backend_parity.py     # A6 / SC-006：同一事件流两后端逐条等价
├── contracts/
│   ├── test_b20f2_contracts.py          # 导出面 / 查询签名 / 冻结字段 / L5 依赖 / 无 schema 泄漏
│   ├── test_b20f2_gates.py              # 零 env / 零出站 / 零第三方 / sqlite3 仅 SQLite 模块
│   ├── test_b19f1_lazy.py               # 更新：SqliteTraceStore 在 observability.__all__
│   ├── test_b19f1_gates.py              # 更新：新模块纳入扫描（只增）
│   ├── test_b20f1_contracts.py          # 更新：FileTraceStore.query 允许（拆分）
│   └── test_architecture.py             # 更新：SIGNED_SOURCE_FILES 追加新文件（只增）
├── facade/
│   └── test_api_snapshot.py             # 更新：observability.__all__ 精确集合（只增）
├── differential/
│   └── test_b20f2_trace_query_parity.py # D-501…D-508（上游缺席即 skip）
└── runtime/
    ├── test_acceptance_script.py        # 追加 B20F2 一键验收守卫
    └── test_b20f2_manual_record_guard.py# SC-015 文档守卫

harness/
├── demo/
│   └── README.md                        # 更新：SQLite 后端 / query() 稳定接口
└── verification/
    ├── README.md                        # 更新 B20F2 记录行
    └── B20F2/
        ├── acceptance.py                # 一键验收 A1–A6
        └── manual-verification.md       # 人工验证记录 + 冻结面追认 + 门禁 5 偏离
```

**Structure Decision**: 单包库（发行名 = 导入名 = `freegraph`）。本 feature 不在仓库根新增
目录；只新增 L5 私有模块、测试、验收脚本与文档更新。`_file_store.py` 保持写侧实现，
仅新增 `query()` 与改用共享行构造；`_sqlite_store.py` 独立承载 SQLite 写 + 查询。

---

## Phase 0: Research（摘要 · 详见 [research.md](./research.md)）

| # | 决策 | 理由 | 备选 |
|---|---|---|---|
| **D-01** | 公开读取载体 = 两个 store 上同一 `query(query: TraceQuery \| None = None) -> list[dict]` | spec 锁定；C27 ④ 可替换；复用 B2F1 冻结 `TraceQuery` | 新增 L1 Protocol / 独立函数 / 返回对象（拒绝） |
| **D-02** | 共享查询引擎 `_query.py`：请求校验 / 时间解析 / 行校验 / 过滤 / 排序 | 一套语义两后端共用，A6 可判定；避免过滤 / 排序漂移 | 每后端各写一套（拒绝：漂移）；SQL 下推（v1 拒绝：等价性优先） |
| **D-03** | 共享行构造 `_payloads.py`：`span_to_dict` / `record_to_dict` | 两后端返回同一 B20F1 行视图；只搬纯函数，不改写侧行为 | 复制两套（拒绝：重复载体）；从 `_file_store` 反向 import（拒绝：耦合） |
| **D-04** | JSONL 查询：只读扫描白名单 `trace-<run_id>.jsonl`；不跟随候选符号链接；坏行 / 未知 kind / 字段残缺跳过 + WARNING | spec FR-024/025 + 容错裁定；不要求 B20F1 加读方法 | 让 B20F1 提供查询（拒绝：越界）；宽松读所有 `trace-*.jsonl`（拒绝：外部文件） |
| **D-05** | SQLite 内部 schema = 单表 `trace_entries`（payload + 索引列）；写时 `CREATE TABLE IF NOT EXISTS`；查询读全部 payload 后走共享引擎 | schema 是内部细节；v1 正确性 / 等价性优先；本地规模有限 | 多表规范化 / SQL 下推（v1 拒绝：复杂度 / 等价风险） |
| **D-06** | SQLite 连接 = 每次操作短生命周期连接；per-instance 锁串行；`busy_timeout` 有限；跨进程依赖 SQLite 文件锁 | 避免线程亲和 / 持久句柄 / 生命周期 API；与 B20F1 逐行短生命周期口径一致 | 持久连接 / 连接池 / 模块全局锁（拒绝） |
| **D-07** | SQLite 惰性建父目录 / 库 / 表；新建库 `0o600`；已存在不放宽；`:memory:` / URI 构造时拒绝；写入失败四路诊断；不重试 | spec FR-015 / FR-017…FR-019 / SC-018；与 B20F1 一致 | 自动迁移 / 放宽权限 / 重试 / `:memory:` 静默（拒绝） |
| **D-08** | 查询结果行 = 严格 B20F1 行视图：必需字段 + 类型校验；额外字段丢弃；未知 kind 跳过 | spec §4 / §8；结果契约稳定；CI 断言可直接用 | 原样返回未知字段 / 宽松结构（拒绝） |
| **D-09** | 时间：解析为 UTC **纳秒**瞬时；闭区间；有效起始时刻 = span `start_time` / 同 run 关联 span 的 `start_time`；倒置 ⇒ `[]` | spec §5 / §6；避免 `datetime` 微秒截断；record 无时刻时排最后 | 字符串简单比较（对非规范串不安全）/ 区间相交（拒绝：spec 锁定） |
| **D-10** | 排序：有时刻在前；`(start_ns, run_id, kind_rank, stable_id)`；无时刻 record 按 `(run_id, superstep, task_id, span_id)`；record 先于 span | spec §5；两后端共享；重复行相对顺序不影响 | 按文件行序 / 插入序（拒绝：跨后端不等价） |
| **D-11** | 容错：坏行 / 单文件不可读 / 未知 kind / 不兼容旧表 ⇒ 跳过 + WARNING；目录是文件 / 全部候选不可读 / SQLite 损坏 ⇒ 抛错；只读 | 用户 clarify A；trace 诊断价值；绝不改数据 | 严格抛错 / 全吞返回 [] / 自动修复（拒绝） |
| **D-12** | 请求校验：`query` 非 `TraceQuery` / `None` 或 5 字段非 `str` / `None` ⇒ 读取前 `TypeError`；坏时间串 ⇒ `ValueError` | 用户 clarify A；错误早暴露 | 静默空结果 / 宽松转换（拒绝） |
| **D-13** | SQLite 写侧诊断**本地实现**（同语义），不重构 `FileTraceStore._report` | 避免改 B20F1 写侧 / 测试；行为由 `test_b20f2_sqlite_write.py` 对齐 | 抽共享 diagnostics 并改 B20F1（拒绝：风险 > 收益） |
| **D-14** | 不新增 L1 Protocol；导出仅 `SqliteTraceStore`；`FileTraceStore.query` 视为新方法 | spec FR-030；L1 冻结；C27 ④ 由同一签名满足 | 新增 `TraceStore` Protocol（拒绝：契约修订） |
| **D-15** | 测试 / 一键验收 / 差分 / README / 人工验证全部落点；质量门禁 5 偏离由 B25F1 承接 | 原则 VI / V / XI；判据级覆盖 | 只写单元测试（拒绝：不满足门禁） |

**无未决澄清。**

---

## Phase 1: Design（摘要）

- **[data-model.md](./data-model.md)**：`TraceQuery` / 查询结果行 / `FileTraceStore` 查询扩展 /
  `SqliteTraceStore` 形态 / 内部 SQLite 表 / 查询流水线 / 行校验规则 / 时间与排序 /
  并发与权限 / 不变量。
- **[contracts/query-api-contract.md](./contracts/query-api-contract.md)**：
  公开签名 / 请求 / 返回 / 四类过滤 / 排序 / 时间 / 空过滤器 / 失败 / 只读 / 类型校验 /
  后端替换 / 内部格式边界。
- **[contracts/sqlite-store-contract.md](./contracts/sqlite-store-contract.md)**：
  构造 / 公开面 / 写侧 / schema / 生命周期 / 并发 / 权限 / 失败 / 查询。
- **[contracts/upstream-parity.md](./contracts/upstream-parity.md)**：P-01…P-07、E-1…E-3、
  D-501…D-508、X-1…X-8、冻结面 / 回溯修订。
- **[quickstart.md](./quickstart.md)**：端到端验证（JSONL / SQLite 查询、四类过滤、组合、
  空过滤器、排序、容错、并发、两后端等价、命令、人工记录）。

---

## Risks & Registrations

| # | 风险 / 事项 | 处置 |
|---|---|---|
| **R-1** | `observability.__all__` 精确集合断言会红 | **只增不改**：新增 `SqliteTraceStore`；更新 `test_api_snapshot.py` / `test_b19f1_lazy.py`；既有 6 符号逐字保留；追认进 manual-verification |
| **R-2** | B20F1「无查询方法」断言会红 | **拆分而不删**：`test_b20f1_contracts.py` 保留写侧 / 生命周期 / `search` / `read` 断言；`query` 改为允许；同时按 B-3 / T016 追加 B20F1 spec / contract 说明；不弱化其它判据 |
| **R-3** | 两后端过滤 / 排序语义漂移 | 共享 `_query.py`；`test_b20f2_backend_parity.py` 对同一事件流逐条比对 |
| **R-4** | 时间纳秒精度 / 时区 / 倒置 | `_query.parse_instant_ns` 单元测试覆盖 9 位小数 / `Z` / 偏移 / 无时区 / 非法串；倒置 ⇒ `[]` |
| **R-5** | JSONL 坏行 / 半行 / 符号链接 / 非白名单 | 逐类测试；跳过 + WARNING；整库不可读才抛错；只读哈希断言 |
| **R-6** | SQLite schema 不兼容 / 单行 `payload` JSON 损坏 | `PRAGMA table_info` 校验列；不兼容 ⇒ `[]` + WARNING；单行 `payload` 解码失败（含 `input_state` / `output_state` / `error`）⇒ 跳过；不自动迁移 |
| **R-7** | SQLite 权限 / 父目录 | 预创建 `0o600`；惰性建父目录；已存在不放宽；父目录不可写 ⇒ 写入失败隔离 |
| **R-8** | Windows 文件锁差异 | `busy_timeout` 有限；并发用例在 Windows CI 跑；超时按写入失败隔离 / 查询异常交调用方 |
| **R-9** | 查询无上限 / 大结果集 | spec 锁定无隐式截断；文档说明调用方控制规模；不做墙钟断言 |
| **R-10** | 文档守卫 / README 更新遗漏 | `test_b20f2_manual_record_guard.py` 断言记录与 README；守卫安排在记录写就后 |
| **R-11** | 真实模型轮 | **已登记质量门禁 5 偏离（2026-11-21 · 发起者选择 A；2026-11-22 确认沿用 B20F1 先例）**：B20F2 只跑本地图 + fake 模型；真实模型轮由 **B25F1（M4）** 承接；承接条款已写入 B25F1 提示词并由 T058 守卫；正式追认文字由发起者本人签署 |
| **R-12** | 动 B20F1 写侧 | `FileTraceStore` 只加 `query()` + 改用 `_payloads` 纯函数；写侧行为由既有 B20F1 回归守护；不重排 / 不改字段 / 不改锁。`SqliteTraceStore` 写侧 MUST 同步 B20F1 的两处隐含 parity：开始快照（`end_time is None`）no-op、`run_id` 安全 allowlist；由 T021 / T022 / T023 守护 |

---

## Green Baseline & Red List（宪法 v1.11.0 的基线义务）

### 基线（**2026-11-22 · 实施前实跑**）

```text
.venv/bin/python -m pytest -q --tb=no
1991 passed, 7 skipped in 137.60s (0:02:17)
```

**跳过项**（既有环境 / 开关 skip，非本 feature 相关）：
C8 元测试占位 · `IPython` 缺失的 PNG 用例 · `mypy` 未安装 · 上游 PNG 未开启 ·
API 快照未开启更新 · Windows 分支（B20F1 权限） · Windows 时钟精度档。

### 变红清单（**预登记** · 实测后 MUST 逐条核对）

| # | 可能变红的既有断言 | 变红原因 | 处置 |
|---|---|---|---|
| **B-1** | `tests/facade/test_api_snapshot.py::test_observability_module_exports_only_its_own_symbols` | `observability.__all__` 新增 `SqliteTraceStore` | **更新（非放宽）**：集合加入 `SqliteTraceStore`；既有 6 符号逐字保留 |
| **B-2** | `tests/contracts/test_b19f1_lazy.py` | 需断言 `SqliteTraceStore` 在 `observability.__all__` | **只增**断言；`trace_run_scope` 仍不在；`FileTraceStore` 仍只 L5 |
| **B-3** | `tests/contracts/test_b20f1_contracts.py::test_public_face_is_write_only_and_has_diagnostics`；`specs/b20f1-local-trace-jsonl/spec.md` 的 SC-006 / Clarifications；`specs/b20f1-local-trace-jsonl/contracts/file-trace-store-contract.md` §1 / §8 | `queries` 期望 `[]` / B20F1 写「不提供查询」；B20F2 新增 `query` | **拆分而不删**：`queries` 期望改为 `["query"]`；写侧 4 方法 + 2 诊断 + 无生命周期断言保留；`search` / `read` / `read_all` 仍禁止；B20F1 文字**只追加**「查询归 B20F2，写侧不变」的说明，不删除原事实 |
| **B-4** | `tests/contracts/test_b19f1_gates.py` 的 `paths` / `test_no_network_client_is_used_by_new_modules` | 新模块未纳入扫描 | 追加 `_query.py` / `_payloads.py` / `_sqlite_store.py`（**只增**） |
| **B-5** | `tests/contracts/test_architecture.py::TestSignatureHeader` | 新源文件未登记署名头清单 | 追加 3 个新源文件（**只增**） |
| **B-6** | `tests/contracts/test_b20f1_gates.py` 的 `FORBIDDEN_ROOTS` 含 `sqlite3` | 若 `_file_store.py` 引入 `sqlite3` | **保持绿**：`_file_store.py` 仍不 import `sqlite3`；SQLite 只在 `_sqlite_store.py` |
| **B-7** | `tests/contracts/test_b20f1_contracts.py::test_file_store_imports_only_stdlib_l1_and_same_layer` | 新同层相对导入 | **保持绿**：相对导入 `level=1` 不被绝对 import 扫描计入；只 import 标准库 + L1 + 同层 |
| **B-8** | `tests/runtime/test_b20f1_manual_record_guard.py` | `harness/demo/README.md` 需保留 B20F1 行 | **保持绿**：只追加 B20F2 行；`已锁定（B20F1）` 与 `FileTraceStore(directory=` 逐字保留 |
| **B-9** | `tests/facade/_gatesupport.py` 的 `SIGNED_SOURCE_FILES` | B2F2 专用清单，不含 L5 | **零改动**；B20F2 只更新 `test_architecture.py` 的清单 |
| **B-10** | 全量测试计数 | 新增测试 | 只增不减；基线 1991 passed 不下降 |
| **B-11** | `harness/verification/README.md` | 新 feature 记录行 | 追加 B20F2 行；既有行逐字保留 |
| **B-12** | `tests/runtime/test_acceptance_script.py` | 新一键验收 | 追加 B20F2 守卫；既有 B13F1 / B8F3 / B18F1 / B19F1 / B20F1 用例保留 |
| **B-13** | SC-015 文档守卫 | 守卫断言人工记录 / README；若在记录写就前加入会永久红 | **守卫安排在记录写就后**；MUST NOT 为转绿而弱化断言 |

> 实施前 MUST 重跑基线；若变红，先判「是否由本 feature 落地形态导致」→ 再判「是否属冻结断言」；
> **MUST NOT** 以「实现期再说」放过。**B-10 是硬约束**：不得靠修改既有测试来「修复」。

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **无** | 本 feature 无 ARCH-1 / ARCH-3 例外；L5 只 import L1 + 同层 + 标准库（`sqlite3` 仅 `_sqlite_store.py`） | 若把查询放 L2 / 门面会破分层；若引入第三方 ORM 会破零依赖 |
| **新增 3 个内部模块** | `_query.py`（共享语义）/ `_payloads.py`（共享行构造）/ `_sqlite_store.py`（后端） | 把全部塞进 `_file_store.py` ⇒ 职责混杂 / SQLite 污染 JSONL 模块；每后端各写一套 ⇒ 语义漂移 |

> 唯一「冻结面更新」是 L5 `observability.__all__` 精确集合**只增** `SqliteTraceStore`
> 与 B20F1「无查询方法」断言的**拆分**；均属**更新（非放宽）**，已登记在
> `contracts/upstream-parity.md` §5 与 spec §5。

---

## Implementation Sequencing（供 /speckit.tasks 展开）

1. **Setup / Foundational**：新增 `_payloads.py`（纯函数搬迁）/ `_query.py`（请求校验 /
   行校验 / `finalize` 的 run/thread 骨架）；`_file_store.py` 改用 `_payloads`；
   导出面 / 扫描清单 / 署名清单更新。
2. **US1（按 run / thread）**：`_query.finalize` 的 `run_id` / `thread_id` 过滤；
   `FileTraceStore.query()` 文件枚举 + 白名单 + 坏行容错；`test_b20f2_query_api.py` 的 A1/A2。
3. **US2（时间）**：`_query.parse_instant_ns` + 在 `finalize` 增加有效起始时刻 / 闭区间 / 倒置；
   `test_b20f2_query_time.py`；A3。
4. **US5（两后端）**：`_sqlite_store.py` 写侧 + 查询；`test_b20f2_backend_parity.py`；
   A6 / SC-006。
5. **US3（节点）**：在 `finalize` 增加 `node` 精确匹配（含模型 / 工具子 span）；record `node`；
   `test_b20f2_query_node.py`；A4。
6. **US4（CI 断言）**：在 `finalize` 增加完整排序键 / 独立副本 / 连续查询相等；
   `test_b20f2_query_result.py`；A5。
7. **SQLite 生命周期 / 并发 / 权限**：惰性建父目录 / 库 / 表；`0o600`；busy timeout；
   跨线程 / 跨进程 / Windows CI；`test_b20f2_sqlite_*.py`。
8. **容错 / 只读 / 类型校验**：坏行 / 未知 kind / 字段残缺 / 额外字段 / 非白名单 /
   符号链接 / 不兼容旧表 / 单行 `payload` JSON 损坏；`test_b20f2_query_tolerance.py` /
   `test_b20f2_query_read_only.py`。
9. **契约 / 差分 / 文档**：`test_b20f2_contracts.py` / `test_b20f2_gates.py` /
   `test_b20f2_trace_query_parity.py` / README / acceptance / manual-verification；
   **T058** 守卫 B25F1 §「下游承接（B20F2）」（MUST 早于 T052）。
10. **Polish**：全量回归、G21/G24/G26/G27、人工验收记录、冻结面追认。
11. **Coverage Closure**：`test_b20f2_manual_record_guard.py`（SC-015）安排在记录写就后；
    B20F1 断言拆分追认；B25F1 承接真实模型轮的说明（T058 / T055）。

---

## Notes

- `harness/demo/target.py` **零改动**（只读基准）。
- 不新增运行时依赖、不新增 L1 / 门面 / `runtime.__all__` 符号。
- `Span` / `TraceRecord` / `TraceSink` / `TraceQuery` / `RunConfig` / `SuperStepResult` /
  `PregelTask` **零改动**；两个 store 只消费。
- `FileTraceStore` 写侧（`on_span_start` / `on_span_end` / `on_trace_record` /
  `current_span` / 文件命名 / `kind` / `0o600` / per-instance 锁 / 四路诊断）**逐字不变**；
  只新增 `query()` 与改用 `_payloads` 纯函数。
- SQLite schema / 表名 / 列名 / SQL / JSONL 行格式是 C27 ⑤ 的**内部实现细节**；
  Studio / 测试 / 用户只能经 `query()` 取数。
- 人工验证记录：`harness/verification/B20F2/manual-verification.md`
  （四类过滤 / 组合 / 空过滤器 / 排序 / 两后端等价 / 并发 / 零出站 /
  `__all__` 与 B20F1 断言修订追认 / **质量门禁 5 偏离声明 + 发起者追认**）；
  由 `tests/runtime/test_b20f2_manual_record_guard.py` 自动守卫。
- 一键验收：`harness/verification/B20F2/acceptance.py`（A1–A6）。
- **质量门禁 5**：本 feature 只跑 fake / 本地轮；真实模型轮由 **B25F1（M4）** 承接
  （承接条款已写入 `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B20F2）」，
  由 T058 守卫；B21F1 可选复用）；正式追认文字由发起者本人签署，**MUST NOT** 由实现者代签。
