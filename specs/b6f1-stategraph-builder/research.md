> **2026-11-20 后续修订（C25 正式作废）**：`add_node` 不再接受 `alias`，`_NodeRecord` 不再含 `alias`。本文件中 alias 记录文字保留为历史。
> 差分场景 **D-74** 已迁移到 **B8F3 D-142**，`parity_probe.py` 不再承载；本文件中的 `D-50…D-74` 为历史范围。

# 研究与技术决策（B6F1 · `StateGraph` 构建器）

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-11-15
**上游版本**: `langgraph` **1.2.11**
**取证环境**: `/home/ctyun/workspace/github/freegraph/.venv/lib/python3.11/site-packages/langgraph`

> **原则 XI**：上游是唯一权威。每条行为断言带版本 + `路径:行号`；行为断言有实测支撑。
> 本文件是 plan 的设计底稿；语义冲突时以 `spec.md` 为准。

---

## 1. 上游实测取证（E-01…E-24）

> 探针只用 `StateGraph` 的构建 / `validate()`，不执行节点；与 B6F1 的判据同域。
> 结果按 1.2.11 实测记录；换版本 MUST 重跑并重判。

| # | 场景 | 上游实测结果 | 与 freegraph 的关系 |
|---|---|---|---|
| **E-01** | target 风格：2 节点 + `START` 边 + list `path_map` + 回边 | 成功；`nodes = ['llm_call','tool_node']`；`edges` 含 `('__start__','llm_call')` / `('tool_node','llm_call')`；`branches['llm_call']['should_continue'] = {'tool_node':'tool_node','__end__':'__end__'}` | SAME；`D-50` |
| **E-02** | dict `path_map = {'hit':'hit','miss':'miss'}` | 成功；lambda 分支名 `condition`；`ends` 逐字等于用户 dict | SAME；`D-51` |
| **E-03** | `path_map` 为 tuple `('a',)`（路由函数返回注解**不含** `Literal`） | **接受**；`ends = None`（不报错，静默降级） | STRICTER；freegraph 立即 `TypeError`；`D-56` / `X-2`。⚠️ 若返回注解含 `Literal`，上游反而按注解推断目标集合 |
| **E-04** | `path_map=None` 且 `path` 返回注解为 `Literal['a','__end__']` | 成功；`ends = {'a':'a','__end__':'__end__'}` | SAME；freegraph 照抄推断；`D-60` |
| **E-05** | 重复节点名 | `ValueError: Node \`a\` already present.` | SAME；`D-52` |
| **E-06** | 单源边指向不存在节点（随后 `validate()`） | `ValueError: Found edge ending at unknown node \`missing\`` | SAME；`D-53` |
| **E-07** | 没有任何 `START` 入口，随后 `validate()` | `ValueError: Graph must have an entrypoint: add at least one edge from START to another node` | SAME；`D-54` |
| **E-08** | `add_edge(START,'a')` 返回值 | 返回同一个 builder（`is` 为真） | SAME；`D-55` |
| **E-09** | 空多源 source：`add_edge([], 'a')` | **接受**；`waiting_edges = {((), 'a')}`（静默登记无效汇合） | STRICTER；freegraph 立即 `ValueError`；`D-59` / `X-2` |
| **E-10** | `add_node('a')` 缺 `action` | `RuntimeError`（无消息） | STRICTER；freegraph 用 `TypeError`；`D-58` / `X-4` |
| **E-11** | `add_node(fn, fn2)`（单 callable 形态同时传 action） | **接受**；节点名为 `fn.__name__`，`action` 被静默忽略 | STRICTER；freegraph 拒绝多传 `action`；`X-4` |
| **E-12** | 节点名含 `':'` | `ValueError: ':' is a reserved character and is not allowed in the node names.` | SAME |
| **E-13** | 多源边 `add_edge(['a','b'], 'c')` | **接受**；`waiting_edges = {(('a','b'), 'c')}` | SAME；`D-57` |
| **E-14** | `validate(interrupt=['nope'])` | `ValueError: Interrupt node \`nope\` not found` | SAME；`D-61` |
| **E-15** | `add_edge('a', 123)` | 接受（不校验 `end_key` 类型） | STRICTER；`D-62` / `X-2` |
| **E-16** | `add_conditional_edges(123, router, ['a'])` | 接受（`source` 非 str 直接作为 `branches` 键） | STRICTER；`D-63` / `X-2` |
| **E-17** | `path_map=['a', 3]` / `{'x': 3}` | 接受（不校验元素 / value 类型） | STRICTER；`D-64` / `X-2` |
| **E-18** | `add_node(START, fn)` / `add_node(END, fn)` | 均 `ValueError: Node ... is reserved.` | SAME；`D-67` / `P-03` |
| **E-19** | `add_edge(END, "a")` / `add_edge("a", START)` | `ValueError: END cannot be a start node` / `START cannot be an end node` | SAME；`D-68` / `P-05` |
| **E-20** | 空节点 + `add_edge(START, END)` + `validate()` | 上游接受；freegraph 计划 `ValueError` | STRICTER；`X-5`；`D-72` / `P-14` |
| **E-21** | 普通 callable 仅有 `.name`、无 `__name__` | `add_node` 取名**类型名**（`.name` 不参与）；branch 名 `condition` | SAME；`D-70` / `P-02c` / `P-08` |
| **E-22** | `add_edge(123, "a")` 非法 `start_key` | `TypeError: 'int' object is not iterable` | SAME（异常类型）；`D-69` |
| **E-23** | 非 callable `Runnable` 作为 `path` | 上游接受并使用 `.name`（RunnableLambda 实测） | DIFF；`X-6`；`D-73` / `P-06c` |
| **E-24** | `add_node("a", fn, alias="model")` | 上游**接受**并经 `**kwargs`（`DeprecatedKwargs`）**静默忽略** `alias`；无 alias 语义 | C25 作废后 freegraph 抛 `TypeError` ⇒ **STRICTER**；`X-3`；`D-74` / `P-02b` |

### 1.1 实测脚本要点

探针不入库（研究期一次性脚本），但结论必须可复现：

```text
.venv/bin/python - <<'PY'
from typing import Literal, TypedDict
from langgraph.graph import StateGraph, START, END
...
PY
```

复核时 MUST 重新跑 E-01…E-24；上游换版本时 MUST 重判 `D-50…D-74`。

---

## 2. 上游源码锚点（版本 + 路径:行号）

| 语义点 | 锚点 |
|---|---|
| `StateGraph` 类 | `langgraph/graph/state.py:131` |
| 构造签名 | `langgraph/graph/state.py:216-225` |
| `add_node` 签名 | `langgraph/graph/state.py:667-682`（含 `**kwargs: Unpack[DeprecatedKwargs]`；alias 实测 E-24） |
| 单 callable 取名 | `langgraph/graph/state.py:778-799`（实测 E-21） |
| `coerce_to_runnable` 的 TypeError | `langgraph/_internal/_runnable.py:579`（非法 action / node 类型） |
| 重复 / 保留节点名 | `langgraph/graph/state.py:802-805`（实测 E-18） |
| 保留字符 `\|` / `:` | `langgraph/graph/state.py:807-811` · `langgraph/_internal/_constants.py:87-89` |
| `add_edge` 签名 | `langgraph/graph/state.py:928` |
| 单源边 / 多源边 | `langgraph/graph/state.py:951-979`（哨兵实测 E-19；非法 `start_key` 实测 E-22） |
| `add_conditional_edges` 签名 | `langgraph/graph/state.py:982-989` · `:1018-1019`（Runnable 实测 E-23） |
| 同名分支重复 / 分支名推断 | `langgraph/graph/state.py:1022-1025` · `langgraph/_internal/_runnable.py:313-319`（实测 E-21） |
| `BranchSpec.from_path` | `langgraph/graph/_branch.py:89-120` |
| `path_map` list / dict 归一化 | `langgraph/graph/_branch.py:96-101` |
| `path_map=None` 的 `Literal` 推断 | `langgraph/graph/_branch.py:102-114` |
| `validate` 入口 / 源与目标 / `interrupt` 节点校验 | `langgraph/graph/state.py:1129-1175`（`interrupt` 见 `:1168-1174`） |
| `compile()` 读取自身 `nodes` / `edges` / `branches` | `langgraph/graph/state.py:1242-1247` · `:1374-1399` |
| 路由通道 `branch:to:<key>` | `langgraph/graph/state.py:98` · `:1525-1530` |

---

## 3. 设计决策（DR-1…DR-15）

### DR-1 · schema 解析推迟到构建期末

- **Decision**：`StateGraph.__init__` 只保存 `state_schema`（以及已冻结的可选参数占位），
  不调用 `parse_state_schema`；解析在 `validate()` / `_build_spec()` 执行。
- **Rationale**：B2F2 FR-007 冻结「构造 MUST 成功、MUST NOT 抛异常」；schema 内容错误属构建期。
- **Alternatives**：构造期解析（违反 B2F2）；每次 `add_*` 都解析（慢且无必要）。

### DR-2 · 构建器内部状态容器

- **Decision**：`_nodes: dict[str, _NodeRecord]` · `_edges: dict[str | tuple[str, ...], list[str]]`
  · `_conditional_edges: list[_ConditionalEdgeDraft]` · `_branch_names: dict[str, set[str]]`。
- **Rationale**：`dict` / `list` 保序；边在构建期用 `list` 累积、snapshot 时冻结为 `tuple`。
- **Alternatives**：直接用不可变结构（每次 `add_*` 复制，成本高且无收益）。

### DR-3 · 节点记录与单 callable 形态

- **Decision（历史）**：`_NodeRecord(name, action, alias, defer, metadata)`；**C25 已正式作废，当前 `_NodeRecord` 无 `alias`。** `add_node(fn)` 用
  `fn.__name__`，无 `__name__` 时用类型名（普通 callable 的 `.name` **不参与**）；重复 /
  保留名 / 保留字符立即失败。非 callable `Runnable` 不承载（X-6）。
- **Rationale**：与上游 `state.py:778-811` 同款（实测 E-21/E-23）；**C25 已于 2026-11-20 正式作废**，freegraph 不再接受 `alias`；上游签名无 `alias`，运行时经 `**kwargs` 静默忽略（实测 E-24）。
- **Alternatives**：只允许 `(str, Callable)`（不兼容上游单 callable 形态）；按 `.name`
  取名（与上游普通 callable 行为不一致）。

### DR-4 · 静态边归一化与幂等

- **Decision**：单源键保持 `str`；多源键为保序去重后的 `tuple[str, ...]`；目标按首次出现
  顺序累积；完全相同的 `(source, target)` 重复登记幂等；非法 `start_key` / `end_key`
  类型 ⇒ 立即 `TypeError`。
- **Rationale**：与 B7F1 `GraphSpec.edges` 同构；与上游 `set` 去重语义同款；B7F4 要求元组键；
  上游对非法 `start_key` 也是同类 `TypeError`（E-22）。
- **Alternatives**：每次 `add_edge` 立即构造 `tuple`（可读但频繁复制）；不去重（运行期
  重复触发风险）。

### DR-5 · 条件边草稿与分支名

- **Decision**：`_ConditionalEdgeDraft(source, path, path_map, branch_name)`；分支名取
  `path.__name__`，但当无 `__name__` 或为 `<lambda>` 时取 `"condition"`（普通 callable 的
  `.name` **不参与**；上游 `_runnable.py:313-319` 同款 · 实测 E-21）；同一 source 同名分支
  立即 `ValueError`。非 callable Runnable 不承载（X-6 · E-23）。
- **Rationale**：上游 `state.py:1022-1025` 同款；分支名是「同一源上多条条件边」的消歧键。
- **Alternatives**：允许同名分支（会导致 B8F1 无法区分，且上游拒绝）；按 `.name` 取名
  （与上游普通 callable 行为不一致）。

### DR-6 · `path_map` 归一化与 `Literal` 推断

- **Decision**：list → `{name: name}`；dict 浅拷贝；`None` 时尝试
  `typing.get_type_hints(path).get("return")`，仅当 `get_origin(...) is Literal` 时展开为
  `{name: name}`；任何异常 / 非 `Literal` ⇒ 保持 `None`，不报错；此时
  `targets=()` / `route_channels=()`，B7F2 原样保留 `None` 供 B8F1 动态求值。
- **Rationale**：直接复制 `_branch.py:96-114`；差分为 `D-51` / `D-56` / `D-60`；
  非法元素 / value 类型更严（`D-64`）。
- **Alternatives**：不推断（偏离上游）；推断失败报错（上游静默忽略，会破坏合法图）；
  把空目标等价为 `END`（会误终止）。

### DR-7 · 两层校验与顺序

- **Decision**：
  1. **立即层**：节点重复 / 保留名 / 保留字符；`END` 作边源；`START` 作边目标；多源边源
     不存在 / 空源；`start_key` / 单源边 `end_key` 非法类型；条件边 `source` 非 `str`；
     `path_map` 类型 / 元素 / value 非法；同名分支重复。
  2. **构建期末层**（`validate()` / `_build_spec()`，顺序固定）：
     schema 非法 → **源存在性** → **入口存在性** → **目标存在性** → **空节点表**（X-5）。
     该顺序与上游 `validate()` 的「源 → 入口 → 目标」一致；空节点表为本项目更严项。
  3. **`validate(interrupt=...)`**：按上游校验每个名字是已登记节点（未知 ⇒ `ValueError`，
     BV-13）；`_build_spec()` 本身不接收 `interrupt`。
- **Rationale**：spec FR-006 要求构建期早失败；上游 `validate()` 也是构建 / 编译期；
  多故障同时存在时的优先级必须与上游一致（E-07 / E-20）。
- **Alternatives**：全部立即（拒绝合法前向引用）；全部推迟到 compile（违反早失败）；
  目标先于入口（与上游失败优先级不一致）。

### DR-8 · `_build_spec` 的快照顺序

- **Decision**：`_build_spec` 的无副作用顺序为：
  1. `parse_state_schema(self._schema)` → `SchemaSpec`
  2. **源存在性**校验（静态边源 / 条件边源，`START` 除外）
  3. **入口存在性**校验（静态边或条件边 source == `START`）
  4. **目标存在性**校验（静态边 / 条件边目标，`END` 除外）
  5. **空节点表**校验（X-5；放在最后以保持与上游多故障优先级一致）
  6. `build_channels(schema_spec)` → 状态通道
  7. 创建路由通道
  8. 组装 `_NodeRecord` / `NodeSpec` / `edges` / `_ConditionalEdgeSpec`
- **Rationale**：先完成所有会失败的校验，再创建通道，避免失败时产生部分快照；构建器状态不被
  修改 ⇒ 失败后状态不变（FR-019）；顺序与上游 `validate()` 的「源 → 入口 → 目标」一致。
- **Alternatives**：边校验边建通道（失败时留下局部对象，虽然可丢弃但更难审计）；
  空节点表先于入口（与上游失败优先级不一致）。

### DR-9 · `targets` 与 `route_channels` 的语义

- **Decision**：`_ConditionalEdgeSpec.branch` = `_branch_name(path)` 的登记结果（同一
  `source` 上唯一）；`targets` = 归一化 `path_map` 的**全部唯一 values**，**含 `END`**，
  顺序 = 首次出现；`route_channels` = 其中**非 `END`** 目标的 `branch:to:<target>`，
  同序、去重。
- **Rationale**：B7F2 翻译为 L2 映射时需要保留 `END` 作为合法分支目标，B8F1 才能从
  `GraphSpec.conditional_edges` 读到终止信息；但 `END` 不需要路由通道。`branch` 是上游
  `branches` 的键，必须在快照中携带，B7F2 才能机械翻译而不重算。
- **跨层形状**：B7F2 MUST 把 `_ConditionalEdgeSpec` 机械翻译为纯内建类型
  `dict[str, tuple[dict[str, Any], ...]]`（内层 `{"branch": str, "path": Callable,
  "path_map": dict[Hashable, str] | None, "targets": tuple[str, ...],
  "route_channels": tuple[str, ...]}`；`branch` 取自 `_ConditionalEdgeSpec.branch`）并存放
  在 `CompiledGraph` 私有字段；形状以 spec D-2 为准。
- **Alternatives**：`targets` 排除 `END`（B8F1 会丢终止信息）；`route_channels` 含 `END`
  （会创建永不写入的通道）。

### DR-10 · 路由通道的形状

- **Decision**：`EphemeralValue(key="branch:to:<target>", value_type=Any, guard=False)`；
  放入 `_BuilderSpec.channels`；同一目标只建一次。`defer=True` 目标也统一用
  `EphemeralValue`；上游 `LastValueAfterFinish` 的差异登记为 **X-7**（已知不支持），由 **B7F4 X-03** 在 defer 落地时一并处理。
- **Rationale**：上游 `state.py:1525-1530` 同款（`EphemeralValue(Any, guard=False)`）；
  `guard=False` 允许一步内多写取末值。
- **Alternatives**：`guard=True`（多源路由同轮会抛 `InvalidChannelUpdateError`，偏离上游）；
  单独字段存放（B7F2 需二次合并，spec Q11 已否决）。

### DR-11 · 节点订阅集

- **Decision**：`NodeSpec.subscribes = tuple(状态通道 keys)`（顺序 = schema 声明顺序）；
  不含路由通道；不实现上游窄 `input_schema` 推断。
- **Rationale**：B2F2 冻结的 `add_node` 签名没有 `input_schema`；`target.py` 的节点首参为
  完整 `MessagesState`，订阅全部状态通道与上游结果一致。窄 `input_schema` 已登记为
  Out of Scope。
- **Alternatives**：自动从首参类型推断并解析输入 schema（超出本 feature 范围，且需要新增
  通道来源）。

### DR-12 · 快照的不可变性与结构等价

- **Decision**：`_build_spec` 每次返回新副本；`_BuilderSpec` 是冻结 dataclass，但内部 dict
  由构建器独占（调用方约定不修改）；两次快照按「通道类型 / 归约器 / key + 节点 / 边 / 分支
  字段」判结构等价，不按通道对象身份。
- **Rationale**：B5F1 / B7F1 的通道不实现值相等；对象身份比较会产生假红。
- **Alternatives**：缓存同一批通道对象（调用方可能修改，污染后续 compile）；实现
  `Channel.__eq__`（破 B5F1 冻结面）。

### DR-13 · 不执行用户代码

- **Decision**：`add_node` 只存 `action`；`add_conditional_edges` 只存 `path`；`validate` /
  `_build_spec` 都不调用它们；`validate(interrupt=...)` 只检查名字是否在节点表（不调用
  节点）；不检查返回注解（`Literal` 推断只看注解，不调用函数）。
- **Rationale**：spec FR-008 / FR-009 / 裁定 10；构建与执行职责分离。
- **Alternatives**：构建期试跑节点（副作用不可控，且违反 spec）。

### DR-14 · 测试与差分

- **Decision**：
  - 新增 `tests/facade/test_stategraph_builder.py` / `test_stategraph_validation.py` /
    `test_stategraph_spec.py` / `_builder_support.py`；
  - 修改 `tests/facade/test_facade.py` 的 `TestNotWired`，只保留 `compile()` 与其余未交付
    方法的未接线断言；
  - 在 `parity_probe.py` 内新增 **builder-only** 场景模型（不复用 runtime 场景，不改既有
    30+ 场景；场景名含 `builder` 前缀，便于 `-k builder`），`test_parity_probe.py` 新增对应包装。
- **Rationale**：构建器差分不执行节点，不能塞进现有 `Scenario` 的 runtime 管线；并列模型
  可以保持既有判据零改动。
- **Alternatives**：硬塞进现有 `Scenario`（需要大量可选字段和分支，风险高）。

### DR-15 · 文档与验收

- **Decision**：README 的 `StateGraph` 行只做事实性措辞更新；新增 B6F1 acceptance + manual；
  `graph_core.py` 不改（compile 仍桩，继续退出码 2）。
- **Rationale**：`graph_core.py` 的端到端真跑属 B7F2 / B7F3；本 feature 不伪造通过。
- **Alternatives**：提前改 `graph_core.py` 为硬断言（会产生永久红 CI）。

---

## 4. 实现落点（逐函数 / 逐类）

| 落点 | 内容 |
|---|---|
| `StateGraph.__init__` | 保存 `_schema`；初始化 `_nodes` / `_edges` / `_conditional_edges` / `_branch_names` |
| `StateGraph.add_node` | 单 callable / str+action 形态；立即校验；记录 `_NodeRecord` |
| `StateGraph.add_edge` | `str` / `list` / `tuple` 源；立即校验；聚合边表 |
| `StateGraph.add_conditional_edges` | source / path / `path_map` 校验；归一化；分支名去重；记录草稿 |
| `StateGraph.validate` | 调 `_build_spec()`；返回 `self`；`interrupt` 按上游校验节点存在性（BV-13） |
| `StateGraph._build_spec` | 校验顺序 + schema / 通道 / 节点 / 边 / 分支 / 路由通道 / 快照 |
| `_BuilderSpec` | 冻结 dataclass：`channels` / `nodes` / `node_records` / `edges` / `conditional_edges` |
| `_NodeRecord` | 冻结 dataclass：`name` / `action` / `defer` / `metadata`（C25 作废后无 `alias`） |
| `_ConditionalEdgeSpec` | 冻结 dataclass：`source` / `branch` / `path` / `path_map` / `targets` / `route_channels` |
| `_ConditionalEdgeDraft` | 构建期草稿：`source` / `path` / `path_map` / `branch_name` |

### 4.1 零改动清单

- `src/freegraph/runtime/**`（B7F1 / B4F1 / B5F1）。
- `src/freegraph/contracts/**`。
- `src/freegraph/graph.py` 的导出语句与 `__all__`。
- `tests/facade/test_api_snapshot.py`。
- `harness/demo/target.py`。
- `harness/scripts/gates/**`。

---

## 5. 待核对项 / 已知边界

| # | 项 | 处置 |
|---|---|---|
| **O-1** | 路由通道 `branch:to:<target>` 与用户 schema key 同名 | 复制上游覆盖行为（`state.py:1525-1530`）；在 data-model / 人工验证记录中登记为已知边界；不新增 spec 判据 |
| **O-2** | 上游窄 `input_schema` 自动推断 | 明确 Out of Scope；`NodeSpec.subscribes` = 全部状态通道 |
| **O-3** | `path_map` 的 `Literal` 推断对可调用对象实例的支持 | 先按 `typing.get_type_hints(path)` 尝试；异常 / 取不到 ⇒ 保持 `None`，与上游 `try/except` 同款 |
| **O-4** | `_BuilderSpec` 的结构等价判定 | 测试侧辅助函数；不要求 `Channel.__eq__` |
| **O-5** | 门禁 3 / 4 / 5 的端到端部分 | EV-1a / EV-1b / EV-1c 具名承接 B25F1；本 feature 不写永久红断言 |
| **O-6** | 非 callable `Runnable` / Runnable-like 对象 | 明确不承载（X-6）；只接受普通 callable；差分 D-73 |
| **O-7** | 空节点表 / `START -> END` 空图 | freegraph 比上游更严（X-5）；上游接受（E-20）；差分 D-72 |
| **O-8** | `defer=True` 目标的路由通道类型 | B6F1 不实现 defer 屏障，统一用 `EphemeralValue`；上游用 `LastValueAfterFinish` ⇒ 登记 **X-7**（已知不支持），由 **B7F4 X-03** 在 defer 落地时一并处理；P-13 限为「非 defer SAME」 |
| **O-9** | B9F1 的 `__parent__` 保留名检查 / B7F4 的 **V-16** 校验落点 | B6F1 不提前校验；`__parent__` / 多源 `END` / 多源目标数 ≠ 1 由 **B7F2** 构造 `GraphSpec` 时最终失败（H-2 的「语义一致」仅限 V-1 / V-2 / V-3） |

---

## 6. 换版本复核清单

1. 重跑 E-01…E-24；
2. 复核 §2 全部行号；
3. 重判 D-50…D-74 的三态；
4. 复核 `path_map` 的 list / dict / None 接受形态（含非 dict/list 时的 `Literal` 推断差异）；
5. 复核 `add_node` 的单 callable / 缺 action / 多传 action / `.name` 不参与取名 / `alias` 已被 C25 正式作废（拒绝形态）；
6. 复核 `validate(interrupt=...)` 的未知节点行为；
7. 复核 `validate()` 的「源 → 入口 → 目标」顺序与空图接受行为；
8. 复核保留字符集合（当前 `|` / `:`）。
