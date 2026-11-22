# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B14F1 · L4 ``MemorySaver`` 协议 / 存储 / 查询 / 删除 / 并发。"""

from __future__ import annotations

import copy
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from freegraph.contracts import Checkpointer
from freegraph.contracts.types import RunConfig
from freegraph.persistence import (
    CheckpointTuple,
    InMemorySaver,
    MemorySaver,
)


def _cfg(thread_id: str = "t", checkpoint_id: str | None = None) -> RunConfig:
    configurable = {} if checkpoint_id is None else {"checkpoint_id": checkpoint_id}
    return RunConfig(thread_id=thread_id, configurable=configurable)


def _put(saver: MemorySaver, thread_id: str = "t", **metadata):
    return saver.put(
        _cfg(thread_id),
        values={"x": 1},
        metadata=metadata or {"next": ()},
    )


class _Uncopyable:
    def __deepcopy__(self, memo):
        raise RuntimeError("cannot deep copy")


# ── 协议 / 模块面 ───────────────────────────────────────────────────────


def test_memory_saver_satisfies_checkpointer_and_method_surface() -> None:
    saver = MemorySaver()
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
    assert InMemorySaver is MemorySaver


def test_delete_for_runs_and_copy_thread_are_not_implemented_in_v1() -> None:
    saver = MemorySaver()
    with pytest.raises(NotImplementedError):
        saver.delete_for_runs(["r"])
    with pytest.raises(NotImplementedError):
        saver.copy_thread("a", "b")


def test_get_next_version_is_int_and_rejects_bool() -> None:
    saver = MemorySaver()
    assert saver.get_next_version(None) == 1
    assert saver.get_next_version(0) == 1
    assert saver.get_next_version(7) == 8
    with pytest.raises(TypeError):
        saver.get_next_version(True)
    with pytest.raises(TypeError):
        saver.get_next_version("1")


# ── put / get_tuple ─────────────────────────────────────────────────────


def test_put_builds_state_snapshot_and_parent_chain() -> None:
    saver = MemorySaver()
    first_cfg = saver.put(
        _cfg(),
        values={"x": 1},
        metadata={"next": ("a",), "tasks": (), "interrupts": ()},
    )
    second_cfg = saver.put(
        _cfg(),
        values={"x": 2},
        metadata={"next": (), "tasks": (), "interrupts": ()},
    )

    first = saver.get_tuple(first_cfg)
    second = saver.get_tuple(second_cfg)
    assert isinstance(first, CheckpointTuple)
    assert first is not None and second is not None
    assert first.snapshot.values == {"x": 1}
    assert first.snapshot.next == ("a",)
    assert first.snapshot.config.context is None
    assert first.snapshot.config.configurable["checkpoint_id"] == (
        first_cfg.configurable["checkpoint_id"]
    )
    assert first.snapshot.parent_config is None
    assert second.snapshot.parent_config == first.snapshot.config
    assert isinstance(second.snapshot.created_at, str)
    assert second.snapshot.metadata["next"] == ()


def test_put_rejects_non_mappings_and_missing_thread_id() -> None:
    saver = MemorySaver()
    with pytest.raises(ValueError):
        saver.put(RunConfig(), values={}, metadata={})
    with pytest.raises(TypeError):
        saver.put(_cfg(), values=[], metadata={})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        saver.put(_cfg(), values={}, metadata=[])  # type: ignore[arg-type]


def test_put_is_atomic_on_deepcopy_failure() -> None:
    saver = MemorySaver()
    with pytest.raises(RuntimeError):
        saver.put(
            _cfg(),
            values={"x": _Uncopyable()},
            metadata={"next": ()},
        )
    assert list(saver.list(_cfg())) == []


def test_get_tuple_three_states_and_missing_thread_id() -> None:
    saver = MemorySaver()
    assert saver.get_tuple(_cfg()) is None
    cfg = _put(saver)
    assert saver.get_tuple(_cfg("t", "999")) is None
    assert saver.get_tuple(cfg) is not None
    with pytest.raises(ValueError):
        saver.get_tuple(RunConfig())


def test_get_tuple_and_list_return_defensive_copies() -> None:
    saver = MemorySaver()
    cfg = saver.put(
        _cfg(),
        values={"x": {"nested": 1}},
        metadata={"next": (), "scheduler": {"channel_versions": {"x": 1}}},
    )
    saver.put_writes(cfg, writes=[("x", {"nested": 2})], task_id="n")

    first = saver.get_tuple(cfg)
    assert first is not None
    first.snapshot.values["x"]["nested"] = 99
    first.pending_writes[0][2]["nested"] = 99
    first.scheduler["channel_versions"]["x"] = 99

    second = saver.get_tuple(cfg)
    assert second is not None
    assert second.snapshot.values["x"]["nested"] == 1
    assert second.pending_writes[0][2]["nested"] == 2
    assert second.scheduler["channel_versions"]["x"] == 1


def test_metadata_is_deep_copied_on_put() -> None:
    saver = MemorySaver()
    metadata = {"next": (), "scheduler": {"channel_versions": {"x": 1}}}
    cfg = saver.put(_cfg(), values={"x": 1}, metadata=metadata)
    metadata["scheduler"]["channel_versions"]["x"] = 99
    stored = saver.get_tuple(cfg)
    assert stored is not None
    assert stored.scheduler["channel_versions"]["x"] == 1


# ── put_writes ─────────────────────────────────────────────────────────


def test_put_writes_keeps_snapshot_values_unchanged() -> None:
    saver = MemorySaver()
    cfg = saver.put(_cfg(), values={"x": 1}, metadata={"next": ()})
    saver.put_writes(cfg, writes=[("x", 2)], task_id="n", task_path="n")
    stored = saver.get_tuple(cfg)
    assert stored is not None
    assert stored.snapshot.values == {"x": 1}
    assert stored.pending_writes == (("n", "x", 2),)


def test_put_writes_dedup_normal_and_reserved_channels() -> None:
    saver = MemorySaver()
    cfg = saver.put(_cfg(), values={}, metadata={"next": ()})
    saver.put_writes(cfg, writes=[("x", 1)], task_id="n")
    saver.put_writes(cfg, writes=[("x", 2)], task_id="n")
    saver.put_writes(
        cfg,
        writes=[("__interrupt__", ("p1",)), ("__interrupt__", ("p2",))],
        task_id="n",
    )
    stored = saver.get_tuple(cfg)
    assert stored is not None
    assert ("n", "x", 1) in stored.pending_writes
    assert ("n", "x", 2) not in stored.pending_writes
    assert ("n", "__interrupt__", ("p2",)) in stored.pending_writes
    assert ("n", "__interrupt__", ("p1",)) not in stored.pending_writes


def test_put_writes_keeps_distinct_normal_indices_and_sorts() -> None:
    saver = MemorySaver()
    cfg = saver.put(_cfg(), values={}, metadata={"next": ()})
    saver.put_writes(
        cfg,
        writes=[("a", 1), ("b", 2)],
        task_id="z",
        task_path="b",
    )
    saver.put_writes(cfg, writes=[("c", 3)], task_id="a", task_path="a")
    stored = saver.get_tuple(cfg)
    assert stored is not None
    assert stored.pending_writes == (
        ("a", "c", 3),
        ("z", "a", 1),
        ("z", "b", 2),
    )


def test_put_writes_failure_signals() -> None:
    saver = MemorySaver()
    cfg = saver.put(_cfg(), values={}, metadata={"next": ()})
    with pytest.raises(ValueError):
        saver.put_writes(RunConfig(), writes=[], task_id="n")
    with pytest.raises(KeyError):
        saver.put_writes(_cfg(), writes=[], task_id="n")
    with pytest.raises(ValueError):
        saver.put_writes(_cfg("t", "999"), writes=[], task_id="n")
    with pytest.raises(TypeError):
        saver.put_writes(cfg, writes=[], task_id=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        saver.put_writes(cfg, writes=[], task_id="")
    with pytest.raises(TypeError):
        saver.put_writes(cfg, writes=[(1, "x")], task_id="n")  # type: ignore[list-item]
    saver.put_writes(cfg, writes=[], task_id="n")
    stored = saver.get_tuple(cfg)
    assert stored is not None and stored.pending_writes == ()


# ── list ───────────────────────────────────────────────────────────────


def test_list_filter_before_limit_and_order() -> None:
    saver = MemorySaver()
    first = saver.put(_cfg(), values={"x": 1}, metadata={"kind": "a"})
    second = saver.put(_cfg(), values={"x": 2}, metadata={"kind": "b"})
    third = saver.put(_cfg(), values={"x": 3}, metadata={"kind": "a"})
    ids = [item.snapshot.config.configurable["checkpoint_id"] for item in saver.list(_cfg())]
    assert ids == [
        third.configurable["checkpoint_id"],
        second.configurable["checkpoint_id"],
        first.configurable["checkpoint_id"],
    ]

    filtered = list(saver.list(_cfg(), filter={"kind": "a"}))
    assert [item.snapshot.values["x"] for item in filtered] == [3, 1]
    before = _cfg("t", second.configurable["checkpoint_id"])
    assert [item.snapshot.values["x"] for item in saver.list(_cfg(), before=before)] == [1]
    assert list(saver.list(_cfg(), limit=2))[0].snapshot.values["x"] == 3
    assert list(saver.list(_cfg(), limit=0)) == []
    assert list(saver.list(_cfg(), limit=-1)) == []


def test_list_none_uses_thread_insertion_order() -> None:
    saver = MemorySaver()
    saver.put(_cfg("thread-b"), values={"x": 1}, metadata={"next": ()})
    saver.put(_cfg("thread-a"), values={"x": 2}, metadata={"next": ()})
    items = list(saver.list(None))
    assert [item.snapshot.config.thread_id for item in items] == [
        "thread-b",
        "thread-a",
    ]


def test_list_and_get_tuple_require_thread_id_but_list_none_is_legal() -> None:
    saver = MemorySaver()
    with pytest.raises(ValueError):
        list(saver.list(RunConfig()))
    assert list(saver.list(None)) == []
    with pytest.raises(ValueError):
        saver.get_tuple(RunConfig())


# ── delete / isolation / concurrency ───────────────────────────────────


def test_delete_thread_is_idempotent_and_isolated() -> None:
    saver = MemorySaver()
    saver.put(_cfg("thread-1"), values={"x": 1}, metadata={"next": ()})
    saver.put(_cfg("thread-2"), values={"x": 2}, metadata={"next": ()})
    saver.delete_thread("thread-1")
    saver.delete_thread("thread-1")
    assert list(saver.list(_cfg("thread-1"))) == []
    assert list(saver.list(_cfg("thread-2")))[0].snapshot.values == {"x": 2}
    with pytest.raises(TypeError):
        saver.delete_thread(1)  # type: ignore[arg-type]


def test_delete_thread_then_recreate_starts_at_one() -> None:
    saver = MemorySaver()
    saver.put(_cfg("t"), values={}, metadata={"next": ()})
    saver.put(_cfg("t"), values={}, metadata={"next": ()})
    saver.delete_thread("t")
    cfg = saver.put(_cfg("t"), values={}, metadata={"next": ()})
    assert cfg.configurable["checkpoint_id"] == "0" * 31 + "1"


def test_two_threads_are_isolated() -> None:
    saver = MemorySaver()
    cfg1 = saver.put(_cfg("thread-1"), values={"x": 1}, metadata={"next": ()})
    cfg2 = saver.put(_cfg("thread-2"), values={"x": 2}, metadata={"next": ()})
    saver.put_writes(cfg1, writes=[("x", 10)], task_id="n")
    saver.put_writes(cfg2, writes=[("x", 20)], task_id="n")
    first = saver.get_tuple(cfg1)
    second = saver.get_tuple(cfg2)
    assert first is not None and second is not None
    assert first.snapshot.values == {"x": 1}
    assert second.snapshot.values == {"x": 2}
    assert first.pending_writes == (("n", "x", 10),)
    assert second.pending_writes == (("n", "x", 20),)


def test_concurrent_puts_on_same_thread_are_serialized() -> None:
    saver = MemorySaver()

    def write(index: int) -> None:
        saver.put(
            _cfg("t"),
            values={"x": index},
            metadata={"next": (), "index": index},
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(40)))

    items = list(saver.list(_cfg("t")))
    assert len(items) == 40
    ids = [item.snapshot.config.configurable["checkpoint_id"] for item in items]
    assert len(set(ids)) == 40
    assert ids == sorted(ids, reverse=True)


# ── on_checkpoint ──────────────────────────────────────────────────────


def test_on_checkpoint_called_once_per_successful_put_with_deep_copy() -> None:
    seen = []

    def callback(snapshot) -> None:
        snapshot.values["x"] = 999
        seen.append(snapshot)

    saver = MemorySaver(on_checkpoint=callback)
    cfg = saver.put(_cfg(), values={"x": 1}, metadata={"next": ()})
    assert len(seen) == 1
    stored = saver.get_tuple(cfg)
    assert stored is not None and stored.snapshot.values["x"] == 1


def test_on_checkpoint_exception_is_swallowed_and_put_succeeds() -> None:
    def callback(snapshot) -> None:
        raise RuntimeError("observer failed")

    saver = MemorySaver(on_checkpoint=callback)
    cfg = saver.put(_cfg(), values={"x": 1}, metadata={"next": ()})
    assert saver.get_tuple(cfg) is not None


def test_on_checkpoint_may_reenter_saver_without_deadlock() -> None:
    saver: MemorySaver | None = None
    observed = []

    def callback(snapshot) -> None:
        assert saver is not None
        observed.append(saver.get_tuple(_cfg()).snapshot.values)

    saver = MemorySaver(on_checkpoint=callback)
    saver.put(_cfg(), values={"x": 1}, metadata={"next": ()})
    assert observed == [{"x": 1}]


def test_on_checkpoint_must_be_callable_or_none() -> None:
    with pytest.raises(TypeError):
        MemorySaver(on_checkpoint=1)  # type: ignore[arg-type]
    MemorySaver(on_checkpoint=None)


def test_scheduler_is_json_serializable() -> None:
    saver = MemorySaver()
    cfg = saver.put(
        _cfg(),
        values={},
        metadata={"next": (), "scheduler": {"channel_versions": {"x": 1}}},
    )
    stored = saver.get_tuple(cfg)
    assert stored is not None
    json.dumps(stored.scheduler)
