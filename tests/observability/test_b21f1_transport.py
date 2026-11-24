# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B21F1 · US1：最小 gRPC 接收端验证真实 OTLP wire（Linux 全量）。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypedDict

import grpc
import pytest
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2, trace_service_pb2_grpc

from freegraph.graph import END, START, StateGraph
from freegraph.observability import OtlpExporter, invoke_model, invoke_tool


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


class _Servicer(trace_service_pb2_grpc.TraceServiceServicer):
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def Export(self, request: Any, context: Any) -> Any:  # noqa: N802 - gRPC API
        self.requests.append(request)
        return trace_service_pb2.ExportTraceServiceResponse()


def _all_spans(requests: list[Any]) -> list[Any]:
    spans: list[Any] = []
    for request in requests:
        for resource_spans in request.resource_spans:
            for scope_spans in resource_spans.scope_spans:
                spans.extend(scope_spans.spans)
    return spans


def _graph(tracer: Any) -> Any:
    def node(state: _State) -> dict[str, int]:
        invoke_model(_Model(), "hello")
        invoke_tool(_Tool(), "hello")
        return {"x": state.get("x", 0) + 1}

    builder = StateGraph(_State)
    builder.add_node("a", node)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    return builder.compile(tracer=tracer)


@pytest.mark.linux_only
@pytest.mark.full_install
def test_minimal_grpc_receiver_parses_all_complete_spans() -> None:
    servicer = _Servicer()
    server = grpc.server(ThreadPoolExecutor(max_workers=4))
    trace_service_pb2_grpc.add_TraceServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    try:
        exporter = OtlpExporter(endpoint=f"127.0.0.1:{port}", insecure=True)
        graph = _graph(exporter)
        assert graph.invoke({"x": 0}) == {"x": 1}
    finally:
        server.stop(0).wait()

    assert len(servicer.requests) == 3
    spans = _all_spans(servicer.requests)
    assert len(spans) == 3
    names = {span.name for span in spans}
    assert "a" in names
    assert any(name.startswith("chat") for name in names)
    assert any(name.startswith("execute_tool") for name in names)

    node = next(span for span in spans if span.name == "a")
    assert node.parent_span_id == b""
    assert node.trace_id
    for span in spans:
        assert span.trace_id == node.trace_id
        assert span.start_time_unix_nano > 0
        assert span.end_time_unix_nano >= span.start_time_unix_nano
    model = next(span for span in spans if span.name.startswith("chat"))
    assert model.parent_span_id == node.span_id
    assert any(
        attribute.key == "gen_ai.operation.name"
        and attribute.value.string_value == "chat"
        for attribute in model.attributes
    )
