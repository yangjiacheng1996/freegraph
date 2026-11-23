# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · ``update_state`` 的 L2 调度 / 后继 / 静态标记行为。"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest

from freegraph.contracts import InvalidUpdateError, RunConfig
from freegraph.graph import END, START, StateGraph
from freegraph.persistence import MemorySaver


class _State(TypedDict):
    x: int
    route: str
    log: Annotated[list, operator.add]


def _a(state: dict) -> dict:
    return {"x": 1, "route": state.get("route", "b"), "log": ["a"]}


def _b(state: dict) -> dict:
    return {"x": state.get("x", 0) + 1, "log": ["b"]}


def _c(state: dict) -> dict:
    return {"x": state.get("x", 0) + 10, "log": ["c"]}


def _router(state: dict) -> str:
    return state.get("route", "b")


def _conditional() -> StateGraph:
    graph = StateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("b", _b)
    graph.add_node("c", _c)
    graph.add_edge(START, "a")
    graph.add_conditional_edges("a", _router, ["b", "c"])
    graph.add_edge("b", END)
    graph.add_edge("c", END)
    return graph


def _linear() -> StateGraph:
    graph = StateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("b", _b)
    graph.add_node("c", _c)
    graph.add_edge(START, "a")
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", END)
    return graph


def _run(graph: StateGraph, input: dict | None = None):
    saver = MemorySaver()
    compiled = graph.compile(checkpointer=saver)
    compiled.invoke(input or {"log": [], "route": "b"}, {"thread_id": "t"})
    return compiled, saver


def _history(compiled) -> list:
    return list(compiled.get_state_history({"thread_id": "t"}))


def _id(config: RunConfig) -> str:
    value = config.configurable["checkpoint_id"]
    assert isinstance(value, str)
    return value


def test_as_node_omitted_on_terminal_with_many_updaters_is_ambiguous() -> None:
    compiled, _ = _run(_linear())
    terminal = _history(compiled)[0]
    with pytest.raises(InvalidUpdateError, match="Ambiguous update"):
        compiled.update_state(terminal.config, {"x": 2})


def test_as_node_missing_and_single_node_fallback() -> None:
    compiled, _ = _run(_linear())
    base = next(s for s in _history(compiled) if s.next == ("b",))
    with pytest.raises(InvalidUpdateError, match="missing"):
        compiled.update_state(base.config, {"x": 2}, as_node="missing")

    single = StateGraph(_State)
    single.add_node("only", _a)
    single.add_edge(START, "only")
    single.add_edge("only", END)
    compiled_single, _ = _run(single)
    terminal = _history(compiled_single)[0]
    fork = compiled_single.update_state(terminal.config, {"x": 3})
    assert compiled_single.get_state(fork).values["x"] == 3


def test_as_node_reevaluates_conditional_successors() -> None:
    compiled, _ = _run(_conditional())
    base = next(s for s in _history(compiled) if s.next == ("b",))
    fork = compiled.update_state(
        base.config, {"route": "c"}, as_node="a"
    )
    branch = compiled.get_state(fork)
    assert branch is not None
    assert branch.next == ("c",)
    result = compiled.invoke(None, fork)
    assert result["log"] == ["a", "c"]
    assert result["x"] == 11


def test_static_marks_are_cleared_on_new_branch() -> None:
    saver = MemorySaver()
    compiled = _linear().compile(checkpointer=saver, interrupt_before=["b"])
    compiled.invoke({"log": [], "route": "b"}, {"thread_id": "t"})
    paused = _history(compiled)[0]
    assert paused.next == ("b",)
    stored = saver.get_tuple(paused.config).scheduler
    assert stored["suspension_kind"] == "static_before"

    fork = compiled.update_state(paused.config, {"x": 5}, as_node="a")
    new_stored = saver.get_tuple(fork)
    assert new_stored.snapshot.metadata["suspension_kind"] is None
    assert new_stored.snapshot.metadata["static_ack"] is None
    assert new_stored.pending_writes == ()


def test_dynamic_pending_writes_are_not_copied() -> None:
    def ask(state: dict) -> dict:
        from freegraph.graph import interrupt

        interrupt({"ask": "approve"})
        return {"log": ["asked"]}

    graph = StateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("ask", ask)
    graph.add_edge(START, "a")
    graph.add_edge("a", "ask")
    graph.add_edge("ask", END)

    saver = MemorySaver()
    compiled = graph.compile(checkpointer=saver)
    compiled.invoke({"log": [], "route": "b"}, {"thread_id": "t"})
    paused = _history(compiled)[0]
    assert paused.next == ("ask",)
    assert saver.get_tuple(paused.config).pending_writes

    base = next(s for s in _history(compiled) if s.next == ("ask",) and not s.interrupts)
    fork = compiled.update_state(base.config, {"x": 8}, as_node="a")
    stored = saver.get_tuple(fork)
    assert stored.pending_writes == ()
    assert stored.snapshot.metadata["interrupts"] == ()
