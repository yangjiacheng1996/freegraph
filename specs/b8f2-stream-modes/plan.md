> **2026-11-20 后续修订（C25 正式作废）**：C25 流式别名软断言已移除；本计划中 alias 文字保留为历史。

# Implementation Plan: B8F2 · `stream()`：多模式流式输出 + `StreamWriter`

**Branch**: `b8f2-stream-modes`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`
⇒ 无 `before_plan` 钩子；既有 feature 同样在 `main` 上开发）
| **Date**: 2026-11-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b8f2-stream-modes/spec.md`

**feature ID**: `B8F2`（M2 图定义与对外 API · **第 19 个** · 前置：**B7F3**（主）+
B7F1 / B10F1 / B8F1 / B12F1 / B13F1 / B1F1 / B2F1 / B2F2 / B7F2 / B6F1（承接 H-1…H-10）
· 下游口径承接：**B8F3 / B18F1 / B19F1**（D-1 / D-3）；**B22F1 / B23F1 与本 feature 互不依赖**（D-4））

---

## Summary

交付 freegraph 的**同步多模式流式输出**：以**惰性迭代器**逐轮产出运行过程事件，
支持 LangGraph 同名的七种 mode（`values` / `updates` / `checkpoints` / `tasks` /
`debug` / `messages` / `custom`），并提供节点侧的 `StreamWriter`（contextvar +
执行器 `copy_context()`）。主循环**反复驱动** L2 单轮入口（`run_super_step` / `_stream_tick`；上游 `while loop.tick()`
同构）；`values` 的完整状态归一**复用** B7F3 的 `_full_state`（L3）；`tasks` 载荷
**复用** L1 既有 `PregelTask`（零新增类型）；`SuperStepResult` **追加** `tasks` 字段
（原 4 字段一个不删）。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **`stream()` 门面** | 七种 mode 的惰性事件迭代器 | L3 `_stategraph.py` · 调用时校验 mode · 四键信封 |
| **L2 私有单轮助手** | `_stream_tick`（`SuperStepResult \| None`） | 与 `run_super_step` 共享 `_run_single_step` / `_run_round` / `_evaluate_*` / `_determine_triggers` · 透传原始 `route_config` · 执行前精确判定递归上限 · 不进 `runtime.__all__` |
| **事件信封** | 每条事件携带运行/会话标识 | `{stream_mode, payload, run_id, thread_id}` · `run_id = uuid4().hex` |
| **`values`** | 初始 + 每完成步的完整状态 | 复用 `_full_state`（L3）· 最后一条 == `invoke` 终态（限定） |
| **`updates`** | 每完成 task 的增量 | `{节点名: {通道: 值 \| 元组}}` · 按通道归约可合并回终态 |
| **`tasks`** | 每完成 task 的 `PregelTask` | `tasks` 事件含被中断 task；`SuperStepResult.tasks` 只累计成功返回的轮次 |
| **`debug`** | `tasks` 的包裹事件 | `{step, timestamp, type:"task_result", payload}` · 1 起 step |
| **`custom`** | 节点主动写入 | `get_stream_writer()` · 参数名 `writer` 的关键字注入 · 每任务 `copy_context()` · 线程安全 + **轮末批量** + TaskId 序（**P-23 / X-6**） |
| **`checkpoints` / `messages`** | v1 空序列 | checkpoint 源归 B14F1 · messages 抽取归 freechain |
| **差分场景组** | 与上游同场景对跑 | D-121…D-136 · SAME 10 / DIFF 4 / STRICTER 2 · 上游缺席即 skip |
| **一键验收** | `harness/verification/B8F2/acceptance.py` | 退出码 0/1/2 · 打印 `B8F2 acceptance: PASS\|FAIL` · pytest 真跑 |

**技术方案（关键落点）**：

| 环节 | 落点 |
|---|---|
| 主循环 | L3 `CompiledGraph.stream`（`src/freegraph/_stategraph.py:357-365` 替换）· 调用 L2 单轮入口 |
| 单轮驱动 | L2 `superstep.py` 私有 `_stream_tick` + `_run_single_step`（`run_super_step` 也走同一 `_run_single_step`）· `route_config` 原样透传 · 执行前判上限 |
| 会话初始化 | L2 私有 `_stream.py`（输入写入 / `bind_run` / contextvar / `run_id` / `thread_id` / 初始稀疏状态） |
| contextvar | L2 私有 `_stream_context.py`（writer / custom sink / round capture / 当前 TaskId / **`_STREAM_RUN_ID` / `_STREAM_THREAD_ID`**） |
| custom 传播 | `_concurrency.py:184-256` 的每任务 `copy_context()` |
| 任务定格 | `superstep.py` 的 `_run_round`（`:1282-1445`）构建 `PregelTask` |
| 结果对象 | `SuperStepResult`（`:348-377`）追加 `tasks: tuple[PregelTask, ...] = ()` |
| 完整状态 | 复用 `_full_state`（`_stategraph.py:235-267`）· L2 只产出稀疏状态 |
| 路由 | 复用 B8F1 的同一份路由求值实现（`_stream_tick` / `run_super_step` 共用）· 双参路由的原始 `config` 逐字透传 |
| `StreamWriter` 公开入口 | 门面 `graph.py` +1（`get_stream_writer`）· L1 `contracts` +1（`StreamWriter`） |
| 关键字注入 | L3 `_stategraph.py` 的 `_wrap_node_action`：在**节点注册/编译**统一包装（`invoke` 与 `stream` 共用）；`inspect.signature` 识别参数名 `writer`（`POSITIONAL_OR_KEYWORD` / `KEYWORD_ONLY`；注解 ∈ `StreamWriter` / `"StreamWriter"` / 空）⇒ 以关键字注入 `get_stream_writer()`；无流为 no-op |

**零新增**：运行时依赖 · 错误类型 · async · 公开 L2 符号（`runtime.__all__` 仍 23）·
门禁编号。**破冻结面 5 类**（T-1…T-5）并入**唯一一次**追认。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`requires-python = ">=3.11"`）；
typing 构件上限 3.11（`contextvars` / `dataclasses` / `uuid` / `inspect` / `collections.abc`）。
**MUST NOT** 使用 3.12+ 的 `TypeAliasType` / `override` / `TypeIs` / PEP 695 `type`。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []`）。
开发期：`pytest`（既有 `dev`）· 差分：`langgraph==1.2.11`（既有 `differential` 组）。
`pyproject.toml` **零改动** ⇒ G3 / G21 / G22 / G23 恒绿。

**Storage**: N/A（v1 流式不做 checkpoint 持久化；B14F1）。
**Testing**: pytest —— `tests/facade/`（`stream` 行为 / 信封 / 七档）·
`tests/runtime/`（`SuperStepResult.tasks` / writer / 并发 / 中断）·
`tests/differential/parity_probe.py`（D-121…D-136）·
`tests/runtime/test_stream_acceptance.py`（验收脚本真跑）。

**Target Platform**: Linux / macOS / Windows · CPython 3.11+ · 零出站。
**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A（不设墙钟预算）** —— 流式每轮 = 一次 L2 单轮入口 +
一次事件组装；无 I/O / 无网络。MUST NOT 用耗时做断言（CI 假红）。

**Constraints**（主要来自 spec 的 MUST 条目）：

| 约束 | spec 条目 |
|---|---|
| 只依赖标准库；MUST NOT import `langchain*` / `langgraph*` / `langsmith` | FR-008 |
| 零出站 / 零环境变量 / 导入无副作用 | FR-008 · SC-005 |
| 七种 mode 名与 LangGraph 逐字一致；默认 `None ⇒ "updates"`，`None` 被接受 | FR-001 / FR-002 |
| 主循环 MUST 反复驱动 L2 单轮入口（公开 `run_super_step` 或私有 `_stream_tick`）；MUST NOT 改两个公开入口签名；MUST NOT 自己求值路由/触发 | FR-009 · SC-014 |
| 轮循环 MUST 复用 `recursion_limit` / `max_steps` 的既有解析口径（`resolve_limit`）；`_stream_tick` MUST 在**执行前**判「触发集非空且已到上限 ⇒ `GraphRecursionError`」（恰好收敛不误抛） | FR-037 · SC-022 · B13F1 承接 |
| `max_concurrency` 由流式会话从 `config`（`RunConfig.max_concurrency` 或普通映射同名字段）解析后传给 L2 单轮入口；`stream()` **不新增**该关键字 | FR-037 · B7F3 D-5 / B12F1 |
| 双参路由 `f(state, config)` 的第二参 MUST 是用户交给 `stream()` 的**原始 `config`**（逐字传入；MUST NOT 传 `None`/翻译） | FR-024 · SC-023 · B8F1 D-1 |
| `values` 归一 MUST 复用 `_full_state`（L3）；L2 只产出稀疏状态 | FR-012 · SC-002 |
| `tasks` 载荷 MUST 是 `PregelTask`；`SuperStepResult` 追加 `tasks`，不删 4 字段 | FR-010 / FR-020 · SC-006 |
| `StreamWriter` MUST 走 contextvar + `copy_context()` | FR-011 / FR-021 |
| 节点签名声明 `writer` 时 MUST 以关键字注入 writer；`**kwargs` / 其它参数名 / 注解不匹配 ⇒ 不注入 | FR-036 · SC-021 |
| `stream` 的 `input` 注解沿用 `StateDict`；运行期允许 `None` = 无输入写入；`Command` / 非法类型在**首次迭代**拒绝；`checkpointer` 被忽略；静态断点在**首次迭代**以 V-26 `ValueError` 拒绝 | FR-023 / FR-028 |
| 每条事件四键 + `run_id` / `thread_id` | FR-013 / FR-027 · SC-010 / SC-011 |
| `run_id` / `thread_id` MUST 绑定 L2 私有 contextvar，供 B18F1 / L2 读取；B19F1 继承 | FR-027 · D-3 · H-9 |
| 非法 mode / 空序列 ⇒ 调用时 `ValueError`；非 `str` / 非 `Sequence` / 非 `None` ⇒ 调用时 `TypeError` | FR-002 · SC-001 |
| 中断：task 补发 + `__interrupt__` + 正常结束 | FR-025 · SC-017 |
| 失败：custom 先出 + 原异常重抛 + 失败轮无 values/updates/tasks/debug | FR-026 · SC-013 |
| `checkpoints` / `messages` 恒空序列且不抛 | FR-017 / FR-018 · SC-008 / SC-009 |
| 公开面 == 门面 8 / 契约 22 / runtime 23；顶层包仍惰性 | FR-030 · SC-018 |
| 差分 D-121…D-136 · 上游缺席即 skip | FR-032 · SC-015 |
| 破冻结面 T-1…T-5 · 追认 == 1 次 | FR-033 · SC-020 |
| 新源文件署名头 + docstring 首语句 | 宪法原则 X · G30 |
| 人工验证五段式 + 追认文字 | 宪法原则 V |

---

## 绿基线记录 + 变红清单（宪法 v1.11.0 的基线义务）

### 基线（**2026-11-19 · 实施前**）

| 项 | 计数 |
|---|---|
| passed | **1607** |
| skipped | **4** |
| failed | **0** |
| 耗时 | **106.58s** |

```
1607 passed, 4 skipped in 106.58s (0:01:46)
```

### 变红清单（**预登记** · 实测后 MUST 逐条核对）

> ⚠️ 本表是**预登记**（依据 = spec 的破面清单 + 已核实的代码锚点 + grep 实测）；
> 实施开始前 MUST 记录真实基线，改动后 MUST 重跑并逐条归因。**MUST NOT** 只凭本表追认。

| # | 断言位置 | 变红原因 | 处置（拆分而不删 / 只补注记） |
|---|---|---|---|
| R-01 | `tests/runtime/test_command_purity.py:236-243` | `SuperStepResult` 字段名恰 4 | 追加 `tasks`；原 4 个名字保留 |
| R-02 | `tests/runtime/test_command_contract.py:565-567` | `len(fields(SuperStepResult)) == 4` | 改为 `== 5`，并点名 `tasks` |
| R-03 | `tests/runtime/test_interrupt_contract.py:29-39,72-95` | `SuperStepResult` / `InterruptResult` 均 4；硬编码 L1 21 符号集 | `SuperStepResult` → 5（`InterruptResult` 仍 4）；L1 集 + `StreamWriter`（22） |
| R-04 | `tests/runtime/test_superstep_concurrency.py:608-616` | 字段名恰 4（SC-019） | 追加 `tasks`；原 4 个名字保留 |
| R-05 | `tests/runtime/test_conditional_edge_surface.py:50,65,70` | 门面 7 / runtime 23 / 契约 21 | 门面 8 / runtime 23 / 契约 22 |
| R-06 | `tests/runtime/test_conditional_edge_surface.py:100` | `stream` 仍抛 `NotImplementedError("B8F2")` | 改为反面断言（真实可流式） |
| R-07 | `tests/runtime/test_channel_contract.py:355-356` | 契约 21 / 门面 7 | 22 / 8 |
| R-08 | `tests/runtime/test_conditional_edge_contract.py:424-426` | 门面 7 / 契约 21 | 8 / 22 |
| R-09 | `tests/runtime/test_read_contract.py:561-562` | `CONTRACT_SYMBOL_COUNT` / `FACADE_SYMBOL_COUNT` | 22 / 8 |
| R-10 | `tests/facade/test_facade.py:306-309` | 门面公开名集合由 `facade-api.md` §0 **动态解析**（当前 7） | **实际动作 = T018 更新 `facade-api.md` §0 至 8**；该测试自动通过。**MUST NOT** 把清单相等改成硬编码 8（会弱化清单驱动判据） |
| R-11 | `tests/facade/test_invoke_full_state.py:212-219` | runtime 23 / 门面 7 | runtime 23 / 门面 8 |
| R-12 | `tests/facade/test_compiled_graph.py:76` | `stream` 期望 `NotImplementedError` | 改为真实流式断言 |
| R-13 | `tests/facade/test_api_snapshot.py` | 快照逐字节相同 | `--update-api-snapshot` 后提交（`get_stream_writer` 行） |
| R-14 | `tests/runtime/test_command_purity.py:287-288` | `contracts` / `facade` 计数 | 22 / 8 |
| R-15 | `tests/runtime/test_superstep_concurrency.py:596` | 门面 7 | 8 |
| R-16 | `tests/contracts/test_architecture.py:389-460,450,1508`（G7 解析器） | 硬编码 21；现有分段实际为 **8 existing + 11 new（含 `Send`）+ 2 aligned**；解析器返回 `(existing, new+aligned)`；`public-api.md` 的「B2F1 新增的 10 个」注释已实际包含 11 个名字（含 `Send`） | 22 · 新增「B8F2 新增的 1 个」分段（`StreamWriter`）⇒ **8 existing + 11 B2F1（含 `Send`）+ 1 B8F2 + 2 aligned**；若并入 `new` 返回段则 `new+aligned` = **12 + 2**；同步解析器 docstring、分段断言与测试名称/注释；**`FR012_NEW_SYMBOLS` 保持 B2F1 的 10 个不变**，`Send` 与 `StreamWriter` 以显式并集加入断言；T016 一并订正 `public-api.md` 的分组注释为「B2F1 / B11F1 新增的 11 个（含 `Send`）」 |
| R-17 | `tests/runtime/test_parse_contract.py:443-444` | 契约 21 / 门面 7 | 22 / 8 |
| R-18 | `tests/facade/test_facade.py:219-235` | `stream` 仍在「未就绪」循环里期望 `NotImplementedError` | 移出循环；改为 `stream` 真实可流式（拆分而不删） |

**MUST NOT 变红**（不破面）：
- `target.py`（只读基准）· `tests/differential/test_differential.py`（B5F2 线性替身）
- `tests/contracts/test_protocols.py:269-271`（`stream` 返回 `Iterator[dict[str, Any]]`）
- `tests/contracts/test_architecture.py` 的 G1 / G2 / G3 等（零依赖 / 顶层惰性）

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith / 零出站 / 零环境变量） | FR-008 · G24 / G26 / G27 / G4 | ✅ |
| 原则 II（零 LangChain · 状态语义等价） | 零新增依赖 · G3 / G21 / G22 / G23 · P-01…P-23 · D-121…D-136 | ✅ |
| 原则 III（验收契约优先 · `target.py` 只读） | `target.py` **零改动**；验收走 `visualization.py` / `graph_core.py` / `acceptance.py` | ✅ |
| 原则 IV（可诊断性 · 可视化不阻断） | D11 的 `run_id` / `thread_id`；惰性 + 零悬挂线程 + 不吞异常 | ✅ |
| 原则 V（人工验收） | 五段式 `manual-verification.md` + 追认 | ✅ |
| 原则 VI（规格驱动 · 判据级覆盖） | spec FR-001…FR-037 / SC-001…SC-023 · 追溯表 · 守卫断言 | ✅ |
| 原则 VII（职责边界 · C12 / C22 / C23） | 流式事件带 id；`stream()` 与 `TraceSink` 独立 | ✅ |
| 原则 VIII（证据与术语） | `research.md` E-1…E-18 实测 + `upstream-parity.md` P/X/D 三表一致 | ✅ |
| 原则 IX（许可证 / 商标） | 零新增依赖 ⇒ `THIRD_PARTY_NOTICES` 零变更 | ✅ |
| 原则 X（署名头 / 文档） | G30 · API 快照 + 兼容矩阵更新 | ✅ |
| 原则 XI（上游优先） | 七种 mode 照抄；偏离只 6 条（X-1…X-6）如实登记；P-11 仅载体 SAME，custom 时机归 P-23/X-6 | ✅ |
| 原则 XII（最优设计 / 零重复载体） | `_full_state` 复用 · `PregelTask` 复用 · writer 单载体 · `_run_single_step` 单轮单实现 · `SuperStepResult` 追加而非另立 | ✅ |
| 立项书 §5.1 **ARCH-3**（跨层只经 Protocol + 纯数据类） | D-3 的 L2 私有运行期 contextvar 读取（B18F1 / L2）⇒ **例外 R-6 已收窄**；B19F1 不直接读取（从节点 span 继承）· 不新增公开符号 · 不改 ARCH-1 方向 | ⚠️ **R-6** |
| 运行时基线（3.11 · typing 上限） | Technical Context 逐项 ≤ 3.11 · G9 | ✅ |
| 依赖白名单 / 黑名单 | 零新增运行时依赖 | ✅ |
| 跨 feature 承接（v1.8.0） | H-1…H-10 消费既有 feature；D-1…D-4 写入目标初稿（R-2） | ⚠️ R-2 |
| 质量门禁 1 / 2 / 6 / 7 | 规格 + tasks + 零新增依赖 + 证据 + 文档 | ✅ |
| 门禁 3 / 4 / 5 | 流式不改变图语义 ⇒ 既有 C4 / C8 回归全绿；`target.py` 仍不可达（PNG 属 B23F1） | ⚠️ **R-5** |
| 发布门禁 | 不接入（B24F1）；新增代码在 `src/` · 零依赖 | ✅ |

### 登记项 R-1（**破冻结面 5 类** · 唯一一次追认 · **T-3 含 B7F2 契约 / 计划 / 任务注记**）

**依据**：宪法 v1.8.0「破冻结面的三条」——① 回溯修订（契约 + spec + 冻结断言，
**拆分而不删**）② 上游对照表写明「上游有 ⇒ freegraph 原先缺」或「上游无 ⇒ 自研区」
③ 发起者追认（落 `harness/verification/B8F2/manual-verification.md`，**未追认前 MUST NOT 合入**）
⇒ 追认次数每 feature **≤ 1 次**。

| # | 冻结面 | 回溯修订位置 | 承接 | 处置 |
|---|---|---|---|---|
| **T-1** | B7F1 `SuperStepResult(state, executed, node_writes, steps)` | ① `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §1 / §5.3 ② `specs/b7f1-superstep-loop/spec.md` 相关 FR / 裁定 ③ `src/freegraph/runtime/superstep.py:348-377` docstring | B8F2（M2） | **拆分而不删**：原 4 字段**逐字保留**；**追加** `tasks: tuple[PregelTask, ...] = ()`（末尾 · 缺省 ⇒ 既有调用方零改动） |
| **T-2** | B12F1 裁定 25 ② / FR-013「四字段零改动」 | `specs/b12f1-concurrency-errors/spec.md` 裁定 25 ② / FR-013 行 | B8F2（M2） | **只补注记**：原描述不改写；追加「自 B8F2 起：追加第 5 字段 `tasks` · 原 4 字段不变」 |
| **T-3** | L1 + L3 `CompiledGraph.stream` 的 `config` 注解 + `stream_mode` 默认值 | ① `src/freegraph/contracts/protocols.py:278-286`（`config` 放宽 + `stream_mode` 默认 `None`⇒`updates`）② `src/freegraph/_stategraph.py:357-365`（concrete stub 同步；**由 T022 落地，T064 只复核**）③ `specs/b2f1-contracts-protocols/contracts/public-api.md` 的 `stream` 行与 `specs/b2f1-contracts-protocols/data-model.md` §2.5 ④ **B7F2** `specs/b7f2-compile/contracts/compile-contract.md` §2.4 + `specs/b7f2-compile/data-model.md` §2.3 + `specs/b7f2-compile/plan.md` Phase A / `specs/b7f2-compile/tasks.md` T006（只补注记）⑤ `README.md` API 矩阵（**由 T068 执行**） | B8F2（M2） | **拆分而不删**：原 `RunConfig \| None` 为**子集**；显式 `"values"` 仍合法；默认改为 `None ⇒ "updates"`；B7F2 原描述不改写、只补注记 |
| **T-4** | B10F1 契约 §3 + `_interrupt.py` docstring | ① `specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md` §3 ② `src/freegraph/runtime/_interrupt.py:15-27` | B8F2（M2） | **只补注记**：原「线程池不继承 contextvars」不改写；追加「自 B8F2 起：每任务 `copy_context()` ⇒ 继承；两级机制照常工作」 |
| **T-5** | B2F2 门面 7 + B2F1 契约清单 21 | ① `specs/b2f2-public-api-facade/contracts/facade-api.md` §0 ② `public-api-snapshot.txt` ③ `specs/b2f1-contracts-protocols/contracts/public-api.md` §0 ④ `tests/contracts/test_architecture.py` 的 G7 解析器（`:389-460` · 21→22 + 新分段）⑤ `README.md` API 矩阵（**由 T068 执行**）⑥ 源码模块 docstring：`contracts/types.py` / `contracts/__init__.py` / `graph.py` / `_stategraph.py`（计数与「未实现」表述只补注记） | B8F2（M2） | **拆分而不删**：原 7 / 21 一个不删；**追加**门面 `get_stream_writer`（7→8）· 契约 `StreamWriter`（21→22） |

**判据未被放宽**：T-1/T-2 只**追加**字段；T-3 只**放宽注解 + 按上游落定默认档 +
给 B7F2 补注记**（原写法仍合法）；T-4 只**补注记**；T-5 只**追加**符号 ⇒ **零条既有判据被删** ⇒
「拆分而不删」在语义留存与判据强度两个维度均只增不减。

**红线**：追认额度用尽后 MUST NOT 再破其它冻结面 · MUST NOT 弱化任何断言 · MUST NOT 改宪法正文 ·
MUST NOT 新增门禁编号 · MUST NOT 放宽依赖 / 许可证 / 商标 / 零出站红线。

### 登记项 R-2（**下游承接 D-1…D-4** 的跨 feature 接线）

| # | 承接方 | 内容 | 目标提示词初稿 |
|---|---|---|---|
| D-1 | B8F3（M2） | 别名在流式事件中的可见性（`updates` 键 = 节点名；不另造映射） | `harness/features/B8F3_节点别名与context通道.md` |
| D-2 | B14F1（M3） | `checkpoints` 档真实数据源（每 checkpoint 一条 · 与 `get_state()` 同形） | `harness/features/B14F1_Checkpointer协议与MemorySaver.md` |
| D-3 | B18F1 / L2（读取）· B19F1（继承）· M3 | 两条事件通道独立、共享 `run_id` / `thread_id`；**载体 = L2 私有 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID` contextvar**（**ARCH-3 例外 · R-6，已收窄**）；B19F1 从节点 span 继承；trace 不塞进信封 | `harness/features/B18F1_Span数据类生产.md` / `B19F1_TraceSink与current_span.md` |
| D-4 | B22F1 / B23F1（M2） | 图导出不依赖流式副作用；流式不调用图导出 | `harness/features/B22F1_get_graph与draw_mermaid.md` / `B23F1_draw_mermaid_png离线不阻断.md` |

**落点**：`tasks.md` 的可勾选接线任务（只接线 · 不越界实现）+ 追认文字并入 R-1 的同一次追认。

### 登记项 R-3（**范围/优先级** · 不属破冻结面）

| # | 项 | 现状 | 处置 |
|---|---|---|---|
| R-3① | `StreamWriter` 关键字注入 | 上游有；2026-11-19 用户决策：本 feature 实现 | **本 feature 交付（待实现）**：参数名 `writer`（上游同款）· 无流 no-op · 关闭 B8F1 DR-4；不新增公开符号 |
| R-3② | 会话连续 / `Command` 恢复 / checkpoint 持久化 | 上游支持；本 feature 只做全新运行 | 归 B14F1 / B15F1 / B16F1；`stream(None)` = 无输入写入（允许）；`stream(Command)` 显式 `TypeError` |
| R-3③ | 规模口径（1,180 行 · 3 人日） | FR-009…FR-012 带来额外工作量 | 以实现期实测为准；修订属发起者职权（与 B8F1 R-5 同款） |

### 登记项 R-4（**Phase 0 的事实性更正** · 已回写 spec）

| # | 原表述 | 事实 | 处置 |
|---|---|---|---|
| C-1 | 上游 `tasks` 载荷 = `PregelTask` | 上游是 `TaskPayload` / `TaskResultPayload` dict · 每 task 双事件 | 已登记 X-3；按提示词 FR-010 冻结 |
| C-2 | 「不迭代也跑完」 | 上游惰性生成器 · 不迭代 = 零执行 | 已收敛为「提前停止不泄漏」 |
| C-3 | D11「`run_id` 不进 `RunConfig`」 | `RunConfig` 现含 `run_id` | 不改字段；事件 id 运行时生成；忽略用户值 |
| C-4 | 只登记 B7F1 破面 | B12F1 也冻结四字段 | 新增 T-2 |
| C-5 | 中断不补发 task | 上游补发 | 已改为补发（D-06） |
| C-6 | 失败丢弃 custom | 上游先产出 | 已改为先 flush（D-07） |
| C-7 | 提示词写 `stream_writer` 关键字注入 | 上游参数名是 `writer`；`stream_writer` 是 runtime key | 已改为参数名 `writer`（D-13 / FR-036） |
| C-8 | 提示词/初版称 `custom` 实时 | 上游逐写即时；freegraph 为并发确定性取 **轮末批量** | 已登记 **P-23 / X-6**（DIFF · 必须自研区 ②） |

### 登记项 R-5（**门禁 3/4/5 的物理不可达部分** · 宪法 v1.6.0）

| # | 被偏离的门禁项 | 不可达成根因 | 判据未放宽的论证 | 承接方 | 承接机制 |
|---|---|---|---|---|---|
| R-5 | 门禁 3 的「`harness/demo/target.py` 原样可跑」· 门禁 4 的「验收基线 fake 轮」· 门禁 5 的「真实模型轮」 | `target.py` 在 `:163` 先调 `draw_mermaid_png()`（属 B23F1），在 `:168` 才 `invoke()` ⇒ 本 feature 在到达验收点前中断；真实模型轮需厂商端点 + 凭据，本环境不具备 | 固定脚本**零改动**；本 feature 以 `visualization.py` / `graph_core.py` / `acceptance.py` 承担**可改**的图能力侧证据；门禁 3 的 C4/C8 回归全绿；**判据一字未改** | B22F1 + B23F1（M2）· B25F1（M4） | 下游接线 D-4；追认文字并入 `harness/verification/B8F2/manual-verification.md` 的同一次追认 |

> ⚠️ R-5 与 B8F1 的 R-2 同源；B8F2 **不重复定义** B8F1 的偏离，只登记本 feature 的不可达部分。
> 红线：MUST NOT 写永久红 CI；MUST NOT 把 R-5 当长期豁免；MUST NOT 放宽任何能力型判据。

### 登记项 R-6（**ARCH-3 例外** · 2026-11-20 发起者授权）

| # | 被登记项 | 现状 | 判据未放宽的论证 | 承接方 |
|---|---|---|---|---|
| R-6 | `立项书 §5.1` **ARCH-3**「跨层只经由 `Protocol` + 纯数据类」 | D-3 / H-9 让 B18F1 / L2 读取 L2 私有 contextvar `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`；B19F1 从节点 span 继承，不直接读取 | 载荷 = `str \| None` **运行期元数据**，不是新的公开契约载体；**不新增公开符号**（`runtime.__all__` 仍 23）· **不改变** ARCH-1 导入方向（L5 → L2 合法）· 若未来升级为公开 API ⇒ MUST 另走契约修订（`Protocol` + 纯数据类） | B8F2（登记）· B18F1 / L2（读取）· B19F1（继承） |

> 红线：该例外**只覆盖**运行期标识的私有 contextvar 读取；MUST NOT 被扩展为「任意 L5 → L2 私有模块依赖」的通行证。

### 门禁编号纪律

- **零新增门禁编号**（G1–G30 的连续性是不变量）；
- 本 feature 只**复用**既有门禁：G1 / G2 / G3 / G4 / G7 / G8 / G9 / G14 / G15 / G17 / G18 /
  G19 / G21 / G22 / G23 / G24 / G26 / G27 / G30；
- 新增的源文件 MUST 带署名头（G30）且模块 docstring 是首个语句。

### 设计后复核（Phase 1 后）

| 项 | 复核结果 |
|---|---|
| ARCH-1：L2 只依赖 L1 | ✅ `_stream.py` / `_stream_context.py` 只依赖标准库 + L1 + 同层 `superstep`（私有） |
| 反向依赖：L2 → L3 | ✅ 零（`_full_state` 只在 L3 使用） |
| **ARCH-3：跨层只经 Protocol + 纯数据类** | ⚠️ **例外 R-6（已收窄）**：B18F1 / L2 读取 L2 私有运行期 contextvar（`str \| None` 元数据）；B19F1 从节点 span 继承，**不直接读取**；不新增公开符号、不改 ARCH-1 方向 |
| 公开面 | ✅ 门面 8 / 契约 22 / runtime 23 / 顶层 `__all__` 仍 `["__version__"]` |
| 零重复载体 | ✅ `_full_state` / `PregelTask` / `StreamWriter` 各一个实现点；`_run_single_step` / `_run_round` 由 `run_super_step` 与 `_stream_tick` **共用**；`run_id` / `thread_id` 只经 L2 contextvar 传递 |
| 偏离登记 | ✅ X-1…X-6 全部登记；X-6（custom 轮末批量）不消耗追认额度 |
| 破冻结面 | ✅ T-1…T-5 全部登记 + 回溯修订 + 同一次追认；**T-3 已含 B7F2 compile-contract/data-model/plan/tasks 注记** |
| 差分组 | ✅ D-121…D-136 判词分布与 spec 一致（SAME 10 / DIFF 4 / STRICTER 2）；D-124 仅比载荷，时机归 X-6 |

---

## Project Structure

### Documentation (this feature)

```text
specs/b8f2-stream-modes/
├── plan.md                          # 本文件
├── research.md                      # Phase 0 —— 实测 + 决策 + 遗留 DR-1…DR-9
├── data-model.md                    # Phase 1 —— 实体 + 状态机 + 校验 + 不变量
├── quickstart.md                    # Phase 1 —— 验证手册 V1…V21
├── contracts/
│   ├── stream-contract.md           # Phase 1 —— 流式契约（**唯一权威**）
│   └── upstream-parity.md           # Phase 1 —— P-01…P-23 + D-121…D-136 + X-1…X-6
├── spec.md                          # 规格（37 FR · 23 SC · 10 裁定 · 3 clarify 问答）
├── checklists/
│   └── requirements.md              # 规格质量清单（35/35）
└── tasks.md                         # Phase 2（/speckit.tasks —— 已生成）
```

### Phase 1 产物状态

| 工件 | 状态 |
|---|---|
| `research.md` | ✅ 已产出（D-01…D-15 · E-1…E-18 · DR-1…DR-9 · C-1…C-8） |
| `data-model.md` | ✅ 已产出（实体 · 状态机 · VS-1…VS-11 · IS-1…IS-25） |
| `contracts/stream-contract.md` | ✅ 已产出（签名 · 七档 · 信封 · 生命周期 · 破面） |
| `contracts/upstream-parity.md` | ✅ 已产出（P / E / D / X / T · 三态一致） |
| `quickstart.md` | ✅ 已产出（V1…V21） |

### Source Code (repository root)

```text
src/freegraph/
├── __init__.py                      # 既有 · 零改动（顶层惰性 · G1）
├── graph.py                         # ★ 改 —— 门面 7 → 8（加 get_stream_writer）
├── _stategraph.py                   # ★ 改 —— 实现 CompiledGraph.stream（L3 主循环）
├── contracts/
│   ├── types.py                     # ★ 改 —— 新增 StreamWriter 类型别名
│   └── __init__.py                  # ★ 改 —— 导出 StreamWriter（21 → 22）
└── runtime/
    ├── __init__.py                  # 既有 · 零改动（导出面仍 23）
    ├── _concurrency.py              # ★ 改 —— 每任务 copy_context()
    ├── _interrupt.py                # ★ 只改 docstring（T-4 注记）
    ├── superstep.py                 # ★ 改 —— SuperStepResult.tasks + PregelTask 快照 + 中断 capture + 私有 `_run_single_step` / `_stream_tick`
    ├── _stream_context.py           # ★ 新增（L2 私有）—— contextvars / writer / sink / capture / run_id / thread_id
    └── _stream.py                   # ★ 新增（L2 私有）—— StreamSession 初始化（含 run_id / thread_id 绑定）

tests/
├── facade/
│   ├── test_stream_modes.py         # ★ 新增 —— 七档 / 信封 / id / 多 mode
│   ├── test_stream_lifecycle.py     # ★ 新增 —— 惰性 / 提前停止 / 中断 / 失败
│   ├── test_compiled_graph.py       # ★ 改 —— stream 由 NotImplemented → 真实断言
│   ├── test_api_snapshot.py         # ★ 改（快照更新）
│   └── test_stream_writer_injection.py # ★ 新增 —— 参数名 writer 的关键字注入
├── runtime/
│   ├── test_stream_writer.py        # ★ 新增 —— writer / 并发 / 顺序 / no-op
│   ├── test_superstep_tasks.py      # ★ 新增 —— SuperStepResult.tasks / PregelTask
│   ├── test_command_purity.py       # ★ 改 —— 字段数 4 → 5
│   ├── test_command_contract.py     # ★ 改 —— 字段数 4 → 5
│   ├── test_interrupt_contract.py   # ★ 改 —— SuperStepResult 5 / InterruptResult 4
│   ├── test_superstep_concurrency.py# ★ 改 —— 字段名 / 门面计数
│   ├── test_conditional_edge_surface.py # ★ 改 —— 门面 8 / runtime 23 / 契约 22 / stream 已交付
│   ├── test_channel_contract.py     # ★ 改 —— 契约 22 / 门面 8
│   ├── test_conditional_edge_contract.py # ★ 改 —— 门面 8 / 契约 22
│   ├── test_read_contract.py        # ★ 改 —— 计数 22 / 8
│   ├── test_stream_acceptance.py    # ★ 新增 —— 真跑 B8F2 acceptance.py
│   └── test_stream_manual_record_guard.py # ★ 新增 —— 文档守卫（SC-020 / T-1…T-5）
├── differential/
│   └── parity_probe.py              # ★ 改 —— D-121…D-136（16 条）
└── contracts/
    └── test_architecture.py         # ★ 改 —— G7 解析器 21 → 22 + 新分段

harness/
├── demo/
│   ├── visualization.py             # ★ 改 —— case_stream_modes 期望转绿
│   └── graph_core.py                # ★ 改 —— C25 流式别名软断言已移除
└── verification/B8F2/
    ├── acceptance.py                # ★ 新增 —— 一键验收（0/1/2）
    └── manual-verification.md       # ★ 新增 —— 五段式 + 追认

README.md                            # ★ 改 —— API 矩阵 + stream 行为说明

specs/                               # ★ 回溯修订（T-1…T-5）
├── b7f1-superstep-loop/             # 契约 §1/§5.3 + spec
├── b12f1-concurrency-errors/        # 裁定 25 ② / FR-013 注记
├── b10f1-interrupt-resume/          # 契约 §3 + docstring 注记
├── b7f2-compile/                    # compile-contract.md §2.4 + data-model.md §2.3 + plan.md Phase A + tasks.md T006 注记（T-3 扩展）
├── b2f1-contracts-protocols/        # public-api.md §0 清单（+StreamWriter）· stream 行
└── b2f2-public-api-facade/          # facade-api.md + public-api-snapshot.txt

harness/features/                    # ★ 下游接线（R-2）
├── B8F3_节点别名与context通道.md
├── B14F1_Checkpointer协议与MemorySaver.md
├── B18F1_Span数据类生产.md
├── B19F1_TraceSink与current_span.md
├── B22F1_get_graph与draw_mermaid.md
└── B23F1_draw_mermaid_png离线不阻断.md
```

**Structure Decision**：

- **L3 持有主循环**：与上游 `while loop.tick()` 同构；`values` 归一必须复用
  `_full_state`（L3 私有）⇒ 主循环在 L3 才能做到「单一实现点」。
- **L2 私有 `_stream.py` + `_stream_context.py`**：会话初始化（输入写入 / `bind_run` /
  contextvar）属 L2 语义；拆成两个私有模块以避免 `superstep.py ↔ _stream.py` 循环 import：
  `_stream_context.py` 只依赖标准库 + L1；`superstep.py` 只 import 它；`_stream.py`
  import `superstep` 的私有初始化助手。
- **L2 私有 `_stream_tick` / `_run_single_step` 落 `superstep.py`**：`_run_single_step`
  是 `run_super_step` 与 `_stream_tick` 的**唯一单轮实现点**（验证 / 触发 / 路由 /
  `_run_round` / 结果构造）；`run_super_step` 不传 `route_config`、不判上限；
  `_stream_tick` 传原始 `route_config` 并在执行前判上限 ⇒ 既不改公开签名，也不复制路由/触发。
- **`copy_context()` 落 `_concurrency.py`**：每任务 `ctx = copy_context()` +
  `executor.submit(ctx.run, _worker, ...)` ⇒ 与上游 `_executor.py:64`/`:71` 同款；
  不改变 `_TaskOutcome` 五字段 / 并发度 / 失败顺序。
- **`PregelTask` 快照落 `_run_round`**：任务 id / 目标 / 结果 / 中断在阶段 ③′ / ⑥ 都已就绪；
  在阶段 ⑥ 之前构建 `tuple[PregelTask, ...]` ⇒ 成功轮进 `SuperStepResult.tasks`；
  中断轮进 `RoundCapture`（contextvar）⇒ 不新增 `SchedulerState` 字段。
- **差分落 `parity_probe.py`**：沿用 B5F2 的「双真实实现」体系；不重造夹具。

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**本 feature 零违反**。全部语义照抄上游（原则 XI）；形态差异只 6 条（X-1…X-6），
已如实登记。本表只列**登记项**（登记项 ≠ 违反）：

| 登记项 | 依据 | 被偏离的具体项 | 根因 | 判据未放宽的论证 | 承接方 | 承接机制 | 落点 |
|---|---|---|---|---|---|---|---|
| **R-1** | v1.8.0 破冻结面三条 | T-1…T-5 | 流式需要 `tasks` 字段 + `config` 注解 + contextvar 继承 + 公开面 2 符号 + **B7F2 concrete `stream` 签名** | 只追加 / 只补注记 / 原写法仍合法 ⇒ 零删除 | B8F2（M2） | 回溯修订 + 唯一一次追认 | `tasks.md` 追认任务 + `manual-verification.md` |
| **R-2** | v1.8.0 跨 feature 接线 | D-1…D-4 | 流式事件 / checkpoint / trace / 图导出的口径交接 | 只接线 · 不越界 · 零新增门禁编号 | B8F3 / B14F1 / B18F1 / B19F1 / B22F1 / B23F1 | 写入目标初稿 + 可勾选任务 | `tasks.md` 接线任务 |
| **R-3** | v1.6.0 分阶段 / 原则 VIII | 关键字注入（已交付）/ 会话恢复 / 规模 | 提示词边界 | 关键字注入已交付；会话恢复显式 Out of Scope；规模不单方面修改；判据未放宽 | B14F1 / 发起者（规模） | 注记 + 承接 | `spec.md` Out of Scope / Assumptions |
| **R-4** | 原则 VIII | C-1…C-8 事实更正 | Phase 0 实测 | 已回写 spec；判据只收紧 | B8F2（M2） | 文档更正 | `research.md` §3 + `spec.md` 引文差异 |
| **R-5** | v1.6.0 门禁分阶段 | 门禁 3/4/5 的 target.py / fake 轮 / 真实模型轮 | PNG 属 B23F1；真实模型环境不具备 | 固定脚本零改动；图能力侧证据照常；判据未放宽 | B22F1 + B23F1 · B25F1 | 下游接线 + 追认 | `manual-verification.md` · `tasks.md` T061 |
| **R-6** | 立项书 §5.1 ARCH-3 | B18F1 / L2 读取 L2 私有运行期 contextvar；B19F1 从节点 span 继承，**不直接读取** | 标识需跨事件/span 对齐，且不得新增公开符号 | 载荷 = `str \| None` 运行期元数据；不改 ARCH-1 方向；未来升级公开 API 须另走契约修订 | B8F2（登记）· B18F1 / L2（读取）· B19F1（继承） | 登记例外 + 下游接线 | `spec.md` D-3 注 · `tasks.md` T067 |

> **X-6**（`custom` 产出时机 DIFF）已按原则 XI 的**必须自研区 ②（上游自身的不确定）**
> 登记于 `spec.md` §4；它**不属破冻结面**、**不消耗** T-1…T-5 的唯一追认额度；
> 实现口径固定为「轮末批量 + TaskId 序」。

---

## ⚠️ 本 plan 阶段的「零源码改动」声明

> 本 phase（含 2026-11-20 分析修复轮）**未改动任何 `src/` / `tests/` 源码**；只修改 `specs/`
> 下的文档（`spec.md` / `plan.md` / `tasks.md` / `data-model.md` / `contracts/` / `quickstart.md`）
> ⇒ 绿基线 **1607 passed** 已记录；变红清单是
> **预登记**（grep + spec 破面推导）⇒ **MUST NOT** 凭它追认。
> 实施开始前 MUST 重跑基线；改动后 MUST 重跑并按 R-01…R-18 逐条归因。
