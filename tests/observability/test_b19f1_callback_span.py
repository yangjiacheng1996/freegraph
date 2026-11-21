# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · US2：回调内 current_span() 与事件顺序。"""

from __future__ import annotations

from typing import Any, TypedDict

from freegraph.graph import END, START, StateGraph
from freegraph.observability import current_span

from .conftest import RecordingSink


class _State(TypedDict, total=False):
    x: int


class _OrderSink(RecordingSink):
    def __init__(self) -> None:
        super().__init__()
        self.order: list[str] = []
        self.in_start: list[Any] = []
        self.in_record: list[Any] = []
        self.in_end: list[Any] = []

    def on_span_start(self, span: Any) -> None:
        super().on_span_start(span)
        self.order.append("start")
        self.in_start.append(current_span())

    def on_trace_record(self, record: Any) -> None:
        super().on_trace_record(record)
        self.order.append("record")
        self.in_record.append(current_span())

    def on_span_end(self, span: Any) -> None:
        super().on_span_end(span)
        self.order.append("end")
        self.in_end.append(current_span())


def test_callback_order_and_current_span_values() -> None:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    sink = _OrderSink()
    builder.compile(tracer=sink).invoke({"x": 0})

    assert sink.order == ["start", "record", "end"]
    assert sink.in_start[0].id == sink.started[0].id
    assert sink.in_record[0].id == sink.started[0].id
    assert sink.in_end[0] is None
