# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · US1：节点 span 的产生 / 字段 / 异常成对。"""

from __future__ import annotations

from typing import TypedDict

import pytest

from freegraph.graph import END, START, Send, StateGraph
from freegraph.observability import SpanProducer

from ._span_support import RecordingReceiver, bind_producer, node_spans


class _State(TypedDict, total=False):
    x: int


def _linear() -> tuple[object, RecordingReceiver]:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder.compile(), RecordingReceiver()


def test_single_node_produces_one_node_span_with_expected_fields() -> None:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    compiled = builder.compile()
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)

    with bind_producer(producer):
        compiled.invoke({"x": 0})

    assert len(receiver.started) == 1
    assert len(receiver.ended) == 1
    start = receiver.started[0]
    end = receiver.ended[0]
    assert start.id == end.id
    assert start.name == "a"
    assert start.node == "a"
    assert start.attributes == {}
    assert start.context == {}
    assert start.checkpoint_id is None
    assert start.parent is None
    assert start.end_time is None
    assert end.end_time is not None
    assert end.end_time > start.start_time
    assert start.run_id
    assert start.thread_id is None


def test_two_node_linear_graph_produces_two_node_spans() -> None:
    compiled, receiver = _linear()
    producer = SpanProducer(receiver)

    with bind_producer(producer):
        compiled.invoke({"x": 0})

    spans = node_spans(receiver)
    assert [span.name for span in spans] == ["a", "b"]
    assert len({span.id for span in spans}) == 2


def test_node_exception_still_ends_span_and_reraises_same_object() -> None:
    error = RuntimeError("boom")

    def boom(state: _State) -> _State:
        raise error

    builder = StateGraph(_State)
    builder.add_node("boom", boom)
    builder.add_edge(START, "boom")
    builder.add_edge("boom", END)
    compiled = builder.compile()
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)

    with bind_producer(producer):
        with pytest.raises(RuntimeError) as exc_info:
            compiled.invoke({"x": 0})

    assert exc_info.value is error
    assert len(receiver.started) == 1
    assert len(receiver.ended) == 1
    assert receiver.started[0].id == receiver.ended[0].id
    assert receiver.ended[0].end_time is not None
    assert receiver.started[0].attributes == {}
    assert "error.type" not in receiver.started[0].attributes
    assert "error.type" not in receiver.ended[0].attributes


def test_send_fanout_tasks_each_produce_a_node_span() -> None:
    builder = StateGraph(_State)
    builder.add_node("fan", lambda state: [Send("worker", {"x": 1}), Send("worker", {"x": 2})])
    builder.add_node("worker", lambda state: {})
    builder.add_edge(START, "fan")
    builder.add_edge("fan", "worker")
    builder.add_edge("worker", END)
    compiled = builder.compile()
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)

    with bind_producer(producer):
        compiled.invoke({"x": 0})

    spans = node_spans(receiver)
    assert [span.name for span in spans].count("worker") == 2
    assert [span.name for span in spans].count("fan") == 1


def test_untaken_branch_produces_no_span() -> None:
    builder = StateGraph(_State)
    builder.add_node("start", lambda state: {"x": 1})
    builder.add_node("a", lambda state: {"x": 2})
    builder.add_node("b", lambda state: {"x": 3})
    builder.add_edge(START, "start")
    builder.add_conditional_edges("start", lambda state: "a", ["a", "b"])
    builder.add_edge("a", END)
    builder.add_edge("b", END)
    compiled = builder.compile()
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)

    with bind_producer(producer):
        compiled.invoke({"x": 0})

    assert [span.name for span in node_spans(receiver)] == ["start", "a"]
