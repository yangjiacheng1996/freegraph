#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 可诊断性验收（diagnostics · 四组验收脚本的第四组）。

覆盖：

* **trace**：`FileTraceStore` / `SqliteTraceStore` + `query()` 的四类过滤
  （`run_id` / `thread_id` / `node` / 时间窗）、组合过滤、空过滤器；
* **checkpoint**：`MemorySaver` / `SqliteSaver` + `get_tuple` / `get_state` /
  `get_state_history`（倒序）/ `stream(checkpoints)`；
* **time_travel**：历史点重放、`update_state` 覆盖 / 归约、分叉后原历史不变、
  中断组合（动态中断 + `Command(resume=...)`）。

**只 import `freegraph` + Python 标准库**；退出码 0 = PASS · 1 = FAIL ·
2 = 环境未就绪。最后一行 MUST 打印 ``diagnostics: PASS|FAIL``。
"""

from __future__ import annotations

import json
import operator
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from freegraph.contracts import RunConfig, Span, StateSnapshot, TraceQuery
    from freegraph.graph import END, START, Command, StateGraph, interrupt
    from freegraph.observability import FileTraceStore, SqliteTraceStore, TraceRecord
    from freegraph.persistence import MemorySaver, SqliteSaver
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"[环境未就绪] 无法导入 freegraph：{exc}")
    print("diagnostics: FAIL")
    raise SystemExit(2) from exc

FAILURES: list[str] = []
CHECKS = 0


def section(title: str) -> None:
    print(f"\n[{title}]")


def check(condition: Any, label: str, detail: str = "") -> bool:
    global CHECKS
    CHECKS += 1
    ok = bool(condition)
    print(f"  {'✔' if ok else '✘'} {label}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        FAILURES.append(f"{label}" + (f" — {detail}" if detail else ""))
    return ok


class _State(TypedDict, total=False):
    x: int
    log: Annotated[list[str], operator.add]


def _a(state: dict) -> dict:
    return {"log": ["a"], "x": 1}


def _b(state: dict) -> dict:
    return {"log": ["b"]}


def _c(state: dict) -> dict:
    return {"log": ["c"]}


def _linear() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", _a)
    builder.add_node("b", _b)
    builder.add_node("c", _c)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", "c")
    builder.add_edge("c", END)
    return builder


def _ask(state: dict) -> dict:
    interrupt({"ask": "approve"})
    return {"log": ["answered"]}


def _interrupting() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", _a)
    builder.add_node("ask", _ask)
    builder.add_edge(START, "a")
    builder.add_edge("a", "ask")
    builder.add_edge("ask", END)
    return builder


def _seed_trace(store: Any, *, thread_id: str, run_id: str) -> None:
    span_a = Span(
        id="span-a",
        name="a",
        start_time="2026-11-25T00:00:00.000000000+00:00",
        end_time="2026-11-25T00:00:01.000000000+00:00",
        thread_id=thread_id,
        run_id=run_id,
        node="a",
    )
    span_b = Span(
        id="span-b",
        name="b",
        start_time="2026-11-25T00:00:01.000000000+00:00",
        end_time="2026-11-25T00:00:02.000000000+00:00",
        thread_id=thread_id,
        run_id=run_id,
        node="b",
    )
    for span in (span_a, span_b):
        store.on_trace_record(
            TraceRecord(
                span_id=span.id,
                task_id=span.node,
                run_id=run_id,
                thread_id=thread_id,
                checkpoint_id=None,
                node=span.node,
                superstep=0,
                triggers=(),
                concurrency_group=(),
                barrier_groups=(),
                input_state={},
                output_state={},
                error=None,
            )
        )
    for span in (span_a, span_b):
        store.on_span_end(span)


def trace_group() -> None:
    section("trace")
    import tempfile as _tempfile

    with _tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        # ① 真跑一次：FileTraceStore
        file_store = FileTraceStore(root / "file")
        _linear().compile(tracer=file_store).invoke({"log": []}, RunConfig(thread_id="trace-live"))
        rows = file_store.query()
        check(bool(rows), "FileTraceStore 产出可查询行")
        check(all("run_id" in row and "thread_id" in row for row in rows), "C23 关联键存在")
        check(json.dumps(rows) is not None, "FileTraceStore query 结果可 json.dumps")

        # ② 真跑一次：SqliteTraceStore
        sqlite_store = SqliteTraceStore(root / "traces.sqlite3")
        _linear().compile(tracer=sqlite_store).invoke({"log": []}, RunConfig(thread_id="trace-live"))
        sqlite_rows = sqlite_store.query()
        check(bool(sqlite_rows), "SqliteTraceStore 产出可查询行")

    # ③ 同一份种子数据 ⇒ 两后端逐条等价 + 四类过滤 / 组合 / 空
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        file_store = FileTraceStore(root / "file")
        sqlite_store = SqliteTraceStore(root / "traces.sqlite3")
        for store in (file_store, sqlite_store):
            _seed_trace(store, thread_id="seed", run_id="run-seed")

        def _spans(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return [row for row in rows if row.get("kind") == "span"]

        by_run = _spans(file_store.query(TraceQuery(run_id="run-seed")))
        by_thread = _spans(file_store.query(TraceQuery(thread_id="seed")))
        by_node = _spans(file_store.query(TraceQuery(node="a")))
        by_time = _spans(
            file_store.query(
                TraceQuery(
                    start_time="2026-11-25T00:00:00.000000000+00:00",
                    end_time="2026-11-25T00:00:01.500000000+00:00",
                )
            )
        )
        combo = _spans(file_store.query(TraceQuery(thread_id="seed", node="b")))
        empty = file_store.query(TraceQuery())
        check(len(by_run) == 2, "按 run_id 过滤", f"实际 {len(by_run)}")
        check(len(by_thread) == 2, "按 thread_id 过滤", f"实际 {len(by_thread)}")
        check(len(by_node) == 1, "按 node 过滤", f"实际 {len(by_node)}")
        check(len(by_time) == 2, "按时间窗过滤", f"实际 {len(by_time)}")
        check(len(combo) == 1, "组合过滤（thread_id + node）", f"实际 {len(combo)}")
        check(len(empty) == 4, "空过滤器返回全部", f"实际 {len(empty)}")
        check(json.dumps(by_run) is not None, "query 结果可 json.dumps")

        file_view = sorted(
            file_store.query(TraceQuery(thread_id="seed")), key=lambda row: row.get("span_id", "")
        )
        sqlite_view = sorted(
            sqlite_store.query(TraceQuery(thread_id="seed")), key=lambda row: row.get("span_id", "")
        )
        check(file_view == sqlite_view, "FileTraceStore ↔ SqliteTraceStore 逐条等价")


def checkpoint_group() -> None:
    section("checkpoint")
    memory = MemorySaver()
    memory_graph = _linear().compile(checkpointer=memory)
    memory_graph.invoke({"log": []}, RunConfig(thread_id="cp-memory"))
    state = memory_graph.get_state(RunConfig(thread_id="cp-memory"))
    check(state is not None and state.values["log"] == ["a", "b", "c"], "MemorySaver get_state")
    check(len(list(memory_graph.get_state_history(RunConfig(thread_id="cp-memory")))) >= 1, "MemorySaver get_state_history")
    check(memory.get_tuple(RunConfig(thread_id="cp-memory")) is not None, "MemorySaver get_tuple")

    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "checkpoints.sqlite3"
        with SqliteSaver.from_conn_string(str(path)) as saver:
            graph = _linear().compile(checkpointer=saver)
            graph.invoke({"log": []}, RunConfig(thread_id="cp-sqlite"))
            snapshot = graph.get_state(RunConfig(thread_id="cp-sqlite"))
            check(snapshot is not None and snapshot.values["log"] == ["a", "b", "c"], "SqliteSaver get_state")
            history = list(graph.get_state_history(RunConfig(thread_id="cp-sqlite")))
            ids = [item.config.configurable["checkpoint_id"] for item in history]
            check(len(history) >= 1, "SqliteSaver get_state_history 非空")
            check(ids == sorted(ids, reverse=True), "历史 checkpoint_id 倒序")
            events = list(
                graph.stream(
                    {"log": []},
                    RunConfig(thread_id="cp-stream"),
                    stream_mode="checkpoints",
                )
            )
            check(bool(events), "stream(checkpoints) 非空")
            check(
                all(set(event) == {"stream_mode", "payload", "run_id", "thread_id"} for event in events),
                "stream(checkpoints) 四键信封",
            )
            check(
                all(isinstance(event["payload"], StateSnapshot) for event in events),
                "stream(checkpoints) payload 是 StateSnapshot",
            )
            check(
                len(events) == len(list(saver.list(RunConfig(thread_id="cp-stream")))),
                "stream(checkpoints) 事件数 == 快照数",
            )


def time_travel_group() -> None:
    section("time_travel")
    saver = MemorySaver()
    graph = _linear().compile(checkpointer=saver)
    graph.invoke({"log": []}, RunConfig(thread_id="tt"))
    history = list(graph.get_state_history(RunConfig(thread_id="tt")))
    check(bool(history), "时间旅行基线历史非空")

    base = next(item for item in history if item.next == ("b",))
    before = {
        item.config.configurable["checkpoint_id"]: dict(item.values) for item in history
    }
    fork = graph.update_state(base.config, {"x": 99, "log": ["fork"]}, as_node="a")
    branch = graph.get_state(fork)
    check(branch is not None and branch.values["x"] == 99, "update_state 覆盖型通道生效")
    check(branch is not None and branch.values["log"] == ["a", "fork"], "update_state 归约型通道追加")
    after = {
        item.config.configurable["checkpoint_id"]: dict(item.values)
        for item in graph.get_state_history(RunConfig(thread_id="tt"))
    }
    check(
        all(after.get(checkpoint_id) == values for checkpoint_id, values in before.items()),
        "分叉后原历史不变",
    )

    for snapshot in history:
        if not snapshot.next:
            continue
        result = graph.invoke(None, snapshot.config)
        check(result["log"] == ["a", "b", "c"], f"从 {snapshot.next} 重放到一致终态")

    dsaver = MemorySaver()
    dynamic = _interrupting().compile(checkpointer=dsaver)
    paused = dynamic.invoke({"log": []}, RunConfig(thread_id="tt-interrupt"))
    check("__interrupt__" in paused, "中断组合：invoke 暂停")
    st = dynamic.get_state(RunConfig(thread_id="tt-interrupt"))
    check(st is not None and bool(st.interrupts), "中断组合：interrupts 关联")
    resumed = dynamic.invoke(Command(resume="ok"), RunConfig(thread_id="tt-interrupt"))
    check(resumed["log"] == ["a", "answered"], "中断组合：Command(resume) 恢复")


def main() -> int:
    for name, fn in (
        ("trace", trace_group),
        ("checkpoint", checkpoint_group),
        ("time_travel", time_travel_group),
    ):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - 单组失败不中断其余检查
            print(f"  ✘ {name}: {type(exc).__name__}: {exc}")
            FAILURES.append(f"{name}: {type(exc).__name__}: {exc}")

    print(f"\n── diagnostics 汇总 ──\n硬断言 {CHECKS} 条 · 失败 {len(FAILURES)}")
    for failure in FAILURES:
        print(f"  ✘ {failure}")
    if FAILURES:
        print("diagnostics: FAIL")
        return 1
    print("diagnostics: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
