# harness/features —— feature 提示词初稿（`/speckit.specify` 用）

> **本目录是「人看的导航 + 机器用的提示词」的组合体。**
>
> 本目录共 **32** 个 feature 初稿（每个 `B<n>F<m>_*.md` 文件是一个 feature 的 `/speckit.specify` 提示词初稿）——
> 执行 `/speckit.specify` 时，把该文件正文中的「提示词正文」整段作为特性描述传入。
>
> **权威来源**：本目录的一切内容派生自 `harness/proposals/立项书.md`：
> - **feature 清单与小目标** = §5.2 总表（唯一权威）；
> - **契约 C1–C26** = §5.3（同步自 `harness/reports/Q8-图运行时最小契约.md` §3.4）；
> - **红线与门禁** = `.specify/memory/constitution.md`（原则 I–X）+ §9.1；
> - **验收契约** = §9.2 + `harness/demo/`。
>
> **冲突处理**：本目录与立项书 / 宪法冲突时，**以立项书与宪法为准**；
> 发现本目录有误 → 直接改本目录（它是派生文档）。

---

## 1. 开发顺序（**第 1 步做什么，第 2 步做什么…**）

> **行序 = 立项书 §5.2 的行序 = 单人串行推进顺序**（报价与现金流按此口径）。
> 「天」按 **每 feature 3 天**（开发 1 天 + 人工调试 1 天 + 修改 1 天）累计。
>
> **★ = 固定脚本（`harness/demo/target.py`）所需能力**，六项齐备即可跑通 fake 模型轮。

| 步 | feature | 文件 | 层 | 里程碑 | 依赖 | 行数 | 小目标（可判定验收判据） | ★ |
|---|---|---|---|---|---|---|---|---|
| 1 | **B1F1** | [B1F1_契约层骨架.md](B1F1_契约层骨架.md) | L1 | M0 | — | 900 | `import freegraph.contracts` 成功；**依赖零（闭包为空集）**；C1/C11/C16/C22 类型冻结；契约层不 import 任何内部模块 | |
| 2 | **B2F1** | [B2F1_四类协议与图数据类.md](B2F1_四类协议与图数据类.md) | L1 | M0 | B1F1 | 820 | 协议齐全；契约层可被单独消费；ARCH-2 通过；**冻结前置：D11 已批准** | |
| 3 | **B2F2** | [B2F2_公开API门面与快照测试.md](B2F2_公开API门面与快照测试.md) | L1 | M0 | B1F1,B2F1 | 560 | `from freegraph.graph import StateGraph, START, END` 可用；签名快照入库 | |
| 4 | **B3F1** | [B3F1_项目脚手架与CI门禁.md](B3F1_项目脚手架与CI门禁.md) | — | M0 | B1F1,B2F1 | 1,100 | 门禁生效：故意引入 `langchain` 依赖 → CI 必须失败 | |
| 5 | **B4F1** | [B4F1_schema解析与归约器提取.md](B4F1_schema解析与归约器提取.md) | L2 | M1 | B2F2 | 940 | `Annotated[list, operator.add]` 被正确识别为二元归约器 | |
| 6 | **B5F1** | [B5F1_Channel抽象与三类通道.md](B5F1_Channel抽象与三类通道.md) | L2 | M1 | B4F1 | 1,060 | 归约器 `operator(current, new)` 语义一致；无归约器 key 被覆盖 | |
| 7 | **B5F2** | [B5F2_稀疏状态读取.md](B5F2_稀疏状态读取.md) | L2 | M1 | B5F1 | 860 | C4 独立回归测试通过（`"llm_calls" not in node_input` 且 `.get("llm_calls", 0) == 0`）；差分测试夹具建立 | |
| 8 | **B7F1** | [B7F1_任务准备与super-step循环.md](B7F1_任务准备与super-step循环.md) | L2 | M1 | B5F1,B5F2 | **1,480** | 单 super-step 可执行；状态按归约器合并；**可脱离构建器验收**；**C4 回归测试推进到真实节点入参**（承接 B5F2）；**步末只清路由型 + 写入只由调度层发起 + 通道映射可变**（承接 B5F1）；**稀疏读唯一实现**（承接 B5F2） | |
| 9 | **B9F1** | [B9F1_Command原语.md](B9F1_Command原语.md) | L2 | M1 | B7F1 | 880 | `Command` 跳转 + 状态更新同时生效 | |
| 10 | **B12F1** | [B12F1_并发执行与错误传播.md](B12F1_并发执行与错误传播.md) | L2 | M1 | B7F1,B9F1 | 1,080 | 并行节点不串行化；首个异常正确抛出 | |
| 11 | **B7F4** | [B7F4_多源汇合边与屏障.md](B7F4_多源汇合边与屏障.md) | L2 | M1 | B7F1,B12F1 | 620 | `edges` 支持多源 `tuple[str, ...]`；目标节点在**所有**源跑完后才被触发（**上游同款** · 上游 `add_edge([a,b], c)`）；**破 B7F1 的 `edges` 冻结面**（发起者 2026-11-12 同意） | ⚠️ **口径注记（2026-11-13 · B7F4 澄清轮 **C-Q1** 拍板）**：上文的「**所有**源跑完后才被触发」比拍板后的口径（**组内全 · 组间任一**）**更窄** ⇒ ⇒ 精确口径 = 「**∃** 组 g：**∀** s∈g」⇒ ⇒ 单源边 + 多源边并存时**任一**入边满足即触发（**上游同款**）⇒ ⇒ **原描述不改写**（**只补注记**） |
| 12 | **B10F1** | [B10F1_interrupt与resume.md](B10F1_interrupt与resume.md) | L2 | M1 | B9F1 | **2,945** | HITL 中断/恢复闭环；从节点起点重跑 | |
| 13 | **B11F1** | [B11F1_Send动态fan-out.md](B11F1_Send动态fan-out.md) | L2 | M1 | B7F1 | 980 | map-reduce 模式可运行 | |
| 14 | **B13F1** | [B13F1_静态中断点与递归上限.md](B13F1_静态中断点与递归上限.md) | L2 | M1 | B10F1 | 680 | 递归超限抛明确异常 | |
| 15 | **B6F1** | [B6F1_StateGraph构建器.md](B6F1_StateGraph构建器.md) | L3 | M2 | B4F1 | 1,320 | 构建器 API 与 LangGraph 同名同签名 | ★ |
| 16 | **B7F2** | [B7F2_compile编译.md](B7F2_compile编译.md) | L3 | M2 | B6F1 | 1,200 | 图可编译；`compile()` 无参可调用 | ★ |
| 17 | **B7F3** | [B7F3_invoke返回完整状态.md](B7F3_invoke返回完整状态.md) | L2 | M2 | B7F1,B12F1 | 980 | `invoke` 返回 `{'messages': [...], 'llm_calls': N}` 完整状态 | ★ |
| 18 | **B8F1** | [B8F1_条件边路由与fresh读.md](B8F1_条件边路由与fresh读.md) | L2 | M2 | B5F2,B7F1 | 1,100 | C8 独立回归测试通过：路由函数看到本节点刚写入的值；差分夹具比对路由判定；**复用 B5F2 差分夹具**（条件边字段已预留）；**B7F1 侧已预留 `GraphSpec.conditional_edges`**（本轮恒空 · 填值即失败 ⇒ B8F1 **只需填值**即可复用，不新造第三套） | ★ |
| 19 | **B8F2** | [B8F2_stream多模式流式.md](B8F2_stream多模式流式.md) | L2 | M2 | B7F3 | 1,180 | 多模式流式输出 | |
| 20 | **B22F1** | [B22F1_get_graph与draw_mermaid.md](B22F1_get_graph与draw_mermaid.md) | L3 | M2 | B7F2 | 1,140 | `draw_mermaid()` 离线必然成功、零出站 | ★ |
| 21 | **B23F1** | [B23F1_draw_mermaid_png离线不阻断.md](B23F1_draw_mermaid_png离线不阻断.md) | L3 | M2 | B22F1 | 1,080 | PNG 路径离线不抛阻断性异常 | ★ |
| 22 | **B8F3** | [B8F3_节点别名与context通道.md](B8F3_节点别名与context通道.md) | L3 | M2 | B7F3 | 580 | C21（`context` 通道）/ C22（`RunConfig` 标识）/ C25（节点别名）落地 | |
| 23 | **B18F1** | [B18F1_Span数据类生产.md](B18F1_Span数据类生产.md) | L5 | M3 | B7F3 | 1,140 | span 属性命名符合 OTel GenAI semconv；未注入 tracer 时零副作用、零开销 | |
| 24 | **B19F1** | [B19F1_TraceSink与current_span.md](B19F1_TraceSink与current_span.md) | L5 | M3 | B18F1 | 840 | 嵌套 span 父子关系正确；不注入 tracer 时零副作用 | |
| 25 | **B20F1** | [B20F1_本地Trace存储JSONL.md](B20F1_本地Trace存储JSONL.md) | L5 | M3 | B19F1 | 820 | trace 落盘，零出站 | |
| 26 | **B20F2** | [B20F2_Trace查询API与SQLite后端.md](B20F2_Trace查询API与SQLite后端.md) | L5 | M3 | B20F1 | 1,020 | 可按 thread / 时间 / 节点名检索 | |
| 27 | **B14F1** | [B14F1_Checkpointer协议与MemorySaver.md](B14F1_Checkpointer协议与MemorySaver.md) | L4 | M3 | B7F3 | 1,200 | 快照 + pending writes 双层持久化 | |
| 28 | **B15F1** | [B15F1_SqliteSaver与状态历史.md](B15F1_SqliteSaver与状态历史.md) | L4 | M3 | B14F1 | 1,240 | 历史快照可枚举 | |
| 29 | **B16F1** | [B16F1_update_state与时间旅行.md](B16F1_update_state与时间旅行.md) | L4 | M3 | B15F1 | 1,040 | 可从历史 checkpoint 重放 | |
| 30 | **B21F1** | [B21F1_OTLP导出插件与后端对接.md](B21F1_OTLP导出插件与后端对接.md) | L5 | M4 | B20F2 | 700 | OTLP exporter（可选 extra）+ 三个后端最小对接示例 + 失效风险说明；默认关闭 | |
| 31 | **B24F1** | [B24F1_打包分发与兼容矩阵.md](B24F1_打包分发与兼容矩阵.md) | — | M4 | B23F1,B16F1 | 900 | 发行包就绪；兼容矩阵与归属清单齐备；**发行产物纯度门禁通过** | |
| 32 | **B25F1** | [B25F1_双跑验收与迁移说明.md](B25F1_双跑验收与迁移说明.md) | — | M4 | B24F1 | 620 | **MVP 完成**：双跑通过，框架零出站断言通过 | |

**合计**：**32 feature / 24 功能块 / 33,005 行 / 96 人日 / 报价 192,000 元 / 96 天**。

> **B17（`Store` 长期记忆）已于 2026-11-05 砍掉**——理由：freegraph 是**通用图框架**
> （智能体 / RPA 自动化 / 脚本编排 / 在一定程度上替代 `main` 函数 / 可视化工作流编排），
> 共同前提是「**图 = 一个进程**」；`Store` 是**跨会话 / 跨图**能力，复杂且违背初衷。
> 契约 **C20 仍冻结**（freechain 的设计输入不受影响），**实现后补（v2）**；
> `compile(store=...)` 关键字仍被接受，但 v1 **背后无实现**。详见立项书 §12 D5。

---

## 2. 里程碑视图（同一顺序的分组视角）

| 里程碑 | 步次 | feature | 天数区间 | 达成状态 |
|---|---|---|---|---|
| **M0 地基** | 1–4 | B1F1 · B2F1 · B2F2 · B3F1 | 第 3 → 12 天 | 契约冻结，CI 门禁生效 |
| **M1 运行时内核** | 5–14 | B4F1 · B5F1 · B5F2 · B7F1 · B9F1 · B12F1 · **B7F4** · B10F1 · B11F1 · B13F1 | 第 15 → 42 天 | 状态模型、super-step、Command/HITL/Send/并发就绪；**运行时可独立验收（不依赖构建器）** |
| **M2 图定义与对外 API** | 15–22 | B6F1 · B7F2 · B7F3 · B8F1 · B8F2 · B22F1 · B23F1 · B8F3 | 第 45 → 66 天 | 构建器 + compile + invoke + 路由 + stream + 图导出；**固定脚本跑通（fake 模型）= MVP 验收点（第 21 步 / 第 63 天）** |
| **M3 可诊断** | 23–29 | B18F1 · B19F1 · B20F1 · B20F2 · B14F1 · B15F1 · B16F1 | 第 67 → 87 天 | checkpoint + trace + 时间旅行（**四类诊断能力齐备**） |
| **M4 生态** | 30–32 | B21F1 · B24F1 · B25F1 | 第 88 → 96 天 | 打包、兼容矩阵、双跑验收、文档（**v1.0 收口**） |

**关键路径（15 个 feature / 45 天）**：
`B1F1 → B2F1 → B2F2 → B4F1 → B5F1 → B5F2 → B7F1 → B9F1 → B12F1 → B7F3 → B14F1 → B15F1 → B16F1 → B24F1 → B25F1`

**可并行的次长链（可观测链，15 个 feature，与交付终点无依赖边）**：
`B1F1 → B2F1 → B2F2 → B4F1 → B5F1 → B5F2 → B7F1 → B9F1 → B12F1 → B7F3 → B18F1 → B19F1 → B20F1 → B20F2 → B21F1`

> 单人按 M0→M4 串行；多人可并行：`B10F1`/`B11F1`、`B20F1`/`B14F1`、`B7F4`/`B10F1`。

---

## 3. 开工前的 M0 前置决策（**全部已决 · 2026-11-05**）

| 决策 | 内容 | 阻塞谁 | 状态 / 决议 |
|---|---|---|---|
| **D1** | 契约层是否物理拆成独立发行包 | `pyproject.toml` 布局（B1F1/B2F1） | ✅ **已拍板（2026-11-04）：v1 同包子模块，不拆独立发行包**。理由：① 拓扑与 LangChain-land 的 `langchain-core` 同构（契约层是底座，L2–L5 全坐其上），但 `langchain-core` 必须独立是因为**被 5+ 个包共享**；freegraph v1 下游只有 **1 个**（freechain），全包**强制依赖为零** → 无依赖需隔离；② LangGraph 自身的拆包序列解的是**可选能力 / 后端 / 许可证**，核心契约类型（`Command` / `Send` / `interrupt` / `START` / `END`）**就在主包内**；③ 拆包代价 = 两套版本号 / 兼容矩阵 / 发布流水线，与 R9 单点依赖冲突；④ 「freechain 只想要契约」已被 ARCH-2 解决（装 `freegraph` **一个第三方包都不拉**，`from freegraph.contracts import ...` 不加载内部层）。**附加约束**：`freegraph/__init__.py` MUST 保持惰性 / 空壳（见 B1F1 / B2F2）。**重开信号**：freechain 需单独依赖契约 / 出现非可选的重量级依赖 / 出现第 3 个消费契约层的包 |
| **D11** | 契约增补（C27）+ C22/C23 字段约定修订 + 宪法原则 VII MINOR 修订 | **B2F1 冻结契约** / B20F1 / B20F2 / B21F1 | ✅ **已批准（2026-11-05）并落地**：Q8 §3.4.1（增补 **C27** + C22/C23 字段约定）· 立项书 §5.3 / §5.3.1 · 宪法原则 VII MINOR 修订 + 宪法定版 **1.0.0**。**契约清单权威范围 = C1–C27**；**B2F1 的冻结前置已解除** |
| **D12** | 零出站与依赖门禁的**作用域定义**（只观测不阻断 + 按发起方归因） | **B3F1 CI 门禁** / B2F1 依赖断言口径 | ✅ **已批准（2026-11-05）**：宪法原则 V 门禁 4 措辞 PATCH 生效——socket 夹具**只观测不阻断 + 按发起方归因**，只对「框架出站」断言 = 0（用户出站记录在案不判失败；人工轮允许「模型厂商端点」一条） |

> **M0 前置已全部解除**（2026-11-05）→ **可以开工 B1F1**。
> **D2–D9** 于 2026-11-05 随立项书签署**接受默认建议**（D3 的最终取值属 B 类议题，待专项讨论）。
> **D10** 已更早拍板（发行名 = 导入名 = `freegraph`）。

---

## 4. 通用红线（每个 feature 都要守；详见宪法）

| # | 红线 | 检查方式 |
|---|---|---|
| 1 | freegraph 自身依赖闭包无 `langsmith` / `langchain*` / `langgraph*`；基础安装**零**第三方依赖 | CI 依赖门禁（隔离 venv + 运行时反向断言） |
| 2 | 依赖许可证 ∈ {MIT, Apache-2.0, BSD-2/3, PSF}；禁 `langgraph-api` / `langgraph-runtime-inmem` / Phoenix（ELv2） | CI 许可证白名单 |
| 3 | 内核**不读任何环境变量**（`LANGSMITH_*` / `LANGCHAIN_*` / `OTEL_*` 一律不读） | CI 静态扫描 |
| 4 | **freegraph 自身零出站**（用户代码出网**不受限制、不被阻断**；只观测不阻断 + 按发起方归因） | socket 监测夹具 + 静态扫描 + 断网等价性任务 |
| 5 | 导入图单向：L1 → L6 编号递增方向即允许方向；跨层单元只能 import L1 与更低层 | CI AST 扫描（ARCH-1/2/3） |
| 6 | 公开 API 只经由 L1 导出；API 快照入库 | API 快照测试（ARCH-4） |
| 7 | `harness/demo/target.py` 是**只读基准**，diff 必须为空 | CI diff 断言 |
| 8 | C4（稀疏状态）/ C8（条件边 fresh 读）两条**独立回归测试**常驻 | CI |
| 9 | 第三方代码入 `THIRD_PARTY_NOTICES`；API 兼容矩阵随公开 API 变更同步 | 评审门禁 |
| 10 | 每个 feature 必须留**人工验证记录**（`harness/verification/<feature>/manual-verification.md`） | 人工门禁 |

---

## 5. 验收脚本集（各 feature 的「靶子」）

| 脚本 | 验证什么 | 主要覆盖 feature |
|---|---|---|
| `harness/demo/graph_core.py` | 图运行时内核（前置用例，零第三方依赖） | B4F1–B13F1、B6F1–B8F3 |
| `harness/demo/agent_loop.py` | Agent 工具循环（`target.py` 的零依赖等价物） | B7F3 · B8F1 · B8F2 · B9F1 · B10F1 |
| `harness/demo/visualization.py` | 图导出与可视化（mermaid / PNG / 流式） | B8F2 · B22F1 · B23F1 |
| `harness/demo/diagnostics.py` | **M3 可诊断性**（trace / checkpoint / 时间旅行）——**待 B25F1 补齐**（四个 API 形态随 M3 各 feature 锁定） | B14F1–B20F2 · B21F1 |
| `harness/demo/acceptance.py` | 人工验收编排器（前置自检 + 零出站断言 + 串跑） | B25F1 |
| `harness/demo/target.py` | **只读基准**（LangGraph Quickstart 的机械替换版） | 全程回归 |

> 退出码：`0` = PASS / `1` = 断言失败 / `2` = 环境未就绪（两者必须分开）。
> 「软断言 → 硬断言」的升级节点已写在相应 feature 的初稿里（`recursion_limit` 载体 →
> B13F1；`MemorySaver` 模块路径 / trace 目录参数名 / `update_state` 签名 / tracer
> 注入载体 → M3 各 feature；节点别名形态 → B8F3）。

---

## 6. 单个 feature 初稿的结构（模板说明）

每个 `B<n>F<m>_*.md` 都按同一骨架写，便于横向对照：

| 章节 | 内容 |
|---|---|
| 顶部元信息表 | feature ID / 所属 功能块 / 架构层 / 里程碑 / 依赖 / 规模 / 建议 short-name / 是否 MVP 必需 |
| 1 目标 | 一句话说清这个 feature 交付什么 |
| 2 背景与上下文 | 为什么需要它、它依赖什么、上位约束是什么 |
| 3 用户场景 | P1/P2/P3 用户旅程 + 独立验收方式（可直接转成 spec 的 User Stories） |
| 4 功能需求 | 编号 FR-001…（可测试、无歧义） |
| 5 成功标准 | SC-001…（可度量、可验证） |
| 6 验收判据 | **立项书 §5.2 小目标逐条拆解 + 判定方式**（小目标原文照抄，便于核对） |
| 7 关键实体与契约 | 相关 C 编号、数据类 / 协议、口径提醒（含 D11 未冻结项标注） |
| 8 边界 | **本 feature 明确不做**的事 |
| 9 红线与质量门禁 | 依赖门禁 / 零出站 / 导入方向 / 人工门禁 / 证据门禁 |
| 10 交付物与后续 | 交付物清单、解锁的下一个 feature、风险提示 |
| 依据 | 立项书章节、宪法原则、Q 报告、源码行号、验收脚本 |

---

## 7. 相关文档

| 文档 | 作用 |
|---|---|
| `harness/proposals/立项书.md` | **上位依据**：§5.2 总表（唯一权威）、§5.3 契约、§9 验收契约、§12 待决 |
| `.specify/memory/constitution.md` | 宪法原则 I–X + 7 项质量门禁 + 发布门禁 |
| `harness/reports/Q8-图运行时最小契约.md` | C1–C26 的**唯一权威** |
| `harness/reports/Q3-LangGraph的开源边界.md` | 18 项 API 逐项裁定、付费墙触发点、出站点 |
| `harness/reports/Q6-可视化与可诊断性的规模与可行性.md` | 路线 B 选型与达成度口径 |
| `harness/prompts/guide.md` | 架构分层、4 类协议、feature 拆解规则（PR-1…PR-6） |
| `harness/demo/README.md` | 验收脚本集说明 + 「待锁定形态」清单 |
| `harness/proposals/更名与迁移说明.md` | `opengraph` → `freegraph` 更名与迁移清单 |
