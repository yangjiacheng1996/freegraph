#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · 一键验收脚本（节点 / 工具 / 模型三级 span）。

一条命令跑完本 feature 的机械验收：

    .venv/bin/python harness/verification/B18F1/acceptance.py

覆盖：
- A1 三级 span 可生产；模型 / 工具属性最小集；节点属性 / context 恒空；
- A2 未绑定 tracer ⇒ 零 Span 构造 / 零回调 / 零 span 专用 run_id；
- A3 stream 事件与 span 共享 run_id / thread_id；RunConfig.run_id 被忽略；
- A4 并发节点 span 独立；模型 / 工具子 span 不跨任务串父；
- A5 依赖闭包为空；公开门面 / L2 ``__all__`` 不变；新源码无禁用 import；
- A6 零出站（socket 监测）；
- A7 人工验证记录存在且非空。

只依赖标准库 + ``freegraph``；退出码 ``0`` = PASS · ``1`` = FAIL ·
``2`` = 环境未就绪。最后一行 MUST 打印 ``B18F1 acceptance: PASS|FAIL``。
"""

from __future__ import annotations

import importlib.metadata
import socket
import sys
from pathlib import Path
from typing import Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

try:
    from freegraph.graph import END, START, RunConfig, Send, StateGraph
    from freegraph.observability import SpanProducer, invoke_model, invoke_tool
    from freegraph.observability._producer import bind_tracer as bind_l5
    from freegraph.runtime._span_hook import bind_span_tracer
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"B18F1 acceptance: FAIL (environment: {exc})")
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


class _Receiver:
    def __init__(self) -> None:
        self.started: list[Any] = []
        self.ended: list[Any] = []

    def on_span_start(self, span: Any) -> None:
        self.started.append(span)

    def on_span_end(self, span: Any) -> None:
        self.ended.append(span)


class State(TypedDict, total=False):
    x: int
    result: int


class Model:
    model_name = "demo-model"

    def invoke(self, value: Any) -> Any:
        return value


class Tool:
    name = "multiply"
    description = "Multiply"

    def invoke(self, value: Any) -> Any:
        return value


def _bind(producer: SpanProducer) -> Any:
    from contextlib import contextmanager

    @contextmanager
    def _scope() -> Any:
        with bind_span_tracer(producer), bind_l5(producer):
            yield producer

    return _scope()


def _three_levels() -> None:
    def node(state: State) -> State:
        invoke_model(Model(), 1)
        invoke_tool(Tool(), 2, call_id="call-1")
        return {"result": 1}

    builder = StateGraph(State)
    builder.add_node("node", node)
    builder.add_edge(START, "node")
    builder.add_edge("node", END)
    compiled = builder.compile()
    receiver = _Receiver()
    producer = SpanProducer(receiver)
    with _bind(producer):
        compiled.invoke({})

    node_span = next(span for span in receiver.started if span.name == "node")
    model_span = next(span for span in receiver.started if span.name == "chat demo-model")
    tool_span = next(span for span in receiver.started if span.name == "execute_tool multiply")
    check(len(receiver.started) == 3, "A1 三级 span 各一例")
    check(len(receiver.ended) == 3, "A1 三级 span 均已成对结束")
    check(node_span.attributes == {} and node_span.context == {}, "A1 节点属性 / context 恒空")
    check(
        dict(model_span.attributes)
        == {"gen_ai.operation.name": "chat", "gen_ai.request.model": "demo-model"},
        "A1 模型 span 最小属性集",
    )
    check(
        dict(tool_span.attributes)
        == {
            "gen_ai.operation.name": "execute_tool",
            "gen_ai.tool.name": "multiply",
            "gen_ai.tool.call.id": "call-1",
        },
        "A1 工具 span 最小属性集",
    )
    check(model_span.parent == node_span.id, "A1 模型 span parent == 节点 span id")
    check(tool_span.parent == node_span.id, "A1 工具 span parent == 节点 span id")


class _SpanCounter:
    def __init__(self) -> None:
        self.count = 0
        self.bindings = 0
        self._restore: list[tuple[Any, str, Any]] = []

    def __enter__(self) -> "_SpanCounter":
        import freegraph.observability._producer as producer_module
        import freegraph.runtime._span_hook as hook_module
        import freegraph.runtime._stream_context as stream_context
        import freegraph.runtime.superstep as superstep

        for module in (hook_module, producer_module):
            original = module.Span

            def wrapper(*args: Any, __original: Any = original, **kwargs: Any) -> Any:
                self.count += 1
                return __original(*args, **kwargs)

            module.Span = wrapper
            self._restore.append((module, "Span", original))

        original_bind = stream_context.bind_run_ids

        def bind_wrapper(run_id: str, thread_id: str | None) -> Any:
            self.bindings += 1
            return original_bind(run_id, thread_id)

        stream_context.bind_run_ids = bind_wrapper
        self._restore.append((stream_context, "bind_run_ids", original_bind))
        superstep.bind_run_ids = bind_wrapper
        self._restore.append((superstep, "bind_run_ids", original_bind))
        return self

    def __exit__(self, *args: Any) -> None:
        for module, name, original in reversed(self._restore):
            setattr(module, name, original)


def _zero_overhead() -> None:
    builder = StateGraph(State)
    builder.add_node("n", lambda state: {"x": 1})
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    compiled = builder.compile()
    counter = _SpanCounter()
    with counter:
        compiled.invoke({"x": 0})
    check(counter.count == 0, "A2 未绑定 tracer ⇒ Span 构造数 == 0")
    check(counter.bindings == 0, "A2 未绑定 tracer ⇒ span 专用 run_id 绑定数 == 0")


def _stream_ids() -> None:
    builder = StateGraph(State)
    builder.add_node("n", lambda state: {"x": 1})
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    compiled = builder.compile()
    receiver = _Receiver()
    producer = SpanProducer(receiver)
    with _bind(producer):
        events = list(
            compiled.stream(
                {"x": 0},
                config=RunConfig(thread_id="t-1", run_id="user-supplied"),
                stream_mode="values",
            )
        )
    event_run_id = events[0]["run_id"]
    event_thread_id = events[0]["thread_id"]
    check(event_run_id != "user-supplied", "A3 RunConfig.run_id 被忽略")
    check(
        all(span.run_id == event_run_id for span in receiver.started),
        "A3 stream 事件与 span 共享 run_id",
    )
    check(
        all(span.thread_id == event_thread_id == "t-1" for span in receiver.started),
        "A3 stream 事件与 span 共享 thread_id",
    )


class DynamicTool:
    def __init__(self, name: str) -> None:
        self.name = name
        self.description = "dynamic"

    def invoke(self, value: Any) -> None:
        return None


def _concurrency() -> None:
    def worker(state: State) -> State:
        invoke_tool(DynamicTool(f"tool-{state['x']}"), {})
        return {}

    builder = StateGraph(State)
    builder.add_node(
        "fan", lambda state: [Send("worker", {"x": value}) for value in (1, 2, 3)]
    )
    builder.add_node("worker", worker)
    builder.add_edge(START, "fan")
    builder.add_edge("fan", "worker")
    builder.add_edge("worker", END)
    compiled = builder.compile()
    receiver = _Receiver()
    producer = SpanProducer(receiver)
    with _bind(producer):
        compiled.invoke({"x": 0}, config=RunConfig(max_concurrency=3))

    workers = [
        span for span in receiver.started if span.name == "worker" and not span.attributes
    ]
    tools = [
        span
        for span in receiver.started
        if span.attributes.get("gen_ai.operation.name") == "execute_tool"
    ]
    check(len(workers) == 3, "A4 3 个并发节点各 1 个节点 span")
    check(all(span.parent is None for span in workers), "A4 并发顶层节点 parent 均为 None")
    check(
        {span.parent for span in tools} == {span.id for span in workers},
        "A4 工具 span 只挂在本任务节点下",
    )


def _surface_and_dependencies() -> None:
    import freegraph.graph as graph
    import freegraph.runtime as runtime

    check(len(graph.__all__) == 8, "A5 freegraph.graph 公开符号数不变（8）")
    check(len(runtime.__all__) == 23, "A5 freegraph.runtime.__all__ 不变（23）")
    try:
        requires = importlib.metadata.requires("freegraph") or []
    except importlib.metadata.PackageNotFoundError:
        requires = []
    check(requires == [], "A5 基础安装依赖闭包为空")

    import ast

    forbidden_roots = {
        "langchain",
        "langgraph",
        "langsmith",
        "opentelemetry",
        "socket",
        "http",
        "urllib",
        "requests",
        "httpx",
    }
    files = list((SRC_DIR / "freegraph" / "observability").glob("*.py"))
    files.append(SRC_DIR / "freegraph" / "runtime" / "_span_hook.py")
    violations: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        if "os.environ" in text or "os.getenv" in text:
            violations.append(f"{path.name}: env read")
        tree = ast.parse(text, filename=str(path))
        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
        for root in sorted(roots & forbidden_roots):
            violations.append(f"{path.name}: import {root}")
    check(violations == [], f"A5 新源码无禁用 import / env 读取（{violations}）")


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


def _zero_egress() -> None:
    builder = StateGraph(State)
    builder.add_node("n", lambda state: {"result": 1})
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    compiled = builder.compile()
    receiver = _Receiver()
    producer = SpanProducer(receiver)
    guard = _EgressGuard()
    with guard, _bind(producer):
        compiled.invoke({})
    check(guard.calls == 0, "A6 框架出站 == 0")


def _manual_record() -> None:
    record = REPO_ROOT / "harness" / "verification" / "B18F1" / "manual-verification.md"
    check(record.is_file() and record.stat().st_size > 0, "A7 人工验证记录存在且非空")
    check("B18F1" in record.read_text(encoding="utf-8"), "A7 人工验证记录含 B18F1")


def main() -> int:
    print("══ B18F1 acceptance · Span 数据类生产 ══")
    for name, fn in (
        ("A1 三级 span", _three_levels),
        ("A2 零开销", _zero_overhead),
        ("A3 关联键 / stream 同源", _stream_ids),
        ("A4 并发隔离", _concurrency),
        ("A5 公开面 / 依赖", _surface_and_dependencies),
        ("A6 零出站", _zero_egress),
        ("A7 人工记录", _manual_record),
    ):
        run(name, fn)

    if _FAILURES:
        print(f"B18F1 acceptance: FAIL（{len(_FAILURES)} 项失败 / {_CHECKS} 项检查）")
        for failure in _FAILURES:
            print(f"  - {failure}")
        return 1
    print(f"B18F1 acceptance: PASS（{_CHECKS} 项检查）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
