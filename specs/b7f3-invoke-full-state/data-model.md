# 数据模型（Data Model）—— B7F3 · `invoke()` 返回完整状态

**Feature**: `B7F3` · **Spec**: [../spec.md](../spec.md) · **契约**: [../contracts/invoke-contract.md](../contracts/invoke-contract.md)

> **纪律**：本文件只描述**本 feature 新产出 / 新消费**的数据形态。
> **L1 的既有类型**（`StateDict` / `RunConfig` / `Command` / `Interrupt` / `InvalidUpdateError` …）
> 与 **L2 的既有结果对象**（`SuperStepResult` / `InterruptResult`）**逐字沿用**，**不重定义**
> （原则 XII「同类项同类承载」）。

---

## 1. 实体总览

```text
编译产物 (CompiledGraph · 既有)
├── _spec: GraphSpec                       （既有 · 只读）
│   └── channels: dict[str, Channel]       （既有 · 键顺序 = schema 声明顺序 + 路由通道）
└── checkpointer: Checkpointer | None       （既有 · 只透传）

        │  invoke(input, config)
        ▼
┌─────────────────────────────┐
│ invoke 结果字典 (dict)      │  ← 本 feature 的**唯一新产出**
│   键集 = schema 全集        │
│         + （挂起时）__interrupt__
│   值   = 合并后的最终状态   │
└─────────────────────────────┘
```

---

## 2. `invoke` 结果字典

| # | 项 | 形态 | 约束 |
|---|---|---|---|
| **2.1** | 类型 | **普通 `dict`**（`type(out) is dict`） | MUST NOT 是 `MappingProxyType` / 自定义映射 / dataclass |
| **2.2** | **键集** | schema 的**全部** key（**按 schema 声明顺序**） | MUST NOT 漏 key（MUST NOT 因「无值」漏）· MUST NOT 多 key（内部通道 MUST NOT 泄漏） |
| **2.3** | **`__interrupt__` 键** | **仅挂起时**出现 · 值 = `tuple[Interrupt, ...]`（**元组**） | 无挂起时**出现次数 == 0** |
| **2.4** | **值的来源** | 归约型 key = 「初始 + 全部新增」的合并值；无归约器 key = 最后一次写入值 | MUST NOT 返回增量 · MUST NOT 累加覆盖型 key |
| **2.5** | **无值 key** | **覆盖型（无归约器）** ⇒ `None`；**归约型** ⇒ **类型空值**（`[]` / `0`） | ⚠️ 只适用于**返回值**；节点入参仍稀疏（C4）· ⚠️ **MUST NOT** 把类型空值改写成 `None`（§2.3 · 契约 R-06） |

### 2.2 键集的**推导链**（**单一真源**）

```text
编译产物._spec.channels                  （既有 · 键顺序 = schema 声明顺序 + 路由通道）
        │
        ├─ 扣除：isinstance(channel, EphemeralValue)   ← 路由型通道（B7F1 FR-014 的冻结判定）
        │                                                （MUST NOT 用「branch:to:」前缀启发式）
        ▼
   schema key 序列（保序）  ──────────────►  结果字典的键顺序
```

| # | 规则 | 冻结依据 |
|---|---|---|
| **2.6** | 路由通道的判定 MUST 以 `isinstance(channel, EphemeralValue)` 为准 | `specs/b7f1-superstep-loop/spec.md:547-551`（FR-014 末条）· 契约 `superstep-contract.md:241` |
| **2.7** | MUST NOT 依赖「节点订阅集」（`NodeSpec.subscribes`）—— 那是**间接口径**，不承诺 == schema 全集 | B7F1 FR-008 ③ |
| **2.8** | MUST NOT 新增编译产物的私有字段（持有面「3 私有 + 8 公开」是 B7F2 的冻结面） | `tests/facade/test_compiled_graph.py:111-114`（`vars()` 恰 11 键） |

### 2.3 「有值 / 无值 / 值为 `None`」的三态

> ⚠️ **口径的前提**：下表的「**类型空值**」指**可构造**的空实例（`list` → `[]` · `int` → `0`）⇒ ⇒
> **构造失败**（`_derive_empty_value` ⇒ `_MISSING`）的**退化分支**见本节末行 ⇒ ⇒ ⇒ ⇒
> **判据零放宽**（退化时补齐值 = `None`，仍落在 FR-009 的「覆盖型」那一档）。

| 通道状态 | 在**稀疏视图**里 | 在**返回值**里 | 说明 |
|---|---|---|---|
| 归约型通道 · 已写 | 键存在 · 合并值 | 键存在 · 合并值 | 正常 |
| 归约型通道 · **未写** | 键存在 · **类型空值**（`list` → `[]` · `int` → `0`） | 键存在 · **类型空值**（**NOT** `None`） | `BinaryOperatorAggregate.__init__` 用 `_derive_empty_value`（`channel.py:437` + `:350-374`）⇒ 上游同款（E-8） |
| 覆盖型通道 · 未写 | **缺席** | 键存在 · **`None`** | ← 「补齐」只作用于**缺席**的 key |
| 覆盖型通道 · 写了 `None` | 键存在 · `None` | 键存在 · `None` | ⚠️ 与「未写」在**值上**不可区分（freegraph 的通道**无**「有无值」与「值为 None」的区分 · 上游同款：`None` ≠ `MISSING`） |
| **归约型**通道 · 未写 **且** 该通道的**类型空值不可构造** | **缺席**（`_derive_empty_value` 构造失败 ⇒ 返回 `_MISSING` · `channel.py:350-374`） | 键存在 · **`None`** | ⚠️ **退化分支**（**极少见**）：值类型的「空实例」构造失败（如 `Annotated[SomeAbstract, …]`）⇒ ⇒ ⇒ 该通道在稀疏视图里**缺席** ⇒ ⇒ ⇒ ⇒ 于是落在**覆盖型**那一档 ⇒ ⇒ ⇒ ⇒ 值 = `None`（**不是**类型空值）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据不受影响**：本条只覆盖「**可构造**类型空值」的常见情形；退化时 **MUST NOT** 因此把 `None` 改写成别的值 |

> ⚠️ **实现要点**：`LastValue` 的 `is_available()` 在「值为 `None`」时**为真**（`channel.py:302-304`
> 只看 `is not _MISSING`）⇒ ⇒ 稀疏读**会**把它读出来（值为 `None`）⇒ ⇒ 「补齐」的实现 MUST 是
> 「**按 schema key 顺序逐个取 `sparse.get(key, None)`**」⇒ ⇒ **MUST NOT** 用
> 「值是否为 `None`」来判断「有无值」。

---

## 3. 输入侧（**既有类型 · 不新增**）

| # | 形态 | 类型 | 语义 | 归属 |
|---|---|---|---|---|
| **3.1** | 初始状态 | `StateDict`（`dict[str, Any]`） | **部分** key 即可；按通道语义写入（归约 / 覆盖） | 写入路径 = L2 `_apply_input_writes`（`superstep.py:1566-1590`） |
| **3.2** | 恢复输入 | `Command`（L1 · `contracts/types.py:51-114`） | `resume` / `update` / `goto` 三位 | 判定表 = **B10F1 FR-013**（唯一事实源）· 顺序 = **B10F1 裁定 4** |
| **3.3** | 会话连续 | `None` | 首轮不写任何通道；或（有 checkpointer 时）续跑该会话 | 同上（FR-013 末两行） |
| **3.4** | 运行期配置 | `RunConfig` \| `Mapping[str, Any]` | **原样**交给 L2（`resolve_config`）⇒ 未知键**宽容忽略** | L2 `_recursion.py:30-48` |

---

## 4. 中间结果（**既有对象 · 只消费**）

| # | 对象 | 字段 | 本 feature 的用法 |
|---|---|---|---|
| **4.1** | `SuperStepResult` | `state`（**稀疏**）· `executed` · `node_writes` · `steps` | 只取 `.state` 作补齐基线；其余字段**不**外泄 |
| **4.2** | `InterruptResult` | `state`（**稀疏**）· `interrupts` · `executed` · `steps` | 只经 `as_result_dict()` 转成（**唯一**转成路径） |
| **4.3** | `Interrupt`（L1） | `value` · `id` | 由 `__interrupt__` 承载（元素具备 `.value` / `.id`） |
| **4.4** | `GraphSpec`（L2） | `channels` / `nodes` / `edges` / … | 只读：推导 schema key 序列 |

---

## 5. 归一算法（**逐字**）

```text
输入：result = run_graph(spec, input, *, checkpointer=..., config=...)   # max_concurrency 由 L2 自行解析（关键字优先 · config 兜底）
      spec   = 编译产物持有的图规格（只读）

步骤：
  ① 若 result 是 InterruptResult：
        base = result.as_result_dict()          ← 唯一转成路径（产出 "__interrupt__" 键）
     否则：
        base = result.state                     ← 稀疏视图

  ② schema_keys = [k for k, ch in spec.channels.items()
                      if not isinstance(ch, EphemeralValue)]      ← 扣除路由通道（保序）

  ③ out = {}
     for k in schema_keys:
         out[k] = base.get(k, None)             ← 缺席 ⇒ None；值为 None ⇒ 原样 None
     if "__interrupt__" in base:                 ← 挂起 ⇒ 保留（不覆盖、不重排）
         out["__interrupt__"] = base["__interrupt__"]

  ④ 返回 out
```

| # | 不变量 | 判据 |
|---|---|---|
| **5.1** | `list(out)` 前 `len(schema_keys)` 项 **==** `schema_keys`（顺序逐字相等） | 键集断言 |
| **5.2** | `out` 的键集 == `schema_keys` ∪（挂起时）`{"__interrupt__"}` | 键集断言 |
| **5.3** | `out` 中**不含**任何路由通道名 | `"branch:to:*" not in out` |
| **5.4** | 无挂起时 `"__interrupt__"` **不在** `out` 里 | 出现次数 == 0 |
| **5.5** | 归约型通道的**类型空值**不被改写成 `None` | `out[k] == []`（`list` 型）断言 |
| **5.6** | 该算法是**一个**实现点（B8F2 MUST 复用） | 代码审查 + 差分 D-92…D-102 |

---

## 6. 失败信号的**数据形态**

| # | 异常 | 结构化属性 | 消息 | 产生位置 |
|---|---|---|---|---|
| **6.1** | `InvalidUpdateError` | `.invalid_keys: tuple[str, ...]`（**全部**未知 key） | `"Invalid state update: unknown key(s) 'k1', 'k2'"`（**点名违规 key**） | L2 `_reject_unknown_keys`（`superstep.py:1047-1058`） |
| **6.2** | `GraphRecursionError` | `.recursion_limit` · `.current_step` | 英文摘要 | L2 `superstep.py:1706-1708` |
| **6.3** | `InterruptError`（L2） | `.reason`（**封闭取值域**：`checkpointer_required` / `resume_value_required` / `ambiguous_resume` / `no_pending_interrupt` / `not_in_run`） | 英文摘要 | L2 `superstep.py:2084-2145` |
| **6.4** | 用户异常 | — | **原始消息逐字保留** | 节点 ⇒ 零捕获 ⇒ 直达调用方 |

> ⚠️ **零捕获纪律**：门面 `invoke` **MUST NOT** 写任何 `try/except` ⇒ 上表的所有异常
> **原类型 + 原消息**到达调用方（不包装、不吞掉）。

---

## 7. 生命周期（一次 `invoke` 的状态流）

```text
① 入口校验          max_concurrency（关键字优先 · 否则取 config.max_concurrency）· config 形态 ⇒ 失败即抛（L2 入口即失败）· ⚠️ 关键字来源的校验在 resolve_config **之前** · config 来源的在**之后**（FR-023）
② 调度状态新建      SchedulerState()（不传 state= ⇒ 每次调用内部自洽）
③ 通道实例新建      每通道 template.from_checkpoint(template.checkpoint()) ⇒ 零状态残留
④ 初始写入          _apply_input_writes（归约 / 覆盖 / 未知 key ⇒ InvalidUpdateError）
⑤ 轮循环            触发判定 → 任务准备 → 任务执行 → 写入收集 → 写入合并 →（步末清空）
                     ├─ 节点真异常 ⇒ 原样上抛
                     └─ 中断 ⇒ GraphInterrupt ⇒ L2 转 InterruptResult ⇒ 挂起
⑥ 终止              到达 END 或无待执行任务 ⇒ SuperStepResult（稀疏）
⑦ 归一             as_result_dict()（挂起）⇒ 补齐 ⇒ 返回完整状态字典
```

| # | 不变量 | 判据 |
|---|---|---|
| **7.1** | 每次调用**新建**通道实例 ⇒ 连续两次**不累积** | 结果逐字比较 |
| **7.2** | 每次调用**新建**调度状态 ⇒ 并发两次**不串扰** | 结果逐字比较 |
| **7.3** | 编译产物持有的通道**全程零写入** ⇒ 编译产物可反复使用 | 通道模板 `is_available()` 全为假 / 值未变 |
| **7.4** | 步末清空 ⇒ 路由通道的值**不残留**到下一次调用 | 连续两次调用的键集断言 |
