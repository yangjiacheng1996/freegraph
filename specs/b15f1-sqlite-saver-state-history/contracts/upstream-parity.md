# Contract · 上游对照（Upstream Parity）

**Feature**: B15F1 · **Date**: 2026-11-22 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md)

> 本文件是 **spec 的 P-01…P-25 / D-01…D-21 / X-01…X-08 的索引与取证清单**；
> 语义权威仍是 [spec.md](../spec.md)。本文件不新增判据，只把「上游怎么说 / freegraph 怎么做 /
> 为什么」集中到一处，供 plan / tasks / 实现 / 复核使用。

---

## 1. 取证环境

| 项 | 值 |
|---|---|
| `langgraph` | **1.2.11** · `.venv` 已安装（2026-11-22） |
| `langgraph-checkpoint-sqlite` | **3.1.1**（MIT）· uv 缓存 |
| SQLite 源码 | `/home/ctyun/.cache/uv/archive-v0/UtTk-BJ9thKpSH0Q/langgraph/checkpoint/sqlite/__init__.py`（645 行） |
| 状态读取 | `.venv/lib/python3.11/site-packages/langgraph/pregel/main.py` |
| 文档 | `harness/docs/oss/python/langgraph/checkpointers.md:130,170` |
| 实测 | E8 `HISTORY: 6`（`harness/reports/Q3-LangGraph的开源边界.md:43`） |
| Python | `.venv` 3.11.16 |

> 上游 SQLite 包**未安装进 `.venv`**；差分运行时不可导入 ⇒ `SKIP (source-aligned)`。
> 源码只作**行为锚点**；不复制其依赖（`aiosqlite` / `sqlite-vec` / `langchain_core`）。

---

## 2. 语义点索引（P-01…P-25）

| # | 语义点 | 上游锚点 | freegraph 口径 | 关系 |
|---|---|---|---|---|
| P-01 | `get_state` 最新 / 按 id | `pregel/main.py:1392-1435` · docs `:130` | 同款 | SAME |
| P-02 | 无快照的 `get_state` | `pregel/main.py:1152-1162` | `None` | DIFF · X-01 |
| P-03 | `get_state` 合并 pending | `pregel/main.py:1431` · `:1145-1162` | 无 id 合并 / 有 id 不合并 | SAME |
| P-04 | 历史排序 | `pregel/main.py:1505-1530` · docs `:170` · E8 | id 降序（最新在前） | SAME |
| P-05 | 历史 `filter` / `before` / `limit` | `pregel/main.py:1480-1487` · `:1518-1523` · SQLite `utils.py:9-100` | 上游 filter；B14F1 `limit` / `list(None)` | SAME（带冻结差异） |
| P-06 | 无 checkpointer 读取 | `pregel/main.py:1400-1401` / `:1496-1497` | `ValueError("No checkpointer set")` | SAME |
| P-07 | `StateSnapshot` 8 字段 | `types.py:684-701` | L1 8 字段 | SAME |
| P-08 | 中断顺序 | B12F1 裁定 25 / D-7 · 上游 `GraphInterrupt` | 标准节点名 / fan-out TaskId | SAME（顺序更确定 · B12F1 X-7） |
| P-09 | `config` 载体 | `pregel/main.py:1392` / `:1480` | `RunConfig \| Mapping \| None` | DIFF · X-03 |
| P-10 | `checkpoints` 事件 | `_loop.py:631-636` · `debug.py:144-185` · E-5 | 四键信封 + `StateSnapshot`（`tasks` / `interrupts` 为 next-tasks 投影） | DIFF · X-04 |
| P-11 | SQLite 序列化 | SQLite `__init__.py:17-30` / `:387-445` | 标准库 JSON | DIFF · X-05 |
| P-12 | 连接 / 并发 / WAL | SQLite `__init__.py:85-130` / `:95` / `:124` / `:141` | 单连接 + 锁 + WAL | SAME |
| P-13 | `delete_thread` | `base/__init__.py:344-353` | 删除快照 / 写入；幂等 | SAME |
| P-14 | `delete_for_runs` / `copy_thread` | `base/__init__.py:355-388` | v1 `NotImplementedError` | SAME |
| P-15 | `get_next_version` | `base/__init__.py:721-740`（**base 默认**） | `int+1` | SAME（对照 **base 默认实现**；SQLite 覆写为字符串版本 ⇒ 见 P-21） |
| P-16 | 保留通道名 | `_internal/_constants.py:9,11,13,17` | 逐字 | SAME |
| P-17 | 配置级 checkpointer / 子图 | `pregel/main.py:1396-1398` / `:1403-1422` | 只用编译期 saver；无子图 | DIFF（能力边界） |
| P-18 | `context` 持久化 | `RunnableConfig.configurable` | 不持久化 | DIFF · X-07 |
| P-19 | 建库 / 建表 | SQLite `__init__.py:132-166` | 镜像两表 + 内部 `task_path` | SAME（schema 内部） |
| P-20 | pending 排序 | SQLite `__init__.py:191-380` | `(task_path, task_id, idx)` | DIFF（B14F1 冻结） |
| P-21 | `put` id / 版本 | SQLite `__init__.py:387-445` / `:626-644`（**SQLite 实现**） | saver 生成 32 位 id；int 版本 | DIFF（对照 **SQLite 实现** · B14F1 冻结；与 P-15 的 base 对照不矛盾） |
| P-22 | `list(None)` 线程顺序 | SQLite `__init__.py:295-380` | 首次写入顺序 | DIFF（B14F1 冻结） |
| P-23 | `filter` key 校验 | SQLite `utils.py:9-25` | 照抄 | SAME |
| P-24 | `tasks` / `interrupts`（**next-tasks**） | `pregel/main.py:1145-1210` · B10F1 F-3 | 读取层按 `next` + `.scheduler["fanout"]` + pending `__interrupt__` 重建 next-tasks；不使用存储的完成态 `snapshot.tasks`。**两类来源 id 域不同**：`next` 来源 `id` = 运行时 `task_key`（权威）；账本来源 `id` = 本地 `index`（非 `task_key`，`interrupts` 恒 `()`，不跨源去重） | SAME（`id` / `path` 为 freegraph 口径） |
| P-25 | 缺失 `thread_id` 读取 | `pregel/main.py:1392` / `:1480`（实测 1.2.11 `ValueError` / 部分 `KeyError`） | `ValueError`（点名 `thread_id`） | STRICTER（X-08） |

---

## 3. 差分场景（D-01…D-21）

| # | 场景 | 判词 |
|---|---|---|
| D-01 | `get_state` 取最新 | SAME（比较 `values` / `next`（非 fan-out）/ `tasks` / `interrupts`；`metadata` / `created_at` / `config` 投影排除） |
| D-02 | `get_state` 按 id | DIFF · X-01 |
| D-03 | 历史数量 / 顺序 | SAME（同上投影） |
| D-04 | 历史 `filter` / `before` / `limit` | SAME（带冻结差异） |
| D-05 | 静态挂起历史表示 | SAME |
| D-06 | 动态中断 `interrupts` | SAME |
| D-07 | 真异常 + 中断同现 | SAME |
| D-08 | `context` 不持久化 | DIFF · X-07 |
| D-09 | 无 checkpointer 读取 | SAME |
| D-10 | 缺失 `thread_id` | STRICTER · X-08 |
| D-11 | `checkpoints` 事件 | DIFF · X-04（payload 的 `tasks` / `interrupts` 为 next-tasks 投影） |
| D-12 | `delete_thread` | SAME |
| D-13 | `SqliteSaver` ↔ `MemorySaver` | SAME（freegraph 双后端） |
| D-14 | 跨实例持久化 | SAME（freegraph 部分始终运行；上游对照缺失只跳过对照） |
| D-15 | 并发写 | SAME（freegraph 部分始终运行；source-aligned 对照不可导入时才跳过对照） |
| D-16 | 不可序列化载荷 | DIFF · X-05 |
| D-17 | `get_state` 无 id + pending | SAME |
| D-18 | `get_state` 带 id + pending | SAME（`values` 不合并；`tasks` 仍为 next-tasks） |
| D-19 | `from_conn_string` / `:memory:` / WAL / 建表 | SAME（source-aligned） |
| D-20 | `filter` 非法 key | SAME |
| D-21 | next-tasks 重建 | SAME（每个 `next` / fan-out 目标一个任务；收敛快照 `tasks=()`；`id` / `path` 为 freegraph 口径；fan-out 轮不比较 `next`） |

> 上游 SQLite 运行时不可导入 ⇒ D-14 / D-15 / D-19 等标 `SKIP (source-aligned)`；
> state 读取对照用已安装的 `MemorySaver`。**skip 不是 fail。**
> **比较投影**：`metadata` 内容为 freegraph 内部调度账本（与上游 `{source,step,parents}` 不同）
> ⇒ 不逐字比较；`created_at` 只比 ISO 形态；`config` / `parent_config` 的载体差异归 **X-03**。
> fan-out 轮的 `next` 在 freegraph v1 可能为 `()`（调度账本 pending）或 `节点名:TaskId`
> （挂起现场）⇒ 只比较 `tasks`，不比较 `next` 字面值。

---

## 4. 偏离登记（X-01…X-08）

| # | 状态 | 判据 | 处置 |
|---|---|---|---|
| X-01 | 有效 | `get_state` 无快照 ⇒ `None`（上游空快照） | L1 协议冻结；本 feature 只执行 |
| X-02 | **已撤销** | 原「不合并 pending」 | clarify 轮改为上游同款；编号保留不复用 |
| X-03 | 有效 | `config` 双形态 | B7F3 CF-05 冻结 |
| X-04 | 有效 | **仅** `checkpoints` 四键信封 + `StateSnapshot` | B8F2 冻结 |
| X-05 | 有效 | 标准库 JSON（上游 serde / msgpack） | 零第三方红线 |
| X-06 | **已撤销** | 原自研短连接 / 重试并发 | clarify 轮改为上游单连接 + 锁 + WAL（**不额外重试**） |
| X-07 | 有效 | `context` 不持久化 | B8F3 冻结 |
| X-08 | 有效 | 缺 `thread_id` ⇒ `ValueError` | 更明确的失败信号 |

> **当前有效 = 6 条**（X-01 / X-03 / X-04 / X-05 / X-07 / X-08）。
> X-02 / X-06 已按 clarify 轮决议撤销，编号保留不复用（宪法原则 VIII）。
> **X-04 仅指 `checkpoints` 事件载荷**；上游额外 `__start__` 快照的差分排除不占 X 编号。
> **X-08 的对照行 = P-25 + D-10**（关系标注均为 STRICTER）；**P-17 为能力边界（C26 · v2），不是偏离、不占 X 编号**。

---

## 5. 复核清单

- [ ] 每条上游断言带版本 + `路径:行号`（spec 已满足）。
- [ ] P 表 ↔ X 表对同一分叉的关系标注一致（SAME / DIFF / STRICTER）。
- [ ] D 场景落 `tests/differential/test_b15f1_state_parity.py`；缺席 skip。
- [ ] 上游 SQLite 同步 saver 的**改编代码**已在 `THIRD_PARTY_NOTICES` §1 登记（MIT · 原始版权保留）；
      其 `aiosqlite` / `sqlite-vec` / `langchain_core` 依赖**不**引入；运行时依赖仍为零。
- [ ] 换上游版本 ⇒ 重新核实全部行号与本表。
