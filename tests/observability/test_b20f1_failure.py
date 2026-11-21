# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · US3：写入失败不阻断，且四路可感知。"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TypedDict

import pytest

from freegraph.graph import END, START, StateGraph
from freegraph.observability import FileTraceStore

from .conftest import make_span, read_jsonl


class _State(TypedDict, total=False):
    x: int


def _linear() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def _target_is_file(tmp_path: Path) -> Path:
    target = tmp_path / "not-a-directory"
    target.write_text("occupied", encoding="utf-8")
    return target


def test_directory_is_a_file_does_not_propagate_and_reports(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    target = _target_is_file(tmp_path)
    errors: list[BaseException] = []
    store = FileTraceStore(target, on_error=errors.append)

    with caplog.at_level(logging.WARNING, logger="freegraph.observability._file_store"):
        store.on_span_end(make_span())

    assert store.write_errors == 1
    assert store.last_error is not None
    assert "FileExistsError" in store.last_error or "NotADirectoryError" in store.last_error
    assert len(errors) == 1
    assert isinstance(errors[0], Exception)
    assert any(record.levelno == logging.WARNING for record in caplog.records)
    assert not list(tmp_path.glob("trace-*.jsonl"))


def test_serialization_failure_is_isolated(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    store.on_span_end(make_span(attributes={"bad": object()}))
    assert store.write_errors == 1
    assert store.last_error is not None
    assert "TypeError" in store.last_error
    assert not target.exists()


def test_graph_still_returns_when_directory_is_a_file(tmp_path: Path) -> None:
    target = _target_is_file(tmp_path)
    store = FileTraceStore(target)
    out = _linear().compile(tracer=store).invoke({"x": 0})
    assert out["x"] == 2
    assert store.write_errors > 0


def test_previous_valid_line_is_preserved_after_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    store.on_span_end(make_span(node="good"))
    path = next(target.glob("trace-*.jsonl"))
    good_size = path.stat().st_size
    good_lines = read_jsonl(path)

    original = os.fdopen

    class _PartialThenBoom:
        def __init__(self, real):
            self.real = real

        def write(self, data):
            self.real.write(data[:5])
            raise OSError("disk full")

        def flush(self):
            self.real.flush()

        def close(self):
            self.real.close()

    def fake_fdopen(fd, *args, **kwargs):
        return _PartialThenBoom(original(fd, *args, **kwargs))

    monkeypatch.setattr(os, "fdopen", fake_fdopen)
    store.on_span_end(make_span(node="bad"))

    assert store.write_errors == 1
    assert path.stat().st_size == good_size
    assert read_jsonl(path) == good_lines


def test_readonly_directory_when_permissions_are_enforced(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    if os.name != "posix" or os.geteuid() == 0:
        pytest.skip("POSIX non-root required to enforce chmod")
    target = tmp_path / "readonly"
    target.mkdir()
    target.chmod(0o500)
    try:
        store = FileTraceStore(target)
        with caplog.at_level(logging.WARNING):
            store.on_span_end(make_span())
        assert store.write_errors == 1
        assert store.last_error
    finally:
        target.chmod(0o700)
