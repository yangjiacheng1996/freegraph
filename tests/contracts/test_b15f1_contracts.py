# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · 导出面 / 依赖方向 / L1 注解 / 零 env / 零出站。"""

from __future__ import annotations

import importlib
from pathlib import Path
from collections.abc import Mapping
from typing import Any, get_type_hints

from freegraph.contracts import CompiledGraph, RunConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
PERSISTENCE = REPO_ROOT / "src" / "freegraph" / "persistence"


def test_public_exports() -> None:
    persistence = importlib.import_module("freegraph.persistence")
    assert "SqliteSaver" in persistence.__all__
    assert persistence.SqliteSaver is not None

    facade = importlib.import_module("freegraph.graph")
    assert not hasattr(facade, "SqliteSaver")
    assert "SqliteSaver" not in getattr(facade, "__all__", ())


def test_l4_does_not_import_upper_layers() -> None:
    forbidden = (
        "freegraph.runtime",
        "freegraph.observability",
        "freegraph.graph",
        "freegraph._stategraph",
        "langchain",
        "langgraph",
        "langsmith",
    )
    for path in PERSISTENCE.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert f"import {token}" not in source, (path.name, token)
            assert f"from {token}" not in source, (path.name, token)


def test_sqlite_saver_has_no_env_or_egress() -> None:
    for name in ("sqlite.py", "_json.py"):
        source = (PERSISTENCE / name).read_text(encoding="utf-8")
        for token in (
            "os.environ",
            "getenv",
            "requests",
            "urlopen",
            "socket",
        ):
            assert token not in source, (name, token)


def test_l1_config_annotations_are_widened() -> None:
    expected = RunConfig | Mapping[str, Any] | None
    for method in (CompiledGraph.get_state, CompiledGraph.get_state_history):
        hints = get_type_hints(method)
        assert hints["config"] == expected
    # return annotations unchanged (get_state still returns StateSnapshot | None)
    state_return = str(get_type_hints(CompiledGraph.get_state)["return"])
    assert "StateSnapshot" in state_return
    assert "None" in state_return


def test_no_new_contract_exceptions() -> None:
    contracts = importlib.import_module("freegraph.contracts")
    exported = set(getattr(contracts, "__all__", ()))
    exception_names = {
        name
        for name in exported
        if isinstance(getattr(contracts, name), type)
        and issubclass(getattr(contracts, name), BaseException)
    }
    # B15F1 MUST NOT add new L1 exception types (frozen surface).
    assert exception_names == {
        "FreegraphError",
        "InvalidUpdateError",
        "GraphRecursionError",
        "GraphInterrupt",
    }
