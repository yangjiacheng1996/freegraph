<!-- authority: yes -->

# 编译契约（compile-contract.md）· B7F2

**Feature**: `specs/b7f2-compile/` · **Date**: 2026-11-16
**契约性质**: **冻结面 · 唯一权威** —— `compile()` 与编译产物的形状、判据、接口的**唯一**机器 / 人可读来源
**上位权威**: `spec.md`（需求与判据）· 本文件只把形状与机械判据**落细**，**不得**放宽 spec
**上游**: `langgraph 1.2.11`（锚点与实测见 `../research.md` §1 / §2）

> **机器标记**：本文件带 `<!-- authority: yes -->`（沿用层注册表 / 公开符号清单的「唯一权威」惯例）。
> 本 feature 的下游（B7F3 / B8F1 / B8F3 / B14F1 / B22F1）MUST 以 §8 的接口口径为准。

---

## 0. 作用域

本契约覆盖：

1. `StateGraph.compile()` 的**入口形状**（签名 · 关键字 · 失败信号）；
2. 编译产物 `CompiledGraph` 的**形状**（私有字段 / 公开属性 / 能力面）；
3. 编译期的**校验清单**（CV-1…CV-14）与**不检查项**（NV-1…NV-7）；
4. 静态断点的**两段判定**（入口容器形态 / 图规格元素级）；
5. 条件边 plain mapping 的**交接形状**；
6. 上述各面的**不变量**与**禁止事项**。

**不覆盖**：`invoke` 的执行语义（B7F3）· `stream`（B8F2）· 条件边求值（B8F1）·
图结构导出（B22F1 / B23F1）· checkpointer 行为（B14F1）· store 行为（v1 无实现）·
别名语义（B8F3）· 子图（v2）。

---

## 1. `compile()` 入口（**签名逐字冻结**）

```python
def compile(
    self,
    checkpointer: Checkpointer | None = None,
    *,
    cache: Any = None,
    store: Store | None = None,
    interrupt_before: Any = None,
    interrupt_after: Any = None,
    debug: bool = False,
    name: str | None = None,
    transformers: Any = None,
) -> CompiledGraph:
```

**判据**

| # | 要求 |
|---|---|
| 1.1 | **无参可调用**（全部关键字有缺省）；返回**非空**产物（SC-001） |
| 1.2 | `compile(checkpointer=None, store=None)` **不得**抛 `TypeError`（SC-002） |
| 1.3 | 参数名 / 顺序 / 种类 / 缺省值 MUST **逐字**等于 `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt` 的 `StateGraph.compile` 行 |
| 1.4 | MUST NOT 新增 / 删除 / 改名任何关键字 |
| 1.5 | 返回类型注解保持 `CompiledGraph`（L1 协议名） |

---

## 2. 编译产物形状

### 2.1 私有字段（**名字冻结** · 跨 feature 接口）

| 字段 | 类型 | 消费方 |
|---|---|---|
| `_spec` | `freegraph.runtime.GraphSpec` | B7F3（执行）/ B22F1（导出） |
| `_builder_spec` | `freegraph._stategraph._BuilderSpec` | 其他用途；**C25 已正式作废，B8F3 不再读取 alias** |
| `_conditional_edges` | `dict[str, tuple[dict[str, Any], ...]]` | B8F1（分支规格） |

> ⚠️ **MUST NOT 改名、MUST NOT 删除、MUST NOT 换成 property**（下游按名读取）。
> ⚠️ 下游 MUST **只读**：产物持有的是**快照**，改写它会破坏其他下游的视图。

### 2.2 公开属性（**读** · 注入项见 E-31；`transformers` 命名见 **X-12**）

| 属性 | 类型 | 值口径 |
|---|---|---|
| `checkpointer` | `Checkpointer \| None` | **原样**（身份保留 · E-53） |
| `store` | `Store \| None` | **原样** |
| `cache` | `Any` | **原样** |
| `debug` | `bool` | **原样**（缺省 `False` · 硬编码 · 零 env） |
| `name` | `str \| None` | **原样** |
| `transformers` | `Any` | **原样**（freegraph 自有命名；上游属性名为 `stream_transformers` ⇒ **X-12**） |
| `interrupt_before_nodes` | `tuple[str, ...]` | `_spec.interrupt_before`（**归一后**） |
| `interrupt_after_nodes` | `tuple[str, ...]` | `_spec.interrupt_after`（**归一后**） |

> **「只读」的口径**：只读 = **用户不需要写**。本契约**不要求**赋值被拒（不新增异常类型）；
> 测试只断言「存在 + 值正确」。
> ⚠️ **载体 MUST 为实例属性（不是 `@property`）** ⇒ 否则 `vars(compiled)` 不含它们，
> §7 的 I-1「11 键」不成立。

### 2.3 其余一切 → 私有

`nodes` / `channels` / `builder` / `graph` / `spec` 等名字 **MUST NOT** 出现在产物的公开属性面上
（X-10：上游公开它们，freegraph 走 `get_graph()` 导出，B22F1）。

### 2.4 能力面（6 方法 · 签名逐字对齐 L1 协议）

| 方法 | 本 feature 行为 |
|---|---|
| `invoke(input, config=None)` | `NotImplementedError`（消息含 `B7F3`） |
| `stream(input, config=None, *, stream_mode="values")` | `NotImplementedError`（含 `B8F2`） |
| `get_graph(*, xray=False)` | `NotImplementedError`（含 `B22F1`） |
| `get_state(config)` | `NotImplementedError`（含 `B15F1`） |
| `get_state_history(config)` | `NotImplementedError`（含 `B15F1`） |
| `update_state(config, values, as_node=None)` | `NotImplementedError`（含 `B16F1`） |

> ⚠️ **2026-11-20 · B8F2 回溯修订注记（T-3 · 只补注记 · 原描述不改写）**：
> 自 **B8F2** 起，`stream` 的**行为**由 `NotImplementedError` 改为**真实交付**，且
> **签名默认值**由 `stream_mode="values"` 改为 **`stream_mode=None`（解析为 `"updates"`）**、
> `config` 注解放宽为 `RunConfig | Mapping[str, Any] | None`（与 L1 协议同步）。
> 上表原 `"values"` / `NotImplementedError` 文字**保留为历史事实**；现行权威以
> `specs/b8f2-stream-modes/contracts/stream-contract.md` 与 `specs/b2f1-contracts-protocols/contracts/public-api.md` 为准。

**判据**：`hasattr` 6/6；`AttributeError` 出现次数 == 0；静默返回 `None` 次数 == 0。

---

## 3. 校验清单

### 3.1 MUST 查（CV-1…CV-14）

见 `../data-model.md` §6（逐项：检查项 / 失败信号 / 判定来源 / spec 编号）。**要求**：

- 3.1.1 **单一真源**：CV-1…CV-10、CV-12…CV-14 **MUST** 由 `_build_spec()` 或
  `GraphSpec.__post_init__` 产出；`compile()` **MUST NOT** 重写同义判定。
- 3.1.2 **唯一自写判据** = CV-11（断点容器形态 · §4）。
- 3.1.2b ⚠️ **CV-13 的时机例外**：`path_map` 形态由 B6F1 的**立即层**在
  `add_conditional_edges` 时失败 ⇒ **早于** `compile()` ⇒ 其用例 MUST 包裹**登记调用**，
  MUST NOT 假定 `compile()` 会抛（3.1.3 的「在 compile 调用点」对它**不适用**）。
- 3.1.3 **时机**：全部在 **`compile()` 调用点**抛出（MUST NOT 推迟到 `invoke()`）。
- 3.1.4 **异常类型面**：内置 `ValueError` / `TypeError`；schema 非法沿用
  `freegraph.runtime.InvalidSchemaError`；**零新增异常类型**。
- 3.1.5 **消息可定位**：含问题节点 / 源 / 分支 / 目标 / `entrypoint` / 字段名。

### 3.2 MUST NOT 查（NV-1…NV-7）

见 `../data-model.md` §7。**每条 MUST 有反向测试**（证明「未报错」），尤其：

- `path_map=None` 的动态路由图 **`compile()` 成功**；
- `compile(checkpointer=object(), store=object())` **成功**（仅 store 发 1 条 warning）；
- 不可达节点 / 自环图 **`compile()` 成功**。

---

## 4. 静态断点的两段判定

### 4.1 入口层（`compile()` · **只判容器形态**）

| 输入 | 动作 |
|---|---|
| `None` | 归一为 `()` |
| `str`（含 `"*"`） | **原样**交 `GraphSpec` |
| `list` | **原样**交 `GraphSpec` |
| 其它（`tuple` / `set` / `dict` / 数值 / …） | `TypeError`（V-22 家族 · 消息含字段名与类型） |

### 4.2 图规格层（`normalize_static_points` · **元素级唯一真源**）

| 输入 | 结果 |
|---|---|
| `"*"` | 全部可执行节点（排除 `__start__` / `__end__`） |
| 空串元素 | `ValueError`（V-23） |
| 元素 ∈ {`__start__`, `__end__`, `"*"`} | `ValueError`（V-24） |
| 未知节点名 | `ValueError`（V-25 · **点名该节点**） |
| 非 `str` 元素 | `TypeError`（V-22） |

**判据**：对同一字段、同一非法值，入口层委托产生的异常 **类型 + 消息字符串** MUST 与本契约
§4.2 直接调用 `normalize_static_points` 的结果 **逐字相等**（B13F1 D-2）。

### 4.3 归一结果

`_spec.interrupt_before` / `_spec.interrupt_after` = **保序去重后的元组**；
产物公开属性 `interrupt_before_nodes` / `interrupt_after_nodes` **逐字等于**它们（X-11）。

---

## 5. 条件边 plain mapping（`_conditional_edges`）

见 `../data-model.md` §4（形状 + I-9…I-13）。**判据**：

| # | 要求 |
|---|---|
| 5.1 | 外层 key = 源节点名（含 `"__start__"`）；顺序 = 源首次出现顺序 |
| 5.2 | 内层分支项**恰 5 键**：`branch` / `path` / `path_map` / `targets` / `route_channels` |
| 5.3 | `branch` **逐字**取自 `_ConditionalEdgeSpec.branch`（MUST NOT 由 `path.__name__` 重算） |
| 5.4 | `path_map` / `targets` / `route_channels` **零归一化、零过滤**（`END` 保留在 `targets`，不在 `route_channels`） |
| 5.5 | `_spec.conditional_edges` **恒为空**（填了即 V-8 失败） |
| 5.6 | 该映射 MUST 只放在**私有字段** `_conditional_edges`（不进公开属性面、不进 L2 字段） |

---

## 6. 注入项与 `store` 警告

| # | 要求 |
|---|---|
| 6.1 | 6 个关键字**全部接受**（含非法类型 / 假值），**零类型校验**，**零 `TypeError`** |
| 6.2 | 全部**原样记录**（身份保留）并可从**公开属性**读到 |
| 6.3 | `store` **非 `None`** ⇒ `warnings.warn(msg, stacklevel=2)` **恰好 1 条**，消息含 `Store` |
| 6.4 | `store is None` ⇒ **0 条**；`checkpointer` / `cache` / `transformers` / `debug` / `name` ⇒ **0 条** |
| 6.5 | 文档 MUST 写明「**v1 不支持 `Store`**」与「checkpointer 的行为归 B14F1」 |
| 6.6 | MUST NOT 用 `logging` 代替 `warnings`（本条的机制由用户裁定为 `warnings.warn`） |

---

## 7. 不变量（汇总）

| # | 不变量 | 判据 |
|---|---|---|
| I-1 | `vars(compiled)` = 3 私有 + 8 公开 = **11** 个 key，零多余 | SC-010 / SC-013 |
| I-2 | 8 个公开属性恒可读 | SC-002 / SC-015 |
| I-3 | `_spec.conditional_edges` 恒空 | SC-010 |
| I-4 | `_spec.channels` 与 `_builder_spec.channels` 是**两个映射对象** | SC-011 |
| I-5 | 产物内通道全为**未写入模板** | SC-011 |
| I-6 | `_builder_spec` 内容**未被改写** | SC-010 |
| I-7 | 三个私有字段名逐字冻结 | SC-010 |
| I-8 | 不要求公开属性「赋值被拒」 | FR-018 |
| I-9…I-13 | 条件边映射的顺序 / 键集 / `branch` / 原样搬运 / 恒空 | SC-010 |
| I-14 | 每次 `compile()` 返回**新对象**，产物间私有状态**不共享** | SC-012 |

---

## 8. 跨 feature 接口（下游 MUST 照此读取）

| 下游 | 读取点 | 允许 | 禁止 |
|---|---|---|---|
| **B7F3** | `compiled._spec`（交给 `run_graph`）· `compiled.checkpointer` | 读 | 改写 `_spec`；另建执行路径 |
| **B8F1** | `compiled._conditional_edges`（读取并填入 `GraphSpec.conditional_edges`）· `_spec.channels` 的 `branch:to:*`；**路由求值只消费 `GraphSpec.conditional_edges`** | 读 | import `freegraph._stategraph` / `_ConditionalEdgeSpec`；重算 `branch`；重归一化 `path_map` |
| **B8F3（历史 · 已撤回）** | ~~`compiled._builder_spec.node_records[*].alias`~~ | 不读 | C25 已正式作废；不改写快照 |
| **B14F1** | `compiled.checkpointer`（行为落地） | 读 | —— （并 MUST 补编译期类型校验 · D-4） |
| **B22F1** | `compiled._spec`（节点 / 边 / 通道）+ `compiled._conditional_edges` | 读 | 重新解析构建器状态 |
| **B23F1** | 经 B22F1 的 `Graph` | —— | 直接读产物私有字段 |

---

## 9. 禁止事项（MUST NOT）

1. 在 `compile()` 内**重解析 schema** / 重造节点表 / 边表 / 通道表；
2. 在 `compile()` 内**另写**一套图结构校验（CV-1…CV-10 / CV-12…CV-14）；
3. 在 `compile()` 内**调用**任何用户函数（节点 / 路由 / 归约器）；
4. 在编译期**写入**任何通道值；
5. 把 `conditional_edges` 填进 `GraphSpec`（V-8 会失败）；
6. 在编译期对 `checkpointer` / `store` 做**类型校验**；
7. 把 `CompiledGraph` 放进 `freegraph.graph` 的导出面或 API 快照；
8. 新建 **L3 横向**源文件（层注册表冻结 · G25）；
9. 新增异常类型 / 新增门禁编号 / 改 `harness/demo/target.py`；
10. 读环境变量 / 做 I/O / 发起任何出站连接。

---

## 10. 证据（本契约每条断言的实测来源）

| 断言 | 证据 |
|---|---|
| §1.1 / §1.2 | E-27 / E-28 |
| §1.4（关键字集合） | E-27 / E-28 + B2F2 快照 |
| §2.2（公开属性集合） | E-31 / E-33 / E-47 / E-48 / E-53 / E-54 / E-55（⚠️ E-31 **不含** `transformers`；命名差异 ⇒ **X-12**） |
| §2.3（门面不导出产物类） | E-25 / E-26 |
| §2.4（6 方法） | E-32 |
| §3.1.4（缺入口 / 未知目标的失败信号） | E-51 / E-52 |
| §3.2 NV-5（非法 checkpointer 上游 = TypeError · freegraph 不校验） | E-29 |
| §4.1（元组 / 裸串 / set 的容器失败） | E-37 / E-38 / E-45 / E-46 |
| §4.1（裸空串上游放行 ⇒ freegraph 更严） | E-36 |
| §4.2（`["*"]` / 未知节点 ⇒ ValueError） | E-35 / E-39 |
| §4.3（上游保留原值 ⇒ freegraph 归一元组 = X-11） | E-47 / E-48 |
| §6（上游 store 无警告 · 本条的警告是 freegraph 增量） | E-30 |
| §9.2（上游 `__all__` 不含产物类） | E-25 |
