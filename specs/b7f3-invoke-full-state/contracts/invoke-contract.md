<!-- authority: yes -->

# 执行契约（Invoke Contract）—— B7F3 的**唯一权威**

**Feature**: `B7F3` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**核实环境**: CPython **3.11.16** · 上游 `langgraph` **1.2.11**（核实于 2026-11-16）

> **本文件是「`invoke()` 怎么用、返回什么、失败什么」的**唯一权威**（沿用 B7F1 / B7F2 的契约先例：
> 机器可读 Markdown + `<!-- authority: yes -->` 标记）。
> **spec** 讲「**要什么**」（需求与判据）· 本文件讲「**是什么**」（**逐字冻结**的行为契约）。
> ⚠️ 两者冲突时以 **spec** 为准（spec 是上位文档），并 MUST 回修本文件。

---

## 1. 入口（对外形态）

| 项 | 契约 |
|---|---|
| 宿主 | 编译产物 `CompiledGraph` 的方法（实现体在 L3 私有模块 `src/freegraph/_stategraph.py` · **零新增源文件**） |
| 签名 | `invoke(input: StateDict \| Command \| None, config: RunConfig \| Mapping[str, Any] \| None = None) -> StateDict`（**`input` 必填位置参数** · `config` 缺省 `None`） |
| L1 协议 | `freegraph.contracts.protocols.CompiledGraph.invoke` 的注解 **自 B7F3 起** = 上述签名（**破 L1 冻结面** ⇒ 走「登记 + 回溯修订 + 发起者追认」三条） |
| `input` 的三种形态 | ① **状态字典**（部分 key 即可）⇒ 初始状态 ② **`Command`** ⇒ 恢复路径 ③ **`None`** ⇒ 会话连续 / 首轮不写任何通道 |
| `config` 的两种形态 | ① **`RunConfig`** 实例 ② **普通映射**（如 `{"recursion_limit": 3}`）⇒ **原样**交给 L2（**MUST NOT** 在门面层翻译） |
| 返回 | **普通 `dict`**（`type(out) is dict`）· **完整状态**（见 §3） |
| 不就绪信号 | **零** —— `invoke` 已交付 ⇒ **MUST NOT** 抛 `NotImplementedError`（就绪探针以它为判据 · `harness/demo/graph_core.py:555-571`） |

---

## 2. 执行语义（唯一的执行路径）

> ⚠️ **编号域**（2026-11-16 analyse 轮 · **S-15**）：本节的 **`ES-01…ES-11`**（执行语义条款）
> **刻意区别于** §1 的**实测台账 `E-1…E-10`**（上游实测证据 · 见 `upstream-parity.md` §1）
> ⇒ ⇒ ⇒ 两者**不再同形** ⇒ ⇒ ⇒ ⇒ 消除「`E-06`（条款）vs `E-6`（实测）」的歧义。

| # | 项 | 契约 |
|---|---|---|
| **ES-01** | **驱动入口** | MUST 调 L2 的 `run_graph(spec, input, *, checkpointer=..., config=...)`（`src/freegraph/runtime/superstep.py:1918-1990`）⇒ ⇒ **MUST NOT** 另写一条「编译 → 执行」的路径 ⇒ ⇒ ⚠️ **MUST NOT** 传 `max_concurrency` 关键字（旋钮的**读取点在 L2** · ES-08 ⇒ 关键字缺省时由 L2 回落到 `config.max_concurrency`）⇒ ⇒ ⇒ **门面层零搬运逻辑** |
| **ES-02** | **图规格** | MUST 传编译产物持有的 `_spec`（**只读**）⇒ ⇒ **MUST NOT** 改写 `_spec` ⇒ ⇒ **MUST NOT** 新增/删除编译产物的私有字段（持有面「3 私有 + 8 公开」是 B7F2 的冻结面） |
| **ES-03** | **调度状态** | MUST **不传** `state=` ⇒ ⇒ L2 自建 `SchedulerState()`（`superstep.py:1965`）⇒ ⇒ **每次调用内部自洽**（不依赖调用方复用调度状态） |
| **ES-04** | **通道实例** | 每次运行由 L2 从**规格**新建通道实例（`_run_channels` · `superstep.py:575-591`）⇒ ⇒ 同一张编译图**连续两次不累积**、**并发两次不串扰** |
| **ES-05** | **初始状态写入** | MUST 走 L2 的既有输入写入路径（`_apply_input_writes` · `superstep.py:1566-1590`）⇒ ⇒ 带归约器 ⇒ **归约**；无归约器 ⇒ **覆盖** ⇒ ⇒ **MUST NOT** 另写一条写入路径 |
| **ES-06** | **`checkpointer`** | MUST 由编译产物**透传**（`compiled.checkpointer`）⇒ ⇒ 本 feature **MUST NOT** 自己落盘 / 实现 saver（归 B14F1） |
| **ES-07** | **`config`** | MUST **原样**交给 L2（`run_graph(config=...)`）⇒ ⇒ L2 的 `resolve_config` 归一（`RunConfig` 原样 / `Mapping` ⇒ `from_dict(..., ignore_unknown=True)` / 其它 ⇒ `TypeError`）⇒ ⇒ 映射里的**未知键被宽容忽略**（与上游同款 · 实测 E-6） |
| **ES-08** | **`max_concurrency` 的读取点** | ⚠️ **2026-11-16 clarify 轮 · 用户拍板（Q2 = B）**：旋钮的**读取点落在 L2** —— `run_graph`（`superstep.py:1964-1967`）在**关键字缺省时**回落到 `config.max_concurrency`（**关键字优先**）⇒ ⇒ **兼容扩展**（既有调用方零改动 · 关键字的失败顺序**逐字不变**）⇒ ⇒ ⇒ 门面 MUST **原样**传 `config`、MUST NOT 读取该旋钮、**MUST NOT** 把整个映射翻译成 `RunConfig` ⇒ ⇒ 非法取值的失败信号由 **L2** 产出（`superstep.py:1339-1361`：类型不符 ⇒ `TypeError`；`< 1` ⇒ `ValueError`；均**点名该参数**）⇒ ⇒ **MUST NOT** 在门面层另写一份校验 ⇒ ⇒ ⇒ ⚠️ **config 兜底值的校验点 = `resolve_config` 之后、`_first_graph` 之前**（它只能在 resolve 之后才读到）⇒ ⇒ ⇒ ⇒ 失败信号与关键字形态**同款**（`TypeError` / `ValueError` 点名该参数）⇒ ⇒ ⇒ ⇒ **关键字形态的失败先后逐字不变** ⇒ ⇒ ⇒ ⇒ 回溯修订 B10F1 / B12F1 的契约行（破冻结面 **T-3**）⇒ ⇒ ⇒ ⚠️ **`None` ≡ 未指定**（2026-11-16 analyse 轮 · **D-B 决策** · **本契约的唯一口径**）：关键字为 `None`（**未传**或**显式 `None`** · 二者**不可区分** ⇒ 门面的 `invoke` **恒不传**该关键字）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **一律回落到 `config.max_concurrency`** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **不存在**「显式 `None` 覆盖 config」的第三种语义 |
| **ES-09** | **`recursion_limit`** | MUST 由 L2 的 `resolve_limit` 决定（优先级：`config.recursion_limit` > `max_steps` > **硬编码** `10007` · `_recursion.py:66-80`）⇒ ⇒ 超限 ⇒ `GraphRecursionError`（`superstep.py:1706-1708`）⇒ ⇒ **MUST NOT** 包装成别的类型 |
| **ES-10** | **节点入参** | MUST **原样**沿用 L2 的稀疏读口径（入参 == `read_channels(子映射)`，子映射按**通道映射的顺序**构造）⇒ ⇒ **MUST NOT** 改写 key 顺序 ⇒ ⇒ 「无值 key 填 `None`」**MUST NOT** 泄漏到节点入参（C4：入参仍稀疏） |
| **ES-11** | **终止** | MUST 驱动整张图执行到终止（到达 `END` 或无待执行任务）⇒ ⇒ 多源汇合边（屏障）MUST 在**同一条**路径上生效（**MUST NOT** 为屏障另开路径）⇒ ⇒ ⚠️ **屏障 = 静态多源边**（`add_edge(["a", "b"], "c")` · B7F4 已交付于 L2）⇒ ⇒ ⇒ **本 feature 判定**（**不依赖** B8F1 的条件边路由 ⇒ 上游同款 · **实测 E-10** · research §1） |

---

## 3. 返回值（完整状态）

### 3.1 键集

| # | 项 | 契约 |
|---|---|---|
| **R-01** | **键集** | MUST **等于** schema 的**全部** key 集合（**按 schema 声明顺序**）⇒ ⇒ **MUST NOT** 因「无值」漏 key ⇒ ⇒ **MUST NOT** 出现 schema 之外的 key（**路由通道等内部通道 MUST NOT 泄漏**）⇒ ⇒ ⚠️ **唯一例外** = **挂起**时的 `"__interrupt__"`（R-08 产出 · 值为元组）⇒ ⇒ ⇒ **非挂起**时该键 MUST **不**出现 ⇒ ⇒ ⇒ ⇒ ⇒ **本条不收紧**（判据零放宽 · 2026-11-16 analyse 轮 · **D-C 决策**） |
| **R-02** | **schema key 集合的来源** | MUST 由编译产物持有的**图规格通道表扣除路由型通道**得出；路由型通道的判定 MUST 沿用 **B7F1 的冻结口径**（`isinstance(channel, EphemeralValue)` · `specs/b7f1-superstep-loop/spec.md:547-551`）⇒ ⇒ **MUST NOT** 用「`branch:to:` 前缀」之类**名称启发式** ⇒ ⇒ **MUST NOT** 依赖「节点订阅集」（间接口径） |
| **R-03** | **无值 key 的取值** | MUST 以 **`None`** 补齐 ⇒ ⇒ ⚠️ **仅适用于「覆盖型（无归约器）」通道**（该 key 在稀疏视图里**缺席**）⇒ ⇒ ⇒ **归约型**通道未写时其稀疏视图里**已有**「类型空值」（`[]` / `0`）⇒ ⇒ ⇒ **MUST NOT** 把类型空值改写成 `None`（R-06）⇒ ⇒ ⇒ ⚠️ **只影响返回值**；**MUST NOT** 改变「用户显式传入 `None` 作为初始值」的写入语义（`{"x": None}` 仍 MUST 被写进通道） |
| **R-04** | **归约型 key** | 值 MUST 是「**初始值 + 全部新增值**」的合并结果 ⇒ ⇒ **MUST NOT** 只返回增量 |
| **R-05** | **无归约器 key** | 值 MUST 是**覆盖**后的最终值 ⇒ ⇒ **MUST NOT** 累加 |
| **R-06** | **归约型通道的「类型空值」** | ⚠️ `BinaryOperatorAggregate` 的初值是**类型空值**（`list` → `[]` · `int` → `0` · `channel.py:437` + `:350-374`）⇒ ⇒ 它**已经**出现在稀疏状态里 ⇒ ⇒ 故「填 `None`」只作用于**缺席**的 key ⇒ ⇒ **MUST NOT** 把「类型空值」改写成 `None` ⇒ ⇒ ⇒ ⚠️ **退化分支（极少见）**：若该通道的**类型空值不可构造**（`_derive_empty_value` ⇒ `_MISSING`）⇒ ⇒ ⇒ 该通道在稀疏视图里**缺席** ⇒ ⇒ ⇒ ⇒ 于是补齐值 = `None`（落**覆盖型**那一档）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽** |

### 3.2 归一顺序（**唯一**的两步）

```text
① 取结果：
   run_graph(...) -> SuperStepResult | InterruptResult
   ├─ SuperStepResult  ⇒ 稀疏视图 = result.state
   └─ InterruptResult  ⇒ as_result_dict()        ← 唯一转成路径（产出 "__interrupt__" 键）
② 补齐（对两条路径同款）：
   完整状态 = {schema key: 稀疏视图.get(key, None) for key in schema key 顺序}
             + （挂起时）{"__interrupt__": interrupts}     ← 保留，不覆盖、不重排
```

| # | 项 | 契约 |
|---|---|---|
| **R-07** | **转成路径** | 「**异常 → `__interrupt__` 键**」的转成路径 **只此一条** = `InterruptResult.as_result_dict()`（`superstep.py:406-418` · 其 docstring `:415-416` 明写「B7F3 **MUST NOT** 另写」）⇒ ⇒ **MUST NOT** 另写一条（含静态挂起专用的一条） |
| **R-08** | **静态挂起** | MUST 走**同一条**路径 ⇒ 值 = **空元组** `()`（B13F1 D-4）⇒ ⇒ **MUST NOT** 另写「静态中断 → 结果键」的转成路径 |
| **R-09** | **无挂起** | MUST **不**含 `"__interrupt__"` 键（出现次数 == 0） |
| **R-10** | **单一实现点** | 「稀疏视图 + 补齐」MUST 是**一个**实现点（L3 模块内的私有函数）⇒ ⇒ 下游 **B8F2** 的 `stream(values)` MUST **复用**它（下游承接 D-1）⇒ ⇒ **MUST NOT** 在门面层另写一份 |
| **R-11** | **只读快照** | ⚠️ 返回值是**只读快照**：**MUST NOT** 把返回值**原样回喂**给下一次 `invoke`（回喂会把补齐的 `None` **真的写进**通道 ⇒ 节点里 `state.get("llm_calls", 0) + 1` 会 `TypeError`）⇒ ⇒ 该禁令 MUST 写进**用户可见文档**（`invoke` 的 docstring + `README.md`）**并写明理由**（上游因省略无值 key 而回喂**安全** · 实测 E-5 ⇒ 这是 freegraph 的**已知代价**） |

---

## 4. 失败信号（**零捕获 · 原样传播**）

| # | 场景 | 失败信号 | 产生位置 |
|---|---|---|---|
| **F-01** | 节点返回**未知 key** | `InvalidUpdateError`（L1 · `contracts/errors.py:38-66`）· 消息**点名违规 key**（多个 ⇒ 含**全部**）· `.invalid_keys` 为元组 | L2 `_reject_unknown_keys`（`superstep.py:1047-1058`）⇒ **比上游更严**（上游静默忽略 · 实测 E-2）⇒ 偏离 **X-2** |
| **F-02** | 初始输入含**未知 key** | `InvalidUpdateError`（同上） | L2 `_apply_input_writes`（`superstep.py:1581`）⇒ **比上游更严**（上游只告警 · 实测 E-3）⇒ 偏离 **X-3** |
| **F-03** | 节点抛**真异常** | **原始类型 + 原始消息**（不包装） | 节点 ⇒ L2 ⇒ 门面**零捕获**⇒ 直达调用方（上游同款 · 实测 E-4） |
| **F-04** | `recursion_limit` 超限 | `GraphRecursionError`（**不包装**） | L2 `superstep.py:1706-1708` |
| **F-05** | 恢复失败（未挂 checkpointer / 未提供恢复值 / 多挂起歧义 / 无挂起中断） | `InterruptError`（带**封闭** `reason`）· **不**静默降级为内存态恢复 | L2 `superstep.py:2084-2145`（判定顺序 = B10F1 裁定 4） ⇒ ⇒ ⚠️ **恢复路径的 checkpointer 载体（2026-11-16 analyse 轮第三轮 · S-22）**：**「恢复后拿到 resume 值」MUST 挂 checkpointer** ⇒ ⇒ ⇒ `src/freegraph/**` 内**零** saver 实现（`MemorySaver` 归 **B14F1**）⇒ ⇒ ⇒ ⇒ ⇒ **载体 = 测试侧的「自足桩 checkpointer」**（tasks **T002** 交付 · 形态参照 `tests/differential/parity_probe.py:251-255`）⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 在 `src/` 内实现任何 saver（宪法原则 IV 的「内存态旁路」禁令 + 原则 VII 的 **C20** 冻结面） ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **桩的方法集 MUST 冻结（2026-11-16 analyse 轮第四轮 · M1 回修）** ——**实测 L2 的实际调用点**（`superstep.py:1873` / `:1885` / `:1904` / `:2007` / `:2092` / `:2169`） ⇒ ⇒ ⇒ ⇒ ⇒ **MUST 实现且仅需实现 3 个方法**：① `get_tuple(config)` —— 查不到 MUST 返 `None` · 返回时 MUST 带**三个具名属性**：`.snapshot`（**MUST** 带 `.values` / `.next` / `.interrupts` / `.tasks`）· `.pending_writes`（`task_id` / `channel` / `value` 三元组序列）· `.scheduler`（`dict` · 含 `suspension_kind` / `static_ack` / `fanout`） ② `put(config, values=…, metadata=…)`（**挂起**时与**静态恢复完成**时各写一次） ③ `put_writes(config, writes=…, task_id=…, task_path=…)`（**挂起**时写 interrupt 载荷 · **恢复**时写恢复值） ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **L2 恢复路径不调用**的 5 个协议方法（`list` / `delete_thread` / `delete_for_runs` / `copy_thread` / `get_next_version`）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 被桩依赖 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据**：桩「够不够」MUST 由**本行的方法集**判定 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 以「等最小集」这类开放表述留给实施期临场判断 |
| **F-06** | `config` 形态非法（非 `RunConfig` / 非映射 / `None` 以外） | `TypeError` | L2 `resolve_config`（`_recursion.py:45-47`） |
| **F-07** | `max_concurrency` 非法 | 类型不符 ⇒ `TypeError`；`< 1` ⇒ `ValueError`（均**点名该参数**） | L2 `superstep.py:1339-1361`（**入口即**失败）⇒ ⚠️ **关键字来源**在 `resolve_config` **之前**失败（既有顺序**逐字不变**）· **config 来源**在其**之后**失败（校验点 = `resolve_config` 之后 · `_first_graph` 之前） |
| **F-08** | `GraphInterrupt` 仍从 L2 抛出 | **原样**抛出（不吞、不假装跑完） | 兜底（B10F1 已把中断转成 `InterruptResult` ⇒ 正常路径**不**触达） |

> ⚠️ **门面 MUST NOT** 写任何 `try/except`（零捕获 ⇒ 「不包装 / 不吞掉」是**结构上**成立的）。

---

## 5. 跨 feature 接口（B7F3 冻结 · 下游 MUST 照写）

> ⚠️ **编号域**（2026-11-16 analyse 轮 · **M4**）：本节的 **`CF-01…CF-05`**（跨 feature 接口）**刻意区别于** spec / `upstream-parity.md` 的 **`X-1…X-6`**（偏离登记）—— ⇒ ⇒ ⇒ **两者不再同形** ⇒ ⇒ ⇒ ⇒ 消除歧义。

| # | 接口 | 冻结口径 | 下游 |
|---|---|---|---|
| **CF-01** | **「完整状态」的归一** | 「稀疏视图 + 补齐无值 key」= **一个**实现点；键集 == schema 全集（顺序 = schema 声明顺序）；路由通道**不进**键集 | **B8F2**（`stream` 的 `values` 档 MUST 复用 · 下游承接 **D-1**） |
| **CF-02** | **执行路径** | 门面**只**驱动 L2 的 `run_graph`；**MUST NOT** 另写「编译 → 执行」的路径 | **B8F1**（条件边路由在**同一条**路径上生效 · 下游承接 **D-2**） |
| **CF-03** | **就绪顺序** | `get_graph` / `draw_mermaid_png`（B22F1 / B23F1）MUST **先于** `invoke` 就绪 | **B22F1 / B23F1**（下游承接 **D-3**） |
| **CF-04** | **`checkpointer` 的落盘职责** | 门面**只透传**；落盘与 saver 归 B14F1 | **B14F1**（下游承接 **D-4**） |
| **CF-05** | **`config` 注解放宽的**归属边界** | 本 feature 只放宽 `CompiledGraph.invoke` 的 `config` 注解（`RunConfig \| Mapping[str, Any] \| None` · 裁定 1）⇒ ⇒ L1 的 `stream` / `get_state` / `get_state_history` / `update_state` **仍**是 `RunConfig \| None` ⇒ ⇒ ⇒ **这 4 处的放宽归** B8F2 / B15F1 / B16F1 **各自**走「登记 + 回溯修订 + 发起者追认」（宪法 v1.8.0 / v1.9.0）⇒ ⇒ ⇒ ⚠️ **本 feature MUST NOT** 代为放宽（**追认额度 ≤ 1 次 / feature** · 已用尽）⇒ ⇒ ⇒ ⇒ **下游 MUST 复用本 feature 已定的载体边界**（`RunConfig` = 会话面 + `max_concurrency`；普通映射 = 运行期参数 ⇒ **原样**交给 L2 ⇒ **MUST NOT** 在门面层翻译成 `RunConfig`） | **B8F2 / B15F1 / B16F1**（下游承接 **D-5**） |

> **状态更新（2026-11-22）**：B15F1 已交付`get_state` / `get_state_history` 的 `config`
> 注解放宽；B8F2 已交付 `stream`；`update_state` 待 B16F1。

---

## 6. 本契约的**自检**（实现期 MUST 逐条断言）

| # | 自检项 | 判据 |
|---|---|---|
| **I-01** | 返回键集 == schema 全集（顺序一致） | 键集**逐字相等**断言 |
| **I-02** | 无值 key 的值为 `None`；归约型通道的**类型空值**不被改写 | `None` 断言 + 类型空值断言 |
| **I-03** | 路由通道**不**在返回键集里 | 条件边图上断言 `"branch:to:*" not in out` |
| **I-04** | 挂起结果含 `"__interrupt__"`；未挂起**不含** | 出现次数断言 |
| **I-05** | 挂起结果的键集**同样** == schema 全集 **+** `__interrupt__` | 键集断言 |
| **I-06** | 未知 key ⇒ `InvalidUpdateError` 且消息含 key 名 | `pytest.raises` + 消息子串 |
| **I-07** | 真异常**原类型 + 原消息** | 类型**逐字相等** + 消息**逐字相等** |
| **I-08** | `GraphRecursionError` **不被包装** | `type(exc) is GraphRecursionError` |
| **I-09** | 连续两次 / 并发两次**互不干扰** | 结果**逐字比较** |
| **I-10** | `vars(compiled)` 的键数仍 == **11** | 精确集合断言（B7F2 冻结面） |
| **I-11** | 文档含「只读快照 / 不得回喂」**及理由** | 文档文本**子串**断言 |
| **I-12** | `invoke` 在合法路径上**不**抛 `NotImplementedError` | 退出码探针（`graph_core.py` 不再以 2 结束） |
| **I-13** | **多源汇合（屏障）**：屏障目标出现在**所有**源之后 | `add_edge(["a", "b"], "c")` ⇒ 执行序 `a`/`b` → `c` ⇒ 完整状态含 `c` 的写入 |
| **I-14** | ⚠️ **人工验证记录的守卫断言**（2026-11-16 analyse 轮 · **新增** · 判据级覆盖）：`harness/verification/B7F3/manual-verification.md` **存在** 且 含 **fake 模型轮** / **真实模型轮** 两轮的**非空实测输出**（**MUST NOT** 只写「符合预期」）且 含**发起者追认**文字（**五项** —— **唯一事实源 = spec.md「Assumptions」的「破面全集 5 类」**：① L1 `invoke` 的 `input` 注解放宽 ② L1 `invoke` 的 `config` 注解放宽 ③ L2 `run_graph` 的 `max_concurrency` 读取点（兼容扩展）④ **G19**「既有契约层矩阵行逐字未改」判据（新增 `MATRIX_ROWS_UPDATABLE_BY_B7F3` 白名单 · 只放行 `CompiledGraph` 一行）⑤ **四处**「invoke 未就绪」冻结断言的拆分替换）⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST** 在该记录**写就之后**才转绿（⇒ ⇒ **MUST NOT** 造成「永久红的 CI」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **「写记录」本身不构成判定覆盖**（宪法原则 VI v1.11.0 + v1.13.0 的「人工门禁类 SC」条款）| 文档**子串**断言 + **非空**正文断言 |
