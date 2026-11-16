# 上游对照与差分取证底稿（upstream-parity.md）· B7F2

**Feature**: `specs/b7f2-compile/` · **Date**: 2026-11-16
**上游版本**: `langgraph 1.2.11`（取证于 2026-11-16 ·
`.venv/lib/python3.11/site-packages/langgraph`）
**上位权威**: `spec.md` 的 **Upstream Parity** / **差分场景组** / **偏离登记** 三节（判词以 spec 为准）
**本文件作用**：把 spec 的三张表落成**可核对底稿**（锚点 · 实测编号 · 差分实现口径 · 一致性自检）

> ⚠️ **三态标注一致性**（宪法 v1.12.0）：同一分叉在本文件与 spec 的标注 MUST **逐字一致**。
> 若两者冲突 ⇒ 以 **spec** 为准并回修本文件。

---

## 1. 上游源码锚点

| # | 语义点 | 锚点 |
|---|---|---|
| A-01 | `compile()` 签名 | `langgraph/graph/state.py:1177-1189` |
| A-02 | checkpointer 校验（调用） | `langgraph/graph/state.py:1234` |
| A-03 | checkpointer 校验（定义） | `langgraph/types.py:109-118` |
| A-04 | 断点归一 `or []` + `validate` 调用 | `langgraph/graph/state.py:1264-1272` |
| A-05 | `validate()`（源 / 入口 / 目标 / 断点节点 / `compiled=True`） | `langgraph/graph/state.py:1129-1175` |
| A-06 | 产物构造（含通道集合） | `langgraph/graph/state.py:1346-1371` |
| A-07 | 通道集合明细（`START` / managed） | `langgraph/graph/state.py:1354-1358` |
| A-08 | `attach_node` / `attach_edge` / `attach_branch` | `langgraph/graph/state.py:1373-1399` · `:1444` · `:1551` · `:1577` |
| A-09 | 产物类定义 | `langgraph/graph/state.py:1404-1407` |
| A-10 | `Pregel` 类 | `langgraph/pregel/main.py:450` |
| A-11 | 公开属性赋值 | `langgraph/pregel/main.py:800-830` |
| A-12 | 路由通道名 | `langgraph/graph/state.py:98` · `:1525-1530` |
| A-13 | 6 方法入口 | `langgraph/pregel/main.py:845` · `:1392` · `:1480` · `:2515` · `:2616+` · `:3783+` |
| A-14 | 通道规格 / 每次运行新建 | `langgraph/channels/last_value.py:50-54` · `langgraph/channels/base.py:61-64` |
| A-15 | 门面导出面 | `langgraph/graph/__init__.py`（`__all__` 6 项） |

---

## 2. 语义点表（与 spec 的 P 表逐条对应）

| # | 语义点 | 锚点 | freegraph 口径 | 关系 | 偏离 | 实测 |
|---|---|---|---|---|---|---|
| P-01 | `compile()` 方法名 / 关键字集合 | A-01 | 逐字沿用 B6F1 / B2F2 冻结面 | SAME | — | E-27 / E-28 |
| P-02 | **无参可调用** | A-01 | 同款 | SAME | — | E-27 |
| P-03 | 产物**类型与基类链** | A-09 / A-10 | 持有并驱动 L2 运行时（非基类） | DIFF | X-1 | E-27（上游类名 `CompiledStateGraph`） |
| P-03b | 产物类**是否进门面导出面** | A-15 | 不进 | SAME | — | E-25 / E-26 |
| P-03c | 产物**公开属性** | A-11 | 暴露 8 个注入项 / 断点属性；内部规格私有 | SAME（注入项）/ DIFF（`transformers` 命名 ⇒ X-12；`nodes` / `channels` / `builder` 私有 ⇒ X-10） | X-10 / X-12 | E-31 |
| P-03d | **断点属性的值形态** | A-11 | 归一后的**保序元组** | DIFF | X-11 | E-47 / E-48 |
| P-04 | 挂载节点 | A-08 | 产物持 `NodeSpec`（结构同构） | SAME | — | — （结构面） |
| P-05 | 断点**接受形态与归一** | A-04 / A-12 | `None` / `"*"` / `list[str]`；`"*"` ⇒ 全部可执行节点（**编译期**展开） | SAME | — （展开时机归 B13F1 X-2） | E-34 / E-40 |
| P-05b | 断点**裸空串** | A-04 | 入口层 `TypeError` | STRICTER | X-2 | E-36 |
| P-05c | 断点**元组 / 裸非 `"*"` 字符串 / `set`** | A-04 | 入口层 `TypeError` | SAME（失败信号家族） | — | E-37 / E-38 / E-45 / E-46 |
| P-06 | **编译期校验** | A-04 / A-05 | 等价校验（源 / 入口 / 目标 / 断点 / 非空节点表） | SAME | — | E-51 / E-52 |
| P-07 | 挂载边 | A-08 | 产物持边表（结构同构） | SAME | — | — （结构面） |
| P-08 | 边表键类型 | A-08 | `str \| tuple[str, ...]` 原样透传 | SAME | — | — （B7F4 收紧面） |
| P-09 | `store=` | A-01 / A-11 | 接受 + 记录 + **1 条 warning**，v1 无实现 | DIFF | X-3 | E-30 |
| P-10 | `checkpointer=` 与**编译期类型校验** | A-01 / A-02 / A-03 | 接受 + 记录；**不校验** | DIFF | X-4 | E-29 |
| P-11 | 挂载条件分支 | A-08 | 私有 plain mapping；`GraphSpec.conditional_edges` 恒空 | DIFF | X-6 | — （结构面） |
| P-12 | `→ END` 的边 | A-08 | 单源 `END` 目标**过滤** | DIFF | X-7 | E-43（`END` 不在上游 `nodes`） |
| P-13 | 「已编译」标志 / 改图提示 | A-05 | 不设标志、不提示 | DIFF | X-5 | E-41 / E-49 / E-50 |
| P-14 | 通道集合（`START` / 路由通道） | A-06 / A-07 / A-12 | 照建 `branch:to:<target>` + `EphemeralValue(Any, guard=False)`；**不建 `START` 通道**；路由通道**只为条件边静态目标**建 | DIFF | X-8 | E-43 |
| P-15 | 只持通道**规格** / 每次运行新建 | A-14 | 同款（L2 `_run_channels`） | SAME | — | — （B12F1 实测） |
| P-16 | 产物**能力面 6 方法** | A-13 | 6 方法齐备；未就绪抛 `NotImplementedError` | SAME（方法面）/ 未就绪信号为 freegraph 增量 | — | E-32 |
| P-17 | 其余选项（`cache` / `debug` / `name` / `transformers`） | A-01 / A-06 | 接受 + 记录；v1 无行为 | SAME（接受面） | — | E-54 / E-55 |
| P-17b | `debug` **缺省值来源** | A-11（`get_debug()`） | 硬编码 `False` | DIFF | X-9 | E-33 |
| P-18 | 可达性 / 环的编译期检查 | A-04 / A-05 | **不做** | SAME | — | — （上游源码无该检查） |

> **实测编号**：E-25…E-55（见 `../research.md` §1）。本文件只引用编号，不复制原始输出。
> E-01…E-24 属 B6F1，不重号。

---

## 3. 差分场景（D-75…D-91）· 实现口径

**落点**：`tests/differential/parity_probe.py` ⇒ 新增 `CompileScenario`（不改既有 runtime / builder 场景）。
**上游缺席 ⇒ 空列表 ⇒ `skip`**（沿用 B5F2 纪律）。

### 3.1 判定口径（`CompileScenario`）

```text
两侧各自执行 fn() ⇒ 得到下列归一化观测：
   kind      : "OK" | "ERROR"
   exc_type  : 异常类名（失败时）
   summary   : 成功时的离散摘要
               ( has_6_methods: bool,
                 store_identity_kept: bool,      # compiled.store is <sentinel>
                 store_warning_count: int,       # warnings.catch_warnings(record=True)
                 interrupt_before_nodes: tuple,  # 归一后的元组（freegraph）/ 原值（上游）
                 has_not_implemented: bool )     # 任一方法调用抛 NotImplementedError

判定：
   SAME      ⇒ kind 相等 且（同为 ERROR ⇒ exc_type 相等；同为 OK ⇒ 按场景 note 指定的**子集**相等）
   STRICTER  ⇒ note 非空 且 方向合法（freegraph=ERROR 且 upstream=OK，或同为 ERROR 但 freegraph
               的失败更早 / 类型更明确 —— 由 note 写明）
   DIFF      ⇒ note 非空（不做相等断言，只要求两侧均可判定）
```

**归一化纪律**：摘要**MUST NOT** 含对象身份 / 内存地址 / 异常消息全文（消息不冻结）；
断点元组按场景声明「比较 / 不比较」（`"*"` 场景不比较值 —— 展开时机差异归 B13F1 X-2）。

### 3.2 场景清单

| # | 场景 | freegraph | 上游 | 断言 | 判词 |
|---|---|---|---|---|---|
| **D-75** | 最小合法图 `compile()`（无参） | OK | OK | 产物非空 · 6 方法 · 6 个能力面方法存在于两侧 | SAME |
| **D-76** | `compile(checkpointer=None, store=None)` | OK | OK | 两侧均 OK | SAME |
| **D-77** | `compile(checkpointer=<非 saver>)` | OK（记录） | ERROR `TypeError` | 两侧 kind 不同，**note 写明** | DIFF（X-4） |
| **D-78** | `compile(store=<任意对象>)` | OK + **1 条 warning** | OK + 0 条 | note 写明（warning 是 freegraph 增量） | DIFF（X-3） |
| **D-79** | `compile(interrupt_before=["nope"])` | ERROR `ValueError` | ERROR `ValueError` | 类型相等；freegraph 消息含 `nope` | SAME |
| **D-80** | `compile(interrupt_before="*")` | OK | OK | 两侧 OK；**不比较**断点属性值 | SAME |
| **D-81** | `compile(interrupt_before=("a",))` | ERROR `TypeError` | ERROR `TypeError` | 类型相等 | SAME |
| **D-82** | `compile(interrupt_before="")` | ERROR `TypeError` | OK | note 写明 | STRICTER（X-2） |
| **D-83** | `compile(interrupt_before="a")` | ERROR `TypeError` | ERROR `TypeError` | 类型相等 | SAME |
| **D-84** | `compile(interrupt_before=["*"])` | ERROR `ValueError` | ERROR `ValueError` | 类型相等 | SAME |
| **D-85** | 边指向不存在节点 | ERROR `ValueError` | ERROR `ValueError` | 类型相等；freegraph 消息含目标名 | SAME |
| **D-86** | 缺少 `START` 入口 | ERROR `ValueError`（含 `entrypoint` / `START`） | ERROR `ValueError` | 类型相等；freegraph 消息含 `entrypoint` / `START` | SAME |
| **D-87** | 条件边源不存在 | ERROR `ValueError` | ERROR `ValueError` | 类型相等；freegraph 消息含源 | SAME |
| **D-88** | `path_map` 目标不存在 | ERROR `ValueError` | ERROR `ValueError` | 类型相等；freegraph 消息含源 / 分支 / 目标 | SAME |
| **D-89** | `path_map=None`（动态路由） | OK | OK | 两侧 OK | SAME |
| **D-90** | `compile()` 后再 `add_node` | OK · **0 条 warning** | OK · 1 条 **logging** 记录 | note 写明（机制 + 行为均不同） | DIFF（X-5） |
| **D-91** | 同一构建器连续 `compile()` 两次 | OK · 两对象不同 | OK · 两对象不同 | 两侧均为两个不同对象 | SAME |

> ⚠️ **D-82 的判词与 spec 的对照表 MUST 一致**：D-82 ⇒ **P-05b / X-2**（STRICTER）。
> **空图（`START -> END`）**的差异（上游放行 E-44 · freegraph V-3 拒绝）**已在 B6F1 的
> D-72 / X-5 登记**，属**构建期**分叉、编译期只是同一分叉的**再次可观察** ⇒
> **本 feature 不新增差分行、不新增偏离编号**（避免同一分叉两处登记）。

---

## 4. 偏离登记（X-1…X-12）· 取证底稿

| # | 类别 | 分叉 | 理由（压缩） | 判据 / 证据 |
|---|---|---|---|---|
| **X-1** | 分层接缝（DIFF） | P-03：产物**不是**运行时基类 | freegraph 分层（L2 执行 / L3 定义）· 原则 XII | 立项书 §5.1 · A-09 |
| **X-2** | 更严失败信号（STRICTER） | P-05b：裸空串断点 ⇒ `TypeError` | 上游静默接受会误导 | E-36 |
| **X-3** | 定位边界（DIFF） | P-09：`store=` 接受 + **1 条 warning**，v1 无实现 | 原则 VII · 用户裁定 A | E-30 |
| **X-4** | 能力未就绪（DIFF） | P-10：不校验 checkpointer | v1 无实现 · 补校验归 B14F1 | E-29 + D-4 |
| **X-5** | 范围边界（DIFF） | P-13：不设 `compiled` 标志 / 不改图提示 | B6F1 已裁定不复制 | E-41 / E-49 / E-50 |
| **X-6** | 分层接缝（DIFF） | P-11：条件边挂私有映射；`GraphSpec.conditional_edges` 恒空 | B7F1 的 V-8 | — |
| **X-7** | 分层接缝（DIFF） | P-12：单源 `END` 过滤 | 节点表不含 `END` · V-2 | E-43 |
| **X-8** | 分层接缝（DIFF） | P-14：不建 `START` 通道；路由通道只为条件边静态目标建 | 入口哨兵 / B6F1 裁定 3 | E-43 |
| **X-9** | 零环境变量红线（DIFF） | P-17b：`debug` 硬编码 `False` | 原则 I | E-33 |
| **X-10** | 分层接缝（DIFF） | P-03c：`nodes` / `channels` / `builder` 私有 | 快照隔离 + B22F1 导出 | E-31 |
| **X-11** | 形态优化（DIFF） | P-03d：断点属性暴露**归一元组** | 原则 XII（单一载体） | E-47 / E-48 |
| **X-12** | 命名形态（DIFF） | P-03c：公开属性 `transformers`（上游为 `stream_transformers`） | 与 compile 关键字同名、单一载体（原则 XII） | E-31 + `pregel/main.py:831` |

**X 与 P 的双向映射**（宪法 v1.12.0 一致性自检）：

- STRICTER：P-05b ⇔ X-2 **（唯一）**；P-06 家族不单独登记（上游同款）。
- DIFF：P-03 ⇔ X-1 · P-09 ⇔ X-3 · P-10 ⇔ X-4 · P-13 ⇔ X-5 · P-11 ⇔ X-6 ·
  P-12 ⇔ X-7 · P-14 ⇔ X-8 · P-17b ⇔ X-9 · P-03c ⇔ X-10 / X-12 · P-03d ⇔ X-11。
- SAME：P-01 / P-02 / P-03b / P-04 / P-05 / P-05c / P-06 / P-07 / P-08 / P-15 / P-16 / P-17 / P-18
  ⇒ **无**偏离登记行。

---

## 5. 三态一致性自检（逐条打勾）

- [x] 每条 STRICTER 都落在偏离登记（P-05b ⇒ X-2）
- [x] 每条 DIFF 都落在偏离登记（10 条）
- [x] 偏离登记的每一条都有对照表对应行（X-1…X-12 全部命中）
- [x] 外部编号（`B6F1 的 X-5` / `B13F1 X-2` / `B6F1 D-1`）**MUST** 带限定词 —— 已带
- [x] 差分表的判词与对照表一致（17/17；空图分叉归**外部** `B6F1 的 D-72 / X-5`，本 feature 不重复登记）
- [x] 无「同一分叉两处不同标注」

---

## 6. 换版本复核清单

1. 重跑 `harness/verification/B7F2/probe_upstream.py` ⇒ 核对 **E-25…E-55**；
2. 重核 §1 的 **A-01…A-15** 全部行号；
3. 重跑 `D-75…D-91`（上游缺席 ⇒ `skip`）；
4. 重点复核 **X-2 / X-3 / X-4 / X-5 / X-11 / X-12** 的取证点（E-36 / E-30 / E-29 / E-49-E-50 / E-47-E-48 / E-31 + `main.py:831`）；
5. 若上游把 `compile()` 的断点容器失败改成**显式**类型（不再是拼接副作用）⇒ 复核 P-05c 的
   「失败信号家族」判词；
6. 若上游给 `store=` 加了警告 / 或 `compiled` 的属性面变化 ⇒ 同步 P-09 / P-03c 的判词与
   X-3 / X-10 的理由。
