# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · 上游差分 D-401…D-408（上游缺席即 skip）。"""

from __future__ import annotations

import json
import socket
import tomllib
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypedDict

import pytest

from freegraph.contracts.trace import Span
from freegraph.graph import END, START, StateGraph
from freegraph.observability import FileTraceStore


class _State(TypedDict, total=False):
    x: int


def _make_span(run_id: str) -> Span:
    return Span(
        id=uuid.uuid4().hex,
        name="a",
        start_time="2026-11-21T12:00:00.000000000+00:00",
        end_time="2026-11-21T12:00:00.000120000+00:00",
        run_id=run_id,
        node="a",
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _graph() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def _upstream_graph():
    pytest.importorskip("langgraph.graph")
    from langgraph.graph import END as U_END
    from langgraph.graph import START as U_START
    from langgraph.graph import StateGraph as UStateGraph

    builder = UStateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(U_START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", U_END)
    return builder


def _callback_counter():
    pytest.importorskip("langchain_core")
    from langchain_core.callbacks import BaseCallbackHandler

    class Counter(BaseCallbackHandler):
        def __init__(self) -> None:
            self.starts = 0
            self.ends = 0

        def on_chain_start(self, serialized, inputs, **kwargs) -> None:
            self.starts += 1

        def on_chain_end(self, outputs, **kwargs) -> None:
            self.ends += 1

    return Counter()


def test_d401_default_off_has_no_local_files_and_upstream_runs(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    assert not target.exists()
    assert _graph().compile().invoke({"x": 0})["x"] == 2
    assert _upstream_graph().compile().invoke({"x": 0})["x"] == 2
    assert not target.exists()


def test_d402_injected_store_writes_file_and_same_final_state(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    free_state = _graph().compile(tracer=store).invoke({"x": 0})
    handler = _callback_counter()
    up_state = _upstream_graph().compile().invoke(
        {"x": 0}, config={"callbacks": [handler]}
    )
    assert free_state == up_state == {"x": 2}
    assert list((tmp_path / "traces").glob("trace-*.jsonl"))
    assert handler.starts >= 2 and handler.ends >= 2


def test_d403_environment_variables_do_not_enable_freegraph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    target = tmp_path / "traces"
    _graph().compile().invoke({"x": 0})
    assert not target.exists()
    store = FileTraceStore(target)
    _graph().compile(tracer=store).invoke({"x": 0})
    assert list(target.glob("trace-*.jsonl"))


@contextmanager
def _observe_egress():
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


def test_d404_framework_egress_is_zero(tmp_path: Path) -> None:
    with _observe_egress() as calls:
        store = FileTraceStore(tmp_path / "traces")
        _graph().compile(tracer=store).invoke({"x": 0})
    assert calls == []


def test_d405_unwritable_directory_does_not_block(tmp_path: Path) -> None:
    target = tmp_path / "occupied"
    target.write_text("occupied", encoding="utf-8")
    store = FileTraceStore(target)
    assert _graph().compile(tracer=store).invoke({"x": 0})["x"] == 2
    assert store.write_errors > 0


def test_d406_two_runs_are_grouped_by_run_id(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    app = _graph().compile(tracer=store)
    app.invoke({"x": 0})
    app.invoke({"x": 0})
    files = sorted(target.glob("trace-*.jsonl"))
    assert len(files) == 2
    for path in files:
        objs = _read_jsonl(path)
        assert len({obj["run_id"] for obj in objs}) == 1
        assert path.stem == f"trace-{objs[0]['run_id']}"


def test_d407_base_dependency_closure_is_empty() -> None:
    repo = Path(__file__).resolve().parents[2]
    data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"].get("dependencies", []) == []


def test_d408_same_instance_serializes_multiple_writers(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    spans = [_make_span(run_id="parity-run") for _ in range(20)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(store.on_span_end, spans))
    objs = _read_jsonl(next(target.glob("trace-*.jsonl")))
    assert len(objs) == 20
    assert len({obj["id"] for obj in objs}) == 20
