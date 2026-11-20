#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B8F3 · 一键验收脚本（`context` 独立通道 + `RunConfig` 接线 + alias 移除）。

一条命令跑完本 feature 的机械验收：

    .venv/bin/python harness/verification/B8F3/acceptance.py

覆盖：
- A1  C21：节点经 `state.context` 读到 context；`invoke` / `values` 无 context；
      `context is None` ⇒ 精确 `dict`；非 None ⇒ `dict` 子类视图。
- A2  C22：`RunConfig` 九字段不变；四核心字段可读；`configurable` 不承载 context。
- A3  C25 退役：`add_node(..., alias=...)` ⇒ `TypeError`；`_NodeRecord` /
      `_BuilderSpec` 无 `alias` 字段。
- A4  路由 / 流式 / 图导出：fresh 视图无 context；双参路由可读原始 config；
      节点名始终是内部名。
- A5  公开面 / 零依赖：`runtime.__all__ == 23`；源码无 `langchain*` /
      `langgraph*` / `langsmith*` import。
- A6  差分 D-137…D-144：上游缺席 ⇒ SKIP；在场 ⇒ 判词全绿。
- A7  人工验证记录：五段式 + T-1…T-7 追认 + 发起者确认在位。

退出码：``0`` = PASS · ``1`` = FAIL · ``2`` = 环境未就绪。
最后一行 MUST 打印 ``B8F3 acceptance: PASS|FAIL``。
"""

from __future__ import annotations

import argparse
import dataclasses
import inspect
import re
import subprocess
import sys
from pathlib import Path
from typing import Annotated, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

try:
    from freegraph._stategraph import _BuilderSpec, _NodeRecord
    from freegraph.contracts import RunConfig
    from freegraph.graph import END, START, Send, StateGraph
    from freegraph.runtime import SchedulerState, run_graph
except Exception as exc:  # pragma: no cover - 环境未就绪
    print(f"B8F3 acceptance: FAIL (environment: {exc})")
    raise SystemExit(2) from exc

_FAILURES: list[str] = []
_CHECKS = 0
_SKIPPED = 0


def _check(name: str, fn) -> None:
    global _CHECKS
    _CHECKS += 1
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
        _FAILURES.append(name)
    else:
        print(f"[PASS] {name}")


class _Append:
    @staticmethod
    def apply(left: list[str], right: list[str]) -> list[str]:
        return [*left, *right]


class State(TypedDict, total=False):
    x: int
    messages: Annotated[list[str], _Append.apply]


def _one(seen: dict, node=None):
    def default_node(state: dict) -> dict:
        seen["state"] = state
        seen["context"] = getattr(state, "context", None)
        return {"x": 1}

    builder = StateGraph(State)
    builder.add_node("n", node or default_node)
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    return builder.compile()


# ── A1 · C21 context 独立通道 ───────────────────────────────────────────────


def _a1_context() -> None:
    seen: dict = {}
    app = _one(seen)
    ctx = {"user": "u1"}

    out = app.invoke({"x": 0}, RunConfig(context=ctx))
    assert seen["context"] is ctx
    assert "context" not in out

    values = list(app.stream({"x": 0}, RunConfig(context=ctx), stream_mode="values"))
    assert values and all("context" not in event["payload"] for event in values)

    seen_none: dict = {}
    _one(seen_none).invoke({"x": 0})
    assert seen_none["context"] is None
    assert type(seen_none["state"]) is dict

    seen_empty: dict = {}
    _one(seen_empty).invoke({"x": 0}, RunConfig(context={}))
    assert seen_empty["context"] == {}
    assert isinstance(seen_empty["state"], dict)
    assert type(seen_empty["state"]) is not dict


# ── A2 · C22 RunConfig / configurable ───────────────────────────────────────


def _a2_run_config() -> None:
    names = tuple(field.name for field in dataclasses.fields(RunConfig))
    assert names == (
        "thread_id",
        "context",
        "metadata",
        "tags",
        "configurable",
        "max_concurrency",
        "recursion_limit",
        "run_name",
        "run_id",
    )
    cfg = RunConfig(
        thread_id="t",
        context={"u": 1},
        metadata={"m": 1},
        tags=["a"],
    )
    assert cfg.thread_id == "t"
    assert cfg.context == {"u": 1}
    assert cfg.metadata == {"m": 1}
    assert cfg.tags == ("a",)
    assert cfg.configurable == {}

    seen: dict = {}
    _one(seen).invoke({"x": 0}, RunConfig(context={"u": 1}))
    assert "configurable" not in seen["state"]
    assert not hasattr(seen["state"], "configurable")

    seen_only: dict = {}
    _one(seen_only).invoke({"x": 0}, {"configurable": {"context": {"u": 1}}})
    assert seen_only["context"] is None
    assert type(seen_only["state"]) is dict


# ── A3 · C25 退役 / alias 移除 ──────────────────────────────────────────────


def _a3_alias_removed() -> None:
    assert "alias" not in inspect.signature(StateGraph.add_node).parameters
    builder = StateGraph(State)
    try:
        builder.add_node("a", lambda state: {}, alias="model")
    except TypeError as exc:
        assert "alias" in str(exc)
    else:
        raise AssertionError("add_node(alias=...) 未抛 TypeError")

    record_fields = {field.name for field in dataclasses.fields(_NodeRecord)}
    spec_fields = {field.name for field in dataclasses.fields(_BuilderSpec)}
    assert "alias" not in record_fields
    assert "alias" not in spec_fields


# ── A4 · 路由 / 流式 / 图导出 ───────────────────────────────────────────────


def _a4_route_and_names() -> None:
    seen: dict = {}
    cfg = RunConfig(context={"route": 1})

    def route(state: dict, config) -> str:
        seen["state"] = state
        seen["config"] = config
        return "b"

    builder = StateGraph(State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_conditional_edges("a", route, ["b", END])
    builder.add_edge("b", END)
    app = builder.compile()

    out = app.invoke({"x": 0}, cfg)
    assert out["x"] == 2
    assert "context" not in out
    assert type(seen["state"]) is dict
    assert "context" not in seen["state"]
    assert not hasattr(seen["state"], "context")
    assert seen["config"] is cfg
    assert seen["config"].context == {"route": 1}

    updates = list(app.stream({}, RunConfig(context={"u": 1}), stream_mode="updates"))
    assert [set(event["payload"]) for event in updates] == [{"a"}, {"b"}]
    tasks = list(app.stream({}, RunConfig(context={"u": 1}), stream_mode="tasks"))
    assert {event["payload"].name for event in tasks} == {"a", "b"}
    assert all(node.id == node.name for node in app.get_graph().nodes)


# ── A5 · 公开面 / 零依赖 ────────────────────────────────────────────────────


def _a5_public_and_zero_deps() -> None:
    import freegraph.runtime as runtime

    assert len(runtime.__all__) == 23
    assert "context" not in SchedulerState().channels
    source = REPO_ROOT / "src" / "freegraph"
    for path in source.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(
            r"^\s*(import|from)\s+(langchain|langgraph|langsmith)", text, re.M
        ), f"禁止的第三方 import：{path}"


# ── A6 · 差分 D-137…D-144 ───────────────────────────────────────────────────


def _a6_differential() -> None:
    import importlib.util

    if importlib.util.find_spec("langgraph") is None:
        global _SKIPPED
        _SKIPPED += 1
        print("[SKIP] A6 · 上游 langgraph 缺席 —— 差分 D-137…D-144 跳过")
        return
    script = REPO_ROOT / "harness" / "scripts" / "diff_parity.py"
    proc = subprocess.run(
        [sys.executable, str(script), "-k", "context D-"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "场景数 8" in proc.stdout
    assert "失败 0" in proc.stdout


# ── A7 · 人工验证记录 ───────────────────────────────────────────────────────


def _a7_manual_record() -> None:
    record = REPO_ROOT / "harness" / "verification" / "B8F3" / "manual-verification.md"
    assert record.is_file(), f"缺少人工验证记录：{record}"
    text = record.read_text(encoding="utf-8")
    for heading in ("## 1. ", "## 2. ", "## 3. ", "## 4. ", "## 5. "):
        assert heading in text
    for index in range(1, 8):
        assert f"T-{index}" in text
    assert "发起者确认" in text
    assert "2026-11-20" in text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-differential", action="store_true")
    args = parser.parse_args(argv)

    checks = [
        ("A1 · C21 context 独立通道", _a1_context),
        ("A2 · C22 RunConfig / configurable", _a2_run_config),
        ("A3 · C25 退役 / alias 移除", _a3_alias_removed),
        ("A4 · 路由 / 流式 / 图导出", _a4_route_and_names),
        ("A5 · 公开面 / 零依赖", _a5_public_and_zero_deps),
    ]
    if args.skip_differential:
        print("[SKIP] A6 · 差分组 —— --skip-differential")
    else:
        checks.append(("A6 · 差分 D-137…D-144", _a6_differential))
    checks.append(("A7 · 人工验证记录", _a7_manual_record))

    for name, fn in checks:
        _check(name, fn)

    print()
    print(
        f"B8F3 acceptance: {'PASS' if not _FAILURES else 'FAIL'}"
        f"（{_CHECKS - len(_FAILURES)}/{_CHECKS} 通过，跳过 {_SKIPPED}）"
    )
    return 0 if not _FAILURES else 1


if __name__ == "__main__":
    raise SystemExit(main())
