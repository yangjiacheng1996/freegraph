#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · 一键验收脚本（``update_state`` + 时间旅行回放）。

一条命令跑完本 feature 的机械验收：

    .venv/bin/python harness/verification/B16F1/acceptance.py

覆盖：L1 签名 / 返回载体 / 无 saver 失败；L4 显式父链（双后端）；
``update_state`` C6 合并 / 父链 / 原历史不变；任意历史 checkpoint 重放；
正常终态 no-op；branch anchor；分叉不写额外 anchor；静态 / 动态中断组合；
``Command(resume)`` 最新快照；context 不持久化；能力边界；双后端一致性；
零 env / 零出站 / ARCH-1。

**只依赖标准库 + ``freegraph`` 本身**；退出码 ``0`` = PASS · ``1`` = FAIL ·
``2`` = 环境未就绪。
"""

from __future__ import annotations

import operator
import sqlite3
import sys
from pathlib import Path
from typing import Annotated, Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

try:
    from freegraph.contracts import Command, InvalidUpdateError, RunConfig
    from freegraph.graph import END, START, StateGraph, interrupt
    from freegraph.persistence import MemorySaver, SqliteSaver
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"[环境未就绪] 无法导入 freegraph：{exc}")
    raise SystemExit(2) from exc


class _State(TypedDict):
    x: int
    log: Annotated[list, operator.add]


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


def _a(state: dict) -> dict:
    return {"log": ["a"], "x": 1}


def _b(state: dict) -> dict:
    return {"log": ["b"]}


def _c(state: dict) -> dict:
    return {"log": ["c"]}


def _linear() -> StateGraph:
    graph = StateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("b", _b)
    graph.add_node("c", _c)
    graph.add_edge(START, "a")
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", END)
    return graph


def _ask(state: dict) -> dict:
    interrupt({"ask": "approve"})
    return {"log": ["answered"]}


def _interrupting() -> StateGraph:
    graph = StateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("ask", _ask)
    graph.add_edge(START, "a")
    graph.add_edge("a", "ask")
    graph.add_edge("ask", END)
    return graph


def _history(compiled, thread_id: str = "t") -> list:
    return list(compiled.get_state_history({"thread_id": thread_id}))


def _id(config: RunConfig) -> str:
    value = config.configurable["checkpoint_id"]
    assert isinstance(value, str)
    return value


def _run(graph: StateGraph, saver: Any, input: dict | None = None, thread_id: str = "t"):
    compiled = graph.compile(checkpointer=saver)
    compiled.invoke(input or {"log": []}, {"thread_id": thread_id})
    return compiled


def _projection(snapshot: Any) -> tuple[dict, tuple]:
    return dict(snapshot.values), tuple(snapshot.next)


def v1_l1_surface_and_failures() -> None:
    saver = MemorySaver()
    compiled = _run(_linear(), saver)
    fork = compiled.update_state({"thread_id": "t"}, {"x": 2}, as_node="a")
    check(isinstance(fork, RunConfig), "V1 update_state 返回 RunConfig")
    check(bool(fork.configurable["checkpoint_id"]), "V1 返回新 checkpoint_id")

    no_saver = _linear().compile()
    try:
        no_saver.update_state({"thread_id": "t"}, {"x": 1})
    except ValueError as exc:
        check("No checkpointer set" in str(exc), "V1 未挂 saver ⇒ ValueError")
    else:
        check(False, "V1 未挂 saver 未抛错")

    for call, exc_type, label in (
        (lambda: compiled.update_state({}, {"x": 1}), ValueError, "V1 缺 thread_id ⇒ ValueError"),
        (lambda: compiled.update_state("t", {"x": 1}), TypeError, "V1 裸 str config ⇒ TypeError"),
        (lambda: compiled.update_state({"thread_id": "t"}, None), TypeError, "V1 values=None ⇒ TypeError"),
        (
            lambda: compiled.update_state(
                {"thread_id": "t", "configurable": {"checkpoint_id": "9" * 32}},
                {"x": 1},
            ),
            ValueError,
            "V1 不存在 checkpoint_id ⇒ ValueError",
        ),
    ):
        try:
            call()
        except exc_type:
            check(True, label)
        except Exception as exc:  # noqa: BLE001
            check(False, f"{label}（实际 {type(exc).__name__}）")
        else:
            check(False, f"{label}（未抛错）")


def _saver_factories() -> list[tuple[str, Any]]:
    return [
        ("memory", lambda: MemorySaver()),
        (
            "sqlite",
            lambda: SqliteSaver(
                sqlite3.connect(":memory:", check_same_thread=False)
            ),
        ),
    ]


def v2_put_explicit_parent_dual_backend() -> None:
    for name, factory in _saver_factories():
        saver = factory()
        cfg = RunConfig(thread_id="p")
        first = saver.put(cfg, values={"n": 1}, metadata={"next": ()})
        second = saver.put(cfg, values={"n": 2}, metadata={"next": ()})
        branch = saver.put(
            RunConfig(
                thread_id="p",
                configurable={"checkpoint_id": _id(first)},
            ),
            values={"n": 3},
            metadata={"next": ()},
        )
        snapshot = saver.get_tuple(branch).snapshot
        check(snapshot.parent_config is not None and _id(snapshot.parent_config) == _id(first), f"V2 {name} 显式父链")
        check(_id(branch) > _id(second), f"V2 {name} 新 id = MAX+1")
        before = len(list(saver.list(cfg)))
        try:
            saver.put(
                RunConfig(
                    thread_id="p",
                    configurable={"checkpoint_id": "9" * 32},
                ),
                values={"n": 4},
                metadata={"next": ()},
            )
        except ValueError:
            check(len(list(saver.list(cfg))) == before, f"V2 {name} 不存在父 id ⇒ 原子失败")
        else:
            check(False, f"V2 {name} 不存在父 id 未抛错")


def v3_update_state_merge_and_history() -> None:
    saver = MemorySaver()
    compiled = _run(_linear(), saver)
    base = next(s for s in _history(compiled) if s.next == ("b",))
    before = _history(compiled)
    original = {_id(s.config): _projection(s) for s in before}

    fork = compiled.update_state(
        base.config, {"x": 99, "log": ["fork"]}, as_node="a"
    )
    branch = compiled.get_state(fork)
    check(branch is not None and branch.values["x"] == 99, "V3 覆盖型通道生效")
    check(branch is not None and branch.values["log"] == ["a", "fork"], "V3 归约型通道追加")
    check(branch is not None and _id(branch.parent_config) == _id(base.config), "V3 parent_config = 基准")
    check(_history(compiled)[1:] == before, "V3 原历史快照不变")
    check(
        all(
            _projection(compiled.get_state({"thread_id": "t", "configurable": {"checkpoint_id": key}}))
            == value
            for key, value in original.items()
        ),
        "V3 按 id 取回原快照逐项不变",
    )

    before_unknown = _history(compiled)
    try:
        compiled.update_state(base.config, {"nope": 1})
    except InvalidUpdateError:
        check(_history(compiled) == before_unknown, "V3 未知 key ⇒ InvalidUpdateError 且存储零变化")
    else:
        check(False, "V3 未知 key 未抛错")


def v4_replay_and_normal_terminal() -> None:
    compiled = _run(_linear(), MemorySaver())
    original = _history(compiled)
    originals = {_id(s.config): _projection(s) for s in original}

    for snapshot in original:
        if not snapshot.next:
            continue
        result = compiled.invoke(None, snapshot.config)
        check(result["log"] == ["a", "b", "c"], f"V4 从 {snapshot.next} 重放到一致终态")
    check(
        all(
            _projection(compiled.get_state({"thread_id": "t", "configurable": {"checkpoint_id": key}}))
            == value
            for key, value in originals.items()
        ),
        "V4 重放后原快照逐项不变",
    )

    final = _history(compiled)[0]
    before = len(_history(compiled))
    compiled.invoke(None, final.config)
    check(len(_history(compiled)) == before, "V4 正常终态重放 no-op（零新快照）")


def v5_anchor_and_fork_no_extra_anchor() -> None:
    compiled = _run(_linear(), MemorySaver())
    base = next(s for s in _history(compiled) if s.next == ("b",))
    before = _history(compiled)
    compiled.invoke(None, base.config)
    after = _history(compiled)
    check(len(after) - len(before) == 3, "V5 非 no-op replay = anchor + b + c")
    anchor = after[2]
    check(_id(anchor.parent_config) == _id(base.config), "V5 anchor parent = 基准")

    before_fork = _history(compiled)
    fork = compiled.update_state(base.config, {"x": 3}, as_node="a")
    compiled.invoke(None, fork)
    after_fork = _history(compiled)
    check(
        len(after_fork) - len(before_fork) == 3,
        "V5 update_state 分叉 + 执行 = 分支快照 + b + c（无额外 anchor）",
    )
    check(_id(after_fork[1].parent_config) == _id(fork), "V5 首条执行快照 parent = 分支快照")


def v6_static_and_dynamic_interrupts() -> None:
    saver = MemorySaver()
    static = _linear().compile(checkpointer=saver, interrupt_before=["b"])
    static.invoke({"log": []}, {"thread_id": "s"})
    paused = _history(static, "s")[0]
    check(paused.next == ("b",), "V6 静态挂起 next == ('b',)")
    check(saver.get_tuple(paused.config).scheduler["suspension_kind"] == "static_before", "V6 suspension_kind = static_before")
    result = static.invoke(None, paused.config)
    check(result["log"] == ["a", "b", "c"], "V6 静态快照 replay 保留 ack 并完成")

    static2 = _linear().compile(checkpointer=MemorySaver(), interrupt_before=["b"])
    static2.invoke({"log": []}, {"thread_id": "s2"})
    paused2 = _history(static2, "s2")[0]
    fork = static2.update_state(paused2.config, {"x": 9}, as_node="a")
    branch = static2.get_state(fork)
    check(
        branch is not None
        and branch.metadata["suspension_kind"] is None
        and branch.metadata["static_ack"] is None,
        "V6 update_state 新分支清空静态标记",
    )
    static2.invoke(None, fork)
    check(_history(static2, "s2")[0].next == ("b",), "V6 新分支后继再次命中静态断点")

    dsaver = MemorySaver()
    dynamic = _interrupting().compile(checkpointer=dsaver)
    dynamic.invoke({"log": []}, {"thread_id": "d"})
    pause = _history(dynamic, "d")[0]
    old_pending = dsaver.get_tuple(pause.config).pending_writes
    check(bool(old_pending), "V6 动态中断 pending 非空")
    replay = dynamic.invoke(None, pause.config)
    check("__interrupt__" in replay, "V6 动态中断 replay 再次暂停")
    check(dsaver.get_tuple(pause.config).pending_writes == old_pending, "V6 原 pending 零变化")
    resumed = dynamic.invoke(Command(resume="ok"), {"thread_id": "d"})
    check(resumed["log"] == ["a", "answered"], "V6 Command(resume) 恢复最新暂停点")
    check(dsaver.get_tuple(pause.config).pending_writes == old_pending, "V6 恢复后原 pending 仍不变")


def v7_context_and_capability_boundaries() -> None:
    saver = MemorySaver()
    compiled = _run(_linear(), saver)
    base = next(s for s in _history(compiled) if s.next == ("b",))
    fork = compiled.update_state(
        RunConfig(
            thread_id="t",
            context={"secret": 1},
            configurable={"checkpoint_id": _id(base.config)},
        ),
        {"x": 4},
    )
    snapshot = compiled.get_state(fork)
    check(snapshot is not None and snapshot.config.context is None, "V7 context 不进入新快照 config")
    check("secret" not in repr(snapshot.metadata), "V7 context 不进入 metadata")

    try:
        compiled.update_state({"thread_id": "t"}, {}, task_id="task")  # type: ignore[call-arg]
    except TypeError:
        check(True, "V7 task_id 不暴露（TypeError）")
    else:
        check(False, "V7 task_id 未拒绝")
    for name in ("get_state_tree", "get_branches", "aupdate_state"):
        check(not hasattr(compiled, name), f"V7 不提供 {name}")


def v8_dual_backend_consistency() -> None:
    def sequence(saver: Any) -> list[tuple]:
        graph = _linear()
        compiled = graph.compile(checkpointer=saver)
        compiled.invoke({"log": []}, {"thread_id": "d"})
        base = next(s for s in _history(compiled, "d") if s.next == ("b",))
        fork = compiled.update_state(base.config, {"log": ["fork"]}, as_node="a")
        compiled.invoke(None, fork)
        return [
            (
                _projection(snapshot),
                None
                if snapshot.parent_config is None
                else _id(snapshot.parent_config),
            )
            for snapshot in _history(compiled, "d")
        ]

    memory = sequence(MemorySaver())
    sqlite = sequence(
        SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))
    )
    check(memory == sqlite, "V8 MemorySaver ↔ SqliteSaver 8 字段 / 父链 / 历史顺序一致")


def v9_zero_env_egress_arch() -> None:
    runtime = REPO_ROOT / "src" / "freegraph" / "runtime"
    persistence = REPO_ROOT / "src" / "freegraph" / "persistence"
    for path in (
        runtime / "_time_travel.py",
        runtime / "superstep.py",
        runtime / "_stream_checkpoint.py",
        persistence / "memory.py",
        persistence / "sqlite.py",
    ):
        source = path.read_text(encoding="utf-8")
        for token in ("os.environ", "getenv", "urlopen", "requests", "socket"):
            check(token not in source, f"V9 {path.name} 不含 {token}")
    travel = (runtime / "_time_travel.py").read_text(encoding="utf-8")
    for token in ("freegraph.persistence", "freegraph.graph", "freegraph._stategraph", "langchain", "langgraph", "langsmith"):
        check(
            f"import {token}" not in travel and f"from {token}" not in travel,
            f"V9 _time_travel.py 不 import {token}",
        )
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    check("dependencies = []" in pyproject, "V9 dependencies 仍为空集")


def main() -> int:
    print("══ B16F1 · update_state + 时间旅行回放 · 一键验收 ══")
    for case in (
        v1_l1_surface_and_failures,
        v2_put_explicit_parent_dual_backend,
        v3_update_state_merge_and_history,
        v4_replay_and_normal_terminal,
        v5_anchor_and_fork_no_extra_anchor,
        v6_static_and_dynamic_interrupts,
        v7_context_and_capability_boundaries,
        v8_dual_backend_consistency,
        v9_zero_env_egress_arch,
    ):
        try:
            case()
        except Exception as exc:  # noqa: BLE001 - 单组失败不中断其余组
            check(False, f"{case.__name__} 未抛异常即完成：{type(exc).__name__}: {exc}")

    print(f"\n共 {_CHECKS} 条断言 · 失败 {len(_FAILURES)} 条")
    if _FAILURES:
        for label in _FAILURES:
            print(f"  - {label}")
        print("B16F1 acceptance: FAIL")
        return 1
    print("B16F1 acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
