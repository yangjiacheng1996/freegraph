# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**条件边契约**的守卫测试 —— 属 **B8F1**（tasks T018）。

**契约权威**：``specs/b8f1-conditional-edges-fresh-read/contracts/conditional-edge-contract.md``
（``<!-- authority: yes -->``）⇒ 本文件 MUST **解析**该契约并**逐条**断言
§7 的 **I-1…I-14**（MUST NOT 只测行为而不校验契约文本）。

**逐条绑定**的机制（防「判据与实现同源 ⇒ 自证」）：

* **契约文本**是「**有哪些不变量**」的**唯一权威** ⇒ 本文件**解析** §7 的
  不变量编号集合；
* **编号 → 断言**的绑定写在 ``INVARIANT_TESTS`` 里 ⇒ 每条不变量**恰好**对应
  一个**真实断言**的测试函数；
* 参数化的守卫用例断言「**契约里的每条不变量都有绑定**」且「**每条绑定都
  指向一个真实存在的测试函数**」⇒ 契约新增一条不变量而没人断言 ⇒ **变红**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import ast
import copy
import operator
import re
from pathlib import Path
from typing import Annotated, Any, TypedDict

import pytest

from freegraph import contracts, graph, runtime
from freegraph.graph import END, START, StateGraph
from freegraph.runtime import (
    BinaryOperatorAggregate,
    Channel,
    EphemeralValue,
    GraphSpec,
    LastValue,
    NodeSpec,
    SchedulerState,
    local_read,
    run_super_step,
)

from ._runtime_export_manifest import ERROR_EXPORT_SYMBOLS, RUNTIME_EXPORT_SYMBOLS

#: 仓库根目录（契约文件的定位基准）。
REPO_ROOT = Path(__file__).resolve().parents[2]

#: **条件边契约**的唯一权威文件（``<!-- authority: yes -->``）。
CONDITIONAL_EDGE_CONTRACT_PATH = (
    REPO_ROOT
    / "specs"
    / "b8f1-conditional-edges-fresh-read"
    / "contracts"
    / "conditional-edge-contract.md"
)

#: 契约 §7 冻结的**不变量编号集合**（**逐条** · I-1…I-14）。
EXPECTED_INVARIANTS = tuple(f"I-{index}" for index in range(1, 15))

#: **编号 → 断言**的绑定表（每条不变量**恰好**一个**真实断言**的测试函数）。
INVARIANT_TESTS: dict[str, str] = {
    "I-1": "test_i1_the_conditional_payload_keeps_its_five_keys_verbatim",
    "I-2": "test_i2_the_path_map_is_not_renormalized_by_l2",
    "I-3": "test_i3_two_sources_routing_to_one_target_do_not_trigger_v6",
    "I-4": "test_i4_the_route_targets_are_delivered_through_the_dynamic_edges",
    "I-5": "test_i5_the_fresh_read_leaves_the_channels_untouched",
    "I-6": "test_i6_the_route_channels_are_absent_from_the_fresh_view",
    "I-7": "test_i7_the_two_failure_signals_are_key_error_and_value_error",
    "I-8": "test_i8_returning_end_terminates_and_a_sequence_drops_it",
    "I-9": "test_i9_the_router_exception_propagates_as_the_very_same_object",
    "I-10": "test_i10_the_config_injection_is_decided_by_the_parameter_name",
    "I-11": "test_i11_the_start_conditional_edge_is_evaluated_exactly_once",
    "I-12": "test_i12_a_duplicated_branch_name_is_rejected",
    "I-13": "test_i13_the_public_faces_are_unchanged",
    "I-14": "test_i14_no_new_error_type_is_introduced",
}


# ── 契约解析（**唯一权威** = 契约文本）────────────────────────────────────


def _contract_text() -> str:
    """读取条件边契约权威文件的全文。"""
    return CONDITIONAL_EDGE_CONTRACT_PATH.read_text(encoding="utf-8")


def _table_cells(line: str) -> list[str]:
    """把一行 Markdown 表格拆成单元格（去首尾空单元格 · 去空白）。"""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    parts = stripped.split("|")
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    parts = [cell.strip() for cell in parts]
    while parts and not parts[0]:
        parts = parts[1:]
    while parts and not parts[-1]:
        parts = parts[:-1]
    return parts


def _is_separator(cells: list[str]) -> bool:
    """判定是否表格的**分隔行**。"""
    return bool(cells) and all(set(cell) <= {"-", ":", " "} and cell for cell in cells)


def _section_body(text: str, heading: str) -> list[str]:
    """取出某个 ``## `` 小节的正文行（**不含**小节标题本身）。"""
    collected: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.startswith(heading)
            continue
        if inside:
            collected.append(line)
    return collected


def _contract_invariants() -> list[str]:
    """**解析**契约 §7 ⇒ 不变量编号列表（**按出现顺序**）。"""
    identifiers: list[str] = []
    for line in _section_body(_contract_text(), "## 7."):
        cells = _table_cells(line)
        if len(cells) < 2 or _is_separator(cells):
            continue
        match = re.fullmatch(r"\*\*(I-\d+)\*\*|(I-\d+)", cells[0])
        if match:
            identifiers.append(match.group(1) or match.group(2))
    return identifiers


# ── 守卫 · 契约与绑定**双向齐全**（防「新增不变量而没人断言」）──────────


def test_the_contract_declares_exactly_the_expected_invariants() -> None:
    """契约 §7 的不变量编号集合 == 期望集合（**逐条** · I-1…I-14）。"""
    assert _contract_invariants() == list(EXPECTED_INVARIANTS)


@pytest.mark.parametrize("invariant", EXPECTED_INVARIANTS)
def test_every_contract_invariant_has_a_binding(invariant: str) -> None:
    """契约里的**每条**不变量都有**编号 → 断言**的绑定。"""
    assert invariant in INVARIANT_TESTS


@pytest.mark.parametrize("invariant", EXPECTED_INVARIANTS)
def test_every_binding_points_to_a_real_test_function(invariant: str) -> None:
    """**每条**绑定都指向一个**真实存在**的测试函数。"""
    name = INVARIANT_TESTS[invariant]
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"), filename=__file__)
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert name in functions


# ── 共享夹具 ────────────────────────────────────────────────────────────


class _RouteState(TypedDict):
    """被测 schema（**归约型** + **覆盖型**）。"""

    messages: Annotated[list, operator.add]
    llm_calls: int


def _compiled_with_routes(path_map: Any = None, result: str = "a"):
    """编译一张「``r`` →（条件边）→ ``a``」的最小图 + 路由函数。"""
    builder = StateGraph(_RouteState)
    builder.add_node("r", lambda state: {"messages": ["written"]})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", lambda state: result, path_map)
    return builder.compile()


# ── I-1…I-14 的**逐条**断言 ─────────────────────────────────────────────


def test_i1_the_conditional_payload_keeps_its_five_keys_verbatim() -> None:
    """**I-1**：载荷的**五键**形态**逐字不变**（且与编译产物**逐字相等**）。"""
    compiled = _compiled_with_routes(["a", END])
    payload = compiled._spec.conditional_edges
    assert payload == compiled._conditional_edges
    for entries in payload.values():
        for entry in entries:
            assert set(entry) == {
                "branch",
                "path",
                "path_map",
                "targets",
                "route_channels",
            }


def test_i2_the_path_map_is_not_renormalized_by_l2() -> None:
    """**I-2**：``path_map`` **不被重新归一化**（L2 只消费 L3 的两形态）。"""
    compiled = _compiled_with_routes(["a", END])
    entry = compiled._spec.conditional_edges["r"][0]
    assert entry["path_map"] == {"a": "a", "__end__": "__end__"}
    assert isinstance(entry["path_map"], dict)


def test_i3_two_sources_routing_to_one_target_do_not_trigger_v6() -> None:
    """**I-3**：路由通道**零写入** ⇒ MUST NOT 触发 **V-6**。"""
    calls: list[str] = []

    builder = StateGraph(_RouteState)
    builder.add_node("a", lambda state: calls.append("a"))
    builder.add_node("b", lambda state: calls.append("b"))
    builder.add_node("c", lambda state: calls.append("c"))
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_conditional_edges("a", lambda state: "c", ["c"])
    builder.add_conditional_edges("b", lambda state: "c", ["c"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls.count("c") == 1


def test_i4_the_route_targets_are_delivered_through_the_dynamic_edges() -> None:
    """**I-4**：路由目标以**动态边**投递（键 == 源节点名 · 零新增触发机制）。"""
    spec = GraphSpec(
        channels={"llm_calls": LastValue("llm_calls", int)},
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
    assert list(state.dynamic_edges) == ["r"]


def test_i5_the_fresh_read_leaves_the_channels_untouched() -> None:
    """**I-5**：fresh 读**零污染**（绑定与可用性判定**不变**）。"""
    channels = {
        "a": LastValue("a", int),
        "route": EphemeralValue("route", str),
        "acc": BinaryOperatorAggregate("acc", list, operator.add),
    }
    channels["a"].update([2])
    channels["acc"].update([["x"]])
    before = [
        (key, channel.is_available(), channel.get())
        for key, channel in channels.items()
        if channel.is_available()
    ]

    local_read(channels, {"acc": [["y"]]}, fresh=True)

    after = [
        (key, channel.is_available(), channel.get())
        for key, channel in channels.items()
        if channel.is_available()
    ]
    assert after == before


def test_i6_the_route_channels_are_absent_from_the_fresh_view() -> None:
    """**I-6**：路由通道**缺席**于 fresh 视图（且**不**用名称前缀启发式）。"""
    observed: list[dict[str, Any]] = []

    builder = StateGraph(_RouteState)
    builder.add_node("r", lambda state: {"messages": ["written"]})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges(
        "r", lambda state: (observed.append(dict(state)) or "a"), ["a"]
    )

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert observed
    assert not any(key.startswith("branch:to:") for key in observed[0])


def test_i7_the_two_failure_signals_are_key_error_and_value_error() -> None:
    """**I-7**：失败信号**两态**（**有** ``path_map`` ⇒ ``KeyError``；**无** ⇒ ``ValueError``）。"""
    with_path_map = StateGraph(_RouteState)
    with_path_map.add_node("r", lambda state: {})
    with_path_map.add_node("a", lambda state: {})
    with_path_map.add_edge(START, "r")
    with_path_map.add_conditional_edges("r", lambda state: "nope", {"hit": "a"})

    without_path_map = StateGraph(_RouteState)
    without_path_map.add_node("r", lambda state: {})
    without_path_map.add_edge(START, "r")
    without_path_map.add_conditional_edges("r", lambda state: "ghost")

    with pytest.raises(KeyError):
        with_path_map.compile().invoke({"messages": [], "llm_calls": 0})
    with pytest.raises(ValueError):
        without_path_map.compile().invoke({"messages": [], "llm_calls": 0})


def test_i8_returning_end_terminates_and_a_sequence_drops_it() -> None:
    """**I-8**：**单独返回** ``END`` ⇒ 无条件终止；**序列**内的 ``END`` ⇒ 剔除。"""
    calls: list[str] = []

    terminating = StateGraph(_RouteState)
    terminating.add_node("r", lambda state: calls.append("r"))
    terminating.add_node("a", lambda state: calls.append("a"))
    terminating.add_edge(START, "r")
    terminating.add_conditional_edges("r", lambda state: END, ["a"])
    terminating.compile().invoke({"messages": [], "llm_calls": 0})
    assert calls == ["r"]

    calls.clear()
    dropping = StateGraph(_RouteState)
    dropping.add_node("r", lambda state: calls.append("r"))
    dropping.add_node("a", lambda state: calls.append("a"))
    dropping.add_edge(START, "r")
    dropping.add_conditional_edges("r", lambda state: [END, "a"], ["a", END])
    dropping.compile().invoke({"messages": [], "llm_calls": 0})
    assert calls == ["r", "a"]


def test_i9_the_router_exception_propagates_as_the_very_same_object() -> None:
    """**I-9**：路由函数**自身**的异常**原样**传播（**同一对象**）。"""
    boom = RuntimeError("boom")

    def _explode(state: dict[str, Any]) -> str:
        raise boom

    builder = StateGraph(_RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", _explode, ["a"])

    with pytest.raises(RuntimeError) as excinfo:
        builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert excinfo.value is boom
    assert str(excinfo.value) == "boom"


def test_i10_the_config_injection_is_decided_by_the_parameter_name() -> None:
    """**I-10**：双参判别**按参数名** ``config``（**不是**位置参数个数）。"""
    calls: list[str] = []

    def _misnamed(state: dict[str, Any], cfg: Any) -> str:
        calls.append("misnamed")
        return "a"

    builder = StateGraph(_RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", _misnamed, ["a"])

    with pytest.raises(TypeError):
        builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert calls == []


def test_i11_the_start_conditional_edge_is_evaluated_exactly_once() -> None:
    """**I-11**：``__start__`` 上的条件边**被求值**且**求值次数 == 1**。"""
    route_calls: list[str] = []

    def _entry(state: dict[str, Any]) -> str:
        route_calls.append("entry")
        return "a"

    builder = StateGraph(_RouteState)
    builder.add_node("a", lambda state: {})
    builder.add_node("b", lambda state: {})
    builder.add_conditional_edges(START, _entry, ["a"])
    builder.add_conditional_edges("a", lambda state: "b", ["b"])

    builder.compile().invoke({"messages": [], "llm_calls": 0})

    assert route_calls == ["entry"]


def test_i12_a_duplicated_branch_name_is_rejected() -> None:
    """**I-12**：同源**重名** branch ⇒ 内置 ``ValueError``（点名分支名与源节点）。"""
    builder = StateGraph(_RouteState)
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


def test_i13_the_public_faces_are_unchanged() -> None:
    """**I-13**：B8F2 后公开面为 8 / 23 / 22（原 7 / 23 / 21 只增不删）。"""
    assert len(graph.__all__) == 8
    assert set(runtime.__all__) == set(RUNTIME_EXPORT_SYMBOLS)
    assert len(contracts.__all__) == 22

    builder = StateGraph(_RouteState)
    builder.add_node("r", lambda state: {})
    builder.add_node("a", lambda state: {})
    builder.add_edge(START, "r")
    compiled = builder.compile()
    assert len(vars(compiled)) == 12


def test_i14_no_new_error_type_is_introduced() -> None:
    """**I-14**：**零新增错误类型**（只用内置 ``KeyError`` / ``ValueError``）。"""
    assert set(runtime.errors.__all__) == set(ERROR_EXPORT_SYMBOLS)
