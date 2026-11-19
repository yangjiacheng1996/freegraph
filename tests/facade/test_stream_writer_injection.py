# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B8F2 · 节点签名 ``writer`` 的关键字注入（T072 / FR-036）。"""

from __future__ import annotations

from typing import TypedDict

import pytest

from freegraph.contracts import StreamWriter
from freegraph.graph import END, START, StateGraph


class _State(TypedDict):
    x: int


def _run(node, *, mode: str = "custom"):
    builder = StateGraph(_State)
    builder.add_node("a", node)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    return builder.compile()


def test_unannotated_writer_is_injected() -> None:
    def node(state: _State, writer) -> dict[str, int]:
        writer({"msg": "plain"})
        return {"x": 1}

    assert [e["payload"] for e in _run(node).stream({}, stream_mode="custom")] == [
        {"msg": "plain"}
    ]


def test_stream_writer_annotation_is_injected() -> None:
    def node(state: _State, writer: StreamWriter) -> dict[str, int]:
        writer({"msg": "typed"})
        return {"x": 1}

    assert [e["payload"] for e in _run(node).stream({}, stream_mode="custom")] == [
        {"msg": "typed"}
    ]


def test_keyword_only_writer_is_injected() -> None:
    def node(state: _State, *, writer) -> dict[str, int]:
        writer({"msg": "kwonly"})
        return {"x": 1}

    assert [e["payload"] for e in _run(node).stream({}, stream_mode="custom")] == [
        {"msg": "kwonly"}
    ]


def test_upstream_runtime_key_name_is_not_injected() -> None:
    def node(state: _State, stream_writer) -> dict[str, int]:
        return {"x": 1}

    with pytest.raises(TypeError):
        _run(node).invoke({})


def test_kwargs_is_not_injected() -> None:
    def node(state: _State, **kwargs) -> dict[str, int]:
        return {"x": 1}

    assert _run(node).invoke({}) == {"x": 1}


def test_invoke_injects_a_noop_writer() -> None:
    def node(state: _State, writer) -> dict[str, int]:
        writer({"ignored": True})
        return {"x": 1}

    assert _run(node).invoke({}) == {"x": 1}
