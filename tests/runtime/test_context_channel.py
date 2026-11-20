# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B8F3 · US1 —— ``context`` 的 L2 载体、节点视图与 fan-out 边界。

契约权威：``specs/b8f3-node-alias-context/contracts/context-channel-contract.md``。

* ``context is None`` ⇒ 节点入参是**精确** ``dict``（C4 / I-1 不变）；
* ``context is not None`` ⇒ ``_ContextState``（``dict`` 子类 + 只读 ``.context``）；
* ``Send.arg`` 只包装 ``dict``；非 ``dict`` 原样；
* ``run_graph`` / ``StreamSession`` 的运行入口绑定 / 复原 context。
"""

from __future__ import annotations

from typing import Any, TypedDict

import pytest

from freegraph.contracts import Command, RunConfig, Send
from freegraph.graph import END, START, StateGraph
from freegraph.runtime import SchedulerState, run_graph
from freegraph.runtime._context import bind_context, get_context
from freegraph.runtime._stream import StreamSession


class _State(TypedDict):
    x: int


def _compiled(seen: dict) -> Any:
    def node(state: dict) -> dict:
        seen["state"] = state
        seen["context"] = getattr(state, "context", None)
        return {"x": 1}

    builder = StateGraph(_State)
    builder.add_node("n", node)
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    return builder.compile()


class TestNodeInputView:
    def test_no_context_keeps_exact_dict(self) -> None:
        seen: dict = {}
        compiled = _compiled(seen)

        run_graph(compiled._spec, {"x": 0})

        assert type(seen["state"]) is dict
        assert seen["context"] is None

    def test_context_wraps_with_readonly_attribute(self) -> None:
        seen: dict = {}
        compiled = _compiled(seen)
        ctx = {"user": "u1"}

        run_graph(compiled._spec, {"x": 0}, config=RunConfig(context=ctx))

        view = seen["state"]
        assert isinstance(view, dict)
        assert type(view) is not dict
        assert dict(view) == {"x": 0}
        assert view.context is ctx
        assert "context" not in view
        with pytest.raises(AttributeError):
            view.context = object()  # type: ignore[misc]

    def test_mapping_remains_mutable(self) -> None:
        seen: dict = {}
        compiled = _compiled(seen)

        run_graph(compiled._spec, {"x": 0}, config=RunConfig(context={"u": 1}))

        view = seen["state"]
        view["x"] = 2
        assert view["x"] == 2

    def test_unknown_attribute_raises(self) -> None:
        seen: dict = {}
        compiled = _compiled(seen)

        run_graph(compiled._spec, {"x": 0}, config=RunConfig(context={"u": 1}))

        with pytest.raises(AttributeError):
            _ = seen["state"].nope  # type: ignore[attr-defined]

    def test_context_is_not_a_state_channel(self) -> None:
        seen: dict = {}
        compiled = _compiled(seen)

        assert "context" not in compiled._spec.channels
        assert "context" not in SchedulerState().channels

        run_graph(compiled._spec, {"x": 0}, config=RunConfig(context={"u": 1}))
        assert "context" not in seen["state"]


class TestFanOutAndCommand:
    def test_send_dict_arg_is_wrapped(self) -> None:
        seen: dict = {}
        ctx = {"u": 1}

        def producer(state: dict) -> Send:
            return Send("worker", {"payload": 1})

        def worker(state: dict) -> dict:
            seen["state"] = state
            seen["context"] = getattr(state, "context", None)
            return {"x": 1}

        builder = StateGraph(_State)
        builder.add_node("producer", producer)
        builder.add_node("worker", worker)
        builder.add_edge(START, "producer")
        builder.add_edge("worker", END)
        builder.compile().invoke({"x": 0}, RunConfig(context=ctx))

        assert type(seen["state"]) is not dict
        assert dict(seen["state"]) == {"payload": 1}
        assert seen["context"] is ctx

    def test_send_non_dict_arg_is_unchanged(self) -> None:
        seen: dict = {}
        sentinel = object()

        def producer(state: dict) -> Send:
            return Send("worker", sentinel)

        def worker(state: Any) -> dict:
            seen["state"] = state
            return {"x": 1}

        builder = StateGraph(_State)
        builder.add_node("producer", producer)
        builder.add_node("worker", worker)
        builder.add_edge(START, "producer")
        builder.add_edge("worker", END)
        builder.compile().invoke({"x": 0}, RunConfig(context={"u": 1}))

        assert seen["state"] is sentinel
        assert not isinstance(seen["state"], dict)

    def test_command_goto_target_reads_context(self) -> None:
        seen: dict = {}
        ctx = {"u": 1}

        def producer(state: dict) -> Command:
            return Command(goto="worker")

        def worker(state: dict) -> dict:
            seen["context"] = getattr(state, "context", None)
            return {"x": 1}

        builder = StateGraph(_State)
        builder.add_node("producer", producer)
        builder.add_node("worker", worker)
        builder.add_edge(START, "producer")
        builder.add_edge("worker", END)
        builder.compile().invoke({"x": 0}, RunConfig(context=ctx))

        assert seen["context"] is ctx


class TestBindingLifecycle:
    def test_two_consecutive_runs_do_not_leak_context(self) -> None:
        seen: dict = {}
        compiled = _compiled(seen)

        run_graph(compiled._spec, {"x": 0}, config=RunConfig(context="one"))
        assert seen["context"] == "one"
        assert get_context() is None

        run_graph(compiled._spec, {"x": 0}, config=RunConfig(context="two"))
        assert seen["context"] == "two"
        assert get_context() is None

        run_graph(compiled._spec, {"x": 0})
        assert seen["context"] is None
        assert get_context() is None

    def test_stream_session_binds_and_restores_context(self) -> None:
        seen: dict = {}
        compiled = _compiled(seen)

        with StreamSession(
            compiled._spec, {"x": 0}, RunConfig(context="stream"), run_id="r1"
        ):
            assert get_context() == "stream"

        assert get_context() is None

    def test_bind_context_none_restores_inner_value(self) -> None:
        with bind_context("outer"):
            with bind_context(None):
                assert get_context() is None
            assert get_context() == "outer"
        assert get_context() is None


# ── US4 · 路由 / 流式 / 图导出口径不变 ──────────────────────────────────────


class TestRouteAndNaming:
    def test_route_fresh_view_has_no_context_but_raw_config_does(self) -> None:
        seen: dict = {}
        cfg = RunConfig(context={"route": 1})

        def route(state: dict, config) -> str:
            seen["state"] = state
            seen["config"] = config
            return "b"

        builder = StateGraph(_State)
        builder.add_node("a", lambda state: {"x": 1})
        builder.add_node("b", lambda state: {"x": 2})
        builder.add_edge(START, "a")
        builder.add_conditional_edges("a", route, ["b", END])
        builder.add_edge("b", END)
        out = builder.compile().invoke({"x": 0}, cfg)

        assert out == {"x": 2}
        assert type(seen["state"]) is dict
        assert "context" not in seen["state"]
        assert not hasattr(seen["state"], "context")
        assert seen["config"] is cfg
        assert seen["config"].context == {"route": 1}

    def test_stream_updates_and_tasks_use_internal_node_names(self) -> None:
        def route(state: dict, config) -> str:
            return "b"

        builder = StateGraph(_State)
        builder.add_node("a", lambda state: {"x": 1})
        builder.add_node("b", lambda state: {"x": 2})
        builder.add_edge(START, "a")
        builder.add_conditional_edges("a", route, ["b", END])
        builder.add_edge("b", END)
        compiled = builder.compile()

        updates = list(
            compiled.stream({}, RunConfig(context={"u": 1}), stream_mode="updates")
        )
        assert [set(event["payload"]) for event in updates] == [{"a"}, {"b"}]

        tasks = list(
            compiled.stream({}, RunConfig(context={"u": 1}), stream_mode="tasks")
        )
        assert {event["payload"].name for event in tasks} == {"a", "b"}

    def test_graph_export_uses_internal_node_names(self) -> None:
        builder = StateGraph(_State)
        builder.add_node("a", lambda state: {"x": 1})
        builder.add_node("b", lambda state: {"x": 2})
        builder.add_edge(START, "a")
        builder.add_edge("a", "b")
        builder.add_edge("b", END)
        graph = builder.compile().get_graph()

        node_pairs = {(node.id, node.name) for node in graph.nodes}
        assert ("a", "a") in node_pairs
        assert ("b", "b") in node_pairs
        assert all(node.id == node.name for node in graph.nodes)
