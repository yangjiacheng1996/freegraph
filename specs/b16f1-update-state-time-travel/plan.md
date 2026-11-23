# Implementation Plan: B16F1 · `update_state` + 时间旅行回放

**Branch**: `b16f1-update-state-time-travel`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_plan` 钩子；既有 feature 同样在 `main` 上开发）

**Date**: 2026-11-23 | **Spec**: [spec.md](./spec.md)（**唯一权威** · 含 **11** 条 Clarifications 定案 + **10** 条形态锁定裁定 + **26** 条 FR + **18** 条 SC + **23** 条编号 P（P-01…P-23，另加 P-01b / P-03b 拆分，共 **25** 行）+ **17** 条 D + **6** 条 X）

**Input**: Feature specification from `specs/b16f1-update-state-time-travel/spec.md`

**Feature ID**: `B16F1`（M3 可诊断 · **第 29 个**（对齐 `harness/features/README.md` 开发序）· 前置：**B15F1**；承接 **B10F1 / B13F1 / B8F3 / B14F1 / B15F1 / B7F3**）

> **范围提醒**：本 feature 是 **L4 持久化层的回放入口** + **L1 `CompiledGraph` 的状态更新面** +
> **L2 执行内核的时间旅行接线**。
> **不实现** `Store`（B17 已砍）· Postgres / async（v2）· 前端 UI（B26）·
> trace 存储（B20F1 / B20F2）· 并行分支执行 / 分支树 UI ·
> `task_id` / `values=None, as_node=END` / fresh-thread `update_state` 初始化（v1 能力边界）。
> **MUST NOT** 改变普通运行的图执行语义；**MUST** 保持运行时依赖闭包为空集。
> **复用** B14F1 / B15F1 的 checkpoint 顺位 id、`parent_config` 父链、
> `put` / `put_writes` 渠道、`get_state` / `get_state_history` 组装口径与
> `MemorySaver` / `SqliteSaver` 后端；**MUST NOT** 另立 id 空间、第二套快照组装路径。

---

## Summary

交付**五件事**：

| # | 交付物 | 语义 | 关键规则 |
|---|---|---|---|
| **①** | **`CompiledGraph.update_state`** | 基于历史 checkpoint 修改状态并开新分支 | 锁定签名 `(config, values, as_node=None) -> RunConfig`；`values` 走 C6；`as_node` 后继（出边 / 条件边 / fan-out）；新 id = `MAX+1`；`parent_config` = 基准快照 |
| **②** | **历史 checkpoint 重放** | 从任意历史点继续执行 | 唯一入口 `invoke(None, snapshot.config)`；显式 id 不存在 / **该显式 id 分支**无 saver / 坏 ns ⇒ `ValueError`；非 no-op replay / 历史续跑先写 branch anchor；`update_state` 分支快照兼任 anchor；**正常终态** no-op |
| **③** | **分叉不污染原历史** | 重放 / 分叉多次后原快照仍完整 | 只追加；原 8 字段与 pending writes 零变化；`get_state_history` 继续倒序可枚举；分支结构由 `parent_config` 表达 |
| **④** | **中断 / 静态挂起与时间旅行组合** | 动态中断重放、静态快照继续、恢复最新暂停点 | 静态快照 `invoke(None, ...)` **保留 `static_ack`**；`update_state` 新分支**清空**静态标记；`Command(resume)` 只读**最新**快照 + pending writes |
| **⑤** | **L4 `put` 的显式父链扩展** | 分支快照的父链指向被分叉点 | `configurable["checkpoint_id"]` 非空 ⇒ parent = 该 id；缺失 ⇒ 保持 B14F1「最新」语义；`MemorySaver` / `SqliteSaver` 一致 |

**技术路线（零第三方依赖 · 零出站 · 零环境变量）**：

| 环节 | 落点 | 说明 |
|---|---|---|
| **L1 协议** | **修改** `src/freegraph/contracts/protocols.py` | `CompiledGraph.update_state` 的 `config` 注解放宽为 `RunConfig \| Mapping \| None`；返回类别改为 **`RunConfig`**；其余五方法与字段面零改动 |
| **L3 门面实现** | **修改** `src/freegraph/_stategraph.py` | `update_state` 替换 `NotImplementedError`，调用 L2 私有 `_time_travel`；L3 只做编排 / 校验，不在门面层翻译 config |
| **L2 时间旅行助手** | **新增** `src/freegraph/runtime/_time_travel.py` | 基准定位 / `as_node` 推断 / C6 合并 / 条件边 + fan-out 后继 / `put` / 返回新 config |
| **L2 执行内核接线** | **修改** `src/freegraph/runtime/superstep.py` | `_first_graph` 的显式 id 校验 + replay anchor；`_resume_graph` 最新快照定位；`_run_graph_loop` 父链逐条推进；静态 ack 保留 / 清空分工 |
| **L2 checkpoint 助手** | **不修改** `src/freegraph/runtime/_checkpoint.py` | anchor 的 metadata 构造复用既有私有助手（`_metadata` / `config_for_checkpoint`）；如需新 helper，落 `superstep.py` / `_time_travel.py`，**不新增公开面** |
| **L2 stream 写盘** | **修改** `src/freegraph/runtime/_stream_checkpoint.py` | 每次 `put` 用当前 checkpoint id 作 parent；stream v1 仍忽略用户 config 的 `checkpoint_id`（B8F2 冻结面） |
| **L4 写侧** | **修改** `src/freegraph/persistence/memory.py` · `sqlite.py` | `put` 的显式父链扩展；既有「无 id ⇒ 最新」行为零变化 |
| **测试** | 新增 `tests/facade/test_b16f1_*` / `tests/runtime/test_b16f1_*` / `tests/persistence/test_b16f1_*` / `tests/contracts/test_b16f1_*` / `tests/differential/test_b16f1_*` | 重放 / 分叉 / 合并 / 父链 / 静态 / 恢复 / 双后端 / 差分 / 文档守卫 |
| **文档 / 人工验收** | `README.md` · `harness/demo/README.md` · `harness/verification/B16F1/manual-verification.md` | 锁定 `update_state` 签名；移除「待锁定」条目；fake + 真实模型两轮 |

**明确边界（不是偏离，是能力边界）**：

- `stream` v1 **不是**回放入口；保持 B8F2 的「忽略 checkpointer 恢复」语义。
- `update_state` 不暴露 `task_id`；`values=None` ⇒ `TypeError`；fresh-thread 初始化不支持。
- 历史是**扁平倒序列表**；不提供分支树 / 按分支枚举 API；分支结构由 `parent_config` 读取。
- 同一 thread 可多次分叉；每次 `update_state` 只产生一条新分支；v1 不做并行分支执行 / 分支 UI。
- `delete_for_runs` / `copy_thread` 继续 `NotImplementedError`。
- `metadata` 仍是内部调度账本；不承诺上游 `source` 字段；差分排除 metadata。
- `SqliteSaver` 的 JSON 纯数据约束（B15F1 X-05）继续适用。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（本机 `.venv` 3.11.16）；只用标准库
`collections.abc` / `copy` / `dataclasses` / `datetime` / `typing` / `contextlib`。
**MUST NOT** 使用 3.12+ 的 `override` / `TypeIs` / `TypeAliasType` / PEP 695。

**Primary Dependencies**: **零第三方运行时依赖**（`dependencies = []`）。
开发期 `pytest` 既有；差分侧仅钉 `langgraph==1.2.11`（`.venv` 已装）。
`pyproject.toml` **零改动** ⇒ G3 / G21 / G23 恒绿。

**Storage**: 复用 B14F1 `MemorySaver` 与 B15F1 `SqliteSaver`；本 feature **不新增存储后端**、
不新增表 / 列 / 序列化格式。SQLite 的 checkpoint 存储与 trace 的 SQLite 仍是**两套存储**。

**Testing**: pytest ——
`tests/facade/test_b16f1_update_state.py`（签名 / config 载体 / 合并 / as_node / 错误）·
`tests/facade/test_b16f1_time_travel.py`（历史点重放 / 正常终态 no-op / 父链 / 历史完整性 / 多次分叉 / `invoke(dict, historical.config)` 边界）·
`tests/runtime/test_b16f1_update_state_runtime.py`（scheduler / 后继 / 条件边 / fan-out / 静态标记）·
`tests/runtime/test_b16f1_replay_anchor.py`（branch anchor / 父链 / 正常终态 no-op）·
`tests/runtime/test_b16f1_pending_protection.py`（pending 只落新 checkpoint / 原历史不变）·
`tests/runtime/test_b16f1_static_replay.py`（静态 ack 保留 / 断点前重放再次暂停）·
`tests/runtime/test_b16f1_resume_latest.py`（`Command(resume)` 最新定位 / 旧 pending 不变）·
`tests/persistence/test_b16f1_put_parent.py`（双后端显式父链 / 既有行为不变）·
`tests/contracts/test_b16f1_contracts.py`（L1 注解 / 返回类别 / 零依赖 / 零 env / 零出站 / ARCH-1）·
`tests/runtime/test_b16f1_manual_record_guard.py`（SC-013 文档守卫）·
`tests/runtime/test_b16f1_doc_guard.py`（SC-018 文档守卫：demo README / target.py）·
`tests/differential/test_b16f1_time_travel_parity.py`（D-01…D-17；上游缺席 ⇒ skip）。

**Target Platform**: Linux / macOS / Windows · CPython 3.11+ · 零出站。Windows 证据沿用现有 CI 矩阵。

**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A（不设墙钟预算）**。v1 以**正确性 / 上游对齐**优先；
本 feature 不设吞吐 / 延迟断言；MUST NOT 用耗时做 CI 断言。

**Scale/Scope**: 低并发 · 单线程历史枚举 · 每次 `update_state` 一条分支 ·
同 thread 可分叉多次；不承诺高并发 / 跨进程严格串行（沿用 B15F1 的 SQLite 口径）。

**Constraints**（主要来自 spec）：

| 约束 | spec 条目 |
|---|---|
| 零第三方 / 零 env / 零出站；L4 只依赖 L1 + stdlib；L3 → L2 合法；L2 不 import L4 | FR-021 · SC-005 |
| `update_state` 签名 / 返回 `RunConfig` / 双形态 config | FR-001 / FR-002 · 裁定 1 · R-1 |
| 基准必须存在；显式 id 不存在 / thread 不存在 ⇒ `ValueError` | FR-003 / FR-004 / FR-010 · 裁定 2 / 8 |
| 新 id = `MAX+1`；`parent_config` = 基准；只追加；原历史零变化 | FR-005 / FR-014 / FR-017 · 裁定 3 · SC-002 / SC-007 |
| `values` 按 C6（归约 / 覆盖）；未知 key ⇒ `InvalidUpdateError` | FR-006 · 裁定 4 · SC-003 |
| `as_node` 推断 / 不存在 / 歧义；`next` = 后继（出边 + 条件边 + fan-out） | FR-007 · 裁定 4 · SC-009 |
| 新快照 8 字段；`tasks=()` / `interrupts=()` / 静态标记清空 / 不复制 pending | FR-008 · 裁定 4 |
| 重放入口 = `invoke(None, snapshot.config)`；**正常终态** no-op；不读缓存 | FR-009 / FR-015 · 裁定 5 · SC-016 |
| **显式 `checkpoint_id` 的重放**无 saver / `True` / `False` / 非空 `checkpoint_ns` ⇒ `ValueError`；无显式 id 的普通 `invoke` 行为不变 | FR-003 · 裁定 5 · SC-017 |
| 非 no-op replay / 历史续跑先写 branch anchor；正常终态不写；`update_state` 分支快照兼任 anchor，分叉后 `invoke(None, fork_config)` 不再写 anchor | FR-026 · 裁定 10 · SC-008 / SC-014 / SC-016 |
| 静态快照 replay 保留 ack；断点前重放再次暂停；`update_state` 清空 ack | FR-011 · 裁定 6 · P-23 · SC-011 |
| `Command(resume)` 只读最新快照 + pending writes；旧 pending 不变 | FR-013 · 裁定 6 · SC-011 / SC-014 |
| `context` 不持久化 / 不从历史恢复 | FR-012 · 裁定 7 · SC-010 |
| 不新增 L1 异常类型；失败信号按裁定 8 | FR-025 · SC-015 |
| 差分 D-01…D-17；上游缺席 skip | FR-023 · SC-012 |
| 人工验证五段式 + fake + 真实模型两轮 | FR-024 · SC-013 |
| README / demo README 更新；`target.py` 零改动 | FR-022 · SC-018 |

> **无未决澄清**：spec 的 11 条 Clarifications 定案 + 10 条形态锁定裁定已收敛全部用户决策点；
> 本 plan 只落设计决策与实现顺序。**唯一 parity 事实订正（正常终态 replay）已落 spec 的 X-06（自研区 ②）**。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| **原则 I · 零 LangSmith / 零出站 / 零环境变量** | 零新增依赖；无 env / 网络 / 出站；G24 / G26 / G27 | ✅ 通过 |
| **原则 II · 内核纯净** | 不 import `langchain*` / `langgraph*` / `langsmith`；L2 新文件只依赖 L1 + 同层 runtime；L2 不 import L4；L3 → L2 合法 | ✅ 通过 |
| **原则 III · 验收契约优先** | `harness/demo/target.py` **零改动**；门面 8 符号面零改动；C4 / C6 / C8 回归保持 | ✅ 通过 |
| **原则 IV · 可诊断性** | 历史重放 + 分叉 + 状态快照 + 中断 / 恢复四类能力可组合；回放入口已交付 | ✅ 通过 |
| **原则 V · 人工验收** | `harness/verification/B16F1/manual-verification.md` 五段式 + **fake 轮 + 真实模型轮（本 feature 自跑；B25F1 仅复验）** | ✅ 计划交付（门禁 5 合规） |
| **原则 VI · 规格驱动** | spec FR-001…FR-026 / SC-001…SC-018 全部可追溯；tasks 由 `/speckit.tasks` 展开 | ✅ 通过 |
| **原则 VII · 职责边界** | 只做 C19 的时间旅行 + C10 的 `update_state`；不做 Store / Postgres / async / UI / 分支树 | ✅ 通过 |
| **原则 VIII · 证据与术语** | spec P-01…P-23 / D-01…D-17 / X-01…X-06 带版本 + `路径:行号`；术语「基准快照 / 分支快照 / branch anchor / 静态 ack」统一 | ✅ 通过 |
| **原则 IX · 许可证 / 商标** | **不复制上游代码**；只按上游行为语义自研；`THIRD_PARTY_NOTICES` 不新增条目；运行时依赖仍为零 | ✅ 通过 |
| **原则 X · 文档 / 署名头** | 新增 L2 文件带本项目署名头；README / demo README / manual-verification 更新 | ✅ 计划交付 |
| **原则 XI · 上游优先** | P-01…P-23 逐条对照；X-01…X-06 有效偏离；D-01…D-17；**X-06 的 normal-terminal replay parity 订正已落 spec（自研区 ②：上游文档/实现不一致）** | ✅ 通过（含已登记偏离） |
| **原则 XII · 最优设计优先** | 复用 `StateSnapshot` / `RunConfig` / `CheckpointTuple` / 调度账本；不另造第二套快照 / id / 合并路径 | ✅ 通过 |

### 登记项（**plan 阶段必须如实登记**）

| # | 类别 | 内容 | 处置 | 追认 |
|---|---|---|---|---|
| **R-1** | **L1 `update_state` 返回类别 / config 注解放宽** | B2F1 冻结 `StateSnapshot` 返回 + `RunConfig` 注解；spec 裁定 1 要求改为 `RunConfig` 返回 + 双形态注解 | `contracts/protocols.py` 只改 `update_state` 一处；**拆分而不删**；追认文字落 `harness/verification/B16F1/manual-verification.md`；发起者已于 2026-11-23 选 **A** 批准 | **已追认**（R-1 · 唯一一次） |
| **R-2** | **L4 `put` 显式父链扩展** | B14F1 裁定 6 / B15F1 裁定 4 / 5：`put` 的 parent = 最新快照 | 新增「显式 `configurable["checkpoint_id"]` ⇒ parent = 该 id」；缺失 / 空串 ⇒ 保持「最新」；既有调用零变化；双后端一致 | **不需要**（向后兼容扩展） |
| **R-3** | **`Command(resume)` 最新定位** | 现行 `_resume_graph` 用 `get_tuple(run_config)`，会取指定 id | 改为只读该 thread **最新**快照 + pending writes（忽略旧 `checkpoint_id`）；`__resume__` 只写最新；与 B10F1 FR-010 的「最新快照」口径对齐 | **不需要**（B10F1 已知情 · spec X-04） |
| **R-4** | **非 no-op replay 的 branch anchor** | 上游 `_loop.py:952-965` 在 time-travel 首轮写 `source="fork"` 快照；freegraph 需要保证首轮中断 / 真异常不把 pending writes 写到原快照 | **spec 已正式化（裁定 10 / FR-026）**：对**显式历史 id + 非 no-op**（`next` / fanout / 静态 / pending / 非空 input dict）的 replay / B7F3 历史续跑，在 `_first_graph` 先写一条 branch anchor（parent = 基准；values / next / static 标记 / scheduler 与基准一致；`interrupts=()` / `tasks=()`）；后续快照链在 anchor 之后；`invoke(dict, historical.config)` 仍是 B7F3 续跑、不是 replay，但同受 anchor 保护；**`update_state` 产出的分支快照兼任 anchor，从该分支快照 `invoke(None, fork_config)` 不再写额外 anchor** | **不需要**（实现决策 · 上游同款 · spec 已落） |
| **R-5** | **正常终态 replay 不写 anchor（STRICTER · X-06）** | 实测上游 `invoke(None, final.config)` **会**写一条 `source="fork"` 快照（不重跑节点）；spec SC-016 要求**零新快照** | 按 spec 实现：**正常终态**（`next==()` 且无 fanout / 静态挂起 / pending 中断，且 input 为 None / 空 dict）⇒ **不写 anchor、零新快照**；差分 D-02 只比较「不执行节点 / 终态一致」，**不比较快照数**；spec 的 P-12 / D-02 已改 **STRICTER（X-06）**；X-06 归入自研区 **②（上游文档/实现不一致）** | **本 feature 登记**（更严行为；不新增门禁） |
| **R-6** | **冻结断言拆分** | 三处测试断言 `update_state` 抛 `NotImplementedError`：`test_compiled_graph.py:76-78` · `test_facade.py:234-236` · `test_conditional_edge_surface.py:102-111` | **拆分而不删**：保留「B16F1 之前未实现」历史注记；改为已实现正面断言（无 saver ⇒ `ValueError`；有 saver ⇒ 返回 `RunConfig`） | **不需要**（基线冻结断言拆分） |
| **R-7** | **README / demo README** | `harness/demo/README.md:118` 仍列 `update_state` 签名未锁定；`README.md` 的 `CompiledGraph` 行仍写「由 B16F1 交付」 | 移除 demo README 待锁定行并补锁定说明；更新 README 的 `CompiledGraph` 行（**不新增**兼容矩阵行 · B24F1 定稿）；`target.py` 零改动 | **不需要** |
| **R-8** | **人工验证 / 质量门禁 5** | 宪法原则 V / 立项书 §9.1 门禁 5 要求真实模型一轮 | B16F1 **自跑** fake 轮 + 真实模型轮；真实模型轮使用 `harness/demo/target.py` 或等价固定脚本；记录端点 / 调用次数 / 零出站归因；B25F1 只复验 | **计划交付** |
| **R-9** | **零新增门禁编号** | 本 feature 不新增 G 编号；复用 G3 / G7 / G8 / G16 / G18 / G19 / G21 / G22 / G23 / G24 / G25 / G26 / G27 / G30 | 由 tasks 显式运行关键门禁 + 全量 pytest 隐式覆盖 | **不需要** |
| **R-10** | **行数 / 范围登记** | 立项书 1,040 行（实现 480 / 测试 560）；父链扩展 + 静态 / 中断组合 + anchor + 差分必然扩大范围 | tasks 行数预算**如实登记**（预估实现 +120~200 / 测试 +150~300）；**不削减任何 FR / SC** | **已登记（实施期复核）** |
| **R-11** | **条件边 / fan-out 后继的复用** | `as_node` 需要产出 `next` / `.scheduler["fanout"]`；不得另写合并 / 路由路径 | 复用 `_evaluate_source_routes` + `_commit_outcome` + `_merge_writes` + `_clear_step_end` + `_determine_triggers`；`values` 构造为 `{key: (value,)}` 的 `_TaskOutcome`；不执行 `as_node` 节点函数 | **不需要**（私有实现 · C6 / C8 复用） |
| **R-12** | **静态 ack 的分工** | `update_state` 新分支清空 ack；静态快照 `invoke(None, ...)` 保留 ack | `update_state` 的 metadata `suspension_kind=None` / `static_ack=None`；replay 使用基准 history 的 `scheduler.static_ack`（不重写）；anchor 复制静态标记；B13F1 FR-007 不破 | **不需要**（spec 裁定 4 / 6 已锁定） |
| **R-13** | **上游 parity 事实订正（已落 spec · X-06 · 自研区 ②）** | 上游 final replay **会写 fork checkpoint**（实测：`history before 4 → after 5`，新增 `source="fork"`；不重跑节点）；spec 原 P-12 / D-02 标 `SAME` 与 SC-016「零新快照」不一致 | **已订正**：spec 的 P-12 / D-02 改 **STRICTER（X-06）**，并归入自研区 **②（上游文档/实现不一致）**；实现按 SC-016 零新快照；差分 D-02 比较「不执行节点 / 终态一致」 | **已确认**（2026-11-23 · 只改标注 / 判据不放松） |
| **R-14** | **下游承接接线** | spec 的 D-01…D-05（B24F1 / B25F1 / B26 v2 / Postgres v2 / B20F1-B20F2） | 由 tasks 在既有提示词初稿追加「下游承接（B16F1）」节；B26 v2 / Postgres v2 无提示词文件 ⇒ 在 B24F1 矩阵 / plan 记录口径；**不新增门禁编号** | **不需要**（登记项） |
| **R-15** | **冻结断言清单实测化（宪法 v1.11.0）** | 本表的 RED-1…RED-5 为**推理预登记**；宪法要求「沙箱按落地形态改源码 → 跑既有套件 → 采集变红断言」，带 `文件:行号` + 变红原因 | **T001 MUST 实测复核**：在临时副本按本 feature 落地形态改动 `update_state` / `put` 父链 → 跑全量套件 → 逐条核对 RED-1…RED-5，缺失即补登记；基线计数同步记入 manual-verification「环境」段 | **不需要**（基线 / 冻结断言拆分） |
| **R-16** | **上游 spec / data-model 回溯修订** | 宪法 v1.9.0 ①要求「回溯修订该冻结面的契约 + spec + 冻结断言」；B16F1 改了 `CompiledGraph.update_state` 的返回类别 / config 注解与 `put` 父链 | 由 tasks **核对已落 + 补齐遗漏**：`specs/b2f1-contracts-protocols/{spec,data-model}.md`、`specs/b14f1-checkpointer-memory-saver/spec.md` 裁定 6、`specs/b15f1-sqlite-saver-state-history/spec.md` 裁定 4 / 5、`specs/b7f3-invoke-full-state/spec.md` CF-05 **与 `contracts/invoke-contract.md`**（**拆分而不删**，保留历史注解） | **并入 R-1**（唯一一次追认） |

### 质量门禁 5 合规执行

| 项 | 内容 |
|---|---|
| 门禁项 | 宪法原则 V / 立项书 §9.1 门禁 5「人工验证记录含真实模型一轮」 |
| 执行方式 | B16F1 **自跑** fake 轮 + 真实模型轮；真实模型轮使用 `harness/demo/target.py` 或等价固定脚本 |
| 证据要求 | 模型端点 / 调用次数 / 零出站归因写入 `manual-verification.md`；去 `LANGSMITH_*` 干净环境；socket 只观测不阻断 |
| 判据 | 门禁 5 **不偏离、不放宽**；时间旅行 / 分叉 / 合并 / 静默失败判据一字未改 |
| 承接方 | **B25F1（M4 · 双跑验收）** 做跨 feature **复验**（不是替代） |

### 设计后复核（Phase 1 后）

- **L1**：仅 `CompiledGraph.update_state` 一处注解 / 返回类别改动；`StateSnapshot` /
  `RunConfig` / `Interrupt` / `PregelTask` / `Checkpointer` 字段面与其余五方法零改动。
- **L2**：新增 `runtime/_time_travel.py` 属 **L2 目录条目**，与 `superstep.py` / `_state_read.py`
  同一注册条目 ⇒ 内部 import **不产生层边**；L2 不 import `freegraph.persistence`（saver 走鸭子类型）。
- **L3**：`_stategraph.py` → `runtime/_time_travel.py` 是 L3 → L2 **合法方向**；
  门面 `freegraph.graph` 不新增导出（`update_state` 只是编译产物方法）。
- **L4**：`memory.py` / `sqlite.py` 的 `put` 仍只依赖 L1 + stdlib；显式父链是**行为扩展**，
  不新增公开符号；`from freegraph.persistence import ...` 面不变。
- **状态读取**：`get_state` / `get_state_history` 的组装路径**零改动**；新分支快照由同一
  `assemble_snapshot` 读取；`parent_config` / `tasks` / `interrupts` 自动一致。
- **测试基线**：见「Green Baseline & Red List」；实施后必须回到全绿（除上游缺席 skip）。

---

## Project Structure

### Documentation (this feature)

```text
specs/b16f1-update-state-time-travel/
├── plan.md                  # 本文件
├── research.md              # Phase 0 输出
├── data-model.md            # Phase 1 输出
├── quickstart.md            # Phase 1 输出
├── contracts/
│   ├── update-state-contract.md
│   ├── time-travel-contract.md
│   ├── put-parent-contract.md
│   └── upstream-parity.md
├── checklists/
│   └── requirements.md      # /speckit.specify 产物
└── tasks.md                 # /speckit.tasks 输出（不在本命令创建）
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/
│   └── protocols.py                 # L1 · 只改 update_state 的 config 注解 / 返回类别
├── _stategraph.py                   # L3 · update_state 真实实现（委托 L2）
├── runtime/
│   ├── _time_travel.py              # L2 新增 · 基准 / as_node / C6 / 后继 / put
│   ├── _state_read.py               # L2 既有 · 读取组装（零改动，复用）
│   ├── _checkpoint.py               # L2 既有 · 写盘助手（本 feature 零改动，复用 `_metadata` / `config_for_checkpoint`）
│   ├── _stream_checkpoint.py        # L2 既有 · stream 写盘父链推进
│   ├── _routing.py                  # L2 既有 · 条件边求值（复用）
│   ├── _fanout.py                   # L2 既有 · fan-out 编码（复用）
│   └── superstep.py                 # L2 既有 · _first_graph / _resume_graph / _run_graph_loop
└── persistence/
    ├── memory.py                    # L4 · put 显式父链
    └── sqlite.py                    # L4 · put 显式父链
```

```text
tests/
├── facade/
│   ├── test_b16f1_update_state.py           # 新增
│   ├── test_b16f1_time_travel.py            # 新增
│   ├── test_compiled_graph.py               # 修改冻结断言
│   └── test_facade.py                       # 修改冻结断言
├── runtime/
│   ├── test_b16f1_update_state_runtime.py   # 新增
│   ├── test_b16f1_replay_anchor.py          # 新增（anchor / 父链）
│   ├── test_b16f1_pending_protection.py     # 新增（pending 保护）
│   ├── test_b16f1_static_replay.py          # 新增
│   ├── test_b16f1_resume_latest.py          # 新增
│   ├── test_b16f1_manual_record_guard.py    # 新增（SC-013 文档守卫）
│   ├── test_b16f1_doc_guard.py              # 新增（SC-018 文档守卫）
│   └── test_conditional_edge_surface.py     # 修改冻结断言
├── persistence/
│   └── test_b16f1_put_parent.py             # 新增（双后端）
├── contracts/
│   └── test_b16f1_contracts.py              # 新增（L1 / 零依赖 / ARCH-1）
└── differential/
    └── test_b16f1_time_travel_parity.py     # 新增（D-01…D-17）
```

**Structure Decision**: 单项目 library；新代码落 **L2 `runtime/`**（执行内核）+
**L3 `_stategraph.py`**（门面实现）+ **L1 `contracts/protocols.py`**（唯一协议改动）+
**L4 `persistence/`**（`put` 父链扩展）。不新增层 / 不新增发行包 / 不新增公开符号。

---

## Design Decisions（摘要 · 详版见 [research.md](./research.md)）

| # | 决策 | 结论 | 理由 |
|---|---|---|---|
| **D-01** | `update_state` 的实现落点 | L3 委托 **L2 私有 `runtime/_time_travel.py`** | L4 不能应用归约器；L3 → L2 合法；复用 `superstep` 的调度 / 合并 / 路由 |
| **D-02** | 合并 / 后继的计算路径 | 复用 `_evaluate_source_routes` + `_commit_outcome` + `_merge_writes` + `_clear_step_end` + `_determine_triggers` | C6 / C8 只有一条路径；不写第二套归约 / 路由 |
| **D-03** | `as_node` 推断 | 镜像上游：省略且单节点 ⇒ 该节点；否则 `versions_seen`「最后更新者」；歧义 / 无历史 ⇒ `InvalidUpdateError`；MUST NOT 回退 `node_versions` | 上游 `main.py:1875-1935`；消息要点同款；`input_channels` 兜底列能力边界 |
| **D-04** | `as_node` 后继 | 出边 + 条件边 + fan-out（`Send`）按运行期同款求值；`next` = 标准触发目标；fan-out 落 `.scheduler["fanout"]` | 上游 node writers / `apply_writes`；B15F1 的 next-tasks 读取层 |
| **D-05** | 父链 | L4 `put` 显式父链扩展；L2 每次写盘用 `config_for_checkpoint(run_config, current_id)` 作 parent，写完推进 current | 上游 `put` 的 parent = config 的 checkpoint_id；分支内线性接续 |
| **D-06** | 重放起点校验 | 显式 `checkpoint_id` + `get_tuple` 为 `None` ⇒ `ValueError`；**仅该显式 id 分支**无 saver / `True` / `False` / 非空 `checkpoint_ns` ⇒ `ValueError`（消息含 `No checkpointer set` 或点名 ns）；**MUST NOT** 回退 latest / fresh；无显式 id 的普通 `invoke` 行为不变 | FR-003 / FR-010 / SC-004 / SC-017；显式失败优于静默污染，且不误伤普通运行 |
| **D-07** | branch anchor | 显式历史 id + **非 no-op**（`next` / fanout / 静态 / pending / 非空 input dict）⇒ 先写 anchor（parent=基准；values / next / 静态标记 / scheduler 同基准；`interrupts=()` / `tasks=()`）；**正常终态** + `input` 为 None / 空 dict 才 no-op 不写；`invoke(dict, historical.config)` 属 B7F3 续跑、同受 anchor 保护；**`update_state` 分支快照兼任 anchor ⇒ `invoke(None, fork_config)` 不再写额外 anchor**；分支快照的识别由 `update_state` 在 L2 侧记录 id / 内部账本私有标记承担，不改公开面 | **spec 裁定 10 / FR-026**；上游 `source="fork"`；保证首轮中断 / 真异常不写原快照；SC-014 |
| **D-08** | 恢复定位 | `Command(resume)` 只读该 thread **最新**快照 + pending writes；忽略旧 `checkpoint_id` | B10F1 FR-010；防旧 id 误写历史；spec X-04 |
| **D-09** | 静态 ack | replay 保留 ack（越过已确认断点）；`update_state` 清空 ack（新分支重新经过断点）；断点前 replay 因新写入再次触发 | B13F1 FR-007 + 上游 `versions_seen[INTERRUPT]` 水位 |
| **D-10** | `context` | 不读 / 不存 / 不还原 / 不透出；`snapshot.config.context is None` | B8F3 D-1 / D-3；spec X-03 |
| **D-11** | 失败信号 | 复用 `ValueError` / `TypeError` / `InvalidUpdateError`；消息点名 `thread_id` / `checkpoint_id` / 节点 / key | 不新增 L1 异常；裁定 8 |
| **D-12** | L1 改动 | 只改 `update_state` 的 `config` 注解 + 返回类别；其余五方法 / 字段面零改动 | 已获 R-1 追认；上游 `RunnableConfig` 形态 |
| **D-13** | stream 写盘 | 每次 `put` 用当前 id 作 parent；stream v1 仍忽略用户 config 的 `checkpoint_id` | 保持 B8F2「不恢复历史」；父链不因 put 扩展而错乱 |
| **D-14** | 测试 / 差分 | 单元 / facade / runtime / persistence / contracts / differential；D-02 比较执行不比较快照数（X-06） | 覆盖 A1–A3；上游缺席 skip |
| **D-15** | 文档 / 人工验收 | README / demo README / manual-verification；fake + 真实模型两轮 | FR-022 / FR-024；门禁 5 |

---

## Work Packages（供 `/speckit.tasks` 展开）

| WP | 内容 | 主要文件 | 依赖 | 判据 |
|---|---|---|---|---|
| **WP-1** | L1 协议 + L3 签名 | `contracts/protocols.py` · `_stategraph.py` | — | FR-001 / FR-018 · SC-006 |
| **WP-2** | L4 `put` 显式父链（双后端） | `persistence/memory.py` · `sqlite.py` | WP-1 | FR-017 · SC-007 |
| **WP-3** | L2 `update_state` 助手 | `runtime/_time_travel.py` | WP-1 / WP-2 | FR-004…FR-008 · SC-003 / SC-009 |
| **WP-4** | L3 `update_state` 接线 | `_stategraph.py` | WP-3 | FR-001 / FR-002 · SC-006 / SC-015 |
| **WP-5** | Replay 校验 + anchor + 父链推进 | `runtime/superstep.py`（复用 `_checkpoint.py` 既有助手，零改动） | WP-2 | FR-009 / FR-010 / FR-014 · SC-001 / SC-002 / SC-016 |
| **WP-6** | `Command(resume)` 最新定位 | `runtime/superstep.py` | WP-5 | FR-013 · SC-011 / SC-014 |
| **WP-7** | 静态 ack + stream 父链 | `runtime/superstep.py` · `_stream_checkpoint.py` | WP-5 | FR-011 · SC-011 / SC-017 |
| **WP-8** | 单元 / facade / runtime / persistence 测试 | `tests/**/test_b16f1_*`（冻结断言已在 Foundational T013 拆分） | WP-1…WP-7 | FR-023 · SC-001…SC-018 |
| **WP-9** | 差分 + 门禁 | `tests/differential/test_b16f1_*` · `harness/scripts/gates` | WP-8 | FR-023 · SC-012 · R-9 |
| **WP-10** | 文档 / 人工验收 / 下游接线 / 上游回溯修订 | `README.md` · `harness/demo/README.md` · `harness/verification/B16F1/**` · 下游提示词 · `specs/{b2f1-contracts-protocols,b14f1-checkpointer-memory-saver,b15f1-sqlite-saver-state-history,b7f3-invoke-full-state}/**`（含 `b7f3/contracts/invoke-contract.md`） | WP-8 | FR-022 / FR-024 · SC-013 / SC-018 · R-14 / R-16 |

### 实施顺序（关键路径）

1. **WP-1 → WP-2**：先把 L1 签名 / L4 父链打通，保证既有 2266 passed 基线不破坏。
2. **WP-3 → WP-4**：`update_state` 的合并 / 后继 / 返回 config 先单测绿。
3. **WP-5 → WP-6 → WP-7**：replay / resume / static 三条路径逐条接线；每步跑
   `tests/runtime/` + `tests/facade/` 子集。
4. **WP-8**：把 A1–A3 的判据全部落成测试；冻结断言已在 Foundational T013 拆分。
5. **WP-9**：差分 D-01…D-17；上游在场时真跑，缺席 skip。
6. **WP-10**：文档 / 人工验收 / 下游提示词；最后全量 pytest + 门禁。

---

## Green Baseline & Red List

**基线（2026-11-23 实跑）**：

```bash
.venv/bin/python -m pytest -q --tb=no
# ⇒ 2266 passed, 10 skipped in 123.23s
```

**预登记红点 / 必须拆分的冻结断言（宪法 v1.11.0：T001 MUST 实测复核）**：

> 下表是**推理预登记**。T001 MUST 在临时副本按本 feature 落地形态改动源码
> （`update_state` 落地 + `put` 父链扩展）⇒ 跑既有套件 ⇒ **实测采集变红断言**，
> 逐条核对 RED-1…RED-5 是否完整（缺失 ⇒ 补登记，带 `文件:行号` + 变红原因）。

| # | 位置 | 现值 | 变红原因 | 处置 |
|---|---|---|---|---|
| **RED-1** | `tests/facade/test_compiled_graph.py:76-78`（`test_each_unready_method_raises_not_implemented_naming_owner`） | 断言 `update_state` 抛 `NotImplementedError` + 点名 B16F1 | `update_state` 实现后不再抛 `NotImplementedError` | **拆分而不删**：保留历史注记；改为「无 saver ⇒ `ValueError`；有 saver ⇒ 返回 `RunConfig`」 |
| **RED-2** | `tests/facade/test_facade.py:234-236`（`test_compile_returns_a_product_but_capability_methods_are_not_implemented`） | 同上 | 同上 | 同上 |
| **RED-3** | `tests/runtime/test_conditional_edge_surface.py:102-111`（`test_the_unimplemented_protocol_methods_still_name_their_owner`） | 参数化含 `update_state` | `update_state` 改为抛 `ValueError` / 返回 `RunConfig`，原断言失败；移除后参数集为空 | 参数化列表移除 `update_state`；新增已实现正面断言 |
| **RED-4** | `tests/contracts/test_protocols.py:247`（`COMPILED_GRAPH_METHODS` / 返回类别区） | 未断言 `update_state` 返回类别 | **新增覆盖（非既有红点）**：T001 实测时应确认该处无遗漏 | **新增** `update_state` 返回 `RunConfig` / `config` 双形态注解断言 |
| **RED-5** | `tests/facade/test_facade_gates.py:466-581`（矩阵白名单 / 注释） | 仍写 `update_state` 未交付 | README 行更新可能触发矩阵白名单断言 | 只更新注释（`CompiledGraph` 行不在契约层矩阵比对集；若 README 行更新触发白名单，按需加 `MATRIX_ROWS_UPDATABLE_BY_B16F1`） |

> **基线纪律**：实施后 MUST 回到全绿（除上游缺席 skip）；MUST NOT 用「删判据 / 弱化断言」
> 换取绿；冻结断言只做「拆分而不删」。

---

## Risks & Mitigations

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| **RK-1** | 父链推进漏改某个 `put` 调用点（常态 / 挂起 / 静态完成 / stream） | 分支父链错乱 / 原父链被重排 | 统一经 `config_for_checkpoint(run_config, current_id)`；双后端父链测试 + 全量历史完整性测试 |
| **RK-2** | `as_node` 后继 / fan-out 求值与运行期不一致 | 分叉后跑错分支 / 漏任务 | 复用 `_evaluate_source_routes` + `_commit_outcome` + `_determine_triggers`；D-06 差分 |
| **RK-3** | replay / update_state 把 pending writes 写到原快照 | 历史污染（P3 失败） | branch anchor + `Command(resume)` 最新定位；SC-014 专项测试 |
| **RK-4** | 静态 ack 在 replay / 分叉两条路径混用 | 审批点被绕过 / 重放立即重挂 | replay 保留 ack、`update_state` 清空；B13F1 FR-007 回归 + D-17 |
| **RK-5** | L4 `put` 扩展改变既有调用行为 | B14F1 / B15F1 回归红 | 「显式 id 才生效」；既有调用零变化；双后端 + 全量 pytest |
| **RK-6** | 上游 final replay 写 fork checkpoint 与 spec SC-016 不一致 | 差分误判 | D-02 只比执行 / 终态；X-06 已落 spec；**不**把快照数当判据 |
| **RK-7** | 新 L2 模块被层门禁判「未登记 / 反向 import」 | G25 红 | 放在 `runtime/` 目录条目下（L2）；不 import L4；设计后复核 |
| **RK-8** | 行数超预算 | 交付延期 | tasks 行数预算如实登记；不削减 FR / SC；必要时拆 WP |

---

## Verification Plan

| 层 | 命令 / 证据 | 覆盖 |
|---|---|---|
| **单元 / 契约** | `pytest tests/contracts/test_b16f1_contracts.py tests/contracts/test_protocols.py -q` | L1 注解 / 返回类别 / 零依赖 / ARCH-1 |
| **Facade** | `pytest tests/facade/test_b16f1_update_state.py tests/facade/test_b16f1_time_travel.py -q` | 签名 / 重放 / 分叉 / 历史完整性 / 错误 |
| **Runtime** | `pytest tests/runtime/test_b16f1_* -q` | 后继 / 静态 / resume / 文档守卫 |
| **文档守卫** | `pytest tests/runtime/test_b16f1_manual_record_guard.py tests/runtime/test_b16f1_doc_guard.py -q` | SC-013 / SC-018 |
| **Persistence** | `pytest tests/persistence/test_b16f1_put_parent.py -q` | 双后端父链 / 既有行为 |
| **上游回溯修订** | 文档核对：`specs/b2f1-contracts-protocols/{spec,data-model}.md` · `specs/b14f1.../spec.md` 裁定 6 · `specs/b15f1.../spec.md` 裁定 4/5 · `specs/b7f3.../spec.md` CF-05 · `specs/b7f3.../contracts/invoke-contract.md` | R-16（核对已落 + 拆分而不删） |
| **Differential** | `pytest tests/differential/test_b16f1_time_travel_parity.py -q` | D-01…D-17；上游缺席 skip |
| **全量** | `.venv/bin/python -m pytest -q --tb=no` | 2266+ 基线 → 全绿 |
| **门禁** | 既有 G3 / G7 / G8 / G16 / G18 / G19 / G21 / G22 / G23 / G24 / G25 / G26 / G27 / G30 | 零新增依赖 / env / 出站 / 层方向 / 门面 |
| **人工验收** | `harness/verification/B16F1/manual-verification.md` | 五段式 + fake + 真实模型 + 追认文字（R-1） |
| **Demo** | `harness/demo/README.md` 锁定说明 | FR-022 / SC-018 |

---

## Complexity Tracking

> **无宪法违规需要豁免**。本 feature 不新增层 / 不新增发行包 / 不新增公开符号 / 不新增门禁编号；
> 唯一 L1 改动（`update_state` 返回类别 + config 注解）已按 R-1 登记并获发起者追认。
> 唯一 parity 事实订正 = **X-06**（上游 final replay 的 fork checkpoint 与 SC-016 的差异）；**已落 spec**；归入自研区 **②（上游文档/实现不一致）**。

---

## Post-Design Constitution Re-Check

- **原则 I / II**：零新增依赖；L2 新文件不 import L3 / L4 / L5；L4 不 import L2 / L3；
  差分测试的上游 import 只在 `tests/`。✅
- **原则 III**：`target.py` 零改动；C4 / C6 / C8 回归保持。✅
- **原则 IV**：重放 + 分叉 + 中断 / 静态组合均可达；`get_state_history` 仍是唯一历史枚举口径。✅
- **原则 V**：manual-verification 五段式 + fake + 真实模型；B25F1 只复验。✅
- **原则 VI**：FR / SC / A1–A3 的可判定承载已在 spec；tasks 将逐条挂测试。✅
- **原则 VII / VIII / IX / X**：职责边界 / 证据 / 许可证 / 署名头无新增偏离；
  **不复制上游代码** ⇒ `THIRD_PARTY_NOTICES` 不变。✅
- **原则 XI / XII**：P-01…P-23 / X-01…X-06 已对照；X-06 是唯一 parity 订正项（已落 spec）；
  复用既有载体 / 调度账本 / 合并路径。✅

---

## Downstream Handoff（本 feature → 下游）

| # | 承接方 | 动作 |
|---|---|---|
| **D-01** | **B24F1** | API 兼容矩阵增加 `CompiledGraph.update_state`（`RunConfig` 返回 · `as_node` · 无 `task_id`）与时间旅行 / 分叉行 |
| **D-02** | **B25F1** | 双跑验收覆盖历史点重放 / 分叉 / 合并 / 中断组合；对真实模型轮做跨 feature 复验 |
| **D-03** | **B26F1（v2 UI）** | 只消费 `get_state_history` + `invoke(None, config)` + `update_state`；不新增私有接口 |
| **D-04** | **Postgres v2** | 复用 `put` 显式父链扩展与同一时间旅行语义；不另造 id 空间 |
| **D-05** | **B20F1 / B20F2** | checkpoint 与 trace 两套存储；时间旅行不写 trace 存储 |

---

## 完成判据

- [X] `update_state` 签名 / 返回类别 / `as_node` / C6 合并全部落地（A3）
- [X] 任意历史 checkpoint 重放（含**正常终态** no-op）；非 no-op replay / 历史续跑写 branch anchor；`update_state` 分支快照兼任 anchor，分叉后不再写额外 anchor（A1 / FR-026）
- [X] 分叉后原历史 8 字段 + pending writes 零变化（A2）
- [X] 静态 / 动态中断与时间旅行组合落地（SC-011 / SC-014）
- [X] 双后端父链一致；既有普通运行语义零变化（SC-007 / SC-017）
- [X] 差分 D-01…D-17 / 全量 pytest / 门禁绿
- [X] 上游 spec / data-model 回溯修订**核对已落 + 补齐遗漏**（T056，含 `invoke-contract.md`）与 SC-018 文档守卫（T057）
- [X] manual-verification 五段式 + fake + 真实模型两轮 + R-1 追认文字
- [X] README / demo README 更新；`target.py` 零改动
