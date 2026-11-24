# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B21F1 · US1：``Span`` → OTel SDK 数据对象的 11 字段映射。"""

from __future__ import annotations

import logging

import pytest
from opentelemetry.trace import SpanKind, StatusCode, TraceFlags

from freegraph.observability._otlp_mapping import (
    map_span,
    span_id_for,
    trace_id_for,
)
from freegraph.observability._time import parse_iso_ns

from .conftest import make_model_span, make_span, make_tool_span

START = "2026-11-24T12:00:00.123456789+00:00"
END = "2026-11-24T12:00:01.987654321+00:00"


def test_identity_is_stable_and_groups_by_run_id() -> None:
    a = make_span(id="a1", run_id="run-A")
    b = make_span(id="b1", run_id="run-A")
    c = make_span(id="c1", run_id="run-B")
    ra = map_span(a).readable
    rb = map_span(b).readable
    rc = map_span(c).readable
    assert ra is not None and rb is not None and rc is not None
    assert ra.context.trace_id == rb.context.trace_id == trace_id_for("run-A")
    assert rc.context.trace_id == trace_id_for("run-B")
    assert ra.context.span_id == span_id_for("a1")
    assert rb.context.span_id == span_id_for("b1")


def test_span_kind_for_node_model_and_tool() -> None:
    assert map_span(make_span()).readable.kind == SpanKind.INTERNAL
    assert map_span(make_model_span()).readable.kind == SpanKind.CLIENT
    assert map_span(make_tool_span()).readable.kind == SpanKind.CLIENT
    other = make_span(attributes={"gen_ai.operation.name": "embed"})
    assert map_span(other).readable.kind == SpanKind.INTERNAL


def test_error_type_sets_error_status_and_is_preserved() -> None:
    readable = map_span(
        make_model_span(attributes={
            "gen_ai.operation.name": "chat",
            "error.type": "RuntimeError",
        })
    ).readable
    assert readable is not None
    assert readable.attributes["error.type"] == "RuntimeError"
    assert readable.status.status_code == StatusCode.ERROR
    assert readable.status.description == "RuntimeError"


def test_no_error_type_is_unset_status() -> None:
    readable = map_span(make_span()).readable
    assert readable is not None
    assert readable.status.status_code == StatusCode.UNSET


def test_thread_id_derives_conversation_id_without_overwriting() -> None:
    derived = map_span(make_span(thread_id="t-1")).readable
    assert derived is not None
    assert derived.attributes["gen_ai.conversation.id"] == "t-1"

    existing = map_span(
        make_span(
            thread_id="t-new",
            attributes={"gen_ai.conversation.id": "original"},
        )
    ).readable
    assert existing is not None
    assert existing.attributes["gen_ai.conversation.id"] == "original"


def test_non_str_thread_id_is_not_derived(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        readable = map_span(make_span(thread_id=123)).readable  # type: ignore[arg-type]
    assert readable is not None
    assert "gen_ai.conversation.id" not in readable.attributes
    assert any("non-str thread_id" in record.message for record in caplog.records)


def test_context_checkpoint_id_and_node_are_not_exported() -> None:
    readable = map_span(
        make_span(
            node="node-a",
            checkpoint_id="cp-1",
            context={"local": "context"},
            attributes={"gen_ai.operation.name": "chat"},
        )
    ).readable
    assert readable is not None
    keys = set(readable.attributes)
    assert "context" not in keys
    assert "checkpoint_id" not in keys
    assert "node" not in keys
    assert "local" not in keys
    assert not any(key.startswith("freegraph.") for key in keys)


def test_parent_maps_to_parent_span_id_and_empty_parent_is_root() -> None:
    child = map_span(make_span(id="child", parent="parent-id")).readable
    assert child is not None
    assert child.parent is not None
    assert child.parent.span_id == span_id_for("parent-id")

    for parent in (None, ""):
        root = map_span(make_span(parent=parent)).readable
        assert root is not None
        assert root.parent is None


def test_invalid_id_run_id_and_time_are_skipped() -> None:
    assert map_span(make_span(id="")).skip_reason == "empty span id"
    assert map_span(make_span(run_id="")).skip_reason == "empty run_id"
    assert map_span(make_span(start_time="bad")).skip_reason == "invalid start_time"
    assert map_span(make_span(end_time="bad")).skip_reason == "invalid end_time"


def test_none_end_time_is_no_export() -> None:
    result = map_span(make_span(end_time=None))
    assert result.no_export is True
    assert result.readable is None


def test_end_before_start_is_clamped_to_start(caplog: pytest.LogCaptureFixture) -> None:
    start = "2026-11-24T12:00:01.000000000+00:00"
    end = "2026-11-24T12:00:00.000000000+00:00"
    with caplog.at_level(logging.WARNING):
        readable = map_span(make_span(start_time=start, end_time=end)).readable
    assert readable is not None
    assert readable.start_time == parse_iso_ns(start)
    assert readable.end_time == parse_iso_ns(start)
    assert any("clamped end_time" in record.message for record in caplog.records)


def test_attribute_value_normalization() -> None:
    readable = map_span(
        make_span(
            attributes={
                "scalar": "x",
                "bool": True,
                "int": 3,
                "float": 1.5,
                "bytes": b"raw",
                "seq": [1, 2],
                "empty_seq": [],
                "nested": {"b": 2, "a": 1},
                "mixed": [1, "x"],
                "none": None,
                "non_ascii": "中文\nline",
                1: "non-str-key",
            }
        )
    ).readable
    assert readable is not None
    attrs = readable.attributes
    assert attrs["scalar"] == "x"
    assert attrs["bool"] is True
    assert attrs["int"] == 3
    assert attrs["float"] == 1.5
    assert attrs["bytes"] == b"raw"
    assert attrs["seq"] == [1, 2]
    assert attrs["empty_seq"] == []
    assert attrs["nested"] == '{"a": 1, "b": 2}'
    assert attrs["mixed"] == '[1, "x"]'
    assert attrs["none"] == "null"
    assert attrs["non_ascii"] == "中文\nline"
    assert 1 not in attrs


def test_duplicate_id_is_not_deduped() -> None:
    span = make_span(id="same", run_id="run-same")
    first = map_span(span).readable
    second = map_span(span).readable
    assert first is not None and second is not None
    assert first.context.span_id == second.context.span_id
    assert first.context.trace_id == second.context.trace_id


def test_resource_scope_and_trace_flags() -> None:
    readable = map_span(make_span()).readable
    assert readable is not None
    assert readable.resource.attributes["service.name"] == "freegraph"
    assert readable.instrumentation_scope is not None
    assert readable.instrumentation_scope.name == "freegraph"
    assert readable.instrumentation_scope.version
    assert readable.context.trace_flags & TraceFlags.SAMPLED
    assert readable.context.is_remote is False


def test_nanosecond_precision_is_preserved() -> None:
    readable = map_span(make_span(start_time=START, end_time=END)).readable
    assert readable is not None
    assert readable.start_time == parse_iso_ns(START)
    assert readable.end_time == parse_iso_ns(END)
    assert readable.start_time % 1_000 == 789
    assert readable.end_time % 1_000 == 321
