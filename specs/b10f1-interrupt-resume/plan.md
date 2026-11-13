# Implementation Plan: B10F1 · `interrupt()` + `resume`（HITL 中断与恢复闭环）

**Branch**: `b10f1-interrupt-resume` | **Date**: 2026-11-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/b10f1-interrupt-resume/spec.md`（**唯一权威** · 含澄清轮 **5** 条拍板 + 上游照抄补记 **F-1…F-5**）

> ⚠️ **本 plan 的上游**：宪法 **v1.11.0**（原则 **XI 上游优先** / **XII 最优设计优先**；
> **v1.11.0** 的两条补强 —— 「判据级可追溯性」+「冻结断言清单实测化」—— **由本 feature 的分析轮实测触发**）+
> 上游 `langgraph` **1.2.11**（取证于 2026-11-13）⇒ ⇒ **内容照抄上游 + 形态取最优** ⇒
> **只在失败信号上更严**（spec 的 **X-1…X-5**）并**如实标注**。
> ⚠️ **plan 阶段发现 spec 的两处问题** ⇒ **登记项 PR-1**（读侧契约**增** `.scheduler` ⇒ **回修**
> spec 裁定 9 / FR-018）⇒ ⇒ **不是 L1 冻结面** ⇒ ⇒ **不需要发起者追认**；
> ⇒ + **PR-4**（`interrupt()` 实现体的**落点**与**门禁 G25** 冲突 ⇒ ⇒ **实测**两种口径**都判红**
> ⇒ ⇒ **回修**为「机制落 `runtime/_interrupt.py`（**L2 目录条目内**）· 门面 `graph.py`
> **模块级**转出 · `_primitives.py` **只留 `Send`**」）⇒ ⇒ **判据零放宽**（G25 一字未改）
> ⇒ ⇒ **不需要发起者追认**。
> ⚠️ **2026-11-13 分析轮再登记两项**：**PR-8**（破冻结面清单扩容为 **6 处** —— **实测**发现
> **另 3 处**既有冻结断言按现 tasks 实施会**必红** ⇒ ⇒ 须回溯修订 + 发起者追认 · **并入 V-1 的
> 那一次**）· **PR-7**（范围变更 **+60 行** —— 补 **3** 条**测试级**覆盖缺口
> ⇒ ⇒ **发起者已确认** · 同样并入 V-1 的那一次）。
> ⚠️ **2026-11-14 实施期再登记两项**：**PR-9**（破冻结面清单 **6 处 → 7 处** —— **实施期实测**
> 又发现 **1 处**必红 ⇒ 须回溯修订 + 追认 · **并入 V-1 的那一次**）·
> **PR-10**（范围变更 **+1,685 行** ⇒ **实施口径 2,945 行 = 实现 1,091 / 测试 1,854** ——
> **7 处**冻结断言的**实测化**回溯修订 + 差分探针的**两段式**能力 + **8** 个 `DI-` 场景 +
> 本 feature 的 **6** 个测试文件 ⇒ **零功能删减**）
> ⇒ ⇒ **立项书 §5.2 已同步**（B10F1 行 **1,260 → 2,945** · 合计 **31,320 → 33,005**）
> ⇒ ⇒ **全部**已由**发起者于 2026-11-14 追认**（**一次**打包 · 追认次数 = **1**）。

---

## Summary

**交付什么**：**人工介入（HITL）的中断与恢复闭环** —— 节点调用 `interrupt(value)` ⇒ 图**挂起**
并把中断信息交还调用方（`__interrupt__`）⇒ 调用方用 `Command(resume=...)` 提交输入 ⇒
**图从被中断节点的起点重跑**、节点第二次执行时拿到 resume 值并继续跑完。

**技术路线**（零第三方依赖 · 零出站 · 零环境变量）：

| 关注点 | 落法 | 依据 |
|---|---|---|
| **中断原语** | 门面导出名 `interrupt(value)`（**7 符号面零改动**）· **运行期机制**落 `src/freegraph/runtime/_interrupt.py`（**L2 目录条目内**）· 门面 `src/freegraph/graph.py` 用**模块级** `ImportFrom` **直接转出**（`facade-L1-L3` 例外）⇒ ⇒ `src/freegraph/_primitives.py` **只留 `Send`**、**MUST NOT** import `runtime/`（**跨注册表条目的同层 import** ⇒ **门禁 G25** 判红） | spec 裁定 1 / DR-01 / **DR-13** · **PR-4** |
| **运行期上下文** | **两级 `contextvars.ContextVar`**（**运行级**：恢复值 + 先前中断载荷 · **任务级**：节点内进度）⇒ 落 L2 **私有**模块 `runtime/_interrupt.py` | **上游同款**（`langgraph/config.py:17-29`）· DR-01 / DR-02 |
| **中断的抛出** | `GraphInterrupt((Interrupt(value=value, id=…),))`（**1-元组** · **上游同款**） | `langgraph/types.py:967-974` |
| **`.id` 的生成** | 命名空间 = `f"{节点名}:{uuid4().hex}"`（**含随机量** ⇒ **不可猜**）· 摘要 = `hashlib.blake2b(digest_size=16)` ⇒ **32 位十六进制** | **上游同款**（E-23）· 偏离登记 **X-4**（零依赖） |
| **`.id` 的跨恢复稳定** | **恢复时复用** pending writes 里那个 `Interrupt` 的 **既有 id** ⇒ ⇒ **结构性保证** · **零新增持久化字段** | E-17 · 补记 **F-1** · DR-03 |
| **挂起的结果载体** | **L2 新增 `InterruptResult`**（**4 字段**：`state` / `interrupts` / `executed` / `steps`）⇒ `SuperStepResult` **四字段零改动** | spec 裁定 2（澄清轮 **Q1**）· DR-04 |
| **结果键** | `as_result_dict()` = `{**state, "__interrupt__": interrupts}` ⇒ **本 feature 独占**转成路径 ⇒ B7F3 只调用 | spec 裁定 1 / 裁定 10 · **X-1** |
| **失败信号** | **L2 新增 `InterruptError`**（`FreegraphError` 子类 · `.reason` **封闭 5 码** · **不带**上下文） | spec 裁定 3（澄清轮 **Q2**）· **X-2** |
| **恢复的入口** | **L2 新增 `run_graph(spec, input=None, *, state=None, checkpointer=None, config=None, max_steps=10007, max_concurrency=None) -> SuperStepResult \| InterruptResult`**（⚠️ **`state` = `SchedulerState` · 调度状态** · **不是**状态字典 · 逐条参数口径见 spec 裁定 10） | spec 裁定 10 · DR-06 |
| **恢复的状态重建** | 通道 = `Channel.from_checkpoint`（**现成**）· 调度账本 = `.scheduler` · 待跑节点 = `.snapshot.next`（**显式** · **不走**触发判定） | spec H-5 ⑤ · DR-07 |
| **检查点契约** | **读侧** = `.snapshot` + `.pending_writes` + **`.scheduler`** · **写侧** = `put(values=, metadata=)` + `put_writes(writes=, task_id=, task_path=)` · 保留通道名 `__interrupt__` / `__resume__` | spec 裁定 9 · [`contracts/checkpoint-contract.md`](./contracts/checkpoint-contract.md) |
| **恢复值的传递** | 恢复时写 `__resume__` 的 pending write（值 = **列表** · 节点内顺序）⇒ 执行时按序消费 | **上游同款**（`_algo.py:1301-1308`）· DR-10 |
| **恢复的语义** | **从节点起点重跑**（**不**保存局部变量 · **不**从中断点继续）· 恢复值**不足** ⇒ **再次挂起** | **上游同款**（E-2 / E-8 / E-17）· 裁定 5 / 裁定 7 |
| **可验证出口** | 差分场景 **DI-01…DI-08**（**`DI-` 前缀** · 与既有 B12F1 / B7F4 的 `D-xx` **不重号**；含**新的**比较口径 `"interrupt-shape"` ⇒ 比 `.value` + id **形态** · **不比**具体值） | 宪法原则 XI · [`contracts/upstream-parity.md`](./contracts/upstream-parity.md) §3 |

**唯一权威**：本 feature 的**需求与判据**以 `spec.md` 为**唯一权威**；本 plan 只**承接**它 ⇒
⇒ 数值与口径**一律以 spec 为准**（若不一致 ⇒ 以 spec 为准并回修本 plan）。

---

## Technical Context

**Language/Version**: Python **>= 3.11**（typing 构件上限 = **3.11**）· 本 feature 用到的
`contextvars` / `hashlib` / `uuid` / `json` **全部**是 **3.11** 起的标准库 ⇒ **零**新构件

**Primary Dependencies**: **零**（`dependencies = []`）⇒ 实现 MUST 只用**标准库**
（`contextvars` / `hashlib` / `uuid` / `dataclasses` / `json`）⇒ ⚠️ 上游 `langgraph` /
`langchain-core` **仅作 dev/test 依赖**（PEP 735 依赖组）⇒ **绝不进 `Requires-Dist`** ⇒
门禁 **G3 / G21 / G23** 恒绿

**Storage**: **本 feature 不实现任何持久化**（FR-019）⇒ 恢复路径**只消费** L1 的
`Checkpointer` **协议** ⇒ 首个可用实现属 **B14F1 / M3**（`MemorySaver`）⇒ ⇒ 本 feature 的
测试用**桩**（记录调用的测试替身）⇒ ⇒ 契约见 [`contracts/checkpoint-contract.md`](./contracts/checkpoint-contract.md)

**Testing**: **pytest**（既有）· 差分探针 `tests/differential/parity_probe.py`（既有 · **只增能力**）·
上游缺席即 **skip**（既有纪律）

**Target Platform**: **跨平台**（Linux / macOS / Windows）⇒ MUST **NOT** 依赖 POSIX 专有语义
⇒ ⚠️ `uuid4()` 在 Windows 上同样可用（`os.urandom` 支撑）⇒ ⇒ **零**平台分支

**Project Type**: **library**（Python 包 · 图运行内核）

**Performance Goals**: **本 feature 不新增性能指标** ⇒ 中断路径的额外开销 = **每个节点一次
`ContextVar.set/reset`** + **每次挂起一次 `blake2b`**（16 字节摘要）⇒ ⇒ **O(1)** ⇒ ⇒
**MUST NOT** 引入 O(n²) 的扫描 ⇒ ⇒ 恢复时的**快照读取**是 **1 次** `get_tuple`（**上游同款** · E-22）

**Constraints**: 零第三方依赖 · 零环境变量 · 零出站 · **L1 的 20 符号面零改动** ·
**门面的 7 符号面零改动** · `SuperStepResult` **四字段零改动** · L2 **只依赖 L1**（ARCH-1）

**Scale/Scope**: 单次运行的**节点数**沿用 B7F1 / B12F1 的口径 ⇒ **本 feature 不新增规模维度**
⇒ 中断集合的大小 = **被中断的节点数**（≤ 单轮任务数）⇒ ⇒ 恢复时的匹配是 **O(挂起数)**

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 通过项（逐条 · 原则 I–XII）

| 原则 | 检查 | 结论 |
|---|---|---|
| **I · 零 LangSmith** | 零环境变量读取 · 零出站 | ✅ 本 feature **零**环境变量（`uuid4` 走 `os.urandom`，**非**环境变量）· **零**网络调用 |
| **II · 内核纯净** | 零 `langchain` / `langchain-core` import | ✅ 生产代码**零**第三方 import；上游**只**在差分测试侧 |
| **III · 验收契约优先** | `harness/demo/target.py` 原样可跑 | ✅ 本 feature **零**改动 `target.py` ⇒ 契约门禁恒绿（C4 / C6 / C8 零破坏 · SC-019）⇒ ⚠️ **但**「**跑一遍固定脚本**」在 M1 **物理不可达成**（需 `compile()` / `invoke()` = B7F2 / B7F3 · M2）⇒ ⇒ **登记项 V-2 / V-3** |
| **IV · 可诊断性** | 失败信号 MUST 暴露**结构化属性** | ✅ `InterruptError.reason`（**封闭 5 码**）⇒ 上层**无须解析消息** |
| **V · 人工验收** | 人工验证记录 | ⚠️ **登记项 V-1 / V-2 / V-3**（「恢复侧真跑一轮」·「fake 模型跑通固定脚本一轮」·「真实模型再跑一遍」**物理不可达成** ⇒ 偏离登记 + **一次**发起者追认）⇒ ⇒ **已达成部分**（本 feature 自身的**挂起侧**人工验证 · 走 L2 入口）**照常**做 |
| **VI · 规格驱动** | 有 spec · tasks 可逐条勾选 | ✅ 本 feature 的 spec / plan / research / data-model / contracts / quickstart **齐备** |
| **VII · 职责边界** | 内核提供**原语** · freechain 做 agent 装配 | ✅ 本 feature **零** UI / 通知 / 审批工作流（承接 **D-6**） |
| **VIII · 证据与术语** | 新增结论带来源标记 | ✅ 上游锚点带 **版本 + `路径:行号`** · 行为断言带**实测**（E-1…E-26） |
| **IX · 依赖许可证与商标** | 无 AGPL / SSPL / Elastic-2.0 · 无第三方商标 | ✅ 零新增依赖 ⇒ 许可证白名单判定**不变** |
| **X · 文档合规** | `THIRD_PARTY_NOTICES` / API 兼容矩阵 | ✅ **本 feature MUST 更新** README「API 兼容矩阵」的 `interrupt` **那一行**（由「**中断 / 恢复行为待 B10F1 交付**」改为「**中断 / 恢复行为已落地**（B10F1）」）⇒ ⇒ 门禁 **G19 / G8** 恒绿（**FR-026 / SC-022** · `tasks.md` **T054**）；⚠️ `THIRD_PARTY_NOTICES` **零新增行**（本 feature **零**新增第三方代码）；新增的 L2 符号**不进**兼容矩阵（B12F1 裁定 13）⇒ ⇒ 门禁 7 在本 feature **可达成** ⇒ ⇒ **不**登记偏离 |
| **XI · 上游优先** | 上游有答案 ⇒ 照抄 | ✅ **17 条**语义点逐条对照 · 只在 **X-1…X-5** 分叉并登记 · 差分场景 **DI-01…DI-08**（**`DI-` 前缀**）|
| **XII · 最优设计优先** | 层次对应优先于容器对应 | ✅ `__interrupt__` **不进 `state`** · `SuperStepResult` **不加字段** · 调度账本**一等**（不塞 `metadata`） |

### ⚠️ 登记项（**偏离登记 + 发起者追认**）

| # | 类别 | 内容 | 处置 | 追认 |
|---|---|---|---|---|
| **PR-1** | **spec 自相矛盾**（**非**门禁偏离 · **非**L1 冻结面） | spec **H-5 ⑤** 要求「恢复 MUST 重建调度状态」· 而 spec **裁定 9 / FR-018** 的**读侧契约**只有 `.snapshot` + `.pending_writes` **两个**属性 ⇒ ⇒ **调度账本无处可取** ⇒ ⇒ 恢复后的**后续轮**触发判定失效 | ✅ **回修 spec 裁定 9 + FR-018**：读侧契约**增**第三个具名属性 **`.scheduler`**（**调度账本**）⇒ ⇒ **L1 零改动**（`StateSnapshot` **不加**字段）⇒ ⇒ 与澄清轮 **Q3** 的拍板（「B10F1 不破 L1 冻结面」）**一致** ⇒ ⇒ **不需要**发起者追认 ⇒ ⇒ B14F1 的实现面**同步**落进 [`contracts/checkpoint-contract.md`](./contracts/checkpoint-contract.md) | **不需要**（**不是** L1 冻结面 · **不是**门禁偏离）⇒ 但 MUST 在本 plan **如实登记**（research **PR-1**） |
| **PR-6** | **范围变更**（**非**门禁偏离 · **非**L1 冻结面） | 2026-11-13 分析轮补齐 **4** 条**判据级覆盖缺口**（SC-015 的「按 id 映射恢复**成功**」半边 · FR-013 ⑦「dict 非 map」· 补记 F-2「resume 与 update 并存」· FR-010「跨运行不得持有现场」）**+ 1** 条语义补齐（FR-013 末行「**会话连续**」）⇒ ⇒ **测试**行数 **640 → 680** ⇒ ⇒ **合计 1,160 → 1,200**（**+40**） | ✅ **登记范围变更**（`tasks.md` §行数预算表 · **PR-6**）⇒ ⇒ **实现**行数**不变**（会话连续的读写并入 T010 的既有预算）⇒ ⇒ ✅ **发起者已确认**（**2026-11-13 分析轮** · **并入 V-1 的那一次追认**）⇒ ⇒ ⇒ ✅ **立项书 §5.2 已同步**（2026-11-13 分析轮 · **发起者授权本轮回修代为同步** ⇒ B10F1 行 1,160 → **1,260** · 合计 31,220 → **31,320** 行）⇒ ⇒ ⚠️ **除**该**行数**同步外，本 feature **MUST NOT** 自行改立项书的**其余**内容 | ✅ **已确认**（**不是**门禁偏离 ⇒ **不**消耗「追认次数 ≤ 1」的额度 —— 它**并入** V-1 的那一次追认）⇒ 但 MUST 在本 plan **如实登记**（research **PR-6**） |
| **PR-7** | **范围变更**（**非**门禁偏离 · **非**L1 冻结面） | 2026-11-13 分析轮**实测**发现 **3** 条**测试级覆盖缺口**（**SC-008**「真异常优先」**只有实现任务 · 无测试** · **FR-013 末行**「会话连续」**只有实现任务 · 无测试**（PR-6 只补了实现面）· **SC-019**「契约门禁」只由 T051 兜底 · **无逐条核对**）⇒ ⇒ ⇒ 新增 **3** 条测试任务（**T056 / T057 / T058**）⇒ ⇒ **测试**行数 **680 → 740** ⇒ ⇒ **合计 1,200 → 1,260**（**+60** · +5.0%） | ✅ **登记范围变更**（`tasks.md` §行数预算表 · **PR-7**）⇒ ⇒ **实现**行数**不变**（**只加测试**）⇒ ⇒ ✅ **发起者已确认**（**2026-11-13 分析轮** · **并入 V-1 的那一次追认**）⇒ ⇒ ⇒ ✅ **立项书 §5.2 已同步**（1,160 → **1,260** · 合计 31,220 → **31,320** 行） | ✅ **已确认**（**并入** V-1 的那一次追认 ⇒ **追认次数仍为 1 次**）⇒ 但 MUST 在本 plan **如实登记**（research **PR-7**） |
| **PR-8** | **破冻结面清单不完整**（**非**门禁偏离 · **非**L1 冻结面 · **判据零放宽**） | 破冻结面回溯修订清单 **T-1** 初版只登记 `runtime.__all__` 的 **3 处**代码断言 ⇒ ⇒ **2026-11-13 分析轮实测**（在沙箱里按 T-005 / T-018 / T-019 模拟改动并跑既有测试）发现**另 3 处**既有冻结断言**必红**：④ `test_read_contract.py::test_i9_the_reading_layer_adds_no_new_error_type`（`runtime.errors` 的 `__all__` **精确元组** + AST **类清单**）⑤ `test_facade.py::TestInterrupt::test_raises_not_implemented`（门面 `interrupt` 恒抛 `NotImplementedError`）⑥ `test_superstep_concurrency.py` 里 `assert "NotImplementedError" in primitives`（**仅靠** docstring 残留字符串**侥幸通过**）⇒ ⇒ ⇒ 按现 tasks 实施 ⇒ **pytest 必红** ⇒ ⇒ 违反「MUST NOT 写**永久红**的 CI」 | ✅ **扩容破冻结面清单**为 **6 处**（spec §1.1 **+3 行** · spec §5 **+3 行** · 本表 **+3 行** · tasks **T012-a**（第 ④ 处）+ **T012-b**（第 ⑤⑥ 两处）⇒ ⇒ **2026-11-13 分析轮第二轮**：**T012 按「落地后可判定性」拆为 T012-a（①–④ · Phase 2）+ T012-b（⑤⑥ · 紧随 T019）** ⇒ ⇒ **六处 MUST 同改**）⇒ ⇒ **三处均属「上游无此项 ⇒ 必须自研区 ③」⇒ 零行为面偏离** ⇒ ⇒ ⇒ **不**进偏离登记表（X-1…X-5 仍为 5 项）⇒ ⇒ ⇒ **判据零放宽**（全部改成「集合相等 / 更具体的断言」）⇒ ⇒ ⇒ **发起者追认**（**并入 V-1 的那一次** ⇒ 追认次数仍为 1 次 · 宪法 E-6） | ✅ **需要发起者追认**（**并入** V-1 的那一次追认 ⇒ **追认次数仍为 1 次**）⇒ 但 MUST 在本 plan **如实登记**（research **PR-8**） |
| **PR-9** | **破冻结面清单在实施期再漏一处**（**非**门禁偏离 · **非**L1 冻结面 · **判据零放宽**） | 按本 feature 的落地形态改源码后跑既有测试 ⇒ **又发现 1 处**既有冻结断言**必红**（`tests/runtime/test_superstep_purity.py::test_importing_the_kernel_has_no_side_effects` —— 断言 `superstep.__all__` == **一份内联的 6 项精确列表**）⇒ ⇒ 破冻结面清单 **6 处 → 7 处** ⇒ ⇒ 违反「MUST NOT 写**永久红**的 CI」 | ✅ **扩容破冻结面清单为 7 处**（spec §1.1 **+1 行** · spec §5 **+1 行** · plan §破冻结面表 **+1 行** · tasks **T012-a** **+1 处** · **新增** `tests/runtime/_runtime_export_manifest.py` 作**单一事实源**）⇒ ⇒ 该处**属「上游无此项 ⇒ 必须自研区 ③」⇒ 零行为面偏离** ⇒ ⇒ **不**进偏离登记（X-1…X-5 仍为 5 项）⇒ ⇒ **判据零放宽**（改成「**集合相等**」）⇒ ⇒ **发起者追认**（**并入 V-1 的那一次** ⇒ 追认次数仍为 1 次 · 宪法 E-6） | ✅ **需要发起者追认**（**并入** V-1 的那一次追认 ⇒ **追认次数仍为 1 次**）⇒ 但 MUST 在本 plan **如实登记**（research **PR-9**） |
| **PR-10** | **范围变更（实施期实测超支 · **非**门禁偏离 · **非**L1 冻结面）** | 实施期**实测**的行数 = **实现 1,091 / 测试 1,854 ⇒ 合计 2,945**（预算 **520 / 740 ⇒ 1,260**）⇒ ⇒ **超 +1,685 行（+134%）** ⇒ ⇒ 构成：① **T-1 的 7 处**冻结断言回溯修订（含**单一事实源** `tests/runtime/_runtime_export_manifest.py`）② **PR-8 / PR-9** 的**实测化**要求（**必须逐条**回溯修订 ⇒ **不可省**）③ 差分探针的**两段式**能力 + **``interrupt-shape``** 口径 + **8** 个 `DI-` 场景（`parity_probe.py` **+544**）④ 本 feature 的 **6** 个测试文件（**1,288**）+ **桩** checkpointer + **会话连续**路径 ⇒ ⇒ **零**功能删减 | **范围膨胀** ⇒ ⇒ 违反「MUST NOT 悄悄超支」 | ✅ **如实登记超支**（tasks §行数预算表 · **实施期实测**列）⇒ ⇒ **由发起者在 V-1 的那一次追认中一并追认**（**不**新增追认次数）⇒ ⇒ **立项书 §5.2 的 B10F1 行 MUST 同步为 2,945**（**由发起者拍板后**执行 ⇒ ⇒ **本 feature MUST NOT** 自行改立项书） | ⬜ **待发起者追认**（**并入** V-1 的那一次追认 ⇒ **追认次数仍为 1 次**）⇒ 但 MUST 在本 plan **如实登记**（research **PR-10**） |
| **PR-4** | **spec 落点与门禁 G25 冲突**（**非**门禁偏离 · **非**L1 冻结面） | spec §0 / Key Entities / Assumptions 8 说「`interrupt()` 的**实现体**在 `src/freegraph/_primitives.py`」· 而 tasks T019 说「在 `_primitives.py` 惰性 import `freegraph.runtime._interrupt`」⇒ ⇒ 二者**互斥** ⇒ ⇒ **更关键**：**两个口径都会被门禁 G25 判红**（**实测**）—— 层注册表 §1 把 `_primitives.py` 登记为 **L2 单文件条目**、把 `runtime/` 登记为**另一个 L2 目录条目** ⇒ 按 §0.2 规则 3 的「模块定位口径」，二者**互相 import = 跨注册表条目的同层 import = 违规** ⇒ ⇒ **实测两个方向都 FAIL**（`_primitives.py` → `runtime/` · `runtime/superstep.py` → `_primitives.py` · **函数体内的惰性 import 同样判红** —— 门禁扫 AST） | ✅ **回修 spec**（§0 表格「架构层」+「门禁约束（G25）」两行 · Key Entities · Assumptions 8 · Out of Scope 第 15 条）⇒ ⇒ **唯一合法形态** = 「机制整体住在 `runtime/_interrupt.py`（**L2 目录条目内**）· 门面 `src/freegraph/graph.py` 用**模块级** `ImportFrom` **直接转出**（`facade-L1-L3` 例外）· `_primitives.py` **只留 `Send`**、**MUST NOT** import `runtime/`」⇒ ⇒ **实测**：G25 **PASS** + 门面的 G14 / G15 / G16 / G18 与架构门禁 **150 passed** ⇒ ⇒ **L1 零改动** ⇒ ⇒ **判据零放宽**（G25 一字未改 —— 本回修恰恰是**让实现合规**）⇒ ⇒ **不需要**发起者追认 ⇒ ⇒ 配套：`tasks.md`（T002 / T019 / **T055** 门禁核对）· `contracts/interrupt-resume-contract.md` §1 / §4 · `contracts/upstream-parity.md` §2 · `research.md` **DR-13** + §4 **PR-4** | **不需要**（**不是** L1 冻结面 · **不是**门禁偏离 · **判据零放宽**）⇒ 但 MUST 在本 plan **如实登记**（research **PR-4**） |
| **V-1** | **门禁项的不可达成**（宪法 v1.6.0） | **人工门禁**的「**恢复侧真跑一轮**」⇒ 根因 = 可用 saver 属 **B14F1 / M3** ⇒ 本 feature 按里程碑**不**交付其前置能力 | ✅ ① `plan.md` 本表登记（四要素齐备）② `tasks.md` 放一条**阻断合入**的**追认任务** ③ **追认文字**落 `harness/verification/B10F1/manual-verification.md` | **发起者本人**（**未追认前 MUST NOT 合入** · **MUST NOT** 由实现者代签）· ⚠️ 澄清轮 **Q4 · 发起者拍板** |
| **V-2** | **门禁项的不可达成**（宪法 v1.6.0） | **自动门禁**（门禁 4）+ **原则 V 第 1 轮**：「**fake / 伪模型跑通 MVP 验收基线的一轮**」⇒ 根因 = 固定脚本需 `compile()` + `invoke()`（`harness/demo/target.py:158,168`）= **B7F2 / B7F3 · M2** ⇒ 本 feature 在 **M1** 按里程碑**不**交付其前置能力 ⇒ ⇒ **已达成部分**（本 feature 自身的挂起侧人工验证 · 走 L2 入口）**照常**做 ⇒ ⇒ **MUST NOT** 写**永久红**的 CI | 偏离登记 + 发起者追认（**打包进 V-1 的那一次** ⇒ 追认次数仍为 **1**）· 承接方 **B7F3 / M2**（下游承接 **D-8**）| **发起者本人**在 `harness/verification/B10F1/manual-verification.md` 落追认文字 + 确认 + 日期（**未追认前 MUST NOT 合入** · **MUST NOT** 由实现者代签）· ⚠️ **2026-11-13 分析轮拍板**（登记档位 **A**）|
| **V-3** | **门禁项的不可达成**（宪法 v1.6.0） | **人工门禁**（门禁 5）+ **原则 V 第 2 轮**：「**真实模型再跑一遍**」⇒ 根因同 **V-2**（固定脚本需 `compile()` + `invoke()` = B7F2 / B7F3 · **M2**）⇒ ⇒ **已达成部分**同 **V-2** ⇒ ⇒ **MUST NOT** 写**永久红**的 CI | 偏离登记 + 发起者追认（**同一次**打包 ⇒ 追认次数仍为 **1**）· 承接方 **B7F3 / M2**（下游承接 **D-8**）| 同 **V-2**（**同一次**追认打包 ⇒ 追认次数仍为 **1 次**）|
| **V-4** | **门禁项的不可达成**（宪法 v1.6.0） | **契约门禁**（门禁 3）的「**`harness/demo/target.py` 原样可跑（真跑）**」这一部分 ⇒ 根因 = `target.py` 需 `compile()` + `invoke()` = **B7F2 / B7F3** · **M2** ⇒ ⇒ **M1 物理不可达成** | ① **只读基准零改动**照常执行（门禁 **G29** ①）；② **验收脚本集**在 **G29** ② 的**失败来源分级**下判为「**环境未就绪** ⇒ 通过」（⇒ **MUST NOT** 写永久红 CI）；③ **C4** 回归恒绿；④ **C8** 挂载点**保持** `not-landed · owner=B8F1`（**不**伪装成 `landed`）；⑤ **判据零放宽** ⇒ ⇒ **G29 三条判定全部可判定且恒绿** · 偏离登记 + 发起者追认（**同一次**打包 ⇒ 追认次数仍为 **1**）· 承接方 **B7F3 / M2**（下游承接 **D-3**）· 承接机制 = B7F3 落地 `invoke()` 后，在 B7F3 的 `manual-verification.md` 补上「**`target.py` 原样真跑一轮**（fake 模型轮）」的**实测输出** ⇒ ⇒ 与 **V-2**（门禁 4 的 fake 轮）**同棒承接** 偏离登记 + 发起者追认（**同一次**打包 ⇒ 追认次数仍为 **1**）· 承接方 **B7F3 / M2**（下游承接 **D-3**）| **发起者本人**在 `harness/verification/B10F1/manual-verification.md` 落追认文字 + 确认 + 日期（**未追认前 MUST NOT 合入** · **MUST NOT** 由实现者代签）· ⚠️ **2026-11-13 分析轮拍板**（登记档位 **A**）|

### 破冻结面的回溯修订清单（**T-1** · **拆分而不删** · **共 6 处**）

> ⚠️ **2026-11-13 分析轮实测扩容（PR-8）**：初版只登记了 `runtime.__all__` 的 **3 处**代码断言
> ⇒ ⇒ **实测**发现**另 3 处**既有冻结断言会因本 feature 落地而**必红**（行 3–5）⇒ ⇒ ⇒ 按现 tasks
> 实施 ⇒ **pytest 必红** ⇒ ⇒ 违反「MUST NOT 写**永久红**的 CI」⇒ ⇒ ⇒ **六处 MUST 同改**
> （只改一处 ⇒ **必红**）⇒ ⇒ **判据零放宽**（全部改成「集合相等 / 更具体的断言」）。
>
> ⚠️ **2026-11-13 实施期实测再扩容（PR-9）**：按本 feature 的落地形态改源码后跑既有测试 ⇒
> **又发现 1 处**必红（`tests/runtime/test_superstep_purity.py` 的 `superstep.__all__`
> **精确列表**）⇒ ⇒ **清单 6 处 → 7 处**⇒ ⇒ **七处 MUST 同改**⇒ ⇒ **判据零放宽**。
> ⇒ ⇒ 这是宪法 v1.11.0「冻结断言清单 MUST 实测化」的**第二次**触发 ⇒ ⇒ **清单以**实测**为准**。

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| **B12F1 `tasks.md` T072** 的「`freegraph.runtime.__all__` 的符号数 == **20**」**+** **三处**真正会红的**代码断言**（⚠️ 初版只登记了 ① —— **实测**另有 ② ③ ⇒ ⇒ 实现后 **pytest 必红** ⇒ 违反「MUST NOT 写**永久红**的 CI」）：① `tests/runtime/test_command_purity.py:255` ② `tests/runtime/test_superstep_concurrency.py:597` ③ `tests/runtime/test_read_contract.py:80` + `:547` + `:550` | ① `specs/b12f1-concurrency-errors/tasks.md` **T072** ⇒ 改为「与本 feature 的 `runtime.__all__` 清单**集合相等**」（**不硬编码数字** · 与该任务对 L1 符号面的既有做法**同款**）② **三处**代码断言 ⇒ 同一改法（**断言集合** · **不**硬编码 23）③ `test_command_purity.py` / `test_read_contract.py` 的**函数名与 docstring**里的「twenty symbols」/「== **20**」**同步** | **拆分而不删**（保留「符号面**零意外新增**」的判据形态 · 只去掉硬编码数字）⇒ ⇒ 新增的 3 个符号是**本 feature 的交付物**（契约 §1）⇒ ⇒ 判据**未放宽**（仍是「集合相等」而非「≥ 20」） | 追认文字落 `harness/verification/B10F1/manual-verification.md`（**并入** V-1 的那一次追认 ⇒ **追认次数仍为 1 次**） |
| **`freegraph.runtime.errors` 的符号面 + 异常类清单**（`__all__` **精确 7 元组** + `FreegraphError` 子类**精确清单** = 3 个） | `tests/runtime/test_read_contract.py:313-338`（`test_i9_the_reading_layer_adds_no_new_error_type`）⇒ 改为「`errors.__all__` **集合相等**（**允许** `InterruptError`）」+「`FreegraphError` 子类清单**集合相等**（**允许** `InterruptError`）」 | **拆分而不删**（保留「零意外新增」的判据形态）⇒ ⇒ ⚠️ **判据零放宽** ⇒ ⇒ ⚠️ **实测**：**无论** `InterruptError` 是否写进 `errors.__all__` ⇒ **都必红**（第二段断言 AST 类清单） | 同上（**并入** V-1 的那一次） |
| **门面 `interrupt` 的「未接线」测试** | `tests/facade/test_facade.py:315-330`（`TestInterrupt::test_raises_not_implemented`）⇒ 改为「**接线后** 抛 `InterruptError(reason="not_in_run")` · **不再**抛 `NotImplementedError`」⇒ 同步该类的 **docstring / 类名** | **拆分而不删**（保留「位置 / 关键字两种形态走**同一分支**」的判据形态）⇒ ⇒ ⚠️ **判据零放宽**（断言**更具体**）⇒ ⇒ ⚠️ **实测**：接线后**必红** | 同上（**并入** V-1 的那一次） |
| **`superstep.__all__` 的「精确列表」**（**PR-9** · **实施期实测**新增） | `tests/runtime/test_superstep_purity.py:122-146`（`test_importing_the_kernel_has_no_side_effects`）⇒ 改为「**与清单集合相等**」（清单 = `tests/runtime/_runtime_export_manifest.py` 的 `SUPERSTEP_EXPORT_SYMBOLS` · **单一事实源**）⇒ ⇒ 同步该测试的**函数名 / docstring**（不再暗示「恰为 6 项」） | **拆分而不删**（保留「符号面**零意外新增**」的判据形态 · 只去掉硬编码清单）⇒ ⇒ **判据零放宽**（仍是「**集合相等**」⇒ **不是**「⊇」）⇒ ⇒ 该断言**同时**守「导入调度内核**无副作用**」⇒ ⇒ 那两条**保留** | 同上（**并入** V-1 的那一次） |
| **`_primitives.py` 的「未接线守卫」** | `tests/runtime/test_superstep_concurrency.py:790-795`（`assert "NotImplementedError" in primitives`）⇒ 改为「`_primitives.py` **只留 `Send`**（`"def interrupt" not in primitives`）」的**源码文本**断言 ⇒ 同步该测试的 **docstring / 命名** | **拆分而不删**（保留「占位**必须**被接线掉」的判据形态）⇒ ⇒ ⚠️ **判据零放宽**（新判据**更强**）⇒ ⇒ ⚠️ **实测**：当前**仅靠** docstring 残留字符串**侥幸通过**；按 **PR-4** 删实现体 + 清理 docstring 后**必红** | 同上（**并入** V-1 的那一次） |

> ⚠️ **契约侧环节（补齐 · 2026-11-13 分析轮第二轮 · 宪法 v1.8.0「破冻结面的三条」第 ① 条的三个环节）**：
> **契约侧**另有 **8 处**文档记载「`freegraph.runtime.__all__` **仍 20** / **零改动**」
> （`b12f1/concurrency-contract.md:20,:32` · `b7f4/superstep-multisource-contract.md:15,:34,:45` ·
> `b9f1/command-contract.md:14,:26` · `b7f1/superstep-contract.md:15,:26`）⇒ ⇒ **不回溯修订**
> （**理由 = 宪法原则 VIII「已发布的事实 MUST NOT 改写」** —— 它们是**各 feature 交付当时的历史记录**，
> 而**不是**活约束 ⇒ **≠「漏登记」**）⇒ ⇒ **清单至此穷举**（**契约 + spec + 冻结断言** 三环节齐备）
> ⇒ ⇒ **判据零放宽**（6 处冻结断言的处置**一字不改**）。
>
> 📌 **单一事实源**：**spec §5**（`specs/b10f1-interrupt-resume/spec.md`）是本清单的**唯一权威**
> ⇒ ⇒ 本 plan 的表**只登记处置差异**，**MUST NOT** 另抄一份逐字内容 ⇒ ⇒ 修订时**先改 spec**。

### 门禁编号纪律

- 本 feature **不新增**门禁编号（**只引用**既有 **G1–G30**）⇒ ⇒ 编号集合**不变** ⇒ ⇒ **G7 / G8 /
  G16 / G19 / G21–G30** 恒绿 ⇒ ⇒ **「MUST NOT 新增门禁编号」**（跨 feature 承接通则）**守住** ✓。
- 本 feature **依赖**的门禁：**G4**（零环境变量 + 零出站）· **G7**（L1 符号面 == 20）· **G8** /
  **G16** / **G19**（API 快照 / 兼容矩阵）· **G21 / G22 / G23**（依赖闭包 / 隔离 / 许可证）·
  **G24**（配置层）· **G25**（导入图单向 · ARCH-1）· **G26 / G27**（零出站）· **G29**（契约门禁载体）·
  **G30**（全仓署名头 · **新文件 MUST 带署名头**）· **G19 / G8**（兼容矩阵覆盖门面 7 符号 ·
  严格比对）· **G29**（契约门禁载体 · 只读基准 diff + 验收脚本集**失败来源分级** + C4 / C8 挂载点）。
- ⚠️ **门禁 G25（导入图单向）**在本 feature 是**硬约束**（**不是**「跑一下看看」）⇒ ⇒ 本
  feature 的**实现落点**被它唯一确定（**PR-4**）⇒ ⇒ **实现期 MUST 先跑** `harness/scripts/
  gates/gate_G25_import_graph.py`（见 `tasks.md` **T055**）⇒ ⇒ **MUST NOT** 让 `_primitives.py`
  import `runtime/`（**实测判红**）。

### 设计后复核（Phase 1 后 · 模板要求「Re-check after Phase 1 design」）

| 项 | 复核结果 |
|---|---|
| **原则 XI**（上游优先） | ✅ 设计后复核：**DR-01…DR-13** 逐条对照上游 ⇒ **零**未登记的分叉 ⇒ 偏离总数仍为 **5**（X-1…X-5） |
| **原则 XII**（最优设计） | ✅ `__interrupt__` **不进 `state`** · `SuperStepResult` **不加字段** · 调度账本**一等** · `InterruptResult` **只 4 字段**（澄清轮 Q1）⇒ ⇒ **无**「在既有设计上做局部最优」的形态 |
| **ARCH-1** | ✅ L2 **只** import L1 ⇒ ⇒ 门禁 **G25** 恒绿（**导入图断言**可判定 · SC-006）⇒ ⇒ ⚠️ **G25 的「跨注册表条目同层 import」约束**把 `interrupt()` 的落点**唯一确定**为「机制在 `runtime/_interrupt.py`（**L2 目录条目内**）· 门面 `graph.py` **模块级**转出 · `_primitives.py` **只留 `Send`**」（**PR-4** · **实测** PASS）|
| **L1 零改动** | ✅ `StateSnapshot` / `Interrupt` / `GraphInterrupt` / `Command` / `RunConfig` / `Checkpointer` **一字不动** ⇒ ⇒ G7 / G8 / G16 / G19 恒绿（SC-007） |
| **门面零改动** | ✅ `freegraph.graph` 的 **7** 个导出名**一字不动**（`interrupt` 已在其中）⇒ ⇒ G15 / G16 / G19 恒绿 |
| **spec 一致性** | ⚠️ **PR-1** ⇒ **已回修 spec 裁定 9 / FR-018** ⇒ ⇒ ⚠️ **PR-8** ⇒ **已回修 spec §1.1 / §5**（破冻结面清单扩容为 **6 处**）⇒ ⇒ ⚠️ **PR-7** ⇒ **已登记范围变更**（+60 行 · **发起者已确认**）⇒ ⇒ spec 与 plan **一致** ⇒ ⇒ **零**未闭合矛盾 |

---

## Project Structure

### Documentation (this feature)

```text
specs/b10f1-interrupt-resume/
├── plan.md              # 本文件（/speckit.plan 输出）
├── spec.md              # 唯一权威（/speckit.specify + /speckit.clarify 输出）
├── research.md          # Phase 0 输出（DR-01…DR-13 · F-01…F-13 · PR-1…PR-4）
├── data-model.md        # Phase 1 输出（EM-1…EM-11 · V-1…V-14 · SM-1…SM-7 状态迁移（`SM-` 前缀 · 与「破冻结面 T-1」区分））
├── quickstart.md        # Phase 1 输出（§0…§14 可跑验收指南）
├── contracts/
│   ├── interrupt-resume-contract.md   # 本 feature 的唯一权威契约（§1…§9）
│   ├── checkpoint-contract.md          # B10F1 ⇄ B14F1 的接缝（读侧 / 写侧）
│   └── upstream-parity.md              # 上游对照的执行细则（§1…§5）
├── checklists/
│   └── requirements.md       # 规格质量清单（24/24）
└── tasks.md             # Phase 2 输出（/speckit.tasks —— **本次生成**）
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/            # L1 · **本 feature 零改动**
│   ├── types.py              # Interrupt / Command / RunConfig / StateSnapshot（只消费）
│   ├── errors.py             # GraphInterrupt（只消费）
│   └── protocols.py          # Checkpointer（只消费 · 载荷形状由本 feature 的契约冻结）
├── runtime/              # L2 · **本 feature 的主战场**
│   ├── __init__.py           # 改：__all__ 20 → 23（+ InterruptResult / InterruptError / run_graph）
│                              #     ⇒ 附带：模块 docstring 里的「契约层仍 18 个符号」⇒ **20**（实测）
│   ├── errors.py             # 改：新增 InterruptError（.reason 封闭 5 码）
│   ├── superstep.py          # 改：新增 InterruptResult + run_graph + SchedulerState 两个方法
│   │                         #     + _bind 挂载「任务级」现场（1 处）
│   ├── _interrupt.py         # 新增（私有 · **L2 目录条目内**）：两级 ContextVar
│   │                         #     + **interrupt() 的实现体** + .id 生成 + 任务现场
│   └── _concurrency.py       # **零改动**（并发内核不动）
├── _primitives.py        # 改：**删掉 interrupt 的实现体**（**只留 `Send`**）
│                         #     ⇒ **零** import runtime/（**G25** · 跨条目同层 import ⇒ 判红）
└── graph.py              # 改（**仅 import 行**）：模块级 from .runtime._interrupt import interrupt
                           #     ⇒ 门面 7 符号面**零改动**（G14 零实现体 / G15 / G16 / G19 恒绿）

tests/
├── runtime/
│   ├── test_interrupt_basic.py        # 新增：US1（挂起 + 结果键）+ T056（真异常优先）
│   ├── test_interrupt_resume.py       # 新增：US2 / US3 / US4（恢复 / 从头重跑 / 经由 checkpointer）+ T057（会话连续）
│   ├── test_interrupt_errors.py       # 新增：US2 的失败信号族（封闭 5 码中的 4 个 · `ambiguous_resume` 在 T052）
│   ├── test_interrupt_checkpoint.py   # 新增：US4 的「桩」与读侧 / 写侧契约
│   ├── test_interrupt_contract.py     # 新增：结构纪律（导出面 / 字段数 / 层依赖 / 零依赖）
│   ├── test_command_purity.py         # 改：runtime.__all__ 的硬编码 20 → 集合相等（T-1 ①）
│   ├── test_superstep_concurrency.py  # 改：runtime.__all__ 集合相等（T-1 ②）+ 未接线守卫回溯修订（T-1 ⑥）
│   └── test_read_contract.py          # 改：runtime.__all__ 集合相等（T-1 ③）+ errors 符号面回溯修订（T-1 ④）
├── facade/
│   ├── test_facade.py                 # 改：TestInterrupt 的「未接线」断言回溯修订（T-1 ⑤ · T012-b）
│   └── test_facade_gates.py           # 改：docstring「契约层 18 个符号」⇒ 20（T054 附带订正②）
├── differential/
│   ├── parity_probe.py                # 改：新增 "interrupt-shape" 比较口径 + 挂 checkpointer 的能力
│   │                                 #     + freegraph 侧切 run_graph（两段式输入）
│   │                                 #     + DI-01…DI-08 八个场景（既有 43 条逐字不变）
│   └── test_parity_probe.py           # 核对：⚠️ **实测无场景数硬断言**（只遍历 _scenarios()）⇒ ⇒ **零改动**
└── contracts/test_architecture.py     # **零改动**（G25 既有断言覆盖本 feature）

docs（**文档侧改动** · 与下方「本 feature **触及**的文件」表**逐行对应**）
├── README.md                                   # 改：API 兼容矩阵的 `interrupt` 那一行（T054）
├── specs/b12f1-concurrency-errors/tasks.md     # 改：T072 的硬编码数字（T046）
└── specs/b10f1-interrupt-resume/spec.md        # 改：裁定 2 / FR-018（PR-1）等（分析轮回修）

harness/
├── features/                          # 改：接线下游承接 D-1 / D-3 / D-4 / D-7（只接线 · 逐条最小改动）
│   ├── B14F1_Checkpointer协议与MemorySaver.md
│   ├── B7F3_invoke返回完整状态.md
│   ├── B13F1_静态中断点与递归上限.md
│   └── B16F1_update_state与时间旅行.md
└── verification/B10F1/               # 新增
    ├── manual-verification.md         # 五段式 + V-1 的追认文字
    └── acceptance.py                  # 一键验收闸口
```

### ── 本 feature **触及**的文件（**表格 31 行** · 新增 **9** / 修改 **18** / 核对 **4**） ──

| # | 文件 | 动作 | 依据 | 触及点 |
|---|---|---|---|---|
| 1 | `src/freegraph/runtime/_interrupt.py` | **新增** | DR-01 / DR-02 / DR-03 | 两级 `ContextVar` · `interrupt()` 实现 · `.id` 生成 · 任务现场 |
| 2 | `src/freegraph/runtime/errors.py` | **改** | DR-05 | 新增 `InterruptError`（`.reason` 5 码） |
| 3 | `src/freegraph/runtime/superstep.py` | **改** | DR-04 / DR-06 / DR-08 | `InterruptResult` · `run_graph` · `SchedulerState.to_checkpoint/from_checkpoint` · `_bind` 挂载任务现场 |
| 4 | `src/freegraph/runtime/__init__.py` | **改** | 契约 §1 | `__all__` 20 → 23 |
| 5 | `src/freegraph/_primitives.py` | **改** | spec F-01 / **PR-4** | **删掉 `interrupt` 的实现体**（**只留 `Send`**）⇒ **零** import `runtime/`（**G25**）|
| 6 | `src/freegraph/contracts/**` | **核对** | FR-017 | **零改动** ⇒ G7 / G8 / G16 / G19 恒绿 |
| 7 | `src/freegraph/graph.py` | **改** | 契约 §1 / **PR-4** | **仅**把 `interrupt` 的 import 改为**模块级** `from .runtime._interrupt import interrupt`（`facade-L1-L3` 例外）⇒ 门面 7 符号面**零改动**（G14 / G15 / G16 / G19 恒绿）|
| 8 | `src/freegraph/runtime/_concurrency.py` | **核对** | B12F1 冻结面 | **零改动** ⇒ 并发内核不动 |
| 9 | `tests/runtime/test_interrupt_basic.py` | **新增** | US1 | 挂起 · 结果键 · `.value` / `.id` |
| 10 | `tests/runtime/test_interrupt_resume.py` | **新增** | US2 / US3 | 恢复闭环 · 从头重跑 · 多中断 |
| 11 | `tests/runtime/test_interrupt_errors.py` | **新增** | US2 | 4 个 `reason` + `not_in_run` |
| 12 | `tests/runtime/test_interrupt_checkpoint.py` | **新增** | US4 | 桩 checkpointer · 读侧 / 写侧契约 |
| 13 | `tests/runtime/test_interrupt_contract.py` | **新增** | Polish | 导出面 · 四字段 · 层依赖 · 零依赖 |
| 14 | `tests/runtime/test_command_purity.py` | **改** | **T-1** | `runtime.__all__` 的硬编码 20 → 集合相等（**T-1** 第 ① 处）|
| 15 | `tests/differential/parity_probe.py` | **改** | DR-12 / DR-13 / 差分 §3 | `"interrupt-shape"` 口径 · 挂 checkpointer 的能力 · **DI-01…DI-08**（**`DI-` 前缀** · 与既有 `D-xx` 不重号）|
| 16 | `tests/differential/test_parity_probe.py` | **核对** | 差分 §3 | ⚠️ **实测无场景数硬断言**（只遍历 `_scenarios()`）⇒ ⇒ **零改动** ⇒ ⇒ 若实施期发现硬断言再同步 |
| 17 | `harness/verification/B10F1/manual-verification.md` | **新增** | 原则 V / **V-1** | 五段式 + 追认文字 |
| 18 | `harness/verification/B10F1/acceptance.py` | **新增** | 原则 V | 一键验收入口 |
| 19 | `specs/b10f1-interrupt-resume/spec.md` | **改** | **PR-1** | 回修裁定 9 + FR-018（读侧契约增 `.scheduler`） |
| 20 | `specs/b12f1-concurrency-errors/tasks.md` | **改** | **T-1** | T072 的硬编码数字同步 |
| 21 | `harness/features/B14F1_*.md` | **改** | 承接 **D-1** | 检查点契约的兑现 + V-1 的承接 |
| 22 | `harness/features/B7F3_*.md` | **改** | 承接 **D-3** | `invoke` 接线 + L1 入参放宽 |
| 23 | `harness/features/B13F1_*.md` | **改** | 承接 **D-4** | 静态中断点的挂起载体一致 |
| 24 | `harness/features/B16F1_*.md` | **改** | 承接 **D-7** | 时间旅行与恢复路径的边界 |
| 25 | `README.md` | **改** | **FR-026** / **SC-022** | 「API 兼容矩阵」的 `interrupt` **那一行**：由「**中断 / 恢复行为待 B10F1 交付**」改为「**中断 / 恢复行为已落地**（B10F1）」⇒ ⇒ **MUST NOT** 增删行 ⇒ ⇒ 门禁 **G19 / G8** 恒绿 · ⚠️ **附带**：同章节「公开面判定口径」里的「契约层 **18** 个符号」⇒ **20**（实测为 20 · 与 `runtime/__init__.py` docstring 同处订正）|
| 26 | `tests/runtime/test_superstep_concurrency.py` | **改** | **T-1** · **PR-8** | ① `runtime.__all__` 的硬编码 20 → 集合相等（**T-1** 第 **②** 处）② `assert "NotImplementedError" in primitives` → 「`_primitives.py` **只留 `Send`**」的**源码文本**断言（**PR-8** 第 **⑥** 处）⇒ ⇒ 同步该测试的 docstring / 命名 |
| 27 | `tests/runtime/test_read_contract.py` | **改** | **T-1** · **PR-8** | ① `RUNTIME_SYMBOL_COUNT = 20` + `:547` + `:550` → 集合相等（**T-1** 第 **③** 处）② `test_i9_the_reading_layer_adds_no_new_error_type`（`:313-338`）⇒ `errors.__all__` 与 `FreegraphError` 子类清单**改集合相等**（**允许** `InterruptError`）⇒ ⇒ **PR-8** 第 **④** 处 |
| 28 | `tests/facade/test_facade.py` | **改** | **T-1** · **PR-8** | `TestInterrupt::test_raises_not_implemented`（`:315-330`）⇒ 「**接线后** 抛 `InterruptError(reason="not_in_run")`」⇒ ⇒ 同步该类的 docstring / 类名 ⇒ ⇒ **PR-8** 第 **⑤** 处 |
| 29 | `tests/contracts/test_architecture.py` | **核对** | ARCH-1 | **零改动** ⇒ ⇒ 既有断言已覆盖本 feature 的落点（G25 · 门面的模块加载面）⇒ ⇒ **零改动** |
| 30 | `tests/facade/test_facade_gates.py` | **改** | **T054** 附带订正② | docstring 里「契约层 **18** 个符号」⇒ **20**（**实测** `len(freegraph.contracts.__all__) == 20`）⇒ ⇒ **仅**文案（**零**行为影响）⇒ ⇒ **MUST NOT** 增删兼容矩阵的**行** |
| 31 | `tests/runtime/_runtime_export_manifest.py` | **新增** | **T012-a**（**PR-9** 的**单一事实源**） | L2 导出面 / `errors.__all__` / `superstep.__all__` 的**清单**（**集合** · **不硬编码数字**）⇒ ⇒ 三处既有冻结断言**共用**它 ⇒ ⇒ **不**在三处各抄一份 ⇒ ⇒ **不会漂移** |

**Structure Decision**: **单包结构**（`src/freegraph/` · L1 `contracts/` + L2 `runtime/` + 门面）⇒
沿用仓库既有分层 ⇒ ⇒ 本 feature **不新增**任何顶层目录 ⇒ ⇒ L2 的新代码落 **`runtime/_interrupt.py`
（私有 · 前导下划线）**⇒ ⇒ 与 B12F1 的 `_concurrency.py` **同款** ⇒ ⇒ **不进** `runtime.__all__`
⇒ ⇒ **不进** API 兼容矩阵 ⇒ ⇒ 门禁 **G8 / G19** 恒绿。

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **（无）** | — | 本 feature **零**门禁偏离（红线判据一律照常执行）⇒ ⇒ 登记项 **PR-1**（读侧契约增 `.scheduler`）· **PR-4**（落点与 G25 对齐）· **PR-8**（破冻结面清单扩容为 6 处 —— **判据零放宽** · 零行为面偏离）都是**本 feature 自己**的契约细化 / 合规修正（**非** L1 冻结面 ⇒ **判据零放宽**）⇒ ⇒ 登记项 **PR-6** / **PR-7** 是**范围变更**（**发起者已确认** · 并入 V-1 的那一次追认）⇒ ⇒ ⇒ **Complexity Tracking 无需填** |
