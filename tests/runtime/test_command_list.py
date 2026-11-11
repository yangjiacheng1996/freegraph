# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**命令列表**的用例 —— 属 **B9F1**（tasks T018 的**专属**用例）。

覆盖的判定：

* **SC-021** —— 命令列表（**上游同款**）：① 写入按**列表顺序**合并 ·
  ② 每条命令的 ``goto`` **各自成边** · ③ 混入的 ``dict`` 按**所在位置**生效 ·
  ④ **空列表** = 无操作 · ⑤ 元素类型非法 ⇒ ``TypeError`` · ⑥ 与单条命令
  **行为分叉**的现象 == **0** 次。

⚠️ 与 ``test_command_merge_parity.py`` 的分工：后者验「三形态**共用同一条**
合并路径」的**等价性**；本文件验命令列表**自身**的**顺序 / 位置 / 空列表**
语义。

**手写图规格**驱动 ⇒ MUST **不经由** ``StateGraph`` / ``compile()`` /
``invoke()``（FR-020 · SC-016）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Any

import pytest

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
    """构造通道状态：**归约型**（``messages``）+ 覆盖型（``count`` / ``seed``）。"""
    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "count": LastValue("count", int),
        "seed": LastValue("seed", int),
    }


def _run_returning(result: Any) -> Any:
    """跑一个**只返回** ``result`` 的单节点图。"""
    channels = _channels()
    channels["seed"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("seed",), run=lambda state: result)},
        edges={},
    )
    return run_super_step(spec, SchedulerState())


def test_the_command_list_writes_are_merged_in_the_list_order() -> None:
    """**SC-021 ①**：多条命令的写入按**列表顺序**归约（**逐元素相等**）。

    ⇒ 与上游 ``_get_updates`` 的 ``updates.extend(...)`` 顺序**逐字一致**。
    """
    result = _run_returning(
        [
            Command(update={"messages": ["a"]}),
            Command(update={"messages": ["b"]}),
            Command(update={"messages": ["c"]}),
        ]
    )

    assert result.state["messages"] == ["a", "b", "c"]


def test_the_command_list_gotos_become_separate_edges() -> None:
    """**SC-021 ②**：列表里**每条**命令的 ``goto`` **各自成边**。

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


def test_the_command_list_gotos_are_deduplicated_in_order() -> None:
    """**SC-021 ②**：重复的 ``goto`` 目标**去重**（保序）⇒ 不重复触发。"""
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> list[Command]:
        executed.append("writer")
        return [Command(goto="one"), Command(goto="one")]

    def one(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("one")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "one": NodeSpec(subscribes=(), run=one),
        },
        edges={},
    )

    run_super_steps(spec)

    assert executed == ["writer", "one"]


def test_a_goto_sequence_with_a_duplicate_target_is_deduplicated() -> None:
    """**SC-011 / I-5**：多目标 ``goto`` 里的**重复**目标**去重**（保序）。

    ⇒ 重复目标**只**成为**一条**边 ⇒ 该目标**只**被执行一次
    （契约 §3「保序去重」）。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("writer")
        return Command(goto=("one", "one"))

    def one(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("one")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "one": NodeSpec(subscribes=(), run=one),
        },
        edges={},
    )

    run_super_steps(spec)

    assert executed == ["writer", "one"]


def test_a_dict_element_in_the_command_list_applies_at_its_own_position() -> None:
    """**SC-021 ③**：混入的 ``dict`` 按其**所在位置**生效。

    ⇒ 与「单独返回该 dict」**逐项一致**。
    """
    listed = _run_returning(
        [Command(update={"messages": ["a"]}), {"messages": ["b"]}, Command(update={"messages": ["c"]})]
    )

    assert listed.state["messages"] == ["a", "b", "c"]


def test_an_empty_command_list_is_an_explicit_no_op() -> None:
    """**SC-021 ④**：**空列表** ⇒ 零写入 + 零跳转（节点仍计入执行记录）。"""
    result = _run_returning([])

    assert result.executed == ("writer",)
    assert result.state["messages"] == []
    assert result.node_writes == {"writer": {}}


def test_an_illegal_command_list_element_fails_with_a_type_error() -> None:
    """**SC-021 ⑤**：元素类型非法 ⇒ 内置 ``TypeError``（V-10）。"""
    for bad in ([1], ["text"], [None]):
        with pytest.raises(TypeError):
            _run_returning(bad)


def test_the_command_list_and_a_single_command_do_not_diverge() -> None:
    """**SC-021 ⑥**：命令列表与单条命令**行为分叉**的现象 == **0** 次。

    ⇒ 同一组写入分别以两种形态给出 ⇒ 合并结果**逐项一致**。
    """
    single = _run_returning(Command(update={"messages": ["x"], "count": 3}))
    listed = _run_returning([Command(update={"messages": ["x"], "count": 3})])

    assert single.state["messages"] == listed.state["messages"]
    assert single.state["count"] == listed.state["count"]
    assert single.node_writes == listed.node_writes
    assert single.executed == listed.executed
