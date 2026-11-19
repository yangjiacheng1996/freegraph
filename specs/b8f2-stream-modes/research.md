# B8F2 · Phase 0 研究记录（上游实测取证 + 决策登记 + 遗留登记）

**Feature**: `B8F2` · `stream()`：多模式流式输出 + `StreamWriter`
**Spec**: [./spec.md](./spec.md) · **Plan**: [./plan.md](./plan.md)
**取证日期**: 2026-11-19 · **上游版本**: `langgraph` **1.2.11** + `langchain-core` **1.7.6**

> **本文件是「证据」载体，不是「判据」载体** —— 判据的唯一权威是 spec 与
> `contracts/stream-contract.md`（Phase 1 写就）；本文件 MUST NOT 被测试解析。

> **编号域隔离**：本文的 **D-01…D-15** 是**决策**编号 · **DR-1…DR-9** 是**遗留登记** ·
> **C-1…C-8** 是**事实性更正** · **E-1…E-18** 是**实测**编号；
> 与 spec 的「承接 H-1…H-10」「差分 D-121…D-136」「破面 T-1…T-5」是**互不相干**的编号域。

---

## §0 方法与取证环境

### 0.1 环境（零仓库改动）

| 项 | 值 | 核实方式 |
|---|---|---|
| 上游版本 | `langgraph` **1.2.11** · `langchain-core` **1.7.6** | `importlib.metadata.version` |
| 版本钉死 | `pyproject.toml:99-101`（`"langgraph==1.2.11"` · `differential` 依赖组） | 读文件 |
| 解释器 | CPython **3.11.16** | `.venv/bin/python -c "import sys"` |
| 上游包根 | `.venv/lib/python3.11/site-packages/langgraph/` | —— |
| 仓库改动 | **零**（本 phase 只写 `specs/` 工件） | `git status --porcelain` |
| 实施前复核（2026-11-20） | `langgraph==1.2.11` / `langchain-core==1.7.6`；锚点 `types.py:122-124,637-646` / `config.py:126` / `_executor.py:64,71,164` / `_loop.py:580,674,1461-1466` / `main.py:2964,4228,4236-4243` 已复核 | `.venv/bin/python` |

### 0.2 绿基线（**实施前** · 2026-11-19）

| 项 | 计数 |
|---|---|
| passed | **1607** |
| skipped | **4** |
| failed | **0** |
| 耗时 | **106.58s** |

```
1607 passed, 4 skipped in 106.58s (0:01:46)
```

> 4 条 skip 的原因：① C8 占位用例（B8F1 已落地）② mypy 未安装 ③ API 快照未开
> `--update-api-snapshot` ④ Windows 时钟分辨率。⇒ **零失败** ⇒ 后续红点可归因。

### 0.3 实测命令形态

```bash
cd /home/ctyun/workspace/github/freegraph
.venv/bin/python - <<'PY'
# 探针：构造 StateGraph，逐 mode 消费 stream()，打印类型 / 条数 / 载荷
...
PY
```

本轮探针覆盖：七种 mode · `StreamWriter` · 多 mode · 非法 mode · 中断 ·
失败 · 挂 checkpointer 的 `checkpoints` · 多次 `custom` 写入 · 无流 `get_stream_writer`。

---

## §1 决策登记（D-01…D-15）

| # | 决策 | 理由 | 被否的备选 |
|---|---|---|---|
| **D-01** | **事件信封 = 四键** `{stream_mode, payload, run_id, thread_id}` | D11 要求每条事件带 id；L1 返回类别是 `Iterator[dict[str, Any]]`；七档统一、无死字段；后期官方文档可自洽 | 上游 v2 六键（`ns` 在 v1 恒空、`interrupts` 仅 `values` 有意义）· 单 mode 直接载荷 + 旁路 id（不满足「每条事件携带」） |
| **D-02** | **L3 持有主循环**，**L2 提供私有会话/初始化助手** | 与上游 `while loop.tick()` 同构；`values` 归一必须复用 L3 的 `_full_state`；ARCH-1 禁止 L2 import L3 | 把整条流式循环塞进 L2（会让 L2 依赖 `_full_state` ⇒ 反向依赖） |
| **D-03** | **`StreamWriter` = 运行级 contextvar getter + 每任务 `copy_context()`** | 照抄上游 `config.py:126` + `_executor.py:64`（`copy_context()`）/:71（`ctx.run`）/`:164`（async）；零重复载体（原则 XII） | 显式把 writer 作为节点参数传入（另立第二套载体） |
| **D-04** | **`custom` 缓冲 = 每任务独立 + 轮末按 TaskId 序产出** | 并发下保证确定性；不把可观测事件塞进 `_TaskOutcome`（H-7）；⚠️ 上游为逐写即时 ⇒ 登记 **P-23 / X-6** | 全局无序 list（完成时刻抖动）· 塞进结果槽（污染执行结果） |
| **D-05** | **`tasks` = 每完成 task 一条 + `PregelTask`；`SuperStepResult` 追加 `tasks`** | spec FR-010 的冻结口径；复用 L1 既有 `PregelTask`；`SuperStepResult` 是任务级别的唯一现成载体 | 完全照抄上游 `tasks` 的 start/result 双事件 + 普通 dict（提示词已冻结相反口径）· 新建独立的 task 结果对象（原则 XII ③） |
| **D-06** | **中断时 `tasks` / `debug` 仍为被中断 task 产出一条** | 上游实测 E-8 明确产出；提示词说「每个 task 完成时一条」；不改变 `SuperStepResult` / `InterruptResult` 字段 | 中断轮完全不产 task 事件（与上游和提示词都不一致） |
| **D-07** | **失败时先产出已发生的 `custom`，再重抛原异常** | 上游实测：`custom` 先出、异常后抛；FR-006 要求不吞异常 | 丢弃失败轮 custom（丢失已发生的可观测事实） |
| **D-08** | **`checkpoints` / `messages` v1 恒为空序列** | `checkpoints` 源属 B14F1；`messages` 是 LangChain LLM token 流（freechain）；提示词允许空/占位 | 伪造 checkpoint 事件（违反证据纪律）· 从节点写入里猜 message（启发式，错误） |
| **D-09** | **`updates` 的载荷 = `{节点名: {通道: 值 \| 元组}}`** | 与上游单 task 载荷同形；同通道多写用元组保留归约顺序 | 上游的 `{"$writes": [...]}`（多一层包装）· 简单最后值（丢失归约信息） |
| **D-10** | **`debug` = `tasks` 的包裹 + `type="task_result"` + 1 起 step** | 上游 `debug` = `checkpoints` + `tasks` 的包裹；v1 无 checkpoint 源 ⇒ 只剩 tasks；固定 step 便于断言 | 照抄上游 `task` / `task_result` 双事件（本 feature 的 `tasks` 只有完成事件）· 0 起 step（与上游负 step 更远） |
| **D-11** | **`run_id` = `uuid4().hex`，每次 `stream()` 一个；`thread_id` 按 `resolved_thread_id()`；`RunConfig.run_id` 忽略** | D11 冻结「运行时生成、用户不可覆盖」；忽略而非拒绝以保持上游配置可原样传入（clarify 轮 A） | 采用 `RunConfig.run_id`（违反 D11）· 显式拒绝（成功路径新增失败点） |
| **D-12** | **公开面 = 门面 +1（`get_stream_writer`）· 契约 +1（`StreamWriter`）· runtime 不变** | 单一门面是本仓既有结构；类型属于 L1；不新建 `freegraph.config`（clarify 轮 A） | 新建 `freegraph.config` 模块（公开模块变多）· 双入口别名（公开面更大） |
| **D-13** | **节点关键字注入 = 参数名 `writer`**（`POSITIONAL_OR_KEYWORD` / `KEYWORD_ONLY`；注解 ∈ `StreamWriter` / `"StreamWriter"` / 空） | 上游 `_runnable.py:183-188` 的 runtime key 是 `stream_writer`，但**参数名是 `writer`**；注入值是 `get_stream_writer()`（无流为 no-op）；关闭 B8F1 DR-4 | 参数名 `stream_writer`（上游**不**注入；实测 E-17）· 支持 `**kwargs`（上游不注入） |
| **D-14** | **`stream_mode` 默认档照抄上游**：签名默认 `None`，`None` ⇒ `"updates"` | `CompiledStateGraph` 默认 `updates`（`state.py:1357`）；`Pregel.stream` 接受 `None`（`main.py:2737-2743`）；实测 E-18 | 保留 `"values"` 默认（未登记的行为偏离）· 拒绝 `None`（未登记的成功路径差异） |
| **D-15** | **L2 私有单轮助手 `_run_single_step` / `_stream_tick`**：`run_super_step` 与 `_stream_tick` 共用同一执行/路由/触发实现；`_stream_tick` 透传原始 `route_config` 并在**执行前**精确判 `recursion_limit` | `run_super_step` 当前把 `route_config` 写死 `None`（`superstep.py:1536` / `:1597`），会切断 B8F1 双参路由的 `config`；且它不暴露「下一轮是否仍有任务」，无法精确判上限；私有助手不改公开签名、不复制实现 | 改 `run_super_step` 签名（破 B7F1 冻结面，需额外追认）· 用 L2 私有 contextvar 隐藏传递（可读性差、生命周期隐式）· 只支持单参路由（登记新偏离，伤上游兼容） |

---

## §2 上游实测基线（E-1…E-18）

> 全部于 `.venv` 的 `langgraph 1.2.11` 真跑；探针脚本不提交仓库。

| # | 实验 | 真实输出 |
|---|---|---|
| **E-1** | `a → b` 线性图，`stream_mode="values"` | 3 条：初始 `{"x":0,"log":[]}` → `{"x":1,"log":["a"]}` → `{"x":2,"log":["a","b"]}` |
| **E-2** | 同图，`stream_mode="updates"` | 2 条：`{"a": {...}}` / `{"b": {...}}` |
| **E-3** | 同图，`stream_mode="tasks"` | **4 条**：每 task 一条开始（`id/name/input/triggers`）+ 一条完成（`id/name/error/result/interrupts`） |
| **E-4** | 同图，`stream_mode="debug"` | 4 条：`{step,timestamp,type,payload}`；`type` 为 `task` / `task_result` |
| **E-5** | 挂 `MemorySaver`，`stream_mode="checkpoints"` | 3 条 checkpoint（`config` / `values` / `metadata` / `next` / `tasks`） |
| **E-6** | 无 LLM 调用，`stream_mode="messages"` | 0 条 |
| **E-7** | 节点内 `get_stream_writer()({"msg":"hi"})`，`stream_mode="custom"` | 1 条：`{"msg":"hi"}` |
| **E-8** | 节点内 `interrupt("approve?")`，分别消费 `values` / `updates` / `tasks` | `values` = 初始 + 含 `__interrupt__` 的收尾；`updates` = `{"__interrupt__": (...)}`；`tasks` = **开始 + 完成**（完成事件 `interrupts` 非空）；**流均不抛** |
| **E-9** | `invoke()` 期间调用 `get_stream_writer()` | 返回可调用对象（no-op），不抛；图正常完成 |
| **E-10** | `stream_mode="bogus"` / `["values","bogus"]` | 静默空流 / 只产出合法 mode；**不抛** |
| **E-11** | `stream_mode=["values","updates"]` | `("values", …)` / `("updates", …)` / `("values", …)` 元组序列 |
| **E-12** | `values` 的第一条 | 是**输入状态**（执行前），不是第一步之后 |

### 2.1 新增实测（本 feature 修正 spec 用）

| # | 实验 | 真实输出 | 结论 |
|---|---|---|---|
| **E-13** | 节点写 `custom` 后 `raise RuntimeError` | `custom` 事件**先产出**，然后 `RuntimeError` | 失败时 MUST 先 flush custom（D-07） |
| **E-14** | 中断节点，`stream_mode="tasks"` / `debug` | `tasks` = 开始 + 完成（`interrupts` 非空）；`debug` = `task` + `task_result` | 中断时 MUST 为 task 补发完成事件（D-06） |
| **E-15** | 非法 mode | `list(app.stream(...))` 返回空 / 忽略非法项 | freegraph 取 `ValueError`（更严 · X-2） |
| **E-16** | 多 mode | 产出 `(mode, payload)` 元组 | freegraph 用四键信封（D-01） |
| **E-17** | 节点签名 `def node(state, writer)` / `def node(state, stream_writer)` | `writer` 被注入并产出 custom；`stream_writer` **不被注入** ⇒ `TypeError` | 参数名是 **`writer`**；`stream_writer` 是 runtime key（D-13 / C-7） |
| **E-18** | 不传 `stream_mode` / 显式 `stream_mode=None`（`CompiledStateGraph`） | 均按 **`updates`** 产出（两节点图 = 每 task 一条），不抛异常 | 默认档是 **`updates`**；`None` 被接受（D-14） |

---

## §3 事实性更正（C-1…C-8）

| # | 位置 | 原表述 | 实测 / 事实 | 处置 |
|---|---|---|---|---|
| **C-1** | spec 引文差异 ② | 提示词说上游 `tasks` 载荷 = `PregelTask` | 上游是 `TaskPayload` / `TaskResultPayload` 普通 dict，且每 task 两条 | 已登记 **X-3**；按提示词 FR-010 冻结口径实现 |
| **C-2** | spec 引文差异 ③ | 「消费者不迭代时图仍应能正常跑完」 | 上游是**惰性生成器** ⇒ 不迭代 = 零执行 | 已收敛为「提前停止不泄漏 / 不吞异常」 |
| **C-3** | spec 引文差异 ① | D11「`run_id` 不进 `RunConfig`」 | `RunConfig` 现含 `run_id`（上游对齐 P3） | 不改字段；事件 `run_id` 仍由运行时生成；忽略用户值（clarify A）；**宪法已订正为 v1.15.2**（立项书 §5.3.1 保留为历史） |
| **C-4** | spec 引文差异 ④ | 只登记 B7F1 的 `SuperStepResult` 冻结面 | B12F1 裁定 25 ② / FR-013 也写「四字段零改动」 | 新增 **T-2** |
| **C-5** | 上游 `tasks` 的中断行为 | spec 初版写「不为被中断 task 补发」 | 上游实测 E-8 / E-14 **产出** | 已改为补发（D-06 · X-4 收窄） |
| **C-6** | 上游失败时 custom | spec 初版写「丢弃」 | 上游实测 E-13 **先产出** | 已改为先 flush 再重抛（D-07） |
| **C-7** | 上游 `stream_writer` 注入的参数名 | spec 初版沿用提示词写 `stream_writer` 关键字 | 上游参数名是 **`writer`**（`_runnable.py:183-188`）；`stream_writer` 是 runtime key；实测 E-17 | 已改为参数名 `writer`（D-13 / FR-036） |
| **C-8** | `custom` 产出时机 | 提示词 / US3 写「实时观察」 | 上游 `stream_writer` 直接 `stream.put(...)` ⇒ 逐写即时；freegraph 为并发确定性取**轮末批量** | 已登记 **P-23 / X-6**（DIFF · 必须自研区 ②「上游自身的不确定」）；US3 措辞改为「按轮观察」 |

---

## §4 遗留登记（DR-1…DR-9）

| # | 遗留项 | 现状 | 处置 / 承接 |
|---|---|---|---|
| **DR-1** | `StreamWriter` 的**关键字注入**（参数名 **`writer`**） | 上游有（`_runnable.py:183-188`）；2026-11-19 用户决策：本 feature 实现 | **已关闭**：FR-036 / T071-T072；参数名 `writer`；B8F1 DR-4 关闭 |
| **DR-2** | 会话连续 / `Command` 恢复 / checkpoint 持久化 | 上游支持；本 feature 的 `stream()` 只做全新运行 | 归 **B14F1 / B15F1 / B16F1**；`stream` 的 `input` 注解仍为 `StateDict` |
| **DR-3** | `tasks` 载荷形态 | 上游 dict + 双事件；freegraph `PregelTask` + 单完成事件 | 已登记 **X-3**；差分 **D-125** |
| **DR-4** | `debug` 载荷 | 上游 dict + `task`/`task_result` 双事件；freegraph `PregelTask` + 单 `task_result` | 已登记 **X-4**；差分 **D-126** |
| **DR-5** | `checkpoints` / `messages` 空序列 | 能力尚未交付 | 归 **B14F1**（checkpoint）/ freechain（messages） |
| **DR-6** | `PregelTask.id` 生成方式 | 上游 UUID；freegraph 不冻结生成方式 | 运行内唯一、不跨运行比较；差分不比较 id |
| **DR-7** | `updates` 同通道多写 | 上游 `{"$writes": [...]}`；freegraph 元组 | **X-1** 的子项；归约语义不变 |
| **DR-8** | 事件信封 | 上游 v1 原始载荷 / v2 四/三键；freegraph 四键 + id | **X-1**；D11 硬约束 |
| **DR-9** | 多 mode 事件形态 | 上游元组；freegraph 统一信封 | **X-1**；`stream_mode` 字段区分 |

---

## §5 关键代码锚点（freegraph 侧）

| 落点 | 文件:行号（当前） | 本 feature 动作 |
|---|---|---|
| `CompiledGraph.stream` 占位 | `src/freegraph/_stategraph.py:357-365` | 替换为真实流式门面（L3 主循环） |
| `_full_state` | `src/freegraph/_stategraph.py:235-267` | **复用**（MUST NOT 复制） |
| `SuperStepResult` | `src/freegraph/runtime/superstep.py:348-377` | **追加** `tasks` 字段 |
| `_run_round` | `src/freegraph/runtime/superstep.py:1282-1445` | 构建 `PregelTask` 快照 + 中断 capture |
| `_run_single_step` / `_stream_tick`（新增私有） | `src/freegraph/runtime/superstep.py`（`run_super_step` 邻域） | 单轮唯一实现点；透传 `route_config` + 执行前判上限 |
| `run_super_step` | `src/freegraph/runtime/superstep.py:1509-1550` | 委托 `_run_single_step`；透传 `tasks` |
| `run_super_steps` | `src/freegraph/runtime/superstep.py:1553-1630` | 累计 `tasks` |
| `_run_graph_loop` | `src/freegraph/runtime/superstep.py:1825-1950` | 累计 `tasks` |
| `_apply_input_writes` | `src/freegraph/runtime/superstep.py:1717-1742` | 流式会话初始化复用 |
| `_sparse_state` | `src/freegraph/runtime/superstep.py:1479-1481` | 流式会话取每轮稀疏状态 |
| `run_tasks_concurrently` | `src/freegraph/runtime/_concurrency.py:184-256` | 每任务 `copy_context()` |
| `_bind` | `src/freegraph/runtime/superstep.py:1330-1344` | 绑定当前 TaskId（供 custom 排序） |
| `bind_run` / `new_run_table` | `src/freegraph/runtime/_interrupt.py` | 流式会话初始化复用 |
| `RunConfig.resolved_thread_id` | `src/freegraph/contracts/types.py:234-245` | 事件 `thread_id` 解析 |
| `contracts.__all__` | `src/freegraph/contracts/__init__.py:30-52` | **追加** `StreamWriter`（21→22） |
| `facade.__all__` | `src/freegraph/graph.py:47-55` | **追加** `get_stream_writer`（7→8） |
| `runtime.__all__` | `src/freegraph/runtime/__init__.py:111-135` | **不变**（23） |

---

## §6 结论

- 七种 mode 的上游行为**全部**有实测支撑；freegraph 的差异**只**集中在
  信封 / `tasks` / `debug` 的形态与 `custom` 的产出时机，已登记 **X-1…X-6**。
- 需要破的冻结面 **5 类**（T-1…T-5，**T-3 含 B7F2 compile-contract / data-model 注记**）
  已在 spec 登记；本 plan 落实回溯修订与唯一一次追认。
- **D-15** 的 L2 私有 `_run_single_step` / `_stream_tick` 同时解决 **B8F1 双参路由的
  `config` 透传**与**递归上限的精确判定**；公开 L2 入口签名与 `runtime.__all__` 均不变。
- 零新增运行时依赖、零出站、零环境变量、零 async。
