# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · 上游差分场景组 D-501…D-508（上游缺席即 skip）。"""

from __future__ import annotations

import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypedDict

import pytest

pytest.importorskip("langgraph")

from freegraph.contracts import TraceQuery  # noqa: E402
from freegraph.graph import END, START, StateGraph  # noqa: E402
from freegraph.observability import FileTraceStore, SqliteTraceStore  # noqa: E402

from tests.observability.conftest import (  # noqa: E402
    assert_rows_equal,
    make_record,
    make_span,
    seed_events,
)

_PARITY = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "b20f2-trace-query-sqlite"
    / "contracts"
    / "upstream-parity.md"
)


class State(TypedDict, total=False):
    x: int


def _linear():
    builder = StateGraph(State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def _seed(store: object) -> None:
    span = make_span(id="s1", run_id="r1", node="a")
    record = make_record(span_id="s1", run_id="r1", node="a")
    seed_events(store, spans=(span,), records=(record,))  # type: ignore[arg-type]


def _jsonl(tmp_path: Path) -> FileTraceStore:
    store = FileTraceStore(tmp_path / "traces")
    _seed(store)
    return store


def _sqlite(tmp_path: Path) -> SqliteTraceStore:
    store = SqliteTraceStore(tmp_path / "traces.sqlite3")
    _seed(store)
    return store


def test_d501_local_query_returns_entries(tmp_path: Path) -> None:
    assert _jsonl(tmp_path).query() != []


def test_d502_zero_egress_for_queries(tmp_path: Path) -> None:
    calls: list[object] = []
    original_connect = socket.socket.connect
    original_create = socket.create_connection

    def connect(self, address):
        calls.append(address)
        return None

    def create_connection(address, *args, **kwargs):
        calls.append(address)
        return original_create(address, *args, **kwargs)

    socket.socket.connect = connect  # type: ignore[method-assign]
    socket.create_connection = create_connection  # type: ignore[assignment]
    try:
        _jsonl(tmp_path / "jsonl").query()
        _sqlite(tmp_path / "sqlite").query()
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.create_connection = original_create  # type: ignore[assignment]
    assert calls == []


def test_d503_empty_filter_returns_all_local_entries(tmp_path: Path) -> None:
    store = _jsonl(tmp_path)
    assert len(store.query()) == 2
    assert store.query() == store.query(TraceQuery())


def test_d504_four_filters_and_combination(tmp_path: Path) -> None:
    jsonl = _jsonl(tmp_path / "jsonl")
    sqlite = _sqlite(tmp_path / "sqlite")
    queries = (
        TraceQuery(run_id="r1"),
        TraceQuery(thread_id="t-1"),
        TraceQuery(node="a"),
        TraceQuery(start_time="2026-11-21T00:00:00Z"),
        TraceQuery(run_id="r1", thread_id="t-1", node="a"),
    )
    for query in queries:
        assert_rows_equal(jsonl.query(query), sqlite.query(query))


def test_d505_failure_isolation_does_not_change_graph_result(tmp_path: Path) -> None:
    occupied_dir = tmp_path / "occupied-dir"
    occupied_dir.write_text("occupied", encoding="utf-8")
    occupied_db = tmp_path / "occupied-db"
    occupied_db.write_text("occupied", encoding="utf-8")

    for store in (
        FileTraceStore(occupied_dir),
        SqliteTraceStore(occupied_db),
    ):
        result = _linear().compile(tracer=store).invoke({"x": 0})
        assert result["x"] == 2
        assert store.write_errors > 0


def test_d506_environment_variables_do_not_change_queries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _jsonl(tmp_path)
    before = store.query()
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("FREEGRAPH_TRACE_DIR", str(tmp_path / "elsewhere"))
    assert store.query() == before


def test_d507_dependency_closure_is_local() -> None:
    import sys

    assert "sqlite3" in sys.stdlib_module_names
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            Path(__file__).resolve().parents[2]
            / "src"
            / "freegraph"
            / "observability"
            / name
            for name in ("_payloads.py", "_query.py", "_sqlite_store.py")
        )
    )
    for forbidden in ("import langchain", "import langgraph", "import langsmith"):
        assert forbidden not in text


def test_d508_concurrent_write_and_query_do_not_corrupt(tmp_path: Path) -> None:
    database = tmp_path / "concurrent.sqlite3"
    store = SqliteTraceStore(database)

    def writer(index: int) -> None:
        store.on_span_end(make_span(id=f"s{index}", run_id="r1"))

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(writer, range(20)))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.query(), range(4)))
    assert all(len(rows) == 20 for rows in results)
    assert store.write_errors == 0


def test_contracts_cover_all_parity_ids_and_three_state_note() -> None:
    text = _PARITY.read_text(encoding="utf-8")
    for number in range(1, 8):
        assert f"P-0{number}" in text
    for number in range(501, 509):
        assert f"D-{number}" in text
    for number in range(1, 9):
        assert f"X-{number}" in text
    assert "不标 SAME 行为面" in text
