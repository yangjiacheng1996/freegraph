# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · 导出面 / 查询签名 / 冻结字段 / L5 依赖 / 无 schema 泄漏。

契约层测试**不 import 内部层**（``freegraph.observability``）；运行时行为统一
通过子进程取证（与 B20F1 的契约测试口径一致）。
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
_OBS = _SRC / "freegraph" / "observability"
_NEW_MODULES = (_OBS / "_payloads.py", _OBS / "_query.py", _OBS / "_sqlite_store.py")


def _python(code: str) -> str:
    env = {**os.environ, "PYTHONPATH": str(_SRC)}
    proc = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _json(code: str) -> object:
    return json.loads(_python(code))


def test_exports_are_l5_only() -> None:
    payload = _json(
        """
import json
import freegraph.graph as graph
import freegraph.observability as observability
import freegraph.runtime as runtime
print(json.dumps({
    "observability": sorted(observability.__all__),
    "graph": sorted(graph.__all__),
    "runtime": sorted(runtime.__all__),
}))
"""
    )
    assert isinstance(payload, dict)
    assert "FileTraceStore" in payload["observability"]
    assert "SqliteTraceStore" in payload["observability"]
    assert "SqliteTraceStore" not in payload["graph"]
    assert "SqliteTraceStore" not in payload["runtime"]
    assert "FileTraceStore" not in payload["graph"]


def test_public_surfaces() -> None:
    payload = _json(
        """
import json
from freegraph.observability import FileTraceStore, SqliteTraceStore
def public(cls):
    return sorted(name for name in dir(cls) if not name.startswith("_"))
print(json.dumps({
    "file": public(FileTraceStore),
    "sqlite": public(SqliteTraceStore),
    "forbidden": {
        "search": hasattr(SqliteTraceStore, "search"),
        "read": hasattr(SqliteTraceStore, "read"),
        "read_all": hasattr(SqliteTraceStore, "read_all"),
        "enter": hasattr(SqliteTraceStore, "__enter__"),
        "exit": hasattr(SqliteTraceStore, "__exit__"),
        "close": hasattr(SqliteTraceStore, "close"),
    },
}))
"""
    )
    expected = [
        "current_span",
        "last_error",
        "on_span_end",
        "on_span_start",
        "on_trace_record",
        "query",
        "write_errors",
    ]
    assert payload["file"] == expected
    assert payload["sqlite"] == expected
    assert payload["forbidden"] == {
        "search": False,
        "read": False,
        "read_all": False,
        "enter": False,
        "exit": False,
        "close": False,
    }


def test_query_signature_is_shared() -> None:
    payload = _json(
        """
import inspect
import json
from freegraph.observability import FileTraceStore, SqliteTraceStore
def info(fn):
    sig = inspect.signature(fn)
    return {
        "params": list(sig.parameters),
        "default": sig.parameters["query"].default,
    }
print(json.dumps({
    "file": info(FileTraceStore.query),
    "sqlite": info(SqliteTraceStore.query),
}))
"""
    )
    assert payload["file"] == {"params": ["self", "query"], "default": None}
    assert payload["sqlite"] == {"params": ["self", "query"], "default": None}


def test_frozen_field_counts_are_unchanged() -> None:
    payload = _json(
        """
import dataclasses
import json
from freegraph.contracts import PregelTask, RunConfig, Span, TraceQuery, TraceSink
from freegraph.observability import TraceRecord
print(json.dumps({
    "span": len(dataclasses.fields(Span)),
    "record": len(dataclasses.fields(TraceRecord)),
    "query": len(dataclasses.fields(TraceQuery)),
    "run_config": len(dataclasses.fields(RunConfig)),
    "task": len(dataclasses.fields(PregelTask)),
    "sink": sorted(name for name in vars(TraceSink) if not name.startswith("_")),
}))
"""
    )
    assert payload == {
        "span": 11,
        "record": 13,
        "query": 5,
        "run_config": 9,
        "task": 7,
        "sink": ["current_span", "on_span_end", "on_span_start"],
    }


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.append(node.module)
    return modules


def test_new_modules_import_only_stdlib_l1_and_same_layer() -> None:
    violations: list[str] = []
    for path in (*_NEW_MODULES, _OBS / "_file_store.py"):
        for module in _absolute_imports(path):
            root = module.split(".")[0]
            if root in sys.stdlib_module_names:
                continue
            if module.startswith("freegraph.contracts"):
                continue
            violations.append(f"{path.name}: {module}")
    assert violations == [], violations


def test_no_public_schema_or_connection_names() -> None:
    for path in _NEW_MODULES:
        text = path.read_text(encoding="utf-8")
        for forbidden in (
            "def create_table",
            "def connect(",
            "def execute(",
            "public_connection",
        ):
            assert forbidden not in text, (path.name, forbidden)
    payload = _json(
        """
import json
from freegraph.observability import SqliteTraceStore
print(json.dumps({
    "connection": hasattr(SqliteTraceStore, "connection"),
    "conn": hasattr(SqliteTraceStore, "conn"),
    "table": hasattr(SqliteTraceStore, "table"),
}))
"""
    )
    assert payload == {"connection": False, "conn": False, "table": False}
