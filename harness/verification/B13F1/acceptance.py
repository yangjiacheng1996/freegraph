#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B13F1 · 一键验收脚本（静态中断点 + ``recursion_limit``）。

**一条命令**跑完本 feature 的机械验收：

    .venv/bin/python harness/verification/B13F1/acceptance.py

覆盖：
- V1  ``interrupt_before``：目标 0 次、空载荷、状态只含前序写入；
- V2  before 恢复：``input=None`` ⇒ 目标恰好 1 次；
- V3  ``interrupt_after``：目标 1 次、写入已合并、恢复不重跑；
- V4  最后节点 after：``next`` 为空仍可恢复；
- V5  ``recursion_limit`` dict 载体 ⇒ ``GraphRecursionError``；
- V6  ``RunConfig`` 载体 + 优先于 ``max_steps``；
- V7  ``GraphSpec`` 静态字段校验（裸非 ``"*"`` / ``["*"]`` / 未知节点 / 裸 ``"*"``）；
- V8  低层入口 V-26 显式拒绝；
- V9  fan-out N=2 × before / after + 账本恢复；
- V10 ``recursion_limit=None`` 落回 ``max_steps``。

**只依赖标准库 + ``freegraph`` 本身**；退出码 ``0`` = PASS · ``1`` = FAIL · ``2`` = 环境未就绪。
"""

from __future__ import annotations

import operator
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

try:
    from freegraph.contracts import GraphRecursionError, RunConfig, Send
    from freegraph.runtime import (
        GraphSpec,
        InterruptResult,
        NodeSpec,
        SchedulerState,
        run_graph,
        run_super_step,
    )
    from freegraph.runtime.channel import BinaryOperatorAggregate, LastValue
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"[环境未就绪] 无法导入 freegraph：{exc}")
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


class _CheckpointTuple:
    def __init__(self, values, next_nodes, metadata) -> None:
        self.snapshot = SimpleNamespace(values=values, next=next_nodes)
        self.pending_writes = tuple(metadata.get("pending_writes", ()))
        self.scheduler = dict(metadata.get("scheduler", {}))


class _Checkpointer:
    """最小测试桩（**不是** saver 实现；只满足本脚本恢复路径）。"""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _thread(config: RunConfig) -> str:
        resolved = getattr(config, "resolved_thread_id", None)
        if callable(resolved):
            value = resolved()
            if value is not None:
                return str(value)
        return str(getattr(config, "thread_id", ""))

    def get_tuple(self, config: RunConfig):
        stored = self._store.get(self._thread(config))
        if stored is None:
            return None
        return _CheckpointTuple(
            stored["values"], stored["next"], stored["metadata"]
        )

    def put(self, config, values=None, metadata=None, **kwargs) -> None:
        self._store[self._thread(config)] = {
            "values": dict(values or {}),
            "next": tuple((metadata or {}).get("next", ())),
            "metadata": dict(metadata or {}),
        }

    def put_writes(self, config, writes=None, task_id=None, task_path=None, **kwargs) -> None:
        # 静态挂起不写 __interrupt__；本桩只为兼容既有恢复接口。
        stored = self._store.setdefault(
            self._thread(config),
            {"values": {}, "next": (), "metadata": {}},
        )
        pending = list(stored["metadata"].get("pending_writes", ()))
        for channel, value in writes or ():
            pending.append((task_id, channel, value))
        stored["metadata"]["pending_writes"] = tuple(pending)


def _chain_spec(*, before=(), after=(), final: bool = False):
    calls = {"prepare": 0, "review": 0, "final": 0}

    def prepare(state):
        calls["prepare"] += 1
        return {"count": 1}

    def review(state):
        calls["review"] += 1
        return {"count": state.get("count", 0) + 1}

    def final_node(state):
        calls["final"] += 1
        return {"count": state.get("count", 0) + 1}

    nodes = {
        "prepare": NodeSpec((), prepare),
        "review": NodeSpec(("count",), review),
    }
    edges = {"__start__": ("prepare",), "prepare": ("review",)}
    if final:
        nodes["final"] = NodeSpec(("count",), final_node)
        edges["review"] = ("final",)
    spec = GraphSpec(
        channels={"count": LastValue("count", int)},
        nodes=nodes,
        edges=edges,
        interrupt_before=before,
        interrupt_after=after,
    )
    return spec, calls


def _loop_spec():
    def loop(state):
        return {"count": state.get("count", 0) + 1}

    return GraphSpec(
        channels={"count": LastValue("count", int)},
        nodes={"loop": NodeSpec(("count",), loop)},
        edges={"__start__": ("loop",), "loop": ("loop",)},
    )


def _fanout_spec(*, before=(), after=()):
    calls = {"fan": 0, "worker": 0}

    def fan(state):
        calls["fan"] += 1
        return [Send("worker", {"n": 1}), Send("worker", {"n": 2})]

    def worker(state):
        calls["worker"] += 1
        return {"out": [state["n"]]}

    return (
        GraphSpec(
            channels={
                "out": BinaryOperatorAggregate("out", list, operator.add),
            },
            nodes={"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)},
            edges={"__start__": ("fan",)},
            interrupt_before=before,
            interrupt_after=after,
        ),
        calls,
    )


def v1_before() -> None:
    spec, calls = _chain_spec(before=("review",))
    saver = _Checkpointer()
    config = RunConfig(thread_id="v1")
    paused = run_graph(spec, {}, checkpointer=saver, config=config)
    check(isinstance(paused, InterruptResult), "V1 before 返回 InterruptResult")
    check(paused.interrupts == (), "V1 静态挂起载荷为空元组")
    check(paused.state == {"count": 1}, "V1 状态只含前序写入")
    check(paused.executed == ("prepare",), "V1 目标未执行")
    check(calls["review"] == 0, "V1 review 执行 0 次")


def v2_before_resume() -> None:
    spec, calls = _chain_spec(before=("review",))
    saver = _Checkpointer()
    config = RunConfig(thread_id="v2")
    assert isinstance(run_graph(spec, {}, checkpointer=saver, config=config), InterruptResult)
    resumed = run_graph(spec, None, checkpointer=saver, config=config)
    check(not isinstance(resumed, InterruptResult), "V2 before 恢复后完成")
    check(calls["review"] == 1, "V2 before 恢复后目标恰好执行 1 次")
    check(resumed.state == {"count": 2}, "V2 恢复后写入正确")


def v3_after() -> None:
    spec, calls = _chain_spec(after=("review",))
    saver = _Checkpointer()
    config = RunConfig(thread_id="v3")
    paused = run_graph(spec, {}, checkpointer=saver, config=config)
    check(isinstance(paused, InterruptResult), "V3 after 返回 InterruptResult")
    check(calls["review"] == 1, "V3 after 目标执行 1 次")
    check(paused.state == {"count": 2}, "V3 挂起态含本轮写入")
    resumed = run_graph(spec, None, checkpointer=saver, config=config)
    check(not isinstance(resumed, InterruptResult), "V3 after 恢复后完成")
    check(calls["review"] == 1, "V3 恢复不重跑目标")


def v4_after_last_node() -> None:
    spec, calls = _chain_spec(after=("review",), final=False)
    saver = _Checkpointer()
    config = RunConfig(thread_id="v4")
    paused = run_graph(spec, {}, checkpointer=saver, config=config)
    check(isinstance(paused, InterruptResult), "V4 最后节点 after 仍挂起")
    metadata = saver.get_tuple(config)
    assert metadata is not None
    check(metadata.snapshot.next == (), "V4 最后节点 after 的 next 为空")
    resumed = run_graph(spec, None, checkpointer=saver, config=config)
    check(not isinstance(resumed, InterruptResult), "V4 next 为空仍可恢复")
    check(calls["review"] == 1, "V4 恢复不重跑最后节点")


def v5_recursion_dict() -> None:
    try:
        run_graph(_loop_spec(), {"count": 0}, config={"recursion_limit": 3})
    except GraphRecursionError as exc:
        check(exc.recursion_limit == 3, "V5 dict 载体的 recursion_limit == 3")
        check(exc.current_step == 3, "V5 current_step 如实")
        check("recursion" in str(exc).lower(), "V5 消息含递归超限语义")
    else:  # pragma: no cover - 防御
        check(False, "V5 未抛 GraphRecursionError")


def v6_runconfig_priority() -> None:
    try:
        run_graph(
            _loop_spec(),
            {"count": 0},
            config=RunConfig(recursion_limit=3),
            max_steps=100,
        )
    except GraphRecursionError as exc:
        check(exc.recursion_limit == 3, "V6 RunConfig 载体生效")
        check(exc.recursion_limit != 100, "V6 RunConfig 优先于 max_steps")
    else:  # pragma: no cover - 防御
        check(False, "V6 未抛 GraphRecursionError")


def v7_graphspec_validation() -> None:
    channels = {"count": LastValue("count", int)}
    nodes = {"a": NodeSpec((), lambda s: {}), "b": NodeSpec((), lambda s: {})}
    edges = {"__start__": ("a",)}
    try:
        GraphSpec(channels=channels, nodes=nodes, edges=edges, interrupt_before="a")
    except TypeError:
        check(True, "V7 裸非 '*' 字符串 ⇒ TypeError")
    else:  # pragma: no cover - 防御
        check(False, "V7 裸非 '*' 字符串未失败")
    try:
        GraphSpec(channels=channels, nodes=nodes, edges=edges, interrupt_before=["*"])
    except ValueError:
        check(True, "V7 ['*'] ⇒ ValueError")
    else:  # pragma: no cover - 防御
        check(False, "V7 ['*'] 未失败")
    try:
        GraphSpec(channels=channels, nodes=nodes, edges=edges, interrupt_before=["nope"])
    except ValueError as exc:
        check("nope" in str(exc), "V7 未知节点 ⇒ ValueError 且点名")
    else:  # pragma: no cover - 防御
        check(False, "V7 未知节点未失败")
    spec = GraphSpec(
        channels=channels, nodes=nodes, edges=edges, interrupt_before="*"
    )
    check(spec.interrupt_before == ("a", "b"), "V7 裸 '*' 展开为全部可执行节点")


def v8_low_level_reject() -> None:
    spec, _ = _chain_spec(before=("review",))
    try:
        run_super_step(spec, SchedulerState())
    except ValueError as exc:
        check("run_graph" in str(exc), "V8 低层入口 V-26 显式拒绝")
    else:  # pragma: no cover - 防御
        check(False, "V8 低层入口未拒绝静态字段")


def v9_fanout() -> None:
    spec, calls = _fanout_spec(before=("worker",))
    saver = _Checkpointer()
    config = RunConfig(thread_id="v9-before")
    paused = run_graph(spec, checkpointer=saver, config=config)
    check(isinstance(paused, InterruptResult), "V9 fan-out before 返回 InterruptResult")
    check(calls["worker"] == 0, "V9 fan-out before 的 N 个任务一个都不执行")
    stored = saver.get_tuple(config)
    assert stored is not None
    tasks = next(iter(stored.scheduler["fanout"].values()))["tasks"]
    check(len(tasks) == 2, "V9 fan-out 账本保留 2 个独立任务")
    resumed = run_graph(spec, None, checkpointer=saver, config=config)
    check(not isinstance(resumed, InterruptResult), "V9 fan-out before 恢复后完成")
    check(calls["worker"] == 2, "V9 恢复后恰好重试 2 个任务")
    check(resumed.state["out"] == [1, 2], "V9 入参 / 归约结果逐项正确")

    spec2, calls2 = _fanout_spec(after=("worker",))
    saver2 = _Checkpointer()
    config2 = RunConfig(thread_id="v9-after")
    paused2 = run_graph(spec2, checkpointer=saver2, config=config2)
    check(isinstance(paused2, InterruptResult), "V9 fan-out after 返回 InterruptResult")
    check(calls2["worker"] == 2, "V9 fan-out after 的 N 个任务各执行一次")
    check(paused2.state["out"] == [1, 2], "V9 after 挂起态含两次写入")


def v10_none_fallback() -> None:
    try:
        run_graph(
            _loop_spec(),
            {"count": 0},
            config={"recursion_limit": None},
            max_steps=2,
        )
    except GraphRecursionError as exc:
        check(exc.recursion_limit == 2, "V10 None 视为未提供并落回 max_steps")
    else:  # pragma: no cover - 防御
        check(False, "V10 None 未落回 max_steps")


def main() -> int:
    print("══ B13F1 · 静态中断点 + recursion_limit · 一键验收 ══")
    for case in (
        v1_before,
        v2_before_resume,
        v3_after,
        v4_after_last_node,
        v5_recursion_dict,
        v6_runconfig_priority,
        v7_graphspec_validation,
        v8_low_level_reject,
        v9_fanout,
        v10_none_fallback,
    ):
        try:
            case()
        except Exception as exc:  # noqa: BLE001 - 单组失败不中断其余组
            check(False, f"{case.__name__} 未抛异常即完成：{type(exc).__name__}: {exc}")

    print(f"\n共 {_CHECKS} 条断言 · 失败 {len(_FAILURES)} 条")
    if _FAILURES:
        for label in _FAILURES:
            print(f"  - {label}")
        print("B13F1 acceptance: FAIL")
        return 1
    print("B13F1 acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
