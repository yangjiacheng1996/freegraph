# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · US3：默认关闭的零副作用计数。"""

from __future__ import annotations

from typing import TypedDict

from freegraph.graph import END, START, StateGraph

from .conftest import (
    RecordingSink,
    RunIdBindingCounter,
    SpanConstructionCounter,
    SpanProducerConstructionCounter,
    TraceRecordConstructionCounter,
)


class _State(TypedDict, total=False):
    x: int


def _build() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def test_no_tracer_has_zero_span_producer_record_and_run_id(monkeypatch) -> None:
    spans = SpanConstructionCounter()
    producers = SpanProducerConstructionCounter()
    records = TraceRecordConstructionCounter()
    run_ids = RunIdBindingCounter()
    spans.install(monkeypatch)
    producers.install(monkeypatch)
    records.install(monkeypatch)
    run_ids.install(monkeypatch)

    app = _build().compile()
    assert app.invoke({"x": 0})["x"] == 2
    assert spans.count == 0
    assert producers.count == 0
    assert records.count == 0
    assert run_ids.calls == []


def test_explicit_none_is_equivalent_to_omitting(monkeypatch) -> None:
    spans = SpanConstructionCounter()
    producers = SpanProducerConstructionCounter()
    spans.install(monkeypatch)
    producers.install(monkeypatch)
    assert _build().compile(tracer=None).invoke({"x": 0})["x"] == 2
    assert spans.count == 0
    assert producers.count == 0


def test_injected_but_never_run_has_no_span_or_callback(monkeypatch) -> None:
    spans = SpanConstructionCounter()
    producers = SpanProducerConstructionCounter()
    run_ids = RunIdBindingCounter()
    spans.install(monkeypatch)
    producers.install(monkeypatch)
    run_ids.install(monkeypatch)
    sink = RecordingSink()
    _build().compile(tracer=sink)
    assert spans.count == 0
    assert producers.count == 0
    assert sink.started == []
    assert run_ids.calls == []
