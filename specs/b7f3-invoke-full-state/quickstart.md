# 快速验证指南（Quickstart）—— B7F3 · `invoke()` 返回完整状态

**Feature**: `B7F3` · **Spec**: [../spec.md](../spec.md) · **契约**: [../contracts/invoke-contract.md](../contracts/invoke-contract.md)
**用途**：本 feature 的**可复制**验证路径（**不是**实现指南；实现细节归 `tasks.md`）。

---

## 0. 前置

| 项 | 值 |
|---|---|
| Python | **3.11.16**（`.venv/bin/python`） |
| 工作目录 | 仓库根 `/home/ctyun/workspace/github/freegraph` |
| 安装 | `PYTHONPATH=src`（源码树运行；**不**需要安装） |
| 第三方运行时依赖 | **零**（`dependencies = []`） |
| 上游差分依赖 | `langgraph==1.2.11`（**仅**测试侧 · `differential` 依赖组）⇒ 缺席即 skip |
| 前置 feature | **B7F1**（调度内核）· **B7F2**（`compile()`）· **B10F1**（中断/恢复）· **B12F1**（并发）· **B13F1**（递归上限 / 静态断点） |

```bash
cd /home/ctyun/workspace/github/freegraph
```

---

## 1. 第 1 段 · 最小闭环（**完整状态**）

> 判据：**A1**（键集 == schema 全集）· **A2**（含初始 + 新增）· **SC-001 / SC-002 / SC-003**。

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import operator
from typing import Annotated, TypedDict
from freegraph.graph import START, END, StateGraph

class State(TypedDict):
    messages: Annotated[list, operator.add]   # 归约型 ⇒ 追加
    llm_calls: int                            # 无归约器 ⇒ 覆盖

def a(state):
    return {"messages": ["a"]}

def b(state):
    return {"messages": ["b"], "llm_calls": 2}

g = StateGraph(State)
g.add_node("a", a)
g.add_node("b", b)
g.add_edge(START, "a")
g.add_edge("a", "b")
g.add_edge("b", END)

out = g.compile().invoke({"messages": ["seed"], "llm_calls": 0})

print("键集      :", list(out))                 # 期望 ['messages', 'llm_calls']（schema 声明顺序）
print("messages :", out["messages"])            # 期望 ['seed', 'a', 'b']（初始 + 全部新增）
print("llm_calls:", out["llm_calls"])           # 期望 2（覆盖，不是累加）
assert list(out) == ["messages", "llm_calls"]
assert out["messages"] == ["seed", "a", "b"]
assert out["llm_calls"] == 2
print("✅ A1 / A2 通过")
PY
```

**再验「无值 key 补 `None`」**（判据 **SC-003** · 偏离 **X-1** 的正面断言）：

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import operator
from typing import Annotated, TypedDict
from freegraph.graph import START, END, StateGraph

class State(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int

def n(state):
    return {"messages": ["x"]}          # llm_calls 从未被写

g = StateGraph(State)
g.add_node("n", n)
g.add_edge(START, "n")
g.add_edge("n", END)

out = g.compile().invoke({"messages": []})
print("键集 :", list(out))
print("llm_calls:", out["llm_calls"])   # 期望 None（补齐）
assert "llm_calls" in out and out["llm_calls"] is None
print("✅ 无值 key 补齐通过")
PY
```

**再验「多源汇合（屏障）」**（判据 **SC-013** · **H-8** 的落点 · 静态多源边 ⇒ **不依赖 B8F1**）：

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import operator
from typing import Annotated, TypedDict
from freegraph.graph import START, END, StateGraph

class State(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int

def a(state): return {"messages": ["a"]}
def b(state): return {"messages": ["b"]}
def c(state): return {"messages": ["c"]}   # 屏障目标

g = StateGraph(State)
g.add_node("a", a); g.add_node("b", b); g.add_node("c", c)
g.add_edge(START, "a"); g.add_edge(START, "b")
g.add_edge(["a", "b"], "c")                   # 多源汇合（AND / 屏障）
g.add_edge("c", END)

out = g.compile().invoke({"messages": ["seed"]})
print("messages:", out["messages"])
assert out["messages"] == ["seed", "a", "b", "c"]   # 屏障目标在所有源之后
print("✅ 多源汇合（屏障）通过")
PY
```

---

## 2. 第 2 段 · 失败信号

### 2.1 未知 key ⇒ `InvalidUpdateError`（**点名违规 key**）

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import operator
from typing import Annotated, TypedDict
from freegraph.contracts import InvalidUpdateError
from freegraph.graph import START, END, StateGraph

class State(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int

def bad(state):
    return {"messages": ["x"], "typo_key": 1}      # schema 里没有 typo_key

g = StateGraph(State)
g.add_node("bad", bad)
g.add_edge(START, "bad")
g.add_edge("bad", END)

try:
    g.compile().invoke({"messages": []})
except InvalidUpdateError as exc:
    print("类型   :", type(exc).__name__)
    print("消息   :", exc)
    print("结构化 :", exc.invalid_keys)
    assert "typo_key" in str(exc)
    print("✅ 未知 key 报错通过")
else:
    raise SystemExit("❌ 期望 InvalidUpdateError")
PY
```

### 2.2 节点真异常 ⇒ **原类型 + 原消息**（不包装）

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import operator
from typing import Annotated, TypedDict
from freegraph.graph import START, END, StateGraph

class State(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int

class Boom(RuntimeError):
    pass

def boom(state):
    raise Boom("原始消息 payload")

g = StateGraph(State)
g.add_node("boom", boom)
g.add_edge(START, "boom")
g.add_edge("boom", END)

try:
    g.compile().invoke({"messages": []})
except Boom as exc:                      # 注意：断言的是 Boom，不是 RuntimeError 的包装
    print("类型 :", type(exc).__name__, "| 消息 :", exc)
    assert str(exc) == "原始消息 payload"
    print("✅ 异常原样传播通过")
else:
    raise SystemExit("❌ 期望 Boom")
PY
```

### 2.3 `recursion_limit`（dict 形态）⇒ `GraphRecursionError`（不包装）

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import operator
from typing import Annotated, TypedDict
from freegraph.contracts import GraphRecursionError
from freegraph.graph import START, END, StateGraph

class State(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int

def loop(state):
    return {"messages": ["loop"], "llm_calls": state.get("llm_calls", 0) + 1}

g = StateGraph(State)
g.add_node("loop", loop)
g.add_edge(START, "loop")
g.add_edge("loop", "loop")
g.add_edge("loop", END)

try:
    g.compile().invoke({"messages": [], "llm_calls": 0}, {"recursion_limit": 3})
except GraphRecursionError as exc:
    print("类型 :", type(exc).__name__, "| recursion_limit =", exc.recursion_limit)
    assert exc.recursion_limit == 3
    print("✅ recursion_limit 通过")
else:
    raise SystemExit("❌ 期望 GraphRecursionError")
PY
```

### 2.4 `RunConfig` 形态 + 并发度旋钮

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import operator
from typing import Annotated, TypedDict
from freegraph.graph import START, END, RunConfig, StateGraph

class State(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int

def n(state):
    return {"messages": ["x"]}

g = StateGraph(State)
g.add_node("n", n)
g.add_edge(START, "n")
g.add_edge("n", END)

out = g.compile().invoke({"messages": []}, RunConfig(max_concurrency=1))   # 旋钮由 L2 的 run_graph 读取（关键字优先 · config 兜底）
print("串行档 :", out)
print("✅ RunConfig 形态通过")
PY
```

---

## 3. 第 3 段 · 多会话隔离 + 挂起

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import operator, threading
from typing import Annotated, TypedDict
from freegraph.graph import START, END, StateGraph

class State(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int

def n(state):
    # ⚠️ **返回**部分**增量**（不是全量）—— 归约器（``operator.add``）负责**追加**
    # ⇒ ⇒ 返回全量会让归约器把已有内容**再追加一遍**。
    return {"messages": ["x"]}

g = StateGraph(State)
g.add_node("n", n)
g.add_edge(START, "n")
g.add_edge("n", END)
app = g.compile()

# ① 连续两次 ⇒ 不累积
out1 = app.invoke({"messages": ["a"]})
out2 = app.invoke({"messages": ["b"]})
print("run1 :", out1["messages"], "| run2 :", out2["messages"])
assert out2["messages"] == ["b", "x"]        # 不含 run1 的内容
print("✅ 连续两次不累积")

# ② 并发两次 ⇒ 不串扰
results = {}
def run(tag):
    results[tag] = app.invoke({"messages": [tag]})["messages"]
ts = [threading.Thread(target=run, args=(t,)) for t in ("p", "q")]
[t.start() for t in ts]; [t.join() for t in ts]
print("并发 :", results)
assert results["p"] == ["p", "x"] and results["q"] == ["q", "x"]
print("✅ 并发两次不串扰")
PY
```

**挂起 ⇒ `__interrupt__` 键**（判据 **SC-010**）：

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import operator
from typing import Annotated, TypedDict
from freegraph.graph import START, END, StateGraph, interrupt

class State(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int

def n(state):
    answer = interrupt("approve?")            # 挂起
    return {"messages": [f"answer={answer}"]}

g = StateGraph(State)
g.add_node("n", n)
g.add_edge(START, "n")
g.add_edge("n", END)
app = g.compile()

out = app.invoke({"messages": []})
print("键集        :", list(out))
print("__interrupt__:", out.get("__interrupt__"))
assert "__interrupt__" in out
first = out["__interrupt__"][0]
assert first.value == "approve?" and first.id
print("✅ 挂起结果通过（元素具备 .value / .id）")
PY
```

---

## 4. 第 4 段 · 验收脚本 + 门禁 + 全量回归

### 4.1 验收脚本集（**G29 的三个**：前两个**必须全绿**；第三个本 feature 后仍 `ENV_NOT_READY`）

```bash
PYTHONPATH=src .venv/bin/python harness/demo/graph_core.py; echo "rc=$?"   # 期望 rc=0（**脚本成功**）
PYTHONPATH=src .venv/bin/python harness/demo/agent_loop.py; echo "rc=$?"   # 期望 rc=0
PYTHONPATH=src .venv/bin/python harness/demo/visualization.py; echo "rc=$?"   # 期望 rc=2（环境未就绪）—— 其用例组归 B22F1 / B23F1 / B8F2
```

> ⚠️ `G29` 的验收脚本集是**三个**（`gate_G29_contract_carrier.py:60`）⇒ ⇒ 本 feature 只承诺
> **`graph_core.py` / `agent_loop.py` 全绿** ⇒ ⇒ ⇒ `visualization.py` 仍是 `ENV_NOT_READY`
> ⇒ ⇒ ⇒ **MUST NOT** 被读成「三个脚本全绿」。

> ⚠️ `graph_core.py` 的就绪探针（`_invoke_ready()` · `harness/demo/graph_core.py:555-571`）
> 以 **`except NotImplementedError` ⇒ 未就绪** 判定 ⇒ `invoke` 交付后 ⇒ **正常跑全部用例**
> ⇒ ⇒ 任何**非** `NotImplementedError` 的失败 ⇒ **G29 判 FAIL** ⇒ ⇒ **必须全绿**。

### 4.2 一键验收脚本（本 feature 新增）

```bash
PYTHONPATH=src .venv/bin/python harness/verification/B7F3/acceptance.py; echo "rc=$?"   # 期望 rc=0
```

### 4.3 差分探针（上游缺席即 skip）

```bash
.venv/bin/python harness/scripts/diff_parity.py -k D-9 ; echo "rc=$?"   # 期望 rc=0（全部符合判词）
.venv/bin/python -m pytest tests/differential/test_parity_probe.py -q
```

### 4.4 全量回归 + 门禁

```bash
.venv/bin/python -m pytest tests/ -ra -q
.venv/bin/python harness/scripts/gates/gate_G21_dependencies.py --project pyproject.toml
.venv/bin/python harness/scripts/gates/gate_G23_licenses.py
.venv/bin/python harness/scripts/gates/gate_G24_config_layer.py
.venv/bin/python harness/scripts/gates/gate_G25_import_graph.py --root .
.venv/bin/python harness/scripts/gates/gate_G26_network_static.py
.venv/bin/python harness/scripts/gates/gate_G27_zero_egress.py
.venv/bin/python harness/scripts/gates/gate_G22_isolated_env.py   # 本 feature 改了这个门禁 ⇒ MUST 跑
unshare --net --map-root-user .venv/bin/python harness/scripts/gates/gate_G28_offline_equiv.py --root .   # 断网等价性 · 须在已断网环境内跑（CI 档执行）
.venv/bin/python harness/scripts/gates/gate_G29_contract_carrier.py
.venv/bin/python harness/scripts/gates/gate_G30_attribution.py --root .
```

> ⚠️ **仓库无 ruff / mypy 配置**（`pyproject.toml` 无 `[tool.ruff]` / `[tool.mypy]` · CI 无 lint /
> typecheck 步骤）⇒ 验证手段 = **pytest + 门禁脚本**（不臆造 lint 命令）。
> ⚠️ **G30 有 8 条 B7F2 之前就存在的既有违规**（tracked 文档问题）⇒ 本 feature **MUST NOT 新增**。

### 4.5 只读基准的 diff 断言

```bash
git diff --stat HEAD -- harness/demo/target.py     # 期望：空（只读基准 MUST NOT 改动）
```

---

## 5. 第 5 段 · 人工验证（**两轮**）

| 轮次 | 模型 | 环境 | 证据落点 |
|---|---|---|---|
| **CI 轮** | **fake**（猴补 `langchain.chat_models.init_chat_model` 注入 · 立项书 §9.2） | 验收环境 + socket 监测夹具 | `harness/verification/B7F3/manual-verification.md` §3 |
| **人工轮** | **真实模型** `claude-sonnet-4-6` | 干净环境（拦截列表允许「模型厂商端点」一条） | 同上 §3 |

> ⚠️ 真实轮的**用户出站**记录在案、**不判失败**；**框架零出站**断言仍须通过。
> ⚠️ 若真实轮因环境不具备（无凭据 / 无外网）⇒ MUST 按宪法 v1.6.0 登记为**环境偏离**
> ⇒ **MUST NOT** 用「未验证」替代「已登记的环境偏离」。

### 5.1 人工验证记录的五段式

`harness/verification/B7F3/manual-verification.md` MUST 含（宪法原则 V · `harness/verification/README.md:73-83`）：

| # | 段 | 要求 |
|---|---|---|
| 1 | **环境** | Python 版本 / 平台 / 包版本 / 依赖闭包实测结果 |
| 2 | **步骤** | 照本文件第 1–4 节的可复制命令 |
| 3 | **实际输出** | 粘贴**真实**输出（非「符合预期」） |
| 4 | **结论** | 逐条对照 SC-001…SC-020；**不适用**的子项须**显式记一句** |
| 5 | **遗留问题** | 已知限制与其归属 feature |

> ⚠️ **§7（追认段）** MUST 含**破冻结面的发起者追认文字**（L1 协议 `invoke` 的 `input` + `config` 两处
> 注解放宽 —— **同一次**登记 / 回溯修订 / 追认）⇒ **未追认前 MUST NOT 合入**（**SC-019**）。

---

## 6. 本 guide **不**覆盖的范围（明确不做）

| 项 | 归属 |
|---|---|
| `stream()` / `ainvoke()` | **B8F2** / v2 |
| 条件边**路由求值** | **B8F1**（同一执行路径上补齐） |
| `get_graph()` / `draw_mermaid_png()` | **B22F1** / **B23F1**（**MUST 先于** `invoke` 就绪） |
| checkpoint 落盘 / `MemorySaver` | **B14F1**（本 feature 只**透传** `checkpointer`） |
| `get_state()` / `update_state()` | **B15F1** / **B16F1** |
| 节点返回 `Command` 的处理 | **B9F1**（L2 已交付） |
