# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · ``SqliteSaver`` 协议 / CRUD / list / delete / 版本 / 生命周期。"""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from freegraph.contracts import Checkpointer, RunConfig
from freegraph.persistence import SqliteSaver


def _saver() -> SqliteSaver:
    return SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))


def _put(saver: SqliteSaver, thread: str, value: int, next_nodes: tuple[str, ...] = ()) -> Any:
    return saver.put(
        RunConfig(thread_id=thread),
        values={"n": value},
        metadata={
            "next": next_nodes,
            "interrupts": (),
            "tasks": (),
            "scheduler": {"fanout": {}},
        },
    )


def test_is_checkpointer_and_has_eight_methods() -> None:
    saver = _saver()
    assert isinstance(saver, Checkpointer)
    for name in (
        "get_tuple",
        "list",
        "put",
        "put_writes",
        "delete_thread",
        "delete_for_runs",
        "copy_thread",
        "get_next_version",
    ):
        assert callable(getattr(saver, name))
    with pytest.raises(NotImplementedError):
        saver.delete_for_runs(["r"])
    with pytest.raises(NotImplementedError):
        saver.copy_thread("a", "b")


def test_put_get_tuple_parent_chain_and_ids() -> None:
    saver = _saver()
    c1 = _put(saver, "t", 1, ("b",))
    c2 = _put(saver, "t", 2)
    assert c1.configurable["checkpoint_id"] == f"{1:032d}"
    assert c2.configurable["checkpoint_id"] == f"{2:032d}"

    latest = saver.get_tuple(RunConfig(thread_id="t"))
    assert latest is not None
    assert latest.snapshot.values == {"n": 2}
    assert latest.snapshot.parent_config is not None
    assert latest.snapshot.parent_config.configurable["checkpoint_id"] == f"{1:032d}"
    assert latest.snapshot.next == ()

    first = saver.get_tuple(c1)
    assert first is not None
    assert first.snapshot.parent_config is None
    assert first.snapshot.next == ("b",)


def test_get_tuple_unknown_thread_and_id_returns_none() -> None:
    saver = _saver()
    assert saver.get_tuple(RunConfig(thread_id="missing")) is None
    c = _put(saver, "t", 1)
    missing = RunConfig(thread_id="t", configurable={"checkpoint_id": f"{9:032d}"})
    assert saver.get_tuple(missing) is None


def test_pending_writes_dedup_and_order() -> None:
    saver = _saver()
    c = _put(saver, "t", 1, ("b",))
    saver.put_writes(c, writes=[("a", 1), ("b", 2)], task_id="b")
    # ordinary: first write wins across calls
    saver.put_writes(c, writes=[("a", 99)], task_id="b")
    # reserved: last write wins
    saver.put_writes(c, writes=[("__error__", "e1")], task_id="b")
    saver.put_writes(c, writes=[("__error__", "e2")], task_id="b")
    t = saver.get_tuple(c)
    assert t is not None
    pending = {(task, channel): value for task, channel, value in t.pending_writes}
    assert pending[("b", "a")] == 1
    assert pending[("b", "b")] == 2
    assert pending[("b", "__error__")] == "e2"
    # order = (task_path, task_id, idx): reserved negative first
    assert t.pending_writes[0][1] == "__error__"


def test_list_order_before_limit_and_global_limit() -> None:
    saver = _saver()
    for i in range(3):
        _put(saver, "t1", i)
    for i in range(2):
        _put(saver, "t2", i)

    ids = [
        item.snapshot.config.configurable["checkpoint_id"]
        for item in saver.list(RunConfig(thread_id="t1"))
    ]
    assert ids == sorted(ids, reverse=True)
    assert len(ids) == 3

    before = RunConfig(thread_id="t1", configurable={"checkpoint_id": f"{3:032d}"})
    assert len(list(saver.list(RunConfig(thread_id="t1"), before=before))) == 2
    assert len(list(saver.list(RunConfig(thread_id="t1"), limit=1))) == 1
    assert list(saver.list(RunConfig(thread_id="t1"), limit=0)) == []
    # config=None: global limit across threads
    assert len(list(saver.list(None, limit=3))) == 3
    # thread order = first write order (t1 then t2)
    threads = [item.snapshot.config.thread_id for item in saver.list(None)]
    assert threads.index("t1") < threads.index("t2")


def test_list_filter_top_level_and_dotted() -> None:
    saver = _saver()
    saver.put(
        RunConfig(thread_id="t"),
        values={},
        metadata={"source": "loop", "nested": {"k": 1}, "scheduler": {}},
    )
    assert len(list(saver.list(RunConfig(thread_id="t"), filter={"source": "loop"}))) == 1
    assert len(list(saver.list(RunConfig(thread_id="t"), filter={"source": "x"}))) == 0
    assert len(list(saver.list(RunConfig(thread_id="t"), filter={"nested.k": 1}))) == 1


def test_delete_thread_is_idempotent_and_isolated() -> None:
    saver = _saver()
    _put(saver, "t1", 1)
    _put(saver, "t2", 2)
    saver.delete_thread("t1")
    saver.delete_thread("t1")  # idempotent
    assert saver.get_tuple(RunConfig(thread_id="t1")) is None
    assert list(saver.list(RunConfig(thread_id="t1"))) == []
    assert saver.get_tuple(RunConfig(thread_id="t2")) is not None
    # rebuild starts from id 1
    c = _put(saver, "t1", 3)
    assert c.configurable["checkpoint_id"] == f"{1:032d}"
    with pytest.raises(TypeError):
        saver.delete_thread(123)  # type: ignore[arg-type]


def test_get_next_version() -> None:
    saver = _saver()
    assert saver.get_next_version(None) == 1
    assert saver.get_next_version(5) == 6
    with pytest.raises(TypeError):
        saver.get_next_version(True)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        saver.get_next_version("x")  # type: ignore[arg-type]


def test_lifecycle_from_conn_string_and_memory() -> None:
    with SqliteSaver.from_conn_string(":memory:") as saver:
        _put(saver, "t", 1)
        assert saver.get_tuple(RunConfig(thread_id="t")) is not None
    # after context exit the connection is closed
    saver = _saver()
    conn = saver.conn
    conn.close()
    with pytest.raises(sqlite3.ProgrammingError):
        saver.get_tuple(RunConfig(thread_id="t"))


def test_conn_string_is_passed_through_unchanged(tmp_path) -> None:
    # '~' / '$VAR' must not be expanded: they are taken literally as file names.
    target = tmp_path / "weird~name.db"
    with SqliteSaver.from_conn_string(str(target)) as saver:
        _put(saver, "t", 1)
    assert target.exists()


def test_returned_structures_are_independent_copies() -> None:
    saver = _saver()
    c = _put(saver, "t", 1)
    t = saver.get_tuple(c)
    assert t is not None
    t.snapshot.values["n"] = 999
    t.scheduler["injected"] = True
    t2 = saver.get_tuple(c)
    assert t2 is not None
    assert t2.snapshot.values["n"] == 1
    assert "injected" not in t2.scheduler
