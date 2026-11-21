# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · 并发组 / 屏障组 / 跨任务父子隔离。"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from freegraph.graph import END, START, Send, StateGraph

from .conftest import B19RecordingSink


class _State(TypedDict, total=False):
    log: Annotated[list, operator.add]


def _barrier_graph() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"log": ["a"]})
    builder.add_node("b", lambda state: {"log": ["b"]})
    builder.add_node("c", lambda state: {"log": ["c"]})
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_edge(["a", "b"], "c")
    builder.add_edge("c", END)
    return builder


def _fanout_graph() -> StateGraph:
    def fan(state: _State) -> list[Send]:
        return [Send("worker", {"log": ["w1"]}), Send("worker", {"log": ["w2"]})]

    builder = StateGraph(_State)
    builder.add_node("fan", fan)
    builder.add_node("worker", lambda state: {})
    builder.add_edge(START, "fan")
    builder.add_edge("fan", "worker")
    builder.add_edge("worker", END)
    return builder


def test_barrier_group_is_reported() -> None:
    sink = B19RecordingSink()
    _barrier_graph().compile(tracer=sink).invoke({"log": []})
    c_record = next(record for record in sink.records if record.node == "c")
    assert c_record.barrier_groups == (("a", "b"),)
    assert c_record.concurrency_group == ("c",)


def test_fanout_tasks_share_concurrency_group_and_have_no_cross_task_parent() -> None:
    sink = B19RecordingSink()
    _fanout_graph().compile(tracer=sink).invoke({"log": []})
    workers = [record for record in sink.records if record.node == "worker"]
    assert len(workers) == 2
    assert workers[0].concurrency_group == workers[1].concurrency_group == (
        "worker:0",
        "worker:1",
    )
    assert all(span.parent is None for span in sink.started)
    assert {record.task_id for record in workers} == {"worker:0", "worker:1"}
