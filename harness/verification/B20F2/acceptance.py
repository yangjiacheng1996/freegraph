#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · 一键验收脚本（Trace 查询 API + SQLite 后端）。

一条命令跑完本 feature 的机械验收：

    .venv/bin/python harness/verification/B20F2/acceptance.py

覆盖 A1–A6：
- A1 按 run 检索；A2 按 thread 检索；A3 时间窗；A4 节点名；
- A5 四类过滤组合；A6 JSONL / SQLite 两后端逐条等价；
- 额外：零出站、结果可 JSON 序列化。

只依赖标准库 + ``freegraph``；退出码 ``0`` = PASS · ``1`` = FAIL ·
``2`` = 环境未就绪。最后一行 MUST 打印 ``B20F2 acceptance: PASS|FAIL``。
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

try:
    from freegraph.contracts import Span, TraceQuery
    from freegraph.observability import FileTraceStore, SqliteTraceStore, TraceRecord
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"B20F2 acceptance: FAIL (environment: {exc})")
    raise SystemExit(2) from exc

_FAILURES: list[str] = []
_CHECKS = 0

T0 = "2026-11-21T12:00:00.000000000+00:00"
T1 = "2026-11-21T12:00:01.000000000+00:00"
T2 = "2026-11-21T12:00:02.000000000+00:00"


def check(condition: Any, label: str) -> bool:
    global _CHECKS
    _CHECKS += 1
    if condition:
        print(f"[PASS] {label}")
        return True
    print(f"[FAIL] {label}")
    _FAILURES.append(label)
    return False


def run(name: str, fn: Any) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - 单组失败不中断其余检查
        print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
        _FAILURES.append(name)


def _span(
    *,
    node: str,
    run_id: str,
    thread_id: str = "t-1",
    span_id: str | None = None,
    name: str | None = None,
    start_time: str = T0,
) -> Span:
    return Span(
        id=span_id or uuid.uuid4().hex,
        name=name or node,
        start_time=start_time,
        end_time="2026-11-21T12:00:09.000000000+00:00",
        thread_id=thread_id,
        run_id=run_id,
        node=node,
    )


def _record(*, span_id: str, node: str, run_id: str, thread_id: str = "t-1", superstep: int = 0) -> TraceRecord:
    return TraceRecord(
        span_id=span_id,
        task_id=node,
        run_id=run_id,
        thread_id=thread_id,
        checkpoint_id=None,
        node=node,
        superstep=superstep,
        triggers=(),
        concurrency_group=(),
        barrier_groups=(),
        input_state={},
        output_state={},
        error=None,
    )


def _seed(store: Any, spans: tuple[Span, ...], records: tuple[TraceRecord, ...]) -> None:
    span_ids = {span.id for span in spans}
    for record in records:
        if record.span_id in span_ids:
            store.on_trace_record(record)
    for record in records:
        if record.span_id not in span_ids:
            store.on_trace_record(record)
    for span in spans:
        store.on_span_end(span)


def _fixture() -> tuple[tuple[Span, ...], tuple[TraceRecord, ...]]:
    a = _span(node="a", run_id="run-A", thread_id="t-1", span_id="a1", start_time=T0)
    a_model = _span(
        node="a", run_id="run-A", thread_id="t-1", span_id="am", name="chat", start_time=T1
    )
    b = _span(node="b", run_id="run-B", thread_id="t-2", span_id="b1", start_time=T2)
    records = (
        _record(span_id="a1", node="a", run_id="run-A", thread_id="t-1"),
        _record(span_id="am", node="a", run_id="run-A", thread_id="t-1", superstep=1),
        _record(span_id="b1", node="b", run_id="run-B", thread_id="t-2"),
    )
    return (a, a_model, b), records


def _stores(tmp_path: Path) -> tuple[FileTraceStore, SqliteTraceStore]:
    jsonl = FileTraceStore(tmp_path / "traces")
    sqlite = SqliteTraceStore(tmp_path / "traces.sqlite3")
    spans, records = _fixture()
    _seed(jsonl, spans, records)
    _seed(sqlite, spans, records)
    return jsonl, sqlite


def _a1(tmp_path: Path) -> None:
    jsonl, sqlite = _stores(tmp_path)
    for store in (jsonl, sqlite):
        rows = store.query(TraceQuery(run_id="run-A"))
        check(rows and all(row["run_id"] == "run-A" for row in rows), "A1 按 run 检索")
        check(len(rows) == 4, "A1 run-A 全部条目（2 span + 2 record）")


def _a2(tmp_path: Path) -> None:
    jsonl, sqlite = _stores(tmp_path)
    for store in (jsonl, sqlite):
        rows = store.query(TraceQuery(thread_id="t-2"))
        check(rows and all(row["thread_id"] == "t-2" for row in rows), "A2 按 thread 检索")


def _a3(tmp_path: Path) -> None:
    jsonl, sqlite = _stores(tmp_path)
    for store in (jsonl, sqlite):
        rows = store.query(TraceQuery(start_time=T1, end_time=T1))
        check(bool(rows), "A3 时间窗命中")
        check(all(row.get("id") == "am" or row.get("span_id") == "am" for row in rows), "A3 时间窗只返回 T1")
        check(store.query(TraceQuery(start_time=T2, end_time=T1)) == [], "A3 倒置时间为空")


def _a4(tmp_path: Path) -> None:
    jsonl, sqlite = _stores(tmp_path)
    for store in (jsonl, sqlite):
        rows = store.query(TraceQuery(node="a"))
        check(rows and all(row["node"] == "a" for row in rows), "A4 按节点名检索")
        check(any(row.get("id") == "am" for row in rows), "A4 含节点内模型 span")
        check(not any(row.get("id") == "b1" for row in rows), "A4 排除其它节点")


def _a5(tmp_path: Path) -> None:
    jsonl, sqlite = _stores(tmp_path)
    query = TraceQuery(run_id="run-A", thread_id="t-1", node="a", start_time=T1)
    for store in (jsonl, sqlite):
        rows = store.query(query)
        check(bool(rows), "A5 四类过滤组合命中")
        check(
            all(
                row["run_id"] == "run-A"
                and row["thread_id"] == "t-1"
                and row["node"] == "a"
                for row in rows
            ),
            "A5 组合条件 AND",
        )


def _a6(tmp_path: Path) -> None:
    jsonl, sqlite = _stores(tmp_path)
    for query in (
        TraceQuery(),
        TraceQuery(run_id="run-A"),
        TraceQuery(thread_id="t-1"),
        TraceQuery(node="a"),
        TraceQuery(start_time=T0, end_time=T2),
        TraceQuery(run_id="run-A", node="a"),
    ):
        left = jsonl.query(query)
        right = sqlite.query(query)
        check(left == right, f"A6 两后端等价 {query}")
        check(json.loads(json.dumps(left)) == left, "A6 JSON 可序列化")


@contextmanager
def _egress_monitor():
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
        yield calls
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.create_connection = original_create  # type: ignore[assignment]


def _zero_egress(tmp_path: Path) -> None:
    with _egress_monitor() as calls:
        jsonl, sqlite = _stores(tmp_path)
        jsonl.query()
        sqlite.query()
    check(calls == [], "零出站：查询无网络调用")


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        run("A1 按 run", lambda: _a1(root / "a1"))
        run("A2 按 thread", lambda: _a2(root / "a2"))
        run("A3 时间窗", lambda: _a3(root / "a3"))
        run("A4 节点名", lambda: _a4(root / "a4"))
        run("A5 组合", lambda: _a5(root / "a5"))
        run("A6 两后端", lambda: _a6(root / "a6"))
        run("零出站", lambda: _zero_egress(root / "egress"))

    if _FAILURES:
        print(f"B20F2 acceptance: FAIL（{len(_FAILURES)} 项失败 / {_CHECKS} 项检查）")
        for failure in _FAILURES:
            print(f"  - {failure}")
        return 1
    print(f"B20F2 acceptance: PASS（{_CHECKS} 项检查）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
