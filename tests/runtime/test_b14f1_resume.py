# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B14F1 · 真实 ``MemorySaver`` 的动态 / 静态恢复与快照计数。"""

from __future__ import annotations

from typing import Any, TypedDict

import pytest

from freegraph.contracts import Command, RunConfig
from freegraph.graph import END, START, StateGraph, interrupt
from freegraph.persistence import MemorySaver
from freegraph.runtime.errors import InterruptError


class _State(TypedDict, total=False):
    x: Any


def _interrupting() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("ask", lambda state: {"x": interrupt("approve?")})
    builder.add_edge(START, "ask")
    builder.add_edge("ask", END)
    return builder


def _snapshots(saver: MemorySaver, cfg: RunConfig):
    return list(saver.list(cfg))


def test_dynamic_interrupt_resume_count_and_single_node_rerun() -> None:
    saver = MemorySaver()
    cfg = RunConfig(thread_id="dynamic")
    app = _interrupting().compile(checkpointer=saver)
    first = app.invoke({"x": 0}, cfg)
    assert "__interrupt__" in first
    assert len(_snapshots(saver, cfg)) == 2
    suspended = _snapshots(saver, cfg)[0].snapshot
    assert suspended.next == ("ask",)
    assert suspended.tasks == ()
    assert suspended.interrupts
    assert any(
        channel == "__interrupt__"
        for _task, channel, _value in _snapshots(saver, cfg)[0].pending_writes
    )

    second = app.invoke(Command(resume="yes"), cfg)
    assert second["x"] == "yes"
    assert len(_snapshots(saver, cfg)) == 3
    assert _snapshots(saver, cfg)[0].snapshot.next == ()


def test_resume_context_comes_from_current_run_config_not_snapshot() -> None:
    seen: list[Any] = []
    builder = StateGraph(_State)

    def ask(state: _State) -> _State:
        seen.append(state.context)
        return {"x": interrupt("approve?")}

    builder.add_node("ask", ask)
    builder.add_edge(START, "ask")
    builder.add_edge("ask", END)
    saver = MemorySaver()
    app = builder.compile(checkpointer=saver)
    cfg1 = RunConfig(thread_id="ctx-resume", context={"user": "first"})
    cfg2 = RunConfig(thread_id="ctx-resume", context={"user": "second"})
    app.invoke({"x": 0}, cfg1)
    app.invoke(Command(resume="yes"), cfg2)
    assert seen == [{"user": "first"}, {"user": "second"}]
    stored = saver.get_tuple(cfg1)
    assert stored is not None
    assert stored.snapshot.config.context is None


def test_resume_without_checkpointer_raises_checkpointer_required() -> None:
    app = _interrupting().compile()
    app.invoke({"x": 0}, RunConfig(thread_id="no-saver"))
    with pytest.raises(InterruptError) as excinfo:
        app.invoke(Command(resume="yes"), RunConfig(thread_id="no-saver"))
    assert excinfo.value.reason == InterruptError.REASON_CHECKPOINTER_REQUIRED


def test_static_interrupt_before_first_round_counts_one_and_resumes_once() -> None:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    saver = MemorySaver()
    cfg = RunConfig(thread_id="static-before")
    app = builder.compile(checkpointer=saver, interrupt_before=["a"])
    first = app.invoke({"x": 0}, cfg)
    assert "__interrupt__" in first
    snapshots = _snapshots(saver, cfg)
    assert len(snapshots) == 1
    suspended = snapshots[0].snapshot
    assert suspended.next == ("a",)
    assert suspended.interrupts == ()
    assert suspended.tasks == ()
    assert snapshots[0].scheduler["suspension_kind"] == "static_before"

    app.invoke(Command(resume="ignored"), cfg)
    snapshots = _snapshots(saver, cfg)
    assert snapshots[0].snapshot.next == ()
    assert snapshots[0].snapshot.values == {"x": 2}
    assert sum(1 for item in snapshots if item.snapshot.next == ()) == 1


def test_static_interrupt_after_replaces_round_snapshot_and_has_no_tasks() -> None:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    saver = MemorySaver()
    cfg = RunConfig(thread_id="static-after")
    app = builder.compile(checkpointer=saver, interrupt_after=["a"])
    first = app.invoke({"x": 0}, cfg)
    assert "__interrupt__" in first
    snapshots = _snapshots(saver, cfg)
    suspended = snapshots[0].snapshot
    assert suspended.tasks == ()
    assert suspended.next == ("b",)
    assert snapshots[0].scheduler["suspension_kind"] == "static_after"

    app.invoke(Command(resume="ignored"), cfg)
    snapshots = _snapshots(saver, cfg)
    assert snapshots[0].snapshot.values == {"x": 2}
    assert snapshots[0].snapshot.next == ()
    assert sum(1 for item in snapshots if item.snapshot.next == ()) == 1
