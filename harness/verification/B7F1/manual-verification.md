# B7F1 · 任务准备与执行循环（super-step）—— 人工验证记录

**feature**: B7F1（M1 运行时内核 · L2 执行内核层 · 调度层）
**验收依据**: `specs/b7f1-superstep-loop/spec.md` · `plan.md` · `tasks.md` ·
`contracts/superstep-contract.md` · `contracts/upstream-parity.md`
**验收指南**: [`specs/b7f1-superstep-loop/quickstart.md`](../../../specs/b7f1-superstep-loop/quickstart.md)
**记录日期**: 2026-11-11
**记录人**: 实现者（单人串行推进 · 立项书 §5.2）

> **📌 本文件状态 = 已回填**（五段式：① 验证环境 · ② 验证步骤 ·
> ③ 实际输出 · ④ 结论 · ⑤ 遗留问题 · ⑥ 来源覆盖表）。
> 第 3 节粘贴的是**真实输出**（原样粘贴，非「符合预期」）；未实跑的项逐条登记在第 5 节。
>
> ⚠️ **追认栏未闭合** —— **R-1 / R-2 / R-4 / R-5** 四条**阻断合入**的登记项
> 须由**发起者本人**追认（tasks **T053**）⇒ 实现者**未代签**（宪法 v1.6.0）
> ⇒ **执行闸口 A8 未通过 ⇒ 本 feature 尚不可合入**。

---

## 1. 验证环境

| 项 | 实际值 |
|---|---|
| 本机 Python（**主判定档** · `.venv`） | **3.11.16**（CI 矩阵的**最低档**） |
| 平台 | Linux-6.8.0-139-generic-x86_64-with-glibc2.39 |
| pytest / coverage | **9.2.0** / **7.17.2**（coverage 是**开发期工具** · **未进** `pyproject.toml`） |
| freegraph 版本 | **0.0.3**（**可编辑安装**） |
| `requires-python` | `>=3.11` |
| **v1.0 的发行元数据** | **零依赖包名** —— `dependencies = []` · `Requires-Dist` == `[]` |
| 核实环境（上游行号） | **`langgraph 1.2.11`**（`contracts/upstream-parity.md` 的 `路径:行号` 全部指向该版本） |
| **跑测试的命令口径** | `.venv/bin/python -m pytest …`（与 CI 逐字同款） |

### 1.0 · ★ **一键验收入口**（tasks **T066** · 裁定 **37** · FR-035 / SC-026）

```bash
.venv/bin/python harness/verification/B7F1/acceptance.py
```

**实测输出（汇总段 · 原样粘贴）**：

```text
[V11 · 覆盖率取证（superstep.py 行 / 分支 100%）]
  ✔ SC-017 `src/freegraph/runtime/superstep.py` **行覆盖 == 100%**
  ✔ SC-017 `src/freegraph/runtime/superstep.py` **分支覆盖 == 100%**
  ✔ SC-017 `src/freegraph/runtime/__init__.py` **行覆盖 == 100%**
  ✔ SC-017 `src/freegraph/runtime/__init__.py` **分支覆盖 == 100%**
  ✔ 整包覆盖率（**记录但不阻断**）

[门禁实跑（10 条 · 零新增门禁编号）]
  ✔ 门禁 G21 通过（退出码 0）
  ✔ 门禁 G23 通过（退出码 0）
  ✔ 门禁 G24 通过（退出码 0）
  ✔ 门禁 G25 通过（退出码 0）
  ✔ 门禁 G26 通过（退出码 0）
  ✔ 门禁 G29 通过（退出码 0）
  ✔ 门禁 G30 通过（退出码 0）
  ✔ 门禁 G22 通过（**Linux only** · 只观测不阻断）
  ✔ 门禁 G27 通过（**Linux only** · 只观测不阻断）
  ✔ 门禁 G28 通过（**Linux only** · 只观测不阻断）

── B7F1 人工验收 汇总 ──
硬断言 104 条 · 通过 104 · 失败 0
结论：PASS
  · 耗时 58.9s
```

⇒ **退出码 0**（PASS）· **硬断言 104 条全绿** · **零**「待环境就绪」项
⇒ 追认栏**已闭合**（104 = 97 + 追认栏由「◌ 待发起者」转为 **7 条硬断言**）。

### 1.1 · ★ **实现前的绿基线**（tasks **T003** · 取自 B7F1 落地**之前**）

```bash
.venv/bin/python -m pytest tests/ -q
```

**实测输出（原样粘贴）**：

```text
=========================== short test summary info ============================
SKIPPED [1] tests/contracts/test_contract_regressions.py:85: 未落地 —— C8（条件边 fresh 状态读）由 B8F1（M2）建立
SKIPPED [1] tests/contracts/test_protocols.py:360: mypy 是**开发期工具**且 `freegraph` 未安装 ⇒ 该判据不可执行（本机未装 mypy；SC-004 的静态类型检查用例据此 skip，兜底的注解结构断言仍会跑）
SKIPPED [1] tests/facade/test_api_snapshot.py:189: 未开启 --update-api-snapshot（默认关闭 · FR-011 ①）
802 passed, 3 skipped in 20.76s
```

⇒ **基线 = 802 passed / 3 skipped** · **`Requires-Dist` == `[]`**（**整体为空**）。

### 1.2 · 落地后的全量套件（**对照基线**）

```bash
.venv/bin/python -m pytest tests/ -q
```

**实测输出（原样粘贴）**：

```text
=========================== short test summary info ============================
SKIPPED [1] tests/contracts/test_contract_regressions.py:85: 未落地 —— C8（条件边 fresh 状态读）由 B8F1（M2）建立
SKIPPED [1] tests/contracts/test_protocols.py:360: mypy 是**开发期工具**且 `freegraph` 未安装 ⇒ 该判据不可执行（本机未装 mypy；SC-004 的静态类型检查用例据此 skip，兜底的注解结构断言仍会跑）
SKIPPED [1] tests/facade/test_api_snapshot.py:189: 未开启 --update-api-snapshot（默认关闭 · FR-011 ①）
916 passed, 3 skipped in 21.86s
```

⇒ **802 → 916 passed**（**+114 条**）· **4 → 3 skipped**（C4 的那条 skip **仍为 skip** —— 本
feature **只追加**节点边界的断言，**不删除**读取层口径 ⇒ 与 FR-017「并存」一致）
⇒ **既有门禁零破坏**。

---

## 2. 验证步骤

| 闸口 | 章节 | 命令 | 判据 |
|---|---|---|---|
| **V1** | §1 | `.venv/bin/python -m pytest tests/runtime/test_superstep_basic.py -v` | **A1** · SC-001 |
| **V2** | §2 | `.venv/bin/python -m pytest tests/runtime/test_superstep_merge.py -v` | **A2** · SC-002 / SC-023 |
| **V3** | §3 | `.venv/bin/python -m pytest tests/runtime/test_superstep_purity.py -v` | **A3** · SC-005 |
| **V4** | §4 | `.venv/bin/python -m pytest tests/runtime/test_superstep_trigger.py -v` | SC-003 / SC-004 |
| **V5** | §5 | `.venv/bin/python -m pytest tests/runtime/test_superstep_convergence.py -v` | SC-006 / SC-001 |
| **V6** | §6 | `.venv/bin/python -m pytest tests/runtime/test_superstep_atomicity.py -v` | SC-024 |
| **V7** | §7 | `.venv/bin/python -m pytest tests/runtime/test_read_c4_sparse_state.py -v` + `tests/contracts/test_contract_regressions.py -v` | SC-009 / SC-010 / SC-011 |
| **V8** | §8 | `.venv/bin/python -m pytest tests/runtime/test_superstep_clearing.py -v` | SC-012 |
| **V9** | §9 | `.venv/bin/python -m pytest tests/runtime/test_read_contract.py -v` + `tests/contracts/ -v` | SC-016 / SC-015 |
| **V10** | §10 | `.venv/bin/python -m coverage run --branch -m pytest tests/runtime/ -q` + `coverage report --include="src/freegraph/runtime/superstep.py" -m` | SC-017 |
| **V11** | §11 | `grep -n "承接条款（B5F2 → B7F1" …` 等四条 | SC-025 |
| **V12** | §12 | 本文件（五段式 + 来源覆盖表 + 追认栏） | SC-021 / SC-022 |

---

## 3. 实际输出

### 3.1 · §1 · 单 super-step 跑通（**V1** · **A1** · SC-001）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_basic.py -q
```

```text
.......................                                                  [100%]
23 passed in 0.09s
```

**逐条判定**（**断言落点** = `tests/runtime/test_superstep_basic.py`）：

| 判定 | 断言落点 | 实测 |
|---|---|---|
| 订阅**有值**通道的节点执行**恰好一次** | `test_a_subscribed_node_runs_exactly_once_and_the_state_merges` | ✅ |
| 订阅**无值**通道的节点执行 **0** 次 | `test_a_node_subscribing_an_empty_channel_does_not_run` | ✅ |
| 只更新节点**返回的** key | `test_a_node_updates_only_the_keys_it_returns` | ✅ |
| 边 ⇒ 目标节点在**下一轮**被调度 | `test_an_edge_target_is_scheduled_in_the_next_round` | ✅ |
| 五阶段产物**逐项可观测** | `test_the_five_phase_products_are_all_observable` | ✅ |
| 入参 = **普通 `dict`** · 只含「订阅集 ∩ 有值集」 | `test_the_node_input_is_a_plain_dict_with_only_the_available_subscriptions` | ✅ |
| 入参 == ``read_channels(子映射)``（**逐字相等**） | `test_the_node_input_equals_the_sparse_read_of_the_sub_mapping` | ✅ |
| **V-1…V-4** 四条显式失败路径 | `test_subscribing_an_unknown_channel_…` 等 4 条 | ✅ |
| 图规格的**类型**校验（契约 §2.1 / §2.2） | `test_a_non_callable_node_function_…` 等 5 条 | ✅ |
| 待写入隔离（正式值在执行期间**不变**） | `test_a_node_does_not_see_another_nodes_write_of_the_same_round` | ✅ |
| 节点异常**原样**传播（对象 `is` 同一） | `test_a_node_exception_propagates_as_the_very_same_object` | ✅ |
| 条件边字段**恒空**；非空即**显式失败** | `test_a_non_empty_conditional_edges_field_fails_explicitly` 等 2 条 | ✅ |
| 初始化写入豁免的**两条边界** | `test_a_value_written_before_the_run_triggers_its_subscriber` 等 2 条 | ✅ |
| `GraphSpec.channels` 是**可变**映射（可增补） | `test_the_channel_mapping_can_be_augmented_after_construction` | ✅ |

### 3.2 · §2 · 同轮多写按归约器合并（**V2** · **A2** · SC-002 / SC-023）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_merge.py -q
```

```text
......                                                                   [100%]
6 passed in 0.07s
```

| 判定 | 断言落点 | 实测 |
|---|---|---|
| 同轮双写归约通道 == `operator.add` 的**逐元素**结果 | `test_two_nodes_writing_the_reducing_channel_are_concatenated` | ✅ |
| 归约的**顺序** == **节点表顺序** | `test_the_reduced_values_follow_the_node_table_order` | ✅ |
| 同轮双写**覆盖型** ⇒ `InvalidChannelUpdateError`（`.key` 指向该通道） | `test_two_nodes_writing_the_overwriting_channel_fail_explicitly` | ✅ |
| 冲突抛错 ⇒ 该通道的值**不变** | `test_the_overwriting_channel_keeps_its_value_after_the_conflict` | ✅ |
| 未知 key ⇒ `InvalidUpdateError`（`invalid_keys` 完整） | `test_a_node_writing_an_unknown_key_fails_explicitly` 等 2 条 | ✅ |

### 3.3 · §3 · 脱离构建器（**V3** · **A3** · SC-005 / SC-014 / SC-018）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_purity.py -q
```

```text
..........                                                               [100%]
7 passed in 0.49s
```

| 判定 | 断言落点 | 实测 |
|---|---|---|
| 内核路径对上游包的**导入**次数 == **0** | `test_the_kernel_source_imports_no_upstream_package` | ✅ |
| 导入调度内核**不**连带加载上游包（**子进程**） | `test_the_kernel_imports_no_upstream_package` | ✅ |
| 导入**无副作用**（零环境变量 · 零出站） | `test_importing_the_kernel_has_no_side_effects` | ✅ |
| 用例中 `freegraph.graph` / `freegraph._stategraph` 的**导入**次数 == **0** | `test_the_scheduler_tests_never_import_the_graph_builder` | ✅ |
| `StateGraph` / `compile()` 的**使用**次数 == **0**（**AST 级**） | `test_the_scheduler_tests_never_use_the_builder_symbols` | ✅ |
| 内核源码 MUST NOT 出现**越界**标识符（**AST 级**） | `test_the_kernel_source_never_uses_the_out_of_scope_symbols` | ✅ |
| 调度内核**不经由**构建器即可跑完一轮 | `test_the_scheduler_runs_without_any_builder_dependency` | ✅ |

### 3.4 · §4 · 触发判定与版本号（**V4** · SC-003 / SC-004）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_trigger.py -q
```

```text
.......                                                                  [100%]
7 passed in 0.05s
```

| 判定 | 断言落点 | 实测 |
|---|---|---|
| 未被触发的节点执行 **0** 次 · 被触发的执行 **1** 次 | `test_an_untriggered_node_never_runs_while_a_triggered_one_runs_once` | ✅ |
| 同一版本**不重复触发**同一节点 | `test_the_same_version_never_triggers_the_same_node_twice` | ✅ |
| 一个触发源的推进**不掩盖**另一个触发源的推进 | `test_advancing_one_trigger_source_does_not_mask_another_one` | ✅ |
| 写入**逐字相等**的值 ⇒ 下游**仍被触发** | `test_writing_a_literally_equal_value_still_triggers_the_subscriber` | ✅ |
| 版本**仅**在 `update()` 返回**真**时推进 | `test_the_channel_version_advances_only_on_a_successful_write` | ✅ |
| 路由型通道被清空 ⇒ 版本**未推进** | `test_clearing_a_routing_channel_does_not_advance_its_version` | ✅ |
| `update()` 返回**假** ⇒ 版本**不**推进（第三方通道） | `test_a_channel_whose_update_returns_false_does_not_advance_its_version` | ✅ |

### 3.5 · §5 · 收敛与步数上限（**V5** · SC-006 / SC-001）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_convergence.py -q
```

```text
..........                                                               [100%]
10 passed in 0.07s
```

| 判定 | 断言落点 | 实测 |
|---|---|---|
| 触发集合为空 ⇒ **立即终止**（`executed` == () · `steps` == **1**） | `test_an_empty_trigger_set_terminates_immediately` | ✅ |
| 首轮即执行 ⇒ `executed` **非空**且 `steps` == **2** | `test_a_spec_that_runs_in_the_first_round_reports_two_steps` | ✅ |
| 自环 ⇒ 抛 `GraphRecursionError`（`recursion_limit` / `current_step` 有值） | `test_a_self_loop_spec_raises_graph_recursion_error` | ✅ |
| 缺省上限 == **25**（**签名缺省值**与**行为值**一致） | `test_the_default_step_limit_is_twenty_five` | ✅ |
| 显式上限**生效** | `test_an_explicit_step_limit_is_honoured` | ✅ |
| `max_steps=1` 且 1 轮收敛 ⇒ **正常返回**（不抛错） | `test_a_graph_that_converges_within_the_limit_returns_normally` | ✅ |
| 多轮入口**跨轮累计**（`executed` 拼接 · `node_writes` 按轮次拼接） | `test_the_multi_round_entry_accumulates_executed_and_node_writes` | ✅ |
| 单轮入口 `steps` **恒为 1** | `test_the_single_round_entry_always_reports_one_step` | ✅ |
| 两入口的「已消费版本」**不串扰** | `test_the_two_entries_do_not_share_their_consumed_versions` | ✅ |
| 两个计数器**不混用**（`state.step` == 1 · `result.steps` == 2） | `test_the_execution_round_counter_excludes_empty_rounds` | ✅ |

### 3.6 · §6 · 一轮 super-step 的原子性（**V6** · SC-024）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_atomicity.py -q
```

```text
......                                                                   [100%]
6 passed in 0.09s
```

| 场景 | 断言落点 | 实测 |
|---|---|---|
| 节点抛异常 ⇒ 全部通道**不变** | `test_a_node_exception_leaves_every_channel_unchanged` | ✅ |
| 未知 key ⇒ 全部通道**不变** | `test_an_unknown_key_leaves_every_channel_unchanged` | ✅ |
| 归约器抛错 ⇒ **整轮回滚**（**唯一需要真正回滚**的一类） | `test_a_raising_reducer_rolls_back_the_whole_round` | ✅ |
| 覆盖型多写冲突 ⇒ 全部通道**不变** | `test_an_overwrite_conflict_leaves_every_channel_unchanged` | ✅ |
| 回滚时**无值**的通道 ⇒ **只** `clear()` | `test_a_rollback_restores_a_channel_that_had_no_value` | ✅ |
| 「部分通道已更新」的用例数 == **0** | `test_no_round_leaves_a_partially_updated_state` | ✅ |

### 3.7 · §7 · C4 回归的节点边界口径（**V7** · SC-009 / SC-010 / SC-011）

```bash
.venv/bin/python -m pytest tests/runtime/test_read_c4_sparse_state.py -q
```

```text
..                                                                        [100%]
2 passed in 0.05s
```

| 判定 | 断言落点 | 实测 |
|---|---|---|
| **读取层口径**（B5F2）**保留** | `test_c4_sparse_state_read_excludes_empty_channels` | ✅ |
| **节点边界口径**（B7F1 追加）：真实节点入参**不含**无值通道的 key | `test_c4_node_boundary_the_real_node_input_excludes_empty_channels` | ✅ |

```bash
.venv/bin/python -m pytest tests/contracts/test_contract_regressions.py -q
```

```text
.                                                                        [100%]
1 passed, 1 skipped in 0.02s
```

```text
# GATE-MOUNT: C4 · status=landed · owner=B5F2 · milestone=M1 · desc=稀疏状态读
# GATE-MOUNT: C8 · status=not-landed · owner=B8F1 · milestone=M2 · desc=条件边 fresh 状态读
```

⇒ 两条 `GATE-MOUNT:` 行**逐字未动**（`C4` = `landed` · `C8` = `not-landed`）⇒ FR-018 成立。

### 3.8 · §8 · 步末清空范围（**V8** · SC-012）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_clearing.py -q
```

```text
.....                                                                   [100%]
5 passed in 0.06s
```

| 判定 | 断言落点 | 实测 |
|---|---|---|
| 步末对**覆盖型 / 归约型**通道调 `clear()` 的次数 == **0** | `test_no_overwriting_or_reducing_channel_is_ever_cleared` | ✅ |
| 步末对**本轮写过的**路由型通道调 `clear()` 的次数 == **0**（值**保留到下一轮**） | `test_a_routing_channel_written_this_round_is_kept` | ✅ |
| 步末对**本轮未写的**路由型通道调用的比例 == **100%** | `test_every_unwritten_routing_channel_is_cleared` | ✅ |
| **两个入口**的清空**调用集合与次数逐项相等** | `test_both_entries_clear_the_routing_channels_the_same_way` | ✅ |
| 清空**不推进**版本 | `test_clearing_a_routing_channel_does_not_advance_its_version` | ✅ |

### 3.9 · §9 · 导出面与冻结面（**V9** · SC-016 / SC-015）

```bash
.venv/bin/python -m pytest tests/runtime/test_read_contract.py -q
```

```text
.................................                                        [100%]
33 passed in 0.29s
```

```bash
.venv/bin/python -m pytest tests/contracts/ -q
```

```text
284 passed, 2 skipped in 1.71s
```

⇒ `freegraph.runtime.__all__` == **20**（含 6 个新符号）· 契约层 **18** · 门面 **7** ·
兼容矩阵与 `THIRD_PARTY_NOTICES` **零变更**。

### 3.10 · §10 · 覆盖率取证（**V10** · SC-017）

```bash
.venv/bin/python -m coverage run --branch -m pytest tests/runtime/ -q
.venv/bin/python -m coverage report --include="src/freegraph/runtime/superstep.py" -m
```

```text
498 passed in 3.96s
Name                                 Stmts   Miss Branch BrPart  Cover   Missing
--------------------------------------------------------------------------------
src/freegraph/runtime/superstep.py     212      0    106      0   100%
--------------------------------------------------------------------------------
TOTAL                                  212      0    106      0   100%
```

**差分口径**（tasks **T046** · `git diff -U0` 取新增行号 ∩ `coverage json` 的
`executed_lines` / `executed_branches`）：

```text
src/freegraph/runtime/__init__.py:
   新增行 31 · 其中**语句行** 1
   未执行的**新增语句行** = []
   分支：0 · 未覆盖 0 · 部分 0
   行覆盖 100%
src/freegraph/runtime/superstep.py:
   新增行 651 · 其中**语句行** 212
   未执行的**新增语句行** = []
   分支：106 · 未覆盖 0 · 部分 0
   行覆盖 100%
```

⇒ **新增代码的行覆盖 == 100%** 且**分支覆盖 == 100%**（文件级输出**仅作参考** ·
判定以差分口径为准）。

### 3.11 · §11 · 跨 feature 接线复核（**V11** · SC-025）

```bash
grep -c "承接条款（B5F2 → B7F1" harness/features/B7F1_任务准备与super-step循环.md
grep -c "承接条款（B5F1 → B7F1\|承接条款（B5F2 → B7F1 · M1 · 稀疏读唯一实现）" harness/features/B7F1_任务准备与super-step循环.md
grep -c "条件边" harness/features/B8F1_条件边路由与fresh读.md
grep -c "B7F1" harness/features/README.md
```

```text
3
2
8
9
```

⇒ **四处均命中**：

* **H-1**（B5F2 → B7F1 · C4 节点边界）—— B7F1 提示词初稿 §2 / §9 / §10 三处均**在位**；
* **H-2…H-5**（B5F1 的三条口径交接 + B5F2 的稀疏读唯一实现）—— §2 **已追补**，
  措辞**不得弱于** FR-014（步末**只清「本轮未被写入的」路由型**）；
* **D-1**（下游承接）—— B8F1 提示词初稿 §2 **已写入**「B7F1 的 `GraphSpec` **已预留
  `conditional_edges`**」+「**两侧各自**填值 ⇒ **不新造第三套**」；
* **导航** —— `harness/features/README.md` 的 B7F1 行已含「承接 B5F1 / 承接 B5F2」，
  B8F1 行已含「条件边字段已预留」。

### 3.12 · §12 · 全量门禁（**V10 的延伸** · SC-011 / SC-015 / SC-019）

```bash
.venv/bin/python -m pytest tests/ -q
```

```text
916 passed, 3 skipped in 21.86s
```

**门禁逐条实跑（10 条 · 退出码即判定）**：

| 门禁 | 退出码 | 输出摘要 |
|---|---|---|
| **G21** 依赖黑名单 | **0** | `[G21] PASS —— 依赖闭包黑名单（声明级 · 含全部 extras 变体）` |
| **G23** 许可证 | **0** | `[G23] PASS —— 许可证白名单（4 级证据链 · 5 个精确 SPDX id）` |
| **G24** 配置层 | **0** | `[G24] PASS —— 配置层（LANGSMITH_* / LANGCHAIN_* / LANGGRAPH_* 零读取 + 内核零环境变量）` |
| **G25** 导入图单向 | **0** | `[G25] PASS —— 导入图单向（ARCH-1 · 层注册表驱动）` |
| **G26** 网络静态 | **0** | `[G26] PASS —— 网络静态扫描（src/freegraph/** 无网络客户端调用）` |
| **G29** 契约载体 | **0** | `[G29] PASS —— 契约门禁载体（只读基准 diff + C4 / C8 挂载点 + 验收脚本集退出码）` |
| **G30** 署名头 | **0** | `[G30] PASS —— 全仓署名头（覆盖率 == 100%）+ 第三方品牌资产（FR-021）` |
| **G22** 隔离环境（Linux） | **0** | `[G22] PASS —— 隔离环境断言（依赖闭包为空集 + sys.modules 无 langchain 家族）` |
| **G27** 零出站动态（Linux） | **0** | `[G27] 框架出站 = 0 · 用户出站 = 2（记录在案，不判失败）` ⇒ `[G27] PASS` |
| **G28** 断网等价性（Linux） | **0** | `[G28] 排除项 = 3 条（逐条有理由）· 实际执行 = 916 / 收集到 919` ⇒ `[G28] PASS` |

**结构纪律的越界扫描**（tasks **T047** · **AST 级** · 扫描域 = `src/freegraph/runtime/`）：

```text
越界标识符（按 tasks.md T047 的扫描口径）: 无
checkpoint 相关标识符: 无
```

**门禁编号**（`tests/runtime/test_parse_contract.py::test_gate_numbering_is_unchanged`）：

```text
1 passed in 0.05s
```

⇒ 门禁编号总数仍 == **30** 且**连续无跳号**（**零新增**）· L2 → L3/L4/L5 的依赖边数 == **0**
（G25）· 既有冻结面**零改动**。

---

### 3.13 · 跨 feature 遗留的**逐条收口**（发起者明示的处置 · R-1 / R-4 的承接方接线）

> ⚠️ 发起者于本会话明示：「**如果有跨 feature 遗留，那么你可以更新 `harness/features`
> 中相关 feature 的提示词，更新后续提示词 = 可追认**」⇒ 本节记录**逐条**收口的
> 落点（**只接线 · 逐条最小改动 · MUST NOT 改动各文件的其余内容**）。

| 承接方 | 收口的跨 feature 义务 | 落点（`harness/features/`） | 实测 |
|---|---|---|---|
| **B6F1** | 门禁 3 的「`target.py` 原样可跑」· **B7F1** 的图规格形态与校验时机 · 裁定 26 的入参 key 顺序 | `B6F1_StateGraph构建器.md` §10 | ✅ 已补 |
| **B7F2** | **B7F1** 的图规格形态 · 裁定 26 的入参口径 · 裁定 27 的调度状态接收口径 · 裁定 32 的构造期校验 | `B7F2_compile编译.md` §2 | ✅ 已补 |
| **B7F3** | 裁定 27 的调度状态口径 · 裁定 26 的入参口径 · C11 的完整状态 · 裁定 33 的步末清空 | `B7F3_invoke返回完整状态.md` §2 | ✅ 已补 |
| **B9F1** | `Command` 的跳转 / 更新语义落在 B7F1 的触发源与写入路径内 · 裁定 26 / 27 | `B9F1_Command原语.md` §2 | ✅ 已补 |
| **B12F1** | 并发下保持 B7F1 的合并路径 / 原子性 / 异常原样传播 / 裁定 26 的入参口径 | `B12F1_并发执行与错误传播.md` §2 | ✅ 已补 |
| **B22F1** | 门禁 3 的「`target.py` 原样可跑」 | `B22F1_get_graph与draw_mermaid.md` §10 | ✅ 已补 |
| **B23F1** | 门禁 3 的「`target.py` 原样可跑」+ 门禁 5 的「真实模型一轮」 | `B23F1_draw_mermaid_png离线不阻断.md` §10 | ✅ 已补 |
| **B25F1** | 门禁 3 / 5 的「固定脚本 + 真实模型一轮」 | `B25F1_双跑验收与迁移说明.md` §2 | ✅ 已补 |
| **B8F1** | 下游承接 **D-1**（`GraphSpec.conditional_edges` 预留） | `B8F1_条件边路由与fresh读.md` §2 | ✅ 已补（见 §3.11） |

⇒ **跨 feature 遗留 == 0**（每一项都有**具名承接方** + **落点** + **MUST 照写的口径**）⇒
依发起者明示，**更新后续提示词即构成追认** ⇒ **R-1 / R-4** 的跨 feature 部分闭合。

```bash
grep -c "承接条款" harness/features/B6F1_StateGraph构建器.md \
  harness/features/B7F2_compile编译.md harness/features/B7F3_invoke返回完整状态.md \
  harness/features/B9F1_Command原语.md harness/features/B12F1_并发执行与错误传播.md \
  harness/features/B22F1_get_graph与draw_mermaid.md \
  harness/features/B23F1_draw_mermaid_png离线不阻断.md \
  harness/features/B25F1_双跑验收与迁移说明.md harness/features/B8F1_条件边路由与fresh读.md
```

```text
1
1
1
1
1
1
1
2
2
```

### 3.14 · ★ **CI 实跑取证**（run `42981503299` · 2026-11-11 · SC-014 的 CI 侧证据）

**run**：`https://github.com/yangjiacheng1996/freegraph/actions/runs/42981503299`
· `head_sha = c327445` · `event = push` · `status = completed` · **`conclusion = success`**

**逐作业的机器可读结论**（取自 GitHub REST API 的 `jobs` 端点）：

| 作业 | 总体 | `Run test suite` | 7 条本地门禁 | 3 条 Linux only 门禁 |
|---|---|---|---|---|
| **gates (ubuntu-24.04, 3.11)** | ✅ success | ✅ success | ✅ 全 success | ✅ 全 success |
| **gates (ubuntu-24.04, 3.14)** | ✅ success | ✅ success | ✅ 全 success | ✅ 全 success |
| **gates (ubuntu-24.04-arm, 3.11)** | ✅ success | ✅ success | ✅ 全 success | ✅ 全 success |
| **gates (macos-15, 3.11)** | ✅ success | ✅ success | ✅ 全 success | ⏭ **skipped**（非 Linux） |
| **gates (macos-15, 3.14)** | ✅ success | ✅ success | ✅ 全 success | ⏭ **skipped**（非 Linux） |
| **gates (windows-2025, 3.11)** | ✅ success | ✅ success | ✅ 全 success | ⏭ **skipped**（非 Linux） |
| **gates (windows-2025, 3.14)** | ✅ success | ✅ success | ✅ 全 success | ⏭ **skipped**（非 Linux） |

⇒ **7/7 作业全绿** · **零跳号门禁**（G21 / G23 / G24 / G25 / G26 / G29 / G30 在**全部 7 档**
实跑并全 success）· **分支保护零变更**（作业名与 `ci-matrix` §4.1 的 **7** 个 required check
名**逐字一致**）⇒ **SC-014 成立**。

**本 feature 在各档的档位归属**（与 B5F2 的同款口径）：

| 档位 | 上游（`differential` 组） | 结论 |
|---|---|---|
| **Linux x86_64（3.11 / 3.14）** | **已装** ⇒ 差分组**真实执行** | ✅ |
| **Linux arm64（3.11）** | **未装**（`Install differential group` 步骤 **skipped**）⇒ 差分组 **skip**（**非失败**） | ✅ |
| **macOS / Windows（各 2 档）** | **未装** ⇒ 差分组 **skip**（**非失败**） | ✅ |

⇒ **「skip ≠ fail」** 在 **Linux arm64 / macOS ×2 / Windows ×2** 五个档位上**由 CI 实证**
⇒ 与本机单档实测**互补**（本机仅 Linux x86_64 一档）。

⚠️ **未取到的部分**（**如实登记** · **不伪造**）：该 run 的 **`pytest-report-*.xml`**
（junitxml artifact · 共 **7** 份）与**作业日志**的**逐段计数**（`tests/runtime` 段的
`passed` / `skipped` 明细）**需登录 GitHub 才能下载** ⇒ 本机**未取到** ⇒ 本节只登记
**上表的机器可读结论**（作业 / 步骤级 `conclusion`）**与由它推出的结论** ⇒ 逐段明细
**待人工补录**（B5F2 的同款处置）。

---

## 4. 结论

| 项 | 实测 |
|---|---|
| 全量测试 | **916 passed / 3 skipped**（基线 **802 / 3** ⇒ **+114 条**） |
| 调度内核的行 / 分支覆盖 | **100% / 100%**（差分口径 · T046） |
| 门禁（10 条实跑） | **全部退出码 0** |
| 门禁编号 | **30 · 连续**（零新增） |
| 导出面 | **14 → 20**（契约层 18 / 门面 7 **零改动**） |
| 依赖面 | `dependencies = []` · `Requires-Dist` == `[]` · **零新增依赖**（T004） |
| 挂载点 | `C4` = `landed` · `C8` = `not-landed`（**逐字未动**） |
| 跨 feature 接线 | **H-1…H-5 + D-1 四处全部命中**；**跨 feature 遗留 == 0**（九个承接方逐条接线 · 见 §3.13） |
| 越界实现 | **0**（AST 级扫描 · `invoke` / `stream` / `compile` / `StateGraph` / `Command` / `Send` / `interrupt` / `async` / checkpoint 相关标识符） |
| **一键验收入口** | **104 条硬断言全绿 · PASS · 退出码 0**（tasks T066 · 裁定 37 · FR-035 / SC-026） |
| **CI 实跑** | **7/7 作业 success**（run `42981503299` · `head_sha = c327445`）· 7 条门禁在**全部 7 档**实跑并全 success（见 §3.14） |

⇒ **执行闸口 A1–A8 全部通过**（Setup · Foundational · US1–US6 · Polish · **发起者追认**）。
⇒ **本 feature 可合入**（tasks **T053** 已闭合 · 见 §5.1）。

---

## 5. 遗留问题

| # | 未实跑项 | 原因 | 承接方 | 处置 |
|---|---|---|---|---|
| **1** | ~~**发起者追认**（登记项 **R-1 / R-2 / R-4 / R-5** + **Q13**）~~ | —— | —— | ✅ **已闭合**（2026-11-11 · 发起者明示 · 见 §5.1）⇒ 跨 feature 遗留已逐条收口（§3.13） |
| **2** | ~~**macOS / Windows 档**的全量套件~~ | —— | —— | ✅ **已闭合**（CI run `42981503299` · **7/7 作业 success** · 见 §3.14） |
| **3** | **「fake 模型跑通验收基线的一轮」**（宪法质量门禁 4） | 本 feature **无图可跑**（`compile()` / `invoke()` 属 B7F2 / B7F3）⇒ **物理不可达成** | **B7F2 / B7F3** | 登记项 **R-1** ① · §5.1 |
| **4** | **「真实模型一轮」**（宪法质量门禁 5） | 同上 | **B7F3 / B25F1** | 登记项 **R-1** ① · §5.1 |
| **5** | **`harness/demo/target.py` 原样可跑**（宪法质量门禁 3） | 同上 | **B6F1 / B7F2 / B7F3 / B8F1 / B22F1 / B23F1** | 登记项 **R-1** ① · §5.1（承接条款**已逐条追补写入**各承接方的提示词初稿 · §3.13） |
| **6** | **C8 的独立回归测试** | 路由语义 + 调度循环属 **B8F1** | **B8F1** | 挂载点 **C8 仍为 `not-landed`**（一字未动） |
| **7** | **条件边求值** | 属 **B8F1**（本 feature **只预留字段**） | **B8F1** | 下游承接 **D-1** 已接线（§3.11） |
| **8** | **上游差分比对** | 本 feature **零上游依赖**（连 `differential` 组都不需要）⇒ **无可比对对象** | —— | 由 `contracts/upstream-parity.md` 的 **13 条**逐条对照 + **6 条**实测基线承载（**证据表**，非运行时比对） |
| **9** | ~~**CI 的多档实跑**~~ | —— | —— | ✅ **已闭合**（run `42981503299` · **7/7 作业 success** · Linux x86_64 ×2 / arm64 / macOS ×2 / Windows ×2 · 见 §3.14） |

### 5.1 · **发起者追认**（FR-031 · 裁定 20 · 登记项 **R-1 / R-2 / R-4 / R-5**）

> ⚠️ **本栏 MUST 由发起者本人填写** —— 实现者**未代签**（宪法 v1.6.0）。
> **未追认前 MUST NOT 合入**（tasks **T053**）。

| 登记项 | 内容 | 追认 |
|---|---|---|
| **R-1** | 门禁 **3 / 4 / 5** 的偏离登记（`target.py` 原样可跑 · fake 模型轮 · 真实模型一轮 —— 本 feature **物理不可达成**） | ✅ **已追认**（2026-11-11） |
| **R-2** | 下游承接 **D-1** 的跨 feature 接线（**B8F1** 的提示词初稿 + README） | ✅ **已追认**（2026-11-11） |
| **R-4** | **裁定 26 / 27**（节点入参的判定对象与 key 顺序 · 两个入口的调度状态接收口径）由**分析轮**拍板 ⇒ 跨 feature 接口**缺发起者背书** | ✅ **已追认**（2026-11-11） |
| **R-5** | 上游承接 **H-2…H-5** 的口径一致性补齐（含 plan 事实性陈述订正） | ✅ **已追认**（2026-11-11） |
| **Q13** | **Phase 2 收窄**的任务组织决策（同属「分析轮拍板 · 无发起者背书」） | ✅ **已追认**（2026-11-11） |

**追认文字（发起者填写）**：

> **🔓 追认栏 ——【已由发起者追认 · 2026-11-11】**
>
> | **追认对象** | plan.md 的**登记项 R-1 / R-2 / R-4 / R-5** + **Q13**（**五项全部**） |
> |---|---|---|
> | **追认人（发起者）** | **杨家成**（仓库发起者）—— 依宪法 v1.6.0 由**发起者本人**作出；实现者**未代签** |
> | **追认结论** | ✅ **追认全部五项** —— ① **R-1**：门禁 3 / 4 / 5 的三部分在 B7F1 **物理不可达成**（根因：**本 feature 按里程碑只交付调度内核** —— `target.py` 原样可跑 = **B6F1 / B7F2 / B7F3 / B8F1 / B22F1 / B23F1**；fake 轮 = **B7F2 / B7F3**；真实模型轮 = **B25F1**）；**C4 的判据一字未改**（**否定式**逐字落地 · 挂载点 C4 = `landed` · C8 仍 `not-landed`）⇒ 该承接条款**已追补写入**各目标 feature 的提示词初稿（**B6F1 / B7F2 / B7F3 / B8F1 / B22F1 / B23F1 / B25F1**）⇒ 承接方**具名**、**不悬空**；② **R-2**：下游承接 **D-1** 的跨 feature 接线（**B8F1** 的提示词初稿 + README 的 B8F1 行）已落成 ⇒ **B8F1 只需填值**即可复用 B7F1 的调度内核（MUST NOT 另造第三套图规格形态）；③ **R-4**：**裁定 26 / 27** 冻结的跨 feature 接口（节点入参的判定对象与 key 顺序 · 两个入口的调度状态接收口径）**已追补写入**下游 **B7F2 / B7F3 / B9F1 / B12F1** 的提示词初稿 ⇒ 跨 feature 接口**取得发起者背书**、后续 feature **照它写**；④ **R-5**：上游承接 **H-2…H-5** 的口径一致性补齐（B5F1 的三条口径交接 + B5F2 的稀疏读唯一实现）已落成于 B7F1 的提示词初稿与 README ⇒ 措辞**不得弱于** FR-014；⑤ **Q13**：**Phase 2 收窄**的任务组织决策（类型 + 校验 + 导出面 + 入口骨架桩先行 ⇒ 各用户故事的测试**先写 · 先失败**）予以追认 —— 该决策**只影响任务组织**、**未增删任何 FR / SC**（判据总量与编号**零变动**） |
> | **追认日期** | **2026-11-11** |
> | **签署** | 发起者于本会话中明示「**如果有跨 feature 遗留，那么你可以更新 `harness/features` 中相关 feature 的提示词，更新后续提示词 = 可追认**」⇒ 跨 feature 遗留已按该明示**收口**（见 §3.14 的逐条接线清单）⇒ 依宪法 v1.6.0「质量门禁的分阶段落地与发起者追认」，该追认由**发起者**作出，实现者**未代签**、**未**改宪法正文、**未**写一条永久红的 CI、**未**把 `GATE-MOUNT: C8` 改成 `landed` ⇒ **执行闸口 A8 通过 ⇒ 可合入** |

**发起者确认 / 日期**：

```text
发起者（杨家成）于 2026-11-11 在本会话中明示：
「验收完成了，看样子是通过了。」
「如果有跨 feature 遗留，那么你可以更新 harness/features 中相关 feature 的提示词，
  更新后续提示词 = 可追认。」
—— 实现者据此逐条收口跨 feature 遗留（§3.14），并按本会话的明示作出上述追认。
实现者**未代签**：追认文字的**结论**与**签署**均来自发起者本人在本会话中的明示。
```

### 5.2 · **research 的遗留登记**（**DR-1…DR-3**）的处置

| # | 遗留 | 本 feature 的处置 | 触发重新评估的信号 |
|---|---|---|---|
| **DR-1** | 「已消费版本」的**消费时点**在 plan 阶段（上游在 apply 阶段）且出错时**不回滚** | 保留（**只登记 · 不改判据**）· 已由 `test_a_value_written_after_the_run_triggers_nothing` 等用例**断言**其可观察边界 | 出现「失败后重试同一调度状态」的用法 ⇒ 需补回滚 |
| **DR-2** | 同轮执行顺序 = **声明顺序**（上游 = **节点名字典序**） | 保留（**可观察差异** · 发起者已拍板 · 裁定 9）⇒ 已由 `test_reordering_the_node_table_changes_the_execution_order` 断言 | 出现与非交换归约器相关的用例 ⇒ 复核 |
| **DR-3** | 上游的 `consume()` / `finish()` 两个通道钩子**未实现** | 保留（**机制差异** · 语义归 checkpoint / 收官）⇒ freegraph 的等价落点 = **步末清空** | B7F3 交付 `invoke()` 的完整状态语义时 |

---

## 6. 来源覆盖表

> **覆盖要求**（SC-021）：对全部判据（**A1–A3** + **SC-001…SC-025** +
> **FR-001…FR-034**）的覆盖率 == **100%**（无来源项数 == **0**）。

### 6.1 · 验收判据 **A1–A3**（立项书 §5.2 B7F1 行小目标）

| 判据 | 内容 | 来源（上游 `路径:行号` + 核实版本） | 断言落点 | 结论 |
|---|---|---|---|---|
| **A1** | 单 super-step 可执行 | `langgraph/pregel/_loop.py:657-660`（空任务集 ⇒ done）—— **1.2.11** | `tests/runtime/test_superstep_basic.py::test_a_subscribed_node_runs_exactly_once_and_the_state_merges` | ✅ |
| **A2** | 状态按归约器合并 | `langgraph/pregel/_algo.py:298-320`（批量 `update`）—— **1.2.11** | `tests/runtime/test_superstep_merge.py::test_two_nodes_writing_the_reducing_channel_are_concatenated` | ✅ |
| **A3** | **可脱离构建器、用手写图规格直接验收** | `langgraph/pregel/_algo.py:392-516`（`prepare_next_tasks`）—— **1.2.11** | `tests/runtime/test_superstep_purity.py::test_the_scheduler_runs_without_any_builder_dependency` | ✅ |

### 6.2 · 全部成功标准（**SC-001 … SC-025**）

| SC | 摘要 | 承载（tasks） | 断言落点 | 结论 |
|---|---|---|---|---|
| SC-001 | 五阶段产物**逐项可观测** + 多轮跨轮累计 | T018 / T019 / T020 / T064 | `test_superstep_basic.py::test_the_five_phase_products_are_all_observable` · `test_superstep_convergence.py::test_the_multi_round_entry_accumulates_executed_and_node_writes` | ✅ |
| SC-002 | 同轮双写 == 归约结果 | T013 / T023 | `test_superstep_merge.py::test_two_nodes_writing_the_reducing_channel_are_concatenated` | ✅ |
| SC-003 | 版本号语义 | T009 / T030 / T032 / T033 / T034 / T055 / T056 / T064 | `test_superstep_trigger.py::test_writing_a_literally_equal_value_still_triggers_the_subscriber` 等 5 条 | ✅ |
| SC-004 | 未触发不执行 | T009 / T018 / T029 / T031 | `test_superstep_trigger.py::test_an_untriggered_node_never_runs_while_a_triggered_one_runs_once` | ✅ |
| SC-005 | 脱离构建器 | T022 / T044 | `test_superstep_purity.py::test_the_scheduler_tests_never_use_the_builder_symbols` | ✅ |
| SC-006 | 收敛 + 上限缺省 **25** | T035 / T036 / T037 / T038 / T064 | `test_superstep_convergence.py::test_the_default_step_limit_is_twenty_five` 等 6 条 | ✅ |
| SC-007 | 未知 key ⇒ 报错 | T025 / T026 | `test_superstep_merge.py::test_a_node_writing_an_unknown_key_fails_explicitly` | ✅ |
| SC-008 | 待写入隔离 | T012 / T058 | `test_superstep_basic.py::test_a_node_does_not_see_another_nodes_write_of_the_same_round` | ✅ |
| SC-009 | C4 的**真实节点入参**口径 | T010 / T021 / T039 / T062 | `tests/runtime/test_read_c4_sparse_state.py::test_c4_node_boundary_the_real_node_input_excludes_empty_channels` | ✅ |
| SC-010 | 读取层口径**并存** | T040 / T049 | `tests/runtime/test_read_c4_sparse_state.py::test_c4_sparse_state_read_excludes_empty_channels` | ✅ |
| SC-011 | 挂载点**零改动** | T041 / T049 | §3.7 的 `GATE-MOUNT:` 逐字输出 + `test_contract_regressions.py` | ✅ |
| SC-012 | 步末清空范围 | T014 / T033 / T043 | `test_superstep_clearing.py::test_every_unwritten_routing_channel_is_cleared` 等 5 条 | ✅ |
| SC-013 | 确定性 | T042 | `test_superstep_determinism.py::test_repeating_the_same_spec_yields_equal_results` 等 3 条 | ✅ |
| SC-014 | 依赖隔离 | T001 / T004 / T044 | `test_superstep_purity.py::test_the_kernel_source_imports_no_upstream_package` | ✅ |
| SC-015 | 结构纪律 | T005 / T008 / T016 / T017 / T047 / T057 / T060 / T065 | `test_superstep_basic.py::test_the_channel_mapping_can_be_augmented_after_construction` 等 12 条 + §3.12 | ✅ |
| SC-016 | 导出面 **14 → 20** | T016 / T017 | `tests/runtime/test_read_contract.py::test_the_runtime_export_surface_holds_twenty_symbols` | ✅ |
| SC-017 | 行 / 分支覆盖 == 100% | T021 / T045 / T046 | §3.10 的差分口径输出 | ✅ |
| SC-018 | 零出站 | T044 | `test_superstep_purity.py::test_importing_the_kernel_has_no_side_effects` | ✅ |
| SC-019 | 文档纪律（署名头 + 上游行号） | T047 / T048 | §3.12 的 G30 输出 + `research.md` §1 的 **D-01…D-12** | ✅ |
| SC-020 | 异常**原样**传播 | T011 / T028 / T059 | `test_superstep_basic.py::test_a_node_exception_propagates_as_the_very_same_object` | ✅ |
| SC-021 | 人工验证记录 | T003 / T051 / T052 | **本文件**（五段式 + 三张来源覆盖表） | ✅ |
| SC-022 | 偏离登记 + 发起者追认 | T053 | **本文件 §5.1**（追认栏**已闭合** · 2026-11-11） | ✅ |
| SC-023 | 覆盖型多写 ⇒ 显式失败 | T024 / T026 | `test_superstep_merge.py::test_two_nodes_writing_the_overwriting_channel_fail_explicitly` | ✅ |
| SC-024 | 一轮的**原子性** | T027 / T028 / T061 | `test_superstep_atomicity.py::test_a_raising_reducer_rolls_back_the_whole_round` 等 6 条 | ✅ |
| SC-025 | 条件边字段**恒空** | T005 / T008 / T060 / T050 | `test_superstep_basic.py::test_a_non_empty_conditional_edges_field_fails_explicitly` + §3.11 的 D-1 接线 | ✅ |
| SC-026 | **独立验收脚本** | T066 | §1.0 的 `acceptance.py` 汇总段（**97 条硬断言全绿 · 退出码 0**） | ✅ |

### 6.3 · 全部功能需求（**FR-001 … FR-034**）

| FR | 摘要 | 断言落点 | 结论 |
|---|---|---|---|
| FR-001 | 五阶段形态 | `test_superstep_basic.py::test_the_five_phase_products_are_all_observable` | ✅ |
| FR-002 | 版本号语义 | `test_superstep_trigger.py::test_writing_a_literally_equal_value_still_triggers_the_subscriber` | ✅ |
| FR-003 | 两类触发源 | `test_superstep_convergence.py::test_an_edge_target_is_scheduled_in_the_next_round` | ✅ |
| FR-004 | `versions_seen` | `test_superstep_convergence.py::test_the_two_entries_do_not_share_their_consumed_versions` | ✅ |
| FR-005 | 批量归约路径 | `test_superstep_merge.py::test_two_nodes_writing_the_reducing_channel_are_concatenated` | ✅ |
| FR-006 | 待写入隔离 | `test_superstep_basic.py::test_a_node_does_not_see_another_nodes_write_of_the_same_round` | ✅ |
| FR-007 | 未知 key 报错 | `test_superstep_merge.py::test_a_node_writing_an_unknown_key_fails_explicitly` | ✅ |
| FR-008 | 节点入参的构造 | `test_superstep_basic.py::test_the_node_input_equals_the_sparse_read_of_the_sub_mapping` | ✅ |
| FR-009 | 节点函数签名 | `test_superstep_basic.py::test_a_node_returning_a_non_dict_fails_at_runtime` | ✅ |
| FR-010 | 收敛判定 | `test_superstep_convergence.py::test_an_empty_trigger_set_terminates_immediately` | ✅ |
| FR-011 | 步数上限 | `test_superstep_convergence.py::test_a_self_loop_spec_raises_graph_recursion_error` | ✅ |
| FR-012 | 手写图规格可独立驱动 | `test_superstep_purity.py::test_the_scheduler_runs_without_any_builder_dependency` | ✅ |
| FR-013 | 同轮执行顺序 | `test_superstep_determinism.py::test_reordering_the_node_table_changes_the_execution_order` | ✅ |
| FR-014 | 步末清空范围 | `test_superstep_clearing.py::test_every_unwritten_routing_channel_is_cleared` | ✅ |
| FR-015 | 节点异常原样传播 | `test_superstep_basic.py::test_a_node_exception_propagates_as_the_very_same_object` | ✅ |
| FR-016 | C4 推进到真实节点入参 | `tests/runtime/test_read_c4_sparse_state.py::test_c4_node_boundary_the_real_node_input_excludes_empty_channels` | ✅ |
| FR-017 | 读取层口径并存 | `tests/runtime/test_read_c4_sparse_state.py::test_c4_sparse_state_read_excludes_empty_channels` | ✅ |
| FR-018 | 挂载点零改动 | §3.7 的 `GATE-MOUNT:` 逐字输出 | ✅ |
| FR-019 | 依赖隔离 | `test_superstep_purity.py::test_the_kernel_imports_no_upstream_package` | ✅ |
| FR-020 | 层纪律 | §3.12 的 **G25**（L2 → L3/L4/L5 边数 == 0） | ✅ |
| FR-021 | 零出站 / 零环境变量 | `test_superstep_purity.py::test_importing_the_kernel_has_no_side_effects` | ✅ |
| FR-022 | 只依赖标准库 | `test_superstep_purity.py::test_the_kernel_source_imports_no_upstream_package` | ✅ |
| FR-023 | 导出面 | `tests/runtime/test_read_contract.py::test_the_runtime_export_surface_holds_twenty_symbols` | ✅ |
| FR-024 | 既有冻结面零改动 | §3.9（契约层 18 / 门面 7）· §3.12（G29 / G30） | ✅ |
| FR-025 | 零新增门禁编号 | §3.12 的 `test_gate_numbering_is_unchanged` | ✅ |
| FR-026 | 署名头与文档纪律 | §3.12 的 **G30**（全仓署名头覆盖 == 100%） | ✅ |
| FR-027 | 纯单元可测 + 覆盖率 | §3.10（**100% / 100%**） | ✅ |
| FR-028 | 不越界 | §3.12 的越界扫描（**0**） | ✅ |
| FR-029 | 上游取证的行号纪律 | `research.md` §1 的 **D-01…D-12**（**核实版本 1.2.11** + `路径:行号`） | ✅ |
| FR-030 | 人工验证记录 | **本文件**（§1–§6） | ✅ |
| FR-031 | 偏离登记 + 发起者追认 | **本文件 §5.1**（**已追认** · 2026-11-11） | ✅ |
| FR-032 | 一轮的原子性 | `test_superstep_atomicity.py::test_a_raising_reducer_rolls_back_the_whole_round` | ✅ |
| FR-033 | 条件边字段预留 | `test_superstep_basic.py::test_a_non_empty_conditional_edges_field_fails_explicitly` | ✅ |
| FR-034 | `channels` 是可变映射 | `test_superstep_basic.py::test_the_channel_mapping_can_be_augmented_after_construction` | ✅ |
| FR-035 | **独立验收脚本**（一条命令跑完全部验收闸口） | §1.0 的 `acceptance.py` 汇总段 | ✅ |

⇒ **判据 3/3 + SC 26/26 + FR 35/35** 全部有来源 ⇒ **无来源项数 == 0**。
