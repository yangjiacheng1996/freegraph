# Data Model · B7F2 · `compile()` → `CompiledGraph`

**Feature**: `specs/b7f2-compile/` · **Date**: 2026-11-16
**契约权威**：`contracts/compile-contract.md`（形状）· `spec.md`（判据）
**上游**：`langgraph 1.2.11`（实测 E-25…E-55 见 `research.md` §1）

> 本文件只描述**数据形状与不变量**。判据编号（FR / SC / C-xx / N-xx / X-xx）与 `spec.md` 一致；
> 本文新增的编号只有 **CV-1…CV-14**（编译期校验的机械落点）与 **NV-1…NV-7**（不检查项）。

---

## 1. 实体总览

| 实体 | 归属 | 生命周期 | 可变性 |
|---|---|---|---|
| `CompiledGraph` | L3 · `_stategraph.py` | `compile()` 返回的一次产物 | 私有字段**不要求**冻结（MUST NOT 因此新增异常） |
| `_spec: GraphSpec` | L2（B7F1） | 产物持有 | `GraphSpec` 字段不可改写；`channels` **内容**可被调用方增补（B7F1 FR-034） |
| `_builder_spec: _BuilderSpec` | L3（B6F1） | 产物持有 | 冻结 dataclass；产物 MUST NOT 改写其内容 |
| `_conditional_edges: dict[str, tuple[dict[str, Any], ...]]` | L3（本 feature 产出） | 产物持有 | 纯内建容器；产物 MUST NOT 改写 |
| 注入项（8 个公开属性） | L3 | 产物持有 | 记录值原样 |
| 路由通道 `branch:to:<target>` | L2（`EphemeralValue`） | 在 `_spec.channels` 内 | 模板（**编译期零写入**） |

---

## 2. `CompiledGraph` 的内部状态

### 2.1 字段清单（**冻结面**）

```text
CompiledGraph(
    # ── 私有（三个名字是跨 feature 接口 · 见 DD-13 / FR-010）──
    _spec: GraphSpec,                       # B7F1 图规格（节点 + 边 + 通道）
    _builder_spec: _BuilderSpec,            # B6F1 完整快照（含 node_records ⇒ B8F3）
    _conditional_edges: dict[str, tuple[dict[str, Any], ...]],   # ⇒ B8F1

    # ── 公开（读 · 注入项见 E-31；`transformers` 命名见 X-12）──
    checkpointer: Checkpointer | None,      # 记录值（v1 无行为）
    store: Store | None,                    # 记录值（v1 无行为 · 传非 None ⇒ 1 条 warning）
    cache: Any,                             # 记录值（v1 无行为）
    debug: bool,                            # 记录值（缺省 False · 硬编码 · 不读 env）
    name: str | None,                       # 记录值（v1 无行为 · B22F1 消费）
    transformers: Any,                      # 记录值（v1 无行为 · B8F2 消费）
    interrupt_before_nodes: tuple[str, ...],# GraphSpec 归一后的**保序元组**（X-11）
    interrupt_after_nodes: tuple[str, ...], # 同上
)
```

### 2.2 不变量

| # | 不变量 | 判据 |
|---|---|---|
| **I-1** | `vars(compiled)` 的 key 集合 = 上表 **11** 个（3 私有 + 8 公开），**零多余** | SC-010 / SC-013 |
| **I-2** | 公开属性**恒可读**（含全部为 `None` 的情形） | SC-002 / SC-015 |
| **I-3** | `_spec.conditional_edges` **恒为空映射**（B8F1 之前） | SC-010 |
| **I-4** | `_spec.channels` 与 `_builder_spec.channels` 是**两个不同的映射对象**（值层面共享同一批通道模板） | SC-011 / D2 |
| **I-5** | 产物持有的一切通道都是**未被写入过值的模板**（`checkpoint()` 为空值） | SC-011 |
| **I-6** | `_builder_spec` 的内容与 `compile()` 拿到的快照**逐字相等**（产物不改写） | SC-010 |
| **I-7** | 三个私有字段名**逐字**为 `_spec` / `_builder_spec` / `_conditional_edges` | SC-010 |
| **I-8** | 公开属性**只读语义**：本 feature MUST NOT 断言「赋值被拒」（不新增异常类型） | FR-018 |

> **「公开只读属性」的口径**（消歧）：**只读 = 用户不需要写**；本 feature **不**强制
> 赋值失败（上游的 `Pregel` 属性也是可赋值的 · E-31）。测试只断言**存在 + 值正确**。
> ⚠️ **载体形态 MUST 是实例属性（不是 `@property`）**——否则 `vars(compiled)` 看不到它们，
> **I-1** 的「11 键」与 T015 / SC-010 的口径不成立。

### 2.3 能力面（6 方法 · 签名逐字对齐 L1 协议）

| 方法 | 签名 | 本 feature 行为 | 归属 |
|---|---|---|---|
| `invoke` | `(input, config=None)` | `NotImplementedError`（点名 B7F3） | B7F3 |
| `stream` | `(input, config=None, *, stream_mode="values")` | `NotImplementedError`（点名 B8F2） | B8F2 |
| `get_graph` | `(*, xray=False)` | `NotImplementedError`（点名 B22F1） | B22F1 |
| `get_state` | `(config)` | `NotImplementedError`（点名 B15F1） | B15F1 |
| `get_state_history` | `(config)` | `NotImplementedError`（点名 B15F1） | B15F1 |
| `update_state` | `(config, values, as_node=None)` | `NotImplementedError`（点名 B16F1） | B16F1 |

> ⚠️ **2026-11-20 · B8F2 回溯修订注记（T-3 · 只补注记 · 原描述不改写）**：
> 自 **B8F2** 起，`stream` 已交付，签名默认值改为 **`stream_mode=None`（解析为 `"updates"`）**、
> `config` 放宽为 `RunConfig | Mapping[str, Any] | None`。上表原 `"values"` /
> `NotImplementedError` 保留为历史；现行权威见 `specs/b8f2-stream-modes/contracts/stream-contract.md`。

> **与 L1 协议的边界**：协议的「`get_state` 查不到 ⇒ 空值、MUST NOT 抛异常」约束的是
> **已实现之后**的语义；本表的 `NotImplementedError` 是「**尚未交付**」信号 ⇒ 不同层、不冲突。

---

## 3. 注入项（8 个公开属性）

| 属性 | 入参来源 | 记录方式 | v1 行为 | 警告 |
|---|---|---|---|---|
| `checkpointer` | `compile(checkpointer=)` | 原样（**身份保留** · E-53） | 无（B14F1） | **无** |
| `store` | `compile(store=)` | 原样 | **无（永久 · v1 不支持）** | **1 条**（非 `None` 时） |
| `cache` | `compile(cache=)` | 原样 | 无（v2 extras） | 无 |
| `debug` | `compile(debug=)` | 原样（缺省 `False`） | 无（可观测层） | 无 |
| `name` | `compile(name=)` | 原样（缺省 `None`） | 无（B22F1 消费） | 无 |
| `transformers` | `compile(transformers=)` | 原样（**freegraph 自有命名** · 上游属性名为 `stream_transformers` ⇒ **X-12**） | 无（B8F2） | 无 |
| `interrupt_before_nodes` | `compile(interrupt_before=)` | `GraphSpec` **归一后的元组** | 由 B13F1 的运行期（`run_graph`）消费 | 无 |
| `interrupt_after_nodes` | `compile(interrupt_after=)` | 同上 | 同上 | 无 |

**警告的精确形状**（裁定 14）：

- 触发条件：`store is not None`（**不**看 `checkpointer` / `cache` / `transformers` / `debug` / `name`）；
- 条数：**恰好 1 条**（每次 `compile()` 调用）；
- 机制：`warnings.warn(message, UserWarning, stacklevel=2)`（**不是** `logging` —— 上游的
  「已编译后改图」提示才是 `logging` · E-49/E-50）；
- 消息须含「v1 不支持 `Store`」（大小写敏感的子串 `Store` 由测试断言）。

---

## 4. 条件边 plain mapping（`_conditional_edges`）

```text
dict[str, tuple[dict[str, Any], ...]]
  key   = source（条件边源节点名 · 含 "__start__"）
  value = 该源上按**登记顺序**排列的分支项元组
  分支项（5 键逐字 · B6F1 D-2）：
      {
        "branch":         str,                        # = _ConditionalEdgeSpec.branch（MUST NOT 重新推断）
        "path":           Callable[..., Any],         # 路由函数（不调用）
        "path_map":       dict[Hashable, str] | None, # 归一化结果原样（None 保持 None）
        "targets":        tuple[str, ...],            # 含 END
        "route_channels": tuple[str, ...],            # 不含 END
      }
```

**不变量**

| # | 不变量 |
|---|---|
| **I-9** | 外层 key 的顺序 = `_BuilderSpec.conditional_edges` 中源**首次出现**的顺序；同源多个分支的顺序 = 登记顺序 |
| **I-10** | 分支项**恰 5 个 key**，逐字为 `branch` / `path` / `path_map` / `targets` / `route_channels` |
| **I-11** | `branch` **逐字等于** `_ConditionalEdgeSpec.branch`（不得由 `path.__name__` 重算） |
| **I-12** | `path_map` 与 `targets` / `route_channels` **原样搬运**（零归一化、零过滤） |
| **I-13** | `_spec.conditional_edges` **恒为空**（V-8 不触发） |

---

## 5. 图规格适配（`_BuilderSpec` → `GraphSpec`）

### 5.1 `edges` 的过滤与透传

| 情形 | 输入 | 输出 | 依据 |
|---|---|---|---|
| 单源 `END` 目标 | `"a" -> ("__end__",)` | **整键移除** | B6F1 D-1（`END` 不在节点表 · V-2 会判死） |
| 单源混合目标 | `"a" -> ("__end__", "b")` | `"a" -> ("b",)` | 同上（只去 `END`） |
| 单源全 `END`（多目标） | `"a" -> ("__end__", "__end__")` | **整键移除** | 去重后为空 |
| 多源 `END` 目标 | `("a","b") -> ("__end__",)` | **原样保留** | 交 `GraphSpec` **V-16** 显式失败（B7F4） |
| 多源目标数 ≠ 1 | `("a","b") -> ("c","d")` | **原样保留** | 同上（V-16） |
| 多源含 `START` | `("__start__","a") -> ("b",)` | **构建器已拒绝**（`add_edge` 要求源在节点表）；直接构造 `GraphSpec` 时**原样保留** | 同上（V-16） |
| 节点名 `__parent__` | `nodes` 含该名 | **原样保留** | 交 `GraphSpec` 保留名检查（B9F1 FR-005） |

**顺序不变量**：源键顺序 = 快照中的插入顺序；目标顺序 = 快照中的元组顺序。

### 5.2 `channels` / `nodes`

- `channels`：**新 dict**（`dict(builder_spec.channels)`）⇒ 同一批**通道模板对象**；
  顺序 = schema 声明顺序 + 路由通道（首次出现顺序，B6F1 已建好）。
- `nodes`：`dict(builder_spec.nodes)`（`NodeSpec` **同构** · DR-3）；顺序 = `add_node` 登记顺序。
- **MUST NOT** 重建 `NodeSpec`（订阅集已由 B6F1 按「全部状态通道」算好）。

### 5.3 静态断点

```text
compile(interrupt_before=V, interrupt_after=W)
        │
        ├─ V is None              ⇒ ()
        ├─ isinstance(V, str)     ⇒ V        （"*" 或裸串 ⇒ 交 GraphSpec 归一）
        ├─ isinstance(V, list)    ⇒ V        （元素级 ⇒ 交 GraphSpec 归一）
        └─ 其它（tuple/set/int…） ⇒ TypeError（V-22 家族 · 入口层）

GraphSpec.__post_init__ → normalize_static_points
        ├─ "*"            ⇒ 全部可执行节点（排除 __start__ / __end__）
        ├─ 空串元素        ⇒ ValueError（V-23）
        ├─ START/END/"*"  ⇒ ValueError（V-24）
        ├─ 未知节点        ⇒ ValueError（V-25 · 点名）
        └─ 非 str 元素     ⇒ TypeError（V-22）
```

**两段判定的分工**（DR-5）：入口层**只**判容器形态；元素级**100%** 委托
`normalize_static_points` ⇒ 保证 B13F1 D-2 的「逐字同款」。

---

## 6. 校验规则（CV-1…CV-14 · MUST 查）

> 「判定来源」= 实际抛错的代码位置；`compile()` **不得**另写同一判据。

| # | 检查项 | 失败信号 | 判定来源 | spec |
|---|---|---|---|---|
| **CV-1** | schema 合法性 | `InvalidSchemaError`（B4F1） | `_build_spec()` → `parse_state_schema` | C-01 |
| **CV-2** | 静态边源存在（`START` 除外） | `ValueError` | `_build_spec()` → `_validate_sources` | C-02 |
| **CV-3** | 入口存在（`START` 作源） | `ValueError`（含 `entrypoint` / `START`） | `_build_spec()` → `_validate_entrypoint` | C-03 |
| **CV-4** | 静态边目标存在（`END` 除外） | `ValueError` | `_build_spec()` → `_validate_targets` + `GraphSpec` V-2 | C-04 |
| **CV-5** | 条件边源存在 | `ValueError` | `_build_spec()` → `_validate_sources` | C-05 |
| **CV-6** | 条件边目标存在（`END` 除外） | `ValueError`（含源 / 分支 / 目标） | `_build_spec()` → `_validate_targets` | C-06 |
| **CV-7** | 节点表非空 | `ValueError` | `_build_spec()` → `_validate_nodes` + `GraphSpec` V-3（**防御性**：compile 链路中空图先命中 CV-3/CV-4） | C-07 |
| **CV-8** | 节点订阅的通道存在 | `ValueError` | `GraphSpec` V-1（**防御性**：`_build_spec()` 的订阅集恒来自 schema 通道） | C-08 |
| **CV-9** | 保留节点名 `__parent__` | `ValueError` | `GraphSpec`（保留名检查 · B9F1 FR-005） | C-09 |
| **CV-10** | 多源边形态（V-16） | `ValueError` | `GraphSpec` V-16（先于 V-2） | C-10 |
| **CV-11** | 断点的**容器形态**（`None` / `str` / `list` 之外） | `TypeError` | **`compile()` 入口层**（DR-5 · 唯一自写判据；`str` 原样透传，裸非 `"*"` 串由 CV-12 抛） | C-11 |
| **CV-12** | 断点的**元素** | `ValueError` / `TypeError` | `GraphSpec` 归一（V-22…V-25） | C-12 |
| **CV-13** | `path_map` 形态（⚠️ **早于** `compile()`） | `TypeError` | B6F1 **立即层**（`add_conditional_edges` 时就抛）· 用例 MUST 包裹**登记调用** | C-13 |
| **CV-14** | `path_map` 目标节点存在 | `ValueError` | `_build_spec()` → `_validate_targets` | C-14 |

**顺序**：`compile()` 先做 CV-11（容器形态，最外层、最早），随后 `_build_spec()` 的
**实际顺序**为 CV-1 → CV-2 → **CV-5** → CV-3 → CV-4 → CV-6 → CV-14 → CV-7
（`_validate_sources` 先于 `_validate_entrypoint`；CV-13 已在登记期），
最后 `GraphSpec` 构造（CV-8 → CV-9 → CV-10 → CV-12）。**同一次调用只抛第一个**；
**顺序不作为跨 feature 判据**。

## 7. 不检查项（NV-1…NV-7 · MUST NOT 查）

| # | 不检查项 | 反向判据（测试必须能证明「未报错」） | 归属 |
|---|---|---|---|
| **NV-1** | 路由函数的**返回值**是否在 `path_map` 中 | `path_map=None` 的图 `compile()` **成功** | B8F1 |
| **NV-2** | 节点函数的返回形态 | 返回 `Command` / `Send` / `None` 的节点 ⇒ `compile()` 成功 | B7F3 / B9F1 / B11F1 |
| **NV-3** | 节点可达性 | 存在不可达节点的图 ⇒ `compile()` **成功** | — |
| **NV-4** | 环 / 死循环 | 自环图 ⇒ `compile()` **成功** | B13F1 |
| **NV-5** | `checkpointer` / `store` 是否满足协议 | `compile(checkpointer=object(), store=object())` ⇒ **成功** | B14F1 |
| **NV-6** | 节点入参形状 / 归约器组合 | 任意合法 schema ⇒ `compile()` 不额外报错 | B4F1 / B5F1 |
| **NV-7** | `path_map` 的**键**（路由返回值）是否可枚举 | 任意 `Hashable` 键 ⇒ `compile()` 成功 | B8F1 |

---

## 8. 顺序与确定性

| 维度 | 顺序来源 | 判据 |
|---|---|---|
| 通道 key | schema 声明顺序（状态通道）→ 路由通道（静态目标首次出现顺序） | SC-009 |
| 节点表 | `add_node` 登记顺序 | SC-009 |
| 边表（源键） | 快照插入顺序（= 首次登记顺序），**过滤后保持相对顺序** | SC-009 |
| 边表（目标） | 快照元组顺序 | SC-009 |
| 条件边（外层 / 内层） | 源首次出现顺序 / 登记顺序 | SC-010 |
| 断点元组 | `normalize_static_points` 的保序去重 | SC-007 |

**结构等价**：同一构建器两次 `compile()` ⇒ 节点 / 边 / 条件边 / 断点逐字相等；
通道按「类型 + 归约器 + key」比较（**不比对象身份**）。

---

## 9. 状态机（编译期 · 单次 `compile()` 调用）

```text
[A] 入口 ← compile(6 关键字)
      │  ✗ 断点容器形态非法 ⇒ TypeError（CV-11 · 结束）
      ▼
[B] self._build_spec()
      │  ✗ schema / 源 / 入口 / 目标 / 空表 ⇒ ValueError / InvalidSchemaError（CV-1…CV-7）
      ▼
[C] OWN 适配：END 过滤（单源）· channels 新映射 · nodes 原样
      ▼
[D] GraphSpec(...)
      │  ✗ V-1 / V-2 / V-3 / V-8 / V-14 / V-16 / V-22…V-25 ⇒ ValueError / TypeError
      ▼
[E] 条件边 plain mapping（纯搬运）
      ▼
[F] 注入项记录 + （store 非 None ⇒ 1 条 warning）
      ▼
[G] 构造 CompiledGraph ⇒ 返回（每次新对象）
```

- **无副作用**：A–G 全程不调用任何用户函数、不读环境变量、不做 I/O。
- **失败不留痕**：任一 ✗ 均在**构造产物之前**抛出 ⇒ 不产生半成品产物；构建器状态不变。

---

## 10. 边界

- **空节点表**：`ValueError`（CV-7）⇒ 不产出产物（上游放行 · E-44 ⇒ B6F1 X-5）。
- **只有 `START -> END`**：同上（空节点表）。
- **条件边源为 `END`**：B6F1 构建期末已失败（CV-5）。
- **`path_map` 含 `END`**：合法；`targets` 含 `END`、`route_channels` 不含（B6F1 已做）。
- **`interrupt_before=[]`**：合法 = 不配置（归一为空元组）。
- **`interrupt_before="*"`**：展开为全部可执行节点（排除 `START` / `END`）。
- **`store` 传 `False` / `0` 等假值**：**非 `None`** ⇒ 仍发 1 条 warning（记录原值）。
- **`checkpointer=False`**：接受、记录、**零警告**。
- **同一构建器编译后继续 `add_node`**：允许、无提示；下次 `compile()` 取新快照。
- **产物私有字段被用户改写**：不冻结、不报错（I-8）。
- **产物公开属性被赋值**：不阻断（I-8 的口径）。
