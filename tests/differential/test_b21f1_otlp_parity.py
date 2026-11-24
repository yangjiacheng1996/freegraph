# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B21F1 · D-601…D-608 差分场景（上游缺席 ⇒ skip）。"""

from __future__ import annotations

import ast
import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("langchain_core")

from freegraph.graph import END, START, StateGraph
from freegraph.observability import OtlpExporter
from freegraph.contracts.trace import Span
from freegraph.observability._otlp_mapping import map_span


class _State(TypedDict, total=False):
    x: int


class RecordingSpanExporter:
    def __init__(self) -> None:
        self.spans: list[Any] = []
        self.calls = 0

    def export(self, spans: Any) -> None:
        self.calls += 1
        self.spans.extend(spans)
        return None


def make_span(**overrides: Any) -> Span:
    values: dict[str, Any] = {
        "id": "span-1",
        "name": "node",
        "attributes": {},
        "parent": None,
        "start_time": "2026-11-24T12:00:00.000000000+00:00",
        "end_time": "2026-11-24T12:00:01.000000000+00:00",
        "context": {},
        "thread_id": None,
        "run_id": "run-1",
        "node": "node",
        "checkpoint_id": None,
    }
    values.update(overrides)
    return Span(**values)


def _graph(tracer: Any = None) -> Any:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_node("b", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder.compile(tracer=tracer)


def _python(code: str, extra_env: dict[str, str] | None = None) -> str:
    root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONUTF8": "1"}
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def test_d601_standard_otlp_export_is_parseable_by_stub_receiver() -> None:
    recording = RecordingSpanExporter()
    _graph(OtlpExporter(exporter=recording)).invoke({"x": 0})
    assert recording.calls == 2
    assert all(span.context.trace_id for span in recording.spans)


def test_d602_default_off_has_zero_otel_import() -> None:
    output = _python(
        """
from typing import TypedDict
from freegraph.graph import END, START, StateGraph
import sys
class S(TypedDict, total=False):
    x: int
b = StateGraph(S)
b.add_node('a', lambda s: {'x': 1})
b.add_edge(START, 'a')
b.add_edge('a', END)
assert b.compile().invoke({'x': 0})['x'] == 1
assert 'opentelemetry' not in sys.modules
assert 'grpc' not in sys.modules
print('ok')
"""
    )
    assert output == "ok"


def test_d603_otel_and_langsmith_env_do_not_change_behavior() -> None:
    output = _python(
        """
from typing import TypedDict
from freegraph.graph import END, START, StateGraph
class S(TypedDict, total=False):
    x: int
b = StateGraph(S)
b.add_node('a', lambda s: {'x': 1})
b.add_edge(START, 'a')
b.add_edge('a', END)
assert b.compile().invoke({'x': 0})['x'] == 1
print('ok')
""",
        {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://127.0.0.1:4318",
            "OTEL_SERVICE_NAME": "x",
            "LANGSMITH_TRACING": "true",
        },
    )
    assert output == "ok"


def test_d604_failure_isolation() -> None:
    exporter = OtlpExporter(endpoint="127.0.0.1:1", insecure=True, timeout=0.05)
    assert _graph(exporter).invoke({"x": 0}) == {"x": 2}
    assert exporter.export_errors > 0
    assert exporter.last_error is not None


def test_d605_paired_lifecycle_exports_only_completed_spans() -> None:
    recording = RecordingSpanExporter()
    exporter = OtlpExporter(exporter=recording)
    exporter.on_span_start(make_span())
    assert recording.calls == 0
    _graph(exporter).invoke({"x": 0})
    assert recording.calls == 2


def test_d606_attributes_are_directly_mapped() -> None:
    readable = map_span(
        make_span(attributes={"gen_ai.operation.name": "chat", "gen_ai.request.model": "m"})
    ).readable
    assert readable is not None
    assert readable.attributes["gen_ai.operation.name"] == "chat"
    assert readable.attributes["gen_ai.request.model"] == "m"


def test_d607_dependency_closure_is_stricter() -> None:
    requires = importlib.metadata.requires("freegraph") or []
    non_extra = [item for item in requires if "extra ==" not in item]
    assert non_extra == []
    upstream = importlib.metadata.requires("langchain-core") or []
    assert any("langsmith" in item for item in upstream)


def test_d608_no_self_encoding() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "freegraph"
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "OTLPSpanExporter" not in text
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("google.protobuf")
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("google.protobuf")
            elif isinstance(node, ast.Attribute):
                assert node.attr != "SerializeToString"
