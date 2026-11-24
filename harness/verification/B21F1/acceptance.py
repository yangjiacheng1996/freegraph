#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B21F1 · 一键验收（OTLP 导出插件 + 三后端示例）。

覆盖 A1–A5：
- A1 可选 extra + 不自研 OTLP 编码；
- A2 三个后端最小对接示例；
- A3 已知失效风险说明；
- A4 默认关闭 / 零出站；
- A5 可导出到 OTel 后端（桩 + 最小 gRPC 接收端）。

只依赖标准库 + freegraph（[otlp] 已安装）。退出码 0 = PASS · 1 = FAIL ·
2 = 环境未就绪。最后一行 MUST 打印 ``B21F1 acceptance: PASS|FAIL``。
"""

from __future__ import annotations

import ast
import os
import socket
import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

try:
    from freegraph.graph import END, START, StateGraph
    from freegraph.observability import OtlpExporter
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"B21F1 acceptance: FAIL (environment: {exc})")
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


class _State(TypedDict, total=False):
    x: int


class _Fake:
    def invoke(self, value: Any) -> Any:
        return value


def _graph(tracer: Any = None) -> Any:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_node("b", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder.compile(tracer=tracer)


class _RecordingExporter:
    def __init__(self) -> None:
        self.spans: list[Any] = []
        self.calls = 0

    def export(self, spans: Any) -> None:
        self.calls += 1
        self.spans.extend(spans)
        return None


def _a1() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    check(project["dependencies"] == [], "A1 基础依赖为空")
    otlp = project["optional-dependencies"]["otlp"]
    check(
        otlp
        == [
            "opentelemetry-api>=1.20",
            "opentelemetry-sdk>=1.20",
            "opentelemetry-exporter-otlp-proto-grpc>=1.20",
        ],
        "A1 [otlp] 仅 gRPC 协议实现 + OTel SDK",
    )
    check(not any("certifi" in item or "proto-http" in item for item in otlp), "A1 无 certifi / HTTP exporter")
    violations: list[str] = []
    for path in sorted((SRC_DIR / "freegraph").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "OTLPSpanExporter" in text:
            violations.append(f"{path.name}: OTLPSpanExporter")
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("google.protobuf"):
                        violations.append(f"{path.name}: {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("google.protobuf"):
                    violations.append(f"{path.name}: {node.module}")
            elif isinstance(node, ast.Attribute) and node.attr == "SerializeToString":
                violations.append(f"{path.name}: SerializeToString")
    check(violations == [], "A1 无自研 protobuf / wire 编码 / OTLPSpanExporter 门面")


def _a2() -> None:
    examples = REPO_ROOT / "harness" / "examples" / "B21F1"
    for name in ("phoenix.py", "openlit.py", "langfuse.py", "README.md"):
        check((examples / name).is_file(), f"A2 示例存在：{name}")
    env = {**os.environ, "PYTHONPATH": str(SRC_DIR), "PYTHONUTF8": "1"}
    for name in ("phoenix.py", "openlit.py", "langfuse.py"):
        proc = subprocess.run(
            [sys.executable, str(examples / name), "--help"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        check(proc.returncode == 0 and "--endpoint" in proc.stdout, f"A2 --help 成功：{name}")


def _a3() -> None:
    text = (REPO_ROOT / "harness" / "examples" / "B21F1" / "README.md").read_text(encoding="utf-8")
    for marker in (
        "OpenLIT 旧路径 404",
        "https://docs.openlit.io/latest/overview",
        "as-of",
        "能力分工 / 重叠",
        "无默认推荐",
        "HTTP exporter 是**用户侧依赖**",
        "只连不嵌",
    ):
        check(marker in text, f"A3 文档标记：{marker}")


def _a4() -> None:
    code = """
from typing import TypedDict
from freegraph.graph import END, START, StateGraph
import sys
class S(TypedDict, total=False):
    x: int
b = StateGraph(S)
b.add_node('a', lambda s: {'x': 1})
b.add_edge(START, 'a')
b.add_edge('a', END)
assert b.compile().invoke({'x': 0})['x'] == 1
assert 'opentelemetry' not in sys.modules
assert 'grpc' not in sys.modules
print('ok')
"""
    env = {
        **os.environ,
        "PYTHONPATH": str(SRC_DIR),
        "PYTHONUTF8": "1",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://127.0.0.1:4318",
        "LANGSMITH_TRACING": "true",
    }
    proc = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    check(proc.returncode == 0 and proc.stdout.strip() == "ok", "A4 默认关闭 / 零 OTel import / 忽略 env")

    egress: list[Any] = []
    original_connect = socket.socket.connect
    original_create = socket.create_connection

    def connect(self: Any, address: Any, *args: Any, **kwargs: Any) -> Any:
        egress.append(address)
        return original_connect(self, address, *args, **kwargs)

    def create(address: Any, *args: Any, **kwargs: Any) -> Any:
        egress.append(address)
        return original_create(address, *args, **kwargs)

    socket.socket.connect = connect  # type: ignore[method-assign]
    socket.create_connection = create  # type: ignore[assignment]
    try:
        _graph().invoke({"x": 0})
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.create_connection = original_create  # type: ignore[assignment]
    check(egress == [], "A4 默认路径框架出站 == 0")


def _a5_stub() -> None:
    recording = _RecordingExporter()
    exporter = OtlpExporter(exporter=recording)
    check(_graph(exporter).invoke({"x": 0}) == {"x": 2}, "A5 桩 exporter：图结果不变")
    check(recording.calls == 2 and len(recording.spans) == 2, "A5 桩 exporter：2 个完整 span")


def _a5_grpc() -> None:
    try:
        import grpc
        from opentelemetry.proto.collector.trace.v1 import (
            trace_service_pb2,
            trace_service_pb2_grpc,
        )
    except ImportError as exc:  # pragma: no cover - 环境未就绪
        raise RuntimeError(f"gRPC / OTel proto unavailable: {exc}") from exc

    class Servicer(trace_service_pb2_grpc.TraceServiceServicer):
        def __init__(self) -> None:
            self.requests: list[Any] = []

        def Export(self, request: Any, context: Any) -> Any:  # noqa: N802
            self.requests.append(request)
            return trace_service_pb2.ExportTraceServiceResponse()

    servicer = Servicer()
    server = grpc.server(ThreadPoolExecutor(max_workers=4))
    trace_service_pb2_grpc.add_TraceServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    try:
        exporter = OtlpExporter(endpoint=f"127.0.0.1:{port}", insecure=True)
        check(_graph(exporter).invoke({"x": 0}) == {"x": 2}, "A5 最小 gRPC：图结果不变")
    finally:
        server.stop(0).wait()
    spans = [
        span
        for request in servicer.requests
        for resource in request.resource_spans
        for scope in resource.scope_spans
        for span in scope.spans
    ]
    check(len(servicer.requests) == 2 and len(spans) == 2, "A5 最小 gRPC：每 span 一次 Export")
    check(all(span.trace_id for span in spans), "A5 最小 gRPC：trace_id 非空")


def main() -> int:
    run("A1", _a1)
    run("A2", _a2)
    run("A3", _a3)
    run("A4", _a4)
    run("A5-stub", _a5_stub)
    run("A5-grpc", _a5_grpc)
    print(f"checks = {_CHECKS}, failures = {len(_FAILURES)}")
    if _FAILURES:
        print("B21F1 acceptance: FAIL")
        return 1
    print("B21F1 acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
