# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · US4：关联键、stream 同源与 `RunConfig.run_id` 忽略。"""

from __future__ import annotations

from typing import TypedDict

from freegraph.graph import END, START, RunConfig, StateGraph
from freegraph.observability import SpanProducer

from ._span_support import RecordingReceiver, bind_producer


class _State(TypedDict, total=False):
    x: int


def _linear():
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder.compile()


def _run_invoke(config: RunConfig | None = None):
    compiled = _linear()
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)
    with bind_producer(producer):
        compiled.invoke({"x": 0}, config=config)
    return receiver


def test_every_span_has_non_empty_run_id_and_node() -> None:
    receiver = _run_invoke(RunConfig(thread_id="t-1"))
    assert len(receiver.started) == 2
    for span in receiver.started:
        assert span.run_id
        assert span.thread_id == "t-1"
        assert span.node == span.name
        assert span.checkpoint_id is None
    assert len({span.run_id for span in receiver.started}) == 1


def test_thread_id_uses_resolved_configurable_value() -> None:
    receiver = _run_invoke(RunConfig(configurable={"thread_id": "nested-t"}))
    assert {span.thread_id for span in receiver.started} == {"nested-t"}


def test_stream_events_and_spans_share_run_and_thread_ids() -> None:
    compiled = _linear()
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)
    with bind_producer(producer):
        events = list(
            compiled.stream(
                {"x": 0},
                config=RunConfig(thread_id="t-stream"),
                stream_mode="values",
            )
        )
    event_run_ids = {event["run_id"] for event in events}
    event_thread_ids = {event["thread_id"] for event in events}
    assert len(event_run_ids) == 1
    assert {span.run_id for span in receiver.started} == event_run_ids
    assert {span.thread_id for span in receiver.started} == event_thread_ids == {"t-stream"}


def test_run_config_run_id_is_ignored() -> None:
    receiver = _run_invoke(RunConfig(thread_id="t-1", run_id="user-supplied"))
    assert receiver.started
    assert all(span.run_id != "user-supplied" for span in receiver.started)
    assert len({span.run_id for span in receiver.started}) == 1


def test_separate_invokes_get_different_run_ids() -> None:
    first = _run_invoke()
    second = _run_invoke()
    assert first.started[0].run_id != second.started[0].run_id
