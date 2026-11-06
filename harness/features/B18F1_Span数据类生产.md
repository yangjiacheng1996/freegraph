# B18F1 · Span 数据类生产（节点 / 工具 / 模型三级 span，属性名对齐 `gen_ai.*`）

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B18F1` |
> | 所属 功能块 | B18（Span 数据类生产） |
> | 架构层 | L5 可观测层 |
> | 里程碑 | M3 可诊断（第 22 个） |
> | 前置依赖 | **B7F3** |
> | 规模 | 1,140 行（实现 620 / 测试 520）· 3 人日 |
> | 建议 short-name | `b18f1-span-production` |
> | MVP 必需（★） | 否 |

---

## 提示词正文

### 1. 目标

交付 freegraph 的**自有 Span 数据类**，并在运行时为**节点 / 工具 / 模型三级**产生 span。
span 的**属性命名**必须对齐 **OpenTelemetry GenAI 语义约定**（`gen_ai.*`），
以便现成的 OTel 面板能直接消费。本 feature 的判定是：**span 属性命名符合 OTel GenAI
semconv；未注入 tracer 时零副作用、零开销**。

### 2. 背景与上下文

- **路线已选定**：Q6 裁定**路线 B —— OTel 兼容追踪协议 + 轻量 UI**；
  路线 A（自研整套 Studio / 追踪后端，245–415 人日）**MUST NOT** 采用。
- **v1 的零依赖口径**（立项书 §5.4 DF4）：**v1 不依赖 OTel SDK**——基础安装只有
  **零**第三方依赖，因此 **span 由 freegraph 自有的 `Span` 数据类产出**，
  **属性命名**对齐 OTel GenAI semconv，但**不引入 `opentelemetry-*` 运行时**；
  与 OTel SDK 的互操作在 **B21F1 的可选 extra** 内完成。
- **「符合 semconv」的 v1 可判定形式**：是「**span 属性命名**符合 semconv」，
  而**不是**「产出 OTel SDK 的 span 对象」。spec 必须按此口径写成功标准。
- **零开销**：未注入 tracer 时，MUST NOT 产生任何 span 对象分配、不引入任何额外
  import 副作用（原则 IV：「未注入 tracer 时零副作用、零开销」）。
- **DF4 `Span` 的字段**（立项书 §5.4，**已随 B2F1 的冻结同步为 11 字段 · 2026-11-06**）：
  `id`（span 唯一标识）/ `name` / `attributes`（属性名对齐 `gen_ai.*`）/ `parent`（**父 span 的
  `id`**，非对象引用）/ `start_time` / `end_time` / `context` + **必带四项** `thread_id` /
  `run_id` / 节点名 / `checkpoint_id`。
  > **⚠️ 字段面归 B2F1，本 feature 只负责「生产」**（B2F1 澄清 Q2 / Q6）：字段的**逐字冻结**
  > 在 B2F1（唯一权威 = `specs/b2f1-contracts-protocols/contracts/public-api.md` §1.2）
  > ——本 feature **MUST NOT 增删字段**；确需变更走**契约修订**流程。
  > （`id` 的必要性：`parent` 以**标识**引用父 span，放对象引用则 span 不可 JSON 序列化，
  > C27 第 ③ 条作废——**无 `id` 的 span 无法被引用**。）
- ✅ **关联键（缺口 2 · 已冻结 · D11 批准 2026-11-05）**：span **必带**
  `thread_id` / `run_id` / 节点名 / `checkpoint_id`（挂接 checkpointer 时有值，否则为空）；
  **缺 `run_id` 的 span 视为实现缺陷**。修订本体见 Q8 §3.4.1 / 立项书 §5.3.1 /
  宪法原则 VII。

### 3. 用户场景

**P1 — 知道每一步跑了多久、发生了什么**
作为用户，我希望看到每个节点的 span（含名称与耗时），从而定位慢在哪一步。

- **独立验收**：注入 tracer 后，节点执行产生 span，含名称与起止时间。

**P2 — 工具与模型调用也有 span**
作为用户，我希望模型调用与工具调用各自有独立 span（而非埋在节点 span 里），
从而能单独统计模型耗时。

- **独立验收**：模型调用 / 工具调用场景各产生对应层级的 span。

**P3 — 不诊断时零负担**
作为用户，我不需要诊断时，希望 freegraph **完全不产生额外开销**。

- **独立验收**：未注入 tracer 时，无 span 对象被创建（可由计数夹具判定）。

### 4. 功能需求

- **FR-001**：系统 MUST 提供**自有 `Span` 数据类**（零第三方依赖），字段以 **B2F1 冻结面**
  为准（**11 字段逐字冻结**：`id` / `name` / `attributes` / `parent` / `start_time` / `end_time` /
  `context` + 必带四项 `thread_id` / `run_id` / 节点名 / `checkpoint_id`）——本 feature
  **MUST NOT 增删字段**（字段面归 B2F1 · 本 feature 只负责生产行为）。
- **FR-002**：系统 MUST 在节点执行时产生**节点级 span**；在检测到模型调用与工具调用
  时产生**模型级 / 工具级 span**（识别方式 MUST 基于**鸭子类型**：具备
  `invoke` 的对象 = 模型；被节点以工具方式调用 = 工具）。
- **FR-003**：span 的 `attributes` 中与模型/工具相关的属性名 MUST 对齐 OTel GenAI
  semconv 的 `gen_ai.*` 命名（如模型名、请求模型、输入/输出类型等，
  具体属性清单在 spec 中逐条列出并附 semconv 出处）。
- **FR-004**：未注入 tracer 时，MUST **零副作用、零开销**——MUST NOT 创建 span 对象、
  MUST NOT 引入额外 import 副作用、MUST NOT 读环境变量。
- **FR-005**：span MUST 支持**父子关系**（`parent` 字段），使嵌套调用可还原调用树。
- **FR-006**：span MUST 记录**耗时**（起止时间），时间源 MUST 为标准库（不引入
  OTel SDK）。
- **FR-007**：MUST NOT 引入 `opentelemetry-*` 运行时依赖（v1 硬约束）。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量。
- **FR-009**：span MUST 携带关联键 `thread_id` / `run_id` / 节点名 / `checkpoint_id`
  （**C23 字段约定，已冻结**）；四项 MUST 可读，`run_id` 缺失即视为实现缺陷。

### 5. 成功标准

- **SC-001**：span 的 `attributes` 属性名 **100% 符合** `gen_ai.*` 命名约定
  （可由「属性名清单 vs semconv 清单」逐项比对判定）。
- **SC-002**：节点 / 工具 / 模型三级 span 各有一例产生，且层级关系正确。
- **SC-003**：未注入 tracer 时创建的 span 对象数 == 0（计数夹具）。
- **SC-004**：freegraph 的运行时依赖闭包**仍为空集**（无 OTel SDK）。
- **SC-005**：span 的起止时间差 > 0（耗时被记录）。

### 6. 验收判据（= 立项书 §5.2 B18F1 小目标，逐条可判定）

> 小目标原文：span **属性命名**符合 OTel GenAI semconv；未注入 tracer 时零副作用、
> 零开销

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | span 属性命名符合 OTel GenAI semconv | 属性名清单逐项比对（附 semconv 出处） |
| A2 | 未注入 tracer 时零副作用、零开销 | span 创建计数 == 0；依赖闭包无变化 |
| A3 | 三级 span 可产生 | 节点 / 工具 / 模型各一例 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `Span`（自有数据类） | **11 字段**（B2F1 逐字冻结）：`id` / `name` / `attributes` / `parent`（父 span 的 `id`）/ `start_time` / `end_time` / `context` + 必带四项 `thread_id` / `run_id` / 节点名 / `checkpoint_id` | **C23** / DF4（**字段面归 B2F1**） |
| span 关联键 | `thread_id` / `run_id` / 节点名 / `checkpoint_id` | **✅ C23 字段约定（已冻结 · D11 2026-11-05）** |

> ✅ **口径（已冻结 · D11 批准 2026-11-05）**：立项书 §5.8.3 的**缺口 2** 已关闭——
> **每个 span MUST 带** `thread_id` / `run_id` / 节点名 / `checkpoint_id`
> （挂接 checkpointer 时有值，否则为空）；**缺 `run_id` 的 span 视为实现缺陷**
> （违反即 PR 不得合入，宪法原则 VII）。
> - `run_id` 由**运行时**在每次运行开始时生成，**不进 `RunConfig`** 的字段清单；
> - `thread_id` 由 `RunConfig` 承载（`RunConfig` 四字段不变）。

### 8. 边界（本 feature 明确不做）

- 不实现 `TraceSink` 的接入与推送（属 B19F1）——本 feature 只**生产** span。
- 不实现本地 trace 存储（属 B20F1 / B20F2）。
- 不实现 OTLP 导出（属 B21F1）——v1 不引入 OTel SDK。
- 不实现 `current_span()` 上下文 API（属 B19F1）。
- 不实现前端 UI（v2 / B26）。
- 不自研 protobuf / OTLP 编码（属 B21F1，且 v1 明确不采用）。
- 不实现「评测 / 数据集」类能力（永不做，见立项书 §3.4）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：v1 基础安装依赖闭包**为空集**；
  `opentelemetry-*` 只允许出现在 **B21F1 的可选 extra** 中。
- **零出站 / 零环境变量**：span 生产不得触发任何出站。
- **ARCH-1 / ARCH-3**：L5 只依赖 L1 协议；跨层只传纯数据。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：每个 `gen_ai.*` 属性名 MUST 附 semconv 出处
  （`github.com/open-telemetry/semantic-conventions`，Apache-2.0）。

### 10. 交付物与后续

- **交付物**：自有 `Span` 数据类、三级 span 生产接入、属性命名清单（含 semconv 对照）、
  零开销夹具、单元测试 + 人工验证记录。
- **后续解锁**：**B19F1**（`TraceSink` 接入 + `current_span()`）→ **B20F1**（本地存储）。
- **风险提示**：本 feature 的「零开销」判据必须是**可测的计数断言**（span 创建数 == 0），
  而不是「感觉没有开销」；否则将来加埋点时不会有任何红线提醒。

---

## 依据

- 立项书 §5.2（B18F1 行）、§5.3（C23 / C24）、§5.4（DF4 `Span` 的口径说明）、
  §5.5（依赖白名单）、§5.6（路线 B）、§5.8.1（可视化 12 项之「Trace · span 生产」）、
  §5.8.3（缺口 2 / D11）、§9.1（门禁）。
- 语义约定：`github.com/open-telemetry/semantic-conventions`（Apache-2.0，`gen_ai.*`）。
- 路线依据：`harness/reports/Q6-可视化与可诊断性的规模与可行性.md` §1 / §4.2。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C23 / C24）。
- 宪法 `.specify/memory/constitution.md`：原则 IV（可诊断性是一等功能 · 路线 B）。
