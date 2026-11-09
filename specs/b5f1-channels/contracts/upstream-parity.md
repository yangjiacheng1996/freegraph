# 上游语义对照表（LangGraph → freegraph）—— B5F1 的**证据表**

**Feature**: `B5F1` · **Spec**: [../spec.md](../spec.md) · **契约权威**: [channel-contract.md](./channel-contract.md)

> **核实环境**：`langgraph` **1.2.11**（`…/site-packages/langgraph/`）· CPython **3.12.3**
> —— 核实于 **2026-11-08**。
> ⚠️ **换上游版本后 MUST 重新核实全部行号**（宪法原则 VIII · spec FR-021）⇒ **MUST NOT** 凭记忆沿用。

> **本表的用途与边界**：
> ① **证据表** —— 逐条标注「freegraph 的口径 ↔ 上游的实现 ↔ 上游行号」⇒ 满足 spec FR-021
> （与上游的语义对应**须标注源码行号**）与宪法原则 VIII；
> ② **MUST NOT** 被测试解析 —— 与 B4F1 的 `binary-criterion.md` **相反**：那一份是**判据**
> （测试必须解析它，否则判据与断言同源 ⇒ 自证），本份是**证据**（测试**直接断言行为**，
> 解析证据表反而会让人「照着表写实现」⇒ 判据与实现同源）。
> ③ **零依赖** —— 上游**不进**仓库依赖声明、不进 CI（沿用 B4F1 澄清 Q5 的口径）。

---

## 1. 对照表（§2 = 逐条对照 · **12 条**）

| # | 语义点 | freegraph 口径 | 上游实现 | 上游行号（`langgraph 1.2.11`） | 差异 |
|---|---|---|---|---|---|
| P-01 | **覆盖语义** | `LastValue.update([v])` ⇒ 值 == `v`（旧值丢弃 · C3） | `self.value = values[-1]` | `channels/last_value.py:66` | **无** |
| P-02 | **一步内多值 ⇒ 失败** | 抛 `InvalidChannelUpdateError`；**值不变** | 抛 `InvalidUpdateError` | `channels/last_value.py:56-64` | 异常**类型名**不同（freegraph 自有类型） |
| P-03 | **写入空序列** | 无操作（返回假） | `if len(values) == 0: return False` | `channels/last_value.py:57-58` | **无** |
| P-04 | **有值 / 无值判定** | `is_available()`（恒不抛错）+ `get()` 抛 `EmptyChannelError` | `is_available()` / `get()` 抛 `EmptyChannelError` | `channels/last_value.py:69-75` | 异常**类型名**不同 |
| P-05 | **空值推导** | 剥 `Annotated`/`Required`/`NotRequired` → 抽象容器映射 → `typ()`；失败 ⇒ 初始「无值」 | `_strip_extras` → 抽象容器映射 → `try: typ() except Exception: MISSING` | `channels/binop.py:22-28` · `:82-92` | **剥离口径不同**（窄 vs 宽）⇒ **空值结果等价** |
| P-06 | **抽象容器映射** | `Sequence`/`MutableSequence`→`list`；`Set`/`MutableSet`→`set`；`Mapping`/`MutableMapping`→`dict` | 同 6 项 | `channels/binop.py:83-88` | **无** |
| P-07 | **首次写入的 `current`** | 通道**无值** ⇒ **直存**（归约器调用次数 == 0） | `if self.value is MISSING: self.value = values[0]` | `channels/binop.py:126-128` | **无** |
| P-08 | **归约调用形式** | `值 = reducer(写入前的值, 新值)`；多值**按序** | `self.value = self.operator(self.value, value)` | `channels/binop.py:143`（`update` 全段 `:123-144`） | **无** |
| P-09 | **归约失败不污染状态** | 赋值只在 reducer 返回后发生 ⇒ 值不变 | 同（同一行结构） | `channels/binop.py:143` | **无** |
| P-10 | **路由通道清空** | **显式** `clear()` ⇒ 无值 | 对本步未更新的通道调 `update(EMPTY_SEQ)` ⇒ `value = MISSING` | `channels/ephemeral_value.py:55-60` · `pregel/_algo.py:326-334` | **机制不同** ⇒ **可观察语义等价** |
| P-11 | **路由通道一步内多值** | 抛 `InvalidChannelUpdateError` | 抛 `InvalidUpdateError`（guard） | `channels/ephemeral_value.py:62-65` | 异常**类型名**不同 |
| P-12 | **清空语义（三类统一）** | 三类通道的 `clear()` **一律** ⇒ 无值 | **上游无 `clear()` 方法** —— 步末靠 `update(EMPTY_SEQ)`，而**三类通道反应不同**：覆盖型 **no-op**（值保留）· 归约型 **no-op**（值保留）· 路由型 ⇒ `MISSING` | `channels/base.py:19-121`（`BaseChannel` **无** `clear`）· `channels/last_value.py:56-58` · `channels/binop.py:123-125` · `channels/ephemeral_value.py:55-61` | **机制不同**（freegraph 新增显式操作）⇒ **可观察语义等价的落点是「步末调用哪些通道」**（**B7F1**：步末**只**清路由型 · 裁定 17 ② · contract §7 `B-2`） |

## 2. 调度层侧的对照（供 B7F1 / B5F2 参考 · 本 feature **不实现**）

| # | 语义点 | 上游实现 | 上游行号 | 对 freegraph 的含义 |
|---|---|---|---|---|
| S-01 | **本步写入批量交给通道** | `channels[chan].update(vals)` | `pregel/_algo.py:317-320` | ⇒ 通道的写入接口是**批量**（spec FR-002） |
| S-02 | **用 `update()` 的返回值判断「本步是否更新过通道」** | `if channels[chan].update(vals) … updated_channels.add(chan)` | `pregel/_algo.py:319-324` | ⇒ **`update()` 的返回值语义必须是「本次写了值」**（spec FR-002 📌 · 澄清轮 Q5） |
| S-03 | **C4 稀疏读 = 跳过抛 `EmptyChannelError` 的通道** | `read_channels` 捕获 `EmptyChannelError` 后 `pass` | `pregel/_io.py:38-53` | ⇒ B5F2 直接照搬该口径；本 feature 只保证「有值 / 无值」**完全可判定** |
| S-04 | **映射规则** | `_get_channel`：先剥 `Required`/`NotRequired` → 有归约器走 `_is_field_binop` → 否则 `LastValue` 兜底 | `graph/state.py:1850-1873` | ⇒ freegraph 的 `build_channel` 规则与之一致（spec FR-012） |
| S-05 | **步末清空哪些通道** | 步末**只**对**路由型**通道调 `clear()`（覆盖型 / 归约型**保留**其值） | 对本步未更新的通道调 `update(EMPTY_SEQ)`，而覆盖型 / 归约型对其 **no-op**（值保留） | `pregel/_algo.py:326-334` · `channels/last_value.py:56-58` · `channels/binop.py:123-125` | ⇒ **B7F1 的步末调用范围 MUST 与上游逐字同构**（否则覆盖型的「末值保留」/ 归约型的「累积保留」被抹掉 · 裁定 17 ② · contract §7 `B-2`） |

## 3. 上游**未**实现的形态（freegraph 亦不做）

| # | 形态 | 上游出处 | freegraph 的处置 |
|---|---|---|---|
| N-01 | `Overwrite` 旁路值（单值覆盖） | `channels/binop.py:31-51`（`_get_overwrite`） | **不做**（spec FR-018 · research DR-3） |
| N-02 | `Topic` / `Barrier` / `AnyValue` / `NamedBarrierValue` | `channels/topic.py` · `channels/named_barrier_value.py` · `channels/any_value.py` | **不做**（v1.0 只需三类 · spec FR-018） |
| N-03 | 通道的 `copy()` / `checkpoint()` / `from_checkpoint()` | `channels/base.py:40-65` | **不做**（属 **B14F1** · spec FR-018） |
| N-04 | `consume()` / `finish()` 钩子 | `channels/base.py:101-121` | **不做**（v1.0 无订阅 / 收尾语义） |

---

## 4. 核实记录（可复现）

```bash
# 上游版本与路径
python3 -c "import importlib.metadata as m; print(m.version('langgraph'))"     # 1.2.11
python3 -c "import langgraph.channels, os; print(os.path.dirname(langgraph.channels.__file__))"

# 逐条行号复核（示例：P-07 的首次写入直存）
sed -n '123,144p'  …/site-packages/langgraph/channels/binop.py
sed -n '56,67p'    …/site-packages/langgraph/channels/last_value.py
sed -n '55,65p'    …/site-packages/langgraph/channels/ephemeral_value.py
sed -n '317,334p'  …/site-packages/langgraph/pregel/_algo.py
sed -n '38,53p'    …/site-packages/langgraph/pregel/_io.py
sed -n '1850,1873p'…/site-packages/langgraph/graph/state.py

# P-12 / S-05 的复核（上游**没有** clear()；三类通道对 update([]) 的反应不同）
grep -n "def clear" …/site-packages/langgraph/channels/*.py                       # ⇒ 无命中
sed -n '56,58p'    …/site-packages/langgraph/channels/last_value.py                # 覆盖型 ⇒ no-op
sed -n '123,125p'  …/site-packages/langgraph/channels/binop.py                    # 归约型 ⇒ no-op
sed -n '55,61p'    …/site-packages/langgraph/channels/ephemeral_value.py           # 路由型 ⇒ MISSING
```

> **📌 换版本纪律**：本表任一行号在**换 `langgraph` 版本**后 MUST **重新核实**，
> 并把「核实环境」一栏更新为新版本 + 新核实日期（宪法原则 VIII · spec FR-021）。
