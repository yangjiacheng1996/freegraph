# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · ``SqliteSaver`` 的 JSON 编解码 / 冻结字段重建 / 原子性。"""

from __future__ import annotations

import sqlite3

import pytest

from freegraph.contracts import RunConfig
from freegraph.contracts.types import Interrupt, PregelTask
from freegraph.persistence import SqliteSaver


def _saver() -> SqliteSaver:
    return SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))


def _metadata(**overrides):
    base = {"next": (), "interrupts": (), "tasks": (), "scheduler": {"fanout": {}}}
    base.update(overrides)
    return base


def test_values_tuple_becomes_list_and_frozen_fields_rebuilt() -> None:
    saver = _saver()
    interrupt = Interrupt(value={"ask": True}, id="i1")
    task = PregelTask(
        id="a", name="a", path=("a",), interrupts=(interrupt,), result={"x": 1}
    )
    c = saver.put(
        RunConfig(thread_id="t"),
        values={"user": (1, 2)},
        metadata=_metadata(next=("a",), interrupts=(interrupt,), tasks=(task,)),
    )
    t = saver.get_tuple(c)
    assert t is not None
    # X-05: user tuple -> list
    assert t.snapshot.values["user"] == [1, 2]
    # frozen fields rebuilt
    assert t.snapshot.next == ("a",)
    assert isinstance(t.snapshot.interrupts, tuple)
    assert isinstance(t.snapshot.interrupts[0], Interrupt)
    assert t.snapshot.interrupts[0].id == "i1"
    assert isinstance(t.snapshot.tasks, tuple)
    rebuilt = t.snapshot.tasks[0]
    assert isinstance(rebuilt, PregelTask)
    assert rebuilt.path == ("a",)
    assert isinstance(rebuilt.interrupts, tuple)
    assert isinstance(rebuilt.interrupts[0], Interrupt)


def test_pending_interrupt_channel_roundtrip() -> None:
    saver = _saver()
    c = saver.put(RunConfig(thread_id="t"), values={}, metadata=_metadata(next=("a",)))
    payload = (Interrupt(value={"q": 1}, id="i1"),)
    saver.put_writes(c, writes=[("__interrupt__", payload)], task_id="a")
    t = saver.get_tuple(c)
    assert t is not None
    by_channel = {channel: value for _task, channel, value in t.pending_writes}
    assert isinstance(by_channel["__interrupt__"], tuple)
    assert isinstance(by_channel["__interrupt__"][0], Interrupt)
    assert by_channel["__interrupt__"][0].id == "i1"


def test_task_error_or_state_non_none_raises_type_error() -> None:
    saver = _saver()
    bad_error = PregelTask(id="a", name="a", error=ValueError("x"))
    with pytest.raises(TypeError):
        saver.put(
            RunConfig(thread_id="t"),
            values={},
            metadata=_metadata(tasks=(bad_error,)),
        )
    bad_state = PregelTask(id="a", name="a", state=RunConfig(thread_id="t"))
    with pytest.raises(TypeError):
        saver.put(
            RunConfig(thread_id="t"),
            values={},
            metadata=_metadata(tasks=(bad_state,)),
        )


def test_non_serializable_payload_raises_and_writes_nothing() -> None:
    saver = _saver()
    with pytest.raises(TypeError):
        saver.put(
            RunConfig(thread_id="t"),
            values={"bad": object()},
            metadata=_metadata(),
        )
    # zero write
    assert saver.get_tuple(RunConfig(thread_id="t")) is None
    assert list(saver.list(RunConfig(thread_id="t"))) == []


def test_bad_interrupt_payload_raises() -> None:
    saver = _saver()
    c = saver.put(RunConfig(thread_id="t"), values={}, metadata=_metadata())
    with pytest.raises(TypeError):
        saver.put_writes(c, writes=[("__interrupt__", "not-an-interrupt")], task_id="a")
    # zero write on failure
    t = saver.get_tuple(c)
    assert t is not None
    assert all(channel != "__interrupt__" for _t, channel, _v in t.pending_writes)
