# Implementation Plan: B15F1 · `SqliteSaver` + `get_state` / `get_state_history`

**Branch**: `b15f1-sqlite-saver-state-history`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_plan` 钩子；既有 feature 同样在 `main` 上开发）

**Date**: 2026-11-22（2026-11-23 修订） | **Spec**: [spec.md](./spec.md)（**唯一权威** · 含 **6** 条 clarify 拍板（2026-11-22 ×3 + 2026-11-23 ×3）+ **13** 条形态锁定裁定 + **37** 条 FR + **27** 条 SC）

**Input**: Feature specification from `specs/b15f1-sqlite-saver-state-history/spec.md`

**Feature ID**: `B15F1`（M3 可诊断 · **第 28 个**（对齐 `harness/features/README.md` 开发序）· 前置：**B14F1**；承接 **B10F1 / B12F1 / B11F1 / B13F1 / B8F3 / B14F1 / B7F3 / B8F2**）

> **范围提醒**：本 feature 是 **L4 持久化层的磁盘后端** + **L1 `CompiledGraph` 的对外状态读取面** +
> **`checkpoints` 流式档的消费端**。
> **不实现** `update_state` / 时间旅行（B16F1）· `Store`（B17 已砍）· Postgres / async（v2）·
> trace 存储（B20F1 / B20F2）· 子图（C26 · v2）· 运行级删除 / 线程复制（v1 继续 `NotImplementedError`）。
> **MUST NOT** 改变图执行语义；**MUST** 保持运行时依赖闭包为空集。
> `StateSnapshot` 8 字段、`Checkpointer` 8 方法、`RunConfig` 9 字段、`Interrupt` / `PregelTask`
> 字段面、门面符号面 **一律不改**；L1 只放宽 `get_state` / `get_state_history` 的 `config` 注解；
> **L1 方法签名参数个数不变**（`filter` / `before` / `limit` 是 L3 实现体的 keyword-only 扩展）。

---

## Summary

交付三件事：

| # | 交付物 | 语义 | 关键规则 |
|---|---|---|---|
| **①** | **`freegraph.persistence.SqliteSaver`** | 标准库 `sqlite3` 的磁盘 checkpointer | 上游同款 `SqliteSaver(conn)` / `from_conn_string(...)`；单连接 + `threading.Lock` + WAL；`:memory:` 支持；8 方法协议；**复用 B14F1 的 id 空间 / 写侧关键字 / `CheckpointTuple` 三字段** |
| **②** | **`CompiledGraph.get_state` / `get_state_history`** | 对外状态读取面 | `config` 接受 `RunConfig \| Mapping \| None`；最新 / 按 id；历史按 `checkpoint_id` **倒序**；`values` 的 pending 合并按上游（无 id 合并 / 有 id 不合并）；`tasks` 采用上游 **next-tasks** 语义（`next` + `.scheduler["fanout"]` + pending `__interrupt__`），`interrupts` 按任务顺序展平 |
| **③** | **`stream(..., stream_mode="checkpoints")` 消费端** | 本次运行产生的 checkpoint 事件 | 四键信封 + `payload = StateSnapshot`；每次成功 `put` 一条；无 saver / 无 `thread_id` ⇒ 0 条；**不**伪造历史 |

**技术路线（零第三方依赖 · 零出站 · 零环境变量）**：

| 环节 | 落点 |
|---|---|
| L4 公开面 | **新增** `src/freegraph/persistence/sqlite.py`；`__init__.py` 只增 `SqliteSaver` |
| 序列化 | **新增** `src/freegraph/persistence/_json.py`：纯数据 JSON 编码 / 解码；`tuple` → list；`Interrupt` / `PregelTask` 重建 |
| 上游移植 | 以 `langgraph-checkpoint-sqlite 3.1.1`（MIT · uv 缓存）的**同步** `SqliteSaver` 为蓝本：`setup()` / WAL / `cursor()` / `from_conn_string` / `threading.Lock`；**替换** serde 为 JSON；**保留** B14F1 的 `put` 关键字 / id 生成 / `task_path` 排序 |
| 状态读取 | **新增** L2 私有 `src/freegraph/runtime/_state_read.py`：config 校验 / saver 校验 / pending 合并 / **next-tasks 重建**（`next` + `.scheduler["fanout"]`）/ `interrupts` 投影 / 历史组装（由 L3 `_stategraph` 调用；L2 与 `superstep.py` / `_recursion.py` 同一层注册条目，内部 import 不产生层边） |
| pending 合并 | **新增** L2 私有 `merge_pending_writes(spec, values, pending_writes)`（放在 `runtime/superstep.py`，复用 `_restore_channels` + `Channel.update`） |
| 流式写盘 | **新增** L2 私有 `src/freegraph/runtime/_stream_checkpoint.py`：`StreamCheckpointWriter`（初始 / 每轮 / 挂起 / 错误轮写盘 + 读回快照） |
| 流式接线 | **修改** `runtime/_stream.py`（可选 saver / writer）· `_stategraph.py`（`stream` 传 saver；`_stream_events` 发 `checkpoints` 事件） |
| L1 注解 | **修改** `contracts/protocols.py` 的 **2 处** `config` 注解；L1 方法签名（参数个数）**不变**；走「登记 + 回溯修订 + 发起者追认」 |
| 测试 | 新增 `tests/persistence/` + `tests/runtime/test_b15f1_*` + `tests/contracts/test_b15f1_*` + `tests/differential/test_b15f1_*`；修改 3 处「未实现」冻结断言 + 1 处 `__all__` |
| 人工验收 | **新增** `harness/verification/B15F1/manual-verification.md`（五段式 + 跨进程 / 历史枚举 / 中断投影 / 并发） |
| 文档 | `README.md` 的 `CompiledGraph` / `Checkpointer` 行更新；**不新增**兼容矩阵行（B24F1 定稿） |

**明确边界（不是偏离，是能力边界）**：

- `stream` 只有 **`checkpoints` mode** 才写 saver；其它六档保持 B8F2 v1 的「忽略 checkpointer」语义。
- `stream + saver` **不恢复历史**（B8F2 v1 的 input 规则不变）；只把本次运行的新快照追加到该 thread。
- `stream` 仍拒绝静态断点 / `Command` 输入（B8F2 v1 口径不变）。
- `SqliteSaver` 的 `delete_for_runs` / `copy_thread` 继续 `NotImplementedError`。
- `SqliteSaver` 的 schema / SQL / 索引 / `created_at` 存储方式属内部实现细节。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（本机 `.venv` 3.11.16）；只用标准库
`sqlite3` / `json` / `os` / `pathlib` / `re` / `threading` / `datetime` / `contextlib` /
`collections.abc` / `dataclasses` / `typing`。**MUST NOT** 使用 3.12+ 的
`override` / `TypeIs` / `TypeAliasType` / PEP 695。

**Primary Dependencies**: **零第三方运行时依赖**（`dependencies = []`）。
开发期 `pytest` 既有；差分侧仅钉 `langgraph==1.2.11`（`.venv` 已装）。
`langgraph-checkpoint-sqlite 3.1.1` 源码在 uv 缓存中，**不安装进 `.venv`**；
`pyproject.toml` **零改动** ⇒ G3 / G21 / G23 恒绿。

**Storage**: 本地 **SQLite 文件**（或 `:memory:`）· 单连接 + 每实例锁 + WAL。
本地 trace 的 SQLite（B20F2）是**另一套存储**，MUST NOT 共用表 / 文件 / 连接。

**Testing**: pytest ——
`tests/persistence/test_sqlite_saver.py`（协议 / CRUD / list / delete / 版本 / 生命周期）·
`tests/persistence/test_sqlite_saver_failures.py`（失败 / 原子性 / filter 校验）·
`tests/persistence/test_sqlite_saver_json.py`（JSON / tuple / `Interrupt` / `PregelTask`）·
`tests/persistence/test_sqlite_saver_concurrency.py`（同实例多线程 · Windows 必跑）·
`tests/persistence/test_b15f1_cross_process.py`（子进程取回）·
`tests/facade/test_b15f1_state_read.py`（`get_state` / 历史 / pending 合并 / tasks / interrupts / config）·
`tests/runtime/test_b15f1_stream_checkpoints.py`（`checkpoints` 事件）·
`tests/contracts/test_b15f1_contracts.py`（导出 / 依赖方向 / L1 注解 / 零 env / 零出站）·
`tests/runtime/test_b15f1_manual_record_guard.py`（SC-020 文档守卫）·
`tests/differential/test_b15f1_state_parity.py`（D-01…D-21；上游不可导入 ⇒ skip）。

**Target Platform**: Linux / macOS / Windows · CPython 3.11+ · 零出站。
`sqlite3` 的 WAL / 文件锁在 Windows 上由现有 `windows-2025` CI 真跑。

**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A（不设墙钟预算）**。v1 以**正确性 / 上游对齐**优先；
本 feature 不设吞吐 / 延迟断言；MUST NOT 用耗时做 CI 断言。

**Scale/Scope**: 低并发（同实例多线程 + 少量实例）· 单文件 SQLite · 快照数 = 每线程
`put` 次数 · 历史枚举无分页（`limit` 由调用方给）。**不承诺**高并发 / 跨进程严格串行。

**Constraints**（主要来自 spec）：

| 约束 | spec 条目 |
|---|---|
| 零第三方 / 零 env / 零出站；L4 只**依赖** L1 + 标准库（同层内部 import 按层注册表允许） | FR-002 · SC-005 |
| 上游同款 `SqliteSaver(conn)` / `from_conn_string`；`:memory:`；单连接 + 锁 + WAL | FR-003 / FR-004 / FR-011 · 裁定 2 |
| 读侧三字段 / 写侧五关键字 / `put_writes` 目标 / 去重 / 排序复用 B14F1 | FR-006 / FR-007 / FR-008 · 裁定 5 |
| checkpoint id 复用 B14F1（每线程 32 位单调 + 父链） | FR-009 · 裁定 4 |
| 纯数据 JSON；tuple / `Interrupt` / `PregelTask` 重建；非 JSON ⇒ `TypeError` | FR-005 · 裁定 3 · X-05 |
| `get_state` 无 id 合并 pending / 有 id 不合并；历史不合并 | FR-015 / FR-017 · 裁定 8 · SC-025 |
| `tasks` 为上游 next-tasks（`next` + `.scheduler["fanout"]`）；`interrupts` 按任务顺序展平；节点名序 / TaskId 序 | FR-018 / FR-037 · 裁定 8 / 13 · SC-008 / SC-027 |
| 历史按 `checkpoint_id` 倒序；条目数 == `put` 次数 | FR-017 · 裁定 9 · SC-001 |
| 无 saver / 缺 `thread_id` / 非空 `checkpoint_ns` 的失败信号 | FR-014 · SC-015 |
| `stream(checkpoints)` 四键信封 + `StateSnapshot` payload；无伪造 | FR-022 · 裁定 10 · SC-014 |
| L1 只放宽 2 处 `config` 注解；无新 L1 异常 | FR-023 / FR-036 · SC-023 |
| 并发 / Windows；`database is locked` 不泄漏 | FR-011 / FR-027 · SC-004 |
| 跨进程持久化子进程用例 | FR-028 · SC-003 / SC-019 |
| 人工验证五段式 | FR-029 · SC-020 |
| 差分 D-01…D-21；上游缺席 skip | FR-026 · SC-018 |

> **无未决澄清**：spec 的 6 条 clarify 拍板（2026-11-22 ×3 + 2026-11-23 ×3） + 13 条形态锁定裁定已收敛全部未决点；
> 本 plan 只落设计决策与实现顺序。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| **原则 I · 零 LangSmith / 零出站 / 零环境变量** | 零新增依赖；无 env / 网络 / 出站；G24 / G26 / G27 | ✅ 通过 |
| **原则 II · 内核纯净** | 不 import `langchain*` / `langgraph*` / `langsmith`；L4 只依赖 L1 + stdlib（同层内部 import 允许）；L2 状态读取（`runtime/_state_read.py`）不 import L4；L3 `_stategraph` 只 import L2 | ✅ 通过 |
| **原则 III · 验收契约优先** | `harness/demo/target.py` **零改动**；门面 8 符号面零改动；C4 / C6 / C8 回归保持 | ✅ 通过 |
| **原则 IV · 可诊断性** | `get_state` / `get_state_history` 可枚举；`tasks` 承载节点名；恢复仍必须挂 saver；`checkpoints` 事件可消费 | ✅ 通过 |
| **原则 V · 人工验收** | `harness/verification/B15F1/manual-verification.md` 五段式 + 跨进程 / 并发实测 + **fake 轮 + 真实模型轮（本 feature 自跑；B25F1 仅复验）** | ✅ 计划交付（门禁 5 合规） |
| **原则 VI · 规格驱动** | spec FR-001…FR-037 / SC-001…SC-027 全部可追溯；tasks 由 `/speckit.tasks` 展开 | ✅ 通过 |
| **原则 VII · 职责边界** | 只做 C19 的 SQLite 实现 + C10 的状态读取 + `checkpoints` 档；不做 Store / 时间旅行 / Postgres / async | ✅ 通过 |
| **原则 VIII · 证据与术语** | spec P-01…P-25 / D-01…D-21 / X-01…X-08 带版本 + `路径:行号`；术语「快照 / pending writes / 调度账本 / 顺位 id」统一 | ✅ 通过 |
| **原则 IX · 许可证 / 商标** | 新增代码 = 对 `langgraph-checkpoint-sqlite 3.1.1`（MIT）同步 saver 的**改编** ⇒ `THIRD_PARTY_NOTICES` §1 增加 1 条归属（保留原始版权 / 许可）；运行时依赖仍为零；不复制其 `aiosqlite` / `sqlite-vec` / `langchain_core` 依赖 | ✅ 通过（§1 登记） |
| **原则 X · 文档 / 署名头** | 新增 L4 / L3 / L2 文件带**本项目**署名头；`THIRD_PARTY_NOTICES` §1 保留上游 MIT 版权；README 更新；`manual-verification.md` | ✅ 计划交付 |
| **原则 XI · 上游优先** | 25 条语义点逐条对照；X-01 / X-03 / X-04 / X-05 / X-07 / X-08 有效偏离已登记（**X-04 仅指 `checkpoints` 事件载荷**；`__start__` 排除不占编号）；X-02 / X-06 已撤销；差分 D-01…D-21；**`tasks` 采用上游 next-tasks**（R-13） | ✅ 通过（含已登记偏离） |
| **原则 XII · 最优设计优先** | 复用 B14F1 载体（`StateSnapshot` / `CheckpointTuple` / 调度账本）；不另造第二套快照 / id；**`tasks` 彻底改为上游 next-tasks**（2026-11-23 决策），`PregelTask` 复用 L1 已有类型 | ✅ 通过 |

### 登记项（**plan 阶段必须如实登记**）

| # | 类别 | 内容 | 处置 | 追认 |
|---|---|---|---|---|
| **R-1** | **消解 B15F1 的冻结断言** | `tests/facade/test_compiled_graph.py::test_each_unready_method_raises_not_implemented_naming_owner`、`tests/runtime/test_conditional_edge_surface.py::test_the_unimplemented_protocol_methods_still_name_their_owner`、`tests/facade/test_facade.py::test_compile_returns_a_product_but_capability_methods_are_not_implemented` 都断言 `get_state` / `get_state_history` 抛 `NotImplementedError` ⇒ 本 feature 后**必红** | **拆分而不删**：保留 `update_state` 的「未实现 + 点名 B16F1」断言；`get_state` / `get_state_history` 改为「已实现」正面断言（无 saver ⇒ `ValueError`；有 saver ⇒ 返回 `StateSnapshot`） | **不需要**（属宪法 v1.11.0 基线 / 冻结断言拆分，**不占 v1.9.0 追认额度** · 不是门禁偏离 · 不是 L1 冻结面） |
| **R-2** | **导出面精确集合** | `tests/contracts/test_b14f1_contracts.py` 断言 `persistence.__all__ == ["MemorySaver","InMemorySaver","CheckpointTuple"]`；并断言门面无 `MemorySaver` | **只增不改**：新增 `SqliteSaver`；门面同时断言无 `SqliteSaver`；既有 3 符号逐字保留 | **不需要**（只增 · 不占追认额度） |
| **R-3** | **L1 `config` 注解放宽** | `contracts/protocols.py:288-290` 的 `get_state` / `get_state_history` 仍为 `RunConfig`；spec H-9 要求本 feature 走「登记 + 回溯修订 + 发起者追认」 | 改为 `RunConfig \| Mapping[str, Any] \| None`；**L1 方法签名（参数个数）不变**：`get_state_history` 的 `filter` / `before` / `limit` 只是 L3 实现体的 keyword-only 扩展；同步 `_stategraph.py` 方法注解；在 `specs/b2f1-contracts-protocols/spec.md` 的签名表「拆分而不删」；追认文字落 `harness/verification/B15F1/manual-verification.md` | **本 feature 落地时登记**（每 feature 追认 ≤ 1 次） |
| **R-4** | **B8F2 `checkpoints` 档边界（含 FR-028）** | B8F2 v1 的 `checkpoints` 恒空；且 B8F2 **FR-028** 要求 `StreamSession` MUST 忽略 `checkpointer`（不读/写快照）——现行原文为「**非 `checkpoints` 六档**语义不得被改变」。`tests/facade/test_stream_modes.py::test_checkpoints_and_messages_are_empty` 在**无 saver** 时仍应通过 | **拆分而不删**：无 saver / 无 `thread_id` ⇒ 仍 0 条；有 saver + `thread_id` ⇒ 本次运行每 `put` 一条；**非 `checkpoints` 六档语义零改动**。B8F2 **FR-028**（及其 `SC`）按 spec「破冻结面回溯修订清单」改为「六档忽略 + `checkpoints` 档 carve-out」（与 B14F1 H-8 同源），由 T057 落地 | **本 feature 登记**（B8F2 冻结面回溯 · spec 回溯修订清单） |
| **R-5** | **stream 不恢复历史** | B8F2 v1 的 `stream` 不恢复执行 / 不触发恢复；本 feature 只补 `checkpoints` 写盘。⚠️ writer 的 `prepare()` **允许**读最新 `checkpoint_id` 以设置本次首条快照的父链（这不是恢复） | 锁定：`stream` 只在 `"checkpoints" in modes` 时写 saver；**不恢复历史 / 不把历史快照并入本次事件**、不改变 `input` / 静态断点 / `Command` 的既有边界；只追加本次运行快照。**spec FR-022 / 裁定 10 已写明该边界** | **不需要**（能力边界 · 已写入 spec） |
| **R-6** | **pending writes 的只读合并** | `get_state` 需要把 pending writes 合并进 `values`，但 L4 不能应用归约器；L3 可依赖 L2 | 新增 L2 私有 `merge_pending_writes(spec, values, pending_writes)`：重建通道 → 按 `.pending_writes` 顺序 `Channel.update` → 稀疏读；**不推进版本 / 不写存储**；未知 key ⇒ `InvalidUpdateError`（与运行期同款） | **不需要**（L3 复用 L2 · ARCH-1 不变） |
| **R-7** | **stream 写盘的落点** | `_stream_tick` 当前只跑单轮，不写 saver；`run_graph` 的写盘逻辑在 `_run_graph_loop` | 新增 L2 私有 `StreamCheckpointWriter`，复用 `put_initial` / `put_step` / `_write_suspend` / `put_error_interrupts` / `_determine_triggers`；**不**改 `_stream_tick` 的既有签名（新增 writer 包装）。**spec H-7 / FR-022 已允许**该私有 writer 与 `get_tuple(written)` 等价读回 | **不需要**（私有实现 · 行为面只增 checkpoints） |
| **R-8** | **文件权限 / 生命周期** | spec 选择上游口径：跟随 OS 默认 / umask；`from_conn_string` 关闭连接；`SqliteSaver(conn)` 不关闭调用方连接 | 不额外收紧 `0o600`；不提供额外 `close()`；`from_conn_string` 用 `closing(...)` | **不需要**（spec 已锁定） |
| **R-9** | **行数 / 范围登记** | 立项书 1,240 行（实现 620 / 测试 620）；**2026-11-23 next-tasks 重建 + B14F1 回溯修订**已扩大范围 ⇒ 实际规模必然上调 | 实施期实测；在 tasks 的行数预算表**如实登记**（预估 +200~400 行测试 / 实现）；**不削减任何 FR / SC** | **已登记（实施期复核）** |
| **R-10** | **零新增门禁编号** | 本 feature 不新增 G 编号；只复用既有 G3 / G7 / G8 / G16 / G18 / G19 / G21 / **G22** / G23 / G24 / G25 / G26 / G27 / G30。**执行口径**：G21 / **G22** / G23 / G24 / G25 / G26 / G27 / G30 由 tasks T061 显式运行；G8 / G30 另由 T065 复核；G3 / G7 / G16 / G18 / G19 由全量 `pytest` 的既有契约 / 门禁用例**隐式覆盖**（不另设独立入口） | 计划 / 任务 / 实现均不得引入新门禁编号 | **不需要** |
| **R-11** | **第三方代码归属** | 同步 SQLite saver 的存储 / 连接 / WAL / setup / filter 代码改编自 `langgraph-checkpoint-sqlite 3.1.1`（MIT） | `THIRD_PARTY_NOTICES` §1 增加一行：项目 / 来源 / `MIT` / 「改编」/ 修改说明 / 原始版权声明；**不**新增运行时依赖；源文件仍带本项目署名头 | **计划交付**（原则 X） |
| **R-12** | **质量门禁 5 合规** | 宪法原则 V / 立项书 §9.1 门禁 5 要求人工验证含真实模型一轮；B15F1 具备运行时前置，MUST 自跑真实模型轮 | **不登记偏离**：B15F1 执行 fake 轮 + 真实模型轮；真实模型轮使用 `harness/demo/target.py` 或等价固定脚本，记录模型端点 / 调用次数 / 零出站归因；**B25F1 只做跨 feature 复验**（不是替代）；`tasks.md` T058/T059/T067 守卫 | **已确认（发起者 2026-11-23 选择「B15F1 补真实模型轮」）** |
| **R-13** | **破 B14F1 的 `tasks` 冻结面（next-tasks）** | 2026-11-23 决策：`StateSnapshot.tasks` 彻底改用上游 next-tasks（原则 XII 最优设计 + 原则 XI 上游优先）。B14F1 的「每轮完成态 / 挂起 `tasks=()`」降级为**存储 / 流数据源**；`get_state` / `get_state_history` / `stream(checkpoints)` 在**读取层**重建 next-tasks | **拆分而不删**：B14F1 spec 保留原存储口径 + 新增 carve-out；B8F2 `stream(tasks)` 仍为完成态；B15F1 的 `_state_read.assemble_tasks` 以 `next` + `.scheduler["fanout"]` + pending 为准；差分 D-01/D-03/D-21 改为 next-tasks 投影 | **并入本 feature 唯一一次追认**（与 R-3 同一次；每 feature ≤ 1 次） |
| **R-14** | **下游承接接线（原则 VII v1.8.0）** | spec 的「下游承接」D-01…D-03（B16F1）/ D-04（B24F1）/ D-06（B20F2）属跨 feature 义务，按接线通则 MUST 写入目标 feature 提示词初稿 | 由 **T070** 在 `harness/features/B16F1_update_state与时间旅行.md` / `B24F1_打包分发与兼容矩阵.md` / `B20F2_Trace查询API与SQLite后端.md` 各增「下游承接（B15F1）」节（只接线 · 逐条最小改动）；**不新增门禁编号** | **不需要**（登记项 · 不占追认额度） |

### 质量门禁 5 合规执行（2026-11-23 · 发起者选择「B15F1 补真实模型轮」）

| 项 | 内容 |
|---|---|
| 门禁项 | 宪法原则 V / 立项书 §9.1 门禁 5「人工验证记录含真实模型一轮」 |
| 执行方式 | B15F1 **自跑** fake 轮 + 真实模型轮；真实模型轮使用 `harness/demo/target.py` 或等价固定脚本 |
| 证据要求 | 模型端点 / 调用次数 / 零出站归因写入 `manual-verification.md`；去 `LANGSMITH_*` 干净环境；socket 只观测不阻断 |
| 判据 | 门禁 5 **不偏离、不放宽**；持久化 / 跨进程 / 历史 / 中断 / 并发 / 零出站 / 零 env 判据一字未改 |
| 承接方 / 机制 | **B25F1（M4 · 双跑验收）** 对本 feature 的证据做跨 feature **复验**（不是替代）；承接条款写入 `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B15F1）」，由 T067 写入 / T059 守卫 |
| 确认 | 发起者 2026-11-23 **选择「B15F1 补真实模型轮」**；确认文字由发起者本人签署 |

### 设计后复核（Phase 1 后 · 模板要求「Re-check after Phase 1 design」）

- **L4 依赖方向**：`persistence/sqlite.py` / `_json.py` 只依赖 `freegraph.contracts`（L1）+ stdlib；
  同层内部模块（`._types` / `._json`，以及从 `.memory` 复用 `_WRITES_IDX_MAP`）import 按层注册表允许
  ⇒ G25 预期绿；L2 / L3 **不** import `freegraph.persistence`（鸭子类型 / 协议）⇒ 依赖边保持单向。
- **L2 / L3 状态读取落点（G25 关键）**：`runtime/_state_read.py` 归 **L2**（与 `superstep.py` /
  `_recursion.py` **同一注册条目** ⇒ 内部 import 不产生层边）；`_stategraph.py`（L3）→ L2 是**合法方向**。
  ⚠️ **MUST NOT** 把 `_state_read.py` 放在顶层 `src/freegraph/`：顶层目录条目默认 **L1**，其 import L2
  会被 G25 判「反向 import」；也不得登记为独立 L3 文件条目 —— 否则 `_stategraph.py`(L3)→`_state_read.py`(L3)
  会触发「L3 同层横向依赖」⇒ 二者都会使 G25 变红。
- **门面**：`freegraph.graph` 不转出 `SqliteSaver`（G18）⇒ 门面符号面零改动。
- **冻结面**：`StateSnapshot` / `Checkpointer` / `RunConfig` / `Interrupt` / `PregelTask` 字段面零改动；
  唯一改动 = **2 处** `config` 注解（R-3）。
- **读侧语义**：`get_state` 无 id ⇒ pending 合并；有 id ⇒ 不合并；历史 ⇒ 不合并；
  `tasks` 为上游 **next-tasks**（`next` + `.scheduler["fanout"]` + pending `__interrupt__`；
  `id` / `name` / `path` / `interrupts` 按裁定 13）；`interrupts` 按任务顺序展平、无任务中断回退
  `snapshot.interrupts`；**不使用** B14F1 的完成态 `snapshot.tasks`。
- **写侧语义**：`put` 8 字段按 B14F1 组装；`put_writes` 目标由 `configurable["checkpoint_id"]` 指定；
  去重 / 排序逐字 B14F1；`context` 不持久化。
- **流式语义**：`checkpoints` 事件只在 `"checkpoints" in modes` + saver + `thread_id` 时产生；
  其它 mode 的既有事件序列零改动；无 saver / 无 `thread_id` ⇒ 0 条。
- **测试基线**：见下文「Green Baseline & Red List」；实施后 MUST 回到全绿（除上游缺席的 skip）。

---

## Project Structure

### Documentation (this feature)

```text
specs/b15f1-sqlite-saver-state-history/
├── plan.md                  # 本文件
├── research.md              # Phase 0 输出
├── data-model.md            # Phase 1 输出
├── quickstart.md            # Phase 1 输出
├── contracts/
│   ├── sqlite-saver-contract.md
│   ├── state-read-contract.md
│   ├── checkpoints-stream-contract.md
│   └── upstream-parity.md
├── checklists/
│   └── requirements.md      # /speckit.specify 产物
└── tasks.md                 # /speckit.tasks 输出（不在本命令创建）
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/                       # L1 · 只改 2 处注解
│   ├── types.py                     # StateSnapshot / RunConfig / Interrupt / PregelTask（零改动）
│   └── protocols.py                 # get_state / get_state_history 的 config 注解放宽（R-3）
├── persistence/                     # L4 · 修改 / 新增
│   ├── __init__.py                  # __all__ 增加 SqliteSaver（R-2）
│   ├── _types.py                    # CheckpointTuple（零改动）
│   ├── _json.py                     # 新增：JSON 编码 / 解码 / tuple / Interrupt / PregelTask
│   ├── memory.py                    # MemorySaver（零改动）
│   └── sqlite.py                    # 新增：SqliteSaver（上游移植 + B14F1 适配）
├── runtime/                         # L2 · 新增 / 修改
│   ├── _checkpoint.py               # 既有 B14F1 助手（零改动 / 只复用）
│   ├── _state_read.py               # 新增 L2：状态读取组装（与 superstep/_recursion 同条目）
│   ├── _stream_checkpoint.py        # 新增：StreamCheckpointWriter（流式写盘）
│   ├── _stream.py                   # 修改：可选 saver / writer / run_table
│   └── superstep.py                 # 修改：新增 merge_pending_writes（只读合并）
├── _stategraph.py                   # L3 · 修改：get_state / get_state_history / stream 接线
└── graph.py                         # 门面 · 零改动（不转出 L4）

tests/
├── persistence/
│   ├── test_sqlite_saver.py
│   ├── test_sqlite_saver_json.py
│   ├── test_sqlite_saver_failures.py
│   ├── test_sqlite_saver_concurrency.py
│   └── test_b15f1_cross_process.py
├── runtime/
│   ├── test_b15f1_stream_checkpoints.py
│   ├── test_b15f1_manual_record_guard.py
│   └── test_conditional_edge_surface.py   # 修改（R-1）
├── contracts/
│   ├── test_b15f1_contracts.py            # 新增
│   └── test_b14f1_contracts.py            # 修改（R-2）
├── facade/
│   ├── test_b15f1_state_read.py           # 新增
│   ├── test_compiled_graph.py             # 修改（R-1）
│   └── test_facade.py                     # 修改（R-1）
└── differential/
    └── test_b15f1_state_parity.py          # 新增 D-01…D-21

harness/
└── verification/
    └── B15F1/
        ├── manual-verification.md          # 新增（五段式）
        └── acceptance.py                   # 可选（一键跑关键场景）
```

### 本 feature 触及的文件（新增 / 修改 / 核对）

| 类别 | 文件 | 动作 |
|---|---|---|
| **新增 · L4** | `src/freegraph/persistence/sqlite.py` | `SqliteSaver`（构造 / setup / 8 方法 / 锁 / WAL / 失败信号） |
| **新增 · L4** | `src/freegraph/persistence/_json.py` | JSON 编解码 / tuple / `Interrupt` / `PregelTask` |
| **修改 · L4** | `src/freegraph/persistence/__init__.py` | `__all__` 增加 `SqliteSaver` |
| **新增 · L2 私有** | `src/freegraph/runtime/_state_read.py` | config / saver 校验、快照组装、历史组装、pending 合并调用（与 `superstep.py` 同层同条目） |
| **修改 · L3** | `src/freegraph/_stategraph.py` | `get_state` / `get_state_history` 真实实现（调用 `runtime._state_read`）；`stream` 传 saver；`checkpoints` 事件 |
| **修改 · L1** | `src/freegraph/contracts/protocols.py` | 仅 2 处 `config` 注解放宽（R-3） |
| **新增 · L2 私有** | `src/freegraph/runtime/_stream_checkpoint.py` | `StreamCheckpointWriter` |
| **修改 · L2** | `src/freegraph/runtime/_stream.py` | 可选 saver / writer / `run_table` 暴露 |
| **修改 · L2** | `src/freegraph/runtime/superstep.py` | 新增 `merge_pending_writes`（只读） |
| **新增 · 测试** | `tests/persistence/*` · `tests/runtime/test_b15f1_*` · `tests/contracts/test_b15f1_*` · `tests/differential/test_b15f1_*` | 见上 |
| **修改 · 冻结断言** | `tests/facade/test_compiled_graph.py` · `tests/facade/test_facade.py` · `tests/runtime/test_conditional_edge_surface.py` · `tests/contracts/test_b14f1_contracts.py` | R-1 / R-2 |
| **新增 · 人工验收** | `harness/verification/B15F1/manual-verification.md`（可选 `acceptance.py`） | FR-029 / SC-020 |
| **修改 · 文档** | `README.md` 的 `CompiledGraph` / `Checkpointer` 行 | 行为事实订正；不新增矩阵行 |
| **修改 · 合规** | `THIRD_PARTY_NOTICES` §1 | 登记上游 SQLite 同步 saver 的 MIT 改编（R-11） |
| **修改 · 上游规格** | `specs/b2f1-contracts-protocols/spec.md`（+ `contracts/public-api.md` / `data-model.md` 若含同款注记） | `get_state` / `get_state_history` 的 `config` 注解「拆分而不删」（R-3）；当前登记为「**承接中 · 计划**」 |
| **修改 · 上游规格** | `specs/b8f2-stream-modes/{spec,plan,tasks}.md` · `contracts/{stream-contract,upstream-parity}.md` | `checkpoints` 档下游承接状态：无 saver 仍空；有 saver + thread 由 B15F1 产出；当前统一登记为「**承接中**」 |
| **修改 · 上游规格** | `specs/b14f1-checkpointer-memory-saver/{spec,plan}.md` | 关闭 D-02「stream 消费端归 B15F1」的边界记录；当前统一登记为「**承接中**」 |
| **修改 · 上游规格** | `specs/b7f3-invoke-full-state/{spec}.md` · `contracts/invoke-contract.md` | CF-05 / D-5 的下游承接状态（B15F1 的 `config` 注解放宽）；当前登记为「**承接中 · 计划**」 |
| **核对 · 零改动** | `src/freegraph/contracts/types.py` · `src/freegraph/persistence/memory.py` · `src/freegraph/persistence/_types.py` · `src/freegraph/graph.py` · `runtime/__all__` · `pyproject.toml` | 冻结面 / 门面 / 依赖声明 |

---

## Phase 0: Research（摘要 · 详见 [research.md](./research.md)）

| # | 决策 | 结论 |
|---|---|---|
| **D-01** | L4 包结构 | `persistence/{__init__,_types,memory,_json,sqlite}.py`；只**依赖** L1 + stdlib（同层内部 import 允许）；门面不转出 |
| **D-02** | 上游移植范围 | 照抄 `langgraph-checkpoint-sqlite 3.1.1` 的**同步** saver：`setup()` / WAL / `cursor()` / `from_conn_string` / 单连接 + `threading.Lock`；**不**照抄其 serde / aiosqlite / sqlite-vec |
| **D-03** | 公开入口 | `SqliteSaver(conn, *, on_checkpoint=None)` + `SqliteSaver.from_conn_string(conn_string, *, on_checkpoint=None)`；支持 `:memory:`；不提供 `close()` / `serde` |
| **D-04** | 内部 schema | `checkpoints` / `writes` 两表（镜像上游）+ 内部 `task_path` / `created_at`；`checkpoint_ns` 恒 `""`；`list(None)` 线程顺序按首次写入（`MIN(rowid)`） |
| **D-05** | JSON 序列化 | 纯数据；`values` / `metadata` 用标准库 JSON；`next` / `tasks` / `interrupts` 重建 tuple / 对象；**pending `__interrupt__` 值 channel-aware 编码 `Interrupt→{value,id}`**；非 JSON ⇒ `TypeError`；X-05 |
| **D-06** | checkpoint id / 父链 | 完全复用 B14F1：每线程 `f"{n:032d}"` 单调；`MAX(checkpoint_id) + 1`；`parent_config` 指上一快照 |
| **D-07** | 写侧 | `put(config, *, values, metadata)` / `put_writes(config, *, writes, task_id, task_path)`；`put_writes` 目标由 `configurable["checkpoint_id"]` 指定；去重 / 排序逐字 B14F1；保留通道 REPLACE、普通通道 IGNORE |
| **D-08** | 读侧 | `get_tuple` 返回 `CheckpointTuple`（3 字段）；`list` 支持 `filter` / `before` / `limit`；`get_state` / 历史在 L3 组装 |
| **D-09** | pending 合并 | L2 私有 `merge_pending_writes`：重建通道 → 按 `.pending_writes` 顺序 `Channel.update` → 稀疏读；跳过保留通道；不推进版本 / 不写存储 |
| **D-10** | `tasks` / `interrupts` | **上游 next-tasks**：`next` + `.scheduler["fanout"]` + pending `__interrupt__`（裁定 13）；`interrupts` 按任务顺序展平、无任务中断回退 `snapshot.interrupts`；历史同款；**不使用** B14F1 的完成态 `snapshot.tasks` |
| **D-11** | config / 失败信号 | `RunConfig \| Mapping \| None`；裸 `str` ⇒ `TypeError`；缺 `thread_id` / 非空 `checkpoint_ns` / 无 saver ⇒ `ValueError`；`No checkpointer set` |
| **D-12** | L1 注解 | 只放宽 2 处 `config` 注解；L1 方法签名参数个数不变（`filter` / `before` / `limit` 为 L3 keyword-only 扩展）；走登记 + 回溯修订 + 追认 |
| **D-13** | `checkpoints` 流式档 | 只在 `"checkpoints" in modes` 时写 saver；`StreamCheckpointWriter` 复用 B14F1 写盘助手；事件 payload 由 `get_tuple(written)` + **next-tasks 组装**等价读回（`values` 取存储快照；`tasks` / `interrupts` 与 `get_state()` 一致；spec H-7 / FR-022 已允许）；不恢复历史 |
| **D-14** | 并发 / Windows | 单连接 + 每实例 `threading.Lock` + WAL；同实例多线程串行；跨进程只依赖 SQLite 文件锁；Windows CI 真跑 |
| **D-15** | 失败 / 原子性 | `sqlite3.Error` 原样传播；`cursor()` 异常回滚；单次 `put` / `put_writes` 零残留；不删除 / 重建用户库 |
| **D-16** | 生命周期 | `from_conn_string` 上下文关闭连接；`SqliteSaver(conn)` 不关闭调用方连接；不额外提供 `close()` |
| **D-17** | filter 语义 | `SqliteSaver` 用上游 key 校验 + `json_extract`；`MemorySaver` 保持 B14F1 顶层精确匹配（不校验 key）；`limit <= 0` / `list(None)` 线程顺序保留 B14F1；dotted key 与 `MemorySaver` 的差异登记为跨后端已知差异 |
| **D-18** | 差分 | 新 `tests/differential/test_b15f1_state_parity.py`；上游 SQLite 不可导入 ⇒ `SKIP (source-aligned)`；state 读取对照用已安装 `MemorySaver` |
| **D-19** | 人工 / 文档 | 五段式 manual-verification；README 事实订正；不新增兼容矩阵行 |
| **D-20** | 基线 / 红线 | 基线 **2191 passed / 8 skipped**；R-1 / R-2 为已知必红；不新增门禁编号 |

---

## Phase 1: Design（摘要）

- **Data model**：[data-model.md](./data-model.md) —— `SqliteSaver` / SQLite 两表 / `CheckpointTuple` /
  `StateSnapshot` 组装 / `PendingWrite` / `PregelTask` 重建 / `CheckpointId` / 线程顺序 / JSON 编码。
- **Contracts**：
  - [sqlite-saver-contract.md](./contracts/sqlite-saver-contract.md) —— L4 公开面、构造、8 方法、
    schema、并发、失败信号、生命周期、`on_checkpoint`。
  - [state-read-contract.md](./contracts/state-read-contract.md) —— `get_state` / `get_state_history`、
    config 校验、pending 合并、`tasks` / `interrupts`、历史排序 / 过滤、L1 注解。
  - [checkpoints-stream-contract.md](./contracts/checkpoints-stream-contract.md) —— `checkpoints` 事件、
    写盘时机、信封、payload、无 saver / 无 `thread_id`、不恢复历史。
  - [upstream-parity.md](./contracts/upstream-parity.md) —— P-01…P-25 / D-01…D-21 / X-01…X-08 的
    evidence 与判词索引。
- **Quickstart**：[quickstart.md](./quickstart.md) —— 可执行的 **12 组**验证场景
  （跨实例 / 跨进程 / `get_state` / 历史 / 中断 tasks / 静态挂起 / 删除 / 并发 / `checkpoints` /
  失败信号 / 差分 / 人工验收 / 全量回归）。

---

## Risks & Registrations

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| **K-1** | 上游 SQLite 同步 saver 与 B14F1 契约不一致（`put` 签名 / id 来源 / 三字段 `CheckpointTuple`） | 移植时误照抄上游 | 只照抄**存储 / 连接 / 锁 / WAL / schema**；`put` / id / 读侧载体以 B14F1 为**唯一权威** |
| **K-2** | JSON 序列化丢 tuple / 对象 | `MemorySaver` ↔ `SqliteSaver` 行为漂移 | `_json.py` 对冻结字段重建 tuple / `Interrupt` / `PregelTask`；X-05 只允许 `values` 中用户 tuple 变 list |
| **K-3** | pending 合并应用归约器时改变存储 | 快照被污染 | `merge_pending_writes` 只操作**副本**；不推进版本；不写回；单测断言存储零变化 |
| **K-4** | `stream` 写盘改变 B8F2 其它 mode | 既有流式测试变红 | 只在 `"checkpoints" in modes` 时启用 writer；其它 mode 走原路径；无 saver / 无 `thread_id` ⇒ 0 条 |
| **K-5** | L1 注解改动触发冻结面测试 | CI 红 | 只改 2 处注解；`test_protocols.py` 的返回类型断言保持；新增注解测试；R-3 追认 |
| **K-6** | `database is locked` / Windows 文件锁 | 并发测试不稳 | 同实例 `threading.Lock`；WAL；测试不加 `linux_only`；Windows CI 真跑；不承诺跨进程严格串行 |
| **K-7** | 冻结测试必红（R-1 / R-2） | CI 红 | 实施前先改测试（拆分而不删）；每改一处跑对应测试 |
| **K-8** | `filter` dotted key 与 `MemorySaver` 不同 | 跨后端差异被误判为 bug | contract / 边角写明；`SqliteSaver` 按上游 `json_extract`；`MemorySaver` 不改 |
| **K-9** | `from_conn_string` 关闭连接后继续调用 | `sqlite3.ProgrammingError` | 生命周期写死；单测覆盖；不提供额外 `close()` |
| **K-10** | 行数 / 范围超预算 | 交付压力 | 实施期实测；R-9 登记；**不**削减判据 |
| **K-11** | 上游 SQLite 包未安装 | 差分无法真跑 | 源码对齐项标 `SKIP (source-aligned)`；state 读取对照用 `MemorySaver`；CI 不把 skip 判 fail |
| **K-12** | next-tasks 重建在 fan-out / 真异常轮复杂 | `tasks` 与上游不一致或漏任务 | 以 `.scheduler["fanout"]` 为唯一 fan-out 来源；未关联 pending 中断兜底追加；D-21 + SC-027 覆盖收敛 / 静态 / 动态 / fan-out / 真异常五类 |

---

## Green Baseline & Red List（宪法 v1.11.0 的基线义务）

### 基线（**2026-11-22 · 实施前实跑**）

```text
.venv/bin/python -m pytest -q --tb=no
⇒ 2191 passed, 8 skipped in 155.20s
```

### 基线影响清单（**先推理预登记 · 由 T001 实测复核**；KEEP-1…KEEP-4 为**保持绿**）

> **宪法 v1.11.0 实测义务**：本表是**推理预登记**，T001 MUST 在临时副本按本 feature 落地形态
> （`get_state` / `get_state_history` 不再抛 `NotImplementedError`）改动源码 ⇒ 跑既有套件 ⇒
> **实测采集变红断言**并逐条核对本表；缺失项 MUST 补登记（带 `文件:行号` + 变红原因）。

| # | 测试 | 原因 | 处置 |
|---|---|---|---|
| **RED-1** | `tests/facade/test_compiled_graph.py::test_each_unready_method_raises_not_implemented_naming_owner` | `get_state` / `get_state_history` 已实现 | **拆分而不删**：保留 `update_state` → B16F1；新增 `get_state` / `get_state_history` 的正面断言 |
| **RED-2** | `tests/runtime/test_conditional_edge_surface.py::test_the_unimplemented_protocol_methods_still_name_their_owner` | 同上 | 同上（参数化只留 `update_state`；新增已实现断言） |
| **RED-3** | `tests/facade/test_facade.py::test_compile_returns_a_product_but_capability_methods_are_not_implemented` | 同上 | 同上；无 saver 时 `get_state` / history ⇒ `ValueError`（不是 `NotImplementedError`） |
| **RED-4** | `tests/contracts/test_b14f1_contracts.py` 的 `persistence.__all__` / 门面否定断言 | 新增 `SqliteSaver` | **只增不改**：`__all__` 加 `SqliteSaver`；门面同时断言无 `SqliteSaver` |
| **KEEP-1** | `tests/facade/test_stream_modes.py::test_checkpoints_and_messages_are_empty` | 若无 saver 仍应 0 条 | **保持通过**；新增「有 saver + `thread_id`」用例到 `test_b15f1_stream_checkpoints.py` |
| **KEEP-2** | `tests/contracts/test_protocols.py::test_get_state_returns_none_when_not_found` | 返回注解不变（仍含 `None`） | **保持通过**；新增 `config` 注解放宽的断言 |
| **KEEP-3** | `tests/differential/parity_probe.py` 的能力面列表 | 列表含 `get_state` / `get_state_history`（只检查存在性） | **保持通过**；D 场景走新文件 |
| **KEEP-4** | `tests/runtime/test_interrupt_checkpoint.py::test_the_runtime_never_imports_a_saver_implementation` | 只扫描 `runtime/**`；`runtime/_state_read.py` 不 import `freegraph.persistence`、不定义 saver 类 ⇒ 仍绿 | **保持通过**；不新增 L2 → L4 import |

> ⚠️ 除上述项，**其余测试 MUST 保持绿**。实施期若发现新的必红冻结断言 ⇒
> MUST 按「拆分而不删 + 判据只可更严」登记，**MUST NOT** 写永久红的 CI。

---

## Complexity Tracking

> **本 feature 无宪法门禁违规** ⇒ 无需例外论证。以下为**范围 / 复杂度登记**（非违规）：

| 项 | 说明 | 处置 |
|---|---|---|
| 新增 L4 实现 | `persistence/sqlite.py`（上游同步 saver 的零依赖移植） | 只依赖 L1 + stdlib（同层内部 import 允许）；`__all__` 只增 `SqliteSaver` |
| 新增 L2 状态读取 | `runtime/_state_read.py` | 只 import L1 + 同层 runtime（`superstep` / `_recursion`）；不 import L4；复用 `merge_pending_writes`；与 `_stategraph`(L3)→L2 方向一致，G25 不产生反/横依赖 |
| 新增 L2 流式写盘 | `_stream_checkpoint.py` | 私有模块；复用 B14F1 写盘助手；不改 `_stream_tick` 签名 |
| L1 注解改动 | 2 处 `config` 注解 | 登记 + 回溯修订 + 追认；返回类别不变 |
| 新增测试目录 | `tests/persistence/` | 与既有测试目录并列；无新门禁 |
| 差分场景 | D-01…D-21 | 新文件；上游 SQLite 缺席 skip；不改既有差分判词 |

---

## Implementation Sequencing（供 `/speckit.tasks` 展开）

| 阶段 | 内容 | 产出 |
|---|---|---|
| **P0 · 冻结断言预修** | R-1 / R-2 的测试拆分（先明确红线） | RED-1…RED-4 的测试改动 |
| **P1 · L4 JSON + SqliteSaver** | `_json.py` → `sqlite.py` → `__init__.py` | `SqliteSaver` + JSON 编解码 + 导出 |
| **P2 · L4 单测** | 协议 / CRUD / list / delete / 版本 / 生命周期 / 失败 / 并发 / 跨进程 | `tests/persistence/*` |
| **P3 · L2 pending 合并** | `merge_pending_writes`（只读副本） | `superstep.py` 新助手 + 单测 |
| **P4 · L2 状态读取** | `runtime/_state_read.py` + `_stategraph.get_state` / `get_state_history` | `test_b15f1_state_read.py` |
| **P5 · L1 注解** | `contracts/protocols.py` 2 处 + `_stategraph` 注解 | R-3 + `test_b15f1_contracts.py` |
| **P6 · 流式写盘** | `_stream_checkpoint.py` + `_stream.py` + `_stategraph.stream` | `test_b15f1_stream_checkpoints.py` |
| **P7 · 差分** | D-01…D-21 | `test_b15f1_state_parity.py` |
| **P8 · 人工 / 文档** | `manual-verification.md`（fake + 真实模型轮） · `README.md` · B25F1 下游**复验** | FR-029 / SC-020 · R-12 |
| **P9 · 全量回归 / 门禁** | `pytest -q` · G3 / G21 / G23 / G24 / G25 / G26 / G27 / G30 | 全绿 + 行数实测 |

---

## Notes

- **唯一权威**：需求与判据以 [spec.md](./spec.md) 为准；本 plan 只承接，若冲突以 spec 为准并回修本 plan。
- **上游锚点**：`langgraph 1.2.11` + `langgraph-checkpoint-sqlite 3.1.1`（2026-11-22 取证）；
  换版本 MUST 重新核实全部行号。
- **零第三方**：生产代码只用标准库；`langgraph*` 只在差分测试侧。
- **L4 边界**：`persistence` 只**依赖** L1 + stdlib（同层内部 import 允许）；`runtime/**` / `_stategraph.py` 通过鸭子类型调用
  saver，**MUST NOT** import `freegraph.persistence`；门面 **MUST NOT** 转出 `SqliteSaver`。
- **读侧不伪造**：`get_state` / 历史只从真实 `get_tuple` / `list` 组装；无快照 ⇒ `None` / 空；
  `tasks` 只从真实 `next` / `.scheduler["fanout"]` / pending `__interrupt__` 重建（上游 next-tasks）。
- **流式不伪造**：`checkpoints` 事件只对应真实 `put`；无 saver / 无 `thread_id` ⇒ 0 条；
  不把历史快照塞进本次运行事件。
- **不越界**：不实现 `update_state` / 时间旅行 / `Store` / Postgres / async / 子图 /
  运行级删除 / 线程复制。
- **文档纪律**：`README.md` 只做事实订正；`SqliteSaver` / `get_state` / `get_state_history` 的
  兼容矩阵行按 spec D-04 由 **B24F1** 纳入，本 feature 不新增矩阵行。
