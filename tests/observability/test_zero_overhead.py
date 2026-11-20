# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · US3：未绑定 tracer 时零 span / 零回调 / 零 span 专用 id。"""

from __future__ import annotations

from typing import TypedDict

import pytest

from freegraph.graph import END, START, StateGraph
from freegraph.observability import invoke_model

from .conftest import (
    RecordingReceiver,
    RunIdBindingCounter,
    SpanConstructionCounter,
)


class _State(TypedDict, total=False):
    x: int


def _graph(*, fail: bool = False):
    builder = StateGraph(_State)

    def node(state: _State) -> _State:
        if fail:
            raise RuntimeError("boom")
        return {"x": 1}

    builder.add_node("n", node)
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    return builder.compile()


class Model:
    def invoke(self, value):
        return value


def test_no_tracer_no_span_no_callback_no_span_run_id(
    span_counter: SpanConstructionCounter,
    run_id_counter: RunIdBindingCounter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    span_counter.install(monkeypatch)
    run_id_counter.install(monkeypatch)
    receiver = RecordingReceiver()

    _graph().invoke({"x": 0})

    assert span_counter.count == 0
    assert run_id_counter.calls == []
    assert receiver.started == []
    assert receiver.ended == []


def test_no_tracer_exception_path_is_still_zero(
    span_counter: SpanConstructionCounter,
    run_id_counter: RunIdBindingCounter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    span_counter.install(monkeypatch)
    run_id_counter.install(monkeypatch)

    with pytest.raises(RuntimeError):
        _graph(fail=True).invoke({"x": 0})

    assert span_counter.count == 0
    assert run_id_counter.calls == []


def test_no_tracer_outside_node_helper_is_zero(
    span_counter: SpanConstructionCounter,
    run_id_counter: RunIdBindingCounter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    span_counter.install(monkeypatch)
    run_id_counter.install(monkeypatch)
    assert invoke_model(Model(), 1) == 1
    assert span_counter.count == 0
    assert run_id_counter.calls == []


def test_bound_tracer_produces_spans_for_sanity(
    bound_tracer: tuple[object, RecordingReceiver],
) -> None:
    _producer, receiver = bound_tracer
    _graph().invoke({"x": 0})
    assert len(receiver.started) == 1
    assert len(receiver.ended) == 1
