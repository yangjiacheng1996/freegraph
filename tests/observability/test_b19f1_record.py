# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · 补充 TraceRecord 字段 / raw 输出 / JSON 视图。"""

from __future__ import annotations

import json
from typing import Annotated, TypedDict

import operator

from freegraph.graph import END, START, Command, StateGraph

from .conftest import RecordingSink


class _State(TypedDict, total=False):
    x: int
    log: Annotated[list, operator.add]


def test_record_fields_match_node_span_and_preserve_raw_output() -> None:
    def a(state: _State) -> Command:
        return Command(update={"x": 1}, goto="b")

    def b(state: _State) -> _State:
        return {"log": ["b"]}

    builder = StateGraph(_State)
    builder.add_node("a", a)
    builder.add_node("b", b)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    sink = RecordingSink()
    builder.compile(tracer=sink).invoke({"x": 0})

    record = next(item for item in sink.records if item.node == "a")
    span = next(item for item in sink.started if item.name == "a")
    assert record.span_id == span.id
    assert record.task_id == "a"
    assert record.run_id == span.run_id
    assert record.thread_id == span.thread_id
    assert record.checkpoint_id == span.checkpoint_id
    assert record.superstep == 0
    assert record.input_state["x"] == 0
    assert "log" in record.input_state
    assert isinstance(record.output_state, str)
    assert "Command" in record.output_state
    assert record.error is None
    assert json.dumps(record.to_jsonable())
