#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B22F1 一键验收：A1–A4（``draw_mermaid`` 离线 / 零出站 / xray / 自有 Graph）。"""

from __future__ import annotations

import importlib.metadata
import socket
import sys
from typing import Any, TypedDict

from freegraph.graph import END, START, Command, StateGraph

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ENV = 2


class State(TypedDict, total=False):
    count: int


def _node(state: dict[str, Any]) -> dict[str, Any]:
    return {}


def _literal(state: dict[str, Any]) -> Command:
    return Command(goto="b")


def _build() -> Any:
    builder = StateGraph(State)
    builder.add_node("a", _literal)
    builder.add_node("b", _node, destinations={"a": "back"})
    builder.add_edge(START, "a")
    builder.add_edge("b", END)
    return builder.compile()


class _SocketGuard:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *_args: object, **_kwargs: object) -> object:
        self.calls += 1
        raise AssertionError("框架尝试出站")


def main() -> int:
    try:
        compiled = _build()
        graph = compiled.get_graph()
    except Exception as exc:  # noqa: BLE001
        print(f"B22F1 acceptance: FAIL ({type(exc).__name__}: {exc})")
        return EXIT_ENV

    guard = _SocketGuard()
    original = socket.socket
    socket.socket = guard  # type: ignore[assignment]
    try:
        text = graph.draw_mermaid()
    except Exception as exc:  # noqa: BLE001
        print(f"B22F1 acceptance: FAIL (draw_mermaid: {type(exc).__name__}: {exc})")
        return EXIT_FAIL
    finally:
        socket.socket = original  # type: ignore[assignment]

    failures: list[str] = []
    if not (isinstance(text, str) and text.strip() and "graph TD;" in text):
        failures.append("A1 draw_mermaid 未返回合法非空文本")
    if guard.calls != 0:
        failures.append(f"A2 框架出站 != 0（{guard.calls}）")
    g1 = compiled.get_graph(xray=True)
    g0 = compiled.get_graph(xray=False)
    if (g1.nodes, g1.edges) != (g0.nodes, g0.edges):
        failures.append("A3 xray=True 与 xray=False 不一致")
    if type(graph).__module__ != "freegraph.contracts.graph" or type(graph).__name__ != "Graph":
        failures.append("A4 返回类型不是 freegraph.contracts.graph.Graph")
    try:
        requires = importlib.metadata.requires("freegraph") or []
    except importlib.metadata.PackageNotFoundError:
        requires = []
    forbidden = ("langchain", "langsmith", "langgraph")
    if any(any(name in requirement for name in forbidden) for requirement in requires):
        failures.append("A4 依赖闭包含 langchain/langsmith/langgraph")

    if failures:
        print("B22F1 acceptance: FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return EXIT_FAIL
    print("B22F1 acceptance: PASS")
    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
