# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · SC-015：每行 flush 即成功 / 不逐行 fsync / 崩溃后已 flush 行可读。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from freegraph.observability import FileTraceStore

from .conftest import make_span, read_jsonl

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_no_fsync_is_called(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_fsync(fd: int) -> None:
        raise AssertionError("fsync must not be called")

    monkeypatch.setattr(os, "fsync", fail_fsync)
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    store.on_span_end(make_span())
    assert len(read_jsonl(next(target.glob("trace-*.jsonl")))) == 1


def test_flushed_line_survives_process_crash(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    code = """
import os
import sys
from freegraph.contracts.trace import Span
from freegraph.observability import FileTraceStore

store = FileTraceStore(sys.argv[1])
span = Span(
    id="crash-span",
    name="a",
    start_time="2026-11-21T12:00:00.000000000+00:00",
    end_time="2026-11-21T12:00:00.000120000+00:00",
    run_id="crash-run",
    node="a",
)
store.on_span_end(span)
os._exit(0)
"""
    env = {**os.environ, "PYTHONPATH": str(_REPO_ROOT / "src")}
    proc = subprocess.run(
        [sys.executable, "-c", code, str(target)],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    path = next(target.glob("trace-*.jsonl"))
    text = path.read_text(encoding="utf-8")
    assert text.splitlines()
    assert all(json.loads(line) for line in text.splitlines())
