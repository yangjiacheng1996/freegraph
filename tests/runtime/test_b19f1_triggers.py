# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · 触发源覆盖静态边 / goto / Send，且排序确定。"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from freegraph.graph import END, START, Command, Send, StateGraph

from .conftest import B19RecordingSink


class _State(TypedDict, total=False):
    log: Annotated[list, operator.add]


def _mixed() -> StateGraph:
    def a(state: _State) -> Command:
        return Command(update={"log": ["a"]}, goto="c")

    def fan(state: _State) -> list[Send]:
        return [Send("worker", {"log": ["w"]})]

    builder = StateGraph(_State)
    builder.add_node("a", a)
    builder.add_node("b", lambda state: {})
    builder.add_node("c", lambda state: {})
    builder.add_node("fan", fan)
    builder.add_node("worker", lambda state: {})
    builder.add_edge(START, "a")
    builder.add_edge(START, "fan")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    builder.add_edge("c", END)
    builder.add_edge("fan", "worker")
    builder.add_edge("worker", END)
    return builder


def test_all_three_trigger_kinds_appear_and_are_deterministic() -> None:
    first = B19RecordingSink()
    second = B19RecordingSink()
    _mixed().compile(tracer=first).invoke({"log": []})
    _mixed().compile(tracer=second).invoke({"log": []})

    by_node = {record.node: record for record in first.records}
    assert by_node["b"].triggers == (("e", "a"),)
    assert by_node["c"].triggers == (("e", "a"),)
    assert by_node["worker"].triggers == (("send", "fan", 0),)
    first_sorted = sorted((record.node, record.triggers) for record in first.records)
    second_sorted = sorted((record.node, record.triggers) for record in second.records)
    assert first_sorted == second_sorted
