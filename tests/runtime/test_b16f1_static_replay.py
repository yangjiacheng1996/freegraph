# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · 静态快照的 replay / 分叉与 ack 水位。"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from freegraph.graph import END, START, StateGraph
from freegraph.persistence import MemorySaver


class _State(TypedDict):
    x: int
    log: Annotated[list, operator.add]


def _a(state: dict) -> dict:
    return {"x": 1, "log": ["a"]}


def _b(state: dict) -> dict:
    return {"log": ["b"]}


def _c(state: dict) -> dict:
    return {"log": ["c"]}


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


def _history(compiled) -> list:
    return list(compiled.get_state_history({"thread_id": "t"}))


def _id(config) -> str:
    value = config.configurable["checkpoint_id"]
    assert isinstance(value, str)
    return value


def test_static_before_replay_preserves_ack_and_completes() -> None:
    saver = MemorySaver()
    compiled = _linear().compile(checkpointer=saver, interrupt_before=["b"])
    compiled.invoke({"log": []}, {"thread_id": "t"})
    paused = _history(compiled)[0]
    assert paused.next == ("b",)
    original_pending = saver.get_tuple(paused.config).pending_writes
    before = _history(compiled)

    result = compiled.invoke(None, paused.config)
    assert result["log"] == ["a", "b", "c"]
    assert _history(compiled)[0].next == ()
    assert saver.get_tuple(paused.config).pending_writes == original_pending
    assert len(_history(compiled)) == len(before) + 3  # anchor + b + completion


def test_static_before_replay_from_earlier_retriggers() -> None:
    saver = MemorySaver()
    compiled = _linear().compile(checkpointer=saver, interrupt_before=["b"])
    compiled.invoke({"log": []}, {"thread_id": "t"})
    paused = _history(compiled)[0]
    entry = next(s for s in _history(compiled) if s.next == ("a",))

    result = compiled.invoke(None, entry.config)
    assert result.get("__interrupt__", ()) == ()
    latest = _history(compiled)[0]
    assert latest.next == ("b",)
    stored = saver.get_tuple(latest.config).scheduler
    assert stored["suspension_kind"] == "static_before"
    assert _id(latest.config) != _id(paused.config)


def test_update_state_clears_ack_then_successor_retriggers() -> None:
    saver = MemorySaver()
    compiled = _linear().compile(checkpointer=saver, interrupt_before=["b"])
    compiled.invoke({"log": []}, {"thread_id": "t"})
    paused = _history(compiled)[0]

    fork = compiled.update_state(paused.config, {"x": 9}, as_node="a")
    stored = saver.get_tuple(fork).snapshot.metadata
    assert stored["suspension_kind"] is None
    assert stored["static_ack"] is None

    compiled.invoke(None, fork)
    latest = _history(compiled)[0]
    assert latest.next == ("b",)
    assert saver.get_tuple(latest.config).scheduler["suspension_kind"] == "static_before"


def test_static_after_next_empty_replay_is_not_noop() -> None:
    saver = MemorySaver()
    compiled = _linear().compile(checkpointer=saver, interrupt_after=["c"])
    compiled.invoke({"log": []}, {"thread_id": "t"})
    paused = _history(compiled)[0]
    assert paused.next == ()
    assert saver.get_tuple(paused.config).scheduler["suspension_kind"] == "static_after"
    before = _history(compiled)

    result = compiled.invoke(None, paused.config)
    assert result["log"] == ["a", "b", "c"]
    after = _history(compiled)
    assert len(after) == len(before) + 2  # anchor + completion
    assert after[0].next == ()
    assert saver.get_tuple(after[0].config).scheduler["suspension_kind"] is None
