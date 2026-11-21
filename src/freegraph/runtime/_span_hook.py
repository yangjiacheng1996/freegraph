# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **私有 span 生产 hook** —— 属 **B18F1**（内部模块）。

本模块只做三件事：绑定 / 读取鸭子类型 tracer；在节点执行边界构造节点
:class:`~freegraph.contracts.trace.Span`；把开始 / 结束快照交给 tracer。
它 **MUST NOT** import ``freegraph.observability``（ARCH-1）；L5 的
``SpanProducer`` 结构化满足私有 :class:`_SpanTracer` 协议即可。

**关键边界**：

* ``__all__`` 恒空 ⇒ 不进 ``freegraph.runtime.__all__`` / API 兼容矩阵；
* tracer 为 ``None`` 时只做一次廉价读取；**不构造** Span、**不生成** id；
* ``run_id`` 缺失（``None`` / 空串）时 **MUST NOT** 构造 span（C23）；
* 开始 / 结束两个快照同 ``id``；结束快照是新实例，开始快照不被改写；
* 时间源只用标准库；UTC ISO-8601（9 位小数）且严格正耗时。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from freegraph.contracts.trace import Span

__all__: list[str] = []


class _SpanTracer(Protocol):
    """L2 所需的最小鸭子类型 tracer 面（L5 ``SpanProducer`` 结构化满足）。"""

    def on_span_start(self, span: Span) -> None: ...

    def on_span_end(self, span: Span) -> None: ...

    def current_span_id(self) -> str | None: ...


@dataclass(frozen=True, slots=True)
class TaskTraceMeta:
    """L2 私有纯数据：一个节点任务的 trace 元数据（B19F1）。"""

    node: str
    task_key: str
    superstep: int
    triggers: tuple[tuple[Any, ...], ...]
    concurrency_group: tuple[str, ...]
    barrier_groups: tuple[tuple[str, ...], ...]


def build_trace_payload(
    meta: TaskTraceMeta,
    start: Span,
    node_input: Any,
    output_state: Any,
    error: BaseException | None,
) -> dict[str, Any]:
    """构造 L2 → L5 的纯数据 payload（键名与 ``TraceRecord`` 逐字一致）。"""
    return {
        "span_id": start.id,
        "task_id": meta.task_key,
        "run_id": start.run_id,
        "thread_id": start.thread_id,
        "checkpoint_id": start.checkpoint_id,
        "node": meta.node,
        "superstep": meta.superstep,
        "triggers": meta.triggers,
        "concurrency_group": meta.concurrency_group,
        "barrier_groups": meta.barrier_groups,
        "input_state": node_input,
        "output_state": output_state,
        "error": error,
    }


_SPAN_TRACER: ContextVar[_SpanTracer | None] = ContextVar(
    "freegraph_span_tracer", default=None
)

_ISO_NS_RE = re.compile(
    r"^(?P<base>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(?P<frac>\d{9})\+00:00$"
)


@contextmanager
def bind_span_tracer(tracer: _SpanTracer | None) -> Iterator[None]:
    """在当前上下文中绑定 / 解绑 L2 节点 span 的 tracer。"""
    token = _SPAN_TRACER.set(tracer)
    try:
        yield
    finally:
        _SPAN_TRACER.reset(token)


def current_span_tracer() -> _SpanTracer | None:
    """返回当前绑定的 tracer（未绑定 ⇒ ``None``）。"""
    return _SPAN_TRACER.get()


def _iso_from_ns(ns: int) -> str:
    """把 Unix 纳秒转成 ``YYYY-MM-DDTHH:MM:SS.<9 digits>+00:00``。"""
    seconds, fraction = divmod(ns, 1_000_000_000)
    moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S") + f".{fraction:09d}+00:00"


def _ns_from_iso(text: str) -> int | None:
    """解析本模块产出的 ISO 纳秒字符串；无法解析 ⇒ ``None``。"""
    match = _ISO_NS_RE.match(text)
    if match is None:
        return None
    base = datetime.strptime(
        match.group("base"), "%Y-%m-%dT%H:%M:%S"
    ).replace(tzinfo=timezone.utc)
    return int(base.timestamp()) * 1_000_000_000 + int(match.group("frac"))


def _utc_now_iso_ns() -> tuple[str, int]:
    """返回 ``(iso_text, ns)``（标准库时钟 · UTC · 9 位小数）。"""
    ns = time.time_ns()
    return _iso_from_ns(ns), ns


def _end_iso_after(start_iso: str) -> tuple[str, int]:
    """返回严格大于 ``start_iso`` 的结束时刻（相等时 +1ns）。"""
    end_iso, end_ns = _utc_now_iso_ns()
    start_ns = _ns_from_iso(start_iso)
    if start_ns is not None and end_ns <= start_ns:
        end_ns = start_ns + 1
        end_iso = _iso_from_ns(end_ns)
    return end_iso, end_ns


def start_node_span(
    tracer: _SpanTracer,
    node: str,
    run_id: str | None,
    thread_id: str | None,
    checkpoint_id: str | None = None,
) -> Span | None:
    """构造并登记节点开始 span；``run_id`` 缺失 ⇒ 不构造（返回 ``None``）。"""
    if not run_id:
        return None
    start_time, _ = _utc_now_iso_ns()
    span = Span(
        id=uuid.uuid4().hex,
        name=node,
        attributes={},
        parent=tracer.current_span_id(),
        start_time=start_time,
        end_time=None,
        context={},
        thread_id=thread_id,
        run_id=run_id,
        node=node,
        checkpoint_id=checkpoint_id,
    )
    tracer.on_span_start(span)
    return span


def end_node_span(tracer: _SpanTracer, start_span: Span | None) -> Span | None:
    """构造并登记同 ``id`` 的节点结束 span；``start_span`` 为 ``None`` ⇒ 无操作。"""
    if start_span is None:
        return None
    end_time, _ = _end_iso_after(start_span.start_time)
    end_span = Span(
        id=start_span.id,
        name=start_span.name,
        attributes=start_span.attributes,
        parent=start_span.parent,
        start_time=start_span.start_time,
        end_time=end_time,
        context=start_span.context,
        thread_id=start_span.thread_id,
        run_id=start_span.run_id,
        node=start_span.node,
        checkpoint_id=start_span.checkpoint_id,
    )
    tracer.on_span_end(end_span)
    return end_span
