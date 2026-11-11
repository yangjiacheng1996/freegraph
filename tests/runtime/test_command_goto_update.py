# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**跳转 + 更新同时生效**的用例 —— 属 **B9F1**（tasks T013 / T014 / T015 / T016）。

覆盖的判定：

* **SC-001** —— 返回 ``Command(goto=Y)`` 的用例中，Y 在**下一轮**被执行；
* **SC-002** —— ``Command(goto=..., update=...)`` 的用例中，「跳转已登记为下一轮的
  边触发源」与「更新已按通道语义合并进状态」两条断言**同时**成立；
* **SC-003**（部分）—— ``Command.update`` 的写入与普通返回值**逐项一致**；
* **SC-008** —— ``goto=END`` **不产生跳转**、**不终止整张图**（更新照常生效）；
* **SC-022** —— ``Command.update`` 的写入**归源节点**名下（``node_writes``）。

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
    """构造通道状态：**归约型**（``messages``）+ **覆盖型**（``count``）。

    ⚠️ 另备一个 ``seed``（覆盖型）—— 用作**触发源**，与写入目标**分离**
    ⇒ 避免「节点写入自己订阅的通道」导致的自触发回环（B7F1 的既有语义）。
    """
    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "count": LastValue("count", int),
        "seed": LastValue("seed", int),
    }


def test_goto_end_applies_the_update_without_producing_a_jump() -> None:
    """**SC-002 / SC-008**：``goto=END`` ⇒ 更新**照常生效**、**不产生跳转**。

    ⚠️ **END 不终止整张图**（裁定 5）——「不产生跳转」= **该位没有下一站**
    ⇒ 图的收敛由「没有任何触发源」决定 ⇒ 本例中**没有任何节点**在 ``writer``
    之后被执行。
    """
    channels = _channels()
    channels["seed"].update([1])

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("seed",),
                run=lambda state: Command(
                    goto="__end__", update={"messages": ["via-command"]}
                ),
            )
        },
        edges={},
    )

    result = run_super_step(spec, SchedulerState())

    assert result.state["messages"] == ["via-command"]
    assert result.executed == ("writer",)


def test_goto_next_executes_the_target_and_merges_the_update() -> None:
    """**SC-001 / SC-002**：``goto="target"`` ⇒ 目标**被执行**且状态含该更新。

    两条断言**同时**成立（FR-003）⇒ 「只生效其一」的现象 == **0**。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("writer")
        return Command(goto="target", update={"count": 1})

    def target(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("target")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "target": NodeSpec(subscribes=(), run=target),
        },
        edges={},
    )

    result = run_super_steps(spec)

    assert executed == ["writer", "target"]
    assert result.state["count"] == 1


def test_the_goto_target_runs_only_in_the_next_round() -> None:
    """**SC-001**：``goto`` 的目标**不在同一轮**内被执行（FR-002）。

    「``goto`` 目标在**同一轮**内被执行」的现象 == **0** 次。
    """
    channels = _channels()
    channels["seed"].update([1])
    rounds: list[list[str]] = []

    def writer(state: dict[str, Any]) -> Command:
        rounds.append(["writer"])
        return Command(goto="target")

    def target(state: dict[str, Any]) -> dict[str, Any]:
        rounds.append(["target"])
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "target": NodeSpec(subscribes=(), run=target),
        },
        edges={},
    )

    run_super_step(spec, SchedulerState())

    assert rounds == [["writer"]]


def test_the_command_update_is_attributed_to_the_source_node() -> None:
    """**SC-022**：``Command.update`` 的写入归**返回该命令的节点**名下。

    ⇒ **B8F1** 的「本节点**本次**写入」fresh 读**读得到**（裁定 16）。
    """
    channels = _channels()
    channels["seed"].update([1])

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("seed",),
                run=lambda state: Command(update={"messages": ["via-command"]}),
            )
        },
        edges={},
    )

    result = run_super_step(spec, SchedulerState())

    assert result.node_writes == {"writer": {"messages": (["via-command"],)}}


def test_the_goto_target_is_registered_as_an_edge_trigger_source() -> None:
    """**SC-001**：``goto`` 的落点是**边触发源**空间（``("e", 源节点名)``）。

    ⇒ 证据 = **下一轮** ``executed`` 里出现目标节点（裁定 18 · 不新增字段）。
    """
    channels = _channels()
    channels["seed"].update([1])

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(goto="target")
            ),
            "target": NodeSpec(subscribes=(), run=lambda state: {}),
        },
        edges={},
    )

    state = SchedulerState()
    first = run_super_step(spec, state)
    second = run_super_step(spec, state)

    assert first.executed == ("writer",)
    assert second.executed == ("target",)

