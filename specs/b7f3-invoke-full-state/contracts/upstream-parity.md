<!-- authority: yes -->

# 上游对照底稿（Upstream Parity）—— B7F3

**Feature**: `B7F3` · **Spec**: [../spec.md](../spec.md) · **契约**: [invoke-contract.md](./invoke-contract.md)
**上游版本**: `langgraph` **1.2.11** + `langchain-core` **1.7.6**（取证于 2026-11-16 ·
`.venv/lib/python3.11/site-packages/`）
**上游同款依据**: 宪法 v1.12.0 原则 XI「上游优先」· 原则 VIII「证据纪律」

> **纪律**：① 每条上游行为断言 MUST 带 **版本 + `路径:行号`**；② **行为**断言 MUST 有**实测**支撑
> （本底稿 §1 的 **E-1…E-10**）；③ 同一分叉在「上游对照」与「偏离登记」两处的标注 MUST
> **逐字一致**（原则 XI 末条）；④ 「上游有、freegraph v1 没有」= **能力尚未交付**
> ⇒ 走 Out of Scope / 下游承接，**MUST NOT** 记为偏离。

---

## 1. 实测台账（E-1…E-10）

| # | 夹具 | 观察（**逐字**） | 结论 |
|---|---|---|---|
| **E-1** | `invoke({"messages": []})` | `{'messages': ['x']}` | 上游**省略**无值 key ⇒ 键集 ≠ schema 全集 |
| **E-2** | 节点返回 `{"messages": ["x"], "nope": 1}` | **不抛错**、**无告警** | 上游**静默忽略**未知 key |
| **E-3** | `invoke({"messages": [], "bogus": 1})` | **不抛错** | 上游**静默忽略**未知输入 key（只 `logger.warning`） |
| **E-4** | 节点 `raise Boom("原始消息 payload")` | 上抛 `__main__.Boom` · 消息「原始消息 payload」· `args == ('原始消息 payload',)` | 上游**原类型 + 原消息**传播 |
| **E-5** | `invoke(out1)`（把返回值原样回喂） | 节点看到 `{'messages': ['x'], 'llm_calls': 1}` | 上游回喂**安全**（省略 ⇒ 不注入 `None`）⇒ 对照 freegraph ⇒ **回喂会注入 `None`** |
| **E-6** | `invoke({...}, {"bogus_key": 1, "recursion_limit": 5})` | **不抛错** | 上游**忽略**未知 config 键 |
| **E-7** | `invoke(None)`（无 checkpointer） | `langgraph.errors.EmptyInputError`「Received no input for `__start__`」 | 上游在**新会话** + `input=None` ⇒ **显式失败**；freegraph ⇒ **照常跑**（B10F1 FR-013 末行） |
| **E-8** | 源码 + 构造 | `LastValue` ⇒ `MISSING`；`BinaryOperatorAggregate` ⇒ `typ()` | 上游的「类型空值」**只作内部初值**，**从不出现在返回字典里** |
| **E-9** | 源码 | `main.py:3913-3957` ⇒ `values` 档取最后一个 chunk ⇒ `return latest` | 上游返回**最终状态**（非增量） |
| **E-10** | 源码 + 构造 | ① `invoke({"messages": ["seed"], "llm_calls": 0})`（schema 里 `messages` 在前）⇒ 返回键序 = **`['messages','llm_calls']`** ② 把 schema 顺序**反转**后再 invoke ⇒ `['llm_calls','messages']` ③ `add_edge(["a","b"], "c")` + `START→a` / `START→b` ⇒ 返回 `{'messages': ['seed','a','b','c'], 'llm_calls': 0}` | ① 上游按「**schema 声明顺序**」返回（**不是** `['llm_calls','messages']`）② 顺序随 schema 声明顺序走 ③ **多源汇合（屏障）**的目标写入出现在**所有**源之后（**上游同款** · **静态多源边** · **非**条件边路由）|

---

## 2. 上游对照表（P-01…P-14）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 | 偏离 |
|---|---|---|---|---|---|---|
| **P-01** | `invoke` 的**方法名与入参形态** | `langgraph/pregel/main.py:3836-3838`（`input: InputT \| Command \| None`）· `:3839`（`config: RunnableConfig \| None = None`） | 同款：`input` 接受「状态字典 / `Command` / `None`」；`config` 为第二位置参数、缺省 `None` | SAME | 上游同款 ⇒ 原则 III 第 6 项 | — |
| **P-02** | 返回**完整状态**而非增量 | `main.py:3913-3944` · `:3946-3955`（`return latest`）· `pregel/_io.py:100-115` | 同款：最终状态（初始 + 全部新增） | SAME | 原则 XI 照抄 · 实测 E-9 | — |
| **P-03** | 返回**键集** = **有值**的 output channel | `pregel/_io.py:38-53`（`skip_empty=True` ⇒ `except EmptyChannelError: pass`）· `graph/state.py:127-131`（`output_channels` = output schema 的 key）· **实测 E-1 / E-5 / E-8** | 返回**全部 schema key**（含从未写入者 ⇒ ⚠️ **仅覆盖型（无归约器）通道**的值 = `None`；**归约型**通道未写时其稀疏视图里**已有**「类型空值」（`[]` / `0`）⇒ ⇒ **MUST NOT** 改写成 `None` · 契约 R-06）⇒ ⚠️ **代价**：返回值**不可**原样回喂（补的 `None` 会被写进通道）⇒ 该禁令 MUST 写进用户可见文档 | **STRICTER** | 原则 III 第 7 项 + C11；上游的「省略」让「键是否存在」取决于「恰好有没有写过值」⇒ 原则 XI ② 类 | **X-1** |
| **P-04** | 节点返回**未知 key** | **实测 E-2**（静默忽略）· `langgraph/errors.py:90-99`（`InvalidUpdateError` **不由**该路径抛出） | 抛 `InvalidUpdateError` 且消息**点名**违规 key | **STRICTER** | 原则 XI「失败信号 MAY 更严」+ C6 红线 | **X-2** |
| **P-05** | 初始输入含**未知 key** | `pregel/_io.py:81-97`（只 `logger.warning`）· **实测 E-3** | 沿用 L2 既有口径 ⇒ `InvalidUpdateError` | **STRICTER** | 同上；行为源自 B7F1 FR-007 ⇒ 本 feature 只透传 | **X-3** |
| **P-06** | 节点抛**真异常** | **实测 E-4** | 同款：原始类型 + 原始消息；不包装 / 不吞掉 | SAME | 原则 XI 照抄 | — |
| **P-07** | **中断**的对外形态 | `main.py:3949-3954`（`{**latest, INTERRUPT: interrupts}`）· `_internal/_constants.py:9` · 值 = **list** | `{**state, "__interrupt__": interrupts}` · 值 = **tuple** | DIFF（仅值形态） | 已由 **B10F1** 登记并追认 ⇒ 只透传 | **X-4**（已登记） |
| **P-08** | `config` 的**载体类型** | `main.py:3839`（`RunnableConfig`） | `RunConfig \| Mapping[str, Any] \| None`（双形态） | DIFF（载体面 · 非更严） | freegraph 的对应物是 L1 的 `RunConfig`（B2F1 冻结）⇒ 双形态是本项目已锁定形态 | — |
| **P-09** | `recursion_limit` | `_internal/_config.py:32`（缺省 `10007`，**读环境变量**）· `main.py:2563-2564` · `:3002-3011` | dict 形态**原样**透传；缺省**硬编码** `10007`（零环境变量）；超限抛 `GraphRecursionError`（不包装） | DIFF（缺省来源 · 非更严） | 零环境变量红线 ⇒ 已由 **B13F1** 登记 ⇒ 只透传（行为面 **SAME**）| **X-5**（已登记） |
| **P-10** | `max_concurrency` | `langchain_core/runnables/config.py:103-108` · `:659-675` | `RunConfig.max_concurrency`（同名同义 · `types.py:216`）· 缺省 `None` ⇒ `min(32, cpu+4)` ⇒ ⇒ ⚠️ **2026-11-16 clarify 轮（Q2 = B）**：旋钮的**读取点也落在 L2**（`run_graph` 关键字优先 · `config` 兜底）⇒ ⇒ 与上游**更同款** | SAME | 上游同款 ⇒ 裁定 13 · L1 的 `RunConfig` **零改动** · L2 的改动属**兼容扩展**（回溯修订 **T-3**） | — |
| **P-11** | 编译产物只持通道**规格** · 每次运行**新建实例** | `channels/last_value.py:50-54` · `channels/base.py:61-64` | 同款：每次 `invoke` 新建通道实例 | SAME | 上游同款 ⇒ 「一次编译、多会话隔离」天然成立 | — |
| **P-12** | 能力面（6 方法） | `main.py:845` / `:1392` / `:1480` / `:2515` / `:2616+` / `:3783+` | 6 方法**全部存在**；本 feature **只**交付 `invoke` ⇒ 其余 5 个仍抛内置 `NotImplementedError` 且**点名归属 feature** | DIFF（未就绪者的失败信号 · 非更严） | 方法面是 B2F1 冻结的协议（**SAME**）；未就绪者的失败信号已由 B7F2 冻结 | — |
| **P-13** | `invoke` 的**入口形态**（关键字面） | `main.py:3836-3850`（上游另有 `context` / `stream_mode` / `print_mode` / `output_keys` / `interrupt_before` / `interrupt_after` / `durability` / `control` / `version`） | `invoke(input, config=None)` ⇒ **已实现面**逐字一致；**无**上游的其它关键字（v1 不实现）⇒ ⚠️ `interrupt_before` / `interrupt_after` 在 freegraph 走 `compile(...)`（B13F1）· `context` 走 `RunConfig.context`（C21）⇒ 其余归 **B8F2 / v2 extras** | SAME（已实现面） | 「上游有、v1 没有」= **能力尚未交付** ⇒ 走 Out of Scope / 下游承接 ⇒ **MUST NOT** 记为偏离 | — |
| **P-14** | **`input=None`（无 checkpointer 的新会话）** | **实测 E-7** ⇒ 抛 `EmptyInputError`「Received no input for `__start__`」· `pregel/_loop.py` 的首轮入参校验 | **照常跑**（不写任何通道，图从入口起跑）⇒ ⇒ **比上游更宽松** | DIFF（阶段性差异 · 非更严 · 更宽松） | **行为源自 B10F1 FR-013 的末两行（已冻结）** ⇒ 本 feature **只透传** ⇒ ⇒ 若要向上游对齐 ⇒ 归 **B10F1** 的回溯修订 | **X-6** |

---

## 3. 差分场景（D-92…D-102）

> **落点**：`tests/differential/parity_probe.py` ⇒ **新增 `InvokeScenario` 模型**（与既有
> `CompileScenario` 同款）⇒ 接入 `run_all()` ⇒ 上游缺席即 **skip**（沿用 B5F2 的「缺席即 skip」纪律）。

| # | 场景 | 断言（返回键集 / 值 / 失败与否） | 判词 | 实测依据 |
|---|---|---|---|---|
| **D-92** | 最小图 + `invoke({"messages": ["seed"]})` | 两侧返回的 `messages` **逐字相等**（初始 + 全部新增） | SAME | E-9 |
| **D-93** | 初始输入含**全部** schema key | 两侧返回的**键集**逐字相等（`['messages','llm_calls']` · **上游按 schema 声明顺序**） | SAME | E-1 / **E-10** |
| **D-94** | 初始输入**缺**一个**覆盖型（无归约器）** schema key（如 `llm_calls` · 该 key 从未被写）⇒ ⚠️ **MUST** 用**覆盖型** key ⇒ 若误用**归约型** key ⇒ 其值是**类型空值**（`[]`）而非 `None` | 上游**省略**该 key；freegraph **保留**该 key（值 `None`）⇒ 键集**不等** | **STRICTER**（X-1） | E-1 / E-8 |
| **D-95** | 节点返回**未知 key** | 上游**不抛错**；freegraph 抛 `InvalidUpdateError` 且消息含该 key 名 | **STRICTER**（X-2） | E-2 |
| **D-96** | 初始输入含**未知 key** | 上游**不抛错**；freegraph 抛 `InvalidUpdateError` | **STRICTER**（X-3） | E-3 |
| **D-97** | 节点抛**真异常** | 两侧都抛**原异常**（类型与消息**逐字一致**） | SAME | E-4 |
| **D-98** | `config = {"recursion_limit": 3}` + 自环图 | 两侧都抛 `GraphRecursionError`；freegraph `.recursion_limit == 3` | SAME | 源码 `main.py:3002-3011` |
| **D-99** | 同一张编译图**连续两次** `invoke` | 两侧**都不累积**（第二次的结果**不含**第一次的新增） | SAME | P-11 |
| **D-100** | 同一张编译图**并发两次** `invoke` | 两侧**都不串扰**（两次结果**互不含**对方的值） | SAME | P-11 |
| **D-101** | 中断后 `invoke` 的结果 | 两侧都含 `__interrupt__` 键、元素逐字一致；freegraph = **tuple**、上游 = **list** | DIFF（仅值形态 · X-4 透传） | P-07 |
| **D-102** | **多源汇合（屏障）**：`add_edge(["a", "b"], "c")` + 两个源 | 两侧的**最终状态**逐字相等（`messages` 含 `seed,a,b,c`）⇒ ⇒ 屏障目标 `c` 的写入出现在**所有**源之后 | SAME | **E-10**（上游同款 · 静态多源边） |

⇒ **共 11 条**（D-92…D-102）⇒ ⇒ **判词分布**：**SAME 7**（D-92 / D-93 / D-97 / D-98 / D-99 / D-100 / **D-102**）
+ **STRICTER 3**（D-94 / D-95 / D-96）+ **DIFF 1**（D-101）⇒ ⇒ ⚠️ **STRICTER 的三条 MUST 各自带 `note`**
（`test_the_verdict_vocabulary_is_closed` 会强制检查）。

---

## 4. 偏离登记（X-1…X-6）

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **STRICTER**（成功路径的可观察状态 · 原则 XI ② 类） | **返回键集**：上游只返回**有值**的 output channel（`pregel/_io.py:38-53` · 实测 E-1 / E-8）⇒ freegraph 返回**全部 schema key**（无值者填 `None` ⇒ ⚠️ **仅覆盖型（无归约器）通道**适用；**归约型**通道未写时其稀疏视图里**已有**「类型空值」（`[]` / `0`）⇒ ⇒ **MUST NOT** 改写成 `None` · 契约 R-06） | 原则 III 第 7 项 + C11；上游的「省略」让「键是否存在」取决于「恰好有没有写过值」⇒ 用户被迫写 `.get(k, default)` ⇒ freegraph 让「**键一定在**」成为可依赖的事实 ⇒ ⇒ 属原则 XI ② 类 ⇒ ⇒ ⚠️ **已知代价**：返回值**不可**原样回喂（上游因省略而安全 · E-5）⇒ 以**文档禁令**消化（FR-009 · SC-020）⇒ ⇒ **用户 2026-11-16 拍板确认接受** | 本 feature 内闭合 · 追认文字落 `harness/verification/B7F3/manual-verification.md` · 差分 **D-94** 锁住 |
| **X-2** | **STRICTER**（失败信号） | 节点返回未知 key：上游**静默忽略**（E-2）⇒ freegraph 抛 `InvalidUpdateError` 且消息点名 | 原则 XI「失败信号 MAY 更严」+ C6 红线；「拼错的 key 无声地少跑」⇒ 差分 **D-95** 锁住 | 本 feature 内闭合 · 同上追认文字 |
| **X-3** | **STRICTER**（失败信号） | 初始输入含未知 key：上游只告警并忽略（`pregel/_io.py:81-97` · E-3）⇒ freegraph 抛 `InvalidUpdateError` | 同上；行为**已由 B7F1 FR-007 冻结** ⇒ 本 feature **只透传** ⇒ 差分 **D-96** 锁住 | 本 feature 内闭合（行为源自 B7F1） |
| **X-4** | **DIFF**（仅值形态 · 非更严） | `__interrupt__` 的值 = **tuple**（上游 = **list**） | 已由 **B10F1** 登记并追认 ⇒ 本 feature **只透传** ⇒ **不新增登记项** | **B10F1**（已追认） |
| **X-5** | **DIFF**（缺省来源 · 非更严） | `recursion_limit` 缺省**硬编码** `10007`（上游读环境变量） | 零环境变量红线（原则 I）· 已由 **B13F1** 登记 ⇒ **不新增登记项** | **B13F1**（已追认） |
| **X-6** | **DIFF**（阶段性差异 · 非更严 · **更宽松**） | `input=None`（无 checkpointer 的新会话）：上游抛 `EmptyInputError`（E-7）⇒ freegraph **照常跑** | **行为源自 B10F1 FR-013 的末两行（已冻结）** ⇒ 本 feature **只透传** ⇒ ⇒ ⚠️ 「更宽松」**不属**原则 XI 的「失败信号 MAY 更严」⇒ ⇒ ⇒ **如实登记、不掩盖**；⇒ 若要向上游对齐 ⇒ 归 **B10F1** 的回溯修订（**不是**本 feature 的义务） | **B10F1**（FR-013 已冻结）· 本 feature **不追认** |

> ⚠️ **三态标注一致性**（原则 XI 末条 · 2026-11-16 analyse 轮 · **D-C 决策** · M6）：本表 **STRICTER / DIFF** 标注与 §2 对照表的
> **对应行逐字一致**；每条偏离都有对照表的对应行（**X-1↔P-03** · **X-2↔P-04** · **X-3↔P-05** ·
> **X-4↔P-07** · **X-5↔P-09** · **X-6↔P-14**）⇒ ⇒ **判据零放宽**。
> ⇒ ⇒ ⚠️ **严格三态**（机械可判定）：§2 对照表的「关系」列与 §4 偏离登记的「类别」列**逐字相等**
> （`SAME` / `STRICTER` / `DIFF` 三态之一）⇒ ⇒ 一行含**多处分叉**时，复合关系在**理由**列**拆分说明**
> ⇒ ⇒ ⇒ **无孤行 / 无漏行**。
