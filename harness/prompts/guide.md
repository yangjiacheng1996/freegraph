# freegraph 开发指南：架构、模块与 Phase 拆解

> **本文件回答三个问题**：
> 1. 是否要设计架构？初步架构是什么？
> 2. 是否要拆成多个 Feature 模块？如何拆？模块之间用什么数据格式与协议交互？
> 3. 每个模块体量是否超过 5000 行？如何拆成 Phase 使 Phase 与 speckit 闭环一一对应？
>
> **调研方法**：本指南不靠拍脑袋。所有结构判断都有三处硬证据支撑：
> ① **源码实测**——本机已装 `langgraph 1.2.11` / `langchain-core 1.6.3`，逐文件逆向
>    `pregel/_algo.py`、`pregel/_loop.py`、`graph/state.py`、`channels/*.py`、`checkpoint/**`，
>    得到**每个机制的真实实现规模**（LOC 精确计数见 §4.1）；
> ② **调研报告**——`harness/reports/Q1–Q8` 与 `00-调研总览与MVP范围建议.md`（9 份，共约 24 万字符）；
> ③ **宪法**——`.specify/memory/constitution.md` v0.0.1（原则 I–X + 7 项质量门禁）。
>
> **日期**：2026-11-03｜**适用版本**：freegraph v1（对应宪法「路线 B」技术路线）
>
> **本文件不是 spec**。它是**开发指南**：给出决策与拆解方案，供发起者拍板后，
> 转为 `harness/proposals/` 下的设计提案，再逐个进入 speckit 闭环。

---

## 0. TL;DR — 三个问题的直接回答

| # | 问题 | 结论 | 一句话方案 |
|---|---|---|---|
| **1** | 是否要设计架构？ | ✅ **要，但只设计「分层 + 契约」这一种架构，不做微服务/事件驱动/插件市场** | **6 层单向依赖 + 1 个「契约层（contracts）」**。层间只允许通过 `typing.Protocol` + 纯数据类交互；契约层是唯一允许被所有层依赖的模块。理由：Q8 实证 LangGraph 的 135 处 `langchain_core` 引用只集中在 **4 个接缝**（`RunnableConfig` / `Runnable` / `Graph` / callbacks-tracers），**证明"分层 + 契约"是唯一可行的解耦形态**，也是剥离 LangSmith 的物理保证。 |
| **2** | 是否拆成多个 Feature 模块？ | ✅ **要，拆成 8 个 Feature 家族 / 25 个交付 Feature**，模块间用 **4 类协议 + 3 种数据格式**交互 | 依赖关系与协议见 §3。**关键约束**：Feature 必须是**可独立验收的垂直切片**（能单独通过门禁），而不是按技术分层切。契约层（家族 A1）是所有其他 Feature 的前置依赖。 |
| **3** | Phase 拆解？ | ✅ **需要，且必须拆**：**8 个 Feature 家族中 1 个（A3）超 5000 行**，25 个交付 Feature 中 **1 个（F7）超单 Feature 3000 行上限**，最终拆成 **32 个 Phase**，**1 Phase = 1 次 speckit 闭环** | 依据 §4.1 的 LangGraph 真实 LOC 逐模块标定 + §4.3 的 Phase 切分表。**每个 Phase 落在 500–2,000 行**（远低于 5000 硬上限，为 spec/plan/tasks 留上下文余量）。 |

### 0.1 关键数字速览

| 指标 | 数值 | 来源 |
|---|---|---|
| freegraph v1 预计总代码量 | **31,520 行**（实现 15,940 + 测试 15,580） | §4.4 |
| Phase 数（= speckit 闭环数） | **32** | §4.3 |
| 交付 Feature 数 | **25**（分属 8 个家族） | §3.2 |
| 平均 Phase 规模 | **985 行** | §4.4 |
| 最大 Phase 规模 | **1,480 行**（F7P1，调度内核） | §4.4 |
| 测试 / 实现 比 | **0.98** | §4.4 |
| 最长依赖链（关键路径） | **15 个 Phase** | §4.5 |
| 契约层（C1–C26）条目数 | **26** | Q8 §3.4 |
| `target.py` 必须同名同签名的 API | **7 项** | Q3 §3.4 / 宪法原则 III |
| 必须有独立回归测试的契约 | **2 条**（C4 稀疏状态、C8 条件边 fresh 读） | Q8 §5.3–5.4 |

---

## 1. 前置：三条不可协商的约束（决定了后面所有答案）

在回答三个问题前，先固定三条约束。**它们不是偏好，是硬约束**——任何架构/模块方案违反其中一条就出局。

### 约束 A：依赖树必须干净（宪法原则 I / II）

`langchain-core 1.6.3` 的 `Requires-Dist` 含 **`langsmith<1.0.0,>=0.3.45`（硬依赖，非 extras）**
[来源: Q3 §3.1.2]。因此：

> **"依赖树无 `langsmith`" ⟺ "依赖树无 `langchain-core`" ⟺ "依赖树无 `langchain`" ⟺ "依赖树无 `langgraph`"**

这四条是**同一条红线**，不是四条。推论：

- **freegraph 内核不得依赖 `langchain-core`**，不得依赖任何 `langgraph*` 包（哪怕只用其中几个文件）。
  也不能"复制粘贴 `langgraph` 的源码进 freegraph"——那会让 freegraph 与 `langgraph` 的版本演进永久纠缠，
  且 `langgraph` 虽 MIT，但**复制会引入 `langchain_core` 的 API 形状**（如 `RunnableConfig`），
  直接违反"内核只依赖鸭子类型"（宪法原则 II）。
- **唯一建议的必装运行时依赖是 `typing-extensions`** [来源: Q3 §3.6]。
  `pydantic`（可选 extra）、`ormsgpack`（可选 extra）、`opentelemetry-*`（可选 extra）可作为**可选 extra**，
  但**不得进入基础安装**。
- 内核**不读任何环境变量**（宪法「配置层黑名单」）。

**对架构的直接含义**：架构**必须**能表达"哪些依赖是可选的"。
→ 结论：采用 **extras 分组**（`[otel]` / `[pydantic]` / `[png]` / `[checkpoint]`），
且**契约层必须用 `typing.Protocol` 而非具体基类**，否则可选依赖会通过类型标注渗进基础安装。

### 约束 B：状态语义必须与 LangGraph 行为等价（宪法原则 II / III）

Q8 从源码逆向出 8 条核心契约 [来源: Q8 §3.2]。其中两条**最容易实现错且会静默破坏 `target.py`**：

| 契约 | 语义 | 源码证据 | 后果 |
|---|---|---|---|
| **C4 稀疏状态** | 节点入参是**普通 `dict`**，且**只含有值的 key**。空 channel 的 key **不得**出现 | `pregel/_io.py:38-53`（`read_channels(skip_empty=True)`）；实测 `NODE_INPUT_KEYS: ['messages']` | 若出现 `llm_calls: None`，`target.py:81` 的 `state.get('llm_calls', 0)` 返回 `None` → `None + 1` 抛 `TypeError` |
| **C8 条件边读 fresh 状态** | 路由函数必须能看到「当前值 + 本节点本次写入」 | `pregel/_algo.py:188-224`（`local_read(fresh=True)`）；`graph/state.py:1598-1619` | 若读到旧 `messages`，`should_continue` 判断错误 → tool 循环失效或死循环 |

**对架构的直接含义**：架构**必须**把"读状态"这件事收敛到**唯一一个函数**，
使 C4/C8 只有一个可测点。否则状态语义会散落在 N 个地方，等价性无法保证。
→ 结论：**状态读取必须走单一 `read_channels` / `local_read` 抽象**，并在契约层冻结。

### 约束 C：`target.py` 必须"只换包名、不改脚本"跑通（宪法原则 III）

Q3 逐项裁定 18 个 API 元素：**7 项必须同名同签名**，11 项行为等价或原样承载，**0 项要求触及 LangSmith**
[来源: Q3 §3.4 / `00` §7]。

**对架构的直接含义**：架构**必须**让 `from freegraph.graph import StateGraph, START, END`
成为一个**稳定的、不随内部重构漂移的入口**。
→ 结论：**契约层冻结公开 API 名称与签名**，内部实现可任意重构。
这与"分层架构"天然吻合：公开面 = 契约层，实现 = 内核层。

### 1.1 三条约束如何收敛成一个结论

| 约束 | 逼出来的架构要求 |
|---|---|
| A 依赖树干净 | 分层 + `Protocol` 契约 + extras 隔离可选依赖 |
| B 状态语义等价 | 状态读写收敛到单一抽象点，可测 |
| C `target.py` 原样可跑 | 公开 API 冻结在契约层，内部可重构 |

**三条约束的交集只有一个解形态：分层架构 + 契约层。**
这不是"最佳实践偏好"，是**约束推导出的唯一可行形态**。

---

## 2. 问题一：是否要设计架构？初步架构是什么？

### 2.1 结论

> ✅ **要设计架构。**
> 但架构的**粒度必须严格受限**：只设计 **"分层 + 契约 + 依赖方向"** 这一层，
> **不设计**微服务、事件驱动、插件市场、CQRS、六边形架构等。

### 2.2 为什么必须设计（三个理由，缺一不可）

**理由 1：约束 A、B、C 只有在架构层才能被强制执行。**

如果只写代码不写架构：
- "依赖树干净"会退化成"大家记得别 import langchain"——靠自觉，必然失守；
- "状态语义等价"会退化成"每个节点自己读 state"——C4/C8 无处安放；
- "`target.py` 原样可跑"会退化成"改脚本适配"——验收标准松动。

宪法质量门禁第 2、3 项要求这两条**以可自动执行的断言落地**
[来源: `.specify/memory/constitution.md:416-418`]。**架构就是这些断言的载体。**

**理由 2：Q8 的实证直接给出了架构的"接缝数量"。**

LangGraph 对 `langchain_core` 的 135 处引用，按符号统计**只集中在 4 类接缝**：

| `langchain_core` 符号 | 引用数 | 性质 | freegraph 处置 |
|---|---|---|---|
| `runnables.RunnableConfig` | 26 | 配置传递 | 🔴 自有 `RunConfig` |
| `runnables.Runnable` / `RunnableBindingBase` | 8 | 协议 | 🔴 自有 `Node` / `CompiledGraph` 协议 |
| `runnables.graph.Graph` / `Node` / `Edge` | 5 | 图结构类型 | 🔴 自有 `Graph` 类型 |
| `callbacks.*` / `tracers.*` | 12 | 可观测挂钩 | 🟢 换成 OTel |
| `messages.*` / `tools.*` / `language_models.*` | 15 | LangChain 特有 | 🟢 鸭子类型，不需要 |

[来源: Q8 §3.3.1 实测 grep 统计]

> **这 4 个接缝就是架构的"接缝定义"**。替换掉它们，`langgraph/graph` + `langgraph/pregel` + `langgraph/channels`
> 三棵子树就可移植到零 `langchain_core` 依赖的状态（Q8 §3.3.2）。
> **接缝的位置由架构决定，接口的形态由契约层决定。**

**理由 3：freechain 要基于 freegraph 重建 LangChain 层，接口边界必须先冻结。**

官方分层是 Runtime / Framework / Harness 三层 [来源: Q4 §3.4]，freegraph 对标 Runtime。
跨仓库协作若没有一份**可被另一项目独立消费的契约**，freechain 会被迫读 freegraph 的内部实现，
两项目立刻纠缠。**架构中的"契约层"就是 freechain 的设计输入**（Q8 §5.1 建议 1）。

### 2.3 初步架构：6 层单向依赖 + 1 个契约层

```
┌──────────────────────────────────────────────────────────────────────────┐
│ L6  应用层 / Studio UI（可选子包，v1 不做）                                │
│     本地 Web UI：图视图 + trace 时间线 + 状态快照/回放                      │
│     ——  唯一允许引入前端技术栈的层；内核不受影响                          │
└───────────────────────────────▲──────────────────────────────────────────┘
                                │ 只读 Contract 数据（JSON / dict）
┌───────────────────────────────┴──────────────────────────────────────────┐
│ L5  可观测层 observability                                                │
│     OTel span 生产 · TraceSink 协议 · current_span() · 本地 Trace 存储      │
│     ——  默认关闭；只被显式注入时生效（原则 I：环境变量存在也不改变行为）    │
└───────────────────────────────▲──────────────────────────────────────────┘
                                │ TraceSink 协议（回调）
┌───────────────────────────────┴──────────────────────────────────────────┐
│ L4  持久化层 persistence                                                   │
│     Checkpointer 协议 · MemorySaver · SqliteSaver · Store 协议(v2)          │
└───────────────────────────────▲──────────────────────────────────────────┘
                                │ Checkpointer 协议
┌───────────────────────────────┴──────────────────────────────────────────┐
│ L3  图定义层 graph                                                        │
│     StateGraph · CompiledGraph · 路由函数 · 图结构导出(get_graph)          │
└───────────────────────────────▲──────────────────────────────────────────┘
                                │ 纯数据结构（StateDict / ChannelSpec / TaskSpec）
┌───────────────────────────────┴──────────────────────────────────────────┐
│ L2  执行内核层 runtime（Pregel 语义）                                      │
│     Channel 抽象 · reducer 归约 · 任务准备/调度 · super-step 循环          │
│     节点执行 · Command / interrupt · Send                                  │
└───────────────────────────────▲──────────────────────────────────────────┘
                                │ 只有类型，无实现
┌───────────────────────────────┴──────────────────────────────────────────┐
│ L1  契约层 contracts  ⭐ 唯一被所有层依赖的模块（依赖图的根）              │
│     C1–C26 契约 · RunConfig · Graph/Node/Edge 结构 · Command/Interrupt      │
│     StateSnapshot · 异常体系 · 协议(Protocol)定义                          │
└──────────────────────────────────────────────────────────────────────────┘
         ↕  用户代码（鸭子类型：消息 / 模型 / 工具）——不 import 任何内部层
```

**依赖方向铁律（可由 CI 断言）**：

1. **只能向下依赖**。L5 可以 import L4，L4 可以 import L3……**反向 import 一律禁止**。
2. **L1 不 import 任何内部层**（L1 只依赖 stdlib + `typing-extensions`）。
   → 保证契约层可以被 freechain **单独**安装与消费。
3. **L2–L5 之间不横向依赖**。例如持久化层**不得** import 可观测层；
   两者的关联只经由 L1 的协议。
4. **L6 是唯一可以横向依赖 L5 的层**（Studio 要读 trace 数据），但**只读契约数据**，不反向写内核。

**为什么契约层是「依赖图的根」而不是「实现底座」**：契约层定义**所有层之间**的数据形状。
如果契约层位于架构底部并被内核依赖，那它就成了"内核的一部分"，
freechain 想复用契约就必须装上整个内核。**把契约层独立成可单独导入的模块**
（`freegraph/contracts/`），才能实现"freechain 只依赖契约，不依赖内核实现"。

### 2.4 架构的 4 条硬约束（写进 plan.md 的 "Constitution Check"）

| # | 约束 | 判定方式 |
|---|---|---|
| **ARCH-1** | 依赖方向单向；L1 不依赖内部层 | CI 静态检查 import 图（AST 扫描 `freegraph/**`） |
| **ARCH-2** | 契约层可独立安装：仅依赖 `typing-extensions` | `pip install freegraph-contracts` 后 `import freegraph.contracts` 无副作用 |
| **ARCH-3** | 跨层只经由 `Protocol` + 纯数据类；**禁止**跨层 import 具体实现类 | CI 静态检查：L2+ 的模块不得 import 另一层实现模块（白名单除外） |
| **ARCH-4** | 公开 API 面只经由 L1 导出；`freegraph.graph` 是 `target.py` 的稳定入口 | API 快照测试（对 L1 导出符号做签名快照） |

### 2.5 明确**不**设计的架构（避免过度设计）

| 不做 | 理由 |
|---|---|
| 微服务 / 进程间通信 | freegraph 是**库**，不是系统；进程边界会强制序列化，破坏"零出站 + 鸭子类型" |
| 事件驱动 / 消息总线 | 节点执行是**同步数据流**语义（`pregel/_algo.py` 的 super-step 模型已足够）；引入总线会让 C4/C8 的时序语义变得不可测 |
| 插件市场 / entry_points 动态发现 | 依赖树必须可静态断言（约束 A）；动态发现会让"依赖树干净"无法验证 |
| CQRS / 读写模型分离 | freegraph 的状态**本来就是**命令式归约（reducer），再套一层是重复抽象 |
| 六边形架构 / 端口适配器的完整仪式 | 只需 **4 个接缝**（Q8 实证），完整六边形是过度抽象 |
| 依赖注入框架（`dependency-injector` 等） | 会引入第三方运行时依赖，违反约束 A |
| 事件溯源（Event Sourcing） | checkpoint 已经是"快照 + pending writes"的两层模型（§3.3），不是 ES |

> **架构复杂度的判定标准**：每一层/每条规则都必须能追溯到 §1 的三条约束之一，
> 或追溯到一条**可自动检查的质量门禁**。追溯不到 → 删除。

---

## 3. 问题二：如何拆成 Feature 模块？模块间用什么协议交互？

### 3.1 拆解原则

> **Feature ≠ 技术分层。Feature = 一个可独立验收的垂直切片。**

技术分层（L1–L6）是**代码组织**；Feature 是**交付节奏**。两者的关系：

- 一个 Feature 可以跨多层（垂直切片），例如「状态模型」Feature 同时写 L1 的类型与 L2 的 channel；
- 一个 Feature 通常**不**跨越"必须先有下层才能做"的边界，但**可以**提前冻结下层的接口（先写协议 stub）。

**判定一个 Feature 是否合格的 4 条标准**（Speckit 的 spec 需要 user story，这 4 条是其工程化表述）：

1. **有明确的用户可见能力**（"用户能 X"），不是"我们实现了 Y 类"；
2. **可独立验收**：合并后能单独通过 7 项质量门禁中的至少第 1、2、3、4 项；
3. **有明确的契约增量**：落地 C1–C26 中的哪几条，或新增哪条内部协议；
4. **有明确的非目标**：本 Feature **不**做什么（防止范围蔓延）。

### 3.2 Feature 全景（8 家族 / 25 交付 Feature）

```
A1  契约与地基（Contracts & Foundation）         ← 所有其他 Feature 的前置
    F1 契约骨架 + C1–C26 类型          F2 公开 API 门面与签名冻结
    F3 项目脚手架 + CI 门禁（依赖树/许可证/零出站/socket guard）

A2  状态模型（State & Channels）                  ← 内核第一层
    F4 schema 解析 + reducer 归约器提取        F5 Channel 抽象与 LastValue/BinOp

A3  图定义与执行（Graph Definition & Execution）  ← 体量最大的家族
    F6 StateGraph 构建器               F7 compile + 调度 + invoke
    F8 路由语义（fresh 读）+ stream + 别名/context

A4  高级控制原语（Control Primitives）
    F9 Command（goto/update）          F10 interrupt + resume（HITL）
    F11 Send（动态 fan-out）            F12 并发执行 + 错误传播
    F13 静态中断点 + recursion_limit

A5  持久化与时间旅行（Persistence & Time-travel）
    F14 Checkpointer 协议 + MemorySaver          F15 SqliteSaver + get_state_history
    F16 update_state + 时间旅行回放               F17 Store 协议 + MemoryStore（v2 起）

A6  可观测性（Observability）
    F18 OTel span 生产（节点/工具/模型）          F19 TraceSink 协议 + current_span()
    F20 本地 Trace 存储（文件 + SQLite）          F21 OTLP 导出插件

A7  图结构导出与可视化（Graph Export & Drawing）
    F22 Graph 结构类型 + get_graph(xray=) + draw_mermaid（纯本地，零出站）
    F23 draw_mermaid_png（离线不阻断）            F26 本地 Studio UI（v2 起）

A8  交付与生态（Delivery & Ecosystem）
    F24 打包分发 + extras + 兼容矩阵 + 归属清单    F25 target.py 双跑验收 + 迁移说明 + 文档
```

> **计数**：A1 = 3、A2 = 2、A3 = 3、A4 = 5、A5 = 4、A6 = 4、A7 = 2（+F26 v2 预备）、A8 = 2 → **合计 25**（+1 v2 预备）。
> **命名规则**：域 = `A<n>`；Feature = `F<n>`（全局整数，按域连续分配）；Phase = `F<n>P<m>`（**在所属 Feature 内从 1 编号**）。**新增 Feature 追加到 F 末尾、新增 Phase 追加到所属 Feature 末尾，既有编号永不变更**——中途插入功能不需要重排任何编号。
> 其中 **F26**（Studio UI）列入 v2 预备，本轮不排 Phase（见 §4.4）。

### 3.3 Feature 依赖图（拓扑序 = 建议实施顺序）

```
        F1 ──► F2 ──► F3
         │       │
         │       ├──────────────┐
         ▼       ▼              │
        F4 ──► F5           │
         │       │              │
         │       ▼              │
         │   F6 ──► F7 ──► F8
         │       │              │
         │       │              ▼
         │       │           F9 ──► F10 ──► F11
         │       │              │                  │
         │       │              └──► F12 ──► F13
         │       ▼              │
         │   F22 ──► F22 ──► F23
         │                        │
         ▼                        │
     F18 ──► F19 ──► F20 ──► F21
                                 │
         ┌───────────────────────┤
         ▼                       ▼
     F14 ──► F15 ──► F16      F24 ──► F25
         └────────► F17 (v2)
```

**依赖说明**：

- **A1 → 一切**：契约层是根。没有 A1，其他 Feature 无处安放类型与协议。
- **A2 → A3**：没有 channel 与 reducer，无法定义节点入参与状态合并规则。
- **A3 → A4**：`Command` / `interrupt` / `Send` 是**执行期**原语，需要运行时先能跑。
- **F18 → F19 → F20**：先能产出 span，再定义 sink 协议，再落存储。
  注意 **F18 依赖 A3**（没有执行就没有节点可观测），但 **A6 不依赖 A5**（tracing 与 checkpoint 是正交的）。
- **A7 依赖 A3**：`get_graph()` 需要已编译的图；但 **F22/F23 依赖 A1**（返回类型在契约层）。
- **A5 依赖 A3 + A1**：checkpointer 在执行期被调用，其协议在 L1。
- **A8 依赖全部**。

> ⚠️ **注意 F23 的位置**：`draw_mermaid_png` 必须与 `target.py` 同批交付（原则 III），
> 因此 **F23 不能推迟到 v2**——它是 MVP 硬约束，不是可视化增强。
> 相应地，F7（invoke）完成后**立刻**做 F22→F23，**先让 `target.py` 跑通**，再补 A4/A5/A6。
> **这是本指南给出的关键排序建议：MVP 优先序 ≠ 拓扑序。**

### 3.4 MVP 优先序（与拓扑序的差异）

宪法原则 III 要求 `target.py` 原样跑通，这是**硬性验收契约**。
若严格按拓扑序做，F8 之后要等 A4/A5/A6 才轮到 A7，MVP 会被推迟到很后面。

**建议的交付节奏**：

| 里程碑 | 包含 Feature | 达成状态 |
|---|---|---|
| **M0 地基** | F1, F2, F3 | 契约冻结，CI 门禁生效 |
| **M1 运行时内核** | F4, F5, F7(调度), F9, F10, F11, F12, F13 | 状态模型、super-step、Command/HITL/Send/并发；**运行时可独立验收** |
| **M2 图定义与对外 API** | F6, F7, F8, F22, F23 | 构建器 + compile + invoke + 路由 + stream + 图导出；**`target.py` 跑通**（fake 模型） |
| **M3 可诊断** | F14, F15, F16, F17, F18, F19, F20 | checkpoint + trace + 时间旅行 |
| **M4 生态** | F21, F24, F25 | 打包、兼容矩阵、双跑验收、文档 |

### 3.5 模块间交互：4 类协议 + 3 种数据格式

这是问题二的第二半。**freegraph 的模块间交互刻意做到极简**——
因为 Q8 实证"一个图运行时从外界真正需要的只有 6 类东西"
[来源: Q8 §3.1]，且**通用协议可以直接采用，LangChain 特有部分全部外移到 freechain**。

#### 3.5.1 协议总览（4 类）

| # | 协议 | 签名（契约层冻结） | 定义方 | 消费方 | LangChain 特有? |
|---|---|---|---|---|---|
| **P1** | `Node` | `Callable[[StateDict], StateDict \| Command \| None]` | 契约层 | 执行内核 | 🟢 通用 |
| **P2** | `Checkpointer` | `get_tuple / list / put / put_writes / delete_thread / get_next_version` | 契约层 | 执行内核 | 🟡 半通用 |
| **P3** | `TraceSink` | `on_span_start / on_span_end / current_span` | 契约层 | 执行内核 | 🔴 替代 callbacks |
| **P4** | `Store` | `get / search / put / delete / list_namespaces / batch` | 契约层 | 执行内核 | 🟡 半通用 |

**另有一类"注入式依赖"协议**（不跨模块调用，而是由上层注入给内核）：

| # | 注入点 | 形态 | 用途 |
|---|---|---|---|
| **I1** | `RunConfig` | 契约层的 `TypedDict` | 替代 `RunnableConfig`（**不 import `langchain_core`**） |
| **I2** | `CompiledGraph` | 契约层的 `Protocol` | 替代 `Runnable`；`invoke` / `stream` / `get_graph` / `get_state` |
| **I3** | `Graph` / `Node` / `Edge` | 契约层的数据类 | 替代 `langchain_core.runnables.graph.Graph`（**唯一必须重写的类型**） |

> **⚠️ 关键约束**：`RunConfig` / `CompiledGraph` / `Graph` **必须**定义在契约层，
> **不得**从 `langchain_core` 导入。Q8 §5.2 明确：复用 `RunnableConfig` 会把 `langchain-core` 拖回来。

#### 3.5.2 数据格式总览（3 种）

| 格式 | 用途 | 定义 | 关键字段 |
|---|---|---|---|
| **D1 `StateDict`** | 节点入参 / 状态 | `dict[str, Any]`（**稀疏**，只含有值的 key） | C4 语义；**不得**用 Pydantic 对象或自定义 State 类 |
| **D2 `Command`** | 控制流 + 状态更新 | 契约层数据类 | `goto: str\|Sequence[str]\|None`、`update: dict\|None`、`resume: Any` |
| **D3 `StateSnapshot`** | 状态查询 / 时间旅行 | 契约层 `NamedTuple`（对齐 LangGraph `types.py:683`） | `values` / `next` / `config` / `metadata` / `created_at` / `tasks` / `interrupts` |

**跨层传递的三个额外约定**：

1. **状态永远是 `dict`，不是对象。** 节点收到的是普通 `dict`（实测 `NODE_INPUT_TYPE: dict`），
   用户传入的 LangChain 消息对象**原样流转，不做类型转换**（宪法原则 II / `target.py:97`）。
2. **节点返回"部分状态 dict"**，逐 key 应用归约器；无归约器的 key 覆盖。
   未知 key 触发 `InvalidUpdateError`（LangGraph 行为，Q8 §3.2.2）。
3. **`Command` 是唯一的"跳出返回 dict"通道。** 节点返回 `Command` 表示"更新状态 + 跳转"。

#### 3.5.3 交互协议全景图

```
        用户代码 / freechain
              │
              │ ① D1 StateDict（稀疏）in
              │ ② P1 Node（鸭子类型）调用
              ▼
   ┌──────────────────────────────────┐
   │  L2 执行内核                       │◄──③ P2 Checkpointer（快照 + pending writes）
   │  channel 抽象 · reducer           │◄──④ P3 TraceSink（span 回调）
   │  super-step 调度 · 节点执行        │
   └──────────────────────────────────┘
              │
              │ ⑤ D1 StateDict（完整状态）out
              │ ⑥ D3 StateSnapshot out（get_state）
              ▼
        用户代码 / freechain

   ┌──────────────────────────────────┐
   │  L4 图定义层                       │──►⑦ I3 Graph/Node/Edge ──► L5 可视化 / L6 Studio
   └──────────────────────────────────┘

   ┌──────────────────────────────────┐
   │  L5 可观测层                       │──►⑧ Trace JSONL / SQLite（本地）
   └──────────────────────────────────┘
```

**8 条交互路径的格式与协议对照**：

| # | 方向 | 载体 | 格式 | 协议 | 契约依据 |
|---|---|---|---|---|---|
| ① | 用户 → 内核 | 节点入参 | **D1 `StateDict`** | 普通 dict 调用 | C4 / C5 |
| ② | 用户 → 内核 | 节点函数 | **P1 `Node`** | 鸭子类型 callable | C5 |
| ③ | 内核 → 持久化 | 快照 / pending writes | `dict`（JSON 可序列化） | **P2 `Checkpointer`** | C19 |
| ④ | 内核 → 可观测 | span 事件 | 契约层 `Span` 数据类 | **P3 `TraceSink`** | C23 / C24 |
| ⑤ | 内核 → 用户 | 执行结果 | **D1 `StateDict`**（**完整状态**） | 返回值 | C11 |
| ⑥ | 内核 → 用户 | 状态快照 | **D3 `StateSnapshot`** | 返回值 | C19 |
| ⑦ | 图定义 → 可视化 | 图结构 | **I3 `Graph`** | 数据类 | C13 / C14 |
| ⑧ | 可观测 → 存储 | trace 记录 | JSONL 行 / SQLite 行 | 文件协议 | — |

#### 3.5.4 协议设计的 5 条纪律

| # | 纪律 | 依据 |
|---|---|---|
| **PD-1** | **协议用 `typing.Protocol` 定义，实现用数据类**。禁止接口继承链。 | 让 optional extra（pydantic / otel）不渗进基础安装（约束 A） |
| **PD-2** | **跨层只传纯数据**（dict / dataclass / NamedTuple）。**不传行为对象**。 | 使内核可被纯函数式测试，且未来可无痛序列化 |
| **PD-3** | **状态通道只有 dict**。不引入 Pydantic State、不引入自定义 State 基类。 | 宪法原则 II；`target.py` 用 `TypedDict` |
| **PD-4** | **可观测走回调（push），不走查询（pull）**。`TraceSink` 由上层注入。 | 原则 I：环境变量存在也不改变行为；不注入 = 零开销零外呼 |
| **PD-5** | **状态读取收敛为单一抽象点**（`read_channels` / `local_read`）。 | 约束 B：C4/C8 只有一个可测点 |

> **PD-5 的架构含义**：这是整个架构里**最重要的一条**。LangGraph 的 `local_read(fresh=True)`
> 在 `pregel/_algo.py:188-224`，其"复制所有 channel + 只应用本任务写入"的实现，
> 是 C8 语义的**唯一来源**。freegraph 必须把这个函数**单独抽出、单独命名、单独测试**，
> 而不是散落在调度逻辑里。

---

## 4. 问题三：Phase 拆解（≤5000 行 / speckit 闭环）

### 4.1 LOC 标定方法（不是拍脑袋）

**方法**：以本机 `langgraph 1.2.11` 的**真实源码行数**为标定基准。
freegraph 要实现的是 LangGraph 的**一个子集**，且**必须重写而非复制**。
因此每个机制的 freegraph 规模 ≈ LangGraph 对应文件的行数 × **折减系数**。

**折减系数取值依据**：

| 因素 | 影响 | 系数 |
|---|---|---|
| 只实现 v1 必需子集（去掉 async / retry / cache / functional API / 远程图 / delta / 子图） | 砍掉 40–60% | ×0.45 |
| ↳ *（2026-11-03 更新）* **async 已归 v2（未排 Phase）**，故 §4.1 的「去掉 async」假设仍成立；若后续把 async 提前纳入 v1，本行折减需重估（async 约 +900 行 / +2 个 Phase） | —— | —— |
| 去掉 `langchain_core` 类型胶水层（`RunnableConfig` / `Runnable` / `Graph` / callbacks），改用自有协议 | 砍掉 10–15% | ×0.85 |
| 去掉大量 deprecated 兼容分支、`Any` / `cast` 噪音、复杂泛型 | 砍掉 10% | ×0.90 |
| 注释密度：freegraph 需更密的契约注释（每个契约点注明 Q8 条号），抵消一部分精简 | +5% | ×1.05 |
| **净折减** | | **×0.36**（代码行）<br>**×0.55**（含注释行） |

**LangGraph 真实 LOC 基准**（`wc -l`，本机实测）：

| LangGraph 文件 | 行数 | freegraph 对应机制 | 预估代码行 |
|---|---|---|---|
| `pregel/_algo.py` | 1460 | 任务准备/应用、归约、fresh 读 | ~480 |
| `pregel/_loop.py` | 1988 | super-step 循环、checkpoint 编排、中断 | ~620 |
| `pregel/main.py` | 4364 | `invoke` / `stream` / `get_state` / `get_state_history` | ~700 |
| `pregel/_runner.py` | 941 | 节点执行、并发、错误处理 | ~330 |
| `pregel/_read.py` + `_io.py` + `_write.py` | 678 | 读/写通道、输入映射 | ~260 |
| `pregel/_checkpoint.py` | 331 | 快照创建/恢复 | ~140 |
| `graph/state.py` | 1978 | `StateGraph` 构建器 + `CompiledStateGraph` | ~640 |
| `graph/_branch.py` + `_node.py` | 328 | 路由求值、节点规格 | ~140 |
| `channels/*.py`（5 种） | 767 | Channel 抽象 + LastValue/BinOp/Ephemeral/Topic/Barrier | ~330 |
| `types.py`（子集） | 1024 | `Command`/`Send`/`Interrupt`/`StateSnapshot` | ~280 |
| `checkpoint/base` + `memory` | 1558 | Checkpointer 协议 + MemorySaver | ~420 |
| `checkpoint/sqlite` | 645 | SqliteSaver | ~260 |
| `store/base`（v2 子集） | 1322 | Store 协议 + MemoryStore | ~380 |
| `langchain_core/runnables/graph.py` + `graph_mermaid.py` | 1244 | Graph 类型 + mermaid 绘制 | ~520 |
| **小计（内核 L1–L4）** | | | **≈ 5,600** |
| **小计（+ 持久化/store）** | | | **≈ 6,660** |

**⚠️ 这个标定已经给出两个重要结论**：

> **结论 1**：**内核（L1–L4）本身约 5,600 行代码 —— 仅代码行就已超过 5000 行上限。**
> 即使不算测试，A1+A2+A3 也**必须**拆成多个 Phase。这不是保守估计，是算术结论。
>
> **结论 2**：按"只实现 v1 必需子集"的口径，全项目（含持久化、可观测、绘制、打包）
> 预计 **15,940 行实现 + 15,580 行测试 = 31,520 行**。
> → 若按 5000 行/闭环，理论下限是 **7 个闭环**；
> → 但每个闭环还要承载 spec + plan + tasks 的上下文占用，
> **实际应按 ~1000 行/Phase 规划 → 32 个 Phase**（§4.4）。

**测试代码量**：按业界经验，freegraph 这类内核项目的 `测试代码 ≈ 0.9–1.0 × 实现代码`。
本指南按 **测试/实现 = 0.98** 估算（内核语义敏感度高——C4/C8 这类"实现错但静默"的契约必须有测试兜底，
测试占比不能低于实现）。这与 §4.4 的实际求和结果（15,580 / 15,940 = 0.98）一致。

### 4.2 Phase 切分规则

| 规则 | 内容 |
|---|---|
| **PR-1** | **1 Phase = 1 次 speckit 闭环**（specify → plan → tasks → implement），对应 1 个分支 + 1 个 `specs/NNN-*` 目录 |
| **PR-2** | **单 Phase ≤ 5000 行**（实现 + 测试 + 该 Phase 新增的文档/示例） |
| **PR-3** | Phase 内**可包含多个 Feature** 的工作（若它们共同构成一个可验收切片）；反之一个 Feature 也可跨多个 Phase |
| **PR-4** | **Phase 必须能独立通过门禁**。跨 Phase 依赖只允许是"接口契约"依赖（协议已冻结），不允许是"实现未完成"依赖 |
| **PR-5** | 每个 Phase 结束时，**`target.py` 必须仍可运行**（回归不退化） |
| **PR-6** | Phase 边界优先落在**语义接缝**上（协议定义处），而非任意行号切割 |

### 4.3 Phase 切分表（32 个 Phase）

> **列含义**：
> - **实现/测试** = 预估代码行（含注释）
> - **合计** = 实现 + 测试
> - **依赖** = 前置 Phase
> - **交付物** = 该 Phase 结束时**可验证**的东西
>
> **本表是 §4.4 所有汇总数字的唯一来源**（逐行求和，可复算）。

#### M0 地基（4 Phase）

| Phase | 名称 | 实现 | 测试 | 合计 | 依赖 | 交付物 |
|---|---|---|---|---|---|---|
| **F1P1** | 契约层骨架：`contracts/` 包 + `StateDict`/`Command`/`StateSnapshot`/`RunConfig` 类型 + 异常体系 | 520 | 380 | **900** | — | `import freegraph.contracts` 可用；C1/C11/C16 类型冻结 |
| **F2P1** | 4 类协议（`Node`/`Checkpointer`/`TraceSink`/`Store`）+ `CompiledGraph`/`Graph`/`Node`/`Edge` 协议与数据类 | 480 | 340 | **820** | F1P1 | 协议齐全；freechain 可单独依赖契约层 |
| **F2P2** | 公开 API 门面 `freegraph/graph.py`：`StateGraph` / `START` / `END` 签名冻结 + API 快照测试 | 260 | 300 | **560** | F1P1,F2P1 | `from freegraph.graph import StateGraph, START, END` 可用；签名快照入库 |
| **F3P1** | 项目脚手架：`pyproject.toml` + extras 划分 + CI 门禁（依赖树断言 / 许可证白名单 / 零出站 socket guard / 导入图单向检查） | 620 | 480 | **1,100** | F1P1,F2P1 | 门禁生效：故意引入 `langchain` 依赖 → CI 必须失败 |

#### M1 运行时内核（9 Phase）

> **【2026-11-03 修订】Phase 顺序改为「按依赖层级开发：运行时层先行」**：图定义层 import 运行时层（`graph/state.py:73-75` → `from langgraph.pregel import Pregel`），运行时层不 import 图定义层 → 运行时是独立性最高的一层，应先开发。
> 收益：① 调度循环（F7P1）不再依赖 `compile()`，可用手写图规格直接验收；② C4 / C8 / super-step 等静默破坏型语义前置暴露；③ 构建器层成为薄适配器。
> 代价：关键路径由 13 个 Phase 增至 **15 个（45 天）**；全项目 96 天不变；固定脚本最小交付集 = **F6P1 + F7P2 + F7P3 + F8P1**，完成于**第 30 天**（不变）。
> **权威顺序以 `harness/proposals/立项书.md` §5.2 总表为准**（本表已同步重排）。

| Phase | 名称 | 实现 | 测试 | 合计 | 依赖 | 交付物 |
|---|---|---|---|---|---|---|
| **F4P1** | schema 解析：TypedDict/Annotated 解析 → `ChannelSpec`；归约器提取（`_is_field_binop` 等价，恰好 2 位置参数） | 480 | 460 | **940** | F2P2 | `Annotated[list, operator.add]` 被正确识别为二元归约器 |
| **F5P1** | Channel 抽象 + `LastValue`（覆盖语义）+ `BinaryOperatorAggregate`（归约语义）+ `EphemeralValue`（路由通道，每 super-step 清空） | 520 | 540 | **1,060** | F4P1 | 归约器 `operator(current, new)` 语义一致；无归约器 key 被覆盖 |
| **F5P2** | **稀疏状态读取**（C4 回归测试）：`read_channels(skip_empty=True)` + `local_read(fresh=True)` | 340 | 520 | **860** | F5P1 | **C4 独立回归测试通过**：`"llm_calls" not in node_input` 且 `.get("llm_calls", 0) == 0` |
| **F7P1** | 任务准备与执行循环（super-step）：`_triggers` 触发判定 + `prepare_next_tasks` + `apply_writes` + 版本号 + `versions_seen` | 780 | 700 | **1,480** | F5P1,F5P2 | 单 super-step 可执行；状态按归约器合并；**可脱离构建器、用手写图规格直接验收** |
| **F9P1** | `Command` 原语：`goto` / `update` + `Command` 输入映射 + `Command.PARENT` | 420 | 460 | **880** | F7P1 | `Command` 跳转 + 状态更新同时生效 |
| **F12P1** | 节点并发执行：同 super-step 多节点并行 + 错误传播 + `GraphInterrupt` 合并 | 520 | 560 | **1,080** | F7P1,F9P1 | 并行节点不串行化；首个异常正确抛出 |
| **F10P1** | `interrupt()` + `resume`：中断异常 + `__interrupt__` 结果键 + 从**节点起点**重跑语义 | 520 | 640 | **1,160** | F9P1 | HITL 中断/恢复闭环 |
| **F11P1** | `Send`：动态 fan-out / map-reduce（条件边返回 `Send` → 自定义入参调用目标节点） | 460 | 520 | **980** | F7P1 | map-reduce 模式可运行 |
| **F13P1** | `interrupt_before` / `interrupt_after` 静态中断点 + `recursion_limit` | 320 | 360 | **680** | F10P1 | 递归超限抛明确异常 |

#### M2 图定义与对外 API（8 Phase）

| Phase | 名称 | 实现 | 测试 | 合计 | 依赖 | 交付物 |
|---|---|---|---|---|---|---|
| **F6P1** | `StateGraph` 构建器：`add_node` / `add_edge` / `add_conditional_edges`（list+dict 双 `path_map`）/ `START`/`END` / 链式返回 | 700 | 620 | **1,320** | F4P1 | 构建器 API 与 LangGraph 同名同签名 |
| **F7P2** | `compile()` → `CompiledGraph`：节点挂载 + 路由通道 + `branch:to:<node>` 机制 | 640 | 560 | **1,200** | F6P1 | 图可编译；`compile()` 无参可调用 |
| **F7P3** | `invoke()`：返回**完整状态**（含所有 key）；节点返回值 → 通道写入；`InvalidUpdateError` | 460 | 520 | **980** | F7P1,F12P1 | `invoke` 返回 `{'messages': [...], 'llm_calls': N}` 完整状态 |
| **F8P1** | **条件边 fresh 读**（C8 回归测试）+ 路由求值（`path_map` list/dict 双形态）+ `END` 终止 | 480 | 620 | **1,100** | F5P2,F7P1 | **C8 独立回归测试通过**：路由函数看到本节点刚写入的值 |
| **F8P2** | `stream()`：`values` / `updates` / `custom` / `debug` / `tasks` 模式 + `StreamWriter` | 620 | 560 | **1,180** | F7P3 | 多模式流式输出 |
| **F22P1** | `get_graph(xray=)` + 自有 `Graph`/`Node`/`Edge` 类型 + `draw_mermaid()`（纯本地、零出站） | 620 | 520 | **1,140** | F7P2 | `draw_mermaid()` 离线必然成功、零出站 |
| **F23P1** | `draw_mermaid_png()`：**离线不阻断**（默认走本地渲染 / 明确异常可捕获）+ `target.py` 适配 | 520 | 560 | **1,080** | F22P1 | **PNG 路径离线不抛阻断性异常**（原则 III 硬约束） |
| **F8P3** | 节点重命名别名 + `context` 独立通道（不塞 `configurable`） | 280 | 300 | **580** | F7P3 | 契约 C21/C25 落地 |

#### M3 可诊断（8 Phase）

| Phase | 名称 | 实现 | 测试 | 合计 | 依赖 | 交付物 |
|---|---|---|---|---|---|---|
| **F18P1** | OTel span 生产：节点 / 工具 / 模型三级 span，属性对齐 `gen_ai.*` semconv | 620 | 520 | **1,140** | F7P3 | span 产生，属性名符合 OTel GenAI semconv |
| **F19P1** | `TraceSink` 协议接入 + `current_span()` 上下文传播 + 默认关闭（无注入 = 零开销零外呼） | 380 | 460 | **840** | F18P1 | 嵌套 span 父子关系正确；不注入 tracer 时零副作用 |
| **F20P1** | 本地 Trace 存储：JSONL 文件后端（零依赖）+ 写入 | 420 | 400 | **820** | F19P1 | trace 落盘，零出站 |
| **F20P2** | Trace 查询 API + SQLite 后端 + 按 `thread_id` / 时间 / 节点名检索 | 560 | 460 | **1,020** | F20P1 | 可按线程检索 trace |
| **F14P1** | Checkpointer 协议 + `MemorySaver`（`get_tuple`/`list`/`put`/`put_writes`）+ 版本号策略 | 560 | 640 | **1,200** | F7P3 | 快照 + pending writes 双层持久化 |
| **F15P1** | `SqliteSaver` + `get_state` / `get_state_history`（`StateSnapshot` 组装） | 620 | 620 | **1,240** | F14P1 | 历史快照可枚举（对齐 LangGraph `HISTORY: 6` 行为） |
| **F16P1** | `update_state` + 时间旅行回放（从任意 checkpoint 重跑 + fork 分支） | 480 | 560 | **1,040** | F15P1 | 可从历史 checkpoint 重放 |
| **F17P1** | `Store` 协议 + `MemoryStore`（v2 预备；`(namespace, key)` 读写 + 前缀搜索） | 460 | 460 | **920** | F14P1 | 长期记忆接口可用 |

#### M4 生态（3 Phase）

| Phase | 名称 | 实现 | 测试 | 合计 | 依赖 | 交付物 |
|---|---|---|---|---|---|---|
| **F21P1** | OTLP 导出插件（可选 extra）+ 文档化 OpenLIT / Langfuse / Phoenix 对接（**仅外部连接，绝不内嵌 Phoenix**） | 380 | 320 | **700** | F20P2 | 可选导出到任一 OTel 后端 |
| **F24P1** | 打包分发（extras 划分：基础仅 `typing-extensions`）+ API 兼容矩阵 + `THIRD_PARTY_NOTICES` | 520 | 380 | **900** | F23P1,F16P1 | 发行包就绪；兼容矩阵与归属清单齐备 |
| **F25P1** | `target.py` 双跑验收（fake 模型 CI + 真实模型人工）+ 迁移说明 + README/快速上手 | 380 | 240 | **620** | F24P1 | **MVP 完成**：`target.py` 双跑通过，零出站断言通过 |

### 4.4 Phase 规模汇总（对 5000 行上限的验证）

> 下表所有数字由 §4.3 的 32 行 Phase 表**逐行求和**得出（可复算）。

| 指标 | 数值 | 判定 |
|---|---|---|
| Phase 总数 | **32** | — |
| 实现代码合计 | **15,940 行** | — |
| 测试代码合计 | **15,580 行** | — |
| **总计** | **31,520 行** | 与 §4.1 标定（内核 5,600 + 持久化/store + 可观测 + 绘制 + 生态）一致 |
| 测试 / 实现 比 | **0.98** | 内核语义敏感度高，测试与实现近乎 1:1 |
| 最大 Phase | **F7P1 = 1,480 行** | ✅ 仅为 5000 上限的 **30%** |
| 平均 Phase | **985 行** | ✅ |
| 最小 Phase | **F2P2 = 560 行** | ✅ |
| **超 5000 行的 Phase** | **0 个** | ✅ |
| **超 5000 行的 Feature 家族** | **1 个**（A3 = 7,840 行） | → 拆为 F6/F7/F8 共 7 个 Phase |
| **超 5000 行的交付 Feature** | **0 个**（最大 F7 = 3,660 行） | ✅ 但 F7 需拆 3 个 Phase 以满足 PR-4（独立过门禁） |

**Feature 级体量判定表**（回答"每个模块体量是否超过 5000 行"）：

> **口径**：
> - **家族体量** = 该家族下所有交付 Feature 的行数合计（这是"一个模块有多大"的自然问法）；
> - **Feature 体量** = 该 Feature 覆盖的 Phase 行数合计；
> - 行数均为**实现 + 测试**，来自 §4.3 逐行求和。

| 家族 | 家族体量 | > 5000？ | 拆为 Feature |
|---|---|---|---|
| **A1** 契约与地基 | 3,380 | ❌ | F1, F2, F3 |
| **A2** 状态模型 | 2,860 | ❌ | F4, F5 |
| **A3** 图定义与执行 | **7,840** | ✅ **超限** | **F6, F7, F8**（3 个） |
| **A4** 高级控制原语 | 4,780 | ❌ | F9 … F13（5 个） |
| **A5** 持久化与时间旅行 | 4,400 | ❌ | F14 … F17（4 个） |
| **A6** 可观测性 | 4,520 | ❌ | F18 … F21（4 个） |
| **A7** 图结构导出 | 2,220 | ❌ | F22, F22, F23（+ F26 v2） |
| **A8** 交付与生态 | 1,520 | ❌ | F24, F25 |

| 交付 Feature | 体量 | 占 5000 上限 | > 5000？ | 拆为 Phase |
|---|---|---|---|---|
| F1 契约骨架 + C1–C26 类型 | 900 | 18% | ❌ | F1P1 |
| F2 公开 API 门面与签名冻结 | 1,380 | 28% | ❌ | F2P1, F2P2 |
| F3 项目脚手架 + CI 门禁 | 1,100 | 22% | ❌ | F3P1 |
| F4 schema 解析 + reducer 提取 | 940 | 19% | ❌ | F4P1 |
| F5 Channel 抽象 + LastValue/BinOp | 1,920 | 38% | ❌ | F5P1, F5P2 |
| F6 StateGraph 构建器 | 1,320 | 26% | ❌ | F6P1 |
| **F7 compile + 调度 + invoke** | **3,660** | **73%** | ❌ | **F7P1, F7P2, F7P3** |
| F8 路由语义 + stream + 别名/context | 2,860 | 57% | ❌ | F8P1, F8P2, F8P3 |
| F9 Command | 880 | 18% | ❌ | F9P1 |
| F10 interrupt + resume | 1,160 | 23% | ❌ | F10P1 |
| F11 Send | 980 | 20% | ❌ | F11P1 |
| F12 并发执行 + 错误传播 | 1,080 | 22% | ❌ | F12P1 |
| F13 静态中断点 + recursion_limit | 680 | 14% | ❌ | F13P1 |
| F14 Checkpointer 协议 + MemorySaver | 1,200 | 24% | ❌ | F14P1 |
| F15 SqliteSaver + get_state_history | 1,240 | 25% | ❌ | F15P1 |
| F16 update_state + 时间旅行 | 1,040 | 21% | ❌ | F16P1 |
| F17 Store 协议 + MemoryStore | 920 | 18% | ❌ | F17P1 |
| F18 OTel span 生产 | 1,140 | 23% | ❌ | F18P1 |
| F19 TraceSink + current_span | 840 | 17% | ❌ | F19P1 |
| F20 本地 Trace 存储 | 1,840 | 37% | ❌ | F20P1, F20P2 |
| F21 OTLP 导出 | 700 | 14% | ❌ | F21P1 |
| F22 Graph 类型 + get_graph + draw_mermaid | 1,140 | 23% | ❌ | F22P1 |
| F23 draw_mermaid_png | 1,080 | 22% | ❌ | F23P1 |
| F24 打包 + 兼容矩阵 + 归属清单 | 900 | 18% | ❌ | F24P1 |
| F25 target.py 双跑 + 迁移说明 + 文档 | 620 | 12% | ❌ | F25P1 |
| F26 本地 Studio UI（v2 预备） | ~2,600（估） | 52% | ❌ | v2，暂不排期 |

> **判定说明（三层）**：
> 1. **家族层**：只有 **A3（7,840 行）超过 5000**，必须拆为 3 个交付 Feature。这是"一个模块太大"的直接证据。
> 2. **Feature 层**：拆分后 **25 个交付 Feature 全部低于 5000 行**（最大 F7 = 3,660，占上限 73%）。
> 3. **Phase 层**：F7 虽未超 5000，仍拆为 3 个 Phase——因为 **PR-4 要求每个 Phase 独立通过门禁**：
>    F9P1（compile + 图结构）可独立验收，F12P1（调度循环）可独立验收，F10P1（`invoke` 完整状态）可独立验收；
>    三者合一则中途失败时无法定位是哪一层出错。**这是"Feature 可交付"与"Phase 可验收"的区分。**

### 4.5 Phase ↔ Feature ↔ Milestone 映射总表

| Milestone | Phase | Feature | 达成状态 |
|---|---|---|---|
| **M0 地基** | F1P1–F3P1 | F1, F2, F3 | 契约冻结，CI 门禁生效 |
| **M1 运行时内核** | F4P1–F13P1 | F4, F5, F7(调度), F9, F10, F11, F12, F13 | 状态模型、super-step、Command/HITL/Send/并发；**运行时可独立验收** |
| **M2 图定义与对外 API** | F6P1–F8P3 | F6, F7, F8, F22, F23 | 构建器 + compile + invoke + 路由 + stream + 图导出；**`target.py` 跑通**（fake 模型） |
| **M3 可诊断** | F18P1–F17P1 | F18, F19, F20, F14, F15, F16, F17 | checkpoint + trace + 时间旅行 |
| **M4 生态** | F21P1–F25P1 | F21, F24, F25 | 打包、兼容矩阵、双跑验收、文档 |

**关键路径（最长依赖链，15 个 Phase）**：

```
F1P1 → F2P1 → F2P2 → F4P1 → F5P1 → F5P2 → F7P1 → F9P1 → F12P1 → F7P3 → F18P1 → F19P1 → F20P1 → F20P2 → F21P1
```

这条链**不经过** `target.py` 验收路径——说明**可观测链（A6）可与 MVP 验收链并行推进**，
不必串行等待。两条链的交汇点在 F24P1/F25P1。

**`target.py` 验收路径（最小集 F6P1 + F7P2 + F7P3 + F8P1，第 10 个 Phase 达成，即第 30 天）**：

```
F1P1 → F2P1 → F2P2 → F4P1 → F5P1 → F5P2 → F7P1 → F9P1 → F12P1 → F7P3 → (F6P1 → F7P2) → F8P1
```

**F6P1–F8P1（构建器 → compile → invoke → 路由）完成时 `target.py` 即可跑通**（fake 模型）——这是 M2 的验收点，位于第 30 天。

> **并行可行性**：按依赖深度分层，同层 Phase 之间无依赖，可并行推进。
> 最深依赖链 15 层（到 F25P1），**关键路径 15 个 Phase，其余 17 个可并行**。
> 若单人开发，建议按 M0→M1→M2→M3→M4 串行；若多人开发，F10P1/F11P1、F20P1/F14P1、F17P1/F21P1 等可并行。

### 4.6 门禁在每个 Phase 的落地

宪法 7 项质量门禁 [来源: `.specify/memory/constitution.md:408-423`] 的 Phase 级落地：

| 门禁 | 落地 Phase | 说明 |
|---|---|---|
| 1 规格门禁 | 每个 Phase | `specs/NNN-*/` 三件套 + `harness/proposals/` 提案 + `harness/features/<feature>/` 人工记录 |
| 2 **依赖门禁**（红线） | **F3P1** 建立，后续每 Phase 持续 | CI 递归展开 `importlib.metadata.requires()`；许可证白名单；`LANGSMITH_*` 扫描；导入图单向检查 |
| 3 **契约门禁** | **F5P2**（C4）、**F8P1**（C8）建立，后续持续 | 两条独立回归测试；`target.py` 冒烟（F8P1 起为完整验收） |
| 4 自动门禁 | F3P1 建立 | CI 全绿 + fake 模型跑通验收基线 + socket guard 零出站断言 |
| 5 人工门禁 | 每个 Phase | `harness/features/<feature>/manual-verification.md`（环境/步骤/输出/结论/遗留） |
| 6 证据门禁 | 每个 Phase | 新增结论附来源标记；术语用官方对照表 |
| 7 文档合规门禁 | F2P2（兼容矩阵）、F24P1（归属清单 + 终版） | API 兼容矩阵随公开 API 变更同步更新 |

### 4.7 Phase 的 Speckit 产物路径（对齐仓库既有约定）

| 产物 | 路径 | 说明 |
|---|---|---|
| Feature 提案 | `harness/proposals/NNN-<slug>.md` | 调研结论 → 设计提案（原则 VI） |
| Spec | `specs/NNN-<slug>/spec.md` | Speckit 生成 |
| Plan | `specs/NNN-<slug>/plan.md` + `research.md` + `data-model.md` + `contracts/` + `quickstart.md` | Speckit 生成 |
| Tasks | `specs/NNN-<slug>/tasks.md` | Speckit 生成，可逐条勾选 |
| 人工验证记录 | `harness/features/<slug>/manual-verification.md` | 原则 V 硬要求 |
| 分支 | `NNN-<slug>` | `create-new-feature.sh` 生成，编号 3 位补零 |

> **注意**：Speckit 的 `specs/` 编号按 `create-new-feature.sh` 的 `get_highest_from_specs` 自动递增
> [来源: `.specify/scripts/bash/create-new-feature.sh:129-143`]。因此本指南的 F1P1–F25P1 是
> **逻辑 Phase 编号**，与 Speckit 的实际分支号可能不一致（中间会插入 clarify/analyze 等产生的目录）。
> **落地时以 Speckit 实际编号为准**，并在 short-name 中带上 Phase 序号便于追溯：
> 例：`--short-name "p01-contracts-core"`。

---

## 5. 跨 Phase 的持续约束（每个 Phase 都要守）

| # | 约束 | 检查方式 |
|---|---|---|
| 1 | 依赖树无 `langsmith`/`langchain*`/`langgraph*`；许可证 ∈ {MIT, Apache-2.0, BSD, PSF} | CI（依赖门禁） |
| 2 | 代码不读 `LANGSMITH_*` / `LANGCHAIN_*` / `LANGGRAPH_CLOUD_LICENSE_KEY` | CI 静态扫描 |
| 3 | 零出站（除用户显式启用的 OTLP exporter） | socket guard 夹具（阻断非 localhost `socket.connect`，断言拦截列表为空） |
| 4 | 导入图单向；契约层零内部依赖 | CI AST 扫描 |
| 5 | C4 / C8 回归测试常驻 | CI |
| 6 | `target.py` 不被修改 | CI diff 检查 |
| 7 | 公共 API 变更须同步更新兼容矩阵 | CI 检查 `COMPAT.md` 与 API 快照的一致性 |
| 8 | 第三方代码入 `THIRD_PARTY_NOTICES` | 评审门禁 |

---

## 6. 与既有调研/宪法的对齐说明

| 本指南的结论 | 对应依据 | 是否与既有文档冲突 |
|---|---|---|
| 6 层 + 契约层架构 | Q8 §3.3.1（4 个接缝）、Q3 §5.2（必须重写 `Graph`）、宪法原则 II | ❌ 不冲突（细化） |
| 契约层独立可安装 | Q8 §5.1 建议 1（把 C1–C26 转成 `freegraph/protocols.py` 的 `Protocol`） | ❌ 不冲突（细化到"可单独安装"） |
| `RunConfig` / `CompiledGraph` / `Graph` 自有 | Q8 §5.2 建议 2（5 个必须自有类型）、§5.7（`current_span()` 列为 v1 必需） | ❌ 不冲突 |
| 4 类协议（P1–P4） | Q8 §3.4 的 C1–C26（C19 checkpointer / C23 tracer / C24 current_span / C20 store） | ❌ 不冲突（C24 被提升为必需） |
| 3 种数据格式（D1–D3） | Q8 §3.4 C4/C5/C6/C11/C16 | ❌ 不冲突 |
| `draw_mermaid_png` 离线不阻断 | 宪法原则 III 硬约束、Q3 §3.5 风险 1、Q3 §5 建议 3 | ❌ 不冲突 |
| 契约层零依赖 | 宪法「包层白名单」（`typing-extensions` 唯一必装） | ❌ 不冲突 |
| 32 个 Phase | 5000 行上限（`architecture.md` 任务书）+ §4.1 LOC 标定 + §4.4 逐行求和 | ❌ 不冲突 |
| v2 内容（Studio UI / Store / Postgres）标为 v2 | 宪法原则 VII 三类"不做"清单、Q6 §3.3 路线 B | ❌ 不冲突 |

**唯一需要发起者确认的新增判断**：本指南把 **F17 Store** 与 **F26 Studio UI** 标为 v2，
依据是宪法原则 VII 的"范围红线"与 Q6 §3.3 的路线 B 达成度
（Studio 三件套在 v1 只需"图视图 + trace 时间线 + 状态快照/回放入口"，
完整交互式 IDE 属 v2）。**若发起者希望 v1 就交付完整 Studio UI，需把 F26 提前并追加 2 个 Phase。**

---

## 7. 立即可执行的第一步（回答"我不知道如何跨出第一步"）

不需要更多调研。以下 3 件事今天就能做：

### 第 1 步：把本指南转成提案（30 分钟）

```bash
# 在 harness/proposals/ 下创建提案，把本指南的 §2/§3/§4 作为设计输入
# 提案必须回答：架构分层、协议清单、Phase 清单、门禁落地
```

依据宪法原则 VI：调研产物先落 `harness/reports/`，结论再转入 `harness/proposals/`。

### 第 2 步：跑通 F1P1（契约层骨架）——第一次 speckit 闭环

```bash
# 1) 创建特性（short-name 带 Phase 序号，便于追溯）
/speckit.specify 冻结 freegraph 契约层：StateDict/Command/StateSnapshot/RunConfig 类型、异常体系、contracts 包骨架

# 2) 生成计划（需要在 plan.md 里填 §2.3 的分层与 §3.5 的协议）
/speckit.plan

# 3) 生成任务
/speckit.tasks

# 4) 实现
/speckit.implement
```

**F1P1 的验收判据（可自动判定）**：
- `import freegraph.contracts` 成功，且 `pip show freegraph` 的依赖只有 `typing-extensions`；
- `StateDict` / `Command` / `StateSnapshot` / `RunConfig` 四个类型存在且有类型注解；
- 契约层不 import 任何 `freegraph` 内部模块（CI 断言）。

### 第 3 步：把 §4.3 的 Phase 表落成机器可读的清单

建议在 `harness/proposals/` 下维护一张 `phases.md`（或 YAML），字段：
`phase_id / short_name / milestone / feature / depends_on / est_impl / est_test / acceptance`。
**后续每个 Phase 的 `/speckit.plan` 都从这张表取上下文**，避免每次重新推理依赖关系。

---

## 8. 待发起者拍板的 5 个问题

| # | 问题 | 本指南的默认建议 | 影响 |
|---|---|---|---|
| **Q1** | 契约层是否**物理拆成独立发行包**（`freegraph-contracts`），还是同包内的子模块 `freegraph/contracts/`？ | **同包子模块**（v1）。理由：拆包会引入双包版本同步与安装摩擦，收益（freechain 单独装契约）在 freechain 开工前不急。契约层**代码上**保持零内部依赖，将来要拆随时可拆。 | 影响 F1P1/F2P1 的 `pyproject.toml` 布局 |
| **Q2** | `StateSnapshot` 是否**完全对齐** LangGraph 的 `types.py:683` 字段集？ | **对齐**（`values`/`next`/`config`/`metadata`/`created_at`/`tasks`/`interrupts`）。`config` 用 freegraph 自有 `RunConfig` 而非 `RunnableConfig`。 | 影响 F2P1、F15P1 |
| **Q3** | v1 是否**必须包含 async**（`ainvoke`/`astream`）？ | **已答（2026-11-03）：默认 v2（未排 Phase）**。初判为「v1 不做」，理由是 LangGraph 的 async 为 `SyncPregelLoop` 的镜像副本、语义等价但代码量翻倍，且 `target.py` 不需要 async；**该判断已修订**——LangGraph 已实现 async，**能力对等是跟进要求**，故归入 v2 范围。v1 不排期的理由：需同步/异步两套调度与测试，且 v1 无 async 依赖方。**若 freechain 需要 async 能力，应在 freegraph 提供 async 友好的注入点（如 `Checkpointer` 的异步方法可延后），而非在 v1 内核同步实现全套 async。** | 若提前纳入 v1：约 900–1,500 行 + 2 个 Phase ≈ 6 人日 / 12,000 元；且**契约层需补 async 条目**（Q8 C1–C26 目前无 async） |
| **Q4** | `Store`（长期记忆）与 **Studio UI** 是否确实推到 v2？ | **是**（见 §6 末尾）。 | 影响 M3/M4 范围 |
| **Q5** | 是否接受"先做运行时层（M1）→ 再做图定义层（M2，`draw_mermaid_png` 与固定脚本在此就位）→ 再补可观测（M3）"的排序？ | **接受**。理由：运行时层独立性最高（先做可独立验收），且 `draw_mermaid_png` 属 MVP 硬约束，须与固定脚本同在 M2 就位。 | 影响整体排期 |

---

## 9. 自检清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 问题 1 有明确结论（要/不要 + 为什么） | ✅ | §2.1 结论「要，但只做分层 + 契约」+ §2.2 三个理由 + §2.5 明确不做的清单 |
| 问题 1 给出初步架构 | ✅ | §2.3 六层图 + §2.4 四条硬约束 + §3.5 四类协议三族数据格式 |
| 问题 2 有明确结论（要/不要 + 为什么） | ✅ | §3.1 四条判定标准 + §3.2 8 家族 25 交付 Feature |
| 问题 2 给出 Feature 拆解 | ✅ | §3.2 全景 + §3.3 依赖图（拓扑序）+ §3.4 MVP 优先序 |
| 问题 2 给出模块间数据格式与协议 | ✅ | §3.5：4 类协议（P1–P4）+ 3 种格式（D1–D3）+ 8 条交互路径对照表 + PD-1..PD-5 纪律 |
| 问题 3 **家族级**体量判定（模块是否超 5000 行） | ✅ | §4.4 上表：8 家族逐条判定，**A3 = 7,840 超限**，其余均 < 5000 |
| 问题 3 **Feature 级**体量判定 | ✅ | §4.4 下表：25 个交付 Feature 逐条判定，最大 F7 = 3,660（73%），0 个超限 |
| 问题 3 超限部分拆为多个 Phase | ✅ | §4.3 **32 个 Phase** 切分表 + §4.5 映射总表 + §4.4 三层判定说明 |
| Phase 与 speckit 闭环一一对应 | ✅ | 规则 PR-1；§4.7 产物路径 |
| 每个 Phase ≤ 5000 行 | ✅ | §4.4：最大 1,480 行（30% 上限），0 个超限 |
| LOC 估算有依据、非拍脑袋 | ✅ | §4.1 以本机 `langgraph 1.2.11` 实测 LOC 为基准 + 折减系数推导；§4.4 全部数字由 §4.3 逐行求和得出（可复算） |
| 内部数字自洽 | ✅ | §4.3 相加 = 31,520；家族合计 = Feature 合计 = Phase 合计，三者相等 |
| 事实性结论带来源标记 | ✅ | LangGraph 源码 `文件:行号`（本机实测）；报告 `Q# §章节`；宪法 `文件:行号` |
| 术语用官方对照表，未混用自造词 | ✅ | 沿用 Q4 §3.4 权威表（Runtime/Framework/Harness）；"三大基础能力"标注为自造表述 |
| 与宪法七项门禁对齐 | ✅ | §4.6 门禁 × Phase 落地表 |
| 给出"第一步"的行动指引 | ✅ | §7 三步立即可执行 |
| 未修改 `harness/docs`、`harness/demo/target.py`、任何源码 | ✅ | 本次仅新增 `harness/prompts/guide.md` |
