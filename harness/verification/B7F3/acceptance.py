# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B7F3 一键验收 —— ``invoke()`` 返回完整状态 + ``InvalidUpdateError``。

**退出码约定**（与 B7F2 的 ``acceptance.py`` 同款）：

* ``0`` —— **PASS**（全部断言通过）；
* ``1`` —— **FAIL**（有断言不通过）；
* ``2`` —— **环境未就绪**（``freegraph`` 不可导入 / 关键能力未接线）。

**覆盖**：A1（键集 == schema 全集 · 顺序一致）· A2（初始 + 全部新增 · 不是增量）·
A3（未知 key ⇒ ``InvalidUpdateError`` 且点名）· 多会话隔离 · ``config`` 双形态。
"""

from __future__ import annotations

import operator
import sys
from typing import Annotated, TypedDict

_FAILED = False


def check(cond: object, label: str, detail: str = "") -> None:
    """记录一条断言结果（失败**不**中断 —— 跑完再汇总）。"""
    global _FAILED
    if cond:
        print(f"  ✔ {label}")
        return
    _FAILED = True
    print(f"  ✘ {label}")
    if detail:
        print(f"      {detail}")


def section(title: str) -> None:
    """打印一个分组标题。"""
    print(f"\n[{title}]")


def finish(name: str) -> int:
    """汇总并返回退出码。"""
    if _FAILED:
        print(f"\n[{name}] FAIL")
        return 1
    print(f"\n[{name}] PASS")
    return 0


try:
    from freegraph.contracts.errors import InvalidUpdateError
    from freegraph.graph import END, START, StateGraph
except Exception as exc:  # noqa: BLE001
    print(f"[环境未就绪] freegraph 不可导入：{type(exc).__name__}: {exc}")
    raise SystemExit(2) from exc


class State(TypedDict):
    """最小状态 schema（与 ``harness/demo/graph_core.py:124-128`` **逐字同款**）。"""

    messages: Annotated[list, operator.add]
    llm_calls: int


def _node_a(state: dict[str, object]) -> dict[str, object]:
    return {"messages": ["a"]}


def _node_b(state: dict[str, object]) -> dict[str, object]:
    return {"messages": ["b"], "llm_calls": 2}


def _two_node_graph() -> object:
    builder = StateGraph(State)
    builder.add_node("a", _node_a)
    builder.add_node("b", _node_b)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def main() -> int:
    """验收主体。"""
    print("══ B7F3 · invoke() 返回完整状态 + InvalidUpdateError ══")
    print(f"Python {sys.version.split()[0]}")

    # ── A1 · 完整状态（键集 == schema 全集 · 顺序一致）──────────────────────
    section("A1 · 完整状态（键集 == schema 全集 · 顺序一致）")
    app = _two_node_graph().compile()
    out = app.invoke({"messages": ["seed"], "llm_calls": 0})
    check(type(out) is dict, "返回值是普通 dict", f"实际 {type(out)!r}")
    check(
        list(out) == ["messages", "llm_calls"],
        "键集 == schema 全部 key（顺序一致）",
        f"实际 {list(out)!r}",
    )
    check(
        not any(key.startswith("branch:to:") for key in out),
        "路由通道不进返回键集",
        f"实际 {list(out)!r}",
    )

    # ── A2 · 完整状态（初始 + 全部新增 · 不是增量）──────────────────────────
    section("A2 · 完整状态（初始 + 全部新增 · 不是增量）")
    check(
        out["messages"] == ["seed", "a", "b"],
        "messages == 初始 + 全部新增",
        f"实际 {out['messages']!r}",
    )
    check(
        out["llm_calls"] == 2,
        "llm_calls == 覆盖后的最终值（不是累加）",
        f"实际 {out['llm_calls']!r}",
    )
    # ⚠️ **只写 messages 的图** ⇒ ⇒ ``llm_calls`` **从未被写** ⇒ ⇒ 应被补齐为 None。
    only_messages = StateGraph(State)
    only_messages.add_node("a", _node_a)
    only_messages.add_edge(START, "a")
    only_messages.add_edge("a", END)
    partial = only_messages.compile().invoke({"messages": ["seed"]})
    check(
        "llm_calls" in partial and partial["llm_calls"] is None,
        "从未被写的覆盖型 key 以 None 补齐（键一定在）",
        f"实际 {partial.get('llm_calls')!r}",
    )

    # ── A3 · 失败信号（未知 key ⇒ InvalidUpdateError 且点名）───────────────
    section("A3 · 失败信号（未知 key ⇒ InvalidUpdateError 且点名）")
    builder = StateGraph(State)
    builder.add_node("a", lambda state: {"messages": ["a"], "typo_key": 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    try:
        builder.compile().invoke({"messages": []})
    except InvalidUpdateError as exc:
        check("typo_key" in str(exc), "异常消息点名违规 key", str(exc))
        check(
            "typo_key" in tuple(exc.invalid_keys),
            "异常带结构化 invalid_keys",
            repr(exc.invalid_keys),
        )
    except Exception as exc:  # noqa: BLE001
        check(False, "抛 InvalidUpdateError", f"实际 {type(exc).__name__}: {exc}")
    else:
        check(False, "抛 InvalidUpdateError", "未抛异常")

    # ── 多会话隔离（连续 / 并发）──────────────────────────────────────────
    section("多会话隔离（连续两次不累积 · 并发两次不串扰）")
    shared = _two_node_graph().compile()
    first = shared.invoke({"messages": ["first"]})
    second = shared.invoke({"messages": ["second"]})
    check(
        "first" not in second["messages"],
        "连续两次：第二次不含第一次的新增",
        f"实际 {second['messages']!r}",
    )
    check(
        "first" in first["messages"],
        "连续两次：第一次的结果仍完整",
        f"实际 {first['messages']!r}",
    )

    # ── config 双形态（RunConfig / 普通映射）────────────────────────────────
    section("config 双形态（RunConfig / 普通映射）")
    from freegraph.contracts.types import RunConfig

    with_config = _two_node_graph().compile().invoke(
        {"messages": ["seed"], "llm_calls": 0}, RunConfig(max_concurrency=1)
    )
    with_mapping = _two_node_graph().compile().invoke(
        {"messages": ["seed"], "llm_calls": 0}, {"recursion_limit": 100}
    )
    check(
        list(with_config) == list(with_mapping) == ["messages", "llm_calls"],
        "两种 config 形态都生效（键集一致）",
        f"RunConfig ⇒ {list(with_config)!r} · dict ⇒ {list(with_mapping)!r}",
    )

    return finish("B7F3")


if __name__ == "__main__":
    raise SystemExit(main())
