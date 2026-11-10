# Quickstart: B7F1 · 任务准备与执行循环（super-step）

**Feature**: `B7F1` · **Spec**: [spec.md](./spec.md) · **契约**: [contracts/superstep-contract.md](./contracts/superstep-contract.md)
**核实环境**: CPython **3.11.16** · 上游 `langgraph` **1.2.11**（核实于 2026-11-10）

> 本文件是**可照抄的验证手册**（闸口 **V1–V12**）—— 只写**怎么跑**与**期望看到什么**，
> **不含**实现代码（实现属 `tasks.md` 与实现阶段）。
> ⚠️ **本 feature 不交付 `invoke()`** ⇒ **没有** `agent.invoke(...)` 可跑；
> 全部闸口用**手写图规格**直接驱动调度内核（这正是本 feature 的独立可验收性判据 · **A3**）。

---

## 0. 前置条件

### 0.1 环境准备（**一次性 · 四条命令** · 跨平台）

```bash
# ① 建 venv —— ⚠️ 必做：uv pip install 在无活动虚拟环境时报
#    "error: No virtual environment found" 并以退出码 2 失败（B3F1 的既有结论）
python3 -m venv .venv

# ② 开发期依赖组（pytest + packaging）—— PEP 735 · 不进发行包 / 不进 Requires-Dist
.venv/bin/python -m pip install -U pip
uv pip install --python .venv --group dev

# ③ 本 feature 包（editable）
uv pip install --python .venv --editable .

# ④（**可选**）覆盖率工具 —— **不进依赖声明**（v1.0 依赖面为零）⇒ 开发期临时安装
uv pip install --python .venv coverage
```

### 0.2 **不需要**上游

本 feature 的内核**零上游依赖** ⇒ **不需要** `differential` 依赖组 ⇒
**断网**也能跑完全部闸口（宪法原则 I / IV · SC-018）。
⚠️ 上游只在 **Phase 0 取证**时用过（仓库外的临时 venv · **不进仓库**）⇒ 见
[research.md](./research.md) §1。

---

## 1. 单 super-step 跑通（**验收判据 A1** · SC-001）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_basic.py -v
```

**期望**：

| 项 | 期望值 |
|---|---|
| 订阅了有值通道的节点 | 执行次数 == **1** |
| 订阅了无值通道的节点 | 执行次数 == **0** |
| 合并后状态 | 与「按通道自身的写入规则合并」的期望**逐项相等** |
| 五阶段产物 | 逐项可观测（**执行记录** / **待写入** / **合并后状态** / **轮数** —— **四项**口径 · 逐字对应 `SuperStepResult` 的四个字段） |
| **图规格的非法形态** | **构造时**即抛错（MUST NOT 推迟到运行期）⇒ V-1 / V-2 / V-3 ⇒ 内置 **`ValueError`**（裁定 32 · 2026-11-11 分析轮第 3 次） |

⚠️ **不得**出现 `StateGraph` / `compile()` —— 闸口 **V3** 会静态扫描（**A3** · SC-005）。

⚠️ **初始值怎么来**（裁定 31 · 2026-11-11 分析轮 · 发起者批准）：「有值的初始状态」MUST 由
**调用方在跑之前直接向通道对象写入**（`channels["messages"].update(["..."])` 之类）⇒ 这是
「写入只由调度层发起」的**唯一豁免**（**初始化写入豁免** · 走通道自身的 `update()` ⇒ 通道语义不绕道）
⇒ 该通道的版本恒为 **1**
⇒ 订阅者在第 1 轮被触发。**跑之后**再直接往通道塞值 ⇒ 调度器**看不见** ⇒ **不**触发任何节点。

---

## 2. 同轮多写按归约器合并（**验收判据 A2** · SC-002 / SC-023）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_merge.py -v
```

**期望**：

| 场景 | 期望值 |
|---|---|
| 两个节点同轮各写一次归约通道 `messages` | 结果含**两条**消息，且 == `operator.add` 的**逐元素**结果 |
| 两个节点同轮各写一次**覆盖型**通道 | 抛 `InvalidChannelUpdateError`，其 `.key` 指向该通道；**不**静默保留后一个 |

---

## 3. 脱离构建器（**验收判据 A3** · SC-005）

```bash
# ① 静态扫描：调度内核的用例里不得出现 StateGraph / compile()
.venv/bin/python -m pytest tests/runtime/test_superstep_purity.py -v

# ② 内核路径不得 import 图定义层 / 上游
.venv/bin/python -m pytest tests/contracts/test_architecture.py -v
```

**期望**：全部通过；`freegraph.graph` / `freegraph._stategraph` 的导入次数 == **0**。

---

## 4. 触发判定与版本号（SC-003 / SC-004 · 用户故事 3 / 4）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_trigger.py -v
```

**期望**：

| 场景 | 期望值 |
|---|---|
| 写入一个与当前值**逐字相等**的值 | 下游订阅者**仍被触发** |
| 同一版本再次进入触发判定 | 已消费过该版本的节点**不被重复触发** |
| 未被触发的节点 | 执行次数 == **0** |
| 同轮被边与通道同时触发 | 只执行**一次** |
| **两个入口**（单轮 / 多轮）× **独立** `SchedulerState` | 触发判定结果**互不影响**（「已消费版本」**不串扰** · FR-004） |

---

## 5. 收敛与步数上限（SC-006 · 用户故事 5）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_convergence.py -v
```

**期望**：

| 场景 | 期望值 |
|---|---|
| 触发集合为空 | 循环**立即终止** ⇒ `executed` == **空元组**且 `steps` == **1**（**只含**那次发现「任务集为空」的**空轮**） |
| 首轮即执行 1 个节点 | `executed` **非空**且 `steps` == **2**（1 个执行轮 + 1 个空轮） |
| 自环规格 | 在**上限 25** 处抛 `GraphRecursionError`（`recursion_limit=25` · `current_step=25`） |
| 不显式指定上限 | 实际生效上限 == **25**（签名缺省值与行为值 MUST 一致） |
| **多轮入口**（≥ 2 个执行轮） | `executed` == 各轮执行序列的**顺序拼接** · `node_writes` 中**同名节点**的**同一通道**的值序列 == **按轮次先后拼接**（**不**按通道重排） |
| **单轮入口** `run_super_step` | `steps` **恒为 1**（多轮入口的 `steps` == **实际迭代轮数**） |
| **两个入口** × **独立** `SchedulerState` | 触发判定结果**互不影响**（「已消费版本」**不串扰**） |
| **两个计数器** | `SchedulerState.step`（**执行轮** · **不含**空轮）在**每个执行轮结束 +1**、**空轮不 +1** ⇄ `SuperStepResult.steps`（**含**空轮）⇒ **MUST NOT** 混用 |

---

## 6. 原子性（SC-024 · 裁定 22）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_atomicity.py -v
```

**期望**：四类场景（节点抛异常 · 未知 key · 归约器抛错 · 覆盖型多写冲突）**各自**至少一例，
且出错后**全部**通道的值与**本轮开始前**逐字相等。

---

## 7. C4 回归测试的**节点边界**口径（SC-009 / SC-010 · 承接 H-1）

```bash
# C4 独立回归测试（用例住在 tests/runtime/ —— 避开门禁 G2）
.venv/bin/python -m pytest tests/runtime/test_read_c4_sparse_state.py -v

# 挂载点元测试（只做路径扫描 · MUST NOT import freegraph.*）
.venv/bin/python -m pytest tests/contracts/test_contract_regressions.py -v
```

**期望**：

| 断言 | 期望值 |
|---|---|
| 「真实节点收到的入参」不含无值通道的 key | 成立（**否定式**） |
| `node_input.get("<无值通道>", <default>) == <default>` | 成立（**不是** `None`） |
| `type(node_input) is dict` | 成立 |
| **读取层口径**的断言仍在 | **保留**（并存 · FR-017） |
| 挂载点两条 `GATE-MOUNT:` 行 | **逐字不动**（C4 `landed` · C8 `not-landed`） |

---

## 8. 步末清空范围（SC-012 · 承接 H-2 · research D-05）

```bash
.venv/bin/python -m pytest tests/runtime/test_superstep_clearing.py -v
```

**期望**：步末对**覆盖型 / 归约型**调 `clear()` 的次数 == **0**；
对**本轮被写入过的**路由型通道调用的次数 == **0**（其值保留到下一轮）；
对**本轮未被写入的**路由型通道调用的比例 == **100%**。
⚠️ **两个入口都执行**（裁定 33 · 2026-11-11 分析轮第 3 次 · 发起者裁决）：单轮入口
`run_super_step` 跑完一轮后**同样**执行步末清空 ⇒ 两个入口的**调用集合与次数逐项相等**
⇒ 「单轮入口不清空」的用例数 == **0**。
⚠️ **计数窗口 MUST 限定在「步末清空阶段」**（裁定 29 的豁免）—— 合并阶段的**回滚路径**会调
`clear()` ⇒ 该调用**不计入**本节计数。

---

## 9. 导出面与冻结面（SC-016 / SC-015 / SC-011）

```bash
.venv/bin/python -m pytest tests/runtime/test_read_contract.py -v   # 含 RUNTIME_SYMBOL_COUNT == 20
.venv/bin/python -m pytest tests/contracts/ -v                      # G7 / G8 / G15 / G19 / G29
```

**期望**：`freegraph.runtime.__all__` 的符号数 == **20**（含 6 个新符号）；
契约层 **18** 符号面 / 门面 **7** 符号面 / 兼容矩阵 / `THIRD_PARTY_NOTICES` 差异 == **0**。

---

## 10. 覆盖率取证（SC-017）

```bash
# ⚠️ 覆盖率工具**不进依赖声明**（v1.0 依赖面为零）⇒ 开发期临时安装
.venv/bin/python -m coverage run --branch -m pytest tests/runtime/ -q
.venv/bin/python -m coverage report --include="src/freegraph/runtime/superstep.py" -m
```

**期望**：`src/freegraph/runtime/superstep.py` 的**行覆盖 == 100%** 且**分支覆盖 == 100%**。
⚠️ 「新增代码」的范围 = 该文件**全文** + `runtime/__init__.py` 的**新增导出部分**（测试代码不计入）。

---

## 11. 跨 feature 接线复核（宪法 **v1.8.0**）

```bash
# ① 上游承接 H-1：B5F2 的 C4 节点边界条款已写在 B7F1 的提示词初稿里
grep -n "承接条款（B5F2 → B7F1" harness/features/B7F1_任务准备与super-step循环.md

# ①' 上游承接 H-2…H-5（B5F1 的三条口径交接 + B5F2 的稀疏读唯一实现 · 2026-11-11 追补）
grep -n "承接条款（B5F1 → B7F1\|承接条款（B5F2 → B7F1 · M1 · 稀疏读唯一实现）" \
  harness/features/B7F1_任务准备与super-step循环.md

# ② 下游承接：本 feature 的条件边字段预留条款 MUST 写入 B8F1 的提示词初稿
grep -n "条件边" harness/features/B8F1_条件边路由与fresh读.md

# ③ 导航文件
grep -n "B7F1" harness/features/README.md
```

**期望**：四处均命中，且**措辞**与裁定 25 / 承接 **H-1…H-5** / 下游承接 **D-1** 一致
（⚠️ **标题命中不足以判通过** ⇒ 须校验措辞 · 沿用 B5F2 的同款口径）。

---

## 12. 人工验证记录与验收闸口（SC-021 / SC-022）

### 12.1 记录落点与五段式

`harness/verification/B7F1/manual-verification.md` MUST 存在，且含**五段式**小节：
**验证环境** · **验证步骤** · **实际输出** · **结论** · **遗留问题**
（+ 可选第 ⑥ 段「移交后续 feature」）+ **来源覆盖表**（判据 / SC / FR 各一张 · 覆盖率 == 100%）。

⚠️ **未实跑的项 MUST 显式记入「遗留问题」** —— MUST NOT 伪造输出。

### 12.2 验收闸口（`V1`–`V12`）

> ⚠️ **编号空间消歧**（B3 · 2026-11-11 分析轮第 3 次）：本表的 **V1–V12** = **验收闸口**
> （无连字符）· `data-model.md` §6 的 **V-1…V-9** = **校验规则**（连字符）⇒ 两个 V 空间
> **并存但不相通** ⇒ 引用时 MUST 写全（**「验收闸口 Vn」** / **「校验规则 V-n」**）。

| **闸口** | 内容 | 章节 | 判据 |
|---|---|---|---|
| **V1** | 单 super-step 跑通 | §1 | **A1** · SC-001 |
| **V2** | 同轮多写按归约器合并 + 覆盖型冲突显式失败 | §2 | **A2** · SC-002 / SC-023 |
| **V3** | 脱离构建器（无 `StateGraph` / `compile()`） | §3 | **A3** · SC-005 |
| **V4** | 触发判定与版本号推进（**含两入口不串扰**） | §4 | SC-003 / SC-004 |
| **V5** | 收敛与步数上限（缺省 25 · **含多轮累计语义**） | §5 | SC-006 / SC-001 |
| **V6** | 一轮 super-step 的原子性 | §6 | SC-024 |
| **V7** | C4 回归的**节点边界**口径 + 读取层口径并存 + 挂载点零改动 | §7 | SC-009 / SC-010 / SC-011 |
| **V8** | 步末清空范围（只清「本轮未写入的」路由型 · **两个入口都执行**） | §8 | SC-012 |
| **V9** | 导出面（14 → 20）与既有冻结面零改动 | §9 | SC-016 / SC-015 |
| **V10** | 覆盖率 == 100%（行 / 分支） | §10 | SC-017 |
| **V11** | 跨 feature 接线复核（上游 **H-1…H-5** + 下游 **D-1**） | §11 | SC-025 |
| **V12** | 人工验证记录五段式 + 来源覆盖表 + **发起者追认** | §12 | SC-021 / SC-022 |


⚠️ **发起者追认（V12 的后半段）**：本 feature **不交付** `compile()` / `invoke()`
⇒ 宪法质量门禁第 3 / 4 / 5 项中的「固定脚本原样可跑」「fake 模型一轮」「真实模型一轮」
**物理不可达成** ⇒ 依宪法 **v1.6.0** 的通则处置（**偏离登记 + 发起者追认**）⇒
追认文字 MUST 落在 `harness/verification/B7F1/manual-verification.md` ⇒
**未追认前 MUST NOT 合入** · **MUST NOT** 由实现者代签（spec **FR-031** · 裁定 20 · 登记项 **R-1**）。

---

## 13. 常见问题

| 症状 | 原因 | 处置 |
|---|---|---|
| 第一轮「谁都不触发」 | 调用方在**跑的过程中**才往通道塞值 ⇒ 调度器看不见 ⇒ 不触发 | 初始值 MUST 在**跑之前**预置（裁定 21 · research **D-01**） |
| 归约通道只剩一条消息 | 逐次调用了 `update()` ⇒ 退化成「后写覆盖先写」 | MUST **批量**调一次 `update(values)`（裁定 5） |
| 覆盖型通道**没报错**却只剩后一个 | 合并前没做未知 key / 多写校验 | MUST 走 `Channel.update(values)` 的批量路径（FR-005 ②） |
| 路由通道的值「一写就消失」 | 步末清了**本轮写过的**路由通道 | MUST **只清「本轮未被写入的」**（research **D-05**） |
| `GraphRecursionError` 提前抛出 | 图里有自环；上限缺省 **25** | 修图，或显式传 `max_steps` |
| CI 报 `RUNTIME_SYMBOL_COUNT` 不符 | 导出面从 **14 → 20** | 同步更新 `tests/runtime/test_read_contract.py:80` |
