# B19F1 · `TraceSink` 接入 + `current_span()` + 默认关闭

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B19F1` |
> | 所属 功能块 | B19（`TraceSink` + `current_span`） |
> | 架构层 | L5 可观测层 |
> | 里程碑 | M3 可诊断（第 23 个） |
> | 前置依赖 | **B18F1** |
> | 规模 | 840 行（实现 380 / 测试 460）· 3 人日 |
> | 建议 short-name | `b19f1-tracesink-current-span` |
> | MVP 必需（★） | 否 |

---

## 提示词正文

### 1. 目标

把 B18F1 生产的 span **推送给用户注入的接收端**：提供 `TraceSink` 协议接入点与
`current_span()` 上下文 API，使「当前 span」在嵌套调用中可被访问。
本 feature 的判定是：**嵌套 span 父子关系正确；不注入 tracer 时零副作用**。

### 2. 背景与上下文

- **C23（可观测挂钩）**：`tracer` / callback 接口——**默认关闭**；用户**显式传入**
  才生效。freegraph **不用 `RunnableConfig` 的 `callbacks`**（那是 `langchain-core`
  类型，复用即破红线），而是自有 `TraceSink` 协议。
- **C24（当前 span 上下文）**：`current_span()`（对标 LangSmith 的
  `get_current_run_tree`）——**LangSmith 特有 → freegraph 自有协议**；是多 agent
  嵌套 trace 的基础。
- **默认关闭的含义**：**没有注入 `TraceSink` 时，freegraph 的行为与没有可观测层
  完全一致**——不推送、不分配、不出站。这与 LangChain 形成鲜明对照（LangChain 在
  `LANGSMITH_API_KEY` 存在时**自动开 tracing**，Q3 实测）。
- ✅ **缺口 3 已关闭（D11 批准 2026-11-05）**：`stream()` 与 `TraceSink` 仍是**两条
  事件通道**，但**共享同一 `run_id` / `thread_id`**（关联约定已冻结，见 §7）。
- **承接条款（B9F1 → B19F1 · M3 · `Command` 跳转的触发源暴露口径）**：B9F1 已交付 `Command`
  原语的**运行期语义**（`goto` / `update` / `Command.PARENT`）并**冻结**了跨 feature 的接口口径
  ⇒ **本 feature MUST** 照它写：
  - **触发源同源口径**：B9F1 已把 `Command.goto` 落在 B7F1 的**边触发源**空间
    （标识 `("e", 源节点名)`）⇒ `goto` 与**静态边**的触发源**同源** ⇒ 若 span 要展示
    「这个节点是被什么触发的」，**MUST** 由本 feature 在**触发判定层统一暴露**
    （静态边与 `goto` **一起**给）⇒ **MUST NOT** 只暴露 `goto` 一类（否则可观测面只剩一半）；
  - **不预留口径**：B9F1 **刻意未**在结果对象/调度状态里新增任何「跳转观测字段」
    （B7F1 的 `SuperStepResult` **四字段冻结面**不动 · 跳转的可观察证据 = 下一轮 `executed` +
    L1 的 `StateSnapshot.next`）⇒ 本 feature **MUST NOT** 期待 B9F1 预先提供跳转记录
    ⇒ 触发源信息 **MUST** 由本 feature 自行在**调度层**取得。
  该口径由 B9F1 的 `specs/b9f1-command-primitive/spec.md`（FR-002 / FR-022 / 裁定 1 / 裁定 18 /
  裁定 19）落成。

### 3. 用户场景

**P1 — 把运行轨迹接到我自己的系统**
作为用户，我实现一个 `TraceSink`（收 `on_span_start` / `on_span_end`）并传给 freegraph，
从而在**自己的**日志系统里看到每次运行的轨迹——不需要任何 SaaS 账号。

- **独立验收**：注入 sink 后，节点执行触发 `on_span_start` / `on_span_end` 配对调用。

**P2 — 嵌套调用能还原调用树**
作为用户，我的节点里调用了另一个「子任务」，我希望 span 呈父子结构而非平铺。

- **独立验收**：嵌套场景下子 span 的 `parent` == 父 span。

**P3 — 不注入就完全没这回事**
作为用户，我不诊断时，希望 freegraph **完全静默**（无推送、无开销、不读环境变量）。

- **独立验收**：未注入 sink 时，`on_span_start` 调用数 == 0；依赖闭包无变化。

### 4. 功能需求

- **FR-001**：系统 MUST 支持把 `TraceSink` 实例注入运行时（注入点形态 MUST 在 spec 中
  写死：编译期关键字或运行配置，两者择一并说明理由）。
- **FR-002**：注入生效时，每个 span 的开始 MUST 触发 `on_span_start`、结束 MUST 触发
  `on_span_end`，且**成对**（异常路径下也 MUST 成对）。
- **FR-003**：系统 MUST 提供 `current_span()`：返回**当前** span（无当前 span 时
  返回空值语义，MUST NOT 抛异常）。
- **FR-004**：`current_span()` MUST 支持**嵌套**语义（内层结束后外层恢复为当前 span）。
- **FR-005**：**未注入 sink 时 MUST 零副作用、零开销**——MUST NOT 创建 span、
  MUST NOT 触发任何回调、MUST NOT 读环境变量。
- **FR-006**：`TraceSink` MUST 是**协议**（`typing.Protocol`），用户无需继承基类
  （B2F1 已冻结）。
- **FR-007**：系统 MUST NOT 引入 OTel SDK 运行时依赖（v1 硬约束；OTLP 属 B21F1）。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量。

### 5. 成功标准

- **SC-001**：嵌套 span 的父子关系正确（子 span `parent` == 父 span，100%）。
- **SC-002**：不注入 tracer 时零副作用（回调调用数 == 0；span 创建数 == 0）。
- **SC-003**：`on_span_start` / `on_span_end` 在正常与异常路径下均**成对**。
- **SC-004**：`current_span()` 在嵌套内返回内层 span、退出后恢复外层。
- **SC-005**：freegraph 运行时依赖闭包**仍为空集**（零第三方运行时依赖）。

### 6. 验收判据（= 立项书 §5.2 B19F1 小目标，逐条可判定）

> 小目标原文：嵌套 span 父子关系正确；不注入 tracer 时零副作用

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 嵌套 span 父子关系正确 | 父子断言（`parent` 引用相等） |
| A2 | 不注入 tracer 时零副作用 | 回调计数 == 0 且 span 创建计数 == 0 |
| A3 | `current_span()` 可用 | 嵌套场景断言 + 空上下文行为断言 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `TraceSink`（协议） | `on_span_start` / `on_span_end` / `current_span` | **C23** |
| `current_span()` | 当前 span 上下文 | **C24** |
| 两通道关联 | `stream()` 与 `TraceSink` 共享 `run_id` / `thread_id` | **✅ 已冻结（D11，2026-11-05）** |

> ✅ **口径（已冻结 · D11 批准 2026-11-05）**：立项书 §5.8.3 的**缺口 3** 已关闭——
> `stream()` 产出的事件与 `TraceSink` 收到的 span **共享同一 `run_id` / `thread_id`**，
> MAY 按 id 合并为一条时间线（Q8 §3.4.1 / 立项书 §5.3.1 / 宪法原则 VII）。
> - `run_id` 由运行时在每次运行开始时生成（**用户不设置**）；`thread_id` 由 `RunConfig`
  承载；
> - **本 feature 的义务**：`TraceSink` 收到的每个 span MUST 带 `run_id` / `thread_id` /
>   节点名 / `checkpoint_id`（与 `stream()` 事件同源同 id）。

### 8. 边界（本 feature 明确不做）

- 不实现本地 trace 存储与查询（属 B20F1 / B20F2）。
- 不实现 OTLP 导出（属 B21F1）。
- 不实现 `compile(tracer=)` 之外的注入形态（若选运行配置注入，则本 feature 只提供该形态）。
- 不实现前端 UI（v2 / B26）。
- 不实现评测 / 数据集（永不做）。
- 不自研 OTLP 编码（v2 / B21F1 明确不采用）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`；
  v1 不引入 `opentelemetry-*` 运行时。
- **零出站 / 零环境变量**：**环境变量存在也不得改变任何行为**（宪法原则 I 的
  「反着做」要求——只有用户显式注入才生效）。
- **ARCH-1 / ARCH-3**：L5 只依赖 L1；跨层只经由协议 + 纯数据。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：与 LangSmith `get_current_run_tree` 的对应关系须标注来源。

### 10. 交付物与后续

- **交付物**：`TraceSink` 接入点、`current_span()`、默认关闭机制、嵌套父子关系测试、
  人工验证记录。
- **后续解锁**：**B20F1**（本地 Trace 存储：JSONL 后端）→ **B20F2**（查询 API +
  SQLite 后端）→ **B21F1**（OTLP 导出）。
- **形态联动（必读）**：`harness/demo/README.md` 明确列出「`compile(tracer=)` 注入
  `TraceSink` 的载体」是**待锁定的形态**，随 **M3 各 feature 的 spec** 一同锁定。
  本 feature 正是锁定它的时点——spec 必须在「编译期关键字」与「运行配置」之间**择一**，
  并写明理由；锁定后 `harness/demo/README.md` 的对应条目应更新。

---

## 依据

- 立项书 §5.2（B19F1 行）、§5.3（C23 / C24）、§5.4（P3 `TraceSink` 协议）、
  §5.8.1（可视化 12 项之「Trace · span 推送」）、§5.8.3（缺口 3 / D11）、
  §9.2（验收脚本形态与 API 形态一并确定的约定）、§9.1（门禁）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C23 / C24）。
- 验收脚本约定：`harness/demo/README.md`（M3 待锁定形态清单）。
- 宪法 `.specify/memory/constitution.md`：原则 I（环境变量存在也不得改变行为）、
  原则 IV（可观测性 · 默认关闭）。
