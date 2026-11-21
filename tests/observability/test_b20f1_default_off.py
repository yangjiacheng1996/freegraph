# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · US4：未注入 / 只构造 / 环境变量 ⇒ 零文件零目录。"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from freegraph.graph import END, START, StateGraph
from freegraph.observability import FileTraceStore


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


def _snapshot(path: Path) -> tuple[set[str], set[str]]:
    if not path.exists():
        return set(), set()
    files = {str(item) for item in path.rglob("*") if item.is_file()}
    dirs = {str(item) for item in path.rglob("*") if item.is_dir()}
    return files, dirs


def test_no_injection_and_explicit_none_create_nothing(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    before = _snapshot(target)
    _linear().compile().invoke({"x": 0})
    _linear().compile(tracer=None).invoke({"x": 0})
    assert _snapshot(target) == before


def test_constructor_without_running_creates_nothing(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    FileTraceStore(target)
    assert not target.exists()


def test_environment_variables_do_not_enable_or_redirect(
    tmp_path: Path, monkeypatch
) -> None:
    explicit = tmp_path / "explicit"
    env_target = tmp_path / "env-target"
    monkeypatch.setenv("FREEGRAPH_TRACE_DIR", str(env_target))
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")

    _linear().compile().invoke({"x": 0})
    assert not env_target.exists()
    assert not explicit.exists()

    store = FileTraceStore(explicit)
    _linear().compile(tracer=store).invoke({"x": 0})
    assert list(explicit.glob("trace-*.jsonl"))
    assert not env_target.exists()


def test_import_freegraph_does_not_load_l5() -> None:
    import subprocess
    import sys

    code = "import sys, freegraph; print('freegraph.observability' in sys.modules)"
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False"
