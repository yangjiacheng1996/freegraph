#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · 一键验收脚本（`TraceSink` 接入 + `current_span()` + 默认关闭）。

一条命令跑完本 feature 的机械验收：

    .venv/bin/python harness/verification/B19F1/acceptance.py

覆盖：
- A1 嵌套 span 父子关系正确（节点 / 模型 / 工具 / 三层嵌套）；
- A2 不注入 tracer 时零副作用（Span / producer / record / run-id 绑定均 0）；
- A3 `current_span()` 嵌套恢复、空上下文 `None`；
- A4 注入即推送、成败皆成对；接收端异常隔离；
- A5 `stream()` 与 span 共享 `run_id` / `thread_id`，信封不含 trace；
- A6 补充记录与节点 span 一一对齐；触发源 / 并发组 / 屏障组 / JSON 可判定；
- A7 零依赖 / 零环境变量 / 零出站；L5 惰性；人工验证记录存在。

只依赖标准库 + ``freegraph``；退出码 ``0`` = PASS · ``1`` = FAIL ·
``2`` = 环境未就绪。最后一行 MUST 打印 ``B19F1 acceptance: PASS|FAIL``。
"""

from __future__ import annotations

import ast
import json
import logging
import operator
import os
import socket
import subprocess
import sys
import tomllib
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

try:
    from freegraph.graph import END, START, Command, RunConfig, Send, StateGraph
    from freegraph.observability import (
        SpanProducer,
        current_span,
        invoke_model,
        invoke_tool,
    )
    from freegraph.observability._producer import bind_tracer as bind_l5
    from freegraph.runtime._span_hook import bind_span_tracer
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"B19F1 acceptance: FAIL (environment: {exc})")
    raise SystemExit(2) from exc

_FAILURES: list[str] = []
_CHECKS = 0


def check(condition: Any, label: str) -> bool:
    global _CHECKS
    _CHECKS += 1
    if condition:
        print(f"[PASS] {label}")
        return True
    print(f"[FAIL] {label}")
    _FAILURES.append(label)
    return False


def run(name: str, fn: Any) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - 单组失败不中断其余检查
        print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
        _FAILURES.append(name)


class State(TypedDict, total=False):
    x: int
    log: Annotated[list, operator.add]


class Sink:
    def __init__(self) -> None:
        self.started: list[Any] = []
        self.ended: list[Any] = []
        self.records: list[Any] = []

    def on_span_start(self, span: Any) -> None:
        self.started.append(span)

    def on_span_end(self, span: Any) -> None:
        self.ended.append(span)

    def on_trace_record(self, record: Any) -> None:
        self.records.append(record)

    def current_span(self) -> Any:
        return None


class FailingSink(Sink):
    def on_span_start(self, span: Any) -> None:
        raise RuntimeError("sink boom")

    def on_span_end(self, span: Any) -> None:
        raise RuntimeError("sink boom")

    def on_trace_record(self, record: Any) -> None:
        raise RuntimeError("sink boom")


class Model:
    model_name = "demo-model"

    def invoke(self, value: Any) -> Any:
        return value


class Tool:
    name = "demo-tool"
    description = "demo"

    def invoke(self, value: Any) -> Any:
        return value


def _linear() -> StateGraph:
    builder = StateGraph(State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def _nested() -> None:
    observed: list[Any] = []

    def node(state: State) -> State:
        observed.append(current_span())
        invoke_model(Model(), 1)
        invoke_tool(Tool(), 2)
        observed.append(current_span())
        return {"x": 1}

    builder = StateGraph(State)
    builder.add_node("node", node)
    builder.add_edge(START, "node")
    builder.add_edge("node", END)
    sink = Sink()
    builder.compile(tracer=sink).invoke({"x": 0})

    node_span = observed[0]
    model_span = next(span for span in sink.started if span.name == "chat demo-model")
    tool_span = next(span for span in sink.started if span.name == "execute_tool demo-tool")
    check(node_span is not None, "A1 节点内 current_span() 非空")
    check(model_span.parent == node_span.id, "A1 模型 span parent == 节点 span id")
    check(tool_span.parent == node_span.id, "A1 工具 span parent == 节点 span id")
    check(observed[1] is node_span, "A3 子 span 结束后恢复父级 current_span")
    check(current_span() is None, "A3 离开所有 span 后 current_span() == None")
    check(all(span.context == {} for span in sink.started), "A1 Span.context 恒空")


class _SpanCounter:
    def __init__(self) -> None:
        self.spans = 0
        self.producers = 0
        self.bindings = 0
        self._restore: list[tuple[Any, str, Any]] = []

    def __enter__(self) -> "_SpanCounter":
        import freegraph._stategraph as stategraph
        import freegraph.observability._inject as inject_module
        import freegraph.observability._producer as producer_module
        import freegraph.runtime._span_hook as hook_module
        import freegraph.runtime._stream_context as stream_context
        import freegraph.runtime.superstep as superstep

        for module in (hook_module, producer_module):
            original = module.Span

            def span_wrapper(*args: Any, __original: Any = original, **kwargs: Any) -> Any:
                self.spans += 1
                return __original(*args, **kwargs)

            module.Span = span_wrapper
            self._restore.append((module, "Span", original))

        original_producer = producer_module.SpanProducer
        original_inject_producer = inject_module.SpanProducer

        def producer_wrapper(*args: Any, **kwargs: Any) -> Any:
            self.producers += 1
            return original_producer(*args, **kwargs)

        producer_module.SpanProducer = producer_wrapper
        inject_module.SpanProducer = producer_wrapper
        self._restore.append((producer_module, "SpanProducer", original_producer))
        self._restore.append((inject_module, "SpanProducer", original_inject_producer))

        original_bind = stream_context.bind_run_ids

        def bind_wrapper(run_id: str, thread_id: str | None) -> Any:
            self.bindings += 1
            return original_bind(run_id, thread_id)

        for module in (stream_context, stategraph, superstep):
            if hasattr(module, "bind_run_ids"):
                original = module.bind_run_ids
                module.bind_run_ids = bind_wrapper
                self._restore.append((module, "bind_run_ids", original))
        return self

    def __exit__(self, *args: Any) -> None:
        for module, name, original in reversed(self._restore):
            setattr(module, name, original)


def _default_off() -> None:
    counter = _SpanCounter()
    with counter:
        assert _linear().compile().invoke({"x": 0})["x"] == 2
    check(counter.spans == 0, "A2 未注入 ⇒ Span 构造数 == 0")
    check(counter.producers == 0, "A2 未注入 ⇒ SpanProducer 构造数 == 0")
    check(counter.bindings == 0, "A2 未注入 ⇒ span 专用 run_id 绑定数 == 0")

    sink = Sink()
    counter = _SpanCounter()
    with counter:
        _linear().compile(tracer=sink)
    check(counter.spans == 0 and counter.producers == 0, "A2 注入但从不运行 ⇒ 零构造")


def _exception_path() -> None:
    error = RuntimeError("boom")

    def boom(state: State) -> State:
        raise error

    builder = StateGraph(State)
    builder.add_node("boom", boom)
    builder.add_edge(START, "boom")
    builder.add_edge("boom", END)
    sink = Sink()
    try:
        builder.compile(tracer=sink).invoke({"x": 0})
    except RuntimeError as caught:
        check(caught is error, "A4 异常原对象原样重抛")
    else:
        check(False, "A4 异常原对象原样重抛")
    check(len(sink.started) == len(sink.ended) == 1, "A4 异常路径 start / end 成对")
    check(sink.records and sink.records[0].error is error, "A4 record.error = 原异常对象")

    failing = FailingSink()
    logging.disable(logging.CRITICAL)
    try:
        _linear().compile(tracer=failing).invoke({"x": 0})
    except Exception as exc:  # noqa: BLE001 - 验收判据：接收端异常必须被隔离
        check(False, f"A4 接收端异常被隔离（实际抛出 {type(exc).__name__}）")
    else:
        check(True, "A4 接收端异常被隔离")
    finally:
        logging.disable(logging.NOTSET)


def _stream_ids() -> None:
    sink = Sink()
    app = _linear().compile(tracer=sink)
    events = list(
        app.stream(
            {"x": 0},
            config=RunConfig(thread_id="t-1", run_id="user-supplied"),
            stream_mode="updates",
        )
    )
    event_ids = {(event["run_id"], event["thread_id"]) for event in events}
    span_ids = {(span.run_id, span.thread_id) for span in sink.started}
    check(event_ids == span_ids, "A5 stream 事件与 span 共享 run_id / thread_id")
    check(all("trace" not in event for event in events), "A5 stream 信封不含 trace 字段")
    check(
        all(span.run_id != "user-supplied" for span in sink.started),
        "A5 RunConfig.run_id 被忽略",
    )


def _trigger_graph() -> StateGraph:
    def a(state: State) -> Command:
        return Command(update={"log": ["a"]}, goto="c")

    def fan(state: State) -> list[Send]:
        return [Send("worker", {"log": ["w"]})]

    builder = StateGraph(State)
    builder.add_node("a", a)
    builder.add_node("b", lambda state: {"log": ["b"]})
    builder.add_node("c", lambda state: {})
    builder.add_node("fan", fan)
    builder.add_node("worker", lambda state: {})
    builder.add_edge(START, "a")
    builder.add_edge(START, "fan")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    builder.add_edge("c", END)
    builder.add_edge("fan", "worker")
    builder.add_edge("worker", END)
    return builder


def _barrier_graph() -> StateGraph:
    builder = StateGraph(State)
    builder.add_node("a", lambda state: {"log": ["a"]})
    builder.add_node("b", lambda state: {"log": ["b"]})
    builder.add_node("c", lambda state: {"log": ["c"]})
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_edge(["a", "b"], "c")
    builder.add_edge("c", END)
    return builder


def _records() -> None:
    sink = Sink()
    _trigger_graph().compile(tracer=sink).invoke({"log": []})
    by_node = {record.node: record for record in sink.records}
    check(len(sink.records) == len(sink.started), "A6 record 数 == 节点 span 数")
    check(by_node["b"].triggers == (("e", "a"),), "A6 静态边触发源")
    check(by_node["c"].triggers == (("e", "a"),), "A6 Command.goto 触发源")
    check(by_node["worker"].triggers == (("send", "fan", 0),), "A6 Send fan-out 触发源")
    check(
        all(json.dumps(record.to_jsonable()) for record in sink.records),
        "A6 TraceRecord JSON 视图可序列化",
    )

    barrier_sink = Sink()
    _barrier_graph().compile(tracer=barrier_sink).invoke({"log": []})
    c_record = next(record for record in barrier_sink.records if record.node == "c")
    check(c_record.barrier_groups == (("a", "b"),), "A6 屏障组 == (('a','b'),)")
    check(c_record.concurrency_group == ("c",), "A6 并发组可判定")


class _EgressGuard:
    def __init__(self) -> None:
        self.calls = 0
        self._connect = socket.socket.connect
        self._create = socket.create_connection

    def __enter__(self) -> "_EgressGuard":
        def connect(instance: Any, address: Any) -> Any:
            self.calls += 1
            raise AssertionError("框架尝试出站")

        def create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
            self.calls += 1
            raise AssertionError("框架尝试出站")

        socket.socket.connect = connect  # type: ignore[method-assign]
        socket.create_connection = create_connection  # type: ignore[assignment]
        return self

    def __exit__(self, *args: Any) -> None:
        socket.socket.connect = self._connect  # type: ignore[method-assign]
        socket.create_connection = self._create  # type: ignore[assignment]


def _surface_and_dependencies() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    check(data["project"]["dependencies"] == [], "A7 基础安装依赖闭包为空")

    forbidden_roots = {"langchain", "langgraph", "langsmith", "opentelemetry"}
    files = list((SRC_DIR / "freegraph" / "observability").glob("*.py"))
    files.append(SRC_DIR / "freegraph" / "runtime" / "_span_hook.py")
    violations: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        if "os.environ" in text or "os.getenv" in text:
            violations.append(f"{path.name}: env read")
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots = [node.module.split(".")[0]]
            else:
                continue
            for root in roots:
                if root in forbidden_roots:
                    violations.append(f"{path.name}: import {root}")
    check(violations == [], f"A7 新源码无禁用 import / env 读取（{violations}）")

    code = (
        "import sys; import freegraph; "
        "loaded=sorted(m for m in sys.modules if m.startswith('freegraph.')); "
        "assert loaded == [], loaded; print('ok')"
    )
    env = {**os.environ, "PYTHONPATH": str(SRC_DIR)}
    proc = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    check(proc.returncode == 0 and proc.stdout.strip() == "ok", "A7 import freegraph 保持惰性")

    os.environ["LANGSMITH_TRACING"] = "true"
    try:
        counter = _SpanCounter()
        with counter:
            assert _linear().compile().invoke({"x": 0})["x"] == 2
        check(
            counter.spans == 0 and counter.producers == 0,
            "A7 LANGSMITH_TRACING=true 不改变默认关闭",
        )
    finally:
        os.environ.pop("LANGSMITH_TRACING", None)

    record = REPO_ROOT / "harness" / "verification" / "B19F1" / "manual-verification.md"
    check(record.is_file() and record.stat().st_size > 0, "A7 人工验证记录存在且非空")
    check("B19F1" in record.read_text(encoding="utf-8"), "A7 人工验证记录含 B19F1")


def _zero_egress() -> None:
    sink = Sink()
    guard = _EgressGuard()
    with guard:
        _linear().compile(tracer=sink).invoke({"x": 0})
    check(guard.calls == 0, "A7 框架出站 == 0")


def main() -> int:
    print("══ B19F1 acceptance · TraceSink 接入 + current_span() + 默认关闭 ══")
    for name, fn in (
        ("A1/A3 嵌套 / current_span", _nested),
        ("A2 默认关闭 / 零开销", _default_off),
        ("A4 注入推送 / 异常隔离", _exception_path),
        ("A5 stream 同源同 id", _stream_ids),
        ("A6 补充记录 / 触发源 / 并发 / 屏障", _records),
        ("A7 依赖 / env / 惰性 / 人工记录", _surface_and_dependencies),
        ("A7 零出站", _zero_egress),
    ):
        run(name, fn)

    if _FAILURES:
        print(f"B19F1 acceptance: FAIL（{len(_FAILURES)} 项失败 / {_CHECKS} 项检查）")
        for failure in _FAILURES:
            print(f"  - {failure}")
        return 1
    print(f"B19F1 acceptance: PASS（{_CHECKS} 项检查）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
