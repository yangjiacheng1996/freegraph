# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **流式运行期上下文** —— 属 **B8F2**（内部模块）。

本模块是 ``StreamWriter`` / ``custom`` 缓冲 / 中断轮 task 定格 / 运行标识的
**唯一运行期载体**（``contextvars``）。它是 L2 私有模块 ⇒ ``__all__`` 恒空
⇒ 不进 ``freegraph.runtime.__all__``。

**契约权威**：``specs/b8f2-stream-modes/contracts/stream-contract.md``
（§2 事件信封 · §3.5 ``custom`` · §4 生命周期 · §5 ``StreamWriter``）。

**设计要点**（逐条附来源）：

* **单一载体**（原则 XII）—— writer / sink / round capture / 当前 TaskId /
  ``run_id`` / ``thread_id`` 全部走 ``contextvars``；**MUST NOT** 另立显式传参
  的第二套载体（契约 §5）；
* **跨线程可见性** 由执行器的每任务 ``copy_context()`` 提供（上游
  ``langgraph/pregel/_executor.py:64`` / ``:71``）⇒ 本模块只负责把当前值放进
  上下文，不负责线程传播；
* **``custom`` 轮末批量** —— 写入先进入 :class:`_CustomSink`（线程安全），
  每轮结束后按 **TaskId 升序 + 任务内写入序** 取出（P-23 / X-6）；
* **无流 no-op** —— ``get_stream_writer()`` 在未绑定流时返回模块级 no-op
  （上游 ``langgraph/config.py:13-14``）；MUST NOT 抛异常；
* **运行标识** —— ``_STREAM_RUN_ID`` / ``_STREAM_THREAD_ID`` 由
  :class:`~freegraph.runtime._stream.StreamSession` 绑定；B18F1 / B19F1
  的 span MUST 读取同一对值（D-3 / H-9 · ARCH-3 已登记例外 R-6）；
* **invoke 路径 id 绑定** —— B18F1 的私有助手 :func:`bind_run_ids` 只设置
  ``_STREAM_RUN_ID`` / ``_STREAM_THREAD_ID``；``bind_stream`` 仍是
  ``StreamSession`` 的唯一绑定入口。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from freegraph.contracts.types import PregelTask, StreamWriter

__all__: list[str] = []


@dataclass
class _CustomSink:
    """**本轮** custom 写入的线程安全缓冲（私有 · 轮末清空）。

    键 = 本轮整数 TaskId；值 = 该任务的写入序列（按调用顺序）。
    """

    _values: dict[int, list[Any]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, task_id: int, value: Any) -> None:
        """记录一次写入（线程安全）。"""
        with self._lock:
            self._values.setdefault(task_id, []).append(value)

    def take(self) -> list[Any]:
        """取出并清空本轮写入（TaskId 升序 + 任务内写入序）。"""
        with self._lock:
            ordered = [
                value
                for task_id in sorted(self._values)
                for value in self._values[task_id]
            ]
            self._values.clear()
            return ordered


@dataclass
class _RoundCapture:
    """**中断轮**的 task 定格（私有 · 只在本轮使用）。"""

    tasks: tuple[PregelTask, ...] = ()


_STREAM_WRITER: ContextVar[StreamWriter | None] = ContextVar(
    "freegraph_stream_writer", default=None
)
_CUSTOM_SINK: ContextVar[_CustomSink | None] = ContextVar(
    "freegraph_stream_custom_sink", default=None
)
_CURRENT_TASK: ContextVar[int | None] = ContextVar(
    "freegraph_stream_current_task", default=None
)
_ROUND_CAPTURE: ContextVar[_RoundCapture | None] = ContextVar(
    "freegraph_stream_round_capture", default=None
)
_STREAM_RUN_ID: ContextVar[str | None] = ContextVar(
    "freegraph_stream_run_id", default=None
)
_STREAM_THREAD_ID: ContextVar[str | None] = ContextVar(
    "freegraph_stream_thread_id", default=None
)


def _no_op_stream_writer(value: Any) -> None:
    """无流时的 no-op writer（上游同款）。"""


def _bound_writer(value: Any) -> None:
    """把一次写入放进当前 sink（按当前 TaskId 分组）。"""
    sink = _CUSTOM_SINK.get()
    task_id = _CURRENT_TASK.get()
    if sink is None or task_id is None:
        return
    sink.add(task_id, value)


def get_stream_writer() -> StreamWriter:
    """返回**当前**的流写入器；无流时返回 **no-op**（不抛异常）。"""
    writer = _STREAM_WRITER.get()
    if writer is None:
        return _no_op_stream_writer
    return writer


def current_stream_ids() -> tuple[str | None, str | None]:
    """返回当前绑定的 ``(run_id, thread_id)``（供 B18F1 / B19F1 读取）。"""
    return _STREAM_RUN_ID.get(), _STREAM_THREAD_ID.get()


@contextmanager
def bind_run_ids(run_id: str, thread_id: str | None) -> Iterator[None]:
    """只绑定 ``_STREAM_RUN_ID`` / ``_STREAM_THREAD_ID``（B18F1 invoke 路径私有助手）。

    * MUST NOT 触碰 writer / custom sink / round capture；
    * ``bind_stream`` 仍是 :class:`~freegraph.runtime._stream.StreamSession`
      的唯一绑定入口；
    * **不新增第二套载体**：与 stream 路径使用同一对 contextvar。
    """
    run_token = _STREAM_RUN_ID.set(run_id)
    thread_token = _STREAM_THREAD_ID.set(thread_id)
    try:
        yield
    finally:
        _STREAM_THREAD_ID.reset(thread_token)
        _STREAM_RUN_ID.reset(run_token)


@contextmanager
def bind_stream(
    run_id: str,
    thread_id: str | None,
    *,
    sink: _CustomSink | None = None,
    capture: _RoundCapture | None = None,
) -> Iterator[tuple[_CustomSink, _RoundCapture]]:
    """绑定一次流的全部运行期上下文（``StreamSession`` 的唯一绑定入口）。

    返回 ``(sink, capture)``，供会话在轮末取 custom / 中断轮取 task 定格。
    """
    actual_sink = sink if sink is not None else _CustomSink()
    actual_capture = capture if capture is not None else _RoundCapture()
    tokens = [
        _STREAM_WRITER.set(_bound_writer),
        _CUSTOM_SINK.set(actual_sink),
        _ROUND_CAPTURE.set(actual_capture),
        _STREAM_RUN_ID.set(run_id),
        _STREAM_THREAD_ID.set(thread_id),
    ]
    try:
        yield actual_sink, actual_capture
    finally:
        for var, token in reversed(
            list(
                zip(
                    (
                        _STREAM_WRITER,
                        _CUSTOM_SINK,
                        _ROUND_CAPTURE,
                        _STREAM_RUN_ID,
                        _STREAM_THREAD_ID,
                    ),
                    tokens,
                )
            )
        ):
            var.reset(token)


@contextmanager
def bind_current_task(task_id: int) -> Iterator[None]:
    """在当前任务执行期间绑定整数 TaskId（供 custom 排序）。"""
    token = _CURRENT_TASK.set(task_id)
    try:
        yield
    finally:
        _CURRENT_TASK.reset(token)


def record_round_tasks(tasks: tuple[PregelTask, ...]) -> None:
    """记录中断轮的任务定格（无流时为 no-op）。"""
    capture = _ROUND_CAPTURE.get()
    if capture is not None:
        capture.tasks = tasks


def take_round_tasks() -> tuple[PregelTask, ...]:
    """取出并清空中断轮的任务定格。"""
    capture = _ROUND_CAPTURE.get()
    if capture is None:
        return ()
    tasks = capture.tasks
    capture.tasks = ()
    return tasks


def take_custom() -> list[Any]:
    """取出并清空当前轮的 custom 写入（无流时返回空列表）。"""
    sink = _CUSTOM_SINK.get()
    if sink is None:
        return []
    return sink.take()
