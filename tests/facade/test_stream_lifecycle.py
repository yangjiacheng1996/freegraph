# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B8F2 · 流式生命周期 / 递归上限 / 失败 / 中断（T049 / T073）。"""

from __future__ import annotations

import threading
from typing import TypedDict

import pytest

from freegraph.contracts import Command, GraphRecursionError
from freegraph.graph import END, START, StateGraph, get_stream_writer, interrupt


class _State(TypedDict):
    x: int


def _linear(node):
    builder = StateGraph(_State)
    builder.add_node("a", node)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    return builder.compile()


def test_stream_is_lazy() -> None:
    calls = []

    def a(state: _State) -> dict:
        calls.append(1)
        return {"x": 1}

    compiled = _linear(a)
    iterator = compiled.stream({}, stream_mode="values")
    assert calls == []
    next(iterator)
    assert calls == []
    iterator.close()


def test_stream_none_means_no_input_writes() -> None:
    compiled = _linear(lambda state: {"x": 1})
    events = list(compiled.stream(None, stream_mode="values"))
    assert events


def test_command_input_raises_on_first_iteration_not_at_call_time() -> None:
    compiled = _linear(lambda state: {"x": 1})
    iterator = compiled.stream(Command(resume=1), stream_mode="values")
    with pytest.raises(TypeError):
        next(iterator)


def test_invalid_config_raises_on_first_iteration() -> None:
    compiled = _linear(lambda state: {"x": 1})
    iterator = compiled.stream({}, config=123, stream_mode="values")
    with pytest.raises(TypeError):
        next(iterator)


def test_static_interrupt_points_are_rejected_on_first_iteration() -> None:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    compiled = builder.compile(interrupt_before=["a"])
    iterator = compiled.stream({}, stream_mode="values")
    with pytest.raises(ValueError):
        next(iterator)


def test_early_close_leaves_no_threads() -> None:
    compiled = _linear(lambda state: {"x": 1})
    iterator = compiled.stream({}, stream_mode="values")
    next(iterator)
    iterator.close()
    assert not [
        thread
        for thread in threading.enumerate()
        if thread.name.startswith("freegraph-node")
    ]


def test_failing_round_flushes_custom_then_re_raises_original() -> None:
    def a(state: _State) -> dict:
        get_stream_writer()({"m": "before"})
        raise RuntimeError("boom")

    compiled = _linear(a)
    seen = []
    with pytest.raises(RuntimeError) as excinfo:
        for event in compiled.stream({}, stream_mode="custom"):
            seen.append(event["payload"])
    assert seen == [{"m": "before"}]
    assert str(excinfo.value) == "boom"


def test_interrupt_closes_normally_with_closing_events() -> None:
    def a(state: _State) -> dict:
        interrupt("approve?")
        return {"x": 1}

    compiled = _linear(a)
    values = list(compiled.stream({}, stream_mode="values"))
    assert "__interrupt__" in values[-1]["payload"]
    updates = list(compiled.stream({}, stream_mode="updates"))
    assert "__interrupt__" in updates[-1]["payload"]
    tasks = list(compiled.stream({}, stream_mode="tasks"))
    assert tasks and tasks[0]["payload"].interrupts
    debug = list(compiled.stream({}, stream_mode="debug"))
    assert debug and debug[0]["payload"]["step"] == 1


def test_recursion_limit_is_checked_before_the_over_limit_round() -> None:
    calls = []

    def a(state: _State) -> dict:
        calls.append(1)
        return {"x": state.get("x", 0) + 1}

    builder = StateGraph(_State)
    builder.add_node("a", a)
    builder.add_edge(START, "a")
    builder.add_edge("a", "a")
    compiled = builder.compile()
    with pytest.raises(GraphRecursionError) as excinfo:
        list(compiled.stream({}, config={"recursion_limit": 3}, stream_mode="values"))
    assert excinfo.value.recursion_limit == 3
    assert excinfo.value.current_step == 3
    assert len(calls) == 3


def test_exactly_converged_at_the_limit_does_not_raise() -> None:
    def a(state: _State) -> dict:
        return {"x": 1}

    def b(state: _State) -> dict:
        return {"x": 2}

    def c(state: _State) -> dict:
        return {"x": 3}

    builder = StateGraph(_State)
    builder.add_node("a", a)
    builder.add_node("b", b)
    builder.add_node("c", c)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", "c")
    builder.add_edge("c", END)
    compiled = builder.compile()
    events = list(compiled.stream({}, config={"recursion_limit": 3}, stream_mode="values"))
    assert events[-1]["payload"]["x"] == 3


def test_max_concurrency_is_read_from_mapping_config() -> None:
    active = []
    peak = [0]
    lock = threading.Lock()

    def make_node(name: str):
        def node(state: _State) -> dict:
            with lock:
                active.append(name)
                peak[0] = max(peak[0], len(active))
            try:
                return {}
            finally:
                with lock:
                    active.remove(name)

        return node

    builder = StateGraph(_State)
    builder.add_node("a", make_node("a"))
    builder.add_node("b", make_node("b"))
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_edge("a", END)
    builder.add_edge("b", END)
    compiled = builder.compile()
    list(
        compiled.stream(
            {}, config={"max_concurrency": 1}, stream_mode="updates"
        )
    )
    assert peak[0] == 1
