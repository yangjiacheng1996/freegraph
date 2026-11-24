# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B24F1 · 宪法原则 XI 最小差分组 B24F1-D-01…D-03。

只断言 COMPAT.md 所陈述的**既有差异**；上游缺席 ⇒ ``pytest.skip``。
"""

from __future__ import annotations

from typing import TypedDict

import pytest


class _State(TypedDict, total=False):
    x: int


def _compat_rows() -> dict[str, list[str]]:
    from pathlib import Path

    import sys

    facade = Path(__file__).resolve().parents[1] / "facade"
    if str(facade) not in sys.path:
        sys.path.insert(0, str(facade))
    import _gatesupport  # noqa: PLC0415

    text = (Path(__file__).resolve().parents[2] / "COMPAT.md").read_text(encoding="utf-8")
    return dict(_gatesupport.compat_matrix_rows(text))


def test_b24f1_d01_command_goto_default_is_diff() -> None:
    pytest.importorskip("langgraph")
    from freegraph.contracts import Command as FreeCommand
    from langgraph.types import Command as UpstreamCommand

    assert UpstreamCommand().goto == ()
    assert FreeCommand().goto is None
    assert "Y-01" in _compat_rows()["Command"][3]


def test_b24f1_d02_send_mutability_is_diff() -> None:
    pytest.importorskip("langgraph")
    from freegraph.contracts import Send as FreeSend
    from langgraph.types import Send as UpstreamSend

    upstream = UpstreamSend("node", 1)
    upstream.node = "other"
    assert upstream.node == "other"

    free = FreeSend("node", 1)
    with pytest.raises(AttributeError):
        free.node = "other"
    assert "Y-03" in _compat_rows()["Send"][3]


def test_b24f1_d03_get_state_without_snapshot_is_diff() -> None:
    pytest.importorskip("langgraph")
    from freegraph.graph import END as FEND
    from freegraph.graph import START as FSTART
    from freegraph.graph import StateGraph as FreeStateGraph
    from freegraph.persistence import MemorySaver as FreeMemorySaver
    from langgraph.checkpoint.memory import MemorySaver as UpstreamMemorySaver
    from langgraph.graph import END as UEND
    from langgraph.graph import START as USTART
    from langgraph.graph import StateGraph as UpstreamStateGraph

    def build(builder: type, start: str, end: str, saver: type):
        graph = builder(_State)
        graph.add_node("a", lambda state: {"x": 1})
        graph.add_edge(start, "a")
        graph.add_edge("a", end)
        return graph.compile(checkpointer=saver())

    config = {"configurable": {"thread_id": "missing"}}
    upstream = build(UpstreamStateGraph, USTART, UEND, UpstreamMemorySaver).get_state(config)
    free = build(FreeStateGraph, FSTART, FEND, FreeMemorySaver).get_state(config)
    assert upstream.values == {} and upstream.next == ()
    assert free is None
    assert "Y-02" in _compat_rows()["CompiledGraph"][3]
