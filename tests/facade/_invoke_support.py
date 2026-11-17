# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B7F3 ``invoke()`` 测试的共享夹具（schema / 节点替身 / 计数 / 桩 checkpointer / 建图）。

**自足**（除 ``freegraph`` 外不依赖仓库其它模块）⇒ ⇒ 夹具的行为可被逐条复核。

**夹具清单**（与 plan 改动面 §16 一致）：

* :class:`State` —— 最小状态 schema（与 ``harness/demo/graph_core.py:124-128`` **逐字同款**）；
* :func:`build_two_node_graph` —— ``START→a→b→END``（US1 的载体）；
* :func:`build_loop_graph` —— 自环（``recursion_limit`` 的载体）；
* :func:`build_conditional_graph` —— **带** ``path_map`` 的条件边图（**路由通道排除**的载体）；
* :func:`build_fanout_graph` —— ``START→a`` / ``START→b``（**同一 super-step** ⇒ 并发的载体）；
* :class:`CallCounter` —— 节点 / 路由调用计数；
* :class:`StubCheckpointer` —— **自足桩 checkpointer**（恢复路径的载体 · 契约 §4 **F-05**）。
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from typing import Annotated, Any, TypedDict

from freegraph.graph import END, START, StateGraph

__all__ = [
    "CallCounter",
    "State",
    "StubCheckpointer",
    "build_conditional_graph",
    "build_fanout_graph",
    "build_loop_graph",
    "build_two_node_graph",
]


class State(TypedDict):
    """最小状态 schema（**逐字同款** ``harness/demo/graph_core.py:124-128``）。

    * ``messages`` —— **带二元归约器** ⇒ 追加；
    * ``llm_calls`` —— **无归约器** ⇒ 覆盖。
    """

    messages: Annotated[list, operator.add]
    llm_calls: int


# ─────────────────────────────────────────────────────────────────────────────
# 节点替身
# ─────────────────────────────────────────────────────────────────────────────


def append_a(state: dict[str, Any]) -> dict[str, Any]:
    """往 ``messages`` 追加 ``"a"``（**部分**返回值）。"""
    return {"messages": ["a"]}


def append_b(state: dict[str, Any]) -> dict[str, Any]:
    """往 ``messages`` 追加 ``"b"``（**部分**返回值）。"""
    return {"messages": ["b"]}


def bump_calls(state: dict[str, Any]) -> dict[str, Any]:
    """把 ``llm_calls`` 覆盖为 ``+1``（**无归约器** ⇒ 覆盖语义）。"""
    return {"llm_calls": int(state.get("llm_calls") or 0) + 1}


def always_a(state: dict[str, Any]) -> str:
    """条件边路由 —— 恒走 ``"a"``。"""
    return "a"


class CallCounter:
    """节点 / 路由调用计数器。"""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def node(self, name: str, payload: dict[str, Any] | None = None) -> Callable[
        [dict[str, Any]], dict[str, Any]
    ]:
        """返回一个**计数**节点替身（返回值 = ``payload`` 的**副本**）。"""
        data = dict(payload or {})

        def _node(state: dict[str, Any]) -> dict[str, Any]:
            self.counts[name] = self.counts.get(name, 0) + 1
            return dict(data)

        _node.__name__ = name
        return _node

    def total(self) -> int:
        """全部计数之和。"""
        return sum(self.counts.values())


# ─────────────────────────────────────────────────────────────────────────────
# 建图构造器
# ─────────────────────────────────────────────────────────────────────────────


def build_two_node_graph() -> StateGraph:
    """``START→a→b→END``（**两节点** · US1 的载体）。"""
    builder = StateGraph(State)
    builder.add_node("a", append_a)
    builder.add_node("b", append_b)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def build_loop_graph() -> StateGraph:
    """自环（``loop→loop``）—— ``recursion_limit`` 的载体。"""
    builder = StateGraph(State)
    builder.add_node("loop", bump_calls)
    builder.add_edge(START, "loop")
    builder.add_edge("loop", "loop")
    return builder


def build_conditional_graph() -> StateGraph:
    """**带** ``path_map`` 的条件边图 —— **路由通道排除**的载体。

    ⚠️ **MUST 带** ``path_map``（非空）⇒ ⇒ 只有这样 ``_stategraph.py`` 才会建
    ``branch:to:<target>`` 的 :class:`EphemeralValue` 通道 ⇒ ⇒ 否则**无路由通道
    可排除** ⇒ ⇒ 「``branch:to:* not in out``」那条断言**恒真** ⇒ ⇒ **空洞**。

    ⚠️ 本图**只**用于断言「路由通道**不进**返回键集」⇒ ⇒ **MUST NOT** 断言
    「路由求值**的语义面**」（路由语义归 **B8F1** 的**契约**用例）。

    ⚠️ **2026-11-18 · B8F1 实施期修订**（**拆分而不删** · 判据**只收紧**）：
    条件边路由求值**已交付**（**B8F1**）⇒ ⇒ ⇒ 本图的路由函数**会被求值**
    ⇒ ⇒ ⇒ 它的返回值**必须**是 ``path_map`` 的**合法 key** ⇒ ⇒ ⇒ 否则查表失败
    ⇒ ⇒ ⇒ 抛内置 ``KeyError``（**X-1**）⇒ ⇒ ⇒ 图**跑不起来** ⇒ ⇒ ⇒
    **原断言**（「路由通道**不进**返回键集」）**逐字保留** ⇒ ⇒ ⇒ **判据只收紧**
    （路由通道**真的被用过** ⇒ 该断言**不再空洞**）。
    ⇒ ⇒ ⇒ 路由函数返回 ``"a"`` ⇒ ``path_map`` 把 ``"a"`` 映射到 ``"b"``
    ⇒ ⇒ ⇒ 图的流程 = ``START→a→b``（``b`` 无出边 ⇒ 收敛）⇒ ⇒ ⇒ **不构成自环**。
    """
    builder = StateGraph(State)
    builder.add_node("a", append_a)
    builder.add_node("b", append_b)
    builder.add_edge(START, "a")
    builder.add_conditional_edges("a", always_a, {"a": "b"})
    builder.add_edge("b", END)
    return builder


def build_fanout_graph(
    node_a: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    node_b: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> StateGraph:
    """``START→a`` / ``START→b``（**两个节点落在同一 super-step** ⇒ 真并发）。

    ⚠️ **MUST 含一个名为 ``c`` 的节点**（**注册但暂不被任何边引用**）⇒ ⇒ 否则
    T017⑦ 的 ``add_edge(["a", "b"], "c")``（屏障）会指向**未注册节点** ⇒ ⇒
    编译期即失败 ⇒ ⇒ ⇒ **判据载体不完整**。

    ⚠️ **本夹具不含** join 边 ⇒ ⇒ 屏障边由 T017⑦ **自行追加**。

    ⚠️ ``node_a`` / ``node_b`` 让**并发度判据**（T027）能复用**同一个**夹具而
    **不另造第二个**（**MUST NOT** 另造 ⇒ 零漂移）。
    """
    builder = StateGraph(State)
    builder.add_node("a", node_a if node_a is not None else append_a)
    builder.add_node("b", node_b if node_b is not None else append_b)
    builder.add_node("c", append_b)
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    return builder


# ─────────────────────────────────────────────────────────────────────────────
# 自足桩 checkpointer（契约 §4 F-05 冻结的方法集）
# ─────────────────────────────────────────────────────────────────────────────


class StubSnapshot:
    """``get_tuple`` 返回值的 ``.snapshot`` —— **最小**快照载荷。"""

    def __init__(self, values: dict[str, Any], metadata: dict[str, Any]) -> None:
        self.values = values
        self.next = metadata.get("next")
        self.interrupts = tuple(metadata.get("interrupts", ()))
        self.tasks = tuple(metadata.get("tasks", ()))


class StubTuple:
    """``get_tuple`` 的返回值 —— **三个具名属性**（契约 §4 **F-05**）。"""

    def __init__(
        self,
        values: dict[str, Any],
        metadata: dict[str, Any],
        pending: tuple[tuple[Any, str, Any], ...],
    ) -> None:
        self._values = values
        self._metadata = metadata
        self._pending = pending

    @property
    def snapshot(self) -> StubSnapshot:
        """**快照**（``StateSnapshot`` 形态 · 只取用到的字段）。"""
        return StubSnapshot(self._values, self._metadata)

    @property
    def pending_writes(self) -> tuple[tuple[Any, str, Any], ...]:
        """**待写入**（三元组序列）。"""
        return self._pending

    @property
    def scheduler(self) -> dict[str, Any]:
        """**调度账本**。"""
        return dict(self._metadata.get("scheduler", {}))


class StubCheckpointer:
    """**自足桩** checkpointer —— 只存**最小**载荷（恢复路径的载体）。

    ⚠️ **方法集逐字按契约 §4 F-05 冻结的清单实现**（**三个**方法：
    ``get_tuple`` / ``put`` / ``put_writes``）⇒ ⇒ **MUST NOT** 多实现
    ``list`` / ``delete_thread`` / ``delete_for_runs`` / ``copy_thread`` /
    ``get_next_version`` 这 **5 个 L2 恢复路径不调用**的协议方法 ⇒ ⇒
    **MUST NOT** 以「等最小集」这类**开放表述**取舍。

    ⚠️ **仅供测试** ⇒ ⇒ **MUST NOT** 进 ``src/``（``MemorySaver`` / ``SqliteSaver``
    归 **B14F1** · 宪法原则 IV「MUST NOT 提供『不挂 checkpointer 也能恢复』的
    内存态旁路」）。
    """

    def __init__(self) -> None:
        self.snapshot: tuple[dict[str, Any], dict[str, Any]] | None = None
        self.pending: list[tuple[Any, str, Any]] = []

    def get_tuple(self, config: Any) -> Any:
        """取回**最新**快照（**查不到** ⇒ ``None``）。"""
        if self.snapshot is None:
            return None
        values, metadata = self.snapshot
        return StubTuple(values, metadata, tuple(self.pending))

    def put(
        self,
        config: Any,
        values: Any = None,
        metadata: Any = None,
        **kwargs: Any,
    ) -> None:
        """写入**快照**。"""
        self.snapshot = (dict(values or {}), dict(metadata or {}))

    def put_writes(
        self,
        config: Any,
        writes: Any = None,
        task_id: Any = None,
        task_path: Any = None,
        **kwargs: Any,
    ) -> None:
        """写入**待写入数据**（同一任务 + 同一通道 ⇒ **覆盖**）。"""
        for channel, value in writes or ():
            for index, entry in enumerate(self.pending):
                if entry[0] == task_id and entry[1] == channel:
                    self.pending[index] = (task_id, channel, value)
                    break
            else:
                self.pending.append((task_id, channel, value))
