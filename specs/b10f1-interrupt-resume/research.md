# Research · B10F1 · `interrupt()` + `resume`（HITL 中断与恢复闭环）

> **输入**：`spec.md`（**唯一权威** · 裁定 1…11 + FR-001…026 + SC-001…022 + P-01…P-17 +
> E-1…E-26 + X-1…X-5 + V-1…V-4）· 宪法 **v1.11.0**（**v1.11.0 的两条补强即由本 feature 的分析轮实测触发**）· 上游 `langgraph` **1.2.11**
> （取证于 **2026-11-13** · `.venv` 内安装 · 仅**差分测试侧**使用）。
>
> **判定纪律**（宪法 **v1.9.0 原则 XI**）：每条决策 MUST 先问「上游怎么说」⇒ 上游有答案 ⇒
> **照抄**（含上游的缺陷 ⇒ 更确定的口径）⇒ 只在**必须自研区**自研并**如实登记**（spec 的
> **X-1…X-5**）。
> **形态纪律**（宪法 **v1.10.0 原则 XII**）：**内容照抄上游** + **形态取全局最优** ⇒
> 「层次对应优先于容器对应」⇒ **不**给 `SuperStepResult` 加字段（MUST NOT 塞进 `state`）。

---

## §1 现状盘点（**动手前的事实基线**）

| # | 事实 | 取证 | 影响 |
|---|---|---|---|
| **F-01** | `interrupt()` 已在门面**导出**（7 符号面之一）但**恒抛** `NotImplementedError` | `src/freegraph/_primitives.py:49-59`（`def interrupt` + `raise NotImplementedError`）· `src/freegraph/graph.py:30`（`from ._primitives import Send, interrupt`） | ⇒ 本 feature **只接线**行为，**零**门面导出面改动（门禁 G15 / G16 / G19 恒绿） |
| **F-02** | L2 已有 **`Channel.from_checkpoint(checkpoint)`**（抽象方法 + 三个子类覆写） | `src/freegraph/runtime/channel.py:150-160`（抽象）· `:273`（`LastValue`）· `:439`（`BinaryOperatorAggregate`）· `:532`（`EphemeralValue`） | ⇒ **恢复时重建通道**有现成机制 ⇒ **零新增**通道代码 |
| **F-03** | L2 已有 **`SchedulerState`**（6 个字段：`versions_seen` / `step` / `channel_versions` / `node_versions` / `dynamic_edges` / `channels`） | `src/freegraph/runtime/superstep.py:200-236` | ⇒ 恢复**必须重建**它（spec **H-5 ⑤**）⇒ ⇒ **它必须被持久化** ⇒ ⇒ **spec 的读侧契约缺一项**（见 **DR-07**） |
| **F-04** | `_run_round` 的**七个阶段**已冻结（② 任务准备 · ③ 并发执行 · ③′ 判定与落回 · ④ 写入收集 · ⑤ 写入合并 · ⑥ 收尾） | `src/freegraph/runtime/superstep.py:1040-1136` | ⇒ **恢复轮**可**直接复用** `_run_round(spec, state, triggered)`（`triggered` = 快照的 `next`）⇒ ⇒ **零改动** B12F1 的阶段表 |
| **F-05** | 节点函数的**唯一调用点**是 `_execute_node_pure`（经 `_bind` 的闭包） | `src/freegraph/runtime/superstep.py:836-856` · `:1072-1079`（`_bind`） | ⇒ 「运行期上下文」的**挂载点**唯一 ⇒ ⇒ 改动面 = **1 处** |
| **F-06** | 节点在**线程池的线程**里执行（每轮新建池 + 关闭） | `src/freegraph/runtime/_concurrency.py:181-240` | ⇒ 运行期上下文 MUST 是**线程局部**的 ⇒ ⇒ `contextvars` / `threading.local`（见 **DR-01**） |
| **F-07** | 差分探针**已有**中断支持：`expect_interrupt` · `_interrupt_payload` · `_compare_interrupts(compare="set")` | `tests/differential/parity_probe.py:104-108` · `:174-198` | ⇒ **既有 43 个场景逐字不变**（**实测** `parity_probe._scenarios()` == 43）⇒ ⇒ 新场景需要**新的比较口径**（id 两侧不同 ⇒ 见 **DR-12**） |
| **F-08** | `_compare_interrupts` 比的是 `(value, id)` **逐字** | `tests/differential/parity_probe.py:186-198` | ⇒ B10F1 的 id 由**内核**生成 ⇒ 两侧**必不同** ⇒ ⇒ **必须**新增「比形态不比值」的口径（**DR-12**） |
| **F-09** | `runtime.__all__` 当前 **20** 个符号（B12F1 T072 硬编码断言） | `src/freegraph/runtime/__init__.py:71-92` | ⇒ 本 feature 新增 3 个 ⇒ **20 → 23** ⇒ ⇒ **回溯修订 T-1**（spec 已登记） |
| **F-10** | 上游的 `map_command` 支持 `resume` **与** `update` **并存** | `langgraph/pregel/_io.py:74-78` | ⇒ **照抄**（spec 补记 **F-2**）⇒ ⇒ `update` 走**通道写入**路径 |
| **F-11** | 上游的恢复值经 `__resume__` pending write 传递，值被**包成列表**（按节点内顺序） | `langgraph/pregel/_algo.py:1301-1308`（`if not isinstance(task_resume_write, list): task_resume_write = [task_resume_write]`） | ⇒ **照抄**（**DR-10**）⇒ ⇒ 裁定 7 的「按节点内顺序匹配」有了**上游的机制依据** |
| **F-12** | 上游的 `__interrupt__` pending write 载荷 = `exception.args[0]`（**元组**） | `langgraph/pregel/_runner.py:588-591` | ⇒ **照抄** ⇒ ⇒ freegraph 的 `__interrupt__` pending write 载荷 = **元组** |
| **F-13** | 上游的恢复值**可**由「NULL 任务」的 `__resume__` write 提供（全局恢复值） | `langgraph/pregel/_algo.py:1291-1298` | ⇒ freegraph v1 **不实现**「全局恢复值」⇒ ⇒ 单值恢复按**唯一挂起中断**匹配（裁定 4） |

---

## §2 设计决策（**DR-01…DR-13**）

### DR-01 · 运行期上下文的传递机制

**Decision**：用 **标准库 `contextvars.ContextVar`** 承载「当前任务的中断现场」⇒ 落 L2 **私有**模块
`src/freegraph/runtime/_interrupt.py` ⇒ **不**进 `runtime.__all__`（⇒ F-09 的 3 个新增符号不含它）。
⚠️ **落点的唯一合法形态（PR-4 · 2026-11-13 分析轮 · **实测**）**：该模块 MUST 住在
`src/freegraph/runtime/` 这**一个注册表条目**内（与 `superstep.py` 同条目 ⇒ 互相 import **合法**）
⇒ ⇒ 门面 `src/freegraph/graph.py` 用**模块级** `ImportFrom` **直接转出**（`facade-L1-L3` 例外）
⇒ ⇒ `src/freegraph/_primitives.py`（**L2 单文件条目**）**只留 `Send`**、**MUST NOT** import
`runtime/`（**跨注册表条目的同层 import** ⇒ 门禁 **G25** 判红 · **实测**）⇒ ⇒ **DR-13**。

**Rationale**：① **上游同款** —— 上游用 `get_config()`（`langgraph/config.py:17-29`）读
**contextvar** `var_child_runnable_config`（`langgraph/types.py:950`）⇒ **照抄**；
② 节点在**工作线程**里执行（F-06）⇒ 上下文 MUST **线程局部** ⇒ `contextvars` 满足；
③ `contextvars` 对 **async** 天然友好（v2 预留）⇒ **零迁移成本**；
④ **私有模块**（前导下划线）⇒ 与 B12F1 的 `_concurrency.py` **同款** ⇒ 不进 API 兼容矩阵。

**Alternatives considered**：
- ❌ **把现场塞进 `node_input`** ⇒ 污染**状态**（节点入参是稀疏状态 · C4）⇒ 形态污染（原则 XII）⇒ 且会**进入 checkpoint** ⇒ 泄露内部状态。
- ❌ **`threading.local`** ⇒ 与 `contextvars` 同为线程局部 ⇒ 但**不可跨 async** ⇒ v2 要**重做** ⇒ 且 `contextvars` 是上游同款。
- ❌ **模块级全局字典** ⇒ **并发不安全**（同轮多节点并发执行 · B12F1）⇒ 必须加锁 ⇒ 热点。

---

### DR-02 · 两级上下文（运行级 / 任务级）

**Decision**：**两级** `ContextVar`：
① **运行级**（`_RUN`）—— 由 `run_graph` 在**整次运行**期间设置，载荷 =「**按节点名**的现场表」
（恢复值 + 先前挂起的中断载荷）；② **任务级**（`_TASK`）—— 由 `_bind._inner`（F-05）在
**每个节点执行**前设置、**执行后**复原（`token` 复位），载荷 = 该节点的「任务现场」。

**Rationale**：① **运行级**承载「跨节点」的输入（恢复值来自 pending writes ⇒ 与**节点**绑定）；
② **任务级**承载「节点内」的进度（`interrupt()` 已调用几次 · 已消费几个恢复值）⇒ ⇒
`interrupt()` 只读**任务级** ⇒ ⇒ **零**跨层查找；③ **复原** MUST 用 `ContextVar.reset(token)`
⇒ 线程池**复用线程**时**不串味**（F-06）⇒ ⇒ 零脏状态 ⇒ ⇒ **零**额外断言成本。

**Alternatives considered**：
- ❌ **单级**（只用任务级，恢复值经参数逐层传）⇒ 需改 `_run_round` 的**签名**（私有 · 可改）⇒ 但会**污染** B12F1 的阶段契约（`_run_round` 是七阶段契约的载体）⇒ ⇒ 改动面更大 ⇒ **不采纳**。
- ❌ **把现场放进 `SchedulerState`** ⇒ **调度状态**是纯调度账本 ⇒ 混入「运行期现场」⇒ 形态污染 ⇒ 且 `SchedulerState` **会被持久化** ⇒ 恢复值会**落盘**（不该落）⇒ ❌。

---

### DR-03 · `.id` 的生成与**跨恢复稳定**

**Decision**：
1. **命名空间** = `f"{node_name}:{uuid4().hex}"`（**上游同款** · E-23）⇒ **含随机量** ⇒ id **不可猜**；
2. **摘要** = `hashlib.blake2b(ns.encode(), digest_size=16).hexdigest()` ⇒ **32 位十六进制**（零第三方依赖）；
3. ⚠️ **跨恢复稳定**（spec **F-1**）**不靠约定、靠结构** ⇒ ⇒ **恢复时直接复用** pending writes 里
   那个 `Interrupt` 的 **既有 `id`** ⇒ ⇒ **零新增持久化字段**（uuid **不**落盘）。

**Rationale**：① **id 只在「首次挂起」时算一次** ⇒ ⇒ 再次挂起（恢复值不足 · 裁定 7）时**复用** ⇒ ⇒
**逐字相同**（E-17）⇒ ⇒ **F-1 结构性成立**；② **零新增持久化字段** ⇒ ⇒ 写侧契约**更小** ⇒ ⇒
B14F1 的实现面更小；③ 命名空间**含节点名** ⇒ 不同节点的 id **互不相同**（E-11）⇒ ⇒ 挂起中断**可按 id 定位**；
④ 命名空间**不含**「节点内第几次」⇒ 同一节点同一轮的多个 `interrupt()` **共享 id**（E-17）⇒ ⇒ 照抄。

**Alternatives considered**：
- ❌ **持久化 uuid**（多写一个字段）⇒ 破坏「**id 只算一次**」的简洁性 ⇒ ⇒ 写侧契约多一项 ⇒ ⇒ B14F1 多担一件事 ⇒ **不采纳**（复用既有 id 已足够）。
- ❌ **纯确定性命名空间**（节点名 + 轮次序号）⇒ id **可猜** ⇒ ⇒ 「替这次审批拍板」的**能力凭据可被推导** ⇒ ⇒ **安全语义弱于上游** ⇒ ⇒ **澄清轮 Q5 已拍板：含随机量**。

---

### DR-04 · 挂起态的**结果载体**

**Decision**：新增 **L2 的 `InterruptResult`**（**4 字段**：`state` / `interrupts` / `executed` /
`steps`）+ `as_result_dict()`（= `{**state, "__interrupt__": interrupts}`）⇒ 落
`src/freegraph/runtime/superstep.py`（与 `SuperStepResult` **同文件** ⇒ 「同类项同类承载」）。

**Rationale**：① `SuperStepResult` 的**四字段是冻结面**（B12F1 裁定 25 ②）⇒ **不**加第 5 个字段；
② `__interrupt__` **不进 `state`**（形态污染 · 裁定 25 ③）⇒ ⇒ 需要**另一个**载体；
③ **同文件** ⇒ 与 `SuperStepResult` 的**判读路径**一致 ⇒ ⇒ 零学习成本；
④ `as_result_dict()` ⇒ **本 feature 独占**「异常 → `__interrupt__` 键」的转成路径（spec 裁定 10）⇒
⇒ B7F3 只调用它（承接 **D-3**）。

**Alternatives considered**：
- ❌ **新增 `SuperStepResult` 第 5 字段** ⇒ **破冻结面** ⇒ 需追认 ⇒ ⇒ 已在澄清轮被否（spec 裁定 2 / Q1）。
- ❌ **直接返回状态字典**（上游同款）⇒ 「轮数」与「已启动节点名」**无处安放** ⇒ ⇒ SC-010 **失去载体** ⇒ ❌。

---

### DR-05 · 失败信号

**Decision**：新增 **L2 的 `InterruptError`**（`FreegraphError` 子类 · **不**继承 `ValueError`）·
带 **`.reason`**（封闭 5 码：`checkpointer_required` / `resume_value_required` /
`ambiguous_resume` / `no_pending_interrupt` / `not_in_run`）⇒ 落
`src/freegraph/runtime/errors.py`（**L2 内部 API** · 沿用 B4F1 / B5F1 的既有归属）。

**Rationale**：① L1 的 `FreegraphError` **冻结承诺**（「捕获基类即可兜住全部内核错误」）⇒
⇒ **不**抛内置 `RuntimeError`（上游同款）⇒ ⇒ **偏离登记 X-2**；② **可诊断性是一等功能**
（原则 IV）⇒ 结构化 `reason` ⇒ ⇒ 上层**无须解析消息**；③ **不**继承 `ValueError` ⇒ 用户既有的
`except ValueError` **不会**误吞（沿用 `EmptyChannelError` 的继承纪律）；④ **L1 零新增符号** ⇒
⇒ G7 / G8 / G16 / G19 恒绿；⑤ **异常对象只带 `reason`**（澄清轮 Q2）⇒ **不带**上下文。

**Alternatives considered**：
- ❌ **抛内置 `RuntimeError`**（上游逐字）⇒ 破坏 L1 的冻结承诺 ⇒ ⇒ 用户按 `except ValueError` /
  `except RuntimeError` 的既有代码**行为漂移**。
- ❌ **新增 L1 异常类** ⇒ 破 L1 符号面（20 → 21）⇒ ⇒ G7 / G8 / G16 / G19 **全红** ⇒ ⇒ 需追认 ⇒
⇒ **在 L2 落** ⇒ 零 L1 改动。

---

### DR-06 · L2 的**图级入口**（名字与签名）

**Decision**：新增 **`run_graph`**：

```
run_graph(
    spec: GraphSpec,
    input: StateDict | Command | None = None,
    *,
    state: SchedulerState | None = None,
    checkpointer: Checkpointer | None = None,
    config: RunConfig | None = None,
    max_steps: int = 10007,
    max_concurrency: int | None = None,
) -> SuperStepResult | InterruptResult
```

**Rationale**：① **既有入口一字不动**（spec 裁定 10 · B7F1 冻结面）⇒ ⇒ `run_super_step` /
`run_super_steps` 的**签名与返回类型零改动**；② 既有入口是**轮级**（纯调度 · 无输入映射 ·
无 checkpointer · 无恢复）⇒ ⇒ **图级**能力（输入映射 + checkpointer + 恢复 + 挂起/完成二分）
**另立**一个入口；③ **返回联合类型** ⇒ 「挂起」与「跑完」**两种结束方式可区分**（B12F1 裁定 24 ②）
⇒ ⇒ 上游 `invoke()` 返回**一个** dict（挂起时多一个键）⇒ ⇒ freegraph 在 L2 层用**联合类型**表达
⇒ ⇒ **门面层**再归一成 dict（B7F3 · 承接 D-3）；④ `max_steps` 缺省 **10007**（**上游同款** ·
`langgraph/_internal/_config.py:32` · B7F1 已硬编码 ⇒ **不**读环境变量）。

**Alternatives considered**：
- ❌ **给 `run_super_steps` 加 keyword-only 参数** ⇒ 返回类型要变（`SuperStepResult` → 联合）⇒
⇒ **破 B7F1 冻结面**（B12F1 增 `max_concurrency` 时只**增**参数、**未**动返回类型）⇒ ⇒ 不采纳。
- ❌ **名字用 `invoke`** ⇒ 与 B7F3 的**门面** `invoke` **同名不同层** ⇒ ⇒ 易混 ⇒ ⇒ 不采纳。

---

### DR-07 · 恢复时的**状态重建**（⚠️ **发现 spec 缺口**）

**Decision**：恢复时从 `.snapshot` 重建三样东西：
① **通道实例** —— `Channel.from_checkpoint(value)`（F-02 · **现成** ⇒ 零新增）；
② **调度账本** —— `versions_seen` / `channel_versions` / `node_versions` / `dynamic_edges`（F-03）;
③ **待跑节点** —— `.snapshot.next`（L1 **已有**字段）⇒ **显式**跑这些节点（**不走**触发判定）。

⚠️ **spec 缺口**：spec **H-5 ⑤** 要求「恢复 MUST 重建调度状态」，但 spec **裁定 9 / FR-018** 冻结的
**读侧契约**只有 `.snapshot` + `.pending_writes` **两个**属性 ⇒ ⇒ **调度账本无处可取** ⇒ ⇒
**必须回修 spec**：读侧契约**增**第三个具名属性 **`.scheduler`**（**调度账本**）。

**Rationale**：① `.snapshot.next` = 「这一步之后要执行的节点名」（L1 既有）⇒ ⇒ **不需要**用触发判定
重建下一批任务（上游同款：`prepare_next_tasks` 按 checkpoint 的 `next` 重建）⇒ ⇒ 恢复轮
**显式**跑 `next` ⇒ ⇒ 触发判定**不**被重复触发；② **调度账本必须持久化** ⇒ 恢复后的**后续轮**
触发判定要与首次运行**同款**（spec H-5 ⑤）⇒ ⇒ 它**必须**被读回 ⇒ ⇒ 读侧契约**必须**多一项；
③ `.scheduler` 作为**读侧契约的第三个属性** ⇒ ⇒ **L1 零改动**（`StateSnapshot` **不加**字段）⇒
⇒ **澄清轮 Q3 的拍板（「B10F1 不破 L1 冻结面」）仍然成立** ✓ ⇒ ⇒ 不需要为它消耗追认名额。

**Alternatives considered**：
- ❌ **给 L1 的 `StateSnapshot` 加字段** ⇒ **破 L1 冻结面** ⇒ ⇒ 与 Q3 的拍板**直接矛盾** ⇒ ⇒ 排除。
- ❌ **把调度账本塞进 `StateSnapshot.metadata`** ⇒ `metadata` 是「**附加信息**」⇒ ⇒ 调度账本是
**核心状态**⇒ ⇒ 「层次对应优先于容器对应」（原则 XII）⇒ ⇒ **借位** ⇒ ⇒ 排除（且 `metadata` 是
自由字典 ⇒ 无类型约束 ⇒ 易腐化）。
- ❌ **恢复时重新跑触发判定**（不持久化账本）⇒ 被中断节点的触发版本**已在中断轮消费过**⇒ ⇒
它**不会**被重新触发 ⇒ ⇒ 图**卡住** ⇒ ❌。

---

### DR-08 · 调度账本的**序列化**

**Decision**：给 `SchedulerState` **增两个方法**（**不改字段**）：
`to_checkpoint() -> dict[str, Any]` 与 `from_checkpoint(data) -> SchedulerState`。
账本的**编码**：`versions_seen` 的 key 是**二元组**（`(kind, ident)`）⇒ **JSON 不可直接序列化**
⇒ ⇒ 编码为「`{节点名: [[kind, ident, version], ...]}`」的**列表**形态（纯数据 · 可 JSON 序列化 ·
C19 约束③）；`channel_versions` / `node_versions` / `dynamic_edges` **原样**（key 全是字符串）。

**Rationale**：① **只增方法、不改字段** ⇒ ⇒ `SchedulerState()` 的**构造签名逐字不变** ⇒ ⇒
B7F1 冻结面**零破坏**（B12F1 的 `dynamic_edges` 就是这么加的 · 裁定 12 / R-3 ①）⇒ ⇒ 零 L1 改动；
② 载荷 MUST 是**纯数据**（C19 ③）⇒ ⇒ 列表编码满足；③ **不**引入新的数据类 ⇒ ⇒ 零新增面。

**Alternatives considered**：
- ❌ **新建一个 `SchedulerLedger` 数据类** ⇒ **重复的载体**（原则 XII ③：「MUST 先穷举既有的、
  同语义的载体」）⇒ ⇒ `SchedulerState` **已是**那个载体 ⇒ ⇒ 排除。
- ❌ **用 `tuple` 的 `str` 化当 key** ⇒ 不可靠（分隔符歧义）⇒ ⇒ 排除。

---

### DR-09 · **pending writes** 的形状

**Decision**：`pending_writes` 的元素 = **`(task_id, channel, value)` 三元组**（**上游同款** ·
`PendingWrite = tuple[str, str, Any]` · `langgraph/checkpoint/base/__init__.py:32`）⇒
`task_id` = **节点名**（freegraph 取舍）· 通道名 = **`__interrupt__`**（中断留痕）/
**`__resume__`**（恢复值）⇒ 两个名字 **与上游逐字同款**（`langgraph/_internal/_constants.py:9` / `:11`）。

**Rationale**：① 三元组形态 **上游同款** ⇒ ⇒ 上游形状的 saver 的**待写入**可被 freegraph 直接读；
② `task_id` = **节点名** ⇒ freegraph 一轮一个节点一个任务 ⇒ ⇒ 节点名**足够**唯一定位 ⇒ ⇒
**更可读**（上游用任务路径哈希 · 不可读）⇒ ⇒ 属**读侧 / 写侧契约内的自由取舍**
（L1 协议 `-> Any` ⇒ **不约束**载荷形状）⇒ ⇒ **不**构成对上游行为面的偏离（上游的 pending writes
**从不被用户看见**）⇒ ⇒ **不**登记为偏离；③ 通道名**逐字同款** ⇒ ⇒ 上游的 `INTERRUPT` / `RESUME`
常量**同名** ⇒ ⇒ 将来做上游 saver 适配器时**零改名**。

**Alternatives considered**：
- ❌ **`task_id` 用任务路径哈希**（上游同款）⇒ freegraph 无「任务路径」概念 ⇒ ⇒ 需**自造**路径 ⇒
⇒ 得不偿失（节点名**已**足够）⇒ ⇒ 排除。
- ❌ **自定义通道名**（如 `"freegraph.interrupt"`）⇒ 与上游**分叉** ⇒ ⇒ 将来做适配器要改名 ⇒ ⇒ 排除。

---

### DR-10 · 恢复值的**传递**与**消费**

**Decision**：
① **写**：恢复时经 `checkpointer.put_writes(...)` 写一条 `__resume__` 的 pending write，其值 =
**列表**（该节点的中断值，按**节点内顺序**）；
② **读**：任务现场从 pending writes 里取该节点的 `__resume__` 值 ⇒ 规范化成**列表**
（**上游同款** · F-11 · `_algo.py:1301-1308`）；
③ **消费**：`interrupt()` 第 `idx` 次调用 ⇒ 若 `idx < len(resume)` ⇒ 返回 `resume[idx]`
（**上游同款** · `langgraph/types.py:955-958`）；否则 ⇒ **再次挂起**（裁定 7 · E-17）。

**Rationale**：① **上游同款**（F-11）⇒ ⇒ 「按节点内顺序匹配」的机制**不是**自研 ⇒ ⇒ 裁定 7
**有机制依据**；② 恢复值**先落 pending writes 再执行**（上游同款 · `_loop.py:904-925` 的
`map_command` ⇒ 写入 ⇒ 再跑）⇒ ⇒ **「恢复」与「首次运行」共用同一条执行路径** ⇒ ⇒ 零分支；
③ 恢复值**不足** ⇒ 再次挂起（**不**报错）⇒ ⇒ **上游同款**（E-17）⇒ ⇒ SC-014 / SC-013 可判定。

**Alternatives considered**：
- ❌ **恢复值直接塞进任务现场（不落 pending writes）** ⇒ ⇒ 内存态 ⇒ ⇒ **违反 FR-010**
（「MUST NOT 在内核内存里另存一份『待恢复现场』」）⇒ ⇒ 排除。
- ❌ **单值恢复时**把值**同时**写给所有挂起中断 ⇒ 裁定 4 要求**单值 + 多挂起 ⇒ 报错** ⇒ ⇒ 排除。

---

### DR-11 · 「按 id 的映射」的**识别与语义**

**Decision**：识别规则 = 「`resume` 是 dict **且** 它的**全部 key** 都是**当前挂起中断的 id**」
（spec 裁定 4 / 偏离登记 **X-3**）⇒ ⇒ 命中时按 id 逐个恢复；⚠️ **map 的「值」原样投递**给该节点
（**上游同款** · `_algo.py:1313-1314` 的 `task_resume_write.append(mapped_resume_write)`
⇒ ⇒ **标量即可**）⇒ ⇒ 该值 = 该节点**下一个** `interrupt()` 的恢复值 ⇒ ⇒ 未被指定的**仍挂起**（E-20 同款）。
⚠️ **唯一事实源 = spec FR-013 的表 ⑥ 行**（**映射**）· **判定顺序 = spec 裁定 4**（**先后**）⇒ ⇒
本条（DR-11）**只记录决策理由**，**MUST NOT** 被当作第三份口径 ⇒ ⇒ **2026-11-13 分析轮第二轮**：
**spec SC-015 的初版措辞（「映射的值 = 该节点的中断值列表」）已回修为「原样投递」**
⇒ ⇒ 与本条**同款**（⇒ ⇒ 偏离总数仍为 5 · 判据零放宽）。

**Rationale**：① 上游用「key 长得像 `xxh3_128` 摘要」的**启发式**（`_loop.py:910-914`）⇒ ⇒
一个**恰好**像摘要的普通 dict 会被**误判**（E-7 的越界即源于此）⇒ ⇒ freegraph 的规则**更精确**
⇒ ⇒ X-3；② ⚠️ **「map 的值」的形态 = 照抄上游**（**2026-11-13 分析轮回修 · 发起者拍板**）⇒ ⇒
上游在 map 分支把值**原样 append** 进该任务的恢复值序列（`_algo.py:1313-1314`）⇒ ⇒ **标量即可**
⇒ ⇒ 该值即该节点**下一个** `interrupt()` 的恢复值 ⇒ ⇒ 同一节点的**第 2 个** `interrupt()`
因「恢复值不足」⇒ **再次挂起**（裁定 7 · **上游同款** · E-17）⇒ ⇒ **零新增机制 · 零偏离**。
⚠️ **锚点更正**（分析轮实测）：初版引用的 `_algo.py:1301-1308` 实为 **task-specific pending write**
路径（`if not isinstance(task_resume_write, list): task_resume_write = [task_resume_write]`）
⇒ ⇒ **不是** map 路径 ⇒ ⇒ 初版据此推出的「值**必须**是列表」**不成立** ⇒ ⇒ 已回修。

**Alternatives considered**：
- ❌ **照抄上游的启发式** ⇒ ⇒ 保留上游的误判面 ⇒ ⇒ X-3 不成立 ⇒ ⇒ 排除。
- ❌ **给同一节点的多个中断分配不同 id** ⇒ ⇒ 违反 E-17 的上游同款 ⇒ ⇒ 且 id 的语义是「定位**一次中断**」
⇒ ⇒ 排除。
- ❌ **强制 map 的值是「该节点的中断值列表」**（初版口径 ⇒ ⇒ **已由 spec SC-015 的回修同步清除** —— 2026-11-13 分析轮第二轮）⇒ ⇒ 与上游的**成功路径可观察状态**
不一致（上游标量 ⇒ 节点拿到标量；freegraph 列表 ⇒ 节点拿到列表）⇒ ⇒ 属**未登记的行为面偏离**
⇒ ⇒ 违反原则 XI「成功路径的可观察状态 MUST 照抄上游」⇒ ⇒ 排除（**2026-11-13 分析轮拍板**）。

---

### DR-12 · 差分探针的**比较口径**扩展

**Decision**：给 `Scenario` 增一个比较模式 **`"interrupt-shape"`** ⇒ 比 `.value` **逐字** +
比 `.id` 的**形态**（**32 位十六进制** ⇒ 正则 `^[0-9a-f]{32}$`）⇒ ⇒ **不比** id 的**具体值**
⇒ ⇒ 既有 43 个场景**逐字不变**（**只增能力**）⇒ ⇒ ⚠️ **本 feature 的 8 个新场景 MUST 用
`DI-` 前缀**（`DI-01…DI-08`）⇒ ⇒ 探针内**已有** B12F1 的 `D-01…D-15` 与 B7F4 的 `D-16…D-28`
⇒ ⇒ **重号** ⇒ ⇒ **既有场景名逐字不动**。

**Rationale**：① **两侧的 id 必不同**（F-08：freegraph = blake2b · 上游 = xxh3 ⇒ 且 freegraph 的
命名空间含**随机 uuid4**）⇒ ⇒ 既有 `_compare_interrupts` 的**逐字**口径**必红** ⇒ ⇒ 必须**加**口径；
② id 的**用途**是「唯一定位一次中断」⇒ ⇒ **形态**（长度 + 字符集）才是可判定的**同款**面 ⇒ ⇒
DI-01 的判词「**32 位十六进制 + 唯一**」**照此实现**；③ **只增能力、不改既有** ⇒ ⇒ 既有 43 个场景
的判词**恒绿**（沿用 B12F1 的既有纪律）。

**Alternatives considered**：
- ❌ **把两侧的 id 都规范化成「前缀 + 序号」**再比 ⇒ ⇒ 需要**两侧都改**⇒ ⇒ 污染上游侧 ⇒ ⇒ 排除。
- ❌ **不比 id**（只比 `.value`）⇒ ⇒ 丢掉「id 可读且唯一」的判据 ⇒ ⇒ SC-001 弱化 ⇒ ⇒ 排除。

### DR-13 · `interrupt()` 的**落点**（**门禁 G25 唯一确定** · 2026-11-13 分析轮 · **实测**）

**Decision**：**机制整体住在 `src/freegraph/runtime/_interrupt.py`**（**L2 目录条目内**）·
**门面 `src/freegraph/graph.py`** 用**模块级** `ImportFrom` **直接转出**
（`from .runtime._interrupt import interrupt`）· **`src/freegraph/_primitives.py`**（**L2 单文件
条目**）**只留 `Send`**、**MUST NOT** import `runtime/`。

**Rationale**：① **层注册表**（冻结面 · `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`
§1）把 `src/freegraph/_primitives.py` 登记为 **L2 单文件条目**、把 `src/freegraph/runtime/`
登记为**另一个 L2 目录条目** ⇒ 按 §0.2 规则 3 的「**模块定位口径**」：**同一注册表条目**内的
import = 单元内部引用（不产生层边）· **跨条目**的同层 import = 按层间方向判定 ⇒ ⇒ 二者
**互相 import = 跨条目的 L2→L2 = 违规**（立项书 §5.1 铁律 3）⇒ ⇒ **实测两个方向都 FAIL**
（`_primitives.py` → `runtime/` · `runtime/superstep.py` → `_primitives.py`）⇒ ⇒ ⚠️ **函数体内
的「惰性 import」同样判红** —— 门禁扫 AST ⇒ ⇒ ⇒ 两条初版口径（spec 的「实现体在
`_primitives.py`」· tasks T019 的「在 `_primitives.py` 惰性 import `runtime._interrupt`」）
**都不可行** ⇒ ⇒ ⇒ **唯一合法形态** = 机制住在**一个注册表条目**内 + 门面用 **`facade-L1-L3`
例外**直接转出；② **实测**：该形态下 G25 **PASS** + 门面的 **G14 / G15 / G16 / G18** 与架构门禁
**150 passed** ⇒ ⇒ 门面的 7 个导出名**零改动**（`interrupt` 只是**来源模块**变了）⇒ ⇒ 门面的
**模块加载面**只多出 L2（**不**含 L4 / L5 ⇒ G18 恒绿）⇒ ⇒ 顶层包仍**惰性**（G1 / ARCH-2 恒绿）；
③ **零新增持久化字段 / 零第三方依赖**的红线**不受影响**（`_interrupt.py` 只用标准库）；
④ ⚠️ **改层注册表**（把 `_primitives.py` 并入 `runtime/`）属**冻结面变更**（须评审）⇒ ⇒ 代价
远大于收益 ⇒ ⇒ **不采纳**；⑤ 新建 `src/freegraph/_interrupt.py` 单文件条目同样不行（仍是
**跨条目**）⇒ ⇒ **排除**。

**Alternatives considered**：
- ❌ **机制住在 `_primitives.py`**（L2 单文件条目）⇒ `runtime/superstep.py` 必须 import 它来
挂载任务现场 ⇒ ⇒ **跨条目 L2→L2** ⇒ ⇒ **实测判红** ⇒ ⇒ 排除；
- ❌ **新建 `src/freegraph/_interrupt.py` 单文件条目** ⇒ 与 `runtime/` 仍是**跨条目** ⇒ ⇒ 排除；
- ❌ **改层注册表**（合并条目）⇒ **冻结面**（§3 变更纪律）⇒ ⇒ 须评审 ⇒ ⇒ 排除；
- ❌ **在 `graph.py` 里写惰性委托函数** ⇒ 违反门禁 **G14**（门面**零实现体** · AST 判
`class` / `def` == 0）⇒ ⇒ 排除 ⇒ ⇒ ⇒ 故门面只能用**模块级** `ImportFrom`。

---

## §3 被排除的方案（**汇总 · 便于审查**）

| # | 方案 | 排除理由 | 依据 |
|---|---|---|---|
| X-1 | 给 `SuperStepResult` 加第 5 字段 | 破 B12F1 裁定 25 ② 的**四字段冻结面** | spec 裁定 2 / 澄清轮 Q1 |
| X-2 | 把 `__interrupt__` 塞进 `state` | **形态污染**（「state == 合并后的稀疏状态」） | spec 裁定 2 · B12F1 裁定 25 ③ |
| X-3 | 抛内置 `RuntimeError` | 破 L1 `FreegraphError` 的**冻结承诺** | spec 裁定 3 / 偏离登记 X-2 |
| X-4 | 新增 L1 异常类 | 破 L1 **20 符号面** ⇒ G7 / G8 / G16 / G19 全红 | spec 裁定 3 |
| X-5 | 给 L1 `StateSnapshot` 加字段 | 与澄清轮 **Q3** 的拍板**直接矛盾** | 澄清轮 Q3 · DR-07 |
| X-6 | 用 `metadata` 承载调度账本 | **借位**「附加信息」承载核心状态 ⇒ 违反原则 XII | DR-07 |
| X-7 | 恢复时**重新跑触发判定** | 被中断节点的触发版本已消费 ⇒ 图会**卡住** | DR-07 |
| X-8 | 恢复值**只**放内存（不落 pending writes） | **违反 FR-010**（内存态旁路） | DR-10 |
| X-9 | 照抄上游的「key 像摘要 ⇒ 是 map」启发式 | 保留上游的**误判面**（E-7） | DR-11 · 偏离登记 X-3 |

---

## §4 与 spec 的**偏差登记**（⚠️ plan 阶段发现 ⇒ 须回修 spec）

| # | 偏差 | 影响 | 处置 |
|---|---|---|---|
| **PR-1** | spec **裁定 9 / FR-018** 的**读侧契约**只列 `.snapshot` + `.pending_writes` **两个**属性 ⇒ **缺**「**调度账本**」⇒ 而 spec **H-5 ⑤** 要求恢复 MUST 重建调度状态 ⇒ ⇒ **两处自相矛盾** | **B14F1 的实现面**（少一个属性 ⇒ saver 写不出账本 ⇒ 恢复后的**后续轮**触发判定失效） | ✅ **回修 spec 裁定 9 + FR-018**（读侧契约**增** `.scheduler`）⇒ ⇒ **不是 L1 冻结面**（是**本 feature 自己**定义的契约）⇒ ⇒ **不需要发起者追认** ⇒ 但 MUST 在 plan 的**登记项**里如实登记 |
| **PR-2** | spec 的**差分场景 D-01** 的判词写「`.id` **32 位十六进制**」⇒ 但既有探针的 `_compare_interrupts` 比的是**逐字** ⇒ ⇒ 既有能力**不可用** | 差分闸口**必红** | ✅ **不修 spec**（判词不变）⇒ ⇒ **扩探针**（新增 `"interrupt-shape"` 口径 · DR-12）⇒ ⇒ 落 tasks |
| **PR-3** | spec **Out of Scope 第 9 条**说「`compile(checkpointer=...)` 的门面接线 → B7F2」⇒ 而本 feature 的入口**显式**接收 checkpointer | 无矛盾（两者不重叠） | ✅ **无需处置**（仅在 plan 里写明两者边界） |
| **PR-4** | spec §0 / Key Entities / Assumptions 8 说「`interrupt()` 的**实现体**在 `src/freegraph/_primitives.py`」· 而 tasks T019 说「在 `_primitives.py` 惰性 import `freegraph.runtime._interrupt`」⇒ ⇒ 二者**互斥** ⇒ ⇒ **且两个口径都会被门禁 G25 判红**（**实测** · DR-13） | **门禁 G25 判红** ⇒ ⇒ 实现期**必红** ⇒ ⇒ 违反「feature 必须能独立通过其可适用门禁」 | ✅ **回修 spec**（§0 表格「架构层」+「门禁约束（G25）」两行 · Key Entities · Assumptions 8 · Out of Scope 第 15 条）⇒ ⇒ 唯一合法形态 = **DR-13** ⇒ ⇒ **L1 零改动** ⇒ ⇒ **判据零放宽**（G25 一字未改 —— 本回修是**让实现合规**）⇒ ⇒ **不需要**发起者追认 |
| **PR-5** | ① spec / research / plan / tasks / contracts / quickstart **共 8 处**写「既有 **30** 个差分场景」⇒ ⇒ **实测** `parity_probe._scenarios()` == **43**（30 是 B7F4 落库前的旧数 · B7F4 自己加了 13 条）⇒ ⇒ **T001** 会把这个错数写进人工验证记录的**绿基线**（证据件）② 本 feature 的差分场景原用 `D-01…D-08` ⇒ ⇒ 探针内**已有** B12F1 的 `D-01…D-15` 与 B7F4 的 `D-16…D-28` ⇒ ⇒ **重号** | ① 人工验证记录会带**错数**（违反原则 VIII 证据纪律）② 同文件内**三套 D-xx** 含义 ⇒ grep / 引用歧义 | ✅ **回修**（全部改 **43**）⇒ ⇒ 差分场景**改用 `DI-` 前缀**（`DI-01…DI-08`）⇒ ⇒ **既有场景名逐字不动** ⇒ ⇒ **零行为影响**（只是编号与计数） |
| **PR-6** | 分析轮补齐 **4** 条**判据级覆盖缺口**（SC-015 的「按 id 映射恢复**成功**」半边 · FR-013 ⑦「dict 非 map」· 补记 F-2「resume 与 update 并存」· FR-010「跨运行不得持有现场」）**+ 1** 条语义补齐（FR-013 末行「**会话连续**」）⇒ ⇒ **测试**行数 **640 → 680** ⇒ ⇒ **合计 1,160 → 1,200**（**+40**） | **范围膨胀** ⇒ ⇒ 违反「MUST NOT 悄悄超支」 | ✅ **登记范围变更**（`tasks.md` §行数预算表 · **PR-6**）⇒ ⇒ **实现**行数不变 ⇒ ⇒ ✅ **发起者已确认**（**2026-11-13 分析轮** · **并入 V-1 的那一次追认**）⇒ ⇒ ✅ **立项书 §5.2 已同步**（1,160 → **1,260** · 合计 31,220 → **31,320** 行 · 2026-11-13 分析轮） |
| **PR-7** | **分析轮实测**发现 **3** 条**测试级覆盖缺口**：**SC-008**「真异常优先」**只有实现任务 · 无测试** · **FR-013 末行**「会话连续」**只有实现任务 · 无测试**（PR-6 只补了实现面）· **SC-019**「契约门禁」只由 **T051** 兜底 · **无逐条核对** ⇒ ⇒ **新增 3 条测试任务**（**T056 / T057 / T058**）⇒ ⇒ **实现**行数**不变**（**只加测试**）⇒ ⇒ **测试**行数 **680 → 740** ⇒ ⇒ **合计 1,200 → 1,260**（**+60**） | ⇒ ⇒ **范围膨胀** ⇒ ⇒ 违反「MUST NOT 悄悄超支」 | ✅ **登记范围变更**（`tasks.md` §行数预算表 · **PR-7**）⇒ ⇒ ✅ **发起者已确认**（**2026-11-13 分析轮** · **并入 V-1 的那一次追认**）⇒ ⇒ ✅ **立项书 §5.2 已同步**（1,160 → **1,260** · 合计 31,220 → **31,320** 行 · 2026-11-13 分析轮） |
| **PR-8** | 破冻结面回溯修订清单 **T-1** 初版只登记 `runtime.__all__` 的 **3 处**代码断言 ⇒ ⇒ **分析轮实测**（沙箱里按 T-005 / T-018 / T-019 模拟改动并跑既有测试）发现**另 3 处**既有冻结断言**必红**：④ `test_read_contract.py::test_i9_the_reading_layer_adds_no_new_error_type`（`runtime.errors` 的 `__all__` **精确元组** + AST **类清单** —— **无论** `InterruptError` 是否写进 `errors.__all__` ⇒ **都红**）· ⑤ `test_facade.py::TestInterrupt::test_raises_not_implemented`（门面 `interrupt` 恒抛 `NotImplementedError`）· ⑥ `test_superstep_concurrency.py` 里 `assert "NotImplementedError" in primitives`（**仅靠** docstring 残留字符串**侥幸通过**） | ⇒ ⇒ ⇒ 按现 tasks 实施 ⇒ **pytest 必红** ⇒ ⇒ 违反「MUST NOT 写**永久红**的 CI」 | ✅ **扩容破冻结面清单为 6 处**（spec §1.1 **+3 行** · spec §5 **+3 行** · plan §破冻结面表 **+3 行** · tasks **T012-a**（第 ④ 处）+ **T012-b**（第 ⑤⑥ 两处）⇒ ⇒ **2026-11-13 分析轮第二轮**：**T012 按「落地后可判定性」拆为 T012-a（①–④ · Phase 2）+ T012-b（⑤⑥ · 紧随 T019）** ⇒ ⇒ **六处 MUST 同改**）⇒ ⇒ **三处均属「上游无此项 ⇒ 必须自研区 ③」⇒ 零行为面偏离** ⇒ ⇒ ⇒ **不**进偏离登记（X-1…X-5 仍为 5 项）⇒ ⇒ ⇒ **判据零放宽**（全部改成「集合相等 / 更具体的断言」）⇒ ⇒ ⇒ **发起者追认**（**并入 V-1 的那一次** ⇒ 追认次数仍为 1 次 · 宪法 E-6） |
| **PR-9** | **破冻结面清单在实施期再漏一处**（初版 3 处 ⇒ PR-8 扩容到 6 处 ⇒ **实施期实测**再发现 1 处：`tests/runtime/test_superstep_purity.py::test_importing_the_kernel_has_no_side_effects` 断言 `superstep.__all__` == **一份内联的 6 项精确列表** ⇒ ⇒ **硬编码清单** ⇒ ⇒ 本 feature **增**了 3 个符号 ⇒ ⇒ **必红** ⇒ ⇒ 清单 **6 处 → 7 处**） | **pytest 必红** ⇒ ⇒ 违反「MUST NOT 写**永久红**的 CI」 | ✅ **扩容破冻结面清单为 7 处**（spec §1.1 **+1 行** · spec §5 **+1 行** · plan §破冻结面表 **+1 行** · tasks **T012-a** **+1 处** · **新增** `tests/runtime/_runtime_export_manifest.py` 作**单一事实源**）⇒ ⇒ **属「上游无此项 ⇒ 必须自研区 ③」⇒ 零行为面偏离** ⇒ ⇒ **不**进偏离登记（X-1…X-5 仍为 5 项）⇒ ⇒ **判据零放宽**（改成「**集合相等**」）⇒ ⇒ **发起者追认**（**并入 V-1 的那一次** ⇒ 追认次数仍为 1 次 · 宪法 E-6） |
| **PR-10** | **范围变更（实施期实测超支）** —— 实施期**实测**的行数 = **实现 1,091 / 测试 1,854 ⇒ 合计 2,945**（预算 **520 / 740 ⇒ 1,260** ⇒ **超 +1,685 行 / +134%**）⇒ ⇒ 构成：① **T-1 的 7 处**冻结断言回溯修订（含**单一事实源** `tests/runtime/_runtime_export_manifest.py`）② **PR-8 / PR-9** 的**实测化**要求（**必须逐条**回溯修订 ⇒ **不可省**）③ 差分探针的**两段式**能力 + **``interrupt-shape``** 口径 + **8** 个 `DI-` 场景（`parity_probe.py` **+544**）④ 本 feature 的 **6** 个测试文件（**1,288**）+ **桩** checkpointer + **会话连续**路径 ⇒ ⇒ **零**功能删减 | **范围膨胀** ⇒ ⇒ 违反「MUST NOT 悄悄超支」 | ✅ **如实登记超支**（tasks §行数预算表 · **实施期实测**列）⇒ ⇒ **由发起者在 V-1 的那一次追认中一并追认**（**不**新增追认次数）⇒ ⇒ **立项书 §5.2 的 B10F1 行 MUST 同步为 2,945**（**由发起者拍板后**执行） |

| **A-01** | 「`Command(resume=…)` 的**判定表**」在 spec **裁定 4** / spec **FR-013** / `contracts/interrupt-resume-contract.md` §6.1 **三处**并存 ⇒ ⇒ 漂移风险（三处各说各话 ⇒ 实现口径打架） | 实现期可能照抄到**过期**的那一处 ⇒ ⇒ 判据不可判定 | ✅ **分工收口**（**2026-11-13 分析轮**）：**FR-013** = **映射**（输入形态 → 行为 · **唯一事实源**）· **裁定 4** = **判定顺序**（先判哪一条）· **契约 §6.1** = **只承载顺序 + 上游依据**（**不**复述判定表）⇒ ⇒ **引用时 MUST 写全**（「按 FR-013 的表 · 依裁定 4 的顺序」）⇒ ⇒ 另 ⇒ **tasks T027** **MUST NOT** 在实现里另抄一份 |

---

## §5 取证纪律

- 上游锚点一律带 **版本 + `路径:行号`**（`langgraph` **1.2.11**）；
- **行为**断言一律有**实测**编号（E-1…E-26 · 取证于 2026-11-13 · 脚本见 `harness/scripts/` 约定）；
- 本 plan 的**全部**设计决策先问「上游怎么说」⇒ 上游有答案 ⇒ **照抄** ⇒ 只在 **X-1…X-5**
  （spec 已登记）上分叉 ⇒ ⇒ **零**新增偏离。
