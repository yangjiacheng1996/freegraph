# B8F3 人工验证记录

> 本文件按宪法原则 V 的五段式组织：环境 / 步骤 / 实际输出 / 结论 / 遗留问题。
> T-1…T-7 的追认文字见 §3.5。

## 1. 环境

- Feature: `B8F3 · context 独立通道 + RunConfig 运行期接线（alias 已移除）`
- 仓库: `/home/ctyun/workspace/github/freegraph`
- Python: `.venv`（CPython 3.11）
- 上游: `langgraph 1.2.11` / `langchain-core 1.7.6`（实测 `importlib.metadata.version`）
- 环境变量: 清空 `LANGSMITH_*` / `LANGCHAIN_*` / `LANGGRAPH_CLOUD_LICENSE_KEY`

### 1.1 基线

- 命令：`.venv/bin/python -m pytest -q tests/`
- 实测：**3 failed, 1733 passed, 6 skipped in 136.23s**
- 失败（**预期** · T020 尚未实施 alias 移除）：
  - `tests/facade/test_api_snapshot.py::TestSnapshotComparison::test_snapshot_matches_the_committed_file`
  - `tests/facade/test_api_snapshot.py::TestUpdateEntryPoint::test_update_entry_point_is_off_by_default`
  - `tests/facade/test_facade_gates.py::TestApiSnapshotIsFrozen::test_snapshot_matches_the_committed_file`
- 归因：T032 已把 `public-api-snapshot.txt` 更新为**无 `alias`**，而 `_stategraph.py` 仍保留 `alias` 参数 ⇒ 快照比对红；T020 完成后转绿。
- `git diff --exit-code -- harness/demo/target.py pyproject.toml`：**CLEAN**。

## 2. 步骤

### 2.1 US1 · context 独立传递

- 命令：`.venv/bin/python -m pytest tests/facade/test_context_channel.py tests/runtime/test_context_channel.py tests/runtime/test_superstep_contract.py tests/runtime/test_conditional_edges.py -q`
- 实测：**125 passed in 2.33s**
- 覆盖：context 可读 / 状态无污染 / `context is None` ⇒ 精确 `dict` / fan-out dict 包装 / `Command.goto` 标准入参 / 连续运行不泄漏 / C4 与路由视图无 context 保持绿。
- `harness/demo/graph_core.py`：C21 已升级为硬断言，运行 **PASS**（34 通过 / 0 失败；无 `case_node_alias`）。

### 2.2 US2 · RunConfig / configurable 隔离

- 命令：`.venv/bin/python -m pytest tests/facade/test_context_channel.py -k "RunConfig or configurable or Configurable or context_schema" -q`
- 实测：**6 passed, 8 deselected in 0.13s**
- 覆盖：九字段名 / 顺序不变；四核心字段可读且 `tags` 为 `tuple`；`configurable` 独立且不含 `context`；节点 view 无注入的 `configurable`；`thread_id` / `metadata` / `tags` 不注入状态；只传 `configurable={"context": ...}` ⇒ `context is None`；`StateGraph(context_schema=...)` 接受但未使用。
- checkpoint 持久化归 B14F1（本 feature 不读写快照）。

### 2.3 US3 · C25 正式作废与 alias 移除

- 命令：`.venv/bin/python -m pytest tests/facade/test_stategraph_builder.py tests/runtime/test_acceptance_script.py -q`
- 实测：**18 passed in 1.62s**
- 覆盖：`add_node(..., alias=...)` ⇒ `TypeError`；`_NodeRecord` / `_BuilderSpec` 无 `alias` 字段；`defer` / `metadata` / 单 callable 仍正常；D-74 已从 `parity_probe.py` 移除；demo / README / acceptance 的 C25 引用已清理（历史墓碑保留）。
- 复核：`src` / `tests` / `harness/demo` / `README.md` 中无 **active** 的 `case_node_alias` / `alias=None` / C25 验收引用；剩余命中均为历史文档或负向断言。

### 2.4 US4 · 路由 / 流式 / 图导出

- 命令：`.venv/bin/python -m pytest tests/runtime/test_context_channel.py -k "route or Route or stream or graph" tests/runtime/test_conditional_edges.py -q`
- 实测：**15 passed, 49 deselected in 0.39s**
- 补充：`tests/runtime/test_context_channel.py -q` ⇒ **14 passed in 0.24s**
- 覆盖：路由 fresh 视图是普通 `dict` 且无 `context` / `.context`；双参路由第二参 = 原始 `RunConfig`（可读 `.context`）；`path_map` / `updates` / `tasks` / `get_graph()` 全部使用内部节点名。

### 2.5 差分 D-137…D-144

- 命令：`.venv/bin/python harness/scripts/diff_parity.py -k "context D-"`
- 实测：**场景数 8 · 符合判词 8 · 失败 0**（退出码 0）
- 判词分布：**SAME 5**（D-137 / D-139 / D-141 / D-143 / D-144）· **DIFF 2**（D-138 / D-140）· **STRICTER 1**（D-142）。
- pytest 包装：`.venv/bin/python -m pytest tests/differential/test_parity_probe.py -q -k "context"` ⇒ **2 passed, 23 deselected in 1.23s**。

### 2.6 演示 / 验收脚本

- `graph_core.py`：退出码 **0**；**34 条硬断言全通过**（C21 context 为硬断言；无 `case_node_alias`）。
- `acceptance.py`：退出码 **0**；自身硬断言 **13/13 通过**；子脚本 `graph_core` / `agent_loop` / `visualization` 全部 **PASS**；框架出站数 = **0**。
- 本 feature 一键验收：`.venv/bin/python harness/verification/B8F3/acceptance.py` ⇒ 退出码 **0**，**A1…A7 全部 PASS（7/7）**。
- 修复记录：`acceptance.py` 的 `build_minimal_graph()` 原用 `StateGraph(dict)`，在 B4F1 schema 校验下抛 `InvalidSchemaError`；已改为 `TypedDict` 最小 schema（`_MinimalState`），不改变验收语义。

### 2.7 C25 作废与治理层证据

- 宪法：`.specify/memory/constitution.md` 页脚 **Version: 1.16.0**；原则 VII active 清单 = **C1–C24 + C26–C27**；C25 墓碑注记保留。
- changelog：`.specify/memory/constitution-changelog.md` 含 **v1.16.0（2026-11-20）| MINOR —— C25（节点命名别名）正式作废**。
- Q8 / 立项书：均写死 active = `C1–C24 + C26–C27`，并保留 C25 历史墓碑。
- 代码：`StateGraph.add_node` 无 `alias` 形参；`_NodeRecord` / `_BuilderSpec` 无 `alias` 字段；`add_node(..., alias=...)` ⇒ 内置 `TypeError`。

## 3. 实际输出

### 3.1 context 实测

- `RunConfig(context={"user": "u1"})` ⇒ 节点 `getattr(state, "context", None) is ctx` 为 **True**。
- `invoke()` 终态键集 == schema 键集，**无** `"context"`。
- `stream(..., stream_mode="values")` 每条 payload **无** `"context"`。
- `context is None` ⇒ `type(state) is dict`；`context={}` / `0` / `""` ⇒ `_ContextState`（`isinstance(dict)` 且 `type(...) is not dict`）。

### 3.2 RunConfig 四字段实测

- `thread_id == "thread-1"` · `context == {"user": "u1"}` · `metadata == {"m": 1}` · `tags == ("t1",)`。
- 九字段顺序固定；`configurable` 独立且不含 `context`。

### 3.3 C25 作废 / alias 移除实测

- `add_node("a", fn, alias="model")` ⇒ `TypeError`（消息点名 `alias`）。
- 差分 D-142：freegraph **ERROR / TypeError**；上游 **OK / 静默忽略** ⇒ **STRICTER**。

### 3.4 差分 D-137…D-144

- 实际判词：D-137 SAME · D-138 DIFF · D-139 SAME · D-140 DIFF · D-141 SAME · D-142 STRICTER · D-143 SAME · D-144 SAME。
- 汇总：**SAME 5 / DIFF 2 / STRICTER 1**；失败 **0**。

### 3.5 T-1…T-7 追认

| # | 冻结面 | 处置 | 结果 |
|---|---|---|---|
| T-1 | B5F2 / B7F1 的 C4「节点入参是普通 `dict`」 | 只补注记：无 context ⇒ 精确 `dict`；有 context ⇒ 带只读 `.context` 的 `dict` 子类，映射语义不变 | 已落 `superstep-contract.md` §I-1 + 测试 docstring |
| T-2 | C25 / Q8 active 清单 / 宪法 / 立项书 / changelog | C25 正式作废、编号不复用；active = C1–C24 + C26–C27；宪法 1.16.0 | 已落宪法 + Q8 + 立项书 + changelog |
| T-3 | B6F1 `add_node(alias=)` / `_NodeRecord.alias` | 移除参数 / 字段 / 测试 / 合同；D-74 迁移到 B8F3 D-142 | 已落 B6F1 spec / plan / research / quickstart / contracts / checklist |
| T-4 | B2F2 门面 / 兼容矩阵 | 移除 alias 签名 / 矩阵行 | 已落 B2F2 spec / contracts / snapshot / data-model / research / checklist |
| T-5 | B22F1 图导出注记 | 删除「别名归 B8F3」；`name == id` 不变 | 已落 B22F1 spec / contract / data-model |
| T-6 | 验收脚本 / README / 测试的 C25 用例 | 移除 `case_node_alias` / C25 软断言行 / A10；C21 改硬断言 | 已落 demo / README / acceptance / test_acceptance_script |
| T-7 | B6F1 / B7F2 / B8F2 alias 交接 | 撤回 / 收缩为「stream 只用内部节点名」 | 已落 B6F1 / B7F2 / B8F2 / B8F1 文档 |

**发起者确认**：项目发起人（杨家成）于 **2026-11-20** 授权并追认上述 **T-1…T-7** 的冻结面修订；本次为 B8F3 的**唯一一次**追认额度。未追认前 MUST NOT 合入的约束按本记录解除。

### 3.6 零出站证据

- `acceptance.py` A3：**框架出站数 = 0**（freegraph 自身未发起任何连接）。
- 用户出站记录 0 条（记录在案，不判失败）。

## 4. 结论

- **PASS**：C21 / C22 运行期接线完成；alias / C25 已彻底移除；D-137…D-144 全部符合判词；demo / acceptance 全绿；框架零出站。
- 回归：US1 / US2 / US3 / US4 定向测试全绿；既有 C4 / C8 / 路由 / 流式 / 图导出未回归。

### 4.1 人工验收签署

- **验收结论**：**PASS**
- **发起者**：杨家成
- **签署日期**：**2026-11-20**
- **签署说明**：发起者确认「人工验收通过」，同意按本记录收尾、提交与推送。

## 5. 遗留问题

### 5.1 最终门禁（T040）

- 全量测试：`.venv/bin/python -m pytest -q tests/` ⇒ **1777 passed, 6 skipped in 133.23s**（0 failed）。
- 验收编排：`.venv/bin/python harness/demo/acceptance.py` ⇒ 退出码 **0**；自身硬断言 **13/13**，子脚本全 PASS。
- 本 feature 一键验收：`.venv/bin/python harness/verification/B8F3/acceptance.py` ⇒ 退出码 **0**；**A1…A7 全 PASS（7/7）**。
- `freegraph.runtime.__all__`：**23**（零新增公开符号）。
- 依赖 / 环境变量 / 零出站门禁：全量测试中的既有门禁全部通过；`import freegraph` 后无 `langchain*` / `langgraph*` / `langsmith*` 模块。
- `git diff --exit-code -- harness/demo/target.py pyproject.toml` ⇒ **CLEAN**。
- C25 active 引用复核：`src` / `tests` / `harness/demo` / `README.md` 无 `case_node_alias` / `alias=None` 的 **active** 代码或验收引用；剩余命中为历史墓碑或负向断言。

### 5.2 明确不在本 feature 内

- `context` 的 checkpoint 持久化 / 恢复归 **B14F1 / B15F1 / B16F1**（本 feature 明确不持久化）。
- C21 `context` 与 `Span.context` 的关系归 **B18F1 / B19F1**（MUST NOT 复用 `Span.context`）。
- `context_schema` 的声明式校验 / coerce 未实现（Out of Scope）。
- `Send.arg` 非 `dict` 不注入 `.context`（v1 边界，已登记）。
