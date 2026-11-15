# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""``StateGraph`` 的构建器实现（B6F1 · L3 图定义层）。

本模块是门面 ``freegraph.graph.StateGraph`` 的实现体。B6F1 交付**声明式建图**：

* 构造期只保存 ``state_schema`` 并初始化空私有容器（零 schema 解析 / 零校验 / 零 I/O）；
* :meth:`StateGraph.add_node` / :meth:`StateGraph.add_edge` /
  :meth:`StateGraph.add_conditional_edges` 只**登记并立即校验**；
* :meth:`StateGraph.validate` / :meth:`StateGraph._build_spec` 在**构建期末**执行
  完整校验并产出冻结的 :class:`_BuilderSpec`，供 B7F2 ``compile()`` 消费。

本 feature **不执行**任何节点 / 路由函数 / 归约器，也**不实现**
``compile()`` / ``invoke()`` / ``stream()`` / ``get_graph()``。

**上游对齐**（``langgraph 1.2.11`` · 原则 XI）：``StateGraph.__init__`` /
``add_node`` / ``add_edge`` / ``add_conditional_edges`` / ``validate`` 的方法名与必填位置参数
与上游同款；更严失败信号与 defer 差异见 spec 的偏离登记 X-1…X-7。
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Self, get_args, get_origin, get_type_hints

from .contracts import Checkpointer, CompiledGraph, Store
from .runtime import (
    Channel,
    EphemeralValue,
    NodeSpec,
    build_channels,
    parse_state_schema,
)

_START = "__start__"
_END = "__end__"
_RESERVED_CHARS = ("|", ":")


@dataclass(frozen=True)
class _NodeRecord:
    """一个节点登记项（构建期持有，不调用其 ``action``）。"""

    name: str
    action: Callable[..., Any]
    alias: str | None = None
    defer: bool = False
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class _ConditionalEdgeDraft:
    """一条条件边的构建期草稿。"""

    source: str
    path: Callable[..., Any]
    path_map: dict[Hashable, str] | None
    branch_name: str


@dataclass(frozen=True)
class _ConditionalEdgeSpec:
    """冻结的条件边规格（``_BuilderSpec.conditional_edges`` 的元素）。"""

    source: str
    branch: str
    path: Callable[..., Any]
    path_map: dict[Hashable, str] | None
    targets: tuple[str, ...]
    route_channels: tuple[str, ...]


@dataclass(frozen=True)
class _BuilderSpec:
    """构建器 → B7F2 的唯一冻结内部规格。"""

    channels: dict[str, Channel]
    nodes: dict[str, NodeSpec]
    node_records: dict[str, _NodeRecord]
    edges: dict[str | tuple[str, ...], tuple[str, ...]]
    conditional_edges: tuple[_ConditionalEdgeSpec, ...]


def _branch_name(path: Callable[..., Any]) -> str:
    """按上游同款规则取分支名（普通 callable 的 ``.name`` **不参与**）。"""
    name = getattr(path, "__name__", None)
    if not isinstance(name, str) or not name or name == "<lambda>":
        return "condition"
    return name


def _normalize_path_map(
    path: Callable[..., Any],
    path_map: Any,
) -> dict[Hashable, str] | None:
    """把 ``path_map`` 归一化为 ``dict[Hashable, str] | None``。

    * ``dict`` ⇒ 校验 value 全为 ``str`` 后**浅拷贝**；
    * ``list`` ⇒ 校验元素全为 ``str`` 后归一化为 ``{name: name}``；
    * ``None`` ⇒ 仅当 ``path`` 的返回注解为 ``Literal[...]`` 时推断；
    * 其它类型 / 非法元素 / 非法 value ⇒ 立即 ``TypeError``。
    """
    if isinstance(path_map, dict):
        if any(not isinstance(value, str) for value in path_map.values()):
            raise TypeError("path_map dict values must be str")
        return dict(path_map)
    if isinstance(path_map, list):
        if any(not isinstance(value, str) for value in path_map):
            raise TypeError("path_map list elements must be str")
        return {name: name for name in path_map}
    if path_map is not None:
        raise TypeError(
            "path_map must be list[str], dict[Hashable, str] or None, "
            f"got {type(path_map).__name__}"
        )
    try:
        return_type = get_type_hints(path).get("return")
    except Exception:
        return None
    if get_origin(return_type) is not Literal:
        return None
    names = get_args(return_type)
    if not names or any(not isinstance(name, str) for name in names):
        return None
    return {name: name for name in names}


class StateGraph:
    """**图构建器**——用户从门面取到的建图入口（B6F1 已接线建图环节）。

    构造只保存 ``state_schema`` 并初始化空私有登记容器；**不解析 schema、不校验、
    不调用用户函数、不做 I/O**。``compile()`` 仍归 **B7F2**。
    """

    def __init__(
        self,
        state_schema: Any,
        context_schema: Any = None,
        *,
        input_schema: Any = None,
        output_schema: Any = None,
    ) -> None:
        """只保存 ``state_schema`` 并初始化空容器（零 schema 解析 / 零副作用）。"""
        self._schema = state_schema
        self._nodes: dict[str, _NodeRecord] = {}
        self._edges: dict[str | tuple[str, ...], list[str]] = {}
        self._conditional_edges: list[_ConditionalEdgeDraft] = []
        self._branch_names: dict[str, set[str]] = {}

    def add_node(
        self,
        node: str | Callable[..., Any],
        action: Callable[..., Any] | None = None,
        *,
        alias: str | None = None,
        defer: bool = False,
        metadata: Mapping[str, Any] | None = None,
    ) -> Self:
        """登记一个节点（``str + action`` 或单 callable 形态），返回 ``self``。"""
        if isinstance(node, str):
            name = node
            if action is None or not callable(action):
                raise TypeError("add_node(str_node, action) requires a callable action")
        elif callable(node):
            if action is not None:
                raise TypeError("add_node(fn) does not accept an explicit action")
            name = getattr(node, "__name__", None)
            if not isinstance(name, str) or not name:
                name = type(node).__name__
            if not name:
                raise ValueError("cannot infer a node name from the callable")
            action = node
        else:
            raise TypeError("add_node node must be a str or a callable")

        if name == _START or name == _END:
            raise ValueError(f"Node `{name}` is reserved")
        for character in _RESERVED_CHARS:
            if character in name:
                raise ValueError(
                    f"'{character}' is a reserved character and is not allowed "
                    "in node names"
                )
        if name in self._nodes:
            raise ValueError(f"Node `{name}` already present")

        if metadata is not None and isinstance(metadata, Mapping):
            metadata = dict(metadata)
        self._nodes[name] = _NodeRecord(
            name=name,
            action=action,
            alias=alias,
            defer=defer,
            metadata=metadata,
        )
        return self

    def add_edge(self, start_key: str | list[str], end_key: str) -> Self:
        """登记静态边（单源或多源），返回 ``self``。"""
        if not isinstance(end_key, str):
            raise TypeError(
                f"add_edge end_key must be str, got {type(end_key).__name__}"
            )

        if isinstance(start_key, str):
            if start_key == _END:
                raise ValueError("END cannot be a start node")
            if end_key == _START:
                raise ValueError("START cannot be an end node")
            self._record_edge(start_key, end_key)
            return self

        if isinstance(start_key, (list, tuple)):
            if not start_key:
                raise ValueError("multi-source edge must have at least one source")
            sources: list[str] = []
            for source in start_key:
                if not isinstance(source, str):
                    raise ValueError(f"multi-source edge source {source!r} is not a node")
                if source == _END:
                    raise ValueError("END cannot be a start node")
                if source not in self._nodes:
                    raise ValueError(f"Need to add_node `{source}` first")
                sources.append(source)
            if end_key == _START:
                raise ValueError("START cannot be an end node")
            if end_key != _END and end_key not in self._nodes:
                raise ValueError(f"Need to add_node `{end_key}` first")
            key = tuple(dict.fromkeys(sources))
            self._record_edge(key, end_key)
            return self

        raise TypeError(
            "add_edge start_key must be str, list[str] or tuple[str, ...], "
            f"got {type(start_key).__name__}"
        )

    def _record_edge(self, key: str | tuple[str, ...], target: str) -> None:
        targets = self._edges.setdefault(key, [])
        if target not in targets:
            targets.append(target)

    def add_conditional_edges(
        self,
        source: str,
        path: Callable[..., str | list[str]],
        path_map: list[str] | dict[str, str] | None = None,
    ) -> Self:
        """登记条件边（``path_map`` 支持 list / dict / None），返回 ``self``。"""
        if not isinstance(source, str):
            raise TypeError(
                f"add_conditional_edges source must be str, got {type(source).__name__}"
            )
        if not callable(path):
            raise TypeError("add_conditional_edges path must be callable")

        normalized = _normalize_path_map(path, path_map)
        branch = _branch_name(path)
        used = self._branch_names.setdefault(source, set())
        if branch in used:
            raise ValueError(
                f"Branch with name `{branch}` already exists at `{source}`"
            )
        used.add(branch)
        self._conditional_edges.append(
            _ConditionalEdgeDraft(
                source=source,
                path=path,
                path_map=normalized,
                branch_name=branch,
            )
        )
        return self

    def add_sequence(self, nodes: Sequence[Any]) -> Self:
        """**本版本不交付**（上游同款方法 · 另行立项）。"""
        raise NotImplementedError("add_sequence 本版本不交付 · 另行立项")

    def set_entry_point(self, key: str) -> Self:
        """**本版本不交付**（上游同款方法 · 另行立项）。"""
        raise NotImplementedError("set_entry_point 本版本不交付 · 另行立项")

    def set_conditional_entry_point(
        self,
        path: Callable[..., str | list[str]],
        path_map: list[str] | dict[str, str] | None = None,
    ) -> Self:
        """**本版本不交付**（上游同款方法 · 另行立项）。"""
        raise NotImplementedError("set_conditional_entry_point 本版本不交付 · 另行立项")

    def set_finish_point(self, key: str) -> Self:
        """**本版本不交付**（上游同款方法 · 另行立项）。"""
        raise NotImplementedError("set_finish_point 本版本不交付 · 另行立项")

    def validate(self, interrupt: Sequence[str] | None = None) -> Self:
        """构建期校验入口；成功返回 ``self``，失败不修改构建器状态。"""
        self._build_spec()
        if interrupt is not None:
            self._validate_interrupt(interrupt)
        return self

    def set_node_defaults(self, **kwargs: Any) -> Self:
        """**本版本不交付**（上游同款方法 · 另行立项）。"""
        raise NotImplementedError("set_node_defaults 本版本不交付 · 另行立项")

    def _validate_sources(self) -> None:
        for key in self._edges:
            if isinstance(key, str):
                if key != _START and key not in self._nodes:
                    raise ValueError(f"Found edge starting at unknown node '{key}'")
                continue
            for source in key:
                if source != _START and source not in self._nodes:
                    raise ValueError(f"Found edge starting at unknown node '{source}'")
        for draft in self._conditional_edges:
            if draft.source != _START and draft.source not in self._nodes:
                raise ValueError(
                    f"Found edge starting at unknown node '{draft.source}'"
                )

    def _validate_entrypoint(self) -> None:
        static_entry = any(
            (isinstance(key, str) and key == _START)
            or (isinstance(key, tuple) and _START in key)
            for key in self._edges
        )
        conditional_entry = any(
            draft.source == _START for draft in self._conditional_edges
        )
        if not static_entry and not conditional_entry:
            raise ValueError(
                "Graph must have an entrypoint: add at least one edge from START "
                "to another node"
            )

    def _validate_targets(self) -> None:
        for targets in self._edges.values():
            for target in targets:
                if target != _END and target not in self._nodes:
                    raise ValueError(f"Found edge ending at unknown node `{target}`")
        for draft in self._conditional_edges:
            if draft.path_map is None:
                continue
            for target in draft.path_map.values():
                if target != _END and target not in self._nodes:
                    raise ValueError(
                        f"At '{draft.source}' node, '{draft.branch_name}' branch "
                        f"found unknown target '{target}'"
                    )

    def _validate_nodes(self) -> None:
        if not self._nodes:
            raise ValueError("Graph must have at least one node (node table is empty)")

    def _validate_interrupt(self, interrupt: Sequence[str]) -> None:
        for name in interrupt:
            if name not in self._nodes:
                raise ValueError(f"Interrupt node `{name}` not found")

    def _build_spec(self) -> _BuilderSpec:
        """执行构建期末校验并返回**新快照**（调用方修改不影响构建器）。"""
        schema_spec = parse_state_schema(self._schema)
        self._validate_sources()
        self._validate_entrypoint()
        self._validate_targets()
        self._validate_nodes()

        channels = build_channels(schema_spec)
        route_channel_names: dict[str, str] = {}
        for draft in self._conditional_edges:
            if draft.path_map is None:
                continue
            for target in draft.path_map.values():
                if target == _END or target in route_channel_names:
                    continue
                route_channel_names[target] = f"branch:to:{target}"
        for target, key in route_channel_names.items():
            channels[key] = EphemeralValue(key, Any, guard=False)

        state_channels = tuple(schema_spec.keys)
        nodes = {
            name: NodeSpec(subscribes=state_channels, run=record.action)
            for name, record in self._nodes.items()
        }
        edges = {key: tuple(targets) for key, targets in self._edges.items()}
        node_records = dict(self._nodes)
        conditional_edges: list[_ConditionalEdgeSpec] = []
        for draft in self._conditional_edges:
            if draft.path_map is None:
                targets: tuple[str, ...] = ()
                route_channels: tuple[str, ...] = ()
                path_map = None
            else:
                targets = tuple(dict.fromkeys(draft.path_map.values()))
                route_channels = tuple(
                    f"branch:to:{target}" for target in targets if target != _END
                )
                path_map = dict(draft.path_map)
            conditional_edges.append(
                _ConditionalEdgeSpec(
                    source=draft.source,
                    branch=draft.branch_name,
                    path=draft.path,
                    path_map=path_map,
                    targets=targets,
                    route_channels=route_channels,
                )
            )

        return _BuilderSpec(
            channels=channels,
            nodes=nodes,
            node_records=node_records,
            edges=edges,
            conditional_edges=tuple(conditional_edges),
        )

    def compile(
        self,
        checkpointer: Checkpointer | None = None,
        *,
        cache: Any = None,
        store: Store | None = None,
        interrupt_before: Any = None,
        interrupt_after: Any = None,
        debug: bool = False,
        name: str | None = None,
        transformers: Any = None,
    ) -> CompiledGraph:
        """编译成可执行产物——**未接线**（由 **B7F2** 交付）。"""
        raise NotImplementedError("compile 尚未接线（由 B7F2 交付）")
