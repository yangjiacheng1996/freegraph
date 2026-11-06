# freegraph 开发指南：架构、模块与 feature 拆解

> ⚠️ **状态提示（2026-11-05）**：本文件是 **2026-11-03 的设计输入稿**——它的 §4.3 feature 表与
> §4.4 totals 已被 `harness/proposals/立项书.md` **取代**（**执行口径一律以立项书为准**）。
> 2026-11-05 的决议 **D5：砍掉 `Store`（B17 / B17F1）** → 本文件中涉及 B17、32 feature /
> 25 功能块 / 31,520 行 / 96 人日 / 192,000 元的数字**均已过期**，正确口径为
> **24 功能块 / 31 feature / 30,600 行 / 93 人日 / 186,000 元 / 94 天**（立项书 §4.4 / §7.2）。
> 其余结论（架构分层、4 类协议、feature 切分规则 PR-1…PR-6）仍然有效。

> **本文件回答三个问题**：
> 1. 是否要设计架构？初步架构是什么？
> 2. 是否要拆成多个 功能块 模块？如何拆？模块之间用什么数据格式与协议交互？
> 3. 每个模块体量是否超过 5000 行？如何拆成 feature 使 feature 与 speckit 闭环一一对应？
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
| **2** | 是否拆成多个功能块（模块）？ | ✅ **要，拆成 8 个**领域** / 25 个**功能块**，模块间用 **4 类协议 + 3 种数据格式**交互 | 依赖关系与协议见 §3。**关键约束**：功能块 必须是**可独立验收的垂直切片**（能单独通过门禁），而不是按技术分层切。契约层（领域 A1）是所有其他 功能块 的前置依赖。 |
| **3** | feature 拆解？ | ✅ **需要，且必须拆**：**8 个**领域**中 1 个（A3）超 5000 行**，25 个**功能块**中 **1 个（B7）超单功能块 3000 行上限**，最终拆成 **32 个 feature**，**1 feature = 1 次 speckit 闭环** | 依据 §4.1 的 LangGraph 真实 LOC 逐模块标定 + §4.3 的 feature 切分表。**每个 feature 落在 500–2,000 行**（远低于 5000 硬上限，为 spec/plan/tasks 留上下文余量）。 |

### 0.1 关键数字速览

| 指标 | 数值 | 来源 |
|---|---|---|
| freegraph v1 预计总代码量 | **31,520 行**（实现 15,940 + 测试 15,580） | §4.4 |
| feature 数（= speckit 闭环数 = 最小开发单位） | **32** | §4.3 |
| 功能块数（= 交付单元） | **25**（分属 8 个**领域**） | §3.2 |
| 平均 feature 规模 | **985 行** | §4.4 |
| 最大 feature 规模 | **1,480 行**（B7F1，调度内核） | §4.4 |
| 测试 / 实现 比 | **0.98** | §4.4 |
| 最长依赖链（关键路径） | **15 个 feature** | §4.5 |
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
- **必装运行时依赖 = 无**（基础安装零第三方依赖）[来源: Q3 §3.6 + 宪法修订记录 v1.2.0 · 2026-11-05]。
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
2. **L1 不 import 任何内部层**（L1 **只依赖 stdlib**）。
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
| **ARCH-2** | 契约层可独立安装：**零**第三方依赖 | `pip install freegraph` 后 `import freegraph.contracts` 无副作用 |
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

## 3. 问题二：如何拆成功能块？模块间用什么协议交互？

### 3.1 拆解原则

> **feature ≠ 技术分层。feature = 一个可独立验收的垂直切片**（= speckit 的一次闭环）。
> **功能块 = 一组共同交付的 feature**（交付单元，`B<n>`）。

技术分层（L1–L6）是**代码组织**；功能块 / feature 是**交付节奏**。三者的关系：

- 一个 feature 可以跨多层（垂直切片），例如「状态模型」里的某个 feature 同时写 L1 的类型与 L2 的 channel；
- 一个 feature 通常**不**跨越"必须先有下层才能做"的边界，但**可以**提前冻结下层的接口（先写协议 stub）；
- 一个功能块 是 1–3 个 feature 的分组（按主题聚合，如「契约与地基」下的 B1/B2/B3）。

**判定一个 feature 是否合格的 4 条标准**（Speckit 的 spec 需要 user story，这 4 条是其工程化表述）：

1. **有明确的用户可见能力**（"用户能 X"），不是"我们实现了 Y 类"；
2. **可独立验收**：合并后能单独通过 7 项质量门禁中的至少第 1、2、3、4 项；
3. **有明确的契约增量**：落地 C1–C26 中的哪几条，或新增哪条内部协议；
4. **有明确的非目标**：本 功能块 **不**做什么（防止范围蔓延）。

### 3.2 功能块 全景（8 领域 / 25 交付 功能块）

```
A1  契约与地基（Contracts & Foundation）         ← 所有其他 功能块 的前置
    B1 契约骨架 + C1–C26 类型          B2 公开 API 门面与签名冻结
    B3 项目脚手架 + CI 门禁（依赖树/许可证/零出站/socket guard）

A2  状态模型（State & Channels）                  ← 内核第一层
    B4 schema 解析 + reducer 归约器提取        B5 Channel 抽象与 LastValue/BinOp

A3  图定义与执行（Graph Definition & Execution）  ← 体量最大的领域
    B6 StateGraph 构建器               B7 compile + 调度 + invoke
    B8 路由语义（fresh 读）+ stream + 别名/context

A4  高级控制原语（Control Primitives）
    B9 Command（goto/update）          B10 interrupt + resume（HITL）
    B11 Send（动态 fan-out）            B12 并发执行 + 错误传播
    B13 静态中断点 + recursion_limit

A5  持久化与时间旅行（Persistence & Time-travel）
    B14 Checkpointer 协议 + MemorySaver          B15 SqliteSaver + get_state_history
    B16 update_state + 时间旅行回放               B17 Store 协议 + MemoryStore（v2 起）

A6  可观测性（Observability）
    B18 OTel span 生产（节点/工具/模型）          B19 TraceSink 协议 + current_span()
    B20 本地 Trace 存储（文件 + SQLite）          B21 OTLP 导出插件

A7  图结构导出与可视化（Graph Export & Drawing）
    B22 Graph 结构类型 + get_graph(xray=) + draw_mermaid（纯本地，零出站）
    B23 draw_mermaid_png（离线不阻断）            B26 本地 Studio UI（v2 起）

A8  交付与生态（Delivery & Ecosystem）
    B24 打包分发 + extras + 兼容矩阵 + 归属清单    B25 target.py 双跑验收 + 迁移说明 + 文档
```

> **计数**：A1 = 3、A2 = 2、A3 = 3、A4 = 5、A5 = 4、A6 = 4、A7 = 2（+B26 v2 预备）、A8 = 2 → **合计 25**（+1 v2 预备）。
> **命名规则**：领域 = `A<n>`；功能块 = `B<n>`（全局整数，按领域连续分配）；feature = `B<n>F<m>`（**在所属 功能块 内从 1 编号**）。**新增 功能块 追加到 F 末尾、新增 feature 追加到所属 功能块 末尾，既有编号永不变更**——中途插入功能不需要重排任何编号。
> 其中 **B26**（Studio UI）列入 v2 预备，本轮不排 feature（见 §4.4）。

### 3.3 功能块 依赖图（拓扑序 = 建议实施顺序）

```
        B1 ──► B2 ──► B3
         │       │
         │       ├──────────────┐
         ▼       ▼              │
        B4 ──► B5           │
         │       │              │
         │       ▼              │
         │   B6 ──► B7 ──► B8
         │       │              │
         │       │              ▼
         │       │           B9 ──► B10 ──► B11
         │       │              │                  │
         │       │              └──► B12 ──► B13
         │       ▼              │
         │   B22 ──► B22 ──► B23
         │                        │
         ▼                        │
     B18 ──► B19 ──► B20 ──► B21
                                 │
         ┌───────────────────────┤
         ▼                       ▼
     B14 ──► B15 ──► B16      B24 ──► B25
         └────────► B17 (v2)
```

**依赖说明**：

- **A1 → 一切**：契约层是根。没有 A1，其他 功能块 无处安放类型与协议。
- **A2 → A3**：没有 channel 与 reducer，无法定义节点入参与状态合并规则。
- **A3 → A4**：`Command` / `interrupt` / `Send` 是**执行期**原语，需要运行时先能跑。
- **B18 → B19 → B20**：先能产出 span，再定义 sink 协议，再落存储。
  注意 **B18 依赖 A3**（没有执行就没有节点可观测），但 **A6 不依赖 A5**（tracing 与 checkpoint 是正交的）。
- **A7 依赖 A3**：`get_graph()` 需要已编译的图；但 **B22/B23 依赖 A1**（返回类型在契约层）。
- **A5 依赖 A3 + A1**：checkpointer 在执行期被调用，其协议在 L1。
- **A8 依赖全部**。

> ⚠️ **注意 B23 的位置**：`draw_mermaid_png` 必须与 `target.py` 同批交付（原则 III），
> 因此 **B23 不能推迟到 v2**——它是 MVP 硬约束，不是可视化增强。
> 相应地，B7（invoke）完成后**立刻**做 B22→B23，**先让 `target.py` 跑通**，再补 A4/A5/A6。
> **这是本指南给出的关键排序建议：MVP 优先序 ≠ 拓扑序。**

### 3.4 MVP 优先序（与拓扑序的差异）

宪法原则 III 要求 `target.py` 原样跑通，这是**硬性验收契约**。
若严格按拓扑序做，B8 之后要等 A4/A5/A6 才轮到 A7，MVP 会被推迟到很后面。

**建议的交付节奏**：

| 里程碑 | 包含 功能块 | 达成状态 |
|---|---|---|
| **M0 地基** | B1, B2, B3 | 契约冻结，CI 门禁生效 |
| **M1 运行时内核** | B4, B5, B7(调度), B9, B10, B11, B12, B13 | 状态模型、super-step、Command/HITL/Send/并发；**运行时可独立验收** |
| **M2 图定义与对外 API** | B6, B7, B8, B22, B23 | 构建器 + compile + invoke + 路由 + stream + 图导出；**`target.py` 跑通**（fake 模型） |
| **M3 可诊断** | B14, B15, B16, B17, B18, B19, B20 | checkpoint + trace + 时间旅行 |
| **M4 生态** | B21, B24, B25 | 打包、兼容矩阵、双跑验收、文档 |

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

## 4. 问题三：feature 拆解（≤5000 行 / speckit 闭环）

### 4.1 LOC 标定方法（不是拍脑袋）

**方法**：以本机 `langgraph 1.2.11` 的**真实源码行数**为标定基准。
freegraph 要实现的是 LangGraph 的**一个子集**，且**必须重写而非复制**。
因此每个机制的 freegraph 规模 ≈ LangGraph 对应文件的行数 × **折减系数**。

**折减系数取值依据**：

| 因素 | 影响 | 系数 |
|---|---|---|
| 只实现 v1 必需子集（去掉 async / retry / cache / functional API / 远程图 / delta / 子图） | 砍掉 40–60% | ×0.45 |
| ↳ *（2026-11-03 更新）* **async 已归 v2（未排 feature）**，故 §4.1 的「去掉 async」假设仍成立；若后续把 async 提前纳入 v1，本行折减需重估（async 约 +900 行 / +2 个 feature） | —— | —— |
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
> 即使不算测试，A1+A2+A3 也**必须**拆成多个 feature。这不是保守估计，是算术结论。
>
> **结论 2**：按"只实现 v1 必需子集"的口径，全项目（含持久化、可观测、绘制、打包）
> 预计 **15,940 行实现 + 15,580 行测试 = 31,520 行**。
> → 若按 5000 行/闭环，理论下限是 **7 个闭环**；
> → 但每个闭环还要承载 spec + plan + tasks 的上下文占用，
> **实际应按 ~1000 行/feature 规划 → 32 个 feature**（§4.4）。

**测试代码量**：按业界经验，freegraph 这类内核项目的 `测试代码 ≈ 0.9–1.0 × 实现代码`。
本指南按 **测试/实现 = 0.98** 估算（内核语义敏感度高——C4/C8 这类"实现错但静默"的契约必须有测试兜底，
测试占比不能低于实现）。这与 §4.4 的实际求和结果（15,580 / 15,940 = 0.98）一致。

### 4.2 feature 切分规则

| 规则 | 内容 |
|---|---|
| **PR-1** | **1 feature = 1 次 speckit 闭环**（specify → plan → tasks → implement），对应 1 个分支 + 1 个 `specs/NNN-*` 目录 |
| **PR-2** | **单 feature ≤ 5000 行**（实现 + 测试 + 该 feature 新增的文档/示例） |
| **PR-3** | feature 内**可包含多个 功能块** 的工作（若它们共同构成一个可验收切片）；反之一个 功能块 也可跨多个 feature |
| **PR-4** | **feature 必须能独立通过门禁**。跨 feature 依赖只允许是"接口契约"依赖（协议已冻结），不允许是"实现未完成"依赖 |
| **PR-5** | 每个 feature 结束时，**`target.py` 必须仍可运行**（回归不退化） |
| **PR-6** | feature 边界优先落在**语义接缝**上（协议定义处），而非任意行号切割 |

### 4.3 feature 切分表（32 个 feature）

> **列含义**：
> - **实现/测试** = 预估代码行（含注释）
> - **合计** = 实现 + 测试
> - **依赖** = 前置 feature
> - **交付物** = 该 feature 结束时**可验证**的东西
>
> **本表是 §4.4 所有汇总数字的唯一来源**（逐行求和，可复算）。

#### M0 地基（4 feature）

| feature | 名称 | 实现 | 测试 | 合计 | 依赖 | 交付物 |
|---|---|---|---|---|---|---|
| **B1F1** | 契约层骨架：`contracts/` 包 + `StateDict`/`Command`/`StateSnapshot`/`RunConfig` 类型 + 异常体系 | 520 | 380 | **900** | — | `import freegraph.contracts` 可用；C1/C11/C16 类型冻结 |
| **B2F1** | 4 类协议（`Node`/`Checkpointer`/`TraceSink`/`Store`）+ `CompiledGraph`/`Graph`/`Node`/`Edge` 协议与数据类 | 480 | 340 | **820** | B1F1 | 协议齐全；freechain 可单独依赖契约层 |
| **B2F2** | 公开 API 门面 `freegraph/graph.py`：`StateGraph` / `START` / `END` 签名冻结 + API 快照测试 | 260 | 300 | **560** | B1F1,B2F1 | `from freegraph.graph import StateGraph, START, END` 可用；签名快照入库 |
| **B3F1** | 项目脚手架：`pyproject.toml` + extras 划分 + CI 门禁（依赖树断言 / 许可证白名单 / 零出站 socket guard / 导入图单向检查） | 620 | 480 | **1,100** | B1F1,B2F1 | 门禁生效：故意引入 `langchain` 依赖 → CI 必须失败 |

#### M1 运行时内核（9 feature）

> **【2026-11-03 修订】feature 顺序改为「按依赖层级开发：运行时层先行」**：图定义层 import 运行时层（`graph/state.py:73-75` → `from langgraph.pregel import Pregel`），运行时层不 import 图定义层 → 运行时是独立性最高的一层，应先开发。
> 收益：① 调度循环（B7F1）不再依赖 `compile()`，可用手写图规格直接验收；② C4 / C8 / super-step 等静默破坏型语义前置暴露；③ 构建器层成为薄适配器。
> 代价：关键路径由 13 个 feature 增至 **15 个（45 天）**；全项目 96 天不变；固定脚本最小交付集 = **B6F1 + B7F2 + B7F3 + B8F1**，完成于**第 30 天**（不变）。
> **权威顺序以 `harness/proposals/立项书.md` §5.2 总表为准**（本表已同步重排）。

| feature | 名称 | 实现 | 测试 | 合计 | 依赖 | 交付物 |
|---|---|---|---|---|---|---|
| **B4F1** | schema 解析：TypedDict/Annotated 解析 → `ChannelSpec`；归约器提取（`_is_field_binop` 等价，恰好 2 位置参数） | 480 | 460 | **940** | B2F2 | `Annotated[list, operator.add]` 被正确识别为二元归约器 |
| **B5F1** | Channel 抽象 + `LastValue`（覆盖语义）+ `BinaryOperatorAggregate`（归约语义）+ `EphemeralValue`（路由通道，每 super-step 清空） | 520 | 540 | **1,060** | B4F1 | 归约器 `operator(current, new)` 语义一致；无归约器 key 被覆盖 |
| **B5F2** | **稀疏状态读取**（C4 回归测试）：`read_channels(skip_empty=True)` + `local_read(fresh=True)` | 340 | 520 | **860** | B5F1 | **C4 独立回归测试通过**：`"llm_calls" not in node_input` 且 `.get("llm_calls", 0) == 0` |
| **B7F1** | 任务准备与执行循环（super-step）：`_triggers` 触发判定 + `prepare_next_tasks` + `apply_writes` + 版本号 + `versions_seen` | 780 | 700 | **1,480** | B5F1,B5F2 | 单 super-step 可执行；状态按归约器合并；**可脱离构建器、用手写图规格直接验收** |
| **B9F1** | `Command` 原语：`goto` / `update` + `Command` 输入映射 + `Command.PARENT` | 420 | 460 | **880** | B7F1 | `Command` 跳转 + 状态更新同时生效 |
| **B12F1** | 节点并发执行：同 super-step 多节点并行 + 错误传播 + `GraphInterrupt` 合并 | 520 | 560 | **1,080** | B7F1,B9F1 | 并行节点不串行化；首个异常正确抛出 |
| **B10F1** | `interrupt()` + `resume`：中断异常 + `__interrupt__` 结果键 + 从**节点起点**重跑语义 | 520 | 640 | **1,160** | B9F1 | HITL 中断/恢复闭环 |
| **B11F1** | `Send`：动态 fan-out / map-reduce（条件边返回 `Send` → 自定义入参调用目标节点） | 460 | 520 | **980** | B7F1 | map-reduce 模式可运行 |
| **B13F1** | `interrupt_before` / `interrupt_after` 静态中断点 + `recursion_limit` | 320 | 360 | **680** | B10F1 | 递归超限抛明确异常 |

#### M2 图定义与对外 API（8 feature）

| feature | 名称 | 实现 | 测试 | 合计 | 依赖 | 交付物 |
|---|---|---|---|---|---|---|
| **B6F1** | `StateGraph` 构建器：`add_node` / `add_edge` / `add_conditional_edges`（list+dict 双 `path_map`）/ `START`/`END` / 链式返回 | 700 | 620 | **1,320** | B4F1 | 构建器 API 与 LangGraph 同名同签名 |
| **B7F2** | `compile()` → `CompiledGraph`：节点挂载 + 路由通道 + `branch:to:<node>` 机制 | 640 | 560 | **1,200** | B6F1 | 图可编译；`compile()` 无参可调用 |
| **B7F3** | `invoke()`：返回**完整状态**（含所有 key）；节点返回值 → 通道写入；`InvalidUpdateError` | 460 | 520 | **980** | B7F1,B12F1 | `invoke` 返回 `{'messages': [...], 'llm_calls': N}` 完整状态 |
| **B8F1** | **条件边 fresh 读**（C8 回归测试）+ 路由求值（`path_map` list/dict 双形态）+ `END` 终止 | 480 | 620 | **1,100** | B5F2,B7F1 | **C8 独立回归测试通过**：路由函数看到本节点刚写入的值 |
| **B8F2** | `stream()`：`values` / `updates` / `custom` / `debug` / `tasks` 模式 + `StreamWriter` | 620 | 560 | **1,180** | B7F3 | 多模式流式输出 |
| **B22F1** | `get_graph(xray=)` + 自有 `Graph`/`Node`/`Edge` 类型 + `draw_mermaid()`（纯本地、零出站） | 620 | 520 | **1,140** | B7F2 | `draw_mermaid()` 离线必然成功、零出站 |
| **B23F1** | `draw_mermaid_png()`：**离线不阻断**（默认走本地渲染 / 明确异常可捕获）+ `target.py` 适配 | 520 | 560 | **1,080** | B22F1 | **PNG 路径离线不抛阻断性异常**（原则 III 硬约束） |
| **B8F3** | 节点重命名别名 + `context` 独立通道（不塞 `configurable`） | 280 | 300 | **580** | B7F3 | 契约 C21/C25 落地 |

#### M3 可诊断（8 feature）

| feature | 名称 | 实现 | 测试 | 合计 | 依赖 | 交付物 |
|---|---|---|---|---|---|---|
| **B18F1** | OTel span 生产：节点 / 工具 / 模型三级 span，属性对齐 `gen_ai.*` semconv | 620 | 520 | **1,140** | B7F3 | span 产生，属性名符合 OTel GenAI semconv |
| **B19F1** | `TraceSink` 协议接入 + `current_span()` 上下文传播 + 默认关闭（无注入 = 零开销零外呼） | 380 | 460 | **840** | B18F1 | 嵌套 span 父子关系正确；不注入 tracer 时零副作用 |
| **B20F1** | 本地 Trace 存储：JSONL 文件后端（零依赖）+ 写入 | 420 | 400 | **820** | B19F1 | trace 落盘，零出站 |
| **B20F2** | Trace 查询 API + SQLite 后端 + 按 `thread_id` / 时间 / 节点名检索 | 560 | 460 | **1,020** | B20F1 | 可按线程检索 trace |
| **B14F1** | Checkpointer 协议 + `MemorySaver`（`get_tuple`/`list`/`put`/`put_writes`）+ 版本号策略 | 560 | 640 | **1,200** | B7F3 | 快照 + pending writes 双层持久化 |
| **B15F1** | `SqliteSaver` + `get_state` / `get_state_history`（`StateSnapshot` 组装） | 620 | 620 | **1,240** | B14F1 | 历史快照可枚举（对齐 LangGraph `HISTORY: 6` 行为） |
| **B16F1** | `update_state` + 时间旅行回放（从任意 checkpoint 重跑 + fork 分支） | 480 | 560 | **1,040** | B15F1 | 可从历史 checkpoint 重放 |
| **B17F1** | `Store` 协议 + `MemoryStore`（v2 预备；`(namespace, key)` 读写 + 前缀搜索） | 460 | 460 | **920** | B14F1 | 长期记忆接口可用 |

#### M4 生态（3 feature）

| feature | 名称 | 实现 | 测试 | 合计 | 依赖 | 交付物 |
|---|---|---|---|---|---|---|
| **B21F1** | OTLP 导出插件（可选 extra）+ 文档化 OpenLIT / Langfuse / Phoenix 对接（**仅外部连接，绝不内嵌 Phoenix**） | 380 | 320 | **700** | B20F2 | 可选导出到任一 OTel 后端 |
| **B24F1** | 打包分发（extras 划分：基础**零**依赖）+ API 兼容矩阵 + `THIRD_PARTY_NOTICES` | 520 | 380 | **900** | B23F1,B16F1 | 发行包就绪；兼容矩阵与归属清单齐备 |
| **B25F1** | `target.py` 双跑验收（fake 模型 CI + 真实模型人工）+ 迁移说明 + README/快速上手 | 380 | 240 | **620** | B24F1 | **MVP 完成**：`target.py` 双跑通过，零出站断言通过 |

### 4.4 feature 规模汇总（对 5000 行上限的验证）

> 下表所有数字由 §4.3 的 32 行 feature 表**逐行求和**得出（可复算）。

| 指标 | 数值 | 判定 |
|---|---|---|
| feature 总数 | **32** | — |
| 实现代码合计 | **15,940 行** | — |
| 测试代码合计 | **15,580 行** | — |
| **总计** | **31,520 行** | 与 §4.1 标定（内核 5,600 + 持久化/store + 可观测 + 绘制 + 生态）一致 |
| 测试 / 实现 比 | **0.98** | 内核语义敏感度高，测试与实现近乎 1:1 |
| 最大 feature | **B7F1 = 1,480 行** | ✅ 仅为 5000 上限的 **30%** |
| 平均 feature | **985 行** | ✅ |
| 最小 feature | **B2F2 = 560 行** | ✅ |
| **超 5000 行的 feature** | **0 个** | ✅ |
| **超 5000 行的领域** | **1 个**（A3 = 7,840 行） | → 拆为 B6/B7/B8 共 7 个 feature |
| **超 5000 行的交付 功能块** | **0 个**（最大 B7 = 3,660 行） | ✅ 但 B7 需拆 3 个 feature 以满足 PR-4（独立过门禁） |

**功能块 级体量判定表**（回答"每个模块体量是否超过 5000 行"）：

> **口径**：
> - **领域体量** = 该领域下所有交付 功能块 的行数合计（这是"一个模块有多大"的自然问法）；
> - **功能块 体量** = 该 功能块 覆盖的 feature 行数合计；
> - 行数均为**实现 + 测试**，来自 §4.3 逐行求和。

| 领域 | 领域体量 | > 5000？ | 拆为 功能块 |
|---|---|---|---|
| **A1** 契约与地基 | 3,380 | ❌ | B1, B2, B3 |
| **A2** 状态模型 | 2,860 | ❌ | B4, B5 |
| **A3** 图定义与执行 | **7,840** | ✅ **超限** | **B6, B7, B8**（3 个） |
| **A4** 高级控制原语 | 4,780 | ❌ | B9 … B13（5 个） |
| **A5** 持久化与时间旅行 | 4,400 | ❌ | B14 … B17（4 个） |
| **A6** 可观测性 | 4,520 | ❌ | B18 … B21（4 个） |
| **A7** 图结构导出 | 2,220 | ❌ | B22, B22, B23（+ B26 v2） |
| **A8** 交付与生态 | 1,520 | ❌ | B24, B25 |

| 交付 功能块 | 体量 | 占 5000 上限 | > 5000？ | 拆为 feature |
|---|---|---|---|---|
| B1 契约骨架 + C1–C26 类型 | 900 | 18% | ❌ | B1F1 |
| B2 公开 API 门面与签名冻结 | 1,380 | 28% | ❌ | B2F1, B2F2 |
| B3 项目脚手架 + CI 门禁 | 1,100 | 22% | ❌ | B3F1 |
| B4 schema 解析 + reducer 提取 | 940 | 19% | ❌ | B4F1 |
| B5 Channel 抽象 + LastValue/BinOp | 1,920 | 38% | ❌ | B5F1, B5F2 |
| B6 StateGraph 构建器 | 1,320 | 26% | ❌ | B6F1 |
| **B7 compile + 调度 + invoke** | **3,660** | **73%** | ❌ | **B7F1, B7F2, B7F3** |
| B8 路由语义 + stream + 别名/context | 2,860 | 57% | ❌ | B8F1, B8F2, B8F3 |
| B9 Command | 880 | 18% | ❌ | B9F1 |
| B10 interrupt + resume | 1,160 | 23% | ❌ | B10F1 |
| B11 Send | 980 | 20% | ❌ | B11F1 |
| B12 并发执行 + 错误传播 | 1,080 | 22% | ❌ | B12F1 |
| B13 静态中断点 + recursion_limit | 680 | 14% | ❌ | B13F1 |
| B14 Checkpointer 协议 + MemorySaver | 1,200 | 24% | ❌ | B14F1 |
| B15 SqliteSaver + get_state_history | 1,240 | 25% | ❌ | B15F1 |
| B16 update_state + 时间旅行 | 1,040 | 21% | ❌ | B16F1 |
| B17 Store 协议 + MemoryStore | 920 | 18% | ❌ | B17F1 |
| B18 OTel span 生产 | 1,140 | 23% | ❌ | B18F1 |
| B19 TraceSink + current_span | 840 | 17% | ❌ | B19F1 |
| B20 本地 Trace 存储 | 1,840 | 37% | ❌ | B20F1, B20F2 |
| B21 OTLP 导出 | 700 | 14% | ❌ | B21F1 |
| B22 Graph 类型 + get_graph + draw_mermaid | 1,140 | 23% | ❌ | B22F1 |
| B23 draw_mermaid_png | 1,080 | 22% | ❌ | B23F1 |
| B24 打包 + 兼容矩阵 + 归属清单 | 900 | 18% | ❌ | B24F1 |
| B25 target.py 双跑 + 迁移说明 + 文档 | 620 | 12% | ❌ | B25F1 |
| B26 本地 Studio UI（v2 预备） | ~2,600（估） | 52% | ❌ | v2，暂不排期 |

> **判定说明（三层）**：
> 1. **领域层**：只有 **A3（7,840 行）超过 5000**，必须拆为 3 个交付 功能块。这是"一个模块太大"的直接证据。
> 2. **功能块 层**：拆分后 **25 个交付 功能块 全部低于 5000 行**（最大 B7 = 3,660，占上限 73%）。
> 3. **feature 层**：B7 虽未超 5000，仍拆为 3 个 feature——因为 **PR-4 要求每个 feature 独立通过门禁**：
>    B9F1（compile + 图结构）可独立验收，B12F1（调度循环）可独立验收，B10F1（`invoke` 完整状态）可独立验收；
>    三者合一则中途失败时无法定位是哪一层出错。**这是"功能块 可交付"与"feature 可验收"的区分。**

### 4.5 feature ↔ 功能块 ↔ Milestone 映射总表

| Milestone | feature | 功能块 | 达成状态 |
|---|---|---|---|
| **M0 地基** | B1F1–B3F1 | B1, B2, B3 | 契约冻结，CI 门禁生效 |
| **M1 运行时内核** | B4F1–B13F1 | B4, B5, B7(调度), B9, B10, B11, B12, B13 | 状态模型、super-step、Command/HITL/Send/并发；**运行时可独立验收** |
| **M2 图定义与对外 API** | B6F1–B8F3 | B6, B7, B8, B22, B23 | 构建器 + compile + invoke + 路由 + stream + 图导出；**`target.py` 跑通**（fake 模型） |
| **M3 可诊断** | B18F1–B17F1 | B18, B19, B20, B14, B15, B16, B17 | checkpoint + trace + 时间旅行 |
| **M4 生态** | B21F1–B25F1 | B21, B24, B25 | 打包、兼容矩阵、双跑验收、文档 |

**关键路径（最长依赖链，15 个 feature）**：

```
B1F1 → B2F1 → B2F2 → B4F1 → B5F1 → B5F2 → B7F1 → B9F1 → B12F1 → B7F3 → B18F1 → B19F1 → B20F1 → B20F2 → B21F1
```

这条链**不经过** `target.py` 验收路径——说明**可观测链（A6）可与 MVP 验收链并行推进**，
不必串行等待。两条链的交汇点在 B24F1/B25F1。

**`target.py` 验收路径（最小集 B6F1 + B7F2 + B7F3 + B8F1，第 10 个 feature 达成，即第 30 天）**：

```
B1F1 → B2F1 → B2F2 → B4F1 → B5F1 → B5F2 → B7F1 → B9F1 → B12F1 → B7F3 → (B6F1 → B7F2) → B8F1
```

**B6F1–B8F1（构建器 → compile → invoke → 路由）完成时 `target.py` 即可跑通**（fake 模型）——这是 M2 的验收点，位于第 30 天。

> **并行可行性**：按依赖深度分层，同层 feature 之间无依赖，可并行推进。
> 最深依赖链 15 层（到 B25F1），**关键路径 15 个 feature，其余 17 个可并行**。
> 若单人开发，建议按 M0→M1→M2→M3→M4 串行；若多人开发，B10F1/B11F1、B20F1/B14F1、B17F1/B21F1 等可并行。

### 4.6 门禁在每个 feature 的落地

宪法 7 项质量门禁 [来源: `.specify/memory/constitution.md:408-423`] 的 feature 级落地：

| 门禁 | 落地 feature | 说明 |
|---|---|---|
| 1 规格门禁 | 每个 feature | `specs/NNN-*/` 三件套 + `harness/proposals/` 提案 + `harness/features/<feature>/` 人工记录 |
| 2 **依赖门禁**（红线） | **B3F1** 建立，后续每 feature 持续 | CI 递归展开 `importlib.metadata.requires()`；许可证白名单；`LANGSMITH_*` 扫描；导入图单向检查 |
| 3 **契约门禁** | **B5F2**（C4）、**B8F1**（C8）建立，后续持续 | 两条独立回归测试；`target.py` 冒烟（B8F1 起为完整验收） |
| 4 自动门禁 | B3F1 建立 | CI 全绿 + fake 模型跑通验收基线 + socket guard 零出站断言 |
| 5 人工门禁 | 每个 feature | `harness/verification/<feature>/manual-verification.md`（环境/步骤/输出/结论/遗留） |
| 6 证据门禁 | 每个 feature | 新增结论附来源标记；术语用官方对照表 |
| 7 文档合规门禁 | B2F2（兼容矩阵）、B24F1（归属清单 + 终版） | API 兼容矩阵随公开 API 变更同步更新 |

### 4.7 feature 的 Speckit 产物路径（对齐仓库既有约定）

| 产物 | 路径 | 说明 |
|---|---|---|
| 功能块 提案 | `harness/proposals/NNN-<slug>.md` | 调研结论 → 设计提案（原则 VI） |
| Spec | `specs/b<n>f<m>-<slug>/spec.md` | 本仓库自行创建 |
| Plan | `specs/b<n>f<m>-<slug>/plan.md` + `research.md` + `data-model.md` + `contracts/` + `quickstart.md` | 本仓库自行创建 |
| Tasks | `specs/b<n>f<m>-<slug>/tasks.md` | 本仓库自行创建，可逐条勾选 |
| 人工验证记录 | `harness/verification/B<n>F<m>/manual-verification.md` | 原则 V 硬要求 |
| 分支 | `b<n>f<m>-<slug>` | 与目录同名，见下方「本仓库的目录命名约定」 |

> **本仓库的目录命名约定（2026-11-05 定）**：feature 目录**直接用规划 ID**，
> 即 `specs/b<n>f<m>-<slug>/`（如 `specs/b1f1-contracts-core/`），**不带** Speckit 的三位序号。
> 理由：Speckit 的 `get_highest_from_specs()`（`.specify/scripts/bash/create-new-feature.sh:118-134`）
> 统计的是**创建序号**（`printf "%03d"`），与立项书的**规划 ID** 是两个不同的轴——
> 一旦创建顺序 ≠ 规划顺序，序号就会指错 feature。目录名应**只表达唯一权威的规划 ID**。
>
> **连带影响**：Speckit 的自动编号器因此**看不见**本仓库的 feature 目录，
> 故每个 feature 的目录由本仓库**自行创建**（`mkdir specs/b<n>f<m>-<slug>` + 写 spec.md），
> 并在 `.specify/feature.json` 登记 `feature_directory` —— 工具链的路径解析只认这个文件，
> 因此读写完全正常（`check-prerequisites.sh` 已实测通过）。

---

## 5. 跨 feature 的持续约束（每个 feature 都要守）

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
| 契约层零依赖 | 宪法「包层白名单」（**必装依赖 = 无**，宪法 v1.2.0） | ❌ 不冲突 |
| 32 个 feature | 5000 行上限（`architecture.md` 任务书）+ §4.1 LOC 标定 + §4.4 逐行求和 | ❌ 不冲突 |
| v2 内容（Studio UI / Store / Postgres）标为 v2 | 宪法原则 VII 三类"不做"清单、Q6 §3.3 路线 B | ❌ 不冲突 |

**唯一需要发起者确认的新增判断**：本指南把 **B17 Store** 与 **B26 Studio UI** 标为 v2，
依据是宪法原则 VII 的"范围红线"与 Q6 §3.3 的路线 B 达成度
（Studio 三件套在 v1 只需"图视图 + trace 时间线 + 状态快照/回放入口"，
完整交互式 IDE 属 v2）。**若发起者希望 v1 就交付完整 Studio UI，需把 B26 提前并追加 2 个 feature。**

---

## 7. 立即可执行的第一步（回答"我不知道如何跨出第一步"）

不需要更多调研。以下 3 件事今天就能做：

### 第 1 步：把本指南转成提案（30 分钟）

```bash
# 在 harness/proposals/ 下创建提案，把本指南的 §2/§3/§4 作为设计输入
# 提案必须回答：架构分层、协议清单、feature 清单、门禁落地
```

依据宪法原则 VI：调研产物先落 `harness/reports/`，结论再转入 `harness/proposals/`。

### 第 2 步：跑通 B1F1（契约层骨架）——第一次 speckit 闭环

```bash
# 1) 创建特性（short-name 带 feature 序号，便于追溯）
/speckit.specify 冻结 freegraph 契约层：StateDict/Command/StateSnapshot/RunConfig 类型、异常体系、contracts 包骨架

# 2) 生成计划（需要在 plan.md 里填 §2.3 的分层与 §3.5 的协议）
/speckit.plan

# 3) 生成任务
/speckit.tasks

# 4) 实现
/speckit.implement
```

**B1F1 的验收判据（可自动判定）**：
- `import freegraph.contracts` 成功，且 `pip show freegraph` **无任何必装依赖**（零第三方运行时依赖）；
- `StateDict` / `Command` / `StateSnapshot` / `RunConfig` 四个类型存在且有类型注解；
- 契约层不 import 任何 `freegraph` 内部模块（CI 断言）。

### 第 3 步：把 §4.3 的 feature 表落成机器可读的清单

建议在 `harness/proposals/` 下维护一张 `phases.md`（或 YAML），字段：
`feature_id / short_name / milestone / block / depends_on / est_impl / est_test / acceptance`。
**后续每个 feature 的 `/speckit.plan` 都从这张表取上下文**，避免每次重新推理依赖关系。

---

## 8. 待发起者拍板的 5 个问题

| # | 问题 | 本指南的默认建议 | 影响 |
|---|---|---|---|
| **Q1** | 契约层是否**物理拆成独立发行包**（`freegraph-contracts`），还是同包内的子模块 `freegraph/contracts/`？ | **同包子模块**（v1）。理由：拆包会引入双包版本同步与安装摩擦，收益（freechain 单独装契约）在 freechain 开工前不急。契约层**代码上**保持零内部依赖，将来要拆随时可拆。 | 影响 B1F1/B2F1 的 `pyproject.toml` 布局 |
| **Q2** | `StateSnapshot` 是否**完全对齐** LangGraph 的 `types.py:683` 字段集？ | **对齐**（`values`/`next`/`config`/`metadata`/`created_at`/`tasks`/`interrupts`）。`config` 用 freegraph 自有 `RunConfig` 而非 `RunnableConfig`。 | 影响 B2F1、B15F1 |
| **Q3** | v1 是否**必须包含 async**（`ainvoke`/`astream`）？ | **已答（2026-11-03）：默认 v2（未排 feature）**。初判为「v1 不做」，理由是 LangGraph 的 async 为 `SyncPregelLoop` 的镜像副本、语义等价但代码量翻倍，且 `target.py` 不需要 async；**该判断已修订**——LangGraph 已实现 async，**能力对等是跟进要求**，故归入 v2 范围。v1 不排期的理由：需同步/异步两套调度与测试，且 v1 无 async 依赖方。**若 freechain 需要 async 能力，应在 freegraph 提供 async 友好的注入点（如 `Checkpointer` 的异步方法可延后），而非在 v1 内核同步实现全套 async。** | 若提前纳入 v1：约 900–1,500 行 + 2 个 feature ≈ 6 人日 / 12,000 元；且**契约层需补 async 条目**（Q8 C1–C26 目前无 async） |
| **Q4** | `Store`（长期记忆）与 **Studio UI** 是否确实推到 v2？ | **是**（见 §6 末尾）。 | 影响 M3/M4 范围 |
| **Q5** | 是否接受"先做运行时层（M1）→ 再做图定义层（M2，`draw_mermaid_png` 与固定脚本在此就位）→ 再补可观测（M3）"的排序？ | **接受**。理由：运行时层独立性最高（先做可独立验收），且 `draw_mermaid_png` 属 MVP 硬约束，须与固定脚本同在 M2 就位。 | 影响整体排期 |

---

## 9. 自检清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 问题 1 有明确结论（要/不要 + 为什么） | ✅ | §2.1 结论「要，但只做分层 + 契约」+ §2.2 三个理由 + §2.5 明确不做的清单 |
| 问题 1 给出初步架构 | ✅ | §2.3 六层图 + §2.4 四条硬约束 + §3.5 四类协议三族数据格式 |
| 问题 2 有明确结论（要/不要 + 为什么） | ✅ | §3.1 四条判定标准 + §3.2 8 领域 25 交付 功能块 |
| 问题 2 给出 功能块 拆解 | ✅ | §3.2 全景 + §3.3 依赖图（拓扑序）+ §3.4 MVP 优先序 |
| 问题 2 给出模块间数据格式与协议 | ✅ | §3.5：4 类协议（P1–P4）+ 3 种格式（D1–D3）+ 8 条交互路径对照表 + PD-1..PD-5 纪律 |
| 问题 3 **领域级**体量判定（模块是否超 5000 行） | ✅ | §4.4 上表：8 领域逐条判定，**A3 = 7,840 超限**，其余均 < 5000 |
| 问题 3 **功能块 级**体量判定 | ✅ | §4.4 下表：25 个交付 功能块 逐条判定，最大 B7 = 3,660（73%），0 个超限 |
| 问题 3 超限部分拆为多个 feature | ✅ | §4.3 **32 个 feature** 切分表 + §4.5 映射总表 + §4.4 三层判定说明 |
| feature 与 speckit 闭环一一对应 | ✅ | 规则 PR-1；§4.7 产物路径 |
| 每个 feature ≤ 5000 行 | ✅ | §4.4：最大 1,480 行（30% 上限），0 个超限 |
| LOC 估算有依据、非拍脑袋 | ✅ | §4.1 以本机 `langgraph 1.2.11` 实测 LOC 为基准 + 折减系数推导；§4.4 全部数字由 §4.3 逐行求和得出（可复算） |
| 内部数字自洽 | ✅ | §4.3 相加 = 31,520；领域合计 = 功能块 合计 = feature 合计，三者相等 |
| 事实性结论带来源标记 | ✅ | LangGraph 源码 `文件:行号`（本机实测）；报告 `Q# §章节`；宪法 `文件:行号` |
| 术语用官方对照表，未混用自造词 | ✅ | 沿用 Q4 §3.4 权威表（Runtime/Framework/Harness）；"三大基础能力"标注为自造表述 |
| 与宪法七项门禁对齐 | ✅ | §4.6 门禁 × feature 落地表 |
| 给出"第一步"的行动指引 | ✅ | §7 三步立即可执行 |
| 未修改 `harness/docs`、`harness/demo/target.py`、任何源码 | ✅ | 本次仅新增 `harness/prompts/guide.md` |
