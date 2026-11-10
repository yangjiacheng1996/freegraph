# 研究记录（Phase 0）—— B5F2 · 稀疏状态读取 + 差分测试夹具

**Feature**: `B5F2` · **Spec**: [./spec.md](./spec.md) · **Plan**: [./plan.md](./plan.md)

> **本文件的用途与边界**（沿用 B5F1 / B4F1 的同款口径）：
> ① **决策记录** —— 每条决策附**实测命令 + 真实输出** ⇒ 满足宪法原则 VIII（证据与术语纪律）；
> ② **MUST NOT** 被测试解析（它是**证据表**，不是**判据**）—— 测试**直接断言行为** ⇒
> 避免「判据与实现同源 ⇒ 自证」；
> ③ 本文件的**全部实测**在**临时环境**完成（`langgraph` **不进**仓库依赖声明 · spec FR-018 / FR-020）。

---

## 0. 核实环境（所有行号与输出的来源）

| 项 | 值 |
|---|---|
| 上游版本 | **`langgraph` 1.2.11**（与 B5F1 的 parity 表**同一版本** ⇒ 行号可对照） |
| 核实方式 | **临时 venv**（`/tmp/opencode/lgvenv` · CPython **3.11.16**）⇒ **不进**仓库 `.venv`、**不进**任何依赖声明 |
| 依赖 | `uv pip install "langgraph==1.2.11"`（连带 `langchain-core` / `langsmith` 等 —— **仅在临时 venv 内**） |
| 核实日期 | **2026-11-09** |
| freegraph 侧 | 仓库 `.venv`（CPython **3.11.16**）· `freegraph 0.0.3`（editable） |

> ⚠️ **换上游版本后 MUST 重新核实全部行号**（宪法原则 VIII）⇒ **MUST NOT** 凭记忆沿用。
> ⚠️ **零出站红线**：上游核实**只在开发期**进行（临时 venv 内的 `pip install`）⇒
> **freegraph 自身**零出站（门禁 **G26 / G27** 不受本文件影响）。

---

## 1. 决策记录（D-01 … D-18）

### D-01 · 上游核实环境 = 临时 venv（**不进**仓库依赖）

**决策**：上游源码在**仓库之外**的临时 venv 中取得；仓库的 `[dependency-groups]` **只**加
`differential` 组（spec FR-018 / 裁定 5），且该组**仅供**差分夹具的 CI 作业使用。

**理由**：① 宪法原则 II（内核纯净）+ 门禁 **G21 / G22 / G3** 要求发行依赖闭包**为空集** ⇒
核实用的上游**不得**进 `[project].dependencies`；② 核实动作**一次性**（本 Phase 0 已完成）⇒
不需要把上游长期留在开发环境；③ 差分夹具的**运行**（CI 作业）才需要上游 ⇒ 那是**测试侧**依赖。

**落点**：spec FR-018 · 裁定 5 · `plan.md` 的 Technical Context。

---

### D-02 · `read_channels` 的入参形态 = `Mapping[str, BaseChannel]` ⇒ **与裁定 14 同构**

**实测**（`langgraph 1.2.11` · `pregel/_io.py:38-53`）：

```python
def read_channels(
    channels: Mapping[str, BaseChannel],
    select: Sequence[str] | str,
    *,
    skip_empty: bool = True,
) -> dict[str, Any] | Any:
```

**决策**：freegraph 的 `read_channels` 的通道入参 **MUST** 是「key → 通道」的映射
（spec 裁定 14 / FR-002）—— **该裁定被上游实测证实**。

**差异（形状）**：上游另有 **`select`** 参数（只读指定 key；为 `str` 时**返回单值**而非 `dict`）⇒
freegraph 的读取层**恒读全部**、**恒返回 `dict`** ⇒ 登记为**形状差异**（`P-05`）。

**落点**：spec 裁定 14（已更正为「已核实」）· `contracts/upstream-parity.md` P-02 / P-05。

---

### D-03 · `skip_empty` 的**缺省 = True** ⇒ **与上游同构**（更正 spec 裁定 22 的错误表述）

**实测**：源码 `skip_empty: bool = True`（`pregel/_io.py:42`）。

**决策**：freegraph 的 `skip_empty` 缺省 **MUST** 为 `True`（spec 裁定 22 / FR-007）——
**该裁定与上游同构**。

> ⚠️ **更正登记**：spec 裁定 22 曾写「上游的缺省与本裁定**相反**」⇒ **该表述不成立**，已更正
> （宪法原则 VIII：MUST NOT 输出无来源的事实性断言）。真正的形状差异在**返回类型**（D-02）。

**落点**：spec 裁定 22（已更正）· SC-027（已更正）· `contracts/upstream-parity.md` P-03。

---

### D-04 · 上游 `skip_empty=False` ⇒ **以 `None` 填充**（与裁定 3 分叉）⇒ 但**不可观察**

**实测**（E5'）：

```
skip_empty=True （缺省）⇒ {'filled': 7}                'empty' 缺席 = True
skip_empty=False      ⇒ {'filled': 7, 'empty': None}   'empty' 值为 None = None
```

**机理**（`pregel/_io.py:48-52`）：`read_channel(channels, k, catch=not skip_empty)`
⇒ `skip_empty=False` ⇒ `catch=True` ⇒ `read_channel` **捕获** `EmptyChannelError` 并**返回 `None`**
⇒ 无值 key **出现且值为 `None`**（**以 `None` 冒充「有值」**）。

**可观察性**（E6 · 全包 grep）：

```
含 'skip_empty' 的行数 = 2
  <langgraph>/langgraph/pregel/_io.py:42:    skip_empty: bool = True,
  <langgraph>/langgraph/pregel/_io.py:50:                values[k] = read_channel(channels, k, catch=not skip_empty)
```

⇒ **上游全包从未显式传 `skip_empty=False`** ⇒ 该分支**不可观察** ⇒ freegraph 的裁定 3
（**抛 `EmptyChannelError`**）与上游的分叉**在实践中不会显现**。

**决策**：**保留** spec 裁定 3 的口径（抛错）—— 理由：① 上游的「以 `None` 填充」会把
「**无值**」与「**值为 `None`**」**重新混判** ⇒ 直接违反 **B5F1 裁定 5** 的可分性；
② 该分支上游不用 ⇒ 不存在「等价性受损」的实际风险；③ 若将来上游启用该分支 ⇒ **DR-1** 触发重新评估。

**落点**：spec 裁定 3（已补上游对照）· `contracts/upstream-parity.md` P-04 · **DR-1**。

---

### D-05 · 上游的稀疏实现 = **捕获异常**；freegraph = `is_available()` 判定 ⇒ 机制差异 · 结果等价

**实测**（源码）：上游靠 `catch=not skip_empty` + 外层 `except EmptyChannelError: pass` 实现跳过；
freegraph 靠 B5F1 冻结的 `is_available()`（**恒不抛错**）判定。

**决策**：采纳 spec 裁定 3 的判定式实现 ⇒ 登记为**机制差异**（可观察语义等价）。

**落点**：spec 裁定 3 · `contracts/upstream-parity.md` P-01。

---

### D-06 · `local_read` 的 `fresh` **缺省 = False**（上游）⇒ freegraph **取 False**

**实测**（源码 `pregel/_algo.py:188-224`）：

```python
def local_read(
    scratchpad: PregelScratchpad,
    channels: Mapping[str, BaseChannel],
    managed: ManagedValueMapping,
    task: WritesProtocol,
    select: list[str] | str,
    fresh: bool = False,          # ← 缺省 False
) -> dict[str, Any] | Any:
```

**决策**：freegraph 的 `local_read(..., fresh=False)` **缺省取 `False`**（与上游一致）⇒
形状差异最小、迁移时不踩坑；**B8F1 MUST 显式传 `fresh=True`** 才拿到 fresh 视图
（spec FR-008 的「fresh 读模式」由此满足）。

> **spec 未冻结 `fresh` 的缺省** ⇒ 本条属 **plan 级决策**（spec FR-008 只要求「提供两种模式」）。

**落点**：spec FR-008 · `data-model.md` §3 · `contracts/read-contract.md` §3。

---

### D-07 · `local_read` 的**副本法**与上游**逐字同构** ⇒ 裁定 4 证实

**实测**（源码 `pregel/_algo.py:213-219`）：

```python
    if fresh:
        # apply writes
        local_channels: dict[str, BaseChannel] = {}
        for k in channels:
            cc = channels[k].copy()          # ← 复制通道
            cc.update(updated[k])            # ← 在副本上应用写入
            local_channels[k] = cc
        # read fresh values
        values = read_channels(local_channels, select)   # ← 从副本读
```

**实测**（E7 · 直接调用上游 `local_read`）：

```
通道当前值 = ['old']
local_read(fresh=True)  = {'messages': ['old', 'new']}
local_read(fresh=False) = {'messages': ['old']}
通道正式值（读后）= ['old']   ← 零污染 ✓
```

**决策**：freegraph 的 `local_read` **MUST** 走**同款副本法**（spec 裁定 4 / FR-008 / FR-009）——
**该裁定被上游实测证实**，且「零污染」在两侧**逐字一致**。

**落点**：spec 裁定 4 · `contracts/upstream-parity.md` P-06 · SC-005。

---

### D-08 · 上游的 `copy()` = `from_checkpoint(checkpoint())`；`checkpoint()` 返回**同一值对象**

**实测**（源码）：

```python
class BaseChannel:
    def copy(self) -> Self:
        """Return a copy of the channel.
        By default, delegates to `checkpoint()` and `from_checkpoint()`."""
        return self.from_checkpoint(self.checkpoint())

    def checkpoint(self) -> Checkpoint | Any:
        try:
            return self.get()          # ← 返回**同一值对象**（浅共享）
        except EmptyChannelError:
            return MISSING
```

**决策**：freegraph 的 `Channel` 抽象（**B5F1 冻结面 · 不可变**）**没有** `copy()` 方法 ⇒
读取层**改用标准库 `copy.copy`**（见 D-09）⇒ 登记为**机制差异**（两侧都**浅共享** ⇒ 语义等价）。

**落点**：spec 裁定 4 · `contracts/upstream-parity.md` P-07 · **DR-4**。

---

### D-09 · `copy.copy` 对 B5F1 的 `__slots__` 通道**实测可行** ⇒ 副本法的实现前提成立

**实测**（仓库 `.venv` · CPython 3.11.16）：

```
--- copy.copy（副本法的实现前提）---
  LastValue 副本: LastValue | reducer 同一引用: True
  BinOp 原值: ['a'] | 副本值: ['a', 'b']   ← 原值未被污染
  副本无 __dict__: True | 槽位: ()
```

**决策**：读取层 MUST 用 `copy.copy(channel)` 实现副本 ⇒ 前提成立：
① `__slots__` 类可被 `copy.copy` 复制（CPython **3.11** 的 `object.__getstate__` 处理 slots）；
② 副本**无** `__dict__`（B5F1 裁定 17 ① 的结构纪律**不被破坏**）；
③ **归约器按引用**保持同一（FR-014）⇒ 副本的归约行为与原通道**一致**。

**落点**：spec 裁定 4 · `data-model.md` §4 · `contracts/read-contract.md` §4。

---

### D-10 · **就地修改型**归约器 ⇒ 副本法**会**污染原值（两侧**同样**如此）

**实测**（仓库 `.venv`）：

```
--- 就地修改型归约器的污染面（上游同样存在）---
  原值: ['a', 'b']  副本值: ['a', 'b']   ← 浅共享 ⇒ 同样污染（上游 checkpoint() 亦浅共享）
```

**决策**：**不**为此在读取层深拷贝 —— ① 深拷贝会破坏用户对象身份（spec FR-005）且对不可拷贝对象
**会失败**；② 上游**同样**浅共享（D-08）⇒ **两侧同构**，不构成等价性缺口。
⇒ 登记为**已知的浅共享面**（`contracts/read-contract.md` MUST 写明）。

**落点**：spec FR-005 / 裁定 10 · `contracts/read-contract.md` §4 · **DR-4**。

---

### D-11 · **C4 的上游实测证据**（判据 A1 / A2 的上游侧）

**实测**（E1' · 初始输入只给 `messages`）：

```
节点入参 type = dict   keys = ['messages']
'llm_calls' in 入参 = False          ← C4 的否定式断言
入参.get('llm_calls', 0) = 0         ← C4 的 default 断言
'never_written' in 入参 = False
最终输出 keys = ['messages']         （无值 key 不出现在输出里）
```

⇒ 与 Q8 §3.2.1 记录的实测（`NODE_INPUT_KEYS: ['messages']` · `HAS_llm_calls: False`）**逐字一致**
⇒ **判据 A1 / A2 的上游侧已具备可复现的对照值** ⇒ 差分夹具的「节点入参」投影**有基准**。

**落点**：spec SC-001 / SC-002 · `contracts/differential-fixture.md` §3。

---

### D-12 · **初始输入 = 一次写入** ⇒ 裁定 16 证实

**实测**（E2）：初始输入里的 key **全部**出现在节点入参里（`keys = ['llm_calls','messages','never_written']`）
⇒ 初始输入**确实进了通道** ⇒ 与上游「`invoke(input)` 把入参当一次写入」**同构**。

**落点**：spec 裁定 16 / FR-029 · `contracts/upstream-parity.md` P-08。

---

### D-13 · **值为 `None` 的通道出现在入参里** ⇒ 裁定 9 证实

**实测**（E1''）：节点写入 `{"a": None}` 后，下一个节点的入参 `keys = ['a','b']` 且 `a` 的值为 `None`
⇒ 「**值为 `None`**」的通道**有值** ⇒ **出现** ⇒ 与上游**同构**。

**落点**：spec 裁定 9 / FR-006 · `contracts/upstream-parity.md` P-09。

---

### D-14 · **空更新口径**（spec FR-034 的待冻结项）⇒ **冻结为「计入 · 写入投影为 `None`」**

**实测**（E3' · 三种写法）：

```
节点返回 {}        ⇒ 事件数 = 2   事件 = [{'a': None}, {'b': {'messages': ['z']}}]
节点返回 None      ⇒ 事件数 = 2   事件 = [{'a': None}, {'b': {'messages': ['z']}}]
节点返回 {'x': 1}  ⇒ 事件数 = 2   事件 = [{'a': None}, {'b': {'messages': ['z']}}]
```

**决策（口径冻结）**：在 `stream_mode="updates"` 下，**「节点执行了但没有产生任何写入」**
⇒ 事件序列**计入**一条，其「写入」投影为 **`None`**（**不是** `{}`、**不是**缺席）。
⇒ freegraph 侧的规格驱动器 MUST 产出**同一形态** ⇒ 否则「事件序列一致」会稳定报**假差异**。

⇒ **裁定 7 的归一化形态据此精确化**：`(步序, 节点名, 写入)` 中的「写入」字段
MUST 取「该节点本步产生的更新；无更新 ⇒ `None`」。

**落点**：spec FR-034 / 裁定 7 / 裁定 23（已闭合）· SC-028 · `contracts/differential-fixture.md` §4。

---

### D-15 · 上游对**未知 key 的写入** = **静默丢弃** ⇒ freegraph 与**立项书 C6**「未知 key 报错」**一致** ⇒ 登记为「**上游偏离**」

**实测**（E8）：节点返回 `{"x": 1}`（`x` 不在 schema）⇒ 上游**未抛错**，该次更新被**静默丢弃**
（事件为 `{'a': None}`）。

**决策**：① freegraph **保留**「未知 key ⇒ 显式失败」的口径（spec FR-011 ③ / Edge Cases）——
理由：① **权威口径在立项书一侧** —— Q8 契约的 **C6「节点返回值合并」**逐字写「**未知 key 报错**」
⇒ freegraph 与 C6 **一致**；⇒ **偏离方是上游**（`langgraph 1.2.11` **静默丢弃**）⇒ 本条登记为
「**上游偏离**」（**非**「freegraph 与上游的语义分叉」）；② 上游的静默丢弃会让**用户的拼写错误
无声消失**（与 B5F1「非法输入 MUST 显式失败」同立场）；③ 但 ⇒ **差分夹具 MUST NOT 让图规格
产生未知 key 的写入**（夹具侧**前置校验**）⇒ 否则两侧「一方失败、一方成功」⇒ 判定为「**不等价**」
而非「等价地失败」⇒ 假差异；④ 该场景由 freegraph 的**单元测试独占断言**（显式失败），
**不进入**双侧比对。

**落点**：spec FR-011 · 裁定 19 · `contracts/differential-fixture.md` §5 · **DR-2** ·
`contracts/upstream-parity.md` §2（实测基线表末行）。

---

### D-16 · **函数式 `TypedDict`** 可被 B4F1 解析 ⇒ 裁定 21 的实现前提成立

**实测**（仓库 `.venv`）：

```
函数式 TypedDict 解析成功 ✓
  keys = ('messages', 'llm_calls')
  channels = {'messages': (ChannelSpec, <class 'list'>, True), 'llm_calls': (ChannelSpec, <class 'int'>, False)}
  build_channels = {'messages': 'BinaryOperatorAggregate', 'llm_calls': 'LastValue'}
```

⇒ `typing.TypedDict("名称", {...})` 的**函数式**写法**既能被上游接受**（它要求真 `TypedDict`），
**也能被 B4F1 的 `parse_state_schema` 解析** ⇒ 裁定 21 的「一份数据源 + 两侧消费同一个对象」**可行**。

**落点**：spec 裁定 21 / FR-033 · `contracts/differential-fixture.md` §2 · SC-026。

---

### D-17 · 上游通道的**构造签名**与 freegraph 不同 ⇒ 形状差异（**B5F1 已冻结 freegraph 侧**）

**实测**（上游 1.2.11）：

```
BaseChannel            (self, typ: Any, key: str = '')
LastValue              (self, typ: Any, key: str = '')
BinaryOperatorAggregate(self, typ: type[Value], operator: Callable[[Value, Value], Value])
```

⇒ 上游把 **`typ` 放第一位**、`key` 是**可选**的**第二**参数；`BinaryOperatorAggregate` **根本没有 key 参数**
（key 由 `from_checkpoint` 另行赋值）⇒ 与 freegraph 的 `Channel(key, value_type)` **形状不同**。

**决策**：**不改动** freegraph 侧（B5F1 的**冻结面** · 四个操作 + 四个属性 + 构造签名逐字冻结）⇒
仅**登记**为形状差异。

**落点**：spec 裁定 2 / FR-026 · `contracts/upstream-parity.md` P-10。

---

### D-18 · 上游 `local_read` 的**签名**远比 freegraph 复杂 ⇒ 形状差异（**B8F1 需适配**）

**实测**（上游 1.2.11）：

```python
def local_read(scratchpad, channels, managed, task, select, fresh=False) -> dict[str, Any] | Any:
```

⇒ 上游的 `local_read` 还承担 **managed 值**（`managed` 通道）的读取与 `select` 的 str/序列双形态 ⇒
freegraph 的简化签名（`channels` + `writes` + `fresh`）是**自己的形态** ⇒ 登记为形状差异 ⇒
**B8F1** 在 freegraph 侧用 `local_read` 实现路由读时**MUST NOT** 假设上游的 managed 语义。

**落点**：spec 裁定 4 / FR-008 · `contracts/upstream-parity.md` P-11 · **DR-3**。

---

## 2. 遗留登记（DR-1 … DR-5 · 只登记 · 不改判据）

| # | 事项 | 事实依据 | 处置 | 触发重新评估的信号 |
|---|---|---|---|---|
| **DR-1** | 上游 `skip_empty=False` 分支**以 `None` 填充**（与裁定 3 分叉），但**全包从未被显式使用** | E5' + E6（`skip_empty` 全包仅 2 处） | 保留裁定 3（抛错）⇒ 登记为「**不可观察**的语义差异」 | 上游**开始显式传** `skip_empty=False` ⇒ 需在 parity 表升级为「可观察的语义差异」并重新裁定 |
| **DR-2** | 上游对**未知 key 的写入**静默丢弃 ⇒ **上游偏离**（freegraph 与**立项书 C6**「未知 key 报错」**一致**） | E8 + Q8 契约 **C6** | 差分夹具**前置校验**未知 key ⇒ 该场景**不进入**双侧比对；由 freegraph 单元测试独占断言；parity 表末行改记「**上游偏离**」 | 差分夹具需要覆盖「未知 key」场景时 ⇒ 须先裁定 freegraph 是否改为静默丢弃（**不建议**） |
| **DR-3** | 上游 `local_read` 的签名含 `scratchpad` / `managed` / `task` / `select`；freegraph 的简化 | 上游 `pregel/_algo.py:188-201` | 登记为**形状差异**；**B8F1** MUST NOT 假设 managed 语义 | B8F1 需要 managed 值语义时 ⇒ 另立 feature |
| **DR-4** | **就地修改型**归约器会让副本法污染原值（浅共享） | D-08 + D-10（实测） | **两侧同构** ⇒ 登记为**已知的浅共享面**，写入 `read-contract.md`；**不**改实现 | 用户要求「fresh 读绝对零污染」时 ⇒ 需引入深拷贝（**代价**：破坏对象身份 + 不可拷贝对象会失败） |
| **DR-5** | 立项书 §9.2「fake 模型的注入机制」的**落点含 B5F2（差分夹具）**（`harness/proposals/立项书.md:1068`）⇒ 「**差分夹具与 fake 轮共用同一套注入机制**」（§4.2 **S5**） | 立项书 §9.2「fake 模型的注入机制」表 · §4.2 S5 | 本 feature 只交付**纯本地**规格 + **预留「模型工厂」钩子**（本 feature **恒空** ⇒ 非空即**显式失败**）⇒ fake 注入的实现归 **B25F1**（M4）⇒ 承接条款按宪法 **v1.8.0**「跨 feature 承接的接线通则」写入 `harness/features/B25F1_双跑验收与迁移说明.md`（**只接线**）⇒ **只登记、不改判据**（spec 裁定 26 · FR-036 · SC-030） | **B25F1** 的 spec 落成 FR + 裁定时 ⇒ 本条即可闭合；若 **B25F1** 被重排 ⇒ MUST 重新指名承接方 |

> **📌 DR-5 的处置原则**：本条**不**改任何 FR / SC 的**判据** —— 本 feature 的图规格**恒为纯本地**
> （差分夹具的节点函数 MUST 零网络 · 裁定 13），与立项书 §9.2 的「fake 轮」是**两件事**；
> 「共用同一套注入机制」的**落点**由**承接条款**兑现（**B25F1** 提供 fake 模型工厂 ⇒ 差分夹具
> 可跑**模型形状**的图规格）⇒ 立项书的口径**未被否定**，只是**分棒交付**。

---

## 3. 与 spec 的**差异登记**（本 Phase 0 发现 ⇒ 已回写 spec）

| # | spec 位置 | 原表述 | 更正后 | 依据 |
|---|---|---|---|---|
| **C-1** | 裁定 22（上游对照段） | 「上游 `read_channels` 的缺省与本裁定**相反**」 | 「上游的缺省**也是** `True` ⇒ **与上游同构**；真正的差异在**返回类型**」 | D-03（源码 `skip_empty: bool = True`） |
| **C-2** | 裁定 22（上游对照段） | —— | 追加：「上游 `skip_empty=False` **以 `None` 填充**（分叉）· 但该分支上游**从不使用** ⇒ **不可观察**」 | D-04（E5' + E6） |
| **C-3** | 裁定 3（上游对照段） | 「上游靠捕获 `EmptyChannelError` 实现跳过」 | 保留 + 追加「`skip_empty=False` 分支的分叉与不可观察性」 | D-04 / D-05 |
| **C-4** | 裁定 14（依据段） | 「上游 `read_channels` 的入参形态按 Q8 引用**未能逐字核实** ⇒ plan 阶段 MUST 重新核实」 | 「已核实 = `Mapping[str, BaseChannel]` ⇒ **与本裁定同构**」 | D-02（源码 `_io.py:38-41`） |
| **C-5** | SC-027 | 「该缺省与上游相反一事 MUST 已在与上游对照文档中登记」 | 改为「上游 `skip_empty=False` 以 `None` 填充 · 上游从不使用该分支」+「上游返回类型依 `select` 而变」两条事实的登记 | D-03 / D-04 / D-02 |

> **处置原则**：本 Phase 0 的实测**只更正事实性表述**（宪法原则 VIII）⇒ **未**改动任何 FR / SC 的**判据**；
> 若更正导致某条判据**不再可判定**，才需回到 spec —— 本次**未发生**（逐条复核：SC-001…SC-030 **全部仍成立**）。

---

## 4. 与 spec 裁定**一致**的实测（无需更正的部分）

| spec 裁定 | 实测证据 | 结论 |
|---|---|---|
| 裁定 9（「空」=「无值」≠「假值」） | D-13（值为 `None` 的通道**出现**在入参里） | ✅ **证实** |
| 裁定 16（初始输入 = 一次写入） | D-12（初始输入的 key 全部进通道） | ✅ **证实** |
| 裁定 4（fresh 读 = 副本法 · 零污染） | D-07（上游同款副本法 · 读后正式值不变） | ✅ **证实** |
| 裁定 3（稀疏 = 判定式 · `skip_empty=False` 抛错） | D-05（机制差异）· D-04（分叉但不可观察） | ✅ **证实**（+ DR-1） |
| 裁定 14（入参 = key→通道映射） | D-02（上游同款 `Mapping`） | ✅ **证实** |
| 裁定 22（`skip_empty` 缺省 = True） | D-03（上游缺省也是 `True`） | ✅ **证实**（+ C-1 更正） |
| 裁定 21（schema = 字段描述 + 动态构造 `TypedDict`） | D-16（函数式 `TypedDict` 可被 B4F1 解析） | ✅ **证实** |
| 裁定 5（依赖隔离） | D-01（临时 venv · 不进仓库） | ✅ **证实** |
