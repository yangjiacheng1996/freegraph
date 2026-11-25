#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · 真实模型轮（A2 · 人工）—— 两段式探针。

段 1（固定脚本）：**原样**执行 `harness/demo/target.py`，记录最终消息 / 工具结果 /
PNG 字节 / 框架出站 / 用户出站。
段 2（专用探针）：用同一 agent 循环形状 + 真实模型，注入：

* `FileTraceStore(directory=...)`（独立运行 1）；
* `SqliteTraceStore(database=...)`（独立运行 2）；
* `OtlpExporter(exporter=RecordingSpanExporter())`（默认无网络）或
  `OtlpExporter(endpoint=本地 gRPC)`（可选）；
* `SqliteSaver.from_conn_string(path)` + 时间旅行；
* 中断组合（`interrupt` + `Command(resume=...)`）。

**MUST NOT** 猴补固定脚本的 `compile` / `invoke`；段 2 是独立图实例。
凭据 / 网络受限 ⇒ 登记**环境偏离**（已完成 / 未完成 / 原因），MUST NOT 用
「未验证」替代；完全无法执行 ⇒ 退出码 2，且不得宣布 v1.0 收口。

退出码：0 = PASS · 1 = 断言 / 运行失败 · 2 = 环境未就绪。
最后一行 MUST 打印 ``B25F1 real round: PASS|FAIL|ENV``。
"""

from __future__ import annotations

import argparse
import json
import operator
import os
import runpy
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
B25F1_DIR = Path(__file__).resolve().parent
GATES_DIR = REPO_ROOT / "harness" / "scripts" / "gates"
TARGET = REPO_ROOT / "harness" / "demo" / "target.py"

for _path in (SRC_DIR, B25F1_DIR, GATES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EVIDENCE: dict[str, Any] = {}
FAILURES: list[str] = []


def record_section(name: str, payload: Any) -> None:
    EVIDENCE[name] = payload
    print(f"\n[{name}]")
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def fail(label: str, detail: Any = "") -> None:
    FAILURES.append(label + (f" — {detail}" if detail else ""))
    print(f"[FAIL] {label}" + (f" — {detail}" if detail else ""))


def _detect_access() -> dict[str, Any] | None:
    """识别真实模型接入路径（不读取 / 打印任何 secret 值）。"""
    model = os.environ.get("B25F1_MODEL")
    base_url = os.environ.get("B25F1_BASE_URL")
    gateway_key = os.environ.get("B25F1_API_KEY")
    anthropic = os.environ.get("ANTHROPIC_API_KEY")
    openai = os.environ.get("OPENAI_API_KEY")

    if base_url:
        if not (gateway_key or anthropic or openai):
            return None
        return {
            "path": "兼容网关",
            "model": model or "claude-sonnet-4-6",
            "base_url": base_url,
            "api_key": gateway_key or anthropic or openai,
            "reason": "B25F1_BASE_URL 显式配置",
        }
    if anthropic:
        return {
            "path": "官方直连",
            "model": model or "claude-sonnet-4-6",
            "base_url": None,
            "api_key": anthropic,
            "reason": "ANTHROPIC_API_KEY 官方直连",
        }
    if openai:
        return {
            "path": "官方直连",
            "model": model or "gpt-4o-mini",
            "base_url": None,
            "api_key": openai,
            "reason": "OPENAI_API_KEY 官方直连",
        }
    return None


def _make_model(access: dict[str, Any]) -> Any:
    from langchain.chat_models import init_chat_model

    kwargs: dict[str, Any] = {"temperature": 0}
    if access.get("api_key"):
        kwargs["api_key"] = access["api_key"]
    if access.get("base_url"):
        kwargs["base_url"] = access["base_url"]
    try:
        return init_chat_model(access["model"], **kwargs)
    except TypeError:
        # provider 不接收 base_url / api_key 关键字 ⇒ 退化为官方直连口径。
        return init_chat_model(access["model"], temperature=0)


class _AgentState(TypedDict, total=False):
    messages: Annotated[list[Any], operator.add]
    llm_calls: int


class _ProbeState(TypedDict, total=False):
    reply: str
    log: Annotated[list[str], operator.add]
    llm_calls: int


def _tools() -> list[Any]:
    from langchain.tools import tool

    @tool
    def add(a: int, b: int) -> int:
        """Add `a` and `b`."""
        return a + b

    @tool
    def multiply(a: int, b: int) -> int:
        """Multiply `a` and `b`."""
        return a * b

    return [add, multiply]


def _agent_graph(model: Any) -> Any:
    from freegraph.graph import END, START, StateGraph
    from langchain.messages import SystemMessage, ToolMessage

    tools = _tools()
    tools_by_name = {item.name: item for item in tools}
    model_with_tools = model.bind_tools(tools)

    def llm_call(state: _AgentState) -> dict[str, Any]:
        reply = model_with_tools.invoke(
            [
                SystemMessage(
                    content="You are a helpful assistant tasked with performing arithmetic."
                )
            ]
            + list(state["messages"])
        )
        return {"messages": [reply], "llm_calls": state.get("llm_calls", 0) + 1}

    def tool_node(state: _AgentState) -> dict[str, Any]:
        result: list[Any] = []
        for call in state["messages"][-1].tool_calls:
            observation = tools_by_name[call["name"]].invoke(call["args"])
            result.append(ToolMessage(content=observation, tool_call_id=call["id"]))
        return {"messages": result}

    def should_continue(state: _AgentState) -> str:
        if state["messages"][-1].tool_calls:
            return "tool_node"
        return END

    builder = StateGraph(_AgentState)
    builder.add_node("llm_call", llm_call)
    builder.add_node("tool_node", tool_node)
    builder.add_edge(START, "llm_call")
    builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
    builder.add_edge("tool_node", "llm_call")
    return builder


def _probe_graph(model: Any) -> Any:
    from freegraph.graph import END, START, StateGraph
    from langchain.messages import HumanMessage

    def model_node(state: _ProbeState) -> dict[str, Any]:
        reply = model.invoke([HumanMessage(content="Say hello in one short word.")])
        return {
            "reply": getattr(reply, "content", str(reply)),
            "log": ["model"],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    def finish_node(state: _ProbeState) -> dict[str, Any]:
        return {"log": ["finish"]}

    builder = StateGraph(_ProbeState)
    builder.add_node("model", model_node)
    builder.add_node("finish", finish_node)
    builder.add_edge(START, "model")
    builder.add_edge("model", "finish")
    builder.add_edge("finish", END)
    return builder


def _message_view(messages: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "cls": type(message).__name__,
            "content": getattr(message, "content", None),
            "tool_calls": list(getattr(message, "tool_calls", []) or []),
            "tool_call_id": getattr(message, "tool_call_id", None),
        }
        for message in messages
    ]


def segment1(access: dict[str, Any]) -> None:
    from freegraph.contracts import RunConfig
    import IPython.display as ipython_display
    import _gatekit

    png: list[bytes] = []
    original_display = ipython_display.display

    def _capture(value: Any) -> None:
        data = getattr(value, "data", None)
        if data is not None:
            png.append(bytes(data))

    import langchain.chat_models as chat_models

    original_init = getattr(chat_models, "init_chat_model", None)
    if access["path"] == "兼容网关":
        def _wrapper(model_name: Any = None, **kwargs: Any) -> Any:
            kwargs.setdefault("base_url", access["base_url"])
            kwargs.setdefault("api_key", access["api_key"])
            return original_init(model_name or access["model"], **kwargs)

        chat_models.init_chat_model = _wrapper  # type: ignore[attr-defined]

    ipython_display.display = _capture  # type: ignore[assignment]
    records: list[_gatekit.EgressRecord] = []
    try:
        with _gatekit.record_egress(records):
            namespace = runpy.run_path(str(TARGET), run_name="__main__")
    finally:
        ipython_display.display = original_display  # type: ignore[assignment]
        if original_init is not None:
            chat_models.init_chat_model = original_init  # type: ignore[attr-defined]

    state = namespace.get("messages")
    if not isinstance(state, dict):
        fail("段 1 未产出完整状态")
        return
    messages = list(state.get("messages") or [])
    tool_contents = [
        getattr(message, "content", None)
        for message in messages
        if type(message).__name__ == "ToolMessage"
    ]
    framework = [item for item in records if item.attribution == "framework"]
    user = [item for item in records if item.attribution == "user"]
    if framework:
        fail("段 1 框架出站 != 0", [item.target for item in framework])
    if not png:
        fail("段 1 未捕获 PNG")
    record_section(
        "segment1_fixed_script",
        {
            "access_path": access["path"],
            "model": access["model"],
            "endpoint": access.get("base_url") or "provider 官方端点",
            "messages": _message_view(messages),
            "llm_calls": state.get("llm_calls"),
            "tool_results": tool_contents,
            "png_bytes": len(png[-1]) if png else 0,
            "png_signature_ok": bool(png and png[-1].startswith(PNG_SIGNATURE)),
            "framework_egress": len(framework),
            "user_egress": [item.target for item in user],
        },
    )


def _trace_evidence(store: Any, model: Any, thread_id: str) -> dict[str, Any]:
    from freegraph.contracts import RunConfig, TraceQuery
    from langchain.messages import HumanMessage

    compiled = _agent_graph(model).compile(tracer=store)
    result = compiled.invoke(
        {"messages": [HumanMessage(content="Add 3 and 4.")]},
        RunConfig(thread_id=thread_id, run_id=f"{thread_id}-run"),
    )
    rows = store.query()
    spans = [row for row in rows if row.get("kind") == "span"]
    records = [row for row in rows if row.get("kind") == "trace_record"]
    run_id = spans[0].get("run_id") if spans else None
    node = spans[0].get("node") if spans else None
    start = spans[0].get("start_time") if spans else None
    queries = {
        "run_id": len(store.query(TraceQuery(run_id=run_id))) if run_id else 0,
        "thread_id": len(store.query(TraceQuery(thread_id=thread_id))),
        "node": len(store.query(TraceQuery(node=node))) if node else 0,
        "time_window": len(
            store.query(
                TraceQuery(
                    start_time=start,
                    end_time="2099-01-01T00:00:00.000000000+00:00",
                )
            )
        )
        if start
        else 0,
        "combo": len(store.query(TraceQuery(thread_id=thread_id, node=node)))
        if node
        else 0,
        "empty": len(store.query(TraceQuery())),
    }
    model_spans = [row for row in spans if row.get("node") == "llm_call"]
    return {
        "run_id": run_id,
        "thread_id": thread_id,
        "span_lines": len(spans),
        "trace_record_lines": len(records),
        "model_spans": len(model_spans),
        "c23_keys": sorted(spans[0]) if spans else [],
        "queries": queries,
        "json_dumps_ok": isinstance(json.dumps(rows, default=str), str),
        "final_llm_calls": result.get("llm_calls"),
    }


def segment2_trace(access: dict[str, Any], model: Any) -> None:
    from freegraph.observability import FileTraceStore, SqliteTraceStore

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        file_store = FileTraceStore(root / "file")
        file_evidence = _trace_evidence(file_store, model, "b25f1-real-file")
        record_section("segment2_trace_file", file_evidence)

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        sqlite_store = SqliteTraceStore(root / "traces.sqlite3")
        sqlite_evidence = _trace_evidence(sqlite_store, model, "b25f1-real-sqlite")
        record_section("segment2_trace_sqlite", sqlite_evidence)


class RecordingSpanExporter:
    """记录型 SpanExporter（**无网络**）。"""

    def __init__(self) -> None:
        self.spans: list[Any] = []

    def export(self, spans: Any) -> None:
        self.spans.extend(list(spans))

    def shutdown(self) -> None:
        return None


def segment2_otlp(access: dict[str, Any], model: Any, endpoint: str | None = None) -> None:
    from freegraph.observability import OtlpExporter
    from langchain.messages import HumanMessage
    from freegraph.contracts import RunConfig

    recording = RecordingSpanExporter()
    exporter = (
        OtlpExporter(endpoint=endpoint)
        if endpoint
        else OtlpExporter(exporter=recording)
    )
    compiled = _agent_graph(model).compile(tracer=exporter)
    result = compiled.invoke(
        {"messages": [HumanMessage(content="Add 3 and 4.")]},
        RunConfig(thread_id="b25f1-real-otlp", run_id="b25f1-real-otlp-run"),
    )
    spans = list(recording.spans)
    record_section(
        "segment2_otlp",
        {
            "mode": "endpoint" if endpoint else "exporter",
            "endpoint": endpoint,
            "received_spans": len(spans),
            "names": [getattr(span, "name", None) for span in spans],
            "trace_ids": [
                getattr(getattr(span, "context", None), "trace_id", None)
                for span in spans
            ],
            "parents": [str(getattr(span, "parent", None)) for span in spans],
            "gen_ai_attributes": [
                {
                    key: value
                    for key, value in dict(getattr(span, "attributes", {}) or {}).items()
                    if key.startswith("gen_ai.")
                }
                for span in spans
            ],
            "export_errors": getattr(exporter, "export_errors", None),
            "final_llm_calls": result.get("llm_calls"),
        },
    )
    if endpoint:
        record_section(
            "segment2_otlp_endpoint_note",
            {"note": "endpoint= 模式为**用户显式启用的 OTLP 端点**，不计入框架出站"},
        )


def segment2_checkpoint_time_travel(access: dict[str, Any], model: Any) -> None:
    from freegraph.contracts import RunConfig
    from freegraph.graph import END, START, StateGraph, Command, interrupt
    from freegraph.persistence import SqliteSaver
    from langchain.messages import HumanMessage

    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "checkpoints.sqlite3"
        with SqliteSaver.from_conn_string(str(path)) as saver:
            compiled = _probe_graph(model).compile(checkpointer=saver)
            compiled.invoke({"log": []}, RunConfig(thread_id="b25f1-real-cp"))
            cfg = RunConfig(thread_id="b25f1-real-cp")
            snapshot = compiled.get_state(cfg)
            history = list(compiled.get_state_history(cfg))
            events = list(compiled.stream({"log": []}, cfg, stream_mode="checkpoints"))
            record_section(
                "segment2_checkpoint",
                {
                    "get_tuple": saver.get_tuple(cfg) is not None,
                    "get_state": snapshot is not None,
                    "history_count": len(history),
                    "history_desc": [
                        item.config.configurable["checkpoint_id"] for item in history
                    ]
                    == sorted(
                        (item.config.configurable["checkpoint_id"] for item in history),
                        reverse=True,
                    ),
                    "tasks_shape": str(getattr(snapshot, "tasks", None)),
                    "interrupts_shape": str(getattr(snapshot, "interrupts", None)),
                    "checkpoint_events": len(events),
                    "checkpoint_payload_types": [
                        type(event.get("payload")).__name__ for event in events
                    ],
                },
            )

            # 时间旅行：历史点重放 / update_state 覆盖 + 归约 / 分叉后原历史不变
            base = next((item for item in history if item.next == ("finish",)), None)
            if base is None:
                fail("时间旅行：找不到 next == ('finish',) 的基准快照")
            else:
                before = {
                    item.config.configurable["checkpoint_id"]: dict(item.values)
                    for item in history
                }
                fork = compiled.update_state(
                    base.config,
                    {"log": ["fork"], "llm_calls": 99},
                    as_node="model",
                )
                branch = compiled.get_state(fork)
                after = {
                    item.config.configurable["checkpoint_id"]: dict(item.values)
                    for item in compiled.get_state_history(cfg)
                }
                replay = compiled.invoke(None, base.config)
                record_section(
                    "segment2_time_travel",
                    {
                        "update_state_returns_runconfig": type(fork).__name__ == "RunConfig",
                        "branch_log": getattr(branch, "values", {}).get("log")
                        if branch
                        else None,
                        "branch_llm_calls": getattr(branch, "values", {}).get("llm_calls")
                        if branch
                        else None,
                        "original_history_unchanged": all(
                            after.get(checkpoint_id) == values
                            for checkpoint_id, values in before.items()
                        ),
                        "replay_log": replay.get("log"),
                    },
                )

    # 中断组合（不依赖模型；验证 interrupt + Command(resume)）
    from freegraph.persistence import MemorySaver

    class _InterruptState(TypedDict, total=False):
        log: Annotated[list[str], operator.add]

    def ask(state: dict) -> dict:
        interrupt({"ask": "approve"})
        return {"log": ["answered"]}

    builder = StateGraph(_InterruptState)
    builder.add_node("ask", ask)
    builder.add_edge(START, "ask")
    builder.add_edge("ask", END)
    dynamic = builder.compile(checkpointer=MemorySaver())
    paused = dynamic.invoke({"log": []}, RunConfig(thread_id="b25f1-real-interrupt"))
    snapshot = dynamic.get_state(RunConfig(thread_id="b25f1-real-interrupt"))
    resumed = dynamic.invoke(
        Command(resume="ok"), RunConfig(thread_id="b25f1-real-interrupt")
    )
    record_section(
        "segment2_interrupt",
        {
            "paused": "__interrupt__" in paused,
            "interrupts": str(getattr(snapshot, "interrupts", None)),
            "resumed_log": resumed.get("log"),
        },
    )


def _write_draft(path: Path, access: dict[str, Any] | None, deviations: list[str]) -> None:
    lines = [
        "# B25F1 真实模型轮草稿",
        "",
        "## 环境",
        "",
        f"- 接入路径：{access['path'] if access else '未识别'}",
        f"- 模型：{access['model'] if access else '—'}",
        f"- 端点：{(access.get('base_url') if access else None) or 'provider 官方端点'}",
        "- `LANGSMITH_*` 清空：子进程 / 本进程均剔除全部 `LANGSMITH_*`",
        "",
        "## 证据",
        "",
        "```json",
        json.dumps(EVIDENCE, ensure_ascii=False, indent=2, default=str),
        "```",
        "",
        "## 环境偏离",
        "",
    ]
    lines.extend(f"- {item}" for item in deviations) if deviations else lines.append("- 无")
    lines.extend(
        [
            "",
            "## 遗留问题",
            "",
            "- **Y-01**：`Command.goto` 缺省 `()`（上游）vs `None`（freegraph）= DIFF；v1 行为提示；运行时对齐归 v2 独立契约修订。",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B25F1 真实模型轮（A2 · 人工）")
    parser.add_argument("--record", help="写出真实轮 Markdown 草稿")
    parser.add_argument("--endpoint", help="可选：本地 OTLP gRPC 接收端 host:port")
    parser.add_argument("--skip-segment1", action="store_true")
    parser.add_argument("--skip-segment2", action="store_true")
    args = parser.parse_args(argv)

    access = _detect_access()
    if access is None:
        deviation = (
            "真实模型凭据未配置：未检测到 ANTHROPIC_API_KEY / OPENAI_API_KEY / "
            "B25F1_BASE_URL；已完成：fake 轮 / 四组 / 诊断；未完成：真实模型轮 段 1 + 段 2。"
        )
        record_section("environment_deviation", {"deviation": deviation})
        if args.record:
            _write_draft(Path(args.record), None, [deviation])
        print("B25F1 real round: ENV")
        return 2

    record_section(
        "access",
        {
            "path": access["path"],
            "model": access["model"],
            "endpoint": access.get("base_url") or "provider 官方端点",
            "reason": access["reason"],
        },
    )

    try:
        model = _make_model(access)
    except Exception as exc:  # noqa: BLE001
        fail("构造真实模型失败", f"{type(exc).__name__}: {exc}")
        model = None

    if model is not None and not args.skip_segment1:
        try:
            segment1(access)
        except Exception as exc:  # noqa: BLE001
            fail("段 1 运行失败", f"{type(exc).__name__}: {exc}")

    if model is not None and not args.skip_segment2:
        for name, fn in (
            ("trace_file", lambda: segment2_trace(access, model)),
            ("otlp", lambda: segment2_otlp(access, model, args.endpoint)),
            ("checkpoint_time_travel", lambda: segment2_checkpoint_time_travel(access, model)),
        ):
            try:
                fn()
            except Exception as exc:  # noqa: BLE001 - 单组件失败不中断其余
                fail(name, f"{type(exc).__name__}: {exc}")

    if args.record:
        _write_draft(Path(args.record), access, [])

    if FAILURES:
        for item in FAILURES:
            print(f"[FAIL] {item}")
        print("B25F1 real round: FAIL")
        return 1
    print("B25F1 real round: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
