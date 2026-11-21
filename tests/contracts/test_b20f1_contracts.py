# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · 导出面 / 冻结字段 / L5 依赖方向（契约层测试不 import 内部层）。"""

from __future__ import annotations

import ast
import dataclasses
import json
import os
import subprocess
import sys
from pathlib import Path

from freegraph.contracts import PregelTask, RunConfig, Span, TraceSink

STOREFILE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "freegraph"
    / "observability"
    / "_file_store.py"
)


def _python(src_dir: Path, code: str, *args: str) -> str:
    env = {**os.environ, "PYTHONPATH": str(src_dir)}
    proc = subprocess.run(
        [sys.executable, "-c", code, *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_store_is_exported_only_from_l5(src_dir: Path) -> None:
    output = _python(
        src_dir,
        """
import json
import freegraph.graph as graph
import freegraph.observability as observability
import freegraph.runtime as runtime
print(json.dumps({
    "observability": "FileTraceStore" in observability.__all__,
    "graph": "FileTraceStore" in graph.__all__,
    "runtime": "FileTraceStore" in runtime.__all__,
}))
""",
    )
    assert json.loads(output) == {
        "observability": True,
        "graph": False,
        "runtime": False,
    }


def test_public_face_is_write_only_and_has_diagnostics(
    src_dir: Path, tmp_path: Path
) -> None:
    output = _python(
        src_dir,
        """
import json
import sys
from freegraph.observability import FileTraceStore
store = FileTraceStore(sys.argv[1])
names = ("on_span_start", "on_span_end", "on_trace_record", "current_span",
         "write_errors", "last_error")
lifecycle = ("close", "__enter__", "__exit__")
queries = ("query", "search", "read", "read_all")
print(json.dumps({
    "present": [name for name in names if hasattr(store, name)],
    "lifecycle": [name for name in lifecycle if hasattr(store, name)],
    "queries": [name for name in queries if hasattr(store, name)],
}))
""",
        str(tmp_path),
    )
    payload = json.loads(output)
    assert set(payload["present"]) == {
        "on_span_start",
        "on_span_end",
        "on_trace_record",
        "current_span",
        "write_errors",
        "last_error",
    }
    assert payload["lifecycle"] == []
    assert payload["queries"] == ["query"]


def test_frozen_field_counts_are_unchanged(src_dir: Path) -> None:
    assert len(dataclasses.fields(Span)) == 11
    assert len(dataclasses.fields(RunConfig)) == 9
    assert len(dataclasses.fields(PregelTask)) == 7
    output = _python(
        src_dir,
        """
import dataclasses
import json
from freegraph.observability import TraceRecord
from freegraph.runtime import SuperStepResult
from freegraph.contracts import TraceSink
print(json.dumps({
    "record": len(dataclasses.fields(TraceRecord)),
    "steps": len(dataclasses.fields(SuperStepResult)),
    "sink": sorted(name for name in vars(TraceSink) if not name.startswith("_")),
}))
""",
    )
    payload = json.loads(output)
    assert payload["record"] == 13
    assert payload["steps"] == 5
    assert payload["sink"] == ["current_span", "on_span_end", "on_span_start"]


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.append(node.module)
    return modules


def test_file_store_imports_only_stdlib_l1_and_same_layer() -> None:
    violations: list[str] = []
    for module in _absolute_imports(STOREFILE):
        root = module.split(".")[0]
        if root in sys.stdlib_module_names:
            continue
        if module.startswith("freegraph.contracts"):
            continue
        violations.append(module)
    assert violations == [], violations
