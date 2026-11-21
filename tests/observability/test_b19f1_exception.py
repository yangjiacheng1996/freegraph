# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · US1：异常路径仍成对 + 接收端异常隔离。"""

from __future__ import annotations

from typing import TypedDict

import pytest

from freegraph.graph import END, START, StateGraph

from .conftest import FailingSink, RecordingSink


class _State(TypedDict, total=False):
    x: int


def _boom_graph() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("boom", lambda state: (_ for _ in ()).throw(RuntimeError("boom")))
    builder.add_edge(START, "boom")
    builder.add_edge("boom", END)
    return builder


def test_node_exception_still_pairs_and_reraises_same_object() -> None:
    sink = RecordingSink()
    app = _boom_graph().compile(tracer=sink)
    with pytest.raises(RuntimeError) as info:
        app.invoke({"x": 0})
    assert str(info.value) == "boom"
    assert len(sink.started) == len(sink.ended) == 1
    assert sink.started[0].id == sink.ended[0].id
    assert sink.ended[0].end_time is not None


def test_failing_sink_is_isolated_and_node_error_is_preserved() -> None:
    normal = RecordingSink()
    failing = FailingSink()
    with pytest.raises(RuntimeError) as expected:
        _boom_graph().compile(tracer=normal).invoke({"x": 0})
    with pytest.raises(RuntimeError) as observed:
        _boom_graph().compile(tracer=failing).invoke({"x": 0})
    assert str(observed.value) == str(expected.value) == "boom"
    assert type(observed.value) is type(expected.value)
    assert failing.calls >= 2
