# 上游对照 · B6F1 · `StateGraph` 构建器

**Spec**: [../spec.md](../spec.md) · **Research**: [../research.md](../research.md) · **Date**: 2026-11-15
**上游版本**: `langgraph` **1.2.11**
**取证环境**: `/home/ctyun/workspace/github/freegraph/.venv/lib/python3.11/site-packages/langgraph`

> **原则 XI**：上游是唯一权威；每条行为断言带版本 + `路径:行号`；行为断言有实测支撑。
> 本文件是 spec 的上游对照表 / 差分场景组 / 偏离登记的取证底稿；语义以 `spec.md` 为准。

---

## §1 上游对照表（P-01…P-14）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | `StateGraph` 类与构造参数名 | `langgraph/graph/state.py:131` · `:216-225` | 同名同签名；`state_schema` 唯一必填位置参数；其余可选 | SAME | 宪法原则 III 第 2 项 |
| P-02 | `add_node(node, action, *, defer, metadata, ...)` 与单 callable 形态 | `langgraph/graph/state.py:667-682` · `:778-799` | 同名同签名；支持单 callable；普通 callable `.name` 不参与取名 | SAME | 宪法原则 III 第 3 项 · E-21 |
| P-02b | `add_node(..., alias=...)` | `langgraph/graph/state.py:667-682`（签名无 `alias`；运行时经 `**kwargs` 静默忽略 · 实测 E-24） | `alias` 为 freegraph 自研增量，只记录不实现语义 | DIFF | C25 · B8F3 ⇒ X-1 · D-74 |
| P-02c | 普通 callable 的 `.name` 不参与取名 | `langgraph/graph/state.py:778-799`（实测 E-21） | 同款：`__name__` → 类型名；`.name` 忽略 | SAME | 上游首段已把 `node` 固定为 `str` ⇒ 第二段不再取 `.name` |
| P-03 | 重复节点名 / 保留节点名 / 保留字符 | `langgraph/graph/state.py:802-811` · `langgraph/_internal/_constants.py:87-89` · 实测 E-18 | `add_node` 立即 `ValueError`，消息点名节点 | SAME | 早失败且异常类型一致 |
| P-03b | 缺 `action` / 单 callable 同时传 `action` | `langgraph/graph/state.py:800-801`（缺 action ⇒ `RuntimeError`）· `:782-799`（单 callable 忽略 action） | 缺 action / 多传 action ⇒ 立即 `TypeError` | STRICTER | 统一用户输入错误类型，且不静默忽略 ⇒ X-4 |
| P-03c | `action` 不可调用 / `node` 非 `str` 非 callable | `langgraph/_internal/_runnable.py:579`（`coerce_to_runnable` 抛 `TypeError`） | 立即 `TypeError` | SAME | 异常类型一致；消息不冻结 |
| P-04 | `add_edge(start_key, end_key) -> Self` 与多源源 | `langgraph/graph/state.py:928` · `:951-979` | 同名同签名；单源 `str`、多源 `list` / `tuple`；链式返回 `Self` | SAME | 宪法原则 III 第 4 项 |
| P-04b | 空多源 source（`[]` / `()`） | `langgraph/graph/state.py:969-979`（实测 E-09 接受） | 立即 `ValueError` | STRICTER | 空汇合无意义，早失败 ⇒ X-2 |
| P-04c | 单源边 `end_key` 非 `str` | `langgraph/graph/state.py:958`（上游不校验 `end_key` 类型） | 立即 `TypeError` | STRICTER | 非法目标值会让错误推迟到上游 `validate()` / `compile()` ⇒ X-2 |
| P-04d | 非法 `start_key` 类型（既非 `str` 也非 list / tuple） | `langgraph/graph/state.py:951-979`（迭代非可迭代对象 ⇒ `TypeError` · 实测 E-22） | 立即 `TypeError` | SAME | 异常类型与上游一致；消息不冻结 · D-69 |
| P-05 | 边的 `END` 源 / `START` 目标失败信号 | `langgraph/graph/state.py:951-955` · `:969-977` · 实测 E-19 | `add_edge` 立即 `ValueError` | SAME | 与上游同款 |
| P-06 | `add_conditional_edges(source, path, path_map) -> Self` | `langgraph/graph/state.py:982-989` · `:1018-1027` | 同名同签名；`path_map` list / dict / None | SAME | 宪法原则 III 第 5 项 |
| P-06b | 条件边 `source` 非 `str` | `langgraph/graph/state.py:1008-1025`（上游直接作为 `branches` 键；`validate()` 才报未知源） | 立即 `TypeError` | STRICTER | 非法源键会让错误推迟到构建期末 ⇒ X-2 |
| P-06c | 非 callable `Runnable` 作为 `path` | `langgraph/graph/state.py:1018-1019`（`coerce_to_runnable` · 实测 E-23） | 仅接受 callable；非 callable ⇒ 立即 `TypeError` | DIFF（范围边界） | 零 langchain 约束 ⇒ X-6 |
| P-07 | `path_map` list / dict 归一化 | `langgraph/graph/_branch.py:89-120` · `:98-101` | list → `{name: name}`；dict 浅拷贝；None 保持 / 推断 | SAME | 与上游同构 |
| P-07b | `path_map=None` 的 `Literal[...]` 推断 | `langgraph/graph/_branch.py:102-114` | 仅 `Literal[...]` 时展开；异常 / 非 Literal ⇒ 保持 None | SAME | 与上游同款 |
| P-07c | `path_map` 的 list 元素 / dict value 非 `str` | `langgraph/graph/_branch.py:96-101`（上游不校验元素类型） | 立即 `TypeError` | STRICTER | 非法目标值会让错误推迟到上游 `validate()` / `compile()` ⇒ X-2 |
| P-08 | 同一源上同名分支重复 / 分支名推断 | `langgraph/graph/state.py:1022-1025` · `langgraph/_internal/_runnable.py:313-319`（实测 E-21） | `add_conditional_edges` 立即 `ValueError`；分支名 `__name__`（普通 callable `.name` 不参与），lambda / 无名 ⇒ `condition` | SAME | 与上游同款 |
| P-09 | 构建期末的边 / 条件边 / 入口 / `interrupt` 节点校验 | `langgraph/graph/state.py:1129-1175` · `:1138-1145` · `:1147-1168` · `:1168-1174` · `:1175`（`compiled=True`） | `validate()` / `_build_spec()` 抛 `ValueError`，消息点名；`validate(interrupt=...)` 对未知节点抛 `ValueError`；顺序 = 源 → 入口 → 目标（空节点表见 P-14） | SAME（校验顺序 / 失败信号） | 上游 `validate()` 同款；`compiled=True` 副作用不复制（B6F1 无 compile 状态，范围边界） |
| P-10 | `path_map` 非法容器类型 | `langgraph/graph/_branch.py:96-116`（非 dict / list 落入 else：无 `Literal` ⇒ None；有 `Literal` 则推断） | 立即 `TypeError` | STRICTER | 上游静默降级 / 静默推断不可接受 ⇒ X-2 |
| P-11 | 构建器内部规格 | `langgraph/graph/state.py:1242-1247` / `:1374-1399`（`compile()` 读取自身 `nodes` / `edges` / `branches`） | 私有 `_build_spec() -> _BuilderSpec` | DIFF（分层接缝） | L3 构建器与 L2 运行时物理分层 ⇒ X-3（原则 XII 形态优化） |
| P-12 | 静态断点关键字 | `langgraph/graph/state.py:1177-1188` | 构建器不拦截；`compile()` 由 B7F2 接受 | SAME | H-6 · D-7 |
| P-13 | 条件边路由通道的类型与 guard（非 defer） | `langgraph/graph/state.py:1525-1530`（非 defer 用 `EphemeralValue(Any, guard=False)`） | `EphemeralValue("branch:to:<target>", Any, guard=False)` | SAME | 与上游**非 defer** 路由通道同款；行为面由 B5F1 差分覆盖 |
| P-13b | `defer=True` 目标的路由通道类型 | `langgraph/graph/state.py:1525-1530`（defer 用 `LastValueAfterFinish(Any)`） | B6F1 统一用 `EphemeralValue` | DIFF（已知不支持） | defer 屏障不在本 feature 实现 ⇒ 登记 X-7；B7F4 X-03 同源 |
| P-14 | 空节点表 / `START -> END` 空图 | `langgraph/graph/state.py:1138-1168`（实测 E-20） | 空节点表 ⇒ `ValueError` | STRICTER | 与 L2 `GraphSpec` V-3 一致 ⇒ X-5 |

### §1.1 三态一致性

- DIFF：P-02b（alias 增量 → X-1）· P-06c（Runnable 范围边界 → X-6）· P-11（内部快照 → X-3）· P-13b（defer 路由通道 → X-7）；
- STRICTER：P-03b（缺 action → X-4）· P-04b / P-04c / P-06b / P-07c / P-10
  （空多源 / 非 str 输入 / 非法 path_map 元素 → X-2）· P-14（空节点表 → X-5）；
- SAME：P-01 / P-02 / P-02c / P-03 / P-03c / P-04 / P-04d / P-05 / P-06 / P-07 / P-07b / P-08 /
  P-09（顺序）/ P-12 / P-13（非 defer）；
- 无孤行、无漏行；同一分叉只保留一个关系判词。

---

## §2 实测取证（E-01…E-24）

| # | 场景 | 上游结果 |
|---|---|---|
| E-01 | target 风格 list `path_map` | 成功；`nodes` / `edges` / `branches` 与 spec 预期一致 |
| E-02 | dict `path_map` | 成功；`ends` 逐字等于用户 dict |
| E-03 | `path_map` 为 tuple（路由函数返回注解**不含** `Literal`） | 接受；`ends = None`（静默降级；有 `Literal` 时反而推断） |
| E-04 | `path_map=None` + `Literal` 返回注解 | 成功；`ends` 展开为 `{'a':'a','__end__':'__end__'}` |
| E-05 | 重复节点名 | `ValueError: Node \`a\` already present.` |
| E-06 | 单源边指向未知节点 | `ValueError: Found edge ending at unknown node \`missing\`` |
| E-07 | 缺少 `START` 入口 | `ValueError: Graph must have an entrypoint: ...` |
| E-08 | `add_edge` 链式 | 返回同一 builder |
| E-09 | 空多源 source | 接受；`waiting_edges = {((), 'a')}` |
| E-10 | 缺 `action` | `RuntimeError` |
| E-11 | 单 callable + action | 接受；action 被静默忽略 |
| E-12 | 节点名含 `:` | `ValueError: ':' is a reserved character ...` |
| E-13 | 多源边 `add_edge(['a','b'],'c')` | 接受；`waiting_edges = {(('a','b'), 'c')}` |
| E-14 | `validate(interrupt=['nope'])` | `ValueError: Interrupt node \`nope\` not found` |
| E-15 | `add_edge('a', 123)` | 接受（不校验 `end_key` 类型） |
| E-16 | `add_conditional_edges(123, router, ['a'])` | 接受（`source` 非 str 直接作为 `branches` 键） |
| E-17 | `path_map=['a', 3]` / `{'x': 3}` | 接受（不校验元素 / value 类型） |
| E-18 | `add_node(START, fn)` / `add_node(END, fn)` | 均 `ValueError: Node ... is reserved.` |
| E-19 | `add_edge(END, "a")` / `add_edge("a", START)` | `ValueError: END cannot be a start node` / `START cannot be an end node` |
| E-20 | 空节点 + `add_edge(START, END)` + `validate()` | 接受；`validate()` 通过 |
| E-21 | 普通 callable 仅有 `.name`、无 `__name__` | `add_node` 取名类型名（`.name` 不参与）；branch 名 `condition` |
| E-22 | `add_edge(123, "a")` 非法 `start_key` | `TypeError: 'int' object is not iterable` |
| E-23 | 非 callable `Runnable` 作为 `path` | 接受并使用 `.name`（RunnableLambda 实测） |
| E-24 | `add_node("a", fn, alias="model")` | **接受**并经 `**kwargs`（`DeprecatedKwargs`）静默忽略 `alias`；无 alias 语义 |

> 探针只做构建 / `validate()`，不执行节点；与 B6F1 同域。换版本 MUST 重跑并重判。

---

## §3 差分场景（D-50…D-74）

> 落点：`tests/differential/parity_probe.py` 的 **builder-only** 场景模型 +
> `tests/differential/test_parity_probe.py` 的包装测试。
> 上游缺席 ⇒ **skip**，不判失败。

| # | 场景 | 断言 | 判词 |
|---|---|---|---|
| D-50 | target 风格建图（2 节点 + START 边 + list `path_map` + 回边） | 两侧 `validate()` 均成功；节点名 / 边数一致 | SAME |
| D-51 | dict 形态 `path_map` | 两侧成功；归一化映射一致 | SAME |
| D-52 | 重复节点名 | 两侧均 `ValueError`；消息含重复名 | SAME |
| D-53 | 静态边指向不存在的节点（先建立有效 `START` 入口） | 两侧 `validate()` 均 `ValueError`；freegraph 消息含目标名 | SAME |
| D-54 | 缺少 `START` 入口 | 两侧 `validate()` 均 `ValueError`；消息含 `entrypoint` / `START` | SAME |
| D-55 | 链式 `add_edge(...).add_edge(...)` | 两侧均成功且返回同一 builder | SAME |
| D-56 | `path_map` 为 tuple（路由函数返回注解**不含** `Literal`） | 上游静默接受并保持 `ends=None`；freegraph 立即 `TypeError` | STRICTER（X-2） |
| D-57 | 多源边 `add_edge(["a","b"], "c")` | 两侧均接受；freegraph 记录元组键 | SAME |
| D-58 | `add_node("a")` 缺 `action` | 两侧均失败；上游 `RuntimeError`，freegraph `TypeError` | STRICTER（X-4） |
| D-59 | `add_edge([], "a")` 空多源 source | 上游接受；freegraph 立即 `ValueError` | STRICTER（X-2） |
| D-60 | `path_map=None` + `Literal[...]` 返回注解 | 两侧推断出的目标集合一致 | SAME |
| D-61 | `validate(interrupt=["nope"])` 未知节点 | 两侧均 `ValueError`；freegraph 消息含 `nope` | SAME |
| D-62 | `add_edge("a", 123)` 单源 `end_key` 非 `str` | 上游接受；freegraph 立即 `TypeError` | STRICTER（X-2） |
| D-63 | `add_conditional_edges(123, router, ["a"])` `source` 非 `str` | 上游接受并把错误推迟到 `validate()`；freegraph 立即 `TypeError` | STRICTER（X-2） |
| D-64 | `path_map=["a", 3]` / `{"x": 3}` 元素或 value 非 `str` | 上游接受；freegraph 立即 `TypeError` | STRICTER（X-2） |
| D-65 | 多源边 `add_edge(["a","b"], END)` | 构建期两侧均接受并记录；freegraph 保留元组键的 `END` 目标 | SAME（构建期；下游 V-16 属 B7F4 的 STRICTER · D-1） |
| D-66 | `add_node(fn, fn2)` 单 callable + action | 上游接受并静默忽略 action；freegraph 立即 `TypeError` | STRICTER（X-4 · E-11） |
| D-67 | `add_node(START, fn)` / `add_node(END, fn)` | 两侧均 `ValueError`；消息含 `reserved` | SAME（P-03 · E-18） |
| D-68 | `add_edge(END, "a")` / `add_edge("a", START)` | 两侧均 `ValueError` | SAME（P-05 · E-19） |
| D-69 | `add_edge(123, "a")` 非法 `start_key` | 两侧均 `TypeError` | SAME（E-22） |
| D-70 | 普通 callable 仅有 `.name`、无 `__name__` 时取名 | 两侧均忽略 `.name`：节点名取类型名、分支名取 `condition` | SAME（P-02c / P-08 · E-21） |
| D-71 | 缺入口 + 未知目标 | 两侧均先报入口错误（消息含 `entrypoint` / `START`） | SAME（P-09 顺序） |
| D-72 | 空节点 + `START -> END` | 上游通过；freegraph `ValueError` | STRICTER（X-5 · E-20） |
| D-73 | 非 callable `Runnable` 作为 `path` | 上游接受；freegraph 立即 `TypeError` | DIFF（X-6 · E-23） |
| D-74 | `add_node(..., alias="model")` | 两侧均接受；上游静默忽略 `alias`，freegraph 记录到 `_NodeRecord.alias` | DIFF（X-1 · E-24） |

---

## §4 偏离登记（X-1…X-7）

| # | 类别 | 被偏离的判据 | 理由 | 承接 / 追认 |
|---|---|---|---|---|
| X-1 | 必须自研区（上游没有） | `add_node(..., alias=...)` | C25 / B8F3 的节点别名是 freegraph 自有增量；上游签名无 `alias`，运行时经 `**kwargs` 静默忽略（E-24） | B8F3 · 本 feature 只记录 · D-74 |
| X-2 | 更严失败信号 | `path_map` 非 list / dict / None ⇒ `TypeError`；list 元素 / dict value 非 `str` ⇒ `TypeError`；条件边 `source` 非 `str`、单源边 `end_key` 非 `str` ⇒ `TypeError`；空多源列表 ⇒ `ValueError` | 上游对非 dict/list 的 `path_map` 不报错（无 Literal ⇒ None；有 Literal 则推断）；对非 str 的 source / end_key / path_map 元素静默接受并把错误推迟到 `validate()` / `compile()` | 本 feature 内闭合 · Q12 发起者确认选项 A（含同类非法输入） · D-56 / D-59 / D-62 / D-63 / D-64 |
| X-3 | 形态优化（原则 XII） | 私有 `_build_spec() -> _BuilderSpec` | 上游 `compile()` 直接读自身字段（`state.py:1242-1247` / `:1374-1399`）；L3 构建器与 L2 运行时物理分层 ⇒ 冻结内部规格是「形态最优」而非「上游缺失能力」；Q10 发起者确认 | B7F2（B8F1 经 L2）· spec D-1 / D-2 |
| X-4 | 更严失败信号 | 缺 `action` / 单 callable 同时传 `action` ⇒ `TypeError` | 上游 `RuntimeError` / 静默忽略；freegraph 统一明确拒绝 | 本 feature 内闭合 · Q12 发起者确认选项 A · D-58 / D-66 |
| X-5 | 更严失败信号 | 空节点表 ⇒ `ValueError` | 上游 `START -> END` 空图可通过 `validate()`；freegraph 的 L2 `GraphSpec` V-3 要求节点表非空，且空图无可执行语义 ⇒ 提前显式失败 | 本 feature 内闭合 · D-72 · E-20 |
| X-6 | 必须自研区（零依赖 duck-typing 边界） | 非 callable `Runnable` / Runnable-like 对象 | freegraph MUST NOT import langchain / langchain-core；只接受普通 callable。上游对 Runnable 的 `.get_name()` / `.name` 取值不承载 | 本 feature 内登记 · D-73 · E-23 |
| X-7 | 结构差异（DIFF · 已知不支持） | `defer=True` 目标的路由通道类型：freegraph 用 `EphemeralValue`；上游用 `LastValueAfterFinish` | defer 节点屏障不在 v1 本 feature 实现（B7F4 X-03 同源）；只接受并记录 `defer=True`，不改变路由通道类型 | 本 feature 只记录 · B7F4 X-03 在 defer 落地时一并处理 |

---

## §5 换版本复核清单

1. 复核 §1 全部行号；
2. 重跑 E-01…E-24；
3. 重判 D-50…D-74 的三态；
4. 复核 `path_map` 的 list / dict / None 接受形态（含非 dict/list 时的 `Literal` 推断差异）；
5. 复核 `add_node` 的单 callable / 缺 action / 多传 action / `.name` 不参与取名 / `alias` 经 `**kwargs` 忽略；
6. 复核 `validate()` 的「源 → 入口 → 目标」顺序与空图接受行为；
7. 复核保留字符集合（当前 `|` / `:`）。
