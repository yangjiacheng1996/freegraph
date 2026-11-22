#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B14F1 · 一键验收脚本（Checkpointer + ``MemorySaver``）。

一条命令跑完本 feature 的机械验收：

    .venv/bin/python harness/verification/B14F1/acceptance.py

覆盖：协议 / 快照计数 / pending writes / 动态恢复 / 静态挂起 / context /
编译期校验 / span ``checkpoint_id`` / ``on_checkpoint`` / 线程隔离。

**只依赖标准库 + ``freegraph`` 本身**；退出码 ``0`` = PASS · ``1`` = FAIL
· ``2`` = 环境未就绪。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

try:
    from freegraph.contracts import Checkpointer, Command, RunConfig
    from freegraph.graph import END, START, StateGraph, interrupt
    from freegraph.observability import invoke_model
    from freegraph.persistence import InMemorySaver, MemorySaver
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"[环境未就绪] 无法导入 freegraph：{exc}")
    raise SystemExit(2) from exc


class _State(TypedDict, total=False):
    x: Any


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


class _Receiver:
    def __init__(self) -> None:
        self.started: list[Any] = []
        self.ended: list[Any] = []

    def on_span_start(self, span: Any) -> None:
        self.started.append(span)

    def on_span_end(self, span: Any) -> None:
        self.ended.append(span)

    def current_span_id(self) -> str | None:
        return self.started[-1].id if self.started else None


class _Model:
    def invoke(self, value: Any) -> str:
        return "ok"


def _linear() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def v1_protocol() -> None:
    saver = MemorySaver()
    check(isinstance(saver, Checkpointer), "V1 MemorySaver 满足 Checkpointer 协议")
    check(InMemorySaver is MemorySaver, "V1 InMemorySaver is MemorySaver")
    for name in (
        "get_tuple",
        "list",
        "put",
        "put_writes",
        "delete_thread",
        "delete_for_runs",
        "copy_thread",
        "get_next_version",
    ):
        check(callable(getattr(saver, name)), f"V1 方法存在：{name}")


def v2_snapshots_and_writes() -> None:
    saver = MemorySaver()
    cfg = RunConfig(thread_id="v2")
    _linear().compile(checkpointer=saver).invoke({"x": 0}, cfg)
    items = list(saver.list(cfg))
    check(len(items) == 3, "V2 a→b 快照数 == 3")
    check(items[0].snapshot.values == {"x": 2}, "V2 最新快照值正确")
    check(items[-1].snapshot.next == ("a",), "V2 初始快照 next 正确")

    cfg2 = saver.put(cfg, values={"x": 1}, metadata={"next": ()})
    saver.put_writes(cfg2, writes=[("x", 2)], task_id="n", task_path="n")
    stored = saver.get_tuple(cfg2)
    check(stored is not None, "V2 get_tuple 命中指定 id")
    check(stored is not None and stored.snapshot.values == {"x": 1}, "V2 pending writes 不污染 values")
    check(stored is not None and stored.pending_writes == (("n", "x", 2),), "V2 pending writes 取回")


def v3_dynamic_resume() -> None:
    seen: list[Any] = []
    builder = StateGraph(_State)

    def ask(state: _State) -> _State:
        seen.append(interrupt("approve?"))
        return {"x": "yes"}

    builder.add_node("ask", ask)
    builder.add_edge(START, "ask")
    builder.add_edge("ask", END)
    saver = MemorySaver()
    cfg = RunConfig(thread_id="v3")
    app = builder.compile(checkpointer=saver)
    first = app.invoke({"x": 0}, cfg)
    check("__interrupt__" in first, "V3 首次 invoke 挂起")
    check(len(list(saver.list(cfg))) == 2, "V3 动态挂起快照数 == 2")
    stored = saver.get_tuple(cfg)
    check(stored is not None and stored.snapshot.tasks == (), "V3 挂起快照 tasks == ()")
    check(
        stored is not None
        and any(channel == "__interrupt__" for _t, channel, _v in stored.pending_writes),
        "V3 挂起态有 __interrupt__ pending write",
    )
    second = app.invoke(Command(resume="yes"), cfg)
    check(second.get("x") == "yes", "V3 恢复得到 resume 值")
    check(seen == ["yes"], "V3 只重跑被中断节点")
    check(len(list(saver.list(cfg))) == 3, "V3 恢复后快照数 == 3")


def v4_static_before() -> None:
    saver = MemorySaver()
    cfg = RunConfig(thread_id="v4")
    app = _linear().compile(checkpointer=saver, interrupt_before=["a"])
    first = app.invoke({"x": 0}, cfg)
    check("__interrupt__" in first, "V4 首轮前静态挂起")
    items = list(saver.list(cfg))
    check(len(items) == 1, "V4 首轮前静态挂起快照数 == 1")
    check(items[0].snapshot.next == ("a",), "V4 挂起快照 next 指向待执行节点")
    check(items[0].snapshot.tasks == (), "V4 挂起快照 tasks == ()")
    check(items[0].scheduler.get("suspension_kind") == "static_before", "V4 suspension_kind == static_before")
    app.invoke(Command(resume="ignored"), cfg)
    check(list(saver.list(cfg))[0].snapshot.next == (), "V4 恢复后收敛")


def v5_context_not_persisted() -> None:
    saver = MemorySaver()
    cfg = RunConfig(thread_id="v5", context={"user": "a"})
    _linear().compile(checkpointer=saver).invoke({"x": 0}, cfg)
    stored = saver.get_tuple(cfg)
    check(stored is not None and stored.snapshot.config.context is None, "V5 snapshot.config.context is None")
    check(stored is not None and "context" not in stored.snapshot.metadata, "V5 metadata 不含 context")


def v6_compile_validation() -> None:
    for value in (None, True, False, MemorySaver()):
        try:
            _linear().compile(checkpointer=value)
        except Exception as exc:  # noqa: BLE001
            check(False, f"V6 合法 checkpointer 被拒：{value!r} / {exc}")
        else:
            check(True, f"V6 合法 checkpointer 被接受：{type(value).__name__}")
    for value in (object(), "saver", [], 0, 1, 0.0):
        try:
            _linear().compile(checkpointer=value)
        except TypeError:
            check(True, f"V6 非法 checkpointer 抛 TypeError：{value!r}")
        except Exception as exc:  # noqa: BLE001
            check(False, f"V6 非法 checkpointer 抛错类型不对：{type(exc).__name__}")
        else:
            check(False, f"V6 非法 checkpointer 未抛错：{value!r}")


def v7_span_checkpoint_id() -> None:
    def node(state: _State) -> _State:
        invoke_model(_Model(), "hello")
        return {"x": 1}

    builder = StateGraph(_State)
    builder.add_node("a", node)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    saver = MemorySaver()
    cfg = RunConfig(thread_id="v7")
    receiver = _Receiver()
    builder.compile(checkpointer=saver, tracer=receiver).invoke({"x": 0}, cfg)
    node_span = next(span for span in receiver.started if span.node == "a")
    model_span = next(span for span in receiver.started if span is not node_span)
    initial = list(saver.list(cfg))[-1].snapshot
    initial_id = initial.config.configurable["checkpoint_id"]
    check(node_span.checkpoint_id == initial_id, "V7 节点 span.checkpoint_id == 初始快照 id")
    check(model_span.checkpoint_id == initial_id, "V7 子 span 继承 checkpoint_id")
    check(model_span.parent == node_span.id, "V7 子 span parent == 节点 span id")


def v8_on_checkpoint_and_isolation() -> None:
    seen = []
    saver = MemorySaver(on_checkpoint=lambda snapshot: seen.append(snapshot.values))
    cfg1 = RunConfig(thread_id="v8-a")
    cfg2 = RunConfig(thread_id="v8-b")
    _linear().compile(checkpointer=saver).invoke({"x": 0}, cfg1)
    _linear().compile(checkpointer=saver).invoke({"x": 0}, cfg2)
    check(len(seen) == 6, "V8 on_checkpoint 每次成功 put 恰一次")
    check(list(saver.list(cfg1))[0].snapshot.values == {"x": 2}, "V8 thread-a 数据正确")
    saver.delete_thread("v8-a")
    check(list(saver.list(cfg1)) == [], "V8 delete_thread 清空目标线程")
    check(len(list(saver.list(cfg2))) == 3, "V8 delete_thread 不影响其它线程")


def main() -> int:
    print("══ B14F1 · Checkpointer + MemorySaver · 一键验收 ══")
    for case in (
        v1_protocol,
        v2_snapshots_and_writes,
        v3_dynamic_resume,
        v4_static_before,
        v5_context_not_persisted,
        v6_compile_validation,
        v7_span_checkpoint_id,
        v8_on_checkpoint_and_isolation,
    ):
        try:
            case()
        except Exception as exc:  # noqa: BLE001 - 单组失败不中断其余组
            check(False, f"{case.__name__} 未抛异常即完成：{type(exc).__name__}: {exc}")

    print(f"\n共 {_CHECKS} 条断言 · 失败 {len(_FAILURES)} 条")
    if _FAILURES:
        for label in _FAILURES:
            print(f"  - {label}")
        print("B14F1 acceptance: FAIL")
        return 1
    print("B14F1 acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
