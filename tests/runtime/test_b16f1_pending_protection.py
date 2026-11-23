# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · pending writes 只落新追加 checkpoint，原历史零变化。"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from freegraph.graph import END, START, StateGraph, interrupt
from freegraph.persistence import MemorySaver


class _State(TypedDict):
    log: Annotated[list, operator.add]


def _a(state: dict) -> dict:
    return {"log": ["a"]}


def _ask(state: dict) -> dict:
    interrupt({"ask": "approve"})
    return {"log": ["answered"]}


def _graph() -> StateGraph:
    graph = StateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("ask", _ask)
    graph.add_edge(START, "a")
    graph.add_edge("a", "ask")
    graph.add_edge("ask", END)
    return graph


def _run():
    saver = MemorySaver()
    compiled = _graph().compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "t"})
    return compiled, saver


def _history(compiled) -> list:
    return list(compiled.get_state_history({"thread_id": "t"}))


def test_replay_keeps_original_pending_writes() -> None:
    compiled, saver = _run()
    first = _history(compiled)[0]
    first_pending = saver.get_tuple(first.config).pending_writes
    assert first_pending

    compiled.invoke(None, first.config)
    second = _history(compiled)[0]
    assert saver.get_tuple(first.config).pending_writes == first_pending
    assert second.config.configurable["checkpoint_id"] != first.config.configurable["checkpoint_id"]


def test_fork_keeps_old_pending_writes() -> None:
    compiled, saver = _run()
    paused = _history(compiled)[0]
    old_pending = saver.get_tuple(paused.config).pending_writes
    base = next(
        s
        for s in _history(compiled)
        if s.next == ("ask",) and not s.interrupts
    )

    fork = compiled.update_state(base.config, {"log": ["fork"]}, as_node="a")
    assert saver.get_tuple(paused.config).pending_writes == old_pending
    assert saver.get_tuple(fork).pending_writes == ()

    compiled.invoke(None, fork)
    new_pause = _history(compiled)[0]
    assert new_pause.next == ("ask",)
    assert saver.get_tuple(paused.config).pending_writes == old_pending
    assert saver.get_tuple(new_pause.config).pending_writes
