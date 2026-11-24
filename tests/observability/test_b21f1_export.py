# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B21F1 · US1：导出器模式的基本注入 / 字段面 / 图结果不变。"""

from __future__ import annotations

from typing import Any, TypedDict

from freegraph.graph import END, START, StateGraph
from freegraph.observability import OtlpExporter, invoke_model, invoke_tool

from .conftest import RecordingSpanExporter, make_span


class _State(TypedDict, total=False):
    x: int


class _Model:
    def invoke(self, value: Any) -> Any:
        return value


class _Tool:
    name = "add"
    description = "add numbers"

    def invoke(self, value: Any) -> Any:
        return value


def _build_graph(*, tracer: Any = None) -> Any:
    def node(state: _State) -> dict[str, int]:
        invoke_model(_Model(), "hello")
        invoke_tool(_Tool(), "hello")
        return {"x": state.get("x", 0) + 1}

    builder = StateGraph(_State)
    builder.add_node("a", node)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    return builder.compile(tracer=tracer)


def test_exporter_mode_exports_node_model_and_tool_spans() -> None:
    recording = RecordingSpanExporter()
    exporter = OtlpExporter(exporter=recording)
    graph = _build_graph(tracer=exporter)
    assert graph.invoke({"x": 0}) == {"x": 1}
    assert recording.calls == 3
    names = [span.name for span in recording.spans]
    assert "a" in names
    assert any(name.startswith("chat") for name in names)
    assert any(name.startswith("execute_tool") for name in names)
    assert exporter.export_errors == 0
    assert exporter.last_error is None


def test_exported_fields_match_span_and_graph_result_is_unchanged() -> None:
    recording = RecordingSpanExporter()
    graph = _build_graph(tracer=OtlpExporter(exporter=recording))
    exported_result = graph.invoke({"x": 0})
    baseline_result = _build_graph().invoke({"x": 0})
    assert exported_result == baseline_result

    node_span = next(span for span in recording.spans if span.name == "a")
    assert node_span.attributes == {}
    assert node_span.resource.attributes["service.name"] == "freegraph"
    assert node_span.instrumentation_scope.name == "freegraph"
    for span in recording.spans:
        assert span.context.trace_id == node_span.context.trace_id
    model_span = next(span for span in recording.spans if span.name.startswith("chat"))
    tool_span = next(
        span for span in recording.spans if span.name.startswith("execute_tool")
    )
    assert model_span.parent is not None
    assert tool_span.parent is not None
    assert model_span.parent.span_id == node_span.context.span_id
    assert tool_span.parent.span_id == node_span.context.span_id


def test_on_span_start_and_none_end_time_are_noops() -> None:
    recording = RecordingSpanExporter()
    exporter = OtlpExporter(exporter=recording)
    exporter.on_span_start(make_span())
    exporter.on_span_end(make_span(end_time=None))
    assert recording.calls == 0


def test_current_span_is_always_none() -> None:
    exporter = OtlpExporter(exporter=RecordingSpanExporter())
    assert exporter.current_span() is None


def test_trace_record_is_not_exported() -> None:
    exporter = OtlpExporter(exporter=RecordingSpanExporter())
    assert not hasattr(exporter, "on_trace_record")
    assert not any(span.name == "trace_record" for span in exporter_spans(exporter))


def exporter_spans(exporter: OtlpExporter) -> list[Any]:
    """从导出器内部拿到测试 exporter 捕获的 span（仅测试使用）。"""
    return getattr(exporter, "_exporter").spans


def test_b20f2_query_is_not_called(monkeypatch: Any) -> None:
    from freegraph.observability import FileTraceStore

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("query() must not be called by the OTLP exporter")

    monkeypatch.setattr(FileTraceStore, "query", boom)
    graph = _build_graph(tracer=OtlpExporter(exporter=RecordingSpanExporter()))
    assert graph.invoke({"x": 0}) == {"x": 1}
