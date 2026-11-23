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
  新 channels 映射 · **B8F1 起** ``conditional_edges`` **填入** L3 产出的
  plain mapping（**恰 5 键** · 零归一化））；
* 条件边 plain mapping 与注入项挂到 :class:`CompiledGraph` 上；
* 尚未就绪的能力面方法抛内置 ``NotImplementedError``（点名归属 feature）。

**B8F2 交付 ``stream()``**：L3 持有主循环（反复驱动 L2 私有 ``_stream_tick``），
事件信封 / ``values`` 归一 / ``custom`` 轮末批量的组装均在本模块；``checkpointer``
与静态断点在 v1 分别被忽略 / 显式拒绝。

**B22F1 交付 ``get_graph()``**：从编译期冻结快照导出自有 ``Graph``（零执行 / 零副作用）；
checkpointer / store 的**行为**仍不在本模块。

**上游对齐**（``langgraph 1.2.11`` · 原则 XI）：``StateGraph.__init__`` /
``add_node`` / ``add_edge`` / ``add_conditional_edges`` / ``validate`` / ``compile``
的方法名与必填位置参数与上游同款；更严失败信号与 defer 差异见 spec 的偏离登记
X-1…X-12。
"""

from __future__ import annotations

import inspect
import types
import uuid
import warnings
from collections.abc import Callable, Hashable, Iterator, Mapping, Sequence
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any, Literal, Self, Union, get_args, get_origin, get_type_hints

from .contracts import (
    Checkpointer,
    Command,
    Edge,
    Graph,
    Node,
    CompiledGraph as CompiledGraphProtocol,
    GraphInterrupt,
    RunConfig,
    StateDict,
    StateSnapshot,
    Store,
    StreamWriter,
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
from .runtime import _state_read
from .runtime._checkpoint import bind_error_interrupts, reset_error_interrupts
from .runtime._stream import StreamSession
from .runtime._stream_checkpoint import StreamCheckpointWriter
from .runtime._recursion import resolve_config
from .runtime._span_hook import current_span_tracer
from .runtime._stream_context import bind_run_ids, get_stream_writer
from .runtime.superstep import _stream_tick

_START = "__start__"
_END = "__end__"
_RESERVED_CHARS = ("|", ":")


def _validate_checkpointer(checkpointer: Any) -> None:
    """**编译期**校验 ``checkpointer=``（B14F1 · 消解 B7F2 X-4）。

    接受 ``None`` / ``True`` / ``False`` / 满足 L1 ``Checkpointer`` 协议的
    鸭子类型对象；其它抛 ``TypeError``。布尔判定 MUST 用 ``isinstance(x, bool)``
    —— **MUST NOT** 用 ``x in (None, True, False)``（否则 ``0`` / ``1`` 会被
    ``==`` 误接受）。
    """
    if checkpointer is None or isinstance(checkpointer, bool):
        return
    if isinstance(checkpointer, Checkpointer):
        return
    raise TypeError(
        "Invalid checkpointer provided. Expected a BaseCheckpointSaver equivalent "
        "(an object satisfying freegraph.contracts.Checkpointer), True, False, or None. "
        f"Received {type(checkpointer).__name__}."
    )

_TRACE_OWN = "OWN"
_TRACE_MASK = "MASK"
_TRACE_LEGACY_DIRECT = "LEGACY_DIRECT"
_TRACE_NONE = "NONE"


def _trace_mode(tracer: Any) -> str:
    """单一共享守卫：OWN / MASK / LEGACY_DIRECT / NONE（B19F1 · T031）。"""
    if tracer is not None:
        return _TRACE_OWN
    if current_span_tracer() is None:
        return _TRACE_NONE
    from .observability._inject import b19f1_scope_active

    return _TRACE_MASK if b19f1_scope_active() else _TRACE_LEGACY_DIRECT

#: L1 协议别名（仅用于静态检查 / 文档；实现体类同名但**不继承**它 ⇒ 结构化子类型）。
_COMPILED_GRAPH_PROTOCOL = CompiledGraphProtocol


@dataclass(frozen=True)
class _NodeRecord:
    """一个节点登记项（构建期持有，不调用其 ``action``）。"""

    name: str
    action: Callable[..., Any]
    defer: bool = False
    metadata: Mapping[str, Any] | None = None
    destinations: tuple[tuple[str, str | None], ...] = ()


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


@dataclass(frozen=True)
class _EdgeGroup:
    """图导出中间体：一条「边组」（B22F1 · 仅 L3 内部）。"""

    sources: tuple[str, ...]
    target: str
    conditional: bool = False
    condition: str | None = None


def _branch_name(path: Callable[..., Any]) -> str:
    """按上游同款规则取分支名（普通 callable 的 ``.name`` **不参与**）。"""
    name = getattr(path, "__name__", None)
    if not isinstance(name, str) or not name or name == "<lambda>":
        return "condition"
    return name


def _infer_command_destinations(action: Callable[..., Any]) -> tuple[str, ...]:
    """从节点返回注解推断 ``Command[Literal[...]]`` 的目标（B22F1）。

    与上游 ``langgraph/graph/state.py:810-858`` 同款：仅函数 / 方法 / 有方法
    ``__call__`` 的可调用对象参与；先取 ``__call__`` 的 hints，再回退 action 本身；
    任何解析异常都**静默降级为无声明**（MUST NOT 让登记失败）。
    """
    call = getattr(action, "__call__", None)
    if not (
        inspect.isfunction(action)
        or inspect.ismethod(action)
        or inspect.ismethod(call)
    ):
        return ()
    try:
        hints = (get_type_hints(call) if call is not None else None) or get_type_hints(
            action
        )
    except (NameError, TypeError, StopIteration):
        return ()

    rtn = hints.get("return")
    if rtn is None:
        return ()
    origin = get_origin(rtn)
    if origin in (Union, types.UnionType):
        for arg in get_args(rtn):
            if get_origin(arg) is Command:
                rtn = arg
                origin = get_origin(rtn)
                break
    if origin is not Command:
        return ()
    args = get_args(rtn)
    if not args:
        return ()
    literal = args[0]
    if get_origin(literal) is not Literal:
        return ()
    return tuple(get_args(literal))


def _normalize_destinations(
    value: Mapping[str, str] | Sequence[str],
) -> tuple[tuple[str, str | None], ...]:
    """把**显式** ``destinations`` 归一为 ``(target, label | None)``（B22F1）。

    ``None`` 不在此处理——``add_node`` 必须先判 ``destinations is None`` 再决定
    是否调用推断（否则「未提供」与「显式空」不可区分）。
    """
    if isinstance(value, Mapping):
        normalized: list[tuple[str, str | None]] = []
        for target, label in value.items():
            if not isinstance(target, str) or not isinstance(label, str):
                raise TypeError("destinations mapping must be dict[str, str]")
            normalized.append((target, label))
        return tuple(normalized)
    if isinstance(value, (str, bytes)):
        raise TypeError("destinations must be a non-str sequence or a dict[str, str]")
    if isinstance(value, Sequence):
        normalized = []
        for target in value:
            if not isinstance(target, str):
                raise TypeError("destinations sequence elements must be str")
            normalized.append((target, None))
        return tuple(normalized)
    raise TypeError("destinations must be a non-str sequence or a dict[str, str]")


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
    conditional_edges: dict[str, tuple[dict[str, Any], ...]] | None = None,
) -> GraphSpec:
    """把 :class:`_BuilderSpec` 适配为 L2 的 :class:`GraphSpec`（B7F2 · DD-04/05）。

    * ``channels`` 用**新映射**（同一批模板对象 ⇒ 运行期增补不污染构建器快照）；
    * ``nodes`` 原样搬运（``NodeSpec`` 同构）；
    * ``edges`` **仅**对 ``str``（单源）键过滤 ``END`` 目标；过滤后目标元组为空
      的源键**整体移除**；``tuple``（多源）键**原样透传**（交 V-16 显式失败）；
    * ``conditional_edges`` —— **B8F1**（裁定 14 · 承接条款 **H-3**）⇒ **填入**
      ``_conditional_mapping()`` 的结果（plain mapping · 外层 key = 源节点名 ·
      内层 = **tuple** of **恰 5 键** dict）⇒ ⇒ ⇒ **零新增编译产物私有字段**
      ⇒ ⇒ ⇒ **V-8 已放宽**（该字段**非空**不再��构造期失败）⇒ ⇒ ⇒
      **零重新归一化**（L2 MUST NOT 重新归一化 ``path_map``）。
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
        conditional_edges=dict(conditional_edges or {}),
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


def _export_nodes(
    spec: GraphSpec,
    builder_spec: _BuilderSpec,
    interrupt_before: Sequence[str],
    interrupt_after: Sequence[str],
) -> list[Node]:
    """构造 ``Graph.nodes``（B22F1 · 上游 ``_draw.py:221-236`` 同款）。"""
    before = set(interrupt_before)
    after = set(interrupt_after)
    nodes: list[Node] = [Node(id=_START)]
    for name in spec.nodes:
        record = builder_spec.node_records[name]
        metadata = dict(record.metadata or {})
        if record.defer:
            metadata["defer"] = True
        if name in before and name in after:
            metadata["__interrupt"] = "before,after"
        elif name in before:
            metadata["__interrupt"] = "before"
        elif name in after:
            metadata["__interrupt"] = "after"
        nodes.append(Node(id=name, name=name, metadata=metadata))
    nodes.append(Node(id=_END))
    return nodes


def _export_groups(
    spec: GraphSpec,
    builder_spec: _BuilderSpec,
    conditional_edges: Mapping[str, tuple[dict[str, Any], ...]],
) -> list[_EdgeGroup]:
    """把静态 / 条件 / 节点声明边归一为 ``_EdgeGroup``（保序）。"""
    groups: list[_EdgeGroup] = []
    for key, targets in spec.edges.items():
        sources = (key,) if isinstance(key, str) else tuple(key)
        for target in targets:
            groups.append(_EdgeGroup(sources=sources, target=target))
    # ``_spec.edges`` 过滤了单源 END ⇒ 从完整冻结快照恢复。
    for key, targets in builder_spec.edges.items():
        if not isinstance(key, str):
            continue
        for target in targets:
            if target == _END:
                groups.append(_EdgeGroup(sources=(key,), target=target))
    for source, items in conditional_edges.items():
        for item in items:
            branch = item["branch"]
            for target in item["targets"]:
                groups.append(
                    _EdgeGroup(
                        sources=(source,),
                        target=target,
                        conditional=True,
                        condition=branch,
                    )
                )
    for name in spec.nodes:
        for target, label in builder_spec.node_records[name].destinations:
            groups.append(
                _EdgeGroup(
                    sources=(name,),
                    target=target,
                    conditional=True,
                    condition=label,
                )
            )
    return groups


def _export_edges(groups: Sequence[_EdgeGroup], spec: GraphSpec) -> tuple[Edge, ...]:
    """静态可达闭包 + 终结补边 + 去重（B22F1 契约 §3）。"""
    reachable = {_START}
    changed = True
    while changed:
        changed = False
        for group in groups:
            if group.target in reachable:
                continue
            if all(source in reachable for source in group.sources):
                reachable.add(group.target)
                changed = True

    edges: list[Edge] = []
    for group in groups:
        if not all(source in reachable for source in group.sources):
            continue
        for source in group.sources:
            if source == _END:
                continue
            edges.append(
                Edge(
                    source=source,
                    target=group.target,
                    conditional=group.conditional,
                    condition=group.condition,
                )
            )

    outgoing = {edge.source for edge in edges}
    for name in spec.nodes:
        if name in reachable and name not in outgoing:
            edges.append(Edge(source=name, target=_END))

    deduped: dict[tuple[str, str], Edge] = {}
    order: list[tuple[str, str]] = []
    for edge in edges:
        key = (edge.source, edge.target)
        if key not in deduped:
            deduped[key] = edge
            order.append(key)
        elif edge.conditional and not deduped[key].conditional:
            deduped[key] = edge
    return tuple(deduped[key] for key in order)


def _export_graph(
    spec: GraphSpec,
    builder_spec: _BuilderSpec,
    conditional_edges: Mapping[str, tuple[dict[str, Any], ...]],
    interrupt_before: Sequence[str],
    interrupt_after: Sequence[str],
) -> Graph:
    """从编译期冻结快照导出自有 ``Graph``（B22F1 · 零执行）。"""
    nodes = _export_nodes(spec, builder_spec, interrupt_before, interrupt_after)
    groups = _export_groups(spec, builder_spec, conditional_edges)
    return Graph(nodes=tuple(nodes), edges=_export_edges(groups, spec))


_STREAM_MODES: frozenset[str] = frozenset(
    {"values", "updates", "checkpoints", "tasks", "debug", "messages", "custom"}
)


def _normalize_stream_modes(
    stream_mode: str | Sequence[str] | None,
) -> tuple[str, ...]:
    """校验并归一 ``stream_mode``（调用时完成 · 契约 §7）。"""
    if stream_mode is None:
        return ("updates",)
    if isinstance(stream_mode, str):
        values = (stream_mode,)
    elif isinstance(stream_mode, Sequence):
        values = tuple(stream_mode)
    else:
        raise TypeError(
            "stream_mode must be a str, a sequence of str, or None, "
            f"got {type(stream_mode).__name__}"
        )
    if not values:
        raise ValueError(
            "stream_mode must not be an empty sequence; "
            f"legal values: {sorted(_STREAM_MODES)}"
        )
    for value in values:
        if not isinstance(value, str):
            raise TypeError(
                "stream_mode sequence items must be str, "
                f"got {type(value).__name__}"
            )
        if value not in _STREAM_MODES:
            raise ValueError(
                f"invalid stream_mode {value!r}; legal values: {sorted(_STREAM_MODES)}"
            )
    return tuple(dict.fromkeys(values))


def _event(
    stream_mode: str,
    payload: Any,
    run_id: str,
    thread_id: str | None,
) -> dict[str, Any]:
    """构造四键事件信封（唯一形态 · 契约 §2）。"""
    return {
        "stream_mode": stream_mode,
        "payload": payload,
        "run_id": run_id,
        "thread_id": thread_id,
    }


def _debug_event(
    step: int,
    task: Any,
    run_id: str,
    thread_id: str | None,
) -> dict[str, Any]:
    """构造 ``debug`` 的包裹载荷（契约 §3.4）。"""
    from datetime import datetime, timezone

    return _event(
        "debug",
        {
            "step": step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "task_result",
            "payload": task,
        },
        run_id,
        thread_id,
    )


def _wrap_node_action(action: Callable[..., Any]) -> Callable[..., Any]:
    """按上游同款规则注入 ``writer`` 关键字（FR-036 · P-20）。"""
    try:
        signature = inspect.signature(action)
    except (TypeError, ValueError):
        return action
    parameter = signature.parameters.get("writer")
    if parameter is None:
        return action
    if parameter.kind not in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    ):
        return action
    annotation = parameter.annotation
    if annotation not in (inspect.Parameter.empty, StreamWriter, "StreamWriter"):
        return action

    def wrapped(state: Any) -> Any:
        return action(state, writer=get_stream_writer())

    return wrapped


class CompiledGraph:
    """``compile()`` 的编译产物（B7F2 · L3 私有实现体 · **不进**门面导出面）。

    **持有面**（冻结 · DD-13）：

    * 私有：``_spec``（L2 ``GraphSpec``）/ ``_builder_spec``（完整
      ``_BuilderSpec``，含 ``node_records``）/ ``_conditional_edges``（plain
      mapping）；
    * 公开：6 个注入项 + 2 个归一后的断点元组（上游 ``Pregel`` 同款；
      ``transformers`` 命名差异见 X-12）。

    ``invoke`` / ``stream`` 已交付；其余能力面方法仍抛内置
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
        tracer: Any = None,
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
        self._tracer = tracer

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
        mode = _trace_mode(self._tracer)
        if mode == _TRACE_OWN:
            run_id = uuid.uuid4().hex
            thread_id = resolve_config(config).resolved_thread_id()
            id_cm: Any = bind_run_ids(run_id, thread_id)
            from .observability._inject import trace_run_scope

            scope_cm: Any = trace_run_scope(self._tracer)
        elif mode == _TRACE_MASK:
            id_cm = nullcontext()
            from .observability._inject import trace_run_scope

            scope_cm = trace_run_scope(None)
        else:
            id_cm = nullcontext()
            scope_cm = nullcontext()
        with id_cm, scope_cm:
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
        input: StateDict,
        config: RunConfig | Mapping[str, Any] | None = None,
        *,
        stream_mode: str | Sequence[str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """流式执行（**B8F2**）—— 惰性返回四键事件迭代器。"""
        modes = _normalize_stream_modes(stream_mode)
        run_id = uuid.uuid4().hex
        return self._stream_events(input, config, modes, run_id)

    def _stream_events(
        self,
        input: StateDict,
        config: RunConfig | Mapping[str, Any] | None,
        modes: tuple[str, ...],
        run_id: str,
    ) -> Iterator[dict[str, Any]]:
        """L3 主循环：反复驱动 L2 私有单轮入口（与上游 ``while loop.tick()`` 同构）。"""
        spec = self._spec
        mode = _trace_mode(self._tracer)
        if mode == _TRACE_OWN:
            from .observability._inject import trace_run_scope

            trace_cm: Any = trace_run_scope(self._tracer)
        elif mode == _TRACE_MASK:
            from .observability._inject import trace_run_scope

            trace_cm = trace_run_scope(None)
        else:
            trace_cm = nullcontext()
        with trace_cm, StreamSession(spec, input, config, run_id=run_id) as session:
            thread_id = session.thread_id
            run_config = resolve_config(config)
            writer: StreamCheckpointWriter | None = None
            if (
                "checkpoints" in modes
                and self.checkpointer is not None
                and not isinstance(self.checkpointer, bool)
                and thread_id
            ):
                writer = StreamCheckpointWriter(spec, self.checkpointer, run_config)
                written = writer.prepare(session.state)
                if written is not None:
                    yield _event(
                        "checkpoints",
                        writer.snapshot_of(written),
                        run_id,
                        thread_id,
                    )
            if "values" in modes:
                yield _event(
                    "values",
                    _full_state(spec, session.initial_sparse),
                    run_id,
                    thread_id,
                )

            round_index = 1
            while True:
                step = round_index
                round_index += 1
                if writer is not None:
                    collector, token = bind_error_interrupts()
                else:
                    collector, token = [], None
                try:
                    result = _stream_tick(
                        spec,
                        session.state,
                        max_steps=session.max_steps,
                        max_concurrency=session.max_concurrency,
                        route_config=session.route_config,
                    )
                except GraphInterrupt as exc:
                    if token is not None:
                        reset_error_interrupts(token)
                    interrupts = tuple(exc.args[0]) if exc.args else ()
                    for value in session.take_custom():
                        if "custom" in modes:
                            yield _event("custom", value, run_id, thread_id)
                    if "updates" in modes:
                        yield _event(
                            "updates",
                            {"__interrupt__": interrupts},
                            run_id,
                            thread_id,
                        )
                    captured = session.take_round_tasks()
                    if "tasks" in modes:
                        for task in captured:
                            yield _event("tasks", task, run_id, thread_id)
                    if "debug" in modes:
                        for task in captured:
                            yield _debug_event(step, task, run_id, thread_id)
                    if "values" in modes:
                        sparse = dict(session.sparse_state())
                        sparse["__interrupt__"] = interrupts
                        yield _event(
                            "values",
                            _full_state(spec, sparse),
                            run_id,
                            thread_id,
                        )
                    if writer is not None:
                        written = writer.on_interrupt(
                            session.state, captured, interrupts
                        )
                        yield _event(
                            "checkpoints",
                            writer.snapshot_of(written),
                            run_id,
                            thread_id,
                        )
                    break
                except BaseException:
                    if token is not None:
                        reset_error_interrupts(token)
                    for value in session.take_custom():
                        if "custom" in modes:
                            yield _event("custom", value, run_id, thread_id)
                    if writer is not None:
                        writer.on_error(collector)
                    raise
                else:
                    if token is not None:
                        reset_error_interrupts(token)

                if result is None:
                    break

                for value in session.take_custom():
                    if "custom" in modes:
                        yield _event("custom", value, run_id, thread_id)
                if "updates" in modes:
                    for task in result.tasks:
                        yield _event(
                            "updates",
                            {task.name: task.result},
                            run_id,
                            thread_id,
                        )
                if "tasks" in modes:
                    for task in result.tasks:
                        yield _event("tasks", task, run_id, thread_id)
                if "debug" in modes:
                    for task in result.tasks:
                        yield _debug_event(step, task, run_id, thread_id)
                if "values" in modes:
                    yield _event(
                        "values",
                        _full_state(spec, result.state),
                        run_id,
                        thread_id,
                    )
                if writer is not None:
                    written = writer.after_result(session.state, result)
                    yield _event(
                        "checkpoints",
                        writer.snapshot_of(written),
                        run_id,
                        thread_id,
                    )

    def get_graph(self, *, xray: bool = False) -> Graph:
        """图结构导出（**B22F1 已交付** · C13）。

        ``xray`` 在 v1 **仅作签名兼容**（无子图 ⇒ ``True`` 与 ``False`` 结果一致）；
        导出只读编译期冻结快照，**零执行 / 零副作用**，运行前后逐项相等。
        """
        return _export_graph(
            self._spec,
            self._builder_spec,
            self._conditional_edges,
            self.interrupt_before_nodes,
            self.interrupt_after_nodes,
        )

    def get_state(
        self, config: RunConfig | Mapping[str, Any] | None
    ) -> StateSnapshot | None:
        """状态查询（**B15F1**）—— 返回 8 字段 ``StateSnapshot`` 或 ``None``。

        未指定 ``configurable["checkpoint_id"]``（含 ``None`` / 空串）⇒ 把 pending
        writes 合并进 ``values`` 的副本；指定非空 id ⇒ 不合并。``tasks`` / ``interrupts``
        按上游 **next-tasks** 语义重建（不使用存储的完成态 ``snapshot.tasks``）。
        """
        cfg = _state_read.resolve_read_config(config)
        saver = _state_read.require_saver(self.checkpointer)
        checkpoint_tuple = saver.get_tuple(cfg)
        if checkpoint_tuple is None:
            return None
        configurable = cfg.configurable
        has_id = bool(
            isinstance(configurable, Mapping)
            and configurable.get("checkpoint_id")
        )
        return _state_read.assemble_snapshot(
            checkpoint_tuple.snapshot,
            checkpoint_tuple.scheduler,
            checkpoint_tuple.pending_writes,
            apply_values=not has_id,
            spec=self._spec,
        )

    def get_state_history(
        self,
        config: RunConfig | Mapping[str, Any] | None,
        *,
        filter: Mapping[str, Any] | None = None,
        before: RunConfig | Mapping[str, Any] | None = None,
        limit: int | None = None,
    ) -> Iterator[StateSnapshot]:
        """状态历史（**B15F1**）—— 按 ``checkpoint_id`` 倒序返回快照迭代器。

        ``filter`` / ``before`` / ``limit`` 是 L3 实现体的 keyword-only 扩展（L1 协议
        保持 ``config`` 单参数）；``values`` 不合并 pending writes。
        """
        cfg = _state_read.resolve_read_config(config)
        saver = _state_read.require_saver(self.checkpointer)
        tuples = list(
            saver.list(cfg, filter=filter, before=before, limit=limit)
        )
        snapshots = [
            _state_read.assemble_snapshot(
                item.snapshot,
                item.scheduler,
                item.pending_writes,
                apply_values=False,
                spec=self._spec,
            )
            for item in tuples
        ]
        return iter(snapshots)

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
        defer: bool = False,
        metadata: Mapping[str, Any] | None = None,
        destinations: dict[str, str] | tuple[str, ...] | None = None,
    ) -> Self:
        """登记一个节点（``str + action`` 或单 callable 形态），返回 ``self``。

        ``destinations`` 仅用于**图渲染**（`get_graph`），不影响执行；显式值覆盖
        返回注解推断（含空序列 / 空 dict）。形态 / 目标校验见 B22F1 契约。
        """
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
        if destinations is None:
            effective_destinations = tuple(
                (target, None) for target in _infer_command_destinations(action)
            )
        else:
            effective_destinations = _normalize_destinations(destinations)
        self._nodes[name] = _NodeRecord(
            name=name,
            action=action,
            defer=defer,
            metadata=metadata,
            destinations=effective_destinations,
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
        for name, record in self._nodes.items():
            for target, _label in record.destinations:
                if target != _END and target not in self._nodes:
                    raise ValueError(
                        f"At '{name}' node, destinations found unknown target "
                        f"'{target}'"
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
            name: NodeSpec(
                subscribes=state_channels, run=_wrap_node_action(record.action)
            )
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
        tracer: Any = None,
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
        # ⚠️ **B8F1**（裁定 14 · 承接条款 **H-3**）⇒ 条件边的 plain mapping
        # **由 L3 产出**（`_conditional_mapping()` · **恰 5 键** · 零归一化）
        # ⇒ ⇒ ⇒ **一次求值**（**MUST NOT** 在 `_graph_spec_from()` **内部**再调
        # 一次 ⇒ 同一载荷**两处派生** ⇒ 漂移风险）。
        conditional_edges = _conditional_mapping(builder_spec)
        spec = _graph_spec_from(builder_spec, before, after, conditional_edges)

        if store is not None:
            warnings.warn(
                "compile(store=...) 已接受并记录，但 v1 不支持 Store："
                "该参数不会生效（v1 的 Store 行为归 v2）",
                stacklevel=2,
            )

        _validate_checkpointer(checkpointer)

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
            tracer=tracer,
        )
