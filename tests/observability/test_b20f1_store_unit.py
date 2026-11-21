# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · US1：``FileTraceStore`` 行结构 / 文件命名 / 默认关闭构造 / 空事件。"""

from __future__ import annotations

from pathlib import Path

from freegraph.observability import FileTraceStore

from .conftest import make_record, make_span, read_jsonl

SPAN_FIELDS = {
    "kind",
    "id",
    "name",
    "attributes",
    "parent",
    "start_time",
    "end_time",
    "context",
    "thread_id",
    "run_id",
    "node",
    "checkpoint_id",
}

RECORD_FIELDS = {
    "kind",
    "span_id",
    "task_id",
    "run_id",
    "thread_id",
    "checkpoint_id",
    "node",
    "superstep",
    "triggers",
    "concurrency_group",
    "barrier_groups",
    "input_state",
    "output_state",
    "error",
}


def _files(directory: Path) -> list[Path]:
    return sorted(directory.glob("trace-*.jsonl"))


def test_constructor_has_no_filesystem_side_effect(tmp_path: Path) -> None:
    target = tmp_path / "never"
    FileTraceStore(target)
    assert not target.exists()


def test_on_span_start_writes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    store.on_span_start(make_span(end_time=None))
    assert not target.exists()
    assert store.write_errors == 0
    assert store.current_span() is None


def test_on_span_end_writes_one_file_with_all_span_fields(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    span = make_span(attributes={"gen_ai.system": "demo"}, context={"k": "v"})
    store.on_span_end(span)

    files = _files(target)
    assert len(files) == 1
    assert files[0].name == f"trace-{span.run_id}.jsonl"
    objs = read_jsonl(files[0])
    assert len(objs) == 1
    assert set(objs[0]) == SPAN_FIELDS
    assert objs[0]["kind"] == "span"
    assert objs[0]["id"] == span.id
    assert objs[0]["name"] == span.name
    assert objs[0]["attributes"] == {"gen_ai.system": "demo"}
    assert objs[0]["context"] == {"k": "v"}
    assert objs[0]["end_time"] == span.end_time
    assert store.write_errors == 0
    assert store.last_error is None


def test_on_trace_record_writes_all_record_fields(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    record = make_record(
        triggers=(("e", "__start__"),),
        concurrency_group=("a",),
        barrier_groups=(("a", "b"),),
        input_state={"x": 0},
        output_state={"x": 1},
    )
    store.on_trace_record(record)

    files = _files(target)
    assert len(files) == 1
    objs = read_jsonl(files[0])
    assert len(objs) == 1
    assert set(objs[0]) == RECORD_FIELDS
    assert objs[0]["kind"] == "trace_record"
    assert objs[0]["span_id"] == record.span_id
    assert objs[0]["triggers"] == [["e", "__start__"]]
    assert objs[0]["barrier_groups"] == [["a", "b"]]
    assert objs[0]["input_state"] == {"x": 0}
    assert objs[0]["output_state"] == {"x": 1}
    assert objs[0]["error"] is None


def test_append_and_record_before_span(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    span = make_span()
    record = make_record(span_id=span.id)
    store.on_trace_record(record)
    store.on_span_end(span)

    objs = read_jsonl(_files(target)[0])
    assert [obj["kind"] for obj in objs] == ["trace_record", "span"]

    store.on_span_end(make_span(id=span.id))
    assert len(read_jsonl(_files(target)[0])) == 3


def test_two_run_ids_write_two_files(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    store.on_span_end(make_span(run_id="run-one"))
    store.on_span_end(make_span(run_id="run-two"))

    files = _files(target)
    assert [path.name for path in files] == ["trace-run-one.jsonl", "trace-run-two.jsonl"]
    for path in files:
        objs = read_jsonl(path)
        assert len({obj["run_id"] for obj in objs}) == 1
        assert path.stem == f"trace-{objs[0]['run_id']}"


def test_no_events_writes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    FileTraceStore(target)
    assert not target.exists()
