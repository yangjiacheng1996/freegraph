# 上游对照：B8F3 · context 通道与 alias 移除

**Feature**: `B8F3` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**上游版本**: `langgraph` **1.2.11** · `langchain-core` **1.7.6**（取证于 2026-11-20）
**证据**: [research.md](../research.md) §2（E-01…E-05）· `.venv` 实测

---

## §1 逐条对照（P-01…P-11）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | `add_node` 的关键字面 | `langgraph/graph/state.py:667-682`（无 `alias`） | alias 移除后，freegraph 的 `add_node` 也**无 `alias`** | SAME | 与上游一致 |
| P-02 | 传入 `alias=` 的失败信号 | 上游经 `**kwargs: Unpack[DeprecatedKwargs]` **静默忽略**（E-01） | `add_node(alias=...)` ⇒ **`TypeError`** | STRICTER | 避免「可传但没用」的误导 ⇒ **X-3** |
| P-03 | 运行时 `context` 的载体 | `langgraph/pregel/main.py:3783-3843`（`invoke(..., context=...)`）· `langgraph/runtime.py:198`（`Runtime.context`）· 文档 `harness/docs/oss/python/langgraph/graph-api.md:999-1035` | `RunConfig.context`（C22）+ 节点侧 `state.context` 属性 | DIFF | 上游 `context=` + `Runtime`；freegraph 自有 `RunConfig` + 已冻结的节点形态 ⇒ **X-1** |
| P-04 | `context` 不进入状态 | 实测 **E-02 / E-05**（`state` 键集无 `context`） | `context` 不进状态 / 归约 / `invoke` 终态 / `values` 载荷 | SAME | 只比「状态中无 context」 |
| P-05 | `context` 与 `configurable` 分离 | 上游 `context` 是独立参数，**不**要求塞进 `configurable`（`main.py:3783-3843`；文档 `graph-api.md:1012-1035`） | `RunConfig.context` 独立；`configurable` 不承载 context | SAME | 二者都拒绝「context 塞 configurable」 |
| P-06 | `RunConfig` vs `RunnableConfig` | 上游 `RunnableConfig` 含 `configurable` / `metadata` / `tags` 等（`langchain_core/runnables/config.py` 一族） | freegraph 自有 `RunConfig`（九字段，含四核心 C22 字段） | DIFF | C22 已冻结；freegraph 不复用 `RunnableConfig`（避免拖回 `langchain-core`）⇒ **X-2** |
| P-07 | `path_map` 查表用节点名 | `langgraph/graph/_branch.py:199-211`（按返回目的地解析；不解析别名） | `path_map` 查表用**内部节点名**；alias 已移除 | SAME | H-2；无别名解析 |
| P-08 | 路由函数看到的状态 | 实测 **E-05**（路由函数入参无 `context`） | 路由函数 fresh 视图无 `context`；第二参 `config` 可携带 | SAME | H-2；C8 fresh 读不变 |
| P-09 | `updates` 流事件的载荷键 | `langgraph/pregel/_io.py:118`· 实测 **E-03**（键 = 内部节点名） | `updates` 键 = 内部节点名 | SAME | alias 已移除；B8F2 口径不变 |
| P-10 | 图导出的节点名 | `langgraph/graph/state.py:1356-1374`· 实测 **E-04**（`Node.id` / `name` = 内部名） | `get_graph()` / `draw_mermaid` = 内部节点名 | SAME | alias 已移除；B22F1 口径不变 |
| P-11 | 零依赖 / 零环境变量 / 零出站 | 本 feature 不引入任何第三方依赖，不读环境变量 | 同宪法原则 I / II | SAME | 红线不变 |

---

## §2 实测基线（E-01…E-05）

| # | 实验 | 结果 | 结论 |
|---|---|---|---|
| E-01 | `add_node("agent", fn, alias="model")` | 上游接受但静默忽略；图仍以 `agent` 登记 | alias 是自研增量；移除后 freegraph `TypeError`（X-3） |
| E-02 | `invoke(..., context={"user":"u1"})`，节点 `(state, runtime)` | `runtime.context` 读到；`state` 无 `context` | context 独立通道（X-1） |
| E-03 | `stream(..., stream_mode="updates")` | 载荷键 = `agent` | 内部节点名；alias 不参与 |
| E-04 | `get_graph()` / `draw_mermaid()` | 节点 `id` / `name` = `agent`；无 `model` | 图导出内部节点名 |
| E-05 | 条件边路由函数 | 入参无 `context`；只能经 `Runtime` 取 | fresh 视图无 context |

---

## §3 差分场景组（D-137…D-144）

| # | 场景 | 断言 | 判词 |
|---|---|---|---|
| D-137 | `context` 不进入 `invoke` 终态 | 两侧最终状态键集都不含 `context`；状态值逐字相等 | SAME |
| D-138 | 节点读取 `context` 的值 | 上游 `Runtime.context` / freegraph `state.context` 读到同一个值 | DIFF（X-1，仅访问形态） |
| D-139 | `context` 不塞进 `configurable` | 两侧都不要求 / 不产生 `configurable.context`；freegraph 的 `configurable` 保持独立 | SAME |
| D-140 | `RunConfig` 四字段 | freegraph 四字段可读；上游用 `RunnableConfig` 表达 | DIFF（X-2） |
| D-141 | 无别名图的节点名 / 路由 | 两侧 `updates` 键 / 图节点名 / 终态一致 | SAME |
| D-142 | `add_node(..., alias=...)` | freegraph：`TypeError`；上游：静默忽略 | STRICTER（X-3） |
| D-143 | `stream()` / `get_graph()` 的节点名 | 两侧都使用内部节点名；无别名映射 | SAME |
| D-144 | 条件边路由视图 | 两侧路由函数入参都无 `context`；路由目标按内部节点名解析 | SAME |

⇒ **SAME 5**（D-137 / D-139 / D-141 / D-143 / D-144）+ **DIFF 2**（D-138 / D-140）+
**STRICTER 1**（D-142）。

---

## §4 偏离登记（X-1…X-3）

| # | 类别 | 被偏离的判据 | 理由 |
|---|---|---|---|
| **X-1** | DIFF（必须自研区 ① / ③） | `context` 的载体与访问形态 | 上游 `context=` + `Runtime.context`；freegraph `RunConfig.context` + `state.context`（提示词已冻结） |
| **X-2** | DIFF（必须自研区 ①） | `RunConfig` 不复用 `RunnableConfig` | `RunnableConfig` 属 `langchain-core`，复用会拖回 `langsmith` |
| **X-3** | STRICTER（更严失败信号） | `add_node(..., alias=...)` | 上游静默忽略；freegraph `TypeError`，避免误导 |

---

## §5 破冻结面（T-1…T-7）

| # | 冻结面 | 处置 |
|---|---|---|
| T-1 | B5F2 / B7F1 C4「普通 dict」 | 只补注记：无 context ⇒ 精确 dict；有 context ⇒ dict 子类 |
| T-2 | C25 / Q8 / 宪法 / 立项书 §5.2 / §5.3 / §9.2 / 宪法 changelog | 正式移除：C25 从 active 清单移除、编号不复用；C26/C27 不重编号；宪法 1.16.0 + changelog |
| T-3 | B6F1 `add_node(alias=)` / `_NodeRecord.alias` | 移除参数 / 字段 / 测试 / 合同 |
| T-4 | B2F2 门面 / 兼容矩阵 | 移除 alias 签名 / 矩阵行 |
| T-5 | B22F1 图导出注记 | 删除「别名归 B8F3」；`name == id` 不变 |
| T-6 | 验收脚本 / README / 测试 C25 | 移除 C25 用例 / 软断言行 |
| T-7 | B6F1 / B7F2 / B8F2 alias 交接 | 撤回 / 收缩 B8F2 D-1 |

> **追认**：T-1…T-7 共用本 feature 的**唯一一次**追认；文字落
> `harness/verification/B8F3/manual-verification.md`；**未追认前 MUST NOT 合入**。

---

## §6 三态标注一致性

- 对照表（§1）的 `DIFF` / `STRICTER` / `SAME` 与偏离登记（§4）逐字一致。
- `X-1` → P-03 / D-138；`X-2` → P-06 / D-140；`X-3` → P-02 / D-142。
- alias 移除不是「偏离」而是**契约修订**（T-2…T-7）；不在 X 表重复登记。
