# 上游对照（Upstream Parity）—— B10F1 的**证据表**

**上游**：`langgraph` **1.2.11**（取证于 **2026-11-13** · 本仓库 `.venv` 内安装 · **仅差分测试侧**使用）
**Spec 的权威表**：[`../spec.md`](../spec.md) §Upstream Parity（**P-01…P-17** · **E-1…E-26** ·
**DI-01…DI-08** · **X-1…X-5**）

> 本文件**不重复** spec 的三张表 ⇒ 只落**「实现期要怎么做」**的**执行细则** ⇒
> 任务派发时以 **spec §Upstream Parity + 本文件**为准 ⇒ 冲突时 ⇒ **以 spec 为准**。

---

## §1 取证方式（**原则 XI「上游锚点纪律」**）

| 类别 | 要求 | 本 feature 的落实 |
|---|---|---|
| **版本钉住** | MUST 钉住 `langgraph` 的**实际安装版本** | **1.2.11**（换版本 MUST 重新核实全部锚点） |
| **锚点格式** | 每条行为断言 MUST 带 **版本 + `路径:行号`** | spec 的 **P-01…P-17** 全部带 `langgraph/…:行号` |
| **行为断言** | MUST 有**实测**支撑（只读源码**不足**） | spec 的 **E-1…E-26**（实跑脚本取自 `.venv`） |
| **关系标注** | MUST 标 `SAME` / `STRICTER` / `DIFF` | spec §1 逐条标注 |
| **可验证出口** | MUST 交付**差分场景组** | **DI-01…DI-08**（落 `tests/differential/parity_probe.py`） |
| **偏离登记** | 只允许三类 | **X-1…X-5**（spec §4） |

---

## §2 上游的**机制**落点（**实现期照抄清单**）

| 机制 | 上游锚点 | freegraph 落点 | 关系 |
|---|---|---|---|
| `interrupt()` 的**首次**行为（抛中断） | `langgraph/types.py:967-974` | `freegraph.runtime._interrupt.interrupt`（⚠️ **L2 目录条目内** · 门面 `graph.py` **模块级**转出 · **PR-4** / **DR-13**）· 抛 `GraphInterrupt((Interrupt(...),))` | SAME |
| `interrupt()` 的**恢复**行为（返回恢复值） | `langgraph/types.py:955-958` | 同上 · `resume[index]` | SAME |
| 中断载荷 = **1-元组** | `langgraph/types.py:967-974` | 同上 | SAME |
| `Interrupt.id` 由**内核**从命名空间派生 | `langgraph/types.py:616-618` | `_interrupt` · `blake2b(f"{node}:{uuid4}")` | **DIFF**（算法 · **X-4**） |
| 命名空间**含随机 uuid4** | **实测 E-23** | 同上 | SAME |
| 恢复值经 **`__resume__`** pending write 传递 · 值**包成列表** | `langgraph/pregel/_algo.py:1301-1308` | `run_graph` 的恢复路径 | SAME |
| 中断留痕经 **`__interrupt__`** pending write · 载荷 = **元组** | `langgraph/pregel/_runner.py:588-591` | `run_graph` 的挂起路径 | SAME |
| 恢复值**按节点内顺序**消费 | `langgraph/types.py:951-958` + **实测 E-17** | `_interrupt` 的任务现场 | SAME |
| 恢复值**不足** ⇒ **再次挂起** | **实测 E-17** | `_interrupt` | SAME |
| 中断**前**的写入**不丢失** | **实测 E-16 / E-21** | B12F1 的既有合并路径（**零改动**） | SAME |
| 「**真异常优先**」⇒ 中断元组**丢弃** | `langgraph/pregel/_runner.py:687` 先于 `:690` | B12F1 的既有收尾（**零改动**） | SAME |
| 根图**抑制**中断 ⇒ 落进结果键 | `langgraph/pregel/_loop.py:1333-1339` | `run_graph` 接住 ⇒ `InterruptResult` ⇒ `as_result_dict()` | SAME（**层次**：L2 抛 · 图级转键） |
| **未挂** checkpointer ⇒ 恢复**明确异常** | `langgraph/pregel/_loop.py:904-907` | `InterruptError(reason="checkpointer_required")` | **STRICTER**（**X-2**） |
| 多个挂起中断 ⇒ 须**按 id** 指定 | `langgraph/pregel/_loop.py:910-919` | `InterruptError(reason="ambiguous_resume")` + map 形态 | **STRICTER**（**X-2** / **X-3**） |
| **未提供**恢复值 | ⚠️ **实测 E-13 / E-14**（上游缺陷：`UnboundLocalError`） | `InterruptError(reason="resume_value_required")` | **STRICTER**（上游缺陷 ⇒ 更确定） |
| `Command(resume=…)` **与** `update=` **并存** | `langgraph/pregel/_io.py:74-78` | `update` 走**通道写入** · `resume` 走**恢复通道** | SAME |
| 已有快照的会话 + **普通字典**输入 ⇒ **会话连续** | `langgraph/pregel/_loop.py:975-985` · **实测 E-26 ②** | `run_graph` 的首次运行路径（**续跑** · 读 `.scheduler` · 写通道 ⇒ 版本推进 ⇒ 订阅节点重新触发） | SAME |
| 已有快照的会话 + **`None`** 输入 ⇒ **只有被中断的节点**重跑 · **`.id` 不变** | `langgraph/pregel/_loop.py:975-985` · **实测 E-15 / E-26 ①** | 同上（**不**写任何通道） | SAME |
| `invoke(None, config)` **不是**恢复入口 | **实测 E-15** | 同款 | SAME |

---

## §3 差分场景的**实现细则**（**DI-01…DI-08**）

### 3.1 ⚠️ **必须新增**的比较口径（**探针扩展**）

既有 `_compare_interrupts` 比的是 `(value, id)` **逐字**（`tests/differential/parity_probe.py:186-198`）
⇒ ⇒ B10F1 的 `.id` 由**内核**生成 ⇒ **两侧必不同**（freegraph = `blake2b` · 上游 = `xxh3`；
且 freegraph 的命名空间含**随机 uuid4**）⇒ ⇒ **必须**新增一个口径：

| 口径 | 语义 | 用途 |
|---|---|---|
| `"interrupt-shape"` | 比 `.value` **逐字** + 比 `.id` 的**形态**（正则 `^[0-9a-f]{32}$`）⇒ ⇒ **不比**具体值 | **DI-01 / DI-07** |

⚠️ **只增能力** ⇒ ⇒ **既有 43 个场景的行为与判词逐字不变**（**实测** `parity_probe._scenarios()` == 43） ⇒ ⇒ 既有差分闸口**恒绿**
（沿用 B12F1 的既有纪律）。
⚠️ `Scenario` 已有 `expect_interrupt` · `_interrupt_payload` · `_compare_interrupts` ⇒ ⇒
**复用**即可 ⇒ ⇒ **零**新夹具。

### 3.2 场景 ↔ 取值口径 ↔ 判词

| # | 场景 | 口径 | 判词 | 备注 |
|---|---|---|---|---|
| **DI-01** | 单节点中断 ⇒ 结果含 `__interrupt__`，元素带 `.value` / `.id` | `interrupt-shape` | SAME | freegraph 从**挂起结果**取 · 上游从**结果键**取 ⇒ 取法不同、**比的是同一批东西** |
| **DI-02** | `Command(resume=…)` 恢复 ⇒ 跑完且状态含恢复值 | `exact` | SAME | 两侧**最终状态**逐 key 相等 |
| **DI-03** | 恢复时节点**从头重跑** | `exact` | SAME | 两侧的**执行次数**都 == 2（节点内自增计数）⇒ **不**比中间态 |
| **DI-04** | **未挂** checkpointer 时恢复 ⇒ **失败** | 失败/成功 | STRICTER | 差分探针**只比「成功 / 失败」**（既有纪律）⇒ ⇒ 异常**类名不同**不影响判词 |
| **DI-05** | 中断**前**的写入**不丢失** | `exact` | SAME | 两侧最终状态逐 key 相等 |
| **DI-06** | 同节点内**两个** `interrupt()` ⇒ 恢复值**按顺序**匹配 | `exact` | SAME | 两个恢复值按序落位 |
| **DI-07** | 跨节点**两个**挂起中断 ⇒ `__interrupt__` **两个**元素 | `interrupt-shape` + **集合比较** | SAME | ⚠️ **不**比顺序（上游的合并顺序是**竞态** · `langgraph/pregel/_runner.py:672`） |
| **DI-08** | 跨节点多挂起中断 + **单值**恢复 ⇒ **失败** | 失败/成功 | STRICTER | 同 **DI-04** |

### 3.3 ⚠️ 差分场景的**前置条件**

| 场景 | 前置 |
|---|---|
| **DI-02 / DI-03 / DI-05 / DI-06 / DI-08** | **两侧都必须挂 checkpointer** ⇒ ⇒ **上游侧**用 `InMemorySaver` · **freegraph 侧**用**桩**（本 feature **不实现** saver · FR-019）⇒ ⇒ 探针需要**新增**「挂 checkpointer」的能力（上游侧 `compile(checkpointer=…)` · freegraph 侧 `run_graph(..., checkpointer=…)`）⇒ ⇒ **探针要能表达「两次调用 + 同一 config」**（恢复语义**必然**是两次调用）⇒ ⇒ ⚠️ **探针需要扩展**（`Scenario` 增「第二次输入 / 是否挂 saver / 是否比较恢复后结果」的字段）⇒ ⇒ **只增能力** ⇒ ⇒ 既有 43 个场景**逐字不变** |

---

## §4 偏离登记（**与 spec §4 同步** · **零新增**）

| # | 类别 | 摘要 |
|---|---|---|
| **X-1** | DIFF（结构 · 非更严） | `__interrupt__` 的**值** = **元组**（上游 `invoke()` = **list**） |
| **X-2** | **STRICTER**（失败信号更严 · 更结构化） | 失败信号的**异常类型** = `InterruptError`（上游 = 内置 `RuntimeError`）· **消息要点逐字同款** |
| **X-3** | DIFF（结构 · 非更严 · 消除歧义） | 「按 id 的映射」的**识别规则** = 「全部 key 都是挂起中断的 id」（上游 = 「key 像摘要」） |
| **X-4** | **DIFF**（算法 · **必须自研区 ①** · 零依赖） | `.id` 的**摘要算法** = `blake2b-128`（上游 = `xxh3_128`）⇒ **长度与不可猜性同款** |
| **X-5** | DIFF（**阶段性** · 消解条件已写死） | 「真异常 + 中断同现」时上游把中断元组写进 **pending writes** ⇒ freegraph v1 **无 checkpoint** ⇒ **丢弃** ⇒ ⇒ **B14F1** 落地后**自动消解**（承接 **D-2**） |

⚠️ **零新增偏离** ⇒ ⇒ 本 feature 的偏离总数 = **5**（与 spec 一致）。
> 📌 **「L2 内部 API 的导出面」类冻结面不属偏离**（宪法 v1.8.0「破冻结面的三条」第 ② 条）：
> **上游无此项** ⇒ ⇒ **属必须自研区 ③**（上游**没有** `runtime.__all__` / `runtime.errors.__all__`
> 这个「L2 内部 API 导出面」的概念）⇒ ⇒ ⇒ **零行为面偏离**（用户**看不见** L2 内部 API）⇒ ⇒ ⇒ 但**冻结断言**
> 仍 MUST **回溯修订**（spec §5 **T-1** · **六处**代码断言）+ **发起者追认** ⇒ ⇒ 详见 spec
> §Upstream Parity **§1.1**。
> ⚠️ **2026-11-13 分析轮实测扩容（PR-8）**：初版只登记 **3 处**（`runtime.__all__`）⇒ ⇒ **实测**发现
> **另 3 处**必红（`runtime.errors` 的符号面与异常类清单 · 门面 `interrupt` 的「未接线」测试 ·
> `_primitives.py` 的「未接线守卫」）⇒ ⇒ ⇒ 破冻结面清单 = **6 处** ⇒ ⇒ **判据零放宽**。

---

> ⚠️ **「登记」≠「偏离」**（原则 XI / 立项书 §5.9 **E-2**）：本节列出的机制名是**上游的实现零件**，freegraph **不采用**其**形态** ⇒ ⇒ 但它们的**行为面**一律**照抄** ⇒ ⇒ **故不构成偏离** ⇒ ⇒ **不**进 spec 的偏离登记表（**X-1…X-5**）⇒ ⇒ ⚠️ 若将来某个零件**连行为面**也分叉 ⇒ ⇒ **必须**补进偏离登记并论证 ⇒ ⇒ **本节不是**「漏登记」。

## §5 上游的**保留**机制名（freegraph **不**采用 · 仅登记）

| 上游名 | 上游位置 | freegraph 的处置 |
|---|---|---|
| `GraphBubbleUp` | `langgraph/errors.py:50` | **不采用** ⇒ freegraph 用 L1 已有的 `GraphInterrupt`（**零新增异常类型**） |
| `NodeInterrupt` | `langgraph/errors.py:114-126`（**已 deprecated**） | **不采用** |
| `PregelScratchpad` | `langgraph/_internal/_scratchpad.py` | **不采用**该类 ⇒ freegraph 用**自研**的两级 `ContextVar`（research **DR-01 / DR-02**）⇒ ⇒ **必须自研区 ③**（上游的类与 freegraph 的层级结构不匹配）⇒ ⇒ **零**行为面偏离（语义**照抄**） |
| `CONFIG_KEY_SEND` / `CONFIG_KEY_SCRATCHPAD` / `CONFIG_KEY_CHECKPOINT_NS` | `langgraph/_internal/_constants.py` | **不采用**（freegraph 的现场走**两级 ContextVar**）⇒ ⇒ 仅登记 |
| `CONFIG_KEY_RESUME_MAP` | `langgraph/_internal/_constants.py:72` | **不采用** ⇒ freegraph 直接按 **id** 匹配（**X-3**） |
| `NULL_TASK_ID` | `langgraph/_internal/_constants.py:93` | **不采用** ⇒ freegraph 的 `task_id` = **节点名**（checkpoint 契约 §5） |
