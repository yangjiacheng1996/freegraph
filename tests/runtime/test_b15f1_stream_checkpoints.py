# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · ``stream(stream_mode="checkpoints")`` 消费端。"""

from __future__ import annotations

import operator
import sqlite3
from typing import Annotated, TypedDict

from freegraph.contracts import RunConfig, StateSnapshot
from freegraph.graph import END, START, StateGraph
from freegraph.persistence import SqliteSaver


class _State(TypedDict):
    log: Annotated[list, operator.add]


def _a(state: dict) -> dict:
    return {"log": ["a"]}


def _b(state: dict) -> dict:
    return {"log": ["b"]}


def _graph() -> StateGraph:
    graph = StateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("b", _b)
    graph.add_edge(START, "a")
    graph.add_edge("a", "b")
    graph.add_edge("b", END)
    return graph


def _saver() -> SqliteSaver:
    return SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))


def test_checkpoints_events_match_put_count_and_shape() -> None:
    saver = _saver()
    compiled = _graph().compile(checkpointer=saver)
    events = list(
        compiled.stream({"log": []}, {"thread_id": "t"}, stream_mode="checkpoints")
    )
    assert events
    for event in events:
        assert set(event) == {"stream_mode", "payload", "run_id", "thread_id"}
        assert event["stream_mode"] == "checkpoints"
        assert isinstance(event["payload"], StateSnapshot)
    ids = [event["payload"].config.configurable["checkpoint_id"] for event in events]
    assert len(ids) == len(set(ids))
    # count == number of successful put in this run == saver history length (fresh thread)
    assert len(events) == len(list(saver.list(RunConfig(thread_id="t"))))
    # initial snapshot event precedes the first completed round
    assert events[0]["payload"].next == ("a",)


def test_checkpoints_zero_without_saver_or_thread() -> None:
    compiled = _graph().compile()
    assert list(compiled.stream({"log": []}, {"thread_id": "t"}, stream_mode="checkpoints")) == []
    saver = _saver()
    compiled2 = _graph().compile(checkpointer=saver)
    assert list(compiled2.stream({"log": []}, {}, stream_mode="checkpoints")) == []


def test_checkpoints_only_new_snapshots_when_history_exists() -> None:
    saver = _saver()
    compiled = _graph().compile(checkpointer=saver)
    first = list(compiled.stream({"log": []}, {"thread_id": "t"}, stream_mode="checkpoints"))
    before = len(list(saver.list(RunConfig(thread_id="t"))))
    second = list(compiled.stream({"log": []}, {"thread_id": "t"}, stream_mode="checkpoints"))
    after = len(list(saver.list(RunConfig(thread_id="t"))))
    assert len(second) == after - before
    # no history snapshots are replayed into the new run
    first_ids = {event["payload"].config.configurable["checkpoint_id"] for event in first}
    second_ids = {event["payload"].config.configurable["checkpoint_id"] for event in second}
    assert first_ids.isdisjoint(second_ids)


def test_other_modes_unchanged_by_checkpoints_mode() -> None:
    saver = _saver()
    compiled = _graph().compile(checkpointer=saver)
    updates = list(compiled.stream({"log": []}, {"thread_id": "t"}, stream_mode="updates"))
    assert updates
    assert all(event["stream_mode"] == "updates" for event in updates)
