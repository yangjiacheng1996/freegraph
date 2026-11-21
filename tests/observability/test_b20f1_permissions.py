# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · Phase 7：POSIX 权限 / 无生命周期 API / 句柄释放。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from freegraph.observability import FileTraceStore

from .conftest import file_mode, make_span


def test_new_file_mode_is_not_wider_than_0600(tmp_path: Path) -> None:
    if os.name != "posix":
        pytest.skip("POSIX mode only")
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    store.on_span_end(make_span(run_id="mode-run"))
    path = next(target.glob("trace-*.jsonl"))
    mode = file_mode(path)
    assert mode is not None
    assert mode & 0o077 == 0


def test_existing_file_mode_is_not_broadened(tmp_path: Path) -> None:
    if os.name != "posix":
        pytest.skip("POSIX mode only")
    target = tmp_path / "traces"
    target.mkdir()
    path = target / "trace-existing-run.jsonl"
    path.write_text("", encoding="utf-8")
    path.chmod(0o644)
    before = file_mode(path)

    store = FileTraceStore(target)
    store.on_span_end(make_span(run_id="existing-run"))
    assert file_mode(path) == before


def test_no_lifecycle_api(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    assert not hasattr(store, "close")
    assert not hasattr(store, "__enter__")
    assert not hasattr(store, "__exit__")


def test_file_can_be_renamed_and_deleted_after_callback(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    store.on_span_end(make_span(run_id="rename-run"))
    path = next(target.glob("trace-*.jsonl"))
    moved = path.with_name(path.name + ".moved")
    path.rename(moved)
    moved.unlink()
    assert not path.exists()


def test_each_line_closes_its_handle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = os.fdopen
    closes = {"n": 0}

    class _CloseCounter:
        def __init__(self, real) -> None:
            self.real = real

        def write(self, data: str) -> int:
            return self.real.write(data)

        def flush(self) -> None:
            self.real.flush()

        def close(self) -> None:
            closes["n"] += 1
            self.real.close()

    def fake_fdopen(fd, *args, **kwargs):
        return _CloseCounter(original(fd, *args, **kwargs))

    monkeypatch.setattr(os, "fdopen", fake_fdopen)
    store = FileTraceStore(tmp_path / "traces")
    for index in range(3):
        store.on_span_end(make_span(id=f"line-{index}"))
    assert closes["n"] == 3


def test_windows_path_as_file_does_not_block(tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("Windows branch")
    target = tmp_path / "not-a-dir"
    target.write_text("occupied", encoding="utf-8")
    store = FileTraceStore(target)
    store.on_span_end(make_span())
    assert store.write_errors == 1
