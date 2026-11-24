# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B21F1 · US3：失败隔离 / 四路诊断 / BaseException / 不重试 / 并发。"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

import pytest
from opentelemetry.sdk.trace.export import SpanExportResult

from freegraph.graph import END, START, StateGraph
from freegraph.observability import OtlpExporter

from .conftest import RecordingSpanExporter, make_span


class _State(TypedDict, total=False):
    x: int


class _BarrierState(TypedDict, total=False):
    log: Annotated[list, operator.add]


class _RaisingExporter:
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc
        self.calls = 0

    def export(self, spans: Any) -> Any:
        self.calls += 1
        raise self.exc


class _FailureExporter:
    def __init__(self) -> None:
        self.calls = 0

    def export(self, spans: Any) -> Any:
        self.calls += 1
        return SpanExportResult.FAILURE


def _graph(tracer: Any) -> Any:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_node("b", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder.compile(tracer=tracer)


def _barrier_graph(tracer: Any) -> Any:
    builder = StateGraph(_BarrierState)
    builder.add_node("a", lambda state: {"log": ["a"]})
    builder.add_node("b", lambda state: {"log": ["b"]})
    builder.add_node("c", lambda state: {"log": ["c"]})
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_edge(["a", "b"], "c")
    builder.add_edge("c", END)
    return builder.compile(tracer=tracer)


def test_unreachable_endpoint_does_not_block_graph() -> None:
    exporter = OtlpExporter(endpoint="127.0.0.1:1", insecure=True, timeout=0.05)
    assert _graph(exporter).invoke({"x": 0}) == {"x": 2}
    assert exporter.export_errors > 0
    assert exporter.last_error is not None


def test_user_exporter_exception_is_isolated_and_not_retried() -> None:
    fake = _RaisingExporter(RuntimeError("boom"))
    exporter = OtlpExporter(exporter=fake)
    assert _graph(exporter).invoke({"x": 0}) == {"x": 2}
    assert fake.calls == 2
    assert exporter.export_errors == 2
    assert isinstance(exporter.last_error, RuntimeError)


def test_failure_result_is_recorded_as_synthetic_runtime_error() -> None:
    fake = _FailureExporter()
    exporter = OtlpExporter(exporter=fake)
    assert _graph(exporter).invoke({"x": 0}) == {"x": 2}
    assert fake.calls == 2
    assert exporter.export_errors == 2
    assert isinstance(exporter.last_error, RuntimeError)
    assert "FAILURE" in str(exporter.last_error)


def test_on_error_exception_is_isolated_and_original_error_preserved() -> None:
    seen: list[BaseException] = []

    def on_error(exc: BaseException) -> None:
        seen.append(exc)
        raise ValueError("callback boom")

    fake = _RaisingExporter(RuntimeError("original"))
    exporter = OtlpExporter(exporter=fake, on_error=on_error)
    assert _graph(exporter).invoke({"x": 0}) == {"x": 2}
    assert len(seen) == 2
    assert all(isinstance(item, RuntimeError) for item in seen)
    assert isinstance(exporter.last_error, RuntimeError)
    assert "original" in str(exporter.last_error)


def test_base_exception_is_not_swallowed() -> None:
    exporter = OtlpExporter(exporter=_RaisingExporter(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        _graph(exporter).invoke({"x": 0})


def test_success_does_not_clear_last_error() -> None:
    fake = _RaisingExporter(RuntimeError("first"))
    exporter = OtlpExporter(exporter=fake)
    graph = _graph(exporter)
    graph.invoke({"x": 0})
    first_error = exporter.last_error
    assert first_error is not None

    exporter._exporter = RecordingSpanExporter()  # type: ignore[attr-defined]
    graph.invoke({"x": 0})
    assert exporter.last_error is first_error


def test_mapping_skip_counts_as_failure() -> None:
    exporter = OtlpExporter(exporter=RecordingSpanExporter())
    exporter.on_span_end(make_span(id=""))
    assert exporter.export_errors == 1
    assert isinstance(exporter.last_error, ValueError)


def test_empty_or_incomplete_span_is_not_exported() -> None:
    recording = RecordingSpanExporter()
    exporter = OtlpExporter(exporter=recording)
    exporter.on_span_end(make_span(end_time=None))
    assert recording.calls == 0
    assert exporter.export_errors == 0


def test_concurrent_node_completions_do_not_corrupt_exporter() -> None:
    recording = RecordingSpanExporter()
    exporter = OtlpExporter(exporter=recording)
    result = _barrier_graph(exporter).invoke({"log": []})
    assert sorted(result["log"]) == ["a", "b", "c"]
    assert recording.calls == 3
    assert exporter.export_errors == 0
    assert exporter.last_error is None
