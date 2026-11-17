# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""``StateGraph`` 的构建器实现 + ``compile()`` 产物（B6F1 / B7F2 · L3 图定义层）。

本模块是门面 ``freegraph.graph.StateGraph`` 的实现体。

**B6F1 交付声明式建图**：

* 构造期只保存 ``state_schema`` 并初始化空私有容器（零 schema 解析 / 零校验 / 零 I/O）；
* :meth:`StateGraph.add_node` / :meth:`StateGraph.add_edge` /
  :meth:`StateGraph.add_conditional_edges` 只**登记并立即校验**；
* :meth:`StateGraph.validate` / :meth:`StateGraph._build_spec` 在**构建期末**执行
  完整校验并产出冻结的 :class:`_BuilderSpec`，供 ``compile()`` 消费。

**B7F2 交付 ``compile()``**：

* 把 :class:`_BuilderSpec` **适配**为 L2 的 :class:`GraphSpec`（单源 ``END`` 过滤 ·
  新 channels 映射 · ``conditional_edges`` 恒空）；
* 条件边 plain mapping 与注入项挂到 :class:`CompiledGraph` 上；
* 未就绪的 6 个能力面方法抛内置 ``NotImplementedError``（点名归属 feature）。

本模块 **不执行**任何节点 / 路由函数 / 归约器，也**不实现** ``invoke()`` /
``stream()`` / ``get_graph()`` / 条件边求值 / checkpointer / store 的**行为**。

**上游对齐**（``langgraph 1.2.11`` · 原则 XI）：``StateGraph.__init__`` /
``add_node`` / ``add_edge`` / ``add_conditional_edges`` / ``validate`` / ``compile``
的方法名与必填位置参数与上游同款；更严失败信号与 defer 差异见 spec 的偏离登记
X-1…X-12。
"""

from __future__ import annotations

import warnings
from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Self, get_args, get_origin, get_type_hints

from .contracts import (
    Checkpointer,
    Command,
    CompiledGraph as CompiledGraphProtocol,
    RunConfig,
    StateDict,
    Store,
)
from .runtime import (
    Channel,
    EphemeralValue,
    GraphSpec,
    InterruptResult,
    NodeSpec,
    SuperStepResult,
    build_channels,
    parse_state_schema,
    run_graph,
)

_START = "__start__"
_END = "__end__"
_RESERVED_CHARS = ("|", ":")

#: L1 协议别名（仅用于静态检查 / 文档；实现体类同名但**不继承**它 ⇒ 结构化子类型）。
_COMPILED_GRAPH_PROTOCOL = CompiledGraphProtocol


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


def _static_points(value: Any, field_name: str) -> Any:
    """静态断点入口层**容器形态门**（B7F2 · CV-11 · DR-5）。

    * ``None`` ⇒ ``()``（关闭）；
    * ``str`` / ``list`` ⇒ **原样透传**（元素级与裸字符串失败信号由
      :class:`GraphSpec` 的归一函数产出 ⇒ B13F1 D-2 的「逐字同款」）；
    * 其它容器（``tuple`` / ``set`` / ``dict`` / 数值 …）⇒ 内置 ``TypeError``。

    这是 ``compile()`` 内**唯一**自写的图结构判定；其余校验全部委托
    ``_build_spec()`` / ``GraphSpec.__post_init__``（单一真源）。
    """
    if value is None:
        return ()
    if isinstance(value, (str, list)):
        return value
    raise TypeError(
        f"{field_name} must be '*' or a list of node names, "
        f"got {type(value).__name__} (V-22)"
    )


def _graph_spec_from(
    builder_spec: _BuilderSpec,
    interrupt_before: Any,
    interrupt_after: Any,
) -> GraphSpec:
    """把 :class:`_BuilderSpec` 适配为 L2 的 :class:`GraphSpec`（B7F2 · DD-04/05）。

    * ``channels`` 用**新映射**（同一批模板对象 ⇒ 运行期增补不污染构建器快照）；
    * ``nodes`` 原样搬运（``NodeSpec`` 同构）；
    * ``edges`` **仅**对 ``str``（单源）键过滤 ``END`` 目标；过滤后目标元组为空
      的源键**整体移除**；``tuple``（多源）键**原样透传**（交 V-16 显式失败）；
    * ``conditional_edges`` **不传**（恒空 ⇒ 不触发 V-8）。
    """
    edges: dict[str | tuple[str, ...], tuple[str, ...]] = {}
    for key, targets in builder_spec.edges.items():
        if isinstance(key, str):
            kept = tuple(target for target in targets if target != _END)
            if kept:
                edges[key] = kept
            continue
        edges[key] = targets
    return GraphSpec(
        channels=dict(builder_spec.channels),
        nodes=dict(builder_spec.nodes),
        edges=edges,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
    )


def _conditional_mapping(
    builder_spec: _BuilderSpec,
) -> dict[str, tuple[dict[str, Any], ...]]:
    """把条件边机械翻译为 plain mapping（B7F2 · B6F1 D-2 形状逐字）。

    外层 key = 源节点名（首次出现顺序）；内层每项**恰 5 键**、顺序 = 登记顺序；
    ``branch`` 取自 :attr:`_ConditionalEdgeSpec.branch`（**MUST NOT** 重新推断）；
    ``path_map`` / ``targets`` / ``route_channels`` 原样搬运（零归一化、零过滤）。
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for spec in builder_spec.conditional_edges:
        grouped.setdefault(spec.source, []).append(
            {
                "branch": spec.branch,
                "path": spec.path,
                "path_map": spec.path_map,
                "targets": spec.targets,
                "route_channels": spec.route_channels,
            }
        )
    return {source: tuple(items) for source, items in grouped.items()}


def _full_state(spec: GraphSpec, sparse: Mapping[str, Any]) -> dict[str, Any]:
    """**「完整状态」的归一** —— 稀疏视图 ⇒ 键集 == schema 全集的普通 ``dict``。

    **单一实现点**（契约 **CF-01** / R-10）⇒ ⇒ 下游 **B8F2** 的
    ``stream(values)`` MUST **复用**它 ⇒ ⇒ **MUST NOT** 另写一份「补齐」逻辑。

    * 键集 = ``spec.channels`` **扣除**路由型通道 ⇒ ⇒ 路由通道的判定 MUST 沿用
      **B7F1 的冻结口径**（``isinstance(channel, EphemeralValue)``）⇒ ⇒
      **MUST NOT** 用「``branch:to:`` 前缀」之类**名称启发式** ⇒ ⇒
      **MUST NOT** 依赖「节点订阅集」（间接口径）；
    * 顺序 = 通道表的键顺序（= **schema 声明顺序** + 路由通道）⇒ ⇒ 扣除后
      **自然**得到 schema 声明顺序（**不重排**）；
    * 值 = ``sparse.get(key, None)`` ⇒ ⇒ **「缺席」** ⇒ ``None``；
      **「值为 ``None``」** ⇒ 原样 ``None``（**MUST NOT** 把两者混为一谈）⇒ ⇒
      归约型通道的**类型空值**（``[]`` / ``0``）**MUST NOT** 被改写成 ``None``
      （契约 R-06）；
    * ``"__interrupt__"`` 键（挂起时）⇒ ⇒ **保留**（追加在末尾 · **不覆盖** ·
      **不重排**）⇒ ⇒ **无挂起**时**不出现**。

    ⚠️ 返回值是**只读快照**：**MUST NOT** 原样回喂给下一次 ``invoke``
    （回喂会把补齐的 ``None`` **真的写进**通道 ⇒ 节点里
    ``state.get("llm_calls", 0) + 1`` 会 ``TypeError``）⇒ ⇒ 上游因省略无值
    key 而回喂**安全**（实测 E-5）⇒ ⇒ 这是 freegraph 的**已知代价**。
    """
    out: dict[str, Any] = {}
    for key, channel in spec.channels.items():
        if isinstance(channel, EphemeralValue):
            continue
        out[key] = sparse.get(key, None)
    if "__interrupt__" in sparse:
        out["__interrupt__"] = sparse["__interrupt__"]
    return out


class CompiledGraph:
    """``compile()`` 的编译产物（B7F2 · L3 私有实现体 · **不进**门面导出面）。

    **持有面**（冻结 · DD-13）：

    * 私有：``_spec``（L2 ``GraphSpec``）/ ``_builder_spec``（完整
      ``_BuilderSpec``，含 ``node_records``）/ ``_conditional_edges``（plain
      mapping）；
    * 公开：6 个注入项 + 2 个归一后的断点元组（上游 ``Pregel`` 同款；
      ``transformers`` 命名差异见 X-12）。

    6 个能力面方法在本 feature **全部未就绪** ⇒ 抛内置
    ``NotImplementedError``（点名归属 feature）；MUST NOT 抛 ``AttributeError``。
    """

    def __init__(
        self,
        spec: GraphSpec,
        builder_spec: _BuilderSpec,
        conditional_edges: dict[str, tuple[dict[str, Any], ...]],
        checkpointer: Checkpointer | None,
        store: Store | None,
        cache: Any,
        debug: bool,
        name: str | None,
        transformers: Any,
        interrupt_before_nodes: tuple[str, ...],
        interrupt_after_nodes: tuple[str, ...],
    ) -> None:
        self._spec = spec
        self._builder_spec = builder_spec
        self._conditional_edges = conditional_edges
        self.checkpointer = checkpointer
        self.store = store
        self.cache = cache
        self.debug = debug
        self.name = name
        self.transformers = transformers
        self.interrupt_before_nodes = interrupt_before_nodes
        self.interrupt_after_nodes = interrupt_after_nodes

    def invoke(
        self,
        input: StateDict | Command | None,
        config: RunConfig | Mapping[str, Any] | None = None,
    ) -> StateDict:
        """执行整张图并返回**完整状态**（**B7F3 已交付** · 契约 §1 / §3）。

        **签名**（**逐字冻结** · 契约 §1）::

            invoke(self, input: StateDict | Command | None,
                   config: RunConfig | Mapping[str, Any] | None = None) -> StateDict

        * ``input`` —— **状态字典**（**部分**键值对即可）/ ``Command``（恢复路径）
          / ``None``（会话连续 · 照常跑 · **不**写任何通道）⇒ ⇒ **上游同款**
          （``langgraph/pregel/main.py:3836-3838``）；
        * ``config`` —— ``RunConfig``（会话面 + ``max_concurrency``）**或**普通
          映射（运行期参数 · 如 ``{"recursion_limit": 3}``）**或** ``None``
          ⇒ ⇒ **原样**交给 L2（**MUST NOT** 在门面层把映射翻译成 ``RunConfig``）；
        * 返回 —— **普通 ``dict``**（``type(out) is dict``）· 键集 == **schema
          全部 key**（**按 schema 声明顺序**）⇒ ⇒ 无值键以 ``None`` 补齐
          （**仅覆盖型（无归约器）**通道）⇒ ⇒ 归约型通道的**类型空值**
          （``[]`` / ``0``）**原样保留**（契约 R-06）⇒ ⇒ 路由通道**不进**键集
          ⇒ ⇒ **挂起**时额外含 ``"__interrupt__"``（**元组**）。

        ⚠️ **返回值是只读快照 · 不要原样回喂给下一次 `invoke`** —— 回喂会把
        补齐的 ``None`` **真的写进**通道 ⇒ 节点里
        ``state.get("llm_calls", 0) + 1`` 会 ``TypeError``（**归约型**通道则
        会被追加一个 ``None``）⇒ ⇒ 上游因**省略**无值 key 而回喂**安全**
        （实测 E-5）⇒ ⇒ 这是 freegraph 的**已知代价**（偏离登记 X-1）⇒ ⇒
        **该禁令 MUST 写进用户可见文档**（本 docstring + ``README.md``）。

        ⚠️ **零捕获** ⇒ 失败信号（``InvalidUpdateError`` / ``GraphRecursionError``
        / ``InterruptError`` / 节点的真异常）**原类型 + 原消息**直达调用方 ⇒ ⇒
        **MUST NOT** 包装 / 吞掉（契约 §4）。
        """
        result = run_graph(
            self._spec,
            input,
            checkpointer=self.checkpointer,
            config=config,
        )
        if isinstance(result, InterruptResult):
            # ⚠️ **唯一**转成路径 = ``as_result_dict()``（B10F1 独占）⇒ ⇒
            # 「补齐」是其**之后**的**独立**一步（对两条路径**同款**）。
            return _full_state(self._spec, result.as_result_dict())
        return _full_state(self._spec, result.state)

    def stream(
        self,
        input: Any,  # noqa: A002
        config: Any = None,
        *,
        stream_mode: Any = "values",
    ) -> Any:
        """流式执行——**未就绪**（由 **B8F2** 交付）。"""
        raise NotImplementedError("stream 由 B8F2 交付")

    def get_graph(self, *, xray: bool = False) -> Any:
        """图结构导出——**未就绪**（由 **B22F1** 交付）。"""
        raise NotImplementedError("get_graph 由 B22F1 交付")

    def get_state(self, config: Any) -> Any:
        """状态查询——**未就绪**（由 **B15F1** 交付）。"""
        raise NotImplementedError("get_state 由 B15F1 交付")

    def get_state_history(self, config: Any) -> Any:
        """状态历史——**未就绪**（由 **B15F1** 交付）。"""
        raise NotImplementedError("get_state_history 由 B15F1 交付")

    def update_state(self, config: Any, values: Any, as_node: str | None = None) -> Any:
        """状态更新——**未就绪**（由 **B16F1** 交付）。"""
        raise NotImplementedError("update_state 由 B16F1 交付")


class StateGraph:
    """**图构建器**——用户从门面取到的建图入口（B6F1 已接线建图环节）。

    构造只保存 ``state_schema`` 并初始化空私有登记容器；**不解析 schema、不校验、
    不调用用户函数、不做 I/O**。``compile()`` 由 **B7F2** 交付。
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
        """编译成可执行产物（B7F2）。

        **顺序**：入口容器门（CV-11）→ ``_build_spec()``（构建期末校验）→
        ``GraphSpec`` 适配（构造期校验）→ 条件边 plain mapping → 注入项记录/
        ``store`` 告警 → 返回**新** :class:`CompiledGraph`。

        本方法**不执行**任何节点 / 路由 / 归约器，不读环境变量，不做 I/O，
        每次调用取**独立快照**（可重复编译；不设 ``compiled`` 标志）。
        """
        before = _static_points(interrupt_before, "interrupt_before")
        after = _static_points(interrupt_after, "interrupt_after")

        builder_spec = self._build_spec()
        spec = _graph_spec_from(builder_spec, before, after)
        conditional_edges = _conditional_mapping(builder_spec)

        if store is not None:
            warnings.warn(
                "compile(store=...) 已接受并记录，但 v1 不支持 Store："
                "该参数不会生效（v1 的 Store 行为归 v2）",
                stacklevel=2,
            )

        return CompiledGraph(
            spec=spec,
            builder_spec=builder_spec,
            conditional_edges=conditional_edges,
            checkpointer=checkpointer,
            store=store,
            cache=cache,
            debug=debug,
            name=name,
            transformers=transformers,
            interrupt_before_nodes=spec.interrupt_before,
            interrupt_after_nodes=spec.interrupt_after,
        )
