# B22F1 人工验证记录

**Feature**: `specs/b22f1-get-graph-mermaid/`
**日期**: 2026-11-20
**验收人**: opencode（执行）· 发起者（人工验收 + T-1…T-6 追认）
**发起者人工验收**: **通过**（2026-11-20）
**签名**: 发起者

## 1. 环境

- `.venv/bin/python --version`: Python 3.11.16
- `.venv/bin/python -m pytest --version`: pytest 9.2.0
- 上游（差分用，非仓库依赖）: `langgraph 1.2.11`
- 基线（实施前）: `.venv/bin/python -m pytest -q` = `1661 passed, 4 skipped, 0 failed`（108.22s）
- `pyproject.toml`: 未改动；运行时依赖 `dependencies = []`

## 2. 步骤与实际输出

### 2.0 Foundational（Command 泛型 / destinations）

```text
$ .venv/bin/python -m pytest -q tests/contracts/test_types.py tests/facade/test_stategraph_builder.py tests/facade/test_api_snapshot.py
93 passed, 1 skipped in 3.16s
```

（`test_api_snapshot.py` 的 1 条 skip 为 `--update-api-snapshot` 默认关闭的守卫。）

### 2.1 US1 · 图结构导出

```text
$ .venv/bin/python -m pytest -q tests/runtime/test_graph_export.py tests/facade/test_get_graph.py tests/runtime/test_conditional_edge_surface.py tests/facade/test_compiled_graph.py
66 passed in 0.52s
```

### 2.2 US2 · mermaid 文本

```text
$ .venv/bin/python -m pytest -q tests/contracts/test_graph.py tests/runtime/test_graph_export.py
42 passed in 0.21s
```

### 2.3 US3 · 断网 / 零出站

```text
$ .venv/bin/python -m pytest -q tests/runtime/test_graph_offline.py tests/contracts/test_graph.py
34 passed in 0.27s
```

### 3. 差分与一键验收

```text
$ .venv/bin/python -m pytest -q tests/differential/test_parity_probe.py::test_graph_export_parity_scenarios_meet_their_verdicts
1 passed in 1.01s

$ .venv/bin/python harness/verification/B22F1/acceptance.py
B22F1 acceptance: PASS
```

差分场景组：D-01…D-15（含 D-12a 自环 / D-12b 两节点循环）。上游在场 ⇒ 真跑；
上游缺席 ⇒ skip（沿用 B5F2 纪律）。

## 4. 结论（A1–A4）

| # | 判据 | 结论 |
|---|---|---|
| A1 | `draw_mermaid()` 离线必然成功 | **通过**（断网 socket 守卫下返回合法文本） |
| A2 | 零出站 | **通过**（框架出站计数 == 0） |
| A3 | `get_graph(xray=)` 可用 | **通过**（`xray=True` / `False` 逐项相等；真值/假值不抛） |
| A4 | 自有 `Graph` 类型 | **通过**（`freegraph.contracts.graph.Graph`；依赖闭包无 LangChain 家族） |

## 5. 遗留问题

```text
$ .venv/bin/python -m pytest -q
1700 passed, 4 skipped in 112.51s
```

4 条 skip 均为既有环境 / 可选工具 / Windows 专属路径；0 failed。

### 破冻结面追认

- **无遗留阻塞**。
- 发起者 **2026-11-20** 追认 T-1…T-6：
  - T-1 `Command` 泛型化（运行期语义不变）
  - T-2 `add_node(destinations=)`
  - T-3 `_NodeRecord` / 编译快照追加 `destinations`
  - T-4 B9F1 D-8 的「运行期跳转记录」由上游静态声明取代
  - T-5 `Graph.draw_mermaid()` 追加（字段 / 构造 / `__all__` 不变）
  - T-6 无标签声明边 `condition=None`（分支边仍非空）
- 承接方：**B22F1**。
