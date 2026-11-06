# B21F1 · OTLP 导出插件（可选 extra）+ 后端对接文档

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B21F1` |
> | 所属 功能块 | B21（OTLP 导出） |
> | 架构层 | L5 可观测层 |
> | 里程碑 | M4 生态（第 30 个） |
> | 前置依赖 | **B20F2** |
> | 规模 | 700 行（实现 380 / 测试 320）· 3 人日 |
> | 建议 short-name | `b21f1-otlp-export` |
> | MVP 必需（★） | **不可砍**（宪法原则 IV 的 MUST 项） |

---

## 提示词正文

### 1. 目标

交付**可观测生态出口**：把 freegraph 自有的 `Span` 编码为 **OTLP** 并导出到用户
显式提供的端点（可选 extra，**默认关闭**），同时交付**三个后端的最小对接示例**。
本 feature 的判定是：**可导出到任一 OTel 后端**。

### 2. 背景与上下文

- **宪法原则 IV 的后端对接政策是强制项**：`freegraph` **MUST** 以 OTLP 等标准协议
  输出，用户 **MAY** 自行接入 OpenLIT / Langfuse / Phoenix；**MUST NOT** 内嵌 Phoenix
  （Elastic-2.0）。
  → 因此本 feature **不可砍**：砍掉即构成对 MUST 的静默弱化（立项书 §7.2）。
  → 若必须缩减，只能降级为「仅文档化对接说明（不含 exporter 代码）」，且降级 MUST
  走宪法原则 IV 的修订流程。
- **实现口径已写死**（立项书 §5.4 DF4）：**不自研 protobuf / OTLP 编码**——
  由可选 extra `opentelemetry-exporter-otlp` 完成「自有 `Span` → OTLP」的映射。
  基础安装仍**零**第三方依赖。
- **零出站的口径**：OTLP 导出**只在用户显式传入端点时生效**；
  freegraph 自身**不得**有默认端点、不得读环境变量来推断端点。
- **达成度口径**：接上外部 OTel 后端时，可诊断性达成度约 **85%**；
  不接后端时按**保守口径 60–70%**（立项书 §5.6）。

### 3. 用户场景

**P1 — 接进我现有的 OTel 栈**
作为用户，我已有 Grafana / Langfuse / OpenLIT 栈，我希望 freegraph 的 span 能导出
到那里，从而与既有系统统一观测。

- **独立验收**：显式传入端点后，span 被导出（后端可查到）。

**P2 — 不导出时零负担**
作为用户，我不用 OTel 时，希望**完全不受影响**（不装 extra、不出站、不报错）。

- **独立验收**：未安装 extra / 未传端点时，导出路径完全不激活。

**P3 — 导出失败不阻断运行**
作为用户，后端挂了，我的图**必须**照常跑完。

- **独立验收**：端点不可达时运行成功，失败仅被记录。

### 4. 功能需求

- **FR-001**：系统 MUST 提供**可选 extra**（如 `[otel]`），其依赖为
  `opentelemetry-exporter-otlp`；基础安装 MUST NOT 引入它。
- **FR-002**：导出 MUST **默认关闭**；仅在用户**显式传入端点/导出器**时生效。
- **FR-003**：系统 MUST NOT 读取环境变量推断端点（`OTEL_EXPORTER_OTLP_*` 等亦不读——
  freegraph 内核不读任何环境变量）。
- **FR-004**：系统 MUST 提供「自有 `Span` → OTLP」的映射，映射 MUST 复用
  `opentelemetry-exporter-otlp`（**不自研 protobuf / OTLP 编码**）。
- **FR-005**：导出失败（端点不可达 / 编码失败）MUST **不阻断**核心执行
  （原则 IV：可视化层 MUST NOT 阻断执行）。
- **FR-006**：系统 MUST 交付**三个后端的最小对接示例**（OpenLIT / Langfuse /
  Phoenix），每个示例 MUST 可复制运行。
- **FR-007**：系统 MUST 交付**已知失效风险说明**（OpenLIT 文档站 404，只能依赖仓库
  README；OTel 后端 API 变更可能导致示例失效）。
- **FR-008**：系统 MUST NOT 内嵌 Phoenix（Elastic-2.0 红线）。
- **FR-009**：系统 MUST NOT import `langchain` / `langchain-core`。

### 5. 成功标准

- **SC-001**：显式传入端点后 span 被成功导出（后端可查到；可用一个最小 OTel
  collector 或桩接收端判定）。
- **SC-002**：未安装 extra / 未传端点时，**导出路径不激活**（零副作用、零出站）。
- **SC-003**：端点不可达时**运行仍成功**（导出失败不阻断）。
- **SC-004**：三个后端示例各自可运行（各一例冒烟）。
- **SC-005**：基础安装的依赖闭包**仍为空集**（extra 之外零新增）。

### 6. 验收判据（= 立项书 §5.2 B21F1 小目标，逐条可判定）

> 小目标原文：交付物清单：① OTLP exporter（**可选 extra，基于
> `opentelemetry-exporter-otlp`，不自研 protobuf/OTLP 编码**）② **三个后端的最小对接
> 示例**（OpenLIT / Langfuse / Phoenix）③ **已知失效风险说明**（OpenLIT 文档站 404）
> ④ 默认关闭，仅用户显式传入端点时生效；可选导出到任一 OTel 后端

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 可选 extra + 不自研 OTLP 编码 | 依赖声明核对 + 代码审查（无自研 protobuf） |
| A2 | 三个后端最小对接示例 | 三个示例文件存在且各有一例冒烟 |
| A3 | 已知失效风险说明 | 文档条目存在（OpenLIT 文档站 404） |
| A4 | 默认关闭，仅显式传入端点时生效 | 未传端点时零出站断言通过 |
| A5 | 可导出到任一 OTel 后端 | 导出用例（最小接收端判定） |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| OTLP exporter（可选 extra） | 自有 `Span` → OTLP | C23 / 原则 IV 的后端对接政策 |
| `Span` → OTLP 映射 | 属性名沿用 `gen_ai.*` | C23 / DF4 |

> **口径提醒**：本 feature **不新增契约条目**；它落的是宪法原则 IV 的 MUST
> （以标准协议输出）。若需调整原则 IV 的措辞，MUST 走 Governance 修订流程。

### 8. 边界（本 feature 明确不做）

- 不实现本地 Agent Server / SSE 推送（v2 / D8）。
- 不实现前端 UI（v2 / B26）。
- 不实现评测 / 数据集（永不做）。
- 不自研 protobuf / OTLP 编码（**明确不采用**）。
- 不内嵌 Phoenix（ELv2 红线），也不内嵌 Langfuse / OpenLIT（只做对接示例）。
- 不实现「自托管 trace 后端」（路线 A，**MUST NOT** 采用）。
- 不实现 async 导出（v2 范围）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：`opentelemetry-exporter-otlp` 只能在**可选 extra** 中；
  基础安装闭包不变；许可证必须 ∈ {MIT, Apache-2.0, BSD-2/3, PSF}。
- **零出站**：默认关闭；仅用户显式传入端点时导出；freegraph 内核不读任何环境变量
  （**包括 `OTEL_*`**）。
- **Elastic-2.0 禁令**：MUST NOT 内嵌 Phoenix。
- **可视化不阻断执行**：导出失败不影响运行。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：三个后端的接入方式 MUST 标注来源与 as-of 日期；
  OpenLIT 文档站 404 的事实 MUST 写明「仅依据仓库 README」。

### 10. 交付物与后续

- **交付物**：OTLP exporter（可选 extra）、`Span` → OTLP 映射、三个后端最小对接示例、
  已知失效风险说明、单元测试 + 人工验证记录。
- **风险提示（立项书 §7.5 已量化）**：若在实现时发现该 extra **无法**满足
  「自有 `Span` → OTLP」的映射（须自研编码），则本 feature **需上浮 +2 人日**
  （+2,000 元直接成本 / +4,000 元报价，总工期 +2 天）。**触发信号 = 本 feature 的 spec
  阶段确认必须自研 OTLP 编码**——spec 中 MUST 给出结论（可行 / 需上浮）。
- **后续解锁**：**B24F1**（打包分发，依赖 B23F1 + B16F1）→ **B25F1**（双跑验收）。
- **不可砍声明**：本 feature 砍掉即构成对宪法原则 IV 的 MUST 的静默弱化。

---

## 依据

- 立项书 §5.2（B21F1 行）、§5.3（C23 / C24）、§5.4（DF4 的互操作口径）、
  §5.5（依赖白名单 · `opentelemetry-*`）、§5.6（路线 B 与达成度两个口径）、
  §5.8.1（可视化 12 项之「导出 · 接入既有可观测栈」）、§7.2（B21F1 不可砍）、
  §7.5（B21F1 单点敏感性 +2 人日）、§10（R12 第三方对接文档不可用风险）、
  §9.1（门禁第 2 / 4 项）。
- 事实依据：`harness/reports/Q6-可视化与可诊断性的规模与可行性.md`（OTel 生态已解决
  trace 数据层）、`harness/reports/Q7-开源边界地图与许可证合规.md`（Phoenix = ELv2）。
- 宪法 `.specify/memory/constitution.md`：原则 IV（后端对接政策 · MUST）、
  原则 IX（Elastic-2.0 组件禁令）、原则 X（第三方归属登记 → `THIRD_PARTY_NOTICES`）。
