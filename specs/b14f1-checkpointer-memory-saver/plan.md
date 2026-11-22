# Implementation Plan: B14F1 · Checkpointer 协议 + `MemorySaver`（快照 + pending writes 双层持久化）

**Branch**: `b14f1-checkpointer-memory-saver`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_plan` 钩子；既有 feature 同样在 `main` 上开发）

**Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/b14f1-checkpointer-memory-saver/spec.md`（**唯一权威** · 含 **5** 条澄清轮拍板 + **13** 条形态锁定裁定 + **35** 条 FR + **25** 条 SC）

**Feature ID**: `B14F1`（M3 可诊断 · **第 26 个** · 前置：**B7F3**；承接 **B10F1 / B12F1 / B11F1 / B13F1 / B7F4 / B7F2 / B8F2 / B8F3 / B18F1 / B7F3 / B1F1 / B2F1**）

> **范围提醒**：本 feature 是 **L4 持久化层**的第一段，交付 **L1 `Checkpointer` 协议的完整实现**（`MemorySaver`）+ **运行期每轮落盘接线** + **读侧最小契约**（`CheckpointTuple`）+ **编译期 checkpointer 校验** + **节点 span 的 `checkpoint_id` 接缝** + **`checkpoints` 事件数据源**。
> **不交付** `SqliteSaver` / `get_state` / `get_state_history`（B15F1）· `update_state` / 时间旅行（B16F1）· `Store`（B17 已砍）· Postgres / 跨进程共享（v2）· `stream(checkpoints)` 消费端接线（B8F2 / B15F1）。
> `StateSnapshot` 8 字段、`Checkpointer` 8 方法、`RunConfig` 9 字段、`Span` 11 字段、`freegraph.graph` 门面符号面、**L1 符号面**、`runtime.__all__`、`superstep.__all__` **一律不改**。

---

## Summary

交付 **`freegraph.persistence.MemorySaver`**：按 `thread_id` 分区的**快照**与 **pending writes** 双层内存存储，满足 L1 `Checkpointer` 的 **8** 个方法；提供 `CheckpointTuple`（`.snapshot` / `.pending_writes` / `.scheduler`）作为读侧载体。

交付 **运行期每轮落盘**：空会话先写**惰性初始快照**；每个**实际执行过**的 super-step 结束后写一条**每轮快照**（`tasks` = 本轮 `PregelTask`）；动态中断 / 静态挂起用**挂起写**计入该轮（**挂起快照 `tasks` 恒为 `()`** · 与 B10F1 冻结挂起写一致）；`interrupt_after` 的挂起写**代替**该轮每轮快照；`static_resume` 的完成快照由 **B13F1 的 F-10 写一次**（本 feature 不重复）；收敛空轮**不写**。

交付 **关键接缝**：

| 接缝 | 落法 |
|---|---|
| **真异常 + 中断同现** | 先把该轮每个中断经 `put_writes(round_start_config, writes=[("__interrupt__", (payload,))], task_id=..., task_path=...)` 留痕（显式 round-start checkpoint id），再**原样**抛出真异常；不改变异常类型 / 消息 / identity；不**为中断留痕**新增附注 / 调度字段（B12F1 的 `attach_failure_notes` 保留） |
| **节点 span 的 `checkpoint_id`** | 通过 `start_node_span(..., checkpoint_id=...)` 的**既有参数**填值；`Span` 11 字段零改动；无 checkpointer ⇒ `None` |
| **`checkpoints` 事件数据源** | `MemorySaver(*, on_checkpoint=...)`：每次成功 `put` 恰调用一次；`list()` 提供历史枚举；**不**接线 `stream()`（消费端归 B8F2 / B15F1） |
| **编译期校验** | `compile(checkpointer=...)`：`None` / `True` / `False` / 满足 L1 `Checkpointer` 协议的对象 ⇒ 接受；其它 ⇒ `TypeError`；`CompiledGraph.checkpointer` 记录方式零改动 |
| **`context` 不持久化** | `snapshot.config.context is None`；不写入 `metadata` / `configurable`；恢复时不从快照还原 |

**技术路线**（零第三方依赖 · 零出站 · 零环境变量）：

| 环节 | 落点 |
|---|---|
| L4 公开包 | **新增** `src/freegraph/persistence/{__init__.py,_types.py,memory.py}`（只 import L1 + 标准库） |
| 读侧载体 | `_types.py` 的 `CheckpointTuple`（`frozen=True, slots=True` · 恰好 3 字段） |
| 内存实现 | `memory.py` 的 `MemorySaver` + `InMemorySaver` 别名；每实例 `threading.RLock`；`copy.deepcopy` 防御性拷贝 |
| 运行期接缝 | **新增** L2 私有 `src/freegraph/runtime/_checkpoint.py`（归一化 / 写快照 / 写错误轮中断 / checkpoint id 提取）；**修改** `runtime/superstep.py` 的 `run_graph` / `_first_graph` / `_resume_graph` / `_run_graph_loop` / `_run_round` |
| span 接缝 | `runtime/_span_hook.start_node_span` 的既有 `checkpoint_id` 参数；`_run_round` 增 **keyword-only** 私有参数 `checkpoint_id=None` |
| 编译期校验 | **修改** `src/freegraph/_stategraph.py`：私有 `_validate_checkpointer()` + `compile()` 入口调用 |
| 测试 | 新增 `tests/persistence/` + `tests/runtime/test_b14f1_*.py` + `tests/facade/test_b14f1_*.py` + `tests/differential/test_b14f1_checkpoint_parity.py` + 文档守卫 |
| 验收脚本 | **修改** `harness/demo/graph_core.py`（真实 `MemorySaver` + `soft→check`）· `harness/demo/README.md`（移除待锁定条目）· **新增** `harness/verification/B14F1/manual-verification.md`（可选 `acceptance.py`） |
| 文档联动 | `README.md` 的 `Checkpointer` 行移除「挂起 B14F1」并写明已落地；**不新增**兼容矩阵行（矩阵只覆盖 L1 + 门面；B24F1 / B25F1 定稿） |

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（本机 `.venv` 3.11.16）；只用标准库
`copy` / `threading` / `datetime` / `collections.abc` / `contextvars` / `dataclasses` / `typing`。
**MUST NOT** 使用 3.12+ 的 `override` / `TypeIs` / PEP 695。

**Primary Dependencies**: **零第三方运行时依赖**（`dependencies = []`）。
开发期 `pytest` 既有；差分测试侧仅钉 `langgraph==1.2.11`（`.venv` 已装）；
`pyproject.toml` **零改动** ⇒ G3 / G21 / G22 / G23 恒绿。

**Storage**: **进程内内存**（`MemorySaver`）· 按 `thread_id` 分区 · 无文件 / 网络 / 数据库。
持久化后端（SQLite）属 **B15F1**；跨进程共享属 **v2**。

**Testing**: pytest ——
`tests/persistence/test_memory_saver.py`（协议 / 快照 / 写入 / 列表 / 删除 / 版本 / 隔离 /
深拷贝 / 并发 / 失败信号 / 别名）·
`tests/runtime/test_b14f1_step_snapshots.py`（初始 / 每轮 / 计数 / 无 checkpointer / 无 thread_id）·
`tests/runtime/test_b14f1_resume.py`（动态 / 静态 / F-10 不重复）·
`tests/runtime/test_b14f1_fanout_barrier.py`（fan-out task_id / 屏障 seen）·
`tests/runtime/test_b14f1_error_interrupts.py`（真异常 + 中断留痕）·
`tests/runtime/test_b14f1_spans.py`（节点 span 的 `checkpoint_id`）·
`tests/runtime/test_b14f1_manual_record_guard.py`（SC-022 文档守卫）·
`tests/facade/test_b14f1_compile_validation.py`（编译期 `TypeError`）·
`tests/contracts/test_b14f1_contracts.py`（L4 导出 / 依赖方向 / 零 env / 零出站 / L1 零改动）·
`tests/differential/test_b14f1_checkpoint_parity.py`（D-01…D-15 · 上游缺席即 skip）。

**Target Platform**: Linux / macOS / Windows · CPython 3.11+ · 零出站。
`threading.RLock` / `datetime.now(timezone.utc)` / `copy.deepcopy` 跨平台一致。

**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A（不设墙钟预算）**。内存 saver 的 `put` / `get_tuple` / `delete_thread`
为 `O(1)` 字典操作；`list` 为 `O(N log N)`（排序）· `N` = 该线程快照数。
**MUST NOT** 用耗时做断言（CI 假红）。

**Constraints**（主要来自 spec）：

| 约束 | spec 条目 |
|---|---|
| L4 `persistence` 只 import L1 + 标准库；零第三方 / 零 env / 零出站 | FR-008 · FR-032 · SC-024 |
| `MemorySaver` 结构化满足 `Checkpointer` **8 方法**；`InMemorySaver` 同对象别名 | FR-001 · SC-006 |
| 快照 + pending writes **分层**；写侧关键字逐字；`put_writes` 目标由 `configurable["checkpoint_id"]` 指定（缺 key ⇒ `KeyError`） | FR-002 / FR-003 / FR-013 · SC-001 / SC-002 |
| pending writes 去重 / 排序逐字上游（`WRITES_IDX_MAP` + `writes_sort_key`）；`list(None)` 线程插入序 | FR-003 / FR-014 / FR-016 · SC-002 / SC-009 / SC-010 |
| 按 `thread_id` 隔离；防御性深拷贝；每实例锁 | FR-004 / FR-017 / FR-030 · SC-003 |
| checkpoint 顺位 id 每线程单调；`get_next_version` 返回 `int+1`；不改写调度版本 | FR-005 · SC-004 · 裁定 4 |
| `get_tuple` / `list` / `delete_thread` 语义 | FR-006 / FR-011 / FR-015 / FR-016 · SC-007 / SC-010 / SC-011 |
| 编译期校验；运行期只归一 `None` / `True` / `False` / `thread_id`（**不判 `isinstance`**） | FR-007 / FR-010 / FR-018 · SC-013 |
| 无 `thread_id` ⇒ 运行期跳过落盘；直接调用 saver ⇒ `ValueError` | FR-018 · SC-005 / SC-014 |
| 静态挂起 / fan-out / 屏障原样存取；F-10 不重复 | FR-019 / FR-020 · SC-015 / SC-016 / SC-017 |
| 真异常 + 中断留痕；异常 identity 不变 | FR-021 · SC-018 |
| 节点 span 的 `checkpoint_id`；`Span` 11 字段不改 | FR-022 · SC-019 |
| `on_checkpoint` + `list()` 数据源；不伪造 stream 事件 | FR-023 · SC-020 |
| `context` 不持久化 | FR-024 · SC-021 |
| 人工验证 + demo 硬断言 | FR-026 / FR-027 · SC-022 / SC-023 |
| 证据锚点 + 差分 D-01…D-15 | FR-033 / FR-035 · SC-025 |

> **无未决澄清**：spec 的 clarify 轮 5 条拍板 + 13 条形态锁定裁定已收敛全部未决点；
> 本 plan 只落设计决策与实现顺序。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| **原则 I · 零 LangSmith** | 零新增依赖；无 env / 网络 / 出站；G24 / G26 / G27 | ✅ 通过 |
| **原则 II · 内核纯净** | 不 import `langchain*` / `langgraph*` / `langsmith`；L4 只 import L1 + stdlib | ✅ 通过 |
| **原则 III · 验收契约优先** | `harness/demo/target.py` **零改动**；门面 8 符号面零改动；C4 / C6 / C8 回归保持 | ✅ 通过 |
| **原则 IV · 可诊断性** | `checkpoint_id` 进节点 span；`on_checkpoint` / `list()` 数据源；恢复必须挂 checkpointer；无内存态旁路（FR-028） | ✅ 通过 |
| **原则 V · 人工验收** | `harness/verification/B14F1/manual-verification.md` 含**恢复侧真跑一轮**（B10F1 的 V-1 承接）；五段式记录 | ✅ 计划交付 |
| **原则 VI · 规格驱动** | spec FR-001…FR-035 / SC-001…SC-025 全部可追溯；tasks 由 `/speckit.tasks` 展开 | ✅ 通过 |
| **原则 VII · 职责边界** | 只做 C19 的内存实现 + 运行期接缝；不实现 `Store` / `SqliteSaver` / 时间旅行 | ✅ 通过 |
| **原则 VIII · 证据与术语** | spec 的 P-01…P-21 / D-01…D-15 / X-01…X-08 带 `langgraph 1.2.11` + `路径:行号`；术语「快照 / pending writes / 调度账本 / 顺位 id」统一 | ✅ 通过 |
| **原则 IX · 许可证 / 商标** | 零新增第三方代码 ⇒ `THIRD_PARTY_NOTICES` 零变更 | ✅ 通过 |
| **原则 X · 文档 / 署名头** | 新增 L4 / L2 文件带署名头；`harness/demo/README.md` 更新；`README.md` 的 `Checkpointer` 行更新（不新增矩阵行） | ✅ 计划交付 |
| **原则 XI · 上游优先** | 21 条语义点逐条对照；仅 X-01…X-08 分叉并登记；差分 D-01…D-15 | ✅ 通过（含已登记偏离） |
| **原则 XII · 最优设计优先** | 快照与写入**分层**；调度账本**一等**（`.scheduler`，不借位 `metadata`）；`CheckpointTuple` 恰好 3 字段 | ✅ 通过 |

### 登记项（**plan 阶段必须如实登记**）

| # | 类别 | 内容 | 处置 | 追认 |
|---|---|---|---|---|
| **R-1** | **消解已登记的偏离（B7F2 X-4）** | B7F2 的差分 D-77 与 `tests/facade/test_compile_validation.py::test_nv5`、`tests/facade/test_compiled_graph.py::test_non_store_objects_are_accepted` 都断言「非 saver 对象被接受」⇒ 本 feature 的编译期校验落地后**必红** | **拆分而不删**：① `test_nv5` 拆为「非法 checkpointer ⇒ `TypeError`」+「非法 store ⇒ 仍接受 + 1 warning」；② `test_non_store_objects_are_accepted` 拆为「非法 checkpointer ⇒ `TypeError`」+「非法 store ⇒ 接受」；③ `parity_probe.py` 的 D-77 判词由 `DIFF` 改为 **`SAME`**（两侧都 `TypeError`） | **不需要**（消解 B7F2 的 X-4 · 不改门禁判据） |
| **R-2** | **消解 B10F1 的冻结断言** | `tests/runtime/test_interrupt_checkpoint.py::test_the_runtime_never_imports_a_saver_implementation` 断言 `src/freegraph/**` 内**零** `class MemorySaver` / `SqliteSaver` ⇒ 本 feature 落地后**必红** | **拆分而不删**：① 保留「`src/freegraph/runtime/**` 内**零** saver 实现」；② 改为「`src/freegraph/persistence/memory.py` 有 `MemorySaver`，但 `runtime/**` **不 import** `freegraph.persistence`」；③ 同步该测试的 docstring（B10F1 的 FR-019 仍成立：B10F1 未越界实现 saver） | **不需要**（不是门禁偏离 · 不是 L1 冻结面） |
| **R-3** | **B10F1 V-1 的人工验证承接** | B10F1 在 M1 物理不可达成「恢复侧真跑一轮」 | `harness/verification/B14F1/manual-verification.md` MUST 含真实 `MemorySaver` 的「`interrupt` → `Command(resume=…)` → 跑完」实测输出；旧记录不作废，追加「恢复侧实测」段 | **不需要**（由本 feature 补齐） |
| **R-4** | **B8F2 D-2 的数据源边界** | B8F2 的 `checkpoints` 档 v1 恒空；本 feature 只交付 `on_checkpoint` + `list()` 数据源，**不**重写 `StreamSession` | 在 plan / research / contracts 写明「消费端接线归 B8F2 / B15F1」；`stream(checkpoints)` 的伪造事件数 == 0；**不**把「stream 已支持 checkpoint」写进任何文档 | **不需要**（能力边界 · 非偏离） |
| **R-5** | **README / demo 的过期文本** | `README.md:167` 写「checkpointer 的行为归 B14F1（本阶段只接受并记录，编译期不做类型校验）」；`harness/demo/README.md` 的待锁定清单仍列 `MemorySaver` 模块路径；`tests/facade/test_compiled_graph.py::test_readme_states_store_and_checkpointer_boundaries` 依赖旧文本 | **更新文本 + 同步测试**：README 改为「已由 B14F1 的 `MemorySaver` 落地；编译期校验已交付」；demo README 移除待锁定条目；测试断言同步为**新文本**（**不是**放宽）。⚠️ `MemorySaver` / `InMemorySaver` / `CheckpointTuple` 的 **3 行**兼容矩阵按 spec **D-07** 由 **B24F1 / B25F1** 增加；B14F1 只更新 `Checkpointer` 行 | **不需要**（文档事实订正） |
| **R-6** | **运行期接缝的私有扩展** | `_run_round` 被 `run_super_step` / `run_super_steps` / `_run_graph_loop` 三处调用；若改返回类型会波及两个低层入口 | 只给 `_run_round` 增 **keyword-only** 私有参数 `checkpoint_id: str \| None = None`（缺省 ⇒ 既有调用零改动）；「真异常 + 中断」的收集用 **L2 私有 contextvar**，**不改** `_run_round` 的返回类型 / 不往异常上挂字段 | **不需要**（私有实现 · 行为面不变） |
| **R-7** | **范围 / 行数登记** | 立项书 1,200 行（实现 560 / 测试 640）；运行期接线 + 差分探针可能超预算 | 实施期实测：实现 **986** / 测试 **1,767** / 合计 **2,753** ⇒ 已在 `tasks.md` §行数预算表**如实登记**；**未削减任何 FR / SC**；超支追认按发起者授权流程登记 | **已登记（发起者已授权实施）** |
| **R-8** | **零新增门禁编号** | 本 feature 不新增 G 编号；只复用 G1–G30 | 计划 / 任务 / 实现均不得引入新门禁编号 | **不需要** |
| **R-9** | **编译期校验的额外必红（SENTINEL / object()）** | `tests/facade/test_compiled_graph.py::test_injection_identities_are_preserved`、`::test_all_six_keywords_are_readable` 用 `SENTINEL_CHECKPOINTER = object()`；`::test_non_store_injections_emit_zero_warnings[checkpointer]` 用 `object()` ⇒ 本 feature 后**必红** | **拆分而不删**：checkpointer 用**合法 dummy saver**（或单独断言 `TypeError`）；store/cache/transformers 的 identity / warning 断言保留 | **不需要**（消解 B7F2 的 X-4） |
| **R-10** | **facade 3 方法桩被编译期拒绝** | `tests/facade/test_invoke_interrupt.py::test_resume_re_runs_the_interrupted_node` 用只实现 3 方法的 `StubCheckpointer` 调 `compile()` ⇒ 本 feature 后**必红** | **扩展 `_invoke_support.StubCheckpointer` 到 8 方法**（其余 5 个 no-op / `NotImplementedError`）；保留 `tests/runtime` 的 3 方法桩（运行期不判 `isinstance`） | **不需要**（测试夹具适配 · 不改判据） |
| **R-11** | **普通完成不再“零 put”** | `tests/runtime/test_static_interrupt.py::test_ordinary_completion_does_not_write_a_static_completion_snapshot` 断言 `"put" not in stub.calls` ⇒ 新增每轮 `put` 后**必红** | 改为断言「`put` 次数 == 实际执行轮数 + 1」+「无 F-10 完成快照标记」（**不是**放宽为“随便有 put”） | **不需要**（判据改写 · 非放宽） |
| **R-12** | **运行期归一化不判协议** | 若 `effective_checkpointer` 判 `isinstance` ⇒ `StubCheckpointer` / `_ProbeCheckpointer` 被归一为 `None`，大量既有测试与差分场景变红 | **锁定**：运行期只归一 `None` / `True` / `False` / `thread_id`；协议校验只在编译期（D-15 / FR-018） | **不需要**（口径锁定 · 非门禁偏离） |

### 设计后复核（Phase 1 后 · 模板要求「Re-check after Phase 1 design」）

- **L4 依赖方向**：`persistence` 只 import `freegraph.contracts`（L1）+ stdlib ⇒ G25 预期绿；
  `runtime/**` 不 import `persistence`（鸭子类型）⇒ L2 → L4 的依赖边数 **0**。
- **门面**：`freegraph.graph` 不转出 `MemorySaver`（`facade-L1-L3` 不覆盖 L4 · G18）⇒ 门面符号面零改动。
- **冻结面**：`StateSnapshot` / `Checkpointer` / `RunConfig` / `Span` / `Interrupt` / `PregelTask` /
  `runtime.__all__` / `superstep.__all__` / `contracts.__all__` 均零改动。
- **检查点语义**：快照 + pending writes 分层；`snapshot.config.context is None`；
  `get_next_version` 返回 `int`；`checkpoint_id` 单调可排序；`put_writes` 目标由
  `configurable["checkpoint_id"]` 指定（缺 key ⇒ `KeyError`）；pending writes 去重 / 排序
  逐字上游（`WRITES_IDX_MAP` + `writes_sort_key`）；`list(None)` 线程按插入序。
- **运行期归一化**：`effective_checkpointer` 只判 `None` / `True` / `False` / `thread_id`，
  **不判 `isinstance`** ⇒ L2 测试桩（3 方法）与差分探针继续可用。
- **测试基线**：见下文「Green Baseline & Red List」；实施后 MUST 回到全绿（除上游缺席的 skip）。

---

## Project Structure

### Documentation (this feature)

```text
specs/b14f1-checkpointer-memory-saver/
├── plan.md                  # 本文件
├── research.md              # Phase 0 输出
├── data-model.md            # Phase 1 输出
├── quickstart.md            # Phase 1 输出
├── contracts/
│   ├── memory-saver-contract.md
│   ├── checkpoint-persistence-contract.md
│   └── upstream-parity.md
├── checklists/
│   └── requirements.md      # /speckit.specify 产物
└── tasks.md                 # /speckit.tasks 输出（不在本命令创建）
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/                       # L1 · 零改动（只消费）
│   ├── types.py                     # StateSnapshot / RunConfig / Interrupt / PregelTask
│   └── protocols.py                 # Checkpointer（8 方法）
├── persistence/                     # L4 · 新增
│   ├── __init__.py                  # MemorySaver / InMemorySaver / CheckpointTuple
│   ├── _types.py                    # CheckpointTuple（frozen / slots / 3 字段）
│   └── memory.py                    # MemorySaver 实现（存储 / 锁 / 深拷贝 / on_checkpoint）
├── runtime/                         # L2 · 修改（鸭子类型，不 import L4）
│   ├── _checkpoint.py               # 新增：归一化 / 写快照 / 错误轮中断 / checkpoint id
│   ├── superstep.py                 # 修改：run_graph / _first_graph / _resume_graph / _run_graph_loop / _run_round
│   └── _span_hook.py                # 既有 checkpoint_id 参数（无需改签名）
├── _stategraph.py                   # L3 · 修改：compile() 的 checkpointer 编译期校验
└── graph.py                         # 门面 · 零改动（不转出 L4）

tests/
├── persistence/                     # 新增
│   ├── __init__.py
│   ├── test_memory_saver.py
│   └── test_checkpoint_tuple.py
├── runtime/
│   ├── test_b14f1_step_snapshots.py
│   ├── test_b14f1_resume.py
│   ├── test_b14f1_fanout_barrier.py
│   ├── test_b14f1_error_interrupts.py
│   ├── test_b14f1_spans.py
│   ├── test_b14f1_manual_record_guard.py
│   └── test_interrupt_checkpoint.py        # 修改：拆分「零 saver」断言（R-2）
├── facade/
│   ├── test_b14f1_compile_validation.py    # 新增
│   ├── test_compile_validation.py          # 修改：拆分 nv5（R-1）
│   └── test_compiled_graph.py              # 修改：拆分 non-saver / README 文本（R-1 / R-5）
├── contracts/
│   └── test_b14f1_contracts.py             # 新增
└── differential/
    ├── test_b14f1_checkpoint_parity.py     # 新增 D-01…D-15
    └── parity_probe.py                     # 修改：D-77 判词（R-1）

harness/
├── demo/
│   ├── graph_core.py                # 修改：case_interrupt_resume 挂真实 MemorySaver + soft→check
│   └── README.md                    # 修改：移除 MemorySaver 待锁定条目
└── verification/
    └── B14F1/
        ├── manual-verification.md   # 新增（五段式 + 恢复侧实测）
        └── acceptance.py            # 可选：一键跑关键场景并输出记录
```

### 本 feature 触及的文件（新增 / 修改 / 核对）

| 类别 | 文件 | 动作 |
|---|---|---|
| **新增 · L4** | `src/freegraph/persistence/__init__.py` | 导出 `MemorySaver` / `InMemorySaver` / `CheckpointTuple` |
| **新增 · L4** | `src/freegraph/persistence/_types.py` | `CheckpointTuple` 载体 |
| **新增 · L4** | `src/freegraph/persistence/memory.py` | `MemorySaver` 实现 |
| **新增 · L2 私有** | `src/freegraph/runtime/_checkpoint.py` | 归一化 / 写快照 / 错误轮中断 / id 提取 |
| **修改 · L2** | `src/freegraph/runtime/superstep.py` | 每轮 / 初始 / 错误轮 / span id 接线 |
| **修改 · L2 私有** | `src/freegraph/runtime/_span_hook.py` | **核对**：`start_node_span` 已接受 `checkpoint_id`；如无缺口则零改动 |
| **修改 · L3** | `src/freegraph/_stategraph.py` | `compile()` 编译期校验 |
| **新增 · 测试** | `tests/persistence/` · `tests/runtime/test_b14f1_*.py` · `tests/facade/test_b14f1_*.py` · `tests/contracts/test_b14f1_contracts.py` · `tests/differential/test_b14f1_checkpoint_parity.py` | 见上 |
| **修改 · 冻结断言** | `tests/runtime/test_interrupt_checkpoint.py` · `tests/facade/test_compile_validation.py` · `tests/facade/test_compiled_graph.py` · `tests/differential/parity_probe.py` | R-1 / R-2 / R-5 |
| **修改 · demo** | `harness/demo/graph_core.py` · `harness/demo/README.md` | FR-027 |
| **新增 · 人工验收** | `harness/verification/B14F1/manual-verification.md`（可选 `acceptance.py`） | FR-026 |
| **修改 · 文档** | `README.md` 的 `Checkpointer` 行 + 边界段 | R-5 |
| **核对 · 零改动** | `src/freegraph/contracts/**` · `src/freegraph/graph.py` · `src/freegraph/runtime/__init__.py` · `pyproject.toml` | L1 / 门面 / `runtime.__all__` / 依赖声明 |

---

## Phase 0: Research（摘要 · 详见 [research.md](./research.md)）

| # | 决策 | 结论 |
|---|---|---|
| **D-01** | L4 包结构 | `persistence/{__init__,_types,memory}.py`；只 import L1 + stdlib；门面不转出 |
| **D-02** | 存储模型 | 每 `thread_id` 一份 `_ThreadStore`：`snapshots: dict[id, _StoredCheckpoint]` + 有序 id 列表 + `writes: dict[id, dict[(task_id, idx), _StoredWrite]]`；快照 / 写入分层 |
| **D-03** | checkpoint id | 每线程单调递增 32 位零填充十进制字符串（`f"{n:032d}"`）；字典序 == 数值序；X-01 |
| **D-04** | 版本命名空间 | `get_next_version` 返回 `int+1`；调度版本原样存取；X-02 |
| **D-05** | 读侧载体 | `CheckpointTuple` 恰好 3 字段（用户确认 A）；`snapshot` 是 L1 `StateSnapshot` |
| **D-06** | 写入语义 | `put` 返回带新 id 的 `RunConfig`；`put_writes` 目标由 `configurable["checkpoint_id"]` 指定（缺 key ⇒ `KeyError`）；去重键 `(task_id, WRITES_IDX_MAP.get(channel, idx))`（普通跨调用同 idx 首次、保留最后且同调用内覆盖）；`.pending_writes` 按 `(task_path, task_id, idx)` 升序；`list(None)` 线程按**插入序** |
| **D-07** | 无 `thread_id` | 运行期跳过落盘；直接调用 saver ⇒ `ValueError`（用户确认 A · X-03） |
| **D-08** | 每轮快照策略 | 初始惰性写；挂起写计入该轮；`interrupt_after` 代替该轮；首轮前 `interrupt_before` 兼作初始；空轮不写（用户确认 A） |
| **D-09** | 真异常 + 中断 | L2 私有 contextvar 收集该轮中断；`_run_graph_loop` 先 `put_writes`（显式 round-start checkpoint id）再原样 `raise`；不碰异常字段 |
| **D-10** | span `checkpoint_id` | `_run_round` 增 keyword-only `checkpoint_id`；从初始 / 上一轮 `put` 的返回 config 取；无 saver ⇒ `None` |
| **D-11** | 事件数据源 | `on_checkpoint` 在锁外调用；深拷贝；异常吞掉；`list()` 同源（用户确认 A） |
| **D-12** | `context` / config | `snapshot.config` 只承载 `thread_id` + `configurable["checkpoint_id"]`；`context=None`；不复制 metadata/tags；不写其它 configurable 键 |
| **D-13** | 编译期校验 | L3 私有 `_validate_checkpointer`，用 L1 `runtime_checkable` 协议；`None` / `True` / `False` / 协议实例；其它 `TypeError`；**运行期不再判 `isinstance`** |
| **D-14** | 失败信号 | 内置 `TypeError` / `ValueError` / `KeyError`（`put_writes` 缺 `checkpoint_id` 逐字上游）；不新增 L1 异常；深拷贝失败原样传播 |
| **D-15** | 运行期归一化 | `effective_checkpointer` **只**归一 `None` / `True` / `False` / 缺失/空 `thread_id` ⇒ `None`；**MUST NOT** 判 `isinstance`（保留 L2 测试桩与差分探针） |
| **D-16** | 差分 / 基线 | 新 `tests/differential/test_b14f1_checkpoint_parity.py`；上游缺席 skip；基线 2111 passed / 8 skipped |

---

## Phase 1: Design（摘要）

- **Data model**：[data-model.md](./data-model.md) —— `MemorySaver` / `_ThreadStore` / `_StoredCheckpoint` /
  `_StoredWrite` / `CheckpointTuple` / `CheckpointId` / `StateSnapshot`（消费）/ `PendingWrite` /
  `SchedulerLedger` 的字段、不变量、生命周期与状态转换。
- **Contracts**：
  - [memory-saver-contract.md](./contracts/memory-saver-contract.md) —— L4 公开面、`CheckpointTuple`、
    8 方法、存储 / 锁 / 深拷贝 / 失败信号、编译期校验。
  - [checkpoint-persistence-contract.md](./contracts/checkpoint-persistence-contract.md) —— 运行期写盘时机、
    快照 8 字段组装、pending writes、静态 / fan-out / 屏障、真异常 + 中断、span `checkpoint_id`、
    `context` 不持久化、`checkpoints` 数据源。
  - [upstream-parity.md](./contracts/upstream-parity.md) —— P-01…P-21 / D-01…D-15 / X-01…X-08 的
    evidence 与判词。
- **Quickstart**：[quickstart.md](./quickstart.md) —— 可执行的 **15 组**验证场景（§0 前置条件 +
  §1–§15：快照计数 / 写入取回 / 隔离 / 协议 / 恢复 / 静态挂起 / fan-out / 屏障 / 真异常 + 中断 /
  span / 编译期 / `on_checkpoint` / `context` / 差分 / demo + 人工验收 / 全量回归）。

---

## Risks & Registrations

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| **K-1** | 运行期接线改到 `_run_graph_loop` / `_run_round` 的既有控制流 | 可能影响 B7F1 / B10F1 / B13F1 的冻结语义 | 只增 keyword-only 参数（缺省不改既有调用）；快照写入全部 `if checkpointer is not None` 守卫；差分 + 全量回归 |
| **K-2** | 「真异常 + 中断」收集改变异常时序 | 真异常类型 / identity / 消息被改 | 用 L2 私有 contextvar；不碰异常对象；SC-018 断言 identity / 类型 / 消息不变 |
| **K-3** | F-10 完成快照与每轮快照重复 | SC-015 红 | `static_resume` 的最后一轮跳过每轮 `put`，由 `_clear_static_suspension` 写一次；测试断言重复次数 0 |
| **K-4** | `snapshot.config` 的 `configurable` 键选择 | B15F1 / B16F1 取快照时行为不一致 | 按上游 `InMemorySaver.put` 的最小返回形态：只含 `thread_id` + `checkpoint_id`；contract 写死 |
| **K-5** | 冻结测试必红（R-1 / R-2 / R-5） | CI 红 | 实施前先改测试（拆分而不删）；每改一处跑对应测试 |
| **K-6** | 差分探针上游缺席 | D-01…D-15 skip | `pytest.importorskip("langgraph")`；CI Linux 全量档真跑；缺上游不判失败 |
| **K-7** | 行数超预算 | 范围登记 | 实施期实测；R-7 如实登记；**不**削减判据 |
| **K-8** | `MemorySaver` 深拷贝不可拷贝对象 | 注入 checkpointer 时新增异常 | 原异常传播；SC-005 明确「可深拷贝载荷」；文档写明 |
| **K-9** | `put_writes` 改为显式 `checkpoint_id` 后，既有 `_write_suspend` / `_resume_graph` 仍传裸 `run_config` | `KeyError` / 写错 checkpoint | 实施时同步改：`_write_suspend` 捕获 `put` 返回 config；`_resume_graph` 复用 `history.snapshot.config`；`put_error_interrupts` 用 round-start id（T046 / T057） |

---

## Green Baseline & Red List（宪法 v1.11.0 的基线义务）

### 基线（**2026-11-22 · 实施前实跑**）

```text
.venv/bin/python -m pytest -q --tb=no
⇒ 2111 passed, 8 skipped in 167.45s
```

### 变红清单（**实施前 MUST 用沙箱实测补全** · 宪法 v1.11.0）

> ⚠️ **不得只凭推理**：实施前 MUST 按本 feature 的落地形态（加 `_validate_checkpointer` +
> 每轮 `put` + 运行期归一化）改动源码、跑全量测试，把实际变红项逐条登记到本表
> （带 `文件:行号` + 变红原因）。下列 **13** 项为**已知必红**，实测若发现新增项 MUST 追加。

| # | 测试 | 原因 | 处置 |
|---|---|---|---|
| **RED-1** | `tests/facade/test_compile_validation.py::test_nv5_non_conforming_checkpointer_and_store_compile` | 本 feature 后非法 checkpointer ⇒ `TypeError` | **拆分而不删**：拆成「checkpointer 非法 ⇒ TypeError」+「store 非法 ⇒ 接受 + 1 warning」 |
| **RED-2** | `tests/facade/test_compiled_graph.py::test_non_store_objects_are_accepted` | 同上 | **拆分而不删**：非法 store 接受；非法 checkpointer 改断言 `TypeError` |
| **RED-3** | `tests/facade/test_compiled_graph.py::test_readme_states_store_and_checkpointer_boundaries` | README 文本更新（R-5） | 断言改为新文本（**不是**放宽） |
| **RED-4** | `tests/differential/parity_probe.py` 的 D-77 | 编译期校验落地 | 判词 `DIFF` → `SAME`；理由改为「两侧都 `TypeError`（B7F2 X-4 消解）」 |
| **RED-5** | `tests/runtime/test_interrupt_checkpoint.py::test_the_runtime_never_imports_a_saver_implementation` | 新增 L4 `MemorySaver` | **拆分而不删**：保留「`runtime/**` 零 saver + 不 import `persistence`」；新增「`persistence/memory.py` 有 `MemorySaver`」 |
| **RED-6** | `tests/runtime/test_acceptance_script.py` 中依赖 demo README / `graph_core.py` 的文本断言 | FR-027 更新 | 同步断言（**不是**放宽）；`graph_core.py` 退出码仍须 0 |
| **RED-7** | `tests/facade/test_invoke_interrupt.py` 的 docstring（若实施期选择同步） | 旧文本「`src/**` 零 saver」已过期 | 只改 docstring（**不加**判据） |
| **RED-8** | `tests/facade/test_compiled_graph.py::test_injection_identities_are_preserved` | `SENTINEL_CHECKPOINTER = object()` 被编译期校验拒绝 | **拆分而不删**：checkpointer 用合法 dummy saver（或单独断言 `TypeError`）；其余注入项 identity 保留 |
| **RED-9** | `tests/facade/test_compiled_graph.py::test_all_six_keywords_are_readable` | 同上 | 同上（checkpointer 用合法 dummy saver） |
| **RED-10** | `tests/facade/test_compiled_graph.py::test_non_store_injections_emit_zero_warnings[checkpointer]` | 参数化中的 `object()` 被拒 | 该参数改用合法 dummy saver，或把 checkpointer 从参数化中拆出 |
| **RED-11** | `tests/facade/test_invoke_interrupt.py::test_resume_re_runs_the_interrupted_node` | facade `StubCheckpointer` 只实现 3 方法，编译期拒绝 | 扩展 `_invoke_support.StubCheckpointer` 到 8 方法（其余 5 个 no-op / `NotImplementedError`） |
| **RED-12** | `tests/runtime/test_static_interrupt.py::test_ordinary_completion_does_not_write_a_static_completion_snapshot` | 新增每轮 `put` 后 `"put" not in stub.calls` 必红 | 改为「`put` 次数 == 实际执行轮数 + 1」+「无 F-10 完成快照标记」 |
| **RED-13** | `tests/facade/test_invoke_interrupt.py::test_resume_re_runs_the_interrupted_node` | 原用例未传 `thread_id`；B14F1 的运行期归一化在无 `thread_id` 时跳过 saver ⇒ `checkpointer_required` 必红 | 更新用例：两次 `invoke` 传同一 `RunConfig(thread_id=...)`（**保留原恢复断言，不放宽**） |

> ⚠️ 除上述 **13** 处，**其余测试 MUST 保持绿**。实施期若发现新的必红冻结断言 ⇒
> MUST 按「拆分而不删 + 判据只可更严」登记，**MUST NOT** 写永久红的 CI。

---

## Complexity Tracking

> **本 feature 无宪法门禁违规** ⇒ 无需例外论证。以下为**范围 / 复杂度登记**（非违规）：

| 项 | 说明 | 处置 |
|---|---|---|
| 新增 L4 包 | `persistence/` 在层注册表已登记（B3F1），G25 零改动 | 直接新增目录；`__all__` 只 3 个符号 |
| 运行期接缝 | `_run_graph_loop` / `_run_round` 的私有扩展 | keyword-only 缺省参数；contextvar 收集错误轮中断 |
| 新增测试目录 | `tests/persistence/` | 与 `tests/runtime` / `tests/facade` 并列；无新门禁 |
| 差分场景 | D-01…D-15 | 新文件；上游缺席 skip；不改既有场景 |

---

## Implementation Sequencing（供 `/speckit.tasks` 展开）

| 阶段 | 内容 | 产出 |
|---|---|---|
| **P0 · 冻结断言预修** | R-1 / R-2 / R-5 / R-9…R-11 的测试拆分（**逻辑前置**：先明确红线再落源码；tasks 中与 Foundational 同批执行，不要求物理排在 L4 实现之前） | RED-1…RED-13 的测试改动 |
| **P1 · L4 包** | `_types.py` → `memory.py` → `__init__.py` | `CheckpointTuple` + `MemorySaver` + 别名 |
| **P2 · L4 单测** | 协议 / 快照 / 写入（显式 id + 上游去重/排序）/ 列表 / 删除 / 版本 / 隔离 / 深拷贝 / 并发 / 失败信号 | `tests/persistence/*` |
| **P3 · 运行期归一化** | `runtime/_checkpoint.py` + `run_graph` 的 `effective_checkpointer` | 只归一 `None` / `True` / `False` / 无 `thread_id`；**不判 `isinstance`** |
| **P4 · 初始 / 每轮快照** | `_run_graph_loop` 的初始惰性写 + 每轮写 + `interrupt_after` 代替 | `test_b14f1_step_snapshots.py` |
| **P5 · 恢复 / 静态 / F-10** | `_first_graph` / `_resume_graph` 传初始 id；`static_resume` 跳过最后一轮；**`put_writes` 用显式 checkpoint id** | `test_b14f1_resume.py` |
| **P6 · 真异常 + 中断** | contextvar 收集 + `put_writes`（round-start checkpoint id）+ 原样抛 | `test_b14f1_error_interrupts.py` |
| **P7 · span `checkpoint_id`** | `_run_round` 的 keyword-only 参数 + `start_node_span` | `test_b14f1_spans.py` |
| **P8 · 编译期校验** | `_stategraph._validate_checkpointer` | `test_b14f1_compile_validation.py` |
| **P9 · fan-out / 屏障** | 原样存取 + 多 task_id | `test_b14f1_fanout_barrier.py` |
| **P10 · 差分** | D-01…D-15 + D-77 更新 | `test_b14f1_checkpoint_parity.py` |
| **P11 · demo / 文档** | `graph_core.py` 硬断言 · `README` · `harness/demo/README.md` | FR-027 / SC-023 |
| **P12 · 人工验收** | `manual-verification.md`（恢复侧实测） | FR-026 / SC-022 |
| **P13 · 全量回归 / 门禁** | `pytest -q` · G25 / G7 / G8 / G16 / G18 / G19 | 全绿 + 行数实测 |

---

## Notes

- **唯一权威**：需求与判据以 [spec.md](./spec.md) 为准；本 plan 只承接，若冲突以 spec 为准并回修本 plan。
- **上游锚点**：`langgraph` **1.2.11**（2026-11-22 取证）；换版本 MUST 重新核实全部行号。
- **零第三方**：生产代码只用标准库；`langgraph` 只在差分测试侧。
- **L4 边界**：`persistence` 只 import L1 + stdlib；`runtime/**` 通过鸭子类型调用 checkpointer，
  **MUST NOT** import `freegraph.persistence`；门面 **MUST NOT** 转出 `MemorySaver`。
- **运行期归一化**：`effective_checkpointer` **只**归一 `None` / `True` / `False` / 缺失/空
  `thread_id`；**MUST NOT** 判 `isinstance(..., Checkpointer)`（协议校验只在编译期）。
- **不伪造**：`stream(checkpoints)` 的消费端未接线前，**MUST NOT** 产生伪造 checkpoint 事件。
- **不越界**：不实现 `SqliteSaver` / `get_state` / `Time Travel` / `Store` / Postgres / async。
- **文档纪律**：`README.md` 只更新 `Checkpointer` 行与边界段，**不新增**兼容矩阵行
  （矩阵只覆盖 L1 + 门面；`MemorySaver` / `InMemorySaver` / `CheckpointTuple` 的 3 行按
  spec **D-07** 由 **B24F1 / B25F1** 定稿）。
- **人工验证目录名**：按 `harness/verification/README.md` 的既有约定使用
  `harness/verification/B14F1/`（`<feature>` = feature ID）；spec 已同步为同一路径。
