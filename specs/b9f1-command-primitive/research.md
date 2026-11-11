# B9F1 · Phase 0 研究记录（上游实测取证 + 决策登记）

**核实环境**：上游 `langgraph==1.2.11`（**用户 site-packages**：`~/.local/lib/python3.12/site-packages`
· **非**仓库依赖）· CPython **3.12.3**（`/usr/bin/python3.12`）—— 核实于 **2026-11-11**。
⚠️ **换上游版本后 MUST 重新核实全部行号**（宪法原则 VIII）。
⚠️ **取证环境隔离**：上游装在**用户级 site-packages**，**不在**仓库的 venv / `pyproject.toml` 里
⇒ 仓库的依赖声明**零改动** ⇒ 门禁 **G3 / G21 / G22 / G23** 恒绿（沿用 B5F1 / B5F2 / B7F1 的同款口径）。
⚠️ **与 B7F1 的取证环境差异（如实登记）**：B7F1 用的是**仓库外临时 venv**（CPython **3.11.16**）；
本轮用**用户 site-packages**（CPython **3.12.3**）⇒ **上游版本相同**（1.2.11）⇒ **行号可对照**；
但 **Python 版本不同** ⇒ 上游的**运行时行为**取证结论仍成立（无 3.11/3.12 相关的行为分支），
而 freegraph 侧的实现仍 MUST 在 **3.11** 上成立（CI 最低档）。

> **本文件是「证据」载体，不是「判据」载体** —— 判据的唯一权威是
> [contracts/command-contract.md](./contracts/command-contract.md)；
> 本文件与 [contracts/upstream-parity.md](./contracts/upstream-parity.md) **MUST NOT** 被测试解析
> （测试**直接断言行为** ⇒ 避免「判据与实现同源 ⇒ 自证」的循环论证）。

---

## §1 上游实测取证（D-01…D-09）

### 核实方法（一次性采集）

```bash
# 上游安装位置（本机既有 · 非仓库依赖）
ls ~/.local/lib/python3.12/site-packages/ | grep -i langgraph
#   langgraph-1.2.11.dist-info

# 关键源码位置
sed -n '798,848p'  ~/.local/lib/python3.12/site-packages/langgraph/types.py            # Command 定义
sed -n '683,701p'  ~/.local/lib/python3.12/site-packages/langgraph/types.py            # StateSnapshot 七字段
sed -n '1456,1493p' ~/.local/lib/python3.12/site-packages/langgraph/graph/state.py      # _get_updates（返回值 → 更新）
sed -n '1498,1504p' ~/.local/lib/python3.12/site-packages/langgraph/graph/state.py      # 节点写出项
sed -n '1525,1530p' ~/.local/lib/python3.12/site-packages/langgraph/graph/state.py      # 分支通道 = EphemeralValue
sed -n '1551,1558p' ~/.local/lib/python3.12/site-packages/langgraph/graph/state.py      # attach_edge（静态边写出）
sed -n '1749,1775p' ~/.local/lib/python3.12/site-packages/langgraph/graph/state.py      # _control_branch（goto → 分支写）
sed -n '1778,1789p' ~/.local/lib/python3.12/site-packages/langgraph/graph/state.py      # _control_static
sed -n '  56, 78p' ~/.local/lib/python3.12/site-packages/langgraph/pregel/_io.py        # map_command
sed -n '1379,1390p' ~/.local/lib/python3.12/site-packages/langgraph/pregel/main.py      # 快照的 next 计算
sed -n '172,192p'  ~/.local/lib/python3.12/site-packages/langgraph/pregel/_write.py     # _assemble_writes
sed -n '895,910p'  ~/.local/lib/python3.12/site-packages/langgraph/prebuilt/tool_node.py # 多命令归一

# 行为实测（一次性脚本 · **不进仓库**）
cd /tmp/opencode && python3.12 lg_b9f1_probe.py
```

---

### D-01 · `goto` 的落点 = **边**（上游：`branch:to:<目标>` 通道写）

**上游**：`langgraph/graph/state.py:1749-1775`（`_control_branch`）

```python
def _control_branch(value: Any) -> Sequence[tuple[str, Any]]:
    if isinstance(value, Send):
        return ((TASKS, value),)
    commands: list[Command] = []
    if isinstance(value, Command):
        commands.append(value)
    elif isinstance(value, (list, tuple)):
        for cmd in value:
            if isinstance(cmd, Command):
                commands.append(cmd)
    rtn: list[tuple[str, Any]] = []
    for command in commands:
        if command.graph == Command.PARENT:
            raise ParentCommand(command)

        goto_targets = (
            [command.goto] if isinstance(command.goto, (Send, str)) else command.goto
        )

        for go in goto_targets:
            if isinstance(go, Send):
                rtn.append((TASKS, go))
            elif isinstance(go, str) and go != END:
                # END is a special case, it's not actually a node in a practical sense
                # but rather a special terminal node that we don't need to branch to
                rtn.append((_CHANNEL_BRANCH_TO.format(go), None))
    return rtn
```

**结论**：上游把 `Command.goto` 写成对 `branch:to:<目标>` 通道的一次写 ⇒ **语义上就是「一条边」**
（目标节点正是以 `branch:to:<目标>` 为**触发通道**的：`state.py:1532` 的 `triggers=[branch_channel]`），
而静态边（`attach_edge` · `state.py:1551-1558`）写的**也是**同一个形态的通道 ⇒
**`goto` 与静态边在触发机制上同构**。
⇒ **freegraph 的裁定 1**（`goto` MUST 落在 B7F1 的**边触发源**空间 · `("e", 源节点名)`）**有上游同款依据** ✔
⇒ 上游的分支通道是 `EphemeralValue`（`state.py:1525-1530`）⇒ **步末即清** ⇒ `goto` **只对下一步有效**
⇒ **freegraph 的裁定 2**（`goto` 目标由源节点**最近一次执行**决定）**有上游同款依据** ✔

**落点**：FR-002 · 裁定 1 / 裁定 2 · parity **P-01 / P-02**。

---

### D-02 · `goto` 与静态边并存 ⇒ **叠加**（上游实测）

**实测**（`E-01`）：节点 `a` 有静态边 `a→b`，且 `a` 返回 `Command(goto="c", update=...)` ⇒

```
执行顺序: {'messages': ['from-a', 'from-b', 'from-c']}
```

⇒ **b 与 c 都执行** ⇒ 上游是**叠加**、**不覆盖** ✔
⇒ **freegraph 的裁定 3**（叠加）+ **发起者的概念锚点**（「Edge 是给框架和人看的，节点本身不知道
Edge 的存在；`goto` 相当于 Edge 在节点中的一个标签」⇒ 静态边 = 框架层写死的边 · `goto` = 节点层
自己声明的边 ⇒ 同类 ⇒ 叠加自洽）**与上游一致** ✔

**落点**：FR-008 · 裁定 3 · parity **P-03**。

---

### D-03 · `goto=END` ⇒ **不产生跳转**（上游逐字特判 + 实测）

**上游源码**：`state.py:1771-1774`（见 D-01 代码块）—— `END` 被**特判**掉，注释逐字：
「END is a special case, it's not actually a node in a practical sense but rather a special
terminal node that we don't need to branch to」。

**实测**（`E-02`）：`a` 返回 `Command(goto=END, update=...)` 且 `a` 有静态边 `a→b` ⇒

```
结果: {'messages': ['from-a', 'from-b']}
```

⇒ `END` **不产生分支写**（静态边**照走**）✔
⇒ **freegraph 的裁定 5**（`END` = 「该位不产生动作」· 终止是**收敛**的结果）**与上游同款** ✔

**落点**：FR-007 · 裁定 5 · parity **P-04**。

---

### D-04 · `goto` 指向**不存在的节点** ⇒ 上游 **warning + 静默忽略**

**实测**（`E-04`）：`a` 返回 `Command(goto="no-such-node", update=...)` ⇒

```
Task a with path ('__pregel_pull', 'a') wrote to unknown channel branch:to:no-such-node, ignoring it.
结果: {'messages': ['from-a']}
```

⇒ 上游**只打一条 warning 就忽略** ⇒ 流程「悄悄少跑一段」，最终产出**看起来正常**、实则缺了一半。
⇒ **freegraph 的裁定 8**（**显式失败** · 内置 `ValueError` · 点名目标）**与上游分叉** ——
分叉理由：C6「未知 key 报错」的同款立场（**显式失败优于静默**）+ B7F1 的 V-2 同款（边的端点不在
节点表 ⇒ 显式失败）⇒ **登记为 parity 的可观察分叉**（**P-07**）。

**落点**：FR-007 · 裁定 8 · parity **P-07**。

---

### D-05 · `Command.PARENT` ⇒ 上游 **warning + 静默忽略**（作为 `goto` 目标时）

**上游源码**：`pregel/_io.py:56-59`（`map_command`）——

```python
def map_command(cmd: Command) -> Iterator[tuple[str, str, Any]]:
    """Map input chunk to a sequence of pending writes in the form (channel, value)."""
    if cmd.graph == Command.PARENT:
        raise InvalidUpdateError("There is no parent graph")
```

⇒ 上游的 `PARENT` 是**另一个字段** `graph=` 的取值（`types.py:821`）⇒ 上游「无父图」时报
**`InvalidUpdateError`**（**显式失败**）。
⚠️ 而 freegraph 的 `Command`（B1F1 冻结 · `types.py:32-83`）**没有 `graph` 字段** ⇒
`PARENT` 只能作为 **`goto` 目标**使用（字符串 `"__parent__"` · `types.py:64` / 上游 `types.py:848`）。

**实测**（`E-03`）：`a` 返回 `Command(goto=Command.PARENT, update=...)` ⇒

```
Task a with path ('__pregel_pull', 'a') wrote to unknown channel branch:to:__parent__, ignoring it.
结果: {'messages': ['from-a']}
```

⇒ **作为 `goto` 目标**时上游是 **warning + 忽略**（不是报错）⇒ **静默失效**。
⇒ **freegraph 的裁定 7**（**显式失败** · `NotImplementedError` · 点名「子图属 v2 能力」）**与上游分叉**
—— 分叉理由：`Command.PARENT` 是**合法常量**（不是写错了）只是**本版本未实现子图** ⇒
用 `NotImplementedError` 与「拼错名字」的 `ValueError` **区分**（发起者拍板 · 澄清轮 Q2），
且沿用仓库 `interrupt()`（`src/freegraph/_primitives.py`）未接线时的**同款用法**。
⇒ **登记为 parity 的可观察分叉**（**P-08**）。

**落点**：FR-005 · 裁定 7 · parity **P-08**。

---

### D-06 · 「槽位为空」⇒ 上游是**无操作**（不是异常）

**实测**（`E-05`）：`a` 返回 `Command(update={})` 且 `a` 有静态边 `a→b` ⇒

```
结果: {'messages': ['from-b']}
```

⇒ `a` **执行了**、**没写任何东西**、静态边**照走** ⇒ 「显式给了但内容为空」= **该位不产生动作** ✔
⇒ 与 **L1 的 `Command` docstring 逐字一致**（`src/freegraph/contracts/types.py:46-48`）
⇒ **freegraph 的裁定 10**（明确无操作）**与上游同款** ✔

**落点**：FR-006 · 裁定 10 · parity **P-05**。

---

### D-07 · **多目标** `goto` ⇒ 上游**全部**执行

**实测**（`E-06`）：`a` 返回 `Command(goto=["b", "c"], update=...)` ⇒

```
结果: {'messages': ['from-a', 'from-b', 'from-c']}
```

⇒ 两个目标**都**执行 ✔ ⇒ **freegraph 的裁定 9**（支持多目标 · 各自成边）**与上游同款** ✔
⚠️ **上游自己把「多条命令」归一**（`prebuilt/tool_node.py:895-910`）：

```python
        # combine all parent commands with goto into a single parent command
        parent_command: Command | None = None
        for output in flat_outputs:
            if isinstance(output, Command):
                if (
                    output.graph is Command.PARENT
                    and isinstance(output.goto, list)
                    and all(isinstance(send, Send) for send in output.goto)
                ):
                    if parent_command:
                        parent_command = replace(
                            parent_command,
                            goto=cast("list[Send]", parent_command.goto) + output.goto,
                        )
```

⇒ 上游把「多个命令」**归一**成「一条命令 + 拼接的 goto」⇒ **列表是实现层的便利形态**、不是独立语义
⇒ **freegraph 支持命令列表不引入新语义概念**（澄清轮第 2 次 Q1 的评估依据）。

**落点**：FR-007 · 裁定 9 / 裁定 15 · parity **P-06**。

---

### D-08 · **命令列表** ⇒ 上游支持（更新侧 + 分支侧都认列表）

**上游源码**：`state.py:1456-1484`（`_get_updates`）—— 列表里的每个 `Command` 的 `update`
**按列表顺序** `extend` 进同一份更新（`else` 分支还允许混入普通 `dict`）：

```python
            elif (
                isinstance(input, (list, tuple))
                and input
                and any(isinstance(i, Command) for i in input)
            ):
                updates: list[tuple[str, Any]] = []
                for i in input:
                    if isinstance(i, Command):
                        if i.graph == Command.PARENT:
                            continue
                        updates.extend(
                            (k, v) for k, v in i._update_as_tuples() if k in output_keys
                        )
                    else:
                        updates.extend(_get_updates(i) or [])
                return updates
```

⇒ **「列表顺序 = 生效顺序」**（上游逐字：`for i in input:` 顺序 `extend`）✔
⇒ **freegraph 的裁定 15**（命令列表 · 上游同款 · 按列表顺序依次生效）**有上游逐字依据** ✔
⚠️ **上游的空列表 ⇒ 报错**（`and input` 为假 ⇒ 落到 `else` 分支的 `InvalidUpdateError`）⇒
**freegraph 取「空列表 = 明确无操作」**（与裁定 10 的空槽位**同款**）⇒ **登记为可观察分叉**（**P-09**）。

**落点**：FR-001 / FR-004 · 裁定 15 · parity **P-09**。

---

### D-09 · `goto` 目标：**入参为空也照跑**、且**读得到本次 `update`**

**实测**（`E-07`）：`a` 返回 `Command(goto="z", ...)`，`z` 订阅的通道分三种情形 ⇒

```
  (1) z 订阅 other（全程无值）⇒ {'messages': ['from-z']} | z 入参 = {'messages': []}
  (2) z 订阅 messages（有值）    ⇒ {'messages': ['seed', 'from-z']} | z 入参 = {'messages': ['seed']}
  (3) goto + update               ⇒ {'messages': ['from-a', 'from-z']} | z 入参 = {'messages': ['from-a']}
```

⇒ ① 目标**订阅的通道没值** ⇒ **照跑**（入参里无值的 key **不出现** ⇒ 稀疏读同款）；
② 目标读的是**轮末合并后**的状态；③ **读得到源节点这次 `update` 的内容** ✔
⇒ **freegraph 的裁定 17**（照跑 · 入参 = 正常稀疏读 · 读轮末合并后的状态）**与上游同款** ✔
⇒ **freegraph 的依据**：`goto` = 一条边（裁定 1）⇒ **边触发源本就没有「有值」门槛**
（B7F1 FR-003 · 契约 §3.2「边触发源无值概念」）⇒ 既是边，就享受边的同款待遇。
⚠️ **如实登记的一处差异（非触发语义）**：上游节点默认读**整个 input schema**（稀疏），
而 freegraph 的入参是「**订阅集 ∩ 有值集**」（B7F1 裁定 2 的**更窄**口径）⇒
**入参的「范围」两者不同**，但**「跳过去就跑」这个触发语义完全一致**。

**落点**：FR-002 · 裁定 17 · parity **P-10**。

---

### D-10 · 「跳到哪里去了」在上游被记在哪 ⇒ **快照层**，不是「每步结果」

**实测**（`E-08`）：`a` 返回 `Command(goto="z", update=...)`，跑完后取 `get_state_history()` ⇒

```
  snapshot.next = ()                  | task names = []
  snapshot.next = ('z',)              | task names = ['z']
  snapshot.next = ('a',)              | task names = ['a']
  snapshot.next = ('__start__',)      | task names = ['__start__']
```

⇒ **第 2 步的 `next = ('z',)`** 就是 `a` 的 `goto="z"` 的落点 ⇒ 上游把「下一轮要执行谁」记在
**`StateSnapshot.next`**（`types.py:688-689`：「The name of the node to execute in each task for
this step」；计算处 `pregel/main.py:1379-1390`：`tuple(t.name for t in next_tasks.values() ...)`）。
⚠️ **上游没有「源 → 目标」的跳转映射字段**；debug 流里跳转痕迹是**通道名** ⇒

```
  debug task payload = {'id': '3c74d472-…', 'name': 'a', 'input': {...}, 'triggers': ('branch:to:a',)}
```

⇒ **freegraph 的裁定 18**（**不加字段** · 证据 = 下一轮 `executed` + **L1 的 `StateSnapshot.next`**
—— 与上游**逐字同款**的字段，B1F1 已冻结）**有上游依据** ✔ ⇒ B7F1 的**四字段冻结面不动** ✔

**落点**：FR-002 / FR-016 · 裁定 18 · parity **P-11**。

---

## §2 遗留登记（DR-1…DR-2 · **只登记 · 不改判据**）

| # | 遗留项 | 事实 | 处置 |
|---|---|---|---|
| **DR-1** | **上游的 `Command` 是**泛型** `Command[Literal[...]]`**（类型参数用于**图渲染**） | `types.py:799`（`class Command(Generic[N], ToolOutputMixin])`）+ 官方文档 `use-graph-api.md:2191`（类型参数「is necessary for the graph rendering and tells LangGraph that `node_a` can navigate to `node_b` and `node_c`」） | freegraph 的 `Command`（B1F1 冻结）**非泛型** ⇒ **图渲染侧无法逐字照抄上游写法** ⇒ 归 **B22F1**（`get_graph` / `draw_mermaid`）自行设计 ⇒ **本 feature 不受影响**（只登记） |
| **DR-2** | **freegraph 的触发源与上游的通道名**不可直接对照 | 上游用 `branch:to:<目标>` **通道**（`state.py:98` 的 `_CHANNEL_BRANCH_TO`）承载跳转；freegraph 用**边触发源** `("e", 源节点名)`（B7F1 裁定 3）⇒ 上游的 debug payload 里的 `triggers` 字段在 freegraph 侧**没有同名对应物** | 触发源的**暴露口径**归 **B19F1**（下游承接 **D-3** · 裁定 19）⇒ **本 feature 零越界**（SC-025） |

---

## §3 spec 事实性更正（C-1…C-2 · **只更正事实 · 未改任何判据**）

| # | 事实性表述 | 更正 | 影响 |
|---|---|---|---|
| **C-1** | spec 的 **Assumptions** 第 ① 条写「本 spec 的裁定 **1–14**」 | 澄清轮第 2 次后裁定已增至 **19** 条 ⇒ **已订正为 1–19** | **零判据影响**（纯计数） |
| **C-2** | spec 的 **依据 · 宪法**条写「本 spec 抬头的四条承接条款 + **两条**下游承接」 | 下游承接已增至 **三条**（**D-1** B12F1 · **D-2** B10F1 · **D-3** B19F1）⇒ **已订正为三条** | **零判据影响**（纯计数） |

⚠️ **两条均为澄清轮期间的**追加编辑**留下的计数漂移**（不是判据分歧）⇒ 已回写 spec
⇒ **SC-001…SC-025 全部仍成立** · **FR / SC 的编号与总数零变动**。

---

## §4 遗留的取证动作（**换上游版本时** MUST 重做）

| # | 动作 | 触发条件 | 落点 |
|---|---|---|---|
| 1 | **重新核实** 本文件 §1 引用的全部**上游行号**（`types.py:683-701` / `:798-848` · `graph/state.py:98` / `:1456-1493` / `:1498-1504` / `:1525-1530` / `:1551-1558` / `:1749-1775` / `:1778-1789` · `pregel/_io.py:56-78` · `pregel/main.py:1379-1390` · `pregel/_write.py:172-192` · `prebuilt/tool_node.py:895-910`） | 换上游版本时 | spec **FR-017** · SC-020 |
| 2 | **重跑** 一次性取证脚本（`/tmp/opencode/lg_b9f1_probe.py` · **不进仓库**）复核 **E-01…E-08** 的输出 | 换上游版本时 | 本文件 §1 |
| 3 | **把 freegraph 侧的实现放到 CI 最低档 3.11 上跑**（上游取证用的是 3.12 ⇒ **行为取证**与 freegraph 的 **3.11 承诺**是**两件事**） | 实现阶段（tasks） | spec **FR-017** / Assumptions「Python 基线」 |
