# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · US2：时间窗闭区间 / 纳秒 / 时区 / 倒置 / 有效起始时刻。"""

from __future__ import annotations

from pathlib import Path

import pytest

from freegraph.contracts import TraceQuery
from freegraph.observability import FileTraceStore

from .conftest import make_record, make_span, query_by_kind

T0 = "2026-11-21T12:00:00.000000000+00:00"
T1 = "2026-11-21T12:00:01.000000000+00:00"
T2 = "2026-11-21T12:00:02.000000000+00:00"


def _store(tmp_path: Path) -> FileTraceStore:
    return FileTraceStore(tmp_path / "traces")


def test_closed_interval_and_boundaries(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for index, moment in enumerate((T0, T1, T2)):
        store.on_span_end(make_span(id=f"s{index}", run_id="r1", start_time=moment))
    assert [row["id"] for row in store.query(TraceQuery(start_time=T1, end_time=T1))] == ["s1"]
    assert {row["id"] for row in store.query(TraceQuery(start_time=T1, end_time=T2))} == {
        "s1",
        "s2",
    }


def test_one_sided_bounds(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for index, moment in enumerate((T0, T1, T2)):
        store.on_span_end(make_span(id=f"s{index}", run_id="r1", start_time=moment))
    assert {row["id"] for row in store.query(TraceQuery(start_time=T1))} == {"s1", "s2"}
    assert {row["id"] for row in store.query(TraceQuery(end_time=T1))} == {"s0", "s1"}


def test_inverted_range_is_empty(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.on_span_end(make_span(run_id="r1", start_time=T1))
    assert store.query(TraceQuery(start_time=T2, end_time=T1)) == []


def test_z_offset_and_naive_utc_are_equivalent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.on_span_end(
        make_span(id="offset", run_id="r1", start_time="2026-11-21T20:00:00+08:00")
    )
    store.on_span_end(
        make_span(id="compact", run_id="r2", start_time="2026-11-21T12:00:00+0000")
    )
    store.on_span_end(
        make_span(id="naive", run_id="r3", start_time="2026-11-21T12:00:00")
    )
    store.on_span_end(make_span(id="zulu", run_id="r4", start_time="2026-11-21T12:00:00Z"))
    rows = store.query(
        TraceQuery(start_time="2026-11-21T12:00:00Z", end_time="2026-11-21T12:00:00Z")
    )
    assert {row["id"] for row in rows} == {"offset", "compact", "naive", "zulu"}


def test_nanosecond_precision_is_not_truncated_to_microseconds(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.on_span_end(
        make_span(id="one", run_id="r1", start_time="2026-11-21T12:00:00.000000001+00:00")
    )
    store.on_span_end(
        make_span(id="two", run_id="r1", start_time="2026-11-21T12:00:00.000000002+00:00")
    )
    rows = store.query(
        TraceQuery(
            start_time="2026-11-21T12:00:00.000000001+00:00",
            end_time="2026-11-21T12:00:00.000000001+00:00",
        )
    )
    assert [row["id"] for row in rows] == ["one"]


def test_invalid_time_string_raises_value_error(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.query(TraceQuery(start_time="not-a-time"))
    with pytest.raises(ValueError):
        store.query(TraceQuery(end_time="2026-13-40T99:99:99Z"))


def test_record_effective_time_uses_linked_span(tmp_path: Path) -> None:
    store = _store(tmp_path)
    span = make_span(id="linked", run_id="r1", start_time=T1)
    record = make_record(span_id="linked", run_id="r1")
    store.on_trace_record(record)
    store.on_span_end(span)
    rows = store.query(TraceQuery(start_time=T1, end_time=T1))
    assert {row["kind"] for row in rows} == {"span", "trace_record"}
    assert store.query(TraceQuery(start_time=T2)) == []


def test_record_without_linked_span_is_excluded_by_time_bounds(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.on_trace_record(make_record(span_id="missing", run_id="r1"))
    assert len(store.query()) == 1
    assert store.query(TraceQuery(start_time=T0)) == []


def test_record_is_not_linked_across_runs(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.on_span_end(make_span(id="shared", run_id="run-A", start_time=T1))
    store.on_trace_record(make_record(span_id="shared", run_id="run-B"))
    rows = store.query(TraceQuery(run_id="run-B", start_time=T1, end_time=T1))
    assert query_by_kind(rows, "trace_record") == []
