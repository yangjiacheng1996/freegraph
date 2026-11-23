# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · L1 注解 / 返回类别 / 导出面 / 零依赖 / 零 env / 零出站 / ARCH-1。"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict, get_type_hints

import pytest

from freegraph.contracts import CompiledGraph, RunConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src" / "freegraph"
RUNTIME = SRC / "runtime"


def test_update_state_l1_annotation_and_return() -> None:
    hints = get_type_hints(CompiledGraph.update_state)
    assert hints["config"] == (RunConfig | Mapping[str, Any] | None)
    assert hints["return"] is RunConfig
    assert hints["values"] is not None
    assert hints["as_node"] == (str | None)


def test_update_state_is_delivered_and_returns_run_config() -> None:
    graph_module = importlib.import_module("freegraph.graph")
    END = graph_module.END
    START = graph_module.START
    StateGraph = graph_module.StateGraph
    MemorySaver = importlib.import_module("freegraph.persistence").MemorySaver

    class State(TypedDict):
        pass

    def node(state: dict) -> dict:
        return {}

    graph = StateGraph(State)
    graph.add_node("a", node)
    graph.add_edge(START, "a")
    graph.add_edge("a", END)

    no_saver = graph.compile()
    with pytest.raises(ValueError, match="No checkpointer set"):
        no_saver.update_state({"thread_id": "t"}, {})

    compiled = graph.compile(checkpointer=MemorySaver())
    compiled.invoke({}, {"thread_id": "t"})
    new_config = compiled.update_state({"thread_id": "t"}, {})
    assert isinstance(new_config, RunConfig)
    assert new_config.configurable["checkpoint_id"]


def test_no_new_l1_exception_types() -> None:
    contracts = importlib.import_module("freegraph.contracts")
    exported = set(getattr(contracts, "__all__", ()))
    exception_names = {
        name
        for name in exported
        if isinstance(getattr(contracts, name), type)
        and issubclass(getattr(contracts, name), BaseException)
    }
    assert exception_names == {
        "FreegraphError",
        "InvalidUpdateError",
        "GraphRecursionError",
        "GraphInterrupt",
    }


def test_persistence_exports_and_facade_stay_unchanged() -> None:
    persistence = importlib.import_module("freegraph.persistence")
    assert set(persistence.__all__) == {
        "MemorySaver",
        "InMemorySaver",
        "CheckpointTuple",
        "SqliteSaver",
    }
    facade = importlib.import_module("freegraph.graph")
    assert not hasattr(facade, "MemorySaver")
    assert "MemorySaver" not in getattr(facade, "__all__", ())


def test_time_travel_module_is_l2_and_has_no_upper_or_third_party_imports() -> None:
    path = RUNTIME / "_time_travel.py"
    source = path.read_text(encoding="utf-8")
    forbidden = (
        "freegraph.persistence",
        "freegraph.graph",
        "freegraph._stategraph",
        "langchain",
        "langgraph",
        "langsmith",
    )
    for token in forbidden:
        assert f"import {token}" not in source, token
        assert f"from {token}" not in source, token


def test_runtime_and_persistence_have_no_env_or_egress() -> None:
    paths = [RUNTIME / "_time_travel.py", SRC / "persistence" / "memory.py", SRC / "persistence" / "sqlite.py"]
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for token in ("os.environ", "getenv", "requests", "urlopen", "socket"):
            assert token not in source, (path.name, token)


def test_update_state_boundary_symbols_remain_unimplemented() -> None:
    saver = importlib.import_module("freegraph.persistence").MemorySaver()
    with pytest.raises(NotImplementedError):
        saver.delete_for_runs([])
    with pytest.raises(NotImplementedError):
        saver.copy_thread("a", "b")
