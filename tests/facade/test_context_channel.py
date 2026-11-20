# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B8F3 · US1 / US2 —— ``context`` 独立通道与 ``RunConfig`` 运行期接线。

契约权威：``specs/b8f3-node-alias-context/contracts/context-channel-contract.md``。

* US1：节点经 ``getattr(state, "context", None)`` 读到 ``RunConfig.context``；
  ``invoke`` 终态 / ``values`` 载荷无 ``context``；``context is None`` ⇒ 精确 ``dict``。
* US2：``RunConfig`` 九字段不变；``context`` 不塞进 ``configurable``。
"""

from __future__ import annotations

import dataclasses
from typing import TypedDict

import pytest

from freegraph.contracts import RunConfig
from freegraph.graph import END, START, StateGraph


class _State(TypedDict):
    x: int


def _single_node_graph(seen: dict) -> object:
    def node(state: dict) -> dict:
        seen["state"] = state
        seen["context"] = getattr(state, "context", None)
        return {"x": 1}

    builder = StateGraph(_State)
    builder.add_node("n", node)
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    return builder.compile()


# ── US1 · 运行时上下文独立传递 ───────────────────────────────────────────────


class TestContextChannel:
    def test_node_reads_context_and_state_has_no_context_key(self) -> None:
        seen: dict = {}
        compiled = _single_node_graph(seen)
        ctx = {"user": "u1"}

        out = compiled.invoke({"x": 0}, RunConfig(context=ctx))

        assert seen["context"] is ctx
        assert list(out) == ["x"]
        assert "context" not in out

    def test_values_stream_payload_has_no_context_key(self) -> None:
        seen: dict = {}
        compiled = _single_node_graph(seen)
        ctx = {"user": "u1"}

        events = list(
            compiled.stream(
                {"x": 0},
                RunConfig(context=ctx),
                stream_mode="values",
            )
        )

        assert seen["context"] is ctx
        assert events
        assert all("context" not in event["payload"] for event in events)

    def test_context_none_keeps_exact_dict_and_reads_none(self) -> None:
        seen: dict = {}
        compiled = _single_node_graph(seen)

        compiled.invoke({"x": 0})

        assert seen["context"] is None
        assert type(seen["state"]) is dict

    @pytest.mark.parametrize("context", [{}, 0, ""])
    def test_non_none_context_uses_dict_subclass_view(self, context: object) -> None:
        seen: dict = {}
        compiled = _single_node_graph(seen)

        compiled.invoke({"x": 0}, RunConfig(context=context))

        assert seen["context"] is context
        assert isinstance(seen["state"], dict)
        assert type(seen["state"]) is not dict

    def test_mapping_config_form_resolves_context(self) -> None:
        seen: dict = {}
        compiled = _single_node_graph(seen)

        compiled.invoke({"x": 0}, {"context": {"user": "u1"}})

        assert seen["context"] == {"user": "u1"}
        assert seen["context"] is not None

    def test_context_keyword_is_not_an_invoke_or_stream_parameter(self) -> None:
        seen: dict = {}
        compiled = _single_node_graph(seen)

        with pytest.raises(TypeError):
            compiled.invoke({"x": 0}, context={"user": "u1"})
        with pytest.raises(TypeError):
            compiled.stream({"x": 0}, context={"user": "u1"})


# ── US2 · context 与 configurable 的职责分离 ────────────────────────────────


class TestRunConfigBoundary:
    def test_run_config_keeps_exactly_nine_fields_in_order(self) -> None:
        names = tuple(field.name for field in dataclasses.fields(RunConfig))
        assert names == (
            "thread_id",
            "context",
            "metadata",
            "tags",
            "configurable",
            "max_concurrency",
            "recursion_limit",
            "run_name",
            "run_id",
        )

    def test_four_core_fields_are_readable_and_tags_is_tuple(self) -> None:
        cfg = RunConfig(
            thread_id="thread-1",
            context={"user": "u1"},
            metadata={"m": 1},
            tags=["t1"],
        )
        assert cfg.thread_id == "thread-1"
        assert cfg.context == {"user": "u1"}
        assert cfg.metadata == {"m": 1}
        assert cfg.tags == ("t1",)
        assert type(cfg.tags) is tuple

    def test_configurable_is_independent_and_never_carries_context(self) -> None:
        cfg = RunConfig(context={"user": "u1"})
        assert cfg.configurable == {}
        assert "context" not in cfg.configurable

    def test_node_view_has_no_injected_configurable_key(self) -> None:
        seen: dict = {}
        compiled = _single_node_graph(seen)

        compiled.invoke(
            {"x": 0},
            RunConfig(thread_id="t", context={"u": 1}, metadata={"m": 1}, tags=["a"]),
        )

        assert "configurable" not in seen["state"]
        assert not hasattr(seen["state"], "configurable")
        assert "thread_id" not in seen["state"]
        assert "metadata" not in seen["state"]
        assert "tags" not in seen["state"]
        assert seen["context"] == {"u": 1}

    def test_only_configurable_context_is_not_treated_as_context(self) -> None:
        seen: dict = {}
        compiled = _single_node_graph(seen)

        compiled.invoke({"x": 0}, {"configurable": {"context": {"user": "u1"}}})

        assert seen["context"] is None
        assert type(seen["state"]) is dict

    def test_context_schema_is_accepted_but_unused(self) -> None:
        seen: dict = {}

        def node(state: dict) -> dict:
            seen["context"] = getattr(state, "context", None)
            return {"x": 1}

        builder = StateGraph(_State, context_schema=dict)
        builder.add_node("n", node)
        builder.add_edge(START, "n")
        builder.add_edge("n", END)
        builder.compile().invoke({"x": 0}, RunConfig(context={"u": 1}))

        assert seen["context"] == {"u": 1}
