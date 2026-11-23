# 上游对照契约（Upstream Parity）—— B8F2

**Feature**: `B8F2` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**核实环境**: CPython **3.11.16** · `langgraph` **1.2.11** + `langchain-core` **1.7.6**
（取证于 **2026-11-19**）

> **本文件是「证据」载体，不是「判据」载体** —— 判据的唯一权威是
> `stream-contract.md` 与 spec；本文件 MUST NOT 被测试解析。

---

## 1. 取证环境与纪律

| 项 | 值 |
|---|---|
| 上游版本 | `langgraph` **1.2.11** · `langchain-core` **1.7.6** |
| 版本钉死 | `pyproject.toml:99-101`（`"langgraph==1.2.11"` · `differential` 组） |
| 解释器 | CPython **3.11.16**（`.venv`） |
| 上游包根 | `.venv/lib/python3.11/site-packages/langgraph/` |
| 绿基线 | **1607 passed / 4 skipped / 0 failed**（2026-11-19 · 实施前） |
| 仓库改动 | 本 phase **零源码改动** |

**纪律**（宪法原则 VIII / XI）：

- 每条「上游行为」断言 MUST 带 **版本 + `路径:行号`**；
- **行为**断言 MUST 有**实测**支撑（只读源码不够）；
- `SAME` / `STRICTER` / `DIFF` 三态标注 MUST 与 spec 的偏离登记**逐字一致**；
- 换版本 ⇒ MUST 重新核实全部行号。

---

## 2. 上游对照表（P-01…P-23）

| # | 语义点 | 上游实现（1.2.11 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | 七种 mode 名 | `langgraph/types.py:122-124` | 逐字同名 | SAME | 照抄命名 |
| P-02 | 单 mode 形态 | `langgraph/pregel/main.py:4242-4243` | 四键信封 | DIFF | D11 ⇒ X-1 |
| P-03 | 多 mode 形态 | `langgraph/pregel/main.py:4236-4239` | 同一信封 + `stream_mode` | DIFF | D11 ⇒ X-1 |
| P-04 | `values` 节奏 | `types.py:127` · `_loop.py:699-707` · E-1/E-12 | 初始 + 每完成步一条 | SAME | 只比 payload 投影；信封归 X-1 |
| P-05 | `values` 含中断 | `_loop.py:1443-1451` · E-8 | 收尾含 `__interrupt__` | SAME | 同上 |
| P-06 | `updates` 粒度 / 同通道多写 | `types.py:129-130` · `_loop.py:1452-1459` · `_io.py:118-174` · E-2 | 每完成 task 一条；元组 | DIFF | 仅值形态 ⇒ X-1 子项 |
| P-07 | `tasks` 粒度 / 载荷 | `_loop.py:580`/`:674`/`:1461-1466` · `debug.py:41-70`/`:106-125` · E-3/E-14 | 每完成 task 一条 + `PregelTask` | DIFF | X-3 |
| P-08 | `debug` 包裹 | `_loop.py:1389-1412` · E-4/E-14 | 同形 + `PregelTask`；无 checkpoint | DIFF | X-4 |
| P-09 | `checkpoints` 源 | `_loop.py:631-636` · `debug.py:144` · `_loop.py:1081` · E-5 | v1 空序列；⏳ B15F1 已交付（计划交付消费端）（有 saver + thread 时按本次运行产出） | 能力已由 B15F1 补齐 | B14F1 · B15F1 · D-2 |
| P-10 | `messages` 源 | `types.py:132` · E-6 | v1 空序列；有源时原样透传 | 能力尚未交付 | freechain |
| P-11 | `custom` 载体 | `config.py:126`/`:195-196` · `_executor.py:64`（`copy_context()`）/`:71`（`ctx.run`）/`:164`（async `copy_context()`）· E-7 | contextvar + 每任务 `copy_context()` | SAME | 照抄；⚠️ 仅指载体，产出时机见 P-23 / X-6 |
| P-12 | 无流 writer | `config.py:13-14` · E-9 | no-op | SAME | 照抄 |
| P-13 | 单步 / 整轮 | `_loop.py:599` · `main.py:2964` | L3 主循环反复驱动 L2 单轮入口（公开 `run_super_step` 或私有 `_stream_tick`）；两者共享同一单轮实现 | SAME | 同构（私有助手只是透传 `route_config` / 精确判上限的实现细节） |
| P-14 | `PregelTask` 七字段 | `types.py:637-646` | `contracts/types.py:141` | SAME | 已存在 |
| P-15 | 非法 mode | E-10/E-15（静默空流） | 调用时 `ValueError` | STRICTER | X-2 |
| P-16 | 事件 id | 上游 v1/v2 事件不带 `run_id`/`thread_id`（`main.py:4228`） | 每条带 id | DIFF | D11 ⇒ X-1 |
| P-17 | `RunConfig.run_id` | 上游允许 `RunnableConfig` 传入 | 事件 `run_id` 运行时生成；`RunConfig.run_id` 忽略 | STRICTER | D11 · X-5 |
| P-18 | 中断收尾 | `_loop.py:1441-1451`/`:1461-1466` · E-8/E-14 | values/updates 收尾 + tasks/debug 补发 | SAME | 载荷类型差异归 X-3/X-4 |
| P-19 | 提前停止 / 惰性 | 上游同步惰性生成器 | 同款；零泄漏、不吞异常 | SAME | 与上游一致 |
| P-20 | `StreamWriter` 关键字注入 | `_runnable.py:183-188`（参数名 `writer` · runtime key `stream_writer`）· E-17 | 参数名 `writer` 的关键字注入（FR-036）· 无流 no-op | SAME | 照抄参数名与注解匹配集；`stream_writer` 是 runtime key |
| P-21 | `stream_mode` 默认档 / `None` | `graph/state.py:1357`（默认 `updates`）· `pregel/main.py:2737-2743`（`None` 解析默认档）· E-18 | 签名默认 `None`，解析为 `updates` | SAME | 照抄 |
| P-22 | `stream(Command)` 输入 | 上游接受 `Command` 恢复输入（`pregel/main.py:2655`） | v1 只做全新运行；`Command` ⇒ 首次迭代 `TypeError` | 能力尚未交付 | B14F1 / B15F1 · 不记偏离 |
| P-23 | `custom` 产出时机 | 上游 `stream_writer` 直接 `stream.put(...)`（`pregel/main.py:2841-2849` / `:3280-3287` 的 `SyncQueue`）⇒ 逐写即时 | 每轮 L2 单轮入口结束后按 TaskId 序批量产出 | DIFF | 并发确定性 ⇒ X-6 |

---

## 3. 实测基线索引（E-1…E-18）

| # | 实验 | 关键结果 |
|---|---|---|
| E-1 | 线性图 `values` | 初始 + 2 步 |
| E-2 | 线性图 `updates` | 2 条按 task |
| E-3 | 线性图 `tasks` | 每 task 开始 + 完成（4 条） |
| E-4 | 线性图 `debug` | 4 条 `{step,timestamp,type,payload}` |
| E-5 | 挂 `MemorySaver` `checkpoints` | 3 条 |
| E-6 | 无 LLM `messages` | 0 条 |
| E-7 | `custom` | 1 条原样 |
| E-8 | 中断 `values`/`updates`/`tasks` | 收尾含 `__interrupt__`；task 完成含 `interrupts`；流不抛 |
| E-9 | `invoke` 期间 writer | 可调用 no-op；不抛 |
| E-10 | 非法 mode | 静默空流 / 忽略 |
| E-11 | 多 mode | `(mode, payload)` 元组 |
| E-12 | `values` 第一条 | 输入状态 |
| E-13 | 失败前 `custom` | custom 先出，再抛 |
| E-14 | 中断 `tasks`/`debug` | 补发 task 完成 / 包裹 |
| E-15 | 非法 mode（再次） | 空 / 忽略 |
| E-16 | 多 mode（再次） | 元组序列 |
| E-17 | 节点签名 `def node(state, writer)` / `def node(state, stream_writer)` | `writer` 被注入并产出 custom；`stream_writer` **不被注入** ⇒ `TypeError` |
| E-18 | 不传 `stream_mode` / 显式 `stream_mode=None` | 均按 `updates` 产出；不抛 |

> 完整命令形态与真实输出见 `../research.md` §0 / §2。

---

## 4. 差分场景索引（D-121…D-136 · 16 条）

| # | 场景 | 断言 | 判词 |
|---|---|---|---|
| D-121 | `values` payload 序列（投影信封） | 与上游逐字相等 | SAME |
| D-122 | `values` 最后一条 vs `invoke` | 相等 | SAME |
| D-123 | `updates` 单 task 载荷 | 逐字相等 | SAME |
| D-124 | `custom` 载荷 | 原样出现 | SAME（仅比载荷；时机差异归 X-6） |
| D-125 | `tasks` 条数 / 载荷 | freegraph 单完成 + `PregelTask`；上游双事件 + dict | DIFF（X-3） |
| D-126 | `debug` 载荷 | freegraph `task_result` + `PregelTask`；上游 `task`/`task_result` + dict | DIFF（X-4） |
| D-127 | 多 mode 形态 | 信封 vs 元组 | DIFF（X-1） |
| D-128 | 每条事件 id | 有 vs 无 | DIFF（X-1） |
| D-129 | 非法 mode | `ValueError` vs 空流 | STRICTER（X-2） |
| D-130 | 中断 `values`/`updates` | 含 `__interrupt__`，流不抛 | SAME |
| D-131 | 提前停止 | 两侧零悬挂 / 不吞 | SAME |
| D-132 | 无流 writer | 两侧可调用 / 不抛 | SAME |
| D-133 | 中断 `tasks` | 两侧都为被中断 task 产出一条（name/interrupts 投影一致） | SAME |
| D-134 | `RunConfig(run_id="x")` | freegraph 忽略 `"x"`；上游采用 | STRICTER（X-5） |
| D-135 | 不传 `stream_mode` / `stream_mode=None` | 两侧都按默认 `updates` 产出 | SAME |
| D-136 | 条件边图的 `stream` 路由 | 两侧执行节点序列 / 终态一致 | SAME |

**判词分布**：SAME **10** / DIFF **4** / STRICTER **2**。
**落点**：`tests/differential/parity_probe.py` · 上游缺席即 `skip`。
> `StreamWriter` 关键字注入（P-20 · SAME）由单测 `tests/facade/test_stream_writer_injection.py` 覆盖，
> **不新增差分场景**（载荷形态与 D-124 `custom` 同源；参数名/注解匹配由单测逐字判定）。
**纪律**：判词非 `SAME` 的 6 条 MUST 带非空 `note`（与既有守卫 `test_parity_probe.py` 对齐）。

---

## 5. 偏离登记（X-1…X-6）

| # | 类别 | 被偏离的判据 | 理由 | 承接 / 追认 |
|---|---|---|---|---|
| X-1 | DIFF（自研区 ③） | 事件形态：上游 v1 原始载荷 / 元组；freegraph 四键信封 | D11 要求每条事件带 `run_id`/`thread_id`；L1 返回类别是 `Iterator[dict[str, Any]]` | D11（2026-11-05 已批准） |
| X-2 | STRICTER（失败信号更严） | 非法 mode：上游静默空流；freegraph 调用时 `ValueError` | 「拼错名字无声少跑」与 B7F3 X-2 同类 | 本 feature |
| X-3 | DIFF（形态差异） | `tasks`：上游每 task 双事件 + dict；freegraph 单完成 + `PregelTask` | 提示词 FR-010 冻结；复用 L1 既有类型 | 提示词初稿「下游承接（B7F1 + B10F1）」D-2 · `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §5.3 |
| X-4 | DIFF（形态差异） | `debug`：载荷换 `PregelTask`；v1 无 checkpoint 类 debug | `debug` 以 `tasks` 为唯一 v1 源；checkpoint 源归 B14F1 | 本 feature |
| X-5 | STRICTER（标识纪律） | `run_id`：上游允许 `RunnableConfig` 指定；freegraph 运行时生成，`RunConfig.run_id` 忽略 | D11「用户不可指定 / 不可覆盖」；忽略而非拒绝以保持上游配置可原样传入 | D11 · clarify 轮 A（2026-11-19） |
| X-6 | DIFF（**必须自研区 ②：上游自身的缺陷 / 不确定**） | `custom`：上游逐写即时；freegraph 每轮结束后按 TaskId 序批量 | 上游并发 `custom` 的跨任务顺序依赖完成时刻（不确定）；freegraph 取轮末批量保证确定性；与 P-11 的载体 SAME 分开标注 | 本 feature |

### 5.1 三态一致性（正向：X ⇒ P）

| X | 对应 P |
|---|---|
| X-1 | P-02 / P-03 / P-06 / P-16 |
| X-2 | P-15 |
| X-3 | P-07 |
| X-4 | P-08 |
| X-5 | P-17 |
| X-6 | P-23 |

### 5.2 三态一致性（反向：P 非 SAME ⇒ X）

| P | 关系 | X |
|---|---|---|
| P-02 / P-03 / P-06 / P-16 | DIFF | X-1 |
| P-07 | DIFF | X-3 |
| P-08 | DIFF | X-4 |
| P-15 | STRICTER | X-2 |
| P-17 | STRICTER | X-5 |
| P-23 | DIFF | X-6 |
| P-21 | SAME | — |
| P-09 / P-10 / P-22 | 能力尚未交付 | 不记偏离（Out of Scope） |

---

## 6. 破冻结面（T-1…T-5）

| # | 冻结面 | 回溯修订位置 | 处置 |
|---|---|---|---|
| T-1 | B7F1 `SuperStepResult` 签名 | `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1/§5.3 + `spec.md` + `superstep.py:348-377` | 拆分而不删；追加 `tasks` |
| T-2 | B12F1 裁定 25 ② / FR-013 | `specs/b12f1-concurrency-errors/spec.md` | 只补注记；原描述不改写 |
| T-3 | L1 + L3 `stream` 的 `config` 注解 + `stream_mode` 默认值 | `protocols.py:278-286` + `_stategraph.py:357-365`（concrete 由 T022 落地，T064 只复核）+ B2F1 `public-api.md` / `specs/b2f1-contracts-protocols/data-model.md` §2.5 + **B7F2 `specs/b7f2-compile/contracts/compile-contract.md` §2.4 / `specs/b7f2-compile/data-model.md` §2.3 / `specs/b7f2-compile/plan.md` Phase A / `specs/b7f2-compile/tasks.md` T006（只补注记）** + `README.md`（由 T068 执行） | 拆分而不删；原 `RunConfig \| None` 为子集；显式 `"values"` 仍合法；默认改为 `None ⇒ "updates"`；B7F2 原描述保留 |
| T-4 | B10F1 契约 §3 + `_interrupt.py` docstring | `interrupt-resume-contract.md` §3 + `_interrupt.py:15-27` | 只补注记 |
| T-5 | B2F2 门面 7 + B2F1 契约清单 21 | `facade-api.md` §0 + `public-api-snapshot.txt` + `specs/b2f1-contracts-protocols/contracts/public-api.md` §0 + `tests/contracts/test_architecture.py` G7 解析器 + `README.md`（由 T068 执行）+ 源码模块 docstring（只补计数/注记） | 拆分而不删；追加 8 / 22 |

> 追认次数 == **1**（T-1…T-5 共用）· 落 `harness/verification/B8F2/manual-verification.md`。

---

## 7. 结构面断言清单（换版本时 MUST 重跑）

| # | 断言 | 命令 / 落点 |
|---|---|---|
| S-1 | 七种 mode 名逐字 | `python -c "from langgraph.types import StreamMode; ..."` |
| S-2 | `get_stream_writer()` 存在且返回可调用 | 探针 E-7 / E-9 |
| S-3 | `copy_context()` 在 `_executor.py:64` / `ctx.run` 在 `:71`（async `:164`） | `awk` 锚点 |
| S-4 | `tasks` 的 emit 锚点 `_loop.py:580`/`:674`/`:1461-1466` | `awk` |
| S-5 | `PregelTask` 七字段 | `types.py:637-646` |
| S-6 | `checkpoints` emit 锚点 `_loop.py:631-636` | `awk` |
| S-7 | 非法 mode 静默 | 探针 E-10 / E-15 |

---

## 8. 双份维护的同步义务

- 本文件的 P / X / D 表与 `../spec.md` 的 §Upstream Parity / §偏离登记 / §差分场景组
  MUST **同时**更新；发现漂移 ⇒ **双侧同改**。
- 上游版本变化 ⇒ MUST 重新核实全部行号并改写版本号（宪法原则 XI）。
- 本文件 MUST NOT 被测试解析；测试断言**行为**。
