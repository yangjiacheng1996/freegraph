# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**一轮 super-step 的原子性**的用例 —— 属 **B7F1**（tasks T028）。

覆盖的判定：

* **SC-024** —— 本轮出错的用例中，出错后**全部**通道的值与**本轮开始前**
  **逐字相等**的比例 == **100%**；
* 四类触发场景（节点抛异常 · 未知 key · 归约器抛错 · 覆盖型多写冲突）
  **各自**被覆盖的用例数 ≥ **1**。

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


def _exploding_reducer(current: list[Any], new: Any) -> list[Any]:
    """一个**只在特定值上**抛错的归约器（其余值正常归约）。

    ⚠️ 归约器收到的是「**本次写入的整个值**」（此处 = ``["boom"]``）⇒ 判据
    按**列表内容**比较。
    """
    if new == ["boom"]:
        raise RuntimeError("reducer exploded")
    return operator.add(current, new)


def _channels() -> dict[str, Channel]:
    """构造通道状态：**覆盖型**（``a``）+ **归约型**（``b``）。"""
    return {
        "a": LastValue("a", int),
        "b": BinaryOperatorAggregate("b", list, _exploding_reducer),
    }


def _snapshot(channels: dict[str, Channel]) -> dict[str, Any]:
    """每个通道的「**值 / 有无值**」快照（原子性判定的基准）。"""
    snapshot: dict[str, Any] = {}
    for key, channel in channels.items():
        snapshot[key] = channel.get() if channel.is_available() else None
    return snapshot


# ── 场景 ① · 节点抛异常 ─────────────────────────────────────────────────


def test_a_node_exception_leaves_every_channel_unchanged() -> None:
    """**SC-024**：节点抛异常 ⇒ 出错后**全部**通道的值与**本轮开始前**相等。"""
    channels = _channels()
    channels["a"].update([1])
    channels["b"].update([["seed"]])
    before = _snapshot(channels)

    def node(state: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("node exploded")

    spec = GraphSpec(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("a",), run=node)},
        edges={},
    )

    with pytest.raises(RuntimeError):
        run_super_step(spec, SchedulerState())

    assert _snapshot(channels) == before


# ── 场景 ② · 未知 key ───────────────────────────────────────────────────


def test_an_unknown_key_leaves_every_channel_unchanged() -> None:
    """**SC-024**：节点返回 schema 外的 key ⇒ 出错后**全部**通道的值不变。"""
    channels = _channels()
    channels["a"].update([1])
    before = _snapshot(channels)

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("a",), run=lambda state: {"a": 2, "ghost": 3}
            )
        },
        edges={},
    )

    with pytest.raises(InvalidUpdateError):
        run_super_step(spec, SchedulerState())

    assert _snapshot(channels) == before


# ── 场景 ③ · 归约器抛错（**唯一需要真正回滚**的一类）───────────────────


def test_a_raising_reducer_rolls_back_the_whole_round() -> None:
    """**SC-024**：归约器抛错 ⇒ **本轮全部**写入**不合并** ⇒ 通道值不变。

    ⚠️ 这是四类错误中**唯一需要真正回滚**的一类（``b`` 抛错时 ``a`` **已经**
    被合并 ⇒ MUST 用**快照**逐通道回滚 · 契约 §5.4）。
    """
    channels = _channels()
    channels["a"].update([1])
    channels["b"].update([["seed"]])
    before = _snapshot(channels)

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("a",), run=lambda state: {"a": 99, "b": ["boom"]}
            )
        },
        edges={},
    )

    with pytest.raises(RuntimeError):
        run_super_step(spec, SchedulerState())

    assert _snapshot(channels) == before
    assert channels["a"].get() == 1
    assert channels["b"].get() == ["seed"]


# ── 场景 ④ · 覆盖型多写冲突 ─────────────────────────────────────────────


def test_an_overwrite_conflict_leaves_every_channel_unchanged() -> None:
    """**SC-024**：覆盖型通道同轮多写冲突 ⇒ 出错后**全部**通道的值不变。"""
    channels = _channels()
    channels["a"].update([1])
    before = _snapshot(channels)

    spec = GraphSpec(
        channels=channels,
        nodes={
            "first": NodeSpec(subscribes=("a",), run=lambda state: {"a": 2}),
            "second": NodeSpec(subscribes=("a",), run=lambda state: {"a": 3}),
        },
        edges={},
    )

    with pytest.raises(InvalidChannelUpdateError):
        run_super_step(spec, SchedulerState())

    assert _snapshot(channels) == before


def test_a_rollback_restores_a_channel_that_had_no_value() -> None:
    """**SC-024**：回滚时**无值**的通道 ⇒ **只** ``clear()``（不写回一个值）。

    ⚠️ 快照**无值** ⇒ **只** ``clear()``（无值快照**不是**一个可写回的值）·
    裁定 29 的补齐分支。

    ⚠️ 归约型通道在构造时**推导**出空值（``[]``）⇒ 它**有值** ⇒ 本用例用
    **覆盖型**通道（``c``）来构造「本轮开始前**无值**」的快照。
    """
    channels = _channels()
    channels["c"] = LastValue("c", int)
    channels["a"].update([1])
    before = _snapshot(channels)

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("a",),
                # ``c`` 本轮**无值** ⇒ 它的快照**无值** ⇒ 回滚只 ``clear()``。
                run=lambda state: {"c": 5, "b": ["boom"]},
            )
        },
        edges={},
    )

    with pytest.raises(RuntimeError):
        run_super_step(spec, SchedulerState())

    assert _snapshot(channels) == before
    assert channels["c"].is_available() is False


# ── 汇总 · 「部分通道已更新」的现象出现次数 == 0 ──────────────────────────

def test_no_round_leaves_a_partially_updated_state() -> None:
    """**SC-024**：「一部分通道已更新、一部分没更新」的用例数 == **0**。

    ⚠️ 四类错误**逐一**跑一遍 ⇒ 每次都断言「全部通道」都未变。
    """
    channels = _channels()
    channels["a"].update([1])
    channels["b"].update([["seed"]])
    before = _snapshot(channels)

    def raising_node(state: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("boom")

    def unknown_key_node(state: dict[str, Any]) -> dict[str, Any]:
        return {"ghost": 1}

    def raising_reducer_node(state: dict[str, Any]) -> dict[str, Any]:
        return {"b": ["boom"]}

    def conflicting_node(state: dict[str, Any]) -> dict[str, Any]:
        return {"a": 5}

    cases = [
        (raising_node, ValueError),
        (unknown_key_node, InvalidUpdateError),
        (raising_reducer_node, RuntimeError),
    ]
    for node, error_type in cases:
        spec = GraphSpec(
            channels=channels,
            nodes={"writer": NodeSpec(subscribes=("a",), run=node)},
            edges={},
        )
        with pytest.raises(error_type):
            run_super_step(spec, SchedulerState())
        assert _snapshot(channels) == before

    conflict_spec = GraphSpec(
        channels=channels,
        nodes={
            "first": NodeSpec(subscribes=("a",), run=conflicting_node),
            "second": NodeSpec(subscribes=("a",), run=conflicting_node),
        },
        edges={},
    )
    with pytest.raises(InvalidChannelUpdateError):
        run_super_step(conflict_spec, SchedulerState())
    assert _snapshot(channels) == before
