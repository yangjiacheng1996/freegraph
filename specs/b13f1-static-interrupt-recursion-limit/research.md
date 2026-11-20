# Research · B13F1 · 静态中断点 + `recursion_limit`

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-11-15
**上游取证版本**: `langgraph` **1.2.11**（`/home/ctyun/.local/lib/python3.12/site-packages/langgraph`）

> **本文件是 Phase 0 的产物**：把 spec 里「上游有答案」的点逐条查上游 / 查仓库现状，
> 把「上游没答案」的点落成 **plan 冻结**的设计决策（名字 / 形状 / 落点）。
> ⚠️ **本文件不新增判据**：一切需求与判据以 `spec.md` 为**唯一权威**（若不一致 ⇒ 以 spec 为准）。

---

## §0 取证环境与方法

| 项 | 值 |
|---|---|
| 上游安装 | `langgraph` **1.2.11**（PEP 735 依赖组 · **仅测试侧**） |
| 解释器 | CPython **3.12**（仓库基线 **>= 3.11**） |
| 探针脚本 | 一律落在 `/tmp`（**不进仓库** · 不进依赖声明） |
| 绿基线 | **1203 passed / 4 skipped**（2026-11-15 · `.venv/bin/python -m pytest -q`） |
| 方法 | ① **只读源码**（带 `路径:行号`）② **行为实测**（探针脚本 · 两侧对跑）③ **仓库现状**（AST / grep / 测试断言） |

---

## §1 上游实测取证（**E-01…E-14**）

> ⚠️ **原则 XI 的纪律**：**行为**断言 MUST 有**实测**支撑（只读源码**不足以**支撑行为断言）。
> ⇒ 本节每条 E 都是**本机实跑**的产物；探针脚本**不进仓库**。

| # | 场景 | 上游实际行为 | 对本 feature 的含义 |
|---|---|---|---|
| **E-01** | 自环图 + `recursion_limit=3` | 抛 `langgraph.errors.GraphRecursionError`；消息 `Recursion limit of 3 reached without hitting a stop condition...` | 类型可判定（spec P-04 / P-05） |
| **E-02** | 不设置上限 | `ensure_config()["recursion_limit"] == 10007` | 默认值 **10007**（spec P-01） |
| **E-03** | 静态 `interrupt_before=["a"]` | `a` 执行 **0** 次；结果字典**没有** `__interrupt__` 键 | 静态 before 语义（spec P-08 / P-12） |
| **E-04** | 静态 `interrupt_after=["a"]` | `a` 执行 **1** 次；结果字典**没有** `__interrupt__` 键 | 静态 after 语义（spec P-09 / P-12） |
| **E-05** | 静态 before 后 `invoke(None, config)` 恢复 | 目标执行 **1** 次；`snapshot.next` 被消费 | 恢复入口（spec P-13） |
| **E-06** | 静态挂起后 `Command(resume="X")` | 与 `None` **行为一致**；`X` 不被投递给任何节点 | resume 值被忽略（spec P-14） |
| **E-07** | `Command(goto=[Send,Send])` + 静态边 `fan→w` + `interrupt_before=["w"]` | **3** 个待执行任务（1 标准 + 2 fan-out）；`w` 执行 **0** 次；`snapshot.interrupts == ()` | fan-out × before（spec P-15） |
| **E-08** | 同上 + `interrupt_after=["w"]` | 3 个任务各执行 **1** 次；单个挂起；`snapshot.interrupts == ()` | fan-out × after（spec P-15） |
| **E-09** | 同一节点同时配 before / after | 首次 **before** 挂起；恢复后执行；再 **after** 挂起 | 优先级（spec P-16） |
| **E-10** | `compile(interrupt_before=["nope"])` | `ValueError: Interrupt node \`nope\` not found` | 未知节点名失败（spec P-07） |
| **E-11** | 裸 `"*"` / `["*"]` / 裸 `"review"` / `("review",)` | 裸 `"*"` 接受（`interrupt_before_nodes == "*"`）；`["*"]` 抛 `ValueError`；裸 `"review"` 与 `("review",)` 抛 `TypeError`；`["review"]` 接受 | 静态写法（spec P-17 / Q13） |
| **E-12** | 节点抛真异常 + `interrupt_after` | 抛**原异常**，不返回挂起态 | 真异常优先（spec P-08 / H-7） |
| **E-13** | 最后节点 `interrupt_after` | `snapshot.next == ()`；`invoke(None, config)` 直接完成 | `next` 可为空（spec P-19） |
| **E-14** | `recursion_limit` 为 `True` / `1.5` / `"3"` | `True` 与 `1.5` 被实际接受（`True ≈ 1`）；`"3"` 抛 `TypeError`（`'<' not supported`） | freegraph **拒绝** `bool` / 浮点（spec X-7 · 更严） |

### 1.1 逐条源码锚点（`路径:行号`）

- `langgraph/_internal/_config.py:32` —— `DEFAULT_RECURSION_LIMIT = int(getenv("LANGGRAPH_DEFAULT_RECURSION_LIMIT", "10007"))`。
- `langgraph/_internal/_config.py:184-186` —— `recursion_limit` 的 config 键。
- `langgraph/pregel/main.py:2563-2564` —— `recursion_limit must be at least 1`。
- `langgraph/pregel/main.py:3004-3011` —— `out_of_steps` ⇒ `GraphRecursionError`。
- `langgraph/pregel/_loop.py:608-610` —— 步数上限先判（`step > stop`）。
- `langgraph/pregel/_loop.py:667-670` —— 静态 before 抛 `GraphInterrupt()`（**空载荷**）。
- `langgraph/pregel/_loop.py:720-723` —— 静态 after 抛 `GraphInterrupt()`（**空载荷**）。
- `langgraph/pregel/_loop.py:1701` —— `stop = step + recursion_limit + 1`。
- `langgraph/pregel/_algo.py:155-185` —— `should_interrupt` 的「自上次中断以来有更新」判定。
- `langgraph/graph/state.py:1177-1188` —— `compile(..., interrupt_before=, interrupt_after=)` 签名。
- `langgraph/graph/state.py:1257-1264` —— `interrupt_before = interrupt_before or []` 与列表拼接
  （⇒ 裸字符串 / 元组会 `TypeError`）。
- `langgraph/pregel/main.py:768-769` / `:814-815` —— `interrupt_*_nodes` 的存储。

---

## §2 既有测试的**回归面探测**（**C-01…C-12**）

> **方法**（宪法 v1.11.0「冻结断言清单 MUST **实测化**」）：以**源码引用**定位会被本 feature
> 落地形态影响的冻结断言 ⇒ 逐条判定「变红 / 不变红」。
> ⚠️ **基线**：**1203 passed / 4 skipped**（2026-11-15）⇒ 变红才可归因到本 feature。

| # | 冻结断言（`文件:行号`） | 断言内容 | 本 feature 的落地形态 ⇒ 判定 | 处置 |
|---|---|---|---|---|
| **C-01** | `tests/runtime/test_interrupt_contract.py:38-39` | `SuperStepResult` / `InterruptResult` 各 **4** 字段 | 静态挂起复用 `InterruptResult`；`suspension_kind` 只进 metadata ⇒ **不变红** | ✅ 零改动 |
| **C-02** | `tests/runtime/test_superstep_concurrency.py:621-645` | `SchedulerState` 字段清单（含 `fanout`）与零参构造 | 本 feature **不新增字段** ⇒ 字段清单**逐字不变** | ✅ 零改动 |
| **C-03** | `tests/runtime/test_superstep_concurrency.py:655-676` | `run_super_step` / `run_super_steps` 参数名 / 种类 / 缺省 | **一字不动**（静态断点只在 `run_graph`） | ✅ 零改动 |
| **C-04** | `tests/runtime/test_interrupt_checkpoint.py:206-230` | `.scheduler` 的 JSON 往返 + 四个字段相等 | `to_checkpoint` **增 `fanout` 键** ⇒ 空图时 `fanout == {}` 仍可 JSON；新测试补 `fanout` 往返。⚠️ **B11F1 I-12「不落盘」历史断言**按 **F-3** 拆分（B11F1 交付时不含 ⇒ B13F1 起含） | ⚠️ **扩展**（不删既有断言） |
| **C-05** | `tests/runtime/test_superstep_contract.py`（GraphSpec 构造 / V-1…V-8） | 既有 `GraphSpec(...)` 写法与失败信号 | 新字段 **keyword-only + 缺省 `()`** ⇒ 既有写法零改动；B7F1 既有 V-1…V-9 与 B7F4 的 V-16 形态族不动；B11F1 的 V-15…V-21（其 V-16 为 `goto` 槽位规则）不动 | ✅ 零改动 |
| **C-06** | `tests/runtime/test_superstep_basic.py:557-576` | `conditional_edges` 非空 ⇒ `ValueError`；交付规格恒空 | 本 feature **不碰** `conditional_edges` | ✅ 零改动 |
| **C-07** | `tests/runtime/test_send_fanout.py` | fan-out 任务 / 归并 / 并发 / 恢复 | 本 feature **只增**静态断点分支；fan-out 既有语义不变 | ✅ 零改动 |
| **C-08** | `tests/runtime/test_interrupt_resume.py` | 动态中断的挂起 / 恢复闭环 | `_resume_graph` 只在「无中断 + 静态标记」时新增分支；动态路径不变 | ✅ 零改动（新分支不触发） |
| **C-09** | `tests/contracts/test_architecture.py:450` · `test_read_contract.py:63` | L1 公开符号面 **21** | 本 feature **零 L1 改动** | ✅ 零改动 |
| **C-10** | `tests/differential/parity_probe.py`（既有 **45** 个场景 = D-01…D-37 + DI-01…DI-08） | 上游 ↔ freegraph 对跑 | 既有场景不涉及静态断点 / `recursion_limit` ⇒ **追加** D-38…D-49 | ✅ 追加 |
| **C-11** | `harness/demo/graph_core.py:447-464` | `case_recursion_limit` 的 `soft(...)` | **本 feature 改为 `check(...)` + 精确异常类型**；M1 门面未就绪 ⇒ 脚本以**退出码 2** 结束（不判 FAIL），端到端仍待 B7F3 | ⚠️ **计划内改动**（F-6） |
| **C-12** | `harness/demo/README.md:66-75` | 软断言清单含 `recursion_limit` | 删除该行（形态已锁定） | ⚠️ **计划内改动**（F-7） |

### 2.1 结论

- **必须回溯修订的冻结断言 = 0 处**（`GraphSpec` / `run_graph` 的签名是**兼容扩展**）。
- **计划内改动的文档 / 验收脚本 = 2 处**（`graph_core.py` · `README.md`）。
- **需要扩展的测试 = 1 处**（`test_interrupt_checkpoint.py` 的 JSON 往返，**只增** `fanout` 断言）。
- **不能改的基准**：`harness/demo/target.py`（只读）· L1 契约层 · `runtime.__all__`（仍 **23**）·
  门禁编号 **G1–G30** · C1–C27。

---

## §3 设计决策（**由 plan 冻结** · 与 spec 裁定一一对应）

> **记注**：本节只落**名字 / 形状 / 落点**（spec 未规定、但实现必须定死的部分）⇒
> **MUST NOT** 改变任何语义（语义一律以 spec 为准）。

| # | 决策 | 选定 | 理由 | 落点 |
|---|---|---|---|---|
| **D-01** | **静态断点字段的形状** | `GraphSpec` 增两个 **keyword-only** 字段：`interrupt_before: str \| Sequence[str] = ()` · `interrupt_after: str \| Sequence[str] = ()` | 与 spec FR-002 逐字一致；缺省 `()` ⇒ 既有调用方零改动；`"*"` 在构造期展开为**可执行节点**（排除 `__start__` / `__end__`；节点表顺序） | data-model §1 · contract §1 |
| **D-02** | **静态断点的校验（V-22…V-25）** | **V-22** 非 `str` 元素 / 裸非 `"*"` 字符串 ⇒ `TypeError`；**V-23** 空串 ⇒ `ValueError`；**V-24** `__start__` / `__end__` / 序列中的 `"*"` ⇒ `ValueError`；**V-25** 不在节点表 ⇒ `ValueError`；重复去重；`"*"` 裸串 ⇒ 展开为可执行节点；`None` ⇒ `TypeError`（B7F2 把 `None` 归一为 `()`） | 与上游 E-10 / E-11 的可观察失败信号同族；构造期失败与 B7F1 裁定 32 一致 | data-model §1.2 · contract §1.2 |
| **D-03** | **低层入口的拒绝（V-26）** | `run_super_step` / `run_super_steps` 入口若 `spec.interrupt_before` 或 `.interrupt_after` **非空** ⇒ `ValueError`（消息点名「静态断点只在 run_graph 生效」） | 低层返回类型冻结为 `SuperStepResult`；静默忽略会误导用户 ⇒ spec Q12 / X-6 | data-model §1.3 · contract §9 |
| **D-04** | **before 的检查位置** | 在 `_run_graph_loop` 的「触发判定之后、递归上限检查之后、`_run_round` 之前」检查；**不移动循环顶部 `steps += 1`**（空终轮口径属 B7F1 冻结面）⇒ 命中且 ack 允许 ⇒ 直接返回 `InterruptResult`，其 `steps = 循环 steps - 1` | 不执行任何任务 / 不消费触发源 / 不推进 `state.step`；`InterruptResult.steps` **不含**这一轮 | data-model §2.1 · contract §2 |
| **D-05** | **after 的检查位置** | 在本轮 `_run_round` 成功、`state.step += 1`、待写收集之后；若 `round_executed` 命中且 ack 允许 ⇒ 返回 `InterruptResult` | 写入已合并、`steps` **含**本轮；恢复后不重跑已执行节点 | data-model §2.2 · contract §3 |
| **D-06** | **静态挂起的 metadata 形状** | `_suspend_metadata` 增加两个键：`"suspension_kind": "static_before" \| "static_after" \| None` · `"static_ack": {"channel_versions": dict[str,int]} \| None`；同时把这两个键镜像进 `scheduler` 子字典（供当前 `get_tuple` 读取） | 当前 `Checkpointer` 协议只把 `.scheduler` 暴露给 L2；镜像两份使 B13F1 可独立恢复；B14F1 只读 metadata 也能拿到 | data-model §3 · contract §5 |
| **D-07** | **静态挂起的恢复分支** | `_first_graph` / `_resume_graph` 从 `history.scheduler` 读 `suspension_kind` / `static_ack`：① `input=None` ⇒ `first_round = snapshot.next`（可为空）；② `Command(resume=...)` ⇒ 若 `interrupts == ()` 且 kind 为静态值 ⇒ **不**抛 `no_pending_interrupt`，**忽略** resume 值，按 `snapshot.next` 继续；③ 状态字典输入 ⇒ 先写通道（新进度）再继续 | 与 spec FR-007 / Q14 逐字一致；动态路径（kind 非静态）保持原判定 | data-model §2.3 · contract §6 |
| **D-08** | **静态恢复完成后的清标记** | 若本次运行是**静态恢复**且最终返回 `SuperStepResult` ⇒ 调 `checkpointer.put` 写一次**完成快照**：`values=最终稀疏状态` · `metadata` 的 `next=()` / `interrupts=()` / `tasks=()` / `scheduler` 中 `suspension_kind=None` / `static_ack=None`；登记为 **F-10**（一次性完成写） | 否则旧快照的 `suspension_kind` / `next` 会在后续 `input=None` 时被再次当成挂起（静态 before 会重复执行）；这是恢复闭环的必要收尾 | data-model §2.4 · contract §6.4 · spec F-10 |
| **D-09** | **防重复触发的 ack 语义** | `static_ack["channel_versions"]` = 挂起时的通道版本水位；`static_allowed(ack, state)` = `ack is None` 或对**两侧键的并集**比较 `current.get(k, 0) > previous.get(k, 0)`（新通道视为 0 → >0 ⇒ 允许触发） | 与上游 `should_interrupt` 的「自上次中断以来有更新」同款（P-10）；不引入额外状态字段；**MUST NOT** 只遍历旧 ack 键（会漏掉新通道） | data-model §2.5 · contract §7 |
| **D-10** | **`recursion_limit` 的解析与优先级** | 新私有模块 `_recursion.py`：`DEFAULT_RECURSION_LIMIT = 10007`；`resolve_config(config)`：`None → RunConfig()` · `Mapping → RunConfig.from_dict(..., ignore_unknown=True)` · `RunConfig → 原样`；`resolve_limit(config_limit, max_steps) = config_limit if not None else max_steps`；再 `validate_limit` | spec FR-010 / Q11：dict / `RunConfig` **互斥二选一** > `max_steps` > 默认；**不新增** `recursion_limit=` 关键字；只放宽 `run_graph.config` 注解 | data-model §4 · contract §1 |
| **D-11** | **`fanout` 的检查点编码** | `SchedulerState.to_checkpoint` 增 `"fanout"` 键：`{str(producer_id): {"producer": str, "suppresses_static": bool, "tasks": [{"target","arg","index","suppresses_static"}, ...]}}`；`from_checkpoint` 缺键 ⇒ `{}`；键还原为 `int`；**`_restore_scheduler` MUST 回填 `state.fanout`** | 静态 before 的 N 个 fan-out 任务必须跨挂起保留（spec 裁定 10 / F-3）；旧快照缺键宽容；只改 to/from 不够 | data-model §3.2 · contract §8 |
| **D-12** | **`recursion_limit` 的校验（V-R1…V-R4）** | **V-R1** **非 `None` 值**且 `type(value) is not int`（含 `bool`）⇒ `TypeError`；**V-R2** `value < 1` ⇒ `ValueError("recursion_limit must be at least 1")`；**V-R3** `config` 不是 `None` / `Mapping` / `RunConfig` ⇒ `TypeError`；**V-R4** dict 的未知键忽略（`ignore_unknown=True`）。⚠️ `recursion_limit=None` **跳过 V-R1 / V-R2**（视为未提供 ⇒ 落回下一层） | spec FR-012 / X-7；上游 `bool` / 浮点宽容，freegraph 刻意更严 | data-model §4.2 · contract §2 / §3 |
| **D-13** | **新私有模块落位** | `src/freegraph/runtime/_static.py`（常量 / 归一 / 匹配 / ack）· `_recursion.py`（默认值 / 解析 / 校验）；`_fanout.py` 增编解码；`superstep.py` 只做接线 | 与 B12F1 的 `_concurrency.py` 同款（私有模块 · 不进 `__all__`）；L2 目录条目内 ⇒ G25 恒绿；**MUST NOT** 单独立层注册表条目 | plan §Project Structure |
| **D-14** | **验收脚本升级与延期** | `graph_core.py` 立即 `soft → check` + 精确 `GraphRecursionError`；新增 L2 等价硬测试；端到端真跑归 **B7F3**（D-3） | spec Q9 / Q10 / EV-1；避免永久红 CI | quickstart §8 · plan §Phases |

---

## §4 破冻结面的回溯修订清单（**T-1…T-10** · 与 spec F-1…F-10 一一对应）

> **拆分而不删**：只增字段 / 键 / 校验 / 措辞；不删除既有断言。

| # | 对应 | 冻结面（`文件:行号`） | 处置 |
|---|---|---|---|
| **T-1** | **F-1** | `src/freegraph/runtime/superstep.py:166-210` 的 `GraphSpec` 构造签名；`specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §2 | **只增**两个 keyword-only 字段（缺省 `()`）⇒ 既有 `GraphSpec(...)` 零改动 |
| **T-2** | **F-2** | `superstep.py:401-468` 的 `_validate_graph_spec`；契约 §2.1.1 | **只增** V-22…V-25 的**调用点**（`_validate_graph_spec` → `normalize_static_points` 单一入口；不重复校验）⇒ B7F1 既有 V-1…V-9 与 B7F4 的 V-16 形态族一字不改；B11F1 的 V-15…V-21（其 V-16 为 `goto` 槽位规则）不动 |
| **T-3** | **F-3** | `superstep.py:250-322` 的 `to_checkpoint` / `from_checkpoint`；B10F1 `checkpoint-contract.md` §3 · B10F1 spec 裁定 9；**B11F1 的 `contracts/send-contract.md` §5.1 / `data-model.md` I-12 / `tasks.md` T019 / `plan.md` PR-8 / `research.md` DR-02·D-08 / `quickstart.md` DR-02 / `spec.md` D-3**（F-14 仅顺序口径说明） | **只增** `fanout` 键（缺省 `{}`）⇒ 旧快照宽容解码；**B11F1 的「不落盘」历史断言拆分而不删**（B11F1 交付时不含 ⇒ B13F1 起含） |
| **T-4** | **F-4** | `superstep.py:1768-1840` 的 `run_graph`；B10F1 `interrupt-resume-contract.md` §2 · B10F1 spec 裁定 10 | `config` 注解**放宽**为 `RunConfig \| Mapping[str, Any] \| None`；**不新增** `recursion_limit=` 关键字 |
| **T-5** | **F-5** | `superstep.py:1912-2010` 的 `_resume_graph`；B10F1 契约 §6.2 · B10F1 spec 裁定 4 | **拆分** `no_pending_interrupt`：静态标记（`static_before` / `static_after`）⇒ 继续（`next` 允许为空）；**非静态且无动态中断** ⇒ 仍抛（**不论 `next` 是否为空**） |
| **T-6** | **F-6** | `harness/demo/graph_core.py:447-464` | `soft(...)` → `check(...)`；异常判定收紧为 `GraphRecursionError` |
| **T-7** | **F-7** | `harness/demo/README.md:66-75` | 删除 `recursion_limit` 软断言行；C25 行由后续 B8F3 正式作废移除；规则文字保留 |
| **T-8** | **F-8** | `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §5 · `spec.md` | **只增**一句：低层入口收到非空静态字段时显式拒绝 |
| **T-9** | **F-9** | `superstep.py:1574-1599` 的 `_suspend_metadata` / `_write_suspend`；B10F1 契约 §4 · B10F1 spec 裁定 9 | **只增** `suspension_kind` / `static_ack` 两个 metadata 键；既有 `next` / `interrupts` / `tasks` / `scheduler` 的**既有键**不变；kind/ack **MUST** 镜像进 `scheduler` 子字典 |
| **T-10** | **F-10** | `_clear_static_suspension`（`run_graph` 完成路径）；B10F1 契约 §4 · B10F1 spec 裁定 9 | **只增**一次性完成写：静态恢复返回 `SuperStepResult` ⇒ `checkpointer.put` 写完成快照（清 `suspension_kind` / `static_ack` / `next` / `fanout`）；**不是**每轮末快照（后者仍归 B14F1） |

> ⚠️ **基线义务**：上述修订**全部落地**后，`pytest -q` MUST 保持 **1203 + 新增** 全绿；
> **MUST NOT** 写永久红 CI。`graph_core.py` 的端到端真跑按 **EV-1** 延期到 B7F3。

---

## §5 遗留登记 / 已知限制（**DR-01…DR-07** · **不改判据**）

| # | 遗留 | 影响 | 处置 |
|---|---|---|---|
| **DR-01** | `fanout` 账本里的 `arg: Any` 可能**不是 JSON 可序列化**对象 | `.scheduler` 的「纯数据」承诺（C19 ③）在极端自定义对象上不成立 | **编码职责**：本 feature 把 `fanout` 编入 `to_checkpoint`（F-3），测试使用 **JSON 兼容** `arg`；**存储职责**：非 JSON 兼容 `arg` 的持久化失败面 / 序列化协议归 **B14F1**（D-5）⇒ **MUST NOT** 在本 feature 里静默 `repr` / 丢弃 |
| **DR-02** | 静态挂起的 `suspension_kind` / `static_ack` 需要跨运行保存 | 当前 `StubCheckpointer` 只暴露 `.scheduler` | 本 feature **镜像**进 `scheduler` 子字典（D-06）；B14F1 同时持久化顶层 metadata（D-5） |
| **DR-03** | `graph_core.py` 端到端真跑需 `compile()` / `invoke()` | M1 无门面 API | **B7F3**（D-3）· **EV-1** |
| **DR-04** | 最后节点 after 挂起后 `next == ()` | 若不复位标记，后续 `input=None` 可能重放 | **D-08** 的完成快照清标记 |
| **DR-05** | `"*"` 在构造期展开为**当前节点表的可执行节点**（排除 `__start__` / `__end__`） | 构造后增删节点不会改变展开结果 | `GraphSpec` 本就冻结 / 纯数据；文档写明 |
| **DR-06** | `bool` / 浮点作为 `recursion_limit` 被拒绝 | 与上游的实际宽容不同 | **X-7**（更严失败信号 · 判据零放宽） |
| **DR-07** | **纯 fan-out before** 时上游 `snapshot.next` 是否为空**未实测**（E-07 含标准边；E-13 只覆盖 after 最后节点） | D-45 若断言上游 `next == ()` 会缺实测支撑 | D-45 **不判**上游 `next`；freegraph 侧空 `next` 恢复由本地 **T076** 覆盖；若要恢复该差分断言，先补一条上游实测 |

---

## §6 spec 事实性核对（**只更正事实 · 未改任何判据**）

| # | spec 的断言 | 核对结果 | 处置 |
|---|---|---|---|
| 1 | 上游有效缺省 **10007** | ✅ 实测 `ensure_config()["recursion_limit"] == 10007` | 硬编码 10007（X-4） |
| 2 | 静态 before / after 的结果**无** `__interrupt__` 键 | ✅ 实测 E-03 / E-04 | freegraph 刻意补空元组（X-1） |
| 3 | 最后节点 after 的 `snapshot.next == ()` | ✅ 实测 E-13 | freegraph 用 `suspension_kind`（X-8） |
| 4 | 裸 `"*"` = All · `["*"]` 非法 | ✅ 实测 E-11 | 构造期展开（P-17 / Q13） |
| 5 | `GraphSpec` 当前字段 = `channels` / `nodes` / `edges` / `conditional_edges` | ✅ `superstep.py:197-207` | 只增两个 keyword-only 字段 |
| 6 | `SchedulerState` 当前字段含 `fanout` | ✅ `superstep.py:245-248` | **不新增字段**；只增账本键 |
| 7 | `run_graph` 当前 `config: RunConfig \| None` | ✅ `superstep.py:1774` | 只放宽注解 |
| 8 | `graph_core.py` 的 `soft(...)` 在 `:462` | ✅ | 改为 `check(...)`（F-6） |
| 9 | 既有绿基线 **1203 passed / 4 skipped** | ✅ 2026-11-15 实跑 | 基线义务 |
| 10 | spec Assumptions 曾写「裁定 1–13」 | ✅ 已修正为 **1–14**（Q14 新增 `suspension_kind`；T115 只做最终复核） | 判据未变；plan / tasks 以 **1–14** 为准 |

---

## §7 换上游版本时 **MUST 重做** 的取证动作

1. **复核全部行号**：`_internal/_config.py:32` / `:184-186` · `pregel/main.py:2563-2564` /
   `:3004-3011` / `:768-769` / `:814-815` · `pregel/_loop.py:608-610` / `:667-670` /
   `:720-723` / `:1701` · `pregel/_algo.py:155-185` · `graph/state.py:1177-1188` / `:1257-1264`。
2. **重跑 E-01…E-14**（探针脚本**不进仓库** ⇒ 换版本后须重写并重跑）。
3. **复核差分判词**：`tests/differential/parity_probe.py` 的 **D-38…D-49** 在新版本上的判词
   ⇒ 若上游行为变了 ⇒ **必须**重判（`SAME` / `STRICTER` / `DIFF` 三态同步改）。
4. **复核 `recursion_limit` 的类型宽容度**（上游 `bool` / 浮点）⇒ 若上游收紧 ⇒ 重判 **X-7**。
