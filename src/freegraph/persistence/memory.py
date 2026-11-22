# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L4 持久化层 · **内存 checkpointer** —— 属 **B14F1**。

``MemorySaver`` 按 ``thread_id`` 分区保存**状态快照**与 **pending writes**，满足
L1 ``Checkpointer`` 的 8 个方法。它定位为**开发 / 调试**（与上游
``InMemorySaver`` 一致），不保证跨进程 / 跨重启；生产场景由 B15F1 的
``SqliteSaver`` 承担。

**依赖纪律**（L4）：只依赖 L1 ``freegraph.contracts`` + 标准库；MUST NOT import
L2 / L3 / L5；零第三方依赖、零环境变量、零出站。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import copy
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from freegraph.contracts.types import RunConfig, StateSnapshot

from ._types import CheckpointTuple

__all__ = ["MemorySaver", "InMemorySaver"]


_WRITES_IDX_MAP = {
    "__error__": -1,
    "__scheduled__": -2,
    "__interrupt__": -3,
    "__resume__": -4,
}


@dataclass(frozen=True, slots=True)
class _StoredWrite:
    task_id: str
    channel: str
    value: Any
    task_path: str = ""
    idx: int = 0


@dataclass(frozen=True, slots=True)
class _StoredCheckpoint:
    snapshot: StateSnapshot
    metadata: dict[str, Any]
    created_at: str
    parent_config: RunConfig | None


@dataclass
class _ThreadStore:
    snapshots: dict[str, _StoredCheckpoint] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    writes: dict[str, dict[tuple[str, int], _StoredWrite]] = field(
        default_factory=dict
    )
    next_seq: int = 1
    latest_id: str | None = None


def _resolved_thread_id(config: Any) -> str | None:
    resolver = getattr(config, "resolved_thread_id", None)
    if callable(resolver):
        value = resolver()
        return value if isinstance(value, str) else None
    if isinstance(config, Mapping):
        configurable = config.get("configurable")
        if isinstance(configurable, Mapping):
            nested = configurable.get("thread_id")
            if isinstance(nested, str):
                return nested
        value = config.get("thread_id")
        return value if isinstance(value, str) else None
    return None


def _require_thread_id(config: Any) -> str:
    thread_id = _resolved_thread_id(config)
    if not thread_id:
        raise ValueError("config.configurable['thread_id'] is required")
    return thread_id


def _configurable(config: Any) -> Mapping[str, Any]:
    value = getattr(config, "configurable", None)
    if isinstance(value, Mapping):
        return value
    if isinstance(config, Mapping):
        value = config.get("configurable")
        if isinstance(value, Mapping):
            return value
    return {}


def _checkpoint_id(config: Any) -> Any:
    if config is None:
        return None
    return _configurable(config).get("checkpoint_id")


def _as_tuple(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    return tuple(value)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemorySaver:
    """**进程内 checkpointer**（开发 / 调试定位）。

    存储模型：每个 ``thread_id`` 一份 :class:`_ThreadStore`；快照与 pending writes
    **分层**保存。所有公开方法在**每实例一把** ``threading.RLock`` 下串行化；
    ``on_checkpoint`` 在锁释放后调用，其异常被吞掉且不回滚已提交的快照。
    """

    def __init__(
        self,
        *,
        on_checkpoint: Any = None,
    ) -> None:
        if on_checkpoint is not None and not callable(on_checkpoint):
            raise TypeError("on_checkpoint must be callable or None")
        self._on_checkpoint = on_checkpoint
        self._lock = RLock()
        self._threads: dict[str, _ThreadStore] = {}

    def _make_tuple(self, stored: _StoredCheckpoint, writes: Mapping[Any, _StoredWrite]) -> CheckpointTuple:
        pending = tuple(
            (item.task_id, item.channel, copy.deepcopy(item.value))
            for item in sorted(
                writes.values(),
                key=lambda item: (item.task_path, item.task_id, item.idx),
            )
        )
        scheduler = stored.metadata.get("scheduler")
        scheduler_copy = (
            copy.deepcopy(dict(scheduler))
            if isinstance(scheduler, Mapping)
            else {}
        )
        return CheckpointTuple(
            snapshot=copy.deepcopy(stored.snapshot),
            pending_writes=pending,
            scheduler=scheduler_copy,
        )

    def get_tuple(self, config: RunConfig) -> CheckpointTuple | None:
        thread_id = _require_thread_id(config)
        checkpoint_id = _checkpoint_id(config)
        with self._lock:
            store = self._threads.get(thread_id)
            if store is None:
                return None
            target = checkpoint_id if checkpoint_id else store.latest_id
            if not target:
                return None
            stored = store.snapshots.get(str(target))
            if stored is None:
                return None
            writes = store.writes.get(str(target), {})
            return self._make_tuple(stored, writes)

    def list(
        self,
        config: RunConfig | None = None,
        *,
        filter: Mapping[str, Any] | None = None,
        before: RunConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        if config is None:
            thread_id = None
        else:
            thread_id = _require_thread_id(config)

        if limit is not None and limit <= 0:
            return iter(())

        checkpoint_filter = _checkpoint_id(config)
        before_id = _checkpoint_id(before)

        with self._lock:
            thread_ids = (
                [thread_id]
                if thread_id is not None
                else list(self._threads.keys())
            )
            results: list[CheckpointTuple] = []
            remaining = limit
            for current_thread in thread_ids:
                store = self._threads.get(current_thread)
                if store is None:
                    continue
                for checkpoint_id in sorted(store.snapshots.keys(), reverse=True):
                    if checkpoint_filter and checkpoint_id != checkpoint_filter:
                        continue
                    if before_id and checkpoint_id >= before_id:
                        continue
                    stored = store.snapshots[checkpoint_id]
                    metadata = stored.metadata
                    if filter and not all(
                        metadata.get(key) == value
                        for key, value in filter.items()
                    ):
                        continue
                    if remaining is not None:
                        remaining -= 1
                    results.append(
                        self._make_tuple(
                            stored,
                            store.writes.get(checkpoint_id, {}),
                        )
                    )
                    if remaining is not None and remaining <= 0:
                        return iter(results)
            return iter(results)

    def put(
        self,
        config: RunConfig,
        *,
        values: Mapping[str, Any],
        metadata: Mapping[str, Any],
    ) -> RunConfig:
        thread_id = _require_thread_id(config)
        if not isinstance(values, Mapping):
            raise TypeError("values must be a Mapping")
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a Mapping")

        values_copy = copy.deepcopy(dict(values))
        metadata_copy = copy.deepcopy(dict(metadata))

        with self._lock:
            store = self._threads.get(thread_id)
            if store is None:
                store = _ThreadStore()
                self._threads[thread_id] = store

            sequence = store.next_seq
            store.next_seq += 1
            checkpoint_id = f"{sequence:032d}"

            parent_config = None
            if store.latest_id is not None:
                parent_config = store.snapshots[store.latest_id].snapshot.config

            created_at = _now_iso()
            snapshot_config = RunConfig(
                thread_id=thread_id,
                configurable={"checkpoint_id": checkpoint_id},
            )
            snapshot = StateSnapshot(
                values=values_copy,
                next=_as_tuple(metadata_copy.get("next")),
                config=snapshot_config,
                metadata=metadata_copy,
                created_at=created_at,
                parent_config=parent_config,
                tasks=_as_tuple(metadata_copy.get("tasks")),
                interrupts=_as_tuple(metadata_copy.get("interrupts")),
            )
            stored = _StoredCheckpoint(
                snapshot=snapshot,
                metadata=metadata_copy,
                created_at=created_at,
                parent_config=parent_config,
            )
            store.snapshots[checkpoint_id] = stored
            store.order.append(checkpoint_id)
            store.latest_id = checkpoint_id

            result = RunConfig(
                thread_id=thread_id,
                configurable={"checkpoint_id": checkpoint_id},
            )

        callback = self._on_checkpoint
        if callback is not None:
            try:
                callback(copy.deepcopy(snapshot))
            except Exception:
                pass
        return result

    def put_writes(
        self,
        config: RunConfig,
        *,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = _require_thread_id(config)
        configurable = _configurable(config)
        try:
            checkpoint_id = configurable["checkpoint_id"]
        except KeyError:
            raise KeyError("checkpoint_id") from None
        if not checkpoint_id:
            raise KeyError("checkpoint_id")
        if not isinstance(task_id, str):
            raise TypeError("task_id must be a str")
        if not task_id:
            raise ValueError("task_id must be non-empty")
        if not isinstance(task_path, str):
            raise TypeError("task_path must be a str")

        items: list[tuple[str, Any]] = []
        for item in writes:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise TypeError("writes must be a sequence of (channel, value)")
            channel, value = item
            if not isinstance(channel, str):
                raise TypeError("write channel must be a str")
            items.append((channel, copy.deepcopy(value)))

        with self._lock:
            store = self._threads.get(thread_id)
            if store is None or str(checkpoint_id) not in store.snapshots:
                raise ValueError("checkpoint_id does not exist in this thread")
            bucket = store.writes.setdefault(str(checkpoint_id), {})
            for index, (channel, value) in enumerate(items):
                inner_index = _WRITES_IDX_MAP.get(channel, index)
                inner_key = (task_id, inner_index)
                if inner_index >= 0 and inner_key in bucket:
                    continue
                bucket[inner_key] = _StoredWrite(
                    task_id=task_id,
                    channel=channel,
                    value=value,
                    task_path=task_path,
                    idx=inner_index,
                )

    def delete_thread(self, thread_id: str) -> None:
        if not isinstance(thread_id, str):
            raise TypeError("thread_id must be a str")
        with self._lock:
            self._threads.pop(thread_id, None)

    def delete_for_runs(self, run_ids: Sequence[str]) -> None:
        raise NotImplementedError("delete_for_runs is not implemented in v1")

    def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        raise NotImplementedError("copy_thread is not implemented in v1")

    def get_next_version(self, current: int | None, channel: None = None) -> int:
        if current is None:
            return 1
        if isinstance(current, bool) or not isinstance(current, int):
            raise TypeError("current must be an int or None")
        return current + 1


InMemorySaver = MemorySaver
