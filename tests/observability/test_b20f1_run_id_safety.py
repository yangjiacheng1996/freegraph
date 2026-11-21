# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · SC-014：run_id 文件名安全 / 目录不展开 / 无穿越。"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from freegraph.observability import FileTraceStore

from .conftest import make_span, read_jsonl


@pytest.mark.parametrize(
    "bad_run_id",
    ["", ".", "..", "a.b", "a..b", "../evil", "a/b", "a\\b", "-leading", "_leading"],
)
def test_unsafe_run_id_is_rejected_without_creating_anything(
    tmp_path: Path, bad_run_id: str
) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    store.on_span_end(make_span(run_id=bad_run_id))
    assert not target.exists()
    assert store.write_errors == 1
    assert store.last_error is not None
    assert "ValueError" in store.last_error


def test_safe_uuid_hex_is_accepted(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    run_id = uuid.uuid4().hex
    store.on_span_end(make_span(run_id=run_id))
    path = target / f"trace-{run_id}.jsonl"
    assert path.is_file()
    assert read_jsonl(path)[0]["run_id"] == run_id


def test_directory_tilde_and_home_are_not_expanded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    literal = tmp_path / "~" / "$HOME"
    store = FileTraceStore(literal)
    store.on_span_end(make_span(run_id="literal-run"))
    assert list(literal.glob("trace-*.jsonl"))
    assert not list(fake_home.rglob("trace-*.jsonl"))


def test_environment_variable_does_not_redirect_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    requested = tmp_path / "requested"
    env_target = tmp_path / "env-target"
    monkeypatch.setenv("FREEGRAPH_TRACE_DIR", str(env_target))
    store = FileTraceStore(requested)
    store.on_span_end(make_span(run_id="env-run"))
    assert list(requested.glob("trace-*.jsonl"))
    assert not env_target.exists()
