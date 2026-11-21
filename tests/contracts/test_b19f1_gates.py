# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · US3：零环境变量 / 零第三方依赖 / 零出站（契约层不 import 内部层）。"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path


def test_langsmith_environment_does_not_change_default_off(src_dir: Path) -> None:
    code = """
from typing import TypedDict
from freegraph.graph import END, START, StateGraph

class S(TypedDict, total=False):
    x: int

builder = StateGraph(S)
builder.add_node("a", lambda state: {"x": 1})
builder.add_edge(START, "a")
builder.add_edge("a", END)
assert builder.compile().invoke({"x": 0})["x"] == 1
print("ok")
"""
    env = {
        **os.environ,
        "PYTHONPATH": str(src_dir),
        "LANGSMITH_TRACING": "true",
        "LANGCHAIN_TRACING_V2": "true",
    }
    proc = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "ok"


def test_new_modules_have_no_forbidden_imports_or_env_reads(src_dir: Path) -> None:
    paths = [
        src_dir / "freegraph" / "observability" / "_record.py",
        src_dir / "freegraph" / "observability" / "_inject.py",
        src_dir / "freegraph" / "observability" / "_producer.py",
        src_dir / "freegraph" / "observability" / "_file_store.py",
        src_dir / "freegraph" / "observability" / "__init__.py",
        src_dir / "freegraph" / "runtime" / "_span_hook.py",
    ]
    forbidden_roots = {"langchain", "langgraph", "langsmith", "opentelemetry"}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden_roots, (path, alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden_roots, (path, node.module)
            elif isinstance(node, ast.Name) and node.id in {"environ", "getenv"}:
                raise AssertionError(f"{path} reads environment variable")


def test_no_network_client_is_used_by_new_modules(src_dir: Path) -> None:
    for name in ("_record.py", "_inject.py", "_producer.py", "_file_store.py"):
        text = (src_dir / "freegraph" / "observability" / name).read_text(encoding="utf-8")
        assert "socket" not in text
        assert "requests" not in text
