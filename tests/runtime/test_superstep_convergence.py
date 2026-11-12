# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**收敛与步数上限**的用例 —— 属 **B7F1**（tasks T035 / T036 / T037 / T064）。

覆盖的判定：

* **SC-006** —— 触发集合为空 ⇒ 循环**立即终止**（`executed` == **空元组**
  且 `steps` == **1**）；自环规格在步数上限处抛 `GraphRecursionError`；
  **不显式指定上限**时实际生效的上限 == **25**；
* **SC-001** —— 多轮入口的**跨轮累计语义**（`executed` 累计 ·
  `node_writes` 按轮次先后拼接 · 单轮入口 `steps` 恒为 **1**）·
  两个入口的「已消费版本」**不串扰**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from freegraph.contracts import GraphRecursionError
from freegraph.runtime import (
    Channel,
    GraphSpec,
    LastValue,
    NodeSpec,
    SchedulerState,
    run_super_step,
    run_super_steps,
)


def _channels() -> dict[str, Channel]:
    """构造通道状态：**覆盖型**（``count``）+ **覆盖型**（``other``）。"""
    return {
        "count": LastValue("count", int),
        "other": LastValue("other", str),
    }


#: **入口哨兵节点**（上游 ``START`` 同款 · ``langgraph/constants.py:30``）。
#:
#: ⚠️ 它**无入边** ⇒ **永不执行**（永不进 ``executed``）⇒ 它只作「入口边」的**源**。
#:
#: ⚠️ **为什么它 MUST 在节点表里** —— ``GraphSpec`` 的校验规则 **V-2** 要求
#: 「边的**源** MUST 在节点表里」⇒ 入口边 ``edges={"__start__": ("首节点",)}``
#: 的源 ``__start__`` 也 MUST 在节点表里（上游的 ``START`` 是**编译期**补进去的
#: 伪节点 · ``langgraph/graph/state.py:321`` ⇒ freegraph 在**手写图规格**层面
#: 用「节点表里的一个哨兵节点」表达**同款**语义）。
_ENTRY = NodeSpec(subscribes=(), run=lambda state: {})


def _self_loop_spec() -> GraphSpec:
    """构造一份**自环**规格：节点被**自环边**触发 ⇒ 永远有任务。

    ⚠️ **上游同款**：触发源**恒为边** ⇒ 「自环」= **自环边**
    （``edges={"loop": ("loop",)}``）⇒ 每次执行都把它的**边触发源**版本推进 1
    ⇒ 下一轮**再次**被触发 ⇒ 永远有任务。
    """
    channels = _channels()
    channels["count"].update([1])
    return GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "loop": NodeSpec(
                subscribes=("count",), run=lambda state: {"count": state["count"] + 1}
            ),
        },
        edges={"__start__": ("loop",), "loop": ("loop",)},
    )


# ── T035 · 收敛（SC-006）────────────────────────────────────────────────


def test_an_empty_trigger_set_terminates_immediately() -> None:
    """**SC-006**：触发集合为空 ⇒ 循环**立即终止** ⇒ `executed` == **空元组**。

    ⚠️ ``steps`` == **1**（**只含**那次用于发现「任务集为空」的**空轮**）。

    ⚠️ **上游同款**：该节点**无入边** ⇒ 触发源**恒为边** ⇒ 触发集合为空。
    """
    spec = GraphSpec(
        channels=_channels(),
        nodes={
            "__start__": _ENTRY,
            "idle": NodeSpec(subscribes=("count",), run=lambda state: {}),
        },
        edges={},
    )

    result = run_super_steps(spec)

    assert result.executed == ()
    assert result.steps == 1
    assert result.node_writes == {}


def test_a_spec_that_runs_in_the_first_round_reports_two_steps() -> None:
    """**SC-006**：首轮即有任务被执行 ⇒ `executed` **非空**且 `steps` == **2**。

    ⚠️ **2** = 1 个**执行轮** + 1 个**空轮**（发现「任务集为空」的那一轮）。
    """
    channels = _channels()
    channels["count"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "worker": NodeSpec(subscribes=("count",), run=lambda state: {}),
        },
        edges={"__start__": ("worker",)},
    )

    result = run_super_steps(spec)

    assert result.executed == ("worker",)
    assert result.steps == 2


# ── T036 · 自环被上限拦住（SC-006）──────────────────────────────────────


def test_a_self_loop_spec_raises_graph_recursion_error() -> None:
    """**SC-006**：自环规格 ⇒ 在步数上限处抛 ``GraphRecursionError``。

    ⚠️ 其 ``recursion_limit`` / ``current_step`` 两个结构化字段 MUST 有值；
    「无界死循环」的出现次数 == **0**。
    """
    spec = _self_loop_spec()

    # ⚠️ **显式**给一个小上限（否则要跑满缺省的 10007 轮）⇒ 上限**行为**与**缺省值**解耦
    with pytest.raises(GraphRecursionError) as excinfo:
        run_super_steps(spec, max_steps=25)

    assert excinfo.value.recursion_limit == 25
    assert excinfo.value.current_step == 25


# ── T037 · 上限的缺省值（SC-006）────────────────────────────────────────


def test_the_default_step_limit_is_ten_thousand_and_seven() -> None:
    """**SC-006**：**不显式指定上限**时实际生效的上限 == **10007**。

    ⚠️ **2026-11-12 · 上游对齐 P2-c**：缺省由 **25** 改为 **10007**（**上游同款** ·
    ``langgraph/_internal/_config.py:32`` 的 ``DEFAULT_RECURSION_LIMIT = 10007``）——
    ⚠️ 上游可由环境变量 ``LANGGRAPH_DEFAULT_RECURSION_LIMIT`` 覆盖，freegraph **MUST NOT**
    读环境变量（零环境变量红线）⇒ **硬编码**。
    ⚠️ 原「缺省 25 · 与上游一致」的表述是**事实错误**（上游是 10007）⇒ 本次**订正**。

    ⚠️ 测量方法 MUST 明确 —— **签名缺省值**与**行为值** MUST **一致**
    （契约 §6 的判定顺序）。
    """
    default = inspect.signature(run_super_steps).parameters["max_steps"].default
    assert default == 10007

    with pytest.raises(GraphRecursionError) as excinfo:
        run_super_steps(_self_loop_spec())

    assert excinfo.value.recursion_limit == 10007


def test_an_explicit_step_limit_is_honoured() -> None:
    """**SC-006**：显式指定上限 ⇒ 该上限**生效**（``recursion_limit`` 字段）。"""
    spec = _self_loop_spec()

    with pytest.raises(GraphRecursionError) as excinfo:
        run_super_steps(spec, max_steps=3)

    assert excinfo.value.recursion_limit == 3
    assert excinfo.value.current_step == 3


def test_a_graph_that_converges_within_the_limit_returns_normally() -> None:
    """**SC-006**：``max_steps=1`` 且图恰好 1 轮收敛 ⇒ **正常返回**（不抛错）。

    ⚠️ 判定顺序 MUST 是 ① 先判「任务集合为空 ⇒ 立即终止」② 再判「执行轮数
    == 上限 **且**下一轮任务集非空 ⇒ 抛错」（FR-011 ⚠️）。
    """
    channels = _channels()
    channels["count"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "worker": NodeSpec(subscribes=("count",), run=lambda state: {}),
        },
        edges={"__start__": ("worker",)},
    )

    result = run_super_steps(spec, max_steps=1)

    assert result.executed == ("worker",)
    assert result.steps == 2


# ── T064 · 多轮入口的跨轮累计语义（SC-001 / SC-003）──────────────────────


def test_the_multi_round_entry_accumulates_executed_and_node_writes() -> None:
    """**SC-001**：多轮入口 ⇒ `executed` == 各轮执行序列的**顺序拼接**。

    ⚠️ `node_writes` 中**同名节点**的**同一通道**的值序列 == **按轮次先后拼接**
    （**不**按通道重排）。

    链条（**边**驱动 · 上游同款）：``s1``（入口边）在第 1 轮写 ``ax`` ⇒ ``s2``
    与 ``p``（``s1`` 的**出边**）在**第 2 轮**各跑一次 ⇒ ``p``（``s2`` 的**出边**）
    在**第 3 轮**再跑一次 ⇒ ``p`` 对 ``out`` 的两次写入 MUST 按**轮次先后**拼接。
    """
    channels = _channels()
    channels["ax"] = LastValue("ax", int)
    channels["ay"] = LastValue("ay", int)
    channels["out"] = LastValue("out", str)
    channels["sa"] = LastValue("sa", int)
    channels["sa"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "s1": NodeSpec(subscribes=("sa",), run=lambda state: {"ax": 1}),
            "s2": NodeSpec(subscribes=("ax",), run=lambda state: {"ay": 2}),
            "p": NodeSpec(
                subscribes=("ax", "ay"), run=lambda state: {"out": "written"}
            ),
        },
        edges={"__start__": ("s1",), "s1": ("s2", "p"), "s2": ("p",)},
    )

    result = run_super_steps(spec)

    assert result.executed == ("s1", "p", "s2", "p")
    assert result.node_writes["p"]["out"] == ("written", "written")
    assert result.node_writes["s1"]["ax"] == (1,)
    assert result.node_writes["s2"]["ay"] == (2,)


def test_the_single_round_entry_always_reports_one_step() -> None:
    """**SC-001**：单轮入口的 `steps` **恒为 1**（多轮入口的 `steps` == **实际
    迭代轮数** · **含**空轮）。"""
    channels = _channels()
    channels["count"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "worker": NodeSpec(subscribes=("count",), run=lambda state: {}),
        },
        edges={"__start__": ("worker",)},
    )

    single = run_super_step(spec, SchedulerState())
    multi = run_super_steps(spec)

    assert single.steps == 1
    assert multi.steps == 2


def test_the_two_entries_do_not_share_their_consumed_versions() -> None:
    """**SC-003**：两个入口的「已消费版本」**互不串扰**（FR-004）。

    ⚠️ 同一份图规格 × 独立的两份调度状态 ⇒ 一个入口的消费记录 MUST **不**
    影响另一个入口的触发判定。
    """
    channels = _channels()
    channels["count"].update([1])
    calls: list[str] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("node")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "node": NodeSpec(subscribes=("count",), run=node),
        },
        edges={"__start__": ("node",)},
    )

    run_super_step(spec, SchedulerState())
    assert calls == ["node"]

    # 独立的调度状态 ⇒ 「已消费版本」为空 ⇒ 节点**再次**被触发。
    run_super_step(spec, SchedulerState())
    assert calls == ["node", "node"]


def test_the_execution_round_counter_excludes_empty_rounds() -> None:
    """**SC-003**：两个计数器 MUST NOT 混用（裁定 34）。

    * ``SchedulerState.step``（**执行轮** · **不含**空轮）在**每个执行轮结束**
      **+1**、**空轮不 +1**；
    * ⇄ ``SuperStepResult.steps``（**含**空轮的**迭代轮数**）。
    """
    channels = _channels()
    channels["count"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "worker": NodeSpec(subscribes=("count",), run=lambda state: {}),
        },
        edges={"__start__": ("worker",)},
    )
    state = SchedulerState()

    result = run_super_steps(spec, state)

    assert result.steps == 2
    assert state.step == 1
