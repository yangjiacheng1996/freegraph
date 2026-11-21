# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · US1：注入即推送、成对、id / thread_id / run_id。"""

from __future__ import annotations

from typing import TypedDict

from freegraph.graph import END, START, RunConfig, StateGraph

from .conftest import RecordingSink, SpanOnlySink


class _State(TypedDict, total=False):
    x: int


def _linear() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def test_injected_sink_receives_paired_node_spans() -> None:
    sink = RecordingSink()
    app = _linear().compile(tracer=sink)
    out = app.invoke({"x": 0}, config=RunConfig(thread_id="t-1"))

    assert out["x"] == 2
    assert len(sink.started) == len(sink.ended) == 2
    assert [span.name for span in sink.started] == ["a", "b"]
    assert {span.id for span in sink.started} == {span.id for span in sink.ended}
    for start in sink.started:
        assert start.end_time is None
        assert start.run_id
        assert start.thread_id == "t-1"
        assert start.checkpoint_id is None
        assert start.node == start.name
    for end in sink.ended:
        assert end.end_time is not None


def test_span_only_sink_is_accepted_and_produces_no_records() -> None:
    sink = SpanOnlySink()
    app = _linear().compile(tracer=sink)
    assert app.invoke({"x": 0})["x"] == 2
    assert len(sink.started) == len(sink.ended) == 2


def test_user_supplied_run_id_is_ignored() -> None:
    sink = RecordingSink()
    app = _linear().compile(tracer=sink)
    app.invoke({"x": 0}, config=RunConfig(run_id="user-supplied"))
    assert all(span.run_id and span.run_id != "user-supplied" for span in sink.started)


def test_thread_id_none_is_legal() -> None:
    sink = RecordingSink()
    app = _linear().compile(tracer=sink)
    app.invoke({"x": 0}, config=RunConfig(thread_id=None))
    assert all(span.thread_id is None for span in sink.started)
