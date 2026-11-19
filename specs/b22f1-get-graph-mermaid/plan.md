# Implementation Plan: B22F1 · `get_graph(xray=)` + 自有 `Graph` 类型 + `draw_mermaid()`

**Branch**: `b22f1-get-graph-mermaid`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`
⇒ 无 `before_plan` 钩子；既有 feature 同样在 `main` 上开发）
| **Date**: 2026-11-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b22f1-get-graph-mermaid/spec.md`

**feature ID**: `B22F1`（M2 图定义与对外 API · **第 19 个** · 前置：**B7F2**（主）+
B1F1 / B2F1 / B2F2 / B6F1 / B7F1 / B7F3 / B7F4 / B8F1 / B8F2 / B9F1（承接 H-1…H-9）
· 下游：**B23F1**（D-1 / D-2））

---

## Summary

交付**图结构导出**与**mermaid 文本导出**：

1. `CompiledGraph.get_graph(*, xray=False)` 从**编译期冻结快照**（`_spec` /
   `_conditional_edges` / `_builder_spec`）导出**自有** `Graph`（含 `Node` / `Edge`）；
2. `Graph.draw_mermaid()` **纯本地**生成合法 mermaid 文本 —— 零网络、零第三方、确定性；
3. 为达成上游最优图渲染，**破冻结面**实现上游**完整静态声明**：
   `Command` 泛型化 + `Command[Literal[...]]` 类型推断；`add_node(..., destinations=...)`；
   `destinations` 优先；**无运行期跳转记录**。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **`get_graph`** | 编译产物 → 自有 `Graph` | 只读快照 · 零执行 · `xray=True ≡ False`（无子图） |
| **`Graph` 节点表** | `__start__` + 业务节点 + `__end__` | 全部业务节点（含不可达）· `metadata` / `defer` / `__interrupt` |
| **`Graph` 边表** | 静态 / 条件 / 节点声明 / join | 每源一条边 · `(source,target)` 去重且条件优先 · 终结补 `END` |
| **可达性** | 静态边组闭包 | 单源 / 条件 / 声明 = 大小 1 的组；join = 全源一组；只导出可满足组 |
| **`draw_mermaid`** | 合法、确定、离线的文本 | `graph TD;` · 安全 id · 标签转义 · 虚线条件边 |
| **`Command[N]`** | 泛型命令原语 | 运行期语义不变；仅用于图渲染的类型推断 |
| **`destinations`** | `add_node` 的图渲染声明 | `Sequence[str]` / `dict[str,str]`；覆盖推断；不影响执行 |
| **差分场景组** | 与上游同场景对跑 | D-01…D-15 · SAME 13 / DIFF 1 / STRICTER 1 · 上游缺席即 skip |
| **一键验收** | `harness/verification/B22F1/acceptance.py` | 退出码 0/1/2 · pytest 真跑 |

**技术方案（关键落点）**：

| 环节 | 落点 |
|---|---|
| 图导出 | L3 `src/freegraph/_stategraph.py` 的 `CompiledGraph.get_graph`（替换 `:572` 的 stub） |
| 图渲染 | L1 `src/freegraph/contracts/graph.py` 的 `Graph.draw_mermaid` + 私有 `_safe_id` / `_escape_label` |
| `Command` 泛型 | L1 `src/freegraph/contracts/types.py:60`（`class Command(Generic[N])`） |
| 类型推断 | L3 `_stategraph.py` 私有 `_infer_command_destinations`（登记期调用） |
| `destinations` | L3 `_NodeRecord`（`:78`）追加字段；`StateGraph.add_node`（`:611`）追加关键字 |
| 目标校验 | L3 `_validate_targets`（`:797`）扩展声明目标 |
| 快照 | L3 `_BuilderSpec`（`:111`）经 `node_records` 携带声明；`CompiledGraph._builder_spec` 只读 |
| 图导出算法 | L3 私有 `_export_graph(spec, builder_spec, conditional, interrupts)`（纯函数） |
| 验收脚本 | `harness/verification/B22F1/acceptance.py`（新建） |

**零新增**：运行时依赖 · 公开顶层符号 · 错误类型 · async · 门禁编号。
**破冻结面 6 类**（T-1…T-6）并入**唯一一次**发起者追认（2026-11-20）。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`requires-python = ">=3.11"`）。
使用 `typing.get_type_hints` / `get_origin` / `get_args` / `Generic` / `TypeVar` /
`Literal` / `dataclasses` —— 均为 3.11 标准库。**MUST NOT** 使用 3.12+ 的
`TypeAliasType` / `override` / `TypeIs` / PEP 695 `type`。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []`）。
开发期：`pytest`（`.venv` · 9.2.0）· 差分：`langgraph==1.2.11`（既有 `differential` 组）。
`pyproject.toml` **零改动** ⇒ G3 / G21 / G22 / G23 恒绿。

**Storage**: N/A（不持久化；checkpointer / store 不在本 feature 范围）。

**Testing**:
- `tests/contracts/test_graph.py`（`draw_mermaid` / 转义 / 空图 / 确定性）
- `tests/contracts/test_types.py`（`Command[...]` 下标与运行期语义不变）
- `tests/runtime/test_graph_export.py`（节点 / 边 / 可达性 / join / metadata；**新建**）
- `tests/facade/test_stategraph_builder.py`（`destinations` 形态 / 推断 / 覆盖 / 校验）
- `tests/facade/test_get_graph.py`（门面行为：`xray`、运行前后一致；**新建**）
- `tests/runtime/test_graph_offline.py`（断网 / 零出站 / 静态禁用扫描；**新建**）
- `tests/runtime/test_graph_manual_record_guard.py`（人工验证记录的自动守卫；**新建**）
- `tests/differential/parity_probe.py`（新增 `GraphScenario` + `_run_graph_scenarios`；D-01…D-15）
- `tests/differential/test_parity_probe.py`（调用图导出场景组；上游缺席即 skip）
- `tests/runtime/test_graph_acceptance.py`（一键验收真跑；**新建**）

**Target Platform**: Linux / macOS / Windows · CPython 3.11+ · **零出站**。

**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A（不设墙钟预算）**。图导出 = O(V+E) 的纯内存遍历；
mermaid 渲染 = O(V+E) 字符串拼接；无 I/O / 无网络。MUST NOT 用耗时做断言。

**Constraints**（主要来自 spec 的 MUST 条目）：

| 约束 | spec 条目 |
|---|---|
| 只依赖标准库；MUST NOT import `langchain*` / `langgraph*` / `langsmith` | FR-017 |
| 零出站 / 零环境变量 / 导入无副作用（尤其 `draw_mermaid`） | FR-013 · FR-017 · SC-001 |
| `get_graph` 只读快照、零执行、运行前后逐项相等 | FR-008 / FR-009 / FR-012 · SC-008 / SC-010 |
| `xray=True ≡ xray=False`（v1 无子图）；不抛 `TypeError` | FR-007 / FR-021 · SC-003 |
| 节点 / 边：START+业务+END；不可达节点保留、出边不导出 | FR-002 / FR-004 / FR-028 · SC-016 |
| 条件边逐分支逐目标；`condition == branch` | FR-005 · SC-006 |
| 节点声明边：推断 + `destinations`（覆盖）；多目标各一条 | FR-010 / FR-011 · SC-007 / SC-013 |
| join 边：每源一条普通边；组内全源可达才导出 | FR-029 · SC-017 |
| 去重按 `(source,target)`；条件 / 声明边优先 | FR-023 · SC-018 |
| 终结节点补 `END`；`metadata` / `defer` / `__interrupt` | FR-006 / FR-025 |
| mermaid 合法 / 含全部节点名 / 虚线条件边 / 转义 | FR-014 / FR-015 / FR-016 · SC-002 / SC-005 |
| 声明未知目标 ⇒ 编译期 `ValueError`；`destinations` 形态非法 ⇒ `TypeError` | FR-026 · SC-014 |
| 注解不可解析 ⇒ 静默无声明 | FR-027 |
| 破冻结面 T-1…T-6 · 追认 == 1 次 | spec 偏离登记 X-01…X-13 |
| 新源文件署名头 + docstring 首语句 | 宪法原则 X · G30 |
| 人工验证五段式 + 追认文字 | 宪法原则 V |

---

## 绿基线记录 + 变红清单（宪法 v1.11.0 的基线义务）

### 基线（**2026-11-20 · 实施前**）

> 必须使用 **`.venv`**（Python 3.11.16 · packaging 26.3 · pytest 9.2.0）。
> 系统 `python3`（3.12）未安装 `freegraph` 且 `packaging 24.0` 缺
> `packaging.licenses` ⇒ 环境性失败，**不得**作为基线。

| 项 | 计数 |
|---|---|
| passed | **1661** |
| skipped | **4** |
| failed | **0** |
| 耗时 | **108.22s** |

```
1661 passed, 4 skipped in 108.22s (0:01:48)
```

### 变红清单（**预登记** · 实测后 MUST 逐条核对）

| # | 断言位置 | 变红原因 | 处置（拆分而不删 / 只补注记） |
|---|---|---|---|
| R-01 | `tests/runtime/test_conditional_edge_surface.py:101` | `get_graph` 仍在「未实现」参数化里 | 移出；改为真实图导出断言 |
| R-02 | `tests/facade/test_compiled_graph.py:76` | `get_graph` 期望 `NotImplementedError` | 移出循环；新增真实行为断言 |
| R-03 | `tests/facade/test_api_snapshot.py`（入库快照） | `StateGraph.add_node` 增 `destinations` | `--update-api-snapshot` 后提交；`Command` class 行无泛型展示则不变 |
| R-04 | `tests/contracts/test_graph.py`（新增方法） | 既有字段 / 不可哈希 / 相等断言**不应**变红 | 不删；新增 `draw_mermaid` 断言文件内追加 |
| R-05 | `tests/contracts/test_types.py`（`Command`） | 泛型化不得改字段 / `PARENT` / `__slots__` | 既有断言逐条保留；新增 `Command[Literal[...]]` 下标断言 |
| R-06 | `tests/facade/test_stategraph_builder.py`（若存在签名断言） | `add_node` 增关键字 | 原断言保留；新增 `destinations` 断言 |
| R-07 | 兼容矩阵（`README.md` / `public-api.md`） | 新增 `destinations` / `Command` 泛型 | 更新矩阵；**MUST NOT** 漏记（原则 X） |
| R-08 | 人工验证记录（B1F1 / B2F1 / B6F1 / B7F2 / B9F1） | 破冻结面需追认文字 | 落 `harness/verification/B22F1/manual-verification.md`；既有记录只补注记 |

**MUST NOT 变红**（不破面）：
- `target.py`（只读基准）· G1 / G2 / G3 / G4（零依赖 / 惰性 / 零出站 / 禁模块）
- G7 公开符号面（**仍 20**；本 feature 不加顶层符号）
- `tests/contracts/test_protocols.py:258-261`（`get_graph` 关键字 / 缺省）
- `tests/runtime/test_command_contract.py`（`goto` 运行期语义）
- `tests/runtime/test_superstep_*.py`（调度内核零改动）

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith / 零出站 / 零环境变量） | FR-013 / FR-017 · G4 / G24 / G26 / G27 | ✅ |
| 原则 II（零 LangChain · 状态语义等价） | 零新增依赖 · G3 / G21 / G22 / G23 · P-01…P-19 · D-01…D-15 | ✅ |
| 原则 III（验收契约优先 · `target.py` 只读） | `target.py` **零改动**；验收走 `harness/demo/visualization.py` + 新验收脚本 | ✅ |
| 原则 IV（可诊断性 · 可视化不阻断） | 导出零异常；未知目标编译期 `ValueError`；`draw_mermaid` 永不抛 | ✅ |
| 原则 V（人工验收） | 五段式 `manual-verification.md` + T-1…T-6 追认 | ✅ |
| 原则 VI（规格驱动 · 判据级覆盖） | spec FR-001…FR-029 / SC-001…SC-018 · 追溯表 · 守卫断言 | ✅ |
| 原则 VII（职责边界 · C13 / C14 / C26） | `Graph` 自有类型；`xray` v1 仅签名；PNG 归 B23F1 | ✅ |
| 原则 VIII（证据与术语） | `research.md` E-1…E-16 实测 + `contracts/upstream-parity.md` P/X/D 三表一致 | ✅ |
| 原则 IX（许可证 / 商标） | 零新增依赖 ⇒ `THIRD_PARTY_NOTICES` 零变更；mermaid 文本为自有生成 | ✅ |
| 原则 X（署名头 / 文档） | G30 · API 快照 + 兼容矩阵更新 | ✅ |
| 原则 XI（上游优先） | 静态声明 / 渲染语义照抄；偏离 13 条（X-01…X-13）如实登记 | ✅ |
| 原则 XII（最优设计 / 零重复载体） | 复用 `_spec` / `_builder_spec` / `_conditional_edges`；不另造图模型；不重复路由目标 | ✅ |
| 立项书 §5.1 **ARCH-1**（L3 只依赖 L1 / L2） | `_stategraph.py`（L3）→ `contracts.graph`（L1）；`contracts.graph` 只依赖标准库 | ✅ |
| 立项书 §5.1 **ARCH-3**（跨层只经 Protocol + 纯数据类） | 图导出只用 L1 纯数据类；`draw_mermaid` 是 `Graph` 的**纯函数式**方法 | ✅ |
| 运行时基线（3.11 · typing 上限） | Technical Context 逐项 ≤ 3.11 · G9 | ✅ |
| 依赖白名单 / 黑名单 | 零新增运行时依赖 | ✅ |

**破冻结面登记**（发起者 2026-11-20 追认 · 承接方 B22F1）：

| # | 冻结面 | 处置 |
|---|---|---|
| T-1 | B1F1 `Command` 非泛型 | `Generic[N]`；运行期语义不变 |
| T-2 | B6F1 `add_node` 签名 | 增 `destinations` 关键字 |
| T-3 | B7F2 `_NodeRecord` / 快照 | 追加 `destinations` 字段 |
| T-4 | B9F1 D-8 运行期跳转记录 | 静态声明取代；运行期 `goto` 语义不变 |
| T-5 | B2F1 `Graph` 2 字段 | 追加 `draw_mermaid()` 方法；字段不变 |
| T-6 | B2F1 `Edge` 不变式 | 无标签声明边 `condition=None`；分支边仍非空 |

---

## Project Structure

### Documentation (this feature)

```text
specs/b22f1-get-graph-mermaid/
├── plan.md                       # 本文件
├── research.md                   # Phase 0 · 决策 + 实测证据
├── data-model.md                 # Phase 1 · 数据形状
├── quickstart.md                 # Phase 1 · 验证指南
├── contracts/
│   ├── graph-export-contract.md  # 图导出 / mermaid 的冻结口径
│   └── upstream-parity.md        # P / X / D 三表 + 实测
├── checklists/
│   └── requirements.md           # clarify 后的质量检查表
└── tasks.md                      # Phase 2（/speckit.tasks）
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/
│   ├── graph.py                  # L1：Graph.draw_mermaid + _safe_id + _escape_label（修改）
│   ├── types.py                  # L1：Command 泛型化（修改）
│   └── __init__.py               # 不改导出面
├── _stategraph.py                # L3：_NodeRecord / add_node / 推断 / 校验 / get_graph（修改）
└── graph.py                      # L2 门面：不改签名 / 不新增符号

tests/
├── contracts/
│   ├── test_graph.py             # 追加 draw_mermaid / 转义 / 空图断言
│   └── test_types.py             # 追加 Command 泛型下标断言
├── runtime/
│   ├── test_graph_export.py      # 新建：节点 / 边 / 可达性 / join / metadata
│   ├── test_conditional_edge_surface.py  # R-01：get_graph 移出未实现列表
│   ├── test_graph_offline.py     # 新建：断网 / 零出站 / 静态扫描
│   ├── test_graph_manual_record_guard.py  # 新建：人工记录守卫
│   └── test_graph_acceptance.py  # 新建：一键验收真跑
├── facade/
│   ├── test_compiled_graph.py    # R-02：get_graph 移出未实现循环
│   ├── test_stategraph_builder.py# 追加 destinations / 推断 / 覆盖 / 校验
│   └── test_get_graph.py         # 新建：门面行为
└── differential/
    ├── parity_probe.py           # 追加 GraphScenario + D-01…D-15
    └── test_parity_probe.py      # 调用图导出场景组

harness/verification/B22F1/
├── acceptance.py                 # 新建：一键验收
└── manual-verification.md        # 新建：五段式 + T-1…T-6 追认
```

**Structure Decision**: 单项目（`src/freegraph` + `tests`）；图结构类型在 **L1**
`contracts/graph.py`，图导出在 **L3** `_stategraph.py`。`draw_mermaid` 必须与 `Graph`
同模块（否则 L1 反向依赖 L3，违反 ARCH-1）；其实现只用标准库、无 import 副作用。

---

## Phase 0：Outline & Research

**输出**：[research.md](./research.md)

要解决的设计点（**全部已有唯一裁定**，无 `NEEDS CLARIFICATION`）：

1. 静态声明（`Command[Literal]` + `destinations`）取代运行期记录 —— 已由发起者裁定。
2. `Command` 泛型化的最小改动面（L1 符号 / 运行期语义 / 快照）。
3. 登记期类型推断的实现与失败降级（`get_type_hints` + `Union` 解包 + 静默忽略）。
4. `destinations` 归一化（`Sequence[str]` / `dict[str,str]` / 覆盖 / 校验时机）。
5. 图导出：边组模型、静态可达闭包、join 拆分、终结 `END`、去重优先级。
6. 不可达节点 / 末步单源（自环 / 循环）/ 多源 join 的边界（DIFF 登记）。
7. mermaid：头部、安全 id、标签 / 边标签转义、虚线标签、空图。
8. 层归属：`Graph.draw_mermaid` 在 L1；导出算法在 L3；零反向 import。
9. 破冻结面 T-1…T-6 的回溯修订与基线变红清单。

---

## Phase 1：Design & Contracts

**输出**：[data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

### 数据形状（摘要）

- `Node(id, name, metadata)` / `Edge(source, target, conditional, condition)` /
  `Graph(nodes, edges)` 字段不变；`Graph` 追加无状态方法 `draw_mermaid()`。
- `Command[N]`：字段 / 构造 / `PARENT` 不变；仅增加 `__class_getitem__` 能力。
- `_NodeRecord.destinations: tuple[tuple[str, str | None], ...]`（归一后；
  空元组 = 无声明；`END` 原样保留）。
- 导出中间体（**仅 L3 内部**）：`_EdgeGroup(sources, target, conditional, condition)`；
  节点 / 边最终仍是 L1 纯数据类。

### 接口契约

- [contracts/graph-export-contract.md](./contracts/graph-export-contract.md)：
  `get_graph` / `draw_mermaid` 的**唯一权威**口径（形状、算法、失败信号、不变式）。
- [contracts/upstream-parity.md](./contracts/upstream-parity.md)：
  P-01…P-19 / X-01…X-13 / D-01…D-15 + 实测 E-1…E-16。

### 验证指南

- [quickstart.md](./quickstart.md)：`get_graph` / `draw_mermaid` / 断网 / 差分 /
  一键验收的可运行步骤与预期输出。

---

## 关键算法（设计级伪代码）

```text
export_graph(spec, builder_spec, conditional_edges, interrupt_before, interrupt_after):
    nodes = [Node("__start__")] + [node(name, metadata, defer, interrupts)
                                   for name in spec.nodes] + [Node("__end__")]

    groups = []
    # 1) START 入口 + 静态单源边（不含 END）
    for key, targets in spec.edges:
        if isinstance(key, str): groups += [Group((key,), tgt, False, None) for tgt in targets]
        else:                     groups += [Group(key,     tgt, False, None) for tgt in targets]  # join
    # 2) 静态 END 边（_spec 已过滤 ⇒ 从 _builder_spec 恢复）
    for key, targets in builder_spec.edges:
        for tgt in targets where tgt == END:
            groups += [Group((key,) if str else key, END, False, None)]
    # 3) 条件边（B8F1 targets 逐字）
    for source, items in conditional_edges:
        for item in items: groups += [Group((source,), tgt, True, item["branch"])
                                      for tgt in item["targets"]]
    # 4) 节点声明边（destinations / Literal 推断）
    for name, record in builder_spec.node_records:
        for tgt, label in record.destinations:
            groups += [Group((name,), tgt, True, label)]

    reachable = {"__start__"}
    loop until fixpoint:
        for g in groups where all(src in reachable for src in g.sources):
            reachable.add(g.target)   # END 也记入（汇点）

    edges = []
    for g in groups where all(src in reachable for src in g.sources):
        for src in g.sources: edges.append(Edge(src, g.target, g.conditional, g.condition))

    # 终结节点：可达、无任何已导出出边、且未显式连 END
    for name in spec.nodes where name in reachable and no edge.source == name:
        edges.append(Edge(name, END, False, None))

    edges = dedupe_by_pair(edges, conditional_wins=True)
    return Graph(tuple(nodes), tuple(edges))
```

```text
draw_mermaid():
    lines = ["graph TD;"]
    for node in nodes:
        lines.append(f'\t{_safe_id(node.id)}["{_escape_label(node.name)}"];')
    for edge in edges:
        s, t = _safe_id(edge.source), _safe_id(edge.target)
        if edge.conditional and edge.condition is not None:
            lines.append(f'\t{s} -. &nbsp;{_escape_label(edge.condition)}&nbsp; .-> {t};')
        elif edge.conditional:
            lines.append(f'\t{s} -.-> {t};')
        else:
            lines.append(f'\t{s} --> {t};')
    return "\n".join(lines) + "\n"
```

---

## Complexity Tracking

> **仅登记破冻结面与已裁定偏离**；无其它复杂度豁免。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| `Command` 泛型化（T-1） | 上游图渲染依赖 `Command[Literal[...]]` 推断；发起者裁定按最优设计 | 保留非泛型 + 运行期记录 ⇒ 已证伪为更差（依赖运行、丢失分支） |
| `add_node(destinations=)`（T-2/T-3） | 无类型标注 / 无边图场景的唯一上游声明方式 | 只做泛型 ⇒ 无标注场景无法声明 |
| `Graph.draw_mermaid` 放 L1（T-5） | `Graph` 是 L1 类型，方法必须同模块；L1 不能 import L3 | 放 L3 ⇒ L1→L3 反向依赖（ARCH-1 违规） |
| `Edge.condition=None`（T-6） | 与上游 `Edge.data=None` 同款；发起者裁定 | 填 `"goto"` ⇒ 偏离上游标签语义 |
| 不模拟执行（X-08） | 宪法/承接要求 `get_graph` 零执行、零副作用 | 复制上游 `_draw.py` 的 Pregel 模拟 ⇒ 引入运行期语义与 250 截断 |

**追认**：发起者 **2026-11-20** 批准 T-1…T-6；追认文字落
`harness/verification/B22F1/manual-verification.md`。

---

## Re-check（Phase 1 后）

| 检查 | 结论 |
|---|---|
| 分支/层：L3 → L1 单向；`contracts.graph` 零内部 import | ✅ |
| 零出站：`draw_mermaid` 无 `socket` / `http` / `urllib` / 子进程 | ✅ |
| 公开面：`__all__` 不变；G7 仍 20 | ✅ |
| 冻结面：T-1…T-6 均有 FR + 追认 + 变红清单 | ✅ |
| 判据级覆盖：FR-001…FR-029 ↔ SC-001…SC-018 ↔ D-01…D-15 | ✅ |
| 上游证据：P/X/D 三表一致；E-1…E-16 实测 | ✅ |
| 人工门禁：五段式记录 + 追认 | ✅ |

---

## 后续（Phase 2 · `/speckit.tasks`）

任务 MUST 至少覆盖：

1. T-1…T-6 的回溯修订（源码 + 快照 + 兼容矩阵 + 既有断言拆分）。
2. `Command` 泛型 + `destinations` 形态 / 推断 / 覆盖 / 校验。
3. `Graph.draw_mermaid` + 转义 + 空图 + 确定性。
4. `get_graph` 导出算法（边组 / 可达 / join / 终结 / 去重 / metadata）。
5. 单元 + 门面 + 差分 + 一键验收 + 人工验证记录。
6. 变红清单逐条核对；基线重跑（`.venv/bin/python -m pytest -q`）。
