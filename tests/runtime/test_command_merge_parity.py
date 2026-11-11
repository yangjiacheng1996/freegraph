# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**三形态共用同一条合并路径**的用例 —— 属 **B9F1**（tasks T017 / T018）。

覆盖的判定：

* **SC-003** —— 同一 key 分别以「返回 ``dict``」「返回 ``Command(update=)」
  「返回**命令列表**」写入时，合并结果**逐项一致**；未知 key ⇒ 三者**都**抛
  ``InvalidUpdateError`` 且 ``invalid_keys`` **一致**；
* **SC-004** —— ``Command.update`` 含未知 key ⇒ 抛 ``InvalidUpdateError``，
  其 ``invalid_keys`` == **实际未知 key 集合**（顺序保持）；
* **SC-021** —— **命令列表**（上游同款）：按**列表顺序**合并 · 每条 ``goto``
  各自成边 · 混入 ``dict`` 按所在位置生效 · **空列表** = 无操作；
* **SC-023** —— 覆盖型通道同轮多写 ⇒ 抛 ``InvalidChannelUpdateError``
  （B5F1 既有类型 · **零新增错误类型**）。

**手写图规格**驱动 ⇒ MUST **不经由** ``StateGraph`` / ``compile()`` /
``invoke()``（FR-020 · SC-016）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Any

import pytest

from freegraph.contracts import Command, InvalidUpdateError
from freegraph.runtime import (
    BinaryOperatorAggregate,
    Channel,
    GraphSpec,
    InvalidChannelUpdateError,
    LastValue,
    NodeSpec,
    SchedulerState,
    run_super_step,
    run_super_steps,
)


def _channels() -> dict[str, Channel]:
    """构造通道状态：**归约型**（``messages``）+ **覆盖型**（``count``）。"""
    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "count": LastValue("count", int),
        "seed": LastValue("seed", int),
    }


def _run_returning(result: Any) -> Any:
    """跑一个**只返回** ``result`` 的单节点图 ⇒ 合并后的状态。"""
    channels = _channels()
    channels["seed"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("seed",), run=lambda state: result)},
        edges={},
    )
    return run_super_step(spec, SchedulerState())


def test_the_three_return_forms_merge_identically() -> None:
    """**SC-003**：三种返回形态的合并结果**逐项相等**。

    ⇒ 「**行为分叉**」的现象 == **0** 次（归一 ⇒ **一条**合并路径）。
    """
    plain = _run_returning({"messages": ["b"]})
    command = _run_returning(Command(update={"messages": ["b"]}))
    listed = _run_returning([Command(update={"messages": ["b"]})])

    assert plain.state["messages"] == command.state["messages"]
    assert command.state["messages"] == listed.state["messages"]
    assert plain.state["messages"] == operator.add([], ["b"])


def test_the_three_return_forms_reject_unknown_keys_identically() -> None:
    """**SC-003 / SC-004**：三种形态写未知 key ⇒ **都**抛同一类型的错。

    且 ``invalid_keys`` **一致**（顺序保持）⇒ 「未知 key 只对 ``dict`` 报错」
    这类分叉**物理不可能**发生。
    """
    errors: list[InvalidUpdateError] = []
    for result in (
        {"ghost": 1},
        Command(update={"ghost": 1}),
        [Command(update={"ghost": 1})],
    ):
        with pytest.raises(InvalidUpdateError) as excinfo:
            _run_returning(result)
        errors.append(excinfo.value)

    assert all(error.invalid_keys == ("ghost",) for error in errors)
    assert all(
        type(error) is InvalidUpdateError for error in errors
    ), "失败信号的类型 MUST **逐项一致**"


def test_a_command_update_with_multiple_unknown_keys_lists_all_of_them() -> None:
    """**SC-004**：``invalid_keys`` 列出**全部**未知 key（顺序保持）。"""
    with pytest.raises(InvalidUpdateError) as excinfo:
        _run_returning(Command(update={"ghost_a": 1, "ghost_b": 2}))

    assert excinfo.value.invalid_keys == ("ghost_a", "ghost_b")


def test_a_command_update_on_an_overwriting_channel_conflicts_like_a_plain_dict() -> None:
    """**SC-003 / SC-023**：覆盖型通道同轮多写 ⇒ ``InvalidChannelUpdateError``。

    ⚠️ **零新增错误类型** —— 复用 B5F1 的既有类型（复用 B7F1 的**同一条**合并
    路径 ⇒ 与普通返回值**同款**）。
    """
    channels = _channels()
    channels["seed"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "a": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(update={"count": 1})
            ),
            "b": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(update={"count": 2})
            ),
        },
        edges={},
    )

    with pytest.raises(InvalidChannelUpdateError) as excinfo:
        run_super_step(spec, SchedulerState())

    assert excinfo.value.key == "count"


def test_the_command_list_writes_merge_in_list_order() -> None:
    """**SC-021 ①**：列表内多条命令的写入按**列表顺序**合并。

    ⇒ 归约型通道的结果与「按列表顺序逐条写入」**逐元素相等**。
    """
    result = _run_returning(
        [
            Command(update={"messages": ["first"]}),
            Command(update={"messages": ["second"]}),
        ]
    )

    assert result.state["messages"] == operator.add(
        operator.add([], ["first"]), ["second"]
    )


def test_the_command_list_writes_are_not_overwritten_by_a_later_command() -> None:
    """**SC-021 ①**：同 key 的多条命令 ⇒ **后者不覆盖前者**（值序列）。

    ⇒ 归约型通道上**两个值都在**（按列表顺序）⇒ 若被压成单值，第二个会
    **覆盖**第一个 ⇒ 与 FR-004 / 裁定 15 的「MUST NOT 让后一条命令覆盖前一条」
    **直接冲突**。
    """
    result = _run_returning(
        [
            Command(update={"messages": ["first"]}),
            Command(update={"messages": ["second"]}),
        ]
    )

    assert result.state["messages"] == ["first", "second"]


def test_a_command_list_writing_the_overwriting_channel_twice_fails_explicitly() -> None:
    """**SC-021 ① + SC-023**：列表内同 key 写**覆盖型**通道 ⇒ **显式失败**。

    ⚠️ **零新增错误类型** —— 复用 B5F1 的既有 ``InvalidChannelUpdateError``
    （同一条合并路径 ⇒ 与普通返回值**同款**）。
    """
    with pytest.raises(InvalidChannelUpdateError) as excinfo:
        _run_returning(
            [
                Command(update={"count": 1}),
                Command(update={"count": 2}),
            ]
        )

    assert excinfo.value.key == "count"


def test_a_dict_element_in_the_command_list_applies_at_its_position() -> None:
    """**SC-021 ③**：列表里**混入的** ``dict`` 按其**所在位置**生效。

    ⇒ 与「单独返回该 dict」**逐项一致**。
    """
    listed = _run_returning([Command(update={"messages": ["a"]}), {"messages": ["b"]}])
    plain = _run_returning({"messages": ["b"]})

    assert listed.state["messages"] == operator.add(
        operator.add([], ["a"]), ["b"]
    )
    assert listed.state["messages"][-1] == plain.state["messages"][-1]


def test_every_goto_in_the_command_list_becomes_its_own_edge() -> None:
    """**SC-021 ② / SC-005**：列表里**每条**命令的 ``goto`` 各自成边。

    ⇒ **全部**目标在下一轮被触发（与「单条命令 + 多目标 ``goto``」**同款**）。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> list[Command]:
        executed.append("writer")
        return [Command(goto="one"), Command(goto="two")]

    def one(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("one")
        return {}

    def two(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("two")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "one": NodeSpec(subscribes=(), run=one),
            "two": NodeSpec(subscribes=(), run=two),
        },
        edges={},
    )

    run_super_steps(spec)

    assert executed == ["writer", "one", "two"]


def test_an_empty_command_list_is_an_explicit_no_op() -> None:
    """**SC-021 ④**：**空列表** ⇒ 零写入 + 零跳转（且节点仍计入执行记录）。"""
    result = _run_returning([])

    assert result.executed == ("writer",)
    assert result.state["messages"] == []
    assert result.node_writes == {"writer": {}}


def test_the_command_list_and_a_single_command_behave_identically() -> None:
    """**SC-021 ⑥**：命令列表与单条命令**行为分叉**的现象 == **0** 次。

    同一组写入分别以两种形态给出 ⇒ 合并结果**逐项一致**。
    """
    single = _run_returning(Command(update={"messages": ["x"], "count": 5}))
    listed = _run_returning([Command(update={"messages": ["x"], "count": 5})])

    assert single.state["messages"] == listed.state["messages"]
    assert single.state["count"] == listed.state["count"]
    assert single.node_writes == listed.node_writes
