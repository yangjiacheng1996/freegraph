# B8F3 · Phase 0 研究记录（上游实测取证 + 决策登记 + 遗留登记）

**Feature**: `B8F3` · `context` 独立通道 + `RunConfig` 运行期接线（alias 已移除）
**Spec**: [./spec.md](./spec.md) · **Plan**: [./plan.md](./plan.md)
**取证日期**: 2026-11-20 · **上游版本**: `langgraph` **1.2.11** + `langchain-core` **1.7.6**

> **本文件是「证据」载体，不是「判据」载体** —— 判据的唯一权威是 spec 与
> `contracts/context-channel-contract.md` / `contracts/alias-removal-contract.md`
> （Phase 1 写就）；本文件 MUST NOT 被测试解析。
>
> **编号域隔离**：本文的 **D-01…D-10** 是**决策**编号 · **E-01…E-05** 是**实测**编号 ·
> **DR-1…DR-4** 是**遗留登记**；与 spec 的「承接 H-1…H-5」「差分 D-137…D-144」
> 「破面 T-1…T-7」是**互不相干**的编号域。

---

## §0 方法与取证环境

### 0.1 环境（零仓库改动）

| 项 | 值 | 核实方式 |
|---|---|---|
| 上游版本 | `langgraph` **1.2.11** · `langchain-core` **1.7.6** | `importlib.metadata.version` |
| 版本钉死 | `pyproject.toml` 的 `differential` 依赖组（`"langgraph==1.2.11"`） | 读文件 |
| 解释器 | CPython **3.11**（仓库 `.venv`） | `.venv/bin/python -c "import sys"` |
| 上游包根 | `.venv/lib/python3.11/site-packages/langgraph/` | —— |
| 仓库改动 | **零**（本 phase 只写 `specs/` 工件） | `git status --porcelain` |
| 测试收集 | **1742 tests collected**（2026-11-20） | `pytest --collect-only -q` |

> 实施前 MUST 记录 `pytest -q` 的真实绿基线（passed / skipped / failed / 耗时）；
> 本文件的收集数**不能**替代真实基线。

### 0.2 实测命令形态

```bash
cd /home/ctyun/workspace/github/freegraph
.venv/bin/python - <<'PY'
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime

class S(TypedDict, total=False):
    x: int

def node(state, runtime: Runtime):
    print("ctx =", runtime.context, "state_keys =", sorted(state))
    return {"x": 1}

g = StateGraph(S)
g.add_node("agent", node, alias="model")
g.add_edge(START, "agent")
g.add_edge("agent", END)
app = g.compile()
print(app.invoke({"x": 0}, context={"user": "u1"}))
print([(n.id, n.name) for n in app.get_graph().nodes.values()])
print(list(app.stream({"x": 0}, stream_mode="updates", context={"user": "u1"})))
PY
```

---

## §1 决策登记（D-01…D-10）

| # | 决策 | 理由 | 被否的备选 |
|---|---|---|---|
| **D-01** | **`context` 的唯一来源 = `RunConfig.context`**；不新增 `invoke(..., context=...)` / `stream(..., context=...)` 关键字 | C22 已冻结 `RunConfig`；提示词锁定 `RunConfig(context=...)`；新增关键字会扩大公开面并与 C22 形成双入口 | 上游同款 `context=` 关键字（与 C22 冲突）· `configurable["context"]`（违反 C21 / 拖回 `langchain-core`） |
| **D-02** | **运行期载体 = L2 私有 `ContextVar`**（新 `runtime/_context.py`）；`run_graph` 与 `StreamSession` 在运行入口绑定 / `finally` 复原 | `context` 必须同时服务 `invoke` 与 `stream`；不能进入状态 channels；`ContextVar` 与既有 `_stream_context` / `_interrupt` 的私有载体模式一致；不改任何公开签名 | 复用 `_stream_context.py`（流式专用，invoke 不经过）· 把 `context` 放进 `SchedulerState`（破 B7F1 冻结面）· 显式传参（改 `run_super_step` 签名） |
| **D-03** | **节点视图 = 只读 `dict` 子类 `_ContextState`**；`context is None` 时**不包装**，保持精确 `dict` | 提示词冻结 `getattr(state, "context", None)`；C4 要求无 context 时 `type(state) is dict`；`dict` 子类同时满足「映射语义不变」与「可读 `.context`」 | 把 `context` 作为状态 key（污染状态 / 归约 / C4）· 把 state 换成非 dict 对象（破 C4）· 在节点签名注入 Runtime（超出本 feature 范围 / 改 C5 节点签名） |
| **D-04** | **路由 fresh 视图不包装**；路由第二参 `config` 保持原始 config，可携带 `RunConfig.context` | H-2 只禁止 `context` 进入 fresh 状态视图；上游条件边可经 `Runtime` 读 context（P-03 / P-08）；freegraph 对应物是第二参原始 config | 把 context 加入路由状态视图（违反 H-2 / C8）· 禁止路由读 context（比上游更严且无必要） |
| **D-05** | **`Send.arg` 边界**：`dict` 形态按需包装为 `_ContextState`；非 `dict` 原样传递，不注入 `.context` | `Send.arg` 是任意对象（C18）；只有 `dict` 能安全附加属性；避免改变用户对象类型 / 身份 | 包装所有对象（改变类型 / 身份）· 完全不包装（dict 形态的 fan-out 失去 context） |
| **D-06** | **alias 彻底移除**：`add_node` 无 `alias` 参数；`_NodeRecord` / `_BuilderSpec` 无 `alias` 字段；传 `alias=` ⇒ `TypeError` | 用户 2026-11-20 明确拍板：freechain 稳定、alias 无真实高频改名场景、与上游一致、降低心智负担；保留 no-op 会误导 | 保留 no-op 关键字（用户以为可用）· 保留 alias 语义（继续维护无收益命名空间）· 仅标记 deprecated（仓库尚未发布 v1，无迁移负担） |
| **D-07** | **C25 正式作废 + 历史文字保留为墓碑** | 宪法原则 VIII「已发布事实不改写」；C25 从 active 清单移除、编号不复用、C26/C27 不重编号；未来 alias 使用新编号（如 C28） | 删除 C25 全部历史文字（违反原则 VIII）· 全量重编号（改写 C26/C27 事实）· 继续把 C25 列为 v1 验收项（与用户决定冲突） |
| **D-08** | **零新增公开面**：`_context.py` 私有（`__all__ = []`）；`runtime.__all__` 仍 23；无新依赖 / 新错误类型 | 原则 XII「零重复载体」；`context` 不需要新的公开 getter（节点经 `state.context`）；不扩大 API 面 | 新增 `get_context()` 公开函数（超出提示词形态）· 新增 `context` 类型 / 模块（无必要） |
| **D-09** | **C4 双断言**：无 context ⇒ `type(state) is dict`；有 context ⇒ `isinstance(state, dict)` + `dict(state)` == 稀疏状态 | 保持 B7F1 / B5F2 的 C4 判据逐字不变，同时验证新能力 | 放宽 C4 为 `isinstance`（会削弱既有判据） |
| **D-10** | **差分场景新组 D-137…D-144** | 与 B8F2 的 D-121…D-136 编号衔接；覆盖 context 状态隔离、RunConfig、alias 移除、路由视图 | 复用既有 invoke / stream 组（编号语义混杂） |

---

## §2 上游实测基线（E-01…E-05）

> 全部于 `.venv` 的 `langgraph 1.2.11` 真跑；探针脚本不提交仓库。

| # | 实验 | 真实输出 | 对 freegraph 的结论 |
|---|---|---|---|
| **E-01** | `StateGraph.add_node("agent", fn, alias="model")` | 上游**接受**该关键字（经 `**kwargs: Unpack[DeprecatedKwargs]`），但**静默忽略**；图仍以 `agent` 登记 | alias 是 freegraph 自研增量；移除后 freegraph 抛 `TypeError` ⇒ **X-3 STRICTER** |
| **E-02** | `invoke({...}, context={"user":"u1"})`，节点签名 `(state, runtime: Runtime)` | 节点从 `runtime.context` 读到 `{"user":"u1"}`；`state` 键集不含 `context` | `context` 是独立通道；freegraph 用 `RunConfig.context` + `state.context` ⇒ **X-1 DIFF** |
| **E-03** | 同图 `stream(..., stream_mode="updates")` | 载荷键为 `agent`（不是 `model`）；alias 不参与 | freegraph 移除 alias 后与上游同口径（内部节点名） |
| **E-04** | 同图 `get_graph()` / `draw_mermaid()` | 节点 `id` / `name` 为 `agent`；mermaid 文本不出现 `model` | 图导出继续用内部节点名；B22F1 现有断言不变 |
| **E-05** | 条件边路由函数在 `invoke(..., context=...)` 下执行 | 路由函数入参键集不含 `context`；`context` 只能经 `Runtime` 取得 | freegraph 的 fresh 视图无 context；第二参原始 config 可携带 context（D-04） |

### 2.1 上游锚点（版本 + 路径:行号）

| 语义点 | 上游锚点 |
|---|---|
| `add_node` 签名无 `alias` | `langgraph/graph/state.py:667-682` |
| `invoke` 的 `context=` 参数 | `langgraph/pregel/main.py:3783-3843` |
| `Runtime.context` | `langgraph/runtime.py:198` |
| 条件边可读 context（文档） | `harness/docs/oss/python/langgraph/graph-api.md:999-1035` |
| `updates` 载荷键 = 节点名 | `langgraph/pregel/_io.py:118` |
| `PregelTask` 七字段 | `langgraph/types.py:637-646` |
| `path_map` 查表（不解析别名） | `langgraph/graph/_branch.py:199-211` |

---

## §3 freegraph 侧代码锚点

| 落点 | 文件:行号（当前） | 本 feature 动作 |
|---|---|---|
| `_NodeRecord` | `src/freegraph/_stategraph.py:83-89` | 删除 `alias` 字段 |
| `add_node` | `src/freegraph/_stategraph.py:834-890` | 删除 keyword-only `alias`；失败时 `TypeError` |
| `CompiledGraph.invoke` | `src/freegraph/_stategraph.py:635-680` | **零改动**（`run_graph` 内部绑定 context） |
| `CompiledGraph.stream` | `src/freegraph/_stategraph.py:682-700` | **零改动**（`StreamSession` 内部绑定 context） |
| `_node_input` | `src/freegraph/runtime/superstep.py:784-800` | `read_channels(...)` 后按需 `with_context(...)` |
| `_run_round` fan-out 准备 | `src/freegraph/runtime/superstep.py:1328-1340` | `Send.arg` 为 `dict` 时按需 `with_context_arg(...)` |
| `run_graph` | `src/freegraph/runtime/superstep.py:2178-2260` | 在 `bind_run(table)` 同一作用域绑定 `bind_context(run_config.context)` |
| `StreamSession.__enter__` | `src/freegraph/runtime/_stream.py:74-118` | 绑定 `bind_context(run_config.context)`；`__exit__` 复原 |
| `StreamSession.__exit__` | `src/freegraph/runtime/_stream.py:119-133` | 复原 context token |
| 流式上下文（既有） | `src/freegraph/runtime/_stream_context.py:120-166` | **零改动**；不把 C21 context 混入流式上下文 |
| `RunConfig` | `src/freegraph/contracts/types.py:180-260` | **零改动**（九字段已含 `context`） |
| `Node` 文档 | `src/freegraph/contracts/graph.py:131-153` | 去掉 C25 引用；`Node.name` 是展示名，不是节点注册别名 |
| `runtime.__all__` | `src/freegraph/runtime/__init__.py` | 仍 **23**；`_context.py` 不进 `__all__` |

---

## §4 受影响面与预登记红点

| # | 位置 | 当前事实 | 本 feature 动作 |
|---|---|---|---|
| **AF-1** | `tests/facade/test_stategraph_builder.py:61-77` | 断言 `record.alias == "model"` | 改为 `TypeError` + 无 `alias` 字段；保留 defer / metadata / 单 callable |
| **AF-2** | `tests/differential/parity_probe.py:4139-4162,4220` | D-74 alias 场景 | 移除；D-142 在新 context 组覆盖 alias 传参失败 |
| **AF-3** | `tests/runtime/test_acceptance_script.py:59-64` | 断言 README 保留 C25 | 改为断言 C25 已移除；新增 C21 硬断言检查 |
| **AF-4** | `harness/demo/README.md:25,70,83` · `harness/demo/acceptance.py:70` · `harness/demo/graph_core.py:31,563-602,660` | C25 / `case_node_alias` / `C1–C25` | 删除 C25 / A10 / `case_node_alias`；覆盖改 C1–C24；C21 改硬断言 |
| **AF-5** | `README.md:114` | `add_node(... alias=None ...)` / C25 | 删除 alias / C25；其余兼容矩阵不变 |
| **AF-6** | `src/freegraph/contracts/graph.py:152` | `Node` 文档「C13 / C25」 | 改为 C13；注明 `Node.name` 是展示名，不是 C25 别名 |
| **AF-7** | C25 / Q8 / 宪法 / 立项书 / B6F1 / B2F2 / B22F1 / B7F2 / B8F2 / B8F1 specs | alias 承诺 / 交接注记 | 按 T-2…T-7 修订：C25 正式作废、编号不复用；历史文字保留；代码 / 签名 / 测试彻底移除 |
| **AF-8** | `tests/runtime/test_superstep_contract.py:204-227` | C4 I-1 `type(state) is dict` | **保持绿**（无 context 时精确 dict） |
| **AF-9** | `tests/runtime/test_conditional_edges.py:918` | 路由视图无 context | **保持绿**（不包装 route view） |
| **AF-10** | `tests/contracts/test_types.py:350,364` | `RunConfig.context` | **保持绿**（字段零改动） |

---

## §5 遗留登记（DR-1…DR-4）

| # | 遗留项 | 现状 | 处置 / 承接 |
|---|---|---|---|
| **DR-1** | `context_schema` 的声明式 schema / 校验 / coerce | 上游支持；本 feature 不实现 | Out of Scope；`StateGraph(context_schema=...)` 仍「接受但不使用」 |
| **DR-2** | checkpoint 中的 `context` 持久化 / 恢复 | 上游支持；本 feature 不读写快照 | 归 **B14F1**；`context` 不进 checkpoint |
| **DR-3** | `Send.arg` 非 `dict` 的 `.context` | 无法安全附加属性 | v1 边界：原样传递，不承诺 `.context`；写入 spec / contract / quickstart |
| **DR-4** | `invoke(..., context=...)` 上游关键字 | freegraph 不新增 | 记录为 **X-1**；`context` 只经 `RunConfig` / mapping |

---

## §6 Phase 0 结论

- 无 `NEEDS CLARIFICATION`：上游对 context 有答案，freegraph 的差异已登记；alias 已由用户移除。
- `context` 的实现是**单载体 + 单视图**：`ContextVar` + `_ContextState`；
  不碰 channels / `configurable` / checkpoint / route fresh view。
- alias 的移除是**契约修订 + 代码移除**，不是行为新增；C25 正式作废、编号保留不复用、C26/C27 不重编号；历史文字保留为墓碑。
- 预登记红点集中在 5 个文件（builder 测试 / parity probe / acceptance 脚本 / demo / README）
  与 6 份 spec 文档；实施时按 plan 的 RD-01…RD-12 逐条归因。
