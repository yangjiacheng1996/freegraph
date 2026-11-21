#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · 一键验收脚本（本地 JSONL trace 存储）。

一条命令跑完本 feature 的机械验收：

    .venv/bin/python harness/verification/B20F1/acceptance.py

覆盖：
- A1 trace 落盘（每个 run 一个 ``trace-<run_id>.jsonl``，含 span + record 行）；
- A2 零出站（socket 监测夹具「框架出站 == 0」）；
- A3 每行可独立 ``json.loads`` + C23 四项；
- A4 写入失败不阻断 + 四路诊断 + 无半行；
- A5 不启用零痕迹（未注入 / 只构造 / env 变量）。

只依赖标准库 + ``freegraph``；退出码 ``0`` = PASS · ``1`` = FAIL ·
``2`` = 环境未就绪。最后一行 MUST 打印 ``B20F1 acceptance: PASS|FAIL``。
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

try:
    from freegraph.graph import END, START, StateGraph
    from freegraph.observability import FileTraceStore
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"B20F1 acceptance: FAIL (environment: {exc})")
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


def _linear() -> StateGraph:
    builder = StateGraph(State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def _jsonl(directory: Path) -> list[dict[str, Any]]:
    files = sorted(directory.glob("trace-*.jsonl"))
    assert len(files) == 1, files
    return [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]


def _write() -> None:
    with tempfile.TemporaryDirectory() as raw:
        target = Path(raw) / "traces"
        store = FileTraceStore(target)
        assert _linear().compile(tracer=store).invoke({"x": 0})["x"] == 2
        files = sorted(target.glob("trace-*.jsonl"))
        check(len(files) == 1, "A1 每个 run 一个 trace-<run_id>.jsonl")
        objs = [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]
        check(any(obj["kind"] == "span" for obj in objs), "A1 含 span 行")
        check(any(obj["kind"] == "trace_record" for obj in objs), "A1 含 record 行")
        check(len([obj for obj in objs if obj["kind"] == "span"]) == 2, "A1 两个节点 span")
        check(
            len([obj for obj in objs if obj["kind"] == "trace_record"]) == 2,
            "A1 两个节点 record",
        )


@contextmanager
def _egress_monitor():
    calls: list[object] = []
    original_connect = socket.socket.connect
    original_create = socket.create_connection

    def connect(self, address):
        calls.append(address)
        return None

    def create_connection(address, *args, **kwargs):
        calls.append(address)
        return original_create(address, *args, **kwargs)

    socket.socket.connect = connect  # type: ignore[method-assign]
    socket.create_connection = create_connection  # type: ignore[assignment]
    try:
        yield calls
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.create_connection = original_create  # type: ignore[assignment]


def _zero_egress() -> None:
    with tempfile.TemporaryDirectory() as raw:
        target = Path(raw) / "traces"
        with _egress_monitor() as calls:
            store = FileTraceStore(target)
            _linear().compile(tracer=store).invoke({"x": 0})
        check(calls == [], "A2 框架出站 == 0")


def _parse_and_keys() -> None:
    with tempfile.TemporaryDirectory() as raw:
        target = Path(raw) / "traces"
        store = FileTraceStore(target)
        _linear().compile(tracer=store).invoke({"x": 0})
        for obj in _jsonl(target):
            check(isinstance(obj, dict), "A3 每行是 JSON 对象")
            check(
                {"run_id", "thread_id", "node", "checkpoint_id"} <= set(obj),
                "A3 含 C23 四项",
            )


class _WarningCounter(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _failure_isolation() -> None:
    with tempfile.TemporaryDirectory() as raw:
        target = Path(raw) / "occupied"
        target.write_text("occupied", encoding="utf-8")
        errors: list[BaseException] = []
        store = FileTraceStore(target, on_error=errors.append)
        logger = logging.getLogger("freegraph.observability._file_store")
        handler = _WarningCounter()
        logger.addHandler(handler)
        try:
            out = _linear().compile(tracer=store).invoke({"x": 0})
        finally:
            logger.removeHandler(handler)
        check(out["x"] == 2, "A4 写入失败不阻断图执行")
        check(store.write_errors > 0, "A4 write_errors > 0")
        check(bool(store.last_error), "A4 last_error 非空")
        check(
            len(errors) == store.write_errors and bool(errors),
            "A4 on_error 每次失败调用一次",
        )
        check(bool(handler.messages), "A4 logging.WARNING 出现")
        check(not list(target.parent.glob("trace-*.jsonl")), "A4 无 trace 文件产生")


def _default_off() -> None:
    with tempfile.TemporaryDirectory() as raw:
        target = Path(raw) / "traces"
        _linear().compile().invoke({"x": 0})
        check(not target.exists(), "A5 未注入 ⇒ 零目录 / 零文件")

        FileTraceStore(target)
        check(not target.exists(), "A5 只构造 ⇒ 零目录 / 零文件")

        old = {key: os.environ.get(key) for key in ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2", "FREEGRAPH_TRACE_DIR")}
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["FREEGRAPH_TRACE_DIR"] = str(Path(raw) / "env-target")
        try:
            _linear().compile().invoke({"x": 0})
            check(not target.exists(), "A5 env 不开启观测")
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def main() -> int:
    run("A1 落盘", _write)
    run("A2 零出站", _zero_egress)
    run("A3 解析 / 关联键", _parse_and_keys)
    run("A4 失败隔离", _failure_isolation)
    run("A5 默认关闭", _default_off)

    if _FAILURES:
        print(f"B20F1 acceptance: FAIL（{len(_FAILURES)} 项失败 / {_CHECKS} 项检查）")
        for failure in _FAILURES:
            print(f"  - {failure}")
        return 1
    print(f"B20F1 acceptance: PASS（{_CHECKS} 项检查）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
