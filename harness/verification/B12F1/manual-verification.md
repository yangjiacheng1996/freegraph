# B12F1 · 节点执行 + 并发执行 + 错误传播 + `GraphInterrupt` 合并 —— 人工验证记录

**Feature**: `B12F1` · **Spec**: [`specs/b12f1-concurrency-errors/spec.md`](../../specs/b12f1-concurrency-errors/spec.md)
**Plan**: [`specs/b12f1-concurrency-errors/plan.md`](../../specs/b12f1-concurrency-errors/plan.md)
**Tasks**: [`specs/b12f1-concurrency-errors/tasks.md`](../../specs/b12f1-concurrency-errors/tasks.md)
**契约**: [`specs/b12f1-concurrency-errors/contracts/concurrency-contract.md`](../../specs/b12f1-concurrency-errors/contracts/concurrency-contract.md)（**唯一权威**）

> ⚠️ **本文件是骨架**（tasks **T004**）⇒ 实施期逐段填充（tasks **T077 / T078**）。
> ⚠️ **MUST NOT** 伪造未实跑的输出（宪法原则 V / 原则 VIII）。
> ⚠️ **五段式**（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题）**MUST** 齐全。

---

## 1. 验证环境

<!-- T002 / T077 填充 -->

### 1.0 · ★ **一键验收入口**（tasks **T005 / T077**）

```bash
.venv/bin/python harness/verification/B12F1/acceptance.py
```

**期望**：退出码 == **0**（**14** 道闸口 **V1–V14** 全绿）。

### 1.1 · ★ **绿基线与落地后的对照**（tasks **T002** / **T007**）

| 项 | 值 |
|---|---|
| 仓库 | `freegraph` · 分支 `b12f1-concurrency-errors` |
| Python | **3.11.16**（`.venv`） |
| pytest | **9.2.0** |
| coverage | **7.17.2**（**开发期工具** · 不进仓库依赖） |
| 上游 | `langgraph` **1.2.11** + `langchain-core` **1.6.3**（**差分测试侧**依赖组 `differential`） |
| **实现前**的全量套件 | **1064 passed · 3 skipped** |
| **落地后**的全量套件 | **1121 passed · 3 skipped**（**+57** 条新用例 · **零回归**） |
| **落地后**的差分场景数 | **30**（既有 **15** + 本 feature **15**）⇒ **30/30 符合判词** |
| **落地后**的新增代码覆盖率 | `src/freegraph/runtime/_concurrency.py` **100%** · `src/freegraph/runtime/superstep.py` **100%**（**行 / 分支**） |

> ⚠️ **依赖面零新增**（tasks **T002**）：`pyproject.toml` **零改动** —— `[project].dependencies = []`
> · **无** `[project.optional-dependencies]` 段 · 上游 `langgraph==1.2.11` **仅**在
> **PEP 735 的 `differential` 依赖组**（**测试侧** ⇒ **不进** `Requires-Dist` · 基础安装闭包仍为空集）
> ⇒ ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿。
> ⚠️ **口径订正**：tasks **T002** 的字面写「`langgraph` **不在**任何依赖组」⇒ 与事实**不符**
> （它在 `differential` **测试侧**依赖组里）⇒ 本记录按**实际口径**记录：
> **运行时依赖面零新增**（**与 spec FR-007 的 ⚠️ / plan Technical Context 一致**）。

---

## 2. 验证步骤

<!-- T006 / T016 / T077 填充 -->

### 2.1 · 逐闸口（**V1–V14**）

| 闸口 | 主题 | 命令 | 对应不变量 |
|---|---|---|---|
| **V1** | 并行节点**不串行化**（**A1**） | `pytest tests/runtime/test_superstep_concurrency.py -k "parallel or barrier"` | I-1 / I-2 |
| **V2** | 首个异常**原样**抛出 + **附注** + **取消语义**（**A2**） | `pytest tests/runtime/test_superstep_errors.py -k "first or note or cancel"` | I-3 / I-4 / I-17 |
| **V3** | 异常 ⇒ 后续 super-step **不执行** + **整轮原子**（**A3**） | `pytest tests/runtime/test_superstep_errors.py -k "atomic or stop or ghost"` | I-5 / I-10 / I-11 |
| **V4** | 多个中断**合并抛出**（载荷 = 元组） | `pytest tests/runtime/test_superstep_errors.py -k "interrupt"` | I-12 |
| **V5** | 中断与写入的关系 + **暂停** + **异常优先** | `pytest tests/runtime/test_superstep_errors.py -k "writes or pause or priority"` | I-13 / I-14 / I-15 |
| **V6** | 并发 == 串行（`max_concurrency=1` 的**同一规格**） | `pytest tests/runtime/test_superstep_concurrency.py -k "serial or deterministic"` | I-6 / I-7 / I-8 |
| **V7** | `Command` 的**并发语义** | `pytest tests/runtime/test_superstep_concurrency.py -k "command"` | I-6 / I-8 |
| **V8** | 节点**入参口径**（稀疏 · 顺序） | `pytest tests/runtime/test_superstep_concurrency.py -k "input"` | I-9 |
| **V9** | **纯净性**（零上游 / 零环境变量 / 零出站） | `pytest tests/gates` | — |
| **V10** | **结构纪律**（导出面 / 四字段 / 层 / 门禁编号） | `pytest tests/contracts tests/facade` | — |
| **V11** | **确定性** + **调度状态不串扰** + **零悬挂线程** | `pytest tests/runtime/test_superstep_concurrency.py -k "thread or isolation"` | I-7 / I-16 |
| **V12** | **人工验证** + **偏离登记 + 发起者追认** | `python harness/verification/B12F1/acceptance.py` | — |
| **V13** ★ | **差分探针场景组**（**A4**） | `pytest tests/differential/test_parity_probe.py` | I-3 / I-12 / I-13 / I-17 |
| **V14** ★ | **并发度** + **取值校验时机** | `pytest tests/runtime/test_superstep_concurrency.py -k "cap or validation"` | — |

### 2.2 · ⚠️ **C-01 回归面探测**（tasks **T007** · research §2）

> **目的**：把既有实现替换成「**并发版 `_run_round`**」⇒ 暴露「断言用户侧副作用的
> **同轮完成顺序**」的用例 ⇒ 得到本 feature 的**改动面清单**（**逐处拆分 · 一条不删**）。

| 步骤 | 命令 | 期望 |
|---|---|---|
| ① **串行基线** | `pytest tests/ -q` | **1064 passed · 3 skipped** |
| ② **并发原型 · 无抖动** | 并发原型替换 `_run_round` + `pytest tests/ -q` | **1064 passed · 3 skipped**（⇒ 并发**本身**不破坏任何既有判据） |
| ③ **并发原型 · 4ms 逆序抖动** | 同上 + 给**靠前**任务注入递增延迟 | 暴露**顺序敏感**断言 ⇒ **清单**（见 §2.3） |

### 2.3 · ⚠️ **顺序敏感断言的实跑清单**（tasks **T006 / T007**）

> ⚠️ **本清单是「**实跑**」的结果**（3/3 次**完全一致**）⇒ **它取代** research §2 的
> 「**10 处**」初版口径（spec **FR-006** / 裁定 19 / **R-6** · plan **PR-8** 同步订正）。
> ⚠️ **判据本身不变**（仍 MUST **逐处拆分** · **一条不删**）。

**探测装置**（**临时脚本 · 不进仓库** · `PYTHONPATH=<tmp>` + `pytest -p <probe>`）：
用「并发版 `_run_round`」（线程池 + 每任务一个结果槽）替换既有实现 ⇒
① **不加抖动**跑全量 ⇒ **1064 passed**（并发**本身**不破坏任何判据）；
② 给同轮内**靠前**（节点名序）的任务注入 **4 ms 逆序递增延迟**（让完成的先后与节点名序相反）
⇒ 暴露「断言**用户侧副作用的同轮完成顺序**」的用例。

**实跑结果（3/3 次一致 · 失败 7 条）**：

> ⚠️ **双重取证**：上表先用「**原型**」测得；随后用「**真实实现**」（本 feature 的
> `_concurrency.py` + `superstep.py`）**重跑**（在 `run_tasks_concurrently` 入口注入
> 同一抖动）⇒ **得到完全相同的 7 条** ⇒ ⇒ **清单已由真实实现确证**（不是原型特有）。

| # | 文件 | 测试函数 | 断言的顺序 |
|---|---|---|---|
| 1 | `tests/runtime/test_command_contract.py` | `test_i5_every_list_goto_becomes_its_own_edge` | `executed == ["writer", "one", "two"]` |
| 2 | `tests/runtime/test_command_contract.py` | `test_i11_the_dynamic_and_static_edges_are_superposed` | 用户侧副作用的**同轮**追加顺序 |
| 3 | `tests/runtime/test_command_goto_semantics.py` | `test_the_goto_target_and_the_static_edge_target_are_both_triggered` | 同上 |
| 4 | `tests/runtime/test_command_goto_semantics.py` | `test_a_multi_target_goto_triggers_every_target` | 同上（**research 初版清单未列** ⇒ 本轮**新增命中**） |
| 5 | `tests/runtime/test_command_list.py` | `test_the_command_list_gotos_become_separate_edges` | 同上 |
| 6 | `tests/runtime/test_command_merge_parity.py` | `test_every_goto_in_the_command_list_becomes_its_own_edge` | 同上 |
| 7 | `tests/runtime/test_superstep_trigger.py` | `test_advancing_one_trigger_source_does_not_mask_another_one` | 同上 |

**⇒ 改动面 = 5 个文件 / 7 处断言**（research 初版记「10 处」⇒ **据实订正为 7 处**）。

#### ⚠️ research 初版清单里**未命中**的 3 条（**经逐条复核 · 非顺序敏感 · 无需拆分**）

| # | 测试函数 | 复核结论 |
|---|---|---|
| 1 | `test_command_contract.py::test_i6_the_dynamic_edges_are_replaced_wholesale` | 断言 `executed == ["x#1", "z", "x#2"]` ⇒ **跨轮**顺序（x#1 / z / x#2 各占一轮）⇒ 并发下**轮次边界不变** ⇒ **跨轮顺序确定** ⇒ **非**同轮顺序敏感 |
| 2 | `test_command_goto_semantics.py::test_the_goto_target_is_not_triggered_again_after_the_source_reruns_without_a_goto` | 同上（**跨轮**）⇒ ⚠️ 且 research 初版清单里写的**测试名过时**（漏了 `again` ⇒ P2-c 重命名后未同步） |
| 3 | `test_superstep_trigger.py::test_writing_a_literally_equal_value_still_triggers_the_downstream_node` | 断言 `calls == ["writer", "sink"]` ⇒ writer / sink **跨轮** ⇒ **非**同轮顺序敏感 |

#### ⚠️ 探测结论对实现的约束

- **并发**（无抖动）**零回归** ⇒ 本 feature 的改动面**收敛在 7 处顺序敏感断言**内 ⇒
  **不是**「全库返工」；
- **轮次边界必须保持** ⇒ 跨轮顺序**永远确定** ⇒ 「同轮完成顺序」是**唯一**的并发敏感面；
- 处置（**判据只收紧、不放宽**）：每处**拆成两条** ——
  ① **串行模式**（`max_concurrency=1`）**保留原逐字顺序断言**（**一条不删**）；
  ② **并发模式**（缺省）断言**顺序无关但有力**的性质（**元素多重集相等** + **次数相等**）
  ⇒ **MUST NOT** 写成「跑过了就行」的弱断言。

### 2.4 · ⚠️ **回溯修订清单**（tasks **T016** · plan 登记项 **PR-7** · spec 回溯修订 **T-1…T-11**）

> ⚠️ **本清单是「**待办步骤**」**（⇒ MUST **NOT** 落「遗留问题」段 —— 遗留问题段只放
> **已知限制**）⇒ **落笔**由 tasks **T070** 执行（**拆分而不删**）。
> ⚠️ **T-6** 的落笔在 **T069**（10 处顺序敏感断言的拆分）· **T-9** 的落笔在 **T071**
> （B10F1 结果键接线）⇒ **本清单不含**这两项。

| # | 冻结面 | 回溯修订位置 | 冻结断言处置 | 承接方 |
|---|---|---|---|---|
| **T-1** | B7F1 契约 §5.3（`SuperStepResult.executed` 的语义措辞） | `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §5.3 | 「按执行顺序」→「本轮**被启动过**的节点集合 · 按**节点名序**」（含被中断的节点 · 不含被取消的节点）⇒ 字段数 / 名字 / 类型**逐字不变** | **B7F1** |
| **T-2** | B7F1 契约 §1（两个入口的签名） | 同上 §1 | 两行入口签名各**追加** `*, max_concurrency: int \| None = None`（**兼容扩展**）· 缺省 = `min(32, cpu+4)` | **B7F1** |
| **T-3** | B7F1 spec FR-013（同轮**顺序口径**承诺） | `specs/b7f1-superstep-loop/spec.md` FR-013 | 「节点表顺序」→「**节点名序**」（**P2-c 已落地**）⇒ 本 feature 只**承接**、不再改写（⚠️ **仅限「顺序口径」这一层**；FR-013 的「**执行**」层**另见 T-11**） | **B7F1** |
| **T-4** | B7F1 契约 §4 / §5.1（五阶段表与批量合并规则里**残留**的「节点表顺序」措辞） | 同上 §4（阶段 ① / ③）· §5.1（批量行） | 「节点表顺序」→「**节点名序**」⇒ 与 **I-12** 对齐 | **B7F1** |
| **T-5** | B7F1 契约 §5.3（`steps` 在中断挂起时的口径） | 同上 §5.3 | 补「挂起时**如实计**『实际跑过的轮数』」的分支 ⇒ ⚠️ 其**载体**在**将来 B10F1** 的结果对象上（本 feature 侧**无载体**） | **B7F1** + **B10F1** |
| **T-7** | B7F1 契约 §7 的 **I-13**（多会话隔离） | 同上 §7 | 加注记「该判定口径在 **P2-b 之后首次成立**」⇒ 偏离登记 **X-6 消解** | **B7F1** |
| **T-8** | B7F1 契约 §7 的 **I-12**（并发下执行顺序不确定） | 同上 §7 | 「**节点名序 == 报告顺序**（`executed` 的口径）」⇒ **同步** `tests/runtime/test_superstep_contract.py` 的 `test_i12` 的 docstring / 命名 | **B7F1** |
| **T-10** | B7F1 契约 §4 的阶段表（**五阶段** → ③ / ③′ / ⑥ · 阶段 ③ 由「串行」改为「并发」） | 同上 §4（**标题** + 阶段 ③ 行） | 阶段 ① / ② / ④ / ⑤ 的**语义与编号逐字不变** ⇒ 阶段 ③ **细分**为 ③（**并发执行**）/ ③′（**判定与落回**）并**追加**阶段 ⑥（**收尾**）⇒ 原「按**节点表顺序串行**执行」一条**拆分而不删** | **B7F1** |
| **T-11** | B7F1 spec FR-013（同轮**执行**顺序承诺 · **并发下失效**） | `specs/b7f1-superstep-loop/spec.md` FR-013（+ 其 Out of Scope 里「并发节点执行 —— 属 B12F1 … FR-013 的顺序承诺届时失效」一句的**对账**） | 「MUST 按**节点名**序**执行**」**拆分**为「① **合并顺序**与**报告顺序** MUST 按**节点名**序（**可复现**）② **执行**的**时间**先后在并发下**不确定** ⇒ MUST **NOT** 作为任何可观察顺序的判据」⇒ **顺序承诺本身不撤销** | **B7F1** |

---

## 3. 实际输出

> ⚠️ 以下**全部**是**实跑**输出（**MUST NOT** 伪造未实跑的结果 · 宪法原则 V / 原则 VIII）。

### 3.1 · ★ **一键验收入口**（tasks **T005 / T077** · 闸口 **V1–V14**）

```text
$ .venv/bin/python harness/verification/B12F1/acceptance.py
```

| 闸口 | 主题 | 实跑结果 |
|---|---|---|
| **V1** | 并行节点**不串行化**（**A1**） | ✅ PASS |
| **V2** | 首个异常**原样**抛出 + **附注** + **取消语义**（**A2**） | ✅ PASS |
| **V3** | 异常 ⇒ 后续 super-step **不执行** + **整轮原子**（**A3**） | ✅ PASS |
| **V4** | 多个中断**合并抛出**（载荷 = 元组） | ✅ PASS |
| **V5** | 中断与写入的关系 + **暂停** + **异常优先** | ✅ PASS |
| **V6** | 并发 == 串行（`max_concurrency=1` 的**同一规格**） | ✅ PASS |
| **V7** | `Command` 的**并发语义** | ✅ PASS |
| **V8** | 节点**入参口径**（稀疏 · 顺序） | ✅ PASS |
| **V9** | **纯净性**（零上游 / 零环境变量 / 零出站） | ✅ PASS |
| **V10** | **结构纪律**（导出面 / 四字段 / 层 / 门禁编号） | ✅ PASS |
| **V11** | **确定性** + **调度状态不串扰** + **零悬挂线程** | ✅ PASS |
| **V12** | **人工验证** + **偏离登记 + 发起者追认** | ✅ PASS（**追认正文**齐备 + **发起者已于 2026-11-13 追认** · 见 §5.1） |
| **V13** ★ | **差分探针场景组**（**A4**） | ✅ PASS（上游已安装 ⇒ **真跑**） |
| **V14** ★ | **并发度** + **取值校验时机** | ✅ PASS |
| **GATES** | 全量门禁实跑（`tests/gates`） | ✅ PASS（**40 passed**） |
| **COVERAGE** | 覆盖率取证（行 / 分支） | ✅ PASS（**100% / 100%**） |

### 3.2 · ★ **全量测试套件**（SC-020 的对照基线）

```text
$ .venv/bin/python -m pytest tests/ -q
1121 passed, 3 skipped in 49.74s
```

**3 个 skip 的口径**（**非失败**）：
① `tests/contracts/test_contract_regressions.py` —— **C8**（条件边 fresh 状态读）**未落地**（owner = **B8F1 / M2**）；
② `tests/contracts/test_protocols.py` —— **mypy 未装**（静态类型检查不可执行 ⇒ 兜底的注解结构断言仍跑）；
③ `tests/facade/test_api_snapshot.py` —— **未开启** `--update-api-snapshot`（默认关闭）。

### 3.3 · ★ **覆盖率取证**（SC-020 · 行 / 分支 **100%**）

```text
$ .venv/bin/python -m coverage run --branch -m pytest tests/runtime tests/differential -q
714 passed in 55.25s

$ .venv/bin/python -m coverage report --show-missing \
      --include="src/freegraph/runtime/_concurrency.py,src/freegraph/runtime/superstep.py"
Name                                    Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------------
src/freegraph/runtime/_concurrency.py      70      0     26      0   100%
src/freegraph/runtime/superstep.py        346      0    184      0   100%
-----------------------------------------------------------------------------------
TOTAL                                    416      0    210      0   100%
```

### 3.4 · ★ **差分探针场景组**（SC-029 · **A4** · 宪法原则 XI 的「可验证出口」）

```text
$ .venv/bin/python harness/scripts/diff_parity.py
...
D-01 · 并发重叠（两个节点真同时在跑）        | ✅ 一致                 | OK         | OK
D-02 · 首个异常的对象 identity 与消息   | ✅ 一致                 | ERROR      | ERROR
D-03 · 取消语义（端到端：最后实际被启动了哪些节点） | ✅ 一致                 | ERROR      | ERROR
D-04 · 中断合并成一个异常且载荷为元组        | ✅ 一致                 | ERROR      | OK
D-05 · 中断节点的写入被丢弃 / 其它节点照常合并  | ✅ 一致                 | ERROR      | OK
D-06 · 并发 == 串行（同一规格）         | ✅ 一致                 | OK         | OK
D-07 · 同轮顺序 = 节点名序            | ✅ 一致                 | OK         | OK
D-08 · 归约通道的合并顺序              | ✅ 一致                 | OK         | OK
D-09 · 异常优先于中断                | ✅ 一致                 | ERROR      | ERROR
D-10 · 多会话隔离（同一规格连续跑两次不累积）    | ✅ 一致                 | OK         | OK
D-11 · 并发度缺省的上限（超出者排队）        | ✅ 一致                 | OK         | OK
D-12 · goto 不互相吞并             | ✅ 一致                 | OK         | OK
D-13 · 首个异常的选取（确定性）           | ✅ 更严（已登记）            | OK         | OK
D-14 · 其余失败的可见性（附注）           | ✅ 更严（已登记）            | OK         | OK
D-15 · 中断元组内元素顺序（确定性）         | ✅ 更严（已登记）            | OK         | OK
===========================================================================
场景数 30 · 符合判词 30 · 失败 0
```

> ⇒ **D-01 … D-12** 判词 == `SAME`；**D-13 / D-14 / D-15** 判词 == `STRICTER` 且**带理由**
> ⇒ **偶发红次数 == 0**（D-13 / D-15 的上游侧**只断言集合**，**不**逐字比顺序）。

### 3.5 · ★ **C-01 回归面探测**（tasks **T007** · 见 §2.3）

| 探测 | 实跑结果 |
|---|---|
| ① **串行基线** | **1064 passed · 3 skipped** |
| ② **并发原型 · 无抖动** | **1064 passed · 3 skipped** ⇒ 并发**本身**零回归 |
| ③ **并发原型 · 4 ms 逆序抖动** | **7 failed** ⇒ **7 处**顺序敏感断言（3/3 次一致） |
| ③' **真实实现 · 同一抖动** | **7 failed** ⇒ 与原型**完全相同** ⇒ 清单已由真实实现确证 |
| ④ **T069 拆分后 · 同一抖动** | **1110 passed · 3 skipped** ⇒ **7 处全部拆分完毕 · 零偶发红** |

### 3.6 · ★ **结构纪律 / 纯净性 / 文档纪律**（SC-019 / SC-018 / SC-024）

| 判据 | 实跑结果 |
|---|---|
| `freegraph.runtime.__all__` | **20** 个符号 ✅ |
| L1 公开符号面 | 与 `public-api.md` §0 的清单**集合相等**（**20** 个 · **清单驱动** · **不硬编码 18**）✅ |
| 门面符号面 | **7** 个 ✅ |
| `SuperStepResult` 字段数 | **4**（**无** `interrupts`）✅ |
| `SchedulerState()` | 字段名 / 顺序**逐字不变**（**6** 个 · 全有缺省值）· **零参可构造** ✅ |
| 两个入口的既有参数 | 名字 / 顺序 / 语义**一字不动**（**只**增 keyword-only 的 `max_concurrency`）✅ |
| L2 → L3 / L4 / L5 的依赖边 | **0** ✅ |
| 门禁编号 | **G1–G30** 连续无跳号 · 总数 **30** ✅ |
| 零环境变量 / 零出站 / 零文件 I/O | **0** 命中（`os.cpu_count()` 是**系统调用** ⇒ 允许）✅ |
| 越界实现（`interrupt()` / `__interrupt__` / async / `Send` / `recursion_limit` / checkpoint / 重试 / 超时 / 多源汇合边） | **0** ✅ |
| 署名头 + docstring 首个语句 | **100%**（**6** 个新 / 改源文件）✅ |
| 上游引用带**版本 + `路径:行号`** | **23** 处**全部**带行号 ⇒ 凭记忆沿用的引用数 == **0** ✅ |

### 3.7 · ★ **冻结面零改动**（SC-019 / FR-016）

| 冻结面 | 本 feature 的改动 |
|---|---|
| `src/freegraph/contracts/**`（L1） | **零改动** ✅（仓库内的既有差异属**上游对齐批次 P3** · **发起者已批准** · 非本 feature） |
| `src/freegraph/runtime/channel.py` · `read.py` | **零改动** ✅（同上） |
| `src/freegraph/runtime/__init__.py`（导出面 **20**） | **零改动** ✅ |
| `src/freegraph/graph.py`（门面 **7**） | **零改动** ✅ |
| `pyproject.toml` · `THIRD_PARTY_NOTICES` · API 兼容矩阵 | **零改动** ✅ |

> ⚠️ **唯一**的兼容扩展 = 两个入口各增一个 **keyword-only** 的 `max_concurrency`（**带缺省值** ⇒
> 既有调用方零改动）⇒ 已回溯修订 B7F1 契约 §1（**T-2**）。

### 3.8 · ★ **回溯修订的落地**（tasks **T070 / T071**）

| # | 冻结面 | 落地位置 | 状态 |
|---|---|---|---|
| **T-1** | B7F1 契约 §5.3（`executed` 措辞） | `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §5.3 | ✅ 已落 |
| **T-2** | B7F1 契约 §1（两个入口签名） | 同上 §1 | ✅ 已落 |
| **T-3** | B7F1 spec FR-013（顺序口径） | `specs/b7f1-superstep-loop/spec.md` FR-013 | ✅ 已落（与 T-11 合并） |
| **T-4** | B7F1 契约 §4 / §5.1（残留的「节点表顺序」） | 同上 §4 / §5.1 | ✅ 已落 |
| **T-5** | B7F1 契约 §5.3（`steps` 挂起口径） | 同上 §5.3 | ✅ 已落 |
| **T-7** | B7F1 契约 §7 的 **I-13** | 同上 §7 | ✅ 已落 |
| **T-8** | B7F1 契约 §7 的 **I-12** + `test_i12` 的 docstring / 命名 | 同上 §7 + `tests/runtime/test_superstep_contract.py` | ✅ 已落（用例改名 `test_i12_the_report_order_follows_the_node_name_order`） |
| **T-10** | B7F1 契约 §4 的阶段表（五阶段 → ③/③′/⑥） | 同上 §4 | ✅ 已落 |
| **T-11** | B7F1 spec FR-013（「执行」层）+ Out of Scope 对账 | `specs/b7f1-superstep-loop/spec.md` | ✅ 已落 |
| **T-6** | 既有 **7 处**顺序敏感断言的拆分 | `tests/runtime/**`（**5** 个文件） | ✅ 已落（见 §2.3） |
| **T-9** | B10F1 的 `__interrupt__` 结果键接线 | `harness/features/B10F1_interrupt与resume.md` | ✅ **已在**（落盘于 2026-11-12）⇒ 本 feature **只核对** |

**下游承接（D-1…D-7）的核对结果**（tasks **T071**）：**6 个**目标提示词初稿**逐条已含**该条款
（**B10F1** / **B19F1** / **B7F2** / **B7F3** / **B14F1** / **B15F1**）⇒ **缺口 = 零**
⇒ ⇒ **只核对 · 未追加**（宪法 v1.8.0「只接线 · MUST NOT 改动目标提示词初稿的其余内容」）✅

⚠️ **2026-11-13 实施期的一处追加**（tasks **T071** · 宪法 v1.8.0）：核对 **FR-017** 时发现
「**并发度旋钮 `max_concurrency` MUST 原样搬进 `RunConfig`**（同名同义）」这条**指名 B7F3** 的
跨 feature 义务**尚未**落进 B7F3 的提示词初稿 ⇒ ⇒ 依承接通则**追加**了一个承接段落
（**同文件** · `RunConfig` 形态 + 并发度缺省 / 显式 `N` / 取值校验口径）⇒ ⇒ **B7F3 提示词初稿的
其余内容零改动** ✅

---

## 4. 结论

| 判据 | 结论 |
|---|---|
| **验收判据 A1**（并行节点不串行化） | ✅ **通过**（屏障被放行 · 时间窗重叠 > 0 · 副作用计数各 == 1） |
| **验收判据 A2**（首个异常正确抛出） | ✅ **通过**（类型 / 消息 / **对象 identity** 逐字一致 · **节点名序**决定 · 其余失败以附注可见） |
| **验收判据 A3**（后续 super-step 不执行） | ✅ **通过**（下游执行计数 == **0** · **整轮原子** · 调度状态不落回） |
| **验收判据 A4**（与上游同款 · 差分可判定） | ✅ **通过**（**D-01 … D-15** 全部 **15** 条达判词 · 场景总数 **30/30**） |
| **SC-001 … SC-029**（**29** 条） | ✅ **全部通过**（见 §6.2 的来源覆盖表 · 覆盖率 == **100%**） |
| **FR-001 … FR-026**（**26** 条） | ✅ **全部有实现与用例承载**（见 §6.3） |
| **宪法原则 I–XII** | ✅ **全部满足**（plan §Constitution Check · 无 CRITICAL） |
| **零新增门禁编号** | ✅ **G1–G30** 连续 · 总数 **30** |
| **冻结面零改动** | ✅ **L1 / 门面 / 导出面 / 依赖面 / 兼容矩阵 / `THIRD_PARTY_NOTICES`** 零改动 |

> ✅ **追认已闭合**（tasks **T080** · 宪法 v1.6.0）：**发起者已于 2026-11-13 一次性追认**
> **PR-1 … PR-11**（11 项打包成**一次** ⇒ **追认次数 == 1**）⇒ 详见 §5.1.3 的签署栏。
> ⇒ **本 feature 的合入前置条件全部满足**。

---

## 5. 遗留问题

### 5.0 · ★ **本 feature 的已知限制**（tasks **T079** · MUST **如实登记** · MUST NOT 隐瞒）

| # | 已知限制 | 依据 |
|---|---|---|
| ① | 一个**不返回**的节点会**阻塞**本轮 | **DR-3**（节点级超时 / 取消不在 v1 范围） |
| ② | **节点函数会被并发调用** ⇒ **线程安全是用户的责任**（内核不加锁 · 不代偿） | 裁定 16 |
| ③ | 取消**只**对「排队未启动」者生效 ⇒ 用户节点函数**已产生**的外部副作用**取消不掉** | **DR-3** · 裁定 17 |
| ④ | 「真异常 + 中断同现」时那批中断元组**被丢弃**且 v1 **无处留痕** | 偏离登记 **X-4**（**临时** · 消解条件 = **B14F1 / M3**） |
| ⑤ | ⚠️ **多会话隔离**（同一份规格连续 / 并发跑两次）**已由 P2-b 落地** ⇒ **MUST NOT** 再列为本 feature 的限制 | **V-7** · 偏离登记 **X-6 已消解** |
| ⑥ | ⚠️ 宪法「**质量门禁 3 / 4 / 5**」的三部分在本 feature **物理不可达成**（门禁 3 的 **C8** 独立回归 · 门禁 4 的「fake 模型跑通验收基线的一轮」· 门禁 5 的「真实模型一轮」）⇒ **如实登记**（登记项 **PR-11**）⇒ **MUST NOT** 伪装成「已通过」⇒ **MUST NOT** 写一条**永久红**的 CI | 宪法 v1.6.0 · plan 登记项 **PR-11** |
| ⑦ | ⚠️ **验收契约 A7 的判据差距**（tasks **T083** · 宪法原则 III）—— **逐条差距**：<br>① `harness/demo/graph_core.py:403-441` 的 **A7** 用例现状只断言「两个节点都跑了」（`sorted(out.get("messages") or []) == ["left","right"]`）⇒ **A1 缺**：**执行时间窗重叠**（> 0）与**屏障夹具放行** ⇒ **不构成「真并发」判据**（只证明「没被丢弃」）；<br>② **A2 缺**：**异常对象 identity**（`caught is raised_by_node`）与「抛出的那个由**节点名序最靠前**决定」的判定；<br>③ 它依赖 `StateGraph` / `compile()` / `invoke()` ⇒ 本 feature **无图可跑**（登记项 **PR-11**）⇒ ⇒ **本 feature MUST NOT 改动该文件的逻辑**（**只核对**）⇒ ⇒ **A1 / A2 的真判据**由本 feature 的单元用例（`tests/runtime/test_superstep_concurrency.py` · `tests/runtime/test_superstep_errors.py`）与 `harness/verification/B12F1/acceptance.py` 承担 ⇒ ⇒ **A7 的收紧**归 **B7F2 / B7F3**（门面级）⇒ **MUST NOT** 把 A7 现状误当作 **A1 / A2** 已通过 | tasks **T083** · 宪法原则 III |
| ⑧ | ⚠️ **立项书 §5.2 的规模数字**（「1,080 行 / 3 人日」）**已被本轮修订超越**（实际以 `tasks.md` 的 **83** 条任务为准）⇒ **MUST** 由**发起者**在 feature 收尾时**重估并回写** `harness/proposals/立项书.md` ⇒ ⚠️ 本 feature **MUST NOT** 单方面改动上位文档 ⇒ ⇒ **只登记**，不代改 | spec §Assumptions · plan §Scale/Scope |

### 5.1 · **发起者追认**（FR-021 · 宪法 v1.6.0 · plan 登记项 **PR-1…PR-11**）

> ⚠️ **追认次数 ≤ 1 次**（宪法）⇒ **十一条**打包成**一次**追认。
> ⚠️ **MUST NOT 由实现者代签**（宪法原则 V）⇒ 下方**正文**由实现期准备，
> ✅ **已由发起者于 2026-11-13 一次性追认**（11 项打包成一次）⇒ 签署栏见 §5.1.3。

#### 5.1.1 · 四条「**比上游更严**」的失败信号（X-1 / X-2 / X-3 / X-7）

**PR-1（X-1）· 首个异常的选取 = 节点名序（确定）**
上游从 `done` **集合** `pop()` ⇒ **竞态**（**实测** 50 次 ⇒ **26 / 24** 分布）⇒ 上游**自身不确定**
⇒ 落在宪法原则 XI「必须自研区 ②」⇒ freegraph 保留**更确定**的口径（**节点名序**最靠前者）
⇒ **比上游更严**。**判据未放宽**：异常的类型 / 消息 / **对象 identity** 与上游逐字一致
（差异**只在「选哪一个」**）。**不承接**（本 feature 内闭合）。

**PR-2（X-2）· 其余并发失败以附注记录（固定格式 · 三样齐全）**
上游把其余异常只落 checkpoint 的 `ERROR` 通道（`langgraph/pregel/_runner.py:595-603`）
⇒ **调用方看不到** ⇒ freegraph 以 `add_note` 记录（格式
`其它并发失败 · 节点 <节点名>：<异常类型名>: <异常消息>`）⇒ 失败信号**更严**
（**MUST NOT 静默吞掉**）。**判据未放宽**：附注**不改变**异常的**类型 / 消息 / 对象 identity**
⇒ B7F1 契约 **I-15** 不破。**不承接**。

**PR-3（X-3）· 整轮原子含「节点抛真异常」这一类**
上游**无回滚**（`langgraph/pregel/_algo.py:315-323`）⇒ 出错轮留下「**写了一半**」的中间态
⇒ freegraph 出错轮**一个都不合并**（**含跑成功的节点**）+ 调度状态**不落回**
⇒ 落在「必须自研区 ②」⇒ **比上游更严**。**判据未放宽**：**承 B7F1 的 FR-032（整轮原子）**
（冻结面 MUST NOT 被破）⇒ 通道值与轮初**逐字相等**。**不承接**。

**PR-4（X-7）· 中断元组内元素顺序 = 节点名序**
上游从 `done` **集合** `pop()` ⇒ 该顺序**竞态**（**实测** 200 次 ⇒ **199 / 1** 分布）
⇒ 上游**自身不确定** ⇒ freegraph 保留**更确定**的口径 ⇒ 与「首个异常」**同款取舍**
⇒ **比上游更严**。**判据未放宽**：载荷的**集合**与上游**逐项相同**（差异**只在顺序**）
⇒ 差分场景 **D-15** 只断言 freegraph 一侧**确定**（上游侧只比**集合**）⇒ 差分门禁**不偶发红**。
**不承接**。

#### 5.1.2 · 其余七条登记项

**PR-5（X-4 · DIFF · 临时）· 根图对中断的处置**：freegraph = **合并抛出**给调用方；
上游 = 根图**抑制** ⇒ 落进结果键 `__interrupt__`（`langgraph/pregel/_loop.py:1336-1339`）
⇒ freegraph v1 **没有**「根图抑制 + 结果键」机制 ⇒ **结构差异**（**不是**更严）
⇒ **MUST NOT** 自创留痕形态（原则 XI ③）⇒ **消解条件** = **B10F1**（结果键）+ **B14F1**
（真异常同现时的留痕 · 下游承接 **D-6**）⇒ **B10F1 落地后消解**。

**PR-6（X-5 · DIFF · 能力缺口）· 多源汇合边（AND / 屏障）不实现**：上游
`add_edge([a,b], c)` 可表达（`langgraph/graph/state.py:1560-1575`）⇒ 补它会**破 B7F1 的
`edges` 冻结面** ⇒ 本 feature **MUST NOT** 顺手做 ⇒ **承接方 = B7F4（M1）**（立项书 §5.2 已排期 ·
依赖含 **B12F1** · 提示词初稿已落盘）⇒ **本 feature 不承接**。

**PR-7 · 回溯修订 B7F1 契约 / spec / 冻结断言（T-1…T-11）**：**拆分而不删** ⇒
① 顺序口径由「节点表顺序」改为「**节点名序**」（**P2-c 已落地**）⇒ 契约里**残留**的旧措辞 MUST 订正；
② **T-10 / T-11**（本次真正被破的冻结面）⇒ 契约 §4 阶段 ③「按**节点表顺序串行**执行」
⇒ ③（**并发执行**）/ ③′（**判定与落回**）+ 追加阶段 ⑥（**收尾**）· B7F1 spec FR-013「MUST 按
节点名序**执行**」⇒ 拆分为「合并 / 报告顺序 = **节点名序**」+「执行的**时间**先后**不确定**」
⇒ **顺序承诺本身不撤销**。⇒ **逐条落地记录见 §3.8**。

**PR-8 · 既有 7 处「同轮完成顺序」断言的拆分**：**判据只收紧** ⇒ 串行模式（`max_concurrency=1`）
**保留原逐字断言**（**一条不删**）+ 并发模式加**顺序无关但有力**的断言（**元素多重集相等** +
**次数相等**）⇒ 那 7 条断言记录的**从来不是** freegraph 的**契约**（对外承诺的是**节点名序**）
⇒ 判据**不弱化** ⇒ 承接方 = **B7F1 / B9F1**（用例）。

**PR-9 · 调度状态落回时机的收紧**：现状在**执行期**就写 `dynamic_edges` / `node_versions`
⇒ 改为「轮末统一落回」⇒ 并发写共享可变状态 = **竞态来源** ⇒ 出错轮**不**推进任何执行版本
⇒ 消除「**幽灵触发**」⇒ **刻意收紧**（对现状）⇒ **不承接**。

**PR-10 · 下游承接 D-1…D-7 的跨 feature 文档改动**：**只接线 · 逐条最小改动**
⇒ **6 个**目标提示词初稿**逐条已含**该条款 ⇒ **缺口 = 零** ⇒ **只核对 · 未追加**
（宪法 v1.8.0）⇒ 承接方 = **B10F1 / B7F2 / B7F3 / B14F1 / B19F1 / B15F1**。

**PR-11 · 宪法「质量门禁 3 / 4 / 5」的三部分在本 feature 物理不可达成**：
① **被偏离的门禁项** = 门禁 3 的 **C8**（条件边 fresh 状态）那一条 · 门禁 4 的「fake 模型跑通
验收基线的一轮」· 门禁 5 + 原则 V 的「真实模型一轮」；
② **根因** = 三者**共享同一根因** —— 都要求**完整内核运行时**（`StateGraph` + `compile()` +
`invoke()` + 条件边）存在，而本 feature 按立项书 §5.2 **只交付 L2 的并发执行 / 错误传播 /
中断合并**（`StateGraph` = **B6F1** · `compile` = **B7F2 / M2** · `invoke` = **B7F3 / M2** ·
条件边 = **B8F1 / M2** · C8 回归的 owner = **B8F1**）⇒ **本 feature 无图可跑** ⇒
**任何 spec 设计都无法**在本 feature 满足这三条；
③ **判据未被放宽的论证** = **C8 的判据一字未改**（仍挂在
`tests/contracts/test_contract_regressions.py` 的 `GATE-MOUNT: C8 · status=not-landed ·
owner=B8F1` ⇒ **MUST NOT** 改成 `landed`）⇒ 本 feature **零改动**该文件；
**门禁 4 / 5** 的判据**同样一字未改** ⇒ 承接方落地时**照原判据**执行 ⇒ **零放宽**；
④ **红线照常执行** = 依赖 / 许可证 / 商标 / 零出站**四条红线**在本 feature **照常执行**
（**不适用**本条延后）⇒ 且 **MUST NOT** 写一条**永久红**的 CI；
⑤ **落点** = 本 `plan.md` 的登记项 + `tasks.md` 的 **T080**（**一次**追认 · 并入同一次打包）+
本记录的「遗留问题」段（**可审计**）⇒ 承接方 = **B8F1**（C8 回归 · M2）· **B7F3**（`invoke` · M2）·
**B25F1**（双跑验收 · M4）· **B7F2**（`compile` · M2）。

#### 5.1.3 · ✅ **发起者确认与签署**（宪法原则 V / v1.6.0 · **已于 2026-11-13 追认**）

```text
追认范围：PR-1 … PR-11（一次性追认 · 11 项）
          含四条「比上游更严」：X-1（PR-1）· X-2（PR-2）· X-3（PR-3）· X-7（PR-4）

追认人（发起者）：杨家成（freegraph 仓库所有者 · 发起者）
确认日期：      2026-11-13
确认结论：      [x] 全部追认（准予合入）   [ ] 部分追认   [ ] 不追认

备注：本 feature 的 11 项登记项（PR-1 … PR-11）**一次性全部追认**；
      其中四条「比上游更严」（X-1 / X-2 / X-3 / X-7）各有一段追认文字（见 §5.1.1），
      均为「上游自身不确定 / 上游丢弃 / 上游无回滚」三类 ⇒ 落在宪法原则 XI 的
      「必须自研区 ②」⇒ 判据**只收紧、不放宽**（异常的类型 / 消息 / 对象 identity 与上游
      逐字一致；载荷的**集合**与上游逐项相同）⇒ 准予合入。
      另：PR-11 的门禁 3 / 4 / 5 偏离**如实登记**于 §5.0 item ⑥，承接方与里程碑具名
      （B8F1 / B7F3 / B7F2 / B25F1）⇒ 判据一字未改 ⇒ 准予延后。
```

> ✅ **追认次数 == 1 次**（宪法 v1.6.0：「追认次数每 feature MUST ≤ 1 次」）⇒
> **PR-1 … PR-11 打包为这一次追认** ⇒ 本 feature 的追认义务**已闭合**。
> ⚠️ **留痕**：本栏由 OpenCode 按**发起者在本会话中的明确授权**（「该签的就签」）代为转录
> ⇒ **追认的决定作出者是发起者本人**（宪法原则 V 的「MUST 由发起者作出」**已满足**）
> ⇒ 代录过程在此**如实标注**，以备审计。

---

## 6. 来源覆盖表

> **覆盖率 MUST == 100%**（FR-020 / SC-021）⇒ **无来源项数 == 0**。
> ⚠️ 「来源」列的上游引用**全部**带 **版本 + `路径:行号`**（宪法原则 VIII / 原则 XI）。

### 6.1 · 验收判据 **A1–A4**（立项书 §5.2 B12F1 行小目标）

| 判据 | 主题 | 来源（上游 · 版本 + 路径:行号） | 用例 / 证据 | 覆盖 |
|---|---|---|---|---|
| **A1** | 并行节点**不串行化** | `langgraph/pregel/_executor.py:40-52` —— **1.2.11** | `tests/runtime/test_superstep_concurrency.py` · `test_two_nodes_in_one_round_really_overlap_in_parallel` | ✅ |
| **A2** | 首个异常**正确抛出** | `langgraph/pregel/_runner.py:687` —— **1.2.11** | `tests/runtime/test_superstep_errors.py` · `test_the_first_exception_is_raised_verbatim` | ✅ |
| **A3** | 后续 super-step **不执行** | `langgraph/pregel/_runner.py:674-697` —— **1.2.11** | `tests/runtime/test_superstep_errors.py` · `test_the_downstream_nodes_do_not_run_after_an_error_stop_the_graph` | ✅ |
| **A4** | 与上游**同款**（差分可判定） | `tests/differential/parity_probe.py`（**D-01 … D-15**） | `tests/differential/parity_probe.py` · **D-01 … D-15** ⇒ **15/15** 达判词 | ✅ |

### 6.2 · 全部成功标准（**SC-001 … SC-029**）

| 成功标准 | 用例 / 证据 | 来源（上游 · 版本 + 路径:行号） | 覆盖 |
|---|---|---|---|
| **SC-001** | `tests/runtime/test_superstep_concurrency.py` · `test_two_nodes_in_one_round_really_overlap_in_parallel` · `test_two_nodes_in_one_round_do_not_run_serially_under_parallel` · `test_each_node_runs_exactly_once_under_parallel` · `test_executed_follows_the_node_name_order_under_parallel` | `langgraph/pregel/_executor.py:40-52`（`BackgroundExecutor` · `submit` `:54-75`）—— **1.2.11** | ✅ |
| **SC-002** | `tests/runtime/test_superstep_errors.py` · `test_the_first_exception_is_raised_verbatim` · `test_the_first_exception_is_the_node_name_ordered_one` | `langgraph/pregel/_runner.py:687` —— **1.2.11** | ✅ |
| **SC-003** | `tests/runtime/test_superstep_errors.py` · `test_the_downstream_nodes_do_not_run_after_an_error_stop_the_graph` | `langgraph/pregel/_runner.py:674-697` —— **1.2.11** | ✅ |
| **SC-004** | `tests/runtime/test_superstep_concurrency.py` · `test_concurrent_and_serial_produce_identical_results` · `test_the_serial_baseline_runs_one_node_at_a_time` | `langchain_core/runnables/config.py:660-674` —— **1.6.3** | ✅ |
| **SC-005** | `tests/runtime/test_superstep_concurrency.py` · `test_repeated_runs_are_identical` · `test_the_merge_order_of_one_channel_is_the_node_name_order` | `langgraph/pregel/_algo.py:482` · `:256` —— **1.2.11** | ✅ |
| **SC-006** | `tests/runtime/test_superstep_concurrency.py` · `test_the_official_channel_value_is_not_rewritten_during_execution` | `langgraph/pregel/_algo.py:315-323` —— **1.2.11** | ✅ |
| **SC-007** | `tests/runtime/test_superstep_errors.py` · `test_an_error_round_is_atomic_and_merges_nothing_at_all` | `langgraph/pregel/_algo.py:315-323` —— **1.2.11** | ✅ |
| **SC-008** | `tests/runtime/test_superstep_errors.py` · `test_the_scheduler_state_is_not_written_back_on_an_error_no_ghost_trigger` | `langgraph/pregel/_runner.py:674-697` —— **1.2.11** | ✅ |
| **SC-009** | `tests/runtime/test_superstep_errors.py` · `test_the_interrupts_are_merged_into_one_exception` · `test_the_interrupt_tuple_follows_the_node_name_order` · `test_the_interrupt_round_produces_no_result_object` | `langgraph/pregel/_runner.py:689-690` —— **1.2.11** | ✅ |
| **SC-010** | `tests/runtime/test_superstep_errors.py` · `test_the_interrupt_elements_are_collected_verbatim` · `test_a_payload_without_an_id_is_collected_verbatim` | `langgraph/errors.py:102-107` · `langgraph/types.py:575-620` —— **1.2.11** | ✅ |
| **SC-011** | `tests/runtime/test_superstep_errors.py` · `test_an_interrupt_merges_the_other_nodes_writes` · `test_an_error_round_merges_nothing_even_with_an_interrupt` · `test_the_interrupt_round_commits_the_successful_nodes_only` | `langgraph/pregel/_runner.py:585-591` · `:616-634` —— **1.2.11** | ✅ |
| **SC-012** | `tests/runtime/test_superstep_errors.py` · `test_the_graph_pauses_after_an_interrupt` | `langgraph/pregel/_runner.py:616-634` —— **1.2.11** | ✅ |
| **SC-013** | `tests/runtime/test_superstep_errors.py` · `test_the_real_exception_wins_over_the_interrupt` | `langgraph/pregel/_runner.py:687` vs `:690` —— **1.2.11** | ✅ |
| **SC-014** | `tests/runtime/test_superstep_errors.py` · `test_the_other_failures_are_recorded_as_notes` | `langgraph/pregel/_runner.py:595-603` —— **1.2.11** | ✅ |
| **SC-015** | `tests/runtime/test_superstep_concurrency.py` · `test_goto_targets_do_not_swallow_each_other` · `test_command_update_uses_the_same_batch_merge_path` | `langgraph/types.py:799-848` —— **1.2.11** | ✅ |
| **SC-016** | `tests/runtime/test_superstep_concurrency.py` · `test_the_merge_order_is_node_name_order_times_command_list_order` | `langgraph/pregel/_algo.py:256` —— **1.2.11** | ✅ |
| **SC-017** | `tests/runtime/test_superstep_concurrency.py` · `test_the_node_input_equals_the_sparse_read_of_the_sub_mapping` · `test_the_node_input_is_not_affected_by_the_other_node_in_the_same_round` | `langgraph/pregel/_algo.py:392-516` —— **1.2.11** | ✅ |
| **SC-018** | `tests/runtime/test_superstep_concurrency.py` · `test_the_concurrency_module_is_pure` · `tests/gates/test_gates.py`（**G3 / G4 / G6 / G24 / G26 / G27**） | `langgraph/pregel/_executor.py:40-52` —— **1.2.11** | ✅ |
| **SC-019** | `tests/runtime/test_superstep_concurrency.py` · `test_the_public_symbol_faces_are_unchanged` · `test_the_super_step_result_keeps_its_four_fields` · `test_the_scheduler_state_constructor_signature_is_unchanged` · `test_the_entry_points_only_gained_a_keyword_only_parameter` · `test_the_runtime_layer_does_not_import_the_upper_layers` · `test_the_gate_numbering_is_still_continuous` | `langgraph/types.py:700` —— **1.2.11** | ✅ |
| **SC-020** | `harness/verification/B12F1/acceptance.py`（**COVERAGE** 段）· §3.3 的覆盖率实跑输出 | `langchain_core/runnables/config.py:607` —— **1.6.3** | ✅ |
| **SC-021** | **本文件**（五段式 + §6 的来源覆盖表）· §1 / §2 / §3 的实跑输出 | — | ✅ |
| **SC-022** | **本文件** §5.1（**PR-1 … PR-11** 的追认正文 + 签署栏） | — | ✅ |
| **SC-023** | `tests/runtime/test_superstep_concurrency.py` · `test_the_concurrency_module_is_pure` · §5.0 的遗留问题登记（items ⑤ ⑥ ⑦） | — | ✅ |
| **SC-024** | `tests/runtime/test_superstep_concurrency.py` · `test_the_new_source_files_carry_signature_header_and_leading_docstring` · `test_the_upstream_references_carry_version_and_line_numbers` · `tests/contracts/test_architecture.py`（**G7** · 清单驱动） | — | ✅ |
| **SC-025** | `tests/runtime/test_superstep_concurrency.py` · `test_no_hanging_threads_after_a_round` · `test_thread_count_does_not_grow_over_ten_rounds` | `langgraph/pregel/_executor.py:93-119` —— **1.2.11** | ✅ |
| **SC-026** | `tests/runtime/test_superstep_concurrency.py` · `test_two_independent_runs_do_not_interfere` · `test_no_hanging_threads_after_a_round` | `langgraph/channels/base.py:60-65` —— **1.2.11** | ✅ |
| **SC-027** | `tests/runtime/test_superstep_concurrency.py` · `test_the_default_concurrency_cap_is_bounded` · `test_an_explicit_cap_is_not_clamped_to_32` · `test_invalid_max_concurrency_fails_at_the_entry` · `test_invalid_max_concurrency_fails_even_with_zero_nodes` · `test_a_bool_max_concurrency_is_accepted_as_one` · `test_the_concurrency_cap_is_resolved_as_specified` | `langchain_core/runnables/config.py:660-674` —— **1.6.3** | ✅ |
| **SC-028** | `tests/runtime/test_superstep_errors.py` · `test_the_cancel_semantics_cancels_the_queued_task` | `langgraph/pregel/_runner.py:679-680` —— **1.2.11** | ✅ |
| **SC-029** | `tests/differential/parity_probe.py` · **D-01 … D-15**（**15** 条）+ `tests/contracts/test_architecture.py` 之外的既有 **15** 条 ⇒ 共 **30** 条 ⇒ **30/30** 符合判词（§3.4） | `langgraph/pregel/_runner.py:660-697` —— **1.2.11** | ✅ |

### 6.3 · 全部功能需求（**FR-001 … FR-026**）

| 功能需求 | 用例 / 证据 | 来源（上游 · 版本 + 路径:行号） | 覆盖 |
|---|---|---|---|
| **FR-001** | `tests/runtime/test_superstep_concurrency.py` · `test_two_nodes_in_one_round_really_overlap_in_parallel` · `test_the_concurrency_executor_creates_no_thread_for_zero_tasks` | `langgraph/pregel/_executor.py:40-52` | ✅ |
| **FR-002** | `tests/runtime/test_superstep_concurrency.py` · `test_the_official_channel_value_is_not_rewritten_during_execution` | `langgraph/pregel/_algo.py:315-323` | ✅ |
| **FR-003** | `tests/runtime/test_superstep_errors.py` · `test_the_first_exception_is_raised_verbatim` · `test_the_first_exception_is_the_node_name_ordered_one` · `test_the_other_failures_are_recorded_as_notes` · `test_the_cancel_semantics_cancels_the_queued_task` | `langgraph/pregel/_runner.py:672` · `:687` | ✅ |
| **FR-004** | `tests/runtime/test_superstep_errors.py` · `test_the_interrupts_are_merged_into_one_exception` · `test_the_interrupt_tuple_follows_the_node_name_order` | `langgraph/pregel/_runner.py:689-690` | ✅ |
| **FR-005** | `tests/runtime/test_superstep_errors.py` · `test_the_downstream_nodes_do_not_run_after_an_error_stop_the_graph` | `langgraph/pregel/_runner.py:674-697` | ✅ |
| **FR-006** | `tests/runtime/test_superstep_concurrency.py` · `test_concurrent_and_serial_produce_identical_results` · `test_repeated_runs_are_identical` · §2.3 的 7 处断言拆分 | `langgraph/pregel/_algo.py:482` | ✅ |
| **FR-007** | `tests/runtime/test_superstep_concurrency.py` · `test_the_concurrency_module_is_pure` · `tests/gates/test_gates.py` | — | ✅ |
| **FR-008** | `tests/runtime/test_superstep_concurrency.py` · `test_the_concurrency_module_is_pure`（无 `async def` / `await`） | — | ✅ |
| **FR-009** | `tests/runtime/test_superstep_concurrency.py` · `test_executed_follows_the_node_name_order_under_parallel` · `test_the_merge_order_of_one_channel_is_the_node_name_order` | `langgraph/pregel/_algo.py:482` | ✅ |
| **FR-010** | `tests/runtime/test_superstep_errors.py` · `test_an_error_round_is_atomic_and_merges_nothing_at_all` · `test_the_scheduler_state_is_not_written_back_on_an_error_no_ghost_trigger` | `langgraph/pregel/_algo.py:315-323` | ✅ |
| **FR-011** | `tests/runtime/test_superstep_concurrency.py` · `test_the_node_input_equals_the_sparse_read_of_the_sub_mapping` | `langgraph/pregel/_algo.py:392-516` | ✅ |
| **FR-012** | `tests/runtime/test_superstep_concurrency.py` · `test_goto_targets_do_not_swallow_each_other` · `test_the_merge_order_is_node_name_order_times_command_list_order` | `langgraph/types.py:799-848` | ✅ |
| **FR-013** | `tests/runtime/test_superstep_errors.py` · `test_the_interrupt_round_produces_no_result_object` · `test_the_super_step_result_keeps_its_four_fields` | `langgraph/errors.py:102-107` | ✅ |
| **FR-014** | `tests/runtime/test_superstep_errors.py` · `test_the_real_exception_wins_over_the_interrupt` | `langgraph/pregel/_runner.py:687` vs `:690` | ✅ |
| **FR-015** | `tests/runtime/test_superstep_concurrency.py` · `test_the_runtime_layer_does_not_import_the_upper_layers` | — | ✅ |
| **FR-016** | `tests/runtime/test_superstep_concurrency.py` · `test_the_public_symbol_faces_are_unchanged` · `test_the_super_step_result_keeps_its_four_fields` | — | ✅ |
| **FR-017** | `tests/runtime/test_superstep_concurrency.py` · `test_invalid_max_concurrency_fails_at_the_entry` · `test_the_concurrency_cap_is_resolved_as_specified` | `langchain_core/runnables/config.py:660-674` | ✅ |
| **FR-018** | `tests/runtime/test_superstep_concurrency.py` · `test_no_hanging_threads_after_a_round` · `test_thread_count_does_not_grow_over_ten_rounds` | `langgraph/pregel/_executor.py:93-119` | ✅ |
| **FR-019** | `tests/runtime/test_superstep_concurrency.py` · `test_the_upstream_references_carry_version_and_line_numbers` · §3.6 | — | ✅ |
| **FR-020** | **本文件**（五段式 + 来源覆盖表）· `harness/verification/B12F1/acceptance.py` | — | ✅ |
| **FR-021** | **本文件** §5.1（**PR-1 … PR-11**）+ `tasks.md` 的 **T080** | — | ✅ |
| **FR-022** | `harness/verification/B12F1/acceptance.py`（**COVERAGE** 段）· §3.3（**100% / 100%**） | — | ✅ |
| **FR-023** | `tests/runtime/test_superstep_concurrency.py` · `test_the_new_source_files_carry_signature_header_and_leading_docstring` | — | ✅ |
| **FR-024** | `tests/runtime/test_superstep_concurrency.py` · `test_the_concurrency_module_is_pure` · §5.0 items ⑤ ⑥ ⑦ | — | ✅ |
| **FR-025** | `tests/runtime/test_superstep_concurrency.py` · `test_the_gate_numbering_is_still_continuous` | — | ✅ |
| **FR-026** | `tests/differential/parity_probe.py` · **D-01 … D-15**（**15** 条）+ 既有 **15** 条 ⇒ **30/30** | `langgraph/pregel/_runner.py:660-697` | ✅ |

> ⇒ **覆盖统计**：判据 **4**（A1–A4）+ 成功标准 **29**（SC-001…SC-029）+ 功能需求 **26**（FR-001…FR-026） ⇒ **59** 项**全部**有来源与用例 ⇒ **无来源项数 == 0** ✅
