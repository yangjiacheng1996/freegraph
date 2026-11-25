# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · B25F1-D-04：模型形状入口 + 旧纯本地拒绝语义不变。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from freegraph.graph import END, START, StateGraph

from .spec_builder import GraphSpecError, build_graph_spec, build_model_graph_spec

_FACTORY_PATH = Path(__file__).with_name("_b25f1_model_factory.py")
_SPEC = importlib.util.spec_from_file_location("_b25f1_model_factory", _FACTORY_PATH)
assert _SPEC is not None and _SPEC.loader is not None
factory_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(factory_module)
FakeModelFactory = factory_module.FakeModelFactory


def test_build_model_graph_spec_is_executable() -> None:
    factory = FakeModelFactory(answer="ok")

    def llm_node(state: dict) -> dict:
        model = factory()
        return {
            "messages": list(state.get("messages", [])) + [model.invoke(state.get("messages"))],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    spec = build_model_graph_spec(
        name="B25F1ModelState",
        schema={"messages": (list, operator_add), "llm_calls": (int, None)},
        nodes=(("llm", llm_node),),
        initial_input={"messages": [], "llm_calls": 0},
        model_factory=factory,
    )
    assert spec.model_factory is factory
    assert spec.schema_typed is not None

    builder = StateGraph(spec.schema_typed)
    builder.add_node("llm", spec.nodes[0][1])
    builder.add_edge(START, "llm")
    builder.add_edge("llm", END)
    result = builder.compile().invoke(spec.initial_input)
    assert result["llm_calls"] == 1
    assert result["messages"] == ["ok"]
    assert factory.created and factory.created[0].calls == 1


def test_build_model_graph_spec_requires_non_empty_factory() -> None:
    with pytest.raises(GraphSpecError):
        build_model_graph_spec(
            name="B25F1EmptyFactory",
            schema={"value": (int, None)},
            nodes=(("n", lambda state: {}),),
            initial_input={"value": 0},
            model_factory=None,
        )
    with pytest.raises(GraphSpecError):
        build_model_graph_spec(
            name="B25F1EmptyFactory",
            schema={"value": (int, None)},
            nodes=(("n", lambda state: {}),),
            initial_input={"value": 0},
            model_factory=(),
        )


def test_pure_local_builder_still_rejects_non_empty_factory() -> None:
    with pytest.raises(GraphSpecError):
        build_graph_spec(
            name="B25F1PureLocal",
            schema={"value": (int, None)},
            nodes=(("n", lambda state: {}),),
            initial_input={"value": 0},
            model_factory=lambda: object(),
        )


def operator_add(left: list, right: list) -> list:
    return left + right
