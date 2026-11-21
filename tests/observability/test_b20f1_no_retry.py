# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · US3：不重试 / 截断回写前偏移 / BaseException 不吞。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from freegraph.observability import FileTraceStore

from .conftest import make_span, read_jsonl


class _FlakyHandle:
    def __init__(self, real, state: dict[str, int]) -> None:
        self.real = real
        self.state = state

    def write(self, data: str) -> int:
        self.state["writes"] += 1
        if self.state["fail_on"] == self.state["writes"]:
            raise OSError("transient")
        return self.real.write(data)

    def flush(self) -> None:
        self.real.flush()

    def close(self) -> None:
        self.state["closes"] += 1
        self.real.close()


def _install_flaky(monkeypatch: pytest.MonkeyPatch, fail_on: int) -> dict[str, int]:
    original = os.fdopen
    state = {"writes": 0, "closes": 0, "fdopen": 0, "fail_on": fail_on}

    def fake_fdopen(fd, *args, **kwargs):
        state["fdopen"] += 1
        return _FlakyHandle(original(fd, *args, **kwargs), state)

    monkeypatch.setattr(os, "fdopen", fake_fdopen)
    return state


def test_failed_line_is_not_retried_and_next_line_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    state = _install_flaky(monkeypatch, fail_on=1)

    store.on_span_end(make_span(node="first"))
    assert store.write_errors == 1
    assert state["writes"] == 1
    assert state["fdopen"] == 1

    store.on_span_end(make_span(node="second"))
    assert state["writes"] == 2
    assert state["fdopen"] == 2
    objs = read_jsonl(next(target.glob("trace-*.jsonl")))
    assert len(objs) == 1
    assert objs[0]["node"] == "second"
    assert "transient" in (store.last_error or "")


def test_base_exception_is_not_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = os.fdopen

    class _InterruptHandle:
        def __init__(self, real) -> None:
            self.real = real

        def write(self, data: str) -> int:
            raise KeyboardInterrupt

        def flush(self) -> None:
            self.real.flush()

        def close(self) -> None:
            self.real.close()

    def fake_fdopen(fd, *args, **kwargs):
        return _InterruptHandle(original(fd, *args, **kwargs))

    monkeypatch.setattr(os, "fdopen", fake_fdopen)
    store = FileTraceStore(tmp_path / "traces")
    with pytest.raises(KeyboardInterrupt):
        store.on_span_end(make_span())
    assert store.write_errors == 0
