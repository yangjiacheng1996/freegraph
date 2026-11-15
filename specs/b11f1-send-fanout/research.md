# Research · B11F1 · `Send`：动态 fan-out / map-reduce

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-11-14
**上游取证版本**: `langgraph` **1.2.11**（`/home/ctyun/.local/lib/python3.12/site-packages/langgraph`）

> **本文件是 Phase 0 的产物**：把 spec 里**上游没答案**的点**逐条查上游 / 查仓库现状**，
> 并把**必须由 plan 冻结**的设计决策（名字 / 形状 / 落点）落成**可判定**的条款。
> ⚠️ **本文件不新增判据**：一切需求与判据以 `spec.md` 为**唯一权威**（若不一致 ⇒ 以 spec 为准）。

---

## §0 取证环境与方法

| 项 | 值 |
|---|---|
| 上游安装 | `langgraph` **1.2.11**（PEP 735 依赖组 · **仅测试侧**） |
| 解释器 | CPython **3.12**（仓库基线 **>= 3.11**） |
| 探针脚本 | 一律落在 `/tmp`（**不进仓库** · 不进依赖声明） |
| 绿基线 | **1184 passed / 4 skipped**（2026-11-14 · `pytest -q`）⇒ FR-022 的**基线义务**已履行 |
| 方法 | ① **只读源码**（带 `路径:行号`）② **行为实测**（探针脚本 · 两侧对跑）③ **仓库现状**（AST / grep / 测试断言） |

---

## §1 上游实测取证（**E-1…E-11** · 与澄清轮同源）

> ⚠️ **原则 XI 的纪律**：**行为**断言 MUST 有**实测**支撑（只读源码**不足以**支撑行为断言）。
> ⇒ 本节的每条 E 都是**本机实跑**的产物；探针脚本**不进仓库**。

| # | 场景 | 上游实际行为 | 对本 feature 的含义 |
|---|---|---|---|
| **E-1** | 条件边返回 `[Send("worker", {"n": 1}), Send("worker", {"n": 2})]` | 目标**被调用两次** · 两次入参**分别逐字等于** `{"n": 1}` / `{"n": 2}` | map-reduce 的核心语义 ⇒ 照抄（spec P-06） |
| **E-2** | `Command(goto=[Send("worker", …)])` **+ 静态边** `fan→worker` | worker **被调用 2 次**：一次**标准入参**、一次**自定义** | **载体 A** 的「与静态边并存」⇒ **叠加**（spec P-10 · 裁定 5） |
| **E-3** | `Send` 的 arg = **完整状态** | 目标节点**只**看到 arg 的 key（**不**与图状态合并） | 入参形态 = **替代**（spec P-05 · 裁定 3） |
| **E-4** | `Send` 的 arg = `{"n": 1}`（非状态 schema 的 key） | 目标节点**只**看到 `["n"]`（**不**按订阅 / schema 过滤） | arg **逐字**（spec FR-003） |
| **E-5** | `Send` 的目标节点**不存在** | **warning + 忽略**：「Ignoring unknown node name nope in pending sends」⇒ 流程**照跑完** · 目标**没跑** | freegraph **显式失败**（**STRICTER** · spec P-07 · X-1） |
| **E-6** | 两个 `Send` ⇒ 各 sleep 0.3s | 总耗时 **0.308s** ⇒ 同轮**并发** | fan-out 任务**并发**（spec P-08 · 裁定 8） |
| **E-7** | **节点**返回 `list[Send]` | **抛错**：`InvalidUpdateError("Expected dict, got [Send(...), Send(...)]")` | 上游**无**「节点返回 `Send` 列表」形态 ⇒ freegraph **自研**（spec P-09 · X-6） |
| **E-8** | `Command(goto=[Send(…), Send(…)], update={"messages": ["from-fan"]})` | 产出 `{'messages': ['from-fan', 'w1', 'w2']}` ⇒ **派发与写入同时生效** | 一次返回里**既派发又写入** ⇒ freegraph **照抄**（spec P-12 · 澄清轮第 2 次 Q1 = **B**） |
| **E-9** | `Command.goto` 的**注解** | `Send \| Sequence[Send \| N] \| N`（`langgraph/types.py:824`）⇒ 节点名（`N`）与 `Send` **可混装** | L1 的 `goto` 注解 MUST 放宽（spec FR-012） |
| **E-10** | `Send("worker", "not-a-dict")` | 目标节点**逐字**收到 `"not-a-dict"` ⇒ 非 dict 入参**不被校验 / 不被转换** | arg **不校验**（spec FR-008） |
| **E-11** | 两个产生者 `p1` / `p2` 各发 `Send` 到乱序目标（`p1→a,z` · `p2→b,a`）· worker 的完成顺序**故意颠倒**（n=1/3 慢） | **10 次运行**最终归约值恒为 `['w1','w2','w3','w4']` ⇒ **写入顺序确定** = 产生者序 + 载荷内 `Send` 序号（**不是**完成时刻竞态）· 上游 `pregel/_algo.py:253-256` 逐字「sort tasks on path, to ensure deterministic order for update application」 | **照抄上游**（spec **P-13** · FR-005 / SC-008 · 差分 **D-31** 可断言**逐项顺序**） |

### E-1b…E-7b · 逐条源码锚点（`路径:行号`）

- `langgraph/types.py:704-792` —— `Send` 类定义（`:704`）· `__init__`（`:757-776`）·
  docstring 逐字「the same node multiple times in parallel with different states」。
- `langgraph/types.py:798-848` —— `Command` 定义 · **`goto` 注解在 `:824`**。
- `langgraph/graph/state.py:1749-1775` —— `_control_branch`：`Send` → `TASKS` 写（`:1750-1751`）·
  `Command.goto` 里的 `Send` → `:1768-1770` · **逐元素分派** `:1768-1774`。
- `langgraph/graph/state.py:1488-1492` —— 节点返回**非 dict** ⇒ `InvalidUpdateError`（E-7 的依据）。
- `langgraph/pregel/_algo.py:962-965` —— 逐字「SEND tasks, executed in superstep n+1」⇒ **下一轮**执行。
- `langgraph/pregel/_algo.py:978` —— 「Ignoring unknown node name … in pending sends」（E-5 的依据）。
- `langgraph/pregel/_write.py:172-192` —— `_assemble_writes`：`Send` → `TASKS`（`:178-179`）。

---

## §2 既有测试的**回归面探测**（**C-01** · 本 feature 最高风险项）

> **方法**（宪法 v1.11.0「冻结断言清单 MUST **实测化**」）：以**源码引用**定位**会被本 feature
> 的落地形态影响**的冻结断言 ⇒ 逐条判定「变红 / 不变红」⇒ 构成 spec 的回溯修订清单
> **F-1…F-14** 的**实测底稿**。
> ⚠️ **基线**：**1184 passed / 4 skipped**（2026-11-14）⇒ 变红才可归因到本 feature。

| # | 冻结断言（`文件:行号`） | 断言内容 | 本 feature 的落地形态 ⇒ 判定 | 处置 |
|---|---|---|---|---|
| **C-01** | `tests/contracts/test_architecture.py:450` · `:1511` | G7：L1 公开符号面 **恰为 20 个** | `Send` 进 `contracts.__all__` ⇒ **21** ⇒ **变红** | 回溯修订（**F-5** · 拆分而不删 · 集合成员增 `Send`） |
| **C-02** | `tests/runtime/test_read_contract.py:63` · `:561` | `CONTRACT_SYMBOL_COUNT = 20` | 同上 ⇒ **变红** | 回溯修订（**F-5**） |
| **C-03** | `tests/runtime/test_command_purity.py:287` | `payload["contracts"] == 20` | 同上 ⇒ **变红** | 回溯修订（**F-5**） |
| **C-04** | `tests/contracts/test_protocols.py:136`（`get_type_hints(NodeFunc.__call__)`） | 返回联合 = `StateDict \| Command \| list[Command \| StateDict] \| None`（**四形态**） | 载体 B ⇒ 节点函数可返回 `Send` / `list[Send]` / `tuple[Send, ...]` ⇒ **变红** | 回溯修订（**F-11** · 拆分而不删 · **增补**三形态） |
| **C-05** | `tests/runtime/test_superstep_concurrency.py:800-808` | 「`_primitives.py` **只留 `Send`**」 | 文件随 `Send` 迁出而**删除** ⇒ **变红** | 回溯修订（**F-2** · 意图保留：改为「`Send` 的类型定义在 L1」） |
| **C-06** | `tests/facade/_gatesupport.py:46` · `:60` | `SIGNED_SOURCE_FILES` / `FACADE_MODULES` 含 `src/freegraph/_primitives.py` | 文件**删除** ⇒ 清单项失效 ⇒ **变红** | 回溯修订（**F-3** · 只更新**扫描清单**） |
| **C-07** | `specs/b1f1-contracts-core/contracts/public-api.md` §0（G7 的**清单来源**） | L1 符号清单（20 项） | 增 `Send` ⇒ **清单与断言同步** | 回溯修订（**F-5** · 清单**增一行**） |
| **C-08** | `tests/facade/test_facade.py:276-300`（`TestSend`） | `Send` 两种构造形态 · frozen · `FrozenInstanceError` · 不可哈希 | 类的**形状逐字不变**（只换模块）⇒ **不变红** | ✅ **零改动** |
| **C-09** | `tests/facade/_snapshot_tools.py:346-352`（`_render_class`）+ `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt` | 门面 API 快照 | 快照**不渲染** `__module__` ⇒ 换模块**不影响**快照 ⇒ **不变红** | ✅ **零改动**（**已实测确认**） |
| **C-10** | `tests/contracts/test_types.py:99-148`（`Command.goto` 的行为断言） | `goto` **不归一化** · `goto=()` 合法 · `PARENT` 非字段 | **运行期行为不变**（只放宽**注解**）⇒ **不变红** | ✅ **零改动** |
| **C-11** | `tests/differential/parity_probe.py`（既有 **50** 个场景定义 = 14 基础 + B12F1 `D-01…D-15` + B7F4 `D-16…D-28` + B10F1 `DI-01…DI-08`） | 上游 ↔ freegraph 对跑 | 既有场景**不涉及 `Send`** ⇒ **不变红** | ✅ **零改动**（**追加** D-29…D-37） |
| **C-12** | `harness/demo/graph_core.py`（C18 用例） | 节点返回 `list[Send]` ⇒ 目标两次 | 本 feature **不交付**构建器（**B6F1**）⇒ 该用例**仍不可跑** | ✅ **不属本 feature**（**如实登记** · 人工验证记录「遗留问题」） |

### C-01 的结论

**变红并须回溯修订的冻结断言 = 6 处（C-01…C-06）+ 1 处清单（C-07）**
⇒ 与 spec 的回溯修订清单 **F-1…F-14** 逐条对应 ⇒ **判据只收紧、不放宽**。
⚠️ **另有 2 类「非测试变红、但契约语义冲突」的冻结面**（2026-11-14 修复分析轮 C1/C2 追加）：
**F-13**（B10F1 的 `task_id` / 任务现场 / 命名空间）· **F-14**（B7F1 / B9F1 / B12F1 / B10F1（`.executed`）的
阶段模型 / 执行次数 / 报告与合并次序）⇒ 它们不由既有测试变红暴露（既有测试无 `Send`），
但会与 B11 的 N 任务 / TaskId 口径**直接矛盾** ⇒ MUST 回溯修订 ⇒ ⚠️ **2026-11-14 收口：F-13 / F-14 已在工作区落地**（tasks T093 / T094 改为核验项）。
⚠️ **另有 4 处非测试的冻结文档**（层注册表 / B1F1 两份文档 / B9F1 契约 / B12F1 契约 /
B2F2 的 `architecture-gates.md`）⇒ 见 plan 的回溯修订清单 **T-1…T-15**。

---

## §3 设计决策（**由 plan 冻结** · 与 spec 裁定一一对应）

> **记注**：本节只落**名字 / 形状 / 落点**（spec 未规定、但实现必须定死的部分）⇒
> **MUST NOT** 改变任何语义（语义一律以 spec 为准）。

| # | 决策 | 选定 | 理由 | 落点 |
|---|---|---|---|---|
| **D-01** | **内部任务标识（TaskId）**（⚠️ 归并顺序已在 spec FR-005 写死 · **2026-11-14 复核更正**为**上游同款**（`pregel/_algo.py:253-256` · **P-13**）⇒ 本条只落**内部标识**） | **`TaskId = int`** = 本轮任务的**规范序号（0 起）**<br>· **标准触发任务**：先分配 · 按**目标节点名序**<br>· **fan-out 任务**：后分配 · 按**产生者 TaskId 序 + 载荷内 `Send` 序号** | ① 排序键 = TaskId 本身（`int` 字典序）⇒ **与 spec FR-005 的上游任务序逐字一致**（标准全部在前 · fan-out 按产生者任务序 + `Send` 序号）⇒ **归并顺序天然成立**；② **唯一性**：同一节点在一轮内执行多次 ⇒ **各次任务各有独立 TaskId**（产生者用任务而不是节点名标识）；③ 同时服务结果槽的键、「首个异常」与 `executed` 的确定性；④ **持久化 `task_id`**（F-13）：标准任务 = 节点名 · fan-out 任务 = `f"{节点名}:{TaskId}"` | data-model §3.3 · contracts §4 |
| **D-02** | **并发执行器的结果槽键** | 由 `str`（节点名）改为 **TaskId**（`_concurrency.py`） | ⚠️ **现有实现会互相覆盖**：`run_tasks_concurrently` 用 `outcomes: dict[str, _TaskOutcome]` 按**节点名**索引 ⇒ 同一节点的两个任务**只留最后一个** ⇒ ⇒ **必须**改键；⇒ 改动面**极小**（`futures[fut] = task_id` + `sorted(outcomes)` 仍可用）⇒ 且「首个异常 = 扫结果槽的第一个」的口径**自动继承**（B12F1 裁定 5 的确定性**零破坏**） | data-model §2.2 · contracts §4 |
| **D-03** | **调度状态的运行期记录** | `SchedulerState` **新增一个**带缺省值的字段 `fanout: dict[TaskId, _FanOut]`（`default_factory=dict`） | ① 与 B9F1 的 `dynamic_edges` **同款**（裁定 12 的先例）⇒ `SchedulerState()` 的**构造签名逐字不变** ⇒ **B7F2 / B7F3 / B8F1 / B12F1 零改动**；② fan-out 载荷**含用户对象** ⇒ **不能**进 `dynamic_edges`（那里只放**字符串**目标名）⇒ ⇒ **单独一个字段**；③ 键必须是**产生者 TaskId**（同一节点一轮内可执行多次 ⇒ 用节点名会**互相覆盖**）⇒ `_FanOut` **另带 `producer`（产生者节点名）** 供静态边抑制按 **(producer, target)** 匹配；④ 载荷**一次性**：下一轮消费后清空（上游 `TASKS` 的 `accumulate=False`） | data-model §3 · contracts §3 |
| **D-04** | **fan-out 任务与触发源版本的关系** | ① fan-out 任务**不消费**任何触发源版本（它是「**派发**」不是「**触发**」）⇒ 下一轮该目标**仍**可能被静态边触发（**载体 A** 的叠加口径因此**自然成立**）<br>② **载体 B** 的 fan-out 覆盖 ⇒ 当且仅当 `_FanOut.suppresses_static=True` **且** `_FanOut.producer == 该静态边的源节点` **且** `target == 当前节点` ⇒ 该对（producer, target）的**单元素**边触发组（`("e", producer)`）在触发判定阶段**被抑制**（⇒ 不满足 ⇒ 不触发 ⇒ 不消费）⇒ **同一对（产生者, 目标）一轮内至多一次**；**其它 producer 的静态边不抑制**；**多源屏障组不抑制** | ① 「不消费」是「派发 ≠ 触发」的**直接推论** ⇒ 版本账本**不被污染**；② 载体 B 的「`Send` 胜出」需要一个**明确的抑制点** ⇒ 落在**触发组枚举层**（`_trigger_groups`）⇒ ⇒ **多源屏障组（B7F4）不抑制**（屏障语义优先 · **已回写 spec FR-006/SC-005 的例外条款**）；③ ⚠️ **术语澄清（M1）**：fan-out 任务**不是** `("e", 源节点名)` 边触发源，而是独立**派发任务**；「与 `goto` 同族」只指**下一轮落点**，不是「登记为边触发源」 | data-model §4.3 · contracts §5.4 |
| **D-05** | **内部归一形状** | `{"writes": dict[str, tuple[Any, ...]], "gotos": tuple[str, ...], "fanout": tuple[_FanOutTask, ...]}`（**增一个键**）<br>⇒ `_TaskOutcome` 同步增 `fanout` 字段 | ① 「归一为一种内部形状」是 B9F1 的既有结构（裁定 4）⇒ ⇒ **增一个键**即可 ⇒ **不新增概念**；② `_TaskOutcome` 是**私有**（不进 `__all__`）⇒ **导出面零改动** ⇒ 但 B9F1 / B12F1 的**契约文档**须**回溯修订**（**F-10 / F-12** · **T-10 / T-12**）⇒ ⚠️ **2026-11-14 收口：已落地**（`fanout` 键 / 结果槽键 = TaskId / `_TaskOutcome.fanout` 已补入对应契约） | data-model §2.3 · contracts §3.2 |
| **D-06** | **`Send` 类型的落位与顺序** | 类型定义迁入 **`freegraph/contracts/types.py`** · **定义在 `Command` 之前**（⇒ `Command.goto` 的注解**无需** `from __future__ import annotations`）· `contracts/__init__.py` **导出**（`__all__` 20 → 21）· 门面从 **L1** 转出（`from .contracts import …, Send`）· `src/freegraph/_primitives.py` **删除** | ① **照抄上游**（上游与 `Command` **同模块** · `langgraph/types.py:704`）⇒ ⇒ **P-11 判词 SAME**；② **定义在前** ⇒ 注解是**普通表达式**（`str \| Send \| Sequence[str \| Send] \| None`）⇒ **不引入** future import（facade 已有「future import 会留公开绑定」的教训）⇒ **零新增风险**；③ `__all__` 21 ⇒ **G7** 冻结断言回溯修订（**F-5**）⇒ **追认** | data-model §1 · contracts §6 |
| **D-07** | **L1 协议面的放宽 + 入参例外注记** | ① `Command.goto: str \| Send \| Sequence[str \| Send] \| None`（**保留 `None` 缺省** · 不照抄上游的 `()`）<br>② `NodeFunc.__call__` 的返回联合**增补** `Send` / `list[Send]` / `tuple[Send, ...]` ⇒ 七形态<br>③ docstring / C5 注记：「经 `Send` 调用的目标节点入参 = `arg` 原样（可为非 `dict` / `None`）⇒ 稀疏 `dict` 注记只适用于标准触发 / `goto`」（**H3**） | ① 缺省 `None` vs 上游 `()` 是**既有登记**的差异（B9F1 · B12F1 的上游对齐批次）⇒ **不动**；② 协议 MUST 与运行时**一致**（B9F1 裁定 21 的原则）⇒ 否则「用 `NodeFunc` 标注的节点」在类型层**无法表达**载体 B；③ 上游 **E-10** 明确允许非 dict 入参 ⇒ 不改注记会造成**协议 / 运行时分歧** ⇒ ⇒ **破 L1 冻结面** ⇒ 回溯修订（**F-11**）+ **追认** | contracts §6.2 / §6.3 |
| **D-08** | **fan-out 载荷的持久化** | **B11F1 交付时：不落盘**（`SchedulerState.to_checkpoint` **不含**它）；⚠️ **B13F1 F-3 起**：`to_checkpoint` **含** `fanout`（拆分而不删；存储仍归 B14F1） | ① 载荷含**用户对象**（`arg: Any`）⇒ **未必可 JSON 序列化** ⇒ 落盘会引入**新的失败面**；② 与 B7F1 的「`step` **不落盘**」**同款**（运行期记账不跨运行）；③ 与「pending writes 的持久化」（**B14F1** · 下游承接 **D-3**）**分离** ⇒ ⇒ **登记为已知限制**（DR-02） | data-model §3.4 · DR-02 |
| **D-09** | **同一节点一轮内多次执行时的调度状态落回** | ① `node_versions[node]` **按成功执行次数**递增（**+N**）<br>② `dynamic_edges[node]` 取 **TaskId 序最后一个**任务的产出<br>③ 新产生的 `fanout` 按**产生者 TaskId** 记录（不按节点名 · 各次任务分别保留） | ① spec 裁定 13 已定「+N」⇒ **照抄**；② 多个任务写同一 `dynamic_edges` 格 ⇒ 取**最后一个**（**可复现** · 与上游分支通道的后写覆盖**同族** · 上游写序**确定**：`_algo.py:253-256`）；③ fan-out 载荷是**多项集合**（不是覆盖语义）⇒ 必须按任务保留 | data-model §4.4 · contracts §5.4 / §5.5 |
| **D-10** | **`executed` 的报告口径** | **逐次列出**（同一节点名**可重复**）· 顺序 = **TaskId 序**（标准触发任务按目标节点名序 → fan-out 任务按产生者 TaskId 序 · `Send` 序号） | ① spec 裁定 13 已定「逐次列出」⇒ **照抄**；② 上游的 `snapshot.tasks` **每个 PUSH 任务各一条** ⇒ **同款**；③ `SuperStepResult` 的**四字段零改动**（只改**成员口径**）⇒ **不破冻结面** | contracts §5.5 |
| **D-11** | **内部模块落位** | 新增 **`src/freegraph/runtime/_fanout.py`**（**私有** · 不进 `__all__`）⇒ 承载：fan-out 载荷的解析 / 校验 / 任务构造 / 触发组抑制 | ① 与 B12F1 的 `_concurrency.py` **同款**（私有内部模块 · 导出面零改动）；② 落在 **L2 目录条目内** ⇒ **同注册表条目** ⇒ G25 恒绿（**MUST NOT** 为它单独立条目 —— 那会造成 L2 → L2 横向依赖误判） | plan §Project Structure |

---

## §4 遗留登记 / 已知限制（**DR-01…DR-06** · **不改判据**）

| # | 遗留 | 影响 | 处置 |
|---|---|---|---|
| **DR-01** | **fan-out 任务的中断 id** 按**节点名**派生（B10F1 的口径）⇒ 同一节点被 N 次调用时 ⇒ 可能产生**同 id** 的多条中断 | 恢复时按 id 匹配 ⇒ 可能歧义 | **本 feature 承接**：**T027** 把任务级现场键改为**任务标识（TaskId）** ⇒ 同节点 N 次 fan-out **各自独立的 scratchpad**；**T034** 补「同节点 N 次调用各自中断」用例；与 **B10F1** 的恢复口径**对齐**（MUST NOT 破坏既有 resume 语义）。⚠️ **2026-11-14 修复分析轮 C1**：仅改运行期现场键不够 ⇒ **持久化 `task_id` / B14F1 / B15F1 也必须按 F-13 拆分**（标准 = 节点名 · fan-out = `f"{节点名}:{TaskId}"`）⇒ **T093 / T095** 承载。 |
| **DR-02** | **fan-out 载荷不落盘**（D-08）⇒ checkpoint 恢复后**未执行的 fan-out 任务丢失** | 影响 B14F1 的 checkpoint 语义 | **登记** ⇒ 归 **B14F1**（下游承接 **D-3**）⇒ 本 feature **MUST NOT** 自行实现持久化。⚠️ **2026-11-15 · B13F1 F-3 回溯修订**：`to_checkpoint` 的**键编码**由 B13F1 接管（增 `fanout`）；**实际存储 / 序列化协议**仍归 **B14F1**（拆分而不删） |
| **DR-03** | **载体 A 与载体 B** 在「与静态边并存」时口径**不同**（叠加 vs `Send` 胜出） | 同一张图换一种写法 ⇒ **调用次数可能不同** | **登记** ⇒ spec 裁定 5 已要求「MUST 显著写进文档 / 人工验证记录」⇒ 本 feature MUST 在 `quickstart.md` 与人工验证记录里**各写一处** |
| **DR-04** | `Send` 的**可变性 / 哈希性 / `timeout`** 与上游不同（X-5） | 与上游**不完全**同款 | 归**上游对齐批次 P3-8**（**不属本 feature**） |
| **DR-05** | **条件边返回 `Send`** 的运行期语义未实现（`conditional_edges` 恒空 · **V-8**） | 提示词 FR-001 的「条件边」那一半未交付 | 归 **B8F1**（下游承接 **D-1** · 接线动作在本 feature 的 plan / tasks 阶段执行） |
| **DR-06** | **静态中断点**（`interrupt_before` / `interrupt_after`）× fan-out 的交互（B13F1 已落地） | N 次调用 ⇒ N 次中断？ | 归 **B13F1**（下游承接 **D-7**）⇒ **已由 B13F1 裁定 8 收口**：**任务粒度独立、挂起载荷为空元组**（N 个任务级命中，不是 N 个载荷元素） |

---

## §5 换上游版本时 **MUST 重做** 的取证动作

1. **复核全部行号**：`types.py:704-792`（`Send`）· `types.py:824`（`goto` 注解）·
   `graph/state.py:1488-1492` · `graph/state.py:1749-1775` ·
   `pregel/_algo.py:962-965` · `pregel/_algo.py:978` · `pregel/_algo.py:253-256`
   （**写入顺序**：`sort tasks on path`）· `pregel/main.py:809`（`TASKS` = `Topic(..., accumulate=False)`）·
   `pregel/_write.py:172-192`。
2. **重跑 E-1…E-11**（探针脚本**不进仓库** ⇒ 换版本后须重写并重跑）。
3. **复核差分判词**：`tests/differential/parity_probe.py` 的 **D-29…D-37** 在新版本上的判词
   ⇒ 若上游行为变了 ⇒ **必须**重判（**SAME / STRICTER / DIFF** 三态同步改）⇒
   ⇒ **MUST NOT** 让差分场景因上游漂移而**偶发红**（宪法原则 XI 的「可验证出口」纪律）。
4. **复核 `Command.goto` 的缺省值**（上游 = `()` · freegraph = `None`）⇒ 若上游改 ⇒ 登记。

---

## §6 spec 事实性核对（**只更正事实 · 未改任何判据**）

| # | spec 的断言 | 核对结果 | 处置 |
|---|---|---|---|
| 1 | L1 公开符号面 **20** | ✅ 属实（`freegraph.contracts.__all__` == 20） | 本 feature 后为 **21**（D-06） |
| 2 | 门面 **7** 符号面 | ✅ 属实 | 零改动 |
| 3 | `freegraph.runtime.__all__` **23** | ✅ 属实 | 零改动（D-11 的私有模块不进 `__all__`） |
| 4 | `Send` 现居 `src/freegraph/_primitives.py` | ✅ 属实（**L2 单文件条目**） | 按 D-06 迁入 L1 |
| 5 | `_primitives.py` 是 L2 单文件条目 · `runtime/` 是 L2 目录条目 ⇒ 互相 import 判红 | ✅ 属实（层注册表 §1 + `_primitives.py` 的模块 docstring） | 本 feature 迁出后该冲突**消失**（F-1） |
| 6 | G25 判「同层跨条目 import」为红 | ✅ 属实（`harness/scripts/gates/gate_G25_import_graph.py` · 判定规则 §0.2） | — |
| 7 | 既有测试 **1184 passed / 4 skipped** | ✅ 属实（2026-11-14 实跑） | 绿基线（FR-022） |
| 8 | 门面 API 快照**不渲染** `__module__` ⇒ 换模块**不**使快照变红 | ✅ 属实（`_snapshot_tools.py:346-352`） | ⇒ **零快照重生成**（C-09） |
| 9 | `tests/contracts/test_types.py` 的 `Command.goto` 行为断言**不**受注解放宽影响 | ✅ 属实（**运行期行为不变**） | ⇒ **零改动**（C-10） |
| 10 | 验收脚本 C18 用例当前**不可跑**（B6F1 / B7F2 / B7F3 未接线） | ✅ 属实（实跑 `harness/demo/graph_core.py` ⇒ `NotImplementedError: add_node 尚未接线`） | **如实登记**（C-12）⇒ 本 feature 的用例 MUST 在**手写图规格**上验证同一形态（FR-017） |
