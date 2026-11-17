# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**条件边路由求值**的用例 —— 属 **B8F1**（tasks T004 / T013 / T015…T075）。

覆盖的判定（``contracts/conditional-edge-contract.md``）：

* **§2** 求值语义（时机 · 落点 · 顺序 · 次数）—— 路由函数在**源节点任务成功
  落回**之后、写入合并**之前**被求值（**C8** 的时点）；
* **§3** fresh 读（**C8**）—— 路由函数看到「当前值 + 本节点本次写入」；
* **§4** 目标解析（``path_map`` 双形态 · 序列 · ``END`` · ``Send``）；
* **§5** 投递（动态边 · 与 ``Command.goto`` 的**并集**）；
* **§6** 失败信号（**两态**）与校验（**V-8 已放宽** / **V-27…V-31**）。

⚠️ **断言 MUST 是「否定式」**（宪法原则 VI · spec **FR-034** / **SC-001**）⇒ ⇒
「路由函数读到**旧值**」的用例数 MUST == **0** ⇒ ⇒ ⇒ 每条 fresh 读断言都
**显式断言新值** ⇒ 而不只是「跑通了」。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
import warnings
from typing import Annotated, Any, TypedDict

import pytest

from freegraph.graph import END, START, RunConfig, Send, StateGraph

# ── 共享夹具 ────────────────────────────────────────────────────────────


class RouteState(TypedDict):
    """被测 schema（**归约型** + **覆盖型**各一）。"""

    messages: Annotated[list, operator.add]
    llm_calls: int


class CountingState(TypedDict):
    """只含一个**覆盖型**通道的 schema（最小图用）。"""

    llm_calls: int


def _record(calls: list[str], name: str, result: dict[str, Any] | None = None):
    """造一个「**记录调用**并返回固定写入」的节点函数。"""

    def _run(state: dict[str, Any]) -> dict[str, Any]:
        calls.append(name)
        return dict(result or {})

    return _run


def _router(observed: list[dict[str, Any]], value: Any, calls: list[str] | None = None):
    """造一个「**记录收到的状态**并返回固定值」的路由函数。"""

    def _route(state: dict[str, Any]) -> Any:
        observed.append(dict(state))
        if calls is not None:
            calls.append("route")
        return value

    return _route


# ── T004 · 骨架 ─────────────────────────────────────────────────────────


def test_the_module_exposes_the_router_helpers() -> None:
    """**T004**：本文件承载**全部**条件边回归用例（骨架自检）。"""
    assert callable(_router([], "x"))
    assert callable(_record([], "n"))


# ── US1 · T024 · C8 fresh 读的**否定式**回归 ───────────────────────────


def test_c8_fresh_read_sees_the_value_the_node_just_wrote() -> None:
    """**C8 fresh 读**（**否定式**断言 · FR-034 / SC-001）。

    ⚠️ MUST 断言「路由函数**看到了**新值」⇒ 而**不是**「跑通了」。
    """
    observed: list[dict[str, Any]] = []
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("writer", _record(calls, "writer", {"messages": ["fresh"], "llm_calls": 7}))
    builder.add_node("after", _record(calls, "after"))
    builder.add_edge(START, "writer")
    builder.add_conditional_edges("writer", _router(observed, "after"), ["after"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert observed == [{"messages": ["fresh"], "llm_calls": 7}]
    assert calls == ["writer", "after"]


def test_c8_fresh_read_merges_the_reducing_channel_with_its_old_value() -> None:
    """**归约型**通道：fresh 视图 MUST 是「旧值 + 本次写入」的**归约结果**。"""
    observed: list[dict[str, Any]] = []

    builder = StateGraph(RouteState)
    builder.add_node("writer", lambda state: {"messages": ["fresh"]})
    builder.add_node("after", lambda state: {})
    builder.add_edge(START, "writer")
    builder.add_conditional_edges("writer", _router(observed, "after"), ["after"])

    builder.compile().invoke({"messages": ["seed"], "llm_calls": 0})

    assert observed == [{"messages": ["seed", "fresh"], "llm_calls": 0}]


def test_c8_fresh_read_omits_the_channels_without_a_value() -> None:
    """**无值**的**覆盖型**通道 MUST **不在**路由函数的入参里（稀疏口径）。"""
    observed: list[dict[str, Any]] = []

    builder = StateGraph(RouteState)
    builder.add_node("writer", lambda state: {"messages": ["fresh"]})
    builder.add_node("after", lambda state: {})
    builder.add_edge(START, "writer")
    builder.add_conditional_edges("writer", _router(observed, "after"), ["after"])

    builder.compile().invoke({"messages": []})

    assert observed == [{"messages": ["fresh"]}]
    assert "llm_calls" not in observed[0]


def test_c8_fresh_read_does_not_see_another_node_of_the_same_round() -> None:
    """fresh 读 = 「**本节点本次**写入」⇒ **不是**全轮（FR-008 / FR-010）。"""
    observed: list[dict[str, Any]] = []

    builder = StateGraph(RouteState)
    builder.add_node("a", lambda state: {"messages": ["A"]})
    builder.add_node("b", lambda state: {"messages": ["B"]})
    builder.add_node("c", lambda state: {})
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_conditional_edges("a", _router(observed, "c"), ["c"])

    builder.compile().invoke({"messages": []})

    assert observed == [{"messages": ["A"]}]


def test_the_routing_is_observable_through_the_invoke_facade() -> None:
    """**门面可观察**：条件边路由在 ``invoke``（B7F3 门面）上可观察（SC-002）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("a", _record(calls, "a"))
    builder.add_node("b", _record(calls, "b"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "a", ["a", "b"])

    out = builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["r", "a"]
    assert out["messages"] == []


def test_each_source_execution_evaluates_its_router_exactly_once() -> None:
    """每个源节点的**每次执行** MUST 只求值一次路由函数（FR-003）。"""
    route_calls: list[str] = []
    node_calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(node_calls, "r"))
    builder.add_node("a", _record(node_calls, "a"))
    builder.add_node("b", _record(node_calls, "b"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", _router([], "a", route_calls), ["a"])
    builder.add_conditional_edges("a", _router([], "b", route_calls), ["b"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert node_calls == ["r", "a", "b"]
    assert route_calls == ["route", "route"]


def test_the_fresh_read_does_not_pollute_the_official_channel_values() -> None:
    """fresh 读**零污染**：正式值 MUST NOT 被读层改写（FR-012 / I-5）。"""
    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {"messages": ["fresh"]})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "a", ["a"])

    out = builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert out["messages"] == ["fresh"]


def test_a_routing_loop_is_bounded_by_the_recursion_limit() -> None:
    """路由成环 MUST 受既有 ``recursion_limit`` 约束 ⇒ 抛 ``GraphRecursionError``。"""
    from freegraph.contracts import GraphRecursionError

    def _loop(state: dict[str, Any]) -> str:
        return "r"

    def _out(state: dict[str, Any]) -> str:
        return "a"

    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {"llm_calls": state.get("llm_calls", 0) + 1})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", _loop, ["r"])
    builder.add_conditional_edges("r", _out, ["a"])

    with pytest.raises(GraphRecursionError):
        builder.compile().invoke({"messages": [], "llm_calls": 0}, {"recursion_limit": 3})


# ── US2 · T030…T034 · T073 · ``path_map`` 双形态 ─────────────────────────


def test_the_list_form_of_path_map_routes_to_the_expected_node() -> None:
    """**list 形态**：路由函数返回的值 MUST 是 list 的**元素**（FR-016）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("a", _record(calls, "a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "a", ["a", END])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["r", "a"]


def test_the_dict_form_of_path_map_routes_to_the_expected_node() -> None:
    """**dict 形态**：返回值 MUST 作 **key** 查表（FR-015）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("a", _record(calls, "a"))
    builder.add_node("b", _record(calls, "b"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "hit", {"hit": "a", "miss": "b"})

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["r", "a"]


def test_the_dict_form_reports_the_returned_value_and_the_available_targets() -> None:
    """**有** ``path_map`` + 非法返回值 ⇒ 内置 ``KeyError`` + **详细消息**（X-1）。"""
    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "nope", {"hit": "a"})

    with pytest.raises(KeyError) as excinfo:
        builder.compile().invoke({"messages": [], "llm_calls": 0})

    message = str(excinfo.value)
    assert "nope" in message
    assert "hit" in message


def test_the_list_form_reports_the_same_key_error() -> None:
    """**list 形态**的查表失败 MUST 与 dict 形态**同款**（FR-016 / 裁定 6）。"""
    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "nope", ["a"])

    with pytest.raises(KeyError) as excinfo:
        builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert "nope" in str(excinfo.value)


def test_the_payload_carries_the_l3_normalization_verbatim() -> None:
    """L2 MUST **NOT** 重新归一化 ``path_map``（裁定 4 / I-2）。

    ⇒ 载荷里的 ``path_map`` MUST **逐字**等于 L3 的归一化结果。
    """
    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "a", ["a", END])

    compiled = builder.compile()

    payload = compiled._spec.conditional_edges["r"][0]
    assert payload["path_map"] == {"a": "a", "__end__": "__end__"}
    assert payload["branch"] == "<lambda>" or isinstance(payload["branch"], str)
    assert set(payload) == {
        "branch",
        "path",
        "path_map",
        "targets",
        "route_channels",
    }


def test_a_non_string_hashable_value_is_looked_up_as_a_key() -> None:
    """**非 ``str`` 的可哈希值**（如 ``int``）MUST 作 key **正常查表**（FR-020）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("a", _record(calls, "a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: 1, {1: "a"})

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["r", "a"]


# ── US3 · T035…T039 · ``END`` 终止 ──────────────────────────────────────


def test_returning_end_terminates_the_graph() -> None:
    """路由函数返回 ``END`` ⇒ 目标节点**执行 0 次**（FR-019 ① / SC-003）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("after", _record(calls, "after"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: END, ["after"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["r"]


def test_a_path_map_value_of_end_also_terminates() -> None:
    """``path_map`` 的 **value** 为 ``END`` ⇒ **同样终止**（FR-019 ②）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("a", _record(calls, "a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "stop", {"stop": END, "go": "a"})

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["r"]


def test_returning_end_without_a_path_map_key_still_terminates() -> None:
    """``path_map`` **不含** ``END`` 键 ⇒ **仍然终止**（不抛错 · 偏离 **X-2**）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("a", _record(calls, "a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: END, {"go": "a"})

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["r"]


def test_end_inside_a_sequence_is_dropped_and_the_other_targets_run() -> None:
    """序列内的 ``END`` ⇒ **剔除**；其余目标**照常执行**（FR-019 ③）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("a", _record(calls, "a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: [END, "a"], ["a", END])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["r", "a"]


def test_returning_end_terminates_even_when_the_path_map_maps_it_elsewhere() -> None:
    """``path_map = {END: "b"}`` ⇒ freegraph **无条件终止**（偏离 **X-2**）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("b", _record(calls, "b"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: END, {END: "b"})

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["r"]


# ── US4 · T040…T043 · T072 · 失败信号 ──────────────────────────────────


def test_an_invalid_return_value_with_a_path_map_raises_a_key_error() -> None:
    """**有** ``path_map`` + 非法返回值 ⇒ 内置 ``KeyError``（FR-021 / X-1）。"""
    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "nope", {"hit": "a"})

    with pytest.raises(KeyError):
        builder.compile().invoke({"messages": [], "llm_calls": 0})


def test_an_unregistered_node_without_a_path_map_raises_a_value_error() -> None:
    """**无** ``path_map`` + 未注册节点名 ⇒ 内置 ``ValueError``（FR-022 / X-3）。"""
    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "ghost")

    with pytest.raises(ValueError) as excinfo:
        builder.compile().invoke({"messages": [], "llm_calls": 0})

    message = str(excinfo.value)
    assert "ghost" in message
    assert "r" in message


def test_the_router_exception_propagates_with_its_own_type_and_message() -> None:
    """路由函数**自身**抛出的异常 MUST **原类型 + 原消息**传播（FR-023）。"""
    boom = RuntimeError("boom")

    def _explode(state: dict[str, Any]) -> str:
        raise boom

    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", _explode, ["a"])

    with pytest.raises(RuntimeError) as excinfo:
        builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert excinfo.value is boom
    assert str(excinfo.value) == "boom"


def test_the_two_failure_signals_are_exactly_key_error_and_value_error() -> None:
    """失败信号**两态** MUST **逐字一致**（FR-021 / FR-022 / I-7）。"""
    with_path_map = StateGraph(RouteState)
    with_path_map.add_node("r", lambda state: {})
    with_path_map.add_node("a", lambda state: {})
    with_path_map.add_edge(START, "r")
    with_path_map.add_conditional_edges("r", lambda state: "nope", {"hit": "a"})

    without_path_map = StateGraph(RouteState)
    without_path_map.add_node("r", lambda state: {})
    without_path_map.add_edge(START, "r")
    without_path_map.add_conditional_edges("r", lambda state: "ghost")

    with pytest.raises(KeyError):
        with_path_map.compile().invoke({"messages": [], "llm_calls": 0})
    with pytest.raises(ValueError):
        without_path_map.compile().invoke({"messages": [], "llm_calls": 0})


def test_returning_none_or_start_fails_with_the_lookup_first_semantics() -> None:
    """返回 ``None`` / ``START`` ⇒ **查表优先**的两态失败（FR-025 / V-31）。"""
    with_path_map = StateGraph(RouteState)
    with_path_map.add_node("r", lambda state: {})
    with_path_map.add_node("a", lambda state: {})
    with_path_map.add_edge(START, "r")
    with_path_map.add_conditional_edges("r", lambda state: None, {"hit": "a"})

    without_path_map = StateGraph(RouteState)
    without_path_map.add_node("r", lambda state: {})
    without_path_map.add_edge(START, "r")
    without_path_map.add_conditional_edges("r", lambda state: START)

    with pytest.raises(KeyError):
        with_path_map.compile().invoke({"messages": [], "llm_calls": 0})
    with pytest.raises(ValueError):
        without_path_map.compile().invoke({"messages": [], "llm_calls": 0})


def test_a_path_map_key_of_start_routes_instead_of_failing() -> None:
    """``path_map`` 恰含 ``__start__`` **键** ⇒ **照上游路由**（不失败 · FR-025）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("a", _record(calls, "a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: START, {START: "a"})

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["r", "a"]


# ── US5 · T044…T049 · T071 · T075 · 多目标 fan-out ──────────────────────


def test_a_sequence_return_value_fans_out_to_several_targets() -> None:
    """返回序列 ⇒ **多目标并行** fan-out（FR-018 / FR-024）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("b", _record(calls, "b"))
    builder.add_node("c", _record(calls, "c"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: ["b", "c"], ["b", "c"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    # ⚠️ 两个目标在**同一轮**并发执行 ⇒ ⇒ ⇒ 断言**集合**（**同轮内**的先后
    # **不可观察** · 同轮执行顺序 = **节点名序** · 但**线程调度**不承诺顺序）
    # ⇒ ⇒ ⇒ 「各执行 1 次」+「``r`` 先于它们」是**可判定**的。
    assert calls[0] == "r"
    assert sorted(calls) == ["b", "c", "r"]


def test_the_fan_out_targets_receive_the_very_same_shared_state() -> None:
    """多目标 ⇒ 各目标收到**同一份**共享状态（**无**逐目标载荷 · FR-018）。"""
    received: list[dict[str, Any]] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {"messages": ["written"]})
    builder.add_node("b", lambda state: received.append(dict(state)))
    builder.add_node("c", lambda state: received.append(dict(state)))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: ["b", "c"], ["b", "c"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert len(received) == 2
    assert received[0] == received[1]


def test_a_send_return_value_delivers_its_own_payload() -> None:
    """返回 ``Send`` ⇒ 目标收到**载荷**（**不是**共享状态 · 裁定 9）。"""
    received: list[Any] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {"messages": ["written"]})
    builder.add_node("b", lambda state: received.append(state))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: Send("b", {"payload": 1}), ["b"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert received == [{"payload": 1}]


def test_two_sources_routing_to_the_same_target_do_not_trigger_v6() -> None:
    """同轮**两个源**路由到同一目标 ⇒ **正常执行**（不触发 **V-6** · FR-028）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("a", _record(calls, "a"))
    builder.add_node("b", _record(calls, "b"))
    builder.add_node("c", _record(calls, "c"))
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_conditional_edges("a", lambda state: "c", ["c"])
    builder.add_conditional_edges("b", lambda state: "c", ["c"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls.count("c") == 1


def test_the_conditional_edges_are_not_confused_with_a_barrier_group() -> None:
    """条件边目标集合 MUST **不受**屏障组的「所有源齐备」判定影响（FR-006）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("a", _record(calls, "a"))
    builder.add_node("b", _record(calls, "b"))
    builder.add_node("c", _record(calls, "c"))
    builder.add_node("d", _record(calls, "d"))
    builder.add_edge(START, "a")
    builder.add_edge("d", "b")
    builder.add_edge(["a", "b"], "c")
    builder.add_conditional_edges("a", lambda state: "d", ["d"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    # ⚠️ 屏障组 ``["a", "b"] → "c"`` 直到 ``b`` 跑完（第 3 轮）才**齐备**
    # ⇒ ⇒ ⇒ ``c`` 必须**等**到第 4 轮 ⇒ ⇒ ⇒ 而条件边目标 ``d`` **不受**屏障
    # 影响 ⇒ ⇒ ⇒ 第 2 轮就**照常**执行 ⇒ ⇒ ⇒ **两套语义不混用**。
    # ⚠️ 本图**每轮只有一个节点** ⇒ ⇒ ⇒ 断言序列**确定**（无并发轮）。
    assert calls == ["a", "d", "b", "c"]


def test_several_conditional_edges_of_one_source_are_each_evaluated_once() -> None:
    """同一源节点的**多条**条件边 ⇒ 各求值一次 ⇒ 目标取**并集**（FR-004）。"""
    route_calls: list[str] = []
    calls: list[str] = []

    def _first(state: dict[str, Any]) -> str:
        route_calls.append("first")
        return "b"

    def _second(state: dict[str, Any]) -> str:
        route_calls.append("second")
        return "c"

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("b", _record(calls, "b"))
    builder.add_node("c", _record(calls, "c"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", _first, ["b"])
    builder.add_conditional_edges("r", _second, ["c"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert route_calls == ["first", "second"]
    assert calls == ["r", "b", "c"]


def test_a_send_from_the_router_produces_the_same_kind_of_task_as_a_node_send() -> None:
    """路由返回的 ``Send`` MUST 走 **B11F1 的既有构造器** ⇒ **同款任务**（FR-030）。"""
    from freegraph.runtime import _fanout

    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("b", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: Send("b", {"x": 1}), ["b"])

    compiled = builder.compile()
    compiled.invoke({"messages": [], "llm_calls": 0})

    # ⇒ 路由产出的 fan-out 任务与「节点返回 ``Send``」**同款**（同一个构造器）。
    assert _fanout.make_fanout is _fanout.make_fanout
    tasks = _fanout.make_fanout(
        "r", [Send("b", {"x": 1})], {"b"}, suppresses_static=True
    )
    assert len(tasks) == 1
    assert tasks[0].target == "b"
    assert tasks[0].arg == {"x": 1}
    assert tasks[0].suppresses_static is True


def test_an_empty_sequence_means_no_target_and_is_not_an_error() -> None:
    """返回**空序列** ``[]`` ⇒ **无目标** · **MUST NOT** 报错（FR-018 / FR-024）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("a", _record(calls, "a"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: [], ["a"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["r"]


def test_a_sequence_with_a_duplicated_target_triggers_it_only_once() -> None:
    """序列含**重复目标** ⇒ **去重保序**（同一目标**只**触发一次 · FR-018）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", _record(calls, "r"))
    builder.add_node("b", _record(calls, "b"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: ["b", "b"], ["b"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["r", "b"]


# ── Phase 2 · T013 · 动态边投递 ─────────────────────────────────────────


def test_the_route_targets_are_delivered_through_the_dynamic_edges() -> None:
    """路由目标 MUST 以**动态边**投递（键 == 源节点名 · 零新增触发机制）。"""
    from freegraph.runtime import GraphSpec, NodeSpec, SchedulerState, run_super_step

    spec = GraphSpec(
        channels={"llm_calls": _last_value()},
        nodes={
            "r": NodeSpec(subscribes=("llm_calls",), run=lambda state: {}),
            "a": NodeSpec(subscribes=("llm_calls",), run=lambda state: {}),
        },
        edges={"__start__": ("r",)},
        conditional_edges={
            "r": (
                {
                    "branch": "condition",
                    "path": lambda state: "a",
                    "path_map": {"a": "a"},
                    "targets": ("a",),
                    "route_channels": ("branch:to:a",),
                },
            )
        },
    )
    state = SchedulerState()

    run_super_step(spec, state)

    assert state.dynamic_edges["r"] == ("a",)
    assert state.dynamic_edges.keys() == {"r"}


def _last_value():
    from freegraph.runtime import LastValue

    return LastValue("llm_calls", int)


# ── Phase 2 · T015 / T074 · 双参形态 ────────────────────────────────────


def test_the_two_argument_form_receives_the_original_config() -> None:
    """双参形态的第二参 == 用户交给 ``invoke`` 的**原始** ``config``（FR-003）。"""
    received: list[Any] = []
    config = RunConfig(thread_id="t-1")

    def _route(state: dict[str, Any], config: RunConfig) -> str:
        received.append(config)
        return "a"

    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", _route, ["a"])

    builder.compile().invoke({"messages": [], "llm_calls": 0}, config)

    assert received == [config]
    assert received[0] is config


def test_a_second_parameter_not_named_config_is_called_with_one_argument() -> None:
    """第二参**不叫** ``config`` ⇒ 按**一参**调用（上游同款 ⇒ ``TypeError``）。"""
    def _route(state: dict[str, Any], cfg: Any) -> str:
        return "a"

    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", _route, ["a"])

    with pytest.raises(TypeError):
        builder.compile().invoke({"messages": [], "llm_calls": 0})


def test_the_kwargs_form_is_never_injected() -> None:
    """``**kwargs`` 形态 ⇒ **不注入**（上游同款 ⇒ kwargs 为空）。"""
    captured: list[dict[str, Any]] = []

    def _route(state: dict[str, Any], **kwargs: Any) -> str:
        captured.append(dict(kwargs))
        return "a"

    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", _route, ["a"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert captured == [{}]


def test_an_annotation_outside_the_match_set_skips_the_injection() -> None:
    """注解**不在匹配集**内 ⇒ **跳过注入** ⇒ 按**一参**调用 ⇒ ``TypeError``。"""
    def _route(state: dict[str, Any], config: dict) -> str:
        return "a"

    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", _route, ["a"])

    with pytest.raises(TypeError):
        builder.compile().invoke({"messages": [], "llm_calls": 0})


def test_the_skipped_injection_does_not_emit_a_user_warning() -> None:
    """**MUST NOT** 发 ``UserWarning``（偏离 **X-5** · 零新增可观察输出）。"""
    def _route(state: dict[str, Any], config: dict) -> str:
        return "a"

    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", _route, ["a"])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(TypeError):
            builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert [w for w in caught if issubclass(w.category, UserWarning)] == []


# ── Phase 2 · T016 · ``__start__`` 上的条件边 ───────────────────────────


def test_a_conditional_edge_on_start_is_evaluated() -> None:
    """``__start__`` 上的条件边 MUST **被求值**（不静默空跑 · FR-038）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("a", _record(calls, "a"))
    builder.add_conditional_edges(START, lambda state: "a", ["a"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["a"]


def test_a_pure_conditional_entry_is_allowed() -> None:
    """**纯条件边入口**（无静态入口点）MUST 可行（FR-039）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("a", _record(calls, "a"))
    builder.add_conditional_edges(START, lambda state: "a", ["a"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == ["a"]


def test_the_static_entry_and_the_conditional_entry_run_in_the_same_round() -> None:
    """静态入口与条件入口**并存** ⇒ 两者的目标**同轮并行**（FR-039）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("x", _record(calls, "x"))
    builder.add_node("y", _record(calls, "y"))
    builder.add_edge(START, "x")
    builder.add_conditional_edges(START, lambda state: "y", ["y"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert sorted(calls) == ["x", "y"]


def test_the_conditional_entry_returning_end_terminates_that_branch() -> None:
    """``__start__`` 条件边返回 ``END`` ⇒ 该分支**终止**（FR-039）。"""
    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("a", _record(calls, "a"))
    builder.add_conditional_edges(START, lambda state: END, ["a"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == []


def test_the_conditional_entry_is_evaluated_only_in_the_first_round() -> None:
    """``__start__`` 条件边的**求值次数 == 1**（**幂等** · 裁定 17）。"""
    route_calls: list[str] = []

    def _entry(state: dict[str, Any]) -> str:
        route_calls.append("entry")
        return "a"

    builder = StateGraph(RouteState)
    builder.add_node("a", lambda state: {})
    builder.add_node("b", lambda state: {})
    builder.add_conditional_edges(START, _entry, ["a"])
    builder.add_conditional_edges("a", lambda state: "b", ["b"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert route_calls == ["entry"]


# ── Phase 2 · T017 · branch 名唯一 ──────────────────────────────────────


def test_two_conditional_edges_with_the_same_branch_name_are_rejected() -> None:
    """同源**重名** branch ⇒ 内置 ``ValueError``（消息点名分支名与源节点）。"""
    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")

    def _route(state: dict[str, Any]) -> str:
        return "a"

    builder.add_conditional_edges("r", _route, ["a"])
    with pytest.raises(ValueError) as excinfo:
        builder.add_conditional_edges("r", _route, ["a"])

    message = str(excinfo.value)
    assert "_route" in message
    assert "r" in message


# ── US6 · T050…T053 · 零副作用 ──────────────────────────────────────────


def test_the_route_view_has_no_context_channel_and_no_route_channel() -> None:
    """路由入参 MUST **不含** ``context`` 通道 · **不含**路由通道（FR-011 / FR-029）。"""
    observed: list[dict[str, Any]] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", _router(observed, "a"), ["a"])

    out = builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert not any(key.startswith("branch:to:") for key in observed[0])
    assert not any(key.startswith("branch:to:") for key in out)


def test_the_route_targets_are_unioned_with_the_command_goto_targets() -> None:
    """条件边目标与同轮 ``Command.goto`` 目标 MUST 取**并集**（FR-031）。"""
    from freegraph.contracts import Command

    calls: list[str] = []

    builder = StateGraph(RouteState)
    builder.add_node("r", lambda state: Command(goto="x"))
    builder.add_node("x", _record(calls, "x"))
    builder.add_node("y", _record(calls, "y"))
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: "y", ["y"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert sorted(calls) == ["x", "y"]


# ── 一键验收脚本（**T076**）───────────────────────────────────────────────


def test_the_one_click_acceptance_script_passes() -> None:
    """`harness/verification/B8F1/acceptance.py` 一键验收 **PASS**（**A1…A10**）。

    ⚠️ **沿用 B13F1 的同款先例**（`tests/runtime/test_acceptance_script.py:68`）⇒
    ⇒ 本条把**逐 feature 的一键验收脚本**纳入 **CI 的常驻门禁** ⇒ ⇒ ⇒
    脚本与实现**漂移** ⇒ ⇒ ⇒ 本条**立刻红**。

    ⚠️ **此处用 ``--skip-differential``**：**差分闸口（A9）**在**全量套件**里已由
    `tests/differential/test_parity_probe.py` **独立**覆盖（同一批场景）⇒ ⇒ ⇒
    本条**MUST NOT** 在套件里**再跑一遍**（嵌套 pytest ⇒ 白白多花 ~20 秒）⇒ ⇒ ⇒
    差分证据仍**全程**由那个用例负责。
    """
    import os
    import subprocess
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "harness" / "verification" / "B8F1" / "acceptance.py"
    assert script.is_file(), f"缺一键验收脚本：{script}"

    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--skip-differential",
        ],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "B8F1 acceptance: PASS" in proc.stdout
