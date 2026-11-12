# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**原子性**（覆盖 ``Command`` 路径）的用例 —— 属 **B9F1**（tasks T028）。

⚠️ **触发模型**（上游对齐 · 2026-11-12）：触发源**恒为边** ⇒ 每张图 MUST 有
**入口边** ``{"__start__": (首节点,)}``（上游 ``add_edge(START, "a")`` 的同款写法）
⇒ 「同轮多写」的用例让相关节点**同轮**被触发（**都**挂入口边）。

覆盖的判定：

* **SC-013** —— ``Command.update`` 引发的四类错误（未知 key · 覆盖型多写 ·
  归约器抛错 · 与同轮其它节点的冲突）⇒ 出错后**全部**通道的值与**本轮开始前**
  **逐字相等** + 通道的**写入版本未推进**；「一部分通道已更新、一部分没更新」
  的用例数 == **0**。

⚠️ **MUST NOT** 改 B7F1 的回滚机制（快照 + 逐通道回滚 + 版本延后推进）⇒ 本
feature 只**复用**它 ⇒ 「原子性覆盖 ``Command`` 路径」= **同款处置**。

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
)


class _RaisingReducerChannel(BinaryOperatorAggregate):
    """**抛错的归约型通道** —— 归约器在合并时抛错（原子性的第四类错误）。"""

    def update(self, values: Any) -> bool:
        raise RuntimeError("reducer exploded")


def _channels() -> dict[str, Channel]:
    """构造通道状态：归约型（``messages``）+ 覆盖型（``count`` / ``seed``）。

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

    ⚠️ **同轮多写**的用例 MUST 让相关节点**同轮**被触发 ⇒ 它们**都**挂**入口边**
    （``{"__start__": ("a", "b")}`` ⇒ 二者在第 1 轮**同时**被触发）。
    """
    return GraphSpec(
        channels=channels,
        nodes={_START: _SENTINEL, **nodes},
        edges=edges,
    )


def _spec_with(result: Any) -> GraphSpec:
    """构造一个**只返回** ``result`` 的单节点图（靠**入口边**起跑）。"""
    channels = _channels()
    channels["seed"].update([1])
    return _graph(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("seed",), run=lambda state: result)},
        edges={_START: ("writer",)},
    )


def test_an_unknown_key_leaves_every_channel_unchanged() -> None:
    """**SC-013**：``Command.update`` 含未知 key ⇒ **全部**通道的值**不变**。"""
    spec = _spec_with(Command(update={"messages": ["x"], "ghost": 1}))

    with pytest.raises(InvalidUpdateError):
        run_super_step(spec, SchedulerState())

    assert spec.channels["messages"].get() == []
    assert spec.channels["count"].is_available() is False


def test_an_unknown_key_does_not_advance_the_channel_write_versions() -> None:
    """**SC-013**：出错后通道的**写入版本未推进**。"""
    spec = _spec_with(Command(update={"ghost": 1}))
    state = SchedulerState()

    with pytest.raises(InvalidUpdateError):
        run_super_step(spec, state)

    assert "messages" not in state.channel_versions
    assert "count" not in state.channel_versions


def test_an_overwriting_conflict_leaves_every_channel_unchanged() -> None:
    """**SC-013**：覆盖型通道同轮多写 ⇒ **全部**通道的值**不变**。"""
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

    with pytest.raises(InvalidChannelUpdateError):
        run_super_step(spec, SchedulerState())

    assert channels["count"].is_available() is False
    assert channels["messages"].get() == []


def test_a_raising_reducer_rolls_back_the_whole_round() -> None:
    """**SC-013**：归约器抛错 ⇒ **整轮回滚**（**唯一需要真正回滚**的一类）。"""
    channels: dict[str, Channel] = {
        "messages": _RaisingReducerChannel("messages", list, operator.add),
        "count": LastValue("count", int),
        "seed": LastValue("seed", int),
    }
    channels["seed"].update([1])
    spec = _graph(
        channels=channels,
        nodes={
            "a": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(update={"messages": ["x"]})
            ),
            "b": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(update={"count": 9})
            ),
        },
        edges={_START: ("a", "b")},
    )

    with pytest.raises(RuntimeError):
        run_super_step(spec, SchedulerState())

    assert channels["count"].is_available() is False


def test_a_conflict_with_another_node_leaves_every_channel_unchanged() -> None:
    """**SC-013**：与同轮**其它**节点的冲突 ⇒ **全部**通道的值**不变**。"""
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

    with pytest.raises(InvalidChannelUpdateError):
        run_super_step(spec, SchedulerState())

    assert channels["count"].is_available() is False
    assert channels["messages"].get() == []


def test_no_round_leaves_a_partially_updated_state() -> None:
    """**SC-013**：「一部分通道已更新、一部分没更新」的用例数 == **0**。"""
    channels = _channels()
    channels["seed"].update([1])
    spec = _graph(
        channels=channels,
        nodes={
            "a": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(update={"messages": ["x"]})
            ),
            "b": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(update={"ghost": 1})
            ),
        },
        edges={_START: ("a", "b")},
    )

    with pytest.raises(InvalidUpdateError):
        run_super_step(spec, SchedulerState())

    assert channels["messages"].get() == []
    assert channels["count"].is_available() is False


def test_the_command_path_rolls_back_exactly_like_the_plain_dict_path() -> None:
    """**SC-013**：``Command.update`` 与普通 ``dict`` 返回值**同款处置**。"""
    plain_spec = _spec_with({"messages": ["x"], "ghost": 1})
    command_spec = _spec_with(Command(update={"messages": ["x"], "ghost": 1}))

    with pytest.raises(InvalidUpdateError):
        run_super_step(plain_spec, SchedulerState())
    with pytest.raises(InvalidUpdateError):
        run_super_step(command_spec, SchedulerState())

    assert plain_spec.channels["messages"].get() == (
        command_spec.channels["messages"].get()
    )
    assert plain_spec.channels["count"].is_available() == (
        command_spec.channels["count"].is_available()
    )
