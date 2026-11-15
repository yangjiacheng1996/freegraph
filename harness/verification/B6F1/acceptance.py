#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B6F1 · ``StateGraph`` 构建器一键验收（建图 / 校验 / 快照 / 构建期纯净）。

    .venv/bin/python harness/verification/B6F1/acceptance.py

退出码：``0`` = PASS · ``1`` = FAIL · ``2`` = 环境未就绪。
本脚本**不执行** ``compile()`` / ``invoke()``。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Literal, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    from freegraph.graph import END, START, Send, StateGraph
    from freegraph.runtime import EphemeralValue, GraphSpec, InvalidSchemaError
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


class State(TypedDict):
    count: int


class NamedOnly:
    name = "not-used"

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        return {}


def node(state: dict[str, Any]) -> dict[str, Any]:
    return {}


def router(state: dict[str, Any]) -> str:
    return "a"


def literal_router(state: dict[str, Any]) -> Literal["a", "__end__"]:
    return "a"


def valid_builder() -> StateGraph:
    builder = StateGraph(State)
    builder.add_node("a", node)
    builder.add_node("b", node)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def target_style() -> StateGraph:
    builder = StateGraph(State)
    builder.add_node("llm_call", node)
    builder.add_node("tool_node", node)
    builder.add_edge(START, "llm_call")
    builder.add_conditional_edges("llm_call", router, ["tool_node", END])
    builder.add_edge("tool_node", "llm_call")
    return builder


def v1_target_build() -> None:
    builder = target_style()
    builder.validate()
    spec = builder._build_spec()
    check(list(spec.nodes) == ["llm_call", "tool_node"], "V1 target 节点顺序")
    check(spec.edges["__start__"] == ("llm_call",), "V1 START 边")
    check(spec.edges["tool_node"] == ("llm_call",), "V1 回边")
    check(len(spec.conditional_edges) == 1, "V1 条件边数 == 1")
    check(spec.conditional_edges[0].branch == "router", "V1 branch 记录")


def v2_path_map_forms() -> None:
    builder = StateGraph(State)
    builder.add_node("r", node)
    builder.add_node("hit", node)
    builder.add_node("miss", node)
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", router, {"hit": "hit", "miss": "miss"})
    builder.validate()
    ce = builder._build_spec().conditional_edges[0]
    check(ce.path_map == {"hit": "hit", "miss": "miss"}, "V2 dict path_map")
    check(ce.targets == ("hit", "miss"), "V2 targets 保序")
    check(ce.route_channels == ("branch:to:hit", "branch:to:miss"), "V2 路由通道")

    builder = StateGraph(State)
    builder.add_node("r", node)
    builder.add_node("a", node)
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", router, {1: "a"})
    builder.validate()
    ce = builder._build_spec().conditional_edges[0]
    check(ce.path_map == {1: "a"}, "V2 Hashable path_map key")

    builder = StateGraph(State)
    builder.add_node("r", node)
    builder.add_node("a", node)
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", literal_router)
    builder.validate()
    ce = builder._build_spec().conditional_edges[0]
    check(ce.path_map == {"a": "a", END: END}, "V2 None+Literal 推断")

    builder = StateGraph(State)
    builder.add_node("r", node)
    builder.add_node("a", node)
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", router)
    builder.validate()
    ce = builder._build_spec().conditional_edges[0]
    check(ce.path_map is None and ce.targets == (), "V2 None+非 Literal")


def v3_build_errors() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node)
    try:
        builder.add_node("a", node)
    except ValueError:
        check(True, "V3 重复节点立即失败")
    else:
        check(False, "V3 重复节点立即失败")

    builder = valid_builder()
    builder._edges["a"].append("missing")  # type: ignore[attr-defined]
    try:
        builder.validate()
    except ValueError as exc:
        check("missing" in str(exc), "V3 未知目标点名")
    else:
        check(False, "V3 未知目标点名")

    builder = StateGraph(State)
    builder.add_node("a", node)
    builder.add_edge("a", END)
    try:
        builder.validate()
    except ValueError as exc:
        check("entrypoint" in str(exc), "V3 缺入口")
    else:
        check(False, "V3 缺入口")

    builder = StateGraph({"count": 0})
    builder.add_node("a", node)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    try:
        builder.validate()
    except InvalidSchemaError:
        check(True, "V3 schema 错误传播")
    else:
        check(False, "V3 schema 错误传播")

    builder = StateGraph(State)
    builder.add_edge(START, END)
    try:
        builder.validate()
    except ValueError:
        check(True, "V3 空节点表 X-5")
    else:
        check(False, "V3 空节点表 X-5")


def v4_invalid_start_key() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node)
    try:
        builder.add_edge(123, "a")  # type: ignore[arg-type]
    except TypeError:
        check(True, "V4 非法 start_key ⇒ TypeError")
    else:
        check(False, "V4 非法 start_key ⇒ TypeError")


def v5_chain_and_purity() -> None:
    calls: list[str] = []

    def counted(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("node")
        return {}

    def counted_router(state: dict[str, Any]) -> str:
        calls.append("router")
        return "a"

    builder = StateGraph(State)
    check(builder.add_node("a", counted) is builder, "V5 add_node 链式")
    check(builder.add_edge(START, "a") is builder, "V5 add_edge 链式")
    builder.add_edge("a", END)
    check(builder.add_conditional_edges("a", counted_router, ["a", END]) is builder, "V5 条件边链式")
    check(builder.validate() is builder, "V5 validate 链式")
    builder._build_spec()
    check(calls == [], "V5 构建期零用户代码执行")


def v6_snapshot_and_graphspec() -> None:
    builder = valid_builder()
    builder.add_conditional_edges("a", router, ["a", "b", END])
    first = builder._build_spec()
    second = builder._build_spec()
    check(first is not second, "V6 每次返回新快照")
    check(first.conditional_edges[0].branch == "router", "V6 branch 冻结")
    check(first.channels["branch:to:a"] is not second.channels["branch:to:a"], "V6 新通道实例")

    edges = {}
    for key, targets in first.edges.items():
        if isinstance(key, str):
            edges[key] = tuple(target for target in targets if target != END)
        else:
            edges[key] = targets
    graph_spec = GraphSpec(channels=dict(first.channels), nodes=dict(first.nodes), edges=edges)
    check(graph_spec.conditional_edges == {}, "V6 GraphSpec 适配")
    check(isinstance(first.channels["branch:to:a"], EphemeralValue), "V6 路由通道类型")
    check(first.channels["branch:to:a"].guard is False, "V6 guard=False")


def v7_signature_parity() -> None:
    try:
        import inspect

        from langgraph.graph import StateGraph as Upstream
    except Exception:
        print("[SKIP] V7 上游 langgraph 缺席")
        return
    for name in ("__init__", "add_node", "add_edge", "add_conditional_edges", "validate"):
        ours = inspect.signature(getattr(StateGraph, name))
        theirs = inspect.signature(getattr(Upstream, name))
        ours_required = [
            p.name
            for p in ours.parameters.values()
            if p.name != "self" and p.default is p.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        theirs_required = [
            p.name
            for p in theirs.parameters.values()
            if p.name != "self" and p.default is p.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        check(ours_required == theirs_required, f"V7 {name} 必填位置参数")


def v8_minimal_and_entrypoint() -> None:
    builder = valid_builder()
    builder.validate()
    spec = builder._build_spec()
    check(len(spec.nodes) == 2 and sum(len(v) for v in spec.edges.values()) == 3, "V8 最小图")

    builder = StateGraph(State)
    builder.add_node("a", node)
    builder.add_conditional_edges(START, router, {"a": "a"})
    builder.validate()
    check(True, "V8 条件 START 入口")


def v9_retention_and_interrupt() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node)
    builder.add_node("b", node)
    builder.add_node("c", node)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    builder.add_edge(["a", "b"], END)
    builder.add_edge(["a", "b"], "c")
    builder.validate()
    edges = builder._build_spec().edges
    check(edges[("a", "b")] == (END, "c"), "V9 多源 END / 多目标保留")

    builder = StateGraph(State)
    builder.add_node("__parent__", node)
    builder.add_edge(START, "__parent__")
    builder.add_edge("__parent__", END)
    builder.validate()
    check("__parent__" in builder._build_spec().nodes, "V9 __parent__ 保留")

    builder = valid_builder()
    try:
        builder.validate(interrupt=["nope"])
    except ValueError as exc:
        check("nope" in str(exc), "V9 validate(interrupt) 未知节点")
    else:
        check(False, "V9 validate(interrupt) 未知节点")


def v10_named_only_and_runnable() -> None:
    builder = StateGraph(State)
    builder.add_node(NamedOnly())
    builder.add_edge(START, "NamedOnly")
    builder.add_edge("NamedOnly", END)
    builder.validate()
    spec = builder._build_spec()
    check("NamedOnly" in spec.nodes and "not-used" not in spec.nodes, "V10 普通 callable .name 不参与")

    try:
        from langchain_core.runnables import RunnableLambda
    except Exception:
        print("[SKIP] V10 RunnableLambda 缺席")
        return
    builder = StateGraph(State)
    builder.add_node("a", node)
    builder.add_edge(START, "a")
    try:
        builder.add_conditional_edges("a", RunnableLambda(router), ["a", END])
    except TypeError:
        check(True, "V10 非 callable Runnable 拒绝（X-6）")
    else:
        check(False, "V10 非 callable Runnable 拒绝（X-6）")


def main() -> int:
    print("══ B6F1 · StateGraph 构建器 · 一键验收 ══")
    for case in (
        v1_target_build,
        v2_path_map_forms,
        v3_build_errors,
        v4_invalid_start_key,
        v5_chain_and_purity,
        v6_snapshot_and_graphspec,
        v7_signature_parity,
        v8_minimal_and_entrypoint,
        v9_retention_and_interrupt,
        v10_named_only_and_runnable,
    ):
        try:
            case()
        except Exception as exc:  # noqa: BLE001 - 单组失败不中断其余组
            check(False, f"{case.__name__} 未完成：{type(exc).__name__}: {exc}")

    print(f"\n共 {_CHECKS} 条断言 · 失败 {len(_FAILURES)} 条")
    if _FAILURES:
        for label in _FAILURES:
            print(f"  - {label}")
        print("B6F1 acceptance: FAIL")
        return 1
    print("B6F1 acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
