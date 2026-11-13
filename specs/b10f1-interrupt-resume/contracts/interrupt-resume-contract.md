# 中断 / 恢复契约（Interrupt-Resume Contract）—— B10F1 的**唯一权威**

**Feature**: `B10F1` · **Spec**: [`../spec.md`](../spec.md) · **Plan**: [`../plan.md`](../plan.md)
**Research**: [`../research.md`](../research.md) · **Data model**: [`../data-model.md`](../data-model.md)

> **本契约是 B10F1 的**唯一权威**（宪法 原则 VI「规格驱动开发」· 跨 feature 承接通则）⇒
> **tasks 与实现 MUST 逐条照本契约**⇒ ⇒ 与 spec 冲突时 ⇒ **以 spec 为准**并**回修本契约**。
> ⚠️ **本契约**只规定「**中断 / 恢复**」这条线 ⇒ **checkpointer 的读侧 / 写侧**归
> [`checkpoint-contract.md`](./checkpoint-contract.md)。

---

## 1. 抽象（**零新增 L1 符号**）

| 载体 | 位置 | 性质 | 冻结面 |
|---|---|---|---|
| `interrupt(value)` | **门面导出名**（`freegraph.graph.interrupt` · 7 符号面之一） | **已有**（现恒抛 `NotImplementedError`）⇒ 本 feature **只接线** | 门面的导出面**零改动**（G15 / G16 / G19）· ⚠️ **实现体**在 `src/freegraph/runtime/_interrupt.py`（**L2 目录条目内**）· 门面 `graph.py` **模块级**转出（**PR-4** / **DR-13**）|
| `GraphInterrupt` | **L1**（`freegraph.contracts.errors`） | **已有** · 只消费 | **零改动**（FR-017） |
| `Interrupt` | **L1**（`freegraph.contracts.types`） | **已有** · 只消费（`.id` 的**生成义务**归本 feature） | **零改动** |
| `Command` | **L1**（`freegraph.contracts.types`） | **已有** · 只消费（`resume` 位**已存在**） | **零改动** |
| `InterruptResult` | **L2**（`freegraph.runtime`） | **新增** · 4 字段 | L2 内部 API |
| `InterruptError` | **L2**（`freegraph.runtime.errors`） | **新增** · `.reason` 5 码 | L2 内部 API |
| `run_graph` | **L2**（`freegraph.runtime`） | **新增** · 图级入口 | L2 内部 API |
| `_interrupt`（模块） | **L2 私有**（`freegraph.runtime._interrupt`） | **新增** · 运行期上下文 | **不进** `__all__` |

⇒ **`freegraph.runtime.__all__`：20 → 23**（新增 `InterruptResult` / `InterruptError` / `run_graph`）
⇒ ⇒ **`freegraph.runtime.errors.__all__`：7 → 8**（新增 `InterruptError`）⇒ ⇒ 与 `tasks.md`
**T012-a** 第 ④ 处的**期望集合**（**7 + `InterruptError`**）**逐字对齐**（**否则该断言不可判定**）
⇒ ⇒ **L1 的 20 符号面零改动**（G7 / G8 / G16 / G19 恒绿）⇒ ⇒ 回溯修订 **T-1**（spec §破冻结面）。

---

## 2. 入口（**签名逐字冻结**）

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

| 参数 | 语义 | 校验 |
|---|---|---|
| `spec` | 图规格 | **必填** |
| `input` | 首次运行的**输入状态** / **恢复输入**（`Command`） | `None` ⇒ 空状态起跑 |
| `state` | **调度状态**（缺省新建 ⇒ 内部自洽）· ⚠️ **MUST NOT** 读成「状态字典」（`StateDict` 走 `input`）| 与 B7F1 裁定 27 同款 |
| `checkpointer` | **检查点后端**（**L1 协议**） | `None` ⇒ **不**持久化 ⇒ ⇒ **恢复不可用**（抛 `InterruptError`） |
| `config` | 运行配置（`thread_id` 等） | 缺省 ⇒ `RunConfig()` |
| `max_steps` | 步数上限 · 缺省 **10007**（**上游同款** · `langgraph/_internal/_config.py:32`） | 触顶且仍有任务 ⇒ 抛 `GraphRecursionError`（**L1 已有** · `contracts/errors.py:69`）⇒ ⚠️ 本 feature **只复用**该异常类型 ⇒ ⇒ **`recursion_limit` 配置面**属 **B13F1**（spec FR-024 · 本 feature **MUST NOT** 实现）|
| `max_concurrency` | 并发度（**上游同名同义**） | **入口即失败**（类型不符 ⇒ `TypeError` · `< 1` ⇒ `ValueError`）· 沿用 B12F1 `_validate_max_concurrency` |

⚠️ **既有入口一字不动**：`run_super_step` / `run_super_steps` 的**签名与返回类型零改动**
（B7F1 冻结面 · spec 裁定 10）⇒ ⇒ `run_graph` 是**图级**入口，二者是**不同层**（非替代关系）。

---

## 3. 「中断现场」的两级上下文

| 级 | 载体 | 设置点 | 载荷 | 复原 |
|---|---|---|---|---|
| **运行级** | `contextvars.ContextVar` | `run_graph`（整次运行） | `{节点名: 任务现场}` | `run_graph` 返回前 `reset(token)` |
| **任务级** | `contextvars.ContextVar` | `_bind._inner`（**每个节点执行**） | 该节点的任务现场 | 节点执行完 `reset(token)` |

**任务现场**的字段：

| 字段 | 类型 | 语义 |
|---|---|---|
| `resume` | `list[Any]` | 该节点**已提供**的恢复值（**按节点内顺序** · 上游同款） |
| `index` | `int` | 该节点内**第几次**调用 `interrupt()`（**原子计数**） |
| `existing` | `Interrupt \| None` | 该节点**先前**挂起时的中断载荷（**恢复时读回** ⇒ 复用其 `.id`） |
| `namespace` | `str \| None` | 命名空间 `f"{节点名}:{uuid4().hex}"`（**首次挂起时**才生成） |

⚠️ **复原 MUST 用 `ContextVar.reset(token)`** ⇒ 线程池**复用线程**时**零脏状态**。
⚠️ `contextvars` ⇒ **async 天然兼容**（v2 预留）⇒ ⇒ 零迁移成本。

---

## 4. `interrupt(value)` 的语义（**上游同款**）

```
answer = interrupt("approve?")
```

| 情形 | 行为 | 上游锚点 |
|---|---|---|
| **图运行之外**调用 | 抛 `InterruptError(reason="not_in_run")` | `langgraph/config.py:26-29`（`RuntimeError`）· 类型差异见 **X-2** |
| 节点内 · **有**可用的恢复值（`index < len(resume)`） | **返回** `resume[index]`（**不**抛中断） | `langgraph/types.py:955-958` |
| 节点内 · **无**可用的恢复值 | 抛 `GraphInterrupt((Interrupt(value=value, id=<id>),))` | `langgraph/types.py:967-974` |
| 节点内 · **重复**调用（第 2 次起） | `index` 递增 ⇒ 依次取下一个恢复值 | `langgraph/types.py:951-953` |

⚠️ **载荷 = 1-元组**（`tuple[Interrupt, ...]`）⇒ **上游同款**（`types.py:967-974`）⇒ ⇒
**不得**写成 `raise GraphInterrupt(payload)`（单个对象）⇒ L1 的 `payload` 是**序列** ⇒ 会 `TypeError`。

### 4.0 实现体的**落点**（⚠️ **门禁 G25 唯一确定** · **PR-4** / **DR-13**）

| 项 | 落点 |
|---|---|
| **运行期机制**（两级 `ContextVar` · 任务现场 · `.id` 生成 · resume 消费） | **`src/freegraph/runtime/_interrupt.py`**（**L2 目录条目内** ⇒ 与 `superstep.py` **同一注册表条目** ⇒ 互相 import **合法**）|
| **门面转出** | **`src/freegraph/graph.py`** 的**模块级** `from .runtime._interrupt import interrupt`（`facade-L1-L3` 例外 ⇒ 门面 → L2 合法）|
| **`src/freegraph/_primitives.py`** | **只留 `Send`** ⇒ ⇒ **MUST NOT** import `runtime/`（**跨注册表条目的同层 import** ⇒ **门禁 G25 判红** · **实测**）|

⚠️ **两个旧口径都判红**（**实测**）：① 实现体住在 `_primitives.py` ⇒ `runtime/superstep.py` 必须
反向 import 它 ⇒ **跨条目 L2→L2** ⇒ 判红；② 在 `_primitives.py` 里**惰性** import
`runtime._interrupt` ⇒ 门禁扫 AST ⇒ **函数体内的 import 同样判红** ⇒ ⇒ ⇒ **唯一合法形态** = 上表。

### 4.1 `.id` 的生成（**内核自动 · 零第三方依赖**）

| 步 | 落法 | 理由 |
|---|---|---|
| 1 | 命名空间 = `f"{节点名}:{uuid4().hex}"` | **上游同款**（E-23 · `langgraph/types.py:967-974` 用 `CONFIG_KEY_CHECKPOINT_NS`）⇒ **含随机量** ⇒ **不可猜** |
| 2 | `id = hashlib.blake2b(ns.encode(), digest_size=16).hexdigest()` | **零第三方依赖**（宪法依赖白名单）⇒ 上游的 `xxh3_128_hexdigest`（`xxhash` 包）**不可用** ⇒ 偏离登记 **X-4** |
| 3 | 长度 = **32 位十六进制** | 与上游 `xxh3_128` **同长度**（E-9）⇒ **形态同款** |
| 4 | **恢复时复用** `existing.id`（**不重算**） | ⇒ **跨恢复稳定**（F-1 · E-17）⇒ **零新增持久化字段** |

⚠️ **同一节点同一轮内的多个 `interrupt()` 共享同一个 `id`**（E-17 · 上游同款）。
⚠️ **不同节点的 `id` 互不相同**（E-11 · 上游同款）。
⚠️ **用户 MUST NOT 自带 `.id`**（C17 · 节点只能看到 `.value`）。

---

## 5. 挂起（**paused**）与**完成**（**completed**）两条结束方式

### 5.1 挂起

| 步 | 动作 | 依据 |
|---|---|---|
| 1 | 节点抛 `GraphInterrupt` ⇒ B12F1 的**合并抛出**语义产出**一个** `GraphInterrupt`（载荷 = **元组**） | B12F1 契约 §7（**零改动**） |
| 2 | **真异常优先** ⇒ 一轮里既有真异常又有中断时 ⇒ **真异常抛出**、中断元组**丢弃** | 上游同款（`langgraph/pregel/_runner.py:687` 先于 `:690`）· spec 裁定 11 |
| 3 | 被中断节点**不落回**（**未完成**）· 同轮**其它**节点**照常落回 + 合并** | B12F1 契约 §5 / §7（**零改动**）· 上游同款（E-21） |
| 4 | **中断轮之后不再进入下一轮** | B12F1 裁定 9 |
| 5 | 本 feature **接住**那个 `GraphInterrupt` ⇒ 读 `exc.args[0]`（**元组**）⇒ 产出 **`InterruptResult`** | spec 裁定 1 / 裁定 2 · B12F1 **D-1** |

**`InterruptResult` 的四字段（逐字冻结）**：

| 字段 | 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | **合并后**的稀疏状态（**含**中断前已产生的写入） |
| `interrupts` | `tuple[Interrupt, ...]` | 中断集合（= `exc.args[0]` · **元组**） |
| `executed` | `tuple[str, ...]` | **已启动过**的节点名（**含**被中断的 · **节点名序** = **升序** · 与 `SuperStepResult.executed` **同排序口径**）⇒ ⚠️ 中断轮**不**产出 `SuperStepResult` ⇒ ⇒ 判据形态 = 「**逐字等于期望的节点名序**」+「**是升序的**」（**不**是「两个对象逐字相等」· **2026-11-13 分析轮回修**） |
| `steps` | `int` | **实际跑过的轮数**（**如实计** · **含**被中断的那轮 · **不含**那个空轮）⇒ ⚠️ **与 `SuperStepResult.steps` 计数口径「刻意不同」**（后者**含**空轮 · B7F1 冻结面）⇒ ⇒ 同一张图「挂起 N 轮」与「跑完 N+1 轮」⇒ ⇒ **数值不可直接比较** |

⚠️ **MUST NOT** 带「待写入」字段（`node_writes`）⇒ 挂起时那些写入**已合并进 `state`** ⇒ 语义不明
（澄清轮 **Q1** · spec 裁定 2）。
⚠️ `__interrupt__` **不进 `state`**（形态污染 · B12F1 裁定 25 ③）。
⚠️ **MUST NOT** 改 `SuperStepResult` 的**字段数**（**四字段** · B12F1 裁定 25 ②）。

### 5.2 `as_result_dict()`（**本 feature 独占**的转成路径）

```
InterruptResult.as_result_dict() -> dict[str, Any]
    = {**state, "__interrupt__": interrupts}
```

⚠️ **键名逐字** = `"__interrupt__"`（**上游同款** · `langgraph/_internal/_constants.py:9`）
⚠️ **值 = 元组**（spec 裁定 1 · 偏离登记 **X-1** · 上游 `invoke()` 返回 **list**）
⚠️ **完成态**的结果**不含**该键（**上游同款** · E-2）
⚠️ **转成路径只此一条** ⇒ B7F3 **MUST NOT** 另写（承接 **D-3**）

### 5.3 完成

返回 `SuperStepResult`（**四字段 · 零改动**）⇒ 与首次运行**同款**。

---

## 6. 恢复（**resume**）

### 6.1 前置判定（**顺序固定**）

> ⚠️ **判定表的唯一事实源 = spec 的 FR-013**（**逐字照抄** · **MUST NOT** 在本契约另抄一份
> —— 2026-11-13 分析轮 **A-01**）⇒ ⇒ **判定顺序**的唯一事实源 = spec 的 **裁定 4**（
> 2026-11-13 分析轮 **A-01 收口**：**本节不再复述那张表** ⇒ ⇒ 避免第三处漂移）⇒ ⇒
> **本节只承载「判定顺序 + 上游依据 + 失败信号清单」** ⇒ ⇒ 实现时 MUST **同时**读这两处：
> 「**按 FR-013 的表**（映射）· **依裁定 4 的顺序**（先后）」。

| 序 | 判定（**顺序**的权威在 spec 裁定 4） | 失败信号 |
|---|---|---|
| ① | 输入**不是** `Command` ⇒ ⇒ **首次运行**路径（**不**要求 checkpointer） | — |
| ② | 输入是 `Command` 但 `resume` 位**未提供**（`None`） | `InterruptError(reason="resume_value_required")` |
| ③ | **未挂** checkpointer | `InterruptError(reason="checkpointer_required")` |
| ④ | 该会话**没有**挂起的中断 | `InterruptError(reason="no_pending_interrupt")` |
| ⑤ | `resume` 是**标量** 且挂起中断 **> 1** | `InterruptError(reason="ambiguous_resume")` |
| ⑥ | `resume` 是 **dict** 且**全部 key** 都是**当前挂起中断的 id** ⇒ ⇒ 按 id 逐个恢复（**未被指定的仍挂起**）⇒ ⚠️ **map 的「值」原样投递**（**标量即可** · **上游同款** · `langgraph/pregel/_algo.py:1313-1314`）⇒ ⇒ 该值 = 该节点**下一个** `interrupt()` 的恢复值 ⇒ ⇒ 同一节点的**第 2 个** `interrupt()` ⇒ **再次挂起**（裁定 7） | — |
| ⑦ | `resume` 是 **dict** 但 key **不**全是挂起中断的 id ⇒ ⇒ **普通恢复值**（**仅当**挂起中断数 == 1 时有效 ⇒ **> 1** ⇒ 回到 ⑤） | `InterruptError(reason="ambiguous_resume")`（**> 1** 时） |
| ⑧ | `resume` 与 `update` **并存** ⇒ ⇒ 两者**各走各的通道** | — |

⚠️ **各行的**具体输入形态 → 行为**的映射**见 **FR-013 的表** ⇒ ⇒ 本表**不**复制它。

⚠️ **② 先于 ③**（**上游同款** · **实测 E-25a / E-25b**）：上游的 checkpointer 检查**在
`if resume is not None` 之内**（`langgraph/pregel/_loop.py:904-907`）⇒ ⇒ `resume=None` 时
**根本不触达** ⇒ ⇒ 故 `Command(resume=None)` ⇒ **`resume_value_required`**（**不是**
`checkpointer_required`）⇒ ⇒ **spec FR-013** 的表与**裁定 4** 的「判定顺序」**同款**。
⚠️ ⑦ 的「> 1 ⇒ `ambiguous_resume`」是为消除「普通恢复值**到底恢复哪一个**」的歧义。

### 6.2 恢复的五个步骤

| 步 | 动作 | 落点 |
|---|---|---|
| 1 | `checkpointer.get_tuple(config)` ⇒ 取 `.snapshot` / `.pending_writes` / `.scheduler` | [`checkpoint-contract.md`](./checkpoint-contract.md) |
| 2 | 从 `.pending_writes` 里取该会话的**挂起中断集合**（`__interrupt__` 通道）⇒ 校验「**有**挂起中断」 | spec 裁定 4 ④ |
| 3 | 把**恢复值**写进 `__resume__` 的 pending write（值 = **列表** · 节点内顺序）⇒ 再写回 checkpointer | **上游同款**（`langgraph/pregel/_loop.py:904-925`）· research **DR-10** |
| 4 | **重建**通道实例（`Channel.from_checkpoint`）+ 调度账本（`.scheduler`）⇒ ⚠️ **两条路径刻意不同**（**2026-11-13 分析轮拍板 · 照抄上游**）：<br>**④a · 恢复**（输入是 `Command`）⇒ 跑 `.snapshot.next` 的节点（**显式** · **不走**触发判定）⇒ 任务现场带 `resume` + `existing`；<br>**④b · 会话连续**（输入**非** `Command`）⇒ 先用 `.scheduler` **重建调度状态**（**续跑** · **上游同款** · **实测 E-26**）⇒ ⚠️ **两种输入形态行为不同**（**上游同款** · **实测 E-26**）：**`input = None`** ⇒ **不**写任何通道 ⇒ **只有被中断的节点**重跑 ⇒ `.id` **逐字不变**（**实测 E-15 / E-26 ①** · 补记 **F-1**）；**`input = StateDict`** ⇒ 先读 `.snapshot.values`、再把 `input` **按通道写入**叠加上去（**覆盖型 ⇒ 覆盖** · **归约型 ⇒ 追加** · **与 B5F1 的 `Channel.update` 同款** · **MUST NOT** 另写一条叠加路径）⇒ **写通道 ⇒ 通道版本推进 ⇒ 订阅节点重新触发** ⇒ 被触及的节点**重跑**（**实测 E-26 ②**）⇒ `.id` **可变**（新的检查点 ⇒ 新的任务路径）⇒ ⇒ 两条支路**共用**同一条续跑路径（**MUST NOT** 另写一条「整图重跑」路径）⇒ **不**消费 `__resume__` ⇒ ⇒ **不**触发恢复| research **DR-07** / **DR-08** · spec **H-5 ⑤** · **FR-013** 末行 · 裁定 9 |
| 5 | 节点跑完 ⇒ **继续**后续轮次（触发判定与首次运行**同款**）⇒ 跑完 ⇒ 返回 `SuperStepResult` | spec **H-5 ⑤** |

### 6.3 「从节点起点重跑」（**最容易实现错的语义**）

| 要求 | 判据 |
|---|---|
| 节点函数**整个重新执行** | 节点内**前半段**的副作用**再次出现**（E-8 · `['enter', 'enter', 'got yes']`） |
| **不**保存局部变量 | 节点内变量在恢复后**从头**开始 |
| **不**从中断点继续 | 节点靠 `interrupt()` 的**返回值**区分「首次 / 恢复」（写法：`answer = interrupt("approve?")`） |
| 恢复值**不足** ⇒ **再次挂起**（**不**报错） | 节点在**下一个** `interrupt()` 处**再次**产生中断载荷（E-17）⇒ 该载荷的 `.id` 与第一次**逐字相同**（F-1） |

---

## 7. 失败信号汇总（**FS-1…FS-5** · 本 feature 自己的编号段）

> ⚠️ **编号前缀（2026-11-13 分析轮回修）**：本表的**失败信号**编号一律用 **`FS-`** 前缀
> ⇒ ⇒ **与** data-model 的**校验规则** `V-1…V-14` **区分** ⇒ ⇒ **与** 上游 feature（B12F1 等）的
> `V-n` **区分** ⇒ ⇒ 原先写的「V-16…V-20」是**悬空标签**（表内无该编号）⇒ ⇒ 已改前缀。

| 码 | 触发 | 消息要点（**上游同款**） |
|---|---|---|
| **FS-1** · `checkpointer_required` | 恢复时**未挂** checkpointer | `Cannot resume without a checkpointer`（上游 `_loop.py:906` 逐字要点） |
| **FS-2** · `resume_value_required` | `Command(resume=None)` / `Command()` | `resume value is required`（上游**意图**是 `EmptyInputError` · `_loop.py:927`） |
| **FS-3** · `ambiguous_resume` | 多个挂起中断 + 单值恢复 | `When there are multiple pending interrupts, you must specify the interrupt id when resuming.`（上游 `_loop.py:917-919` 逐字要点） |
| **FS-4** · `no_pending_interrupt` | 该会话**没有**挂起的中断 | `No pending interrupt to resume` |
| **FS-5** · `not_in_run` | 在**图运行之外**调用 `interrupt()` | `interrupt() called outside of a graph run`（上游 `config.py:29` 逐字要点） |

⚠️ **异常对象只带 `.reason`** ⇒ **不**带会话标识 / 待恢复中断的 id 列表（澄清轮 **Q2**）
⚠️ **MUST NOT** 继承 `ValueError` ⇒ 用户既有的 `except ValueError` **不**误吞
⚠️ **MUST** 继承 `FreegraphError` ⇒ 用户 `except FreegraphError` **兜得住全部**内核错误（L1 冻结承诺）

---

## 8. 不变量（**逐条可断言** · I-1…I-15）

| # | 不变量 | 判据 |
|---|---|---|
| **I-1** | `SuperStepResult` 的**字段数恒为 4** | `dataclasses.fields(...)` 长度 == 4 |
| **I-2** | `__interrupt__` **不进** `state` | `set(state) ∩ {"__interrupt__"} == ∅` |
| **I-3** | `__interrupt__` 的**元素**带 `.value` 与 `.id` | 逐元素 `hasattr` |
| **I-4** | `.id` 恒为 **32 位十六进制** | 正则 `^[0-9a-f]{32}$` |
| **I-5** | 同一节点同一轮的多个 `interrupt()` **共享 id** | 逐字相等 |
| **I-6** | **恢复时**的 `.id` 与先前交给调用方的**逐字相同** | 逐字相等（F-1） |
| **I-7** | 中断**前**的状态写入**不丢失** | 挂起结果含那些写入（E-16） |
| **I-8** | 同轮**其它**节点的写入**照常合并** | 挂起结果含那些写入（E-21） |
| **I-9** | 中断轮**不**产出 `SuperStepResult` | 返回类型 == `InterruptResult` |
| **I-10** | 挂起的 `steps` **如实计**（含被中断的那轮 · 不含空轮）⇒ ⇒ **与 `SuperStepResult.steps`（含空轮）口径刻意不同 · 数值不可直接比较** | 逐字相等 |
| **I-11** | **未挂** checkpointer ⇒ 恢复抛 `InterruptError`（**不**降级） | `pytest.raises` + `.reason` |
| **I-12** | 恢复**确实**读了 checkpointer 的**快照 + 待写入** | **桩**记录调用 |
| **I-13** | L2 **不** import L4 实现 | 导入图断言（门禁 **G25**） |
| **I-14** | `interrupt()` 在**图运行之外** ⇒ 抛 `InterruptError` | `pytest.raises` + `.reason` |
| **I-15** | 门面的 **7 个导出名零改动**且 `interrupt` 的来源是**模块级** `from .runtime._interrupt import interrupt` · `_primitives.py` **零** import `runtime/` | `tests/facade/test_facade_gates.py`（G14 / G15 / G16 / G18）+ 门禁 **G25** |

---

## 9. 边界（本契约**不**规定的事）

- **checkpointer 的读侧 / 写侧** ⇒ [`checkpoint-contract.md`](./checkpoint-contract.md)；
- **门面 `invoke()` 的接线** ⇒ **B7F3**（承接 **D-3**）；
- **`compile(checkpointer=...)` 的门面接线** ⇒ **B7F2**；
- **checkpointer 的实现** ⇒ **B14F1**（`MemorySaver`）· **B15F1**（`SqliteSaver`）；
- **静态中断点 / `recursion_limit`** ⇒ **B13F1**（承接 **D-4**）；
- **`Send`** ⇒ **B11F1**；
- **async / 子图** ⇒ **v2**；
- **可观测标注** ⇒ **B18F1 / B19F1**；
- **agent 层审批 UI** ⇒ **freechain**（承接 **D-6**）。
