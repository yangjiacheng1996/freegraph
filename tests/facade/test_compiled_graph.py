# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B7F2 编译产物测试：能力面 / 注入项 / 快照 / 通道模板 / 零副作用 / 文档。

覆盖 T014 / T015 / T018 / T019 / T020 / T031 / T032 / T033 / T034 / T036 /
T037 / T038 / T043b。
"""

from __future__ import annotations

import ast
import socket
from pathlib import Path
from typing import Annotated, Any, TypedDict

import pytest

from freegraph.graph import END, START, StateGraph
from freegraph.runtime import GraphSpec

from ._builder_support import CallCounter, RichState, State, node_a, node_b, router
from ._compiled_support import (
    SENTINEL_CACHE,
    SENTINEL_CHECKPOINTER,
    SENTINEL_STORE,
    SENTINEL_TRANSFORMERS,
    build_minimal_graph,
    capture_warnings,
    normalized_summary,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
STATEGRAPH_SOURCE = REPO_ROOT / "src" / "freegraph" / "_stategraph.py"

CAPABILITY_METHODS = (
    "invoke",
    "stream",
    "get_graph",
    "get_state",
    "get_state_history",
    "update_state",
)


class _Reducer:
    """归约器调用计数（compile MUST NOT 调用它）。"""

    calls = 0

    @staticmethod
    def apply(left: Any, right: Any) -> Any:
        _Reducer.calls += 1
        return right


class ReducerState(TypedDict):
    items: Annotated[list[int], _Reducer.apply]


# ── T014 · 能力面（SC-001 / SC-004）───────────────────────────────────────


class TestCapabilitySurface:
    def test_compile_no_arguments_returns_a_non_null_product(self) -> None:
        compiled = build_minimal_graph().compile()
        assert compiled is not None

    def test_all_six_capability_methods_exist(self) -> None:
        compiled = build_minimal_graph().compile()
        for name in CAPABILITY_METHODS:
            assert hasattr(compiled, name), name

    def test_each_unready_method_raises_not_implemented_naming_owner(self) -> None:
        compiled = build_minimal_graph().compile()
        calls = {
            "get_state": (({},), "B15F1"),
            "get_state_history": (({},), "B15F1"),
            "update_state": (({}, {}), "B16F1"),
        }
        for name, (args, owner) in calls.items():
            with pytest.raises(NotImplementedError) as excinfo:
                getattr(compiled, name)(*args)
            assert owner in str(excinfo.value), (name, str(excinfo.value))

    def test_get_graph_is_delivered(self) -> None:
        """B22F1：``get_graph`` 返回自有 ``Graph``。"""
        from freegraph.contracts.graph import Graph

        compiled = build_minimal_graph().compile()
        assert isinstance(compiled.get_graph(), Graph)

    def test_invoke_is_delivered_and_does_not_raise_not_implemented(self) -> None:
        """**B7F3 已交付** ⇒ ``invoke()`` 在合法路径上 MUST **不**抛 ``NotImplementedError``。

        ⚠️ **拆分而不删**（B7F3 · 破冻结面 · 追认项 ⑤）：原断言把 ``invoke`` 与其余
        **5 个**未就绪方法**并列**在参数化列表里 ⇒ ⇒ 本条**从列表中提出** ⇒ ⇒
        改为**独立断言**（语义**不删**）⇒ ⇒ 其余 **5** 条目**逐字不动**。
        """
        compiled = build_minimal_graph().compile()
        try:
            compiled.invoke({})
        except NotImplementedError as exc:  # pragma: no cover - 失败路径
            pytest.fail(f"invoke 已由 B7F3 交付，不应抛 NotImplementedError：{exc}")

    def test_stream_is_delivered_and_yields_events(self) -> None:
        """**B8F2 已交付** ⇒ ``stream()`` 返回惰性事件迭代器且可消费。"""
        compiled = build_minimal_graph().compile()
        events = list(compiled.stream({}, stream_mode="updates"))
        assert events
        assert all(set(event) == {"stream_mode", "payload", "run_id", "thread_id"} for event in events)

    def test_zero_attribute_error(self) -> None:
        compiled = build_minimal_graph().compile()
        for name in CAPABILITY_METHODS:
            # 取属性本身 MUST NOT 抛 AttributeError（未就绪是「调用时」的信号）
            assert callable(getattr(compiled, name))


# ── T015 · 产物形状（12 键 / 公开属性默认值）──────────────────────────────


class TestProductShape:
    PRIVATE = {"_spec", "_builder_spec", "_conditional_edges", "_tracer"}
    PUBLIC = {
        "checkpointer",
        "store",
        "cache",
        "debug",
        "name",
        "transformers",
        "interrupt_before_nodes",
        "interrupt_after_nodes",
    }

    def test_vars_is_exactly_the_eleven_frozen_keys(self) -> None:
        compiled = build_minimal_graph().compile()
        assert set(vars(compiled)) == self.PRIVATE | self.PUBLIC
        assert len(vars(compiled)) == 12

    def test_public_attributes_are_instance_attributes(self) -> None:
        compiled = build_minimal_graph().compile()
        # 若用 @property，则 vars() 看不到它们 ⇒ 该断言失败
        for name in self.PUBLIC:
            assert name in vars(compiled), name

    def test_public_default_values(self) -> None:
        compiled = build_minimal_graph().compile()
        assert compiled.debug is False
        assert compiled.name is None
        assert compiled.interrupt_before_nodes == ()
        assert compiled.interrupt_after_nodes == ()
        assert compiled.checkpointer is None
        assert compiled.store is None
        assert compiled.cache is None
        assert compiled.transformers is None


# ── T018 / T019 / T020 · 注入项（SC-002 / SC-015）─────────────────────────


class TestInjections:
    def test_compile_with_none_injections_does_not_raise_type_error(self) -> None:
        build_minimal_graph().compile()
        build_minimal_graph().compile(checkpointer=None, store=None)

    def test_injection_identities_are_preserved(self) -> None:
        with capture_warnings():
            compiled = build_minimal_graph().compile(
                checkpointer=SENTINEL_CHECKPOINTER,
                store=SENTINEL_STORE,
                cache=SENTINEL_CACHE,
                transformers=SENTINEL_TRANSFORMERS,
            )
        assert compiled.checkpointer is SENTINEL_CHECKPOINTER
        assert compiled.store is SENTINEL_STORE
        assert compiled.cache is SENTINEL_CACHE
        assert compiled.transformers is SENTINEL_TRANSFORMERS

    def test_falsy_values_are_accepted(self) -> None:
        with capture_warnings() as caught:
            compiled = build_minimal_graph().compile(checkpointer=False, store=0)
        assert compiled.checkpointer is False
        assert compiled.store == 0
        assert len(caught) == 1  # store 非 None ⇒ 恰好 1 条

    def test_non_store_objects_are_accepted(self) -> None:
        build_minimal_graph().compile(checkpointer=object())
        with capture_warnings():
            build_minimal_graph().compile(store=object())

    def test_store_non_none_emits_exactly_one_warning(self) -> None:
        with capture_warnings() as caught:
            build_minimal_graph().compile(store=object())
        assert len(caught) == 1
        assert "v1 不支持 Store" in str(caught[0].message)

    def test_store_none_emits_zero_warnings(self) -> None:
        with capture_warnings() as caught:
            build_minimal_graph().compile(store=None)
        assert caught == []

    @pytest.mark.parametrize(
        "keyword",
        ["checkpointer", "cache", "transformers", "debug", "name"],
    )
    def test_non_store_injections_emit_zero_warnings(self, keyword: str) -> None:
        value: Any = False if keyword == "debug" else object()
        with capture_warnings() as caught:
            build_minimal_graph().compile(**{keyword: value})
        assert caught == []

    def test_all_six_keywords_are_readable(self) -> None:
        sentinels = {
            "checkpointer": SENTINEL_CHECKPOINTER,
            "store": SENTINEL_STORE,
            "cache": SENTINEL_CACHE,
            "debug": True,
            "name": "my-graph",
            "transformers": SENTINEL_TRANSFORMERS,
        }
        with capture_warnings() as caught:
            compiled = build_minimal_graph().compile(**sentinels)
        assert compiled.checkpointer is SENTINEL_CHECKPOINTER
        assert compiled.store is SENTINEL_STORE
        assert compiled.cache is SENTINEL_CACHE
        assert compiled.debug is True
        assert compiled.name == "my-graph"
        assert compiled.transformers is SENTINEL_TRANSFORMERS
        assert len(caught) == 1


# ── T031 · 快照隔离（SC-012）──────────────────────────────────────────────


class TestSnapshotIsolation:
    def test_builder_mutation_after_compile_does_not_change_the_product(self) -> None:
        graph = build_minimal_graph()
        compiled = graph.compile()
        before = list(compiled._spec.nodes)
        graph.add_node("late", node_a)
        assert list(compiled._spec.nodes) == before

    def test_two_compiles_return_independent_products(self) -> None:
        graph = build_minimal_graph()
        first = graph.compile()
        second = graph.compile()
        assert first is not second
        assert first._spec is not second._spec
        assert first._spec.nodes is not second._spec.nodes
        assert first._spec.edges is not second._spec.edges

    def test_post_compile_mutation_emits_no_warning(self) -> None:
        graph = build_minimal_graph()
        graph.compile()
        with capture_warnings() as caught:
            graph.add_node("late", node_a)
            graph.add_edge("late", END)
        assert caught == []


# ── T032 · 通道模板（SC-011）──────────────────────────────────────────────


class TestChannelTemplates:
    def test_spec_and_builder_channels_are_distinct_mappings(self) -> None:
        compiled = build_minimal_graph().compile()
        assert compiled._spec.channels is not compiled._builder_spec.channels

    def test_every_channel_is_an_unwritten_template(self) -> None:
        compiled = build_minimal_graph().compile()
        fresh = build_minimal_graph().compile()
        for key, channel in compiled._spec.channels.items():
            assert channel.checkpoint() == fresh._spec.channels[key].checkpoint()

    def test_graphspec_conditional_edges_carries_the_l3_payload(self) -> None:
        """**2026-11-18 · B8F1 回溯修订**（破冻结面 · 冻结断言 ④ · **替换为反面断言**）。

        ⚠️ **原断言**「``GraphSpec.conditional_edges`` **恒空**」⇒ ⇒ ⇒ **自 B8F1
        起**该字段**承载** L3 产出的 plain mapping（**V-8 已放宽** · 裁定 14）
        ⇒ ⇒ ⇒ **替换为反面断言**：**非空**且与 ``compiled._conditional_edges``
        **逐字相等** ⇒ ⇒ ⇒ **判据只可更严**（恒空 ⇒ 非空且一致）⇒ ⇒ ⇒
        **「产物持有条件边」的语义留存**（**拆分而不删**）。

        ⚠️ **零新增私有字段** ⇒ ⇒ ⇒ ``vars(compiled)`` 的键数 == **12**（B19F1 新增私有 `_tracer`）
        （**T-3 不破** ⇒ ``:111-114`` 的既有断言**逐字不动**）。
        """
        compiled = build_minimal_graph(conditional=True).compile()
        assert compiled._spec.conditional_edges != {}
        assert compiled._spec.conditional_edges == compiled._conditional_edges


# ── T033 · 冻结载体（SC-010）──────────────────────────────────────────────


class TestFrozenCarriers:
    def test_three_private_field_names_and_types(self) -> None:
        compiled = build_minimal_graph().compile()
        assert isinstance(compiled._spec, GraphSpec)
        assert hasattr(compiled._builder_spec, "node_records")
        assert isinstance(compiled._conditional_edges, dict)

    def test_builder_spec_keeps_complete_node_records(self) -> None:
        compiled = build_minimal_graph().compile()
        assert set(compiled._builder_spec.node_records) == {"a", "b"}

    def test_conditional_mapping_has_five_frozen_keys_and_registration_order(self) -> None:
        graph = StateGraph(State)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge(START, "a")
        graph.add_conditional_edges("a", router, ["b", END])
        graph.add_edge("b", END)
        compiled = graph.compile()

        assert list(compiled._conditional_edges) == ["a"]
        items = compiled._conditional_edges["a"]
        assert len(items) == 1
        assert tuple(items[0]) == (
            "branch",
            "path",
            "path_map",
            "targets",
            "route_channels",
        )
        assert items[0]["branch"] == "router"
        assert items[0]["targets"] == ("b", "__end__")
        assert items[0]["route_channels"] == ("branch:to:b",)


# ── T034 · 顺序与确定性（SC-009 / SC-012）────────────────────────────────


class TestOrderAndDeterminism:
    def test_channel_key_order_is_schema_then_route_channels(self) -> None:
        graph = StateGraph(RichState)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge(START, "a")
        graph.add_conditional_edges("a", router, ["b", END])
        graph.add_edge("b", END)
        compiled = graph.compile()
        assert list(compiled._spec.channels) == ["first", "second", "branch:to:b"]

    def test_node_order_is_registration_order(self) -> None:
        compiled = build_minimal_graph().compile()
        assert list(compiled._spec.nodes) == ["a", "b"]

    def test_edge_order_preserved_after_end_filtering(self) -> None:
        compiled = build_minimal_graph().compile()
        assert list(compiled._spec.edges) == [START, "a"]
        assert compiled._spec.edges[START] == ("a",)
        assert compiled._spec.edges["a"] == ("b",)

    def test_two_compiles_are_structurally_equivalent(self) -> None:
        graph = build_minimal_graph()
        first = normalized_summary(graph.compile())
        second = normalized_summary(graph.compile())
        for key in ("channels", "nodes", "edges", "conditional_edges"):
            assert first[key] == second[key]
        assert first["interrupt_before"] == second["interrupt_before"]
        assert first["interrupt_after"] == second["interrupt_after"]


# ── T036 · 零用户函数调用（SC-005）────────────────────────────────────────


class TestZeroUserCalls:
    def test_compile_does_not_call_nodes_routers_or_reducers(self) -> None:
        counter = CallCounter()
        _Reducer.calls = 0
        graph = StateGraph(ReducerState)
        graph.add_node("a", counter.node("a"))
        graph.add_node("b", counter.node("b"))
        graph.add_edge(START, "a")
        graph.add_conditional_edges("a", counter.router("r", "b"), ["b", END])
        graph.add_edge("b", END)

        graph.compile()

        assert counter.counts == {}
        assert _Reducer.calls == 0


# ── T037 · 零环境变量 / 零出站（SC-005）──────────────────────────────────


class TestEnvironmentAndEgress:
    def test_environment_variables_do_not_change_compile_behaviour(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LANGSMITH_TRACING", "true")
        monkeypatch.setenv("LANGCHAIN_DEBUG", "true")
        monkeypatch.setenv("LANGGRAPH_DEBUG", "true")
        compiled = build_minimal_graph().compile()
        assert compiled.debug is False
        assert set(vars(compiled)) == set(vars(build_minimal_graph().compile()))

    def test_compile_opens_no_socket(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _boom(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("compile MUST NOT open a socket")

        monkeypatch.setattr(socket, "socket", _boom)
        monkeypatch.setattr(socket, "create_connection", _boom)
        build_minimal_graph().compile()


# ── T038 · 导入面（SC-005 / FR-023）──────────────────────────────────────


class TestImportSurface:
    FORBIDDEN_IMPORTS = {
        "langchain",
        "langchain_core",
        "langgraph",
        "langsmith",
        "socket",
        "urllib",
        "http",
        "subprocess",
    }

    def test_no_forbidden_imports_or_environment_reads(self) -> None:
        tree = ast.parse(STATEGRAPH_SOURCE.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in self.FORBIDDEN_IMPORTS
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                assert module not in self.FORBIDDEN_IMPORTS
            elif isinstance(node, ast.Attribute):
                assert not (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "os"
                    and node.attr in {"environ", "environb", "getenv"}
                )


# ── T043b · README 文档面（SC-015）───────────────────────────────────────


class TestReadmeDocumentation:
    def test_readme_states_store_and_checkpointer_boundaries(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "v1 不支持 `Store`" in readme
        assert "checkpointer 的行为归 B14F1" in readme
