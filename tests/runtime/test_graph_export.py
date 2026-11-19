# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B22F1 · 图结构导出（C13）：节点 / 边 / 可达性 / join / metadata。"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

import pytest

from freegraph.graph import END, START, Command, StateGraph


class State(TypedDict, total=False):
    count: int


def a(state: dict[str, Any]) -> dict[str, Any]:
    return {}


def b(state: dict[str, Any]) -> dict[str, Any]:
    return {}


def c(state: dict[str, Any]) -> dict[str, Any]:
    return {}


def literal_a(state: dict[str, Any]) -> Command[Literal["b", "c"]]:
    return Command(goto="b")


def _edges(graph: Any) -> set[tuple[str, str, bool, str | None]]:
    return {(e.source, e.target, e.conditional, e.condition) for e in graph.edges}


def test_nodes_include_start_business_and_end() -> None:
    builder = StateGraph(State)
    builder.add_node("a", a)
    builder.add_node("b", b)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    graph = builder.compile().get_graph()
    assert [n.id for n in graph.nodes] == ["__start__", "a", "b", "__end__"]
    assert {n.id for n in graph.nodes if n.id in {"__start__", "__end__"}} == {
        "__start__",
        "__end__",
    }
    assert all(n.id == n.name for n in graph.nodes)


def test_conditional_edges_are_per_target_and_labelled() -> None:
    builder = StateGraph(State)
    builder.add_node("a", a)
    builder.add_node("b", b)
    builder.add_edge(START, "a")
    builder.add_conditional_edges("a", lambda s: "b", ["b", END])
    graph = builder.compile().get_graph()
    assert ("__start__", "a", False, None) in _edges(graph)
    assert ("a", "b", True, "condition") in _edges(graph)
    assert ("a", "__end__", True, "condition") in _edges(graph)
    assert ("b", "__end__", False, None) in _edges(graph)


def test_literal_and_destinations_produce_multiple_edges() -> None:
    builder = StateGraph(State)
    builder.add_node("a", literal_a)
    builder.add_node("b", b)
    builder.add_node("c", c)
    builder.add_edge(START, "a")
    builder.add_edge("b", "a")
    builder.add_edge("c", "a")
    graph = builder.compile().get_graph()
    declared = {(e.source, e.target, e.condition) for e in graph.edges if e.source == "a"}
    assert declared == {("a", "b", None), ("a", "c", None)}


def test_destinations_override_inference_and_labels() -> None:
    builder = StateGraph(State)
    builder.add_node("a", literal_a, destinations={"c": "only-c"})
    builder.add_node("b", b)
    builder.add_node("c", c)
    builder.add_edge(START, "a")
    builder.add_edge("b", "a")
    builder.add_edge("c", "a")
    graph = builder.compile().get_graph()
    declared = {(e.source, e.target, e.condition) for e in graph.edges if e.source == "a"}
    assert declared == {("a", "c", "only-c")}


def test_unreachable_node_has_no_outgoing_edges() -> None:
    builder = StateGraph(State)
    builder.add_node("a", a)
    builder.add_node("d", b, destinations={"a": "x"})
    builder.add_edge(START, "a")
    graph = builder.compile().get_graph()
    assert "d" in {n.id for n in graph.nodes}
    assert not any(e.source == "d" for e in graph.edges)


def test_join_edges_are_one_per_source_and_satisfiable_only() -> None:
    builder = StateGraph(State)
    builder.add_node("a", a)
    builder.add_node("b", b)
    builder.add_node("c", c)
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_edge(["a", "b"], "c")
    builder.add_edge("c", END)
    graph = builder.compile().get_graph()
    assert ("a", "c", False, None) in _edges(graph)
    assert ("b", "c", False, None) in _edges(graph)


def test_unsatisfied_join_does_not_emit_and_reachable_source_gets_end() -> None:
    builder = StateGraph(State)
    builder.add_node("a", a)
    builder.add_node("b", b)
    builder.add_node("c", c)
    builder.add_edge(START, "a")
    builder.add_edge(["a", "b"], "c")
    builder.add_edge("c", END)
    graph = builder.compile().get_graph()
    assert not any(e.target == "c" for e in graph.edges)
    assert ("a", "__end__", False, None) in _edges(graph)


def test_dedupe_conditional_wins_over_static() -> None:
    builder = StateGraph(State)
    builder.add_node("a", a, destinations={"b": "x"})
    builder.add_node("b", b)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    graph = builder.compile().get_graph()
    pairs = [(e.source, e.target, e.conditional) for e in graph.edges]
    assert pairs.count(("a", "b", True)) == 1
    assert ("a", "b", False) not in pairs


def test_node_metadata_defer_and_interrupt_markers() -> None:
    builder = StateGraph(State)
    builder.add_node("a", a, metadata={"k": "v"}, defer=True)
    builder.add_node("b", b)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    graph = builder.compile(interrupt_before=["a"], interrupt_after=["b"]).get_graph()
    by_id = {n.id: n for n in graph.nodes}
    assert by_id["a"].metadata == {
        "k": "v",
        "defer": True,
        "__interrupt": "before",
    }
    assert by_id["b"].metadata == {"__interrupt": "after"}


def test_export_does_not_mutate_snapshots_or_run_nodes() -> None:
    calls = {"a": 0}

    def counted(state: dict[str, Any]) -> dict[str, Any]:
        calls["a"] += 1
        return {}

    builder = StateGraph(State)
    builder.add_node("a", counted)
    builder.add_edge(START, "a")
    compiled = builder.compile()
    before_edges = dict(compiled._spec.edges)  # type: ignore[attr-defined]
    graph1 = compiled.get_graph()
    graph2 = compiled.get_graph(xray=True)
    assert graph1 == graph2
    assert dict(compiled._spec.edges) == before_edges  # type: ignore[attr-defined]
    assert calls["a"] == 0
