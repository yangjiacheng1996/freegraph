# B8F1 · Phase 0 研究记录（上游实测取证 + 决策登记 + 遗留登记）

**Feature**: `B8F1` · 条件边路由求值 + `END` 终止 + fresh 读（C8 独立回归测试）
**Spec**: [./spec.md](./spec.md) · **Plan**: [./plan.md](./plan.md)
**取证日期**: 2026-11-17 · **上游版本**: `langgraph` **1.2.11** + `langchain-core` **1.7.6**

> **本文件是「证据」载体，不是「判据」载体** —— 判据的唯一权威是 spec 与
> `contracts/conditional-edge-contract.md`（Phase 1 写就）；
> 本文件 MUST NOT 被测试解析（测试**直接断言行为** ⇒ 避免「判据与实现同源 ⇒ 自证」）。

> ⚠️ **编号域隔离**（沿用 B7F1 / B5F2 的同款纪律）：
> 本文的 **D-01…D-24** 是**决策**编号 · **DR-1…DR-n** 是**遗留登记**编号 ·
> **C-1…C-n** 是**事实性更正**编号 · **E-n / M-x / N-x / P-x** 是**实测编号**；
> 它们与 spec 的「下游承接 **D-1…D-5**」「差分场景 **D-103…D-120**」
> 「承接条款 **H-1…H-11**」是**四套互不相干的编号域** ⇒ 引用时 MUST 写全前缀。

---

## §0 方法与取证环境

### 0.1 取证环境（零仓库改动）

| 项 | 值 | 核实方式 |
|---|---|---|
| 上游版本 | `langgraph` **1.2.11** · `langchain-core` **1.7.6** | `importlib.metadata.version` |
| 版本钉死 | `pyproject.toml:100`（`"langgraph==1.2.11"` · 属 `differential` **依赖组**） | 读文件 |
| 解释器 | CPython **3.11.16** | `.venv/bin/python -c "import sys"` |
| 探针解释器 | `/home/ctyun/workspace/github/freegraph/.venv/bin/python` | —— |
| 探针脚本目录 | `/tmp/opencode/b8f1/`（**干净目录** · **仓库之外**） | —— |
| 上游包根 | `.venv/lib/python3.11/site-packages/langgraph/` | —— |
| 仓库改动 | **零**（`pyproject.toml` 未动 ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿） | `git status --porcelain` |

⚠️ **探针目录纪律**（实测踩坑记录）：探针脚本 MUST 置于**干净目录**
（`/tmp/opencode/b8f1/`）⇒ 若从含杂散模块的目录运行，`import langchain_core`
会触发**循环 import 的 `ImportError`**（报错信息极具误导性）。
⇒ 另：上游 import MUST 走 `from langgraph.graph.state import StateGraph, START, END`
（直接 `import langgraph.graph` 在部分上下文下同样触发该循环 import 问题）。

⚠️ **差分组的定位**：`langgraph` 属 **PEP 735 的 `differential` 依赖组**
（`pyproject.toml:99-101`）⇒ **不是**运行时依赖 ⇒ `pyproject.toml` **零改动**
⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿（宪法原则 II · 原则 X）。

### 0.2 每条断言的**实测命令形态**

```bash
# ① 源码锚点定位（行号 MUST 逐条复核，不凭记忆）
SP=/home/ctyun/workspace/github/freegraph/.venv/lib/python3.11/site-packages
awk 'NR>=96 && NR<=114 {printf "%d: %s\n", NR, $0}' $SP/langgraph/graph/_branch.py

# ② 行为断言（探针脚本 · 仓库外）
cd /tmp/opencode/b8f1
/home/ctyun/workspace/github/freegraph/.venv/bin/python p1_routing.py
```

本轮共 **7** 个探针脚本（`p1`…`p7`），覆盖 §2 的 **全部** 行为断言。

| 探针 | 覆盖的实测编号 |
|---|---|
| `p1_routing.py` | E-1 … E-16 · M-A … M-H |
| `p2_end_send.py` | E-3b / E-3c / E-5c / E-9b / E-11 … E-23 |
| `p3_start.py` | N-A1 … N-A8 |
| `p4_twoarg.py` | P-A01 … P-A19（双参判别矩阵） |
| `p5_misc.py` | P-B / P-C / P-D / P-E / P-F / P-G / P-H |
| `p6_extra.py` | Q-1 … Q-7（`Send` 混合 · 去重 · `set` 返回） |
| `p7_freegraph.py` | E-34（freegraph 侧**现状**：静默空跑） |
| `p8_norm.py` | E-18（构建期归一化的**直接观测**） |

### 0.3 纪律（本轮的自证要求）

- **宪法原则 VIII（证据与术语纪律）**：每条**事实性结论** MUST 附 `路径:行号`
  （上游用上游路径 · freegraph 用仓库路径）。
- **行为断言 MUST 有实测支撑** —— ⚠️ **只读源码不足以支撑行为断言**：
  `_branch.py:203` 的 `self.ends[r]` 只是「**会**抛 `KeyError`」的**依据**，
  「**抛的是什么**、**抛在哪个场景**」由 §2 的**实测**给出（E-5 / E-6 / E-7 / M-C / M-E）。
- **宪法原则 XI（上游优先 · 上游锚点纪律）**：上游有答案 ⇒ 照抄 ⇒ 不问用户；
  上游**自身无定论**（代码与 docstring 矛盾）⇒ 取**更确定**的一侧 ⇒ 如实登记偏离。
- **换上游版本 ⇒ MUST 重新核实全部行号**（`pyproject.toml:100` 钉死版本）。

---

## §1 决策表（D-01 … D-24）

### D-01 · 路由求值落 **L2 `run_super_step` 的阶段 ③′**（源节点任务**成功落回**时）

- **Decision（决策）**：路由求值 MUST 落在 **L2 的 super-step 循环内部**
  （`run_super_step` / `run_super_steps` 的**阶段 ③′「判定与落回」**），
  于**源节点任务成功落回**之后求值；MUST NOT 另开「条件边专用」的调度路径；
  MUST NOT 在源节点执行**前**或**节点入参构造**时求值。
- **Rationale（理由）**：上游同款 —— 上游的分支是**源节点的 writer**
  （`langgraph/graph/state.py:1624`：
  `self.nodes[start].writers.append(branch.run(get_writes, reader))`）
  ⇒ 分支随源节点任务完成而执行（**实测 E-24**：节点挂起时路由函数**未被求值**，
  `router called = 0`）⇒ 「落回后求值」是上游的**结构事实**而非设计取舍。
  落 L2 ⇒ 路由产生的写入进入**同一份**完整状态（H-5 · B7F3 的 D-2）；
  阶段 ③′ 早于阶段 ⑤（写入合并）⇒ 路由函数读到「**轮次开始前的通道值 + 本节点本次写入**」。
  ⇒ 落点：**spec FR-001 / FR-002 / FR-005** · **裁定 1** · **SC-002 / SC-013**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **编译期固化目标** —— 否决：目标由**运行期**路由函数决定，编译期不可知。
  ② **独立的「条件边调度路径」** —— 否决：会造出第二套调度器 ⇒ 语义必然漂移
  （spec FR-002 · 宪法原则 XII「最优设计优先」）。
  ③ **在节点入参构造时求值** —— 否决：此时写入尚未落回 ⇒ fresh 读无意义（FR-001）。

### D-02 · fresh 读的**唯一**实现点 = `local_read(channels, writes, fresh=True)`

- **Decision（决策）**：路由函数的状态视图 MUST 由 B5F2 的
  `local_read(channels, writes, fresh=True)` 产出 ⇒ MUST **显式**传 `fresh=True`
  （**缺省是 `False`**）⇒ MUST NOT 依赖缺省 ⇒ MUST NOT 在调度层另写一份合并逻辑
  ⇒ MUST NOT 假设上游的 `managed` 语义。
- **Rationale（理由）**：上游同款 —— 上游 fresh 分支在
  `langgraph/pregel/_algo.py:211-219`（逐通道 `copy()` + `update(updated[k])`）
  ⇒ 路由读的 reader **显式** `fresh=True`（`langgraph/graph/state.py:1613-1619`）。
  实测 **E-10**（路由函数看到 `{'messages': ['fresh'], 'llm_calls': 7}`）
  与 **E-16**（归约型通道合并为 `['seed', 'n1']`）证实 C8 语义。
  freegraph 侧 `local_read` 的**缺省是 `False`**（`src/freegraph/runtime/read.py:163-197`）
  ⇒ MUST 显式传参；`fresh=True` 的实现是 `_fresh_read`
  （`src/freegraph/runtime/read.py:101-133` · 逐通道 `copy.copy` ⇒ 零污染）。
  ⇒ 落点：**spec FR-007 … FR-012** · **裁定 2** · **SC-004 / SC-010**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **调度层自写 fresh 合并** —— 否决：会产生第二份归约逻辑（漂移风险）且违反 FR-007。
  ② **依赖 `fresh` 缺省** —— 否决：缺省是 `False`（B5F2 `read-contract.md` §1.1）。
  ③ **照搬上游 `local_read` 的六参签名** —— 否决：含 freegraph **不实现**的
  `managed`（**DR-1**）⇒ 只需**语义**同款，不需**签名**同款。

### D-03 · 路由函数的入参 = **覆盖整张通道表**的 fresh 视图（路由型通道**缺席**）

- **Decision（决策）**：路由函数 MUST 收到**覆盖整张通道表**的 fresh 视图；
  **路由型通道**（`EphemeralValue`）MUST **缺席**；**无值**的覆盖型通道 MUST **缺席**（稀疏）；
  MUST NOT 收窄为「源节点订阅集」；MUST NOT 用「`branch:to:` 前缀」启发式判定路由通道。
- **Rationale（理由）**：上游同款 —— **实测 E-10**：路由函数看到的 key 集合 =
  `['llm_calls', 'messages']`（**全部 schema 通道**），**不是**源节点的订阅集；
  上游的 reader 以 `select=channels`（整张通道表）读取
  （`langgraph/graph/state.py:1615`）。路由型通道**缺席**是 `EphemeralValue` 的
  `update([])` 清空副本之**结果**（上游 `langgraph/channels/ephemeral_value.py`）
  ⇒ freegraph 侧沿用 B5F2 的**同款副本法** ⇒ 同一实现点自动满足（D-02）
  ⇒ MUST NOT 用名称启发式（FR-011 / FR-029）。
  ⇒ 落点：**spec FR-011 / FR-013** · **裁定 3** · **SC-010**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **只传源节点订阅集** —— 否决：与上游**可观察不等价**（实测 E-10）。
  ② **按名称前缀过滤路由通道** —— 否决：违反 FR-011 的「非启发式」硬约束。
  ③ **把路由通道的值注入视图** —— 否决：上游同款**缺席**（实测 E-10 的 key 集合）。

### D-04 · `path_map` 在 L2 只有 **dict** 与 **`None`** 两种形态（L2 **零归一化**）

- **Decision（决策）**：L2 MUST **只**消费 L3 已归一化的 `path_map`
  （**dict** 或 **`None`**）⇒ MUST NOT 重新归一化 ⇒ MUST NOT import
  `freegraph._stategraph` / `_ConditionalEdgeSpec` ⇒ MUST NOT 另起路由通道命名
  （沿用 `branch:to:<target>`）。
- **Rationale（理由）**：上游的归一化在**构建期**完成
  （`langgraph/graph/_branch.py:96-101`：dict ⇒ `copy()` · list ⇒ `{name: name}`），
  与 freegraph 的 L3（`src/freegraph/_stategraph.py:118-159` 的 `_normalize_path_map`）
  **同层同款** ⇒ 归一化位置不同但**行为面逐字同款**（**实测 E-1 / E-2**）。
  **实测 E-18** 直接观测到归一化后的产物（`compiled.builder.branches`）：
  list ⇒ `ends = {'a': 'a', 'b': 'b'}` · dict ⇒ `ends = {'hit': 'a', 'miss': 'b'}`
  · `None` ⇒ `ends = None` ⇒ 证明归一化**只**发生在**构建期**。
  L3 的 `_conditional_mapping()`（`src/freegraph/_stategraph.py:205-225`）
  已产出**外层 key = 源节点名 · 内层恰 5 键 · 顺序 = 登记顺序**的 plain mapping
  ⇒ L2 MUST 原样消费（H-3 / H-4 · 裁定 4）。
  ⇒ 落点：**spec FR-014 / FR-016** · **裁定 4** · **SC-005 / SC-013**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **L2 内再做一次 list ⇒ dict 归一化** —— 否决：违反 FR-016 + 裁定 4（重复实现）。
  ② **L2 直接持有 `_ConditionalEdgeSpec` 对象** —— 否决：违反层纪律（G25 · ARCH-1），
  且会把 L3 的类型泄漏进 L2。
  ③ **在 L3 之外另建一套条件边载体** —— 否决：会产生第二套来源（T-3 不破的要求）。

### D-05 · `END` 的判定**先于** `path_map` 查表 ⇒ **单独返回** `END` ⇒ **无条件终止**（序列内的 `END` ⇒ **剔除**）

- **Decision（决策）**：路由函数**单独返回** `END`（`'__end__'` · **非**序列）时 MUST **无条件终止整张图**；
  `END` 的判定 MUST **先于** `path_map` 查表；序列中**同时**含 `END` 与其它目标时
  ⇒ `END` 被**剔除**、其余目标照常执行。
- **Rationale（理由）**：**上游代码与上游自己的 docstring 相互矛盾** ⇒ 属原则 XI ② 类
  （上游自身的不确定）⇒ 取**更确定**的一侧。
  · 上游**代码**：查表 `self.ends[r]`（`langgraph/graph/_branch.py:202-204`）
    **先于** `END` 的剔除 ⇒ `path_map` 不含 `END` **键**时返回 `END` ⇒
    **实测 E-5 / E-20**：`KeyError: '__end__'`。
  · 上游**docstring**：`langgraph/graph/state.py:999` 写
    「If it returns `'END'`, the graph will stop execution.」⇒ **无条件**。
  ⇒ 「`END` 是 key」才终止是**查表顺序的副产品**，不是上游的**设计意图**
  ⇒ freegraph 取 docstring 口径 ⇒ **单独返回** `END` ⇒ **无条件终止** ⇒ 如实登记偏离 **X-2**（DIFF · 非更严）·
  ⇒ 差分 **D-110 与 D-118**（两例）锁住（实测 **E-13** 证实 `[END, 'a']` ⇒ `a` 执行 1 次
  · 实测 **E-35** 证实 `{END: "b"}` ⇒ 上游路由到 `b` · **不终止**）。
  ⇒ 落点：**spec FR-019** · **裁定 5** · **偏离 X-2** · **SC-003 / SC-006**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **照抄上游代码（`END` 不在 `path_map` 键内 ⇒ `KeyError`）** —— 否决：
    上游自身无定论（docstring 反证）⇒ 取 docstring 口径更确定（原则 XI ② 类）。
  ② **只在 `path_map` 存在时判 `END`** —— 否决：**实测 E-19 / Q-7**：上游在
    **无** `path_map` 时返回 `END` ⇒ **正常终止**（不抛错）⇒ 判据必须与
    「有无 `path_map`」**正交**。

### D-06 · 非法路由返回值的失败信号 = **两态**（有 ⇒ `KeyError` · 无 ⇒ `ValueError`）

- **Decision（决策）**：**有** `path_map` 时返回值不在表内 ⇒ 内置 **`KeyError`**；
  **无** `path_map` 时返回值不是已注册节点名 / `END` ⇒ 内置 **`ValueError`**；
  两态的**消息**均 MUST **指明返回值与可选目标** ⇒ MUST **NOT** 新增异常类型。
- **Rationale（理由）**：照抄上游的**两态**（**实测**）：
  · **有** `path_map` ⇒ 查表失败 ⇒ `KeyError`（**实测 E-6** `KeyError('nope')` ·
    **E-7** `KeyError('other')` · **M-C** `KeyError(None)` · **M-E** `KeyError('__start__')`）
    ⇒ 触点 `langgraph/graph/_branch.py:203`。
  · **无** `path_map` ⇒ 走不到查表 ⇒ `ValueError("Branch did not return a valid destination")`
    （**实测 M-B** / **M-D**）⇒ 触点 `langgraph/graph/_branch.py:207-208`。
  上游的差异源自**查表顺序**而非刻意设计 ⇒ 原则 XI ② 类 ⇒ 发起者于
  **2026-11-17 澄清轮 Q2** 拍板「照抄上游两态」（两场景本就是两种失败）。
  消息**比上游更详细** ⇒ 属「失败信号 MAY 更严」⇒ **STRICTER**（**X-1 / X-3**），
  **类型逐字同款** ⇒ 差分 **D-107 / D-113** 只比对**类型**。
  ⇒ 落点：**spec FR-021 / FR-022 / FR-025** · **裁定 6 / 裁定 7** · **SC-006 / SC-007**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **统一成一种异常** —— 否决：发起者已拍板（澄清轮 Q2 = 选项 B）；且会抹掉
  「查表场景」与「目标非法场景」的**语义区分**。
  ② **无 `path_map` 的非法目标也用 `KeyError`** —— 否决：与上游在该形态下的
  失败信号**不同型** ⇒ 违反「类型逐字同款」（照抄纪律 ①）。
  ③ **上游的静默忽略**（**实测 E-8**）—— 否决：属原则 XI ② 类 ⇒ **STRICTER**
  （**X-3**）；且与 B7F3 的 **X-2**（未知 key ⇒ 显式失败）同类。

### D-07 · **序列**返回 = **多目标并行 fan-out**（共享状态 · 无逐目标载荷 · 去重保序）

- **Decision（决策）**：路由函数返回 `list` / `tuple` ⇒ MUST 解析为**多个目标**；
  多个目标 MUST 在**同一轮**并行执行；各目标 MUST 收到**同一份**共享状态
  ⇒ **无**逐目标载荷 ⇒ MUST 与 `Send` **语义相异**；目标序列 MUST **去重保序**。
- **Rationale（理由）**：上游同款 —— `langgraph/graph/_branch.py:199-200`
  （`if not isinstance(result, (list, tuple)): result = [result]`）
  ⇒ 只有 `list` / `tuple` 是「多目标」，**其它**容器（`set`）**不是**
  （**实测 E-27 / Q-4 / M-H**）。**实测 E-9 / E-9b**：两个目标**同轮**执行、
  各自收到**逐字相等**的入参 ⇒ 共享状态、无逐目标载荷。
  **实测 E-26 / Q-2**：序列含重复目标 ⇒ 目标节点**只执行 1 次** ⇒ 去重保序。
  ⇒ 落点：**spec FR-018 / FR-024** · **裁定 9** · **SC-008**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **把序列当作「一个不可哈希的 key」** —— 否决：上游**逐字相反**（`_branch.py:199-200`）
  ⇒ 且实测 **M-H**（`['a', 'zz']` ⇒ `KeyError('zz')` ⇒ 失败发生在**元素**层）。
  ② **序列目标各带一份载荷** —— 否决：那是 `Send` 的语义（实测 E-11 · E-23）。
  ③ **序列目标跨轮顺序执行** —— 否决：上游**同轮**（实测 E-9b）。

### D-08 · 路由返回 `Send` ⇒ **复用 B11F1 的既有构造器**（不另写条件边专属路径）

- **Decision（决策）**：路由函数返回 `Send` / `list[Send]` 时 MUST 产生**同款** fan-out 任务
  ⇒ MUST **只**把返回值**喂进** B11F1 的 `validate_send` / `make_fanout`
  ⇒ MUST NOT 另写「路由来源」的 fan-out 路径 ⇒ MUST NOT 改 B11F1 的校验规则。
- **Rationale（理由）**：上游同款 —— `Send` 实例**不**查表
  （`langgraph/graph/_branch.py:203` 的 `r if isinstance(r, Send) else self.ends[r]`）
  ⇒ **实测 E-11**：目标节点收到的是 `Send` 携带的**载荷**，**不是**共享状态；
  **实测 E-23**：序列里混入 `Send` 与普通目标名 ⇒ 两者**并行**投递
  （`Send` 目标带载荷 · 普通目标带共享状态）。
  freegraph 侧的构造器在 `src/freegraph/runtime/_fanout.py:56-82`（`validate_send`）
  与 `:85-104`（`make_fanout`）⇒ 只接线（H-8 · 裁定 10 · 下游承接 D-3）。
  ⇒ 落点：**spec FR-011 / FR-020 / FR-030** · **裁定 10** · **SC-008**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **为路由来源单独写一套 fan-out 任务构造** —— 否决：会产生第二种任务形状 ⇒ 漂移。
  ② **本 feature 实现 `Send` 的调度** —— 否决：属 B11F1（spec 引文差异 8 · FR-036）。
  ③ **把 `Send` 当作普通目标名处理** —— 否决：与上游**语义相异**（实测 E-11）。

### D-09 · 路由通道（`branch:to:<target>`）**不被写入** —— 只作**声明载体**

- **Decision（决策）**：路由通道 MUST **不被写入** ⇒ 它**只作声明载体**
  （供 `targets` / `route_channels` 口径与未来的图导出用）⇒ 触发 MUST 由**动态边**投递
  ⇒ MUST **NOT** 触发 **V-6**（单值语义通道一轮收到多于一个值）。
- **Rationale（理由）**：**硬约束** —— 上游把路由通道写成 `EphemeralValue(Any, guard=False)`
  （`langgraph/graph/state.py:1524-1530`）并**写** `branch:to:<target>` 以**触发**目标
  （`langgraph/graph/state.py:1581-1596` 的 `get_writes`）⇒ 上游用 `guard=False` 规避了
  单值冲突；而 freegraph 的 `V-6`（单值语义通道一轮收到多于一个值 ⇒
  `InvalidChannelUpdateError`）**不可放宽** ⇒ 同轮**两个源**路由到**同一目标**时
  写两次 ⇒ 必红 ⇒ **不写**是 freegraph 触发模型下的**唯一**正确选择。
  ⇒ 落点：**spec FR-028** · **裁定 8** · **偏离 X-4** · **SC-011**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **照抄上游写通道** —— 否决：会触发 V-6（既有判据不可放宽）。
  ② **把路由通道改成多值语义** —— 否决：那是改 B7F1 的**冻结面**（通道语义）。
  ③ **用通道写入 + 单独的目标集合** —— 否决：会引入第二套触发源 ⇒ 与 B7F1 §3.0 冲突。

### D-10 · 触发投递 MUST 走**既有的「动态边」载体**（零新增触发机制 · 零新增私有字段）

- **Decision（决策）**：路由目标 MUST 通过**既有的动态边载体**投递触发
  ⇒ MUST NOT 增删编译产物的私有字段（`vars(compiled)` 键数仍 == **11**）
  ⇒ MUST NOT 另写一套「条件边触发」机制。
- **Rationale（理由）**：freegraph 的触发源恒为**边**（B7F1 契约 §3.0「上游对齐 P1-0」）
  ⇒ 上游的「`branch:to:` 通道触发」≡ freegraph 的**边触发**（**同款语义** · 不同载体）。
  既有载体 = `SchedulerState.dynamic_edges`（`src/freegraph/runtime/superstep.py:264`）
  ⇒ 由 `_commit_outcome`（`:979-1014` · `:987` 写
  `state.dynamic_edges[target] = outcome.gotos`）
  落盘 ⇒ `_trigger_groups`（`:613-657`）把动态边编成**单元素组**。
  路由通道**不写**（D-09）⇒ 动态边是**唯一**触发路径 ⇒ 两条来源
  （`Command.goto` / 路由）**同款**。
  ⇒ 落点：**spec FR-005 / FR-020 / FR-031** · **裁定 1 / 裁定 13** · **SC-016**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **新增编译产物私有字段承载路由目标** —— 否决：破 **T-3**（11 键持有面是冻结面）。
  ② **新增一套「条件边触发组」** —— 否决：会产生第二种触发语义 ⇒ 漂移。
  ③ **复用路由通道触发** —— 否决：见 D-09（触发 V-6）。

### D-11 · 双参路由函数的**判别依据 = 第二参的**参数名**是 `config`**

- **Decision（决策）**：MUST 支持**单参**（`f(fresh_view)`）与**双参**
  （`f(fresh_view, config)`）两形态 ⇒ 判别依据 MUST 是
  「**第二参的参数名是 `config`**」（**不是**位置参数个数）
  ⇒ MUST **永远只传一个位置实参**（fresh 视图）⇒ `config` MUST 以**关键字**注入
  ⇒ 第二参**不存在**或名字**不叫** `config` ⇒ MUST 按**一参**调用（上游同款 ⇒ `TypeError`）
  ⇒ `**kwargs` 形态 MUST **NOT** 注入（上游同款 ⇒ kwargs 为空）。
- **Rationale（理由）**：照抄上游 —— 上游的 `self.path.invoke(value, config)`
  （`langgraph/graph/_branch.py:166`）经 `RunnableCallable`
  ⇒ 判别发生在 `RunnableCallable.__init__` 里（`langgraph/_internal/_runnable.py:299`
  与 `:341-365`）⇒ 按 `KWARGS_CONFIG_KEYS` 的 `"config"` 项（`:168-181`）查**参数名**
  ⇒ **关键字**注入 ⇒ **永远只传一个位置实参**。
  **实测矩阵**（P-A01 … P-A11 · P-A18）：`f(state)` ⇒ 一参调用；
  `f(state, cfg)` ⇒ `TypeError`；`f(state, config)`（无注解）⇒ OK；
  `f(state, *, config)` ⇒ OK（`config` 拿到 **dict**）；`f(state, **kwargs)` ⇒ OK 且
  **kwargs 为空**；`f(state, *args)` ⇒ 一参调用；`f()` / `f(a,b,c)` ⇒ `TypeError`；
  可调用对象 `__call__(self, state, config)` ⇒ OK；`f(state, config, /)`（**仅位置**）⇒
  `TypeError`（上游的 `VALID_KINDS` 不含 `POSITIONAL_ONLY`）。
  ⇒ 「位置参数个数」是**推测**而非上游行为 ⇒ 按推测实现会让 freegraph **比上游宽松**
  ⇒ 那是一条**未登记的偏离** ⇒ 照抄则调用形态与判别规则**逐字相同**（**P-13 = SAME**）。
  ⇒ 落点：**spec FR-003** · **裁定 12 / 裁定 16** · **SC-021** · **P-13**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **按位置参数个数判别** —— 否决：与上游**不等价**（实测 P-A02 ⇒ 上游 `TypeError`）。
  ② **第二参名字不叫 `config` 时凭位置补传** —— 否决：与上游**不等价**且更宽松。
  ③ **只支持单参** —— 否决：上游支持双参（实测 N-B）⇒ 会让迁移过来的路由函数**跑不通**。

### D-12 · 双参形态的第二参 = 用户交给 `invoke` 的**原始 `config`**（**逐字传入**）

- **Decision（决策）**：双参形态的第二参 MUST 是用户交给 `invoke` 的**原始 `config`**
  （`RunConfig` / mapping / `None` · **逐字传入**）⇒ MUST **NOT** 归一化它
  ⇒ MUST **NOT** 用 `context` 通道顶替（B8F3 的 C21 是**另一套**机制）。
- **Rationale（理由）**：上游传的是**增广后**的 `RunnableConfig`（**实测 P-B**：
  顶层 key = `['callbacks', 'configurable', 'metadata']`；`configurable` 内既含用户自己的
  `my_key`，又含上游内部的 `__pregel_runtime` 等键）⇒ **不是**用户原始 config 的逐字副本。
  ⇒ freegraph 的「原始 config」与上游的「增广 `RunnableConfig`」是**载体形态差异**
  ⇒ **非更严** ⇒ 登记 **X-5**（DIFF）⇒ 差分 **D-114** **比对形态而非内容**。
  发起者于 **2026-11-17 澄清轮 Q4** 拍板「第二参逐字传用户那份配置」。
  ⇒ 落点：**spec FR-003** · **裁定 12** · **偏离 X-5** · **SC-021**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **传上游同款的增广 `RunnableConfig`** —— 否决：会把 `RunnableConfig` 的
  `callbacks` / `metadata` / `__pregel_*` 语义搬进 freegraph ⇒ 违反宪法原则 I / X
  （零第三方依赖 · 零出站）⇒ **NOT** 引入 `langchain-core`。
  ② **用 `context` 通道（C21）承载** —— 否决：B8F3 的 C21 是**往图里注入数据**，
  与「运行期配置」是**两套**语义（澄清轮 Q4 的理由）。
  ③ **只支持单参** —— 否决：见 D-11。

### D-13 · 第二参的**注解匹配集** MUST 与上游 `KWARGS_CONFIG_KEYS` 的 `"config"` 项**同形**

- **Decision（决策）**：第二参的注解 MUST 落在**匹配集**内
  ⇒ 匹配集 = **无注解** ∨ **类对象** ∨ **字符串** ∨ `Optional[...]` / `Union[..., None]`
  ∨ 其 **PEP-604** 等价形式 ⇒ 匹配集 MUST 与上游 `KWARGS_CONFIG_KEYS` 的 `"config"` 项
  **同形**（仅载体类型不同）⇒ 注解**不在**匹配集内 ⇒ MUST **跳过注入**
  （上游同款 ⇒ `UserWarning` + 按**一参**调用 ⇒ `TypeError`）。
- **Rationale（理由）**：上游的匹配集是**精确的 5 元组**
  （`langgraph/_internal/_runnable.py:170-176`）：
  `(RunnableConfig, "RunnableConfig", Optional[RunnableConfig],`
  `"Optional[RunnableConfig]", inspect.Parameter.empty)`。
  **实测 P-A12 … P-A16 / P-A19**：类对象 `RunnableConfig` ⇒ OK；
  字符串 `"RunnableConfig"` ⇒ OK；`Optional[RunnableConfig]` ⇒ OK；
  字符串 `"Optional[RunnableConfig]"` ⇒ OK；**PEP-604** `RunnableConfig | None` ⇒ OK
  （⚠️ 成立的原因是 `Optional[RunnableConfig] == RunnableConfig | None` 为 **True**，
  实测 equality 事实）；`Optional[str]` ⇒ `UserWarning` + `TypeError`。
  ⇒ freegraph 侧把类对象槽换成 `RunConfig` / `Mapping[str, Any]`、字符串槽换成对应字符串
  ⇒ **形状逐字同款**（仅载体类型不同 ⇒ 归 **X-5**）。
  ⚠️ **该等价机制对 freegraph 的载体同样成立**（实测 equality 事实）：
  `Optional[RunConfig] == (RunConfig | None)` 为 **True**；
  `Optional[RunConfig | Mapping[str, Any]] == (RunConfig | Mapping[str, Any] | None)`
  亦为 **True** ⇒ PEP-604 槽**零成本**照抄。
  ⇒ 落点：**spec FR-003** · **裁定 16** · **偏离 X-5** · **SC-021** · 差分 **D-115**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **匹配集放宽到「任意注解」** —— 否决：那比上游**宽松** ⇒ 未登记的偏离。
  ② **匹配集收紧到「必须是类对象」** —— 否决：比上游**更严**且会让
  `Optional[...]` / PEP-604 形态的路由函数跑不通（上游**可用** · 实测 P-A14 / P-A16）。
  ③ **注解不匹配时抛错** —— 否决：上游是**跳过注入 + 警告**（不是抛错）。

### D-14 · `__start__` 上的条件边 MUST **被求值**（求值落点 = 图启动时 · 入口口径照抄上游）

- **Decision（决策）**：条件边的源节点为 `__start__`（入口哨兵）时 MUST **求值**该路由函数
  ⇒ 其结果 MUST 成为**入口目标** ⇒ MUST **NOT** 静默跳过（当前的「空跑」是**缺陷**）
  ⇒ MUST 允许「**唯一入口 = `__start__` 条件边**」（**无**静态入口点）
  ⇒ 静态入口与 `__start__` 条件边**并存**时两者的目标 MUST **同轮并行**（取**并集**）
  ⇒ `__start__` 条件边返回 `END` ⇒ 该分支 MUST **终止**。
- **Rationale（理由）**：上游的 `__start__` 是**真实伪节点**
  （`langgraph/graph/state.py:1373` `compiled.attach_node(START, None)`；
  `:1508-1514` 建 `PregelNode(triggers=[START], channels=START)`；
  分支挂到它身上 ⇒ `langgraph/graph/state.py:1624`）⇒ 挂在它上面的分支**会**被求值。
  **实测 N-A1 … N-A5**：纯条件边入口 ⇒ 节点序列 `['b']`；静态入口与条件入口并存 ⇒
  `['a', 'b']`（同轮并行）；返回 `END` ⇒ 节点序列 `[]`；非法返回值 **有** `path_map`
  ⇒ `KeyError`、**无** `path_map` ⇒ 静默忽略（warning）。
  freegraph 的 `__start__` 是**哨兵**（`src/freegraph/runtime/superstep.py:123`
  的 `_START_MARKER`）⇒ **照抄的是「求值」这件事**，而**不是**把 `__start__`
  变成会执行的节点 ⇒ 当前的「静默空跑」被标为**缺陷**（**实测 E-34**：
  freegraph 现状下条件边的目标**执行 0 次**）。
  ⇒ 落点：**spec FR-038 / FR-039** · **裁定 17** · **SC-022 / SC-023** ·
  差分 **D-116 / D-117**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **维持「静默空跑」** —— 否决：那是**缺陷**（上游**会**求值 ⇒ 可观察不等价）。
  ② **把 `__start__` 变成可执行节点** —— 否决：freegraph 的 `__start__` 是**哨兵**
  ⇒ 会引入一个「假节点」（与 B7F1 的哨兵口径冲突）。
  ③ **禁止纯条件边入口** —— 否决：上游**允许**（实测 N-A1）⇒ freegraph 的
  `_validate_entrypoint`（`src/freegraph/_stategraph.py:570-583` 的 `conditional_entry` 分支）
  **本就接受**条件入口 ⇒ **零新增**。

### D-15 · branch 名纪律照抄上游（重名 ⇒ 内置 `ValueError` · `__start__` 不特例化）

- **Decision（决策）**：同一源节点（含 `__start__`）登记多条条件边时 branch 名 MUST **唯一**
  ⇒ 重名 MUST 抛内置 **`ValueError`**（消息**点名**分支名与源节点）
  ⇒ `__start__` MUST **NOT** 特例化（与普通源节点**同款**）。
- **Rationale（理由）**：上游同款 —— `langgraph/graph/state.py:1019-1025`
  （`path = coerce_to_runnable(path, name=None, trace=True)`；
  `name = path.name or "condition"`；重名 ⇒ 内置 `ValueError`）。
  **实测 N-A5b**：在 `__start__` 上登记**两条** lambda 条件边 ⇒
  `ValueError: Branch with name \`None\` already exists for node \`__start__\``；
  **实测 N-A5a / N-A7**：两条**具名**函数（`cond1` / `cond2`）⇒ 分支名不同 ⇒ **不**冲突；
  两条 **lambda**（⇒ 同名 `condition`）⇒ 内置 `ValueError`
  （`__start__` 与普通源节点**同款**）。
  freegraph 侧**已实现**该校验（`src/freegraph/_stategraph.py:110-115` 的 `_branch_name`
  与 `:509-512` 的 `ValueError`）⇒ **零新增**。
  ⇒ 落点：**spec FR-040** · **裁定 18** · **SC-024** · **上游对照 P-21**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **`__start__` 特例化（允许重名）** —— 否决：制造第二条规则 ⇒ 与普通源节点不一致。
  ② **允许同源多条条件边共用一个 branch 名** —— 否决：与上游**不等价**
  （实测 N-A5b ⇒ 上游抛错）。

### D-16 · 条件边的**路由判定差分**落 `parity_probe.py`（**双真实实现**对跑）

- **Decision（决策）**：条件边的路由判定差分 MUST 落 `tests/differential/parity_probe.py`
  ⇒ MUST **NOT** 填值 B5F2 差分夹具的 `conditional_edges` 字段 ⇒ MUST **NOT** 重造夹具接口
  ⇒ MUST **NOT** 使 B5F2 已产出的差分证据作废 ⇒ B5F2 的 **V-4 无需放宽**。
- **Rationale（理由）**：三条实证 —— ① B5F2 的 `tests/differential/driver.py` 是**替身**
  不是调度器（其模块 docstring 明文「MUST NOT 含调度逻辑」）⇒ 给它加分支调度 =
  **在测试替身里重写一遍生产调度器** ⇒ 两个调度器必然漂移 ⇒ 测到的就不再是
  「上游 vs freegraph」；② `tests/differential/parity_probe.py` 已是「**双真实实现**对跑」
  的载体（上游 `StateGraph.compile().invoke()` vs freegraph `run_super_steps`）
  ⇒ 且**已有** `add_conditional_edges` 的既有场景（**D-29…D-32** · 上游侧
  `add_conditional_edges` + freegraph 侧 `_fg_branches`）⇒ 条件边的路由判定**属于**那里；
  ⚠️ 此处的 **D-29…D-32** 是 **B11F1 已占用的差分编号**（与本文的 **D-01…D-24** 决策编号、
  与 spec 的 **D-103…D-120** 差分编号是**三套互不相干的编号域**）；
  ③ 「不破不立」的正解（宪法原则 XII）。
  ⇒ 落点：**spec FR-032** · **裁定 14 / 裁定 15** · **SC-013** ·
  破冻结面 **T-2** 与冻结断言 **③**（本轮**取消**）。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **给 B5F2 的夹具加分支调度** —— 否决：见上①（替身 ≠ 调度器 ⇒ 漂移）。
  ② **新建一个差分载体文件** —— 否决：重造夹具接口 ⇒ 违反 FR-032。
  ③ **填值 B5F2 夹具的 `conditional_edges` 字段** —— 否决：其 freegraph 侧驱动器
  是**线性替身** ⇒ **填值无消费者** ⇒ 违反 FR-032 的 MUST NOT。

### D-17 · **V-8** 的**放宽**（移除构造期守卫 · 走「登记 + 回溯修订 + 发起者追认」**一次**）

- **Decision（决策）**：MUST **放宽** B7F1 的校验规则 **V-8**
  （`GraphSpec.conditional_edges` 非空 ⇒ 内置 `ValueError`）
  ⇒ 构造期**不再**因该字段非空而失败 ⇒ 放宽 MUST 走「**登记 + 回溯修订 +
  发起者追认**」**一次**（追认次数 == **1**）⇒ MUST **NOT** 再破任何其它冻结面。
- **Rationale（理由）**：B7F1 已**预留**该字段（名字逐字冻结 ·
  `src/freegraph/runtime/superstep.py:219` 的 `conditional_edges`）
  ⇒ B8F1 **只需填值**即可复用 ⇒ MUST NOT 改造 B7F1 的调度内核。
  守卫本体在 `src/freegraph/runtime/superstep.py:484-487`
  （`raise ValueError("GraphSpec.conditional_edges must stay empty in this feature (V-8)")`）
  ⇒ 破面**只**放宽「该字段非空是否构造期失败」这一条**构造期守卫**
  ⇒ **零条既有判据被删**（其余 **V-1…V-3** 等逐字不动）⇒ 判据**只收紧不放宽**。
  ⇒ 落点：**spec FR-026** · **裁定 14** · **破冻结面 T-1** · **SC-016**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **不改 V-8** —— 否决：字段非空即失败 ⇒ 条件边**无法**被承载 ⇒ 本 feature 无从落地。
  ② **新增第二个字段承载条件边** —— 否决：制造第二套来源 ⇒ 破 B7F1 的**预留面**。
  ③ **把 V-8 改成 warning** —— 否决：判据**放宽**（构造期不再失败）⇒ 与
  「破冻结面须追认」的要求相悖 ⇒ 走**正规放宽**流程。

### D-18 · 路由函数**自身**抛出的异常 MUST **原类型 + 原消息**传播

- **Decision（决策）**：路由函数自身抛出的异常 MUST 以**原始类型与原始消息**传播
  ⇒ MUST **NOT** 包装 ⇒ MUST **NOT** 吞掉 ⇒ MUST **NOT** 返回部分结果。
- **Rationale（理由）**：上游同款 —— **实测 E-12**：路由函数抛 `RuntimeError("boom")`
  ⇒ 调用方收到**原始类型 + 原始消息**（上游不包装）。
  ⇒ 落点：**spec FR-023** · **裁定 11** · **SC-012** · 差分 **D-112**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **包装成 freegraph 自有异常** —— 否决：违反「类型逐字同款」且丢失用户诊断信息。
  ② **吞掉并按「无目标」处理** —— 否决：会把**拼错**的路由函数伪装成正常空跑。

### D-19 · 路由返回值的**形态**判定（标量 / `list` / `tuple` / 其它可哈希值）

- **Decision（决策）**：返回值形态判定 MUST 为：
  ① `Send` ⇒ fan-out 载荷；② `list` / `tuple` ⇒ **多目标**；
  ③ 其它**可哈希**值 ⇒ 作为 `path_map` 的 **key** 正常查表（**不**先做类型收窄）；
  ④ `set` 等**非** `list`/`tuple` 容器 ⇒ **不是**多目标（按**单个**值处理）。
- **Rationale（理由）**：上游同款 —— `langgraph/graph/_branch.py:199-200`
  （**只有** `list` / `tuple` 被包成多目标）⇒ **实测 E-30**（`int` 键正常查表）
  · **E-31 / E-15b**（`tuple` 返回 ⇒ **多目标** ⇒ 逐元素查表 ⇒ **不是**单个 key）
  · **E-32 / E-15c**（`list` 内含 `tuple` ⇒ 该 `tuple` 元素**按单个 key** 查表 ⇒ 成功）
  · **E-27 / Q-5**（`set` 返回 + 有 `path_map` ⇒ `TypeError: unhashable type: 'set'`；
  无 `path_map` ⇒ 静默忽略）。
  ⇒ 落点：**spec FR-020 / FR-024** · **裁定 6 / 裁定 9** · **SC-005 / SC-006**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **把 `tuple` 当作单个 key** —— 否决：与上游**不等价**（实测 E-31）⇒ 且与 FR-024 矛盾。
  ② **把所有 `Sequence` 都当多目标** —— 否决：`str` 是 `Sequence` ⇒ 会把
  `"a"` 拆成字符 ⇒ 与上游**不等价**（上游只认 `list` / `tuple`）。
  ③ **先做 `str` 类型收窄** —— 否决：违反 FR-020（**不**先做类型收窄）。

### D-20 · 条件边目标与同轮 `Command.goto` 目标取**并集**（去重保序）

- **Decision（决策）**：条件边目标 MUST 与该节点**同轮**的 `Command.goto` 目标取**并集**
  （去重保序）⇒ 顺序**不可观察**（同轮执行顺序 = **节点名序**）。
- **Rationale（理由）**：两条来源**互不排斥** ⇒ 都投递才是**逐字同款**的合流点；
  `Command.goto` 的写入**归源节点名下**（B9F1 · 裁定 16）⇒ fresh 读**读得到**
  `Command` 的写入 ⇒ 条件边的求值与 `Command.goto` 的合流**同轮**发生。
  ⇒ 落点：**spec FR-008 / FR-009 / FR-031** · **裁定 13** · **SC-012**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **条件边目标覆盖 `Command.goto` 目标** —— 否决：会**丢**一条来源 ⇒ 可观察不等价。
  ② **`Command.goto` 覆盖条件边目标** —— 否决：同上。
  ③ **两条来源分轮投递** —— 否决：会改变**轮次**语义 ⇒ 与 B7F1 的 super-step 口径冲突。

### D-21 · 路由通道 MUST **不**出现在 `invoke` 的返回键集里

- **Decision（决策）**：路由通道 MUST **不**出现在 `invoke` 的返回键集里
  ⇒ 判定 MUST 沿用 **B7F1 的冻结口径**（`isinstance(channel, EphemeralValue)`）
  ⇒ MUST **NOT** 用名称前缀启发式。
- **Rationale（理由）**：上游同款 —— 上游的 `branch:to:*` 建在 `self.channels` 而非 schema
  （`langgraph/graph/state.py:1524-1530`）⇒ **不在** output schema。
  freegraph 侧 `_full_state`（`src/freegraph/_stategraph.py:252-259`）已排除
  `EphemeralValue` ⇒ **零新增**。⇒ 落点：**spec FR-029** · **裁定 3** · **SC-002 / SC-010**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **用 `branch:to:` 前缀排除** —— 否决：违反 FR-029 的「非启发式」。
  ② **让路由通道进返回键集** —— 否决：与上游**不等价**且污染 C4 的「完整状态」口径。

### D-22 · 路由函数**内部**的 `interrupt()` ⇒ 归 **B10F1**（本 feature **不**判失败）

- **Decision（决策）**：路由函数内部调用 `interrupt()` 时，本 feature MUST **NOT** 把它当作
  「路由失败」⇒ 中断语义的判定 MUST 沿用 **B10F1** 的既有口径 ⇒ 本 feature **零新增**。
- **Rationale（理由）**：**实测 E-25**：上游的路由函数内 `interrupt()` ⇒ 图返回
  `{'__interrupt__': [Interrupt(value=..., id=...)]}` ⇒ **不抛异常**、目标节点**不执行**。
  **实测 E-24**（对照）：**节点**挂起时路由函数**不被求值**（`router called = 0`）
  ⇒ 与承接条款 **H-10** 一致（中断路径与路由路径**互斥**）。
  ⇒ 落点：**spec FR-003 / FR-018** · 承接 **H-10** · **SC-012**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **把 `__interrupt__` 当作非法返回值报错** —— 否决：会把**上游可用**的路径变成失败。
  ② **本 feature 实现中断恢复** —— 否决：属 **B10F1**（FR-036）。

### D-23 · `path_map=None` + 返回注解 `Literal[...]` ⇒ **L3 已实现**（L2 **零**新增）

- **Decision（决策）**：`path_map` 为 `None` 且路由函数的**返回注解**是 `Literal[...]` 时
  ⇒ `path_map` 的推断 MUST 在 **L3（构建期）**完成 ⇒ L2 **零**推断、**零**归一化。
- **Rationale（理由）**：上游同款 —— `langgraph/graph/_branch.py:102-114`
  （`get_type_hints(func).get("return")` ⇒ `get_origin(rtn_type) is Literal`
  ⇒ `path_map_ = {name: name for name in get_args(rtn_type)}`）。
  **实测 E-33**：上游在 `path_map=None` + `-> Literal["a"]` 时**推断**出 `path_map`
  ⇒ 路由返回 `"zz"` ⇒ **`KeyError('zz')`**（**不是**「无 `path_map`」的静默忽略）
  ⇒ 证明推断生效。freegraph 侧**已实现**（`src/freegraph/_stategraph.py:145-159` 的
  `get_type_hints` + `get_origin(...) is Literal` 分支）⇒ **零新增**。
  ⇒ 落点：**spec FR-014 / FR-016** · **裁定 4** · **上游对照 P-02**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **L2 侧再推断一次** —— 否决：违反裁定 4（零归一化）。
  ② **freegraph 不支持 `Literal` 推断** —— 否决：与上游**不等价**（实测 E-33 的
  `KeyError` vs 静默忽略是可观察差异）⇒ 且 L3 **已实现** ⇒ 零成本。

### D-24 · 条件边的**目标集合**与「屏障组」**不混用**

- **Decision（决策）**：路由求值 MUST **NOT** 受屏障组的「所有源齐备」判定影响
  ⇒ 条件边的目标由**路由函数**决定 ⇒ MUST **NOT** 把「多源边」当作「条件边」求值。
- **Rationale（理由）**：两套**语义相异** —— 屏障组的目标由**多源边的全部源齐备**决定，
  条件边的目标由**路由函数**决定（B7F4 的下游承接 **D-3** · 登记项 **PR-4**）
  ⇒ 混用会让「路由已返回目标但屏障未齐备」的场景**少跑**一条分支。
  ⇒ 落点：**spec FR-004 / FR-006** · **裁定 1** · **SC-009**。
- **Alternatives considered（评估过但未采纳的备选）**：
  ① **让条件边目标也等屏障齐备** —— 否决：与上游**不等价**（上游的分支是源节点的
  writer ⇒ 只等**源节点自己**落回）。
  ② **把多源边的目标也走路由求值** —— 否决：语义相异 ⇒ 会把「静态多源」变成「动态」。

---

## §2 实测基线表（E-n / M-x / N-x / P-x）

> **编号说明**：本表沿用 spec **已引用**的编号（**E-1…E-16** / **M-B…M-F** / **N-A / N-B**）
> ⇒ 本轮**新增**者自 **E-17** 起续号 ⇒ 新增的 **N-x / P-x** 亦在 **N-A / N-B** 之后续号。
> **判词**列 = 该语义点上 freegraph **目标**口径与上游的**关系**
> （**SAME / DIFF / STRICTER**）⇒ 与 spec 的偏离登记 **X-1…X-7** 逐字对齐。

### 2.1 路由求值 · `path_map` · `END`（**E-n**）

| 编号 | 场景 | 上游观察（实测） | freegraph 期望 | 判词 | 差分场景 |
|---|---|---|---|---|---|
| **E-1** | **list 形态** `path_map`（`["a", END]`）· 路由返回 `"a"` | 正常路由 ⇒ 输出 `{'messages': ['x'], 'llm_calls': 1}` | list ⇒ L3 归一化为 `{name: name}` ⇒ 路由到 `"a"` | SAME | **D-103** |
| **E-2** | **dict 形态** `path_map`（`{"hit": "a", "miss": "b"}`）· 路由返回 `"hit"` | 正常路由 ⇒ 节点 `a` 执行 · `b` 未执行 | 同款 | SAME | **D-104** |
| **E-18** | 上游在**构建期**完成 `path_map` 归一化（观测 `compiled.builder.branches`） | list 形态 ⇒ `ends = {'a': 'a', 'b': 'b'}`（已归一化的 dict）· dict 形态 ⇒ `ends = {'hit': 'a', 'miss': 'b'}` · `None`（无 `Literal` 注解）⇒ `ends = None` ⇒ 且分支名 = 函数的 `__name__`（`r_list` / `r_dict` / `r_none`） | L3 归一化（`_normalize_path_map`）⇒ L2 **零**归一化 | SAME | **D-103 / D-104** |
| **E-3** | `path_map` 含 `END` **键**且映射到普通节点（`{END: "a"}`）· 路由返回 `END` | **不终止** ⇒ 节点 `a` **执行 1 次** | **单独返回** `END` ⇒ **无条件终止**（不路由到 `a`） | **DIFF**（X-2） | **D-118** |
| **E-3b** | `path_map = {END: END}` · 路由返回 `END` | **终止** ⇒ 目标节点执行 **0** 次 | 同款 | SAME | **D-106** |
| **E-4** | `path_map` 的 **value** 是 `END`（`{"stop": END}`）· 路由返回 `"stop"` | **终止** ⇒ 目标节点执行 **0** 次 | 同款 | SAME | **D-106** |
| **E-5** | `path_map` **不含** `END` 键（`{"go": "a"}`）· 路由返回 `END` | **抛 `KeyError: '__end__'`**（查表先于 `END` 剔除） | **单独返回** `END` ⇒ **无条件终止**（不抛错） | **DIFF**（X-2） | **D-110** |
| **E-6** | **有** `path_map` · 路由返回表外的 `"nope"` | **抛 `KeyError('nope')`**（消息只有 key 本身） | 同型 `KeyError` + 消息指明返回值与可选目标 | **STRICTER**（X-1） | **D-107** |
| **E-7** | **有** `path_map` · 路由返回表外的 `"other"` | **抛 `KeyError('other')`** | 同上 | **STRICTER**（X-1） | **D-107** |
| **E-8** | **无** `path_map` · 路由返回**未注册**节点名 `"ghost"` | **静默忽略** ⇒ 只打一条 warning（`Task r with path ('__pregel_pull', 'r') wrote to unknown channel branch:to:ghost, ignoring it.`）· 图**成功**结束 | **显式失败**（内置 `ValueError`） | **STRICTER**（X-3） | **D-111** |
| **E-9 / E-9b** | 路由返回序列 `["b", "c"]` | 两个目标**同轮**执行 · 各自收到**逐字相等**的入参（共享状态） | 同款（动态边投递 · 共享状态） | SAME | **D-108** |
| **E-10** | **fresh 读**：源节点写 `{"messages": ["fresh"], "llm_calls": 7}` 后路由 | 路由函数看到 **`{'messages': ['fresh'], 'llm_calls': 7}`** · key 集合 = `['llm_calls', 'messages']`（**全部 schema 通道**） | 同款（覆盖整张通道表） | SAME | **D-105** |
| **E-11** | 路由返回 `Send("a", payload)` | 目标节点收到**载荷** `{'llm_calls': 99}`（**不是**共享状态） | 复用 B11F1 的 fan-out 构造器 | SAME | **D-108**（对照） |
| **E-12** | 路由函数**自身**抛 `RuntimeError("boom")` | **原样传播**（原始类型 + 原始消息） | 同款 | SAME | **D-112** |
| **E-13** | 路由返回 `[END, "a"]` | 节点 `a` **执行 1 次**（`END` 被剔除）· **不**终止整张图 | 同款（`END` 剔除 · 其余照常） | SAME | **D-106**（对照） |
| **E-14 / E-30** | 路由返回**非 `str` 的可哈希值** `42` · `path_map = {42: "a"}` | 正常查表 ⇒ 节点 `a` 执行 | 同款（**不**先做类型收窄） | SAME | **D-104**（对照） |
| **E-15 / E-31** | 路由返回 **`tuple`** `("x", "y")` | **被当作多目标** ⇒ 逐元素查表 ⇒ `KeyError('x')`（**不是**单个 key） | 同款（`tuple` ⇒ 多目标） | SAME | **D-108**（对照） |
| **E-15b** | 路由返回 `("x", "y")` · `path_map = {"x": "a", "y": "b"}` | **多目标** ⇒ `a` 与 `b` **同轮**执行 | 同款 | SAME | **D-108** |
| **E-15c / E-32** | 路由返回 `[("x", "y")]`（list 内含 tuple）· `path_map = {("x","y"): "a"}` | 该 `tuple` 元素**按单个 key** 查表 ⇒ 成功 | 同款 | SAME | **D-104**（对照） |
| **E-16** | **归约型**通道（初始 `["seed"]` · 写入 `["n1"]`）后路由 | 路由函数看到 **`['seed', 'n1']`**（归约器**已**在 fresh 读里生效） | 同款（复用通道自身的写入规则） | SAME | **D-105** |
| **E-17** | `path_map = {END: "a"}` · 路由返回 `END` | **不终止** ⇒ `a` 执行 **1** 次 | **单独返回** `END` ⇒ **无条件终止**（不路由到 `a`） | **DIFF**（X-2） | **D-118** |
| **E-19 / Q-7** | **无** `path_map` · 路由返回 `END` | **正常终止**（不抛错）⇒ 目标节点执行 **0** 次 | 同款（判定与「有无 `path_map`」正交） | SAME | **D-106** |
| **E-20** | `path_map = {"go": "a"}` · 路由返回 `END` | **抛 `KeyError: '__end__'`** | **单独返回** `END` ⇒ **无条件终止** | **DIFF**（X-2） | **D-110** |
| **E-35** | `path_map = {END: "b"}` · 路由返回 `END` | **解析后目的地 == "b"** ⇒ 节点 `b` **执行 1 次** ⇒ **不终止**（实测） | **单独返回** `END` ⇒ **无条件终止**（不路由到 `b`） | **DIFF**（X-2） | **D-118** |
| **E-21** | 路由返回 `Send(END, ...)` | **抛 `InvalidUpdateError('Cannot send a packet to the END node')`** | 复用 B11F1 的 `validate_send`（V-21 · `ValueError`）⇒ **类型不同** | **DIFF**（**DR-6**） | —— |
| **E-22** | 路由返回 `Send("ghost", ...)`（未注册节点） | **静默忽略**（不抛错） | B11F1 的 V-19 ⇒ `ValueError` 显式失败 | **STRICTER**（**DR-6**） | —— |
| **E-23** | 路由返回 `[Send("a", payload), "b"]` | 两者**并行**投递：`a` 收到**载荷** `{'llm_calls': 5}` · `b` 收到**共享状态** `{}` | 同款（各自语义） | SAME | **D-108**（对照） |
| **E-24** | **节点**挂起（`interrupt()`）后路由 | 路由函数**未被求值**（`router called = 0`）⇒ 中断路径与路由路径**互斥** | 同款（节点不成功落回 ⇒ 不求值） | SAME | —— |
| **E-25** | 路由函数**内部** `interrupt()` | 图返回 `{'__interrupt__': [Interrupt(value=..., id=...)]}` ⇒ **不抛异常**、目标**不执行** | 归 B10F1 · 本 feature 零新增 | SAME | —— |
| **E-26 / Q-2** | 路由返回 `["a", "a"]`（序列含**重复**目标） | 目标节点**只执行 1 次**（去重） | 去重保序 | SAME | **D-108**（对照） |
| **E-27 / Q-4** | 路由返回 `{"a"}`（**`set`**）· **无** `path_map` | **不**被当作多目标 ⇒ 目标名 `"{'a'}"` 不存在 ⇒ **静默忽略** | 同款（只有 `list`/`tuple` 是多目标） | SAME | —— |
| **E-27 / Q-5** | 路由返回 `{"a"}`（`set`）· **有** `path_map` | **抛 `TypeError: unhashable type: 'set'`** | 同款 | SAME | —— |
| **E-28** | 条件边的**源节点未注册**（`"ghost"`） | **编译期** `ValueError: Found edge starting at unknown node 'ghost'` | L3 已有同款校验 | SAME | —— |
| **E-29** | 同源**两条**条件边（不同 branch 名） | 两条路由函数**各求值一次**（顺序 = 登记顺序）⇒ 目标**并集** | 同款 | SAME | —— |
| **E-33 / P-C** | `path_map=None` + 返回注解 `-> Literal["a"]` · 路由返回 `"zz"` | 上游**推断**出 `path_map` ⇒ **抛 `KeyError('zz')`** | L3 已实现同款推断 | SAME | —— |
| **E-34** | **freegraph 现状**（本 feature 落地前）：普通源节点 / `__start__` 上的条件边 | —— | 目标节点**执行 0 次** ⇒ **静默空跑**（**缺陷**） | ——（待修） | **D-116 / D-117** |

### 2.2 失败信号矩阵（**M-x**）

| 编号 | 场景 | 上游观察（实测） | freegraph 期望 | 判词 | 差分场景 |
|---|---|---|---|---|---|
| **M-A** | 路由返回**空序列** `[]`（**无** `path_map`） | **不报错** ⇒ 无目标 ⇒ 图结束 | 同款（空序列**不是**非法返回值） | SAME | —— |
| **M-A2** | 路由返回**空序列** `[]`（**有** `path_map`） | **不报错** ⇒ 无目标 | 同款 | SAME | —— |
| **M-B** | 路由返回 `None` · **无** `path_map` | **抛 `ValueError('Branch did not return a valid destination')`** | 同型 `ValueError` + 消息更详细 | **STRICTER**（X-1） | **D-113** |
| **M-C** | 路由返回 `None` · **有** `path_map` | **抛 `KeyError(None)`** | 同型 `KeyError` + 消息更详细 | **STRICTER**（X-1） | **D-107** |
| **M-D** | 路由返回 `START`（`'__start__'`）· **无** `path_map` | **抛 `ValueError('Branch did not return a valid destination')`** | 同型 `ValueError` | **STRICTER**（X-1） | **D-113** |
| **M-E** | 路由返回 `START` · **有** `path_map` | **抛 `KeyError('__start__')`** | 同型 `KeyError` | **STRICTER**（X-1） | **D-107** |
| **M-F** | 路由返回 `["a", "zz"]` · `path_map = {"a": "a"}` | **抛 `KeyError('zz')`**（失败在**元素**层）⇒ 证明 `list` 是**多目标**而非「不可哈希的 key」 | 同款 | SAME | **D-107** |
| **M-G** | 路由返回 `("a", "b")`（`tuple`） | **多目标** ⇒ 两目标同轮执行 | 同款 | SAME | **D-108** |
| **M-H** | 路由返回 `{"a"}`（`set`）· **有** `path_map` | **抛 `TypeError: unhashable type: 'set'`** | 同款 | SAME | —— |
| **M-I** | 路由返回 `["ghost"]` · **无** `path_map` | 逐元素当节点名 ⇒ `ghost` 不存在 ⇒ **静默忽略** | **显式失败** | **STRICTER**（X-3） | **D-111** |
| **M-J** | `path_map` 的 **value** 是 `END` · 路由返回该 key | **终止**（不抛错） | 同款 | SAME | **D-106** |

### 2.3 `__start__` 条件边（**N-x**）

| 编号 | 场景 | 上游观察（实测） | freegraph 期望 | 判词 | 差分场景 |
|---|---|---|---|---|---|
| **N-A1** | **纯条件边入口**（`__start__` 上有条件边 · **无**静态入口点）· 路由返回 `"b"` | **允许** ⇒ 节点序列 = **`['b']`**（从路由结果起步） | 同款（`__start__` 是哨兵但路由**会被求值**） | SAME | **D-117** |
| **N-A2** | **静态入口 + `__start__` 条件边并存** | 两个目标**同轮并行** ⇒ 节点序列 = **`['a', 'b']`** | 同款（取并集） | SAME | **D-116** |
| **N-A3** | `__start__` 条件边返回 `END`（**有** `path_map`） | 该分支**终止** ⇒ 节点序列 = **`[]`** | 同款 | SAME | **D-116** |
| **N-A3b** | `__start__` 条件边返回 `END`（**无** `path_map`） | **终止** ⇒ 节点序列 = `[]` | 同款 | SAME | **D-116** |
| **N-A4a** | `__start__` 条件边返回非法值 + **有** `path_map` | **抛 `KeyError('ghost')`** | 同款 | SAME | **D-116** |
| **N-A4b** | `__start__` 条件边返回非法值 + **无** `path_map` | **静默忽略**（warning） | **显式失败** | **STRICTER**（X-3） | **D-111** |
| **N-A5a** | `__start__` 上登记**两条**条件边（**具名**函数 `cond1` / `cond2`） | **不报错**（分支名不同） | 同款 | SAME | —— |
| **N-A5b** | `__start__` 上登记**两条**条件边（**两条 lambda** ⇒ 同名 `condition`） | **抛 `ValueError: Branch with name \`None\` already exists for node \`__start__\``** | 同款（`_branch_name` + 重名 `ValueError`） | SAME | —— |
| **N-A6** | `__start__` 上两条**不同名**条件边 | 目标**并集** ⇒ 节点序列 = `['b', 'c']` | 同款 | SAME | **D-116** |
| **N-A7** | **普通**源节点 `r` 上登记**两条** lambda 条件边（⇒ 同名 `condition`） | **抛 `ValueError: Branch with name \`None\` already exists for node \`r\`**` | 同款（`_branch_name` + 重名 `ValueError`） | SAME | —— |
| **N-A8** | 上游的 `__start__` 是否为**真实伪节点** | `compiled.builder.nodes` **不含** `__start__`，但 `attach_node(START, None)`（`state.py:1373`）建了 `PregelNode(triggers=[START])`（`:1508-1514`）⇒ **是**真实伪节点 | freegraph 的 `__start__` 是**哨兵** ⇒ 只照抄「求值」这件事 | SAME（语义层） | —— |
| **N-B** | **双参**路由函数 `f(state, config)` | **调用成功** ⇒ 第二参是 **`dict`** | 同款（第二参 = 用户原始 `config`） | **DIFF**（X-5 · 内容） | **D-114** |

### 2.4 双参判别矩阵（**P-x**）

| 编号 | 路由函数形态 | 上游观察（实测） | freegraph 期望 | 判词 | 差分场景 |
|---|---|---|---|---|---|
| **P-A01** | `f(state)` | OK（按**一参**调用） | 同款 | SAME | **D-114** |
| **P-A02** | `f(state, cfg)`（第二参**不叫** `config`） | **抛 `TypeError`**（`missing 1 required positional argument: 'cfg'`） | 同款（**不**凭位置补传） | SAME | **D-115** |
| **P-A03** | `f(state, config)`（**无注解**） | OK ⇒ `config` 是 **`dict`** | 同款 | SAME | **D-114** |
| **P-A04** | `f(state, config: dict)` | **`UserWarning`** + **抛 `TypeError`**（跳过注入 ⇒ 按一参调用） | 同款（注解不在匹配集 ⇒ 跳过注入 + 警告） | SAME | **D-115** |
| **P-A05** | `f(state, config: int)` | **`UserWarning`** + **抛 `TypeError`** | 同款 | SAME | **D-115** |
| **P-A06** | `f(state, *, config)`（keyword-only） | OK ⇒ `config` 是 **`dict`** | 同款（**关键字**注入） | SAME | **D-114** |
| **P-A07** | `f(state, **kwargs)` | OK ⇒ **kwargs 为空** `{}`（**不注入**） | 同款 | SAME | **D-115** |
| **P-A08** | `f(state, *args)` | OK ⇒ `args == ()`（按**一参**调用） | 同款 | SAME | **D-115** |
| **P-A09** | `f()` | **抛 `TypeError`** | 同款 | SAME | —— |
| **P-A10** | `f(a, b, c)` | **抛 `TypeError`** | 同款 | SAME | —— |
| **P-A11** | 可调用对象 `__call__(self, state, config)` | OK ⇒ `config` 是 **`dict`** | 同款 | SAME | **D-114** |
| **P-A12** | `f(state, config: RunnableConfig)`（类对象） | OK | 同款（匹配集：类对象） | SAME | **D-114** |
| **P-A13** | `f(state, config: "RunnableConfig")`（**字符串**） | OK | 同款（匹配集：字符串） | SAME | **D-114** |
| **P-A14** | `f(state, config: Optional[RunnableConfig])` | OK | 同款（匹配集：`Optional`） | SAME | **D-114** |
| **P-A15** | `f(state, config: "Optional[RunnableConfig]")`（**字符串**） | OK | 同款（匹配集：字符串 `Optional[...]`） | SAME | **D-114** |
| **P-A16** | `f(state, config: RunnableConfig \| None)`（**PEP-604**） | OK ⇒ ⚠️ 成立原因是 `Optional[RunnableConfig] == RunnableConfig \| None` 为 **True** | 同款（匹配集：PEP-604 等价形式） | SAME | **D-114** |
| **P-A17** | `f(state, config: "RunnableConfig \| None")`（**字符串**形式） | **`UserWarning`** + **抛 `TypeError`** ⇒ ⚠️ **字符串**形式**不**在匹配集内 | 同款（匹配集只含**两个**字面量字符串） | SAME | **D-115** |
| **P-A18** | `f(state, config, /)`（**仅位置**） | **抛 `TypeError`** ⇒ 上游的 `VALID_KINDS` **不含** `POSITIONAL_ONLY` | 同款 | SAME | **D-115** |
| **P-A19** | `f(state, config: Optional[str])` | **`UserWarning`** + **抛 `TypeError`** | 同款（`Optional[str]` **不**在匹配集内） | SAME | **D-115** |
| **P-B** | 双参第二参的**内容** | 顶层 key = `['callbacks', 'configurable', 'metadata']` 的 **dict**；`configurable` 内含用户自己的 `my_key` **与**上游内部的 `__pregel_runtime` 等键 ⇒ 是**增广**后的 `RunnableConfig` | 传用户交给 `invoke` 的**原始 `config`**（**逐字**） | **DIFF**（X-5） | **D-114**（比对**形态**） |
| **P-C** | 上游的**注解匹配集**（精确） | `(RunnableConfig, "RunnableConfig", Optional[RunnableConfig], "Optional[RunnableConfig]", inspect.Parameter.empty)` —— `langgraph/_internal/_runnable.py:170-176` | **同形**（类对象 / 字符串 / `Optional` / PEP-604 / 空）⇒ 仅载体类型不同 | SAME（形状） | **D-115** |
| **P-D** | `RunnableCallable` 的**判别位置** | 判别在 `RunnableCallable.__init__`（`langgraph/_internal/_runnable.py:299` · `:341-365`）⇒ 按**参数名**查 ⇒ **关键字**注入 ⇒ **永远只传一个位置实参** | 同款 | SAME | **D-115** |
| **P-E** | 上游 `local_read` 的**签名** | `(scratchpad, channels, managed, task, select, fresh=False)` ⇒ **六个**入参（含 freegraph **不实现**的 `managed`） | `local_read(channels, writes, *, fresh=False)`（B5F2 的**自有**形状）⇒ **只对齐语义**，**不对齐签名** | DIFF（形状 · **DR-1**） | —— |

### 2.5 差分场景索引（**D-103 … D-120** · **18** 条 · 逐条落点）

| 差分编号 | 场景 | 覆盖的实测编号 | 判词 | 备注 |
|---|---|---|---|---|
| **D-103** | **list 形态** `path_map` · 路由返回 `"a"` | E-1 / E-18 | SAME | —— |
| **D-104** | **dict 形态** `path_map` · 路由返回 `"hit"` | E-2 / E-14 / E-15c / E-18 | SAME | —— |
| **D-105** | **fresh 读**：源节点写 `{"messages": ["fresh"], "llm_calls": 7}` 后路由 | E-10 / E-16 | SAME | **否定式断言** |
| **D-106** | 路由返回 `END`（`path_map` = **`{END: END}`** · 即 `END` 映射到 `END`） | E-3b / E-4 / E-13 / E-19 / M-J | SAME | —— |
| **D-107** | 路由返回**非法值**（不在 `path_map` 内） | E-6 / E-7 / M-C / M-E / M-F | SAME（**类型**相同） | 消息**不**逐字比对 |
| **D-108** | 路由返回**序列**（`["b", "c"]`） | E-9 / E-9b / E-11 / E-23 / E-26 / M-G | SAME | 两个目标**同轮** · 入参**逐字相等** |
| **D-109** | **无** `path_map` 的**动态目标**（返回**已注册**节点名） | E-8（对照组） | SAME | —— |
| **D-110** | 路由返回 `END` 而 `path_map` **不含** `END` 键 | E-5 / E-20 | **DIFF**（X-2） | 失败与否**不等** |
| **D-111** | **无** `path_map` 且返回**未注册**节点名 | E-8 / M-I / N-A4b | **STRICTER**（X-3） | ⚠️ MUST 带 `note` |
| **D-112** | 路由函数**抛异常** | E-12 | SAME | 类型与消息**逐字一致** |
| **D-113** | **无** `path_map` 且路由返回 `None` / `START` | M-B / M-D | SAME（**类型**相同） | 消息**不**逐字比对 |
| **D-114** | **双参**形态的路由函数 `f(state, config)` | N-B / P-A01 / P-A03 / P-A06 / P-A11 / P-A12 … P-A16 / P-B | **DIFF**（X-5） | 比对**形态**而非**内容** |
| **D-115** | **双参**形态的**判别规则**（第二参名字**不叫** `config`） | P-A02 / P-A04 / P-A05 / P-A07 / P-A08 / P-A17 / P-A18 / P-A19 / P-C / P-D | SAME | —— |
| **D-116** | **条件边挂在 `__start__` 上** | N-A2 / N-A3 / N-A3b / N-A4a / N-A6 | SAME | —— |
| **D-117** | **纯条件边入口**（**无**静态入口点） | N-A1 | SAME | —— |
| **D-118** | 路由返回 `END` 而 `path_map` 把 `END` 映射到**别的节点**（`{END: "b"}`） | E-3 / E-17 / E-35 | **DIFF**（X-2） | 终止与否**不等** |

> **判词分布**（与 spec 的 SC-013 逐字一致）：**SAME 12**（D-103 / D-104 / D-105 / D-106 /
> D-107 / D-108 / D-109 / D-112 / D-113 / D-115 / D-116 / D-117）·
> **DIFF 3**（D-110 / D-114 / **D-118**）· **STRICTER 1**（D-111 · ⚠️ MUST 带 `note`）。

---

## §3 遗留登记（DR-1 … DR-14 · **只登记 · 不改判据**）

> 本节登记「**上游有、而 freegraph 不实现**」的语义面 ⇒ **只登记** ⇒ **不改任何判据**
> ⇒ **不构成**偏离（偏离登记只收 **X-1…X-7** 七条 · 见 spec 的「偏离登记」表）。

| # | 遗留项 | 上游锚点 | 为何**不属**本 feature | 归属 feature | 触发重新评估的信号 |
|---|---|---|---|---|---|
| **DR-1** | 上游 `local_read` 的 **`managed` 值**语义（第四类入参 · `ManagedValueMapping`） | `langgraph/pregel/_algo.py:188-201`（六参签名）· `:206-209` | freegraph 的 `local_read`（`src/freegraph/runtime/read.py:163-197`）是 **B5F2 的自有形状** ⇒ **不实现** `managed` ⇒ 本 feature **只对齐 `fresh` 语义**（D-02）⇒ **不得**假设 `managed` 存在 | **B5F2**（既有 **DR-3** 的延续）· 若将来需要 managed 值语义 ⇒ 另立 feature | 出现「路由函数需要读**运行期**（非状态）值」的用例 |
| **DR-2** | 上游的 **`Runnable` 载体**（`path` 可以是 `RunnableLambda` / `RunnableCallable` / `RunnableParallel`） | `langgraph/graph/state.py:1019`（`coerce_to_runnable`）· `langgraph/_internal/_runnable.py:550-581` | freegraph 的 `add_conditional_edges` 只接受 **`callable`**（`src/freegraph/_stategraph.py:503-505`）⇒ **不实现** Runnable 载体 ⇒ 连带地，**分支名**取自 `__name__` 而非 `Runnable.name`（见 **DR-5**） | **B6F1**（构建器面） | 出现「用户想传一个已封装的 `Runnable` 作为路由函数」的用例 |
| **DR-3** | 上游的 **callbacks / tracing**（`RunnableConfig` 的 `callbacks` / `metadata` / `tags` / `run_id`） | `langgraph/_internal/_runnable.py:404-420`（`kw_value = config`）· **实测 P-B** | 宪法原则 I（零出站 · 零第三方依赖）+ 原则 X ⇒ freegraph **不引入** `langchain-core` 的追踪栈 ⇒ 本 feature 只传**用户原始 `config`**（D-12） | **无**（红线 · 不实现）· 若将来 ⇒ 另立 feature | 出现「需要把 callback 注入路由函数」的用例 |
| **DR-4** | 上游的 **`stream_writer` 注入**（`KWARGS_CONFIG_KEYS` 的 `"writer"` 项） | `langgraph/_internal/_runnable.py:183-188` | 上游把 `stream_writer` 作为**第二个**可注入关键字 ⇒ freegraph **不实现**（本 feature 只交付**同步** `invoke` 路径） | **B8F2**（`stream()`） | B8F2 落地时 |
| **DR-5** | 上游的 **`store` 注入**（`KWARGS_CONFIG_KEYS` 的 `"store"` 项） | `langgraph/_internal/_runnable.py:189-195` | 上游把 `BaseStore` 注入运行期载体 ⇒ freegraph **不实现**持久化载体（checkpoint 属 B14F1 · store 属更远） | **B14F1**（checkpoint）· store 另立 | 出现「路由函数需要读 store」的用例 |
| **DR-6** | 上游对 **`Send` 的两个失败信号**与 freegraph **不同型** | 上游：`Send`→`END` ⇒ `InvalidUpdateError`（`langgraph/graph/_branch.py:209-210` · **实测 E-21**）· `Send`→未注册节点 ⇒ **静默忽略**（**实测 E-22**）<br>freegraph：B11F1 的 `validate_send`（`src/freegraph/runtime/_fanout.py:56-82`）⇒ `Send`→哨兵 ⇒ `ValueError`（V-21）· `Send`→未注册节点 ⇒ `ValueError`（V-19） | 两者的**校验规则**属 **B11F1 的冻结面** ⇒ 本 feature **只复用**构造器（D-08）⇒ MUST **NOT** 改 B11F1 的判据 ⇒ 故「**同一失败信号**」在**路由来源**上与上游**不同型** ⇒ ⇒ ⇒ ⚠️ **2026-11-17 clarify 轮 · 用户拍板（Q4 = 选项 A）**：本项已由「**只登记**」升级为 **正式偏离登记 X-6（STRICTER）/ X-7（DIFF）** + **差分场景 D-119 / D-120**（plan 的**登记项 R-6**）⇒ ⇒ ⇒ **零新增错误类型** ⇒ ⇒ ⇒ **MUST NOT** 改 B11F1 的冻结面 | **B11F1** | B11F1 改版时；或 spec FR-030 的「同一失败信号」被解释为「跨 feature 逐字同款」时（见 **C-7**） |
| **DR-7** | 上游的 **节点别名**（`add_node("x", ..., metadata=...)` 之类的重命名） | `langgraph/graph/state.py` 的 `attach_node` | 本 feature 的 `path_map` 查表用**节点名** ⇒ 别名**不**影响查表 ⇒ 属下游承接 **D-2** 的范围 | **B8F3** | B8F3 落地时 |
| **DR-8** | 上游的 **`context` 通道**（C21） | `langgraph/graph/state.py:1343`（`allow_managed`）· `langgraph/_internal/_runnable.py` 的 runtime 注入 | `context` 是**运行期载体**、不是状态通道 ⇒ MUST **NOT** 进入路由函数的 fresh 视图 ⇒ 属下游承接 **D-2** | **B8F3** | B8F3 落地时 |
| **DR-9** | 上游的 **`Command.PARENT` fan-out**（子图跳转） | `src/freegraph/runtime/_fanout.py:71-75` 侧的**上游对应物**（上游 `Send.node == "__parent__"`） | 子图能力属 v2 ⇒ 本 feature **不实现**（FR-036）⇒ 路由返回 `Send("__parent__")` MUST NOT 被支持 | **v2**（子图） | v2 立项时 |
| **DR-10** | 上游的 **async 路径**（`_aroute` / `ainvoke`） | `langgraph/graph/_branch.py:169-190`（`_aroute`） | 本 feature 只交付**同步**路由求值（FR-036 ⑦）⇒ async 归 v2 | **v2** | v2 立项时 |
| **DR-11** | 上游的 **subgraph** 与 `Command(goto=...)` 的 parent 跳转 | `langgraph/graph/state.py` 的 `Command` 家族 | 与条件边求值**正交** ⇒ 本 feature **零实现** | **v2** | v2 立项时 |
| **DR-12** | 上游的 **`__pregel_*` 内部 config 键**（`__pregel_runtime` / `__pregel_read` / `__pregel_send` / `__pregel_task_id` …） | **实测 P-B**（`configurable` 内含 `__pregel_runtime` 等） | 上游**内部**实现细节 ⇒ freegraph **不实现**、**不**复制 ⇒ 用户若依赖它们 ⇒ 迁移成本由迁移说明承担 | **B25F1**（迁移说明） | B25F1 写迁移说明时 |
| **DR-13** | 上游的 **`__start__` 伪节点的其余副作用**（`triggers=[START]` · `channels=START` · `tags=[TAG_HIDDEN]` · `attach_node(START, None)`） | `langgraph/graph/state.py:1373` · `:1508-1514` | freegraph 的 `__start__` 是**哨兵**（`src/freegraph/runtime/superstep.py:123`）⇒ 本 feature **只照抄「求值」这件事**（D-14）⇒ MUST **NOT** 把 `__start__` 变成可执行节点 | **B8F1**（本 feature 的口径）· 伪节点的其余形态仍**不**实现 | 出现「`__start__` 需要成为可观察节点」的用例 |
| **DR-14** | 上游的 **`branch:to:` 通道写入**（`guard=False` 的 `EphemeralValue` + 写入即触发） | `langgraph/graph/state.py:1524-1530` · `:1581-1596` | freegraph 的 `V-6`（单值语义通道一轮收到多于一个值）**不可放宽** ⇒ 路由通道**不写**（D-09 · 偏离 **X-4**）⇒ 这是**结构差异**、非更严 | **B8F1**（本 feature 的口径） | 若 freegraph 的通道语义引入多值 ⇒ 需重新评估 |

---

## §4 事实性表述的更正（**C-1 … C-9** · **只更正事实 · 判据只收紧不放宽**）

> **处置原则**（沿用 B5F2 / B7F1 的同款）：本轮的实测**只更正事实性表述**
> ⇒ **未**改动任何 FR / SC 的**判据**；若更正导致某条判据**不再可判定**，
> 才需回到 spec —— 本次**未发生**（逐条复核：**SC-001…SC-026 全部仍成立**）。

| # | 位置 | 原表述 | 实测结论 | 处置 |
|---|---|---|---|---|
| **C-1** | spec **Edge Cases**（`spec.md:526-527`）· **X-3**（`spec.md:677`）· **User Story 4 AS 2**（`spec.md:471-472`）· **US4 Independent Test**（`spec.md:465`）· **Q7**（`spec.md:139`） | 「**无** `path_map` 且返回值不是已注册节点名 / `END` ⇒ MUST 抛内置 **`KeyError`**」 | **实测 E-8 / M-I**：上游在**无** `path_map** 时对**非法节点名**是**静默忽略**；而上游对 `None` / `START` 才是 `ValueError`（M-B / M-D）⇒ **澄清轮 Q2（选项 B）已拍板「照抄上游两态」** ⇒ 该场景的 freegraph 口径是 **`ValueError`**（**FR-022** / **SC-007** / **D-111** 均已如此写） | **spec 的这 5 处是澄清轮前的**残留** ⇒ 与 **FR-022 / SC-007 / D-111** **自相矛盾** ⇒ MUST 统一为 **`ValueError`**（**类型**照抄上游 · 消息更详细 ⇒ **X-3** 仍为 **STRICTER**）⇒ **判据不变 · 只更正事实与措辞** |
| **C-2** | spec **Q5 / 引文差异 3 / P-08 / X-2**（`spec.md:112-113` · `:216-217` · `:357` · `:603` · `:676`） | 「上游**代码**（`langgraph/graph/_branch.py:202-204` 的查表**先于** `:207-208` 的 `END` 过滤）」「「`END` 是 `path_map` 的 key」才终止」 | ① `_branch.py:207-208` **不是** `END` 过滤 —— 它是 **`None` / `START` 的 `ValueError` 判定**；真正的 `END` 剔除在 **`langgraph/graph/state.py:1592`**（`if (True if static else p != END)`，配套的 `END` → 通道映射在 `:1586`）⇒ **锚点写错了文件与行号**。<br>② 「`END` 是 `path_map` 的 key」⇒ **终止** **不成立**：**实测 E-17 / E-3**（`path_map = {END: "a"}`）⇒ 查表结果 = `"a"` ⇒ **不终止**、节点 `a` 执行 1 次；只有**查表结果本身是 `END`** 才终止（**E-3b** `{END: END}` · **E-4 / M-J** value 为 `END`）。<br>③ **实测 E-19**：**无** `path_map` 时返回 `END` ⇒ **正常终止**（**不抛错**）⇒ 「只在 `END` 是 key 时才终止」的表述**还漏了**这一种。 | **锚点与措辞 MUST 更正** ⇒ 精确表述 = 「**返回值先查表** ⇒ 只有**查表结果**是 `END`（或**无** `path_map` 且返回值就是 `END`）才终止；查表**失败** ⇒ `KeyError`」⇒ **偏离 X-2 的结论不变**（freegraph 取 docstring 口径 ⇒ **单独返回** `END` ⇒ **无条件终止**（序列内的 `END` ⇒ **剔除**））⇒ **判据不变** |
| **C-3** | spec **Edge Cases**（`spec.md:539-540`）· **FR-020**（`spec.md:808-809`） | 「路由函数返回**非 `str` 的可哈希值**（如 `int` / **`tuple`**）⇒ MUST 作为 `path_map` 的 **key** 正常查表（实测 **E-14 / E-15**）」 | **实测 E-15 / E-31**：返回 **`tuple`** ⇒ 上游按 `_branch.py:199-200` 把它当作**多目标序列** ⇒ **逐元素**查表 ⇒ 失败发生在**元素**层（`KeyError('x')`）⇒ **`tuple` 不是**「单个可哈希 key」。<br>**实测 E-15c / E-32**：只有 `list` **内含** `tuple` 时，该 `tuple` 元素才**按单个 key** 查表（成功）。⇒ `int` 等**非** `list`/`tuple` 的可哈希值确实可作 key（**E-14 / E-30**）。 | **Edge Cases 的 `tuple` 示例 MUST 删除**（与同文的 **FR-024**「`list`/`tuple` ⇒ 多目标」**自相矛盾**）⇒ **FR-020 的正文**（「非 `str` 的**可哈希**值」· 「**不**先做类型收窄」）**仍成立** ⇒ **判据不变**（只是**示例**更正） |
| **C-4** | spec **下游承接条款**表（`spec.md:42-43`）· plan 的**事实性核对**注（`plan.md:288-292`） | D-4 / D-5 的里程碑写作 **M3** | **实测仓库现状**：`harness/features/README.md:47`（**B22F1 = M2**）· `:48`（**B23F1 = M2**）· `:59`（**B25F1 = M4**）⇒ 与立项书 §5.2 逐字一致（`harness/proposals/立项书.md:476` · `:477` · `:488`）⇒ **M3 既不是 README 的、也不是立项书的** ⇒ plan 的注记**成立**（本 plan 以仓库现状为准） | **只记事实 · 不改判据** ⇒ plan 的口径正确 ⇒ spec 的表格**里程碑栏**留待回溯修订（属**发起者**职权）⇒ 见下行 **C-5**（**D-3** 的里程碑另有一处偏差） |
| **C-5** | spec **下游承接条款**表（`spec.md:41`） | D-3（→ **B11F1**）的里程碑写作 **M2** | **实测仓库现状**：`harness/features/README.md:40`（**B11F1 = M1**）· 立项书 `harness/proposals/立项书.md:469`（**B11F1 = M1**）⇒ **M2 不成立** ⇒ 这是 plan 的事实性核对注**未覆盖**的**第三处**里程碑偏差 | **只记事实 · 不改判据** ⇒ plan 的 **R-3** 表已写 **B11F1（M1）** ⇒ **口径一致** ⇒ spec 的表格**里程碑栏**留待回溯修订 |
| **C-6** | spec **P-02**（`spec.md:597`）· **裁定 4** | 上游的 `path_map` 归一化在 `langgraph/graph/_branch.py:96-101` · `:112-114` | 锚点**正确**（`:96-101` = dict/list 归一化 · `:102-114` = `Literal` 推断）⇒ 但本轮**补充实测**（**E-33**）：`path_map=None` + `-> Literal["a"]` ⇒ 上游**推断**出 `path_map` ⇒ 返回表外值 ⇒ **`KeyError('zz')`**（**不是**「无 `path_map`」的静默忽略）⇒ **freegraph 侧 L3 已实现同款**（`src/freegraph/_stategraph.py:145-159`）⇒ **零新增** | **一致**（锚点无误）⇒ 追加**实测证据**（E-33）⇒ **判据不变** ⇒ 落 **D-23** |
| **C-7** | spec **FR-030**（`spec.md:855-857`）· **裁定 10** | 「路由函数返回 `Send` / `list[Send]` 时 MUST 产生**同款** fan-out 任务（同一落点 · 同一入参形态 · **同一失败信号**）」 | **实测 E-21 / E-22**：上游对 `Send`→`END` 抛 **`InvalidUpdateError`**、对 `Send`→未注册节点**静默忽略**；而 freegraph 的 B11F1 `validate_send`（`src/freegraph/runtime/_fanout.py:56-82`）⇒ `Send`→哨兵 ⇒ **`ValueError`**（V-21）· `Send`→未注册节点 ⇒ **`ValueError`**（V-19）⇒ **失败信号的类型**两侧**不同** ⇒ 「同一失败信号」若按「跨 feature 逐字同款」解读，则与 B11F1 的**冻结面**（V-19 / V-21）**冲突** | **已升级为正式偏离登记**（**X-6 / X-7** + 差分 **D-119 / D-120** · plan 的**登记项 R-6**）⇒ 判据**只收紧**（新增覆盖）⇒ 本 feature **MUST NOT** 改 B11F1 的校验 ⇒ 「同一失败信号」在**路由来源**上的**逐字**含义**留待** B11F1 / 差分阶段裁定 ⇒ **不**在本 feature 动判据 |
| **C-8** | spec **P-13**（`spec.md:608`）· **裁定 16** | 双参判别的上游依据只写了 `langgraph/graph/_branch.py:166`（`self.path.invoke(value, config)`） | 判别的**真正实现点** = **`RunnableCallable.__init__`** ⇒ 上游的权威路径是 **`langgraph/_internal/_runnable.py:299`**（类）与 **`:341-365`**（判别循环）+ **`:168-181`**（`KWARGS_CONFIG_KEYS` 的 `"config"` 项）。⚠️ `langgraph/utils/runnable.py` **只是**「Backwards compat imports」的一行 re-export（`:3`）⇒ **MUST NOT** 把它当作类定义位置引用 | **锚点补齐**（**只补事实**）⇒ 判据**不变**（**P-13 = SAME**）⇒ Phase 1 的 `contracts/upstream-parity.md` MUST 引用 **`langgraph/_internal/_runnable.py`** 的行号 ⇒ 追加**实测矩阵**（P-A01…P-A19 · P-C）⇒ 落 **D-11 / D-13** |
| **C-9** | spec **裁定 16**（`spec.md:347`）的**注解匹配集**表述 | 「匹配集 = 无注解 ∨ 类对象 `RunConfig` / `Mapping[str, Any]` ∨ 对应的**字符串**注解 ∨ `Optional[...]` / `Union[..., None]` ∨ 其 PEP-604 等价形式」 | 上游的匹配集是**精确的 5 元组**（`langgraph/_internal/_runnable.py:170-176`）：`(RunnableConfig, "RunnableConfig", Optional[RunnableConfig], "Optional[RunnableConfig]", inspect.Parameter.empty)`<br>⇒ ⚠️ **字符串**槽只含**两个**字面量（`"RunnableConfig"` / `"Optional[RunnableConfig]"`）⇒ **实测 P-A17**：`config: "RunnableConfig \| None"`（**字符串**）⇒ **`UserWarning` + `TypeError`** ⇒ **不**在匹配集内。<br>⇒ **实测 P-A16**：`config: RunnableConfig \| None`（**类对象**的 PEP-604）⇒ **OK** ⇒ 成立的原因是 `Optional[RunnableConfig] == RunnableConfig \| None` 为 **True**（equality 事实）⇒ 即「**类对象**槽」的 PEP-604 等价形式。 | **补齐事实**（**只收紧**）：spec 的**形状**表述正确 ⇒ 但 Phase 1 MUST 把**字符串**槽**逐字钉死**为两个字面量 ⇒ 否则 freegraph 会比上游**宽松**（多接受 `"RunnableConfig \| None"` 字符串）⇒ 追加**实测矩阵** ⇒ 落 **D-13** |

> ⚠️ **本轮实测除上表 9 条外，未发现其它与 spec 判据相抵触的事实**
> ⇒ **SC-001…SC-026 全部仍成立**（C-1 / C-7 是**措辞与口径的一致性**修正 ·
> **判据只收紧不放宽**）。

---

## §5 未决项

> ⚠️ **零 `[NEEDS CLARIFICATION]`** —— 宪法原则 XI「上游有答案 ⇒ 照抄 ⇒ 不问用户」：
> 本 feature 的**全部**语义点上游**均已给出答案**（含本轮实测）⇒ **无**待用户澄清项。
> 下表登记的是「**上游无定论 / freegraph 特有**」的语义点及其**处置**。

| # | 未决点 | 性质 | 处置 | 归属 |
|---|---|---|---|---|
| **U-1** | 上游 `END` 的**终止条件**：代码（查表先于 `END` 剔除）与上游**自己的 docstring**（`state.py:999`）**相互矛盾** ⇒ 上游**自身无定论** | 原则 XI ② 类 | **本轮已由发起者拍板**（澄清轮 **Q1 = 选项 A**）⇒ 取 docstring 口径 ⇒ **单独返回** `END` ⇒ **无条件终止** ⇒ 如实登记 **X-2**（DIFF · 非更严）⇒ 差分 **D-110 / D-118** 锁住 ⇒ 另见 **C-2**（**锚点与措辞**的更正） | 本 feature 内闭合（**裁定 5**） |
| **U-2** | 非法返回值的失败信号：**统一一种异常** vs **照抄上游两态** | 上游的差异源自**查表顺序**而非刻意设计 ⇒ 上游**自身无定论** | **本轮已由发起者拍板**（澄清轮 **Q2 = 选项 B**）⇒ 照抄两态（有 ⇒ `KeyError` · 无 ⇒ `ValueError`）⇒ 消息**更详细** ⇒ **STRICTER**（**X-1 / X-3**）⇒ 另见 **C-1**（spec 的 5 处**残留措辞**待统一） | 本 feature 内闭合（**裁定 6**） |
| **U-3** | 双参路由函数的**判别依据**（**位置参数个数** vs **参数名 `config`**） | 「位置参数个数」是**推测**而非上游行为 ⇒ 上游**有**答案（实测 P-A02 ⇒ `TypeError`）⇒ 不属「可问」 | **本轮已由发起者拍板**（澄清轮 **Q6**）⇒ 照抄上游（**参数名**判别 · **关键字**注入 · 永远一个位置实参）⇒ **P-13 = SAME** ⇒ 只第二参的**内容**与**注解匹配集**不同 ⇒ 归 **X-5** | 本 feature 内闭合（**裁定 16**） |
| **U-4** | 双参第二参的**内容**（上游 = **增广**的 `RunnableConfig` dict · 实测 P-B） | **上游无定论**（「用户那份配置」这一层语义上游**没有**给出） | **本轮已由发起者拍板**（澄清轮 **Q4 = 选项 A**）⇒ 传用户交给 `invoke` 的**原始 `config`**（**逐字**）⇒ **DIFF** · 非更严 ⇒ 归 **X-5** | 本 feature 内闭合（**裁定 12**） |
| **U-5** | `__start__` 上的条件边是否被求值 | 上游**有**答案（`__start__` 是**真实伪节点** · 实测 N-A1…N-A6） | 照抄 ⇒ **本轮已由发起者拍板**（澄清轮 **Q5 = 选项 A**）⇒ freegraph 的「静默空跑」被标为**缺陷** ⇒ 落 **D-14** / **裁定 17** | 本 feature 内闭合 |
| **U-6** | `__start__` 条件边与「**唯一入口点**」契约的关系（纯条件边入口 · 静态与条件并存） | 上游**有**答案（实测 N-A1 / N-A2） | 照抄 ⇒ **本轮已由发起者拍板**（澄清轮 **Q7**）⇒ 允许纯条件边入口 · 并存时**同轮并行** · 返回 `END` ⇒ 该分支终止 ⇒ 落 **D-14** / **裁定 17** | 本 feature 内闭合 |
| **U-7** | `__start__` 上登记**多条**条件边的 branch 名纪律 | 上游**有**答案（`path.name or "condition"` ⇒ 重名 ⇒ 内置 `ValueError` · 实测 N-A5b） | 照抄 ⇒ **本轮已由发起者拍板**（澄清轮 **Q8**）⇒ 与普通源节点**同款** ⇒ 落 **D-15** / **裁定 18** | 本 feature 内闭合 |
| **U-8** | 条件边的**路由判定差分**的载体（B5F2 夹具 vs `parity_probe.py`） | 上游**无对应物**（freegraph 自有的夹具体系）⇒ 属「必须自研区」 | **本轮已由发起者委托判断**（澄清轮 **Q3 = 选项 B**）⇒ 落 `tests/differential/parity_probe.py`（**双真实实现**对跑）⇒ B5F2 的 **V-4 无需放宽** ⇒ 落 **D-16** / **裁定 15** | 本 feature 内闭合 |
| **U-9** | 路由返回 `Send` 时的**失败信号**与 B11F1 的**冻结面**（V-19 / V-21）的关系 | **freegraph 特有**（B11F1 已冻结）⇒ 跨 feature 的口径交叉 | **只登记**（**DR-6** / **C-7**）⇒ 本 feature **MUST NOT** 改 B11F1 的判据 ⇒ 「同一失败信号」的**逐字**含义**留待** B11F1 / 差分阶段裁定 ⇒ **本轮不改判据** | **B11F1**（承接方）· 本 feature 只接线 |
| **U-10** | `Send` 的上游失败信号（`InvalidUpdateError`）与 freegraph 的 `ValueError` 的**类型差** | 上游**有**答案（实测 E-21）· 但 freegraph 侧**已冻结** | **只登记**（**DR-6**）⇒ 不在本 feature 改判据 ⇒ 若将来统一 ⇒ 归 **B11F1** | **B11F1** |
| **U-11** | spec「下游承接」表的**里程碑栏**（D-3 / D-4 / D-5）与仓库现状不符 | **事实性**偏差（非判据） | **本轮已实测核对**（README + 立项书 §5.2）⇒ 结论见 **C-4 / C-5** ⇒ **只记事实 · 不改判据** ⇒ spec 表格的**里程碑栏**留待**回溯修订**（属**发起者**职权） | **发起者**（回溯修订）· 本 feature 只登记 |

---

> ⚠️ **本文件的边界**（沿用 B7F1 / B5F2 的同款口径）：
> ① 本文件是**证据表**，**MUST NOT** 被测试解析（测试**直接断言行为**）；
> ② 判据的唯一权威是 spec 与 Phase 1 的 `contracts/conditional-edge-contract.md`；
> ③ 本文件的**全部实测**在**仓库之外**完成 ⇒ 仓库**零改动** ⇒
> `pyproject.toml` **零改动** ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿；
> ④ 换上游版本 ⇒ MUST 重新核实**全部**行号并重跑 §2 的**全部**探针。
