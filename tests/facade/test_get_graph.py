# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B22F1 · 门面 ``get_graph`` 行为（C13 / C26）。"""

from __future__ import annotations

from typing import Any

from freegraph.contracts.graph import Graph

from ._builder_support import State, node_a
from ._compiled_support import build_minimal_graph


def _nodes_and_edges(graph: Graph) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    return graph.nodes, graph.edges


def test_get_graph_returns_own_graph_type() -> None:
    compiled = build_minimal_graph().compile()
    graph = compiled.get_graph()
    assert type(graph).__module__ == "freegraph.contracts.graph"
    assert type(graph).__name__ == "Graph"


def test_xray_true_and_false_are_identical_in_v1() -> None:
    compiled = build_minimal_graph(conditional=True).compile()
    assert _nodes_and_edges(compiled.get_graph(xray=True)) == _nodes_and_edges(
        compiled.get_graph(xray=False)
    )


def test_xray_accepts_non_bool_truthy_and_falsy() -> None:
    compiled = build_minimal_graph().compile()
    expected = _nodes_and_edges(compiled.get_graph(xray=False))
    assert _nodes_and_edges(compiled.get_graph(xray=1)) == expected
    assert _nodes_and_edges(compiled.get_graph(xray=0)) == expected


def test_graph_is_stable_before_and_after_runs() -> None:
    compiled = build_minimal_graph().compile()
    before = compiled.get_graph()
    compiled.invoke({})
    after = compiled.get_graph()
    assert _nodes_and_edges(before) == _nodes_and_edges(after)


def test_graph_is_stable_before_and_after_stream() -> None:
    compiled = build_minimal_graph().compile()
    before = compiled.get_graph()
    list(compiled.stream({}, stream_mode="updates"))
    after = compiled.get_graph()
    assert _nodes_and_edges(before) == _nodes_and_edges(after)


def test_get_graph_does_not_execute_nodes() -> None:
    calls = {"n": 0}

    def counted(state: dict[str, Any]) -> dict[str, Any]:
        calls["n"] += 1
        return {}

    from freegraph.graph import START, StateGraph

    builder = StateGraph(State)
    builder.add_node("a", counted)
    builder.add_edge(START, "a")
    compiled = builder.compile()
    compiled.get_graph()
    assert calls["n"] == 0


def test_get_graph_is_repeatable_and_equal() -> None:
    compiled = build_minimal_graph().compile()
    first = compiled.get_graph()
    second = compiled.get_graph()
    assert first == second
    assert first is not second
