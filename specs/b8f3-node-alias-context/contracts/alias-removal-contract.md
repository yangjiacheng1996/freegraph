# 契约：B8F3 · alias 彻底移除（C25 正式作废）

**Feature**: `B8F3` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**状态**: Phase 1 设计契约 · **可被 `/speckit.tasks` 追溯** · **MUST NOT** 被测试解析

> **背景**：用户 2026-11-20 拍板：freechain 是稳定、开箱即用的图集合，不存在频繁改节点名的
> 真实场景；alias 是未经充分论证的「脂肪」。**彻底移除**，接受跨 feature 冻结面修订。

---

## §0 `add_node` 签名（唯一权威）

**本 feature 之后**：

```text
StateGraph.add_node(
    node: str | Callable[..., Any],
    action: Callable[..., Any] | None = None,
    *,
    defer: bool = False,
    metadata: Mapping[str, Any] | None = None,
    destinations: dict[str, str] | tuple[str, ...] | None = None,
) -> Self
```

- **无 `alias`** 参数。
- 单 callable 形态 `add_node(fn)` 保留。
- `defer` / `metadata` / `destinations` 语义不变。
- 位置参数 `(node, action)` 不变。

### §0.1 失败信号

| 输入 | 行为 |
|---|---|
| `add_node("agent", fn, alias="model")` | **内置 `TypeError`**；消息点名 `alias`（具体措辞不冻结） |
| `add_node("agent", fn, alias=None)` | 同上（关键字存在即失败） |
| `add_node("agent", fn)` / `add_node("agent", fn, defer=True)` | 正常登记 |
| 失败后 | 构建器状态**零修改**（不留下半登记节点） |

> 与上游的差异：上游经 `**kwargs` **静默忽略** `alias`（E-01）；freegraph 选择**更严**的
> `TypeError`（X-3 STRICTER），避免「可传但没用」的误导。

---

## §1 `_NodeRecord` / `_BuilderSpec`

### 1.1 `_NodeRecord`（L3 私有）

**之后字段**（顺序冻结）：

```text
_NodeRecord(
    name: str,
    action: Callable[..., Any],
    defer: bool = False,
    metadata: Mapping[str, Any] | None = None,
    destinations: tuple[tuple[str, str | None], ...] = (),
)
```

- **无 `alias`** 字段。
- `metadata` 浅拷贝、`destinations` 归一化等既有规则不变。

### 1.2 `_BuilderSpec`

| 字段 | 之后 |
|---|---|
| `channels` | 不变 |
| `nodes` | 不变（`NodeSpec` 无 alias） |
| `node_records` | `dict[str, _NodeRecord]`（无 alias） |
| `edges` | 不变 |
| `conditional_edges` | 不变 |

- `CompiledGraph._builder_spec` 的保留**不变**；只是不再承载 alias。
- 任何读取 `_NodeRecord.alias` 的代码 MUST 一并删除。

---

## §2 不受影响的行为（逐条）

| 面 | 之后 |
|---|---|
| `invoke` 终态 | 内部节点名无影响；完整状态不变 |
| `stream_mode="updates"` 载荷键 | 内部节点名 |
| `PregelTask.name` / `path[0]` | 内部节点名 |
| `stream_mode="tasks"` / `"debug"` | 内部节点名 |
| `get_graph()` 节点 `id` / `name` | 内部节点名；`name == id`（B22F1 现有断言不变） |
| `draw_mermaid()` 标签 | 内部节点名 |
| `draw_mermaid_png()` | 由 mermaid 文本派生；内部节点名 |
| `path_map` 查表 | 内部节点名 |
| `Command.goto` / `Send.node` | 内部节点名 |
| 静态边 / 多源边 / 条件边 | 不受影响 |
| `defer` / `metadata` / `destinations` | 不受影响 |
| `Node.name`（图展示名） | **不是** C25 别名；保持现状（缺省归一为 `id`） |

---

## §3 C25 历史处理

| 文件 / 面 | 处理 |
|---|---|
| `harness/reports/Q8-图运行时最小契约.md` §3.4 | C25 行**保留为历史墓碑**；active 清单改为 **C1–C24 + C26–C27**；编号不复用；C26/C27 不重编号 |
| `.specify/memory/constitution.md` 原则 VII + 版本 1.16.0 | C25 提及保留；active 清单改为 **C1–C24 + C26–C27**；编号不复用；C26/C27 不重编号 |
| `harness/proposals/立项书.md` §5.2 / §5.3 / §9.2 | C25 行保留为墓碑；B8F3 行改为 C21/C22；§9.2 graph_core 覆盖改 C1–C24 |
| `harness/features/B8F3_节点别名与context通道.md` | **不改写**（历史提示词）；B8F3 spec 的「范围变更」为权威 |
| B6F1 / B2F2 / B22F1 / B7F2 / B8F2 | 按 T-3…T-7 移除代码 / 签名 / 兼容矩阵 / 交接注记 |

> **原则 VIII**：已发布的事实不改写。C25 正式作废后仍是历史 / 墓碑条目；
> 编号保留不复用、C26/C27 不重编号；未来 alias 使用新编号（如 C28）。

---

## §4 受影响文件（T-2…T-7 / R-1…R-7 / RD-xx）

> **编号约定**：`T-x` / `R-x` 以 `spec.md` 的「契约修订：移除 alias」为唯一权威；
> `RD-xx` 指 `plan.md` 的 Pre-registered Red List。本表不再复用 `R-5 / R-6 / R-7`
> 表示具体文件，避免与 spec 的同号条目冲突。

| # | 文件 / 面 | 动作 |
|---|---|---|
| **T-2** | Q8 §3.4 active 清单 / 宪法原则 VII / 立项书 §5.2 / §5.3 / §9.2 / 宪法 changelog | **正式移除**：C25 从 active 清单移除、编号不复用；C26/C27 不重编号；宪法 1.16.0 + changelog |
| **T-3** | `specs/b6f1-stategraph-builder/{spec,contracts/builder-contract,data-model}.md` · `tests/facade/test_stategraph_builder.py` | 移除 alias 参数 / 字段 / 测试；撤回 D-3；更新 FR-010 / 裁定 7 / SC-014 / P-02b / D-74 / X-1 |
| **T-4** | `specs/b2f2-public-api-facade/{spec,contracts/facade-api,data-model,research,checklists/requirements}.md` | 门面签名移除 alias；兼容矩阵删除「新增 alias」与「别名寻址 → B8F3」 |
| **T-5** | `specs/b22f1-get-graph-mermaid/{spec,contracts/graph-export-contract,data-model}.md` | 删除「别名归 B8F3 / 待解析」注记；`name == id` 不变 |
| **T-6** | `harness/demo/graph_core.py` · `harness/demo/README.md` · `harness/demo/acceptance.py` · `tests/runtime/test_acceptance_script.py` | 删除 `case_node_alias` / C25 软断言行 / A10 行 / `C1–C25` 描述；C21 改硬断言 |
| **T-7** | B6F1 / B7F2 / B8F2 的 alias 交接注记 | 撤回 D-3 / 收缩 B8F2 D-1 为「只用内部节点名」 |
| **RD-07** | `README.md:114` | `StateGraph` 兼容矩阵删除 alias / C25 |
| **RD-08** | `src/freegraph/contracts/graph.py:152` | `Node` 文档改为 C13；`Node.name` 是展示名 |
| **RD-02** | `tests/differential/parity_probe.py:4139-4162,4220` | 移除 D-74 alias 场景；D-142 覆盖 alias 传参失败 |

---

## §5 测试要求

| 测试 | 断言 |
|---|---|
| `tests/facade/test_stategraph_builder.py` | `add_node(alias=...)` ⇒ `TypeError`；`_NodeRecord` 无 alias 字段；`defer` / `metadata` / 单 callable 仍正常 |
| `tests/differential/parity_probe.py` D-142 | freegraph：`TypeError`；上游：静默忽略 ⇒ STRICTER |
| `tests/runtime/test_acceptance_script.py` | README 不再包含 C25 软断言行；C21 为硬断言 |
| `harness/demo/graph_core.py` | 无 `case_node_alias`；C21 硬断言 |
| `README.md` / `harness/demo/README.md` / `acceptance.py` | 无 `alias=` / C25 / `case_node_alias` 悬空引用 |
| 全量 pytest | 除预登记红点外零回归；`runtime.__all__` 23 不变 |

---

## §6 验收映射

| 判据 | 验证面 |
|---|---|
| SC-004 | alias 彻底移除；`TypeError`；无 alias 字段；C25 不再作为 active 契约 / 验收项 |
| SC-009 | demo core 套件通过；C25 用例 / README 行移除 |
| SC-012 | T-2…T-7 契约修订落地；无「可传 alias」的误导性文档 |
| D-142 | alias 传参失败信号（STRICTER） |

---

## §7 禁止事项（逐条）

1. **MUST NOT** 保留 `add_node(..., alias=...)` 的 no-op 兼容关键字。
2. **MUST NOT** 在 `_NodeRecord` / `_BuilderSpec` 保留 `alias` 字段。
3. **MUST NOT** 在 `stream()` / `get_graph()` / `PregelTask.name` 引入别名映射。
4. **MUST NOT** 删除或改写 C25 的历史文字（只追加正式作废注记）。
5. **MUST NOT** 留下 `case_node_alias` / C25 软断言行 / `C1–C25` 的悬空引用。
6. **MUST NOT** 把 `Node.name`（图展示名）误当成 C25 别名一并删除。
7. **MUST NOT** 静默忽略 `alias` 关键字（必须 `TypeError`）。
8. **MUST NOT** 让 alias 移除改变无 alias 图的任何可观察行为。
