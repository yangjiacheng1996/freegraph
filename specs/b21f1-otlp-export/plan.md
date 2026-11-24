# Implementation Plan: B21F1 · OTLP 导出插件（可选 extra）+ 后端对接文档

**Branch**: `b21f1-otlp-export`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_plan` 钩子；既有 feature 同样在 `main` 上开发）

**Date**: 2026-11-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b21f1-otlp-export/spec.md`

**Feature ID**: `B21F1`（M4 生态 · **第 30 个** · 前置：**B20F2**；承接 **B18F1 / B19F1 / B20F2 / B14F1 / B2F1 / B3F1**）

> **范围提醒**：本 feature 是 **L5 可观测层的导出侧**。它只消费 B18F1 生产、B19F1
> 推送的 `Span`；**不消费** B20F2 的 `query()`，**不导出** `TraceRecord`，**不修改**
> `Span` / `TraceSink` / `TraceRecord` / `TraceQuery` / `RunConfig` 的任何字段，
> **不改变**图执行结果。**不实现**本地 Agent Server / SSE（v2 / D8）、前端 UI
> （v2 / B26）、评测 / 数据集（永不做）、自托管 trace 后端（路线 A，MUST NOT）、
> async 导出（v2）、自研 protobuf / OTLP 编码（明确不采用）。

---

## Summary

交付 **可观测生态出口**：新增可选 extra **`[otlp]`** 与 L5 公开符号
**`freegraph.observability.OtlpExporter`**，把 B18F1 的 `Span` 逐字段映射为
**官方 OTel SDK 数据对象**，再由**官方 OTLP 编码器 + 官方 gRPC proto stubs** 导出到用户
显式提供的 OTLP gRPC 端点（或用户显式传入的官方 `SpanExporter` 对象）。默认关闭、
无默认端点、不读任何环境变量、导出失败不阻断图执行。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **`[otlp]` extra** | 可选依赖单元 | 仅 gRPC 协议实现：`opentelemetry-exporter-otlp-proto-grpc` + OTel SDK；基础安装仍零依赖 |
| **`OtlpExporter`** | L5 公开符号，实现 `TraceSink` 三方法 | `compile(tracer=OtlpExporter(...))` 注入；`on_span_start` no-op；`on_span_end` 同步导出完整 span；`current_span()` 恒 `None` |
| **端点模式** | `endpoint="host:port"` | `insecure=False` 默认 TLS；`insecure=True` 本地明文；**MUST NOT** 带 `http://` / `https://` scheme |
| **导出器模式** | `exporter=<官方 SpanExporter>` | 供 HTTP-only 后端（OpenLIT / Langfuse）使用；TLS / 认证由用户对象负责 |
| **Span → OTLP 映射** | 11 字段逐字段映射 | `run_id` → `trace_id`；`id` / `parent` → `span_id` / `parent_span_id`；`attributes` 逐键直映射；`thread_id` → `gen_ai.conversation.id`；`context` / `checkpoint_id` v1 不导出 |
| **失败隔离** | 四路诊断 | `export_errors` / `last_error` / 可选 `on_error` / `WARNING`；`BaseException` 不吞；不重试 |
| **同步 / 并发** | v1 同步 | 每导出一次短生命周期 gRPC channel；每实例一把进程内锁；无后台线程 / async / batching |
| **三后端示例** | OpenLIT / Langfuse / Phoenix | 并列、无默认推荐；Phoenix 用 gRPC；OpenLIT / Langfuse 用用户自装 HTTP exporter + `exporter=`；HTTP exporter 延迟导入（`--help` 不依赖） |
| **文档** | README + 示例 README + 风险说明 | 旧路径 `openlit.io/docs` 404、现行 `docs.openlit.io`、as-of 日期、能力分工 / 重叠说明 |
| **测试 / 验收** | 单元 + 契约 + 差分 + 人工 | 桩接收端 + 最小 gRPC 接收端；至少一个真实后端冒烟；质量门禁 5 偏离由 B25F1 承接 |

**技术方案（关键落点）**：

| 环节 | 落点 |
|---|---|
| 公开 API | **新增** `src/freegraph/observability/_otlp_exporter.py`：`OtlpExporter` 构造校验 / 注入 / 锁 / 诊断 / 失败隔离 / 惰性 import |
| 纯映射 | **新增** `src/freegraph/observability/_otlp_mapping.py`：`Span` → `ReadableSpan` / `ExportTraceServiceRequest`；身份哈希 / 时间 / 属性 / Resource / Scope / SpanKind / Status |
| 传输 | **新增** `src/freegraph/observability/_otlp_transport.py`：官方 `encode_spans` + 官方 `TraceServiceStub`；短生命周期 channel；TLS / insecure / headers / timeout |
| 导出面 | **修改** `src/freegraph/observability/__init__.py`：`__all__` 只增 `OtlpExporter` |
| 依赖 / 门禁 | **修改** `pyproject.toml`（仅 `[otlp]`）· `specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml` · `tests/contracts/test_architecture.py`（白名单 / 署名 / L5 扫描例外）· `harness/scripts/gates/_gatekit.py`（G23 归一 / G26 例外 / grpc 扫描）· `.github/workflows/ci.yml` |
| 测试 | `tests/observability/test_b21f1_*.py` · `tests/contracts/test_b21f1_*.py` · `tests/differential/test_b21f1_otlp_parity.py` · `tests/runtime/test_b21f1_manual_record_guard.py` |
| 示例 | **新增** `harness/examples/B21F1/{phoenix,openlit,langfuse}.py` + `README.md` |
| 人工验收 | **新增** `harness/verification/B21F1/acceptance.py` + `manual-verification.md` |
| 文档 | `README.md` · `THIRD_PARTY_NOTICES` · `harness/demo/README.md` · `harness/verification/README.md` |

**关键实现结论（研究阶段实测，详见 [research.md](./research.md)）**：

1. **不用 `OTLPSpanExporter` 门面**：它在构造期读取 `OTEL_EXPORTER_OTLP_*`
   （`trace_exporter/__init__.py:94-122`；`exporter.py:286-366`），且内部最多重试
   `_MAX_RETRYS = 6`（`exporter.py:121,421-463`），与「零 env / 不重试」冲突。
2. **改用官方编码器 + 官方 gRPC stubs**：`encode_spans()`（`trace_encoder/__init__.py:41`）
   生成 `ExportTraceServiceRequest`，`TraceServiceStub.Export()` 发送；**不自研编码**。
3. **不用 `Resource.create()`**：它会读 `OTEL_RESOURCE_ATTRIBUTES` / `OTEL_SERVICE_NAME`
   （`resources/__init__.py:199,333,350`）；改用 `Resource({...})` 直接构造，固定
   `service.name="freegraph"`。
4. **直接构造 `ReadableSpan`**：SDK 1.45.2 的 `ReadableSpan`（`sdk/trace/__init__.py:396,404`）
   接受 name / context / parent / resource / attributes / kind / status / start/end ns；
   `encode_spans` 可直接消费。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`requires-python = ">=3.11"`；本机 `.venv` 为 3.11.16）。
本 feature **MUST NOT** 使用 3.12+ 专属语法。

**Primary Dependencies**:
- 基础安装：**零第三方运行时依赖**（`dependencies = []`）。
- `[otlp]`（新增，默认不安装）：`opentelemetry-api` · `opentelemetry-sdk` ·
  `opentelemetry-exporter-otlp-proto-grpc`。
- 实测闭包（as-of **2026-11-24**；wheel 元数据取证）：`opentelemetry-api 1.45.2` ·
  `opentelemetry-sdk 1.45.2` · `opentelemetry-semantic-conventions 0.66b2` ·
  `opentelemetry-exporter-otlp-proto-grpc 1.45.2` ·
  `opentelemetry-exporter-otlp-proto-common 1.45.2` ·
  `opentelemetry-exporter-otlp-common 0.66b2` · `opentelemetry-proto 1.45.2` ·
  `googleapis-common-protos 1.76.0` · `grpcio 1.85.3` · `protobuf 7.36.2` ·
  `typing-extensions`（PSF-2.0，既有白名单）。
- **MUST NOT** 声明：`opentelemetry-exporter-otlp` 元包、
  `opentelemetry-exporter-otlp-proto-http`、`requests`、`certifi`。
- 开发期：`pytest`（既有 `dev`）；差分：`langgraph==1.2.11`（既有 `differential`）。
- **CI**：全量作业 MUST 安装 `.[otlp]`（或等价的三个声明包），使 G21 / G23 取证可达。

**Storage**: **N/A**（不落盘；只向用户显式端点出站）。不消费 B20F2 的本地存储。

**Testing**: pytest ——
`tests/observability/test_b21f1_mapping.py`（身份 / 时间 / 属性 / status / kind / Resource）·
`test_b21f1_export.py`（桩导出器 / 基本注入 / 字段面）·
`test_b21f1_failure.py`（失败隔离 / 诊断 / 并发 / 不重试）·
`test_b21f1_transport.py`（最小 gRPC 接收端 · `linux_only` / `full_install`）·
`test_b21f1_default_off.py`（零 OTel import / 零出站）·
`test_b21f1_examples.py`（三示例存在 / `--help` / 分工表 / as-of）·
`tests/contracts/test_b21f1_contracts.py` / `test_b21f1_gates.py`（公开面 / 惰性 / 依赖 / 许可证 / 门禁）·
`tests/differential/test_b21f1_otlp_parity.py`（D-601…D-608）·
`tests/runtime/test_b21f1_manual_record_guard.py`（SC-010 文档守卫）·
`tests/runtime/test_acceptance_script.py`（追加 B21F1 一键验收守卫）。

**Target Platform**: Linux / macOS / Windows · CPython 3.11+ · 基础路径零出站。
**真实 gRPC 接收端用例**：Linux 全量作业跑；非 Linux 作业用桩导出器覆盖映射 / 隔离。

**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A（不设墙钟预算）**。v1 以正确性 / 失败隔离 / 许可证合规优先；
同步导出、每 span 短生命周期 channel 是**有意的 v1 取舍**（无 `close()` / 后台线程）。
MUST NOT 用耗时做断言。

**Constraints**（主要来自 spec）：

| 约束 | spec 条目 |
|---|---|
| `[otlp]` 只含 gRPC 协议实现 + OTel SDK；基础安装零依赖 | FR-001 / FR-002 · SC-005 |
| 许可证白名单；`protobuf` 散文标识归一为 `BSD-3-Clause`；无 MPL | FR-003 · SC-005 / SC-009 |
| 默认关闭；无默认端点；不读任何 env | FR-006 / FR-007 / FR-008 · SC-002 / SC-006 |
| 缺 extra ⇒ 构造时 `ImportError` | FR-009 · SC-011 |
| `endpoint` = `host:port`；`insecure` 默认 False（TLS）；`headers` / `timeout` 仅端点模式 | FR-007 · SC-011 |
| 只导出有 `end_time` 的完整 span；同步；无 async / batching | FR-012 / FR-013 · SC-012 |
| 不提供 `close()` / 上下文管理器 / 公开 OTel 对象 | FR-014 |
| 11 字段映射；`attributes` 逐键直映射；无私有前缀 | FR-016…FR-022 · SC-007 |
| `TraceRecord` 不导出；不消费 B20F2 查询 API | FR-023 / FR-038 · SC-013 |
| 复用官方编码；无自研 protobuf / wire format | FR-024 · SC-008 |
| 失败隔离 + 四路诊断；`BaseException` 不吞；不重试 | FR-025…FR-029 · SC-003 |
| 三示例并列 / 无默认推荐；至少一个真实后端冒烟 | FR-030…FR-034 · SC-004 / SC-015 |
| L5 惰性 import；无 langchain / langsmith / langgraph | FR-035 / FR-036 · SC-005 / SC-008 |
| 不内嵌 Phoenix / Langfuse / OpenLIT | FR-037 · SC-009 |

> **无未决澄清**：spec 的 clarify 轮 + 形态锁定裁定已收敛全部功能决策；本 plan
> 只落实现方法、门禁变更与证据。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith / 零出站 / 零环境变量） | 基础路径零出站；无 env；`[otlp]` 只在显式构造时出站；G24 / G26 / G27 | 通过（具名 OTLP 例外） |
| 原则 II（零 LangChain · 状态语义等价） | 不 import `langchain*` / `langgraph*` / `langsmith`；既有回归保持 | 通过 |
| 原则 III（验收契约优先 · `target.py` 只读） | `target.py` **零改动**；`compile(tracer=...)` 形态不变 | 通过 |
| 原则 IV（可诊断性 · 可视化不阻断） | 导出失败隔离；只消费 `Span`；标准 OTLP 输出 | 通过 |
| 原则 V（人工验收） | `harness/verification/B21F1/manual-verification.md` + 零出站证据 + **质量门禁 5 偏离**（真实模型轮由 B25F1 承接） | 计划交付（偏离已登记） |
| 原则 VI（规格驱动 · 判据级覆盖） | spec FR-001…FR-041 / SC-001…SC-015 · tasks 追溯（/speckit.tasks）· SC-010 文档守卫 | 通过（补齐后） |
| 原则 VII（职责边界 · C23 / C24） | 不新增契约条目；不新增 L1 Protocol；不扩门面 | 通过 |
| 原则 VIII（证据与术语） | spec P-01…P-07 / D-601…D-608 + 本 plan 的 OTel wheel 实测；`Span` / `TraceSink` / `gen_ai.*` 术语统一 | 通过 |
| 原则 IX（许可证 / 商标） | `[otlp]` 闭包全白名单；`protobuf` 归一；无 MPL / ELv2；无 Phoenix 内嵌 | **条件通过**（G23 归一化通道须追认） |
| 原则 X（署名头 / 文档） | 新增模块带署名头；`THIRD_PARTY_NOTICES` / README 更新 | 通过 |
| 原则 XI（上游优先） | 上游无内建 OTLP（自研区 ③）；默认关闭 / 失败隔离 / 成对生命周期对齐；D-601…D-608；P ↔ X 三态一致 | 通过（X-1…X-5） |
| 原则 XII（最优设计 / 零重复载体） | 复用 `Span` + 官方 SDK 数据对象 + 官方编码器；不另立私有 span / 编码 | 通过 |
| 立项书 **ARCH-1**（单向依赖） | L5 → L1 `Span` + 标准库 + **惰性** OTel；无 L5 → L2/L3/L4 | 通过（具名 OTLP 例外） |
| 立项书 **ARCH-2**（顶层惰性） | `import freegraph` 不加载 L5 / OTel；`OtlpExporter` 不进 `freegraph.graph` | 通过 |
| 立项书 **ARCH-3**（跨层只经协议 + 纯数据） | 只消费 `Span`；不读 L2 私有状态 / B20F2 查询 API | 通过 |
| **L5 依赖面断言**（B18F1 / B19F1 / B20F1 / B20F2） | 新 OTLP 模块只 import 标准库 + L1 + OTel/grpc（**具名例外**）；其它 L5 模块不变 | **更新（非放宽）** |
| **B19F1 的 `opentelemetry` import 禁令** | `_otlp_*.py` 具名例外；新增运行时惰性断言（`import observability` 不加载 OTel / grpc） | **更新（非放宽）** |
| **B19F1 的第三方 import / egress 扫描** | 只允许 `_otlp_mapping.py` / `_otlp_transport.py` / `_otlp_exporter.py`；其它模块仍禁止 | **更新（非放宽）** |
| **`observability.__all__` 精确集合** | 只增 `OtlpExporter`；既有 7 符号逐字保留 | 更新（非放宽） |
| **B3F1 的 G3 extras 白名单** | 12 → 19 名（新增 7 个确切包名）；基础安装闭包仍为空 | 更新（非放宽） |
| **B3F1 的 G23 许可证门禁** | 新增**仅 `protobuf`** 的具名归一（`3-Clause BSD License` → `BSD-3-Clause`）；不放宽白名单 | **条件通过**（须追认） |
| **B3F1 的 G26 网络静态扫描** | 把 `grpc` 加入网络客户端清单；仅 `_otlp_transport.py` 进例外名单 | **更新（更严 + 具名例外）** |
| **宪法 v1.7.0（v1.0 无 optional-dependencies；已由 v1.17.0 修订）** | 窄例外：仅 `[otlp]` 进入 v1.0 发行元数据；其它 extra 仍归 v2.0 | **已按宪法 v1.17.0（2026-11-24 · MINOR）正式修订**（唯一具名例外；条件见宪法正文） |

### 冻结面 / 回溯修订清单

| 冻结面 | 回溯修订位置 | 处置 | 追认 |
|---|---|---|---|
| 宪法 v1.7.0「v1.0 无 `[project.optional-dependencies]`」（已由 v1.17.0 修订） | `.specify/memory/constitution.md`（已改为 v1.17.0）+ `pyproject.toml` | **唯一具名例外**：仅 `[otlp]`；其它 extra 仍归 v2.0；基础安装闭包不变；条件见宪法 v1.17.0 正文 | 宪法 v1.17.0 正式修订 + 发起者追认；正式文字落 manual-verification |
| B3F1 G3 extras 白名单（12 名） | `tests/contracts/test_architecture.py::CONSTITUTION_DEPENDENCY_WHITELIST` | **只增** 7 名：`opentelemetry-exporter-otlp-proto-grpc` / `opentelemetry-exporter-otlp-proto-common` / `opentelemetry-exporter-otlp-common` / `opentelemetry-proto` / `googleapis-common-protos` / `grpcio` / `protobuf` | 发起者书面追认 + manual-verification |
| B3F1 G23「散文式标识 MUST 失败 / 禁止归一化」 | `harness/scripts/gates/_gatekit.py` · `gate_G23_licenses.py` · `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` | **只加一条具名归一**：`protobuf` 的 `License: 3-Clause BSD License` → `BSD-3-Clause`（依据其 LICENSE 文件）；**不是**通用对照表，不放宽白名单 | 发起者书面追认 + manual-verification |
| B3F1 G26 例外名单（当前为空） | `harness/scripts/gates/_gatekit.py::G26_EXCEPTED_MODULES` | **只增** `_otlp_transport.py`；扫描域不变；`grpc` 加入网络客户端清单（**更严**） | manual-verification 追认 |
| B19F1「L5 模块禁止 import `opentelemetry`」 | `tests/contracts/test_b19f1_gates.py` · `tests/contracts/test_architecture.py::test_l5_observability_imports_only_stdlib_and_l1` · `test_b18f1_modules_have_no_forbidden_third_party_imports` | **拆分而不删**：保留其它 L5 模块的禁令；只允许 `_otlp_mapping.py` / `_otlp_transport.py` / `_otlp_exporter.py` 惰性 import OTel / grpc；新增运行时断言「`import freegraph.observability` 后 `opentelemetry` / `grpc` 不在 `sys.modules`」 | manual-verification 追认 |
| `observability.__all__` 精确集合 | `tests/facade/test_api_snapshot.py` · `tests/contracts/test_b19f1_lazy.py` | **只增** `OtlpExporter`；既有 7 符号逐字保留 | manual-verification |
| `SIGNED_SOURCE_FILES` / L5 扫描清单 | `tests/contracts/test_architecture.py` · `tests/contracts/test_b19f1_gates.py` | 追加 3 个新源文件（**只增**） | manual-verification |
| B3F1 CI 安装范围 | `.github/workflows/ci.yml` · `specs/b3f1-scaffold-ci-gates/contracts/ci-matrix.md` | 全量作业安装 `.[otlp]`；G21 / G23 的取证对象改为含 `otlp` 的 `extras-v2.toml` | manual-verification |
| **不破** | `Span` 11 字段 · `TraceSink` 3 方法 · `TraceRecord` 13 字段 · `TraceQuery` 5 字段 · `RunConfig` 9 字段 · `stream()` 信封 · 门面 8 符号 · L1 22 符号 · `freegraph.runtime.__all__` · B20F2 查询语义 / 行结构 / schema · `compile()` 既有签名 | 零改动 | — |

### 质量门禁 5 偏离登记（2026-11-24 · 沿用 B20F1 / B20F2 先例 · 已追认）

| 项 | 内容 |
|---|---|
| 被偏离门禁 | 质量门禁 5「人工验证记录，含真实模型一轮」 |
| 根因 | B21F1 是 L5 OTLP 导出层；验收对象是映射正确性 / 默认关闭 / 失败隔离 / 许可证合规 / 后端示例可用性。真实模型轮不产生本 feature 的新判据，反而引入 provider 依赖。**沿用 B20F1 / B20F2 的同一偏离口径**；判据未放宽。 |
| 判据未放宽 | 本地图 + fake 模型 + 桩接收端 / 最小 gRPC 接收端的轮次照常执行；导出、默认关闭、零出站、失败隔离、三示例、许可证、治理追认等判据**一字未改**；人工记录五段式照常。 |
| 承接方 / 机制 | **B25F1（M4 · 双跑验收）** 补真实模型轮（含 OTLP 导出证据）；承接条款 MUST 写入 `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B21F1）」，并由 B21F1 tasks 的守卫断言核验。B21F1 只交付 fake / 桩 / 最小接收端轮证据；真实后端冒烟按 SC-015 执行。 |
| 追认 | **已由发起者于 2026-11-24 书面追认**（确认人：发起者本人；见 `harness/verification/B21F1/manual-verification.md` §4.2）。真实模型轮由 **B25F1** 承接。 |

### Post-Design Re-check（Phase 1 后）

| 检查 | 结果 |
|---|---|
| 基础安装闭包仍为空集；`[otlp]` 闭包 ⊆ 白名单 | 计划验证（G3 / G23；见 [contracts/dependency-and-gate-contract.md](./contracts/dependency-and-gate-contract.md)） |
| `import freegraph` 不加载 L5 / OTel；`import freegraph.observability` 不加载 OTel / grpc | 计划验证（`test_b19f1_lazy.py` + `test_b21f1_default_off.py`） |
| `Span` / `TraceSink` / `TraceRecord` / `TraceQuery` / `RunConfig` 零改动 | 计划验证（契约测试） |
| `compile(tracer=...)` 仍无参可调用；不新增关键字 | 计划验证（门面快照） |
| 11 字段映射 / 身份哈希 / 时间纳秒 / status / kind | 计划验证（`test_b21f1_mapping.py`） |
| 默认关闭 / 无默认端点 / 零 env / 零出站 | 计划验证（`test_b21f1_default_off.py`） |
| 失败隔离 / 四路诊断 / `BaseException` 不吞 / 不重试 | 计划验证（`test_b21f1_failure.py`） |
| 三示例并列 / 无默认推荐 / 分工表 / as-of / 至少一个真实后端 | 计划验证（`test_b21f1_examples.py` + manual-verification） |
| 不自研编码：官方 `encode_spans` + 官方 stubs | 计划验证（AST / 静态扫描） |
| D-601…D-608 有落点；X-1…X-5 与 P-01…P-07 三态一致 | 计划验证（`contracts/upstream-parity.md`） |
| 人工验证记录 + 一键验收 + 文档守卫 | 计划验证（`harness/verification/B21F1/`） |
| G23 归一化 / G26 例外 / B19F1 import 例外 / v1.17.0 具名例外 | 计划验证（见“冻结面 / 回溯修订清单”；**合入前 MUST 完成书面追认**） |

---

## Project Structure

### Documentation (this feature)

```text
specs/b21f1-otlp-export/
├── plan.md                                      # 本文件
├── research.md                                  # Phase 0
├── data-model.md                                # Phase 1
├── quickstart.md                                # Phase 1
├── contracts/
│   ├── otlp-exporter-contract.md                # 公开 API / 注入 / 校验 / 诊断 / 生命周期
│   ├── span-to-otlp-mapping-contract.md         # 11 字段映射 / 身份 / 时间 / 属性 / status / Resource / kind
│   ├── dependency-and-gate-contract.md          # extra / 闭包 / 许可证 / G3 / G21 / G23 / G26 / CI
│   ├── backend-examples-contract.md             # 三示例 / 端点 / 认证 / 来源 / as-of / 分工表 / 风险
│   └── upstream-parity.md                       # P-01…P-07 / D-601…D-608 / X-1…X-5 / 冻结面
├── checklists/
│   └── requirements.md
└── tasks.md                                     # Phase 2（/speckit.tasks）
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/
│   └── trace.py                                 # L1：Span（零改动；只消费）
└── observability/                               # L5
    ├── __init__.py                              # 修改：__all__ 只增 OtlpExporter
    ├── _otlp_exporter.py                        # 新增：公开 OtlpExporter（校验 / 锁 / 诊断 / 失败隔离）
    ├── _otlp_mapping.py                         # 新增：Span → ReadableSpan / request（纯映射）
    ├── _otlp_transport.py                       # 新增：官方 encode_spans + TraceServiceStub（gRPC）
    ├── _time.py                                 # 既有：复用 parse_iso_ns（零改动）
    ├── _producer.py                             # 既有（B18F1 / B19F1；零改动）
    ├── _record.py                               # 既有（B19F1；零改动）
    ├── _file_store.py / _sqlite_store.py        # 既有（B20F1 / B20F2；零改动）
    └── _query.py / _payloads.py                 # 既有（B20F2；零改动）

tests/
├── observability/
│   ├── test_b21f1_mapping.py                    # 身份 / 时间 / 属性 / status / kind / Resource
│   ├── test_b21f1_export.py                     # 桩导出器 / 基本注入 / 字段面
│   ├── test_b21f1_failure.py                    # 失败隔离 / 诊断 / 并发 / 不重试
│   ├── test_b21f1_transport.py                  # 最小 gRPC 接收端（linux_only / full_install）
│   ├── test_b21f1_default_off.py                # 零 OTel import / 零出站 / 零 env
│   └── test_b21f1_examples.py                   # 三示例存在 / --help / 分工表 / as-of
├── contracts/
│   ├── test_b21f1_contracts.py                  # 公开面 / 签名 / 惰性 / 冻结字段 / 无 schema 泄漏
│   ├── test_b21f1_gates.py                      # 依赖闭包 / 许可证 / G26 / 无自研编码
│   ├── test_b19f1_lazy.py                       # 更新：OtlpExporter 在 __all__；无 OTel / grpc 加载
│   ├── test_b19f1_gates.py                      # 更新：OTLP 模块具名例外（只增）
│   └── test_architecture.py                     # 更新：白名单 / 署名 / L5 扫描例外（只增）
├── differential/
│   └── test_b21f1_otlp_parity.py                # D-601…D-608（上游缺席即 skip）
└── runtime/
    ├── test_acceptance_script.py                # 追加 B21F1 一键验收守卫
    └── test_b21f1_manual_record_guard.py        # SC-010 文档守卫

harness/
├── examples/
│   └── B21F1/
│       ├── phoenix.py                           # gRPC endpoint + insecure=True
│       ├── openlit.py                           # HTTP exporter 对象 + exporter=
│       ├── langfuse.py                          # HTTP exporter 对象 + Basic auth
│       └── README.md                            # 来源 / as-of / 分工表 / 风险 / 前置安装
├── demo/
│   └── README.md                                # 更新：OTLP 导出入口
└── verification/
    ├── README.md                                # 更新 B21F1 记录行
    └── B21F1/
        ├── acceptance.py                        # 一键验收 A1–A5
        └── manual-verification.md               # 人工验证 + 治理追认 + 门禁 5 偏离

（根级）README.md · THIRD_PARTY_NOTICES · pyproject.toml · .github/workflows/ci.yml
specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml · contracts/ci-matrix.md
harness/scripts/gates/_gatekit.py · gate_G23_licenses.py
```

**Structure Decision**: 单包库（发行名 = 导入名 = `freegraph`）。本 feature 不新增仓库根
目录；示例放 `harness/examples/B21F1/`（与 `harness/demo/`、`harness/verification/`
的「开发辅助材料」定位一致，不进发行包）。L5 新增 3 个内部模块：纯映射 / 传输 /
公开导出器；`OTel` 与 `grpc` 只在 `_otlp_mapping.py` / `_otlp_transport.py` /
`_otlp_exporter.py` 中**惰性** import（`__init__.py` 不直接加载）。

---

## Phase 0: Research（摘要 · 详见 [research.md](./research.md)）

| # | 决策 | 理由 | 备选 |
|---|---|---|---|
| **D-01** | `[otlp]` = `opentelemetry-api` + `opentelemetry-sdk` + `opentelemetry-exporter-otlp-proto-grpc` | 唯一同时满足「官方编码复用」+「许可证白名单」的路径；避开 `certifi` / MPL-2.0 | 元包（拒绝：certifi）；HTTP 协议（拒绝：certifi）；自研 JSON（拒绝：违反提示词） |
| **D-02** | `protobuf` 的 `3-Clause BSD License` **仅此一包**归一为 `BSD-3-Clause` | protobuf 的 LICENSE 文件就是 BSD-3-Clause；属证据规范化，不是放宽白名单 | 通用对照表（拒绝：破 G23 规则）；换包（不可行） |
| **D-03** | 传输用官方 `encode_spans` + 官方 `TraceServiceStub`；**不用** `OTLPSpanExporter` 门面 | 门面构造期读 env（`:94-122` / `:286-366`）且内部重试（`_MAX_RETRYS=6` / `:421-463`）；thin transport 可严格零 env / 不重试，仍复用官方编码 | 门面 + 清空 env（拒绝：线程不安全）；自研编码（拒绝） |
| **D-04** | 直接构造 `ReadableSpan` / `SpanContext` / `Resource({...})` / `InstrumentationScope` | 官方编码器消费 `ReadableSpan`；`Resource.create()` 会读 env（`:199,333,350`）⇒ 用 `Resource(...)` | `Resource.create`（拒绝：env）；`TracerProvider`（拒绝：全局状态 / 隐式出站） |
| **D-05** | 身份哈希：`trace_id = sha256("freegraph:run:"+run_id)[:16]`；`span_id = sha256("freegraph:span:"+id)[:8]`；`TraceFlags.SAMPLED` | 同 run 同 trace；跨进程稳定；不依赖随机状态 | 每实例随机映射（拒绝：跨进程不一致）；直接用 id（长度不符） |
| **D-06** | 时间复用 L5 `_time.parse_iso_ns`；`end_time is None` ⇒ no-op；非法 ⇒ 跳过 + WARNING；`end < start` ⇒ 钳到 `start` + WARNING | B18F1 的规范格式是 9 位 UTC；复用同层助手；保留纳秒 | `datetime.fromisoformat`（拒绝：微秒截断风险）；丢弃 `end<start`（拒绝：损失诊断） |
| **D-07** | 属性面：`Span.attributes` 逐键直映射 + 唯一派生 `gen_ai.conversation.id`；无私有前缀；值归一 | B18F1 D-3；`gen_ai.*` 纯净；CI 可断言 | 导出 `freegraph.*`（拒绝：破属性面）；导出 `TraceRecord`（拒绝：不是 Span） |
| **D-08** | 默认关闭 / 无默认端点 / 不读 env；OTel 惰性 import | 宪法原则 I / IV；spec FR-006…FR-008 | 自动注册全局 provider（拒绝）；读 `OTEL_*`（拒绝） |
| **D-09** | 失败四路诊断；`export_errors` 每失败 span +1；`last_error` 保留最近失败；`on_error` 的 `Exception` 也被隔离；`BaseException` 不吞；不重试 | 宪法原则 IV；spec FR-025…FR-029 | 静默吞错（拒绝）；重试（拒绝：spec 锁定）；熔断（拒绝：v1 不做） |
| **D-10** | 同步导出；每实例一把进程内锁；每次导出短生命周期 gRPC channel；不提供 `close()` | spec FR-013 / FR-014；避免生命周期 API / 资源泄漏 / 后台线程 | 持久 channel + `close()`（拒绝：破公开面）；后台线程（拒绝：v2） |
| **D-11** | 端点 `host:port`；`insecure=False` 默认 TLS；`insecure` 与 `exporter=` 互斥；`exporter` 鸭子类型校验 | spec FR-007 / SC-011；默认安全；HTTP 后端用 `exporter=` | URL scheme 推断（拒绝：用户已选 B）；默认明文（拒绝：默认不安全） |
| **D-12** | 三示例并列、无默认推荐；Phoenix gRPC，OpenLIT / Langfuse HTTP + `exporter=`；分工表 + 来源 / as-of + 风险 | spec FR-030…FR-034；宪法原则 X；R12 | 选默认后端（拒绝：affiliation / 文档风险）；只做两示例（拒绝：偏离提示词） |
| **D-13** | 测试：桩导出器（全平台）+ 最小 gRPC 接收端（Linux 全量）+ 子进程惰性 / 零 env / 零出站 + 门禁测试 | 判据级覆盖；CI 稳定；真实 OTLP wire 验证 | 只做 mock（拒绝：不验证 wire）；只做真实后端（拒绝：不稳定） |
| **D-14** | 文档：README / 示例 README / `THIRD_PARTY_NOTICES` / demo / verification 全更新 | 宪法原则 X；证据门禁；可复制运行 | 只写代码注释（拒绝：不满足交付物） |
| **D-15** | 治理：v1.7.0 → **v1.17.0 具名例外（已正式修订）** + G3 / G23 / G26 / B19F1 import 例外 / CI（待书面追认） | spec §6 + 研究发现的额外门禁冲突；**MUST** 登记 + 追认 | 静默改门禁（拒绝）；放宽白名单（拒绝） |

**无未决澄清。**

---

## Phase 1: Design（摘要）

- **[data-model.md](./data-model.md)**：`OtlpExporter` 状态机 / 配置 / 诊断；`Span` 11 字段
  到 `ReadableSpan` / `SpanContext` / `Resource` / `InstrumentationScope` 的映射；身份哈希；
  属性归一；时间 / status / kind；失败与跳过规则；并发 / 生命周期；不变量。
- **[contracts/otlp-exporter-contract.md](./contracts/otlp-exporter-contract.md)**：
  构造签名 / 两种模式 / 校验 / TLS / headers / timeout / 诊断 / 失败隔离 / 惰性 import /
  公开面边界。
- **[contracts/span-to-otlp-mapping-contract.md](./contracts/span-to-otlp-mapping-contract.md)**：
  11 字段映射表 / 身份哈希 / 纳秒时间 / 属性值归一 / `error.type` → status / `SpanKind` /
  Resource / Scope / 不导出字段 / 无自研编码。
- **[contracts/dependency-and-gate-contract.md](./contracts/dependency-and-gate-contract.md)**：
  `[otlp]` 精确闭包 / 版本 / 许可证 / `protobuf` 归一 / G3 / G21 / G23 / G26 / CI /
  v1.17.0 具名例外 / `THIRD_PARTY_NOTICES`。
- **[contracts/backend-examples-contract.md](./contracts/backend-examples-contract.md)**：
  三示例 / 端点 / 认证 / 前置安装 / 来源 / as-of / 分工表 / 已知失效风险 / 验收口径。
- **[contracts/upstream-parity.md](./contracts/upstream-parity.md)**：P-01…P-07、E-1…E-3、
  D-601…D-608、X-1…X-5、OTel wheel 行为证据、冻结面 / 回溯修订。
- **[quickstart.md](./quickstart.md)**：安装 / 端点导出 / 桩接收端 / 失败隔离 / 三示例 /
  门禁 / 人工记录命令与预期结果。

---

## Risks & Registrations

| # | 风险 / 事项 | 处置 |
|---|---|---|
| **R-1** | v1.7.0「v1.0 无 extra」冲突 | **已按宪法 v1.17.0（2026-11-24 · MINOR）正式修订**：唯一具名例外 `[otlp]`；正式文字落 manual-verification |
| **R-2** | G3 白名单 12 → 19；`extras-v2.toml` / CI 取证变化 | **只增不改**；更新 `CONSTITUTION_DEPENDENCY_WHITELIST` / `extras-v2.toml` / `ci.yml`；基础闭包仍为空；书面追认 |
| **R-3** | G23「散文式标识 MUST 失败 / 禁止归一化」与 `protobuf` 冲突 | **仅 `protobuf` 具名归一**；更新 `_gatekit` / `gate_G23_licenses.py` / `architecture-gates.md`；**不放宽白名单**；书面追认；若不追认 ⇒ **STOP**，不得自研编码 |
| **R-4** | G26 / B19F1 import / egress 扫描会因 OTel / grpc 变红 | **具名例外**只给 3 个 OTLP 模块；`grpc` 加入网络客户端清单（更严）；其它 L5 模块禁令不变；运行时惰性断言补强 |
| **R-5** | `OTLPSpanExporter` 读 env + 内部重试 | **不用门面**；官方 `encode_spans` + `TraceServiceStub`；见 research D-03 |
| **R-6** | `Resource.create()` 读 env | 用 `Resource({...})` 直接构造；见 research D-04 |
| **R-7** | 短生命周期 gRPC channel 的连接开销 | v1 接受；无墙钟断言；未来若需连接复用，走新 feature / `exporter=` 模式 |
| **R-8** | 真实 gRPC 接收端测试在非 Linux 可能不稳定 | 桩导出器覆盖全平台；真实 gRPC 接收端标 `linux_only` + `full_install`；CI Linux 全量作业真跑 |
| **R-9** | `[otlp]` 安装体积 / CI 时间增加 | 只装 gRPC 路径（不装 HTTP / requests / certifi）；CI 全量作业安装；文档说明 |
| **R-10** | 三示例真实后端环境不可得 | 至少一个真实后端冒烟；其余桩接收端；manual-verification 写明原因 / 替代证据 / 待补验证项；已由发起者追认（2026-11-24） |
| **R-11** | OpenLIT / Langfuse / Phoenix 文档 / API 变更 | 示例 README 标注来源 + as-of + 已知风险；不承诺长期兼容；无默认推荐 |
| **R-12** | 真实模型轮 | **质量门禁 5 偏离**：本地图 + fake 模型 + 桩 / 最小接收端；真实模型轮由 **B25F1** 承接；正式追认落 manual-verification |
| **R-13** | `protobuf` 版本 / 许可证漂移 | 白名单 + G23 归一仅对 `protobuf`；版本下限由 tasks 锁定；CI G23 每次复核；漂移 ⇒ 重新核实 |
| **R-14** | `import freegraph.observability` 意外加载 OTel / grpc | `_otlp_exporter.py` 顶层不 import OTel / grpc；`_otlp_mapping` / `_otlp_transport` 仅在 `__init__` / `on_span_end` 内惰性 import；`test_b19f1_lazy.py` 子进程断言 |
| **R-15** | 文档守卫 / README / THIRD_PARTY_NOTICES 遗漏 | `test_b21f1_manual_record_guard.py` + `test_b21f1_examples.py`；守卫安排在记录写就后 |

---

## Green Baseline & Red List（宪法 v1.11.0 的基线义务）

### 基线（**2026-11-24 · 实施前实跑**）

```text
.venv/bin/python -m pytest -q --tb=no
2345 passed, 10 skipped in 132.75s (0:02:12)
```

**跳过项**（既有环境 / 开关 skip，非本 feature 相关）：
C8 占位 · `IPython` 缺失的 PNG 用例 · `mypy` 未安装 · 上游 PNG 未开启 ·
API 快照未开启更新 · Windows 分支（B20F1 权限 / B20F2 文件锁） · Windows 时钟精度档。

### 变红清单（**预登记** · 实测后 MUST 逐条核对）

| # | 可能变红的既有断言 / 文件 | 变红原因 | 处置 |
|---|---|---|---|
| **B-1** | `tests/facade/test_api_snapshot.py::test_observability_module_exports_only_its_own_symbols` | `observability.__all__` 新增 `OtlpExporter` | **更新（非放宽）**：集合加入 `OtlpExporter`；既有 7 符号逐字保留 |
| **B-2** | `tests/contracts/test_b19f1_lazy.py` | 需断言 `OtlpExporter` 在 `__all__`，且 `import observability` 不加载 OTel / grpc | **只增**断言；`trace_run_scope` 仍不在 |
| **B-3** | `tests/contracts/test_b19f1_gates.py::test_new_modules_have_no_forbidden_imports_or_env_reads` | 新 OTLP 模块 import `opentelemetry` / `grpc` | **具名例外**：只允许 3 个 `_otlp_*.py`；其它模块禁令不变；仍断言无 env |
| **B-4** | `tests/contracts/test_b19f1_gates.py::test_no_network_client_is_used_by_new_modules` | `_otlp_transport.py` 使用 `grpc` | **具名例外**：只允许 `_otlp_transport.py`；其它模块仍禁止；`grpc` 加入全局网络清单 |
| **B-5** | `tests/contracts/test_architecture.py::test_l5_observability_imports_only_stdlib_and_l1` | 新模块 import `opentelemetry` / `grpc` | **具名例外**：只允许 3 个 OTLP 模块；仍禁止 L2/L3/L4 |
| **B-6** | `tests/contracts/test_architecture.py::test_b18f1_modules_have_no_forbidden_third_party_imports` | 同上 | 同上；`langchain*` / `langsmith` / `langgraph*` 仍零 |
| **B-7** | `tests/contracts/test_architecture.py::test_b18f1_modules_have_no_env_or_egress` | `_otlp_transport.py` 是合法出站方 | **具名例外**只给传输模块；默认路径仍零出站 |
| **B-8** | `tests/contracts/test_architecture.py::CONSTITUTION_DEPENDENCY_WHITELIST` | `[otlp]` 闭包新增 7 名 | **只增** 7 名；既有 12 名逐字保留 |
| **B-9** | `tests/contracts/test_architecture.py::SIGNED_SOURCE_FILES` | 3 个新源文件 | **只增** `_otlp_exporter.py` / `_otlp_mapping.py` / `_otlp_transport.py` |
| **B-10** | `harness/scripts/gates/gate_G23_licenses.py` + `_gatekit.py` | `protobuf` 散文标识 `3-Clause BSD License` | **具名归一**：仅 `protobuf` → `BSD-3-Clause`；更新门禁文档；书面追认 |
| **B-11** | `harness/scripts/gates/gate_G26_network_static.py` + `_gatekit.py` | OTLP 传输模块 / `grpc` | `G26_EXCEPTED_MODULES` 只增 `_otlp_transport.py`；`grpc` 加入网络清单（更严） |
| **B-12** | `harness/scripts/gates/gate_G21_dependencies.py` / `gate_G23_licenses.py` 的取证对象 | `extras-v2.toml` 新增 `otlp` | 更新清单 / CI 安装；G21 仍无黑名单；G23 仍全白名单 |
| **B-13** | `.github/workflows/ci.yml` 第 5.5 步 / `ci-matrix.md` | 需安装 `.[otlp]` | **只增**安装 `opentelemetry-exporter-otlp-proto-grpc`；更新注释 / 矩阵文档 |
| **B-14** | `tests/runtime/test_acceptance_script.py` | 新一键验收 | 追加 B21F1 守卫；既有用例保留 |
| **B-15** | `harness/verification/README.md` / `harness/demo/README.md` | 新记录行 / OTLP 入口 | 追加 B21F1 行；既有行逐字保留 |
| **B-16** | 新增 `test_b21f1_manual_record_guard.py` | 若在 manual-verification 写就前加入会永久红 | **守卫安排在记录写就后**；MUST NOT 为转绿弱化断言 |
| **B-17** | 全量测试计数 | 新增测试 | 只增不减；基线 2345 passed 不下降 |

> 实施前 MUST 重跑基线；若变红，先判「是否由本 feature 落地形态导致」→ 再判「是否属冻结断言」；
> **MUST NOT** 以「实现期再说」放过。**B-17 是硬约束**：不得靠修改既有测试来「修复」。

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **新增 3 个 L5 内部模块** | `_otlp_mapping.py`（纯映射）/ `_otlp_transport.py`（官方编码 + gRPC）/ `_otlp_exporter.py`（公开面） | 全塞进一个模块 ⇒ 纯映射与 I/O 混杂、难测；映射放 L1 ⇒ 破契约层零依赖 |
| **L5 模块 import `opentelemetry` / `grpc`（具名例外）** | 可选 OTLP 导出必须复用官方 SDK / 编码 / stubs；放在 L5 是最低层可落点 | 放 L4 / 门面 ⇒ 破分层与惰性；放独立发行包 ⇒ 超出 v1 范围 |
| **G23 仅 `protobuf` 具名归一** | `protobuf` 的 LICENSE 是 BSD-3-Clause，但元数据是散文标识；不归一则无法通过 G23 | 通用对照表（破 G23 规则）；换包（OTel proto 无替代）；放宽白名单（违宪） |
| **G26 / B19F1 import / egress 具名例外** | `_otlp_transport.py` 是用户显式启用的合法出站方；OTel / grpc 是第三方依赖 | 不放行 ⇒ 无法实现；放宽扫描域 ⇒ 门禁失效 |
| **短生命周期 gRPC channel** | 不提供 `close()` / 上下文管理器；避免持久句柄 / 后台线程 / 资源泄漏 | 持久 channel + `close()` ⇒ 破公开面；后台 flush ⇒ v2；`atexit` ⇒ 全局状态 |
| **固定 `service.name="freegraph"`** | 让三后端可按服务名分组；避免 `Resource.create()` 读 env | 用户自定义 resource ⇒ 新增 API 参数 / spec 变更；不设 ⇒ `unknown_service` |

> 唯一「冻结面更新」是 L5 `observability.__all__` **只增** `OtlpExporter`、G3 白名单
> **只增** 7 名、G23 **仅 `protobuf`** 归一、G26 / B19F1 import **具名例外**；均属
> **更新（非放宽）**，已登记在 `contracts/dependency-and-gate-contract.md` 与 spec §6。

---

## Implementation Sequencing（供 /speckit.tasks 展开）

1. **Setup / Governance**：
   - `pyproject.toml` 新增 `[project.optional-dependencies] otlp = [...]`（窄例外）。
   - `specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml` 新增 `otlp` + `closed_closure`。
   - `tests/contracts/test_architecture.py` 白名单 / 署名 / L5 扫描例外。
   - `harness/scripts/gates/_gatekit.py` + `gate_G23_licenses.py`：`protobuf` 具名归一；
     `G26_EXCEPTED_MODULES` 增 `_otlp_transport.py`；`grpc` 加入网络客户端清单。
   - `.github/workflows/ci.yml` / `ci-matrix.md`：全量作业安装 `.[otlp]`。
   - `THIRD_PARTY_NOTICES`：新增 `[otlp]` 闭包与 `protobuf` 归一说明。
   - **核对 spec §6 的 G23 / B19F1 import 例外两行已存在；仅当漂移时补齐**；书面追认已完成（2026-11-24）。
2. **Mapping Core（US1 / A5）**：`_otlp_mapping.py`：身份哈希 / 时间 / 属性 / status /
   SpanKind / Resource / Scope；`test_b21f1_mapping.py`。
3. **Transport（US1 / A5）**：`_otlp_transport.py`：官方 `encode_spans` + `TraceServiceStub`；
   短生命周期 channel；TLS / insecure / headers / timeout；`test_b21f1_transport.py`
   （最小 gRPC 接收端 · Linux 全量）。
4. **Public API（US1 / US2 / US3）**：`_otlp_exporter.py`：构造校验 / 锁 / 诊断 /
   失败隔离 / 惰性 import / `exporter=` 模式；`__init__.__all__` 只增；
   `test_b21f1_export.py` + `test_b21f1_failure.py`。
5. **Default-Off / Zero-Egress（US2 / A4）**：`test_b21f1_default_off.py`；子进程断言
   `opentelemetry` / `grpc` 未加载；零 env / 零出站。
6. **Examples（US4 / A2）**：`harness/examples/B21F1/{phoenix,openlit,langfuse}.py` +
   `README.md`；`test_b21f1_examples.py`（存在 / `--help` / 分工表 / as-of）。
7. **Contracts / Gates（A1 / A2 / A3 / A4 / A5）**：`test_b21f1_contracts.py` /
   `test_b21f1_gates.py`；G3 / G21 / G23 / G26；无自研编码 AST 扫描。
8. **Differential（原则 XI）**：`test_b21f1_otlp_parity.py`（D-601…D-608；上游缺席即 skip）。
9. **Acceptance / Manual（原则 V / VI）**：`harness/verification/B21F1/acceptance.py` +
   `manual-verification.md`；**先跑真实后端冒烟（SC-015）并记录，再 finalize manual
   record**；README / demo / verification 更新；B25F1 承接条款守卫。
10. **Polish**：全量回归、G21–G30、人工记录、冻结面追认、OpenLIT 文档 as-of 复核。

---

## Notes

- `harness/demo/target.py` **零改动**（只读基准）。
- 不新增基础运行时依赖；`[otlp]` 是唯一新增 extra。
- 不新增 L1 / 门面符号；唯一新增公开符号 = L5 `OtlpExporter`。
- `Span` / `TraceSink` / `TraceRecord` / `TraceQuery` / `RunConfig` / `SuperStepResult` /
  `PregelTask` **零改动**；不导出 `TraceRecord`；不消费 B20F2 `query()`。
- `import freegraph` **不加载** L5 / OTel；`import freegraph.observability` **不加载**
  OTel / grpc；`OtlpExporter` 只在显式构造时惰性 import。
- 手动验证记录：`harness/verification/B21F1/manual-verification.md`
  （显式端点导出 / 桩接收端 / 最小 gRPC 接收端 / 失败隔离 / 三示例 / 零出站 /
  许可证归一 / 治理追认 / **质量门禁 5 偏离声明**）；
  由 `tests/runtime/test_b21f1_manual_record_guard.py` 自动守卫。
- 本命令只到 Phase 1；`tasks.md` 由 `/speckit.tasks` 生成。
