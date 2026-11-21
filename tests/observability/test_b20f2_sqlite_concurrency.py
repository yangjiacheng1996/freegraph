# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · SQLite 并发写 + 查询 / 跨进程 / Windows 分支。"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from freegraph.observability import SqliteTraceStore

from .conftest import make_span

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"


def test_threaded_write_and_query_do_not_corrupt(tmp_path: Path) -> None:
    database = tmp_path / "threaded.sqlite3"
    store = SqliteTraceStore(database)

    def writer(index: int) -> None:
        store.on_span_end(make_span(id=f"s{index}", run_id="r1"))

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(writer, range(100)))

    def reader(_: int) -> list[dict[str, object]]:
        return store.query()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(reader, range(8)))

    assert all(len(rows) == 100 for rows in results)
    assert store.write_errors == 0
    assert all(row["kind"] == "span" for row in results[0])


def test_two_instances_have_distinct_locks_and_both_write(tmp_path: Path) -> None:
    first = SqliteTraceStore(tmp_path / "first.sqlite3")
    second = SqliteTraceStore(tmp_path / "second.sqlite3")
    assert first._lock is not second._lock  # noqa: SLF001

    def write(store: SqliteTraceStore, label: str) -> None:
        for index in range(10):
            store.on_span_end(make_span(id=f"{label}{index}", run_id=label))

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda pair: write(*pair), ((first, "a"), (second, "b"))))
    assert len(first.query()) == 10
    assert len(second.query()) == 10


def test_cross_process_writer_and_parent_queries(tmp_path: Path) -> None:
    database = tmp_path / "cross-process.sqlite3"
    code = """
import time
import uuid
from freegraph.contracts import Span
from freegraph.observability import SqliteTraceStore

store = SqliteTraceStore(r'''%s''')
for index in range(40):
    span_id = uuid.uuid4().hex
    store.on_span_end(Span(
        id=span_id,
        name="a",
        start_time="2026-11-21T12:00:00.000000000+00:00",
        end_time="2026-11-21T12:00:00.000120000+00:00",
        run_id="r1",
        node="a",
    ))
    time.sleep(0.001)
""" % database
    env = {**os.environ, "PYTHONPATH": str(_SRC), "PYTHONUTF8": "1"}
    process = subprocess.Popen(
        [sys.executable, "-c", code],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    store = SqliteTraceStore(database)
    try:
        deadline = time.monotonic() + 30
        while process.poll() is None and time.monotonic() < deadline:
            rows = store.query()
            assert isinstance(rows, list)
            time.sleep(0.005)
    finally:
        stdout, stderr = process.communicate(timeout=30)
    assert process.returncode == 0, stdout + stderr
    rows = store.query()
    assert len(rows) == 40
    assert store.write_errors == 0


@pytest.mark.skipif(os.name != "nt", reason="Windows 文件锁分支")
def test_windows_branch_placeholder() -> None:
    """Windows CI 由真实并发用例覆盖；此处仅保留显式分支标记。"""
    assert os.name == "nt"
