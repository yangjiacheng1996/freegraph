# B8F2 · `stream()`：多模式流式输出 + `StreamWriter`

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B8F2` |
> | 所属 功能块 | B8（路由语义 + stream + 别名/context） |
> | 架构层 | L2 执行内核层 |
> | 里程碑 | M2 图定义与对外 API（第 19 个） |
> | 前置依赖 | **B7F3** |
> | 规模 | 1,180 行（实现 620 / 测试 560）· 3 人日 |
> | 建议 short-name | `b8f2-stream-modes` |
> | MVP 必需（★） | 否（但**是「可诊断性」三件套的运行侧基础**） |

---

## 提示词正文

### 1. 目标

交付 `stream()`：以**流式**方式产出运行过程事件，支持多种流式模式，让用户能在图
运行过程中**实时观察**每一步的产出。本 feature 的判定是：**多模式流式输出**。

### 2. 背景与上下文

- **C12（流式）**：`stream(input, stream_mode=...)`，mode 名称是 **LangGraph 特有**
  （须同名），取值至少覆盖 `values` / `updates` / `checkpoints` / `tasks` / `debug` /
  `messages` / `custom`。
- **「可诊断性是一等功能」（宪法原则 IV）**：流式是用户「实时观察运行」的手段
  （立项书 §5.8.2 第 7 项）。
- **`StreamWriter`**：节点内部主动向流写自定义数据的能力（`custom` 模式的来源）。
- **可视化不阻断执行（宪法原则 IV）**：流式消费 MUST NOT 影响图的执行语义；
  消费者不取（不迭代）时，图仍应能正常跑完。
- 本 feature 与 B19F1（`TraceSink`）是**两条独立的事件通道**——D11 尚未批准前，
  二者的关联性未规定；spec 中 MUST 标注这一未冻结项（见 §7）。
- **上游的 `StreamWriter` 机制**（**照抄依据** · `langgraph 1.2.11`）：
  `langgraph/config.py:126` 的 `get_stream_writer()` 靠 **contextvar** 取写入器；
  跨线程可见性由**执行器**的 **`copy_context()`** 提供（`langgraph/pregel/_executor.py:64`
  的 `copy_context()` 与 `:71` 的 `ctx.run(fn, …)`；async 路径见 `:164`）
  ⇒ ⇒ ⇒ 本仓库的落点见「下游承接（B7F1 + B10F1）」条。
- **上游的 `tasks` 档产出粒度**（**照抄依据**）：`langgraph/pregel/_loop.py:580` 与 `:674`
  的 `self._emit("tasks", map_debug_tasks, …)` ⇒ ⇒ ⇒ 产出 **task 级**事件（**每个**
  task 完成时一条）⇒ 载荷 = `langgraph/types.py:637` 的 `PregelTask`（**七字段**：
  `id` / `name` / `path` / `error` / `interrupts` / `state` / `result`）⇒ ⇒ ⇒ 本仓库
  契约层**已有**逐字同名的 `PregelTask`（`src/freegraph/contracts/types.py:141`）⇒ ⇒ ⇒
  ⇒ ⇒ ⇒ **零新增公开面**。
- **上游的「单步 / 整轮」分离**（**照抄依据**）：`PregelLoop.tick()`
  （`langgraph/pregel/_loop.py:599` · 注释「Execute a single iteration of the Pregel
  loop」）⇒ ⇒ ⇒ `stream()` 的主循环 = `while loop.tick(): … yield`
  （`langgraph/pregel/main.py:2964`）⇒ ⇒ ⇒ **单步是一等公民** ⇒ ⇒ ⇒ 本仓库的对应物
  = `run_super_step`（**B7F1 已交付**）⇒ ⇒ ⇒ **零新增 L2 入口**。

### 3. 用户场景

**P1 — 观察每一步的状态演进**
作为用户，我在开发期想看到图跑到每一步时的完整状态，以便定位问题出在哪一步。

- **独立验收**：`stream_mode="values"` 产出随执行推进的状态序列。

**P2 — 只看每步的增量**
作为用户，我只想看每步**改了什么**（而非全量状态），以便快速定位变化点。

- **独立验收**：`stream_mode="updates"` 产出每步的更新增量。

**P3 — 节点主动写自定义数据**
作为用户，我的节点想主动往流里写一条进度信息（如「正在检索…」）。

- **独立验收**：节点内经 `StreamWriter` 写入的内容出现在 `custom` 模式的流中。

### 4. 功能需求

- **FR-001**：系统 MUST 提供 `stream(input, stream_mode=...)`，返回**可迭代对象**
  （生成器或等价可迭代结构）。
- **FR-002**：系统 MUST 支持的 mode 名 MUST 与 LangGraph 一致，至少覆盖：
  `values` / `updates` / `checkpoints` / `tasks` / `debug` / `messages` / `custom`
  （C12）。
- **FR-003**：`values` 模式 MUST 产出每步之后的**完整状态**。
- **FR-004**：`updates` 模式 MUST 产出每步的**更新增量**。
- **FR-005**：系统 MUST 提供 `StreamWriter`（节点侧写入自定义数据的入口），
  其数据 MUST 在 `custom` 模式中产出。
- **FR-006**：流式消费 MUST NOT 改变图的执行语义；消费者提前停止迭代时，MUST NOT
  造成资源泄漏或状态不一致（至少：不吞异常）。
- **FR-007**：MUST NOT 引入 async（`astream` 属 v2 范围，未排 feature）——
  本 feature 只做同步流。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量。
- **FR-009**：`stream()` MUST **逐轮**产出 ⇒ ⇒ ⇒ MUST 以**单轮入口**
  （`run_super_step`）**反复驱动**（**上游同款** · `PregelLoop.tick()` · 见 §2 背景）
  ⇒ ⇒ ⇒ MUST **NOT** 改动既有 L2 入口（`run_super_step` / `run_super_steps`）的
  **签名**（**B7F1 的冻结面** · 契约 §1）⇒ ⇒ ⇒ ⇒ 要改 ⇒ MUST 走「破冻结面的三条」。
- **FR-010**：`tasks` 档 MUST 产出 **task 级**事件（**每个** task 完成时一条 · **上游
  同款**）⇒ ⇒ ⇒ 载荷 MUST 用 `freegraph.contracts.PregelTask`（**七字段**与上游**同名
  同义**）⇒ ⇒ ⇒ ⇒ `SuperStepResult` MUST 增 `tasks` 字段 ⇒ ⇒ ⇒ ⇒ MUST **NOT** 删既有
  **4** 个字段（**拆分而不删**）⇒ ⇒ ⇒ ⇒ 扩 `SuperStepResult` = **破 B7F1 的冻结面**
  ⇒ ⇒ ⇒ MUST 走「破冻结面的三条」（**登记 + 回溯修订 + 发起者追认**）。
- **FR-011**：节点侧的 `StreamWriter` 写入 MUST 照抄上游的 **contextvar + 执行器
  `copy_context()`** 传播机制（见 §2 背景）⇒ ⇒ ⇒ MUST **NOT** 另立一套**并行**的显式
  传参机制（原则 XII「零重复载体」）⇒ ⇒ ⇒ ⇒ 落点 = 给
  `src/freegraph/runtime/_concurrency.py` 的 `run_tasks_concurrently` 加
  `copy_context()` ⇒ ⇒ ⇒ ⇒ ⚠️ 该改动使 `_interrupt.py` docstring 的「线程池**不继承**
  `contextvars`（**实测**）」表述**对 freegraph 的执行器**不再为真 ⇒ ⇒ ⇒ ⇒ MUST
  **回溯修订**该表述与 B10F1 契约 §3（**只补注记** · **原描述不改写**）⇒ ⇒ ⇒ ⇒ B10F1
  的两级 ContextVar 机制 MUST **NOT** 被移除（它照常工作）⇒ ⇒ ⇒ ⇒ ⇒ **判据只收紧**。
- **FR-012**：`values` 档的**完整状态**归一 MUST 在 **L3**（门面侧 · 与 `invoke()`
  **同模块**）完成 ⇒ ⇒ ⇒ MUST 复用 B7F3 的 `_full_state`（**单一实现点** · B7F3 的
  下游承接 D-1）⇒ ⇒ ⇒ MUST **NOT** 复制到 L2（**ARCH-1** · L2 只依赖 L1）⇒ ⇒ ⇒ ⇒
  ⇒ ⇒ ⇒ **L2 只负责产出每轮的稀疏状态**。

### 5. 成功标准

- **SC-001**：7 种 mode 名全部被接受（非法 mode 名抛明确异常）。
- **SC-002**：`values` 模式产出的状态序列 == 对应 `invoke` 的最终状态（最后一个元素）。
- **SC-003**：`updates` 模式产出每步增量，且增量可合并回最终状态（合并结果 ==
  `invoke` 的最终状态）。
- **SC-004**：`StreamWriter` 写入的数据出现在 `custom` 流中。
- **SC-005**：流式执行过程中不产生额外出站、不读环境变量。

### 6. 验收判据（= 立项书 §5.2 B8F2 小目标，逐条可判定）

> 小目标原文：多模式流式输出

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 多模式流式输出 | 7 种 mode 各有一例产出断言 |
| A2 | `values` 与 `invoke` 终态一致 | 等值断言 |
| A3 | `updates` 可合并回终态 | 合并断言 |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `stream(input, stream_mode)` | 流式执行入口 | **C12** |
| `StreamWriter` | 节点侧自定义数据写入 | C12 |
| 事件通道 | `stream()` 与 `TraceSink` 为**两条独立通道**，共享 `run_id` / `thread_id` | **✅ 已冻结（D11 2026-11-05）** |

> ✅ **口径（已冻结 · D11 批准 2026-11-05）**：立项书 §5.8.3 的**缺口 3** 已关闭——
> `stream()` 产出的事件与 `TraceSink` 收到的 span **共享同一 `run_id` / `thread_id`**
> （Q8 §3.4.1 / 立项书 §5.3.1 / 宪法原则 VII）。
> - `thread_id` = **会话**标识（由 `RunConfig` 承载，字段清单不变）；
> - `run_id` = **单次运行**标识（由运行时在每次 `invoke` / `stream` 开始时生成，
>   **用户不设置**，**不进 `RunConfig`**）；
> - **本 feature 的义务**：`stream()` 产出的每一条事件 MUST 携带 `run_id` 与 `thread_id`
>   （可作为事件载荷的字段或事件信封的字段，**形态在 spec 中写死**），以便与 span 树
>   按 id 合并为一条时间线。

### 8. 边界（本 feature 明确不做）

- 不实现 `astream`（v2 范围，未排 feature）。
- 不实现 trace span 的生产（属 B18F1）与 `TraceSink` 接入（属 B19F1）。
- 不实现 checkpoint 事件（`checkpoints` mode 的真实数据源属 B14F1——本 feature 可先
  产出占位或空序列，但 MUST 明确其语义边界）。
- 不实现 `messages` mode 的 LangChain 消息抽取语义（**LangChain 特有**，属 freechain；
  freegraph 只做**原样透传**）。
- 不实现前端 / UI 消费（v2，B26）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：无 `langsmith` / `langchain*` / `langgraph*`。
- **零出站 / 零环境变量**。
- **ARCH-1**：L2 只依赖 L1。
- **可视化不阻断执行**（宪法原则 IV）：流式消费不得改变执行语义。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：mode 名与语义须附 LangGraph 源码 / 文档来源
  （`langgraph/types.py:122-124` `StreamMode` 字面量；说明 docstring 至 `:136`）。

### 10. 交付物与后续

- **交付物**：`stream()` 实现（7 种 mode）、`StreamWriter`、单元测试 +
  人工验证记录。
- **逐 feature 的一键验收脚本**：`harness/verification/B8F2/acceptance.py`
  （仓库既有范式 · **16** 个 feature 均有）⇒ ⇒ ⇒ 退出码 `0` PASS / `1` FAIL /
  `2` 环境未就绪 ⇒ ⇒ ⇒ MUST 打印 `B8F2 acceptance: PASS|FAIL` ⇒ ⇒ ⇒ 并由一条
  pytest **真跑**它（**纳入 CI 的常驻门禁** ⇒ 脚本与实现漂移 ⇒ 立刻红）。
- **破冻结面的登记与回溯修订**（**FR-010 / FR-011** 触发）⇒ ⇒ ⇒ MUST 走宪法 v1.8.0 的
  「破冻结面的三条」（登记 + 回溯修订 + 发起者追认）⇒ ⇒ ⇒ 受影响的上游已交付文档 =
  **B7F1** 的 `superstep-contract.md`（`SuperStepResult` 的构造签名）与 **B10F1** 的
  `interrupt-resume-contract.md` §3 + `src/freegraph/runtime/_interrupt.py` 的 docstring
  ⇒ ⇒ ⇒ **只补注记** · 原描述**不改写**（宪法 v1.14.0）。
- ⚠️ **规模口径的登记**（**不**单方面修改）：立项书 §5.2 的 B8F2 行写「1,180 行 · 3 人日」
  ⇒ ⇒ ⇒ **FR-009…FR-012** 带来**额外工作量**（线程池 `copy_context()` + `SuperStepResult`
  扩字段 + 两份上游契约的回溯修订 + 一键验收脚本）⇒ ⇒ ⇒ 本 feature 以**实现期实测**为准
  ⇒ ⇒ ⇒ **行数 / 工时的修订属发起者职权**（与 B8F1 的**登记项 R-5** 同款处置 · 原则 VIII）。
- **后续解锁**：**B22F1**（`get_graph` + `draw_mermaid`）→ **B23F1**（PNG）。
- **验收脚本联动**：`harness/demo/visualization.py` 覆盖 C12–C15 / C26，
  其中「七种流式模式」一项由本 feature 交付——该脚本在 M2 阶段应转绿。
- **风险提示**：mode 名是 LangGraph **特有**约定——若实现时「顺手」改成自造名字，
  验收脚本会直接失败。spec 阶段把 mode 名**逐个列出**并作为 FR。

---

## 下游承接（**B7F3** · 2026-11-16 · **只接线 · 逐条最小改动**）

- **D-1（B7F3 → B8F2 · M2 · 「完整状态」的归一）**：`stream()` 的 `values` 档 MUST 与
  B7F3 的 `invoke()` **逐字同款**（同一份「稀疏视图 + 补齐无值 key」的归一 ⇒ **单一实现点**）
  ⇒ ⇒ MUST NOT 另写一份「补齐」逻辑；`updates` 档（增量）**不受**本口径约束。
  ⇒ ⚠️ **层纪律（ARCH-1）**：`_full_state` 是 **L3 模块内**的私有函数 ⇒ ⇒ `stream()` 的**门面侧**（L3 · 与 `invoke()` **同模块**）MUST **复用**它 ⇒ ⇒ **MUST NOT** 让 **L2 依赖 L3**（反向 import）⇒ ⇒ **L2 只负责产出事件**（每轮的稀疏状态），**归一**在 L3 侧完成。
  ⇒ 落点：`specs/b7f3-invoke-full-state/spec.md` 的**下游承接 D-1** · 契约 **CF-01**。
- **D-5（B7F3 → B8F2 · M2 · `config` 注解放宽的归属）**：L1 `CompiledGraph.stream` 的
  `config` 注解仍写 `RunConfig | None` ⇒ ⇒ 它的放宽归 **B8F2 自己**走「登记 + 回溯修订 +
  发起者追认」⇒ ⇒ MUST 复用 B7F3 已定的**载体边界**（`RunConfig` = 会话面 + `max_concurrency`；
  普通映射 = 运行期参数 ⇒ **原样**交给 L2 ⇒ MUST NOT 在门面层翻译成 `RunConfig`）。
  ⇒ 落点：`specs/b7f3-invoke-full-state/spec.md` 的**下游承接 D-5** · 契约 **CF-05**。

## 下游承接（**B7F1 + B10F1** · 2026-11-18 · **只接线 · 逐条最小改动**）

- **D-1（B7F1 → B8F2 · M2 · 「单轮驱动」的入口形态）**：`stream()` MUST 以**单轮入口**
  `run_super_step` **反复驱动**（**上游同款** · 上游的 `PregelLoop.tick()` 注释
  「Execute a single iteration of the Pregel loop」· `langgraph/pregel/_loop.py:599`
  ⇒ `stream()` 的主循环 = `while loop.tick(): … yield` · `langgraph/pregel/main.py:2964`）
  ⇒ ⇒ ⇒ 本 feature MUST **NOT** 改动既有 L2 入口（`run_super_step` / `run_super_steps`）的
  **签名**（**B7F1 的冻结面** · 契约 §1）⇒ ⇒ ⇒ ⇒ **零新增 L2 入口** ⇒ ⇒ ⇒
  ⇒ ⇒ ⇒ 该形态是**上游同款** ⇒ ⇒ ⇒ **无需发起者另行裁决**。
  ⇒ 落点：`specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1（两个入口的签名）
  · `specs/b8f2-stream-modes/spec.md` 的 **FR-009**。
- **D-2（B7F1 → B8F2 · M2 · 「结果对象」的 task 级载荷）**：`tasks` 档 MUST 产出
  **task 级**事件（**每个** task 完成时一条 · **上游同款** · 上游
  `langgraph/pregel/_loop.py:580` / `:674` 的 `self._emit("tasks", map_debug_tasks, …)`
  ⇒ 载荷 = `langgraph/types.py:637` 的 `PregelTask` **七字段**）
  ⇒ ⇒ ⇒ 本仓库契约层**已有**逐字同名的 `PregelTask`
  （`src/freegraph/contracts/types.py:141`）⇒ ⇒ ⇒ ⇒ **零新增公开面**
  ⇒ ⇒ ⇒ ⇒ `SuperStepResult` MUST 增 `tasks` 字段 ⇒ ⇒ ⇒ ⇒ **MUST NOT** 删既有
  **4** 个字段（**拆分而不删**）⇒ ⇒ ⇒ ⇒ ⚠️ **这是破 B7F1 的冻结面**（契约 §1 的
  `SuperStepResult(state, executed, node_writes, steps)` 构造签名）⇒ ⇒ ⇒ ⇒ MUST 走
  「破冻结面的三条」（**登记 + 回溯修订 + 发起者追认**）⇒ ⇒ ⇒ ⇒ **B8F2 有自己的
  一次追认额度**（宪法 v1.8.0「每 feature ≤ 1 次」）。
  ⇒ 落点：`specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 与 §5.3
  · `specs/b8f2-stream-modes/spec.md` 的 **FR-010**。
- **D-3（B10F1 → B8F2 · M2 · `StreamWriter` 的跨线程可见性）**：节点侧的 `StreamWriter`
  写入 MUST 照抄上游的 **contextvar + 执行器 `copy_context()`** 传播机制
  （`langgraph/config.py:126` 的 `get_stream_writer()` + `langgraph/pregel/_executor.py:64`
  与 `:164` 的 `ctx.run(fn, …)`）⇒ ⇒ ⇒ 本仓库的落点 = 给
  `src/freegraph/runtime/_concurrency.py` 的 `run_tasks_concurrently` 加
  `copy_context()` ⇒ ⇒ ⇒ ⇒ **MUST NOT** 另立一套**并行**的显式传参机制
  （原则 XII「零重复载体」）⇒ ⇒ ⇒ ⇒ ⚠️ 该改动使 `_interrupt.py` docstring 的
  「线程池**不继承** `contextvars`（**实测**）」表述**对 freegraph 的执行器**不再为真
  ⇒ ⇒ ⇒ ⇒ MUST **回溯修订**该表述与 B10F1 契约 §3（**只补注记** · **原描述不改写**）
  ⇒ ⇒ ⇒ ⇒ B10F1 的两级 ContextVar 机制 MUST **NOT** 被移除（它照常工作 · 零脏状态
  更成立）⇒ ⇒ ⇒ ⇒ ⇒ **判据只收紧**。
  ⇒ 落点：`specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md` §3
  · `src/freegraph/runtime/_interrupt.py` 的模块 docstring
  · `specs/b8f2-stream-modes/spec.md` 的 **FR-011**。

## 下游承接（B8F1 · 2026-11-18 · **只接线 · 逐条最小改动**）

- **D-1（B8F1 → B8F2 · M2 · `stream()` 的路由口径）**：`stream()` 的每一档的**路由判定** MUST 与
  **B8F1** 交付的**路由求值实现点** **逐字同款**（**同一份**实现 ⇒ **MUST NOT** 另写一份）
  ⇒ ⇒ 路由判定 MUST 在 `stream()` 的**同一次**执行里可观察 ⇒ ⇒ 「稀疏视图 + 补齐」（B7F3 的
  D-1）口径**继续**适用 ⇒ ⇒ **MUST NOT** 让 `stream()` 自己求值路由。
  ⇒ 落点：`specs/b8f1-conditional-edges-fresh-read/spec.md` 的**下游承接 D-1** ·
  契约 `conditional-edge-contract.md` §2。

## 依据

- 立项书 §5.2（B8F2 行）、§5.3（C12）、§5.8.1（可视化 12 项接口之「运行 · 流式事件」）、
  §5.8.2（第 7 项）、§5.8.3（缺口 3 / D11）、§9.1（门禁）。
- 源码参照：`langgraph/types.py:122-124`（`StreamMode` 字面量；说明 docstring 至 `:136`）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C12）。
- 验收脚本：`harness/demo/visualization.py`（七种流式模式用例）、
  `harness/demo/graph_core.py`（`stream_mode="updates"` 用例）。
- 宪法 `.specify/memory/constitution.md`：原则 IV（可视化不阻断执行）。
