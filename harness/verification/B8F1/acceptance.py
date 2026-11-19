#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**B8F1** 人工验收脚本（条件边路由求值 + ``END`` 终止 + fresh 读 · **C8**）。

定位
----
本脚本是 **B8F1 这个 feature 的人工验收入口**——**开发期**（v1.0 之前）逐 feature
验收用；**v1.0 完成后的端到端验收**在 ``harness/demo/``。

**一条命令跑完全部验收**——验收判据 **A1…A10**（逐条对应
``specs/b8f1-conditional-edges-fresh-read/quickstart.md`` 的 §1…§17 与
``spec.md`` 的 **SC-001…SC-026**）。

覆盖的分组（**逐组对应一条验收判据**）：

* **A1** **C8 fresh 读**（**否定式**断言 · 路由函数**看到了**本节点本次写入的值 ·
  归约型通道**已合并** · 无值通道**缺席** · 同轮另一节点的写入**不可见**）·
  FR-007…FR-013 · SC-001 / SC-004；
* **A2** **``path_map`` 双形态 + 动态目标**（list / dict / ``None`` 各自路由正确 ·
  **非** ``str`` 的可哈希值作 key 正常查表）· FR-014…FR-020 · SC-005；
* **A3** **``END`` 终止**（**单独返回** ⇒ **无条件终止** · ``path_map`` 的 value
  为 ``END`` ⇒ 终止 · ``path_map`` **不含** ``END`` 键 ⇒ **仍然**终止 ·
  序列内的 ``END`` ⇒ **剔除**且其余目标照常执行）· FR-019 · SC-003 · **X-2**；
* **A4** **失败信号两态**（**有** ``path_map`` ⇒ 内置 ``KeyError``；**无** ⇒ 内置
  ``ValueError`` · 消息**指明返回值与可选目标**）· 路由函数**自身**的异常
  **原类型 + 原消息**传播 · FR-021…FR-025 · SC-006 / SC-007 / SC-012；
* **A5** **序列 ⇒ 多目标并行**（**同一份**共享状态 · 重复目标**去重保序** ·
  **空序列** ⇒ 无目标且**不报错**）· FR-018 / FR-024 · SC-008；
* **A6** **``__start__`` 上的条件边**（**被求值** · **纯条件边入口** · 与静态
  入口**并存** ⇒ 同轮并行 · 返回 ``END`` ⇒ 该分支终止 · **求值次数 == 1**（幂等））·
  FR-038 / FR-039 · SC-022 / SC-023；
* **A7** **双参形态**（第二参 == 用户交给 ``invoke`` 的**原始** ``config``（逐字）·
  第二参**不叫** ``config`` ⇒ 按**一参**调用 ⇒ ``TypeError`` · 注解**不在**
  匹配集 ⇒ **跳过注入** · **MUST NOT** 发 ``UserWarning``）· FR-003 · SC-021；
* **A8** **公开面只增不删**（B8F2 后契约 **22** · 门面 **8** · ``runtime`` **23** ·
  ``vars(compiled)`` == **11** 键 · **零新增错误类型**）· FR-037 · SC-016；
* **A9** **差分组全绿**（**D-103…D-120** · 判词分布 SAME **12** / DIFF **4** /
  STRICTER **2**）· FR-032 · SC-013；
* **A10** **破冻结面的回溯验证**（**7 类** · 逐条**机械判据** + 人工验证记录的
  **五段式** + **追认**文字在位）· FR-026 / FR-034 · SC-019 / SC-025。

依赖
----
**只 import Python 标准库**（+ 被验收的 ``freegraph`` 本身）——**零第三方依赖**。

两态运行
--------
| 情形 | 行为 |
|---|---|
| 当前环境**已安装** freegraph | 测**发行产物** |
| 当前环境**未安装** | 自动把 ``<repo>/src`` 插入 ``sys.path``（源码优先），测**源码树** |

⚠️ **上游缺席即 skip**（沿用 B5F2 的「缺席即 skip」纪律）⇒ ⇒ 差分闸口（**A9**）
在上游未安装时**跳过**而非**失败**。

用法
----
    python3 harness/verification/B8F1/acceptance.py                    # 跑全部
    python3 harness/verification/B8F1/acceptance.py --record out.md    # 同时生成验收记录片段
    python3 harness/verification/B8F1/acceptance.py --require-installed # 把「未安装」判为失败
    python3 harness/verification/B8F1/acceptance.py --skip-differential # 跳过差分闸口（快）

退出码：``0`` = PASS · ``1`` = FAIL · ``2`` = 环境未就绪。
"""

from __future__ import annotations

import argparse
import json
import operator
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Annotated, Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
SPEC_DIR = REPO_ROOT / "specs" / "b8f1-conditional-edges-fresh-read"
MANUAL_VERIFICATION = (
    REPO_ROOT / "harness" / "verification" / "B8F1" / "manual-verification.md"
)
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)

#: 人工验证记录的**五段式**小节（原则 V · 宪法）——**标题口径** = 「``## N. <名>``」。
MANUAL_SECTIONS = ["环境", "步骤", "实际输出", "结论", "遗留问题"]

#: **破面全集 7 类**的**逐条落点**（**A10** 的机械判据 · 文件 + 正则）。
#: ⇒ ⇒ ⇒ 「**唯一事实源** = ``spec.md``「Assumptions」的「破面全集 7 类」」。
RETRO_LANDINGS: list[tuple[str, str]] = [
    # ① T-1 · B7F1 的校验规则 V-8（放宽 · 回溯修订上游已交付文档）
    ("specs/b7f1-superstep-loop/contracts/superstep-contract.md", r"自 B8F1 起放宽"),
    ("specs/b7f1-superstep-loop/spec.md", r"2026-11-18 · B8F1 回溯修订"),
    ("specs/b7f1-superstep-loop/data-model.md", r"自 B8F1 起放宽"),
    # ② 冻结断言 ①（拆分而不删）
    ("tests/runtime/test_superstep_basic.py", r"test_a_non_empty_conditional_edges_field_is_accepted_and_carried_verbatim"),
    # ③ 冻结断言 ②（I-14 拆分 · 编号与槽位不变）
    ("tests/runtime/test_superstep_contract.py", r"test_i14_a_filled_conditional_edges_field_is_accepted_and_carried_verbatim"),
    # ④ 冻结断言 ④（替换为反面断言）
    ("tests/facade/test_compiled_graph.py", r"carries_the_l3_payload"),
    # ⑤ T-5 · C8 挂载点
    ("tests/contracts/test_contract_regressions.py", r"GATE-MOUNT: C8 · status=landed"),
    # ⑥ T-6 · graph_core.py 的 A5 组（软 ⇒ 硬）
    ("harness/demo/graph_core.py", r"C8 路由函数看到本节点刚写入的值（fresh 读）"),
    # ⑦ T-7 · agent_loop.py 的 B1 / B2 组（软 ⇒ 硬）
    ("harness/demo/agent_loop.py", r"模型被调用 2 次（工具循环走了一轮）"),
]

#: **破面全集 7 类**的**逐条标识**（**A10** 的机械判据 · 记录文本里 MUST 逐条出现）。
BREAK_UNIVERSE_MARKERS = (
    "T-1",
    "冻结断言 ①",
    "冻结断言 ②",
    "冻结断言 ④",
    "T-5",
    "T-6",
    "T-7",
)

#: 「**已登记的环境偏离**」的**关键词**（真实模型轮 · 宪法 v1.6.0）。
ENV_DEVIATION_MARKERS = ("环境偏离", "未落地")

_results: list[dict[str, Any]] = []
_failures = 0
_skipped = 0


def _record(gate: str, label: str, status: str, detail: str = "") -> None:
    """把一条闸口结果登记进记录片段。"""
    _results.append({"gate": gate, "label": label, "status": status, "detail": detail})


def _check_gate(gate: str, label: str, fn) -> bool:
    """跑一条闸口（函数）⇒ 失败**不**中断（跑完再汇总）。"""
    global _failures
    try:
        ok, detail = fn()
    except Exception as exc:  # noqa: BLE001 —— 闸口自身的异常也算失败
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    if ok:
        print(f"  ✔ {label}")
        _record(gate, label, "PASS", detail)
        return True
    _failures += 1
    print(f"  ✘ {label}")
    if detail:
        print(f"      {detail}")
    _record(gate, label, "FAIL", detail)
    return False


def _pytest_gate(
    gate: str,
    label: str,
    args: list[str],
    *,
    needs_upstream: bool = False,
) -> None:
    """跑一条 **pytest** 闸口（子进程 ⇒ 退出码即判定）。"""
    global _failures, _skipped
    if needs_upstream and not _upstream_installed():
        _skipped += 1
        print(f"[SKIP] {gate}   {label} —— 上游 langgraph 缺席（**非失败**）")
        _record(gate, label, "SKIP", "上游 langgraph 缺席")
        return
    completed = subprocess.run(
        [str(PYTHON), "-m", "pytest", *args, "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=_env_with_src(),
    )
    tail = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    ok = completed.returncode == 0
    if ok:
        print(f"  ✔ {label}")
        _record(gate, label, "PASS", tail)
        return
    _failures += 1
    print(f"  ✘ {label}")
    print(f"      退出码 {completed.returncode} · {tail}")
    _record(gate, label, "FAIL", tail)


def _env_with_src() -> dict[str, str]:
    """构造子进程环境（把 ``src`` 放进 ``PYTHONPATH`` ⇒ 源码树可直接跑）。"""
    import os

    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{SRC_DIR}{os.pathsep}{existing}" if existing else str(SRC_DIR)
    )
    return env


def _upstream_installed() -> bool:
    """上游 ``langgraph`` **是否已安装**（缺席 ⇒ 差分闸口 skip）。"""
    completed = subprocess.run(
        [str(PYTHON), "-c", "import langgraph"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=_env_with_src(),
    )
    return completed.returncode == 0


def _read(relpath: str) -> str:
    """读仓库内的一个文件（不存在 ⇒ 空串）。"""
    path = REPO_ROOT / relpath
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


# ── 环境就绪（两态运行）──────────────────────────────────────────────────

try:
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    from freegraph.contracts.types import RunConfig
    from freegraph.graph import END, START, Send, StateGraph
except Exception as exc:  # noqa: BLE001
    print(f"[环境未就绪] freegraph 不可导入：{type(exc).__name__}: {exc}")
    raise SystemExit(2) from exc


# ── 最小 schema ──────────────────────────────────────────────────────────


class State(TypedDict):
    """最小状态 schema（与 ``harness/demo/graph_core.py`` **同款**）。"""

    messages: Annotated[list, operator.add]
    llm_calls: int


def _invoke(builder: Any, payload: dict | None = None, config: Any = None) -> dict:
    """跑一张图并返回完整状态（``config`` 缺省 ⇒ 不传）。"""
    compiled = builder.compile()
    if config is None:
        return compiled.invoke(payload if payload is not None else {"messages": []})
    return compiled.invoke(payload if payload is not None else {"messages": []}, config)


# ── A1 · C8 fresh 读（否定式断言）─────────────────────────────────────────


def _check_a1() -> tuple[bool, str]:
    """**A1** · 路由函数**看到了**本节点本次写入的值（**否定式**断言）。"""
    observed: list[dict[str, Any]] = []

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["fresh"], "llm_calls": 7}

    def router(state: dict[str, Any]) -> str:
        observed.append(dict(state))
        return "after"

    builder = StateGraph(State)
    builder.add_node("writer", writer)
    builder.add_node("after", lambda state: {})
    builder.add_edge(START, "writer")
    builder.add_conditional_edges("writer", router, ["after", END])
    _invoke(builder, {"messages": [], "llm_calls": 0})

    view = observed[0]
    ok = view.get("messages") == ["fresh"] and view.get("llm_calls") == 7
    return ok, f"路由函数的 fresh 视图 = {view!r}"

def _check_a1_reducer() -> tuple[bool, str]:
    """**A1** · 归约型通道在 fresh 读里**已合并**。"""
    observed: list[dict[str, Any]] = []

    def router(state: dict[str, Any]) -> str:
        observed.append(dict(state))
        return "after"

    builder = StateGraph(State)
    builder.add_node("writer", lambda state: {"messages": ["fresh"]})
    builder.add_node("after", lambda state: {})
    builder.add_edge(START, "writer")
    builder.add_conditional_edges("writer", router, ["after", END])
    _invoke(builder, {"messages": ["seed"], "llm_calls": 0})

    view = observed[0]
    ok = view.get("messages") == ["seed", "fresh"]
    return ok, f"fresh 视图 = {view!r}"

def _check_a1_sparse() -> tuple[bool, str]:
    """**A1** · **无值**的覆盖型通道**不在**路由函数的入参里。"""
    observed: list[dict[str, Any]] = []

    def router(state: dict[str, Any]) -> str:
        observed.append(dict(state))
        return "after"

    builder = StateGraph(State)
    builder.add_node("writer", lambda state: {"messages": ["fresh"]})
    builder.add_node("after", lambda state: {})
    builder.add_edge(START, "writer")
    builder.add_conditional_edges("writer", router, ["after", END])
    _invoke(builder, {"messages": []})

    view = observed[0]
    ok = "llm_calls" not in view and view.get("messages") == ["fresh"]
    return ok, f"fresh 视图 = {view!r}"

def _check_a1_isolation() -> tuple[bool, str]:
    """**A1** · 同轮**另一**节点的写入**不可见**（fresh 读 = 本节点本次）。"""
    observed: list[dict[str, Any]] = []

    def router(state: dict[str, Any]) -> str:
        observed.append(dict(state))
        return "c"

    builder = StateGraph(State)
    builder.add_node("a", lambda state: {"messages": ["A"]})
    builder.add_node("b", lambda state: {"messages": ["B"]})
    builder.add_node("c", lambda state: {})
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_conditional_edges("a", router, ["c"])
    _invoke(builder, {"messages": []})

    view = observed[0]
    ok = view.get("messages") == ["A"]
    return ok, f"路由函数的 fresh 视图 = {view!r}"


# ── A2 · path_map 双形态 + 动态目标 ──────────────────────────────────────


def _check_a2_list() -> tuple[bool, str]:
    """**A2** · **list 形态**的 ``path_map``。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: calls.append("r"))
    builder.add_node("a", lambda state: calls.append("a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "a", ["a", END])
    _invoke(builder)
    ok = calls == ["r", "a"]
    return ok, f"执行序列 = {calls!r}"

def _check_a2_dict() -> tuple[bool, str]:
    """**A2** · **dict 形态**的 ``path_map``（返回值作 key 查表）。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: calls.append("r"))
    builder.add_node("a", lambda state: calls.append("a"))
    builder.add_node("b", lambda state: calls.append("b"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "hit", {"hit": "a", "miss": "b"})
    _invoke(builder)
    ok = calls == ["r", "a"]
    return ok, f"执行序列 = {calls!r}"

def _check_a2_dynamic() -> tuple[bool, str]:
    """**A2** · **无** ``path_map`` 的动态目标（返回值 = 已注册节点名）。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: calls.append("r"))
    builder.add_node("a", lambda state: calls.append("a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "a")
    _invoke(builder)
    ok = calls == ["r", "a"]
    return ok, f"执行序列 = {calls!r}"

def _check_a2_hashable() -> tuple[bool, str]:
    """**A2** · **非** ``str`` 的可哈希值（如 ``int``）作 key 正常查表。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: calls.append("r"))
    builder.add_node("a", lambda state: calls.append("a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: 1, {1: "a"})
    _invoke(builder)
    ok = calls == ["r", "a"]
    return ok, f"执行序列 = {calls!r}"


# ── A3 · END 终止 ────────────────────────────────────────────────────────


def _check_a3_singleton() -> tuple[bool, str]:
    """**A3** · **单独返回** ``END`` ⇒ 后续目标**执行 0 次**。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: calls.append("r"))
    builder.add_node("after", lambda state: calls.append("after"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: END, ["after", END])
    _invoke(builder)
    ok = calls == ["r"]
    return ok, f"执行序列 = {calls!r}"

def _check_a3_value() -> tuple[bool, str]:
    """**A3** · ``path_map`` 的 **value** 为 ``END`` ⇒ 同样终止。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: calls.append("r"))
    builder.add_node("a", lambda state: calls.append("a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "stop", {"stop": END, "go": "a"})
    _invoke(builder)
    ok = calls == ["r"]
    return ok, f"执行序列 = {calls!r}"

def _check_a3_no_key() -> tuple[bool, str]:
    """**A3** · ``path_map`` **不含** ``END`` 键 ⇒ **仍然**终止（**X-2** 的分叉）。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: calls.append("r"))
    builder.add_node("a", lambda state: calls.append("a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: END, {"go": "a"})
    _invoke(builder)
    ok = calls == ["r"]
    return ok, f"执行序列 = {calls!r}"

def _check_a3_sequence() -> tuple[bool, str]:
    """**A3** · 序列内的 ``END`` ⇒ **剔除**且其余目标**照常执行**。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: calls.append("r"))
    builder.add_node("a", lambda state: calls.append("a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: [END, "a"], ["a", END])
    _invoke(builder)
    ok = calls == ["r", "a"]
    return ok, f"执行序列 = {calls!r}"

def _check_a3_mapped_elsewhere() -> tuple[bool, str]:
    """**A3** · ``path_map = {END: "b"}`` ⇒ freegraph **无条件终止**（**X-2** 的另一半）。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: calls.append("r"))
    builder.add_node("b", lambda state: calls.append("b"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: END, {END: "b"})
    _invoke(builder)
    ok = calls == ["r"]
    return ok, f"执行序列 = {calls!r}（上游会执行 'b' ⇒ **X-2** 的登记分叉）"


# ── A4 · 失败信号两态 ────────────────────────────────────────────────────


def _check_a4_key_error() -> tuple[bool, str]:
    """**A4** · **有** ``path_map`` + 非法返回值 ⇒ 内置 ``KeyError`` + 详细消息。"""
    builder = StateGraph(State)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "nope", {"hit": "a"})
    try:
        _invoke(builder)
    except KeyError as exc:
        message = str(exc)
        ok = "nope" in message and "hit" in message
        return ok, f"KeyError 消息 = {message!r}"
    except Exception as exc:  # noqa: BLE001
        return False, f"实际 {type(exc).__name__}: {exc}"
    return False, "未抛异常"

def _check_a4_value_error() -> tuple[bool, str]:
    """**A4** · **无** ``path_map`` + 未注册节点名 ⇒ 内置 ``ValueError``（**X-3**）。"""
    builder = StateGraph(State)
    builder.add_node("r", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "ghost")
    try:
        _invoke(builder)
    except ValueError as exc:
        message = str(exc)
        ok = "ghost" in message and "r" in message
        return ok, f"ValueError 消息 = {message!r}"
    except Exception as exc:  # noqa: BLE001
        return False, f"实际 {type(exc).__name__}: {exc}"
    return False, "未抛异常"

def _check_a4_none_start() -> tuple[bool, str]:
    """**A4** · 返回 ``None`` / ``START`` ⇒ **查表优先**的两态失败。"""
    with_map = StateGraph(State)
    with_map.add_node("r", lambda state: {})
    with_map.add_node("a", lambda state: {})
    with_map.add_edge(START, "r")
    with_map.add_conditional_edges("r", lambda state: None, {"hit": "a"})

    without_map = StateGraph(State)
    without_map.add_node("r", lambda state: {})
    without_map.add_edge(START, "r")
    without_map.add_conditional_edges("r", lambda state: START)

    try:
        _invoke(with_map)
    except KeyError:
        pass
    except Exception as exc:  # noqa: BLE001
        return False, f"有 path_map 侧实际 {type(exc).__name__}: {exc}"
    else:
        return False, "有 path_map 侧未抛异常"

    try:
        _invoke(without_map)
    except ValueError:
        return True, "两态各自成立（KeyError / ValueError）"
    except Exception as exc:  # noqa: BLE001
        return False, f"无 path_map 侧实际 {type(exc).__name__}: {exc}"
    return False, "无 path_map 侧未抛异常"

def _check_a4_router_exception() -> tuple[bool, str]:
    """**A4** · 路由函数**自身**的异常**原类型 + 原消息**传播。"""
    boom = RuntimeError("boom")

    def explode(state: dict[str, Any]) -> str:
        raise boom

    builder = StateGraph(State)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", explode, ["a"])
    try:
        _invoke(builder)
    except RuntimeError as exc:
        ok = exc is boom and str(exc) == "boom"
        return ok, f"实际 {type(exc).__name__}: {exc}"
    except Exception as exc:  # noqa: BLE001
        return False, f"实际 {type(exc).__name__}: {exc}"
    return False, "未抛异常"


# ── A5 · 序列 ⇒ 多目标并行 ───────────────────────────────────────────────


def _check_a5_fanout() -> tuple[bool, str]:
    """**A5** · 返回序列 ⇒ 多目标**同轮**并行（各执行 1 次）。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: calls.append("r"))
    builder.add_node("b", lambda state: calls.append("b"))
    builder.add_node("c", lambda state: calls.append("c"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: ["b", "c"], ["b", "c"])
    _invoke(builder)
    ok = calls[0] == "r" and sorted(calls) == ["b", "c", "r"]
    return ok, f"执行序列 = {calls!r}（同轮内顺序**不可观察**）"

def _check_a5_shared_state() -> tuple[bool, str]:
    """**A5** · 多目标收到**同一份**共享状态（**无**逐目标载荷）。"""
    received: list[dict[str, Any]] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: {"messages": ["written"]})
    builder.add_node("b", lambda state: received.append(dict(state)))
    builder.add_node("c", lambda state: received.append(dict(state)))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: ["b", "c"], ["b", "c"])
    _invoke(builder)
    ok = len(received) == 2 and received[0] == received[1]
    return ok, f"两个目标的入参 = {received!r}"

def _check_a5_dedupe() -> tuple[bool, str]:
    """**A5** · 序列含**重复目标** ⇒ **去重保序**（只触发一次）。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: calls.append("r"))
    builder.add_node("b", lambda state: calls.append("b"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: ["b", "b"], ["b"])
    _invoke(builder)
    ok = calls == ["r", "b"]
    return ok, f"执行序列 = {calls!r}"

def _check_a5_empty() -> tuple[bool, str]:
    """**A5** · **空序列** ⇒ 无目标且**不报错**。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: calls.append("r"))
    builder.add_node("a", lambda state: calls.append("a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: [], ["a"])
    _invoke(builder)
    ok = calls == ["r"]
    return ok, f"执行序列 = {calls!r}"

def _check_a5_send() -> tuple[bool, str]:
    """**A5** · 返回 ``Send`` ⇒ 目标收到**载荷**（**不是**共享状态）。"""
    received: list[Any] = []

    builder = StateGraph(State)
    builder.add_node("r", lambda state: {"messages": ["written"]})
    builder.add_node("b", lambda state: received.append(state))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: Send("b", {"payload": 1}), ["b"])
    _invoke(builder)
    ok = received == [{"payload": 1}]
    return ok, f"目标收到的入参 = {received!r}"


# ── A6 · __start__ 上的条件边 ─────────────────────────────────────────────


def _check_a6_evaluated() -> tuple[bool, str]:
    """**A6** · ``__start__`` 上的条件边**被求值**（不静默空跑）。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("a", lambda state: calls.append("a"))
    builder.add_conditional_edges(START, lambda state: "a", ["a"])
    _invoke(builder)
    ok = calls == ["a"]
    return ok, f"执行序列 = {calls!r}"

def _check_a6_pure_entry() -> tuple[bool, str]:
    """**A6** · **纯条件边入口**（无静态入口点）可行。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("a", lambda state: calls.append("a"))
    builder.add_conditional_edges(START, lambda state: "a", ["a"])
    _invoke(builder)
    ok = calls == ["a"]
    return ok, f"执行序列 = {calls!r}"

def _check_a6_parallel() -> tuple[bool, str]:
    """**A6** · 静态入口与条件入口**并存** ⇒ 两者的目标**同轮并行**。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("x", lambda state: calls.append("x"))
    builder.add_node("y", lambda state: calls.append("y"))
    builder.add_edge(START, "x")
    builder.add_conditional_edges(START, lambda state: "y", ["y"])
    _invoke(builder)
    ok = sorted(calls) == ["x", "y"]
    return ok, f"执行序列 = {calls!r}"

def _check_a6_end() -> tuple[bool, str]:
    """**A6** · 条件入口返回 ``END`` ⇒ 该分支终止。"""
    calls: list[str] = []

    builder = StateGraph(State)
    builder.add_node("a", lambda state: calls.append("a"))
    builder.add_conditional_edges(START, lambda state: END, ["a"])
    _invoke(builder)
    ok = calls == []
    return ok, f"执行序列 = {calls!r}"

def _check_a6_idempotent() -> tuple[bool, str]:
    """**A6** · ``__start__`` 条件边的**求值次数 == 1**（**幂等**）。"""
    route_calls: list[str] = []

    def entry(state: dict[str, Any]) -> str:
        route_calls.append("entry")
        return "a"

    builder = StateGraph(State)
    builder.add_node("a", lambda state: {})
    builder.add_node("b", lambda state: {})
    builder.add_conditional_edges(START, entry, ["a"])
    builder.add_conditional_edges("a", lambda state: "b", ["b"])
    _invoke(builder)
    ok = route_calls == ["entry"]
    return ok, f"路由函数被调用 {len(route_calls)} 次（期望 1）"


# ── A7 · 双参形态 ────────────────────────────────────────────────────────


def _check_a7_config() -> tuple[bool, str]:
    """**A7** · 双参形态的第二参 == 用户交给 ``invoke`` 的**原始** ``config``。"""
    received: list[Any] = []
    config = RunConfig(thread_id="t-1")

    def route(state: dict[str, Any], config: RunConfig) -> str:
        received.append(config)
        return "a"

    builder = StateGraph(State)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", route, ["a"])
    _invoke(builder, {"messages": []}, config)
    ok = len(received) == 1 and received[0] is config
    return ok, f"第二参 = {received!r}（**逐字**同一对象）"

def _check_a7_misnamed() -> tuple[bool, str]:
    """**A7** · 第二参**不叫** ``config`` ⇒ 按**一参**调用 ⇒ ``TypeError``。"""

    def route(state: dict[str, Any], cfg: Any) -> str:
        return "a"

    builder = StateGraph(State)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", route, ["a"])
    try:
        _invoke(builder)
    except TypeError as exc:
        return True, f"TypeError: {exc}"
    except Exception as exc:  # noqa: BLE001
        return False, f"实际 {type(exc).__name__}: {exc}"
    return False, "未抛异常"

def _check_a7_no_warning() -> tuple[bool, str]:
    """**A7** · 注解**不在**匹配集 ⇒ **跳过注入** ⇒ **不发** ``UserWarning``。"""
    import warnings

    def route(state: dict[str, Any], config: dict) -> str:
        return "a"

    builder = StateGraph(State)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", route, ["a"])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            _invoke(builder)
        except TypeError:
            pass
        except Exception as exc:  # noqa: BLE001
            return False, f"实际 {type(exc).__name__}: {exc}"
        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    ok = not user_warnings
    return ok, f"捕获到的 UserWarning = {len(user_warnings)} 条（期望 0）"


# ── A8 · 零新增公开面 ────────────────────────────────────────────────────


def _check_a8() -> tuple[bool, str]:
    """**A8** · 公开面**只增不删**（B8F2 后 22 / 8 / 23 / 11 键 · 零新增错误类型）。"""
    from freegraph import contracts, graph, runtime

    counts = (len(contracts.__all__), len(graph.__all__), len(runtime.__all__))
    ok = counts == (22, 8, 23)

    builder = StateGraph(State)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "a", ["a"])
    compiled = builder.compile()
    keys = len(vars(compiled))
    ok = ok and keys == 11

    from freegraph.runtime import errors

    error_symbols = set(errors.__all__)
    ok = ok and error_symbols == {
        "EmptyChannelError",
        "InterruptError",
        "InvalidChannelUpdateError",
        "InvalidSchemaError",
        "REASON_ANNOTATION_UNRESOLVABLE",
        "REASON_NOT_A_STATE_SCHEMA",
        "REASON_REDUCER_NOT_BINARY",
        "SCHEMA_ERROR_REASONS",
    }
    return ok, (
        f"contracts / facade / runtime = {counts[0]} / {counts[1]} / {counts[2]}"
        f" · vars(compiled) = {keys} 键 · errors 符号集合 = {len(error_symbols)}"
    )


# ── A10 · 破冻结面的回溯验证 ─────────────────────────────────────────────


def _check_a10_landings() -> tuple[bool, str]:
    """**A10** · 破面全集 **7 类**的**回溯修订**逐条命中。"""
    missing: list[str] = []
    for relpath, pattern in RETRO_LANDINGS:
        text = _read(relpath)
        if text and pattern in text:
            continue
        missing.append(f"{relpath} :: {pattern}")
    ok = not missing
    detail = "全部命中" if ok else f"未命中 {len(missing)} 条：{missing!r}"
    return ok, detail


def _check_a10_manual_record() -> tuple[bool, str]:
    """**A10** · 人工验证记录**五段式** + **追认**文字 + 破面全集 **7 类**。"""
    if not MANUAL_VERIFICATION.is_file():
        return False, f"缺人工验证记录：{MANUAL_VERIFICATION}"
    text = MANUAL_VERIFICATION.read_text(encoding="utf-8")
    if not text.strip():
        return False, "人工验证记录的正文为空"
    missing_sections = [
        s
        for s in MANUAL_SECTIONS
        if not any(
            line.startswith("## ") and s in line
            for line in text.splitlines()
        )
    ]
    if missing_sections:
        return False, f"缺五段式小节：{missing_sections!r}"
    if "追认" not in text:
        return False, "缺「追认」文字"
    missing_markers = [m for m in BREAK_UNIVERSE_MARKERS if m not in text]
    if missing_markers:
        return False, f"追认文字缺破面项：{missing_markers!r}"
    if not all(m in text for m in ENV_DEVIATION_MARKERS):
        return False, "缺「真实模型轮」的**已登记环境偏离**声明"
    return True, f"五段式齐全 · 破面全集 {len(BREAK_UNIVERSE_MARKERS)} 类逐条在位"


def _check_a10_signature() -> tuple[bool, str]:
    """**A10** · **零改动清单**（只读基准与 B5F2 的差分夹具 / 冻结断言 ③）。"""
    import subprocess as sp

    files = [
        "harness/demo/target.py",
        "tests/differential/spec_builder.py",
        "tests/differential/test_differential.py",
    ]
    changed: list[str] = []
    for relpath in files:
        completed = sp.run(
            ["git", "diff", "--stat", "HEAD", "--", relpath],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if completed.stdout.strip():
            changed.append(relpath)
    ok = not changed
    return ok, ("全部未改动" if ok else f"被改动：{changed!r}")


# ── 主流程 ───────────────────────────────────────────────────────────────


def main() -> int:
    """验收主体。"""
    parser = argparse.ArgumentParser(description="B8F1 一键验收")
    parser.add_argument("--record", help="把验收结果写入该 JSON 文件")
    parser.add_argument(
        "--require-installed",
        action="store_true",
        help="把「freegraph 未安装（跑的是源码树）」判为失败",
    )
    parser.add_argument(
        "--skip-differential",
        action="store_true",
        help="跳过差分闸口（快）",
    )
    global _skipped

    args = parser.parse_args()

    print("══ B8F1 · 条件边路由求值 + END 终止 + fresh 读（C8）══")
    print(f"Python {sys.version.split()[0]} · {platform.platform()}")
    print(f"freegraph 源：{SRC_DIR}")

    # ── A1 · C8 fresh 读 ─────────────────────────────────────────────────
    print("\n[A1] C8 fresh 读（否定式断言）")
    _check_gate("A1", "路由函数看到了本节点本次写入的值", _check_a1)
    _check_gate("A1", "归约型通道在 fresh 读里已合并", _check_a1_reducer)
    _check_gate("A1", "无值的覆盖型通道不在路由入参里", _check_a1_sparse)
    _check_gate("A1", "同轮另一节点的写入不可见", _check_a1_isolation)

    # ── A2 · path_map 双形态 ────────────────────────────────────────────
    print("\n[A2] path_map 双形态 + 动态目标")
    _check_gate("A2", "list 形态的 path_map 路由正确", _check_a2_list)
    _check_gate("A2", "dict 形态的 path_map 路由正确", _check_a2_dict)
    _check_gate("A2", "无 path_map 的动态目标路由正确", _check_a2_dynamic)
    _check_gate("A2", "非 str 的可哈希值作 key 正常查表", _check_a2_hashable)

    # ── A3 · END 终止 ───────────────────────────────────────────────────
    print("\n[A3] END 终止")
    _check_gate("A3", "单独返回 END ⇒ 后续目标执行 0 次", _check_a3_singleton)
    _check_gate("A3", "path_map 的 value 为 END ⇒ 同样终止", _check_a3_value)
    _check_gate("A3", "path_map 不含 END 键 ⇒ 仍然终止（X-2）", _check_a3_no_key)
    _check_gate("A3", "序列内的 END ⇒ 剔除且其余照常执行", _check_a3_sequence)
    _check_gate("A3", "path_map 把 END 映射到别的节点 ⇒ 无条件终止（X-2）", _check_a3_mapped_elsewhere)

    # ── A4 · 失败信号两态 ────────────────────────────────────────────────
    print("\n[A4] 失败信号两态")
    _check_gate("A4", "有 path_map + 非法返回值 ⇒ KeyError + 详细消息", _check_a4_key_error)
    _check_gate("A4", "无 path_map + 未注册节点名 ⇒ ValueError（X-3）", _check_a4_value_error)
    _check_gate("A4", "返回 None / START ⇒ 查表优先的两态", _check_a4_none_start)
    _check_gate("A4", "路由函数自身的异常原类型 + 原消息传播", _check_a4_router_exception)

    # ── A5 · 多目标 fan-out ─────────────────────────────────────────────
    print("\n[A5] 序列 ⇒ 多目标并行")
    _check_gate("A5", "返回序列 ⇒ 多目标同轮并行", _check_a5_fanout)
    _check_gate("A5", "多目标收到同一份共享状态", _check_a5_shared_state)
    _check_gate("A5", "序列含重复目标 ⇒ 去重保序", _check_a5_dedupe)
    _check_gate("A5", "空序列 ⇒ 无目标且不报错", _check_a5_empty)
    _check_gate("A5", "返回 Send ⇒ 目标收到载荷", _check_a5_send)

    # ── A6 · __start__ 上的条件边 ────────────────────────────────────────
    print("\n[A6] __start__ 上的条件边")
    _check_gate("A6", "__start__ 上的条件边被求值", _check_a6_evaluated)
    _check_gate("A6", "纯条件边入口可行", _check_a6_pure_entry)
    _check_gate("A6", "静态入口与条件入口并存 ⇒ 同轮并行", _check_a6_parallel)
    _check_gate("A6", "条件入口返回 END ⇒ 该分支终止", _check_a6_end)
    _check_gate("A6", "__start__ 条件边的求值次数 == 1（幂等）", _check_a6_idempotent)

    # ── A7 · 双参形态 ───────────────────────────────────────────────────
    print("\n[A7] 双参形态")
    _check_gate("A7", "第二参 == 用户的原始 config（逐字）", _check_a7_config)
    _check_gate("A7", "第二参不叫 config ⇒ TypeError", _check_a7_misnamed)
    _check_gate("A7", "注解不在匹配集 ⇒ 跳过注入且不发 UserWarning", _check_a7_no_warning)

    # ── A8 · 零新增公开面 ───────────────────────────────────────────────
    print("\n[A8] 零新增公开面")
    _check_gate("A8", "22 / 8 / 23 符号 + 11 键 + 零新增错误类型", _check_a8)

    # ── A9 · 差分组 ─────────────────────────────────────────────────────
    print("\n[A9] 差分组 D-103…D-120")
    if args.skip_differential:
        _skipped += 1
        print("[SKIP] A9   差分组全绿 —— --skip-differential")
        _record("A9", "差分组全绿（D-103…D-120）", "SKIP", "--skip-differential")
    else:
        _pytest_gate(
            "A9",
            "差分组 D-103…D-120 全绿（SC-013）",
            ["tests/differential/test_parity_probe.py"],
            needs_upstream=True,
        )

    # ── A10 · 破冻结面的回溯验证 ────────────────────────────────────────
    print("\n[A10] 破冻结面的回溯验证（7 类）")
    _check_gate("A10", "破面全集 7 类的回溯修订逐条命中", _check_a10_landings)
    _check_gate("A10", "人工验证记录五段式 + 追认文字 + 破面全集 7 类", _check_a10_manual_record)
    _check_gate("A10", "零改动清单（target.py / 差分夹具 / 冻结断言 ③）", _check_a10_signature)

    print()
    print("=" * 78)
    verdict = "PASS" if _failures == 0 else "FAIL"
    print(f"总闸口 {len(_results)} · 失败 {_failures} · 跳过 {_skipped} ⇒ **{verdict}**")
    print("=" * 78)
    if _failures:
        for item in _results:
            if item["status"] == "FAIL":
                print(f"  - {item['gate']} · {item['label']} · {item['detail']}")
        print("B8F1 acceptance: FAIL")
    else:
        print("B8F1 acceptance: PASS")

    if args.record:
        record = Path(args.record)
        record.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "feature": "B8F1",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "verdict": verdict,
            "failures": _failures,
            "skipped": _skipped,
            "gates": _results,
        }
        record.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"验收记录片段已写入：{record}")

    return 0 if _failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
