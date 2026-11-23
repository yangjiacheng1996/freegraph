# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · ``SqliteSaver`` 的失败信号 / 类型校验 / 生命周期。"""

from __future__ import annotations

import sqlite3

import pytest

from freegraph.contracts import RunConfig
from freegraph.persistence import SqliteSaver


def _saver() -> SqliteSaver:
    return SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))


def test_filter_key_validation() -> None:
    saver = _saver()
    with pytest.raises(ValueError):
        list(saver.list(RunConfig(thread_id="t"), filter={"bad key; drop": 1}))
    with pytest.raises(TypeError):
        list(saver.list(RunConfig(thread_id="t"), filter=["not", "mapping"]))  # type: ignore[arg-type]


def test_list_argument_type_errors() -> None:
    saver = _saver()
    with pytest.raises(TypeError):
        list(saver.list(RunConfig(thread_id="t"), before="not-a-config"))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        list(saver.list(RunConfig(thread_id="t"), limit=True))  # type: ignore[arg-type]


def test_put_type_errors() -> None:
    saver = _saver()
    with pytest.raises(TypeError):
        saver.put(RunConfig(thread_id="t"), values=[], metadata={})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        saver.put(RunConfig(thread_id="t"), values={}, metadata=[])  # type: ignore[arg-type]


def test_put_writes_targets_and_types() -> None:
    saver = _saver()
    with pytest.raises(KeyError):
        saver.put_writes(RunConfig(thread_id="t"), writes=[("a", 1)], task_id="x")
    c = saver.put(
        RunConfig(thread_id="t"),
        values={},
        metadata={"next": (), "interrupts": (), "tasks": (), "scheduler": {}},
    )
    missing = RunConfig(thread_id="t", configurable={"checkpoint_id": f"{9:032d}"})
    with pytest.raises(ValueError):
        saver.put_writes(missing, writes=[("a", 1)], task_id="x")
    with pytest.raises(TypeError):
        saver.put_writes(c, writes=[("a", 1)], task_id=123)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        saver.put_writes(c, writes=[("a", 1)], task_id="")


def test_closed_connection_propagates_programming_error() -> None:
    saver = SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))
    saver.conn.close()
    with pytest.raises(sqlite3.ProgrammingError):
        saver.get_tuple(RunConfig(thread_id="t"))
