# 与上游 LangGraph 的逐条对照（`Command` 运行期语义）

**Feature**: `B9F1` · **契约**: [command-contract.md](./command-contract.md) · **取证**: [../research.md](../research.md)
**核实环境**: 上游 `langgraph` **1.2.11**（用户 site-packages · **非仓库依赖**）· CPython **3.12.3**
—— 核实于 **2026-11-11**。
⚠️ **换上游版本后 MUST 重新核实全部行号**（宪法原则 VIII）。
⚠️ **本文件是「证据」载体** ⇒ **MUST NOT** 被测试解析（测试**直接断言行为** ⇒ 避免自证）。

---

## §1 逐条对照（P-01…P-12）

| # | 语义点 | freegraph | 上游（行号 / 实测） | 关系 |
|---|---|---|---|---|
| **P-01** | `goto` 的语义落点 | **边触发源** `("e", 源节点名)`（裁定 1） | `branch:to:<目标>` **通道**写（`graph/state.py:1768-1774`）⇒ 目标以该通道为**触发**（`:1532`）⇒ **语义上就是「一条边」** | ✅ **同款**（机制不同 · DR-2） |
| **P-02** | `goto` 的有效期 | 由源节点**最近一次执行**决定（裁定 2） | 分支通道 = `EphemeralValue`（`:1525-1530`）⇒ **步末即清** ⇒ 只对下一步有效 | ✅ **同款** |
| **P-03** | `goto` × 静态边 | **叠加**（裁定 3） | 实测 **E-01**：`['from-a', 'from-b', 'from-c']` ⇒ **b 与 c 都执行** | ✅ **同款** |
| **P-04** | `goto=END` | **不产生跳转**（裁定 5） | `:1771-1774` **特判** + 实测 **E-02** ⇒ 静态边**照走** | ✅ **同款** |
| **P-05** | 槽位为空 | **明确无操作**（裁定 10） | 实测 **E-05** ⇒ `a` 执行、无写入、静态边照走 | ✅ **同款** |
| **P-06** | **多目标** `goto` | **支持**（裁定 9） | 实测 **E-06** ⇒ 两个目标**都**执行 | ✅ **同款** |
| **P-07** | `goto` 目标**不存在** | **显式失败**（`ValueError` · 裁定 8） | 实测 **E-04** ⇒ **warning + 静默忽略**（`wrote to unknown channel …, ignoring it`） | ⚠️ **分叉**（freegraph 更严 · 「显式失败优于静默」）<br>⚠️ **2026-11-12 上游对齐 P3**：**维持**（**比上游更严** · 已登记） |
| **P-08** | `Command.PARENT` | **显式失败**（`NotImplementedError` · 裁定 7） | ① `graph=PARENT` ⇒ 上游抛 **`ParentCommand`**（`graph/state.py:1761-1762` · `errors.py:129-133`）② 作为 `goto` 目标 ⇒ 实测 **E-03** **warning + 忽略** | ⚠️ **分叉**（类型不同 · 语义同 = **都失败**）<br>⚠️ **2026-11-12 上游对齐 P3**：`graph=PARENT` 由「静默」改为**显式失败**（**上游同款**）⇒ freegraph 抛内置 `NotImplementedError`（上游 `ParentCommand`）⇒ **类型不同 · 语义等价（失败）** |
| **P-09** | **命令列表** | **支持** · 按列表顺序（裁定 15） | `state.py:1456-1484`（`_get_updates` · 顺序 `extend`）+ `:1752-1758`（`_control_branch`）⇒ 支持 · ⚠️ **空列表上游报错** | ✅ **同款**<br>⚠️ **2026-11-12 上游对齐 P3**：**空列表由「无操作」改为「失败」**（**上游同款** · 上游 `state.py:1488-1492`）⇒ 异常类型不同（内置 `TypeError` vs 上游 `InvalidUpdateError`）· **语义等价（都失败）** |
| **P-13** | `update` 的 **list/tuple of 2-tuples** | **支持**（**上游同款** · 2026-11-12 P3） | `types.py:836-840`（元素**必须是 tuple** · 键**必须是 str**）⇒ 支持 | ✅ **同款**（逐字照抄 · 含「列表元素不算」的细节） |
| **P-14** | `update` 的**其它形态**（非 dict / 非 2-tuples） | **显式失败**（`TypeError` · V-11） | 塞进 `__root__` 通道 ⇒ 无该通道时 **warning + 静默丢弃** | ⚠️ **分叉**（freegraph 更严 · 已登记） |
| **P-15** | 节点返回 **`None`** | **无写入**（**上游同款** · 2026-11-12 P3） | `state.py:1459-1460`（`if input is None: return None`）⇒ 无写入 | ✅ **同款** |
| **P-10** | `goto` 目标的**触发与入参** | 照跑 · 入参 = 稀疏读 · 读得到本次 `update`（裁定 17） | 实测 **E-07** 三组 ⇒ 完全一致 | ✅ **触发语义同款**（⚠️ **入参范围**不同：上游读整个 input schema · freegraph 读「订阅集 ∩ 有值集」） |
| **P-11** | 「跳到哪里去了」的**记录位置** | 下一轮 `executed` + **L1 `StateSnapshot.next`**（裁定 18） | 实测 **E-08** ⇒ `StateSnapshot.next`（`types.py:688-689` · `pregel/main.py:1379-1390`）· debug payload 里是**通道名**（`triggers`）⇒ **无**「源 → 目标」映射字段 | ✅ **同款**（freegraph 的 L1 已逐字冻结同款字段） |
| **P-12** | `Command` 的**泛型参数** | **非泛型**（B1F1 冻结） | `class Command(Generic[N], …)`（`types.py:799`）· `Command[Literal["node_b"]]` 用于**图渲染** | ⚠️ **分叉**（**DR-1** · 归 **B22F1**） |

---

## §2 分叉汇总（**4 条** · 全部**刻意** · 全部已登记 · **X-3 已于 2026-11-12 消除**）

| # | 分叉 | freegraph | 上游 | 为什么**刻意** | 登记 |
|---|---|---|---|---|---|
| **X-1** | 非法跳转目标 | **显式失败** | warning + 忽略 | C6「未知 key 报错」的同款立场 + B7F1 的 V-2 同款 ⇒ 静默忽略会让流程「悄悄少跑一段」 | spec 裁定 8 · SC-009 · parity **P-07** · ⚠️ **2026-11-12 P3 维持 · 标注「比上游更严」** |
| **X-2** | `Command.PARENT` | **`NotImplementedError`** | ① `graph=PARENT` ⇒ **`ParentCommand`**（`state.py:1761-1762`）② 忽略（`goto="__parent__"`） | 它是**合法常量**、只是**本版本未实现子图** ⇒ 与「拼错名字」**语义不同** ⇒ 失败信号**可区分**（`ValueError` vs `NotImplementedError`） | spec 裁定 7 · SC-005 · parity **P-08** · 登记项 **R-4** · ⚠️ **2026-11-12 P3**：`graph=PARENT` 已**显式失败**（上游同款）· 异常类型不同 · 语义等价 |
| **X-3** | **空命令列表** | ~~**无操作**~~ ⇒ **失败** | `InvalidUpdateError`（`_get_updates` 的 `and input` 为假 ⇒ 落到 `else` 分支） | ⚠️ **2026-11-12 上游对齐 P3 已消除** ⇒ **照抄上游**（失败）⇒ freegraph 抛内置 `TypeError`（上游 `InvalidUpdateError`）⇒ **类型不同 · 语义等价** | spec 裁定 15 · SC-021 ④ · parity **P-09** |
| **X-4** | `update` 的**其它形态** | **显式失败** | `__root__` 通道 ⇒ warning + 静默丢弃 | 与 **X-1** 同款立场（**显式失败优于静默**）⇒ ⚠️ **2026-11-12 P3 维持 · 标注「比上游更严」** | parity **P-14** |

⚠️ **X-2 的附带偏离**：本 feature 引入了**第三种**内置异常（`NotImplementedError`）⇒ 偏离 B7F1 的
「一个 feature 只用**两种**内置异常」不变量 ⇒ **刻意 · 已登记**（登记项 **R-4**）。

---

## §3 实测基线（**8 组** · 复核命令见 [../research.md](../research.md) §1）

```text
E-01 · Command(goto='c') + 静态边 a→b
       执行顺序: {'messages': ['from-a', 'from-b', 'from-c']}
E-02 · Command(goto=END) + 静态边 a→b
       结果: {'messages': ['from-a', 'from-b']}
E-03 · Command(goto=Command.PARENT)
       Task a … wrote to unknown channel branch:to:__parent__, ignoring it.
       结果: {'messages': ['from-a']}
E-04 · Command(goto='no-such-node')
       Task a … wrote to unknown channel branch:to:no-such-node, ignoring it.
       结果: {'messages': ['from-a']}
E-05 · Command(update={}) + 静态边 a→b
       结果: {'messages': ['from-b']}
E-06 · Command(goto=['b','c'])
       结果: {'messages': ['from-a', 'from-b', 'from-c']}
E-07 · goto 目标的入参
       (1) z 订阅 other（全程无值）⇒ z 入参 = {'messages': []}
       (2) z 订阅 messages（有值）    ⇒ z 入参 = {'messages': ['seed']}
       (3) goto + update               ⇒ z 入参 = {'messages': ['from-a']}
E-08 · StateSnapshot.next 与 debug payload
       snapshot.next = ('z',) | task names = ['z']        ← goto 的落点
       debug task payload = {'name': 'a', 'triggers': ('branch:to:a',), …}
```

---

## §4 上游的**保留**机制名（freegraph **不**采用 · 仅登记）

| 上游名 | 用途 | freegraph 的处置 |
|---|---|---|
| `branch:to:<节点>` | 承载跳转的**通道**（`state.py:98`） | **不采用** ⇒ freegraph 用**边触发源** `("e", 源节点名)`（DR-2） |
| `branch:source:<条件>:<节点>` | 条件边的通道（迁移前的旧名） | **不采用**（条件边归 **B8F1**） |
| `TASKS` | `Send` 的投递通道（`types.py:67` / `state.py:1770`） | **不采用**（`Send` 归 **B11F1**） |
| `PUSH` / `RESUME` / `INTERRUPT` / `ERROR` | 上游的控制流保留通道 | **不采用**（`resume` 归 **B10F1** · `interrupt` 归 **B10F1**） |

---

## §5 取证纪律

| 项 | 口径 |
|---|---|
| 行号来源 | **本轮实际核对**（`sed -n` 逐段打印 · 2026-11-11）⇒ **不是**凭记忆沿用 |
| 版本 | `langgraph 1.2.11` ⇒ 换版本 **MUST 重新核实**全部行号（spec **FR-017** · SC-020） |
| 取证隔离 | 上游装在**用户 site-packages** ⇒ **不在**仓库 venv / `pyproject.toml` ⇒ 依赖声明**零改动** ⇒ **G3 / G21 / G22 / G23** 恒绿 |
| Python 版本 | 取证用 **3.12.3**（用户 site-packages）⇒ **行为**取证结论成立；⚠️ freegraph 侧的实现仍 MUST 在 **3.11**（CI 最低档）成立 ⇒ **两件事**，不可混谈 |
| 脚本归属 | 一次性脚本在**仓库外**（`/tmp/opencode/`）⇒ **不进仓库**、**不进依赖声明** |
