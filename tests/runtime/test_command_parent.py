# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**``Command.PARENT`` 与保留名**的用例 —— 属 **B9F1**（tasks T019 / T020 / T021）。

覆盖的判定：

* **SC-005** —— ``goto=Command.PARENT`` ⇒ **显式失败**（``NotImplementedError`` ·
  消息点名 ``__parent__`` 与「子图属 v2 能力」）；图规格含名为 ``__parent__``
  的节点 ⇒ **构造期**显式失败（``ValueError``）；两条失败信号**可区分**。

⚠️ **上游对照**：上游对 ``goto="__parent__"`` 只是 **warning + 忽略**
⇒ freegraph **刻意分叉**（parity **P-08 / X-2**）⇒ **静默失效**的现象 == **0**。

**手写图规格**驱动 ⇒ MUST **不经由** ``StateGraph`` / ``compile()`` /
``invoke()``（FR-020 · SC-016）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator

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
)


def _channels() -> dict[str, Channel]:
    """构造通道状态：**归约型**（``messages``）+ **覆盖型**（``seed``）。"""
    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "seed": LastValue("seed", int),
    }


def test_goto_parent_fails_explicitly_at_runtime() -> None:
    """**SC-005**：``goto=Command.PARENT`` ⇒ 抛 ``NotImplementedError``。

    ⇒ **MUST NOT** 静默失效（上游同款是 warning + 忽略 ⇒ freegraph **分叉**）。
    """
    channels = _channels()
    channels["seed"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(goto=Command.PARENT)
            )
        },
        edges={},
    )

    with pytest.raises(NotImplementedError) as excinfo:
        run_super_step(spec, SchedulerState())

    message = str(excinfo.value)
    assert "__parent__" in message
    assert "v2" in message


def test_the_parent_failure_message_names_the_v2_subgraph_boundary() -> None:
    """**SC-005**：消息点名「子图属 v2 能力」⇒ 用户知道**缺的是哪块能力**。"""
    channels = _channels()
    channels["seed"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(goto=Command.PARENT)
            )
        },
        edges={},
    )

    with pytest.raises(NotImplementedError) as excinfo:
        run_super_step(spec, SchedulerState())

    assert "子图属 v2 能力" in str(excinfo.value)


def test_a_graph_with_a_node_named_parent_fails_at_construction_time() -> None:
    """**SC-005**：图规格含名为 ``__parent__`` 的节点 ⇒ **构造期**抛 ``ValueError``。

    ⇒ ``__parent__`` 是**保留名** ⇒ 杜绝「用户自建同名节点 ⇒ ``Command.PARENT``
    跳到它」的**语义歧义**（宪法原则 VIII 的术语纪律）。
    """
    with pytest.raises(ValueError) as excinfo:
        GraphSpec(
            channels=_channels(),
            nodes={"__parent__": NodeSpec(subscribes=(), run=lambda state: {})},
            edges={},
        )

    assert "__parent__" in str(excinfo.value)


def test_the_parent_failure_and_the_unknown_target_failure_are_distinguishable() -> None:
    """**SC-005**：``NotImplementedError`` 与 ``ValueError`` **可区分**。

    ⇒ 「**写错了**」（名字不存在 ⇒ ``ValueError``）与「**合法但未实现**」
    （``Command.PARENT`` ⇒ ``NotImplementedError``）是**两种语义** ⇒ 用户（及
    下游 freechain）可**分别捕获**（裁定 7 · 澄清轮第 2 次 **Q2**）。
    """
    channels = _channels()
    channels["seed"].update([1])

    parent_spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(goto=Command.PARENT)
            )
        },
        edges={},
    )
    unknown_spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(goto="no-such-node")
            )
        },
        edges={},
    )

    with pytest.raises(NotImplementedError):
        run_super_step(parent_spec, SchedulerState())
    with pytest.raises(ValueError):
        run_super_step(unknown_spec, SchedulerState())

    assert not isinstance(NotImplementedError(), ValueError)
