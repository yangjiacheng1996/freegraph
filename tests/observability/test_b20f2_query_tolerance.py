# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · 容错 / 只读边界：坏行 / 未知 kind / 字段残缺 / 非白名单 / 符号链接 /
SQLite 不兼容表 / 单行 payload 损坏 / 损坏库 / 重复行。"""

from __future__ import annotations

import json
import logging
import pathlib
import sqlite3
from pathlib import Path

import pytest

from freegraph.contracts import TraceQuery
from freegraph.observability import FileTraceStore, SqliteTraceStore
from freegraph.observability._payloads import record_to_dict, span_to_dict

from .conftest import make_record, make_span

T0 = "2026-11-21T12:00:00.000000000+00:00"


def _span_row(**overrides: object) -> dict[str, object]:
    values = {
        "id": "s1",
        "name": "a",
        "run_id": "r1",
        "node": "a",
        "thread_id": "t-1",
        "start_time": T0,
        "end_time": T0,
    }
    values.update(overrides)
    return span_to_dict(make_span(**values))  # type: ignore[arg-type]


def _record_row(**overrides: object) -> dict[str, object]:
    values = {
        "span_id": "s1",
        "run_id": "r1",
        "node": "a",
        "thread_id": "t-1",
        "superstep": 0,
    }
    values.update(overrides)
    return record_to_dict(make_record(**values))  # type: ignore[arg-type]


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_bad_and_truncated_jsonl_lines_are_skipped_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    target = tmp_path / "traces"
    target.mkdir()
    text = (
        json.dumps(_span_row()) + "\n"
        + "{not json}\n"
        + json.dumps([1, 2, 3]) + "\n"
        + '{"kind": "span", "id": "trunc"\n'
        + json.dumps(_span_row(id="s2")) + "\n"
    )
    (target / "trace-r1.jsonl").write_text(text, encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        rows = FileTraceStore(target).query()
    assert {row["id"] for row in rows} == {"s1", "s2"}
    assert any("malformed" in record.message or "invalid" in record.message for record in caplog.records)


def test_unknown_kind_and_missing_or_wrong_fields_are_skipped(
    tmp_path: Path,
) -> None:
    target = tmp_path / "traces"
    target.mkdir()
    missing = _span_row()
    del missing["name"]
    wrong = _span_row(id="wrong")
    wrong["attributes"] = "not-a-dict"
    bool_superstep = _record_row(span_id="bool-record", superstep=True)
    _write(
        target / "trace-r1.jsonl",
        [
            {"kind": "future", "x": 1},
            missing,  # type: ignore[list-item]
            wrong,  # type: ignore[list-item]
            bool_superstep,  # type: ignore[list-item]
            _span_row(),
        ],
    )
    rows = FileTraceStore(target).query()
    assert len(rows) == 1
    assert rows[0]["kind"] == "span" and rows[0]["id"] == "s1"


def test_extra_fields_are_dropped(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    target.mkdir()
    row = _span_row()
    row["extra"] = "drop"
    _write(target / "trace-r1.jsonl", [row])
    rows = FileTraceStore(target).query()
    assert rows and "extra" not in rows[0]


def test_non_allowlist_filename_is_skipped(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    target.mkdir()
    _write(target / "trace-a.b.jsonl", [_span_row()])
    assert FileTraceStore(target).query() == []


def test_symlink_candidate_is_not_followed(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    target.mkdir()
    outside = target / "data.jsonl"
    _write(outside, [_span_row()])
    try:
        (target / "trace-r1.jsonl").symlink_to(outside)
    except OSError as exc:  # Windows 无符号链接权限
        pytest.skip(f"symlink unsupported: {exc}")
    assert FileTraceStore(target).query() == []


def test_single_unreadable_file_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "traces"
    target.mkdir()
    good = target / "trace-good.jsonl"
    bad = target / "trace-bad.jsonl"
    _write(good, [_span_row(run_id="good")])
    _write(bad, [_span_row(run_id="bad")])
    original = pathlib.Path.open

    def fake_open(self: pathlib.Path, *args: object, **kwargs: object):
        if self == bad:
            raise PermissionError("denied")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "open", fake_open)
    rows = FileTraceStore(target).query()
    assert {row["run_id"] for row in rows} == {"good"}


def test_all_candidates_unreadable_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "traces"
    target.mkdir()
    one = target / "trace-one.jsonl"
    two = target / "trace-two.jsonl"
    _write(one, [_span_row(run_id="one")])
    _write(two, [_span_row(run_id="two")])
    original = pathlib.Path.open

    def fake_open(self: pathlib.Path, *args: object, **kwargs: object):
        if self in {one, two}:
            raise PermissionError("denied")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "open", fake_open)
    with pytest.raises(PermissionError):
        FileTraceStore(target).query()


def _create_table(path: Path, columns: str = "") -> None:
    connection = sqlite3.connect(str(path))
    try:
        if columns:
            connection.execute(f"CREATE TABLE trace_entries ({columns})")
        connection.commit()
    finally:
        connection.close()


def test_incompatible_sqlite_table_returns_empty_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    database = tmp_path / "incompatible.sqlite3"
    _create_table(database, "seq INTEGER PRIMARY KEY, kind TEXT, run_id TEXT")
    store = SqliteTraceStore(database)
    with caplog.at_level(logging.WARNING):
        assert store.query() == []
    assert any("incompatible" in record.message for record in caplog.records)


def test_sqlite_type_conflict_returns_empty(tmp_path: Path) -> None:
    database = tmp_path / "type-conflict.sqlite3"
    _create_table(
        database,
        "seq INTEGER PRIMARY KEY, kind TEXT, run_id TEXT, thread_id TEXT, "
        "node TEXT, checkpoint_id TEXT, span_id INTEGER, start_time TEXT, payload TEXT",
    )
    assert SqliteTraceStore(database).query() == []


def test_sqlite_single_row_payload_decode_failure_is_skipped(tmp_path: Path) -> None:
    database = tmp_path / "single-bad.sqlite3"
    store = SqliteTraceStore(database)
    store.on_span_end(make_span(id="good", run_id="r1", start_time=T0))
    connection = sqlite3.connect(str(database))
    try:
        connection.execute(
            "INSERT INTO trace_entries "
            "(kind, run_id, thread_id, node, checkpoint_id, span_id, start_time, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("span", "r1", "t-1", "a", None, "bad", T0, "{bad json"),
        )
        connection.commit()
    finally:
        connection.close()
    rows = store.query()
    assert [row.get("id") for row in rows] == ["good"]


def test_sqlite_corrupt_or_non_sqlite_raises(tmp_path: Path) -> None:
    database = tmp_path / "broken.sqlite3"
    database.write_text("not a sqlite database", encoding="utf-8")
    with pytest.raises(sqlite3.DatabaseError):
        SqliteTraceStore(database).query()


def test_duplicate_identical_rows_are_returned_twice(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    target.mkdir()
    row = _span_row()
    _write(target / "trace-r1.jsonl", [row, row])
    rows = FileTraceStore(target).query()
    assert len(rows) == 2
    assert rows[0] == rows[1]
