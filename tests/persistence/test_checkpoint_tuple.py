# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B14F1 · ``CheckpointTuple`` 读侧载体（恰好三个公开字段）。"""

from __future__ import annotations

from dataclasses import fields

from freegraph.contracts.types import RunConfig, StateSnapshot
from freegraph.persistence import CheckpointTuple


def _snapshot() -> StateSnapshot:
    return StateSnapshot(
        values={"x": 1},
        next=(),
        config=RunConfig(thread_id="t"),
        metadata={},
        created_at="2026-11-22T00:00:00+00:00",
        parent_config=None,
        tasks=(),
        interrupts=(),
    )


def test_checkpoint_tuple_has_exactly_three_fields() -> None:
    assert [field.name for field in fields(CheckpointTuple)] == [
        "snapshot",
        "pending_writes",
        "scheduler",
    ]


def test_checkpoint_tuple_is_frozen_and_slots() -> None:
    tuple_ = CheckpointTuple(_snapshot(), (), {})
    assert not hasattr(tuple_, "__dict__")
    try:
        tuple_.scheduler = {}  # type: ignore[misc]
    except Exception as error:
        assert type(error).__name__ == "FrozenInstanceError"
    else:  # pragma: no cover
        raise AssertionError("CheckpointTuple must be frozen")


def test_checkpoint_tuple_has_no_upstream_aliases() -> None:
    tuple_ = CheckpointTuple(_snapshot(), (), {})
    for name in ("config", "checkpoint", "metadata"):
        assert not hasattr(tuple_, name)


def test_checkpoint_tuple_fields_are_typed_as_specified() -> None:
    tuple_ = CheckpointTuple(
        _snapshot(),
        (("n", "x", 1),),
        {"channel_versions": {"x": 1}},
    )
    assert isinstance(tuple_.snapshot, StateSnapshot)
    assert isinstance(tuple_.pending_writes, tuple)
    assert isinstance(tuple_.scheduler, dict)
