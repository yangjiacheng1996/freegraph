# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · US1：stream 与 span 共享 run_id / thread_id，信封不变。"""

from __future__ import annotations

from typing import TypedDict

from freegraph.graph import END, START, RunConfig, StateGraph

from .conftest import RecordingSink


class _State(TypedDict, total=False):
    x: int


def _graph() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def test_stream_events_and_spans_share_ids_and_envelope_has_no_trace_fields() -> None:
    sink = RecordingSink()
    app = _graph().compile(tracer=sink)
    events = list(
        app.stream({"x": 0}, config=RunConfig(thread_id="t-1"), stream_mode="updates")
    )
    event_ids = {(event["run_id"], event["thread_id"]) for event in events}
    span_ids = {(span.run_id, span.thread_id) for span in sink.started}
    assert event_ids == span_ids
    assert all("trace" not in event and "records" not in event for event in events)


def test_stream_works_without_tracer() -> None:
    app = _graph().compile()
    events = list(app.stream({"x": 0}, stream_mode="updates"))
    assert events
