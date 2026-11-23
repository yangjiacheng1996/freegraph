# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L4 持久化层 · **SQLite checkpointer** —— 属 **B15F1**。

``SqliteSaver`` 用标准库 ``sqlite3`` 把 checkpoint（快照 + pending writes）落到
本地文件或 ``:memory:``，满足 L1 ``Checkpointer`` 的 8 个方法；定位是
freegraph **面向真实使用的默认后端**（零第三方依赖、零配置、可跨重启）。

**核心口径**（详见 ``specs/b15f1-sqlite-saver-state-history/spec.md``）：

* **B14F1 冻结面逐字复用**：``put`` / ``put_writes`` 关键字、``CheckpointTuple``
  三字段、checkpoint 顺位 id（每线程 ``f"{n:032d}"``）、``.pending_writes`` 按
  ``(task_path, task_id, idx)`` 升序、``context`` 不持久化；
* **上游同款连接模型**：单连接 + 每实例一把 ``threading.Lock`` +
  ``check_same_thread=False`` + ``PRAGMA journal_mode=WAL``；支持 ``:memory:``；
* **序列化**：标准库 ``json``（``._json``）；``__interrupt__`` 走 channel-aware 投影；
  不可序列化 ⇒ ``TypeError`` 且**零写入**；
* **失败信号**：``sqlite3.Error`` 子类**原样传播**，单次写操作原子回滚。

**依赖纪律**（L4）：只依赖 L1 ``freegraph.contracts`` + 标准库；MUST NOT import
L2 / L3 / L5；零第三方依赖、零环境变量、零出站。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import copy
import re
import sqlite3
import threading
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from freegraph.contracts.types import RunConfig, StateSnapshot

from . import _json
from ._types import CheckpointTuple
from .memory import _WRITES_IDX_MAP

__all__ = ["SqliteSaver"]


_FILTER_KEY_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_MISSING = object()


def _json_extract(data: Any, key: str) -> Any:
    """简化版 ``json_extract(data, '$.a.b')`` —— 点分路径逐层取值。"""
    current = data
    for part in key.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


def _canonical(value: Any) -> str:
    return _json.dumps(value)


def _filter_value_matches(actual: Any, expected: Any) -> bool:
    """按上游 ``_metadata_predicate`` 的取值口径比较。"""
    if expected is None:
        return actual is _MISSING or actual is None
    if isinstance(expected, bool):
        target = 1 if expected else 0
        return actual is not _MISSING and actual == target
    if isinstance(expected, (dict, list)):
        if actual is _MISSING:
            return False
        try:
            return _canonical(actual) == _canonical(expected)
        except TypeError:
            return False
    return actual is not _MISSING and actual == expected


def _metadata_matches(metadata: Mapping[str, Any], predicate: Mapping[str, Any]) -> bool:
    for key, expected in predicate.items():
        if not _FILTER_KEY_RE.match(key):
            raise ValueError(f"Invalid filter key: {key!r}")
        actual = _json_extract(metadata, key)
        if not _filter_value_matches(actual, expected):
            return False
    return True


class SqliteSaver:
    """**SQLite checkpointer**（磁盘持久化 · 上游同步 saver 的零依赖移植）。"""

    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        on_checkpoint: Any = None,
    ) -> None:
        if on_checkpoint is not None and not callable(on_checkpoint):
            raise TypeError("on_checkpoint must be callable or None")
        self.conn = conn
        self._on_checkpoint = on_checkpoint
        self._lock = threading.Lock()
        self._setup_done = False

    # ── 构造入口（上游同款）─────────────────────────────────────────

    @classmethod
    @contextmanager
    def from_conn_string(
        cls,
        conn_string: str,
        *,
        on_checkpoint: Any = None,
    ) -> Iterator["SqliteSaver"]:
        """用 ``sqlite3.connect(conn_string, check_same_thread=False)`` 打开，
        退出 ``with`` 时关闭连接（上游 ``closing`` 同款）。"""
        conn = sqlite3.connect(conn_string, check_same_thread=False)
        try:
            yield cls(conn, on_checkpoint=on_checkpoint)
        finally:
            conn.close()

    # ── setup / 事务 ────────────────────────────────────────────────

    def _ensure_setup(self) -> None:
        """首次操作建表（WAL + ``checkpoints`` / ``writes``）· 调用方持锁。"""
        if self._setup_done:
            return
        cursor = self.conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS checkpoints ("
                " thread_id TEXT NOT NULL,"
                " checkpoint_ns TEXT NOT NULL DEFAULT '',"
                " checkpoint_id TEXT NOT NULL,"
                " parent_checkpoint_id TEXT,"
                " state_values TEXT NOT NULL,"
                " state_metadata TEXT NOT NULL,"
                " created_at TEXT NOT NULL,"
                " PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)"
                ")"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS writes ("
                " thread_id TEXT NOT NULL,"
                " checkpoint_ns TEXT NOT NULL DEFAULT '',"
                " checkpoint_id TEXT NOT NULL,"
                " task_id TEXT NOT NULL,"
                " idx INTEGER NOT NULL,"
                " task_path TEXT NOT NULL DEFAULT '',"
                " channel TEXT NOT NULL,"
                " value TEXT NOT NULL,"
                " PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)"
                ")"
            )
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        finally:
            cursor.close()
        self._setup_done = True

    def _snapshot_from_row(self, row: Sequence[Any]) -> tuple[StateSnapshot, dict[str, Any]]:
        thread_id = row[0]
        checkpoint_id = row[2]
        parent_id = row[3]
        values = _json.decode_values(row[4])
        metadata = _json.decode_metadata(row[5])
        created_at = row[6]
        snapshot_config = RunConfig(
            thread_id=thread_id,
            configurable={"checkpoint_id": checkpoint_id},
        )
        parent_config = (
            RunConfig(
                thread_id=thread_id,
                configurable={"checkpoint_id": parent_id},
            )
            if parent_id
            else None
        )
        snapshot = StateSnapshot(
            values=values,
            next=tuple(metadata.get("next") or ()),
            config=snapshot_config,
            metadata=metadata,
            created_at=created_at,
            parent_config=parent_config,
            tasks=tuple(metadata.get("tasks") or ()),
            interrupts=tuple(metadata.get("interrupts") or ()),
        )
        return snapshot, metadata

    def _load_writes(
        self, thread_id: str, checkpoint_id: str
    ) -> tuple[tuple[str, str, Any], ...]:
        cursor = self.conn.cursor()
        try:
            rows = cursor.execute(
                "SELECT task_id, channel, value FROM writes"
                " WHERE thread_id=? AND checkpoint_ns='' AND checkpoint_id=?"
                " ORDER BY task_path, task_id, idx",
                (thread_id, checkpoint_id),
            ).fetchall()
        finally:
            cursor.close()
        return tuple(
            (task_id, channel, _json.decode_write_value(channel, value))
            for task_id, channel, value in rows
        )

    def _make_tuple(
        self, row: Sequence[Any]
    ) -> CheckpointTuple:
        snapshot, metadata = self._snapshot_from_row(row)
        pending = self._load_writes(row[0], row[2])
        scheduler = metadata.get("scheduler")
        scheduler_copy = copy.deepcopy(dict(scheduler)) if isinstance(scheduler, Mapping) else {}
        return CheckpointTuple(
            snapshot=copy.deepcopy(snapshot),
            pending_writes=pending,
            scheduler=scheduler_copy,
        )

    # ── 8 方法协议 ──────────────────────────────────────────────────

    def get_tuple(self, config: RunConfig) -> CheckpointTuple | None:
        thread_id = _require_thread_id(config)
        checkpoint_id = _checkpoint_id(config)
        with self._lock:
            self._ensure_setup()
            cursor = self.conn.cursor()
            try:
                if checkpoint_id:
                    row = cursor.execute(
                        "SELECT * FROM checkpoints"
                        " WHERE thread_id=? AND checkpoint_ns='' AND checkpoint_id=?",
                        (thread_id, str(checkpoint_id)),
                    ).fetchone()
                else:
                    row = cursor.execute(
                        "SELECT * FROM checkpoints"
                        " WHERE thread_id=? AND checkpoint_ns=''"
                        " ORDER BY checkpoint_id DESC LIMIT 1",
                        (thread_id,),
                    ).fetchone()
            finally:
                cursor.close()
            if row is None:
                return None
            return self._make_tuple(row)

    def list(
        self,
        config: RunConfig | None = None,
        *,
        filter: Mapping[str, Any] | None = None,
        before: RunConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        if filter is not None and not isinstance(filter, Mapping):
            raise TypeError("filter must be a Mapping or None")
        if before is not None and not isinstance(before, (RunConfig, Mapping)):
            raise TypeError("before must be a RunConfig, Mapping, or None")
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int)):
            raise TypeError("limit must be an int or None")
        if filter is not None:
            for key in filter:
                if not isinstance(key, str) or not _FILTER_KEY_RE.match(key):
                    raise ValueError(f"Invalid filter key: {key!r}")

        thread_id = None if config is None else _require_thread_id(config)
        if limit is not None and limit <= 0:
            return iter(())

        checkpoint_filter = _checkpoint_id(config)
        before_id = _checkpoint_id(before)

        with self._lock:
            self._ensure_setup()
            cursor = self.conn.cursor()
            try:
                if thread_id is not None:
                    thread_ids = [thread_id]
                else:
                    thread_ids = [
                        row[0]
                        for row in cursor.execute(
                            "SELECT thread_id FROM checkpoints"
                            " WHERE checkpoint_ns=''"
                            " GROUP BY thread_id ORDER BY MIN(rowid)"
                        ).fetchall()
                    ]
                results: list[CheckpointTuple] = []
                remaining = limit
                for current_thread in thread_ids:
                    rows = cursor.execute(
                        "SELECT * FROM checkpoints"
                        " WHERE thread_id=? AND checkpoint_ns=''"
                        " ORDER BY checkpoint_id DESC",
                        (current_thread,),
                    ).fetchall()
                    for row in rows:
                        cid = row[2]
                        if checkpoint_filter and cid != str(checkpoint_filter):
                            continue
                        if before_id and cid >= str(before_id):
                            continue
                        if filter:
                            metadata = _json.decode_metadata(row[5])
                            if not _metadata_matches(metadata, filter):
                                continue
                        if remaining is not None:
                            remaining -= 1
                        results.append(self._make_tuple(row))
                        if remaining is not None and remaining <= 0:
                            return iter(results)
                return iter(results)
            finally:
                cursor.close()

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

        values_json = _json.encode_values(values)
        metadata_json = _json.encode_metadata(metadata)

        with self._lock:
            self._ensure_setup()
            cursor = self.conn.cursor()
            try:
                max_row = cursor.execute(
                    "SELECT MAX(checkpoint_id) FROM checkpoints"
                    " WHERE thread_id=? AND checkpoint_ns=''",
                    (thread_id,),
                ).fetchone()
                max_id = max_row[0] if max_row else None
                sequence = int(max_id) + 1 if max_id else 1
                checkpoint_id = f"{sequence:032d}"
                created_at = _now_iso()
                cursor.execute(
                    "INSERT INTO checkpoints"
                    " (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id,"
                    "  state_values, state_metadata, created_at)"
                    " VALUES (?, '', ?, ?, ?, ?, ?)",
                    (
                        thread_id,
                        checkpoint_id,
                        max_id,
                        values_json,
                        metadata_json,
                        created_at,
                    ),
                )
                self.conn.commit()
            except BaseException:
                self.conn.rollback()
                raise
            finally:
                cursor.close()

        result = RunConfig(
            thread_id=thread_id,
            configurable={"checkpoint_id": checkpoint_id},
        )
        callback = self._on_checkpoint
        if callback is not None:
            snapshot = StateSnapshot(
                values=_json.decode_values(values_json),
                next=tuple(metadata.get("next") or ()),
                config=result,
                metadata=_json.decode_metadata(metadata_json),
                created_at=created_at,
                parent_config=(
                    RunConfig(
                        thread_id=thread_id,
                        configurable={"checkpoint_id": max_id},
                    )
                    if max_id
                    else None
                ),
                tasks=tuple(metadata.get("tasks") or ()),
                interrupts=tuple(metadata.get("interrupts") or ()),
            )
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

        encoded: list[tuple[int, str, str]] = []
        for index, item in enumerate(writes):
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise TypeError("writes must be a sequence of (channel, value)")
            channel, value = item
            if not isinstance(channel, str):
                raise TypeError("write channel must be a str")
            inner_index = _WRITES_IDX_MAP.get(channel, index)
            encoded.append((inner_index, channel, _json.encode_write_value(channel, value)))

        with self._lock:
            self._ensure_setup()
            cursor = self.conn.cursor()
            try:
                exists = cursor.execute(
                    "SELECT 1 FROM checkpoints"
                    " WHERE thread_id=? AND checkpoint_ns='' AND checkpoint_id=?",
                    (thread_id, str(checkpoint_id)),
                ).fetchone()
                if exists is None:
                    raise ValueError("checkpoint_id does not exist in this thread")
                for inner_index, channel, value_json in encoded:
                    verb = "INSERT OR REPLACE" if inner_index < 0 else "INSERT OR IGNORE"
                    cursor.execute(
                        f"{verb} INTO writes"
                        " (thread_id, checkpoint_ns, checkpoint_id, task_id, idx,"
                        "  task_path, channel, value)"
                        " VALUES (?, '', ?, ?, ?, ?, ?, ?)",
                        (
                            thread_id,
                            str(checkpoint_id),
                            task_id,
                            inner_index,
                            task_path,
                            channel,
                            value_json,
                        ),
                    )
                self.conn.commit()
            except BaseException:
                self.conn.rollback()
                raise
            finally:
                cursor.close()

    def delete_thread(self, thread_id: str) -> None:
        if not isinstance(thread_id, str):
            raise TypeError("thread_id must be a str")
        with self._lock:
            self._ensure_setup()
            cursor = self.conn.cursor()
            try:
                cursor.execute(
                    "DELETE FROM writes WHERE thread_id=?", (thread_id,)
                )
                cursor.execute(
                    "DELETE FROM checkpoints WHERE thread_id=?", (thread_id,)
                )
                self.conn.commit()
            except BaseException:
                self.conn.rollback()
                raise
            finally:
                cursor.close()

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
