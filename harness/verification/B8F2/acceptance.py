#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B8F2 一键验收 —— ``stream()`` 七种 mode + ``StreamWriter``（A1…A3 / V1…V21）。

退出码：``0`` PASS · ``1`` FAIL · ``2`` 环境未就绪。
最后一行 MUST 打印 ``B8F2 acceptance: PASS|FAIL``。
"""

from __future__ import annotations

import argparse
import sys
import threading
from datetime import datetime, timedelta
from typing import Annotated, TypedDict

try:
    from freegraph.contracts import (
        Command,
        GraphInterrupt,
        GraphRecursionError,
        PregelTask,
        RunConfig,
    )
    from freegraph.graph import (
        END,
        START,
        StateGraph,
        get_stream_writer,
        interrupt,
    )
except Exception as exc:  # pragma: no cover - 环境未就绪
    print(f"B8F2 acceptance: FAIL (environment: {exc})")
    raise SystemExit(2)


class _Append:
    @staticmethod
    def apply(left: list[str], right: list[str]) -> list[str]:
        return [*left, *right]


class State(TypedDict):
    x: int
    llm_calls: int
    messages: Annotated[list[str], _Append.apply]


def _linear():
    def a(state: State) -> dict:
        return {"x": 1, "llm_calls": 1, "messages": ["a"]}

    def b(state: State) -> dict:
        return {"x": 2, "llm_calls": 2, "messages": ["b"]}

    builder = StateGraph(State)
    builder.add_node("a", a)
    builder.add_node("b", b)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder.compile()


def _one(node):
    builder = StateGraph(State)
    builder.add_node("a", node)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    return builder.compile()


def _check(name: str, fn) -> bool:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
        return False
    print(f"[PASS] {name}")
    return True


def _a1_seven_modes() -> None:
    app = _linear()
    for mode in ["values", "updates", "checkpoints", "tasks", "debug", "messages", "custom"]:
        list(app.stream({"x": 0}, stream_mode=mode))
    assert list(app.stream({"x": 0}, stream_mode="checkpoints")) == []
    assert list(app.stream({"x": 0}, stream_mode="messages")) == []


def _a2_values_equal_invoke() -> None:
    app = _linear()
    events = list(app.stream({"x": 0}, stream_mode="values"))
    assert events[-1]["payload"] == app.invoke({"x": 0})


def _a3_updates_merge() -> None:
    app = _linear()
    merged: dict = {"x": 0, "llm_calls": 0, "messages": []}
    for event in app.stream({"x": 0}, stream_mode="updates"):
        for update in event["payload"].values():
            for key, value in update.items():
                if key == "messages":
                    merged[key] = _Append.apply(merged[key], value)
                else:
                    merged[key] = value
    assert merged == app.invoke({"x": 0})


def _default_none() -> None:
    app = _linear()
    assert [event["stream_mode"] for event in app.stream({"x": 0})] == [
        "updates",
        "updates",
    ]
    assert [event["stream_mode"] for event in app.stream({"x": 0}, stream_mode=None)] == [
        "updates",
        "updates",
    ]


def _custom_and_writer() -> None:
    def node(state: State, writer) -> dict:
        writer({"via": "writer"})
        get_stream_writer()({"via": "getter"})
        return {"x": 1}

    app = _one(node)
    assert [event["payload"] for event in app.stream({}, stream_mode="custom")] == [
        {"via": "writer"},
        {"via": "getter"},
    ]
    assert app.invoke({})["x"] == 1


def _tasks_debug() -> None:
    app = _linear()
    tasks = list(app.stream({}, stream_mode="tasks"))
    assert len(tasks) == 2 and all(isinstance(e["payload"], PregelTask) for e in tasks)
    debug = list(app.stream({}, stream_mode="debug"))
    assert [e["payload"]["step"] for e in debug] == [1, 2]
    for event in debug:
        payload = event["payload"]
        assert set(payload) == {"step", "timestamp", "type", "payload"}
        assert payload["type"] == "task_result"
        assert datetime.fromisoformat(payload["timestamp"]).utcoffset() == timedelta(0)


def _envelope_and_ids() -> None:
    app = _linear()
    events = list(
        app.stream(
            {}, config={"configurable": {"thread_id": "t-1"}}, stream_mode="values"
        )
    )
    assert all(
        set(event) == {"stream_mode", "payload", "run_id", "thread_id"} for event in events
    )
    assert len({event["run_id"] for event in events}) == 1
    assert {event["thread_id"] for event in events} == {"t-1"}
    assert all(event["run_id"] != "user-run" for event in events)


def _run_config_run_id_ignored() -> None:
    app = _linear()
    events = list(
        app.stream({}, config=RunConfig(run_id="user-run"), stream_mode="updates")
    )
    assert all(event["run_id"] != "user-run" for event in events)


def _invalid_modes() -> None:
    app = _linear()
    try:
        app.stream({}, stream_mode="bogus")
    except ValueError:
        pass
    else:
        raise AssertionError("bogus mode did not raise ValueError")
    try:
        app.stream({}, stream_mode=[])
    except ValueError:
        pass
    else:
        raise AssertionError("empty mode sequence did not raise ValueError")
    try:
        app.stream({}, stream_mode=123)
    except TypeError:
        pass
    else:
        raise AssertionError("int mode did not raise TypeError")


def _lazy_and_close() -> None:
    calls = []

    def node(state: State) -> dict:
        calls.append(1)
        return {"x": 1}

    app = _one(node)
    iterator = app.stream({}, stream_mode="values")
    assert calls == []
    next(iterator)
    assert calls == []
    iterator.close()
    assert not [
        thread
        for thread in threading.enumerate()
        if thread.name.startswith("freegraph-node")
    ]


def _stream_none() -> None:
    app = _one(lambda state: {"x": 1})
    assert list(app.stream(None, stream_mode="values"))


def _command_rejected_lazily() -> None:
    app = _one(lambda state: {"x": 1})
    iterator = app.stream(Command(resume=1), stream_mode="values")
    try:
        next(iterator)
    except TypeError:
        return
    raise AssertionError("Command input did not raise TypeError on first next()")


def _static_rejected() -> None:
    builder = StateGraph(State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    app = builder.compile(interrupt_before=["a"])
    iterator = app.stream({}, stream_mode="values")
    try:
        next(iterator)
    except ValueError:
        return
    raise AssertionError("static interrupt point did not raise ValueError")


def _interrupt_and_failure() -> None:
    def stop(state: State) -> dict:
        interrupt("approve?")
        return {"x": 1}

    app = _one(stop)
    values = list(app.stream({}, stream_mode="values"))
    assert "__interrupt__" in values[-1]["payload"]
    updates = list(app.stream({}, stream_mode="updates"))
    assert "__interrupt__" in updates[-1]["payload"]
    tasks = list(app.stream({}, stream_mode="tasks"))
    assert tasks and tasks[0]["payload"].interrupts

    def boom(state: State) -> dict:
        get_stream_writer()({"m": "before"})
        raise RuntimeError("boom")

    failing = _one(boom)
    seen = []
    try:
        for event in failing.stream({}, stream_mode="custom"):
            seen.append(event["payload"])
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("failing node did not re-raise")
    assert seen == [{"m": "before"}]


def _recursion_limit() -> None:
    def node(state: State) -> dict:
        return {"x": int(state.get("x") or 0) + 1}

    builder = StateGraph(State)
    builder.add_node("loop", node)
    builder.add_edge(START, "loop")
    builder.add_edge("loop", "loop")
    app = builder.compile()
    try:
        list(app.stream({}, config={"recursion_limit": 3}, stream_mode="values"))
    except GraphRecursionError as exc:
        assert exc.recursion_limit == 3 and exc.current_step == 3
    else:
        raise AssertionError("recursion limit did not raise")


def _route_raw_config() -> None:
    seen = []

    def route(state: State, config) -> str:
        seen.append(config)
        return "b"

    builder = StateGraph(State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_conditional_edges("a", route, ["b"])
    builder.add_edge("b", END)
    app = builder.compile()
    raw = {"configurable": {"thread_id": "t-1"}, "recursion_limit": 9}
    list(app.stream({}, config=raw, stream_mode="updates"))
    assert seen == [raw] and seen[0] is raw


def _public_surface() -> None:
    import freegraph.contracts as contracts
    import freegraph.graph as graph
    import freegraph.runtime as runtime

    assert len(graph.__all__) == 8
    assert len(contracts.__all__) == 22
    assert len(runtime.__all__) == 23


def _zero_deps() -> None:
    import pathlib
    import re

    source = pathlib.Path(__file__).resolve().parents[3] / "src" / "freegraph"
    for path in source.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(langchain|langgraph|langsmith)", text, re.M)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-differential", action="store_true")
    parser.parse_args(argv)

    checks = [
        ("A1 · 七种 mode 被接受", _a1_seven_modes),
        ("A2 · values == invoke", _a2_values_equal_invoke),
        ("A3 · updates 可合并", _a3_updates_merge),
        ("V1 · 默认 None ⇒ updates", _default_none),
        ("V4 · custom / writer 注入", _custom_and_writer),
        ("V5 · tasks / debug", _tasks_debug),
        ("V6 · 四键信封 + id", _envelope_and_ids),
        ("V6b · RunConfig.run_id 被忽略", _run_config_run_id_ignored),
        ("V8 · 非法 mode", _invalid_modes),
        ("V9 · 惰性 / 提前停止", _lazy_and_close),
        ("V19 · stream(None)", _stream_none),
        ("V19b · Command 首次迭代拒绝", _command_rejected_lazily),
        ("V19c · 静态断点拒绝", _static_rejected),
        ("V10/V11 · 中断 / 失败", _interrupt_and_failure),
        ("V21 · 递归上限", _recursion_limit),
        ("V20 · 双参路由原始 config", _route_raw_config),
        ("V13 · 公开面 8/22/23", _public_surface),
        ("V16 · 零第三方 import", _zero_deps),
    ]
    ok = True
    for name, fn in checks:
        ok = _check(name, fn) and ok

    print()
    print(f"B8F2 acceptance: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
