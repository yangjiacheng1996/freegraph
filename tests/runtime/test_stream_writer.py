# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B8F2 · ``StreamWriter`` / custom 顺序的运行时判据（T015）。"""

from __future__ import annotations

from typing import Annotated, TypedDict

from freegraph.graph import END, START, StateGraph, get_stream_writer


class _Append:
    @staticmethod
    def apply(left: list[str], right: list[str]) -> list[str]:
        return [*left, *right]


class _State(TypedDict):
    log: Annotated[list[str], _Append.apply]


def test_get_stream_writer_outside_a_stream_is_noop() -> None:
    writer = get_stream_writer()
    assert callable(writer)
    writer({"ignored": True})  # MUST NOT raise


def test_custom_writes_from_concurrent_tasks_are_deterministically_ordered() -> None:
    def a(state: _State) -> dict:
        writer = get_stream_writer()
        writer("a0")
        writer("a1")
        return {"log": ["a"]}

    def b(state: _State) -> dict:
        get_stream_writer()("b0")
        return {"log": ["b"]}

    builder = StateGraph(_State)
    builder.add_node("a", a)
    builder.add_node("b", b)
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_edge("a", END)
    builder.add_edge("b", END)
    compiled = builder.compile()
    payloads = [event["payload"] for event in compiled.stream({}, stream_mode="custom")]
    assert payloads == ["a0", "a1", "b0"]


def test_writer_getter_and_keyword_injection_share_the_same_carrier() -> None:
    def a(state: _State, writer) -> dict:
        writer("injected")
        get_stream_writer()("getter")
        return {"log": ["a"]}

    builder = StateGraph(_State)
    builder.add_node("a", a)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    compiled = builder.compile()
    payloads = [event["payload"] for event in compiled.stream({}, stream_mode="custom")]
    assert payloads == ["injected", "getter"]
    assert compiled.invoke({}) == {"log": ["a"]}
