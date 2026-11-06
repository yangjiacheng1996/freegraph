# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**图结构自有类型**的契约面断言 —— ``Graph`` / ``Node`` / ``Edge``。

覆盖 US3：字段清单逐字 / 缺省归一 / 冻结 / 不可哈希 / 字段级相等 /
JSON 可序列化 / 无对象引用字段。
"""

from __future__ import annotations

import json
import types
from collections.abc import Mapping
from dataclasses import FrozenInstanceError, asdict, fields
from typing import Any, Union, get_args, get_origin, get_type_hints

import pytest

from freegraph.contracts import Edge, Graph, Node

#: ``Node`` 的字段清单（**3 个**，逐字）——``data-model.md`` §3.1。
NODE_FIELDS = ["id", "name", "metadata"]

#: ``Edge`` 的字段清单（**4 个**，逐字）——``data-model.md`` §3.2。
EDGE_FIELDS = ["source", "target", "conditional", "condition"]

#: ``Graph`` 的字段清单（**2 个**，逐字）——``data-model.md`` §3.3。
GRAPH_FIELDS = ["nodes", "edges"]


# ── US3 · Node ─────────────────────────────────────────────────────────


class TestNode:
    """US3 · 图节点元素 —— 3 字段、别名归一、浅拷贝、不可变、不可哈希。"""

    def test_field_list_is_exactly_three(self) -> None:
        """字段清单 MUST **恰为**那 3 个（逐字）。"""
        assert [f.name for f in fields(Node)] == NODE_FIELDS

    def test_name_defaults_to_id(self) -> None:
        """``name`` 缺省时 MUST **归一为 ``id``**（构造后恒为 ``str``）。"""
        node = Node(id="a")
        assert node.name == "a"
        assert isinstance(node.name, str)

    def test_explicit_name_is_kept(self) -> None:
        """显式给出的别名 MUST 原样保留。"""
        assert Node(id="a", name="别名 A").name == "别名 A"

    def test_metadata_is_shallow_copied(self) -> None:
        """构造后改原 dict MUST NOT 影响实例。"""
        metadata: dict[str, Any] = {"kind": "llm"}
        node = Node(id="a", metadata=metadata)
        metadata["kind"] = "tampered"
        assert node.metadata == {"kind": "llm"}

    def test_is_frozen(self) -> None:
        """构造后改字段 MUST 抛 ``FrozenInstanceError``。"""
        node = Node(id="a")
        with pytest.raises(FrozenInstanceError):
            node.id = "b"  # type: ignore[misc]

    def test_is_unhashable(self) -> None:
        """``hash()`` MUST 抛 ``TypeError``（含映射字段 ⇒ 不可哈希）。"""
        with pytest.raises(TypeError):
            hash(Node(id="a"))

    def test_equality_is_field_level(self) -> None:
        """同字段值 ⇒ 相等；异值 ⇒ 不等。"""
        assert Node(id="a") == Node(id="a")
        assert Node(id="a") != Node(id="b")

    def test_is_json_serializable(self) -> None:
        """字段值 MUST 可 JSON 序列化。"""
        payload = json.dumps(asdict(Node(id="a", metadata={"k": "v"})))
        assert json.loads(payload)["id"] == "a"


# ── US3 · Edge ─────────────────────────────────────────────────────────


class TestEdge:
    """US3 · 边元素 —— 4 字段、缺省、不可变、**不可哈希**。"""

    def test_field_list_is_exactly_four(self) -> None:
        """字段清单 MUST **恰为**那 4 个（逐字）。"""
        assert [f.name for f in fields(Edge)] == EDGE_FIELDS

    def test_defaults(self) -> None:
        """``conditional`` 缺省 ``False``；``condition`` 缺省 ``None``。"""
        edge = Edge(source="a", target="b")
        assert edge.conditional is False
        assert edge.condition is None

    def test_conditional_edge_keeps_condition(self) -> None:
        """条件边 MUST 能表达条件名。"""
        edge = Edge(source="a", target="b", conditional=True, condition="route")
        assert edge.conditional is True
        assert edge.condition == "route"

    def test_is_frozen(self) -> None:
        """构造后改字段 MUST 抛 ``FrozenInstanceError``。"""
        edge = Edge(source="a", target="b")
        with pytest.raises(FrozenInstanceError):
            edge.target = "c"  # type: ignore[misc]

    def test_is_unhashable(self) -> None:
        """``hash()`` MUST 抛 ``TypeError``。

        （``Edge`` 四字段**全是标量** ⇒ dataclass 会**自动生成** ``__hash__``
        ⇒ 必须**显式**写 ``__hash__ = None`` 才兑现「四类统一不可哈希」。）
        """
        with pytest.raises(TypeError):
            hash(Edge(source="a", target="b"))

    def test_equality_is_field_level(self) -> None:
        """同字段值 ⇒ 相等；异值 ⇒ 不等。"""
        assert Edge(source="a", target="b") == Edge(source="a", target="b")
        assert Edge(source="a", target="b") != Edge(source="a", target="c")

    def test_is_json_serializable(self) -> None:
        """字段值 MUST 可 JSON 序列化。"""
        payload = json.dumps(asdict(Edge(source="a", target="b")))
        assert json.loads(payload)["source"] == "a"


# ── US3 · Graph ────────────────────────────────────────────────────────


class TestGraph:
    """US3 · 图结构 —— 2 字段、元组容器、不可变、不可哈希。"""

    def test_field_list_is_exactly_two(self) -> None:
        """字段清单 MUST **恰为**那 2 个（逐字）。"""
        assert [f.name for f in fields(Graph)] == GRAPH_FIELDS

    def test_defaults_are_empty_tuples(self) -> None:
        """两个集合缺省 MUST 为**空元组**（不是 list）。"""
        graph = Graph()
        assert graph.nodes == ()
        assert graph.edges == ()

    def test_containers_are_tuples_of_pure_data_classes(self) -> None:
        """两个集合 MUST 是**元组**，元素 MUST 是本层纯数据类。"""
        graph = Graph(nodes=(Node(id="a"),), edges=(Edge(source="a", target="b"),))
        assert isinstance(graph.nodes, tuple)
        assert isinstance(graph.edges, tuple)
        assert all(isinstance(node, Node) for node in graph.nodes)
        assert all(isinstance(edge, Edge) for edge in graph.edges)

    def test_is_frozen(self) -> None:
        """构造后改字段 MUST 抛 ``FrozenInstanceError``。"""
        graph = Graph()
        with pytest.raises(FrozenInstanceError):
            graph.nodes = ()  # type: ignore[misc]

    def test_is_unhashable(self) -> None:
        """``hash()`` MUST 抛 ``TypeError``（元素不可哈希 ⇒ 自身不可哈希）。"""
        with pytest.raises(TypeError):
            hash(Graph())

    def test_equality_is_field_level(self) -> None:
        """同字段值 ⇒ 相等；异值 ⇒ 不等。"""
        assert Graph() == Graph()
        assert Graph(nodes=(Node(id="a"),)) != Graph(nodes=(Node(id="b"),))

    def test_is_json_serializable(self) -> None:
        """字段值 MUST 可 JSON 序列化。"""
        graph = Graph(nodes=(Node(id="a"),), edges=(Edge(source="a", target="b"),))
        payload = json.dumps(asdict(graph))
        decoded = json.loads(payload)
        assert decoded["nodes"][0]["id"] == "a"
        assert decoded["edges"][0]["target"] == "b"


# ── US3 · 纯数据纪律（无对象引用字段）──────────────────────────────────


class TestNoObjectReferenceFields:
    """US3 · 三个数据类的字段类型 MUST NOT 承载**对象引用**。"""

    @pytest.mark.parametrize(
        ("cls", "expected"),
        [(Node, NODE_FIELDS), (Edge, EDGE_FIELDS), (Graph, GRAPH_FIELDS)],
    )
    def test_field_types_are_pure_data(self, cls: type, expected: list[str]) -> None:
        """字段类型 MUST 落在「标量 / 映射 / 元组 / 本层纯数据类」之内。"""
        hints = get_type_hints(cls)
        assert list(hints) == expected
        for name, annotation in hints.items():
            assert _is_pure_data_type(annotation), (
                f"{cls.__name__}.{name} 的类型 {annotation!r} 不是纯数据类型"
            )


def _is_pure_data_type(annotation: Any) -> bool:
    """判定一个字段注解是否落在**纯数据白名单**之内。

    白名单：标量（``str`` / ``int`` / ``float`` / ``bool`` / ``None``）、
    ``Mapping[str, Any]``、``tuple[...]``（元素为标量或本层纯数据类）、
    以及本层纯数据类（``Node`` / ``Edge`` / ``Graph``）。
    """
    pure_data_classes = (Node, Edge, Graph)
    scalars = (str, int, float, bool, type(None))

    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        return all(_is_pure_data_type(arg) for arg in get_args(annotation))
    if origin is tuple:
        args = [arg for arg in get_args(annotation) if arg is not Ellipsis]
        return bool(args) and all(_is_pure_data_type(arg) for arg in args)
    if origin is not None:
        if origin is Mapping:
            return get_args(annotation) == (str, Any)
        return False
    if annotation is Any:
        return False
    if isinstance(annotation, type) and issubclass(annotation, pure_data_classes):
        return True
    return annotation in scalars
