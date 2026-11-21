# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 · **本地 JSONL trace 存储后端** —— 属 **B20F1**（内部模块）。

``FileTraceStore`` 是 B19F1 sink 的**写入侧**实现：只把接收到的 ``Span`` 与
``TraceRecord`` 序列化为 ``trace-<run_id>.jsonl``，不产生 span、不读写当前 span
栈、不提供查询 API（查询归 B20F2）。

**关键边界**：

* 只用标准库 + L1 :class:`~freegraph.contracts.trace.Span` + 同层 ``TraceRecord``；
* 零出站、零环境变量、构造期零文件系统副作用；
* 每个 ``run_id`` 一个文件，惰性建目录，追加写入；
* 写入失败隔离 ``Exception``，通过 ``write_errors`` / ``last_error`` / 可选
  ``on_error`` / ``logging.WARNING`` 四路可感知，永不阻断图执行；
* 每行独立 ``open → append → flush → close``，不逐行 ``fsync``、不重试；
* 每个 store 实例一把锁；JSON 序列化在锁外，``on_error`` 在锁外调用。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from freegraph.contracts.trace import Span

from ._record import TraceRecord

__all__ = ["FileTraceStore"]

_LOGGER = logging.getLogger(__name__)

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def _span_to_dict(span: Span) -> dict[str, Any]:
    """把结束快照手工映射为 11 字段 dict（``kind`` 第一）。"""
    return {
        "kind": "span",
        "id": span.id,
        "name": span.name,
        "attributes": dict(span.attributes),
        "parent": span.parent,
        "start_time": span.start_time,
        "end_time": span.end_time,
        "context": dict(span.context),
        "thread_id": span.thread_id,
        "run_id": span.run_id,
        "node": span.node,
        "checkpoint_id": span.checkpoint_id,
    }


def _record_to_dict(record: TraceRecord) -> dict[str, Any]:
    """把 ``TraceRecord.to_jsonable()`` 原样包装为带 ``kind`` 的 dict。"""
    return {"kind": "trace_record", **record.to_jsonable()}


class FileTraceStore:
    """JSONL 文件后端的 sink 实现（L5 · 写入侧）。"""

    __slots__ = (
        "_directory",
        "_on_error",
        "_lock",
        "_local",
        "_write_errors",
        "_last_error",
    )

    def __init__(
        self,
        directory: str | os.PathLike[str],
        *,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> None:
        """只保存参数并初始化锁 / 诊断；**不访问文件系统**。"""
        self._directory = Path(directory)
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
        """开始快照不落盘（避免半成品 span）。"""
        return None

    def on_span_end(self, span: Span) -> None:
        """写一条 ``kind="span"`` 行；开始快照（``end_time`` 为空）不落盘。"""
        if span.end_time is None:
            return None
        try:
            run_id = span.run_id
            self._validate_run_id(run_id)
            payload = _span_to_dict(span)
        except Exception as exc:  # noqa: BLE001 - 写入失败必须被隔离
            self._report(exc)
            return
        self._write_event(run_id, payload)

    def on_trace_record(self, record: TraceRecord) -> None:
        """写一条 ``kind="trace_record"`` 行。"""
        try:
            run_id = record.run_id
            self._validate_run_id(run_id)
            payload = _record_to_dict(record)
        except Exception as exc:  # noqa: BLE001 - 写入失败必须被隔离
            self._report(exc)
            return
        self._write_event(run_id, payload)

    def current_span(self) -> Span | None:
        """sink 不是 producer；恒返回 ``None``。"""
        return None

    @staticmethod
    def _validate_run_id(run_id: Any) -> None:
        """拒绝空 / 含点号 / 含路径分隔符的 ``run_id``。"""
        if not isinstance(run_id, str) or _RUN_ID_RE.fullmatch(run_id) is None:
            raise ValueError(f"unsafe run_id: {run_id!r}")

    def _write_event(self, run_id: str, payload: dict[str, Any]) -> None:
        """序列化（锁外）后写一行（锁内）；任何失败不传播。"""
        try:
            path = self._directory / f"trace-{run_id}.jsonl"
            line = json.dumps(payload, ensure_ascii=False) + "\n"
        except Exception as exc:  # noqa: BLE001 - 序列化失败同样隔离
            self._report(exc)
            return
        self._write_line(path, line)

    def _write_line(self, path: Path, line: str) -> None:
        """锁内完成「记偏移 → 追加 → flush → close」；失败截断并诊断。"""
        failure: Exception | None = None
        with self._lock:
            before: int | None = None
            fd: int | None = None
            handle: Any = None
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    before = path.stat().st_size
                except FileNotFoundError:
                    before = 0
                fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
                handle = os.fdopen(fd, "a", encoding="utf-8", newline="\n")
                fd = None
                try:
                    handle.write(line)
                    handle.flush()
                finally:
                    handle.close()
            except Exception as exc:  # noqa: BLE001 - 写入失败必须被隔离
                failure = exc
                if fd is not None:
                    try:
                        os.close(fd)
                    except Exception:  # noqa: BLE001 - 清理失败不掩盖原错误
                        pass
                if handle is not None:
                    try:
                        handle.close()
                    except Exception:  # noqa: BLE001 - 清理失败不掩盖原错误
                        pass
                if before is not None:
                    try:
                        os.truncate(path, before)
                    except Exception:  # noqa: BLE001 - 截断失败只记诊断
                        _LOGGER.warning(
                            "trace truncate failed for %s", path, exc_info=True
                        )
        if failure is not None:
            self._report(failure)

    def _report(self, exc: Exception) -> None:
        """更新四路诊断；``on_error`` 在锁外调用且防重入。"""
        message = f"{type(exc).__name__}: {exc}"
        with self._lock:
            self._write_errors += 1
            self._last_error = message
        _LOGGER.warning("trace write failed: %s", message, exc_info=exc)

        on_error = self._on_error
        if on_error is None or getattr(self._local, "in_on_error", False):
            return
        self._local.in_on_error = True
        try:
            on_error(exc)
        except Exception:  # noqa: BLE001 - 回调自身异常只记日志、不增加计数
            _LOGGER.warning("trace on_error failed", exc_info=True)
        finally:
            self._local.in_on_error = False
