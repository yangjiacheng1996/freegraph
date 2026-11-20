# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · run-scoped 生命周期（T059）。"""

from __future__ import annotations

from typing import Any, TypedDict

import pytest

from freegraph.graph import END, START, StateGraph
from freegraph.observability import SpanProducer

from ._span_support import RecordingReceiver, bind_producer


class _State(TypedDict, total=False):
    x: int


def _graph():
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder.compile()


def _install_binding_counter(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    import freegraph.runtime._stream_context as stream_context
    import freegraph.runtime.superstep as superstep

    calls: list[Any] = []
    original = stream_context.bind_run_ids

    def wrapper(run_id: str, thread_id: str | None) -> Any:
        calls.append((run_id, thread_id))
        return original(run_id, thread_id)

    monkeypatch.setattr(stream_context, "bind_run_ids", wrapper)
    monkeypatch.setattr(superstep, "bind_run_ids", wrapper)
    return calls


def test_scope_exit_stops_spans_and_reentry_gets_new_run_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compiled = _graph()
    calls = _install_binding_counter(monkeypatch)

    first_receiver = RecordingReceiver()
    first_producer = SpanProducer(first_receiver)
    with bind_producer(first_producer):
        compiled.invoke({"x": 0})
    first_run_ids = {span.run_id for span in first_receiver.started}
    assert len(calls) == 1
    assert len(first_run_ids) == 1

    before = len(first_receiver.started)
    compiled.invoke({"x": 0})  # tracer 作用域已退出
    assert len(first_receiver.started) == before
    assert len(calls) == 1

    second_receiver = RecordingReceiver()
    second_producer = SpanProducer(second_receiver)
    with bind_producer(second_producer):
        compiled.invoke({"x": 0})
    second_run_ids = {span.run_id for span in second_receiver.started}
    assert len(calls) == 2
    assert len(second_run_ids) == 1
    assert second_run_ids != first_run_ids


def test_no_tracer_never_binds_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    compiled = _graph()
    calls = _install_binding_counter(monkeypatch)
    compiled.invoke({"x": 0})
    assert calls == []
