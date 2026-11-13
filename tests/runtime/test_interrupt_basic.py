# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**US1** · 节点挂起并把「要审批什么」交还调用方（**P1** · **MVP**）。

**判据**：SC-001（``.value`` / ``.id`` 均可读）· SC-004（中断前的写入**不丢失**）·
SC-009（同轮**多个**节点中断 ⇒ **全部**交还）· SC-010（``steps`` **如实计**）·
SC-008（**真异常优先** · 中断元组**丢弃**）。

**契约权威**：``specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md``
§4 / §5（data-model **V-1…V-7**）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from typing import Any

import pytest

from freegraph.graph import interrupt
from freegraph.runtime import (
    GraphSpec,
    InterruptResult,
    NodeSpec,
    SuperStepResult,
    run_graph,
)
from freegraph.runtime.channel import LastValue

#: 图的通道（**覆盖型** · 无归约器 ⇒ 覆盖）。
_CHANNELS: dict[str, LastValue] = {
    "messages": LastValue("messages", list),
    "count": LastValue("count", int),
}


def _spec(
    nodes: dict[str, NodeSpec], edges: dict[str, tuple[str, ...]]
) -> GraphSpec:
    """组装一张图规格（**入口哨兵** ``__start__`` 作为边源 · 上游同款）。"""
    return GraphSpec(channels=dict(_CHANNELS), nodes=nodes, edges=edges)


def _ask_node(value: str = "approve?", log: list[str] | None = None) -> NodeSpec:
    """一个调用 ``interrupt(value)`` 的节点。"""

    def _run(state: dict[str, Any]) -> dict[str, Any]:
        if log is not None:
            log.append("ask")
        answer = interrupt(value)
        return {"messages": [f"answer={answer}"]}

    return NodeSpec(subscribes=(), run=_run)


def test_the_interrupt_result_carries_value_and_id() -> None:
    """**SC-001** / **A3**：结果含 ``__interrupt__`` 键 · 元素 ``.value`` 逐字 ·
    ``.id`` 是 **32 位十六进制**（**100%** 的中断用例）。

    ⇒ ``.id`` 由**内核**生成（用户**未**自带）⇒ ⇒ **不可猜**（命名空间含
    随机 uuid4 · 上游同款）⇒ ⇒ 断言**形态**（正则）而**不**断言具体值。
    """
    spec = _spec({"ask": _ask_node()}, {"__start__": ("ask",)})

    result = run_graph(spec)

    assert isinstance(result, InterruptResult)
    assert "__interrupt__" in result.as_result_dict()
    payload = result.as_result_dict()["__interrupt__"]
    assert isinstance(payload, tuple)
    assert payload[0].value == "approve?"
    assert len(payload[0].id) == 32
    assert all(char in "0123456789abcdef" for char in payload[0].id)


def test_the_writes_preserved_before_the_interrupt() -> None:
    """**SC-004**：中断**前**已产生的状态写入**不丢失**（挂起**不是**回滚）·
    同轮**其它**节点的写入**照常合并**（**上游同款** · 实测 E-16 / E-21）。"""

    def _pre(state: dict[str, Any]) -> dict[str, Any]:
        return {"count": 99}

    spec = _spec(
        {"pre": NodeSpec(subscribes=(), run=_pre), "ask": _ask_node()},
        {"__start__": ("pre",), "pre": ("ask",)},
    )

    result = run_graph(spec)

    assert isinstance(result, InterruptResult)
    # ⚠️ 中断**前**的写入**保留** ⇒ ⇒ 挂起态的状态里含 ``count``
    assert result.state["count"] == 99


def test_the_same_round_writes_of_other_nodes_are_merged() -> None:
    """**SC-004** 的第二半：同轮**其它**节点的写入**照常合并**（挂起**不是**
    「整轮不落回」）⇒ ⇒ 被中断节点**自身**的写入**丢弃**（它**没完成**）。"""

    def _ok(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["ok"]}

    spec = _spec(
        {"ask": _ask_node(), "ok": NodeSpec(subscribes=(), run=_ok)},
        {"__start__": ("ask", "ok")},
    )

    result = run_graph(spec)

    assert isinstance(result, InterruptResult)
    assert result.state["messages"] == ["ok"]


def test_every_interrupted_node_is_reported() -> None:
    """**SC-009**：同一 super-step 内**两个**节点同时中断 ⇒ ``__interrupt__``
    的**两个**元素**都在** · ``.value`` 逐个对得上（**一个都不丢**）。

    ⇒ 元素顺序 = **节点名序**（**上游同款** · freegraph **更严**：上游是竞态）。
    """

    def _make(name: str) -> NodeSpec:
        def _run(state: dict[str, Any]) -> dict[str, Any]:
            interrupt(f"approve-{name}")
            return {}

        return NodeSpec(subscribes=(), run=_run)

    spec = _spec(
        {"a": _make("a"), "b": _make("b")},
        {"__start__": ("a", "b")},
    )

    result = run_graph(spec)

    assert isinstance(result, InterruptResult)
    values = sorted(item.value for item in result.interrupts)
    assert values == ["approve-a", "approve-b"]
    # ⚠️ 不同节点的 ``.id`` **互不相同**（**上游同款** · 实测 E-11）
    assert len({item.id for item in result.interrupts}) == 2


def test_the_paused_result_is_an_interrupt_result() -> None:
    """**SC-010** / **I-9**：中断轮**不**产出 ``SuperStepResult`` ⇒ 返回类型
    == ``InterruptResult`` · ``steps`` **如实计**（**含**被中断的那轮 ·
    **不含**空轮）· ``__interrupt__`` **不进** ``state``（形态污染）。

    ⚠️ ``executed`` 的**排序口径** = **节点名序**（**升序**）⇒ 与
    ``SuperStepResult.executed`` **同款**（但中断轮**没有** ``SuperStepResult``
    ⇒ **不**断言「两个对象逐字相等」）。
    """
    spec = _spec({"ask": _ask_node()}, {"__start__": ("ask",)})

    result = run_graph(spec)

    assert isinstance(result, InterruptResult)
    # ⚠️ **I-9**：中断轮**不**产出 ``SuperStepResult``（B12F1 裁定 24 ②）
    assert not isinstance(result, SuperStepResult)
    assert result.steps == 1
    assert "__interrupt__" not in result.state
    assert result.executed == ("ask",)


def test_a_real_exception_wins_over_the_interrupt() -> None:
    """**SC-008**（裁定 11 · **上游同款**）：同一 super-step 内**一个**节点抛
    真异常、**另一个**节点调 ``interrupt()`` ⇒ ⇒ 抛出的是**那个真异常**
    （类型 + 消息**原样**）⇒ ⇒ **结果里读不到**那批中断元组。

    ⚠️ 上游的**真异常优先**（``langgraph/pregel/_runner.py:687`` 先于 ``:690``）
    ⇒ ⇒ 中断元组**被丢弃** ⇒ ⇒ freegraph **MUST NOT** 自创留痕形态。
    """

    def _boom(state: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("boom")

    spec = _spec(
        {"ask": _ask_node(), "boom": NodeSpec(subscribes=(), run=_boom)},
        {"__start__": ("ask", "boom")},
    )

    with pytest.raises(ValueError) as caught:
        run_graph(spec)

    assert str(caught.value) == "boom"


def test_the_interrupt_payload_is_a_tuple_not_a_nested_tuple() -> None:
    """**I-3**：``__interrupt__`` 的**元素**带 ``.value`` 与 ``.id`` ⇒ ⇒
    **不是**嵌套元组（否则元素**没有**那两个属性 ⇒ 判据不可判定）。"""
    spec = _spec({"ask": _ask_node()}, {"__start__": ("ask",)})

    result = run_graph(spec)

    assert isinstance(result, InterruptResult)
    for item in result.interrupts:
        assert not isinstance(item, tuple)
        assert hasattr(item, "value")
        assert hasattr(item, "id")
