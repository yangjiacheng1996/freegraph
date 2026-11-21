# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · invoke() 与 stream() 的逐节点输入 / 输出记录。"""

from __future__ import annotations

from typing import TypedDict

from freegraph.graph import END, START, StateGraph

from .conftest import B19RecordingSink


class _State(TypedDict, total=False):
    x: int
    y: int


def _graph() -> StateGraph:
    def a(state: _State) -> _State:
        return {"x": 1}

    def b(state: _State) -> _State:
        assert state.get("x") == 1
        return {"y": 2}

    builder = StateGraph(_State)
    builder.add_node("a", a)
    builder.add_node("b", b)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def test_invoke_records_have_complete_input_and_raw_output() -> None:
    sink = B19RecordingSink()
    _graph().compile(tracer=sink).invoke({"x": 0})
    a_record = next(record for record in sink.records if record.node == "a")
    b_record = next(record for record in sink.records if record.node == "b")
    assert a_record.input_state == {"x": 0}
    assert a_record.output_state == {"x": 1}
    assert b_record.input_state == {"x": 1}
    assert b_record.output_state == {"y": 2}


def test_stream_records_align_with_node_spans() -> None:
    sink = B19RecordingSink()
    app = _graph().compile(tracer=sink)
    list(app.stream({"x": 0}, stream_mode="updates"))
    assert len(sink.records) == len(sink.started) == 2
    assert {record.span_id for record in sink.records} == {
        span.id for span in sink.started
    }


def test_span_context_stays_empty_and_records_are_separate() -> None:
    sink = B19RecordingSink()
    _graph().compile(tracer=sink).invoke({"x": 0})
    assert all(span.context == {} for span in sink.started)
    assert all(record.input_state for record in sink.records)
