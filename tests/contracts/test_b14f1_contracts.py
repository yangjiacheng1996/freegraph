# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B14F1 · L4 导出面 / 依赖方向 / 零扩张。"""

from __future__ import annotations

import dataclasses
import importlib
import subprocess
import sys
from pathlib import Path

from freegraph.contracts import Checkpointer
from freegraph.contracts.trace import Span
from freegraph.contracts.types import RunConfig, StateSnapshot

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PERSISTENCE = _REPO_ROOT / "src" / "freegraph" / "persistence"


def test_public_exports_and_alias() -> None:
    persistence = importlib.import_module("freegraph.persistence")

    assert persistence.__all__ == [
        "MemorySaver",
        "InMemorySaver",
        "CheckpointTuple",
        "SqliteSaver",
    ]
    assert persistence.InMemorySaver is persistence.MemorySaver
    assert persistence.CheckpointTuple is not None
    assert persistence.SqliteSaver is not None


def test_checkpoint_tuple_has_exactly_three_fields() -> None:
    persistence = importlib.import_module("freegraph.persistence")
    assert [
        field.name for field in dataclasses.fields(persistence.CheckpointTuple)
    ] == ["snapshot", "pending_writes", "scheduler"]


def test_l1_surfaces_are_unchanged() -> None:
    assert len(StateSnapshot.__dataclass_fields__) == 8
    assert len(RunConfig.__dataclass_fields__) == 9
    assert len(Span.__dataclass_fields__) == 11
    for name in (
        "get_tuple",
        "list",
        "put",
        "put_writes",
        "delete_thread",
        "delete_for_runs",
        "copy_thread",
        "get_next_version",
    ):
        assert hasattr(Checkpointer, name)


def test_persistence_source_has_no_forbidden_imports_or_io() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(_PERSISTENCE.glob("*.py"))
    )
    for marker in (
        "langchain",
        "langgraph",
        "langsmith",
        "import requests",
        "import urllib",
        "import socket",
        "os.environ",
        "os.getenv",
    ):
        assert marker not in source, marker


def test_importing_persistence_does_not_load_l2_l3_l5() -> None:
    code = """
import sys
import freegraph.persistence
for name in ("freegraph.runtime", "freegraph.observability", "freegraph.graph"):
    assert name not in sys.modules, name
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_facade_does_not_export_memory_saver() -> None:
    facade = importlib.import_module("freegraph.graph")
    assert not hasattr(facade, "MemorySaver")
    assert "MemorySaver" not in getattr(facade, "__all__", ())


def test_facade_does_not_export_sqlite_saver() -> None:
    """B15F1 · R-2：``SqliteSaver`` 只在 L4 公开，门面 **MUST NOT** 转出（G18）。"""
    facade = importlib.import_module("freegraph.graph")
    assert not hasattr(facade, "SqliteSaver")
    assert "SqliteSaver" not in getattr(facade, "__all__", ())
