# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**三形态共用同一条合并路径**的用例 —— 属 **B9F1**（tasks T017 / T018）。

⚠️ **触发模型**（上游对齐 · 2026-11-12）：触发源**恒为边** ⇒ 每张图 MUST 有
**入口边** ``{"__start__": (首节点,)}``（上游 ``add_edge(START, "a")`` 的同款写法）。

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
    """构造通道状态：**归约型**（``messages``）+ **覆盖型**（``count``）。

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


def _run_returning(result: Any) -> Any:
    """跑一个**只返回** ``result`` 的单节点图（靠**入口边**起跑）⇒ 合并后的状态。"""
    channels = _channels()
    channels["seed"].update([1])
    spec = _graph(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("seed",), run=lambda state: result)},
        edges={_START: ("writer",)},
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

    ⚠️ **上游同款**（上游对齐 · 2026-11-12）：触发源**恒为边** ⇒ 「同轮多写」
    MUST 由**同轮被触发的两个节点**构成 ⇒ 两个节点**都**挂**入口边**
    （``{"__start__": ("a", "b")}`` ⇒ 二者在第 1 轮**同时**被触发）。
    """
    channels = _channels()
    channels["seed"].update([1])
    spec = _graph(
        channels=channels,
        nodes={
            "a": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(update={"count": 1})
            ),
            "b": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(update={"count": 2})
            ),
        },
        edges={_START: ("a", "b")},
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


@pytest.mark.parametrize("max_concurrency", [1, None], ids=["serial", "concurrent"])
def test_every_goto_in_the_command_list_becomes_its_own_edge(max_concurrency: int | None) -> None:
    """**SC-021 ② / SC-005**：列表里**每条**命令的 ``goto`` 各自成边。

    ⇒ **全部**目标在下一轮被触发（与「单条命令 + 多目标 ``goto``」**同款**）。
    
    ⚠️ **B12F1（T069）**：本用例断言「用户侧副作用的**同轮完成顺序**」⇒
    并发下该顺序**不再确定** ⇒ **拆分而不删** —— ① **串行模式**
    （``max_concurrency=1``）**保留原逐字顺序断言**（**一条不删**）·
    ② **并发模式**（缺省）断言**顺序无关但有力**的性质
    （**元素多重集相等** + **次数相等**）⇒ **MUST NOT** 写成「跑过了就行」的弱断言。
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

    spec = _graph(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "one": NodeSpec(subscribes=(), run=one),
            "two": NodeSpec(subscribes=(), run=two),
        },
        edges={_START: ("writer",)},
    )

    run_super_steps(spec, max_concurrency=max_concurrency)

    if max_concurrency == 1:
        # ⚠️ **串行模式**：**原逐字**顺序断言（**一条不删**）
        assert executed == ["writer", "one", "two"]
    else:
        # ⚠️ **并发模式**：**顺序无关**但**有力**（元素多重集相等 + 次数相等）
        assert sorted(executed) == ['one', 'two', 'writer']
        assert len(executed) == 3


def test_an_empty_command_list_is_an_explicit_no_op() -> None:
    """**SC-021 ④**：**空列表** ⇒ **显式失败**（**上游同款** · 2026-11-12 上游对齐 P3）。

    ⚠️ 上游 ``langgraph/graph/state.py:1488-1492``：**空列表落 ``else``** ⇒
    ``InvalidUpdateError("Expected dict, got []")`` ⇒ freegraph 抛内置 ``TypeError``。
    """
    with pytest.raises(TypeError):
        _run_returning([])


def test_the_command_list_and_a_single_command_behave_identically() -> None:
    """**SC-021 ⑥**：命令列表与单条命令**行为分叉**的现象 == **0** 次。

    同一组写入分别以两种形态给出 ⇒ 合并结果**逐项一致**。
    """
    single = _run_returning(Command(update={"messages": ["x"], "count": 5}))
    listed = _run_returning([Command(update={"messages": ["x"], "count": 5})])

    assert single.state["messages"] == listed.state["messages"]
    assert single.state["count"] == listed.state["count"]
    assert single.node_writes == listed.node_writes
