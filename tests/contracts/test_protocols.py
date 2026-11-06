# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**五个协议**的契约面断言 —— 方法集 / 纯抽象 / 结构化子类型判定。

覆盖 US1（``NodeFunc`` / ``Checkpointer`` / ``Store``）与
US5（``CompiledGraph`` + 三协议「同时满足」的一致性断言）。

> **方法集一律以「集合相等」判定**——MUST NOT 断言成员的**定义顺序**
> （``typing.Protocol`` 的成员集合是 ``set``，其迭代顺序随
> ``PYTHONHASHSEED`` 变化，按序断言必然 flaky）。
"""

from __future__ import annotations

import importlib.util
import inspect
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

import pytest

from freegraph.contracts import (
    Checkpointer,
    Command,
    CompiledGraph,
    NodeFunc,
    StateDict,
    StateSnapshot,
    Store,
    TraceSink,
)

#: 五个协议的方法集（**集合**）——与 ``contracts/public-api.md`` §1.1 一致。
CHECKPOINTER_METHODS = {
    "get_tuple",
    "list",
    "put",
    "put_writes",
    "delete_thread",
    "get_next_version",
}

STORE_METHODS = {
    "get",
    "search",
    "put",
    "delete",
    "list_namespaces",
    "batch",
}


def _protocol_methods(proto: type) -> set[str]:
    """取协议的方法集（**集合**，不判顺序）。

    ``typing.Protocol.__protocol_attrs__`` 是 ``set``（CPython 3.11 / 3.12 实测）——
    这正是「成员定义顺序 MUST NOT 纳入冻结面」的根因。
    旧版本 Python 无该属性时，退回按 ``vars()`` 过滤（兜底，非主路径）。
    """
    attrs = getattr(proto, "__protocol_attrs__", None)
    if attrs is not None:
        return set(attrs)
    excluded = {
        "__abstractmethods__",
        "__annotations__",
        "__dict__",
        "__doc__",
        "__init__",
        "__module__",
        "__new__",
        "__parameters__",
        "__slots__",
        "__subclasshook__",
        "__weakref__",
        "__class_getitem__",
        "_is_protocol",
        "_is_runtime_protocol",
    }
    return {
        name
        for name in vars(proto)
        if name not in excluded and not name.startswith("_abc_")
    }


def _partial_protocol(protocol: type, missing: str) -> type:
    """造一个**缺 ``missing`` 方法**的实现类（其余方法齐备）。

    「缺实现」必须被结构化子类型判定**判假**——这是 FR-007 的核心判据：
    默认实现会让只声明部分方法的假实现**静默通过**。
    """
    namespace: dict[str, Any] = {}
    for name in _protocol_methods(protocol):
        if name == missing:
            continue
        namespace[name] = lambda self, *args, **kwargs: None
    return type(f"Partial{protocol.__name__}", (), namespace)


# ── US1 · NodeFunc ─────────────────────────────────────────────────────


class TestNodeFunc:
    """US1 · 节点函数协议 —— 只有 ``__call__`` 一个成员。"""

    def test_only_call_is_a_member(self) -> None:
        """``NodeFunc`` 的成员集 MUST **恰为** ``{'__call__'}``。"""
        assert _protocol_methods(NodeFunc) == {"__call__"}

    def test_call_signature_is_frozen(self) -> None:
        """``__call__`` 的注解 MUST 逐字为 ``(state: StateDict) -> StateDict | Command | None``。"""
        hints = get_type_hints(NodeFunc.__call__)
        assert hints["state"] == StateDict
        assert hints["return"] == (StateDict | Command | None)

    def test_isinstance_is_available(self) -> None:
        """``runtime_checkable`` 生效 ⇒ 协议可做 ``isinstance`` 判定。"""
        def node(state: StateDict) -> StateDict:
            return state

        assert isinstance(node, NodeFunc)

    def test_non_callable_is_not_an_instance(self) -> None:
        """非可调用对象 MUST 判**假**。

        （``isinstance`` 对**任意可调用对象**恒为真——那是 ``__call__`` 协议的
        固有性质；「合法节点函数」由**静态类型检查**判定。）
        """
        assert not isinstance(object(), NodeFunc)


# ── US1 · Checkpointer ─────────────────────────────────────────────────


class TestCheckpointer:
    """US1 · 检查点协议 —— 恰 6 个方法、纯抽象、缺方法判假。"""

    def test_method_set_is_exactly_six(self) -> None:
        """方法集 MUST **集合恰为**那 6 个（不判顺序）。"""
        assert _protocol_methods(Checkpointer) == CHECKPOINTER_METHODS

    @pytest.mark.parametrize("missing", sorted(CHECKPOINTER_METHODS))
    def test_missing_any_method_is_not_an_instance(self, missing: str) -> None:
        """缺**任一**方法的实现 MUST 判**假**。"""
        partial = _partial_protocol(Checkpointer, missing)()
        assert not isinstance(partial, Checkpointer)


# ── US1 · Store ────────────────────────────────────────────────────────


class TestStore:
    """US1 · 长期存储协议 —— 恰 6 个方法、纯抽象、缺方法判假。"""

    def test_method_set_is_exactly_six(self) -> None:
        """方法集 MUST **集合恰为**那 6 个（不判顺序）。"""
        assert _protocol_methods(Store) == STORE_METHODS

    @pytest.mark.parametrize("missing", sorted(STORE_METHODS))
    def test_missing_any_method_is_not_an_instance(self, missing: str) -> None:
        """缺**任一**方法的实现 MUST 判**假**。"""
        partial = _partial_protocol(Store, missing)()
        assert not isinstance(partial, Store)


# ── US1 · 外部实现夹具（零内部依赖）────────────────────────────────────


class TestExternalImplementationIsAccepted:
    """US1 · 夹具中的完整实现 MUST 被判定为协议实例。"""

    def test_in_memory_checkpointer_satisfies_the_protocol(self) -> None:
        """假 checkpointer（**不继承任何 freegraph 基类**）MUST 判**真**。"""
        from fixtures.external_impl import InMemoryCheckpointer

        assert isinstance(InMemoryCheckpointer(), Checkpointer)

    def test_in_memory_store_satisfies_the_protocol(self) -> None:
        """假 store（**不继承任何 freegraph 基类**）MUST 判**真**。"""
        from fixtures.external_impl import InMemoryStore

        assert isinstance(InMemoryStore(), Store)

    def test_partial_checkpointer_variants_are_rejected(self) -> None:
        """夹具的**缺方法变体** MUST 判**假**（逐个缺法都试）。"""
        from fixtures.external_impl import make_partial_checkpointer

        for missing in sorted(CHECKPOINTER_METHODS):
            assert not isinstance(make_partial_checkpointer(missing), Checkpointer)

    def test_partial_store_variants_are_rejected(self) -> None:
        """夹具的**缺方法变体** MUST 判**假**（逐个缺法都试）。"""
        from fixtures.external_impl import make_partial_store

        for missing in sorted(STORE_METHODS):
            assert not isinstance(make_partial_store(missing), Store)

    def test_fixture_implementations_expose_the_frozen_method_sets(self) -> None:
        """夹具实现 MUST 暴露与协议**逐字相同**的方法集。"""
        from fixtures.external_impl import InMemoryCheckpointer, InMemoryStore

        assert set(vars(InMemoryCheckpointer)) >= CHECKPOINTER_METHODS
        assert set(vars(InMemoryStore)) >= STORE_METHODS


# ── US5 · CompiledGraph ────────────────────────────────────────────────

#: ``CompiledGraph`` 的方法集（**6 个**）——``data-model.md`` §2.5。
COMPILED_GRAPH_METHODS = {
    "invoke",
    "stream",
    "get_graph",
    "get_state",
    "get_state_history",
    "update_state",
}


class TestCompiledGraph:
    """US5 · 编译产物能力面 —— 恰 6 个方法、返回类别逐条冻结。"""

    def test_method_set_is_exactly_six(self) -> None:
        """方法集 MUST **集合恰为**那 6 个（不判顺序）。"""
        assert _protocol_methods(CompiledGraph) == COMPILED_GRAPH_METHODS

    def test_get_graph_xray_is_keyword_only_with_false_default(self) -> None:
        """``get_graph`` 的 ``xray`` MUST 是**关键字参数**且缺省 ``False``。"""
        parameter = inspect.signature(CompiledGraph.get_graph).parameters["xray"]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is False

    def test_get_state_returns_none_when_not_found(self) -> None:
        """``get_state`` 的返回注解 MUST 含 ``None``（查不到返回空值）。"""
        hints = get_type_hints(CompiledGraph.get_state)
        assert hints["return"] == (StateSnapshot | None)

    def test_stream_yields_pure_data_dicts(self) -> None:
        """``stream`` 的返回注解元素类型 MUST 是 ``dict[str, Any]``（**非** ``Any``）。"""
        hints = get_type_hints(CompiledGraph.stream)
        return_type = hints["return"]
        assert get_origin(return_type) is Iterator
        assert get_args(return_type) == (dict[str, Any],)

    @pytest.mark.parametrize("missing", sorted(COMPILED_GRAPH_METHODS))
    def test_missing_any_method_is_not_an_instance(self, missing: str) -> None:
        """缺**任一**方法的实现 MUST 判**假**。"""
        partial = _partial_protocol(CompiledGraph, missing)()
        assert not isinstance(partial, CompiledGraph)


class TestThreeProtocolsAreSimultaneouslySatisfiable:
    """US5 · 一个**零内部依赖**的夹具 MUST 能**同时**满足三个协议。"""

    def test_single_fixture_satisfies_all_three(self) -> None:
        """同一份夹具实现 MUST 同时判真于 ``Checkpointer`` / ``TraceSink`` / ``Store``。"""
        from fixtures.external_impl import (  # noqa: PLC0415
            InMemoryCheckpointer,
            InMemoryStore,
            RecordingTraceSink,
        )

        assert isinstance(InMemoryCheckpointer(), Checkpointer)
        assert isinstance(RecordingTraceSink(), TraceSink)
        assert isinstance(InMemoryStore(), Store)

    def test_conformance_helper_accepts_the_concrete_implementations(self) -> None:
        """夹具的一致性断言 MUST 接受三个**具体实现类**（静态检查的落点）。"""
        from fixtures.external_impl import (  # noqa: PLC0415
            prove_conformance_with_concrete_implementations,
        )

        assert prove_conformance_with_concrete_implementations() is None


class TestAnnotationStructureFallback:
    """US5 · **注解结构兜底断言**（不依赖 mypy，任何环境都跑）。

    比对夹具实现与协议本身的**方法名 / 参数名 / 参数顺序 / 注解**——
    挡「签名写错」这类最常见的失守。**不替代**静态类型检查（SC-004 以 mypy 为准）。
    """

    @pytest.mark.parametrize(
        ("protocol", "implementation", "methods"),
        [
            (
                Checkpointer,
                "InMemoryCheckpointer",
                (
                    "get_tuple",
                    "list",
                    "put",
                    "put_writes",
                    "delete_thread",
                    "get_next_version",
                ),
            ),
            (
                TraceSink,
                "RecordingTraceSink",
                ("on_span_start", "on_span_end", "current_span"),
            ),
            (
                Store,
                "InMemoryStore",
                ("get", "search", "put", "delete", "list_namespaces", "batch"),
            ),
        ],
    )
    def test_fixture_signatures_match_the_protocols(
        self, protocol: type, implementation: str, methods: tuple[str, ...]
    ) -> None:
        """夹具的方法签名 MUST 与协议**逐字相同**（名 / 参数名 / 参数顺序 / 注解）。"""
        import fixtures.external_impl as fixture  # noqa: PLC0415

        cls = getattr(fixture, implementation)
        for name in methods:
            protocol_params, protocol_hints = _signature_of(protocol, name)
            fixture_params, fixture_hints = _signature_of(cls, name)
            assert fixture_params == protocol_params, (
                f"{implementation}.{name} 的参数（名 / 顺序 / 形态）与协议不一致："
                f"{fixture_params} != {protocol_params}"
            )
            assert fixture_hints == protocol_hints, (
                f"{implementation}.{name} 的注解与协议不一致："
                f"{fixture_hints} != {protocol_hints}"
            )


def _signature_of(cls: type, name: str) -> tuple[list[tuple[str, Any]], dict[str, Any]]:
    """取一个方法的**参数（名 / 形态 / 顺序）**与**注解**。

    方法名与参数顺序用 ``inspect.signature`` 取（``typing.get_type_hints`` 取的是
    **类级注解**，拿不到方法签名）；注解用 ``typing.get_type_hints`` 取。
    """
    method = getattr(cls, name)
    signature = inspect.signature(method)
    params = [
        (parameter.name, parameter.kind) for parameter in signature.parameters.values()
    ]
    return params, get_type_hints(method)


class TestStaticTypeCheck:
    """US5 · SC-004 · 静态类型检查（mypy）——**可选**开发期工具。"""

    def test_mypy_strict_accepts_the_fixture(self, repo_root: Path) -> None:
        """``mypy --strict`` MUST 对夹具**无错**。

        **前提**：夹具方法已按协议签名**写全类型注解**（``--strict`` 的
        ``disallow_untyped_defs`` 会把漏注解直接判错）。

        **mypy 缺失时该用例 ``skip``**（MUST NOT 失败）——mypy 是**开发期工具**
        且 ``freegraph`` 未安装 ⇒ 该判据不可执行。
        """
        if importlib.util.find_spec("mypy") is None:
            pytest.skip(
                "mypy 是**开发期工具**且 `freegraph` 未安装 ⇒ 该判据不可执行"
                "（本机未装 mypy；SC-004 的静态类型检查用例据此 skip，"
                "兜底的注解结构断言仍会跑）"
            )
        env = {**os.environ, "MYPYPATH": str(repo_root / "src")}
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "--strict",
                str(repo_root / "tests" / "contracts" / "fixtures" / "external_impl.py"),
            ],
            env=env,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert proc.returncode == 0, (
            f"mypy --strict 对夹具报错：\n{proc.stdout}\n{proc.stderr}"
        )
