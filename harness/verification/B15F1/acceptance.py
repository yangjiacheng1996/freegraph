#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · 一键验收脚本（``SqliteSaver`` + ``get_state`` / ``get_state_history``）。

一条命令跑完本 feature 的机械验收：

    .venv/bin/python harness/verification/B15F1/acceptance.py

覆盖：协议 / 导出面 / CRUD / 列表 / 删除 / 版本 / 生命周期 / 跨实例与跨进程持久化 /
``get_state`` 8 字段 / pending 合并口径 / next-tasks / 动态与静态挂起 / 历史倒序与
按 id 相等 / ``checkpoints`` 流式事件 / 并发 / 零 env 零出站。

**只依赖标准库 + ``freegraph`` 本身**；退出码 ``0`` = PASS · ``1`` = FAIL ·
``2`` = 环境未就绪。
"""

from __future__ import annotations

import operator
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Annotated, Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

try:
    from freegraph.contracts import Checkpointer, RunConfig, StateSnapshot
    from freegraph.graph import END, START, StateGraph, interrupt
    from freegraph.persistence import SqliteSaver
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"[环境未就绪] 无法导入 freegraph：{exc}")
    raise SystemExit(2) from exc


class _State(TypedDict):
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


def _linear() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"log": ["a"]})
    builder.add_node("b", lambda state: {"log": ["b"]})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def _interrupting() -> StateGraph:
    def ask(state: dict) -> dict:
        interrupt({"ask": "approve"})
        return {"log": ["asked"]}

    builder = StateGraph(_State)
    builder.add_node("ask", ask)
    builder.add_edge(START, "ask")
    builder.add_edge("ask", END)
    return builder


def _meta(next_nodes: tuple[str, ...] = ()) -> dict[str, Any]:
    return {"next": next_nodes, "interrupts": (), "tasks": (), "scheduler": {"fanout": {}}}


def v1_protocol_and_exports() -> None:
    import freegraph.graph as facade
    import freegraph.persistence as persistence

    saver = SqliteSaver(__import__("sqlite3").connect(":memory:", check_same_thread=False))
    check(isinstance(saver, Checkpointer), "V1 SqliteSaver 满足 Checkpointer 协议")
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
    check("SqliteSaver" in persistence.__all__, "V1 persistence.__all__ 含 SqliteSaver")
    check(not hasattr(facade, "SqliteSaver"), "V1 门面不转出 SqliteSaver（G18）")


def v2_crud_list_delete_version() -> None:
    saver = SqliteSaver(__import__("sqlite3").connect(":memory:", check_same_thread=False))
    cfg = RunConfig(thread_id="v2")
    c1 = saver.put(cfg, values={"n": 1}, metadata=_meta(("a",)))
    c2 = saver.put(cfg, values={"n": 2}, metadata=_meta())
    check(c1.configurable["checkpoint_id"] == f"{1:032d}", "V2 首个 id == 1")
    check(c2.configurable["checkpoint_id"] == f"{2:032d}", "V2 第二个 id == 2")
    latest = saver.get_tuple(cfg)
    check(latest is not None and latest.snapshot.values == {"n": 2}, "V2 get_tuple 取最新")
    check(
        latest is not None
        and latest.snapshot.parent_config is not None
        and latest.snapshot.parent_config.configurable["checkpoint_id"] == f"{1:032d}",
        "V2 parent_config 指向上一快照",
    )
    ids = [item.snapshot.config.configurable["checkpoint_id"] for item in saver.list(cfg)]
    check(ids == sorted(ids, reverse=True), "V2 list 按 checkpoint_id 倒序")
    check(len(list(saver.list(cfg, limit=1))) == 1, "V2 limit 生效")
    check(list(saver.list(cfg, limit=0)) == [], "V2 limit<=0 ⇒ 空")
    check(saver.get_next_version(4) == 5, "V2 get_next_version int+1")
    saver.delete_thread("v2")
    saver.delete_thread("v2")
    check(saver.get_tuple(cfg) is None, "V2 delete_thread 幂等且清空")


def v3_persistence_across_instances(tmpdir: str) -> None:
    path = str(Path(tmpdir) / "accept.db")
    with SqliteSaver.from_conn_string(path) as saver:
        saver.put(RunConfig(thread_id="v3"), values={"n": 7}, metadata=_meta())
    with SqliteSaver.from_conn_string(path) as saver:
        stored = saver.get_tuple(RunConfig(thread_id="v3"))
        check(stored is not None and stored.snapshot.values == {"n": 7}, "V3 跨实例取回旧快照")


def v4_cross_process(tmpdir: str) -> None:
    path = str(Path(tmpdir) / "cross.db")
    with SqliteSaver.from_conn_string(path) as saver:
        saver.put(RunConfig(thread_id="v4"), values={"n": 9}, metadata=_meta())
    script = (
        "from freegraph.contracts import RunConfig\n"
        "from freegraph.persistence import SqliteSaver\n"
        f"with SqliteSaver.from_conn_string({path!r}) as s:\n"
        "    t = s.get_tuple(RunConfig(thread_id='v4'))\n"
        "    print(t.snapshot.values['n'])\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    check(
        completed.returncode == 0 and completed.stdout.strip().endswith("9"),
        "V4 新 Python 子进程取回旧快照（退出码 0）",
    )


def v5_get_state_fields_and_next_tasks() -> None:
    saver = SqliteSaver(__import__("sqlite3").connect(":memory:", check_same_thread=False))
    compiled = _linear().compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "v5"})
    snapshot = compiled.get_state({"thread_id": "v5"})
    check(isinstance(snapshot, StateSnapshot), "V5 get_state 返回 StateSnapshot")
    check(snapshot is not None and snapshot.values == {"log": ["a", "b"]}, "V5 values 正确")
    check(snapshot is not None and snapshot.next == (), "V5 收敛 next == ()")
    check(snapshot is not None and snapshot.tasks == (), "V5 收敛 tasks == ()（next-tasks）")
    check(snapshot is not None and snapshot.config.context is None, "V5 config.context is None")
    check(snapshot is not None and bool(snapshot.config.configurable["checkpoint_id"]), "V5 checkpoint_id 非空")


def v6_config_failures() -> None:
    saver = SqliteSaver(__import__("sqlite3").connect(":memory:", check_same_thread=False))
    compiled = _linear().compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "v6"})
    for call, exc_type, label in (
        (lambda: compiled.get_state(None), ValueError, "V6 None ⇒ ValueError（缺 thread_id）"),
        (lambda: compiled.get_state({}), ValueError, "V6 缺 thread_id ⇒ ValueError"),
        (lambda: compiled.get_state("t"), TypeError, "V6 裸 str ⇒ TypeError"),
        (
            lambda: compiled.get_state({"thread_id": "v6", "configurable": {"checkpoint_ns": "sub"}}),
            ValueError,
            "V6 非空 checkpoint_ns ⇒ ValueError",
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
    no_saver = _linear().compile()
    try:
        no_saver.get_state({"thread_id": "v6"})
    except ValueError as exc:
        check("No checkpointer set" in str(exc), "V6 未挂 saver ⇒ ValueError（No checkpointer set）")
    except Exception as exc:  # noqa: BLE001
        check(False, f"V6 未挂 saver 抛错类型不对：{type(exc).__name__}")
    else:
        check(False, "V6 未挂 saver 未抛错")


def v7_pending_merge() -> None:
    saver = SqliteSaver(__import__("sqlite3").connect(":memory:", check_same_thread=False))
    compiled = _linear().compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "v7"})
    latest = saver.get_tuple(RunConfig(thread_id="v7"))
    assert latest is not None
    latest_id = latest.snapshot.config.configurable["checkpoint_id"]
    saver.put_writes(
        RunConfig(thread_id="v7", configurable={"checkpoint_id": latest_id}),
        writes=[("log", ["pending"]), ("__error__", "ignored")],
        task_id="a",
    )
    merged = compiled.get_state({"thread_id": "v7"})
    check(merged is not None and merged.values["log"] == ["a", "b", "pending"], "V7 无 id ⇒ 合并 pending")
    by_id = compiled.get_state(
        {"thread_id": "v7", "configurable": {"checkpoint_id": latest_id}}
    )
    check(by_id is not None and by_id.values["log"] == ["a", "b"], "V7 有 id ⇒ 不合并")
    history_first = list(compiled.get_state_history({"thread_id": "v7"}))[0]
    check(history_first.values["log"] == ["a", "b"], "V7 历史 ⇒ 不合并")


def v8_dynamic_and_static_interrupts() -> None:
    saver = SqliteSaver(__import__("sqlite3").connect(":memory:", check_same_thread=False))
    compiled = _interrupting().compile(checkpointer=saver)
    result = compiled.invoke({"log": []}, {"thread_id": "v8d"})
    expected = tuple(result["__interrupt__"])
    snapshot = compiled.get_state({"thread_id": "v8d"})
    check(snapshot is not None and snapshot.interrupts == expected, "V8 动态中断：interrupts 与 __interrupt__ 一致")
    check(
        snapshot is not None
        and len(snapshot.tasks) == 1
        and snapshot.tasks[0].name == "ask"
        and snapshot.tasks[0].interrupts == expected,
        "V8 动态中断：tasks 为 next-tasks 且带 interrupts",
    )

    saver2 = SqliteSaver(__import__("sqlite3").connect(":memory:", check_same_thread=False))
    static = _linear().compile(checkpointer=saver2, interrupt_before=["b"])
    static.invoke({"log": []}, {"thread_id": "v8s"})
    st = static.get_state({"thread_id": "v8s"})
    check(st is not None and st.next == ("b",), "V8 静态挂起：next 指向待执行节点")
    check(st is not None and st.interrupts == (), "V8 静态挂起：interrupts == ()")
    check(
        st is not None and len(st.tasks) == 1 and st.tasks[0].id == "b" and st.tasks[0].interrupts == (),
        "V8 静态挂起：tasks 为 next-tasks 且 interrupts == ()",
    )


def v9_history() -> None:
    saver = SqliteSaver(__import__("sqlite3").connect(":memory:", check_same_thread=False))
    compiled = _linear().compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "v9"})
    history = list(compiled.get_state_history({"thread_id": "v9"}))
    check(len(history) == len(list(saver.list(RunConfig(thread_id="v9")))), "V9 历史数量 == saver.list")
    ids = [item.config.configurable["checkpoint_id"] for item in history]
    check(ids == sorted(ids, reverse=True), "V9 历史 checkpoint_id 严格递减")
    first = history[0]
    by_id = compiled.get_state(
        {"thread_id": "v9", "configurable": {"checkpoint_id": first.config.configurable["checkpoint_id"]}}
    )
    check(by_id is not None and by_id.values == first.values and by_id.tasks == first.tasks, "V9 get_state(id) 与历史同 id 逐字段相等")


def v10_stream_checkpoints() -> None:
    saver = SqliteSaver(__import__("sqlite3").connect(":memory:", check_same_thread=False))
    compiled = _linear().compile(checkpointer=saver)
    events = list(compiled.stream({"log": []}, {"thread_id": "v10"}, stream_mode="checkpoints"))
    check(events != [], "V10 checkpoints 事件非空")
    check(
        all(set(event) == {"stream_mode", "payload", "run_id", "thread_id"} for event in events),
        "V10 事件四键齐全",
    )
    check(all(isinstance(event["payload"], StateSnapshot) for event in events), "V10 payload 是 StateSnapshot")
    check(len(events) == len(list(saver.list(RunConfig(thread_id="v10")))), "V10 事件数 == 成功 put 次数")
    no_saver = _linear().compile()
    check(list(no_saver.stream({"log": []}, {"thread_id": "v10"}, stream_mode="checkpoints")) == [], "V10 无 saver ⇒ 0 条")


def v11_concurrency() -> None:
    saver = SqliteSaver(__import__("sqlite3").connect(":memory:", check_same_thread=False))
    errors: list[BaseException] = []

    def worker(worker_id: int) -> None:
        try:
            for index in range(4):
                saver.put(
                    RunConfig(thread_id="v11"),
                    values={"w": worker_id, "i": index},
                    metadata=_meta(),
                )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(worker_id,)) for worker_id in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    ids = [
        item.snapshot.config.configurable["checkpoint_id"]
        for item in saver.list(RunConfig(thread_id="v11"))
    ]
    check(not errors, "V11 并发无异常")
    check(len(ids) == 32 and len(set(ids)) == 32, "V11 并发 checkpoint id 唯一")
    check(not any("database is locked" in str(exc) for exc in errors), "V11 无 database is locked 泄漏")


def v12_zero_env_zero_egress() -> None:
    persistence = REPO_ROOT / "src" / "freegraph" / "persistence"
    for name in ("sqlite.py", "_json.py"):
        source = (persistence / name).read_text(encoding="utf-8")
        for token in ("os.environ", "getenv", "urlopen", "requests", "socket"):
            check(token not in source, f"V12 {name} 不含 {token}")


def main() -> int:
    print("══ B15F1 · SqliteSaver + get_state / get_state_history · 一键验收 ══")
    with tempfile.TemporaryDirectory() as tmpdir:
        for case in (
            v1_protocol_and_exports,
            v2_crud_list_delete_version,
            v5_get_state_fields_and_next_tasks,
            v6_config_failures,
            v7_pending_merge,
            v8_dynamic_and_static_interrupts,
            v9_history,
            v10_stream_checkpoints,
            v11_concurrency,
            v12_zero_env_zero_egress,
        ):
            try:
                case()
            except Exception as exc:  # noqa: BLE001 - 单组失败不中断其余组
                check(False, f"{case.__name__} 未抛异常即完成：{type(exc).__name__}: {exc}")
        for case_with_tmp in (v3_persistence_across_instances, v4_cross_process):
            try:
                case_with_tmp(tmpdir)
            except Exception as exc:  # noqa: BLE001
                check(False, f"{case_with_tmp.__name__} 未抛异常即完成：{type(exc).__name__}: {exc}")

    print(f"\n共 {_CHECKS} 条断言 · 失败 {len(_FAILURES)} 条")
    if _FAILURES:
        for label in _FAILURES:
            print(f"  - {label}")
        print("B15F1 acceptance: FAIL")
        return 1
    print("B15F1 acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
