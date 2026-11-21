# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · 冻结面零改动 + L5 导出面（契约层测试不 import 内部层）。"""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
from pathlib import Path

from freegraph.contracts import PregelTask, RunConfig, Span, TraceSink


def _field_names(cls) -> set[str]:
    return {field.name for field in dataclasses.fields(cls)}


def test_frozen_dataclasses_are_unchanged() -> None:
    assert _field_names(Span) == {
        "id",
        "name",
        "attributes",
        "parent",
        "start_time",
        "end_time",
        "context",
        "thread_id",
        "run_id",
        "node",
        "checkpoint_id",
    }
    assert _field_names(RunConfig) == {
        "thread_id",
        "context",
        "metadata",
        "tags",
        "configurable",
        "max_concurrency",
        "recursion_limit",
        "run_name",
        "run_id",
    }
    assert len(dataclasses.fields(PregelTask)) == 7


def test_tracesink_has_exactly_three_methods() -> None:
    names = {name for name in vars(TraceSink) if not name.startswith("_")}
    assert names == {"on_span_start", "on_span_end", "current_span"}


def test_public_symbol_surfaces_are_unchanged(src_dir: Path) -> None:
    code = """
import json
import freegraph.contracts as contracts
import freegraph.graph as graph
import freegraph.runtime as runtime
from freegraph.runtime import SuperStepResult
import dataclasses
print(json.dumps({
    "graph": len(graph.__all__),
    "contracts": len(contracts.__all__),
    "runtime": len(runtime.__all__),
    "steps": len(dataclasses.fields(SuperStepResult)),
}))
"""
    env = {**os.environ, "PYTHONPATH": str(src_dir)}
    proc = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload == {"graph": 8, "contracts": 22, "runtime": 23, "steps": 5}
