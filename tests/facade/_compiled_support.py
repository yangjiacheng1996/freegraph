# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B7F2 编译测试的共享夹具（最小合法图 / 注入哨兵 / 警告捕获 / 归一化摘要）。"""

from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import Any, Iterator

from freegraph.graph import END, START, StateGraph

from ._builder_support import (  # noqa: F401 - 供测试模块复用
    CallCounter,
    RichState,
    State,
    node_a,
    node_b,
    router,
    unnamed_router,
)


def build_minimal_graph(
    *,
    state_schema: Any = State,
    conditional: bool = False,
) -> StateGraph:
    """构造一张最小合法图（``START → a`` + ``a → b`` / 条件边 + ``b → END``）。"""
    graph = StateGraph(state_schema)
    graph.add_node("a", node_a)
    graph.add_node("b", node_b)
    graph.add_edge(START, "a")
    if conditional:
        graph.add_conditional_edges("a", router, ["b", END])
    else:
        graph.add_edge("a", "b")
    graph.add_edge("b", END)
    return graph


def build_two_node_graph() -> StateGraph:
    """别名：2 节点最小图（A1 判据使用）。"""
    return build_minimal_graph()


#: 注入项哨兵（**身份保留**由 `is` 断言）。
SENTINEL_CHECKPOINTER = object()


class _DummyCheckpointer:
    """B14F1 编译期校验用的**合法** 8 方法鸭子类型 saver。"""

    def get_tuple(self, config: Any) -> Any:
        return None

    def list(self, config: Any, *args: Any, **kwargs: Any) -> Any:
        return iter(())

    def put(self, config: Any, *args: Any, **kwargs: Any) -> Any:
        return None

    def put_writes(self, config: Any, *args: Any, **kwargs: Any) -> Any:
        return None

    def delete_thread(self, thread_id: str) -> None:
        return None

    def delete_for_runs(self, run_ids: Any) -> None:
        raise NotImplementedError

    def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        raise NotImplementedError

    def get_next_version(self, *args: Any, **kwargs: Any) -> int:
        return 1


#: 满足 L1 ``Checkpointer`` 的**合法**注入项（B14F1 起编译期会校验）。
DUMMY_CHECKPOINTER = _DummyCheckpointer()
SENTINEL_STORE = object()
SENTINEL_CACHE = object()
SENTINEL_TRANSFORMERS = object()


@contextmanager
def capture_warnings() -> Iterator[list[warnings.WarningMessage]]:
    """捕获 ``warnings.warn``（**记录全部**，不改变条数）。"""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        yield caught


def _channel_signature(channel: Any) -> tuple[Any, ...]:
    return (
        type(channel).__name__,
        channel.key,
        repr(channel.value_type),
        getattr(channel, "reducer", None),
        getattr(channel, "guard", None),
    )


def normalized_summary(compiled: Any) -> dict[str, Any]:
    """产物的**结构等价**摘要（通道按类型 / reducer / key 比较，不比对象身份）。"""
    spec = compiled._spec
    return {
        "keys": tuple(sorted(vars(compiled))),
        "checkpointer": compiled.checkpointer,
        "store": compiled.store,
        "cache": compiled.cache,
        "debug": compiled.debug,
        "name": compiled.name,
        "transformers": compiled.transformers,
        "interrupt_before": compiled.interrupt_before_nodes,
        "interrupt_after": compiled.interrupt_after_nodes,
        "channels": tuple(
            (key, _channel_signature(channel)) for key, channel in spec.channels.items()
        ),
        "nodes": tuple(
            (name, tuple(node.subscribes), getattr(node.run, "__name__", ""))
            for name, node in spec.nodes.items()
        ),
        "edges": tuple((key, tuple(targets)) for key, targets in spec.edges.items()),
        "conditional_edges": tuple(
            (
                source,
                tuple(
                    (
                        item["branch"],
                        item["path_map"],
                        item["targets"],
                        item["route_channels"],
                        getattr(item["path"], "__name__", ""),
                    )
                    for item in items
                ),
            )
            for source, items in compiled._conditional_edges.items()
        ),
    }
