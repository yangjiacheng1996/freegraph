# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**写入合并**的用例 —— 属 **B7F1**（tasks T023 / T024 / T025）。

覆盖的判定：

* **SC-002** —— 同轮双写归约通道的合并结果与「两次写入的归约结果」**逐元素相等**；
* **SC-007** —— 节点返回 schema 外的 key ⇒ 抛 `InvalidUpdateError`，
  其 `invalid_keys` == **实际未知 key 集合**；
* **SC-023** —— 同轮双写**覆盖型**通道 ⇒ 抛 `InvalidChannelUpdateError`，
  其 `key` 字段指向该通道。

⚠️ **2026-11-12 · 上游对齐（P1-0-2）**：触发源**恒为边**（上游 ``branch:to:<node>``
· ``langgraph/graph/state.py:1531-1532``）⇒ 本文件的夹具一律带**入口边**
（``edges={"__start__": ("首节点",)}`）⇒ ``subscribes`` **只**决定「读哪些通道」，
**不再**是触发源。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Any

import pytest

from freegraph.contracts import InvalidUpdateError
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


def _channels() -> dict[str, Channel]:
    """构造通道状态：**归约型**（``messages``）+ **覆盖型**（``count``）。"""
    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "count": LastValue("count", int),
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


def _two_writers(first: Any, second: Any) -> GraphSpec:
    """构造一份「**两个节点同轮各写一次**」的图规格（节点表顺序 = ``a`` → ``b``）。

    ⚠️ 两个节点**同轮**被触发 ⇒ 触发它们的**入口边** MUST **同时**指向两者
    （触发源**恒为边** · 上游同款）⇒ ``edges={"__start__": ("a", "b")}``。
    """
    channels = _channels()
    channels["count"].update([0])
    return GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "a": NodeSpec(subscribes=("count",), run=lambda state: {"messages": first}),
            "b": NodeSpec(subscribes=("count",), run=lambda state: {"messages": second}),
        },
        edges={"__start__": ("a", "b")},
    )


# ── T023 · 归约通道的同轮双写（SC-002）──────────────────────────────────


def test_two_nodes_writing_the_reducing_channel_are_concatenated() -> None:
    """**SC-002**：同轮双写归约通道 ⇒ 结果 == 两次写入的**归约结果**（逐元素相等）。

    ⚠️ 「后写覆盖先写」的出现次数 == **0**（FR-005 ①）。
    """
    spec = _two_writers(["from-a"], ["from-b"])

    result = run_super_step(spec, SchedulerState())

    assert result.state["messages"] == operator.add(["from-a"], ["from-b"])
    assert result.state["messages"] == ["from-a", "from-b"]
    assert result.node_writes == {
        "a": {"messages": (["from-a"],)},
        "b": {"messages": (["from-b"],)},
    }


def test_the_reduced_values_follow_the_node_table_order() -> None:
    """**SC-002**：归约的**顺序** == **节点表顺序**（FR-005 · 裁定 9）。"""
    spec = _two_writers(["a1"], ["b1"])

    result = run_super_step(spec, SchedulerState())

    assert result.state["messages"] == ["a1", "b1"]


# ── T024 · 覆盖型通道的同轮双写（SC-023）────────────────────────────────


def test_two_nodes_writing_the_overwriting_channel_fail_explicitly() -> None:
    """**SC-023**：同轮双写**覆盖型**通道 ⇒ 抛 ``InvalidChannelUpdateError``。

    * 其 ``key`` 字段 MUST 指向该通道；
    * 「静默只保留后一个」的现象出现次数 == **0**。
    """
    channels = _channels()
    channels["count"].update([0])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "a": NodeSpec(subscribes=("count",), run=lambda state: {"count": 1}),
            "b": NodeSpec(subscribes=("count",), run=lambda state: {"count": 2}),
        },
        edges={"__start__": ("a", "b")},
    )

    with pytest.raises(InvalidChannelUpdateError) as excinfo:
        run_super_step(spec, SchedulerState())

    assert excinfo.value.key == "count"
    assert excinfo.value.received_count == 2
    assert excinfo.value.expected_count == 1


def test_the_overwriting_channel_keeps_its_value_after_the_conflict() -> None:
    """**SC-023**：冲突抛错 ⇒ 该通道的值**不变**（**先检测后写入**）。"""
    channels = _channels()
    channels["count"].update([7])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "a": NodeSpec(subscribes=("count",), run=lambda state: {"count": 1}),
            "b": NodeSpec(subscribes=("count",), run=lambda state: {"count": 2}),
        },
        edges={"__start__": ("a", "b")},
    )

    with pytest.raises(InvalidChannelUpdateError):
        run_super_step(spec, SchedulerState())

    assert channels["count"].get() == 7


# ── T025 · 未知 key（SC-007）─────────────────────────────────────────────


def test_a_node_writing_an_unknown_key_fails_explicitly() -> None:
    """**SC-007**：节点返回**通道映射之外**的 key ⇒ 抛 ``InvalidUpdateError``。

    * 其 ``invalid_keys`` MUST 列出**全部**未知 key；
    * 「静默丢弃未知 key」的出现次数 == **0**。
    """
    channels = _channels()
    channels["count"].update([0])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "a": NodeSpec(
                subscribes=("count",), run=lambda state: {"count": 1, "ghost": 2}
            ),
        },
        edges={"__start__": ("a",)},
    )

    with pytest.raises(InvalidUpdateError) as excinfo:
        run_super_step(spec, SchedulerState())

    assert excinfo.value.invalid_keys == ("ghost",)


def test_all_unknown_keys_are_reported_at_once() -> None:
    """**SC-007**：多个未知 key ⇒ **一次**报错列出**全部**（契约 §5.1 的校验顺序）。"""
    channels = _channels()
    channels["count"].update([0])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "a": NodeSpec(
                subscribes=("count",),
                run=lambda state: {"count": 1, "ghost_a": 2, "ghost_b": 3},
            ),
        },
        edges={"__start__": ("a",)},
    )

    with pytest.raises(InvalidUpdateError) as excinfo:
        run_super_step(spec, SchedulerState())

    assert sorted(excinfo.value.invalid_keys) == ["ghost_a", "ghost_b"]
