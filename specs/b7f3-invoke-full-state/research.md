# 研究底稿（Research）—— B7F3 · `invoke()` 返回完整状态

**Feature**: `B7F3` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**核实环境**: CPython **3.11.16**（`.venv`）· 上游 `langgraph` **1.2.11** + `langchain-core` **1.7.6**
（取证于 2026-11-16 · `.venv/lib/python3.11/site-packages/`）

> **纪律**（宪法 v1.12.0 原则 XI + 原则 VIII）：**行为**断言 MUST 有**实测**支撑（只读源码不足）；
> 每条上游行为断言 MUST 带 **版本 + `路径:行号`**；本底稿的实测编号 **E-1…E-10** 与 spec 的
> **P-xx / D-xx / X-xx** 逐条对齐。

---

## 1. 上游实测（E-1…E-10）

> **取证方式**：在 `.venv` 里用**真实**的 `langgraph`（1.2.11）跑最小 `StateGraph`，
> schema = `{"messages": Annotated[list, operator.add], "llm_calls": int}`（与
> `harness/demo/graph_core.py:124-128` 的 `State` **逐字同款**）。

| # | 实测项 | 命令 / 夹具 | 观察结果（**逐字**） | 落点 |
|---|---|---|---|---|
| **E-1** | **`invoke` 的返回键集（输入缺一个 key）** | `invoke({"messages": []})` | 返回 `{'messages': ['x']}` ⇒ **`llm_calls` 被省略**（上游**不**补齐无值 key） | spec **P-03** · 差分 **D-94** |
| **E-2** | **节点返回未知 key** | 节点返回 `{"messages": ["x"], "nope": 1}` | **不抛错**、**无告警** ⇒ 上游**静默忽略**该 key（`langgraph/errors.py:90-99` 的 `InvalidUpdateError` **不由**该路径抛出） | spec **P-04** · 差分 **D-95** |
| **E-3** | **初始输入含未知 key** | `invoke({"messages": [], "bogus": 1})` | **不抛错** ⇒ 静默忽略（`langgraph/pregel/_io.py:81-97` 的 `map_input` 只 `logger.warning`） | spec **P-05** · 差分 **D-96** |
| **E-4** | **节点抛真异常** | 节点 `raise Boom("原始消息 payload")` | 上抛 **`__main__.Boom`**，消息**逐字**为「原始消息 payload」，`args == ('原始消息 payload',)` ⇒ **原类型 + 原消息**传播（**不包装**） | spec **P-06** · 差分 **D-97** |
| **E-5** | **把返回值原样回喂** | `invoke(out1)` | 节点看到 `{'messages': ['x'], 'llm_calls': 1}` ⇒ **安全**（上游省略无值 key ⇒ 回喂**不注入** `None`）⇒ ⇒ 对照：freegraph 补 `None` ⇒ 回喂会写入 `None` ⇒ **节点里 `state.get(k, 0) + 1` 会 `TypeError`** | spec **P-03** 的「代价」列 · 裁定 3 · **FR-009** |
| **E-6** | **上游的 `config` 未知键** | `invoke({...}, {"bogus_key": 1, "recursion_limit": 5})` | **不抛错** ⇒ 未知键被**忽略**（只挑认识的键）⇒ 与 freegraph 的 `RunConfig.from_dict(..., ignore_unknown=True)`（`runtime/_recursion.py:44`）**同款** | spec **FR-021** 的「未知键宽容忽略」 |
| **E-7** | **上游 `invoke(None)`（无 checkpointer 的新会话）** | `invoke(None)` | 抛 **`langgraph.errors.EmptyInputError`「Received no input for __start__」** ⇒ ⇒ ⚠️ **freegraph 更宽松**（B10F1 FR-013 末行：新会话 + `input=None` ⇒ 照常跑、不写任何通道） | spec **P-14**（新增）· 偏离 **X-6**（只透传 · 源自 B10F1） |
| **E-8** | **上游的通道初值** | 源码 + 构造 | `LastValue.__init__` ⇒ `self.value = MISSING`（**无初值**）；`BinaryOperatorAggregate.__init__` ⇒ `self.value = typ()`（**类型空值**：`list` → `[]`、`int` → `0`）⇒ ⇒ **上游的「类型空值」只作内部初始值，从不出现在返回字典里** | spec **P-03** · **裁定 3** 的填充值论证 |
| **E-9** | **上游 `invoke` 的返回来源** | 源码 | `langgraph/pregel/main.py:3913-3957`：`stream_mode="values"` ⇒ 取**最后一个** `values` chunk ⇒ `return latest`；该 chunk 由 `map_output_values`（`langgraph/pregel/_io.py:100-115`）⇒ `read_channels(channels, output_channels)` ⇒ ⇒ **上游返回的是「最终状态」而非增量** | spec **P-02** |
| **E-10** | **上游的返回键序 + 多源汇合（屏障）** | ① `invoke({"messages": ["seed"], "llm_calls": 0})`（schema 里 `messages` 在前）② 把 schema 顺序**反转**后再 invoke ③ `add_edge(["a", "b"], "c")` + `START→a` / `START→b` | ① 返回键序 = **`['messages','llm_calls']`** ⇒ **上游按「schema 声明顺序」返回**（**不是** `['llm_calls','messages']`）② 反转 schema ⇒ `['llm_calls','messages']` ⇒ **顺序随 schema 声明顺序走** ③ 返回 `{'messages': ['seed','a','b','c'], 'llm_calls': 0}` ⇒ **屏障目标 `c` 的写入出现在所有源之后**（**上游同款** · **静态多源边** · **非**条件边路由）⇒ freegraph 的 L2 实测**逐字一致**（`executed == ('a','b','c')`） | 差分 **D-93**（键序）· **D-102**（屏障） |

> **差分探针的固化**：E-1…E-10 中 E-1 / E-2 / E-3 / E-4 / E-5 / E-6 / E-7 落 **D-92…D-102**
> （spec §差分场景组 · **11 条**）⇒ plan **DD-11** ⇒ tasks 落 `tests/differential/parity_probe.py`。
> E-8 / E-9 属**结构面**断言（源码锚点 + 差分的可观察结果）；**E-10** 落 **D-93**（键序）与 **D-102**（屏障）。

---

## 2. 上游源码锚点（本次取证的逐字位置）

| 语义点 | 锚点（`langgraph 1.2.11`） | 逐字要点 |
|---|---|---|
| `invoke` 的签名 | `langgraph/pregel/main.py:3836-3850` | `input: InputT \| Command \| None` · `config: RunnableConfig \| None = None` · 另有 `context` / `stream_mode` / `print_mode` / `output_keys` / `interrupt_before` / `interrupt_after` / `durability` / `control` / `version` |
| `invoke` 的返回值 | `langgraph/pregel/main.py:3913-3957` | `values` 档 ⇒ `latest`；挂起时 `{**latest, INTERRUPT: interrupts}`（`:3949-3954`） |
| `INTERRUPT` 常量 | `langgraph/_internal/_constants.py:9` | `INTERRUPT == "__interrupt__"` |
| 稀疏读 | `langgraph/pregel/_io.py:38-53` | `skip_empty=True` ⇒ `except EmptyChannelError: pass` ⇒ **省略**无值 channel |
| 单键读 | `langgraph/pregel/_io.py:23-35` | `catch=True` ⇒ 无值时返回 `None`（**但 `invoke` 走的是多键路径 ⇒ 不适用**） |
| 输入映射 | `langgraph/pregel/_io.py:81-97` | 不在 `input_channels` 的 key ⇒ **只** `logger.warning` |
| `Command` 映射 | `langgraph/pregel/_io.py:56-78` | `resume` ⇒ `(NULL_TASK_ID, RESUME, value)`；`update` ⇒ 逐 key 写入 |
| `Command` 输入的判定 | `langgraph/pregel/_loop.py:848-931` | `resume is not None` 且**无 checkpointer** ⇒ `RuntimeError`（上游）⇒ freegraph 换 `InterruptError`（B10F1 **X-2**） |
| `recursion_limit` 缺省 | `langgraph/_internal/_config.py:32` | `int(getenv("LANGGRAPH_DEFAULT_RECURSION_LIMIT", "10007"))` ⇒ **读环境变量**（freegraph 硬编码 · **X-5**） |
| `recursion_limit` 校验 | `langgraph/pregel/main.py:2563-2564` | `< 1` ⇒ `ValueError` |
| `recursion_limit` 超限 | `langgraph/pregel/main.py:3002-3011` | ⇒ `GraphRecursionError` |
| `max_concurrency` | `langchain_core/runnables/config.py:103-108` · `:659-675` | `int \| None`；`get_executor_for_config` ⇒ `ContextThreadPoolExecutor(max_workers=…)` |
| 通道只持规格 | `langgraph/channels/last_value.py:50-54` · `langgraph/channels/base.py:61-64` | `from_checkpoint` ⇒ `self.__class__(…)`；docstring「Return a **new identical channel**」 |
| `InvalidUpdateError` | `langgraph/errors.py:90-99` | 上游 = **plain `Exception`**（无结构化属性）；freegraph 的 L1 版带 `.invalid_keys` ⇒ **更严** |
| `GraphInterrupt` | `langgraph/errors.py:102-107` | `args[0]` = 中断序列（freegraph 同款） |

---

## 3. freegraph 侧的既有能力盘点（**MUST 复用 · MUST NOT 重写**）

| # | 既有能力 | 位置 | 本 feature 的用法 |
|---|---|---|---|
| **EX-01** | **图级执行入口** `run_graph(spec, input=None, *, state=None, checkpointer=None, config=None, max_steps=10007, max_concurrency=None) -> SuperStepResult \| InterruptResult` | `src/freegraph/runtime/superstep.py:1918-1990` | 门面**唯一**的执行路径（FR-002）⇒ MUST NOT 另写 |
| **EX-02** | **输入写入路径** `_apply_input_writes` | `superstep.py:1566-1590` | 归约 / 覆盖语义 + **未知 key ⇒ `InvalidUpdateError`**（`:1581` → `_reject_unknown_keys` `:1047-1058`）⇒ 门面**只调**、不另写 |
| **EX-03** | **稀疏状态唯一产出点** `_sparse_state` | `superstep.py:1334-1336` ⇒ `read_channels(_run_channels(spec, state))` | 补齐的**基线**（**稀疏**）⇒ 补齐逻辑 MUST 建在它之上 |
| **EX-04** | **「异常 → `__interrupt__` 键」的唯一转成路径** `InterruptResult.as_result_dict()` | `superstep.py:406-418`（docstring `:415-416` 明写「**B7F3 MUST NOT** 另写」） | 挂起时的**唯一**转成（FR-014）⇒ ⚠️ 其 `.state` **也是稀疏** ⇒ 补齐 MUST 在其**之后** |
| **EX-05** | **稀疏读原语** `read_channels(channels, *, skip_empty=True)` | `src/freegraph/runtime/read.py:136-160` | 键**保序**；值为 `None` **出现**、无值**缺席** |
| **EX-06** | **路由型通道的冻结判定** `isinstance(channel, EphemeralValue)` | `specs/b7f1-superstep-loop/spec.md:547-551`（FR-014 末条）· 契约 `:241` | 补齐时**扣除**路由通道（裁定 4）⇒ MUST NOT 用「`branch:to:` 前缀」启发式 |
| **EX-07** | **通道实例的按运行新建** `_run_channels` | `superstep.py:575-591`（`template.from_checkpoint(template.checkpoint())`） | 每次 `invoke` **新建**实例（裁定 10 · H-2）⇒ 门面**不传** `state=` 即可 |
| **EX-08** | **调度状态的按调用新建** `SchedulerState()` | `superstep.py:1965`（`state is None ⇒ SchedulerState()`）· 字段 `:260-266` | 同上 ⇒ 「每次 invoke 内部自洽」（FR-005） |
| **EX-09** | **并发度校验（入口即）** `_validate_max_concurrency` | `superstep.py:1339-1361`（非 `int` ⇒ `TypeError`；`< 1` ⇒ `ValueError`；均点名参数） | 非法取值的失败信号**由 L2 产出**（FR-023 · 裁定 13）⇒ ⚠️ **2026-11-16 clarify 轮（Q2 = B）**：旋钮的**读取点也在 L2**（`run_graph` 关键字优先 · `config` 兜底）⇒ ⇒ **门面零搬运逻辑** |
| **EX-10** | **递归上限的载体与优先级** `resolve_config` / `resolve_limit` / `validate_limit` | `src/freegraph/runtime/_recursion.py:30-80`（`config.recursion_limit` > `max_steps` > 硬编码 `10007`） | dict 形态的 `recursion_limit` **原样**交给 L2（FR-022 · H-5） |
| **EX-11** | **L1 的异常家族** `InvalidUpdateError` / `GraphRecursionError` / `GraphInterrupt` | `src/freegraph/contracts/errors.py:38-66` / `:69-99` / `:102-129` | 门面**零捕获** ⇒ 原样到达调用方（FR-016…FR-020） |
| **EX-12** | **编译产物的持有面**（3 私有 + 8 公开） | `src/freegraph/_stategraph.py:233-257` · `tests/facade/test_compiled_graph.py:111-114`（`vars()` 恰 11 键） | 门面**只读** `_spec` + `checkpointer` ⇒ **MUST NOT** 增第 4 个私有字段（FR-012 / FR-028） |

> ⚠️ **编号域**（2026-11-16 analyse 轮 · **M4**）：本节的 **`EX-01…EX-12`**（既有能力盘点）
> **刻意区别于** 契约 §2 的 **`ES-01…ES-11`**（执行语义条款）· 契约 §3 的 **`R-01…R-11`**（返回值契约）
> 与 plan 的 **`R-1…R-17`**（风险）⇒ ⇒ ⇒ **四者不再同形**。
> ⇒ ⇒ ⇒ ⚠️ **另**：本底稿 §1 的 **`E-1…E-10`** = **上游实测证据**（与契约 §2 的 `ES-` 刻意区别）
> ⇒ ⇒ ⇒ ⇒ **凡「实测 E-n」皆指本底稿 §1 的那一条**（如「实测 E-6」= 上游忽略未知 config 键）。
>
> ⚠️ **EX-12 的跨 feature 授权**：`specs/b7f2-compile/contracts/compile-contract.md:219`
> —— 「**B7F3** | `compiled._spec`（交给 `run_graph`）· `compiled.checkpointer` | **读** | 改写 `_spec`；另建执行路径」。

---

## 4. 设计决策（DD-1…DD-12）

| # | 决策 | **Decision** | **Rationale** | **Alternatives considered** |
|---|---|---|---|---|
| **DD-1** | `invoke` 的实现落点 | 原地替换 `src/freegraph/_stategraph.py:259-261` 的桩（`CompiledGraph.invoke`）⇒ **零新增源文件** | 层注册表把 `_stategraph.py` 登记为**文件级 L3** ⇒ 新建 `_invoke.py` 会构成 **L3 → L3** 违规（G25）⇒ 同模块是代价最小的形态（B7F2 **DD-02** 的同款论证） | ① 新建 `src/freegraph/_invoke.py` ⇒ G25 红 / 需改冻结的层注册表 ✗；② 把实现放进 `runtime/` ⇒ 违反 L2 只依赖 L1（ARCH-1）✗ |
| **DD-2** | 「完整状态」的归一函数 | `src/freegraph/_stategraph.py` 内的**模块级私有函数** `_full_state(spec, sparse) -> dict`（**单一实现点**） | ① 下游承接 **D-1** 要求 B8F2 的 `stream` **复用**同一份补齐逻辑 ⇒ 必须有**单一实现点**；② 它只依赖**既有**字段（`_spec.channels`）+ **既有**原语（`EphemeralValue` 判定）⇒ 零新增 L2 导出面（`freegraph.runtime.__all__` 23 符号冻结） | ① 放进 `freegraph.runtime` ⇒ **扩 L2 导出面** ⇒ 破 B10F1 的 `FR-021` / 冻结 manifest ✗；② 写成 `CompiledGraph` 的**方法** ⇒ **扩能力面面**（B2F1 协议 6 方法冻结）✗；③ 内联在 `invoke` 里 ⇒ B8F2 必然重写一份（违反 D-1）✗ |
| **DD-3** | 驱动路径 | `run_graph(self._spec, input, checkpointer=self.checkpointer, config=config)` ⇒ **不传 `state=`** ⇒ ⇒ ⚠️ `max_concurrency` **不由门面传**（读取点在 L2 · DD-4） | ① 「每次 invoke 内部自洽」（FR-005 · 裁定 27）⇒ 不传 `state` ⇒ L2 自建 `SchedulerState()`（EX-08）⇒ 并由 `_run_channels` 新建通道实例（EX-07）⇒ **多会话隔离**自动成立；② `run_graph` 是**唯一**图级入口（EX-01）⇒ MUST NOT 另写执行路径 | ① 传一个复用的 `state` ⇒ 两次调用的「已消费版本」串扰 ✗；② 先调 `run_super_steps` 再自己拼 ⇒ 另写执行路径 ✗ |
| **DD-4** | `max_concurrency` 的**读取点** | ⚠️ **2026-11-16 clarify 轮 · 用户拍板（Q2 = B）**：**下沉到 L2** —— `run_graph` 在**关键字缺省时**回落到 `config.max_concurrency`（**关键字优先**）⇒ ⇒ **兼容扩展**（既有调用方零改动 · 关键字的失败顺序**逐字不变**：其校验仍在 `resolve_config` 之前）⇒ ⇒ ⇒ 门面层**零搬运逻辑** ⇒ ⇒ ⇒ 回溯修订 B10F1 / B12F1 的契约行（破冻结面 **T-3**） | ⚠️ **本次上游/内核自查的新发现**：`run_graph` **只**从**关键字参数**读 `max_concurrency`（`superstep.py:1964`），**从不**读 `run_config.max_concurrency` ⇒ ⇒ 若门面不搬运，L1 的 `RunConfig.max_concurrency`（`types.py:216`）**永远不生效** ⇒ ⇒ 而 L2 的两个**低层**入口（`run_super_step` / `run_super_steps`）又**只**收关键字 ⇒ ⇒ **初版结论已作废**（2026-11-16 clarify 轮）—— 上游的旋钮本就住在 **config** 里 ⇒ ⇒ 「门面搬运」是**绕过根因**的次优解 ⇒ ⇒ 改由 **L2 读取**（更根本 · 原则 XII）⇒ ⇒ 代价 = **回溯修订** B10F1 / B12F1 的契约行 + 并入**那一次**追认（B12F1 裁定 18 说「将来 B7F3 若要让它对用户可见，可**原样**搬进 `RunConfig`」⇒ 本次落地该搬运） | ① **改 L2 读 `config.max_concurrency`**（**✅ 选定** · 2026-11-16 clarify 轮）⇒ **兼容扩展**（签名一字不动 · 关键字优先 · 关键字的失败顺序逐字不变）⇒ ⇒ ② 扩 L2 导出面 ✗；③ 门面把整个映射翻译成 `RunConfig` ⇒ 违反 FR-021「MUST NOT 翻译」✗；④ **只定点读取一个键**（门面侧搬运）⇒ 绕过根因的次优解（**初版结论 · 已作废**）✗ |
| **DD-5** | `config` 的两形态 | **原样**传给 `run_graph(config=...)` ⇒ 由 L2 的 `resolve_config` 归一（`RunConfig` 原样 / `Mapping` ⇒ `from_dict(..., ignore_unknown=True)` / 其它 ⇒ `TypeError`） | ① FR-021「原样交给 L2」+「MUST NOT 在门面层翻译」；② `recursion_limit` 的**优先级**（`config` > `max_steps` > 硬编码 `10007`）由 L2 的 `resolve_limit` 承担（EX-10）⇒ 门面**不**参与优先级判定 | ① 门面自己解析 `recursion_limit` ⇒ 另写解析路径 ✗；② 门面把 `config` 规整成 `RunConfig` 再传 ⇒ 违反 FR-021 ✗ |
| **DD-6** | 挂起结果的归一**顺序** | ① 若是 `InterruptResult` ⇒ **先**调 `as_result_dict()`（唯一转成路径 · EX-04）② **再**按 schema key 顺序补齐无值 key（**保留** `__interrupt__` 键，不覆盖、不重排） | ⚠️ **口径冲突的消解**：`as_result_dict()` 的 `.state` 是**稀疏**（EX-03 / EX-04）⇒ 若**逐字**返回它 ⇒ 挂起时的键集 ≠ schema 全集 ⇒ 与 **FR-008**（100% 齐全）冲突 ⇒ ⇒ ⇒ **唯一自洽读法**：「转成路径只此一条」指的是「**产生 `__interrupt__` 键的那一步**」（EX-04 的 docstring 正是这个意思），而「**补齐**」是**其后**的**独立一步**、对两条路径**同款** ⇒ ⇒ ⇒ 最终键集 = schema 全集 **+**（挂起时）`__interrupt__` | ① 挂起时**不**补齐 ⇒ FR-008 在挂起路径上不成立 ✗；② 另写一条挂起专用的转成 ⇒ 违反裁定 8 / EX-04 ✗；③ 把补齐写进 `as_result_dict` ⇒ 改 L2 冻结面 ✗ |
| **DD-7** | 错误传播 | 门面**零 `try/except`** ⇒ L2 的失败信号（`InvalidUpdateError` / `GraphRecursionError` / `InterruptError` / 用户异常）**原样**到达调用方 | ① FR-016…FR-020「原始类型 + 原始消息 · MUST NOT 包装 / 吞掉」；② `run_graph` 已把 `GraphInterrupt` 转成 `InterruptResult`（`superstep.py:1739-1740`）⇒ 门面**看不到**它 ⇒ FR-020 是**自动满足**的兜底；③ **零捕获**是达成「不包装」的**最简**方式（写 `try/except` 才有包装风险） | ① `except Exception: raise RuntimeError(...)` ⇒ 违反 FR-017 ✗；② 捕获后转成返回值 ⇒ 违反「MUST NOT 吞掉」✗；③ 捕获 `GraphInterrupt` 再转换 ⇒ 违反裁定 8（转成路径只此一条）✗ |
| **DD-8** | `input` 的形态 | 全部**原样**交给 `run_graph`（`StateDict \| Command \| None`）⇒ 门面**不判**输入形态 | ① FR-013 / FR-015：初始写入语义、恢复判定表、**会话连续**三支**全部**在 L2（B10F1 FR-013 的表 + B7F1 的写入路径）⇒ ⇒ 门面**只驱动** ⇒ ⇒ 判定表**不在**门面另抄（宪法 + 裁定 7） | ① 门面自己写「是 `Command` 就走恢复」⇒ 另抄判定表 ✗；② 门面自己把 `input` 写进通道 ⇒ 违反「MUST NOT 另写一条写入路径」（裁定 6）✗ |
| **DD-9** | L1 协议的放宽 | `src/freegraph/contracts/protocols.py:270-272` 的 `invoke` 签名改为 `input: StateDict \| Command \| None` + `config: RunConfig \| Mapping[str, Any] \| None = None`；**两处同属一次**登记 + 回溯修订 + 追认 | ① 裁定 1 + clarify 轮（用户拍板）；② 协议面写不准 ⇒ 下游（B8F2 / B15F1）会照错口径写；③ 与 L2 的 `run_graph`（`superstep.py:1920` / `:1924`）**逐字同款** | ① 不放宽（协议只写 `StateDict`）⇒ 契约**说谎** ✗；② 放宽 `input` 但不放宽 `config` ⇒ FR-002 无法落地 ✗；③ 放宽成 `dict[str, Any]`（而非 `Mapping`）⇒ 比 L2 更窄 ⇒ **L3 → L2** 口径不一致 ✗ |
| **DD-10** | 文档 | `invoke` 的 **docstring** + `README.md` 的兼容矩阵行 MUST 含「返回值是**只读快照**、**不要原样回喂**」**及理由** | ① SC-020；② 补齐带来的**已知代价**（E-5 对照）MUST **当场可见**；③ README 的 `StateGraph` 行现写「`invoke` 待 B7F3」⇒ MUST 事实性更新（⚠️ **`StateGraph` 行属**门面层 7 符号 ⇒ 不参与 G19 的字节比对 ⇒ 可改**；⚠️ **`CompiledGraph` 行属**契约层 18 符号 ⇒ 受 G19「既有契约层矩阵行逐字未改」保护 ⇒ **原不在任何白名单** ⇒ ⇒ **须由 B7F3 新增 `MATRIX_ROWS_UPDATABLE_BY_B7F3` 白名单**并登记进 spec 的破冻结面清单 ⇒ ⇒ **并入那唯一一次追认**） | ① 只在 spec 里写 ⇒ 用户**看不到** ✗；② 只写禁令不写理由 ⇒ 用户不知道为什么 ✗； |
| **DD-11** | 差分探针 | `tests/differential/parity_probe.py` 新增 **`InvokeScenario`** 模型（与既有 `CompileScenario` 同款：`fg` / `up` 两个 callable + `verdict` + `note`）⇒ 落 **D-92…D-102** ⇒ 接入 `run_all()` ⇒ `test_parity_probe.py` 加包装 **且** 纳入 `test_the_verdict_vocabulary_is_closed` 的循环 | ① 既有三套模型（runtime / builder / compile）都是**独立 dataclass + 独立注册函数 + 独立 pytest 包装** ⇒ 照此同款 ⇒ ⇒ ② 判词词汇表的封闭性检查**必须**纳入新模型，否则新场景**逃逸**该检查 | ① 复用 `Scenario`（runtime 模型）⇒ 它的形状（channels / initial / nodes / edges）与「门面级 invoke」**不匹配**（要跑图、要比较两侧的返回字典）✗；② 不加模型、只加用例 ⇒ 无从承载 `invoke` 的比较语义 ✗ |
| **DD-12** | 就绪探针与门禁风险 | `harness/demo/graph_core.py:555-571` 的 `_invoke_ready()` 以 **`except NotImplementedError` ⇒ 未就绪**判定 ⇒ `invoke` 交付后探针返回 **True** ⇒ 脚本**正常跑全部用例** ⇒ ⚠️ **G29 的判定 2**（「非 `NotImplementedError` 的失败 ⇒ FAIL」）⇒ 本 feature **必须**让 `graph_core.py` / `agent_loop.py` **全绿** | ① 探针判据**不动**（它键在 `NotImplementedError` 上 ⇒ 自动切换）⇒ ⇒ ② ⇒ ⇒ **风险**：一旦有真实断言失败 ⇒ G29 **红** ⇒ ⇒ ⇒ 本 plan 把「两个验收脚本全绿」列为**合入前置** | ① 把探针改成「6 方法齐备即就绪」⇒ 会在 `invoke` 未就绪时**假装就绪** ✗（B7F2 **DD-15** 的同一教训）；② 保留 rc==2 ⇒ 与「invoke 已交付」矛盾 ✗ |

---

## 5. plan 阶段自查发现的 6 处 spec 口径问题（**回修清单 S-1…S-6**）· analyse 轮追加 **S-7…S-11** · 跨工件对齐审查追加 **S-12…S-18** · analyse 轮第三轮追加 **S-19…S-26** · analyse 轮第四轮追加 **S-27…S-37** · analyse 轮第五轮追加 **S-38…S-45**

> **纪律**：plan 阶段的上游 / 内核自查若发现 spec 的口径不完整或自相矛盾，MUST 如实登记并
> **最小回修**（MUST NOT 放宽判据）。

| # | 问题 | 证据 | 处置（**已回修 spec**） |
|---|---|---|---|
| **S-1** | spec 的破冻结面清单把 `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt` 列为 `invoke` 签名行的回溯修订目标 | 该快照**只渲染门面导出面**（`freegraph.graph` 的 7 个符号）⇒ **不含** `invoke` 行（实测 `grep` 命中 0）⇒ ⇒ 改它 ⇒ **G16 逐字节红** | 清单的 ③ 改为 `specs/b2f1-contracts-protocols/contracts/public-api.md:82`（`CompiledGraph` 行）+ `:195`（C11 行）⇒ **快照 MUST NOT 改** |
| **S-2** | FR-014 说「挂起时 MUST 返回 `InterruptResult.as_result_dict()`」；而该方法的 `.state` 是**稀疏** ⇒ 与 FR-008（键集 == schema 全集）**冲突** | `superstep.py:406-418` + `:1334-1336` | FR-014 改为「MUST 走 `as_result_dict()` 这**唯一**转成路径（产出 `__interrupt__` 键）⇒ ⇒ **再**按 FR-008 补齐无值 key（**保留**该键）」⇒ 裁定 8 同步加注 |
| **S-3** | Assumptions 的「L1 冻结面」条仍写「唯一破面 = `input` 注解放宽」 | clarify 轮已把 `config` 注解一并放宽（同属一次追认） | 改为「**两处**（`input` + `config`）· **同一次**登记 / 回溯修订 / 追认」 |
| **S-4** | 承接条款 **H-4** ① 只提 `input` 注解的放宽 | 同上 | 补上 `config` 注解的放宽（逐字按裁定 1 + clarify 轮） |
| **S-5** | 上游 `invoke(None)` 在**无 checkpointer 的新会话** ⇒ 抛 `EmptyInputError`（**实测 E-7**）；freegraph ⇒ **照常跑**（B10F1 FR-013 末行）⇒ spec 的上游对照表**未覆盖**该面 | E-7 · `specs/b10f1-interrupt-resume/spec.md` FR-013 末两行 | spec 新增 **P-14**（DIFF · 只透传）+ 偏离登记 **X-6**（DIFF · 行为源自 B10F1 · 本 feature 不追认）⇒ ⇒ 判词**零放宽**（freegraph 的既有口径**如实登记**，不掩盖） |
| **S-6** | `harness/demo/graph_core.py:509-512` 的 `not hasattr(cfg, "configurable")` 与**已冻结**的 `RunConfig`（**有** `configurable`）矛盾 ⇒ 该断言**已红**（只在 `invoke` 就绪后才可达） | `graph_core.py:509-512`（断言）⇄ `types.py:215`（`RunConfig.configurable` **已冻结**）⇒ invoke 就绪后该行**可达** ⇒ 变红 | **plan 阶段登记**（不在本底稿的 §1 实测面）⇒ plan **R-3** + 改动面 §8 / §E2 ⇒ **MUST** 修（`cfg.configurable == {}`）⇒ ⇒ 属**验收脚本**（可改），**不**触及只读基准 |
| **S-7** | spec 的破冻结面清单只列 2 处「invoke 未就绪」冻结断言，漏 `test_facade.py:195-200` / `:217-234`（plan / tasks 均按 4 处计） | 实测确认两处断言存在 | **回填 spec 为 4 处**（拆而不删）+ 追认文字改「四处」 |
| **S-8** | **SC-018 无判定任务**（违反宪法原则 VI v1.11.0）+ 「两轮」若指固定脚本则物理不可达成 | 宪法原则 VI v1.11.0 + 宪法 v1.6.0 的分阶段窄口径 | spec 的 SC-018 补「两轮定义」+「判据级覆盖」；**登记 EV-4**；契约新增 **I-14** |
| **S-9** | SC-006 的「可观测并发度」判据依赖**时序竞争** | 仓库历史 commit `88331ed`（修「时序测量假红」） | spec 的 SC-006 补「测量 MUST 确定性」条款（判据数值不变） |
| **S-10** | 差分 D-94 未指明缺失 key 的类型 | FR-009 的消歧（归约型未写 ⇒ 类型空值） | D-94 指明用**覆盖型** key |
| **S-11** | 编号漂移：D-92…D-101（漏 D-102）/「10 条」（实为 11）/ SC-010 的 `.id**` 笔误 / E-1…E-9 vs 实际的 E-1…E-10（⇒ upstream-parity §3 的 E-10 悬空） | `grep` 全量核对 + 逐条读 | 全部**事实性订正**（11 条 / E-10 入台账 / 笔误）· 判据零放宽 |

| **S-12** | 偏离登记的「类别」列**原**写「更严（…）」⇒ 与对照表的 `STRICTER` **分类词不同** ⇒ 违反**宪法原则 XI 末条**（三态标注 MUST 逐字一致）⇒ 且偏离仓库先例 **B10F1** 的写法 | **已回修**：X-1 / X-2 / X-3 的「类别」列加 `STRICTER` 令牌（与 B10F1 同款）⇒ 判据零放宽 |
| **S-13** | spec **SC-017** 的判词分布括注**挂错对象**（「7/3/1」是差分场景组的分布，对照表实为「6/3/5」） | **已回修**：SC-017 括注改挂「差分场景组」并给出对照表真实分布 |
| **S-14** | 「无值 key 填 `None`」在 12 处重述、限定分裂（6 处带「仅覆盖型」限定 / 6 处未带）⇒ 归约型通道未写时值是**类型空值** | **已回修**：spec 裁定 3 / FR-009 首句 / Edge Cases / Key Entities · 契约 R-03 · data-model §2.5 全部补限定 ⇒ 判据零放宽 |
| **S-15** | 契约 §2 的条款编号 `E-01…E-11` 与**实测台账** `E-1…E-10` 同前缀不同义（同表歧义） | **已回修**：契约 §2 改为 `ES-01…ES-11` + 加编号域注；research §3 的编号域注扩为四者 |
| **S-16** | 提示词初稿的 `SC-001…SC-005` 与 spec 的 `SC-001…SC-020` 编号同形、含义不同 | **已回修**：spec 的「引文差异」表新增第 11 条（提示词的 SC 编号作废） |
| **S-17** | 第 4 处冻结断言的替换判据**原**写「不再是 2」⇒ 真失败（rc == 1）仍判绿 ⇒ 判据被弱化 | **已回修**：spec / plan / tasks 三处统一改为「脚本成功 = `rc == 0`」⇒ 判据**收紧** |
| **S-18** | plan 的 Phase 0 混含前置与后置项（与自身 GATE 声明冲突）· 0.4 要写 `manual-verification.md` 而该文件由 T044 创建 | **已回修**：Phase 0 拆为「Phase 0（前置）+ Phase 0′（后置 · = T011）」；0′.1 的产出落任务自带 note、T044 转录 ⇒ 零永久红窗口 |
| **S-19** | plan Summary 的「执行路径」写 `max_concurrency=...` ⇒ 与 DD-3 / DD-4 / 契约 ES-01 / tasks T010·T026 冲突 | **已回修**：删去该关键字 ⇒ 门面恒不传（旋钮读取点在 L2）⇒ 判据零放宽 |
| **S-20** | plan 两处仍写「不再是 2」（弱化判据） | **已回修**：统一为「脚本成功 = `rc == 0`」⇒ 判据收紧（对齐 S-17 / 宪法 v1.14.0） |
| **S-21** | 任务阶段编排导致 Phase 2 → Phase 10 红窗（脚本修复排在 Phase 10） | **已回修**（发起者拍板）：T040 / T041 / T042 前移至 **Phase 2′**、T014 移至本阶段末尾 ⇒ 红窗收敛为阶段内有界窗口 |
| **S-22** | SC-010 的「恢复取值」缺 checkpointer 载体（`src/` 内零 saver） | **已回修**：载体 = 测试侧「自足桩 checkpointer」（T002 交付 · T029① 挂它）⇒ 判据不放宽 · MUST NOT 在 `src/` 实现 saver |
| **S-23** | 「无值 key 填 `None`」在 spec P-03/X-1 与 upstream-parity P-03/X-1 四处缺「仅覆盖型」限定 | **已回修**：四处补限定 ⇒ T052 必查项① 由 12 处扩到 16 处 |
| **S-24** | 验收脚本用例组清单漏「A6 的 C17 段（中断与恢复）」 | **已回修**：该段保持硬断言（挂起半边）· 恢复半边沿用 soft ⇒ MUST NOT 整体降级 |
| **S-25** | 同文件 `[P]` 冲突（T022/T023、T025/T027、T040/T041）· T037 依赖 T036 却标 `[P]` · 追溯表 T002/T008 与正文不符 · FR-006「步末清空」无用例 | **已回修**：T023/T027/T037/T041 去 `[P]` · 追溯表 T002/T008 订正 · T031 增 ④（步末清空用例） |
| **S-26** | R-9 误引 DD-5 · I-01\|I-13 漏 I-14 · Edge Cases 漏 `get_state_history()` · T045 未强调「追认由发起者本人作出」· 裁定 11–16 无 Q&A 出处 · 门禁 7 实际可达 | **已回修**：DD-5→DD-2 · I-13→I-14 · Edge Cases 补方法 · T045 补签署主体 · 裁定表补来源注 · EV 表补门禁 7 可达性说明 |

> **S-1…S-5 的共同纪律**：**只补口径、不放宽判据**；每一条都带**可核对的证据**（实测 / 源码锚点 /
> 门禁清单），并在 plan 的「改动面」表里**逐条列明**。

---

## 6. 未决项（**零**）

| 项 | 结论 |
|---|---|
| `[NEEDS CLARIFICATION]` | **零**（spec 的 Clarifications 已写死 16 条裁定 + clarify 轮 2 条用户裁定） |
| 上游版本 | `langgraph 1.2.11` · `langchain-core 1.7.6`（**钉死** · 换版本 MUST 重新核实全部锚点） |
| 技术选型 | **零新增依赖**；`langgraph==1.2.11` 只在 `differential` 依赖组（测试侧） |
| Lint / Typecheck | 仓库**无** ruff / mypy 配置（`pyproject.toml` 无 `[tool.ruff]` / `[tool.mypy]`；CI 无 lint / typecheck 步骤）⇒ 验证手段 = **pytest + 门禁脚本**（不臆造 lint 命令） |

---

## 7. 编号域与「**发现编号**」对照表（**消歧的唯一权威**）

> ⚠️ **背景（2026-11-16 analyse 轮 · 第四轮 · H1）**：本 feature 的工件里同时存在**多套**形如
> `X-n` 的编号 ⇒ 且其中三套**只差一个连字符或一个粗体标记** ⇒ ⇒ ⇒ 极易互相误读
> （实测：`H5`（发现编号）vs `H-5`（承接条款）· `A3`（发现编号）vs `A3`（提示词判据）vs
> `A3`（`graph_core.py` 用例组）· `B2`（发现编号）vs `B2`（`agent_loop.py` 用例组）·
> `C1`（发现编号）vs `C1`（契约条目）· `M3`（发现编号）vs `M3`（里程碑））。
> ⇒ ⇒ ⇒ **处置**：① 所有 analyse 轮的**发现编号**统一加 **`FND-`** 前缀
> （`FND-A1` / `FND-B7` / `FND-C3` / `FND-H5` / `FND-L3` / `FND-M3`）；
> ② 本表是**这些编号的唯一解释处**；③ 其余编号域按下表**各归各位**。

### 7.1 编号域一览

| 前缀 | 含义 | 权威位置 | 备注 |
|---|---|---|---|
| **`FND-x#`** | **analyse 轮的发现编号**（回修项） | **本表 §7.2** | ✅ **本 feature 专用前缀** ⇒ 与其它编号域**零冲突** · ⚠️ **第五轮新增 `FND-N1`…`FND-N5`**（与既有 `FND-M3` / `FND-M6` **刻意错开** ⇒ 零撞名） |
| `S-#` | spec 的**回修登记**（plan 阶段自查 + analyse 轮各批次） | research.md §5 · plan「spec 回修登记」 | 连续编号 `S-1…S-45`（⚠️ **2026-11-16 analyse 轮第五轮订正**：原写 `S-1…S-26`，已过期 ⇒ ⇒ **第五轮再订正**：追加 **S-38…S-45**） |
| `H-#` | spec 的**跨 feature 承接条款**（上游 → 本 feature） | spec.md「承接条款」表 · `H-1…H-10` | **带连字符** ⇒ 与 `FND-H#` 区分 |
| `D-#` | spec 的**下游承接条款**（本 feature → 下一棒） | spec.md「下游承接条款」表 · `D-1…D-5`（⚠️ **第五轮新增 `D-5`** = `config` 注解放宽的归属边界 · 归 B8F2 / B15F1 / B16F1） | ⚠️ 与 spec 差分场景的 `D-9#` **同前缀不同义**（见 §7.3） |
| `D-B` / `D-C` | analyse 轮的**决策标签**（Decision B / Decision C） | spec 的相关括注 | ⚠️ **带字母** ⇒ 与 `D-#`（一位数）/ `D-9#`（三位数）**均不同形** ⇒ ⇒ **位数/字母即消歧** |
| `D-9#` / `D-10#` | **差分场景**编号（上游对照） | spec.md「差分场景组」· `contracts/upstream-parity.md` §3 · `D-92…D-102` | 与上游 `D-1…D-91`（既有 feature 占用）连号 |
| `C#` | **契约条目** C1–C27 | `harness/reports/Q8-图运行时最小契约.md` | ⚠️ 与契约自身的 `CF-#` / `ES-#` / `R-#` / `I-#` / `F-#` **并列** ⇒ **勿混** |
| `A#` | **提示词初稿**的判据 A1–A3 | `harness/features/B7F3_invoke返回完整状态.md` §6 | ⚠️ **同名**于 `graph_core.py` 的用例组 A1–A10 ⇒ **以所在文件为准** |
| `A#`（用例组） | `harness/demo/graph_core.py` 的**用例组** A1–A10 | `harness/demo/graph_core.py` | plan 改动面 §8 / tasks T040 的「A1 / A2 / A4 / A7 / A8」 |
| `B#`（用例组） | `harness/demo/agent_loop.py` 的**用例组** B1–B4 | `harness/demo/agent_loop.py` | plan 改动面 §9 / tasks T042 的「B1 / B2 / B3 / B4」 |
| `L#` | **层** L1 契约层 / L2 执行内核 / L3 图定义层 | 层注册表 | ⚠️ **不是**发现编号 ⇒ 一律**不加** `FND-` |
| `M#` | **里程碑** M1 / M2 / M3 / M4 | 立项书 §6 | ⚠️ spec 承接条款的「里程碑」列 ⇒ **不是**发现编号 |
| `ES-#` / `R-#` / `CF-#` / `I-#` / `F-#` | **契约**的条款编号（执行语义 / 返回值 / 跨 feature 接口 / 自检 / 失败信号） | `contracts/invoke-contract.md` §2 / §3 / §5 / §6 / §4 | ⚠️ 契约的 `F-#`（失败信号）≠ 发现编号 ⇒ 发现编号一律带 `FND-` |
| `E-#` | **上游实测台账** E-1…E-10 | research.md §1 · `contracts/upstream-parity.md` §1 | 契约的执行语义条款**已改名** `ES-#`（S-15）⇒ **不再同形** |
| `P-#` / `X-#` | **上游对照** P-01…P-14 / **偏离登记** X-1…X-6 | spec.md「Upstream Parity」· `contracts/upstream-parity.md` §2 / §4 | **双份维护**（发现漂移 MUST 双侧同改） |
| `DD-#` | **设计决策** DD-1…DD-12 | research.md §4 · plan「Design Decisions」 | — |
| `EV-#` | **门禁分阶段登记** | plan「质量门禁的分阶段登记」 | **EV-3 已撤销** ⇒ 不在编号集内 |
| `T-#` | **破冻结面回溯修订项**（本 feature：**T-1 / T-2 / T-3 / T-4**） | spec.md「破冻结面的回溯修订清单」 | ⚠️ 与 tasks 的 `T0##`（任务号）**同前缀不同义**（前者带连字符）⇒ ⚠️ **跨 feature 引用 MUST 带来源 feature 前缀**（例：「**B12F1 的** T-7」·「**B12F1 的** T-2」· 见 §7.3） |

### 7.2 analyse 轮**发现编号**对照表（`FND-x#`）

| 编号 | 发现（**一句话**） | 处置落点 |
|---|---|---|
| **FND-A1** | plan Summary 的「执行路径」写 `run_graph(..., max_concurrency=...)` ⇒ 与「门面**恒不传**该关键字」冲突 | plan Summary「执行路径」行（= S-19） |
| **FND-A2** | **冻结断言 ①** 的替换判据写成「不再是 2」⇒ 真失败（rc == 1）仍判绿 | 统一为「脚本成功 = `rc == 0`」（= S-17 / S-20） |
| **FND-A3** | 验收脚本分级（T040 / T041 / T042）原排 Phase 10 ⇒ `invoke` 接通后到 Phase 10 之间存在红窗 | 三条前移至 **Phase 2′**（= S-21） |
| **FND-A4** | SC-010 的「恢复取值」缺 checkpointer 载体 | 载体 = 测试侧「自足桩 checkpointer」（= S-22） |
| **FND-B1** | 「无值 key 填 `None`」在 10 处未带「仅覆盖型（无归约器）」限定 | 补限定（= S-14 / S-23） |
| **FND-B2** | 验收脚本的用例组清单**漏**「A6 的 C17 段（中断与恢复）」 | 该段保持硬断言（= S-24） |
| **FND-B4** | `build_fanout_graph()` 的形态歧义（是否自带 join 边） | 夹具**不含** join 边 ⇒ 由 **T017⑦** 自行追加（tasks T002） |
| **FND-B5** | 同文件 `[P]` 冲突（T022/T023 · T025/T027 · T040/T041）+ T037 依赖 T036 却标 `[P]` | 去掉 `[P]`（= S-25） |
| **FND-B7** | FR-006 的「步末清空（路由通道值不残留）」**无专门用例** | **T031 增 ④**（= S-25） |
| **FND-B9** | 「上游对照表」与「偏离登记」是**双份维护**的两处落点 ⇒ 漂移 MUST 双侧同改 | spec 加注「双份维护的同步义务」（C7） |
| **FND-C1** | `protocols.py` **无** `from __future__ import annotations` ⇒ 补 `Mapping` import 时若漏 ⇒ **import 期** `NameError` ⇒ 全仓不可导入 | **C1 · CRITICAL** · 与 T005 **同批**（spec 破冻结面清单 + tasks T005） |
| **FND-C2** | 验收脚本的未交付方法清单漏 `get_state_history()` | spec Edge Cases 补齐为 **5** 个（与 FR-026 一致） |
| **FND-C3** | T045 未强调「追认 MUST 由**发起者本人**作出 · MUST NOT 由实现者代签」 | T045 补签署主体条款（= S-26 ④） |
| **FND-C4** | 「裁定编号映射」的来源注把 **H-5** 列进「裁定 11–16」（**H-5** 落在**裁定 5**；**裁定 16** 的来源是**下游承接 D-3**） | spec 裁定来源注订正（= S-34） |
| **FND-H2** | `run_graph` / `InterruptResult` / `SuperStepResult` 三者**已在** `freegraph.runtime.__all__` ⇒ import 追加**不扩**导出面 | tasks T008（追溯表归属同步） |
| **FND-H3** | `_stategraph.py` **已导入** `collections.abc.Mapping`（`:34`）⇒ **MUST NOT** 重复导入 | tasks T008 |
| **FND-H4** | 「路由通道排除」的判据载体缺失 ⇒ 条件边图**必须带 `path_map`**（否则无 `branch:to:*` 通道 ⇒ 断言**恒真** ⇒ **空洞**） | tasks T002 的 `build_conditional_graph()` + T017⑧ / T031④ |
| **FND-H5** | 宪法 v1.12.0 的「冻结断言清单 MUST **实测化**」+「绿基线义务」被 plan/tasks 降格为「候选清单」 | **T001 只立候选** + **T011 实测**（= S-18 的配套） |
| **FND-L3** | SC-006 的「可观测并发度」超时兜底值 MUST **实测标定**（CI 最低档 + Windows 档） | tasks T027 |
| **FND-M6** | 「严格三态标注」：对照表的「关系」列与偏离登记的「类别」列 MUST **逐字相等** | spec 加注（D-C 决策） |
| **FND-M3** | `_stategraph.py` **已导入** `Mapping` ⇒ **MUST NOT** 再导入（重复导入 ⇒ lint 红） | plan 改动面 §1 + tasks T008 |
| **FND-G1** | 宪法 v1.15.0 的**记账不同步**：生效副本正文已含 v1.15.0（括注订正），但**页脚仍写 1.14.0** · **changelog 无 v1.15.0 条目** · **模板 `init_constitution.md` 未同步旧括注** ⇒ ⇒ 再跑 `/speckit.constitution` 会把修订冲掉 | 宪法页脚 + `constitution-changelog.md`（索引行 + 修订节）+ 模板**三处已同步**（正文逐字一致） |
| **FND-A5** | **破冻结面 T-4**（G19 兼容矩阵行白名单）**无任何任务承载** ⇒ ⇒ 而工作区里该改动**已被带外应用**（未提交）⇒ ⇒ 任务链缺口 + 带外改动 | 工作区改动**已回退** + 新增 **tasks T053** 承载（Phase 10 · MUST 早于 T047） |
| **FND-B8** | **追认项的计数在四份工件里各不相同**（契约 I-14 = 3 · plan C6 = 4 · tasks T046 = 4 · tasks T045 = 5）⇒ ⇒ 守卫断言与「唯一权威」的契约判定集合不一致 | **唯一事实源 = spec Assumptions 的「破面全集 5 类」** ⇒ 契约 I-14 / plan C6 / T045 / T046 / plan Notes **已逐字统一为 5 项** |
| **FND-C8** | **破面计数跨工件 + plan 内部三处不一致**（spec = 5 类 · plan 导语 = 2 处 · plan Constitution Check = 3 处 · plan re-check = 5 条） | plan 三处**统一为「5 类破面 / 1 次追认」** |
| **FND-H6** | 编号域消歧**未跟上新变化**：§7.1 仍写 `T-#` = T-1/T-2/T-3（**漏 T-4**）⇒ ⇒ 且 spec H-2/H-3 裸写**别的 feature** 的 `T-7` / `T-2` | §7.1 补 T-4 + §7.3 增「**跨 feature 的 `T-#` MUST 带来源前缀**」· spec H-2/H-3 补「B12F1 的」 |
| **FND-C9** | **跨 feature 的裁定号裸写**：裁定 7 / FR-015 写「依**裁定 4**」（本 spec 的裁定 4 = schema key 推导 · 与 **B10F1 裁定 4**（恢复判定顺序）完全不同）⇒ ⇒ 裁定 11 / Edge Cases 的「裁定 33」= **B7F1** 的 | spec 四处**补来源前缀**（「B10F1 的裁定 4」/「B7F1 的裁定 33」） |
| **FND-D1** | **S 回修编号范围过期两处**（`S-1…S-26` ⇒ 实际已到 **S-37**）⇒ ⇒ T052 的一致性自检会**漏检 S-27…S-37** | research §7.1 + tasks T052 + plan E6 **三处改为 `S-1…S-37`**（⚠️ **第五轮再订正** ⇒ 范围扩至 `S-1…S-45`） |
| **FND-E1** | plan 的「门禁 7 的可达性说明」**整块逐字重复两次** | 删去单行版（保留多行完整版）+ 括注句**按宪法 v1.15.0 的实际修订状态**更新 |
| **FND-E2** | 四处**事实 / 边界补齐**缺口：① T044 取证范围 `§1–§4` **漏 quickstart §5**（= SC-018 两轮实测输出的出处）② T002 的 fan-out 夹具**未含 `c` 节点** ⇒ T017⑦ 的 `add_edge(["a","b"],"c")` 会指向未注册节点 ③ T051 只列 G21–G30 而 Constitution Check 声明 G1–G30 ④ spec 追溯表 FR-013 未挂 SC-004 | 四处**逐条补齐**（判据零放宽） |
| **FND-F1** | `graph_core.py:388-391` **行号漂移**（soft() 调用与「载体待 B14F1 锁定」注记实际在 **:392-393**）⇒ ⇒ 四份工件各引一次 | spec SC-010 / plan S-22 / tasks T002 / T029 **四处统一为 `:392-393`** |

| **FND-B10** | **三对 `[P]` 任务同文件冲突**（`T017`×`T020` · `T028`×`T029` · `T015`×`T036`）=> FND-B5 第三轮回修只修了 3 组，漏了这 3 组 | tasks `T020`/`T029`/`T036` 去 `[P]` + 串行清单补为**五组**（= S-38） |
| **FND-H7** | **T052 的三条 grep 型自检判据不可执行**（裸字符串命中 7 / 4 / 3 处，全在禁止语境或历史陈述）=> 必红 | T052 必查项 ④⑥⑦ 改为**判据形态 / 语义形态**的 grep（= S-39） |
| **FND-N1** | plan Constitution Check「原则 X」行仍断言「`StateGraph`/`CompiledGraph` 两行在 G19 的白名单内」=> **事实错误** + 与 plan 改动面 §4 / spec 破冻结面 T-4 / tasks T052 必查项 ⑧④ 冲突 | plan 原则 X 行改写（= S-40） |
| **FND-N2** | tasks **T002 内部自相矛盾**（桩 checkpointer 方法集：`get_tuple`/`put`/`put_writes`/`list` 等最小集 vs 契约 F-05 的 3 个方法） | T002 前半句并入 F-05 口径（= S-41） |
| **FND-N3** | **US4 的验收场景缺 SC-006 修订后的判定性半边**（「可观测并发度」）且 Independent Test 用**自环图**（重叠恒为 0 => 断言空洞） | spec US4 增两条验收场景 + Independent Test 补 fan-out 图（= S-42） |
| **FND-N4** | **L1 其余 4 个带 `config` 参数的方法**的 `config` 注解放宽未登记为下游承接义务 | spec 下游承接 **D-5** + 契约 **CF-05** + plan/tasks 接线（= S-43） |
| **FND-N5** | 计数过期（「契约层 18 符号」=> 实际 **21**）· spec X-1 与 `upstream-parity.md` X-1 的实测引用不一致 · plan 改动面 §16 夹具清单漏 2 个 builder · demo README「RunConfig 四字段」与现状 9 字段矛盾 | 四处逐条订正（= S-44） |
| **FND-F2** | 提示词初稿的 `SC-001…SC-005` 与 spec 的 `SC-001…SC-020` **编号同形、含义不同**（spec 引文差异 11 已判初稿编号**作废**）=> 初稿本身未标注 + 初稿内部 `SC-004` 引用错 | `harness/features/B7F3_invoke返回完整状态.md` 加**编号域隔离**注 + 修 `SC-004` 引用 |
> ⚠️ **编号完整性**：本表**零**未登记引用（`spec.md` / `plan.md` / `tasks.md` 内出现的每个 `FND-` 编号 MUST
> 在此表有行 —— ⚠️ **2026-11-16 analyse 轮第五轮订正**：原范围只列 `plan.md` / `tasks.md`，而 **FND-B9 / FND-C2 / FND-M6** 的处置落点在 **spec.md** ⇒ ⇒ 范围**扩为三份工件**）⇒ ⇒ **必查项**（tasks **T052**）：`grep -o "FND-[A-Z][0-9]"` 的结果集 MUST
> 与本表的编号集**逐项相等**。

### 7.3 两条仍需注意的「同前缀不同义」

| 冲突 | 消歧口径 |
|---|---|
| `D-#`（下游承接条款 · **5 条**）vs `D-9#` / `D-10#`（差分场景 · 11 条） | 差分场景恒为**三位数**（`D-92`…`D-102`）；下游承接恒为**一位数**（`D-1`…`D-5`）⇒ **位数即消歧** |
| `T-#`（破冻结面回溯修订项 · T-1/T-2/T-3）vs `T0##`（任务号 · T001…T052） | 破冻结面项恒为**一位数**（`T-3`）；任务号恒为**三位数**（`T052`）⇒ **位数即消歧** |
| `C#`（契约条目 C1–C27）vs `CF-#` / `F-#`（契约自身的条款） | 契约条目**无连字符**且**不带 `FND-`**；契约自身的失败信号条款恒为 `F-0#` |
| **跨 feature 的 `T-#`**（破冻结面回溯修订项）vs **本 feature 的 `T-1…T-4`** | 破冻结面项是**每个 feature 各自的编号空间**（例：**B12F1** 的 `T-2` / `T-7`）⇒ ⇒ **跨 feature 引用 MUST 带来源 feature 前缀**（「**B12F1 的** T-7」）⇒ ⇒ **MUST NOT** 裸写 `T-n` ⇒ ⇒ 裸写时**默认**指本 feature 自己的 `T-1…T-4` |
