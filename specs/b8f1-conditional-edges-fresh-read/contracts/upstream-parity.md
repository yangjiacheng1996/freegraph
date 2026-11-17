<!-- authority: yes -->

# 上游对照契约（Upstream Parity）—— B8F1

**Feature**: `B8F1` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**取证记录**: [../research.md](../research.md) · **契约权威**:
[conditional-edge-contract.md](./conditional-edge-contract.md)
**上游版本**: `langgraph` **1.2.11** + `langchain-core` **1.7.6**（取证于 **2026-11-17**）

> ⚠️ **本文件是「上游对照 + 差分索引 + 偏离登记」的落点** —— 它与
> [../spec.md](../spec.md) 的「Upstream Parity」表 / 「差分场景组」表 / 「偏离登记」表
> 是**同一份内容的两处落点** ⇒ ⇒ ⇒ **发现漂移 MUST 双侧同改**（见 §7）⇒ ⇒ ⇒
> **MUST NOT** 只改一侧。
> ⚠️ **判据的唯一权威** = [conditional-edge-contract.md](./conditional-edge-contract.md)
> ⇒ 本文件是**证据表** ⇒ **MUST NOT** 被测试解析（测试**直接断言行为** ⇒
> 避免「判据与实现同源 ⇒ 自证」）。
> ⚠️ **换上游版本 ⇒ MUST 重新核实全部锚点并改写版本号**（宪法原则 VIII · 原则 XI）。

---

## 1. 取证环境与纪律

### 1.1 取证环境

| 项 | 值 | 核实方式 |
|---|---|---|
| 上游版本 | `langgraph` **1.2.11** · `langchain-core` **1.7.6** | `importlib.metadata.version`（本仓库 `.venv`） |
| 版本钉死 | `pyproject.toml:100`（`"langgraph==1.2.11"`）· 属 **PEP 735 的 `differential` 依赖组**（`:99-101`） | 读文件 |
| 取证方式 | 仓库 `.venv` 的 `differential` **开发组**（**非**运行时依赖）⇒ 探针脚本置于**仓库之外**的干净目录 | [../research.md](../research.md) §0.1 / §0.2（探针 `p1`…`p8`） |
| 仓库改动 | **零** ⇒ `pyproject.toml` **零改动** ⇒ **运行时依赖闭包仍为空**（`:43` 的 `dependencies = []`） | `git status --porcelain` |
| 上游包根 | `.venv/lib/python3.11/site-packages/langgraph/` | —— |
| 零依赖面 | 内核 `src/freegraph/**` 对 `langchain` / `langchain-core` / `langgraph*` / `langsmith` 的 import 数 == **0** | `src/freegraph/**` 的 **AST** import 扫描（见 §8） |

> ⚠️ **差分组 ≠ 运行时依赖**：`langgraph` 属**开发组**（`pyproject.toml:99-101`）
> ⇒ ⇒ ⇒ `pyproject.toml` **零改动** ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿
> （宪法原则 II · 原则 X）。

### 1.2 纪律（宪法原则 VIII · 原则 XI「上游锚点纪律」）

| # | 纪律 | 落点 |
|---|---|---|
| **R-1** | 每条**事实性结论** MUST 附 `路径:行号`（上游用上游路径 · freegraph 用仓库路径） | 本文件 §2 的「上游锚点」列 · §1.1 的「核实方式」列 |
| **R-2** | **行为**断言 MUST 有**实测**支撑 —— ⚠️ **只读源码不足以支撑行为断言** | 本文件 §2 的「实测编号」列 · §3 的「实测编号」列（**E-n / M-x / N-x / P-x**） |
| **R-3** | 上游**有答案** ⇒ **照抄** ⇒ 不问用户；上游**自身无定论** ⇒ 取**更确定**的一侧 ⇒ 如实登记偏离 | §4 的 **X-1…X-7**（原则 XI ② 类） |
| **R-4** | **上游版本变化时 MUST 重新核实全部锚点并改写版本号**（`pyproject.toml:100` 钉死） | §6 的「结构面断言清单」是重跑的**最小集** |
| **R-5** | 同一分叉在「上游对照」与「偏离登记」两处的**三态标注 MUST 逐字一致**（原则 XI 末条 · v1.12.0） | §5 的「三态一致性对照表」 |

---

## 2. 上游对照表（**P-01 … P-23** · 共 **23** 条）

> **列的读法**：「上游锚点」列 = `langgraph 1.2.11` 的 `路径:行号` + **实测编号**；
> 「关系」列 = **三态**（`SAME` / `STRICTER` / `DIFF`）· **逐字**与
> [../spec.md](../spec.md) 的「Upstream Parity」表一致 ⇒ **MUST NOT** 改判词。

| # | 语义点 | 上游锚点（`langgraph 1.2.11`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| **P-01** | 条件边的**登记方法与签名** | `langgraph/graph/state.py:982-989`（`add_conditional_edges(source, path, path_map=None)`） | 同款：`add_conditional_edges(source, path, path_map=None)`（L3 · B6F1 已交付） | SAME | 原则 XI 照抄 · 门面已由 B6F1 冻结 |
| **P-02** | `path_map` 的 **list / dict 双形态** | `langgraph/graph/_branch.py:96-101`（dict ⇒ `copy()` · list ⇒ `{name: name}`）· `:112-114`（`None` ⇒ 从 `Literal[...]` 注解推断）· 实测 **E-18** | 消费 L3 **已归一化**的结果（dict 或 `None`）⇒ ⇒ L2 **零归一化** | SAME | 归一化位置不同（L3 vs 上游的 L3 同层）⇒ 行为面**逐字同款** |
| **P-03** | **路由求值的时机** | `langgraph/graph/state.py:1624`（`self.nodes[start].writers.append(branch.run(get_writes, reader))` ⇒ 分支是**源节点的 writer**）· `langgraph/graph/_branch.py:146-167` · 实测 **E-24** | 源节点任务**成功落回**时求值 | SAME | 上游同款 ⇒ 原则 XI 照抄（裁定 1） |
| **P-04** | **fresh 读**（C8 的唯一来源） | `langgraph/pregel/_algo.py:188-224`（`local_read` · `:211-219` 的 `fresh=True` 分支：每个通道 `copy()` + `update(updated[k])`）· `langgraph/graph/state.py:1613-1617`（`ChannelRead.do_read(..., fresh=True)`）· 实测 **E-1 / E-16** | `local_read(channels, writes, fresh=True)`（**显式**传参） | SAME | 上游同款 ⇒ 原则 XI 照抄（裁定 2）· C8 的**唯一来源** |
| **P-05** | 路由函数的**入参** | 实测 **E-10**：全部 schema 通道 `['llm_calls','messages']`（**不是**源节点订阅集）· `langgraph/graph/state.py:1615`（`select=channels`） | fresh 视图（覆盖整张通道表 · 路由型通道**缺席**） | SAME | 上游同款 ⇒ 两者**可观察等价**（裁定 3） |
| **P-06** | 路由函数**返回值**的形态 | `langgraph/graph/_branch.py:199-200`（标量包成 1 元列表 · `list`/`tuple` ⇒ 多目标）· 实测 **M-F / M-G** | 同款 | SAME | 上游同款 ⇒ 原则 XI 照抄 |
| **P-07** | `path_map` **key** 的查表 | `langgraph/graph/_branch.py:202-204`（`self.ends[r]`）· 实测 **E-6 / E-7 / M-C / M-E** ⇒ `KeyError`（消息只有 key） | 查表 + 内置 `KeyError`（**类型逐字同款**）+ **消息指明返回值与可选目标** | **STRICTER** | 原则 XI「失败信号 MAY 更严」+ 原则 XI ② 类 ⇒ **X-1** |
| **P-08** | 返回 `END` 的**终止** | `langgraph/graph/_branch.py:199-211`（**不**过滤 `END`）· `:202-204`（查表）· `langgraph/graph/state.py:1592`（`if (True if static else p != END)` ⇒ `END` 包从写入里剔除）· `langgraph/graph/state.py:999`（docstring）· 实测 **E-3 / E-4 / E-5 / E-5b** | `END` **无条件**终止（**单独返回** 时 · 查表**前**判定） | **DIFF** | 上游终止的充要条件是「**解析后的目的地**恰为 `'__end__'`」⇒ 「`END` 是 `path_map` 的 key」**不**等于终止（实测 `{END: "b"}` ⇒ 路由到 `b`）⇒ 上游**代码**与上游**自己的 docstring** 矛盾 ⇒ 原则 XI ② 类 ⇒ 取 docstring 口径（**更确定**）⇒ **X-2** |
| **P-09** | **无** `path_map` 时的非法目标 | `langgraph/graph/_branch.py:205-206`（返回值**直接**当节点名 ⇒ **静默忽略**）· `:207-208`（`None` / `START` ⇒ `ValueError`）· 实测 **E-8 / M-B / M-D** | 非法**节点名** ⇒ 显式失败（内置 `ValueError`）；`None` / `START` ⇒ 内置 `ValueError`（**类型逐字同款**）+ 更详细消息 | **STRICTER** | 原则 XI ② 类（上游的静默忽略）+ 与 B7F3 的 **X-2** 同类 ⇒ **X-3** |
| **P-10** | **序列**返回 ⇒ 多目标 fan-out | `langgraph/graph/_branch.py:199-200`（`list`/`tuple` ⇒ 多目标）· `:211`（`writer(destinations, False)`）· 实测 **E-9 / E-9b** | 同款（动态边投递 · 共享状态） | SAME | 上游同款 ⇒ 原则 XI 照抄（裁定 9） |
| **P-11** | 路由函数返回 **`Send`** | `langgraph/graph/_branch.py:203`（`Send` 实例**不**查表）· 实测 **E-11** | 复用 **B11F1** 的 fan-out 任务构造器 | SAME | 上游同款 ⇒ 原则 XI 照抄（裁定 10）· ⚠ 本行的 SAME **仅**指**任务形态 / 载荷语义** ⇒ ⇒ ⇒ **失败信号**的类型分叉见 **P-22 / P-23**（**X-6 / X-7**） |
| **P-12** | 路由函数**抛异常** | `langgraph/graph/_branch.py:146-167`（`_route` 内**不**捕获路由函数的异常）· 实测 **E-12** | 原样传播（原始类型 + 原始消息） | SAME | 上游同款 ⇒ 原则 XI 照抄（裁定 11） |
| **P-13** | 路由函数的**调用形态与判别规则** | `langgraph/graph/_branch.py:166`（`self.path.invoke(value, config)`）⇒ 经 `RunnableCallable`（`langgraph/_internal/_runnable.py:299`（类定义）· `:341-365`（判别循环）· `:168-181`（`KWARGS_CONFIG_KEYS` 的 `"config"` 项））⇒ `langgraph/utils/runnable.py:3` **仅**为兼容再导出 · 实测 **N-B / P-A01…P-A19 / P-D** | **同款** —— **单参**与**双参**两形态均支持 · 判别按**参数名 `config`** · **关键字注入** | **SAME** | 调用**形态**与**判别规则**逐字相同 ⇒ 第二参的**内容**是 freegraph 自有的载体语义（见 **P-19**） |
| **P-14** | **路由通道**的写入 | `langgraph/graph/state.py:1583-1592`（`get_writes` ⇒ 写 `branch:to:<target>` ⇒ **触发**）· `:1525-1530`（通道为 `EphemeralValue(Any, guard=False)`）· `:1586`（`END` → 通道映射） | 路由通道**只作声明载体** · **不被写入** · 触发走**动态边** | DIFF（结构差异 · 非更严） | freegraph 的触发源恒为**边**（B7F1 §3.0）⇒ 上游的通道触发 ≡ freegraph 的边触发；⇒ 而路由通道是**单值语义**（写两次 ⇒ V-6）⇒ **不写**是唯一正确选择（裁定 8）⇒ **X-4** |
| **P-15** | `END` 常量的**值** | `langgraph/constants.py:28`（`END = sys.intern("__end__")` ⇒ 值 `"__end__"`） | `freegraph.graph.END == "__end__"`（`src/freegraph/graph.py:45`） | SAME | 上游同款 ⇒ 原则 XI 照抄 |
| **P-16** | 路由通道**不进**返回键集 | 上游的 `branch:to:*` **不在** output schema（`langgraph/graph/state.py:1526-1530` 建在 `self.channels` 而非 schema） | `EphemeralValue` ⇒ 不在 schema key 集（B7F3 的裁定 4 · `isinstance(channel, EphemeralValue)`） | SAME | 上游同款 ⇒ 原则 XI 照抄 |
| **P-17** | 路由函数入参是否含节点返回的**非 schema key** | `langgraph/graph/_branch.py:158-163`（passthrough：`value = {**input, **value}`） | freegraph **拒绝**未知 key（`InvalidUpdateError` · B7F3 的 **X-2**）⇒ **无** passthrough 需求 | DIFF（源自**更严**的未知 key 口径 · 非更严） | 上游的 passthrough 是它「未知 key 只告警」的上游条件下的伴生行为 ⇒ freegraph 在该处**更早失败** ⇒ 路由函数**看不到**非 schema key ⇒ **不构成**行为面的分叉 |
| **P-18** | **零出站 / 零环境变量 / 零第三方依赖** | ——（上游是依赖方 · 本项目是**替代方**）· 仓库侧：`pyproject.toml:43`（`dependencies = []`）· `:15`（`langgraph` 在**黑名单**）· `:99-101`（`differential` **开发组** ⇒ 非运行时依赖） | 同款（零出站 · 零环境变量 · 零 `langchain*` / `langgraph*` / `langsmith`） | SAME | 宪法原则 I / X（**红线**）· 与上游**无冲突**（上游的依赖面被**主动排除**） |
| **P-19** | 双参形态的**第二参内容** | 上游传的是 `RunnableConfig`（dict 形态）· `langgraph/pregel/main.py:39-43`（import · `:40`）· `langchain_core/runnables/config.py:57`（`class RunnableConfig(TypedDict, total=False)` ⇒ dict 形态）· `langgraph/_internal/_runnable.py:170-176`（注解匹配集 = 精确 5 元组）· `:400-401`（`kw_value = config`）· 实测 **P-B** | freegraph 传的是用户交给 `invoke` 的**原始 `config`**（`RunConfig \| Mapping[str, Any] \| None`）· **逐字传入** | **DIFF** | **载体形态差异** ⇒ **非更严**（调用**形态**与上游同款 · 见 **P-13**）⇒ 已登记为偏离登记 **X-5** · 上游的 `config` **注解匹配集** = `RunnableConfig` · freegraph = `RunConfig \| Mapping[str, Any]` ⇒ 注解**匹配集**亦不同（同属载体形态差异 · **非更严**）⇒ freegraph 的匹配集与上游 `KWARGS_CONFIG_KEYS` 的 `"config"` 项**同形**（类对象 / 字符串 / `Optional` / PEP-604 / 空）⇒ **仅载体类型**不同（`RunnableConfig` ⇒ `RunConfig \| Mapping[str, Any]`）⇒ ⚠️ **附带诊断信号**（2026-11-18 · analyse 轮补登记）：上游在注解不匹配时**发** `UserWarning`（`langgraph/_internal/_runnable.py:352-359`）⇒ freegraph **不发**（零新增可观察输出）⇒ ⇒ ⇒ 失败信号 `TypeError` **逐字同款** ⇒ ⇒ ⇒ **非更严** ⇒ ⇒ ⇒ 归 **X-5**（差分**三投影**不含 Python 警告 ⇒ 由**单元测试**锁定 · tasks **T074**） |
| **P-20** | `__start__` 上的**条件边**是否被求值 | 上游的 `__start__` 是**真实伪节点**（`langgraph/graph/state.py:1373` 的 `attach_node(START, None)` · `:1508-1514` 的 `PregelNode(triggers=[START], channels=START)` · `:1624` 分支挂到它身上）⇒ 挂在它上面的分支**会**被求值 ⇒ 纯条件边入口**可行** · 并存时两个目标**同轮并行** · 实测 **N-A1 … N-A8** | freegraph **同款** —— `__start__` 上的条件边 MUST 被求值 · 允许纯条件边入口 · 并存时**同轮并行** | **SAME** | 照抄上游 ⇒ 当前 freegraph 的「静默空跑」是**缺陷**而非口径差异 ⇒ **FR-038 / FR-039** 修正它 |
| **P-21** | 条件边的 **branch 名**纪律 | `langgraph/graph/state.py:1019-1025`（`coerce_to_runnable` · `name = path.name or "condition"` · 同源**重名** ⇒ 内置 `ValueError`）· 实测 **N-A5a / N-A5b / N-A7** | freegraph **同款** —— `_branch_name` 取 `__name__`（缺省 `"condition"`）· 重名 ⇒ 内置 `ValueError`（消息点名分支名与源节点） | **SAME** | freegraph **已实现**该校验 ⇒ 本 feature **零新增** ⇒ `__start__` 亦**不特例化** |
| **P-22** | 路由函数返回 **`Send`** → **未注册节点**的**失败信号** | **实测 E-22**：上游**静默忽略**（**不**抛错 · `langgraph/graph/_branch.py:205-206` 把返回值直接当节点名） | **显式失败**（内置 `ValueError` · B11F1 的 **V-19** · `src/freegraph/runtime/_fanout.py:56-82`）⇒ ⇒ ⇒ MUST **NOT** 改 B11F1 的冻结面 | **STRICTER** | 原则 XI ② 类（上游的**静默忽略**）+ 与 B7F3 的 **X-2** 同类 ⇒ ⇒ 「拼错的 `Send` 目标无声地少跑一条分支」会让图「看起来成功」却结果不对 ⇒ ⇒ ⇒ **X-6** |
| **P-23** | 路由函数返回 **`Send`** → **`END`** 的**失败信号类型** | **实测 E-21**：上游抛 **`InvalidUpdateError`**（`langgraph/graph/_branch.py:209-210`） | 内置 **`ValueError`**（B11F1 的 **V-21** · `validate_send`）⇒ ⇒ ⇒ **类型不同型** ⇒ ⇒ ⇒ MUST **NOT** 改 B11F1 的冻结面 | **DIFF** | freegraph **零新增错误类型**（只用**内置**异常）⇒ ⇒ ⇒ 与上游的**异常类型家族**不同 ⇒ ⇒ ⇒ **非更严**（上游更宽）⇒ ⇒ ⇒ **X-7** |

### 2.1 锚点复核备注（版本漂移登记）

> ⚠️ **纪律**：核对后发现行号漂移时，**MUST NOT** 自行改动 spec ⇒ 在此登记备注
> （spec 记的行号 X ⇒ 实测为 Y）⇒ ⇒ ⇒ **换版本时 MUST 一并复核**。

| 备注 | 对象 | spec / 任务清单记的行号 | **实测**行号（`langgraph 1.2.11`） | 结论 |
|---|---|---|---|---|
| **P-09-r1** | `ValueError("Branch did not return a valid destination")` 的触点 | `:207-209`（`data-model.md:116` · `conditional-edge-contract.md:179`） | `:207-208`（`:207` = `if any(dest is None or dest == START ...)` · `:208` = `raise ValueError(...)`） | **版本漂移**（末尾多含一行）⇒ 本契约按**实测**记 · **MUST NOT** 自行改动 spec |
| **P-11-r1** | `Send` → `END` ⇒ `InvalidUpdateError` 的触点 | `:210-211` | `:209-210`（`:209` = `if any(p.node == END ...)` · `:210` = `raise InvalidUpdateError(...)`） | **版本漂移**（+1）⇒ research **DR-6** 记的 `:209-210` 与**实测一致** |
| **P-19-r1** | `RunnableConfig` 的定义位置 | 「`langgraph/pregel/main.py`（**行号随版本变动**）」 | `langgraph/pregel/main.py:39-43`（import · `:40`）· `langchain_core/runnables/config.py:57`（`TypedDict` ⇒ dict 形态） | **补齐**（非漂移）⇒ 行号已**钉死** |
| **P-13-r1** | `RunnableCallable` 的权威位置 | `langgraph/_internal/_runnable.py:299` | `:299`（类）· `:341-365`（判别循环）· `:168-181`（`KWARGS_CONFIG_KEYS`）· `:170-176`（匹配集 5 元组） | **补齐**（非漂移）· `langgraph/utils/runnable.py:3` **仅**兼容再导出 ⇒ **MUST NOT** 当类定义位置引用（research **C-8**） |
| **P-20-r1** | `__start__` 伪节点的锚点 | 「`langgraph/pregel/_algo.py`」（泛指） | `langgraph/graph/state.py:1373` · `:1508-1514` · `:1624` | **补齐**（非漂移）⇒ 换版本 MUST 重核 |
| **P-01…P-18** | 其余各行 | 见 §2 各行 | **逐条命中**（`:96-101` · `:112-114` · `:158-163` · `:166` · `:199-200` · `:202-204` · `state.py:982-989` · `:999` · `:1373` · `:1508-1514` · `:1525-1530` · `:1526-1530` · `:1583-1592` · `:1586` · `:1592` · `:1613-1617` · `:1615` · `:1624` · `constants.py:28`） | **无漂移** |

---

## 3. 差分场景索引（**D-103 … D-120** · 共 **18** 条）

> **落点**：`tests/differential/parity_probe.py`（**双真实实现**对跑）⇒ 上游缺席即 `skip`
> （`tests/differential/conftest.py:25-33` 的 `pytest.importorskip`）⇒ 判据 = spec
> 「差分场景组」表 · **逐条一致**（**MUST NOT** 改判词）。
> ⚠️ **载体扩展（属「扩展」非「重造」· 裁定 15 · FR-032）**：为承载条件边载荷而**扩字段**
> —— `Scenario` dataclass 新增**条件边字段**（外层 key = 源节点名 · 内层 = `branch` / `path`
> / `path_map` / `targets` / `route_channels` **五键** · 顺序 = 登记顺序）+ `run_freegraph()`
> 把该载荷**传入** `GraphSpec.conditional_edges` ⇒ ⇒ ⇒ **MUST NOT** 新建第二套差分夹具 /
> 第二条差分执行路径 ⇒ ⇒ ⇒ **MUST NOT** 作废 B5F2 已产出的**线性链路**差分证据。

| # | 场景 | 上游观察（实测） | freegraph 期望 | 判词 | 实测编号 | 锁定的不变量 |
|---|---|---|---|---|---|---|
| **D-103** | **list 形态** `path_map`（`["a", END]`）· 路由返回 `"a"` | 正常路由 ⇒ 输出 `{'messages': ['x'], 'llm_calls': 1}` | 两侧的**执行节点序列**逐字相等（`('r','a')`）· 最终状态**逐字相等** | SAME | E-1 / E-18 | **I-2**（`path_map` **不被重新归一化**）· **I-4**（动态边投递） |
| **D-104** | **dict 形态** `path_map`（`{"hit": "a", "miss": "b"}`）· 路由返回 `"hit"` | 正常路由 ⇒ 节点 `a` 执行 · `b` 未执行 | 两侧的**执行节点序列**逐字相等（`('r','a')` · `b` **未**执行）· 最终状态**逐字相等** | SAME | E-2 / E-14 / E-15c / E-18 | **I-2** · **I-4** |
| **D-105** | **fresh 读**：源节点写 `{"messages": ["fresh"], "llm_calls": 7}` 后路由 | 路由函数看到 **`{'messages': ['fresh'], 'llm_calls': 7}`** · key 集合 = `['llm_calls', 'messages']` | 两侧路由函数收到的**状态逐字相等** ⇒ ⇒ ⇒ **否定式断言**（断言**看到了**新值） | SAME | E-10 / E-16 | **I-5**（fresh 视图**零污染**）· FR-008 / FR-010 / FR-013（**本节点本次**写入 · 覆盖整张通道表） |
| **D-106** | 路由返回 `END`（`path_map` = **`{END: END}`**） | **终止** ⇒ 目标节点执行 **0** 次 | 两侧都**终止**（`END` 之后的目标节点**执行 0 次**）· 最终状态**逐字相等** | SAME | E-3b / E-4 / E-13 / E-19 / M-J | **I-8**（`END` **无条件**终止 · **单独返回** 时 ⇒ 后续目标执行次数 == **0**） |
| **D-107** | 路由返回**非法值**（不在 `path_map` 内） | **抛 `KeyError`**（消息只有 key 本身） | 两侧都**抛异常**且**异常类型相同**（`KeyError`）⇒ freegraph 的**消息更详细**（含可选目标）⇒ 消息**不**逐字比对 | SAME（类型相同） | E-6 / E-7 / M-C / M-E / M-F | **I-7**（有 `path_map` ⇒ 内置 `KeyError`）· **X-1** |
| **D-108** | 路由返回**序列**（`["b", "c"]`） | 两个目标**同轮**执行 · 各自收到**逐字相等**的入参（共享状态） | 两侧的**执行节点序列**逐字相等（两个目标**同轮**执行）· 两个目标收到的**入参逐字相等** | SAME | E-9 / E-9b / E-11 / E-23 / E-26 / M-G | **I-4**（动态边投递）· FR-018（共享状态 · **无**逐目标载荷） |
| **D-109** | **无** `path_map` 的**动态目标**（返回已注册节点名） | 正常路由 ⇒ 目标节点执行 1 次 | 两侧的**执行节点序列**逐字相等 · 最终状态**逐字相等** | SAME | E-8（对照组） | **I-4** · FR-017 |
| **D-110** | 路由返回 `END` 而 `path_map` **不含** `END` 键 | **抛 `KeyError: '__end__'`**（查表失败）⇒ 上游**失败** | **终止**（**成功**）⇒ ⇒ ⇒ 失败与否**不等** | **DIFF**（X-2） | E-5 / E-20 | **I-8**（freegraph **无条件**终止 · **单独返回** `END` 时 · **不**抛错）· **X-2** · ⚠️ MUST 带 `note` |
| **D-111** | **无** `path_map` 且返回**未注册**节点名 | **静默忽略**（warning · 图**成功**结束） | 抛 `ValueError`（**失败**）⇒ ⇒ ⇒ 失败与否**不等** | **STRICTER**（X-3） | E-8 / M-I / N-A4b | **I-7**（无 `path_map` ⇒ 内置 `ValueError`）· **V-29** · ⚠️ MUST 带 `note` |
| **D-112** | 路由函数**抛异常** | **原样传播**（`RuntimeError: boom`） | 两侧都抛**原异常**（类型与消息**逐字一致**） | SAME | E-12 | **I-9**（原类型 + 原消息） |
| **D-113** | **无** `path_map` 且路由返回 `None` / `START` | **抛 `ValueError("Branch did not return a valid destination")`** | 两侧都抛**内置 `ValueError`**（类型**逐字相同**）⇒ ⇒ ⇒ freegraph 的**消息更详细**⇒ 消息**不**逐字比对 | SAME（**类型**相同） | M-B / M-D | **I-7**（无 `path_map` ⇒ 内置 `ValueError`）· **X-1** |
| **D-114** | **双参**形态的路由函数（`f(state, config)`） | 第二参是**增广**后的 `RunnableConfig`（dict · 顶层 key = `['callbacks', 'configurable', 'metadata']`） | 两侧的**调用形态**均成功 ⇒ freegraph 的第二参 = 用户交给 `invoke` 的**原始 `config`** ⇒ ⇒ ⇒ 比对**形态**而非**内容** | **DIFF**（X-5） | N-B / P-A01 / P-A03 / P-A06 / P-A11 / P-A12…P-A16 / P-B | **I-10**（判别按**参数名 `config`**）· **X-5** · ⚠️ MUST 带 `note` |
| **D-115** | **双参**形态的**判别规则**（第二参名字**不叫** `config`） | **抛 `TypeError`**（`missing 1 required positional argument: 'cfg'`） | 两侧都抛 **`TypeError`**（**类型相同**）⇒ ⇒ ⇒ freegraph MUST **NOT** 凭位置个数补传第二参 | SAME | P-A02 / P-A04 / P-A05 / P-A07 / P-A08 / P-A17 / P-A18 / P-A19 / P-C / P-D | **I-10** · **P-C**（注解匹配集**同形**） |
| **D-116** | **条件边挂在 `__start__` 上** | 路由目标**同轮**执行（`['a', 'b']`）· 返回 `END` ⇒ 节点序列 `[]` | 两侧的**执行节点序列**逐字相等（路由目标**同轮**执行）· 最终状态**逐字相等** | SAME | N-A2 / N-A3 / N-A3b / N-A4a / N-A6 | **I-11**（`__start__` 上的条件边**被求值**） |
| **D-117** | **纯条件边入口**（**无**静态入口点） | **允许** ⇒ 节点序列 = **`['b']`** | 两侧都从**路由结果**起步 · 执行节点序列**逐字相等** | SAME | N-A1 | **I-11** · FR-039 |
| **D-118** | 路由返回 `END` 而 `path_map` 把 `END` 映射到**别的节点**（`{END: "b"}`） | **解析后目的地 == "b"** ⇒ 节点 `b` **执行 1 次** ⇒ **不终止** | **无条件终止**（**单独返回** `END` · 不路由到 `b`）⇒ ⇒ ⇒ 终止与否**不等** | **DIFF**（X-2） | E-3 / E-17 / E-35 | **I-8** · **X-2** · ⚠️ MUST 带 `note` |
| **D-119** | 路由返回 `Send("ghost", payload)`（**未注册**节点） | **静默忽略**（warning · 图**成功**结束 · 实测 **E-22**） | 抛 `ValueError`（**失败** · B11F1 的 V-19）⇒ ⇒ ⇒ 失败与否**不等** | **STRICTER**（X-6） | E-22 | **I-7**（失败信号**两态** · 无 `path_map` ⇒ 内置 `ValueError`）· ⚠ MUST 带 `note` |
| **D-120** | 路由返回 `Send(END, payload)` | **抛 `InvalidUpdateError`**（实测 **E-21**） | 抛**内置 `ValueError`**（B11F1 的 V-21）⇒ ⇒ ⇒ **异常类型不同型** ⇒ ⇒ ⇒ 消息**不**逐字比对 | **DIFF**（X-7） | E-21 | **I-7** · **X-7** · ⚠️ MUST 带 `note` |

⇒ **共 18 条**（D-103…D-120）⇒ ⇒ **判词分布 = SAME 12**（D-103 / D-104 / D-105 / D-106 /
D-107 / D-108 / D-109 / **D-112 / D-113 / D-115 / D-116 / D-117**）·
**DIFF 4**（D-110 / D-114 / **D-118 / D-120**）· **STRICTER 2**（D-111 / **D-119**）
⇒ ⇒ ⚠️ **判词非 `SAME` 的 6 条 MUST 带非空 `note`**（**STRICTER 2** · D-111 / D-119
＋ **DIFF 4** · D-110 / D-114 / D-118 / D-120）⇒ ⇒ ⇒ 宪法原则 XI「失败信号更严须标注」
+ 既有守卫 `tests/differential/test_parity_probe.py:106-108`
（`if scenario.verdict in {"STRICTER", "DIFF"}: assert scenario.note`）⇒ ⇒ ⇒
⚠️ **本口径只收紧不放宽**（判词分布**零变动** · 差分编号**零变动**）
⇒ ⇒ ⚠️ **D-107 / D-113 的断言口径**：比对「**异常类型**」而非「异常消息」
⇒ ⇒ ⇒ 因为 freegraph 的消息**刻意更详细**（**X-1**）⇒ ⇒ ⇒ 若逐字比对消息
⇒ ⇒ ⇒ 那两条**必红** ⇒ ⇒ ⇒ 故判词为 **SAME（类型相同）** ⇒ ⇒ ⇒ 而「消息更详细」
⇒ ⇒ ⇒ 这条**由单测**（FR-021 的消息内容断言）判定。

---

## 4. 偏离登记（**X-1 … X-7** · 共 **7** 条）

> **类别列 = 三态**（`STRICTER` / `DIFF`）· **逐字**与 §2 对应行的「关系」列一致
> （宪法原则 XI 末条 · v1.12.0）⇒ ⇒ ⇒ **零新增错误类型** ⇒ ⇒ ⇒ **零判据放宽**。

| # | 类别 | 被偏离的判据 | 理由（含上游锚点） | 锁定的差分场景 | 承接与追认 |
|---|---|---|---|---|---|
| **X-1** | **STRICTER**（更严的失败信号） | **非法路由返回值的失败信号**：① **有** `path_map` ⇒ 上游抛**裸 `KeyError`**（消息只有 key 本身 · `langgraph/graph/_branch.py:203` · 实测 **E-6 / E-7 / M-C / M-E**）；② **无** `path_map` ⇒ 上游抛 `ValueError("Branch did not return a valid destination")`（实测 **M-B / M-D**）⇒ freegraph 抛**同型**的 `KeyError` / `ValueError` ⇒ 两态的**消息均 MUST 指明返回值与可选目标** | 原则 XI「失败信号 MAY 比上游更严」+ 原则 XI ② 类（上游自身的**不确定**：消息不含「可以返回什么」）⇒ 「路由拼错」在 freegraph 里**一次就说清** ⇒ **类型逐字同款**（照抄纪律 ①）+ **消息更严** ⇒ **零新增错误类型** ⇒ ⚠️ **2026-11-17 clarify 轮 · 用户拍板（Q2 = 选项 B）** | **D-107 / D-113**（**只比对类型**） | 本 feature 内闭合 · 追认文字落 `harness/verification/B8F1/manual-verification.md` |
| **X-2** | **DIFF**（终止条件差异 · 非更严 · **更宽松**） | **返回 `END` 的终止条件**：上游**不**在 `_branch.py` 里过滤 `END`（`langgraph/graph/_branch.py:199-211`）⇒ 终止的充要条件是「**解析后的目的地**恰为 `'__end__'`」⇒ 「`END` 是 `path_map` 的 key」**不**等于终止（实测 `path_map = {END: "b"}` ⇒ 路由到 `b` · **不终止** · **E-3 / E-17 / E-35**）⇒ 上游抛 `KeyError: '__end__'` 的场景是「`path_map` **不含** `END` 键」（**E-5 / E-20**）⇒ 「无 `path_map` + 返回 `END`」⇒ 上游**正常终止**（**E-19**）⇒ freegraph 对「**单独返回** `END`」**无条件**终止（序列内的 `END` ⇒ **剔除** · 不终止） | 上游**自己的 docstring**（`langgraph/graph/state.py:999`）写「If it returns `'END'`, the graph will stop execution.」⇒ **代码与 docstring 相互矛盾** ⇒ 上游**自身无定论**（原则 XI ② 类）⇒ freegraph 取**docstring 口径** ⇒ **更确定** ⇒ 如实登记、**不掩盖** ⇒ ⚠️ **2026-11-17 clarify 轮 · 用户拍板（Q1 = 选项 A）** | **D-110**（`path_map` 不含 `END` 键 ⇒ 上游 `KeyError`）· **D-118**（`path_map` 把 `END` 映射到别的节点 ⇒ 上游**不终止**） | 本 feature 内闭合 · 追认文字落同上手工验证记录 |
| **X-3** | **STRICTER**（更严的失败信号） | **无 `path_map` 时的非法目标**：上游**静默忽略**（只打一条 warning · 实测 **E-8** · `langgraph/graph/_branch.py:205-206` 把返回值直接当节点名）⇒ freegraph **显式失败**（内置 `ValueError`） | 原则 XI ② 类（上游的**静默忽略**）+ 与 B7F3 的 **X-2**（未知 key ⇒ 显式失败）**同类** ⇒ 「拼错的节点名无声地少跑一条分支」会让图「看起来成功」却结果不对 ⇒ 差分 **D-111** 锁住 | **D-111**（⚠️ MUST 带 `note`） | 本 feature 内闭合 · 追认文字落同上手工验证记录 |
| **X-4** | **DIFF**（结构差异 · 非更严） | **路由通道的写入**：上游**写** `branch:to:<target>` 并以该通道写入**触发**目标（`langgraph/graph/state.py:1583-1592` · `:1525-1530` 的 `EphemeralValue(Any, guard=False)`）⇒ freegraph **不写**该通道（只作声明载体）· 触发由**动态边**投递 | freegraph 的触发源恒为**边**（B7F1 契约 §3.0「上游对齐 P1-0」⇒ 上游的「`branch:to:` 通道触发」≡ freegraph 的**边触发** · **同款语义**）⇒ 路由通道是 `EphemeralValue`（**单值语义**）⇒ 同轮**两个源**路由到**同一目标**时写两次 ⇒ **触发 V-6**（`InvalidChannelUpdateError`）⇒ **不写**是 freegraph 触发模型下的**唯一**正确选择（裁定 8）⇒ **不构成**行为面分叉（目标集合与执行序列**逐字相同**） | ——（**D-108 / D-111** 的**间接**锁） | 本 feature 内闭合 · 追认文字落同上手工验证记录 |
| **X-5** | **DIFF**（载体形态差异 · 非更严） | **双参形态的第二参内容**：上游传 `RunnableConfig`（dict）⇒ freegraph 传用户交给 `invoke` 的**原始 `config`**（`RunConfig \| Mapping[str, Any] \| None`）· **逐字传入** ⇒ 上游要求 `config` 参数的注解匹配 `RunnableConfig`（不匹配 ⇒ 跳过注入 + `UserWarning`）⇒ freegraph 的对应集合是 `RunConfig \| Mapping[str, Any]` 的**同形**集合 ⇒ ⇒ ⇒ ⚠️ **附带诊断信号**：上游**发** `UserWarning` ⇒ freegraph **不发** | freegraph 的运行期配置载体**形态**与上游不同 ⇒ 但调用**形态**（1 参 / 2 参）**逐字相同** ⇒ 已登记但**非更严** ⇒ 差分 **D-114** 锁住（**形态**）⇒ ⇒ ⇒ **附带诊断信号**的差异**同属**本条（**非更严** · `TypeError` **逐字同款**）⇒ ⇒ ⇒ 差分**三投影**不含 Python 警告 ⇒ ⇒ ⇒ 由**单元测试**锁定（tasks **T074**） | **D-114**（比对**形态**而非内容）· **T074**（`UserWarning` 不发） | 本 feature 内闭合 · 追认文字落 `harness/verification/B8F1/manual-verification.md` |
| **X-6** | **STRICTER**（更严的失败信号） | **路由函数返回 `Send` → 未注册节点**：上游**静默忽略**（只打一条 warning · 实测 **E-22** · `langgraph/graph/_branch.py:205-206` 把返回值直接当节点名）⇒ freegraph **显式失败**（内置 `ValueError` · B11F1 的 **V-19**） | 原则 XI ② 类（上游自身的**静默忽略**）+ 与 B7F3 的 **X-2** 同类 ⇒ 「拼错的 `Send` 目标无声地少跑一条分支」会让图「看起来成功」却结果不对 ⇒ **零新增错误类型** ⇒ MUST **NOT** 改 B11F1 的冻结面（V-19）⇒ ⚠ **2026-11-17 clarify 轮 · 用户拍板（Q4 = 选项 A）** | **D-119**（比对「失败与否」· ⚠ MUST 带 `note`） | 本 feature 内闭合 · 追认文字落 `harness/verification/B8F1/manual-verification.md` |
| **X-7** | **DIFF**（失败信号的**异常类型**差异 · 非更严） | **路由函数返回 `Send` → `END`**：上游抛 **`InvalidUpdateError`**（`langgraph/graph/_branch.py:209-210` · 实测 **E-21**）⇒ freegraph 抛**内置 `ValueError`**（B11F1 的 **V-21**）⇒ **异常类型不同型** | freegraph **零新增错误类型**（只用**内置**异常）⇒ 与上游的**异常类型家族**不同 ⇒ **非更严**（上游更宽）⇒ MUST **NOT** 改 B11F1 的冻结面（V-21）⇒ ⚠ **2026-11-17 clarify 轮 · 用户拍板（Q4 = 选项 A）** | **D-120**（比对「异常类型」） | 本 feature 内闭合 · 追认文字落 `harness/verification/B8F1/manual-verification.md` |

---

## 5. 三态一致性对照表

### 5.1 正向（偏离登记 ⇒ 上游对照行）

| 偏离登记 | 对照表行 | 类别 / 关系（**逐字一致**） | 核验点 |
|---|---|---|---|
| **X-1** | **P-07** | `STRICTER` / `STRICTER` | 非法返回值 ⇒ 查表失败 ⇒ 内置 `KeyError`（**类型同款** · **消息更详细**） |
| **X-2** | **P-08** | `DIFF` / `DIFF` | 返回 `END` ⇒ freegraph「**单独返回** `END`」⇒ **无条件终止** vs 上游「解析后目的地 == `'__end__'`」 |
| **X-3** | **P-09** | `STRICTER` / `STRICTER` | 无 `path_map` 的非法节点名 ⇒ 上游**静默忽略** vs freegraph **显式失败** |
| **X-4** | **P-14** | `DIFF` / `DIFF` | 路由通道**不写** · 触发走**动态边**（结构差异） |
| **X-5** | **P-19** | `DIFF` / `DIFF` | 双参第二参的**内容**与**注解匹配集**的**载体形态**差异 |
| **X-6** | **P-22** | `STRICTER` / `STRICTER` | `Send` → **未注册节点**：上游**静默忽略** vs freegraph **显式失败**（内置 `ValueError`） |
| **X-7** | **P-23** | `DIFF` / `DIFF` | `Send` → `END` 的**失败信号类型**：上游 `InvalidUpdateError` vs freegraph 内置 `ValueError` |

### 5.2 反向（上游对照行 ⇒ 偏离登记）

| 对照表行 | 关系 | 是否**在**偏离登记里 | 说明 |
|---|---|---|---|
| **P-07** | `STRICTER` | ✅ **X-1** | —— |
| **P-08** | `DIFF` | ✅ **X-2** | —— |
| **P-09** | `STRICTER` | ✅ **X-3** | —— |
| **P-14** | `DIFF` | ✅ **X-4** | —— |
| **P-17** | `DIFF` | ❌ **无** | passthrough（`langgraph/graph/_branch.py:158-163`）⇒ 源自 freegraph **更严**的未知 key 口径（B7F3 的 **X-2**）⇒ ⇒ **不构成**行为面分叉 ⇒ 故**不**登记为偏离 |
| **P-19** | `DIFF` | ✅ **X-5** | —— |
| **P-22** | `STRICTER` | ✅ **X-6** | —— |
| **P-23** | `DIFF` | ✅ **X-7** | —— |

> ⚠️ **「无孤行 / 无漏行」的方向定义**（宪法原则 XI 末条 · v1.12.0）：
> **无孤行 / 无漏行指的是「偏离登记的每一条都有对照表的对应行」这一方向**
> ⇒ 即 §5.1 的 **X-1…X-7** 每条都有对应的 **P 行**（**7** 条对 **7** 条）⇒ ⇒ ⇒ **判据零放宽**。
> ⚠️ **反向**（§5.2）**允许**存在「对照表标 `DIFF` 但**不**在偏离登记里」的行
> —— 本 feature **恰有 1 条**：**P-17**（passthrough · 源自**更严**的未知 key 口径）
> ⇒ ⇒ ⇒ 故**反向不是**「无漏行」的判定方向。

---

## 6. 结构面断言清单（换版本时 MUST 一并重跑）

> **判据**（spec 的「Upstream Parity」note）：P-04 / P-05 / P-07 / P-08 / P-09 / P-10 / P-11 /
> P-12 属**行为**断言（须实测支撑）；P-01 / P-02 / P-03 / P-06 / P-14 / P-15 / P-16 / P-17 /
> P-18 / P-19 属**结构面**断言（源码锚点 + 差分场景的可观察结果）
> ⇒ ⇒ ⇒ **换上游版本时 MUST 一并重跑**下列各行。

| P 行 | 语义点 | 结构面断言（源码锚点 / 差分可观察结果） | 换版本时 MUST 重跑的动作 |
|---|---|---|---|
| **P-01** | 条件边的登记方法与签名 | `langgraph/graph/state.py:982-989` 的签名逐字一致 | 复核 `add_conditional_edges` 的签名与行号 |
| **P-02** | `path_map` 双形态 | `langgraph/graph/_branch.py:96-101` · `:112-114`（归一化与 `Literal` 推断） | 复核归一化位置 + 重跑 **D-103 / D-104** |
| **P-03** | 路由求值的时机 | `langgraph/graph/state.py:1624`（分支是源节点的 writer）· `langgraph/graph/_branch.py:146-167` | 复核「writer 挂载点」行号 |
| **P-06** | 返回值的形态 | `langgraph/graph/_branch.py:199-200`（`list` / `tuple` ⇒ 多目标） | 复核多目标判定行号 + 重跑 **D-108** |
| **P-14** | 路由通道的写入 | `langgraph/graph/state.py:1583-1592` · `:1525-1530` · `:1586` | 复核写入点与 `EphemeralValue` 行号 |
| **P-15** | `END` 常量的值 | `langgraph/constants.py:28`（`"__end__"`） | 复核常量行号与字面值 |
| **P-16** | 路由通道不进返回键集 | `langgraph/graph/state.py:1526-1530`（建在 `self.channels` 而非 schema） | 复核通道建点行号 |
| **P-17** | 路由函数入参的 passthrough | `langgraph/graph/_branch.py:158-163`（`value = {**input, **value}`） | 复核 passthrough 判定行号 |
| **P-18** | 零出站 / 零环境变量 / 零第三方依赖 | `pyproject.toml:43`（`dependencies = []`）· `:15`（黑名单）· `:99-101`（`differential` 开发组） | 复核依赖面 + 重跑门禁 **G3 / G21 / G22 / G23** |
| **P-19** | 双参第二参的内容 | `langgraph/pregel/main.py:39-43` · `langchain_core/runnables/config.py:57` · `langgraph/_internal/_runnable.py:170-176` | 复核 `RunnableConfig` 定义与注解匹配集行号 |

---

## 7. 双份维护的同步义务

> ⚠️ **本表 §2 / §4 与 spec 的「上游对照」表 / 「偏离登记」表 MUST 同时落成**
> ⇒ ⇒ ⇒ **发现漂移 MUST 双侧同改**（MUST NOT 只改一侧）
> ⇒ ⇒ ⇒ **spec 的「上游对照」表 / 「偏离登记」表 与本文件的 §2 / §4 互为镜像** ⇒ ⇒ ⇒ **一处改、另一处 MUST 同改**。
> ⇒ ⇒ ⇒ 镜像的**两侧落点**：spec 的「Upstream Parity」note（**双份维护的同步义务**）
> ⇒ ⇒ ⇒ 与「偏离登记」note（**三态标注一致性**）· **MUST NOT** 只改本文件这一侧。

| 侧 | 落点 | 内容 |
|---|---|---|
| **spec 侧** | `specs/b8f1-conditional-edges-fresh-read/spec.md` 的「Upstream Parity」表 | **P-01…P-23**（23 条 · 三态标注） |
| **spec 侧** | 同文件的「差分场景组」表 | **D-103…D-120**（18 条 · 判词分布） |
| **spec 侧** | 同文件的「偏离登记」表 | **X-1…X-7**（7 条 · 类别标注） |
| **本文件侧** | `contracts/upstream-parity.md` §2 | **P-01…P-23**（本表） |
| **本文件侧** | `contracts/upstream-parity.md` §3 | **D-103…D-120**（本索引） |
| **本文件侧** | `contracts/upstream-parity.md` §4 | **X-1…X-7**（本登记） |

⇒ **两处是「同一份内容的两处落点」** ⇒ ⇒ ⇒ **发现漂移 MUST 双侧同改**
⇒ ⇒ ⇒ **MUST NOT** 只改一侧 ⇒ ⇒ ⇒ **MUST NOT** 改判词、FR / SC / 裁定 / 差分编号
⇒ ⇒ ⇒ 以及三处计数（**P 23** · **D 18** · **X 7**）· **SAME 12 / DIFF 4 / STRICTER 2**。

---

## 8. 零新增面声明

| 面 | 数量 / 状态 | 本 feature 的处置 |
|---|---|---|
| 内核对上游的**依赖面** | **零** —— `src/freegraph/**` 对 `langchain` / `langchain-core` / `langgraph*` / `langsmith` 的 import 数 == **0** | **零新增** ⇒ 零第三方依赖 ⇒ 零出站 · 零环境变量（FR-033） |
| **运行时依赖闭包** | **空集**（`pyproject.toml:43` 的 `dependencies = []`） | **零改动** ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿 |
| 差分载体 | 只存在于 `tests/differential/`（**开发期**）⇒ 上游缺席即 `skip`（`tests/differential/conftest.py:25-33`） | **不进**发行元数据 · **不**进基础 CI |
| 门面 `freegraph.graph` 的 `__all__` | **7** 个符号 | **一字不动** |
| 导出面 `freegraph.runtime` 的 `__all__` | **23** 个符号 | **一字不动** ⇒ 新模块 `src/freegraph/runtime/_routing.py` MUST 是**私有**（**不进** `__all__`） |
| 契约层 `freegraph.contracts` 的 `__all__` | **21** 个符号 | **一字不动** |
| 编译产物持有面 `vars(compiled)` | **11** 个键（3 私有 + 8 公开） | **零新增私有字段** ⇒ **T-3 不破**（FR-037） |
| 错误类型 | **零新增**（只用内置 `KeyError` / `ValueError`） | 归 **X-1 / X-3**（**STRICTER** · 消息更详细） |
| 门禁编号 | **G1–G30** | **零新增**（新模块由 **G25** 的目录条目与 **G30** 的署名头扫描**自动**覆盖） |

⇒ ⇒ ⇒ **本 feature 对上游的依赖面为零** ⇒ ⇒ ⇒ 差分载体只存在于 `tests/differential/`
（**开发期**）⇒ ⇒ ⇒ **运行时依赖闭包仍为空** ⇒ ⇒ ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿。

---

> ⚠️ **本文件的边界**（沿用 B7F1 / B5F2 / B7F3 的同款口径）：
> ① 本文件是**证据表** ⇒ **MUST NOT** 被测试解析（测试**直接断言行为** ⇒
> 避免「判据与实现同源 ⇒ 自证」）；
> ② **判据的唯一权威** = `conditional-edge-contract.md`（`<!-- authority: yes -->`）；
> ③ 本文件的**全部上游实测**在**仓库之外**完成 ⇒ 仓库**零改动** ⇒
> `pyproject.toml` **零改动** ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿；
> ④ **换上游版本 ⇒ MUST 重新核实全部行号**并重跑 §6 的结构面断言 ⇒
> ⇒ ⇒ **MUST NOT** 凭记忆沿用（宪法原则 VIII）。
