# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B21F1 · 公开面 / 构造校验 / 冻结字段 / 无 schema 泄漏（契约层不 import 内部层）。"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

from freegraph.contracts.protocols import TraceSink
from freegraph.contracts.trace import Span, TraceQuery
from freegraph.contracts.types import RunConfig

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"


def _python(code: str) -> str:
    env = {**os.environ, "PYTHONPATH": str(_SRC), "PYTHONUTF8": "1"}
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


def test_public_symbol_is_exported_only_from_l5() -> None:
    output = _python(
        """
import freegraph.graph as graph
import freegraph.runtime as runtime
import freegraph.observability as observability
from freegraph.observability import OtlpExporter
assert 'OtlpExporter' in observability.__all__
assert 'OtlpExporter' not in graph.__all__
assert 'OtlpExporter' not in runtime.__all__
assert OtlpExporter.__module__ == 'freegraph.observability._otlp_exporter'
print('ok')
"""
    )
    assert output == "ok"


def test_trace_sink_shape_and_no_lifecycle_api() -> None:
    for method in ("on_span_start", "on_span_end", "current_span"):
        assert callable(getattr(TraceSink, method))
    output = _python(
        """
from freegraph.observability import OtlpExporter
fake = type('E', (), {'export': lambda self, spans: None})()
exporter = OtlpExporter(exporter=fake)
for method in ('on_span_start', 'on_span_end', 'current_span'):
    assert callable(getattr(exporter, method))
for forbidden in ('close', '__enter__', '__exit__'):
    assert not hasattr(exporter, forbidden)
print('ok')
"""
    )
    assert output == "ok"


def test_diagnostics_are_read_only_properties() -> None:
    output = _python(
        """
from freegraph.observability import OtlpExporter
assert isinstance(OtlpExporter.export_errors, property)
assert isinstance(OtlpExporter.last_error, property)
assert OtlpExporter.export_errors.fset is None
assert OtlpExporter.last_error.fset is None
assert not hasattr(OtlpExporter, 'on_trace_record')
print('ok')
"""
    )
    assert output == "ok"


def test_frozen_field_counts_are_unchanged() -> None:
    assert len(fields(Span)) == 11
    assert len(fields(TraceQuery)) == 5
    assert len(fields(RunConfig)) == 9
    for method in ("on_span_start", "on_span_end", "current_span"):
        assert callable(getattr(TraceSink, method))
    assert not hasattr(TraceSink, "on_trace_record")
    output = _python(
        """
from dataclasses import fields
from freegraph.observability._record import TraceRecord
assert len(fields(TraceRecord)) == 13
print('ok')
"""
    )
    assert output == "ok"


def test_constructor_validation() -> None:
    output = _python(
        """
from freegraph.observability import OtlpExporter
fake = type('E', (), {'export': lambda self, spans: None})()
def expect(kind, fn):
    try:
        fn()
    except kind:
        return
    raise AssertionError('expected ' + kind.__name__)
expect(ValueError, lambda: OtlpExporter())
expect(ValueError, lambda: OtlpExporter(endpoint='127.0.0.1:4317', exporter=fake))
for endpoint in ('', 'http://127.0.0.1:4317', '127.0.0.1', '127.0.0.1:0', '127.0.0.1:65536', '127.0.0.1:no', 'host:1:2'):
    expect(ValueError, lambda endpoint=endpoint: OtlpExporter(endpoint=endpoint, insecure=True))
OtlpExporter(endpoint='127.0.0.1:4317', insecure=True)
OtlpExporter(endpoint='[::1]:4317', insecure=True)
expect(ValueError, lambda: OtlpExporter(exporter=fake, insecure=True))
expect(ValueError, lambda: OtlpExporter(exporter=fake, headers={'a': 'b'}))
expect(ValueError, lambda: OtlpExporter(exporter=fake, timeout=1.0))
expect(ValueError, lambda: OtlpExporter(exporter=object()))
expect(ValueError, lambda: OtlpExporter(exporter=fake, on_error=object()))
expect(ValueError, lambda: OtlpExporter(endpoint='127.0.0.1:4317', insecure=1))
expect(ValueError, lambda: OtlpExporter(endpoint='127.0.0.1:4317', headers={'a': 1}))
expect(ValueError, lambda: OtlpExporter(endpoint='127.0.0.1:4317', timeout=0))
print('ok')
"""
    )
    assert output == "ok"


def test_no_schema_or_wire_format_leakage() -> None:
    root = _SRC / "freegraph"
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "SerializeToString" not in text, path
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("google.protobuf"), path
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("google.protobuf"), path


def test_mapping_modules_do_not_consume_query_api() -> None:
    root = _SRC / "freegraph" / "observability"
    for name in ("_otlp_mapping.py", "_otlp_exporter.py", "_otlp_transport.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert ".query(" not in text, name
        assert "FileTraceStore" not in text, name
        assert "SqliteTraceStore" not in text, name


def test_mapping_does_not_reference_trace_record() -> None:
    path = _SRC / "freegraph" / "observability" / "_otlp_mapping.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert node.id != "TraceRecord"
        elif isinstance(node, ast.Attribute):
            assert node.attr != "on_trace_record"


def test_current_span_returns_none_and_no_otel_leak() -> None:
    output = _python(
        """
from freegraph.observability import OtlpExporter
fake = type('E', (), {'export': lambda self, spans: None})()
exporter = OtlpExporter(exporter=fake)
assert exporter.current_span() is None
assert all(name.startswith('_') for name in vars(exporter))
print('ok')
"""
    )
    assert output == "ok"
