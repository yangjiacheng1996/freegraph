# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B21F1 · US2：默认关闭 / 惰性 import / 零 env / 零出站。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"


def _python(code: str, *, env_extra: dict[str, str] | None = None) -> str:
    env = {**os.environ, "PYTHONPATH": str(_SRC), "PYTHONUTF8": "1"}
    env.pop("LANGSMITH_TRACING", None)
    env.pop("LANGCHAIN_TRACING_V2", None)
    if env_extra:
        env.update(env_extra)
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


def test_importing_observability_does_not_load_otel_or_grpc() -> None:
    output = _python(
        """
import sys
import freegraph.observability as observability
assert 'OtlpExporter' in observability.__all__
assert 'opentelemetry' not in sys.modules
assert 'grpc' not in sys.modules
print('ok')
"""
    )
    assert output == "ok"


def test_default_off_run_does_not_load_otel_or_grpc() -> None:
    output = _python(
        """
from typing import TypedDict
from freegraph.graph import END, START, StateGraph
class S(TypedDict, total=False):
    x: int
b = StateGraph(S)
b.add_node('a', lambda state: {'x': 1})
b.add_edge(START, 'a')
b.add_edge('a', END)
assert b.compile().invoke({'x': 0})['x'] == 1
import sys
assert 'opentelemetry' not in sys.modules
assert 'grpc' not in sys.modules
print('ok')
""",
        env_extra={
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://127.0.0.1:4318",
            "OTEL_SERVICE_NAME": "should-not-be-read",
            "LANGSMITH_TRACING": "true",
        },
    )
    assert output == "ok"


def test_constructing_endpoint_with_missing_extra_raises_import_error_only_then() -> None:
    output = _python(
        """
import importlib.abc
import sys

class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'opentelemetry', 'grpc'}:
            raise ImportError('blocked by test')
        return None

sys.meta_path.insert(0, Blocker())
from typing import TypedDict
from freegraph.graph import END, START, StateGraph
class S(TypedDict, total=False):
    x: int
b = StateGraph(S)
b.add_node('a', lambda state: {'x': 1})
b.add_edge(START, 'a')
b.add_edge('a', END)
assert b.compile().invoke({'x': 0})['x'] == 1
from freegraph.observability import OtlpExporter
try:
    OtlpExporter(endpoint='127.0.0.1:4317')
except ImportError as exc:
    assert 'freegraph[otlp]' in str(exc)
else:
    raise AssertionError('expected ImportError')
print('ok')
"""
    )
    assert output == "ok"


def test_endpoint_with_invalid_arguments_is_value_error_without_import() -> None:
    from freegraph.observability import OtlpExporter

    with pytest.raises(ValueError):
        OtlpExporter()
    with pytest.raises(ValueError):
        OtlpExporter(endpoint="127.0.0.1:4317", exporter=object())
    with pytest.raises(ValueError):
        OtlpExporter(endpoint="http://127.0.0.1:4317", insecure=True)
    with pytest.raises(ValueError):
        OtlpExporter(endpoint="127.0.0.1:99999", insecure=True)
    with pytest.raises(ValueError):
        OtlpExporter(exporter=type("E", (), {"export": lambda self, spans: None})(), headers={"a": "b"})
    with pytest.raises(ValueError):
        OtlpExporter(exporter=type("E", (), {"export": lambda self, spans: None})(), timeout=1.0)
    with pytest.raises(ValueError):
        OtlpExporter(exporter=object())
