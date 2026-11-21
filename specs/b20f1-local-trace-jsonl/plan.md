# Implementation Plan: B20F1 · 本地 Trace 存储：JSONL 文件后端（零依赖）

**Branch**: `b20f1-local-trace-jsonl`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_plan` 钩子；既有 feature 同样在 `main` 上开发）
| **Date**: 2026-11-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b20f1-local-trace-jsonl/spec.md`

**Feature ID**: `B20F1`（M3 可诊断 · **第 25 个** · 前置：**B19F1**；承接 **B18F1 / B19F1 / B2F1 / C23 / C27**；本 feature 完成后解锁 **B20F2**）

> **范围提醒**：本 feature 是 **L5 可观测层的写入侧**。只把 B18F1 的 `Span` 与 B19F1 的
> `TraceRecord` **原样**持久化为本地 JSONL；**不实现查询 API / SQLite 后端**（B20F2）、
> **不实现 OTLP 导出**（B21F1）、**不实现前端 / UI**（v2 / B26）。`Span` 11 字段、
> `TraceSink` 3 方法、`TraceRecord` 字段面、`RunConfig` 9 字段、`SuperStepResult` /
> `PregelTask`、`freegraph.graph` 门面符号面**一律不改**。

---

## Summary

交付 **`freegraph.observability.FileTraceStore`**：一个零第三方依赖、零出站、默认关闭的
**JSONL 文件后端**。用户通过 B19F1 已锁定的 `compile(tracer=FileTraceStore(directory=...))`
注入；每个 `run_id` 写一个 `trace-<run_id>.jsonl`，文件含 `kind="span"`（`Span` 全部
11 字段）与 `kind="trace_record"`（B19F1 `to_jsonable()` 全部字段）两类行。写入失败
**不阻断图执行**，但通过 `write_errors` / `last_error` / 可选 `on_error` / `logging.WARNING`
四路可感知；每行 `flush` 即成功、不逐行 `fsync`、不重试、每行独立 `open → append →
flush → close`、每个 store 实例一把锁。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **公开载体** | `FileTraceStore(directory, *, on_error=None)` | `directory` 必填；无默认目录；经 `compile(tracer=...)` 注入 |
| **文件粒度** | 每个 `run_id` 一个 `trace-<run_id>.jsonl` | 惰性建目录；追加；不同 run 不混写 |
| **span 行** | `kind="span"` + `Span` 11 字段 | 在 `on_span_end` 写；开始回调不写盘 |
| **record 行** | `kind="trace_record"` + `to_jsonable()` 13 字段 | 在 `on_trace_record` 写；字段名不改 |
| **行序** | 按 B19F1 回调到达顺序 | 同一节点 record 行在 span 行之前；不排序 / 不聚合 |
| **持久化** | 每行 `flush` 到 OS 即成功 | 不逐行 `fsync`；进程崩溃不丢已 flush 行；断电可丢最后若干行 |
| **权限** | POSIX 新建文件 `0o600` | 仅本人可读写；不提供权限配置；Windows 由 ACL 解释 |
| **生命周期** | 每行独立 `open → append → flush → close` | 不提供 `close()` / 上下文管理器 / 持久句柄 |
| **并发** | 每个 `FileTraceStore` 实例一把 `threading.Lock` | 不共享模块级全局锁 / 不建「每 run 锁表」；`on_error` 在锁外 |
| **失败** | 不阻断运行 + 四路诊断 | `write_errors` / `last_error` / `on_error` / `logging.WARNING`；不重试；截断半行 |
| **默认关闭** | 未注入 ⇒ 零文件 / 零目录 / 零 env | 只构造不运行也零副作用；`import freegraph` 仍惰性 |
| **零扩张** | 不改 L1 / 门面 / `runtime.__all__` | 唯一新增公开符号 = L5 `FileTraceStore` |

**技术方案（关键落点）**：

| 环节 | 落点 |
|---|---|
| 新模块 | **新增** `src/freegraph/observability/_file_store.py`：`FileTraceStore` |
| 导出 | `src/freegraph/observability/__init__.py`：新增 `FileTraceStore` 到 `__all__`（不进 `freegraph.graph`） |
| span 视图 | 手工构造 11 字段 dict（**不**依赖 `dataclasses.asdict` 的深拷贝）；`kind` 为唯一新增字段 |
| record 视图 | 直接 `record.to_jsonable()` + `kind`；不重新降级 / 不改字段名 |
| 写盘 | `json.dumps(..., ensure_ascii=False)` → 实例锁内 `mkdir → os.open(0o600) → 写行 → flush → close` |
| 失败 | `Exception` 隔离；记 `write_errors` / `last_error`；截断回写前偏移；`on_error` 锁外调用；不重试 |
| 测试 | `tests/observability/` · `tests/contracts/` · `tests/facade/` · `tests/differential/` · `tests/runtime/test_acceptance_script.py` |
| 人工验收 | **新增** `harness/verification/B20F1/acceptance.py` + `manual-verification.md` + **T053 文档守卫**；质量门禁 5 偏离（真实模型轮由 B25F1 承接） |
| 文档联动 | `harness/demo/README.md` 的「本地 trace 存储目录的参数名」标为**已锁定**；`harness/verification/README.md` 更新 B20F1 行（T049） |

**零新增运行时依赖**。**无 ARCH 例外**：L5 `_file_store.py` 只 import 标准库 + L1 `Span` +
同层 `TraceRecord`，不 import L2 / L3 / L4。**唯一冻结面更新**：L5
`observability.__all__` 精确集合断言**只增** `FileTraceStore`（更新非放宽）。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`requires-python = ">=3.11"`）；
允许 `json` / `os` / `pathlib` / `threading` / `logging` / `collections.abc` / `typing`。
**MUST NOT** 使用 3.12+ 的 `TypeAliasType` / `override` / `TypeIs` / PEP 695 `type`。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []`）。
开发期：`pytest`（既有 `dev`）· 差分：`langgraph==1.2.11` / `langchain-core==1.7.6` /
`langsmith==0.14.17`（既有 `differential` 组）。`pyproject.toml` **零改动** ⇒
G3 / G21 / G22 / G23 恒绿。

**Storage**: **本地 JSONL 文件**（`directory` 注入；每个 `run_id` 一个
`trace-<run_id>.jsonl`）。不实现查询 / SQLite / 远端存储。

**Testing**: pytest —— `tests/observability/`（单元 / 集成 / 格式 / 失败 / 不重试 /
默认关闭 / 并发 / 权限 / `run_id` 安全 / flush 持久化 / span-only 适配器）· `tests/contracts/`（冻结面 / 门禁 /
L5 依赖方向 / 署名头）· `tests/facade/`（`observability.__all__` 精确集合）·
`tests/differential/test_b20f1_local_trace_parity.py`（D-401…D-408；上游缺席即 skip）·
`tests/runtime/test_acceptance_script.py`（B20F1 一键验收守卫）·
`tests/runtime/test_b20f1_manual_record_guard.py`（SC-012 / SC-013 文档守卫）。

**Target Platform**: Linux / macOS / Windows · CPython 3.11+ · 零出站。

**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A（不设墙钟预算）**。每行一次 `open` / `flush` / `close`；
不逐行 `fsync`；trace 写入不是高频热点。MUST NOT 用耗时做断言（CI 假红）。

**Constraints**（主要来自 spec）：

| 约束 | spec 条目 |
|---|---|
| 只依赖标准库 + L1；零第三方依赖 | FR-001 · SC-006 |
| 零出站 / 零环境变量 / 导入无副作用 | FR-004 / FR-005 / FR-008 · SC-003 / SC-005 / SC-006 |
| 注入形态锁定 `FileTraceStore(directory=...)` + `compile(tracer=...)` | FR-006 |
| 每个 `run_id` 一个 `trace-<run_id>.jsonl`；不同 run 不混写 | FR-009 · SC-007 |
| `kind="span"` 含 `Span` **11/11** 字段；`kind="trace_record"` 含 `to_jsonable()` **13/13** 字段 | FR-003 / FR-016 · SC-002 |
| 每行可 `json.loads`；UTF-8 / LF / 无头部 / 一行一对象 | FR-002 · SC-001 / SC-010 |
| span 行只在 `on_span_end` 写；开始回调不写盘 | FR-019 |
| 行序 = 回调到达顺序；同节点 record 在 span 前；不排序 / 不聚合 | FR-020 |
| 写入失败不阻断；四路可感知；不重试；截断半行 | FR-007 / FR-028 · SC-004 / SC-019 |
| 持久化 = 每行 `flush`；不逐行 `fsync` | FR-024 · SC-015 |
| POSIX 新建文件 `0o600`；v1 无权限配置；Windows 由 ACL 解释 | FR-025 · SC-016 |
| 每行独立 `open → append → flush → close`；无 `close()` / 上下文管理器 | FR-026 · SC-017 |
| 每个 store 实例一把锁；不共享全局锁 / 不建每 run 锁表；`on_error` 锁外 | FR-027 · SC-018 |
| `run_id` 为空 / 不安全 ⇒ 拒绝并诊断；不伪造 | FR-014 · SC-014 |
| 不扩 L1 / 门面 / `runtime.__all__` | FR-012 · SC-011 |
| 查询 API / SQLite / OTLP / UI / 保留期不做 | FR-013 · Out of Scope |

> **无未决澄清**：spec 的 5 条 clarify 轮裁定 + 7 条 spec 阶段锁定已收敛全部
> 未决点；本 plan 只落实现方法。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith / 零出站 / 零环境变量） | 零新增依赖；无 env / 网络；G24 / G26 / G27 | 通过 |
| 原则 II（零 LangChain · 状态语义等价） | 不 import `langchain*` / `langgraph*` / `langsmith`；既有回归保持 | 通过 |
| 原则 III（验收契约优先 · `target.py` 只读） | `target.py` **零改动**；`compile(tracer=...)` 形态不变 | 通过 |
| 原则 IV（可诊断性 · 可视化不阻断） | 写入失败不阻断；四路诊断；半行截断 | 通过 |
| 原则 V（人工验收） | `harness/verification/B20F1/manual-verification.md` + 零出站证据 + **质量门禁 5 偏离**（真实模型轮由 B25F1 承接） | 计划交付（偏离已登记） |
| 原则 VI（规格驱动 · 判据级覆盖） | spec FR-001…FR-028 / SC-001…SC-019 · tasks 追溯（/speckit.tasks）· **SC-012 文档守卫 T053** · **SC-014/015 判定测试 T050/T051** | 通过（补齐后） |
| 原则 VII（职责边界 · C23 / C27） | 只做 C27 写入侧；查询仍归 B20F2 | 通过 |
| 原则 VIII（证据与术语） | spec P-01…P-07 / E-1…E-3 + `路径:行号`；`FileTraceStore` / `kind` 术语统一 | 通过 |
| 原则 IX（许可证 / 商标） | 零新增依赖 ⇒ `THIRD_PARTY_NOTICES` 零变更 | 通过 |
| 原则 X（署名头 / 文档） | `_file_store.py` 带署名头；`harness/demo/README.md` 更新 | 通过 |
| 原则 XI（上游优先） | 上游无本地 JSONL（自研区 ③）；默认关闭 / 失败隔离 / 按 run 分组对齐 | 通过（X-1…X-6） |
| 原则 XII（最优设计 / 零重复载体） | 复用 B18F1 `Span` / B19F1 `TraceRecord.to_jsonable()`；不另立第二套序列化 | 通过 |
| 立项书 **ARCH-1**（单向依赖） | L5 `_file_store.py` → L1 `Span` + 同层 `TraceRecord`（向下 / 同层）；无 L3 → L5 / L5 → L2 | 通过 |
| 立项书 **ARCH-2**（顶层惰性） | `import freegraph` 不加载 L5 | 通过 |
| 立项书 **ARCH-3**（跨层只经协议 + 纯数据） | 只消费 `Span` / `TraceRecord` 纯数据；不 import L2 / L3 / L4 | 通过 |
| **L5 依赖面断言**（B18F1 / B19F1） | 新模块只 import 标准库 + `freegraph.contracts` + 同层相对导入 | 通过（无需拆分） |
| **B19F1 的 `observability.__all__` 精确集合** | 只增 `FileTraceStore`；既有 5 符号逐字保留 | 更新（非放宽） |

### 冻结面 / 回溯修订清单

| 冻结面 | 回溯修订位置 | 处置 | 追认 |
|---|---|---|---|
| `freegraph.observability.__all__` 精确集合断言（B19F1） | `tests/facade/test_api_snapshot.py` 的精确集合；`tests/contracts/test_b19f1_lazy.py` 的成员断言 | **只增不改**：新增 `FileTraceStore`；`SpanProducer` / `TraceRecord` / `current_span` / `invoke_model` / `invoke_tool` 逐字保留；`trace_run_scope` 仍不导出 | `harness/verification/B20F1/manual-verification.md` 追认 |
| `SIGNED_SOURCE_FILES` / L5 门禁扫描清单 | `tests/contracts/test_architecture.py` · `tests/contracts/test_b19f1_gates.py` | 追加 `_file_store.py`（**只增**）；原断言继续覆盖既有模块 | 同上 |
| **不破** | `Span` 11 字段 · `TraceSink` 3 方法 · `TraceRecord` 13 字段 · `RunConfig` 9 字段 · `SuperStepResult` / `PregelTask` · `stream()` 信封 · 门面 8 符号 · L1 22 符号 · `freegraph.runtime.__all__` | 零改动 | — |

**无 ARCH-1 / ARCH-3 例外**：本 feature 不需要 L3 → L5 或 L5 → L2 的新接缝。

### 质量门禁 5 偏离登记（2026-11-21 · 发起者选择 A）

| 项 | 内容 |
|---|---|
| 被偏离门禁 | 质量门禁 5「人工验证记录，含真实模型一轮」 |
| 根因 | B20F1 是 L5 本地 JSONL 写入层，不交付模型 provider；真实模型轮不产生本 feature 的新判据 |
| 判据未放宽 | 本地图 + 本地 sink 的 fake / 本地轮照常；JSONL 字段、四路诊断、零出站、默认关闭、`0o600`、per-instance 锁、逐行短生命周期**一字未改** |
| 承接方 / 机制 | **B25F1（M4 · 双跑验收）** 补真实模型轮（含 `FileTraceStore` 落盘证据；承接条款已写入 `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B20F1）」）；B21F1（OTLP）可选复用；B20F1 只交付 fake / 本地轮证据 |
| 追认 | 发起者 2026-11-21 **选择 A（登记偏离）**；正式追认文字 + 确认人 + 日期落 `harness/verification/B20F1/manual-verification.md`，由发起者本人签署 |

### Post-Design Re-check（Phase 1 后）

| 检查 | 结果 |
|---|---|
| L1 符号面仍 22 / 门面仍 8 / `runtime.__all__` 不变 | ✅（只新增 L5 `FileTraceStore`） |
| `import freegraph` 仍只加载 `freegraph` | ✅（L5 惰性） |
| `Span` / `TraceSink` / `TraceRecord` / `RunConfig` / `SuperStepResult` / `PregelTask` 零改动 | ✅ |
| 未注入 ⇒ 零文件 / 零目录 / 零 env | ✅（无默认 sink；构造不建目录） |
| 依赖闭包为空 / 零 env / 零出站 | ✅（只标准库 + L1 / 同层） |
| 上游差分组 D-401…D-408 有落点 | ✅（见 `contracts/upstream-parity.md`） |
| 失败四路可感知 / 不重试 / 无半行 | ✅（见 `contracts/file-trace-store-contract.md`） |
| 权限 `0o600` / 每行短生命周期 / per-instance 锁 | ✅（见 `data-model.md`） |
| README 形态锁定条目更新 | ✅（FR-017 / T038 / T053；`harness/verification/README.md` 由 T049） |
| 人工验证记录 + 一键验收脚本 | ✅（`harness/verification/B20F1/`） |
| 质量门禁 5 偏离 + 文档守卫 | ✅（T048 / T053；B25F1 承接真实模型轮） |
| SC-012 / SC-013 / SC-014 / SC-015 判定覆盖 | ✅（T053 / T050 / T051；见 tasks 追溯表） |

---

## Project Structure

### Documentation (this feature)

```text
specs/b20f1-local-trace-jsonl/
├── plan.md                              # 本文件
├── research.md                          # Phase 0
├── data-model.md                        # Phase 1
├── quickstart.md                        # Phase 1
├── contracts/
│   ├── file-trace-store-contract.md     # 公开 API / 写盘 / 失败 / 并发 / 权限 / 生命周期
│   ├── jsonl-record-contract.md         # span 行 / record 行 / 字段 / 编码 / 行序
│   └── upstream-parity.md               # P-01…P-07 / D-401…D-408 / X-1…X-6 / 冻结面
├── checklists/
│   └── requirements.md
└── tasks.md                             # Phase 2（/speckit.tasks）
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/
│   └── trace.py                         # L1：Span / TraceQuery（零改动；只消费 Span）
├── runtime/                             # L2：span / record 生产（零改动）
│   ├── _span_hook.py                    # 既有：节点 span 接缝 / payload（零改动）
│   └── superstep.py                     # 既有：逐节点 record 推送（零改动）
└── observability/                       # L5
    ├── __init__.py                      # 新增导出 FileTraceStore（不进 facade）
    ├── _file_store.py                   # 新增：JSONL 文件后端 / sink 实现
    ├── _producer.py                     # 既有（B18F1 / B19F1；零改动）
    ├── _record.py                       # 既有：TraceRecord.to_jsonable（零改动）
    ├── _inject.py                       # 既有（B19F1；零改动）
    └── _invoke.py / _time.py            # 既有（零改动）

tests/
├── observability/
│   ├── test_b20f1_store_unit.py         # 行结构 / 文件命名 / 编码 / 默认关闭构造 / 无事件
│   ├── test_b20f1_graph_integration.py  # compile(tracer=...) / invoke / stream / 多 run / 异常
│   ├── test_b20f1_format.py             # US2：UTF-8 / LF / 转义 / kind 过滤
│   ├── test_b20f1_failure.py            # 四路诊断 / 截断 / BaseException
│   ├── test_b20f1_no_retry.py           # US3：不重试 / 截断回写前偏移
│   ├── test_b20f1_default_off.py        # US4：未注入 / 只构造 / env no-op
│   ├── test_b20f1_concurrency.py        # per-instance 锁 / 并发行完整 / on_error 重入
│   ├── test_b20f1_permissions.py        # 0o600 / 无 close / 句柄释放（POSIX / Windows 分支）
│   ├── test_b20f1_run_id_safety.py      # SC-014：空 / 含点 / 不安全 run_id / ~ 不展开 / 无穿越
│   ├── test_b20f1_flush_durability.py   # SC-015：无 fsync / flush 后崩溃仍可读回
│   └── test_b20f1_span_only.py          # INC-01：span-only 适配器 ⇒ 允许 span-only
├── contracts/
│   ├── test_b20f1_contracts.py          # 导出面 / 冻结字段 / L5 依赖 / 署名头
│   ├── test_b20f1_gates.py              # 零 env / 零出站 / 零第三方
│   ├── test_b19f1_lazy.py               # 更新：FileTraceStore 在 observability.__all__
│   ├── test_b19f1_gates.py              # 更新：_file_store.py 纳入扫描
│   └── test_architecture.py             # 更新：SIGNED_SOURCE_FILES 追加 _file_store.py
├── facade/
│   └── test_api_snapshot.py             # 更新：observability.__all__ 精确集合
├── differential/
│   └── test_b20f1_local_trace_parity.py # D-401…D-408（上游缺席即 skip）
└── runtime/
    ├── test_acceptance_script.py        # 追加 B20F1 一键验收守卫
    └── test_b20f1_manual_record_guard.py # SC-012 / SC-013 文档守卫（T053）

harness/
├── demo/
│   └── README.md                        # 更新「本地 trace 存储目录的参数名」为已锁定
└── verification/
    ├── README.md                        # 更新 B20F1 记录行（T049）
    └── B20F1/
        ├── acceptance.py                # 一键验收 A1–A5
        └── manual-verification.md       # 人工验证记录 + 冻结面追认 + 门禁 5 偏离
```

**Structure Decision**: 单包库（发行名 = 导入名 = `freegraph`）。本 feature 不在仓库根新增
目录；只新增 L5 私有模块、测试、验收脚本与文档更新。

---

## Phase 0: Research（摘要 · 详见 [research.md](./research.md)）

| # | 决策 | 理由 | 备选 |
|---|---|---|---|
| **D-01** | 公开载体 = `FileTraceStore(directory=..., *, on_error=None)`，经 `compile(tracer=...)` 注入 | spec 锁定；复用 B19F1 注入点；`directory` 与 B20F2 `database=` 并列 | 扩 `RunConfig` / 读 env / 第二种注入形态（拒绝） |
| **D-02** | 每个 `run_id` 一个 `trace-<run_id>.jsonl`；惰性建目录；追加 | C22「一次运行一个 `run_id`」；不混写；构造无副作用 | 单文件全局 `trace.jsonl`（拒绝：无法按 run 归档） |
| **D-03** | 双行结构：`kind="span"` + `kind="trace_record"`；span 手工 11 字段映射；record 用 `to_jsonable()`；B19F1 注入路径要求双行；接收端不含 `on_trace_record`（span-only 适配器 / 纯 span sink）允许 span-only；`FileTraceStore` 本身始终写 record | record 不含 Span 字段；手工映射避免 `asdict` 深拷贝；`kind` 仅新增字段；span-only 与 Edge Case 对齐 | 只落 record / 只落 span / 嵌套 `span` 对象（拒绝） |
| **D-04** | span 只在 `on_span_end` 写；开始回调不写盘；record 在 span 前到达 | 开始快照 `end_time=None` 是半成品；B19F1 顺序 `start → record → end` | 开始/结束都写（重复 / 半成品）；结束后写 record（违背 B19F1 顺序） |
| **D-05** | 每行 `flush` 即成功；不逐行 `fsync`；每行独立 `open → append → flush → close`；无 `close()` | 用户 clarify 选择；诊断优先不阻断；无句柄泄漏 | 逐行 fsync / 持久句柄 / 上下文管理器（拒绝：慢或需生命周期） |
| **D-06** | POSIX 新建文件 `os.open(..., 0o600)`；已存在不放宽；v1 无权限配置；Windows 由 ACL | 用户 clarify 选择；trace 按敏感数据；`umask` 只能收紧 | 遵循 umask / 可配置权限（拒绝：可能过宽 / 增加 API） |
| **D-07** | 每 store 实例一把 `threading.Lock`；序列化锁外；诊断锁内；`on_error` 锁外；thread-local 防重入 | 上游是 per-Client / 全局锁 + 后台队列，无每 run 文件锁；避免锁表与死锁 | 模块全局锁 / 每 run 锁表 / 无锁（拒绝） |
| **D-08** | 失败四路：`write_errors` / `last_error`（`Type: message`）/ `on_error` / `logging.WARNING`；不重试；截断回写前偏移 | 宪法原则 IV；静默吞错不可接受；不重试避免阻塞 | 静默 / 只日志 / 重试 / 睡眠退避（拒绝） |
| **D-09** | `json.dumps(..., ensure_ascii=False)`；默认分隔符；`kind` 第一；UTF-8 / LF；无头部；非有限浮点遵循 Python json | 一行一对象；中文可读；不另造第二套 `json_safe` | 紧凑分隔符 / `ascii` 转义 / 头部元数据（拒绝：可读性或破坏 A3） |
| **D-10** | `run_id` 严格安全字符：`^[A-Za-z0-9][A-Za-z0-9_-]*$`（**无点号**）；空 / 不安全 ⇒ 诊断、跳过 | 防目录穿越 / Windows 非法文件名；任意 `.` / `..` 一律拒绝；内部 `uuid4().hex` 天然兼容 | 仅拒绝 `/` `\` `..`（拒绝：与 spec「含 `.` 即拒绝」冲突，且 Windows 仍可能非法） |
| **D-11** | L5 `_file_store.py`；只 import 标准库 + L1 `Span` + 同层 `TraceRecord`；导出到 `observability.__all__`，不进 facade；`import freegraph` 惰性 | ARCH-1 / ARCH-2 / ARCH-3；与 B18F1 / B19F1 同层 | 放 L1 / L2 / 门面（拒绝：破层或破惰性） |
| **D-12** | 测试 / 一键验收 / 差分 / README / 人工验证全部落点 | 判据级覆盖（原则 VI）；证据门禁 | 只写单元测试（拒绝：不满足门禁） |
| **D-13** | 质量门禁 5 登记偏离：B20F1 只跑 fake / 本地轮，真实模型轮由 B25F1 承接 | 纯写入层不交付模型 provider；判据零放宽；发起者 2026-11-21 选择 A | 补真实模型轮 / 声明完全不适用（拒绝） |
| **D-14** | SC-012 / SC-013 由 `test_b20f1_manual_record_guard.py`（T053）自动守卫 | 宪法 v1.13.0：人工门禁类 SC 不能只靠写记录 / 审计 | 只人工审计（不满足） |

**无未决澄清。**

---

## Phase 1: Design（摘要）

- **[data-model.md](./data-model.md)**：`FileTraceStore` 形态 / 内部字段、两类 JSONL 行、
  run 文件命名、写盘状态机、失败与截断、并发 / 锁、权限、诊断、生命周期、不变量。
- **[contracts/file-trace-store-contract.md](./contracts/file-trace-store-contract.md)**：
  构造 / 公开只读属性 / sink 回调 / 文件粒度 / 失败语义 / 并发 / 权限 / 生命周期 /
  默认关闭 / 明确不做。
- **[contracts/jsonl-record-contract.md](./contracts/jsonl-record-contract.md)**：
  `kind="span"` 11 字段、`kind="trace_record"` 13 字段、`error` 视图、行序、编码、
  不变量与示例。
- **[contracts/upstream-parity.md](./contracts/upstream-parity.md)**：P-01…P-07、
  E-1…E-3、D-401…D-408、X-1…X-6、冻结面 / 回溯修订。
- **[quickstart.md](./quickstart.md)**：端到端验证（最小落盘、字段、默认关闭、
  失败感知、并发、权限、命令、人工记录）。

---

## Risks & Registrations

| # | 风险 / 事项 | 处置 |
|---|---|---|
| **R-1** | `observability.__all__` 精确集合断言会红 | **只增不改**：新增 `FileTraceStore`；更新 `test_api_snapshot.py` / `test_b19f1_lazy.py`；既有 5 符号逐字保留；追认进 manual-verification |
| **R-2** | 部分写入留下半行 | 写前记录 `st_size`；失败 `os.truncate(path, before)`；截断失败只记诊断；测试「预置一行 + 第二行中途失败」 |
| **R-3** | `on_error` 重入 / 死锁 / 递归 | 锁外调用；`threading.local` 防重入；重入失败不再回调；测试 `on_error` 内写一行 |
| **R-4** | 并发写入交错 | 每实例一把锁；每行先完整序列化；锁内 `open/append/flush/close`；ThreadPoolExecutor 测试逐行 `json.loads` |
| **R-5** | Windows 权限 / 文件锁差异 | POSIX 才断言 `0o600`；Windows 只断言「不因权限失败而阻断」；回调返回后 rename/delete 断言无句柄 |
| **R-6** | 逐行 open/close 性能 | 接受；trace 非高频热点；**MUST NOT** 用墙钟做断言；不引入 fsync / 后台线程 |
| **R-7** | 非 JSON 可序列化 `attributes` / 外部构造对象 | `json.dumps` 失败按写入失败处理；不传播；不写半行；测试 `object()` 值 |
| **R-8** | `run_id` 路径穿越 / Windows 非法字符 | 严格安全字符 allowlist；空 / 不安全 ⇒ 诊断 + 跳过；不伪造 id |
| **R-9** | 改动 B18F1 / B19F1 既有断言 | **MUST NOT** 削弱；只更新 `__all__` 精确集合、L5 扫描清单、signature 清单（只增） |
| **R-10** | README 更新遗漏 | FR-017 / SC-013；**T053** 文档守卫断言 `harness/demo/README.md` 行已锁定；`harness/verification/README.md` 由 **T049** 更新 |
| **R-11** | 真实模型轮 | **已登记质量门禁 5 偏离（2026-11-21 · 发起者选择 A）**：B20F1 只跑本地图 + 本地 sink；真实模型轮由 **B25F1（M4）** 承接，B21F1 可选复用；正式追认文字落 `manual-verification.md`，由发起者本人签署。**MUST NOT** 伪装成已通过 |

---

## Green Baseline & Red List（宪法 v1.11.0 的基线义务）

### 基线（**2026-11-21 · 实施前实跑**）

```text
.venv/bin/python -m pytest -q --tb=no
1917 passed, 6 skipped in 112.86s (0:01:52)
```

**跳过项**（既有环境 / 开关 skip，非本 feature 相关）：
C8 元测试占位 · `IPython` 缺失的 PNG 用例 · `mypy` 未安装 · 上游 PNG 未开启 ·
API 快照未开启更新 · Windows 时钟精度档。

### 变红清单（**预登记** · 实测后 MUST 逐条核对）

| # | 可能变红的既有断言 | 变红原因 | 处置 |
|---|---|---|---|
| **B-1** | `tests/facade/test_api_snapshot.py::test_observability_module_exports_only_its_own_symbols` | `observability.__all__` 新增 `FileTraceStore` | **更新（非放宽）**：集合加入 `FileTraceStore`；既有 5 符号逐字保留 |
| **B-2** | `tests/contracts/test_b19f1_lazy.py` | 需断言 `FileTraceStore` 在 `observability.__all__` | **只增**断言；`trace_run_scope` 仍不在 |
| **B-3** | `tests/contracts/test_b19f1_gates.py` 的 `paths` / `test_no_network_client_is_used_by_new_modules` | 新模块未纳入扫描 | 追加 `_file_store.py`（只增） |
| **B-4** | `tests/contracts/test_architecture.py::TestSignatureHeader` | 新源文件未登记署名头清单 | 追加 `src/freegraph/observability/_file_store.py`（只增） |
| **B-5** | `test_l5_observability_imports_only_stdlib_and_l1` | 新模块若 import L2 / 第三方 | 实现只 import 标准库 + `freegraph.contracts` + 同层相对导入 ⇒ **保持绿** |
| **B-6** | `test_importing_freegraph_is_lazy_for_b18f1_modules` | 若在顶层 `freegraph/__init__` 导入 L5 | 不改顶层；`import freegraph` 仍只加载 `freegraph` |
| **B-7** | `tests/contracts/test_b19f1_contracts.py` 的冻结面计数 | 若改 `Span` / `RunConfig` / `PregelTask` / 门面 | **零改动**；只新增 L5 符号 |
| **B-8** | `tests/facade` 的 `public-api-snapshot.txt` | `FileTraceStore` 不进 `freegraph.graph` | **零改动**；不更新门面快照 |
| **B-9** | 全量测试计数 | 新增测试 | 只增不减；基线 1917 passed 不下降 |
| **B-10** | `harness/demo/README.md` 的待锁定表 | 新形态锁定 | 行改为「已锁定（B20F1）」+ spec 链接；不新增 `diagnostics.py`（另两项仍待定） |
| **B-11** | SC-012 / SC-013 文档守卫（T053） | 守卫断言人工记录 / README；若在记录写就前加入会永久红 | **T053 安排在 T048 / T049 之后**；MUST NOT 在记录前启用；不得为转绿而弱化断言 |

> 实施前 MUST 重跑基线；若变红，先判「是否由本 feature 落地形态导致」→ 再判「是否属冻结断言」；
> **MUST NOT** 以「实现期再说」放过。**B-9 是硬约束**：不得靠修改既有测试来「修复」。

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **无** | 本 feature 无 ARCH-1 / ARCH-3 例外；L5 只 import L1 + 同层 + 标准库 | 若把 `FileTraceStore` 放 L2 / 门面会破分层与惰性；若引入第三方 / SQLite 会破零依赖 |

> 唯一「冻结面更新」是 L5 `observability.__all__` 精确集合**只增** `FileTraceStore`；
> 属**更新（非放宽）**，已登记在 `contracts/upstream-parity.md` §5 与 spec §5。

---

## Implementation Sequencing（供 /speckit.tasks 展开）

1. **Setup / Foundational**：`_file_store.py` 骨架 / 署名头 / `FileTraceStore` 导出；
   更新 `observability.__all__`、L5 扫描清单、signature 清单。
2. **US1（落盘）**：`on_span_end` / `on_trace_record`、文件命名、惰性目录、
   span 11 字段 / record 13 字段、`kind`、UTF-8 / LF、追加。
3. **US2（可读）**：逐行 `json.loads`、`kind` 过滤、非 ASCII / 换行转义、
   无头部 / 半行、行序 / record 在 span 前。
4. **US3（失败不阻断 + 可感知）**：四路诊断、`last_error` 格式、`on_error` 锁外、
   不重试、截断回写前偏移、`BaseException` 不吞。
5. **US4（默认关闭）**：未注入 / 只构造 / env 变量；零文件 / 零目录 / 惰性 import。
6. **并发 / 权限 / 生命周期**：per-instance 锁、线程池测试、`0o600`、无 `close`、
   rename/delete、句柄基线。
7. **契约 / 差分 / 文档**：`test_b20f1_contracts.py` / `test_b20f1_gates.py` /
   `test_b20f1_local_trace_parity.py` / README / acceptance / manual-verification。
8. **Polish**：全量回归、G21/G24/G26/G27、人工验收记录、冻结面追认。
9. **Coverage Closure**：T049 更新 `harness/verification/README.md`；T050 `run_id` 安全；
   T051 flush 持久化；T052 span-only；T053 文档守卫（SC-012 / SC-013 + 门禁 5 偏离）。
   T053 MUST 在 T048 / T049 之后；其余测试可与 T049 并行。

---

## Notes

- `harness/demo/target.py` **零改动**（只读基准）。
- 不新增运行时依赖、不新增 L1 / 门面 / `runtime.__all__` 符号。
- `Span` / `TraceRecord` / `TraceSink` / `RunConfig` / `SuperStepResult` / `PregelTask`
  **零改动**；`FileTraceStore` 只消费。
- 文件格式（`kind` / 文件名 / 行序 / 编码）是 C27 ⑤ 的**内部实现细节**，但本 plan 写死
  以保证可重复验收；B20F2 查询实现 MUST 按此读取，Studio MUST NOT 直连。
- 人工验证记录：`harness/verification/B20F1/manual-verification.md`
  （JSONL 样例、`jq` / `json.loads` 读回、失败感知、零出站、`__all__` 快照追认、
  **质量门禁 5 偏离声明 + 发起者追认**）；由
  `tests/runtime/test_b20f1_manual_record_guard.py`（T053）自动守卫。
- 一键验收：`harness/verification/B20F1/acceptance.py`（A1–A5）。
- `harness/verification/README.md` 由 T049 更新 B20F1 行；`harness/demo/README.md` 的
  `diagnostics.py` **仍不新增**：`MemorySaver` / `update_state` 两项形态尚未锁定；本次只把
  「本地 trace 存储目录的参数名」标为已锁定。
- **质量门禁 5**：本 feature 只跑 fake / 本地轮；真实模型轮由 **B25F1（M4）** 承接
  （承接条款已写入 `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B20F1）」；
  B21F1 可选复用）；正式追认文字由发起者本人签署，**MUST NOT** 由实现者代签。
