#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B7F2 上游取证脚本 —— 复现 ``research.md`` §1 的 **E-25…E-55**。

**只在开发 / 人工复核时运行**（依赖已安装的 ``langgraph``）；缺席即干净跳过。
每条观测打印一行 ``E-xx: <结果>`` ⇒ 供人工与 ``research.md`` 逐条核对。

用法::

    .venv/bin/python harness/verification/B7F2/probe_upstream.py
"""

from __future__ import annotations

import importlib.metadata
import logging
import warnings
from typing import Any, Callable, TypedDict


def _skip(reason: str) -> None:
    print(f"[SKIP] {reason}")


def _state() -> Any:
    from langgraph.graph import StateGraph

    class State(TypedDict):
        x: int

    graph = StateGraph(State)
    graph.add_node("a", lambda state: {})
    graph.add_edge("__start__", "a")
    graph.add_edge("a", "__end__")
    return graph


def _probe(eid: str, fn: Callable[[], Any]) -> None:
    try:
        print(f"{eid}: {fn()!r}")
    except Exception as exc:  # noqa: BLE001 - 取证脚本只打印观测结果
        print(f"{eid}: ERROR {type(exc).__name__}: {exc}")


def main() -> int:
    try:
        import langgraph  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        _skip(f"langgraph 不可用：{exc}")
        return 0

    print(f"langgraph {importlib.metadata.version('langgraph')}")

    import langgraph.graph as lg_graph

    _probe("E-25", lambda: sorted(getattr(lg_graph, "__all__", ())))
    _probe("E-26", lambda: hasattr(lg_graph, "CompiledStateGraph"))
    _probe("E-27", lambda: type(_state().compile()).__name__)
    _probe(
        "E-28",
        lambda: type(_state().compile(checkpointer=None, store=None)).__name__,
    )
    _probe("E-29", lambda: _state().compile(checkpointer=object()))
    _probe("E-30", lambda: type(_state().compile(store=object())).__name__)

    compiled = _state().compile()
    _probe(
        "E-31",
        lambda: [
            name
            for name in (
                "checkpointer",
                "store",
                "cache",
                "debug",
                "name",
                "interrupt_before_nodes",
                "interrupt_after_nodes",
                "nodes",
                "channels",
                "builder",
            )
            if hasattr(compiled, name)
        ],
    )
    _probe(
        "E-32",
        lambda: [
            name
            for name in (
                "invoke",
                "stream",
                "get_graph",
                "get_state",
                "get_state_history",
                "update_state",
            )
            if hasattr(compiled, name)
        ],
    )
    _probe(
        "E-33",
        lambda: (compiled.debug, compiled.name, compiled.interrupt_before_nodes, compiled.interrupt_after_nodes),
    )
    _probe("E-34", lambda: type(_state().compile(interrupt_before="*")).__name__)
    _probe("E-35", lambda: _state().compile(interrupt_before=["*"]))
    _probe("E-36", lambda: type(_state().compile(interrupt_before="")).__name__)
    _probe("E-37", lambda: _state().compile(interrupt_before="a"))
    _probe("E-38", lambda: _state().compile(interrupt_before=("a",)))
    _probe("E-39", lambda: _state().compile(interrupt_before=["nope"]))
    _probe("E-40", lambda: type(_state().compile(interrupt_before=["a"])).__name__)

    def _e41() -> Any:
        graph = _state()
        graph.compile()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            graph.add_node("late", lambda state: {})
        return len(caught)

    _probe("E-41", _e41)

    def _e42() -> Any:
        graph = _state()
        first = graph.compile()
        second = graph.compile()
        return first is not second

    _probe("E-42", _e42)
    _probe("E-43", lambda: (sorted(compiled.channels), sorted(compiled.nodes)))

    from langgraph.graph import END, StateGraph

    def _e44() -> Any:
        class State(TypedDict):
            x: int

        graph = StateGraph(State)
        graph.add_edge("__start__", END)
        return type(graph.compile()).__name__

    _probe("E-44", _e44)
    _probe("E-45", lambda: _state().compile(interrupt_after=("a",)))
    _probe("E-46", lambda: _state().compile(interrupt_before={"a"}))
    _probe("E-47", lambda: _state().compile(interrupt_before="*").interrupt_before_nodes)
    _probe(
        "E-48",
        lambda: (
            _state().compile(interrupt_before=["a"], interrupt_after=["a"]).interrupt_before_nodes,
            _state().compile(interrupt_before=["a"], interrupt_after=["a"]).interrupt_after_nodes,
        ),
    )

    def _e49_e50() -> Any:
        graph = _state()
        graph.compile()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with _capture_logs() as records:
                graph.add_node("late", lambda state: {})
        return (len(caught), len(records), records[0] if records else "")

    _probe("E-49/E-50", _e49_e50)

    def _e51() -> Any:
        class State(TypedDict):
            x: int

        return StateGraph(State).compile()

    _probe("E-51", _e51)

    def _e52() -> Any:
        class State(TypedDict):
            x: int

        graph = StateGraph(State)
        graph.add_node("a", lambda state: {})
        graph.add_edge("__start__", "a")
        graph.add_edge("a", "ghost")
        return graph.compile()

    _probe("E-52", _e52)

    sentinel = object()
    _probe("E-53", lambda: _state().compile(store=sentinel).store is sentinel)
    _probe("E-54", lambda: _state().compile(debug=True).debug)
    _probe("E-55", lambda: _state().compile(name="my-graph").name)
    return 0


class _capture_logs:
    """上下文管理器：捕获根 logger 上的 ``logging`` 记录。"""

    def __init__(self) -> None:
        self.records: list[str] = []
        self._handler: logging.Handler | None = None

    def __enter__(self) -> list[str]:
        records = self.records

        class _Handler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record.getMessage())

        self._handler = _Handler()
        logging.getLogger().addHandler(self._handler)
        return records

    def __exit__(self, *exc: Any) -> None:
        if self._handler is not None:
            logging.getLogger().removeHandler(self._handler)


if __name__ == "__main__":
    raise SystemExit(main())
