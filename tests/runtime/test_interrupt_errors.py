# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**US2 的失败信号族** —— 中断 / 恢复路径的**显式失败**（**4 + 1** 个 reason）。

**判据**：SC-011（未挂 checkpointer ⇒ ``checkpointer_required``）·
SC-012（未提供恢复值 ⇒ ``resume_value_required``）· FR-014（没有挂起中断 ⇒
``no_pending_interrupt``）· FR-025（图运行之外 ⇒ ``not_in_run``）·
FR-013 ⑤（多挂起 + 单值 ⇒ ``ambiguous_resume``）。

**契约权威**：``specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md`
§7「失败信号汇总（**FS-1…FS-5**）」。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from typing import Any

import pytest

from freegraph.contracts.types import Command, RunConfig
from freegraph.graph import interrupt
from freegraph.runtime import GraphSpec, InterruptResult, NodeSpec, run_graph
from freegraph.runtime.channel import LastValue
from freegraph.runtime.errors import InterruptError

from .test_interrupt_checkpoint import StubCheckpointer

#: 图的通道（**覆盖型** · 无归约器 ⇒ 覆盖）。
_CHANNELS: dict[str, LastValue] = {
    "messages": LastValue("messages", list),
    "count": LastValue("count", int),
}


def _spec(nodes: dict[str, NodeSpec], edges: dict[str, tuple[str, ...]]) -> GraphSpec:
    """组装一张图规格（**入口哨兵** ``__start__`` 作为边源）。"""
    return GraphSpec(channels=dict(_CHANNELS), nodes=nodes, edges=edges)


def _ask_node() -> NodeSpec:
    """一个调用 ``interrupt("approve?")`` 的节点。"""

    def _run(state: dict[str, Any]) -> dict[str, Any]:
        interrupt("approve?")
        return {"messages": ["done"]}

    return NodeSpec(subscribes=(), run=_run)


def test_the_checkpointer_required_failure() -> None:
    """**SC-011** / **A4②**：``Command(resume="yes")`` 且**未挂** checkpointer ⇒
    ⇒ 抛 ``InterruptError`` 且 ``.reason == "checkpointer_required"`` ⇒ ⇒ 消息
    指明「恢复需要 checkpointer」（**消息要点与上游逐字同款**）。

    ⚠️ **必须**给出一个**非** ``None`` 的 ``resume`` 才触达该检查（**上游同款**
    · 实测 **E-25b**：上游的 checkpointer 检查**在** ``if resume is not None``
    **之内**）⇒ ⇒ **不**用 ``Command(resume=None)`` 来触发本用例。
    """
    spec = _spec({"ask": _ask_node()}, {"__start__": ("ask",)})

    with pytest.raises(InterruptError) as caught:
        run_graph(spec, Command(resume="yes"))

    assert caught.value.reason == "checkpointer_required"
    assert "Cannot resume without a checkpointer" in str(caught.value)
    # ⇒ 结构化原因码 ⇒ 上层**无须**解析消息
    assert caught.value.reason in InterruptError.REASONS


def test_the_resume_value_required_failure() -> None:
    """**SC-012**：``Command(resume=None)`` 与 ``Command()`` ⇒ 均抛
    ``InterruptError(reason="resume_value_required")`` ⇒ ⇒ **交叠情形**
    （**未提供恢复值** + **未挂** checkpointer）⇒ ⇒ **仍是**
    ``resume_value_required``（**未提供恢复值优先** · **上游同款** · 实测
    E-25a）⇒ ⇒ **不**写成 ``checkpointer_required``。
    """
    spec = _spec({"ask": _ask_node()}, {"__start__": ("ask",)})

    for command in (Command(resume=None), Command()):
        with pytest.raises(InterruptError) as caught:
            run_graph(spec, command)
        assert caught.value.reason == "resume_value_required"
        assert "resume value is required" in str(caught.value)


def test_the_no_pending_interrupt_failure() -> None:
    """**FR-014**：该会话**没有**挂起的中断时提交恢复 ⇒ ⇒ 抛
    ``InterruptError(reason="no_pending_interrupt")`` ⇒ ⇒ **不**静默当作
    「空状态从头跑」。"""
    stub = StubCheckpointer()
    spec = _spec({"ask": _ask_node()}, {"__start__": ("ask",)})

    # ⇒ 该会话**从来没有**跑过 ⇒ ⇒ 查不到任何快照
    with pytest.raises(InterruptError) as caught:
        run_graph(
            spec,
            Command(resume="yes"),
            checkpointer=stub,
            config=RunConfig(thread_id="t-empty"),
        )

    assert caught.value.reason == "no_pending_interrupt"
    assert "No pending interrupt to resume" in str(caught.value)


def test_the_not_in_run_failure() -> None:
    """**FR-025**：在**图运行之外**调用 ``interrupt()`` ⇒ ⇒ 抛
    ``InterruptError(reason="not_in_run")`` ⇒ ⇒ **不**静默返回 ``None``。"""
    with pytest.raises(InterruptError) as caught:
        interrupt("approve?")

    assert caught.value.reason == "not_in_run"
    assert "outside of a graph run" in str(caught.value)


def test_the_ambiguous_resume_failure() -> None:
    """**FR-013 ⑤**：跨节点**多个**挂起中断 + **单值**恢复 ⇒ ⇒ 抛
    ``InterruptError(reason="ambiguous_resume")`` ⇒ ⇒ 消息要点与上游同款。"""
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-ambiguous")

    def _make(name: str) -> NodeSpec:
        def _run(state: dict[str, Any]) -> dict[str, Any]:
            interrupt(f"approve-{name}")
            return {}

        return NodeSpec(subscribes=(), run=_run)

    spec = _spec(
        {"a": _make("a"), "b": _make("b")},
        {"__start__": ("a", "b")},
    )

    paused = run_graph(spec, checkpointer=stub, config=config)
    assert isinstance(paused, InterruptResult)
    assert len(paused.interrupts) == 2

    with pytest.raises(InterruptError) as caught:
        run_graph(spec, Command(resume="A"), checkpointer=stub, config=config)

    assert caught.value.reason == "ambiguous_resume"
    assert "you must specify the interrupt id" in str(caught.value)


def test_the_failure_carries_only_the_reason() -> None:
    """**裁定 3 ⑤**（澄清轮 **Q2**）：异常对象**只**带 ``reason`` ⇒ ⇒
    **不**携带会话标识 / 待恢复中断的 id 列表等**上下文**（那些是调用方自己
    传进去的）⇒ ⇒ 异常**只**回答「**为什么失败**」。"""
    spec = _spec({"ask": _ask_node()}, {"__start__": ("ask",)})

    with pytest.raises(InterruptError) as caught:
        run_graph(spec, Command(resume="yes"))

    payload = {
        name
        for name in vars(caught.value)
        if name not in {"reason", "args"}
    }
    assert payload == set()
    assert not isinstance(caught.value, ValueError)
    assert isinstance(caught.value, Exception)
