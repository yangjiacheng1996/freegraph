# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 可观测层共享夹具。"""

from __future__ import annotations

import json
import os
import stat
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest


class RecordingReceiver:
    """记录开始 / 结束 span 的接收端。"""

    def __init__(self) -> None:
        self.started: list[Any] = []
        self.ended: list[Any] = []

    def on_span_start(self, span: Any) -> None:
        self.started.append(span)

    def on_span_end(self, span: Any) -> None:
        self.ended.append(span)


class FailingReceiver:
    """回调即抛异常的接收端（用于异常隔离测试）。"""

    def __init__(self) -> None:
        self.calls = 0

    def on_span_start(self, span: Any) -> None:
        self.calls += 1
        raise RuntimeError("receiver boom")

    def on_span_end(self, span: Any) -> None:
        self.calls += 1
        raise RuntimeError("receiver boom")


class SpanConstructionCounter:
    """同时统计 ``_span_hook.Span`` 与 ``_producer.Span`` 的构造次数。"""

    def __init__(self) -> None:
        self.count = 0

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import freegraph.observability._producer as producer_module
        import freegraph.runtime._span_hook as hook_module

        for module in (hook_module, producer_module):
            original = module.Span

            def wrapper(*args: Any, __original: Any = original, **kwargs: Any) -> Any:
                self.count += 1
                return __original(*args, **kwargs)

            monkeypatch.setattr(module, "Span", wrapper)


class RunIdBindingCounter:
    """统计 invoke 路径 ``bind_run_ids`` 的调用次数。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import freegraph._stategraph as stategraph
        import freegraph.runtime._stream_context as stream_context
        import freegraph.runtime.superstep as superstep

        original = stream_context.bind_run_ids

        def wrapper(run_id: str, thread_id: str | None) -> Any:
            self.calls.append((run_id, thread_id))
            return original(run_id, thread_id)

        monkeypatch.setattr(stream_context, "bind_run_ids", wrapper)
        monkeypatch.setattr(superstep, "bind_run_ids", wrapper)
        monkeypatch.setattr(stategraph, "bind_run_ids", wrapper)


@contextmanager
def bind_producer(producer: Any) -> Iterator[Any]:
    """把同一个 producer 同时绑定到 L2 hook 与 L5 helper。"""
    from freegraph.observability._producer import bind_tracer as bind_l5
    from freegraph.runtime._span_hook import bind_span_tracer

    with bind_span_tracer(producer), bind_l5(producer):
        yield producer


@pytest.fixture
def recording_receiver() -> RecordingReceiver:
    return RecordingReceiver()


@pytest.fixture
def failing_receiver() -> FailingReceiver:
    return FailingReceiver()


@pytest.fixture
def span_counter() -> SpanConstructionCounter:
    return SpanConstructionCounter()


@pytest.fixture
def run_id_counter() -> RunIdBindingCounter:
    return RunIdBindingCounter()


@pytest.fixture
def bound_tracer(
    recording_receiver: RecordingReceiver,
) -> Iterator[tuple[Any, RecordingReceiver]]:
    from freegraph.observability import SpanProducer

    producer = SpanProducer(recording_receiver)
    with bind_producer(producer):
        yield producer, recording_receiver


@pytest.fixture
def node_span(
    bound_tracer: tuple[Any, RecordingReceiver],
) -> Iterator[Any]:
    """在 bound_tracer 上先压入一个合成节点 span，测试结束再弹出。"""
    from freegraph.runtime._span_hook import end_node_span, start_node_span

    producer, _receiver = bound_tracer
    span = start_node_span(producer, "test_node", "run-1", "thread-1", None)
    assert span is not None
    try:
        yield span
    finally:
        end_node_span(producer, span)


class RecordingSink:
    """B19F1 通用接收端：start/end + 可选 records。"""

    def __init__(self) -> None:
        self.started: list[Any] = []
        self.ended: list[Any] = []
        self.records: list[Any] = []
        self.current: list[Any] = []

    def on_span_start(self, span: Any) -> None:
        self.started.append(span)

    def on_span_end(self, span: Any) -> None:
        self.ended.append(span)

    def on_trace_record(self, record: Any) -> None:
        self.records.append(record)

    def current_span(self) -> Any:
        return None


class SpanOnlySink:
    """仅实现 start/end（运行期最小面）。"""

    def __init__(self) -> None:
        self.started: list[Any] = []
        self.ended: list[Any] = []

    def on_span_start(self, span: Any) -> None:
        self.started.append(span)

    def on_span_end(self, span: Any) -> None:
        self.ended.append(span)


class FailingSink:
    """start / end / record 均抛异常。"""

    def __init__(self) -> None:
        self.calls = 0

    def on_span_start(self, span: Any) -> None:
        self.calls += 1
        raise RuntimeError("sink boom")

    def on_span_end(self, span: Any) -> None:
        self.calls += 1
        raise RuntimeError("sink boom")

    def on_trace_record(self, record: Any) -> None:
        self.calls += 1
        raise RuntimeError("sink boom")


class FailingRecordSink(RecordingSink):
    """start/end 正常，仅 record 抛异常。"""

    def on_trace_record(self, record: Any) -> None:
        self.records.append(record)
        raise RuntimeError("record boom")


class RecordSink:
    """仅实现 on_trace_record（不接收 span）。"""

    def __init__(self) -> None:
        self.records: list[Any] = []

    def on_trace_record(self, record: Any) -> None:
        self.records.append(record)


class SpanProducerConstructionCounter:
    def __init__(self) -> None:
        self.count = 0

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import freegraph.observability._inject as inject_module
        import freegraph.observability._producer as producer_module

        original = producer_module.SpanProducer

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self.count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(producer_module, "SpanProducer", wrapper)
        monkeypatch.setattr(inject_module, "SpanProducer", wrapper)


class TraceRecordConstructionCounter:
    def __init__(self) -> None:
        self.count = 0

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import freegraph.observability._producer as producer_module
        import freegraph.observability._record as record_module

        original = record_module.TraceRecord

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self.count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(record_module, "TraceRecord", wrapper)
        monkeypatch.setattr(producer_module, "TraceRecord", wrapper)


class InputOutputCaptureCounter:
    def __init__(self) -> None:
        self.count = 0

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import freegraph.runtime.superstep as superstep

        original_raw = superstep._execute_node_pure_with_raw
        original_payload = superstep.build_trace_payload

        def raw_wrapper(*args: Any, **kwargs: Any) -> Any:
            self.count += 1
            return original_raw(*args, **kwargs)

        def payload_wrapper(*args: Any, **kwargs: Any) -> Any:
            self.count += 1
            return original_payload(*args, **kwargs)

        monkeypatch.setattr(superstep, "_execute_node_pure_with_raw", raw_wrapper)
        monkeypatch.setattr(superstep, "build_trace_payload", payload_wrapper)


@pytest.fixture
def recording_sink() -> RecordingSink:
    return RecordingSink()


@pytest.fixture
def span_only_sink() -> SpanOnlySink:
    return SpanOnlySink()


@pytest.fixture
def failing_sink() -> FailingSink:
    return FailingSink()


@pytest.fixture
def failing_record_sink() -> FailingRecordSink:
    return FailingRecordSink()


@pytest.fixture
def record_sink() -> RecordSink:
    return RecordSink()


@pytest.fixture
def span_producer_counter() -> SpanProducerConstructionCounter:
    return SpanProducerConstructionCounter()


@pytest.fixture
def trace_record_counter() -> TraceRecordConstructionCounter:
    return TraceRecordConstructionCounter()


@pytest.fixture
def input_output_counter() -> InputOutputCaptureCounter:
    return InputOutputCaptureCounter()


# ── B20F1 共享 helpers ───────────────────────────────────────────────────


def make_span(*, run_id: str = "safe-run-1", node: str = "a", **overrides: Any) -> Any:
    """构造一个字段齐全的 ``Span``（默认是结束快照）。"""
    from freegraph.contracts.trace import Span

    values: dict[str, Any] = {
        "id": uuid.uuid4().hex,
        "name": node,
        "attributes": {},
        "parent": None,
        "start_time": "2026-11-21T12:00:00.000000000+00:00",
        "end_time": "2026-11-21T12:00:00.000120000+00:00",
        "context": {},
        "thread_id": "t-1",
        "run_id": run_id,
        "node": node,
        "checkpoint_id": None,
    }
    values.update(overrides)
    return Span(**values)


def make_record(*, run_id: str = "safe-run-1", node: str = "a", **overrides: Any) -> Any:
    """构造一个字段齐全的 ``TraceRecord``。"""
    from freegraph.observability._record import TraceRecord

    values: dict[str, Any] = {
        "span_id": uuid.uuid4().hex,
        "task_id": node,
        "run_id": run_id,
        "thread_id": "t-1",
        "checkpoint_id": None,
        "node": node,
        "superstep": 0,
        "triggers": (),
        "concurrency_group": (),
        "barrier_groups": (),
        "input_state": {},
        "output_state": {},
        "error": None,
    }
    values.update(overrides)
    return TraceRecord(**values)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """逐行 ``json.loads`` 并返回对象列表（空行视为错误）。"""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert all(line for line in lines), "empty line in JSONL"
    return [json.loads(line) for line in lines]


def file_mode(path: Path) -> int | None:
    """返回 POSIX mode；Windows / 非 POSIX 返回 ``None``。"""
    if os.name != "posix":
        return None
    return stat.S_IMODE(os.stat(path).st_mode)


# ── B20F2 共享 helpers ───────────────────────────────────────────────────


def seed_events(
    store: Any,
    *,
    spans: tuple[Any, ...] = (),
    records: tuple[Any, ...] = (),
) -> None:
    """按 B19F1 顺序向 store 喂事件：record 先于其 span（若同 ``span_id``）。"""
    span_ids = {span.id for span in spans}
    for record in records:
        if record.span_id in span_ids:
            store.on_trace_record(record)
    for record in records:
        if record.span_id not in span_ids:
            store.on_trace_record(record)
    for span in spans:
        store.on_span_end(span)


def assert_rows_equal(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> None:
    """逐条比较两个查询结果，并在不等时给出可读差异。"""
    assert len(left) == len(right), (
        f"row count differs: {len(left)} != {len(right)}\n"
        f"left={left!r}\nright={right!r}"
    )
    for index, (a, b) in enumerate(zip(left, right, strict=True)):
        assert a == b, f"row {index} differs:\nleft={a!r}\nright={b!r}"


def query_by_kind(rows: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    """按 ``kind`` 过滤查询结果（测试辅助，不改变原列表）。"""
    return [row for row in rows if row.get("kind") == kind]
