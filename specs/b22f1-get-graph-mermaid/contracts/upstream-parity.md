# 与上游 LangGraph 的逐条对照（图导出 / mermaid）

**Feature**: `B22F1` · **契约**: [graph-export-contract.md](./graph-export-contract.md) ·
**取证**: [../research.md](../research.md)
**核实环境**: 上游 `langgraph` **1.2.11** + 同批 `langchain-core`
（用户 site-packages · **非仓库依赖**）· CPython **3.11 / 3.12** · 取证于 **2026-11-20**
⚠️ **换上游版本后 MUST 重新核实全部行号**（宪法原则 VIII）。
⚠️ **本文件是「证据」载体** ⇒ **MUST NOT** 被测试解析（测试直接断言行为）。

---

## §1 逐条对照（P-01…P-19）

| # | 语义点 | 上游（版本 + `路径:行号`） | freegraph | 关系 | 理由 / 证据 |
|---|---|---|---|---|---|
| **P-01** | `get_graph` 入口 | `langgraph/pregel/main.py:845-870`：`get_graph(config=None, *, xray=False)`；返回 `draw_graph(...)` | `get_graph(*, xray=False)`；v1 无子图；返回自有 `Graph` | **DIFF** | 无 `config`；C26 v1 不实现；E-1 |
| **P-02** | 节点集合 | `_draw.py:225-236` 业务节点 + `START`；`:292-293` 需要时补 `END` | 业务节点 + `__start__` + `__end__`；顺序 start → 业务 → end | **SAME** | E-1 / E-7 |
| **P-03** | 静态边 | `_draw.py:236` START→入口；`:247-256` 终结→END；普通实线 | 静态边逐条；含 START / END；普通实线 | **SAME** | E-1 / E-2 |
| **P-04** | `add_conditional_edges` | `_draw.py:138-151`；`:256` `conditional=True`；渲染虚线（`graph_mermaid.py:159-164`） | 逐目标成边、`conditional=True`、`condition=branch`、虚线 | **SAME（结构）/ DIFF（标签）** | 上游 `data=None`；freegraph 用 branch（X-09）；E-2 |
| **P-05** | `draw_mermaid` 入口 | `graph_mermaid.py:45`：`draw_mermaid(nodes, edges, ...) -> str` | `Graph.draw_mermaid() -> str` | **DIFF** | 自有 `Graph` 已持有节点 / 边（C13） |
| **P-06** | mermaid 节点 id | `graph_mermaid.py:255-266`：保留 `[A-Za-z0-9_-]`，其它 → `\` + 小写 hex | **逐字同款** | **SAME** | E-14 |
| **P-07** | mermaid 头部 / 样式 | 默认 `with_styles=True` ⇒ YAML frontmatter + `graph TD;` | 仅 `graph TD;`，无 frontmatter | **DIFF** | 零依赖 / 确定性（X-05） |
| **P-08** | 标签转义 | 仅安全化 id；标签引号 / 换行未系统转义 | **STRICTER**：标签额外转义 `"` / 换行 / `<` / `>` / `&` / `\|` / `\` / `#` | **STRICTER** | 始终合法（X-04） |
| **P-09** | 动态目标来源 | `graph/state.py:810-861` 返回注解推断；`:860-861` `destinations` 覆盖；`:1780-1788` `_control_static` | **逐字同款**：`Command` 泛型 + 推断 + `destinations` 覆盖；无运行期记录 | **SAME** | 2026-11-20 发起者裁定；E-3 / E-4 / E-5 |
| **P-10** | 是否模拟执行 | `_draw.py:42` 以受限轮次模拟 Pregel（不执行节点） | 静态快照 + 静态可达闭包，**零执行** | **DIFF** | X-08；E-7 / E-9 |
| **P-11** | PNG 外呼 | `graph_mermaid.py:277`；`:422-423` 默认 `https://mermaid.ink` | 本 feature 不交付 PNG；文本零网络 | **STRICTER** | 原则 I；C15 归 B23F1 |
| **P-12** | 节点 / 边类型 | `langchain_core/runnables/graph.py:65`（Edge）/ `:95`（Node）/ `:255`（Graph） | 同名自有实现（`freegraph.contracts.graph`） | **DIFF** | 原则 I / IX |
| **P-13** | 节点 metadata | `_draw.py:221-229`：拷贝 metadata；`defer`；`__interrupt` | **逐字同款** | **SAME** | E-11 |
| **P-14** | 终结补 END | `_draw.py:247-257`：`termini` → 普通 END；无边且末步单源 → 条件 END | 可达无出边节点 → 普通 END；**不复制**末步单源启发式 | **SAME（常规）/ DIFF（末步单源：自环 / 循环）** | E-2 / E-9 / E-10 / E-12；X-08 |
| **P-15** | 边去重 | `_draw.py:286-288`：按 `(source,target)`；实测条件 / 声明优先 | 按 `(source,target)`；`conditional=True` 优先；同级先出现 | **SAME** | E-13 / E-15 |
| **P-16** | `destinations` 标签 / 执行影响 | `state.py:404-410`：dict 键 = 目标、值 = 标签；tuple = 目标（运行期亦接受 list）；仅渲染 | **逐字同款**；dict 标签 → `condition`；序列 → `None` | **SAME** | E-4 / E-4b / E-4c |
| **P-17** | 声明目标存在性 | `state.py:1150-1162`：不在 nodes 且非 END ⇒ `ValueError` | **逐字同款**（编译期） | **SAME** | E-6 |
| **P-18** | 边可达性 | `_draw.py:42-214`：模拟只发现可达边；不可达节点只进节点表 | 静态边组闭包；只导出可满足组 | **SAME** | E-7 / E-9 |
| **P-19** | 多源 join 渲染 | `graph/state.py:1551-1561` 建 join；`_draw.py` 每源各发现一条普通边 | 每源一条普通 `Edge`；全源可达才导出 | **SAME** | E-8 / E-9 |

---

## §2 偏离登记（X-01…X-13）

| # | 类别 | 偏离点 | freegraph 口径 | 上游 | 理由 / 追认 |
|---|---|---|---|---|---|
| **X-01** | 破冻结面 | `Command` 非泛型 | `Generic[N]` | `Command(Generic[N])` | 发起者 2026-11-20；T-1 |
| **X-02** | 破冻结面 | `add_node` 无 `destinations` | 接受 `Sequence[str]` / `dict[str,str]` | 接受 `tuple` / `dict` | 发起者 2026-11-20；T-2 |
| **X-03** | 自研区 / 破冻结面 | 快照缺 END / metadata / defer / destinations | 只读 `_builder_spec` 补齐 | 从活对象模拟 | 不重跑 `_build_spec`；T-3 |
| **X-04** | 更严输出约束（STRICTER） | 标签系统转义 | 是 | 否 | 始终合法 mermaid |
| **X-05** | 自研区 | 无 frontmatter / 样式参数 | 最小文本 | 默认 frontmatter | 零依赖 / 确定性 |
| **X-06** | 自研区 | 无子图穿透 | `xray` 仅签名 | 递归子图 | C26 v1 |
| **X-07** | 破冻结面 | `Edge.condition` 非空 | 无标签声明边 `None` | `Edge.data=None` | 发起者 2026-11-20；T-6 |
| **X-08** | 自研区 / DIFF | 不模拟执行 | 静态闭包 | Pregel 模拟 + 末步单源 + 250 截断 | 零执行 / 零副作用 |
| **X-09** | 自研区 / DIFF（标签） | 条件边标签 | `condition=branch` | `data=None` | prompt 要求虚线 + 标签 |
| **X-10** | 自研区（DIFF） | `get_graph` 的 `config` / 子图入口 | `get_graph(*, xray=False)` | `get_graph(config=None, *, xray=False)` | C26 v1 不实现；P-01 |
| **X-11** | 自研区（DIFF） | `draw_mermaid` 入口形态 | `Graph.draw_mermaid()` | `draw_mermaid(nodes, edges, ...)` | 自有 `Graph` 已持有节点 / 边；P-05 |
| **X-12** | 自研区（DIFF · C13 强制重写） | 节点 / 边类型 | `freegraph.contracts.graph` 自有类型 | `langchain_core.runnables.graph` | 原则 I / IX；P-12 |
| **X-13** | 更严输出约束（STRICTER） | PNG 外呼 | 文本零出站；PNG 归 B23F1 | `mermaid.ink` 默认外呼 | 原则 I；P-11 |

**X ↔ P 对应**：X-01↔P-09 · X-02↔P-16 · X-03↔P-10/P-13 · X-04↔P-08 · X-05↔P-07 ·
X-06↔P-01 · X-07↔P-04/P-16 · X-08↔P-10/P-14 · X-09↔P-04 · X-10↔P-01 · X-11↔P-05 ·
X-12↔P-12 · X-13↔P-11。

---

## §3 差分场景组（D-01…D-15）

> 落点：`tests/differential/parity_probe.py`；上游缺席即 skip（沿用 B5F2 纪律）。
> 上游对照只断言**结构语义**（节点名集合 / 边端点 / 条件标记）；**MUST NOT** 断言
> mermaid 文本逐字相等。

| # | 场景 | 断言 | 判词 |
|---|---|---|---|
| **D-01** | 线性 `START→a→b→END` | 业务节点 `{a,b}`；`__start__→a`、`a→b`、`b→__end__` | SAME |
| **D-02** | 条件边 `a --route--> {b, END}` | `a→b` / `a→__end__` 均 `conditional=True`；freegraph `condition=="route"`（上游 data 不参与） | SAME |
| **D-03** | 同源多分支 | 每分支每目标各一条；分支名正确 | SAME |
| **D-04** | 特殊字符节点名 | 所有节点可判定出现；文本合法（安全 id + 转义） | STRICTER |
| **D-05** | `Command[Literal["b","c"]]`（不运行） | `a→b` / `a→c` 各一条；`condition is None` | SAME |
| **D-06** | `destinations={"b":"to-b","c":"to-c"}` | 两条边；标签正确；覆盖注解 | SAME |
| **D-07** | 声明未知目标 | 两侧编译期 `ValueError`，消息含目标名 | SAME |
| **D-08** | 运行前 vs 运行后导出 | `nodes` / `edges` 逐项相等 | SAME |
| **D-09** | `xray=True` vs `False` | 逐项相等 | SAME |
| **D-10** | `stream()` 后导出 | 与之前逐项相等 | SAME |
| **D-11** | 不可达节点 | 两侧节点表含它；出边都不出现 | SAME |
| **D-12** | 末步单源（单节点自环 **或** 两节点循环） | 上游多一条末步源 `→__end__` 条件边（自环 = `a`；循环 = `b`）；freegraph 无 | DIFF（X-08） |
| **D-13** | join `["a","b"]→c`（两源可达） | 两侧 `a→c` + `b→c` 普通边 | SAME |
| **D-14** | join 其一源不可达 | 两侧无该组边；可达源补 `→__end__` | SAME |
| **D-15** | 同端点静态 + 条件 / 声明 | 只一条，且 `conditional=True` | SAME |

**图导出场景的执行口径**（T023 / T042）：

- 新增 `GraphScenario` + `_run_graph_scenarios()`，**不**复用 `CompileScenario` /
  `InvokeScenario`（后者不比较 `Graph.nodes` / `Graph.edges`）；
- 比较键：节点 id 集合 / 边 `(source,target,conditional,condition)` 集合；
- `D-04` 的 `STRICTER` 判据 = freegraph mermaid 文本通过 §5.5 合法性断言（**不**与上游
  文本逐字比较）；`D-12` 必须**显式断言**「上游有额外边、freegraph 无」，不能只靠 `note`；
- 入口测试：`tests/differential/test_parity_probe.py`；T042 MUST 跑该文件。

---

## §4 实测基线（E-1…E-16）

> 取证于 2026-11-20 · `langgraph 1.2.11`；完整输出见 [../research.md](../research.md) §2。

| # | 场景 | 实测要点 |
|---|---|---|
| E-1 | 线性 + 条件 | 节点 / 边集合见 D-01 / D-02 |
| E-2 | 条件标记 + 终结 END | `a→b`(True), `a→__end__`(True), `b→__end__`(False) |
| E-3 | `Command[Literal]` | `a→b` / `a→c`(True,None)；循环末步单源额外 `a→__end__`(True) |
| E-4 | `destinations` dict / tuple / list | 标签 `to-b` / `to-c`；序列为 None；list 接受 |
| E-5 | `destinations` 覆盖 | 仅 `a→c`(True,'only-c') |
| E-6 | 未知目标 | `ValueError: Found edge ending at unknown node \`nope\`` |
| E-7 | 不可达节点 | 节点 `d` 在；出边无 |
| E-8 | join 两源可达 | `a→c` / `b→c`(False) |
| E-9 | join 一源不可达 | 组边无；`a→__end__` |
| E-10 | 单源自环 | `a→a`(False) + `a→__end__`(True) |
| E-11 | metadata | `{'k':'v','defer':True,'__interrupt':'before'}` |
| E-12 | 两节点循环（末步单源） | `a→b` / `b→a`(False) + `b→__end__`(True)；X-08 |
| E-13 | 声明覆盖静态 | `a→b`(True,'cond') |
| E-14 | 安全 id | `a"b` → `a\22b`；`x\ny` → `x\ay` |
| E-15 | 条件覆盖静态 | `a→b`(True,None) |
| E-16 | 目标 mermaid 形态 | `graph TD;` + 节点行 + 实线 / 虚线 |

---

## §5 与 spec 的三表一致性

| 检查 | 结果 |
|---|---|
| 上游对照表（P）与偏离登记（X）逐条对应 | ✅ |
| 差分场景组（D）覆盖所有 X / STRICTER / DIFF | ✅（D-04 / D-12 / D-15） |
| 无「未登记的分叉」 | ✅ |
| 换版本重核义务 | P 表头已写明 |
