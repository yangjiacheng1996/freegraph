# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · Phase 7：per-instance 锁 / 并发完整性 / on_error 重入。"""

from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from freegraph.observability import FileTraceStore

from .conftest import make_span, read_jsonl


def test_same_instance_serializes_concurrent_lines(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    spans = [make_span(run_id="concurrent-run", id=uuid.uuid4().hex) for _ in range(40)]

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(store.on_span_end, spans))

    path = next(target.glob("trace-*.jsonl"))
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 40
    objs = [json.loads(line) for line in lines]
    assert {obj["id"] for obj in objs} == {span.id for span in spans}
    assert store.write_errors == 0


def test_different_instances_have_distinct_locks(tmp_path: Path) -> None:
    first = FileTraceStore(tmp_path / "first")
    second = FileTraceStore(tmp_path / "second")
    assert first._lock is not second._lock
    first.on_span_end(make_span(run_id="run-first"))
    second.on_span_end(make_span(run_id="run-second"))
    assert len(list((tmp_path / "first").glob("trace-*.jsonl"))) == 1
    assert len(list((tmp_path / "second").glob("trace-*.jsonl"))) == 1


def test_on_error_can_reenter_without_deadlock_or_recursion(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("occupied", encoding="utf-8")
    good = tmp_path / "good"
    holder: dict[str, FileTraceStore] = {}
    calls: list[BaseException] = []

    def on_error(exc: BaseException) -> None:
        calls.append(exc)
        store = holder["store"]
        store._directory = good
        store.on_span_end(make_span(node="reentrant"))

    store = FileTraceStore(blocked, on_error=on_error)
    holder["store"] = store
    store.on_span_end(make_span(node="first"))

    assert len(calls) == 1
    assert store.write_errors == 1
    objs = read_jsonl(next(good.glob("trace-*.jsonl")))
    assert [obj["node"] for obj in objs] == ["reentrant"]
