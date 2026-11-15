# Quickstart: B11F1 · `Send` 的动态 fan-out / map-reduce

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-11-14

> **本文件是**验证指南（**可运行的场景**）⇒ **不含**实现代码、不含完整测试套件。
> ⚠️ **全部场景用「手写图规格」**（`GraphSpec` + `NodeSpec` + `run_super_steps`）⇒
> **不经由** `StateGraph` / `compile()` / `invoke()` ⇒ ⇒ **本 feature 可独立验收**
> （FR-017 · 原则 III 的「验收契约」在 B6F1 / B7F2 / B7F3 落地前**不可跑** ⇒ 见 §0.3）。

---

## 0. 前置条件

### 0.1 环境准备（**一次性 · 四条命令** · 跨平台）

```bash
# ① 建 venv —— ⚠️ 必做：uv pip install 在无活动虚拟环境时报
#    "error: No virtual environment found" 并以退出码 2 失败（B3F1 的既有结论）
uv venv .venv
# ② 开发期依赖组（pytest + packaging）—— PEP 735 · 不进发行包 / 不进 Requires-Dist
uv pip install --python .venv --group dev
# ③ 本 feature 包（editable）
uv pip install --python .venv --no-deps -e .
# ④（**可选**）覆盖率工具 —— **不进依赖声明**（v1.0 依赖面为零）⇒ 开发期临时安装
uv pip install --python .venv coverage
```

### 0.2 **不需要**上游（**除差分闸口外**）

内核路径 **零** `langchain*` / `langgraph*` / `langsmith` 导入 ⇒ **零出站** · **零环境变量**（FR-013 / SC-021）。
上游**仅**在差分场景里用到 ⇒ **缺席即 skip**（不是失败）。

### 0.3 闸口与判据的对应

| 闸口 | 场景（本文的章节） | 判据 |
|---|---|---|
| **A1** map-reduce 模式可运行 | §1 · §2 | SC-001 / SC-002 |
| **A2** 产出按归约器汇合 | §2 | SC-002 |
| **A3** 目标不存在 ⇒ 明确报错 | §4 | SC-003 |
| 回归不破 | §3 | SC-004 |
| 混合调度可判定 | §5 | SC-005 |
| 上游对照 | §9 | SC-019 |

> ⚠️ **验收脚本的 C18 用例当前**不可跑**（`harness/demo/graph_core.py` ⇒
> `NotImplementedError: add_node 尚未接线（由 B6F1 交付）`）⇒ ⇒ 本 feature 的等价验证
> 在 §1（**手写图规格**）里 ⇒ **同一形态 · 同一断言** ⇒ 待 B6F1 / B7F2 / B7F3 落地后
> 验收脚本自然转绿（**人工验证记录**里如实登记）。

---

## 1. ★ map-reduce 模式可运行（**验收判据 A1** · SC-001 · I-1 / I-2 / I-3）

```python
# tests/runtime/test_send_fanout.py（**示意**：实现阶段落盘）
from freegraph.contracts import Send
from freegraph.runtime import GraphSpec, NodeSpec, run_super_steps
from freegraph.runtime.channel import BinaryOperatorAggregate, LastValue

seen: list[dict] = []


def fanout(state):
    return [Send("worker", {"n": 1}), Send("worker", {"n": 2})]


def worker(state):
    seen.append(dict(state))
    return {"messages": [f"w{state['n']}"]}


spec = GraphSpec(
    channels={
        "messages": BinaryOperatorAggregate(lambda a, b: a + b),
        "count": LastValue(),
    },
    nodes={
        "fan": NodeSpec(subscribes=("count",), run=fanout),
        "worker": NodeSpec(subscribes=("count",), run=worker),
    },
    edges={"__start__": ("fan",), "fan": ("worker",), "worker": ("__end__",)},
)

result = run_super_steps(spec)

assert len(seen) == 2, seen                      # 执行次数 == Send 条数
assert seen[0] == {"n": 1} and seen[1] == {"n": 2}   # 各次入参逐字正确
assert sorted(result.state["messages"]) == ["w1", "w2"]
```

**期望**：目标被调用 **2** 次 · 入参分别是 `{"n": 1}` 与 `{"n": 2}` · 汇合通道 == `["w1","w2"]`。

---

## 2. 产出按归约器汇合 + **可复现**（**验收判据 A2** · SC-002 / SC-009 · I-7）

```python
# 同一份规格重复跑 ≥ 3 次 ⇒ 最终状态与执行序列逐项相等
runs = [run_super_steps(spec) for _ in range(3)]
assert runs[0].state == runs[1].state == runs[2].state
assert runs[0].executed == runs[1].executed == runs[2].executed
```

**期望**：三次**逐项相等**（⇒ 归并顺序**确定** ⇒ **上游任务序**：标准触发任务按目标节点名序 → fan-out 任务按产生者任务序 · `Send` 序号；标准任务全部在前）。

---

## 3. 没有 `Send` 时行为**一字不变**（SC-004 · 回归）

```bash
# 既有套件**零改动**全绿（绿基线：1184 passed / 4 skipped）
.venv/bin/python -m pytest -q
```

**期望**：**1184 + 新增用例** 全部通过 ⇒ 既有断言**一条不删**。

---

## 4. ★ 目标节点不存在 ⇒ **明确报错**（**验收判据 A3** · SC-003 / I-14 · V-19）

```python
import pytest

from freegraph.contracts import Send


def bad(state):
    return [Send("no-such-node", {"n": 1})]


spec = GraphSpec(
    channels={"count": LastValue()},
    nodes={
        "fan": NodeSpec(subscribes=("count",), run=bad),
        "worker": NodeSpec(subscribes=("count",), run=lambda s: {"count": 1}),
    },
    edges={"__start__": ("fan",), "fan": ("worker",), "worker": ("__end__",)},
)

with pytest.raises(ValueError) as excinfo:
    run_super_steps(spec)

message = str(excinfo.value)
assert "no-such-node" in message      # A3：消息指明目标节点名
assert "fan" in message                # 澄清轮 Q3 = A：同时点名产生者
```

**期望**：**显式失败**（`ValueError`）· 消息**同时点名产生者与目标** ⇒ **不静默丢弃**该 `Send`。

---

## 5. 混合调度可判定（SC-005 · I-5 · 裁定 5 的**按载体分列表**）

```python
# 载体 B（节点直接返回 list[Send]）+ 同一条静态边 ⇒ 标准触发被抑制 · 只被 Send 调用（Send 胜出）
calls: list[str] = []


def fan(state):
    return [Send("worker", {"n": 1}), Send("worker", {"n": 2})]


def worker(state):
    calls.append("custom")
    return {}


spec = GraphSpec(
    channels={"count": LastValue()},
    nodes={
        "fan": NodeSpec(subscribes=("count",), run=fan),
        "worker": NodeSpec(subscribes=("count",), run=worker),
    },
    edges={"__start__": ("fan",), "fan": ("worker",), "worker": ("__end__",)},
)
run_super_steps(spec)
assert calls == ["custom", "custom"]     # 2 次 · 全部自定义入参 · 无标准入参那次
```

⚠️ **载体 A（`Command(goto=[Send(…)])`）在同一场景下是「叠加」**（标准入参那次**照常发生**）
⇒ ⇒ **两条载体口径不同** ⇒ 迁移写法时**必须复查调用次数**（**DR-03**）。
⚠️ **多源屏障组（B7F4）不抑制**：若该目标同时是多源屏障组的目标，屏障组的**标准入参那次照常发生**
（**屏障语义优先** · FR-006 / SC-005 的例外）。

---

## 6. 一次返回里「既派发又写入」（上游同款 · SC-008 · I-6 · P-12）

```python
from freegraph.contracts import Command, Send
from freegraph.runtime import GraphSpec, NodeSpec, run_super_steps
from freegraph.runtime.channel import BinaryOperatorAggregate


def fan(state):
    return Command(
        goto=[Send("worker", {"n": 1}), Send("worker", {"n": 2})],
        update={"messages": ["from-fan"]},
    )


def worker(state):
    return {"messages": [f"w{state['n']}"]}


spec = GraphSpec(
    channels={"messages": BinaryOperatorAggregate(lambda a, b: a + b)},
    nodes={
        "fan": NodeSpec(subscribes=("messages",), run=fan),
        "worker": NodeSpec(subscribes=("messages",), run=worker),
    },
    edges={"__start__": ("fan",), "worker": ("__end__",)},
)
result = run_super_steps(spec)

assert sorted(result.state["messages"]) == ["from-fan", "w1", "w2"]
```

**期望**：**写入生效**（`from-fan`）与**派发生效**（`w1` / `w2`）两条断言**同时**成立（互不吞并）。

---

## 7. 失败信号与边界形态（SC-012 / SC-013 · V-15…V-21）

| 输入 | 期望 |
|---|---|
| 节点返回 `[]` | `TypeError`（空列表**无歧义**） |
| 节点返回 `[Send("w", {}), {"x": 1}]` | `TypeError`（两种列表语义**不得混谈**） |
| `Command(goto=[123])` | `TypeError`（`goto` 槽位的非法元素） |
| `Send(123, {})` | `TypeError`（`node` 类型非法） |
| `Send("", {})` | `ValueError`（空串） |
| `Send("__parent__", {})` | `NotImplementedError`（点名 `__parent__` + 「子图属 v2 能力」） |
| `Send("__start__", {})` / `Send("__end__", {})` | `ValueError`（哨兵不是可调用的节点） |

---

## 8. 结构纪律（SC-014 / SC-015 · 层纪律 + 导出面）

```bash
# ① L1 符号面 == 21（含 Send）· 门面 == 7 · runtime.__all__ == 23
.venv/bin/python -c "
import freegraph.contracts as c, freegraph.graph as g, freegraph.runtime as r
assert len(c.__all__) == 21 and 'Send' in c.__all__
assert len(g.__all__) == 7 and g.Send is c.Send
assert len(r.__all__) == 23
"
# ② 门禁：依赖 / 许可 / 导入图 / 出站 / 署名头
.venv/bin/python harness/scripts/gates/gate_G21_dependencies.py
.venv/bin/python harness/scripts/gates/gate_G25_import_graph.py
.venv/bin/python harness/scripts/gates/gate_G30_attribution.py
```

---

## 9. ★ 差分探针（**上游同款**的唯一可自动化判据 · SC-019 · D-29…D-37）

```bash
# 上游已安装 ⇒ 真跑；上游缺席 ⇒ skip（非失败）
.venv/bin/python harness/scripts/diff_parity.py -v
# 或只跑本 feature 的场景
.venv/bin/python harness/scripts/diff_parity.py -k D-29
```

**期望**：**D-29 / D-30 / D-31 / D-33 / D-34 / D-36** 判词 **SAME**（**逐字一致**）·
**D-32** 判词 **STRICTER**（上游不抛错 · freegraph 抛错）· **D-35 / D-37** 判词 **DIFF**
（上游无该形态 ⇒ 两侧各自断言）⇒ ⇒ **MUST NOT** 偶发红（写入顺序**确定**：上游
`apply_writes` 按任务路径排序 ⇒ **D-31 断言逐项顺序** · 实测 **E-11**）。

---

## 10. 人工验证（原则 V）+ **发起者追认**（SC-017 / SC-020）

```text
harness/verification/B11F1/manual-verification.md   ← 五段式 + 来源覆盖表（100%）
harness/verification/B11F1/acceptance.py             ← 机械层一键验收
```

⚠️ **追认文字 MUST 落在同一文件**：偏离登记 **X-1 / X-3 / X-6** + 破冻结面 **F-1…F-14**
（**未追认前 MUST NOT 合入** · 宪法 v1.8.0）。
⚠️ **DR-03 MUST 在人工验证记录里显著写明**（两条载体的调用次数口径差异）。

---

## 11. 已知限制（**如实登记** · 勿当缺陷）

| # | 限制 | 归属 |
|---|---|---|
| **DR-01** | fan-out 任务的中断 id 按**节点名**派生 ⇒ 同节点 N 次调用可能**同 id** | **本 feature 修复**（T027/T034：任务级现场键 → TaskId；**T093/T095**：持久化 `task_id` = 标准节点名 / fan-out `节点名:TaskId`）· 与 **B10F1** 恢复口径对齐 |
| **DR-02** | fan-out 载荷**不落盘** ⇒ checkpoint 恢复后未执行的 fan-out 丢失 | **B14F1** |
| **DR-03** | 载体 A / 载体 B 的「与静态边并存」口径**不同** | 已写死（裁定 5）· 文档须显著说明 |
| **DR-04** | `Send` 的可变性 / 哈希性 / `timeout` 与上游不同 | **上游对齐批次 P3-8**（偏离 **X-5**） |
| **DR-05** | 条件边返回 `Send` 的运行期语义**未实现** | **B8F1** |
| **DR-06** | 静态中断点 × fan-out 的交互**未定** | **B13F1** |
| — | 验收脚本的 C18 用例**仍不可跑**（构建器未接线） | **B6F1 / B7F2 / B7F3** |
