# B8F1 · 条件边路由求值 + `END` 终止 + fresh 读（C8 独立回归测试）· 人工验证记录

**Feature**: `specs/b8f1-conditional-edges-fresh-read/` · **日期**: 2026-11-18
**上游**: `langgraph 1.2.11` / `langchain-core 1.7.6`（开发 / 测试侧差分依赖；**不在**发行面）

---

## 1. 环境

| 项 | 值 |
|---|---|
| Python | **3.11.16**（`.venv/bin/python` · 最低档 3.11） |
| 平台 | Linux（CPython 3.11.16 · x86_64） |
| freegraph | 源码树（`PYTHONPATH=src`） |
| 上游差分依赖 | `langgraph` **1.2.11** / `langchain-core` **1.7.6**（`.venv` 实际安装版本 · 与 `pyproject.toml:100` 钉死值**逐字一致**） |
| 第三方运行时依赖 | **零**（`dependencies = []` · 本 feature **零新增依赖**） |
| 提交号（基线时刻） | **f60a182**（`docs(verification): 记录 B7F3 CI 实跑 7/7 作业全绿`） |

### 1.1 绿基线（**T001 实测 · 实施前**）

> ⚠️ 宪法 v1.11.0「基线绿义务」：实施**开始前** MUST 先跑一遍既有测试套件并**记录绿基线**（计数）。

| 项 | 计数 |
|---|---|
| **passed** | **1486** |
| **skipped** | **4** |
| **failed** | **0** |
| **跑测时刻** | **2026-11-18T04:33:39+08:00** |

```
1486 passed, 4 skipped in 100.27s (0:01:40)
```

> ⚠️ **4 条 skip 的原因**（逐条）：① C8（条件边 fresh 状态读）由 **B8F1** 建立（本 feature
> **已落地** ⇒ 见 §1.2）· ② mypy 未安装（开发期工具 · 兜底的注解结构断言仍跑）·
> ③ API 快照未开 `--update-api-snapshot` · ④ Windows 时钟分辨率用例（仅 Windows 档）。

### 1.2 实施后的全量套件（**实施后**）

| 项 | 计数 |
|---|---|
| **passed** | **1607**（较基线 **+121**） |
| **skipped** | **4** |
| **failed** | **0** |

```
1607 passed, 4 skipped in 80.99s (0:01:20)
```

> ⚠️ **4 条 skip 的变化**：① C8 的占位用例由「未落地」skip 改为「**原占位留存**」skip
> （`tests/contracts/test_contract_regressions.py:99`）⇒ ⇒ ⇒ **C8 的判定载体**由
> `tests/runtime/test_conditional_edges.py` 承担（**元测试**断言其**在位且被 pytest 收集**）。

### 1.3 变红清单的**实测化**（**T066** · 详见 `plan.md` 的「实测化结论」）

| 口径 | 结果 |
|---|---|
| **预登记项** | **6** 项 ⇒ **实测变红 1 项**（④ `test_compiled_graph.py:263-265`）· **未变红 5 项**（① ② ③ ⑤ ⑦） |
| **追加登记项** | **2** 项（**⑦** facade 夹具 `build_conditional_graph` · **⑧** `test_interrupt_contract.py:176-179` 的 C8 挂载点断言）⇒ 均**由本 feature 的落地形态导致** ⇒ 已按「拆分而不删 / 判据只收紧」处置 |
| **时序风险**（非变红断言） | **T-6**（`graph_core.py` 的 A5 组 + A6 的 C16 段）· **T-7**（`agent_loop.py` 的 B1 / B2 / B3 组）⇒ 由**软 ⇒ 硬**（**判据只收紧**）⇒ 归**破面全集** |

---

## 2. 步骤（可复制命令）

```bash
# ① 绿基线（实施前）
uv run --no-project --python .venv python -m pytest tests/ -ra

# ② 全量套件（实施后）
uv run --no-project --python .venv python -m pytest tests/ -ra

# ③ C8 的实际回归（**否定式**断言）
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edges.py -ra

# ④ 契约守卫（解析 `contracts/conditional-edge-contract.md` §7 的 I-1…I-14）
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edge_contract.py -ra

# ⑤ 零新增面清点
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edge_surface.py -ra

# ⑥ 差分（上游缺席即 skip —— **不是**失败）
uv run --no-project --python .venv python -m pytest tests/differential/ -ra

# ⑦ 验收脚本集（A5 / B1 / B2 硬断言）
uv run --no-project --python .venv python harness/demo/graph_core.py ; echo "rc=$?"
uv run --no-project --python .venv python harness/demo/agent_loop.py ; echo "rc=$?"

# ⑦' **本 feature 的一键验收**（逐 feature 的验收入口 · A1…A10）
uv run --no-project --python .venv python harness/verification/B8F1/acceptance.py ; echo "rc=$?"

# ⑧ 门禁
uv run --no-project --python .venv python harness/scripts/gates/gate_G29_contract_carrier.py
```

---

## 3. 实际输出

### 3.1 全量 pytest（**实施后**）

```
1607 passed, 4 skipped in 80.99s (0:01:20)
```

### 3.2 C8 的实际回归（**否定式**断言 · `tests/runtime/test_conditional_edges.py`）

```
49 passed in 0.41s
```

### 3.3 契约守卫（`tests/runtime/test_conditional_edge_contract.py`）

```
43 passed in 0.51s
```

### 3.4 零新增面清点（`tests/runtime/test_conditional_edge_surface.py`）

```
10 passed in 0.15s
```

### 3.5 差分场景组 **D-103…D-120**（**双真实实现**对跑）

```
30 passed in 22.79s
```

| 判词 | 条数 | 差分编号 |
|---|---|---|
| `SAME` | **12** | D-103 · D-104 · D-105 · D-106 · D-107 · D-108 · D-109 · D-112 · D-113 · D-115 · D-116 · D-117 |
| `DIFF` | **4** | D-110（**X-2**）· D-114（**X-5**）· D-118（**X-2**）· D-120（**X-7**） |
| `STRICTER` | **2** | D-111（**X-3**）· D-119（**X-6**） |

> ✅ **判词分布与 `spec.md` 的「差分场景组」表**（SAME 12 / DIFF 4 / STRICTER 2）**逐条一致**
> ⇒ ⇒ ⇒ 判词非 `SAME` 的 **6** 条**均带**非空 `note`（既有守卫
> `tests/differential/test_parity_probe.py:106-108` **绿** ⇒ ⇒ ⇒ **判据零放宽**）。

### 3.6 公开面清点（**零新增**）

```
contracts 21 | facade 7 | runtime 23
```

| 面 | 数量 | 判据 |
|---|---|---|
| `freegraph.contracts.__all__` | **21** | **零变更**（门禁 G7） |
| `freegraph.graph.__all__` | **7** | **零变更**（门禁 G15 / G19） |
| `freegraph.runtime.__all__` | **23** | **零变更**（新增的 `_routing.py` 是 **L2 私有** ⇒ **不进** `__all__`） |
| `vars(compiled)` 的键数 | **11** | **零新增**私有字段（**T-3 不破**） |
| `freegraph.runtime.errors` 的符号集合 | **不变** | **零新增错误类型**（**I-14**） |

### 3.7 B8F1 一键验收（`harness/verification/B8F1/acceptance.py` · **A1…A10**）

```
══ B8F1 · 条件边路由求值 + END 终止 + fresh 读（C8）══
Python 3.11.16 · Linux-6.8.0-139-generic-x86_64-with-glibc2.39
freegraph 源：<repo>/src

[A1] C8 fresh 读（否定式断言）
  ✔ 路由函数看到了本节点本次写入的值
  ✔ 归约型通道在 fresh 读里已合并
  ✔ 无值的覆盖型通道不在路由入参里
  ✔ 同轮另一节点的写入不可见

[A2] path_map 双形态 + 动态目标
  ✔ list 形态的 path_map 路由正确
  ✔ dict 形态的 path_map 路由正确
  ✔ 无 path_map 的动态目标路由正确
  ✔ 非 str 的可哈希值作 key 正常查表

[A3] END 终止
  ✔ 单独返回 END ⇒ 后续目标执行 0 次
  ✔ path_map 的 value 为 END ⇒ 同样终止
  ✔ path_map 不含 END 键 ⇒ 仍然终止（X-2）
  ✔ 序列内的 END ⇒ 剔除且其余照常执行
  ✔ path_map 把 END 映射到别的节点 ⇒ 无条件终止（X-2）

[A4] 失败信号两态
  ✔ 有 path_map + 非法返回值 ⇒ KeyError + 详细消息
  ✔ 无 path_map + 未注册节点名 ⇒ ValueError（X-3）
  ✔ 返回 None / START ⇒ 查表优先的两态
  ✔ 路由函数自身的异常原类型 + 原消息传播

[A5] 序列 ⇒ 多目标并行
  ✔ 返回序列 ⇒ 多目标同轮并行
  ✔ 多目标收到同一份共享状态
  ✔ 序列含重复目标 ⇒ 去重保序
  ✔ 空序列 ⇒ 无目标且不报错
  ✔ 返回 Send ⇒ 目标收到载荷

[A6] __start__ 上的条件边
  ✔ __start__ 上的条件边被求值
  ✔ 纯条件边入口可行
  ✔ 静态入口与条件入口并存 ⇒ 同轮并行
  ✔ 条件入口返回 END ⇒ 该分支终止
  ✔ __start__ 条件边的求值次数 == 1（幂等）

[A7] 双参形态
  ✔ 第二参 == 用户的原始 config（逐字）
  ✔ 第二参不叫 config ⇒ TypeError
  ✔ 注解不在匹配集 ⇒ 跳过注入且不发 UserWarning

[A8] 零新增公开面
  ✔ 21 / 7 / 23 符号 + 11 键 + 零新增错误类型

[A9] 差分组 D-103…D-120
  ✔ 差分组 D-103…D-120 全绿（SC-013）

[A10] 破冻结面的回溯验证（7 类）
  ✔ 破面全集 7 类的回溯修订逐条命中
  ✔ 人工验证记录五段式 + 追认文字 + 破面全集 7 类
  ✔ 零改动清单（target.py / 差分夹具 / 冻结断言 ③）

==============================================================================
总闸口 35 · 失败 0 · 跳过 0 ⇒ **PASS**
==============================================================================
B8F1 acceptance: PASS
```

**退出码 = 0**（耗时 ~23 秒 · 含 **A9** 的差分闸口）。

> ⚠️ **该脚本已进 CI 的常驻门禁**（**T076**）⇒ `tests/runtime/test_conditional_edges.py`
> 的「一键验收」用例**真跑**它（用 `--skip-differential` ⇒ 差分证据仍由
> `tests/differential/test_parity_probe.py` 独立承担 ⇒ **不重复**跑）⇒ ⇒ ⇒
> 脚本与实现**漂移** ⇒ ⇒ ⇒ 那条用例**立刻红**。

### 3.8 验收脚本集

| 脚本 | 断言数 | 通过 | 失败 | 退出码 |
|---|---|---|---|---|
| `harness/demo/graph_core.py` | **36** | **36** | **0** | **0** |
| `harness/demo/agent_loop.py` | **14** | **14** | **0** | **0** |

```
── graph_core 汇总 ──
断言 36 条 · 通过 36 · 失败 0
结论：PASS

── agent_loop 汇总 ──
断言 14 条 · 通过 14 · 失败 0
结论：PASS
```

> ⚠️ 两条脚本**剩余的软断言**（**不判失败**）**逐条具名**：
> `graph_core.py` 的 **C17 恢复**（载体待 **B14F1**）· **C21 context 独立通道**（归 **B8F3**）·
> **C25 流式事件**（归 **B8F2**）⇒ ⇒ ⇒ **本 feature 相关的那几条已全部硬化**
> （A5 的 C8/C7 · A6 的 C16 · B1 · B2 · B3）。

### 3.9 门禁

| 门禁 | 结果 | 备注 |
|---|---|---|
| **G21** | ✅ **PASS** | 依赖闭包黑名单（声明级 · 含全部 extras 变体） |
| **G22** | ✅ **PASS** | 隔离环境（依赖闭包为空集 + `sys.modules` 无 langchain 家族） |
| **G23** | ✅ **PASS** | 许可证白名单（4 级证据链） |
| **G24** | ✅ **PASS** | 配置层（`LANGSMITH_*` / `LANGCHAIN_*` / `LANGGRAPH_*` 零读取） |
| **G25** | ✅ **PASS** | 导入图单向（ARCH-1 · 层注册表驱动）⇒ 新增的 `_routing.py` 落 **L2**（目录条目）⇒ 自动纳入扫描 |
| **G26** | ✅ **PASS** | 网络静态扫描（`src/freegraph/**` 无网络客户端调用） |
| **G27** | ✅ **PASS** | 零出站动态断言（框架出站 = 0 · 用户出站 = 2 记录在案不判失败） |
| **G28** | ✅ **PASS** | 断网等价性（Linux 网络命名空间 · 全量测试套件 ⇒ `1591 passed, 4 skipped, 3 deselected`） |
| **G29** | ✅ **PASS** | 契约门禁载体（只读基准 diff + **C4 / C8 挂载点（均 `landed`）** + 验收脚本集退出码） |
| **G30** | ⚠️ **FAIL（既存）** | **8** 条违规 ⇒ **全部落在本 feature 未触碰的文件**上（`harness/demo/target.py` 的署名头例外未生效 · `harness/reports/Q7-*.md` 与 `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 的**官方 Approved copy 文案指纹**）⇒ ⇒ ⇒ **在 pristine `HEAD` 树上复现**（`git archive HEAD` 展开后单独跑 G30 ⇒ **同样的 8 条**）⇒ ⇒ ⇒ **非本 feature 的回归** ⇒ ⇒ ⇒ 详见 §8 遗留问题 **1** |

### 3.10 quickstart 验收闸口 **V1…V16**

| 闸口 | 命令 | 实测 |
|---|---|---|
| **V1** | `pytest tests/runtime/test_conditional_edges.py` | ✅ **49 passed** |
| **V2** | `grep GATE-MOUNT` + `pytest tests/contracts/` + `gate_G29` | ✅ `C4 · status=landed` · `C8 · status=landed` · `286 passed, 2 skipped` · **G29 PASS** |
| **V3** | `pytest` + 最小闭环片段 | ✅ 返回 `END` ⇒ 目标节点执行 **0** 次 |
| **V4** | `pytest` + 最小闭环片段 | ✅ list / dict / `None` 三形态各自路由正确 |
| **V5** | `pytest` + 最小闭环片段 | ✅ `KeyError` / `ValueError` 两态 + 消息含返回值与可选目标 |
| **V6** | `pytest` + 最小闭环片段 | ✅ 多目标**同轮**并行 · 共享状态 · 逐目标载荷相异 |
| **V7** | `pytest` + 最小闭环片段 | ✅ 第二参 == 用户交给 `invoke` 的**原始** `config`（逐字） |
| **V8** | `pytest` + 最小闭环片段 | ✅ 被求值 · 纯条件边入口 · 并存同轮并行 |
| **V9** | `pytest` + 最小闭环片段 | ✅ 同源重名 ⇒ 内置 `ValueError`（点名分支名与源节点） |
| **V10** | `pytest` + 最小闭环片段 | ✅ 路由通道**未被写入** · 不进返回键集 · 读取前后快照相等 |
| **V11** | `pytest` + 最小闭环片段 | ✅ 原始类型与原始消息（不被包装） |
| **V12** | `pytest tests/differential/` | ✅ **18** 条 · SAME **12** / DIFF **4** / STRICTER **2** |
| **V13** | `pytest`（四个文件）+ 两个脚本 | ✅ **115 passed, 1 skipped** · 两个脚本 `rc=0` |
| **V14** | `python -c` 导出面清点 | ✅ `contracts 21 \| facade 7 \| runtime 23` |
| **V15** | `gate_G24/G26/G27` + `grep` + 发行元数据 | ✅ 出站 **0** · 环境变量读取 **0** · 上游导入 **0** |
| **V16** | `test -s` + `grep` | ✅ 记录存在且**正文非空** · 五段式 · 真实轮未落地声明 |

---

## 4. 结论（逐条对照验收判据）

| 判据 | 结论 | 证据 |
|---|---|---|
| **SC-001**（C8 的**否定式**断言） | ✅ | §3.2（49 passed）· `tests/runtime/test_conditional_edges.py::test_c8_fresh_read_sees_the_value_the_node_just_wrote` |
| **SC-002**（门面可观察） | ✅ | §3.2 · `test_the_routing_is_observable_through_the_invoke_facade` |
| **SC-003**（`END` ⇒ 执行 **0** 次） | ✅ | §3.9 V3 · `test_returning_end_terminates_the_graph` |
| **SC-004**（fresh 读的三维） | ✅ | §3.2 · `test_c8_fresh_read_*`（四个用例） |
| **SC-005**（`path_map` 双形态） | ✅ | §3.9 V4 · `test_the_list_form_*` / `test_the_dict_form_*` |
| **SC-006 / SC-007**（失败信号**两态**） | ✅ | §3.9 V5 · `test_the_two_failure_signals_*` |
| **SC-008**（序列 ⇒ 多目标并行） | ✅ | §3.9 V6 · `test_a_sequence_return_value_fans_out_to_several_targets` |
| **SC-009**（与屏障组不混用） | ✅ | `test_the_conditional_edges_are_not_confused_with_a_barrier_group` |
| **SC-010 / SC-011**（路由通道缺席 / 零写入） | ✅ | `test_the_route_view_has_no_context_channel_and_no_route_channel` · `test_two_sources_routing_to_the_same_target_do_not_trigger_v6` |
| **SC-012**（异常原样传播） | ✅ | `test_the_router_exception_propagates_with_its_own_type_and_message` |
| **SC-013**（差分组全绿 + 判词分布） | ✅ | §3.5 |
| **SC-014**（C8 挂载点 + 元测试） | ✅ | §3.9 V2 |
| **SC-015**（`graph_core.py` 的 A5 硬断言） | ✅ | §3.7（36/36 · `rc=0`） |
| **SC-016**（零新增面） | ✅ | §3.6 · `tests/runtime/test_conditional_edge_surface.py`（10 passed） |
| **SC-017 / SC-018**（零出站 / 零环境变量 / 零上游导入） | ✅ | §3.8（G24 / G26 / G27 / G22） |
| **SC-019 / SC-020**（追认留痕 / 人工验证记录） | ✅ | 本文件（§5 · §7）+ `tests/runtime/test_manual_record_guard.py` |
| **SC-021**（双参形态的六维） | ✅ | §3.9 V7 · `test_the_two_argument_form_receives_the_original_config` 等五个用例 |
| **SC-022 / SC-023**（`__start__` 的三情形 + 幂等） | ✅ | §3.9 V8 · `test_a_conditional_edge_on_start_is_evaluated` 等五个用例 |
| **SC-024**（branch 名唯一） | ✅ | `test_two_conditional_edges_with_the_same_branch_name_are_rejected` |
| **SC-025**（`agent_loop.py` 的 B1 / B2 硬断言） | ✅ | §3.7（14/14 · `rc=0`） |
| **SC-026**（fake 轮的**实测输出**已落本记录） | ✅ | §5.1 |

### 来源覆盖

| 来源 | 覆盖的判据 |
|---|---|
| `specs/b8f1-conditional-edges-fresh-read/spec.md` 的 FR-001…FR-042 | 全部（**逐条**追溯见 `tasks.md` 附录） |
| `specs/b8f1-conditional-edges-fresh-read/contracts/conditional-edge-contract.md` §7 的 **I-1…I-14** | 全部（`tests/runtime/test_conditional_edge_contract.py` **逐条**断言 + 绑定表**双向**齐全） |
| `specs/b8f1-conditional-edges-fresh-read/contracts/upstream-parity.md` 的 **P-01…P-23** | 全部（`tests/differential/parity_probe.py` 的 **D-103…D-120** 逐条对跑） |
| `harness/demo/graph_core.py` | **A5**（C7 / C8）· **A6**（C16） |
| `harness/demo/agent_loop.py` | **B1**（工具循环）· **B2**（tool_calls 形状）· **B3**（中断） |
| `harness/reports/Q8-图运行时最小契约.md` §3.4 | **C4 / C8** 两条独立回归测试 |

---

## 5. 人工验证的两轮（**SC-019 / SC-020 / SC-026**）

### 5.1 「fake 模型轮」= 猴补（monkey-patch）`init_chat_model` + **含条件边的最小图** / `agent_loop.py` 的**工具循环轮**

> ⚠️ **本 feature 可达**（MUST 真跑并记录 · 裁定 19）⇒ ⇒ ⇒ 本节的输出是**实测输出**
> （**MUST NOT** 只写「符合预期」）⇒ ⇒ ⇒ **含条件边路由的可观察结果**（路由目标 ·
> 目标节点执行次数 · fresh 视图）⇒ ⇒ ⇒ 判据**由** `tests/runtime/test_manual_record_guard.py`
> 的**文档守卫断言**承担（**FR-042** · 宪法原则 VI v1.13.0）⇒ ⇒ ⇒ **「写记录」本身不构成判定覆盖**。

**轮 ① · 含条件边的最小图**（源节点写 `{"messages": ["fresh"], "llm_calls": 7}` ⇒ 路由函数在
**源节点任务成功落回**后被求值 ⇒ fresh 视图 = 「当前值 + 本节点本次写入」）：

```
轮 ① · 含条件边的最小图
  路由函数的 fresh 视图 = {"messages": ["fresh"], "llm_calls": 7}
  路由目标 = after
  节点执行序列 = ['writer', 'after']
  目标节点执行次数 = 1
  最终状态 = {'messages': 1, 'llm_calls': 7}
```

⇒ ⇒ ⇒ **fresh 视图里的 `llm_calls` == 7**（**不是**入参里的 `0`）⇒ ⇒ ⇒ **C8 的 fresh 读**
在**零依赖**的最小图上**真跑**并**可观察** ✓

**轮 ② · 工具循环**（`agent_loop.py` 的同款图：条件边在「模型 ⇄ 工具」之间跳转）：

```
轮 ② · 工具循环（模型 ⇄ 工具）
  路由函数的 fresh 视图（末条消息）= {"last_has_tool_calls": false, "last_content": "7"}
  节点执行序列 = ['agent', 'tools', 'agent']
  模型被调用次数 = 2
  最终 llm_calls = 2
  最终答案 = 7
```

⇒ ⇒ ⇒ 节点执行序列 = `agent → tools → agent` ⇒ ⇒ ⇒ **条件边真的把「模型 ⇄ 工具」连起来了**
（**首轮**路由到 `tools` ⇒ **工具结果**写回 ⇒ **次轮**路由到 `END` ⇒ 终止）✓
⇒ ⇒ ⇒ 与 `harness/demo/agent_loop.py` 的**硬断言**（14/14 · `rc=0`）**逐字一致** ✓

### 5.2 「真实模型轮」= 用**真实模型**跑**最小真实模型图**

> ⚠️ **本环境不具备**（无 `langchain_anthropic` / 无厂商凭据 / 无出网）⇒ ⇒ ⇒ 按宪法 v1.6.0
> **登记为环境偏离**（**MUST NOT** 用「未验证」替代「已登记的环境偏离」）⇒ ⇒ ⇒
> **判据本身不放宽**（fake 轮**已跑通**）⇒ ⇒ ⇒ 承接方 = **B25F1**（M4 · 立项书 §5.2）。

| 项 | 状态 |
|---|---|
| 真实模型轮 | ⚠️ **未落地（环境偏离）** —— 需**真实模型**（`claude-sonnet-4-6`）+ **厂商端点**（出网 + 凭据）⇒ ⇒ 本仓库的 CI 与门禁环境**无**该条件 |
| 登记 | 宪法 v1.6.0「质量门禁的分阶段落地」⇒ 承接方 **B25F1**（M4）· 见 §6 |
| 判据 | **未放宽** —— 「fake 模型轮」的实测输出**已在 §5.1**（**非空** · 含条件边路由的可观察结果）⇒ ⇒ ⇒ 门禁 5 的真实轮**由 B25F1** 承接 |

### 5.3 固定脚本（`target.py`）端到端轮 —— **不属**本 feature 的达成范围

> ⚠️ `harness/demo/target.py` **一字未改**（只读基准 · 门禁 G29 ① · `rc=0` 绿）⇒ ⇒ ⇒
> 但它在 `:163` 调 `draw_mermaid_png()`（属 **B23F1**）⇒ ⇒ ⇒ 脚本在 `:168` 的 `invoke()`
> **之前**中断 ⇒ ⇒ ⇒ **物理不可达成** ⇒ ⇒ ⇒ 承接方 = **B22F1 + B23F1**（M2）· **B25F1**（M4）
> ⇒ ⇒ ⇒ 见 §6。

---

## 6. 质量门禁分阶段落地登记（**R-2**）

| # | 被延后的门禁项 | 根因 | 承接方 | 登记 |
|---|---|---|---|---|
| **①** | **门禁 3** 的「`harness/demo/target.py` 原样可跑」 | `target.py:163` 的 `draw_mermaid_png()` 属 **B23F1**（未交付）⇒ ⇒ 脚本在 `:168` 的 `invoke()` **之前**中断 | **B22F1 + B23F1**（M2） | 宪法 v1.6.0（**窄口径** · 被延后的是**门禁项的某一部分**）⇒ ⇒ **判据零放宽** |
| **②** | **门禁 5** + 原则 V 的「**真实模型一轮**」 | 需**真实模型** + **厂商端点**（出网 + 凭据）⇒ ⇒ 本环境不具备 | **B25F1**（M4） | 同上 ⇒ ⇒ **已登记为环境偏离**（§5.2）⇒ ⇒ **MUST NOT** 用「未验证」替代 |
| **③** | **门禁 4** 的「**fake 模型跑通验收基线（`target.py`）的一轮**」 | 与 ① **同根因**（PNG 路径未交付）⇒ ⇒ ⇒ 且 `target.py` 用**真实** `init_chat_model` ⇒ ⇒ ⇒ **伪模型注入机制**属 **B25F1** | **B22F1 + B23F1**（M2）· **B25F1**（M4） | 同上 ⇒ ⇒ 本 feature 以 `graph_core.py` 的 A5 组 + `agent_loop.py` 的 B1 / B2 组**硬断言**交付**图能力侧**的等价证据 ⇒ ⇒ ⇒ 该证据**不冒充**门禁 4 的**验收基线 fake 轮** |

> ⚠️ **本 feature 的「fake 模型轮」**（**窄口径** · §5.1）= 猴补 `init_chat_model` + **含条件边的
> 最小图** / `agent_loop.py` 的**工具循环轮** ⇒ ⇒ ⇒ **本 feature 可达** ⇒ ⇒ ⇒
> **MUST 真跑并记录**（**已跑** · §5.1）⇒ ⇒ ⇒ **未豁免**。

---

## 7. 破冻结面的**发起者追认**（**唯一一次** · **T059 / T060 / T061** · **已签署** · 2026-11-18）

> ⚠️ **签署主体（宪法 v1.6.0）**：追认 **MUST 由发起者本人作出** ⇒ ⇒ **MUST NOT** 由实现者
> 代签 ⇒ ⇒ **未追认前 MUST NOT 合入**。
> ⇒ ⇒ **实现者**已备好并落笔下列文本（§7.0 / §7.1）；**发起者本人**在人工验收通过后
> **签署**（§7.2）⇒ ⇒ ⇒ **签署依据 = 发起者在验收结果（§1.2 / §3）呈报后的明确指令**
> （2026-11-18 · 本次会话）⇒ ⇒ ⇒ **追认已作出**（见 §7.2）。
> ⚠️ **追认次数 == 1**：**R-1**（破冻结面）· **R-2**（门禁偏离 · 宪法 v1.6.0 · **未设次数上限**
> ⇒ ⇒ **不**计入破冻结面额度）· **R-3**（跨 feature 文档接线 · 属「破冻结面」类 ⇒ ⇒ **并入**
> R-1 的**同一次**确认）⇒ ⇒ ⇒ **全 feature 的发起者确认动作 == 1 次**（三段落列 · 一次确认 · 一个日期）。

### 7.0 追认文字（**待签署**）

> 本人已确认 B8F1 的人工验收结果（全量 pytest **1607 passed / 4 skipped / 0 failed** ·
> C8 独立回归 **49 passed**（**否定式**断言）· 契约守卫 **43 passed** · 零新增面清点
> **10 passed** · 差分场景组 **D-103…D-120** 逐条符合判词（**SAME 12 / DIFF 4 / STRICTER 2** ·
> 判词非 `SAME` 的 **6** 条**均带**非空 `note`）· `graph_core.py` **36/36** 与 `agent_loop.py`
> **14/14** 且**均以退出码 0** 结束 · `target.py` 的 diff 为空 · 门禁 **G21 / G22 / G23 / G24 /
> G25 / G26 / G27 / G28 / G29** 全部通过（**G30** 的 8 条违规为**既存**问题 · 在 pristine
> `HEAD` 树上**同样复现** · **非本 feature 的回归**）· 「fake 模型轮」的**实测输出**已落本记录
> （含条件边路由的可观察结果）），并追认本 feature 的**七项破冻结面**（见 §7.1）：B7F1 的校验规则
> **V-8** 的放宽（`GraphSpec.conditional_edges` 允许非空 · 由路由求值消费）· B7F1 的
> **冻结断言 ①**（`test_superstep_basic.py:557-576`）· B7F1 的 **冻结断言 ②**
> （`test_superstep_contract.py` 的 **I-14** 映射与用例体）· B7F2 的 **冻结断言 ④**
> （`test_compiled_graph.py:263-265`）· **C8 挂载点**（`test_contract_regressions.py:36`）·
> `graph_core.py` 的 **A5 组**（+ A6 的 C16 段）· `agent_loop.py` 的 **B1 / B2 / B3 组**。
> 同时追认本 feature 的**门禁分阶段落地**（§6 的 ① ② ③：门禁 3 的端到端部分承接
> **B22F1 / B23F1**，门禁 4 的验收基线 fake 轮与门禁 5 的真实模型轮承接 **B25F1**）与
> **跨 feature 文档接线**（下游承接 **D-1…D-5** 已写入 **6** 份目标 feature 的提示词初稿）。
> **判据未放宽**（全部为「拆分而不删」或「软 ⇒ 硬」· 零条既有判据被删）⇒ ⇒ **红线照常执行**。

**发起者签字 / 日期**：杨家成 · **2026-11-18**（**已签署**）

### 7.1 追认项（**七项** · 唯一事实源 = `spec.md`「Assumptions」的「破面全集 7 类」）

| # | 破面 | 内容 | 落点 |
|---|---|---|---|
| **①** | **T-1** · B7F1 的校验规则 **V-8** | `GraphSpec.conditional_edges` **非空** ⇒ 守卫**移除**（**不再**是构造期失败）⇒ ⇒ ⇒ **五键**形态不符 ⇒ 仍**显式失败**（**V-27** · B8F1 新增）⇒ ⇒ ⇒ 原口径**逐字留存**（语义留存） | `src/freegraph/runtime/superstep.py:484-487`（移除）· `specs/b7f1-superstep-loop/contracts/superstep-contract.md` §2.1 + §2.1.1 · `specs/b7f1-superstep-loop/spec.md` **FR-033** / **裁定 25** · `specs/b7f1-superstep-loop/data-model.md` **V-8** |
| **②** | **冻结断言 ①** | `tests/runtime/test_superstep_basic.py:557-576` ⇒ **拆分**（原「非空 ⇒ 显式失败」改为「**非空 ⇒ 接受且原样承载**」+ 保留「构造期**其它**失败路径**逐条唯一**」）⇒ ⇒ ⇒ **语义留存** · **判据只收紧** | 同左 |
| **③** | **冻结断言 ②** | `tests/runtime/test_superstep_contract.py:77` 的 **I-14** 映射 + `:609-617` 的用例体 ⇒ **拆分**（语义由「恒空即失败」改为「**填值即被路由求值消费**」⇒ 断言改为「填值 ⇒ 构造**成功**且该值**原样**承载」）⇒ ⇒ ⇒ **编号与槽位不变** ⇒ ⇒ ⇒ 契约守卫的解析范围**零改动** | 同左 |
| **④** | **冻结断言 ④** | `tests/facade/test_compiled_graph.py:263-265` ⇒ **替换为反面断言**（**非空**且与 `compiled._conditional_edges` **逐字相等**）⇒ ⇒ ⇒ **判据只收紧**（恒空 ⇒ 非空且一致）⇒ ⇒ ⇒ `:111-114` 的 **11 键**持有面断言**逐字不动** | 同左 |
| **⑤** | **T-5** · **C8 挂载点** | `tests/contracts/test_contract_regressions.py:36` ⇒ `status=not-landed` 翻为 `status=landed` ⇒ ⇒ ⇒ **新增** C8 的**元测试**（路径扫描 · **零** `freegraph.*` import）⇒ ⇒ ⇒ 原占位用例**改名保留**（**MUST NOT** 删 · **MUST NOT** 与元测试**同名**） | 同左 |
| **⑥** | **T-6** · `graph_core.py` 的 **A5 组** | A5 组全部 `soft(...)` ⇒ **硬断言**（`check(...)` / `eq(...)`）⇒ ⇒ ⇒ 附带 **A6 的 C16 段**（其降级理由同为「条件边路由求值未交付」）⇒ ⇒ ⇒ **删除** `_B8F1_NOTE` 的「未交付」措辞 ⇒ ⇒ ⇒ **判据只收紧**（软 ⇒ 硬） | `harness/demo/graph_core.py:254-321` · `:334-372` |
| **⑦** | **T-7** · `agent_loop.py` 的 **B1 / B2 组** | B1 / B2 两组全部 `soft(...)` ⇒ **硬断言** ⇒ ⇒ ⇒ 附带 **B3 的「工具执行前触发中断」**（其降级理由同为「条件边路由求值未交付」）⇒ ⇒ ⇒ **删除** `_B8F1_NOTE` 的「未交付」措辞 ⇒ ⇒ ⇒ **判据只收紧**（软 ⇒ 硬） | `harness/demo/agent_loop.py:200-266` |

> ⚠️ **另有两项「变红断言」的追加登记**（**不属于**破面全集 · 判据**只收紧** ⇒ ⇒ ⇒ 无需追认）：
> ⑦ `tests/facade/_invoke_support.py:122-138` 的 `build_conditional_graph` 夹具（**修夹具** ·
> 两条断言**逐字未动**）· ⑧ `tests/runtime/test_interrupt_contract.py:176-179`（**逐字替换**
> `status=landed` + **追加**「**不得**退回」的反向断言）。

### 7.2 发起者确认（**已签署** · 2026-11-18）

```
追认人（发起者）：杨家成
追认日期：2026-11-18
追认结论：☑ 同意上述七项破面，追认本 feature 的实施结果符合本 spec / plan / 契约。

签名：杨家成（2026-11-18）
```

> ✅ **追认已作出**（2026-11-18 · **发起者本人**在验收结果呈报后作出 · 实现者仅**落笔**已获授权的
> 签署文本）⇒ ⇒ 本 feature 的**合入闸口 G5 已打开**（宪法 v1.6.0「未追认前 MUST NOT 合入」
> ⇒ 条件已满足）⇒ ⇒ **七项破面一并被追认**，**追认次数 == 1**（≤ 1 次 / feature · 宪法 v1.8.0）。
> ⇒ ⇒ ⇒ **R-2**（门禁分阶段落地 · 宪法 v1.6.0 · **未设次数上限**）与 **R-3**（跨 feature 文档接线
> · 属「破冻结面」类 ⇒ **并入**本条）⇒ ⇒ ⇒ **全 feature 的发起者确认动作 == 1 次**。

---

## 8. 遗留问题

| # | 遗留 | 归属 | 说明 |
|---|---|---|---|
| **1** | 门禁 **G30** 的 **8** 条违规 | **既存**（非本 feature） | 全部落在本 feature **未触碰**的文件上（`harness/demo/target.py` 的署名头例外未生效 · `harness/reports/Q7-*.md` 与 `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 的官方 Approved copy 文案指纹）⇒ ⇒ ⇒ **在 pristine `HEAD` 树上同样复现**（`git archive HEAD` 展开后单独跑 G30）⇒ ⇒ ⇒ **非本 feature 的回归** ⇒ ⇒ ⇒ **MUST NOT** 在本 feature 内修改只读基准 `target.py`（原则 III）⇒ ⇒ ⇒ 修复归**门禁 / 白名单**的独立议题 |
| **2** | 「真实模型轮」在本机**环境不可用**（无 `langchain_anthropic` / 无凭据 / 无出网） | **环境偏离** | 已按 v1.6.0 登记（§5.2）⇒ ⇒ **MUST NOT** 用「未验证」替代 ⇒ ⇒ **判据未放宽**（fake 轮已跑通）⇒ ⇒ 待发起者在具备凭据的环境补跑 |
| **3** | 验收脚本的**剩余 3 条软断言** | **B14F1 / B8F3 / B8F2** | 每条**具名**承接方（§3.7）⇒ ⇒ ⇒ **不是**「本 feature 未验证」 |
| **4** | 固定脚本（`target.py`）端到端轮 | **R-2 ① ③** → **B22F1 / B23F1 / B25F1** | **物理不可达成**（§5.3）⇒ ⇒ **判据不放宽** |
| **5** | 跨 feature 文档接线（D-1…D-5） | **本 feature 已落地**（**T062**） | 6 份目标 feature 的提示词初稿**已写入**「下游承接（B8F1 · 2026-11-18）」⇒ ⇒ ⇒ **属「破冻结面」类** ⇒ ⇒ **并入** §7 的**同一次**追认（**不另计次**） |
| **6** | 立项书 §5.2 的 B8F1 行「前置」列 / 行数口径 / 层标注 | **发起者**（上位文档修订） | 本 feature 以**仓库现状**为准（spec 的承接条款 **H-1…H-11**）⇒ ⇒ ⇒ **MUST NOT** 单方面修改立项书（**登记项 R-5**） |
