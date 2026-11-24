#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""Langfuse 最小对接示例（OTLP/HTTP + Basic auth · 用户侧 HTTP exporter）。"""

from __future__ import annotations

import argparse
import base64
import sys
from typing import TypedDict

from freegraph.graph import END, START, StateGraph
from freegraph.observability import OtlpExporter, invoke_model, invoke_tool

_INSTALL_HINT = 'pip install "opentelemetry-exporter-otlp-proto-http>=1.20"'


class _State(TypedDict, total=False):
    x: int


class _FakeModel:
    def invoke(self, value: object) -> object:
        return value


class _FakeTool:
    name = "add"
    description = "add two numbers"

    def invoke(self, value: object) -> object:
        return value


def _load_http_exporter() -> object | None:
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
    except ImportError:
        print(f"Langfuse example requires the user-side HTTP exporter: {_INSTALL_HINT}", file=sys.stderr)
        return None
    return OTLPSpanExporter


def _auth_header(public_key: str, secret_key: str) -> dict[str, str]:
    token = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _run(endpoint: str, public_key: str, secret_key: str) -> int:
    http_exporter = _load_http_exporter()
    if http_exporter is None:
        return 2
    exporter = OtlpExporter(
        exporter=http_exporter(
            endpoint=endpoint,
            headers=_auth_header(public_key, secret_key),
        )
    )

    def node(state: _State) -> dict[str, int]:
        invoke_model(_FakeModel(), "hello")
        invoke_tool(_FakeTool(), "hello")
        return {"x": state.get("x", 0) + 1}

    def second(state: _State) -> dict[str, int]:
        return {"x": state.get("x", 0) + 1}

    builder = StateGraph(_State)
    builder.add_node("a", node)
    builder.add_node("b", second)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    result = builder.compile(tracer=exporter).invoke({"x": 0})
    print(f"exported spans to {endpoint}; result={result}; export_errors={exporter.export_errors}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Langfuse OTLP/HTTP example")
    parser.add_argument("--endpoint", required=True, help="OTLP/HTTP endpoint")
    parser.add_argument("--public-key", required=True)
    parser.add_argument("--secret-key", required=True)
    args = parser.parse_args(argv)
    return _run(args.endpoint, args.public_key, args.secret_key)


if __name__ == "__main__":
    raise SystemExit(main())
