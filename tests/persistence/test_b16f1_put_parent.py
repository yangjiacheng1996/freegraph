# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · L4 ``put`` 显式父链扩展（双后端）。"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

import pytest

from freegraph.contracts import RunConfig
from freegraph.persistence import MemorySaver, SqliteSaver


def _memory() -> MemorySaver:
    return MemorySaver()


def _sqlite() -> SqliteSaver:
    return SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))


@pytest.fixture(params=[_memory, _sqlite], ids=["memory", "sqlite"])
def saver_factory(request: pytest.FixtureRequest) -> Callable[[], Any]:
    return request.param


def _config(thread_id: str = "t", checkpoint_id: str | None = None) -> RunConfig:
    configurable = {"checkpoint_id": checkpoint_id} if checkpoint_id else {}
    return RunConfig(thread_id=thread_id, configurable=configurable)


def _put(saver: Any, *, thread_id: str = "t", value: int = 1, parent: str | None = None) -> RunConfig:
    return saver.put(
        _config(thread_id, parent),
        values={"x": value},
        metadata={"next": (), "tasks": (), "interrupts": (), "scheduler": {}},
    )


def _id(config: RunConfig) -> str:
    value = config.configurable["checkpoint_id"]
    assert isinstance(value, str)
    return value


def test_explicit_parent_points_to_requested_snapshot(saver_factory: Callable[[], Any]) -> None:
    saver = saver_factory()
    first = _put(saver, value=1)
    second = _put(saver, value=2)
    branch = _put(saver, value=3, parent=_id(first))

    assert _id(branch) > _id(second)
    snapshot = saver.get_tuple(branch).snapshot
    assert snapshot.parent_config is not None
    assert _id(snapshot.parent_config) == _id(first)


def test_missing_explicit_id_keeps_latest_parent(saver_factory: Callable[[], Any]) -> None:
    saver = saver_factory()
    first = _put(saver, value=1)
    second = _put(saver, value=2)

    snapshot = saver.get_tuple(second).snapshot
    assert snapshot.parent_config is not None
    assert _id(snapshot.parent_config) == _id(first)


def test_explicit_missing_parent_fails_atomically(saver_factory: Callable[[], Any]) -> None:
    saver = saver_factory()
    _put(saver, value=1)
    before = len(list(saver.list(_config())))

    with pytest.raises(ValueError, match="checkpoint_id"):
        _put(saver, value=2, parent="9" * 32)

    assert len(list(saver.list(_config()))) == before


def test_callback_sees_actual_parent(saver_factory: Callable[[], Any]) -> None:
    seen: list[Any] = []
    if saver_factory is _sqlite:
        saver = SqliteSaver(
            sqlite3.connect(":memory:", check_same_thread=False),
            on_checkpoint=seen.append,
        )
    else:
        saver = MemorySaver(on_checkpoint=seen.append)

    first = _put(saver, value=1)
    _put(saver, value=2, parent=_id(first))

    assert len(seen) == 2
    assert seen[-1].parent_config is not None
    assert _id(seen[-1].parent_config) == _id(first)


def test_existing_calls_without_explicit_id_are_unchanged() -> None:
    memory = MemorySaver()
    sqlite = _sqlite()

    def sequence(saver: Any) -> list[str | None]:
        ids: list[str | None] = []
        for value in (1, 2, 3):
            config = _put(saver, value=value)
            snapshot = saver.get_tuple(config).snapshot
            ids.append(
                None
                if snapshot.parent_config is None
                else _id(snapshot.parent_config)
            )
        return ids

    assert sequence(memory) == sequence(sqlite)
