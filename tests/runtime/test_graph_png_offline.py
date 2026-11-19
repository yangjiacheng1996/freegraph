# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B23F1 · PNG 导出的流式隔离 / 并发 / 文件副作用。"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypedDict

from freegraph.contracts.graph import Graph
from freegraph.graph import END, START, StateGraph


class State(TypedDict, total=False):
    value: int


def _node(state: State) -> dict[str, int]:
    return {"value": state.get("value", 0) + 1}


def _build():
    builder = StateGraph(State)
    builder.add_node("a", _node)
    builder.add_node("b", _node)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder.compile()


def test_stream_does_not_call_draw_mermaid_png(monkeypatch) -> None:
    calls = {"n": 0}

    def forbidden(self: Graph) -> bytes:
        calls["n"] += 1
        raise AssertionError("stream() 不应调用 PNG 导出")

    monkeypatch.setattr(Graph, "draw_mermaid_png", forbidden)
    events = list(_build().stream({}, stream_mode="updates"))
    assert events
    assert calls["n"] == 0


def test_png_is_stable_before_and_after_stream() -> None:
    compiled = _build()
    before = compiled.get_graph().draw_mermaid_png()
    list(compiled.stream({}, stream_mode="updates"))
    after = compiled.get_graph().draw_mermaid_png()
    assert before == after


def test_png_calls_during_stream_are_safe() -> None:
    compiled = _build()
    graph = compiled.get_graph()
    errors: list[BaseException] = []

    def consume_stream() -> None:
        try:
            list(compiled.stream({}, stream_mode="updates"))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    thread = threading.Thread(target=consume_stream)
    thread.start()
    try:
        results = [graph.draw_mermaid_png() for _ in range(8)]
    finally:
        thread.join()
    assert not errors
    assert results and all(data == results[0] for data in results)


def test_concurrent_png_calls_are_deterministic() -> None:
    graph = _build().get_graph()
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: graph.draw_mermaid_png(), range(8)))
    assert results and all(data == results[0] for data in results)


def test_png_call_creates_no_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    graph = Graph()
    assert graph.draw_mermaid_png()
    assert list(tmp_path.iterdir()) == []


def test_offline_exclusions_have_no_b23f1_entries() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    text = (repo_root / "tests" / "gates" / "data" / "offline_exclusions.txt").read_text(
        encoding="utf-8"
    )
    lowered = text.lower()
    assert "b23f1" not in lowered
    assert "test_graph_png" not in lowered
