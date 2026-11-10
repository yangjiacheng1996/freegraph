# 上游语义对照表（LangGraph → freegraph）—— B5F2 的**证据表**

**Feature**: `B5F2` · **Spec**: [../spec.md](../spec.md) · **契约权威**: [read-contract.md](./read-contract.md)

> **核实环境**：`langgraph` **1.2.11**（`…/site-packages/langgraph/`）· CPython **3.11.16**
> —— 核实于 **2026-11-09**（**临时 venv** · 不进仓库依赖声明 · spec FR-018 / 裁定 5）。
> ⚠️ **换上游版本后 MUST 重新核实全部行号**（宪法原则 VIII）⇒ **MUST NOT** 凭记忆沿用。
>
> **本表的用途与边界**（沿用 B5F1 的 `upstream-parity.md` 同款口径）：
> ① **证据表** —— 逐条标注「freegraph 的口径 ↔ 上游的实现 ↔ 上游行号」⇒ 满足 spec FR-028
> 与宪法原则 VIII；② **MUST NOT** 被测试解析（测试**直接断言行为** ⇒ 避免「判据与实现同源 ⇒ 自证」）；
> ③ **零依赖** —— 上游**不进**仓库依赖声明、不进基础 CI。
> ④ 与 B5F1 的 `upstream-parity.md` **同版本**（1.2.11）⇒ **P-01…P-04** 的行号可直接对照。

---

## 1. 对照表（**12 条**）

> ✅ **P-12 的上游侧已实测**（**2026-11-10** · 任务 **T044** · `langgraph 1.2.11`）
> ⇒ **上游 `local_read` 对「待写入映射里有、但通道映射里没有」的 key **静默丢弃**
> （**未抛错**）⇒ 归入「**上游偏离**」⇒ 本表 **12 条全部有实测依据**。
> ⚠️ **换上游版本后 MUST 重新核实全部行号**（宪法原则 VIII）。

| # | 语义点 | freegraph 口径 | 上游实现 | 上游行号（`langgraph 1.2.11`） | 差异 |
|---|---|---|---|---|---|
| **P-01** | **稀疏的实现机制** | `is_available()` 判定（**恒不抛错**） | `read_channel(channels, k, catch=not skip_empty)` + 外层 `except EmptyChannelError: pass` | `pregel/_io.py:48-52` | **机制不同** ⇒ **可观察语义等价**（C4 的结果一致） |
| **P-02** | **入参形态** | `Mapping[str, Channel]`（**恒读全部**） | `channels: Mapping[str, BaseChannel]`（+ `select` 参数选 key） | `pregel/_io.py:39-41` | **形状不同**（freegraph 无 `select`） |
| **P-03** | **`skip_empty` 缺省** | `True` | `skip_empty: bool = True` | `pregel/_io.py:42` | **无**（与上游**同构**） |
| **P-04** | **`skip_empty=False`** | 读到无值 ⇒ **抛 `EmptyChannelError`** | `catch=True` ⇒ **以 `None` 填充**（无值 key 出现且值为 `None`） | `pregel/_io.py:26-33` · `:50` | **语义不同** ⇒ 但该分支**上游全包从未显式使用**（`skip_empty` 仅 2 处）⇒ **不可观察**（research **D-04** / **DR-1**） |
| **P-05** | **返回类型** | **恒为 `dict`** | `dict[str, Any] \| Any`（`select` 为 `str` ⇒ 返回**单值**） | `pregel/_io.py:44-53` | **形状不同**（freegraph 更窄、更可判定） |
| **P-06** | **fresh 读的构造** | **副本法**：复制通道 → 在副本上 `update` → 从副本读 | **同款**：`cc = channels[k].copy(); cc.update(updated[k]); read_channels(local_channels, select)` | `pregel/_algo.py:213-219` | **无**（语义**逐字同构**） |
| **P-07** | **通道的复制机制** | 标准库 `copy.copy`（B5F1 的 `Channel` 抽象**无** `copy()`） | `BaseChannel.copy()` = `from_checkpoint(checkpoint())`；`checkpoint()` 返回**同一值对象** ⇒ 浅共享 | `channels/base.py:38-46` · `:63-70` | **机制不同** ⇒ **浅共享语义等价**（research **D-08** / **D-09**） |
| **P-08** | **初始输入** | 视为**一次写入**（走通道自身的写入语义） | `invoke(input)` 把入参当**一次写入**（实测：入参的 key 全部进通道） | 实测 E2（`langgraph 1.2.11`） | **无** |
| **P-09** | **「值为 `None`」的通道** | **有值** ⇒ 出现（值为 `None`） | **出现**（实测 E1''：写入 `None` 后该 key 仍在入参里） | 实测 E1''（`langgraph 1.2.11`） | **无** |
| **P-10** | **通道构造签名** | `Channel(key, value_type)`（B5F1 **冻结面**） | `BaseChannel(typ, key="")` · `BinaryOperatorAggregate(typ, operator)`（**无 key 参数**） | `channels/base.py:52-54` · `channels/binop.py` | **形状不同**（freegraph 侧**不改动** · research **D-17**） |
| **P-11** | **`local_read` 的签名** | `(channels, writes, *, fresh=False)` | `(scratchpad, channels, managed, task, select, fresh=False)` | `pregel/_algo.py:188-201` | **形状不同**（freegraph **不实现** `managed` · research **D-18** / **DR-3**） |
| **P-12** | **`local_read` 遇「待写入映射里有、但通道映射里没有」的 key** | **抛 `InvalidChannelUpdateError`**（其 `key` 字段指向那个未知 key）⇒ **MUST NOT** 静默丢弃（FR-011 / 裁定 19） | **静默丢弃**（**实测 E3 · 2026-11-10 · 任务 T044**）—— 上游 `local_read` 只把 **`select` 里出现**的 key 收进 `updated` ⇒ 未知 key **被丢弃** ⇒ **未抛错** | `pregel/_algo.py:208-210`（`for c, v in task.writes: if c in select`）· 实测 E3 | **上游偏离** —— freegraph 与 **C6**「未知 key 报错」**一致**，上游**静默丢弃** ⇒ 该场景 **不进入**差分比对（`differential-fixture.md` §5）⇒ 由 freegraph 的**单元测试独占断言**（research **D-15** / **DR-2**） |

> **📌 实测 E3（2026-11-10 · `langgraph 1.2.11` · CPython 3.11.16 · 任务 **T044**）**：
>
> ```python
> from langgraph.pregel._algo import local_read
> from langgraph.channels import LastValue
>
> class Task:
>     writes = [("unknown_key", 42)]
>
> ch = {"a": LastValue("a")}
> ch["a"].update([1])
> local_read({}, ch, {}, Task(), ["a"], fresh=True)
> # ⇒ {'a': 1}   ← **未抛错**（未知 key 被静默丢弃）
> ```
>
> ⇒ **结论**：上游 **P-12 的上游侧已实测** ⇒ 本表 **12 条全部有实测依据**
> （**10 条**带 `路径:行号` + **2 条**带实测编号 · **P-12** 现补齐）。
> ⚠️ **换上游版本后 MUST 重新实测该条**（宪法原则 VIII）。

---

## 2. 上游的**实测基线**（差分夹具的比对基准 · research §1 D-11 / D-14）

> 下表是**上游侧的可复现观测值** ⇒ 差分夹具的「节点入参 / 输出状态 / 事件序列」三项投影
> MUST 与之**逐项一致**（spec FR-016 · SC-006 / SC-007）。

| 场景 | 上游观测（`langgraph 1.2.11`） |
|---|---|
| **C4 · 稀疏入参**（初始输入只给 `messages`） | 节点入参 `type = dict` · `keys = ['messages']` · `'llm_calls' in 入参 = False` · `入参.get('llm_calls', 0) = 0` · 最终输出 `keys = ['messages']` |
| **初始输入**（给了三个 key） | 节点入参 `keys = ['llm_calls','messages','never_written']`（**全部出现**）⇒ 初始输入进了通道 |
| **归约语义**（两节点各写一次 `messages`） | `['a', 'b']` ⇒ `operator.add` 的归约结果一致 |
| **空更新**（节点返回 `{}` / `None` / 未知 key） | `stream_mode="updates"` 一律产出 `{'<node>': None}` ⇒ **计入**事件序列，「写入」投影为 **`None`** |
| **「写入」投影的语义** | 该「写入」= **节点函数返回的部分状态**（**原样 · 未归约**）—— 与 `contracts/differential-fixture.md` §3.3 的定义**逐字一致** |
| **fresh 读**（`local_read(fresh=True)`） | `{'messages': ['old', 'new']}`（含本次写入）· `fresh=False` ⇒ `{'messages': ['old']}` · 读后通道正式值**不变** |
| **条件边读 fresh**（路由函数） | 读到 `['new']` ⇒ 含本节点刚写的值（**C8** 的上游基线 · **B8F1** 用） |
| **未知 key 的写入** | **静默丢弃**（未抛错）⇒ freegraph 与**立项书 C6**「未知 key 报错」**一致**；上游 **静默丢弃** ⇒ 登记为「**上游偏离**」（research **D-15** / **DR-2**）—— **实测 E3**（2026-11-10 · 见 **P-12** 的实测记录） |

---

## 3. 逐条行号复核（示例：P-04 的 `skip_empty=False` 分支）

```python
# langgraph/pregel/_io.py:26-33（read_channel）
def read_channel(channels, chan, *, catch: bool = True) -> Any:
    try:
        return channels[chan].get()
    except EmptyChannelError:
        if catch:
            return None          # ← skip_empty=False ⇒ catch=True ⇒ 以 None 填充
        else:
            raise

# langgraph/pregel/_io.py:38-53（read_channels）
def read_channels(channels, select, *, skip_empty: bool = True) -> dict[str, Any] | Any:
    ...
    for k in select:
        try:
            values[k] = read_channel(channels, k, catch=not skip_empty)
        except EmptyChannelError:
            pass                   # ← skip_empty=True ⇒ raise ⇒ 被吞 ⇒ key 缺席（C4）
```

**可观察性的复核**（`grep -rn "skip_empty" <langgraph>/`）：

```
<pregel>/pregel/_io.py:42:    skip_empty: bool = True,
<pregel>/pregel/_io.py:50:                values[k] = read_channel(channels, k, catch=not skip_empty)
```

⇒ **全包 2 处** ⇒ 无任何调用点显式传 `skip_empty=False` ⇒ **P-04 的分叉不可观察**。

---

## 4. 与 B5F1 的对照表的关系

| 本表 | B5F1 的 `upstream-parity.md` | 关系 |
|---|---|---|
| P-01 … P-04（读取侧） | —— | 本表**新增**（读取层） |
| P-08（初始输入 = 一次写入） | B5F1 的 **P-07**（首次写入直存） | **依赖**：初始输入按写入语义进通道 ⇒ 首次写入直存的规则**沿用** |
| P-09（值为 `None`） | B5F1 的 **P-04**（有值 / 无值判定） | **同源**（`is_available()` / `get()` 抛 `EmptyChannelError`） |
| P-10（构造签名） | —— | 本表**新增**（形状差异 · freegraph 侧**不改动**） |

> ⚠️ **本表与 B5F1 的表 MUST 保持版本一致**（同为 `langgraph 1.2.11`）⇒ 若任一方升级上游版本，
> **另一方 MUST 同步重新核实**（宪法原则 VIII）。
