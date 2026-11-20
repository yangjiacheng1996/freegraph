# Quickstart：B8F3 `context` 独立通道（alias 已移除）

**Feature**: `B8F3` · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**适用环境**: CPython 3.11+ · 仓库 `.venv` · 零第三方运行时依赖 · 零出站

> 本文件是**验证 / 运行指南**，不是实现说明；具体实现任务见后续 `tasks.md`。

---

## 0. 前置检查

```bash
cd /home/ctyun/workspace/github/freegraph
.venv/bin/python -V
.venv/bin/python -m pytest --collect-only -q | tail -3
```

预期：
- Python `3.11.x`。
- 收集数 = 既有基线（2026-11-20 为 **1742**；以实施时实测为准）。

---

## 1. `context` 公开行为（facade）

```bash
.venv/bin/python -m pytest tests/facade/test_context_channel.py -q
```

预期：
- 节点内 `getattr(state, "context", None)` == `RunConfig.context`。
- `invoke()` 返回 dict 键集 == schema 键集，**不含** `"context"`。
- `stream(..., stream_mode="values")` 的每条 payload **不含** `"context"`。
- `RunConfig(thread_id=..., context=..., metadata=..., tags=...)` 四字段可读；
  `tags` 为 `tuple`。
- `RunConfig.configurable` 独立；无注入的 `"configurable"` 键。
- `invoke(..., context=...)` / `stream(..., context=...)` ⇒ `TypeError`（未新增关键字）。

---

## 2. 节点视图与 C4 回归（runtime）

```bash
.venv/bin/python -m pytest tests/runtime/test_context_channel.py -q
```

预期：
- `context is None` ⇒ 节点入参 `type(state) is dict`（C4 / I-1 逐字不变）。
- `context is not None` ⇒ `isinstance(state, dict)` 为真、`type(state) is dict` 为假；
  `dict(state)` == 稀疏状态；`"context" not in state`。
- `.context` 只读；未知属性 ⇒ `AttributeError`。
- 路由 fresh 视图无 `context` 键 / `.context` 属性。
- `Send.arg` 为 `dict` ⇒ 包装；非 `dict` ⇒ 原样（不注入 `.context`）。
- 连续两次运行 context 不泄漏。

---

## 3. alias 移除

```bash
.venv/bin/python -m pytest tests/facade/test_stategraph_builder.py -q
.venv/bin/python -m pytest tests/runtime/test_acceptance_script.py -q
```

预期：
- `add_node("agent", fn, alias="model")` ⇒ `TypeError`（消息点名 `alias`）。
- `_NodeRecord` 无 `alias` 字段；`defer` / `metadata` / 单 callable 仍正常。
- `harness/demo/README.md` 不再包含 C25 软断言行；`graph_core.py` 无 `case_node_alias`。
- `C1–C25` 描述改为 `C1–C24`；C25 在 Q8 / 立项书 / 宪法中是**墓碑**状态，不是 active 契约。

### 3.1 手工检查（示例）

```bash
.venv/bin/python - <<'PY'
from typing import TypedDict
from freegraph.graph import StateGraph, START, END

class S(TypedDict, total=False):
    x: int

g = StateGraph(S)
g.add_node("agent", lambda s: {"x": 1})
g.add_edge(START, "agent")
g.add_edge("agent", END)
app = g.compile()

try:
    g.add_node("other", lambda s: {}, alias="model")
except TypeError as exc:
    print("TypeError:", exc)
else:
    raise AssertionError("alias 关键字未被拒绝")

print(app.invoke({"x": 0}))
print([(n.id, n.name) for n in app.get_graph().nodes.values()])
PY
```

预期：
- 打印 `TypeError`，消息含 `alias`。
- `invoke` 终态不含 `context`；图节点名为 `agent`（无 `model`）。

---

## 4. 差分场景（上游缺席即 skip）

```bash
.venv/bin/python -m pytest tests/differential/ -q -k "D-137 or D-138 or D-139 or D-140 or D-141 or D-142 or D-143 or D-144"
```

预期：
- `langgraph 1.2.11` 存在 ⇒ 真跑；缺席 ⇒ skip。
- 判词：SAME 5 / DIFF 2 / STRICTER 1（见 [contracts/upstream-parity.md](./contracts/upstream-parity.md) §3）。
- D-142：freegraph `TypeError`；上游静默忽略。

---

## 5. 演示 / 验收脚本

```bash
.venv/bin/python harness/demo/graph_core.py
.venv/bin/python harness/demo/acceptance.py
```

预期：
- `graph_core.py` 退出码 `0`；C21 为**硬断言**（无 `soft(...)`）；无 C25 / `case_node_alias`。
- `acceptance.py` core 套件通过；**固定脚本（`harness/demo/target.py`）的 fake 模型双跑属 M2 / B25F1 验收路径，不作为 B8F3 的独立判据**（见 spec SC-009）。
- 输出中不再出现 `C25` / `alias` 的待办提示。

---

## 6. 全量回归 + 门禁

```bash
.venv/bin/python -m pytest -q
```

预期：
- 除预登记红点（已按 RD-01…RD-12 修复）外零失败。
- `freegraph.runtime.__all__` 仍 **23**。
- 无 `langchain*` / `langgraph*` / `langsmith` import；无环境变量读取。
- `target.py` 零改动。

零出站（人工轮）：按宪法原则 V 的 socket 观测夹具记录；只对「框架出站」断言为 0；
用户节点 / 模型端点出站记录在案但不判失败。

---

## 7. 人工验证记录

```bash
mkdir -p harness/verification/B8F3
```

记录文件：`harness/verification/B8F3/manual-verification.md`，必须包含：

1. 验证环境（Python / OS / 上游版本 / 无 `LANGSMITH_*`）。
2. `context` 实测输出（节点读到值；`invoke` / `values` 无 context）。
3. `RunConfig` 四字段实测输出。
4. C25 正式作废 / alias 移除实测（`TypeError` / 无 alias 字段 / 无 C25 active 引用 / 宪法 1.16.0 + changelog）。
5. 差分 D-137…D-144 结果。
6. 零出站证据（框架出站 = 0）。
7. **T-1…T-7 追认文字**（唯一一次追认）。
8. 遗留问题 / 结论。

> 人工门禁未完成前，本 feature **MUST NOT** 宣布完成（宪法原则 V）。

---

## 8. 常见失败信号

| 现象 | 原因 | 处置 |
|---|---|---|
| 无 context 时 `type(state) is dict` 失败 | 无条件包装了节点入参 | 只在 `get_context() is not None` 时包装 |
| `context` 出现在 `invoke` / `values` | 把 context 写进状态 / channels | 只经 `_ContextState` 暴露；不改 `_full_state` |
| 路由视图出现 `.context` | 包装了 route view | 只包装 `_node_input`；route view 保持普通 dict |
| `context` 跨运行泄漏 | 未复原 contextvar token | `bind_context` 用 `finally` + token.reset |
| `Send.arg` 非 dict 被包装 | 无条件包装 fan-out 入参 | 仅 `isinstance(arg, dict)` 时包装 |
| `add_node(alias=...)` 未报错 | 保留了 no-op 关键字 | 删除 `alias` 参数；让 Python 抛 `TypeError` |
| C25 悬空引用导致测试红 | demo / README / acceptance 未同步 | 按 T022 / T023 / T024 清理 |
