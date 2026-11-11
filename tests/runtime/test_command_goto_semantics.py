# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**跳转语义**（叠加 / 生命周期 / 触发门槛 / 入参）的用例 —— 属 **B9F1**
（tasks T024 / T025）。

覆盖的判定：

* **SC-007** —— 静态边目标与 ``goto`` 目标**都**在下一轮被触发（**叠加**）；
  同一对 (源, 目标) 在一轮内被触发**两次**的次数 == **0**；
* **SC-008** —— ``END`` **不跳转、不终止**（静态边目标仍被执行 + 更新生效）；
* **SC-010** —— 源节点再次执行且**不**返回 ``goto`` ⇒ 旧目标**不再**被触发
  （「残留触发 / 幽灵触发」的现象 == **0**）；
* **SC-011** —— **多目标** ``goto`` ⇒ 全部目标在下一轮被执行；``goto=()`` ⇒ 无跳转；
* **SC-023** —— ``goto`` 目标**无「有值」门槛**；其入参 == **正常稀疏读**；
  目标**读得到**源节点本次 ``update`` 的内容。

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
    read_channels,
    run_super_step,
    run_super_steps,
)


def _channels() -> dict[str, Channel]:
    """构造通道状态：**归约型**（``messages``）+ 覆盖型（``count`` / ``seed``）。"""
    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "count": LastValue("count", int),
        "seed": LastValue("seed", int),
    }


def test_the_goto_target_and_the_static_edge_target_are_both_triggered() -> None:
    """**SC-007**：静态边目标与 ``goto`` 目标**都**在下一轮被触发（**叠加**）。

    ⇒ 「``goto`` 取消静态边」或「静态边取消 ``goto``」的现象 == **0** 次
    （裁定 3 · 发起者的概念锚点：「两者同类 ⇒ 叠加自洽」）。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto="z")

    def y(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("y")
        return {}

    def z(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("z")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "y": NodeSpec(subscribes=(), run=y),
            "z": NodeSpec(subscribes=(), run=z),
        },
        edges={"x": ("y",)},
    )

    run_super_steps(spec)

    assert executed == ["x", "y", "z"]


def test_the_same_source_target_pair_is_triggered_at_most_once_per_round() -> None:
    """**SC-007**：同一对 (源, 目标) 在一轮内被触发**两次**的次数 == **0**。

    ⇒ 静态边与动态边指向**同一**目标时，仍**只执行一次**。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto="y")

    def y(state: dict[str[str, Any]]) -> dict[str, Any]:
        executed.append("y")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "y": NodeSpec(subscribes=(), run=y),
        },
        edges={"x": ("y",)},
    )

    run_super_steps(spec)

    assert executed == ["x", "y"]


def test_the_goto_target_is_not_triggered_again_after_the_source_reruns_without_a_goto() -> None:
    """**SC-010**：源节点再次执行且**不**返回 ``goto`` ⇒ 旧目标**不再**被触发。

    ⇒ 「残留触发（幽灵触发）」的现象 == **0** 次（裁定 2 · FR-009）。

    ⚠️ 源节点靠**自己写入的通道**再次被触发（第 1 轮写 ``count`` ⇒ 第 2 轮
    ``count`` 版本推进 ⇒ 源节点再跑一次 ⇒ 本次**不**给 ``goto``）。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []
    calls = {"count": 0}

    def writer(state: dict[str, Any]) -> Any:
        calls["count"] += 1
        executed.append(f"x#{calls['count']}")
        if calls["count"] == 1:
            return Command(goto="z", update={"count": 2})
        return {}

    def z(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("z")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed", "count"), run=writer),
            "z": NodeSpec(subscribes=("count",), run=z),
        },
        edges={},
    )

    run_super_steps(spec)

    assert executed == ["x#1", "x#2", "z"]


def test_the_goto_target_runs_even_when_its_subscribed_channels_have_no_value() -> None:
    """**SC-023**：``goto`` 目标订阅的通道**都没值** ⇒ 目标**照跑**（入参为空）。

    ⇒ 「目标因为入参为空而**没跑**」的现象 == **0** 次（裁定 17 · 上游实测同款）。
    """
    channels = _channels()
    channels["seed"].update([1])
    captured: list[dict[str, Any]] = []

    def writer(state: dict[str, Any]) -> Command:
        return Command(goto="z")

    def z(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=("count",), run=z),
        },
        edges={},
    )

    run_super_steps(spec)

    assert captured == [{}]


def test_the_goto_target_input_equals_the_sparse_read_of_the_sub_mapping() -> None:
    """**SC-023**：目标的入参 == ``read_channels(子映射)`` 的结果（**逐字相等**）。

    ⚠️ 子映射 MUST 按「**通道映射的顺序**」构造（裁定 26）⇒ 入参的 key 顺序
    与**整张状态表**的 key 顺序**天然一致**。
    """
    channels = _channels()
    channels["seed"].update([1])
    channels["count"].update([7])
    captured: list[dict[str, Any]] = []

    def writer(state: dict[str, Any]) -> Command:
        return Command(goto="z")

    def z(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=("count", "messages"), run=z),
        },
        edges={},
    )

    run_super_steps(spec)

    sub_mapping = {
        key: channel for key, channel in channels.items() if key in ("count", "messages")
    }
    expected = read_channels(sub_mapping)
    assert captured[0] == expected
    assert list(captured[0]) == list(expected)


def test_the_goto_target_reads_the_source_update() -> None:
    """**SC-023**：源节点 ``goto`` + ``update`` ⇒ 目标**读得到**这次更新。

    ⇒ 目标读的是**上一轮合并后**的状态（裁定 17 · 上游实测同款）。
    """
    channels = _channels()
    channels["seed"].update([1])
    captured: list[dict[str, Any]] = []

    def writer(state: dict[str, Any]) -> Command:
        return Command(goto="z", update={"count": 5})

    def z(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=("count",), run=z),
        },
        edges={},
    )

    run_super_steps(spec)

    assert captured[0]["count"] == 5


def test_a_multi_target_goto_triggers_every_target() -> None:
    """**SC-011**：``goto=("one", "two")`` ⇒ **全部**目标在下一轮被执行。

    ⇒ 与「单条命令 + 多目标 ``goto``」**同款**（裁定 9 · 上游实测同款）。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto=("one", "two"))

    def one(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("one")
        return {}

    def two(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("two")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "one": NodeSpec(subscribes=(), run=one),
            "two": NodeSpec(subscribes=(), run=two),
        },
        edges={},
    )

    run_super_steps(spec)

    assert executed == ["x", "one", "two"]


def test_an_empty_goto_sequence_produces_no_jump() -> None:
    """**SC-011**：``goto=()`` ⇒ **不产生跳转**（该位不产生动作）。"""
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto=())

    def z(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("z")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=(), run=z),
        },
        edges={},
    )

    run_super_steps(spec)

    assert executed == ["x"]


def test_goto_end_does_not_terminate_the_graph_and_the_update_still_applies() -> None:
    """**SC-008**：``goto=END`` ⇒ **不跳转、不终止**（静态边目标仍被执行）。

    ⇒ 终止是「**收敛**」的结果（裁定 5 · 上游实测同款）。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto="__end__", update={"messages": ["via-command"]})

    def y(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("y")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "y": NodeSpec(subscribes=(), run=y),
        },
        edges={"x": ("y",)},
    )

    result = run_super_steps(spec)

    assert executed == ["x", "y"]
    assert result.state["messages"] == ["via-command"]


def test_the_goto_target_is_not_executed_in_the_same_round() -> None:
    """**SC-001**：``goto`` 目标在**同一轮**内被执行的现象 == **0** 次。"""
    channels = _channels()
    channels["seed"].update([1])
    state = SchedulerState()

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=lambda state: Command(goto="z")),
            "z": NodeSpec(subscribes=(), run=lambda state: {}),
        },
        edges={},
    )

    first = run_super_step(spec, state)

    assert first.executed == ("x",)
