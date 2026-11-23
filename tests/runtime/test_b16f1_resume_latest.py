# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · ``Command(resume=...)`` 只读最新快照 + pending 保护。"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from freegraph.contracts import Command
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


def _id(config) -> str:
    value = config.configurable["checkpoint_id"]
    assert isinstance(value, str)
    return value


def test_resume_latest_and_old_pending_unchanged() -> None:
    compiled, saver = _run()
    first = _history(compiled)[0]
    first_pending = saver.get_tuple(first.config).pending_writes
    assert first_pending

    compiled.invoke(None, first.config)
    second = _history(compiled)[0]
    assert _id(second.config) != _id(first.config)
    assert saver.get_tuple(first.config).pending_writes == first_pending

    result = compiled.invoke(Command(resume="ok"), {"thread_id": "t"})
    assert result["log"] == ["a", "answered"]
    assert saver.get_tuple(first.config).pending_writes == first_pending


def test_resume_ignores_old_checkpoint_id() -> None:
    compiled, saver = _run()
    first = _history(compiled)[0]
    first_pending = saver.get_tuple(first.config).pending_writes

    compiled.invoke(None, first.config)
    second = _history(compiled)[0]
    assert _id(second.config) != _id(first.config)

    result = compiled.invoke(
        Command(resume="ok"),
        {
            "thread_id": "t",
            "configurable": {"checkpoint_id": _id(first.config)},
        },
    )
    assert result["log"] == ["a", "answered"]
    assert saver.get_tuple(first.config).pending_writes == first_pending
