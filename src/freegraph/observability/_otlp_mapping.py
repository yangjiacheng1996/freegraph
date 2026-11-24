# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 · **Span → OTel SDK 数据对象**（B21F1 · 内部模块）。

只读 L1 ``Span`` 的 11 个字段，组装官方 ``ReadableSpan``；不解析任何
freegraph 私有格式 / 存储行 / ``TraceRecord``。身份使用稳定 SHA-256 截断，
时间复用同层 ``_time.parse_iso_ns``。**不写 protobuf / OTLP wire format**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import SpanContext, SpanKind, Status, StatusCode, TraceFlags

from freegraph.contracts.trace import Span

from ._time import parse_iso_ns

__all__ = [
    "MappingResult",
    "map_span",
    "span_id_for",
    "trace_id_for",
]

_LOG = logging.getLogger("freegraph.observability.otlp")


def _package_version() -> str | None:
    """取本发行版版本（无 dist-info 时返回 ``None``）；不读环境变量。"""
    try:
        from importlib.metadata import version

        return version("freegraph")
    except Exception:  # noqa: BLE001 - 未安装时不影响映射
        return None


_SCALAR_TYPES = (str, bool, int, float, bytes)
_RESOURCE = Resource({"service.name": "freegraph"})
_SCOPE = InstrumentationScope("freegraph", _package_version())
_TRACE_FLAGS = TraceFlags(TraceFlags.SAMPLED)


@dataclass(frozen=True, slots=True)
class MappingResult:
    """一次映射的结果：``readable`` 或跳过原因 / 不导出。"""

    readable: ReadableSpan | None = None
    skip_reason: str | None = None
    no_export: bool = False


def trace_id_for(run_id: str) -> int:
    """稳定 trace_id：``sha256("freegraph:run:" + run_id)[:16]``。"""
    digest = hashlib.sha256(b"freegraph:run:" + run_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:16], "big")


def span_id_for(span_id: str) -> int:
    """稳定 span_id：``sha256("freegraph:span:" + id)[:8]``。"""
    digest = hashlib.sha256(b"freegraph:span:" + span_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _normalize_value(value: Any) -> Any:
    """按锁定值归一规则转换单个属性值（绝不抛出到图执行路径）。"""
    if value is None:
        return "null"
    if isinstance(value, _SCALAR_TYPES):
        return value
    if isinstance(value, (list, tuple)):
        if not value:
            return value
        first_type = type(value[0])
        if first_type in _SCALAR_TYPES and all(type(item) is first_type for item in value):
            return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:  # noqa: BLE001 - 任何不可序列化值都退化为 str
        return str(value)


def _normalize_attributes(span: Span) -> dict[str, Any]:
    """逐键直映射 + 唯一的 ``gen_ai.conversation.id`` 派生。"""
    attributes: dict[str, Any] = {}
    for key, value in span.attributes.items():
        if not isinstance(key, str):
            _LOG.warning("OTLP mapping skipped non-str attribute key: %r", key)
            continue
        attributes[key] = _normalize_value(value)
    thread_id = span.thread_id
    if thread_id is not None:
        if isinstance(thread_id, str):
            if "gen_ai.conversation.id" not in attributes:
                attributes["gen_ai.conversation.id"] = thread_id
        else:
            _LOG.warning("OTLP mapping skipped non-str thread_id: %r", thread_id)
    return attributes


def _status_for(attributes: Mapping[str, Any]) -> Status:
    if "error.type" in attributes:
        return Status(StatusCode.ERROR, str(attributes["error.type"]))
    return Status(StatusCode.UNSET)


def _kind_for(attributes: Mapping[str, Any]) -> SpanKind:
    operation = attributes.get("gen_ai.operation.name")
    if operation in {"chat", "execute_tool"}:
        return SpanKind.CLIENT
    return SpanKind.INTERNAL


def map_span(span: Span) -> MappingResult:
    """把 L1 ``Span`` 映射为官方 ``ReadableSpan``。

    ``end_time is None`` ⇒ ``no_export``；空 ``id`` / ``run_id`` / 非法时间
    ⇒ ``skip_reason``（调用方记诊断，不抛到图执行路径）。
    """
    if span.end_time is None:
        return MappingResult(no_export=True)
    if not span.id:
        return MappingResult(skip_reason="empty span id")
    if not span.run_id:
        return MappingResult(skip_reason="empty run_id")
    start_ns = parse_iso_ns(span.start_time)
    if start_ns is None:
        return MappingResult(skip_reason="invalid start_time")
    end_ns = parse_iso_ns(span.end_time)
    if end_ns is None:
        return MappingResult(skip_reason="invalid end_time")
    if end_ns < start_ns:
        _LOG.warning("OTLP mapping clamped end_time < start_time for span %s", span.id)
        end_ns = start_ns

    trace_id = trace_id_for(span.run_id)
    span_id = span_id_for(span.id)
    parent_context = None
    if span.parent:
        parent_context = SpanContext(
            trace_id=trace_id,
            span_id=span_id_for(span.parent),
            is_remote=False,
            trace_flags=_TRACE_FLAGS,
        )
    context = SpanContext(
        trace_id=trace_id,
        span_id=span_id,
        is_remote=False,
        trace_flags=_TRACE_FLAGS,
    )
    attributes = _normalize_attributes(span)
    readable = ReadableSpan(
        name=span.name,
        context=context,
        parent=parent_context,
        resource=_RESOURCE,
        attributes=attributes,
        kind=_kind_for(attributes),
        status=_status_for(attributes),
        start_time=start_ns,
        end_time=end_ns,
        instrumentation_scope=_SCOPE,
    )
    return MappingResult(readable=readable)

