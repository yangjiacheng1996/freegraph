# Data Model: B5F1 · 通道抽象 + 三类通道

**Feature**: `B5F1` · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**契约权威**: [contracts/channel-contract.md](./contracts/channel-contract.md)（**唯一权威**）

> **本文件的纪律**：字段名**逐字冻结**（spec FR-002 / FR-012 · 澄清轮 Q4）⇒ 本文件与 spec 一致；
> **不变量** MUST 可由单元测试直接断言。

---

## 1. 实体总览

```text
SchemaSpec (B4F1 产物 · 冻结)
    │  channels: Mapping[key → ChannelSpec]（保序）
    │  keys: Sequence[str]
    ▼
build_channels(schema_spec) ──► 通道集合: dict[str, Channel]（保序 · 可变）
                                    │
                                    ├─ LastValue                 （覆盖型 · 无归约器）
                                    ├─ BinaryOperatorAggregate   （归约型 · 有归约器）
                                    └─ EphemeralValue            （路由型 · 显式创建 · 不由 schema 派生）
```

---

## 2. 实体与字段（**字段名逐字冻结**）

### 2.1 `Channel`（抽象基类 · 唯一的读写单元）

| 字段 / 属性 | 类型 | 说明 | 冻结来源 |
|---|---|---|---|
| `key` | `str` | schema key；内部通道 MAY 为空串 | spec FR-002 |
| `value_type` | `Any` | **归约前的基类型 `T`**；与 B4F1 的 `ChannelSpec.value_type` **同名同义** | spec FR-002 / FR-012 |
| `value` | `Any` | 通道**当前值**（**只读**）；无值时**抛 `EmptyChannelError`**（与 `get()` 同义） | spec FR-002 · research D-04 |
| `reducer` | `Callable[[Any, Any], Any] \| None` | 归约器**引用**（**按引用**持有）；`LastValue` / `EphemeralValue` 恒为 `None` | spec FR-002 / FR-014 |

**构造签名（逐字冻结）**

| 类 | 构造签名 |
|---|---|
| `Channel` | `Channel(key: str, value_type: Any)` |
| `LastValue` | `LastValue(key: str, value_type: Any)` |
| `BinaryOperatorAggregate` | `BinaryOperatorAggregate(key: str, value_type: Any, reducer: Callable[[Any, Any], Any])` |
| `EphemeralValue` | `EphemeralValue(key: str, value_type: Any)` |

**方法（逐字冻结 · 4 个操作）**

| 方法 | 返回 | 语义 | 无值 / 异常行为 |
|---|---|---|---|
| `update(values: Sequence[Any]) -> bool` | `bool` | 把「本步的写入序列」并入通道 | **本次调用是否写入了值**（非空 ⇒ 恒真；空 ⇒ 假）· 多值冲突 ⇒ 抛 `InvalidChannelUpdateError` |
| `get() -> Any` | 当前值 | 取回通道当前值 | 无值 ⇒ 抛 `EmptyChannelError` |
| `is_available() -> bool` | `bool` | 判定「有值 / 无值」 | **恒不抛错** |
| `clear() -> bool` | `bool` | 把通道恢复到「无值」 | **状态是否真的变化**（已是「无值」⇒ 假）· **三类通道全部覆写**（默认实现 = 无操作 · 裁定 17 ①） |

**内部表示（实现细节 · 非契约面）**

| 私有槽 | 含义 |
|---|---|
| `_key` / `_value_type` / `_value` / `_reducer` | 4 个公开属性的存储（`__slots__` · research D-02） |
| `_MISSING`（**模块级** · `object()`） | 「无值」的哨兵（**MUST NOT** 用 `None` · research D-03） |

### 2.2 `LastValue`（覆盖型 · C3）

- **归约器**：**无**（`reducer is None`）· **空值**：**不推导**（初始「无值」）。
- **写入**：一次 `update` 收到**多于一个**值 ⇒ `InvalidChannelUpdateError`；收到**一个** ⇒ 覆盖。
- **清空**：`clear()` **覆写** ⇒ 「无值」（清空**不**等于「撤销最后一次写入」· 裁定 17 ①）。

### 2.3 `BinaryOperatorAggregate`（归约型 · C2）

- **归约器**：**按引用**持有（`channel.reducer is operator.add` MUST 成立 · FR-014）。
- **空值**：构造时按 `value_type` 推导（剥 `Annotated`/`Required`/`NotRequired` → 抽象容器映射 → `typ()`）；
  推导失败 ⇒ **初始「无值」**（构造**不**失败 · FR-006）。
- **写入**：`reducer(current, new)`；通道**无值** ⇒ **直存首个写入值**（**单值**写入时归约器调用次数 == **0**）。
- **清空**：`clear()` **覆写** ⇒ 「无值」（**不回到**初始空值 · 裁定 17 ①）。

### 2.4 `EphemeralValue`（路由型 · C7 / C8）

- **归约器**：**无** · **空值**：**不推导**（初始「无值」）· **不由 schema 派生**（显式创建）。
- **覆写** `clear()` ⇒ 回到「无值」；一次 `update` 收到**多于一个**值 ⇒ `InvalidChannelUpdateError`。
### 2.5 通道集合（`build_channels` 的返回值）

| 项 | 类型 | 说明 |
|---|---|---|
| 键 | `str` | schema key（**保序** · 与 `SchemaSpec.keys` 同序） |
| 值 | `Channel` | 每个 key **恰一个**通道 |
| 容器 | `dict[str, Channel]` | **保序**（3.7+）· **可变**（下游可增补内部通道 · research D-14） |

### 2.6 错误类型（L2 · 结构化字段逐字冻结）

| 错误类型 | 继承 | 结构化字段 | 触发时机 |
|---|---|---|---|
| `EmptyChannelError` | `FreegraphError`（**不**继承 `ValueError`） | `key: str` | 读取「无值」通道 |
| `InvalidChannelUpdateError` | `FreegraphError` **且** `ValueError` | `key: str` · `received_count: int` · `expected_count: int`（**恒为 1**） | 一次写入调用收到多于一个值 |

⚠️ 错误对象 **MUST NOT** 携带用户写入的**值本身**（FR-017 ⑥）· 消息只是**英文摘要**。

---

## 3. 状态机（每个通道类型一张）

### 3.1 通用状态

```text
                 write(values)                     clear()
      ┌────────┐ ─────────────► ┌────────┐   ┌──────────────► ┌────────┐
      │ 无值   │                 │ 有值   │   │  （覆写 ⇒ 无值） │ 无值   │
      └────────┘ ◄───────────── └────────┘   └────────────────┘
                    （三类通道同构 · 裁定 17 ①）
```

> **📌 步末调用范围（裁定 17 ②）**：本表冻结的是 **`clear()` 的语义**（三类一律 ⇒ 无值）；
> **步末对哪些通道调用**属调度层（**B7F1**）—— 与上游逐字同构的做法是**步末只清路由型**
> （上游的 `update(EMPTY_SEQ)` 对覆盖型 / 归约型是 **no-op** · 见 `upstream-parity` P-12 / S-05）。

### 3.2 `LastValue`（覆盖型）

| 起点 | 事件 | 终点 | 备注 |
|---|---|---|---|
| 无值 | `update([v])` | 有值（`v`） | 归约器调用次数 == 0 |
| 有值 | `update([v])` | 有值（`v`） | **覆盖**（旧值丢弃 · C3） |
| 任意 | `update([])` | **不变** | 返回假 |
| 任意 | `update([v1, v2, …])` | **不变** | 抛 `InvalidChannelUpdateError`（**先检测后写入**） |
| 有值 | `clear()` | **无值** | **覆写** ⇒ 无值（裁定 17 ①）· 返回真 |
| 无值 | `clear()` | 无值 | 无操作 · 返回假（幂等） |

### 3.3 `BinaryOperatorAggregate`（归约型）

| 起点 | 事件 | 终点 | 备注 |
|---|---|---|---|
| **有值（空值）** | `update([v])` | 有值（`reducer(空值, v)`） | 归约器调用次数 == 1 |
| 有值 | `update([v1, v2])` | 有值（`reducer(reducer(cur, v1), v2)`） | **按序**逐个归约 |
| **无值**（类型不可实例化） | `update([v])` | 有值（`v`，**直存**） | **归约器调用次数 == 0**（单值写入 · FR-007 ②） |
| 无值 | `update([v1, v2])` | 有值（`v1` 直存，再 `reducer(v1, v2)`） | 首个值直存，其余按序归约（调用次数 == 值数 − 1 · 裁定 17 ④） |
| 任意 | `update([])` | **不变** | 返回假 |
| 有值 | `clear()` | **无值** | ⚠️ **不回到**初始空值（FR-022 ③ · 裁定 17 ①）· 返回真 |
| 无值 | `clear()` | 无值 | 返回假（幂等） |
| 有值 | 归约器抛错 | **不变** | 异常向上传播 · 值未被改写（FR-008） |

### 3.4 `EphemeralValue`（路由型）

| 起点 | 事件 | 终点 | 备注 |
|---|---|---|---|
| 无值 | `update([v])` | 有值（`v`） | |
| 有值 | `update([v])` | 有值（`v`） | 覆盖为最新值 |
| 任意 | `update([])` | **不变** | 返回假（**清空走 `clear()`**，不靠空序列） |
| 任意 | `update([v1, v2, …])` | **不变** | 抛 `InvalidChannelUpdateError` |
| 有值 | `clear()` | **无值** | **覆写** ⇒ 无值（路由判定结果**不跨 super-step 残留**）· 返回真 |
| 无值 | `clear()` | 无值 | 返回假（幂等） |

---

## 4. 不变量（每条 MUST 有单元测试断言）

| # | 不变量 | 关联 |
|---|---|---|
| **I-1** | **公开**属性（4 个 `property`）集合**恰为** {`key`, `value_type`, `value`, `reducer`} **且** **实例槽位**集合 ⊆ {`_key`, `_value_type`, `_value`, `_reducer`}；MUST NOT 持节点 / 图 / 配置 / 时钟 / 句柄 / 锁；**子类 MUST NOT 引入新槽**（⇒ 实例 MUST NOT 拥有 `__dict__`）· **公开属性的收集 MUST 沿 MRO** | FR-013 ① · SC-009 · 澄清轮 Q15 · 裁定 17 ① |
| **I-2** | 通道**MUST NOT** 持有其它通道或状态表的引用 ⇒ ① **引用类型白名单**（直接引用集合中 MUST NOT 出现 `dict` / `SchemaSpec` / 其它 `Channel` 实例）；② `len(gc.get_referents(ch))` 与 schema 的 key 数**无关**（**辅助**判据 · **探针口径逐字冻结** · MUST NOT 用墙钟耗时 / 数行） | FR-013 ②③ · SC-022 ①③ · 澄清轮 Q15 · 裁定 17 ③ |
| **I-3** | 「无值」与「值为 `None`」**严格可分**：写入 `None` 后 `is_available()` 为真 | FR-011 ③ · SC-004 |
| **I-4** | `is_available()` **恒不抛错**；`get()` 在无值时**必抛** `EmptyChannelError` | FR-011 ①② · SC-004 |
| **I-5** | `value` 属性与 `get()` **同义**（无值时同样抛 `EmptyChannelError`）⇒ 不存在第三种语义 | research D-04 · SC-004 |
| **I-6** | `update()` 的返回值 = 「**本次调用是否写入了值**」：非空 ⇒ 恒真（哪怕值未变）；空 ⇒ 假 | FR-002 📌 · SC-020 |
| **I-7** | 一步内多值冲突时，通道**值不变**（**先检测后写入**） | FR-004 / FR-010 · SC-006 |
| **I-8** | 归约器抛错时，通道**值不变** | FR-008 · SC-006 |
| **I-9** | 归约器**按引用**持有：`channel.reducer is operator.add` | FR-014 · SC-010 |
| **I-10** | 归约型通道的**首次**写入（通道初始「无值」时）**单值**写入 ⇒ 归约器调用次数 == **0**（多值写入 ⇒ 首个直存、其余按序归约） | FR-007 ② · SC-007 · 裁定 17 ④ |
| **I-11** | 两个同类型归约型通道的**空值是不同对象**（共享次数 == 0） | FR-006 ④ · SC-007 |
| **I-12** | 清空后**一律**「无值」（**三类通道同构** · 含归约型）；清空**不**回到初始状态（规范性表述见 spec **FR-022 ③**） | FR-022 ③ · SC-023 · 裁定 17 ① |
| **I-13** | 覆盖型 / 路由型通道的**初始状态** = 「无值」；归约型 = 「有值（空值）」或（类型不可实例化时）「无值」 | FR-022 · SC-023 |
| **I-14** | 通道**浅引用**用户对象：写入后 `channel.value is 传入对象` | FR-024 · SC-025 |
| **I-15** | 通道**不校验**写入值的**类型**；**不重做**归约器二元性校验 | FR-024 ③ · FR-025 ④⑤ · SC-026 |
| **I-16** | 构造期：归约器**不可调用** ⇒ `TypeError`；「有归约器但归约器为空」⇒ `ValueError` | FR-025 ①② · SC-026 |
| **I-17** | 映射**保序**：产出通道的键序 == `SchemaSpec.keys` 序；通道数 == key 数 | FR-012 ④ · SC-008 |
| **I-18** | 映射产出的归约型通道，其 `reducer` **就是**规格里的那个引用（身份判定） | FR-012 ① · SC-008 |
| **I-19** | 导入本 feature 的模块：`sys.modules` 增量中非标准库条目数 == 0；环境变量读取 == 0；出站 == 0 | FR-015 · SC-005 |
| **I-20** | 通道**无同步原语**（无锁 / 无原子性保证）；写入入口**只有** `update()` 一个 | FR-023 · SC-024 |
| **I-21** | 错误对象的**结构化字段齐备**（`key`；冲突错误另有 `received_count` / `expected_count == 1`）；**不携带**用户写入的值 | FR-017 ④⑥ · SC-018 |
| **I-22** | 两个错误类型均可被 `except FreegraphError` 捕获；`EmptyChannelError` **不是** `ValueError` | FR-017 ③⑦ · SC-018 |
| **I-23** | 名字面逐字一致：4 操作 + 4 属性 + 4 类名 + 2 映射入口 + 2 错误名 | FR-002 / FR-012 / FR-017 · SC-019 |

---

## 5. 关系（Relationships）

| 关系 | 基数 | 说明 |
|---|---|---|
| `SchemaSpec` → `ChannelSpec` | 1 : N（保序） | B4F1 的冻结产物 |
| `ChannelSpec` → `Channel` | 1 : 1 | `build_channel(spec)`：**有归约器 ⇒ BinOp**；**无 ⇒ LastValue** |
| `SchemaSpec` → 通道集合 | 1 : N（保序） | `build_channels(spec)`；每 key **恰一个**通道 |
| `Channel` → 归约器 | 0..1 | **按引用**；仅归约型持有 |
| 通道 → 错误类型 | 0..1（每次调用至多一个） | 冲突 ⇒ `InvalidChannelUpdateError`；读无值 ⇒ `EmptyChannelError` |
| 路由通道（`EphemeralValue`） | **不由 schema 派生** | 显式创建（FR-012 ③） |

---

## 6. 与 B4F1 的**形态差异登记**（非冲突 · 各自用途不同）

| # | 差异 | B4F1 | B5F1 | 理由 |
|---|---|---|---|---|
| 1 | 集合容器的**可变性** | `SchemaSpec.channels` = **不可变**映射（`MappingProxyType`） | `build_channels(...)` = **可变** `dict` | B4F1 是**冻结的解析产物**；B5F1 返回**活的通道集合**（下游 B5F2 / B7F1 要在其上增补内部通道）· research **D-14** |
| 2 | 空值/默认值的**表示** | `reducer` 缺省 = `None` | 「无值」= **模块私有 sentinel** `_MISSING` | `None` 是**合法用户值** ⇒ 不能兼任「无值」标记（FR-011 ③ · research **D-03**） |
| 3 | 类型的**剥离口径** | 剥 `Required` / `NotRequired`（+ 保留 `Annotated` 元数据解析） | 剥 `Annotated` / `Required` / `NotRequired` | 通道消费的是**已解析的基类型**；但该基类型**仍可能**带 `Required` 包装（B4F1 的 `Annotated[Required[list], op]` 边缘形态）⇒ 必须能剥（research **D-05**） |
