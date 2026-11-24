#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""Phoenix 最小对接示例（gRPC OTLP · 显式端点 · 本地明文）。"""

from __future__ import annotations

import argparse
from typing import TypedDict

from freegraph.graph import END, START, StateGraph
from freegraph.observability import OtlpExporter, invoke_model, invoke_tool


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


def _run(endpoint: str) -> int:
    exporter = OtlpExporter(endpoint=endpoint, insecure=True)

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
    parser = argparse.ArgumentParser(description="Phoenix OTLP gRPC example")
    parser.add_argument("--endpoint", required=True, help="gRPC endpoint, e.g. 127.0.0.1:4317")
    args = parser.parse_args(argv)
    return _run(args.endpoint)


if __name__ == "__main__":
    raise SystemExit(main())
