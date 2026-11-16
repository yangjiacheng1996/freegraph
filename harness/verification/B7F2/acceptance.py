#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B7F2 · ``compile()`` → ``CompiledGraph`` 一键验收。

    .venv/bin/python harness/verification/B7F2/acceptance.py

退出码：``0`` = PASS · ``1`` = FAIL · ``2`` = 环境未就绪。
本脚本**不执行**任何节点 / 路由 / 归约器，只验收**编译期**判据。
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    from freegraph.graph import END, START, StateGraph
    from freegraph.runtime import GraphSpec, InvalidSchemaError
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"[环境未就绪] 无法导入 freegraph：{exc}")
    raise SystemExit(2) from exc

_FAILURES: list[str] = []
_CHECKS = 0

CAPABILITY_METHODS = (
    "invoke",
    "stream",
    "get_graph",
    "get_state",
    "get_state_history",
    "update_state",
)


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


def node(state: dict[str, Any]) -> dict[str, Any]:
    return {}


def router(state: dict[str, Any]) -> str:
    return "b"


def minimal_builder() -> StateGraph:
    graph = StateGraph(State)
    graph.add_node("a", node)
    graph.add_node("b", node)
    graph.add_edge(START, "a")
    graph.add_edge("a", "b")
    graph.add_edge("b", END)
    return graph


def compile_error(builder: StateGraph, *, field: str, value: Any) -> BaseException | None:
    try:
        builder.compile(**{field: value})
    except BaseException as exc:  # noqa: BLE001 - 验收只关心失败信号
        return exc
    return None


def _capture_warnings(call: Any) -> tuple[Any, list[warnings.WarningMessage]]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = call()
    return value, caught


def a1_capability_surface() -> None:
    print("\n[A1 · 能力面]")
    compiled = minimal_builder().compile()
    check(compiled is not None, "A1 compile() 无参可调用")
    for name in CAPABILITY_METHODS:
        check(hasattr(compiled, name), f"A1 产物具备 {name}()")


def a2_a3_injections() -> None:
    print("\n[A2/A3 · 注入项]")
    try:
        minimal_builder().compile(checkpointer=None, store=None)
        check(True, "A2 compile(checkpointer=None, store=None) 被接受")
    except TypeError as exc:
        check(False, f"A2 compile(checkpointer=None, store=None) 被接受：{exc}")

    sentinel_ckpt, sentinel_store = object(), object()
    compiled, caught = _capture_warnings(
        lambda: minimal_builder().compile(
            checkpointer=sentinel_ckpt, store=sentinel_store
        )
    )
    check(compiled.checkpointer is sentinel_ckpt, "A3 checkpointer 身份保留")
    check(compiled.store is sentinel_store, "A3 store 身份保留")
    check(len(caught) == 1, "A3 store 非 None ⇒ 恰好 1 条 warning")
    check(
        "v1 不支持 Store" in str(caught[0].message),
        "A3 warning 点名「v1 不支持 Store」",
    )
    _, caught_none = _capture_warnings(lambda: minimal_builder().compile(store=None))
    check(len(caught_none) == 0, "A3 store=None ⇒ 0 条 warning")


def b1_core_errors() -> None:
    print("\n[B1 · 3 类核心错误]")
    try:
        StateGraph(dict).compile()
    except InvalidSchemaError:
        check(True, "B1 非法 schema ⇒ InvalidSchemaError")
    else:
        check(False, "B1 非法 schema ⇒ InvalidSchemaError")

    graph = minimal_builder()
    graph.add_edge("a", "missing")
    try:
        graph.compile()
    except ValueError as raised:
        check("missing" in str(raised), "B1 未知静态边目标 ⇒ ValueError 点名")
    else:
        check(False, "B1 未知静态边目标 ⇒ ValueError 点名")

    graph = minimal_builder()
    graph.add_conditional_edges("nope", router, ["a"])
    try:
        graph.compile()
    except ValueError as raised:
        check("nope" in str(raised), "B1 未知条件边源 ⇒ ValueError 点名")
    else:
        check(False, "B1 未知条件边源 ⇒ ValueError 点名")

    graph = minimal_builder()
    graph.add_conditional_edges("a", router, {"x": "missing"})
    try:
        graph.compile()
    except ValueError as raised:
        check("missing" in str(raised), "B1 未知 path_map 目标 ⇒ ValueError 点名")
    else:
        check(False, "B1 未知 path_map 目标 ⇒ ValueError 点名")


def b2_static_interrupts() -> None:
    print("\n[B2 · 静态断点 6 形态]")
    compiled = minimal_builder().compile(interrupt_before=None)
    check(compiled.interrupt_before_nodes == (), "B2 None ⇒ ()")

    compiled = minimal_builder().compile(interrupt_before="*")
    check(compiled.interrupt_before_nodes == ("a", "b"), "B2 裸 * ⇒ 全部可执行节点")

    compiled = minimal_builder().compile(interrupt_before=["b", "a", "b"])
    check(compiled.interrupt_before_nodes == ("b", "a"), "B2 list ⇒ 保序去重")

    exc = compile_error(minimal_builder(), field="interrupt_before", value=("a",))
    check(isinstance(exc, TypeError), "B2 元组 ⇒ TypeError")

    exc = compile_error(minimal_builder(), field="interrupt_before", value="a")
    check(isinstance(exc, TypeError), "B2 裸非 * 字符串 ⇒ TypeError")

    exc = compile_error(minimal_builder(), field="interrupt_before", value=["nope"])
    check(
        isinstance(exc, ValueError) and "nope" in str(exc),
        "B2 未知节点 ⇒ ValueError 点名",
    )


def b3_end_filtering_and_v16() -> None:
    print("\n[B3 · END 过滤 / V-16 / 保留名]")
    compiled = minimal_builder().compile()
    check("b" not in compiled._spec.edges, "B3 单源 END 目标被整体移除")

    graph = minimal_builder()
    graph.add_edge(["a", "b"], END)
    try:
        graph.compile()
    except ValueError as raised:
        check("V-16" in str(raised), "B3 多源 END ⇒ V-16 ValueError")
    else:
        check(False, "B3 多源 END ⇒ V-16 ValueError")

    graph = StateGraph(State)
    graph.add_node("__parent__", node)
    graph.add_edge(START, "__parent__")
    graph.add_edge("__parent__", END)
    try:
        graph.compile()
    except ValueError as raised:
        check("__parent__" in str(raised), "B3 __parent__ ⇒ ValueError")
    else:
        check(False, "B3 __parent__ ⇒ ValueError")


def b4_snapshot_and_fields() -> None:
    print("\n[B4 · 快照 / 冻结字段 / 零调用]")
    graph = minimal_builder()
    first = graph.compile()
    second = graph.compile()
    check(first is not second, "B4 两次 compile 返回不同对象")
    before = list(first._spec.nodes)
    graph.add_node("late", node)
    check(list(first._spec.nodes) == before, "B4 编译后改图不影响已编译产物")
    check(isinstance(first._spec, GraphSpec), "B4 私有字段 _spec 是 GraphSpec")
    check(hasattr(first._builder_spec, "node_records"), "B4 私有字段 _builder_spec 完整")
    check(isinstance(first._conditional_edges, dict), "B4 私有字段 _conditional_edges 存在")
    check(
        set(vars(first))
        == {
            "_spec",
            "_builder_spec",
            "_conditional_edges",
            "checkpointer",
            "store",
            "cache",
            "debug",
            "name",
            "transformers",
            "interrupt_before_nodes",
            "interrupt_after_nodes",
        },
        "B4 vars(compiled) 恰 11 键",
    )

    counter: dict[str, int] = {}

    def counting_node(state: dict[str, Any]) -> dict[str, Any]:
        counter["node"] = counter.get("node", 0) + 1
        return {}

    graph = StateGraph(State)
    graph.add_node("n", counting_node)
    graph.add_edge(START, "n")
    graph.add_edge("n", END)
    graph.compile()
    check(counter == {}, "B4 编译期零用户函数调用")


def main() -> int:
    print("══ B7F2 · compile() → CompiledGraph 一键验收 ══")
    print(f"Python {sys.version.split()[0]}")
    a1_capability_surface()
    a2_a3_injections()
    b1_core_errors()
    b2_static_interrupts()
    b3_end_filtering_and_v16()
    b4_snapshot_and_fields()
    print(f"\n共 {_CHECKS} 项断言 · 失败 {len(_FAILURES)} 项")
    if _FAILURES:
        for label in _FAILURES:
            print(f"  ✘ {label}")
        return 1
    print("结论：PASS（B7F2 编译期判据全部满足）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
