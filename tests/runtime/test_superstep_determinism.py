# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**确定性**的用例 —— 属 **B7F1**（tasks T042）。

覆盖的判定：

* **SC-013** —— 同一份规格重复执行 **≥ 3** 次，合并后状态与执行序列
  **逐项相等**；图规格的**节点表被重排**时执行序列**随之改变**；
  同一份规格可**安全跑两次**（调度状态由调用方持有 ⇒ 互不干扰）。

⚠️ **2026-11-12 · 上游对齐（P1-0-2）**：触发源**恒为边**（上游 ``branch:to:<node>``
· ``langgraph/graph/state.py:1531-1532``）⇒ 本文件的夹具一律带**入口边**
（``edges={"__start__": ("首节点", ...)}``）⇒ ``subscribes`` **只**决定「读哪些
通道」，**不再**是触发源。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Any

from freegraph.runtime import (
    BinaryOperatorAggregate,
    Channel,
    GraphSpec,
    LastValue,
    NodeSpec,
    SchedulerState,
    run_super_step,
)


def _channels() -> dict[str, Channel]:
    """构造通道状态：**覆盖型** + **归约型**。"""
    return {
        "count": LastValue("count", int),
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
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


def _spec(order: tuple[str, ...]) -> GraphSpec:
    """构造一份「**节点表顺序** = ``order``」的图规格。

    ⚠️ **入口边**指向**全部**节点 ⇒ 它们**同轮**被执行 ⇒ 执行顺序 == 节点表顺序。
    """
    channels = _channels()
    channels["count"].update([1])

    def make(name: str) -> Any:
        def run(state: dict[str, Any]) -> dict[str, Any]:
            return {"messages": [name]}

        return run

    return GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            **{name: NodeSpec(subscribes=("count",), run=make(name)) for name in order},
        },
        edges={"__start__": order},
    )


# ── T042 · 确定性（SC-013）──────────────────────────────────────────────


def test_repeating_the_same_spec_yields_equal_results() -> None:
    """**SC-013**：同一份规格重复执行 **≥ 3** 次 ⇒ 状态与执行序列**逐项相等**。"""
    states: list[dict[str, Any]] = []
    executions: list[tuple[str, ...]] = []

    for _ in range(3):
        spec = _spec(("alpha", "beta"))
        result = run_super_step(spec, SchedulerState())
        states.append(result.state)
        executions.append(result.executed)

    assert states[0] == states[1] == states[2]
    assert executions[0] == executions[1] == executions[2]


def test_reordering_the_node_table_does_not_change_the_execution_order() -> None:
    """**SC-013**：节点表**被重排** ⇒ 执行序列**不变**（恒为**节点名序**）。

    ⚠️ **2026-11-12 · 上游对齐 P2-c**：执行顺序 MUST 取自**节点名序**
    （上游 ``langgraph/pregel/_algo.py:482`` 的 ``sorted(triggered_nodes)``）
    ⇒ **取代**原「取自**声明顺序**」的口径（FR-013 · 裁定 9）⇒ 重排节点表**不再**改变
    执行序列 ⇒ 这也正是**差分测试**能与上游**逐项相等**的前提。
    """
    forward = run_super_step(_spec(("alpha", "beta")), SchedulerState())
    backward = run_super_step(_spec(("beta", "alpha")), SchedulerState())

    assert forward.executed == ("alpha", "beta")
    assert backward.executed == ("alpha", "beta")
    assert forward.executed == backward.executed


def test_two_independent_scheduler_states_give_equal_results() -> None:
    """**SC-013**：两个**独立**的调度状态跑同一份规格 ⇒ 结果**逐项相等**。

    ⚠️ 同一份规格可**安全跑两次**（调度状态由调用方持有 ⇒ 互不干扰 · FR-004）。
    """
    first = run_super_step(_spec(("alpha", "beta")), SchedulerState())
    second = run_super_step(_spec(("alpha", "beta")), SchedulerState())

    assert first.state == second.state
    assert first.executed == second.executed
    assert first.node_writes == second.node_writes
