# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 · **SQLite trace 后端** —— 属 **B20F2**（内部模块）。

``SqliteTraceStore`` 是 B19F1 sink 的 SQLite 写入 + 查询实现：写侧语义与
``FileTraceStore`` 完全一致（失败隔离 / 四路诊断 / 不重试 / 每实例锁），
查询语义由共享 :mod:`freegraph.observability._query` 提供。

* 只用标准库 ``sqlite3``；表结构 / SQL 是内部实现细节（C27 ⑤）；
* 构造与查询零文件系统副作用；首次写行才惰性建父目录 / 库 / 表；
* 不提供 ``close()`` / 上下文管理器 / 公开连接对象。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from freegraph.contracts.trace import Span, TraceQuery

from ._payloads import record_to_dict, span_to_dict
from ._query import finalize, normalize_query, normalize_row, parse_instant_ns
from ._record import TraceRecord

__all__ = ["SqliteTraceStore"]

_LOGGER = logging.getLogger(__name__)

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

_REQUIRED_COLUMNS: dict[str, str] = {
    "seq": "INTEGER",
    "kind": "TEXT",
    "run_id": "TEXT",
    "thread_id": "TEXT",
    "node": "TEXT",
    "checkpoint_id": "TEXT",
    "span_id": "TEXT",
    "start_time": "TEXT",
    "payload": "TEXT",
}

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS trace_entries (
    seq           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind          TEXT NOT NULL,
    run_id        TEXT NOT NULL,
    thread_id     TEXT,
    node          TEXT NOT NULL,
    checkpoint_id TEXT,
    span_id       TEXT NOT NULL,
    start_time    TEXT,
    payload       TEXT NOT NULL
)
"""

_CREATE_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_trace_run ON trace_entries(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_trace_thread ON trace_entries(thread_id)",
    "CREATE INDEX IF NOT EXISTS idx_trace_node ON trace_entries(node)",
    "CREATE INDEX IF NOT EXISTS idx_trace_span ON trace_entries(run_id, span_id)",
    "CREATE INDEX IF NOT EXISTS idx_trace_start ON trace_entries(start_time)",
)


class SqliteTraceStore:
    """SQLite 后端的 sink + 查询实现（L5）。"""

    __slots__ = (
        "_database",
        "_on_error",
        "_lock",
        "_local",
        "_write_errors",
        "_last_error",
    )

    def __init__(
        self,
        database: str | os.PathLike[str],
        *,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> None:
        """只保存参数并初始化锁 / 诊断；**不访问文件系统**。"""
        raw = os.fspath(database)
        if not isinstance(raw, str):
            raise TypeError("database must be str or os.PathLike[str]")
        if raw == ":memory:" or raw.startswith("file:"):
            raise ValueError("database must be a local file path (no :memory: / URI)")
        self._database = Path(raw)
        self._on_error = on_error
        self._lock = threading.Lock()
        self._local = threading.local()
        self._write_errors = 0
        self._last_error: str | None = None

    @property
    def write_errors(self) -> int:
        """持久化失败计数（初值 0，单调递增）；读时持锁。"""
        with self._lock:
            return self._write_errors

    @property
    def last_error(self) -> str | None:
        """最后一次持久化失败的 ``Type: message``；无失败 ⇒ ``None``。"""
        with self._lock:
            return self._last_error

    def on_span_start(self, span: Span) -> None:
        """开始快照不落盘；不建库 / 目录 / 表。"""
        return None

    def on_span_end(self, span: Span) -> None:
        """仅 ``end_time`` 非空时写一条 ``kind="span"`` 行。"""
        if span.end_time is None:
            return None
        try:
            run_id = span.run_id
            self._validate_run_id(run_id)
            payload = span_to_dict(span)
        except Exception as exc:  # noqa: BLE001 - 写入失败必须被隔离
            self._report(exc)
            return
        self._persist(
            payload,
            run_id=run_id,
            thread_id=span.thread_id,
            node=span.node,
            checkpoint_id=span.checkpoint_id,
            span_id=span.id,
            start_time=span.start_time,
        )

    def on_trace_record(self, record: TraceRecord) -> None:
        """写一条 ``kind="trace_record"`` 行。"""
        try:
            run_id = record.run_id
            self._validate_run_id(run_id)
            payload = record_to_dict(record)
        except Exception as exc:  # noqa: BLE001 - 写入失败必须被隔离
            self._report(exc)
            return
        self._persist(
            payload,
            run_id=run_id,
            thread_id=record.thread_id,
            node=record.node,
            checkpoint_id=record.checkpoint_id,
            span_id=record.span_id,
            start_time=None,
        )

    def current_span(self) -> Span | None:
        """sink 不是 producer；恒返回 ``None``。"""
        return None

    def query(self, query: TraceQuery | None = None) -> list[dict[str, Any]]:
        """只读检索 SQLite trace；返回 B20F1 行视图的独立副本列表。"""
        normalized = normalize_query(query)
        start_ns = (
            parse_instant_ns(normalized.start_time)
            if normalized.start_time is not None
            else None
        )
        end_ns = (
            parse_instant_ns(normalized.end_time)
            if normalized.end_time is not None
            else None
        )
        if start_ns is not None and end_ns is not None and start_ns > end_ns:
            return []

        path = self._database
        if not path.exists():
            return []

        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(str(path), timeout=5.0)
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute("PRAGMA query_only=ON")
            info = connection.execute("PRAGMA table_info(trace_entries)").fetchall()
            if not info:
                return []
            columns = {
                row[1]: (row[2] or "").upper()
                for row in info
            }
            for name, expected in _REQUIRED_COLUMNS.items():
                actual = columns.get(name)
                if actual is None:
                    _LOGGER.warning(
                        "incompatible trace_entries schema: missing column %s", name
                    )
                    return []
                if actual and not actual.startswith(expected):
                    _LOGGER.warning(
                        "incompatible trace_entries schema: %s declared %s", name, actual
                    )
                    return []
            rows: list[dict[str, Any]] = []
            cursor = connection.execute("SELECT payload FROM trace_entries")
            for (payload_text,) in cursor:
                try:
                    raw = json.loads(payload_text)
                except (TypeError, ValueError) as exc:
                    _LOGGER.warning(
                        "skip malformed sqlite trace payload", exc_info=exc
                    )
                    continue
                row = normalize_row(raw)
                if row is None:
                    _LOGGER.warning("skip invalid sqlite trace row")
                    continue
                rows.append(row)
            return finalize(rows, normalized)
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:  # noqa: BLE001 - 关闭失败不掩盖原错误
                    pass

    @staticmethod
    def _validate_run_id(run_id: Any) -> None:
        """拒绝空 / 含点号 / 含路径分隔符的 ``run_id``。"""
        if not isinstance(run_id, str) or _RUN_ID_RE.fullmatch(run_id) is None:
            raise ValueError(f"unsafe run_id: {run_id!r}")

    def _persist(
        self,
        payload: dict[str, Any],
        *,
        run_id: str,
        thread_id: str | None,
        node: str,
        checkpoint_id: str | None,
        span_id: str,
        start_time: str | None,
    ) -> None:
        """序列化（锁外）后写一行（锁内）；任何失败不传播。"""
        try:
            text = json.dumps(payload, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001 - 序列化失败同样隔离
            self._report(exc)
            return
        path = self._database
        failure: Exception | None = None
        with self._lock:
            connection: sqlite3.Connection | None = None
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    descriptor = os.open(
                        path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
                    )
                    os.close(descriptor)
                connection = sqlite3.connect(str(path), timeout=5.0)
                connection.execute("PRAGMA busy_timeout=5000")
                connection.execute(_CREATE_TABLE)
                for statement in _CREATE_INDEXES:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO trace_entries "
                    "(kind, run_id, thread_id, node, checkpoint_id, span_id, start_time, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        payload["kind"],
                        run_id,
                        thread_id,
                        node,
                        checkpoint_id,
                        span_id,
                        start_time,
                        text,
                    ),
                )
                connection.commit()
            except Exception as exc:  # noqa: BLE001 - 写入失败必须被隔离
                failure = exc
                if connection is not None:
                    try:
                        connection.rollback()
                    except Exception:  # noqa: BLE001 - 清理失败不掩盖原错误
                        pass
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:  # noqa: BLE001 - 清理失败不掩盖原错误
                        pass
        if failure is not None:
            self._report(failure)

    def _report(self, exc: Exception) -> None:
        """更新四路诊断；``on_error`` 在锁外调用且防重入。"""
        message = f"{type(exc).__name__}: {exc}"
        with self._lock:
            self._write_errors += 1
            self._last_error = message
        _LOGGER.warning("sqlite trace write failed: %s", message, exc_info=exc)

        on_error = self._on_error
        if on_error is None or getattr(self._local, "in_on_error", False):
            return
        self._local.in_on_error = True
        try:
            on_error(exc)
        except Exception:  # noqa: BLE001 - 回调自身异常只记日志、不增加计数
            _LOGGER.warning("sqlite trace on_error failed", exc_info=True)
        finally:
            self._local.in_on_error = False
