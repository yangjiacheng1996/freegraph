# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B14F1 · 初始 / 每轮快照、8 字段、context 不持久化、无 saver 路径。"""

from __future__ import annotations

import json
from typing import Any, TypedDict

from freegraph.contracts import RunConfig
from freegraph.graph import END, START, StateGraph
from freegraph.persistence import MemorySaver
from freegraph.runtime import (
    GraphSpec,
    LastValue,
    NodeSpec,
    SchedulerState,
    run_graph,
)


class _State(TypedDict, total=False):
    x: int


def _linear() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def _single() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    return builder


def _snapshots(saver: MemorySaver, config: RunConfig):
    return list(saver.list(config))


def test_single_and_two_node_snapshot_counts() -> None:
    single_saver = MemorySaver()
    single_cfg = RunConfig(thread_id="single")
    _single().compile(checkpointer=single_saver).invoke({"x": 0}, single_cfg)
    assert len(_snapshots(single_saver, single_cfg)) == 2
    assert _snapshots(single_saver, single_cfg)[0].snapshot.next == ()

    saver = MemorySaver()
    cfg = RunConfig(thread_id="linear")
    _linear().compile(checkpointer=saver).invoke({"x": 0}, cfg)
    snapshots = _snapshots(saver, cfg)
    assert len(snapshots) == 3
    assert [item.snapshot.next for item in snapshots] == [(), ("b",), ("a",)]
    assert [item.snapshot.values for item in snapshots] == [
        {"x": 2},
        {"x": 1},
        {"x": 0},
    ]


def test_snapshot_eight_fields_parent_chain_and_tasks() -> None:
    saver = MemorySaver()
    cfg = RunConfig(thread_id="fields")
    _linear().compile(checkpointer=saver).invoke({"x": 0}, cfg)
    snapshots = _snapshots(saver, cfg)
    latest = snapshots[0].snapshot
    initial = snapshots[-1].snapshot

    assert not hasattr(latest, "__dict__")
    for name in (
        "values",
        "next",
        "config",
        "metadata",
        "created_at",
        "parent_config",
        "tasks",
        "interrupts",
    ):
        assert hasattr(latest, name), name
    assert isinstance(latest.created_at, str)
    assert isinstance(latest.next, tuple)
    assert isinstance(latest.tasks, tuple)
    assert isinstance(latest.interrupts, tuple)
    assert initial.parent_config is None
    assert latest.parent_config is not None
    assert snapshots[1].snapshot.parent_config == initial.config
    assert latest.tasks and latest.tasks[0].name == "b"
    assert initial.tasks == ()
    assert latest.interrupts == ()


def test_context_is_not_persisted() -> None:
    seen: list[Any] = []

    def node(state: _State) -> _State:
        seen.append(state.context)
        return {"x": 1}

    builder = StateGraph(_State)
    builder.add_node("a", node)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    saver = MemorySaver()
    cfg = RunConfig(thread_id="ctx", context={"user": "a"})
    builder.compile(checkpointer=saver).invoke({"x": 0}, cfg)

    assert seen == [{"user": "a"}]
    stored = saver.get_tuple(cfg)
    assert stored is not None
    assert stored.snapshot.config.context is None
    dump = json.dumps(
        {
            "metadata": stored.snapshot.metadata,
            "scheduler": stored.scheduler,
            "pending": stored.pending_writes,
        },
        default=str,
    )
    assert "context" not in dump


def test_scheduler_ledger_matches_runtime_state() -> None:
    spec = GraphSpec(
        channels={"x": LastValue("x", int)},
        nodes={
            "a": NodeSpec(("x",), lambda state: {"x": 1}),
            "b": NodeSpec(("x",), lambda state: {"x": 2}),
        },
        edges={"__start__": ("a",), "a": ("b",)},
    )
    state = SchedulerState()
    saver = MemorySaver()
    cfg = RunConfig(thread_id="ledger")
    run_graph(spec, {"x": 0}, state=state, checkpointer=saver, config=cfg)
    stored = saver.get_tuple(cfg)
    assert stored is not None
    assert stored.scheduler["channel_versions"] == state.channel_versions
    assert stored.scheduler["node_versions"] == state.node_versions


def test_no_checkpointer_and_no_thread_id_keep_execution_result_identical() -> None:
    base = _linear().compile().invoke({"x": 0})
    assert base == {"x": 2}

    no_thread = MemorySaver()
    with_thread = MemorySaver()
    cfg = RunConfig(thread_id="present")
    assert _linear().compile(checkpointer=no_thread).invoke({"x": 0}) == base
    assert _linear().compile(checkpointer=with_thread).invoke({"x": 0}, cfg) == base
    assert list(no_thread.list(None)) == []
    assert len(list(with_thread.list(cfg))) == 3


def test_checkpointer_true_and_false_are_accepted_and_do_not_persist() -> None:
    for value in (True, False):
        saver = MemorySaver()
        out = _linear().compile(checkpointer=value).invoke(
            {"x": 0}, RunConfig(thread_id="bool")
        )
        assert out == {"x": 2}
        assert list(saver.list(None)) == []
