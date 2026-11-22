# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B14F1 · 「真异常 + 中断同现」时中断随 pending writes 留痕。"""

from __future__ import annotations

from typing import Any, TypedDict

import pytest

from freegraph.contracts import RunConfig
from freegraph.graph import END, START, StateGraph, interrupt
from freegraph.persistence import MemorySaver


class _State(TypedDict, total=False):
    x: Any


class _Boom(RuntimeError):
    pass


def _graph(captured: list[BaseException]) -> StateGraph:
    def boom(state: _State) -> _State:
        error = _Boom("boom")
        captured.append(error)
        raise error

    def ask(state: _State) -> _State:
        interrupt("approve?")
        return {"x": 1}

    builder = StateGraph(_State)
    builder.add_node("boom", boom)
    builder.add_node("ask", ask)
    builder.add_edge(START, "boom")
    builder.add_edge(START, "ask")
    builder.add_edge("boom", END)
    builder.add_edge("ask", END)
    return builder


def test_true_error_with_interrupt_leaves_pending_write() -> None:
    captured: list[BaseException] = []
    saver = MemorySaver()
    cfg = RunConfig(thread_id="err-int")
    app = _graph(captured).compile(checkpointer=saver)
    with pytest.raises(_Boom) as excinfo:
        app.invoke({"x": 0}, cfg)
    assert excinfo.value is captured[0]

    stored = saver.get_tuple(cfg)
    assert stored is not None
    interrupt_writes = [
        item for item in stored.pending_writes if item[1] == "__interrupt__"
    ]
    assert len(interrupt_writes) == 1
    assert stored.snapshot.tasks == ()


def test_exception_identity_type_message_and_existing_notes_are_preserved() -> None:
    plain_captured: list[BaseException] = []
    with pytest.raises(_Boom) as plain:
        _graph(plain_captured).compile().invoke({"x": 0}, RunConfig(thread_id="p"))

    saver_captured: list[BaseException] = []
    saver = MemorySaver()
    with pytest.raises(_Boom) as with_saver:
        _graph(saver_captured).compile(checkpointer=saver).invoke(
            {"x": 0}, RunConfig(thread_id="s")
        )

    assert with_saver.value is saver_captured[0]
    assert plain.value is plain_captured[0]
    assert type(with_saver.value) is type(plain.value)
    assert str(with_saver.value) == str(plain.value)
    assert len(getattr(with_saver.value, "__notes__", ())) == len(
        getattr(plain.value, "__notes__", ())
    )
