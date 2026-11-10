# 与上游 LangGraph 的逐条对照（Upstream Parity）—— B7F1 的**证据表**

**Feature**: `B7F1` · **Spec**: [../spec.md](../spec.md) · **契约**: [superstep-contract.md](./superstep-contract.md)
**核实环境**: 上游 `langgraph` **1.2.11** · CPython **3.11.16** —— 核实于 **2026-11-10**
（临时 venv · **不进仓库依赖** · `pyproject.toml` 与 `Requires-Dist` 零改动）

> ⚠️ **本文件是「证据」载体，不是「判据」载体** ⇒ **MUST NOT** 被测试解析
> （测试**直接断言行为** ⇒ 避免「判据与实现同源 ⇒ 自证」）。
> **判据的唯一权威** = [superstep-contract.md](./superstep-contract.md)（`<!-- authority: yes -->`）。
> ⚠️ **换上游版本后 MUST 重新核实全部行号**（宪法原则 VIII）。

---

## 1. 逐条对照（**13 条**）

| # | 语义点 | freegraph | 上游 `langgraph 1.2.11` | 性质 | 来源 |
|---|---|---|---|---|---|
| **P-01** | **触发判定 · 首轮** | 「**有值**」即算已写过一次（调度器首次见到有值的通道时记版本 1） | `_triggers`：`seen is None` 时**只看** `channels[chan].is_available()` | **逐字同构** | `_algo.py:1260-1278` |
| **P-02** | **触发判定 · 后续轮** | `∃ s: has_value(s) ∧ version(s) > seen(N)[s]`（**逐触发源**） | `channels[chan].is_available() and versions.get(chan) > seen.get(chan)` | **逐字同构**（freegraph 的判定式与上游 `_triggers` **逐字同构**；「清空不是写入 ⇒ 版本不推进」是 freegraph 让 `has_value` 变假（路由型通道步末被清空）的**实现手段**，**不**替代该合取项 · 裁定 28） | `_algo.py:1271-1276` |
| **P-03** | **通道版本的空间** | **每通道独立**的写入版本 | **全局单调计数器** `next_version`（所有通道共享） | **机制差异 · 可观察等价**（比较只在同一通道内） | `_algo.py:273-284` · `:322-331` |
| **P-04** | **已消费版本的结构与时点** | `节点名 → {触发源 → 版本}`，在 **plan 阶段**消费 | `checkpoint["versions_seen"][task.name][chan]`，在 **apply 阶段**更新 | **机制差异**（时点）· 失败后重试的行为不同 ⇒ **DR-1** | `_algo.py:264-271` |
| **P-05** | **同轮执行顺序** | **节点表声明顺序**（发起者裁定） | **节点名字典序**（`sorted(triggered_nodes)`）；写入合并再按**任务路径**排序 | **可观察差异**（非交换归约器的合并顺序两侧不同）⇒ **DR-2** | `_algo.py:476-484` · `:258-259` |
| **P-06** | **步末清空范围** | **只**对**路由型**通道调 `clear()`，**且只清「本轮未被写入的」** | 对「**本步未更新**」的通道调 `update(EMPTY_SEQ)` ⇒ 覆盖型 / 归约型 **no-op**（值保留）· 路由型 ⇒ 清空 | **逐字同构**（D-05 的订正后） | `_algo.py:333-341` · `last_value.py:56-58` · `binop.py:123-125` · `ephemeral_value.py:56-61` |
| **P-07** | **未知 key 的写入** | **显式失败** —— `InvalidUpdateError` | **warning + 静默忽略**（`logger.warning(... "ignoring it.")`） | **分叉**（与 **C6** 一致 ⇒ 与上游**不同**；沿用 B5F2 的 **DR-2** 登记） | `_algo.py:310-314` |
| **P-08** | **写入合并的形态** | **批量**：每通道**一次** `update(values)` | **批量**：`pending_writes_by_channel` ⇒ 一次 `channels[chan].update(vals)` | **逐字同构** | `_algo.py:298-320` |
| **P-09** | **节点入参的范围** | **订阅集 ∩ 有值集**（普通 `dict`） | `proc.channels` 里 `is_available()` 的那些（`val[chan] = channels[chan].get()`） | **逐字同构**（= **C4**） | `_algo.py:1356-1370` |
| **P-10** | **静态边的触发时机** | 边触发源 = 源节点的**执行版本** ⇒ 目标节点**下一轮**执行 | `add_edge` 编译成 **Branch** ⇒ **PUSH 任务** ⇒ 下一 tick 执行 | **机制差异 · 语义等价** | `graph/state.py:928` · `:1399` · `_algo.py:800+` |
| **P-11** | **收敛判定** | 任务集**为空** ⇒ 立即终止 | `if not self.tasks: self.status = "done"; return False` | **逐字同构** | `_loop.py:657-660` |
| **P-12** | **步数上限的缺省** | **25** | `DEFAULT_RECURSION_LIMIT = 25` | **逐字一致**（对外**载体**归 B13F1） | `langchain_core/runnables/config.py:171` · `_loop.py:1701` |
| **P-13** | **收官钩子**（`consume()` / `finish()`） | **不实现**（B5F1 的通道抽象只有四个**冻结**操作） | `BaseChannel.consume()` / `finish()` 两个钩子；最后一轮对**所有**通道调 `finish()` | **机制差异**（语义归 checkpoint / 收官）⇒ **DR-3** | `channels/base.py:101` · `:112` · `last_value.py:130-145` · `_algo.py:343-346` |

---

## 2. 保留通道名（上游控制流 · 本 feature **零实现**）

| 名字 | 语义 | 归属 |
|---|---|---|
| `NO_WRITES` | 「本任务无写入」标记 | **B9F1 / B10F1** |
| `PUSH` | 推送任务（Sends / Branch） | **B11F1 / B8F1** |
| `RESUME` | 恢复 | **B10F1** |
| `INTERRUPT` | 中断 | **B10F1** |
| `RETURN` / `ERROR` / `ERROR_SOURCE_NODE` | 错误传播 | **B12F1** |

> 上游在 `apply_writes` 的分组阶段**跳过**这些名字（`_algo.py:297-307`）⇒ 本 feature 的
> 「未知 key ⇒ 显式失败」**不会**误伤它们（因为 freegraph **不实现**这些保留名 ⇒ 它们本就是未知 key
> ⇒ 显式失败 ⇒ **符合预期**）。

---

## 3. 实测基线（可复现的**事实**）

| # | 事实 | 核实方式 |
|---|---|---|
| **B-1** | `langgraph/pregel/_algo.py` 共 **1460** 行；`pregel/_loop.py` 共 **1988** 行 | `wc -l` |
| **B-2** | `_triggers` 定义于 `_algo.py:1260`；`apply_writes` 定义于 `_algo.py:232`；`prepare_next_tasks` 定义于 `_algo.py:392`（重载在 `:349` / `:371`）；`prepare_single_task` 定义于 `_algo.py:524`；`prepare_input` 定义于 `_algo.py:1356` | `grep -n "^def "` |
| **B-3** | `graph/state.py:73-75` ⇒ `from langgraph.pregel import Pregel` / `pregel._read` / `pregel._write` —— **分层证据**（运行时层**不** import 图定义层） | 直读 |
| **B-4** | `channels/ephemeral_value.py:56-61` ⇒ `update([])` ⇒ 清为 `MISSING` 并返回**真**；`:62-65` ⇒ 多值 + `guard=True` ⇒ 抛 `InvalidUpdateError` | 直读 |
| **B-5** | `channels/last_value.py:56-58` / `channels/binop.py:123-125` ⇒ `update([])` **no-op**（值保留） | 直读 |
| **B-6** | `channels/base.py:101` / `:112` ⇒ `consume()` / `finish()` 默认 **no-op** | 直读 |

---

## 4. 遗留（**只登记 · 不改判据**）

| # | 遗留 | 触发重新评估的条件 |
|---|---|---|
| **DR-1** | `versions_seen` 的消费时点（plan vs apply）与失败后不回滚 | 出现「失败后重试同一调度状态」的用法 |
| **DR-2** | 同轮执行顺序 = 声明顺序（上游 = 名字序） | 出现与非交换归约器相关的用例 |
| **DR-3** | 上游的 `consume()` / `finish()` 两个钩子未实现 | B7F3 交付 `invoke()` 的完整状态语义时 |
