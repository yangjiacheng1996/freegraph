# Quickstart: B8F1 · 条件边路由求值 + `END` 终止 + fresh 读（C8 独立回归测试）

**Feature**: `B8F1` · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**契约权威**: [contracts/conditional-edge-contract.md](./contracts/conditional-edge-contract.md) ·
**上游对照**: [contracts/upstream-parity.md](./contracts/upstream-parity.md)
**核实环境**: CPython **3.11.16** · 上游 `langgraph` **1.2.11** + `langchain-core` **1.7.6**
（取证于 2026-11-17）

> 本文件是**可照抄的验证手册**（闸口 **V1…V16**）—— 只写**怎么跑**与**期望看到什么**，
> **不含**实现代码（实现属 `tasks.md` 与实现阶段）。
> ⚠️ **实施前这些闸口 MUST 为红**：本手册描述的是**交付后**应当看到的形态 ⇒
> 期望输出写的是**目标形态**，不是当前仓库的状态。
> ⚠️ **编号消歧**：本手册的 `V1…V16` = **验收闸口**（无连字符）；
> `data-model.md` §5 的 `V-8` / `V-27…V-31` = **校验规则**（连字符）
> ⇒ 两个空间**并存但不相通** ⇒ 引用时 MUST 写全（「验收闸口 Vn」/「校验规则 V-n」）。
> ⚠️ **公开面**：本 feature 的公开 API 不变 ⇒ 本手册的片段只用 `freegraph.graph` 的
> `StateGraph` / `START` / `END`（+ 既有 `Command` / `Send` / `interrupt` / `RunConfig`）。

---

## 0. 环境与前置

### 0.1 解释器与仓库根目录的 `.venv`

| 项 | 要求 | 备注 |
|---|---|---|
| Python | **≥ 3.11** | **最低档 3.11 MUST 跑全量**（门禁 **G9** 的 AST 静态断言配套）⇒ `typing` 构件上限 = 3.11 |
| venv | 仓库根目录的 **`.venv`** | 本手册所有命令统一写成 `uv run --no-project --python .venv python …` ⇒ 跨平台一致 |
| 开发依赖组 | **`differential`** MUST 已装 | 上游 `langgraph` **1.2.11** 在该组里 ⇒ 差分闸口**真跑**；缺席即 `skip` |
| 运行时依赖 | **零第三方** | `dependencies = []` ⇒ `pyproject.toml` **零改动**（FR-033） |

```bash
# 自检：解释器版本 + 两条依赖面的实际状态
uv run --no-project --python .venv python -c "import sys, importlib.metadata as m; \
print(sys.version.split()[0], m.version('langgraph'))"
```

**期望输出**：`3.11.16 1.2.11` ⇒ 最低档 3.11 · 上游版本与 `pyproject.toml:100` 钉死值**逐字一致**。
（`langgraph` 缺席时本命令只打印版本号 ⇒ 差分闸口走 `skip` 路径。）

### 0.2 两条命令的形态

```bash
# ① 全量测试（CI 的等价物）
uv run --no-project --python .venv python -m pytest tests/ -ra

# ② 差分（上游缺席即 skip —— **不是**失败）
uv run --no-project --python .venv python -m pytest tests/differential/ -ra
```

⚠️ 差分那条在**未装** `differential` 组的环境里 ⇒ 差分用例被 **skip**
⇒ **不是失败**（FR-032 · 上游缺席即 `skip`）⇒ 但 **MUST NOT** 把 skip 当成「已验证」。
⚠️ 本 feature **零新增依赖** ⇒ `pyproject.toml` **零改动** ⇒ 门禁
**G3 / G21 / G22 / G23** 恒绿（plan「门禁编号纪律」）。

### 0.3 既有门禁（**零新增编号** · 编号连续性 `G1–G30` 是不变量）

```bash
uv run --no-project --python .venv python harness/scripts/gates/gate_G29_contract_carrier.py
```

| 既有门禁 | 对本 feature 的覆盖 | 本手册落在哪一闸口 |
|---|---|---|
| **G2** | `tests/contracts/**` **零** `freegraph.*` import ⇒ C8 用例 MUST 住 `tests/runtime/` | V2 |
| **G29** | C4 / C8 挂载点（C8 由 `not-landed` 翻 `landed`） | V2 |
| **G25** | 新增的 `src/freegraph/runtime/_routing.py` 落 L2（目录条目）⇒ 自动纳入扫描 | V14 |
| **G30** | 新源文件的署名头覆盖率 == 100% | V14 |
| **G9** | typing 构件上限 3.11（AST 静态断言） | §0.1 自检 + 全量 |
| **G3 / G21 / G22 / G23** | 零新增依赖（依赖闭包 / 隔离环境 / 许可证） | V15 |
| **G4 / G24 / G26 / G27** | 零环境变量 / 零出站 | V15 |
| **G7 / G15 / G19** | 公开面零变更（契约 **21** / 门面 **7** / runtime **23**） | V14 |

### 0.4 两条红线提醒

- **内核零出站** · **零环境变量** · **零第三方运行时依赖**（FR-033 · SC-017 / SC-018）
  ⇒ 路由求值**不得**引入任何 I/O、网络、配置读取。
- **门禁编号零新增** ⇒ 新能力一律由**既有门禁**自动覆盖 ⇒ 门禁总数仍 == **30**。

---

## 1. 闸口表总览

| 闸口 | 验证什么 | SC 编号 | 命令形态 | 通过判据 |
|---|---|---|---|---|
| **V1** | C8 fresh 读（**否定式**断言） | SC-001 · SC-002 · SC-004 | `pytest tests/runtime/test_conditional_edges.py` | 路由函数**看到了**本节点本次写入的值 |
| **V2** | C8 挂载点翻 `landed` + 元测试 + G29 | SC-014 | `grep GATE-MOUNT` + `pytest tests/contracts/` + `gate_G29` | 挂载点 `landed` · 元测试非 skip · G29 PASS |
| **V3** | `END` 终止（含**与上游的分叉**） | SC-003 | `pytest` + 最小闭环片段 | 后续目标执行次数 == **0** · 分叉被断言 |
| **V4** | `path_map` 双形态与目标解析 | SC-005 · SC-009 | `pytest` + 最小闭环片段 | list / dict / `None` 三形态各自路由正确 · **非 `str` 的可哈希值（如 `int`）作 key 正常查表** |
| **V5** | 失败信号**两态** + 消息更详细 | SC-006 · SC-007 | `pytest` + 最小闭环片段 | `KeyError` / `ValueError` 两态 + 消息含返回值与可选目标 · 返回 `None` / `START` 的**查表优先**两态 |
| **V6** | 序列多目标 · `Send` 复用 · `Command.goto` 并集 | SC-008 | `pytest` + 最小闭环片段 | 多目标**同轮**并行 · 共享状态 · 逐目标载荷相异 · **空序列 `[]` ⇒ 不报错** · 重复目标**去重保序** |
| **V7** | 双参形态与 `config` 注入规则 | SC-021 | `pytest` + 最小闭环片段 | 第二参 == 用户交给 `invoke` 的**原始** `config`（逐字）· 注解不匹配 ⇒ 跳过注入 ⇒ **不发** `UserWarning` |
| **V8** | `__start__` 条件边（三情形） | SC-022 · SC-023 | `pytest` + 最小闭环片段 | 被求值 · 纯条件边入口 · 并存同轮并行 |
| **V9** | branch 名唯一 | SC-024 | `pytest` + 最小闭环片段 | 同源重名 ⇒ 内置 `ValueError`（消息点名分支名与源节点） |
| **V10** | 零副作用（路由通道 / 返回键集 / 零污染） | SC-002 · SC-010 · SC-011 | `pytest` + 最小闭环片段 | 路由通道**未被写入** · 不进返回键集 · 读取前后快照相等 |
| **V11** | 路由函数异常**原样传播** | SC-012 | `pytest` + 最小闭环片段 | 原始类型 + 原始消息（不被包装） |
| **V12** | 差分组 **D-103…D-120** | SC-013 | `diff_parity.py` + `pytest tests/differential/` | **18** 条 · SAME **12** / DIFF **4** / STRICTER **2** |
| **V13** | 破冻结面的回溯验证（**7 类**） | SC-015 · SC-016 · SC-019 · SC-025 | `pytest`（四个文件）+ `graph_core.py` + `agent_loop.py` | **7 类**全部按「拆分而不删」落地 · **4 类**既有断言仍绿 |
| **V14** | 零新增面 | SC-016 · SC-018 | `python -c` 导出面清点 | **7** / **23** / **21** / `vars(compiled)` == **11** |
| **V15** | 零出站 · 零环境变量 · 零第三方 | SC-017 · SC-018 | `gate_G24/G26/G27` + `grep` + 发行元数据 | 出站 **0** · 环境变量读取 **0** · 上游导入 **0** |
| **V16** | 人工验证记录 + 发起者追认 | SC-019 · SC-020 | `test -s` + `grep` | 记录存在且**正文非空** · 五段式 · 真实轮未落地声明 |

> ⚠️ **SC 覆盖自检**：SC-001…SC-026 共 **26** 条 ⇒ 上表逐条可溯
> （SC-001→V1 · SC-002→V1/V10 · SC-003→V3 · SC-004→V1 · SC-005→V4 ·
> SC-006→V5 · SC-007→V5 · SC-008→V6 · SC-009→V4 · SC-010→V10 · SC-011→V10 ·
> SC-012→V6/V11 · SC-013→V12 · SC-014→V2 · SC-015→V13 · SC-016→V13/V14 ·
> SC-017→V15 · SC-018→V14/V15 · SC-019→V13/V16 · SC-020→V16 · SC-021→V7 ·
> SC-022→V8 · SC-023→V8 · SC-024→V9）。

---

## 2. 闸口 V1 · C8 fresh 读（**核心判据**）

**目的**：断言路由函数**看到了**本节点**本次**写入的值（C8 · **否定式**断言）。

**命令**：

```bash
# C8 的**实际**回归用例 MUST 住 tests/runtime/（门禁 G2 禁 tests/contracts/** import freegraph.*）
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edges.py -ra
```

**期望输出**：pytest 末行 `N passed`（N ≥ **1**）⇒ 且其中 MUST 含 **C8 的否定式用例**
⇒ 「路由函数读到**旧值**」的用例数 == **0**。

手工复核（最小闭环 · **15 行**）：

```python
from typing import Annotated, TypedDict
import operator
from freegraph.graph import StateGraph, START, END
S = TypedDict("S", {"messages": Annotated[list, operator.add], "llm_calls": int})
seen = {}
def router(state): seen.update(state); return "after"
g = StateGraph(S)
g.add_node("writer", lambda s: {"messages": ["fresh"], "llm_calls": 7})
g.add_node("after", lambda s: {})
g.add_edge(START, "writer")
g.add_conditional_edges("writer", router, ["after", END])
g.compile().invoke({"messages": [], "llm_calls": 0})
assert seen["messages"] == ["fresh"], seen
assert seen["llm_calls"] == 7, seen
print("C8 fresh 读 OK", seen["messages"], seen["llm_calls"])
```

**期望输出**（手工复核）：`C8 fresh 读 OK ['fresh'] 7`
⇒ 两条断言都是**否定式**（断言**看到了**新值）⇒ 而不只是「跑通了」。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
49 passed in 0.41s
C8 fresh 读 OK ['fresh'] 7
```

**判据出处**：`SC-001` · `SC-002` · `SC-004`（+ `FR-007`…`FR-013`）·
差分场景 `D-105`（两侧 fresh 视图**逐字相等**）· 契约条款
`contracts/conditional-edge-contract.md` §3（fresh 读）+ §7 **I-5**（零污染）/ **I-6**（路由通道缺席）。

**失败排查**：

1. 路由函数读到**旧值** ⇒ 求值落点错到**阶段 ⑤ 之后** ⇒ 见契约 §2.1「与写入合并的关系」。
2. 路由函数**根本没被调用** ⇒ 条件边载荷没接线 ⇒ 见契约 §1「载荷载体」+ §9。
3. 视图里**缺 key** ⇒ 稀疏口径判错 ⇒ 无值覆盖型通道应当**缺席**（契约 §3）。
4. `messages` 看到的是 `["fresh"]` 而**不是** `["seed", "fresh"]` ⇒ 归约器未在 fresh 读里生效
   ⇒ 见契约 §3「归约器已生效」（FR-009）。

---

## 3. 闸口 V2 · C8 挂载点翻 `landed` + 元测试（门禁 **G29**）

**目的**：C8 的**断言本体**住 `tests/runtime/` ⇒ `tests/contracts/` 只留**路径扫描**的
**元测试**（**零** `freegraph.*` import）⇒ 挂载点由 `not-landed` 翻为 `landed`
（破冻结面 **T-5**）。

**命令**：

```bash
# ① 挂载点的机器可读标记（门禁 G29 逐条解析）
grep -n "GATE-MOUNT" tests/contracts/test_contract_regressions.py

# ② 元测试 + 门禁 G2（契约层零内部 import）
uv run --no-project --python .venv python -m pytest tests/contracts/ -ra

# ③ 门禁 G29（C4 / C8 挂载点 + 只读基准 diff + 验收脚本退出码）
uv run --no-project --python .venv python harness/scripts/gates/gate_G29_contract_carrier.py
```

**期望输出**：

```
35:# GATE-MOUNT: C4 · status=landed · owner=B5F2 · milestone=M1 · desc=稀疏状态读
36:# GATE-MOUNT: C8 · status=landed · owner=B8F1 · milestone=M2 · desc=条件边 fresh 状态读
```

⇒ ② 的 pytest 末行 `N passed` ⇒ 且 **C8 那条不再是 skip**
（当前是 `@pytest.mark.skip` + `raise NotImplementedError` ⇒ 实施后 MUST 被替换为真正的元测试）
⇒ ③ 的输出含 `[G29] 挂载点 C8：已落地（tests/contracts/test_contract_regressions.py）`
⇒ 且末行 `[G29] PASS —— 契约门禁载体（只读基准 diff + C4 / C8 挂载点 + 验收脚本集退出码）`。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
286 passed, 2 skipped in 2.12s
[G29] 挂载点 C4：已落地（tests/contracts/test_contract_regressions.py）
[G29] 挂载点 C8：已落地（tests/contracts/test_contract_regressions.py）
[G29] PASS —— 契约门禁载体
```

**判据出处**：`SC-014`（+ `FR-034`）· 破冻结面 **T-5** · 承接条款 **H-9** ·
契约条款 `conditional-edge-contract.md` §1（载荷载体）+ §9（零新增面）。

**失败排查**：

1. 元测试报「不在 pytest 的收集根内」⇒ C8 回归文件落在了 `tests/` 之外
   ⇒ MUST 住 `tests/runtime/`（**参照**同文件 `:49-82` 的 C4 元测试写法）。
2. G2 变红 ⇒ `tests/contracts/**` 里出现了 `freegraph.*` import ⇒ 元测试 MUST **只**做路径扫描。
3. G29 仍输出「挂载点 C8：未落地」⇒ `:36` 的 `status=` 未翻 ⇒ 见 spec 破面清单 **T-5**。
4. G29 报「只读基准 diff 不一致」⇒ `harness/demo/target.py` 被改了 ⇒ **T-4 不破**，MUST 回退。

---

## 4. 闸口 V3 · `END` 终止（含**与上游的分叉**）

**目的**：路由函数返回 `END` ⇒ 整张图终止；并**断言与上游的分叉本身**（偏离 **X-2**）。

**命令**：

```bash
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edges.py -ra
```

**期望输出**：pytest 末行 `N passed` ⇒ 且下列四类情形的断言**逐条成立**：

| 情形 | freegraph（期望） | 上游（实测） | 判词 |
|---|---|---|---|
| 返回 `END` · `path_map` **不含** `END` 键 | **终止**（不抛错）· 后续节点执行 **0** 次 | 抛 `KeyError: '__end__'`（查表失败） | **DIFF** · `D-110` |
| 返回 `END` · `path_map = {END: "b"}` | **单独返回** `END` ⇒ **无条件终止**（`b` 执行 **0** 次） | 解析后目的地 == `"b"` ⇒ 路由到 `b`（**不终止**） | **DIFF** · `D-118` |
| 返回 `END` · `path_map = {END: END}` | **终止** | **终止** | SAME · `D-106` |
| 返回 `END` · **无** `path_map` | **终止** | **终止** | SAME |

手工复核（分叉那一例 · **13 行**）：

```python
from typing import TypedDict
from freegraph.graph import StateGraph, START, END
S = TypedDict("S", {"messages": list})
seen = []
def b(state): seen.append("b"); return {}
g = StateGraph(S)
g.add_node("r", lambda s: {"messages": ["r"]})
g.add_node("b", b)
g.add_edge(START, "r")
g.add_conditional_edges("r", lambda s: END, {END: "b"})
g.compile().invoke({"messages": []})
assert seen == [], seen
print("END 单独返回 ⇒ 无条件终止 OK（上游会执行 b）")
```

**期望输出**（手工复核）：`END 单独返回 ⇒ 无条件终止 OK（上游会执行 b）`
⇒ 即「freegraph 终止、**上游会执行 `b`**」这条**分叉被断言**（不是把分叉抹平）。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
END 单独返回 ⇒ 无条件终止 OK（上游会执行 b）
```

**判据出处**：`SC-003`（+ `FR-019`）· 偏离 **X-2**（DIFF · 非更严）· 裁定 **5** ·
差分场景 `D-110` / `D-118`（另 `D-106` 为 SAME）·
契约条款 `conditional-edge-contract.md` §4.3（序列与 `END`）+ §7 **I-8**。

**失败排查**：

1. `b` **被执行了** ⇒ `END` 的判定被放到 `path_map` 查表**之后** ⇒ MUST **先于**查表（契约 §4.3）。
2. 抛了 `KeyError` ⇒ 走的是「查表失败」路径 ⇒ `END` 未被无条件识别（契约 §4.3「`END` **单独返回** ⇒ **无条件终止**」）。
3. 整张图**没终止** ⇒ 终止信号未进调度内核 ⇒ 检查目标序列里 `END` 是否被剔除并触发终止。

> ⚠️ **口径**：`END` 的判定分**三处** —— ① **单独返回** `END` ⇒ **无条件终止**；
> ② 经 `path_map` **解析后**的目标是 `END` ⇒ 终止；
> ③ **序列内**的 `END` ⇒ **被剔除**（其余目标照常执行 · 照抄上游 E-13）
> ⇒ ⇒ ⇒ 详见 spec 的 FR-019 与契约 §4

---

## 5. 闸口 V4 · `path_map` 双形态与目标解析

**目的**：`path_map` 的 **list / dict / 无** 三形态各自路由正确，且**条件边 ≠ 屏障组**。

**命令**：

```bash
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edges.py -ra
```

**期望输出**：pytest 末行 `N passed` ⇒ 逐条成立：

| 形态 | 路由函数返回 | 期望结果 |
|---|---|---|
| **list**（构建期归一化为 `{name: name}`） | `"a"` | 节点 `a` 执行 **1** 次 · 另一目标执行 **0** 次 |
| **dict**（返回值作 **key** 查表） | `"hit"`（`{"hit": "a", "miss": "b"}`） | 节点 `a` 执行 **1** 次 · `b` 执行 **0** 次 |
| **无** `path_map`（动态目标） | 已注册节点名 | 该节点执行 **1** 次（返回值**直接**作节点名） |
| **无** `path_map` + 未注册节点名 | `"ghost"` | 内置 `ValueError`（见 V5） |

手工复核（dict 形态 · **14 行**）：

```python
from typing import TypedDict
from freegraph.graph import StateGraph, START
S = TypedDict("S", {"messages": list})
hits = []
def hit(state): hits.append("hit"); return {}
def miss(state): hits.append("miss"); return {}
g = StateGraph(S)
g.add_node("r", lambda s: {"messages": ["r"]})
g.add_node("hit", hit); g.add_node("miss", miss)
g.add_edge(START, "r")
g.add_conditional_edges("r", lambda s: "hit", {"hit": "hit", "miss": "miss"})
g.compile().invoke({"messages": []})
assert hits == ["hit"], hits
print("dict 形态 OK", hits)
```

**期望输出**（手工复核）：`dict 形态 OK ['hit']`
⇒ 「返回值作 key 查表 ⇒ 命中 `hit` · `miss` **未**执行」两条同时成立。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
dict 形态 OK ['hit']
```

**判据出处**：`SC-005`（+ `FR-015` / `FR-016` / `FR-017` / `FR-020`）· `SC-009`（+ `FR-004` / `FR-006`）
⇒ ⇒ ⇒ ⚠️ **2026-11-18 · analyse 轮补登记**：新增「**非 `str` 的可哈希值**（如 `int`）作 key
正常查表」的用例（tasks **T073**）
（+ `FR-004` / `FR-006` · 条件边目标集合**不**受屏障组判定影响）·
差分场景 `D-103`（list）· `D-104`（dict）· `D-109`（动态目标）·
契约条款 `conditional-edge-contract.md` §4.2 + §7 **I-2**。

**失败排查**：

1. list 形态报「查表失败」⇒ L2 **重新归一化**了 `path_map` ⇒ MUST NOT（裁定 **4** · H-3 / H-4）。
2. dict 形态路由到**错的目标** ⇒ 返回值被当成了 **value** 而非 **key** ⇒ 见契约 §4.2。
3. 动态目标（无 `path_map`）报「目标不存在」⇒ 目标存在性校验口径错 ⇒ 见契约 §4.2 / 校验规则 **V-29**。
4. 多源边被当条件边求值 ⇒ 条件边与屏障组**混用** ⇒ 见契约 §2.3（承接 **H-6**）。

---

## 6. 闸口 V5 · 失败信号**两态** + 消息更详细

**目的**：**有** `path_map` ⇒ 内置 `KeyError`；**无** `path_map` ⇒ 内置 `ValueError`；
两态的**消息**都 MUST 指明**返回值**与**可选目标**（偏离 **X-1 / X-3**）。

**命令**：

```bash
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edges.py -ra
```

**期望输出**：pytest 末行 `N passed` ⇒ 且「被**静默忽略**的用例数 == **0**」：

| 场景 | 异常类型 | 消息 MUST 含 |
|---|---|---|
| 有 `path_map` · 返回值不在表内 | 内置 **`KeyError`**（类型与上游**逐字同款**） | 返回值 + 可选目标清单 |
| 无 `path_map` · 返回未注册节点名 | 内置 **`ValueError`** | 返回值 + 已注册节点名 |
| 有 `path_map` · 返回 `None` / `START` | 内置 **`KeyError`** | 返回值 |
| 无 `path_map` · 返回 `None` / `START` | 内置 **`ValueError`** | 返回值 |

手工复核（两态 + 消息 · **15 行**）：

```python
from typing import TypedDict
from freegraph.graph import StateGraph, START
S = TypedDict("S", {"messages": list})
def build(pm):
    g = StateGraph(S)
    g.add_node("r", lambda s: {"messages": ["r"]})
    g.add_node("hit", lambda s: {})
    g.add_edge(START, "r")
    g.add_conditional_edges("r", lambda s: "nope", pm)
    return g.compile()
for pm, exc in (({"hit": "hit"}, KeyError), (None, ValueError)):
    try:
        build(pm).invoke({"messages": []})
    except exc as e:
        print(type(e).__name__, "| 消息含返回值 nope:", "nope" in str(e))
```

**期望输出**（手工复核）：

```
KeyError | 消息含返回值 nope: True
ValueError | 消息含返回值 nope: True
```

⇒ 两态的**类型**分得开 ⇒ 且**消息**都点名了返回值（**比上游更详细** ⇒ STRICTER）。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
KeyError | 消息含返回值 nope: True
ValueError | 消息含返回值 nope: True
```

**判据出处**：`SC-006` · `SC-007`（+ `FR-021` / `FR-022` / `FR-025`）· 偏离 **X-1**（STRICTER）·
⚠️ **2026-11-18 · analyse 轮补登记**：新增「返回 `None` / `START` ⇒ **查表优先**的两态」
用例（tasks **T072**）与「注入被跳过时**不发** `UserWarning`」的用例（tasks **T074** · 偏离 **X-5**）·
偏离 **X-3**（STRICTER）· 裁定 **6** / 裁定 **7** ·
差分场景 `D-107`（**只比对异常类型**）· `D-111`（⚠️ MUST 带 `note`）·
契约条款 `conditional-edge-contract.md` §6.1 + §7 **I-7**。

**失败排查**：

1. 两态都抛**同一种**类型 ⇒ 未照抄上游的**两态**（澄清轮 **Q2** = 选项 B）⇒ 见裁定 **6**。
2. 类型对但**消息**只有 key ⇒ 未实现「更详细的消息」⇒ 偏离 **X-1** 未落地。
3. 无 `path_map` + 非法节点名**静默结束** ⇒ 照抄了上游的静默忽略 ⇒ 偏离 **X-3** 未落地（校验规则 **V-29**）。
4. 差分场景 `D-107` 红了 ⇒ 多半是**逐字比对了异常消息** ⇒ MUST **只比对类型**。

---

## 7. 闸口 V6 · 序列多目标 · `Send` 复用 · `Command.goto` 并集

**目的**：序列 = **多目标并行**（共享状态 · **无**逐目标载荷）· `Send` 复用 B11F1 构造器 ·
条件边目标与同轮 `Command.goto` 目标**取并集**。

**命令**：

```bash
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edges.py -ra
```

**期望输出**：pytest 末行 `N passed` ⇒ 逐条成立：

| 场景 | 期望结果 |
|---|---|
| 返回 `["b", "c"]` | `b` 与 `c` **各执行 1 次** · **同轮**并行 |
| 两个目标收到的入参 | **逐字相等**（**共享同一份状态** · 无逐目标载荷） |
| 返回 `[Send("b", payload)]` | `b` 收到的是**载荷**（**不是**共享状态）⇒ 与序列**语义相异** |
| 同轮既有 `Command(goto=...)` 又有条件边 | 两个来源的目标**并集**（去重保序）· 各自执行 **1** 次 |
| 返回含重复目标的序列 | **去重保序**（同一目标只触发一次） |
| 返回空序列 `[]` | **无目标**（**不是**非法返回值）· 不报错 |

手工复核（序列多目标 + 共享状态 · **15 行**）：

```python
from typing import TypedDict
from freegraph.graph import StateGraph, START
S = TypedDict("S", {"messages": list})
seen = []
def b(state): seen.append(("b", dict(state))); return {}
def c(state): seen.append(("c", dict(state))); return {}
g = StateGraph(S)
g.add_node("r", lambda s: {"messages": ["r"]})
g.add_node("b", b); g.add_node("c", c)
g.add_edge(START, "r")
g.add_conditional_edges("r", lambda s: ["b", "c"], ["b", "c"])
g.compile().invoke({"messages": []})
assert [n for n, _ in seen] == ["b", "c"], seen
assert seen[0][1] == seen[1][1], seen
print("序列多目标 OK", [n for n, _ in seen])
```

**期望输出**（手工复核）：`序列多目标 OK ['b', 'c']`
⇒ 两个目标**同轮**执行（轮内顺序 = **节点名序**）⇒ 且收到的入参**逐字相等**。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
序列多目标 OK ['b', 'c']
```

**判据出处**：`SC-008`（+ `FR-018` / `FR-024` / `FR-030`）· `SC-012`（+ `FR-031` 并集）·
⚠️ **2026-11-18 · analyse 轮补登记**：新增「**空序列** `[]` ⇒ 不报错 · 不触发任何目标」
（tasks **T071**）与「序列含**重复目标** ⇒ **去重保序**」（tasks **T075**）·
裁定 **9**（序列 vs `Send` 语义相异）· 裁定 **10**（复用 B11F1 的 `validate_send` / `make_fanout`）·
裁定 **13**（并集）· 差分场景 `D-108`（序列）· 承接条款 **H-8** / **H-7** ·
契约条款 `conditional-edge-contract.md` §4.1 / §4.3 / §5 + §7 **I-4**。

**失败排查**：

1. 序列只执行了**第一个**目标 ⇒ 序列被当成「单个返回值」⇒ 见 **FR-024**（上游同款 · `list`/`tuple` ⇒ 多目标）。
2. 两个目标收到的入参**不等** ⇒ 序列被当成了 `Send` ⇒ 两者语义**必须相异**（裁定 **9**）。
3. `Send` 的目标收到**共享状态** ⇒ 路由另写了一条 fan-out 路径 ⇒ MUST 复用 B11F1 构造器（裁定 **10**）。
4. `Command.goto` 的目标**没跑** ⇒ 未取并集 ⇒ 见裁定 **13**（去重保序）。

---

## 8. 闸口 V7 · 双参形态与 `config` 注入规则

**目的**：路由函数支持**单参**与**双参**两形态；双参的第二参 = 用户交给 `invoke` 的
**原始 `config`**（**逐字**）；判别依据 = **第二参的参数名是 `config`**。

**命令**：

```bash
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edges.py -ra
```

**期望输出**：pytest 末行 `N passed` ⇒ 判别矩阵逐条成立（上游同款）：

| 路由函数形态 | 期望 | 依据 |
|---|---|---|
| `f(state)` | 一参调用 · OK | P-A01 |
| `f(state, config)`（**无注解**） | 一参 + `config=` **关键字**注入 · OK | P-A03 |
| `f(state, config: RunConfig)` / `Mapping[str, Any]`（**类对象**） | 注入 · OK | P-A12 |
| 字符串注解 `"RunConfig"` / `"Optional[RunConfig]"` / `"Mapping[str, Any]"` / `"Optional[Mapping[str, Any]]"` | 注入 · OK | P-A13 / P-A15 |
| `Optional[...]` / `Union[..., None]` / **PEP-604** 等价形式 | 注入 · OK | P-A14 / P-A16 |
| `f(state, cfg)`（第二参**不叫** `config`） | 按**一参**调用 ⇒ `TypeError` | P-A02 · `D-115` |
| `f(state, **kwargs)` | **不注入**（kwargs 为空） | P-A07 |
| `f(state, config: "RunConfig \| None")`（**字符串**的 PEP-604 写法） | **跳过注入** ⇒ `UserWarning` + 按一参调用 ⇒ `TypeError` | P-A17 |
| `f(state, config: dict)`（**匹配集外**） | **跳过注入** ⇒ `UserWarning` + 按一参调用 ⇒ `TypeError` | P-A04 / P-A05 / P-A19 |

手工复核（第二参**逐字** = 用户那份 `config` · **13 行**）：

```python
from typing import TypedDict
from freegraph.graph import StateGraph, START
S = TypedDict("S", {"messages": list})
got = {}
def router(state, config): got["cfg"] = config; return "hit"
g = StateGraph(S)
g.add_node("r", lambda s: {"messages": ["r"]})
g.add_node("hit", lambda s: {})
g.add_edge(START, "r")
g.add_conditional_edges("r", router, {"hit": "hit"})
g.compile().invoke({"messages": []}, {"recursion_limit": 3})
assert got["cfg"] == {"recursion_limit": 3}, got
print("双参 OK", got["cfg"])
```

**期望输出**（手工复核）：`双参 OK {'recursion_limit': 3}`
⇒ 第二参 == **用户交给 `invoke` 的原始 `config`**（**逐字** · 未归一化 · 未用 `context` 顶替）。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
双参 OK {'recursion_limit': 3}
```

**判据出处**：`SC-021`（+ `FR-003`）· 偏离 **X-5**（DIFF · 非更严 · 只差载体类型）·
裁定 **12** / 裁定 **16**（判别规则与注解匹配集）· 上游对照 **P-13**（SAME）· **P-19**（DIFF）·
差分场景 `D-114`（比对**形态**而非内容）· `D-115`（`TypeError`）·
契约条款 `conditional-edge-contract.md` §1.1（双参判别矩阵）+ §7 **I-10**。

**失败排查**：

1. `f(state, cfg)` **正常跑通** ⇒ 凭**位置参数个数**补传了第二参 ⇒ MUST 按**参数名**判别（裁定 **16**）。
2. `config: dict` 也被注入了 ⇒ 注解匹配集**放宽**了 ⇒ 匹配集外的注解 MUST **跳过注入**。
3. `"RunConfig | None"` 字符串被接受了 ⇒ 字符串槽**多收了**字面量 ⇒ MUST 只含**每种载体两个字面量**。
4. 第二参被**归一化**过（mapping 变成 `RunConfig` 之类）⇒ MUST **逐字**传入（裁定 **12**）。

---

## 9. 闸口 V8 · `__start__` 条件边（三情形）

**目的**：`__start__` 上的条件边**被求值**（不是静默空跑）· 允许**纯条件边入口** ·
与静态入口**并存**时两目标**同轮并行**。

**命令**：

```bash
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edges.py -ra
```

**期望输出**：pytest 末行 `N passed` ⇒ 三类情形逐条成立：

| 情形 | 期望结果 |
|---|---|
| 条件边挂在 `__start__` 上 | 路由函数**确实被求值**（调用次数 == **1**）· 入口目标执行 **1** 次 |
| **纯条件边入口**（**无**静态入口点） | 允许 · 图**从路由结果起步** |
| 静态入口与 `__start__` 条件边**并存** | 两者的目标**同轮并行**（取并集）· **不**只跑静态入口那条 |
| `__start__` 条件边返回 `END` | 该分支**终止**（纯条件边入口 ⇒ 图**直接结束**） |

手工复核（纯条件边入口 · **11 行**）：

```python
from typing import TypedDict
from freegraph.graph import StateGraph, START, END
S = TypedDict("S", {"messages": list})
seen = []
def router(state): seen.append("router"); return "b"
g = StateGraph(S)
g.add_node("b", lambda s: seen.append("b") or {})
g.add_conditional_edges(START, router, ["b"])
g.compile().invoke({"messages": []})
assert seen == ["router", "b"], seen
print("__start__ 条件边 OK", seen)
```

**期望输出**（手工复核）：`__start__ 条件边 OK ['router', 'b']`
⇒ 路由函数**被调用了**（不是静默空跑）⇒ 且入口目标**照常执行**。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
__start__ 条件边 OK ['router', 'b']
```

**判据出处**：`SC-022` · `SC-023`（+ `FR-038` / `FR-039`）· 裁定 **17** ·
上游对照 **P-20**（SAME · 上游的 `__start__` 是真实伪节点）·
差分场景 `D-116`（挂在 `__start__` 上）· `D-117`（纯条件边入口）·
契约条款 `conditional-edge-contract.md` §2.4（`__start__` 相位）+ §7 **I-11**。

**失败排查**：

1. 路由函数**没被调用**（`seen == []`）⇒ 复现了「静默空跑」的缺陷 ⇒ 求值落点 MUST 在**阶段 ① 之前**。
2. 报「图必须有入口点」⇒ 纯条件边入口被拒 ⇒ `_validate_entrypoint` 的 `conditional_entry` 分支失效。
3. 并存时**只跑了静态入口**那条 ⇒ 未取并集 ⇒ 见裁定 **17** / 契约 §5「入口目标的投递」。
4. 返回 `END` 时整张图**还在跑** ⇒ 该分支未终止 ⇒ 见契约 §4.3。

---

## 10. 闸口 V9 · branch 名唯一

**目的**：同一源节点（含 `__start__`）登记**重名** branch ⇒ 内置 `ValueError`，
消息**点名**分支名与源节点。

**命令**：

```bash
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edges.py -ra
```

**期望输出**：pytest 末行 `N passed` ⇒ 且构造期抛错那条成立（**构造期** ⇒ 不是运行期）：

手工复核（**8 行**）：

```python
from typing import TypedDict
from freegraph.graph import StateGraph, START
S = TypedDict("S", {"messages": list})
g = StateGraph(S)
g.add_node("r", lambda s: {})
def router(state): return "r"
g.add_conditional_edges("r", router)
g.add_conditional_edges("r", router)   # 同源重名 ⇒ 构造期失败
```

**期望输出**（手工复核）：抛内置 **`ValueError`**，消息形如
`Branch with name `router` already exists at `r`` ⇒ 即**同时点名**了分支名 `router`
与源节点 `r` ⇒ 且 `__start__` **不特例化**（同款纪律）。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
ValueError: Branch with name `router` already exists at `r`
（**期望的失败** · 构造期显式失败）
```

**判据出处**：`SC-024`（+ `FR-040`）· 裁定 **18** · 上游对照 **P-21**（SAME）·
校验规则 **V-30** · 契约条款 `conditional-edge-contract.md` §2.1（签名与载体）+ §7 **I-12**。

**失败排查**：

1. 没抛错 ⇒ 分支名取自 `__name__` 的规则被改了 ⇒ 缺省名 MUST 仍为 `"condition"`（上游同款）。
2. 抛错但**消息没点名**分支名或源节点 ⇒ 消息口径不合（上游同款：两处都点名）。
3. 错误落在**运行期** ⇒ 校验被推迟 ⇒ MUST 在**构造期**（登记时）失败。

---

## 11. 闸口 V10 · 零副作用（路由通道 · 返回键集 · fresh 零污染）

**目的**：路由通道 `branch:to:<target>` **不被写入**（⇒ MUST **NOT** 触发 **V-6**）·
**不进** `invoke` 的返回键集 · fresh 读**零污染**。

**命令**：

```bash
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edges.py -ra
```

**期望输出**：pytest 末行 `N passed` ⇒ 逐条成立：

| 判定 | 期望 |
|---|---|
| **同轮两个源**节点路由到**同一目标** | **正常执行**（**不**抛 `InvalidChannelUpdateError`）⇒ 路由通道**零写入**的可判定证据 |
| `invoke` 返回的 key 集合 | == schema key 集合（**不含**任何 `branch:to:*`） |
| fresh 视图的 key 集合 | **不含**任何 `branch:to:*`（路由型通道**缺席**） |
| fresh 读**前后**逐通道快照 | `is_available()` 与 `get()` 的取值**不变**（**零污染**） |
| fresh 读的**范围** | 覆盖**整张通道表**（不是源节点的订阅集） |

手工复核（返回键集 · **11 行**）：

```python
from typing import TypedDict
from freegraph.graph import StateGraph, START
S = TypedDict("S", {"messages": list})
g = StateGraph(S)
g.add_node("r", lambda s: {"messages": ["r"]})
g.add_node("t", lambda s: {})
g.add_edge(START, "r")
g.add_conditional_edges("r", lambda s: "t", ["t"])
out = g.compile().invoke({"messages": []})
assert set(out) == {"messages"}, out
print("返回键集 OK", sorted(out))
```

**期望输出**（手工复核）：`返回键集 OK ['messages']`
⇒ 返回键集里**没有**路由通道 ⇒ 路由通道只作**声明载体**。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
返回键集 OK ['messages']
```

**判据出处**：`SC-011`（+ `FR-028`）· `SC-010`（+ `FR-011` / `FR-029`）· `SC-002`（+ `FR-002`）·
`SC-004`（+ `FR-012` / `FR-013`）· 偏离 **X-4**（DIFF · 结构差异 · 非更严）· 裁定 **8** ·
校验规则 **V-6** · 契约条款 `conditional-edge-contract.md` §3 + §5「路由通道不写」+
§7 **I-3** / **I-5** / **I-6**。

**失败排查**：

1. 同轮两源路由到同一目标抛 `InvalidChannelUpdateError` ⇒ 路由通道**被写入**了 ⇒ 触发 **V-6**。
2. 返回键集里出现 `branch:to:*` ⇒ 路由通道进了 schema key 集 ⇒ 判定 MUST 用
   `isinstance(channel, EphemeralValue)`（**MUST NOT** 用名称前缀启发式）。
3. fresh 视图里出现 `branch:to:*` ⇒ 同上 ⇒ 路由型通道 MUST **缺席**（契约 §3）。
4. 读完之后通道的 `is_available()` 变了 ⇒ fresh 读**污染**了通道 ⇒ 见契约 §3「零污染」。

---

## 12. 闸口 V11 · 路由函数异常**原样传播**

**目的**：路由函数抛出的异常以**原始类型 + 原始消息**到达调用方（不被包装 / 不被吞掉）。

**命令**：

```bash
uv run --no-project --python .venv python -m pytest tests/runtime/test_conditional_edges.py -ra
```

**期望输出**：pytest 末行 `N passed` ⇒ 「被**包装**成别的类型的次数 == **0**」。

手工复核（**14 行**）：

```python
from typing import TypedDict
from freegraph.graph import StateGraph, START
S = TypedDict("S", {"messages": list})
boom = RuntimeError("boom")
def router(state): raise boom
g = StateGraph(S)
g.add_node("r", lambda s: {})
g.add_edge(START, "r")
g.add_conditional_edges("r", router)
try:
    g.compile().invoke({"messages": []})
except RuntimeError as e:
    assert e is boom and str(e) == "boom", (type(e), str(e))
    print("异常原样传播 OK", type(e).__name__, e)
```

**期望输出**（手工复核）：`异常原样传播 OK RuntimeError boom`
⇒ 捕获到的**就是**路由函数抛出的**同一个对象**（`is` 成立）⇒ 类型与消息**逐字**一致。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
异常原样传播 OK RuntimeError boom
```

**判据出处**：`SC-012`（+ `FR-023`）· 裁定 **11** · 上游对照 **P-12**（SAME）·
差分场景 `D-112`（两侧类型与消息**逐字一致**）· 契约条款
`conditional-edge-contract.md` §6.1「路由函数自身抛出」+ §7 **I-9**。

**失败排查**：

1. 收到的是 `FreegraphError` 之类 ⇒ 异常被**包装**了 ⇒ MUST 原样传播。
2. 消息被改写（多了前缀）⇒ 消息**非原始** ⇒ MUST 原样传播。
3. 异常被**吞掉**（图「成功」结束）⇒ MUST NOT 吞掉 / MUST NOT 返回部分结果。

---

## 13. 闸口 V12 · 差分组 **D-103…D-120**

**目的**：条件边的路由判定与上游**同场景对跑**（**双真实实现**）⇒ **18** 条 ·
判词分布 SAME **12** / DIFF **3** / STRICTER **1**。

**命令**：

```bash
# ① 差分探针 CLI（场景表 + 判词）
uv run --no-project --python .venv python harness/scripts/diff_parity.py -v

# ② 计数（只数场景表行 · 锚定行首以避开 -v 的明细行）
uv run --no-project --python .venv python harness/scripts/diff_parity.py -v 2>&1 \
  | grep -cE "^[^ ].*D-1(0[3-9]|1[0-8])"

# ③ pytest 形态（CI 的 Linux 全量档真跑）
uv run --no-project --python .venv python -m pytest tests/differential/ -ra
```

**期望输出**：

| 项 | 期望值 |
|---|---|
| ① 的场景表里 **D-103…D-120** | **18** 条 · 逐条与 spec 的「差分场景组」表**一致** |
| ② 的计数 | **16** |
| 判词分布 | SAME **12** / DIFF **3**（`D-110` / `D-114` / `D-118`）/ STRICTER **1**（`D-111`） |
| STRICTER 那条 | **MUST 带 `note`**（写明「上游成功、freegraph 失败」的理由） |
| `D-107` / `D-113` 的断言口径 | **比对「异常类型」而非「异常消息」** ⇒ 消息更详细（**X-1**）由**单测**判定 |
| ③ 的 pytest 末行 | `N passed`（上游缺席时 ⇒ 差分用例被 **skip** ⇒ **不是失败**） |
| 探针末行 | `场景数 N · 符合判词 N · 失败 0` ⇒ 退出码 **0** |

**实测输出**（**2026-11-18 · T057 实测**）：

```text
30 passed in 22.79s
判词分布 = SAME 12 / DIFF 4 / STRICTER 2（判词非 SAME 的 6 条均带非空 note）
```

**判据出处**：`SC-013`（+ `FR-032`）· 裁定 **15**（落 `parity_probe.py` · **不**重造夹具接口）·
承接条款 **H-2 ①**（B5F2 夹具的 `conditional_edges` 字段**保持恒空**）·
上游对照 `contracts/upstream-parity.md` §3（差分场景索引）+ §4（偏离登记 **X-1…X-7**）·
契约条款 `conditional-edge-contract.md` §8（与上游的差异登记）。

**失败排查**：

1. `D-107` / `D-113` 红 ⇒ 逐字比对了**异常消息** ⇒ MUST 只比对**类型**（消息更详细是 **X-1**）。
2. `D-111` 红 ⇒ 无 `path_map` 的非法节点名仍**静默忽略** ⇒ 偏离 **X-3** 未落地。
3. `D-110` / `D-118` 红 ⇒ `END` **单独返回**时**不**是**无条件**终止 ⇒ 偏离 **X-2** 未落地。
4. `D-114` 红 ⇒ 第二参的**形态**（不是内容）与上游不同 ⇒ 检查是不是被归一化了。
5. 差分用例**全 skip** ⇒ 环境**未装** `differential` 组 ⇒ 装它（**MUST NOT** 把 skip 当已验证）。

---

## 14. 闸口 V13 · 破冻结面的**回溯验证**（**7 类**）

**目的**：本 feature 破的**全部**冻结面（**7 类**）按「**拆分而不删**」落地；
且 **4 类 MUST NOT 变红**的既有断言**保持绿**。

**命令**：

```bash
# ① V-8 守卫移除 + 冻结断言 ①（拆分而不删）
uv run --no-project --python .venv python -m pytest tests/runtime/test_superstep_basic.py -ra

# ② 冻结断言 ②（I-14 拆分 · 编号与槽位不变）
uv run --no-project --python .venv python -m pytest \
  tests/runtime/test_superstep_contract.py -ra

# ③ 冻结断言 ④（替换为反面断言）+ T-3（11 键持有面）
uv run --no-project --python .venv python -m pytest tests/facade/test_compiled_graph.py -ra

# ④ T-6：A5 组由软断言转**硬断言**（脚本退出码 0）
uv run --no-project --python .venv python harness/demo/graph_core.py

# ⑤ T-7：B1 / B2 组由软断言转**硬断言**（脚本退出码 0 · 工具循环轮）
uv run --no-project --python .venv python harness/demo/agent_loop.py

# ⑥ MUST NOT 变红的既有断言（T-2 / 冻结断言 ③）
uv run --no-project --python .venv python -m pytest tests/differential/test_differential.py -ra
```

**期望输出**：①…③⑥ 的 pytest 末行各为 `N passed`（**failed 0**）· ④ ⑤ 的脚本退出码 **0**
⇒ 且 `graph_core.py` 的 A5 组**不再**出现 `◌`（软断言标记）⇒ A5 三条（C8 fresh 读 /
C7 list 形态 / C7 dict 形态）**全部**是硬断言
⇒ 且 `agent_loop.py` 的 B1（工具循环）/ B2（`tool_calls` 形状）两组**不再**出现 `◌`
⇒ ⇒ ⇒ 五条断言（模型被调用 2 次 · `llm_calls == 2` · `messages` 长度 == 4 ·
最终答案是 `'7'` · `tool_calls` 结构）**全部**是硬断言。

| 破面类 | 落点 | 落地后的形态 |
|---|---|---|
| **T-1**（**V-8** 守卫移除） | `src/freegraph/runtime/superstep.py:484-487` | 构造期**不再**因 `conditional_edges` 非空而失败 |
| **冻结断言 ①** | `tests/runtime/test_superstep_basic.py:557-576` | **拆分**：非空 ⇒ 接受且原样承载 + 构造期**其它**失败路径逐条唯一 |
| **冻结断言 ②**（**I-14**） | `tests/runtime/test_superstep_contract.py:77` + `:609-617` | **拆分**：**I-14 编号与槽位不变**（契约守卫解析范围零改动）· 用例体改为「填值 ⇒ 构造成功且原样承载」 |
| **冻结断言 ④** | `tests/facade/test_compiled_graph.py:263-265` | **替换为反面断言**：非空**且**与 `compiled._conditional_edges` **逐字相等** |
| **T-5**（C8 挂载点） | `tests/contracts/test_contract_regressions.py:36` | `status=landed` + 新增 C8 元测试（详见 **V2**） |
| **T-6**（A5 软断言） | `harness/demo/graph_core.py:254-321` | 全部 `soft(...)` ⇒ **硬断言**（`check` / `eq`）⇒ 删除「未交付」措辞 |
| **T-7**（`agent_loop.py` 的 B1 / B2 软断言） | `harness/demo/agent_loop.py:214-262` | 全部 `soft(...)` ⇒ **硬断言**（`eq`）⇒ 删除 `_B8F1_NOTE` 的「未交付」措辞 · 保留五条断言的**语义** · ⚠️ **时序**：MUST 在条件边路由求值就位**之后** |

| MUST NOT 变红 | 锚点 | 期望 |
|---|---|---|
| **T-2**（**V-4**） | `tests/differential/spec_builder.py:122-126` | **绿**（B5F2 夹具的 `conditional_edges` 字段**保持恒空**） |
| **冻结断言 ③** | `tests/differential/test_differential.py:123-132` | **绿**（原断言**逐字不动**） |
| **T-3**（11 键持有面） | `tests/facade/test_compiled_graph.py:111-114` | **绿**（`vars(compiled)` 仍 == **11**） |
| **T-4**（只读基准 diff） | `harness/demo/target.py` | **一字不改**（G29 的 diff 断言恒绿） |

**实测输出**（**2026-11-18 · T057 实测**）：

```text
115 passed, 1 skipped in 0.88s
graph_core.py ⇒ 断言 36 条 · 通过 36 · 失败 0 · rc=0
agent_loop.py ⇒ 断言 14 条 · 通过 14 · 失败 0 · rc=0
```

**判据出处**：`SC-015`（A5 硬断言）· `SC-025`（`agent_loop.py` 的 B1 / B2 硬断言）· `SC-016`（11 键 + `target.py` 未改）· `SC-019`（**唯一一次**追认）·
plan「变红清单」**7 项**（变红断言 · ⚠️ **≠ 破面全集 7 类** —— ⚠️ **两个「7」不是同一组**：本行的 ⑦ 是**差分侧既有守卫**，spec 的 ⑦ 是 **T-7**） + 「MUST NOT 变红的既有断言」**4 类** · 登记项 **R-1**（追认次数 == **1**）·
spec「破冻结面的回溯修订清单」· 契约条款 `conditional-edge-contract.md` §6.2（**V-8** 已放宽）。

**失败排查**：

1. ① 红 ⇒ 冻结断言 ① **没拆**（只删不拆 ⇒ 判据被放宽）⇒ MUST「拆分而不删」。
2. ② 红且报「I-14 缺失」⇒ 槽位被挪动 ⇒ **编号与槽位 MUST 不变**。
3. ③ 红 ⇒ 冻结断言 ④ 没换成**反面断言**（仍是「恒空」⇒ 与接线后的事实矛盾）。
4. ④ 的 A5 组出现 `◌` ⇒ 软断言**没转硬** ⇒ T-6 未落地。
5. ⑤ 的 B1 / B2 组出现 `◌` ⇒ 软断言**没转硬** ⇒ T-7 未落地（⇒ ⇒ ⇒ ⚠️ **时序**：过早硬化 ⇒ 永久红 CI）。
6. ⑥ 红 ⇒ 碰了 B5F2 的差分夹具接口 ⇒ MUST **不重造夹具**（裁定 **15**）。

---

## 15. 闸口 V14 · 零新增面

**目的**：公开面与编译产物持有面**一字不动** ⇒ 兼容矩阵**零新增行**。

**命令**：

```bash
uv run --no-project --python .venv python - <<'PY'
from typing import TypedDict
import freegraph.contracts as c, freegraph.graph as g, freegraph.runtime as r
from freegraph.graph import StateGraph, START
S = TypedDict("S", {"messages": list})
b = StateGraph(S)
b.add_node("a", lambda s: {})
b.add_edge(START, "a")
print("契约层 =", len(c.__all__), "· 门面 =", len(g.__all__), "· runtime =", len(r.__all__))
print("持有面键数 =", len(vars(b.compile())))
PY
```

**期望输出**：

```
契约层 = 21 · 门面 = 7 · runtime = 23
持有面键数 = 11
```

⇒ **7**（门面）/ **23**（runtime）/ **21**（契约层）/ **11**（`vars(compiled)` 的键数）
四个数字**全部不变** ⇒ 兼容矩阵**零新增行** ⇒ 门禁 **G7 / G15 / G19** 恒绿。

⚠️ **断言口径**：`freegraph.runtime.__all__` 的判定 MUST 以
**`tests/runtime/_runtime_export_manifest.py` 的 `RUNTIME_EXPORT_SYMBOLS` 清单**为准
（导出面清单的**单一事实源**）⇒ 断言写成「**符号集合 == 清单**」，
**MUST NOT** 另抄一份硬编码数字 ⇒ 新模块 `src/freegraph/runtime/_routing.py` 是
**L2 私有** ⇒ **不进** `__all__`。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
contracts 21 | facade 7 | runtime 23
vars(compiled) == 11 键 · freegraph.runtime.errors 的符号集合不变
```

**判据出处**：`SC-016`（+ `FR-037` / `FR-026` / `FR-027`）· `SC-018`（+ `FR-033` · 零新增错误类型）·
契约 §7 **I-13**（零新增公开面）/ **I-14**（零新增错误类型）· 契约 §9（零新增面声明）·
破冻结面 **T-3 不破** · 门禁 **G25** / **G30**（新模块自动纳入扫描与署名头扫描）。

**失败排查**：

1. `runtime = 24` ⇒ 新模块被加进了 `__all__` ⇒ `_routing.py` MUST 是**私有**。
2. `持有面键数 = 12` ⇒ 新增了编译产物私有字段 ⇒ MUST 复用既有的 `_conditional_edges` 与 `_spec`。
3. `契约层 = 22` ⇒ 契约层被扩了 ⇒ 本 feature **零新增公开符号**。

---

## 16. 闸口 V15 · 零出站 · 零环境变量 · 零第三方依赖

**目的**：路由求值全过程**零出站** · **零环境变量读取** · `sys.modules` 里**零**上游。

**命令**：

```bash
# ① 既有门禁（配置层 / 网络静态 / 零出站动态）
uv run --no-project --python .venv python harness/scripts/gates/gate_G24_config_layer.py
uv run --no-project --python .venv python harness/scripts/gates/gate_G26_network_static.py
uv run --no-project --python .venv python harness/scripts/gates/gate_G27_zero_egress.py

# ② 内核路径零上游 import
grep -rn "import langgraph\|import langchain\|from langgraph\|from langchain" src/freegraph/ \
  || echo "OK：无上游导入"

# ③ 发行元数据零依赖包
uv run --no-project --python .venv python -c \
  "import importlib.metadata as m; print(m.requires('freegraph') or [])"
```

**期望输出**：① 三条门禁**全部**退出码 **0** · ② 输出 `OK：无上游导入` · ③ 输出 `[]`
⇒ 且 `pytest tests/runtime/test_conditional_edges.py -ra` 里
「一次完整 `invoke`（含条件边求值）之后 `sys.modules` 中
`langchain` / `langchain_core` / `langgraph` / `langsmith` 的出现次数 == **0**」这条**成立**。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
[G21] PASS · [G22] PASS · [G23] PASS · [G24] PASS · [G25] PASS · [G26] PASS · [G27] PASS（框架出站 = 0）· [G28] PASS · [G29] PASS
[G30] ⚠️ FAIL（**既存** · 8 条违规 · 在 pristine `HEAD` 树上同样复现 ⇒ 非本 feature 的回归）
```

**判据出处**：`SC-017`（出站连接数 == **0** · 环境变量读取次数 == **0**）·
`SC-018`（`sys.modules` 零上游）· `FR-033` · 上游对照 **P-18**（SAME）· 宪法原则 I / X ·
契约 §8「依赖」行（**零新增**）· 门禁 **G3 / G21 / G23 / G24 / G26 / G27**。

**失败排查**：

1. ② 命中 ⇒ 内核 import 了上游 ⇒ 运行时依赖闭包**不再为空** ⇒ 门禁 G3/G21/G23 变红。
2. ③ 非 `[]` ⇒ 发行元数据被扩了 ⇒ `pyproject.toml` MUST **零改动**。
3. ②/③ 都绿但 `sys.modules` 里有上游 ⇒ 是**差分侧**把上游导进了同一进程
   ⇒ 差分导入 MUST 延迟到用例运行时（`tests/differential/conftest.py` 的既有纪律）。

---

## 17. 闸口 V16 · 人工验证记录 + 发起者追认

**目的**：人工验证记录 MUST 存在且**正文非空**（五段式 + 来源覆盖表）⇒ 门禁 5 + 原则 V；
**唯一一次**破面追认 MUST 落在同一份记录里。

**命令**：

```bash
# ① 记录存在且正文非空
test -s harness/verification/B8F1/manual-verification.md && echo "记录存在且正文非空"

# ② 五段式小节 + 追认 + 真实轮声明
grep -n "^## " harness/verification/B8F1/manual-verification.md
grep -n "B25F1" harness/verification/B8F1/manual-verification.md
```

**期望输出**：① 打印 `记录存在且正文非空`；② 的小节清单 MUST 含
**验证环境** · **验证步骤** · **实际输出** · **结论** · **遗留问题**（五段式）·
外加**来源覆盖表**与**发起者追认**一节 ⇒ 且 `B25F1` **至少命中一行**。

⚠️ **真实模型一轮在本 feature 物理不可达成**（需真实模型 + 厂商端点 ⇒ 本环境不具备）
⇒ 记录里 MUST **显式写明该项未落地**并写明**承接方 = B25F1（M4）**
（plan 登记项 **R-2** ② · 宪法 v1.6.0 的「环境偏离」登记）
⇒ **MUST NOT** 用「未验证」替代「已登记的环境偏离」⇒ **MUST NOT** 伪造实测输出。
⚠️ **fake 模型轮 MUST 跑通**（`harness/demo/graph_core.py` 零第三方依赖 ⇒ 本 feature 可达）⇒
**判据本身不放宽**。

**实测输出**（**2026-11-18 · T057 实测**）：

```text
记录存在且正文非空（harness/verification/B8F1/manual-verification.md · 五段式 + 来源覆盖表 + 两轮实测输出 + 追认文字含破面全集 7 类）
追认签署：⏳ **待发起者签署**（MUST NOT 由实现者代签 · 宪法 v1.6.0）⇒ **合入闸口 G5 未打开**
```

**判据出处**：`SC-020`（记录存在且正文非空 + 覆盖 fake / 真实两轮的实测输出）·
`SC-019`（**唯一一次**追认 · 合入前完成率 == **100%** · 追认次数 == **1**）·
plan 登记项 **R-1**（破面追认）/ **R-2**（分阶段延后）· 宪法原则 V / v1.6.0 / v1.8.0 ·
契约 §8「零新增面」行（人工记录里 MUST **显式记「零新增」**）。

**失败排查**：

1. `test -s` 失败 ⇒ 记录缺失或**正文为空** ⇒ 守卫 MUST 在记录写就之后才转绿（**MUST NOT** 永久红）。
2. 缺五段式之一 ⇒ 人工门禁的判定覆盖不成立 ⇒ 按 §18 的模板补齐。
3. 真实轮写成「已验证」但**无实测输出** ⇒ 属伪造 ⇒ MUST 改为「**已登记的环境偏离** + 承接方 B25F1」。
4. 追认文字缺失 ⇒ **未追认前 MUST NOT 合入** ⇒ 追认 MUST 由**发起者**签署（**MUST NOT** 由实现者代签）。

---

## 18. 人工验证记录模板（`harness/verification/B8F1/manual-verification.md`）

> ⚠️ 本模板**只给骨架与必须填的清单** ⇒ **MUST NOT** 替用户写结论、
> **MUST NOT** 伪造实测输出 ⇒ 每一处「实测输出」MUST 由**实跑**填入。

```markdown
# B8F1 · 条件边路由求值 + `END` 终止 + fresh 读 · 人工验证记录

**Feature**: `specs/b8f1-conditional-edges-fresh-read/` · **日期**: <YYYY-MM-DD>
**上游**: `langgraph 1.2.11`（开发 / 测试侧差分依赖；不在发行面）

## 1. 验证环境

| 项 | 值 |
|---|---|
| Python | <实测版本号> |
| 平台 | <实测平台> |
| freegraph | 源码树（`PYTHONPATH=src`） |
| 上游差分依赖 | `langgraph <版本>` / `langchain-core <版本>` |
| 第三方运行时依赖 | **零**（`dependencies = []`） |
| 绿基线（实施前） | passed <N> · skipped <N> · failed <N> |

## 2. 验证步骤

<!-- 逐条抄本手册 §2…§17 的闸口命令（可复制）· 每条 MUST 写明闸口号 -->

## 3. 实际输出

<!-- ⚠️ MUST 粘贴**实跑**的原始输出 · MUST NOT 伪造 · MUST NOT 只写「一致」 -->

### 3.1 V1 · C8 fresh 读（否定式断言）
<!-- 粘贴 pytest 末行 + 手工复核的 print 输出 -->

### 3.2 V2 · C8 挂载点（`landed`）+ 元测试 + 门禁 G29
### 3.3 V3 · `END` 终止（含与上游的分叉 D-110 / D-118）
### 3.4 V4…V9 · 目标解析 / 失败信号 / 双参 / `__start__` / branch 名
### 3.5 V10 / V11 · 零副作用（路由通道零写入 · 返回键集 · 零污染）/ 异常原样传播
### 3.6 V12 · 差分组 D-103…D-120（18 条 · 判词分布 SAME 12 / DIFF 4 / STRICTER 2）
### 3.7 V13 · 破冻结面回溯验证（**7 类**）与 MUST NOT 变红的既有断言（4 类）
### 3.8 V14 / V15 · 零新增面 / 零出站
### 3.9 fake 模型轮（猴补 `init_chat_model` + 含条件边的最小图 / `agent_loop.py` 工具循环轮 · 含条件边路由的**非空**实测输出）

## 4. 结论

<!-- 逐条对照 SC-001…SC-026 · MUST 由实跑支撑 · MUST NOT 预写「通过」 -->

## 5. 遗留问题

### 5.1 **真实模型一轮 —— 未落地 · 承接方 B25F1（M4）**

<!-- MUST 显式写明：
     ① 本 feature **物理不可达成**（需真实模型 `claude-sonnet-4-6` + 厂商端点
        ⇒ 出网 + 凭据 ⇒ 本仓库的 CI / 门禁环境不具备）；
     ② 依宪法 **v1.6.0**「质量门禁的分阶段落地」登记为**环境偏离**
        ⇒ **MUST NOT** 用「未验证」替代「已登记的环境偏离」；
     ③ **fake 模型轮仍 MUST 跑通**（判据本身**不放宽**）· 见 §3.8；
     ④ **承接方 = B25F1（M4）** · 机制 = 本 feature 的下游承接 **D-5**
        （fake 注入与路由函数**正交**）⇒ 由 B25F1 的 spec 落成 FR + 裁定。 -->

### 5.2 其它遗留项

<!-- 未实跑 / 未达成的项 MUST 逐条列出 · MUST NOT 留空 -->

## 6. 来源覆盖表

<!-- 判据 / SC / FR 各一张 · 覆盖率 == 100% · 逐条指向 §3 的实测输出 -->

## 7. 破冻结面的**发起者追认**（**唯一一次**）

<!-- 追认文字 MUST 覆盖破面全集 **7 类**（T-1 / 冻结断言 ① / ② / ④ / T-5 / T-6 / **T-7**）
     · 发起者确认 · 日期 · **MUST NOT** 由实现者代签 -->

## 8. 零新增面声明

<!-- MUST 显式记「零新增」：门面 7 / runtime 23 / 契约层 21 / vars(compiled) == 11
     · 兼容矩阵零新增行 · 门禁编号仍为 30（G1–G30） -->
```

---

## 19. 常见问题

| 症状 | 原因 | 处置 |
|---|---|---|
| 路由函数**没被调用** | 条件边载荷没接线（`GraphSpec.conditional_edges` 恒空） | 见契约 §1「载荷载体」+ V-8 已放宽 |
| 路由函数读到**旧值** | 求值落点晚于写入合并 | 见契约 §2.1 · 落点 MUST 在阶段 ③′ |
| 路由函数**被调用两次** | 同一轮里被重复求值 | 见契约 §2.4「每源每次一次」 |
| `END` 抛 `KeyError` | `END` 判定被放在 `path_map` 查表之后 | 见契约 §4.3 · MUST **无条件**终止 |
| `f(state, cfg)` **没报错** | 凭位置参数个数补传了第二参 | 见裁定 **16** · MUST 按**参数名**判别 |
| 差分用例**全 skipped** | 环境**未装** `differential` 组 | 装它（**MUST NOT** 把 skip 当已验证 · SC-013） |
| `D-107` 红 | 逐字比对了**异常消息** | MUST **只比对异常类型**（消息更详细是 **X-1**） |
| 同轮两源路由到同一目标抛 `InvalidChannelUpdateError` | 路由通道**被写入**了 | 路由通道 MUST **不被写入**（裁定 **8** · **X-4**） |
| A5 组仍显示 `◌` | T-6 未落地（软断言没转硬） | 见 §14 · 硬断言必须排在条件边求值**就位之后** |
| 门禁 G29 报「只读基准 diff 不一致」 | `harness/demo/target.py` 被改了 | **T-4 不破** ⇒ MUST 回退 |
