# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**确定性 + 调度状态不串扰**的用例 —— 属 **B9F1**（tasks T029）。

⚠️ **触发模型**（上游对齐 · 2026-11-12）：触发源**恒为边** ⇒ 每张图 MUST 有
**入口边** ``{"__start__": (首节点,)}``（上游 ``add_edge(START, "a")`` 的同款写法）。

覆盖的判定：

* **SC-019** —— 同一份规格重复执行 **≥ 3** 次 ⇒ 合并后状态与执行序列**逐项
  相等**（差异 == **0**）；两次**独立**运行（各自新建调度状态）⇒ **互不影响**
  （比率 == **100%**）；多轮入口**省略**调度状态 ⇒ 内部自洽（**不**继承此前
  任何调用的消费记录）。

⚠️ **动态边表**落在**调度状态**上（裁定 12）⇒ 「同一份规格可**安全跑多次**」
的承诺 MUST 仍然成立 ⇒ **不串扰**是**结构性**的（运行期记录**不在**图规格里）。

**手写图规格**驱动 ⇒ MUST **不经由** ``StateGraph`` / ``compile()`` /
``invoke()``（FR-020 · SC-016）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Any

from freegraph.contracts import Command
from freegraph.runtime import (
    BinaryOperatorAggregate,
    Channel,
    GraphSpec,
    LastValue,
    NodeSpec,
    SchedulerState,
    run_super_step,
    run_super_steps,
)


def _channels() -> dict[str, Channel]:
    """构造通道状态：**归约型**（``messages``）+ **覆盖型**（``count`` / ``seed``）。

    ⚠️ ``seed`` 的**初值**只作**入参**（``subscribes`` 只决定「读哪些通道」·
    上游 ``langgraph/graph/state.py:1534``）⇒ **不再**是触发源。
    """
    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "count": LastValue("count", int),
        "seed": LastValue("seed", int),
    }


#: **入口哨兵**（上游 ``START`` 的值 · ``langgraph/constants.py:30``）——
#: 触发源**恒为边**（上游 ``branch:to:<node>`` · ``langgraph/graph/state.py:1531``）
#: ⇒ 每张图 MUST 有**入口边** ``{"__start__": (首节点,)}``（上游
#: ``add_edge(START, "a")`` 的同款写法 · ``langgraph/graph/state.py:321``）。
_START = "__start__"


def _never(state: dict[str, Any]) -> dict[str, Any]:
    """**入口哨兵**的节点函数 —— 恒**不被调用**（哨兵无入边 ⇒ 永不被触发）。"""
    raise AssertionError("入口哨兵 __start__ 恒不被执行")


#: **入口哨兵节点**（上游 ``START`` **伪节点**）—— 恒**不被执行**。
_SENTINEL = NodeSpec(subscribes=(), run=_never)


def _graph(
    channels: dict[str, Channel],
    nodes: dict[str, NodeSpec],
    edges: dict[str, tuple[str, ...]],
) -> GraphSpec:
    """组装图规格 —— **注入**入口哨兵节点（``edges`` MUST 已含**入口边**）。

    ⚠️ 边的**源** MUST 在节点表里（V-2）⇒ 入口边的**源**（``__start__``）由
    **哨兵节点**承载（上游的 ``START`` 亦是图里的**伪节点**）。
    """
    return GraphSpec(
        channels=channels,
        nodes={_START: _SENTINEL, **nodes},
        edges=edges,
    )


def _spec() -> GraphSpec:
    """构造一份带 ``goto`` 的图规格（``x`` → ``y``（静态边）+ ``x`` ``goto`` → ``z``）。

    ⚠️ ``z`` 订阅 ``count``（**覆盖型** · 初始**无值**）⇒ 它**只**可能被
    ``x`` 的 ``goto``（**动态边**）触发（触发源**恒为边** ⇒ 判据聚焦在
    **动态边**上）。
    """
    channels = _channels()
    channels["seed"].update([1])
    return _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(
                subscribes=("seed",),
                run=lambda state: Command(goto="z", update={"messages": ["from-x"]}),
            ),
            "y": NodeSpec(subscribes=(), run=lambda state: {"count": 1}),
            "z": NodeSpec(subscribes=("count",), run=lambda state: {}),
        },
        edges={_START: ("x",), "x": ("y",)},
    )


def test_repeating_the_same_spec_yields_equal_results() -> None:
    """**SC-019**：同一份规格重复执行 **3** 次 ⇒ 状态与执行序列**逐项相等**。"""
    results = []
    for _ in range(3):
        spec = _spec()
        results.append(run_super_steps(spec))

    assert results[0].state == results[1].state == results[2].state
    assert results[0].executed == results[1].executed == results[2].executed
    assert results[0].node_writes == results[1].node_writes == results[2].node_writes


def test_two_independent_scheduler_states_do_not_interfere() -> None:
    """**SC-019**：两次**独立**运行（各自新建调度状态）⇒ **互不影响**。

    ⇒ 动态边表等运行期记录**不串扰**（裁定 27 · 动态边表落在调度状态上）。
    """
    first = run_super_steps(_spec(), SchedulerState())
    second = run_super_steps(_spec(), SchedulerState())

    assert first.executed == second.executed
    assert first.state == second.state


def test_the_multi_round_entry_omitting_the_state_starts_from_scratch() -> None:
    """**SC-019**：多轮入口**省略**调度状态 ⇒ 内部自洽（**不**继承消费记录）。"""
    first = run_super_steps(_spec())
    second = run_super_steps(_spec())

    assert first.executed == second.executed
    assert first.state == second.state


def test_the_dynamic_edge_table_lives_in_the_scheduler_state() -> None:
    """**SC-019**：动态边表落在**调度状态**上 ⇒ 图规格**不含**任何运行期记录。

    ⇒ 同一份图规格**可安全跑多次**（FR-004 · 裁定 12）。
    """
    spec = _spec()
    state = SchedulerState()
    run_super_step(spec, state)

    assert state.dynamic_edges["x"] == ("z",)
    assert not hasattr(spec, "dynamic_edges")


def test_a_second_run_with_the_same_state_does_not_replay_the_jump() -> None:
    """**SC-019**：**同一**调度状态续跑 ⇒ 「已消费版本」**不**被重置。

    ⇒ 动态边的触发与静态边**同款**（版本口径一致 ⇒ 不重复触发）。
    """
    spec = _spec()
    state = SchedulerState()
    first = run_super_step(spec, state)
    second = run_super_step(spec, state)

    assert first.executed == ("x",)
    assert second.executed == ("y", "z")


def test_the_execution_order_is_stable_across_repeated_runs() -> None:
    """**SC-019**：执行序列在重复运行间**稳定**（节点表顺序 · FR-013）。"""
    orders = []
    for _ in range(3):
        spec = _spec()
        orders.append(run_super_steps(spec).executed)

    assert orders[0] == orders[1] == orders[2]


def test_a_command_returning_graph_is_reproducible() -> None:
    """**SC-019**：含 ``Command`` 返回的图**可复现**（合并结果逐项相等）。"""
    states = []
    for _ in range(3):
        spec = _spec()
        states.append(run_super_steps(spec).state)

    assert states[0] == states[1] == states[2]


def test_the_node_input_is_never_affected_by_a_previous_run() -> None:
    """**SC-019**：前一次运行的写入**不**成为本次运行的入参（确定性）。"""
    captured: list[dict[str, Any]] = []

    def writer(state: dict[str, Any]) -> Command:
        captured.append(state)
        return Command(update={"count": 1})

    channels = _channels()
    channels["seed"].update([1])
    spec = _graph(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("seed", "count"), run=writer)},
        edges={_START: ("writer",)},
    )

    run_super_step(spec, SchedulerState())

    assert captured[0] == {"seed": 1}
